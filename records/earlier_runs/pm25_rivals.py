"""PM2.5 NOWCAST RIVALS -- the learning engines operational PM2.5 maps use, run on our drivers, against the
clean nowcast (nowref). Pre-registered in EXPERIMENT_SUMMARY Part 563; design PM25_RIVALS_PLAN.md; code
reviewed (Part 565: 20 findings fixed before any full-scale number).

WHY ENGINES, NOT PRODUCTS. Every operational PM2.5 product (ACAG, CAMS, MERRA-2, CHAP, EPA fused surfaces)
calibrates satellite AOD or a chemistry model against same-period monitors. Our inputs have neither by
design, so the fair rivals are the methods those products are built from, fed the architecture's own
inputs: the clean 103 drivers (oni/tni dropped -- centred means) + month + lat.
DISCLOSED ASYMMETRY: the rivals' learners take month (ridge: 12 dummies) and lat as inputs; the
architecture's trees see the 103 drivers only and month/lat reach it only through its per-cell linear
router (where lat is constant within a cell). Same information, used differently.
DISCLOSED GUARD STATUS: nowref is the 103-feature re-route of the tool and penalty that passed the N2 guard
at 105 features (log_corrector 3.8182 vs geometric normal 4.0744, D:/pm25_adapt/full/verdict.json); the
103-feature route itself was not re-guarded. Board B also prints an UNGUARDED diagnostic (raw MOS vs raw
nowref) -- never primary, never in the W/T/L counts.

THE RIVALS (core, owner ruling 2026-09-25)
    N  recent-level / trend normals from each cell's own pre-2020 record (no model, no donors)
    R  land-use-regression-style ridge (ESCAPE / CACES shape), solved in float64
    G  LightGBM (the most-used engine in national PM2.5 maps; Zhong 2021 = meteorology only)
    F  random forest (Hu 2017 shape), scikit-learn-intelex / oneDAL engine (recorded)
THE BOARDS
    A  donor-only: fitted on donor regions, never sees a test-cell label; hyperparameters picked by MAE on a
       FIXED donor holdout (every 4th donor region, frozen split order), 2017-2019 rows.
    C  (Part 571) OPERATIONAL PRODUCTS (MERRA-2): input-advantaged, never pooled with A/B/H/N -- --rivals M
    H  (Part 569) the GAUGED global model: one LightGBM trained on the donors AND the test cells' own history.
    B  the SAME local calibration for everyone: per cell, log1p(y) ~ [1, lclim - mean, month, z] on the cell's
       own history, OLS on the first three and a shrink (grid incl. 0) on the rival column z, picked jointly
       with the trial by inner MAE (MOS fitted <=2016, scored 2017-2019). N2 guard vs the geometric normal ->
       guess-normal. Without z the MOS IS the geometric normal (asserted). A cell whose z has < 1% log spread
       or < 12 informative rows gets no z (= its geometric normal), counted.
    N  the local no-model floor.
Everything is scored on nowref's 95,856 rows against ONE climatology (the L1 file's), with the per-region
jackknife and the R5 rule (band 0.0395 ug/m3). No clipping. Every row, every trial surface, every MOS
coefficient and every raw engine prediction is saved (owner rule: for future baseline tests).

    py -3.9 -u pm25_rivals.py --smoke                    all rivals at smoke scale
    py -3.9 -u pm25_rivals.py --timing --rivals G        one heavy + one light real trial per engine
    py -3.9 -u pm25_rivals.py --rivals N,R               then G, then F -- one heavy job at a time; resumable
    py -3.9 -u pm25_rivals.py --report                   the board tables over every finished rival
"""
import gc
import glob
import hashlib
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_ARGV = list(sys.argv)


def _num(flag, default, cast):
    if flag in _ARGV:
        return cast(_ARGV[_ARGV.index(flag) + 1])
    return default


SMOKE = "--smoke" in _ARGV
TIMING = "--timing" in _ARGV
REPORT = "--report" in _ARGV
# --use-done (owner ruling 2026-09-26, Part 567): pick from the trials ALREADY finished, run no new ones. The
# LightGBM grid was stopped for cost after 4 of 48 trials; this is declared before any LightGBM test number.
USE_DONE = "--use-done" in _ARGV
RIVALS = _num("--rivals", "N,R,G,F", str).split(",")
THREADS = _num("--threads", 6, int)
ROOT = "D:/pm25_rivals/%s" % ("smoke" if SMOKE else "full")
CACHE = os.path.join(ROOT, "cache")
LAMS = [0.0, 0.01, 0.1, 1.0, 10.0]          # Board-B shrink on the rival column (x n rows), incl. OLS
FIT_END, INNER_END = 2016, 2019
CHECKPOINTS = (100, 300, 1000)
PREREG = dict(don=2177990, don_le2016=1793679, cal=405391, cal_inner=71892, tst=95856, regions=20, cells=1997)
L1_FILES = ("donor_rows.parquet", "calib_rows.parquet", "predictions.parquet")
CODE = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:12]
ENGINE = {}

import pm25_adaptation as PAD              # noqa: E402  score(), EQ_UGM3; swaps argv for its imports
import adaptation as AD                    # noqa: E402  jack()

EQ = PAD.EQ_UGM3


def log(m):
    s = "[%s] %s" % (time.strftime("%H:%M:%S"), m)
    print(s, flush=True)
    os.makedirs(ROOT, exist_ok=True)
    with open(os.path.join(ROOT, "rivals.log"), "a", encoding="utf-8") as f:
        f.write(s + "\n")


def mem():
    try:
        import psutil
        mi = psutil.Process().memory_info()
        peak = getattr(mi, "peak_wset", mi.rss)
        return "peak RSS %.2f GB | RSS %.2f GB | free RAM %.2f GB" % (
            peak / 2**30, mi.rss / 2**30, psutil.virtual_memory().available / 2**30)
    except Exception:                      # noqa: BLE001 -- a missing psutil must not stop a run
        return "memory n/a"


def atomic_json(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(PAD._jsonable(obj), indent=1))
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def atomic_csv(df, path):
    df.to_csv(path + ".tmp", index=False)
    os.replace(path + ".tmp", path)


def fingerprint(src):
    out = {}
    for f in L1_FILES:
        p = os.path.join(src, f)
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for b in iter(lambda: fh.read(1 << 20), b""):
                h.update(b)
        out[f] = {"size": os.path.getsize(p), "sha256": h.hexdigest()}
    return out


