"""A small, fully declared, CLEAN package with data (every check guard passes or only flags), and the planted
faults: each one breaks exactly one rule, and the named guard must refuse it (or flag it, for a guard whose
signed contract is report only). The table is PLANTED_FAULTS.md; tests/test_check_planted.py runs it.

The clean package: 3 groups x 4 units, monthly 2001-2010, a positive target with a few invalid labels (NaN), one
driver store keyed (unit, year, month) with a monthly driver holding its declared fill code, a global monthly
index with a signed centred window, an annual driver stored on the monthly rows, a static driver, a monthly
fraction, and a feature script that makes one router-context column (the calendar month) and one engineered
lag (x1 one month earlier, through the dense-grid predecessor lookup).
"""

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

GROUPS = ("grp_a", "grp_b", "grp_c")
UNITS_PER_GROUP = 4
YEARS = tuple(range(2001, 2011))
FILL = -32768.0

STORE = """\
store: planted_store
description: the planted-fault test store
columns:
  x1:
    dtype: float32
    units: '1'
    cadence: {kind: regular, length: 1, unit: month}
    scope: unit
    stamp: period_end
    window: {length: 1, unit: month, align: backward}
    legal_range: [-100.0, 100.0]
    fill_values: [-32768]
    fact_status: verified
  g1:
    dtype: float32
    units: '1'
    cadence: {kind: regular, length: 1, unit: month}
    scope: global
    stamp: period_centre
    window: {length: 3, unit: month, align: centred}
    fact_status: verified
  x2:
    dtype: float32
    units: '1'
    cadence: {kind: regular, length: 1, unit: year}
    scope: unit
    stamp: period_end
    window: {length: 1, unit: year, align: backward}
    fact_status: verified
  s1:
    dtype: float32
    units: '1'
    cadence: {kind: static}
    scope: unit
    stamp: period_end
    fact_status: verified
    content_epoch: timeless   # ruling N2: a physical static map
  frac:
    dtype: float32
    units: '1'
    cadence: {kind: regular, length: 1, unit: month}
    scope: unit
    stamp: period_end
    window: {length: 1, unit: month, align: backward}
    legal_range: [0.0, 1.0]
    fact_status: verified
"""

CATALOG = """\
columns:
  unit_id: {role: key_unit}
  group_id: {role: key_group}
  step_year: {role: key_time, calendar_part: year}
  step_month: {role: key_time, calendar_part: month}
  y:
    role: target
    legal_range: [0, .inf]
    legal_range_source: synthetic product guide, valid range table
    window: {length: 1, unit: month, align: backward}
    stamp: period_end
  x1: {role: driver, co_measured_with_target: false, co_measured_evidence: Part 1}
  g1: {role: driver, co_measured_with_target: false, co_measured_evidence: Part 1}
  x2: {role: driver, co_measured_with_target: false, co_measured_evidence: Part 1}
  s1: {role: driver}
  frac: {role: driver, co_measured_with_target: false, co_measured_evidence: Part 1}
  'ctx:m': {role: router_context, co_measured_with_target: false, co_measured_evidence: Part 1}
  x1_lag1: {role: engineered, co_measured_with_target: false, co_measured_evidence: Part 1}
"""

BAN = """\
verdicts:
  y: {verdict: ban, reason: label, evidence: Part 1}
  x1: {verdict: keep, reason: reviewed, evidence: Part 1}
  g1: {verdict: keep, reason: reviewed, evidence: Part 1}
  x2: {verdict: keep, reason: reviewed, evidence: Part 1}
  s1: {verdict: keep, reason: reviewed, evidence: Part 1}
  frac: {verdict: keep, reason: reviewed, evidence: Part 1}
  'ctx:m': {verdict: keep, reason: reviewed, evidence: Part 1}
  x1_lag1: {verdict: keep, reason: reviewed, evidence: Part 1}
"""

