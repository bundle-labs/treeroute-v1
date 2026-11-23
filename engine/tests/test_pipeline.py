"""The one pipeline (treeroute.pipeline) end to end on a synthetic package (plan 4.1; smoke R21).

make_pipeline_package() writes a small, fully declared package under a temp folder: 4 groups of 12
units ({group}_{ix}_{iy}; two groups touch on the grid, so they form one overlap block), 12 years of a
monthly positive target (a complete census with a few invalid labels), one driver store with a monthly
unit driver (with a declared fill code), a global monthly index (keep_unreviewed: listed in every
report), an annual driver stored on the monthly rows (lagged a year by R8 through join_coarser_column), a
static column and a static report stratum (banned as a feature, used by the per-stratum table), a static
table with grid indices, and a feature script that makes one router-context column. fraction=True makes
the target a fraction with the legal range [0, 1] (so R22 adds the arcsine link). decline=True makes
the drivers' anomaly effect flip sign from FLIP_FROM on (the inner-score and test years), so no tree arm
can beat its trees-off on the decision surface and the layer declines. Every run writes only under the
test's temp folder (the fake machine file's run root and temp dir).
"""

import hashlib
import json
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from conftest import make_registry, sha256_of

GROUPS = {"grp_a": (0, 0), "grp_b": (4, 0), "grp_c": (100, 50), "grp_d": (200, 90)}
YEARS = tuple(range(2000, 2012))
UNITS_PER_GROUP = 12
FLIP_FROM = 2005          # the first inner-score year derive_all finds for YEARS (checked in the decline test)
K_FLOOR = 10 * 9e-8       # owner ruling O4: C9.k_min_multiple_of_arith_error x C9.measured_arith_error
LEADS = (6, 12)           # R10's leads on a monthly target (owner ruling I1: 6 and 12 months; lead 0 is the contract)
SPARSE_GROUP, SPARSE_UNITS, SPARSE_FROM = "grp_c", (0, 1), 2006   # sparse=True: short-history units (R12)
LADDER_PHASES = ["ladder_contract"] + ["ladder_lead_%d" % L for L in LEADS] + ["ladder"]
# the ladder-table phase hands nothing out when the nowcast's report ran in the same process (its hit
# tolerance is kept), so its fitctx part is written empty
LADDER_LOG_PARTS = set(LADDER_PHASES) - {"ladder"}

STORE = """\
store: synth_store
description: a synthetic driver store for the pipeline tests
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
    stamp: period_end
    window: {length: 1, unit: month, align: backward}
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
  area:
    dtype: float32
    units: 'km2'
    cadence: {kind: static}
    scope: unit
    stamp: period_end
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
    legal_range: [0, %(ub)s]
    legal_range_source: synthetic product guide
    window: {length: 1, unit: month, align: backward}
    stamp: period_end
    measurement_error_floor: 0.5
  x1: {role: driver, co_measured_with_target: false, co_measured_evidence: Part 1}
  g1: {role: driver}
  x2: {role: driver}
  s1: {role: driver}
  area: {role: report_stratum}
  'ctx:m': {role: router_context}
"""

FEATURES = '''\
"""Synthetic feature script: the calendar month of the row as router context."""
import pandas as pd

OUTPUTS = {
    "ctx:m": {"dtype": "float32", "units": "1",
              "cadence": {"kind": "regular", "length": 1, "unit": "month"},
              "scope": "global", "stamp": "period_end",
              "window": {"length": 1, "unit": "month", "align": "backward"},
              "legal_range": [1.0, 12.0], "derived_from": ["step_month"], "reads_target": False,
              "fact_status": "verified"},
}


def build(frame, keys):
    month = [c for c, part in keys["time"].items() if part == "month"][0]
    return pd.DataFrame({"ctx:m": frame[month].astype("float32")}, index=frame.index)
'''

TARGET_READER = '''\
"""Synthetic target reader: the store writes -1 for an invalid label; the reader makes it NaN."""
import numpy as np
import pandas as pd
import pyarrow.parquet as pq


def read_target_file(path, key):
    frame = pq.read_table(str(path)).to_pandas()
    y = frame["y_raw"].to_numpy(dtype=np.float64)
    y[y < 0] = np.nan
    return pd.DataFrame({"unit_id": frame["unit_id"].astype(object), "group_id": key["group"],
                         "step_year": frame["step_year"].astype("int64"),
                         "step_month": frame["step_month"].astype("int64"), "y": y})
'''


def verdicts(stamp=None):
    ev = "Part 1" if stamp is None else "%s | synthetic" % stamp
    lines = ["verdicts:", "  y: {verdict: ban, reason: label, evidence: '%s'}" % ev,
             "  area: {verdict: ban, reason: structural, evidence: '%s'}" % ev,
             "  g1: {verdict: keep_unreviewed, reason: 'timing facts signed, not yet reviewed'}"]
    for c in ("x1", "x2", "s1", "ctx:m"):
        lines.append("  '%s': {verdict: keep, reason: reviewed, evidence: '%s'}" % (c, ev))
    return "\n".join(lines) + "\n"


