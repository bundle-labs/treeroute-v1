"""T-H11 guard (N2) and T-H12 coverage (SPEC_HUMAN.txt 1.9; Q2.HQ3 a, Q2.HQ9, Q12 b).

T-H11: on the covered guard rows, a rival worse than its comparator (MAE not strictly lower; n2_eligible) gets the
run's decline target on its covered test rows, a better one keeps raw; a score_without_net lead keeps raw with the
flag "no safety net"; the guard file's labels and comparator equal the run's inner_preds / guard_preds byte for
byte. T-H12: groups with < 10 covered test rows leave the deciding contrast; ours is scored on the same rows; the
filled line equals the decline target on uncovered rows; the coverage mask is label-free (it equals the index's
finite x on the saved test rows, written at the lock).
"""

import numpy as np
import pandas as pd
import pytest

from rivals_human.tests import hooks as HK

KEYS3 = ["unit", "time", "lead"]


def _decline_col(h):
    LY, H = HK.common_modules(h.config)
    return h.h_run().decline_target


def _done(out, lead, rid):
    return HK.read_json(HK.lead_dir(out, lead) / ("done_%s.json" % rid))


def _rows(flow, lead):
    """(rival id, done record) of every refit rival at the lead."""
    out = []
    for p in sorted(HK.lead_dir(flow.out, lead).glob("done_*.json")):
        rec = HK.read_json(p)
        if rec.get("status") == "ok":
            out.append((rec["rival"], rec))
    return out


# ------------------------------------------------------------------------------------------ T-H11
@pytest.mark.parametrize("which", ["grid", "table"])
def test_h11_guarded_is_raw_when_passed_else_the_decline_target(which, grid_flow, table_flow):
    flow_ = grid_flow if which == "grid" else table_flow; flow_.ok(*["refit %d" % L for L in flow_.h.leads])
    flow = grid_flow if which == "grid" else table_flow
    h = flow.h
    from treeroute.layer.decide import n2_eligible
    from treeroute.report.metrics import mae
    seen_pass = seen_fail = 0
    for L in h.leads:
        fb_col = _decline_col(h)
        saved = HK.saved_test(h, L, KEYS3 + [fb_col])
        for rid, done in _rows(flow, L):
            g = HK.guard_file(flow.out, L, rid)
            passed = bool(n2_eligible(mae(g["y"].to_numpy(), g["pred"].to_numpy()),
                                      mae(g["y"].to_numpy(), g["comparator"].to_numpy())))
            assert passed == bool(done["guard"]["passed"]), (rid, L)
            p = HK.preds(flow.out, L, rid)
            j = saved.merge(p, on=KEYS3, how="left", validate="one_to_one")
            cov = j["covered"].to_numpy(bool)
            raw, guarded = j["raw"].to_numpy(np.float64), j["guarded"].to_numpy(np.float64)
            if done["guard"]["score_without_net"]:
                assert np.array_equal(guarded[cov], raw[cov])
                continue
            want = raw[cov] if passed else j[fb_col].to_numpy(np.float64)[cov]
            assert guarded[cov].tobytes() == want.tobytes(), (rid, L, passed)
            assert np.isnan(guarded[~cov]).all()
            seen_pass += passed
            seen_fail += not passed
    assert seen_pass + seen_fail > 0


def test_h11_raw_is_the_engine_clip_of_pre(grid_flow):
    grid_flow.ok(*["refit %d" % L for L in grid_flow.h.leads])
    from treeroute.layer.links import clip_to_legal
    legal = tuple(grid_flow.h.h_run().legal)
    for L in grid_flow.h.leads:
        for rid, _ in _rows(grid_flow, L):
            p = HK.preds(grid_flow.out, L, rid)
            cov = p["covered"].to_numpy(bool)
            want, _, _ = clip_to_legal(p["pre"].to_numpy(np.float64)[cov], legal, allow_nan=False)
            assert p["raw"].to_numpy(np.float64)[cov].tobytes() == np.asarray(want, np.float64).tobytes(), (rid, L)


def test_h11_score_without_net_keeps_raw_and_says_so(table_flow):
    table_flow.ok("refit 183", "refit 365", "score 365")
    done = _done(table_flow.out, 365, "toy_outlook")
    assert done["guard"]["score_without_net"] is True
    p = HK.preds(table_flow.out, 365, "toy_outlook")
    cov = p["covered"].to_numpy(bool)
    assert p["no_safety_net"].all()
    assert np.array_equal(p["guarded"].to_numpy()[cov], p["raw"].to_numpy()[cov])
    b = HK.board_lead(table_flow.out, 365)
    row = b[(b["rival"] == "toy_outlook") & (b["contrast"] == "guarded_vs_headline")]
    assert len(row) == 1 and "no safety net" in str(row["flags"].iloc[0])
    assert not bool(row["decides"].iloc[0])                 # tier A never decides
    d183 = _done(table_flow.out, 183, "toy_outlook")
    assert d183["guard"]["score_without_net"] is False


