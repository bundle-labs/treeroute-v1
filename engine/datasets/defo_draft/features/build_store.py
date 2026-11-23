"""Deforestation package: the builder of the package's annual FEATURES store (plan 1.5 feature script;
owner ruling C 'Defo store'; rulings F5, D34).

    cd "C:\\Users\\moh the ghost\\Desktop\\data set for reserch paper\\engine\\datasets\\defo\\features"
    py -3.9 -u build_store.py catalog ..                   # the store catalog (facts only; reads no data)
    py -3.9 -u build_store.py build ..                     # every group-year file, resumable
    py -3.9 -u build_store.py build .. --groups=costa_rica,pearl_river_delta
    py -3.9 -u build_store.py build .. --out-root=D:/treeroute/<task>/features       (a test store)

WHAT IT BUILDS (ruling C: "Rebuild defo's yearly columns from the monthly panel with the package's
feature script (aggregate_time). Do not read D:/defo_matrix's target copy, train/test flag or pre-lagged
columns.")
  One parquet file per group and panel year (dataset.yaml's first driver template,
  D:/defo_features/{group}_{year}.parquet), one row per target cell (every cell of D:/defo_target's
  group file, sorted), with cell_id, year and these float64 columns:
    <parent>_mean / _min / _max  every monthly-panel column (cadence one month) whose three aggregates
        catalog.yaml declares (role engineered; the parents themselves are not catalog rows since owner
        ruling J4, 2026-10-05: an annual target never reads a monthly row), as
        treeroute.io.aggregate_time builds it (mean, min and max, as shipped: defo_matrix.py:156-166)
        over the calendar year, D34 strict (a unit-year missing any month is NaN), sentinels masked at
        read with the panel store facts (io.sentinel.mask_sentinels). A parent whose own window is
        unknown with no signed bound cannot get an aggregate window (aggregate_time refuses, G-LAG):
        its three aggregates are NOT built and the catalog lists them as such (13 parents, 39
        columns; the owner signs a bound or rules them in the Q34 review).
    <column>  every catalog DRIVER whose panel cadence is one year or static, read as it is: the
        panel repeats it on each month, so the one value of the cell's year is taken (all finite
        values of a cell-year must agree; a static value must also agree across years). Their store
        facts are the panel catalog's (the same column).
    h_nbr1, h_nbr2, h_nbr_cum, h_yrs_since  the owner-kept target-derived columns (ruling Q12; the
        task's ruling list: "declared engineered target-derived columns"), computed from the
        per-year target read through the package's own target reader, every value at year t from
        years <= t-1 only (defo_matrix.py:173-229, reproduced): the mean loss fraction of the 8
        grid neighbours present in the group at t-1 and t-2, the cumulative neighbourhood loss
        before t, and the years since the cell's last non-zero loss before t (99 when none).
        h_lag1-3 and h_cum are NOT built: the engine's history block replaces them (Q12).
  The store catalog (features/defo_features_store_catalog.yaml, included by dataset.yaml with its
  sha256): every built aggregate's facts exactly as aggregate_time computes them (F5: stamp and window
  from the timing helpers over every year the store holds, so the ruled one-year annual lags survive),
  plus the declared facts of the four h_* columns. The 'catalog' command writes it from the facts
  alone; the 'build' command refuses to run when the committed file is not what it would write, and
  checks every aggregate's facts on the real rows against the same computation for that year.

WHY A STORE AND NOT THE ENGINE'S features/build.py HOOK
  (1) The hook runs on the target rows, and the engine's driver reader cannot hand it a monthly source
  on an annual target (its one-to-one (unit, year) join refuses the 12 month rows of a key). (2) The
  hook refuses any output that reads the target (G-HIST), and the four h_* columns do, by the owner's
  ruling. (3) Plan 1.5: the script "writes its outputs to the package's features store with a code
  fingerprint". So the features store is an ordinary driver store the engine reads first; its files
  are built here, once, with a record per file.

RECORDS AND RESUME. Beside the files, _build/<group>_<year>.json records this file's sha256 and its
content_sha256 (the statements that decide what a file holds, see content_sha256), the store
catalog's sha256, the engine's aggregate code's, the panel file read (size, mtime), the target file
read (sha256), the file's size, row counts, masked sentinels, the facts checked, the within-year mixes
of NaN and a value, and the NaN share of every column. An existing file is kept only when its record
says it would be built the same way today (resume_check): the same content_sha256 (or, for a record
written before records carried it, a code sha256 pinned in OUTPUT_IDENTICAL_PREDECESSORS to today's
content_sha256), the same store catalog and aggregate code, the same target file sha256, the
same panel file size and mtime, and the file's own size. Anything else is refused, naming what
differs (delete the file by hand to rebuild: the builder never deletes). Files are written to a
temporary name and renamed (never half-written, never overwritten).

SIGNATURES (owner ruling N S5, FREEZE_SIGNOFF_SHEET.md; datasets/_tools/apply_signoff.py). The owner signs entries of
the committed catalog in place (SIGNATURE_FIELDS: fact_status, reviewed_by, date and a provenance note). 'catalog'
and every check carry a committed signature onto the regenerated entry when every other fact of that entry is
unchanged and the regenerated provenance is where the signed one starts (carry_signatures); an entry whose facts
changed loses its signature, and the command names it (the owner signs again). The resume rule compares the
records' catalog_sha256 with the sha256 of the catalog as generated WITHOUT signatures (a signature changes no fact
a file is checked against; the 924 records were written under the unsigned catalog). These functions write or check
the catalog only, never a group-year file, so they are NOT_FILE_CONTENT (content_sha256 unchanged).

BOOKKEEPING ROWS (owner ruling N S10). catalog.yaml declares a row for every store column (the closed world), so a
monthly panel column that ban.yaml BANS may be a catalog driver row (grace_lwe): it is never read, so the store
plan leaves it out (plan_package); a monthly driver row that is not banned is still refused (J4).

FACTS AGAINST THE CATALOG. Each file's aggregates are checked on the real rows against aggregate_time's
facts for that year (build_group_year); before any file is built or kept, those facts of EVERY store
year are checked against the committed store-catalog entry (check_year_facts_against_catalog): every
field equal, the window of the same length, unit and align, its reach facts at most the catalog's
(the catalog holds their maxima over the years: a leap year reaches one day further).

READ-ONLY on D:/monthly_panel and D:/defo_target. Nothing is read from D:/defo_matrix. Dataset code: it
may name its stores, products and years; the engine may not (G-NONAMES).
"""
# Provenance: OWNER_RULINGS_2026-09-28.md C ('Defo store'), F5 (aggregate facts through the timing helpers),
# D34 (strict missing months); plan 1.5 (feature script, aggregate_time, trailing only, target-derived
# transforms allowed: "years since the last event and neighbour aggregates"); defo_matrix.py:156-166
# (annualise: static columns once, dynamic columns as _mean/_min/_max), :173-229 (hist_block: the h_* block
# from per-year counts, every quantity using only years <= t-1), :210-216 (99 when no earlier loss);
# engine/datasets/_stores/defo_annual_features_schema_catalog.yaml (the catalogs task's seed of the aggregate
# facts, cross-checked by the 'catalog' command).