def _units(group):
    ix0, iy0 = GROUPS[group]
    return ["%s_%d_%d" % (group, ix0 + i % 4, iy0 + i // 4) for i in range(UNITS_PER_GROUP)]


def make_pipeline_package(root, name="synth_pkg", stamp=None, with_reader=False, excluded=None, fraction=False,
                          decline=False, sparse=False):
    """Write the synthetic package (and its data) under root/<name>; returns the package folder. sparse=True
    gives SPARSE_UNITS of grp_c no valid label before SPARSE_FROM, so they are short-history units (R12) at
    the inner cut and take their group's region fallback router."""
    root = Path(root)
    stores = root / "_stores"
    stores.mkdir(parents=True, exist_ok=True)
    store_path = stores / "synth_store.yaml"
    store_path.write_text(STORE, encoding="utf-8")
    pkg = root / name
    (pkg / "features").mkdir(parents=True)
    rng = np.random.default_rng(20)      # test data only; the engine never draws
    target_rows, driver_rows, static_rows = [], [], []
    for gi, group in enumerate(sorted(GROUPS)):
        for ui, unit in enumerate(_units(group)):
            ix, iy = (int(v) for v in unit.rsplit("_", 2)[1:])
            s1 = float(gi) + 0.1 * ui
            area = 10.0 + 3.0 * ((ui * 7 + gi) % UNITS_PER_GROUP)
            static_rows.append((unit, group, 10.0 + 0.01 * ix, 20.0 + 0.01 * iy, ix, iy))
            for year in YEARS:
                x2 = 0.5 * np.sin(year + ui) + 0.2 * gi
                for month in range(1, 13):
                    g1 = np.sin(2 * np.pi * (year * 12 + month) / 40.0)
                    seasonal = np.cos(2 * np.pi * month / 12.0 + 0.3 * ui)
                    e = (0.5 if decline else 0.3) * rng.standard_normal()
                    x1 = seasonal + e
                    if decline:
                        # a strong white driver anomaly (no autocorrelated effect the history block could
                        # carry) whose effect flips sign in the inner-score and test years
                        sign = 1.0 if year < FLIP_FROM else -1.0
                        y = max(0.05, 6.0 + 2.0 * np.sin(2 * np.pi * month / 12.0) + 0.8 * seasonal
                                + sign * 2.0 * e + 0.2 * s1 + 0.2 * rng.standard_normal())
                    else:
                        y = max(0.05, 6.0 + 2.0 * np.sin(2 * np.pi * month / 12.0) + 0.8 * x1 + 0.6 * x2
                                + 0.5 * g1 + 0.2 * s1 + 0.4 * rng.standard_normal())
                    if fraction:
                        y = min(0.98, max(0.01, y / 12.0))
                    if rng.random() < 0.01:
                        y = float("nan")
                    if sparse and group == SPARSE_GROUP and ui in SPARSE_UNITS and year < SPARSE_FROM:
                        y = float("nan")
                    x1_stored = -32768.0 if rng.random() < 0.005 else x1
                    target_rows.append((group, year, unit, month, y))
                    driver_rows.append((group, year, unit, month, x1_stored, g1, x2, s1, area))
    t = pd.DataFrame(target_rows, columns=["group_id", "step_year", "unit_id", "step_month", "y"])
    d = pd.DataFrame(driver_rows, columns=["group_id", "step_year", "unit_id", "step_month", "x1", "g1", "x2", "s1",
                                           "area"])
    for (group, year), sub in t.groupby(["group_id", "step_year"]):
        out = pkg / "data" / "target" / ("group=%s" % group) / ("year=%d" % year)
        out.mkdir(parents=True)
        frame = sub[["unit_id", "step_year", "step_month", "y"]].copy()
        if with_reader:
            frame = frame.rename(columns={"y": "y_raw"})
            frame["y_raw"] = frame["y_raw"].fillna(-1.0)
        else:
            frame.insert(1, "group_id", group)
        frame.to_parquet(out / "part-0.parquet", index=False)
    for (group, year), sub in d.groupby(["group_id", "step_year"]):
        out = pkg / "data" / "drivers" / ("group=%s" % group) / ("year=%d" % year)
        out.mkdir(parents=True)
        sub[["unit_id", "step_year", "step_month", "x1", "g1", "x2", "s1", "area"]].astype(
            {"x1": "float32", "g1": "float32", "x2": "float32", "s1": "float32", "area": "float32"}).to_parquet(
            out / "part-0.parquet", index=False)
    (pkg / "data" / "static").mkdir(parents=True)
    pd.DataFrame(static_rows, columns=["unit_id", "group_id", "lat", "lon", "grid_ix", "grid_iy"]).to_parquet(
        pkg / "data" / "static" / "part-0.parquet", index=False)
    (pkg / "dataset.yaml").write_text(
        "name: %s\nversion: '0.1'\nowner: tester\ndescription: a synthetic package for the pipeline tests\n"
        "stores:\n"
        "  target: 'data/target/group={group}/year={year}/part-0.parquet'\n"
        "  static: 'data/static/part-0.parquet'\n"
        "  drivers: ['data/drivers/group={group}/year={year}/part-0.parquet']\n"
        "includes:\n  - {path: ../_stores/synth_store.yaml, sha256: %s}\n" % (name, sha256_of(store_path)),
        encoding="utf-8")
    (pkg / "catalog.yaml").write_text(CATALOG % {"ub": "1" if fraction else ".inf"}, encoding="utf-8")
    (pkg / "ban.yaml").write_text(verdicts(stamp), encoding="utf-8")
    ex = "excluded: {}\n" if not excluded else "excluded:\n" + "".join(
        "  %s: synthetic exclusion\n" % g for g in excluded)
    (pkg / "split.yaml").write_text(ex, encoding="utf-8")
    (pkg / "exceptions.yaml").write_text("", encoding="utf-8")
    (pkg / "AUDIT_CHECKLIST.md").write_text("# Audit checklist\n\n- [ ] signed by: tester\n", encoding="utf-8")
    (pkg / "features" / "build.py").write_text(FEATURES, encoding="utf-8")
    if with_reader:
        (pkg / "ingest").mkdir()
        (pkg / "ingest" / "target_reader.py").write_text(TARGET_READER, encoding="utf-8")
    return pkg


# ------------------------------------------------------------------------------------------ fixtures
FAKE_LAUNCH = {"test_only": True, "env_pins": {"OMP_NUM_THREADS": "4"},
               "backend": {"sklearn_patched": True, "onedal_threads": 4}}


@pytest.fixture(scope="module", autouse=True)
def sklearnex_patched():
    """The tree-answer store and the GLS forest run only with sklearn patched (owner ruling C).
    Importing sklearnex sets KMP_* variables in this process's environment; they are put back at the
    end, so a later test's child process (started through the launcher, which refuses them) does not
    inherit them."""
    import os

    before = dict(os.environ)
    import sklearnex

    was = sklearnex.sklearn_is_patched()
    if not was:
        sklearnex.patch_sklearn(verbose=False)
    yield
    if not was:
        sklearnex.unpatch_sklearn()
    for name in set(os.environ) - set(before):
        del os.environ[name]
    for name, value in before.items():
        if os.environ.get(name) != value:
            os.environ[name] = value


def _machine(tmp_path):
    from types import SimpleNamespace

    protected = tmp_path / "shipped_root"
    protected.mkdir(exist_ok=True)
    reg = make_registry(tmp_path, [protected])
    (tmp_path / "temp").mkdir(exist_ok=True)
    return SimpleNamespace(run_root=str(tmp_path / "runs"), temp_dir=str(tmp_path / "temp"),
                           registry_dir=str(reg))


def _run(pkg, tmp_path, kind="smoke", machine=None):
    from treeroute.pipeline.run import run_pipeline

    machine = machine or _machine(tmp_path)
    return run_pipeline(pkg, tmp_path / "runs", kind, machine=machine, echo=lambda s: None,
                        launch_record=FAKE_LAUNCH)


@pytest.fixture(scope="module")
def smoke_run(tmp_path_factory):
    base = tmp_path_factory.mktemp("pipeline_smoke")
    pkg = make_pipeline_package(base / "pk")
    folder = _run(pkg, base)
    return base, pkg, Path(folder)


def _k_set(monkeypatch, value=1e-6):
    """Stand in the owner's C9 k for a headline test (the constant is unset in the engine)."""
    from treeroute import engine_constants as K

    original = K.get
    monkeypatch.setattr(K, "GUARD_TOLERANCE_K", value)
    monkeypatch.setattr(K, "get", lambda cid: value if cid == "C9.guard_tolerance_k" else original(cid))


def _k_unset(monkeypatch):
    """Stand in the state before owner ruling N (S12 a) for a test of the C9-unset path: since 2026-10-06 the
    engine sets C9.guard_tolerance_k, so the registry entry is put back to 'unset' for this test only."""
    from treeroute import engine_constants as K

    cid = "C9.guard_tolerance_k"
    monkeypatch.setitem(K._REGISTRY, cid, K._REGISTRY[cid]._replace(value=K.UNSET, status="unset"))
    monkeypatch.setattr(K, "GUARD_TOLERANCE_K", K.UNSET)


# ------------------------------------------------------------------------------------------ the smoke
def test_the_smoke_runs_every_step_and_writes_the_run_folder(smoke_run):
    base, pkg, folder = smoke_run
    for name in ("run.json", "run_record.json", "manifest.json", "derived.json", "plan.json", "status.json",
                 "run.log", "inner_candidates.csv", "inner_preds.parquet", "adoption.json",
                 "adoption.json.lock.json", "test_labels_opened_lead_0.json", "test_preds.parquet",
                 "fitctx_log.parquet", "score_by_group.csv", "per_year.csv", "per_stratum.csv", "score_pooled.csv",
                 "per_group.csv", "jackknife.csv", "preclip.csv", "guard_report.json", "verdict.json",
                 "gls_weight_model.json", "decision_checks.json", "tables.json", "manifest_adoption.json",
                 "test_pass_router.json", "DONE.json", "ladder/ladder.json", "ladder/ladder_table.csv",
                 "ladder/contract_lead_0.json"):
        assert (folder / name).is_file(), name
    for lead in LEADS:
        for name in ("adoption_lead_%d.json" % lead, "adoption_lead_%d.json.lock.json" % lead,
                     "test_labels_opened_lead_%d.json" % lead, "ladder/lead_%d/test_preds.parquet" % lead,
                     "ladder/lead_%d/guard_preds.parquet" % lead, "ladder/lead_%d/lead.json" % lead):
            assert (folder / name).is_file(), name
    done = sorted(p.name for p in (folder / "phases").iterdir() if (p / "DONE").is_file())
    assert done == sorted(["decision", "plan", "report", "test_pass"] + LADDER_PHASES)
    # the FitContext hand-outs, part by part (each written before its phase is marked done)
    parts = sorted(p.name for p in (folder / "phases").iterdir() if (p / "fitctx_log.parquet").is_file())
    assert parts == sorted(["decision", "report", "setup_with_inner", "test_pass"] + LADDER_PHASES)
    status = json.loads((folder / "status.json").read_text(encoding="utf-8"))
    assert status["state"] == "finished"
    # every temp file was released and the heavy-job lock removed
    assert list((base / "temp").iterdir()) == []


def test_the_smoke_plan_follows_r21(smoke_run):
    from treeroute import engine_constants as K

    _, _, folder = smoke_run
    derived = json.loads((folder / "derived.json").read_text(encoding="utf-8"))
    sel = derived["R21:smoke_selection"]["value"]
    assert sel["groups"] == sorted(GROUPS)[:K.SMOKE_GROUPS]
    assert derived["R19:smoke"]["value"]["trees_per_group"] == K.SMOKE_TREES_PER_GROUP
    units = derived["R18:units"]["value"]
    for g in sorted(GROUPS):
        assert len(units["bank"][g]) == min(K.SMOKE_UNITS_PER_GROUP, UNITS_PER_GROUP)
        assert units["scored"][g] == units["bank"][g]           # every smoke unit is scored
    # the labels before Y0 are lag sources only (C4): withheld from derive's label views
    assert derived["R4"]["value"] == YEARS[0] + 1
    assert derived["R4:model_labels"]["inputs"]["withheld_rows"] == len(GROUPS) * UNITS_PER_GROUP * 12


def test_the_saved_rows_hold_every_arm_placebo_and_baseline(smoke_run):
    from treeroute.pipeline.record import check_scored_units
    from treeroute.report import metrics as M

    _, _, folder = smoke_run
    rows = M.read_rows(folder / "test_preds.parquet")
    arms = sorted(c for c in rows.columns if c.startswith("arm__"))
    assert arms == sorted(["arm__%s_%s_%s" % (link, tool, w) for link in ("identity", "log_c")
                           for tool in ("corrector", "plain") for w in ("unweighted", "gls")]
                          + ["arm__%s_trees_off_unweighted" % link for link in ("identity", "log_c")])
    assert sorted(c for c in rows.columns if c.startswith("placebo__")) == sorted(
        "placebo__%s_placebo_corrector_%s" % (link, w) for link in ("identity", "log_c") for w in ("unweighted", "gls"))
    assert sorted(c for c in rows.columns if c.startswith("base__")) == [
        "base__guess_normal", "base__last5_normal", "base__predict_zero"]
    test_steps = 4 * 12
    assert len(rows) == len(GROUPS) * UNITS_PER_GROUP * test_steps      # every row, labelled or not
    assert rows["y"].isna().any()                                      # invalid labels are saved too
    check_scored_units(folder)                                         # G-SPLIT on the outputs
    # the identity trees-off is the arithmetic normal (R16) and guess-normal, within the R36 tolerance
    # (trees-off is a fitted intercept + normal, so the identity holds to the tolerance, not bit for bit)
    tol = json.loads((folder / "decision_checks.json").read_text(encoding="utf-8"))["tolerances"]["tolerance"]
    gap = np.abs(rows["arm__identity_trees_off_unweighted"] - rows["base__guess_normal"]).max()
    assert gap <= tol["identity"]
    assert np.array_equal(rows["normal"], rows["base__guess_normal"])


def test_the_adoption_is_locked_before_the_test_labels_opened(smoke_run):
    _, _, folder = smoke_run
    lock = json.loads((folder / "adoption.json.lock.json").read_text(encoding="utf-8"))
    opened = json.loads((folder / "test_labels_opened_lead_0.json").read_text(encoding="utf-8"))
    assert opened["adoption_sha256"] == lock["sha256"] == sha256_of(folder / "adoption.json")
    doc = json.loads((folder / "adoption.json").read_text(encoding="utf-8"))
    # every R24 candidate is on the surface, the GLS arms included (the weighted per-unit solve)
    assert doc["decision"]["missing_arms"] == [] and doc["decision"]["gls_absent_reason"] is None
    verdict = json.loads((folder / "verdict.json").read_text(encoding="utf-8"))
    assert verdict["adoption_sha256"] == lock["sha256"]
    checks = json.loads((folder / "decision_checks.json").read_text(encoding="utf-8"))
    for link in ("identity", "log_c"):
        assert checks["g_plumb"][link]["trees_off_equals_normal"]["pass"]
        assert checks["g_plumb"][link]["base_point_reproduces_unswept"]["pass"]
        # G-PLUMB: the GLS arm with equal weights reproduces the unweighted arm (trace-normalised penalty)
        assert checks["g_plumb"][link]["weighted_equal_weights_equals_unweighted"]["pass"]
    # UPDATED 2026-10-06: C9 k is set (ruling N S12 a), so no stand-in; ruling O4 floors every tolerance
    tols = checks["tolerances"]
    assert tols["standin"] is False and tols["floor"] == K_FLOOR
    assert all(t >= K_FLOOR for t in tols["tolerance"].values())
    assert checks["router_kind"] == "per_unit" and checks["gls"]["routed"] is True


def test_the_overlap_block_is_one_block_and_the_masks_drop_it(smoke_run):
    from treeroute import split as SP
    from treeroute.pipeline.stages import block_masks

    _, _, folder = smoke_run
    derived = json.loads((folder / "derived.json").read_text(encoding="utf-8"))
    members = derived["R14:overlap_blocks"]["value"]["members"]
    assert ["grp_a", "grp_b"] in members and ["grp_c"] in members and ["grp_d"] in members
    blocks = SP.OverlapBlocks(block_of_group={"grp_a": 0, "grp_b": 0, "grp_c": 1, "grp_d": 2},
                              members=(("grp_a", "grp_b"), ("grp_c",), ("grp_d",)), linked_pairs=(),
                              link_rule="grid_indices")
    tree_group = tuple(g for g in sorted(GROUPS) for _ in range(3))
    masks = block_masks(tree_group, blocks)
    owners = np.asarray(tree_group, dtype=object)
    assert set(owners[masks.columns_by_group["grp_a"]]) == {"grp_c", "grp_d"}
    assert set(owners[masks.columns_by_group["grp_c"]]) == {"grp_a", "grp_b", "grp_d"}
    per_group = pd.read_csv(folder / "per_group.csv")
    assert per_group.set_index("group").loc["grp_a", "overlap_block"] == "grp_a+grp_b"


def test_the_verdict_uses_the_ruled_references(smoke_run):
    from treeroute.report.metrics import VerdictTag

    _, _, folder = smoke_run
    v = json.loads((folder / "verdict.json").read_text(encoding="utf-8"))
    assert v["verdict"]["tag"] in {t.value for t in VerdictTag}
    assert v["reference"].startswith("arm__") and v["reference"].endswith("trees_off_unweighted")
    if not v["declined"]:
        link = v["adopted"].rsplit("_", 2)[0].rsplit("_plain", 1)[0].rsplit("_corrector", 1)[0]
        assert v["reference"] == "arm__%s_trees_off_unweighted" % link   # its OWN link's trees-off (N2, Q17 a)
    assert len(v["band_pairs"]) == 12                                 # D75: 3 pairs per link x weighting
    assert v["band"] > 0 and v["n_groups"] == len(GROUPS)
    assert v["blocked_jackknife"]["n_blocks"] == 3
    rec = json.loads((folder / "run_record.json").read_text(encoding="utf-8"))
    assert rec["kind"] == "smoke" and rec["headline_eligible"] is False
    assert any("smoke" in r for r in rec["not_headline_reasons"])


def test_the_run_folder_holds_the_plan_7_1_records(smoke_run):
    from treeroute.runs.atomic import dumps_canonical

    _, _, folder = smoke_run
    man = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    units = json.loads((folder / "derived.json").read_text(encoding="utf-8"))["R18:units"]["value"]
    hashes = man["unit_list_hashes"]
    for g in sorted(GROUPS):                                           # per group (plan 7.1)
        for which in ("bank", "scored"):
            want = hashlib.sha256(dumps_canonical(list(units[which][g])).encode("ascii")).hexdigest()
            assert hashes[which][g] == want
    # the adoption hash is in the manifest's write-once addendum, equal to the lock's
    add = json.loads((folder / "manifest_adoption.json").read_text(encoding="utf-8"))
    lock = json.loads((folder / "adoption.json.lock.json").read_text(encoding="utf-8"))
    assert add["adoption_sha256"] == lock["sha256"] and add["fingerprint"] == man["fingerprint"]
    # the target, static AND driver files enter the fingerprint by size and time
    for key in ("target_files_sha256", "static_files_sha256", "driver_files_sha256"):
        assert len(man["config"][key]) == 64
    per_year = pd.read_csv(folder / "per_year.csv")
    assert set(per_year["year"].dropna().astype(int)) == set(YEARS[-4:])
    preclip = pd.read_csv(folder / "preclip.csv")
    assert set(preclip["pass"]) == {"decision_surface", "test"}
    guard = json.loads((folder / "guard_report.json").read_text(encoding="utf-8"))
    # UPDATED 2026-10-06: ruling S21 accept moved every build departure to ACCEPTED_DEPARTURES: none is listed
    assert guard["not_run"] and guard["ran"]["G-PLUMB"] and guard["departures"] == []


def test_the_declared_report_stratum_gets_its_own_table(smoke_run):
    _, _, folder = smoke_run
    table = pd.read_csv(folder / "per_stratum.csv")
    assert set(table["stratum_column"]) == {"area"}
    assert set(table["stratum"].dropna().astype(int)) <= {1, 2, 3, 4}
    rec = json.loads((folder / "verdict.json").read_text(encoding="utf-8"))["strata"]["area"]
    assert len(rec["edges"]) == 3 and rec["test_rows_without_value"] == 0 and rec["donor_rows"] > 0
    man = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert "area" not in man["feature_list"]                           # a stratum is never a feature


def test_inner_preds_recompute_every_decision_surface_mae(smoke_run):
    _, _, folder = smoke_run
    inner = pd.read_parquet(folder / "inner_preds.parquet")
    adoption = json.loads((folder / "adoption.json").read_text(encoding="utf-8"))
    y = inner["y"].to_numpy(dtype=np.float64)
    assert np.isfinite(y).all()                                        # D67: valid labels only
    assert len(adoption["surface_mae"]) == 8 * 35 + 2                  # 8 tree arms (GLS included)
    for name, mae in adoption["surface_mae"].items():
        assert np.abs(inner[name].to_numpy(dtype=np.float64) - y).mean() == pytest.approx(mae, abs=1e-12)
        assert "pre__" + name in inner.columns                         # and the value before the clip


def test_the_inner_decision_stands_at_the_guard_cut(smoke_run):
    _, _, folder = smoke_run
    cuts = json.loads((folder / "derived.json").read_text(encoding="utf-8"))["R11"]["value"]["0"]
    checks = json.loads((folder / "decision_checks.json").read_text(encoding="utf-8"))
    assert checks["inner_history"]["cut"] == cuts["guard_cut"]
    assert checks["inner_features"] == "own-history block at the guard cut"
    log = pd.read_parquet(folder / "fitctx_log.parquet")
    inner = log[log["context"].isin(["ctx_inner", "ctx_inner_history"])]
    assert len(inner) and (inner["cut"] == cuts["guard_cut"]).all()
    assert (inner["max_label_time"].dropna() <= cuts["guard_cut"]).all()
    assert {"bank_inner", "router_inner", "history_fill"} <= set(inner["purpose"])
    assert set(log["part"]) == {"setup_with_inner", "decision", "test_pass", "report"} | LADDER_LOG_PARTS


# ------------------------------------------------------------------------------------------ declined, arcsine
def test_a_declined_run_adopts_the_normal_and_pins_the_best_tree_arm(tmp_path, monkeypatch):
    """The decline package flips the drivers' effect in the inner-score and test years, so the unweighted
    tree arms cannot beat their trees-off; a GLS arm may still edge it by its row weights alone (the
    weights move the intercept and normal fit too). The N2 verdict is therefore stood in as 'not
    eligible' for every arm (layer.decide.n2_eligible, read by select_adoption and, at each forecast
    lead, by forecast_adoption), so the decline path runs end to end: the nowcast declines, and every
    lead's guard fails and adopts the decline target (D86)."""
    from treeroute.layer import decide as LD
    from treeroute.report import metrics as M

    monkeypatch.setattr(LD, "n2_eligible", lambda arm_mae, own_trees_off_mae: False)
    pkg = make_pipeline_package(tmp_path / "pk", name="synth_decline", decline=True)
    folder = Path(_run(pkg, tmp_path))
    derived = json.loads((folder / "derived.json").read_text(encoding="utf-8"))
    assert derived["R7"]["value"]["inner_score"][0] == FLIP_FROM
    adoption = json.loads((folder / "adoption.json").read_text(encoding="utf-8"))
    assert adoption["declined"] is True and adoption["adopted"] is None and adoption["penalty"] is None
    assert adoption["eligible"] == [] and adoption["best_tree_penalty"] is not None
    v = json.loads((folder / "verdict.json").read_text(encoding="utf-8"))
    assert v["declined"] is True and v["verdict"]["tag"] == "declined"
    assert v["adopted"] == "identity_trees_off_unweighted"
    assert v["reference"] == "arm__identity_trees_off_unweighted"
    assert v["pooled_mae_adopted"] == v["pooled_mae_reference"]
    # every tree arm is still saved, at the best tree arm's penalty (the shipped TEST_ARMS)
    rows = M.read_rows(folder / "test_preds.parquet")
    for link in ("identity", "log_c"):
        for tool in ("plain", "corrector"):
            for w in ("unweighted", "gls"):
                assert np.isfinite(rows["arm__%s_%s_%s" % (link, tool, w)]).all()
    pt = adoption["best_tree_penalty"]
    assert ("tree arms at level %r ratio %r (the best tree arm's penalty: the layer declined)"
            % (pt["level"], pt["ratio"])) in (folder / "run.log").read_text(encoding="utf-8")
    per_group = pd.read_csv(folder / "per_group.csv")
    assert (per_group["contrast"] == 0).all()
    # the ladder pins the best tree arm at its penalty (R29) and every lead declines (D86)
    ladder = json.loads((folder / "ladder" / "ladder.json").read_text(encoding="utf-8"))
    assert ladder["pinned"] == adoption["best_tree_arm"]["link"] + "_" + adoption["best_tree_arm"]["tool"] + "_" +         adoption["best_tree_arm"]["weighting"]
    assert ladder["penalty"] == {"level": pt["level"], "ratio": pt["ratio"]}
    for lead in LEADS:
        doc = json.loads((folder / ("adoption_lead_%d.json" % lead)).read_text(encoding="utf-8"))
        assert doc["guard_passed"] is False and doc["adopted"] is None
        assert ladder["verdicts"][str(lead)]["tag"] == "declined"
        assert ladder["verdicts"][str(lead)]["adopted"] == "arm__identity_trees_off_unweighted"
        rows_l = M.read_rows(folder / "ladder" / ("lead_%d" % lead) / "test_preds.parquet")
        assert "arm__identity_trees_off_unweighted" in rows_l.columns
        weighted = adoption["best_tree_arm"]["weighting"] == "gls"
        assert (folder / "ladder" / ("lead_%d" % lead) / "gls_weight_model.json").is_file() == weighted


def test_the_arcsine_link_runs_on_a_fraction_target(tmp_path):
    from treeroute.report import metrics as M

    pkg = make_pipeline_package(tmp_path / "pk", name="synth_fraction", fraction=True)
    folder = Path(_run(pkg, tmp_path))
    links = json.loads((folder / "derived.json").read_text(encoding="utf-8"))["R22"]["value"]
    assert "arcsine" in links
    rows = M.read_rows(folder / "test_preds.parquet")
    for tool in ("plain", "corrector", "trees_off"):
        assert "arm__arcsine_%s_unweighted" % tool in rows.columns
    for tool in ("plain", "corrector"):
        assert "arm__arcsine_%s_gls" % tool in rows.columns
    assert "placebo__arcsine_placebo_corrector_unweighted" in rows.columns
    assert "placebo__arcsine_placebo_corrector_gls" in rows.columns
    for c in [c for c in rows.columns if c.startswith(("arm__", "placebo__", "base__"))]:
        v = rows[c].to_numpy(dtype=np.float64)
        assert np.isfinite(v).all() and v.min() >= 0.0 and v.max() <= 1.0, c   # the legal clip [0, UB]
    checks = json.loads((folder / "decision_checks.json").read_text(encoding="utf-8"))
    assert checks["g_plumb"]["arcsine"]["trees_off_equals_normal"]["pass"]
    assert checks["g_plumb"]["arcsine"]["base_point_reproduces_unswept"]["pass"]
    assert "arcsine" in checks["tolerances"]["tolerance"]
    v = json.loads((folder / "verdict.json").read_text(encoding="utf-8"))
    assert len(v["band_pairs"]) == 6 * len(links)


# ------------------------------------------------------------------------------------------ resume, refusals
def test_a_finished_run_is_refused(smoke_run):
    from treeroute.errors import ResumeRefusal

    base, pkg, folder = smoke_run
    with pytest.raises(ResumeRefusal):
        _run(pkg, base)


def test_a_crashed_run_resumes_from_its_locked_adoption(tmp_path, monkeypatch):
    """The process stops right after the adoption lock, before the manifest addendum and the decision's
    DONE marker: the resumed run reads the lock back (never re-decides), marks the phase, and its fitctx
    log still holds the inner-cut hand-outs behind the adoption (written per part by the first process)."""
    from treeroute.pipeline import passes

    pkg = make_pipeline_package(tmp_path / "pk")

    def crash(self):
        raise RuntimeError("simulated power cut right after the adoption lock")
    monkeypatch.setattr(passes.RunState, "_manifest_adoption", crash)
    with pytest.raises(RuntimeError, match="simulated power cut"):
        _run(pkg, tmp_path)
    folder = next((tmp_path / "runs" / "synth_pkg" / "smoke").iterdir())
    assert (folder / "adoption.json.lock.json").is_file() and not (folder / "DONE.json").exists()
    assert not (folder / "phases" / "decision" / "DONE").exists()
    assert (folder / "decision_checks.json").is_file()                 # written before the lock
    assert (folder / "phases" / "decision" / "fitctx_log.parquet").is_file()
    status = json.loads((folder / "status.json").read_text(encoding="utf-8"))
    assert status["state"] == "failed"
    assert list((tmp_path / "temp").iterdir()) == []                   # released on the crash too
    sha = sha256_of(folder / "adoption.json")
    inner = sha256_of(folder / "inner_preds.parquet")
    monkeypatch.undo()
    again = Path(_run(pkg, tmp_path))
    assert again == folder
    assert sha256_of(folder / "adoption.json") == sha and sha256_of(folder / "inner_preds.parquet") == inner
    assert (folder / "DONE.json").is_file()
    assert "resumed from the locked adoption.json" in (folder / "run.log").read_text(encoding="utf-8")
    marker = json.loads((folder / "phases" / "decision" / "DONE").read_text(encoding="utf-8"))
    assert marker["summary"]["marked_on_resume"] is True
    add = json.loads((folder / "manifest_adoption.json").read_text(encoding="utf-8"))
    assert add["adoption_sha256"] == sha
    log = pd.read_parquet(folder / "fitctx_log.parquet")
    assert set(log["part"]) == {"setup_with_inner", "decision", "setup", "test_pass", "report"} | LADDER_LOG_PARTS
    first = log[log["part"].isin(["setup_with_inner", "decision"])]
    assert {"bank_inner", "router_inner"} <= set(first["purpose"])     # the hand-outs behind the lock
    assert "bank_inner" not in set(log[log["part"] == "setup"]["purpose"])   # the resumed process refit nothing inner


def test_a_headline_run_refuses_while_c9_is_unset(tmp_path, monkeypatch):
    from treeroute.errors import UnsetConstantError

    _k_unset(monkeypatch)              # UPDATED 2026-10-06: k is set in the engine (ruling N S12 a)
    pkg = make_pipeline_package(tmp_path / "pk")
    with pytest.raises(UnsetConstantError):
        _run(pkg, tmp_path, kind="headline")
    assert not (tmp_path / "runs").exists()                # refused before any folder or compute


def test_a_freeze_verdict_is_refused(tmp_path):
    from treeroute.pipeline.run import PipelineRefusal

    pkg = make_pipeline_package(tmp_path / "pk")
    text = (pkg / "ban.yaml").read_text(encoding="utf-8").replace(
        "'s1': {verdict: keep", "'s1': {verdict: freeze")
    (pkg / "ban.yaml").write_text(text, encoding="utf-8")
    with pytest.raises(PipelineRefusal, match="freeze"):
        _run(pkg, tmp_path)


# ------------------------------------------------------------------------------------------ DRAFT and the table
def test_a_draft_package_is_stamped_and_the_table_builder_refuses_it(tmp_path, monkeypatch):
    from treeroute.pipeline.record import TableRefusal, build_headline_table

    stamp = "DRAFT -- synthetic verdicts, not a review; smoke and development only"
    pkg = make_pipeline_package(tmp_path / "pk", name="synth_draft", stamp=stamp)
    folder = Path(_run(pkg, tmp_path))
    rec = json.loads((folder / "run_record.json").read_text(encoding="utf-8"))
    assert rec["draft"]["is_draft"] and rec["DRAFT"].startswith("DRAFT: " + stamp)
    assert rec["headline_eligible"] is False
    v = json.loads((folder / "verdict.json").read_text(encoding="utf-8"))
    assert v["DRAFT"].startswith("DRAFT: ")
    man = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert man["config"]["draft"]["is_draft"] is True
    with pytest.raises(TableRefusal) as info:
        build_headline_table([folder])
    assert info.value.rule == "G-DRAFT"
    # a headline-kind run of the draft package (k stood in) is refused too
    _k_set(monkeypatch)
    head = Path(_run(pkg, tmp_path, kind="headline"))
    assert json.loads((head / "run_record.json").read_text(encoding="utf-8"))["kind"] == "headline"
    with pytest.raises(TableRefusal) as info:
        build_headline_table([head])
    assert info.value.rule == "G-DRAFT"


def test_headline_runs_carry_no_departure_after_the_s21_ruling(tmp_path, monkeypatch, smoke_run):
    """Owner ruling S21 accept (OWNER_RULINGS_2026-10-06.md N): every build departure, the pre-Y0 label reading
    included, is ruled acceptable and is no not-headline reason; split_view (a probe's excluded groups) still is.
    A signed package's headline run enters the table."""
    from treeroute import engine_constants as K
    from treeroute.pipeline import run as R
    from treeroute.pipeline.record import TableRefusal, build_headline_table, write_headline_table

    with pytest.raises(TableRefusal) as info:
        build_headline_table([smoke_run[2]])
    assert info.value.rule == "G-LEGACY"
    assert R.DEPARTURES == ()
    accepted = [k for k, _ in R.ACCEPTED_DEPARTURES]
    assert "model_labels" in accepted and "gls_kernel" in accepted and "split_view" not in accepted
    from types import SimpleNamespace as NS
    assert R.build_departures(NS(model_labels_withheld=True, split_view_dropped=None)) == []
    assert [r.split(":")[0] for r in R.build_departures(NS(model_labels_withheld=True, split_view_dropped=["g"]))]         == ["departure split_view"]
    _k_set(monkeypatch)
    pkg2 = make_pipeline_package(tmp_path / "pk2", name="synth_ruled")
    ruled = Path(_run(pkg2, tmp_path, kind="headline"))
    rec = json.loads((ruled / "run_record.json").read_text(encoding="utf-8"))
    assert rec["headline_eligible"] is True and rec["not_headline_reasons"] == []
    derived = json.loads((ruled / "derived.json").read_text(encoding="utf-8"))
    assert derived["R19"]["value"]["trees_per_group"] == K.TREES_PER_GROUP
    table = build_headline_table([ruled])
    assert list(table["package"]) == ["synth_ruled"]
    path = write_headline_table(table, tmp_path)
    assert path == write_headline_table(table, tmp_path)               # identical content: kept once
    with pytest.raises(TableRefusal):
        build_headline_table([ruled, smoke_run[2]])                    # one smoke run refuses the table


def test_run_refuses_when_derived_json_differs_from_the_latest_plan(tmp_path, monkeypatch):
    from treeroute.pipeline.run import PipelineRefusal, plan_pipeline

    _k_set(monkeypatch)
    pkg = make_pipeline_package(tmp_path / "pk")
    machine = _machine(tmp_path)
    plan_pipeline(pkg, tmp_path / "runs", machine=machine, echo=lambda s: None, launch_record=FAKE_LAUNCH)
    (pkg / "split.yaml").write_text("excluded:\n  grp_d: synthetic exclusion\n", encoding="utf-8")
    with pytest.raises(PipelineRefusal) as info:
        _run(pkg, tmp_path, kind="headline", machine=machine)
    assert info.value.rule == "G-FINGERPRINT" and "latest plan" in str(info.value)
    assert len(list((tmp_path / "runs" / "synth_pkg" / "headline").iterdir())) == 1   # no folder opened
    assert list((tmp_path / "temp").iterdir()) == []
    # plan again: the excluded group's rows are never read, and derive_all is handed a split view that
    # names only the read groups (recorded; a departure until the owner rules the reading)
    again = Path(plan_pipeline(pkg, tmp_path / "runs", machine=machine, echo=lambda s: None,
                               launch_record=FAKE_LAUNCH))
    derived = json.loads((again / "derived.json").read_text(encoding="utf-8"))
    assert derived["R18:split_view"]["value"]["excluded_not_read"] == {"grp_d": "synthetic exclusion"}
    assert derived["R18:groups"]["value"] == ["grp_a", "grp_b", "grp_c"]
    plan = json.loads((again / "plan.json").read_text(encoding="utf-8"))
    assert any(r.startswith("departure split_view") for r in plan["not_headline_reasons"])
    # a smoke of a package with an exclusion runs end to end (its split view names its own groups)
    smoke = Path(_run(pkg, tmp_path, machine=machine))
    assert (smoke / "DONE.json").is_file()
    derived = json.loads((smoke / "derived.json").read_text(encoding="utf-8"))
    assert sorted(derived["R18:units"]["value"]["bank"]) == ["grp_a", "grp_b", "grp_c"]


def test_the_heavy_job_lock_is_taken_before_anything_is_read(tmp_path, monkeypatch):
    from treeroute.errors import PreflightRefusal
    from treeroute.pipeline import data as D
    from treeroute.pipeline.run import plan_pipeline
    from treeroute.runs.preflight import HeavyJobLock

    pkg = make_pipeline_package(tmp_path / "pk")
    machine = _machine(tmp_path)

    def never(*args, **kwargs):
        raise AssertionError("the target was listed or read before the heavy-job lock")
    monkeypatch.setattr(D, "list_target", never)
    monkeypatch.setattr(D, "read_target", never)
    held = HeavyJobLock(machine.temp_dir).acquire()
    try:
        with pytest.raises(PreflightRefusal, match="another heavy engine job"):
            plan_pipeline(pkg, tmp_path / "runs", machine=machine, echo=lambda s: None, launch_record=FAKE_LAUNCH)
        with pytest.raises(PreflightRefusal, match="another heavy engine job"):
            _run(pkg, tmp_path, machine=machine)
    finally:
        held.release()
    assert not (tmp_path / "runs").exists()


def test_a_feature_output_built_from_a_leak_banned_column_is_refused(tmp_path):
    from treeroute.package.load import load_package
    from treeroute.pipeline import data as D

    pkg_dir = make_pipeline_package(tmp_path / "pk")
    package = load_package(pkg_dir)
    facts = D.feature_outputs(D.load_hook(package.root, D.FEATURE_SCRIPT))["ctx:m"]
    from_area = {"ctx:m": facts.model_copy(update={"derived_from": ["area"]})}
    # banned as structural (not a leak reason): recorded beside the output, not refused
    assert D.check_feature_lineage(from_area, package) == {"ctx:m": ["area: ban (structural)"]}
    base = (pkg_dir / "ban.yaml").read_text(encoding="utf-8")
    for reason in ("lookahead_unfixable", "post_window_snapshot", "trend_proxy"):
        (pkg_dir / "ban.yaml").write_text(base.replace("area: {verdict: ban, reason: structural",
                                                       "area: {verdict: ban, reason: %s" % reason), encoding="utf-8")
        with pytest.raises(D.DataRefusal) as info:
            D.check_feature_lineage(from_area, load_package(pkg_dir))
        assert info.value.rule == "G-LINEAGE" and reason in str(info.value)
    from_target = {"ctx:m": facts.model_copy(update={"derived_from": ["y"]})}
    with pytest.raises(D.DataRefusal) as info:
        D.check_feature_lineage(from_target, package)
    assert info.value.rule == "G-LINEAGE"


# ------------------------------------------------------------------------------------------ data layer
def test_the_column_reader_masks_lags_and_joins(tmp_path):
    from treeroute.derive.rules import derive_r01_cadence
    from treeroute.derive.shapes import Cadence, CadenceKind, StepUnit
    from treeroute.package.load import load_package
    from treeroute.pipeline import data as D
    from treeroute.timing.shapes import Lag

    pkg_dir = make_pipeline_package(tmp_path / "pk", with_reader=True)
    package = load_package(pkg_dir)
    hook = D.load_hook(package.root, D.FEATURE_SCRIPT)
    reader_hook = D.load_hook(package.root, D.TARGET_READER)
    pkg = D.augment_package(package, D.feature_outputs(hook))
    spec = D.package_spec(pkg)
    assert spec.context == ("ctx:m",) and set(spec.tree_features) == {"x1", "g1", "x2", "s1"}
    listing = D.list_target(pkg)
    frame = D.read_target(pkg, spec, reader_hook, listing, ("grp_c",), None, lambda s: None)
    assert frame[spec.target_col].isna().any()                         # the reader's -1 became NaN
    t = D.target_table(frame, spec)
    cad = derive_r01_cadence(t.unit_ids, t.time_columns, spec.time_facts).value
    reader = D.ColumnReader(pkg, spec, frame, cad, hook, lambda s: None)
    assert np.isnan(reader.raw["x1"].to_numpy()).sum() > 0             # the declared fill was masked
    month = Cadence(kind=CadenceKind.REGULAR, length=1, unit=StepUnit.MONTH)
    year = Cadence(kind=CadenceKind.REGULAR, length=1, unit=StepUnit.YEAR)
    lags = {"x1": Lag("x1", 0, month, None), "g1": Lag("g1", 0, month, None), "x2": Lag("x2", 1, year, None),
            "ctx:m": Lag("ctx:m", 0, month, None)}
    lagged = reader.lagged(lags)
    first_unit = (frame[spec.unit_col] == frame[spec.unit_col].iloc[0]).to_numpy()
    rows_2001 = np.flatnonzero(first_unit & (frame["step_year"].to_numpy() == 2001))
    rows_2000 = np.flatnonzero(first_unit & (frame["step_year"].to_numpy() == 2000))
    assert np.allclose(lagged["x2"].to_numpy()[rows_2001], reader.raw["x2"].to_numpy()[rows_2000][0])
    assert np.isnan(lagged["x2"].to_numpy()[rows_2000]).all()          # no year before the data
    months = frame["step_month"].to_numpy()[rows_2001]
    assert np.array_equal(lagged["ctx:m"].to_numpy()[rows_2001], months.astype(float))
    present = reader.drivers_present(t.unit_ids, t.group_ids, t.time_columns, ("x1",))
    assert present.all()


def test_target_ids_share_one_str_per_id_and_driver_files_enter_the_fingerprint(tmp_path):
    import os

    from treeroute.pipeline import data as D
    from treeroute.pipeline.run import _file_list_sha

    raw = pd.Series(["".join(list(u)) for u in ["a_1", "b_2", "a_1"] * 3], dtype=object)   # distinct objects
    assert raw[0] is not raw[2]
    ids = D.shared_str_ids(raw, "unit id")
    assert list(ids[:3]) == ["a_1", "b_2", "a_1"] and ids[0] is ids[2] and ids[0] is ids[8]
    with pytest.raises(D.DataRefusal):
        D.shared_str_ids(pd.Series(["a_1", None], dtype=object), "unit id")
    f = tmp_path / "part-0.parquet"
    f.write_bytes(b"x")
    before = _file_list_sha([str(f)])
    st = os.stat(f)
    os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns + 10 ** 9))            # rewritten, same size
    assert _file_list_sha([str(f)]) != before


