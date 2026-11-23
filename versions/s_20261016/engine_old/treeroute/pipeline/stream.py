"""The pipeline's side of the streaming census (derive/census.py): the target store as a file-by-file
source, the drivers' row presence per target file (F2, J5), and the column reader derive_all_streamed
calls for R30.

Boilerplate around pipeline/data.py and the approved io functions; it names no problem, unit, year or
drive (G-NONAMES). Every check read_target and ColumnReader make on the rows they read is made here on
each file, so a full-size run refuses what a small one refuses.

  - TargetFileSource: the target files of the run's groups in read_target's order (group by group, in
    the order the listing first names each group; a group's files in listing order), each read through
    the package's target reader (or the generic reader) with read_target's checks. A smoke's fixed-size
    pick runs first, group by group: pick_units(group, its units with a valid label) -- the only thing
    the smoke's pick reads of read_target's whole group frame -- with those units gathered file by file
    (a group is never held whole).
  - PresenceReader: ColumnReader's store plan (the same driver templates, columns, absent groups and
    refusals), answering per target file which stores hold each row: (unit, calendar parts) for a
    store keyed like the target, (unit, year) for a coarse store. A group's driver keys are read once
    (key columns only) and kept while that group's files stream; each driver file's first and last
    calendar coordinate is kept (file_coords). A driver store whose template has no {group} placeholder
    is refused (its files would be read once per group).
  - StreamedShareReader: R30's shares. The donor-row shares come from a ColumnReader built on the
    PICKED units' full rows (the bank units: the pool reads the same reader). The per-test-year missing
    share is over EVERY target row of the year (ColumnReader.measure's rule): when the picked rows are
    every census row it is the picked reader's own; otherwise it is counted once per lag map and test
    years (both derive passes read the same count) over every census unit with a row in a test year,
    group by group in unit blocks, and the counts are divided once, the same number numpy's mean gives.
    A block reads only the rows from a first year on (window_of_test_years: far enough back that the
    lagged, last-value-filled value of every tree feature at every test-year row is the value a reader
    of whole unit histories gives), skips the target and driver files that end before it, and drops
    every label as it is read. The window rests on R8's lags, the last-value maximum and the feature
    script's DECLARED backward windows; it is checked in the run: in every block, each picked unit's
    lagged tree features at its test-year rows must equal the picked reader's (whole histories), or the
    run refuses (R30).
  - GroupReaders (plan R20's per-group batching, the pipeline's default): the picked units' column reader
    built ONE GROUP AT A TIME from the picked rows already read (census.read_units' cached picked rows), used
    and released before the next group, so RAM holds one group's reader (the largest group's picked rows at
    the peak), never every picked unit's. StreamedShareReader(group_readers=True) measures R30 with them:
    the donor-row missing and zero counts, the last-value counts and (when every census row is picked) the
    per-test-year counts are INTEGER counts summed over the groups and divided once (the same float numpy's
    mean gives over the whole reader); the streamed test-year blocks of a group are checked against that
    group's picked reader. The per-group path rests on the feature script being group-separable (a group's
    outputs computed alone equal its outputs computed beside the other groups); check_group_separable checks
    it in every run on the smoke-shaped sample (the first C13.smoke_groups groups, C13.smoke_units_per_group
    picked units each: on a smoke, its whole pick) and refuses the per-group path when it does not hold.
"""

import datetime as _dt
import hashlib
import json
import math
import time
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from treeroute import engine_constants as K
from treeroute.derive.census import FileRows
from treeroute.derive.shapes import MissingShares
from treeroute.io.listing import list_store
from treeroute.io.readers import read_footer
from treeroute.io.joins import coarse_periods
from treeroute.io.lastvalue import last_value_max_steps
from treeroute.runs.checkpoint import record_name
from treeroute.io.steps import (COMPOSITE_OF_YEAR, as_int_array, cadence_identity, cadence_view, step_bounds,
                                step_containing)

from . import data as D

KEY_SHIFT = 20                       # a driver key: unit code << KEY_SHIFT | calendar coordinate
_SHOW = 5


def _coord(time_columns: Mapping[str, np.ndarray], time_facts: Mapping[str, str]) -> np.ndarray:
    """The calendar coordinate the census keys a row by: year x 12 + month - 1, or the year."""
    part = {D._v(f): c for c, f in time_facts.items()}
    year = as_int_array(time_columns[part["year"]], "time column %s" % part["year"])
    if "month" in part:
        month = as_int_array(time_columns[part["month"]], "time column %s" % part["month"])
        return year * K.MONTHS_PER_YEAR + month - 1
    return year


# ---------------------------------------------------------------------------------------------------
class TargetFileSource(object):
    """The run's target files as a census source (module docstring)."""

    def __init__(self, package: Any, spec: D.PackageSpec, hook: Any, listing: Any, groups: Optional[Sequence[str]],
                 pick_units: Optional[Callable[[str, Sequence[str]], Any]] = None,
                 echo: Callable[[str], None] = print) -> None:
        import pyarrow.parquet as pq

        files = D._files_of(listing, groups)
        if not files:
            raise D.DataRefusal("G-SUPPORT", "no target file for the groups %s" % D._fmt(groups or ()))
        self._reader = getattr(hook, "read_target_file", None) if hook is not None else None
        if hook is not None and not callable(self._reader):
            raise D.DataRefusal("R1", "ingest/target_reader.py has no read_target_file(path, key)")
        self.package, self.spec, self.listing, self.echo = package, spec, listing, echo
        self.wanted = [spec.unit_col, spec.group_col] + list(spec.time_facts) + [spec.target_col]
        by_group: Dict[str, List[Tuple[Any, str]]] = {}
        order: List[str] = []
        for key, path in files:
            kd = D._key_dict(listing, key)
            g = str(kd.get(D.GROUP_PLACEHOLDER, "")) or "__all__"
            if g not in by_group:
                by_group[g] = []
                order.append(g)
            by_group[g].append((key, path))
        self.files = [(g, key, path) for g in order for key, path in by_group[g]]
        self.groups = tuple(order)
        self._meta_rows = {path: int(pq.ParquetFile(path).metadata.num_rows) for _, _, path in self.files}
        self._keep: Optional[Dict[str, frozenset]] = None
        self._kept_rows: Optional[int] = None
        if pick_units is not None:
            self._pick(pick_units)

    def _raw(self, handle: Any) -> pd.DataFrame:
        g, key, path = handle
        kd = D._key_dict(self.listing, key)
        frame = self._reader(path, kd) if self._reader is not None else D._read_target_generic(path, kd, self.spec)
        if not isinstance(frame, pd.DataFrame):
            raise D.DataRefusal("R1", "the target reader returned %s for %s" % (type(frame).__name__, path))
        missing = [c for c in self.wanted if c not in frame.columns]
        if missing:
            raise D.DataRefusal("R1", "the target rows of %s lack the columns %s" % (path, missing))
        frame = frame[self.wanted]
        if D.GROUP_PLACEHOLDER in kd:
            wrong = frame[self.spec.group_col].astype(object).to_numpy() != kd[D.GROUP_PLACEHOLDER]
            if wrong.any():
                raise D.DataRefusal("G-DISJOINT", "%d target rows of %s carry another group than the file's %r"
                                    % (int(wrong.sum()), path, kd[D.GROUP_PLACEHOLDER]))
        return frame

    def _pick(self, pick_units: Callable[[str, Sequence[str]], Any]) -> None:
        """The smoke's pick before the census pass: per group, pick_units(group, the group's units with a
        valid label, as text), those units and each unit's row count gathered file by file."""
        spec = self.spec
        self._keep, self._kept_rows = {}, 0
        for g in self.groups:
            valid: set = set()
            rows: Dict[str, int] = {}
            for h in self.files:
                if h[0] != g:
                    continue
                frame = self._raw(h)
                units = frame[spec.unit_col].astype(str)
                ok = np.isfinite(frame[spec.target_col].to_numpy(dtype=np.float64))
                valid.update(units[ok].tolist())
                for u, n in units.value_counts(sort=False).items():
                    rows[u] = rows.get(u, 0) + int(n)
                del frame, units
            keep = frozenset(pick_units(g, sorted(valid)))
            self._keep[g] = keep
            self._kept_rows += int(sum(n for u, n in rows.items() if u in keep))

    def expected_rows(self) -> int:
        return int(self._kept_rows) if self._kept_rows is not None else int(sum(self._meta_rows.values()))

    def meta_rows(self) -> Dict[str, int]:
        return dict(self._meta_rows)

    def file_groups(self, handle: Any) -> Optional[Tuple[str, ...]]:
        return (handle[0],) if D.GROUP_PLACEHOLDER in self.listing.key_names else None

    def read(self, handle: Any) -> FileRows:
        spec = self.spec
        frame = self._raw(handle)
        if self._keep is not None:
            frame = frame[frame[spec.unit_col].isin(set(self._keep[handle[0]]))].reset_index(drop=True)
        y = frame[spec.target_col].to_numpy()
        if y.dtype.kind not in "fiu" or y.dtype == np.bool_:
            raise D.DataRefusal("R1", "the target column %s is not numeric (%s)" % (spec.target_col, y.dtype))
        y = y.astype(np.float64)
        big = np.isfinite(y) & (np.abs(y) >= K.SENTINEL_MASK_ABS)
        if big.any():
            raise D.DataRefusal("G-SENTINEL", "%d target values at the sentinel magnitude; the ingest writes invalid "
                                "labels as NaN (D30)" % int(big.sum()),
                                fix="the package's target reader (ingest/) must write NaN for invalid labels")
        if np.isinf(y).any():
            raise D.DataRefusal("G-SENTINEL", "%d target values are infinite" % int(np.isinf(y).sum()))
        return FileRows(unit_ids=D.shared_str_ids(frame[spec.unit_col], "unit id") if len(frame) else
                        np.zeros(0, dtype=object),
                        group_ids=D.shared_str_ids(frame[spec.group_col], "group id") if len(frame) else
                        np.zeros(0, dtype=object),
                        time_columns={c: as_int_array(frame[c].to_numpy(), "time column %s" % c, rule="R1")
                                      for c in spec.time_facts},
                        y=y)


