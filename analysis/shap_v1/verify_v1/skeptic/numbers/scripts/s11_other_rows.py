"""Skeptic (numbers lens): the other main-text rows (coral, defo; fire's defined part), mine vs A, B, official."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s_lib as L

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
OUT = os.path.join(V, "skeptic", "numbers", "work")
GL = json.load(open(os.path.join(OUT, "s01_global_coral_fire_pm25_ndvi.json"), encoding="utf-8"))
GL.update(json.load(open(os.path.join(OUT, "s01_global_defo.json"), encoding="utf-8")))
A = json.load(open(os.path.join(V, "A", "results.json"), encoding="utf-8"))
Bj = json.load(open(os.path.join(V, "B", "results.json"), encoding="utf-8"))
lines = []


def show(key, mine, a, b, o):
    flag = ""
    for x in (a, b, o):
        if x is None:
            continue
        if isinstance(mine, (int, float)) and isinstance(x, (int, float)):
            if abs(mine - x) > 1e-9 * max(1.0, abs(mine)):
                flag = "  <-- DIFF"
        elif mine != x:
            flag = "  <-- DIFF"
    s = "%s | mine %r | A %r | B %r | off %r%s" % (key, mine, a, b, o, flag)
    lines.append(s)
    print(s)


def g(dct, *ks):
    for k in ks:
        if dct is None:
            return None
        dct = dct.get(k) if isinstance(dct, dict) else None
    return dct


for p in ["coral", "defo", "fire"]:
    pl = L.per_lead(p)
    d, _ = L.load_draws(p)
    data, g0 = {}, None
    for m in pl["models"]:
        _, gr, _, ph = L.load(p, m, "variable")
        g0 = gr if g0 is None else g0
        data[m] = ph
    R = L.Regions(g0, d)
    J, _ = L.active_set(data, R)
    main = pl["main_set"]
    imps = {m: L.imp(data[m], J, R) for m in main}
    rivals = [m for m in main if m != "treeroute"]
    off = json.load(open(os.path.join(L.SHAP, "out", p, "lead_0", "compare", "AW4_main_row.json"), encoding="utf-8"))
    a = A["problems"][p]["main_row"]
    b = Bj["problems"][p]["main_row"]
    sh_tr = L.shares_of(imps["treeroute"]["I"])
    o_tr = L.order(imps["treeroute"]["I"])
    show(p + "/treeroute_top3/names", [J[i] for i in o_tr[:3]], [x[0] for x in a["treeroute_top3"]],
         [x[0] for x in b["treeroute_top3"]], off.get("treeroute_top3"))
    Ff, Fd = L.family_imp(data["treeroute"], set(GL[p]["global_vars"]), R)
    tot = Ff.sum()
    ohv = float(Ff[0] / tot)
    ohd = L.shares_of(Fd)[:, 0]
    ohiv = L.iv(ohv, ohd)
    oo = off.get("own_history_share_treeroute")
    for k in ["value", "ci_low", "ci_high", "n_finite"]:
        ov = None
        if isinstance(oo, dict):
            ov = oo.get("value") if k == "value" else (oo.get("ci") or [None, None, None])[["ci_low", "ci_high", "n_finite"].index(k)]
        show(p + "/own_history_share_treeroute/" + k, ohiv[k], g(a, "own_history_share_treeroute", k),
             g(b, "own_history_share_treeroute", k), ov)
    if not rivals:
        continue
    Wf = L.kendall_w([imps[m]["I"] for m in main])
    Wd = L.kendall_w_draws([imps[m]["Id"] for m in main])
    wiv = L.iv(Wf, Wd)
    for k in ["value", "ci_low", "ci_high", "n_finite"]:
        ov = off["kendall_w"]["value"] if k == "value" else off["kendall_w"]["ci"][["ci_low", "ci_high", "n_finite"].index(k)]
        show(p + "/kendall_w/" + k, wiv[k], a["kendall_w"][k], b["kendall_w"][k], ov)
    vals = np.array([L.spearman_top20_union(imps["treeroute"]["I"], imps[r]["I"])[0] for r in rivals])
    D = np.vstack([L.spearman_top20_union_draws(imps["treeroute"]["Id"], imps[r]["Id"]) for r in rivals])
    med = L.iv(np.median(vals), np.median(D, axis=0))
    om = off["treeroute_vs_same_link_rivals_median_spearman_top20_union"]
    for k in ["value", "ci_low", "ci_high", "n_finite"]:
        ov = om["value"] if k == "value" else om["ci"][["ci_low", "ci_high", "n_finite"].index(k)]
        show(p + "/rho20_median/" + k, med[k], a["spearman_top20_union_median"][k], b["spearman_top20_union_median"][k], ov)
    show(p + "/rho20_range_min", float(vals.min()), a["spearman_top20_union_min"]["value"], b["spearman_top20_union_min"]["value"], om["range"][0])
    show(p + "/rho20_range_max", float(vals.max()), a["spearman_top20_union_max"]["value"], b["spearman_top20_union_max"]["value"], om["range"][1])
    shd = {m: L.shares_of(imps[m]["Id"]) for m in main}
    cons = np.mean([L.shares_of(imps[r]["I"]) for r in rivals], axis=0)
    consd = np.mean([shd[r] for r in rivals], axis=0)
    rb = L.iv(float(L.rbo(imps["treeroute"]["I"], cons, 0.9)[0]),
              L.rbo_orders(L.order(imps["treeroute"]["Id"]), L.order(consd), 0.9))
    orr = off["rbo_vs_consensus_p0.9"]
    for k in ["value", "ci_low", "ci_high", "n_finite"]:
        ov = orr["value"] if k == "value" else orr["ci"][["ci_low", "ci_high", "n_finite"].index(k)]
        show(p + "/rbo_p090_vs_consensus/" + k, rb[k], a["rbo_p090_vs_consensus"][k], b["rbo_p090_vs_consensus"][k], ov)
    show(p + "/consensus_top3/names", [J[i] for i in L.order(cons)[:3]], [x[0] for x in a["consensus_top3"]],
         [x[0] for x in b["consensus_top3"]], off.get("consensus_top3"))
    ohr = {}
    ohrd = {}
    for r in rivals:
        F1, F1d = L.family_imp(data[r], set(GL[p]["global_vars"]), R)
        ohr[r] = float(F1[0] / F1.sum())
        ohrd[r] = L.shares_of(F1d)[:, 0]
    mr = L.iv(np.median(list(ohr.values())), np.median(np.vstack(list(ohrd.values())), axis=0))
    oo = off.get("own_history_share_median_rival")
    for k in ["value", "ci_low", "ci_high", "n_finite"]:
        ov = oo.get("value") if k == "value" else (oo.get("ci") or [None, None, None])[["ci_low", "ci_high", "n_finite"].index(k)]
        show(p + "/own_history_share_median_rival/" + k, mr[k], g(a, "own_history_share_median_rival", k),
             g(b, "own_history_share_median_rival", k), ov)
open(os.path.join(OUT, "s11_other_rows.out.txt"), "w", encoding="utf-8").write("\n".join(lines))
print("differences:", sum("DIFF" in s for s in lines), "of", len(lines))
