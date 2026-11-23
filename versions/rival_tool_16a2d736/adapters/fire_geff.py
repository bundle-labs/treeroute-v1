"""Fire human rivals F-ERA5 and F-SEAS5: the CEMS GEFF Fire Weather Index (FWI) per unit and target month.

SPEC_HUMAN_PARTB.txt sections 3.1-3.8 (builder B1). Kind I (an index: the tool's maps F2-F6, fitted on training rows
only, turn it into a burned fraction). One index table per rival x lead, written in one go (stage "all"; FWI reads no
label): keys, x__fwi_mean, x__fwi_pct, info_end, target_obs_end (NaN: FWI observes no burned area), product_cell, src.

Plain idea:
  kind era5_daily (geff_era5, lead 0; product D2 = CEMS GEFF-ERA5 v4.1, daily, 0.25 deg): x__fwi_mean of a row is the
    mean of the daily FWI at the unit's grid point over the calendar days of the row's target month t. The run reads
    target-month weather (R8 steps 0 for the FWI inputs), so this is parity (Q3). info_end = t.
  kind seas5_daily_leads (geff_seas5, lead 6; product D3 = CEMS GEFF-SEAS5, daily leads 150-184, 1 deg): the forecast
    started at 00 UTC on the 1st of month t-5, which is the end of the issue month (Q16); x__fwi_mean = the mean over
    members 0-24 (by `number` value) and the daily leads whose valid date lies in month t (the whole month always lies
    inside leads 150-184). info_end = the issue (the forecast's initial state).
  x__fwi_pct (both kinds, 3.6): the unit's mid-rank percentile among its own same-calendar-month x__fwi_mean of target
    months up to the lead's GUARD cut, the row's own month left out. The pick rows (lead-0 inner, lead-6 guard) run on
    the guard-cut normal and history, so the one reference legal for every set is the guard-cut one; every row (pick,
    refit, test) is then ranked out of sample against FWI known before its issue (asserted).
Units -> grid (3.3): a unit takes its nearest point of its box (haversine over ALL points, first minimum in
latitude-major file order). Longitudes are wrapped to [-180, 180) first: the old fire_cems.py matcher compared -100
with 256..263 and snapped every western unit to one column (PEND Part 620). A point is land ("valid") when it is finite
somewhere in EVERY file of its box; a unit whose nearest point is sea takes the nearest valid point within
sea_window_steps grid steps (counted, distance recorded), else it is uncovered (counted; refuse above
max_uncovered_unit_share of the bank units). The window is taken in each axis's spatial order (the axis sorted by its
wrapped value), which is the file's index order for a monotonic axis and stays right for a 0-360 file whose box
crosses 0 deg (non-monotonic in the file).
Daily -> monthly (3.5): a unit-month is covered only when its finite cells (days; members x days for SEAS5) make at
least min_day_share of the month's cells (MINDAYS), else NaN (counted). Two passes per box (3.8): the valid mask from
every file, then, once the units are mapped, the selected points only (vectorised isel); each point's cells of a month
are summed as one contiguous float64 row, so a unit-month equals a plain numpy mean of the same values.

The fetcher's layout is the only layout read (fetch_products.py spec_D2 / spec_D3 and its product_manifest.json): the
manifest must say "complete": true, every file must match its request (dataset, the registry's request_check keys,
SEAS5 leadtime_hour, area [N, W, S, E] with W <= E, regions), and each file is opened through ctx.open_product (sha256
against the manifest), one file at a time, read with xarray and closed. The netCDF check covers fwinx's dims and the
named coordinates only; an extra SCALAR coordinate (every RAW file has `surface`) and extra data variables are ignored.

The AdapterCtx calls used here (index.AdapterCtx; SPEC_HUMAN_PARTB 1.2):
  ctx.products[pid]             the product registry entry; availability() reads its fetcher manifest itself
  ctx.product_root(pid)         the folder of the fetcher's product_manifest.json
  ctx.product_files(pid)        the file names the manifest lists
  ctx.open_product(pid, name)   the path of one listed file after its sha256 check
  ctx.keys(set)                 keys of "stage" (all), "test", "inner" (lead 0) or "guard" (a lead >= 1)
  ctx.units()                   the bank units (unit, group, ...)
  ctx.run                       .cuts[L]["guard_cut"], .derived (R2 steps per year)
  ctx.work_dir(), ctx.write_bytes(path, data), ctx.log(message)
availability() deliberately does not use the tool's product_available / index.product_status, nor the pm25
template: those refuse only "complete": false, and a first or killed fetcher run leaves a manifest with NO "complete"
key, so a half-downloaded D2 / D3 would count as on disk and init would pin it (ATTENTION B8). Here "complete" must be
true.
Nothing here opens a label, a slim set, test_preds or the fire target store (T-F17). No import of the common harness,
the engine or the old fire_cems.py.
"""
# Provenance: SPEC_HUMAN_PARTB.txt 3.1-3.8, 2.2-2.3 (options); fetch_products.py spec_D2 :295-320, spec_D3 :323-359,
# seas_request :206-210 (leadtime_hour 12 + 24 k), _run_product :724-809 (manifest files / requests / complete);
# research_fire.md 1.1-1.2, 2 (C-A); RAW formats D:/fire/cems/raw (xarray 2024.7.0: ERA5 dims (valid_time, latitude,
# longitude); SEAS5 dims (number, time, step, latitude, longitude), valid_time (time, step), scalar `surface`).

import calendar
import datetime as _dt
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

ADAPTER_FORMAT = "human-adapter-fire-geff/1"
KINDS = ("era5_daily", "seas5_daily_leads")
EARTH_RADIUS_KM = 6371.0
KEYS = ("unit", "group", "time", "issue", "lead")
STAT_MEAN = "x__fwi_mean"
STAT_PCT = "x__fwi_pct"
STATS = (STAT_MEAN, STAT_PCT)
MONTHS_PER_YEAR = 12
MANIFEST_NAME = "product_manifest.json"
FILE_PREFIX = {"era5_daily": "hist_", "seas5_daily_leads": "seas_"}      # fetch_products.py :312, :356
FILE_RX = re.compile(r"^(?P<prefix>hist_|seas_)(?P<box>.+)_(?P<tag>\d{4}(?:-\d{4})?)\.nc$")
PCT_REFERENCE_ENDS = ("lead_guard_cut",)
PICK_SET = {True: "inner", False: "guard"}          # the pick score set: inner at the nowcast, guard at a lead >= 1
SEAS_VALID_HOUR = 12                                # leadtime_hour 12 + 24 k: the valid time is noon of day k
UNIT_CHUNK = 64                                     # units per haversine block (64 x 33k points x 8 B = 17 MB)
DEFAULT_WAITING = ("product %s is not on disk, or its fetcher manifest (product_manifest.json) does not say "
                   "\"complete\": true")


class FireGeffRefusal(RuntimeError):
    """A fire GEFF adapter rule refused (fail loud; nothing in this module catches it)."""


def _refuse(message: str, fix: Optional[str] = None):
    raise FireGeffRefusal(message + ("" if not fix else "  FIX: " + fix))


