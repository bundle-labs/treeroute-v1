"""Ingest TerraClimate MONTHLY climate variables (no Google Earth Engine) and sample them
onto the project's 4km cells -> a monthly panel [cell_id, year, month, tc_*].

TerraClimate is served as plain HTTP NetCDF (one global file per variable per year) from the
University of Idaho THREDDS server -- NOT a manual click-download:
  download : https://thredds.northwestknowledge.net/thredds/fileServer/TERRACLIMATE_ALL/data/TerraClimate_<var>_<year>.nc
  opendap  : https://thredds.northwestknowledge.net/thredds/dodsC/TERRACLIMATE_ALL/data/TerraClimate_<var>_<year>.nc
No login / API key. Native monthly, 1/24deg (~4km, matches the panel), 1958-2023+.

Raw vars pulled -> derived driver columns (maps onto the existing annual features):
  tmax,tmin -> tc_tmean=(tmax+tmin)/2  tc_dtr=tmax-tmin       (V01_mean_temp, diurnal_temp_range)
  ppt -> tc_precip                                            (V02_total_precip)
  pet -> tc_ref_et          aet -> tc_aet                     (V07_ref_ET, aet_total)
  def -> tc_water_deficit   soil -> tc_soil_moisture          (climate_water_deficit, V30/soil_water)
  vpd -> tc_vpd             ws  -> tc_wind                     (V05_vpd, V09_wind)
  srad-> tc_solar           swe -> tc_swe   vap -> tc_vapor    (solar_radiation, swe_mean, sph source)
  ppt/pet -> tc_aridity                                       (aridity_index_p_pet)

Sampling: each 4km cell takes the TerraClimate grid cell containing its (lon,lat) -- the same
validated grid_indices() used for LUH3. Crash-safe: writes <out>/<region>_tc_<year>.parquet and
skips a year whose files all exist. Memory-bounded: reads one global month-slice at a time.

  py -3.9 presplit_cc/ingest_terraclimate_monthly.py --selftest                       # geometry, no net
  py -3.9 presplit_cc/ingest_terraclimate_monthly.py --probe                          # open 1 OPeNDAP file, print structure
  py -3.9 presplit_cc/ingest_terraclimate_monthly.py --vars ppt,tmax,tmin --years 2002 --region thar_desert  # tiny real test
  py -3.9 presplit_cc/ingest_terraclimate_monthly.py                                  # full pull, all vars/years/regions
"""
import glob
import os
import sys
import tempfile

import numpy as np
import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ingest_luh3_drivers import grid_indices       # noqa: E402  reuse validated geometry

cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
CC = "cell_id"
FILE = "https://thredds.northwestknowledge.net/thredds/fileServer/TERRACLIMATE_ALL/data/TerraClimate_{v}_{y}.nc"
DODS = "https://thredds.northwestknowledge.net/thredds/dodsC/TERRACLIMATE_ALL/data/TerraClimate_{v}_{y}.nc"
RAW = ["tmax", "tmin", "ppt", "pet", "aet", "def", "soil", "vpd", "ws", "srad", "swe", "vap"]
YEARS = list(range(2002, 2024))


def _derive(s):
    """s: dict raw_var -> (ncell,12) array. Returns dict out_col -> (ncell,12)."""
    out = {}
    if "tmax" in s and "tmin" in s:
        out["tc_tmean"] = (s["tmax"] + s["tmin"]) / 2.0
        out["tc_dtr"] = s["tmax"] - s["tmin"]
    m = {"ppt": "tc_precip", "pet": "tc_ref_et", "aet": "tc_aet", "def": "tc_water_deficit",
         "soil": "tc_soil_moisture", "vpd": "tc_vpd", "ws": "tc_wind", "srad": "tc_solar",
         "swe": "tc_swe", "vap": "tc_vapor_pressure"}
    for r, c in m.items():
        if r in s:
            out[c] = s[r]
    if "ppt" in s and "pet" in s:
        with np.errstate(divide="ignore", invalid="ignore"):
            out["tc_aridity"] = np.where(s["pet"] > 0, s["ppt"] / s["pet"], np.nan)
    return out


def _open(var, year, opendap, tmp, retries=5):
    """Return (netCDF4.Dataset, local_path_or_None). Downloads (with retries + atomic
    finalize) unless opendap=True. A partial/dropped download never becomes the final file,
    so transient IncompleteRead/ChunkedEncodingError just re-tries instead of being skipped."""
    import time

    from netCDF4 import Dataset
    if opendap:
        return Dataset(DODS.format(v=var, y=year)), None
    import requests
    path = os.path.join(tmp, f"TerraClimate_{var}_{year}.nc")
    url = FILE.format(v=var, y=year)
    last = None
    for attempt in range(retries):
        try:
            if not os.path.exists(path) or os.path.getsize(path) < 1_000_000:
                part = path + ".part"
                with requests.get(url, stream=True, timeout=900) as r:
                    r.raise_for_status()
                    with open(part, "wb") as fh:
                        for chunk in r.iter_content(chunk_size=1 << 20):
                            fh.write(chunk)
                os.replace(part, path)                     # atomic: only a COMPLETE file becomes 'path'
            return Dataset(path), path                     # also verifies it opens cleanly
        except Exception as e:
            last = e
            for p in (path, path + ".part"):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
            time.sleep(3 * (attempt + 1))
    raise last