# ------------------------------------------------------------------------------------------- data
def load():
    D = {}
    for name in ("don", "cal", "tst"):
        D[name] = {k: np.load(os.path.join(CACHE, "%s_%s.npy" % (name, k)), allow_pickle=False)
                   for k in ("X", "y", "year", "month", "reg", "cell_id")}
    D["keys"] = pd.read_parquet(os.path.join(CACHE, "tst_keys.parquet"))
    with open(os.path.join(CACHE, "meta.json"), encoding="utf-8") as fh:
        D["meta"] = json.load(fh)
    fp = D["meta"].get("l1_fingerprint")
    assert fp is not None and fingerprint(D["meta"]["source"]) == fp, \
        "L1 key files in %s changed since the cache was built -- rerun pm25_rivals_data.py" % D["meta"]["source"]
    t, k = D["tst"], D["keys"]
    assert (t["cell_id"] == k.cell_id.values.astype(str)).all() and np.abs(t["y"] - k.y.values).max() == 0.0, \
        "the cached test rows are not the key file's rows"
    assert int(D["don"]["year"].max()) <= INNER_END and int(D["cal"]["year"].max()) <= INNER_END
    if not SMOKE:
        got = dict(don=len(D["don"]["y"]), don_le2016=int((D["don"]["year"] <= FIT_END).sum()),
                   cal=len(D["cal"]["y"]), cal_inner=int((D["cal"]["year"] > FIT_END).sum()),
                   tst=len(t["y"]), regions=int(k.reg.nunique()), cells=int(k.cell_id.nunique()))
        assert got == PREREG, "the cache is not the Part 563 board: %s" % got
        assert D["meta"]["source"] == "D:/pm25_forecast/full/L1"
    return D


def cell_blocks(cell_id):
    """(starts, ends) of contiguous cell blocks -- the cached rows are in (cell, t) order."""
    change = np.r_[True, cell_id[1:] != cell_id[:-1]]
    starts = np.flatnonzero(change)
    ends = np.r_[starts[1:], len(cell_id)]
    assert len(np.unique(cell_id)) == len(starts), "a cell's rows are not contiguous"
    return starts, ends


def cell_month_mean(cell, month, v, cell_q, month_q):
    """Mean of v per (cell, month) over the given rows, looked up at (cell_q, month_q); cell-mean fallback."""
    df = pd.DataFrame({"c": cell, "m": month, "v": v})
    cm = df.groupby(["c", "m"]).v.mean()
    cc = df.groupby("c").v.mean()
    q = pd.MultiIndex.from_arrays([cell_q, month_q])
    out = pd.Series(cm.reindex(q).values)
    return out.fillna(pd.Series(cell_q).map(cc)).values


# -------------------------------------------------------------------------------------------- MOS
def mos(cal, fit_mask, app_rows, app_lc, z_cal, z_app, lams, with_z=True, coef=False):
    """THE BOARD-B LOCAL CALIBRATION. Per cell: log1p(y) ~ [1, lclim - m, month_s, z_s] on the cell's fit
    rows (lclim built from exactly those rows), OLS on the first three, penalty lam * n on z_s only.
    Returns log-space predictions (n_app x len(lams)) for the application rows (dict of cell_id, month)
    given their lclim `app_lc`; with coef=True also a per-cell coefficient table and the number of cells
    whose z was dropped (< 1% log spread or < 12 informative rows -> that cell's geometric normal)."""
    cid, mon, y = cal["cell_id"], cal["month"].astype(np.float64), cal["y"]
    fi = np.flatnonzero(fit_mask)
    lc_fit = cell_month_mean(cid[fi], cal["month"][fi], np.log1p(y[fi]), cid[fi], cal["month"][fi])
    s_f, e_f = cell_blocks(cid[fi])
    s_a, e_a = cell_blocks(app_rows["cell_id"])
    assert (cid[fi][s_f] == app_rows["cell_id"][s_a]).all(), "fit and application cells differ"
    out = np.full((len(app_rows["cell_id"]), len(lams)), np.nan)
    tf = np.log1p(y[fi])
    mon_f = mon[fi]
    mon_a = app_rows["month"].astype(np.float64)
    z_f = z_cal[fi] if with_z else None
    rows, n_drop = [], 0
    for c in range(len(s_f)):
        a, b = s_f[c], e_f[c]
        p, q = s_a[c], e_a[c]
        lc, lca = lc_fit[a:b], app_lc[p:q]
        m0 = lc.mean()
        cols = [np.ones(b - a), lc - m0, (mon_f[a:b] - 6.5) / 3.452]
        colsa = [np.ones(q - p), lca - m0, (mon_a[p:q] - 6.5) / 3.452]
        mu = sd = np.nan
        if with_z:
            zf, za = z_f[a:b], z_app[p:q]
            mu, sd = zf.mean(), zf.std()
            if sd > 1e-2 and int(np.count_nonzero(zf > zf.min())) >= 12:
                cols.append((zf - mu) / sd)
                colsa.append((za - mu) / sd)
            else:
                n_drop += 1
        X, Xa = np.column_stack(cols), np.column_stack(colsa)
        G, g = X.T @ X, X.T @ tf[a:b]
        for j, lam in enumerate(lams):
            Gj = G.copy()
            if X.shape[1] == 4:
                Gj[3, 3] += lam * (b - a)
            beta = np.linalg.lstsq(Gj, g, rcond=None)[0]
            out[p:q, j] = Xa @ beta
            if coef:
                bb = np.r_[beta, [np.nan] * (4 - len(beta))]
                rows.append((cid[fi][a], lam, m0, mu, sd, X.shape[1] == 4, *bb))
    if coef:
        C = pd.DataFrame(rows, columns=["cell_id", "lam", "m0", "z_mu", "z_sd", "has_z",
                                        "b0", "b_lclim", "b_month", "b_z"])
        return out, C, n_drop
    return out


# ------------------------------------------------------------------------------------------ engines
def month_dummies(X):
    m = X[:, -2].astype(int)
    return np.column_stack([X[:, :-2], (m[:, None] == np.arange(1, 13)[None, :]).astype(np.float32), X[:, -1:]])


def engine_grid(rv):
    if rv == "R":
        return [dict(alpha=a, link=l) for l in ("y", "log1p") for a in (0.1, 1, 10, 100, 1e3, 1e4)]
    if rv == "G":
        return [dict(num_leaves=nl, learning_rate=lr, min_child_samples=mc, colsample_bytree=cs, link=l)
                for l in ("y", "log1p") for nl in (31, 127, 511) for lr in (0.1, 0.03)
                for mc in (20, 100) for cs in (0.3, 0.8)]
    if rv == "F":
        return [dict(max_features=mf, max_depth=md, link=l)
                for l in ("y", "log1p") for mf in (0.3, 0.6) for md in (12, 16)]
    raise ValueError(rv)


