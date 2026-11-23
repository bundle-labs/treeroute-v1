"""Skeptic (numbers lens): B1 numbers of my sample.

- defo identity check: largest |difference| between treeroute_B1\\rows.parquet and treeroute\\rows.parquet over every
  phi__ and every phiv__ column, rows matched by `row`, players and variables by name;
- fire: the pair (treeroute, treeroute_B1) at the variable level (and the feature level as a by-product):
  Spearman over the pair's J and TV distance between shares, with intervals from the saved draws.
"""
import os, sys, json
import numpy as np
import pyarrow.parquet as pq
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s_lib as L

OUT = r"D:\treeroute\analysis\shap_v1\verify_v1\skeptic\numbers\work"
res = {}

# ---- defo identity ----
pm = os.path.join(L.piece("defo", "treeroute"), "rows.parquet")
pb = os.path.join(L.piece("defo", "treeroute_B1"), "rows.parquet")
tm = pq.read_table(pm).to_pandas().set_index("row").sort_index()
tb = pq.read_table(pb).to_pandas().set_index("row").sort_index()
same_rows = set(tm.index) == set(tb.index)
com = tm.index.intersection(tb.index)
out = {"n_rows_main": len(tm), "n_rows_b1": len(tb), "same_rows": same_rows}
for pref, key in [("phi__", "phi"), ("phiv__", "phiv")]:
    cm = sorted(c for c in tm.columns if c.startswith(pref))
    cb = sorted(c for c in tb.columns if c.startswith(pref))
    both = sorted(set(cm) & set(cb))
    d = np.abs(tm.loc[com, both].to_numpy(dtype=np.float64) - tb.loc[com, both].to_numpy(dtype=np.float64))
    out["max_abs_diff_" + key] = float(np.nanmax(d)) if d.size else None
    out["nan_mismatch_" + key] = int((np.isnan(tm.loc[com, both].to_numpy()) != np.isnan(tb.loc[com, both].to_numpy())).sum())
    out["n_" + key + "_main"] = len(cm)
    out["n_" + key + "_b1"] = len(cb)
    out["same_" + key + "_names"] = cm == cb
    out["bitwise_equal_" + key] = bool(np.array_equal(tm.loc[com, both].to_numpy(), tb.loc[com, both].to_numpy()))
# extra: the other columns
other = {}
for c in ["unit", "group", "time", "year", "base", "eta", "eta_model", "pre", "resid", "gap", "add_err"]:
    a = tm.loc[com, c].to_numpy()
    b = tb.loc[com, c].to_numpy()
    if a.dtype.kind in "fc":
        other[c] = float(np.nanmax(np.abs(a - b)))
    else:
        other[c] = bool((a == b).all())
out["other_columns"] = other
for nm in ["treeroute", "treeroute_B1"]:
    mt = L.meta("defo", nm)
    out["meta_" + nm] = {k: mt.get(k) for k in ["pairs", "trees_used", "players_nonzero", "variables_nonzero",
                                                 "tree_shap_seconds", "background", "pass"]}
res["defo_identity"] = out
print("defo identity:", json.dumps(out))

# ---- fire B1 pair ----
pl = L.per_lead("fire")
d, sha = L.load_draws("fire")
for level in ["variable", "feature"]:
    rows_m, g_m, pre_m, ph_m = L.load("fire", "treeroute", level)
    rows_b, g_b, pre_b, ph_b = L.load("fire", "treeroute_B1", level)
    assert (rows_m == rows_b).all() and (g_m == g_b).all()
    R = L.Regions(g_m, d)
    J, allnames = L.active_set({"main": ph_m, "b1": ph_b}, R)
    im = L.imp(ph_m, J, R)
    ib = L.imp(ph_b, J, R)
    sm, sb = L.shares_of(im["I"]), L.shares_of(ib["I"])
    smd, sbd = L.shares_of(im["Id"]), L.shares_of(ib["Id"])
    rho_f = float(L.spearman(im["I"], ib["I"]))
    rho_d = L.spearman(im["Id"], ib["Id"])
    tv_f = float(L.tv(sm, sb))
    tv_d = L.tv(smd, sbd)
    rho20_f, u = L.spearman_top20_union(im["I"], ib["I"])
    rho20_d = L.spearman_top20_union_draws(im["Id"], ib["Id"])
    rbo9_f = float(L.rbo(im["I"], ib["I"], 0.9)[0])
    rbo9_d = L.rbo_orders(L.order(im["Id"]), L.order(ib["Id"]), 0.9)
    ob = L.order(ib["I"])
    out = {"J_n": len(J), "structural_zeros": sorted(set(allnames) - set(J)),
           "J_only_from_b1": sorted(j for j, a in zip(J, im["I"]) if not a > 1e-12 * L.imp(ph_m, allnames, R)["I"].sum()),
           "spearman_J": L.iv(rho_f, rho_d), "tv_shares": L.iv(tv_f, tv_d),
           "spearman_top20_union": L.iv(rho20_f, rho20_d), "rbo_p090": L.iv(rbo9_f, rbo9_d),
           "b1_top10": [[J[i], float(sb[i])] for i in ob[:10]],
           "b1_n_nonzero_own_columns": int(sum(1 for j, x in ph_b.items() if np.any(x != 0))),
           "draws_sha256_match": sha == pl["draws_sha256"]}
    if level == "variable":
        GL = json.load(open(os.path.join(OUT, "s01_global_coral_fire_pm25_ndvi.json"), encoding="utf-8"))["fire"]["global_vars"]
        Fm, Fmd = L.family_imp(ph_m, set(GL), R)
        Fb, Fbd = L.family_imp(ph_b, set(GL), R)
        out["b1_family_shares"] = {f: float(x) for f, x in zip(L.FAMS, L.shares_of(Fb))}
        out["tv_family_shares"] = L.iv(float(L.tv(L.shares_of(Fm), L.shares_of(Fb))), L.tv(L.shares_of(Fmd), L.shares_of(Fbd)))
        out["b1_own_history_share"] = L.iv(float(L.shares_of(Fb)[0]), L.shares_of(Fbd)[:, 0])
        out["b1_top3"] = [[J[i], float(sb[i])] for i in ob[:3]]
    res["fire_b1_" + level] = out
    print("fire", level, json.dumps({k: v for k, v in out.items() if k not in ("structural_zeros",)}))
with open(os.path.join(OUT, "s20_b1.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, allow_nan=False)
