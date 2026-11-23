"""The locked alarm is re-checked after the labels open (skeptic review of the alarm build, 2026-10-21, issues 1, 2, 5
and 6; owner ruling AE).

  W1 pipeline/alarm_pass.verify_alarm (used by both engine reports and the headline-table builder): an untouched
     folder passes; a record edited after its lock, an alarm_preds whose bytes are not the locked hash, an opened
     marker naming another alarm record, a forged 'fired' column whose hashes were made consistent, recorded counts
     or a status that do not follow from the record are each refused;
  W2 with_alarm_frame given the record: the twin column must be the saved twin arm bit for bit, and the nowcast must
     hold it; the pre-clip 'with alarm' column must be the adopted arm's outside the switched rows;
  W3 labels/vault.py: lock_alarm refuses a record naming predictions that are missing; open_test_labels refuses when
     the predictions named by the locked record changed after the lock;
  W4 layer/alarm.py: a negative reference gap is refused (not called 'active'); an issue day ordinal that is not a
     calendar day is an AlarmRefusal; the harness record has its own status.
"""

import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from test_vault_world import decide_world, make_world
from treeroute.labels.vault import (ADOPTION_FILE, ALARM_FILE, ALARM_LOCK_SUFFIX, OPENED_FILE, VaultRefusal,
                                    lock_adoption, lock_alarm)
from treeroute.layer import alarm as LAL
from treeroute.pipeline import alarm_pass as AP
from treeroute.runs.atomic import dumps

N = 80


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _rows():
    a = np.linspace(1.0, 2.0, N)
    t = a.copy()
    t[:40] += 1.0                    # batch step:1 far apart: ratio 10 > 2, fires
    t[40:] += 0.05                   # batch step:2 close: ratio 0.5, stays
    keys = np.asarray(["step:1"] * 40 + ["step:2"] * 40, dtype=object)
    return a, t, keys


def _write(folder, frame, rec, *, doc_edit=None, status=LAL.STATUS_ACTIVE, eligible=True):
    p = folder / AP.ALARM_PREDS
    frame.to_parquet(p, index=False)
    ctx = {"lead": 0, "adopted_arm": "log_c_corrector_gls", "adopted_column": "arm__log_c_corrector_gls",
           "twin_arm": "log_c_corrector_unweighted", "twin_simpler": True, "twin_eligible": eligible,
           "twin_routed": True, "reference": {"gap": 0.1}, "alarm_preds_file": AP.ALARM_PREDS,
           "alarm_preds_sha256": _sha(p), "alarm_guard_preds_file": None, "alarm_guard_preds_sha256": None,
           "test_rows": int(len(frame))}
    doc = LAL.alarm_document(rec, ctx)
    doc["status"] = status
    if doc_edit:
        doc_edit(doc)
    d = folder / (ALARM_FILE % 0)
    d.write_text(dumps(doc) + "\n", encoding="utf-8")
    (folder / (ALARM_FILE % 0 + ALARM_LOCK_SUFFIX)).write_text(
        json.dumps({"lead": 0, "file": ALARM_FILE % 0, "sha256": _sha(d)}), encoding="utf-8")
    return doc


def _frame(rec, a, t, keys):
    return pd.DataFrame({"unit": np.asarray(["u%d" % (i % 8) for i in range(N)], dtype=object),
                         "group": np.asarray(["g"] * N, dtype=object), "time": np.arange(N, dtype=np.int64),
                         "year": np.full(N, 2020, dtype=np.int64), "lead": np.zeros(N, dtype=np.int64),
                         "issue": np.asarray([1] * 40 + [2] * 40, dtype=np.int64), "batch": keys,
                         "adopted": a, "twin": t, "with_alarm": np.asarray(rec.with_alarm),
                         "pre_with_alarm": np.asarray(rec.pre_with_alarm), "fired": np.asarray(rec.fired)})


@pytest.fixture
def folder(tmp_path):
    a, t, keys = _rows()
    rec = LAL.decide_alarm(LAL.STATUS_ACTIVE, a, a, t, t, keys, 0.1)
    _write(tmp_path, _frame(rec, a, t, keys), rec)
    return tmp_path


