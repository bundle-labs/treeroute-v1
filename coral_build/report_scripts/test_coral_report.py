"""Tests for coral_report.py on SYNTHETIC data only: hand-computed numbers for the pure functions, and the engine's
toy table runs (built by build_toy_runs.py under toy_runs/) for the whole script. No real-data run is read: the toy
runs are smokes, so every call passes --toy (or toy=True), which admits only the synthetic package 'toy_table'.

    py -3.9 -m pytest -q test_coral_report.py -p no:cacheprovider
"""

import json
import math
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import coral_report as CR  # noqa: E402

TOY = HERE / "toy_runs"
VARIANTS = ("ok", "donor_only_group")


# ============================================================================== hand-computed, pure functions
def test_magnitude_bins_are_right_closed_by_hand():
    e = {"pos_q25": 10.0, "pos_q50": 20.0, "pos_q75": 30.0}
    y = np.array([0.0, 5.0, 10.0, 10.5, 20.0, 25.0, 30.0, 31.0, 100.0])
    want = ["B0 zero", "B1 (0, q25]", "B1 (0, q25]", "B2 (q25, q50]", "B2 (q25, q50]", "B3 (q50, q75]",
            "B3 (q50, q75]", "B4 (q75, max]", "B4 (q75, max]"]
    assert CR.magnitude_bin(y, e).tolist() == want


def _frame():
    # y, an arm, predict-zero and a donor median of 10, two groups
    return pd.DataFrame({"y": [0.0, 10.0, 20.0, 50.0], "group": ["a", "a", "b", "b"], "src": ["x", "x", "y", "y"],
                         "arm__m": [5.0, 5.0, 5.0, 5.0], "base__predict_zero": [0.0] * 4,
                         "base__donor_median": [10.0] * 4})


def test_line_prints_predict_zero_and_the_donor_median_beside_by_hand():
    r = CR.line(_frame(), "arm__m", tol=5.0)
    # |y - p| = 5, 5, 15, 45 -> 70 / 4
    assert r["mae"] == pytest.approx(17.5)
    # predict-zero: |y| = 0, 10, 20, 50 -> 80 / 4
    assert r["mae_predict_zero"] == pytest.approx(20.0)
    # donor median 10: 10, 0, 10, 40 -> 60 / 4
    assert r["mae_donor_median"] == pytest.approx(15.0)
    assert r["gain_vs_predict_zero"] == pytest.approx(2.5) and r["gain_vs_donor_median"] == pytest.approx(-2.5)
    assert r["hit"] == pytest.approx(0.5)                    # 5 and 5 are within the tolerance 5 (inclusive)
    assert r["calibration_ratio"] == pytest.approx(5.0 / 20.0)
    assert r["zero_share"] == pytest.approx(0.25) and r["n"] == 4 and r["n_groups"] == 2
    assert math.isnan(r["corr2"])                             # a constant prediction has no correlation


def test_line_uses_only_rows_with_a_finite_prediction_and_scores_the_baselines_on_them():
    f = _frame()
    f.loc[3, "arm__m"] = np.nan                               # e.g. persistence without a previous label
    r = CR.line(f, "arm__m", tol=5.0)
    assert r["n"] == 3
    assert r["mae"] == pytest.approx((5 + 5 + 15) / 3.0)
    assert r["mae_predict_zero"] == pytest.approx((0 + 10 + 20) / 3.0)
    assert r["mae_donor_median"] == pytest.approx((10 + 0 + 10) / 3.0)


class _FakeRun:
    """Just what flattening_table needs: one lead, its rows, the stratum, the adopted column."""

    def __init__(self, frame):
        self.leads = [0]
        self.preds = {0: frame}
        self.adopted = {0: "arm__m"}
        self.stratum = "src"
        self.tol = {0: 5.0}

    def frame(self, L, basis, common):
        return self.preds[L].reset_index(drop=True)


def test_flattening_guard_by_hand():
    f = pd.DataFrame({"y": [0.0, 0.0, 10.0, 40.0, 60.0, 80.0], "group": list("aabbcc"), "src": ["x"] * 6,
                      "arm__m": [1.0, 2.0, 8.0, 30.0, 40.0, 50.0], "base__predict_zero": [0.0] * 6,
                      "base__donor_median": [5.0] * 6})
    edges = {0: {CR.EDGE_PRIMARY: 40.0, CR.EDGE_POSITIVE: 70.0}}
    t = CR.flattening_table(_FakeRun(f), set(), ["x"], edges)
    t = t[(t["rows_basis"] == "all") & (t["stratum_value"] == CR.ALL)].set_index(["edge_rule", "column"])
    # primary edge 40: rows 40, 60, 80 (at or above), observed mean 60
    arm = t.loc[(CR.EDGE_PRIMARY, "arm__m")]
    assert arm["n"] == 3 and arm["observed_mean"] == pytest.approx(60.0)
    assert arm["mean_pred"] == pytest.approx(40.0) and arm["mean_pred_minus_observed"] == pytest.approx(-20.0)
    assert arm["ratio_pred_to_observed"] == pytest.approx(40.0 / 60.0)
    assert t.loc[(CR.EDGE_PRIMARY, "base__predict_zero")]["mean_pred"] == pytest.approx(0.0)
    assert t.loc[(CR.EDGE_PRIMARY, "base__donor_median")]["mean_pred"] == pytest.approx(5.0)
    # beside edge 70: row 80 only
    arm2 = t.loc[(CR.EDGE_POSITIVE, "arm__m")]
    assert arm2["n"] == 1 and arm2["observed_mean"] == pytest.approx(80.0) and arm2["mean_pred"] == pytest.approx(50.0)


def test_d74_tag_by_hand():
    tag, jk = CR.d74_tag(np.array([1.0, 2.0, 3.0]), band=0.5, declined=False)
    # leave-one-out means 2.5, 2, 1.5; SE = sqrt(2/3 * 0.5) = sqrt(1/3)
    assert jk["mean"] == pytest.approx(2.0) and jk["se"] == pytest.approx(math.sqrt(1.0 / 3.0))
    assert jk["low"] == pytest.approx(2.0 - 1.96 * math.sqrt(1.0 / 3.0)) and tag == "helps"
    assert CR.d74_tag(np.zeros(3), 0.5, False)[0] == "identical"
    assert CR.d74_tag(np.array([1.0, 2.0]), 0.5, False)[0] == "cannot_tell"
    assert CR.d74_tag(np.array([-1.0, -2.0, -3.0]), 0.5, False)[0] == "hurts"
    assert CR.d74_tag(np.array([0.01, -0.01, 0.02]), 0.5, False)[0] == "equivalent"
    assert CR.d74_tag(np.array([1.0, 2.0, 3.0]), 0.5, True)[0] == "declined"
    assert CR.d74_tag(np.array([1.0, 2.0, 3.0]), None, False)[0] == "no band (R35)"


# ============================================================================== the engine's toy runs
def _toy(variant):
    rf = TOY / variant / "RUN_FOLDER.txt"
    if not rf.is_file():
        pytest.skip("toy run %s not built: run build_toy_runs.py first" % variant)
    return Path(rf.read_text(encoding="utf-8").strip()), TOY / variant / "pk" / "toy_table"


@pytest.fixture(scope="module", params=VARIANTS)
def toy(request, tmp_path_factory):
    run, pkg = _toy(request.param)
    out = tmp_path_factory.mktemp("report_%s" % request.param) / "out"
    roots = tmp_path_factory.mktemp("roots") / "protected_roots.txt"
    roots.write_text("# none\n", encoding="utf-8")
    assert CR.main([str(run), "--package", str(pkg), "--out", str(out), "--protected-roots", str(roots), "--toy"]) == 0
    csv = {p.stem: pd.read_csv(p) for p in out.glob("*.csv")}
    return {"variant": request.param, "run": run, "pkg": pkg, "out": out, "csv": csv}


