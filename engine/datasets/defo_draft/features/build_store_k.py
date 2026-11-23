"""Deforestation package: the builder of the K supplementary store (owner ruling K, OWNER_RULINGS_2026-10-05.md
section K, "yes apply it"). A SMALL store beside the features store (features/build_store.py), so the 6.3-hour
features store is not rebuilt.

    cd "C:\\Users\\moh the ghost\\Desktop\\data set for reserch paper\\engine\\datasets\\defo\\features"
    py -3.9 -u build_store_k.py catalog ..                 # the store catalog (facts only; reads no panel data)
    py -3.9 -u build_store_k.py build ..                   # every group-year file, resumable
    py -3.9 -u build_store_k.py build .. --groups=costa_rica,pearl_river_delta
    py -3.9 -u build_store_k.py build .. --out-root=D:/treeroute/<task>/features_k    (a test store)

WHAT IT BUILDS. One parquet file per group and panel year (K_TEMPLATE, dataset.yaml's second driver store), one
row per target cell (every cell of D:/defo_target's group file, sorted: the rows of the features store), with
cell_id, year and 42 float64 columns (3 K2 + 3 K3 + 3 K5 + 33 K6), every value at year t built from data of year t
or earlier. NOT BUILT YET in D:/defo_features_k (2026-10-06): that store holds only 44 files of costa_rica and
pearl_river_delta in the OLDER 9-column schema (before K6); the owner's 'build ..' moves them aside and builds every
group, and until it finishes every defo run stops at the driver read (G-MISSING). The columns:
  K2  epo_mean / epo_min / epo_max: "build its yearly aggregates after the last-value rule (J2 d) fills December
      from November, so the strict aggregation (D34) is complete." The monthly epo is filled with the engine's
      own rule (treeroute.io.lastvalue.fill_last_value, monthly cadence: a month missing INSIDE the record takes
      the same cell's most recent EARLIER value, at most 2 months back), then aggregated over the calendar year
      by treeroute.io.aggregate_time (D34 strict). The fill reads a LATER month for its PRESENCE only (the gap
      must close within the maximum), never its value (lastvalue.py:32-34): the year-t aggregate exists only when
      January of t+1 holds a value. December 2023 comes after the record's last value (a tail), so it is NOT
      filled and the 2023 aggregates stay empty (measured on costa_rica and pearl_river_delta: every cell; epo is
      one global series, so every group is alike).
  K3  deeprec_twsa_k3_mean / _min / _max: the calendar-year aggregates of deeprec_twsa with the facts
      aggregate_time computes TODAY from the panel store catalog, which carries the J2 (b) bound
      (reach_after_max {3, month}, assumed): the aggregate reaches 91 days past its year, so R8 gives one year
      ("its signed 3-month reach carried through aggregate_time; R8 then gives one year"). Their values equal
      the features store's deeprec_twsa_<stat>; those columns cannot carry the new facts because their store
      catalog was generated before J2 (b) and regenerating it would refuse to keep all 924 files (resume rule),
      and a column may be declared by one store catalog only (features/build.py, pipeline/data.py), hence the
      new names.
  K5  V15_bare_ground_pct_lag2, V17_herb_cover_pct_lag2, tree_cover_pct_lag2: "Keep through engineered LAG-2-YEAR
      columns." The cell's MOD44B value of year t-2 (the one value of each cell-year, all months agreeing), NaN
      when t-2 is before the store's first year. The parent's content (stamp period_start, {430 day forward})
      of year t-2 runs from 1 January t-2 to about 6 March t-1, so the column is declared {2 years backward}
      from period_start of year t: content that ENDS before the predicted year starts (checked for every store
      year). K5's "same sum group, one verdict" read as: the three lag columns form ONE sum group of their own,
      MOD44B_V15_V17_tree_cover_lag2 (the parents' group name + '_lag2'), one verdict (keep); the banned raw trio
      keeps its group MOD44B_V15_V17_tree_cover, so no group name holds two verdicts (APP_PLAN.md 1.4: all
      members of a sum group get the same verdict). OWNER may rule the other reading.
  K6  <index>_mean / _min / _max of the 11 monthly climate-index families soi, tna, tsa, iod, ao, nao, pna, wp, sam,
      noi, pdo (33 columns): "The 11 climate-index families come back when the owner signs their timing windows"
      (ruling K6). Ruling L1 (b) (2026-10-06) signed their windows {3, month, centred} in the panel store catalog, so
      treeroute.io.aggregate_time (D34 strict) computes each aggregate's facts (F5): the December value's content
      reaches into January, so R8 gives the annual aggregate one year (as ruling B R-A gives the ERSST family on
      annual aggregates; pdo, possibly ERSST-based, comes out the same on this annual target). Built exactly as the
      features store builds every other monthly aggregate (build_store.py build_group_year), here because that
      6.3-hour store is not rebuilt; catalog.yaml declares the 33 names (role engineered) and the features store
      catalog declares none of them. A parent the panel catalog leaves without a signed window is REFUSED (the
      catalog command fails loudly; nothing is guessed).
NOT BUILT HERE:
  K1  spei_*/amo lag-1-year aggregates: already built, exactly as K1 words them, by features/build.py (owner
      ruling J2 a: <aggregate>_lag1 = the same cell's aggregate of the previous calendar year; keep, the raw
      parents banned 'incomplete'). A second copy here would declare the same columns twice.
  K4  the MCD12Q1/MCD12C1 land-cover columns: facts alone (catalog.yaml co_measured_with_target: true, assumed;
      R8 floors them at one year); their values are the features store's annual columns, read as they are.

FACTS. The store catalog (CATALOG_FILE, included by dataset.yaml with its sha256) is GENERATED by 'catalog' from
the panel store catalog (its sha256 checked against dataset.yaml): every column declares derived_from, its
operation, a backward window and reads_target false. K3 facts are aggregate_time's (F5). K2 facts are
aggregate_time's when the panel catalog gives epo a window: since 2026-10-06 it does ({3, month, centred}, ruling
L1 b, merged by another task), so the K2 entries carry {1, year, backward} + reach 31 days and R8 lags them one
year. Were the window unknown again (align unknown, no signed bound), aggregate_time would refuse to compute the
aggregate's window (G-LAG) and the catalog would carry the parent's unknown window as it is (nothing is guessed):
R8 then refuses the epo aggregates at lag 0. The generated entries never copy the parent's reviewed_by/date.
VALUES ONLY: aggregate_time computes the values before the facts and refuses an unknown window only in its
facts step, so for the epo VALUES of an unknown window it is called with a view whose window is the parent's own
one-month step; the facts that call returns are discarded, never written (_values_view).

LINEAGE GUARD NOT RUN ON THESE COLUMNS (disclosed: exceptions.yaml 'G-LINEAGE stand-in', ban.yaml K3/K5 evidence).
The engine's G-LINEAGE stand-in (treeroute/pipeline/data.py check_feature_lineage) checks the FEATURE SCRIPT's
outputs (features/build.py) only; the K columns are STORE columns, so it never runs on them. Were they built by
features/build.py it would refuse them: the K5 lag columns are derived from the raw MOD44B trio, banned
'coproduct' (a leak reason, LINEAGE_LEAK_REASONS); the K3 and K2 columns are derived from the monthly panel
columns deeprec_twsa and epo, which catalog.yaml does not declare (ruling J4 removed the monthly parents), so it
would refuse them G-CLOSED (the position of every aggregate of the features store; K3's features-store twins
deeprec_twsa_<stat> are banned 'lookahead_unfixable', before K3 'target_derived', both leak reasons). Not a leak
(backward only: tests/test_defo_k_ruling.py plants later values) and the keeps are the owner's rulings, but the
guard is sidestepped, while the L3 hold columns (features/build.py) had their parents' reason word set to
'incomplete' to pass it. OWNER item: keep as is, change the parents' reason words, or extend the stand-in to
store columns that declare derived_from (an engine change).

PDO, RULING N1 (OWNER_RULINGS_2026-10-06.md N1: "pdo at lag 2 (ERSSTv5-based, like nino34)"; SIGNOFF_REVIEW.md N1).
PSL's PDO is the projection of ERSSTv5 anomalies. The shared panel store catalog carries the N1 window for pdo (with
the ERSSTv5 filter reach_after_max {2, month}, like nino34; edited 2026-10-06 by the shared task), so aggregate_time
computes the reach of pdo_mean/_min/_max into the next year from it and R8 still gives one year on this annual
target. N1_PARENTS names the K6 families N1 rules: the catalog command refuses when the panel window of one of them
carries no forward reach (N1 not in the panel catalog), and their provenance names the ruling. The window enters no
K value (value_facts), so the built files stay valid.

SIGNATURES (owner ruling N S5; datasets/_tools/apply_signoff.py): the owner signs entries of the committed catalog in
place (fact_status, reviewed_by, date, a provenance note). 'catalog' and the build's catalog check carry each
signature onto the regenerated entry whose other facts are unchanged (features/build_store.py carry_signatures); an
entry whose facts changed (pdo's under N1) loses it, and 'catalog' names it, so the owner's sign-off tool signs it
again. signed_catalog_document and check_signed_catalog write or check the catalog only, never a file, so they are
NOT_FILE_CONTENT (content_sha256 and the 924 records unchanged).

RECORDS AND RESUME. Beside the files, _build/<group>_<year>.json records the file's size, this file's content
digest (content_sha256), build_store.py's (the helpers this file imports), the engine code the values come from
(io/aggregate.py, io/lastvalue.py, io/sentinel.py), the panel facts that enter the values (value_facts: each
parent's cadence, fill_values and near_sentinel_optout, read from the pinned panel store catalog), the target file
and its sha256, and the size and mtime of every panel file the year's values read (years t-2, t-1, t, t+1). An
existing file is kept only when all of these are today's (resume_check); anything else is refused, naming what
differs (the builder never deletes). ONE EXCEPTION, the STORE SCHEMA: every record carries schema_sha256 (sha256 of
the ordered output column list, schema_sha256), and an existing file whose own parquet column list hashes to another
schema (for example the 2026-10-06 files of costa_rica and pearl_river_delta, built before K6) is STALE: the builder
moves it and its record aside into <store folder>/_moved_20261006/<its schema sha256, 12 hex>/ (records under
_build/ there; refused if a file of that name is already there, never overwritten, never deleted) and rebuilds it.
A file of today's schema that differs in anything else is still refused. The K store catalog's sha256 is recorded
but does not decide resume: no fact of THAT catalog enters a value (it is checked against what 'catalog' writes
before any build, and pinned by sha256 in dataset.yaml); the panel facts that do enter one are value_facts. Files
are written to a temporary name in _build/ and renamed (never half-written, never overwritten).

READ-ONLY on D:/monthly_panel and D:/defo_target. Dataset code: it may name its stores, products and years; the
engine may not (G-NONAMES).
"""
# Provenance: OWNER_RULINGS_2026-10-05.md K1-K6 (2026-10-06, "yes apply it"), J2 (b) (deeprec_twsa bound), J2 (d)
# (last-value rule), J5 (R4 counts a declared lag operation); K6 + L1 (b) (2026-10-06: the 11 index families' windows
# signed {3, month, centred}, so their annual aggregates are built here); features/build_store.py (the features store, whose
# helpers and conventions this file reuses); features/build.py (K1); INDEX_WINDOW_AUDIT.md:75 (CPC issues no
# December EPO); panel store catalog V15_bare_ground_pct / V17_herb_cover_pct / tree_cover_pct (MODIS MOD44B,
# stamp period_start, window {430, day, forward}, sum_group MOD44B_V15_V17_tree_cover); 2026-10-06 review (the lag
# columns' own sum group; value_facts in the build records; the G-LINEAGE disclosure).

