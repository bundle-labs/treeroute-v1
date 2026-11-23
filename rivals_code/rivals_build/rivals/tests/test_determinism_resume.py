"""T11 (determinism) and T12 (resume) of the tuning on the toy table run (SPEC_RIVALS.md 3.4, 3.6, 3.10).

Flow A and flow B (conftest) are two independent init / tune / lock runs on the same export: their trials.csv,
trial inner predictions and picks.json must be byte-equal (item B6: those files hold no wall-clock and no out path).
"""

from pathlib import Path

import pytest

from rivals.tests import toy_runs as T


def _tuning_files(out):
    out = Path(out)
    files = {"trials.csv": out / "trials.csv", "picks.json": out / "picks.json"}
    for f in T.trial_pred_files(out):
        files[str(f.relative_to(out))] = f
    return files


def _assert_same(a_out, b_out):
    a, b = _tuning_files(a_out), _tuning_files(b_out)
    assert sorted(a) == sorted(b), sorted(set(a) ^ set(b))[:10]
    assert len(a) > 2, "no trial predictions saved"
    diff = [k for k in sorted(a) if a[k].read_bytes() != b[k].read_bytes()]
    assert not diff, "not byte-equal: %s" % diff[:10]


def test_t11_two_tunings_are_byte_equal(table_flow, table_flow_b):
    _assert_same(table_flow.out, table_flow_b.out)
    assert table_flow.fit_calls_tune == table_flow_b.fit_calls_tune


def test_t11_every_board_learner_has_a_pick_and_a_complete_grid(table_toy, table_flow):
    picks = T.read_json(table_flow.out / "picks.json")
    learners = T.learners_of(table_flow.out)
    assert set(learners) == {"ridge", "rf", "lgbm", "lgbm_tweedie", "hgb_l1"}, learners   # toy: 40 % zeros, log_c
    blob = picks.get("picks", picks)
    for learner in learners:
        assert learner in blob, "picks.json has no pick for %s" % learner
        assert (table_flow.out / "trials" / learner).is_dir()


def test_t12_an_interrupted_tuning_resumes_and_ends_byte_equal(table_toy, table_export, table_flow):
    k = 3
    out_root = table_toy.base / "_out_c"
    with T.counting_fit_predict(stop_after=k) as box:
        out = T.h_init(table_toy, table_export.dirs[0], out_root, ("hgb_l1",))
        with pytest.raises(box["Interrupted"]):
            T.h_tune(table_toy, out)
        assert box["calls"] == k
    done_before = sorted(p for p in (out / "trials").glob("*/*/trial.json"))
    assert len(done_before) >= 1, "no finished trial was saved before the interrupt"
    with T.counting_fit_predict() as box2:
        T.h_tune(table_toy, out, resume=True)
    assert box2["calls"] == table_flow.fit_calls_tune - k, (
        "resume refitted %d trials; %d were finished" % (box2["calls"], k))
    T.h_lock(table_toy, out)
    _assert_same(table_flow.out, out)
