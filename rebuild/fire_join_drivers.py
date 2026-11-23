"""Put the three downloaded fire drivers onto the panel cells.

    py -3.9 -u fire_join_drivers.py --only=greece_mainland    # smoke, ~1 min
    py -3.9 -u fire_join_drivers.py                           # all complete regions

These files have been on disk since the first day and were never joined, so every result so far
came from 135 columns fetched for the NDVI problem with nothing fire-specific in them. This is the
subsetting step, not a download.

WHAT GOES IN, WITH THE STRUCTURE VERIFIED AGAINST THE FILES THEMSELVES

  WGLC lightning   0.5 deg, 192 months, time = days since 2010-01-01, lat ASCENDING, lon -180..180,
                   pixel-registered so the containing cell is floor((lat+90)*2), never round().
                   The 0.5 deg file is used deliberately, not the 5-arcmin one: the >=2-strokes/hour
                   noise filter is applied AT THE TARGET RESOLUTION, so the finer grid is the more
                   heavily censored one, worst in exactly the sparse-lightning regions.
                   RECORD STARTS 2010-01 and Kaplan & Lau say to discard 2010-2012 as WWLLN
                   build-out, so 2002-2012 is emitted as NaN with an explicit missing flag rather
                   than zero -- a zero here would read as "no lightning" instead of "not measured",
                   which is the difference between a desert and a gap in the network.

  LPDR v3 VOD      25 km EASE-Grid v1 (EPSG:3410), 233 monthly GeoTIFFs, 2002-07..2022-12.
                   Microwave, so it is mechanically independent of the optical stack and cannot
                   mistake a burn scar for low greenness. NODATA is <= -998. A ten-month hole runs
                   2011-10..2012-07 (AMSR-E antenna failure to AMSR2 start) and is left as NaN --
                   interpolating across it would fabricate fuel state through two fire seasons.

  ESA CCI Biomass  0.1 deg, 18 epochs 2005-2012 and 2015-2024, lat DESCENDING. Forest product, so
                   it is blind to herbaceous fuel and is literally constant in grassland regions.
                   Lagged ONE YEAR: target year Y reads epoch Y-1, because AGB already contains the
                   post-fire drop and reading it at Y would partly report the answer.

RATIOS AND ANOMALIES, NOT LEVELS. An absolute lightning density or biomass fingerprints the region
and evaporates under a region-blocked split. Every normaliser here is fitted on TRAIN YEARS ONLY
(<= NORM_END): fitting a climatology on the full record and then splitting is the classic temporal
leak, and it is invisible in the output.
"""
import argparse
import glob
import io as _io
import os
import re
import sys
import time
import warnings
import zipfile

sys.path.insert(0, r"C:\Users\<user>\Desktop\data set for reserch paper")
from coral_safe import cap_threads, mem_str

cap_threads(4)
warnings.filterwarnings("ignore")

import netCDF4
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform as rio_transform
from scipy.ndimage import median_filter

YEARS = list(range(2002, 2023))
NORM_END = 2018          # anomalies/z-scores fitted on <= this year only
RAW = "D:/fire/drivers/raw"
OUT = "D:/fire/drivers/joined"
WGLC = os.path.join(RAW, "wglc_timeseries_30m_monthly.nc")
VODZ = os.path.join(RAW, "LPDR_v3_monthlyVOD_AM130.zip")
AGB = os.path.join(RAW, "ESACCI-BIOMASS-L4-AGB-MERGED-10000m-fv7.0.nc")
WGLC_START = 2010
WGLC_TRUST = 2013        # Kaplan & Lau: discard 2010-2012, network build-out


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


def complete_regions():
    by = {}
    for f in glob.glob("D:/fire/target/*.parquet"):
        m = re.match(r"(.+)_(\d{4})\.parquet$", os.path.basename(f))
        if m:
            by.setdefault(m.group(1), set()).add(int(m.group(2)))
    return sorted(r for r in by if set(YEARS) <= by[r])