def _selftest():
    glon = -179.97916 + (1 / 24) * np.arange(8640)        # TerraClimate cell centres
    glat = 89.97916 - (1 / 24) * np.arange(4320)
    ok = True
    for lon, lat in [(-64.98, -5.01), (0, 0), (115.3, 42.7), (-179.9, 89.9)]:
        il, ia = grid_indices([lon], [lat], glon, glat)
        if abs(glon[il[0]] - lon) > 1 / 48 + 1e-6 or abs(glat[ia[0]] - lat) > 1 / 48 + 1e-6:
            print(f"  FAIL ({lon},{lat})"); ok = False
    print("selftest:", "PASS (1/24deg containing-cell sampling correct)" if ok else "FAIL")
    return 0 if ok else 1


def _probe():
    from netCDF4 import Dataset
    url = DODS.format(v="ppt", y=2002)
    print("opening (OPeNDAP):", url)
    nc = Dataset(url)
    print("dims:", {d: len(nc.dimensions[d]) for d in nc.dimensions})
    print("vars:", [v for v in nc.variables])
    lat = nc.variables["lat"][:3]; lon = nc.variables["lon"][:3]
    print("lat[0:3]:", [float(x) for x in lat], " lon[0:3]:", [float(x) for x in lon])
    v = nc.variables["ppt"]
    print("ppt shape:", v.shape, " units:", getattr(v, "units", "?"))
    val = float(np.ma.filled(v[0, 2000, 4000], np.nan))     # one point, Jan 2002
    print("ppt[Jan, lat=%.2f, lon=%.2f] = %s" % (float(nc.variables["lat"][2000]),
          float(nc.variables["lon"][4000]), val))
    nc.close()
    print("probe: PASS (TerraClimate reachable, structure as expected)")
    return 0


def main(argv):
    if "--selftest" in argv:
        return _selftest()
    if "--probe" in argv:
        return _probe()

    def opt(flag, d=None):
        return argv[argv.index(flag) + 1] if flag in argv else d
    vars_ = opt("--vars", ",".join(RAW)).split(",")
    years = [int(y) for y in opt("--years", ",".join(map(str, YEARS))).split(",")]
    only = opt("--region"); limit = opt("--limit")
    out_dir = opt("--out", os.path.join(HERE, "terraclimate_monthly"))
    tmp = opt("--tmp", os.path.join(tempfile.gettempdir(), "tc_dl"))
    opendap = "--opendap" in argv
    keep = "--keep" in argv
    os.makedirs(out_dir, exist_ok=True); os.makedirs(tmp, exist_ok=True)

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

    # per-region cell tables (cell_id, lon, lat); grid indices filled lazily from first file
    cells = {r: pd.read_parquet(masters[r], columns=[CC, "lon", "lat"]).drop_duplicates(CC) for r in regs}
    idx = {}                                              # region -> (ilat, ilon)
    print(f"TerraClimate -> {len(regs)} regions, {len(years)} years, vars={vars_} "
          f"(mode={'opendap' if opendap else 'download'})", flush=True)

    for year in years:
        donefiles = {r: os.path.join(out_dir, f"{r}_tc_{year}.parquet") for r in regs}
        todo = [r for r in regs if not os.path.exists(donefiles[r])]
        if not todo:
            print(f"  {year}: all {len(regs)} region files exist, skip", flush=True); continue
        buf = {r: {} for r in todo}                       # region -> raw_var -> (ncell,12)
        for var in vars_:
            try:
                nc, path = _open(var, year, opendap, tmp)
            except Exception as e:
                print(f"  {year} {var}: OPEN ERROR {type(e).__name__}: {e}", flush=True); continue
            if not idx:                                   # compute grid indices once
                glat = np.asarray(nc.variables["lat"][:]); glon = np.asarray(nc.variables["lon"][:])
                for r in regs:
                    il, ia = grid_indices(cells[r]["lon"].to_numpy(), cells[r]["lat"].to_numpy(), glon, glat)
                    idx[r] = (ia, il)
            v = nc.variables[var]
            for m in range(12):
                arr = np.ma.filled(np.asarray(v[m, :, :], dtype="float32"), np.nan)
                for r in todo:
                    ia, il = idx[r]
                    buf[r].setdefault(var, np.full((len(ia), 12), np.nan, "float32"))[:, m] = arr[ia, il]
            nc.close()
            if path and not keep:
                os.remove(path)
            print(f"  {year} {var}: sampled", flush=True)
        # write each region's year
        for r in todo:
            der = _derive(buf[r])
            if not der:
                continue
            ncell = len(cells[r])
            rows = {CC: np.repeat(cells[r][CC].to_numpy(), 12), "year": year,
                    "month": np.tile(np.arange(1, 13), ncell)}
            for c, a in der.items():
                rows[c] = a.reshape(-1)
            pd.DataFrame(rows).to_parquet(donefiles[r], index=False)
        print(f"  {year}: wrote {len(todo)} region files", flush=True)

    print(f"done -> {out_dir}/  (join to masters on [{CC}, year, month])")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
