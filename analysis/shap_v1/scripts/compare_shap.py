"""AW3 disagreement tables and AW4 agreement statistics for one problem-lead (PROTOCOL.md section 8, v3).

  py -3.9 -I -B compare_shap.py --problem coral --lead 0 [--models-root DIR] [--sample-root DIR] [--register FILE]
        [--draws 2000] [--out DIR]

Reads every <models-root>/<model>/rows.parquet with a done record (treeroute, rival_*). Refuses (S-SAMPLE / S-BG)
unless every model's done record and meta.json name the CURRENT registered sample, the explained (row, unit, time,
group) keys are identical, and the background keys are identical row by row (one value function for every model).
Two levels: feature (phi__) and variable (phiv__, the exact grouped game; the main-text level); families (own
history, global indices, local drivers, context and calendar, seasonal normal) are sums of the variable-level phi per
row. Model sets: a pair is 'same-link' when both models explain in the same link space (same link, c and ub) and
'cross-link' otherwise (reported, never pooled: shares and ranks depend on the link); a rival declined by its own
guard is labelled 'raw model, declined by its guard' (D6) and kept out of Kendall's W, the consensus and the main row.
The main set is treeroute plus its same-link, guard-passing rivals (at a lead without treeroute SHAP: the largest
same-link set of guard-passing rivals). Writes compare/: importance.parquet, families.parquet, pairs.parquet,
per_lead.json, bootstrap_draws.npy (+ SHA-256 in per_lead.json), bootstrap_stats.parquet, AW3_table.md, AW4_table.md,
AW4_main_row.json. Statistics: shapv1_stats.py (checked on constructed examples, smoke S1).
"""
import argparse
import os
import sys
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import shapv1_common as C  # noqa: E402

C.pin_threads(1)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

import shapv1_stats as ST  # noqa: E402

J_REL = 1e-12                     # a player is active when some model gives it more than this share of its total
TOPU = 20
FAMILIES = ("own history", "global indices", "local drivers", "context and calendar", "seasonal normal")


def parse():
    ap = argparse.ArgumentParser()
    ap.add_argument("--problem", required=True, choices=sorted(C.PROBLEMS))
    ap.add_argument("--lead", type=int, required=True)
    ap.add_argument("--models-root", default=None)
    ap.add_argument("--sample-root", default=None)
    ap.add_argument("--register", default=None)
    ap.add_argument("--draws", type=int, default=2000)
    ap.add_argument("--out", default=None)
    return ap.parse_args()


def global_columns(problem, lead, players):
    """x__ columns whose value at a time step is the same for every unit of the lead's test set (a data rule)."""
    files = C.export_files(problem, lead, "test")
    frames = []
    xs = [p for p in players if p.startswith("x__")]
    for g, f in sorted(files.items()):
        cols = [c for c in pq.read_schema(f).names if c in xs]
        frames.append(pq.read_table(f, columns=["unit", "time"] + cols).to_pandas())
    T = pd.concat(frames, ignore_index=True)
    out = set()
    if T.groupby("time")["unit"].nunique().max() < 2:
        return out
    cnt = T.groupby("time")["unit"].nunique()
    for c in xs:
        if c not in T.columns:
            continue
        nun = T.groupby("time")[c].nunique(dropna=True)
        if (nun[cnt > 1] <= 1).all():
            out.add(c)
    return out


def link_key(meta):
    c = meta.get("c")
    ub = meta.get("ub")
    return "%s|c=%s|ub=%s" % (meta.get("link"), "-" if c is None else "%.12g" % float(c),
                              "-" if ub is None else "%.12g" % float(ub))


