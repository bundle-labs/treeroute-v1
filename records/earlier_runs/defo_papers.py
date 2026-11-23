"""Problem #4 -- PUBLISHED BASELINES vs THE SOFT GATE. Every arm is a named method from the
literature, rebuilt on our panel. The only in-house arm is `softgate`, the reference.

    py -3.9 -u defo_papers.py --tests=6                    # cheap arms only, ~2 min a region
    py -3.9 -u defo_papers.py --tests=6 --fitted=1         # + the fitted rivals, ~8 min a region
    py -3.9 -u defo_papers.py --tests=17 --fitted=1 --donors=8

THE RULE OF THIS FILE: no baseline I invented. `zero` and cell-climatology do not appear -- they are
my own conventions and they live in defo_bench.py. Everything here is a method somebody published,
cited in its own docstring block, together with an explicit statement of what had to be ADAPTED to
run on a 4 km annual panel. A rebuild that changes the covariates is a DIFFERENT MODEL and is
labelled so; it is not scored as though it were theirs.

PUBLISHED ACCURACIES ARE NEVER QUOTED. Those papers used other data, grids, periods and splits, most
on a spatially random split, which is far easier than our region-blocked forward-in-time one. The
only fair comparison is a rebuild on these rows, and that is what this script does.

THE ARMS

  vm0015        Verra VM0015 v1.2 "Methodology for Avoided Unplanned Deforestation"; FCPF Carbon
                Fund Methodological Framework (2013); VCS JNR. The historical-average-rate baseline:
                the region's mean annual loss fraction over the calibration period, applied
                uniformly to every cell and every year of the crediting period. THE CONVENTION THAT
                CARBON FINANCE IS PRICED AGAINST, and the reference a referee asks for first.
  vm0015_trend  the same with the quantity extrapolated by an OLS trend on the calibration-period
                annual totals, the variant allowed where a jurisdiction's frontier is accelerating.
  varnier_rand  Varnier & Weber (2025), Land 14(3):560. Quantity-matched RANDOM allocation: spread
                the calibration-period regional quantity over cells with no covariate information.
                ADAPTED: the draw is a deterministic evenly-spaced stride over sorted cell ids, not
                a pseudo-random draw, because this project forbids seeds.
  pontius_null  Pontius Jr.'s null model of no change, the standard reference in the land-change
                validation literature (Pontius, Cornell & Hall 2001 and the figure-of-merit line of
                work that follows it).
  ff_persist    Forest Foresight's own trivial baseline (Overlan/Kruijssen line of work; the
                published comparison has persistence at F0.5 60.6% against their XGBoost's 63.4%).
                The cell's own last calibration-year loss, held constant across the whole crediting
                period. LEGAL FORM: frozen at 2019, never rolling.
  forestcast_ch ForestCast's change-history-only ablation (Overlan et al. 2025, doi:10.31223/X5Q757),
                whose reported result is that change history ALONE matched or beat configurations
                adding imagery, roads, protected areas, population and elevation. Built here as a
                ridge on the h_* block FROZEN AT 2019. Carry their own caveat: change history partly
                lets a model learn the state of the DETECTION algorithm rather than a driver.
  cushman_null  Cushman's naive null, risk proportional to 1/d^10 with d an accessibility distance.
                ADAPTED, AND THE ADAPTATION IS LARGE: the canonical d is DISTANCE TO FOREST EDGE,
                which we cannot build -- it is a function of forest2000_px, the target's own
                denominator, and therefore banned under our rule (d). Substituted: travel_time.
  geomod        GEOMOD2, Pontius Jr., Cornell & Hall (2001), Agriculture, Ecosystems & Environment
                85(1-3):191-203. Quantity x allocation: rank cells by a suitability score built from
                STATIC drivers only, then assign the calibration-period quantity to the highest-
                ranked cells. ADAPTED: suitability is fitted on <=2019 from the static/accessibility
                columns rather than from a land-cover-derived edge distance.
  udef_a        Verra VT0007 Unplanned Deforestation Allocation (UDef-A) v1.0, Feb 2024 (Eastman &
                Pontius Jr., Clark Labs; Dickson, TerraCarbon); reference implementation UDef-ARP.
                Fits deforestation DENSITY as a function of a distance covariate on the calibration
                period, then allocates the legal (calibration-period) quantity by that relationship.
                ADAPTED the same way as geomod: distance-to-forest-edge is unavailable, so the
                density relationship is fitted against travel_time and road_density.
  sales_hurdle  Ribeiro Sales, de Bruin, Herold, Kyriakidis & Souza (2017), Spatial Statistics
                21(A):304-318, doi:10.1016/j.spasta.2017.06.003. The two-part model: occurrence
                x intensity. ADAPTED: both limbs are plain GLMs on our covariates (L2 logistic for
                occurrence, gamma-log for intensity fitted on positives only); their geostatistical
                space-time limb is infeasible at our row count and would read in-window neighbour
                loss. This is the PUBLISHED PRECEDENT for our own soft gate, built bank-free, so the
                comparison answers whether the tree bank and router add anything over the structure.
  vieilledent   forestatrisk / deforisk (Vieilledent 2021, JOSS 6(59):2975, doi:10.21105/joss.02975;
                Vieilledent & Arsouze 2024 FAO/CIRAD benchmark). ADAPTED: their iCAR spatial random
                effect is replaced by a RandomForest on the same covariates, which is the RF arm
                their own benchmark ladder reports.
  cuelarosa     Cue La Rosa, van Duijvenbode, Calle, Marcos, Dallinga & Reiche (2025), Environmental
                Research Communications 7:125002, doi:10.1088/2515-7620/ae1f69. The XGBoost tabular
                baseline, trained on donor rows plus the test region's own calibration rows -- the
                same information budget K_AD_climcol consumes.
  softgate      OURS, the only in-house arm. P(fire) * E[y|fire] + (1-P) * m_neg over the donor tree
                banks, isotonic calibration fitted on <=2019.

FAIRNESS, enforced by construction: one row set, one split (train <=2019, test 2020-2023, region
blocked), one information budget (donor <=2019 rows plus the test region's own <=2019 rows), one ban
list, one metric bundle. Nothing touches a 2020-2023 row for fitting, selection, thresholding or
calibration. PRED MAX is reported for every arm because our own defect is a prediction ceiling of
~0.04 against a target range of 0-1, and a rival that fixes that while scoring slightly worse is the
more useful model.

NO SEEDS: random_state=0 is a fixed constant, never varied. Uncertainty is jackknife OVER REGIONS.
CRASH-SAFE: one CSV per region, skipped on a re-run.
"""
import os
import sys
import time
import gc
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
import defo_train as T
import defo_binary as B
import defo_softgate as S