def fit_predict(rv, cfg, Xf, yf, Xs, rounds=None):
    """Fit one configuration; return {checkpoint: ([ug/m3 predictions per X in Xs], [link-space ones])}.
    No clip anywhere (PM2.5 is unbounded; rivals.py's _clip would cap it at 1)."""
    t = np.log1p(yf) if cfg["link"] == "log1p" else np.asarray(yf, np.float64)
    back = (lambda q: np.expm1(q)) if cfg["link"] == "log1p" else (lambda q: q)
    if rv == "R":
        # FLOAT64, CHUNKED GRAM (review): the patched sklearnex Ridge ran in float32 with thread-dependent
        # errors near the equivalence band. Constant columns are dropped explicitly.
        mu = np.zeros(0)
        n = len(t)
        p = month_dummies(Xf[:1]).shape[1]
        s1, s2 = np.zeros(p), np.zeros(p)
        for s in range(0, n, 200_000):
            B = month_dummies(Xf[s:s + 200_000]).astype(np.float64)
            s1 += B.sum(0)
            s2 += (B ** 2).sum(0)
        mu = s1 / n
        sd = np.sqrt(np.maximum(s2 / n - mu ** 2, 0.0))
        keep = sd > 1e-9
        tm = float(t.mean())
        G = np.zeros((int(keep.sum()),) * 2)
        g = np.zeros(int(keep.sum()))
        for s in range(0, n, 200_000):
            B = (month_dummies(Xf[s:s + 200_000]).astype(np.float64)[:, keep] - mu[keep]) / sd[keep]
            G += B.T @ B
            g += B.T @ (t[s:s + 200_000] - tm)
        G[np.diag_indices_from(G)] += cfg["alpha"]
        w = np.linalg.solve(G, g)
        qs = [((month_dummies(X).astype(np.float64)[:, keep] - mu[keep]) / sd[keep]) @ w + tm for X in Xs]
        assert all(np.isfinite(q).all() for q in qs), "ridge produced non-finite predictions"
        return {0: ([back(q) for q in qs], qs)}
    if rv == "G":
        import lightgbm as lgb
        n_max = rounds or max(CHECKPOINTS)
        m = lgb.LGBMRegressor(n_estimators=n_max, num_leaves=cfg["num_leaves"],
                              learning_rate=cfg["learning_rate"], min_child_samples=cfg["min_child_samples"],
                              colsample_bytree=cfg["colsample_bytree"], subsample=1.0, random_state=0,
                              deterministic=True, force_row_wise=True, num_threads=THREADS, verbose=-1)
        m.fit(Xf, t)
        ENGINE.setdefault("G", {"lightgbm": lgb.__version__, "threads": THREADS})
        out = {}
        for k in ([rounds] if rounds else list(CHECKPOINTS)):
            qs = [m.predict(X, num_iteration=k) for X in Xs]
            out[k] = ([back(q) for q in qs], qs)
        return out
    if rv == "F":
        import sklearn
        import sklearnex
        from sklearnex.ensemble import RandomForestRegressor as RF      # no silent fallback (review)
        m = RF(n_estimators=200, max_depth=cfg["max_depth"], max_features=cfg["max_features"],
               min_samples_leaf=5, random_state=0, n_jobs=THREADS).fit(Xf, t)
        ENGINE.setdefault("F", {"rf_class": RF.__module__ + "." + RF.__name__, "sklearnex": sklearnex.__version__,
                                "sklearn": sklearn.__version__, "threads": THREADS})
        qs = [m.predict(X) for X in Xs]
        del m
        gc.collect()
        return {0: ([back(q) for q in qs], qs)}
    raise ValueError(rv)


def zcol(cfg, p, q):
    """The rival's column in the log-link MOS: its log prediction as is, or log1p of a y-link prediction
    floored at 0 inside the log (a transformation of the covariate, not a clip of the prediction)."""
    return q if cfg["link"] == "log1p" else np.log1p(np.maximum(p, 0.0))


# -------------------------------------------------------------------------------------------- run
def sets(D):
    don, cal = D["don"], D["cal"]
    holdout = set(D["meta"]["donors"][::4])                     # FIXED: every 4th donor, frozen order
    fitm = (don["year"] <= FIT_END) & ~np.isin(don["reg"], list(holdout))
    hom = (don["year"] > FIT_END) & np.isin(don["reg"], list(holdout))
    calfit = cal["year"] <= FIT_END
    inn = cal["year"] > FIT_END
    return holdout, fitm, hom, calfit, inn