import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
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

from treeroute.errors import RefusedError  # noqa: E402
from treeroute.io.aggregate import STEP, UNIT_CODE, aggregate_time  # noqa: E402
from treeroute.io.sentinel import mask_sentinels  # noqa: E402
from treeroute.io.steps import step_index  # noqa: E402
from treeroute.package import schema as S  # noqa: E402
from treeroute.package.load import validate_file  # noqa: E402

PANEL_TEMPLATE = "D:/monthly_panel/{group}_monthly_{year}.parquet"
PANEL_CATALOG = "../_stores/monthly_panel_v170_schema_catalog.yaml"
SEED_CATALOG = "../_stores/defo_annual_features_schema_catalog.yaml"
CATALOG_FILE = "features/defo_features_store_catalog.yaml"
TARGET_READER = "ingest/target_reader.py"
STORE_NAME = "defo_annual_features"
# origin: defo_matrix.py:156-166 (annualise: mean, min and max of every time-varying column)
STATS = ("mean", "min", "max")
H_COLUMNS = ("h_nbr1", "h_nbr2", "h_nbr_cum", "h_yrs_since")
# origin: defo_matrix.py:210-216 (years since the last non-zero loss is 99 when there was none)
YRS_SINCE_NONE = 99
TARGET = "loss_frac"
UNIT, YEAR_COL, MONTH_COL = "cell_id", "year", "month"
MONTH = SimpleNamespace(kind="regular", length=1, unit="month")
YEAR = SimpleNamespace(kind="regular", length=1, unit="year")
COMPRESSION = "zstd"
# The functions that decide only whether a group-year file is built, kept or refused, check facts, or read
# the command line, and the two constants naming them: left out of content_sha256, because a change to
# them never changes what a file holds. Every other statement of this file is part of it. build() writes
# the files, so its one write call is pinned by tests/test_route_region_defo_package.py.
NOT_FILE_CONTENT = ("build", "main", "content_sha256", "resume_check", "check_year_facts_against_catalog",
                    "_window_not_covered", "plan_package", "split_catalog_text", "join_catalog_text",
                    "carry_signatures", "signed_catalog_document", "check_signed_catalog", "write_signed_catalog")
NOT_FILE_CONTENT_CONSTANTS = ("NOT_FILE_CONTENT", "NOT_FILE_CONTENT_CONSTANTS", "OUTPUT_IDENTICAL_PREDECESSORS",
                              "SIGNATURE_FIELDS")
# The owner's signature on a store-catalog entry, as datasets/_tools/apply_signoff.py writes it (S5): carried by
# carry_signatures onto a regenerated entry whose other facts are unchanged.
SIGNATURE_FIELDS = ("fact_status", "reviewed_by", "date", "provenance")
# Earlier versions of this file whose files are today's: {their sha256: the content_sha256 of THIS file,
# under which they were verified output-identical}. A record written before records carried content_sha256
# is kept only when its code sha256 is listed here AND the listed content_sha256 equals content_sha256() of
# this file (resume_check); the test file checks the pin. Any later change to the file content drops the pin
# until the identity is verified again.
OUTPUT_IDENTICAL_PREDECESSORS = {
    # 2026-09-29 13:10: the version the first full build ran (the owner, started 2026-09-29 17:46). It
    # differs from this file in the NOT_FILE_CONTENT functions (resume re-checks target, panel and file;
    # facts checked against the catalog), the docstring, and column_plan (2026-10-05, owner ruling J4: the
    # monthly parents are taken from the declared aggregates, because catalog.yaml no longer lists them).
    # Its content_sha256 was 28411a5d7c512fe96baeccca0462db56bd393a961b6f99960f9ca6c522807550. Verified
    # 2026-10-05 (defo J ban-list task): column_plan on today's catalog returns exactly the plan the 13:10
    # version returned on the catalog it ran with (the same 101 monthly, 36 annual and 29 static columns in
    # the same order), and build_group_year rebuilt costa_rica 2019 and pearl_river_delta 2003 equal to the
    # stored files (same columns in the same order, dtypes and values).
    "7d6e39e03aaf8ff1969fe1e4ac8077a2592b02c5eb1cf75b91dc6c14613c8ab3": "87505b6f63939bbf5f6b17d132baf79b7b73df8638afa41bc2648a396a119dfa",
}
FACT_FIELDS_CHECKED = ("dtype", "units", "scope", "stamp", "legal_range", "fill_values", "derived_from",
                       "absent_groups", "fact_status", "product_family", "baseline_period", "observed_through")

# The four target-derived columns: declared facts (plan 1.5: "Every output column is declared:
# derived_from, operation, a backward-only window, reads_target"). Each window is a BACKWARD superset
# ending at the row's own year end (R8 reads the forward edge, so a superset can only raise a lag): the
# content itself ends at t-1, and R8 gives lag 0 on the annual target (a nowcast of year t reads the
# neighbours' loss of years before t). The legal ranges follow from the definitions.
_H_COMMON = {"dtype": "float64", "units": "1", "cadence": {"kind": "regular", "length": 1, "unit": "year"},
             "scope": "unit", "stamp": "period_end", "fill_values": [], "product_family": "Hansen GFC",
             "derived_from": [TARGET], "reads_target": True, "fact_status": "unverified"}
H_FACTS = {
    "h_nbr1": dict(_H_COMMON, window={"length": 2, "unit": "year", "align": "backward"}, legal_range=[0.0, 1.0],
                   operation="neighbour aggregate {grid: the 8 adjacent cells present in the group, stat: mean} "
                             "of the target at year t-1",
                   provenance="mean loss_frac of the 8 grid neighbours at t-1 (defo_matrix.py:180-196, 220; ruling "
                              "Q12: a defo dataset feature); content year t-1 inside the declared window t-1..t; "
                              "features/build_store.py"),
    "h_nbr2": dict(_H_COMMON, window={"length": 3, "unit": "year", "align": "backward"}, legal_range=[0.0, 1.0],
                   operation="neighbour aggregate {grid: the 8 adjacent cells present in the group, stat: mean} "
                             "of the target at year t-2",
                   provenance="mean loss_frac of the 8 grid neighbours at t-2 (defo_matrix.py:180-196, 221; ruling "
                              "Q12); content year t-2 inside the declared window t-2..t; features/build_store.py"),
    "h_nbr_cum": dict(_H_COMMON, window={"length": 25, "unit": "year", "align": "backward"},
                      legal_range=[0.0, 25.0],
                      operation="cumulative sum over the years before t of the neighbour aggregate {grid: the 8 "
                                "adjacent cells present in the group, stat: mean} of the target",
                      provenance="cumulative neighbourhood loss up to t-1 (defo_matrix.py:204, 222; ruling Q12); the "
                                 "target starts in 2001, so the declared 25-year window holds every year before t; "
                                 "features/build_store.py"),
    "h_yrs_since": dict(_H_COMMON, window={"length": 25, "unit": "year", "align": "backward"},
                        legal_range=[1.0, float(YRS_SINCE_NONE)],
                        operation="years since the unit's last year with non-zero target before t (99 when none)",
                        provenance="years since the cell's last non-zero loss, right-censored at t-1, 99 when none "
                                   "(defo_matrix.py:206-216, 223; ruling Q12: 'years since the last event' is an "
                                   "allowed target-derived transform, plan 1.5); features/build_store.py"),
}


