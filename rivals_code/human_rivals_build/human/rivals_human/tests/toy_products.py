"""Tiny synthetic products, toy adapters, a toy M runner and the toy registries (SPEC_HUMAN.txt section 7).

Product writers (all under a test's basetemp, never in a real product folder):
  grid netCDF (N / I kind, one value per unit x step), a daily per-unit npz (table toy), an uncompressed SST npz in
  the layout of D:/coral/drivers/sst_compact_all.npz (members uk, start, end, day, sst, manifest; STORED, so each
  member can be memory-mapped by its zip offset), a CRW-like MMM netCDF (int16, scale 0.01, lat north -> south), a
  CRW Outlook-like weekly netCDF (CRW_BAA_Week_20 with start_time / stop_time attributes, surface_flag), 64 x 64
  GeoTIFF tiles (lossyear, treecover2000, datamask) and a zipped 2-polygon GeoPackage (layer gadm36_TOY_2), an
  EAC4-like and a MERRA-2-like monthly grid. Each product folder gets a product_manifest.json in the format of
  D:/treeroute/human_tools/fetch_products.py (files: {name: {bytes, sha256}}, complete: true).

Toy adapters (registry `adapter: rivals_human.tests.toy_products:<function>`) follow the adapter contract of
BUILD_NOTES_shared.txt: build(ctx, rival, lead, stage) -> the 1.4 columns. Their behaviour is set by the rival's
registry `options` (data): which product variable, which step or day relative to the issue, what they report as
info_end / target_obs_end. They never read a label.

The toy M runner (registry `runner: rivals_human.tests.toy_products`) is fit / predict at module level: a per-unit
mean anomaly of the fit labels (read only through ctx.fit_labels) added to the row's identity normal.

Fixed synthetic data use one fixed generator (TOY_RNG_SEED); no seed is ever varied (owner rule).
"""

import hashlib
import io
import json
import os
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

TOY_RNG_SEED = 20261021
KEYS = ["unit", "group", "time", "issue", "lead"]


# ===================================================================================================== manifests
def sha256_file(path: Any) -> str:
    h = hashlib.sha256()
    with open(str(path), "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_product_manifest(folder: Path, product: str, version: str, licence: str = "toy data (tests only)",
                           note: str = "") -> Path:
    """product_manifest.json over every file of the folder (fetch_products.py format)."""
    folder = Path(folder)
    files = {}
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.name != "product_manifest.json":
            files[p.name] = {"bytes": p.stat().st_size, "sha256": sha256_file(p)}
    doc = {"product": product, "version": version, "label": "toy %s" % product, "dataset": "synthetic",
           "source_url": None, "licence": licence, "store": None, "note": note or "synthetic test product",
           "created": "2026-10-21T00:00:00+00:00", "tool": {"path": __file__, "sha256": None},
           "approval": "test fixture", "requests": {}, "files": files, "runs": [],
           "total_bytes": int(sum(f["bytes"] for f in files.values())), "complete": True}
    mp = folder / "product_manifest.json"
    mp.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return mp


# ===================================================================================================== writers
def write_unit_step_nc(path: Path, units: Sequence[str], steps: Sequence[int], variables: Mapping[str, np.ndarray]
                       ) -> Path:
    """netCDF with dimensions (unit, step): variables unit (str), step (int64) and float64 fields [unit, step]
    (NaN stored as the fill value)."""
    import netCDF4
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with netCDF4.Dataset(str(path), "w", format="NETCDF4") as ds:
        ds.createDimension("unit", len(units))
        ds.createDimension("step", len(steps))
        vu = ds.createVariable("unit", str, ("unit",))
        vu[:] = np.asarray([str(u) for u in units], dtype=object)
        vs = ds.createVariable("step", "i8", ("step",))
        vs[:] = np.asarray(steps, dtype=np.int64)
        for name, arr in variables.items():
            v = ds.createVariable(name, "f8", ("unit", "step"), fill_value=-9999.0)
            v[:] = np.ma.masked_invalid(np.asarray(arr, dtype=np.float64))
    return path


