"""Post-hoc selection-noise diagnosis for the coral headline run (read-only on the run).

Run: python -I D:\\treeroute\\analysis\\coral_choice\\noise\\noise_analysis.py
Writes only into this folder: results.json, contrasts.csv, per_group_gap.csv, selection_bootstrap.csv.
No seed variation is studied; the bootstrap is over GROUPS (and over overlap blocks) on fixed predictions.
"""
import json
import os

import numpy as np
import pandas as pd

RUN = r"D:\treeroute\runs\coral\headline\20261020_f3b8e3da"
OUT = os.path.dirname(os.path.abspath(__file__))
B = 20000
RNG = np.random.default_rng(20261021)  # resampling only; fixed so the numbers are reproducible
BAND = 0.9175581931137083        # verdict.json "band"
C9_TOL = 9e-07                   # verdict.json tolerances.tolerance.arcsine (C9 floor 10 x 9e-8)
PT = "level=100.0,ratio=1.0"

inner = pd.read_parquet(os.path.join(RUN, "inner_preds.parquet"))
test = pd.read_parquet(os.path.join(RUN, "test_preds.parquet"))
derived = json.load(open(os.path.join(RUN, "derived.json"), encoding="utf-8"))
block_of_group = derived["R14:overlap_blocks"]["value"]["block_of_group"]

y = inner["y"].to_numpy(float)
groups = inner["group"].to_numpy()
G = np.array(sorted(set(groups)))
gidx = np.searchsorted(G, groups)
nG = len(G)
n_g = np.bincount(gidx, minlength=nG).astype(float)
years = pd.to_datetime([pd.Timestamp.fromordinal(int(t)) for t in inner["time"]]).year.to_numpy()

ARMS = [a for a in ["identity_plain_unweighted", "identity_plain_gls", "identity_corrector_unweighted",
                    "identity_corrector_gls", "log_c_plain_unweighted", "log_c_plain_gls",
                    "log_c_corrector_unweighted", "log_c_corrector_gls", "arcsine_plain_unweighted",
                    "arcsine_plain_gls", "arcsine_corrector_unweighted", "arcsine_corrector_gls"]]
cols = {a: [c for c in inner.columns if c.startswith(a + "@")] for a in ARMS}
for a in ARMS:
    assert len(cols[a]) == 35, (a, len(cols[a]))


def abserr(col):
    return np.abs(y - inner[col].to_numpy(float))


# ---------------------------------------------------------------- reproduce the run's picks
picks = {}
for a in ARMS:
    m = [abserr(c).mean() for c in cols[a]]
    k = int(np.argmin(m))
    picks[a] = (cols[a][k], float(m[k]))
donor_mae = float(abserr("base__donor_median").mean())


def jackknife(v):
    v = np.asarray(v, float)
    n = v.size
    jk = np.array([np.delete(v, i).mean() for i in range(n)])
    se = float(np.sqrt((n - 1) / n * ((jk - jk.mean()) ** 2).sum()))
    return float(v.mean()), se


