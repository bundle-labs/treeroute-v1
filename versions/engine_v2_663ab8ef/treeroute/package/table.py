"""The table option's package contract: the ready-row tables a table package supplies, read and checked.

Owner ruling U (the owner rulings file, section U, U1-U6); design in SPEC_TABLE_MODE.md sections 1-3.3.
A table package (dataset.yaml ``input: table``) supplies ONE ROW PER SAMPLE: its group, its package unit, its
target date, its label, its features and its train / test mark, in one parquet file per lead (lead 0 plus
R10's leads, in days), each lead's features already ending before that lead's issue date. The engine computes
no lag and runs no package code for a table (U1); it checks the dates it can check (section 2.1 of the spec)
and records what the package vouches for (U2).

What this module holds (boilerplate and checks only; no rule computes a number here):
  - TABLE_KEY_ROLES: the nine key roles of a table (the three grid key roles and the six table-only roles of
    package/schema.py). They are KEY roles: never a tree feature, never a verdict. They are split off before
    io.apply.apply_verdicts, which refuses an unknown role; no shared KEY_ROLES tuple is edited.
  - table_spec(package): the PackageSpec-shaped facts a TablePipeline reads (roles, tree features, router
    context, strata, legal range, listed columns, frozen columns), with the target-fact rules of section 1.5.
  - table_leads(): lead 0 plus R10's event leads (derive.rules.derive_r10_leads on the event season key).
  - read_tables(...): every lead file read whole, checked (T-FILES ... T-FINITE, T-LEADSET; T-MARK runs in
    derive/table.py, after R5), the excluded groups dropped, and the rows laid out in the ROW GRID order:
    each sample row is the engine's unit, so the rows become a keys-only DenseGrid with one step
    (io.steps.build_dense_grid, rows sorted by row id in plain code-point order, D37).
Each refusal is a RefusedError naming its check id and rule id (fail loudly).
"""
# Provenance for the module: OWNER_RULINGS_2026-10-06.md U1 (a generic table option; the package supplies ready
# rows, one table per lead; the engine skips the grid-only steps and keeps simple date checks), U2 (the package
# owner vouches for the features; the engine cannot recompute them), I1 (event leads 183 and 365 days);
# SPEC_TABLE_MODE.md 1.1-1.7, 2.1, 3.3; io/steps.py build_dense_grid (the keys-only grid), days_to_ordinals.

import glob
import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from treeroute import engine_constants as K
from treeroute.errors import RefusedError
from treeroute.package import schema as S

TABLE_KEY_ROLES = ("key_row", "key_unit", "key_group", "key_lat", "key_lon", "key_time", "key_issue",
                   "key_feature_end", "key_mark")
ROLE_ROW, ROLE_UNIT, ROLE_GROUP = "key_row", "key_unit", "key_group"
ROLE_LAT, ROLE_LON, ROLE_TIME = "key_lat", "key_lon", "key_time"
ROLE_ISSUE, ROLE_FEATURE_END, ROLE_MARK = "key_issue", "key_feature_end", "key_mark"
TARGET_ROLE = "target"
STRATUM_ROLE = "report_stratum"
TREE_ROLES = ("driver", "engineered")
CONTEXT_ROLE = "router_context"
CALENDAR_DATE = "date"
MARK_TRAIN, MARK_TEST = "train", "test"
MARKS = (MARK_TRAIN, MARK_TEST)
# The saved-row names a package-unit or stratum column may not take (report/metrics.py RESERVED_COLUMNS and the
# column prefixes of the saved rows, report/metrics.py ARM_PREFIX, PLACEBO_PREFIX, PRE_PREFIX, BASELINE_PREFIX):
# T-NAMES (SPEC_TABLE_MODE.md 2.1, rule R34)
SAVED_PREFIXES = ("arm__", "placebo__", "pre__", "base__")
# Section 1.5: the only target window a table accepts (the target date is the label's last content day)
TABLE_TARGET_STAMP = "event_date"
TABLE_TARGET_WINDOW = {"length": 1.0, "unit": "day", "align": "backward"}
# Section 1.7, ruling U2: what the package owner vouches for (written into plan.json and run_record.json)
U2_VOUCHED = (
    "U2: features vouched by the package owner (owner ruling U2); the engine recomputes none of them",
    "1. every feature and context value of a lead-L row uses only content dated strictly before its issue date, "
    "in the source's own day convention (publication delay disclosed per source in exceptions.yaml)",
    "2. no feature reads the row's own label, a label of any test row, or any label dated on or after the issue "
    "date",
    "3. the issue date equals the target date minus L days (checked by the engine: T-ISSUE)",
    "4. the same row id means the same sample, with the same label, in every lead file (checked: T-LEADSET)",
    "5. the target date is the label's last content day",
    "6. key_feature_end is the last content day any of the row's feature windows may read; the engine checks "
    "that it is before the issue day on every row (T-FEATEND) but cannot check that the declaration is true",
    "the G-DERIVED recompute and the look-ahead canary are not run on tables (U2)")
