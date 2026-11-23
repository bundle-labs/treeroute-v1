"""Skeptic (numbers lens): top-k overlaps that exist only through the name-order tie rule.

For every pair of every problem at both levels (full sample): the players in both top-k sets (k = 5, 10, and 20 when
|J| >= 200) of which at least one model gives exactly 0 (a tie filled by name order), and the Jaccard / RBO / top-20-union
Spearman under three collations of the tie rule (code-point ascending = what A, B and compare_shap do; case-insensitive
ascending; code-point descending)."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s_lib as L

OUT = r"D:\treeroute\analysis\shap_v1\verify_v1\skeptic\numbers\work"


def keyrank(J, mode):
    if mode == "tie_ci":
        srt = sorted(range(len(J)), key=lambda i: (J[i].lower(), J[i]))
    elif mode == "tie_desc":
        srt = sorted(range(len(J)), key=lambda i: J[i], reverse=True)
    else:
        srt = sorted(range(len(J)), key=lambda i: J[i])
    kr = np.empty(len(J), dtype=np.int64)
    kr[np.array(srt)] = np.arange(len(J))
    return kr


def topk(v, kr, k):
    return list(np.lexsort((kr, -v))[:k])


res = {}
for p in ["coral", "defo", "fire", "pm25", "ndvi"]:
    pl = L.per_lead(p)
    d, _ = L.load_draws(p)
    for level in ["variable", "feature"]:
        data, g0 = {}, None
        for m in pl["models"]:
            _, gr, _, ph = L.load(p, m, level)
            g0 = gr if g0 is None else g0
            data[m] = ph
        R = L.Regions(g0, d)
        J, _ = L.active_set(data, R)
        I = {m: L.imp(data[m], J, R)["I"] for m in pl["models"]}
        ks = [5, 10] + ([20] if len(J) >= 200 else [])
        ms = sorted(pl["models"])
        for i, a in enumerate(ms):
            for b in ms[i + 1:]:
                rec = {}
                any_artifact = False
                for mode in ["base", "tie_ci", "tie_desc"]:
                    kr = keyrank(J, mode)
                    r = {}
                    for k in ks:
                        ta, tb = set(topk(I[a], kr, k)), set(topk(I[b], kr, k))
                        inter = ta & tb
                        art = [J[j] for j in inter if I[a][j] == 0 or I[b][j] == 0]
                        r["jaccard_top%d" % k] = len(inter) / len(ta | tb)
                        r["coincidental_top%d" % k] = sorted(art)
                        if art:
                            any_artifact = True
                    u = np.union1d(topk(I[a], kr, 20), topk(I[b], kr, 20))
                    r["rho20"] = float(L.spearman(I[a][u], I[b][u]))
                    r["rbo090"] = float(L.rbo_orders(np.lexsort((kr, -I[a])), np.lexsort((kr, -I[b])), 0.9)[0])
                    r["rbo095"] = float(L.rbo_orders(np.lexsort((kr, -I[a])), np.lexsort((kr, -I[b])), 0.95)[0])
                    rec[mode] = r
                spread = {}
                for st in rec["base"]:
                    if st.startswith("coincidental"):
                        continue
                    vals = [rec[mo][st] for mo in rec]
                    spread[st] = max(vals) - min(vals)
                if any_artifact or max(spread.values()) > 1e-12:
                    res["%s/%s/%s|%s" % (p, level, a, b)] = dict(rec, spread=spread,
                                                                 zeros_in_J={a: int((I[a] == 0).sum()), b: int((I[b] == 0).sum())})
for k, v in res.items():
    print(k, "| zeros", v["zeros_in_J"], "| spread", {s: round(x, 4) for s, x in v["spread"].items() if x > 1e-12})
    print("     base:", {s: (round(x, 4) if isinstance(x, float) else x) for s, x in v["base"].items()})
with open(os.path.join(OUT, "s41_tie_artifacts.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1)
