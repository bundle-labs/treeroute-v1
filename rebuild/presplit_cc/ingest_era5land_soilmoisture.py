"""Ingest V30_soil_moisture_pct -- master's EXACT source (feature_definitions.json): ERA5-Land monthly
`volumetric_soil_water_layer_1` (0-7cm topsoil) x 100 -> percent. CDS `reanalysis-era5-land-monthly-means`,
0.1deg. GLOBAL strategy: ERA5-Land has a strict per-dataset queued-request cap AND tonight CDS is
queue-congested (~min per request), so per-region (133 requests) is far too slow. Instead download the
GLOBAL field in a few multi-year chunks (~4 requests total) and sample ALL 133 regions from each ->
30x fewer requests, dodges the cap, ~1 process. m3/m3 x 100. Crash-safe (skip done regions). On D:.

  py -3.9 presplit_cc/ingest_era5land_soilmoisture.py --years 2010 --region thar_desert   # quick test
  py -3.9 presplit_cc/ingest_era5land_soilmoisture.py --out D:\soil_moisture_monthly
"""
import math
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ingest_agera5_daycounts import CC, _masters, grid_indices  # noqa: E402

DATASET = "reanalysis-era5-land-monthly-means"
VAR = "volumetric_soil_water_layer_1"
YEARS = list(range(2002, 2024))
CHUNK = 6                                                        # years of GLOBAL data per request (memory vs request-count)
TMP_DEFAULT = r"D:\era5land_dl"
OUT_DEFAULT = r"D:\soil_moisture_monthly"
_TRANSIENT = ("429", "too many", "500", "502", "503", "504", "timeout", "timed out", "connection",
              "remote", "bad gateway", "download", "0 byte", "incomplete", "reset", "cci2",
              "internalerror", "serviceunavailable", "slowdown")


def _valid_nc(path):
    try:
        from netCDF4 import Dataset
        ds = Dataset(path); ok = "swvl1" in ds.variables and ds.variables["swvl1"].size > 0; ds.close()
        return ok
    except Exception:
        return False


def _retrieve(c, bbox, years, tmp, tag, attempt=0):
    """bbox=None -> GLOBAL (no area). Year-split on a genuine size/cost limit; long backoff on the
    per-dataset queued-request cap; standard backoff on transient/download errors."""
    out = os.path.join(tmp, f"{tag}_{years[0]}_{years[-1]}.nc")
    if os.path.exists(out):
        if os.path.getsize(out) > 1000 and _valid_nc(out):
            return [out]
        try:
            os.remove(out)
        except OSError:
            pass
    req = {"variable": [VAR], "product_type": ["monthly_averaged_reanalysis"],
           "year": [str(y) for y in years], "month": [f"{m:02d}" for m in range(1, 13)],
           "time": ["00:00"], "data_format": "netcdf", "download_format": "unarchived"}
    if bbox is not None:
        req["area"] = bbox
    try:
        c.retrieve(DATASET, req, out)
        return [out]
    except Exception as e:
        msg = str(e).lower()
        if ("cost" in msg or "too large" in msg or "exceeds" in msg) and len(years) > 1:
            mid = len(years) // 2
            return _retrieve(c, bbox, years[:mid], tmp, tag) + _retrieve(c, bbox, years[mid:], tmp, tag)
        if ("temporarily limited" in msg or "queued requests" in msg or "rejected" in msg) and attempt < 30:
            time.sleep(120)
            return _retrieve(c, bbox, years, tmp, tag, attempt + 1)
        if any(k in msg for k in _TRANSIENT) and attempt < 12:
            time.sleep(min(20 * (attempt + 1), 180))
            return _retrieve(c, bbox, years, tmp, tag, attempt + 1)
        raise


def _read(ncs):
    from netCDF4 import Dataset, num2date
    out = {}; glat = glon = None
    for nc in ncs:
        ds = Dataset(nc)
        la = next(v for v in ds.variables if v.lower() in ("latitude", "lat"))
        lo = next(v for v in ds.variables if v.lower() in ("longitude", "lon"))
        if glat is None:
            glat = np.asarray(ds.variables[la][:]); glon = np.asarray(ds.variables[lo][:])
        tv = next(v for v in ds.variables if v.lower() in ("valid_time", "time"))
        times = num2date(ds.variables[tv][:], ds.variables[tv].units)
        arr = np.ma.filled(np.asarray(ds.variables["swvl1"][:]).astype("float32"), np.nan)
        while arr.ndim > 3:
            arr = np.nanmean(arr, axis=1)
        if arr.ndim == 2:
            arr = arr[None]
        for i, t in enumerate(np.atleast_1d(times)):
            out[(t.year, t.month)] = arr[i]
        ds.close()
    return out, glat, glon


