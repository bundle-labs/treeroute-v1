"""Extension #3 -- the 3 'gated' drivers that turned out to have OPEN back-doors (no registration).
Writes to D:\\ndvi_drivers\\. Resumable.

  WDPA protected areas : wcmc.io permalink -> full global File-GDB zip (~1.8 GB). Terms: attribution, non-commercial.
  Coal plants (open)   : KAPSARC mirror CSV (coords+capacity+status; NO commission/retire dates -> static).
  Fertilizer (fallback): Lu & Tian N+P application zip (~9 MB; 0.5 deg, 1900-2013 -> covers 2002-2013 only).

  py -3.9 presplit_cc/download_drivers_extra3.py
"""
import os
import sys
import time

import requests

ROOT = r"D:\ndvi_drivers"
UA = {"User-Agent": "Mozilla/5.0 (research fetch)"}

JOBS = [
    ("protected_areas", "WDPA_current_global.zip",
     "http://wcmc.io/wdpa_current_release", 1794),
    ("energy", "global_coal_plant_tracker_kapsarc.csv",
     "https://datasource.kapsarc.org/api/explore/v2.1/catalog/datasets/global-coal-plant-tracker/exports/csv", 3),
    ("fertilizer", "Lu-Tian_2016_NP_fertilizer.zip",
     "https://store.pangaea.de/Publications/Lu_Tian_2016/Lu-Tian_2016.zip", 9),
]


def download(url, path, mb, retries=4):
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


def main():
    print(f"=== driver extension #3 (open back-doors) -> {ROOT} ===")
    t = {}
    for cat, fn, url, mb in JOBS:
        print(f"\n[{cat}] {fn}  (~{mb} MB)")
        r = download(url, os.path.join(ROOT, cat, fn), mb)
        t[r] = t.get(r, 0) + 1
    print("\n=== SUMMARY ===")
    for k in ("ok", "skip", "fail"):
        if t.get(k):
            print(f"  {k}: {t[k]}")


if __name__ == "__main__":
    main()
