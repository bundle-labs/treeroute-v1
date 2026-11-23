"""Extension fetcher -- the high-value drivers the main script couldn't script directly.
Writes to D:\\ndvi_drivers\\. Resumable (skips complete files). Run in YOUR terminal (multi-GB).

  N-deposition  : ISIMIP2a NHx+NOy, MONTHLY, covers 2002-2016 (2017-2023 absent). Plain HTTP.   ~300 MB
  MERRA-2 ozone : M2TMNXSLV TO3 = TOTAL-COLUMN ozone (UV proxy, NOT surface O3), MONTHLY 2002-2023,
                  via Earthdata .netrc + OPeNDAP variable subset (TO3 only -> ~1 MB/mo).            ~260 MB
  Hansen        : forest-loss lossyear, 262 tiles covering the 133 regions (--hansen). GCS, no auth. ~26 GB

  py -3.9 presplit_cc/download_drivers_extra.py            # N-dep + MERRA-2 ozone
  py -3.9 presplit_cc/download_drivers_extra.py --hansen   # ALSO the 26 GB Hansen lossyear tiles
"""
import glob
import math
import os
import sys
import time

import requests

ROOT = r"D:\ndvi_drivers"
UA = {"User-Agent": "Mozilla/5.0 (research fetch)"}
HANSEN = "--hansen" in sys.argv


def download(url, path, session=None, retries=4):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    name = os.path.basename(path)
    get = (session or requests).get
    rem = 0
    try:
        h = (session or requests).head(url, headers=UA, allow_redirects=True, timeout=30)
        rem = int(h.headers.get("Content-Length", 0))
    except Exception:
        pass
    if os.path.exists(path) and rem and os.path.getsize(path) >= rem:
        print(f"  skip {name}"); return "skip"
    for a in range(retries):
        try:
            pos = os.path.getsize(path) if os.path.exists(path) else 0
            hdr = dict(UA)
            if pos:
                hdr["Range"] = f"bytes={pos}-"
            r = get(url, headers=hdr, stream=True, allow_redirects=True, timeout=120)
            mode = "ab" if (pos and r.status_code == 206) else "wb"
            got = pos if mode == "ab" else 0
            with open(path, mode) as f:
                for chunk in r.iter_content(1 << 20):
                    if chunk:
                        f.write(chunk); got += len(chunk)
            if got < 500:                                    # OPeNDAP error pages are tiny
                print(f"  WARN tiny file {name} ({got} B) -- check auth/var"); return "fail"
            print(f"  OK {name} ({got/1e6:.1f} MB)"); return "ok"
        except Exception as e:
            print(f"  retry {a+1}/{retries} {name}: {type(e).__name__} {str(e)[:70]}"); time.sleep(4 * (a + 1))
    print(f"  FAIL {name}"); return "fail"


def ndep():
    print("\n[ndep] ISIMIP2a NHx+NOy monthly 1860-2016 (covers 2002-2016):")
    base = "https://files.isimip.org/ISIMIP2a/InputData/landuse_humaninfluences/n-deposition/histsoc/"
    t = {}
    for v in ("nhx", "noy"):
        fn = f"ndep_{v}_histsoc_monthly_1860_2016.nc4"
        r = download(base + fn, os.path.join(ROOT, "ndep", fn))
        t[r] = t.get(r, 0) + 1
    return t


