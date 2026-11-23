"""Ingest LUH3 (CMIP7 land-use harmonization, U Maryland) HUMAN/LAND-MANAGEMENT layers
as NEW drivers aligned to the project's 4km annual panel (cell_id x year, 2002-2023).

Produces, per cell per year, interpretable anthropogenic drivers derived from the LUH3
states + management NetCDFs (0.25 deg, annual, global -- the one true drop-in human-driver
product, confirmed absent from GEE):
  luh3_cropland_frac   grid-cell fraction that is cropland (sum of crop state fractions)
  luh3_rangeland_frac  fraction that is RANGELAND (grazing on natural veg) -- overgrazing signal
  luh3_pasture_frac    fraction that is MANAGED PASTURE (converted, high-intensity grazing)
  luh3_nfert_kgha      cropland-area-weighted synthetic-N application rate (kg N/ha/yr)
  luh3_irrig_frac      cropland-area-weighted irrigation fraction (management intensity)

Sampling: each 4km cell (lon,lat) takes the value of the LUH 0.25-deg grid cell that
CONTAINS it (4km << 28km, so nearest-centre == containing cell). The lon/lat->grid-index
math is in grid_indices() and is unit-tested by --selftest (no NetCDF needed).

REQUIRES: netCDF4  (py -3.9 -m pip install netCDF4) and the downloaded LUH3 files:
  states:     e.g. multiple-states.nc  (vars c3ann,c4ann,c3per,c4per,c3nfx,pastr,range)
  management: e.g. multiple-management.nc (vars fertl_<crop>, irrig_<crop>)
  Portal: https://luh.umd.edu/data.shtml  or Zenodo record 19261724 (LUH3 v1.2, 0850-2023).
  Verify exact variable/time names first with:  --list <file.nc>

  py -3.9 presplit_cc/ingest_luh3_drivers.py --selftest                          # geometry test, no data
  py -3.9 presplit_cc/ingest_luh3_drivers.py --list path/to/multiple-states.nc   # inspect a file
  py -3.9 presplit_cc/ingest_luh3_drivers.py --states states.nc --management management.nc \
          --out presplit_cc/luh3_drivers [--region thar_desert] [--limit N]
"""
import glob
import os
import sys

import numpy as np
import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
CC = "cell_id"
YEARS = list(range(2002, 2024))                    # 2002-2023 inclusive
CROPS = ["c3ann", "c4ann", "c3per", "c4per", "c3nfx"]


def grid_indices(lons, lats, glon, glat):
    """Map each (lon,lat) to the containing cell of a REGULAR grid given its 1-D centre
    coordinate arrays glon, glat (any orientation/step sign). Pure numpy -> unit-testable."""
    lons = np.asarray(lons, float); lats = np.asarray(lats, float)
    lon0, dlon = float(glon[0]), float(glon[1] - glon[0])
    lat0, dlat = float(glat[0]), float(glat[1] - glat[0])
    ilon = np.rint((lons - lon0) / dlon).astype(int)
    ilat = np.rint((lats - lat0) / dlat).astype(int)
    ilon = np.clip(ilon, 0, len(glon) - 1)
    ilat = np.clip(ilat, 0, len(glat) - 1)
    return ilon, ilat


def _selftest():
    """Validate grid_indices against a synthetic 0.25-deg grid in BOTH orientations."""
    ok = True
    # LUH-style: lon ascending -179.875.., lat DESCENDING 89.875..
    glon = -179.875 + 0.25 * np.arange(1440)
    glat = 89.875 - 0.25 * np.arange(720)
    cases = [(-64.98, -5.01), (0.0, 0.0), (179.9, -89.9), (-179.9, 89.9), (115.3, 42.7)]
    for lon, lat in cases:
        ilon, ilat = grid_indices([lon], [lat], glon, glat)
        clon, clat = glon[ilon[0]], glat[ilat[0]]
        if abs(clon - lon) > 0.125 + 1e-9 or abs(clat - lat) > 0.125 + 1e-9:
            print(f"  FAIL desc ({lon},{lat}) -> centre ({clon:.3f},{clat:.3f})"); ok = False
    # ascending-lat orientation
    glat2 = -89.875 + 0.25 * np.arange(720)
    for lon, lat in cases:
        ilon, ilat = grid_indices([lon], [lat], glon, glat2)
        clon, clat = glon[ilon[0]], glat2[ilat[0]]
        if abs(clat - lat) > 0.125 + 1e-9:
            print(f"  FAIL asc ({lon},{lat}) -> centre lat {clat:.3f}"); ok = False
    # out-of-range clips, no crash
    grid_indices([200, -200], [100, -100], glon, glat)
    print("selftest:", "PASS -- containing-cell sampling correct in both orientations" if ok else "FAIL")
    return 0 if ok else 1


def _list(path):
    from netCDF4 import Dataset
    nc = Dataset(path)
    print(f"== {os.path.basename(path)} ==")
    print("dims:", {d: len(nc.dimensions[d]) for d in nc.dimensions})
    if "time" in nc.variables:
        t = nc.variables["time"]; tv = t[:]
        print("time units:", getattr(t, "units", "?"), " n=", len(tv), " first/last:", float(tv[0]), float(tv[-1]))
    print("vars:", [v for v in nc.variables if v not in nc.dimensions])
    nc.close()
    return 0


