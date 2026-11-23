"""Reading a package's data for the pipeline (plan 4.1 steps 1 and 3): the package's code hooks, the
target table, the static table, the driver stores and the column reader derive_all calls.

Boilerplate around the approved io functions: every science step is theirs (io.sentinel.mask_sentinels,
io.joins.join_one_to_one / join_coarser_column / coarse_periods, io.apply.apply_lags / apply_verdicts,
io.steps.step_index, io.listing.list_store, io.readers.read_columns). This module moves bytes, checks
shapes and fails loudly; it names no problem, unit, year or drive (G-NONAMES).

The package's code hooks (dataset code, in the package, fingerprinted with it):
  - ingest/target_reader.py (optional): read_target_file(path, key) -> DataFrame. The engine lists the
    target store with dataset.yaml's template and hands the reader one file at a time with the key the
    listing read back from the path; the reader returns that file's target rows with the catalog's key
    columns and target column, invalid labels as NaN (D30). Without a reader the engine reads the
    catalog's columns itself (a missing key_group column is taken from a {group} placeholder).
    OWNER NOTE: plan 1.1 says ingest/ is 'hashed, never executed by the engine'; the target reader is
    the one ingest file the engine runs (the pipeline task asked for 'the package's own target reader').
  - features/build.py (optional, plan 1.5): OUTPUTS {column: store facts} and build(frame, keys). The
    outputs' facts are validated as store-catalog columns and added to the package's store facts, so
    derive's R8 lags each one from its declared facts.

The column reader (the object derive_all calls 'share_reader'): drivers_present (F2's joined rows),
content_epochs ('freeze' columns: not built in the pipeline, refused) and measure (R30's shares over one
donor view, after R8's lags). It holds the joined, sentinel-masked, UNLAGGED feature frame of the run's
target rows; lagged(lags) applies R8's lags through the approved io functions and is cached, so the pool
reads the same lagged values the shares were measured on.

Report strata (R34 'per declared stratum'): every catalog column whose ROLE is report_stratum, whatever
its verdict (a verdict decides the trees and the router; the role decides the report, and a stratum is
never a feature). Only a STATIC stratum is built (one value per unit, from a driver store whose facts
say cadence static, or from the static table); a time-varying stratum has no timing rule yet and is
refused.

Feature lineage (a stand-in for G-LINEAGE, which is not built): a feature output whose derived_from
names the target, a target twin, or a column banned for a leak reason is refused; any other banned or
conditional source is recorded.
"""

import hashlib
import importlib.util
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from treeroute import engine_constants as K
from treeroute.derive.shapes import MissingShares
from treeroute.errors import RefusedError
from treeroute.io.apply import apply_lags, apply_verdicts
from treeroute.io.joins import coarse_periods, join_coarser_column, join_one_to_one
from treeroute.io.lastvalue import fill_last_value
from treeroute.io.listing import list_store
from treeroute.io.readers import read_footer
from treeroute.io.sentinel import mask_sentinels
from treeroute.io.steps import as_int_array, cadence_identity, cadence_view, step_bounds, step_index
from treeroute.package import schema as S

KEY_ROLES = ("key_unit", "key_group", "key_time")
TARGET_ROLE = "target"
TARGET_ROLES = ("target", "target_twin")
STRATUM_ROLE = "report_stratum"
# Ban reasons that mean the column carries the label, a co-product of it, or information from after the
# row (package.schema.BAN_REASONS): a feature built from such a column carries it too.
LINEAGE_LEAK_REASONS = ("label", "coproduct", "target_derived", "post_event_state", "lookahead_unfixable",
                        "trend_proxy", "post_window_snapshot")
GROUP_PLACEHOLDER = "group"
TARGET_READER = "ingest/target_reader.py"
FEATURE_SCRIPT = "features/build.py"
FEATURE_STORE = "features/build.py"
STATIC_LAT, STATIC_LON = "lat", "lon"
STATIC_GRID = ("grid_ix", "grid_iy")
UNIT_CODE, STEP = "_unit_code", "_step"
_SHOW = 5


class DataRefusal(RefusedError):
    """A data read refused (fail loudly; nothing is guessed or skipped)."""


def _v(x: Any) -> Any:
    return getattr(x, "value", x)


def _fmt(names: Sequence[Any]) -> str:
    names = list(names)
    return "%s%s" % (names[:_SHOW], " ..." if len(names) > _SHOW else "")


# ---------------------------------------------------------------------------------------------------
# Package facts the pipeline reads
@dataclass(frozen=True)
class PackageSpec:
    """The catalog's roles, the merged store facts and where each non-key column goes."""
    unit_col: str
    group_col: str
    time_facts: Mapping[str, str]            # key_time column -> calendar part
    target_col: str
    legal_range: Tuple[float, float]
    measurement_error_floor: Optional[float]
    roles: Mapping[str, str]                 # every catalog column -> role
    store_facts: Mapping[str, Any]           # every column with store facts (feature outputs included)
    tree_features: Tuple[str, ...]
    context: Tuple[str, ...]
    frozen: Tuple[str, ...]
    listed_in_reports: Tuple[str, ...]       # keep_unreviewed and watch columns: named in every report
    feature_outputs: Tuple[str, ...]
    strata: Tuple[str, ...] = ()             # role report_stratum (any verdict): per-stratum tables only


