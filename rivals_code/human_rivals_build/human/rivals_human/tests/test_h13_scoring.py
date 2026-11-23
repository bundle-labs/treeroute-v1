"""T-H13 the scoring path (SPEC_HUMAN.txt 1.9; as SPECR T15): verdict, d and the jackknife of every human row equal a
hand computation with the LIVE engine's own functions (score_table, metric_by_key, _paired_contrast, contrast_tag,
VERDICT_WORDS) on the deciding rows (covered rows of groups with >= 10 covered rows); tiers decide as registered;
check_ours_against_run passes on the toy and refuses on a run copy whose score_pooled.csv was edited."""

import math

import numpy as np
import pandas as pd
import pytest

from rivals_human.tests import hooks as HK

KEYS3 = ["unit", "time", "lead"]


def _hand(h, out, lead, rid, contrast):
    from treeroute.report import metrics as M
    LY, H = HK.common_modules(h.config)
    run = h.h_run()
    headline, raw = run.ours(lead)
    saved = HK.saved_test(h, lead)
    p = HK.preds(out, lead, rid)
    j = saved.merge(p[KEYS3 + ["covered", "raw", "guarded"]], on=KEYS3, how="left", validate="one_to_one")
    cov = j["covered"].to_numpy(bool)
    fc = j.loc[cov].reset_index(drop=True)
    counts = fc.groupby("group").size()
    dec = sorted(counts.index[counts >= 10].astype(str))
    fd = fc[fc["group"].astype(str).isin(dec)].reset_index(drop=True)
    keep = [c for c in ("unit", "group", "time", "year", "lead", "issue", "y", "normal", "legal_min", "legal_max")
            if c in fd.columns]
    f = fd[keep].copy()
    rcol, ocol = ("guarded", headline) if contrast == "guarded_vs_headline" else ("raw", raw)
    f["arm__rival"] = fd[rcol].to_numpy(np.float64)
    f["arm__ours"] = fd[ocol].to_numpy(np.float64)
    gt = M.score_table(f, ("group",), run.tol, run.floor, run.kind)
    rmap = M.metric_by_key(gt, "arm__rival", "mae", "group")
    omap = M.metric_by_key(gt, "arm__ours", "mae", "group")
    groups, d = M._paired_contrast(rmap, omap, "hand")
    tag, jk = M.contrast_tag(d, run.band)
    ok = np.isfinite(f["y"].to_numpy(np.float64))                  # rows without a label are not scored (R34)
    return {"verdict": H.VERDICT_WORDS[tag.value], "tag": tag.value, "d_mean": jk.mean, "d_low": jk.low,
            "d_high": jk.high, "n_groups": jk.n_groups,
            "rival_mae": M.mae(f["y"].to_numpy()[ok], f["arm__rival"].to_numpy()[ok]),
            "ours_mae": M.mae(f["y"].to_numpy()[ok], f["arm__ours"].to_numpy()[ok])}


def _close(a, b):
    a, b = float(a), float(b)
    return (math.isnan(a) and math.isnan(b)) or a == b or abs(a - b) <= 1e-12 * max(1.0, abs(b))


@pytest.mark.parametrize("which", ["grid", "table"])
def test_h13_board_rows_equal_a_hand_computation(which, grid_flow, table_flow):
    flow_ = grid_flow if which == "grid" else table_flow; flow_.ok(*["score %d" % L for L in flow_.h.leads])
    flow = grid_flow if which == "grid" else table_flow
    h = flow.h
    checked = 0
    for L in h.leads:
        b = HK.board_lead(flow.out, L)
        hb = b[b["rival_type"] == "human"]
        for _, row in hb.iterrows():
            if row["contrast"] not in ("guarded_vs_headline", "raw_vs_raw") or str(row["verdict"]) in (
                    "NOT CALIBRATABLE", "CANNOT TELL"):
                continue
            want = _hand(h, flow.out, L, row["rival"], row["contrast"])
            for k in ("d_mean", "d_low", "d_high", "rival_mae"):
                assert _close(row[k], want[k]), (L, row["rival"], row["contrast"], k, row[k], want[k])
            assert _close(row["ours_mae_same_rows"], want["ours_mae"])
            assert row["verdict"] == want["verdict"] and row["tag"] == want["tag"]
            assert int(row["n_groups"]) == want["n_groups"]
            assert float(row["band"]) == float(h.h_run().band)
            checked += 1
    assert checked > 0


