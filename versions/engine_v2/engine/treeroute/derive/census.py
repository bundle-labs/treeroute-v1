"""The streaming target census, and derive_all over it (plan 4.1 steps 1-2 at full size).

WHY. derive_all (orchestrate.py) takes the target table whole: one row object per (unit, step), every
label in memory. The largest packages hold several hundred million target rows, beyond this machine's
memory. This module reads the target store FILE BY FILE and keeps only what the derive rules read, then
runs the same rules in the same order. RULES DO NOT CHANGE: only how the data is read. Every derived
value and every hash is byte-identical to derive_all's on the same table (tests/test_census.py checks
it against derive_all; the draft smokes check it end to end).

What one pass keeps (scan_target), never the whole census:
  - the unit list (first-appearance order, the order pd.factorize gives derive_all) with each unit's
    group and row count;
  - two bit matrices over (calendar coordinate x unit): the row EXISTS, its label is VALID. A month
    line holds 24 years in 36 bytes per unit. Every validity count derive_all makes (R3's joined rows,
    the candidates, R12's inner counts, the fit-row windows, the donor row keys) is a popcount over a
    window of these bits;
  - per (group, year, driver-presence mask): the number of valid rows, and per (group, mask) the first
    year with a row and the number of rows: R3's joined rows (F2), R4's driver-store first years (J5),
    and each store's present rows for the data manifest (present_rows);
  - per coordinate, a 2^16-bin histogram of the valid labels (their sortable bit keys): R18's event
    rate is found from it exactly (an exact radix select: one more pass collects the one or two bins
    that hold the 90th percentile's neighbours; it skips the files that hold no usable coordinate).
    A zero label is keyed as +0.0 (-0.0 == 0.0: numpy's comparisons do not tell them apart, so the
    event count is numpy's; event_rate puts back numpy's sign of a zero q90 when the zeros hold one sign);
  - per target file, the first and last calendar coordinate it holds (file_coords): a later read that
    needs only the rows from a coordinate on skips the files that end before it;
  - R1's input hashes (the unit ids and time columns in row order), streamed into SHA-256.
Memory: one file plus the per-unit counters (census_ram_bytes gives the estimate the pre-flight uses).

What is read again, later, by unit (read_units): the full label rows of the PICKED units only (the
bank units, which hold every scored unit), after the picks: the plan-time label reader
(orchestrate._PlanLabels, reused as it is) is built on them, and the run's vault on the bank units' rows.
row_guard (the pipeline's RAM go/refuse of the picked working set) is called with their row count, from
the census's own counts, before any of their rows is read. R30's per-test-year missing share
(pipeline/stream.py) reads the rows of every census unit with a test-year row again, from a first
coordinate on (read_units with min_coord, labels=False): the target files are read from disk again there
(the target reader returns the label with the row), and read_units drops every label (NaN) before the
rows leave it, so a label read there reaches no reader, no derived value and no vault.

R1 at scale. derive_r01_cadence reads every row; on a month or year time line its outcome depends only
on each unit's set of gaps between consecutive rows (and the row count and the hashes). census.r01
calls the SAME rule on a reduced table that keeps every unit and each unit's first coordinate and one
gap of each size it shows, then puts back the true row count and the streamed hashes. A calendar with a
date or day_of_year column (a day time line, composites) is refused by the streamed census (not built).

derive_all_streamed mirrors derive_all line by line (orchestrate.py is the reference; it is not edited
here) and reuses its helpers (_Facts, _PlanLabels, _r04_entry, _region_fit, _fallback_rows,
_check_r23_plan_time, _check_epoch_columns, _non_tree_columns). The drivers' row presence (F2) comes
from a presence source evaluated file by file during the scan (pipeline.data.PresenceReader), not from
share_reader.drivers_present over the whole table. R30's shares still come from share_reader.measure.
"""
# Provenance: plan 4.1 steps 1-2, 5 G-DISK; the owner item "a streaming vault and derive (a
# validity-only census for the derived rules, full rows only for the bank units)".

import hashlib
import json
import time
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from treeroute import engine_constants as K
from treeroute import split as _split
from treeroute import timing
from treeroute.io import steps as _steps

from . import orchestrate as O
from . import router_rules as RR
from . import rules as R
from . import unit_rules as UR
from .derived import DeriveRefusal, make_derived, sha256_of_json
from .shapes import CutKind, Link, RouterKind

HIST_BITS = 16                         # top bits of a label's sortable key per histogram bin
COLLECT_CAP = 16_000_000               # labels held at once by the exact-quantile collect pass
UNIT_BLOCK = 1 << 13                   # units per block when the bit matrices are read
EVENT_RATE_SOURCE = "donor_event_rate over the label-only donor view"   # derive_r18_scored_count's text
MONTH, YEAR = "month", "year"
_SHOW = 5


# ---------------------------------------------------------------------------------------------------
# Shapes
class FileRows(SimpleNamespace):
    """One target file's rows: unit_ids and group_ids (object arrays of str), time_columns {column:
    int64 array}, y (float64, NaN = invalid label)."""


class TableSource(object):
    """A target table already in memory, served in row blocks as if each block were one file (tests;
    any caller whose table fits). Rows keep the table's order."""

    def __init__(self, target: Any, rows_per_file: int) -> None:
        self._units = np.asarray(target.unit_ids, dtype=object)
        self._groups = np.asarray(target.group_ids, dtype=object)
        self._times = {c: np.asarray(v, dtype=np.int64) for c, v in target.time_columns.items()}
        self._y = np.asarray(target.y, dtype=np.float64)
        n = len(self._units)
        step = max(1, int(rows_per_file))
        self.files = [(a, min(a + step, n)) for a in range(0, n, step)]

    def expected_rows(self) -> int:
        return int(len(self._units))

    def file_groups(self, handle: Any) -> Optional[Tuple[str, ...]]:
        a, b = handle
        return tuple(sorted(set(self._groups[a:b].tolist())))

    def read(self, handle: Any) -> FileRows:
        a, b = handle
        return FileRows(unit_ids=self._units[a:b], group_ids=self._groups[a:b],
                        time_columns={c: v[a:b] for c, v in self._times.items()}, y=self._y[a:b])


class ReaderPresence(object):
    """A presence source from a derive_all column reader whose drivers_present answers any rows (tests:
    a synthetic reader). One store; its bit is drivers_present over every column."""

    def __init__(self, reader: Any, columns: Sequence[str] = ()) -> None:
        self._reader = reader
        self._columns = tuple(columns)
        self.stores = ("reader",)
        self.absent = (frozenset(),)

    def stores_for(self, columns: Sequence[str]) -> Tuple[int, ...]:
        return (0,)

    def masks(self, rows: FileRows) -> np.ndarray:
        held = np.asarray(self._reader.drivers_present(rows.unit_ids, rows.group_ids, rows.time_columns,
                                                       self._columns))
        if held.shape != np.asarray(rows.unit_ids).shape or held.dtype.kind != "b":
            raise DeriveRefusal("R3", "drivers_present must give one boolean per target row, got %s %s"
                                % (held.dtype, held.shape), fix="the column reader answers per row")
        return held.astype(np.uint32)


# ---------------------------------------------------------------------------------------------------
# Streamed array hashes (derived.sha256_of_array, fed in chunks; the length is known first)
class _ArrayHash(object):
    """SHA-256 of a 1-D array exactly as derived.sha256_of_array hashes it, fed in chunks. kind 'text'
    hashes the JSON list of the values' text (an object array of str); kind 'int64' the raw bytes.
    resumable: the digest runs on runs.checkpoint.ResumableSha256 (the same SHA-256, its state saved as bytes
    by export and put back by restore: the census checkpoints, owner ruling P1); else on hashlib."""

    def __init__(self, n: int, kind: str, resumable: bool = False) -> None:
        self.n, self.kind, self.seen = int(n), kind, 0
        self.resumable = bool(resumable)
        if self.resumable:
            from treeroute.runs.checkpoint import ResumableSha256

            self._h = ResumableSha256()
        else:
            self._h = hashlib.sha256()
        dtype = "|O" if kind == "text" else np.dtype(np.int64).str
        self._h.update(("%s|%s|" % (dtype, (self.n,))).encode("ascii"))
        self._open = False

    def export(self) -> Dict[str, Any]:
        """The hash's whole state (JSON-ready): the declared length, the values fed, the open list, the SHA-256
        state bytes (hex)."""
        if not self.resumable:
            raise DeriveRefusal("P1", "internal: a hashlib digest has no state to save", fix="internal")
        return {"n": self.n, "kind": self.kind, "seen": self.seen, "open": self._open, "state": self._h.state().hex()}

    def restore(self, state: Mapping[str, Any]) -> None:
        from treeroute.runs.checkpoint import ResumableSha256

        if (int(state["n"]), str(state["kind"])) != (self.n, self.kind) or not self.resumable:
            raise CensusCheckpointMismatch("a saved hash state is for %s values of kind %s, this census hashes %d of "
                                           "kind %s" % (state["n"], state["kind"], self.n, self.kind))
        self._h = ResumableSha256.from_state(bytes.fromhex(str(state["state"])))
        self.seen, self._open = int(state["seen"]), bool(state["open"])

    def update(self, values: Any) -> None:
        if self.kind == "text":
            arr = np.asarray(values, dtype=object)
            if arr.size == 0:
                return
            body = json.dumps([v if isinstance(v, str) else repr(v) for v in arr.tolist()],
                              ensure_ascii=False, separators=(",", ":"))[1:-1]
            self._h.update((("," if self._open else "[") + body).encode("utf-8"))
            self._open = True
        else:
            arr = np.ascontiguousarray(np.asarray(values, dtype=np.int64))
            self._h.update(arr.tobytes())
        self.seen += int(np.asarray(values).size)

    def hexdigest(self) -> str:
        if self.seen != self.n:
            raise DeriveRefusal("R1", "internal: a streamed hash was fed %d values for a declared %d"
                                % (self.seen, self.n), fix="internal")
        h = self._h.copy()
        if self.kind == "text":
            h.update(b"]" if self._open else b"[]")
        return h.hexdigest()