OUT = "D:/defo_papers"
os.makedirs(OUT, exist_ok=True)

THR      = T._a("--thr", 0.01, float)
ARM      = T._a("--arm", "hist")
NDON     = T._a("--donors", 8, int)
NTEST    = T._a("--tests", 6, int)
FROM     = T._a("--from", 0, int)
RNT      = T._a("--regtrees", 150, int)
RMF      = T._a("--regmf", 15, int)
LAM      = T._a("--lam", 100.0, float)
MAXCELLS = T._a("--maxcells", 4000, int)
REGROWS  = T._a("--regrows", 60000, int)
FITTED   = T._a("--fitted", 0, int)
POOLROWS = T._a("--poolrows", 250000, int)
NEST     = T._a("--nest", 400, int)
JOBS     = T._a("--jobs", 6, int)
SEED     = 0

STATIC = ["travel_time", "road_density", "dist_to_coast_km", "population_density",
          "gdp_pc", "hdi", "elevation_m", "slope_deg"]
HCOLS  = ["h_lag1", "h_lag2", "h_lag3", "h_cum", "h_nbr1", "h_nbr2", "h_nbr_cum", "h_yrs_since"]


def log(m):
    print(m, flush=True)
    with open(os.path.join(OUT, "_papers.log"), "a", encoding="utf-8") as f:
        f.write(m + "\n")


def col(meta, X, cols, name):
    """Fetch one named feature column from the loaded matrix, or None."""
    if name not in cols:
        return None
    return X[:, cols.index(name)].astype(np.float64)


