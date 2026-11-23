"""Skeptic (numbers lens): spot check of S3.13 pair statistics (variable level, full sample) for two pairs in NDVI
and PM2.5, mine vs A, B and the official pairs.parquet (single named file)."""
import os, sys, json
import numpy as np
import pandas as pd
from scipy.stats import kendalltau
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s_lib as L

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
OUT = os.path.join(V, "skeptic", "numbers", "work")
GL = json.load(open(os.path.join(OUT, "s01_global_coral_fire_pm25_ndvi.json"), encoding="utf-8"))
A = json.load(open(os.path.join(V, "A", "results.json"), encoding="utf-8"))
Bj = json.load(open(os.path.join(V, "B", "results.json"), encoding="utf-8"))
lines = []


def show(key, mine, a, b, o):
    flag = ""
    for x in (a, b, o):
        if x is None:
            continue
        if isinstance(mine, (int, float)) and isinstance(x, (int, float)):
            if not (np.isnan(mine) and np.isnan(x)) and abs(mine - x) > 1e-9 * max(1.0, abs(mine)):
                flag = "  <-- DIFF"
        elif mine != x:
            flag = "  <-- DIFF"
    s = "%s | mine %r | A %r | B %r | off %r%s" % (key, mine, a, b, o, flag)
    lines.append(s)
    print(s)


for p, pairs in [("ndvi", [("rival_lgbm", "treeroute"), ("rival_bardl_h1", "treeroute")]),
                 ("pm25", [("rival_ridge", "treeroute"), ("rival_lgbm", "rival_rf")])]:
    pl = L.per_lead(p)
    d, _ = L.load_draws(p)
    data, g0 = {}, None
    for m in pl["models"]:
        _, gr, _, ph = L.load(p, m, "variable")
        g0 = gr if g0 is None else g0
        data[m] = ph
    R = L.Regions(g0, d)
    J, _ = L.active_set(data, R)
    imps = {m: L.imp(data[m], J, R) for m in pl["models"]}
    pq_ = pd.read_parquet(os.path.join(L.SHAP, "out", p, "lead_0", "compare", "pairs.parquet"))
    for a_, b_ in pairs:
        key = a_ + "|" + b_
        Ia, Ib = imps[a_]["I"], imps[b_]["I"]
        sa, sb = L.shares_of(Ia), L.shares_of(Ib)
        st = {}
        st["spearman"] = float(L.spearman(Ia, Ib))
        st["spearman_top20_union"] = L.spearman_top20_union(Ia, Ib)[0]
        st["kendall_tau_b"] = float(kendalltau(Ia, Ib).statistic)
        st["jaccard_top5"] = len(L.topk_set(Ia, 5) & L.topk_set(Ib, 5)) / len(L.topk_set(Ia, 5) | L.topk_set(Ib, 5))
        st["jaccard_top10"] = len(L.topk_set(Ia, 10) & L.topk_set(Ib, 10)) / len(L.topk_set(Ia, 10) | L.topk_set(Ib, 10))
        st["rbo_p0.9"] = float(L.rbo(Ia, Ib, 0.9)[0])
        st["rbo_p0.95"] = float(L.rbo(Ia, Ib, 0.95)[0])
        st["tvd"] = float(L.tv(sa, sb))
        Fa, _ = L.family_imp(data[a_], set(GL[p]["global_vars"]), R)
        Fb, _ = L.family_imp(data[b_], set(GL[p]["global_vars"]), R)
        st["tvd_family"] = float(L.tv(L.shares_of(Fa), L.shares_of(Fb)))
        # sign agreement
        det = {}
        for m in (a_, b_):
            lo = np.percentile(imps[m]["Sd"], 2.5, axis=0)
            hi = np.percentile(imps[m]["Sd"], 97.5, axis=0)
            det[m] = (lo > 0) | (hi < 0)
        U = sorted(L.topk_set(Ia, 10) | L.topk_set(Ib, 10))
        both = [j for j in U if det[a_][j] and det[b_][j]]
        agree = sum(np.sign(imps[a_]["S"][j]) == np.sign(imps[b_]["S"][j]) for j in both)
        st["sign_agreement_top10"] = (agree / len(both)) if both else float("nan")
        st["signs_compared"] = len(both)
        offrows = pq_[(pq_["level"] == "variable") & (pq_["model_a"] == a_) & (pq_["model_b"] == b_)].set_index("statistic")
        amap = {"spearman": "spearman_J", "spearman_top20_union": "spearman_top20_union", "kendall_tau_b": "kendall_tau_b",
                "jaccard_top5": "jaccard_top5", "jaccard_top10": "jaccard_top10", "rbo_p0.9": "rbo_p090", "rbo_p0.95": "rbo_p095",
                "tvd": "tv_shares", "tvd_family": "tv_family_shares", "sign_agreement_top10": "sign_agreement",
                "signs_compared": "sign_n_determined"}
        Ap = A["problems"][p]["levels"]["variable"]["pairs"][key]
        Bp = Bj["problems"][p]["levels"]["variable"]["pairs"][key]
        for k, v in st.items():
            if k == "signs_compared":
                ov = int(offrows.loc["sign_agreement_top10", "signs_compared"]) if "sign_agreement_top10" in offrows.index else None
            else:
                ov = float(offrows.loc[k, "value"]) if k in offrows.index else None
            av = (Ap.get(amap[k]) or {}).get("value") if isinstance(Ap.get(amap[k]), dict) else Ap.get(amap[k])
            bv = (Bp.get(amap[k]) or {}).get("value") if isinstance(Bp.get(amap[k]), dict) else Bp.get(amap[k])
            show("%s/variable/%s/%s" % (p, key, k), v, av, bv, ov)
open(os.path.join(OUT, "s12_pairs_spot.out.txt"), "w", encoding="utf-8").write("\n".join(lines))
print("differences:", sum("DIFF" in s for s in lines), "of", len(lines))
