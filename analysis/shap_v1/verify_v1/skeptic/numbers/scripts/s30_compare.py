"""Skeptic (numbers lens): put my numbers beside A's, B's and the official ones (single named official files)."""
import os, sys, json
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s_lib as L

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
OUT = os.path.join(V, "skeptic", "numbers", "work")
A = json.load(open(os.path.join(V, "A", "results.json"), encoding="utf-8"))
Bj = json.load(open(os.path.join(V, "B", "results.json"), encoding="utf-8"))
ME = json.load(open(os.path.join(OUT, "s10_main.json"), encoding="utf-8"))


def comp(p):
    return os.path.join(L.SHAP, "out", p, "lead_0", "compare")


rows = []


def add(key, mine, a, b, off):
    def f(x):
        if isinstance(x, dict):
            return x
        return x
    vals = [mine, a, b, off]
    nums = [v for v in vals if isinstance(v, (int, float)) and v is not None]
    worst = None
    if isinstance(mine, (int, float)) and mine is not None:
        dd = [abs(mine - v) for v in vals[1:] if isinstance(v, (int, float)) and v is not None]
        worst = max(dd) if dd else None
    rows.append(dict(key=key, mine=mine, A=a, B=b, official=off, max_abs_diff_mine_vs_others=worst))


def ivs(prefix, mine, a, b, off):
    for k in ["value", "ci_low", "ci_high", "n_finite"]:
        add(prefix + "/" + k, (mine or {}).get(k), (a or {}).get(k) if isinstance(a, dict) else None,
            (b or {}).get(k) if isinstance(b, dict) else None, (off or {}).get(k) if isinstance(off, dict) else None)


def off_iv(o):
    """official {value, ci:[low, high, finite]} -> interval dict"""
    if o is None:
        return None
    ci = o.get("ci") or [None, None, None]
    return dict(value=o.get("value"), ci_low=ci[0], ci_high=ci[1], n_finite=ci[2] if len(ci) > 2 else None)


for p in ["ndvi", "pm25"]:
    mr = json.load(open(os.path.join(comp(p), "AW4_main_row.json"), encoding="utf-8"))
    me = ME[p]
    a = A["problems"][p]["main_row"]
    b = Bj["problems"][p]["main_row"]
    print(p, "official AW4_main_row keys:", sorted(mr.keys()))
    ivs(p + "/main_row/kendall_w", me["kendall_w"], a["kendall_w"], b["kendall_w"], off_iv(mr.get("kendall_w")))
    om = mr.get("treeroute_vs_same_link_rivals_median_spearman_top20_union")
    ivs(p + "/main_row/spearman_top20_union_median", me["spearman_top20_union_median"], a["spearman_top20_union_median"],
        b["spearman_top20_union_median"], off_iv(om))
    add(p + "/main_row/spearman_top20_union_min/value", me["spearman_top20_union_min"]["value"],
        a["spearman_top20_union_min"]["value"], b["spearman_top20_union_min"]["value"], (om or {}).get("range", [None, None])[0])
    add(p + "/main_row/spearman_top20_union_max/value", me["spearman_top20_union_max"]["value"],
        a["spearman_top20_union_max"]["value"], b["spearman_top20_union_max"]["value"], (om or {}).get("range", [None, None])[1])
    for k in ["ci_low", "ci_high", "n_finite"]:
        add(p + "/main_row/spearman_top20_union_min/" + k, me["spearman_top20_union_min"][k], a["spearman_top20_union_min"].get(k),
            b["spearman_top20_union_min"].get(k), None)
        add(p + "/main_row/spearman_top20_union_max/" + k, me["spearman_top20_union_max"][k], a["spearman_top20_union_max"].get(k),
            b["spearman_top20_union_max"].get(k), None)
    for r, v in me["spearman_top20_union_per_rival"].items():
        add(p + "/main_row/spearman_top20_union_per_rival/" + r, v, a["spearman_top20_union_per_rival"].get(r),
            b["spearman_top20_union_per_rival"].get(r), None)
    ivs(p + "/main_row/rbo_p090_vs_consensus", me["rbo_p090_vs_consensus"], a["rbo_p090_vs_consensus"],
        b["rbo_p090_vs_consensus"], off_iv(mr.get("rbo_vs_consensus_p0.9")))
    add(p + "/main_row/treeroute_top3/names", [x[0] for x in me["treeroute_top3"]], [x[0] for x in a["treeroute_top3"]],
        [x[0] for x in b["treeroute_top3"]], mr.get("treeroute_top3"))
    for i in range(3):
        add(p + "/main_row/treeroute_top3/share%d" % i, me["treeroute_top3"][i][1], a["treeroute_top3"][i][1],
            b["treeroute_top3"][i][1], None)
    add(p + "/main_row/consensus_top3/names", [x[0] for x in me["consensus_top3"]], [x[0] for x in a["consensus_top3"]],
        [x[0] for x in b["consensus_top3"]], mr.get("consensus_top3"))
    for i in range(3):
        add(p + "/main_row/consensus_top3/share%d" % i, me["consensus_top3"][i][1], a["consensus_top3"][i][1],
            b["consensus_top3"][i][1], None)
    ivs(p + "/main_row/own_history_share_treeroute", me["own_history_share_treeroute"], a["own_history_share_treeroute"],
        b["own_history_share_treeroute"], off_iv(mr.get("own_history_share_treeroute")))
    ivs(p + "/main_row/own_history_share_median_rival", me["own_history_share_median_rival"],
        a["own_history_share_median_rival"], b["own_history_share_median_rival"], off_iv(mr.get("own_history_share_median_rival")))
    with open(os.path.join(OUT, "official_AW4_main_row_%s.json" % p), "w", encoding="utf-8") as f:
        json.dump(mr, f, indent=1)