class CensusCheckpointMismatch(Exception):
    """A census checkpoint record does not continue the census state replayed so far (never trusted: the
    replay restarts without it: CensusCheckpoint)."""


def sortable_keys(y: np.ndarray) -> np.ndarray:
    """uint64 keys whose order is the order of the float64 values (finite values; -0.0 just below 0.0)."""
    bits = np.ascontiguousarray(np.asarray(y, dtype=np.float64)).view(np.uint64)
    neg = (bits >> np.uint64(63)) == 1
    return np.where(neg, ~bits, bits | np.uint64(1 << 63))


def _linear_percentile(prev: float, nxt: float, n: int, pct: float) -> float:
    """np.percentile(a, pct) (method 'linear') from the two order statistics it interpolates: the same
    float64 operations numpy 2 performs (q = pct / 100; virtual index (n - 1) q; at or above the last
    index numpy's _get_indexes takes the last value with previous index -1, so gamma = virtual + 1;
    numpy's _lerp). The sign of a zero result follows numpy's too."""
    q = np.asanyarray(np.true_divide(pct, np.float64(100)))
    virtual = np.asanyarray((n - 1) * q)
    below = np.asanyarray(np.floor(virtual))
    if virtual >= n - 1:
        below = np.asanyarray(np.float64(-1))
    gamma = np.asanyarray(virtual - below, dtype=virtual.dtype)
    a, b = np.float64(prev), np.float64(nxt)
    diff = np.subtract(b, a)
    out = np.asanyarray(np.add(a, diff * gamma))
    if gamma >= 0.5:
        out = np.asanyarray(np.subtract(b, diff * (1 - gamma)))
    return float(out[()] if out.ndim == 0 else out)


def percentile_ranks(n: int, pct: float) -> Tuple[int, int]:
    """The 0-based ranks np.percentile (linear) interpolates between, for n values."""
    q = np.asanyarray(np.true_divide(pct, np.float64(100)))
    virtual = (n - 1) * q
    if virtual >= n - 1:
        return n - 1, n - 1
    if virtual < 0:
        return 0, 0
    lo = int(np.floor(virtual))
    return lo, lo + 1


