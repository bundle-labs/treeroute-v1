"""'check --deep': the data checks (plan 6.1; plan 8.1 M4), streamed file by file with bounded RAM.

Pass 1, one read of every store file of the checked groups, group by group (as derive/census.py streams the
target): the group's target files through the package's own target reader (pipeline.data.read_target), then
each driver file of that group, one at a time. Per driver file: its column set against its store catalog
(io.checks.check_column_set), the RAW values for G-SENTINEL's deep scan, the values masked at read
(io.sentinel.mask_sentinels) for G-RANGE, the 1:1 join of its keys onto the group's target rows
(io.joins.join_one_to_one: a duplicated key refuses, the row count is asserted) for G-JOIN, and on the
target-aligned values the missing shares per column x group x year (G-MISSING) and the declared-versus-
observed step on every unit (G-CADENCE). Counts are summed over files and decided once (guards.py).
The target rows of a year inside a store's record (its files' first to last year) for which the group has no
file, or of a group with no file at all, enter no join: they are counted as missing in the shares and as rows
without a file in G-JOIN, and G-MISSING (files) refuses the missing (group, year) files (io.checks.
check_missing_files on the target's years inside the store's record).
What is held: one group's target keys and labels, one driver file, the per-row presence bits of the stores a
run reads, and the per-column counts.
Which store refuses: read_plan applies the pipeline reader's own rule (each needed column is taken from the FIRST
driver store whose first file holds it). A store a run reads no column from has its join and column-set problems
FLAGGED (the run never joins it); a declared store with no file at all is refused, as the reader refuses it.

The windows (R3-R11), derived with the engine's own rules on the deep pass's rows, never estimated. Per target row
pass 1 keeps, for every store a run reads (read_plan), whether the store holds the row (the pipeline reader's
'present', pipeline.data.ColumnReader). Then: R3 (derive_r03_coverage_end) on the JOINED rows per group and year
(a valid label and every store holding a kept column or a kept output's source present, a declared-absent group
counting as present: count_valid_rows_per_group_year's rule, F2, F8); R4 (orchestrate._r04_entry: R8's lags plus
a declared lag operation's look-back, from the driver stores' first years, J5) on one row per (group, presence
bits) at its first year, as the streaming census does; R3 again on the years from Y0 (the pipeline withholds the
labels before Y0, C4); R5, R6, R7, R2, R10, R11 (derive_r11_cuts: timing.cuts_for_leads) and the cuts as days
(derive.rules.cut_days). The groups are the checked groups after split.yaml's exclusions. A rule that refuses
refuses the windows line, and every guard that reads the windows says it was not judged (no estimate replaces
it). Readers: G-EPOCH (every R11 cut), G-SUPPORT's donor values, G-RANGE's target rows, the no-all-zero-unit
flag and R30 (donor rows: the years Y0 to the train end; R30's test years: R5's), the G-HIST sample rows (at or
before the train end). derived.json is the authority; at a gate's size (a group subset) the windows are those of
the subset.

Pass 2, the sample: a stride sample of V1.check_sample_rows target rows (all rows if fewer) over the census
in group, unit, step order (D79, D92). The sampled units' rows are read again (target reader; driver files
read through the pipeline's own ColumnReader, which also runs the feature script on them), so: G-DERIVED
recomputes every declared output from its declaration (D93: the sample spans every row); G-HIST matches
every dataset column against the own target's look-backs, read only through the label vault, on the sample
rows at or before the donor train end; G-CALENDAR asserts the predecessor reads (on the grid's own keys: it
checks the engine's lookup, so package content cannot fail it; a row-shift lag in a package is caught by the
G-DERIVED recompute); G-LINEAGE tests the declared sum groups for a rebuildable banned member.

Which groups (owner ruling M2): the data passes check the package's R21 smoke groups,
the first C13.smoke_groups groups in sorted order after split.yaml's exclusions, chosen by the engine's own smoke
rule (report.smoke_group_selection -> derive.unit_rules.derive_r21_smoke_plan_loro), never a size knob: the
command takes none. The quick checks before them cover the whole package. The checked groups, how they were chosen
and the package's group count go into the 'deep groups (ruling M2)' line, ctx.deep_selection and the report's
checked_groups (report.py); the freeze accepts a deep report only on exactly those groups. Tests and gates may pass
'groups' (a subset of the package's groups); the report then says so, and the freeze refuses it unless the subset
is the R21 one. A full-size deep check (every group) is a side record only (ruling M2), never the freeze's gate.
"""
# Provenance: plan 5 (the deep guards), 6.1 (check --deep: "sentinels, units, ranges, observed step on ALL
# units, missingness per year, join integrity, engineered recompute, co-product and clock flags (years up to the
# donor end only)"), 8.1 M4; derive/census.py (the streamed read, the reduced R4 rows); plan 2.1 R3-R11;
# owner rulings A (D79, D92-D97), D, F (F2, F8), J5.

import time
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from treeroute import engine_constants as K
from treeroute.errors import RefusedError

from . import guards as G
from . import report as REP
from .facts import KEY_ROLES
from .quick import CheckContext, run_quick

GROUP_PLACEHOLDER = "group"
YEAR_PLACEHOLDER = "year"
_U, _T, _POS = "_unit_code", "_time", "_row"
# Columns read from one store file at a time (plumbing: it bounds the RAM of a wide file, never a number).
COLUMN_BLOCK = 32
# Bits of one int64 word in the per-unit year masks (plumbing: a longer record uses several words).
_WORD_BITS = 62
WINDOWS_LABEL = "windows (R3-R11)"
GROUPS_LABEL = "deep groups (ruling M2)"


def _v(x: Any) -> Any:
    return getattr(x, "value", x)


def _quiet(_text: str) -> None:
    return None


def _catalog_for(names: Sequence[str], stores: Mapping[str, Any]) -> Optional[Tuple[str, Any]]:
    """The included store catalog that declares most of a store file's columns (None when none does)."""
    best, best_n = None, 0
    for key, catalog in sorted(stores.items()):
        n = len(set(names) & set(catalog.columns))
        if n > best_n:
            best, best_n = (key, catalog), n
    return best


def declared_set(names: Sequence[str], facts: Any) -> Optional[Tuple[str, Tuple[str, ...]]]:
    """A store file's declared column set for io.checks.check_column_set: every column of its own store catalog
    (the included catalog that declares most of its columns: a declared column the files lack is refused), plus
    the file's columns that another included store catalog or the feature script declares (a package may take a
    store's facts from two catalogs: dataset.yaml says which), plus the package keys it holds. A column no catalog
    declares stays an extra column. None when no included catalog declares any of its columns."""
    found = _catalog_for(names, facts.loaded.stores)
    if found is None:
        return None
    elsewhere = set(facts.store_of) | set(facts.outputs)
    declared = tuple(found[1].columns) + tuple(c for c in names if c in elsewhere or c in facts.keys)
    return found[0], tuple(dict.fromkeys(declared))


def read_plan(ctx: CheckContext) -> Dict[str, Tuple[str, ...]]:
    """{driver store template: the columns a run reads from it}, by the pipeline reader's own rule
    (pipeline.data.ColumnReader: the entering columns, the sources of every feature-script output and the report
    strata, each taken from the FIRST driver store whose first file holds it). A store with no column here is never
    read by a run (its join and column-set findings are reported, not refused)."""
    from treeroute.pipeline import data as D

    facts = ctx.facts
    sources = sorted({s for c, o in facts.outputs.items() for s in (getattr(o, "derived_from", None) or ())})
    strata = [c for c, f in facts.columns.items() if f.role == D.STRATUM_ROLE]
    needed = [c for c in list(ctx.entering) + sources + strata if c not in facts.outputs and c not in facts.keys]
    remaining = list(dict.fromkeys(needed))
    plan: Dict[str, Tuple[str, ...]] = {}
    for template, _listing, names in ctx.store_listings:
        cols = tuple(c for c in remaining if c in names)
        plan[template] = plan.get(template, ()) + cols
        remaining = [c for c in remaining if c not in cols]
    return plan


def _absent_of(facts: Any, column: str) -> Dict[str, str]:
    """A column's absent_groups store fact (the merged catalog row, or the store catalog row of a column the
    package catalog does not list)."""
    f = facts.columns.get(column)
    if f is not None:
        return dict(f.absent_groups or {})
    key = facts.store_of.get(column)
    scol = facts.loaded.stores[key].columns.get(column) if key in facts.loaded.stores else None
    return dict(getattr(scol, "absent_groups", None) or {})