_SHOW = 5


class TableRefusal(RefusedError):
    """A table contract check refused (T-FILES ... T-MARK; fail loudly)."""


def _v(x: Any) -> Any:
    return getattr(x, "value", x)


def _first(values: Sequence[Any]) -> List[Any]:
    return list(values)[:_SHOW]


# ---------------------------------------------------------------------------------------------------
# The package facts a table run reads (PackageSpec-shaped: pipeline/data.py PackageSpec's fields, plus the key
# column names of the nine table key roles)
@dataclass(frozen=True)
class TableSpec:
    """The catalog's roles and where each non-key column goes, for a table package. unit_col is the ROW column
    (the engine unit is the sample row); package_unit_col is the package's own unit (R12, overlap blocks,
    persistence and reports)."""
    unit_col: str
    group_col: str
    time_facts: Mapping[str, str]
    target_col: str
    legal_range: Tuple[float, float]
    measurement_error_floor: Optional[float]
    roles: Mapping[str, str]
    store_facts: Mapping[str, Any]
    tree_features: Tuple[str, ...]
    context: Tuple[str, ...]
    frozen: Tuple[str, ...]
    listed_in_reports: Tuple[str, ...]
    feature_outputs: Tuple[str, ...]
    strata: Tuple[str, ...]
    row_col: str
    package_unit_col: str
    lat_col: str
    lon_col: str
    time_col: str
    issue_col: str
    feature_end_col: str
    mark_col: str
    columns: Tuple[str, ...]                 # every catalog column, in catalog order


# is_table_package (the guarded dispatch read) lives in package/load.py, which every grid run already loads, so
# the dispatch adds no module to a grid run's record (FIX_REPORT.md, grid-identity item 1); re-exported here.
from treeroute.package.load import is_table_package  # noqa: E402


