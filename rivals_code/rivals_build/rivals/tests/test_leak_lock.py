"""T1 (no test-row read before the lock), T3 (score refusals), T13 (the heavy-job lock) on the toy runs
(SPEC_RIVALS.md 2.6, 3.6, 3.8, 3.10, 4.2).

Needs builders A and B. Flow A (conftest.table_flow) runs init / tune / lock under the read spy and tries refit,
score and the label opener before the lock; flow B (conftest.table_flow_b) is a second locked board used here
for the refusals that edit files (each edit is undone).
"""

import json
from pathlib import Path

import pytest

from rivals.tests import toy_runs as T


# ------------------------------------------------------------------------------------------ T1
def _no_leak(spy, export_root, decoded_only):
    assert spy.test_label_opens == [], "the engine's open_test_labels was called"
    bad = spy.test_file_reads(export_root, decoded_only=decoded_only)
    assert bad == [], "a test/ file was read: %s" % bad[:5]
    bad = spy.test_y_requests()
    assert bad == [], "a saved test_preds was read with y (or with every column): %s" % bad[:5]


def test_t1_the_table_export_reads_no_test_file_and_no_test_y(table_toy, table_export):
    """The export writes test/ files; it may hash its own bytes (a raw open), never decode one, never ask a saved
    test_preds for y. (Deviation from the spec's 'never opens a test/ file' for the export: see BUILD_NOTES R1.)"""
    _no_leak(table_export.spy, table_toy.export_root, decoded_only=True)
    reads = [c for c in table_export.spy.calls if Path(c[1]).name == "test_preds.parquet"]
    assert reads, "the spy saw no read of the saved test_preds (P6 reads its keys): is the spy blind?"


def test_t1_the_grid_export_reads_no_test_file_and_no_test_y(grid_toy):
    root = grid_toy.base / "t1"
    cfg = T.write_rivals_yaml(root / "rivals.yaml", grid_toy.machine_file, root / "_export",
                              grid_toy.export_ckpt_root, root / "_out", root / "_moved")
    with T.ReadSpy() as spy:
        T.export_run(grid_toy, [0, max(grid_toy.leads)], None, config=cfg)
    _no_leak(spy, root / "_export", decoded_only=True)


def test_t1_init_tune_lock_never_open_a_test_file(table_toy, table_flow):
    _no_leak(table_flow.spy_pre_lock, table_toy.export_root, decoded_only=False)
    assert table_flow.fit_calls_tune > 0, "tune fitted nothing"


def test_t1_refit_before_the_lock_refuses(table_flow):
    assert table_flow.pre_lock["refit"].startswith("refused"), table_flow.pre_lock["refit"]


def test_t1_refit_reads_no_test_y(table_toy, table_flow):
    """Refit reads test/ files (allowed after the lock) and the decline target column of the saved test_preds,
    never y (SPEC_RIVALS.md 3.7 step 3)."""
    spy = table_flow.spy_refit
    assert spy.test_label_opens == []
    assert spy.test_y_requests() == [], spy.test_y_requests()[:5]


def test_t1_the_lock_exists_before_any_test_label_record(table_flow):
    out = table_flow.out
    lock = out / "picks.json.lock.json"
    assert (out / "picks.json").is_file() and lock.is_file()
    doc = T.read_json(lock)
    assert doc["sha256"] == T.sha256_file(out / "picks.json")
    for L in table_flow.scored_leads:
        rec = out / ("test_labels_opened_rivals_lead_%d.json" % L)
        assert rec.is_file(), rec
        assert T.read_json(rec).get("picks_sha256") == doc["sha256"], "item B5: the record names the picks sha"
        assert rec.stat().st_mtime_ns >= lock.stat().st_mtime_ns


# ------------------------------------------------------------------------------------------ T3
def test_t3_score_and_the_label_opener_refuse_without_the_lock(table_flow):
    for step in ("score", "open_test_labels"):
        assert table_flow.pre_lock[step].startswith("refused"), "%s ran before the lock" % step


def test_t3_refusals_after_the_lock(table_toy, table_flow_b):
    """On flow B: a missing learner's preds refuses; an edited picks.json refuses refit and score (sha check);
    then, everything put back, score runs (the positive control)."""
    toy, out = table_toy, table_flow_b.out
    T.h_refit(toy, out, 0)
    learners = T.learners_of(out)
    preds = out / "lead_0" / ("preds_%s.parquet" % learners[0])
    assert preds.is_file(), preds
    moved = T.move_aside(preds, toy.moved_root)
    try:
        T.expect_refusal("prediction", T.h_score, toy, out, 0)
        T.expect_refusal("prediction", T.h_open_test_labels, toy, out, 0)
    finally:
        moved.replace(preds)
    picks = out / "picks.json"
    original = picks.read_bytes()
    try:
        picks.write_bytes(original + b"\n")
        T.expect_refusal("picks", T.h_score, toy, out, 0)
        T.expect_refusal("picks", T.h_refit, toy, out, 0)
        T.expect_refusal("picks", T.h_open_test_labels, toy, out, 0)
    finally:
        picks.write_bytes(original)
    assert not (out / "test_labels_opened_rivals_lead_0.json").exists(), "a refused score opened the test labels"
    T.h_score(toy, out, 0)
    assert (out / "test_labels_opened_rivals_lead_0.json").is_file()


# ------------------------------------------------------------------------------------------ T13
def _commands(toy, out, case_root):
    cfg = T.write_rivals_yaml(case_root / "rivals.yaml", toy.machine_file, case_root / "_export",
                              toy.export_ckpt_root, case_root / "_out", case_root / "_moved")
    lead0 = T.export_lead_dir(toy, 0)
    return [
        ("export", lambda: T.export_run(toy, [0], None, config=cfg)),
        ("export.main", lambda: T.export_main(toy, "0")),
        ("init", lambda: T.h_init(toy, lead0, case_root / "_out_init")),
        ("tune", lambda: T.h_tune(toy, out)),
        ("lock", lambda: T.h_lock(toy, out)),
        ("refit", lambda: T.h_refit(toy, out, 0)),
        ("score", lambda: T.h_score(toy, out, 0)),
        ("board", lambda: T.h_board(toy, out)),
    ]


def test_t13_a_held_heavy_job_lock_refuses_every_command(table_toy, table_export, table_flow_b):
    from treeroute.runs.preflight import HeavyJobLock

    toy = table_toy
    lock = HeavyJobLock(toy.temp_dir)
    lock.acquire()                                  # this live process holds it
    try:
        for name, cmd in _commands(toy, table_flow_b.out, toy.base / "t13_live"):
            T.expect_refusal("another heavy engine job", cmd)
    finally:
        lock.release()
    assert not (toy.base / "t13_live" / "_out_init").exists(), "init wrote while the lock was held"


def test_t13_a_stale_heavy_job_lock_refuses_with_the_engine_message(table_toy, table_export, table_flow_b):
    from treeroute.runs.preflight import HEAVY_LOCK_FILE

    toy = table_toy
    path = Path(toy.temp_dir) / HEAVY_LOCK_FILE
    assert not path.exists()
    path.write_text(json.dumps({"pid": 4, "pid_created_ms": 1}) + "\n", encoding="utf-8")   # no such process
    try:
        for name, cmd in _commands(toy, table_flow_b.out, toy.base / "t13_stale"):
            T.expect_refusal("stale heavy-job lock", cmd)
    finally:
        T.move_aside(path, toy.moved_root)          # never delete
    assert not path.exists()