def load_models(a, root, log):
    sroot = a.sample_root or C.sample_dir(a.problem)
    ident = C.sample_identity(a.problem, sroot, a.register, lead=a.lead)
    models = []
    for d in sorted(os.listdir(root)):
        f = os.path.join(root, d, "rows.parquet")
        if (d == "treeroute" or d.startswith("rival_")) and os.path.isfile(f) and os.path.isfile(f + ".done.json"):
            models.append(d)
    if len(models) < 2:
        raise SystemExit("fewer than two finished models in %s: %s" % (root, models))
    frames, metas, bkeys = {}, {}, {}
    for m in models:
        done = C.read_json(os.path.join(root, m, "rows.parquet.done.json"))
        meta = C.read_json(os.path.join(root, m, "meta.json"))
        if done.get("sha256") != C.sha256_file(os.path.join(root, m, "rows.parquet")):
            raise SystemExit("REFUSED: %s rows.parquet changed after its done record" % m)
        if done.get("sample_sha256") != ident["sample_sha256"] or meta.get("sample_sha256") != ident["sample_sha256"]:
            raise SystemExit("STOP S-SAMPLE: %s explains sample %s, the registered sample is %s" % (
                m, str(done.get("sample_sha256"))[:16], ident["sample_sha256"][:16]))
        frames[m] = pq.read_table(os.path.join(root, m, "rows.parquet")).to_pandas().sort_values(
            "row").reset_index(drop=True)
        metas[m] = meta
        bkeys[m] = pq.read_table(os.path.join(root, m, "background_keys.parquet")).to_pandas()
    k0 = frames[models[0]][["row", "unit", "time", "group"]].astype(str)
    b0 = bkeys[models[0]].astype(str).sort_values(["row", "unit", "time"]).reset_index(drop=True)
    for m in models[1:]:
        if not frames[m][["row", "unit", "time", "group"]].astype(str).equals(k0):
            raise SystemExit("STOP S-SAMPLE: %s explains other (row, unit, time, group) keys than %s" % (m, models[0]))
        bm = bkeys[m].astype(str).sort_values(["row", "unit", "time"]).reset_index(drop=True)
        if not bm.equals(b0):
            raise SystemExit("STOP S-BG: %s has other background keys than %s (one value function for every model)"
                             % (m, models[0]))
    log("%d models, the same %d rows and %d background keys, registered sample %s"
        % (len(models), len(k0), len(b0), ident["sample_sha256"][:16]))
    return models, frames, metas, ident


def matrices(models, frames, pref):
    allp = sorted(set(c[len(pref):] for m in models for c in frames[m].columns if c.startswith(pref)))
    pidx = {p: j for j, p in enumerate(allp)}
    P = {}
    for m in models:
        M_ = np.zeros((len(frames[m]), len(allp)))
        for c in frames[m].columns:
            if c.startswith(pref):
                M_[:, pidx[c[len(pref):]]] = frames[m][c].to_numpy(np.float64)
        P[m] = M_
    return allp, P


def region_means(P, rpos, nreg):
    cnt = np.bincount(rpos, minlength=nreg).astype(float)
    A = np.vstack([np.bincount(rpos, weights=np.abs(P[:, j]), minlength=nreg) / cnt for j in range(P.shape[1])]).T
    S = np.vstack([np.bincount(rpos, weights=P[:, j], minlength=nreg) / cnt for j in range(P.shape[1])]).T
    return A, S                                          # regions x players


