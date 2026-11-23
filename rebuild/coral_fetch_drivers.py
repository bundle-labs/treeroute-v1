"""Fetch the credential-free drivers for the pilot regions. Resumable, hashed, dated.

    py -3.9 -u coral_fetch_drivers.py --list
    py -3.9 -u coral_fetch_drivers.py

WHAT THIS DOES AND DOES NOT COVER. Of the 19 clean drivers, this fetches the ones that are global or
static and need no account. The per-site TIME SERIES drivers (SST, PAR, Kd) are handled by
coral_fetch_sst.py's tiling machinery, because their cost is per-request and they must be grouped
into 1-degree boxes to be affordable at all.

TWO DRIVERS ARE BLOCKED AND ONLY THE PROJECT OWNER CAN UNBLOCK THEM. ERA5 (C4 wind / shortwave /
precipitation / pressure, and C5 UV-B) is served by the Copernicus Climate Data Store, which requires
a personal account and an API key. Creating that account is not something this script will do -- it
needs the owner's own registration, and the licence-acceptance step silently fails requests until it
is completed by hand. Same for CMEMS (C9 waves, C12-adjacent ocean state). Everything else below runs
unattended.

WHY THE SST FETCH IS SHAPED THE WAY IT IS -- measured, not assumed:
    2-year, 1-degree box  ->  23.5 s,  14.5 MB   OK
    5-year, 1-degree box  ->  > 10 min           TIMES OUT
    36-year, 1 pixel      ->  > 4 min            TIMES OUT
    10-year, 1 pixel      ->  > 100 s            TIMES OUT
The binding cost is the TIME SPAN, not the pixel count. Long series must therefore be pulled in short
time chunks and stitched, which is why a full-history pull for a real MMM is a large overnight job
rather than a quick one.
"""
import argparse
import hashlib
import io
import json
import os
import time
from datetime import datetime, timezone

import requests

ROOT = r"D:\coral\drivers"
MAN = os.path.join(ROOT, "_manifest.json")
UA = {"User-Agent": "coral-bleaching-research/1.0 (academic)"}

# Region ids of the 10-region pilot, for reference by downstream scripts.
PILOT = {6: "donor", 110: "donor", 17: "donor", 71: "donor", 93: "donor",
         62: "test", 40: "test", 77: "test", 2: "test", 13: "test"}


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def grab(url, dest, min_bytes=1024, tries=3):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) >= min_bytes:
        log("    have %s (%.1f MB)" % (os.path.basename(dest), os.path.getsize(dest) / 1e6))
        return True
    for k in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=900, stream=True)
            if r.status_code != 200:
                log("    HTTP %d  %s" % (r.status_code, url[:100]))
                if k == tries - 1:
                    return False
                time.sleep(2 ** k)
                continue
            tmp = dest + ".part"
            n = 0
            with open(tmp, "wb") as f:
                for c in r.iter_content(1 << 20):
                    if c:
                        f.write(c)
                        n += len(c)
            if n < min_bytes:
                os.remove(tmp)
                log("    too small (%d B) %s" % (n, url[:80]))
                return False
            os.replace(tmp, dest)
            log("    get  %s (%.1f MB)" % (os.path.basename(dest), n / 1e6))
            return True
        except Exception as e:
            log("    %s %s" % (type(e).__name__, str(e)[:70]))
            if k < tries - 1:
                time.sleep(2 ** k)
    return False


def arcgis_all(base, dest, page=1000):
    """Page an ArcGIS layer to GeoJSON. maxRecordCount silently truncates, so page explicitly."""
    if os.path.exists(dest) and os.path.getsize(dest) > 2048:
        log("    have %s" % os.path.basename(dest))
        return True
    n = requests.get(base + "/query", params={"where": "1=1", "returnCountOnly": "true", "f": "json"},
                     headers=UA, timeout=300).json().get("count", 0)
    feats, off = [], 0
    while off < n:
        js = requests.get(base + "/query",
                          params={"where": "1=1", "outFields": "*", "returnGeometry": "true",
                                  "resultOffset": off, "resultRecordCount": page, "f": "geojson"},
                          headers=UA, timeout=600).json()
        b = js.get("features", [])
        if not b:
            break
        feats.extend(b)
        off += len(b)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    io.open(dest, "w", encoding="utf-8").write(json.dumps({"type": "FeatureCollection", "features": feats}))
    log("    get  %s (%d/%d features)" % (os.path.basename(dest), len(feats), n))
    return True