def _preds(run, L):
    return pd.read_parquet(run / ("test_preds.parquet" if L == 0 else "ladder/lead_%d/test_preds.parquet" % L))


def _donor_y(run, pkg, L):
    """Independent rebuild of the donor rows' labels (bank ids, fit cut, finite label)."""
    d = json.loads((run / "derived.json").read_text(encoding="utf-8"))
    bank = {u for v in d["R18:units"]["value"]["bank"].values() for u in v}
    cut = d["R11"]["value"][str(L)]["fit_cut"]
    t = pd.read_parquet(pkg / "data" / ("lead_%d.parquet" % L))
    day = np.array([x.toordinal() for x in t["visit_date"]])
    sel = t["row_id"].isin(bank).to_numpy() & (day <= cut) & np.isfinite(t["y"].to_numpy())
    return t.loc[sel, "y"].to_numpy(dtype=float)


def test_every_output_is_written_and_hashed(toy):
    names = {"per_programme", "programme_verdicts", "magnitude_edges", "magnitude_bins", "flattening_guard",
             "per_year_macro", "per_ecoregion", "counts_no_tree", "counts_pool_fallback", "counts_left_out",
             "guard_reference", "r30_missing", "pools_month_precision", "penalty_edge_picks",
             "programme_blocked_jackknife"}
    assert names <= set(toy["csv"])
    man = json.loads((toy["out"] / "inputs_manifest.json").read_text(encoding="utf-8"))
    assert man["script_sha256"] == CR.sha256_file(Path(CR.__file__))
    assert any(k.endswith("test_preds.parquet") for k in man["inputs_sha256"])
    md = (toy["out"] / "coral_report.md").read_text(encoding="utf-8")
    assert "NOT HEADLINE" in md and "given a survey on this date" in md and "not a headline" in md


def test_magnitude_edges_and_bins_against_an_independent_count(toy):
    run, pkg = toy["run"], toy["pkg"]
    edges = toy["csv"]["magnitude_edges"].set_index("lead")
    mb = toy["csv"]["magnitude_bins"]
    for L in (0, 183, 365):
        y = _donor_y(run, pkg, L)
        q = np.quantile(y[y > 0], [0.25, 0.5, 0.75])
        assert edges.loc[L, "donor_rows"] == y.size == edges.loc[L, "donor_rows_engine"]
        assert edges.loc[L, "donor_median"] == pytest.approx(np.median(y))
        assert [edges.loc[L, c] for c in ("pos_q25", "pos_q50", "pos_q75")] == pytest.approx(list(q))
        assert edges.loc[L, CR.EDGE_PRIMARY] == pytest.approx(np.quantile(y, 0.75))
        p = _preds(run, L)
        ty = p["y"].to_numpy(float)
        cut = pd.cut(ty, [-np.inf, 0.0, q[0], q[1], q[2], np.inf], right=True, labels=CR.BIN_ORDER)
        for col in [c for c in p.columns if c.startswith(CR.PRED_PREFIXES)]:
            got = mb[(mb["lead"] == L) & (mb["rows_basis"] == "all") & (mb["stratum_value"] == CR.ALL) &
                     (mb["column"] == col)].set_index("bin")
            for b in CR.BIN_ORDER:
                m = (np.asarray(cut) == b) & np.isfinite(p[col].to_numpy(float))
                assert got.loc[b, "n"] == int(m.sum()), (L, col, b)
                if m.any():
                    assert got.loc[b, "mae"] == pytest.approx(np.mean(np.abs(ty[m] - p[col].to_numpy(float)[m])))
                    assert got.loc[b, "mae_predict_zero"] == pytest.approx(np.mean(np.abs(ty[m])))


def test_flattening_guard_against_an_independent_mean(toy):
    run, pkg = toy["run"], toy["pkg"]
    fg = toy["csv"]["flattening_guard"]
    for L in (0, 183, 365):
        y = _donor_y(run, pkg, L)
        p = _preds(run, L)
        ty = p["y"].to_numpy(float)
        for rule, edge in ((CR.EDGE_PRIMARY, np.quantile(y, 0.75)), (CR.EDGE_POSITIVE, np.quantile(y[y > 0], 0.75))):
            sev = ty >= edge
            assert sev.any()
            for col in [c for c in p.columns if c.startswith(CR.PRED_PREFIXES)]:
                pv = p[col].to_numpy(float)
                m = sev & np.isfinite(pv)
                got = fg[(fg["lead"] == L) & (fg["rows_basis"] == "all") & (fg["edge_rule"] == rule) &
                         (fg["stratum_value"] == CR.ALL) & (fg["column"] == col)].iloc[0]
                assert got["edge"] == pytest.approx(edge) and got["n"] == int(m.sum())
                if m.any():
                    assert got["observed_mean"] == pytest.approx(ty[m].mean())
                    assert got["mean_pred"] == pytest.approx(pv[m].mean())


def test_predict_zero_is_beside_every_mae_and_equals_mean_absolute_label(toy):
    run = toy["run"]
    pp = toy["csv"]["per_programme"]
    full = pp[~pp["n_only"].astype(bool) & (pp["n"] > 0)]
    assert full["mae_predict_zero"].notna().all() and full["mae_donor_median"].notna().all()
    for L in (0, 183, 365):
        p = _preds(run, L)
        assert (p["base__predict_zero"] == 0).all()
        ty = p["y"].to_numpy(float)
        for col in [c for c in p.columns if c.startswith(CR.PRED_PREFIXES)]:
            m = np.isfinite(ty) & np.isfinite(p[col].to_numpy(float))
            got = pp[(pp["lead"] == L) & (pp["rows_basis"] == "all") & (pp["stratum_value"] == CR.ALL) &
                     (pp["column"] == col)].iloc[0]
            assert got["mae_predict_zero"] == pytest.approx(np.mean(np.abs(ty[m])))
            assert got["mae_donor_median"] == pytest.approx(
                np.mean(np.abs(ty[m] - p["base__donor_median"].to_numpy(float)[m])))
        own = pp[(pp["lead"] == L) & (pp["column"] == "base__predict_zero")]
        assert np.allclose(own["mae"], own["mae_predict_zero"], equal_nan=True)


def test_per_programme_and_per_year_equal_the_engine_tables_at_the_nowcast(toy):
    run = toy["run"]
    pp = toy["csv"]["per_programme"]
    eng = pd.read_csv(run / "per_stratum.csv")
    eng = eng[(eng["line"] == "key") & (eng["rows_basis"] == "all")]
    for _, e in eng.iterrows():
        got = pp[(pp["lead"] == 0) & (pp["rows_basis"] == "all") & (pp["stratum_value"] == e["stratum"]) &
                 (pp["column"] == e["column"])].iloc[0]
        assert got["n"] == e["n"]
        for k in ("mae", "hit", "corr2"):
            assert got[k] == pytest.approx(e[k], nan_ok=True), (e["column"], e["stratum"], k)
    py = toy["csv"]["per_year_macro"]
    ey = pd.read_csv(run / "per_year.csv")
    ey = ey[(ey["line"] == "key") & (ey["rows_basis"] == "all")]
    for _, e in ey.iterrows():
        got = py[(py["lead"] == 0) & (py["rows_basis"] == "all") & (py["line"] == "year") &
                 (py["year"] == e["year"]) & (py["column"] == e["column"])].iloc[0]
        assert got["n"] == e["n"] and got["mae"] == pytest.approx(e["mae"])
    pooled = pd.read_csv(run / "score_pooled.csv")
    for _, e in pooled[pooled["rows_basis"] == "all"].iterrows():
        got = py[(py["lead"] == 0) & (py["rows_basis"] == "all") & (py["line"] == "pooled") &
                 (py["column"] == e["column"])].iloc[0]
        assert got["mae"] == pytest.approx(e["mae"])