def quantity(meta, y, tr, kind):
    """The calibration-period regional quantity, per test year. Legal: <=2019 only."""
    trn = meta[tr]
    if kind == "flat":
        r = float(y[tr].mean())
        return np.full(len(y), r)
    ann = trn.groupby("year").y.mean()
    if len(ann) < 3:
        return np.full(len(y), float(y[tr].mean()))
    b1, b0 = np.polyfit(ann.index.to_numpy(np.float64), ann.to_numpy(), 1)
    yr = meta.year.to_numpy()
    return np.array([max(b0 + b1 * float(v), 0.0) for v in yr])


def allocate(meta, score, q, tr, y):
    """Quantity x allocation: distribute the regional quantity q across cells in proportion to a
    non-negative suitability score, normalised so the regional mean equals q."""
    s = np.clip(np.nan_to_num(score, nan=0.0), 0.0, None)
    if s.sum() <= 0:
        return q.copy()
    w = s / s.mean()
    return q * w


def paper_arms(meta, X, cols, y, tr, te):
    out, notes = {}, {}
    trn = meta[tr]
    ly = int(trn.year.max())

    # --- VM0015 / FCPF historical rate, and its trend variant -----------------------------------
    out["vm0015"] = quantity(meta, y, tr, "flat")
    out["vm0015_trend"] = quantity(meta, y, tr, "trend")

    # --- Pontius null of no change ---------------------------------------------------------------
    out["pontius_null"] = np.zeros(len(y))

    # --- Forest Foresight persistence, FROZEN at the last calibration year -----------------------
    last = trn[trn.year == ly].set_index("cell_id").y
    out["ff_persist"] = meta.cell_id.map(last).fillna(0.0).to_numpy(np.float64)

    # --- Varnier & Weber quantity-matched allocation with no covariate information ---------------
    pos_rate = float((y[tr] > THR).mean())
    m_pos = float(y[tr][y[tr] > THR].mean()) if (y[tr] > THR).any() else float(y[tr].mean())
    ids = np.sort(meta.cell_id.unique())
    k = max(1, int(round(pos_rate * len(ids))))
    chosen = set(ids[np.linspace(0, len(ids) - 1, k).astype(np.int64)])
    out["varnier_rand"] = np.where(meta.cell_id.isin(chosen).to_numpy(), m_pos, 0.0)

    # --- Cushman naive null: risk proportional to 1/d^10, d = travel_time (SUBSTITUTED) ----------
    d = col(meta, X, cols, "travel_time")
    if d is not None:
        dd = np.clip(d, np.nanpercentile(d, 1), None)
        dd = dd / max(np.nanmedian(dd), 1e-9)
        sc = 1.0 / np.clip(dd, 1e-3, None) ** 10
        out["cushman_null"] = allocate(meta, sc, quantity(meta, y, tr, "flat"), tr, y)
        notes["cushman_null"] = "d = travel_time; canonical distance-to-forest-edge is banned under rule (d)"

    # --- GEOMOD: static suitability, then quantity allocation ------------------------------------
    av = [c for c in STATIC if c in cols]
    if av:
        Xs = np.column_stack([col(meta, X, cols, c) for c in av])
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        zb = (y > THR)
        try:
            g = make_pipeline(StandardScaler(),
                              LogisticRegression(C=0.1, max_iter=1000, class_weight="balanced",
                                                 n_jobs=JOBS, random_state=SEED))
            g.fit(Xs[tr], zb[tr].astype(np.int32))
            suit = g.predict_proba(Xs)[:, 1]
            out["geomod"] = allocate(meta, suit, quantity(meta, y, tr, "flat"), tr, y)
            notes["geomod"] = "suitability from %d static/accessibility columns" % len(av)
        except Exception as e:
            log("      geomod failed: %s" % type(e).__name__)
        # --- UDef-A: density as a function of the distance covariate, then legal quantity --------
        try:
            dv = col(meta, X, cols, "travel_time")
            rd = col(meta, X, cols, "road_density")
            if dv is not None:
                base = dv if rd is None else (dv / (1.0 + np.clip(rd, 0, None)))
                qs = np.nanpercentile(base[tr], np.linspace(0, 100, 21))
                bins = np.clip(np.digitize(base, qs[1:-1]), 0, 19)
                dens = pd.Series(y[tr]).groupby(bins[tr]).mean()
                sc = pd.Series(bins).map(dens).fillna(float(y[tr].mean())).to_numpy(np.float64)
                out["udef_a"] = allocate(meta, sc, quantity(meta, y, tr, "flat"), tr, y)
                notes["udef_a"] = "density fitted against travel_time/road_density, 20 strata"
        except Exception as e:
            log("      udef_a failed: %s" % type(e).__name__)

    # --- ForestCast change-history-only, FROZEN at the last calibration year ---------------------
    hv = [c for c in HCOLS if c in cols]
    if hv:
        Xh = np.column_stack([col(meta, X, cols, c) for c in hv])
        frz = pd.DataFrame(Xh, columns=hv)
        frz["cell_id"] = meta.cell_id.to_numpy()
        frz["year"] = meta.year.to_numpy()
        snap = frz[frz.year == ly].set_index("cell_id")[hv]
        Xf = meta.cell_id.map(lambda c: None)  # placeholder, replaced below
        Xf = snap.reindex(meta.cell_id.to_numpy()).to_numpy(np.float64)
        Xf = np.nan_to_num(Xf)
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        try:
            m = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
            m.fit(Xf[tr], y[tr])
            out["forestcast_ch"] = m.predict(Xf)
            notes["forestcast_ch"] = "h_* snapshot at %d held constant across the test window" % ly
        except Exception as e:
            log("      forestcast_ch failed: %s" % type(e).__name__)
    return out, notes


