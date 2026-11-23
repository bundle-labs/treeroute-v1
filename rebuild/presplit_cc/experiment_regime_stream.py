"""STREAMING warm-start generalization test (memory-bounded, ALL cells, NO subsampling). For regions too
big to fit in RAM: shuffle cells into chunks, build the exact 290 features per chunk (lags/rolling/ewm are
per-cell so a chunk of full cell-series is EXACT), and train CatBoost incrementally chunk-by-chunk via
init_model continuation -- the whole region never sits in RAM. Cells are SHUFFLED so each chunk is a
representative random sample, keeping warm-start close to true batch training. Two models (base_full vs
+clf_3class) trained in lockstep; test rows streamed to D:\\ and scored after training.

R2 is APPROXIMATE (sequential-chunk boosting != one batch fit); the base-vs-regime DELTA is the valid read.
Run thar first as a CALIBRATION (should land near the batch 0.819 -> confirms streaming ~= batch).

RUN: py -3.9 presplit_cc/experiment_regime_stream.py <region>   (--cpu to force CPU; --batch N cells/chunk)
     (no region -> lists available names)
"""
import glob
import os
import sys
import time

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pqa
from catboost import CatBoostClassifier, CatBoostRegressor, Pool
from sklearn.impute import SimpleImputer
from sklearn.metrics import r2_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import monthly_loader as ML  # noqa: E402
from experiment_thar_regime_full import REMOVE, CAT, GEO, WATERVARS, WINDOWS, PRECIP, DEPTH, LR  # noqa: E402

PANEL, TARGET = ML.PANEL_DIR, ML.TARGET
_args = [a for a in sys.argv[1:] if not a.startswith("--")]
REGION = _args[0] if _args else "thar_desert"
DEVICE = "CPU" if "--cpu" in sys.argv else "GPU"
BATCH_CELLS = int(sys.argv[sys.argv.index("--batch") + 1]) if "--batch" in sys.argv else 2000
TOTAL_TREES, SEED, NFOLD = 1000, 0, 5
TESTPQ = os.path.join("D:\\", f"regime_stream_test_{REGION}.parquet")
RES_CSV = r"D:\regime_generalize_stream.csv"


def _f32(df):
    for c in df.select_dtypes("float64").columns:
        df[c] = df[c].astype("float32")
    return df


def load(files, cols, keep):
    filt = [("cell_id", "in", keep)] if keep is not None else None
    return _f32(pd.concat([pd.read_parquet(f, columns=cols, filters=filt) for f in files], ignore_index=True))


def prep(dd, ff):
    X = dd[ff].copy()
    X[CAT] = X[CAT].fillna(-1).round().astype("int32").astype("string")
    return X


def _clf(X, y):
    kw = dict(iterations=400, depth=DEPTH, learning_rate=LR, loss_function="MultiClass",
              random_seed=0, verbose=0, allow_writing_files=False)
    try:
        m = CatBoostClassifier(task_type=DEVICE, **kw); m.fit(Pool(X, y)); return m
    except Exception:
        m = CatBoostClassifier(**kw); m.fit(X, y); return m