def run_model_rival(rv, D):
    don, cal, tst = D["don"], D["cal"], D["tst"]
    holdout, fitm, hom, calfit, inn = sets(D)
    assert int(don["year"][fitm].max()) <= FIT_END, "a trial saw a donor label past 2016"
    Xf, yf = don["X"][fitm], don["y"][fitm]
    Xh, yh = don["X"][hom], don["y"][hom]
    app_in = {"cell_id": cal["cell_id"][inn], "month": cal["month"][inn]}
    lc_in = cell_month_mean(cal["cell_id"][calfit], cal["month"][calfit], np.log1p(cal["y"][calfit]),
                            app_in["cell_id"], app_in["month"])
    clim_in = cell_month_mean(cal["cell_id"][calfit], cal["month"][calfit], cal["y"][calfit],
                              app_in["cell_id"], app_in["month"])
    y_in, reg_in = cal["y"][inn], cal["reg"][inn]
    geo_in = PAD.score(y_in, np.expm1(lc_in), clim_in, groups=reg_in)["mae"]
    chk = mos(cal, calfit, app_in, lc_in, None, None, [0.0], with_z=False)[:, 0]
    err = float(np.abs(chk - lc_in).max())
    assert err < 1e-8, "the MOS without its rival column is not the geometric normal (%.3g)" % err
    log("  %s: fit rows %s (<=%d, holdout %d regions excluded) | holdout scoring rows %s | inner %s | "
        "MOS check %.1e | geometric normal inner MAE %.4f"
        % (rv, format(len(yf), ","), FIT_END, len(holdout), format(len(yh), ","), format(int(inn.sum()), ","),
           err, geo_in))
    tdir = os.path.join(ROOT, "trials", rv)
    os.makedirs(tdir, exist_ok=True)
    kh = os.path.join(tdir, "keys_holdout.parquet")
    if not os.path.exists(kh):
        pd.DataFrame({"reg": don["reg"][hom], "cell_id": don["cell_id"][hom], "year": don["year"][hom],
                      "month": don["month"][hom], "y": yh}).to_parquet(kh, index=False)
        pd.DataFrame({"reg": reg_in, "cell_id": app_in["cell_id"], "year": cal["year"][inn],
                      "month": app_in["month"], "y": y_in, "clim_in": clim_in, "lclim_in": lc_in}).to_parquet(
            os.path.join(tdir, "keys_inner.parquet"), index=False)
    # ---- RESUMABLE TRIAL GRID (review): each finished trial is written atomically with a fingerprint
    grid = engine_grid(rv)
    tpath = os.path.join(ROOT, "trials_%s.csv" % rv)
    fp = "%s|%s|%d|%s|%s|%d|%d|%d" % (D["meta"]["built"], CODE, FIT_END, LAMS, CHECKPOINTS, len(yf), len(yh),
                                      int(inn.sum()))
    trials, have = [], set()
    if os.path.exists(tpath):
        old = pd.read_csv(tpath, float_precision="round_trip")
        if USE_DONE:
            # everything but the code hash must match: same cache, cut, shrinks, checkpoints and row counts
            strip = lambda f: "|".join(p for k, p in enumerate(str(f).split("|")) if k != 1)   # noqa: E731
            assert (old.fingerprint.map(strip) == strip(fp)).all(), \
                "%s is from a different cache/grid -- cannot reuse it" % tpath
            for r in old.to_dict("records"):
                assert all(r[k] == v for k, v in grid[int(r["trial"])].items()), "trial %d cfg changed" % r["trial"]
        else:
            assert (old.fingerprint == fp).all(), "%s is from a different cache/code/grid -- move it away" % tpath
        trials, have = old.to_dict("records"), set(old.trial.astype(int))
        log("  RESUME %s: %d of %d trials already done" % (rv, len(have), len(grid)))
    assert not (USE_DONE and not have), "--use-done needs finished trials in %s" % tpath
    for i, cfg in enumerate(grid):
        if i in have or USE_DONE:
            continue
        t0 = time.time()
        res = fit_predict(rv, cfg, Xf, yf, [Xh, cal["X"]])
        for ck, (ps, qs) in res.items():
            ph, pc = ps
            qc = qs[1]
            a_mae = float(np.mean(np.abs(yh - ph)))
            a_c2 = float(np.corrcoef(yh, ph)[0, 1] ** 2) if np.std(ph) > 0 else 0.0
            z = zcol(cfg, pc, qc)
            P, C, nd = mos(cal, calfit, app_in, lc_in, z, z[inn], LAMS, coef=True)
            P = np.expm1(P)
            maes = [float(np.mean(np.abs(y_in - P[:, j]))) for j in range(len(LAMS))]
            c2s = [float(np.corrcoef(y_in - clim_in, P[:, j] - clim_in)[0, 1] ** 2) for j in range(len(LAMS))]
            j = int(np.argmin(maes))
            np.savez_compressed(os.path.join(tdir, "t%03d_c%d.npz" % (i, ck)), ph=ph.astype(np.float32),
                                z_cal=z.astype(np.float32), P_inner=P.astype(np.float32), lams=np.array(LAMS))
            C.to_parquet(os.path.join(tdir, "t%03d_c%d_mos_coef.parquet" % (i, ck)), index=False)
            trials.append(dict(rival=rv, trial=i, checkpoint=ck, **cfg, A_holdout_mae=a_mae, A_holdout_corr2=a_c2,
                               B_inner_mae=maes[j], B_lambda=LAMS[j], B_inner_anom_corr2=c2s[j], B_z_dropped=nd,
                               **{"B_mae_lam%g" % l: mm for l, mm in zip(LAMS, maes)},
                               **{"B_c2_lam%g" % l: cc for l, cc in zip(LAMS, c2s)},
                               minutes=round((time.time() - t0) / 60.0, 2), fingerprint=fp))
        atomic_csv(pd.DataFrame(trials), tpath)
        best = min((r for r in trials if r["trial"] == i), key=lambda r: r["B_inner_mae"])
        log("    trial %2d %s -> A holdout MAE %.4f | B inner MAE %.4f (ck %d, lam %g, z dropped in %d cells) | "
            "%.1f min | %s" % (i, cfg, min(r["A_holdout_mae"] for r in trials if r["trial"] == i),
                               best["B_inner_mae"], best["checkpoint"], best["B_lambda"], best["B_z_dropped"],
                               (time.time() - t0) / 60.0, mem()))
        gc.collect()
    T = pd.DataFrame(trials).sort_values(["trial", "checkpoint"]).reset_index(drop=True)
    if USE_DONE:
        log("  !! REDUCED GRID (Part 567): picks from %d of %d pre-registered trials: %s"
            % (T.trial.nunique(), len(grid), [grid[int(i)] for i in sorted(T.trial.unique())]))
    else:
        assert sorted(T.trial.unique()) == list(range(len(grid))), "the trial grid is incomplete"
    pa = T.loc[T.A_holdout_mae.idxmin()]
    pb = T.loc[T.B_inner_mae.idxmin()]
    for tag, pk, col in (("A", pa, "A_holdout_corr2"), ("B", pb, "B_inner_anom_corr2")):
        pc_ = T.loc[T[col].idxmax()]
        flag = "" if pk[col] == T[col].max() else (" (the corr2 pick differs: trial %d ck %d, %.4f vs %.4f)"
                                                   % (int(pc_.trial), int(pc_.checkpoint), pc_[col], pk[col]))
        log("  PICK %s: trial %d checkpoint %d%s" % (tag, int(pk.trial), int(pk.checkpoint), flag))
    if float(pb.B_lambda) == max(LAMS):
        log("  !! EDGE: Board B picked the LARGEST shrink (%g) -- the rival column is being shrunk away" % max(LAMS))
    del Xf, yf, Xh, yh
    gc.collect()
    # ---- refit the picks on ALL donors <= 2019 (holdout included), same rounds; score 2020-2023 once
    Xall, yall = don["X"], don["y"]
    assert int(don["year"].max()) <= INNER_END
    out = {}
    for tag, pk in (("A", pa), ("B", pb)):
        cfg = grid[int(pk.trial)]
        rounds = int(pk.checkpoint) if rv == "G" else None
        res = fit_predict(rv, cfg, Xall, yall, [cal["X"], tst["X"]], rounds=rounds)
        (pc, pt), (qc, qt) = list(res.values())[0]
        pd.DataFrame({"reg": cal["reg"], "cell_id": cal["cell_id"], "year": cal["year"], "month": cal["month"],
                      "y": cal["y"], "p_engine": pc, "q_engine": qc}).to_parquet(
            os.path.join(ROOT, "pretest_%s_%s.parquet" % (tag, rv)), index=False)
        if tag == "A":
            out["A"] = dict(p=pt, p_engine=pt, q_engine=qt, cfg=cfg, pick=pk.to_dict())
        else:
            z_c, z_t = zcol(cfg, pc, qc), zcol(cfg, pt, qt)
            lam = float(pk.B_lambda)
            app_t = {"cell_id": tst["cell_id"], "month": tst["month"]}
            lc_t = D["keys"].lclim.values
            allfit = np.ones(len(cal["y"]), bool)
            PB, Cb, nd = mos(cal, allfit, app_t, lc_t, z_c, z_t, [lam], coef=True)
            pB = np.expm1(PB[:, 0])
            Cb.to_parquet(os.path.join(ROOT, "mos_coef_final_%s.parquet" % rv), index=False)
            ci = pd.read_parquet(os.path.join(tdir, "t%03d_c%d_mos_coef.parquet" % (int(pk.trial), int(pk.checkpoint))))
            ci[ci.lam == lam].to_parquet(os.path.join(ROOT, "mos_coef_inner_%s.parquet" % rv), index=False)
            ymax = pd.Series(cal["y"]).groupby(cal["cell_id"]).max()
            blow = int((pB > 3 * pd.Series(tst["cell_id"]).map(ymax).values).sum())
            guard = bool(pk.B_inner_mae < geo_in)
            out["B"] = dict(p=pB if guard else D["keys"].clim.values, p_raw_mos=pB, p_engine=pt, q_engine=qt,
                            z_test=z_t, cfg=cfg, pick=pk.to_dict(), guard_passes=guard, lam=lam, geo_inner=geo_in,
                            z_dropped_cells=nd, rows_above_3x_cell_max=blow)
            log("  BOARD B guard: inner MAE %.4f vs geometric normal %.4f -> %s | z dropped in %d cells | "
                "%d test rows > 3x their cell's max" % (pk.B_inner_mae, geo_in, "PASSES" if guard else
                                                         "FAILS: falls back to guess-normal", nd, blow))
        gc.collect()
    return out, T


