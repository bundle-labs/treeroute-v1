"""The twin-disagreement alarm in a grid run (owner ruling AE, pipeline/alarm_pass.py), on the synthetic grid package
of tests/test_pipeline.py, with the forecast ladder (leads 6 and 12).

The same toy runs through the frozen engine v1 copy (D:/treeroute/engine_v2/engine_v1_ref, its 930d961c hash checked)
and through this engine, in identical child processes (tests/alarm_toy_runner.py), so v1 and v2 outputs are compared
byte for byte:
  T1 LABEL-LOCK ORDERING: every pass (nowcast and each lead) locked its alarm record (and wrote alarm_preds) BEFORE
     its open_test_labels call (a spy on the call), and alarm_preds holds no label column;
  T2 NEVER SWITCHING (the toy's nowcast is inert, its leads declined): every engine v1 output is byte-identical except
     the files every engine change moves (times, the engine's identity); verdict.json equal without the fingerprint
     and timings; tables.json equal without its timings; the with-alarm results equal the without ones;
  T3 FORCED SWITCHING (the nowcast adopts the GLS corrector, the A8 threshold is 0 and the batch floor 1): the with-alarm
     column is the twin exactly in switched batches; test_preds still equals v1's forced run byte for byte; the
     recorded with-alarm verdict is recomputed from the saved rows; the headline-table builder reads the with_alarm
     role and refuses a tampered alarm_preds;
  T4 LEADS: an active lead routes its twin in separate calls (alarm_guard_preds) and its guard_preds and test_preds
     equal v1's; an inert (declined) lead routes nothing extra and its fitctx part equals v1's;
  T5 RESUME (in process): a run stopped after the alarm lock, before the labels open, resumes to the same alarm bytes;
     a resumed run whose alarm differs is refused.
"""

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alarm_toy_compare import V1_HASH, V1_REF, compare_runs, json_without, run_child
from conftest import make_registry, sha256_of
from test_pipeline import _run, make_pipeline_package, sklearnex_patched  # noqa: F401  (the module's autouse fixture)

LEADS = (6, 12)


@pytest.fixture(scope="module")
def toys(tmp_path_factory):
    if not (V1_REF / "treeroute").is_dir():
        pytest.fail("the frozen engine v1 copy %s is missing" % V1_REF)
    base = tmp_path_factory.mktemp("alarm_grid")
    pkg = make_pipeline_package(base / "pk")
    (base / "shipped").mkdir()
    reg = make_registry(base, [base / "shipped"])
    from conftest import ENGINE_DIR

    out = {}
    for name, engine, mode, switch in (("v1", V1_REF, "normal", False), ("v2", ENGINE_DIR, "normal", False),
                                       ("v1_forced", V1_REF, "forced", False), ("v2_forced", ENGINE_DIR, "forced", True)):
        spy = base / ("spy_%s.json" % name) if name.startswith("v2") else None
        rec = run_child(engine, pkg, base / name, reg, mode=mode, switch_all=switch, spy=spy)
        rec["spy"] = spy
        out[name] = rec
    assert out["v1"]["engine_code_sha256"] == V1_HASH and out["v1_forced"]["engine_code_sha256"] == V1_HASH
    from treeroute.runs.fingerprint import engine_code_sha256

    assert out["v2"]["engine_code_sha256"] == engine_code_sha256() != V1_HASH
    return out


def _alarm(folder, lead):
    return json.loads((Path(folder) / ("alarm_lead_%d.json" % lead)).read_text(encoding="utf-8"))


def _preds_dir(folder, lead):
    return Path(folder) if lead == 0 else Path(folder) / "ladder" / ("lead_%d" % lead)