def presence_plan(ctx: CheckContext) -> SimpleNamespace:
    """The pipeline reader's driver stores (pipeline.data.ColumnReader.stores): every store a run reads a column
    from (read_plan, dataset.yaml order), with its absent groups (those every read column's store facts declare
    absent, as the reader intersects them) and which of them hold a kept column or a kept output's source
    (ColumnReader._stores_for over the kept columns: the stores F2's joined rows need). Bit b of a row's presence
    mask is store b."""
    facts = ctx.facts
    stores = []
    for template, cols in ctx.read_plan.items():
        if not cols:
            continue
        absent = frozenset.intersection(*[frozenset(_absent_of(facts, c)) for c in cols])
        stores.append((template, tuple(cols), absent))
    if len(stores) > _WORD_BITS:
        raise RefusedError("R3", "%d driver stores are read; the presence mask holds %d" % (len(stores), _WORD_BITS),
                           fix="internal: widen the presence mask")
    wanted = _wanted(facts, ctx.entering)
    kept_bits = tuple(b for b, (_, cols, _) in enumerate(stores) if wanted & set(cols))
    return SimpleNamespace(stores=tuple(stores), templates=tuple(s[0] for s in stores), kept_bits=kept_bits,
                           bit_of={s[0]: b for b, s in enumerate(stores)})


def _wanted(facts: Any, columns: Sequence[str]) -> set:
    """ColumnReader._stores_for's columns: a feature output stands for its sources."""
    out = set()
    for c in columns:
        if c in facts.outputs:
            out.update(getattr(facts.outputs[c], "derived_from", None) or ())
        else:
            out.add(c)
    return out


class _Counts(object):
    """Per-column counts summed over files, and the per (column, group, year) missing counts."""

    def __init__(self) -> None:
        self.sentinel: Dict[str, Dict[str, Any]] = {}
        self.range: Dict[str, Dict[str, Any]] = {}
        self.cadence: Dict[str, Dict[str, Any]] = {}
        self.missing: Dict[Tuple[str, str, int], List[int]] = {}      # rows, missing, zero
        self.reports: List[Any] = []
        self.column_set_ok: Dict[str, bool] = {}
        self.refusals: Dict[str, str] = {}
        self.store_rows_outside: Dict[str, int] = {}
        self.skipped_stores: Dict[str, str] = {}
        self.unused_stores: set = set()
        self.nofile: Dict[str, int] = {}                               # store label: target rows without a file
        self.presence_unknown: Dict[str, str] = {}                     # "template / group": why


class _Target(object):
    """Target statistics over every checked group: per year counts, the census, the per-unit year masks, the
    joined-row counts of R3 and the first year of each (group, presence mask) of R4."""

    def __init__(self) -> None:
        self.by_year: Dict[int, Dict[str, Any]] = {}
        self.census: List[Dict[str, Any]] = []
        self.unit_years: Dict[Tuple[int, int, int], int] = {}       # (base year, valid mask, nonzero mask): units
        self.units = 0
        self.rows = 0
        self.order: List[Tuple[str, Tuple[str, ...], np.ndarray]] = []    # (group, sorted units, rows per unit)
        self.refusals: Dict[str, str] = {}
        self.group_years: Dict[str, Tuple[int, ...]] = {}
        self.r3_counts: Dict[Tuple[str, int], int] = {}
        self.mask_first_year: Dict[Tuple[str, int], int] = {}
        self.held_rows: Dict[Tuple[str, str], int] = {}              # (store, group): target rows it holds

    def year(self, y: int) -> Dict[str, Any]:
        return self.by_year.setdefault(int(y), {"rows": 0, "valid": 0, "zero": 0, "below": 0, "above": 0,
                                                "at_bounds": 0, "distinct": set()})


def _target_frame(ctx: CheckContext, group: str, keep_units: Optional[Callable[[str, pd.DataFrame], Any]] = None
                  ) -> pd.DataFrame:
    from treeroute.pipeline import data as D

    facts = ctx.facts
    hook = D.load_hook(facts.loaded.root, D.TARGET_READER)
    return D.read_target(facts.loaded, ctx.spec, hook, ctx.target_listing, [group], keep_units=keep_units,
                         echo=_quiet)