def table_spec(package: Any) -> TableSpec:
    """The table facts of a loaded table package (SPEC_TABLE_MODE.md 1.3-1.5).

    Refuses (rule ids in the messages): a package that is not input: table; a key role declared other than
    exactly once; a key_time column whose calendar_part is not 'date'; no or several target columns; a target
    without legal_range or legal_range_source; a target window or stamp other than none or exactly stamp
    event_date with window {1 day, backward} and no reach; a package-unit or stratum column named like a saved
    column (T-NAMES); whatever io.apply.apply_verdicts refuses on the non-key columns (G-CLOSED)."""
    from treeroute.io.apply import apply_verdicts

    if package.dataset.input != S.INPUT_TABLE:
        raise TableRefusal("U1", "package %s is not a table package (dataset.yaml input: %s)"
                           % (package.dataset.name, package.dataset.input))
    cols = package.catalog.columns
    roles = {c: _v(f.role) for c, f in cols.items()}

    def one(role: str) -> str:
        found = [c for c, r in roles.items() if r == role]
        if len(found) != 1:
            raise TableRefusal("U1", "a table package declares exactly one %s column; found %d %s"
                               % (role, len(found), _first(found)))
        return found[0]

    names = {role: one(role) for role in TABLE_KEY_ROLES}
    target = one(TARGET_ROLE)
    time_col = names[ROLE_TIME]
    part = _v(cols[time_col].calendar_part)
    if part != CALENDAR_DATE:
        raise TableRefusal("R1", "the table's key_time column %s has calendar_part %r; a table's target date is "
                           "one column with calendar_part: date" % (time_col, part))
    tf = cols[target]
    if tf.legal_range is None or not tf.legal_range_source:
        raise TableRefusal("R22", "the table target %s needs legal_range and legal_range_source (section 1.5)"
                           % target, fix="cite the label's documented valid range")
    if tf.window is not None or tf.stamp is not None:
        w = tf.window
        ok = (tf.stamp == TABLE_TARGET_STAMP and w is not None and w.length is not None
              and float(w.length) == TABLE_TARGET_WINDOW["length"] and w.unit == TABLE_TARGET_WINDOW["unit"]
              and w.align == TABLE_TARGET_WINDOW["align"] and w.reach_after_max is None
              and w.reach_before_max is None and w.max_length is None)
        if not ok:
            raise TableRefusal("R11", "in a table the target date is the label's last content day; the target %s "
                               "may carry only stamp: event_date with window {length: 1, unit: day, align: "
                               "backward} and no reach" % target, fix="move the date instead (section 1.5)")
    strata = tuple(c for c in cols if roles[c] == STRATUM_ROLE)
    reserved = _reserved_names()
    for c in (names[ROLE_UNIT],) + strata:
        if c in reserved or c.startswith(SAVED_PREFIXES):
            raise TableRefusal("R34", "T-NAMES: column %r is saved beside the predictions under its catalog name, "
                               "so it may not be a reserved saved column %s or start with %s"
                               % (c, sorted(reserved), list(SAVED_PREFIXES)), fix="rename the column")
    non_key = tuple(c for c in cols if roles[c] not in TABLE_KEY_ROLES)
    sets = apply_verdicts(non_key, dict(package.ban.verdicts), {c: roles[c] for c in non_key})
    return TableSpec(unit_col=names[ROLE_ROW], group_col=names[ROLE_GROUP], time_facts={time_col: CALENDAR_DATE},
                     target_col=target, legal_range=(float(tf.legal_range[0]), float(tf.legal_range[1])),
                     measurement_error_floor=tf.measurement_error_floor, roles=dict(roles), store_facts={},
                     tree_features=tuple(sets.tree_features), context=tuple(sets.router_context),
                     frozen=tuple(sets.frozen), listed_in_reports=tuple(sets.listed_in_reports),
                     feature_outputs=(), strata=strata, row_col=names[ROLE_ROW],
                     package_unit_col=names[ROLE_UNIT], lat_col=names[ROLE_LAT], lon_col=names[ROLE_LON],
                     time_col=time_col, issue_col=names[ROLE_ISSUE], feature_end_col=names[ROLE_FEATURE_END],
                     mark_col=names[ROLE_MARK], columns=tuple(cols))


def _reserved_names() -> Tuple[str, ...]:
    from treeroute.report import metrics as M

    return tuple(M.RESERVED_COLUMNS)


def table_leads() -> Tuple[int, ...]:
    """Lead 0 and R10's event leads in days (owner ruling I1: 183 and 365): derive.rules.derive_r10_leads on
    the event season key, the one rule that sets them."""
    from treeroute.derive import rules as R
    from treeroute.derive.shapes import SeasonKeyKind, SeasonKeySpec

    plan = R.derive_r10_leads(SeasonKeySpec(kind=SeasonKeyKind.EVENT_MONTH, steps_per_year=None), True).value
    return (0,) + tuple(sorted(int(x) for x in plan.leads))


# ---------------------------------------------------------------------------------------------------
# The files
def lead_template(package: Any) -> str:
    """The target template as an absolute path text (relative templates are under the package folder)."""
    t = str(package.dataset.stores.target)
    p = Path(t)
    if not p.is_absolute():
        p = Path(package.root) / t
    return str(p).replace("\\", "/")


