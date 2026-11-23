"""Ingest MONTHLY MODIS gridded products LOCALLY -- no AppEEARS, no GEE. Resolve each granule
via NASA CMR -> direct Earthdata-cloud download (auth via ~/.netrc) -> pyhdf read of the global
grid -> sample the 4km cells -> per-region-per-year parquet. FAST (no server queue) and
SPACE-LIGHT (streams one global file at a time to --tmp on the HDD, deletes after sampling).

RUNS IN THE conda 'modis' ENV (needs pyhdf; the system py -3.9 can't load HDF4):
  C = "D:\\Miniconda3\\Scripts\\conda.exe"
  & $C run --no-capture-output -n modis python -u presplit_cc\\ingest_modis_cmg_local.py --selftest
  & $C run --no-capture-output -n modis python -u presplit_cc\\ingest_modis_cmg_local.py --product cloud --probe
  & $C run --no-capture-output -n modis python -u presplit_cc\\ingest_modis_cmg_local.py --product lst
  & $C run --no-capture-output -n modis python -u presplit_cc\\ingest_modis_cmg_local.py --all          # every product, one shot
  & $C run --no-capture-output -n modis python -u presplit_cc\\ingest_modis_cmg_local.py --all --only cloud,snow

Each product is one registry entry (short_name, CMR version, grid, output dir, SDS->column maps).
--all loops them all; already-complete region-years are skipped, so re-running is cheap.
NOTE: this covers single-file monthly grids (CMG/1deg). Daily (albedo) and sinusoidal-tiled
(fire/GPP) products use different fetchers.
"""
import glob
import netrc
import os
import sys
import time

import numpy as np
import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
CC = "cell_id"
YEARS = list(range(2002, 2024))                       # 2002-2023 inclusive


def _grid(nlon, nlat, res, lon0, lat0):
    """Regular global grid pixel-CENTER coord arrays: lon ascending, lat descending (N->S)."""
    return lon0 + res * np.arange(nlon), lat0 - res * np.arange(nlat)


GRIDS = {
    "cmg005": _grid(7200, 3600, 0.05, -179.975, 89.975),   # MODIS land CMG 0.05deg
    "deg1":   _grid(360, 180, 1.0, -179.5, 89.5),          # MOD08 atmosphere 1deg
}