def test_macro_is_the_unweighted_mean_of_the_group_maes(toy):
    run = toy["run"]
    py = toy["csv"]["per_year_macro"]
    p = _preds(run, 0)
    pg = pd.read_csv(run / "per_group.csv")                  # the engine's per-group adopted MAE
    col = json.loads((run / "verdict.json").read_text(encoding="utf-8"))["adopted_column"]
    got = py[(py["lead"] == 0) & (py["rows_basis"] == "all") & (py["line"] == "macro_over_groups") &
             (py["column"] == col)].iloc[0]
    assert got["n_groups"] == p["group"].nunique() == len(pg)
    assert got["mae"] == pytest.approx(pg["mae_adopted"].mean())


def test_the_all_line_reproduces_the_engine_verdicts(toy):
    pv = toy["csv"]["programme_verdicts"]
    alls = pv[pv["stratum_value"] == CR.ALL]
    assert len(alls) == 4 and alls["matches_engine"].astype(bool).all()


def test_programme_verdicts_reproduce_every_engine_band_pair(toy):
    """The ok toy declined (its adopted column IS the reference, every contrast 0). Here each non-identical
    band pair of jackknife.csv is put through programme_verdicts itself (adopted = the arm, reference = its
    reference, not declined, a huge band), and its ALL line must equal the engine's mean and SE."""
    run = CR.Run(toy["run"], toy["pkg"], CR.Reader(), None, True)
    common, values = CR.common_keys(run), CR._stratum_values(run)
    run.leads = [0]                    # the band pairs are nowcast contrasts; lead files hold fewer arm columns
    jk = pd.read_csv(toy["run"] / "jackknife.csv")
    jk = jk[(jk["kind"] == "band_pair") & (~jk["identical"].astype(bool))]
    assert len(jk)
    for _, e in jk.iterrows():
        run.adopted[0], run.reference, run.declined[0], run.band = e["arm"], e["reference"], False, 1e9
        pv = CR.programme_verdicts(run, common, values)
        got = pv[(pv["lead"] == 0) & (pv["rows_basis"] == "all") & (pv["stratum_value"] == CR.ALL)].iloc[0]
        assert got["mean"] == pytest.approx(e["mean"]) and got["se"] == pytest.approx(e["se"]), (e["arm"], e["reference"])
        assert got["n_groups"] == e["n_groups"] and got["tag"] != "identical"


def test_pooled_lines_at_every_lead_equal_the_engine_ladder_table(toy):
    """Leads 183 and 365 (and 0): per_programme ALL lines and per_year_macro pooled lines against ladder_table.csv."""
    run = toy["run"]
    lt = pd.read_csv(run / "ladder" / "ladder_table.csv")
    lt = lt[(lt["line"] == "pooled") & (lt["rows_basis"] == "all")]
    pp, py = toy["csv"]["per_programme"], toy["csv"]["per_year_macro"]
    checked = set()
    for _, e in lt.iterrows():
        basis = e["ladder_rows"]
        a = pp[(pp["lead"] == e["lead"]) & (pp["rows_basis"] == basis) & (pp["stratum_value"] == CR.ALL) &
               (pp["column"] == e["column"])].iloc[0]
        b = py[(py["lead"] == e["lead"]) & (py["rows_basis"] == basis) & (py["line"] == "pooled") &
               (py["column"] == e["column"])].iloc[0]
        for got in (a, b):
            assert got["n"] == e["n"], (e["lead"], basis, e["column"])
            for k in ("mae", "hit", "corr2"):
                assert got[k] == pytest.approx(e[k], nan_ok=True), (e["lead"], basis, e["column"], k)
        checked.add(int(e["lead"]))
    assert checked == {0, 183, 365}


def test_the_pooled_detection_score_is_labelled(toy):
    pp = toy["csv"]["per_programme"]
    assert (pp.loc[pp["stratum_value"] == CR.ALL, "detection_label"] == CR.DETECTION_POOLED_LABEL).all()
    assert (pp.loc[pp["stratum_value"] != CR.ALL, "detection_label"] == "within programme").all()


def test_counts_match_the_engine_records(toy):
    run = toy["run"]
    pf = toy["csv"]["counts_pool_fallback"]
    assert pf["matches_record"].astype(bool).all() and len(pf) == 6
    for _, r in pf.iterrows():
        t = pd.read_parquet(run / r["pools_file"])
        assert r["rows"] == len(t) and r["rows_pool_fallback"] == int(t["pool_fallback"].sum())
    nt = toy["csv"]["counts_no_tree"]
    dc = json.loads((run / "decision_checks.json").read_text(encoding="utf-8"))["neighbour"]["arms"]
    for arm, folds in dc.items():
        got = nt[(nt["pass"] == "decision_surface") & (nt["arm"] == arm)].iloc[0]
        assert got["n_rows_no_tree"] == sum(f["n_rows_no_tree"] for f in folds.values())
        assert got["share_no_tree"] == pytest.approx(got["n_rows_no_tree"] / got["n_rows"])
    assert set(nt["pass"]) == {"decision_surface", "test_pass", "guard"}
    lo = toy["csv"]["counts_left_out"]
    h4 = lo[lo["what"].str.startswith("H4")]
    assert (h4["rows_record"] == h4["rows_file"]).all() and h4.loc[h4["lead"] == 365, "rows_file"].iloc[0] > 0


def test_the_donor_only_group_scores_nothing_but_lends_donor_rows(toy):
    if toy["variant"] != "donor_only_group":
        pytest.skip("donor-only variant only")
    pe = toy["csv"]["per_ecoregion"]
    assert "g_a" not in set(pe["group"]) and set(pe["group"]) == {"g_b", "g_c", "g_d"}
    d = json.loads((toy["run"] / "derived.json").read_text(encoding="utf-8"))
    assert d["R18:donor_only"]["value"] == ["g_a"]
    assert set(d["R18:units"]["value"]["bank"]["g_a"])              # g_a's rows are bank rows (donor rows)


# ============================================================================== refusals (never writes into a run)
def test_refuses_an_out_folder_inside_the_run_or_a_protected_root_or_not_empty(tmp_path):
    run, pkg = _toy("ok")
    roots = tmp_path / "roots.txt"
    roots.write_text("%s\n" % (tmp_path / "prot").as_posix(), encoding="utf-8")
    with pytest.raises(CR.ReportRefusal, match="inside the run folder"):
        CR.main([str(run), "--package", str(pkg), "--out", str(run / "rep"), "--protected-roots", str(roots), "--toy"])
    with pytest.raises(CR.ReportRefusal, match="protected root"):
        CR.main([str(run), "--package", str(pkg), "--out", str(tmp_path / "prot" / "x"),
                 "--protected-roots", str(roots), "--toy"])
    busy = tmp_path / "busy"
    busy.mkdir()
    (busy / "f.txt").write_text("x", encoding="utf-8")
    with pytest.raises(CR.ReportRefusal, match="not empty"):
        CR.main([str(run), "--package", str(pkg), "--out", str(busy), "--protected-roots", str(roots), "--toy"])
    assert not (run / "rep").exists()


def test_refuses_an_unfinished_run(tmp_path):
    with pytest.raises(CR.ReportRefusal, match="not finished"):
        CR.build(tmp_path, tmp_path)


def _fake_run(folder, record):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "DONE.json").write_text("{}", encoding="utf-8")
    (folder / "run_record.json").write_text(json.dumps(record), encoding="utf-8")
    return folder


