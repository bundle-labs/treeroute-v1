"""The table option end to end on the toy table package (SPEC_TABLE_MODE.md 6.3): the smoke writes every record of
3.10; the adoption is locked before any test label opens; the scored rows are the package's test marks; the ladder
runs leads 183 and 365 (H4 rows saved at 365) and the lead-0 contract holds; the verdict's reference is the donor-row
median; every saved pool passes an audit that re-reads the lead files on its own; overwriting every test label with
the legal maximum moves no prediction (the leak probe); a run stopped after its decision resumes to the same outputs;
the dispatch sends a table package to TablePipeline and a grid package to Pipeline; no grid step helper is reached;
the check command is green on the toy."""

import datetime as _dt
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from table_toy import (FAKE_LAUNCH, build_toy_table_package, patch_sklearn, run_toy, set_test_labels, toy_machine)

RUN_FILES = ("run.json", "run_record.json", "manifest.json", "manifest_adoption.json", "derived.json", "plan.json",
             "status.json", "run.log", "adoption.json", "adoption.json.lock.json", "decision_checks.json",
             "inner_preds.parquet", "test_preds.parquet", "pools_decision_surface.parquet", "pools_test_pass.parquet",
             "gls_weight_model.json", "gls_weight_models_folds.json", "tables.json", "test_pass_router.json",
             "score_by_group.csv", "per_year.csv", "per_stratum.csv", "score_pooled.csv", "per_group.csv",
             "jackknife.csv", "preclip.csv", "guard_report.json", "verdict.json", "fitctx_log.parquet", "DONE.json",
             "test_labels_opened_lead_0.json", "ladder/contract_lead_0.json", "ladder/ladder.json",
             "ladder/ladder_table.csv")
LEAD_FILES = ("lead.json", "test_preds.parquet", "guard_preds.parquet", "pools_guard.parquet", "pools_test_pass.parquet")


@pytest.fixture(scope="module", autouse=True)
def sklearnex_patched():
    undo = patch_sklearn()
    yield
    undo()


@pytest.fixture(scope="module")
def smoke_run(tmp_path_factory):
    base = tmp_path_factory.mktemp("table_smoke")
    pkg = build_toy_table_package(base / "pk")
    return base, pkg, run_toy(pkg, base)


@pytest.fixture(scope="module")
def probe_run(tmp_path_factory):
    """The leak probe's run: every test label set to the legal maximum; every grid step helper made to fail."""
    from treeroute.pipeline import passes as P
    from treeroute.pipeline import stages as ST

    base = tmp_path_factory.mktemp("table_probe")
    pkg = build_toy_table_package(base / "pk")
    set_test_labels(pkg, 100.0)
    mp = pytest.MonkeyPatch()

    def unreachable(*args, **kwargs):
        raise AssertionError("a grid step helper was reached in a table run")
    for owner, name in ((ST, "unit_positions"), (ST, "build_vault"), (ST, "fill_pool"), (ST, "history_block"),
                        (P.RunState, "fill_pool_by_group")):
        mp.setattr(owner, name, unreachable)
    try:
        folder = run_toy(pkg, base)
    finally:
        mp.undo()
    return base, pkg, folder


def _derived(folder):
    return json.loads((folder / "derived.json").read_text(encoding="utf-8"))


def test_the_smoke_writes_every_record(smoke_run):
    _, _, folder = smoke_run
    missing = [f for f in RUN_FILES if not (folder / f).is_file()]
    for L in (183, 365):
        missing += ["ladder/lead_%d/%s" % (L, f) for f in LEAD_FILES if not (folder / "ladder" / ("lead_%d" % L) / f).is_file()]
    assert not missing, missing
    assert (folder / "ladder" / "lead_365" / "issue_missing_rows.parquet").is_file()
    assert not (folder / "ladder" / "lead_183" / "issue_missing_rows.parquet").is_file()
    for ph in ("plan", "decision", "test_pass", "report", "ladder_contract", "ladder_lead_183", "ladder_lead_365",
               "ladder"):
        assert (folder / "phases" / ph / "DONE").is_file(), ph


def test_the_adoption_is_locked_before_the_test_labels_open(smoke_run):
    _, _, folder = smoke_run
    lock = json.loads((folder / "adoption.json.lock.json").read_text(encoding="utf-8"))
    opened = json.loads((folder / "test_labels_opened_lead_0.json").read_text(encoding="utf-8"))
    assert opened["adoption_sha256"] == lock["sha256"]
    assert (folder / "adoption.json.lock.json").stat().st_mtime_ns <= (folder / "test_labels_opened_lead_0.json").stat().st_mtime_ns
    for L in (183, 365):
        lk = folder / ("adoption_lead_%d.json.lock.json" % L)
        op = folder / ("test_labels_opened_lead_%d.json" % L)
        assert lk.stat().st_mtime_ns <= op.stat().st_mtime_ns


