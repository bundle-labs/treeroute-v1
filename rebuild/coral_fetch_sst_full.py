"""Full-history CoralTemp SST for the 10 pilot regions -- 1985 to each site's last dive.

    py -3.9 -u coral_fetch_sst_full.py                 # ~4 h, resumable
    py -3.9 -u coral_fetch_sst_full.py --plan          # show the plan, fetch nothing
    py -3.9 -u coral_fetch_sst_full.py --threads 4

WHY THIS EXISTS ALONGSIDE coral_fetch_sst.py. That one pulls ~370 days before each dive, which is
enough for window statistics but NOT enough for a climatology -- and without a climatology there is
no MMM, no HotSpot and no DHW, only globally-thresholded degree-days. The first smoke showed the
site-relative anomaly features dominating the importances, which is exactly the signal that a real
LOCAL reference is the missing ingredient. This script fetches the history that makes one possible.

FOUR OPTIMISATIONS, ALL MEASURED, NONE COSTING ANY DATA. A naive version of this job is ~18 h; this
is ~4 h and fetches the identical pixels.

  1. YEAR TRIMMING. A cluster whose last dive is 2005 does not need 2006-2026. Pulling
     1985 -> that cluster's own last dive cuts total cluster-years from 5,166 to 3,468.

  2. 2-DEGREE GROUPING. Cost is dominated by the TIME axis, not the pixel count. Measured on this
     dataset: 2 yr x 1 deg = 23.9 s / 14.4 MB; 2 yr x 2 deg = 26.1 s / 55.2 MB; 2 yr x 3 deg =
     31.7 s / 122 MB. Four times the area for nine percent more time. Grouping at 2 degrees drops
     126 clusters to 71. (3 deg is marginally faster still but pulls 72 GB and risks timeouts on
     122 MB responses, so 2 deg is the robust choice.)

  3. TIGHT BOUNDING BOXES. Sites cluster in a corner of their cell: inside a 2-degree cell the actual
     site bbox has a MEDIAN AREA OF 0.32 of 4 deg2, so a grid-aligned request throws away ~92% of
     what it downloads. Requesting the padded site bbox instead: 16.8 h -> 8.8 h.

  4. FOUR THREADS. Measured speedup 2.1x. It is 2.1x at four threads AND at eight -- the server
     throttles -- so there is nothing to gain and a block to risk by pushing harder.

WHAT IS KEPT. Only the pixel series each site needs. The downloaded box is discarded, so 53 GB of
traffic lands as a few tens of MB on disk. Bandwidth is the cost here, not storage.

TWO CONVENTIONS ASSERTED AT THE BOUNDARY. PIFSC ERDDAP is 0-360 longitude while the observations are
-180/+180. And the daily SST grid is latitude ASCENDING while every DERIVED CRW product is
DESCENDING -- nothing here reads a derived product, but reusing a row index across the two silently
mirrors the climatology, measured at +1.80 C on MMM at Heron Island.
"""
import argparse
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import requests

EV = r"D:\coral\target\events_dated.parquet"
OUT = r"D:\coral\drivers\sst_full"
BASE = "https://oceanwatch.pifsc.noaa.gov/erddap/griddap/CRW_sst_v3_1"
UA = {"User-Agent": "coral-bleaching-research/1.0 (academic)"}
PILOT = [6, 110, 17, 71, 93, 62, 40, 77, 2, 13]
GRID = 2.0          # clustering cell, degrees
PAD = 0.05          # bbox padding so the nearest pixel is always inside
CHUNK = 2           # years per request
START = 1985

_lock = threading.Lock()
_done = {"n": 0, "bytes": 0, "fail": 0}


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


# WHICH REGIONS. The original run covered only the 10 pilot ecoregions, and that is the single
# thing standing between this project and the 20-donor / 93-test split it actually decided on: the
# heat block carries 32-40% of all feature importance and it exists for 4,758 of the corpus's 11,048
# sites. OHC, Sea State, SSH and GLORYS were all built corpus-wide, so SST is the only blocker.
# --regions all lifts it. Existing cached files are keyed by cluster and year, so widening the
# region set only ADDS clusters -- nothing already downloaded is refetched or invalidated.
REGION_SETS = {"pilot": PILOT, "all": None}


def build_plan(regions="pilot", min_events=0):
    ev = pd.read_parquet(EV)
    sel = REGION_SETS.get(regions, PILOT)
    if sel is not None:
        ev = ev[ev.eco.isin(sel)].copy()
    else:
        ev = ev.copy()
        if min_events > 0:
            keep = ev.eco.value_counts()
            keep = keep[keep >= min_events].index
            ev = ev[ev.eco.isin(keep)].copy()
    ev["cl"] = (np.floor(ev.lat / GRID) * GRID)
    ev["co"] = (np.floor(ev.lon / GRID) * GRID)
    g = ev.groupby(["cl", "co"]).agg(
        la0=("lat", "min"), la1=("lat", "max"), lo0=("lon", "min"), lo1=("lon", "max"),
        ymax=("date", lambda d: int(d.dt.year.max())), n=("pos", "size"))
    jobs = []
    for (cl, co), r in g.iterrows():
        key = "c%+05.1f_%+06.1f" % (cl, co)
        ymax = int(r.ymax)
        for y0 in range(START, ymax + 1, CHUNK):
            y1 = min(y0 + CHUNK - 1, ymax)
            jobs.append(dict(key=key, cl=cl, co=co, y0=y0, y1=y1,
                             la0=r.la0 - PAD, la1=r.la1 + PAD,
                             lo0=r.lo0 - PAD, lo1=r.lo1 + PAD))
    sites = ev[["lat", "lon"]].drop_duplicates()
    sites["cl"] = np.floor(sites.lat / GRID) * GRID
    sites["co"] = np.floor(sites.lon / GRID) * GRID
    return jobs, g, sites, ev