FEATURES = '''\
"""Planted-fault feature script: the calendar month as router context and x1 one month earlier."""
import numpy as np
import pandas as pd

from treeroute.io.steps import predecessor_index

LAG_K = 1

OUTPUTS = {
    "ctx:m": {"dtype": "float32", "units": "1", "cadence": {"kind": "regular", "length": 1, "unit": "month"},
              "scope": "global", "stamp": "period_end", "window": {"length": 1, "unit": "month", "align": "backward"},
              "legal_range": [1.0, 12.0], "derived_from": ["step_month"], "reads_target": False,
              "fact_status": "verified"},
    "x1_lag1": {"dtype": "float64", "units": "1", "cadence": {"kind": "regular", "length": 1, "unit": "month"},
                "scope": "unit", "stamp": "period_end", "window": {"length": 2, "unit": "month", "align": "backward"},
                "legal_range": [-100.0, 100.0], "derived_from": ["x1"], "operation": "lag k=1 unit=month",
                "reads_target": False, "fact_status": "verified"},
}


def build(frame, keys):
    month = [c for c, part in keys["time"].items() if part == "month"][0]
    codes = pd.factorize(frame[keys["unit"]].to_numpy())[0]
    steps = frame[keys["step"]].to_numpy().astype(np.int64)
    src = predecessor_index(codes, steps, LAG_K)
    x1 = frame["x1"].to_numpy(dtype=np.float64)
    lag = np.full(len(frame), np.nan)
    ok = src >= 0
    lag[ok] = x1[src[ok]]
    return pd.DataFrame({"ctx:m": frame[month].astype("float32"), "x1_lag1": lag}, index=frame.index)
'''


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def units_of(group):
    return ["%s_%d" % (group, i) for i in range(UNITS_PER_GROUP)]


def frames():
    """(target, drivers) as whole frames; the clean data."""
    rng = np.random.default_rng(7)          # test data only; the engine never draws
    t_rows, d_rows = [], []
    for gi, group in enumerate(GROUPS):
        for ui, unit in enumerate(units_of(group)):
            s1 = 0.5 * gi + 0.1 * ui
            for year in YEARS:
                x2 = 0.3 * np.sin(year + ui) + 0.1 * gi
                for month in range(1, 13):
                    g1 = float(np.sin(2 * np.pi * (year * 12 + month) / 37.0))
                    x1 = float(np.cos(2 * np.pi * month / 12.0 + 0.4 * ui) + 0.3 * rng.standard_normal())
                    frac = float(min(0.99, max(0.01, 0.5 + 0.2 * np.sin(month + ui) + 0.05 * rng.standard_normal())))
                    y = max(0.05, 5.0 + 1.5 * np.sin(2 * np.pi * month / 12.0) + 0.7 * x1 + 0.5 * x2 + 0.4 * g1
                            + 0.3 * s1 + 0.3 * rng.standard_normal())
                    if rng.random() < 0.01:
                        y = float("nan")
                    stored_x1 = FILL if rng.random() < 0.01 else x1
                    t_rows.append((group, year, unit, month, y))
                    d_rows.append((group, year, unit, month, stored_x1, g1, x2, s1, frac))
    t = pd.DataFrame(t_rows, columns=["group_id", "step_year", "unit_id", "step_month", "y"])
    d = pd.DataFrame(d_rows, columns=["group_id", "step_year", "unit_id", "step_month", "x1", "g1", "x2", "s1", "frac"])
    return t, d


def write_target(pkg, t):
    base = Path(pkg) / "data" / "target"
    for (group, year), sub in t.groupby(["group_id", "step_year"]):
        out = base / ("group=%s" % group) / ("year=%d" % year)
        out.mkdir(parents=True, exist_ok=True)
        sub[["unit_id", "group_id", "step_year", "step_month", "y"]].to_parquet(out / "part-0.parquet", index=False)


def write_drivers(pkg, d, columns=None):
    base = Path(pkg) / "data" / "drivers"
    cols = columns or ["unit_id", "step_year", "step_month", "x1", "g1", "x2", "s1", "frac"]
    for (group, year), sub in d.groupby(["group_id", "step_year"]):
        out = base / ("group=%s" % group) / ("year=%d" % year)
        out.mkdir(parents=True, exist_ok=True)
        frame = sub[cols].copy()
        for c in cols:
            if c not in ("unit_id", "step_year", "step_month"):
                frame[c] = frame[c].astype("float32")
        frame.to_parquet(out / "part-0.parquet", index=False)


