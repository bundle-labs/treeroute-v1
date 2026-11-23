"""Ingest the 11 ERA5-family day-count / VPD / humidity drivers from AgERA5
(sis-agrometeorological-indicators v2, CDS) -- PRE-COMPUTED DAILY fields (no hourly to crunch),
so requests are light enough to fit the CDS cost limit (with adaptive year-chunking). Per region:
area-subset requests for 4 variable groups over 2002-2023 -> daily 0.1deg fields -> derive 11
MONTHLY cols on the grid -> sample to the 4km cells -> per-region parquet. Crash-safe (skip done
regions). EVERYTHING ON D:. Runs in py-3.9 (cdsapi + netCDF4).  [soil moisture -> ESA-CCI;
snow phenology -> separate; this covers the rest of the ERA5 tier.]

  py -3.9 presplit_cc/ingest_agera5_daycounts.py --region thar_desert --years 2010
  py -3.9 presplit_cc/ingest_agera5_daycounts.py --out D:\agera5_daycounts --tmp D:\agera5_dl
"""
import calendar
import glob
import os
import sys
import time
import zipfile

import numpy as np
import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
CC = "cell_id"
DATASET = "sis-agrometeorological-indicators"
YEARS = list(range(2002, 2024))
TMP_DEFAULT = r"D:\agera5_dl"
OUT_DEFAULT = r"D:\agera5_daycounts"

# ONE statistic per request (3-in-1 temperature blew the CDS cost limit). filename tokens map a
# daily file to its role. The year-chunker in _retrieve splits the year range until each fits.
GROUPS = {
    "tmin":   {"variable": "2m_temperature", "statistic": ["24_hour_minimum"], "roles": {"Min-24h": "tmin"}},
    "tmax":   {"variable": "2m_temperature", "statistic": ["24_hour_maximum"], "roles": {"Max-24h": "tmax"}},
    "tmean":  {"variable": "2m_temperature", "statistic": ["24_hour_mean"], "roles": {"Mean-24h": "tmean"}},
    "precip": {"variable": "precipitation_flux", "roles": {"Precipitation-Flux": "precip"}},
    "vp":     {"variable": "vapour_pressure", "statistic": ["24_hour_mean"], "roles": {"Vapour-Pressure": "vp"}},
    "rh":     {"variable": "2m_relative_humidity", "time": ["15_00"], "roles": {"Relative-Humidity": "rh"}},
}
OUTCOLS = ["frost_days", "heatwave_days_gt35C", "gdd5_degC_days", "wet_day_count", "V03_max_daily_precip_mm",
           "precip_intensity_mm", "vpd_max_daily", "vpd_days_gt_2kpa", "vpd_warm_season_mean", "sph_kgkg", "rmin_pct"]


def grid_indices(lons, lats, glon, glat):
    lons = np.asarray(lons, float); lats = np.asarray(lats, float)
    lon0, dlon = float(glon[0]), float(glon[1] - glon[0])
    lat0, dlat = float(glat[0]), float(glat[1] - glat[0])
    ilon = np.clip(np.rint((lons - lon0) / dlon).astype(int), 0, len(glon) - 1)
    ilat = np.clip(np.rint((lats - lat0) / dlat).astype(int), 0, len(glat) - 1)
    return ilon, ilat


def _esat(tc):
    """Saturation vapour pressure (hPa) from air temp in degC (WMO/Tetens)."""
    return 6.112 * np.exp(17.62 * tc / (243.12 + tc))


def _retrieve(c, gspec, bbox, years, tmp, tag, attempt=0):
    """Retrieve a variable group for `years`. On CDS 'cost limits exceeded' -> split the year range
    and recurse. On a rejection / rate-limit / transient error (CDS busy or over the per-account
    request limit) -> back off and retry. Returns the list of downloaded zip paths."""
    out = os.path.join(tmp, f"{tag}_{years[0]}_{years[-1]}.zip")
    if os.path.exists(out):                                       # validate cache before reuse: a power-loss
        try:                                                      # truncated zip would otherwise STUCK its box
            with zipfile.ZipFile(out) as zf:
                if os.path.getsize(out) > 1000 and zf.testzip() is None and any(n.endswith(".nc") for n in zf.namelist()):
                    return [out]
            raise zipfile.BadZipFile("incomplete")
        except Exception:
            try:
                os.remove(out)                                    # corrupt/partial -> drop it and re-download
            except OSError:
                pass
    req = {"variable": gspec["variable"], "year": [str(y) for y in years],
           "month": [f"{m:02d}" for m in range(1, 13)], "day": [f"{d:02d}" for d in range(1, 32)],
           "area": bbox, "version": "2_0"}
    for k in ("statistic", "time"):
        if k in gspec:
            req[k] = gspec[k]
    try:
        c.retrieve(DATASET, req, out)
        return [out]
    except Exception as e:
        msg = str(e).lower()
        if "cost" in msg and len(years) > 1:                          # too big -> split the year range
            mid = len(years) // 2
            return (_retrieve(c, gspec, bbox, years[:mid], tmp, tag)
                    + _retrieve(c, gspec, bbox, years[mid:], tmp, tag))
        transient = any(k in msg for k in ("reject", "429", "too many", "limit", "500", "502", "503",
                                           "timeout", "timed out", "connection", "remote", "bad gateway",
                                           "download", "0 byte", "incomplete", "reset", "cci2", "504",
                                           "internalerror", "serviceunavailable", "slowdown"))
        if transient and attempt < 12:                                # CDS busy/over-limit -> wait + retry
            time.sleep(min(20 * (attempt + 1), 180))
            return _retrieve(c, gspec, bbox, years, tmp, tag, attempt + 1)
        raise


