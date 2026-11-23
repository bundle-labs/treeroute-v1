"""Ingest the 4 snow-phenology drivers. Master (gee module_19) used MODIS MOD10A1 daily NDSI>=40;
per the user we use ERA5-Land daily `snow_cover` (CDS reanalysis-era5-land, 0.1deg global) with a
snow-day flag `snow_cover >= 50%` (majority-covered, ~NDSI>=40 analog). Per calendar year, split at
DOY 200 (module_19):
  * snow_duration_days     = count of snow-days in the year (0 if none)
  * snow_onset_doy         = FIRST snow-day DOY AFTER day 200 (fall onset); NaN if none
  * snow_disappearance_doy = LAST snow-day DOY BEFORE day 200 (spring melt); NaN if none
  * snow_max_doy           = MEDIAN DOY of all snow-days (peak-season center); NaN if none
GLOBAL per-year download read DAY-BY-DAY (lazy -> memory-bounded), modulo lon sampling, annual values
broadcast to the 12 months. 1 serial process (ERA5-Land queue cap). On D:. LAST tier before assembly.

  py -3.9 presplit_cc/ingest_era5land_snowphen.py --years 2010 --out D:\snowphen_test
  py -3.9 presplit_cc/ingest_era5land_snowphen.py --out D:\snowphen_monthly
"""
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ingest_agera5_daycounts import CC, _masters  # noqa: E402

DATASET = "reanalysis-era5-land"
VAR = "snow_cover"
NCVAR = "snowc"
THRESH = 50.0                                                    # snow_cover% >= this = snow day
SPLIT_DOY = 200
YEARS = list(range(2002, 2024))
TMP_DEFAULT = r"D:\era5land_dl"
OUT_DEFAULT = r"D:\snowphen_monthly"
_LIMIT = ("temporarily limited", "queued requests", "rejected")
_TRANSIENT = ("429", "too many", "500", "502", "503", "504", "timeout", "timed out", "connection",
              "remote", "bad gateway", "download", "0 byte", "incomplete", "reset", "cci2",
              "internalerror", "serviceunavailable", "slowdown")


def _valid_nc(p):
    try:
        from netCDF4 import Dataset
        ds = Dataset(p); ok = NCVAR in ds.variables and ds.variables[NCVAR].size > 0; ds.close()
        return ok
    except Exception:
        return False


def _retrieve(c, year, months, tmp, attempt=0):
    out = os.path.join(tmp, f"snow_{year}_{months[0]:02d}_{months[-1]:02d}.nc")
    if os.path.exists(out):
        if os.path.getsize(out) > 1000 and _valid_nc(out):
            return [out]
        try:
            os.remove(out)
        except OSError:
            pass
    req = {"variable": [VAR], "year": str(year), "month": [f"{m:02d}" for m in months],
           "day": [f"{d:02d}" for d in range(1, 32)], "time": ["00:00"],
           "data_format": "netcdf", "download_format": "unarchived"}
    try:
        c.retrieve(DATASET, req, out)
        return [out]
    except Exception as e:
        msg = str(e).lower()
        if ("cost" in msg or "too large" in msg or "exceeds" in msg) and len(months) > 1:
            mid = len(months) // 2
            return _retrieve(c, year, months[:mid], tmp) + _retrieve(c, year, months[mid:], tmp)
        if any(k in msg for k in _LIMIT) and attempt < 30:
            time.sleep(120); return _retrieve(c, year, months, tmp, attempt + 1)
        if any(k in msg for k in _TRANSIENT) and attempt < 12:
            time.sleep(min(20 * (attempt + 1), 180)); return _retrieve(c, year, months, tmp, attempt + 1)
        raise


def _derive(flag, doy_vec):
    """flag (366, ncell) uint8, doy_vec (366,) -> 4 cols (ncell,). NaN where no snow (per module_19)."""
    snowy = flag > 0
    duration = snowy.sum(0).astype("float32")                   # 0 if none
    after = snowy & (doy_vec[:, None] >= SPLIT_DOY)
    onset = np.where(after, doy_vec[:, None], 9999).min(0).astype("float32")
    onset[onset == 9999] = np.nan                               # no fall snow -> NaN
    before = snowy & (doy_vec[:, None] < SPLIT_DOY)
    disap = np.where(before, doy_vec[:, None], -1).max(0).astype("float32")
    disap[disap == -1] = np.nan                                 # no spring snow -> NaN
    with np.errstate(invalid="ignore"):
        sd = np.where(snowy, doy_vec[:, None].astype("float32"), np.nan)
        snow_max = np.nanmedian(sd, axis=0).astype("float32")   # NaN if no snow at all
    return duration, onset, disap, snow_max