# ------------------------------------------------------------------------------------------------ T1
@pytest.mark.parametrize("which", ("v2", "v2_forced"))
def test_t1_every_pass_locks_its_alarm_before_its_labels_open(toys, which):
    folder = toys[which]["folder"]
    events = json.loads(Path(toys[which]["spy"]).read_text(encoding="utf-8"))
    assert sorted(e["lead"] for e in events) == [0] + list(LEADS)
    for e in events:
        assert e["alarm_lock_exists"] and e["alarm_preds_exists"] and not e["marker_existed"], e
        lock = json.loads((folder / ("alarm_lead_%d.json.alarmlock.json" % e["lead"])).read_text(encoding="utf-8"))
        assert float(lock["locked_at_epoch"]) <= e["at"]
        marker = json.loads((folder / ("test_labels_opened_lead_%d.json" % e["lead"])).read_text(encoding="utf-8"))
        assert marker["alarm_sha256"] == lock["sha256"] == sha256_of(folder / ("alarm_lead_%d.json" % e["lead"]))
        preds = pd.read_parquet(_preds_dir(folder, e["lead"]) / "alarm_preds.parquet")
        assert "y" not in preds.columns
        assert _alarm(folder, e["lead"])["alarm_preds_sha256"] == sha256_of(_preds_dir(folder, e["lead"]) /
                                                                            "alarm_preds.parquet")
    report = json.loads((folder / "guard_report.json").read_text(encoding="utf-8"))
    assert report["ran"]["G-LOCK"]["alarm"]["alarm_sha256"] == sha256_of(folder / "alarm_lead_0.json")


# ------------------------------------------------------------------------------------------------ T2
def test_t2_a_run_where_the_alarm_never_switches_keeps_every_v1_output(toys):
    v1, v2 = toys["v1"]["folder"], toys["v2"]["folder"]
    differ, extra, missing = compare_runs(v1, v2)
    assert differ == [] and extra == [] and missing == [], (differ, extra, missing)
    for name in ("test_preds.parquet", "inner_preds.parquet", "decision_checks.json", "ladder/ladder.json"):
        assert sha256_of(v1 / name) == sha256_of(v2 / name)
    drop = ("run_fingerprint", "timings_seconds")
    assert json_without(v1 / "verdict.json", drop) == json_without(v2 / "verdict.json", drop)
    # tables.json holds per-run build times and the run's temp folder (they differ between any two runs)
    assert json_without(v1 / "tables.json", ("seconds", "temp_dir")) == \
        json_without(v2 / "tables.json", ("seconds", "temp_dir"))
    assert json_without(v1 / "run_record.json", ("run_fingerprint",)) == \
        json_without(v2 / "run_record.json", ("run_fingerprint",))
    for L in (0,) + LEADS:
        a = json_without(v1 / ("test_labels_opened_lead_%d.json" % L), ("opened_at",))
        b = json_without(v2 / ("test_labels_opened_lead_%d.json" % L), ("opened_at", "alarm_sha256"))
        assert a == b
        doc = _alarm(v2, L)
        assert doc["rows_switched"] == 0 and doc["batches_fired"] == 0
    assert _alarm(v2, 0)["status"] == "inert_twin_not_simpler"                 # the toy adopts an unweighted arm
    assert {_alarm(v2, L)["status"] for L in LEADS} == {"not_applicable_declined"}
    rec = json.loads((v2 / "alarm_verdict.json").read_text(encoding="utf-8"))
    assert rec["with"]["pooled_mae"] == rec["without"]["pooled_mae_adopted"] and rec["rows_switched"] == 0
    assert rec["with"]["verdict"] == rec["without"]["verdict"] and rec["post_hoc"] is False
    assert "AFTER the engine v1 headline runs" in rec["alarm_origin"]


