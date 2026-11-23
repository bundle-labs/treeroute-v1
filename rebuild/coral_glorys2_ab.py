"""A/B the GLORYS pass-2 blocks: salinity, currents, bottom-water refuge.

    py -3.9 -u coral_glorys2_ab.py --seeds 7

FIVE ARMS, so a win can be attributed to a MECHANISM rather than to "more columns":
    BASE 74   the shipped working set (CORE 64 + Hobday 10)
    +SAL 5    haline stratification and freshwater/hypersaline anomalies
    +CUR 5    flushing: speed anomaly, self-normalised stagnation, steadiness, vertical shear
    +BOT 5    bottom-water refuge: anomaly, cold pulse, variability ratio, reef-to-floor gap
    +ALL 15   all three, which also measures the DILUTION cost Part 435 diagnosed

ARCSINE LINK ONLY. Part 425 established that solving the local ridge on a raw 68.5%-zero target is
a mis-specification worth -0.5 to -0.7 MAE. Part 438 carried the identity link purely for continuity
with Parts 417-423, then closed with the recommendation to drop it -- it doubled the runtime for a
verdict the arcsine arm had already given. Dropped here.

BOTH SPLITS, because the year-blocked control is the only thing that has caught the eight CLOCKS
in this project -- columns that improve a conventional temporal holdout while DEGRADING held-out
regions. Ocean heat content, sea state, the p90 accumulators, LEGAL 149, ALL 188, OC-CCI, HAMTIDE
and the five-block union all passed a year split and failed the split that matters.

EVENT-CLUSTERED BOOTSTRAP, not a row bootstrap. The 730 test rows sit on only 641 distinct
(lat, lon, date) survey events; rows inside an event share a reef, a day and a survey team, so
resampling rows treats correlated observations as independent and reports a CI that is too narrow.

HONEST PRIOR, STATED BEFORE THE RUN. Thirteen driver families have been tested and exactly one
marginal win survived. The measured decorrelation of this block (|r| <= 0.34 with dhw_56, <= 0.43
with any pass-1 GLORYS column) is NOT evidence it will help: every failed block was also
decorrelated, and Part 438 concluded redundancy was never the problem. The diagnosed failure is
structural -- the router picks calibration neighbours by Euclidean distance in standardised feature
space, so each added column dilutes the metric that selects its own training rows. The +ALL arm is
the direct test of that: if the three blocks each do nothing and +ALL is clearly worse, dilution is
confirmed rather than merely asserted.
"""
import argparse
import re
import sys
import time
import warnings

sys.path.insert(0, r"C:\Users\<user>\Desktop\data set for reserch paper")
from coral_safe import cap_threads, guard, mem_str

cap_threads(4)
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import roc_auc_score

from coral_smoke_regress import continuous_target
from coral_architecture import build_bank, tree_columns, solve_local, haversine

FEAT = "glorys2_features.parquet"
CFG = dict(npd=24, mf=0.15, k=50, alpha=0.5, a_ctx=0.25)
G = lambda y: np.arcsin(np.sqrt(np.clip(y, 0, 100) / 100.0))
GINV = lambda p: 100.0 * np.sin(np.clip(p, 0, np.pi / 2)) ** 2

SAL = ["sa_anom_30", "sa_anom_90", "sa_min_anom_30", "sa_strat_30", "sa_strat_anom_90"]
CUR = ["cu_spd_anom_30", "cu_spd_ratio_30", "cu_stag_30", "cu_persist_30", "cu_shear_30"]
BOT = ["bo_anom_30", "bo_anom_90", "bo_cold_30", "bo_var_ratio_90", "bo_minus_reef_30"]


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


