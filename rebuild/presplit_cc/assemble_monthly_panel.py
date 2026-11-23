"""assemble_monthly_panel.py -- join every monthly tier + carried-forward annual master columns +
global monthly broadcasts into the unified MONTHLY panel: long [cell_id, year, month], 264 rows/cell,
one parquet per region, canonical names. Drops the ~115 redundant seasonal / teleconnection annual
aggregates (month + raw monthly indices encode that signal). Derives V04_precip_seasonality.

DESIGN (locked with the user):
  * monthly-replaceable master cols come ONLY from the monthly tiers (the master's ANNUAL value is
    discarded -- never mixed with monthly); a missing tier -> NaN + a coverage gap, NOT an annual fallback.
  * static / annual-only master cols (topo, soil, human, landcover, livestock) carry forward to all 12 months.
  * global tables (NOAA teleconnections, ERSST SST boxes) broadcast on [year, month].
  * FAIL-LOUD: every one of the 195 master columns must be classified (carry / replace / derive /
    pending / drop) -- an unclassified column aborts (catches schema drift).

  py -3.9 presplit_cc/assemble_monthly_panel.py --regions thar_desert --agera5-dir D:\agera5_ctest --dry
  py -3.9 presplit_cc/assemble_monthly_panel.py --out D:\monthly_panel
"""
import glob
import os
import sys

import numpy as np
import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
MASTER_DIRS = [cfg["data"]["master_dir"], cfg["forecast"]["regions_dir"]]
BUNDLE = cfg["bundle"]["framework_root"]
OUT_DEFAULT = r"D:\monthly_panel"
KEYS = ["cell_id", "year", "month"]

