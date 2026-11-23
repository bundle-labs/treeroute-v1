"""labels/vault.py: the alarm lock (owner ruling AE: the alarm's decision and predictions are locked before a pass's
test labels open).

  V1 lock_alarm after the adoption lock, then open_test_labels(..., alarm_sha256) opens; the opened marker records the
     alarm hash; the lock record's suffix is not an adoption lock's;
  V2 planted faults: opening without the alarm lock, with a wrong alarm hash, after the alarm file changed on disk;
     lock_alarm after that pass's labels opened, before its adoption lock, naming another adoption or lead, or with
     other bytes; a reloaded folder with an adoption lock AND an alarm lock for lead 0 is accepted (the suffixes do
     not collide) and a tampered alarm file is refused.
"""

import json
import os

import pytest

from test_vault_world import decide_world, make_world
from treeroute.labels.vault import (ADOPTION_FILE, ALARM_FILE, ALARM_LOCK_SUFFIX, LOCK_SUFFIX, OPENED_FILE,
                                    VaultRefusal, lock_adoption, lock_alarm)
from treeroute.layer.alarm import not_applicable_document


@pytest.fixture
def world(tmp_path):
    folder = tmp_path / "run"
    folder.mkdir()
    return make_world(run_folder=folder)


def _doc(sha, lead=0, reason="vault test"):
    return not_applicable_document(lead, ADOPTION_FILE, sha, reason)


def _lock(world):
    return lock_adoption(decide_world(world).adoption, world.labels, world.labels.run_folder)


def test_v1_lock_then_open_records_the_alarm_hash(world):
    folder = world.labels.run_folder
    sha = _lock(world)
    alarm = lock_alarm(_doc(sha), 0, world.labels, folder)
    assert not (ALARM_FILE % 0 + ALARM_LOCK_SUFFIX).endswith(LOCK_SUFFIX)
    rec = json.loads((folder / (ALARM_FILE % 0 + ALARM_LOCK_SUFFIX)).read_text(encoding="utf-8"))
    assert rec["sha256"] == alarm and rec["lead"] == 0 and rec["adoption_sha256"] == sha
    assert lock_alarm(_doc(sha), 0, world.labels, folder) == alarm               # the same record confirms
    test = world.labels.open_test_labels(sha, 0, alarm_sha256=alarm)
    assert test.lead == 0
    marker = json.loads((folder / (OPENED_FILE % 0)).read_text(encoding="utf-8"))
    assert marker["alarm_sha256"] == alarm and marker["adoption_sha256"] == sha
    assert float(rec["locked_at_epoch"]) <= os.path.getmtime(folder / (OPENED_FILE % 0)) + 1.0


def test_v2_open_without_or_against_another_alarm_record_is_refused(world):
    folder = world.labels.run_folder
    sha = _lock(world)
    with pytest.raises(VaultRefusal, match="no locked alarm record"):
        world.labels.open_test_labels(sha, 0, alarm_sha256="0" * 64)
    with pytest.raises(TypeError):
        world.labels.open_test_labels(sha, 0)                                   # the keyword is required
    alarm = lock_alarm(_doc(sha), 0, world.labels, folder)
    wrong = ("1" if alarm[0] != "1" else "2") + alarm[1:]
    with pytest.raises(VaultRefusal, match="alarm hash mismatch"):
        world.labels.open_test_labels(sha, 0, alarm_sha256=wrong)
    with pytest.raises(VaultRefusal, match="SHA-256 hex"):
        world.labels.open_test_labels(sha, 0, alarm_sha256="not a hash")
    path = folder / (ALARM_FILE % 0)
    os.chmod(str(path), 0o666)
    path.write_text(path.read_text(encoding="utf-8").replace('"batches_fired": 0', '"batches_fired": 1'),
                    encoding="utf-8")                                           # tampered after the lock
    with pytest.raises(VaultRefusal, match="alarm hash mismatch"):
        world.labels.open_test_labels(sha, 0, alarm_sha256=alarm)
    with pytest.raises(VaultRefusal, match="differs from its alarm lock record"):
        make_world(run_folder=folder)                                           # a resumed run refuses the folder
    assert world.labels.opened_passes() == {}


def test_v2_lock_alarm_is_refused_out_of_order_or_against_another_record(world):
    folder = world.labels.run_folder
    with pytest.raises(VaultRefusal, match="no locked adoption"):
        lock_alarm(_doc("a" * 64), 0, world.labels, folder)                     # before the adoption lock
    sha = _lock(world)
    with pytest.raises(VaultRefusal, match="names adoption"):
        lock_alarm(_doc("a" * 64), 0, world.labels, folder)
    with pytest.raises(VaultRefusal, match="names lead"):
        lock_alarm(_doc(sha, lead=0), 3, world.labels, folder)
    alarm = lock_alarm(_doc(sha), 0, world.labels, folder)
    with pytest.raises(VaultRefusal, match="different content"):
        lock_alarm(_doc(sha, reason="another record"), 0, world.labels, folder)   # a resume that decides otherwise
    world.labels.open_test_labels(sha, 0, alarm_sha256=alarm)
    assert lock_alarm(_doc(sha), 0, world.labels, folder) == alarm                # confirming the same record is fine
    with pytest.raises(VaultRefusal, match="open already|different content"):
        lock_alarm(_doc(sha, reason="after the labels opened"), 0, world.labels, folder)


def test_v2_a_reloaded_folder_accepts_both_locks_of_lead_zero(world):
    folder = world.labels.run_folder
    sha = _lock(world)
    alarm = lock_alarm(_doc(sha), 0, world.labels, folder)
    world.labels.open_test_labels(sha, 0, alarm_sha256=alarm)
    again = make_world(run_folder=folder)
    assert again.labels.locked_passes() == {0: sha} and again.labels.alarm_locked_passes() == {0: alarm}
    assert again.labels.opened_passes() == {0: sha}
    marker = folder / (OPENED_FILE % 0)
    rec = json.loads(marker.read_text(encoding="utf-8"))
    os.chmod(str(marker), 0o666)
    marker.write_text(json.dumps(dict(rec, alarm_sha256="f" * 64)), encoding="utf-8")
    with pytest.raises(VaultRefusal, match="opened against alarm record"):
        make_world(run_folder=folder)