def build_feats(df, lagvars):
    cols = df.columns
    feats94 = [c for c in cols if c not in (ML.ID_KEYS + [TARGET] + GEO + REMOVE)]
    df["t"] = (df.year - 2002) * 12 + (df.month - 1)
    num = [f for f in feats94 if f != CAT]
    if lagvars is None:
        samp = df[df.cell_id.isin(df.cell_id.unique()[:120])]
        lagvars = [f for f in num if samp.groupby(["cell_id", "year"])[f].nunique().median() > 1]
    for k in (1, 2, 3):
        ren = {v: f"{v}_lag{k}" for v in lagvars}
        df = df.merge(df[["cell_id", "t"] + lagvars].rename(columns=ren).assign(t=lambda x: x.t + k),
                      on=["cell_id", "t"], how="left")
    feats = feats94 + [f"{v}_lag{k}" for k in (1, 2, 3) for v in lagvars]
    df = df.sort_values(["cell_id", "t"]).reset_index(drop=True)
    for v in WATERVARS:
        gv = df.groupby("cell_id", sort=False)[v]
        for w in WINDOWS:
            df[f"{v}_roll{w}"] = gv.rolling(w, min_periods=1).mean().to_numpy(); feats.append(f"{v}_roll{w}")
    df["wy"] = df.year - (df.month < 6).astype(int)
    df["precip_wytd"] = df.groupby(["cell_id", "wy"], sort=False)[PRECIP].cumsum(); feats.append("precip_wytd")
    df["api_precip"] = df.groupby("cell_id")[PRECIP].ewm(alpha=0.1, adjust=False).mean().reset_index(level=0, drop=True)
    df["api_soilmoist"] = df.groupby("cell_id")["V30_soil_moisture_pct"].ewm(alpha=0.1, adjust=False).mean().reset_index(level=0, drop=True)
    feats += ["api_precip", "api_soilmoist"]
    for v in ["soil_water_tc_mm", "V30_soil_moisture_pct", "V07_total_ref_ET_mm", "aet_total_mm", "climate_water_deficit_mm"]:
        df[f"{v}_wytd"] = df.groupby(["cell_id", "wy"], sort=False)[v].cumsum(); feats.append(f"{v}_wytd")
    wet10 = (df[PRECIP] >= 10).astype(int); g1 = wet10.groupby(df.cell_id).cumsum()
    df["consec_dry_months"] = (1 - wet10).groupby([df.cell_id, g1]).cumsum()
    sig30 = (df[PRECIP] >= 30).astype(int); g2 = sig30.groupby(df.cell_id).cumsum()
    df["months_since_sig_rain"] = (1 - sig30).groupby([df.cell_id, g2]).cumsum()
    feats += ["consec_dry_months", "months_since_sig_rain"]
    return _f32(df), feats, lagvars


def indicators(files, chunks, feats0):
    anns = []
    for ch in chunks:
        d = load(files, ["cell_id", "year", TARGET] + feats0, ch)
        d = d[d[TARGET].notna()]
        a = d.groupby(["cell_id", "year"], as_index=False)[feats0].mean()
        an = d.groupby(["cell_id", "year"], as_index=False)[TARGET].mean().rename(columns={TARGET: "annN"})
        anns.append(a.merge(an, on=["cell_id", "year"]))
    ann = pd.concat(anns, ignore_index=True)
    tmask = (ann.year >= 2020).to_numpy()
    imp = SimpleImputer(strategy="median").fit(ann.loc[~tmask, feats0])
    X = imp.transform(ann[feats0]).astype(np.float32)
    g = ann.cell_id.to_numpy()
    tr = ann[~tmask]
    def tertile(s):  # cells with <3 valid train years can't be split into 3 -> default to 'normal'
        if len(s) < 3:
            return pd.Series(1, index=s.index)
        return pd.qcut(s.rank(method="first"), 3, labels=[0, 1, 2]).astype(int)
    reg3 = np.full(len(ann), 1, np.int64)
    reg3[~tmask] = tr.groupby("cell_id")["annN"].transform(tertile).to_numpy()
    idx = np.where(~tmask)[0]
    proba = np.full((len(X), 3), np.nan, np.float32)
    for a, b in GroupKFold(NFOLD).split(X[idx], reg3[idx], g[idx]):
        proba[idx[b]] = _clf(X[idx][a], reg3[idx][a]).predict_proba(X[idx][b])
    proba[tmask] = _clf(X[idx], reg3[idx]).predict_proba(X[tmask])
    out = ann[["cell_id", "year"]].copy()
    out["clf_dry"], out["clf_wet"] = proba[:, 0], proba[:, 2]
    return out


def fit_chunk(tr, ff, init, tpc):
    # warm-start continuation is CPU-only in CatBoost (GPU raises "Training continuation ... not supported")
    m = CatBoostRegressor(iterations=tpc, depth=DEPTH, learning_rate=LR, loss_function="RMSE",
                          random_seed=0, task_type="CPU", verbose=0, allow_writing_files=False)
    m.fit(Pool(prep(tr, ff), tr[TARGET].to_numpy(), cat_features=[ff.index(CAT)]), init_model=init)
    return m


