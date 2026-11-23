"""T15 (the scoring path uses the engine's own functions and the run's band) and T16 (our safety net applied to the
rival) on the toy table run (SPEC_RIVALS.md 3.7, 3.8).

Hand computations here call the LIVE engine (report/metrics.py score_table, metric_by_key, _paired_contrast,
contrast_tag; layer/decide.py n2_eligible) on frames built from the saved files, then compare with the board.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from rivals.tests import toy_runs as T

KEYS = ["unit", "time", "lead"]


def _ours_column(toy, lead):
    if lead == 0:
        v = T.read_json(toy.run / "verdict.json")
        if v.get("declined"):
            return v.get("decline_target") or "arm__identity_trees_off_unweighted"
        return "arm__" + v["adopted"]
    return T.read_json(toy.run / "ladder" / ("lead_%d" % lead) / "lead.json")["test"]["adopted_column"]


def _fallback_column(toy):
    dc = T.read_json(toy.run / "decision_checks.json")
    base = dc.get("decline_baseline")
    return base["key"] if base else "arm__identity_trees_off_unweighted"


def _frame(toy, out, lead, learner):
    saved = T.read_parquet(toy.saved_test_preds(lead))          # y read here: after the lock and the score
    preds = T.read_parquet(Path(out) / ("lead_%d" % lead) / ("preds_%s.parquet" % learner))
    j = saved.merge(preds[KEYS + [c for c in preds.columns if c not in saved.columns]], on=KEYS, how="left",
                    validate="one_to_one")
    assert len(j) == len(saved) and j["arm__rival_%s" % learner].notna().all()
    return j


# ------------------------------------------------------------------------------------------ T15
def test_t15_the_board_equals_a_hand_computation_with_the_engines_functions(table_toy, table_flow):
    from treeroute.report import metrics as M

    toy, out = table_toy, table_flow.out
    verdict = T.read_json(toy.run / "verdict.json")
    band = float(verdict["band"])                                # the NOWCAST band at every lead
    tol = float(verdict["hit_tolerance"])
    floor = verdict.get("measurement_error_floor")
    for lead in table_flow.scored_leads:
        board = pd.read_csv(out / ("board_lead_%d.csv" % lead))
        for c in ("learner", "contrast", "tag", "band", "rival_mae", "ours_mae", "d_mean", "decides"):
            assert c in board.columns, "board_lead_%d.csv lacks %s (item B5)" % (lead, c)
        ours = _ours_column(toy, lead)
        for learner in T.learners_of(out):
            f = _frame(toy, out, lead, learner)
            rival = "arm__rival_%s" % learner
            cols = ["unit", "group", "y", "normal", "legal_min", "legal_max", rival, rival + "_raw", ours]
            sub = f[cols].copy()
            table = M.score_table(sub, ("group",), tol, floor, verdict["kind"])
            r_map = M.metric_by_key(table, rival, "mae", "group")
            o_map = M.metric_by_key(table, ours, "mae", "group")
            _, dv = M._paired_contrast(r_map, o_map, "rival minus ours")
            tag, jk = M.contrast_tag(dv, band)
            lab = np.isfinite(sub["y"].to_numpy(np.float64))
            y = sub["y"].to_numpy(np.float64)[lab]
            rows = board[(board["learner"] == learner) & (board["contrast"] == "guarded_vs_headline")]
            assert len(rows) == 1, (lead, learner)
            row = rows.iloc[0]
            assert bool(row["decides"]), "guarded vs headline decides (Q11 c)"
            assert row["tag"] == tag.value, (lead, learner, row["tag"], tag.value)
            assert float(row["band"]) == band
            assert abs(float(row["d_mean"]) - jk.mean) <= 1e-12
            assert abs(float(row["rival_mae"]) - M.mae(y, sub[rival].to_numpy(np.float64)[lab])) <= 1e-12
            assert abs(float(row["ours_mae"]) - M.mae(y, sub[ours].to_numpy(np.float64)[lab])) <= 1e-12
            raw = board[(board["learner"] == learner) & (board["contrast"] == "raw_vs_raw")]
            assert len(raw) == 1 and not bool(raw.iloc[0]["decides"])
            assert abs(float(raw.iloc[0]["rival_mae"]) - M.mae(y, sub[rival + "_raw"].to_numpy(np.float64)[lab])) <= 1e-12


def test_t15_the_scored_rows_are_the_saved_rows_in_the_saved_order(table_toy, table_flow):
    for lead in table_flow.scored_leads:
        saved = T.read_parquet(table_toy.saved_test_preds(lead), KEYS)
        for learner in T.learners_of(table_flow.out):
            preds = T.read_parquet(table_flow.out / ("lead_%d" % lead) / ("preds_%s.parquet" % learner))
            assert list(map(tuple, preds[KEYS].to_numpy())) == list(map(tuple, saved[KEYS].to_numpy())), \
                "preds_%s.parquet rows are not the saved rows in the saved order (lead %d)" % (learner, lead)


# ------------------------------------------------------------------------------------------ T16
def test_t16_the_guard_rule_on_synthetic_arrays():
    g = T.need(T.rivals_harness(), "apply_guard", "B4")
    y = np.array([1.0, 2.0, 3.0, 4.0])
    comp = np.array([1.5, 2.5, 3.5, 4.5])                      # MAE 0.5
    raw = np.array([10.0, 20.0])
    fb = np.array([7.0, 8.0])
    worse = np.array([0.0, 0.0, 0.0, 0.0])                     # MAE 2.5
    better = np.array([1.1, 2.1, 3.1, 4.1])                    # MAE 0.1
    tie = np.array([0.5, 1.5, 2.5, 3.5])                       # MAE 0.5: not strictly lower
    for pred, passed in ((worse, False), (better, True), (tie, False)):
        guarded, ok = g(pred, comp, y, raw, fb)
        assert bool(ok) is passed
        assert np.array_equal(np.asarray(guarded), raw if passed else fb)


def test_t16_every_lead_and_learner_follows_the_guard_it_saved(table_toy, table_flow):
    from treeroute.layer.decide import n2_eligible
    from treeroute.report.metrics import mae

    toy, out = table_toy, table_flow.out
    fb_col = _fallback_column(toy)
    inner = T.read_parquet(toy.run / "inner_preds.parquet")
    seen = {True: 0, False: 0}
    for lead in table_flow.scored_leads:
        saved = T.read_parquet(toy.saved_test_preds(lead), KEYS + [fb_col])
        for learner in T.learners_of(out):
            gf = T.read_parquet(out / ("lead_%d" % lead) / ("guard_%s.parquet" % learner))
            pcol = "arm__rival_%s" % learner                   # the clipped guard prediction
            for c in ("unit", "time", "y", pcol, "comparator"):
                assert c in gf.columns, "guard_%s.parquet lacks %s (item B5)" % (learner, c)
            passed = n2_eligible(mae(gf["y"].to_numpy(np.float64), gf[pcol].to_numpy(np.float64)),
                                 mae(gf["y"].to_numpy(np.float64), gf["comparator"].to_numpy(np.float64)))
            seen[bool(passed)] += 1
            if lead == 0 and fb_col.startswith("base__"):
                j = gf.merge(inner[["unit", "time", fb_col]], on=["unit", "time"], how="left", validate="one_to_one")
                assert np.array_equal(j["comparator"].to_numpy(np.float64), j[fb_col].to_numpy(np.float64)), \
                    "lead 0 comparator is not the saved decline baseline (ruling V1)"
            preds = T.read_parquet(out / ("lead_%d" % lead) / ("preds_%s.parquet" % learner))
            assert (preds["guard_passed"] == passed).all(), (lead, learner)
            j = preds.merge(saved, on=KEYS, how="left", validate="one_to_one")
            want = j["arm__rival_%s_raw" % learner] if passed else j[fb_col]
            assert np.array_equal(j["arm__rival_%s" % learner].to_numpy(np.float64), want.to_numpy(np.float64)), \
                (lead, learner, passed)
    assert seen[True] + seen[False] > 0


def test_t16_a_rival_forced_worse_takes_the_decline_target(table_toy, table_flow_b):
    """Flow B, lead 183 (a forecast lead: the guard is a new fit): every prediction is forced to the legal maximum,
    so every learner loses its guard and its guarded test column is the run's decline target."""
    toy, out = table_toy, table_flow_b.out
    lead = sorted(L for L in toy.leads if L > 0)[0]
    hi = toy.legal()[1]

    M = T.rivals_models()

    def worse(res):
        data = {name: {ck: {k: np.full(np.shape(v), hi, dtype=np.float64) for k, v in d.items()}
                       for ck, d in by_ck.items()} for name, by_ck in res.items()}
        if hasattr(M, "FitResult"):              # keep the fitted model and facts the harness saves
            return M.FitResult(data, model=getattr(res, "model", None), info=getattr(res, "info", {}))
        return data

    with T.counting_fit_predict(transform=worse) as box:
        T.h_refit(toy, out, lead)
    assert box["calls"] > 0
    fb_col = _fallback_column(toy)
    saved = T.read_parquet(toy.saved_test_preds(lead), KEYS + [fb_col])
    for learner in T.learners_of(out):
        preds = T.read_parquet(out / ("lead_%d" % lead) / ("preds_%s.parquet" % learner))
        assert not preds["guard_passed"].any(), learner
        j = preds.merge(saved, on=KEYS, how="left", validate="one_to_one")
        assert np.array_equal(j["arm__rival_%s" % learner].to_numpy(np.float64), j[fb_col].to_numpy(np.float64))
        assert (j["arm__rival_%s_raw" % learner] == hi).all()