# ------------------------------------------------------------------------------------------------ T3
def test_t3_forced_switching_changes_only_the_with_alarm_column(toys):
    from treeroute.pipeline import alarm_pass as AP
    from treeroute.report import metrics as M

    v1, v2 = toys["v1_forced"]["folder"], toys["v2_forced"]["folder"]
    doc = _alarm(v2, 0)
    assert doc["adopted_arm"].endswith("_corrector_gls") and doc["twin_arm"].endswith("_corrector_unweighted")
    assert doc["status"] == "active" and doc["twin_eligible"] is True and doc["twin_simpler"] is True
    assert doc["constants"] == {"A8.alarm_ratio_threshold": 0.0, "A8.alarm_min_batch_rows": 1}
    assert doc["batches_fired"] > 0 and doc["reference"]["surface"] == "decision surface"
    preds = M.read_rows(v2 / "test_preds.parquet")
    alarm = pd.read_parquet(v2 / "alarm_preds.parquet")
    fired = alarm["fired"].to_numpy(dtype=bool)
    twin = preds["arm__" + doc["twin_arm"]].to_numpy(dtype=np.float64)
    adopted = preds["arm__" + doc["adopted_arm"]].to_numpy(dtype=np.float64)
    with_ = alarm["with_alarm"].to_numpy(dtype=np.float64)
    assert np.array_equal(with_[fired], twin[fired]) and np.array_equal(with_[~fired], adopted[~fired])
    assert int(fired.sum()) == doc["rows_switched"] > 0
    assert sha256_of(v1 / "test_preds.parquet") == sha256_of(v2 / "test_preds.parquet")    # never touched
    # the recorded with-alarm verdict, recomputed from the saved rows
    verdict = json.loads((v2 / "verdict.json").read_text(encoding="utf-8"))
    rec = json.loads((v2 / "alarm_verdict.json").read_text(encoding="utf-8"))
    frame = AP.with_alarm_frame(preds, alarm, "arm__" + verdict["adopted"])
    derived = json.loads((v2 / "derived.json").read_text(encoding="utf-8"))
    blocks = {g: int(i) for g, i in derived["R14:overlap_blocks"]["value"]["block_of_group"].items()}
    w = AP.verdict_with(frame, verdict["reference"], "arm__" + verdict["adopted"], float(verdict["band"]), False,
                        M.REFERENCE_OWN_LINK_TREES_OFF, verdict["hit_tolerance"], verdict["measurement_error_floor"],
                        "smoke", blocks)
    assert json.loads(json.dumps(M._json_safe(w["verdict"]))) == rec["with"]["verdict"]
    assert w["pooled_mae"] == rec["with"]["pooled_mae"] != rec["without"]["pooled_mae_adopted"]


def test_t3_the_headline_table_reads_the_with_alarm_role_and_refuses_a_tampered_alarm(toys, tmp_path, monkeypatch):
    from treeroute_report import table as T

    cont = tmp_path / "continuity_groups.yaml"
    cont.write_text(T.CONTINUITY_FILE.read_text(encoding="utf-8")
                    + "\nsynth_pkg:\n  label: none\n  continuity_groups: []\n", encoding="utf-8")
    monkeypatch.setattr(T, "CONTINUITY_FILE", cont)       # report tooling may name packages; the toy is not listed
    v2 = toys["v2_forced"]["folder"]
    built = T.build([v2], watermark=True)
    head = built["frames"]["headline"]
    assert "mae_with_alarm" in head.columns and head["mae_with_alarm"].notna().all()
    verdicts = built["frames"]["verdicts"]
    assert set(verdicts["verdict_of"]) == {"adopted", "with alarm"}
    # one per adopted row: the nowcast on all rows (alarm_verdict.json) and lead 0 and each lead on the common rows
    assert (verdicts["verdict_of"] == "with alarm").sum() == (verdicts["verdict_of"] == "adopted").sum() == 2 + len(LEADS)
    md = T.render_markdown(built, {"x": "x"}, True)
    section = md.split("## With and without the twin-disagreement alarm\n\n", 1)[1]
    assert section.startswith("owner ruling AE3: the twin-disagreement alarm was designed AFTER")
    # a v1 run: NaN with-alarm columns and the disclosure
    old = T.build([toys["v1"]["folder"]], watermark=True)
    assert old["frames"]["headline"]["mae_with_alarm"].isna().all()
    assert "no alarm recorded (engine v1 run)" in set(old["frames"]["disclosures"]["text"])
    # a tampered alarm_preds (a copy of the run folder): refused
    copy = tmp_path / "runs" / "synth_pkg" / "smoke" / v2.name
    shutil.copytree(str(v2), str(copy))
    path = copy / "alarm_preds.parquet"
    frame = pd.read_parquet(path)
    frame.loc[0, "adopted"] = frame.loc[0, "adopted"] + 1.0
    path.chmod(0o666)
    frame.to_parquet(path, index=False)
    with pytest.raises(T.TableRefusal, match="adopted column"):
        T.build([copy], watermark=True)


