"""Extension #2 -- the small no-auth drivers (solar, gas-flaring, CIrrMap250). Writes to D:\\ndvi_drivers\\.
Resumable. (GHSL urban-age dropped: its JRC FTP index won't list files, and it's redundant with the panel's
existing built_surface_fraction -- grab a single epoch by hand from jeodpp.jrc.ec.europa.eu if you want it.)

  solar      : Kruitwagen 2021 global PV polygons (GeoJSON + inventory zip)  ~360 MB   [LOW value -- contested effect]
  flaring    : EOG VIIRS per-year gas-flaring xlsx (fossil-extraction proxy) ~10 MB    [MED -- ~2012-2022, annual]
  cirrmap    : CIrrMap250 China-only irrigation 2000-2020 (--cirrmap)        ~2.5 GB   [LOW -- China regions only]

  py -3.9 presplit_cc/download_drivers_extra2.py            # solar + gas-flaring
  py -3.9 presplit_cc/download_drivers_extra2.py --cirrmap  # ALSO CIrrMap250 (2.5 GB, China only)
"""
import os
import re
import sys
import time

import requests

ROOT = r"D:\ndvi_drivers"
UA = {"User-Agent": "Mozilla/5.0 (research fetch)"}
CIRR = "--cirrmap" in sys.argv


def download(url, path, retries=4):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    name = os.path.basename(path)
    rem = 0
    try:
        h = requests.head(url, headers=UA, allow_redirects=True, timeout=30)
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
            r = requests.get(url, headers=hdr, stream=True, allow_redirects=True, timeout=120)
            mode = "ab" if (pos and r.status_code == 206) else "wb"
            got = pos if mode == "ab" else 0
            with open(path, mode) as f:
                for chunk in r.iter_content(1 << 20):
                    if chunk:
                        f.write(chunk); got += len(chunk)
            if got < 500:
                print(f"  WARN tiny {name} ({got}B)"); return "fail"
            print(f"  OK {name} ({got/1e6:.1f} MB)"); return "ok"
        except Exception as e:
            print(f"  retry {a+1}/{retries} {name}: {type(e).__name__} {str(e)[:60]}"); time.sleep(4 * (a + 1))
    print(f"  FAIL {name}"); return "fail"


def solar():
    print("\n[solar] Kruitwagen 2021 global PV polygons (Zenodo 5005868):")
    t = {}
    for fn in ("predicted_set.geojson", "global_pv_inventory_all.zip"):
        u = f"https://zenodo.org/api/records/5005868/files/{fn}/content"
        r = download(u, os.path.join(ROOT, "solar", fn)); t[r] = t.get(r, 0) + 1
    return t


def flaring():
    print("\n[flaring] EOG VIIRS gas-flaring per-year xlsx (dir-scrape):")
    t = {}
    try:
        idx = requests.get("https://eogdata.mines.edu/global_flare_data/", headers=UA, timeout=45).text
    except Exception as e:
        print(f"  dir index err: {e}"); return {"fail": 1}
    xlsx = sorted(set(re.findall(r'href=[\"\']([^\"\']*VIIRS_Global_flaring[^\"\']*\.xlsx)[\"\']', idx)))
    print(f"  {len(xlsx)} per-year files found")
    for fn in xlsx:
        u = "https://eogdata.mines.edu/global_flare_data/" + fn.split("/")[-1]
        r = download(u, os.path.join(ROOT, "flaring", fn.split("/")[-1])); t[r] = t.get(r, 0) + 1
    return t


def cirrmap():
    print("\n[cirrmap] CIrrMap250 China irrigation 2000-2020 (figshare 24814293):")
    t = {}
    try:
        files = requests.get("https://api.figshare.com/v2/articles/24814293", headers=UA, timeout=45).json()["files"]
    except Exception as e:
        print(f"  figshare API err: {e}"); return {"fail": 1}
    for f in files:
        if f["name"].endswith(".tif"):
            r = download(f["download_url"], os.path.join(ROOT, "cirrmap", f["name"])); t[r] = t.get(r, 0) + 1
    return t


def main():
    print(f"=== driver extension #2 -> {ROOT}  {'[+CIrrMap 2.5GB]' if CIRR else ''} ===")
    tally = {}
    for part in (solar(), flaring(), *((cirrmap(),) if CIRR else ())):
        for k, v in part.items():
            tally[k] = tally.get(k, 0) + v
    print("\n=== SUMMARY ===")
    for k in ("ok", "skip", "fail"):
        if tally.get(k):
            print(f"  {k}: {tally[k]}")
    if not CIRR:
        print("  (CIrrMap250 skipped -- add --cirrmap for the 2.5 GB China-only irrigation series.)")
    print("  (GHSL urban-age NOT scripted -- redundant w/ built_surface_fraction; grab a single epoch by hand if needed.)")


if __name__ == "__main__":
    main()
