"""Ingest monthly multi-timescale SPEI (drought index) from CSIC SPEIbase v2.9 (non-GEE)
and sample onto the 4km cells -> per-region monthly parquet [cell_id, year, month, spei_<ts>m].

SPEIbase: global 0.5deg, monthly, 1901-present, one NetCDF per accumulation timescale
(spei01..spei48). Source = Digital.CSIC bitstreams (handle 10261/332007), discovered at
runtime (so no hard-coded version-specific URLs). Each file ~1.5 GB, so this is a multi-GB
pull (default 5 scales ~ 7.5 GB) -- run it in YOUR terminal; it streams one file at a time to
--tmp on the HDD, samples, and (by default) keeps the file so a re-run resumes for free.

Sampling: each 4km cell takes its containing 0.5deg SPEI cell (validated grid_indices). Time
is mapped via num2date (robust to the file's 'days since ...' units). Ocean/missing -> NaN.

  py -3.9 presplit_cc/ingest_spei_monthly.py --selftest                 # geometry, no data
  py -3.9 presplit_cc/ingest_spei_monthly.py --probe                    # discover URLs + probe 1 file structure (~1.5GB)
  py -3.9 presplit_cc/ingest_spei_monthly.py --scales 12 --region thar_desert   # one scale/region test
  py -3.9 presplit_cc/ingest_spei_monthly.py --out OUT --tmp TMP        # full: scales 1,3,6,12,24
"""
import glob
import os
import re
import sys
import tempfile
import time

import numpy as np
import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ingest_luh3_drivers import grid_indices          # noqa: E402  reuse validated geometry

cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
CC = "cell_id"
HANDLE = "10261/332007"                                 # SPEIbase v2.9
PAGE = f"https://digital.csic.es/handle/{HANDLE}"
BASE = "https://digital.csic.es"
YEARS = list(range(2002, 2024))
TARGET = [(y, m) for y in YEARS for m in range(1, 13)]  # 264 (year, month) in order


def discover_urls():
    """Parse the CSIC handle page -> {timescale_int: full_nc_url}."""
    import requests
    t = requests.get(PAGE, timeout=60).text
    out = {}
    for m in re.finditer(r"(/bitstream/" + re.escape(HANDLE) + r"/\d+/spei(\d+)\.nc)", t):
        out[int(m.group(2))] = BASE + m.group(1)
    return out


def _open(url, path, retries=5):
    from netCDF4 import Dataset
    import requests
    last = None
    for a in range(retries):
        try:
            if not os.path.exists(path) or os.path.getsize(path) < 1_000_000:
                part = path + ".part"
                with requests.get(url, stream=True, timeout=1200) as r:
                    r.raise_for_status()
                    with open(part, "wb") as fh:
                        for chunk in r.iter_content(chunk_size=1 << 20):
                            fh.write(chunk)
                os.replace(part, path)
            return Dataset(path)
        except Exception as e:
            last = e
            for p in (path, path + ".part"):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
            time.sleep(3 * (a + 1))
    raise last


def _selftest():
    glon = -179.75 + 0.5 * np.arange(720)
    glat = 89.75 - 0.5 * np.arange(360)
    ok = all(abs(glon[grid_indices([lo], [la], glon, glat)[0][0]] - lo) <= 0.25 + 1e-9
             and abs(glat[grid_indices([lo], [la], glon, glat)[1][0]] - la) <= 0.25 + 1e-9
             for lo, la in [(-64.98, -5.01), (0, 0), (115.3, 42.7), (-179.6, 89.6)])
    print("selftest:", "PASS (0.5deg containing-cell sampling)" if ok else "FAIL")
    return 0 if ok else 1


def _timemap(nc):
    from netCDF4 import num2date
    t = nc.variables["time"]
    dates = num2date(t[:], t.units, getattr(t, "calendar", "standard"))
    return {(d.year, d.month): i for i, d in enumerate(dates)}


