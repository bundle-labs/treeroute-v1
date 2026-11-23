# Verification only (builder B): checks that every cells.json entry sits in the column whose header it belongs to and
# that its selector names the statistic, level, model, pair, family and rank its row and column say. Writes nothing.
# Version 2 of the spec: one check added, panel f's family shares have part `share` (G1).
import sys, os, re, json
sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_B = os.path.dirname(HERE)
SHAP = "D:\\treeroute\\analysis\\shap_v1"
with open(os.path.join(OUT_B, "tables.md"), "r", encoding="utf-8") as f:
    lines = f.read()[:-1].split("\n")
with open(os.path.join(OUT_B, "cells.json"), "r", encoding="utf-8") as f:
    E = json.load(f)["entries"]

fails = []
PNAME = {"PM2.5": "pm25", "NDVI": "ndvi", "Burned fraction": "fire", "Forest loss": "defo", "Coral bleaching": "coral",
         "Coral bleaching\u1d48": "coral"}
TID2P = {"S3.23": "pm25", "S3.24": "ndvi", "S3.25": "fire", "S3.26": "defo", "S3.27": "coral"}
MH = {"treeroute v1": "treeroute", "Ridge": "rival_ridge", "Random forest": "rival_rf", "LightGBM": "rival_lgbm",
      "Tweedie booster": "rival_lgbm_tweedie", "Absolute-error booster": "rival_hgb_l1", "BARDL": "rival_bardl_h1",
      "BARDL\u2021": "rival_bardl_h1"}
AW3H = {"Spearman over J": "spearman", "Spearman, top-20 union": "spearman_top20_union", "Kendall's tau-b": "kendall_tau_b",
        "Jaccard top 5": "jaccard_top5", "Jaccard top 10": "jaccard_top10", "Jaccard top 20": "jaccard_top20",
        "RBO, p = 0.9": "rbo_p0.9", "RBO, p = 0.95": "rbo_p0.95", "Share distance (TV)": "tvd",
        "Family-share distance (TV)": "tvd_family", "Family-share distance (TV)\u00a7": "tvd_family",
        "Sign agreement, top-10 union (signs)\u2020": "sign_agreement_top10"}
T9H = {"W [95% CI]": "kendall_w",
       "Spearman of treeroute v1 with its same-link rivals: median [95% CI] (range)": "spearman_top20_union_median",
       "RBO with the rivals' consensus, p = 0.9 [95% CI]": "rbo_vs_consensus",
       "Own-history share, treeroute v1 [95% CI]": "own_history_treeroute",
       "Own-history share, median of the rivals\u1d9c [95% CI]": "own_history_median_rivals"}
S319H = {"Frame rows\u1d43": "frame_rows", "Sample rows": "sample_rows", "Regions": "regions", "Locations\u1d47": "locations",
         "Background rows per sample row\u1d9c": "background_rows", "Background pairs": "background_pairs",
         "Feature level: players / J / structural zeros": "feature", "Variable level: players / J / structural zeros": "variable"}
S320H = {"Rows checked\u1d43": "rows_checked", "Bit-identical rows, pre-clip / clipped\u1d43": "bit_identical",
         "Largest absolute difference, rebuilt \u2212 saved (pre-clip, y units)": "max_abs_diff", "S-EXACT": "s_exact",
         "Largest additivity error, feature / variable level": "additivity", "S-ZERO violations": "s_zero_violations"}
S330H = {"Background pairs": "pairs", "Total seconds": "total_seconds", "Tree-SHAP seconds": "tree_shap_seconds", "Result": "result"}
PARTCOL = {"value": "value", "ci_low": "ci_low", "ci_high": "ci_high", "n_finite": "finite_replicates", "signs": "signs_compared"}

# header of each table row line
header_of = {}
cur = None
for i, ln in enumerate(lines):
    if ln.startswith("| ") and i + 1 < len(lines) and lines[i + 1].startswith("|---"):
        cur = ln[2:-2].split(" | ")
    elif ln.startswith("| ") and cur is not None:
        header_of[i + 1] = cur
    elif not ln.startswith("|"):
        cur = None if ln and not ln.startswith("|") else cur

imp_cache = {}