def repin(pkg):
    """Point dataset.yaml at the current store catalog's sha256 (after a catalog edit)."""
    pkg = Path(pkg)
    store = pkg.parent / "_stores" / "planted_store.yaml"
    text = (pkg / "dataset.yaml").read_text(encoding="utf-8")
    head, _, _ = text.partition("includes:")
    (pkg / "dataset.yaml").write_text(head + "includes:\n  - {path: ../_stores/planted_store.yaml, sha256: %s}\n"
                                      % sha256_of(store), encoding="utf-8")


def make_clean_package(root, name="planted_pkg"):
    """Write the clean package under root/<name> (store catalog under root/_stores); returns the package folder."""
    root = Path(root)
    (root / "_stores").mkdir(parents=True, exist_ok=True)
    (root / "_stores" / "planted_store.yaml").write_text(STORE, encoding="utf-8")
    pkg = root / name
    (pkg / "features").mkdir(parents=True)
    t, d = frames()
    write_target(pkg, t)
    write_drivers(pkg, d)
    (pkg / "data" / "static").mkdir(parents=True)
    static = pd.DataFrame([(u, g, 10.0 + i, 20.0 + gi, i, gi) for gi, g in enumerate(GROUPS)
                           for i, u in enumerate(units_of(g))],
                          columns=["unit_id", "group_id", "lat", "lon", "grid_ix", "grid_iy"])
    static.to_parquet(pkg / "data" / "static" / "part-0.parquet", index=False)
    (pkg / "dataset.yaml").write_text(
        "name: %s\nversion: '0.1'\nowner: tester\ndescription: a planted-fault test package\n"
        "stores:\n"
        "  target: 'data/target/group={group}/year={year}/part-0.parquet'\n"
        "  static: 'data/static/part-0.parquet'\n"
        "  drivers: ['data/drivers/group={group}/year={year}/part-0.parquet']\n"
        "includes:\n  - {path: ../_stores/planted_store.yaml, sha256: x}\n" % name, encoding="utf-8")
    repin(pkg)
    (pkg / "catalog.yaml").write_text(CATALOG, encoding="utf-8")
    (pkg / "ban.yaml").write_text(BAN, encoding="utf-8")
    (pkg / "split.yaml").write_text("excluded: {}\n", encoding="utf-8")
    (pkg / "exceptions.yaml").write_text("", encoding="utf-8")
    (pkg / "AUDIT_CHECKLIST.md").write_text("# Audit checklist\n\n- [ ] signed by: tester\n", encoding="utf-8")
    (pkg / "features" / "build.py").write_text(FEATURES, encoding="utf-8")
    return pkg


# ------------------------------------------------------------------------------------------- edits
def edit(pkg, rel, old, new, count=1):
    path = Path(pkg) / rel
    text = path.read_text(encoding="utf-8")
    assert old in text, (rel, old)
    path.write_text(text.replace(old, new, count), encoding="utf-8")


def edit_store(pkg, old, new):
    path = Path(pkg).parent / "_stores" / "planted_store.yaml"
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    repin(pkg)


def add_store_column(pkg, block):
    """Append a column block (already indented as a store catalog column: name at 2 spaces) to the store."""
    path = Path(pkg).parent / "_stores" / "planted_store.yaml"
    path.write_text(path.read_text(encoding="utf-8") + block, encoding="utf-8")
    repin(pkg)


def rewrite_drivers(pkg, mutate, columns=None):
    _, d = frames()
    d = mutate(d)
    write_drivers(pkg, d, columns)            # every (group, year) file is rewritten in place


def rewrite_target(pkg, mutate):
    t, _ = frames()
    t = mutate(t)
    write_target(pkg, t)                      # every (group, year) file is rewritten in place


def target_by_key():
    t, _ = frames()
    return t.set_index(["unit_id", "step_year", "step_month"])["y"]