def test_the_read_gate_refuses_every_run_that_is_not_a_headline_run(tmp_path):
    # the toy smoke without --toy: refused before any score file is opened
    run, pkg = _toy("ok")
    roots = tmp_path / "roots.txt"
    roots.write_text("# none\n", encoding="utf-8")
    with pytest.raises(CR.ReportRefusal, match="not a headline-eligible headline run"):
        CR.main([str(run), "--package", str(pkg), "--out", str(tmp_path / "o"), "--protected-roots", str(roots)])
    assert not (tmp_path / "o").exists()
    # a real-data smoke (package coral_draft) is refused with or without --toy
    smoke = _fake_run(tmp_path / "smoke", {"kind": "smoke", "headline_eligible": False, "package": "coral_draft",
                                           "input": "table"})
    with pytest.raises(CR.ReportRefusal, match="not a headline-eligible headline run"):
        CR.build(smoke, tmp_path)
    with pytest.raises(CR.ReportRefusal, match="--toy is for the synthetic toy packages"):
        CR.build(smoke, tmp_path, toy=True)
    # a headline run that is not headline-eligible is refused too
    nh = _fake_run(tmp_path / "nh", {"kind": "headline", "headline_eligible": False, "package": "coral",
                                     "input": "table"})
    with pytest.raises(CR.ReportRefusal, match="not a headline-eligible headline run"):
        CR.build(nh, tmp_path)
    # a headline-eligible headline run passes the gate (and then needs its saved files)
    ok = _fake_run(tmp_path / "ok", {"kind": "headline", "headline_eligible": True, "package": "coral",
                                     "input": "table"})
    with pytest.raises(CR.ReportRefusal, match="missing saved file: .*verdict.json"):
        CR.build(ok, tmp_path)


def test_refuses_when_the_protected_roots_file_is_missing(tmp_path):
    run, pkg = _toy("ok")
    with pytest.raises(CR.ReportRefusal, match="protected-roots file .* is missing"):
        CR.main([str(run), "--package", str(pkg), "--out", str(tmp_path / "o"),
                 "--protected-roots", str(tmp_path / "absent.txt"), "--toy"])


def test_refuses_a_verdict_that_disagrees_with_the_engine(monkeypatch):
    run, pkg = _toy("ok")
    real = CR._engine_match

    def wrong(r, L, basis, v, rec):
        out = real(r, L, basis, v, rec)
        if v == CR.ALL and L == 183:
            out["matches_engine"] = False
        return out

    monkeypatch.setattr(CR, "_engine_match", wrong)
    with pytest.raises(CR.ReportRefusal, match=r"disagrees with the engine's record at \[\(183, 'common'\)\]"):
        CR.build(run, pkg, toy=True)


def test_refuses_when_a_donor_cross_check_cannot_be_made(monkeypatch):
    run, pkg = _toy("ok")
    r = CR.Run(run, pkg, CR.Reader(), None, True)
    r.preds[183] = r.preds[183].drop(columns=[CR.DONOR_MEDIAN])
    with pytest.raises(CR.ReportRefusal, match="lead 183: test_preds holds no base__donor_median"):
        CR.magnitude_edges(r, 183)
    monkeypatch.setattr(CR.Run, "engine_donor_count", lambda self, L: None)
    with pytest.raises(CR.ReportRefusal, match="fitctx_log holds no 'bank' donor_rows record"):
        CR.magnitude_edges(r, 0)


# ============================================================================== saved records (added 2026-10-20)
# (1) guard reference, (2) R30 and marine-heatwave NaN rows, (3) month-precision pools, (4) penalty-grid edge picks,
# (5) blocked jackknife per programme, and the two flattening edges (sheet item B4).
# Version 1.2.0 (2026-10-20, second skeptic review): R30 counts per lead from the lead tables, the pinned
# month-precision list, fail-loud refusals on the guard and run.log records, the engine's own blocked jackknife,
# edge labels that follow EDGE_DEFAULT.
def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_guard_reference_reads_the_saved_guard_records(toy):
    run = toy["run"]
    gr = toy["csv"]["guard_reference"].set_index("lead")
    assert list(gr.index) == [0, 183, 365]
    for L in (183, 365):
        lj = _json(run / "ladder" / ("lead_%d" % L) / "lead.json")
        g, r = lj["guard"], gr.loc[L]
        assert r["reference_column"] == g["baseline_column"] == "base__donor_median"
        assert r["reference_value"] == pytest.approx(g["baseline_value"])
        assert r["reference_donor_rows"] == g["baseline_donor_rows"] and r["surface_rows"] == g["surface_rows"]
        assert r["reference_mae"] == pytest.approx(g["baseline_mae"]) and r["pinned_mae"] == pytest.approx(g["pinned_mae"])
        assert r["pinned_minus_reference"] == pytest.approx(g["pinned_mae"] - g["baseline_mae"])
        assert r["pinned_arm"] == lj["pinned"] and bool(r["passed"]) == g["passed"]
        assert r["decline_target"] == lj["test"]["decline_target"] and bool(r["guard_and_decline_one_object"])
    # nowcast: the decline baseline's surface MAE and the best tree arm's surface MAE, from the saved records
    dc = _json(run / "decision_checks.json")["decline_baseline"]
    v = _json(run / "verdict.json")
    ic = pd.read_csv(run / "inner_candidates.csv")
    bp = v["best_tree_penalty"]
    want = ic[(ic["arm"] == v["best_tree_arm"]) & (ic["level"] == bp["level"]) & (ic["ratio"] == bp["ratio"])]
    assert len(want) == 1
    r0 = gr.loc[0]
    assert r0["reference_column"] == dc["key"] and r0["reference_mae"] == pytest.approx(dc["mae"])
    assert r0["pinned_arm"] == v["best_tree_arm"] and r0["pinned_mae"] == pytest.approx(want["mae"].iloc[0])
    assert bool(r0["passed"]) == (not v["declined"]) and "reference_donor_rows" in r0["not_saved"]
    if toy["variant"] == "ok":                                  # hand-checked numbers of the ok toy (lead.json, run.log)
        assert gr.loc[183, "reference_value"] == pytest.approx(11.769119)
        assert gr.loc[183, "pinned_minus_reference"] == pytest.approx(22.73744925024354 - 20.926807638888892)
        assert r0["pinned_mae"] == pytest.approx(21.728048, abs=1e-6)     # run.log: log_c_plain_gls MAE 21.728048


def _donor_table(run, pkg, L):
    """Independent rebuild of the donor rows (bank ids, fit cut, finite label), every column of the lead table."""
    d = json.loads((run / "derived.json").read_text(encoding="utf-8"))
    bank = {u for v in d["R18:units"]["value"]["bank"].values() for u in v}
    cut = d["R11"]["value"][str(L)]["fit_cut"]
    t = pd.read_parquet(pkg / "data" / ("lead_%d.parquet" % L))
    day = np.array([x.toordinal() for x in t["visit_date"]])
    return t[t["row_id"].isin(bank).to_numpy() & (day <= cut) & np.isfinite(t["y"].to_numpy())]


