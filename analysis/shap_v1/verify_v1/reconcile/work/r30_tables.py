"""Tables (printed) of the main row (official vs A vs B) and of B1 (A and B side by side).

Prints only. Every official open is logged (rlib).
"""
import json
import math
import os
import sys

sys.path.insert(0, r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile")
import rlib as R  # noqa: E402

WHO = "work\\r30_tables.py"
RA, _ = R.load_results("A")
RB, _ = R.load_results("B")


def f(v, nd=4):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return str(v)
    if nd == "raw":
        return repr(v)
    if isinstance(v, int):
        return "%d" % v
    if isinstance(v, float) and float(v).is_integer() and abs(v) < 1e6 and nd != "raw":
        return "%d" % int(v)
    return ("%." + str(nd) + "f") % v


def ivs(o, nd=4):
    if o is None:
        return "null"
    s = f(o["value"], nd)
    if o.get("ci_low") is None and o.get("ci_high") is None:
        return s + (" (n=%s)" % o["n_finite"] if o.get("n_finite") is not None else "")
    return "%s [%s, %s] (n=%s)" % (s, f(o["ci_low"], nd), f(o["ci_high"], nd), o["n_finite"])


def same(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return all(R.num_eq(a.get(k), b.get(k), exact=(k == "n_finite")) for k in R.IV_PARTS)
    return R.num_eq(a, b)


L = []
# ---- main row, official vs A vs B
L.append("## Main-text row (variable level): official values, with A and B")
L.append("")
L.append("| problem | number | official | A equal | B equal |")
L.append("|---|---|---|---|---|")
for p in R.PROBLEMS:
    mr = R.read_official_json(os.path.join(R.compare_dir(p), "AW4_main_row.json"), WHO)
    a, b = RA["problems"][p]["main_row"], RB["problems"][p]["main_row"]

    def row(name, off, ka):
        L.append("| %s | %s | %s | %s | %s |" % (p, name, off, same_disp(a.get(ka), off_obj[0]),
                                                 same_disp(b.get(ka), off_obj[0])))

    def same_disp(x, o):
        if o is None:
            return "(no official value)"
        if x is None and o.get("value") is None and o.get("ci_low") is None and o.get("ci_high") is None:
            return "yes (undefined: null; the official file has NaN with %s finite replicates)" % o.get("n_finite")
        return "yes" if same(x, o) else "NO: %s" % (ivs(x) if isinstance(x, dict) else "null")

    def off_iv(d):
        if d is None:
            return None
        v = d["value"]
        v = None if (isinstance(v, float) and math.isnan(v)) else v
        lo, hi, n = d["ci"][0], d["ci"][1], d["ci"][2]
        lo = None if (isinstance(lo, float) and math.isnan(lo)) else lo
        hi = None if (isinstance(hi, float) and math.isnan(hi)) else hi
        return {"value": v, "ci_low": lo, "ci_high": hi, "n_finite": n}

    off_obj = [off_iv(mr["kendall_w"])]
    row("Kendall's W", ivs(off_obj[0]), "kendall_w")
    sp = mr.get("treeroute_vs_same_link_rivals_median_spearman_top20_union")
    if sp:
        off_obj = [off_iv(sp)]
        row("median top-20-union Spearman vs rivals", ivs(off_obj[0]), "spearman_top20_union_median")
        off_obj = [{"value": sp["range"][0], "ci_low": None, "ci_high": None, "n_finite": None}]
        L.append("| %s | range min / max | %s / %s | %s | %s |" % (
            p, f(sp["range"][0]), f(sp["range"][1]),
            "yes" if (R.num_eq(a["spearman_top20_union_min"]["value"], sp["range"][0]) and
                      R.num_eq(a["spearman_top20_union_max"]["value"], sp["range"][1])) else "NO",
            "yes" if (R.num_eq(b["spearman_top20_union_min"]["value"], sp["range"][0]) and
                      R.num_eq(b["spearman_top20_union_max"]["value"], sp["range"][1])) else "NO"))
        off_obj = [off_iv(mr["rbo_vs_consensus_p0.9"])]
        row("RBO (p 0.9) vs consensus", ivs(off_obj[0]), "rbo_p090_vs_consensus")
        for k, ka in (("treeroute_top3", "treeroute_top3"), ("consensus_top3", "consensus_top3")):
            na = [x[0] for x in a[ka]] if a.get(ka) else None
            nb = [x[0] for x in b[ka]] if b.get(ka) else None
            L.append("| %s | %s | %s | %s | %s |" % (p, k.replace("_", " "), ", ".join(mr[k]),
                                                     "yes" if na == mr[k] else "NO", "yes" if nb == mr[k] else "NO"))
        off_obj = [off_iv(mr["own_history_share_treeroute"])]
        row("own-history share, treeroute", ivs(off_obj[0]), "own_history_share_treeroute")
        off_obj = [off_iv(mr["own_history_share_median_rival"])]
        row("own-history share, median rival", ivs(off_obj[0]), "own_history_share_median_rival")
    else:
        L.append("| %s | treeroute top 3 | (not written by compare_shap.py) | A: %s | B: %s |" % (
            p, ", ".join("%s %s" % (x[0], f(x[1])) for x in a["treeroute_top3"]),
            ", ".join("%s %s" % (x[0], f(x[1])) for x in b["treeroute_top3"])))
        L.append("| %s | own-history share, treeroute | (not written by compare_shap.py) | A: %s | B: %s |" % (
            p, ivs(a["own_history_share_treeroute"]), ivs(b["own_history_share_treeroute"])))
L.append("")

# ---- B1, A and B side by side
L.append("## B1 (item 9): A and B side by side")
L.append("")
idA, idB = RA["b1"]["defo"]["identity"], RB["b1"]["defo"]["identity"]
L.append("### Defo identity check (first)")
L.append("")
L.append("| number | A | B |")
L.append("|---|---|---|")
for k in ("max_abs_diff_phi", "max_abs_diff_phiv", "same_rows", "same_players", "same_variables", "n_rows_main",
          "n_rows_b1", "n_players_main", "n_players_b1", "n_variables_main", "n_variables_b1", "as_expected",
          "pairs_log", "pairs_meta", "total_seconds_log", "total_seconds_done_json", "tree_shap_seconds_log",
          "tree_shap_seconds_meta", "log_setup_line_number", "log_done_line_number"):
    va, vb = idA.get(k), idB.get(k)
    L.append("| %s | %s | %s |" % (k, f(va, "raw") if isinstance(va, float) else va, f(vb, "raw") if isinstance(vb, float) else vb))
L.append("")
for p in ("fire", "pm25", "ndvi"):
    A1, B1 = RA["b1"][p], RB["b1"][p]
    L.append("### %s" % p)
    L.append("")
    ra, rb = A1["run"], B1["run"]
    L.append("Run: pairs %s (log) / %s (meta); total %s s (log) / %s s (done record); tree SHAP %s s (log) / %s s "
             "(meta); merged context columns in the main run %d, in the B1 run %d, summed %d (A) / %d (B). A and B "
             "give the same run facts: %s." % (
                 ra["pairs_log"], ra["pairs_meta"], ra["total_seconds_log"], ra["total_seconds_done_json"],
                 ra["tree_shap_seconds_log"], ra["tree_shap_seconds_meta"], len(ra["duplicates_merged_main"]),
                 len(ra["duplicates_merged_b1"]), len(ra["context_columns_summed"]), len(rb["context_columns_summed"]),
                 "yes" if all(ra[k] == rb[k] for k in ("pairs_log", "pairs_meta", "total_seconds_log",
                                                         "total_seconds_done_json", "tree_shap_seconds_log",
                                                         "tree_shap_seconds_meta", "log_setup_line_number",
                                                         "log_done_line_number")) else "NO"))
    L.append("")
    L.append("| level | number | A | B | equal |")
    L.append("|---|---|---|---|---|")
    for lev in ("feature", "variable"):
        ia, ib = A1[lev]["importance"], B1[lev]["importance"]
        for k in ("n_nonzero", "n_nonzero_before_merge"):
            if k in ia:
                L.append("| %s | %s | %s | %s | %s |" % (lev, k, ivs(ia[k], 2), ivs(ib[k], 2),
                                                         "yes" if same(ia[k], ib[k]) else "NO"))
        pa, pb = A1[lev]["pair_main_b1"], B1[lev]["pair_main_b1"]
        L.append("| %s | pair J size | %s | %s | %s |" % (lev, f(pa["n_J"]["value"]), f(pb["n_J"]["value"]),
                                                         "yes" if same(pa["n_J"], pb["n_J"]) else "NO"))
        for k in ("spearman_J", "spearman_top20_union", "kendall_tau_b", "jaccard_top5", "jaccard_top10",
                  "jaccard_top20", "rbo_p090", "rbo_p095", "tv_shares", "tv_family_shares", "sign_agreement",
                  "sign_n_determined", "sign_n_agree"):
            xa, xb = pa.get(k), pb.get(k)
            if xa is None and xb is None:
                continue
            L.append("| %s | %s | %s | %s | %s |" % (lev, k, ivs(xa), ivs(xb), "yes" if (
                xa is not None and xb is not None and same(xa, xb)) else "NO (open choice C15)" if k ==
                "tv_family_shares" else "NO"))
        ta = [x[0] for x in A1[lev]["top10"]]
        tb = [x[0] for x in B1[lev]["top10"]]
        L.append("| %s | top 10 | %s | %s | %s |" % (lev, ", ".join(ta), "(same names and order)" if tb == ta else
                                                     ", ".join(tb), "yes" if (ta == tb and all(
                                                         R.num_eq(x[1], y[1]) for x, y in zip(A1[lev]["top10"],
                                                                                               B1[lev]["top10"])))
                                                     else "NO"))
        if lev == "variable":
            for fam in R.FAMILY_KEYS:
                xa, xb = A1[lev]["families"].get(fam), B1[lev]["families"].get(fam)
                L.append("| variable | family share %s | %s | %s | %s |" % (fam.replace("_", " "), ivs(xa), ivs(xb),
                                                                           "yes" if same(xa, xb) else "NO"))
            L.append("| variable | top 3 | %s | %s | %s |" % (
                ", ".join("%s %s" % (x[0], f(x[1])) for x in A1[lev]["top3"]),
                ", ".join("%s %s" % (x[0], f(x[1])) for x in B1[lev]["top3"]),
                "yes" if ([x[0] for x in A1[lev]["top3"]] == [x[0] for x in B1[lev]["top3"]] and all(
                    R.num_eq(x[1], y[1]) for x, y in zip(A1[lev]["top3"], B1[lev]["top3"]))) else "NO"))
            L.append("| variable | own-history share | %s | %s | %s |" % (
                ivs(A1[lev]["own_history_share"]), ivs(B1[lev]["own_history_share"]),
                "yes" if same(A1[lev]["own_history_share"], B1[lev]["own_history_share"]) else "NO"))
    L.append("")
print("\n".join(L))          # printed only (no table file is kept)