# ---------------------------------------------------------------------------------- WGLC
def load_wglc():
    d = netCDF4.Dataset(WGLC)
    dens = np.asarray(d.variables["density"][:], np.float32)      # (192, 360, 720)
    la = np.asarray(d.variables["lat"][:], np.float64)
    d.close()
    if la[0] > la[-1]:                    # defensive: spec says ascending, assert rather than trust
        dens = dens[:, ::-1, :]
    return dens


def wglc_cols(dens, lat, lon, yy, mm):
    i = np.clip(np.floor((lat + 90.0) * 2).astype(int), 0, 359)
    j = np.clip(np.floor((lon + 180.0) * 2).astype(int), 0, 719)
    k = (yy - WGLC_START) * 12 + (mm - 1)
    ok = (k >= 0) & (k < dens.shape[0]) & (yy >= WGLC_TRUST)
    out = np.full(len(lat), np.nan, np.float32)
    out[ok] = dens[k[ok], i[ok], j[ok]]
    return out, (~ok).astype(np.float32)


# ---------------------------------------------------------------------------------- VOD
def vod_series(lat, lon):
    """Monthly VOD at each cell. Returns (n_cells, n_months) with NaN where absent."""
    z = zipfile.ZipFile(VODZ)
    members = {}
    for n in z.namelist():
        m = re.search(r"VOD_(\d{4})_(\d{2})_ave_D\.tif$", n)
        if m:
            members[(int(m.group(1)), int(m.group(2)))] = n
    out = np.full((len(lat), len(YEARS) * 12), np.nan, np.float32)
    xs = ys = None
    for yi, y in enumerate(YEARS):
        for mo in range(1, 13):
            n = members.get((y, mo))
            if n is None:
                continue                    # the 2011-10..2012-07 hole lands here, left as NaN
            with rasterio.open(_io.BytesIO(z.read(n))) as ds:
                if xs is None:              # project cell centres into EASE-Grid once
                    xs, ys = rio_transform("EPSG:4326", ds.crs, list(lon), list(lat))
                    xs = np.asarray(xs)
                    ys = np.asarray(ys)
                    inv = ~ds.transform
                    cc, rr = inv * (xs, ys)
                    rr = np.clip(np.floor(rr).astype(int), 0, ds.height - 1)
                    cc = np.clip(np.floor(cc).astype(int), 0, ds.width - 1)
                a = ds.read(1)
            v = a[rr, cc].astype(np.float32)
            v[v <= -998] = np.nan           # documented NODATA sentinel
            out[:, yi * 12 + mo - 1] = v
    z.close()
    return out


# ---------------------------------------------------------------------------------- AGB
def load_agb():
    d = netCDF4.Dataset(AGB)
    agb = np.asarray(d.variables["agb"][:], np.float32)           # (18, 1800, 3600) lat DESCENDING
    tv = d.variables["time"]
    ep = [int(str(x)[:4]) for x in netCDF4.num2date(tv[:], tv.units)]
    d.close()
    agb = np.where(np.isfinite(agb), agb, np.nan)
    # agb_contrast is the one column that survived the audit: the cell against its neighbourhood,
    # which is dimensionless and therefore survives a region-blocked split, where a raw Mg/ha level
    # does not. Computed once per epoch on the global grid.
    con = np.empty_like(agb)
    for e in range(agb.shape[0]):
        lay = np.nan_to_num(agb[e], nan=0.0)
        med = median_filter(lay, size=5, mode="nearest")
        con[e] = lay / np.maximum(med, 1.0)
    return agb, con, ep