# ---------------------------------------------------------------------------------------------------
# Rival options (registry/fire.yaml `options`; data, not code)
def _options(rival: Mapping[str, Any]) -> Dict[str, Any]:
    rid = rival.get("id")
    opt = dict(rival.get("options") or {})
    for k in ("kind", "product", "dataset", "request_check", "variable", "unit_centres", "min_day_share",
              "sea_window_steps", "max_uncovered_unit_share", "pct_reference_end", "pct_min_reference"):
        if k not in opt:
            _refuse("rival %s: registry options lack %r" % (rid, k))
    if opt["kind"] not in KINDS:
        _refuse("rival %s: unknown kind %r (known: %s)" % (rid, opt["kind"], ", ".join(KINDS)))
    if not isinstance(opt["request_check"], Mapping) or not opt["request_check"]:
        _refuse("rival %s: options.request_check must map request keys to their exact values" % rid)
    uc = opt["unit_centres"]
    if not isinstance(uc, Mapping) or any(k not in uc for k in ("product", "file", "id", "lat", "lon")):
        _refuse("rival %s: options.unit_centres needs product, file, id, lat, lon" % rid)
    if opt["kind"] == "era5_daily":
        if "target_months_offset" not in opt:
            _refuse("rival %s: kind era5_daily needs options.target_months_offset" % rid)
        opt["target_months_offset"] = int(opt["target_months_offset"])
    else:
        for k in ("start_months_before_target", "lead_days", "members"):
            if k not in opt:
                _refuse("rival %s: kind seas5_daily_leads needs options.%s" % (rid, k))
        opt["start_months_before_target"] = int(opt["start_months_before_target"])
        ld = [int(v) for v in opt["lead_days"]]
        mb = [int(v) for v in opt["members"]]
        if len(ld) != 2 or not 0 <= ld[0] <= ld[1]:
            _refuse("rival %s: options.lead_days must be [first, last] daily leads, got %s" % (rid, opt["lead_days"]))
        if len(mb) != 2 or not 0 <= mb[0] <= mb[1]:
            _refuse("rival %s: options.members must be [first, last] member numbers, got %s" % (rid, opt["members"]))
        if opt["start_months_before_target"] < 1:
            _refuse("rival %s: start_months_before_target must be >= 1" % rid)
        opt["lead_days"], opt["members"] = (ld[0], ld[1]), (mb[0], mb[1])
    if opt["pct_reference_end"] not in PCT_REFERENCE_ENDS:
        _refuse("rival %s: pct_reference_end %r is not one of %s (SPEC_HUMAN_PARTB 3.6)"
                % (rid, opt["pct_reference_end"], PCT_REFERENCE_ENDS))
    opt["min_day_share"] = float(opt["min_day_share"])
    opt["sea_window_steps"] = int(opt["sea_window_steps"])
    opt["max_uncovered_unit_share"] = float(opt["max_uncovered_unit_share"])
    opt["pct_min_reference"] = int(opt["pct_min_reference"])
    if not 0.0 < opt["min_day_share"] <= 1.0:
        _refuse("rival %s: min_day_share must lie in (0, 1]" % rid)
    if opt["sea_window_steps"] < 0 or not 0.0 <= opt["max_uncovered_unit_share"] <= 1.0 or opt["pct_min_reference"] < 1:
        _refuse("rival %s: sea_window_steps >= 0, max_uncovered_unit_share in [0, 1], pct_min_reference >= 1" % rid)
    stats = [str(s) for s in (rival.get("stats") or [])]
    if not stats or any(s not in STATS for s in stats) or len(set(stats)) != len(stats):
        _refuse("rival %s: stats must be drawn from %s, got %s" % (rid, list(STATS), stats))
    opt["stats"] = stats
    return opt


# ---------------------------------------------------------------------------------------------------
# Steps. The engine's monthly step: year x 12 + month (24037 = 2003-01; SPEC_HUMAN_PARTB facts).
def steps_per_year(run: Any) -> int:
    d = getattr(run, "derived", None) or {}
    spy = None
    for path in (("R2", "value", "steps_per_year"), ("R17", "inputs", "steps_per_year")):
        try:
            v = d
            for k in path:
                v = v[k]
            spy = int(v)
            break
        except (KeyError, TypeError, ValueError):
            continue
    if spy is None:
        _refuse("the run's derived.json gives no steps per year (R2 value or R17 inputs)")
    if spy != MONTHS_PER_YEAR:
        _refuse("the run has %d steps per year; the monthly FWI rivals need a monthly run (12)" % spy)
    return spy


def step_of(year: Any, month: Any) -> np.ndarray:
    return np.asarray(year, dtype=np.int64) * MONTHS_PER_YEAR + np.asarray(month, dtype=np.int64)


def year_month(step: Any) -> Tuple[np.ndarray, np.ndarray]:
    s = np.asarray(step, dtype=np.int64)
    return (s - 1) // MONTHS_PER_YEAR, (s - 1) % MONTHS_PER_YEAR + 1


def _as_date(d: Any) -> _dt.date:
    if isinstance(d, _dt.datetime):
        return d.date()
    if isinstance(d, _dt.date):
        return d
    return pd.Timestamp(d).date()


# ---------------------------------------------------------------------------------------------------
# Availability (SPEC_HUMAN_PARTB 3.1): the fetcher's own manifest, "complete" must be true
def _manifest_entry(ctx: Any, rival: Mapping[str, Any], opt: Mapping[str, Any]) -> Tuple[Path, str]:
    pid = str(opt["product"])
    if pid not in (rival.get("products") or []):
        _refuse("rival %s: options.product %r is not in its products list" % (rival.get("id"), pid))
    rec = (ctx.products or {}).get(pid)
    if rec is None:
        _refuse("product %r is not in the product registry (registry/_products.yaml)" % pid)
    mpath = rec.get("manifest")
    if not mpath:
        _refuse("product %s names no fetcher manifest (`manifest` in registry/_products.yaml); the FWI products are "
                "downloads of fetch_products.py (D2 / D3)" % pid)
    return Path(str(mpath)), str(rec.get("waiting_line") or DEFAULT_WAITING % pid)


def _complete_manifest(path: Path) -> Optional[Dict[str, Any]]:
    """The manifest when it exists, is JSON, lists files and says "complete": true; else None (never refuses)."""
    if not path.is_file():
        return None
    try:
        with open(str(path), "r", encoding="utf-8") as fh:
            man = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(man, Mapping) or not isinstance(man.get("files"), Mapping) or not man["files"]:
        return None
    if man.get("complete") is not True:            # a missing key (first or killed fetcher run) waits too
        return None
    return dict(man)


def availability(ctx: Any, rival: Mapping[str, Any]) -> Tuple[bool, str]:
    """(on disk and complete?, plain line). Waiting -> the product's waiting_line; ready -> "<n> files, complete"."""
    opt = _options(rival)
    mpath, line = _manifest_entry(ctx, rival, opt)
    man = _complete_manifest(mpath)
    if man is None:
        return False, line
    return True, "%d files, complete" % len(man["files"])


# ---------------------------------------------------------------------------------------------------
# The fetcher's layout (SPEC_HUMAN_PARTB 3.2)
def _same_file(a: Path, b: Path) -> bool:
    import os
    try:
        return os.path.samefile(str(a), str(b))
    except OSError:
        return os.path.normcase(str(a.resolve())) == os.path.normcase(str(b.resolve()))