# ---- per-region monthly tiers: dir, file-glob (per-region or per-region-year), raw->canonical ----
# rename {} means columns already carry their canonical names.
TIERS = {
    "terraclimate": dict(dir=r"D:\terraclimate_monthly", glob="{r}_tc_*.parquet", rename={
        "tc_tmean": "V01_mean_temp_C", "tc_dtr": "diurnal_temp_range_C", "tc_precip": "V02_total_precip_mm",
        "tc_ref_et": "V07_total_ref_ET_mm", "tc_aet": "aet_total_mm", "tc_water_deficit": "climate_water_deficit_mm",
        "tc_soil_moisture": "soil_water_tc_mm", "tc_vpd": "V05_mean_vpd_kPa", "tc_wind": "V09_mean_wind_ms",
        "tc_solar": "solar_radiation_Wm2", "tc_swe": "swe_mean_mm", "tc_aridity": "aridity_index_p_pet",
        "tc_vapor_pressure": "tc_vapor_pressure"}),                       # extra (no master col) -- kept
    "spei": dict(dir=r"D:\spei_monthly", glob="{r}_spei.parquet", rename={
        "spei_12m": "V06_spei_12m", "spei_01m": "spei_01m", "spei_03m": "spei_03m",
        "spei_06m": "spei_06m", "spei_24m": "spei_24m"}),                 # 01/03/06/24m extra -- kept
    # scPDSI + SPI 01/03/06/12/24m + EDDI from fetch_env_noauth.py. All seven are EXTRA columns (no master
    # REPLACE). Built for thar 2026-07-30 and complete through 2023-12 at 0.0% NaN, which is why this tier
    # matters: SPEIbase v2.9 stops at 2022-12, so these are the only standardised drought indices that
    # actually cover the 2020-2023 test window (Part 324).
    "drought": dict(dir=r"D:\env_noauth", glob="{r}_drought.parquet", rename={}),
    "ndvi":   dict(dir=r"D:\modis_ndvi_cmg",     glob="{r}_ndvi_*.parquet",   rename={}),
    "evi":    dict(dir=r"D:\modis_evi_cmg",      glob="{r}_evi_*.parquet",    rename={}),  # V12_mean_evi (extra col, not a master REPLACE)
    "landcover": dict(dir=r"D:\modis_landcover_annual", glob="{r}_landcover_*.parquet", rename={}),  # modis_landcover_annual (extra col)
    "grace":  dict(dir=r"D:\grace_monthly",      glob="{r}_grace_*.parquet",  rename={}),  # grace_lwe (extra col; gap months NaN)
    "lst":    dict(dir=r"D:\modis_lst_monthly",  glob="{r}_lst_*.parquet",    rename={}),
    "snow":   dict(dir=r"D:\modis_snow_monthly", glob="{r}_snow_*.parquet",   rename={}),
    "cloud":  dict(dir=r"D:\modis_cloud_monthly", glob="{r}_cloud_*.parquet", rename={}),
    "albedo": dict(dir=r"D:\modis_albedo_monthly", glob="{r}_albedo_*.parquet", rename={}),
    "gpp":    dict(dir=r"D:\gpp_monthly",        glob="{r}_gpp_*.parquet",    rename={}),
    "agera5": dict(dir=r"D:\agera5_daycounts",   glob="{r}_agera5.parquet",   rename={}),  # 11 canonical cols
    "soilm":  dict(dir=r"D:\soil_moisture_monthly", glob="{r}_soilm.parquet", rename={}),  # V30_soil_moisture_pct
    "fire":   dict(dir=r"D:\fire_monthly", glob="{r}_fire.parquet", rename={}),  # V20_burned_binary + burn_doy_mean + burn_month_count
    "snowphen": dict(dir=r"D:\snowphen_monthly", glob="{r}_snowphen_*.parquet", rename={}),  # 4 snow-phenology cols (per-region-year)
}
# ---- global monthly broadcast tables (join on [year, month]) ----
GLOBALS = {
    "ersst": dict(path=os.path.join(BUNDLE, "ersst_sst_boxes_monthly.parquet"), rename={}),  # sst_anom_* canonical
    "noaa":  dict(path=os.path.join(BUNDLE, "noaa_indices_monthly.parquet"), rename={
        k: k for k in ["nino12", "nino3", "nino4", "nino34", "oni", "soi", "tni", "pdo", "amo", "tna",
                       "tsa", "iod", "noi", "ao", "nao", "pna", "wp", "epo", "sam"]}),  # raw monthly index names
}
# ---- master columns that CARRY FORWARD unchanged (static / annual-only; no monthly source) ----
CARRY = ["lon", "lat", "V25_elevation_m", "V26_slope_deg", "V27_southness", "V28_CTI",
         "clay_pct", "sand_pct", "silt_pct", "soil_organic_carbon_gkg", "nitrogen_gkg", "soil_ph",
         "awc_cm3cm3", "bulk_density_gcm3", "cec_cmolkg", "coarse_fragments_pct",
         "V15_bare_ground_pct", "V17_herb_cover_pct", "tree_cover_pct", "modis_landcover_class",
         "shrub_cover_pct_global", "phenology_sos_doy", "population_density", "built_surface_fraction",
         "cropland_fraction",  # OLD 2-snapshot livestock_*_per_km2 REMOVED 2026-07-16 (replaced by annual aglw_*);
         # do NOT re-add -- the coarse GLW-snapshot copy was stripped from the panel by strip_old_livestock.py
         "hand_m", "upstream_area_km2", "irrigation_pct_gmia", "dist_to_coast_km"]
