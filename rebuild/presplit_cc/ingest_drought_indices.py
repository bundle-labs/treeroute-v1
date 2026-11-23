"""Ingest the DROUGHT-INDEX group (deep-research pass-2, first PRIORITY group) onto the 4km cells ->
per-region monthly parquet [cell_id, year, month, <cols>]. Three clean, no-auth, direct-download sources that
complement the panel's existing SPEI (the panel has SPEI 1-24 but NO Palmer index, NO evaporative-DEMAND index):

  scPDSI  (Palmer self-calibrating drought index, CRU TS 4.09)  -> col 'scpdsi'
          single global 0.5deg NetCDF, monthly, open HTTP (crudata.uea.ac.uk)
  SPI     (Standardized Precipitation Index, GPCC gamma, multi-timescale) -> cols 'spi_01m..spi_24m'
          one 1.0deg NetCDF per timescale, monthly, open HTTPS (ncei.noaa.gov/pub/nidis/gpcc)
  EDDI    (Evaporative Demand Drought Index, NCEP stream) -> col 'eddi'
          0.125deg ESRI-ASCII grid, ONE FILE PER MONTH, open HTTP (downloads.psl.noaa.gov); NCEP stream = the
          only one covering all 2002-2023 homogeneously (do NOT splice with the MERRA-2 'data/' stream).

Sampling = each 4km cell takes its containing grid cell (validated grid_indices, same as SPEI). Ocean/fill -> NaN.
CRASH-SAFE: downloaded files kept (re-run resumes for free); per-source var-name auto-detected; per-region parquet.
Because I can't verify the exact NetCDF variable names / EDDI url dates without fetching, RUN --probe FIRST.
  py -3.9 presplit_cc/ingest_drought_indices.py --selftest                    # geometry only, no data
  py -3.9 presplit_cc/ingest_drought_indices.py --probe                       # discover + inspect 1 file per source
  py -3.9 presplit_cc/ingest_drought_indices.py --only scpdsi --region thar_desert   # one-source/region test
  py -3.9 presplit_cc/ingest_drought_indices.py                               # full: scpdsi + spi{1,3,6,12,24} + eddi
Then fold into the monthly panel with the standard folder (join on [cell_id, year, month]).

ALL 133 REGIONS (2026-07-31). The 2026-07-15 run covered only 22 regions (the alphabetically-first 21 plus
thar_desert), so 111 regions have no drought parquet. `--nbatch/--batch` splits the region list into CELL-BALANCED
groups because `_sample_nc` holds one (ncell, 264) float32 buffer per region simultaneously -- all 133 at once is
2.42 GB, which will not sit next to a training job. `--region` now also accepts a comma-separated list.
Per-column sidecars make every batch resumable for free.

  py -3.9 presplit_cc/ingest_drought_indices.py --out D:\env_noauth --tmp D:\env_noauth_dl --nbatch 7 --batch 0
"""
import calendar
import glob
import os
import sys
import tempfile
import time

import numpy as np
import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ingest_luh3_drivers import grid_indices  # noqa: E402  reuse the validated containing-cell geometry

cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
CC = "cell_id"
YEARS = list(range(2002, 2024))
TARGET = [(y, m) for y in YEARS for m in range(1, 13)]      # 264 (year, month), in order
NMON = len(TARGET)

SCPDSI_URL = ("https://crudata.uea.ac.uk/cru/data/drought/"
              "scPDSI.cru_ts4.09early1.1901.2024.cal_1901_24.bams.2025.GLOBAL.IGBP.WHC.1901.2024.nc")
SPI_SCALES = [1, 3, 6, 12, 24]
SPI_URL = "https://www.ncei.noaa.gov/pub/data/nidis/gpcc/spi-gamma/gpcc-spi-gamma-{ts:02d}.nc"
EDDI_URL = "https://downloads.psl.noaa.gov/Projects/EDDI/global_archive/NCEP/{y}/EDDI_01mn_{ymd}.asc"