def route(trn, tst, fcols, ctxc, npd, mf, k, alpha, a_ctx, seed):
    trees, _ = build_bank(trn, fcols, npd, mf, seed)
    A = np.vstack([tree_columns(trees, trn, fcols), tree_columns(trees, tst, fcols)])
    n_tr = len(trn)
    yp = np.r_[trn.y.values, tst.y.values]
    t = G(yp)
    C = np.vstack([trn[ctxc].values, tst[ctxc].values]).astype(np.float64)
    C = (C - C[:n_tr].mean(0)) / (C[:n_tr].std(0) + 1e-9)
    M = np.r_[trn.mmm.values, tst.mmm.values]
    Z = np.vstack([trn[fcols].fillna(0).values, tst[fcols].fillna(0).values]).astype(np.float64)
    Z = (Z - Z[:n_tr].mean(0)) / (Z[:n_tr].std(0) + 1e-9)
    lat = np.r_[trn.lat.values, tst.lat.values]
    lon = np.r_[trn.lon.values, tst.lon.values]
    eco = np.r_[trn.eco.values, tst.eco.values]
    dat = np.r_[trn.date.values, tst.date.values]
    sg = RandomForestRegressor(300, max_depth=8, min_samples_leaf=5, n_jobs=4,
                               random_state=seed).fit(
        trn[fcols].fillna(0), np.abs(trn.y.values - trn.y.values.mean()))
    s = np.clip(sg.predict(np.vstack([trn[fcols].fillna(0), tst[fcols].fillna(0)])), 1e-6, None)
    lo, hi = np.percentile(s, [5, 95])
    w = 1.0 / np.clip(s, lo, hi) ** 2
    out = np.empty(len(tst))
    for i in range(len(tst)):
        gi = n_tr + i
        ok = np.where((~(eco == eco[gi]) | (dat < dat[gi])) & (np.arange(len(yp)) != gi))[0]
        if len(ok) < 12:
            out[i] = t[:n_tr].mean()
            continue
        d = haversine(lat[gi], lon[gi], lat[ok], lon[ok])
        gg = ok[np.argsort(d)][:min(len(ok), 3 * k)]
        sel = gg[np.argsort(np.sqrt(((Z[gg] - Z[gi]) ** 2).sum(1)))][:k]
        Xc = np.column_stack([np.ones(len(sel)), M[sel] - M[sel].mean(), C[sel], A[sel]])
        b = solve_local(Xc, t[sel], w[sel], A.shape[1], len(ctxc), alpha, a_ctx)
        out[i] = float(np.r_[1.0, M[gi] - M[sel].mean(), C[gi], A[gi]] @ b)
    return GINV(out)


def sc(y, p):
    e = np.abs(y - p)
    sev = y >= 50
    return dict(MAE=e.mean(), R2=1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum(),
                hit5=(e <= 5).mean(), AUC=roc_auc_score((y > 0).astype(int), p),
                AUC50=roc_auc_score(sev.astype(int), p) if 0 < sev.mean() < 1 else np.nan,
                psev=float(p[sev].mean()) if sev.any() else np.nan)


