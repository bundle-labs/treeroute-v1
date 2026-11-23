"""Skeptic (numbers lens): my own recomputation of a sample of the round-14 numbers.

- NDVI and PM2.5: the main-text row (item 7, variable level) with intervals;
- defo: Kendall's W over the main set (both levels) with intervals, and the mean pairwise Spearman;
- coral: treeroute's shares (feature level) with intervals and its top 10.
Opens only row files, meta.json, per_lead.json's structural keys, bootstrap_draws.npy and my own s01 output.
"""
import os, sys, json, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s_lib as L

OUT = r"D:\treeroute\analysis\shap_v1\verify_v1\skeptic\numbers\work"
t0 = time.time()
with open(os.path.join(OUT, "s01_global_coral_fire_pm25_ndvi.json"), encoding="utf-8") as f:
    GLOB = json.load(f)
with open(os.path.join(OUT, "s01_global_defo.json"), encoding="utf-8") as f:
    GLOB.update(json.load(f))

results = {}
npz = {}


def setup(p, level):
    pl = L.per_lead(p)
    d, sha = L.load_draws(p)
    data = {}
    groups0 = rows0 = None
    for m in pl["models"]:
        rows, groups, pre, phi = L.load(p, m, level)
        if groups0 is None:
            rows0, groups0 = rows, groups
        assert (rows == rows0).all() and (groups == groups0).all(), (p, m)
        data[m] = phi
    R = L.Regions(groups0, d)
    J, allnames = L.active_set(data, R)
    imps = {m: L.imp(ph, J, R) for m, ph in data.items()}
    return pl, d, sha, R, J, allnames, data, imps


def main_row(p):
    pl, d, sha, R, J, allnames, data, imps = setup(p, "variable")
    gvars = set(GLOB[p]["global_vars"])
    main = pl["main_set"]
    rivals = [m for m in main if m != "treeroute"]
    out = {"J_n": len(J), "structural_zeros": sorted(set(allnames) - set(J)), "rivals": rivals,
           "draws_sha256_file": sha, "draws_sha256_match": sha == pl["draws_sha256"]}
    # W
    Wf = L.kendall_w([imps[m]["I"] for m in main])
    Wd = L.kendall_w_draws([imps[m]["Id"] for m in main])
    out["kendall_w"] = L.iv(Wf, Wd)
    npz[p + "/main_row/kendall_w"] = Wd
    # mean pairwise spearman of the main set (over J)
    pairs = [(a, b) for i, a in enumerate(main) for b in main[i + 1:]]
    mps_f = np.mean([float(L.spearman(imps[a]["I"], imps[b]["I"])) for a, b in pairs])
    mps_d = np.mean([L.spearman(imps[a]["Id"], imps[b]["Id"]) for a, b in pairs], axis=0)
    out["mean_pairwise_spearman"] = L.iv(mps_f, mps_d)
    # top-20-union spearman treeroute vs each rival
    rf, rd = {}, {}
    for r in rivals:
        rf[r], _u = L.spearman_top20_union(imps["treeroute"]["I"], imps[r]["I"])
        rd[r] = L.spearman_top20_union_draws(imps["treeroute"]["Id"], imps[r]["Id"])
        npz[p + "/main_row/rho20/" + r] = rd[r]
    out["spearman_top20_union_per_rival"] = rf
    vals = np.array([rf[r] for r in rivals])
    D = np.vstack([rd[r] for r in rivals])
    out["spearman_top20_union_median"] = L.iv(np.median(vals), np.median(D, axis=0))
    out["spearman_top20_union_min"] = L.iv(vals.min(), D.min(axis=0))
    out["spearman_top20_union_max"] = L.iv(vals.max(), D.max(axis=0))
    npz[p + "/main_row/rho20_median"] = np.median(D, axis=0)
    # consensus
    sh = {m: L.shares_of(imps[m]["I"]) for m in main}
    shd = {m: L.shares_of(imps[m]["Id"]) for m in main}
    cons = np.mean([sh[r] for r in rivals], axis=0)
    consd = np.mean([shd[r] for r in rivals], axis=0)
    rbo_f = float(L.rbo(imps["treeroute"]["I"], cons, 0.9)[0])
    rbo_d = L.rbo_orders(L.order(imps["treeroute"]["Id"]), L.order(consd), 0.9)
    out["rbo_p090_vs_consensus"] = L.iv(rbo_f, rbo_d)
    npz[p + "/main_row/rbo_p090_vs_consensus"] = rbo_d
    o_tr = L.order(imps["treeroute"]["I"])
    out["treeroute_top3"] = [[J[i], float(sh["treeroute"][i])] for i in o_tr[:3]]
    o_c = L.order(cons)
    out["consensus_top3"] = [[J[i], float(cons[i])] for i in o_c[:3]]
    out["treeroute_top10"] = [[J[i], float(sh["treeroute"][i])] for i in o_tr[:10]]
    # own history (family share)
    oh_f, oh_d = {}, {}
    fam_all = {}
    for m in main:
        Ff, Fd = L.family_imp(data[m], gvars, R)
        sf = L.shares_of(Ff)
        sd = L.shares_of(Fd)
        fam_all[m] = {f: float(sf[i]) for i, f in enumerate(L.FAMS)}
        oh_f[m] = float(sf[0])
        oh_d[m] = sd[:, 0]
    out["family_shares"] = fam_all
    out["own_history_share_treeroute"] = L.iv(oh_f["treeroute"], oh_d["treeroute"])
    out["own_history_share_per_rival"] = {r: oh_f[r] for r in rivals}
    out["own_history_share_median_rival"] = L.iv(np.median([oh_f[r] for r in rivals]),
                                                 np.median(np.vstack([oh_d[r] for r in rivals]), axis=0))
    npz[p + "/main_row/own_history_share_treeroute"] = oh_d["treeroute"]
    npz[p + "/main_row/own_history_share_median_rival"] = np.median(np.vstack([oh_d[r] for r in rivals]), axis=0)
    # alternative readings, for the common-mode search
    alt = {}
    # (a) own-history share as the sum of the hist_* variables' shares s(j)
    hist_idx = [i for i, v in enumerate(J) if v.startswith("hist_")]
    alt["own_history_as_sum_of_variable_shares"] = {m: float(sh[m][hist_idx].sum()) for m in main}
    # (b) row-weighted (each row weighs 1) instead of region-weighted
    n = len(R.ridx)
    rw = {}
    for m in main:
        X = L.matrix(data[m], J, n)
        I_row = np.abs(X).mean(axis=0)
        rw[m] = I_row
    alt["row_weighted_W"] = float(L.kendall_w([rw[m] for m in main]))
    alt["row_weighted_rho20"] = {r: L.spearman_top20_union(rw["treeroute"], rw[r])[0] for r in rivals}
    cons_rw = np.mean([L.shares_of(rw[r]) for r in rivals], axis=0)
    alt["row_weighted_rbo_vs_consensus"] = float(L.rbo(rw["treeroute"], cons_rw, 0.9)[0])
    # (c) RBO without the p^n tail
    nJ = len(J)
    alt["rbo_without_tail"] = rbo_f - 0.9 ** nJ
    # (d) top-20-union spearman with ranks carried from J
    carried = {}
    rt = L.rankdata(imps["treeroute"]["I"], method="average")
    for r in rivals:
        u = sorted(L.topk_set(imps["treeroute"]["I"], 20) | L.topk_set(imps[r]["I"], 20))
        rr = L.rankdata(imps[r]["I"], method="average")
        carried[r] = float(L.pearson_rows(rt[u], rr[u]))
    alt["rho20_ranks_carried_from_J"] = carried
    # (e) J from the main set only
    Jm, _ = L.active_set({m: data[m] for m in main}, R)
    alt["J_main_set_only_n"] = len(Jm)
    out["alternatives"] = alt
    return out