def _download(url, path, retries=5, minbytes=1_000_000):
    """Stream-download with resume-on-rerun (kept file) + retries + atomic replace."""
    import requests
    if os.path.exists(path) and os.path.getsize(path) >= minbytes:
        return path
    last = None
    for a in range(retries):
        try:
            part = path + ".part"
            with requests.get(url, stream=True, timeout=1800) as r:
                r.raise_for_status()
                with open(part, "wb") as fh:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        fh.write(chunk)
            os.replace(part, path)
            return path
        except Exception as e:
            last = e
            for p in (path, path + ".part"):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
            time.sleep(3 * (a + 1))
    raise last


def _nc_open(path):
    from netCDF4 import Dataset
    return Dataset(path)


def _timemap(nc):
    from netCDF4 import num2date
    t = nc.variables["time"]
    dates = num2date(t[:], t.units, getattr(t, "calendar", "standard"))
    return {(d.year, d.month): i for i, d in enumerate(dates)}


def _var3d(nc, prefer):
    for p in prefer:
        if p in nc.variables:
            return p
    return [v for v in nc.variables if nc.variables[v].ndim == 3][0]


def _latlon(nc):
    la = "lat" if "lat" in nc.variables else "latitude"
    lo = "lon" if "lon" in nc.variables else "longitude"
    return np.asarray(nc.variables[la][:]), np.asarray(nc.variables[lo][:])


def _selftest():
    glon = -179.75 + 0.5 * np.arange(720); glat = 89.75 - 0.5 * np.arange(360)
    ok = all(abs(glon[grid_indices([lo], [la], glon, glat)[0][0]] - lo) <= 0.25 + 1e-9
             and abs(glat[grid_indices([lo], [la], glon, glat)[1][0]] - la) <= 0.25 + 1e-9
             for lo, la in [(-64.98, -5.01), (0, 0), (115.3, 42.7), (72.5, 27.0)])
    print("selftest:", "PASS" if ok else "FAIL"); return 0 if ok else 1


def _batches(counts, nbatch):
    """Split regions into `nbatch` CELL-BALANCED groups (largest-first, always into the lightest batch).

    Memory is what forces this. `_sample_nc` holds one (ncell, 264) float32 buffer for EVERY region in the
    invocation at once; across all 133 regions that is 2.29M cells -> 2.42 GB, which will not fit next to a
    training job on a 15.8 GB box. Balancing by cell count (not by name) keeps every batch's peak near
    total/nbatch instead of letting yakutia_larch + siberian_taiga land together."""
    load = [0] * nbatch
    out = [[] for _ in range(nbatch)]
    for n, r in sorted(((c, r) for r, c in counts.items()), reverse=True):
        k = min(range(nbatch), key=lambda i: load[i])
        load[k] += n
        out[k].append(r)
    return [sorted(b) for b in out], load


def _regions(only, limit, batch=None, nbatch=None):
    masters = {}
    for d in (cfg["data"]["master_dir"], cfg["forecast"]["regions_dir"]):
        for p in glob.glob(os.path.join(d, "*_master_*.parquet")):
            if ".bak." not in p:
                masters.setdefault(os.path.basename(p).split("_master_")[0], p)
    regs = sorted(masters)
    if only:
        want = set(only.split(","))
        regs = [r for r in regs if r in want]
    if limit:
        regs = regs[:int(limit)]
    cells = {r: pd.read_parquet(masters[r], columns=[CC, "lon", "lat"]).drop_duplicates(CC) for r in regs}
    if nbatch:
        nb = int(nbatch)
        groups, load = _batches({r: len(cells[r]) for r in regs}, nb)
        print("  cell-balanced batches of %d: %s" % (nb, ", ".join(f"{n:,}" for n in load)), flush=True)
        regs = groups[int(batch)]
        cells = {r: cells[r] for r in regs}
        print("  --batch %s/%s -> %d regions, %d cells (peak buffer %.2f GB)"
              % (batch, nb, len(regs), load[int(batch)], load[int(batch)] * NMON * 4 / 1e9), flush=True)
    return regs, cells


