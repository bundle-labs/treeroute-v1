"""T-H10 lock before test (SPEC_HUMAN.txt 1.11; PROT H8, H16; the design of H:1907-2012 on the human files):
the lock is write-once; an edited human_picks.json refuses every later command; a test-side trace before the lock
refuses the lock; a ledger showing test labels opened under other picks refuses the lock; score refuses without a
lock; a picks file without its lock (a killed lock) is moved aside and the lock redone."""

import json

import pytest

from rivals_human.tests import hooks as HK


def _board(grid_flow, name):
    """A fresh board (own out root, the same slim and index tables as the main grid flow), init and tune only."""
    v = HK.variant_config(grid_flow.h, name)
    out = HK.init(v)
    HK.tune(v, out)
    return v, out


def test_h10_lock_is_write_once(grid_flow):
    v, out = _board(grid_flow, "write_once")
    HK.lock(v, out)
    HK.refuses(("already locked", "written once"), HK.lock, v, out)
    HK.refuses(("locked", "never runs again"), HK.tune, v, out)
    # the scored main board: a second lock refuses too (its test-side traces are named first)
    HK.refuses(("already locked", "test-side"), HK.lock, grid_flow.h, grid_flow.out)
    tok = HK.verify_lock(grid_flow.out)
    assert tok.picks_sha256 == HK.sha256_file(grid_flow.out / "human_picks.json")


def test_h10_an_edited_picks_file_refuses_every_later_command(grid_flow):
    v, out = _board(grid_flow, "edited_picks")
    HK.lock(v, out)
    pp = out / "human_picks.json"
    doc = HK.read_json(pp)
    rid = sorted(r for r, p in doc["picks"].items() if p.get("status") == "ok")[0]
    doc["picks"][rid]["pick_mae"] = 0.0
    HK.move_aside(pp, v.base / "_moved_by_tests")
    pp.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    HK.refuses(("changed after the lock", "lock"), HK.refit, v, out, 0)
    HK.refuses(("changed after the lock", "lock"), HK.score, v, out, 0)
    HK.refuses(("changed after the lock", "lock"), HK.verify_lock, out)


def test_h10_a_test_side_trace_before_the_lock_refuses_it(grid_flow):
    v, out = _board(grid_flow, "trace")
    trace = HK.lead_dir(out, 0) / "preds_toy_idx.parquet"
    trace.parent.mkdir(parents=True, exist_ok=True)
    trace.write_bytes(b"not a parquet: any trace counts")
    HK.refuses(("test-side", "trace"), HK.lock, v, out)
    HK.refuses(("not locked", "lock"), HK.score, v, out, 0)


def test_h10_a_ledger_with_other_picks_refuses_the_lock(grid_flow):
    v, out = _board(grid_flow, "ledger")
    fp = v.h_run().fingerprint
    lp = HK.ledger_path(out, fp)
    lp.parent.mkdir(parents=True, exist_ok=True)
    with open(str(lp), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"event": "test_labels_opened", "lead": 0, "picks_sha256": "e" * 64,
                             "picks_content_sha256": "f" * 64, "utc": "2026-10-21T00:00:00Z",
                             "board": "another board"}) + "\n")
    HK.refuses(("other picks", "ledger"), HK.lock, v, out)


def test_h10_score_refuses_without_a_lock(grid_flow):
    assert grid_flow.pre_lock["score"].startswith("refused:")
    assert "lock" in grid_flow.pre_lock["score"].lower()


def test_h10_a_picks_file_without_its_lock_is_moved_aside_and_the_lock_redone(grid_flow):
    v, out = _board(grid_flow, "relock")
    (out / "human_picks.json").write_text('{"half": "written"}\n', encoding="utf-8")
    HK.lock(v, out)
    HK.verify_lock(out)
    moved = list((v.roots["moved_root"]).rglob("human_picks.json"))
    assert moved, "the killed-lock picks file was not moved aside under moved_root"


def test_h10_the_lock_records_picks_coverage_and_hashes(grid_flow):
    grid_flow.ok("score 6")
    doc = HK.picks(grid_flow.out)
    assert doc["run_fingerprint"] == grid_flow.h.h_run().fingerprint
    assert doc["common_harness_sha256"] == HK.COMMON_SHA
    for rid, p in doc["picks"].items():
        if p.get("status") != "ok":
            continue
        for L, lrec in p["leads"].items():
            if lrec["tier"] == "none":
                continue
            cov = grid_flow.out / lrec["coverage"]["file"]
            assert HK.sha256_file(cov) == lrec["coverage"]["sha256"] == p["coverage_sha256"][L]
            assert "t1_rule" in lrec["timing"]
    ledger = HK.ledger_path(grid_flow.out, doc["run_fingerprint"])
    events = [json.loads(x)["event"] for x in ledger.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert "locked" in events and "test_labels_opened" in events
    assert events.index("locked") < events.index("test_labels_opened")