def main():
    a = parse()
    log = C.Log("compare_%s_lead%d" % (a.problem, a.lead))
    root = a.models_root or C.out_dir(a.problem, a.lead)
    out = C.makedirs(a.out or os.path.join(root, "compare"))
    models, frames, metas, ident = load_models(a, root, log)
    F0 = frames[models[0]]
    regions = F0["group"].astype(str).to_numpy()
    ureg = sorted(set(regions))
    rpos = np.asarray([ureg.index(r) for r in regions])
    nreg = len(ureg)
    lk = {m: link_key(metas[m]) for m in models}
    declined = {m: (metas[m].get("guard") or {}).get("passed") is False for m in models}
    tr = "treeroute" if "treeroute" in models else None
    if tr:
        ref_link = lk[tr]
    else:
        cand = {}
        for m in models:
            if not declined[m]:
                cand.setdefault(lk[m], []).append(m)
        ref_link = sorted(cand.items(), key=lambda kv: (-len(kv[1]), kv[0]))[0][0] if cand else None
    main_set = [m for m in models if lk[m] == ref_link and not declined[m]]
    log("links %s; declined by their guard %s; main set (same link %s, guard passed) %s"
        % (lk, [m for m in models if declined[m]], ref_link, main_set))
    D = C.draw_matrix("shap_v1|AW4|%s|%d" % (a.problem, a.lead), nreg, a.draws)
    np.save(C.assert_writable(os.path.join(out, "bootstrap_draws.npy")), D)
    dsha = C.sha256_file(os.path.join(out, "bootstrap_draws.npy"))
    W8 = [np.bincount(D[b], minlength=nreg).astype(float) for b in range(a.draws)]
    levels = {}
    reps_rows = []
    for level, pref in (("variable", "phiv__"), ("feature", "phi__")):
        players, Pm = matrices(models, frames, pref)
        absr, sgnr = {}, {}
        for m in models:
            absr[m], sgnr[m] = region_means(Pm[m], rpos, nreg)
        I = {m: absr[m].mean(0) for m in models}
        S = {m: sgnr[m].mean(0) for m in models}
        act = np.zeros(len(players), bool)
        for m in models:
            tot = I[m].sum()
            if tot > 0:
                act |= I[m] > J_REL * tot
        J = [players[j] for j in np.flatnonzero(act)]
        zero = [players[j] for j in np.flatnonzero(~act)]
        ja = np.flatnonzero(act)
        order = ST.rankdata(np.arange(len(J)))
        ks = (5, 10, 20) if len(J) >= 200 else (5, 10)
        pairs = [(m1, m2) for i, m1 in enumerate(models) for m2 in models[i + 1:]]

        def stats_of(Iv):
            profs = {m: ST.profile(Iv[m][ja], order) for m in models}
            res = {pq_: ST.pair_from_profiles(profs[pq_[0]], profs[pq_[1]], ks=ks, top_union_k=TOPU)
                   for pq_ in pairs}
            res["W"] = ST.kendall_w_profiles([profs[m] for m in main_set]) if len(main_set) > 1 else float("nan")
            sp = [res[pq_]["spearman"] for pq_ in pairs if pq_[0] in main_set and pq_[1] in main_set]
            res["mean_spearman_main"] = float(np.mean(sp)) if sp else float("nan")
            return res, profs
        full, fprof = stats_of(I)
        # bootstrap: the same region draws for every model
        t0 = time.time()
        reps, stab = [], {m: [] for m in models}
        Sb_all = {m: np.empty((a.draws, len(players))) for m in models}
        Ib_all = {m: np.empty((a.draws, len(players))) for m in models}
        for b in range(a.draws):
            w = W8[b]
            Ib = {m: (absr[m] * w[:, None]).sum(0) / nreg for m in models}
            for m in models:
                Ib_all[m][b] = Ib[m]
                Sb_all[m][b] = (sgnr[m] * w[:, None]).sum(0) / nreg
                stab[m].append(ST.spearman(I[m][ja], Ib[m][ja]))
            r, _ = stats_of(Ib)
            reps.append(r)
        log("%s level: %d players, %d active, %d structural zero; %d pairs; %d draws over %d regions in %.1f s"
            % (level, len(players), len(J), len(zero), len(pairs), a.draws, nreg, time.time() - t0))
        # signs: determined when the bootstrap 95% interval of the signed mean excludes 0
        det = {}
        for m in models:
            lo = np.quantile(Sb_all[m], 0.025, axis=0)
            hi = np.quantile(Sb_all[m], 0.975, axis=0)
            det[m] = (lo > 0) | (hi < 0)
        rows = []
        for pq_ in pairs:
            m1, m2 = pq_
            label = "same-link" if lk[m1] == lk[m2] else "cross-link (not comparable in scale or rank)"
            dl = [x for x in pq_ if declined[x]]
            if dl:
                label += "; raw model, declined by its guard: %s" % ", ".join(dl)
            keep = ST.topk(I[m1][ja], order, 10) | ST.topk(I[m2][ja], order, 10)
            sg, nsg = ST.sign_agreement(S[m1][ja], S[m2][ja], keep, det[m1][ja], det[m2][ja])
            vals = dict(full[pq_], sign_agreement_top10=sg)
            for s, v in vals.items():
                if s == "sign_agreement_top10":
                    lo = hi = float("nan")
                    nfin = 0
                else:
                    lo, hi, nfin = ST.percentile_ci([r[pq_][s] for r in reps])
                rows.append({"level": level, "model_a": m1, "model_b": m2, "pair_label": label, "statistic": s,
                             "value": v, "ci_low": lo, "ci_high": hi, "finite_replicates": nfin,
                             "signs_compared": nsg if s == "sign_agreement_top10" else None})
            for b, r in enumerate(reps):
                reps_rows.append({"level": level, "draw": b, "pair": "%s|%s" % pq_, "spearman": r[pq_]["spearman"],
                                  "spearman_top20_union": r[pq_]["spearman_top%d_union" % TOPU],
                                  "rbo_p0.9": r[pq_]["rbo_p0.9"], "tvd": r[pq_]["tvd"]})
        wlo, whi, wn = ST.percentile_ci([r["W"] for r in reps])
        mlo, mhi, mn = ST.percentile_ci([r["mean_spearman_main"] for r in reps])
        imp = pd.DataFrame([{"level": level, "model": m, "player": players[j], "active": bool(act[j]),
                             "mean_abs": I[m][j], "share": I[m][j] / I[m][ja].sum() if I[m][ja].sum() > 0 else
                             float("nan"), "signed_mean": S[m][j], "sign_determined": bool(det[m][j])}
                            for m in models for j in range(len(players))])
        levels[level] = {"players": players, "J": J, "ja": ja, "zero": zero, "I": I, "S": S, "full": full,
                         "reps": reps, "rows": rows, "imp": imp, "W": (full["W"], wlo, whi, wn),
                         "mean_rho": (full["mean_spearman_main"], mlo, mhi, mn), "order": order,
                         "stab": {m: float(np.nanmean(v)) for m, v in stab.items()}, "Ib_all": Ib_all, "Pm": Pm,
                         "absr": absr, "ks": ks}
    # families (variable level): per row, the sum of the variable-level phi of the family's variables
    V = levels["variable"]
    gcols = global_columns(a.problem, a.lead, levels["feature"]["players"])
    vmaps = {}
    for m in models:
        vmaps.update(metas[m].get("variable_map") or {})
    members = {}
    for p, v in vmaps.items():
        members.setdefault(v, []).append(p)
    fam_of = {v: C.family_of(v, members.get(v, []), gcols) for v in V["players"]}
    fam_rows, fam_abs = [], {}
    for m in models:
        Pm = V["Pm"][m]
        cols = {f: [j for j, v in enumerate(V["players"]) if fam_of[v] == f] for f in FAMILIES}
        Fm = np.column_stack([Pm[:, cols[f]].sum(1) if cols[f] else np.zeros(Pm.shape[0]) for f in FAMILIES])
        Af, _ = region_means(Fm, rpos, nreg)
        fam_abs[m] = Af
        If = Af.mean(0)
        for k, f in enumerate(FAMILIES):
            fam_rows.append({"model": m, "family": f, "mean_abs": If[k],
                             "share": If[k] / If.sum() if If.sum() > 0 else float("nan")})
    fams = pd.DataFrame(fam_rows)

    def fam_share(m, w=None, f="own history"):
        Af = fam_abs[m]
        If = Af.mean(0) if w is None else (Af * w[:, None]).sum(0) / nreg
        return float(If[FAMILIES.index(f)] / If.sum()) if If.sum() > 0 else float("nan")
    lv = levels["variable"]                        # the family TVD (families nest the variables): variable level
    for i, m1 in enumerate(models):
        for m2 in models[i + 1:]:
            ta = np.asarray([fam_share(m1, None, f) for f in FAMILIES])
            tb = np.asarray([fam_share(m2, None, f) for f in FAMILIES])
            reps_f = []
            for w in W8:
                xa = np.asarray([fam_share(m1, w, f) for f in FAMILIES])
                xb = np.asarray([fam_share(m2, w, f) for f in FAMILIES])
                reps_f.append(0.5 * np.abs(xa - xb).sum())
            lo, hi, nfin = ST.percentile_ci(reps_f)
            lab = [r for r in lv["rows"] if r["model_a"] == m1 and r["model_b"] == m2][0]["pair_label"]
            lv["rows"].append({"level": "variable", "model_a": m1, "model_b": m2, "pair_label": lab,
                               "statistic": "tvd_family", "value": 0.5 * np.abs(ta - tb).sum(), "ci_low": lo,
                               "ci_high": hi, "finite_replicates": nfin, "signs_compared": None})
    pairs_df = pd.DataFrame(levels["variable"]["rows"] + levels["feature"]["rows"])
    C.write_parquet(os.path.join(out, "pairs.parquet"), pairs_df)
    C.write_parquet(os.path.join(out, "importance.parquet"), pd.concat([levels[l]["imp"] for l in levels],
                                                                       ignore_index=True))
    C.write_parquet(os.path.join(out, "families.parquet"), fams)
    C.write_parquet(os.path.join(out, "bootstrap_stats.parquet"), pd.DataFrame(reps_rows))
    # nonzero-forecast rows of arcsine models (fire: 75% of treeroute's kept forecasts are exactly 0)
    nonzero = {}
    for m in models:
        if str(metas[m].get("link")) == "arcsine":
            sel = frames[m]["pre"].to_numpy(np.float64) > 0
            if sel.any():
                Pz = V["Pm"][m][sel]
                cz = np.bincount(rpos[sel], minlength=nreg).astype(float)
                Az = np.vstack([np.bincount(rpos[sel], weights=np.abs(Pz[:, j]), minlength=nreg)
                                for j in range(Pz.shape[1])]).T
                Iz = (Az[cz > 0] / cz[cz > 0][:, None]).mean(0)       # each region with such rows weighs 1
                o = np.argsort(-Iz)[:10]
                nonzero[m] = {"rows": int(sel.sum()), "top10": [[V["players"][j], float(Iz[j] / Iz.sum())]
                                                               for j in o if Iz.sum() > 0]}
    # the main row (variable level, main set), every number with its bootstrap interval
    main_row = main_text_row(a, models, main_set, tr, declined, lk, ref_link, V, fam_share, W8, nreg, levels)
    C.write_json(os.path.join(out, "AW4_main_row.json"), main_row)
    per = {"problem": a.problem, "lead": a.lead, "models": models, "links": lk, "declined_by_guard":
           [m for m in models if declined[m]], "main_set": main_set, "reference_link": ref_link,
           "rows": int(len(F0)), "regions": nreg, "draws": a.draws, "draws_sha256": dsha,
           "salt": "shap_v1|AW4|%s|%d" % (a.problem, a.lead), "sample_sha256": ident["sample_sha256"],
           "global_columns": sorted(gcols), "families": fam_of, "nonzero_forecast_rows": nonzero,
           "j_rule": "player active when some model gives it > %g of its total" % J_REL}
    for l, lv in levels.items():
        per[l] = {"players": len(lv["players"]), "active": len(lv["J"]), "structural_zero": lv["zero"],
                  "kendall_w_main_set": {"value": lv["W"][0], "ci": [lv["W"][1], lv["W"][2]],
                                         "finite_replicates": lv["W"][3]},
                  "mean_pairwise_spearman_main_set": {"value": lv["mean_rho"][0], "ci": [lv["mean_rho"][1],
                                                                                         lv["mean_rho"][2]],
                                                      "finite_replicates": lv["mean_rho"][3]},
                  "stability_under_region_resampling": lv["stab"],
                  "nonzero_players": {m: ST.n_nonzero(lv["I"][m][lv["ja"]]) for m in models}}
    C.write_json(os.path.join(out, "per_lead.json"), per)
    write_tables(a, out, models, lk, declined, main_set, levels, fams, nonzero, main_row, per)
    C.mark_done(os.path.join(out, "pairs.parquet"), {"models": models, "draws": a.draws,
                                                      "sample": ident["sample_sha256"],
                                                      "rows": {m: C.sha256_file(os.path.join(root, m, "rows.parquet"))
                                                               for m in models}})
    log("compare written to %s" % out)