class BuildError(Exception):
    """The store cannot be built as declared (fail loudly; nothing is guessed or skipped)."""


# ---------------------------------------------------------------------------------------------------
# the package, its stores and the column plan
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def content_sha256(path=None):
    """sha256 over the parsed statements of this file (or ``path``) that decide what a group-year file
    holds: every top-level statement except the module docstring, the NOT_FILE_CONTENT functions and the
    NOT_FILE_CONTENT_CONSTANTS assignments. ast.dump carries no line numbers or comments, so moving code
    or editing comments and the docstring leaves it unchanged; any change to a reader, the column plan,
    the h_* block, the group-year builder, the catalog code or a constant changes it."""
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


def template_files(template):
    """{key tuple: path} of a '{group}' / '{group}...{year}' template (a plain listing of its folder)."""
    folder, name = os.path.split(template.replace("\\", "/"))
    pattern = re.escape(name).replace(re.escape("{group}"), "(?P<group>.+?)").replace(
        re.escape("{year}"), "(?P<year>[0-9]{4})")
    rx = re.compile("^" + pattern + "$")
    out = {}
    if not os.path.isdir(folder):
        return out
    for entry in sorted(os.listdir(folder)):
        m = rx.match(entry)
        if m and os.path.isfile(os.path.join(folder, entry)):
            key = (m.group("group"),) + ((int(m.group("year")),) if "year" in m.groupdict() else ())
            out[key] = os.path.join(folder, entry).replace("\\", "/")
    return out


def load_package_files(root):
    """dataset.yaml, catalog.yaml and the panel store catalog (its sha256 checked against dataset.yaml),
    read through the engine's schema. The package is not loaded whole: the features catalog this script
    writes is one of its includes."""
    root = Path(root).resolve()
    ds = validate_file(root / "dataset.yaml", S.DatasetFile)
    cat = validate_file(root / "catalog.yaml", S.PackageCatalog)
    inc = {i.path: i.sha256 for i in ds.includes}
    if PANEL_CATALOG not in inc:
        raise BuildError("dataset.yaml does not include the panel store catalog %s" % PANEL_CATALOG)
    got = sha256_file(root / PANEL_CATALOG)
    if got != inc[PANEL_CATALOG]:
        raise BuildError("the panel store catalog has sha256 %s, dataset.yaml declares %s" % (got, inc[PANEL_CATALOG]))
    panel = validate_file(root / PANEL_CATALOG, S.StoreCatalog)
    drivers = list(ds.stores.drivers)
    if PANEL_TEMPLATE not in drivers:
        raise BuildError("dataset.yaml's drivers do not name the monthly panel %s" % PANEL_TEMPLATE)
    features = drivers[0]
    if features == PANEL_TEMPLATE or "{group}" not in features or "{year}" not in features:
        raise BuildError("dataset.yaml's FIRST driver store must be the features store '{group}...{year}', got %r"
                         % features)
    if ds.stores.features is not None and ds.stores.features != features:
        raise BuildError("dataset.yaml's stores.features %r is not its first driver store %r"
                         % (ds.stores.features, features))
    return SimpleNamespace(root=root, dataset=ds, catalog=cat, panel=panel, features_template=features,
                           target_template=ds.stores.target)


def cadence_key(cadence):
    return (cadence.kind, cadence.length, cadence.unit)


def column_plan(pkg):
    """The store's columns from the catalog's roles and the panel's cadences (catalog order). The monthly
    parents are the one-month panel columns whose aggregates catalog.yaml declares (role engineered), in the
    order of their first aggregate; the parents themselves are not catalog rows (owner ruling J4: an annual
    target never reads a monthly row). A monthly panel column declared as a driver is refused."""
    cols = pkg.catalog.columns
    monthly, annual, static = [], [], []
    for c, f in cols.items():
        if f.role == "engineered":
            head, _, stat = c.rpartition("_")
            if (stat in STATS and head not in monthly and head in pkg.panel.columns
                    and cadence_key(pkg.panel.columns[head].cadence) == ("regular", 1, "month")):
                monthly.append(head)
            continue
        if f.role != "driver" or c not in pkg.panel.columns:
            continue
        key = cadence_key(pkg.panel.columns[c].cadence)
        if key == ("regular", 1, "month"):
            raise BuildError("driver %s is a monthly panel column: declare its aggregates %s_mean/_min/_max "
                             "(role engineered), not the column itself (owner ruling J4)" % (c, c))
        elif key == ("regular", 1, "year"):
            annual.append(c)
        elif key[0] == "static":
            static.append(c)
        else:
            raise BuildError("driver %s has the panel cadence %s, which this store does not build" % (c, key))
    for c in H_COLUMNS:
        if c not in cols or cols[c].role != "engineered":
            raise BuildError("catalog.yaml must declare %s with role engineered" % c)
    for p in monthly:
        for s in STATS:
            name = "%s_%s" % (p, s)
            if name not in cols or cols[name].role != "engineered":
                raise BuildError("catalog.yaml must declare the aggregate %s with role engineered" % name)
    if not monthly or not annual or not static:
        raise BuildError("empty column plan: %d monthly, %d annual, %d static" % (len(monthly), len(annual), len(static)))
    return SimpleNamespace(monthly=tuple(monthly), annual=tuple(annual), static=tuple(static), h=H_COLUMNS)


def parent_view(pkg, name):
    """A panel column's store facts as the facts record aggregate_time reads."""
    f = pkg.panel.columns[name]
    return SimpleNamespace(name=name, role="driver", **{k: getattr(f, k) for k in S.StoreColumn.model_fields})


def store_years(pkg, groups):
    """The panel years every group holds (one common set, or refused)."""
    files = template_files(PANEL_TEMPLATE)
    sets = {}
    for g in groups:
        sets[g] = tuple(sorted(y for (gg, y) in files if gg == g))
        if not sets[g]:
            raise BuildError("group %s has no monthly panel file" % g)
    distinct = set(sets.values())
    if len(distinct) != 1:
        raise BuildError("the groups hold different panel years: %s" % sorted(distinct))
    return distinct.pop()


def target_groups(pkg):
    return sorted(k[0] for k in template_files(pkg.target_template))