# Per product: CMR short_name + version (DAAC conventions differ: LP DAAC "061", NSIDC "61",
# LAADS "6.1"), grid name, output dir, and SDS->column field maps. raw_min/raw_max gate valid
# pixels (fills fall outside) BEFORE scaling; k2c => Kelvin value, convert to Celsius.
PRODUCTS = {
    "lst": {
        "short": "MOD11C3", "ver": "061", "grid": "cmg005", "out": r"D:\modis_lst_monthly",
        "fields": {
            "LST_Day_CMG":   {"col": "V13_mean_lst_C",  "scale": 0.02, "k2c": True, "raw_min": 7500, "raw_max": 65535},
            "LST_Night_CMG": {"col": "nighttime_lst_C", "scale": 0.02, "k2c": True, "raw_min": 7500, "raw_max": 65535},
        },
    },
    "ndvi": {                                          # monthly NDVI TARGET (sweep's primary V11 source)
        "short": "MOD13C2", "ver": "061", "grid": "cmg005", "out": r"D:\modis_ndvi_cmg",
        "fields": {
            "CMG 0.05 Deg Monthly NDVI": {"col": "V11_mean_ndvi", "scale": 0.0001, "k2c": False, "raw_min": -2000, "raw_max": 10000},
        },
    },
    "ndvi_qa": {                                       # Pixel Reliability for the NDVI target, SAME MOD13C2 file.
        # WHY THIS EXISTS. The 'ndvi' entry above reads ONLY the NDVI band, so every pixel enters the
        # panel as though it were an observation. It is not: rank 4 = "Estimated -- From MODIS historic
        # time series" is a CLIMATOLOGY BACKFILL written when the month is cloud-blocked, and Part 390
        # showed its exact-repeat fingerprint at up to 5.8x the chance rate in cold cloudy regions,
        # concentrated 93% in the negative-NDVI rows of alaska_north_slope. Ranks: -1 Fill, 0 Good,
        # 1 Marginal, 2 Snow/Ice, 3 Cloudy, 4 Estimated. Separate output dir on purpose -- adding a
        # column to the 'ndvi' parquets would change the schema assemble_monthly_panel.py reads.
        "short": "MOD13C2", "ver": "061", "grid": "cmg005", "out": r"D:\modis_ndvi_qa_cmg",
        "fields": {                                    # confirm the exact SDS name with --probe before a full run
            "CMG 0.05 Deg Monthly pixel reliability": {"col": "V11_ndvi_reliability", "scale": 1.0, "k2c": False, "raw_min": 0, "raw_max": 4},
        },
    },
    "evi": {                                           # monthly EVI -- SIBLING band in the SAME MOD13C2 file as NDVI
        "short": "MOD13C2", "ver": "061", "grid": "cmg005", "out": r"D:\modis_evi_cmg",
        "fields": {                                    # same scale/range as NDVI; confirm the exact SDS name with --probe
            "CMG 0.05 Deg Monthly EVI": {"col": "V12_mean_evi", "scale": 0.0001, "k2c": False, "raw_min": -2000, "raw_max": 10000},
        },
    },
    "landcover": {                                     # ANNUAL CMG land cover (IGBP majority class) -> time-varying cropland signal
        "short": "MCD12C1", "ver": "061", "grid": "cmg005", "out": r"D:\modis_landcover_annual", "temporal": "annual",
        "fields": {                                    # IGBP class int (12=cropland, 14=cropland/natural mosaic); fill 255. v061 covers 2001-2022 (2023 -> NaN). --probe to confirm SDS name.
            "Majority_Land_Cover_Type_1": {"col": "modis_landcover_annual", "scale": 1.0, "k2c": False, "raw_min": 0, "raw_max": 254},
        },
    },
    "snow": {                                          # monthly snow-cover fraction (NSIDC; CMR version "61")
        "short": "MOD10CM", "ver": "61", "grid": "cmg005", "out": r"D:\modis_snow_monthly",
        "fields": {                                    # raw 0-100 %; >100 = flags -> masked; -> 0-1 fraction
            "Snow_Cover_Monthly_CMG": {"col": "snow_cover_fraction", "scale": 0.01, "k2c": False, "raw_min": 0, "raw_max": 100},
        },
    },
    "cloud": {                                         # monthly cloud fraction (LAADS MOD08_M3, 1deg; CMR version "6.1")
        "short": "MOD08_M3", "ver": "6.1", "grid": "deg1", "out": r"D:\modis_cloud_monthly",
        "fields": {                                    # raw int16 0-10000 (scale 1e-4 = fraction); *0.01 -> 0-100 percent
            "Cloud_Fraction_Mean_Mean": {"col": "cloud_frequency_pct", "scale": 0.01, "k2c": False, "raw_min": 0, "raw_max": 10000},
        },
    },
    "albedo": {                                        # white-sky shortwave albedo (LP DAAC MCD43C3, CMG, DAILY -> monthly mean)
        "short": "MCD43C3", "ver": "061", "grid": "cmg005", "out": r"D:\modis_albedo_monthly", "temporal": "daily",
        "fields": {                                    # raw int16, scale 1e-3 -> 0-1; fill 32767 masked
            "Albedo_WSA_shortwave": {"col": "V14_mean_albedo", "scale": 0.001, "k2c": False, "raw_min": 0, "raw_max": 32766},
        },
    },
}


def grid_indices(lons, lats, glon, glat):
    """Containing-cell index on a regular grid (copied from ingest_luh3_drivers.py, validated).
    Returns (ilon, ilat)."""
    lons = np.asarray(lons, float); lats = np.asarray(lats, float)
    lon0, dlon = float(glon[0]), float(glon[1] - glon[0])
    lat0, dlat = float(glat[0]), float(glat[1] - glat[0])
    ilon = np.rint((lons - lon0) / dlon).astype(int)
    ilat = np.rint((lats - lat0) / dlat).astype(int)
    ilon = np.clip(ilon, 0, len(glon) - 1)
    ilat = np.clip(ilat, 0, len(glat) - 1)
    return ilon, ilat


def _ed_session():
    """requests.Session carrying Earthdata Basic auth, dropping it on cross-host redirects except
    to urs.earthdata.nasa.gov (NASA-documented recipe). Creds from ~/.netrc."""
    import requests
    nr = netrc.netrc(os.path.join(os.path.expanduser("~"), ".netrc"))
    user, _, pwd = nr.authenticators("urs.earthdata.nasa.gov")

    class _S(requests.Session):
        AUTH = "urs.earthdata.nasa.gov"

        def rebuild_auth(self, prepared, response):
            h = prepared.headers
            if "Authorization" in h:
                o = requests.utils.urlparse(response.request.url).hostname
                r = requests.utils.urlparse(prepared.url).hostname
                if o != r and r != self.AUTH and o != self.AUTH:
                    del h["Authorization"]
    s = _S(); s.auth = (user, pwd)
    return s


