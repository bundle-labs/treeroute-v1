"""Atomic JSON writes, run folders and phase resume keyed by the fingerprint."""

import datetime
import json
import math

import pytest

from conftest import make_registry
from treeroute.errors import ResumeRefusal
from treeroute.runs.atomic import (AtomicWriteError, dumps_canonical, read_json, replace_json,
                                   write_json_once)
from treeroute.runs.registry import Registry
from treeroute.runs.resume import (RUN_IDENTITY, Phases, find_run_folders, mark_run_finished,
                                   open_run)

FP1 = "1" * 64
FP2 = "2" * 64


# ---- atomic writes ----
def test_write_once_creates_then_refuses(tmp_path):
    path = tmp_path / "manifest.json"
    write_json_once(path, {"b": 1, "a": [1, 2]})
    assert read_json(path) == {"a": [1, 2], "b": 1}
    with pytest.raises(AtomicWriteError):
        write_json_once(path, {"c": 3})
    assert read_json(path) == {"a": [1, 2], "b": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["manifest.json"]  # no temp file left


def test_replace_json_replaces_atomically(tmp_path):
    path = tmp_path / "status.json"
    replace_json(path, {"beat": 1})
    replace_json(path, {"beat": 2})
    assert read_json(path) == {"beat": 2}
    assert [p.name for p in tmp_path.iterdir()] == ["status.json"]


def test_non_finite_values_are_refused_and_leave_no_file(tmp_path):
    path = tmp_path / "x.json"
    with pytest.raises(ValueError):
        write_json_once(path, {"v": math.nan})
    with pytest.raises(ValueError):
        write_json_once(path, {"v": math.inf})
    assert not path.exists()


def test_numpy_values_and_sets_are_converted(tmp_path):
    import numpy as np

    obj = {"f": np.float32(0.5), "i": np.int64(3), "a": np.arange(3), "s": {"b", "a"},
           "b": np.bool_(True), "p": tmp_path}
    text = dumps_canonical(obj)
    back = json.loads(text)
    assert back["f"] == 0.5 and back["i"] == 3 and back["a"] == [0, 1, 2]
    assert back["s"] == ["a", "b"] and back["b"] is True and back["p"] == str(tmp_path)


def test_canonical_json_is_order_independent():
    assert dumps_canonical({"a": 1, "b": 2}) == dumps_canonical({"b": 2, "a": 1})


def test_interrupted_write_never_truncates_the_target(tmp_path):
    path = tmp_path / "verdict.json"
    replace_json(path, {"ok": True})
    # a temp file left by a killed writer sits beside the target and changes nothing
    stale = tmp_path / "verdict.json.tmp-99999999"
    stale.write_text('{"half', encoding="utf-8")
    assert read_json(path) == {"ok": True}


def test_temp_names_carry_start_time_and_never_repeat(tmp_path):
    from treeroute.runs import proc
    from treeroute.runs.atomic import temp_name

    pid, created = proc.own_identity()
    a = temp_name(tmp_path / "x.json")
    b = temp_name(tmp_path / "x.json")
    assert a != b
    assert ".tmp-%d-%s-" % (pid, created) in a


def test_stale_temp_file_with_the_same_pid_does_not_block_a_write(tmp_path):
    """A dead process with a reused pid may have left '<file>.tmp-<pid>'; the next write works."""
    import os

    path = tmp_path / "status.json"
    stale_old_style = tmp_path / ("status.json.tmp-%d" % os.getpid())
    stale_old_style.write_text("{", encoding="utf-8")
    replace_json(path, {"beat": 1})
    write_json_once(tmp_path / "once.json", {"a": 1})
    assert read_json(path) == {"beat": 1}
    assert stale_old_style.read_text(encoding="utf-8") == "{"  # never touched


def _hold_open_without_delete_sharing(path, seconds):
    """A plain Python open on Windows shares read and write but not delete, like many readers."""
    import threading
    import time

    fh = open(str(path), encoding="utf-8")

    def release():
        time.sleep(seconds)
        fh.close()

    thread = threading.Thread(target=release)
    thread.start()
    return fh, thread


@pytest.mark.skipif(__import__("os").name != "nt", reason="Windows sharing semantics")
def test_replace_waits_for_a_brief_reader(tmp_path):
    path = tmp_path / "status.json"
    replace_json(path, {"beat": 1})
    fh, thread = _hold_open_without_delete_sharing(path, 0.3)
    try:
        replace_json(path, {"beat": 2})  # retried until the reader let go
    finally:
        thread.join()
    assert fh.closed
    assert read_json(path) == {"beat": 2}
    assert sorted(p.name for p in tmp_path.iterdir()) == ["status.json"]


@pytest.mark.skipif(__import__("os").name != "nt", reason="Windows sharing semantics")
def test_replace_fails_loudly_when_a_reader_never_lets_go(tmp_path, monkeypatch):
    from treeroute.runs import atomic

    monkeypatch.setattr(atomic, "RENAME_WAIT_S", 0.01)
    path = tmp_path / "status.json"
    replace_json(path, {"beat": 1})
    fh = open(str(path), encoding="utf-8")
    try:
        with pytest.raises(AtomicWriteError) as info:
            replace_json(path, {"beat": 2})
    finally:
        fh.close()
    assert str(path) in str(info.value) and "holds the file open" in str(info.value)
    assert read_json(path) == {"beat": 1}
    assert sorted(p.name for p in tmp_path.iterdir()) == ["status.json"]  # own temp removed


@pytest.mark.skipif(__import__("os").name != "nt", reason="Windows sharing semantics")
def test_write_once_publish_waits_for_a_brief_holder_of_its_temp_file(tmp_path, monkeypatch):
    """An antivirus or indexer holding the fresh temp file makes the rename fail for a moment."""
    import os

    from treeroute.runs import atomic

    calls = {"n": 0}
    real_rename = os.rename

    def flaky_rename(src, dst):
        calls["n"] += 1
        if calls["n"] <= 3:
            raise PermissionError(32, "The process cannot access the file", src)
        return real_rename(src, dst)

    monkeypatch.setattr(atomic.os, "rename", flaky_rename)
    monkeypatch.setattr(atomic, "RENAME_WAIT_S", 0.01)
    write_json_once(tmp_path / "manifest.json", {"a": 1})
    monkeypatch.undo()
    assert calls["n"] == 4
    assert read_json(tmp_path / "manifest.json") == {"a": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["manifest.json"]


def test_unreadable_json_names_the_file(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(AtomicWriteError) as info:
        read_json(path)
    assert "broken.json" in str(info.value)


# ---- run folders ----
@pytest.fixture
def registry(tmp_path):
    shipped = tmp_path / "shipped"
    shipped.mkdir()
    return Registry(make_registry(tmp_path, [shipped]))


def test_new_then_resume_then_refuse_when_finished(tmp_path, registry):
    root = tmp_path / "runs"
    day1 = datetime.date(2001, 1, 1)
    first = open_run(root, "pkg", "smoke", FP1, registry, today=day1)
    assert first.state == "new"
    assert first.path.name.endswith("_" + FP1[:8])
    assert read_json(first.path / RUN_IDENTITY)["fingerprint"] == FP1
    # resumed on another day: same folder, found by fingerprint
    again = open_run(root, "pkg", "smoke", FP1, registry, today=datetime.date(2001, 1, 9))
    assert again.state == "resume" and again.path == first.path
    mark_run_finished(first.path, FP1, {"rows": 3})
    with pytest.raises(ResumeRefusal) as info:
        open_run(root, "pkg", "smoke", FP1, registry)
    assert "already finished" in str(info.value)


def test_new_fingerprint_gets_a_new_folder(tmp_path, registry):
    root = tmp_path / "runs"
    a = open_run(root, "pkg", "headline", FP1, registry)
    b = open_run(root, "pkg", "headline", FP2, registry)
    assert a.path != b.path and b.state == "new"
    assert find_run_folders(root / "pkg" / "headline", FP1) == [a.path]


def test_name_collision_with_a_different_fingerprint_is_refused(tmp_path, registry):
    root = tmp_path / "runs"
    a = open_run(root, "pkg", "smoke", FP1, registry)
    other = FP1[:8] + "f" * 56  # same first 8 characters, different fingerprint
    with pytest.raises(ResumeRefusal) as info:
        open_run(root, "pkg", "smoke", other, registry)
    assert "collision" in str(info.value)
    assert read_json(a.path / RUN_IDENTITY)["fingerprint"] == FP1


def test_bad_kind_and_fingerprint_are_rejected(tmp_path, registry):
    with pytest.raises(ValueError):
        open_run(tmp_path, "pkg", "legacy", FP1, registry)
    with pytest.raises(ValueError):
        open_run(tmp_path, "pkg", "smoke", "abc", registry)
    with pytest.raises(ValueError):
        open_run(tmp_path, "../escape", "smoke", FP1, registry)


# ---- phases ----
def test_phase_resume_keyed_by_fingerprint(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    phases = Phases(run_dir, FP1)
    assert not phases.done("pool")
    phases.mark_done("pool", {"rows": 10})
    phases.mark_done("bank")
    # a resumed process sees the same phases done
    resumed = Phases(run_dir, FP1)
    assert resumed.done("pool") and resumed.done("bank") and not resumed.done("tables")
    assert resumed.completed() == ["bank", "pool"]
    # a marker is written once
    with pytest.raises(AtomicWriteError):
        resumed.mark_done("pool")
    # another configuration never reuses these phases
    with pytest.raises(ResumeRefusal):
        Phases(run_dir, FP2).done("pool")


def test_phase_names_are_checked(tmp_path):
    with pytest.raises(ValueError):
        Phases(tmp_path, FP1).mark_done("../x")