def lead_files(package: Any, leads: Sequence[int]) -> Dict[int, str]:
    """T-FILES (U1): the lead files are exactly lead 0 and R10's leads. A missing file refuses, and so does any
    other file that matches the template's glob (an unknown lead)."""
    template = lead_template(package)
    want = {int(L): template.replace(S.LEAD_PLACEHOLDER, "%d" % int(L)) for L in leads}
    missing = sorted(L for L, p in want.items() if not os.path.isfile(p))
    if missing:
        raise TableRefusal("U1", "T-FILES: the lead file(s) of lead %s are missing (%s)"
                           % (missing, [want[L] for L in missing][:_SHOW]),
                           fix="write one file per lead: lead 0 and R10's leads %s" % list(leads))
    pattern = glob.escape(template).replace(glob.escape(S.LEAD_PLACEHOLDER), "*")
    found = sorted(str(Path(p)).replace("\\", "/") for p in glob.glob(pattern))
    expected = {str(Path(p)).replace("\\", "/") for p in want.values()}
    extra = [p for p in found if p not in expected]
    if extra:
        raise TableRefusal("U1", "T-FILES: file(s) %s match the target template but are not a lead of R10 %s"
                           % (extra[:_SHOW], list(leads)), fix="remove them, or rename them out of the template")
    return want


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def table_ram_bytes(package: Any, spec: TableSpec, leads: Sequence[int]) -> Tuple[int, Dict[int, int]]:
    """The plan-time RAM estimate (SPEC_TABLE_MODE.md 3.3): rows x columns x 8 bytes, summed over the lead
    files (parquet footers only). Returns (bytes, rows per lead)."""
    import pyarrow.parquet as pq

    files = lead_files(package, leads)
    rows = {L: int(pq.ParquetFile(p).metadata.num_rows) for L, p in files.items()}
    return int(sum(rows.values()) * len(spec.columns) * 8), rows


# ---------------------------------------------------------------------------------------------------
# The read
@dataclass
class LeadTable:
    """One lead's rows, in row-grid order (one entry per row position of the lead-0 rows)."""
    lead: int
    present: np.ndarray                     # bool: the row has an issue row at this lead
    issue_day: np.ndarray                   # int64 day; -1 where absent
    feature_end_day: np.ndarray             # int64 day; -1 where absent
    tree: np.ndarray                        # float32 (rows, tree features); NaN where absent
    context: np.ndarray                     # float32 (rows, context columns); NaN where absent
    max_feature_end_gap: Optional[int]      # max(feature_end - issue day) over present rows (always < 0)


@dataclass
class TableData:
    """The table rows of a run (SPEC_TABLE_MODE.md 3.3), in row-grid order (row ids sorted, code-point)."""
    row_ids: np.ndarray                     # object, sorted
    groups: np.ndarray                      # object
    units: np.ndarray                       # object: the package unit of each row
    lat: np.ndarray
    lon: np.ndarray
    target_day: np.ndarray                  # int64 day ordinals
    y: np.ndarray                           # float64, NaN = invalid label
    is_test: np.ndarray                     # bool: marked test
    strata: Dict[str, np.ndarray]
    leads: Dict[int, LeadTable]
    grid: Any                               # io.steps.DenseGrid with one step
    data_manifest: Dict[str, Any]
    excluded_rows: int = 0
    dropped_groups: Tuple[str, ...] = ()
    smoke_units: Optional[Dict[str, Tuple[str, ...]]] = None

    def position_of(self) -> Dict[str, int]:
        return {str(r): i for i, r in enumerate(self.row_ids.tolist())}


def _date_days(col: Any, name: str, path: str) -> np.ndarray:
    """A date32 column, or a timestamp column with no time of day and no time zone, as day ordinals."""
    import pyarrow as pa

    from treeroute.io.steps import days_to_ordinals

    t = col.type
    if pa.types.is_date32(t):
        arr = col.to_numpy(zero_copy_only=False)
    elif pa.types.is_timestamp(t):
        if t.tz is not None:
            raise TableRefusal("G-CLOSED", "T-COLUMNS: %s in %s is a timestamp with time zone %s; a table date is a "
                               "plain day" % (name, path, t.tz))
        arr = col.to_numpy(zero_copy_only=False)
        if np.isnat(arr).any():
            raise TableRefusal("G-CLOSED", "T-COLUMNS: %s in %s holds missing dates" % (name, path))
        days = arr.astype("datetime64[D]")
        if (days.astype(arr.dtype) != arr).any():
            raise TableRefusal("G-CLOSED", "T-COLUMNS: %s in %s holds a time of day; a table date is a whole day"
                               % (name, path))
        arr = days
    else:
        raise TableRefusal("G-CLOSED", "T-COLUMNS: %s in %s has type %s; a table date is date32 or a timestamp with "
                           "no time of day" % (name, path, t))
    arr = np.asarray(arr, dtype="datetime64[D]")
    if np.isnat(arr).any():
        raise TableRefusal("G-CLOSED", "T-COLUMNS: %s in %s holds %d missing dates" % (name, path, int(np.isnat(arr).sum())))
    return days_to_ordinals(arr.astype(np.int64))