def fitted_arms(meta, X, y, tr, te, pool):
    out = {}
    ti = np.where(tr)[0]
    if len(ti) > REGROWS:
        ti = ti[np.linspace(0, len(ti) - 1, REGROWS).astype(np.int64)]
    zb = (y > THR)

    # --- Sales et al. two-part hurdle, both limbs as plain GLMs ---------------------------------
    try:
        from sklearn.linear_model import LogisticRegression, GammaRegressor
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.isotonic import IsotonicRegression
        occ = make_pipeline(StandardScaler(),
                            LogisticRegression(C=0.01, max_iter=2000, class_weight="balanced",
                                               n_jobs=JOBS, random_state=SEED))
        occ.fit(X[ti], zb[ti].astype(np.int32))
        pr = occ.predict_proba(X)[:, 1]
        iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        iso.fit(pr[ti], zb[ti].astype(np.float64))
        P = np.clip(iso.predict(pr), 0.0, 1.0)
        tp = ti[zb[ti]]
        m_neg = float(y[ti][~zb[ti]].mean()) if (~zb[ti]).any() else 0.0
        if len(tp) >= 50:
            gm = make_pipeline(StandardScaler(), GammaRegressor(alpha=1.0, max_iter=300))
            gm.fit(X[tp], np.clip(y[tp], 1e-6, None))
            Mg = np.clip(gm.predict(X), 0.0, 1.0)
        else:
            Mg = np.full(len(y), float(y[tp].mean()) if len(tp) else m_neg)
        out["sales_hurdle"] = P * Mg + (1 - P) * m_neg
    except Exception as e:
        log("      sales_hurdle failed: %s" % type(e).__name__)

    if pool is None:
        return out
    Xp, yp = pool
    Xc = np.concatenate([Xp, X[ti]]); yc = np.concatenate([yp, y[ti]])
    try:
        from sklearn.ensemble import RandomForestRegressor
        cap = min(len(yc), 150000)
        s = np.linspace(0, len(yc) - 1, cap).astype(np.int64)
        rf = RandomForestRegressor(n_estimators=200, max_depth=14, min_samples_leaf=5,
                                   max_features="sqrt", n_jobs=JOBS, random_state=SEED)
        rf.fit(Xc[s], yc[s])
        out["vieilledent"] = rf.predict(X)
        del rf
        gc.collect()
    except Exception as e:
        log("      vieilledent failed: %s" % type(e).__name__)
    try:
        from xgboost import XGBRegressor
        xg = XGBRegressor(n_estimators=NEST, max_depth=6, learning_rate=0.05, subsample=0.8,
                          colsample_bytree=0.5, reg_lambda=1.0, n_jobs=JOBS,
                          random_state=SEED, tree_method="hist")
        xg.fit(Xc, yc)
        out["cuelarosa"] = xg.predict(X)
        del xg
        gc.collect()
    except Exception as e:
        log("      cuelarosa failed: %s" % type(e).__name__)
    del Xc, yc
    gc.collect()
    return out


