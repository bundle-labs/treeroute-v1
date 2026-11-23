"""Small TIME-AWARE bundle (290-feat no-leak+lag+rollwater+water-memory) WITH the leakage-free REGIME prior
(Part 80) -> does the regime TRANSFER cross-region? 10 donor regions trained on ALL their cells + ALL years;
router (per-cell ridge) calibrated on held-out thar 2002-2019, tested 2020-2023. NO cell cap: a donor is
loaded whole when it fits, else STREAMED in shuffled 2000-cell chunks with CatBoost init_model warm-start
(CPU — GPU can't continue-train), exactly like experiment_regime_stream.py. Each donor is trained BOTH ways
(no-regime 'all' + with-regime 'all_reg') for a matched delta; 1-model-per-region bundle.

Regime is per-region OOF & leakage-free: donors get OOF 3-class P_dry/P_wet over ALL their cell-years; thar
gets OOF over 2002-2019 + a cal-trained classifier for the 2020-2023 test years (from features, never test
NDVI). Reuses the streaming feature machinery from experiment_regime_stream.py. Crash-safe at REGION level:
caches D:\\small_bundle_regime_models\\<region>\\{all,all_reg}.cbm (a mid-stream kill re-does that region).
RUN: py -3.9 presplit_cc/train_small_bundle_regime_thar.py   (in YOUR terminal; resumes; --cpu)
"""
import glob
import os
import sys
import time

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, CatBoostRegressor, Pool
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import monthly_loader as ML  # noqa: E402
from experiment_regime_stream import build_feats, load, prep, _f32, CAT  # noqa: E402
from train_small_bundle_wm_thar import PICK10, base_feats, ITERS, DEPTH, LR, ALPHA  # noqa: E402

PANEL, TARGET = ML.PANEL_DIR, ML.TARGET
MD = r"D:\small_bundle_regime_models"
os.makedirs(MD, exist_ok=True)
USE_GPU = "--cpu" not in sys.argv
FIT_CELLS, BATCH_CELLS, TOTAL_TREES, NFOLD, SEED = 5000, 2000, 1000, 5, 0
FEATS0 = [c for c in base_feats() if c != CAT]          # base numeric no-leak drivers for the regime stage-1
LAGVARS = None                                          # set once from a thar sample


def rfiles(r):
    return sorted(glob.glob(os.path.join(PANEL, f"{r}_monthly_*.parquet")))


def region_cells(files):
    return pd.concat([pd.read_parquet(f, columns=["cell_id"]) for f in files], ignore_index=True)["cell_id"].unique()


def _clf(X, y):
    kw = dict(iterations=400, depth=DEPTH, learning_rate=LR, loss_function="MultiClass",
              random_seed=0, verbose=0, allow_writing_files=False)
    try:
        m = CatBoostClassifier(task_type="GPU" if USE_GPU else "CPU", **kw); m.fit(Pool(X, y)); return m
    except Exception:
        m = CatBoostClassifier(**kw); m.fit(X, y); return m


def cellyear_regime(ann, test_region):
    """ann: [cell_id, year, *FEATS0, annN] -> add OOF 3-class P_dry/P_wet -> [cell_id, year, clf_dry, clf_wet]."""
    calm = (ann.year <= 2019).to_numpy() if test_region else np.ones(len(ann), bool)
    imp = SimpleImputer(strategy="median").fit(ann.loc[calm, FEATS0])
    X = imp.transform(ann[FEATS0]).astype(np.float32)
    g = ann.cell_id.to_numpy()

    def tertile(s):
        if len(s) < 3:
            return pd.Series(1, index=s.index)
        return pd.qcut(s.rank(method="first"), 3, labels=[0, 1, 2]).astype(int)
    reg3 = np.full(len(ann), 1, np.int64)
    reg3[calm] = ann[calm].groupby("cell_id")["annN"].transform(tertile).to_numpy()
    idx = np.where(calm)[0]
    proba = np.full((len(ann), 3), np.nan, np.float32)
    for a, b in GroupKFold(NFOLD).split(X[idx], reg3[idx], g[idx]):
        proba[idx[b]] = _clf(X[idx][a], reg3[idx][a]).predict_proba(X[idx][b])
    if (~calm).any():
        proba[~calm] = _clf(X[idx], reg3[idx]).predict_proba(X[~calm])
    out = ann[["cell_id", "year"]].copy()
    out["clf_dry"], out["clf_wet"] = proba[:, 0], proba[:, 2]
    return out


def _ann(d):
    a = d.groupby(["cell_id", "year"], as_index=False)[FEATS0].mean()
    n = d.groupby(["cell_id", "year"], as_index=False)[TARGET].mean().rename(columns={TARGET: "annN"})
    return a.merge(n, on=["cell_id", "year"])


def regfit(d, feats, init, tpc):
    m = CatBoostRegressor(iterations=tpc, depth=DEPTH, learning_rate=LR, loss_function="RMSE",
                          random_seed=0, task_type="CPU", verbose=0, allow_writing_files=False)
    m.fit(Pool(prep(d, feats), d[TARGET].to_numpy(), cat_features=[feats.index(CAT)]), init_model=init)
    return m


def gpu_fit(d, feats, out):
    def f(dev):
        m = CatBoostRegressor(iterations=ITERS, depth=DEPTH, learning_rate=LR, loss_function="RMSE",
                              random_seed=0, task_type=dev, verbose=0, allow_writing_files=False)
        m.fit(Pool(prep(d, feats), d[TARGET].to_numpy(), cat_features=[feats.index(CAT)])); return m
    try:
        m = f("GPU" if USE_GPU else "CPU")
    except Exception:
        m = f("CPU")
    m.save_model(out)