# ---------------------------------------------------------------------------------------------------
# aggregate facts (F5) and the store catalog
def _synthetic_facts(pkg, parent, stat, years):
    """aggregate_time's computed facts over the given years (one unit, every month; the values do not
    enter the facts)."""
    years = np.asarray(years, dtype=np.int64)
    yy = np.repeat(years, 12)
    mm = np.tile(np.arange(1, 13, dtype=np.int64), len(years))
    steps = step_index({YEAR_COL: yy, MONTH_COL: mm}, {YEAR_COL: "year", MONTH_COL: "month"}, MONTH)
    frame = pd.DataFrame({parent: np.zeros(len(yy))})
    _, facts = aggregate_time(frame, np.zeros(len(yy), dtype=np.int64), steps, parent, parent_view(pkg, parent),
                              YEAR, stat, None)
    return facts


def aggregate_facts_or_refusal(pkg, parent, stat, years):
    """(facts, None) or (None, the G-LAG refusal text) for one aggregate."""
    try:
        return _synthetic_facts(pkg, parent, stat, years), None
    except RefusedError as exc:
        if getattr(exc, "rule", None) != "G-LAG":
            raise
        return None, str(exc)


def _plain(value):
    """Facts values as YAML-ready plain data (pydantic models, dataclasses, enums, tuples)."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if hasattr(value, "model_dump"):
        return {k: _plain(v) for k, v in value.model_dump(exclude_none=True).items()}
    if hasattr(value, "value") and hasattr(type(value), "__members__"):
        return value.value
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return {k: _plain(getattr(value, k)) for k in value.__dataclass_fields__ if getattr(value, k) is not None}
    if isinstance(value, SimpleNamespace):
        return {k: _plain(v) for k, v in vars(value).items() if v is not None}
    raise BuildError("cannot write the fact value %r" % (value,))


def facts_entry(facts, parent, stat):
    """The store-catalog entry of one aggregate: aggregate_time's facts, with the aggregate's own
    declaration (operation) and provenance. Validated by the engine schema."""
    window = _plain(facts.window)
    window = {k: window[k] for k in ("length", "unit", "align", "max_length", "reach_after_max", "reach_before_max")
              if k in window}
    entry = {}
    for field in S.StoreColumn.model_fields:
        if field in ("window", "operation", "provenance", "reviewed_by", "date"):
            continue
        v = getattr(facts, field, None)
        if field == "cadence":
            v = {"kind": facts.cadence.kind, "length": facts.cadence.length, "unit": facts.cadence.unit}
        v = _plain(v)
        if v is None or v == {} or (v == [] and field != "fill_values"):
            continue
        if field == "near_sentinel_optout" and v is False:
            continue
        entry[field] = v
    if getattr(facts, "reads_target", None):
        raise BuildError("the parent of %s_%s reads the target" % (parent, stat))
    entry["reads_target"] = False
    entry["window"] = window
    entry["operation"] = "aggregate_time {window: 1 year, stat: %s}" % stat
    entry["provenance"] = ("%s of the monthly panel column %s over each calendar year, built by treeroute.io."
                           "aggregate_time (D34 strict; stamp and window computed, F5) in features/build_store.py; "
                           "shipped equivalent defo_matrix.py:156-166" % (stat, parent))
    S.StoreColumn.model_validate(entry)
    return entry


def catalog_document(pkg):
    """(text, built aggregates {name: entry}, refused {name: reason}) of the features store catalog."""
    plan = column_plan(pkg)
    years = store_years(pkg, target_groups(pkg))
    seed = validate_file(pkg.root / SEED_CATALOG, S.StoreCatalog)
    columns, refused = {}, {}
    for p in plan.monthly:
        for s in STATS:
            name = "%s_%s" % (p, s)
            facts, why = aggregate_facts_or_refusal(pkg, p, s, years)
            if facts is None:
                refused[name] = why
                continue
            entry = facts_entry(facts, p, s)
            # cross-check with the catalogs task's seed (every fact the seed types, the window excepted)
            want = seed.columns.get(name)
            if want is None:
                raise BuildError("the seed catalog has no entry %s" % name)
            got = S.StoreColumn.model_validate(entry)
            for field in ("dtype", "units", "cadence", "scope", "stamp", "legal_range", "fill_values",
                          "product_family", "lineage", "baseline_period", "observed_through", "derived_from",
                          "operation", "reads_target", "fact_status", "absent_groups"):
                if getattr(got, field) != getattr(want, field):
                    raise BuildError("%s.%s: aggregate_time gives %r, the seed catalog %r"
                                     % (name, field, getattr(got, field), getattr(want, field)))
            columns[name] = entry
    for h in plan.h:
        S.StoreColumn.model_validate(H_FACTS[h])
        columns[h] = H_FACTS[h]
    header = [
        "# %s -- GENERATED by engine/datasets/defo/features/build_store.py ('catalog'); do not edit by hand." % CATALOG_FILE,
        "# The STORE catalog of the defo package's features store %s (one file per group and panel" % pkg.features_template,
        "# year; built by 'build_store.py build'). dataset.yaml includes this file by sha256: regenerate, review,",
        "# then update the declared hash.",
        "# Aggregates: <parent>_mean/_min/_max of the catalog drivers whose monthly-panel cadence is one month. Every",
        "# fact is what treeroute.io.aggregate_time computes from the parent's panel facts over the store's years",
        "# %d-%d (ruling F5: stamp and window from the timing helpers; reach facts included), with the aggregate's own" % (years[0], years[-1]),
        "# operation. Cross-checked against ../../_stores/defo_annual_features_schema_catalog.yaml (the seed) on every",
        "# typed fact. Annual and static drivers are stored as they are; their facts are the panel catalog's.",
        "# h_nbr1, h_nbr2, h_nbr_cum, h_yrs_since: declared facts (build_store.py H_FACTS), target-derived (ruling Q12).",
        "# NOT BUILT (%d aggregates): the parent's window is unknown with no signed bound, so aggregate_time refuses" % len(refused),
        "# to compute the aggregate's window (G-LAG): %s." % ", ".join(sorted({n.rsplit("_", 1)[0] for n in refused})),
        "# They are declared in catalog.yaml (role engineered) but absent from the store; the owner signs a bound",
        "# or rules them in the Q34 review.",
    ]
    doc = {"store": STORE_NAME,
           "description": ("Engineered annual columns of the defo package, store %s: %d aggregate_time columns of "
                           "the monthly panel and the 4 target-derived h_* columns; generated by "
                           "features/build_store.py; every fact unverified or, as its parent, assumed."
                           % (pkg.features_template, len(columns) - len(plan.h))),
           "columns": columns}
    body = yaml.safe_dump(doc, sort_keys=False, width=4096, allow_unicode=False, default_flow_style=False)
    return "\n".join(header) + "\n" + body, columns, refused


def check_catalog(pkg):
    """The committed catalog must be what 'catalog' writes, and dataset.yaml must include it by its
    sha256. Returns (sha256, built aggregate names, refused names)."""
    text, columns, refused = catalog_document(pkg)
    path = pkg.root / CATALOG_FILE
    if not path.is_file() or path.read_text(encoding="utf-8") != text:
        raise BuildError("%s is missing or stale; run 'build_store.py catalog', review it and update dataset.yaml's "
                         "sha256" % path)
    sha = sha256_file(path)
    inc = {i.path: i.sha256 for i in pkg.dataset.includes}
    if inc.get(CATALOG_FILE) != sha:
        raise BuildError("dataset.yaml includes %s with sha256 %s; the file has %s" % (CATALOG_FILE,
                                                                                    inc.get(CATALOG_FILE), sha))
    return sha, tuple(n for n in columns if n not in H_COLUMNS), tuple(sorted(refused))


# ---------------------------------------------------------------------------------------------------
# the target-derived block (defo_matrix.py:173-229, only the four kept columns)
def load_target_reader(root):
    path = Path(root) / TARGET_READER
    spec = importlib.util.spec_from_file_location("defo_target_reader_%s" % sha256_file(path)[:12], str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def grid_indices(units, group):
    ix, iy = [], []
    for u in units:
        head, _, tail_y = str(u).rpartition("_")
        head2, _, tail_x = head.rpartition("_")
        if head2 != group:
            raise BuildError("unit %r does not read as '%s_<ix>_<iy>'" % (u, group))
        try:
            ix.append(int(tail_x))
            iy.append(int(tail_y))
        except ValueError:
            raise BuildError("unit %r: the grid indices are not integers" % u) from None
    return np.asarray(ix, dtype=np.int64), np.asarray(iy, dtype=np.int64)


def h_block(target, group):
    """{column: (cells, years) array}, cells sorted, years every target year: each value at year t from
    target years <= t-1 only. Returns (cells, years, block).

    The cells that count are the cells with year-2000 forest, i.e. with a defined loss fraction: the
    shipped block pivoted the target and so dropped every all-NaN cell (pandas pivot_table, dropna)
    before it looked for neighbours (defo_matrix.py:175-190). A cell's labels are all defined or all
    NaN (the forest mask is static, so the set never depends on a later year; a mix is refused).
    Cells without forest get NaN in every h_* column, as they had no row in the shipped block; their
    labels are NaN, so no router fits or scores them."""
    t = target[[UNIT, YEAR_COL, TARGET]]
    cells = np.unique(t[UNIT].astype(str).to_numpy())
    years = np.arange(int(t[YEAR_COL].min()), int(t[YEAR_COL].max()) + 1, dtype=np.int64)
    A = np.full((cells.size, years.size), np.nan)
    ci = np.searchsorted(cells, t[UNIT].astype(str).to_numpy())
    yi = t[YEAR_COL].to_numpy().astype(np.int64) - years[0]
    A[ci, yi] = t[TARGET].to_numpy(dtype=np.float64)
    finite = np.isfinite(A)
    member = finite.all(axis=1)
    mixed = finite.any(axis=1) & ~member
    if mixed.any():
        raise BuildError("%s: %d cells hold defined AND missing loss fractions (e.g. %s); the neighbour set would "
                         "depend on the year" % (group, int(mixed.sum()), cells[mixed][:3].tolist()))
    A0 = np.nan_to_num(A)
    ix, iy = grid_indices(cells, group)
    pos = {(int(a), int(b)): k for k, (a, b) in enumerate(zip(ix.tolist(), iy.tolist())) if member[k]}
    nbr_sum = np.zeros_like(A0)
    nbr_n = np.zeros_like(A0)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            src = np.array([pos.get((int(a) + dx, int(b) + dy), -1) for a, b in zip(ix.tolist(), iy.tolist())],
                           dtype=np.int64)
            m = src >= 0
            nbr_sum[m] += A0[src[m]]
            nbr_n[m] += 1.0
    nbr = np.where(nbr_n > 0, nbr_sum / np.maximum(nbr_n, 1), np.nan)

    def shift(M, k):
        out = np.full_like(M, np.nan)
        if k < M.shape[1]:
            out[:, k:] = M[:, :M.shape[1] - k]
        return out

    nbr0 = np.nan_to_num(nbr)
    # strictly before year t: an EXCLUSIVE running sum. The shipped cumsum(nbr) - nbr (defo_matrix.py:204) gives
    # the same number up to rounding, but that rounding depends on year t's own value, so it is not built from
    # years <= t-1 alone; the exclusive sum is (tests/test_route_region_defo_package.py checks both facts).
    ncum = np.zeros_like(nbr0)
    if nbr0.shape[1] > 1:
        ncum[:, 1:] = np.cumsum(nbr0[:, :-1], axis=1)
    hot = A0 > 0
    ysl = np.full(A0.shape, float(YRS_SINCE_NONE))
    last = np.full(cells.size, -1, dtype=np.int64)
    seen = np.zeros(cells.size, dtype=bool)
    for j, y in enumerate(years.tolist()):
        ysl[:, j] = np.where(seen, y - last, float(YRS_SINCE_NONE))
        last = np.where(hot[:, j], y, last)
        seen = seen | hot[:, j]
    block = {"h_nbr1": shift(nbr, 1), "h_nbr2": shift(nbr, 2), "h_nbr_cum": ncum, "h_yrs_since": ysl}
    for k in block:
        block[k][~member] = np.nan
    return cells, years, block


# ---------------------------------------------------------------------------------------------------
# one group-year
def _facts_key(facts):
    w = _plain(facts.window)
    return (repr(sorted(w.items())), repr(cadence_key(facts.cadence)),
            repr([_plain(getattr(facts, f, None)) for f in FACT_FIELDS_CHECKED]))


def _one_value_per_cell(values, codes, n_cells, column, what):
    """The one finite value of each cell among its rows (NaN when none); refuses two different finite
    values. Returns (values per cell, cells that mixed NaN with the value)."""
    frame = pd.DataFrame({"c": codes, "v": values})
    finite = frame[np.isfinite(frame["v"].to_numpy())]
    g = finite.groupby("c")["v"]
    lo, hi = g.min(), g.max()
    bad = lo.index[(hi - lo).to_numpy() != 0]
    if len(bad):
        raise BuildError("%s: %s holds %d cells with more than one value in %s" % (column, what, len(bad), what))
    out = np.full(n_cells, np.nan)
    out[lo.index.to_numpy()] = lo.to_numpy()
    n_all = frame.groupby("c")["v"].size()
    n_fin = g.size().reindex(n_all.index, fill_value=0)
    mixed = int(((n_fin > 0) & (n_fin < n_all)).sum())
    return out, mixed


def build_group_year(pkg, plan, group, year, cells, h_years, h, built, synthetic, static_first):
    """(DataFrame of the group-year file, record dict)."""
    path = PANEL_TEMPLATE.format(group=group, year=year)
    wanted = [UNIT, YEAR_COL, MONTH_COL] + list(plan.static) + list(plan.annual) + list(plan.monthly)
    with pq.ParquetFile(path) as pf:
        names = pf.schema_arrow.names
    missing = [c for c in wanted if c not in names]
    if missing:
        raise BuildError("%s lacks the columns %s" % (path, missing[:10]))
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
    for c in wanted[3:]:
        f = pkg.panel.columns[c]
        facts[c] = SimpleNamespace(role="driver", fill_values=tuple(f.fill_values or ()),
                                   near_sentinel_optout=bool(f.near_sentinel_optout))
    frame, report = mask_sentinels(frame, facts)
    codes = np.searchsorted(cells, frame[UNIT].to_numpy(dtype=object).astype(str)).astype(np.int64)
    steps = step_index({YEAR_COL: frame[YEAR_COL].to_numpy().astype(np.int64), MONTH_COL: months},
                       {YEAR_COL: "year", MONTH_COL: "month"}, MONTH)
    year_step = int(step_index({YEAR_COL: np.array([year])}, {YEAR_COL: "year"}, YEAR)[0])
    n = cells.size
    out = {}
    mixed = {}
    for c in plan.static:
        v, mix = _one_value_per_cell(frame[c].to_numpy(dtype=np.float64), codes, n, c, "a year")
        prev = static_first.get(c)
        if prev is None:
            static_first[c] = v
        else:
            differ = ~((v == prev) | (np.isnan(v) & np.isnan(prev)))
            if differ.any():
                raise BuildError("%s: static column %s changes between years in %d cells (year %d)"
                                 % (group, c, int(differ.sum()), year))
        out[c], mixed[c] = v, mix
    for c in plan.annual:
        out[c], mixed[c] = _one_value_per_cell(frame[c].to_numpy(dtype=np.float64), codes, n, c, "a year")
    checked = 0
    built_set = set(built)
    for p in plan.monthly:
        for s in STATS:
            name = "%s_%s" % (p, s)
            if name not in built_set:
                continue
            rows, f = aggregate_time(frame[[p]], codes, steps, p, parent_view(pkg, p), YEAR, s, None)
            key = (name, year)
            if key not in synthetic:
                synthetic[key] = _facts_key(_synthetic_facts(pkg, p, s, [year]))
            if _facts_key(f) != synthetic[key]:
                raise BuildError("%s %d: aggregate_time's facts on the real rows differ from its facts for the year "
                                 "(%s)" % (name, year, _facts_key(f)))
            checked += 1
            st = rows[STEP].to_numpy()
            if not (st == year_step).all():
                raise BuildError("%s %d: aggregate rows of other steps" % (name, year))
            v = np.full(n, np.nan)
            v[rows[UNIT_CODE].to_numpy()] = rows[p].to_numpy(dtype=np.float64)
            out[name] = v
    j = int(np.searchsorted(h_years, year))
    if j >= h_years.size or h_years[j] != year:
        raise BuildError("%s: the target has no year %d for the h_* block" % (group, year))
    for c in plan.h:
        out[c] = h[c][:, j]
    table = pd.DataFrame({UNIT: cells.astype(object), YEAR_COL: np.full(n, year, dtype=np.int64)})
    order = list(plan.static) + list(plan.annual) + [c for c in built] + list(plan.h)
    body = pd.DataFrame({c: np.asarray(out[c], dtype=np.float64) for c in order})
    table = pd.concat([table, body], axis=1)
    present = np.zeros(n, dtype=bool)
    present[np.unique(codes)] = True
    record = {"panel_file": path, "panel_size": os.path.getsize(path), "panel_mtime": os.path.getmtime(path),
              "rows": int(n), "cells_missing_from_panel": int((~present).sum()),
              "sentinels_masked": {k: int(v) for k, v in report.masked.items() if v},
              "aggregate_facts_checked": checked,
              "cells_mixing_nan_and_a_value": {k: v for k, v in mixed.items() if v},
              "nan_share": {c: round(float(np.isnan(body[c].to_numpy()).mean()), 6) for c in order}}
    return table, record


# ---------------------------------------------------------------------------------------------------
def out_template(pkg, out_root):
    if out_root is None:
        return pkg.features_template
    name = os.path.basename(pkg.features_template)
    return out_root.rstrip("/\\").replace("\\", "/") + "/" + name


# ---------------------------------------------------------------------------------------------------
# resume and the facts against the catalog (NOT_FILE_CONTENT: they never change what a file holds)
def _window_not_covered(got, want):
    """What of one year's aggregate window is not covered by the catalog's: length, unit and align
    equal and the same window facts present; each reach fact (max_length, reach_after_max,
    reach_before_max) in the same unit and at most the catalog's value. Returns a list of texts (empty
    when covered)."""
    bad = []
    base = ("length", "unit", "align")
    for k in base:
        if got.get(k) != want.get(k):
            bad.append("window.%s %r, catalog %r" % (k, got.get(k), want.get(k)))
    extra = sorted(set(got) - set(want) - set(base))
    missing = sorted(set(want) - set(got) - set(base))
    if extra or missing:
        bad.append("window facts %s absent from the catalog, catalog facts %s absent from the year" % (extra, missing))
    for k in sorted((set(got) & set(want)) - set(base)):
        g, w = got[k], want[k]
        if isinstance(g, dict) and isinstance(w, dict) and set(g) == set(w) == {"value", "unit"}:
            if g["unit"] != w["unit"] or not g["value"] <= w["value"]:
                bad.append("window.%s %r exceeds the catalog's %r" % (k, g, w))
        elif g != w:
            bad.append("window.%s %r, catalog %r" % (k, g, w))
    return bad


def check_year_facts_against_catalog(pkg, plan, built, years, synthetic):
    """Every built aggregate's facts for each single store year -- what build_group_year checks each
    file's real rows against -- must be covered by its entry in the committed store catalog: every
    field equal but the window, which _window_not_covered compares (the catalog's reach facts are the
    maxima over the years). Fills ``synthetic`` with the per-year facts keys build_group_year reuses.
    Returns the number of (aggregate, year) facts checked; refuses the first one not covered."""
    doc = yaml.safe_load((pkg.root / CATALOG_FILE).read_text(encoding="utf-8"))
    entries = doc.get("columns") or {}
    built_set = set(built)
    n = 0
    for p in plan.monthly:
        for s in STATS:
            name = "%s_%s" % (p, s)
            if name not in built_set:
                continue
            want = entries.get(name)
            if not isinstance(want, dict):
                raise BuildError("the store catalog has no entry for the built aggregate %s" % name)
            for year in years:
                f = _synthetic_facts(pkg, p, s, [year])
                synthetic[(name, int(year))] = _facts_key(f)
                got = facts_entry(f, p, s)
                bad = ["%s %r, catalog %r" % (k, got.get(k), want.get(k))
                       for k in sorted(set(got) | set(want)) if k != "window" and got.get(k) != want.get(k)]
                bad += _window_not_covered(got.get("window") or {}, want.get("window") or {})
                if bad:
                    raise BuildError("%s %d: the year's facts are not covered by the store catalog entry: %s"
                                     % (name, year, "; ".join(bad)))
                n += 1
    return n


def resume_check(rec, dst, group, year, now):
    """None when the existing group-year file ``dst`` may be kept, else the text of what differs.

    rec  its build record (None when there is none)
    now  today's code_sha256, content_sha256, catalog_sha256, engine_aggregate_sha256, target_file,
         target_sha256, panel_file, panel_size, panel_mtime
    Kept only when the record says the file would be built the same way today: the same content
    (content_sha256; a record without it: the same code sha256, or a code sha256 pinned in
    OUTPUT_IDENTICAL_PREDECESSORS whose content_sha256 is today's), the same store catalog, aggregate
    code, target file and its sha256, panel file and its size and mtime, and the file's own size."""
    if not isinstance(rec, dict) or not rec:
        return "no build record"
    why = []
    if rec.get("group") != group or rec.get("year") != int(year) or rec.get("file") != dst:
        why.append("the record is for %r %r (%r)" % (rec.get("group"), rec.get("year"), rec.get("file")))
    if "content_sha256" in rec:
        if rec["content_sha256"] != now["content_sha256"]:
            why.append("built by code that writes other content (content_sha256 %s, today %s)"
                       % (rec["content_sha256"], now["content_sha256"]))
    elif rec.get("code_sha256") != now["code_sha256"]:
        pinned = OUTPUT_IDENTICAL_PREDECESSORS.get(rec.get("code_sha256"))
        if pinned is None:
            why.append("built by other code (code_sha256 %s), not a pinned output-identical predecessor"
                       % rec.get("code_sha256"))
        elif pinned != now["content_sha256"]:
            why.append("built by the predecessor %s, whose content_sha256 %s is not today's %s"
                       % (rec.get("code_sha256"), pinned, now["content_sha256"]))
    for k in ("catalog_sha256", "engine_aggregate_sha256", "target_file", "target_sha256", "panel_file",
              "panel_size", "panel_mtime"):
        if rec.get(k) != now[k]:
            why.append("%s %r, today %r" % (k, rec.get(k), now[k]))
    size = os.path.getsize(dst)
    if rec.get("file_size") != size:
        why.append("file_size %r in the record, %d on disk" % (rec.get("file_size"), size))
    return "; ".join(why) or None


def build(root, groups=None, out_root=None, echo=print):
    pkg = plan_package(load_package_files(root))
    plan = column_plan(pkg)
    # the resume key and the records carry the sha256 of the catalog as generated without the owner's signatures
    _, catalog_sha, built, refused = check_signed_catalog(pkg)
    all_groups = target_groups(pkg)
    todo = all_groups if not groups else [g for g in all_groups if g in set(groups)]
    unknown = sorted(set(groups or ()) - set(all_groups))
    if unknown:
        raise BuildError("groups without a target file: %s" % unknown)
    years = store_years(pkg, all_groups)
    template = out_template(pkg, out_root)
    folder = os.path.dirname(template)
    records_dir = os.path.join(folder, "_build")
    os.makedirs(records_dir, exist_ok=True)
    code_sha = sha256_file(__file__)
    content_sha = content_sha256()
    agg_sha = sha256_file(ENGINE / "treeroute" / "io" / "aggregate.py")
    reader = load_target_reader(pkg.root)
    target_files = template_files(pkg.target_template)
    synthetic = {}
    n_facts = check_year_facts_against_catalog(pkg, plan, built, years, synthetic)
    echo("features store %s | %d groups | years %d-%d | %d aggregates built, %d not built (G-LAG) | %d annual, "
         "%d static, %d h_* | %d year facts covered by the catalog"
         % (template, len(todo), years[0], years[-1], len(built), len(refused), len(plan.annual),
            len(plan.static), len(plan.h), n_facts))
    done = []
    for gi, g in enumerate(todo, 1):
        t0 = time.time()
        tpath = target_files[(g,)]
        target_sha = sha256_file(tpath)
        h_state = None
        static_first = {}
        n_written = n_kept = 0
        for year in years:
            dst = template.format(group=g, year=year)
            rec_path = os.path.join(records_dir, "%s_%d.json" % (g, year))
            panel = PANEL_TEMPLATE.format(group=g, year=year)
            if os.path.exists(dst):
                rec = None
                if os.path.exists(rec_path):
                    with open(rec_path, encoding="utf-8") as fh:
                        rec = json.load(fh)
                now = {"code_sha256": code_sha, "content_sha256": content_sha, "catalog_sha256": catalog_sha,
                       "engine_aggregate_sha256": agg_sha, "target_file": tpath, "target_sha256": target_sha,
                       "panel_file": panel, "panel_size": os.path.getsize(panel),
                       "panel_mtime": os.path.getmtime(panel)}
                why = resume_check(rec, dst, g, year, now)
                if why is None:
                    n_kept += 1
                    continue
                raise BuildError("%s exists but cannot be kept: %s (record %s); delete it by hand to rebuild"
                                 % (dst, why, rec_path))
            if h_state is None:
                h_state = h_block(reader.read_target_file(tpath, {"group": g}), g)
            cells, h_years, h = h_state
            table, record = build_group_year(pkg, plan, g, year, cells, h_years, h, built, synthetic,
                                             static_first)
            # the temporary file sits in _build/, never under a name the store template would list
            tmp = os.path.join(records_dir, "_tmp_%d_%s_%d.parquet" % (os.getpid(), g, year))
            pq.write_table(pa.Table.from_pandas(table, preserve_index=False), tmp, compression=COMPRESSION)
            os.rename(tmp, dst)                  # Windows: refuses an existing file, so written once
            record.update({"group": g, "year": int(year), "file": dst, "file_size": os.path.getsize(dst),
                           "code_sha256": code_sha, "content_sha256": content_sha, "catalog_sha256": catalog_sha,
                           "engine_aggregate_sha256": agg_sha, "target_file": tpath, "target_sha256": target_sha,
                           "year_facts_covered_by_catalog": len(built),
                           "built": time.strftime("%Y-%m-%d %H:%M:%S"),
                           "aggregates_not_built": list(refused)})
            with open(rec_path + ".tmp", "w", encoding="utf-8") as fh:
                json.dump(record, fh, indent=1)
            os.replace(rec_path + ".tmp", rec_path)
            n_written += 1
        done.append(g)
        echo("  %2d/%d %-34s %6s cells | %2d files written, %2d kept | %.1f min"
             % (gi, len(todo), g, h_state[0].size if h_state is not None else "-", n_written, n_kept,
                (time.time() - t0) / 60))
    return done


def write_catalog(root, echo=print):
    pkg = load_package_files(root)
    text, columns, refused = catalog_document(pkg)
    path = pkg.root / CATALOG_FILE
    old = path.read_text(encoding="utf-8") if path.is_file() else None
    if old != text:
        tmp = path.with_name(path.name + ".tmp_%d" % os.getpid())
        with open(str(tmp), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(str(tmp), str(path))
    sha = sha256_file(path)
    echo("%s: %d columns (%d aggregates, %d h_*), %d aggregates not built (G-LAG); sha256 %s%s"
         % (path, len(columns), len(columns) - len(H_COLUMNS), len(H_COLUMNS), len(refused), sha,
            "" if old != text else " (unchanged)"))
    return sha


# ---------------------------------------------------------------------------------------------------
# signatures and bookkeeping rows (NOT_FILE_CONTENT: they write or check the catalog, never a group-year file)
def plan_package(pkg):
    """``pkg`` without the catalog driver rows that the store does not build because ban.yaml bans them and they are
    monthly panel columns (owner ruling N S10: closed-world rows, never read). Any other row is kept, so a monthly
    driver row that is not banned is still refused by column_plan (J4)."""
    ban = validate_file(pkg.root / "ban.yaml", S.BanFile)
    drop = [c for c, f in pkg.catalog.columns.items()
            if f.role == "driver" and c in pkg.panel.columns
            and cadence_key(pkg.panel.columns[c].cadence) == ("regular", 1, "month")
            and c in ban.verdicts and ban.verdicts[c].verdict == "ban"]
    if not drop:
        return pkg
    cols = {c: f for c, f in pkg.catalog.columns.items() if c not in drop}
    return SimpleNamespace(**dict(vars(pkg), catalog=pkg.catalog.model_copy(update={"columns": cols})))


def split_catalog_text(text):
    """(header comment lines, parsed document) of a generated catalog text."""
    lines = text.split("\n")
    n = 0
    while n < len(lines) and lines[n].startswith("#"):
        n += 1
    return lines[:n], yaml.safe_load("\n".join(lines[n:]))


def join_catalog_text(header, doc):
    """The catalog text catalog_document writes, from its header lines and document."""
    body = yaml.safe_dump(doc, sort_keys=False, width=4096, allow_unicode=False, default_flow_style=False)
    return "\n".join(header) + "\n" + body


def carry_signatures(text, committed):
    """(signed text, carried names, dropped {name: why}): ``text`` (a generated catalog, unsigned) with the owner's
    signatures of the ``committed`` catalog text carried onto every entry whose facts outside SIGNATURE_FIELDS are
    equal and whose committed provenance starts with the generated one. The signature fields take the committed
    values; reviewed_by and date stand before provenance, where apply_signoff.py writes them."""
    header, doc = split_catalog_text(text)
    if not committed:
        return text, (), {}
    _, old = split_catalog_text(committed)
    columns = doc["columns"]
    carried, dropped = [], {}
    for name, entry in ((old or {}).get("columns") or {}).items():
        if not isinstance(entry, dict) or not entry.get("reviewed_by"):
            continue
        gen = columns.get(name)
        if gen is None:
            dropped[name] = "no longer generated"
            continue
        a = {k: v for k, v in gen.items() if k not in SIGNATURE_FIELDS}
        b = {k: v for k, v in entry.items() if k not in SIGNATURE_FIELDS}
        if a != b:
            dropped[name] = "facts changed: %s" % ", ".join(sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k)))
            continue
        if not str(entry.get("provenance", "")).startswith(str(gen.get("provenance", ""))):
            dropped[name] = "provenance changed"
            continue
        new = {}
        for k, v in gen.items():
            if k == "provenance":
                new["reviewed_by"], new["date"] = entry["reviewed_by"], entry.get("date")
            new[k] = v
        new["fact_status"] = entry.get("fact_status", gen.get("fact_status"))
        if "reviewed_by" not in new:
            new["reviewed_by"], new["date"] = entry["reviewed_by"], entry.get("date")
        if "provenance" in entry:
            new["provenance"] = entry["provenance"]
        new = {k: v for k, v in new.items() if v is not None}
        S.StoreColumn.model_validate(new)
        columns[name] = new
        carried.append(name)
    return join_catalog_text(header, doc), tuple(carried), dropped