def rows_frame(rows: Any, spec: D.PackageSpec) -> pd.DataFrame:
    """A target frame (read_target's columns) of rows read back from the census."""
    frame = pd.DataFrame({spec.unit_col: np.asarray(rows.unit_ids, dtype=object),
                          spec.group_col: np.asarray(rows.group_ids, dtype=object)})
    for c in spec.time_facts:
        frame[c] = np.asarray(rows.time_columns[c], dtype=np.int64)
    frame[spec.target_col] = np.asarray(rows.y, dtype=np.float64)
    return frame


# ---------------------------------------------------------------------------------------------------
class PresenceReader(object):
    """F2's row presence per target file, with ColumnReader's store plan (module docstring)."""

    def __init__(self, package: Any, spec: D.PackageSpec, feature_hook: Any, groups: Sequence[str]) -> None:
        self.spec = spec
        self.outputs = D.feature_outputs(feature_hook) if feature_hook is not None else {}
        wanted_kept = tuple(spec.tree_features) + tuple(spec.context)
        sources = sorted({s for c in self.outputs for s in self.outputs[c].derived_from})
        stored_needed = [c for c in list(wanted_kept) + sources
                         if c not in self.outputs and c not in spec.time_facts
                         and c not in (spec.unit_col, spec.group_col)]
        stored_needed = list(dict.fromkeys(stored_needed))
        optional = [c for c in spec.strata if c not in stored_needed]
        run_groups = sorted(set(groups))
        remaining = list(stored_needed + optional)
        target_parts = tuple(spec.time_facts)
        plan = []
        for template in package.dataset.stores.drivers:
            listing = list_store(template, base=package.root)
            if not listing.files:
                raise D.DataRefusal("G-MISSING", "driver store %s holds no file" % listing.path_template)
            names = read_footer(listing.files[0][1]).names
            cols = [c for c in remaining if c in names]
            if not cols:
                continue
            remaining = [c for c in remaining if c not in cols]
            parts_in_file = tuple(c for c in target_parts if c in names)
            by_step = parts_in_file == target_parts
            coarse_parts = tuple(c for c in parts_in_file if spec.time_facts[c] == "year")
            if not by_step and coarse_parts != parts_in_file:
                raise D.DataRefusal("G-JOIN", "driver store %s holds the time columns %s: neither the target's "
                                    "%s nor a year" % (listing.path_template, parts_in_file, target_parts))
            absent = frozenset.intersection(*[frozenset((getattr(spec.store_facts.get(c), "absent_groups", {})
                                                         or {}).keys()) for c in cols])
            listed = D.listed_groups(listing)
            if listed is None:
                raise D.DataRefusal("G-DISK", "driver store %s has no {group} placeholder: the streamed census "
                                    "reads a store's keys group by group and would read every one of its files "
                                    "once per group" % listing.path_template,
                                    fix="owner item: give the store a {group} placeholder, or build the streamed "
                                        "read of a store without one")
            missing_groups = sorted(set(run_groups) - set(listed) - set(absent))
            if missing_groups:
                raise D.DataRefusal("G-MISSING", "driver store %s has no file for the groups %s, which no "
                                    "store fact declares absent" % (listing.path_template, D._fmt(missing_groups)))
            plan.append(SimpleNamespace(template=template, listing=listing, columns=tuple(cols),
                                        parts=parts_in_file, by_step=by_step, absent=absent))
        remaining = [c for c in remaining if c not in optional]
        if remaining:
            raise D.DataRefusal("G-CLOSED", "columns %s are held by no driver store of dataset.yaml"
                                % D._fmt(remaining), fix="declare the store that holds them")
        self.plan = plan
        self.stores = tuple(p.template for p in plan)
        self.absent = tuple(p.absent for p in plan)
        self._cache: Dict[int, Tuple[str, Any]] = {}
        self.files_read: List[str] = []
        self.file_coords: Dict[str, Optional[Tuple[int, int]]] = {}    # driver file -> (first, last) coordinate
        self.file_rows: Dict[str, int] = {}                             # driver file -> its rows (the RAM checks)
        # census checkpoints (owner ruling P1): store index -> (group, its driver files) whose keys the stopped
        # process held when its last chunk was saved; a resumed census reads them once more without counting
        # them twice in files_read (restore_checkpoint_state)
        self._reread: Dict[int, Tuple[str, set]] = {}

    # ------------------------------------------------------------------ census checkpoints (owner ruling P1)
    def checkpoint_state(self, since: int) -> Dict[str, Any]:
        """The driver files read since files_read[since] (path, calendar span, rows) and the groups whose keys are
        held now with their files (JSON-ready; derive/census.py CensusCheckpoint saves it with each chunk)."""
        files = [[p, None if self.file_coords.get(p) is None else [int(x) for x in self.file_coords[p]],
                  int(self.file_rows[p])] for p in self.files_read[int(since):]]
        held = [[int(i), str(g), [str(path) for _, path in D._files_of(self.plan[i].listing, [g])]]
                for i, (g, _) in sorted(self._cache.items())]
        return {"files": files, "held": held}

    def restore_checkpoint_state(self, state: Mapping[str, Any]) -> None:
        """Replay one chunk's checkpoint_state (in chunk order). Refuses a driver file already replayed."""
        from treeroute.derive.census import CensusCheckpointMismatch

        seen = set(self.files_read)
        for p, span, rows in state["files"]:
            if p in seen:
                raise CensusCheckpointMismatch("driver file %s is replayed twice" % p)
            seen.add(p)
            self.files_read.append(str(p))
            self.file_coords[str(p)] = None if span is None else (int(span[0]), int(span[1]))
            self.file_rows[str(p)] = int(rows)
        self._reread = {int(i): (str(g), set(str(x) for x in paths)) for i, g, paths in state["held"]}

    def reset_checkpoint_state(self) -> None:
        self._cache.clear()
        self.files_read, self.file_coords, self.file_rows, self._reread = [], {}, {}, {}

    def stores_for(self, columns: Sequence[str]) -> Tuple[int, ...]:
        wanted = set()
        for c in columns:
            if c in self.outputs:
                wanted.update(self.outputs[c].derived_from)
            else:
                wanted.add(c)
        return tuple(i for i, p in enumerate(self.plan) if wanted & set(p.columns))

    def _keys(self, i: int, group: str) -> Tuple[pd.Index, np.ndarray]:
        """(unit index, sorted keys) of store i's rows of one group (key columns only; cached while the
        group's target files stream)."""
        import pyarrow as pa
        import pyarrow.parquet as pq

        hit = self._cache.get(i)
        if hit is not None and hit[0] == group:
            return hit[1]
        p = self.plan[i]
        spec = self.spec
        # a resumed census (owner ruling P1): the files of the group whose keys the stopped process held are read
        # again here once, and were counted in files_read already
        held = self._reread.pop(i, None)
        again = set(held[1]) if held is not None and held[0] == group else set()
        code_of: Dict[Any, int] = {}
        codes, coords = [], []
        for _, path in D._files_of(p.listing, [group]):
            with pq.ParquetFile(path) as pf:
                table = pf.read(columns=[spec.unit_col] + list(p.parts))
            # unit ids dictionary-encoded: one text object per distinct unit, never one per row
            enc = table.column(spec.unit_col).cast(pa.string()).combine_chunks().dictionary_encode()
            local = np.array([code_of.setdefault(u, len(code_of)) for u in enc.dictionary.to_pylist()],
                             dtype=np.int64)
            # a row without a unit id names no target unit (ColumnReader's unit filter drops it too)
            has = ~np.asarray(enc.is_null().to_numpy(zero_copy_only=False), dtype=bool)
            idx = enc.indices.fill_null(0).to_numpy(zero_copy_only=False).astype(np.int64)
            codes.append(local[idx][has] if len(local) else np.zeros(0, dtype=np.int64))
            tc = {c: table.column(c).to_numpy(zero_copy_only=False)[has] for c in p.parts}
            facts = {c: spec.time_facts[c] for c in p.parts}
            coords.append(_coord(tc, facts))
            span = (int(coords[-1].min()), int(coords[-1].max())) if len(coords[-1]) else None
            if str(path) in again:
                again.discard(str(path))
                if self.file_coords.get(str(path)) != span or self.file_rows.get(str(path)) != int(table.num_rows):
                    raise D.DataRefusal("P1", "driver file %s changed since the census checkpoint that read it (span "
                                        "%s, %s rows; now %s, %d rows)" % (path, self.file_coords.get(str(path)),
                                                                          self.file_rows.get(str(path)), span,
                                                                          int(table.num_rows)),
                                        fix="never write a store a run reads; run again (the checkpoint's key "
                                            "holds every file's size and time)")
            else:
                self.file_coords[str(path)] = span
                self.file_rows[str(path)] = int(table.num_rows)
                self.files_read.append(str(path))
            del table, enc
        code = np.concatenate(codes) if codes else np.zeros(0, dtype=np.int64)
        c = np.concatenate(coords) if coords else np.zeros(0, dtype=np.int64)
        index = pd.Index(list(code_of), dtype=object)
        if len(c) and (c.min() < 0 or c.max() >= (1 << KEY_SHIFT)):
            raise D.DataRefusal("G-JOIN", "driver store %s holds calendar coordinates outside 0..2^%d"
                                % (p.template, KEY_SHIFT))
        keys = np.sort((code << KEY_SHIFT) | c)
        out = (index, keys)
        self._cache[i] = (group, out)
        return out

    def masks(self, rows: Any) -> np.ndarray:
        units = np.asarray(rows.unit_ids, dtype=object)
        groups = np.asarray(rows.group_ids, dtype=object)
        out = np.zeros(len(units), dtype=np.uint32)
        if not len(units):
            return out
        tcoord = _coord(rows.time_columns, self.spec.time_facts)
        years = tcoord // K.MONTHS_PER_YEAR if "month" in {D._v(f) for f in self.spec.time_facts.values()} \
            else tcoord
        for g in pd.unique(groups).tolist():
            sel = groups == g
            for i, p in enumerate(self.plan):
                if g in p.absent and D.listed_groups(p.listing) is not None \
                        and g not in set(D.listed_groups(p.listing)):
                    continue                                   # declared absent, no file: no row is held
                index, keys = self._keys(i, g)
                code = index.get_indexer(units[sel]).astype(np.int64)
                coord = tcoord[sel] if p.by_step else years[sel]
                want = (code << KEY_SHIFT) | coord
                order = np.argsort(want, kind="stable")       # sorted queries: searchsorted walks forward
                lo = np.empty(len(want), dtype=np.int64)
                hi = np.empty(len(want), dtype=np.int64)
                lo[order] = np.searchsorted(keys, want[order], side="left")
                hi[order] = np.searchsorted(keys, want[order], side="right")
                held = (code >= 0) & (hi > lo)
                if ((hi - lo) > 1).any():
                    raise D.DataRefusal("G-JOIN", "driver store %s repeats a (unit, %s) of %d target rows"
                                        % (p.template, "step" if p.by_step else "year", int(((hi - lo) > 1).sum())))
                bits = out[sel]
                bits[held] |= np.uint32(1 << i)
                out[sel] = bits
        return out