def test_r30_saved_rows_and_the_counts_per_lead(toy):
    run, pkg = toy["run"], toy["pkg"]
    r30 = _json(run / "derived.json")["R30"]["inputs"]
    t = toy["csv"]["r30_missing"]
    per_col = t[t["status"] == "saved: derived.json R30"].set_index("column")
    assert set(per_col.index) == set(r30["filled_share"])
    for c, s in r30["filled_share"].items():
        assert per_col.loc[c, "filled_share"] == pytest.approx(s) and per_col.loc[c, "lead"] == 0
        for yr, ys in r30["test_year_missing_share"][c].items():
            assert per_col.loc[c, "test_year_missing_share_%s" % yr] == pytest.approx(ys)
    counted = t[t["what"].str.startswith("NaN share")]
    assert counted["status"].str.startswith(CR.COUNTED).all()
    assert not t["status"].astype(str).str.startswith(CR.NOT_SAVED).any()
    for L in (0, 183, 365):
        d = _donor_table(run, pkg, L)
        p = _preds(run, L)
        tab = pd.read_parquet(pkg / "data" / ("lead_%d.parquet" % L)).set_index("row_id")
        sc = tab.loc[p.loc[np.isfinite(p["y"].to_numpy(float)), "unit"].astype(str).tolist()]
        for which, rows in (("donor", d), ("scored", sc)):
            label = dict(CR.ROW_SETS)[which]
            got = counted[(counted["lead"] == L) & (counted["rows_set"] == label)].set_index("column")
            assert set(got.index) == set(r30["filled_share"])
            for c in r30["filled_share"]:                                     # independent: isna on the lead table
                assert got.loc[c, "n_rows"] == len(rows) and got.loc[c, "n_nan"] == int(rows[c].isna().sum())
            checked = got["status"].str.contains("equals derived.json R30")
            assert checked.all() if (L == 0 and which == "donor") else not checked.any()
    if toy["variant"] == "ok":                                                # 13 of the 116 lead-0 donor rows
        f6 = counted[(counted["lead"] == 0) & (counted["rows_set"] == dict(CR.ROW_SETS)["donor"]) &
                     (counted["column"] == "f6")].iloc[0]
        assert (f6["n_nan"], f6["n_rows"]) == (13, 116) and f6["nan_share"] == pytest.approx(13 / 116)
        assert f6["r30_saved_share"] == pytest.approx(r30["filled_share"]["f6"])
    # the toy package has no mhw_* column: the marine-heatwave counts say so, per lead and row set
    mh = t[t["what"].str.startswith("rows with a NaN")]
    assert len(mh) == 3 * 2 * 2 and mh["n_nan"].isna().all() and mh["status"].str.startswith("no mhw").all()


def _r30_fake(filled):
    nan = np.nan
    frames = {(0, "donor"): pd.DataFrame({"f1": [nan, 1, 2, 3], "mhw_days_365": [1, nan, 3, 4],
                                          "mhw_thr_gap": [nan, nan, 0.1, 0.2]}),
              (0, "scored"): pd.DataFrame({"f1": [1, 2, 3], "mhw_days_365": [nan, nan, 1],
                                           "mhw_thr_gap": [nan, nan, 0.3]}),
              (183, "donor"): pd.DataFrame({"f1": [1, 2], "mhw_days_365": [1, 2], "mhw_thr_gap": [nan, 0.1]}),
              (183, "scored"): pd.DataFrame({"f1": [nan], "mhw_days_365": [nan], "mhw_thr_gap": [nan]})}
    derived = {"R30": {"inputs": {"filled_share": filled,
                                  "real_zero_share": {"f1": 0.5, "mhw_days_365": 0.2, "mhw_thr_gap": 0.0},
                                  "test_year_missing_share": {"mhw_thr_gap": {"2016": 1.0}},
                                  "constants": {"C15.missing_flag_share": 0.25}},
                       "value": {"mhw_thr_gap": ["over_threshold", "vanishes:2016"]}}}
    return types.SimpleNamespace(derived=derived, leads=[0, 183], feature_columns=["f1", "mhw_days_365", "mhw_thr_gap"],
                                 mhw_columns=["mhw_days_365", "mhw_thr_gap"],
                                 feature_frame=lambda L, which: frames[(L, which)])


def test_r30_marine_heatwave_counts_by_hand():
    t = CR.r30_missing(_r30_fake({"f1": 0.25, "mhw_days_365": 0.25, "mhw_thr_gap": 0.5}))
    cols = t[t["status"] == "saved: derived.json R30"].set_index("column")
    assert cols["marine_heatwave"].tolist() == [False, True, True]
    assert cols["over_threshold"].tolist() == [False, False, True]               # 0.5 > 0.25 only
    assert cols.loc["mhw_thr_gap", "engine_flags"] == "over_threshold;vanishes:2016"
    assert cols.loc["mhw_thr_gap", "test_year_missing_share_2016"] == 1.0
    mx = t[t["what"].str.startswith("largest")].iloc[0]
    assert mx["filled_share"] == pytest.approx(0.5) and mx["column"] == "(2 marine-heatwave columns)"
    donor, scored = dict(CR.ROW_SETS)["donor"], dict(CR.ROW_SETS)["scored"]

    def count(L, rows_set, what):
        r = t[(t["lead"] == L) & (t["rows_set"] == rows_set) & t["what"].str.startswith(what)]
        assert len(r) == 1
        return r.iloc[0]
    # lead 0 donor rows: rows 0 and 1 hold a NaN in some mhw_* column; only row 1 in mhw_days_365 (row 0's NaN is
    # mhw_thr_gap alone, the 'other reason')
    assert count(0, donor, "rows with a NaN in any")["n_nan"] == 2
    assert count(0, donor, "rows with a NaN in mhw_days_365")["n_nan"] == 1
    assert count(0, scored, "rows with a NaN in any")["n_nan"] == 2
    assert count(0, scored, "rows with a NaN in mhw_days_365")["n_nan"] == 2
    assert count(183, donor, "rows with a NaN in any")["n_nan"] == 1
    assert count(183, donor, "rows with a NaN in mhw_days_365")["n_nan"] == 0
    assert count(183, scored, "rows with a NaN in any")["n_nan"] == 1
    assert count(183, scored, "rows with a NaN in any")["n_rows"] == 1
    per = t[t["what"].str.startswith("NaN share") & (t["lead"] == 0) & (t["rows_set"] == donor)].set_index("column")
    assert per["nan_share"].tolist() == pytest.approx([0.25, 0.25, 0.5])
    assert per["status"].str.contains("equals derived.json R30").all()
    lead183 = t[(t["lead"] == 183) & t["what"].str.startswith(("NaN share", "rows with"))]
    assert (lead183["status"].str.startswith(CR.COUNTED)).all()


def test_r30_refuses_a_shifted_share():
    with pytest.raises(CR.ReportRefusal, match="NaN share of f1 on the 4 donor rows.*R30 filled_share is 0.3"):
        CR.r30_missing(_r30_fake({"f1": 0.3, "mhw_days_365": 0.25, "mhw_thr_gap": 0.5}))
    with pytest.raises(CR.ReportRefusal, match="derived.json has no R30"):
        CR.r30_missing(types.SimpleNamespace(derived={}, leads=[0]))


def test_r30_refuses_a_shifted_share_on_the_toy():
    run, pkg = _toy("ok")
    r = CR.Run(run, pkg, CR.Reader(), None, True)
    r.derived = json.loads(json.dumps(r.derived))
    r.derived["R30"]["inputs"]["filled_share"]["f6"] = 14 / 116
    with pytest.raises(CR.ReportRefusal, match="NaN share of f6 on the 116 donor rows"):
        CR.r30_missing(r)


def test_month_precision_pools_by_hand(tmp_path):
    for name, cells in (("pools_decision_surface.parquet", [["a", "b"], ["b"], ["c", "a"]]),
                        ("pools_test_pass.parquet", [["b"], ["c"]])):
        pd.DataFrame({"row_id": ["x%d" % i for i in range(len(cells))],
                      "pool_row_ids": [json.dumps(c) for c in cells]}).to_parquet(tmp_path / name)
    fake = types.SimpleNamespace(folder=tmp_path, leads=[0], r=CR.Reader())
    t = CR.pools_month_precision(fake, {"a", "zzz"}, "hand list").set_index("pass")
    assert t.loc["decision_surface", "pools"] == 3 and t.loc["decision_surface", "pools_holding_month_precision_row"] == 2
    assert t.loc["decision_surface", "share_pools_holding"] == pytest.approx(2 / 3)
    assert t.loc["decision_surface", "distinct_month_precision_rows_in_pools"] == 1
    assert t.loc["test_pass", "pools_holding_month_precision_row"] == 0
    none = CR.pools_month_precision(fake, None)
    assert none["status"].str.startswith(CR.NOT_SAVED).all() and none["pools_holding_month_precision_row"].isna().all()