def train_donor(r, feats_wm, feats_reg):
    rdir = os.path.join(MD, r)
    os.makedirs(rdir, exist_ok=True)
    a, ar = os.path.join(rdir, "all.cbm"), os.path.join(rdir, "all_reg.cbm")
    if os.path.exists(a) and os.path.exists(ar):
        print(f"  {r}: cached -> skip", flush=True)
        return
    files = rfiles(r)
    cells = region_cells(files)
    n = len(cells)
    if n <= FIT_CELLS:                                   # whole-load, GPU
        df, _, _ = build_feats(load(files, None, None), LAGVARS)
        df = _f32(df)
        reg = cellyear_regime(_ann(df), test_region=False)
        d = df.merge(reg, on=["cell_id", "year"], how="left")
        d = d[d[TARGET].notna()]
        gpu_fit(d, feats_wm, a)
        gpu_fit(d, feats_reg, ar)
        print(f"  {r}: WHOLE {n:,} cells, {len(d):,} rows", flush=True)
        del df, d
    else:                                                # stream, warm-start CPU, ALL cells
        cl = cells.copy()
        np.random.RandomState(SEED).shuffle(cl)
        chunks = [cl[i:i + BATCH_CELLS].tolist() for i in range(0, n, BATCH_CELLS)]
        reg = cellyear_regime(pd.concat([_ann(load(files, ["cell_id", "year", TARGET] + FEATS0, ch)
                                               .pipe(lambda x: x[x[TARGET].notna()])) for ch in chunks],
                                        ignore_index=True), test_region=False)
        tpc = max(50, round(TOTAL_TREES / len(chunks)))
        m_no = m_reg = None
        for ci, ch in enumerate(chunks):
            df, _, _ = build_feats(load(files, None, ch), LAGVARS)
            d = _f32(df).merge(reg, on=["cell_id", "year"], how="left")
            d = d[d[TARGET].notna()]
            if len(d):
                m_no = regfit(d, feats_wm, m_no, tpc)
                m_reg = regfit(d, feats_reg, m_reg, tpc)
            del df, d
            print(f"    {r} chunk {ci+1}/{len(chunks)}", flush=True)
        if m_no is not None:
            m_no.save_model(a)
        if m_reg is not None:
            m_reg.save_model(ar)
        print(f"  {r}: STREAMED {n:,} cells, {len(chunks)} chunks", flush=True)


def main():
    global LAGVARS
    t0 = time.time()
    tf = rfiles("thar_desert")
    samp = load(tf, None, region_cells(tf)[:200].tolist())
    _, feats_wm, LAGVARS = build_feats(samp, None)
    feats_reg = feats_wm + ["clf_dry", "clf_wet"]
    del samp
    print(f"{len(PICK10)} donors | {len(feats_wm)} feats (+2 regime) | fit<= {FIT_CELLS} cells else stream | "
          f"clf={'GPU' if USE_GPU else 'CPU'}, warm-start=CPU", flush=True)

    for r in PICK10:
        train_donor(r, feats_wm, feats_reg)

    print("\nbuilding thar (test region, ALL cells) + regime ...", flush=True)
    thar, _, _ = build_feats(load(tf, None, None), LAGVARS)
    thar = _f32(thar)
    thar = thar.merge(cellyear_regime(_ann(thar), test_region=True), on=["cell_id", "year"], how="left")
    thar = thar[thar[TARGET].notna()].reset_index(drop=True)
    y = thar[TARGET].to_numpy(np.float64)
    cal, tst = thar.year.to_numpy() <= 2019, thar.year.to_numpy() >= 2020
    groups = thar.groupby("cell_id").indices

    def build_P(feats, name):
        pool = Pool(prep(thar, feats), cat_features=[feats.index(CAT)])
        P = np.zeros((len(thar), len(PICK10)))
        for j, r in enumerate(PICK10):
            P[:, j] = CatBoostRegressor().load_model(os.path.join(MD, r, f"{name}.cbm")).predict(pool)
        return P

    def route(P):
        I = ALPHA * np.eye(P.shape[1])
        pred = np.full(len(thar), np.nan)
        for c, idx in groups.items():
            idx = np.asarray(idx)
            ci = idx[cal[idx]]
            if len(ci) < 2:
                continue
            try:
                w = np.linalg.solve(P[ci].T @ P[ci] + I, P[ci].T @ y[ci])
            except np.linalg.LinAlgError:
                continue
            ti = idx[tst[idx]]
            if len(ti):
                pred[ti] = P[ti] @ w
        return pred

    print("\n==== SMALL BUNDLE (10 donors, ALL cells, 1-model) -> thar | in-region thar regime ref = 0.8190 ====")
    res = {}
    for label, feats, name in [("no-regime", feats_wm, "all"), ("+regime", feats_reg, "all_reg")]:
        pred = route(build_P(feats, name))
        v = tst & np.isfinite(pred)
        res[label] = r2_score(y[v], pred[v])
        print(f"  {label:10s} R2={res[label]:.4f}  RMSE={np.sqrt(mean_squared_error(y[v], pred[v])):.4f}", flush=True)
    print(f"\n  REGIME TRANSFER delta = {res['+regime']-res['no-regime']:+.4f}")
    print(f"done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