def event_boot(te, nboot=2000, seed=0):
    """Resample the (lat, lon, date) survey EVENTS, not the rows. Rows inside one event share a
    reef, a day and a survey team, so a row bootstrap understates the CI."""
    key = pd.factorize(te.lat.astype(str) + "|" + te.lon.astype(str) + "|" +
                       te.date.astype(str))[0]
    groups = [np.where(key == c)[0] for c in range(key.max() + 1)]
    rs = np.random.RandomState(seed)
    return [np.concatenate([groups[c] for c in rs.randint(0, len(groups), len(groups))])
            for _ in range(nboot)], len(groups)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=7)
    A = ap.parse_args()
    X = pd.read_parquet(FEAT)
    X["y"] = X.sid.map(continuous_target())
    X = X.dropna(subset=["y"]).reset_index(drop=True)
    allf = [c for c in X.columns if c not in ("sid", "eco", "side", "pos", "date", "y",
                                              "lat", "lon", "_side")]
    ABS = [c for c in allf if re.match(r"^(mean|std)_\d+$", c) or c in ("abslat", "mmm", "mmm_n_years")]
    FUK = [c for c in allf if c.startswith(("days2", "days3", "CATS_", "max_sst", "dhwG"))]
    P90 = [c for c in allf if c.startswith("mhw_p90")]
    HOB = [c for c in allf if c.startswith("mhw_") and not c.startswith("mhw_p90")]
    OLD = [c for c in allf if c.startswith(("par_", "kd_", "ohc", "ss_", "ssh_")) or "_x_dhw" in c]
    GLO = [c for c in allf if c.startswith(("mld_", "strat_", "zos_", "treef_", "dhw_depth",
                                            "hs_depth", "mmm_depth", "depth_offset",
                                            "dhw_surf_minus", "glorys_"))]
    NEW5 = [c for c in allf if c.startswith(("oc_", "wv_", "ht_", "gs_", "rm_"))]
    G2 = SAL + CUR + BOT
    CORE = [c for c in allf if c not in ABS + FUK + P90 + HOB + OLD + GLO + NEW5 + G2
            and c not in ("glorys_n90", "glorys2_n90")]
    dm = X[X.side == "donor"]
    for c in HOB + G2:
        if X[c].isna().any():
            X[c] = X[c].fillna(dm[c].median())
    ctxc = ["month", "doy_sin", "doy_cos", "abslat"]
    BASE = CORE + HOB
    ARMS = [("BASE 74", BASE), ("+SAL 5", BASE + SAL), ("+CUR 5", BASE + CUR),
            ("+BOT 5", BASE + BOT), ("+ALL 15", BASE + G2)]
    log("=" * 104)
    log("BASE %d (CORE %d + Hobday %d) | SAL %d | CUR %d | BOT %d | %s"
        % (len(BASE), len(CORE), len(HOB), len(SAL), len(CUR), len(BOT), mem_str()))
    log("  arcsine link only; identity dropped on Part 438's own recommendation.")
    log("  PRIOR: 13 driver families tested, 1 marginal win. This is expected to be null.")

    gains = {}
    for split in ("region", "year"):
        if split == "region":
            X["_side"] = X["side"]
        else:
            frac = (X.side == "test").mean()
            yr = X.date.dt.year.values
            X["_side"] = np.where(yr >= np.quantile(yr, 1 - frac), "test", "donor")
        tr = X[X._side == "donor"].reset_index(drop=True)
        te = X[X._side == "test"].reset_index(drop=True)
        y = te.y.values
        B, nclu = event_boot(te)
        log("=" * 104)
        log("%s-BLOCKED | donor %d / %d eco | test %d / %d eco | %d survey events"
            % (split.upper(), len(tr), tr.eco.nunique(), len(te), te.eco.nunique(), nclu))
        res, preds = {}, {}
        for name, fc in ARMS:
            fc = [c for c in fc if c in X.columns]
            t0 = time.time()
            ps = [route(tr, te, fc, ctxc, CFG["npd"], CFG["mf"], CFG["k"], CFG["alpha"],
                        CFG["a_ctx"], s) for s in range(A.seeds)]
            guard(2.5, name)
            P = np.mean(ps, axis=0)
            res[name], preds[name] = sc(y, P), P
            log("    %-9s %3d cols  %5.1fs" % (name, len(fc), time.time() - t0))
        b = res[ARMS[0][0]]["MAE"]
        log("  %-10s %7s %9s %7s %8s %8s %8s | %8s"
            % ("arm", "MAE", "R2", "hit5", "AUC", "AUC50", "psev", "dMAE"))
        for name, _ in ARMS:
            m = res[name]
            log("  %-10s %7.3f %+9.4f %7.3f %8.4f %8.4f %8.2f | %+8.3f"
                % (name, m["MAE"], m["R2"], m["hit5"], m["AUC"], m["AUC50"], m["psev"],
                   m["MAE"] - b))
        p0 = preds[ARMS[0][0]]
        log("  event-clustered bootstrap, %d clusters, 2000 resamples:" % nclu)
        for name, _ in ARMS[1:]:
            d = np.array([np.abs(y[i] - preds[name][i]).mean() - np.abs(y[i] - p0[i]).mean()
                          for i in B])
            lo, hi = np.percentile(d, [2.5, 97.5])
            log("    %-10s dMAE %+.3f  CI [%+.3f, %+.3f]  %s"
                % (name, d.mean(), lo, hi,
                   ("SIGNIFICANT BETTER" if hi < 0 else "SIGNIFICANT WORSE") if (hi < 0 or lo > 0)
                   else "ns"))
        gains[split] = {n: res[n]["MAE"] - b for n, _ in ARMS}

    log("=" * 104)
    log("REGION vs YEAR -- a real driver helps the REGION split at least as much as the year split")
    for name, _ in ARMS[1:]:
        gr, gy = gains["region"][name], gains["year"][name]
        v = ("no gain either way" if gr > -0.05 and gy > -0.05 else
             "CLOCK -- helps the year split more" if gy < gr - 0.05 else
             "carries regional information")
        log("  %-10s region %+.3f   year %+.3f   %s" % (name, gr, gy, v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