def signed_catalog_document(pkg):
    """(signed text, unsigned text, built aggregates, refused, dropped signatures) of the features store catalog:
    catalog_document on the store plan (plan_package), with the committed catalog's signatures carried."""
    text, columns, refused = catalog_document(plan_package(pkg))
    path = pkg.root / CATALOG_FILE
    committed = path.read_text(encoding="utf-8") if path.is_file() else None
    signed, _, dropped = carry_signatures(text, committed)
    return signed, text, columns, refused, dropped


def check_signed_catalog(pkg):
    """check_catalog with the owner's signatures carried: the committed catalog must be what 'catalog' writes, and
    dataset.yaml must include it by its sha256. Returns (sha256 of the committed file, sha256 of the unsigned
    catalog text -- the resume key --, built aggregate names, refused names)."""
    signed, text, columns, refused, dropped = signed_catalog_document(pkg)
    path = pkg.root / CATALOG_FILE
    if not path.is_file() or path.read_text(encoding="utf-8") != signed:
        raise BuildError("%s is missing or stale%s; run 'build_store.py catalog', review it and update dataset.yaml's "
                         "sha256" % (path, " (signatures that no longer apply: %s)" % sorted(dropped) if dropped else ""))
    sha = sha256_file(path)
    inc = {i.path: i.sha256 for i in pkg.dataset.includes}
    if inc.get(CATALOG_FILE) != sha:
        raise BuildError("dataset.yaml includes %s with sha256 %s; the file has %s" % (CATALOG_FILE,
                                                                                    inc.get(CATALOG_FILE), sha))
    unsigned = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return sha, unsigned, tuple(n for n in columns if n not in H_COLUMNS), tuple(sorted(refused))