def test_a_time_varying_or_unheld_report_stratum_is_refused():
    from types import SimpleNamespace

    from treeroute.pipeline import data as D

    static = pd.DataFrame({"unit_id": ["u_0_0"], "group_id": ["g"], "lat": [1.0], "lon": [2.0]})
    monthly = SimpleNamespace(cadence=SimpleNamespace(kind="regular"))
    spec = SimpleNamespace(strata=("area",), unit_col="unit_id", store_facts={"area": monthly})
    with pytest.raises(D.DataRefusal) as info:
        D.stratum_values(spec, SimpleNamespace(strata_unread=()), static)
    assert info.value.rule == "R34" and "time-varying" in str(info.value)
    with pytest.raises(D.DataRefusal) as info:
        D.stratum_values(spec, SimpleNamespace(strata_unread=("area",)), static)
    assert info.value.rule == "G-CLOSED"


def test_the_package_hooks_are_private_modules(tmp_path):
    import sys

    from treeroute.pipeline import data as D

    pkg_dir = make_pipeline_package(tmp_path / "pk", with_reader=True)
    before = set(sys.modules)
    hook = D.load_hook(pkg_dir, D.TARGET_READER)
    assert callable(hook.read_target_file)
    assert set(sys.modules) - before <= {"pyarrow.parquet"}             # the hook itself is never registered
    assert D.load_hook(pkg_dir, "type3/plugin.py") is None