# ---- master columns refilled monthly from a tier (annual master value discarded) ----
REPLACE = ["V01_mean_temp_C", "diurnal_temp_range_C", "V02_total_precip_mm", "V07_total_ref_ET_mm",
           "aet_total_mm", "climate_water_deficit_mm", "soil_water_tc_mm", "V05_mean_vpd_kPa",
           "V09_mean_wind_ms", "solar_radiation_Wm2", "swe_mean_mm", "aridity_index_p_pet", "V06_spei_12m",
           "V11_mean_ndvi", "V13_mean_lst_C", "nighttime_lst_C", "V14_mean_albedo", "snow_cover_fraction",
           "cloud_frequency_pct", "gpp_kgC_m2", "V03_max_daily_precip_mm", "precip_intensity_mm",
           "vpd_max_daily", "vpd_days_gt_2kpa", "vpd_warm_season_mean", "sph_kgkg", "rmin_pct",
           "heatwave_days_gt35C", "frost_days", "gdd5_degC_days", "wet_day_count", "V30_soil_moisture_pct",
           "V20_burned_binary", "burn_doy_mean", "burn_month_count",
           "sst_anom_nino34", "sst_anom_atl3", "sst_anom_iod_west", "sst_anom_iod_east",
           "sst_anom_subpolar_north_atlantic", "sst_anom_coral_sea", "sst_anom_mediterranean",
           "sst_anom_global_tropical_mean",
           "snow_onset_doy", "snow_disappearance_doy", "snow_duration_days", "snow_max_doy"]
DERIVE = ["V04_precip_seasonality"]                                   # computed from monthly V02
PENDING = []                                                         # ALL tiers built -- nothing pending


def _classify_master(mcols):
    """FAIL-LOUD: assign every master column to carry / replace / derive / pending / drop."""
    keys = {"cell_id", "region", "year"}
    # `livestock_*_per_km2` are the OLD 2-snapshot columns, superseded 2026-07-16 by the annual `aglw_*`
    # tier (see the CARRY note). They were removed from CARRY/REPLACE but remain in the master file, so the
    # fail-loud tripped on them and the assembler could not run at all. Classify them as intentionally
    # dropped rather than re-adding them, since `aglw_cattle/buffalo/horse/sheep/goats/total_lsu` are the
    # live replacements and are already in the panel.
    drop = [c for c in mcols if c.endswith(("_DJF", "_MAM", "_JJA", "_SON")) or c.startswith("tier1_")
            or c.startswith("livestock_")]
    known = set(CARRY) | set(REPLACE) | set(DERIVE) | set(PENDING) | set(drop) | keys
    unmapped = [c for c in mcols if c not in known]
    if unmapped:
        raise SystemExit(f"FAIL-LOUD: {len(unmapped)} master cols unclassified -> {unmapped}")
    return drop


def _all_master_files():
    out = {}
    for d in MASTER_DIRS:
        for p in glob.glob(os.path.join(d, "*_master_*.parquet")):
            if ".bak." not in p:
                out.setdefault(os.path.basename(p).split("_master_")[0], p)
    return out


def _load_tier(spec, region, agera5_dir=None):
    d = agera5_dir if (agera5_dir and spec["dir"].endswith("agera5_daycounts")) else spec["dir"]
    fs = sorted(glob.glob(os.path.join(d, spec["glob"].format(r=region))))
    if not fs:
        return None
    df = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    for k in KEYS:
        if k in df.columns:
            df[k] = df[k].astype("int64") if k != "cell_id" else df[k].astype(str)
    if spec["rename"]:
        keep = KEYS + list(spec["rename"])
        df = df[[c for c in keep if c in df.columns]].rename(columns=spec["rename"])
    return df


def _load_global(spec):
    df = pd.read_parquet(spec["path"])
    df["year"] = df["year"].astype("int64"); df["month"] = df["month"].astype("int64")
    if spec["rename"]:
        df = df[["year", "month"] + [c for c in spec["rename"] if c in df.columns]].rename(columns=spec["rename"])
    for c in df.columns:                                            # float32 -> half memory/merge cost
        if df[c].dtype == "float64":
            df[c] = df[c].astype("float32")
    return df