def main_text_row(a, models, main_set, tr, declined, lk, ref_link, V, fam_share, W8, nreg, levels):
    ja, order, J = V["ja"], V["order"], V["J"]
    row = {"problem": a.problem, "lead": a.lead, "level": "variable", "models_in_main_set": main_set,
           "reference_link": ref_link, "kendall_w": {"value": V["W"][0], "ci": [V["W"][1], V["W"][2], V["W"][3]]},
           "ci_format": "[low, high, finite replicates]"}
    rivals = [m for m in main_set if m != tr]
    if not tr:
        row["treeroute"] = "no feature attribution (feature-free baseline kept, D5)"
    cross = [m for m in models if m != tr and lk[m] != ref_link and not declined[m]]
    if tr and not rivals:
        row["link_note"] = ("no guard-passing rival explains in treeroute's link space (%s): treeroute-against-rival "
                            "agreement cannot separate the link from the model; cross-link pairs are in S3.13 only"
                            % ref_link)
    key = "spearman_top%d_union" % TOPU
    full = V["full"]

    def pair_val(res, m1, m2, s):
        return res[(m1, m2)][s] if (m1, m2) in res else res[(m2, m1)][s]
    if tr and rivals:
        def med(res):
            return float(np.median([pair_val(res, tr, m, key) for m in rivals]))

        def cons_rbo(Iv):
            cons = np.mean([Iv[m][ja] / Iv[m][ja].sum() for m in rivals], 0)
            return ST.rbo_full(Iv[tr][ja], cons, order, 0.9), cons
        rb, cons = cons_rbo(V["I"])
        reps_med, reps_rbo, reps_h_tr, reps_h_rv = [], [], [], []
        for b, w in enumerate(W8):
            reps_med.append(med(V["reps"][b]))
            Ib = {m: V["Ib_all"][m][b] for m in main_set}
            reps_rbo.append(cons_rbo(Ib)[0])
            reps_h_tr.append(fam_share(tr, w))
            reps_h_rv.append(float(np.median([fam_share(m, w) for m in rivals])))
        ci = lambda v: list(ST.percentile_ci(v))  # noqa: E731  (low, high, finite replicates)
        row.update({"treeroute_vs_same_link_rivals_median_spearman_top20_union": {
                        "value": med(full), "ci": ci(reps_med),
                        "range": [float(np.min([pair_val(full, tr, m, key) for m in rivals])),
                                  float(np.max([pair_val(full, tr, m, key) for m in rivals]))]},
                    "rbo_vs_consensus_p0.9": {"value": rb, "ci": ci(reps_rbo)},
                    "treeroute_top3": [J[i] for i in ST.ranked(V["I"][tr][ja], order)[:3]],
                    "consensus_top3": [J[i] for i in ST.ranked(cons, order)[:3]],
                    "own_history_share_treeroute": {"value": fam_share(tr), "ci": ci(reps_h_tr)},
                    "own_history_share_median_rival": {"value": float(np.median([fam_share(m) for m in rivals])),
                                                       "ci": ci(reps_h_rv)}})
    elif rivals or (not tr and len(main_set) > 1):
        cons = np.mean([V["I"][m][ja] / V["I"][m][ja].sum() for m in main_set], 0)
        row["consensus_top3"] = [J[i] for i in ST.ranked(cons, order)[:3]]
    row["cross_link_models"] = cross
    row["declined_models"] = [m for m in models if declined[m]]
    return row