def test_a_feature_output_that_reads_the_target_is_refused():
    from types import SimpleNamespace

    from treeroute.pipeline import data as D

    bad = SimpleNamespace(OUTPUTS={"ctx:m": {"dtype": "float32", "units": "1", "cadence": {"kind": "static"},
                                             "scope": "unit", "stamp": "period_end", "derived_from": ["y"],
                                             "reads_target": True}},
                          build=lambda frame, keys: None)
    with pytest.raises(D.DataRefusal) as info:
        D.feature_outputs(bad)
    assert info.value.rule == "G-HIST"


# ------------------------------------------------------------------------------------------ the CLI
def test_the_cli_runs_smoke_and_report_and_refuses_headline_without_k(tmp_path, monkeypatch, fake_machine):
    from typer.testing import CliRunner

    from treeroute import cli, launch

    monkeypatch.setattr(launch, "record", lambda: dict(FAKE_LAUNCH))
    _k_unset(monkeypatch)              # UPDATED 2026-10-06: k is set in the engine (ruling N S12 a)
    pkg = make_pipeline_package(tmp_path / "pk")
    runner = CliRunner()
    runs = str(fake_machine["runs"])
    res = runner.invoke(cli.app, ["smoke", str(pkg), "--run-root", runs])
    assert res.exit_code == 0, res.output
    assert "smoke finished" in res.output
    res = runner.invoke(cli.app, ["report", str(pkg), "--run-root", runs])
    assert res.exit_code == 0, res.output
    assert "not headline-eligible" in res.output and "no finished headline run" in res.output
    # plan computes no tolerance: it writes the headline folder's derived.json and plan.json; the headline
    # run itself refuses until the owner sets C9's k
    res = runner.invoke(cli.app, ["plan", str(pkg), "--run-root", runs])
    assert res.exit_code == 0, res.output
    headline = next(Path(runs, "synth_pkg", "headline").iterdir())
    plan = json.loads((headline / "plan.json").read_text(encoding="utf-8"))
    assert any("C9.guard_tolerance_k unset" in r for r in plan["not_headline_reasons"])
    res = runner.invoke(cli.app, ["run", str(pkg), "--run-root", runs])
    assert res.exit_code == cli.EXIT_REFUSED, res.output
    assert "C9.guard_tolerance_k" in res.output
    res = runner.invoke(cli.app, ["status", str(pkg), "--run-root", runs])
    assert res.exit_code == 0 and "finished" in res.output