def _read_group(zips, roles):
    """Read all daily files across the group's zips -> {role: {date: 2D array}}, plus glat/glon."""
    from netCDF4 import Dataset
    import re
    out = {r: {} for r in roles.values()}
    glat = glon = None
    for zp in zips:
        z = zipfile.ZipFile(zp)
        for name in z.namelist():
            if not name.endswith(".nc"):
                continue
            role = next((rl for tok, rl in roles.items() if tok in name), None)
            if role is None:
                continue
            m = re.search(r"_(\d{8})_", name)
            if not m:
                continue
            d = pd.Timestamp(m.group(1))
            z.extract(name, os.path.dirname(zp))
            fp = os.path.join(os.path.dirname(zp), name)
            ds = Dataset(fp)
            if glat is None:
                la = next(v for v in ds.variables if v.lower() in ("lat", "latitude"))
                lo = next(v for v in ds.variables if v.lower() in ("lon", "longitude"))
                glat = np.asarray(ds.variables[la][:]); glon = np.asarray(ds.variables[lo][:])
            vn = next(v for v in ds.variables if ds.variables[v].ndim >= 2
                      and v.lower() not in ("lat", "latitude", "lon", "longitude", "time"))
            arr = np.ma.filled(np.squeeze(ds.variables[vn][:]).astype("float32"), np.nan)
            ds.close()
            os.remove(fp)
            out[role][d] = arr
    return out, glat, glon


def _derive(daily, glat, glon, years):
    """daily: {role:{date:2D}} -> monthly grids {col: (12*len(years), nlat, nlon)}."""
    dates = sorted(set().union(*[set(daily[r]) for r in daily if daily[r]]))
    if not dates:
        return None
    ny, nx = next(iter(daily["tmin"].values())).shape
    months = [(y, m) for y in years for m in range(1, 13)]
    out = {c: np.full((len(months), ny, nx), np.nan, "float32") for c in OUTCOLS if c != "sph_kgkg"}
    out["vp_mean"] = np.full((len(months), ny, nx), np.nan, "float32")   # intermediate for sph (needs elev)
    for j, (y, m) in enumerate(months):
        dd = [d for d in dates if d.year == y and d.month == m]
        if not dd:
            continue

        def stk(role):
            return np.stack([daily[role][d] for d in dd if d in daily[role]], 0) if dd else None
        tmin = stk("tmin"); tmax = stk("tmax"); tmean = stk("tmean")
        precip = stk("precip"); vp = stk("vp"); rh = stk("rh")
        with np.errstate(invalid="ignore"):
            if tmin is not None:
                out["frost_days"][j] = np.nansum(tmin - 273.15 < 0, 0)
            if tmax is not None:
                out["heatwave_days_gt35C"][j] = np.nansum(tmax - 273.15 > 35, 0)
            if tmean is not None:
                out["gdd5_degC_days"][j] = np.nansum(np.clip((tmean - 273.15) - 5, 0, None), 0)
            if precip is not None:
                out["wet_day_count"][j] = np.nansum(precip >= 1.0, 0)
                out["V03_max_daily_precip_mm"][j] = np.nanmax(precip, 0)
                wet = np.nansum(precip >= 1.0, 0)
                out["precip_intensity_mm"][j] = np.where(wet > 0, np.nansum(precip, 0) / np.maximum(wet, 1), 0.0)
            if tmean is not None and vp is not None:
                vpd = (_esat(tmean - 273.15) - vp) / 10.0          # hPa -> kPa
                vpd = np.clip(vpd, 0, None)
                out["vpd_max_daily"][j] = np.nanmax(vpd, 0)
                out["vpd_days_gt_2kpa"][j] = np.nansum(vpd > 2.0, 0)
                out["vpd_warm_season_mean"][j] = np.nanmean(vpd, 0)
                out["vp_mean"][j] = np.nanmean(vp, 0)
            if rh is not None:
                out["rmin_pct"][j] = np.nanmean(rh, 0)
    return out