import contextlib
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parents[2]
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))


def _load_build_store():
    """features/build_store.py (package files, listings, facts helpers), loaded by path as a private module
    (never by a bare module name another package could also use)."""
    import importlib.util
    path = HERE / "build_store.py"
    spec = importlib.util.spec_from_file_location("defo_build_store_for_k_%s" % hashlib.sha256(
        path.read_bytes()).hexdigest()[:12], str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


B = _load_build_store()
from treeroute.io.aggregate import STEP, UNIT_CODE, aggregate_time  # noqa: E402
from treeroute.io.lastvalue import fill_last_value  # noqa: E402
from treeroute.io.sentinel import mask_sentinels  # noqa: E402
from treeroute.io.steps import step_bounds, step_index  # noqa: E402
from treeroute.package import schema as S  # noqa: E402
from treeroute.timing import content_interval  # noqa: E402

K_TEMPLATE = "D:/defo_features_k/{group}_{year}.parquet"
CATALOG_FILE = "features/defo_features_k_store_catalog.yaml"
STORE_NAME = "defo_k_features"
STATS = B.STATS
UNIT, YEAR_COL, MONTH_COL = B.UNIT, B.YEAR_COL, B.MONTH_COL
MONTH = SimpleNamespace(kind="regular", length=1, unit="month")
YEAR = SimpleNamespace(kind="regular", length=1, unit="year")
YEAR_FACT = {"kind": "regular", "length": 1, "unit": "year"}
COMPRESSION = "zstd"
# origin: owner ruling K2 (epo), K3 (deeprec_twsa), K5 (the MOD44B trio, lag 2 years)
K2_PARENT = "epo"
K3_PARENT = "deeprec_twsa"
K3_TAG = "k3"
K5_PARENTS = ("V15_bare_ground_pct", "V17_herb_cover_pct", "tree_cover_pct")
K5_LAG = 2
K5_SUM_GROUP_SUFFIX = "_lag%d" % K5_LAG      # the lag columns' own sum group: <parents' group>_lag2
K2_OPERATION = ("last_value {rule: J2 d, at most 2 months back, earlier values only} then aggregate_time "
                "{window: 1 year, stat: %s}")
K5_OPERATION = "lag k=%d unit=year" % K5_LAG
# origin: owner ruling K6 + L1 (b) (OWNER_RULINGS_2026-10-05.md, 2026-10-06): the 11 index families whose windows the
# owner signed {3, month, centred} (L1 b lists 13: epo is K2 here, grace_lwe stays banned 'incomplete' in ban.yaml)
K6_PARENTS = ("soi", "tna", "tsa", "iod", "ao", "nao", "pna", "wp", "sam", "noi", "pdo")
ENGINE_CODE = ("treeroute/io/aggregate.py", "treeroute/io/lastvalue.py", "treeroute/io/sentinel.py")
# Stale files of an older store schema are moved aside here (inside the store folder, one subfolder per old schema
# hash); origin: the 2026-10-06 build rule "never delete; move aside into a _moved_20261006 folder".
MOVED_DIR = "_moved_20261006"
# The functions that only decide whether a file is built, kept, moved aside or refused, or read the command line: left
# out of content_sha256 (a change to them never changes what a file holds).
NOT_FILE_CONTENT = ("build", "main", "content_sha256", "resume_check", "write_catalog", "file_schema_sha256",
                    "move_stale_aside", "signed_catalog_document", "check_signed_catalog")
NOT_FILE_CONTENT_CONSTANTS = ("NOT_FILE_CONTENT", "NOT_FILE_CONTENT_CONSTANTS", "MOVED_DIR", "N1_PARENTS")
# origin: owner ruling N1 (OWNER_RULINGS_2026-10-06.md: "pdo at lag 2 (ERSSTv5-based, like nino34)"): the K6 families
# whose panel window carries the ERSSTv5 reach (facts only; module docstring, PDO, RULING N1)
N1_PARENTS = ("pdo",)


class BuildError(Exception):
    """The K store cannot be built as declared (fail loudly; nothing is guessed or skipped)."""


def k2_columns():
    return tuple("%s_%s" % (K2_PARENT, s) for s in STATS)


def k3_columns():
    return tuple("%s_%s_%s" % (K3_PARENT, K3_TAG, s) for s in STATS)


def k5_columns():
    return tuple("%s_lag%d" % (p, K5_LAG) for p in K5_PARENTS)


def k6_columns():
    return tuple("%s_%s" % (p, s) for p in K6_PARENTS for s in STATS)


def columns():
    return k2_columns() + k3_columns() + k5_columns() + k6_columns()


def schema_columns():
    """The ordered column list of every K file (keys first)."""
    return (UNIT, YEAR_COL) + columns()


def schema_sha256(names=None):
    """sha256 of an ordered column list (default: today's schema_columns()); a file whose own parquet column list
    hashes to another value is of an older store schema (stale)."""
    names = list(schema_columns() if names is None else names)
    return hashlib.sha256(json.dumps(names, separators=(",", ":")).encode("utf-8")).hexdigest()


def content_sha256(path=None):
    """sha256 over the parsed statements of this file that decide what a group-year file holds (every
    top-level statement except the module docstring, the NOT_FILE_CONTENT functions and the
    NOT_FILE_CONTENT_CONSTANTS assignments; build_store.py's rule)."""
    import ast

    text = Path(path or __file__).read_text(encoding="utf-8")
    body = ast.parse(text).body
    if (body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    h = hashlib.sha256()
    for node in body:
        if isinstance(node, ast.FunctionDef) and node.name in NOT_FILE_CONTENT:
            continue
        if isinstance(node, ast.Assign):
            names = {t.id for t in node.targets if isinstance(t, ast.Name)}
            if names and len(names) == len(node.targets) and names <= set(NOT_FILE_CONTENT_CONSTANTS):
                continue
        h.update(ast.dump(node).encode("utf-8"))
        h.update(b"|")
    return h.hexdigest()


# ---------------------------------------------------------------------------------------------------
# the package
def load_package_files(root):
    """build_store.py's package files (dataset.yaml, catalog.yaml, the panel store catalog checked by sha256),
    plus this store's template: dataset.yaml must declare K_TEMPLATE among its driver stores, after the
    features store."""
    pkg = B.load_package_files(root)
    drivers = list(pkg.dataset.stores.drivers)
    if K_TEMPLATE not in drivers:
        raise BuildError("dataset.yaml's driver stores do not name the K store %s" % K_TEMPLATE)
    if drivers.index(K_TEMPLATE) == 0:
        raise BuildError("the K store must not be dataset.yaml's first driver store (the features store is)")
    for c in columns():
        f = pkg.catalog.columns.get(c)
        if f is None or f.role != "engineered":
            raise BuildError("catalog.yaml must declare %s with role engineered" % c)
    for p in (K2_PARENT, K3_PARENT) + K5_PARENTS + K6_PARENTS:
        if p not in pkg.panel.columns:
            raise BuildError("the panel store catalog has no column %s" % p)
    return pkg


def _value(x):
    return getattr(x, "value", x)


def _ordered(entry):
    """A store-catalog entry in the schema's field order, validated."""
    out = {k: entry[k] for k in S.StoreColumn.model_fields if k in entry}
    extra = sorted(set(entry) - set(out))
    if extra:
        raise BuildError("internal: fields %s are not store facts" % extra)
    S.StoreColumn.model_validate(out)
    return out


# ---------------------------------------------------------------------------------------------------
# facts
def _year_period(year):
    first, last = step_bounds(np.array([int(year)], dtype=np.int64), YEAR)
    return int(first[0]), int(last[0])


def _unknown_unsigned(window):
    return window is None or (_value(getattr(window, "align", None)) == "unknown"
                              and getattr(window, "max_length", None) is None)


def k2_entry(pkg, stat, years):
    """epo's aggregate after the last-value fill: aggregate_time's facts when the panel catalog gives epo a window,
    else the parent's unknown window carried as it is (G-LAG)."""
    name = "%s_%s" % (K2_PARENT, stat)
    facts, why = B.aggregate_facts_or_refusal(pkg, K2_PARENT, stat, years)
    common = ("owner ruling K2 (OWNER_RULINGS_2026-10-05.md): the monthly panel column epo filled by the last-value "
              "rule (treeroute.io.lastvalue.fill_last_value on the monthly rows: CPC issues no December EPO, "
              "INDEX_WINDOW_AUDIT.md:75, so each December takes the same cell's November value when January of the "
              "next year holds a value), then aggregated over the calendar year by treeroute.io.aggregate_time (D34 "
              "strict); December 2023 is the record's tail, never filled, so the 2023 aggregate is empty; "
              "features/build_store_k.py")
    if facts is not None:
        entry = B.facts_entry(facts, K2_PARENT, stat)
        entry["operation"] = K2_OPERATION % stat
        entry["provenance"] = common + "; stamp and window computed by aggregate_time from the panel facts (F5)"
        return _ordered(entry)
    p = pkg.panel.columns[K2_PARENT]
    entry = {"dtype": "float64", "units": p.units, "cadence": dict(YEAR_FACT), "scope": _value(p.scope),
             "stamp": "period_end", "window": p.window.model_dump(exclude_none=True),
             "fill_values": [], "derived_from": [K2_PARENT], "operation": K2_OPERATION % stat,
             "reads_target": False, "fact_status": _value(p.fact_status)}
    if p.legal_range is not None:
        entry["legal_range"] = [float(p.legal_range[0]), float(p.legal_range[1])]
    if p.product_family:
        entry["product_family"] = p.product_family
    if p.lineage is not None:
        entry["lineage"] = p.lineage.model_dump()
    entry["provenance"] = (common + "; WINDOW NOT COMPUTED: the panel store catalog gives epo an unknown window "
                           "with no signed bound, so aggregate_time refuses the aggregate's window (%s); the parent's "
                           "window is carried as it is and R8 refuses %s at lag 0 until a window is signed in the "
                           "panel store catalog and this catalog is regenerated (build_store_k.py catalog; the "
                           "values do not change)" % (why.split(" Fix:")[0], name))
    return _ordered(entry)


def k3_entry(pkg, stat, years):
    """deeprec_twsa's calendar-year aggregate with aggregate_time's facts from today's panel catalog (F5)."""
    entry = B.facts_entry(B._synthetic_facts(pkg, K3_PARENT, stat, years), K3_PARENT, stat)
    entry["provenance"] = (
        "owner ruling K3 (OWNER_RULINGS_2026-10-05.md: 'its signed 3-month reach carried through aggregate_time; R8 "
        "then gives one year'): %s of the monthly panel column deeprec_twsa over each calendar year, built by "
        "treeroute.io.aggregate_time (D34 strict) in features/build_store_k.py, with the stamp and window it computes "
        "from the panel store catalog's J2 (b) bound (reach_after_max {3, month}, assumed): the values of the "
        "features store's deeprec_twsa_%s, whose generated facts predate that bound; a new name because a column is "
        "declared by one store catalog only" % (stat, stat))
    return _ordered(entry)


def k6_entry(pkg, parent, stat, years):
    """An index family's calendar-year aggregate with aggregate_time's facts from the panel catalog's signed window
    (L1 b); refused when the panel catalog gives the parent no window aggregate_time can carry (G-LAG)."""
    facts, why = B.aggregate_facts_or_refusal(pkg, parent, stat, years)
    if facts is None:
        raise BuildError("K6 %s_%s: aggregate_time refuses the aggregate's window (%s); ruling K6 builds the index "
                         "families only once their windows are signed in the panel store catalog"
                         % (parent, stat, why.split(" Fix:")[0]))
    entry = B.facts_entry(facts, parent, stat)
    w = pkg.panel.columns[parent].window
    entry["provenance"] = (
        "owner ruling K6 (OWNER_RULINGS_2026-10-05.md: 'The 11 climate-index families come back when the owner signs "
        "their timing windows') after ruling L1 (b) (2026-10-06: window {%g, %s, %s} signed in the panel store "
        "catalog): %s of the monthly panel column %s over each calendar year, built by treeroute.io.aggregate_time (D34 "
        "strict; stamp and window computed from the panel facts, F5) in features/build_store_k.py exactly as "
        "features/build_store.py builds the other monthly aggregates (that store is not rebuilt); the December value "
        "reaches into January, so R8 gives one year on the annual target" % (w.length, _value(w.unit), _value(w.align),
                                                                             stat, parent))
    return _ordered(entry)


def k5_entry(pkg, parent):
    """The MOD44B parent's value of year t-2 at year t: declared {2 years backward} from period_start."""
    p = pkg.panel.columns[parent]
    cad = p.cadence
    if (_value(cad.kind), cad.length, _value(cad.unit)) != ("regular", 1, "year"):
        raise BuildError("K5 parent %s has cadence %s; the lag-2 column reads one value per calendar year" % (parent, cad))
    entry = {"dtype": "float64", "units": p.units, "cadence": dict(YEAR_FACT), "scope": _value(p.scope),
             "stamp": "period_start", "window": {"length": K5_LAG, "unit": "year", "align": "backward"},
             "fill_values": [], "derived_from": [parent], "operation": K5_OPERATION, "reads_target": False,
             "fact_status": _value(p.fact_status)}
    if p.legal_range is not None:
        entry["legal_range"] = [float(p.legal_range[0]), float(p.legal_range[1])]
    if p.product_family:
        entry["product_family"] = p.product_family
    if not p.sum_group:
        raise BuildError("K5 parent %s has no sum group; K5 rules one verdict for the trio's sum group" % parent)
    entry["sum_group"] = p.sum_group + K5_SUM_GROUP_SUFFIX
    w = p.window
    entry["provenance"] = (
        "owner ruling K5 (OWNER_RULINGS_2026-10-05.md: 'Keep through engineered LAG-2-YEAR columns ... two years "
        "ends before it'): the same cell's %s of calendar year t-2 (one value per cell-year, all months agreeing; "
        "NaN before the store's first year + 2); the parent (stamp %s, window {%s, %s, %s}) describes 1 January "
        "t-2 to about 6 March t-1, inside the declared window {2 years backward} from period_start of year t, which "
        "ends where the predicted year starts (checked for every store year by features/build_store_k.py); sum "
        "group %s: the three lag columns, one verdict (the banned raw trio keeps its group %s)"
        % (parent, _value(p.stamp), w.length, _value(w.unit), _value(w.align), entry["sum_group"], p.sum_group))
    return _ordered(entry)


def check_k5_windows(pkg, entries, years):
    """For every store year t: the parent's content of year t-2 lies inside the lag column's declared content of
    year t, and that content ends before 1 January t. Returns the number of (column, year) checks."""
    n = 0
    for parent, name in zip(K5_PARENTS, k5_columns()):
        p = pkg.panel.columns[parent]
        pv = SimpleNamespace(name=parent, cadence=p.cadence, stamp=p.stamp, window=p.window, fact_status=p.fact_status)
        col = S.StoreColumn.model_validate(entries[name])
        lv = SimpleNamespace(name=name, cadence=col.cadence, stamp=col.stamp, window=col.window,
                             fact_status=col.fact_status)
        for t in years:
            a0, a1 = content_interval(pv, _year_period(int(t) - K5_LAG))
            b0, b1 = content_interval(lv, _year_period(int(t)))
            start_t = _year_period(int(t))[0]
            if not (b0 <= a0 and a1 <= b1 and b1 < start_t):
                raise BuildError("%s %d: the parent's content of %d (days %d-%d) is not inside the declared content "
                                 "(days %d-%d) ending before the year starts (day %d)"
                                 % (name, t, int(t) - K5_LAG, a0, a1, b0, b1, start_t))
            n += 1
    return n


def catalog_document(pkg):
    """(text, {column: entry}) of the K store catalog."""
    years = B.store_years(pkg, B.target_groups(pkg))
    entries = {}
    for s in STATS:
        entries["%s_%s" % (K2_PARENT, s)] = k2_entry(pkg, s, years)
    for s, name in zip(STATS, k3_columns()):
        entries[name] = k3_entry(pkg, s, years)
    for parent, name in zip(K5_PARENTS, k5_columns()):
        entries[name] = k5_entry(pkg, parent)
    for parent in K6_PARENTS:
        for s in STATS:
            entries["%s_%s" % (parent, s)] = k6_entry(pkg, parent, s, years)
    check_k5_windows(pkg, entries, years)
    k2_known = not _unknown_unsigned(S.StoreColumn.model_validate(entries[k2_columns()[0]]).window)
    header = [
        "# %s -- GENERATED by engine/datasets/defo/features/build_store_k.py ('catalog'); do not edit by hand." % CATALOG_FILE,
        "# The STORE catalog of the defo package's K supplementary store %s (owner ruling K," % K_TEMPLATE,
        "# OWNER_RULINGS_2026-10-05.md; one file per group and panel year %d-%d, built by 'build_store_k.py build')." % (years[0], years[-1]),
        "# dataset.yaml includes this file by sha256: regenerate, review, then update the declared hash.",
        "# K2 epo_mean/_min/_max: the monthly epo after the last-value rule (J2 d), then aggregate_time (D34 strict).",
        "#   Window: %s." % ("computed by aggregate_time from the panel facts" if k2_known else
                             "NOT computed -- the panel store catalog gives epo an unknown window with no signed bound "
                             "(G-LAG); carried as it is, so R8 refuses these columns until a window is signed there"),
        "# K3 deeprec_twsa_k3_mean/_min/_max: aggregate_time's facts from today's panel catalog (J2 b reach carried, F5).",
        "# K5 V15_bare_ground_pct_lag2, V17_herb_cover_pct_lag2, tree_cover_pct_lag2: the year t-2 MOD44B value, declared",
        "#   {2 years backward} from period_start (content ends before the predicted year; checked per store year);",
        "#   their own sum group <parents' group>%s, one verdict (the banned raw trio keeps the parents' group)." % K5_SUM_GROUP_SUFFIX,
        "# K6 <index>_mean/_min/_max of %s: aggregate_time's facts from the windows" % ", ".join(K6_PARENTS),
        "#   ruling L1 (b) signed in the panel store catalog ({3, month, centred}: one year on the annual target).",
        "# These are STORE columns: the G-LINEAGE stand-in (feature-script outputs only) does not run on them (disclosed).",
        "# K1 (spei/amo lag-1-year aggregates) is features/build.py's (J2 a); K4 is catalog.yaml facts alone.",
        "# Store schema sha256 (the ordered column list of every file; stale files are moved aside and rebuilt): %s"
        % schema_sha256(),
    ]
    doc = {"store": STORE_NAME,
           "description": ("Owner ruling K supplementary store of the defo package, %s: %d engineered annual columns "
                           "(K2 epo aggregates after the last-value fill, K3 deeprec_twsa aggregates with the J2 b "
                           "reach, K5 lag-2-year MOD44B trio, K6 the 11 index families' aggregates after L1 b); "
                           "generated by features/build_store_k.py; every fact unverified or, as its parent, assumed."
                           % (K_TEMPLATE, len(entries))),
           "columns": entries}
    body = yaml.safe_dump(doc, sort_keys=False, width=4096, allow_unicode=False, default_flow_style=False)
    return "\n".join(header) + "\n" + body, entries


def check_catalog(pkg):
    """The committed catalog must be what 'catalog' writes, and dataset.yaml must include it by its sha256.
    Returns (sha256, entries)."""
    text, entries = catalog_document(pkg)
    path = pkg.root / CATALOG_FILE
    if not path.is_file() or path.read_text(encoding="utf-8") != text:
        raise BuildError("%s is missing or stale; run 'build_store_k.py catalog', review it and update dataset.yaml's "
                         "sha256" % path)
    sha = B.sha256_file(path)
    inc = {i.path: i.sha256 for i in pkg.dataset.includes}
    if inc.get(CATALOG_FILE) != sha:
        raise BuildError("dataset.yaml includes %s with sha256 %s; the file has %s" % (CATALOG_FILE, inc.get(CATALOG_FILE), sha))
    return sha, entries


# ---------------------------------------------------------------------------------------------------
# values
def _values_view(pkg, parent):
    """The parent's facts as aggregate_time reads them, for the VALUES: when the parent's window is unknown with no
    signed bound, the window is replaced by the parent's own one-month step so aggregate_time reaches its values
    (computed before its facts step, which would refuse); the facts of such a call are discarded by the caller."""
    view = B.parent_view(pkg, parent)
    if _unknown_unsigned(view.window):
        view = SimpleNamespace(**dict(vars(view), window=SimpleNamespace(length=1, unit="month", align="backward")))
    return view


def value_facts(pkg):
    """{parent: the panel store facts that enter the K values}: fill_values and near_sentinel_optout (mask_sentinels,
    read_panel_year) and cadence (aggregate_time places each stored value in its calendar year by it). Read from
    the pinned panel store catalog, recorded in every build record and compared by resume_check, so a re-pinned
    catalog that changes one of them makes the files built before it stale (refused, never kept silently)."""
    out = {}
    for p in (K2_PARENT, K3_PARENT) + K5_PARENTS + K6_PARENTS:
        f = pkg.panel.columns[p]
        out[p] = {"cadence": json.loads(json.dumps(f.cadence.model_dump(mode="json", exclude_none=True))),
                  "fill_values": list(f.fill_values or ()),
                  "near_sentinel_optout": bool(f.near_sentinel_optout)}
    return out


def read_panel_year(pkg, group, year, cells):
    """One panel file's rows of the group's target cells, sentinels masked with value_facts: (frame, unit codes,
    monthly steps, sentinels masked {column: n}). Cells absent from the panel have no rows."""
    path = B.PANEL_TEMPLATE.format(group=group, year=year)
    wanted = [UNIT, YEAR_COL, MONTH_COL, K2_PARENT, K3_PARENT] + list(K5_PARENTS) + list(K6_PARENTS)
    with pq.ParquetFile(path) as pf:
        names = pf.schema_arrow.names
    missing = [c for c in wanted if c not in names]
    if missing:
        raise BuildError("%s lacks the columns %s" % (path, missing))
    frame = pq.read_table(path, columns=wanted).to_pandas()
    frame[UNIT] = frame[UNIT].astype(str)
    frame = frame[frame[UNIT].isin(set(cells.tolist()))].reset_index(drop=True)
    if not (frame[YEAR_COL].to_numpy() == year).all():
        raise BuildError("%s holds rows of other years" % path)
    months = frame[MONTH_COL].to_numpy().astype(np.int64)
    if months.size and (months.min() < 1 or months.max() > 12):
        raise BuildError("%s holds months outside 1..12" % path)
    if frame.duplicated([UNIT, MONTH_COL]).any():
        raise BuildError("%s repeats a (cell, month)" % path)
    facts = {UNIT: SimpleNamespace(role="key_unit", fill_values=(), near_sentinel_optout=True),
             YEAR_COL: SimpleNamespace(role="key_time", fill_values=(), near_sentinel_optout=True),
             MONTH_COL: SimpleNamespace(role="key_time", fill_values=(), near_sentinel_optout=True)}
    vf = value_facts(pkg)
    for c in wanted[3:]:
        facts[c] = SimpleNamespace(role="driver", fill_values=tuple(vf[c]["fill_values"]),
                                   near_sentinel_optout=vf[c]["near_sentinel_optout"])
    frame, report = mask_sentinels(frame, facts)
    codes = np.searchsorted(cells, frame[UNIT].to_numpy(dtype=object).astype(str)).astype(np.int64)
    steps = step_index({YEAR_COL: frame[YEAR_COL].to_numpy().astype(np.int64), MONTH_COL: months},
                       {YEAR_COL: "year", MONTH_COL: "month"}, MONTH)
    return frame, codes, steps, {k: int(v) for k, v in report.masked.items() if v}


class GroupData(object):
    """The group's panel years, read once each: monthly epo and deeprec_twsa of a sliding window of years, and the
    K5 parents' one value per cell-year for every year read."""

    def __init__(self, pkg, group, cells, years):
        self.pkg, self.group, self.cells, self.years = pkg, group, cells, tuple(int(y) for y in years)
        self.n = cells.size
        self._monthly = {}
        self.annual = {}
        self.masked = {}

    def monthly(self, year):
        if year not in self._monthly:
            frame, codes, steps, masked = read_panel_year(self.pkg, self.group, year, self.cells)
            self._monthly[year] = (frame, codes, steps)
            self.masked[year] = masked
            if year not in self.annual:
                self.annual[year] = {p: B._one_value_per_cell(frame[p].to_numpy(dtype=np.float64), codes, self.n,
                                                              p, "a year")[0] for p in K5_PARENTS}
        return self._monthly[year]

    def forget_before(self, year):
        for y in [y for y in self._monthly if y < year]:
            del self._monthly[y]

    def k5_value(self, parent, year):
        """The parent's value of each cell at ``year`` (NaN everywhere for a year the store does not hold)."""
        if year not in self.years:
            return np.full(self.n, np.nan)
        if year not in self.annual:
            self.monthly(year)
        return self.annual[year][parent]


def _place(rows, column, n, year_step):
    st = rows[STEP].to_numpy()
    if not (st == year_step).all():
        raise BuildError("aggregate rows of other steps than %d" % year_step)
    v = np.full(n, np.nan)
    v[rows[UNIT_CODE].to_numpy()] = rows[column].to_numpy(dtype=np.float64)
    return v


def build_group_year(pkg, data, year, k3_catalog):
    """(DataFrame of the K file of ``year``, record dict) from the group's data (years t-2 .. t+1 only)."""
    n = data.n
    year_step = int(step_index({YEAR_COL: np.array([year])}, {YEAR_COL: "year"}, YEAR)[0])
    out = {}
    # K2: last value over the years t-1 .. t+1 (exact for every gap of year t: a filled gap of at most 2 months
    # has its earlier value at most 3 months back and its closing value at most 3 months ahead), then year t only
    window = [y for y in (year - 1, year, year + 1) if y in data.years]
    parts = [data.monthly(y) for y in window]
    codes = np.concatenate([c for _, c, _ in parts])
    steps = np.concatenate([s for _, _, s in parts])
    epo = pd.DataFrame({K2_PARENT: np.concatenate([f[K2_PARENT].to_numpy(dtype=np.float64) for f, _, _ in parts])})
    with contextlib.redirect_stdout(io.StringIO()):
        filled, _ = fill_last_value(epo, codes, steps, (K2_PARENT,), MONTH)
    in_year = np.concatenate([np.full(len(f), y == year) for (f, _, _), y in zip(parts, window)])
    before = epo[K2_PARENT].to_numpy()[in_year]
    after = filled[K2_PARENT].to_numpy()[in_year]
    if not np.array_equal(after[np.isfinite(before)], before[np.isfinite(before)]):
        raise BuildError("internal: the last-value rule changed a value that was present")
    frame_t = pd.DataFrame({K2_PARENT: after})
    view = _values_view(pkg, K2_PARENT)
    for s in STATS:
        rows, _discarded = aggregate_time(frame_t, codes[in_year], steps[in_year], K2_PARENT, view, YEAR, s, None)
        out["%s_%s" % (K2_PARENT, s)] = _place(rows, K2_PARENT, n, year_step)
    # K3 and K6: aggregate_time on year t's rows, its facts checked against the catalog entry (every field but the
    # window equal; the window covered: build_store.py's rule, reach facts at most the catalog's maxima)
    frame, c_t, s_t = data.monthly(year)
    plain = [(K3_PARENT, s, name) for s, name in zip(STATS, k3_columns())]
    plain += [(p, s, "%s_%s" % (p, s)) for p in K6_PARENTS for s in STATS]
    for parent, s, name in plain:
        rows, f = aggregate_time(frame[[parent]], c_t, s_t, parent, B.parent_view(pkg, parent), YEAR, s, None)
        got = B.facts_entry(f, parent, s)
        want = k3_catalog[name]
        bad = ["%s %r, catalog %r" % (k, got.get(k), want.get(k)) for k in sorted(set(got) | set(want))
               if k not in ("window", "provenance") and got.get(k) != want.get(k)]
        bad += B._window_not_covered(got.get("window") or {}, want.get("window") or {})
        if bad:
            raise BuildError("%s %d: aggregate_time's facts on the real rows are not covered by the catalog: %s"
                             % (name, year, "; ".join(bad)))
        out[name] = _place(rows, parent, n, year_step)
    # K5: the same cell's value of year t-2
    for parent, name in zip(K5_PARENTS, k5_columns()):
        out[name] = np.asarray(data.k5_value(parent, year - K5_LAG), dtype=np.float64)
    table = pd.DataFrame({UNIT: data.cells.astype(object), YEAR_COL: np.full(n, year, dtype=np.int64)})
    body = pd.DataFrame({c: np.asarray(out[c], dtype=np.float64) for c in columns()})
    table = pd.concat([table, body], axis=1)
    present = np.zeros(n, dtype=bool)
    present[np.unique(c_t)] = True
    record = {"rows": int(n), "cells_missing_from_panel": int((~present).sum()),
              "epo_months_filled_in_year": int((np.isnan(before) & np.isfinite(after)).sum()),
              "epo_months_missing_after_fill": int(np.isnan(after).sum()),
              "sentinels_masked": {str(y): data.masked.get(y, {}) for y in sorted(set(window) | {year})},
              "nan_share": {c: round(float(np.isnan(body[c].to_numpy()).mean()), 6) for c in columns()}}
    return table, record


def panel_dependencies(group, year, years):
    """{panel file: [size, mtime]} of the years a K file of ``year`` reads (t-2, t-1, t, t+1, those held)."""
    out = {}
    for y in (year - K5_LAG, year - 1, year, year + 1):
        if y in years:
            p = B.PANEL_TEMPLATE.format(group=group, year=y)
            out[p] = [os.path.getsize(p), os.path.getmtime(p)]
    return out


def engine_code_sha256():
    return {rel: B.sha256_file(ENGINE / rel) for rel in ENGINE_CODE}


def out_template(out_root):
    if out_root is None:
        return K_TEMPLATE
    return out_root.rstrip("/\\").replace("\\", "/") + "/" + os.path.basename(K_TEMPLATE)


def resume_check(rec, dst, group, year, now):
    """None when the existing K file ``dst`` may be kept, else the text of what differs. ``now``: today's
    schema_sha256, content_sha256, build_store_content_sha256, engine_code_sha256, value_facts, target_file,
    target_sha256, panel_files (a record without one of them is refused: the key is missing, so it differs)."""
    if not isinstance(rec, dict) or not rec:
        return "no build record"
    why = []
    if rec.get("group") != group or rec.get("year") != int(year) or rec.get("file") != dst:
        why.append("the record is for %r %r (%r)" % (rec.get("group"), rec.get("year"), rec.get("file")))
    for k in ("schema_sha256", "content_sha256", "build_store_content_sha256", "engine_code_sha256", "value_facts",
              "target_file", "target_sha256", "panel_files"):
        if rec.get(k) != now[k]:
            why.append("%s %r, today %r" % (k, rec.get(k), now[k]))
    size = os.path.getsize(dst)
    if rec.get("file_size") != size:
        why.append("file_size %r in the record, %d on disk" % (rec.get("file_size"), size))
    return "; ".join(why) or None


def file_schema_sha256(path):
    """schema_sha256 of an existing K file's own parquet column list (the footer only)."""
    return schema_sha256(pq.read_schema(path).names)


def move_stale_aside(dst, rec_path, old_schema):
    """Move a stale K file (and its build record, when there is one) into <store folder>/MOVED_DIR/<old schema
    sha256, 12 hex>/ (records under _build/ there). Never overwrites and never deletes: a name already taken there
    is refused. Returns the new path of the file."""
    folder = os.path.dirname(dst)
    aside = os.path.join(folder, MOVED_DIR, old_schema[:12])
    aside_build = os.path.join(aside, "_build")
    moves = [(dst, os.path.join(aside, os.path.basename(dst)))]
    if os.path.exists(rec_path):
        moves.append((rec_path, os.path.join(aside_build, os.path.basename(rec_path))))
    taken = [b for _, b in moves if os.path.exists(b)]
    if taken:
        raise BuildError("cannot move the stale file %s aside: %s already exist(s); nothing was moved" % (dst, taken))
    os.makedirs(aside_build, exist_ok=True)
    for a, b in moves:
        os.rename(a, b)                          # same folder tree, so a rename; Windows refuses an existing target
    return moves[0][1]


def build(root, groups=None, out_root=None, echo=print):
    pkg = load_package_files(root)
    catalog_sha, entries = check_signed_catalog(pkg)
    all_groups = B.target_groups(pkg)
    unknown = sorted(set(groups or ()) - set(all_groups))
    if unknown:
        raise BuildError("groups without a target file: %s" % unknown)
    todo = all_groups if not groups else [g for g in all_groups if g in set(groups)]
    years = tuple(int(y) for y in B.store_years(pkg, all_groups))
    template = out_template(out_root)
    records_dir = os.path.join(os.path.dirname(template), "_build")
    os.makedirs(records_dir, exist_ok=True)
    content_sha = content_sha256()
    bs_sha = B.content_sha256()
    eng = engine_code_sha256()
    vf = value_facts(pkg)
    reader = B.load_target_reader(pkg.root)
    target_files = B.template_files(pkg.target_template)
    k3_catalog = {c: entries[c] for c in k3_columns() + k6_columns()}
    schema = schema_sha256()
    echo("K store %s | %d groups | years %d-%d | %d columns (K2 %d, K3 %d, K5 %d, K6 %d) | schema %s"
         % (template, len(todo), years[0], years[-1], len(columns()), len(k2_columns()), len(k3_columns()),
            len(k5_columns()), len(k6_columns()), schema[:12]))
    done = []
    for gi, g in enumerate(todo, 1):
        t0 = time.time()
        tpath = target_files[(g,)]
        target_sha = B.sha256_file(tpath)
        build_years = []
        n_moved = 0
        for year in years:
            dst = template.format(group=g, year=year)
            rec_path = os.path.join(records_dir, "%s_%d.json" % (g, year))
            if os.path.exists(dst):
                old = file_schema_sha256(dst)
                if old != schema:                # an older store schema: stale, moved aside, rebuilt below
                    moved = move_stale_aside(dst, rec_path, old)
                    n_moved += 1
                    echo("    stale schema %s (today %s): %s moved aside to %s" % (old[:12], schema[:12], dst, moved))
            if not os.path.exists(dst):
                build_years.append(year)
                continue
            rec = None
            if os.path.exists(rec_path):
                with open(rec_path, encoding="utf-8") as fh:
                    rec = json.load(fh)
            now = {"schema_sha256": schema, "content_sha256": content_sha, "build_store_content_sha256": bs_sha,
                   "engine_code_sha256": eng,
                   "value_facts": vf, "target_file": tpath, "target_sha256": target_sha,
                   "panel_files": panel_dependencies(g, year, years)}
            why = resume_check(rec, dst, g, year, now)
            if why is not None:
                raise BuildError("%s exists but cannot be kept: %s (record %s); delete it by hand to rebuild"
                                 % (dst, why, rec_path))
        if build_years:
            target = reader.read_target_file(tpath, {"group": g})
            cells = np.unique(target[UNIT].astype(str).to_numpy())
            data = GroupData(pkg, g, cells, years)
            for year in build_years:
                data.forget_before(year - 1)
                table, record = build_group_year(pkg, data, year, k3_catalog)
                dst = template.format(group=g, year=year)
                rec_path = os.path.join(records_dir, "%s_%d.json" % (g, year))
                tmp = os.path.join(records_dir, "_tmp_%d_%s_%d.parquet" % (os.getpid(), g, year))
                pq.write_table(pa.Table.from_pandas(table, preserve_index=False), tmp, compression=COMPRESSION)
                os.rename(tmp, dst)              # Windows: refuses an existing file, so written once
                record.update({"group": g, "year": int(year), "file": dst, "file_size": os.path.getsize(dst),
                               "schema_sha256": schema,
                               "content_sha256": content_sha, "build_store_content_sha256": bs_sha,
                               "engine_code_sha256": eng, "value_facts": vf, "target_file": tpath,
                               "target_sha256": target_sha,
                               "panel_files": panel_dependencies(g, year, years), "catalog_sha256": catalog_sha,
                               "built": time.strftime("%Y-%m-%d %H:%M:%S")})
                with open(rec_path + ".tmp", "w", encoding="utf-8") as fh:
                    json.dump(record, fh, indent=1)
                os.replace(rec_path + ".tmp", rec_path)
        done.append(g)
        echo("  %2d/%d %-34s | %2d files written, %2d kept | %2d stale moved aside | %.1f min"
             % (gi, len(todo), g, len(build_years), len(years) - len(build_years), n_moved, (time.time() - t0) / 60))
    return done


# ---------------------------------------------------------------------------------------------------
# ruling N1 and the owner's signatures (NOT_FILE_CONTENT: catalog facts only, never a file's values)
def signed_catalog_document(pkg):
    """(signed text, {column: entry}, dropped signatures {column: why}) of the K store catalog: catalog_document, the
    N1 families' provenance and a header line naming ruling N1, then the committed catalog's signatures carried
    (features/build_store.py carry_signatures)."""
    text, entries = catalog_document(pkg)
    header, doc = B.split_catalog_text(text)
    for col in N1_PARENTS:
        w = pkg.panel.columns[col].window
        if col not in K6_PARENTS or w is None or w.reach_after_max is None:
            raise BuildError("ruling N1: %s is not a K6 family whose panel window carries the ERSSTv5 reach (%s); the "
                             "shared panel store catalog must carry it first" % (col, w))
        for stat in STATS:
            name = "%s_%s" % (col, stat)
            doc["columns"][name]["provenance"] += (
                "; ruling N1 (OWNER_RULINGS_2026-10-06.md: '%s at lag 2 (ERSSTv5-based, like nino34)'): the panel "
                "window also carries reach_after_max {%g, %s} (the ERSSTv5 filter reach), so the aggregate reaches "
                "further into the next year; R8 still one year on the annual target"
                % (col, w.reach_after_max.value, w.reach_after_max.unit))
            S.StoreColumn.model_validate(doc["columns"][name])
            entries[name] = doc["columns"][name]
    header.insert(len(header) - 1, "# N1 %s: ruling N1 (OWNER_RULINGS_2026-10-06.md) adds the ERSSTv5 reach to the panel window."
                  % ", ".join("%s_mean/_min/_max" % c for c in N1_PARENTS))
    text = B.join_catalog_text(header, doc)
    path = pkg.root / CATALOG_FILE
    committed = path.read_text(encoding="utf-8") if path.is_file() else None
    signed, _, dropped = B.carry_signatures(text, committed)
    return signed, entries, dropped


def check_signed_catalog(pkg):
    """check_catalog with the N1 provenance and the owner's signatures: the committed catalog must be what 'catalog' writes,
    and dataset.yaml must include it by its sha256. Returns (sha256, entries)."""
    signed, entries, dropped = signed_catalog_document(pkg)
    path = pkg.root / CATALOG_FILE
    if not path.is_file() or path.read_text(encoding="utf-8") != signed:
        raise BuildError("%s is missing or stale%s; run 'build_store_k.py catalog', review it and update dataset.yaml's "
                         "sha256" % (path, " (signatures that no longer apply: %s)" % sorted(dropped) if dropped else ""))
    sha = B.sha256_file(path)
    inc = {i.path: i.sha256 for i in pkg.dataset.includes}
    if inc.get(CATALOG_FILE) != sha:
        raise BuildError("dataset.yaml includes %s with sha256 %s; the file has %s" % (CATALOG_FILE, inc.get(CATALOG_FILE), sha))
    return sha, entries


def write_catalog(root, echo=print):
    pkg = B.load_package_files(root)
    text, entries, dropped = signed_catalog_document(pkg)
    path = pkg.root / CATALOG_FILE
    old = path.read_text(encoding="utf-8") if path.is_file() else None
    if old != text:
        tmp = path.with_name(path.name + ".tmp_%d" % os.getpid())
        with open(str(tmp), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(str(tmp), str(path))
    sha = B.sha256_file(path)
    echo("%s: %d columns; sha256 %s%s" % (path, len(entries), sha, "" if old != text else " (unchanged)"))
    for name, why in sorted(dropped.items()):
        echo("  signature NOT carried: %s (%s): the owner signs it again" % (name, why))
    return sha


def main(argv):
    if len(argv) < 2 or argv[0] not in ("catalog", "build"):
        raise SystemExit("usage: py -3.9 -u build_store_k.py catalog <package> | build <package> [--groups=a,b] "
                         "[--out-root=<folder>]")
    opts = dict(a[2:].split("=", 1) for a in argv[2:] if a.startswith("--") and "=" in a)
    extra = [a for a in argv[2:] if not (a.startswith("--") and "=" in a)] + sorted(set(opts) - {"groups", "out-root"})
    if extra:
        raise SystemExit("unknown arguments: %s" % extra)
    if argv[0] == "catalog":
        write_catalog(argv[1])
    else:
        groups = [g for g in opts.get("groups", "").split(",") if g] or None
        build(argv[1], groups=groups, out_root=opts.get("out-root"))


if __name__ == "__main__":
    main(sys.argv[1:])
