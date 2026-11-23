"""Ingest MONTHLY GPP from FluxSat (GES DISC FluxSatMGPP_L3_Daily_p5deg v2.2) -- NetCDF via
NASA CMR + Earthdata (auth from ~/.netrc). NO conda needed (netCDF4, not HDF4). Each granule is
ONE MONTH of DAILY GPP on the MERRA-2 0.625x0.5deg grid; we mean the daily layers x days/1000
-> monthly GPP in kgC m-2 (the master's gpp_kgC_m2 convention; annual sum ~ master annual).
Streams one ~16 MB file at a time and deletes it. EVERYTHING ON D: (C: must stay untouched).

  py -3.9 presplit_cc/ingest_fluxsat_gpp.py --selftest
  py -3.9 presplit_cc/ingest_fluxsat_gpp.py --probe
  py -3.9 presplit_cc/ingest_fluxsat_gpp.py --region thar_desert --years 2010
  py -3.9 presplit_cc/ingest_fluxsat_gpp.py --out D:\gpp_monthly --tmp D:\fluxsat_dl
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
SHORT, VER, OUTCOL = "FluxSatMGPP_L3_Daily_p5deg", "2.2", "gpp_kgC_m2"
YEARS = list(range(2002, 2024))
TMP_DEFAULT = r"D:\fluxsat_dl"
OUT_DEFAULT = r"D:\gpp_monthly"


def grid_indices(lons, lats, glon, glat):
    lons = np.asarray(lons, float); lats = np.asarray(lats, float)
    lon0, dlon = float(glon[0]), float(glon[1] - glon[0])
    lat0, dlat = float(glat[0]), float(glat[1] - glat[0])
    ilon = np.clip(np.rint((lons - lon0) / dlon).astype(int), 0, len(glon) - 1)
    ilat = np.clip(np.rint((lats - lat0) / dlat).astype(int), 0, len(glat) - 1)
    return ilon, ilat


def _ed_session():
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


def _cmr_url(y, m, retries=6):
    """Resolve the monthly granule's HTTPS .nc URL via CMR (month-matched)."""
    import datetime
    import re
    import requests
    cmr = "https://cmr.earthdata.nasa.gov/search/granules.json"
    params = {"short_name": SHORT, "version": VER,
              "temporal": f"{y:04d}-{m:02d}-01T00:00:00Z,{y:04d}-{m:02d}-28T00:00:00Z", "page_size": 10}
    last = None
    for a in range(retries):
        try:
            r = requests.get(cmr, params=params, timeout=120); r.raise_for_status()
            urls = [L.get("href", "") for e in r.json().get("feed", {}).get("entry", [])
                    for L in e.get("links", [])
                    if L.get("href", "").startswith("https") and L.get("href", "").lower().endswith((".nc", ".nc4"))]
            # filename carries _YYYYMM_; keep the one matching (y, m)
            def ym(u):
                mt = re.search(r"_(\d{4})(\d{2})_", os.path.basename(u))
                return (int(mt.group(1)), int(mt.group(2))) if mt else None
            match = [u for u in urls if ym(u) == (y, m)]
            pick = sorted(set(match or urls))
            if pick:
                return pick[0]
            raise RuntimeError(f"no .nc granule {SHORT} {y}-{m:02d}")
        except Exception as e:
            last = e; time.sleep(4 * (a + 1))
    raise last


def _download(s, url, path, retries=6):
    last = None
    for a in range(retries):
        try:
            part = path + ".part"
            with s.get(url, stream=True, timeout=900) as r:
                r.raise_for_status()
                with open(part, "wb") as fh:
                    for c in r.iter_content(1 << 20):
                        fh.write(c)
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


def _monthly_grid(s, y, m, tmp):
    """Download one month, return (monthly_gpp_kgC_m2 grid, glat, glon). Monthly GPP = mean of
    the daily g m-2 d-1 layers x n_days / 1000 (kgC m-2 month-1)."""
    from netCDF4 import Dataset
    fp = os.path.join(tmp, f"fluxsat_{y}{m:02d}.nc")
    _download(s, _cmr_url(y, m), fp)
    ds = Dataset(fp)
    g = np.ma.filled(ds.variables["GPP"][:].astype("float32"), np.nan)   # (ndays, nlat, nlon)
    glat = np.asarray(ds.variables["lat"][:]); glon = np.asarray(ds.variables["lon"][:])
    ds.close()
    try:
        os.remove(fp)
    except OSError:
        pass
    with np.errstate(invalid="ignore"):
        monthly = np.nanmean(g, axis=0) * g.shape[0] / 1000.0
    return monthly, glat, glon