def _find_url(s, P, y, m, retries=5):
    """Resolve the monthly granule's HTTPS .hdf URL via NASA CMR (paths aren't constructable --
    cloud host + production-timestamped filenames). Picks the granule whose acquisition month
    (A<YYYYDDD> in the name) matches (y, m), guarding against adjacent-month returns."""
    import datetime
    import re
    import requests
    cmr = "https://cmr.earthdata.nasa.gov/search/granules.json"
    params = {"short_name": P["short"], "version": P["ver"],
              "temporal": f"{y:04d}-{m:02d}-01T00:00:00Z,{y:04d}-{m:02d}-28T00:00:00Z", "page_size": 20}

    def amonth(h):
        mt = re.search(r"\.A(\d{4})(\d{3})\.", h)
        if not mt:
            return None
        d = datetime.date(int(mt.group(1)), 1, 1) + datetime.timedelta(days=int(mt.group(2)) - 1)
        return (d.year, d.month)
    last = None
    for a in range(retries):
        try:
            r = requests.get(cmr, params=params, timeout=120); r.raise_for_status()   # CMR public; Basic auth -> 401
            hits = [L.get("href", "") for e in r.json().get("feed", {}).get("entry", [])
                    for L in e.get("links", [])
                    if L.get("href", "").startswith("https") and L.get("href", "").endswith(".hdf")]
            match = [h for h in hits if amonth(h) == (y, m)]
            pick = sorted(set(match or hits))
            if pick:
                return pick[0]
            raise RuntimeError(f"no .hdf granule for {P['short']} {y}-{m:02d}")
        except Exception as e:
            last = e; time.sleep(4 * (a + 1))
    raise last


def _download(s, url, path, retries=5):
    last = None
    for a in range(retries):
        try:
            part = path + ".part"
            with s.get(url, stream=True, timeout=1800) as r:
                r.raise_for_status()
                with open(part, "wb") as fh:
                    for c in r.iter_content(1 << 20):
                        fh.write(c)
            with open(part, "rb") as fh:                # auth failures return an HTML login page
                head = fh.read(64)
            if head[:4] != b"\x0e\x03\x13\x01" and (b"<html" in head.lower() or b"<!doctype" in head.lower()):
                raise RuntimeError("got HTML, not HDF -- authorize the data app at urs.earthdata.nasa.gov "
                                   "(Applications -> Authorized Apps: LP DAAC / NSIDC / LAADS)")
            os.replace(part, path); return path
        except Exception as e:
            last = e
            for p in (path, path + ".part"):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
            time.sleep(4 * (a + 1))
    raise last


def _field_grid(hdf_path, sds, spec):
    """Read one SDS -> full global grid as float32 in physical units, fill/out-of-range -> NaN."""
    from pyhdf.SD import SD, SDC
    sd = SD(hdf_path, SDC.READ)
    ds = sd.select(sds)
    raw = ds[:]
    ds.endaccess(); sd.end()
    bad = (raw < spec["raw_min"]) | (raw > spec["raw_max"])
    val = raw.astype("float32") * spec["scale"]
    if spec.get("k2c"):
        val = val - 273.15
    val[bad] = np.nan
    return val


def _find_urls_daily(P, y, m, ndays, retries=5):
    """Up to ndays evenly-spaced daily .hdf URLs for the month (for 'daily' products)."""
    import calendar
    import re
    import requests
    last = calendar.monthrange(y, m)[1]
    cmr = "https://cmr.earthdata.nasa.gov/search/granules.json"
    params = {"short_name": P["short"], "version": P["ver"],
              "temporal": f"{y:04d}-{m:02d}-01T00:00:00Z,{y:04d}-{m:02d}-{last:02d}T23:59:59Z", "page_size": 50}
    err = None
    for a in range(retries):
        try:
            r = requests.get(cmr, params=params, timeout=120); r.raise_for_status()
            items = []
            for e in r.json().get("feed", {}).get("entry", []):
                for L in e.get("links", []):
                    h = L.get("href", "")
                    if h.startswith("https") and h.endswith(".hdf"):
                        mt = re.search(r"\.A(\d{4})(\d{3})\.", h)
                        if mt:
                            items.append((int(mt.group(2)), h))
                        break
            items = sorted(set(items))
            if not items:
                raise RuntimeError(f"no daily granules {P['short']} {y}-{m:02d}")
            if ndays and len(items) > ndays:
                pick = sorted(set(np.linspace(0, len(items) - 1, ndays).round().astype(int).tolist()))
                items = [items[i] for i in pick]
            return [u for _, u in items]
        except Exception as e:
            err = e; time.sleep(4 * (a + 1))
    raise err