def run_hist_rival(D):
    """H (owner request 2026-09-26, Part 569): the GAUGED global model -- ONE LightGBM trained on the donors AND
    the test cells' own history, as a data scientist with that history would do it. Grid = the 4 LightGBM
    settings finished under Part 567 x 3 checkpoints. Tuning: fit on donors + test cells <= 2016, pick by MAE
    on the test cells' 2017-2019 (the architecture's inner window); refit <= 2019 on both; score 2020-2023
    once. Same N2 guard as Board B (beat the geometric normal on the inner window, else guess-normal)."""
    don, cal, tst = D["don"], D["cal"], D["tst"]
    calfit, inn = cal["year"] <= FIT_END, cal["year"] > FIT_END
    dfit = don["year"] <= FIT_END
    Xf = np.vstack([don["X"][dfit], cal["X"][calfit]])
    yf = np.r_[don["y"][dfit], cal["y"][calfit]]
    assert int(max(don["year"][dfit].max(), cal["year"][calfit].max())) <= FIT_END, "a tuning fit saw a label past 2016"
    app_in = {"cell_id": cal["cell_id"][inn], "month": cal["month"][inn]}
    lc_in = cell_month_mean(cal["cell_id"][calfit], cal["month"][calfit], np.log1p(cal["y"][calfit]),
                            app_in["cell_id"], app_in["month"])
    clim_in = cell_month_mean(cal["cell_id"][calfit], cal["month"][calfit], cal["y"][calfit],
                              app_in["cell_id"], app_in["month"])
    y_in = cal["y"][inn]
    geo_in = PAD.score(y_in, np.expm1(lc_in), clim_in, groups=cal["reg"][inn])["mae"]
    grid = engine_grid("G")[:4]
    log("  H: tuning fit rows %s (donors %s + test-cell history %s, <=%d) | inner %s | grid = the 4 Part-567 "
        "settings x %s rounds | geometric normal inner MAE %.4f"
        % (format(len(yf), ","), format(int(dfit.sum()), ","), format(int(calfit.sum()), ","), FIT_END,
           format(int(inn.sum()), ","), CHECKPOINTS, geo_in))
    rows = []
    hdir = os.path.join(ROOT, "trials", "H")
    os.makedirs(hdir, exist_ok=True)
    for i, cfg in enumerate(grid):
        t0 = time.time()
        res = fit_predict("G", cfg, Xf, yf, [cal["X"][inn]])
        for ck, (ps, qs) in res.items():
            p = ps[0]
            rows.append(dict(rival="H", trial=i, checkpoint=ck, **cfg, inner_mae=float(np.mean(np.abs(y_in - p))),
                             inner_anom_corr2=_c2(y_in - clim_in, p - clim_in),
                             minutes=round((time.time() - t0) / 60.0, 2)))
            np.savez_compressed(os.path.join(hdir, "t%03d_c%d.npz" % (i, ck)), p_inner=p.astype(np.float32))
        atomic_csv(pd.DataFrame(rows), os.path.join(ROOT, "trials_H.csv"))
        best = min((r for r in rows if r["trial"] == i), key=lambda r: r["inner_mae"])
        log("    trial %d %s -> inner MAE %.4f (ck %d) | %.1f min | %s"
            % (i, cfg, best["inner_mae"], best["checkpoint"], (time.time() - t0) / 60.0, mem()))
        gc.collect()
    T = pd.DataFrame(rows)
    pk = T.loc[T.inner_mae.idxmin()]
    pc_ = T.loc[T.inner_anom_corr2.idxmax()]
    log("  PICK H: trial %d checkpoint %d (inner MAE %.4f)%s"
        % (int(pk.trial), int(pk.checkpoint), pk.inner_mae, "" if pk.trial == pc_.trial and pk.checkpoint ==
           pc_.checkpoint else " (the corr2 pick differs: trial %d ck %d)" % (int(pc_.trial), int(pc_.checkpoint))))
    del Xf, yf
    gc.collect()
    Xa = np.vstack([don["X"], cal["X"]])
    ya = np.r_[don["y"], cal["y"]]
    assert int(max(don["year"].max(), cal["year"].max())) <= INNER_END
    cfg = grid[int(pk.trial)]
    res = fit_predict("G", cfg, Xa, ya, [cal["X"], tst["X"]], rounds=int(pk.checkpoint))
    (pc, pt), (qc, qt) = list(res.values())[0]
    pd.DataFrame({"reg": cal["reg"], "cell_id": cal["cell_id"], "year": cal["year"], "month": cal["month"],
                  "y": cal["y"], "p_engine": pc}).to_parquet(os.path.join(ROOT, "pretest_H_G.parquet"), index=False)
    guard = bool(pk.inner_mae < geo_in)
    log("  H guard: inner MAE %.4f vs geometric normal %.4f -> %s"
        % (pk.inner_mae, geo_in, "PASSES" if guard else "FAILS: falls back to guess-normal"))
    return {"H": dict(p=pt if guard else D["keys"].clim.values, p_raw_mos=pt, p_engine=pt, q_engine=qt, cfg=cfg,
                      pick=pk.to_dict(), guard_passes=guard, geo_inner=geo_in)}, T


