"""Ingest ESA-CCI SATELLITE soil moisture (COMBINED v09.2) into the monthly panel. Independent OBSERVED surface soil
moisture (0.25deg daily, volumetric m3/m3), a genuine complement to our MODELED soil moisture (ERA5-Land / TerraClimate).
Direct download from the CEDA archive -- NO registration. COMBINED v09.2 covers 1978-2024 (incl. 2023, so no test-window
gap). Two resumable phases:
  DOWNLOAD  per year, list the CEDA dir + fetch each daily NetCDF -> D:\\esacci_sm\\{year}\\*.nc  (skip existing, retry)
  INGEST    per region, average each month's daily files -> monthly SM, sample onto the 4km cells ->
            D:\\esacci_sm_monthly\\{region}_esaccism_{year}.parquet  (column esacci_sm)
Then fold: py -3.9 presplit_cc/add_evi_to_panel.py --col esacci_sm --src D:\\esacci_sm_monthly --tag esaccism
CRASH-SAFE: per-file/per-region try-except (a bad file/region is logged + skipped, never fatal); resumable (skips done).
PROGRESS: per-year download counts + per-region ingest lines with timing.
RUN: py -3.9 presplit_cc/ingest_esacci_sm.py [--download-only] [--ingest-only] [--region <name>]
"""
import glob
import os
import re
import sys
import time
import urllib.request

import numpy as np
import pandas as pd
import xarray as xr
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
VER = "v09.2"
BASE = f"https://dap.ceda.ac.uk/neodc/esacci/soil_moisture/data/daily_files/COMBINED/{VER}"
DL = r"D:\esacci_sm"
OUT = r"D:\esacci_sm_monthly"
VAR, COL = "sm", "esacci_sm"
YEARS = list(range(2002, 2024))
ONLY = sys.argv[sys.argv.index("--region") + 1] if "--region" in sys.argv else None


def _masters():
    m = {}
    for d in (cfg["data"]["master_dir"], cfg["forecast"]["regions_dir"]):
        for p in glob.glob(os.path.join(d, "*_master_*.parquet")):
            if ".bak." not in p:
                m.setdefault(os.path.basename(p).split("_master_")[0], p)
    return m


def _list_year(year):
    """Parse the CEDA directory listing for that year -> list of daily .nc filenames (robust, no pattern guessing)."""
    try:
        with urllib.request.urlopen(f"{BASE}/{year}/", timeout=60) as r:
            html = r.read().decode("utf-8", "ignore")
    except Exception as e:
        print(f"  !! list {year} failed: {type(e).__name__}: {e}", flush=True); return []
    return sorted(set(re.findall(r"(ESACCI-SOILMOISTURE-\S+?-COMBINED-\d{14}-fv[\d.]+\.nc)", html)))


def download():
    os.makedirs(DL, exist_ok=True)
    for y in YEARS:
        ydir = os.path.join(DL, str(y)); os.makedirs(ydir, exist_ok=True)
        files = _list_year(y)
        if not files:
            print(f"  {y}: no files listed (check {BASE}/{y}/)", flush=True); continue
        got = skip = fail = 0; t0 = time.time()
        for i, fn in enumerate(files):
            dst = os.path.join(ydir, fn)
            if os.path.exists(dst) and os.path.getsize(dst) > 0:
                skip += 1; continue
            for attempt in range(3):
                try:
                    urllib.request.urlretrieve(f"{BASE}/{y}/{fn}", dst + ".part"); os.replace(dst + ".part", dst)
                    got += 1; break
                except Exception as e:
                    if attempt == 2:
                        fail += 1; print(f"  !! {fn}: {type(e).__name__}", flush=True)
                    else:
                        time.sleep(1.5 * (attempt + 1))
            if (i + 1) % 40 == 0:
                print(f"  {y}: [{i+1}/{len(files)}] got {got} skip {skip} fail {fail} ({time.time()-t0:.0f}s)", flush=True)
        print(f"  {y}: DONE got {got} | skip {skip} | fail {fail} of {len(files)} ({time.time()-t0:.0f}s)", flush=True)
    print("ESACCI_SM_DOWNLOAD_DONE", flush=True)


def _month_grid(year, month):
    """Average that month's daily files into one SM grid DataArray (lon,lat); None if no files."""
    pats = os.path.join(DL, str(year), f"*COMBINED-{year}{month:02d}*-fv*.nc")
    fs = sorted(glob.glob(pats))
    if not fs:
        return None
    das = []
    for f in fs:
        try:
            ds = xr.open_dataset(f); da = ds[VAR]
            if "time" in da.dims:
                da = da.isel(time=0)
            das.append(da.load()); ds.close()
        except Exception as e:
            print(f"    !! read {os.path.basename(f)}: {type(e).__name__}", flush=True)
    if not das:
        return None
    return xr.concat(das, dim="d").mean("d", skipna=True)


def ingest():
    os.makedirs(OUT, exist_ok=True)
    M = _masters(); regs = sorted(M)
    if ONLY:
        regs = [r for r in regs if r == ONLY]
    # precompute the 12x22 monthly grids ONCE (shared across all regions) to avoid re-reading 8000 files per region
    print(f"ingest: building monthly grids from daily files ...", flush=True)
    grids = {}; lonname = latname = lonmax = None
    for y in YEARS:
        for mth in range(1, 13):
            g = _month_grid(y, mth)
            if g is not None:
                if lonname is None:
                    lonname = "longitude" if "longitude" in g.coords else "lon"
                    latname = "latitude" if "latitude" in g.coords else "lat"
                    lonmax = float(g[lonname].max())
                grids[(y, mth)] = g.rename({lonname: "lon", latname: "lat"})
        print(f"  grids for {y}: {sum(1 for mm in range(1,13) if (y,mm) in grids)}/12 months", flush=True)
    if not grids:
        raise SystemExit("FAIL-LOUD: no monthly grids built -- run --download-only first")
    for r in regs:
        try:
            cells = pd.read_parquet(M[r], columns=["cell_id", "lon", "lat"]).drop_duplicates("cell_id").reset_index(drop=True)
            lat_da = xr.DataArray(cells.lat.to_numpy(), dims="c")
            lon_da = xr.DataArray((cells.lon.to_numpy() % 360) if (lonmax and lonmax > 180) else cells.lon.to_numpy(), dims="c")
            wrote = 0; t0 = time.time()
            for y in YEARS:
                outf = os.path.join(OUT, f"{r}_esaccism_{y}.parquet")
                if os.path.exists(outf):
                    continue
                buf = np.full((len(cells), 12), np.nan, "float32")
                for mth in range(1, 13):
                    g = grids.get((y, mth))
                    if g is not None:
                        buf[:, mth - 1] = g.sel(lon=lon_da, lat=lat_da, method="nearest").to_numpy()
                pd.DataFrame({"cell_id": np.repeat(cells.cell_id.to_numpy(), 12), "year": y,
                             "month": np.tile(np.arange(1, 13), len(cells)), COL: buf.reshape(-1)}).to_parquet(outf, index=False)
                wrote += 1
            print(f"  {r}: {wrote} year-files ({len(cells)} cells) ({time.time()-t0:.0f}s)", flush=True)
        except Exception as e:
            print(f"  !! {r}: SKIPPED ({type(e).__name__}: {e})", flush=True)
    print("ESACCI_SM_INGEST_DONE", flush=True)


def main():
    if "--ingest-only" not in sys.argv:
        download()
    if "--download-only" not in sys.argv:
        ingest()


if __name__ == "__main__":
    main()
