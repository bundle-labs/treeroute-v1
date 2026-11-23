"""Ingest NEW ERA5-Land monthly variables (CDS 'reanalysis-era5-land-monthly-means') not already in the panel: potential
evaporation, surface + sub-surface runoff, snowmelt, latent + sensible heat flux, net solar + thermal radiation, 2m
dewpoint, top-layer soil temperature. Monthly-native, GLOBAL 0.1deg, full 2002-2023. Two phases, both resumable:
  DOWNLOAD: one CDS request per variable (all years/months, global) -> D:\\era5land_extra\\{var}.nc  (unzips the CDS .zip)
  INGEST:   per variable, sample each 4km cell per (year,month) -> D:\\era5land_extra_monthly\\{region}_{col}_{year}.parquet

MEMORY-SAFE: a full global 0.1deg var is ~6.8 GB in RAM and there are 10 of them (~68 GB if all held at once -> OOM). So
INGEST processes ONE variable at a time and loads only ONE YEAR (12 monthly slices, ~311 MB) into memory at a time, samples
all regions from that in-memory chunk, writes a per-variable sidecar, then releases it. Peak RAM stays well under 1 GB and
each var's file is read exactly once. Resumable at (variable, year, region) granularity (skips existing sidecars).

Then fold each column into the panel (one pass per column), e.g.:
  py -3.9 presplit_cc/add_evi_to_panel.py --col era5l_pev --src D:\\era5land_extra_monthly --tag era5l_pev
RUN: py -3.9 presplit_cc/ingest_era5land_extra.py [--download-only] [--ingest-only] [--region <name>]
"""
import glob
import os
import sys
import zipfile

import numpy as np
import pandas as pd
import xarray as xr
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
DL = r"D:\era5land_extra"
OUT = r"D:\era5land_extra_monthly"
YEARS = list(range(2002, 2024))
MONTHS = [f"{m:02d}" for m in range(1, 13)]
VARS = {  # CDS variable name : panel column
    "potential_evaporation": "era5l_pev", "surface_runoff": "era5l_sro", "sub_surface_runoff": "era5l_ssro",
    "snowmelt": "era5l_smlt", "surface_latent_heat_flux": "era5l_slhf", "surface_sensible_heat_flux": "era5l_sshf",
    "surface_net_solar_radiation": "era5l_ssr", "surface_net_thermal_radiation": "era5l_str",
    "2m_dewpoint_temperature": "era5l_d2m", "soil_temperature_level_1": "era5l_stl1",
}
ONLY = sys.argv[sys.argv.index("--region") + 1] if "--region" in sys.argv else None


def _masters():
    m = {}
    for d in (cfg["data"]["master_dir"], cfg["forecast"]["regions_dir"]):
        for p in glob.glob(os.path.join(d, "*_master_*.parquet")):
            if ".bak." not in p:
                m.setdefault(os.path.basename(p).split("_master_")[0], p)
    return m


def download():
    import cdsapi
    os.makedirs(DL, exist_ok=True)
    for z in glob.glob(os.path.join(DL, "*.zip")):                  # drop stale partial zips from a killed run
        os.remove(z)
    c = cdsapi.Client()
    for i, (cdsvar, col) in enumerate(VARS.items()):
        ncf = os.path.join(DL, f"{cdsvar}.nc")
        if os.path.exists(ncf):
            print(f"  [{i+1}/{len(VARS)}] {cdsvar}: already downloaded", flush=True); continue
        zf = os.path.join(DL, f"{cdsvar}.zip")
        print(f"  [{i+1}/{len(VARS)}] requesting {cdsvar} (global monthly 2002-2023)...", flush=True)
        c.retrieve("reanalysis-era5-land-monthly-means", {
            "variable": [cdsvar], "year": [str(y) for y in YEARS], "month": MONTHS, "time": "00:00",
            "product_type": "monthly_averaged_reanalysis", "data_format": "netcdf"}, zf)
        with zipfile.ZipFile(zf) as z:                              # CDS wraps the nc in a zip
            inner = [n for n in z.namelist() if n.endswith(".nc")][0]
            z.extract(inner, DL); os.replace(os.path.join(DL, inner), ncf)
        os.remove(zf)
        print(f"       -> {ncf} ({os.path.getsize(ncf)/1e6:.0f} MB)", flush=True)
    print("ERA5LX_DOWNLOAD_DONE", flush=True)