def _year_index_map(nc, years):
    """Map calendar year -> time index, handling 'years since YYYY' or raw-year time coords."""
    t = np.asarray(nc.variables["time"][:])
    units = getattr(nc.variables["time"], "units", "")
    if "since" in units:
        base = int(units.split("since")[1].strip()[:4])
        yrs = base + t.astype(int)                  # LUH uses 'years since 0850-..'
    else:
        yrs = t.astype(int)
    return {y: int(np.where(yrs == y)[0][0]) for y in years if y in yrs}


def _derived_fields(states, mgmt, yi_s, yi_m, year):
    """Compute the 5 derived 0.25-deg driver fields for one year (2-D lat x lon arrays)."""
    def S(v):
        return np.asarray(states.variables[v][yi_s[year]]) if v in states.variables else None
    def M(v):
        return np.asarray(mgmt.variables[v][yi_m[year]]) if (mgmt and v in mgmt.variables) else None

    crop_fracs = {c: S(c) for c in CROPS if S(c) is not None}
    cropland = np.sum(list(crop_fracs.values()), axis=0) if crop_fracs else None
    rng = S("range"); pas = S("pastr")
    nfert = irrig = None
    if mgmt is not None and cropland is not None:
        denom = np.where(cropland > 0, cropland, np.nan)
        fn = np.zeros_like(cropland); fi = np.zeros_like(cropland)
        for c, frac in crop_fracs.items():
            fc = M("fertl_" + c); ic = M("irrig_" + c)
            if fc is not None: fn += np.nan_to_num(fc) * frac
            if ic is not None: fi += np.nan_to_num(ic) * frac
        nfert = np.where(cropland > 0, fn / denom, 0.0)
        irrig = np.where(cropland > 0, fi / denom, 0.0)
    return {"luh3_cropland_frac": cropland, "luh3_rangeland_frac": rng,
            "luh3_pasture_frac": pas, "luh3_nfert_kgha": nfert, "luh3_irrig_frac": irrig}


def main(argv):
    if "--selftest" in argv:
        return _selftest()
    if "--list" in argv:
        return _list(argv[argv.index("--list") + 1])

    def opt(flag, d=None):
        return argv[argv.index(flag) + 1] if flag in argv else d
    states_p = opt("--states"); mgmt_p = opt("--management")
    out_dir = opt("--out", os.path.join(HERE, "luh3_drivers"))
    only = opt("--region"); limit = opt("--limit")
    if not states_p:
        print("ERROR: --states <states.nc> required (or use --selftest / --list).")
        return 2
    from netCDF4 import Dataset
    os.makedirs(out_dir, exist_ok=True)

    states = Dataset(states_p)
    mgmt = Dataset(mgmt_p) if mgmt_p else None
    glon = np.asarray(states.variables["lon"][:]); glat = np.asarray(states.variables["lat"][:])
    yi_s = _year_index_map(states, YEARS)
    yi_m = _year_index_map(mgmt, YEARS) if mgmt else {}
    years = [y for y in YEARS if y in yi_s and (not mgmt or y in yi_m)]
    print(f"grid {len(glat)}x{len(glon)}  years available: {years[0]}-{years[-1]} ({len(years)})")
    fields = list(_derived_fields(states, mgmt, yi_s, yi_m, years[0]).keys())

    # precompute the derived 2-D fields once per year (reused across all regions)
    peryear = {y: _derived_fields(states, mgmt, yi_s, yi_m, y) for y in years}

    masters = {}
    for d in (cfg["data"]["master_dir"], cfg["forecast"]["regions_dir"]):
        for p in glob.glob(os.path.join(d, "*_master_*.parquet")):
            if ".bak." in p:
                continue
            masters.setdefault(os.path.basename(p).split("_master_")[0], p)
    regs = sorted(masters)
    if only:
        regs = [r for r in regs if r == only]
    if limit:
        regs = regs[:int(limit)]

    for i, rg in enumerate(regs, 1):
        cells = pd.read_parquet(masters[rg], columns=[CC, "lon", "lat"]).drop_duplicates(CC)
        ilon, ilat = grid_indices(cells["lon"].to_numpy(), cells["lat"].to_numpy(), glon, glat)
        rows = []
        for y in years:
            rec = {CC: cells[CC].to_numpy(), "year": y}
            for f in fields:
                arr = peryear[y][f]
                rec[f] = arr[ilat, ilon] if arr is not None else np.nan
            rows.append(pd.DataFrame(rec))
        out = pd.concat(rows, ignore_index=True)
        outp = os.path.join(out_dir, f"{rg}_luh3.parquet")
        out.to_parquet(outp, index=False)
        print(f"  [{i}/{len(regs)}] {rg:28s} cells={len(cells):>6,} rows={len(out):>7,} -> {os.path.basename(outp)}")

    states.close()
    if mgmt:
        mgmt.close()
    print(f"done -> {out_dir}/  (join to masters on [{CC}, year])")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
