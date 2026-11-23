# Implementer B, round 14: brief items 1-8 (the comparison numbers of scope (i), lead 0), from the protocol's words.
# Reads only: per_lead.json's structural keys, compare\bootstrap_draws.npy, the pieces named in per_lead.json's
# `models` (rows.parquet, meta.json) and V\B\work\global_<p>.json (b_global_index.py). It opens nothing under any
# treeroute_B1 folder. Writes V\B\work\problems.json and V\B\draws\<p>.npz.
import itertools
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import b_lib as L

PROBLEMS = ["coral", "defo", "fire", "pm25", "ndvi"]
STRUCT = ("models", "main_set", "declined_by_guard", "links", "rows")
WHY_NJ = "J is fixed at the full sample (choices.md C07), so its count has no interval (C08)."
WHY_STAB = ("The stability is itself a mean over the bootstrap replicates; it gets no interval of its own "
            "(choices.md C20).")


def importance_stacks(models, rows_of, region, G, Cs):
    U = sorted(set().union(*[set(rows_of[m][0]) for m in models]))
    ui = {n: k for k, n in enumerate(U)}
    I_all, S_all, own, plain = {}, {}, {}, {}
    for m in models:
        players, X = rows_of[m]
        Xu = np.zeros((X.shape[0], len(U)))
        cols = [ui[n] for n in players]
        Xu[:, cols] = X
        own[m] = np.zeros(len(U), dtype=bool)
        own[m][cols] = True
        Aabs, _ = L.region_means(np.abs(Xu), region, G)
        Asig, _ = L.region_means(Xu, region, G)
        I_all[m] = L.weighted_over_regions(Cs, Aabs)
        S_all[m] = L.weighted_over_regions(Cs, Asig)
        plain[m] = np.abs(Xu).mean(axis=0)
    return U, I_all, S_all, own, plain


def compute_level(level, models, main_set, links, declined, region, G, Cs, rows_of, fam, D, meta_nz):
    """Items 1, 2, 4 and 5 at one level. rows_of[m] = (players, X). fam[m]: (R, 5) family shares."""
    U, I_all, S_all, own, plain = importance_stacks(models, rows_of, region, G, Cs)
    R = Cs.shape[0]
    # item 1: active set J (full sample, every model of `models`)
    inJ = np.zeros(len(U), dtype=bool)
    inJ_plain = np.zeros(len(U), dtype=bool)
    for m in models:
        inJ |= I_all[m][0] > L.ACTIVE_REL * I_all[m][0].sum()
        inJ_plain |= plain[m] > L.ACTIVE_REL * plain[m].sum()
    J = [n for n, f in zip(U, inJ) if f]
    jidx = np.flatnonzero(inJ)
    nJ = len(J)
    zeros = [n for n, f in zip(U, inJ) if not f]
    tiny = {m: [U[k] for k in range(len(U)) if (not inJ[k]) and I_all[m][0, k] > 0] for m in models}
    MB = {m: L.model_block(I_all[m], S_all[m], jidx) for m in models}
    base = ["levels", level]
    out = {"active_set": {"J": J, "n_J": L.no_interval(nJ, WHY_NJ), "structural_zeros": zeros,
                          "extra": {"nonzero_players_outside_J": tiny, "universe_size": len(U),
                                    "J_same_under_unweighted_row_mean": bool((inJ == inJ_plain).all())}}}
    # item 2: per model
    mo = {}
    for m in models:
        b = MB[m]
        nz = (I_all[m] > 0) & own[m][None, :]
        e = {"players": D.players(base + ["models", m, "players"], J, b["IJ"], b["SH"], b["SG"], b["DET"]),
             "n_nonzero": D.iv(base + ["models", m, "n_nonzero"], nz.sum(axis=1).astype(np.float64)),
             "ranking": [J[i] for i in b["ORD"][0]],
             "top10": L.top_list(J, b["ORD"][0], b["SH"][0], 10),
             "extra": {"players_of_J_without_a_column": [U[k] for k in range(len(U)) if not own[m][k] and inJ[k]],
                       "meta_nonzero": meta_nz[m], "n_players_in_file": int(own[m].sum())}}
        if level == "variable":
            e["family_shares"] = {f: D.iv(base + ["models", m, "family_shares", f], fam[m][:, k])
                                  for k, f in enumerate(L.FAMILIES)}
        mo[m] = e
    out["models"] = mo
    # item 4: every pair
    pairs = [tuple(sorted(c)) for c in itertools.combinations(models, 2)]
    tau = L.kendall_tau_b_all({m: MB[m]["IJ"] for m in models}, pairs)
    PS, po = {}, {}
    for a, b in pairs:
        key = a + "|" + b
        same = links[a] == links[b]
        e = {"models": [a, b], "link_class": "same-link" if same else "cross-link"}
        if not same:
            e["cross_link_label"] = "not comparable in scale or rank"
        e["declined"] = sorted(x for x in (a, b) if x in declined)
        e["both_in_main_set"] = (a in main_set) and (b in main_set)
        st, sp, s20 = L.pair_block(D, base + ["pairs", key], J, MB[a], MB[b], fam[a], fam[b], tau[(a, b)])
        e.update(st)
        PS[(a, b)] = sp
        PS[(a, b, "u20")] = s20
        po[key] = e
    out["pairs"] = po
    # item 5: per problem
    pp = {}
    ms = [m for m in models if m in main_set]
    if len(ms) >= 2:
        W = L.kendall_w_rows([MB[m]["IJ"] for m in ms])
        pp["kendall_w"] = D.iv(base + ["per_problem", "kendall_w"], W)
        pp["kendall_w_m"] = len(ms)
        pp["kendall_w_n"] = nJ
        mp = np.mean([PS[tuple(sorted(c))] for c in itertools.combinations(ms, 2)], axis=0)
        pp["mean_pairwise_spearman"] = D.iv(base + ["per_problem", "mean_pairwise_spearman"], mp)
        pp_extra = {"kendall_w_textbook_formula_full_sample": L.kendall_w_explicit([MB[m]["IJ"][0] for m in ms]),
                    "mW_minus_1_over_m_minus_1": (len(ms) * W[0] - 1) / (len(ms) - 1)}
    else:
        why = "The main set has %d model(s) (%s); Kendall's W needs two or more rankings." % (len(ms), ", ".join(ms))
        for k in ("kendall_w", "kendall_w_m", "kendall_w_n"):
            pp[k] = None
            pp[k + "_why"] = why
        pp["mean_pairwise_spearman"] = None
        pp["mean_pairwise_spearman_why"] = "The main set has %d model(s); there is no pair in it." % len(ms)
        pp_extra = {}
    st, st_extra = {}, {}
    for m in models:
        IJ = MB[m]["IJ"]
        rho = L.spearman_rows(np.repeat(IJ[:1], R - 1, axis=0), IJ[1:])
        fin = np.isfinite(rho)
        val = float(rho[fin].mean()) if fin.any() else None
        st[m] = L.no_interval(val, WHY_STAB, value_why="No bootstrap replicate gives a finite Spearman.")
        st_extra[m] = {"finite_replicates": int(fin.sum()),
                       "replicate_percentiles_2.5_50_97.5": [float(x) for x in np.percentile(rho[fin], [2.5, 50, 97.5])] if fin.any() else None}
    pp["stability"] = st
    pp_extra["stability_replicates"] = st_extra
    pp["extra"] = pp_extra
    out["per_problem"] = pp
    return out, {"J": J, "MB": MB, "PS": PS, "U": U}