def write_signed_catalog(root, echo=print):
    """write_catalog with the committed signatures carried (and the ones that no longer apply named)."""
    pkg = load_package_files(root)
    text, _, columns, refused, dropped = signed_catalog_document(pkg)
    path = pkg.root / CATALOG_FILE
    old = path.read_text(encoding="utf-8") if path.is_file() else None
    if old != text:
        tmp = path.with_name(path.name + ".tmp_%d" % os.getpid())
        with open(str(tmp), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(str(tmp), str(path))
    sha = sha256_file(path)
    echo("%s: %d columns (%d aggregates, %d h_*), %d aggregates not built (G-LAG); sha256 %s%s"
         % (path, len(columns), len(columns) - len(H_COLUMNS), len(H_COLUMNS), len(refused), sha,
            "" if old != text else " (unchanged)"))
    for name, why in sorted(dropped.items()):
        echo("  signature NOT carried: %s (%s): the owner signs it again" % (name, why))
    return sha


def main(argv):
    if len(argv) < 2 or argv[0] not in ("catalog", "build"):
        raise SystemExit("usage: py -3.9 -u build_store.py catalog <package> | build <package> [--groups=a,b] "
                         "[--out-root=<folder>]")
    opts = dict(a[2:].split("=", 1) for a in argv[2:] if a.startswith("--") and "=" in a)
    extra = [a for a in argv[2:] if not (a.startswith("--") and "=" in a)] + \
        sorted(set(opts) - {"groups", "out-root"})
    if extra:
        raise SystemExit("unknown arguments: %s" % extra)
    if argv[0] == "catalog":
        write_signed_catalog(argv[1])
    else:
        groups = [g for g in opts.get("groups", "").split(",") if g] or None
        build(argv[1], groups=groups, out_root=opts.get("out-root"))


if __name__ == "__main__":
    main(sys.argv[1:])