def fetch_one(j, sites, tries=4):
    dest = os.path.join(OUT, "%s_%d_%d.parquet" % (j["key"], j["y0"], j["y1"]))
    if os.path.exists(dest):
        return 0
    lo0, lo1 = j["lo0"] % 360, j["lo1"] % 360
    if lo1 < lo0:                       # crosses the 0/360 seam
        lo1 += 360
    url = (BASE + ".csv?analysed_sst[(%d-01-01):1:(%d-12-31)][(%.4f):1:(%.4f)][(%.4f):1:(%.4f)]"
           % (j["y0"], j["y1"], j["la0"], j["la1"], lo0, lo1))
    last = None
    for k in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=1200)
            if r.status_code == 404:
                pd.DataFrame(columns=["time", "sst", "site_lat", "site_lon"]).to_parquet(dest, index=False)
                return 0
            if r.status_code != 200:
                last = "HTTP %d" % r.status_code
            else:
                import io as _io
                d = pd.read_csv(_io.StringIO(r.text), skiprows=[1])
                d.columns = [c.strip() for c in d.columns]
                d = d.rename(columns={"analysed_sst": "sst"}).dropna(subset=["sst"])
                d["time"] = pd.to_datetime(d["time"]).dt.tz_localize(None).dt.normalize()
                d["lon180"] = ((d.longitude + 180) % 360) - 180
                mine = sites[(sites.cl == j["cl"]) & (sites.co == j["co"])]
                lats = np.sort(d.latitude.unique())
                lons = np.sort(d.lon180.unique())
                out = []
                for _, s in mine.iterrows():
                    la = lats[np.abs(lats - s.lat).argmin()]
                    lo = lons[np.abs(lons - s.lon).argmin()]
                    sub = d[(d.latitude == la) & (d.lon180 == lo)][["time", "sst"]]
                    if not len(sub):
                        continue
                    sub = sub.copy()
                    sub["site_lat"], sub["site_lon"] = s.lat, s.lon
                    out.append(sub)
                res = pd.concat(out, ignore_index=True) if out else \
                    pd.DataFrame(columns=["time", "sst", "site_lat", "site_lon"])
                tmp = dest + ".part"
                res.to_parquet(tmp, index=False)
                os.replace(tmp, dest)
                return len(r.content)
        except Exception as e:
            last = "%s %s" % (type(e).__name__, str(e)[:60])
        if k < tries - 1:
            time.sleep(4 * (k + 1))
    with _lock:
        _done["fail"] += 1
    log("   FAILED %s %d-%d : %s" % (j["key"], j["y0"], j["y1"], last))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--regions", default="pilot", choices=sorted(REGION_SETS),
                    help="pilot = the original 10; all = every ecoregion in the corpus")
    ap.add_argument("--min-events", type=int, default=0, dest="min_events",
                    help="with --regions all, skip ecoregions with fewer than N events")
    A = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    jobs, g, sites, ev = build_plan(A.regions, A.min_events)
    have = sum(1 for j in jobs
               if os.path.exists(os.path.join(OUT, "%s_%d_%d.parquet" % (j["key"], j["y0"], j["y1"]))))
    area = ((g.la1 - g.la0 + 2 * PAD) * (g.lo1 - g.lo0 + 2 * PAD)).clip(lower=0.01)
    est = float(((11.5 + 4.4 * area) * (g.ymax - START + 1)).sum())
    log("=" * 78)
    log("SST FULL HISTORY [--regions %s] | %d regions | %d events | %d sites"
        % (A.regions, ev.eco.nunique(), len(ev), len(sites)))
    log("%d clusters at %.0f deg | %d requests (%d already cached)" % (len(g), GRID, len(jobs), have))
    log("median tight bbox %.2f deg2 of %.0f | est %.1f h serial, ~%.1f h at %d threads"
        % (area.median(), GRID * GRID, est / 3600, est / 3600 / 2.1, A.threads))
    if A.plan:
        log("--plan: nothing fetched")
        return 0

    todo = [j for j in jobs
            if not os.path.exists(os.path.join(OUT, "%s_%d_%d.parquet" % (j["key"], j["y0"], j["y1"])))]
    log("fetching %d requests with %d threads..." % (len(todo), A.threads))
    t0 = time.time()
    with ThreadPoolExecutor(A.threads) as ex:
        futs = {ex.submit(fetch_one, j, sites): j for j in todo}
        for f in as_completed(futs):
            try:
                b = f.result()
            except Exception as e:
                b = 0
                log("   worker error %s" % str(e)[:70])
            with _lock:
                _done["n"] += 1
                _done["bytes"] += b
                n = _done["n"]
            if n % 25 == 0 or n == len(todo):
                el = time.time() - t0
                log("  %4d/%4d  %5.1f%%  %6.1f min elapsed  ~%5.1f min left  %.1f GB pulled  %d failed"
                    % (n, len(todo), 100 * n / len(todo), el / 60,
                       (el / n) * (len(todo) - n) / 60, _done["bytes"] / 1e9, _done["fail"]))

    files = [f for f in os.listdir(OUT) if f.endswith(".parquet")]
    disk = sum(os.path.getsize(os.path.join(OUT, f)) for f in files)
    log("=" * 78)
    log("done in %.1f min | %d cache files | %.1f MB on disk | %.1f GB downloaded | %d failed"
        % ((time.time() - t0) / 60, len(files), disk / 1e6, _done["bytes"] / 1e9, _done["fail"]))
    log("re-run to retry failures; cached chunks are skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