def census_data_manifest(reader: Any, census: Any, presence: PresenceReader) -> Dict[str, Any]:
    """ColumnReader.data_manifest as the whole-table reader of the run reports it (what the run read:
    every target row; the fingerprint hashes it), from the picked reader and the census: the target rows
    and units are the census's, each store's present rows the census's presence count of that store over
    every target row, the driver files those the census pass read (every run group's, as the whole-table
    reader reads them); the stores and feature outputs are the picked reader's. Refuses a store plan that
    differs from the presence reader's, and a driver file the presence reader read twice."""
    out = dict(reader.data_manifest())
    stores = list(out["stores"])
    if [s["template"] for s in stores] != list(presence.stores):
        raise D.DataRefusal("F2", "internal: the column reader's stores %s differ from the census presence "
                            "reader's %s" % ([s["template"] for s in stores], list(presence.stores)))
    if len(set(presence.files_read)) != len(presence.files_read):
        raise D.DataRefusal("F2", "internal: the census presence reader read a driver file twice")
    out["target_rows"] = int(census.rows)
    out["units"] = int(census.n_units())
    out["stores"] = [dict(s, present_rows=census.present_rows(i)) for i, s in enumerate(stores)]
    out["driver_files"] = len(presence.files_read)
    return out


# ---------------------------------------------------------------------------------------------------
def _months(length: float, unit: str) -> float:
    """A length in months, rounded up for days (a month holds at least 28 days)."""
    if unit == "day":
        return float(length) / 28.0
    if unit == "month":
        return float(length)
    if unit == "year":
        return float(K.MONTHS_PER_YEAR) * float(length)
    raise D.DataRefusal("R30", "internal: a window unit %r" % unit)


def _steps_per_year(cadence: Any) -> int:
    view = cadence_view(cadence)
    if view.kind == COMPOSITE_OF_YEAR:
        return int(view.composites_per_year)
    if view.unit == "month" and view.length == 1:
        return int(K.MONTHS_PER_YEAR)
    if view.unit == "year" and view.length == 1:
        return 1
    raise D.DataRefusal("R30", "the streamed test-year count reads month, year and composite steps; the target's "
                        "cadence is %s" % (cadence_identity(view),))