def run_product_rival(D, prod="merra2"):
    """BOARD C (Part 571): an OPERATIONAL PRODUCT, MERRA-2 surface PM2.5 (NASA reanalysis), mapped to our cells by
    pm25_products_map.py. INPUT-ADVANTAGED: it assimilates each month's satellite aerosol (the same instruments as
    the ACAG target) -- losing to it measures what that observation is worth, not an architecture defect.
        M0  the product as published
        M1  a 2-parameter log mapping log1p(y) = a + b log1p(pm), fitted on the DONOR rows <= 2019 (no test label)
        M2  the SAME per-cell local calibration as Board B, z = log1p(pm), shrink picked on the inner window, N2 guard
        MP  M2's placebo: z from the same cell and calendar month but ANOTHER YEAR -- keeps place and season, loses
            the month's actual state; if MP ~ M2, the product adds nothing beyond a seasonal/spatial prior."""
    don, cal, tst = D["don"], D["cal"], D["tst"]
    P = {k: np.load(os.path.join(CACHE, "%s_%s.npy" % (prod, k))) for k in ("don", "cal", "tst")}
    Pp = {k: np.load(os.path.join(CACHE, "%sp_%s.npy" % (prod, k))) for k in ("cal", "tst")}
    for k, v in P.items():
        assert len(v) == len(D[k]["y"]) and np.isfinite(v).all(), "%s product not aligned with the %s rows" % (prod, k)
    out = {"M0": dict(p=P["tst"], cfg={"arm": "raw product"})}
    # M1: donor-only 2-parameter log mapping
    assert int(don["year"].max()) <= INNER_END
    xd, yd = np.log1p(P["don"]), np.log1p(don["y"])
    b = float(np.cov(xd, yd)[0, 1] / np.var(xd, ddof=1))
    a = float(yd.mean() - b * xd.mean())
    out["M1"] = dict(p=np.expm1(a + b * np.log1p(P["tst"])), cfg={"arm": "donor log mapping", "a": a, "b": b})
    log("  %s: M1 donor mapping log1p(y) = %.3f + %.3f log1p(pm) (%s donor rows)" % (prod, a, b, format(len(yd), ",")))
    # M2 / MP: the Board-B local calibration with the product (or its wrong-year placebo) as the column
    calfit, inn = cal["year"] <= FIT_END, cal["year"] > FIT_END
    app_in = {"cell_id": cal["cell_id"][inn], "month": cal["month"][inn]}
    lc_in = cell_month_mean(cal["cell_id"][calfit], cal["month"][calfit], np.log1p(cal["y"][calfit]),
                            app_in["cell_id"], app_in["month"])
    clim_in = cell_month_mean(cal["cell_id"][calfit], cal["month"][calfit], cal["y"][calfit],
                              app_in["cell_id"], app_in["month"])
    y_in = cal["y"][inn]
    geo_in = PAD.score(y_in, np.expm1(lc_in), clim_in, groups=cal["reg"][inn])["mae"]
    app_t = {"cell_id": tst["cell_id"], "month": tst["month"]}
    allfit = np.ones(len(cal["y"]), bool)
    for arm, zc, zt in (("M2", np.log1p(P["cal"]), np.log1p(P["tst"])), ("MP", np.log1p(Pp["cal"]), np.log1p(Pp["tst"]))):
        Pin = np.expm1(mos(cal, calfit, app_in, lc_in, zc, zc[inn], LAMS))
        maes = [float(np.mean(np.abs(y_in - Pin[:, j]))) for j in range(len(LAMS))]
        j = int(np.argmin(maes))
        PT, Cf, nd = mos(cal, allfit, app_t, D["keys"].lclim.values, zc, zt, [LAMS[j]], coef=True)
        pT = np.expm1(PT[:, 0])
        Cf.to_parquet(os.path.join(ROOT, "mos_coef_final_%s.parquet" % arm), index=False)
        guard = bool(maes[j] < geo_in)
        out[arm] = dict(p=pT if guard else D["keys"].clim.values, p_raw_mos=pT, cfg={"arm": arm, "lam": LAMS[j]},
                        pick={"inner_mae": maes[j], **{"inner_mae_lam%g" % l: mm for l, mm in zip(LAMS, maes)}},
                        guard_passes=guard, lam=LAMS[j], geo_inner=geo_in, z_dropped_cells=nd)
        log("  %s %s: inner MAE %.4f (shrink %g%s) vs geometric normal %.4f -> %s | z dropped in %d cells"
            % (prod, arm, maes[j], LAMS[j], ", EDGE" if LAMS[j] == max(LAMS) else "", geo_in,
               "PASSES" if guard else "FAILS: falls back to guess-normal", nd))
    return out