def test_the_scored_rows_are_the_test_marks_and_the_verdict_uses_the_donor_median(smoke_run):
    from treeroute.pipeline import record as REC

    _, pkg, folder = smoke_run
    assert REC.check_scored_units(folder) == ()
    preds = pd.read_parquet(folder / "test_preds.parquet")
    derived = _derived(folder)
    scored = sorted(u for v in derived["R18:units"]["value"]["scored"].values() for u in v)
    assert sorted(preds["unit"].tolist()) == scored
    assert {"site", "source", "base__donor_median", "base__predict_zero"} <= set(preds.columns)
    assert preds["normal"].isna().all()
    v = json.loads((folder / "verdict.json").read_text(encoding="utf-8"))
    assert v["reference"] == "base__donor_median" and v["reference_rule"] == "donor_row_median"
    assert v["verdict"]["reference"] == "donor_row_median"
    assert v["router_kind"] == "neighbour" and v["input"] == "table"
    lad = json.loads((folder / "ladder" / "ladder.json").read_text(encoding="utf-8"))
    assert sorted(lad["verdicts"]) == ["0", "183", "365"] and lad["reference"] == "base__donor_median"
    assert lad["issue_rows_left_out"]["by_lead"]["365"]["rows_left_out"] > 0
    contract = json.loads((folder / "ladder" / "contract_lead_0.json").read_text(encoding="utf-8"))
    assert contract["pool_identical"] and contract["columns_identical"]


def test_plan_and_run_records_carry_the_table_limits_and_u2(smoke_run):
    from treeroute.package.table import U2_VOUCHED
    from treeroute.pipeline.table_run import TABLE_LIMITS, table_accepted_departures, table_departures

    _, _, folder = smoke_run
    plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    assert plan["limits"] == list(TABLE_LIMITS) and plan["u2_vouched"] == list(U2_VOUCHED)
    assert plan["input"] == "table" and plan["leads"] == [183, 365] and plan["router_kind"] == "neighbour"
    assert plan["max_feature_end_minus_issue_day"] == {"0": -1, "183": -1, "365": -1}
    rec = json.loads((folder / "run_record.json").read_text(encoding="utf-8"))
    assert rec["limits"] == list(TABLE_LIMITS) and rec["departures"] == table_departures()
    # owner ruling V4: every table departure is accepted (recorded, disclosed), none is a not-headline reason
    assert table_departures() == [] and rec["accepted_departures"] == table_accepted_departures()
    assert len(table_accepted_departures()) == 5
    assert not any(d in rec["not_headline_reasons"] for d in table_accepted_departures())


def _lead_rows(pkg, lead):
    import pyarrow.parquet as pq

    t = pq.read_table(str(Path(pkg) / "data" / ("lead_%d.parquet" % lead))).to_pandas()
    day = lambda s: np.asarray([d.toordinal() for d in s], dtype=np.int64)  # noqa: E731
    return {r: (m, td, iss) for r, m, td, iss in zip(t["row_id"], t["mark"], day(t["visit_date"]), day(t["issue_date"]))}


def _audit(pool_file, lead_rows, nowcast_rows, cut):
    frame = pd.read_parquet(pool_file)
    assert len(frame)
    n_pooled = 0
    for rid, pool, fallback in zip(frame["row_id"], frame["pool_row_ids"], frame["pool_fallback"]):
        issue = lead_rows[rid][2]
        ids = json.loads(pool)
        assert bool(fallback) == (len(ids) == 0)
        n_pooled += bool(ids)
        for p in ids:
            mark, td, _ = nowcast_rows[p]
            assert mark == "train", (pool_file, rid, p)
            assert td <= cut, (pool_file, rid, p)
            assert td < issue, (pool_file, rid, p)
            assert p in lead_rows and p != rid
    assert n_pooled