def check_manifest(ctx: Any, rival: Mapping[str, Any], opt: Mapping[str, Any]
                   ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, str]]:
    """(manifest, layout table, region -> box). Refuses with the waiting_line when the product is not complete, and on
    any file / request that is not the fetcher's own."""
    pid, kind = str(opt["product"]), opt["kind"]
    mpath, line = _manifest_entry(ctx, rival, opt)
    if _complete_manifest(mpath) is None:
        _refuse(line)
    root = Path(str(ctx.product_root(pid)))
    if not _same_file(root / MANIFEST_NAME, mpath):
        _refuse("product %s: the registry manifest %s is not the %s of its product folder %s"
                % (pid, mpath, MANIFEST_NAME, root))
    with open(str(root / MANIFEST_NAME), "r", encoding="utf-8") as fh:
        man = json.load(fh)
    if man.get("complete") is not True:
        _refuse(line)
    if str(man.get("dataset")) != str(opt["dataset"]):
        _refuse("product %s: the manifest's dataset is %r, the registry expects %r" % (pid, man.get("dataset"),
                                                                                      opt["dataset"]))
    files, requests = man.get("files"), man.get("requests")
    if not isinstance(requests, Mapping) or not requests:
        _refuse("product %s: the manifest holds no `requests` block (not the fetcher's format)" % pid)
    names = sorted(str(n) for n in ctx.product_files(pid))
    if set(names) != set(str(n) for n in files):
        _refuse("product %s: the listed files differ from the manifest's (only in the listing %s; only in the manifest "
                "%s)" % (pid, sorted(set(names) - set(files))[:3], sorted(set(files) - set(names))[:3]))
    lo_hi = opt.get("lead_days")
    entries = []
    for name in names:
        e = files[name]
        rid = e.get("request_id") if isinstance(e, Mapping) else None
        r = requests.get(rid) if rid is not None else None
        if not isinstance(r, Mapping):
            _refuse("product %s: file %s names request %r, which the manifest does not hold" % (pid, name, rid))
        if str(r.get("file")) != name:
            _refuse("product %s: request %s names file %r, not %s" % (pid, rid, r.get("file"), name))
        req = r.get("request")
        if not isinstance(req, Mapping):
            _refuse("product %s: request %s holds no `request` mapping" % (pid, rid))
        for k, want in opt["request_check"].items():
            if req.get(k) != want:
                _refuse("product %s: request %s holds %s = %r; the registry expects exactly %r"
                        % (pid, rid, k, req.get(k), want), fix="a different product needs its own registry entry")
        if kind == "seas5_daily_leads":
            want_lh = [str(SEAS_VALID_HOUR + 24 * k) for k in range(lo_hi[0], lo_hi[1] + 1)]
            if list(req.get("leadtime_hour") or []) != want_lh:
                _refuse("product %s: request %s leadtime_hour is not 12 + 24 k for k = %d..%d"
                        % (pid, rid, lo_hi[0], lo_hi[1]))
        area = req.get("area")
        if not isinstance(area, (list, tuple)) or len(area) != 4:
            _refuse("product %s: request %s area %r is not [N, W, S, E]" % (pid, rid, area))
        N, W, S, E = (float(a) for a in area)
        if not (W <= E and S <= N):
            _refuse("product %s: request %s area %s has W > E or S > N (an antimeridian box is not read)"
                    % (pid, rid, area))
        regions = r.get("regions")
        if not isinstance(regions, list) or not regions or not all(isinstance(g, str) for g in regions):
            _refuse("product %s: request %s names no regions" % (pid, rid))
        m = FILE_RX.match(name)
        if m is None or m.group("prefix") != FILE_PREFIX[kind]:
            _refuse("product %s: file %s is not named %s<box>_<year tag>.nc (fetch_products.py)"
                    % (pid, name, FILE_PREFIX[kind]))
        years = sorted(int(y) for y in (req.get("year") or []))
        months = sorted(int(x) for x in (req.get("month") or []))
        if not years or len(set(years)) != len(years) or not months or len(set(months)) != len(months) \
                or not all(1 <= x <= MONTHS_PER_YEAR for x in months):
            _refuse("product %s: request %s years %s / months %s are not a clean list" % (pid, rid, req.get("year"),
                                                                                        req.get("month")))
        tags = {"%d-%d" % (years[0], years[-1])} | ({"%d" % years[0]} if len(years) == 1 else set())
        if m.group("tag") not in tags:
            _refuse("product %s: file %s carries year tag %s, its request asks years %s" % (pid, name, m.group("tag"),
                                                                                        years))
        entries.append({"file": name, "box": m.group("box"), "regions": sorted(str(g) for g in regions),
                        "area": [N, W, S, E], "years": years, "months": months})
    by_box: Dict[str, List[Dict[str, Any]]] = {}
    for e in entries:
        by_box.setdefault(e["box"], []).append(e)
    region_box: Dict[str, str] = {}
    for box in sorted(by_box):
        es = by_box[box]
        if any(e["regions"] != es[0]["regions"] or e["area"] != es[0]["area"] for e in es):
            _refuse("product %s: the files of box %s name different regions or areas" % (pid, box))
        for g in es[0]["regions"]:
            if g in region_box and region_box[g] != box:
                _refuse("product %s: region %s is named by two boxes (%s and %s)" % (pid, g, region_box[g], box))
            region_box[g] = box
    return man, entries, region_box


# ---------------------------------------------------------------------------------------------------
# Geometry (SPEC_HUMAN_PARTB 3.3): the explicit longitude wrap, haversine, units -> grid points
def wrap_lon(lon: Any) -> np.ndarray:
    """Longitude in [-180, 180): ((lon + 180) mod 360) - 180 (a 0-360 western value 256.25 -> -103.75)."""
    return np.mod(np.asarray(lon, dtype=np.float64) + 180.0, 360.0) - 180.0


def haversine_km(lat1: Any, lon1: Any, lat2: Any, lon2: Any) -> np.ndarray:
    """Great-circle distance on a sphere of EARTH_RADIUS_KM; inputs cast to float64 FIRST (RF:26), broadcast."""
    p1 = np.radians(np.asarray(lat1, dtype=np.float64))
    p2 = np.radians(np.asarray(lat2, dtype=np.float64))
    dl = np.radians(np.asarray(lon2, dtype=np.float64) - np.asarray(lon1, dtype=np.float64))
    a = np.sin((p2 - p1) / 2.0) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2.0) ** 2
    return 2.0 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def _ranks(axis: np.ndarray) -> np.ndarray:
    """The position of each axis value in the axis sorted ascending (the spatial order)."""
    r = np.empty(axis.size, dtype=np.int64)
    r[np.argsort(axis, kind="mergesort")] = np.arange(axis.size, dtype=np.int64)
    return r


def map_units(grid_lat: Any, grid_lon: Any, valid: Any, unit_lat: Any, unit_lon: Any,
              window_steps: int) -> Dict[str, np.ndarray]:
    """Each unit's grid point. grid_lat (nlat), grid_lon (nlon): the file's own 1-D axes (any order; longitudes 0-360
    or -180..180); valid (nlat, nlon) bool. Nearest point = argmin of haversine over ALL points (first minimum in
    latitude-major file order). A sea nearest point -> the nearest VALID point with |di| <= window_steps and
    |dj| <= window_steps around it (axis positions in spatial order), same tie rule; none -> uncovered.
    Returns per unit: i, j (int64; -1 when uncovered), substituted, dist_km (NaN when uncovered), uncovered, and the
    raw nearest point nearest_i, nearest_j, nearest_km."""
    glat = np.asarray(grid_lat, dtype=np.float64)
    glon = wrap_lon(grid_lon)
    if glat.ndim != 1 or glon.ndim != 1 or not glat.size or not glon.size:
        _refuse("map_units needs the 1-D latitude and longitude axes of the file")
    val = np.asarray(valid, dtype=bool)
    if val.shape != (glat.size, glon.size):
        _refuse("map_units: valid mask shape %s differs from the axes (%d, %d)" % (val.shape, glat.size, glon.size))
    if not (np.isfinite(glat).all() and np.isfinite(glon).all()):
        _refuse("map_units: the grid axes hold a missing value")
    if np.unique(glat).size != glat.size or np.unique(glon).size != glon.size:
        _refuse("map_units: the grid repeats a latitude or a (wrapped) longitude")
    ulat = np.asarray(unit_lat, dtype=np.float64).ravel()
    ulon = wrap_lon(unit_lon).ravel()
    if ulat.size != ulon.size:
        _refuse("map_units: %d unit latitudes, %d longitudes" % (ulat.size, ulon.size))
    if not (np.isfinite(ulat).all() and np.isfinite(ulon).all()):
        _refuse("map_units: a unit centre holds a missing latitude or longitude")
    w = int(window_steps)
    nlat, nlon = glat.size, glon.size
    rlat, rlon = _ranks(glat), _ranks(glon)
    plat, plon = np.repeat(glat, nlon), np.tile(glon, nlat)               # latitude-major (file C order)
    n = ulat.size
    out = {"i": np.full(n, -1, dtype=np.int64), "j": np.full(n, -1, dtype=np.int64),
           "substituted": np.zeros(n, dtype=bool), "dist_km": np.full(n, np.nan), "uncovered": np.zeros(n, dtype=bool),
           "nearest_i": np.full(n, -1, dtype=np.int64), "nearest_j": np.full(n, -1, dtype=np.int64),
           "nearest_km": np.full(n, np.nan)}
    for a in range(0, n, UNIT_CHUNK):
        b = min(n, a + UNIT_CHUNK)
        d = haversine_km(ulat[a:b, None], ulon[a:b, None], plat[None, :], plon[None, :])
        k = np.argmin(d, axis=1)                                          # first minimum: deterministic
        for r in range(b - a):
            u = a + r
            i0, j0 = divmod(int(k[r]), nlon)
            out["nearest_i"][u], out["nearest_j"][u], out["nearest_km"][u] = i0, j0, d[r, k[r]]
            if val[i0, j0]:
                out["i"][u], out["j"][u], out["dist_km"][u] = i0, j0, d[r, k[r]]
                continue
            rows = np.flatnonzero(np.abs(rlat - rlat[i0]) <= w)           # file order, ascending
            cols = np.flatnonzero(np.abs(rlon - rlon[j0]) <= w)
            ci, cj = np.nonzero(val[np.ix_(rows, cols)])                  # row-major: latitude-major file order
            if not ci.size:
                out["uncovered"][u] = True
                continue
            fi, fj = rows[ci], cols[cj]
            dd = d[r, fi * nlon + fj]
            q = int(np.argmin(dd))
            out["i"][u], out["j"][u], out["dist_km"][u] = fi[q], fj[q], dd[q]
            out["substituted"][u] = True
    return out


