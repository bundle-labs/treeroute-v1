"""runs/room.py (owner ruling Q1, OWNER_RULINGS_2026-10-06.md section Q): in-run RAM and temp-disk checks WAIT for
room instead of refusing, and refuse as before after P7.room_max_wait_seconds; memory is given back (gc, the
working-set trim) before a waiting check and before the GLS donor matrix.

  - wait_for_room: a check that passes runs once (no release, no sleep); a check that refuses is retried after a
    memory release and then every poll, with notes (need, what is there, the biggest programs) at most every note
    interval; after the maximum wait the LAST refusal is raised again (today's exception and message); any other
    exception passes through at once;
  - trim_working_set never raises and counts whether it ran; top_programs is fail-safe;
  - the P7 constants are registered;
  - the converted sites call wait_for_room, the plan-time pre-flights keep refusing at once (source scan), and
    Pipeline._refuse_ram waits only when asked (wait=True);
  - review fixes (2026-10-15): only a refusal marked as a shortage (runs.preflight.mark_shortage) waits; one that is
    not a shortage, or needs more than the machine's total RAM or the disk's total size, refuses at once; every
    note starts "[waiting]" and goes through the run's echo (run.log: "[hh:mm:ss] [waiting] room: ..."), stamped the
    same way without one; the store and both GLS fits hand the run's echo to the check.
Tiny and fast: clock and sleep are injected; nothing really waits.
"""

import inspect
import re
import sys
from types import SimpleNamespace

import pytest

from treeroute import engine_constants as K
from treeroute.errors import PreflightRefusal, RefusedError
from treeroute.runs import preflight, room

STAMPED_NOTE = re.compile(r"^\[\d\d:\d\d:\d\d\] \[waiting\] room: ")