def package_spec(package: Any) -> PackageSpec:
    """Read the catalog roles, the store facts and the verdict sets (io.apply_verdicts, G-CLOSED)."""
    cols = package.catalog.columns
    roles = {c: _v(f.role) for c, f in cols.items()}

    def one(role):
        found = [c for c, r in roles.items() if r == role]
        if len(found) != 1:
            raise DataRefusal("R1", "the catalog declares %d %s columns, one is needed" % (len(found), role))
        return found[0]

    unit_col, group_col, target_col = one("key_unit"), one("key_group"), one(TARGET_ROLE)
    time_facts = {c: _v(f.calendar_part) for c, f in cols.items() if roles[c] == "key_time"}
    if not time_facts:
        raise DataRefusal("R1", "the catalog declares no key_time column")
    store: Dict[str, Any] = {}
    for _, catalog in sorted(package.stores.items()):
        for c, f in catalog.columns.items():
            store.setdefault(c, f)
    tf = cols[target_col]
    legal = tf.legal_range if tf.legal_range is not None else getattr(store.get(target_col), "legal_range", None)
    if legal is None:
        raise DataRefusal("R22", "the target %s has no legal range" % target_col)
    non_key = tuple(c for c in cols if roles[c] not in KEY_ROLES)
    sets = apply_verdicts(non_key, dict(package.ban.verdicts), {c: roles[c] for c in non_key})
    outputs = tuple(package.stores[FEATURE_STORE].columns) if FEATURE_STORE in package.stores else ()
    return PackageSpec(unit_col=unit_col, group_col=group_col, time_facts=time_facts, target_col=target_col,
                       legal_range=(float(legal[0]), float(legal[1])),
                       measurement_error_floor=tf.measurement_error_floor, roles=roles, store_facts=store,
                       tree_features=tuple(sets.tree_features), context=tuple(sets.router_context),
                       frozen=tuple(sets.frozen), listed_in_reports=tuple(sets.listed_in_reports),
                       feature_outputs=tuple(outputs),
                       strata=tuple(c for c in cols if roles[c] == STRATUM_ROLE))