def test_every_saved_pool_passes_the_audit(smoke_run):
    """Re-read the lead files on their own: every pool row is train-marked, dated at or before the pass's bank cut and
    strictly before the scored row's key_issue from the file."""
    _, pkg, folder = smoke_run
    cuts = _derived(folder)["R11"]["value"]
    zero = _lead_rows(pkg, 0)
    _audit(folder / "pools_decision_surface.parquet", zero, zero, int(cuts["0"]["guard_cut"]))
    _audit(folder / "pools_test_pass.parquet", zero, zero, int(cuts["0"]["fit_cut"]))
    for L in (183, 365):
        rows = _lead_rows(pkg, L)
        d = folder / "ladder" / ("lead_%d" % L)
        _audit(d / "pools_guard.parquet", rows, zero, int(cuts[str(L)]["guard_cut"]))
        _audit(d / "pools_test_pass.parquet", rows, zero, int(cuts[str(L)]["fit_cut"]))


def _prediction_columns(frame):
    keep = [c for c in frame.columns if c.startswith(("arm__", "placebo__", "pre__"))]
    keep += [c for c in ("base__donor_median", "base__predict_zero") if c in frame.columns]
    return frame[["unit", "time"] + keep].reset_index(drop=True)


def test_overwriting_every_test_label_moves_no_prediction(smoke_run, probe_run):
    """The leak probe (SPEC_TABLE_MODE.md 6.3): derived.json (less the file hashes), every pool, the neighbour records,
    inner_preds, adoption.json, every guard_preds and every prediction column at every lead are byte-identical."""
    _, _, a = smoke_run
    _, _, b = probe_run
    da, db = _derived(a), _derived(b)
    for d in (da, db):
        d.pop("U1:table")
    assert da == db
    same_bytes = ["adoption.json", "pools_decision_surface.parquet", "pools_test_pass.parquet"]
    for L in (183, 365):
        same_bytes += ["ladder/lead_%d/guard_preds.parquet" % L, "ladder/lead_%d/pools_guard.parquet" % L,
                       "ladder/lead_%d/pools_test_pass.parquet" % L, "adoption_lead_%d.json" % L]
    for f in same_bytes:
        assert pd.read_parquet(a / f).equals(pd.read_parquet(b / f)) if f.endswith(".parquet") else \
            (a / f).read_bytes() == (b / f).read_bytes(), f
    assert pd.read_parquet(a / "inner_preds.parquet").equals(pd.read_parquet(b / "inner_preds.parquet"))
    ca = json.loads((a / "decision_checks.json").read_text(encoding="utf-8"))
    cb = json.loads((b / "decision_checks.json").read_text(encoding="utf-8"))
    assert ca["neighbour"] == cb["neighbour"] and ca["g_plumb"] == cb["g_plumb"]
    for f in ["test_preds.parquet"] + ["ladder/lead_%d/test_preds.parquet" % L for L in (183, 365)]:
        pa, pb = pd.read_parquet(a / f), pd.read_parquet(b / f)
        assert _prediction_columns(pa).equals(_prediction_columns(pb)), f
        test_y = pb["y"].to_numpy(dtype=np.float64)
        assert np.all(test_y[np.isfinite(test_y)] == 100.0)


def test_a_run_stopped_after_its_decision_resumes_to_the_same_outputs(smoke_run, tmp_path, monkeypatch):
    from treeroute.pipeline.table_passes import TableRunState

    _, _, ref = smoke_run
    pkg = build_toy_table_package(tmp_path / "pk")
    machine = toy_machine(tmp_path)
    real = TableRunState.test_pass

    def stop(self):
        raise RuntimeError("planted stop after the decision")
    monkeypatch.setattr(TableRunState, "test_pass", stop)
    with pytest.raises(RuntimeError, match="planted stop"):
        run_toy(pkg, tmp_path, machine=machine)
    monkeypatch.setattr(TableRunState, "test_pass", real)
    folder = run_toy(pkg, tmp_path, machine=machine)
    assert (folder / "DONE.json").is_file()
    assert (folder / "adoption.json").read_bytes() == (ref / "adoption.json").read_bytes()
    for f in ["test_preds.parquet", "inner_preds.parquet", "pools_test_pass.parquet"] + \
            ["ladder/lead_%d/test_preds.parquet" % L for L in (183, 365)]:
        assert pd.read_parquet(folder / f).equals(pd.read_parquet(ref / f)), f
    va = json.loads((folder / "verdict.json").read_text(encoding="utf-8"))
    vb = json.loads((ref / "verdict.json").read_text(encoding="utf-8"))
    for k in ("adopted", "verdict", "band", "pooled_mae_adopted", "pooled_mae_reference"):
        assert va[k] == vb[k], k