def _year_masks(codes: np.ndarray, years: np.ndarray, rows: np.ndarray, n_units: int, base: int,
                span: int) -> List[np.ndarray]:
    """Per unit, the years (offset from base) of the selected rows as bit words of _WORD_BITS bits."""
    words = []
    k = years - base
    for w in range(0, max(1, -(-span // _WORD_BITS))):
        sel = rows & (k >= w * _WORD_BITS) & (k < (w + 1) * _WORD_BITS)
        out = np.zeros(n_units, dtype=np.int64)
        np.bitwise_or.at(out, codes[sel], np.left_shift(np.int64(1), (k[sel] - w * _WORD_BITS).astype(np.int64)))
        words.append(out)
    return words


def _target_pass(ctx: CheckContext, group: str, frame: pd.DataFrame, tstat: _Target) -> Dict[str, Any]:
    """The group's target rows: steps, unit codes, per-year label counts, the census summary, the per-unit
    years with a valid and with a non-zero label (the no-all-zero-unit flag is judged once the windows are
    known)."""
    from treeroute.io.steps import step_index
    from treeroute.pipeline import data as D

    facts = ctx.facts
    units = frame[facts.unit_col].to_numpy(dtype=object).astype(str)
    names, codes = np.unique(units, return_inverse=True)
    codes = np.asarray(codes, dtype=np.int64).reshape(-1)
    times = {c: frame[c].to_numpy(dtype=np.int64) for c in facts.time_facts}
    steps = step_index(times, facts.time_facts, ctx.cadence)
    years = np.asarray(D._years_of_steps(steps, ctx.cadence), dtype=np.int64)
    y = frame[facts.target.name].to_numpy(dtype=np.float64)
    lr = facts.target.legal_range
    valid = np.isfinite(y)
    for yr in np.unique(years).tolist():
        sel = years == yr
        v = y[sel & valid]
        slot = tstat.year(yr)
        slot["rows"] += int(sel.sum())
        slot["valid"] += int(v.size)
        slot["zero"] += int((v == 0).sum())
        if lr is not None:
            slot["below"] += int((v < float(lr[0])).sum())
            slot["above"] += int((v > float(lr[1])).sum())
            slot["at_bounds"] += int(((v == float(lr[0])) | (v == float(lr[1]))).sum())
        if len(slot["distinct"]) < 3 and v.size:
            slot["distinct"].update(np.unique(v)[:3].tolist())
    per_unit = np.bincount(codes, minlength=len(names))
    first = np.full(len(names), np.iinfo(np.int64).max)
    last = np.full(len(names), np.iinfo(np.int64).min)
    np.minimum.at(first, codes, steps)
    np.maximum.at(last, codes, steps)
    span = int(steps.max()) - int(steps.min()) + 1 if len(steps) else 1
    keys = np.sort(codes * span + (steps - (int(steps.min()) if len(steps) else 0)))
    dup = bool(keys.size > 1 and (keys[1:] == keys[:-1]).any())
    del keys
    tstat.census.append({"group": group, "units": len(names), "rows": int(len(codes)), "duplicates": bool(dup),
                         "first_min": int(first.min()), "first_max": int(first.max()), "last_min": int(last.min()),
                         "last_max": int(last.max()), "count_min": int(per_unit.min()), "count_max": int(per_unit.max())})
    if len(years):
        base, yspan = int(years.min()), int(years.max()) - int(years.min()) + 1
        vw = _year_masks(codes, years, valid, len(names), base, yspan)
        nw = _year_masks(codes, years, valid & (y != 0), len(names), base, yspan)
        stacked = np.stack(vw + nw, axis=1)
        pats, cnt = np.unique(stacked, axis=0, return_counts=True)
        nwords = len(vw)
        for row, n in zip(pats.tolist(), cnt.tolist()):
            vmask = sum(int(x) << (_WORD_BITS * i) for i, x in enumerate(row[:nwords]))
            nmask = sum(int(x) << (_WORD_BITS * i) for i, x in enumerate(row[nwords:]))
            key = (base, vmask, nmask)
            tstat.unit_years[key] = tstat.unit_years.get(key, 0) + int(n)
    tstat.units += len(names)
    tstat.rows += int(len(codes))
    tstat.order.append((group, tuple(names.tolist()), per_unit.astype(np.int64)))
    tstat.group_years[group] = tuple(int(v) for v in np.unique(years).tolist())
    return {"names": names, "codes": codes, "steps": steps, "years": years, "valid": valid}


def _key_facts(facts: Any, columns: Sequence[str]) -> Dict[str, Any]:
    out = {}
    for c in columns:
        f = facts.columns.get(c)
        if f is not None and f.role not in KEY_ROLES:
            out[c] = f
        else:
            out[c] = SimpleNamespace(role="key_unit", fill_values=(), near_sentinel_optout=True)
    return out


def _data_columns(facts: Any, names: Sequence[str]) -> List[str]:
    return [c for c in names if c in facts.columns and facts.columns[c].role not in KEY_ROLES
            and facts.columns[c].role not in ("target", "target_twin")]


def _driver_file(ctx: CheckContext, group: str, template: str, listing: Any, key: Any, path: str, tg: Dict[str, Any],
                 counts: _Counts, held: Optional[np.ndarray] = None, keys_only: bool = False) -> None:
    """One driver file: column set (footer), the join of its keys onto the group's target rows (once), then the
    data columns in blocks of COLUMN_BLOCK (bounded RAM): raw sentinels, masked ranges, missing shares and
    cadence counts on the target-aligned values. held (a store a run reads): the target rows the file holds are
    marked (the reader's 'present'); a join that cannot be made leaves the store's presence unknown for the group.
    keys_only: the join for held alone (a store without a {group} placeholder, read again for another group)."""
    import pyarrow.parquet as pq

    from treeroute.io.checks import check_column_set
    from treeroute.io.joins import join_one_to_one
    from treeroute.io.readers import read_footer
    from treeroute.io.sentinel import mask_sentinels
    from treeroute.io.steps import step_index

    facts = ctx.facts
    names = tuple(str(c) for c in read_footer(path).names)
    label = "store %s" % template
    where = "%s / %s" % (template, group)
    if not keys_only:
        found = declared_set(names, facts)
        if found is not None:
            try:
                check_column_set(names, found[1], "%s (%s)" % (template, found[0]))
                counts.column_set_ok.setdefault(label, True)
            except RefusedError as exc:
                counts.column_set_ok[label] = False
                counts.refusals.setdefault("column set of " + label, str(exc))
        if not ctx.read_plan.get(template):
            counts.unused_stores.add(label)
    data_cols = [] if keys_only else _data_columns(facts, names)
    if not data_cols and held is None:
        if not keys_only:
            counts.skipped_stores.setdefault(label, "no column with package facts")
        return
    if facts.unit_col not in names:
        text = "the store file %s holds no unit key %r" % (path, facts.unit_col)
        counts.refusals.setdefault("join " + label, text)
        if held is not None:
            counts.presence_unknown.setdefault(where, text)
        return
    parts = [c for c in facts.time_facts if c in names]
    key_cols = [facts.unit_col] + parts
    keys = pq.read_table(path, columns=key_cols).to_pandas()
    # the keys: the store's unit ids in the group's code space; the step (same parts as the target) or the year
    names_sorted = tg["names"]
    sunits = keys[facts.unit_col].to_numpy(dtype=object).astype(str)
    scode = np.searchsorted(names_sorted, sunits)
    inside = scode < len(names_sorted)
    inside[inside] = names_sorted[scode[inside]] == sunits[inside]
    if not keys_only:
        counts.store_rows_outside[label] = counts.store_rows_outside.get(label, 0) + int((~inside).sum())
    by_step = set(parts) == set(facts.time_facts)
    year_parts = [c for c in parts if facts.time_facts[c] == "year"]
    joined_ok = True
    if not by_step and year_parts != parts:
        text = "time columns %s: neither the target's %s nor a year" % (parts, list(facts.time_facts))
        counts.refusals.setdefault("join " + label, text)
        if held is not None:
            counts.presence_unknown.setdefault(where, text)
        joined_ok = False
    if joined_ok:
        if by_step:
            stime = step_index({c: keys[c].to_numpy() for c in parts}, {c: facts.time_facts[c] for c in parts},
                               ctx.cadence)
            ttime = tg["steps"]
        else:
            stime = keys[year_parts[0]].to_numpy(dtype=np.int64) if year_parts else np.zeros(len(keys), np.int64)
            ttime = tg["years"]
        tsel = np.ones(len(ttime), dtype=bool)
        kd = dict(zip(listing.key_names, key))
        if YEAR_PLACEHOLDER in kd:
            tsel = tg["years"] == int(kd[YEAR_PLACEHOLDER])
        lrows = np.flatnonzero(tsel)
        left_codes, left_time = tg["codes"][lrows], ttime[lrows]
        inverse = None
        if not by_step and left_codes.size:
            tmin = int(left_time.min())
            span = int(left_time.max()) - tmin + 1
            ukeys, inverse = np.unique(left_codes * span + (left_time - tmin), return_inverse=True)
            inverse = np.asarray(inverse).reshape(-1)
            left_codes = ukeys // span
            left_time = ukeys - left_codes * span + tmin
        left = pd.DataFrame({_U: left_codes, _T: left_time})
        right = pd.DataFrame({_U: scode[inside].astype(np.int64), _T: np.asarray(stime)[inside].astype(np.int64),
                              _POS: np.flatnonzero(inside).astype(np.float64)})
        what = "%s file %s onto the target of %s" % (label, path, group)
        try:
            joined, rep = join_one_to_one(left, right, (_U, _T), what)
            if not keys_only:
                counts.reports.append(rep)
        except RefusedError as exc:
            counts.refusals.setdefault("join " + label, str(exc))
            if held is not None:
                counts.presence_unknown.setdefault(where, str(exc))
            joined_ok = False
    if joined_ok:
        pos = joined[_POS].to_numpy()
        if inverse is not None:
            pos = pos[inverse]
        matched = np.isfinite(pos)
        if held is not None:
            held[lrows[matched]] = True
        if keys_only:
            return
        take = np.where(matched, pos, 0).astype(np.int64)
        years = tg["years"][lrows]
        steps = tg["steps"][lrows]
        codes = tg["codes"][lrows]
        uyears, yi = np.unique(years, return_inverse=True)
        yi = np.asarray(yi).reshape(-1)
        per_year = np.bincount(yi, minlength=len(uyears))
    cache: Dict[Any, Any] = {}
    for b in range(0, len(data_cols), COLUMN_BLOCK):
        block = data_cols[b:b + COLUMN_BLOCK]
        raw = pq.read_table(path, columns=block).to_pandas()
        G.add_counts(counts.sentinel, G.sentinel_counts(raw, facts.columns))
        masked, _ = mask_sentinels(raw, {c: facts.columns[c] for c in block})
        del raw
        G.add_counts(counts.range, G.range_counts(masked, facts.columns))
        if not joined_ok:
            continue
        for c in block:
            v = masked[c].to_numpy(dtype=np.float64)[take]
            v[~matched] = np.nan
            miss = np.bincount(yi, weights=(~np.isfinite(v)).astype(np.float64), minlength=len(uyears))
            zero = np.bincount(yi, weights=(v == 0).astype(np.float64), minlength=len(uyears))
            for j, yr in enumerate(uyears.tolist()):
                slot = counts.missing.setdefault((c, group, int(yr)), [0, 0, 0])
                slot[0] += int(per_year[j])
                slot[1] += int(miss[j])
                slot[2] += int(zero[j])
            G.add_counts(counts.cadence, G.cadence_counts(pd.DataFrame({c: v}), codes, steps, facts.columns,
                                                          ctx.cadence, cache=cache))


def _store_record(listing: Any) -> Optional[Tuple[int, int]]:
    """A store's record: the first and last year its files hold (its {year} placeholder over every group), or
    None for a store without a {year} placeholder."""
    if YEAR_PLACEHOLDER not in listing.key_names or not listing.files:
        return None
    i = listing.key_names.index(YEAR_PLACEHOLDER)
    years = [int(k[i]) for k, _ in listing.files]
    return min(years), max(years)


def _no_file_rows(ctx: CheckContext, group: str, listing: Any, names: Sequence[str], template: str,
                  tg: Dict[str, Any], counts: _Counts) -> None:
    """The group's target rows for which a {group} store holds no file: the years inside the store's record
    (_store_record) with no file of the group, or every year when the group has no file at all (a store without
    a {year} placeholder). They enter no join; they count as missing in the shares of the store's columns and as
    rows without a file in G-JOIN."""
    if not listing.files or GROUP_PLACEHOLDER not in listing.key_names:
        return
    gi = listing.key_names.index(GROUP_PLACEHOLDER)
    mine = [k for k, _ in listing.files if str(k[gi]) == group]
    uy, cnt = np.unique(tg["years"], return_counts=True)
    record = _store_record(listing)
    if record is not None:
        yi = listing.key_names.index(YEAR_PLACEHOLDER)
        have = {int(k[yi]) for k in mine}
        gone = {int(y): int(n) for y, n in zip(uy.tolist(), cnt.tolist())
                if record[0] <= int(y) <= record[1] and int(y) not in have}
    elif not mine:
        gone = {int(y): int(n) for y, n in zip(uy.tolist(), cnt.tolist())}
    else:
        return
    if not gone:
        return
    label = "store %s" % template
    if group in _store_absent(ctx.facts, template, ctx.read_plan.get(template, ()), names)[1]:
        label += " (groups its store facts declare absent, F8)"
    counts.nofile[label] = counts.nofile.get(label, 0) + sum(gone.values())
    for c in _data_columns(ctx.facts, names):
        for yr, n in gone.items():
            slot = counts.missing.setdefault((c, group, yr), [0, 0, 0])
            slot[0] += n
            slot[1] += n


def _presence(ctx: CheckContext, group: str, tg: Dict[str, Any], held: Mapping[str, np.ndarray],
              tstat: _Target) -> None:
    """The group's joined-row counts per year for R3 (count_valid_rows_per_group_year's rule: a valid label and
    every store holding a kept column present, a store that declares the group absent counting as present, F2,
    F8) and the first year of each presence mask for R4 (the census's reduced rows)."""
    plan = ctx.presence
    n = len(tg["years"])
    present = np.ones(n, dtype=bool)
    for b in plan.kept_bits:
        template, _, absent = plan.stores[b]
        if group not in absent:
            present &= held[template]
    keep = tg["valid"] & present
    uy, cnt = np.unique(tg["years"][keep], return_counts=True)
    for yr, c in zip(uy.tolist(), cnt.tolist()):
        tstat.r3_counts[(group, int(yr))] = tstat.r3_counts.get((group, int(yr)), 0) + int(c)
    masks = np.zeros(n, dtype=np.int64)
    for b, (template, _, _) in enumerate(plan.stores):
        masks |= held[template].astype(np.int64) << b
        tstat.held_rows[(template, group)] = int(held[template].sum())
    if n:
        um, inv = np.unique(masks, return_inverse=True)
        first = np.full(len(um), np.iinfo(np.int64).max, dtype=np.int64)
        np.minimum.at(first, np.asarray(inv).reshape(-1), tg["years"])
        for m, fy in zip(um.tolist(), first.tolist()):
            tstat.mask_first_year[(group, int(m))] = int(fy)


def _r30_flags(ctx: CheckContext, counts: _Counts, win: Any) -> Any:
    """R30's rule (derive.unit_rules.derive_r30_missing_flags, called as it is) on the deep pass's shares of the
    STORED kept tree features: donor rows = every checked unit's rows of the years Y0 to the train end (not the
    bank units of D16), test years R5's, unlagged and before the last-value rule. derived.json's R30 is the
    authority."""
    from treeroute.derive.rules import PICKED_SCOPE
    from treeroute.derive.shapes import MissingShares
    from treeroute.derive.unit_rules import derive_r30_missing_flags

    trees = set(ctx.column_sets.tree_features)
    agg: Dict[str, List[int]] = {}
    by_year: Dict[Tuple[str, int], List[int]] = {}
    for (c, g, yr), (rows, miss, zero) in counts.missing.items():
        if c not in trees:
            continue
        if win.y0 <= yr <= win.train_end:
            a = agg.setdefault(c, [0, 0, 0])
            a[0] += rows
            a[1] += miss
            a[2] += zero
        if yr in win.test_years:
            b = by_year.setdefault((c, yr), [0, 0])
            b[0] += rows
            b[1] += miss
    miss_share = {c: (a[1] / float(a[0]) if a[0] else 0.0) for c, a in agg.items()}
    zero_share = {c: (a[2] / float(a[0]) if a[0] else 0.0) for c, a in agg.items()}
    test_share = {k: (b[1] / float(b[0]) if b[0] else 0.0) for k, b in by_year.items() if k[0] in miss_share}
    shares = MissingShares(donor_row_key_hash="check --deep: every checked unit's rows from Y0 to the train end",
                           donor_unit_scope=PICKED_SCOPE, donor_training_missing_share=miss_share,
                           donor_training_zero_share=zero_share, test_year_missing_share=test_share)
    absent = {c: dict(ctx.facts.columns[c].absent_groups or {}) for c in miss_share}
    return derive_r30_missing_flags(shares, absent)


class _MaskPresence(object):
    """drivers_present over the reduced R4 rows (one per group and presence mask), as the column reader answers
    it (pipeline.data.ColumnReader.drivers_present: every store holding one of the columns, or a source of a feature
    output among them, holds the row; a group the store declares absent counts as present, F8). The same reading
    as the streaming census's _MaskReader."""

    def __init__(self, ctx: CheckContext, masks: Sequence[int], groups: Sequence[str]) -> None:
        self._ctx, self._masks, self._groups = ctx, list(masks), list(groups)

    def drivers_present(self, unit_ids: Any, group_ids: Any, time_columns: Any, columns: Sequence[str]) -> np.ndarray:
        plan = self._ctx.presence
        wanted = _wanted(self._ctx.facts, columns)
        bits = [b for b, (_, cols, _) in enumerate(plan.stores) if wanted & set(cols)]
        return np.array([all(((m >> b) & 1) or g in plan.stores[b][2] for b in bits)
                         for m, g in zip(self._masks, self._groups)], dtype=bool)


def derive_windows(ctx: CheckContext, tstat: _Target, counts: _Counts, run_groups: Sequence[str]) -> SimpleNamespace:
    """R3-R7, R2, R10, R11 and the cuts as days, by the engine's own rules on the deep pass's rows (module
    docstring). Refuses (RefusedError, the rule's own) whatever a rule refuses, and before them: a group whose
    target read refused; a store a run reads whose join could not be made for a group (its presence is unknown), an
    entering time-varying column
    without an R8 lag (G-LAG reports it), an irregular target (the event rules are M8)."""
    from treeroute.derive import rules as R
    from treeroute.derive.orchestrate import _r04_entry

    facts = ctx.facts
    if _v(getattr(ctx.cadence, "kind", None)) == "irregular":
        raise RefusedError("R3", "an irregular (event) target: the plan-time event rules are milestone M8",
                           fix="not built yet for events")
    if tstat.refusals:
        raise RefusedError("R3", "the target of %d groups was refused at read (see the G-SENTINEL (deep) line), so "
                           "their rows cannot be counted: %s" % (len(tstat.refusals), G._fmt(sorted(tstat.refusals), 4)),
                           fix="fix the target store first")
    unknown = dict(counts.presence_unknown)
    if unknown:
        raise RefusedError("R3", "the joined rows are unknown: %d (store / group) joins could not be made: %s"
                           % (len(unknown), G._fmt(["%s: %s" % kv for kv in sorted(unknown.items())], 2)),
                           fix="fix the G-JOIN refusals of the stores a run reads")
    unlagged = sorted(c for c, f in ctx.entering.items()
                      if G._cadence_kind(f) not in G.UNLAGGED_KINDS and c not in ctx.lags)
    if unlagged:
        raise RefusedError("R4", "R8 gives no lag for %d entering time-varying columns (G-LAG): %s; R4's Y0 needs "
                           "every lag" % (len(unlagged), G._fmt(unlagged)), fix="fix G-LAG first")
    allowed = set(ctx.groups)
    groups = tuple(sorted(g for g in run_groups if g in allowed and g in tstat.group_years))
    if not groups:
        raise RefusedError("R3", "no checked group is left after split.yaml's exclusions and the target reads",
                           fix="check the target store and split.yaml")
    counts3 = {k: n for k, n in tstat.r3_counts.items() if k[0] in groups}
    empty = [g for g in groups if not any(k[0] == g for k in counts3)]
    if empty:
        holes = []
        for template, _, absent in (ctx.presence.stores[b] for b in ctx.presence.kept_bits):
            none = [g for g in empty if g not in absent and not tstat.held_rows.get((template, g), 0)]
            if none:
                holes.append("%s holds no row of %s" % (template, G._fmt(none, 4)))
        raise RefusedError("R3", "%d groups have no joined row (a valid label with every store holding a kept "
                           "column present, F2): %s%s" % (len(empty), G._fmt(empty, 4),
                                                           (" (" + "; ".join(holes) + ")") if holes else ""),
                           fix="build or restore the stores the kept columns live in for these groups, or declare "
                               "the groups absent in their store facts")
    first_pass = R.derive_r03_coverage_end(counts3, groups, False)
    # R4 on one row per (group, presence mask) at its first year (derive/census.py r04_rows)
    keys = sorted(k for k in tstat.mask_first_year if k[0] in groups)
    r_groups = np.array([g for g, _ in keys], dtype=object)
    r_masks = [m for _, m in keys]
    r_years = np.array([tstat.mask_first_year[k] for k in keys], dtype=np.int64)
    r_units = np.array(["census_row_%d" % i for i in range(len(keys))], dtype=object)
    target_first = min(min(tstat.group_years[g]) for g in groups)
    store = {c: f for c, f in facts.columns.items() if f.has_store_facts}
    facts_ns = SimpleNamespace(store=store, absent_groups={c: _absent_of(facts, c) for c in ctx.entering})
    package_ns = SimpleNamespace(stores=dict(facts.loaded.stores))
    r4 = _r04_entry(package_ns, facts_ns, ctx.lags, _MaskPresence(ctx, r_masks, r_groups), r_units, r_groups, {},
                    r_years, target_first)
    y0 = int(r4.value)
    # C4: the labels before Y0 are withheld (the pipeline's second derive pass), so R3 counts the years from Y0
    counts_model = {k: n for k, n in counts3.items() if k[1] >= y0}
    r3 = R.derive_r03_coverage_end(counts_model, groups, False) if counts_model != counts3 else first_pass
    y_end = int(r3.value)
    r5 = R.derive_r05_test_window(y0, y_end)
    r6 = R.derive_r06_train_end(r5.value.test_years)
    r7 = R.derive_r07_inner_windows(y0, y_end, r5.value, r6.value)
    r2 = R.derive_r02_season_key(ctx.cadence, getattr(ctx.cadence, "composites_per_year", None))
    r10 = R.derive_r10_leads(r2.value, False)
    r11 = R.derive_r11_cuts(r7.value, r10.value, ctx.cadence)
    days = R.cut_days(r11.value, ctx.cadence)
    w = r7.value
    text = ("Y0 %d (R4%s), Y_end %d (R3 on the joined rows of %d groups%s), test years %s (R5%s), train end %d "
            "(R6), inner fit %d-%d and inner score %s (R7), leads %s (R10), %d cuts (R11: every lead's fit and guard "
            "cut), the earliest %s; derived on the deep pass's rows (derived.json is the authority)"
            % (y0, ", flags %s" % list(r4.flags) if r4.flags else "", y_end, len(groups),
               "; the first pass, before the labels before Y0 are withheld, gave %d" % int(first_pass.value)
               if int(first_pass.value) != y_end else "", list(w.test_years),
               ", %s" % list(r5.flags) if r5.flags else "", int(r6.value), w.inner_fit[0], w.inner_fit[1],
               list(w.inner_score), [0] + list(r10.value.leads), 2 * len(days),
               G._day_text(min(min(d.fit_cut_day, d.guard_cut_day) for d in days.values()))))
    details = {"y0": y0, "y_end": y_end, "test_years": list(w.test_years), "train_end": int(r6.value),
               "inner_fit": list(w.inner_fit), "inner_score": list(w.inner_score),
               "leads": list(r10.value.leads), "groups": list(groups), "r4_flags": list(r4.flags),
               "r4_set_by": r4.inputs.get("set_by"), "r4_driver_stores": r4.inputs.get("driver_stores"),
               "r3_first_pass": int(first_pass.value), "r3_margins": dict(r3.margins or {}),
               "cuts": {str(lead): {"fit_cut_day": G._day_text(d.fit_cut_day), "guard_cut_day":
                                    G._day_text(d.guard_cut_day)} for lead, d in days.items()},
               "joined_rows_per_group_year": {"%s/%d" % k: n for k, n in sorted(counts_model.items())}}
    return SimpleNamespace(y0=y0, y_end=y_end, test_years=tuple(int(t) for t in w.test_years),
                           train_end=int(r6.value), cut_days=days, text=text, details=details)


def _all_zero_units(tstat: _Target, win: Any) -> int:
    """Units whose valid labels in the donor years (Y0 to the train end) are all zero (and that have one)."""
    n = 0
    for (base, vmask, nmask), units in tstat.unit_years.items():
        lo, hi = max(win.y0 - base, 0), win.train_end - base
        if hi < lo:
            continue
        window = ((1 << (hi + 1)) - 1) ^ ((1 << lo) - 1)
        if vmask & window and not nmask & window:
            n += units
    return n


def _sample_positions(tstat: _Target) -> List[Tuple[str, str, int]]:
    """The stride sample (D79, D92): V1.check_sample_rows rows evenly spaced over the census in group, unit,
    step order (all rows if fewer). Returns (group, unit, step offset within the unit) triples."""
    total = tstat.rows
    m = min(int(K.CHECK_SAMPLE_ROWS), total)
    if m <= 0:
        return []
    picks = (np.arange(m, dtype=np.int64) * total) // m
    out = []
    base = 0
    i = 0
    for group, units, per_unit in tstat.order:
        n = int(per_unit.sum())
        ends = base + np.cumsum(per_unit)
        while i < m and picks[i] < base + n:
            u = int(np.searchsorted(ends, picks[i], side="right"))
            start = int(ends[u] - per_unit[u])
            out.append((group, units[u], int(picks[i] - start)))
            i += 1
        base += n
    return out


def _sample_pass(ctx: CheckContext, tstat: _Target, win: Any, add: Callable[[str, Any], None],
                 echo: Callable[[str], None]) -> None:
    """Pass 2: G-DERIVED recompute, G-HIST sample, G-CALENDAR, G-LINEAGE reconstructions on the stride sample.
    win None (the windows refused): the G-HIST sample is not judged (it reads labels only at or before the train
    end, which is unknown)."""
    from treeroute import timing
    from treeroute.io.steps import build_dense_grid, predecessor_index, step_index
    from treeroute.pipeline import data as D
    from treeroute.pipeline.stages import build_vault

    facts = ctx.facts
    picks = _sample_positions(tstat)
    if not picks:
        for label in ("G-DERIVED (recompute)", "G-HIST (sample)", "G-CALENDAR", "G-LINEAGE (deep)"):
            add(label, G.result(label.split(" ")[0], G.BLOCK, (), "no target row to sample"))
        return
    wanted: Dict[str, set] = {}
    for g, u, _ in picks:
        wanted.setdefault(g, set()).add(u)
    frames = []
    for g in sorted(wanted):
        frames.append(_target_frame(ctx, g, keep_units=lambda grp, fr, s=wanted[g]: sorted(s)))
    tframe = pd.concat(frames, ignore_index=True)
    try:
        spec_full = D.package_spec(D.augment_package(facts.loaded, facts.outputs))
    except RefusedError as exc:
        text = "not evaluated: the pipeline's column reader needs the closed world first (%s)" % exc
        for label in ("G-DERIVED (recompute)", "G-HIST (sample)", "G-LINEAGE (deep)"):
            add(label, G.result(label.split(" ")[0], G.BLOCK, (), text, fix="fix G-CLOSED first"))
        spec_full = None
    units = tframe[facts.unit_col].to_numpy(dtype=object).astype(str)
    groups = tframe[facts.group_col].to_numpy(dtype=object).astype(str)
    times = {c: tframe[c].to_numpy(dtype=np.int64) for c in facts.time_facts}
    steps = step_index(times, facts.time_facts, ctx.cadence)
    lo, hi = int(steps.min()), int(steps.max())
    try:
        grid = build_dense_grid(units, groups, steps, (lo, hi))
    except RefusedError as exc:
        for label in ("G-DERIVED (recompute)", "G-HIST (sample)", "G-CALENDAR", "G-LINEAGE (deep)"):
            add(label, G.result(label.split(" ")[0], G.BLOCK, (), "not evaluated: the sampled units are not a "
                                "complete census (%s)" % exc, fix="grid the target to unit x step"))
        return
    n = int(grid.n_steps)
    row_of = {u: i for i, u in enumerate(grid.unit_ids)}
    unit_rows = np.array([row_of[u] for u in units.tolist()], dtype=np.int64)
    pos = unit_rows * n + (steps - lo)
    size = len(grid.unit_ids) * n
    sample = np.array(sorted({row_of[u] * n + off for g, u, off in picks}), dtype=np.int64)
    echo("check --deep sample: %d rows of %d units (stride over %d census rows)" % (sample.size, len(grid.unit_ids),
                                                                                  tstat.rows))

    def on_grid(values: Any) -> np.ndarray:
        out = np.full(size, np.nan)
        out[pos] = np.asarray(pd.to_numeric(pd.Series(values), errors="coerce"), dtype=np.float64)
        return out

    # G-CALENDAR: the predecessor reads every lag of the package needs, on the grid's own keys (it checks the
    # engine's lookup; a package's own row-shift lag is the G-DERIVED recompute's to catch)
    grid_unit = np.repeat(np.arange(len(grid.unit_ids), dtype=np.int64), n)
    grid_step = np.tile(np.arange(lo, lo + n, dtype=np.int64), len(grid.unit_ids))
    ks = sorted({int(l.steps) for l in ctx.lags.values() if int(l.steps) > 0
                 and G._same_cadence(l.column_cadence, ctx.cadence)})
    cal = []
    for k in ks:
        src = predecessor_index(grid_unit, grid_step, k)
        rows = sample[src[sample] >= 0]
        cal.append(G.check_g_calendar(grid_unit[src[rows]], grid_step[src[rows]], grid_unit[rows], grid_step[rows],
                                      k, False))
    if cal:
        status = G.worst(r.status for r in cal)
        add("G-CALENDAR", G.result("G-CALENDAR", status, (), "lags %s: %s" % (ks, "; ".join(
            r.reason for r in cal if r.status is not G.PASS) or "every predecessor read of %d sample rows is in its "
            "own unit and exactly k steps back (the engine's lookup; package content is checked by the G-DERIVED "
            "recompute)" % sample.size), fix=cal[0].fix,
            details={"lags": ks, "reads": int(sum(r.details.get("reads", 0) for r in cal))}))
    else:
        add("G-CALENDAR", G.result("G-CALENDAR", G.PASS, (), "no same-step lag to read (every lag is 0)"))
    if spec_full is None:
        return
    # the reader reads the entering columns and the feature sources; the declared sum-group members that do not
    # enter are added to its read list (only read, never a feature) so the reconstruction test sees them
    import dataclasses

    extra = tuple(sorted(c for c, f in facts.columns.items() if getattr(f, "sum_group", None) and f.has_store_facts
                         and c not in spec_full.tree_features and c not in spec_full.context
                         and f.store != "features/build.py"))
    spec_read = dataclasses.replace(spec_full, tree_features=tuple(spec_full.tree_features) + extra)
    import warnings

    with warnings.catch_warnings():
        # the reader inserts one column at a time; pandas' fragmentation notice (speed only) would print once per
        # column on a wide package and bury the guard lines. Only that warning class is silenced, only here.
        warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
        reader = D.ColumnReader(D.augment_package(facts.loaded, facts.outputs), spec_read, tframe, ctx.cadence,
                                facts.hook, echo=_quiet)
    # G-DERIVED: recompute every declared output from its declaration
    outputs = {c: facts.columns[c] for c in facts.outputs if c in facts.columns}
    if outputs:
        needed = sorted({s for c in outputs for s in facts.columns[c].derived_from})
        src = {}
        for s in needed:
            if s in reader.raw.columns:
                src[s] = on_grid(reader.raw[s].to_numpy())
            elif s in times:
                src[s] = on_grid(times[s])
        script = pd.DataFrame({c: on_grid(reader.raw[c].to_numpy()) for c in outputs if c in reader.raw.columns})
        add("G-DERIVED (recompute)", G.check_g_derived(outputs, script, sample, grid, None, pd.DataFrame(src), None,
                                                        target_cadence=ctx.cadence))
    else:
        add("G-DERIVED (recompute)", G.result("G-DERIVED", G.PASS, (), "no feature script output to recompute"))
    # G-HIST: dataset columns against the own target's look-backs, through the label vault, at or before the
    # train end only (the vault is opened up to it: no test-window label is read)
    if win is None:
        add("G-HIST (sample)", G.result("G-HIST", G.BLOCK, (), "not evaluated: the sample reads labels only at or "
                                        "before the donor train end, and the windows could not be derived (see the "
                                        "%s line)" % WINDOWS_LABEL, fix="fix the windows line first"))
    else:
        y = tframe[facts.target.name].to_numpy(dtype=np.float64)
        test_first = int(timing.year_last_step(win.train_end, ctx.cadence)) + 1
        vg = build_vault(units, groups, steps, y, (lo, hi), test_first, ctx.cadence, facts.target, None)
        hist_rows = sample[grid_step[sample] < test_first]
        dataset_cols = [c for c in ctx.entering if c in reader.raw.columns]
        values = pd.DataFrame({c: on_grid(reader.raw[c].to_numpy()) for c in dataset_cols})
        hist = G.check_g_hist_sample({c: facts.columns[c] for c in dataset_cols}, values, vg.grid, vg.labels,
                                     hist_rows, target_cadence=ctx.cadence)
        add("G-HIST (sample)", G.result("G-HIST", hist.status, hist.columns, hist.reason + " (%d sample rows at or "
                                        "before the train end %d)" % (hist_rows.size, win.train_end), hist.fix,
                                        hist.part, hist.details))
    # G-LINEAGE (deep): declared sum groups on the sample rows
    members = sorted({c for c, f in facts.columns.items() if getattr(f, "sum_group", None)} & set(reader.raw.columns))
    frame = pd.DataFrame({c: on_grid(reader.raw[c].to_numpy())[sample] for c in members})
    add("G-LINEAGE (deep)", G.flag_lineage_reconstructions(frame, facts.columns, ctx.facts.loaded.ban.verdicts))


def _prepare(ctx: CheckContext) -> None:
    ctx.read_plan = read_plan(ctx)
    ctx.presence = presence_plan(ctx)


def _files_of_group(listing: Any, group: str, first: bool) -> List[Tuple[Any, str]]:
    """A store's files for one group; a store without a {group} placeholder is read once, with the first group."""
    if GROUP_PLACEHOLDER not in listing.key_names:
        return list(listing.files) if first else []
    i = listing.key_names.index(GROUP_PLACEHOLDER)
    return [(k, p) for k, p in listing.files if k[i] == group]


def _group_pass(ctx: CheckContext, group: str, first: bool) -> Tuple[str, Any, Any]:
    """Pass 1 for one group: its target files, then every driver file of the group (one file at a time), the rows
    a store holds no file for, and the presence counts of R3 and R4."""
    counts, tstat = _Counts(), _Target()
    try:
        frame = _target_frame(ctx, group)
    except RefusedError as exc:
        tstat.refusals[group] = str(exc)
        return group, counts, tstat
    tg = _target_pass(ctx, group, frame, tstat)
    del frame
    n = len(tg["years"])
    held = {t: np.zeros(n, dtype=bool) for t in ctx.presence.templates}
    for template, listing, names in ctx.store_listings:
        grouped = GROUP_PLACEHOLDER in listing.key_names
        if grouped or first:
            for key, path in _files_of_group(listing, group, first):
                _driver_file(ctx, group, template, listing, key, path, tg, counts, held=held.get(template))
        elif template in held:
            # a store without a {group} placeholder serves every group: its keys are joined again for presence
            for key, path in listing.files:
                _driver_file(ctx, group, template, listing, key, path, tg, counts, held=held[template],
                             keys_only=True)
        _no_file_rows(ctx, group, listing, names, template, tg, counts)
    _presence(ctx, group, tg, held, tstat)
    return group, counts, tstat


def _merge(counts: "_Counts", tstat: "_Target", c: "_Counts", t: "_Target") -> None:
    """Add one group's counts into the totals (sums of integers and unions of sets: order-free)."""
    G.add_counts(counts.sentinel, c.sentinel)
    G.add_counts(counts.range, c.range)
    G.add_counts(counts.cadence, c.cadence)
    for k, v in c.missing.items():
        slot = counts.missing.setdefault(k, [0, 0, 0])
        for i in range(3):
            slot[i] += v[i]
    counts.reports.extend(c.reports)
    for k, ok in c.column_set_ok.items():
        counts.column_set_ok[k] = counts.column_set_ok.get(k, True) and ok
    for k, v in c.refusals.items():
        counts.refusals.setdefault(k, v)
    for k, v in c.store_rows_outside.items():
        counts.store_rows_outside[k] = counts.store_rows_outside.get(k, 0) + v
    for k, v in c.skipped_stores.items():
        counts.skipped_stores.setdefault(k, v)
    counts.unused_stores |= c.unused_stores
    for k, v in c.nofile.items():
        counts.nofile[k] = counts.nofile.get(k, 0) + v
    for k, v in c.presence_unknown.items():
        counts.presence_unknown.setdefault(k, v)
    for yr, s in t.by_year.items():
        slot = tstat.year(yr)
        for k in ("rows", "valid", "zero", "below", "above", "at_bounds"):
            slot[k] += s[k]
        for value in sorted(s["distinct"]):
            if len(slot["distinct"]) < 3:
                slot["distinct"].add(value)
    tstat.census.extend(t.census)
    for k, v in t.unit_years.items():
        tstat.unit_years[k] = tstat.unit_years.get(k, 0) + v
    tstat.units += t.units
    tstat.rows += t.rows
    tstat.order.extend(t.order)
    tstat.refusals.update(t.refusals)
    tstat.group_years.update(t.group_years)
    for k, v in t.r3_counts.items():
        tstat.r3_counts[k] = tstat.r3_counts.get(k, 0) + v
    for k, v in t.mask_first_year.items():
        tstat.mask_first_year[k] = min(v, tstat.mask_first_year.get(k, v))
    tstat.held_rows.update(t.held_rows)


_WORKER: Dict[str, Any] = {}


def _init_worker(package_path: str) -> None:
    """A pass-1 worker process: its own quick pass (the package's facts, listings and R1), read once."""
    ctx = run_quick(package_path, echo=_quiet)
    _prepare(ctx)
    _WORKER["ctx"] = ctx


def _worker_group(group: str, first: bool) -> Tuple[str, Any, Any]:
    return _group_pass(_WORKER["ctx"], group, first)


def _store_absent(facts: Any, template: str, read: Sequence[str], names: Sequence[str]) -> Tuple[List[str], Dict[str, str]]:
    """The columns that decide a store's missing files (the columns a run reads from it, or its data columns when
    no run reads it) and the groups every one of them declares absent."""
    cols = list(read) if read else [c for c in names if c in facts.columns and facts.columns[c].role not in KEY_ROLES]
    absent: Dict[str, str] = {}
    for c in cols:
        for g, reason in _absent_of(facts, c).items():
            absent.setdefault(g, reason)
    absent = {g: r for g, r in absent.items() if all(g in _absent_of(facts, c) for c in cols)}
    return cols, absent


def _missing_files(ctx: CheckContext, run_groups: Sequence[str], tstat: Optional[_Target] = None) -> Any:
    """G-MISSING (files): every declared driver store holds at least one file (the pipeline reader refuses an empty
    store before it looks at any column); every store with a {group} placeholder holds a file for every checked
    group; and, after pass 1 (tstat given), every store with a {group} and a {year} placeholder holds a file for
    every (group, year) of the target inside the store's record (its files' first to last year), for the groups it
    holds any file of. A missing pair refuses unless the store facts of the columns a run reads from it declare the
    group absent (io.checks.check_missing_files on (group, year) pairs from the target). A store no run reads
    (read_plan) is reported, not refused."""
    from treeroute.io.checks import check_missing_files

    facts = ctx.facts
    refused, noted, absent_seen = [], [], []
    for template, listing, names in ctx.store_listings:
        if not listing.files:
            refused.append("driver store %s holds no file (the reader refuses an empty declared store)" % template)
            continue
        if GROUP_PLACEHOLDER not in listing.key_names:
            continue
        gi = listing.key_names.index(GROUP_PLACEHOLDER)
        read = ctx.read_plan.get(template, ())
        used = bool(read)
        cols, absent = _store_absent(facts, template, read, names)
        if not cols:
            continue
        checks = [({(str(k[gi]), 0) for k, _ in listing.files}, {(g, 0) for g in run_groups}, template)]
        record = _store_record(listing)
        if tstat is not None and record is not None:
            yi = listing.key_names.index(YEAR_PLACEHOLDER)
            found = {(str(k[gi]), int(k[yi])) for k, _ in listing.files}
            holding = {g for g, _ in found}
            expected = {(g, y) for g in run_groups if g in holding for y in tstat.group_years.get(g, ())
                        if record[0] <= y <= record[1]}
            checks.append((found, expected, "%s (years %d-%d)" % (template, record[0], record[1])))
        for found, expected, name in checks:
            try:
                rep = check_missing_files(expected, found, absent, name)
                if rep.absent_by_fact:
                    absent_seen.append("%s: %d (group, period) pairs declared absent" % (name, len(rep.absent_by_fact)))
            except RefusedError as exc:
                text = str(exc).replace("[G-MISSING] ", "", 1)
                if getattr(exc, "fix", None):
                    text = text.replace(" Fix: %s" % exc.fix, "")
                (refused if used else noted).append(text)
    details = {"declared_absent": absent_seen, "years_checked": tstat is not None}
    if refused:
        return G.result("G-MISSING", G.BLOCK, (), "; ".join(refused + noted), part=None, details=details,
                        fix="restore the files, or declare the group in the store's absent_groups with a reason")
    if noted:
        return G.result("G-MISSING", G.FLAG, (), "stores a run reads no column from miss files: %s"
                        % "; ".join(noted), fix="remove an unused store from dataset.yaml, or complete it",
                        details=details)
    return G.result("G-MISSING", G.PASS, (), "every driver store holds a file for every checked group%s%s"
                    % (" and every target year inside its record" if tstat is not None else "",
                       (" (" + "; ".join(absent_seen) + ")") if absent_seen else ""), details=details)


def _probe_minutes(ctx: CheckContext, run_groups: Sequence[str], n_workers: int) -> Optional[float]:
    """The expected minutes of pass 1, before it starts: one target file and the first file of each driver store of
    the first group are read and checked exactly as pass 1 does (results thrown away), each time multiplied by its
    store's file count over the checked groups, divided by the workers. A file read through a reader that refuses
    gives no estimate (None); the refusal is reported by pass 1 itself."""
    from treeroute.pipeline import data as D

    facts = ctx.facts
    if not run_groups:
        return None
    group = run_groups[0]
    try:
        t0 = time.time()
        key, path = D._files_of(ctx.target_listing, [group])[0]
        hook = D.load_hook(facts.loaded.root, D.TARGET_READER)
        kd = dict(zip(ctx.target_listing.key_names, key))
        reader = getattr(hook, "read_target_file", None) if hook is not None else None
        frame = reader(path, kd) if reader is not None else D._read_target_generic(path, kd, ctx.spec)
        if facts.group_col not in frame.columns:
            frame[facts.group_col] = group
        tg = _target_pass(ctx, group, frame, _Target())
        total = (time.time() - t0) * len(D._files_of(ctx.target_listing, run_groups))
        for template, listing, _ in ctx.store_listings:
            files = _files_of_group(listing, group, True)
            if not files:
                continue
            t1 = time.time()
            _driver_file(ctx, group, template, listing, files[0][0], files[0][1], tg, _Counts())
            n = sum(len(_files_of_group(listing, g, i == 0)) for i, g in enumerate(run_groups))
            total += (time.time() - t1) * n
        return total / n_workers / 60.0
    except (RefusedError, KeyError, IndexError, ValueError):
        return None


def _not_judged(res: Any, why: str) -> Any:
    """A guard whose window-dependent part could not run: its own findings stand, a PASS becomes a FLAG, and the
    reason says what was not judged."""
    status = G.FLAG if res.status is G.PASS else res.status
    return G.result(res.rule_id, status, res.columns, res.reason + "; " + why, res.fix or "fix the windows line first",
                    res.part, res.details)


def deep_group_selection(ctx: CheckContext, groups: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """The checked_groups record of the deep pass (report.py). groups None (the command): ruling M2, R21's smoke
    groups of the package's groups after split.yaml's exclusions (report.smoke_group_selection; when R21 refuses,
    the record carries the refusal and no group). groups given (tests and gates only): that subset, recorded as
    given by the caller; it must be distinct names of the package's groups (ValueError otherwise)."""
    package_groups, data_groups = tuple(ctx.groups), tuple(ctx.data_groups)
    if groups is None:
        try:
            return REP.smoke_group_selection(package_groups, data_groups)
        except RefusedError as exc:
            return REP.refused_selection(package_groups, data_groups, str(exc))
    if isinstance(groups, str):
        raise ValueError("groups is a sequence of group names, got the string %r" % (groups,))
    names = tuple(groups)
    unknown = sorted(set(names) - set(package_groups))
    if not names or unknown or len(set(names)) != len(names):
        raise ValueError("groups must be distinct names of the package's groups after split.yaml's exclusions; got "
                         "%r (not among them: %s)" % (names, unknown or "none"))
    return REP.caller_selection(names, package_groups, data_groups)


def _groups_line(selection: Mapping[str, Any]) -> Any:
    """The 'deep groups (ruling M2)' line: pass on the ruling-M2 subset, a flag on a caller-given subset (the freeze
    refuses that report unless its groups are exactly the R21 smoke groups), a refusal when R21 refuses (no group is
    checked)."""
    text = REP.selection_text(selection)
    if selection["refused"]:
        return G.result(REP.M2_RULE, G.BLOCK, (), "no group checked: " + text,
                        fix="the package needs at least C15.min_groups groups after split.yaml's exclusions",
                        details=dict(selection))
    if selection["selection"] != REP.M2_SELECTION:
        return G.result(REP.M2_RULE, G.FLAG, (), text + "; not chosen by the ruling-M2 rule, so the freeze refuses "
                        "this report unless these groups are exactly the package's R21 smoke groups",
                        fix="run 'check --deep' (the command checks the ruling-M2 subset)",
                        details=dict(selection))
    return G.result(REP.M2_RULE, G.PASS, (), text + "; the quick checks above cover the whole package",
                    details=dict(selection))


def run_deep(package_path: Any, echo: Callable[[str], None] = print, groups: Optional[Sequence[str]] = None,
             ctx: Optional[CheckContext] = None, workers: Optional[int] = None) -> CheckContext:
    """The quick checks (the whole package), then the two deep passes on the ruling-M2 groups (deep_group_selection:
    R21's smoke groups; ctx.deep_selection holds the record the report writes as checked_groups). groups (gates and
    tests only) checks that subset instead and the record says so; the command passes None. workers (tests only)
    overrides V5.check_deep_workers; pass 1's results are integer counts and sets merged per group, so the number
    of worker processes cannot change any of them (a test checks 1 against 2)."""
    from treeroute.pipeline import data as D

    if ctx is None:
        ctx = run_quick(package_path, echo=echo)
    facts = ctx.facts
    results = ctx.results

    def add(label: str, res: Any) -> None:
        results.append((label, res))

    ctx.deep_groups = ()
    selection = deep_group_selection(ctx, groups)
    if ctx.target_listing is None or ctx.cadence is None or facts.target is None:
        ctx.deep_selection = REP.refused_selection(ctx.groups, ctx.data_groups, "the deep pass cannot read the target "
                                                   "as one regular grid (see the G-SUPPORT (deep) line)")
        add("G-SUPPORT (deep)", G.result("G-SUPPORT", G.BLOCK, (), "the deep pass cannot read the target as one "
                                         "regular grid (the target store, R1's cadence on its first file, or the "
                                         "target column is missing; see the R1 and G-SUPPORT lines): a presence-only "
                                         "or holed table is refused", fix="grid it to unit x step with zeros"))
        return ctx
    ctx.deep_selection = selection
    echo("check --deep: " + REP.selection_text(selection))
    add(GROUPS_LABEL, _groups_line(selection))
    if selection["refused"]:
        return ctx
    _prepare(ctx)
    run_groups = tuple(selection["groups"])
    ctx.deep_groups = run_groups
    n_target = len(D._files_of(ctx.target_listing, run_groups))
    n_driver = sum(len(_files_of_group(listing, g, i == 0)) for template, listing, _ in ctx.store_listings
                   for i, g in enumerate(run_groups))
    n_workers = max(1, min(int(workers if workers is not None else K.CHECK_DEEP_WORKERS), len(run_groups)))
    est = _probe_minutes(ctx, run_groups, n_workers)
    echo("check --deep: %d groups, %d target files, %d driver files, %d worker processes; expected time for pass 1: "
         "about %s min (timed on one file of each store), then the sample pass reads the sampled units again; a "
         "second estimate follows the first group" % (len(run_groups), n_target, n_driver, n_workers,
                                                      "?" if est is None else "%.0f" % est))
    counts, tstat = _Counts(), _Target()
    t0 = time.time()
    done = 0

    def merged(part: Tuple[str, Any, Any]) -> None:
        nonlocal done
        _merge(counts, tstat, part[1], part[2])
        done += 1
        if done == 1:
            spent = time.time() - t0
            echo("check --deep: the first group took %.0f s; expected time for pass 1: about %.0f min (%d groups over "
                 "%d workers), plus the sample pass" % (spent, spent * len(run_groups) / n_workers / 60.0,
                                                        len(run_groups), n_workers))
    if n_workers == 1:
        for gi, group in enumerate(run_groups):
            merged(_group_pass(ctx, group, gi == 0))
    else:
        import concurrent.futures as cf
        import multiprocessing as mp

        with cf.ProcessPoolExecutor(max_workers=n_workers, mp_context=mp.get_context("spawn"),
                                    initializer=_init_worker, initargs=(str(package_path),)) as pool:
            futures = [pool.submit(_worker_group, group, gi == 0) for gi, group in enumerate(run_groups)]
            for fut in futures:                  # in group order: the merge is order-free, the echo is not
                merged(fut.result())
    tstat.census.sort(key=lambda c: c["group"])
    tstat.order.sort(key=lambda o: o[0])
    echo("check --deep: pass 1 done in %.0f s" % (time.time() - t0))
    add("G-MISSING (files)", _missing_files(ctx, run_groups, tstat))

    # the windows (R3-R11) by the engine's rules on the joined rows
    try:
        win = derive_windows(ctx, tstat, counts, run_groups)
        add(WINDOWS_LABEL, G.result("R3-R11", G.PASS, (), win.text, details=win.details))
        echo("check --deep: windows: %s" % win.text)
    except RefusedError as exc:
        win = None
        add(WINDOWS_LABEL, G.refusal_result(exc, None, "the windows cannot be derived on the deep pass's rows, so "
                                            "the guards that read the donor train end or R11's cuts are not judged: "))
    ctx.windows = win
    ctx.train_end = None if win is None else win.train_end
    no_win = "not judged: the windows could not be derived (see the %s line)" % WINDOWS_LABEL
    te_text = ("donor years %d-%d (Y0 to the train end, R4-R6 on the deep pass's rows; derived.json is the authority)"
               % (win.y0, win.train_end)) if win is not None else no_win

    # G-SENTINEL (target refusals too), G-RANGE, G-CADENCE, G-JOIN, G-MISSING (deep)
    sent = G.decide_sentinel(counts.sentinel)
    if tstat.refusals:
        sent = G.result("G-SENTINEL" if any("G-SENTINEL" in t for t in tstat.refusals.values()) else "G-SUPPORT",
                        G.BLOCK, (), "the target of %d groups was refused at read: %s" % (
                            len(tstat.refusals), G._fmt(["%s: %s" % kv for kv in sorted(tstat.refusals.items())], 2)),
                        fix="the ingest writes invalid labels as NaN (D30)", details=sent.details)
    add("G-SENTINEL (deep)", sent)
    donor = None
    distinct: set = set()
    if win is not None:
        donor = {k: 0 for k in ("nonmissing", "below", "above", "at_bounds")}
        for yr, s in tstat.by_year.items():
            if win.y0 <= yr <= win.train_end:
                donor["nonmissing"] += s["valid"]
                donor["below"] += s["below"]
                donor["above"] += s["above"]
                donor["at_bounds"] += s["at_bounds"]
                distinct.update(s["distinct"])
        donor["name"] = facts.target.name
    rng = G.decide_range(counts.range, facts.columns, donor)
    if win is not None:
        add("G-RANGE", G.result("G-RANGE", rng.status, rng.columns, rng.reason + "; target: " + te_text, rng.fix,
                                rng.part, rng.details))
    else:
        add("G-RANGE", _not_judged(rng, "the target's donor rows are " + no_win))
    add("G-CADENCE", G.decide_cadence(counts.cadence, entering=set(ctx.entering)))

    def _unused(key: str) -> bool:
        return any(key.endswith(label) for label in counts.unused_stores)

    blocking = {k: v for k, v in counts.refusals.items() if not _unused(k)}
    noted = {k: v for k, v in counts.refusals.items() if _unused(k)}
    sets_ok = {k: ok for k, ok in counts.column_set_ok.items() if ok or not _unused(k)}
    add("G-JOIN", G.check_g_join(tuple(counts.reports), sets_ok, blocking, noted, rows_without_file=counts.nofile))
    shares = {k: (v[1] / float(v[0]) if v[0] else 0.0) for k, v in counts.missing.items()}
    absent = {c: dict(f.absent_groups or {}) for c, f in facts.columns.items()}
    add("G-MISSING (deep)", G.check_g_missing_deep(shares, absent))

    # G-SUPPORT with the data
    if tstat.census:
        gmin = min(c["first_min"] for c in tstat.census)
        gmax = max(c["last_max"] for c in tstat.census)
        span = gmax - gmin + 1
        holed = [c["group"] for c in tstat.census if c["duplicates"] or c["first_min"] != gmin or c["first_max"] != gmin
                 or c["last_min"] != gmax or c["last_max"] != gmax or c["count_min"] != span or c["count_max"] != span]
        complete = not holed
    else:
        complete, holed = False, list(run_groups)
    zero_units = _all_zero_units(tstat, win) if win is not None else None
    sup = G.check_g_support(SimpleNamespace(y=np.array(sorted(distinct), dtype=np.float64),
                                            n_rows=donor["nonmissing"]) if donor is not None else None,
                            complete, False, None, len(ctx.groups), len(ctx.groups),
                            None if zero_units is None else zero_units > 0)
    extra = "" if complete else " Groups with census holes (rows missing for some unit x step between the first and " \
                                "last step of the store): %s." % G._fmt(holed)
    details = dict(sup.details, census=tstat.census[:20], all_zero_units=zero_units,
                   train_end=None if win is None else win.train_end)
    if win is not None:
        add("G-SUPPORT (deep)", G.result("G-SUPPORT", sup.status, sup.columns, sup.reason + extra + " " + te_text,
                                         sup.fix, sup.part, details))
    else:
        reason = sup.reason.replace(G.SUPPORT_DONOR_NOT_JUDGED + "; ", "").replace(G.SUPPORT_DONOR_NOT_JUDGED, "")
        sup = G.result("G-SUPPORT", sup.status, sup.columns, reason.rstrip("; ") + extra, sup.fix, sup.part, details)
        add("G-SUPPORT (deep)", _not_judged(sup, "the donor values and the all-zero units are " + no_win))

    # G-MISSING (R30's rule on the deep shares) and G-EPOCH at every R11 cut
    if win is None:
        add("G-MISSING", G.result("G-MISSING", G.BLOCK, (), "R30's flags are " + no_win + " (R30 reads the donor "
                                  "years and R5's test years)", fix="fix the windows line first"))
    else:
        try:
            r30 = _r30_flags(ctx, counts, win)
            miss = G.check_g_missing(r30, facts.loaded.ban.verdicts)
            add("G-MISSING", G.result("G-MISSING", miss.status, miss.columns, miss.reason + " (R30's rule on the deep "
                                      "pass's shares of the stored kept tree features, unlagged, every checked unit; "
                                      "feature-script outputs are not measured here; derived.json R30 is the "
                                      "authority; %s; test years %s)" % (te_text, list(win.test_years)), miss.fix,
                                      miss.part, miss.details))
        except RefusedError as exc:
            add("G-MISSING", G.result("G-MISSING", G.BLOCK, (), "R30's rule refused the deep shares: %s" % exc))
    if win is not None:
        ep = G.check_g_epoch(facts.columns, facts.loaded.ban.verdicts, win.cut_days, facts.target, win.train_end,
                             facts.loaded.exceptions.entries)
        add("G-EPOCH", G.result("G-EPOCH", ep.status, ep.columns, ep.reason + "; cuts: R11 (timing.cuts_for_leads) "
                                "of the windows line, each as its last day (derive.rules.cut_days); train end %d (R6)"
                                % win.train_end, ep.fix, ep.part, ep.details))
    else:
        ep = G.check_g_epoch(facts.columns, facts.loaded.ban.verdicts, {}, facts.target, None,
                             facts.loaded.exceptions.entries)
        add("G-EPOCH", G.result("G-EPOCH", G.BLOCK, ep.columns, "the comparison with R11's cuts and the target's "
                                "train-end rule are " + no_win + "; without a cut: " + ep.reason,
                                "fix the windows line first" + ("; " + ep.fix if ep.status is G.BLOCK else ""),
                                ep.part, ep.details))

    # pass 2
    t1 = time.time()
    try:
        _sample_pass(ctx, tstat, win, add, echo)
    except RefusedError as exc:
        add("sample pass", G.refusal_result(exc, None, "the sample pass's reader refused, so the G-DERIVED recompute, "
                                            "the G-HIST sample match and the G-LINEAGE reconstruction test did not "
                                            "run: "))
    echo("check --deep: sample pass done in %.0f s" % (time.time() - t1))
    if facts.hook_source is not None:
        add("G-DERIVED", G.scan_feature_script(facts.hook_source))
    # the deep results replace the quick placeholders of the same label
    latest: Dict[str, Any] = {}
    for label, res in results:
        latest[label] = res
    seen = set()
    merged_results = []
    for label, res in reversed(results):
        if label in seen:
            continue
        seen.add(label)
        merged_results.append((label, latest[label]))
    ctx.results = list(reversed(merged_results))
    return ctx


__all__ = ["run_deep", "deep_group_selection", "derive_windows", "read_plan", "presence_plan", "declared_set",
           "GROUPS_LABEL"]