def _declared_reach(facts: Any, cadence: Any) -> Optional[int]:
    """A feature output's declared backward reach in target steps, rounded up, plus one: its window's
    length (max_length when the alignment is unknown) and its reach_before_max. None when the facts
    declare no bounded window."""
    w = getattr(facts, "window", None)
    if w is None:
        return None
    length = w.length if w.length is not None else getattr(w, "max_length", None)
    if length is None or w.unit is None:
        return None
    months = _months(float(length), str(w.unit))
    reach = getattr(w, "reach_before_max", None)
    if reach is not None:
        months += _months(float(reach.value), str(reach.unit))
    return int(math.ceil(months * _steps_per_year(cadence) / float(K.MONTHS_PER_YEAR))) + 1


def window_of_test_years(spec: D.PackageSpec, outputs: Mapping[str, Any], coarse_store_columns: Sequence[str],
                         lags: Mapping[str, Any], cadence: Any, test_years: Sequence[int]
                         ) -> Tuple[Optional[int], Dict[str, Any]]:
    """The first calendar year whose target rows R30's per-test-year count must read, so that every tree
    feature's lagged, last-value-filled value at every test-year row is the value a reader of whole unit
    histories gives (the rows after the test years are all read). None: no bound (every year is read).
    Per tree feature, the earliest step whose stored value can reach a test-year row (s_fill: the first
    test step minus the last-value maximum and one -- io.lastvalue fills from at most that far back and a
    longer gap is left whole, so a value further back changes no test-year row):
      static stored column        s_fill
      same-step column            s_fill - its lag (R8) - the declared reach of a feature output
      coarser column              the first step of the coarse period that serves s_fill's period (R8's
                                  lag in the column's own steps), minus a feature output's reach; a column
                                  of a coarse store (read whole, never cut) needs nothing earlier than s_fill
      feature output with no bounded declared window, or a static output of a time-varying source: None.
    The window is the calendar year holding the earliest of these. Returns (first year or None, the
    steps per column for the log)."""
    from treeroute import timing

    years = sorted(int(y) for y in test_years)
    first_test = int(timing.year_last_step(years[0] - 1, cadence)) + 1
    s_fill = first_test - int(last_value_max_steps(cadence)) - 1
    target_id = cadence_identity(cadence_view(cadence))
    coarse_store = set(coarse_store_columns)
    keys = set(spec.time_facts) | {spec.unit_col, spec.group_col}
    need: Dict[str, int] = {}
    for c in spec.tree_features:
        facts = spec.store_facts.get(c)
        kind = D._v(getattr(getattr(facts, "cadence", None), "kind", None))
        is_output = c in outputs
        if kind == "static":
            if is_output:
                for src in outputs[c].derived_from:
                    sk = D._v(getattr(getattr(spec.store_facts.get(src), "cadence", None), "kind", None))
                    if src not in keys and sk != "static":
                        return None, {"unbounded": c, "why": "a static output of the time-varying source %s" % src}
            need[c] = s_fill
            continue
        if c not in lags:
            raise D.DataRefusal("R8", "kept column %r has no lag in derived.json" % c)
        lag = lags[c]
        reach = 0
        if is_output:
            reach = _declared_reach(facts, cadence)
            if reach is None:
                return None, {"unbounded": c, "why": "a feature output without a bounded declared window"}
        if cadence_identity(cadence_view(lag.column_cadence)) == target_id:
            need[c] = s_fill - int(lag.steps) - reach
        elif c in coarse_store and not is_output:
            need[c] = s_fill
        else:
            col_cad = lag.column_cadence
            period = int(coarse_periods(np.array([s_fill], dtype=np.int64), cadence, col_cad)[0]) - int(lag.steps)
            first_day = step_bounds(np.array([period], dtype=np.int64), col_cad)[0]
            need[c] = int(step_containing(first_day, cadence)[0]) - reach
    w = min(need.values()) if need else s_fill
    first_day = int(step_bounds(np.array([w], dtype=np.int64), cadence)[0][0])
    year = _dt.date.fromordinal(first_day).year
    binding = sorted(c for c, v in need.items() if v == w)
    return year, {"first_test_step": first_test, "s_fill": s_fill, "first_step": int(w), "binding": binding[:_SHOW]}


def _add_counts(tot: Dict[str, Any], gd: Mapping[str, Any]) -> None:
    """R30's integer counts of one group added into the running sums (summed over the groups, divided once)."""
    for part in ("miss", "zero", "miss_y", "rows_y"):
        for k, v in gd[part].items():
            tot[part][k] += int(v)
    tot["seen"] += int(gd["seen"])


def _count_snapshot(st: Mapping[str, Any]) -> Dict[str, Any]:
    return {"miss": dict(st["miss"]), "rows_y": dict(st["rows_y"]), "stats": dict(st["stats"])}


def _count_delta(st: Mapping[str, Any], before: Mapping[str, Any], had_picked: bool) -> Dict[str, Any]:
    """What one group's _count_group added to the test-year count's state (its saved record)."""
    return {"miss": {k: int(st["miss"][k]) - int(before["miss"][k]) for k in st["miss"]},
            "rows_y": {y: int(st["rows_y"][y]) - int(before["rows_y"][y]) for y in st["rows_y"]},
            "stats": {k: int(st["stats"][k]) - int(before["stats"][k]) for k in st["stats"]},
            "had_picked": bool(had_picked)}


def _lag_key(lags: Mapping[str, Any]) -> str:
    """ColumnReader's cache key of a lag map."""
    return D.ColumnReader._lag_key(None, lags)


def _subset_rows(rows: Any, idx: np.ndarray) -> SimpleNamespace:
    """The given positions of target rows (census.read_units' shape), in that order."""
    return SimpleNamespace(unit_ids=np.asarray(rows.unit_ids, dtype=object)[idx],
                           group_ids=np.asarray(rows.group_ids, dtype=object)[idx],
                           time_columns={c: np.asarray(v)[idx] for c, v in rows.time_columns.items()},
                           y=np.asarray(rows.y, dtype=np.float64)[idx])


def _merge_records(records: Sequence[Any]) -> Any:
    """One last-value record (io.lastvalue.LastValueRecord) of disjoint readers' rows: every count summed (each
    is a count of rows of one column; the rule runs per unit, so a reader of several groups counts the sum)."""
    first = records[0]
    for r in records[1:]:
        if (r.max_months, r.max_steps, tuple(r.columns)) != (first.max_months, first.max_steps, tuple(first.columns)):
            raise D.DataRefusal("J2d", "internal: two groups' last-value records cover other columns or maxima")
    merged = {name: {c: int(sum(int(getattr(r, name)[c]) for r in records)) for c in first.columns}
              for name in ("missing", "filled", "gap_longer", "head", "tail")}
    return type(first)(max_months=first.max_months, max_steps=first.max_steps,
                       rows=int(sum(int(r.rows) for r in records)), units=int(sum(int(r.units) for r in records)),
                       columns=tuple(first.columns), **merged)