def read_unit_step_nc(path: Path, var: str) -> Tuple[Dict[str, int], Dict[int, int], np.ndarray]:
    import netCDF4
    with netCDF4.Dataset(str(path), "r") as ds:
        units = [str(u) for u in ds.variables["unit"][:]]
        steps = np.asarray(ds.variables["step"][:], dtype=np.int64)
        vals = np.ma.filled(np.ma.asarray(ds.variables[var][:], dtype=np.float64), np.nan)
    return {u: i for i, u in enumerate(units)}, {int(s): j for j, s in enumerate(steps.tolist())}, vals


def write_unit_day_npz(path: Path, units: Sequence[str], first_day: int, last_day: int,
                       variables: Mapping[str, np.ndarray]) -> Path:
    """Uncompressed npz: unit (str), day (int64 ordinal), and float64 fields [unit, day]."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    days = np.arange(int(first_day), int(last_day) + 1, dtype=np.int64)
    arrays = {"unit": np.asarray([str(u) for u in units]), "day": days}
    for k, v in variables.items():
        arrays[k] = np.asarray(v, dtype=np.float64)
    np.savez(str(path), **arrays)
    return path


def site_key(lat: Any, lon: Any, dp: int = 4) -> np.ndarray:
    """coral_safe.py:97-107: one int64 per site (1e-4 degrees, offsets keep both halves positive)."""
    s = 10 ** dp
    a = np.rint((np.asarray(lat, dtype="float64") + 90.0) * s).astype("int64")
    b = np.rint((np.asarray(lon, dtype="float64") + 180.0) * s).astype("int64")
    return a * (360 * s + 1) + b


def write_sst_npz(path: Path, sites: Mapping[int, Tuple[np.ndarray, np.ndarray]]) -> Path:
    """The layout of sst_compact_all.npz: uk int64 [n sites, sorted], start / end int64 (half-open slice into day /
    sst), day int32 (ordinal), sst float32, manifest int64 [2] (n sites, n rows). Members STORED (np.savez)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    uk = np.asarray(sorted(int(k) for k in sites), dtype=np.int64)
    start, end, days, ssts = [], [], [], []
    at = 0
    for k in uk.tolist():
        d, s = sites[k]
        d = np.asarray(d, dtype=np.int32)
        s = np.asarray(s, dtype=np.float32)
        order = np.argsort(d, kind="mergesort")
        start.append(at)
        at += d.size
        end.append(at)
        days.append(d[order])
        ssts.append(s[order])
    np.savez(str(path), uk=uk, start=np.asarray(start, np.int64), end=np.asarray(end, np.int64),
             day=np.concatenate(days).astype(np.int32), sst=np.concatenate(ssts).astype(np.float32),
             manifest=np.asarray([uk.size, at], dtype=np.int64))
    return path


def npz_member_offsets(path: Path) -> Dict[str, Tuple[int, int]]:
    """{member: (compress_type, header_offset)} of an npz (the test of 'STORED, memory-mappable')."""
    with zipfile.ZipFile(str(path)) as z:
        return {i.filename: (i.compress_type, i.header_offset) for i in z.infolist()}


def write_mmm_nc(path: Path, lat: np.ndarray, lon: np.ndarray, mmm: np.ndarray, valid: np.ndarray) -> Path:
    """A CRW-like climatology: sst_clim_mmm (time, lat, lon) int16, scale_factor 0.01, _FillValue -32768 on invalid
    pixels, and mask_for_sst_clim_mmm int8 (0 = valid water, 1 = land); lat as given (CRW: north -> south)."""
    import netCDF4
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with netCDF4.Dataset(str(path), "w", format="NETCDF4") as ds:
        ds.createDimension("time", 1)
        ds.createDimension("lat", len(lat))
        ds.createDimension("lon", len(lon))
        vt = ds.createVariable("time", "i4", ("time",))
        vt.units = "seconds since 1981-01-01 00:00:00"
        vt[:] = [0]
        vla = ds.createVariable("lat", "f4", ("lat",))
        vla.units = "degrees_north"
        vla[:] = np.asarray(lat, dtype=np.float32)
        vlo = ds.createVariable("lon", "f4", ("lon",))
        vlo.units = "degrees_east"
        vlo[:] = np.asarray(lon, dtype=np.float32)
        v = ds.createVariable("sst_clim_mmm", "i2", ("time", "lat", "lon"), fill_value=np.int16(-32768))
        v.units = "degrees_Celsius"
        v.scale_factor = np.float32(0.01)
        v.add_offset = np.float32(0.0)
        data = np.ma.masked_array(np.asarray(mmm, dtype=np.float64)[None, :, :],
                                  mask=~np.asarray(valid, dtype=bool)[None, :, :])
        v[:] = data
        m = ds.createVariable("mask_for_sst_clim_mmm", "i1", ("time", "lat", "lon"))
        m.units = "pixel_classification"
        m[:] = np.where(np.asarray(valid, dtype=bool), 0, 1).astype(np.int8)[None, :, :]
    return path