def _sample_nc(path, prefer, cells, regs, idx_cache):
    """Sample one monthly NetCDF onto all regions -> {region: (ncell, 264)}."""
    nc = _nc_open(path); glat, glon = _latlon(nc); tm = _timemap(nc); var = nc.variables[_var3d(nc, prefer)]
    gkey = (int(np.shape(glat)[0]), int(np.shape(glon)[0]))         # cache indices PER GRID (scPDSI 0.5deg != SPI 1.0deg)
    lon0360 = float(np.nanmax(glon)) > 180.0                         # SPI is 0-360; shift W-hemisphere cell lons to match
    if gkey not in idx_cache:
        idx_cache[gkey] = {}
        for r in regs:
            clon = cells[r]["lon"].to_numpy()
            if lon0360:
                clon = np.where(clon < 0, clon + 360.0, clon)
            il, ia = grid_indices(clon, cells[r]["lat"].to_numpy(), glon, glat)
            idx_cache[gkey][r] = (ia, il)
    idx = idx_cache[gkey]
    out = {r: np.full((len(cells[r]), NMON), np.nan, "float32") for r in regs}
    for j, (y, m) in enumerate(TARGET):
        ti = tm.get((y, m))
        if ti is None:
            continue
        arr = np.ma.filled(var[ti, :, :], np.nan).astype("float32")
        arr = np.where(np.abs(arr) < 1e4, arr, np.nan)                 # kill 1e30 ocean fill
        for r in regs:
            ia, il = idx[r]; out[r][:, j] = arr[ia, il]
    nc.close(); return out


def _sample_asc(path, cells, regs):
    """Sample one EDDI .asc (0.125deg global) onto all regions via rasterio rowcol."""
    import rasterio
    with rasterio.open(path) as s:
        arr = s.read(1).astype("float32"); tr = s.transform; nod = s.nodata
    if nod is not None:
        arr = np.where(arr == nod, np.nan, arr)
    out = {}
    for r in regs:
        lons = cells[r]["lon"].to_numpy(); lats = cells[r]["lat"].to_numpy()
        rows, cols = rasterio.transform.rowcol(tr, lons, lats)
        rows = np.asarray(rows); cols = np.asarray(cols); h, w = arr.shape
        ok = (rows >= 0) & (rows < h) & (cols >= 0) & (cols < w)
        v = np.full(len(lons), np.nan, "float32"); v[ok] = arr[rows[ok], cols[ok]]
        out[r] = v
    return out


def _probe(tmp):
    p = _download(SCPDSI_URL, os.path.join(tmp, "scpdsi.nc"))
    nc = _nc_open(p); tm = _timemap(nc)
    print("scPDSI vars:", list(nc.variables), "| 3d:", _var3d(nc, ["scpdsi", "sc_PDSI_pm", "sc_PDSI"]),
          "| 2002-01..2023-12?", (2002, 1) in tm and (2023, 12) in tm); nc.close()
    p = _download(SPI_URL.format(ts=12), os.path.join(tmp, "spi12.nc"))
    nc = _nc_open(p); tm = _timemap(nc)
    print("SPI-12 vars:", list(nc.variables), "| 3d:", _var3d(nc, ["spi", "spi_gamma_12"]),
          "| 2002-01..2023-12?", (2002, 1) in tm and (2023, 12) in tm); nc.close()
    ymd = f"2023{12:02d}{calendar.monthrange(2023, 12)[1]:02d}"
    p = _download(EDDI_URL.format(y=2023, ymd=ymd), os.path.join(tmp, "eddi_test.asc"))
    import rasterio
    with rasterio.open(p) as s:
        print(f"EDDI .asc: shape {s.shape} | bounds {tuple(round(b, 2) for b in s.bounds)} | nodata {s.nodata}")
    print("probe: PASS"); return 0