def test_edge_axes_and_log_picks_by_hand():
    grid = [(0.1, 0.5), (0.1, 1.0), (1.0, 0.5), (1.0, 1.0), (10.0, 0.5), (10.0, 1.0)]
    assert CR.edge_axes((0.1, 0.5), grid) == {"level": "bottom", "ratio": "bottom"}
    assert CR.edge_axes((1.0, 1.0), grid) == {"level": None, "ratio": "top"}
    assert CR._edge_text(CR.edge_axes((1.0, 1.0), grid)) == "ratio top"
    assert CR.edge_axes((1.0, 0.5), [(1.0, 0.5), (1.0, 1.0)]) == {"level": None, "ratio": "bottom"}   # frozen level
    with pytest.raises(CR.ReportRefusal, match="not a point of the saved grid"):
        CR.edge_axes((3.0, 0.5), grid)
    text = "\n".join([
        "[01:00:00]   a_plain_gls                        MAE 1.000000 at level 0.1 ratio 0.5 | pre-clip 0",  # outside
        "[01:00:01] decision surface: 10 rows, 7 candidates, legal range [0.0, 100.0], surface SHA-256 ab",
        "[01:00:01]   a_plain_gls                        MAE 2.500000 at level 1.0 ratio 1.0 | EDGE PICK: ratio top"
        " | pre-clip 0 below, 0 above of 10 | corr2 0.1 (beside)",
        "[01:00:01]   b_plain_gls                        MAE 3.000000 at level 1.0 ratio 0.75 | pre-clip 0 below",
        "[01:00:01]   a_trees_off_unweighted             MAE 4.000000 at no grid | pre-clip 0 below",
        "[01:00:01]   predict-zero MAE 5.000000 (beside, never used)",
        "[01:00:02]   c_plain_gls                        MAE 6.000000 at level 0.1 ratio 0.5 | pre-clip 0"])   # after
    picks = CR.log_picks(text)
    assert [(p["arm"], p["point"], p["printed_edge"], p["block"]) for p in picks] == [
        ("a_plain_gls", (1.0, 1.0), "ratio top", 1), ("b_plain_gls", (1.0, 0.75), "", 1)]
    assert picks[0]["surface_mae"] == 2.5


def test_penalty_edge_picks_on_the_toy(toy):
    run = toy["run"]
    pe = toy["csv"]["penalty_edge_picks"]
    ad = _json(run / "adoption.json")
    levels = sorted({g["level"] for g in ad["decision"]["grid"]})
    ratios = sorted({g["ratio"] for g in ad["decision"]["grid"]})
    log = pe[pe["source"].str.startswith("run.log")]
    assert len(log) == 12                                  # the 12 tree arms (trees-off has no grid)
    assert log["matches_engine_print"].astype(bool).all()
    printed = [ln for ln in (run / "run.log").read_text(encoding="utf-8").splitlines() if "EDGE PICK" in ln]
    assert len(printed) == int(log["at_edge"].astype(bool).sum())
    best = pe[pe["source"] == "adoption.json best_tree_penalty"].iloc[0]
    bp = ad["best_tree_penalty"]
    assert best["level"] == bp["level"] and best["ratio"] == bp["ratio"]
    # independent: 'bottom' / 'top' when the pick is the grid's smallest / largest value on that axis
    want_l = "bottom" if bp["level"] == levels[0] else ("top" if bp["level"] == levels[-1] else "")
    want_r = "bottom" if bp["ratio"] == ratios[0] else ("top" if bp["ratio"] == ratios[-1] else "")
    assert str(best["edge_level"]).replace("nan", "") == want_l and str(best["edge_ratio"]).replace("nan", "") == want_r
    for L in (183, 365):
        r = pe[(pe["lead"] == L)].iloc[0]
        al = _json(run / ("adoption_lead_%d.json" % L))
        assert r["level"] == al["penalty"]["level"] and r["ratio"] == al["penalty"]["ratio"]
    adopted = pe[pe["source"].str.startswith("adoption.json penalty")].iloc[0]
    if ad["penalty"] is None:                              # the ok toy declined at the nowcast
        assert toy["variant"] == "ok" and math.isnan(adopted["level"]) and "declined" in adopted["note"]
    else:                                                  # the donor-only toy adopted identity_plain_gls at level 3, ratio 1/16
        assert toy["variant"] == "donor_only_group"
        assert (adopted["level"], adopted["ratio"]) == (3.0, 0.0625) and 3.0 not in (levels[0], levels[-1])
        assert str(adopted["edge_level"]) == "nan" and adopted["edge_ratio"] == "bottom" and bool(adopted["at_edge"])


def test_blocked_jackknife_by_hand():
    per_group = {"a": 1.0, "b": 3.0, "c": 5.0, "d": 7.0}
    blocks = {"a": 0, "b": 0, "c": 1, "d": 2}
    bj = CR.blocked_jackknife(per_group, blocks)
    # block values 2, 5, 7; leave-one-out means 6, 4.5, 3.5 (mean 14/3); SE = sqrt(2/3 * 19/6)
    assert bj["n_blocks"] == 3 and bj["mean"] == pytest.approx(14 / 3)
    assert bj["se"] == pytest.approx(math.sqrt(2.0 / 3.0 * 19.0 / 6.0))
    gse = CR.jackknife(np.array([1.0, 3.0, 5.0, 7.0]))["se"]                  # sqrt(3/4 * 20/9)
    assert gse == pytest.approx(math.sqrt(0.75 * 20.0 / 9.0))
    assert not CR.blocked_flag(gse, bj["se"])                                  # 1.453 is not above 1.2 x 1.291
    assert CR.blocked_flag(1.0, 1.21) and not CR.blocked_flag(1.0, 1.2) and not CR.blocked_flag(float("nan"), 2.0)
    with pytest.raises(CR.ReportRefusal, match="without an overlap block"):
        CR.blocked_jackknife({"a": 1.0, "z": 2.0}, blocks)


def test_programme_blocked_jackknife_on_the_toy(toy):
    pb = toy["csv"]["programme_blocked_jackknife"]
    alls = pb[(pb["lead"] == 0) & (pb["rows_basis"] == "all") & (pb["stratum_value"] == CR.ALL)]
    assert len(alls) == 1 and bool(alls["matches_engine"].iloc[0])
    v = _json(toy["run"] / "verdict.json")["blocked_jackknife"]
    assert alls["mean"].iloc[0] == pytest.approx(v["mean"]) and alls["n_blocks"].iloc[0] == v["n_blocks"]
    rest = pb.drop(alls.index)
    assert (rest["engine_record"] == CR.NOT_SAVED).all() and set(rest["stratum_value"]) >= {"field", "lab", "remote"}


def test_programme_blocked_jackknife_reproduces_the_engine_band_pairs(toy):
    """The toy's overlap blocks are one group each, so the blocked jackknife equals the group jackknife: each
    non-identical band pair of jackknife.csv, put through programme_blocked_jackknife, gives the engine's mean and SE."""
    run = CR.Run(toy["run"], toy["pkg"], CR.Reader(), None, True)
    bog = run.derived["R14:overlap_blocks"]["value"]["block_of_group"]
    assert len(set(bog.values())) == len(bog)
    common, values = CR.common_keys(run), CR._stratum_values(run)
    run.leads = [0]
    jk = pd.read_csv(toy["run"] / "jackknife.csv")
    jk = jk[(jk["kind"] == "band_pair") & (~jk["identical"].astype(bool))]
    assert len(jk)
    for _, e in jk.iterrows():
        run.adopted[0], run.reference, run.declined[0] = e["arm"], e["reference"], False
        pb = CR.programme_blocked_jackknife(run, common, values)
        got = pb[(pb["lead"] == 0) & (pb["rows_basis"] == "all") & (pb["stratum_value"] == CR.ALL)].iloc[0]
        assert got["mean"] == pytest.approx(e["mean"]) and got["se"] == pytest.approx(e["se"])
        assert got["group_se"] == pytest.approx(e["se"]) and got["n_blocks"] == e["n_groups"] and got["flag"] == ""