class GroupReaders(object):
    """The picked units' column readers, ONE GROUP AT A TIME (plan R20; module docstring). rows: every picked
    unit's target rows (census.read_units' cached picked rows); a group's reader is built on that group's rows
    (in the same order) after check_rows(its row count) passes, and is released before another group's is
    built. Collects, per lag map, each group's last-value record (last_value_record merges them), each group's
    static report-stratum values (unit_values) and one reader's store plan (data_manifest; the plan is the
    package's, the same for every group, checked at every build)."""

    def __init__(self, package: Any, spec: D.PackageSpec, rows: Any, cadence: Any, feature_hook: Any,
                 echo: Callable[[str], None], check_rows: Callable[[int], None]) -> None:
        self.package, self.spec, self.cadence, self.hook, self.echo = package, spec, cadence, feature_hook, echo
        self.check_rows = check_rows
        self._rows = rows
        codes, names = pd.factorize(pd.Series(np.asarray(rows.group_ids, dtype=object), copy=False), sort=True)
        codes = np.asarray(codes)
        if (codes < 0).any():
            raise D.DataRefusal("R1", "%d picked rows have no group" % int((codes < 0).sum()))
        order = np.argsort(codes, kind="stable")              # each group's rows in their read (census) order
        bounds = np.searchsorted(codes[order], np.arange(len(names) + 1))
        self.groups: Tuple[str, ...] = tuple(str(g) for g in names)
        self._index = {g: order[bounds[i]:bounds[i + 1]] for i, g in enumerate(self.groups)}
        self.outputs = D.feature_outputs(feature_hook) if feature_hook is not None else {}
        self._current: Optional[Tuple[str, Any]] = None
        self._last_value: Dict[str, Dict[str, Any]] = {}
        self._strata: Dict[str, Dict[str, pd.Series]] = {}
        self._manifest: Optional[Dict[str, Any]] = None
        self.strata_unread: Optional[Tuple[str, ...]] = None
        self.builds = 0
        self.loaded = 0                     # groups whose reader's records came from an R30 checkpoint (no build)

    def rows_of(self, group: str) -> int:
        return int(self._index[group].size)

    def largest(self) -> Tuple[Optional[str], int]:
        """(the group with the most picked rows, its rows): the per-group reader's peak."""
        if not self.groups:
            return None, 0
        g = max(self.groups, key=lambda x: (self.rows_of(x), x))
        return g, self.rows_of(g)

    def reader(self, group: str) -> Any:
        """The column reader of one group's picked rows (built now unless it is the one held)."""
        if self._current is not None and self._current[0] == group:
            return self._current[1]
        if group not in self._index:
            raise D.DataRefusal("R20", "internal: group %r has no picked rows" % (group,))
        self.release()
        idx = self._index[group]
        self.check_rows(int(idx.size))                    # RAM go/refuse before the group's rows are joined
        reader = D.ColumnReader(self.package, self.spec, rows_frame(_subset_rows(self._rows, idx), self.spec),
                                self.cadence, self.hook, getattr(self.echo, "file_only", self.echo))
        self.builds += 1
        plan = [(s["template"], s["columns"], s["by_step"]) for s in reader.data_manifest()["stores"]]
        if self._manifest is None:
            self._manifest = reader.data_manifest()
            self.strata_unread = tuple(reader.strata_unread)
        elif plan != [(s["template"], s["columns"], s["by_step"]) for s in self._manifest["stores"]] \
                or tuple(reader.strata_unread) != self.strata_unread:
            raise D.DataRefusal("R20", "internal: group %s's column reader read another store plan" % group)
        for c in self.spec.strata:
            facts = self.spec.store_facts.get(c)
            kind = D._v(getattr(getattr(facts, "cadence", None), "kind", None))
            if c not in reader.strata_unread and kind == "static" and reader._column_store(c) is not None:
                self._strata.setdefault(c, {})[group] = reader.unit_values(c)
        self._current = (group, reader)
        return reader

    def lagged(self, group: str, lags: Mapping[str, Any]) -> pd.DataFrame:
        """reader(group).lagged(lags), its last-value record kept for last_value_record."""
        reader = self.reader(group)
        out = reader.lagged(lags)
        self._last_value.setdefault(_lag_key(lags), {})[group] = reader.last_value_record(lags)
        return out

    def release(self) -> None:
        if self._current is not None:
            self._current = None
            import gc

            gc.collect()

    def last_value_record(self, lags: Mapping[str, Any]) -> Any:
        """The last-value record of every group's lagged frame of this lag map, merged (the whole reader's)."""
        got = self._last_value.get(_lag_key(lags), {})
        missing = [g for g in self.groups if g not in got]
        if missing:
            raise D.DataRefusal("J2d", "internal: the last-value record of a lag map asked before every group's "
                                "lagged frame was built (missing %s)" % D._fmt(missing), fix="call lagged first")
        return _merge_records([got[g] for g in self.groups])

    def data_manifest(self) -> Dict[str, Any]:
        """One group reader's data_manifest (its store plan and feature outputs; the rows, units, present rows
        and files are the census's: census_data_manifest replaces them)."""
        if self._manifest is None:
            raise D.DataRefusal("F2", "internal: no group's column reader was built yet")
        return dict(self._manifest)

    def unit_values(self, column: str) -> pd.Series:
        """ColumnReader.unit_values over every picked unit (each group's values, collected at its build)."""
        got = self._strata.get(column, {})
        missing = [g for g in self.groups if g not in got]
        if missing:
            raise D.DataRefusal("R34", "internal: report stratum %r was not read for the groups %s"
                                % (column, D._fmt(missing)))
        parts = [got[g] for g in self.groups]
        names = np.unique(np.concatenate([p.index.to_numpy(dtype=object).astype(str) for p in parts]))
        whole = pd.concat(parts)
        return whole.reindex(pd.Index(names, dtype=object)).astype(np.float64)


SEPARABILITY_RULE = ("plan R20's per-group path builds each group's feature-script outputs from that group's rows "
                     "alone; it runs only when a group's outputs (and every kept column after R8's lags and the "
                     "last-value rule) computed alone equal the values computed beside the other groups, checked "
                     "on the smoke-shaped sample (the first C13.smoke_groups groups, C13.smoke_units_per_group "
                     "picked units each by R21's stride; a smoke's whole pick)")


def check_group_separable(package: Any, spec: D.PackageSpec, rows: Any, cadence: Any, feature_hook: Any,
                          lags: Mapping[str, Any], echo: Callable[[str], None],
                          check_rows: Callable[[int], None]) -> Dict[str, Any]:
    """The separability guard of the per-group path (SEPARABILITY_RULE). rows: the picked units' rows. One
    ColumnReader on the sample's rows of every sampled group together and one per sampled group alone; every
    feature output (the script's own values) and every kept column of the lagged frame compared value for value
    (NaN equals NaN). Refuses (R20) at a difference. Returns the record (what was compared)."""
    from treeroute import split as SP

    out: Dict[str, Any] = {"rule": SEPARABILITY_RULE}
    if feature_hook is None:
        return dict(out, checked=False, reason="the package has no feature script (the engine's own reads are "
                                                "per row and per unit)")
    groups_all = sorted(set(np.asarray(rows.group_ids, dtype=object).astype(str).tolist()))
    groups = groups_all[:int(K.SMOKE_GROUPS)]
    if len(groups) < 2:
        return dict(out, checked=False, reason="one group: the per-group path is the whole path")
    units = np.asarray(rows.unit_ids, dtype=object).astype(str)
    gids = np.asarray(rows.group_ids, dtype=object).astype(str)
    picks = {g: SP.stride_pick(tuple(sorted(set(units[gids == g].tolist()))), int(K.SMOKE_UNITS_PER_GROUP))
             for g in groups}
    want = np.asarray(sorted(u for g in groups for u in picks[g]), dtype=object)
    idx = np.flatnonzero(np.isin(units, want))
    quiet = (lambda _msg: None)
    check_rows(int(idx.size))
    together = D.ColumnReader(package, spec, rows_frame(_subset_rows(rows, idx), spec), cadence, feature_hook, quiet)
    t_lag = together.lagged(lags)
    compared = 0
    outputs = sorted(together.outputs)
    for g in groups:
        gi = idx[gids[idx] == g]
        alone = D.ColumnReader(package, spec, rows_frame(_subset_rows(rows, gi), spec), cadence, feature_hook, quiet)
        a_lag = alone.lagged(lags)
        pos = together.base_rows(alone.units, alone.steps)
        pairs = [("feature output", c, together.raw[c].to_numpy(dtype=np.float64)[pos],
                  alone.raw[c].to_numpy(dtype=np.float64)) for c in outputs]
        pairs += [("kept column", c, t_lag[c].to_numpy(dtype=np.float64)[pos], a_lag[c].to_numpy(dtype=np.float64))
                  for c in alone.kept]
        for what, c, a, b in pairs:
            same = (a == b) | (np.isnan(a) & np.isnan(b))
            if not same.all():
                i = int(np.flatnonzero(~same)[0])
                raise D.DataRefusal(
                    "R20", "the feature script is not group-separable: %s %r of group %s computed from the group's "
                    "rows alone differs from its value computed beside the groups %s at %d of %d rows (e.g. unit %s "
                    "step %d: alone %r, together %r); the per-group path (plan R20) builds each group's features "
                    "alone, so it would change this package's numbers"
                    % (what, c, g, [x for x in groups if x != g], int((~same).sum()), int(same.size),
                       str(alone.units[i]), int(alone.steps[i]), float(b[i]), float(a[i])),
                    fix="make every feature output a function of its own unit's (or group's) rows (features/build.py); "
                        "nothing was computed and no run folder was opened")
            compared += int(same.size)
        del alone, a_lag
    rec = dict(out, checked=True, groups=list(groups), units_per_group={g: len(picks[g]) for g in groups},
               rows=int(idx.size), feature_outputs=outputs, kept_columns=len(together.kept), values_compared=compared,
               result="group-separable on the sample")
    echo("per-group path: the feature script is group-separable on the sample (%d groups, %d rows, %d feature outputs, "
         "%d values compared)" % (len(groups), int(idx.size), len(outputs), compared))
    return rec


