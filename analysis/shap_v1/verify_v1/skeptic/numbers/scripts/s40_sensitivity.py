"""Skeptic (numbers lens): how much the main-text rows (variable level) depend on the shared readings.

Variants (each changes one reading; everything else as in s10):
  base         ties by name, Python code-point order ascending (what A, B and compare_shap do)
  tie_ci       ties by name, case-insensitive ascending
  tie_desc     ties by name, descending
  rowweight    every row weighs 1 instead of every region (I = plain mean over rows; draws: rows of drawn regions)
  j_main       J from the main set's models only
Also the defo W under j_main and the fire B1 pair under the tie variants.
"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s_lib as L

OUT = r"D:\treeroute\analysis\shap_v1\verify_v1\skeptic\numbers\work"
GL = json.load(open(os.path.join(OUT, "s01_global_coral_fire_pm25_ndvi.json"), encoding="utf-8"))
GL.update(json.load(open(os.path.join(OUT, "s01_global_defo.json"), encoding="utf-8")))


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


def order_k(v, kr):
    v = np.asarray(v)
    if v.ndim == 1:
        return np.lexsort((kr, -v))
    return np.lexsort((np.broadcast_to(kr, v.shape), -v), axis=-1)


def rho20(a, b, kr):
    u = np.union1d(order_k(a, kr)[:20], order_k(b, kr)[:20])
    return float(L.spearman(a[u], b[u]))


def rho20_draws(A, Bm, kr):
    oa = order_k(A, kr)[:, :20]
    ob = order_k(Bm, kr)[:, :20]
    out = np.empty(A.shape[0])
    for i in range(A.shape[0]):
        u = np.union1d(oa[i], ob[i])
        out[i] = L.spearman(A[i, u], Bm[i, u])
    return out


def imp_rowweight(phi, names, R):
    X = L.matrix(phi, names, len(R.ridx))
    # per region sums and counts; a draw weighs a region's rows by its count c_r
    Ssum = np.zeros((R.G, X.shape[1]))
    np.add.at(Ssum, R.ridx, np.abs(X))
    I = Ssum.sum(axis=0) / len(R.ridx)
    Id = (R.C @ Ssum) / (R.C @ R.nr)[:, None]
    return dict(I=I, Id=Id)


def main_row(p, mode):
    pl = L.per_lead(p)
    d, _ = L.load_draws(p)
    data = {}
    g0 = None
    for m in pl["models"]:
        rows, groups, pre, phi = L.load(p, m, "variable")
        g0 = groups if g0 is None else g0
        data[m] = phi
    R = L.Regions(g0, d)
    main = pl["main_set"]
    if mode == "j_main":
        J, _ = L.active_set({m: data[m] for m in main}, R)
    else:
        J, _ = L.active_set(data, R)
    kr = keyrank(J, mode)
    if mode == "rowweight":
        imps = {m: imp_rowweight(data[m], J, R) for m in main}
    else:
        imps = {m: L.imp(data[m], J, R) for m in main}
    out = {"n_J": len(J)}
    if len(main) >= 2:
        out["W"] = L.iv(L.kendall_w([imps[m]["I"] for m in main]), L.kendall_w_draws([imps[m]["Id"] for m in main]))
    rivals = [m for m in main if m != "treeroute"]
    if not rivals:
        o = order_k(imps["treeroute"]["I"], kr)
        out["treeroute_top3"] = [J[i] for i in o[:3]]
        return out
    vals = np.array([rho20(imps["treeroute"]["I"], imps[r]["I"], kr) for r in rivals])
    D = np.vstack([rho20_draws(imps["treeroute"]["Id"], imps[r]["Id"], kr) for r in rivals])
    out["rho20_per_rival"] = dict(zip(rivals, vals.tolist()))
    out["rho20_median"] = L.iv(np.median(vals), np.median(D, axis=0))
    out["rho20_min_max"] = [float(vals.min()), float(vals.max())]
    sh = {m: L.shares_of(imps[m]["I"]) for m in main}
    shd = {m: L.shares_of(imps[m]["Id"]) for m in main}
    cons = np.mean([sh[r] for r in rivals], axis=0)
    consd = np.mean([shd[r] for r in rivals], axis=0)
    out["rbo_vs_consensus"] = L.iv(float(L.rbo_orders(order_k(imps["treeroute"]["I"], kr), order_k(cons, kr), 0.9)[0]),
                                   L.rbo_orders(order_k(imps["treeroute"]["Id"], kr), order_k(consd, kr), 0.9))
    out["treeroute_top3"] = [J[i] for i in order_k(imps["treeroute"]["I"], kr)[:3]]
    out["consensus_top3"] = [J[i] for i in order_k(cons, kr)[:3]]
    if mode == "rowweight":
        # own-history family share, rows weighted
        gv = set(GL[p]["global_vars"])
        n = len(R.ridx)
        oh = {}
        for m in main:
            F = np.zeros((n, len(L.FAMS)))
            for v, x in data[m].items():
                F[:, L.FAMS.index(L.family_of(v, gv))] += x
            Fi = np.abs(F).mean(axis=0)
            oh[m] = float(Fi[0] / Fi.sum()) if Fi.sum() > 0 else None
        out["own_history_treeroute"] = oh["treeroute"]
        out["own_history_median_rival"] = float(np.median([oh[r] for r in rivals])) if all(oh[r] is not None for r in rivals) else None
    return out


res = {}
for p in ["ndvi", "pm25", "defo", "coral", "fire"]:
    res[p] = {}
    for mode in ["base", "tie_ci", "tie_desc", "rowweight", "j_main"]:
        res[p][mode] = main_row(p, mode)
    print("==", p)
    for mode, o in res[p].items():
        print("  ", mode, json.dumps(o))

# fire B1 pair under the tie variants (Spearman over J is tie-break free; TV too) -> check top-k-based ones
d, _ = L.load_draws("fire")
_, gm, _, pm = L.load("fire", "treeroute", "variable")
_, gb, _, pb = L.load("fire", "treeroute_B1", "variable")
R = L.Regions(gm, d)
J, _ = L.active_set({"m": pm, "b": pb}, R)
im, ib = L.imp(pm, J, R), L.imp(pb, J, R)
res["fire_b1_variable"] = {}
for mode in ["base", "tie_ci", "tie_desc"]:
    kr = keyrank(J, mode)
    res["fire_b1_variable"][mode] = dict(
        rho20=rho20(im["I"], ib["I"], kr),
        rbo090=float(L.rbo_orders(order_k(im["I"], kr), order_k(ib["I"], kr), 0.9)[0]),
        b1_top3=[J[i] for i in order_k(ib["I"], kr)[:3]])
print("fire B1", json.dumps(res["fire_b1_variable"]))
with open(os.path.join(OUT, "s40_sensitivity.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1)