# defo W, both levels
pl = L.per_lead("defo")
for level in ["feature", "variable"]:
    o = pl[level].get("kendall_w_main_set")
    o2 = None if o is None else dict(value=o.get("value"), ci_low=(o.get("ci") or [None, None])[0],
                                     ci_high=(o.get("ci") or [None, None])[1], n_finite=o.get("finite_replicates"))
    ivs("defo/%s/kendall_w" % level, ME["defo"][level]["kendall_w"],
        A["problems"]["defo"]["levels"][level]["per_problem"]["kendall_w"],
        Bj["problems"]["defo"]["levels"][level]["per_problem"]["kendall_w"], o2)
    o = pl[level].get("mean_pairwise_spearman_main_set")
    o2 = None if o is None else dict(value=o.get("value"), ci_low=(o.get("ci") or [None, None])[0],
                                     ci_high=(o.get("ci") or [None, None])[1], n_finite=o.get("finite_replicates"))
    ivs("defo/%s/mean_pairwise_spearman" % level, ME["defo"][level]["mean_pairwise_spearman"],
        A["problems"]["defo"]["levels"][level]["per_problem"]["mean_pairwise_spearman"],
        Bj["problems"]["defo"]["levels"][level]["per_problem"]["mean_pairwise_spearman"], o2)
    add("defo/%s/active_set/n_J" % level, ME["defo"][level]["J_n"],
        A["problems"]["defo"]["levels"][level]["active_set"]["n_J"]["value"],
        Bj["problems"]["defo"]["levels"][level]["active_set"]["n_J"]["value"], pl[level].get("active"))

# coral treeroute feature-level shares and top 10
imp = pd.read_parquet(os.path.join(comp("coral"), "importance.parquet"))
oi = imp[(imp["level"] == "feature") & (imp["model"] == "treeroute")].set_index("player")
me = ME["coral"]
am = A["problems"]["coral"]["levels"]["feature"]["models"]["treeroute"]
bm = Bj["problems"]["coral"]["levels"]["feature"]["models"]["treeroute"]
for j, v in me["shares"].items():
    ivs("coral/feature/treeroute/share/" + j, v, am["players"][j]["share"], bm["players"][j]["share"],
        dict(value=float(oi.loc[j, "share"])) if j in oi.index else None)
for j, v in me["I"].items():
    add("coral/feature/treeroute/I/" + j, v, am["players"][j]["I"]["value"], bm["players"][j]["I"]["value"],
        float(oi.loc[j, "mean_abs"]) if j in oi.index else None)
act = oi[oi["active"]].reset_index().sort_values(["share", "player"], ascending=[False, True])
add("coral/feature/treeroute/top10/names", [x[0] for x in me["top10"]], [x[0] for x in am["top10"]],
    [x[0] for x in bm["top10"]], act["player"].head(10).tolist())
for i in range(10):
    add("coral/feature/treeroute/top10/share%d" % i, me["top10"][i][1], am["top10"][i][1], bm["top10"][i][1],
        float(act["share"].iloc[i]))
add("coral/feature/active_set/n_J", me["J_n"], A["problems"]["coral"]["levels"]["feature"]["active_set"]["n_J"]["value"],
    Bj["problems"]["coral"]["levels"]["feature"]["active_set"]["n_J"]["value"], L.per_lead("coral")["feature"].get("active"))
add("coral/feature/active_set/structural_zeros", me["structural_zeros"],
    A["problems"]["coral"]["levels"]["feature"]["active_set"]["structural_zeros"],
    Bj["problems"]["coral"]["levels"]["feature"]["active_set"]["structural_zeros"],
    L.per_lead("coral")["feature"].get("structural_zero"))

with open(os.path.join(OUT, "s30_compare.json"), "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=1)
bad = 0
for r in rows:
    m, a, b, o = r["mine"], r["A"], r["B"], r["official"]
    flag = ""
    for x in (a, b, o):
        if x is None:
            continue
        if isinstance(m, (int, float)) and isinstance(x, (int, float)):
            if abs(m - x) > 1e-9 * max(1.0, abs(m)):
                flag = "  <-- DIFF"
        elif m != x:
            flag = "  <-- DIFF"
    if flag:
        bad += 1
    print(r["key"], "| mine", m, "| A", a, "| B", b, "| off", o, flag)
print("rows", len(rows), "with a difference", bad)