def run_normals(D):
    """N: each cell's own record, no model. Build on <=2016, pick on 2017-2019, rebuild <=2019, score once."""
    cal, tst = D["cal"], D["tst"]
    cid, mon, yr, y = cal["cell_id"], cal["month"], cal["year"].astype(int), cal["y"]
    grid = [dict(k=k, scale=s, damp=d) for k in (1, 2, 3, 5) for s in ("log", "raw") for d in (0.0, 0.5, 1.0)]

    def predict(cfg, end, q_cell, q_month, q_year):
        m = yr <= end
        v = np.log1p(y[m]) if cfg["scale"] == "log" else y[m]
        rec = m & (yr > end - cfg["k"])
        vr = np.log1p(y[rec]) if cfg["scale"] == "log" else y[rec]
        level = cell_month_mean(cid[rec], mon[rec], vr, q_cell, q_month)
        out = level
        if cfg["damp"] > 0:
            # per-cell OLS slope of the de-seasonalised series on the integer year, over all rows <= end
            clm = cell_month_mean(cid[m], mon[m], v, cid[m], mon[m])
            df = pd.DataFrame({"c": cid[m], "a": v - clm, "t": yr[m].astype(np.float64)})
            g = df.groupby("c")
            tm, am = g.t.transform("mean"), g.a.transform("mean")
            slope = ((df.t - tm) * (df.a - am)).groupby(df.c).sum() / ((df.t - tm) ** 2).groupby(df.c).sum()
            # CORRECTED (review): the level is a SAME-MONTH mean centred on the recent window's middle year,
            # so the horizon is simply target year - that year; the month offset cancels.
            ahead = q_year.astype(np.float64) - (end - (cfg["k"] - 1) / 2.0)
            out = level + cfg["damp"] * pd.Series(q_cell).map(slope).fillna(0.0).values * ahead
        return np.expm1(out) if cfg["scale"] == "log" else out

    inn = yr > FIT_END
    clim_in = cell_month_mean(cid[~inn], mon[~inn], y[~inn], cid[inn], mon[inn])
    rows = []
    for i, cfg in enumerate(grid):
        p = predict(cfg, FIT_END, cid[inn], mon[inn], yr[inn])
        rows.append(dict(rival="N", trial=i, **cfg, B_inner_mae=float(np.mean(np.abs(y[inn] - p))),
                         B_inner_anom_corr2=float(np.corrcoef(y[inn] - clim_in, p - clim_in)[0, 1] ** 2)))
    T = pd.DataFrame(rows)
    atomic_csv(T, os.path.join(ROOT, "trials_N.csv"))
    pk = T.loc[T.B_inner_mae.idxmin()]
    pc_ = T.loc[T.B_inner_anom_corr2.idxmax()]
    flag = "" if pk.B_inner_anom_corr2 == T.B_inner_anom_corr2.max() else (
        " (the corr2 pick differs: trial %d, %.4f vs %.4f)" % (int(pc_.trial), pc_.B_inner_anom_corr2,
                                                               pk.B_inner_anom_corr2))
    cfg = grid[int(pk.trial)]
    p = predict(cfg, INNER_END, tst["cell_id"], tst["month"], tst["year"].astype(int))
    log("  N pick: %s (inner MAE %.4f)%s" % (cfg, pk.B_inner_mae, flag))
    return {"N": dict(p=p, cfg=cfg, pick=pk.to_dict())}, T


# ----------------------------------------------------------------------------------------- report
def verdict(dv):
    """R5 with the band. dv = MAE(rival) - MAE(nowref) per region: POSITIVE = the architecture is better."""
    m_, lo, hi, se = AD.jack(dv)
    if not np.isfinite(lo):
        tag = "CANNOT TELL"
    elif lo > 0 and m_ >= EQ:
        tag = "ARCHITECTURE BETTER"
    elif hi < 0 and m_ <= -EQ:
        tag = "RIVAL BETTER"
    elif -EQ <= lo and hi <= EQ:
        tag = "EQUIVALENT"
    else:
        tag = "CANNOT TELL"
    return m_, lo, hi, se, tag


def _c2(a, b):
    return float(np.corrcoef(a, b)[0, 1] ** 2) if np.std(a) > 0 and np.std(b) > 0 else float("nan")


def save_and_score(D, board, rv, info):
    k = D["keys"]
    p = np.asarray(info["p"], np.float64)
    assert np.isfinite(p).all(), "%s/%s: %d non-finite predictions" % (board, rv, int((~np.isfinite(p)).sum()))
    assert len(p) == len(k) == len(D["tst"]["y"]) == int(D["meta"]["rows"]["tst"])
    assert not np.mean(np.isclose(p, 1.0)) > 0.5, "predictions look clipped at 1 ug/m3"
    d = k[["reg", "cell_id", "year", "month", "y", "clim", "lclim", "p_nowref", "p_guess_normal",
           "p_geo_normal"]].copy()
    d["p_rival"] = p
    for c in ("p_engine", "q_engine", "z_test"):
        if c in info:
            d[c.replace("_test", "_rival")] = info[c]
    if "p_raw_mos" in info:
        d["p_rival_mos_before_guard"] = info["p_raw_mos"]
    os.makedirs(os.path.join(ROOT, board), exist_ok=True)
    d.to_parquet(os.path.join(ROOT, board, "%s.parquet" % rv), index=False, compression="zstd")
    s = PAD.score(d.y.values, p, d.clim.values, groups=d.reg.values)
    assert s["n"] == len(d), "%s/%s scored %d of %d rows" % (board, rv, s["n"], len(d))
    cols = {"rival": "p_rival", "nowref": "p_nowref", "guess_normal": "p_guess_normal", "geo_normal": "p_geo_normal"}

    def _tab(g):
        o = {}
        for nm, c in cols.items():
            sc = PAD.score(g.y.values, g[c].values, g.clim.values, groups=g.reg.values)
            o["mae_" + nm], o["anomR2_" + nm], o["hit_" + nm] = sc.get("mae"), sc.get("r2"), sc.get("hit")
        o["anom_corr2_rival"] = _c2((g.y - g.clim).values, (g.p_rival - g.clim).values)
        o["anom_corr2_nowref"] = _c2((g.y - g.clim).values, (g.p_nowref - g.clim).values)
        o["level_ratio_rival"] = float(g.p_rival.mean() / g.y.mean())
        o["n"] = len(g)
        return pd.Series(o)

    R = d.groupby("reg").apply(_tab)
    R["dv"] = R.mae_rival - R.mae_nowref
    R.to_csv(os.path.join(ROOT, board, "%s_per_region.csv" % rv))
    Y = d.groupby("year").apply(_tab)
    Y.to_csv(os.path.join(ROOT, board, "%s_per_year.csv" % rv))
    dv = R.dv.to_numpy()
    m_, lo, hi, se, tag = verdict(dv)
    w, l_ = int((dv > EQ).sum()), int((dv < -EQ).sum())
    row = dict(board=board, rival=rv, mae=s["mae"], anomR2=s["r2"], hit=s["hit"],
               level_ratio=float(p.mean() / d.y.mean()), contrast_vs_nowref=m_, lo=lo, hi=hi, verdict=tag,
               arch_wins=w, ties=int(len(dv) - w - l_), rival_wins=l_,
               per_year={int(a): float(b) for a, b in Y.mae_rival.items()}, cfg=info.get("cfg"),
               guard_passes=info.get("guard_passes"), lam=info.get("lam"), geo_inner=info.get("geo_inner"),
               z_dropped_cells=info.get("z_dropped_cells"), rows_above_3x_cell_max=info.get("rows_above_3x_cell_max"),
               engine=ENGINE.get(rv), code=CODE, threads=THREADS)
    if "p_raw_mos" in info:
        # UNGUARDED DIAGNOSTIC (review): raw MOS vs raw nowref -- never primary, never counted in W/T/L
        rr = d.assign(e=np.abs(d.y - d.p_rival_mos_before_guard)).groupby("reg").e.mean() - R.mae_nowref
        m2, lo2, hi2, _, tag2 = verdict(rr.to_numpy())
        row.update(unguarded_mae=float(np.mean(np.abs(d.y - d.p_rival_mos_before_guard))),
                   unguarded_contrast=m2, unguarded_lo=lo2, unguarded_hi=hi2, unguarded_verdict=tag2)
        log("  %s %-2s UNGUARDED DIAGNOSTIC (%s vs raw nowref): MAE %.4f | %+.4f [%+.4f, %+.4f] %s"
            % (board, rv, "raw MOS" if board in ("B", "C") else "raw model", row["unguarded_mae"], m2, lo2, hi2, tag2))
    atomic_json(dict(row, pick=info.get("pick")), os.path.join(ROOT, board, "%s.json" % rv))
    log("  %s %-2s MAE %.4f anomR2 %+.4f hit %.3f | rival - nowref %+.4f [%+.4f, %+.4f] %s  W/T/L(arch) %d/%d/%d"
        % (board, rv, s["mae"], s["r2"], s["hit"], m_, lo, hi, tag, w, int(len(dv) - w - l_), l_))
    return row


