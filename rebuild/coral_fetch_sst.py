"""Fetch CoralTemp 5 km daily SST for the bleaching observations, tile by tile, resumably.

    py -3.9 -u coral_fetch_sst.py --budget 150        # smoke: ~150 requests, ~50 min
    py -3.9 -u coral_fetch_sst.py --budget 0          # FULL: ~2,600 requests, ~14 h
    py -3.9 -u coral_fetch_sst.py --budget 0 --resume # same, skipping what is cached

WHY TILES AND NOT POINTS. ERDDAP's cost is dominated by opening the netCDF, not by bytes moved.
Measured on this dataset: a 1-pixel 1-year pull takes 16.1 s; a 1-degree box over the same year takes
19.0 s and returns ~400x the pixels. So a per-dive request pattern would cost ~10^4 x 16 s = 44 h per
variable-year and return bytes we could have had in a handful of tile pulls. Sites are therefore
grouped into 1-degree boxes, one request serves every site in the box, and the box is thrown away
after the per-site series are extracted -- which is also why the cache stays small.

WHAT IS CACHED. Only the pixel series each site actually needs, at
D:\\coral\\drivers\\sst\\<box>_<y0>_<y1>.parquet. The full box is never written to disk. Re-running
skips any tile already present, so an interrupted 14-hour run resumes by restarting it.

TWO CONVENTIONS THAT WILL BITE IF IGNORED.
  * PIFSC ERDDAP is 0-360 longitude (actual_range 0.025 .. 359.975) while GCBD coordinates are
    -180/+180. Converted at the request boundary and asserted.
  * The daily SST grid is latitude ASCENDING. Every DERIVED CRW product (climatology, DHW, monthly
    means) is latitude DESCENDING. Nothing here reads a derived product, but the moment one is added,
    a reused row index silently mirrors the climatology -- measured at +1.80 C on MMM at Heron Island,
    about 21.6 degree-heating-weeks. Index by coordinate, never by a remembered integer.

NO DERIVED CRW PRODUCT IS FETCHED ON PURPOSE. dhw/hs/ssta/baa are all functions of a FIXED 1985-2012
MMM, so for any dive before 2012 they carry the dive's own future. The heat-stress features are
recomputed from this daily SST with an expanding-window baseline in coral_features.py.
"""
import argparse
import io
import os
import sys
import time

import numpy as np
import pandas as pd
import requests

EV = r"D:\coral\target\events_dated.parquet"
OUT = r"D:\coral\drivers\sst"
BASE = "https://oceanwatch.pifsc.noaa.gov/erddap/griddap/CRW_sst_v3_1"
UA = {"User-Agent": "coral-bleaching-research/1.0 (academic)"}
LOOKBACK = 370          # days of history each observation needs (365 d window + slack)


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


def cells(ev, budget):
    """Group observations into (1-degree box, contiguous date range) request cells."""
    ev = ev.copy()
    ev["blat"] = np.floor(ev.lat).astype(int)
    ev["blon"] = np.floor(ev.lon).astype(int)
    ev["byr"] = ev.date.dt.year
    g = ev.groupby(["blat", "blon", "byr"]).agg(
        n=("pos", "size"), npos=("pos", "sum"),
        ndon=("side", lambda s: (s == "donor").sum()),
        d0=("date", "min"), d1=("date", "max")).reset_index()
    g["nneg"] = g.n - g.npos
    g["ntest"] = g.n - g.ndon
    if budget and budget < len(g):
        # Prioritise cells that carry BOTH classes and TEST-side events -- a smoke run whose test
        # side is empty cannot be scored, and one whose cells are single-class cannot be scored on a
        # classification metric at all. Density alone would select only the big donor regions.
        g["score"] = (np.minimum(g.npos, g.nneg) * 2.0
                      + g.ntest * 3.0
                      + g.n * 0.25)
        g = g.sort_values("score", ascending=False).head(budget)
    return g.reset_index(drop=True)


