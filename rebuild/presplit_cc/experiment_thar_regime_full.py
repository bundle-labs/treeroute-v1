"""DOES THE REGIME FEATURE STACK ON THE FULL WATER-ENGINEERED SET, OR IS IT REDUNDANT?
Rebuilds the exact 290-feature no-leak set (feats94 + lag1/2/3 + rollwater + water-memory, identical to
experiment_thar_watermem.py), then trains a SINGLE CatBoost (train 2002-2019, test 2020-2023) and adds
the winning regime indicators from experiment_thar_drought_regime.py's cache:
   base_full            : the 290 feats alone
   + clf_3class         : + P(dry), P(wet)   [the Exp-1 winner, +0.029 on the plain base]
   + clf_drought        : + P(drought)
KEY QUESTION: Exp-1 showed +0.029 on the PLAIN 93 feats, but the oracle on plain feats (0.7897) already
~matched the 0.786 full-set plateau -- i.e. regime and water-history overlap. If the delta here is much
smaller than +0.029, they were redundant. If it holds, we have a new leakage-free best.
Leakage-free: indicators are feature-derived + out-of-fold (see the drought-regime script). Crash-safe:
caches each single model, appends results CSV.
RUN: py -3.9 presplit_cc/experiment_thar_regime_full.py   (add --cpu to force CPU)
"""
import glob
import os
import sys
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from catboost import CatBoostRegressor, Pool
from sklearn.metrics import r2_score

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import monthly_loader as ML  # noqa: E402

REGION, PANEL, TARGET, CAT, GEO = "thar_desert", ML.PANEL_DIR, ML.TARGET, "modis_landcover_class", ["lon", "lat"]
REMOVE = ["V14_mean_albedo", "V13_mean_lst_C", "nighttime_lst_C", "gpp_kgC_m2", "V15_bare_ground_pct",
          "V17_herb_cover_pct", "tree_cover_pct", "shrub_cover_pct_global", "phenology_sos_doy",
          "V12_mean_evi", "modis_landcover_annual"]   # EVI ~0.9 corr w/ NDVI target => a leak if used as a feature; new annual
#         landcover excluded by DEFAULT so it never silently contaminates honest NDVI runs -- re-included only for the deliberate recoverability test.
WATERVARS = ["V02_total_precip_mm", "soil_water_tc_mm", "V30_soil_moisture_pct", "V07_total_ref_ET_mm",
             "aet_total_mm", "climate_water_deficit_mm"]
WINDOWS = [3, 6, 12]
PRECIP = "V02_total_precip_mm"
IND_CACHE = r"D:\thar_drought_ann_indicators.parquet"
MD, RES_CSV = r"D:\thar_regime_full_models", r"D:\thar_regime_full.csv"
ITERS, DEPTH, LR = 800, 8, 0.05
USE_GPU = "--cpu" not in sys.argv
MN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def build_feats(df):
    cols = df.columns
    feats94 = [c for c in cols if c not in (ML.ID_KEYS + [TARGET] + GEO + REMOVE)]
    df["t"] = (df.year - 2002) * 12 + (df.month - 1)
    num = [f for f in feats94 if f != CAT]
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
            df[f"{v}_roll{w}"] = gv.rolling(w, min_periods=1).mean().to_numpy()
            feats.append(f"{v}_roll{w}")
    df["wy"] = df.year - (df.month < 6).astype(int)
    df["precip_wytd"] = df.groupby(["cell_id", "wy"], sort=False)[PRECIP].cumsum()
    feats.append("precip_wytd")
    df["api_precip"] = df.groupby("cell_id")[PRECIP].ewm(alpha=0.1, adjust=False).mean().reset_index(level=0, drop=True)
    df["api_soilmoist"] = df.groupby("cell_id")["V30_soil_moisture_pct"].ewm(alpha=0.1, adjust=False).mean().reset_index(level=0, drop=True)
    feats += ["api_precip", "api_soilmoist"]
    for v in ["soil_water_tc_mm", "V30_soil_moisture_pct", "V07_total_ref_ET_mm", "aet_total_mm", "climate_water_deficit_mm"]:
        df[f"{v}_wytd"] = df.groupby(["cell_id", "wy"], sort=False)[v].cumsum()
        feats.append(f"{v}_wytd")
    wet10 = (df[PRECIP] >= 10).astype(int); g1 = wet10.groupby(df.cell_id).cumsum()
    df["consec_dry_months"] = (1 - wet10).groupby([df.cell_id, g1]).cumsum()
    sig30 = (df[PRECIP] >= 30).astype(int); g2 = sig30.groupby(df.cell_id).cumsum()
    df["months_since_sig_rain"] = (1 - sig30).groupby([df.cell_id, g2]).cumsum()
    feats += ["consec_dry_months", "months_since_sig_rain"]
    return df, feats


