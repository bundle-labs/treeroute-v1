"""ONE unattended, crash-safe fetch of EVERY environmental driver we can grab WITHOUT credentials/registration.
For each driver it PROBES (opens one file, verifies structure) THEN downloads + samples onto the 4km cells; every
driver is NON-FATAL (a failure/skip is logged, the batch continues) and RESUMABLE (kept files + done-region skip).
Drivers (all open, no login / token / form / API-key):
  drought = EDDI + scPDSI + SPI          (via ingest_drought_indices; Palmer + evaporative-demand + precip-supply)
  chirps  = CHIRPS-2.0 monthly precip    (0.05deg GeoTIFF; independent gauge/IR precip, complements TerraClimate)
  lghap   = LGHAP annual-mean 1km AOD    (Zenodo; gap-free dust/aerosol = the Thar dust blind-spot signal)
EXCLUDED — need YOUR free accounts (a separate batch once you have them): MODIS MAIAC/MOD08/MISR AOD, MERRA-2 dust
  deposition, KBDI, GPM-IMERG, ERA5 extremes (NASA Earthdata / Copernicus CDS); and the daily->monthly precip-extreme
  products (CMORPH/PERSIANN/CPC/CHIRPS-daily = thousands of files, mostly redundant with existing precip).
Output: per-region parquet in D:\env_noauth\ keyed [cell_id, year, month]; fold each with the standard folder.
RUN (unattended, resumable): py -3.9 presplit_cc/fetch_env_noauth.py [--region thar_desert] [--only drought,chirps,lghap]
"""
import calendar
import json
import os
import sys
import time
import urllib.request

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ingest_drought_indices as DRI  # noqa: E402  reuse _download / _sample_asc / _sample_nc / _regions / TARGET ...

OUT = r"D:\env_noauth"
TMP = r"D:\env_noauth_dl"
for _d in (OUT, TMP):
    os.makedirs(_d, exist_ok=True)
CHIRPS_URL = "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/tifs/chirps-v2.0.{y}.{m:02d}.tif.gz"
LGHAP_REC = "14241715"                                     # Zenodo: LGHAP annual-mean AOD 2000-2023, ~1.7 GB