def _month_grids(s, P, y, mo, tmp, ndays):
    """{col: global grid} for the month. 'daily' products -> nan-mean over ndays sampled days;
    else the single monthly file. Returns (grids, n_files_used)."""
    if P.get("temporal", "monthly") == "daily":
        urls = _find_urls_daily(P, y, mo, ndays)
        acc, cnt = {}, {}
        for u in urls:
            hdf = _download(s, u, os.path.join(tmp, os.path.basename(u)))
            for sds, spec in P["fields"].items():
                g = _field_grid(hdf, sds, spec); c = spec["col"]; fin = np.isfinite(g)
                if c not in acc:
                    acc[c] = np.zeros(g.shape, "float64"); cnt[c] = np.zeros(g.shape, "int32")
                acc[c][fin] += g[fin]; cnt[c][fin] += 1
            try:
                os.remove(hdf)
            except OSError:
                pass
        out = {}
        for c in acc:
            with np.errstate(invalid="ignore"):
                out[c] = np.where(cnt[c] > 0, acc[c] / np.maximum(cnt[c], 1), np.nan).astype("float32")
        return out, len(urls)
    url = _find_url(s, P, y, mo)
    hdf = _download(s, url, os.path.join(tmp, f"{P['short']}_{y}{mo:02d}.hdf"))
    out = {spec["col"]: _field_grid(hdf, sds, spec) for sds, spec in P["fields"].items()}
    try:
        os.remove(hdf)
    except OSError:
        pass
    return out, 1


def _masters():
    masters = {}
    for d in (cfg["data"]["master_dir"], cfg["forecast"]["regions_dir"]):
        for p in glob.glob(os.path.join(d, "*_master_*.parquet")):
            if ".bak." not in p:
                masters.setdefault(os.path.basename(p).split("_master_")[0], p)
    return masters


def _selftest():
    ok = True
    for gname, (glon, glat) in GRIDS.items():
        res = abs(glon[1] - glon[0])
        for lon, lat in [(0.0, 0.0), (-179.4, 89.4), (179.4, -89.4), (73.5, 15.5)]:
            il, ia = grid_indices([lon], [lat], glon, glat)
            if abs(glon[il[0]] - lon) > res / 2 + 1e-6 or abs(glat[ia[0]] - lat) > res / 2 + 1e-6:
                print(f"  FAIL {gname} ({lon},{lat})"); ok = False
    print("selftest:", "PASS (containing-cell sampling, all grids)" if ok else "FAIL")
    return 0 if ok else 1


def _probe(P, tmp):
    from pyhdf.SD import SD, SDC
    os.makedirs(tmp, exist_ok=True)
    s = _ed_session()
    url = _find_url(s, P, 2010, 7)
    print("probe file:", url)
    hdf = _download(s, url, os.path.join(tmp, "probe.hdf"))
    sd = SD(hdf, SDC.READ); print("SDS in file:", sorted(sd.datasets().keys())); sd.end()
    glon, glat = GRIDS[P.get("grid", "cmg005")]
    masters = _masters(); r0 = sorted(masters)[0]
    cells = pd.read_parquet(masters[r0], columns=[CC, "lon", "lat"]).drop_duplicates(CC)
    il, ia = grid_indices(cells["lon"].to_numpy(), cells["lat"].to_numpy(), glon, glat)
    for sds, spec in P["fields"].items():
        v = _field_grid(hdf, sds, spec)
        samp = v[ia, il]
        print(f"  {sds[:28]:28s}-> {spec['col']:20s} grid valid%={100*np.isfinite(v).mean():.1f} "
              f"global[min/med/max]=[{np.nanmin(v):.2f}/{np.nanmedian(v):.2f}/{np.nanmax(v):.2f}] "
              f"| {r0} mean={np.nanmean(samp):.2f} valid%={100*np.isfinite(samp).mean():.1f}")
    os.remove(hdf); print("probe: PASS")
    return 0