def merra2_ozone():
    print("\n[ozone] MERRA-2 M2TMNXSLV TO3 (total-column ozone) monthly 2002-2023 via Earthdata OPeNDAP:")
    S401 = {(2020, 9), (2021, 6), (2021, 7), (2021, 8), (2021, 9)}   # 2020 reprocessing -> stream 401, NOT 400
    HDF = bytes([0x89]) + b"HDF"                              # valid netcdf4 magic
    s = requests.Session(); s.trust_env = True               # uses ~/.netrc for urs.earthdata.nasa.gov
    t = {}
    for y in range(2002, 2024):
        for m in range(1, 13):
            path = os.path.join(ROOT, "ozone", f"merra2_TO3_{y}{m:02d}.nc4")
            if os.path.exists(path) and os.path.getsize(path) > 100000 and open(path, "rb").read(4) == HDF:
                t["skip"] = t.get("skip", 0) + 1; continue   # valid file already there (OPeNDAP gives no size)
            stream = 401 if (y, m) in S401 else (300 if y <= 2010 else 400)
            url = (f"https://goldsmr4.gesdisc.eosdis.nasa.gov/opendap/MERRA2_MONTHLY/M2TMNXSLV.5.12.4/"
                   f"{y}/MERRA2_{stream}.tavgM_2d_slv_Nx.{y}{m:02d}.nc4.nc4?TO3,lat,lon,time")
            r = download(url, path, session=s)
            if r == "ok" and (not os.path.exists(path) or open(path, "rb").read(4) != HDF):
                if os.path.exists(path):
                    os.remove(path)                          # an OPeNDAP error page, not real data
                r = "fail"
            t[r] = t.get(r, 0) + 1
    return t


def hansen():
    print("\n[hansen] forest-loss lossyear tiles covering the 133 regions (GCS, no auth):")
    import yaml
    import pandas as pd
    HERE = os.path.dirname(os.path.abspath(__file__))
    cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
    mfiles = []
    for d in (cfg["data"]["master_dir"], cfg["forecast"]["regions_dir"]):
        mfiles += [p for p in glob.glob(os.path.join(d, "*_master_*.parquet")) if ".bak." not in p]

    def tlat(p): v = math.ceil(p / 10) * 10; return f"{abs(v):02d}{'N' if v >= 0 else 'S'}"
    def tlon(l): v = math.floor(l / 10) * 10; return f"{abs(v):03d}{'E' if v >= 0 else 'W'}"
    tiles = set()
    for p in mfiles:
        d = pd.read_parquet(p, columns=["lon", "lat"])
        for la in range(int(math.floor(d.lat.min() / 10) * 10), int(math.ceil(d.lat.max() / 10) * 10) + 1, 10):
            for lo in range(int(math.floor(d.lon.min() / 10) * 10), int(math.ceil(d.lon.max() / 10) * 10) + 1, 10):
                tiles.add((tlat(la + 5), tlon(lo)))
    tiles = sorted(tiles)
    print(f"  {len(tiles)} tiles (~111 MB each ~= {len(tiles)*0.111:.0f} GB; ocean/>80N tiles don't exist -> 'notile')")
    t = {}
    for la, lo in tiles:
        path = os.path.join(ROOT, "hansen", f"lossyear_{la}_{lo}.tif")
        if os.path.exists(path) and open(path, "rb").read(2) in (b"II", b"MM"):
            t["skip"] = t.get("skip", 0) + 1; continue        # valid GeoTIFF already there
        u = (f"https://storage.googleapis.com/earthenginepartners-hansen/GFC-2023-v1.11/"
             f"Hansen_GFC-2023-v1.11_lossyear_{la}_{lo}.tif")
        r = download(u, path)
        if os.path.exists(path) and open(path, "rb").read(2) not in (b"II", b"MM"):
            os.remove(path)                                   # 404 XML -> Hansen has no land tile here (ocean / >80N)
            r = "notile"
        t[r] = t.get(r, 0) + 1
    return t


def main():
    print(f"=== driver extension fetch -> {ROOT}  {'[+HANSEN 26GB]' if HANSEN else ''} ===")
    tally = {}
    for part in (ndep(), merra2_ozone(), *( (hansen(),) if HANSEN else () )):
        for k, v in part.items():
            tally[k] = tally.get(k, 0) + v
    print("\n=== SUMMARY ===")
    for k in ("ok", "skip", "fail"):
        if tally.get(k):
            print(f"  {k}: {tally[k]}")
    if not HANSEN:
        print("  (Hansen forest-loss skipped -- add --hansen for the 26 GB of lossyear tiles.)")


if __name__ == "__main__":
    main()