def write_outlook_nc(path: Path, issue_day: str, weeks: Mapping[int, Tuple[str, str]], baa: Mapping[int, np.ndarray],
                     land: np.ndarray, lat: Optional[np.ndarray] = None, lon: Optional[np.ndarray] = None) -> Path:
    """A CRW Outlook v5-like file: lat 89.75..-89.75 and lon 0.25..359.75 (0.5 degree) unless given;
    CRW_BAA_Week_NN int8 (time, lat, lon) with start_time / stop_time attributes 'YYYYMMDDT000000Z';
    surface_flag (0 water, 1 land)."""
    import netCDF4
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lat = np.arange(89.75, -90.0, -0.5) if lat is None else np.asarray(lat)
    lon = np.arange(0.25, 360.0, 0.5) if lon is None else np.asarray(lon)
    import datetime as _dt
    icwk = _dt.datetime.strptime(str(issue_day)[:8], "%Y%m%d")
    with netCDF4.Dataset(str(path), "w", format="NETCDF4") as ds:
        ds.createDimension("time", 1)
        ds.createDimension("lat", lat.size)
        ds.createDimension("lon", lon.size)
        vt = ds.createVariable("time", "i4", ("time",))
        vt.units = "seconds since 1981-01-01 00:00:00"
        vt.comment = "toy issue %s" % issue_day
        vt[:] = [int((icwk + _dt.timedelta(days=7) - _dt.datetime(1981, 1, 1)).total_seconds())]   # NOAA: time = icwk + 7
        ds.createVariable("lat", "f4", ("lat",))[:] = lat.astype(np.float32)
        ds.createVariable("lon", "f4", ("lon",))[:] = lon.astype(np.float32)
        sf = ds.createVariable("surface_flag", "i1", ("lat", "lon"))
        sf.flag_values = "[0 1 2 4]"
        sf.flag_meanings = "valid-water land missing ice"
        sf[:] = np.where(np.asarray(land, dtype=bool), 1, 0).astype(np.int8)
        for wk, (start, stop) in sorted(weeks.items()):
            v = ds.createVariable("CRW_BAA_Week_%02d" % wk, "i1", ("time", "lat", "lon"), fill_value=np.int8(-5))
            v.start_time = start
            v.stop_time = stop
            v.time_coverage_start = start
            v.time_coverage_duration = stop
            v[:] = np.asarray(baa[wk], dtype=np.int8)[None, :, :]
    return path


def write_geotiff(path: Path, array: np.ndarray, west: float, north: float, pixel: float, dtype: str = "uint8") -> Path:
    import rasterio
    from rasterio.transform import from_origin
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    a = np.asarray(array)
    with rasterio.open(str(path), "w", driver="GTiff", height=a.shape[0], width=a.shape[1], count=1, dtype=dtype,
                       crs="EPSG:4326", transform=from_origin(west, north, pixel, pixel)) as dst:
        dst.write(a.astype(dtype), 1)
    return path


def write_hansen_toy(folder: Path, tag: str, lossyear: np.ndarray, treecover: np.ndarray, datamask: np.ndarray,
                     west: float, north: float, pixel: float, version: str = "GFC-2025-v1.13") -> Dict[str, Path]:
    """Three Hansen-named toy tiles: Hansen_<version>_<layer>_<tag>.tif."""
    out = {}
    for layer, arr in (("lossyear", lossyear), ("treecover2000", treecover), ("datamask", datamask)):
        out[layer] = write_geotiff(Path(folder) / ("Hansen_%s_%s_%s.tif" % (version, layer, tag)), arr, west, north,
                                   pixel)
    return out