def test_plan_writes_derived_json_that_run_then_resumes(tmp_path, monkeypatch):
    from treeroute.pipeline.run import plan_pipeline

    _k_set(monkeypatch)
    pkg = make_pipeline_package(tmp_path / "pk")
    machine = _machine(tmp_path)
    folder = Path(plan_pipeline(pkg, tmp_path / "runs", machine=machine, echo=lambda s: None,
                                launch_record=FAKE_LAUNCH))
    assert (folder / "derived.json").is_file() and (folder / "plan.json").is_file()
    assert (folder / "phases" / "plan" / "DONE").is_file() and not (folder / "adoption.json").exists()
    plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    assert plan["router_kind"] == "per_unit" and plan["links"] == ["identity", "log_c"]
    derived = sha256_of(folder / "derived.json")
    again = Path(_run(pkg, tmp_path, kind="headline", machine=machine))
    assert again == folder and sha256_of(folder / "derived.json") == derived
    assert (folder / "DONE.json").is_file()
    check = json.loads((folder / "plan_check.json").read_text(encoding="utf-8"))
    assert check["plan_folder"] == str(folder) and check["same_fingerprint"] is True


@pytest.mark.parametrize("error, code", [("route_guard", 4), ("launch", 4), ("not_built", 3)])
def test_the_cli_maps_router_guard_launch_and_not_built_errors(tmp_path, monkeypatch, fake_machine, error, code):
    from typer.testing import CliRunner

    from treeroute import cli
    from treeroute.errors import LaunchError, NotBuiltError
    from treeroute.pipeline import run as R
    from treeroute.route.kinds import RouteGuardError

    exc = {"route_guard": RouteGuardError("G-DISJOINT: an own-block tree column reached a router fit"),
           "launch": LaunchError("the thread pins could not be verified"),
           "not_built": NotBuiltError("the region fallback router")}[error]

    def boom(*args, **kwargs):
        raise exc
    monkeypatch.setattr(R, "run_pipeline", boom)
    pkg = make_pipeline_package(tmp_path / "pk")
    res = CliRunner().invoke(cli.app, ["smoke", str(pkg), "--run-root", str(fake_machine["runs"])])
    assert res.exit_code == code, res.output
    assert res.exception is None or isinstance(res.exception, SystemExit)   # no traceback, a documented code
    assert str(exc) in res.output