def fmt(v):
    return "nan" if v is None or not np.isfinite(v) else "%.2f" % v


def write_tables(a, out, models, lk, declined, main_set, levels, fams, nonzero, main_row, per):
    L = ["# AW3: disagreement of SHAP importances, %s lead %d (post hoc, ruling AK)" % (a.problem, a.lead), "",
         "%d rows in %d regions; link space; percentile 95%% intervals from %d paired region draws. Same-link pairs "
         "are comparable; cross-link pairs are shown for completeness and are not comparable in scale or rank. A rival "
         "declined by its own guard is labelled and kept out of W, the consensus and the main row (D6)."
         % (per["rows"], per["regions"], a.draws), "",
         "Models and links: " + "; ".join("%s (%s%s)" % (m, lk[m], ", declined by its guard" if declined[m] else "")
                                          for m in models), "", "Main set: %s" % ", ".join(main_set), ""]
    for level in ("variable", "feature"):
        lv = levels[level]
        stats = [s for s in ("spearman", "spearman_top20_union", "kendall_tau_b", "jaccard_top5", "jaccard_top10",
                             "jaccard_top20", "rbo_p0.9", "rbo_p0.95", "tvd", "tvd_family", "sign_agreement_top10")
                 if any(r["statistic"] == s for r in lv["rows"])]
        L += ["## %s level (%d players, %d active; structural zeros: %s)" % (
            level, len(lv["players"]), len(lv["J"]), ", ".join(lv["zero"][:30]) or "none"), "",
            "| Pair | label | " + " | ".join(stats) + " |", "|---|---|" + "---|" * len(stats)]
        df = pd.DataFrame(lv["rows"])
        for (m1, m2), g in df.groupby(["model_a", "model_b"], sort=False):
            cells = []
            for s in stats:
                r = g[g.statistic == s]
                if not len(r):
                    cells.append("")
                    continue
                r = r.iloc[0]
                if s == "sign_agreement_top10":
                    cells.append("%s (%s signs)" % (fmt(r.value), int(r.signs_compared or 0)))
                else:
                    cells.append("%s [%s, %s]" % (fmt(r.value), fmt(r.ci_low), fmt(r.ci_high)))
            L.append("| %s vs %s | %s | %s |" % (m1, m2, g.pair_label.iloc[0], " | ".join(cells)))
        W = lv["W"]
        L += ["", "Kendall's W (main set) = %s [%s, %s]; mean pairwise Spearman (main set) = %s [%s, %s]." % (
            fmt(W[0]), fmt(W[1]), fmt(W[2]), fmt(lv["mean_rho"][0]), fmt(lv["mean_rho"][1]), fmt(lv["mean_rho"][2])),
            "Stability under region resampling (mean Spearman of a model's full-sample importances with its own "
            "bootstrap replicates; descriptive, not a ceiling on between-model agreement): " +
            ", ".join("%s %s" % (m, fmt(v)) for m, v in lv["stab"].items()), ""]
        imp = lv["imp"]
        for m in models:
            top = imp[(imp.model == m) & imp.active].sort_values(["share", "player"], ascending=[False, True]).head(10)
            L.append("- %s top-10 (%d nonzero): %s" % (m, per[level]["nonzero_players"][m], "; ".join(
                "%s %.1f%%" % (p, 100 * s) for p, s in zip(top.player, top.share))))
        L.append("")
    L += ["## Families (sums of the variable-level attributions per row)", "",
          "| Family | " + " | ".join(models) + " |", "|---|" + "---|" * len(models)]
    pv = fams.pivot(index="family", columns="model", values="share")
    for f in FAMILIES:
        if f in pv.index:
            L.append("| %s | %s |" % (f, " | ".join("%.1f%%" % (100 * pv.loc[f, m]) if m in pv.columns and
                                                     np.isfinite(pv.loc[f, m]) else "" for m in models)))
    if nonzero:
        L += ["", "## Nonzero forecasts of arcsine-link models (rows with pre > 0)", ""]
        for m, v in nonzero.items():
            L.append("- %s, %d rows: %s" % (m, v["rows"], "; ".join("%s %.1f%%" % (p, 100 * s) for p, s in v["top10"])))
    C.write_text(os.path.join(out, "AW3_table.md"), "\n".join(L) + "\n")
    r = main_row

    def iv(k):
        x = r.get(k)
        if not isinstance(x, dict):
            return ""
        return "%s [%s, %s]" % (fmt(x["value"]), fmt(x["ci"][0]), fmt(x["ci"][1]))
    sp = r.get("treeroute_vs_same_link_rivals_median_spearman_top20_union")
    hd = ("| Problem, lead | Main set | W [95% CI] | treeroute vs same-link rivals: median rho, top-20 union [CI] "
          "(range) | RBO vs consensus [CI] | treeroute top 3 | consensus top 3 | own history: treeroute [CI] / "
          "median rival [CI] |\n|---|---|---|---|---|---|---|---|\n")
    line = "| %s %d | %s | %s | %s | %s | %s | %s | %s |\n" % (
        a.problem, a.lead, ", ".join(r["models_in_main_set"]), iv("kendall_w"),
        ("%s (%s to %s)" % (iv("treeroute_vs_same_link_rivals_median_spearman_top20_union"), fmt(sp["range"][0]),
                            fmt(sp["range"][1]))) if sp else r.get("treeroute", r.get("link_note", "")),
        iv("rbo_vs_consensus_p0.9"), ", ".join(r.get("treeroute_top3", [])), ", ".join(r.get("consensus_top3", [])),
        ("%s / %s" % (iv("own_history_share_treeroute"), iv("own_history_share_median_rival")))
        if "own_history_share_treeroute" in r else "")
    note = "\nVariable level; post hoc (ruling AK). %s\n" % (r.get("link_note") or "")
    C.write_text(os.path.join(out, "AW4_table.md"), hd + line + note)


if __name__ == "__main__":
    main()