def test_refuses_a_blocked_jackknife_that_disagrees_with_the_engine(monkeypatch):
    run, pkg = _toy("ok")
    real = CR.blocked_jackknife

    def shifted(per_group, blocks):
        out = dict(real(per_group, blocks))
        out["mean"] += 1.0
        return out

    monkeypatch.setattr(CR, "blocked_jackknife", shifted)
    with pytest.raises(CR.ReportRefusal, match="blocked jackknife disagrees with verdict.json"):
        CR.build(run, pkg, toy=True)


def test_both_flattening_edges_are_printed_and_b_is_the_default(toy):
    # owner ruling X4 (2026-10-20): (b) q75 of the positive donor-row labels is the default
    assert CR.EDGE_DEFAULT == CR.EDGE_POSITIVE == "q75_positive_donor_labels"
    fg = toy["csv"]["flattening_guard"]
    assert set(fg["edge_rule"]) == {CR.EDGE_PRIMARY, CR.EDGE_POSITIVE}
    a = fg[fg["edge_rule"] == CR.EDGE_PRIMARY]
    b = fg[fg["edge_rule"] == CR.EDGE_POSITIVE]
    assert b["is_default"].astype(bool).all() and not a["is_default"].astype(bool).any()
    assert b["edge_role"].str.startswith("(b) q75 of positive donor-row labels -- DEFAULT").all()
    assert a["edge_role"].str.startswith("(a) q75 of all donor-row labels -- printed beside").all()
    md = (toy["out"] / "coral_report.md").read_text(encoding="utf-8")
    roles = CR.edge_roles()
    assert roles[CR.EDGE_PRIMARY] in md and roles[CR.EDGE_POSITIVE] in md and "owner ruling X4" in md
    man = _json(toy["out"] / "inputs_manifest.json")
    assert man["default_flattening_edge"] == CR.EDGE_POSITIVE


def test_month_precision_pools_on_the_toy(toy, tmp_path):
    run, pkg = toy["run"], toy["pkg"]
    t = toy["csv"]["pools_month_precision"]
    assert len(t) == 6 and t["status"].str.startswith(CR.NOT_SAVED).all()     # a toy run without a list
    # a SYNTHETIC month-precision list: one row id that sits in some pools
    first = json.loads(pd.read_parquet(run / "pools_test_pass.parquet")["pool_row_ids"].iloc[0])[0]
    lst = tmp_path / "mp.csv"
    pd.DataFrame({"row_id": [first]}).to_csv(lst, index=False)
    roots = tmp_path / "roots.txt"
    roots.write_text("# none\n", encoding="utf-8")
    out = tmp_path / "o"
    assert CR.main([str(run), "--package", str(pkg), "--out", str(out), "--protected-roots", str(roots), "--toy",
                    "--month-precision-rows", str(lst)]) == 0
    got = pd.read_csv(out / "pools_month_precision.csv")
    quoted = json.dumps(first)
    for _, r in got.iterrows():
        cells = pd.read_parquet(run / r["pools_file"])["pool_row_ids"].tolist()
        want = sum(1 for c in cells if quoted in c)                               # independent: a text search
        assert r["pools_holding_month_precision_row"] == want and "not an engine record" in r["status"]
    assert got["pools_holding_month_precision_row"].sum() > 0
    man = _json(out / "inputs_manifest.json")
    assert str(lst.resolve()) in man["inputs_sha256"] and str(lst.resolve()) in man["month_precision_rows"]
    # a listed id that is no row of the lead-0 table (e.g. a row-id format mismatch) is refused, not counted as 0
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"row_id": [first, "no_such_row"]}).to_csv(bad, index=False)
    with pytest.raises(CR.ReportRefusal, match="1 listed month-precision row ids are not rows of the lead-0 table"):
        CR.build(run, pkg, toy=True, month_precision_rows=bad)


def test_month_precision_list_is_pinned_for_a_non_toy_run(tmp_path, monkeypatch):
    lst = tmp_path / "mp.csv"
    pd.DataFrame({"row_id": ["r1", "r2"], "group": ["a", "b"]}).to_csv(lst, index=False)
    sha = CR.sha256_file(lst)
    fake = types.SimpleNamespace(tables={0: pd.DataFrame({"row_id": ["r1", "r2", "r3"]})})
    assert CR.MONTH_PRECISION_LIST == Path("D:/treeroute/coral_build/coral_data/month_precision_rows.csv")
    monkeypatch.setattr(CR, "MONTH_PRECISION_LIST", lst)
    monkeypatch.setattr(CR, "MONTH_PRECISION_SHA256", sha)
    # non-toy, no flag: the pinned constant is read
    ids, src = CR.month_precision_ids(CR.Reader(), fake, None, toy=False)
    assert ids == {"r1", "r2"} and sha[:16] in src
    # non-toy, a given file with another SHA-256: refused
    other = tmp_path / "other.csv"
    pd.DataFrame({"row_id": ["r1"]}).to_csv(other, index=False)
    with pytest.raises(CR.ReportRefusal, match="the pinned list"):
        CR.month_precision_ids(CR.Reader(), fake, other, toy=False)
    # the pinned file changed: refused
    monkeypatch.setattr(CR, "MONTH_PRECISION_SHA256", "0" * 64)
    with pytest.raises(CR.ReportRefusal, match="the pinned list"):
        CR.month_precision_ids(CR.Reader(), fake, None, toy=False)
    # absent: refused
    monkeypatch.setattr(CR, "MONTH_PRECISION_LIST", tmp_path / "absent.csv")
    with pytest.raises(CR.ReportRefusal, match="does not exist"):
        CR.month_precision_ids(CR.Reader(), fake, None, toy=False)
    # a toy run without a list: none (the count prints 'not saved by the engine')
    assert CR.month_precision_ids(CR.Reader(), fake, None, toy=True) == (None, "")


# ------------------------------------------------------------------ fail-loud refusals on the saved records
def _toy_run_in(dest, names):
    """The ok toy's Run, re-pointed at a COPY of the named record files (the toy run itself is never edited)."""
    import shutil

    run, pkg = _toy("ok")
    r = CR.Run(run, pkg, CR.Reader(), None, True)
    dest.mkdir(parents=True, exist_ok=True)
    for n in names:
        shutil.copyfile(run / n, dest / n)
    r.folder = dest
    r.r = CR.Reader()
    return r


GUARD_FILES = ("adoption.json", "decision_checks.json")
PICK_FILES = ("adoption.json", "adoption_lead_183.json", "adoption_lead_365.json", "run.log")


def test_guard_reference_refuses_missing_or_inconsistent_records(tmp_path):
    r = _toy_run_in(tmp_path / "a", GUARD_FILES)
    assert len(CR.guard_reference(r)) == 3                                       # the copy itself passes
    del r.lead_json[183]["guard"]["baseline_mae"]
    with pytest.raises(CR.ReportRefusal, match=r"lead 183: the guard record .* lacks \['baseline_mae'\]"):
        CR.guard_reference(r)
    r = _toy_run_in(tmp_path / "b", GUARD_FILES)
    r.lead_json[365]["guard"]["passed"] = True                                   # declined_at_lead is True
    with pytest.raises(CR.ReportRefusal, match="lead 365: lead.json guard.passed is True but declined_at_lead"):
        CR.guard_reference(r)
    r = _toy_run_in(tmp_path / "c", GUARD_FILES)
    dc = _json(r.folder / "decision_checks.json")
    del dc["decline_baseline"]
    (r.folder / "decision_checks.json").write_text(json.dumps(dc), encoding="utf-8")
    with pytest.raises(CR.ReportRefusal, match="holds no decline_baseline MAE"):
        CR.guard_reference(r)
    r = _toy_run_in(tmp_path / "d", GUARD_FILES)
    r.verdict["best_tree_penalty"] = {"level": 7.0, "ratio": 0.0625}             # no such surface point
    with pytest.raises(CR.ReportRefusal, match="surface_mae holds no entry for the best tree arm"):
        CR.guard_reference(r)