def main(problems):
    t_all = time.time()
    res = {}
    for p in problems:
        t0 = time.time()
        lead = L.SHAP / "out" / p / "lead_0"
        pl = json.loads((lead / "compare" / "per_lead.json").read_text(encoding="utf-8"))
        st = {k: pl[k] for k in STRUCT}
        sha_per_lead = pl["draws_sha256"]
        del pl  # nothing else of per_lead.json is read
        models, main_set, declined, links = st["models"], st["main_set"], st["declined_by_guard"], st["links"]
        assert "treeroute_B1" not in models
        dpath = lead / "compare" / "bootstrap_draws.npy"
        sha = L.sha256_file(dpath)
        draws = np.load(dpath, allow_pickle=False)
        B, G = draws.shape
        assert B == L.N_DRAWS
        gen_ok = all(L.generator_row(p, 0, b, G) == draws[b].tolist() for b in range(B))
        Cs = np.vstack([np.ones((1, G)), L.draw_counts(draws, G)])
        gl = json.loads((L.VB / "work" / ("global_%s.json" % p)).read_text(encoding="utf-8"))
        gi = set(gl["global_indices"])
        metas = {m: json.loads((lead / m / "meta.json").read_text(encoding="utf-8")) for m in models}
        rows = {"feature": {}, "variable": {}}
        keys0 = None
        pre = {}
        for m in models:
            for level in ("feature", "variable"):
                k, players, X = L.load_rows(lead / m / "rows.parquet", level, ("row", "group", "pre"))
                if keys0 is None:
                    keys0 = k[["row", "group"]].copy()
                assert k["row"].tolist() == keys0["row"].tolist() and k["group"].tolist() == keys0["group"].tolist(), (p, m)
                assert np.isfinite(X).all(), (p, m, level)
                rows[level][m] = (players, X)
                pre[m] = k["pre"].to_numpy()
        regions = sorted(keys0["group"].unique().tolist())
        assert len(regions) == G, (p, len(regions), G)
        rix = {r: i for i, r in enumerate(regions)}
        region = np.array([rix[g] for g in keys0["group"]])
        allvars = sorted(set().union(*[set(rows["variable"][m][0]) for m in models]))
        vf = {v: L.family_of(v, gi) for v in allvars}
        fam = {m: L.family_stack(rows["variable"][m][0], rows["variable"][m][1], vf, region, G, Cs) for m in models}
        D = L.Draws()
        pr = {"lead": 0}
        pr.update({k: st[k] for k in STRUCT})
        pr["draws"] = {"path": L.short(dpath), "shape": [int(B), int(G)], "dtype": str(draws.dtype),
                       "sha256_computed": sha,
                       "sha256_covers": "every byte of the .npy file as saved (header and data), read in binary",
                       "sha256_per_lead": sha_per_lead, "sha256_match": sha == sha_per_lead,
                       "region_source": "rows.parquet column `group` (the engine's region of the row; the same in every piece of the problem)",
                       "regions_in_draw_order": regions,
                       "npz": "V\\B\\draws\\%s.npz" % p,
                       "extra": {"generator_reproduces_matrix": gen_ok,
                                 "generator": "value[b, k] = int.from_bytes(SHA-256('shap_v1|AW4|<problem>|0|<b>|<k>')[:8], 'big') mod G; row b = draw b (0-based), column k = the k-th region drawn",
                                 "rows_per_region_min_max": [int(np.bincount(region).min()), int(np.bincount(region).max())]}}
        levels, keep = {}, {}
        for level in ("feature", "variable"):
            meta_nz = {m: (metas[m].get("players_nonzero") if level == "feature" else metas[m].get("variables_nonzero")) for m in models}
            levels[level], keep[level] = compute_level(level, models, main_set, links, declined, region, G, Cs,
                                                       rows[level], fam, D, meta_nz)
        levels["variable"]["families"] = {
            "variable_family": {v: vf[v] for v in allvars},
            "global_indices": sorted(v for v in allvars if vf[v] == "global_indices"),
            "test_set_records": gl["records"],
            "test_set_columns": gl["columns_read"],
            "extra": {"test_rows": gl["n_test_rows"], "time_steps": gl["n_time_steps"], "units": gl["n_units"],
                      "time_steps_with_one_row": gl["time_steps_with_one_row"],
                      "same_result_if_missing_values_are_ignored": gl["global_indices"] == gl["global_indices_ignore_missing"],
                      "families_with_no_variable": [f for f in L.FAMILIES if not any(vf[v] == f for v in allvars)]}}
        pr["levels"] = levels
        # item 7: main-text row (variable level)
        kv = keep["variable"]
        Jv, MBv = kv["J"], kv["MB"]
        rivals = sorted(m for m in main_set if m != "treeroute")
        mr = {"level": "variable", "main_set": list(main_set), "rivals": rivals}
        mb = ["main_row"]
        own_idx = L.FAMILIES.index("own_history")
        tr = "treeroute"
        mr["treeroute_top3"] = L.top_list(Jv, MBv[tr]["ORD"][0], MBv[tr]["SH"][0], 3)
        mr["own_history_share_treeroute"] = D.iv(mb + ["own_history_share_treeroute"], fam[tr][:, own_idx])
        if rivals:
            mr["kendall_w"] = D.iv(mb + ["kendall_w"], L.kendall_w_rows([MBv[m]["IJ"] for m in main_set]))
            s20 = np.vstack([kv["PS"][tuple(sorted((tr, r))) + ("u20",)] for r in rivals])
            mr["spearman_top20_union_median"] = D.iv(mb + ["spearman_top20_union_median"], np.median(s20, axis=0))
            mr["spearman_top20_union_min"] = D.iv(mb + ["spearman_top20_union_min"], np.min(s20, axis=0))
            mr["spearman_top20_union_max"] = D.iv(mb + ["spearman_top20_union_max"], np.max(s20, axis=0))
            mr["spearman_top20_union_per_rival"] = {r: float(s20[i, 0]) for i, r in enumerate(rivals)}
            cons = np.mean([MBv[r]["SH"] for r in rivals], axis=0)
            co = L.order_by_importance(cons)
            mr["rbo_p090_vs_consensus"] = D.iv(mb + ["rbo_p090_vs_consensus"],
                                               L.rbo_rows(MBv[tr]["POS"], L.positions(co), 0.9))
            mr["consensus_shares"] = {Jv[i]: float(cons[0, i]) for i in range(len(Jv))}
            mr["consensus_top3"] = L.top_list(Jv, co[0], cons[0], 3)
            oh = np.vstack([fam[r][:, own_idx] for r in rivals])
            mr["own_history_share_median_rival"] = D.iv(mb + ["own_history_share_median_rival"], np.median(oh, axis=0))
            mr["own_history_share_per_rival"] = {r: float(oh[i, 0]) for i, r in enumerate(rivals)}
            if len(rivals) % 2 == 1:
                med = np.median(oh[:, 0])
                cand = [r for i, r in enumerate(rivals) if oh[i, 0] == med]
                if len(cand) == 1:
                    mr["median_rival_name"] = cand[0]
                else:
                    mr["median_rival_name"] = None
                    mr["median_rival_name_why"] = ("%d rivals share the median own-history share on the full sample "
                                                   "(%s), so no single rival is the median one." % (len(cand), ", ".join(cand)))
            else:
                mr["median_rival_name"] = None
                mr["median_rival_name_why"] = ("%d rivals: the median of their own-history shares is the mean of the "
                                               "two middle values, not one rival's (choices.md C23)." % len(rivals))
            mr["extra"] = {"kendall_w_equals_per_problem_variable":
                           levels["variable"]["per_problem"]["kendall_w"]["value"] == mr["kendall_w"]["value"]}
        else:
            why = ("The main set is treeroute alone (every rival is on another link): no same-link rival, so this "
                   "number is undefined (section 8; brief item 7).")
            for k in ("kendall_w", "spearman_top20_union_median", "spearman_top20_union_min", "spearman_top20_union_max",
                      "spearman_top20_union_per_rival", "rbo_p090_vs_consensus", "consensus_shares", "consensus_top3",
                      "own_history_share_median_rival", "own_history_share_per_rival", "median_rival_name"):
                mr[k] = None
                mr[k + "_why"] = why
        pr["main_row"] = mr
        # item 8: arcsine-link models on their rows with pre > 0 (variable level, the level's J)
        arc = sorted(m for m in models if links[m].split("|")[0] == "arcsine")
        nzf = {"models_covered": arc,
               "models_covered_why": ("Every model of this problem whose link (per_lead.json links) is arcsine "
                                      "(section 8: 'For every arcsine-link model'), problem by problem.") if arc else
                                     "No model of this problem has the arcsine link.",
               "models": {}}
        Uv = kv["U"]
        uvi = {n: k for k, n in enumerate(Uv)}
        jv_idx = np.array([uvi[n] for n in Jv])
        for m in arc:
            vars_m, Xv = rows["variable"][m]
            Xu = np.zeros((Xv.shape[0], len(Uv)))
            cols = [uvi[n] for n in vars_m]
            Xu[:, cols] = Xv
            ownm = np.zeros(len(Uv), dtype=bool)
            ownm[cols] = True
            sel = pre[m] > 0
            A, nr = L.region_means(np.abs(Xu[sel]), region[sel], G)
            Ag, _ = L.region_means(Xu[sel], region[sel], G)
            present = nr > 0
            Iall = L.weighted_over_regions(Cs, A, present=present)
            Sall = L.weighted_over_regions(Cs, Ag, present=present)
            IJm = Iall[:, jv_idx]
            with np.errstate(invalid="ignore", divide="ignore"):
                SHm = IJm / IJm.sum(axis=1, keepdims=True)
            SGm = Sall[:, jv_idx]
            ordm = L.order_by_importance(np.where(np.isfinite(IJm), IJm, -np.inf))
            detm = L.determined(SGm[1:])
            nzc = ((Iall > 0) & ownm[None, :]).sum(axis=1).astype(np.float64)
            nzc[~np.isfinite(Iall).all(axis=1)] = np.nan
            nb = ["nonzero_forecast", "models", m]
            nzf["models"][m] = {"level": "variable", "rows_used": int(sel.sum()), "regions_used": int(present.sum()),
                                "J": list(Jv),
                                "players": D.players(nb + ["players"], Jv, IJm, SHm, SGm, detm),
                                "n_nonzero": D.iv(nb + ["n_nonzero"], nzc),
                                "ranking": [Jv[i] for i in ordm[0]],
                                "top10": L.top_list(Jv, ordm[0], SHm[0], 10),
                                "extra": {"draws_with_no_region_holding_such_a_row": int((~np.isfinite(Iall[1:, 0])).sum())}}
        pr["nonzero_forecast"] = nzf
        pr["extra"] = {"seconds": round(time.time() - t0, 1),
                       "row_keys_identical_over_models": True,
                       "rows_flagged_resid": {m: metas[m].get("rows_flagged_resid") for m in models}}
        res[p] = pr
        np.savez_compressed(L.VB / "draws" / ("%s.npz" % p), **D.a)
        print("%s done in %.1f s (J feature %d, variable %d; draws sha match %s; generator %s)" % (
            p, time.time() - t0, len(keep["feature"]["J"]), len(Jv), pr["draws"]["sha256_match"], gen_ok))
    L.dump_json(res, L.VB / "work" / "problems.json")
    print("items 1-8 done in %.1f s" % (time.time() - t_all))


if __name__ == "__main__":
    main(sys.argv[1:] or PROBLEMS)