def run_product(s, product, P, regs, cells, tmp, out_dir, years, ndays):
    glon, glat = GRIDS[P.get("grid", "cmg005")]
    idx = {}
    for r in regs:
        il, ia = grid_indices(cells[r]["lon"].to_numpy(), cells[r]["lat"].to_numpy(), glon, glat)
        idx[r] = (ia, il)
    outcols = [spec["col"] for spec in P["fields"].values()]
    os.makedirs(out_dir, exist_ok=True)
    mode = f"daily-mean({ndays}d)" if P.get("temporal") == "daily" else "monthly"
    print(f"\n[{product}] {P['short']} v{P['ver']} grid={P.get('grid', 'cmg005')} {mode} -> "
          f"{len(regs)} regions x {len(years)} yrs, cols={outcols} -> {out_dir}", flush=True)
    for year in years:
        donefiles = {r: os.path.join(out_dir, f"{r}_{product}_{year}.parquet") for r in regs}
        todo = [r for r in regs if not os.path.exists(donefiles[r])]
        if not todo:
            print(f"  {year}: all {len(regs)} exist, skip", flush=True); continue
        buf = {r: {c: np.full((len(cells[r]), 12), np.nan, "float32") for c in outcols} for r in todo}
        if P.get("temporal") == "annual":              # ANNUAL product: one grid per YEAR, broadcast to all 12 months
            try:
                grids, nf = _month_grids(s, P, year, 1, tmp, ndays)   # granule .A{y}001 -> January query resolves it
                for r in todo:
                    ia, il = idx[r]
                    for c in outcols:
                        buf[r][c][:] = grids[c][ia, il][:, None]
                print(f"  {year}: annual grid broadcast to 12 months ({nf} file)", flush=True)
            except Exception as e:
                print(f"  {year}: ERROR {type(e).__name__}: {e} -- year left NaN", flush=True)
        else:
            for mo in range(1, 13):
                try:                                   # one bad month -> NaN + continue, never kills the run
                    grids, nf = _month_grids(s, P, year, mo, tmp, ndays)
                    for r in todo:
                        ia, il = idx[r]
                        for c in outcols:
                            buf[r][c][:, mo - 1] = grids[c][ia, il]
                    print(f"  {year}-{mo:02d}: sampled ({nf} file{'s' if nf > 1 else ''})", flush=True)
                except Exception as e:
                    print(f"  {year}-{mo:02d}: ERROR {type(e).__name__}: {e} -- month left NaN", flush=True)
        for r in todo:
            ncell = len(cells[r])
            rows = {CC: np.repeat(cells[r][CC].to_numpy(), 12), "year": year,
                    "month": np.tile(np.arange(1, 13), ncell)}
            for c in outcols:
                rows[c] = buf[r][c].reshape(-1)
            pd.DataFrame(rows).to_parquet(donefiles[r], index=False)
        print(f"  {year}: wrote {len(todo)} files", flush=True)
    print(f"  [{product}] done -> {out_dir}", flush=True)


def main(argv):
    if "--selftest" in argv:
        return _selftest()

    def opt(flag, d=None):
        return argv[argv.index(flag) + 1] if flag in argv else d
    tmp = opt("--tmp", r"D:\modis_dl")
    only = opt("--region"); limit = opt("--limit")
    years = [int(y) for y in opt("--years", ",".join(map(str, YEARS))).split(",")]
    ndays = int(opt("--days", "6"))                    # days/month averaged for 'daily' products (albedo)
    os.makedirs(tmp, exist_ok=True)

    if "--all" in argv or opt("--product") == "all":
        sub = opt("--only")
        products = [p.strip() for p in sub.split(",")] if sub else list(PRODUCTS)
    else:
        products = [opt("--product", "lst")]
    for p in products:
        if p not in PRODUCTS:
            print(f"unknown product {p}; have {list(PRODUCTS)}"); return 2

    if "--probe" in argv:
        return _probe(PRODUCTS[products[0]], tmp)

    masters = _masters()
    regs = sorted(masters)
    if only:
        regs = [r for r in regs if r == only]
    if limit:
        regs = regs[:int(limit)]
    cells = {r: pd.read_parquet(masters[r], columns=[CC, "lon", "lat"]).drop_duplicates(CC) for r in regs}

    s = _ed_session()
    for product in products:
        P = PRODUCTS[product]
        out_dir = opt("--out", P["out"]) if len(products) == 1 else P["out"]
        run_product(s, product, P, regs, cells, tmp, out_dir, years, ndays)
    print("\nALL DONE.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