def product_cell_id(box: str, lat: Any, lon: Any) -> str:
    """The resolution-matched cell key "<box>|<lat %.3f>|<lon %.3f>" (longitude wrapped)."""
    return "%s|%.3f|%.3f" % (box, float(lat), float(wrap_lon(lon)))


# ---------------------------------------------------------------------------------------------------
# SEAS5 lead window (SPEC_HUMAN_PARTB 3.5)
def month_days_in_window(start_date: Any, target_year: int, target_month: int, lead_days: Sequence[int]) -> List[int]:
    """The daily leads k whose valid date (start + k days; valid time start + k days + 12 h) lies in the target month.
    Refuses when the month is not wholly inside [lead_days[0], lead_days[1]] (never expected for start M-5)."""
    s = _as_date(start_date)
    first = _dt.date(int(target_year), int(target_month), 1)
    ndays = calendar.monthrange(int(target_year), int(target_month))[1]
    d0 = (first - s).days
    lo, hi = int(lead_days[0]), int(lead_days[1])
    if d0 < lo or d0 + ndays - 1 > hi:
        _refuse("target month %04d-%02d of the start %s needs daily leads %d..%d, outside the window %d..%d"
                % (int(target_year), int(target_month), s.isoformat(), d0, d0 + ndays - 1, lo, hi))
    return list(range(d0, d0 + ndays))


# ---------------------------------------------------------------------------------------------------
# The per-unit percentile (SPEC_HUMAN_PARTB 3.6)
def fwi_percentile(unit: Any, time: Any, x: Any, t_ref: int, steps_per_year: int, min_ref: int) -> np.ndarray:
    """p(u, t) = (#{r in R : r < x} + 0.5 #{r in R : r == x}) / |R|, R(u, t) = {x(u, t') : t' <= t_ref, same
    calendar position as t, t' != t, finite} (float64 compares). |R| < min_ref or x NaN -> NaN. One row per (unit,
    time) is expected (refused otherwise)."""
    u = np.asarray(unit).astype(str)
    t = np.asarray(time, dtype=np.int64)
    xv = np.asarray(x, dtype=np.float64)
    if not (u.size == t.size == xv.size):
        _refuse("fwi_percentile: unit, time and x differ in length")
    spy = int(steps_per_year)
    pos = np.mod(t - 1, spy) + 1
    frame = pd.DataFrame({"u": u, "t": t})
    if frame.duplicated().any():
        _refuse("fwi_percentile: a (unit, time) appears twice")
    in_ref = (t <= int(t_ref)) & np.isfinite(xv)
    out = np.full(xv.size, np.nan)
    groups = pd.DataFrame({"u": u, "p": pos}).groupby(["u", "p"], sort=True).indices
    for _key, idx in groups.items():
        idx = np.asarray(idx, dtype=np.int64)
        ref = np.sort(xv[idx[in_ref[idx]]])
        xs = xv[idx]
        less = np.searchsorted(ref, xs, side="left").astype(np.float64)
        equal = np.searchsorted(ref, xs, side="right").astype(np.float64) - less
        own = in_ref[idx].astype(np.float64)                 # the row's own month is in R: leave it out
        equal -= own
        nref = float(ref.size) - own
        ok = np.isfinite(xs) & (nref >= int(min_ref))
        out[idx[ok]] = (less[ok] + 0.5 * equal[ok]) / nref[ok]
    return out


def reference_info_end(opt: Mapping[str, Any], t_ref: int) -> int:
    """The newest data time any reference value carries (its info_end by the 3.5 rule)."""
    if opt["kind"] == "era5_daily":
        return int(t_ref)
    return int(t_ref) - int(opt["start_months_before_target"]) - 1


def check_reference_timing(ctx: Any, opt: Mapping[str, Any], lead: int, t_ref: int) -> Dict[str, Any]:
    """3.6 asserts: T_ref < the smallest test time; the newest reference info_end < the smallest issue of the lead's
    pick score set (inner at lead 0, guard at a lead >= 1) and < the smallest test issue."""
    test = ctx.keys("test")
    pick = PICK_SET[int(lead) == 0]
    pk = ctx.keys(pick)
    if not len(test) or not len(pk):
        _refuse("lead %d: the %s set holds no key; the percentile's out-of-sample rule cannot be checked"
                % (int(lead), "test" if not len(test) else pick))
    t_test = int(np.asarray(test["time"], dtype=np.int64).min())
    i_test = int(np.asarray(test["issue"], dtype=np.int64).min())
    i_pick = int(np.asarray(pk["issue"], dtype=np.int64).min())
    newest = reference_info_end(opt, t_ref)
    if int(t_ref) >= t_test:
        _refuse("x__fwi_pct reference end %d (the lead-%d guard cut) is not before the first test month %d"
                % (int(t_ref), int(lead), t_test))
    if newest >= i_pick or newest >= i_test:
        _refuse("x__fwi_pct reference values carry information to step %d, not before the first %s issue %d and the "
                "first test issue %d (SPEC_HUMAN_PARTB 3.6)" % (newest, pick, i_pick, i_test))
    return {"t_ref": int(t_ref), "reference_info_end_max": newest, "pick_set": pick, "pick_issue_min": i_pick,
            "test_time_min": t_test, "test_issue_min": i_test}


# ---------------------------------------------------------------------------------------------------
# Unit centres (every bank unit must match exactly one cell_id of the engine's static table)
def unit_centres(ctx: Any, opt: Mapping[str, Any], units: Sequence[str]) -> pd.DataFrame:
    import pyarrow.dataset as ds

    uc = opt["unit_centres"]
    path = Path(str(ctx.open_product(str(uc["product"]), str(uc["file"]))))
    idc, latc, lonc = str(uc["id"]), str(uc["lat"]), str(uc["lon"])
    want = sorted(set(str(u) for u in units))
    tab = ds.dataset(str(path), format="parquet").to_table(
        columns=[idc, latc, lonc], filter=ds.field(idc).isin(want)).to_pandas()
    tab[idc] = tab[idc].astype(str)
    if tab[idc].duplicated().any():
        _refuse("unit centres file %s names a cell twice (%s)" % (path, tab.loc[tab[idc].duplicated(), idc].iloc[0]))
    missing = sorted(set(want) - set(tab[idc]))
    if missing:
        _refuse("%d unit(s) match no %s in %s (first %s)" % (len(missing), idc, path, missing[:3]))
    out = tab.rename(columns={idc: "unit", latc: "lat", lonc: "lon"}).set_index("unit").loc[want].reset_index()
    out["lat"] = out["lat"].astype(np.float64)
    out["lon"] = out["lon"].astype(np.float64)
    if not (np.isfinite(out["lat"]).all() and np.isfinite(out["lon"]).all()):
        _refuse("unit centres hold a missing latitude or longitude")
    return out