# ---------------------------------------------------------------------------------------------------
# The package's code hooks
def load_hook(package_root: Any, rel_path: str) -> Optional[Any]:
    """Execute one of the package's own code files as a private module (never put in sys.modules), or
    None when the package has no such file."""
    path = Path(package_root) / rel_path
    if not path.is_file():
        return None
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location("treeroute_package_hook_%s" % digest, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def feature_outputs(hook: Any) -> Dict[str, Any]:
    """The feature script's declared outputs, each validated as a store-catalog column (plan 1.5)."""
    outputs = getattr(hook, "OUTPUTS", None)
    if not isinstance(outputs, Mapping) or not outputs:
        raise DataRefusal("G-DERIVED", "features/build.py declares no OUTPUTS {column: store facts}",
                          fix="declare every output column with its facts (plan 1.5)")
    if not callable(getattr(hook, "build", None)):
        raise DataRefusal("G-DERIVED", "features/build.py has no build(frame, keys)")
    out = {}
    for column, facts in outputs.items():
        try:
            col = S.StoreColumn.model_validate(dict(facts))
        except Exception as exc:
            raise DataRefusal("G-DERIVED", "features/build.py: the facts of %r are not valid store facts: %s"
                              % (column, exc)) from exc
        if col.reads_target:
            raise DataRefusal("G-HIST", "features/build.py: %r reads the target; the engine builds the "
                              "own-history block (plan 1.5, G-HIST)" % column)
        if not col.derived_from:
            raise DataRefusal("G-DERIVED", "features/build.py: %r declares no derived_from" % column)
        out[str(column)] = col
    return out


def augment_package(package: Any, outputs: Mapping[str, Any]) -> Any:
    """The loaded package with the feature script's outputs added as one more store catalog (so
    derive's R8 finds their facts). A column already declared by a store catalog is refused."""
    if not outputs:
        return package
    taken = sorted(c for cat in package.stores.values() for c in cat.columns if c in outputs)
    if taken:
        raise DataRefusal("G-DERIVED", "feature outputs %s are also declared by a store catalog" % taken)
    missing = sorted(c for c in outputs if c not in package.catalog.columns)
    if missing:
        raise DataRefusal("G-CLOSED", "feature outputs %s have no row in catalog.yaml" % missing)
    catalog = S.StoreCatalog(store="features", description="outputs of the package feature script",
                             columns=dict(outputs))
    stores = dict(package.stores)
    stores[FEATURE_STORE] = catalog
    return package._replace(stores=stores)


def check_feature_lineage(outputs: Mapping[str, Any], package: Any) -> Dict[str, List[str]]:
    """The feature script's sources against the package's roles and verdicts (a stand-in for G-LINEAGE,
    which is not built). Refuses an output whose derived_from names a column the catalog does not
    declare, the target or a target twin, or a column banned for a leak reason (LINEAGE_LEAK_REASONS).
    Returns, per output, its sources that are banned for another reason or conditional (recorded in
    plan.json; the trees never read those sources themselves)."""
    cols = package.catalog.columns
    notes: Dict[str, List[str]] = {}
    for column, facts in sorted(outputs.items()):
        for src in facts.derived_from:
            if src not in cols:
                raise DataRefusal("G-CLOSED", "feature output %r is derived from %r, which catalog.yaml does not "
                                  "declare" % (column, src), fix="declare the source with its role and verdict")
            role = _v(cols[src].role)
            if role in TARGET_ROLES:
                raise DataRefusal("G-LINEAGE", "feature output %r is derived from %r, the %s; the engine builds "
                                  "the own-history block (G-HIST)" % (column, src, role))
            v = package.ban.verdicts.get(src)
            if v is None:
                continue                              # a key column: no verdict (G-KEYS decides its use)
            verdict = _v(v.verdict)
            if verdict == "ban" and v.reason in LINEAGE_LEAK_REASONS:
                raise DataRefusal("G-LINEAGE", "feature output %r is derived from %r, banned as %r: a feature "
                                  "built from it carries what the ban keeps out" % (column, src, v.reason),
                                  fix="drop the output, or derive it from reviewed sources only")
            if verdict in ("ban", "conditional"):
                notes.setdefault(column, []).append("%s: %s (%s)" % (src, verdict, v.reason))
    return notes


# ---------------------------------------------------------------------------------------------------
# The target table
def list_target(package: Any) -> Any:
    listing = list_store(package.dataset.stores.target, base=package.root)
    if not listing.store_root_exists or not listing.files:
        raise DataRefusal("G-SUPPORT", "the target store %s holds no file (store root %s)"
                          % (listing.path_template, listing.store_root),
                          fix="check dataset.yaml stores.target and that the store is reachable")
    return listing


def listed_groups(listing: Any) -> Optional[Tuple[str, ...]]:
    """The groups the target listing names (its {group} placeholder), or None without one."""
    if GROUP_PLACEHOLDER not in listing.key_names:
        return None
    i = listing.key_names.index(GROUP_PLACEHOLDER)
    return tuple(sorted({k[i] for k, _ in listing.files}))


def _files_of(listing: Any, groups: Optional[Sequence[str]]) -> List[Tuple[Any, str]]:
    if groups is None or GROUP_PLACEHOLDER not in listing.key_names:
        return list(listing.files)
    i = listing.key_names.index(GROUP_PLACEHOLDER)
    wanted = set(groups)
    return [(k, p) for k, p in listing.files if k[i] in wanted]


def _key_dict(listing: Any, key: Any) -> Dict[str, Any]:
    return dict(zip(listing.key_names, key))


def _read_target_generic(path: str, key: Mapping[str, Any], spec: PackageSpec) -> pd.DataFrame:
    import pyarrow.parquet as pq

    wanted = [spec.unit_col, spec.group_col] + list(spec.time_facts) + [spec.target_col]
    with pq.ParquetFile(path) as pf:
        names = pf.schema_arrow.names
    cols = [c for c in wanted if c in names]
    frame = pq.read_table(path, columns=cols).to_pandas()
    if spec.group_col not in frame.columns:
        if GROUP_PLACEHOLDER not in key:
            raise DataRefusal("R1", "%s holds no %s column and the template has no {group}" % (path, spec.group_col))
        frame[spec.group_col] = key[GROUP_PLACEHOLDER]
    return frame


def shared_str_ids(values: Any, what: str) -> np.ndarray:
    """Ids as an object array of str in which every row of one id points at ONE str object (a row
    holds a pointer, not its own copy of the text: a census repeats each unit id once per step).
    Refuses a missing id."""
    codes, uniques = pd.factorize(pd.Series(values, copy=False), sort=False)
    codes = np.asarray(codes)
    if (codes < 0).any():
        raise DataRefusal("R1", "%d target rows have no %s" % (int((codes < 0).sum()), what))
    names = np.array([str(u) for u in uniques], dtype=object)
    return names[codes]


def read_target(package: Any, spec: PackageSpec, hook: Any, listing: Any,
                groups: Optional[Sequence[str]], keep_units: Optional[Callable[[str, pd.DataFrame], Any]] = None,
                echo: Callable[[str], None] = print) -> pd.DataFrame:
    """The target rows of the given groups (all groups when None), read file by file through the
    package's target reader (or the generic reader), concatenated group by group. keep_units(group,
    frame) may pick a group's units after its files are read (the smoke's fixed-size pick).
    Checks: the catalog's key and target columns are present; the group of every row is its file's
    {group}; the target is numeric and holds no value at the sentinel magnitude (D30)."""
    files = _files_of(listing, groups)
    if not files:
        raise DataRefusal("G-SUPPORT", "no target file for the groups %s" % _fmt(groups or ()))
    reader = getattr(hook, "read_target_file", None) if hook is not None else None
    if hook is not None and not callable(reader):
        raise DataRefusal("R1", "ingest/target_reader.py has no read_target_file(path, key)")
    wanted = [spec.unit_col, spec.group_col] + list(spec.time_facts) + [spec.target_col]
    by_group: Dict[str, List[pd.DataFrame]] = {}
    order: List[str] = []
    for key, path in files:
        kd = _key_dict(listing, key)
        frame = reader(path, kd) if reader is not None else _read_target_generic(path, kd, spec)
        if not isinstance(frame, pd.DataFrame):
            raise DataRefusal("R1", "the target reader returned %s for %s" % (type(frame).__name__, path))
        missing = [c for c in wanted if c not in frame.columns]
        if missing:
            raise DataRefusal("R1", "the target rows of %s lack the columns %s" % (path, missing))
        frame = frame[wanted]
        if GROUP_PLACEHOLDER in kd:
            wrong = frame[spec.group_col].astype(object).to_numpy() != kd[GROUP_PLACEHOLDER]
            if wrong.any():
                raise DataRefusal("G-DISJOINT", "%d target rows of %s carry another group than the file's %r"
                                  % (int(wrong.sum()), path, kd[GROUP_PLACEHOLDER]))
        g = str(kd.get(GROUP_PLACEHOLDER, "")) or "__all__"
        if g not in by_group:
            by_group[g] = []
            order.append(g)
        by_group[g].append(frame)
    parts = []
    for g in order:
        frame = pd.concat(by_group.pop(g), ignore_index=True)
        if keep_units is not None:
            keep = keep_units(g, frame)
            frame = frame[frame[spec.unit_col].isin(set(keep))].reset_index(drop=True)
        parts.append(frame)
    table = pd.concat(parts, ignore_index=True)
    y = table[spec.target_col].to_numpy()
    if y.dtype.kind not in "fiu" or y.dtype == np.bool_:
        raise DataRefusal("R1", "the target column %s is not numeric (%s)" % (spec.target_col, y.dtype))
    y = y.astype(np.float64)
    big = np.isfinite(y) & (np.abs(y) >= K.SENTINEL_MASK_ABS)
    if big.any():
        raise DataRefusal("G-SENTINEL", "%d target values at the sentinel magnitude; the ingest writes invalid "
                          "labels as NaN (D30)" % int(big.sum()),
                          fix="the package's target reader (ingest/) must write NaN for invalid labels")
    if np.isinf(y).any():
        raise DataRefusal("G-SENTINEL", "%d target values are infinite" % int(np.isinf(y).sum()))
    table[spec.target_col] = y
    table[spec.unit_col] = shared_str_ids(table[spec.unit_col], "unit id")
    table[spec.group_col] = shared_str_ids(table[spec.group_col], "group id")
    for c in spec.time_facts:
        table[c] = as_int_array(table[c].to_numpy(), "time column %s" % c, rule="R1")
    echo("target: %d rows, %d units, %d groups (%d files)"
         % (len(table), table[spec.unit_col].nunique(), table[spec.group_col].nunique(), len(files)))
    return table


def target_table(frame: pd.DataFrame, spec: PackageSpec) -> Any:
    """The approved TargetTable shape (unit_ids, group_ids, time_columns, y) of a target frame."""
    return SimpleNamespace(unit_ids=frame[spec.unit_col].to_numpy(dtype=object),
                           group_ids=frame[spec.group_col].to_numpy(dtype=object),
                           time_columns={c: frame[c].to_numpy(dtype=np.int64) for c in spec.time_facts},
                           y=frame[spec.target_col].to_numpy(dtype=np.float64))


# ---------------------------------------------------------------------------------------------------
# The static table (plan 1.2: unit id, group id, lat, lon; optional grid_ix, grid_iy)
def static_files(package: Any) -> List[str]:
    """The static table's files (for the run fingerprint)."""
    return [p for _, p in list_store(package.dataset.stores.static, base=package.root).files]


def read_static(package: Any, spec: PackageSpec, groups: Sequence[str],
                extra: Sequence[str] = ()) -> pd.DataFrame:
    """The static rows of the given groups, with any of the extra columns the table holds (report
    strata). Refuses a missing table, missing columns, a repeated unit, a unit listed under two groups,
    and a non-finite lat or lon."""
    import pyarrow.parquet as pq

    template = package.dataset.stores.static
    listing = list_store(template, base=package.root)
    if not listing.files:
        raise DataRefusal("R14", "the static table %s does not exist" % listing.path_template,
                          fix="write it with the package's ingest (plan 1.2, 6.2 step 2)")
    frames = []
    found_sets = []
    for key, path in listing.files:
        with pq.ParquetFile(path) as pf:
            names = pf.schema_arrow.names
        need = [spec.unit_col, spec.group_col, STATIC_LAT, STATIC_LON]
        missing = [c for c in need if c not in names]
        if missing:
            raise DataRefusal("R14", "the static table %s lacks the columns %s" % (path, missing))
        grid = [c for c in STATIC_GRID if c in names]
        if len(grid) == 1:
            raise DataRefusal("R14", "the static table %s holds %s without its partner" % (path, grid))
        more = [c for c in extra if c in names]
        found_sets.append(tuple(more))
        frames.append(pq.read_table(path, columns=need + grid + more).to_pandas())
    if len(set(found_sets)) > 1:
        raise DataRefusal("R34", "the static table's files hold different stratum columns %s" % sorted(set(found_sets)))
    table = pd.concat(frames, ignore_index=True)
    table[spec.unit_col] = table[spec.unit_col].astype(object).map(str)
    table[spec.group_col] = table[spec.group_col].astype(object).map(str)
    table = table[table[spec.group_col].isin(set(groups))].reset_index(drop=True)
    if table[spec.unit_col].duplicated().any():
        raise DataRefusal("R14", "the static table lists %d units twice"
                          % int(table[spec.unit_col].duplicated().sum()))
    for c in (STATIC_LAT, STATIC_LON):
        if not np.isfinite(table[c].to_numpy(dtype=np.float64)).all():
            raise DataRefusal("R14", "the static table holds non-finite %s values" % c)
    absent = sorted(set(groups) - set(table[spec.group_col]))
    if absent:
        raise DataRefusal("R14", "the static table has no unit of the groups %s" % _fmt(absent))
    return table.sort_values(spec.unit_col, kind="stable").reset_index(drop=True)


# ---------------------------------------------------------------------------------------------------
# The column reader
def _years_of_steps(steps: np.ndarray, cadence: Any) -> np.ndarray:
    import datetime as _dt

    distinct, inverse = np.unique(np.asarray(steps, dtype=np.int64), return_inverse=True)
    first, _ = step_bounds(distinct, cadence)
    years = np.array([_dt.date.fromordinal(int(d)).year for d in first.tolist()], dtype=np.int64)
    return years[np.asarray(inverse).reshape(-1)]


def _fact_ns(column: str, spec: PackageSpec, role: Optional[str] = None) -> Any:
    s = spec.store_facts.get(column)
    return SimpleNamespace(role=role or spec.roles.get(column, "driver"),
                           fill_values=tuple(getattr(s, "fill_values", ()) or ()),
                           near_sentinel_optout=bool(getattr(s, "near_sentinel_optout", False)))


def _merge_last_value(old: Any, new: Any) -> Any:
    """One lag map's last-value record when its lagged frame is built in column chunks (a caller that
    narrows `kept`): the columns of `new` replace or join those of `old` (the rule is per column, so a
    chunk's counts are that column's counts); rows, units and the maximum must agree."""
    if old is None:
        return new
    if (old.rows, old.units, old.max_steps, old.max_months) != (new.rows, new.units, new.max_steps, new.max_months):
        raise DataRefusal("J2d", "internal: two last-value records of one lag map over different rows")
    columns = tuple(c for c in old.columns if c not in new.columns) + tuple(new.columns)
    merged = {}
    for name in ("missing", "filled", "gap_longer", "head", "tail"):
        values = dict(getattr(old, name))
        values.update(getattr(new, name))
        merged[name] = {c: values[c] for c in columns}
    return type(new)(max_months=new.max_months, max_steps=new.max_steps, rows=new.rows, units=new.units,
                     columns=columns, **merged)


@dataclass
class _Store:
    template: str
    columns: Tuple[str, ...]
    by_step: bool                          # keyed (unit, step); else (unit, coarse period)
    present: np.ndarray                    # per base row (by_step) -- or per base row via its year
    absent_groups: frozenset
    coarse: Optional[pd.DataFrame] = None  # (unit code, period, columns) for a coarse store


class ColumnReader(object):
    """The joined, sentinel-masked, unlagged feature frame of the run's target rows, and the column
    reader derive_all calls (drivers_present, content_epochs, measure). Base rows are the target rows,
    in the target table's order."""

    def __init__(self, package: Any, spec: PackageSpec, target: pd.DataFrame, cadence: Any,
                 feature_hook: Any, echo: Callable[[str], None] = print,
                 driver_file_keep: Optional[Callable[[str, bool, str], bool]] = None) -> None:
        """driver_file_keep(template, by_step, path) -> False skips that driver file (a reader whose target
        rows all lie after the file's rows: R30's streamed test-year count, pipeline/stream.py); None reads
        every file of the run's groups."""
        self.spec = spec
        self._driver_file_keep = driver_file_keep
        self.cadence = cadence
        self.echo = echo
        self.units = target[spec.unit_col].to_numpy(dtype=object)
        self.groups = target[spec.group_col].to_numpy(dtype=object)
        self.time_columns = {c: target[c].to_numpy(dtype=np.int64) for c in spec.time_facts}
        self.steps = step_index(self.time_columns, spec.time_facts, cadence)
        self.unit_names, codes = np.unique(self.units.astype(str), return_inverse=True)
        self.codes = np.asarray(codes, dtype=np.int64).reshape(-1)
        self.years = _years_of_steps(self.steps, cadence)
        self._row_of = pd.Series(np.arange(len(self.units), dtype=np.int64),
                                 index=pd.MultiIndex.from_arrays([self.codes, self.steps]))
        if self._row_of.index.duplicated().any():
            raise DataRefusal("G-SUPPORT", "the target repeats a (unit, step)")
        self.outputs = feature_outputs(feature_hook) if feature_hook is not None else {}
        self._hook = feature_hook
        wanted_kept = tuple(spec.tree_features) + tuple(spec.context)
        self.kept = wanted_kept
        sources = sorted({s for c in self.outputs for s in self.outputs[c].derived_from})
        stored_needed = [c for c in list(wanted_kept) + sources
                         if c not in self.outputs and c not in spec.time_facts
                         and c not in (spec.unit_col, spec.group_col)]
        stored_needed = list(dict.fromkeys(stored_needed))
        self.strata = tuple(spec.strata)
        optional = [c for c in self.strata if c not in stored_needed]
        self.raw = pd.DataFrame(index=pd.RangeIndex(len(self.units)))
        self.stores: List[_Store] = []
        self.files_read: List[str] = []
        self.strata_unread: Tuple[str, ...] = ()      # strata no driver store holds (the static table's)
        self._read_drivers(package, stored_needed + optional, optional)
        self._run_feature_script(sources)
        absent_kept = [c for c in wanted_kept if c not in self.raw.columns]
        if absent_kept:
            raise DataRefusal("G-CLOSED", "kept columns %s are in no driver store and no feature output"
                              % _fmt(absent_kept), fix="declare their store, or build them in features/build.py")
        self._lagged: Dict[str, pd.DataFrame] = {}
        self._last_value: Dict[str, Any] = {}

    # ------------------------------------------------------------------ reading the driver stores
    def _read_drivers(self, package: Any, needed: List[str], optional: Sequence[str] = ()) -> None:
        import pyarrow as pa
        import pyarrow.compute as pc
        import pyarrow.parquet as pq

        spec = self.spec
        run_groups = sorted(set(self.groups.tolist()))
        unit_set = pa.array(self.unit_names.tolist(), type=pa.string())
        remaining = list(needed)
        target_parts = tuple(spec.time_facts)
        for template in package.dataset.stores.drivers:
            listing = list_store(template, base=package.root)
            if not listing.files:
                raise DataRefusal("G-MISSING", "driver store %s holds no file" % listing.path_template)
            names = read_footer(listing.files[0][1]).names
            cols = [c for c in remaining if c in names]
            if not cols:
                continue
            remaining = [c for c in remaining if c not in cols]
            parts_in_file = tuple(c for c in target_parts if c in names)
            by_step = parts_in_file == target_parts
            coarse_parts = tuple(c for c in parts_in_file if spec.time_facts[c] == "year")
            if not by_step and coarse_parts != parts_in_file:
                raise DataRefusal("G-JOIN", "driver store %s holds the time columns %s: neither the target's "
                                  "%s nor a year" % (listing.path_template, parts_in_file, target_parts))
            absent = frozenset.intersection(*[frozenset((getattr(spec.store_facts.get(c), "absent_groups", {})
                                                        or {}).keys()) for c in cols])
            files = _files_of(listing, run_groups)
            listed = listed_groups(listing)
            if listed is not None:
                missing_groups = sorted(set(run_groups) - set(listed) - set(absent))
                if missing_groups:
                    raise DataRefusal("G-MISSING", "driver store %s has no file for the groups %s, which no "
                                      "store fact declares absent" % (listing.path_template, _fmt(missing_groups)))
            if self._driver_file_keep is not None:
                kept_files = [(k, p) for k, p in files if self._driver_file_keep(template, by_step, str(p))]
                files = kept_files if kept_files or not files else files   # never an empty read of a held store
            frames = []
            for key, path in files:
                with pq.ParquetFile(path) as pf:
                    table = pf.read(columns=[spec.unit_col] + list(parts_in_file) + cols)
                table = table.filter(pc.is_in(table.column(spec.unit_col).cast(pa.string()), value_set=unit_set))
                frames.append(table.to_pandas())
                self.files_read.append(str(path))
            stored = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
                columns=[spec.unit_col] + list(parts_in_file) + cols)
            stored[spec.unit_col] = stored[spec.unit_col].astype(object).map(str)
            facts = {c: _fact_ns(c, spec) for c in cols}
            facts[spec.unit_col] = SimpleNamespace(role="key_unit", fill_values=(), near_sentinel_optout=True)
            for c in parts_in_file:
                facts[c] = SimpleNamespace(role="key_time", fill_values=(), near_sentinel_optout=True)
            stored, report = mask_sentinels(stored, facts)
            masked = {c: n for c, n in report.masked.items() if n}
            code = np.searchsorted(self.unit_names, stored[spec.unit_col].to_numpy(dtype=object).astype(str))
            if by_step:
                steps = step_index({c: stored[c].to_numpy() for c in parts_in_file},
                                   {c: spec.time_facts[c] for c in parts_in_file}, self.cadence)
                right = pd.DataFrame({UNIT_CODE: code.astype(np.int64), STEP: steps})
                right["_present"] = 1.0
                for c in cols:
                    right[c] = stored[c].to_numpy()
                left = pd.DataFrame({UNIT_CODE: self.codes, STEP: self.steps})
                joined, rep = join_one_to_one(left, right, (UNIT_CODE, STEP), "driver store %s" % template)
                present = joined["_present"].to_numpy() == 1.0
                for c in cols:
                    self.raw[c] = joined[c].to_numpy()
                self.stores.append(_Store(template, tuple(cols), True, present, absent))
            else:
                year_col = coarse_parts[0]
                coarse = pd.DataFrame({UNIT_CODE: code.astype(np.int64),
                                       "_period": stored[year_col].to_numpy(dtype=np.int64)})
                for c in cols:
                    coarse[c] = stored[c].to_numpy()
                if coarse.duplicated([UNIT_CODE, "_period"]).any():
                    raise DataRefusal("G-JOIN", "driver store %s repeats a (unit, year)" % template)
                have = pd.MultiIndex.from_arrays([coarse[UNIT_CODE].to_numpy(), coarse["_period"].to_numpy()])
                present = pd.MultiIndex.from_arrays([self.codes, self.years]).isin(have)
                self.stores.append(_Store(template, tuple(cols), False, np.asarray(present), absent, coarse))
            self.echo("driver store %s: %d columns, %d stored rows, %d of %d target rows present%s"
                      % (listing.path_template, len(cols), len(stored), int(self.stores[-1].present.sum()),
                         len(self.units), "; sentinels masked %s" % masked if masked else ""))
        self.strata_unread = tuple(c for c in remaining if c in optional)
        remaining = [c for c in remaining if c not in optional]
        if remaining:
            raise DataRefusal("G-CLOSED", "columns %s are held by no driver store of dataset.yaml"
                              % _fmt(remaining), fix="declare the store that holds them")

    def _column_store(self, column: str) -> Optional[_Store]:
        for store in self.stores:
            if column in store.columns:
                return store
        return None

    # ------------------------------------------------------------------ the feature script
    def _run_feature_script(self, sources: Sequence[str]) -> None:
        if not self.outputs:
            return
        spec = self.spec
        frame = pd.DataFrame({spec.unit_col: self.units, spec.group_col: self.groups, STEP: self.steps})
        for c, part in spec.time_facts.items():
            frame[c] = self.time_columns[c]
        for s in sources:
            if s in frame.columns:
                continue
            if s in self.raw.columns:
                frame[s] = self.raw[s].to_numpy()
                continue
            store = self._column_store(s)
            if store is not None and not store.by_step:
                raise DataRefusal("G-DERIVED", "feature source %r lives in a coarse store; aggregate or join it "
                                  "in the feature script's own reader" % s)
            raise DataRefusal("G-DERIVED", "feature source %r is read by no driver store" % s)
        order = np.lexsort((self.steps, self.codes))
        ordered = frame.iloc[order].reset_index(drop=True)
        keys = {"unit": spec.unit_col, "group": spec.group_col, "step": STEP, "time": dict(spec.time_facts)}
        out = self._hook.build(ordered, keys)
        if not isinstance(out, pd.DataFrame) or len(out) != len(ordered):
            raise DataRefusal("G-DERIVED", "features/build.py returned %s rows for %d"
                              % (len(out) if hasattr(out, "__len__") else "?", len(ordered)))
        if sorted(out.columns) != sorted(self.outputs):
            raise DataRefusal("G-DERIVED", "features/build.py returned the columns %s, declared %s"
                              % (sorted(out.columns), sorted(self.outputs)))
        back = np.empty(len(order), dtype=np.int64)
        back[order] = np.arange(len(order))
        for c in self.outputs:
            values = np.asarray(out[c].to_numpy(), dtype=np.float64)[back]
            if np.isinf(values).any():
                raise DataRefusal("G-DERIVED", "feature output %r holds infinite values" % c)
            self.raw[c] = values
        self.echo("feature script: %d outputs built on %d rows (%s)" % (len(self.outputs), len(ordered),
                                                                       ", ".join(sorted(self.outputs))))

    # ------------------------------------------------------------------ derive_all's column reader
    def _check_rows(self, unit_ids: Any, time_columns: Mapping[str, Any]) -> None:
        u = np.asarray(unit_ids, dtype=object)
        if u.shape != self.units.shape or not np.array_equal(u, self.units):
            raise DataRefusal("F2", "the column reader was built on other target rows")
        for c in self.spec.time_facts:
            if not np.array_equal(np.asarray(time_columns[c], dtype=np.int64), self.time_columns[c]):
                raise DataRefusal("F2", "the column reader was built on other target times")

    def _stores_for(self, columns: Sequence[str]) -> List[_Store]:
        wanted = set()
        for c in columns:
            if c in self.outputs:
                wanted.update(self.outputs[c].derived_from)
            else:
                wanted.add(c)
        return [s for s in self.stores if wanted & set(s.columns)]

    def drivers_present(self, unit_ids: Any, group_ids: Any, time_columns: Mapping[str, Any],
                        columns: Sequence[str]) -> np.ndarray:
        """F2: per target row, every driver store holding one of the columns (or a source of a feature
        output among them) has the row; a group the store declares absent counts as present (F8)."""
        self._check_rows(unit_ids, time_columns)
        out = np.ones(len(self.units), dtype=bool)
        for store in self._stores_for(columns):
            absent = np.isin(self.groups, np.asarray(sorted(store.absent_groups), dtype=object)) \
                if store.absent_groups else np.zeros(len(self.units), dtype=bool)
            out &= store.present | absent
        return out

    def content_epochs(self, column: str) -> Any:
        raise DataRefusal("R9", "column %r has a 'freeze' verdict; per-cut frozen pools are not built in the "
                          "pipeline yet" % column, fix="owner item: build per-cut pools, or ban the column")

    def _lag_key(self, lags: Mapping[str, Any]) -> str:
        return hashlib.sha256(repr(sorted((c, int(l.steps)) for c, l in lags.items())).encode()).hexdigest()

    def lagged(self, lags: Mapping[str, Any]) -> pd.DataFrame:
        """The kept columns with R8's lags applied through the approved io functions (cached per lag
        map): same-step columns by apply_lags, coarser columns by join_coarser_column, static columns as
        stored; then the last-value rule (owner ruling J2 d, io.lastvalue.fill_last_value) on the kept TREE
        features only (router context is never filled), so R30's shares and the pool read what is still
        missing after it. Its record is kept per lag map (last_value_record). Rows: the base rows, in
        order (every row of each unit the reader holds, as the rule needs)."""
        key = self._lag_key(lags)
        if key in self._lagged:
            return self._lagged[key]
        target_id = cadence_identity(cadence_view(self.cadence))
        same, coarse, static = [], [], []
        for c in self.kept:
            facts = self.spec.store_facts.get(c)
            kind = _v(getattr(getattr(facts, "cadence", None), "kind", None))
            if kind == "static":
                static.append(c)
                continue
            if kind in ("epoch", "irregular"):
                raise DataRefusal("R8", "column %r has cadence %s; the pipeline joins grid columns only" % (c, kind))
            if c not in lags:
                raise DataRefusal("R8", "kept column %r has no lag in derived.json" % c)
            if cadence_identity(cadence_view(lags[c].column_cadence)) == target_id:
                same.append(c)
            else:
                coarse.append(c)
        out = pd.DataFrame(index=self.raw.index)
        if same:
            moved = apply_lags(self.raw[same], self.codes, self.steps, {c: lags[c] for c in same}, self.cadence)
            for c in same:
                out[c] = moved[c].to_numpy(dtype=np.float64)
        for c in coarse:
            cad = lags[c].column_cadence
            grid_periods = coarse_periods(self.steps, self.cadence, cad)
            store = self._column_store(c)
            if store is not None and not store.by_step:
                frame = store.coarse[[c]]
                ucodes = store.coarse[UNIT_CODE].to_numpy()
                periods = store.coarse["_period"].to_numpy()
            else:
                frame, ucodes, periods = self.raw[[c]], self.codes, grid_periods
            joined = join_coarser_column(pd.DataFrame(index=self.raw.index), self.codes, grid_periods, frame,
                                         ucodes, periods, c, cad, self.cadence, lags[c])
            out[c] = joined[c].to_numpy(dtype=np.float64)
        for c in static:
            if c not in self.raw.columns:
                raise DataRefusal("R8", "static column %r is not stored on the target's rows" % c)
            out[c] = self.raw[c].to_numpy(dtype=np.float64)
        out = out[list(self.kept)]
        # J2 d: right after the kept columns are selected, before caching (and so before R30 and the pool)
        trees = set(self.spec.tree_features)
        out, record = fill_last_value(out, self.codes, self.steps, tuple(c for c in self.kept if c in trees),
                                      self.cadence)
        self._last_value[key] = _merge_last_value(self._last_value.get(key), record)
        self._lagged[key] = out
        return out

    def last_value_record(self, lags: Mapping[str, Any]) -> Any:
        """The last-value rule's record (io.lastvalue.LastValueRecord) of the lagged frame of this lag map:
        per tree feature, the rows filled and the rows left to R30, over this reader's rows. Refuses a lag
        map whose lagged frame was not built yet."""
        key = self._lag_key(lags)
        if key not in self._last_value:
            raise DataRefusal("J2d", "internal: the last-value record of a lag map asked before its lagged frame "
                              "was built", fix="call lagged(lags) first")
        return self._last_value[key]

    def base_rows(self, unit_ids: Any, times: Any) -> np.ndarray:
        """Base-row positions of (unit id, step) pairs; refuses a pair the target does not hold."""
        u = np.asarray(unit_ids, dtype=object).astype(str)
        code = np.searchsorted(self.unit_names, u)
        ok = (code < len(self.unit_names))
        ok[ok] = self.unit_names[code[ok]] == u[ok]
        if not ok.all():
            raise DataRefusal("G-JOIN", "%d rows name units the target does not hold" % int((~ok).sum()))
        idx = pd.MultiIndex.from_arrays([code.astype(np.int64), as_int_array(times, "times")])
        pos = self._row_of.reindex(idx).to_numpy()
        if np.isnan(pos.astype(np.float64)).any():
            raise DataRefusal("G-JOIN", "rows name (unit, step) pairs the target does not hold")
        return pos.astype(np.int64)

    def measure(self, donor: Any, lags: Mapping[str, Any], test_years: Sequence[int]) -> MissingShares:
        """R30's shares over ONE donor view (derive_all passes it): per kept tree feature, after R8's
        lags, the share of donor rows missing and the share exactly 0; per test year, the share missing
        over every group's rows of that year."""
        lagged = self.lagged(lags)
        rows = self.base_rows(donor.unit_ids, donor.times)
        miss, zero, by_year = {}, {}, {}
        test_rows = {int(y): np.flatnonzero(self.years == int(y)) for y in test_years}
        for c in self.spec.tree_features:
            v = lagged[c].to_numpy(dtype=np.float64)
            d = v[rows]
            miss[c] = float(np.isnan(d).mean()) if d.size else 0.0
            zero[c] = float((d == 0).mean()) if d.size else 0.0
            for y, idx in test_rows.items():
                if idx.size:
                    by_year[(c, y)] = float(np.isnan(v[idx]).mean())
        return MissingShares(donor_row_key_hash=donor.row_key_hash, donor_unit_scope=donor.unit_scope,
                             donor_training_missing_share=miss, donor_training_zero_share=zero,
                             test_year_missing_share=by_year)

    def unit_values(self, column: str) -> pd.Series:
        """One value per unit of a column a driver store holds (a static report stratum): the unit's
        finite values must be one value (NaN when it has none). Refuses a unit with two values."""
        store = self._column_store(column)
        if store is None:
            raise DataRefusal("R34", "column %r is held by no driver store the run read" % column)
        if store.by_step:
            codes, values = self.codes, self.raw[column].to_numpy(dtype=np.float64)
        else:
            codes = store.coarse[UNIT_CODE].to_numpy(dtype=np.int64)
            values = store.coarse[column].to_numpy(dtype=np.float64)
        frame = pd.DataFrame({"code": codes, "v": values})
        frame = frame[np.isfinite(frame["v"].to_numpy())]
        distinct = frame.groupby("code")["v"].nunique()
        bad = distinct[distinct > 1]
        if len(bad):
            raise DataRefusal("R34", "report stratum %r holds more than one value in %d units (e.g. %s); a static "
                              "stratum has one value per unit" % (column, len(bad), _fmt(self.unit_names[bad.index])))
        first = frame.groupby("code")["v"].first()
        out = pd.Series(np.nan, index=pd.Index(self.unit_names, dtype=object), dtype=np.float64)
        out.iloc[first.index.to_numpy(dtype=np.int64)] = first.to_numpy(dtype=np.float64)
        return out

    def data_manifest(self) -> Dict[str, Any]:
        """What the run read (report only): rows, units, stores and their columns."""
        return {"target_rows": int(len(self.units)), "units": int(len(self.unit_names)),
                "stores": [{"template": s.template, "columns": len(s.columns), "by_step": s.by_step,
                            "present_rows": int(s.present.sum())} for s in self.stores],
                "feature_outputs": sorted(self.outputs), "driver_files": len(self.files_read)}