def softgate(meta, X, y, tr, donors):
    Ar = S.stack([T.bank_path(ARM, d, RNT, RMF) for d in donors], X, len(meta))
    Ab = S.stack([B.bank_path(d) for d in donors], X, len(meta))
    if Ar is None or Ab is None:
        return {}
    ti = np.where(tr)[0]
    if len(ti) > REGROWS:
        ti = ti[np.linspace(0, len(ti) - 1, REGROWS).astype(np.int64)]
    zb = (y > THR)
    tp = ti[zb[ti]]
    out = {}
    if len(tp) >= 30:
        rm = S.ridge(Ar, y, tp, LAM)
        rb = S.ridge(Ab, zb.astype(np.float64), ti, LAM)
        if rm is not None and rb is not None:
            from sklearn.isotonic import IsotonicRegression
            s = S.apply(Ab, rb)
            iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
            iso.fit(s[ti], zb[ti].astype(np.float64))
            P = np.clip(iso.predict(s), 0.0, 1.0)
            Mg = np.clip(S.apply(Ar, rm), 0.0, 1.0)
            m_neg = float(y[ti][~zb[ti]].mean()) if (~zb[ti]).any() else 0.0
            out["softgate"] = P * Mg + (1 - P) * m_neg
    del Ar, Ab
    gc.collect()
    return out


def run_region(reg, donors, cols, pool):
    dst = os.path.join(OUT, "%s_%s_f%d.csv" % (reg, ARM, FITTED))
    if os.path.exists(dst):
        log("  %-24s cached" % reg)
        return pd.read_csv(dst)
    t0 = time.time()
    meta, X = T.load_region(reg, cols, cap=MAXCELLS)
    if not len(meta):
        return None
    y = meta.y.to_numpy(np.float64)
    tr = meta.is_train.to_numpy() == 1
    te = ~tr
    if te.sum() < 100:
        return None
    clim = meta[tr].groupby("cell_id").y.mean()
    cv = meta.cell_id.map(clim).fillna(float(y[tr].mean())).to_numpy(np.float64)
    den = float(np.sum((y[te] - cv[te]) ** 2))
    ext = y[te] > 0.05

    P, notes = paper_arms(meta, X, cols, y, tr, te)
    if FITTED:
        P.update(fitted_arms(meta, X, y, tr, te, pool))
    P.update(softgate(meta, X, y, tr, donors))

    rows = []
    for nm, p in P.items():
        q = np.clip(np.nan_to_num(p), 0.0, 1.0)
        rows.append(dict(region=reg, arm=nm,
                         r2c=1.0 - float(np.sum((y[te] - q[te]) ** 2)) / max(den, 1e-30),
                         mae=float(np.mean(np.abs(y[te] - q[te]))),
                         hit=float(np.mean(np.abs(y[te] - q[te]) <= 0.005)),
                         predmax=float(q[te].max()), predmean=float(q[te].mean()),
                         mae_ext=float(np.mean(np.abs(y[te] - q[te])[ext])) if ext.any() else np.nan,
                         note=notes.get(nm, "")))
    R = pd.DataFrame(rows)
    R["n_te"], R["n_ext"], R["thr"] = int(te.sum()), int(ext.sum()), THR
    R.to_csv(dst, index=False)
    a = R.set_index("arm").r2c
    log("  %-24s vm0015 %+7.4f | ff_persist %+7.4f | softgate %+7.4f | %.1f min"
        % (reg, a.get("vm0015", np.nan), a.get("ff_persist", np.nan), a.get("softgate", np.nan),
           (time.time() - t0) / 60))
    del X, meta
    gc.collect()
    return R