def _derive_precip_seasonality(df):
    """Master's exact definition (feature_definitions.json): CV = stdev(monthly precip)/mean(monthly precip)
    over the 12 months of the cell-year, dimensionless, GEE/population std. (Master sourced CHIRPS; we use
    TerraClimate monthly -- same CV metric.) Broadcast the cell-year CV to all 12 months."""
    p = "V02_total_precip_mm"
    if p not in df.columns:
        df["V04_precip_seasonality"] = np.nan
        return df
    g = df.groupby(["cell_id", "year"])[p]
    cnt = g.transform("count"); m1 = g.transform("mean")
    df["__p2"] = df[p].to_numpy(dtype="float64") ** 2
    m2 = df.groupby(["cell_id", "year"])["__p2"].transform("mean")
    df.drop(columns="__p2", inplace=True)
    std0 = np.sqrt(np.clip(m2 - m1 * m1, 0, None))                 # population std over the year's months
    with np.errstate(invalid="ignore", divide="ignore"):
        cv = np.where((m1 > 1e-6) & (cnt >= 6), std0 / m1, np.nan)
    df["V04_precip_seasonality"] = cv.astype("float32")
    return df


def _load_tier_year(spec, region, year, agera5_dir=None):
    """One YEAR's file for a per-region-year tier (glob '*' -> the year)."""
    d = agera5_dir if (agera5_dir and spec["dir"].endswith("agera5_daycounts")) else spec["dir"]
    path = os.path.join(d, spec["glob"].format(r=region).replace("*", str(year)))
    if not os.path.exists(path):
        return None
    df = pd.read_parquet(path)
    for k in KEYS:
        if k in df.columns:
            df[k] = df[k].astype("int64") if k != "cell_id" else df[k].astype(str)
    if spec["rename"]:
        keep = KEYS + list(spec["rename"])
        df = df[[c for c in keep if c in df.columns]].rename(columns=spec["rename"])
    return df


def assemble_region(region, mpath, out_dir, agera5_dir, years, dry):
    """MEMORY-LIGHT: build + write ONE parquet per region-YEAR (cells x 12 months) so the big full-region
    DataFrame never exists (16GB-safe, ~2-3GB peak). All-years tiers (spei/agera5/soilm/fire) loaded once;
    per-region-year tiers loaded per year. Resumable per region-year. Returns (rows, ncell, nyr, cover, allnan)."""
    import pyarrow.parquet as pq
    avail = set(pq.ParquetFile(mpath).schema.names)                 # load ONLY carry cols (not all 195) -> low memory
    m = pd.read_parquet(mpath, columns=["cell_id", "region", "year"] + [c for c in CARRY if c in avail])
    m["cell_id"] = m["cell_id"].astype(str); m["year"] = m["year"].astype("int64")
    base_all = m.drop_duplicates(["cell_id", "year"])
    for c in base_all.columns:
        if base_all[c].dtype == "float64":
            base_all[c] = base_all[c].astype("float32")
    del m
    months = pd.DataFrame({"month": np.arange(1, 13, dtype="int64")})
    per_year = {n: s for n, s in TIERS.items() if "*" in s["glob"]}
    all_year = {n: _load_tier(s, region, agera5_dir) for n, s in TIERS.items() if "*" not in s["glob"]}
    globs = {n: _load_global(s) for n, s in GLOBALS.items()}
    # WATCHDOG (Part 324): seeded from REPLACE + DERIVE only, this examined 1 of the 5 SPEI columns and
    # never examined `amo`, so SPEI's 100%-missing 2023 and AMO's 11-of-12-missing 2023 both passed
    # silently. `watch` now starts empty and accumulates EVERY column seen, so any all-NaN column is
    # reported regardless of which list it belongs to.
    cover = {}; total = 0; nyr = 0; ncell = base_all["cell_id"].nunique(); allnan = set(REPLACE + DERIVE)
    watch = set(); seen_any = set()
    for year in years:
        outf = os.path.join(out_dir, f"{region}_monthly_{year}.parquet")
        if not dry and os.path.exists(outf):
            nyr += 1; total += ncell * 12; continue
        base_y = base_all[base_all["year"] == year]
        if base_y.empty:
            continue
        panel = base_y.merge(months, how="cross")
        for n, s in per_year.items():
            t = _load_tier_year(s, region, year, agera5_dir)
            if t is not None:
                panel = panel.merge(t, on=KEYS, how="left"); cover[n] = f"{len([c for c in t.columns if c not in KEYS])}c"
        for n, t in all_year.items():
            if t is not None:
                panel = panel.merge(t[t["year"] == year], on=KEYS, how="left"); cover[n] = f"{len([c for c in t.columns if c not in KEYS])}c"
        for n, g in globs.items():
            panel = panel.merge(g[g["year"] == year], on=["year", "month"], how="left")
        panel = _derive_precip_seasonality(panel)
        for c in REPLACE + DERIVE + PENDING:
            if c not in panel.columns:
                panel[c] = np.nan
        allnan -= {c for c in (REPLACE + DERIVE) if c in panel.columns and panel[c].notna().any()}
        watch |= {c for c in panel.columns if c not in ("cell_id", "year", "month", "region")}
        seen_any |= {c for c in panel.columns if panel[c].notna().any()}
        total += len(panel); nyr += 1
        # TerraClimate ocean/edge cells carry the int32 NoData sentinel (-2147483648 = -2**31), which survives
        # the int64->float cast as a finite -2.1e9 and poisons downstream medians (V02_total_precip_mm, swe_mean_mm
        # in 47/133 coastal regions). Scrub it to NaN at write-time so fresh parquets are clean. No real feature
        # reaches 2**31 (largest legit ~2e7 ERA5 fluxes). Read-time imputers guard existing parquets too.
        for c in panel.columns:
            if c not in KEYS and pd.api.types.is_numeric_dtype(panel[c]):
                bad = (panel[c].abs() >= 2**31) | (panel[c] == -32768)   # int32 -2**31 AND int16 -32768 NoData
                if bad.any():
                    panel.loc[bad, c] = np.nan
        if not dry:
            panel.to_parquet(outf, index=False)
        del panel
    dead = sorted(watch - seen_any)
    if dead:
        print(f"  !! ALL-NaN across every year, {len(dead)} column(s): {', '.join(dead)}", flush=True)
    return total, ncell, nyr, cover, sorted(set(allnan) | set(dead))