def stratum_values(spec: PackageSpec, reader: ColumnReader, static: pd.DataFrame) -> Dict[str, pd.Series]:
    """R34: each declared report stratum as one value per unit (index: unit id). Built only for a STATIC
    stratum: from a driver store whose facts say cadence static (one value per unit, checked), or from
    the static table. Refuses a stratum held by neither, one without store facts in a driver store, and
    a time-varying one (no timing rule says which of its values bins a row)."""
    out: Dict[str, pd.Series] = {}
    for c in spec.strata:
        if c in static.columns:
            out[c] = pd.Series(static[c].to_numpy(dtype=np.float64),
                               index=pd.Index(static[spec.unit_col].to_numpy(dtype=object), dtype=object))
            continue
        if c in reader.strata_unread:
            raise DataRefusal("G-CLOSED", "report stratum %r is in no driver store and not in the static table" % c,
                              fix="add it to the static table, or declare the store that holds it")
        facts = spec.store_facts.get(c)
        if facts is None:
            raise DataRefusal("R34", "report stratum %r has no store facts, so its cadence is unknown" % c,
                              fix="declare it in the store catalog (cadence static), or put it in the static table")
        kind = _v(getattr(getattr(facts, "cadence", None), "kind", None))
        if kind != "static":
            raise DataRefusal("R34", "report stratum %r has cadence %s: a time-varying stratum needs a rule for "
                              "which value bins a row, which is not built" % (c, kind),
                              fix="owner item: rule the stratum's timing, or give a static stratum")
        out[c] = reader.unit_values(c)
    return out


__all__ = ["DataRefusal", "PackageSpec", "package_spec", "load_hook", "feature_outputs", "augment_package",
           "check_feature_lineage", "list_target", "listed_groups", "shared_str_ids", "read_target", "target_table",
           "static_files", "read_static", "ColumnReader", "stratum_values", "TARGET_READER", "FEATURE_SCRIPT",
           "UNIT_CODE", "STEP", "LINEAGE_LEAK_REASONS"]
