"""T7 (the Y2 extension rule with AC2, and the pick), T10 (the RF rows per tree; ruling Z2 removed the stride), T14 (the data rules that switch
the board's learners) on synthetic inputs (SPEC_RIVALS.md 3.2, 3.4, 3.5).

Pure hooks requested in BUILD_NOTES_tests.md items B4 (harness.pick_learner, trials_to_extend,
check_extension_prefix, pick_flags, board_learners) and B4 (models.rf_rows_per_tree, RF_RAM_BUDGET).
The out-of-core RF itself is tested in test_rf_out_of_core.py.
"""

import math

import numpy as np
import pytest

from rivals.tests import toy_runs as T

BASE = (100, 200, 400, 800)
EXT = (1200, 1600)


def _rows(trials):
    """trials: {trial_id: (link_order, grid_order, {checkpoint: mae})} -> the flat rows pick_learner reads."""
    out = []
    for tid, (lo, go, by_ck) in trials.items():
        for ck, mae in by_ck.items():
            out.append({"trial_id": tid, "link_order": lo, "grid_order": go, "checkpoint": ck, "inner_mae": mae})
    return out


def _h(name):
    return T.need(T.rivals_harness(), name, "B4")


# ------------------------------------------------------------------------------------------ T7
def test_t7_a_best_at_400_is_not_extended():
    # Y2 reading R-Y2 b (review 2026-10-20): the pick at 400 is not extended, but t2, whose OWN best is the 800
    # edge, is extended although it is not the pick (it may overtake the pick once extended).
    rows = _rows({"t1": (0, 0, {100: 5.0, 200: 4.0, 400: 3.0, 800: 3.5}),
                  "t2": (0, 1, {100: 5.0, 200: 4.5, 400: 4.2, 800: 4.1})})
    pick = _h("pick_learner")(rows)
    assert (pick["trial_id"], pick["checkpoint"]) == ("t1", 400)
    assert list(_h("trials_to_extend")(rows, pick)) == ["t2"]
    assert "edge_rounds_1600" not in list(_h("pick_flags")("lgbm", pick))


def test_t7_no_trial_with_its_own_best_below_800_is_extended():
    rows = _rows({"t1": (0, 0, {100: 5.0, 200: 4.0, 400: 3.0, 800: 3.5}),
                  "t2": (0, 1, {100: 5.0, 200: 4.5, 400: 4.0, 800: 4.1})})
    assert list(_h("trials_to_extend")(rows, _h("pick_learner")(rows))) == []


def test_t7_lower_edge_picks_are_flagged_and_never_extended():
    rows = _rows({"t1": (0, 0, {100: 1.0, 200: 2.0, 400: 3.0, 800: 4.0})})
    pick = _h("pick_learner")(rows)
    assert "edge_rounds_100" in list(_h("pick_flags")("hgb_l1", pick))       # staged: the first stage is the edge
    assert list(_h("pick_flags")("lgbm", pick)) == []                         # early-stopped: round 1 is the edge
    assert list(_h("trials_to_extend")(rows, pick)) == []
    rows = _rows({"ridge_identity": (0, 0, {0.1: 1.0, 1.0: 2.0, 1e6: 3.0})})
    assert "edge_alpha_0.1" in list(_h("pick_flags")("ridge", _h("pick_learner")(rows)))


def test_t7_a_pick_at_800_extends_only_that_learners_trials_whose_own_best_is_800():
    rows = _rows({"t1": (0, 0, {100: 5.0, 200: 4.0, 400: 3.0, 800: 2.0}),     # the pick, best 800
                  "t2": (0, 1, {100: 5.0, 200: 4.5, 400: 4.2, 800: 4.1}),     # own best 800, worse
                  "t3": (1, 0, {100: 5.0, 200: 2.5, 400: 2.6, 800: 2.7}),     # own best 200
                  "t4": (1, 1, {100: 6.0, 200: 5.0, 400: 4.0, 800: 4.0})})    # tie 400 = 800: own best is 400
    pick = _h("pick_learner")(rows)
    assert (pick["trial_id"], pick["checkpoint"]) == ("t1", 800)
    assert sorted(_h("trials_to_extend")(rows, pick)) == ["t1", "t2"]


def test_t7_a_pick_at_1600_is_flagged_and_never_extended_again():
    rows = _rows({"t1": (0, 0, {100: 5.0, 200: 4.0, 400: 3.0, 800: 2.0, 1200: 1.5, 1600: 1.0}),
                  "t2": (0, 1, {100: 5.0, 200: 4.5, 400: 4.2, 800: 4.1, 1200: 4.3, 1600: 4.4})})
    pick = _h("pick_learner")(rows)
    assert (pick["trial_id"], pick["checkpoint"]) == ("t1", 1600)
    assert "edge_rounds_1600" in list(_h("pick_flags")("lgbm", pick))
    assert list(_h("trials_to_extend")(rows, pick)) == []


def test_t7_a_checkpoint_mismatch_after_the_extension_refuses():
    rng = np.random.default_rng(0)                    # test data only
    base = {ck: rng.standard_normal(50) for ck in BASE}
    same = {ck: v.copy() for ck, v in base.items()}
    same.update({ck: rng.standard_normal(50) for ck in EXT})
    _h("check_extension_prefix")(base, same)          # equal 100-800: passes
    bad = {ck: v.copy() for ck, v in same.items()}
    bad[400][7] = np.nextafter(bad[400][7], np.inf)   # one ulp
    with pytest.raises(Exception):
        _h("check_extension_prefix")(base, bad)