def fetch_tile(blat, blon, d0, d1, tries=4):
    """One ERDDAP griddap request for a 1-degree box over a date range. Returns a tidy frame."""
    lo0, lo1 = blon % 360, (blon + 1) % 360
    if lo1 <= lo0:                       # box crosses the 0/360 seam
        lo1 = lo0 + 1
    url = (BASE + ".csv?analysed_sst[(%s):1:(%s)][(%.3f):1:(%.3f)][(%.3f):1:(%.3f)]"
           % (d0.strftime("%Y-%m-%d"), d1.strftime("%Y-%m-%d"),
              blat, blat + 1, lo0, lo1))
    last = None
    for k in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=900)
            if r.status_code == 200:
                d = pd.read_csv(io.StringIO(r.text), skiprows=[1])
                d.columns = [c.strip() for c in d.columns]
                d = d.rename(columns={"analysed_sst": "sst"})
                d["time"] = pd.to_datetime(d["time"]).dt.tz_localize(None).dt.normalize()
                d["lon180"] = ((d.longitude + 180) % 360) - 180
                return d[["time", "latitude", "lon180", "sst"]].dropna(subset=["sst"])
            last = "HTTP %d" % r.status_code
            if r.status_code == 404:
                return pd.DataFrame(columns=["time", "latitude", "lon180", "sst"])
        except Exception as e:
            last = "%s: %s" % (type(e).__name__, str(e)[:90])
        if k < tries - 1:
            time.sleep(3 * (k + 1))
    raise RuntimeError("%s -- %s" % (url[:110], last))


def nearest_series(tile, sites):
    """Reduce a whole box to just the pixel series each site needs. The box itself is discarded."""
    if not len(tile):
        return pd.DataFrame()
    lats = np.sort(tile.latitude.unique())
    lons = np.sort(tile.lon180.unique())
    out = []
    for _, s in sites.iterrows():
        la = lats[np.abs(lats - s.lat).argmin()]
        lo = lons[np.abs(lons - s.lon).argmin()]
        sub = tile[(tile.latitude == la) & (tile.lon180 == lo)][["time", "sst"]].copy()
        if not len(sub):
            continue
        sub["site_lat"], sub["site_lon"] = s.lat, s.lon
        sub["px_lat"], sub["px_lon"] = la, lo
        sub["match_km"] = 111.0 * np.hypot(la - s.lat, (lo - s.lon) * np.cos(np.radians(s.lat)))
        out.append(sub)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--budget", type=int, default=150, help="max requests; 0 = all")
    ap.add_argument("--out", default=OUT)
    A = ap.parse_args()

    ev = pd.read_parquet(EV)
    os.makedirs(A.out, exist_ok=True)
    C = cells(ev, A.budget)
    log("=" * 76)
    log("%d request cells | %d events covered | est %.1f h at 19 s/request"
        % (len(C), int(C.n.sum()), len(C) * 19 / 3600))

    ev = ev.copy()
    ev["blat"] = np.floor(ev.lat).astype(int)
    ev["blon"] = np.floor(ev.lon).astype(int)
    ev["byr"] = ev.date.dt.year

    done = miss = 0
    t0 = time.time()
    for i, c in C.iterrows():
        key = "%+03d_%+04d_%d" % (c.blat, c.blon, c.byr)
        dest = os.path.join(A.out, key + ".parquet")
        if os.path.exists(dest):
            done += 1
            continue
        sites = ev[(ev.blat == c.blat) & (ev.blon == c.blon) & (ev.byr == c.byr)][
            ["lat", "lon"]].drop_duplicates()
        d0 = c.d0 - pd.Timedelta(days=LOOKBACK)
        try:
            tile = fetch_tile(int(c.blat), int(c.blon), d0, c.d1)
            ser = nearest_series(tile, sites)
            if len(ser):
                ser.to_parquet(dest, index=False)
                done += 1
            else:
                pd.DataFrame(columns=["time", "sst", "site_lat", "site_lon",
                                      "px_lat", "px_lon", "match_km"]).to_parquet(dest, index=False)
                miss += 1
            el = time.time() - t0
            log("%4d/%4d  %s  sites %2d  rows %6d  (%.0f%% done, %.1f min elapsed, ~%.1f min left)"
                % (i + 1, len(C), key, len(sites), len(ser), 100 * (i + 1) / len(C), el / 60,
                   (el / max(i + 1, 1)) * (len(C) - i - 1) / 60))
        except Exception as e:
            log("%4d/%4d  %s  FAILED %s" % (i + 1, len(C), key, str(e)[:90]))

    log("=" * 76)
    log("tiles cached %d | empty %d | cache dir %s" % (done, miss, A.out))
    n = sum(os.path.getsize(os.path.join(A.out, f)) for f in os.listdir(A.out))
    log("cache size %.1f MB -- re-run to resume; existing tiles are skipped" % (n / 1e6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