def write_gadm_toy(folder: Path, polygons: Sequence[Tuple[str, Any]], iso: str = "TOY", level: int = 2) -> Path:
    """A zipped GeoPackage gadm36_<iso>_gpkg.zip holding gadm36_<iso>.gpkg with layer gadm36_<iso>_<level>:
    one feature per (GID, shapely polygon), columns GID_0, NAME_0, GID_1, NAME_1, GID_2, NAME_2."""
    import geopandas as gpd
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    gpkg = folder / ("gadm36_%s.gpkg" % iso)
    rows = []
    for gid, poly in polygons:
        rows.append({"GID_0": iso, "NAME_0": "Toyland", "GID_1": "%s.1_1" % iso, "NAME_1": "Toy one",
                     "GID_2": gid, "NAME_2": "toy %s" % gid, "geometry": poly})
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    gdf.to_file(str(gpkg), layer="gadm36_%s_%d" % (iso, level), driver="GPKG")
    zp = folder / ("gadm36_%s_gpkg.zip" % iso)
    with zipfile.ZipFile(str(zp), "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(str(gpkg), arcname=gpkg.name)
        z.writestr("license.txt", "toy")
    moved = folder / "_unzipped"
    moved.mkdir(exist_ok=True)
    os.replace(str(gpkg), str(moved / gpkg.name))          # only the zip stays in the product folder (moved, kept)
    return zp


def write_monthly_grid_nc(path: Path, lat: np.ndarray, lon: np.ndarray, months: Sequence[Tuple[int, int]],
                          variables: Mapping[str, np.ndarray], units: str = "kg m-3", time_name: str = "time") -> Path:
    """A monthly reanalysis-like grid: <time_name> (days since 2000-01-01, the 1st of each month), lat, lon, and
    float32 variables [time, lat, lon] with the given units attribute."""
    import datetime as _dt
    import netCDF4
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with netCDF4.Dataset(str(path), "w", format="NETCDF4") as ds:
        ds.createDimension(time_name, len(months))
        ds.createDimension("lat", len(lat))
        ds.createDimension("lon", len(lon))
        vt = ds.createVariable(time_name, "f8", (time_name,))
        vt.units = "days since 2000-01-01 00:00:00"
        vt.calendar = "standard"
        base = _dt.date(2000, 1, 1)
        vt[:] = [(_dt.date(y, m, 1) - base).days for y, m in months]
        ds.createVariable("lat", "f8", ("lat",))[:] = np.asarray(lat, dtype=np.float64)
        ds.createVariable("lon", "f8", ("lon",))[:] = np.asarray(lon, dtype=np.float64)
        for name, arr in variables.items():
            v = ds.createVariable(name, "f4", (time_name, "lat", "lon"))
            v.units = units
            v[:] = np.asarray(arr, dtype=np.float32)
    return path


# ===================================================================================================== toy problems
def export_frame(export_dir: Path, columns: Sequence[str]) -> pd.DataFrame:
    """train + test rows of one export lead (the columns that exist in each part)."""
    import pyarrow.parquet as pq
    parts = []
    for part in ("train", "test"):
        for f in sorted((Path(export_dir) / part).glob("*.parquet")):
            names = pq.read_schema(str(f)).names
            parts.append(pq.read_table(str(f), columns=[c for c in columns if c in names]).to_pandas())
    return pd.concat(parts, ignore_index=True)


def grid_products(products_root: Path, export_dirs: Mapping[int, Path], fit_cut0: int) -> Dict[str, Any]:
    """The grid toy's product 'toy_grid' (folder products_root/toy_grid/v1, file toy_grid.nc):
      val   = the toy's own x1 at (unit, step) shifted to be >= 0.1 (an informative driver on the target scale),
              steps [first - 24, last]
      val2  = val^2 / 10 (a second statistic)
      noise = fixed-generator normal noise (a rival the guard should decline)
    Coverage hole (T-H12): for every unit of group grp_c, val, val2 and noise are NaN at every step >= the lead-0 fit
    cut, except 5 steps of the first grp_c unit, so grp_c keeps fewer than 10 (but more than 0) covered lead-0 test
    rows. Returns {folder, file, units, hole}."""
    f = export_frame(export_dirs[0], ["unit", "group", "time", "x__x1"])
    f = f.drop_duplicates(subset=["unit", "time"]).sort_values(["unit", "time"])
    units = sorted(f["unit"].astype(str).unique().tolist())
    groups = dict(zip(f["unit"].astype(str), f["group"].astype(str)))
    lo, hi = int(f["time"].min()) - 24, int(f["time"].max())
    steps = list(range(lo, hi + 1))
    ui = {u: i for i, u in enumerate(units)}
    val = np.full((len(units), len(steps)), np.nan)
    for u, t, x in zip(f["unit"].astype(str), f["time"].astype(np.int64), f["x__x1"].astype(np.float64)):
        val[ui[u], int(t) - lo] = x
    # fill the steps before a unit's first row with its first value (a product exists before the labels do)
    for i in range(len(units)):
        row = val[i]
        fin = np.flatnonzero(np.isfinite(row))
        if fin.size:
            row[:fin[0]] = row[fin[0]]
    # an N-kind product is on the target scale: shift x1 so every value is inside the toy's legal range [0, inf)
    val = val + (0.1 - float(np.nanmin(val)))
    rng = np.random.default_rng(TOY_RNG_SEED)
    noise = rng.normal(0.0, 1.0, size=val.shape)
    val2 = val ** 2 / 10.0
    grp_c = [u for u in units if groups[u] == "grp_c"]
    hole_units = grp_c[1:]
    j0 = int(fit_cut0) - lo
    for u in grp_c:
        keep = 5 if u == grp_c[0] else 0          # the first grp_c unit keeps 5 steps from the fit cut on
        val[ui[u], j0 + keep:] = np.nan
        val2[ui[u], j0 + keep:] = np.nan
        noise[ui[u], j0 + keep:] = np.nan
    folder = Path(products_root) / "toy_grid" / "v1"
    path = write_unit_step_nc(folder / "toy_grid.nc", units, steps, {"val": val, "val2": val2, "noise": noise})
    write_product_manifest(folder, "toy_grid", "v1", note="grid toy driver product (x1, x1^2/10, noise)")
    return {"folder": folder, "file": path, "units": units, "hole_units": hole_units, "first_step": lo}


def table_products(products_root: Path, export_dirs: Mapping[int, Path]) -> Dict[str, Any]:
    """The table toy's product 'toy_daily' (products_root/toy_daily/v1/toy_daily.npz): two smooth daily series per
    unit (a, b) from 800 days before the first visit to the last visit; and 'toy_outlook' (same layout, one series
    'w20' that starts at the median visit day: earlier targets are not covered, like the CRW Outlook archive)."""
    f = export_frame(export_dirs[0], ["unit", "time"])
    units = sorted(f["unit"].astype(str).unique().tolist())
    first, last = int(f["time"].min()) - 800, int(f["time"].max())
    days = np.arange(first, last + 1)
    a = np.stack([np.sin(days / 58.0 + i) for i in range(len(units))])
    b = np.stack([np.cos(days / 91.0 + 0.5 * i) for i in range(len(units))])
    d_folder = Path(products_root) / "toy_daily" / "v1"
    write_unit_day_npz(d_folder / "toy_daily.npz", units, first, last, {"a": a, "b": b})
    write_product_manifest(d_folder, "toy_daily", "v1", note="table toy daily driver")
    start = int(np.median(f["time"].to_numpy(np.int64)))
    w = np.stack([np.where(days >= start, np.round(2 + 2 * np.sin(days / 30.0 + i)), np.nan)
                  for i in range(len(units))])
    o_folder = Path(products_root) / "toy_outlook" / "v1"
    write_unit_day_npz(o_folder / "toy_outlook.npz", units, first, last, {"w20": w})
    write_product_manifest(o_folder, "toy_outlook", "v1", note="table toy forecast-only product")
    return {"daily": d_folder, "outlook": o_folder, "units": units, "outlook_start": start}


# ===================================================================================================== toy adapters
def _keys(ctx: Any, lead: int, stage: str) -> pd.DataFrame:
    """The rows the index table must hold (BUILD_NOTES_shared.txt: ctx.keys(set_name='stage'))."""
    k = ctx.keys("stage")
    return k[KEYS].reset_index(drop=True)


def _opts(rival: Mapping[str, Any]) -> Dict[str, Any]:
    return dict(rival.get("options") or {})


def grid_build(ctx: Any, rival: Mapping[str, Any], lead: int, stage: str) -> pd.DataFrame:
    """options: product (id), file, variables {stat: nc variable}, step_shift (product step = issue + shift),
    obs: 'none' (target_obs_end NaN) or 'same' (target_obs_end = the product step: the product assimilates the
    target's own source)."""
    o = _opts(rival)
    keys = _keys(ctx, lead, stage)
    path = ctx.open_product(o["product"], o["file"])
    step = keys["issue"].to_numpy(np.int64) + int(o.get("step_shift", 0))
    out = keys.copy()
    for stat, var in dict(o["variables"]).items():
        ui, si, vals = read_unit_step_nc(path, var)
        col = np.full(len(keys), np.nan)
        for r, (u, s) in enumerate(zip(keys["unit"].astype(str).tolist(), step.tolist())):
            i, j = ui.get(u), si.get(int(s))
            if i is not None and j is not None:
                col[r] = vals[i, j]
        out[stat] = col
    out["info_end"] = step.astype(np.int64)
    out["target_obs_end"] = step.astype(np.float64) if o.get("obs") == "same" else np.nan
    out["product_cell"] = keys["unit"].astype(str).to_numpy()
    out["src"] = str(o["file"])
    return out


def table_build(ctx: Any, rival: Mapping[str, Any], lead: int, stage: str) -> pd.DataFrame:
    """options: product, file, variables {stat: npz member}, anchor 'issue' or 'time', day_shift (product day =
    anchor + shift). info_end = the product day read; target_obs_end NaN (no label read)."""
    o = _opts(rival)
    keys = _keys(ctx, lead, stage)
    path = ctx.open_product(o["product"], o["file"])
    with np.load(str(path), allow_pickle=False) as z:
        units = [str(u) for u in z["unit"]]
        days = z["day"].astype(np.int64)
        data = {stat: z[m].astype(np.float64) for stat, m in dict(o["variables"]).items()}
    ui = {u: i for i, u in enumerate(units)}
    d0 = int(days[0])
    anchor = keys[o.get("anchor", "issue")].to_numpy(np.int64)
    day = anchor + int(o.get("day_shift", 0))
    out = keys.copy()
    for stat, arr in data.items():
        col = np.full(len(keys), np.nan)
        for r, (u, d) in enumerate(zip(keys["unit"].astype(str).tolist(), day.tolist())):
            i, j = ui.get(u), int(d) - d0
            if i is not None and 0 <= j < arr.shape[1]:
                col[r] = arr[i, j]
        out[stat] = col
    out["info_end"] = day.astype(np.int64)
    out["target_obs_end"] = np.nan
    out["product_cell"] = keys["unit"].astype(str).to_numpy()
    out["src"] = str(o["file"])
    return out


# ===================================================================================================== toy M runner
def fit(ctx: Any, rival: Mapping[str, Any], lead: int, fit_set: str) -> Dict[str, Any]:
    """Per-unit mean anomaly (y - identity normal) of the fit labels; pooled mean beside. Labels only through
    ctx.fit_labels (BUILD_NOTES_shared.txt: (keys, y, {link: normal}))."""
    keys, y, normals = ctx.fit_labels(fit_set)
    a = np.asarray(y, dtype=np.float64) - np.asarray(normals["identity"], dtype=np.float64)
    f = pd.DataFrame({"unit": keys["unit"].astype(str).to_numpy(), "a": a})
    means = f.groupby("unit", sort=True)["a"].mean()
    return {"anom": {str(k): float(v) for k, v in means.items()}, "pooled": float(np.mean(a)),
            "newest_label": int(keys["time"].max())}


def predict(ctx: Any, rival: Mapping[str, Any], lead: int, params: Mapping[str, Any], score_set: str) -> pd.DataFrame:
    """pre = the row's identity normal + the unit's mean anomaly (pooled for a unit without fit labels).
    info_end = target_obs_end = the newest fit label time; options.report_target_time: true reports the row's own
    target time instead (the shifted-label runner of T-H07, which the tool must refuse)."""
    s = ctx.features(score_set)
    keys = s.keys[KEYS].reset_index(drop=True)
    z0 = np.asarray(s.normal["identity"], dtype=np.float64)
    an = params["anom"]
    add = np.array([an.get(str(u), params["pooled"]) for u in keys["unit"].astype(str).tolist()], dtype=np.float64)
    out = keys.copy()
    out["pre"] = z0 + add
    newest = int(params["newest_label"])
    if _opts(rival).get("info_days_before_target") is not None:   # a forecast issued after our issue date (tier A)
        out["info_end"] = keys["time"].to_numpy(np.int64) - int(_opts(rival)["info_days_before_target"])
        out["target_obs_end"] = np.full(len(keys), float(newest))
    elif _opts(rival).get("report_target_time"):
        out["info_end"] = keys["time"].to_numpy(np.int64)
        out["target_obs_end"] = keys["time"].to_numpy(np.float64)
    else:
        out["info_end"] = np.full(len(keys), newest, dtype=np.int64)
        out["target_obs_end"] = np.full(len(keys), float(newest))
    return out


# ===================================================================================================== registries
NONE_6_12 = {"tier": "none", "reason": "toy: no forecast product reaches 6 or 12 steps"}
NONE_0 = {"tier": "none", "reason": "toy: the observed product is strictly better at the nowcast"}


def _rival(rid: str, kind: str, leads: Mapping[int, Any], *, adapter: Optional[str] = None,
           runner: Optional[str] = None, products: Sequence[str] = (), stats: Sequence[str] = (),
           families: Sequence[str] = (), t1: Sequence[str] = (), reads_test: bool = False,
           score_without_net: Sequence[int] = (), pick: str = "nowcast_inner", extras: Sequence[str] = (),
           options: Optional[Mapping[str, Any]] = None, label: str = "", coverage: Any = None) -> Dict[str, Any]:
    r: Dict[str, Any] = {"id": rid, "label": label or "toy rival %s" % rid, "kind": kind,
                         "leads": {int(k): (dict(v) if isinstance(v, Mapping) else v) for k, v in leads.items()},
                         "t1_kind_columns": list(t1), "reads_target_in_test_window": bool(reads_test),
                         "score_without_net": [int(x) for x in score_without_net], "pick": pick,
                         "slim_extra_columns": list(extras), "optional": False,
                         "r10_note": "toy rival (tests only)"}
    if adapter:
        r["adapter"] = adapter
        r["products"] = list(products)
        r["stats"] = list(stats)
        r["families"] = list(families)
    if runner:
        r["runner"] = runner
    if options:
        r["options"] = dict(options)
    if coverage is not None:
        r["coverage"] = coverage
    return r


ADAPTER_GRID = "rivals_human.tests.toy_products:grid_build"
ADAPTER_TABLE = "rivals_human.tests.toy_products:table_build"
RUNNER = "rivals_human.tests.toy_products"
GRID_EXTRAS = ["x__x1"]
TABLE_OUTLOOK_ISSUE_MIN = 733100      # a toy "archive start" (day ordinal = 2008-02-28), label-free
TABLE_EXTRAS = ["x__f1"]


def grid_registry(package: str, variant: str = "main") -> Dict[str, Any]:
    """The grid toy's rivals (a PM2.5 / NDVI-like problem):
      toy_lag1  N  P at 0 (product of step t-1, its own target source at t-1: passes T2); none at 6, 12
      toy_same  N  A at 0 (same-step product: breaks T2, printed beside toy_lag1); none at 6, 12
      toy_idx   I  P at 0, L at 6 and 12 (two stats; the pick is pinned and refit per lead)
      toy_noise I  P at 0 (pure noise: the guard should decline it)
      toy_m     M  P at 0, X (labelled extension) at 6 and 12 (runner; labels only through ctx.fit_labels)
    variant 'shifted_m': only toy_m_shift, an M runner that reports reading the target step (T-H07; refused).
    variant 'missing_extra': toy_lag1 naming a slim extra column the export lacks (T-H02; slim refuses)."""
    prod = {"product": "toy_grid", "file": "toy_grid.nc"}
    if variant == "shifted_m":
        rivals = [_rival("toy_m_shift", "M", {0: "P", 6: NONE_6_12, 12: NONE_6_12}, runner=RUNNER, t1=["x1"],
                         extras=GRID_EXTRAS, options={"report_target_time": True}, coverage="all_rows")]
    elif variant == "missing_extra":
        rivals = [_rival("toy_lag1", "N", {0: "P", 6: NONE_6_12, 12: NONE_6_12}, adapter=ADAPTER_GRID,
                         products=["toy_grid"], stats=["x__val"], families=["F0", "F1", "F3"], t1=["x1"],
                         extras=GRID_EXTRAS + ["x__not_in_the_export"],
                         options=dict(prod, variables={"x__val": "val"}, step_shift=-1, obs="same"))]
    else:
        rivals = [
            _rival("toy_lag1", "N", {0: "P", 6: NONE_6_12, 12: NONE_6_12}, adapter=ADAPTER_GRID,
                   products=["toy_grid"], stats=["x__val"], families=["F0", "F1", "F2", "F3", "F4", "F5"], t1=["x1"],
                   extras=GRID_EXTRAS, options=dict(prod, variables={"x__val": "val"}, step_shift=-1, obs="same")),
            _rival("toy_same", "N", {0: "A", 6: NONE_6_12, 12: NONE_6_12}, adapter=ADAPTER_GRID,
                   products=["toy_grid"], stats=["x__val"], families=["F0", "F1", "F3"], t1=["x1"],
                   extras=GRID_EXTRAS, options=dict(prod, variables={"x__val": "val"}, step_shift=0, obs="same")),
            _rival("toy_idx", "I", {0: "P", 6: "L", 12: "L"}, adapter=ADAPTER_GRID, products=["toy_grid"],
                   stats=["x__val", "x__val2"], families=["F2", "F3", "F4", "F5"], t1=["x1"], extras=GRID_EXTRAS,
                   options=dict(prod, variables={"x__val": "val", "x__val2": "val2"}, step_shift=0, obs="none")),
            _rival("toy_noise", "I", {0: "P", 6: NONE_6_12, 12: NONE_6_12}, adapter=ADAPTER_GRID,
                   products=["toy_grid"], stats=["x__noise"], families=["F3"], t1=["x1"], extras=GRID_EXTRAS,
                   options=dict(prod, variables={"x__noise": "noise"}, step_shift=0, obs="none")),
            _rival("toy_m", "M", {0: "P", 6: "X", 12: "X"}, runner=RUNNER, t1=["x1"], extras=GRID_EXTRAS,
                   coverage="all_rows"),
        ]
    return {"format": "human-registry/1", "package": package, "rivals": rivals,
            "nowcast_baseline_note": "the human baseline to beat (reference, Q4)"}


def table_registry(package: str) -> Dict[str, Any]:
    """The table toy's rivals (a coral-like problem). The engine's table toy is small (66 guard-fit, 73 tune rows),
    below the 100-row floor of a calibration map (Q2.HQ9), so the index rival is NOT calibratable at every lead (the
    disclosed no-row path) and the coral-like mechanics run through M runners (no map, no floor):
      toy_dhw      I  P at 0, L at 183 and 365 (a daily driver at issue - 2): not calibratable on this toy
      toy_dhw_m    M  P at 0, L at 183 and 365 (the toy runner)
      toy_outlook  M  forecast-only: none at 0, A at 183 and 365 (reports a forecast issued 40 days before the
                      target: breaks T1), picked on the guard rows of its lowest covered lead, 365 scored without the
                      safety net; label-free coverage: issue days from the median issue day on (an archive start)."""
    return {"format": "human-registry/1", "package": package, "rivals": [
        _rival("toy_dhw", "I", {0: "P", 183: "L", 365: "L"}, adapter=ADAPTER_TABLE, products=["toy_daily"],
               stats=["x__a", "x__b"], families=["F2", "F3", "F4"], extras=TABLE_EXTRAS,
               options={"product": "toy_daily", "file": "toy_daily.npz", "variables": {"x__a": "a", "x__b": "b"},
                        "anchor": "issue", "day_shift": -2}),
        _rival("toy_dhw_m", "M", {0: "P", 183: "L", 365: "L"}, runner=RUNNER, extras=TABLE_EXTRAS,
               coverage="all_rows"),
        _rival("toy_outlook", "M", {0: NONE_0, 183: "A", 365: "A"}, runner=RUNNER, extras=TABLE_EXTRAS,
               score_without_net=[365], pick="lowest_covered_lead_guard",
               options={"info_days_before_target": 40}, coverage={"issue_min": TABLE_OUTLOOK_ISSUE_MIN}),
    ]}


def products_registry(entries: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    """The product registry (1.8, registry/_products.yaml shape): {products: {id: {path, manifest, licence,
    source}}}."""
    return {"products": {pid: dict(rec) for pid, rec in entries.items()}}


def write_yaml(path: Path, obj: Any) -> Path:
    import yaml
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, sort_keys=False, default_flow_style=False), encoding="utf-8")
    return path