def main():
    t0 = time.time()
    files = sorted(glob.glob(os.path.join(PANEL, f"{REGION}_monthly_*.parquet")))
    if not files:
        allf = glob.glob(os.path.join(PANEL, "*_monthly_*.parquet"))
        regions = sorted(set(os.path.basename(f).split("_monthly_")[0] for f in allf))
        raise SystemExit(f"no parquet for '{REGION}'. Available:\n  " + ", ".join(regions))
    cells = pd.concat([pd.read_parquet(f, columns=["cell_id"]) for f in files], ignore_index=True)["cell_id"].unique()
    np.random.RandomState(SEED).shuffle(cells)
    chunks = [cells[i:i + BATCH_CELLS].tolist() for i in range(0, len(cells), BATCH_CELLS)]
    tpc = max(50, round(TOTAL_TREES / len(chunks)))
    print(f"REGION={REGION} | {len(cells):,} cells -> {len(chunks)} chunks x {BATCH_CELLS} | "
          f"{tpc} trees/chunk (~{tpc*len(chunks)} total) | stage-1 clf={DEVICE}, warm-start reg=CPU", flush=True)

    cols = pqa.ParquetFile(files[0]).schema.names
    feats0 = [c for c in cols if c not in (ML.ID_KEYS + [TARGET] + GEO + REMOVE + [CAT])]
    print("stage-1: streaming regime indicators ...", flush=True)
    ind = indicators(files, chunks, feats0)

    if os.path.exists(TESTPQ):
        os.remove(TESTPQ)
    writer, mb, mr, lagvars = None, None, None, None
    print("stage-2: streaming warm-start training ...", flush=True)
    for ci, ch in enumerate(chunks):
        df = load(files, None, ch)
        df, feats, lagvars = build_feats(df, lagvars)
        df = df.merge(ind, on=["cell_id", "year"], how="left")
        d = df[df[TARGET].notna()]
        tr, te = d[d.year <= 2019], d[d.year >= 2020]
        if len(tr):
            mb = fit_chunk(tr, feats, mb, tpc)
            mr = fit_chunk(tr, feats + ["clf_dry", "clf_wet"], mr, tpc)
        if len(te):
            tt = te[["month", TARGET] + feats + ["clf_dry", "clf_wet"]].copy()
            table = pa.Table.from_pandas(tt, preserve_index=False)
            if writer is None:
                writer = pqa.ParquetWriter(TESTPQ, table.schema)
            writer.write_table(table)
        del df, d, tr, te
        print(f"  chunk {ci+1}/{len(chunks)}  (trees so far: {mb.tree_count_ if mb else 0})", flush=True)
    if writer is not None:
        writer.close()

    print("stage-3: streaming test prediction ...", flush=True)
    pf = pqa.ParquetFile(TESTPQ)
    yt, mt, pb, pr = [], [], [], []
    for batch in pf.iter_batches(batch_size=300000):
        tt = batch.to_pandas()
        yt.append(tt[TARGET].to_numpy()); mt.append(tt["month"].to_numpy())
        pb.append(mb.predict(prep(tt, list(mb.feature_names_))))
        pr.append(mr.predict(prep(tt, list(mr.feature_names_))))
    yte, mte = np.concatenate(yt), np.concatenate(mt)
    pbase, preg = np.concatenate(pb), np.concatenate(pr)
    rb, rc = r2_score(yte, pbase), r2_score(yte, preg)
    print(f"\n  base_full   R2={rb:.4f}\n  +clf_3class R2={rc:.4f}   delta={rc-rb:+.4f}", flush=True)
    for lab, mm in (("NH-monsoon Jul-Nov", [7, 8, 9, 10, 11]), ("other Dec-Jun", [12, 1, 2, 3, 4, 5, 6])):
        msk = np.isin(mte, mm)
        if msk.sum() > 1:
            a, b = r2_score(yte[msk], pbase[msk]), r2_score(yte[msk], preg[msk])
            print(f"  {lab:18s} base {a:6.3f}  +regime {b:6.3f}  ({b-a:+.3f})")
    pd.DataFrame([{"region": REGION, "cells": len(cells), "test_rows": len(yte), "base": rb,
                   "regime": rc, "delta": rc - rb, "mode": "stream-warmstart"}]).to_csv(
        RES_CSV, mode="a", header=not os.path.exists(RES_CSV), index=False)
    try:
        os.remove(TESTPQ)
    except OSError:
        pass
    print(f"\nappended {RES_CSV} | done {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