def ranking(p, L, m):
    key = (p, L, m)
    if key not in imp_cache:
        df = pd.read_parquet(SHAP + "\\out\\" + p + "\\lead_0\\compare\\importance.parquet")
        d = df[(df["level"] == L) & (df["model"] == m) & (df["active"])]
        rows = sorted(zip(d["mean_abs"].tolist(), d["player"].tolist()), key=lambda t: (-t[0], t[1]))
        imp_cache[key] = [t[1] for t in rows]
    return imp_cache[key]


def terms(sel):
    return dict(t.split("=", 1) for t in sel.split("; "))


by_line = {}
for e in E:
    by_line.setdefault(e["line"], []).append(e)
for no, es in by_line.items():
    ln = lines[no - 1]
    is_row = ln.startswith("| ")
    cells = ln[2:-2].split(" | ") if is_row else [ln]
    hdr = header_of.get(no) if is_row else None
    ci, pos = 0, 0
    for e in es:
        while not (cells[ci] == e["cell"] and cells[ci].find(e["printed"], pos) >= 0):
            ci += 1
            pos = 0
        pos = cells[ci].find(e["printed"], pos) + len(e["printed"])
        t, pn, row, col, part, src, sel = e["table"], e["panel"], e["row"], e["column"], e["part"], e["source"], e["selector"]
        h = hdr[ci] if hdr else None
        try:
            if row == "note":
                continue
            if t == "9":
                assert T9H[h] == col and PNAME[cells[0]] == row, "column"
                if row != "fire" or col == "kendall_w":
                    assert ("\\" + row + "\\") in src and src.endswith("AW4_main_row.json"), "src"
                    first = sel.split(".")[0].split("[")[0] if not sel.startswith("[") else sel.split("]")[0] + "]"
                    want = {"kendall_w": "kendall_w", "spearman_top20_union_median": "treeroute_vs_same_link_rivals_median_spearman_top20_union",
                            "rbo_vs_consensus": '["rbo_vs_consensus_p0.9"]', "own_history_treeroute": "own_history_share_treeroute",
                            "own_history_median_rivals": "own_history_share_median_rival"}[col]
                    assert first == want, "selector head %r" % first
                else:
                    assert sel.startswith("problems.fire.main_row.own_history_share_treeroute."), "fire A"
            elif t == "S3.19":
                assert S319H[h] == col and PNAME[cells[0]] == row and ("\\" + row + "\\" in src or src.endswith("SAMPLE_REGISTER.txt")), "S3.19"
            elif t == "S3.20":
                p, m = row.split(":")
                assert S320H[h] == col and PNAME[cells[0]] == p, "S3.20 column"
                assert ("\\" + p + "\\") in src, "S3.20 src"
                if col in ("additivity", "s_zero_violations"):
                    assert src.endswith("\\" + m + "\\meta.json"), "S3.20 meta"
                elif m == "treeroute":
                    assert src.endswith("gates.json"), "S3.20 gates"
                else:
                    assert ("\\" + m + "\\") in src, "S3.20 model src"
            elif t in ("S3.21", "S3.22"):
                assert PNAME[h] == col and ("\\" + col + "\\") in src or (t == "S3.22" and col == "fire" and src.endswith("results.json")), "S3.21/22"
                if t == "S3.22" and row == "spearman_per_rival":
                    tm = terms(sel)
                    assert tm["statistic"] == "spearman_top20_union" and tm["level"] == "variable" and {tm["model_a"], tm["model_b"]} == {part, "treeroute"}, "per rival"
                if t == "S3.22" and row == "own_history_per_rival":
                    tm = terms(sel)
                    assert tm["model"] == part and tm["family"] == "own history", "own per rival"
            elif t in TID2P:
                p = TID2P[t]
                assert ("\\" + p + "\\") in src or sel.startswith("problems." + p + "."), "AW3 problem"
                if pn in ("a", "b"):
                    assert AW3H[h] == col, "AW3 column %r %r" % (h, col)
                    a, b = row.split("|")
                    L = "variable" if pn == "a" else "feature"
                    if src.endswith("results.json"):
                        assert sel == 'problems.%s.levels.%s.pairs["%s"].sign_agreement.%s' % (p, L, row, part), "A sign"
                    else:
                        tm = terms(sel)
                        assert tm["statistic"] == col and tm["model_a"] == a and tm["model_b"] == b, "pair stat"
                        assert tm["level"] == ("variable" if col == "tvd_family" else L), "pair level"
                        assert tm["column"] == PARTCOL[part], "pair part"
                    pt = cells[0].replace("\u2021", "")
                    names = {"treeroute v1": "treeroute", "Ridge": "rival_ridge", "random forest": "rival_rf",
                             "LightGBM": "rival_lgbm", "Tweedie booster": "rival_lgbm_tweedie",
                             "absolute-error booster": "rival_hgb_l1", "BARDL": "rival_bardl_h1"}
                    x, y = pt.split(" vs ")
                    assert sorted([names[x], names[y]]) == [a, b], "pair text"
                elif pn == "c":
                    assert {"Variable level": "variable", "Feature level": "feature"}[h] == col, "c column"
                    field = {"kendall_w": "kendall_w_main_set", "mean_pairwise_spearman": "mean_pairwise_spearman_main_set"}.get(row)
                    if field:
                        assert sel.startswith(col + "." + field + "."), "c field"
                    else:
                        assert sel == col + ".stability_under_region_resampling." + row.split(":")[1], "c stability"
                elif pn in ("d", "e"):
                    assert MH[h] == col, "d/e column"
                    L = "variable" if pn == "d" else "feature"
                    if row.startswith("rank_"):
                        k = int(row.split("_")[1])
                        tm = terms(sel)
                        assert tm["level"] == L and tm["model"] == col and tm["column"] == "share", "d/e sel"
                        assert ranking(p, L, col)[k - 1] == tm["player"], "rank order"
                        assert cells[ci].startswith("`" + tm["player"] + "` "), "rank name"
                        assert cells[0] == str(k), "rank label"
                    else:
                        assert sel == L + ".nonzero_players." + col, "nonzero"
                elif pn == "f":
                    tm = terms(sel)
                    assert MH[h] == col and tm["model"] == col and tm["family"] == row, "f"
                    assert part == "share", "f part (version 2, G1)"  # added for version 2 of the spec
                elif pn == "g":
                    assert MH[h] == col, "g column"
                    if row.startswith("rank_"):
                        k = int(row.split("_")[1])
                        assert sel == "nonzero_forecast_rows.%s.top10[%d][1]" % (col, k - 1) and cells[0] == str(k), "g rank"
                    else:
                        assert sel == "nonzero_forecast_rows.%s.rows" % col, "g rows"
            elif t == "S3.28":
                assert PNAME[h] == col, "S3.28 column"
                L = "variable" if pn == "a" else "feature"
                if row == "n_nonzero":
                    assert sel == "b1.%s.%s.importance.n_nonzero.value" % (col, L), "n_nonzero"
                elif row == "sign_counts":
                    k = {"determined": "sign_n_determined", "agree": "sign_n_agree"}[part]
                    assert sel == "b1.%s.%s.pair_main_b1.%s.value" % (col, L, k), "sign counts"
                else:
                    LL = "variable" if row == "tv_family_shares" else L
                    pp = "value" if part == "count" else part
                    assert sel == "b1.%s.%s.pair_main_b1.%s.%s" % (col, LL, row, pp), "S3.28 sel"
            elif t == "S3.29":
                assert PNAME[h] == col, "S3.29 column"
                if pn == "a":
                    assert sel == "b1.%s.variable.families.%s.%s" % (col, row, part), "S3.29 a"
                elif pn == "b":
                    if row == "top3":
                        i = int(part.split("_")[1]) - 1
                        assert sel == "b1.%s.variable.top3[%d][1]" % (col, i), "top3"
                    else:
                        assert sel == "b1.%s.variable.own_history_share.%s" % (col, part), "own"
                else:
                    L = "variable" if pn == "c" else "feature"
                    k = int(row.split("_")[1])
                    assert sel == "b1.%s.%s.top10[%d][1]" % (col, L, k - 1) and cells[0] == str(k), "S3.29 c/d"
            elif t == "S3.30":
                assert S330H[h] == col, "S3.30 column"
                if pn == "a":
                    assert PNAME[cells[0]] == row and src.endswith("tr_shap_%s_lead0.log" % row), "S3.30 a"
                else:
                    assert sel.startswith("b1.defo.identity."), "S3.30 b"
            else:
                raise AssertionError("unknown table")
        except (AssertionError, KeyError, ValueError, IndexError) as ex:
            fails.append("line %d %s %s %s %s %s: %r" % (no, t, pn, row, col, part, ex))

print("entries", len(E), "placement failures:", len(fails))
for m in fails[:30]:
    print("FAIL", m)