def _cell_cache():
    M = _masters(); regs = sorted(M)
    if ONLY:
        regs = [r for r in regs if r == ONLY]
    return regs, {r: pd.read_parquet(M[r], columns=["cell_id", "lon", "lat"]).drop_duplicates("cell_id")
                  .reset_index(drop=True) for r in regs}


def ingest():
    os.makedirs(OUT, exist_ok=True)
    regs, cache = _cell_cache()
    print(f"ingest: {len(VARS)} vars x {len(regs)} regions (one var, one year in RAM at a time)", flush=True)
    for ci, (cdsvar, col) in enumerate(VARS.items()):
        ncf = os.path.join(DL, f"{cdsvar}.nc")
        if not os.path.exists(ncf):
            raise SystemExit(f"FAIL-LOUD: missing {ncf} -- run --download-only first")
        ds = xr.open_dataset(ncf)                                   # LAZY: nothing loaded yet
        v = [x for x in ds.data_vars][0]; da = ds[v]
        tname = "valid_time" if "valid_time" in da.coords else "time"
        lonn = "longitude" if "longitude" in da.coords else "lon"; latn = "latitude" if "latitude" in da.coords else "lat"
        da = da.rename({tname: "time", lonn: "lon", latn: "lat"})
        lonmax = float(da.lon.max())
        ym2i = {(int(y), int(mm)): i for i, (y, mm) in enumerate(zip(da["time.year"].values, da["time.month"].values))}
        # precompute per-region lon/lat selectors (lon convention depends on this var's grid)
        sel = {r: (xr.DataArray((cache[r].lon.to_numpy() % 360) if lonmax > 180 else cache[r].lon.to_numpy(), dims="c"),
                   xr.DataArray(cache[r].lat.to_numpy(), dims="c")) for r in regs}
        print(f"  [{ci+1}/{len(VARS)}] {col}: {dict(da.sizes)} lon<= {lonmax:.1f}", flush=True)
        for y in YEARS:
            months = [mm for mm in range(1, 13) if (y, mm) in ym2i]
            if not months:
                continue
            todo = [r for r in regs if not os.path.exists(os.path.join(OUT, f"{r}_{col}_{y}.parquet"))]
            if not todo:
                continue
            da_y = da.isel(time=[ym2i[(y, mm)] for mm in months]).load()      # ONE year -> ~311 MB in RAM
            for r in todo:
                cells = cache[r]; lon_da, lat_da = sel[r]
                buf = np.full((len(cells), 12), np.nan, "float32")
                for k, mm in enumerate(months):
                    buf[:, mm - 1] = da_y.isel(time=k).sel(lon=lon_da, lat=lat_da, method="nearest").to_numpy()
                out = pd.DataFrame({"cell_id": np.repeat(cells.cell_id.to_numpy(), 12), "year": y,
                                    "month": np.tile(np.arange(1, 13), len(cells)), col: buf.reshape(-1)})
                outf = os.path.join(OUT, f"{r}_{col}_{y}.parquet")
                out.to_parquet(outf + ".tmp", index=False); os.replace(outf + ".tmp", outf)   # crash-safe
            del da_y
            print(f"      {col} {y}: wrote {len(todo)} regions", flush=True)
        ds.close()
    print("ERA5LX_INGEST_DONE", flush=True)


def main():
    if "--ingest-only" not in sys.argv:
        download()
    if "--download-only" not in sys.argv:
        ingest()


if __name__ == "__main__":
    main()