def _strings(col: Any, name: str, path: str) -> np.ndarray:
    import pyarrow as pa

    if not (pa.types.is_string(col.type) or pa.types.is_large_string(col.type)):
        raise TableRefusal("G-CLOSED", "T-COLUMNS: %s in %s has type %s; it holds text" % (name, path, col.type))
    arr = np.asarray(col.to_pylist(), dtype=object)
    bad = [x for x in arr.tolist() if not isinstance(x, str) or x == ""]
    if bad:
        raise TableRefusal("G-SUPPORT", "T-ROWID: %s in %s holds %d empty or missing values" % (name, path, len(bad)))
    return arr


def _floats(col: Any, name: str, path: str, allow_int: bool = True) -> np.ndarray:
    import pyarrow as pa

    t = col.type
    if pa.types.is_boolean(t) or not (pa.types.is_floating(t) or (allow_int and pa.types.is_integer(t))):
        raise TableRefusal("G-CLOSED", "T-COLUMNS: %s in %s has type %s; it holds numbers (float or int, never a "
                           "boolean)" % (name, path, t))
    return np.asarray(col.to_numpy(zero_copy_only=False), dtype=np.float64)


def _read_one(path: str, lead: int, spec: TableSpec) -> Dict[str, Any]:
    """One lead file read whole and checked on its own (T-COLUMNS, T-ROWID, T-UNITTIME, T-UNIT within the
    file, T-ISSUE, T-FEATEND, T-RANGE, T-FINITE)."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    table = pq.read_table(path)
    have = list(table.column_names)
    want = list(spec.columns)
    extra = sorted(set(have) - set(want))
    missing = sorted(set(want) - set(have))
    if extra or missing or len(set(have)) != len(have):
        raise TableRefusal("G-CLOSED", "T-COLUMNS: %s holds columns %s not in catalog.yaml and lacks %s (closed "
                           "world on columns: every catalog column is in every lead file, and nothing else)"
                           % (path, extra[:_SHOW], missing[:_SHOW]))
    n = table.num_rows
    if n == 0:
        raise TableRefusal("G-SUPPORT", "T-ROWID: %s holds no row" % path)
    out: Dict[str, Any] = {"path": path, "rows": n}
    rows = _strings(table.column(spec.row_col), spec.row_col, path)
    if len(set(rows.tolist())) != n:
        raise TableRefusal("G-SUPPORT", "T-ROWID: %s repeats %d row id(s)" % (path, n - len(set(rows.tolist()))))
    out["row"] = rows
    out["unit"] = _strings(table.column(spec.package_unit_col), spec.package_unit_col, path)
    out["group"] = _strings(table.column(spec.group_col), spec.group_col, path)
    for key, col in (("lat", spec.lat_col), ("lon", spec.lon_col)):
        c = table.column(col)
        if not pa.types.is_float64(c.type):
            raise TableRefusal("G-CLOSED", "T-COLUMNS: %s in %s has type %s; it is float64" % (col, path, c.type))
        out[key] = np.asarray(c.to_numpy(zero_copy_only=False), dtype=np.float64)
    lat, lon = out["lat"], out["lon"]
    if not (np.isfinite(lat).all() and np.isfinite(lon).all()) or (np.abs(lat) > 90).any() or (np.abs(lon) > 180).any():
        raise TableRefusal("G-DISJOINT", "T-UNIT: %s holds latitudes or longitudes that are not finite or outside "
                           "[-90, 90] / [-180, 180]" % path)
    tcol = table.column(spec.time_col)
    out["day"] = _date_days(tcol, spec.time_col, path)
    for key, col in (("issue", spec.issue_col), ("feature_end", spec.feature_end_col)):
        c = table.column(col)
        if c.type != tcol.type:
            raise TableRefusal("G-CLOSED", "T-COLUMNS: %s in %s has type %s; it has the target date's type %s"
                               % (col, path, c.type, tcol.type))
        out[key] = _date_days(c, col, path)
    marks = _strings(table.column(spec.mark_col), spec.mark_col, path)
    bad = sorted(set(marks.tolist()) - set(MARKS))
    if bad:
        raise TableRefusal("R5", "T-MARK: %s holds marks %s; a mark is exactly 'train' or 'test'" % (path, bad[:_SHOW]))
    out["test"] = marks == MARK_TEST
    pairs = set(zip(out["unit"].tolist(), out["day"].tolist()))
    if len(pairs) != n:
        raise TableRefusal("R1", "T-UNITTIME: %s repeats a (package unit, target date) on %d row(s); the package merges "
                           "them (O24)" % (path, n - len(pairs)))
    _unit_places(out["unit"], out["group"], lat, lon, path)
    issue_gap = out["issue"] - (out["day"] - int(lead))
    if (issue_gap != 0).any():
        i = int(np.flatnonzero(issue_gap != 0)[0])
        raise TableRefusal("R11", "T-ISSUE: %s: %d row(s) have an issue date that is not the target date minus %d days "
                           "(first row %s)" % (path, int((issue_gap != 0).sum()), lead, rows[i]))
    late = out["feature_end"] >= out["issue"]
    if late.any():
        i = int(np.flatnonzero(late)[0])
        raise TableRefusal("U1", "T-FEATEND: %s: %d row(s) declare a feature-end day on or after their issue day "
                           "(first row %s); no feature is dated on or after the issue date (U1)"
                           % (path, int(late.sum()), rows[i]))
    y = _floats(table.column(spec.target_col), spec.target_col, path)
    lo, hi = spec.legal_range
    if np.isinf(y).any():
        raise TableRefusal("G-RANGE", "T-RANGE: %s holds infinite labels (an invalid label is NaN, D30)" % path)
    fin = np.isfinite(y)
    outside = fin & ((y < lo) | (y > hi))
    if outside.any():
        raise TableRefusal("G-RANGE", "T-RANGE: %s holds %d finite label(s) outside the legal range [%r, %r] (O25)"
                           % (path, int(outside.sum()), lo, hi))
    out["y"] = y
    sentinel = float(K.SENTINEL_MASK_ABS)

    def matrix(columns: Sequence[str]) -> np.ndarray:
        M = np.empty((n, len(columns)), dtype=np.float64)
        for j, c in enumerate(columns):
            v = _floats(table.column(c), c, path)
            if np.isinf(v).any() or (np.isfinite(v) & (np.abs(v) >= sentinel)).any():
                raise TableRefusal("G-SENTINEL", "T-FINITE: %s: column %s holds infinite values or values at the "
                                   "sentinel size %g; a missing value is written as NaN" % (path, c, sentinel))
            M[:, j] = v
        return M
    out["tree"] = matrix(spec.tree_features)
    out["context"] = matrix(spec.context)
    strata: Dict[str, np.ndarray] = {}
    for c in spec.strata:
        col = table.column(c)
        if pa.types.is_string(col.type) or pa.types.is_large_string(col.type):
            strata[c] = np.asarray(col.to_pylist(), dtype=object)
        else:
            strata[c] = _floats(col, c, path)
    out["strata"] = strata
    return out


def _unit_places(units: np.ndarray, groups: np.ndarray, lat: np.ndarray, lon: np.ndarray, path: str) -> None:
    """T-UNIT (G-DISJOINT): a package unit has one group and one (lat, lon)."""
    seen: Dict[str, Tuple[str, float, float]] = {}
    for u, g, a, b in zip(units.tolist(), groups.tolist(), lat.tolist(), lon.tolist()):
        held = seen.get(u)
        if held is None:
            seen[u] = (g, a, b)
            continue
        if held[0] != g:
            raise TableRefusal("G-DISJOINT", "T-UNIT: %s: package unit %s is in groups %s and %s; a unit belongs to one "
                               "group" % (path, u, held[0], g))
        if (held[1], held[2]) != (a, b):
            raise TableRefusal("G-DISJOINT", "T-UNIT: %s: package unit %s has two places (%r, %r) and (%r, %r); one "
                               "(lat, lon) per unit" % (path, u, held[1], held[2], a, b))


def _check_leadset(zero: Dict[str, Any], other: Dict[str, Any], lead: int, spec: TableSpec) -> np.ndarray:
    """T-LEADSET (U1): every lead-L row id is in the lead-0 file, with the same unit, group, lat, lon, target date,
    label (bytes), mark and strata. Returns each lead-L row's index in the lead-0 file."""
    where = {r: i for i, r in enumerate(zero["row"].tolist())}
    idx = np.asarray([where.get(r, -1) for r in other["row"].tolist()], dtype=np.int64)
    if (idx < 0).any():
        raise TableRefusal("U1", "T-LEADSET: %d row id(s) of the lead-%d file are not in the lead-0 file, e.g. %s"
                           % (int((idx < 0).sum()), lead, _first(other["row"][idx < 0].tolist())))
    for key in ("unit", "group", "lat", "lon", "day", "test"):
        a, b = np.asarray(zero[key])[idx], np.asarray(other[key])
        if not np.array_equal(a, b):
            raise TableRefusal("U1", "T-LEADSET: the lead-%d file's %s differs from the lead-0 file's on %d row(s); the "
                               "same row id is the same sample in every file" % (lead, key, int((a != b).sum())))
    ya, yb = zero["y"][idx], other["y"]
    if ya.tobytes() != yb.tobytes():
        raise TableRefusal("U1", "T-LEADSET: the lead-%d file's labels differ from the lead-0 file's (bytes)" % lead)
    for c in spec.strata:
        a, b = zero["strata"][c][idx], other["strata"][c]
        same = np.array_equal(a, b) if a.dtype == object else (a.tobytes() == b.tobytes())
        if not same:
            raise TableRefusal("U1", "T-LEADSET: the lead-%d file's stratum %s differs from the lead-0 file's" % (lead, c))
    return idx