def test_h11_guard_labels_and_comparator_equal_the_runs_saved_files(grid_flow):
    grid_flow.ok(*["refit %d" % L for L in grid_flow.h.leads])
    run_dir = grid_flow.h.run
    picks = HK.picks(grid_flow.out)["picks"]
    for L in grid_flow.h.leads:
        for rid, done in _rows(grid_flow, L):
            g = HK.guard_file(grid_flow.out, L, rid)
            link = picks[rid].get("link") or "identity"
            if L == 0:
                col = "%s_trees_off_unweighted" % link
                saved = HK.read_parquet(run_dir / "inner_preds.parquet", ["unit", "time", "y", col])
                j = g.merge(saved, on=["unit", "time"], how="left", suffixes=("", "_run"), validate="one_to_one")
            else:
                col = "arm__%s_trees_off_unweighted" % link
                saved = HK.read_parquet(run_dir / "ladder" / ("lead_%d" % L) / "guard_preds.parquet",
                                        ["unit", "time", "issue", "y", col])
                j = g.merge(saved, on=["unit", "time", "issue"], how="left", suffixes=("", "_run"),
                            validate="one_to_one")
            assert j["y"].to_numpy(np.float64).tobytes() == j["y_run"].to_numpy(np.float64).tobytes(), (rid, L)
            assert j["comparator"].to_numpy(np.float64).tobytes() == j[col].to_numpy(np.float64).tobytes(), (rid, L)


# ------------------------------------------------------------------------------------------ T-H12
def test_h12_groups_with_fewer_than_10_covered_rows_leave_the_contrast(grid_flow):
    grid_flow.ok("refit 0", "score 0")
    from treeroute.report.metrics import mae
    h = grid_flow.h
    LY, H = HK.common_modules(h.config)
    headline, _ = h.h_run().ours(0)
    saved = HK.saved_test(h, 0, KEYS3 + ["group", "y", headline])
    for rid in ("toy_idx", "toy_lag1"):
        p = HK.preds(grid_flow.out, 0, rid)
        j = saved.merge(p.drop(columns=["group"]), on=KEYS3, how="left", validate="one_to_one")
        cov = j["covered"].to_numpy(bool)
        counts = j.loc[cov].groupby("group").size()
        dec = sorted(counts.index[counts >= 10].astype(str))
        assert "grp_c" not in dec and 0 < int(counts.get("grp_c", 0)) < 10, counts.to_dict()
        b = HK.board_lead(grid_flow.out, 0)
        row = b[(b["rival"] == rid) & (b["contrast"] == "guarded_vs_headline")].iloc[0]
        fd = j[cov & j["group"].astype(str).isin(dec).to_numpy()]
        assert int(row["groups"]) == len(dec) and int(row["groups_total"]) == saved["group"].nunique()
        assert int(row["rows"]) == len(fd) and int(row["rows_covered"]) == int(cov.sum())
        assert int(row["rows_total"]) == len(saved)
        ok = np.isfinite(fd["y"].to_numpy(np.float64))          # rows without a label are not scored (R34)
        assert float(row["ours_mae_same_rows"]) == mae(fd["y"].to_numpy()[ok], fd[headline].to_numpy()[ok])
        assert float(row["rival_mae"]) == mae(fd["y"].to_numpy()[ok], fd["guarded"].to_numpy()[ok])


def test_h12_the_filled_line_takes_the_decline_target_on_uncovered_rows(grid_flow):
    grid_flow.ok("refit 0", "score 0")
    from treeroute.report.metrics import mae
    h = grid_flow.h
    fb = _decline_col(h)
    saved = HK.saved_test(h, 0, KEYS3 + ["y", fb])
    p = HK.preds(grid_flow.out, 0, "toy_idx")
    j = saved.merge(p, on=KEYS3, how="left", validate="one_to_one")
    cov = j["covered"].to_numpy(bool)
    assert (~cov).any()
    filled = j["filled"].to_numpy(np.float64)
    assert filled[~cov].tobytes() == j[fb].to_numpy(np.float64)[~cov].tobytes()
    assert filled[cov].tobytes() == j["guarded"].to_numpy(np.float64)[cov].tobytes()
    b = HK.board_lead(grid_flow.out, 0)
    row = b[(b["rival"] == "toy_idx") & (b["contrast"] == "guarded_vs_headline")].iloc[0]
    ok = np.isfinite(j["y"].to_numpy(np.float64))
    assert float(row["filled_mae_all_rows"]) == mae(j["y"].to_numpy()[ok], filled[ok])


def test_h12_the_coverage_mask_is_label_free(grid_flow):
    """The locked mask equals the finite picked stat of the index on the saved test rows; it was written at the
    lock (its sha is in human_picks.json) before any label was opened."""
    h = grid_flow.h
    doc = HK.picks(grid_flow.out)
    p = doc["picks"]["toy_idx"]
    cov = HK.read_parquet(grid_flow.out / p["leads"]["0"]["coverage"]["file"])
    idx = HK.read_parquet(HK.index_table(h, "toy_idx", 0, "all"))
    j = cov.merge(idx[["unit", "time", "issue", "lead", p["stat"]]], on=["unit", "time", "issue", "lead"],
                  how="left", validate="one_to_one")
    assert np.array_equal(j["covered"].to_numpy(bool), np.isfinite(j[p["stat"]].to_numpy(np.float64)))
    assert "y" not in cov.columns
    assert HK.sha256_file(grid_flow.out / p["leads"]["0"]["coverage"]["file"]) == p["coverage_sha256"]["0"]