def test_t7_ties_break_by_link_order_then_grid_order_then_the_smaller_checkpoint():
    rows = _rows({"a": (1, 0, {100: 2.0}), "b": (0, 1, {100: 2.0}), "c": (0, 0, {200: 2.0, 400: 2.0})})
    pick = _h("pick_learner")(rows)
    assert (pick["trial_id"], pick["checkpoint"]) == ("c", 200)
    rows = _rows({"a": (1, 0, {100: 2.0}), "b": (0, 1, {100: 2.0})})
    assert _h("pick_learner")(rows)["trial_id"] == "b"


def test_t7_ridge_at_the_alpha_edge_is_flagged():
    rows = _rows({"ridge_identity": (0, 0, {0.1: 5.0, 1e5: 3.0, 1e6: 2.0})})
    pick = _h("pick_learner")(rows)
    assert pick["checkpoint"] == 1e6
    assert "edge_alpha_1e6" in list(_h("pick_flags")("ridge", pick))
    assert list(_h("trials_to_extend")(rows, pick)) == []


def test_t7_ac2_only_a_trial_that_ran_to_the_cap_is_extended():
    """Ruling AC2 (amends Y2/Z3 b and AA2): an early-stopped trial is extended only when it ran to the 800 cap
    without a patience stop. t1 ran to the cap (best 790); t2 has its best in (400, 800] too (best 600) but stopped
    by patience at 650, so its extension would only repeat it: not extended; t3 stopped early with best 120."""
    rows = _rows({"t1": (0, 0, {100: 5.0, 200: 4.0, 400: 3.0, 790: 2.0, 800: 2.01}),
                  "t2": (0, 1, {100: 5.0, 200: 4.5, 400: 4.2, 600: 4.0}),
                  "t3": (0, 2, {100: 5.0, 120: 4.9})})
    pick = _h("pick_learner")(rows)
    cap = {"t1": True, "t2": False, "t3": False}
    assert list(_h("trials_to_extend")(rows, pick, ran_to_cap=cap)) == ["t1"]
    # without the cap records (the staged hgb_l1 reading) both last-stage trials would extend
    assert sorted(_h("trials_to_extend")(rows, pick)) == ["t1", "t2"]
    assert list(_h("trials_to_extend")(rows, pick, ran_to_cap=dict(cap, t1=False))) == []
    with pytest.raises(Exception):                    # every trial needs its cap record
        _h("trials_to_extend")(rows, pick, ran_to_cap={"t1": True})


# ------------------------------------------------------------------------------------------ T10 (rows per tree)
# (rows, columns) of the lead-0 refit set: SPEC_RIVALS.md 2.9 rows; columns = tree+history + context + 1 normal.
SIZES = {"pm25": (2_590_280, 122 + 2 + 1), "fire": (751_508, 131 + 2 + 1), "coral": (11_338, 63 + 5 + 1),
         "ndvi": (2_680_841, 498 + 9 + 1), "defo": (3_011_184, 308 + 0 + 1)}


def test_t10_every_rf_fit_sees_all_rows_and_each_tree_the_capped_sample():
    """Ruling Z2: no stride; every tree draws min(200,000, n_fit) rows; the RF budget is 4.5 GiB."""
    M = T.rivals_models()
    assert float(T.need(M, "RF_RAM_BUDGET", "B4")) == 4.5 * 2 ** 30
    assert not hasattr(M, "rf_stride") and not hasattr(M, "rf_max_samples")
    per_tree = T.need(M, "rf_rows_per_tree", "B4")
    for name, (r, c) in SIZES.items():
        assert per_tree(r) == min(200_000, r), name
    # one tree's sample fits the budget at every table size (the RF refuses otherwise)
    for name, (r, c) in SIZES.items():
        plan = M._rf_budget(r, c - 1, per_tree(r), 0, M.RF_RAM_BUDGET)
        assert plan["parent_budget"] >= per_tree(r) * (c * 4 + 8), name


# ------------------------------------------------------------------------------------------ T14 (data rules)
LINKS3 = ["identity", "log_c", "arcsine"]


def _board(*a, **kw):
    return tuple(T.need(T.rivals_harness(), "board_learners", "B4")(*a, **kw))


def test_t14_tweedie_is_switched_on_by_the_data_rule_only():
    assert _board(0.0, 0.40, LINKS3) == ("ridge", "rf", "lgbm", "lgbm_tweedie")
    assert _board(0.0, 0.20, LINKS3) == ("ridge", "rf", "lgbm", "lgbm_tweedie")      # >= 20 %
    assert _board(0.0, 0.1999, LINKS3) == ("ridge", "rf", "lgbm")
    assert _board(-1.0, 0.90, ["identity"]) == ("ridge", "rf", "lgbm")               # legal_min below 0
    assert _board(0.5, 0.90, LINKS3) == ("ridge", "rf", "lgbm")                      # legal_min above 0
    assert _board(0.0, 0.0, ["identity", "log_c"]) == ("ridge", "rf", "lgbm")


def test_t14_tweedie_without_a_log_c_link_refuses():
    T.expect_refusal("log_c", _board, 0.0, 0.5, ["identity", "arcsine"])


def test_t14_hgb_l1_only_on_request_and_no_xgboost():
    assert _board(0.0, 0.5, LINKS3, extra_learners=("hgb_l1",)) == (
        "ridge", "rf", "lgbm", "lgbm_tweedie", "hgb_l1")
    assert "hgb_l1" not in _board(0.0, 0.5, LINKS3)
    for b in (_board(0.0, 0.5, LINKS3, extra_learners=("hgb_l1",)), _board(-1.0, 0.0, ["identity"])):
        assert not [x for x in b if "xgb" in x]
    with pytest.raises(Exception):
        _board(0.0, 0.5, LINKS3, extra_learners=("xgboost",))