def _log_edit(r, old, new, count=1):
    p = r.folder / "run.log"
    s = p.read_text(encoding="utf-8")
    assert old in s
    p.write_text(s.replace(old, new, count), encoding="utf-8")


def test_penalty_edge_picks_refuse_gaps_in_the_saved_records(tmp_path):
    r = _toy_run_in(tmp_path / "ok", PICK_FILES)
    assert len(CR.penalty_edge_picks(r)) == 4 + 12           # adopted, best, two leads; 12 arms: the copy passes
    r = _toy_run_in(tmp_path / "absent", PICK_FILES)
    (r.folder / "run.log").unlink()
    with pytest.raises(CR.ReportRefusal, match="run.log is absent"):
        CR.penalty_edge_picks(r)
    r = _toy_run_in(tmp_path / "nohead", PICK_FILES)
    _log_edit(r, "decision surface:", "decision table:")
    with pytest.raises(CR.ReportRefusal, match="holds 0 decision blocks"):
        CR.penalty_edge_picks(r)
    r = _toy_run_in(tmp_path / "two", PICK_FILES)
    s = (r.folder / "run.log").read_text(encoding="utf-8")
    (r.folder / "run.log").write_text(s + s, encoding="utf-8")
    with pytest.raises(CR.ReportRefusal, match="holds 2 decision blocks"):
        CR.penalty_edge_picks(r)
    r = _toy_run_in(tmp_path / "nolines", PICK_FILES)
    _log_edit(r, " | pre-clip ", " | preclip ", count=-1)
    with pytest.raises(CR.ReportRefusal, match="no parsed per-arm line"):
        CR.penalty_edge_picks(r)
    r = _toy_run_in(tmp_path / "arm", PICK_FILES)
    _log_edit(r, "  arcsine_corrector_gls ", "  arcsine_corrector_glz ")
    with pytest.raises(CR.ReportRefusal, match="parsed tree arms .* differ from adoption.json"):
        CR.penalty_edge_picks(r)
    r = _toy_run_in(tmp_path / "mae", PICK_FILES)
    _log_edit(r, "MAE 21.728048 at level", "MAE 21.728058 at level")             # log_c_plain_gls, +1e-5
    with pytest.raises(CR.ReportRefusal, match="prints MAE 21.728058 for log_c_plain_gls"):
        CR.penalty_edge_picks(r)
    r = _toy_run_in(tmp_path / "best", PICK_FILES)
    ad = _json(r.folder / "adoption.json")
    ad["best_tree_penalty"] = {"level": 0.3, "ratio": 0.0625}                    # a grid point, not the printed one
    (r.folder / "adoption.json").write_text(json.dumps(ad), encoding="utf-8")
    with pytest.raises(CR.ReportRefusal, match="prints the best tree arm log_c_plain_gls at level 0.1"):
        CR.penalty_edge_picks(r)


# ------------------------------------------------------------------ the blocked jackknife against the engine's code
def _engine_metrics():
    import build_toy_runs

    eng = str(build_toy_runs.DEFAULT_ENGINE)
    if eng not in sys.path:
        sys.path.insert(0, eng)
    from treeroute.report import metrics as EM

    return EM


@pytest.mark.parametrize("case", ["hand", "twelve_groups_five_blocks", "five_blocks_wide"])
def test_blocked_jackknife_equals_the_engine_functions(case):
    """Pure functions only: CR.blocked_jackknife / CR.blocked_flag against the engine's own
    treeroute.report.metrics.blocked_jackknife / blocked_jackknife_flag (metrics.py:1058-1086)."""
    EM = _engine_metrics()
    if case == "hand":
        per_group = {"a": 1.0, "b": 3.0, "c": 5.0, "d": 7.0}
        blocks = {"a": 0, "b": 0, "c": 1, "d": 2}
    elif case == "twelve_groups_five_blocks":                 # blocks of 4, 3, 2, 2, 1 groups; mixed values
        vals = [0.4, -1.3, 2.2, 0.9, -0.7, 1.8, 3.1, -2.4, 0.05, 1.1, -0.6, 2.7]
        per_group = {"g%02d" % i: v for i, v in enumerate(vals)}
        bl = [0, 0, 0, 0, 1, 1, 1, 2, 2, 3, 3, 4]
        blocks = {"g%02d" % i: b for i, b in enumerate(bl)}
    else:                                                     # 12 groups, 5 blocks, values alike within a block
        bl = [0, 0, 0, 1, 1, 1, 2, 2, 3, 3, 4, 4]
        centre = {0: -3.0, 1: 4.0, 2: 0.5, 3: 6.0, 4: -1.0}
        per_group = {"g%02d" % i: centre[b] + 0.01 * i for i, b in enumerate(bl)}
        blocks = {"g%02d" % i: b for i, b in enumerate(bl)}
    mine = CR.blocked_jackknife(per_group, blocks)
    eng = EM.blocked_jackknife(per_group, blocks)
    assert mine["mean"] == pytest.approx(eng.mean, rel=1e-12) and mine["se"] == pytest.approx(eng.se, rel=1e-12)
    assert mine["n_blocks"] == eng.n_groups == len(set(blocks.values()))
    groups = sorted(per_group)
    gse_mine = CR.jackknife(np.asarray([per_group[g] for g in groups]))["se"]
    g_eng = EM.group_jackknife(np.asarray([per_group[g] for g in groups]))
    assert gse_mine == pytest.approx(g_eng.se, rel=1e-12)
    flag = CR.blocked_flag(gse_mine, mine["se"])
    assert flag == EM.blocked_jackknife_flag(g_eng, eng)
    if case == "five_blocks_wide":                            # the flag case: blocked SE well above 1.2 x group SE
        assert flag is True
    if case == "hand":
        assert flag is False


def test_edge_labels_follow_edge_default(monkeypatch):
    roles = CR.edge_roles()
    assert "DEFAULT (owner ruling X4)" in roles[CR.EDGE_POSITIVE]
    assert "not the default" in roles[CR.EDGE_PRIMARY]
    monkeypatch.setattr(CR, "EDGE_DEFAULT", CR.EDGE_PRIMARY)                    # the labels follow EDGE_DEFAULT
    roles = CR.edge_roles()
    assert roles[CR.EDGE_PRIMARY].startswith("(a) q75 of all donor-row labels -- DEFAULT")
    assert roles[CR.EDGE_POSITIVE].startswith("(b) q75 of positive donor-row labels -- printed beside")
    monkeypatch.setattr(CR, "EDGE_DEFAULT", CR.EDGE_POSITIVE)                   # back to the ruled default (X4)
    f = pd.DataFrame({"y": [0.0, 10.0, 40.0, 80.0], "group": list("aabb"), "src": ["x"] * 4,
                      "arm__m": [1.0, 8.0, 30.0, 50.0], "base__predict_zero": [0.0] * 4,
                      "base__donor_median": [5.0] * 4})
    t = CR.flattening_table(_FakeRun(f), set(), ["x"], {0: {CR.EDGE_PRIMARY: 40.0, CR.EDGE_POSITIVE: 70.0}})
    b = t[t["edge_rule"] == CR.EDGE_POSITIVE]
    a = t[t["edge_rule"] == CR.EDGE_PRIMARY]
    assert b["is_default"].all() and not a["is_default"].any()
    assert b["edge_role"].str.contains("DEFAULT").all() and not a["edge_role"].str.contains("DEFAULT").any()