def main(argv):
    if "--selftest" in argv:
        return _selftest()

    def opt(f, d=None):
        return argv[argv.index(f) + 1] if f in argv else d
    tmp = opt("--tmp", os.path.join(r"D:\drought_dl")); os.makedirs(tmp, exist_ok=True)
    if "--probe" in argv:
        return _probe(tmp)
    only_src = opt("--only")
    regs, cells = _regions(opt("--region"), opt("--limit"), opt("--batch"), opt("--nbatch"))
    out_dir = opt("--out", r"D:\drought_monthly"); os.makedirs(out_dir, exist_ok=True)
    do = (lambda s: (only_src is None) or (only_src == s))
    idxc = {}
    yrs = np.array([y for y, m in TARGET]); mos = np.array([m for y, m in TARGET])
    print(f"DROUGHT indices -> {len(regs)} regions, 264 months (only={only_src or 'all'})", flush=True)

    def write_col(col, samp):                                          # MEMORY-SAFE: per-region single-col sidecar, then free
        for r in regs:
            nc_ = len(cells[r])
            pd.DataFrame({CC: np.repeat(cells[r][CC].to_numpy(), NMON), "year": np.tile(yrs, nc_),
                          "month": np.tile(mos, nc_), col: samp[r].reshape(-1)}
                         ).to_parquet(os.path.join(out_dir, f"{r}__{col}.parquet"), index=False)

    def col_done(col):
        return all(os.path.exists(os.path.join(out_dir, f"{r}__{col}.parquet")) for r in regs)

    if do("scpdsi") and not col_done("scpdsi"):
        t = time.time(); p = _download(SCPDSI_URL, os.path.join(tmp, "scpdsi.nc"))
        write_col("scpdsi", _sample_nc(p, ["scpdsi", "sc_PDSI_pm", "sc_PDSI"], cells, regs, idxc))
        print(f"  scpdsi sampled+written ({time.time()-t:.0f}s)", flush=True)
    if do("spi"):
        for ts in SPI_SCALES:
            col = f"spi_{ts:02d}m"
            if col_done(col):
                continue
            t = time.time(); p = _download(SPI_URL.format(ts=ts), os.path.join(tmp, f"spi{ts:02d}.nc"))
            write_col(col, _sample_nc(p, ["spi", f"spi_{ts}", f"spi_gamma_{ts}"], cells, regs, idxc))
            print(f"  {col} sampled+written ({time.time()-t:.0f}s)", flush=True)
    if do("eddi") and not col_done("eddi"):
        eb = {r: np.full((len(cells[r]), NMON), np.nan, "float32") for r in regs}; t = time.time()
        for j, (y, m) in enumerate(TARGET):
            ymd = f"{y}{m:02d}{calendar.monthrange(y, m)[1]:02d}"
            try:
                p = _download(EDDI_URL.format(y=y, ymd=ymd), os.path.join(tmp, f"eddi_{y}{m:02d}.asc"), minbytes=1000)
                s = _sample_asc(p, cells, regs)
                for r in regs:
                    eb[r][:, j] = s[r]
            except Exception as e:
                print(f"    !! eddi {y}-{m:02d}: {type(e).__name__}: {e}", flush=True)
            if j % 24 == 0:
                print(f"    eddi {y}-{m:02d} ({j+1}/{NMON}) ({time.time()-t:.0f}s)", flush=True)
        write_col("eddi", eb); del eb
        print(f"  eddi sampled+written ({time.time()-t:.0f}s)", flush=True)

    # MERGE per-region single-col sidecars -> {r}_drought.parquet (one region at a time = memory-safe)
    allcols = (["scpdsi"] if do("scpdsi") else []) + ([f"spi_{ts:02d}m" for ts in SPI_SCALES] if do("spi") else []) \
        + (["eddi"] if do("eddi") else [])
    nmerged = 0
    for r in regs:
        parts = [pd.read_parquet(os.path.join(out_dir, f"{r}__{col}.parquet")).set_index([CC, "year", "month"])
                 for col in allcols if os.path.exists(os.path.join(out_dir, f"{r}__{col}.parquet"))]
        if parts:
            pd.concat(parts, axis=1).reset_index().to_parquet(os.path.join(out_dir, f"{r}_drought.parquet"), index=False)
            nmerged += 1
    print(f"DROUGHT_DONE -> {out_dir}/ ({nmerged} regions merged; per-col sidecars kept for resume; "
          f"join on [cell_id, year, month]); tmp in {tmp}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