def main(argv):
    def opt(f, d=None):
        return argv[argv.index(f) + 1] if f in argv else d
    tmp = opt("--tmp", TMP_DEFAULT); out_dir = opt("--out", OUT_DEFAULT)
    years = [int(y) for y in opt("--years", ",".join(map(str, YEARS))).split(",")]
    if opt("--shard"):                                          # by YEAR; downloads are sparse (1/yr) so a
        i, n = (int(x) for x in opt("--shard").split("/"))      # few shards rarely collide on the queue cap
        years = [y for k, y in enumerate(years) if k % n == i]
    os.makedirs(tmp, exist_ok=True); os.makedirs(out_dir, exist_ok=True)
    masters = _masters(); regs = sorted(masters)
    if opt("--region"):
        regs = [r for r in regs if r == opt("--region")]
    cells = {r: pd.read_parquet(masters[r], columns=[CC, "lon", "lat"]).drop_duplicates(CC) for r in regs}
    doy_vec = np.arange(1, 367)
    print(f"ERA5-Land snow phenology -> {len(regs)} regions x {len(years)} yrs -> {out_dir}", flush=True)

    from netCDF4 import Dataset, num2date
    import cdsapi
    c = cdsapi.Client()
    idx = {}
    for year in years:
        todo = [r for r in regs if not os.path.exists(os.path.join(out_dir, f"{r}_snowphen_{year}.parquet"))]
        if not todo:
            print(f"  {year}: all done, skip", flush=True); continue
        flag = {r: np.zeros((366, len(cells[r])), "uint8") for r in todo}
        try:
            ncs = _retrieve(c, year, list(range(1, 13)), tmp)
            ndays = 0
            for nc in ncs:
                ds = Dataset(nc)
                la = next(v for v in ds.variables if v.lower() in ("latitude", "lat"))
                lo = next(v for v in ds.variables if v.lower() in ("longitude", "lon"))
                glat = np.asarray(ds.variables[la][:]); glon = np.asarray(ds.variables[lo][:])
                tv = next(v for v in ds.variables if v.lower() in ("valid_time", "time"))
                times = num2date(ds.variables[tv][:], ds.variables[tv].units)
                if not idx:
                    lon0 = float(glon[0]); dlon = float(glon[1] - glon[0]); nlon = len(glon)
                    lat0 = float(glat[0]); dlat = float(glat[1] - glat[0]); nlat = len(glat)
                    print(f"    grid lon[{float(glon.min()):.1f},{float(glon.max()):.1f}] n={nlon} "
                          f"lat[{float(glat.min()):.1f},{float(glat.max()):.1f}] n={nlat}", flush=True)
                    for r in regs:
                        il = np.rint((cells[r].lon.to_numpy() - lon0) / dlon).astype(int) % nlon
                        ia = np.clip(np.rint((cells[r].lat.to_numpy() - lat0) / dlat).astype(int), 0, nlat - 1)
                        idx[r] = (ia, il)
                snowc = ds.variables[NCVAR]                     # (ntime, nlat, nlon), read lazily per day
                for di in range(len(times)):
                    doy = int(times[di].timetuple().tm_yday)
                    day = np.ma.filled(snowc[di], 0.0).astype("float32")   # ocean/missing -> 0 (not snow)
                    for r in todo:
                        ia, il = idx[r]
                        flag[r][doy - 1] = (day[ia, il] >= THRESH)
                    ndays += 1
                ds.close()
                try:
                    os.remove(nc)
                except OSError:
                    pass
            print(f"    {year}: read {ndays} days, deriving", flush=True)
        except Exception as ex:
            print(f"    {year} ERROR {type(ex).__name__}: {str(ex)[:160]}", flush=True); return 1
        for r in todo:
            ncell = len(cells[r])
            dur, ons, dis, smx = _derive(flag[r], doy_vec)
            rows = {CC: np.repeat(cells[r][CC].to_numpy(), 12),
                    "year": np.full(ncell * 12, year, "int64"),
                    "month": np.tile(np.arange(1, 13), ncell),
                    "snow_onset_doy": np.repeat(ons, 12), "snow_disappearance_doy": np.repeat(dis, 12),
                    "snow_duration_days": np.repeat(dur, 12), "snow_max_doy": np.repeat(smx, 12)}
            pd.DataFrame(rows).to_parquet(os.path.join(out_dir, f"{r}_snowphen_{year}.parquet"), index=False)
        del flag
        print(f"    {year}: wrote {len(todo)} regions", flush=True)
    print("done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
