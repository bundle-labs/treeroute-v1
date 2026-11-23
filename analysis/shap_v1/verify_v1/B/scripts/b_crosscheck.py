# Implementer B, round 14: a slow, loop-based re-computation of a sample of my own numbers (full sample and single
# draws), written separately from b_lib's vectorised paths, compared with V\B\results.json and V\B\draws\*.npz.
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy import stats

SHAP = Path(r"D:\treeroute\analysis\shap_v1")
VB = Path(r"D:\treeroute\analysis\shap_v1\verify_v1\B")
res = json.loads((VB / "results.json").read_text(encoding="utf-8"))
bad = []


def close(name, a, b, tol=1e-12):
    ok = (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= tol * max(1.0, abs(b)))
    print("%-78s %s  mine=%r  check=%r" % (name, "ok" if ok else "DIFF", a, b))
    if not ok:
        bad.append(name)


def load(p, m, level):
    path = SHAP / "out" / p / "lead_0" / m / "rows.parquet"
    pref = "phi__" if level == "feature" else "phiv__"
    t = pq.read_table(path).to_pandas().sort_values("row")
    cols = {c[len(pref):]: c for c in t.columns if c.startswith(pref)}
    return t, cols


def imp_loop(t, cols, J, regions_list, absval=True, rows_mask=None):
    """Importance by explicit loops over a list of drawn regions (with repetition)."""
    out = {}
    tt = t if rows_mask is None else t[rows_mask]
    for j in J:
        vals = []
        for r in regions_list:
            sub = tt[tt["group"] == r]
            if len(sub) == 0:
                continue
            x = sub[cols[j]].to_numpy() if j in cols else np.zeros(len(sub))
            vals.append(np.mean(np.abs(x)) if absval else np.mean(x))
        out[j] = float(np.mean(vals)) if vals else float("nan")
    return out


def rank_order(imp, J):
    return sorted(J, key=lambda j: (-imp[j], j))


def rbo_eq32(la, lb, p):
    l = len(la)
    Xd = [len(set(la[:d]) & set(lb[:d])) for d in range(1, l + 1)]
    return (1 - p) / p * sum(Xd[d - 1] / d * p ** d for d in range(1, l + 1)) + (Xd[-1] / l) * p ** l


for p, level, a_m, b_m, draw_ids in [("pm25", "variable", "rival_rf", "treeroute", [0, 1999]),
                                     ("defo", "feature", "rival_lgbm", "rival_ridge", [5]),
                                     ("ndvi", "variable", "rival_bardl_h1", "treeroute", [17]),
                                     ("coral", "feature", "rival_lgbm_tweedie", "treeroute", [3])]:
    pr = res["problems"][p]
    lv = pr["levels"][level]
    J = lv["active_set"]["J"]
    regions = pr["draws"]["regions_in_draw_order"]
    draws = np.load(SHAP / "out" / p / "lead_0" / "compare" / "bootstrap_draws.npy")
    z = np.load(VB / "draws" / ("%s.npz" % p), allow_pickle=False)
    ta, ca = load(p, a_m, level)
    tb, cb = load(p, b_m, level)
    key = "|".join(sorted([a_m, b_m]))
    pe = lv["pairs"][key]
    for d in [None] + draw_ids:
        reg_list = regions if d is None else [regions[k] for k in draws[d]]
        tag = "%s %s %s draw %s" % (p, level, key, "full" if d is None else d)
        Ia = imp_loop(ta, ca, J, reg_list)
        Ib = imp_loop(tb, cb, J, reg_list)
        sa = {j: Ia[j] / sum(Ia.values()) for j in J}
        sb = {j: Ib[j] / sum(Ib.values()) for j in J}
        va = np.array([Ia[j] for j in J])
        vb = np.array([Ib[j] for j in J])
        sp = stats.spearmanr(va, vb).correlation
        tau = stats.kendalltau(va, vb, variant="b").correlation
        oa, ob = rank_order(Ia, J), rank_order(Ib, J)
        u20 = sorted(set(oa[:20]) | set(ob[:20]))
        sp20 = stats.spearmanr([Ia[j] for j in u20], [Ib[j] for j in u20]).correlation
        jac10 = len(set(oa[:10]) & set(ob[:10])) / len(set(oa[:10]) | set(ob[:10]))
        jac5 = len(set(oa[:5]) & set(ob[:5])) / len(set(oa[:5]) | set(ob[:5]))
        rbo9 = rbo_eq32(oa, ob, 0.9)
        rbo95 = rbo_eq32(oa, ob, 0.95)
        tv = 0.5 * sum(abs(sa[j] - sb[j]) for j in J)
        # sign agreement with the fixed determined status (recomputed here from the npz draws of S)
        Sa = imp_loop(ta, ca, J, reg_list, absval=False)
        Sb = imp_loop(tb, cb, J, reg_list, absval=False)
        da = {j: lv["models"][a_m]["players"][j]["sign_determined"] for j in J}
        db = {j: lv["models"][b_m]["players"][j]["sign_determined"] for j in J}
        u10 = set(oa[:10]) | set(ob[:10])
        det = [j for j in u10 if da[j] and db[j]]
        agree = [j for j in det if np.sign(Sa[j]) == np.sign(Sb[j])]
        sag = len(agree) / len(det) if det else None
        if d is None:
            get = lambda k: pe[k]["value"]
            close(tag + " I(first J player, " + a_m + ")", lv["models"][a_m]["players"][J[0]]["I"]["value"], Ia[J[0]])
            close(tag + " share(top player of " + b_m + ")", lv["models"][b_m]["players"][ob[0]]["share"]["value"], sb[ob[0]])
            close(tag + " signed mean(top player of " + a_m + ")", lv["models"][a_m]["players"][oa[0]]["signed_mean"]["value"], Sa[oa[0]])
            print("   ranking equal:", lv["models"][a_m]["ranking"] == oa, lv["models"][b_m]["ranking"] == ob,
                  "| top20 union equal:", pe["top20_union"] == u20)
        else:
            get = lambda k: (lambda v: None if not np.isfinite(v) else float(v))(z["levels/%s/pairs/%s/%s" % (level, key, k)][d])
        close(tag + " spearman_J", get("spearman_J"), sp)
        close(tag + " spearman_top20_union", get("spearman_top20_union"), sp20)
        close(tag + " kendall_tau_b", get("kendall_tau_b"), tau)
        close(tag + " jaccard_top5", get("jaccard_top5"), jac5)
        close(tag + " jaccard_top10", get("jaccard_top10"), jac10)
        close(tag + " rbo_p090", get("rbo_p090"), rbo9)
        close(tag + " rbo_p095", get("rbo_p095"), rbo95)
        close(tag + " tv_shares", get("tv_shares"), tv)
        close(tag + " sign_agreement", get("sign_agreement"), sag)
        close(tag + " sign_n_determined", get("sign_n_determined"), float(len(det)))