def _masters():
    masters = {}
    for d in (cfg["data"]["master_dir"], cfg["forecast"]["regions_dir"]):
        for p in glob.glob(os.path.join(d, "*_master_*.parquet")):
            if ".bak." not in p:
                masters.setdefault(os.path.basename(p).split("_master_")[0], p)
    return masters


def main(argv):
    def opt(flag, d=None):
        return argv[argv.index(flag) + 1] if flag in argv else d
    tmp = opt("--tmp", TMP_DEFAULT); out_dir = opt("--out", OUT_DEFAULT)
    only = opt("--region"); limit = opt("--limit")
    years = [int(y) for y in opt("--years", ",".join(map(str, YEARS))).split(",")]
    os.makedirs(tmp, exist_ok=True); os.makedirs(out_dir, exist_ok=True)

    import cdsapi
    c = cdsapi.Client()
    masters = _masters()
    regs = sorted(masters)
    if only:
        regs = [r for r in regs if r == only]
    if limit:
        regs = regs[:int(limit)]
    shard = opt("--shard")                              # "i/n": this instance handles regions where index%n==i
    if shard:
        i, n = (int(x) for x in shard.split("/"))
        regs = [r for k, r in enumerate(regs) if k % n == i]
    print(f"AgERA5 day-counts -> {len(regs)} regions x {len(years)} yrs -> {out_dir}", flush=True)

    for r in regs:
        outf = os.path.join(out_dir, f"{r}_agera5.parquet")
        if os.path.exists(outf):
            print(f"  {r}: exists, skip", flush=True); continue
        cells = pd.read_parquet(masters[r], columns=[CC, "lon", "lat", "V25_elevation_m"]).drop_duplicates(CC)
        # REGION-REPRESENTATIVE: request a SMALL central patch (~9 0.1deg cells) so all 22 years fit
        # in ONE request per variable (vs forced 1-year chunks over the full extent). Each 4km cell
        # then takes its nearest patch value -> near-uniform day-counts per region (sph still varies
        # per cell via elevation). ~6 requests/region instead of ~130. (Half-day fetch vs ~2 weeks.)
        clon, clat = float(cells.lon.mean()), float(cells.lat.mean())
        half = 0.1
        bbox = [clat + half, clon - half, clat - half, clon + half]   # N, W, S, E (~0.2deg = 3x3 cells)
        try:
            daily = {}
            for g, gspec in GROUPS.items():
                zips = _retrieve(c, gspec, bbox, years, tmp, f"{r}_{g}")
                gd, glat, glon = _read_group(zips, gspec["roles"])
                daily.update(gd)
                for z in zips:
                    try:
                        os.remove(z)
                    except OSError:
                        pass
            grids = _derive(daily, glat, glon, years)
            if grids is None:
                print(f"  {r}: NO DATA", flush=True); continue
            il, ia = grid_indices(cells.lon.to_numpy(), cells.lat.to_numpy(), glon, glat)
            months = [(y, m) for y in years for m in range(1, 13)]
            ncell = len(cells)
            rows = {CC: np.repeat(cells[CC].to_numpy(), len(months)),
                    "year": np.tile([y for y, m in months], ncell),
                    "month": np.tile([m for y, m in months], ncell)}
            for col in OUTCOLS:
                if col == "sph_kgkg":
                    continue
                rows[col] = grids[col][:, ia, il].T.reshape(-1)
            # sph from monthly-mean vapour pressure (sampled) + per-cell barometric pressure (elevation)
            e = grids["vp_mean"][:, ia, il].T.reshape(-1) * 100.0           # hPa -> Pa
            elev = np.repeat(cells["V25_elevation_m"].to_numpy(), len(months))
            p = 101325.0 * np.power(np.clip(1 - 2.25577e-5 * np.nan_to_num(elev), 0.1, 1.2), 5.25588)
            with np.errstate(invalid="ignore", divide="ignore"):
                rows["sph_kgkg"] = (0.622 * e / np.maximum(p - 0.378 * e, 1.0)).astype("float32")
            pd.DataFrame(rows).to_parquet(outf, index=False)
            print(f"  {r}: wrote {ncell} cells x {len(months)} months", flush=True)
        except Exception as ex:
            print(f"  {r}: ERROR {type(ex).__name__}: {str(ex)[:160]}", flush=True)
    print("done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