def main():
    t0 = time.time()
    os.makedirs(MD, exist_ok=True)
    files = sorted(glob.glob(os.path.join(PANEL, f"{REGION}_monthly_*.parquet")))
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    df, feats = build_feats(df)
    ind = pd.read_parquet(IND_CACHE)
    df = df.merge(ind[["cell_id", "year", "clf_drought", "clf_dry", "clf_wet"]], on=["cell_id", "year"], how="left")
    print(f"full feats: {len(feats)} | merged regime indicators", flush=True)

    d = df[df[TARGET].notna()].reset_index(drop=True)
    tr, te = d[d.year <= 2019], d[d.year >= 2020]

    def prep(dd, ff):
        X = dd[ff].copy()
        X[CAT] = X[CAT].fillna(-1).round().astype("int32").astype("string")
        return X

    def fit_predict(extra, tag):
        ff = feats + extra
        cache = os.path.join(MD, f"{tag}.cbm")
        m = CatBoostRegressor()
        if os.path.exists(cache):
            m.load_model(cache)
        else:
            ci = [ff.index(CAT)]

            def fit(dev):
                mdl = CatBoostRegressor(iterations=ITERS, depth=DEPTH, learning_rate=LR, loss_function="RMSE",
                                        random_seed=0, task_type=dev, verbose=0, allow_writing_files=False)
                mdl.fit(Pool(prep(tr, ff), tr[TARGET].to_numpy(), cat_features=ci)); return mdl
            try:
                m = fit("GPU" if USE_GPU else "CPU")
            except Exception:
                m = fit("CPU")
            m.save_model(cache)
        p = m.predict(prep(te, ff))
        return p

    VARIANTS = {"base_full": [], "clf_3class": ["clf_dry", "clf_wet"], "clf_drought": ["clf_drought"]}
    done = set()
    if os.path.exists(RES_CSV):
        done = set(pd.read_csv(RES_CSV)["variant"])
    yte, mte = te[TARGET].to_numpy(), te.month.to_numpy()
    preds, rows = {}, []
    base = None
    for tag, extra in VARIANTS.items():
        p = fit_predict(extra, tag)
        preds[tag] = p
        r2 = r2_score(yte, p)
        if tag == "base_full":
            base = r2
        rows.append({"variant": tag, "n_feats": len(feats) + len(extra), "r2": r2})
        if tag not in done:
            pd.DataFrame([rows[-1]]).to_csv(RES_CSV, mode="a" if done or len(rows) > 1 else "w",
                                            header=not (done or len(rows) > 1), index=False)
        print(f"  {tag:12s} R2={r2:.4f}" + (f"  delta_vs_base={r2-base:+.4f}" if base is not None else ""), flush=True)

    # where does the winner help? monsoon vs dry season
    win = "clf_3class" if r2_score(yte, preds["clf_3class"]) >= r2_score(yte, preds["clf_drought"]) else "clf_drought"
    print(f"\nseasonal breakdown  base_full vs +{win}:")
    for lab, mm in (("DRY Jan-Jun", [1, 2, 3, 4, 5, 6]), ("MONSOON Jul-Nov", [7, 8, 9, 10, 11])):
        msk = np.isin(mte, mm)
        a, b = r2_score(yte[msk], preds["base_full"][msk]), r2_score(yte[msk], preds[win][msk])
        print(f"  {lab:16s} base {a:6.3f}  +{win} {b:6.3f}  ({b-a:+.3f})")
    print(f"\nresults -> {RES_CSV} | plateau ref: 12-monthly watermem 0.786 | done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