def report():
    rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, "[ABCNH]", "*.json"))):
        with open(f, encoding="utf-8") as fh:
            rows.append(json.load(fh))
    if not rows:
        log("no finished rivals yet")
        return
    T = pd.DataFrame(rows).sort_values(["board", "mae"])
    T.to_csv(os.path.join(ROOT, "board.csv"), index=False)
    k = pd.read_parquet(os.path.join(CACHE, "tst_keys.parquet"))
    sc = {c: PAD.score(k.y.values, k[c].values, k.clim.values, groups=k.reg.values)
          for c in ("p_nowref", "p_guess_normal", "p_geo_normal")}
    log("=" * 92)
    log("  nowref (clean nowcast, same rows): MAE %.4f / anomR2 %+.3f | guess-normal %.4f | geo %.4f"
        % (sc["p_nowref"]["mae"], sc["p_nowref"]["r2"], sc["p_guess_normal"]["mae"], sc["p_geo_normal"]["mae"]))
    for _, r in T.iterrows():
        log("  board %s  %-2s MAE %.4f anomR2 %+.4f | rival - nowref %+.4f [%+.4f, %+.4f]  %s"
            % (r.board, r.rival, r.mae, r.anomR2, r.contrast_vs_nowref, r.lo, r.hi, r.verdict))


def thread_record():
    from threadpoolctl import threadpool_info
    rec = {"threads": THREADS, "argv": _ARGV, "code": CODE,
           "threadpool_info": [{k: d.get(k) for k in ("user_api", "internal_api", "prefix", "num_threads", "version")}
                               for d in threadpool_info()],
           "env": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")}}
    for f in glob.glob(os.path.join(ROOT, "threads_*.json")):
        with open(f, encoding="utf-8") as fh:
            old = json.load(fh)
        assert old["threads"] == THREADS, "thread count differs from %s -- never change it mid-run" % f
    atomic_json(rec, os.path.join(ROOT, "threads_%s.json" % ("timing" if TIMING else "_".join(RIVALS))))


def timing(D):
    """One HEAVY and one light REAL trial per engine (fit on the Board-A fit rows, predict holdout + all
    calibration rows, one MOS pass), minutes x grid size = a bracket for the full grid."""
    holdout, fitm, hom, calfit, inn = sets(D)
    don, cal = D["don"], D["cal"]
    app_in = {"cell_id": cal["cell_id"][inn], "month": cal["month"][inn]}
    lc_in = cell_month_mean(cal["cell_id"][calfit], cal["month"][calfit], np.log1p(cal["y"][calfit]),
                            app_in["cell_id"], app_in["month"])
    heavy = {"R": 0, "G": 21, "F": 3}
    for rv in [r for r in RIVALS if r != "N"]:
        grid = engine_grid(rv)
        for idx in (heavy[rv], len(grid) // 2):
            t0 = time.time()
            res = fit_predict(rv, grid[idx], don["X"][fitm], don["y"][fitm], [don["X"][hom], cal["X"]])
            for ck, (ps, qs) in res.items():
                z = zcol(grid[idx], ps[1], qs[1])
                mos(cal, calfit, app_in, lc_in, z, z[inn], LAMS)
            dt = (time.time() - t0) / 60.0
            log("  TIMING %s trial %d %s: %.1f min (x%d = %.0f min bound) | %s"
                % (rv, idx, grid[idx], dt, len(grid), dt * len(grid), mem()))


def main():
    os.makedirs(ROOT, exist_ok=True)
    if REPORT:
        report()
        return 0
    D = load()
    log("=" * 92)
    log("PM2.5 NOWCAST RIVALS | %s | rivals %s | threads %d | %d features | test rows %s | code %s"
        % ("SMOKE" if SMOKE else "FULL", RIVALS, THREADS, D["don"]["X"].shape[1], format(len(D["tst"]["y"]), ","),
           CODE))
    thread_record()
    if TIMING:
        timing(D)
        return 0
    for rv in RIVALS:
        t0 = time.time()
        if rv == "N":
            out, _ = run_normals(D)
            save_and_score(D, "N", "N", out["N"])
        elif rv == "H":
            out, _ = run_hist_rival(D)
            save_and_score(D, "H", "G", out["H"])
        elif rv == "M":
            out = run_product_rival(D, "merra2")
            for arm in ("M0", "M1", "M2", "MP"):
                save_and_score(D, "C", arm, out[arm])
        else:
            out, _ = run_model_rival(rv, D)
            if rv in ENGINE:
                log("  %s engine: %s" % (rv, ENGINE[rv]))
            for board in ("A", "B"):
                save_and_score(D, board, rv, out[board])
        log("  rival %s done in %.1f min | %s" % (rv, (time.time() - t0) / 60.0, mem()))
    report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
