"""Skeptic (numbers lens): B1 pair (variable and feature level) for pm25 and ndvi: Spearman over the pair's J, TV of
shares, family TVD and the B1 own-history share, with intervals; mine vs A and B."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s_lib as L

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
OUT = os.path.join(V, "skeptic", "numbers", "work")
GL = json.load(open(os.path.join(OUT, "s01_global_coral_fire_pm25_ndvi.json"), encoding="utf-8"))
A = json.load(open(os.path.join(V, "A", "results.json"), encoding="utf-8"))["b1"]
Bj = json.load(open(os.path.join(V, "B", "results.json"), encoding="utf-8"))["b1"]
lines = []


def show(key, mine, a, b):
    flag = ""
    for x in (a, b):
        if isinstance(mine, (int, float)) and isinstance(x, (int, float)):
            if abs(mine - x) > 1e-9 * max(1.0, abs(mine)):
                flag = "  <-- DIFF"
        elif mine != x:
            flag = "  <-- DIFF"
    s = "%s | mine %r | A %r | B %r%s" % (key, mine, a, b, flag)
    lines.append(s)
    print(s)


for p in ["pm25", "ndvi"]:
    d, _ = L.load_draws(p)
    for level in ["variable", "feature"]:
        _, gm, _, pm = L.load(p, "treeroute", level)
        _, gb, _, pb = L.load(p, "treeroute_B1", level)
        assert (gm == gb).all()
        R = L.Regions(gm, d)
        J, _ = L.active_set({"m": pm, "b": pb}, R)
        im, ib = L.imp(pm, J, R), L.imp(pb, J, R)
        sm, sb = L.shares_of(im["I"]), L.shares_of(ib["I"])
        out = {"n_J": len(J),
               "spearman_J": L.iv(float(L.spearman(im["I"], ib["I"])), L.spearman(im["Id"], ib["Id"])),
               "tv_shares": L.iv(float(L.tv(sm, sb)), L.tv(L.shares_of(im["Id"]), L.shares_of(ib["Id"])))}
        ap = A[p][level]["pair_main_b1"]
        bp = Bj[p][level]["pair_main_b1"]
        show("%s/%s/pair/n_J" % (p, level), out["n_J"], ap["n_J"]["value"], bp["n_J"]["value"])
        for st in ["spearman_J", "tv_shares"]:
            for k in ["value", "ci_low", "ci_high", "n_finite"]:
                show("%s/%s/pair/%s/%s" % (p, level, st, k), out[st][k], ap[st][k], bp[st][k])
        if level == "variable":
            Fm, Fmd = L.family_imp(pm, set(GL[p]["global_vars"]), R)
            Fb, Fbd = L.family_imp(pb, set(GL[p]["global_vars"]), R)
            tvf = L.iv(float(L.tv(L.shares_of(Fm), L.shares_of(Fb))), L.tv(L.shares_of(Fmd), L.shares_of(Fbd)))
            ohb = L.iv(float(L.shares_of(Fb)[0]), L.shares_of(Fbd)[:, 0])
            for k in ["value", "ci_low", "ci_high", "n_finite"]:
                show("%s/variable/pair/tv_family_shares/%s" % (p, k), tvf[k], ap["tv_family_shares"][k], bp["tv_family_shares"][k])
                show("%s/variable/own_history_share/%s" % (p, k), ohb[k], A[p]["variable"]["own_history_share"][k],
                     Bj[p]["variable"]["own_history_share"][k])
            ob = L.order(ib["I"])
            show("%s/variable/top3/names" % p, [J[i] for i in ob[:3]], [x[0] for x in A[p]["variable"]["top3"]],
                 [x[0] for x in Bj[p]["variable"]["top3"]])
open(os.path.join(OUT, "s21_b1_more.out.txt"), "w", encoding="utf-8").write("\n".join(lines))
print("differences:", sum("DIFF" in s for s in lines), "of", len(lines))