# Kendall's W of the main set (pm25 variable level), full sample and one draw, by the textbook formula
p = "pm25"
pr = res["problems"][p]
lv = pr["levels"]["variable"]
J = lv["active_set"]["J"]
regions = pr["draws"]["regions_in_draw_order"]
draws = np.load(SHAP / "out" / p / "lead_0" / "compare" / "bootstrap_draws.npy")
z = np.load(VB / "draws" / ("%s.npz" % p), allow_pickle=False)
for d in [None, 42]:
    reg_list = regions if d is None else [regions[k] for k in draws[d]]
    ranks = []
    T = 0.0
    for m in pr["main_set"]:
        t, c = load(p, m, "variable")
        I = imp_loop(t, c, J, reg_list)
        v = np.array([I[j] for j in J])
        ranks.append(stats.rankdata(v))
        _, cnt = np.unique(v, return_counts=True)
        T += float((cnt ** 3 - cnt).sum())
    R = np.array(ranks)
    m, n = R.shape
    S = ((R.sum(axis=0) - m * (n + 1) / 2) ** 2).sum()
    W = 12 * S / (m * m * (n ** 3 - n) - m * T)
    mine = lv["per_problem"]["kendall_w"]["value"] if d is None else float(z["levels/variable/per_problem/kendall_w"][d])
    close("pm25 variable Kendall W draw %s (textbook formula)" % ("full" if d is None else d), mine, W)

# item 8: fire treeroute, full sample and a draw, by loops over rows with pre > 0
p = "fire"
pr = res["problems"][p]
J = pr["levels"]["variable"]["active_set"]["J"]
regions = pr["draws"]["regions_in_draw_order"]
draws = np.load(SHAP / "out" / p / "lead_0" / "compare" / "bootstrap_draws.npy")
z = np.load(VB / "draws" / ("%s.npz" % p), allow_pickle=False)
t, c = load(p, "treeroute", "variable")
mask = t["pre"] > 0
nzm = pr["nonzero_forecast"]["models"]["treeroute"]
for d in [None, 7]:
    reg_list = regions if d is None else [regions[k] for k in draws[d]]
    I = imp_loop(t, c, J, reg_list, rows_mask=mask)
    tot = sum(I.values())
    top = rank_order(I, J)[0]
    if d is None:
        close("fire item 8 treeroute share of its top variable (full)", nzm["top10"][0][1], I[top] / tot)
        print("   top variable equal:", nzm["top10"][0][0] == top, "| rows used", nzm["rows_used"], int(mask.sum()))
    else:
        names = [str(x) for x in z["nonzero_forecast/models/treeroute/players/names"]]
        close("fire item 8 treeroute I of %s (draw %d)" % (top, d),
              float(z["nonzero_forecast/models/treeroute/players/I"][d, names.index(top)]), I[top])

# family share (own history) of treeroute, defo, by loops
p = "defo"
pr = res["problems"][p]
regions = pr["draws"]["regions_in_draw_order"]
t, c = load(p, "treeroute", "variable")
fam = pr["levels"]["variable"]["families"]["variable_family"]
fams = ["own_history", "global_indices", "local_drivers", "context_and_calendar", "seasonal_normal"]
F = {f: t[[c[v] for v in c if fam[v] == f]].sum(axis=1) if any(fam[v] == f for v in c) else pd.Series(0.0, index=t.index) for f in fams}
FI = {}
for f in fams:
    vals = [np.mean(np.abs(F[f][t["group"] == r])) for r in regions]
    FI[f] = np.mean(vals)
close("defo treeroute own-history family share (full)", pr["main_row"]["own_history_share_treeroute"]["value"],
      FI["own_history"] / sum(FI.values()))

print("CROSSCHECK", "PASSED" if not bad else "FAILED: %s" % bad)
sys.exit(1 if bad else 0)
