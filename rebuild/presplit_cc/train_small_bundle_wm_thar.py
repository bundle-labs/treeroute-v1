"""Small TIME-AWARE bundle, NO-LEAK + LAG + ROLLWATER + WATER-MEMORY edition (290 feats = 94 no-leak +
168 backward lags + 19 rolling/cumulative water + 9 water-memory [API ewm, water-year-cumulative for all
water fluxes, dry-spell counters]). All strictly backward, genuine drivers only (no NDVI/proxy). 10 regions
x {1,4,12} specialists, route on thar. Then run cross_approach_router.py (includes this bundle).
Crash-safe/resumable: models cached at D:\\small_bundle_wm_models\\<region>\\<name>.cbm.

RUN (multi-hour, GPU; in YOUR terminal; resumes if killed):
  py -3.9 presplit_cc/train_small_bundle_wm_thar.py
"""
import glob
import os
import sys
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from catboost import CatBoostRegressor, Pool
from sklearn.metrics import mean_squared_error, r2_score

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import monthly_loader as ML  # noqa: E402

PICK10 = ["chihuahuan_desert", "mojave_desert", "kalahari_woodland", "taimyr_peninsula", "yamal_peninsula",
          "argentine_monte", "sahel", "mongolian_steppe", "great_sandy_desert_au", "central_chile"]
PANEL, TARGET, CAT, GEO = ML.PANEL_DIR, ML.TARGET, "modis_landcover_class", ["lon", "lat"]
REMOVE = ["V14_mean_albedo", "V13_mean_lst_C", "nighttime_lst_C", "gpp_kgC_m2", "V15_bare_ground_pct",
          "V17_herb_cover_pct", "tree_cover_pct", "shrub_cover_pct_global", "phenology_sos_doy"]
WATERVARS = ["V02_total_precip_mm", "soil_water_tc_mm", "V30_soil_moisture_pct", "V07_total_ref_ET_mm",
             "aet_total_mm", "climate_water_deficit_mm"]
WMCUMVARS = ["soil_water_tc_mm", "V30_soil_moisture_pct", "V07_total_ref_ET_mm", "aet_total_mm", "climate_water_deficit_mm"]
WINDOWS, LAGS, PRECIP = [3, 6, 12], [1, 2, 3], "V02_total_precip_mm"
ITERS, DEPTH, LR, ALPHA, MAXCELLS = 800, 8, 0.05, 0.01, 8000
MD = r"D:\small_bundle_wm_models"
os.makedirs(MD, exist_ok=True)
USE_GPU = "--cpu" not in sys.argv
SEASONS = {"winter_DJF": [12, 1, 2], "spring_MAM": [3, 4, 5], "summer_JJA": [6, 7, 8], "autumn_SON": [9, 10, 11]}


def rfiles(r):
    return sorted(glob.glob(os.path.join(PANEL, f"{r}_monthly_*.parquet")))


def base_feats():
    cols = pq.ParquetFile(rfiles("thar_desert")[0]).schema.names
    return [c for c in cols if c not in (ML.ID_KEYS + [TARGET] + GEO + REMOVE)]