def test_the_dispatch_and_the_grid_helpers(tmp_path, monkeypatch):
    from treeroute.errors import PackageError, RefusedError
    from treeroute.pipeline import run as R
    from treeroute.pipeline.table_passes import TableRunState
    from treeroute.pipeline.table_run import TablePipeline

    seen = []
    monkeypatch.setattr(TablePipeline, "run", lambda self: seen.append("table"))
    monkeypatch.setattr(R.Pipeline, "run", lambda self: seen.append("grid"))
    table_pkg = build_toy_table_package(tmp_path / "t")
    R.run_pipeline(table_pkg, tmp_path / "runs", "smoke", machine=toy_machine(tmp_path), echo=lambda s: None,
                   launch_record=FAKE_LAUNCH)
    grid_pkg = tmp_path / "g"
    shutil.copytree(table_pkg, grid_pkg)
    (grid_pkg / "dataset.yaml").write_text("name: [not, a, name]\n", encoding="utf-8")      # malformed: grid path
    R.run_pipeline(grid_pkg, tmp_path / "runs", "smoke", machine=toy_machine(tmp_path), echo=lambda s: None,
                   launch_record=FAKE_LAUNCH)
    assert seen == ["table", "grid"]
    with pytest.raises(RefusedError, match="grid step helper"):
        TableRunState._build_tables(None)
    with pytest.raises(RefusedError, match="grid step helper"):
        TableRunState._pass_tables(None)


def test_check_quick_and_deep_are_green_on_the_toy(tmp_path):
    from treeroute.check.deep import run_deep
    from treeroute.check.quick import run_quick
    from treeroute.check.report import is_green, package_smoke_groups
    from treeroute.package.load import load_package

    pkg = build_toy_table_package(tmp_path)
    ctx = run_quick(pkg, echo=lambda s: None)
    assert ctx.input == "table" and is_green(ctx.results), ctx.results
    deep = run_deep(pkg, echo=lambda s: None)
    assert is_green(deep.results), deep.results
    assert deep.deep_selection["groups"] == ["g_a", "g_b", "g_c", "g_d"]
    assert package_smoke_groups(load_package(pkg))["groups"] == ["g_a", "g_b", "g_c", "g_d"]


def test_a_guard_row_absent_at_its_lead_refuses(tmp_path):
    from treeroute.errors import RefusedError

    pkg = build_toy_table_package(tmp_path / "pk", "guard_row_absent_at_lead")
    with pytest.raises(RefusedError, match="H4"):
        run_toy(pkg, tmp_path)


def test_plan_writes_the_table_plan(tmp_path):
    from treeroute.pipeline.run import plan_pipeline

    pkg = build_toy_table_package(tmp_path / "pk")
    folder = Path(plan_pipeline(pkg, tmp_path / "runs", machine=toy_machine(tmp_path), echo=lambda s: None,
                                launch_record=FAKE_LAUNCH))
    plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    assert plan["input"] == "table" and plan["kind"] == "headline"
    from treeroute.pipeline.table_run import table_departures

    # owner ruling V4: no table departure is a not-headline reason
    from treeroute.pipeline.table_run import table_accepted_departures
    assert not any(d in plan["not_headline_reasons"] for d in table_accepted_departures())
    assert (folder / "derived.json").is_file() and (folder / "phases" / "plan" / "DONE").is_file()


def test_the_report_table_builds_the_smoke_watermarked_table(smoke_run, tmp_path, monkeypatch):
    from treeroute_report import table as RT

    _, _, folder = smoke_run
    cont = tmp_path / "continuity_groups.yaml"
    cont.write_text(RT.CONTINUITY_FILE.read_text(encoding="utf-8")
                    + "\ntoy_table:\n  label: none\n  continuity_groups: []\n", encoding="utf-8")
    monkeypatch.setattr(RT, "CONTINUITY_FILE", cont)       # report tooling may name packages; the toy is not listed
    built = RT.build([folder], watermark=True)
    md = RT.render_markdown(built, {}, True)
    assert "SMOKE - NOT HEADLINE" in md and "per value" in md


def test_the_report_tooling_additions_name_nothing():
    """6.2: treeroute_report/*.py already fails the G-NONAMES scan today (freeze.py and table.py name years and a
    package; reported), so only the table option's additions there are scanned."""
    import inspect
    import textwrap

    from conftest import ENGINE_DIR
    from nonames_scan import registered_names, scan_python_source
    from treeroute_report import table as RT

    names = registered_names(ENGINE_DIR / "datasets")
    for fn in (RT.Run._read_strata, RT._verdict_of, RT._stratum_md_rows):
        problems = scan_python_source(textwrap.dedent(inspect.getsource(fn)), names, fn.__name__)
        assert not problems, problems