def main(argv):
    def opt(f, d=None):
        return argv[argv.index(f) + 1] if f in argv else d
    out_dir = opt("--out", OUT_DEFAULT); agera5_dir = opt("--agera5-dir")
    dry = "--dry" in argv
    masters = _all_master_files()
    regs = sorted(masters)
    if opt("--regions"):
        regs = [r for r in regs if r in opt("--regions").split(",")]
    if opt("--limit"):
        regs = regs[:int(opt("--limit"))]
    if opt("--shard"):                                              # by region; assembly is local+independent
        i, n = (int(x) for x in opt("--shard").split("/"))
        regs = [r for k, r in enumerate(regs) if k % n == i]
    # classify master schema once (fail-loud)
    m0 = pd.read_parquet(next(iter(masters.values())), columns=None)
    drop = _classify_master(list(m0.columns))
    print(f"master schema OK: {len(m0.columns)} cols -> carry {len(CARRY)} | replace {len(REPLACE)} | "
          f"derive {len(DERIVE)} | pending {len(PENDING)} | drop {len(drop)}")
    if not dry:
        os.makedirs(out_dir, exist_ok=True)
    print(f"{'DRY-RUN' if dry else 'ASSEMBLE'} {len(regs)} region(s) -> {out_dir}\n")
    years = list(range(cfg["data"]["first_data_year"], cfg["data"]["last_data_year"] + 1))
    for r in regs:
        total, ncell, nyr, cover, miss = assemble_region(r, masters[r], out_dir, agera5_dir, years, dry)
        exp = ncell * nyr * 12
        flag = "OK" if total == exp else f"!! rows {total} != {exp}"
        print(f"[{r}] rows={total} ({flag}) cells={ncell} yrs={nyr}  ({'DRY' if dry else 'wrote ' + str(nyr) + ' year-files'})")
        print("   coverage: " + "  ".join(f"{k}={v}" for k, v in cover.items()))
        if miss:
            print(f"   all-NaN replace/derive cols: {miss}")
    print("\ndone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