def main():
    DON, TST = T.load_split()
    C = pd.read_csv("D:/run89full/forest_census.csv")
    forested = C[C.frac_tc30 >= 0.25].sort_values("cells").region.tolist()
    donors = [r for r in forested if r in DON][:NDON]
    tests = [r for r in forested if r in TST][FROM:FROM + NTEST]
    cols = T.feature_cols(ARM)
    log("=" * 122)
    log("PUBLISHED BASELINES vs THE SOFT GATE | arm %s | %d donors | %d regions | fitted %s"
        % (ARM, len(donors), len(tests), "ON" if FITTED else "off"))
    log("  every arm is a named published method rebuilt on THESE rows; no published accuracy is quoted")
    t0 = time.time()
    pool = None
    if FITTED:
        Xs, ys = [], []
        per = max(POOLROWS // max(len(donors), 1), 1000)
        for d in donors:
            m, Xd = T.load_region(d, cols, cap=None, train_only=True)
            if len(m) > per:
                s = np.linspace(0, len(m) - 1, per).astype(np.int64)
                Xd, m = Xd[s], m.iloc[s]
            Xs.append(Xd); ys.append(m.y.to_numpy(np.float64))
            del Xd, m
            gc.collect()
        pool = (np.concatenate(Xs), np.concatenate(ys))
        del Xs, ys
        gc.collect()
        log("  donor pool: %s rows from %d donors" % (format(len(pool[1]), ","), len(donors)))
    allR = [r for r in (run_region(x, donors, cols, pool) for x in tests) if r is not None]
    if not allR:
        log("no regions scored")
        return
    D = pd.concat(allR, ignore_index=True)
    D.to_csv(os.path.join(OUT, "_all_%s_f%d.csv" % (ARM, FITTED)), index=False)
    G = D.groupby("arm").agg(r2c=("r2c", "mean"), mae=("mae", "mean"), hit=("hit", "mean"),
                             predmax=("predmax", "mean"), mae_ext=("mae_ext", "mean"),
                             n=("region", "nunique")).sort_values("r2c", ascending=False)
    base = float(G.loc["softgate", "r2c"]) if "softgate" in G.index else np.nan
    log("=" * 122)
    log("RESULT | %d regions | ranked by R2c | softgate is the reference" % D.region.nunique())
    log("  %-14s %10s %12s %9s %7s %11s %11s"
        % ("arm", "R2c", "vs softgate", "MAE", "hit", "PRED MAX", "MAE@ext"))
    for nm, x in G.iterrows():
        tag = "  <-- OURS" if nm == "softgate" else ""
        log("  %-14s %+10.4f %+12.4f %9.6f %7.3f %11.4f %11.6f%s"
            % (nm, x.r2c, x.r2c - base, x.mae, x.hit, x.predmax, x.mae_ext, tag))
    if "softgate" in G.index:
        sg = D[D.arm == "softgate"].set_index("region").r2c
        log("")
        log("  SOFT GATE vs EACH PUBLISHED METHOD, jackknife over regions:")
        for nm in G.index:
            if nm == "softgate":
                continue
            o = D[D.arm == nm].set_index("region").r2c
            c = sorted(set(sg.index) & set(o.index))
            d = (sg[c] - o[c]).dropna()
            if len(d) < 2:
                continue
            jk = np.array([np.delete(d.values, i).mean() for i in range(len(d))])
            se = np.sqrt((len(d) - 1) / len(d) * ((jk - jk.mean()) ** 2).sum())
            lo, hi = d.mean() - 1.96 * se, d.mean() + 1.96 * se
            log("    vs %-14s %+.4f  95%% CI [%+.4f, %+.4f]  we win %d/%d  %s"
                % (nm, d.mean(), lo, hi, int((d > 0).sum()), len(d),
                   "SIG" if lo > 0 else ("SIG AGAINST US" if hi < 0 else "ns")))
    nt = D[D.note.astype(str).str.len() > 0][["arm", "note"]].drop_duplicates()
    if len(nt):
        log("")
        log("  ADAPTATIONS -- these arms are NOT the published model verbatim:")
        for _, x in nt.iterrows():
            log("    %-14s %s" % (x.arm, x.note))
    log("  DONE | %.1f min | artefacts in %s" % ((time.time() - t0) / 60, OUT))


if __name__ == "__main__":
    main()