# ------------------------------------------------------------------------------------------------ W1
def test_w1_an_untouched_folder_passes(folder):
    doc, alarm = AP.verify_alarm(folder, 0)
    assert doc["batches_fired"] == 1 and doc["rows_switched"] == 40 and int(alarm["fired"].sum()) == 40


def test_w1_a_record_edited_after_its_lock_is_refused(folder):
    p = folder / (ALARM_FILE % 0)
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["reference"]["gap"] = 1.0
    p.write_text(dumps(doc) + "\n", encoding="utf-8")
    with pytest.raises(AP.AlarmPassRefusal, match="changed after its lock"):
        AP.verify_alarm(folder, 0)


def test_w1_alarm_preds_with_other_bytes_are_refused(folder):
    p = folder / AP.ALARM_PREDS
    pd.read_parquet(p).to_parquet(p, index=False, compression="gzip")        # same values, other bytes
    with pytest.raises(AP.AlarmPassRefusal, match="is not the file the locked alarm record hashed"):
        AP.verify_alarm(folder, 0)


def test_w1_an_opened_marker_naming_another_alarm_record_is_refused(folder):
    (folder / (OPENED_FILE % 0)).write_text(json.dumps({"lead": 0, "alarm_sha256": "0" * 64}), encoding="utf-8")
    with pytest.raises(AP.AlarmPassRefusal, match="opened against alarm record"):
        AP.verify_alarm(folder, 0)


def test_w1_a_forged_fired_column_with_consistent_hashes_is_refused(tmp_path):
    a, t, keys = _rows()
    rec = LAL.decide_alarm(LAL.STATUS_ACTIVE, a, a, t, t, keys, 0.1)
    frame = _frame(rec, a, t, keys)
    fired = frame["fired"].to_numpy(dtype=bool).copy()
    fired[40:] = True                                    # batch step:2 (ratio 0.5) claimed as switched
    frame["fired"] = fired
    frame["with_alarm"] = np.where(fired, t, a)
    _write(tmp_path, frame, rec, doc_edit=lambda d: d.update(rows_switched=80))
    with pytest.raises(AP.AlarmPassRefusal, match="not what the locked rule gives"):
        AP.verify_alarm(tmp_path, 0)


def test_w1_recorded_batches_or_counts_that_do_not_follow_are_refused(tmp_path):
    a, t, keys = _rows()
    rec = LAL.decide_alarm(LAL.STATUS_ACTIVE, a, a, t, t, keys, 0.1)

    def edit(d):
        d["batches"][1]["ratio"] = 9.0
    _write(tmp_path, _frame(rec, a, t, keys), rec, doc_edit=edit)
    with pytest.raises(AP.AlarmPassRefusal, match="recorded batches"):
        AP.verify_alarm(tmp_path, 0)
    _write(tmp_path, _frame(rec, a, t, keys), rec, doc_edit=lambda d: d.update(batches_tested=1))
    with pytest.raises(AP.AlarmPassRefusal, match="recorded counts"):
        AP.verify_alarm(tmp_path, 0)


def test_w1_a_status_that_does_not_follow_from_the_facts_is_refused(tmp_path):
    a, t, keys = _rows()
    rec = LAL.decide_alarm(LAL.STATUS_ACTIVE, a, a, t, t, keys, 0.1)
    _write(tmp_path, _frame(rec, a, t, keys), rec, eligible=False)      # 'active' while the twin is not eligible
    with pytest.raises(AP.AlarmPassRefusal, match="does not follow from its facts"):
        AP.verify_alarm(tmp_path, 0)


# ------------------------------------------------------------------------------------------------ W2
def _preds(alarm, twin):
    return pd.DataFrame({"unit": alarm["unit"], "time": alarm["time"],
                         "arm__log_c_corrector_gls": alarm["adopted"], "arm__log_c_corrector_unweighted": twin})


def test_w2_the_twin_column_must_be_the_saved_twin_arm(folder):
    doc, alarm = AP.verify_alarm(folder, 0)
    ok = AP.with_alarm_frame(_preds(alarm, alarm["twin"]), alarm, "arm__log_c_corrector_gls", doc)
    assert np.array_equal(ok[LAL.WITH_ALARM_COLUMN].to_numpy(), alarm["with_alarm"].to_numpy())
    with pytest.raises(AP.AlarmPassRefusal, match="twin column is not the saved"):
        AP.with_alarm_frame(_preds(alarm, alarm["twin"] + 1e-9), alarm, "arm__log_c_corrector_gls", doc)
    with pytest.raises(AP.AlarmPassRefusal, match="hold no arm__log_c_corrector_unweighted"):
        AP.with_alarm_frame(_preds(alarm, alarm["twin"]).drop(columns=["arm__log_c_corrector_unweighted"]), alarm,
                            "arm__log_c_corrector_gls", doc)