def main(argv):
    def opt(f, d=None):
        return argv[argv.index(f) + 1] if f in argv else d
    tmp = opt("--tmp", TMP_DEFAULT); out_dir = opt("--out", OUT_DEFAULT)
    years = [int(y) for y in opt("--years", ",".join(map(str, YEARS))).split(",")]
    chunk = int(opt("--chunk", CHUNK))
    os.makedirs(tmp, exist_ok=True); os.makedirs(out_dir, exist_ok=True)
    masters = _masters(); regs = sorted(masters)
    todo = [r for r in regs if not os.path.exists(os.path.join(out_dir, f"{r}_soilm.parquet"))]
    if opt("--region"):
        todo = [r for r in todo if r == opt("--region")] or [opt("--region")]
    if not todo:
        print("all regions done.", flush=True); return 0
    cells = {r: pd.read_parquet(masters[r], columns=[CC, "lon", "lat"]).drop_duplicates(CC) for r in todo}
    months = [(y, m) for y in years for m in range(1, 13)]
    midx = {ym: j for j, ym in enumerate(months)}
    acc = {r: np.full((len(months), len(cells[r])), np.nan, "float32") for r in todo}
    idx = {}
    print(f"ERA5-Land soil moisture (GLOBAL) -> {len(todo)} regions x {len(years)} yrs, chunk={chunk} -> {out_dir}", flush=True)

    import cdsapi
    c = cdsapi.Client()
    for ci in range(0, len(years), chunk):
        ych = years[ci:ci + chunk]
        try:
            ncs = _retrieve(c, None, ych, tmp, "global")           # GLOBAL field for this year-chunk
            data, glat, glon = _read(ncs)
            if not idx:
                # WRAPAROUND-CORRECT lon index via modulo -> works for ANY grid convention (0..360 OR
                # -180..180), no detection needed. (lat clipped; lat doesn't wrap.) This is what the
                # max(glon)>180 heuristic got wrong on multi-year global requests.
                lon0 = float(glon[0]); dlon = float(glon[1] - glon[0]); nlon = len(glon)
                lat0 = float(glat[0]); dlat = float(glat[1] - glat[0]); nlat = len(glat)
                print(f"    grid: lon[{float(np.min(glon)):.1f},{float(np.max(glon)):.1f}] n={nlon}  "
                      f"lat[{float(np.min(glat)):.1f},{float(np.max(glat)):.1f}] n={nlat}", flush=True)
                for r in todo:
                    il = np.rint((cells[r].lon.to_numpy() - lon0) / dlon).astype(int) % nlon
                    ia = np.clip(np.rint((cells[r].lat.to_numpy() - lat0) / dlat).astype(int), 0, nlat - 1)
                    idx[r] = (ia, il)
            for r in todo:
                ia, il = idx[r]
                for ym, field in data.items():
                    if ym in midx:
                        acc[r][midx[ym]] = field[ia, il] * 100.0   # m3/m3 -> percent
            del data
            for z in ncs:
                try:
                    os.remove(z)
                except OSError:
                    pass
            print(f"  chunk {ych[0]}-{ych[-1]}: sampled all {len(todo)} regions", flush=True)
        except Exception as ex:
            print(f"  chunk {ych[0]}-{ych[-1]} ERROR {type(ex).__name__}: {str(ex)[:160]}", flush=True)
            return 1
    for r in todo:
        ncell = len(cells[r])
        rows = {CC: np.repeat(cells[r][CC].to_numpy(), len(months)),
                "year": np.tile([y for y, m in months], ncell),
                "month": np.tile([m for y, m in months], ncell),
                "V30_soil_moisture_pct": acc[r].T.reshape(-1)}
        pd.DataFrame(rows).to_parquet(os.path.join(out_dir, f"{r}_soilm.parquet"), index=False)
        print(f"  wrote {r} ({ncell} cells, mean {np.nanmean(acc[r]):.1f}% nan {np.isnan(acc[r]).mean()*100:.1f}%)", flush=True)
    print("done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