# ---------------------------------------------------------------------------------------------------
# The census
class TargetCensus(object):
    """What one streaming pass over the target store keeps (see the module docstring). Built by
    scan_target; read by derive_all_streamed and by the pipeline (read_units)."""

    def __init__(self, source: Any, time_facts: Mapping[str, Any], presence: Any, expected_rows: int,
                 resumable: bool = False) -> None:
        """resumable: R1's hashes run on the resumable SHA-256, so the census can be checkpointed (scan_target
        with a checkpoint step; owner ruling P1). The digests are the same either way."""
        self.source = source
        self.time_facts = dict(time_facts)
        day_parts = sorted(c for c, f in self.time_facts.items()
                           if getattr(f, "value", f) in (_steps.DATE, _steps.DAY_OF_YEAR))
        if day_parts:
            raise DeriveRefusal("R1", "the streamed census reads year and year + month calendars; this target "
                                "has the day-line time column(s) %s" % day_parts,
                                fix="owner item: build the streamed R1 for day time lines (composites), or "
                                    "run a table that fits in memory through derive_all")
        self.presence = presence
        self.n_stores = len(presence.stores) if presence is not None else 0
        if self.n_stores > 31:
            raise DeriveRefusal("R3", "%d driver stores: the census presence mask holds 31" % self.n_stores,
                                fix="owner item: widen the presence mask")
        self.rows = 0
        self.line: Optional[str] = None
        self.column_of: Dict[str, str] = {}
        self._code_of: Dict[str, int] = {}
        self._names: List[str] = []
        self._group_of: List[str] = []
        self._unit_rows: List[int] = []
        self._rows_grow = np.zeros(0, dtype=np.int64)
        self.groups_seen: List[str] = []
        self._cap = 0                                  # bytes per coordinate row of the bit matrices
        self._exist: Dict[int, np.ndarray] = {}
        self._valid: Dict[int, np.ndarray] = {}
        self._hist: Dict[int, np.ndarray] = {}
        self.mask_valid: Dict[Tuple[str, int, int], int] = {}
        self.mask_rows: Dict[Tuple[str, int], int] = {}
        self.mask_first_year: Dict[Tuple[str, int], int] = {}
        self.row_guard: Optional[Callable[[int], None]] = None     # RAM go/refuse before picked rows are read
        self._h_units = _ArrayHash(expected_rows, "text", resumable)
        self._h_times = {c: _ArrayHash(expected_rows, "int64", resumable) for c in sorted(self.time_facts)}
        # what the files added since the last checkpoint touched (checkpoint_delta): unit codes, coordinates, groups
        self._ck_names = 0
        self._ck_lo: Optional[int] = None
        self._ck_hi: Optional[int] = None
        self._ck_coords: set = set()
        self._ck_groups: set = set()
        self._picked: Optional[Tuple[Tuple[str, ...], Any]] = None
        self.file_coords: Optional[List[Optional[Tuple[int, int]]]] = None   # per source file (scan_target)
        self._r1 = None
        self._views: Dict[Any, Any] = {}

    # ------------------------------------------------------------------ the scan
    def _calendar_coord(self, time_columns: Mapping[str, np.ndarray]) -> np.ndarray:
        _, parts, column_of = _steps._calendar(time_columns, self.time_facts)
        if _steps.DATE in column_of or _steps.DAY_OF_YEAR in column_of:
            raise DeriveRefusal("R1", "the streamed census reads year and year + month calendars; this target "
                                "has a %s column (a day time line)" % ("date" if _steps.DATE in column_of
                                                                      else "day_of_year"),
                                fix="owner item: build the streamed R1 for day time lines (composites), or "
                                    "run a table that fits in memory through derive_all")
        if _steps.MONTH in column_of and _steps.YEAR not in column_of:
            raise DeriveRefusal("R1", "a month column needs a year column (or a date column)",
                                fix="declare the year's key_time column")
        if _steps.YEAR not in column_of:
            raise DeriveRefusal("R1", "the calendar has no year column", fix="declare the year's key_time column")
        line = MONTH if _steps.MONTH in column_of else YEAR
        if self.line is None:
            self.line, self.column_of = line, dict(column_of)
        if line == MONTH:
            return np.asarray(parts[_steps.YEAR] * K.MONTHS_PER_YEAR + parts[_steps.MONTH] - 1, dtype=np.int64)
        return np.asarray(parts[_steps.YEAR], dtype=np.int64)

    def _codes(self, units: np.ndarray, groups: np.ndarray) -> np.ndarray:
        bad = [g for g in pd.unique(groups) if not isinstance(g, str) or not g]
        if bad:
            raise DeriveRefusal("R1", "group ids must be non-empty names, got %r" % (bad[:_SHOW],),
                                fix="pass the key_group column")
        local, uniq = pd.factorize(pd.Series(units, copy=False), sort=False)
        local = np.asarray(local)
        if (local < 0).any():
            raise DeriveRefusal("R1", "%d rows have no unit id" % int((local < 0).sum()),
                                fix="every target row needs its unit id (plan 1.2)")
        pairs = pd.DataFrame({"u": local, "g": groups}).drop_duplicates("u")
        if len(pd.DataFrame({"u": local, "g": groups}).drop_duplicates()) != len(pairs):
            raise DeriveRefusal("G-DISJOINT", "units belong to more than one group within one file",
                                fix="a unit belongs to one group (unit ids carry their group, plan 1.2)")
        group_of_local = pairs.set_index("u")["g"].reindex(np.arange(len(uniq))).to_numpy(dtype=object)
        out = np.empty(len(uniq), dtype=np.int64)
        twice = []
        for i, u in enumerate(uniq.tolist()):
            code = self._code_of.get(u)
            g = group_of_local[i]
            if code is None:
                code = len(self._names)
                self._code_of[u] = code
                self._names.append(u)
                self._group_of.append(g)
                if g not in self.groups_seen:
                    self.groups_seen.append(g)
            elif self._group_of[code] != g:
                twice.append(u)
            out[i] = code
        if twice:
            raise DeriveRefusal("G-DISJOINT", "%d units belong to more than one group, e.g. %s"
                                % (len(twice), twice[:_SHOW]),
                                fix="a unit belongs to one group (unit ids carry their group, plan 1.2)")
        return out[local]

    def _grow(self) -> None:
        need = (len(self._names) + 7) // 8
        if need <= self._cap:
            return
        cap = max(need, 2 * self._cap, 64)
        for store in (self._exist, self._valid):
            for c in list(store):
                grown = np.zeros(cap, dtype=np.uint8)
                grown[:self._cap] = store[c]
                store[c] = grown
        self._cap = cap

    def _row(self, store: Dict[int, np.ndarray], coord: int) -> np.ndarray:
        row = store.get(coord)
        if row is None:
            row = np.zeros(self._cap, dtype=np.uint8)
            store[coord] = row
        return row

    def add(self, rows: FileRows) -> Optional[Tuple[int, int]]:
        """Counts one file's rows into the census; returns the first and last calendar coordinate the file
        holds (None for a file without rows)."""
        units = np.asarray(rows.unit_ids, dtype=object)
        n = len(units)
        if n == 0:
            return None
        groups = np.asarray(rows.group_ids, dtype=object)
        times = {c: _steps.as_int_array(rows.time_columns[c], "time column %s" % c) for c in rows.time_columns}
        y = np.asarray(rows.y)
        if y.ndim != 1 or len(y) != n or y.dtype.kind not in "iuf" or groups.shape != units.shape:
            raise DeriveRefusal("G-LOCK", "target y must be one number per target row, got %s %s"
                                % (y.dtype, y.shape), fix="pass the target table as read")
        coord = self._calendar_coord(times)
        codes = self._codes(units, groups)
        self._grow()
        lo, hi = int(codes.min()), int(codes.max()) + 1
        self._ck_lo = lo if self._ck_lo is None else min(self._ck_lo, lo)
        self._ck_hi = hi if self._ck_hi is None else max(self._ck_hi, hi)
        self._ck_coords.update(int(c) for c in np.unique(coord).tolist())
        self._ck_groups.update(str(g) for g in pd.unique(groups).tolist())
        yf = y.astype(np.float64)
        big = np.isfinite(yf) & (np.abs(yf) >= K.SENTINEL_MASK_ABS)
        if big.any():
            raise DeriveRefusal("G-SENTINEL", "%d target values at the sentinel magnitude; the ingest writes "
                                "invalid labels as NaN (D30)" % int(big.sum()),
                                fix="write invalid labels as NaN in the target store")
        valid = np.isfinite(yf) if y.dtype.kind == "f" else np.ones(n, dtype=bool)
        # R1's hashes, in row order
        self._h_units.update(units)
        for c in self._h_times:
            self._h_times[c].update(times[c])
        # a repeated (unit, time) is R1's refusal
        key = codes * (1 << 24) + (coord - int(coord.min()))
        if np.unique(key).size != n:
            raise DeriveRefusal("R1", "rows repeat a (unit, time) key within one file (time on the %s line)"
                                % self.line, fix="the target table holds one row per unit and time (plan 1.2)")
        byte, bit = codes >> 3, (np.uint8(1) << (codes & 7).astype(np.uint8)).astype(np.uint8)
        for c in np.unique(coord).tolist():
            sel = coord == c
            ex = self._row(self._exist, int(c))
            if (ex[byte[sel]] & bit[sel]).any():
                raise DeriveRefusal("R1", "rows repeat a (unit, time) key across files (time %d on the %s "
                                    "line)" % (int(c), self.line),
                                    fix="the target table holds one row per unit and time (plan 1.2)")
            np.bitwise_or.at(ex, byte[sel], bit[sel])
            vs = sel & valid
            if vs.any():
                np.bitwise_or.at(self._row(self._valid, int(c)), byte[vs], bit[vs])
                hist = self._hist.get(int(c))
                if hist is None:
                    hist = self._hist[int(c)] = np.zeros(1 << HIST_BITS, dtype=np.int64)
                hist += np.bincount((sortable_keys(yf[vs] + 0.0) >> np.uint64(64 - HIST_BITS)).astype(np.int64),
                                    minlength=1 << HIST_BITS)
        self._grow_rows()
        np.add.at(self._rows_grow, codes, 1)
        # presence masks: R3's joined rows, R4's store first years
        year = coord // K.MONTHS_PER_YEAR if self.line == MONTH else coord
        mask = (np.asarray(self.presence.masks(rows), dtype=np.int64) if self.presence is not None
                else np.zeros(n, dtype=np.int64))
        if mask.shape != (n,):
            raise DeriveRefusal("R3", "the presence source gave %s masks for %d rows" % (mask.shape, n),
                                fix="internal: one mask per target row")
        frame = pd.DataFrame({"g": groups, "yr": year, "m": mask, "v": valid})
        for (g, yr, m), cnt in frame[frame["v"]].groupby(["g", "yr", "m"], sort=False).size().items():
            k = (str(g), int(yr), int(m))
            self.mask_valid[k] = self.mask_valid.get(k, 0) + int(cnt)
        by_mask = frame.groupby(["g", "m"], sort=False)["yr"]
        for (g, m), yr in by_mask.min().items():
            k = (str(g), int(m))
            old = self.mask_first_year.get(k)
            self.mask_first_year[k] = int(yr) if old is None else min(old, int(yr))
        for (g, m), cnt in by_mask.size().items():
            k = (str(g), int(m))
            self.mask_rows[k] = self.mask_rows.get(k, 0) + int(cnt)
        self.rows += n
        return int(coord.min()), int(coord.max())

    def _grow_rows(self) -> None:
        if len(self._rows_grow) < len(self._names):
            grown = np.zeros(max(len(self._names), 2 * len(self._rows_grow), 1024), dtype=np.int64)
            grown[:len(self._rows_grow)] = self._rows_grow
            self._rows_grow = grown

    # ------------------------------------------------------------------ checkpoints (owner ruling P1)
    def checkpoint_delta(self) -> Tuple[Dict[str, Any], Dict[str, np.ndarray]]:
        """What the files added since the last call changed, as ABSOLUTE values over what they touched (meta,
        arrays): the units first seen (their names and groups), the row counts of the touched unit codes, the
        existence and validity bytes of the touched coordinates over the touched codes' bytes, the histograms of
        the touched coordinates (non-zero bins), the presence counts of the touched groups, the row total and
        R1's hash states. Replaying the deltas in order (apply_checkpoint_delta) rebuilds the census exactly:
        a delta overwrites only state its files changed, with that state's value after them."""
        n_before, n_after = self._ck_names, len(self._names)
        lo = n_after if self._ck_lo is None else int(self._ck_lo)
        hi = lo if self._ck_hi is None else int(self._ck_hi)
        b_lo, b_hi = lo >> 3, (hi + 7) >> 3
        coords = sorted(self._ck_coords)
        width = max(b_hi - b_lo, 0)
        exist = np.zeros((len(coords), width), dtype=np.uint8)
        valid = np.zeros((len(coords), width), dtype=np.uint8)
        has_valid = []
        h_coord, h_bin, h_count = [], [], []
        for k, c in enumerate(coords):
            exist[k] = self._exist[c][b_lo:b_hi]
            has_valid.append(c in self._valid)
            if c in self._valid:
                valid[k] = self._valid[c][b_lo:b_hi]
            if c in self._hist:
                nz = np.flatnonzero(self._hist[c])
                h_coord.append(np.full(nz.size, c, dtype=np.int64))
                h_bin.append(nz.astype(np.int64))
                h_count.append(self._hist[c][nz])
        gi = {g: i for i, g in enumerate(self.groups_seen)}
        touched = set(self._ck_groups)
        mv = [(gi[g], yr, m, n) for (g, yr, m), n in self.mask_valid.items() if g in touched]
        mr = [(gi[g], m, n) for (g, m), n in self.mask_rows.items() if g in touched]
        mf = [(gi[g], m, yr) for (g, m), yr in self.mask_first_year.items() if g in touched]
        names = json.dumps(self._names[n_before:n_after], ensure_ascii=False).encode("utf-8")
        arrays = {
            "names": np.frombuffer(names, dtype=np.uint8),
            "name_groups": np.array([gi[g] for g in self._group_of[n_before:n_after]], dtype=np.int64),
            "rows": self._rows_grow[lo:hi].copy(),
            "exist": exist, "valid": valid,
            "hist_coord": np.concatenate(h_coord) if h_coord else np.zeros(0, np.int64),
            "hist_bin": np.concatenate(h_bin) if h_bin else np.zeros(0, np.int64),
            "hist_count": np.concatenate(h_count) if h_count else np.zeros(0, np.int64),
            "mask_valid": np.array(mv, dtype=np.int64).reshape(-1, 4),
            "mask_rows": np.array(mr, dtype=np.int64).reshape(-1, 3),
            "mask_first_year": np.array(mf, dtype=np.int64).reshape(-1, 3)}
        meta = {"n_before": n_before, "n_after": n_after, "lo": lo, "hi": hi, "b_lo": b_lo, "b_hi": b_hi,
                "coords": coords, "has_valid": has_valid, "rows_total": int(self.rows), "line": self.line,
                "column_of": dict(self.column_of), "groups_seen": list(self.groups_seen),
                "hash_units": self._h_units.export(),
                "hash_times": {c: h.export() for c, h in self._h_times.items()}}
        self._ck_names, self._ck_lo, self._ck_hi = n_after, None, None
        self._ck_coords, self._ck_groups = set(), set()
        return meta, arrays

    def apply_checkpoint_delta(self, meta: Mapping[str, Any], arrays: Mapping[str, np.ndarray]) -> None:
        """Replay one checkpoint_delta onto this census (the deltas in order, from an empty census). Refuses
        (CensusCheckpointMismatch) a delta that does not continue the state replayed so far."""
        if int(meta["n_before"]) != len(self._names):
            raise CensusCheckpointMismatch("the delta starts at %s units, the replayed census holds %d"
                                           % (meta["n_before"], len(self._names)))
        groups_seen = [str(g) for g in meta["groups_seen"]]
        if groups_seen[:len(self.groups_seen)] != list(self.groups_seen):
            raise CensusCheckpointMismatch("the delta's groups do not continue the replayed ones")
        names = json.loads(np.asarray(arrays["names"], dtype=np.uint8).tobytes().decode("utf-8"))
        name_groups = np.asarray(arrays["name_groups"], dtype=np.int64)
        if len(names) != int(meta["n_after"]) - int(meta["n_before"]) or len(names) != len(name_groups):
            raise CensusCheckpointMismatch("the delta's new units do not match its counts")
        self.groups_seen = list(groups_seen)
        for u, g in zip(names, name_groups.tolist()):
            if u in self._code_of:
                raise CensusCheckpointMismatch("unit %r is new in a delta but already replayed" % (u,))
            self._code_of[u] = len(self._names)
            self._names.append(u)
            self._group_of.append(groups_seen[g])
        self._grow()
        self._grow_rows()
        lo, hi, b_lo, b_hi = int(meta["lo"]), int(meta["hi"]), int(meta["b_lo"]), int(meta["b_hi"])
        if hi > len(self._names) or lo > hi:
            raise CensusCheckpointMismatch("the delta's unit range [%d, %d) lies outside %d units"
                                           % (lo, hi, len(self._names)))
        self._rows_grow[lo:hi] = np.asarray(arrays["rows"], dtype=np.int64)
        exist, valid = np.asarray(arrays["exist"], dtype=np.uint8), np.asarray(arrays["valid"], dtype=np.uint8)
        for k, c in enumerate(int(x) for x in meta["coords"]):
            self._row(self._exist, c)[b_lo:b_hi] = exist[k]
            if meta["has_valid"][k]:
                self._row(self._valid, c)[b_lo:b_hi] = valid[k]
        hc = np.asarray(arrays["hist_coord"], dtype=np.int64)
        hb = np.asarray(arrays["hist_bin"], dtype=np.int64)
        hn = np.asarray(arrays["hist_count"], dtype=np.int64)
        for c in np.unique(hc).tolist():
            sel = hc == c
            hist = np.zeros(1 << HIST_BITS, dtype=np.int64)
            hist[hb[sel]] = hn[sel]
            self._hist[int(c)] = hist
        for g, yr, m, n in np.asarray(arrays["mask_valid"], dtype=np.int64).tolist():
            self.mask_valid[(groups_seen[g], int(yr), int(m))] = int(n)
        for g, m, n in np.asarray(arrays["mask_rows"], dtype=np.int64).tolist():
            self.mask_rows[(groups_seen[g], int(m))] = int(n)
        for g, m, yr in np.asarray(arrays["mask_first_year"], dtype=np.int64).tolist():
            self.mask_first_year[(groups_seen[g], int(m))] = int(yr)
        self.rows = int(meta["rows_total"])
        if meta["line"] is not None:
            self.line, self.column_of = str(meta["line"]), {str(k): str(v) for k, v in meta["column_of"].items()}
        self._h_units.restore(meta["hash_units"])
        if sorted(meta["hash_times"]) != sorted(self._h_times):
            raise CensusCheckpointMismatch("the delta's time hashes are for other columns")
        for c, h in self._h_times.items():
            h.restore(meta["hash_times"][c])
        self._ck_names, self._ck_lo, self._ck_hi = len(self._names), None, None
        self._ck_coords, self._ck_groups = set(), set()

    def finish(self) -> None:
        n_units = len(self._names)
        self.unit_names = np.array(self._names, dtype=object)
        self.unit_group = np.array(self._group_of, dtype=object)
        self.unit_rows = self._rows_grow[:n_units].copy()
        self.coords = np.array(sorted(self._exist), dtype=np.int64)
        width = (n_units + 7) // 8
        self.exist_bits = np.stack([self._exist[int(c)][:width] for c in self.coords]) if len(self.coords) \
            else np.zeros((0, width), dtype=np.uint8)
        self.valid_bits = np.stack([self._valid.get(int(c), np.zeros(self._cap, np.uint8))[:width]
                                    for c in self.coords]) if len(self.coords) else np.zeros((0, width), np.uint8)
        self.hist = {int(c): h for c, h in self._hist.items()}
        self._exist = self._valid = {}
        self._hist = {}
        self.groups = tuple(self.groups_seen)

    def finish_hashes(self) -> Dict[str, str]:
        out = {"unit_ids": self._h_units.hexdigest()}
        for c in sorted(self._h_times):
            out["time:" + c] = self._h_times[c].hexdigest()
        self.r1_hashes = out
        return out

    # ------------------------------------------------------------------ bit matrices
    def n_units(self) -> int:
        return len(self.unit_names)

    def unit_blocks(self) -> List[Tuple[int, int]]:
        n = self.n_units()
        return [(a, min(a + UNIT_BLOCK, n)) for a in range(0, n, UNIT_BLOCK)]

    def bits(self, which: str, a: int, b: int, coord_mask: Optional[np.ndarray] = None) -> np.ndarray:
        """(units a..b-1) x (coordinates) booleans of the 'exist' or 'valid' bits (a multiple of 8)."""
        src = self.exist_bits if which == "exist" else self.valid_bits
        if coord_mask is not None:
            src = src[coord_mask]
        block = np.unpackbits(src[:, a // 8:(b + 7) // 8], axis=1, bitorder="little")
        return block[:, :b - a].T.astype(bool)

    # ------------------------------------------------------------------ R1
    def r01(self) -> Any:
        """R1 by the approved rule on the reduced table (module docstring), with the true row count and
        the streamed hashes."""
        if self._r1 is not None:
            return self._r1
        if self.rows == 0:
            raise DeriveRefusal("R1", "the target table is empty", fix="read the target table first")
        units_r: List[np.ndarray] = []
        coords_r: List[np.ndarray] = []
        for a, b in self.unit_blocks():
            m = self.bits("exist", a, b)
            rr, cc = np.nonzero(m)
            t = self.coords[cc]
            first = np.r_[True, rr[1:] != rr[:-1]]
            same = ~first[1:]
            gaps = (t[1:] - t[:-1])[same]
            gunit = rr[1:][same]
            pairs = pd.DataFrame({"u": gunit, "d": gaps}).drop_duplicates().sort_values(["u", "d"], kind="stable")
            t0 = pd.Series(t[first], index=rr[first])
            pu, pd_ = pairs["u"].to_numpy(), pairs["d"].to_numpy()
            # each unit: its first coordinate, then one step of each gap size it shows, ascending
            cum = pd.Series(pd_).groupby(pu).cumsum().to_numpy() if len(pu) else np.zeros(0, np.int64)
            extra_u = pu
            extra_t = t0.reindex(pu).to_numpy() + cum
            u_all = np.concatenate([t0.index.to_numpy(), extra_u])
            t_all = np.concatenate([t0.to_numpy(), extra_t])
            order = np.lexsort((t_all, u_all))
            units_r.append(self.unit_names[a + u_all[order]])
            coords_r.append(t_all[order])
        units = np.concatenate(units_r) if units_r else np.zeros(0, dtype=object)
        coords = np.concatenate(coords_r) if coords_r else np.zeros(0, dtype=np.int64)
        d = R.derive_r01_cadence(units, self._time_columns_of(coords), self.time_facts)
        inputs = dict(d.inputs)
        inputs["rows"] = int(self.rows)
        self._r1 = make_derived("R1", d.value, inputs, array_hashes=self.r1_hashes, margins=d.margins,
                                flags=tuple(d.flags))
        return self._r1

    def _time_columns_of(self, coords: np.ndarray) -> Dict[str, np.ndarray]:
        coords = np.asarray(coords, dtype=np.int64)
        if self.line == MONTH:
            out = {self.column_of[_steps.YEAR]: coords // K.MONTHS_PER_YEAR,
                   self.column_of[_steps.MONTH]: coords % K.MONTHS_PER_YEAR + 1}
        else:
            out = {self.column_of[_steps.YEAR]: coords}
        return out

    # ------------------------------------------------------------------ the view at one cadence
    def view(self, cadence: Any, target_facts: Any, withhold_before_step: Optional[int]) -> SimpleNamespace:
        """Steps, years and label-window ends per coordinate under R1's cadence, and which coordinates
        keep their labels (withhold_before_step: labels at earlier steps are read as invalid)."""
        key = (repr(cadence), withhold_before_step)
        if key in self._views:
            return self._views[key]
        steps = _steps.step_index(self._time_columns_of(self.coords), self.time_facts, cadence)
        if len(np.unique(steps)) != len(steps) or (np.diff(steps) <= 0).any():
            raise DeriveRefusal("R1", "the census's calendar coordinates do not map one to one onto ascending "
                                "steps under the cadence %s" % (cadence,),
                                fix="owner item: the streamed census keys rows by their calendar parts")
        years = O._step_years(steps, cadence)
        first, last = _steps.step_bounds(steps, cadence)
        wend = np.array([timing.target_content(target_facts, (int(a), int(b)))[1]
                         for a, b in zip(first.tolist(), last.tolist())], dtype=np.int64)
        keep = np.ones(len(steps), dtype=bool) if withhold_before_step is None else steps >= int(withhold_before_step)
        if withhold_before_step is not None:
            before = steps < int(withhold_before_step)
            if before.any() and (~before).any() and years[before].max() >= years[~before].min():
                raise DeriveRefusal("R4", "labels are withheld before step %d, which is not the first step of a "
                                    "year" % int(withhold_before_step), fix="internal: withhold whole years before Y0")
        out = SimpleNamespace(steps=steps, years=years, window_end=wend, keep=keep, last_day=last,
                              withhold=withhold_before_step)
        self._views[key] = out
        return out

    # ------------------------------------------------------------------ counts derive_all reads
    def first_year(self, view: Any) -> int:
        return int(view.years.min())

    def r03_counts(self, view: Any, groups: Tuple[str, ...], kept: Sequence[str]) -> Dict[Tuple[str, int], int]:
        """count_valid_rows_per_group_year's dict: valid AND joined rows (F2) per (group, year) of the
        listed groups, sorted, no zero keys."""
        need = self.presence.stores_for(kept) if self.presence is not None else ()
        withheld_years = set(view.years[~view.keep].tolist())
        listed = set(groups)
        out: Dict[Tuple[str, int], int] = {}
        for (g, yr, m), n in self.mask_valid.items():
            if g not in listed or yr in withheld_years or not self._joined(m, g, need):
                continue
            out[(g, yr)] = out.get((g, yr), 0) + n
        return {k: out[k] for k in sorted(out) if out[k] > 0}

    def _joined(self, mask: int, group: str, stores: Sequence[int]) -> bool:
        for s in stores:
            if not (mask >> s) & 1 and group not in self.presence.absent[s]:
                return False
        return True

    def present_rows(self, store: int) -> int:
        """Target rows (valid label or not) that presence store `store` holds: the column reader's
        present_rows of that store over every census row (its data manifest)."""
        return int(sum(n for (_, m), n in self.mask_rows.items() if (m >> int(store)) & 1))

    def r04_rows(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, "_MaskReader"]:
        """A reduced row set for orchestrate._r04_first_data_year: one row per (group, presence mask) at
        the first year a row with that mask occurs (the store's first year is the earliest held row, and
        whether a row is held depends only on its group and mask), with a reader answering from the
        mask."""
        keys = sorted(self.mask_first_year)
        groups = np.array([g for g, _ in keys], dtype=object)
        masks = np.array([m for _, m in keys], dtype=np.int64)
        years = np.array([self.mask_first_year[k] for k in keys], dtype=np.int64)
        units = np.array(["census_row_%d" % i for i in range(len(keys))], dtype=object)
        return units, groups, years, _MaskReader(self, masks, groups)

    def valid_window_counts(self, view: Any, first_step: int, last_step: int,
                            which: str = "valid") -> np.ndarray:
        """Per unit: rows with the 'valid' (or 'exist') bit inside [first_step, last_step] (withheld
        labels count as invalid)."""
        cm = (view.steps >= int(first_step)) & (view.steps <= int(last_step))
        if which == "valid":
            cm &= view.keep
        out = np.zeros(self.n_units(), dtype=np.int64)
        if not cm.any():
            return out
        for a, b in self.unit_blocks():
            out[a:b] = self.bits(which, a, b, cm).sum(axis=1)
        return out

    def first_valid_step(self, view: Any) -> np.ndarray:
        """Per unit: the step of its first kept valid label (a huge number when it has none)."""
        out = np.full(self.n_units(), np.iinfo(np.int64).max, dtype=np.int64)
        cm = view.keep
        if not cm.any():
            return out
        st = view.steps[cm]
        for a, b in self.unit_blocks():
            m = self.bits("valid", a, b, cm)
            has = m.any(axis=1)
            out[a:b][has] = st[np.argmax(m[has], axis=1)]
        return out

    # ------------------------------------------------------------------ R18's event rate, exactly
    def event_rate(self, view: Any, groups: Tuple[str, ...], cut: int, cut_day: int, pct: float) -> SimpleNamespace:
        """(events, rows, q90, row_key_hash) of the label-only donor view of every unit of the groups at
        the cut (valid labels at or before it whose own window has ended by its last day), exactly as
        orchestrate._PlanLabels.donor_labels and unit_rules.donor_event_rate compute them.
        Zeros: every label is keyed and selected as y + 0.0, so -0.0 and +0.0 share one histogram bin and
        the count of labels at or below q90 is numpy's (its comparisons treat the two as equal). The sign
        of a zero order statistic is put back as numpy's selection gives it: -0.0 when every zero donor
        label is -0.0, +0.0 when none is. When the donor labels hold zeros of both signs, which zeros
        numpy's partition puts at the two ranks is not defined by the values; this takes +0.0 there, so
        a q90 that numpy interpolates to -0.0 from two -0.0 picks is written 0.0 here (the same number;
        the event count is unchanged)."""
        usable = view.keep & (view.steps <= int(cut)) & (view.window_end <= int(cut_day))
        in_groups = pd.Series(self.unit_group).isin(list(groups)).to_numpy()
        # the row keys: units in code-point order, steps ascending (from the validity bits)
        order = np.argsort(self.unit_names, kind="stable")
        counts = np.zeros(self.n_units(), dtype=np.int64)
        for a, b in self.unit_blocks():
            counts[a:b] = self.bits("valid", a, b, usable).sum(axis=1) if usable.any() else 0
        counts[~in_groups] = 0
        n = int(counts.sum())
        h_units, h_times = _ArrayHash(n, "text"), _ArrayHash(n, "int64")
        st = view.steps[usable]
        for a in range(0, len(order), UNIT_BLOCK):
            idx = order[a:a + UNIT_BLOCK]
            idx = idx[counts[idx] > 0]
            if not idx.size:
                continue
            m = self._rows_of_units(idx, usable)
            rr, cc = np.nonzero(m)
            h_units.update(np.repeat(self.unit_names[idx], counts[idx]))
            h_times.update(st[cc])
        key_hash = sha256_of_json([h_units.hexdigest(), h_times.hexdigest()])
        if n == 0:
            return SimpleNamespace(events=0, rows=0, q90=None, row_key_hash=key_hash)
        kp, kn = percentile_ranks(n, pct)
        vals = self._order_statistics(view, usable, in_groups, groups, (kp, kn), n)
        prev, nxt = vals["value"][kp], vals["value"][kn]
        zero = -0.0 if vals["negative_zeros"] and not vals["positive_zeros"] else 0.0
        q = _linear_percentile(zero if prev == 0 else prev, zero if nxt == 0 else nxt, n, pct)
        if not prev <= q <= nxt:
            raise DeriveRefusal("R18", "internal: the interpolated percentile %r lies outside [%r, %r]"
                                % (q, prev, nxt), fix="internal")
        if q < nxt:
            at_most = kp + 1
        else:
            lo_rank, sorted_bin = vals["bin_of"][kn]
            at_most = lo_rank + int(np.searchsorted(sorted_bin, q, side="right"))
        return SimpleNamespace(events=int(n - at_most), rows=n, q90=q, row_key_hash=key_hash)

    def _rows_of_units(self, idx: np.ndarray, coord_mask: np.ndarray) -> np.ndarray:
        """(units idx) x (masked coordinates) valid bits, for arbitrary unit indices."""
        src = self.valid_bits[coord_mask]
        cols = src[:, idx >> 3]
        return ((cols >> (idx & 7).astype(np.uint8)) & 1).T.astype(bool)

    def _order_statistics(self, view: Any, usable: np.ndarray, in_groups: np.ndarray, groups: Tuple[str, ...],
                          ranks: Tuple[int, ...], n: int) -> Dict[str, Any]:
        """The donor labels at the given 0-based ranks (ascending), by an exact radix select over the
        labels' sortable keys: the census histograms (or one histogram pass when the census holds
        groups outside the donor groups) find each rank's 2^16 bin; a bin too large to hold is refined
        16 bits at a time (one pass each); one last pass collects the bins, which are sorted.
        Returns {'value': {rank: label}, 'bin_of': {rank: (rows below its bin, its bin's sorted labels)},
        'negative_zeros' / 'positive_zeros': the donor labels equal to -0.0 / +0.0} (labels as y + 0.0)."""
        shift = 64 - HIST_BITS
        if bool(in_groups.all()):
            hist = np.zeros(1 << HIST_BITS, dtype=np.int64)
            for c, ok in zip(self.coords.tolist(), usable.tolist()):
                if ok and c in self.hist:
                    hist += self.hist[c]
        else:
            hist = self._histogram_pass(view, usable, groups, 0, 1 << 64, shift)
        if int(hist.sum()) != n:
            raise DeriveRefusal("R18", "internal: the label histogram holds %d donor rows, the validity bits %d"
                                % (int(hist.sum()), n), fix="internal")
        cum = np.concatenate([[0], np.cumsum(hist)])
        ranges: Dict[int, Tuple[int, int, int, int]] = {}            # rank -> (lo, hi, below, size)
        for r in ranks:
            b = int(np.searchsorted(cum, r, side="right") - 1)
            ranges[r] = (b << shift, (b + 1) << shift, int(cum[b]), int(hist[b]))
        while shift > 0 and any(size > COLLECT_CAP for _, _, _, size in ranges.values()):
            nxt = max(0, shift - HIST_BITS)
            todo: Dict[Tuple[int, int, int], List[int]] = {}
            for r, (lo, hi, below, size) in ranges.items():
                if size > COLLECT_CAP:
                    todo.setdefault((lo, hi, below), []).append(r)
            for (lo, hi, below), rs in todo.items():
                sub = self._histogram_pass(view, usable, groups, lo, hi, nxt)
                cum2 = np.concatenate([[0], np.cumsum(sub)])
                for r in rs:
                    b = int(np.searchsorted(cum2, r - below, side="right") - 1)
                    ranges[r] = (lo + (b << nxt), lo + ((b + 1) << nxt), below + int(cum2[b]), int(sub[b]))
            shift = nxt
        bins = sorted(set((lo, hi) for lo, hi, _, _ in ranges.values()))
        collected, signs = self._collect_pass(view, usable, groups, bins)
        value: Dict[int, float] = {}
        bin_of: Dict[int, Tuple[int, np.ndarray]] = {}
        for r, (lo, hi, below, size) in ranges.items():
            vals = collected[(lo, hi)]
            if len(vals) != size:
                raise DeriveRefusal("R18", "internal: a label bin held %d rows on the collect pass, %d before: the "
                                    "store changed during the run" % (len(vals), size),
                                    fix="re-run; never write a store a run reads")
            value[r] = float(vals[r - below])
            bin_of[r] = (below, vals)
        return {"value": value, "bin_of": bin_of, "negative_zeros": signs[0], "positive_zeros": signs[1]}

    def _donor_mask(self, rows: FileRows, view: Any, usable: np.ndarray, groups: Tuple[str, ...]) -> np.ndarray:
        y = np.asarray(rows.y, dtype=np.float64)
        coord = self._calendar_coord({c: _steps.as_int_array(v, c) for c, v in rows.time_columns.items()})
        ok = np.isfinite(y) & usable[np.searchsorted(self.coords, coord)]
        return ok & pd.Series(np.asarray(rows.group_ids, dtype=object)).isin(list(groups)).to_numpy()

    def _scan_donor_values(self, view: Any, usable: np.ndarray, groups: Tuple[str, ...],
                           fn: Callable[[np.ndarray], None]) -> None:
        """fn(the donor labels of each file), file by file; a file of no donor group, or whose
        coordinates (file_coords) hold no usable coordinate, is not read."""
        fg = getattr(self.source, "file_groups", None)
        for i, handle in enumerate(self.source.files):
            if fg is not None:
                held = fg(handle)
                if held is not None and not set(held) & set(groups):
                    continue
            span = self._file_span(i)
            if span is not None and not usable[(self.coords >= span[0]) & (self.coords <= span[1])].any():
                continue
            rows = self.source.read(handle)
            if len(rows.unit_ids) == 0:
                continue
            ok = self._donor_mask(rows, view, usable, groups)
            if ok.any():
                fn(np.asarray(rows.y, dtype=np.float64)[ok])

    def _histogram_pass(self, view: Any, usable: np.ndarray, groups: Tuple[str, ...], lo: int, hi: int,
                        shift: int) -> np.ndarray:
        """Counts of the donor labels with keys in [lo, hi), in bins of 2^shift keys from lo."""
        nbins = (hi - lo) >> shift
        hist = np.zeros(nbins, dtype=np.int64)
        lo_k, top_k = np.uint64(lo), np.uint64(hi - 1)

        def add(y: np.ndarray) -> None:
            k = sortable_keys(y + 0.0)                 # -0.0 keyed as +0.0 (event_rate's docstring)
            k = k[(k >= lo_k) & (k <= top_k)]
            if k.size:
                hist[:] += np.bincount(((k - lo_k) >> np.uint64(shift)).astype(np.int64), minlength=nbins)
        self._scan_donor_values(view, usable, groups, add)
        return hist

    def _collect_pass(self, view: Any, usable: np.ndarray, groups: Tuple[str, ...],
                      bins: List[Tuple[int, int]]) -> Tuple[Dict[Tuple[int, int], np.ndarray], Tuple[int, int]]:
        """The donor labels (as y + 0.0) of each key bin, sorted; and the donor labels equal to -0.0 and to
        +0.0 as stored."""
        parts: Dict[Tuple[int, int], List[np.ndarray]] = {b: [] for b in bins}
        signs = [0, 0]

        def add(y: np.ndarray) -> None:
            zero = y == 0
            if zero.any():
                neg = int(np.signbit(y[zero]).sum())
                signs[0] += neg
                signs[1] += int(zero.sum()) - neg
            y = y + 0.0                                # -0.0 read as +0.0 (event_rate's docstring)
            k = sortable_keys(y)
            for lo, hi in bins:
                sel = (k >= np.uint64(lo)) & (k <= np.uint64(hi - 1))
                if sel.any():
                    parts[(lo, hi)].append(y[sel])
        self._scan_donor_values(view, usable, groups, add)
        return ({b: np.sort(np.concatenate(p)) if p else np.zeros(0) for b, p in parts.items()},
                (signs[0], signs[1]))

    # ------------------------------------------------------------------ full rows of picked units
    def _file_span(self, i: int) -> Optional[Tuple[int, int]]:
        """(first, last) calendar coordinate of source file i from the scan, or None when unknown (a
        census not built by scan_target, or a source whose file list changed since)."""
        if self.file_coords is None or len(self.file_coords) != len(self.source.files):
            return None
        span = self.file_coords[i]
        return (1, 0) if span is None else span            # a file without rows: an empty span

    def rows_from(self, codes: np.ndarray, min_coord: Optional[int]) -> np.ndarray:
        """Per unit code: its rows at calendar coordinates >= min_coord (every row with None), from the
        'exist' bits."""
        codes = np.asarray(codes, dtype=np.int64)
        if min_coord is None:
            return self.unit_rows[codes].copy()
        cm = self.coords >= int(min_coord)
        if not cm.any() or not codes.size:
            return np.zeros(codes.size, dtype=np.int64)
        src = self.exist_bits[cm]
        out = np.zeros(codes.size, dtype=np.int64)
        for a in range(0, codes.size, UNIT_BLOCK):
            idx = codes[a:a + UNIT_BLOCK]
            out[a:a + UNIT_BLOCK] = ((src[:, idx >> 3] >> (idx & 7).astype(np.uint8)) & 1).sum(axis=0)
        return out

    def read_units(self, units: Sequence[str], cache: bool = True, min_coord: Optional[int] = None,
                   labels: bool = True) -> SimpleNamespace:
        """The target rows of the given units, in the census's row order (file order). min_coord: only
        the rows at calendar coordinates >= min_coord (a file whose coordinates all lie before it is not
        read); None: every row. labels=False: every label is dropped (NaN) as the file is read, before
        any row leaves this method (the target reader returns the label with the row). Units the census
        does not hold are refused. With cache (the picked units: every row, labels as stored) the last
        unit set is kept and served again."""
        key = tuple(sorted(set(str(u) for u in units)))
        if cache and not (min_coord is None and labels):
            raise DeriveRefusal("G-DONOR", "internal: only the picked units' whole rows are cached", fix="internal")
        if cache and self._picked is not None and self._picked[0] == key:
            return self._picked[1]
        codes = np.array([self._code_of.get(u, -1) for u in key], dtype=np.int64)
        if (codes < 0).any():
            raise DeriveRefusal("G-DONOR", "units %s are not in the target census"
                                % [u for u, c in zip(key, codes) if c < 0][:_SHOW], fix="internal")
        expected = int(self.rows_from(codes, min_coord).sum())
        if self.row_guard is not None:
            self.row_guard(expected)                   # refuses before any row is read when they would not fit
        wanted = np.zeros(self.n_units(), dtype=bool)
        wanted[codes] = True
        groups = set(self.unit_group[codes].tolist())
        parts = []
        fg = getattr(self.source, "file_groups", None)
        self.last_read_files = 0
        for i, handle in enumerate(self.source.files):
            if fg is not None:
                held = fg(handle)
                if held is not None and not set(held) & groups:
                    continue
            span = self._file_span(i)
            if min_coord is not None and span is not None and span[1] < int(min_coord):
                continue
            rows = self.source.read(handle)
            self.last_read_files += 1
            if len(rows.unit_ids) == 0:
                continue
            u = np.asarray(rows.unit_ids, dtype=object)
            local, uniq = pd.factorize(pd.Series(u, copy=False), sort=False)
            hit = np.array([wanted[self._code_of[x]] if x in self._code_of else False for x in uniq.tolist()],
                           dtype=bool)
            sel = hit[np.asarray(local)]
            times = {c: _steps.as_int_array(v, c) for c, v in rows.time_columns.items()}
            if min_coord is not None and sel.any():
                sel &= self._calendar_coord(times) >= int(min_coord)
            if sel.any():
                y = np.asarray(rows.y, dtype=np.float64)[sel] if labels else np.full(int(sel.sum()), np.nan)
                parts.append(FileRows(unit_ids=u[sel], group_ids=np.asarray(rows.group_ids, dtype=object)[sel],
                                      time_columns={c: v[sel] for c, v in times.items()}, y=y))
            del rows
        if not parts:
            raise DeriveRefusal("G-DONOR", "no target row of the units was read again", fix="internal")
        cols = sorted(parts[0].time_columns)
        out = SimpleNamespace(unit_ids=np.concatenate([p.unit_ids for p in parts]),
                              group_ids=np.concatenate([p.group_ids for p in parts]),
                              time_columns={c: np.concatenate([p.time_columns[c] for p in parts]) for c in cols},
                              y=np.concatenate([p.y for p in parts]))
        if len(out.unit_ids) != expected:
            raise DeriveRefusal("G-DONOR", "the units' rows read again (%d) differ from the census's count "
                                "(%d): the store changed during the run" % (len(out.unit_ids), expected),
                                fix="re-run; never write a store a run reads")
        if cache:
            self._picked = (key, out)
        return out

    def units_of_group(self, group: str) -> np.ndarray:
        return self.unit_names[self.unit_group == group]


class _MaskReader(object):
    """drivers_present over the census's reduced (group, mask) rows (for orchestrate._r04_first_data_year)."""

    def __init__(self, census: TargetCensus, masks: np.ndarray, groups: np.ndarray) -> None:
        self._census, self._masks, self._groups = census, masks, groups

    def drivers_present(self, unit_ids: Any, group_ids: Any, time_columns: Any, columns: Sequence[str]) -> np.ndarray:
        stores = self._census.presence.stores_for(columns) if self._census.presence is not None else ()
        return np.array([self._census._joined(int(m), str(g), stores)
                         for m, g in zip(self._masks.tolist(), self._groups.tolist())], dtype=bool)


class CensusCheckpoint(object):
    """scan_target's checkpoints (owner ruling P1; runs/checkpoint.py). A chunk closes after every
    len(files) / C.census_checkpoint_chunks files (at least one), or after C.census_checkpoint_seconds, and at the
    last file; its record 'chunk_<n>' holds TargetCensus.checkpoint_delta (the counters, bits and hash states the
    chunk changed, as their values after it), the presence reader's driver files read in the chunk (with their
    calendar spans and rows) and the groups whose driver keys it held, and the chunk's file spans. A restart
    replays the records in order on an empty census (each must continue the one before: a corrupt or
    non-continuing record is reported, moved aside with every record after it, and its files are read again),
    then reads the files after the last record."""

    PREFIX = "chunk"

    def __init__(self, step: Any, n_files: int, echo: Optional[Callable[[str], None]]) -> None:
        self.step, self.n_files = step, int(n_files)
        self.echo = echo if echo is not None else (lambda _msg: None)
        self.every = max(1, -(-self.n_files // int(K.CENSUS_CHECKPOINT_CHUNKS)))
        self.seconds = float(K.CENSUS_CHECKPOINT_SECONDS)
        self.next_chunk, self.done, self.t, self.presence_mark = 0, 0, time.time(), 0
        self.saved = 0

    def _name(self, k: int) -> str:
        return "%s_%06d" % (self.PREFIX, k)

    def _index(self, name: str) -> int:
        tail = name[len(self.PREFIX) + 1:]
        return int(tail) if tail.isdigit() else -1

    def resume(self, make_census: Callable[[], TargetCensus], presence: Any
               ) -> Tuple[TargetCensus, int, List[Optional[Tuple[int, int]]]]:
        """(census, files done, their spans) after replaying the saved chunks (a fresh census when none)."""
        names = set(n for n in self.step.records(self.PREFIX + "_") if self._index(n) >= 0)
        while True:
            census = make_census()
            reset = getattr(presence, "reset_checkpoint_state", None)
            if reset is not None:
                reset()
            done, spans, k, replay_again = 0, [], 0, False
            while self._name(k) in names:
                got = self.step.load_arrays(self._name(k))
                if got is None:                                  # corrupt: reported loudly and moved aside
                    names.discard(self._name(k))
                    break
                meta, arrays = got
                try:
                    if int(meta["file_from"]) != done or int(meta["files"]) != self.n_files:
                        raise CensusCheckpointMismatch("it covers files %s-%s of %s; the replay stands at file %d of "
                                                       "%d" % (meta["file_from"], meta["file_to"], meta["files"],
                                                               done, self.n_files))
                    census.apply_checkpoint_delta(meta["census"], arrays)
                    if meta.get("presence") is not None:
                        restore = getattr(presence, "restore_checkpoint_state", None)
                        if restore is None:
                            raise CensusCheckpointMismatch("it holds presence state this presence source cannot take")
                        restore(meta["presence"])
                except (CensusCheckpointMismatch, KeyError, ValueError, TypeError, IndexError) as exc:
                    self.step.quarantine(self._name(k), "it does not continue the census replayed so far (%s)" % exc)
                    names.discard(self._name(k))
                    replay_again = True                          # the census may hold part of it: start again
                    break
                spans.extend(None if sp is None else (int(sp[0]), int(sp[1])) for sp in meta["spans"])
                done = int(meta["file_to"])
                k += 1
            if not replay_again:
                break
        rest = sorted((n for n in names if self._index(n) >= k), key=self._index)
        if rest:
            self.step.discard_from(rest, "it follows %s, which is missing or could not be replayed" % self._name(k))
        self.next_chunk, self.done, self.t = k, done, time.time()
        self.presence_mark = len(getattr(presence, "files_read", ()) or ())
        if done:
            self.echo("checkpoint: census resumed at file %d of %d (%d chunk(s) loaded: %d rows, %d units so far)"
                      % (done, self.n_files, k, census.rows, len(census._names)))
        return census, done, spans

    def after_file(self, files_done: int, spans: Sequence[Any], census: TargetCensus, presence: Any) -> None:
        if files_done - self.done >= self.every or time.time() - self.t >= self.seconds:
            self.save(files_done, spans, census, presence)

    def save(self, files_done: int, spans: Sequence[Any], census: TargetCensus, presence: Any) -> None:
        if files_done <= self.done:
            return
        meta_c, arrays = census.checkpoint_delta()
        state = getattr(presence, "checkpoint_state", None)
        meta = {"file_from": self.done, "file_to": int(files_done), "files": self.n_files,
                "spans": [None if sp is None else [int(sp[0]), int(sp[1])] for sp in spans[self.done:files_done]],
                "census": meta_c, "presence": state(self.presence_mark) if state is not None else None}
        self.step.save_arrays(self._name(self.next_chunk), arrays, meta)
        self.next_chunk += 1
        self.saved += 1
        self.done, self.t = int(files_done), time.time()
        self.presence_mark = len(getattr(presence, "files_read", ()) or ())


def scan_target(source: Any, time_facts: Mapping[str, Any], presence: Any = None,
                expected_rows: Optional[int] = None, echo: Callable[[str], None] = None,
                checkpoint: Any = None) -> TargetCensus:
    """One streaming pass over the target source (file by file) -> TargetCensus. expected_rows is the
    row count the R1 hashes declare up front (sha256_of_array hashes the length first); when the files
    hold another count, the hashes are taken again in a second pass with the true count.
    checkpoint: a runs.checkpoint step (owner ruling P1): the census is saved every chunk of files
    (CensusCheckpoint) and a restart under the same key resumes after the last saved chunk. Needs the
    resumable SHA-256 (runs.checkpoint); without it the pass runs whole and the log says why."""
    n0 = int(source.expected_rows() if expected_rows is None else expected_rows)
    ck = None
    if checkpoint is not None:
        from treeroute.runs.checkpoint import resumable_sha256_available

        ok, why = resumable_sha256_available()
        if ok:
            ck = CensusCheckpoint(checkpoint, len(source.files), echo)
        elif echo is not None:
            echo("checkpoint: census chunks are OFF in this process: the resumable SHA-256 is not available (%s); "
                 "the census runs whole" % why)
    start = 0
    spans: List[Optional[Tuple[int, int]]] = []
    if ck is not None:
        census, start, spans = ck.resume(lambda: TargetCensus(source, time_facts, presence, n0, resumable=True),
                                         presence)
    else:
        census = TargetCensus(source, time_facts, presence, n0)
    for i in range(start, len(source.files)):
        spans.append(census.add(source.read(source.files[i])))
        if echo is not None and (i + 1) % 200 == 0:
            echo("census: %d of %d files, %d rows, %d units" % (i + 1, len(source.files), census.rows,
                                                                 len(census._names)))
        if ck is not None:
            ck.after_file(i + 1, spans, census, presence)
    if ck is not None:
        ck.save(len(source.files), spans, census, presence)
        if echo is not None:
            echo("checkpoint: census %s (%d chunk(s) saved by this process, %d in all)"
                 % ("read whole from its checkpoint: no target file was read" if start == len(source.files)
                    else "saved through file %d of %d" % (len(source.files), len(source.files)),
                    ck.saved, ck.next_chunk))
    census.finish()
    census.file_coords = spans
    if census.rows != n0:
        census._h_units = _ArrayHash(census.rows, "text")
        census._h_times = {c: _ArrayHash(census.rows, "int64") for c in sorted(census.time_facts)}
        for handle in source.files:
            rows = source.read(handle)
            census._h_units.update(np.asarray(rows.unit_ids, dtype=object))
            for c in census._h_times:
                census._h_times[c].update(_steps.as_int_array(rows.time_columns[c], c))
    census.finish_hashes()
    if echo is not None:
        echo("census: %d rows, %d units, %d groups, %d calendar steps (%d files)"
             % (census.rows, census.n_units(), len(census.groups), len(census.coords), len(source.files)))
    return census


def census_ram_bytes(units: int, coords: int, biggest_file_rows: int, biggest_group_rows: int,
                     presence_stores: int) -> int:
    """Go/refuse estimate of the census pass (runs.preflight.census_pass_ram_bytes with this module's
    histogram and unit-block sizes): one file being read, one group's driver keys, the two bit matrices,
    the unit table, the label histograms and one unit block unpacked."""
    from treeroute.runs.preflight import census_pass_ram_bytes

    return census_pass_ram_bytes(units, coords, biggest_file_rows, biggest_group_rows, presence_stores,
                                 1 << HIST_BITS, UNIT_BLOCK)


# ---------------------------------------------------------------------------------------------------
# derive_all over the census
def derive_all_streamed(package: Any, census: TargetCensus, share_reader: Any,
                        withhold_before_step: Optional[int] = None) -> Dict[str, Any]:
    """derive_all (orchestrate.py; same rules, same order, same entries, same bytes) over a streaming
    census instead of a whole target table. withhold_before_step: labels at earlier steps are read as
    invalid (the pipeline's second pass, C4: the years before Y0 are lag sources only), as derive_all
    reads a table whose labels there are NaN.
    Label reads: validity and the event rate from the census; the donor views, fit rows and fit-row
    counts from orchestrate._PlanLabels built on the PICKED units' rows (census.read_units).
    Refuses: whatever derive_all refuses, at the same rule (refusal texts may count differently)."""
    facts = O._Facts(package)
    out: Dict[str, Any] = {}

    # R1, R2
    out["R1"] = census.r01()
    cadence = out["R1"].value
    out["R2"] = R.derive_r02_season_key(cadence, getattr(cadence, "composites_per_year", None))
    if O._v(cadence.kind) == O.IRREGULAR:
        raise NotImplementedError("derive_all for events (irregular target cadence): the plan-time "
                                  "event rules are milestone M8")
    season = out["R2"].value

    # R8 over the kept columns, the guard, R4
    out["R8"] = R.derive_r08_feature_lags(facts.kept_facts, facts.target, cadence)
    R.check_r08_covers_kept_columns(facts.kept, out["R8"])
    O._check_epoch_columns(out["R8"], facts.frozen)
    view = census.view(cadence, facts.target, withhold_before_step)
    if census.presence is None:
        raise DeriveRefusal("derive_all", "the census was scanned without a presence source; F2 (R3) and J5 "
                            "(R4) need the drivers' row presence", fix="scan with the io presence reader")
    r_units, r_groups, r_years, r_reader = census.r04_rows()
    out["R4"] = O._r04_entry(package, facts, out["R8"].value, r_reader, r_units, r_groups, {}, r_years,
                             census.first_year(view))

    # the groups (leave one region out), R3 over the joined rows of every group (F2)
    split_sets = _split.loro_split_sets(package.split)
    data_groups = tuple(sorted(census.groups))
    groups = _split.groups_under_loro(split_sets, data_groups)
    diff = _split.loro_split_differences(split_sets, data_groups)
    if diff.listed_not_in_data or diff.reported_and_excluded or diff.duplicates:
        raise DeriveRefusal("G-SPLIT", "split.yaml differs from the data: %s" % (diff,),
                            fix="list only groups the data holds; a reported group is never excluded")
    out["R18:groups"] = make_derived("R18", groups, {
        "data_groups": len(data_groups), "excluded": dict(split_sets.excluded),
        "seen_during_design": list(split_sets.seen_during_design),
        "design": "leave one region out: every group trains its own trees and is tested"})
    counts = census.r03_counts(view, groups, facts.kept)
    out["R3"] = R.derive_r03_coverage_end(counts, groups, False)

    # R5 - R7, R10, R11, R9
    y0, y_end = out["R4"].value, out["R3"].value
    out["R5"] = R.derive_r05_test_window(y0, y_end)
    out["R6"] = R.derive_r06_train_end(out["R5"].value.test_years)
    out["R7"] = R.derive_r07_inner_windows(y0, y_end, out["R5"].value, out["R6"].value)
    windows = out["R7"].value
    out["R10"] = R.derive_r10_leads(season, False)
    out["R11"] = R.derive_r11_cuts(windows, out["R10"].value, cadence)
    cuts = out["R11"].value
    epochs: Dict[str, Sequence[int]] = {}
    if facts.frozen:
        O._require(share_reader, "content_epochs", "R9 (the content epochs of 'freeze' columns)")
        epochs = {c: tuple(int(e) for e in share_reader.content_epochs(c)) for c in facts.frozen}
    out["R9"] = R.derive_r09_freeze_epochs(epochs, R.cut_days(cuts, cadence))

    test_first_step = O._first_step_of_year(min(windows.test_years), cadence)
    train_end_step = int(cuts[0].fit_cut)
    inner_end_step = int(timing.year_last_step(windows.inner_fit[1], cadence))
    y0_step = O._first_step_of_year(y0, cadence)
    if train_end_step >= test_first_step:
        raise DeriveRefusal("G-LOCK", "a donor view at step %d reaches the test window (first step %d)"
                            % (train_end_step, test_first_step),
                            fix="donor and fit-row reads lie before the test window")

    # candidates (every group), R12: validity alone (split.candidate_units on one row per unit at its
    # first valid label: a unit is a candidate when that label lies at or before the train end)
    fvs = census.first_valid_step(view)
    has = fvs < np.iinfo(np.int64).max
    c_units, c_groups, c_steps = census.unit_names[has], census.unit_group[has], fvs[has]
    candidates = {g: _split.candidate_units(c_units, c_groups, c_steps, np.ones(len(c_units), dtype=bool), g,
                                            train_end_step)
                  for g in groups}
    every_candidate = [u for g in groups for u in candidates[g]]
    code_of = census._code_of
    cand_codes = np.array([code_of[u] for u in every_candidate], dtype=np.int64)
    exist_w = census.valid_window_counts(view, y0_step, inner_end_step, which="exist")
    valid_w = census.valid_window_counts(view, y0_step, inner_end_step, which="valid")
    in_window = cand_codes[exist_w[cand_codes] > 0]
    names_w = np.unique(census.unit_names[in_window]) if in_window.size else np.zeros(0, dtype=object)
    inner_counts: Dict[str, int] = {str(u): int(valid_w[code_of[u]]) for u in names_w.tolist()}
    for u in every_candidate:
        inner_counts.setdefault(u, 0)
    out["R12"] = RR.derive_r12_router_kind(inner_counts)
    kind = out["R12"].value

    # R13, R14, R17
    out["R13"] = RR.derive_r13_surface_loro(kind, groups)
    out["R14"] = RR.derive_r14_router_design(kind, facts.context_columns)
    out["R17"] = RR.derive_r17_history_spec(season, facts.target, cadence, kind, False)

    # R18: bank count, scored count (event floor), unit lists
    available = {g: len(candidates[g]) for g in groups}
    pooled = {g: int(sum(inner_counts[u] for u in candidates[g])) for g in groups}
    median_inner = float(np.median(list(inner_counts.values())))
    out["R18:bank"] = UR.derive_r18_bank_count(kind, season, median_inner, available, pooled,
                                               O._non_tree_columns(out["R14"].value, facts.context_columns))
    rule_value, bank = out["R18:bank"].value
    cut_day = int(_steps.step_bounds(np.array([train_end_step], dtype=np.int64), cadence)[1][0])
    rate = census.event_rate(view, groups, train_end_step, cut_day, float(K.EVENT_QUANTILE) * 100.0)
    if rate.rows == 0:
        raise DeriveRefusal("R18", "the donor view holds no row", fix="check the units and the cut")
    test_rows = int(season.steps_per_year) * len(windows.test_years)
    event_rate = UR.EventRate(events=int(rate.events), rows=int(rate.rows), q90=float(rate.q90),
                              unit_scope=UR.ALL_UNITS_SCOPE, cut=train_end_step, cut_kind=UR._value(CutKind.FIT),
                              lead=0, groups=len(tuple(groups)), row_key_hash=str(rate.row_key_hash),
                              source=EVENT_RATE_SOURCE)
    out["R18"] = UR.scored_counts_at_event_rate(kind, rule_value, bank, available, K.K_GROUP_EQUIVALENTS,
                                                event_rate, test_rows)
    lists = _split.pick_unit_lists(groups, candidates, out["R18"].value)
    out["R18:units"] = make_derived("R18", lists, {
        "bank_units_hash": {g: _split.unit_ids_hash(lists.bank[g]) for g in groups},
        "scored_units_hash": {g: _split.unit_ids_hash(lists.scored[g]) for g in groups},
        "rule": "bank by a stride over the sorted candidates (D40); scored = an evenly spaced subset "
                "of the bank units (L2)"})
    bank_units = tuple(u for g in groups for u in lists.bank[g])
    scored_units = tuple(u for g in groups for u in lists.scored[g])

    # the plan-time label reader on the PICKED units' rows only (bank units hold every scored unit)
    labels = plan_labels(census, tuple(bank_units) + tuple(scored_units), cadence, facts, withhold_before_step)
    labels.set_test_first_step(test_first_step)

    fit_units, fit_y = labels.fit_rows(scored_units, y0_step, inner_end_step)
    share = RR.constant_history_share(fit_units, fit_y)
    out["R12:constant_history_share"] = make_derived("R12", share, {
        "units": len(scored_units), "rows": int(len(fit_y)),
        "rows_scope": "valid labels of every group's scored units, Y0 to the inner-fit end, whose own "
                      "label window has ended by then",
        "report_only": True})

    if O._v(kind) == RouterKind.REGION.value:
        inner_fit_rows = labels.fit_row_counts(bank_units, y0_step, inner_end_step)
        test_fit_rows = labels.fit_row_counts(bank_units, y0_step, train_end_step)
        out["R14:region_fit"] = O._region_fit(groups, lists, inner_fit_rows, test_fit_rows)

    donor = labels.donor_labels(groups, train_end_step, CutKind.FIT, 0, bank_units, "bank_plan")
    out["R19"] = UR.derive_r19_bank_plan(donor, False)
    if K.INNER_CUT_BANK_REFIT:
        inner_cut = int(cuts[0].guard_cut)
        inner_donor = labels.donor_labels(groups, inner_cut, CutKind.GUARD, 0, bank_units,
                                          "bank_plan_inner_cut")
        out["R19:inner_cut"] = UR.derive_r19_inner_cut_bank_plan(inner_donor, False)
    out["R20"] = UR.derive_r20_batching(False, groups)
    out["R20:fallback_rows"] = O._fallback_rows(kind, groups, lists, labels, y0_step, cuts, donor)
    out["R21"] = UR.derive_r21_smoke_plan_loro(groups)

    out["R22"] = R.derive_r22_links(facts.target.legal_range, donor)
    if Link.LOG_C in out["R22"].value:
        bank_by_group = {g: lists.bank[g] for g in groups}
        for lead in sorted(cuts):
            cut = int(cuts[lead].fit_cut)
            view_l = labels.donor_labels(groups, cut, CutKind.FIT, lead, bank_units, "links")
            entry = R.derive_r23_c_for_cut(view_l)
            O._check_r23_plan_time(entry, lead, cut, labels.rebuild_donor_rows(bank_by_group, cut))
            out["R23:lead=%d" % lead] = entry
    out["R28"] = R.derive_r28_clip_bounds(facts.target.legal_range)

    O._require(share_reader, "measure", "R30 (the missing and real-zero shares)")
    shares = share_reader.measure(donor, out["R8"].value, tuple(windows.test_years))
    if getattr(shares, "donor_row_key_hash", None) != donor.row_key_hash:
        raise DeriveRefusal("R30", "the shares were measured on other rows (row-key hash %s, the donor "
                            "rows' %s)" % (getattr(shares, "donor_row_key_hash", None), donor.row_key_hash),
                            fix="measure the shares over the donor view derive_all passes")
    out["R30"] = UR.derive_r30_missing_flags(shares, facts.absent_groups)
    return out


def plan_labels(census: TargetCensus, units: Sequence[str], cadence: Any, facts: Any,
                withhold_before_step: Optional[int]) -> Any:
    """orchestrate._PlanLabels on the given units' full rows (census.read_units), labels before
    withhold_before_step read as NaN."""
    rows = census.read_units(units)
    steps = _steps.step_index(rows.time_columns, facts.time_facts, cadence)
    y = np.asarray(rows.y, dtype=np.float64)
    if withhold_before_step is not None:
        y = np.where(steps < int(withhold_before_step), np.nan, y)
    return O._PlanLabels(np.asarray(rows.unit_ids, dtype=object), np.asarray(rows.group_ids, dtype=object),
                         steps, y, cadence, facts.target)


def withheld_counts(census: TargetCensus, cadence: Any, target_facts: Any, before_step: int) -> Tuple[int, int]:
    """(rows, valid labels) at steps before before_step: R4:model_labels' record."""
    view = census.view(cadence, target_facts, None)
    cm = view.steps < int(before_step)
    if not cm.any():
        return 0, 0
    rows = valid = 0
    for a, b in census.unit_blocks():
        rows += int(census.bits("exist", a, b, cm).sum())
        valid += int(census.bits("valid", a, b, cm).sum())
    return rows, valid


__all__ = ["FileRows", "TableSource", "ReaderPresence", "TargetCensus", "scan_target", "census_ram_bytes",
           "CensusCheckpoint", "CensusCheckpointMismatch",
           "derive_all_streamed", "plan_labels", "withheld_counts", "sortable_keys", "percentile_ranks",
           "HIST_BITS", "COLLECT_CAP"]