def _arg(flag, d=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else d


def _all_done(regs, tag):
    return len(regs) > 0 and all(os.path.exists(os.path.join(OUT, f"{r}_{tag}.parquet")) for r in regs)


# ---------------- driver runners (each returns a one-line status; raise only on hard build errors) ----------------
def run_drought(regs, cells, region):
    if _all_done(regs, "drought"):
        return "drought: already done -> skip"
    a = ["--tmp", TMP]
    try:
        DRI.main(["--probe"] + a)                          # PROBE first (verifies NetCDF var names + EDDI url dates)
    except Exception as e:
        return f"drought: PROBE FAILED ({type(e).__name__}: {e}) -- skipped"
    full = ["--out", OUT] + a + (["--region", region] if region else [])
    DRI.main(full)                                          # writes {region}_drought.parquet (resumable)
    return "drought: OK"


def run_chirps(regs, cells):
    if _all_done(regs, "chirps"):
        return "chirps: already done -> skip"
    # PROBE: fetch one month, sample thar-ish, confirm it reads
    ymd0 = CHIRPS_URL.format(y=2020, m=1)
    p0 = DRI._download(ymd0, os.path.join(TMP, "chirps_2020_01.tif.gz"), minbytes=100000)
    _ = DRI._sample_asc(f"/vsigzip/{p0}", cells, regs[:1])  # rasterio reads .tif.gz via /vsigzip/; raises if bad
    buf = {r: np.full((len(cells[r]), DRI.NMON), np.nan, "float32") for r in regs}
    t = time.time()
    for j, (y, m) in enumerate(DRI.TARGET):
        try:
            p = DRI._download(CHIRPS_URL.format(y=y, m=m), os.path.join(TMP, f"chirps_{y}_{m:02d}.tif.gz"), minbytes=100000)
            s = DRI._sample_asc(f"/vsigzip/{p}", cells, regs)
            for r in regs:
                v = s[r]; v[v < -100] = np.nan                          # CHIRPS nodata -9999
                buf[r][:, j] = v
        except Exception as e:
            print(f"    !! chirps {y}-{m:02d}: {type(e).__name__}: {e}", flush=True)
        if j % 24 == 0:
            print(f"    chirps {y}-{m:02d} ({j+1}/{DRI.NMON}) ({time.time()-t:.0f}s)", flush=True)
    _write(regs, cells, buf, "chirps", {"chirps_precip": buf})
    return "chirps: OK"


def _sample_2d(arr, tr, glat, glon, nod, cells, regs):
    """Sample one 2-D global grid at all regions' cell lon/lat. Uses rasterio transform (tr) if given, else grid_indices."""
    arr = np.where((arr == nod) if nod is not None else np.abs(arr) >= 1e4, np.nan, arr).astype("float32")
    h, w = arr.shape; out = {}
    lon0360 = (glon is not None) and float(np.nanmax(glon)) > 180.0
    for r in regs:
        lon = cells[r]["lon"].to_numpy(); lat = cells[r]["lat"].to_numpy()
        if tr is not None:
            import rasterio
            rr, cc = rasterio.transform.rowcol(tr, lon, lat); rr = np.asarray(rr); cc = np.asarray(cc)
        else:
            clon = np.where(lon < 0, lon + 360.0, lon) if lon0360 else lon
            cc, rr = DRI.grid_indices(clon, lat, glon, glat)
        ok = (rr >= 0) & (rr < h) & (cc >= 0) & (cc < w)
        v = np.full(len(lon), np.nan, "float32"); v[ok] = arr[rr[ok], cc[ok]]; out[r] = v
    return out


def _year_file_vals(path, cells, regs):
    """Sample a single-year global AOD file (.nc or .tif) -> {region: values}."""
    if path.lower().endswith((".nc", ".nc4")):
        nc = DRI._nc_open(path); var = DRI._var3d(nc, ["AOD", "aod", "AOD_550", "aod550"]); glat, glon = DRI._latlon(nc)
        a = np.ma.filled(nc.variables[var][:], np.nan)
        a = a[0] if a.ndim == 3 else a
        out = _sample_2d(np.asarray(a, "float32"), None, glat, glon, None, cells, regs); nc.close(); return out
    import rasterio
    with rasterio.open(path) as s:
        return _sample_2d(s.read(1).astype("float32"), s.transform, None, None, s.nodata, cells, regs)


def run_lghap(regs, cells):
    if _all_done(regs, "lghap"):
        return "lghap: already done -> skip"
    meta = json.load(urllib.request.urlopen(f"https://zenodo.org/api/records/{LGHAP_REC}", timeout=120))
    files = meta.get("files", [])
    print("  LGHAP record files:", [(f.get("key"), f"{f.get('size', 0)/1e6:.0f}MB") for f in files][:25], flush=True)

    def pick(exts):
        c = [f for f in files if f.get("key", "").lower().endswith(exts)]
        return max(c, key=lambda z: z.get("size", 0)) if c else None
    f = pick((".nc", ".nc4")) or pick((".tif", ".tiff")) or pick((".zip",))
    if f is None:
        return "lghap: no .nc/.tif/.zip in record (see file list) -- skipped"
    url = f.get("links", {}).get("self") or f.get("links", {}).get("download")
    p = DRI._download(url, os.path.join(TMP, f.get("key")), minbytes=1_000_000)
    key = f.get("key", "").lower()

    year_vals = {}                                                   # year -> {region: values}
    if key.endswith(".zip"):
        import glob as _g
        import re
        import zipfile
        exdir = os.path.join(TMP, "lghap_ex"); os.makedirs(exdir, exist_ok=True)
        with zipfile.ZipFile(p) as z:
            names = z.namelist(); print(f"  LGHAP zip: {len(names)} files, e.g. {names[:4]}", flush=True); z.extractall(exdir)
        yfiles = sorted(_g.glob(os.path.join(exdir, "**", "*.nc"), recursive=True)
                        + _g.glob(os.path.join(exdir, "**", "*.tif"), recursive=True))

        def yof(fn):
            mm = re.search(r"(19|20)\d{2}", os.path.basename(fn)); return int(mm.group()) if mm else None
        y2f = {yof(fn): fn for fn in yfiles if yof(fn)}
        if not y2f:
            return f"lghap: zip extracted but no year-tagged .nc/.tif ({len(yfiles)} files) -- skipped"
        for yy in sorted(y2f):
            year_vals[yy] = _year_file_vals(y2f[yy], cells, regs)
        print(f"  LGHAP sampled {len(year_vals)} yearly files ({min(year_vals)}-{max(year_vals)})", flush=True)
    else:                                                            # stacked .nc / multiband .tif -> one 2-D per band/slice
        if key.endswith((".nc", ".nc4")):
            nc = DRI._nc_open(p); var = DRI._var3d(nc, ["AOD", "aod"]); glat, glon = DRI._latlon(nc)
            n = nc.variables[var].shape[0]
            for i in range(n):
                year_vals[2000 + i] = _sample_2d(np.ma.filled(nc.variables[var][i, :, :], np.nan).astype("float32"),
                                                 None, glat, glon, None, cells, regs)
            nc.close()
        else:
            import rasterio
            with rasterio.open(p) as s:
                for b in range(s.count):
                    year_vals[2000 + b] = _sample_2d(s.read(b + 1).astype("float32"), s.transform, None, None, s.nodata, cells, regs)

    ypres = sorted(year_vals)
    buf = {r: np.full((len(cells[r]), DRI.NMON), np.nan, "float32") for r in regs}
    for j, (y, m) in enumerate(DRI.TARGET):
        yy = y if y in year_vals else (min(ypres) if y < min(ypres) else max(ypres))    # hold tails
        for r in regs:
            buf[r][:, j] = year_vals[yy][r]
    _write(regs, cells, buf, "lghap", {"lghap_aod": buf})
    return f"lghap: OK ({len(ypres)} years -> months; tails held)"


def _write(regs, cells, _buf, tag, colmap):
    yrs = np.array([y for y, m in DRI.TARGET]); mos = np.array([m for y, m in DRI.TARGET])
    for r in regs:
        nc_ = len(cells[r])
        rows = {DRI.CC: np.repeat(cells[r][DRI.CC].to_numpy(), DRI.NMON), "year": np.tile(yrs, nc_), "month": np.tile(mos, nc_)}
        for col, b in colmap.items():
            rows[col] = b[r].reshape(-1)
        pd.DataFrame(rows).to_parquet(os.path.join(OUT, f"{r}_{tag}.parquet"), index=False)


def main():
    region = _arg("--region"); only = set((_arg("--only") or "drought,chirps,lghap").split(","))
    regs, cells = DRI._regions(region, _arg("--limit"))
    print(f"ENV no-auth fetch | {len(regs)} regions | drivers: {sorted(only)} | out {OUT}", flush=True)
    status = []
    for name, fn in [("drought", lambda: run_drought(regs, cells, region)),
                     ("chirps", lambda: run_chirps(regs, cells)),
                     ("lghap", lambda: run_lghap(regs, cells))]:
        if name not in only:
            continue
        print(f"\n=== {name} ===", flush=True); t = time.time()
        try:
            s = fn()
        except Exception as e:
            s = f"{name}: FAILED ({type(e).__name__}: {e})"
        print(f"  [{s}] ({time.time()-t:.0f}s)", flush=True); status.append(s)
    print("\n==== ENV NO-AUTH FETCH SUMMARY ====")
    for s in status:
        print("  " + s)
    print(f"per-region parquets in {OUT}\\  (join each on [cell_id, year, month]); FETCH_ENV_DONE", flush=True)


if __name__ == "__main__":
    main()