def contrast(col_a, col_b, label):
    """gap = MAE(b) - MAE(a): positive = a better. a is the arm the layer preferred."""
    ea, eb = abserr(col_a), abserr(col_b)
    d = eb - ea                               # per-row paired difference
    pooled = float(d.mean())                  # the selection metric (decide.py:278)
    sum_g = np.bincount(gidx, weights=d, minlength=nG)
    per_group = sum_g / n_g                   # per-group MAE contrast (the band's metric)
    # (1) engine-style group jackknife of the per-group contrast (metrics.py:1032-1053)
    gm, gse = jackknife(per_group)
    # (2) delete-one-group jackknife of the POOLED (row-weighted) gap
    loo = np.array([(d.sum() - sum_g[i]) / (d.size - n_g[i]) for i in range(nG)])
    pse = float(np.sqrt((nG - 1) / nG * ((loo - loo.mean()) ** 2).sum()))
    # (3) group bootstrap of the pooled gap
    W = RNG.multinomial(nG, np.full(nG, 1.0 / nG), size=B).astype(float)
    boot = (W @ sum_g) / (W @ n_g)
    # (4) overlap-block bootstrap (blocks of R14)
    blk = np.array([block_of_group[g] for g in G])
    ub, bidx = np.unique(blk, return_inverse=True)
    sum_b = np.bincount(bidx, weights=sum_g, minlength=len(ub))
    n_b = np.bincount(bidx, weights=n_g, minlength=len(ub))
    Wb = RNG.multinomial(len(ub), np.full(len(ub), 1.0 / len(ub)), size=B).astype(float)
    bootb = (Wb @ sum_b) / (Wb @ n_b)
    # rows: zero vs bleached; severity bins
    z = y == 0
    sev = y >= 50
    out = {
        "label": label, "a": col_a, "b": col_b,
        "mae_a": float(ea.mean()), "mae_b": float(eb.mean()), "pooled_gap": pooled,
        "row_naive_se": float(d.std(ddof=1) / np.sqrt(d.size)),
        "rows_a_better": int((d > 0).sum()), "rows_b_better": int((d < 0).sum()), "rows_tied": int((d == 0).sum()),
        "pooled_jk_se": pse, "pooled_jk_low": pooled - 1.96 * pse, "pooled_jk_high": pooled + 1.96 * pse,
        "boot_p_a_wins": float((boot > 0).mean()),
        "boot_ci": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
        "block_boot_p_a_wins": float((bootb > 0).mean()), "n_blocks": int(len(ub)),
        "block_boot_ci": [float(np.percentile(bootb, 2.5)), float(np.percentile(bootb, 97.5))],
        "per_group_mean_gap": gm, "per_group_jk_se": gse,
        "per_group_jk_low": gm - 1.96 * gse, "per_group_jk_high": gm + 1.96 * gse,
        "groups_a_better": int((per_group > 0).sum()), "groups_b_better": int((per_group < 0).sum()),
        "gap_over_band": pooled / BAND, "gap_over_C9_tol": pooled / C9_TOL,
        # share of the pooled gap (sum of d / N) from zero rows vs bleached rows
        "gap_from_zero_rows": float(d[z].sum() / d.size), "gap_from_bleached_rows": float(d[~z].sum() / d.size),
        "gap_from_severe_rows": float(d[sev].sum() / d.size),
        "n_zero": int(z.sum()), "n_bleached": int((~z).sum()), "n_severe": int(sev.sum()),
        "mae_a_zero": float(ea[z].mean()), "mae_b_zero": float(eb[z].mean()),
        "mae_a_bleached": float(ea[~z].mean()), "mae_b_bleached": float(eb[~z].mean()),
        "mae_a_severe": float(ea[sev].mean()), "mae_b_severe": float(eb[sev].mean()),
        "by_year": {int(yr): float(d[years == yr].sum() / d.size) for yr in sorted(set(years))},
        "by_year_mean": {int(yr): float(d[years == yr].mean()) for yr in sorted(set(years))},
    }
    # concentration over groups
    contrib = sum_g / d.size                       # each group's additive share of the pooled gap
    order = np.argsort(-contrib)
    out["top_groups"] = [{"group": G[i], "rows": int(n_g[i]), "contrib": float(contrib[i]),
                          "group_gap": float(per_group[i])} for i in order[:5]]
    out["bottom_groups"] = [{"group": G[i], "rows": int(n_g[i]), "contrib": float(contrib[i]),
                             "group_gap": float(per_group[i])} for i in order[::-1][:3]]
    # remove the top-k positive groups: when does the sign flip?
    flip_k = None
    for k in range(1, nG):
        keep = np.ones(nG, bool)
        keep[order[:k]] = False
        if sum_g[keep].sum() / n_g[keep].sum() <= 0:
            flip_k = k
            break
    out["groups_to_remove_to_flip"] = flip_k
    out["loo_min"] = float(loo.min()); out["loo_max"] = float(loo.max())
    out["loo_min_group"] = G[int(np.argmin(loo))]
    # concentration over rows
    ds = np.sort(d)[::-1]
    cum = np.cumsum(ds)
    out["rows_to_carry_gap"] = int(np.searchsorted(cum, d.sum()) + 1)   # top rows whose sum >= the whole gap
    out["top20_rows_sum_over_N"] = float(ds[:20].sum() / d.size)
    return out, per_group


CONTRASTS = [
    ("GLS vs unweighted (arcsine corrector) [THE PICK]", "arcsine_corrector_gls@" + PT, "arcsine_corrector_unweighted@" + PT),
    ("GLS vs unweighted (arcsine plain)", "arcsine_plain_gls@" + PT, "arcsine_plain_unweighted@" + PT),
    ("corrector vs plain (arcsine GLS)", "arcsine_corrector_gls@" + PT, "arcsine_plain_gls@" + PT),
    ("corrector vs plain (arcsine unweighted)", "arcsine_corrector_unweighted@" + PT, "arcsine_plain_unweighted@" + PT),
    ("arcsine vs log_c (adopted vs best log arm at its own pick)", "arcsine_corrector_gls@" + PT, picks["log_c_corrector_unweighted"][0]),
    ("arcsine vs log_c (unweighted corrector, each at own pick)", "arcsine_corrector_unweighted@" + PT, picks["log_c_corrector_unweighted"][0]),
    ("log_c corrector unweighted (own pick) vs arcsine corrector unweighted", picks["log_c_corrector_unweighted"][0], "arcsine_corrector_unweighted@" + PT),
]
results, pg = [], {}
for label, a, b in CONTRASTS:
    r, per_group = contrast(a, b, label)
    results.append(r)
    pg[label] = per_group

