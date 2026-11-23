"""tools/alarm_replay.py: the POST-HOC replay of the alarm on a saved v1 run (owner rulings AE3, AE4), on a tiny
synthetic folder shaped like a v1 table run: the replay equals layer.alarm.decide_alarm on the same arrays, is
labelled post-hoc with the AE3 sentence, scores with and without the alarm on the same rows, writes only under its
out folder and leaves the run folder untouched (and refuses an out folder inside it)."""

import datetime as dt
import hashlib
import json
import sys

import numpy as np
import pandas as pd
import pytest

from conftest import ENGINE_DIR

sys.path.insert(0, str(ENGINE_DIR / "tools"))

A = "arcsine_corrector_gls"
T = "arcsine_corrector_unweighted"
POINT = "@level=100.0,ratio=1.0"


def _arm(name):
    link, tool, w = "arcsine", name.split("_")[1], name.split("_")[2]
    return {"link": link, "tool": tool, "weighting": w, "selectable": True}


def _hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


@pytest.fixture
def v1_folder(tmp_path):
    from treeroute.report import metrics as M

    f = tmp_path / "runs" / "toy" / "headline" / "20991231_abcdef12"
    f.mkdir(parents=True)
    rng = np.random.default_rng(7)               # test data only
    groups = ("g1", "g2", "g3")
    rows = []
    for gi, g in enumerate(groups):
        for k in range(36):
            for month, gap in ((1, 0.5), (2, 0.1)):              # month 1: ratio 5 (switches); month 2: ratio 1
                day = dt.date(2010, month, 1 + k % 28).toordinal()
                y = float(rng.uniform(10, 90))
                a = y + rng.normal(0, 3)
                rows.append({"unit": "%s_r%d_%d" % (g, k, month), "group": g, "time": day, "year": 2010, "lead": 0,
                             "issue": day, "y": y, "normal": np.nan, "legal_min": 0.0, "legal_max": 100.0,
                             "arm__" + A: a, "pre__" + A: a, "arm__" + T: a + gap, "pre__" + T: a + gap,
                             "base__donor_median": 50.0})
    test = pd.DataFrame(rows)
    test.to_parquet(f / "test_preds.parquet", index=False)
    inner = pd.DataFrame({"unit": ["s%d" % i for i in range(50)], "group": "g1", "time": 1, "y": 1.0,
                          A + POINT: np.linspace(1, 2, 50), T + POINT: np.linspace(1, 2, 50) + 0.1})
    inner.to_parquet(f / "inner_preds.parquet", index=False)
    pooled = M.score_table(test, (), 1.0, None, "headline")
    mae = float(pooled[(pooled["column"] == "arm__" + A) & (pooled["line"] == "pooled")
                       & (pooled["rows_basis"] == "all")]["mae"].iloc[0])
    files = {
        "adoption.json": {"adopted": _arm(A), "declined": False, "penalty": {"level": 100.0, "ratio": 1.0},
                          "eligible": [_arm(A), _arm(T)]},
        "verdict.json": {"package": "toy", "router_kind": "neighbour", "reference": "base__donor_median",
                         "reference_rule": "donor_row_median", "adopted": A, "adopted_column": "arm__" + A,
                         "hit_tolerance": 1.0, "measurement_error_floor": None, "band": 0.5,
                         "pooled_mae_adopted": mae, "verdict": {"tag": "helps"}},
        "run_record.json": {"kind": "headline", "package": "toy"},
        "derived.json": {"R1": {"value": {"kind": "irregular", "length": None, "unit": None,
                                          "composites_per_year": None, "composite_days": None}},
                         "R14:overlap_blocks": {"value": {"block_of_group": {g: i for i, g in enumerate(groups)}}}},
        "decision_checks.json": {"surface_sha256": "c" * 64}}
    for name, doc in files.items():
        (f / name).write_text(json.dumps(doc), encoding="utf-8")
    return f, test


def test_the_replay_is_the_engine_rule_post_hoc_and_read_only(v1_folder, tmp_path):
    import alarm_replay as R
    from treeroute.layer import alarm as LAL

    folder, test = v1_folder
    before = _hashes(folder)
    out = tmp_path / "replay"
    doc = R.replay_run(folder, out)
    assert _hashes(folder) == before                                       # the run folder is untouched
    written = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert written == ["toy/20991231_abcdef12/alarm_replay.json", "toy/20991231_abcdef12/alarm_replay_scores.csv"]
    assert doc["post_hoc"] is True and doc["alarm_origin"] == LAL.ALARM_ORIGIN and doc["tag"] == LAL.POST_HOC_TAG
    assert doc["leads"].startswith("not replayable")
    # the same rule on the same arrays
    a, t = test["arm__" + A].to_numpy(), test["arm__" + T].to_numpy()
    want = LAL.decide_alarm(LAL.STATUS_ACTIVE, a, a, t, t, LAL.batch_keys(test["issue"].to_numpy(), None),
                            LAL.reference_gap(np.linspace(1, 2, 50), np.linspace(1, 2, 50) + 0.1))
    assert doc["status"] == "active" and doc["twin_arm"] == T and doc["twin_kind"] == "weighting"
    assert [(b["batch"], b["fired"]) for b in doc["batches"]] == [("2010-01", True), ("2010-02", False)]
    assert doc["rows_switched"] == want.rows_switched == 108
    with_ = np.asarray(want.with_alarm)
    y = test["y"].to_numpy()
    assert doc["scores"]["pooled_mae_with"] == pytest.approx(float(np.mean(np.abs(y - with_))), abs=1e-12)
    assert doc["scores"]["pooled_mae_without"] == pytest.approx(float(np.mean(np.abs(y - a))), abs=1e-12)
    scores = pd.read_csv(out / "toy" / "20991231_abcdef12" / "alarm_replay_scores.csv")
    assert set(scores["tag"]) == {LAL.POST_HOC_TAG} and set(scores["line"]) == {"pooled", "year", "group"}
    # a second replay to the same folder confirms the same bytes; an out folder inside the run is refused
    assert R.replay_run(folder, out) == doc
    with pytest.raises(R.ReplayRefusal, match="inside a run folder"):
        R.replay_run(folder, folder / "replay")