def _probe(tmp):
    urls = discover_urls()
    print("discovered scales:", sorted(urls))
    ts = 12 if 12 in urls else sorted(urls)[0]
    nc = _open(urls[ts], os.path.join(tmp, f"spei{ts:02d}.nc"))
    print("dims:", {d: len(nc.dimensions[d]) for d in nc.dimensions})
    print("vars:", [v for v in nc.variables])
    tm = _timemap(nc)
    print("time covers 2002-01..2023-12?", (2002, 1) in tm and (2023, 12) in tm)
    var = "spei" if "spei" in nc.variables else [v for v in nc.variables if nc.variables[v].ndim == 3][0]
    print("data var:", var, " lat[0:2]", [float(x) for x in nc.variables["lat"][:2]],
          " lon[0:2]", [float(x) for x in nc.variables["lon"][:2]])
    nc.close()
    print("probe: PASS")
    return 0


def main(argv):
    if "--selftest" in argv:
        return _selftest()

    def opt(flag, d=None):
        return argv[argv.index(flag) + 1] if flag in argv else d
    tmp = opt("--tmp", os.path.join(tempfile.gettempdir(), "spei_dl"))
    os.makedirs(tmp, exist_ok=True)
    if "--probe" in argv:
        return _probe(tmp)

    scales = [int(s) for s in opt("--scales", "1,3,6,12,24").split(",")]
    only = opt("--region"); limit = opt("--limit")
    out_dir = opt("--out", os.path.join(os.path.dirname(cfg["data"]["master_dir"]), "spei_monthly"))
    keep = "--no-keep" not in argv
    os.makedirs(out_dir, exist_ok=True)

    urls = discover_urls()
    missing = [s for s in scales if s not in urls]
    if missing:
        print(f"WARNING: scales not found on CSIC page: {missing} (available: {sorted(urls)})")
    scales = [s for s in scales if s in urls]

    masters = {}
    for d in (cfg["data"]["master_dir"], cfg["forecast"]["regions_dir"]):
        for p in glob.glob(os.path.join(d, "*_master_*.parquet")):
            if ".bak." not in p:
                masters.setdefault(os.path.basename(p).split("_master_")[0], p)
    regs = sorted(masters)
    if only:
        regs = [r for r in regs if r == only]
    if limit:
        regs = regs[:int(limit)]
    cells = {r: pd.read_parquet(masters[r], columns=[CC, "lon", "lat"]).drop_duplicates(CC) for r in regs}
    idx = {}
    print(f"SPEI -> {len(regs)} regions, scales={scales}, 264 months", flush=True)

    buf = {r: {} for r in regs}                          # region -> scale -> (ncell, 264)
    for ts in scales:
        nc = _open(urls[ts], os.path.join(tmp, f"spei{ts:02d}.nc"))
        if not idx:
            glat = np.asarray(nc.variables["lat"][:]); glon = np.asarray(nc.variables["lon"][:])
            for r in regs:
                il, ia = grid_indices(cells[r]["lon"].to_numpy(), cells[r]["lat"].to_numpy(), glon, glat)
                idx[r] = (ia, il)
        tm = _timemap(nc)
        vname = "spei" if "spei" in nc.variables else [v for v in nc.variables if nc.variables[v].ndim == 3][0]
        var = nc.variables[vname]
        for r in regs:
            buf[r][ts] = np.full((len(cells[r]), 264), np.nan, "float32")
        for j, (y, m) in enumerate(TARGET):
            ti = tm.get((y, m))
            if ti is None:
                continue
            arr = np.ma.filled(var[ti, :, :], np.nan).astype("float32")   # mask -> NaN (don't strip first)
            arr = np.where(np.abs(arr) < 100, arr, np.nan)                 # kill the 1e30 ocean fill-value
            for r in regs:
                ia, il = idx[r]
                buf[r][ts][:, j] = arr[ia, il]
        nc.close()
        if not keep:
            os.remove(os.path.join(tmp, f"spei{ts:02d}.nc"))
        print(f"  spei{ts:02d}: sampled {sum(np.isfinite(buf[r][ts]).any() for r in regs)} regions", flush=True)

    yrs = np.array([y for y, m in TARGET]); mos = np.array([m for y, m in TARGET])
    for r in regs:
        nc_ = len(cells[r])
        rows = {CC: np.repeat(cells[r][CC].to_numpy(), 264),
                "year": np.tile(yrs, nc_), "month": np.tile(mos, nc_)}
        for ts in scales:
            rows[f"spei_{ts:02d}m"] = buf[r][ts].reshape(-1)
        pd.DataFrame(rows).to_parquet(os.path.join(out_dir, f"{r}_spei.parquet"), index=False)
    print(f"done -> {out_dir}/  (join on [cell_id, year, month]).  tmp kept={keep}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