def agb_cols(agb, con, ep, lat, lon, yy):
    i = np.clip(np.floor((90.0 - lat) * 10).astype(int), 0, agb.shape[1] - 1)
    j = np.clip(np.floor((lon + 180.0) * 10).astype(int), 0, agb.shape[2] - 1)
    want = yy - 1                                # ONE-YEAR LAG, always
    lvl = np.full(len(lat), np.nan, np.float32)
    ctr = np.full(len(lat), np.nan, np.float32)
    for e, yr in enumerate(ep):
        m = want == yr
        if m.any():
            lvl[m] = agb[e, i[m], j[m]]
            ctr[m] = con[e, i[m], j[m]]
    return lvl, ctr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    A = ap.parse_args()
    regs = ([x.strip() for x in A.only.split(",")] if A.only else complete_regions())
    os.makedirs(OUT, exist_ok=True)
    log("=" * 108)
    log("JOIN FIRE DRIVERS -> panel cells | %d regions | %s" % (len(regs), mem_str()))
    log("  loading WGLC ..."); dens = load_wglc()
    log("    density %s | months %d (%d-01 onward, trusted from %d)"
        % (str(dens.shape), dens.shape[0], WGLC_START, WGLC_TRUST))
    log("  loading CCI Biomass ..."); agb, con, ep = load_agb()
    log("    %d epochs %s" % (len(ep), ep))

    for r in regs:
        dst = os.path.join(OUT, "%s.parquet" % r)
        if os.path.exists(dst):
            log("  %-30s HAVE" % r)
            continue
        t0 = time.time()
        sel = pd.read_parquet("D:/fire/cells_1000.parquet")
        sel = sel[sel.region == r]
        lat = sel.lat.values.astype(np.float64)
        lon = sel.lon.values.astype(np.float64)
        n = len(lat)
        V = vod_series(lat, lon)                                  # (n, 252)
        nm = len(YEARS) * 12
        yy = np.repeat(np.array([y for y in YEARS for _ in range(12)])[None, :], n, 0).ravel()
        mm = np.repeat(np.array([m for _ in YEARS for m in range(1, 13)])[None, :], n, 0).ravel()
        LAT = np.repeat(lat, nm)
        LON = np.repeat(lon, nm)
        lg, lg_miss = wglc_cols(dens, LAT, LON, yy, mm)
        al, ac = agb_cols(agb, con, ep, LAT, LON, yy)

        # VOD derived forms. Level lagged 2 months (the readme does not state whether the internal
        # smoothing window is trailing, so lag 1 is not provably safe); differences and a
        # cell x month anomaly whose climatology uses TRAIN YEARS ONLY.
        Vl = np.full_like(V, np.nan)
        Vl[:, 2:] = V[:, :-2]
        d1 = np.full_like(V, np.nan)
        d1[:, 3:] = V[:, 2:-1] - V[:, 1:-2]
        train_mask = np.array([y <= NORM_END for y in YEARS for _ in range(12)])
        clim = np.full((n, 12), np.nan, np.float32)
        for mo in range(12):
            cols = [k for k in range(nm) if k % 12 == mo and train_mask[k]]
            clim[:, mo] = np.nanmean(Vl[:, cols], axis=1)
        anom = Vl - clim[:, np.arange(nm) % 12]

        out = pd.DataFrame({
            "lat": LAT, "lon": LON, "year": yy, "month": mm,
            "lgt_density": lg, "lgt_missing": lg_miss,
            "lgt_is_zero": np.where(np.isnan(lg), np.nan, (lg <= 0).astype(np.float32)),
            "vod_lag2": Vl.ravel(), "vod_d1": d1.ravel(), "vod_anom": anom.ravel(),
            "agb_lag1y": al, "agb_contrast": ac,
        })
        out.to_parquet(dst + ".part", index=False)
        os.replace(dst + ".part", dst)
        log("  %-30s %6d cells | lgt %4.1f%% present | vod %4.1f%% | agb %4.1f%% | %.1f min"
            % (r, n, 100 * np.isfinite(lg).mean(), 100 * np.isfinite(out.vod_lag2).mean(),
               100 * np.isfinite(al).mean(), (time.time() - t0) / 60))
    log("=" * 108)
    log("wrote %s" % OUT)
    log("COVERAGE IS THE THING TO READ FIRST, not the values: lightning is absent before 2013 by")
    log("construction, VOD has a ten-month hole in 2011-12, and biomass has no 2002-2005 or 2014.")
    log("Those NaNs are honest gaps and must stay NaN -- filling them invents fuel and ignition.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