def defo_w():
    out = {}
    for level in ["feature", "variable"]:
        pl, d, sha, R, J, allnames, data, imps = setup("defo", level)
        main = pl["main_set"]
        Wf = L.kendall_w([imps[m]["I"] for m in main])
        Wd = L.kendall_w_draws([imps[m]["Id"] for m in main])
        npz["defo/%s/kendall_w" % level] = Wd
        pairs = [(a, b) for i, a in enumerate(main) for b in main[i + 1:]]
        mps_f = np.mean([float(L.spearman(imps[a]["I"], imps[b]["I"])) for a, b in pairs])
        mps_d = np.mean([L.spearman(imps[a]["Id"], imps[b]["Id"]) for a, b in pairs], axis=0)
        # direct check of W on the full sample by the (12 S)/(m^2(n^3-n) - m sum T) form vs S/(m sum V)
        Wd_full_alt = float(L.kendall_w_draws([imps[m]["I"][None, :] for m in main])[0])
        out[level] = dict(J_n=len(J), m=len(main), kendall_w=L.iv(Wf, Wd), kendall_w_check_other_form=Wd_full_alt,
                          mean_pairwise_spearman=L.iv(mps_f, mps_d),
                          draws_sha256_match=sha == pl["draws_sha256"])
    return out


def coral_tr():
    pl, d, sha, R, J, allnames, data, imps = setup("coral", "feature")
    I = imps["treeroute"]["I"]
    s = L.shares_of(I)
    sd = L.shares_of(imps["treeroute"]["Id"])
    Sd = imps["treeroute"]["Sd"]
    o = L.order(I)
    out = {"J_n": len(J), "J": J, "structural_zeros": sorted(set(allnames) - set(J)),
           "top10": [[J[i], float(s[i])] for i in o[:10]],
           "shares": {J[i]: L.iv(s[i], sd[:, i]) for i in range(len(J))},
           "I": {J[i]: float(I[i]) for i in range(len(J))},
           "signed_mean": {J[i]: L.iv(imps["treeroute"]["S"][i], Sd[:, i]) for i in range(len(J))},
           "n_nonzero_over_own_columns": int(sum(1 for j, x in data["treeroute"].items() if np.any(x != 0))),
           "draws_sha256_match": sha == pl["draws_sha256"]}
    npz["coral/feature/treeroute/share"] = sd
    npz["coral/feature/treeroute/names"] = np.array(J)
    return out


results["ndvi"] = main_row("ndvi")
print("ndvi done", round(time.time() - t0, 1))
results["pm25"] = main_row("pm25")
print("pm25 done", round(time.time() - t0, 1))
results["defo"] = defo_w()
print("defo done", round(time.time() - t0, 1))
results["coral"] = coral_tr()
print("coral done", round(time.time() - t0, 1))
with open(os.path.join(OUT, "s10_main.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, indent=1, allow_nan=False)
np.savez_compressed(os.path.join(OUT, "s10_main_draws.npz"), **npz)
print("total", round(time.time() - t0, 1))
