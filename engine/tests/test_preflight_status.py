"""Pre-flight go/refuse, orphan temp files, the heavy-job lock, and the status heartbeat."""

import json

import pytest

from treeroute.errors import PreflightRefusal
from treeroute.runs import proc
from treeroute.runs.preflight import (HEAVY_LOCK_FILE, HeavyJobLock, check_resources,
                                      find_orphan_temp_files, refuse_orphans)
from treeroute.runs.status import StatusWriter, describe, read_status

FP = "c" * 64


def test_small_needs_go(tmp_path):
    out = check_resources(tmp_path, need_disk_bytes=1, need_ram_bytes=1)
    assert out["free_disk_bytes"] > 0 and out["available_ram_bytes"] > 0


def test_huge_needs_refuse_with_the_fix(tmp_path):
    with pytest.raises(PreflightRefusal) as info:
        check_resources(tmp_path / "not" / "yet" / "made", need_disk_bytes=10 ** 18,
                        need_ram_bytes=10 ** 18)
    text = str(info.value)
    assert "G-DISK" in text and "free" in text and "GiB" in text          # sizes in 2^30 bytes, labelled GiB
    assert "never reduced" in text


def test_orphans_are_found_and_refused_but_never_deleted(tmp_path):
    pid, created = proc.own_identity()
    live = tmp_path / ("treeroute_%d_%d_live.mm" % (pid, created))
    dead = tmp_path / ("treeroute_%d_%d_dead.mm" % (pid, created + 1))  # same pid, other start
    other = tmp_path / "unrelated.bin"
    for p in (live, dead, other):
        p.write_bytes(b"x")
    assert find_orphan_temp_files(tmp_path) == [dead]
    with pytest.raises(PreflightRefusal) as info:
        refuse_orphans(tmp_path)
    assert "dead" in str(info.value) and "by hand" in str(info.value)
    assert dead.exists() and live.exists() and other.exists()


def test_heavy_job_lock(tmp_path):
    with HeavyJobLock(tmp_path) as lock:
        assert (tmp_path / HEAVY_LOCK_FILE).exists()
        with pytest.raises(PreflightRefusal) as info:
            HeavyJobLock(tmp_path).acquire()
        assert "another heavy engine job" in str(info.value)
        assert lock.held
    assert not (tmp_path / HEAVY_LOCK_FILE).exists()


def test_stale_lock_is_refused_not_removed(tmp_path):
    path = tmp_path / HEAVY_LOCK_FILE
    path.write_text(json.dumps({"pid": 1, "pid_created_ms": 1}), encoding="utf-8")
    with pytest.raises(PreflightRefusal) as info:
        HeavyJobLock(tmp_path).acquire()
    assert "stale" in str(info.value)
    assert path.exists()


def test_status_heartbeat(tmp_path):
    writer = StatusWriter(tmp_path, FP)
    writer.beat("pool", "streaming", done=3, total=10)
    status = read_status(tmp_path)
    assert status["phase"] == "pool" and status["beat"] == 1 and status["fingerprint"] == FP
    line = describe(status)
    assert "running" in line and "3/10" in line and "gone" not in line
    writer.finish()
    assert read_status(tmp_path)["state"] == "finished"


@pytest.mark.skipif(__import__("os").name != "nt", reason="Windows sharing semantics")
def test_beat_survives_a_reader_holding_status_json(tmp_path):
    """A reader that holds status.json for a moment (as 'treeroute status' or a GUI poll does)
    makes the rename fail on Windows; the beat waits for it instead of crashing the run."""
    import threading
    import time

    writer = StatusWriter(tmp_path, FP)
    writer.beat("pool")
    writer.beat("bank")
    fh = open(str(tmp_path / "status.json"), encoding="utf-8")
    thread = threading.Thread(target=lambda: (time.sleep(0.3), fh.close()))
    thread.start()
    try:
        writer.beat("tables")
    finally:
        thread.join()
    status = read_status(tmp_path)
    assert status["phase"] == "tables" and status["beat"] == 3


def test_status_of_a_dead_writer_says_so(tmp_path):
    writer = StatusWriter(tmp_path, FP)
    writer.beat("bank")
    status = read_status(tmp_path)
    status["pid_created_ms"] = status["pid_created_ms"] + 1  # as if the pid were reused
    assert "process is gone" in describe(status)
    assert describe(None) == "no status.json yet"