# ---------------------------------------------------------------------------------------------------
# Reading one netCDF file (layout check, then the per-month / per-start sums of the whole box grid)
def _open_netcdf(path: Any):
    import xarray as xr

    return xr.open_dataset(str(path), decode_times=True)


def _check_variable(ds: Any, opt: Mapping[str, Any], name: str) -> Dict[str, Any]:
    """fwinx's dims and the named coordinates (3.2); extra scalar coordinates and other data variables are ignored."""
    var = str(opt["variable"])

    def listing() -> str:
        return "variables %s, coordinates %s" % (sorted(str(v) for v in ds.data_vars),
                                                 sorted(str(c) for c in ds.coords))

    if var not in ds.data_vars:
        _refuse("file %s holds no variable %r (%s)" % (name, var, listing()))
    v = ds[var]
    dims = tuple(str(d) for d in v.dims)
    scalar_time = False
    if opt["kind"] == "era5_daily":
        if len(dims) != 3 or dims[0] not in ("valid_time", "time") or dims[1:] != ("latitude", "longitude"):
            _refuse("file %s: %s has dims %s, not (valid_time | time, latitude, longitude) (%s)" % (name, var, dims,
                                                                                                    listing()))
        named = {dims[0]: (dims[0],), "latitude": ("latitude",), "longitude": ("longitude",)}
        kinds = {dims[0]: "M", "latitude": "f", "longitude": "f"}
    else:
        if dims == ("number", "time", "step", "latitude", "longitude"):
            scalar_time = False
        elif dims == ("number", "step", "latitude", "longitude"):
            scalar_time = True
        else:
            _refuse("file %s: %s has dims %s, not (number, time, step, latitude, longitude) or (number, step, "
                    "latitude, longitude) with a scalar time (%s)" % (name, var, dims, listing()))
        named = {"number": ("number",), "time": () if scalar_time else ("time",), "step": ("step",),
                 "latitude": ("latitude",), "longitude": ("longitude",),
                 "valid_time": ("step",) if scalar_time else ("time", "step")}
        kinds = {"number": "iu", "time": "M", "step": "m", "latitude": "f", "longitude": "f", "valid_time": "M"}
    for c, cdims in named.items():
        if c not in v.coords:
            _refuse("file %s: %s lacks the coordinate %r (%s)" % (name, var, c, listing()))
        got = tuple(str(d) for d in v.coords[c].dims)
        if got != cdims:
            _refuse("file %s: coordinate %s has dims %s, expected %s (%s)" % (name, c, got, cdims, listing()))
        if v.coords[c].dtype.kind not in kinds[c]:
            _refuse("file %s: coordinate %s has dtype %s (%s)" % (name, c, v.coords[c].dtype, listing()))
    extra = [str(c) for c in v.coords if str(c) not in named and v.coords[c].ndim != 0]
    if extra:
        _refuse("file %s: %s carries non-scalar extra coordinates %s (%s)" % (name, var, extra, listing()))
    lat = np.asarray(v.coords["latitude"].values, dtype=np.float64)
    lon = np.asarray(v.coords["longitude"].values, dtype=np.float64)
    if not lat.size or not lon.size:
        _refuse("file %s: an empty latitude or longitude axis" % name)
    return {"v": v, "dims": dims, "scalar_time": scalar_time, "lat": lat, "lon": lon}