def test_w2_the_pre_clip_with_alarm_column_must_follow_the_saved_pre_clip_arms(folder):
    doc, alarm = AP.verify_alarm(folder, 0)
    preds = _preds(alarm, alarm["twin"])
    preds["pre__log_c_corrector_gls"] = alarm["adopted"]
    preds["pre__log_c_corrector_unweighted"] = alarm["twin"]
    AP.with_alarm_frame(preds, alarm, "arm__log_c_corrector_gls", doc)
    preds["pre__log_c_corrector_gls"] = alarm["adopted"] - 1.0
    with pytest.raises(AP.AlarmPassRefusal, match="outside the switched rows"):
        AP.with_alarm_frame(preds, alarm, "arm__log_c_corrector_gls", doc)


# ------------------------------------------------------------------------------------------------ W3
@pytest.fixture
def world(tmp_path):
    f = tmp_path / "run"
    f.mkdir()
    return make_world(run_folder=f)


def _adopt(world):
    return lock_adoption(decide_world(world).adoption, world.labels, world.labels.run_folder)


def test_w3_lock_alarm_refuses_a_record_naming_missing_predictions(world):
    folder = world.labels.run_folder
    sha = _adopt(world)
    doc = dict(LAL.not_applicable_document(0, ADOPTION_FILE, sha, "verify test"))
    doc.update({"alarm_preds_file": "alarm_preds.parquet", "alarm_preds_sha256": "f" * 64})
    with pytest.raises(VaultRefusal, match="which is missing"):
        lock_alarm(doc, 0, world.labels, folder)
    assert not (folder / (ALARM_FILE % 0)).exists()


def test_w3_open_refuses_predictions_changed_after_the_lock(world):
    folder = world.labels.run_folder
    sha = _adopt(world)
    p = folder / "alarm_preds.parquet"
    pd.DataFrame({"x": [1.0, 2.0]}).to_parquet(p, index=False)
    doc = dict(LAL.not_applicable_document(0, ADOPTION_FILE, sha, "verify test"))
    doc.update({"alarm_preds_file": "alarm_preds.parquet", "alarm_preds_sha256": _sha(p)})
    alarm = lock_alarm(doc, 0, world.labels, folder)
    pd.DataFrame({"x": [1.0, 3.0]}).to_parquet(p, index=False)
    with pytest.raises(VaultRefusal, match="is not the file the locked alarm record of lead 0 hashed"):
        world.labels.open_test_labels(sha, 0, alarm_sha256=alarm)
    assert not (folder / (OPENED_FILE % 0)).exists()


# ------------------------------------------------------------------------------------------------ W4
def test_w4_a_negative_reference_gap_is_refused():
    with pytest.raises(LAL.AlarmRefusal, match="negative"):
        LAL.pass_status(False, True, True, -1.0)
    a = np.zeros(40)
    with pytest.raises(LAL.AlarmRefusal, match="negative"):
        LAL.decide_alarm(LAL.STATUS_ACTIVE, a, a, a + 1, a + 1, np.asarray(["k"] * 40, dtype=object), -1.0)
    assert LAL.pass_status(False, True, True, 0.0) == LAL.STATUS_ZERO_GAP          # zero stays 'not tested' (D3)


def test_w4_an_issue_ordinal_that_is_not_a_calendar_day_is_an_alarm_refusal():
    with pytest.raises(LAL.AlarmRefusal, match="not a calendar day"):
        LAL.batch_keys(np.asarray([0, 1], dtype=np.int64))


def test_w4_the_harness_record_has_its_own_status():
    doc = LAL.not_applicable_document(0, ADOPTION_FILE, "b" * 64, "a harness replay")
    assert doc["status"] == LAL.STATUS_HARNESS != LAL.STATUS_DECLINED and LAL.STATUS_HARNESS in LAL.STATUSES