# ------------------------------------------------------------------------------------------------ T4
def test_t4_an_active_lead_routes_its_twin_apart_and_keeps_its_v1_files(toys):
    v1, v2 = toys["v1_forced"]["folder"], toys["v2_forced"]["folder"]
    differ, extra, missing = compare_runs(v1, v2, allowed_extra={
        "fitctx_log.parquet", "per_group_schedule.json"} | {"phases/ladder_lead_%d/fitctx_log.parquet" % L
                                                            for L in LEADS})
    assert differ == [] and extra == [] and missing == [], (differ, extra, missing)
    for L in LEADS:
        d = v2 / "ladder" / ("lead_%d" % L)
        assert sha256_of(v1 / "ladder" / ("lead_%d" % L) / "guard_preds.parquet") == sha256_of(d / "guard_preds.parquet")
        assert sha256_of(v1 / "ladder" / ("lead_%d" % L) / "test_preds.parquet") == sha256_of(d / "test_preds.parquet")
        doc = _alarm(v2, L)
        assert doc["status"] == "active" and doc["twin_routed"] is True
        assert doc["alarm_guard_preds_file"] == "ladder/lead_%d/alarm_guard_preds.parquet" % L
        assert doc["reference"]["surface"] == "lead %d guard surface" % L and doc["reference"]["gap"] > 0
        g = pd.read_parquet(d / "alarm_guard_preds.parquet")
        assert ("arm__" + doc["twin_arm"]) in g.columns
        log = pd.read_parquet(v2 / "phases" / ("ladder_lead_%d" % L) / "fitctx_log.parquet")
        assert {"router_lead_guard_alarm_twin", "router_lead_test_alarm_twin"} <= set(log["purpose"])


def test_t4_an_inert_lead_routes_nothing_extra(toys):
    v1, v2 = toys["v1"]["folder"], toys["v2"]["folder"]
    for L in LEADS:
        part = Path("phases") / ("ladder_lead_%d" % L) / "fitctx_log.parquet"
        assert sha256_of(v1 / part) == sha256_of(v2 / part)
        assert not (v2 / "ladder" / ("lead_%d" % L) / "alarm_guard_preds.parquet").exists()
        assert _alarm(v2, L)["twin_routed"] is False


# ------------------------------------------------------------------------------------------------ T5
def _crash_at_open(monkeypatch):
    from treeroute.labels import vault as V

    def crash(self, adoption_sha256, lead, *, alarm_sha256):
        raise RuntimeError("simulated power cut after the alarm lock, before the labels open")
    monkeypatch.setattr(V.LabelView, "open_test_labels", crash)


def test_t5_a_run_stopped_after_its_alarm_lock_resumes_to_the_same_alarm(tmp_path, monkeypatch):
    pkg = make_pipeline_package(tmp_path / "pk")
    _crash_at_open(monkeypatch)
    with pytest.raises(RuntimeError, match="simulated power cut"):
        _run(pkg, tmp_path)
    folder = next((tmp_path / "runs" / "synth_pkg" / "smoke").iterdir())
    assert (folder / "alarm_lead_0.json.alarmlock.json").is_file()
    assert not (folder / "test_labels_opened_lead_0.json").exists() and not (folder / "test_preds.parquet").exists()
    alarm, preds = sha256_of(folder / "alarm_lead_0.json"), sha256_of(folder / "alarm_preds.parquet")
    monkeypatch.undo()
    assert Path(_run(pkg, tmp_path)) == folder
    assert sha256_of(folder / "alarm_lead_0.json") == alarm and sha256_of(folder / "alarm_preds.parquet") == preds
    assert (folder / "DONE.json").is_file()
    marker = json.loads((folder / "test_labels_opened_lead_0.json").read_text(encoding="utf-8"))
    assert marker["alarm_sha256"] == alarm


def test_t5_a_resumed_run_whose_alarm_differs_is_refused(tmp_path, monkeypatch):
    from treeroute import engine_constants as K
    from treeroute.errors import RefusedError

    pkg = make_pipeline_package(tmp_path / "pk")
    _crash_at_open(monkeypatch)
    with pytest.raises(RuntimeError, match="simulated power cut"):
        _run(pkg, tmp_path)
    monkeypatch.undo()
    monkeypatch.setattr(K, "ALARM_RATIO_THRESHOLD", 1.5)          # the resumed process would record another alarm
    with pytest.raises(RefusedError, match="different content"):
        _run(pkg, tmp_path)
    folder = next((tmp_path / "runs" / "synth_pkg" / "smoke").iterdir())
    assert not (folder / "test_labels_opened_lead_0.json").exists()