def _era5_plan(lay: Mapping[str, Any], entry: Mapping[str, Any]) -> Dict[str, Any]:
    """The month blocks of one ERA5 file: [(month step, first day, end day, days, info_end)]. Its valid dates must be
    exactly every calendar day of the request years (no gap, no duplicate, no date outside)."""
    v, name = lay["v"], entry["file"]
    t = np.asarray(v.coords[lay["dims"][0]].values).astype("datetime64[ns]")
    days = t.astype("datetime64[D]")
    tod = t - days.astype("datetime64[ns]")
    if tod.size and not (tod == tod[0]).all():
        _refuse("file %s: daily values at different times of day" % name)
    want = np.concatenate([np.arange(np.datetime64("%04d-01-01" % y), np.datetime64("%04d-01-01" % (y + 1)),
                                     dtype="datetime64[D]") for y in entry["years"]])
    if days.shape != want.shape or not np.array_equal(days, want):
        miss = np.setdiff1d(want, days)
        extra = np.setdiff1d(days, want)
        _refuse("file %s: its valid dates are not exactly the calendar days of the years %s (%d dates for %d days; "
                "missing %s; outside %s; duplicates %d)" % (name, entry["years"], days.size, want.size, miss[:3],
                                                            extra[:3], int(days.size - np.unique(days).size)))
    mon = days.astype("datetime64[M]").astype(np.int64)                  # months since 1970-01
    steps = step_of(mon // MONTHS_PER_YEAR + 1970, mon % MONTHS_PER_YEAR + 1)
    cut = np.flatnonzero(np.diff(steps)) + 1
    blocks = [(int(steps[a]), int(a), int(b), int(b - a), int(steps[a])) for a, b in zip(np.r_[0, cut],
                                                                                       np.r_[cut, steps.size])]
    return {"shape": (days.size,), "blocks": blocks}


def _seas5_plan(lay: Mapping[str, Any], entry: Mapping[str, Any], opt: Mapping[str, Any]) -> Dict[str, Any]:
    """The members kept (positions of numbers m0..m1, by value) and the starts of one SEAS5 file:
    [(start index, target step t = start + start_months_before_target, step positions of the days of month t, cells,
    info_end = start - 1)]. Starts must be the request's (year x month) at day 1 00:00, steps exactly 12 h + k days
    for k in lead_days, valid_time == time + step on every cell."""
    v, name = lay["v"], entry["file"]
    lo, hi = opt["lead_days"]
    m0, m1 = opt["members"]
    smbt = int(opt["start_months_before_target"])
    num = np.asarray(v.coords["number"].values)
    if np.unique(num).size != num.size:
        _refuse("file %s: the number coordinate repeats a member" % name)
    pos = []
    for mem in range(m0, m1 + 1):
        hit = np.flatnonzero(num == mem)
        if hit.size != 1:
            _refuse("file %s lacks member %d (members %d..%d are read; it holds %s)" % (name, mem, m0, m1,
                                                                                    num.tolist()))
        pos.append(int(hit[0]))
    tv = np.atleast_1d(np.asarray(v.coords["time"].values)).astype("datetime64[ns]")
    want_t = np.array(["%04d-%02d-01T00:00:00" % (y, m) for y in entry["years"] for m in entry["months"]],
                      dtype="datetime64[ns]")
    if tv.shape != want_t.shape or not np.array_equal(tv, want_t):
        _refuse("file %s: its starts %s are not the request's (year x month) at day 1 00:00 %s"
                % (name, [str(x)[:16] for x in tv[:3]], [str(x)[:16] for x in want_t[:3]]))
    st = np.asarray(v.coords["step"].values).astype("timedelta64[ns]")
    want_s = (np.arange(lo, hi + 1, dtype=np.int64) * 86400 + SEAS_VALID_HOUR * 3600).astype(
        "timedelta64[s]").astype("timedelta64[ns]")
    if st.shape != want_s.shape or not np.array_equal(st, want_s):
        _refuse("file %s: its steps are not exactly %d h + k days for k = %d..%d" % (name, SEAS_VALID_HOUR, lo, hi))
    vt = np.asarray(v.coords["valid_time"].values).astype("datetime64[ns]")
    want_vt = (tv[0] + st) if lay["scalar_time"] else (tv[:, None] + st[None, :])
    if vt.shape != want_vt.shape or not np.array_equal(vt, want_vt):
        _refuse("file %s: valid_time differs from time + step" % name)
    starts = []
    for si in range(tv.size):
        sd = tv[si].astype("datetime64[D]").item()
        start_step = int(step_of(sd.year, sd.month))
        t = start_step + smbt
        ty, tm = year_month(t)
        ks = month_days_in_window(sd, int(ty), int(tm), (lo, hi))
        starts.append((si, t, np.asarray(ks, dtype=np.int64) - lo, int(len(pos) * len(ks)), start_step - 1))
    return {"shape": (num.size, tv.size, st.size), "pos": np.asarray(pos, dtype=np.int64), "starts": starts}


def _file_plan(lay: Mapping[str, Any], entry: Mapping[str, Any], opt: Mapping[str, Any]) -> Dict[str, Any]:
    if opt["kind"] == "era5_daily":
        return _era5_plan(lay, entry)
    return _seas5_plan(lay, entry, opt)


def _full_values(lay: Mapping[str, Any], plan: Mapping[str, Any], opt: Mapping[str, Any], name: str) -> np.ndarray:
    """The whole fwinx of one file; SEAS5: members m0..m1 only, with a time axis also for a scalar-time file."""
    arr = np.asarray(lay["v"].values)
    if opt["kind"] != "era5_daily" and lay["scalar_time"]:
        arr = arr[:, None]
    if arr.shape != tuple(plan["shape"]) + (lay["lat"].size, lay["lon"].size):
        _refuse("file %s: fwinx shape %s differs from its axes" % (name, arr.shape))
    if opt["kind"] != "era5_daily":
        arr = arr[plan["pos"]]
    return arr


def _point_values(lay: Mapping[str, Any], plan: Mapping[str, Any], opt: Mapping[str, Any], name: str,
                  ii: np.ndarray, jj: np.ndarray) -> np.ndarray:
    """fwinx at the selected grid points (vectorised isel; points last). SEAS5: members m0..m1, a time axis always."""
    import xarray as xr

    v = lay["v"]
    sel = v.isel(latitude=xr.DataArray(np.asarray(ii, dtype=np.int64), dims="fire_geff_point"),
                 longitude=xr.DataArray(np.asarray(jj, dtype=np.int64), dims="fire_geff_point"))
    sel = sel.transpose(*([d for d in lay["dims"] if d not in ("latitude", "longitude")] + ["fire_geff_point"]))
    arr = np.asarray(sel.values)
    if opt["kind"] != "era5_daily" and lay["scalar_time"]:
        arr = arr[:, None]
    if arr.shape != tuple(plan["shape"]) + (len(ii),):
        _refuse("file %s: fwinx points shape %s differs from its axes" % (name, arr.shape))
    if opt["kind"] != "era5_daily":
        arr = arr[plan["pos"]]
    return arr


def _point_months(vals: np.ndarray, plan: Mapping[str, Any], opt: Mapping[str, Any], name: str
                  ) -> Dict[int, tuple]:
    """{month step: (sum, n_finite, n_cells, file, info_end)} per selected point. Each point's cells are reduced as
    one contiguous float64 row (days; SEAS5 member-major then day), the order a plain numpy mean of that point's
    values uses."""
    out: Dict[int, tuple] = {}
    npts = vals.shape[-1]
    if opt["kind"] == "era5_daily":
        for step, a, b, ncells, ie in plan["blocks"]:
            blk = np.ascontiguousarray(vals[a:b].T, dtype=np.float64)          # (points, days)
            fin = np.isfinite(blk)
            out[step] = (np.where(fin, blk, 0.0).sum(axis=1), fin.sum(axis=1), ncells, name, ie)
    else:
        for si, t, idx, ncells, ie in plan["starts"]:
            blk = vals[:, si][:, idx]                                          # (members, days, points)
            blk = np.ascontiguousarray(np.moveaxis(blk, -1, 0).reshape(npts, -1), dtype=np.float64)
            fin = np.isfinite(blk)
            out[t] = (np.where(fin, blk, 0.0).sum(axis=1), fin.sum(axis=1), ncells, name, ie)
    return out


def _box_files(entries: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    return sorted(entries, key=lambda e: (e["years"][0], e["months"][0], e["file"]))


def read_box_mask(ctx: Any, opt: Mapping[str, Any], box: str, entries: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Pass 1 of a box: the layout of every file, its axes (equal in every file), the valid mask (finite somewhere in
    EVERY file: AND over files of ANY over time) and the mixed mask points (finite in some files only)."""
    pid = str(opt["product"])
    lat0 = lon0 = valid = any_valid = None
    held: Dict[int, tuple] = {}
    for e in _box_files(entries):
        path = ctx.open_product(pid, e["file"])
        with _open_netcdf(path) as ds:
            lay = _check_variable(ds, opt, e["file"])
            if lat0 is None:
                lat0, lon0 = lay["lat"], lay["lon"]
            elif not (np.array_equal(lay["lat"], lat0) and np.array_equal(lay["lon"], lon0)):
                _refuse("box %s: file %s is on another grid than the box's first file" % (box, e["file"]))
            plan = _file_plan(lay, e, opt)
            arr = _full_values(lay, plan, opt, e["file"])
            fin_any = np.isfinite(arr).reshape((-1,) + arr.shape[-2:]).any(axis=0)
            del arr, lay
        metas = ([(b[0], b[3], b[4]) for b in plan["blocks"]] if "blocks" in plan else
                 [(s[1], s[3], s[4]) for s in plan["starts"]])
        for step, ncells, ie in metas:
            if step in held:
                _refuse("box %s: month step %d is held by two files (%s, %s)" % (box, step, held[step][1], e["file"]))
            held[step] = (ncells, e["file"], ie)
        valid = fin_any.copy() if valid is None else (valid & fin_any)
        any_valid = fin_any.copy() if any_valid is None else (any_valid | fin_any)
    return {"lat": lat0, "lon": lon0, "valid": valid, "mixed": int((any_valid & ~valid).sum()), "held": held}


def read_box_points(ctx: Any, opt: Mapping[str, Any], box: str, entries: Sequence[Mapping[str, Any]],
                    ii: np.ndarray, jj: np.ndarray, lat0: np.ndarray, lon0: np.ndarray) -> Dict[int, tuple]:
    """Pass 2 of a box: the per-month (ERA5) / per-start (SEAS5) sums at the selected points (each file re-opened
    through ctx.open_product and re-checked)."""
    pid = str(opt["product"])
    months: Dict[int, tuple] = {}
    for e in _box_files(entries):
        path = ctx.open_product(pid, e["file"])
        with _open_netcdf(path) as ds:
            lay = _check_variable(ds, opt, e["file"])
            if not (np.array_equal(lay["lat"], lat0) and np.array_equal(lay["lon"], lon0)):
                _refuse("box %s: file %s changed its grid between the two passes" % (box, e["file"]))
            plan = _file_plan(lay, e, opt)
            vals = _point_values(lay, plan, opt, e["file"], ii, jj)
            del lay
        for step, rec in _point_months(vals, plan, opt, e["file"]).items():
            if step in months:
                _refuse("box %s: month step %d is held by two files (%s, %s)" % (box, step, months[step][3], rec[3]))
            months[step] = rec
        del vals
    return months


def box_table(ctx: Any, opt: Mapping[str, Any], box: str, entries: Sequence[Mapping[str, Any]],
              centres: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, np.ndarray], Dict[str, Any]]:
    """Per (unit, month) of one box: x__fwi_mean (MINDAYS rule), n_finite, n_cells, product_cell, src, info_end; the
    unit map; the box's mask record. Pass 1 (mask), the unit map, then pass 2 (the selected points only)."""
    data = read_box_mask(ctx, opt, box, entries)
    mp = map_units(data["lat"], data["lon"], data["valid"], centres["lat"].to_numpy(), centres["lon"].to_numpy(),
                   opt["sea_window_steps"])
    cov = ~mp["uncovered"]
    pts = sorted(set(zip(mp["i"][cov].tolist(), mp["j"][cov].tolist())))
    held = data["held"]
    steps = np.array(sorted(held), dtype=np.int64)
    meta = [held[int(t)] for t in steps]                                  # (cells, file, info_end) per month
    nu, ns = len(centres), steps.size
    x = np.full((ns, nu), np.nan)
    nfin = np.zeros((ns, nu), dtype=np.int64)
    ncell = np.array([m[0] for m in meta], dtype=np.int64)
    if pts and ns:
        ii = np.array([p[0] for p in pts], dtype=np.int64)
        jj = np.array([p[1] for p in pts], dtype=np.int64)
        months = read_box_points(ctx, opt, box, entries, ii, jj, data["lat"], data["lon"])
        if sorted(months) != steps.tolist() or any(months[int(t)][2:] != meta[k] for k, t in enumerate(steps)):
            _refuse("box %s: the two passes read different months" % box)
        where = {p: k for k, p in enumerate(pts)}
        col = np.array([where[(int(i), int(j))] for i, j in zip(mp["i"][cov], mp["j"][cov])], dtype=np.int64)
        s_sel = np.stack([months[int(t)][0][col] for t in steps])
        n_sel = np.stack([months[int(t)][1][col] for t in steps]).astype(np.int64)
        ok = (n_sel > 0) & (n_sel / ncell[:, None] >= float(opt["min_day_share"]))
        vals = np.full(s_sel.shape, np.nan)
        vals[ok] = s_sel[ok] / n_sel[ok]
        x[:, cov] = vals
        nfin[:, cov] = n_sel
    lat, lon = data["lat"], data["lon"]
    cells = np.array([product_cell_id(box, lat[i], lon[j]) if i >= 0 else "" for i, j in zip(mp["i"], mp["j"])],
                     dtype=object)
    src = np.array([m[1] for m in meta], dtype=object)
    frame = pd.DataFrame({
        "unit": np.repeat(centres["unit"].astype(str).to_numpy(), ns),
        "time": np.tile(steps, nu),
        STAT_MEAN: x.T.ravel(),
        "n_finite": nfin.T.ravel(),
        "n_cells": np.tile(ncell, nu),
        "product_cell": np.repeat(cells, ns),
        "src": np.where(np.repeat(cov, ns), np.tile(src, nu), ""),
        "info_end": np.tile(np.array([m[2] for m in meta], dtype=np.int64), nu)})
    data["months"] = int(ns)
    data["points"] = len(pts)
    return frame, mp, data


# ---------------------------------------------------------------------------------------------------
# The adapter (SPEC_HUMAN 1.4 / SPEC_HUMAN_PARTB 3.7)
def _tier(rival: Mapping[str, Any], lead: int) -> Optional[str]:
    tiers = rival.get("leads") or {}
    t = tiers.get(int(lead), tiers.get(str(int(lead))))
    if isinstance(t, Mapping):
        return t.get("tier")
    return t


def _json_float(v: Any) -> Optional[float]:
    v = float(v)
    return v if np.isfinite(v) else None


def build(ctx: Any, rival: Mapping[str, Any], lead: int, stage: str) -> pd.DataFrame:
    """The index table of one rival x lead: one row per slim key of stage "all" (SPEC_HUMAN_PARTB 3.7)."""
    t0 = time.time()
    opt = _options(rival)
    rid, lead, kind = rival.get("id"), int(lead), opt["kind"]
    if stage != "all":
        _refuse("rival %s: an FWI index reads no label and is written in one go (stage all), not %r" % (rid, stage))
    if rival.get("reads_target_in_test_window"):
        _refuse("rival %s: FWI reads no label; reads_target_in_test_window must be false" % rid)
    if _tier(rival, lead) in (None, "none"):
        _refuse("rival %s has no row at lead %d" % (rid, lead))
    man, entries, region_box = check_manifest(ctx, rival, opt)      # first: refuses with the waiting_line (T-F01)
    spy = steps_per_year(ctx.run)
    keys = ctx.keys("stage")
    missing = [k for k in KEYS if k not in keys.columns]
    if missing:
        _refuse("index keys lack %s" % missing)
    keys = keys[list(KEYS)].reset_index(drop=True)
    if keys.duplicated(subset=["unit", "time", "issue"]).any():
        _refuse("index keys name a (unit, time, issue) twice")
    if (keys["lead"].to_numpy(np.int64) != lead).any():
        _refuse("index keys hold rows of another lead")
    tt = keys["time"].to_numpy(np.int64)
    iss = keys["issue"].to_numpy(np.int64)
    if kind == "era5_daily":
        if (tt != iss).any():
            _refuse("rival %s reads the target month's observed-weather FWI: every key needs time == issue (the "
                    "nowcast), %d do not" % (rid, int((tt != iss).sum())))
        read = tt + int(opt["target_months_offset"])
        info_end = read
    else:
        start = tt - int(opt["start_months_before_target"])
        if (start != iss + 1).any():
            _refuse("rival %s: the start (month t - %d) must be the first month after the issue on every key; %d keys "
                    "break it (time - issue != %d)" % (rid, int(opt["start_months_before_target"]),
                                                       int((start != iss + 1).sum()),
                                                       int(opt["start_months_before_target"]) + 1))
        read = tt
        info_end = start - 1
    t_ref = int(ctx.run.cuts[lead]["guard_cut"])
    ref_rec = check_reference_timing(ctx, opt, lead, t_ref)

    units = ctx.units()
    units = pd.DataFrame({"unit": units["unit"].astype(str).to_numpy(), "group": units["group"].astype(str).to_numpy()})
    if units["unit"].duplicated().any():
        _refuse("the slim units table names a unit twice")
    unknown = sorted(set(keys["unit"].astype(str)) - set(units["unit"]))
    if unknown:
        _refuse("%d key unit(s) are not bank units of the slim (first %s)" % (len(unknown), unknown[:3]))
    lost = sorted(set(units["group"]) - set(region_box))
    if lost:
        _refuse("product %s: no box names the group(s) %s" % (opt["product"], lost))
    centres = unit_centres(ctx, opt, units["unit"].tolist()).merge(units, on="unit", how="left", validate="one_to_one")
    by_box: Dict[str, List[Dict[str, Any]]] = {}
    for e in entries:
        by_box.setdefault(e["box"], []).append(e)

    parts, audit_units, box_rec = [], {}, {}
    n_sub = n_unc = n_mixed = 0
    for box in sorted(by_box):
        cb = centres[centres["group"].map(region_box) == box].reset_index(drop=True)
        if not len(cb):
            box_rec[box] = {"files": len(by_box[box]), "units": 0, "read": False}
            continue
        N, W, S, E = by_box[box][0]["area"]
        ulon = wrap_lon(cb["lon"].to_numpy())
        out_box = ~((cb["lat"].to_numpy() >= S) & (cb["lat"].to_numpy() <= N) & (ulon >= W) & (ulon <= E))
        if out_box.any():
            _refuse("box %s area %s does not hold %d unit(s): %s" % (box, [N, W, S, E], int(out_box.sum()),
                                                                     cb.loc[out_box, "unit"].tolist()[:5]))
        tb = time.time()
        frame, mp, data = box_table(ctx, opt, box, by_box[box], cb)
        parts.append(frame)
        n_sub += int(mp["substituted"].sum())
        n_unc += int(mp["uncovered"].sum())
        n_mixed += data["mixed"]
        for k, row in cb.iterrows():
            i, j = int(mp["i"][k]), int(mp["j"][k])
            audit_units[str(row["unit"])] = {
                "group": str(row["group"]), "box": box, "i": i, "j": j, "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "point_lat": None if i < 0 else float(data["lat"][i]),
                "point_lon": None if j < 0 else float(wrap_lon(data["lon"][j])),
                "substituted": bool(mp["substituted"][k]), "dist_km": _json_float(mp["dist_km"][k]),
                "uncovered": bool(mp["uncovered"][k]), "nearest_km": _json_float(mp["nearest_km"][k])}
        box_rec[box] = {"files": len(by_box[box]), "units": int(len(cb)), "read": True, "area": [N, W, S, E],
                        "regions": by_box[box][0]["regions"], "n_lat": int(data["lat"].size),
                        "n_lon": int(data["lon"].size), "valid_points": int(data["valid"].sum()),
                        "mixed_mask_points": int(data["mixed"]), "months": int(data["months"]),
                        "points_read": int(data["points"]),
                        "substituted": int(mp["substituted"].sum()), "uncovered": int(mp["uncovered"].sum()),
                        "seconds": round(time.time() - tb, 1)}
        ctx.log("box %s: %d files, grid %d x %d, %d valid points, %d mixed mask points, %d units (%d substituted, %d "
                "uncovered), %d months, %.0f s" % (box, len(by_box[box]), data["lat"].size, data["lon"].size,
                                                  int(data["valid"].sum()), data["mixed"], len(cb),
                                                  int(mp["substituted"].sum()), int(mp["uncovered"].sum()),
                                                  data["months"], time.time() - tb))
        del data
    n_units = int(len(units))
    max_unc = float(opt["max_uncovered_unit_share"]) * n_units
    audit = {"format": ADAPTER_FORMAT, "rival": rid, "lead": lead, "kind": kind, "product": opt["product"],
             "dataset": man.get("dataset"), "version": man.get("version"), "options": {
                 k2: (list(v) if isinstance(v, tuple) else v) for k2, v in opt.items() if k2 != "unit_centres"},
             "reference": ref_rec, "boxes": box_rec, "units": audit_units,
             "counts": {"bank_units": n_units, "substituted_units": n_sub, "uncovered_units": n_unc,
                        "max_uncovered_units": max_unc, "mixed_mask_points": n_mixed}}
    audit_path = Path(str(ctx.work_dir())) / ("map_units_lead_%d.json" % lead)
    if n_unc > max_unc:
        ctx.write_bytes(audit_path, (json.dumps(audit, sort_keys=True, indent=1) + "\n").encode("utf-8"))
        _refuse("%d of %d bank units have no valid grid point within %d steps (more than %.0f, %.1f%%)"
                % (n_unc, n_units, int(opt["sea_window_steps"]), max_unc, 100.0 * opt["max_uncovered_unit_share"]),
                fix="inspect map_units_lead_%d.json in the work folder" % lead)

    table = pd.concat(parts, ignore_index=True)
    if table.duplicated(subset=["unit", "time"]).any():
        _refuse("the per-unit table names a (unit, month) twice")
    table[STAT_PCT] = fwi_percentile(table["unit"].to_numpy(), table["time"].to_numpy(),
                                     table[STAT_MEAN].to_numpy(), t_ref, spy, opt["pct_min_reference"])
    ref_end = reference_info_end(opt, t_ref)
    late = (table["time"].to_numpy(np.int64) > t_ref) & (table["info_end"].to_numpy(np.int64) <= ref_end)
    if late.any():
        _refuse("internal: %d rows after the reference end carry no newer information than their reference"
                % int(late.sum()))

    k = pd.DataFrame({"unit": keys["unit"].astype(str).to_numpy(), "time": read})
    j = k.merge(table[["unit", "time", STAT_MEAN, STAT_PCT, "product_cell", "src"]], on=["unit", "time"],
                how="left", validate="many_to_one", indicator=True)
    if len(j) != len(keys):
        _refuse("internal: the join changed the number of rows")
    no_month = (j["_merge"] == "left_only").to_numpy()
    xm = j[STAT_MEAN].to_numpy(np.float64)
    xp = j[STAT_PCT].to_numpy(np.float64)
    covered = np.isfinite(xm)
    out = keys.copy()
    stat_values = {STAT_MEAN: xm, STAT_PCT: xp}
    for s in opt["stats"]:
        out[s] = stat_values[s].astype(np.float64)
    out["info_end"] = np.asarray(info_end, dtype=np.int64)
    out["target_obs_end"] = np.full(len(out), np.nan, dtype=np.float64)
    out["product_cell"] = np.where(covered, j["product_cell"].fillna("").astype(str).to_numpy(), "").astype(object)
    out["src"] = np.where(covered, j["src"].fillna("").astype(str).to_numpy(), "").astype(object)
    if any(np.isinf(out[s].to_numpy(np.float64)).any() for s in opt["stats"]):
        _refuse("rival %s: the FWI index holds +-inf" % rid)

    # counts, the audit file and the log (SPEC_HUMAN_PARTB 3.3, 3.7)
    tab_mapped = table["src"].to_numpy(object) != ""
    tab_mean = np.isfinite(table[STAT_MEAN].to_numpy(np.float64))
    tab_pct = np.isfinite(table[STAT_PCT].to_numpy(np.float64))
    counts = {"rows": int(len(out)), "covered_" + STAT_MEAN: int(covered.sum()),
              "covered_" + STAT_PCT: int(np.isfinite(xp).sum()), "rows_without_product_month": int(no_month.sum()),
              "bank_units": n_units, "substituted_units": n_sub, "uncovered_units": n_unc,
              "max_uncovered_units": max_unc, "mixed_mask_points": n_mixed,
              "mindays_failures_unit_months": int((tab_mapped & ~tab_mean).sum()),
              "pct_nan_unit_months_with_mean": int((tab_mean & ~tab_pct).sum()),
              "boxes_read": int(sum(1 for b in box_rec.values() if b["read"])), "files": int(len(entries))}
    audit["counts"] = counts
    ctx.write_bytes(audit_path, (json.dumps(audit, sort_keys=True, indent=1) + "\n").encode("utf-8"))
    ctx.log("rival %s lead %d stage all (%s, %s): %d rows; covered %s %d, %s %d; %d rows without a product month; "
            "reference = target months <= %d (the lead's guard cut), own month left out, newest reference info_end %d "
            "< first %s issue %d; no label read"
            % (rid, lead, kind, opt["product"], counts["rows"], STAT_MEAN, counts["covered_" + STAT_MEAN], STAT_PCT,
               counts["covered_" + STAT_PCT], counts["rows_without_product_month"], t_ref,
               ref_rec["reference_info_end_max"], ref_rec["pick_set"], ref_rec["pick_issue_min"]))
    ctx.log("units: %d bank, %d substituted (sea nearest point), %d uncovered (refuse above %.0f); %d mixed mask "
            "points; MINDAYS failures %d unit-months; pct NaN %d unit-months with a finite mean; %d boxes, %d files"
            % (n_units, n_sub, n_unc, max_unc, n_mixed, counts["mindays_failures_unit_months"],
               counts["pct_nan_unit_months_with_mean"], counts["boxes_read"], counts["files"]))
    tab_group = table["unit"].map(units.set_index("unit")["group"]).to_numpy(object)
    kg = out["group"].astype(str).to_numpy()
    au = pd.DataFrame.from_dict(audit_units, orient="index")
    for g in sorted(set(units["group"])):
        gu = au[au["group"] == g] if len(au) else au
        rows = kg == g
        tg = tab_group == g
        ctx.log("group %s: %d units (%d substituted, %d uncovered); %d rows, %d covered; MINDAYS failures %d, pct NaN "
                "%d unit-months" % (g, int((units["group"] == g).sum()), int(gu["substituted"].sum()) if len(gu) else 0,
                                    int(gu["uncovered"].sum()) if len(gu) else 0, int(rows.sum()),
                                    int((covered & rows).sum()), int((tab_mapped & ~tab_mean & tg).sum()),
                                    int((tab_mean & ~tab_pct & tg).sum())))
    ctx.log("rival %s lead %d: built in %.0f s" % (rid, lead, time.time() - t0))
    return out[list(KEYS) + ["info_end", "target_obs_end", "product_cell", "src"] + list(opt["stats"])]


__all__ = ["ADAPTER_FORMAT", "KINDS", "EARTH_RADIUS_KM", "STAT_MEAN", "STAT_PCT", "FireGeffRefusal", "availability",
           "build", "check_manifest", "wrap_lon", "haversine_km", "map_units", "month_days_in_window",
           "fwi_percentile", "product_cell_id", "reference_info_end", "check_reference_timing", "unit_centres",
           "read_box_mask", "read_box_points", "box_table", "steps_per_year", "step_of", "year_month"]