def _masters():
    masters = {}
    for d in (cfg["data"]["master_dir"], cfg["forecast"]["regions_dir"]):
        for p in glob.glob(os.path.join(d, "*_master_*.parquet")):
            if ".bak." not in p:
                masters.setdefault(os.path.basename(p).split("_master_")[0], p)
    return masters


def _selftest():
    glon = -179.688 + 0.625 * np.arange(576); glat = -89.75 + 0.5 * np.arange(360)
    ok = True
    for lon, lat in [(0.0, 0.0), (-179.5, -89.5), (179.5, 89.5), (73.5, 15.5)]:
        il, ia = grid_indices([lon], [lat], glon, glat)
        if abs(((glon[il[0]] - lon + 180) % 360) - 180) > 0.4 or abs(glat[ia[0]] - lat) > 0.3:
            print(f"  FAIL ({lon},{lat})"); ok = False
    print("selftest:", "PASS (MERRA 0.625x0.5deg sampling)" if ok else "FAIL")
    return 0 if ok else 1


def _probe(tmp):
    os.makedirs(tmp, exist_ok=True)
    s = _ed_session()
    monthly, glat, glon = _monthly_grid(s, 2010, 7, tmp)
    masters = _masters(); r0 = sorted(masters)[0]
    cells = pd.read_parquet(masters[r0], columns=[CC, "lon", "lat"]).drop_duplicates(CC)
    il, ia = grid_indices(cells["lon"].to_numpy(), cells["lat"].to_numpy(), glon, glat)
    samp = monthly[ia, il]
    print(f"GPP 2010-07 monthly grid: valid%={100*np.isfinite(monthly).mean():.1f} "
          f"global[min/med/max]=[{np.nanmin(monthly):.3f}/{np.nanmedian(monthly):.3f}/{np.nanmax(monthly):.3f}] kgC/m2/mo "
          f"| {r0} mean={np.nanmean(samp):.3f}")
    print("probe: PASS")
    return 0


def main(argv):
    if "--selftest" in argv:
        return _selftest()

    def opt(flag, d=None):
        return argv[argv.index(flag) + 1] if flag in argv else d
    tmp = opt("--tmp", TMP_DEFAULT)
    out_dir = opt("--out", OUT_DEFAULT)
    os.makedirs(tmp, exist_ok=True)
    if "--probe" in argv:
        return _probe(tmp)
    only = opt("--region"); limit = opt("--limit")
    years = [int(y) for y in opt("--years", ",".join(map(str, YEARS))).split(",")]
    os.makedirs(out_dir, exist_ok=True)

    masters = _masters()
    regs = sorted(masters)
    if only:
        regs = [r for r in regs if r == only]
    if limit:
        regs = regs[:int(limit)]
    cells = {r: pd.read_parquet(masters[r], columns=[CC, "lon", "lat"]).drop_duplicates(CC) for r in regs}
    idx = {}
    print(f"FluxSat GPP -> {len(regs)} regions x {len(years)} yrs -> {out_dir}", flush=True)

    s = _ed_session()
    for year in years:
        donefiles = {r: os.path.join(out_dir, f"{r}_gpp_{year}.parquet") for r in regs}
        todo = [r for r in regs if not os.path.exists(donefiles[r])]
        if not todo:
            print(f"  {year}: all exist, skip", flush=True); continue
        buf = {r: np.full((len(cells[r]), 12), np.nan, "float32") for r in todo}
        for mo in range(1, 13):
            try:
                monthly, glat, glon = _monthly_grid(s, year, mo, tmp)
                if not idx:
                    for r in regs:
                        il, ia = grid_indices(cells[r]["lon"].to_numpy(), cells[r]["lat"].to_numpy(), glon, glat)
                        idx[r] = (ia, il)
                for r in todo:
                    ia, il = idx[r]
                    buf[r][:, mo - 1] = monthly[ia, il]
                print(f"  {year}-{mo:02d}: sampled", flush=True)
            except Exception as e:
                print(f"  {year}-{mo:02d}: ERROR {type(e).__name__}: {e} -- month NaN", flush=True)
        for r in todo:
            ncell = len(cells[r])
            rows = {CC: np.repeat(cells[r][CC].to_numpy(), 12), "year": year,
                    "month": np.tile(np.arange(1, 13), ncell), OUTCOL: buf[r].reshape(-1)}
            pd.DataFrame(rows).to_parquet(donefiles[r], index=False)
        print(f"  {year}: wrote {len(todo)} files", flush=True)
    print(f"done -> {out_dir}/  (join on [{CC}, year, month])", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