def detect_lagvars(feats94):
    files = rfiles("thar_desert")
    need = ["cell_id", "year", "month"] + [f for f in feats94 if f != CAT]
    samp = pd.concat([b.to_pandas() for b in pq.ParquetFile(files[len(files) // 2]).iter_batches(columns=need, batch_size=300000)], ignore_index=True)
    samp = samp[samp.cell_id.isin(pd.unique(samp.cell_id)[:120])]
    num = [f for f in feats94 if f != CAT]
    return [f for f in num if samp.groupby(["cell_id", "year"])[f].nunique().median() > 1]


def load_region_wm(r, feats94, lagvars, feats_wm):
    files = rfiles(r)
    allc = pd.unique(pq.read_table(files[len(files) // 2], columns=["cell_id"]).column(0).to_numpy())
    rng = np.random.RandomState(0)
    keep = set(allc.tolist() if len(allc) <= MAXCELLS else rng.choice(allc, MAXCELLS, replace=False).tolist())
    parts = []
    for f in files:
        for b in pq.ParquetFile(f).iter_batches(columns=ML.ID_KEYS + [TARGET] + feats94, batch_size=300000):
            d = b.to_pandas(); d = d[d["cell_id"].isin(keep)]
            if len(d):
                parts.append(d)
    df = pd.concat(parts, ignore_index=True)
    df[lagvars] = df[lagvars].astype("float32")
    df["t"] = (df.year - 2002) * 12 + (df.month - 1)
    for k in LAGS:                                                       # backward lags
        ren = {v: f"{v}_lag{k}" for v in lagvars}
        df = df.merge(df[["cell_id", "t"] + lagvars].rename(columns=ren).assign(t=lambda x: x.t + k), on=["cell_id", "t"], how="left")
    df = df.sort_values(["cell_id", "t"]).reset_index(drop=True)
    for v in WATERVARS:                                                  # rolling water
        gv = df.groupby("cell_id", sort=False)[v]
        for w in WINDOWS:
            df[f"{v}_roll{w}"] = gv.rolling(w, min_periods=1).mean().to_numpy().astype("float32")
    df["wy"] = df.year - (df.month < 6).astype(int)
    df["precip_wytd"] = df.groupby(["cell_id", "wy"], sort=False)[PRECIP].cumsum().astype("float32")
    df["api_precip"] = df.groupby("cell_id")[PRECIP].ewm(alpha=0.1, adjust=False).mean().reset_index(level=0, drop=True).astype("float32")
    df["api_soilmoist"] = df.groupby("cell_id")["V30_soil_moisture_pct"].ewm(alpha=0.1, adjust=False).mean().reset_index(level=0, drop=True).astype("float32")
    for v in WMCUMVARS:                                                  # water-year cumulative for all fluxes
        df[f"{v}_wytd"] = df.groupby(["cell_id", "wy"], sort=False)[v].cumsum().astype("float32")
    w10 = (df[PRECIP] >= 10).astype(int); g1 = w10.groupby(df.cell_id).cumsum()
    df["consec_dry_months"] = (1 - w10).groupby([df.cell_id, g1]).cumsum().astype("float32")
    s30 = (df[PRECIP] >= 30).astype(int); g2 = s30.groupby(df.cell_id).cumsum()
    df["months_since_sig_rain"] = (1 - s30).groupby([df.cell_id, g2]).cumsum().astype("float32")
    for c in feats_wm:
        if c != CAT and df[c].dtype == "float64":
            df[c] = df[c].astype("float32")
    return df[df[TARGET].notna()].reset_index(drop=True)


def feature_list(feats94, lagvars):
    lagcols = [f"{v}_lag{k}" for k in LAGS for v in lagvars]
    rollcols = [f"{v}_roll{w}" for v in WATERVARS for w in WINDOWS] + ["precip_wytd"]
    wmcols = ["api_precip", "api_soilmoist"] + [f"{v}_wytd" for v in WMCUMVARS] + ["consec_dry_months", "months_since_sig_rain"]
    return feats94 + lagcols + rollcols + wmcols


def main():
    t0 = time.time()
    feats94 = base_feats()
    lagvars = detect_lagvars(feats94)
    feats_wm = feature_list(feats94, lagvars)
    cat_idx = [feats_wm.index(CAT)]
    print(f"{len(PICK10)} regions | 94 + {len(LAGS)*len(lagvars)} lags + 19 rollwater + 9 water-memory = {len(feats_wm)} feats "
          f"| {'GPU' if USE_GPU else 'CPU'} {ITERS} trees", flush=True)
    names = ["all"] + [f"S_{s}" for s in SEASONS] + [f"m{m:02d}" for m in range(1, 13)]

    for r in PICK10:
        rdir = os.path.join(MD, r); os.makedirs(rdir, exist_ok=True)
        if all(os.path.exists(os.path.join(rdir, f"{n}.cbm")) for n in names):
            print(f"  {r}: 17/17 cached -> skip", flush=True); continue
        df = load_region_wm(r, feats94, lagvars, feats_wm)
        df[CAT] = df[CAT].fillna(-1).round().astype("int32").astype("string")

        def ts(sub, name):
            out = os.path.join(rdir, f"{name}.cbm")
            if os.path.exists(out) or len(sub) < 50:
                return

            def fit(dev):
                m = CatBoostRegressor(iterations=ITERS, depth=DEPTH, learning_rate=LR, loss_function="RMSE",
                                      random_seed=0, task_type=dev, verbose=0, allow_writing_files=False)
                m.fit(Pool(sub[feats_wm], sub[TARGET].to_numpy(), cat_features=cat_idx)); return m
            try:
                m = fit("GPU" if USE_GPU else "CPU")
            except Exception as e:
                print(f"    GPU fail {r}/{name} ({str(e)[:30]}) -> CPU"); m = fit("CPU")
            m.save_model(out); print(f"    {r}/{name} ({len(sub):,} rows)", flush=True)
        ts(df, "all")
        for s, ms in SEASONS.items():
            ts(df[df.month.isin(ms)], f"S_{s}")
        for mm in range(1, 13):
            ts(df[df.month == mm], f"m{mm:02d}")
        print(f"  {r}: {len(df):,} rows -> models ({time.time()-t0:.0f}s)", flush=True)
        del df

    print("\nbuilding thar (no-leak+lag+rollwater+water-memory) ...", flush=True)
    thar = load_region_wm("thar_desert", feats94, lagvars, feats_wm)
    thar[CAT] = thar[CAT].fillna(-1).round().astype("int32").astype("string")
    Xt = thar[feats_wm]
    y = thar[TARGET].to_numpy(np.float64); month = thar.month.to_numpy()
    cal = thar.year.to_numpy() <= 2019; tst = thar.year.to_numpy() >= 2020
    M2S = {mm: s for s, ms in SEASONS.items() for mm in ms}

    def load(r, name):
        p = os.path.join(MD, r, f"{name}.cbm")
        return CatBoostRegressor().load_model(p) if os.path.exists(p) else None

    def best(r, mm, mode):
        if mode == "1model":
            return load(r, "all")
        if mode == "4seasonal":
            return load(r, f"S_{M2S[mm]}") or load(r, "all")
        return load(r, f"m{mm:02d}") or load(r, f"S_{M2S[mm]}") or load(r, "all")

    def build_P(mode):
        P = np.zeros((len(thar), len(PICK10)))
        for j, r in enumerate(PICK10):
            if mode == "1model":
                P[:, j] = load(r, "all").predict(Pool(Xt, cat_features=cat_idx))
            else:
                for mm in range(1, 13):
                    m = month == mm
                    P[m, j] = best(r, mm, mode).predict(Pool(Xt[m], cat_features=cat_idx))
        return P

    groups = thar.groupby("cell_id").indices

    def route(P):
        I = ALPHA * np.eye(P.shape[1]); pred = np.full(len(thar), np.nan)
        for c, idx in groups.items():
            idx = np.asarray(idx); ci = idx[cal[idx]]
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

    print("\n==== SMALL BUNDLE no-leak+lag+rollwater+WATER-MEMORY (10 regions) -> thar, single-approach ====")
    print("   (compare: roll bundle 1model 0.7533/xappr 0.7817 | in-region water-memory 0.7864; then run cross_approach_router.py)")
    for mode, nmod in [("1model", 10), ("4seasonal", 40), ("12monthly", 120)]:
        pred = route(build_P(mode))
        v = tst & np.isfinite(pred)
        print(f"  {mode:11s} ({nmod:3d} models): R2={r2_score(y[v], pred[v]):.4f}  RMSE={np.sqrt(mean_squared_error(y[v], pred[v])):.4f}", flush=True)
    print(f"\ndone in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