class StreamedShareReader(object):
    """derive_all_streamed's column reader (module docstring). check_rows(rows) is the pipeline's RAM
    go/refuse for a reader of that many target rows (it runs before every reader is built); row_budget()
    the most target rows one unit block of the test-year count may hold (asked once per group)."""

    def __init__(self, package: Any, spec: D.PackageSpec, census: Any, cadence: Any, feature_hook: Any,
                 echo: Callable[[str], None], check_rows: Callable[[int], None],
                 row_budget: Callable[[], int], group_readers: bool = False,
                 reader_rows: Optional[Callable[[int], None]] = None,
                 sample_rows: Optional[Callable[[int], None]] = None,
                 checkpoint_step: Optional[Callable[[Mapping[str, Any]], Any]] = None) -> None:
        """group_readers (plan R20's per-group batching, the pipeline's default): measure with the picked units'
        readers built one group at a time (GroupReaders); reader_rows(rows) is the RAM go/refuse of one group's
        reader (check_rows when None), sample_rows(rows) that of the separability check's sample reader
        (reader_rows when None). False: one reader of every picked unit (the gates' whole path).
        checkpoint_step(parts): the run's R30 checkpoint step for these key parts (runs/checkpoint.py; owner ruling
        P1): the per-group path saves each group's counts as soon as the group is counted, and loads the groups a
        stopped process saved under the same key. None: no checkpoint (the gates' whole path, the tests)."""
        self.package, self.spec, self.census, self.cadence = package, spec, census, cadence
        self.hook, self.echo, self.check_rows, self.row_budget = feature_hook, echo, check_rows, row_budget
        self.per_group = bool(group_readers)
        self.checkpoint_step = checkpoint_step
        self.reader_rows = reader_rows if reader_rows is not None else check_rows
        self.sample_rows = sample_rows if sample_rows is not None else self.reader_rows
        self.group_readers: Optional["GroupReaders"] = None
        # the per-group reader builds of the GroupReaders objects an R30 measure replaced (each measure builds its own:
        # derive measures once per pass, twice when the labels before Y0 are withheld); per_group_schedule.json
        # reports them beside the last object's builds (every build reads the group's driver files)
        self.reader_builds_replaced = 0
        # the groups whose reader records those replaced objects loaded from an R30 checkpoint instead of building
        # (owner ruling P1; per_group_schedule.json discloses them beside the builds)
        self.reader_loads_replaced = 0
        self.separability: Optional[Dict[str, Any]] = None
        self._readers: Dict[Tuple[str, ...], Any] = {}
        self._test_year_cache: Dict[Tuple[str, Tuple[int, ...]], Dict[Tuple[str, int], float]] = {}
        self.test_year_source = None
        self.test_year_stats: Dict[str, Any] = {}

    def reader_for(self, units: Sequence[str]) -> Any:
        key = tuple(sorted(set(str(u) for u in units)))
        if key in self._readers:
            return self._readers[key]
        rows = self.census.read_units(key)
        self.check_rows(len(rows.unit_ids))
        reader = D.ColumnReader(self.package, self.spec, rows_frame(rows, self.spec), self.cadence, self.hook,
                                self.echo)
        self._readers = {key: reader}                 # one picked reader at a time
        return reader

    def content_epochs(self, column: str) -> Any:
        raise D.DataRefusal("R9", "column %r has a 'freeze' verdict; per-cut frozen pools are not built in the "
                            "pipeline yet" % column, fix="owner item: build per-cut pools, or ban the column")

    def measure(self, donor: Any, lags: Mapping[str, Any], test_years: Sequence[int]) -> MissingShares:
        if self.per_group:
            return self._measure_by_group(donor, lags, test_years)
        picked = self.census._picked[0] if self.census._picked is not None else ()
        donor_units = set(np.asarray(donor.unit_ids, dtype=object).tolist())
        if not donor_units <= set(picked):
            raise D.DataRefusal("R30", "the donor rows name units outside the picked units read again",
                                fix="internal: measure after derive reads the picked units")
        reader = self.reader_for(picked)
        shares = reader.measure(donor, lags, test_years)
        if len(reader.units) == int(self.census.rows):
            self.test_year_source = "the picked reader (every census row is a picked row)"
            return shares
        key = (reader._lag_key(lags), tuple(int(y) for y in test_years))
        if key in self._test_year_cache:
            self.test_year_source = "the count already made for this lag map and these test years (same rows)"
        else:
            self._test_year_cache[key] = self._test_year_shares(lags, test_years)
            self.test_year_source = "streamed over every census row of the test years, group by group in unit blocks"
        return MissingShares(donor_row_key_hash=shares.donor_row_key_hash, donor_unit_scope=shares.donor_unit_scope,
                             donor_training_missing_share=shares.donor_training_missing_share,
                             donor_training_zero_share=shares.donor_training_zero_share,
                             test_year_missing_share=dict(self._test_year_cache[key]))

    # ------------------------------------------------------------------ the per-test-year count
    def _window(self, lags: Mapping[str, Any], years: Sequence[int]) -> Tuple[Optional[int], Dict[str, Any]]:
        """(the first census coordinate the count reads, or None for every row; the window's facts)."""
        presence = self.census.presence
        outputs = getattr(presence, "outputs", None) or (D.feature_outputs(self.hook) if self.hook is not None else {})
        coarse = [c for p in getattr(presence, "plan", ()) if not p.by_step for c in p.columns]
        first_year, info = window_of_test_years(self.spec, outputs, coarse, lags, self.cadence, years)
        if first_year is None:
            return None, info
        coord = first_year * K.MONTHS_PER_YEAR if self.census.line == "month" else first_year
        info = dict(info, first_year=int(first_year))
        if coord <= int(self.census.coords.min()):
            return None, info
        return int(coord), info

    def _driver_file_keep(self, min_coord: Optional[int]) -> Optional[Callable[[str, bool, str], bool]]:
        """ColumnReader's driver_file_keep for a reader of the rows from min_coord on: a file of a store keyed
        like the target whose rows (the census presence pass's file_coords) all lie before min_coord is
        skipped; a coarse store's files are always read (a lag reaches back by whole coarse periods)."""
        if min_coord is None:
            return None
        spans = getattr(self.census.presence, "file_coords", None) or {}

        def keep(template: str, by_step: bool, path: str) -> bool:
            if not by_step:
                return True
            span = spans.get(str(path))
            return span is None or span[1] >= min_coord
        return keep

    def _check_block(self, block: Any, lagged: pd.DataFrame, lags: Mapping[str, Any], years: Sequence[int],
                     picked: Any) -> int:
        """The window's check: each picked unit of the block, at its test-year rows, holds the picked
        reader's (whole histories) lagged tree features, value for value (NaN where it holds NaN).
        Refuses a difference. Returns the rows compared."""
        if picked is None:
            return 0
        units = np.asarray(block.units, dtype=object).astype(str)
        sel = np.flatnonzero(np.isin(units, picked.unit_names) & np.isin(block.years, np.asarray(years)))
        if not sel.size:
            return 0
        pos = picked.base_rows(units[sel], block.steps[sel])
        whole = picked.lagged(lags)
        for c in self.spec.tree_features:
            a = lagged[c].to_numpy(dtype=np.float64)[sel]
            b = whole[c].to_numpy(dtype=np.float64)[pos]
            same = (a == b) | (np.isnan(a) & np.isnan(b))
            if not same.all():
                i = int(np.flatnonzero(~same)[0])
                raise D.DataRefusal(
                    "R30", "the test-year window changes tree feature %r at %d test-year rows of picked units, e.g. "
                    "unit %s step %d (whole history %r, window %r): a lag, a feature output or the last-value rule "
                    "reads further back than R8's lags and the declared windows say"
                    % (c, int((~same).sum()), units[sel][i], int(block.steps[sel][i]), float(b[i]), float(a[i])),
                    fix="declare the feature script's true backward window (its OUTPUTS facts), or report the "
                        "column's reach; the run cannot count R30's test-year shares from the window")
        return int(sel.size)

    def _test_year_shares(self, lags: Mapping[str, Any], test_years: Sequence[int]) -> Dict[Tuple[str, int], float]:
        st = self._count_setup(lags, test_years)
        picked = next(iter(self._readers.values())) if self._readers else None
        for g in self.census.groups:
            self._count_group(st, g, picked)
        return self._count_finish(st)

    def _count_setup(self, lags: Mapping[str, Any], test_years: Sequence[int]) -> Dict[str, Any]:
        """The per-test-year count's state before its group walk (the window, the units with a test-year row,
        each unit's rows from the window on, the counters)."""
        census = self.census
        years = [int(y) for y in test_years]
        trees = list(self.spec.tree_features)
        min_coord, info = self._window(lags, years)
        # the units with a row in a test year (a unit without one adds nothing to any count)
        cyears = census.coords // K.MONTHS_PER_YEAR if census.line == "month" else census.coords
        tcm = np.isin(cyears, np.asarray(years, dtype=np.int64))
        has_test = np.zeros(census.n_units(), dtype=bool)
        if tcm.any():
            for a, b in census.unit_blocks():
                has_test[a:b] = census.bits("exist", a, b, tcm).any(axis=1)
        group_code, group_names = pd.factorize(pd.Series(census.unit_group, copy=False), sort=False)
        return {"t0": time.time(), "lags": lags, "years": years, "trees": trees,
                "miss": {(c, y): 0 for c in trees for y in years}, "rows_y": {y: 0 for y in years},
                "min_coord": min_coord, "info": info, "keep": self._driver_file_keep(min_coord), "has_test": has_test,
                "window_rows": census.rows_from(np.arange(census.n_units(), dtype=np.int64), min_coord),
                "group_code": np.asarray(group_code), "group_names": np.asarray(group_names, dtype=object),
                "had_picked": False,
                "stats": {"blocks": 0, "units": 0, "rows_read": 0, "target_files_read": 0, "driver_files_read": 0,
                          "checked_rows": 0}}

    def _count_group(self, st: Dict[str, Any], g: str, picked: Any) -> None:
        """One group's unit blocks of the per-test-year count, each block checked against `picked` (the picked
        units' reader holding this group's picked units: the whole picked reader, or the group's own)."""
        census = self.census
        lags, years, trees, stats = st["lags"], st["years"], st["trees"], st["stats"]
        st["had_picked"] = st["had_picked"] or picked is not None
        quiet = (lambda _msg: None)
        gi = int(np.flatnonzero(st["group_names"] == g)[0])
        codes = np.flatnonzero((st["group_code"] == gi) & st["has_test"])
        window_rows = st["window_rows"]
        budget = max(1, int(self.row_budget()))             # asked again per group (the RAM free now)
        a = blocks = 0
        while a < len(codes):
            b, total = a, 0
            while b < len(codes) and (b == a or total + int(window_rows[codes[b]]) <= budget):
                total += int(window_rows[codes[b]])
                b += 1
            self.check_rows(total)                          # RAM go/refuse before the block is read
            rows = census.read_units(census.unit_names[codes[a:b]], cache=False, min_coord=st["min_coord"],
                                     labels=False)
            stats["target_files_read"] += int(getattr(census, "last_read_files", 0))
            reader = D.ColumnReader(self.package, self.spec, rows_frame(rows, self.spec), self.cadence,
                                    self.hook, quiet, driver_file_keep=st["keep"])
            lagged = reader.lagged(lags)
            for y in years:
                idx = np.flatnonzero(reader.years == y)
                st["rows_y"][y] += int(idx.size)
                for c in trees:
                    st["miss"][(c, y)] += int(np.isnan(lagged[c].to_numpy(dtype=np.float64)[idx]).sum())
            stats["checked_rows"] += self._check_block(reader, lagged, lags, years, picked)
            stats["rows_read"] += int(len(rows.unit_ids))
            stats["driver_files_read"] += len(reader.files_read)
            blocks += 1
            del reader, lagged, rows
            a = b
        stats["blocks"] += blocks
        stats["units"] += int(len(codes))
        self.echo("R30 test-year shares: group %s counted (%d units with a test-year row, %d blocks)"
                  % (g, len(codes), blocks))

    def _count_finish(self, st: Dict[str, Any]) -> Dict[Tuple[str, int], float]:
        stats, min_coord = st["stats"], st["min_coord"]
        if min_coord is not None and st["had_picked"] and not stats["checked_rows"]:
            raise D.DataRefusal("R30", "no picked unit holds a test-year row, so the test-year window was checked "
                                "against nothing", fix="internal: check the picked units")
        self.test_year_stats = dict(st["info"], min_coord=min_coord, seconds=round(time.time() - st["t0"], 1),
                                    **stats)
        self.echo("R30 test-year shares: %s" % (self.test_year_stats,))
        out: Dict[Tuple[str, int], float] = {}
        for c in st["trees"]:
            for y in st["years"]:
                if st["rows_y"][y]:
                    out[(c, y)] = float(st["miss"][(c, y)]) / float(st["rows_y"][y])
        return out

    # ------------------------------------------------------------------ R30's per-group checkpoints (owner ruling P1)
    def _load_group(self, step: Any, g: str, readers: "GroupReaders", lags: Mapping[str, Any],
                    st: Optional[Dict[str, Any]], tot: Dict[str, Any]) -> bool:
        """Apply group g's saved record (its counts into tot and st; what its column reader left behind into
        readers). False when the group has no usable record (it is counted now)."""
        name = record_name("group", g)
        got = step.load_object(name)
        if got is None:
            return False
        _, obj = got
        if obj.get("group") != g or (st is not None) != (obj.get("count") is not None) \
                or (obj.get("reader") is None) != (g not in readers.groups):
            step.quarantine(name, "it holds group %r with %s, not the counts this pass makes for group %r"
                            % (obj.get("group"), "a test-year count" if obj.get("count") is not None
                               else "no test-year count", g))
            return False
        r = obj["reader"]
        if r is not None:
            readers._last_value.setdefault(_lag_key(lags), {})[g] = r["last_value"]
            for c, values in r["strata"].items():
                readers._strata.setdefault(c, {})[g] = values
            if readers._manifest is None:
                readers._manifest = dict(r["manifest"])
                readers.strata_unread = tuple(r["strata_unread"])
            readers.loaded += 1
        _add_counts(tot, obj["donor"])
        c = obj["count"]
        if st is not None:
            for k, v in c["miss"].items():
                st["miss"][k] += int(v)
            for y, v in c["rows_y"].items():
                st["rows_y"][y] += int(v)
            for k, v in c["stats"].items():
                st["stats"][k] += int(v)
            st["had_picked"] = st["had_picked"] or bool(c["had_picked"])
            self.echo("R30 test-year shares: group %s loaded from checkpoint (%d units with a test-year row, %d blocks)"
                      % (g, int(c["stats"]["units"]), int(c["stats"]["blocks"])))
        else:
            self.echo("R30 shares: group %s loaded from checkpoint" % g)
        return True

    # ------------------------------------------------------------------ plan R20: one group's reader at a time
    def _measure_by_group(self, donor: Any, lags: Mapping[str, Any], test_years: Sequence[int]) -> MissingShares:
        """measure() with the picked units' readers built one group at a time (GroupReaders; module docstring):
        the same shares, from integer counts summed over the groups and divided once."""
        census = self.census
        if census._picked is None:
            raise D.DataRefusal("R30", "internal: R30 is measured before the picked units' rows are read",
                                fix="internal: measure after derive reads the picked units")
        picked, rows = census._picked
        donor_u = np.asarray(donor.unit_ids, dtype=object)
        if not set(donor_u.tolist()) <= set(picked):
            raise D.DataRefusal("R30", "the donor rows name units outside the picked units read again",
                                fix="internal: measure after derive reads the picked units")
        readers = GroupReaders(self.package, self.spec, rows, self.cadence, self.hook, self.echo, self.reader_rows)
        if self.group_readers is not None:
            self.reader_builds_replaced += int(self.group_readers.builds)
            self.reader_loads_replaced += int(self.group_readers.loaded)
        self.group_readers = readers
        if self.separability is None:
            self.separability = check_group_separable(self.package, self.spec, rows, self.cadence, self.hook, lags,
                                                      self.echo, self.sample_rows)
        trees = list(self.spec.tree_features)
        years = [int(y) for y in test_years]
        all_picked = int(len(rows.unit_ids)) == int(census.rows)
        key = (_lag_key(lags), tuple(years))
        st = self._count_setup(lags, years) if not all_picked and key not in self._test_year_cache else None
        uniq, inv = np.unique(donor_u.astype(str), return_inverse=True)
        unit_group = np.asarray([census.unit_group[census._code_of[u]] for u in uniq.tolist()], dtype=object)
        donor_g = unit_group[np.asarray(inv).reshape(-1)] if uniq.size else np.zeros(0, dtype=object)
        donor_t = np.asarray(donor.times)
        tot = {"miss": {c: 0 for c in trees}, "zero": {c: 0 for c in trees},
               "miss_y": {(c, y): 0 for c in trees for y in years}, "rows_y": {y: 0 for y in years}, "seen": 0}
        stray = sorted(set(readers.groups) - set(census.groups))
        if stray:
            raise D.DataRefusal("R30", "internal: picked groups %s are not census groups" % stray[:5])
        step = None
        if self.checkpoint_step is not None:
            # owner ruling P1: one record per group, keyed by what the group's counts read (the census's inputs come
            # with the step's base parts; here the lag map, the test years, the donor rows and the picked units)
            step = self.checkpoint_step({
                "lag_key": _lag_key(lags), "test_years": years, "donor_row_key_hash": str(donor.row_key_hash),
                "donor_unit_scope": str(donor.unit_scope), "all_picked": bool(all_picked),
                "count_part": st is not None,
                "picked_units_sha256": hashlib.sha256(json.dumps(list(picked), ensure_ascii=False).encode("utf-8"))
                .hexdigest()})
        loaded = 0
        for g in census.groups:
            if step is not None and self._load_group(step, g, readers, lags, st, tot):
                loaded += 1
                continue
            reader = readers.reader(g) if g in readers.groups else None
            gd = {"miss": {c: 0 for c in trees}, "zero": {c: 0 for c in trees},
                  "miss_y": {(c, y): 0 for c in trees for y in years}, "rows_y": {y: 0 for y in years}, "seen": 0}
            if reader is not None:
                lagged = readers.lagged(g, lags)
                sel = np.flatnonzero(donor_g == g)
                if sel.size:
                    pos = reader.base_rows(donor_u[sel], donor_t[sel])
                    for c in trees:
                        d = lagged[c].to_numpy(dtype=np.float64)[pos]
                        gd["miss"][c] += int(np.isnan(d).sum())
                        gd["zero"][c] += int((d == 0).sum())
                    gd["seen"] += int(sel.size)
                if all_picked:
                    for y in years:
                        idx = np.flatnonzero(reader.years == y)
                        gd["rows_y"][y] += int(idx.size)
                        for c in trees:
                            gd["miss_y"][(c, y)] += int(np.isnan(lagged[c].to_numpy(dtype=np.float64)[idx]).sum())
                del lagged
            count = None
            if st is not None:
                before = _count_snapshot(st)
                self._count_group(st, g, reader)
                count = _count_delta(st, before, reader is not None)
            _add_counts(tot, gd)
            if step is not None:
                step.save_object(record_name("group", g), {
                    "group": g, "donor": gd, "count": count,
                    "reader": None if reader is None else {
                        "last_value": readers._last_value[_lag_key(lags)][g],
                        "strata": {c: v[g] for c, v in readers._strata.items() if g in v},
                        "manifest": reader.data_manifest(), "strata_unread": tuple(reader.strata_unread)}},
                    {"group": g})
        if step is not None:
            self.echo("checkpoint: R30: %d of %d groups loaded from checkpoint, %d counted and saved (%s key %s)"
                      % (loaded, len(census.groups), len(census.groups) - loaded, step.name, step.key[:16]))
        miss, zero, miss_y, rows_y, seen = tot["miss"], tot["zero"], tot["miss_y"], tot["rows_y"], tot["seen"]
        readers.release()
        n = int(donor_u.size)
        if seen != n:
            raise D.DataRefusal("R30", "internal: %d of %d donor rows lie in no picked group" % (n - seen, n))
        miss_s = {c: (float(miss[c]) / float(n) if n else 0.0) for c in trees}
        zero_s = {c: (float(zero[c]) / float(n) if n else 0.0) for c in trees}
        if all_picked:
            self.test_year_source = "the picked reader (every census row is a picked row)"
            by_year = {(c, y): float(miss_y[(c, y)]) / float(rows_y[y]) for c in trees for y in years if rows_y[y]}
        else:
            if st is not None:
                self._test_year_cache[key] = self._count_finish(st)
                self.test_year_source = "streamed over every census row of the test years, group by group in unit blocks"
            else:
                self.test_year_source = "the count already made for this lag map and these test years (same rows)"
            by_year = dict(self._test_year_cache[key])
        return MissingShares(donor_row_key_hash=donor.row_key_hash, donor_unit_scope=donor.unit_scope,
                             donor_training_missing_share=miss_s, donor_training_zero_share=zero_s,
                             test_year_missing_share=by_year)


__all__ = ["TargetFileSource", "PresenceReader", "StreamedShareReader", "GroupReaders", "check_group_separable",
           "SEPARABILITY_RULE", "rows_frame", "census_data_manifest", "window_of_test_years", "KEY_SHIFT"]