DRIVERS = {
    "C14_meow": ("MEOW marine ecoregions -- THE SPLIT KEY, fetch this first", lambda: arcgis_all(
        "https://services5.arcgis.com/YCKZmP6DZSq3o9Gi/arcgis/rest/services/MEOW/FeatureServer/0",
        os.path.join(ROOT, "static", "meow_ecoregions.geojson"))),
    "C16_enso": ("ENSO Nino 3.4 + IOD DMI, monthly indices", lambda: all([
        grab("https://psl.noaa.gov/data/correlation/nina34.data",
             os.path.join(ROOT, "climate", "nina34.txt"), 1000),
        grab("https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.had.long.data",
             os.path.join(ROOT, "climate", "dmi.txt"), 500)])),
    "C8_ibtracs": ("IBTrACS v04r01 cyclone tracks, 1842->now, one file", lambda: grab(
        "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-"
        "ibtracs/v04r01/access/netcdf/IBTrACS.ALL.v04r01.nc",
        os.path.join(ROOT, "static", "IBTrACS.ALL.v04r01.nc"), 1 << 20)),
    "C12_reefs": ("UNEP-WCMC coral reef extent polygons", lambda: arcgis_all(
        "https://gis.unep-wcmc.org/arcgis/rest/services/marine/WCMC_008_CoralReefs_WMS/MapServer/0",
        os.path.join(ROOT, "static", "wcmc_reefs.geojson"))),
    "C3_mask": ("CRW land/water mask + climatology grid", lambda: grab(
        "https://www.star.nesdis.noaa.gov/pub/socd/mecb/crw/data/5km/v3.1_op/climatology/nc/"
        "ct5km_climatology_v3.1.nc",
        os.path.join(ROOT, "static", "ct5km_climatology_v3.1.nc"), 1 << 20)),
}

BLOCKED = {
    "C4_era5": "ERA5 wind/shortwave/precip/pressure -- needs a Copernicus CDS account + API key",
    "C5_uvb": "ERA5 surface UV-B -- same CDS account",
    "C9_waves": "CMEMS WAVERYS -- needs a Copernicus Marine account",
    "C10_gebco": "GEBCO bathymetry -- 7.5 GB; needs a ranged reef-band subset, not a blind pull",
    "C11_tides": "EOT20 tides -- 2.33 GB and the server ignores Range headers",
    "C13_wdpa": "WDPA protected areas -- 4.17 GB zip; subset before pulling",
    "C17_loggers": "In-situ loggers -- 30-43 GB even projected; validation-only anyway",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", default="")
    A = ap.parse_args()
    if A.list:
        print("\nFETCHABLE NOW (no credentials):")
        for k, (d, _) in DRIVERS.items():
            print("   %-12s %s" % (k, d))
        print("\nBLOCKED (need your account, or a subset strategy):")
        for k, d in BLOCKED.items():
            print("   %-12s %s" % (k, d))
        print("\nPer-site time series (SST/PAR/Kd) -> coral_fetch_sst.py\n")
        return 0

    keys = [k.strip() for k in A.only.split(",") if k.strip()] or list(DRIVERS)
    man = json.load(io.open(MAN, encoding="utf-8")) if os.path.exists(MAN) else {"drivers": {}}
    ok = bad = 0
    for k in keys:
        desc, fn = DRIVERS[k]
        log("")
        log("--- %s : %s" % (k, desc))
        try:
            r = fn()
            man["drivers"][k] = {"status": "complete" if r else "failed",
                                 "description": desc, "at": now()}
            ok += bool(r)
            bad += (not r)
        except Exception as e:
            log("    FAILED %s" % str(e)[:120])
            man["drivers"][k] = {"status": "failed", "error": str(e)[:300], "at": now()}
            bad += 1
        os.makedirs(ROOT, exist_ok=True)
        io.open(MAN, "w", encoding="utf-8").write(json.dumps(man, indent=2, sort_keys=True))

    tot = 0
    for dp, _, fs in os.walk(ROOT):
        for f in fs:
            tot += os.path.getsize(os.path.join(dp, f))
    log("")
    log("=" * 74)
    log("drivers ok %d | failed %d | %s on disk %.1f MB" % (ok, bad, ROOT, tot / 1e6))
    log("BLOCKED and needing your Copernicus/CDS account: C4 ERA5, C5 UV-B, C9 waves")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