class FakeClock(object):
    def __init__(self):
        self.t = 0.0
        self.sleeps = []

    def clock(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s


def refusing(n_refusals, value="go", need_ram=1 << 20):
    """A check that refuses n_refusals times (a PreflightRefusal marked as a RAM shortage of need_ram bytes,
    numbered), then returns value."""
    calls = []

    def check():
        calls.append(1)
        if len(calls) <= n_refusals:
            raise preflight.mark_shortage(PreflightRefusal("G-DISK", "RAM needs 9.00 GiB, %d.00 GiB available"
                                                           % len(calls)), need_ram=need_ram)
        return value
    return check, calls


def test_a_check_that_passes_runs_once_without_release_or_sleep(monkeypatch):
    released = []
    monkeypatch.setattr(room, "release_memory", lambda: released.append(1) or {"gc_collected": 0, "trimmed": False})
    fc = FakeClock()
    notes = []
    check, calls = refusing(0, {"ok": 1})
    assert room.wait_for_room(check, "x", notes.append, clock=fc.clock, sleep=fc.sleep) == {"ok": 1}
    assert len(calls) == 1 and released == [] and fc.sleeps == [] and notes == []


def test_a_refusal_that_the_memory_release_solves_continues_at_once(monkeypatch):
    released = []
    monkeypatch.setattr(room, "release_memory", lambda: released.append(1) or {"gc_collected": 3, "trimmed": True})
    fc = FakeClock()
    notes = []
    check, calls = refusing(1)
    assert room.wait_for_room(check, "the thing", notes.append, clock=fc.clock, sleep=fc.sleep) == "go"
    assert len(calls) == 2 and released == [1] and fc.sleeps == []
    assert len(notes) == 1 and "room after the memory release" in notes[0]


def test_a_check_waits_polls_and_notes_then_continues(monkeypatch):
    monkeypatch.setattr(room, "release_memory", lambda: {"gc_collected": 0, "trimmed": True})
    monkeypatch.setattr(room, "top_programs", lambda count=None: [(5 << 30, "bigapp.exe", 42)])
    fc = FakeClock()
    notes = []
    check, calls = refusing(6)          # the first call, the retry after the release, then 4 polls refuse
    out = room.wait_for_room(check, "one group's reader", notes.append, poll_seconds=30, note_seconds=60,
                             max_wait_seconds=3600, clock=fc.clock, sleep=fc.sleep)
    assert out == "go" and len(calls) == 7
    assert fc.sleeps == [30.0] * 5
    waiting = [n for n in notes if "is waiting for room" in n]
    # notes at t = 0, 60, 120 (at most one a minute) while it refused at t = 0, 30, 60, 90, 120
    assert len(waiting) == 3
    assert "one group's reader" in waiting[0] and "9.00 GiB" in waiting[0] and "bigapp.exe (pid 42) 5.00 GiB" in waiting[0]
    assert "nothing is lost while it waits" in waiting[0]
    assert "room after waiting" in notes[-1]


def test_after_the_maximum_wait_the_last_refusal_is_raised_as_before(monkeypatch):
    monkeypatch.setattr(room, "release_memory", lambda: {"gc_collected": 0, "trimmed": False})
    monkeypatch.setattr(room, "top_programs", lambda count=None: [])
    fc = FakeClock()
    notes = []
    check, calls = refusing(10 ** 6)
    with pytest.raises(PreflightRefusal) as info:
        room.wait_for_room(check, "x", notes.append, poll_seconds=10, note_seconds=1000, max_wait_seconds=35,
                           clock=fc.clock, sleep=fc.sleep)
    assert sum(fc.sleeps) >= 35 and len(calls) == len(fc.sleeps) + 2
    assert "%d.00 GiB available" % len(calls) in str(info.value)          # the last check's own numbers
    assert info.value.rule == "G-DISK"
    assert "refusing as before" in notes[-1]


def test_a_zero_maximum_wait_refuses_after_one_release_and_recheck(monkeypatch):
    monkeypatch.setattr(K, "ROOM_MAX_WAIT_SECONDS", 0)
    monkeypatch.setattr(room, "release_memory", lambda: {"gc_collected": 0, "trimmed": False})
    fc = FakeClock()
    check, calls = refusing(10)
    with pytest.raises(PreflightRefusal):
        room.wait_for_room(check, "x", lambda s: None, clock=fc.clock, sleep=fc.sleep)
    assert len(calls) == 2 and fc.sleeps == []


def test_a_refusal_that_is_not_a_shortage_refuses_at_once(monkeypatch):
    released = []
    monkeypatch.setattr(room, "release_memory", lambda: released.append(1) or {"gc_collected": 0, "trimmed": False})
    fc = FakeClock()
    notes = []
    calls = []

    def check():
        calls.append(1)
        raise PreflightRefusal("G-DISK", "no existing folder above X:/nowhere")       # no shortage mark
    with pytest.raises(PreflightRefusal, match="no existing folder"):
        room.wait_for_room(check, "x", notes.append, clock=fc.clock, sleep=fc.sleep)
    assert len(calls) == 1 and released == [] and fc.sleeps == []
    assert len(notes) == 1 and notes[0].startswith("[waiting] room: x: refusing at once")
    assert "not a shortage" in notes[0]


def test_a_need_above_the_machine_total_refuses_at_once(tmp_path, monkeypatch):
    released = []
    monkeypatch.setattr(room, "release_memory", lambda: released.append(1) or {"gc_collected": 0, "trimmed": False})
    fc = FakeClock()
    notes = []
    check, calls = refusing(10, need_ram=preflight.total_ram_bytes() + 1)
    with pytest.raises(PreflightRefusal):
        room.wait_for_room(check, "x", notes.append, clock=fc.clock, sleep=fc.sleep)
    assert len(calls) == 1 and released == [] and fc.sleeps == []
    assert "more than the machine's total RAM" in notes[-1]
    disk_calls = []

    def disk_check():
        disk_calls.append(1)
        raise preflight.mark_shortage(PreflightRefusal("G-DISK", "disk short"),
                                      need_disk=preflight.total_disk_bytes(tmp_path) + 1, disk_path=tmp_path)
    with pytest.raises(PreflightRefusal, match="disk short"):
        room.wait_for_room(disk_check, "y", notes.append, clock=fc.clock, sleep=fc.sleep)
    assert len(disk_calls) == 1 and released == [] and "more than that disk's total size" in notes[-1]
    # within the totals, the same marks wait (a shortage that may pass)
    monkeypatch.setattr(K, "ROOM_POLL_SECONDS", 0)
    check, calls = refusing(2, need_ram=preflight.total_ram_bytes())
    assert room.wait_for_room(check, "z", notes.append, clock=fc.clock, sleep=fc.sleep) == "go" and len(calls) == 3


def test_check_resources_marks_its_refusals_as_shortages(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight, "available_ram_bytes", lambda: 100)
    monkeypatch.setattr(preflight, "free_disk_bytes", lambda path: 50)
    with pytest.raises(PreflightRefusal) as info:
        preflight.check_resources(tmp_path, 10, 1000)                   # RAM short, disk fits
    assert info.value.shortage == {"need_ram": 1000, "need_disk": None, "disk_path": str(tmp_path)}
    with pytest.raises(PreflightRefusal) as info:
        preflight.check_resources(tmp_path, 60, 1000)                   # both short
    assert info.value.shortage == {"need_ram": 1000, "need_disk": 60, "disk_path": str(tmp_path)}
    assert preflight.check_resources(tmp_path, 50, 100)["need_ram_bytes"] == 100     # fits: go, as before


def test_the_gls_refusals_are_marked_as_shortages(tmp_path, monkeypatch):
    from treeroute.fit import weights
    from treeroute.fit.weights import WeightsRefusal

    parts = {"rows": 10, "columns": 3, "matrix": 120, "build": 130, "answer_read": 140, "answer_read_group": "g",
             "forest": 150, "peak": 150, "matrix_file": 120}
    monkeypatch.setattr(preflight, "available_ram_bytes", lambda: 149)
    with pytest.raises(WeightsRefusal) as info:
        weights._refuse_gls_ram(parts)
    assert info.value.shortage["need_ram"] == 150 and info.value.shortage["need_disk"] is None
    monkeypatch.setattr(preflight, "free_disk_bytes", lambda path: 119)
    with pytest.raises(WeightsRefusal) as info:
        weights._refuse_gls_ram(parts, tmp_path)
    assert info.value.shortage == {"need_ram": None, "need_disk": 120, "disk_path": str(tmp_path)}


def test_every_note_starts_waiting_and_reaches_the_run_log(tmp_path, monkeypatch, capsys):
    from treeroute.pipeline.record import RUN_LOG, RunLog

    monkeypatch.setattr(room, "release_memory", lambda: {"gc_collected": 0, "trimmed": False})
    monkeypatch.setattr(room, "top_programs", lambda count=None: [])
    log = RunLog(echo=lambda line: None)
    log.attach(tmp_path)
    fc = FakeClock()
    check, _ = refusing(4)
    room.wait_for_room(check, "a reader", log, poll_seconds=10, note_seconds=10, max_wait_seconds=100,
                       clock=fc.clock, sleep=fc.sleep)
    lines = (tmp_path / RUN_LOG).read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 3 and all(STAMPED_NOTE.match(line) for line in lines), lines
    assert any("is waiting for room" in line for line in lines) and "continuing" in lines[-1]
    # without a run echo the notes are printed with the same stamp
    check, _ = refusing(1)
    room.wait_for_room(check, "b", clock=fc.clock, sleep=fc.sleep)
    printed = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert printed and all(STAMPED_NOTE.match(line) for line in printed), printed


def test_the_store_and_both_gls_fits_hand_the_run_echo_to_the_check():
    from treeroute.fit import tables
    from treeroute.pipeline import ladder, passes

    assert "self._echo)" in _source(tables.TreeAnswerStore._build_segment)
    assert "echo=echo" in _source(tables.TreeAnswerStore.from_bank)
    for mod, gls in ((passes, 0), (ladder, 1)):
        src = inspect.getsource(mod)
        stores = src.count("TreeAnswerStore.from_bank(")
        assert stores >= 2 and src.count("echo=p.log)") == stores + gls, mod.__name__
    assert "matrix_dir=p.temp_dir, echo=p.log)" in inspect.getsource(ladder)
    assert "matrix_dir=p.temp_dir,\n" in inspect.getsource(passes) and "echo=self.log)" in inspect.getsource(passes)


def test_other_exceptions_pass_through_at_once(monkeypatch):
    fc = FakeClock()
    calls = []

    def check():
        calls.append(1)
        raise ValueError("not a room problem")
    with pytest.raises(ValueError):
        room.wait_for_room(check, "x", lambda s: None, clock=fc.clock, sleep=fc.sleep)
    assert len(calls) == 1 and fc.sleeps == []

    def other_refusal():
        calls.append(1)
        raise RefusedError("R25", "a rule refused")
    with pytest.raises(RefusedError):
        room.wait_for_room(other_refusal, "x", lambda s: None, clock=fc.clock, sleep=fc.sleep)   # not a PreflightRefusal
    assert len(calls) == 2


def test_the_defaults_are_the_p7_engine_constants(monkeypatch):
    assert (K.get("P7.room_poll_seconds"), K.get("P7.room_note_seconds"), K.get("P7.room_max_wait_seconds"),
            K.get("P7.room_top_programs")) == (K.ROOM_POLL_SECONDS, K.ROOM_NOTE_SECONDS, K.ROOM_MAX_WAIT_SECONDS,
                                               K.ROOM_TOP_PROGRAMS) == (30, 600, 43200, 5)
    monkeypatch.setattr(K, "ROOM_POLL_SECONDS", 7)
    monkeypatch.setattr(K, "ROOM_MAX_WAIT_SECONDS", 20)
    monkeypatch.setattr(room, "release_memory", lambda: {"gc_collected": 0, "trimmed": False})
    monkeypatch.setattr(room, "top_programs", lambda count=None: [])
    fc = FakeClock()
    check, _ = refusing(10 ** 6)
    with pytest.raises(PreflightRefusal):
        room.wait_for_room(check, "x", lambda s: None, clock=fc.clock, sleep=fc.sleep)
    assert fc.sleeps == [7.0, 7.0, 7.0]                      # read at the call: 0, 7, 14, then 21 >= 20 refuses


def test_trim_working_set_never_raises_and_counts(monkeypatch):
    before = dict(room.TRIMS)
    got = room.trim_working_set()
    assert isinstance(got, bool)
    assert sum(room.TRIMS.values()) == sum(before.values()) + 1
    if sys.platform.startswith("win"):
        assert got is True                                    # EmptyWorkingSet on our own process
        import ctypes

        def broken(*a, **k):
            raise OSError("no such library")
        monkeypatch.setattr(ctypes, "WinDLL", broken)
        failed = room.TRIMS["failed"]
        assert room.trim_working_set() is False and room.TRIMS["failed"] == failed + 1
    monkeypatch.setattr(sys, "platform", "linux")
    skipped = room.TRIMS["skipped"]
    assert room.trim_working_set() is False and room.TRIMS["skipped"] == skipped + 1


def test_release_memory_and_top_programs_are_fail_safe(monkeypatch):
    out = room.release_memory()
    assert set(out) == {"gc_collected", "trimmed"} and isinstance(out["trimmed"], bool)
    rows = room.top_programs(3)
    assert len(rows) <= 3 and all(isinstance(r[0], int) and isinstance(r[1], str) for r in rows)
    assert [r[0] for r in rows] == sorted((r[0] for r in rows), reverse=True)
    import psutil

    def broken(*a, **k):
        raise RuntimeError("no process table")
    monkeypatch.setattr(psutil, "process_iter", broken)
    assert room.top_programs() == []


# ------------------------------------------------------------------ which sites wait (ruling Q1) and which refuse
def _source(obj):
    return inspect.getsource(obj)


def test_the_in_run_sites_wait_and_the_plan_time_preflights_refuse():
    from treeroute.fit import tables, weights
    from treeroute.pipeline import run as RUN
    from treeroute.runs import checkpoint

    P = RUN.Pipeline
    # converted (in-run): the four reader / label-row checks, the post-derive disk check, the store's segment check,
    # the GLS weight model's check
    for name in ("_check_picked_rows", "_check_label_rows", "_check_group_reader_rows", "_check_sample_reader_rows"):
        assert "wait=True" in _source(getattr(P, name)), name
    assert "wait_for_room" in _source(P._refuse_ram)
    assert _source(P._preflight_disk).count("wait_for_room(") == 2
    assert "wait_for_room(" in _source(tables.TreeAnswerStore._build_segment)
    assert "wait_for_room(" in _source(weights.weight_model_for_cut)
    # kept (plan-time, before any work starts): the census pre-flight, the in-memory gates' pre-flights, the
    # checkpoints' disk check before the census
    assert "wait=True" not in _source(P._preflight_census)
    assert "wait_for_room" not in _source(P._preflight_target) + _source(P._preflight_frame)
    assert "wait_for_room" not in _source(checkpoint.disk_check)


def test_pipeline_refuse_ram_waits_only_when_asked(tmp_path, monkeypatch):
    from treeroute.pipeline.run import Pipeline, PipelineRefusal
    from treeroute.runs import preflight

    notes = []
    fake = SimpleNamespace(machine=SimpleNamespace(temp_dir=str(tmp_path)), log=notes.append)
    monkeypatch.setattr(room, "release_memory", lambda: {"gc_collected": 0, "trimmed": True})
    seen = []

    def available():
        seen.append(1)
        return 100 if len(seen) < 3 else 10 ** 6         # short twice, then room
    monkeypatch.setattr(preflight, "available_ram_bytes", available)
    with pytest.raises(PipelineRefusal, match="G-DISK"):
        Pipeline._refuse_ram(fake, 1000, "a plan-time pre-flight")            # wait=False: refuses at once
    assert len(seen) == 1
    seen.clear()
    monkeypatch.setattr(K, "ROOM_POLL_SECONDS", 0)
    Pipeline._refuse_ram(fake, 1000, "an in-run check", wait=True)          # waits, then goes
    assert len(seen) == 3 and any("an in-run check is waiting for room" in n for n in notes)
    seen.clear()
    monkeypatch.setattr(preflight, "available_ram_bytes", lambda: 100)
    monkeypatch.setattr(K, "ROOM_MAX_WAIT_SECONDS", 0)
    with pytest.raises(PipelineRefusal, match="an in-run check needs about"):
        Pipeline._refuse_ram(fake, 1000, "an in-run check", wait=True)      # no room after the maximum wait
