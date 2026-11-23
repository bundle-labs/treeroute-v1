# Round 14, implementer A: brief items 1-8 (lead 0 of coral, defo, fire, pm25, ndvi).
# Reads: per_lead.json (structural keys only), bootstrap_draws.npy, the row files and meta.json of the pieces
# named by per_lead.json's `models` (never anything under treeroute_B1\), and V\A\work\global_rule_<p>.json
# (written by a05_global_rule.py from the lead-0 test set). Writes V\A\work\items_<p>.json and V\A\draws\<p>.npz.
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np

import a_lib as L
import a_core as C


def fam_exists_vector(var_family, names):
    fams = set(var_family[v] for v in names)
    return [f in fams for f in L.FAMILIES]


def family_shares_obj(out, path, m, fam_exists):
    obj = {}
    for k, f in enumerate(L.FAMILIES):
        if fam_exists[k]:
            obj[f] = out.iv(path + [f], m.fs_f[k], m.fs_d[:, k])
        else:
            obj[f] = None
            obj[f + "_why"] = "The problem has no variable of this family, so the family has no share."
    return obj


def run_problem(p):
    t0 = time.time()
    out = L.Out()
    pl = L.read_per_lead_struct(p)
    models, main_set, declined, links = pl["models"], pl["main_set"], pl["declined_by_guard"], pl["links"]
    if "treeroute_B1" in models:
        raise SystemExit("per_lead models lists treeroute_B1")
    draws, dsha, dpath = L.load_draws(p)
    rows = {m: L.read_rows(p, m) for m in models}
    metas = {m: L.read_meta(p, m) for m in models}
    k0 = rows[models[0]]["keys"]
    for m in models[1:]:
        for c in L.KEYCOLS:
            if not np.array_equal(rows[m]["keys"][c], k0[c]):
                raise SystemExit("%s: keys of %s differ from %s" % (p, m, models[0]))
    flagged = {m: int(rows[m]["resid_flag"].sum()) for m in models}
    regions, reg = L.region_index(k0["group"])
    G = len(regions)
    if draws.shape != (L.N_DRAWS, G) or draws.min() < 0 or draws.max() >= G:
        raise SystemExit("%s: draw matrix %r does not match %d regions" % (p, draws.shape, G))
    counts = L.draw_counts(draws, G)
    Wd = counts / float(G)
    M, has, cnt = L.region_mean_matrix(reg, G)
    gpath = os.path.join(L.V_A, "work", "global_rule_%s.json" % p)
    with open(gpath, "r", encoding="utf-8") as fh:
        grule = json.load(fh)
    var_family = grule["variable_family"]

    res = {"lead": 0, "models": list(models), "main_set": list(main_set), "declined_by_guard": list(declined),
           "links": dict(links), "rows": pl["rows"]}
    res["draws"] = {
        "path": "SHAP\\out\\%s\\lead_0\\compare\\bootstrap_draws.npy" % p,
        "shape": [int(x) for x in draws.shape], "dtype": str(draws.dtype),
        "sha256_computed": dsha,
        "sha256_covers": "every byte of the .npy file as stored (its header and its data); the SHA-256 of the data bytes alone does not match",
        "sha256_per_lead": pl["draws_sha256"], "sha256_match": dsha == pl["draws_sha256"],
        "region_source": "rows.parquet column `group` (identical in every piece of the problem); regions in Python sorted() order, which here equals their order of first appearance by `row`",
        "regions_in_draw_order": regions,
        "npz": "V\\A\\draws\\%s.npz" % p,
        "extra": {"draws_are_rows": "each of the 2,000 rows is one draw of G region indices with replacement",
                  "generator_reproduced": "entry (b, k) = int.from_bytes(sha256('shap_v1|AW4|%s|0|<b>|<k>')[:8], 'big') mod G for every entry (scripts\\a50_draws_generator_probe.py)" % p,
                  "rows_per_region_min": int(cnt.min()), "rows_per_region_max": int(cnt.max()),
                  "resid_flagged_rows_per_model": flagged},
    }
    levels = {}
    keep = {}
    for level, key, mat in (("feature", "players", "phi"), ("variable", "variables", "phiv")):
        names = sorted(set().union(*[set(rows[m][key]) for m in models]))
        stats = {}
        for m in models:
            X, own = C.union_matrix(rows[m], key, mat, names)
            I_f, I_d, S_f, S_d = C.region_stats(X, M, Wd)
            stats[m] = (I_f, I_d, S_f, S_d, own)
        active = np.zeros(len(names), bool)
        totals = {}
        for m in models:
            I_f = stats[m][0]
            tot = I_f.sum()
            totals[m] = float(tot)
            active |= I_f > L.THRESH * tot
        jj = np.flatnonzero(active)
        Jn = [names[j] for j in jj]
        # J recomputed per draw would have this size (diagnostic only)
        act_d = np.zeros((L.N_DRAWS, len(names)), bool)
        for m in models:
            I_d = stats[m][1]
            act_d |= I_d > L.THRESH * I_d.sum(axis=1, keepdims=True)
        nJd = act_d.sum(axis=1)
        fam_ex = fam_exists_vector(var_family, names) if level == "variable" else None
        mls = {}
        for m in models:
            I_f, I_d, S_f, S_d, own = stats[m]
            fam = None
            if level == "variable":
                Fx = C.family_matrix(rows[m], var_family)
                FA = M @ np.abs(Fx)
                fam = (FA.mean(axis=0), Wd @ FA)
            mls[m] = C.prepare(I_f, I_d, S_f, S_d, own, jj, Jn, fam)
        lv = {"active_set": {
            "J": Jn,
            "n_J": L.Out.iv_noci(len(Jn), "J is fixed at the full sample (choice C07), so its size has no interval."),
            "structural_zeros": sorted(n for n in names if n not in set(Jn)),
            "extra": {"names_in_problem": len(names), "model_totals_mean_abs_phi": totals,
                      "n_J_if_recomputed_per_draw": {"min": int(nJd.min()), "median": float(np.median(nJd)),
                                                     "max": int(nJd.max())}}}}
        mo = {}
        for m in models:
            ml = mls[m]
            base = ["levels", level, "models", m]
            e = {"players": out.players(base + ["players"], Jn, ml.IJ_f, ml.IJ_d, ml.sh_f, ml.sh_d, ml.SJ_f,
                                        ml.SJ_d, ml.det),
                 "n_nonzero": out.iv(base + ["n_nonzero"], ml.nz_f, ml.nz_d),
                 "ranking": ml.ranking, "top10": ml.top10}
            if level == "variable":
                e["family_shares"] = family_shares_obj(out, base + ["family_shares"], ml, fam_ex)
            e["extra"] = {"own_columns": int(ml.own.sum()),
                          "meta_players_nonzero": metas[m].get("players_nonzero"),
                          "meta_variables_nonzero": metas[m].get("variables_nonzero"),
                          "n_nonzero_over_J": int((ml.IJ_f > 0).sum()),
                          "sign_determined_count": int(ml.detb.sum())}
            mo[m] = e
        lv["models"] = mo
        pairs = sorted(tuple(sorted((a, b))) for i, a in enumerate(models) for b in models[i + 1:])
        tau = C.tau_b_pairs(mls, pairs)
        pa = {}
        for (a, b) in pairs:
            k = a + "|" + b
            path = ["levels", level, "pairs", k]
            same = links[a] == links[b]
            d = {"models": [a, b], "link_class": "same-link" if same else "cross-link"}
            if not same:
                d["cross_link_label"] = "not comparable in scale or rank"
            d["declined"] = sorted(x for x in (a, b) if x in declined)
            d["both_in_main_set"] = (a in main_set) and (b in main_set)
            d.update(C.pair_stats(out, path, mls[a], mls[b], Jn, level, tau[(a, b)], fam_ex))
            pa[k] = d
        lv["pairs"] = pa
        # per problem-lead statistics
        pp = {}
        mains = [m for m in models if m in main_set]
        ppath = ["levels", level, "per_problem"]
        if len(mains) >= 2:
            Wf = L.kendall_w_rows([mls[m].IJ_f[None, :] for m in mains])[0]
            Wdr = L.kendall_w_rows([mls[m].IJ_d for m in mains])
            pp["kendall_w"] = out.iv(ppath + ["kendall_w"], Wf, Wdr)
            pp["kendall_w_m"] = len(mains)
            pp["kendall_w_n"] = len(Jn)
            mp = [tuple(sorted((a, b))) for i, a in enumerate(mains) for b in mains[i + 1:]]
            full = np.mean([L.pearson_rows(mls[a].rk_f, mls[b].rk_f)[0] for a, b in mp])
            drw = np.mean([L.pearson_rows(mls[a].rk_d, mls[b].rk_d) for a, b in mp], axis=0)
            pp["mean_pairwise_spearman"] = out.iv(ppath + ["mean_pairwise_spearman"], full, drw)
            keep[(level, "W")] = (Wf, Wdr)
        else:
            why = "The main set holds %d model(s) (%s); Kendall's W and the mean pairwise Spearman need two or more." % (
                len(mains), ", ".join(mains))
            pp["kendall_w"] = None; pp["kendall_w_why"] = why
            pp["kendall_w_m"] = None; pp["kendall_w_m_why"] = why
            pp["kendall_w_n"] = None; pp["kendall_w_n_why"] = why
            pp["mean_pairwise_spearman"] = None; pp["mean_pairwise_spearman_why"] = why
        stab = {}
        sx = {}
        for m in models:
            ml = mls[m]
            rho = L.pearson_rows(np.broadcast_to(ml.rk_f, ml.rk_d.shape), ml.rk_d)
            fin = np.isfinite(rho)
            val = float(rho[fin].mean()) if fin.any() else None
            stab[m] = L.Out.iv_noci(val, "The stability is itself the mean over the 2,000 draws (choice C20); it has no interval.",
                                    "No draw gives a finite Spearman with the full-sample importances.")
            lo, hi, nf = L.pct_ci(rho)
            sx[m] = {"n_finite_draws": nf, "rho_p2_5": lo, "rho_p97_5": hi, "rho_min": L.fnum(np.nanmin(rho)),
                     "rho_median": L.fnum(np.nanmedian(rho))}
        pp["stability"] = stab
        pp["extra"] = {"stability_per_draw_spearman": sx, "main_set_models_used": mains}
        lv["per_problem"] = pp
        if level == "variable":
            lv["families"] = {
                "variable_family": {v: var_family[v] for v in names},
                "global_indices": sorted(v for v in names if var_family[v] == "global_indices"),
                "test_set_records": ["SHAP\\logs\\rival_shap_%s_lead0.log (its 'test set:' line names the folder)" % p,
                                     "D:\\treeroute\\rival_export\\%s\\<run>\\lead_0\\test\\<region>.parquet (%d files, %d rows, %d units, %d time steps)" % (
                                         p, grule["region_files"], grule["rows"], grule["units"], grule["time_steps"])],
                "test_set_columns": sorted(grule["columns_read"]),
                "extra": {"rule": "exact equality of the stored values at each `time` across the units present; "
                                  "a step where every unit is missing counts as one value; a step mixing missing and "
                                  "present values fails",
                          "named_family_also_passing_rule": grule["named_family_also_passing_rule"],
                          "columns_missing_from_test_set": grule["columns_missing"]}}
        levels[level] = lv
        keep[level] = (Jn, mls, fam_ex, names)
    res["levels"] = levels
    # ---------------- item 7: the main-text row (variable level)
    Jn, mls, fam_ex, vnames = keep["variable"]
    mr = {"level": "variable", "main_set": list(main_set)}
    rivals = sorted(m for m in main_set if m != "treeroute") if "treeroute" in main_set else sorted(main_set)
    mr["rivals"] = rivals
    oh = L.FAMILIES.index("own_history")
    tr = mls.get("treeroute")
    mpath = ["main_row"]
    if ("variable", "W") in keep:
        Wf, Wdr = keep[("variable", "W")]
        mr["kendall_w"] = out.iv(mpath + ["kendall_w"], Wf, Wdr)
    else:
        mr["kendall_w"] = None
        mr["kendall_w_why"] = "The main set is treeroute alone, so Kendall's W is undefined."
    if tr is not None and rivals:
        full_r, draw_r = [], []
        for r in rivals:
            A, Bm = tr, mls[r]
            U = (A.pos_f[0] < 20) | (Bm.pos_f[0] < 20)
            full_r.append(L.spearman_1d(A.IJ_f[U], Bm.IJ_f[U]))
            draw_r.append(C.spearman_union_draws(A, Bm, 20))
        full_r = np.array(full_r); draw_r = np.vstack(draw_r).T  # (draws, rivals)
        mr["spearman_top20_union_median"] = out.iv(mpath + ["spearman_top20_union_median"], np.median(full_r), np.median(draw_r, axis=1))
        mr["spearman_top20_union_min"] = out.iv(mpath + ["spearman_top20_union_min"], full_r.min(), draw_r.min(axis=1))
        mr["spearman_top20_union_max"] = out.iv(mpath + ["spearman_top20_union_max"], full_r.max(), draw_r.max(axis=1))
        mr["spearman_top20_union_per_rival"] = {r: float(v) for r, v in zip(rivals, full_r)}
        cons_f = np.mean([mls[r].sh_f for r in rivals], axis=0)
        cons_d = np.mean([mls[r].sh_d for r in rivals], axis=0)
        co_f, cp_f = L.strict_order_2d(cons_f[None, :], Jn)
        co_d, cp_d = L.strict_order_2d(cons_d, Jn)
        mr["rbo_p090_vs_consensus"] = out.iv(mpath + ["rbo_p090_vs_consensus"], L.rbo_rows(tr.pos_f, cp_f, 0.9)[0],
                                             L.rbo_rows(tr.pos_d, cp_d, 0.9))
        mr["consensus_shares"] = {Jn[j]: float(cons_f[j]) for j in range(len(Jn))}
        mr["treeroute_top3"] = tr.top3
        mr["consensus_top3"] = [[Jn[j], float(cons_f[j])] for j in co_f[0][:3]]
        if fam_ex[oh]:
            mr["own_history_share_treeroute"] = out.iv(mpath + ["own_history_share_treeroute"], tr.fs_f[oh], tr.fs_d[:, oh])
            rv_f = np.array([mls[r].fs_f[oh] for r in rivals])
            rv_d = np.vstack([mls[r].fs_d[:, oh] for r in rivals]).T
            mr["own_history_share_median_rival"] = out.iv(mpath + ["own_history_share_median_rival"], np.median(rv_f),
                                                          np.median(rv_d, axis=1))
            mr["own_history_share_per_rival"] = {r: float(v) for r, v in zip(rivals, rv_f)}
            if len(rivals) % 2 == 1:
                med = np.median(rv_f)
                hit = [r for r, v in zip(rivals, rv_f) if v == med]
                mr["median_rival_name"] = hit[0] if len(hit) == 1 else None
                if len(hit) != 1:
                    mr["median_rival_name_why"] = "Several rivals share the median own-history share."
            else:
                mr["median_rival_name"] = None
                mr["median_rival_name_why"] = ("With %d rivals the median is the mean of the two middle own-history "
                                               "shares, so no single rival is the median one." % len(rivals))
        else:
            why = "The problem has no own-history (hist_*) variable, so the own-history share is undefined."
            for kk in ("own_history_share_treeroute", "own_history_share_median_rival", "own_history_share_per_rival",
                       "median_rival_name"):
                mr[kk] = None
                mr[kk + "_why"] = why
        mr["extra"] = {"median_of_even_count": "mean of the two middle values (numpy median)",
                       "range_per_draw": "min and max over the rivals on each draw"}
    else:
        why = "The main set is treeroute alone (no same-link guard-passing rival), so this number needs a rival and is undefined."
        for kk in ("spearman_top20_union_median", "spearman_top20_union_min", "spearman_top20_union_max",
                   "spearman_top20_union_per_rival", "rbo_p090_vs_consensus", "consensus_shares", "consensus_top3",
                   "own_history_share_median_rival", "own_history_share_per_rival", "median_rival_name"):
            mr[kk] = None
            mr[kk + "_why"] = why
        mr["treeroute_top3"] = tr.top3
        if fam_ex[oh]:
            mr["own_history_share_treeroute"] = out.iv(mpath + ["own_history_share_treeroute"], tr.fs_f[oh], tr.fs_d[:, oh])
        else:
            mr["own_history_share_treeroute"] = None
            mr["own_history_share_treeroute_why"] = "The problem has no own-history (hist_*) variable."
    res["main_row"] = mr
    # ---------------- item 8: arcsine-link models on their rows with pre > 0 (variable level)
    arc = sorted(m for m in models if links[m].split("|")[0] == "arcsine")
    nzf = {"models_covered": arc,
           "models_covered_why": ("Every model of this problem whose link string starts with 'arcsine' (section 8: "
                                  "'For every arcsine-link model'); shares over the problem's variable-level J."
                                  if arc else "No model of this problem has the arcsine link."),
           "models": {}}
    for m in arc:
        mask = rows[m]["pre"] > 0
        Mp, hasp, cntp = L.region_mean_matrix(reg, G, mask)
        X, own = C.union_matrix(rows[m], "variables", "phiv", vnames)
        jj = np.array([vnames.index(n) for n in Jn])
        A = Mp @ np.abs(X); Bm = Mp @ X
        I_f = A[hasp].mean(axis=0); S_f = Bm[hasp].mean(axis=0)
        w = counts * hasp[None, :]
        den = w.sum(axis=1, keepdims=True)
        with np.errstate(invalid="ignore", divide="ignore"):
            I_d = np.where(den > 0, (w @ A) / np.where(den > 0, den, 1.0), np.nan)
            S_d = np.where(den > 0, (w @ Bm) / np.where(den > 0, den, 1.0), np.nan)
        ml = C.prepare(I_f, I_d, S_f, S_d, own, jj, Jn, None)
        nz_d = ml.nz_d.copy(); nz_d[den[:, 0] == 0] = np.nan
        base = ["nonzero_forecast", "models", m]
        nzf["models"][m] = {
            "level": "variable", "rows_used": int(mask.sum()), "regions_used": int(hasp.sum()), "J": Jn,
            "players": out.players(base + ["players"], Jn, ml.IJ_f, ml.IJ_d, ml.sh_f, ml.sh_d, ml.SJ_f, ml.SJ_d, ml.det),
            "n_nonzero": out.iv(base + ["n_nonzero"], ml.nz_f, nz_d),
            "ranking": ml.ranking, "top10": ml.top10,
            "extra": {"draws_without_such_rows": int((den[:, 0] == 0).sum()),
                      "region_weighting": "each region with at least one such row weighs 1 (its such rows averaged); a draw weighs a region by its count"}}
    res["nonzero_forecast"] = nzf
    res["extra"] = {"seconds": round(time.time() - t0, 1)}
    with open(os.path.join(L.V_A, "work", "items_%s.json" % p), "w", encoding="utf-8") as fh:
        json.dump(res, fh, allow_nan=False)
    np.savez_compressed(os.path.join(L.V_A, "draws", "%s.npz" % p), **out.npz)
    with open(os.path.join(L.V_A, "work", "opened_items_%s.json" % p), "w", encoding="utf-8") as fh:
        json.dump(sorted(L.OPENED), fh, indent=1)
    print("%s: done in %.1f s; J feature %d, variable %d" % (p, time.time() - t0, len(levels["feature"]["active_set"]["J"]),
                                                              len(levels["variable"]["active_set"]["J"])))


if __name__ == "__main__":
    for p in (sys.argv[1:] or L.PROBLEMS):
        L.OPENED.clear()
        run_problem(p)