def read_tables(package: Any, spec: TableSpec, leads: Sequence[int], excluded: Sequence[str] = (),
                keep_groups: Optional[Sequence[str]] = None,
                smoke_units_per_group: Optional[int] = None) -> TableData:
    """Read every lead file whole and check it (SPEC_TABLE_MODE.md 2.1 and 3.3); returns the rows in row-grid order.

    keep_groups: the run's groups (None: every group not excluded); excluded: split.yaml's exclusions, dropped
    AFTER the contract checks. smoke_units_per_group (a smoke, R21): in each kept group, that many PACKAGE units
    by split.stride_pick over its sorted package units with a valid label (validity only, never a value), and
    every row of those units in every lead file.
    Refuses: whatever the checks refuse; a run group with no row."""
    from treeroute import split as SP
    from treeroute.io.steps import build_dense_grid

    files = lead_files(package, leads)
    raw = {L: _read_one(p, L, spec) for L, p in sorted(files.items())}
    zero = raw[0]
    index = {L: _check_leadset(zero, raw[L], L, spec) for L in raw if L != 0}
    manifest_files = []
    for L, p in sorted(files.items()):
        st = os.stat(p)
        manifest_files.append({"lead": int(L), "path": str(p).replace("\\", "/"), "size": int(st.st_size),
                               "mtime_ns": int(st.st_mtime_ns), "rows": int(raw[L]["rows"]),
                               "columns": len(spec.columns), "sha256": file_sha256(p)})
    groups_all = zero["group"]
    keep = ~np.isin(groups_all, np.asarray(list(excluded), dtype=object)) if excluded else np.ones(groups_all.size, bool)
    dropped = tuple(sorted(set(groups_all[~keep].tolist())))
    excluded_rows = int((~keep).sum())
    if keep_groups is not None:
        wanted = set(str(g) for g in keep_groups)
        absent = sorted(wanted - set(groups_all[keep].tolist()))
        if absent:
            raise TableRefusal("R18", "run group(s) %s have no row in the lead-0 file" % absent[:_SHOW])
        keep &= np.isin(groups_all, np.asarray(sorted(wanted), dtype=object))
    smoke_units = None
    if smoke_units_per_group is not None:
        smoke_units = {}
        for g in sorted(set(groups_all[keep].tolist())):
            sel = keep & (groups_all == g) & np.isfinite(zero["y"])
            units = tuple(sorted(set(zero["unit"][sel].tolist())))
            if not units:
                raise TableRefusal("R21", "smoke group %s has no package unit with a valid label" % g)
            smoke_units[g] = SP.stride_pick(units, int(smoke_units_per_group))
        picked = {u for v in smoke_units.values() for u in v}
        keep &= np.isin(zero["unit"], np.asarray(sorted(picked), dtype=object))
    kept = np.flatnonzero(keep)
    row_ids = zero["row"][kept]
    order = sorted(range(kept.size), key=lambda i: row_ids[i])          # plain code-point order (D37)
    pos0 = kept[np.asarray(order, dtype=np.int64)]
    rows_sorted = zero["row"][pos0]
    grid = build_dense_grid(rows_sorted, zero["group"][pos0], np.zeros(pos0.size, dtype=np.int64), (0, 0))
    if tuple(grid.unit_ids) != tuple(rows_sorted.tolist()):
        raise TableRefusal("U1", "internal: the row grid's order is not the sorted row ids")
    n = pos0.size
    zero_pos = {int(p): i for i, p in enumerate(pos0.tolist())}
    lead_tables: Dict[int, LeadTable] = {}
    for L in sorted(raw):
        src = raw[L]
        present = np.zeros(n, dtype=bool)
        issue = np.full(n, -1, dtype=np.int64)
        fend = np.full(n, -1, dtype=np.int64)
        tree = np.full((n, len(spec.tree_features)), np.nan, dtype=np.float32)
        ctx = np.full((n, len(spec.context)), np.nan, dtype=np.float32)
        lead_idx = np.arange(src["rows"], dtype=np.int64) if L == 0 else index[L]
        for j, p0 in enumerate(lead_idx.tolist()):
            i = zero_pos.get(int(p0))
            if i is None:
                continue
            present[i] = True
            issue[i] = src["issue"][j]
            fend[i] = src["feature_end"][j]
        sel = np.asarray([zero_pos.get(int(p0), -1) for p0 in lead_idx.tolist()], dtype=np.int64)
        ok = sel >= 0
        tree[sel[ok]] = src["tree"][ok].astype(np.float32)
        ctx[sel[ok]] = src["context"][ok].astype(np.float32)
        gap = (fend[present] - issue[present])
        lead_tables[L] = LeadTable(lead=int(L), present=present, issue_day=issue, feature_end_day=fend, tree=tree,
                                   context=ctx, max_feature_end_gap=int(gap.max()) if gap.size else None)
    if not lead_tables[0].present.all():
        raise TableRefusal("U1", "internal: a row of the lead-0 file is absent at lead 0")
    manifest = {"input": S.INPUT_TABLE, "files": manifest_files,
                "content_sha256": hashlib.sha256("".join(f["sha256"] for f in manifest_files).encode("ascii")).hexdigest(),
                "target_rows": int(zero["rows"]), "units": int(len(set(zero["unit"].tolist()))),
                "run_rows": int(n), "run_units": int(len(set(zero["unit"][pos0].tolist())))}
    return TableData(row_ids=np.asarray(rows_sorted, dtype=object), groups=np.asarray(zero["group"][pos0], dtype=object),
                     units=np.asarray(zero["unit"][pos0], dtype=object), lat=zero["lat"][pos0].copy(),
                     lon=zero["lon"][pos0].copy(), target_day=zero["day"][pos0].astype(np.int64),
                     y=zero["y"][pos0].astype(np.float64), is_test=zero["test"][pos0].copy(),
                     strata={c: v[pos0] for c, v in zero["strata"].items()}, leads=lead_tables, grid=grid,
                     data_manifest=manifest, excluded_rows=excluded_rows, dropped_groups=dropped,
                     smoke_units=smoke_units)


def table_groups(package: Any, spec: TableSpec) -> Tuple[str, ...]:
    """The groups of the lead-0 file's group column, sorted (the groups a table package holds)."""
    import pyarrow.parquet as pq

    path = lead_files(package, table_leads())[0]
    col = pq.read_table(path, columns=[spec.group_col]).column(spec.group_col)
    values = [x for x in col.to_pylist()]
    if any(not isinstance(x, str) or not x for x in values):
        raise TableRefusal("G-SUPPORT", "the lead-0 file's group column holds empty or missing names")
    return tuple(sorted(set(values)))


__all__ = ["TABLE_KEY_ROLES", "MARK_TRAIN", "MARK_TEST", "U2_VOUCHED", "TableRefusal", "TableSpec", "is_table_package",
           "table_spec", "table_leads", "lead_template", "lead_files", "file_sha256", "table_ram_bytes", "LeadTable",
           "TableData", "read_tables", "table_groups"]