def test_h13_tiers_decide_as_registered(grid_flow, table_flow):
    grid_flow.ok(*["score %d" % L for L in grid_flow.h.leads]); table_flow.ok(*["score %d" % L for L in table_flow.h.leads])
    want = {"P": True, "L": True, "A": False, "X": False}
    for flow in (grid_flow, table_flow):
        for L in flow.h.leads:
            b = HK.board_lead(flow.out, L)
            for _, row in b[b["rival_type"] == "human"].iterrows():
                dec = str(row["decides"]).lower() == "true"
                if row["contrast"] == "guarded_vs_headline" and str(row["verdict"]) != "NOT CALIBRATABLE":
                    assert dec == want[row["tier"]], (L, row["rival"], row["tier"], row["decides"])
                elif row["contrast"] != "guarded_vs_headline":
                    assert not dec, (L, row["rival"], row["contrast"])
    g6 = HK.board_lead(grid_flow.out, 6)
    m = g6[(g6["rival"] == "toy_m") & (g6["contrast"] == "guarded_vs_headline")]
    assert len(m) == 1 and m["tier"].iloc[0] == "X" and "extension" in str(m["flags"].iloc[0])


def test_h13_ours_on_all_rows_equals_the_runs_score_pooled(grid_flow):
    grid_flow.ok("score 0")
    sp = pd.read_csv(grid_flow.h.run / "score_pooled.csv", float_precision="round_trip")
    LY, H = HK.common_modules(grid_flow.h.config)
    headline, _ = grid_flow.h.h_run().ours(0)
    want = float(sp[(sp["column"] == headline) & (sp["line"] == "pooled") & (sp["rows_basis"] == "all")]["mae"].iloc[0])
    chk = HK.read_json(grid_flow.out / "scores" / "lead_0_ours_check.json")
    assert chk["result"].startswith("pass")
    b = HK.board_lead(grid_flow.out, 0)
    vals = b[b["rival_type"] == "human"]["ours_mae_all_rows"].dropna().astype(float).unique()
    assert len(vals) == 1 and vals[0] == pytest.approx(want, rel=1e-12)


def test_h13_an_edited_ours_score_refuses(grid_flow):
    """A run copy whose score_pooled.csv says another MAE for our headline column: the human score refuses (the
    check of H:2416-2451 runs before any covered-rows table is written)."""
    from rivals.tests import toy_runs as T
    h = grid_flow.h
    LY, H = HK.common_modules(h.config)
    headline, _ = h.h_run().ours(0)
    dest = T.copy_run(h.toy, "edited_ours")
    sp = dest / "score_pooled.csv"
    t = pd.read_csv(sp, float_precision="round_trip")
    sel = (t["column"] == headline) & (t["line"] == "pooled") & (t["rows_basis"] == "all")
    t.loc[sel, "mae"] = t.loc[sel, "mae"] + 1.0
    HK.move_aside(sp, h.base / "_moved_by_tests")
    sp.write_text(t.to_csv(index=False, lineterminator="\n"), encoding="utf-8")
    v = HK.variant_config(h, "edited_ours")
    out = HK.init(v, run=dest)
    HK.tune(v, out)
    HK.lock(v, out)
    HK.refit(v, out, 0)
    HK.refs(v, out, 0)
    HK.refuses(("score_pooled", "pooled MAE", "differs"), HK.score, v, out, 0)
    assert not (out / "human_board_lead_0.csv").is_file()