# GLS - unweighted at EVERY grid point (is the GLS edge stable across the penalty grid?)
grid_rows = []
for cg, cu in zip(cols["arcsine_corrector_gls"], cols["arcsine_corrector_unweighted"]):
    assert cg.split("@")[1] == cu.split("@")[1]
    grid_rows.append({"point": cg.split("@")[1], "mae_gls": abserr(cg).mean(), "mae_unw": abserr(cu).mean(),
                      "gap": abserr(cu).mean() - abserr(cg).mean()})
grid_df = pd.DataFrame(grid_rows)

# ---------------------------------------------------------------- full-selection bootstrap
# Re-run the whole rule (decide.py:270-285 best grid point per arm; :460-477 min over eligible arms,
# eligibility = MAE < donor median MAE under owner ruling V1) on group-resampled surfaces.
allcols = [c for a in ARMS for c in cols[a]]
E = np.abs(y[:, None] - inner[allcols].to_numpy(float))
S = np.zeros((nG, E.shape[1]))
np.add.at(S, gidx, E)
Sd = np.bincount(gidx, weights=abserr("base__donor_median"), minlength=nG)
W = RNG.multinomial(nG, np.full(nG, 1.0 / nG), size=B).astype(float)
den = W @ n_g
M = (W @ S) / den[:, None]                     # B x (12*35)
Md = (W @ Sd) / den
M3 = M.reshape(B, len(ARMS), 35)
best_pt = M3.argmin(axis=2)
best = M3.min(axis=2)
elig = best < Md[:, None]
best_masked = np.where(elig, best, np.inf)
win = best_masked.argmin(axis=1)
sel = pd.Series([ARMS[i] for i in win]).value_counts() / B
pt_names = [c.split("@")[1] for c in cols[ARMS[0]]]
ad_pts = pd.Series([pt_names[best_pt[b, win[b]]] for b in range(B)]).value_counts() / B
sel_df = pd.DataFrame({"arm": sel.index, "share_adopted": sel.values})
# probability the adopted arm's penalty is the top edge (100, 1.0)
p_edge = float(ad_pts.get(PT, 0.0))

# ---------------------------------------------------------------- test-set beside (NOT a decision input)
ty = test["y"].to_numpy(float)
tg = test["group"].to_numpy()
TG = np.array(sorted(set(tg))); tgi = np.searchsorted(TG, tg); tn = np.bincount(tgi).astype(float)
td = np.abs(ty - test["arm__arcsine_corrector_unweighted"]) - np.abs(ty - test["arm__arcsine_corrector_gls"])
td = td.to_numpy(float)
tsum = np.bincount(tgi, weights=td, minlength=len(TG))
tpg = tsum / tn
tm, tse = jackknife(tpg)
tloo = np.array([(td.sum() - tsum[i]) / (td.size - tn[i]) for i in range(len(TG))])
tpse = float(np.sqrt((len(TG) - 1) / len(TG) * ((tloo - tloo.mean()) ** 2).sum()))
tcontrib = tsum / td.size
tord = np.argsort(tcontrib)
test_beside = {
    "pooled_mae_gls_minus_unw": float(-td.mean()),  # positive = unweighted better on test
    "mae_gls": float(np.abs(ty - test["arm__arcsine_corrector_gls"]).mean()),
    "mae_unw": float(np.abs(ty - test["arm__arcsine_corrector_unweighted"]).mean()),
    "pooled_jk_se": tpse, "per_group_mean_unw_minus_gls": tm, "per_group_jk_se": tse,
    "n_groups": int(len(TG)),
    "most_negative_groups": [{"group": TG[i], "rows": int(tn[i]), "contrib": float(tcontrib[i])} for i in tord[:5]],
    "by_programme": {p: float(td[test["programme"].to_numpy() == p].sum() / td.size) for p in sorted(test["programme"].unique())},
}

res = {"surface_rows": int(y.size), "surface_groups": int(nG), "band": BAND, "c9_tolerance_arcsine": C9_TOL,
       "donor_median_mae": donor_mae, "picks": picks, "contrasts": results,
       "grid_gap_gls_minus_unw": grid_rows,
       "selection_bootstrap": {"B": B, "share_adopted": sel.to_dict(), "adopted_point_share": ad_pts.head(8).to_dict(),
                               "p_edge_point": p_edge, "p_any_ineligible": float((~elig).any(axis=1).mean())},
       "test_beside": test_beside}
json.dump(res, open(os.path.join(OUT, "results.json"), "w"), indent=1, default=float)
pd.DataFrame([{k: v for k, v in r.items() if not isinstance(v, (list, dict))} for r in results]).to_csv(
    os.path.join(OUT, "contrasts.csv"), index=False)
pd.DataFrame({"group": G, "rows": n_g.astype(int), **{k: v for k, v in pg.items()}}).to_csv(
    os.path.join(OUT, "per_group_gap.csv"), index=False)
sel_df.to_csv(os.path.join(OUT, "selection_bootstrap.csv"), index=False)
grid_df.to_csv(os.path.join(OUT, "grid_gap.csv"), index=False)
print(json.dumps(res, indent=1, default=float))

