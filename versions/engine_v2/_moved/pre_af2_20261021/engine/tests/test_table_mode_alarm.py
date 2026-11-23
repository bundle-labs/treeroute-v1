"""The twin-disagreement alarm in a table run (owner ruling AE; the neighbour kind, day-dated rows, leads 183 and 365),
on the toy table package of tests/table_toy.py, run through the frozen engine v1 copy and this engine in identical
child processes (tests/alarm_toy_runner.py):
  T1 every pass locks its alarm record before its test labels open; alarm_preds holds no label;
  T2 the toy's nowcast declines (the donor-row median, ruling V1): the alarm is not applicable at every pass and every
     engine v1 output (pools_*.parquet included) is byte-identical except the files every engine change moves;
  T3 forced (the nowcast adopts the GLS corrector; threshold 0, batch floor 1): the with-alarm column is the twin
     exactly in switched batches (the calendar month of each row's target day), test_preds equals v1's forced run;
  T4 the leads: the twin is routed alone on each lead's guard surface (alarm_guard_preds) when the lead can be active,
     the lead's guard_preds and test_preds still equal v1's.
"""

import json

import numpy as np
import pandas as pd
import pytest

from alarm_toy_compare import V1_HASH, V1_REF, compare_runs, json_without, run_child
from conftest import ENGINE_DIR, make_registry, sha256_of
from table_toy import build_toy_table_package

LEADS = (183, 365)


@pytest.fixture(scope="module")
def toys(tmp_path_factory):
    if not (V1_REF / "treeroute").is_dir():
        pytest.fail("the frozen engine v1 copy %s is missing" % V1_REF)
    base = tmp_path_factory.mktemp("alarm_table")
    pkg = build_toy_table_package(base / "pk")
    (base / "shipped").mkdir()
    reg = make_registry(base, [base / "shipped"])
    out = {}
    for name, engine, mode, switch in (("v1", V1_REF, "normal", False), ("v2", ENGINE_DIR, "normal", False),
                                       ("v1_forced", V1_REF, "forced", False), ("v2_forced", ENGINE_DIR, "forced", True)):
        spy = base / ("spy_%s.json" % name) if name.startswith("v2") else None
        rec = run_child(engine, pkg, base / name, reg, mode=mode, switch_all=switch, spy=spy)
        rec["spy"] = spy
        out[name] = rec
    assert out["v1"]["engine_code_sha256"] == V1_HASH != out["v2"]["engine_code_sha256"]
    return out


def _alarm(folder, lead):
    return json.loads((folder / ("alarm_lead_%d.json" % lead)).read_text(encoding="utf-8"))


@pytest.mark.parametrize("which", ("v2", "v2_forced"))
def test_t1_every_table_pass_locks_its_alarm_before_its_labels_open(toys, which):
    folder = toys[which]["folder"]
    events = json.loads(toys[which]["spy"].read_text(encoding="utf-8"))
    assert sorted(e["lead"] for e in events) == [0] + list(LEADS)
    for e in events:
        assert e["alarm_lock_exists"] and e["alarm_preds_exists"] and not e["marker_existed"], e
        marker = json.loads((folder / ("test_labels_opened_lead_%d.json" % e["lead"])).read_text(encoding="utf-8"))
        assert marker["alarm_sha256"] == sha256_of(folder / ("alarm_lead_%d.json" % e["lead"]))
        d = folder if e["lead"] == 0 else folder / "ladder" / ("lead_%d" % e["lead"])
        assert "y" not in pd.read_parquet(d / "alarm_preds.parquet").columns


def test_t2_a_declined_table_run_keeps_every_v1_output(toys):
    v1, v2 = toys["v1"]["folder"], toys["v2"]["folder"]
    differ, extra, missing = compare_runs(v1, v2)
    assert differ == [] and extra == [] and missing == [], (differ, extra, missing)
    assert sorted(p.name for p in v1.glob("pools_*.parquet")) and all(
        sha256_of(p) == sha256_of(v2 / p.name) for p in v1.glob("pools_*.parquet"))
    drop = ("run_fingerprint", "timings_seconds")
    assert json_without(v1 / "verdict.json", drop) == json_without(v2 / "verdict.json", drop)
    assert json_without(v1 / "tables.json", ("seconds", "temp_dir")) == \
        json_without(v2 / "tables.json", ("seconds", "temp_dir"))
    for L in (0,) + LEADS:
        doc = _alarm(v2, L)
        assert doc["status"] == "not_applicable_declined" and doc["rows_switched"] == 0
        assert doc["adopted_column"] == "base__donor_median"
    rec = json.loads((v2 / "alarm_verdict.json").read_text(encoding="utf-8"))
    assert rec["with"]["pooled_mae"] == rec["without"]["pooled_mae_adopted"]
    batches = _alarm(v2, 0)["batches"]
    assert batches and all(len(b["batch"]) == 7 and b["batch"][4] == "-" for b in batches)   # YYYY-MM


def test_t3_forced_switching_in_a_table_run(toys):
    from treeroute.report import metrics as M

    v1, v2 = toys["v1_forced"]["folder"], toys["v2_forced"]["folder"]
    doc = _alarm(v2, 0)
    assert doc["status"] == "active" and doc["twin_arm"].endswith("_corrector_unweighted") and doc["batches_fired"] > 0
    preds = M.read_rows(v2 / "test_preds.parquet")
    alarm = pd.read_parquet(v2 / "alarm_preds.parquet")
    fired = alarm["fired"].to_numpy(dtype=bool)
    twin = preds["arm__" + doc["twin_arm"]].to_numpy(dtype=np.float64)
    adopted = preds[doc["adopted_column"]].to_numpy(dtype=np.float64)
    with_ = alarm["with_alarm"].to_numpy(dtype=np.float64)
    assert np.array_equal(with_[fired], twin[fired]) and np.array_equal(with_[~fired], adopted[~fired])
    assert sha256_of(v1 / "test_preds.parquet") == sha256_of(v2 / "test_preds.parquet")
    rec = json.loads((v2 / "alarm_verdict.json").read_text(encoding="utf-8"))
    assert rec["status"] == "active" and rec["rows_switched"] == int(fired.sum())


def test_t4_the_leads_route_their_twin_apart_and_keep_their_v1_files(toys):
    v1, v2 = toys["v1_forced"]["folder"], toys["v2_forced"]["folder"]
    allowed = {"fitctx_log.parquet"} | {"phases/ladder_lead_%d/fitctx_log.parquet" % L for L in LEADS}
    differ, extra, missing = compare_runs(v1, v2, allowed_extra=allowed)
    assert differ == [] and extra == [] and missing == [], (differ, extra, missing)
    for L in LEADS:
        d1, d2 = v1 / "ladder" / ("lead_%d" % L), v2 / "ladder" / ("lead_%d" % L)
        for name in ("guard_preds.parquet", "test_preds.parquet"):
            assert sha256_of(d1 / name) == sha256_of(d2 / name)
        doc = _alarm(v2, L)
        assert doc["alarm_guard_preds_file"] == "ladder/lead_%d/alarm_guard_preds.parquet" % L
        assert doc["reference"]["surface"] == "lead %d guard surface" % L
        assert doc["twin_routed"] is (doc["status"] == "active")
        assert doc["status"] in ("active", "not_tested_zero_reference_gap")
