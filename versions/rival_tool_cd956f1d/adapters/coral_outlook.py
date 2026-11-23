"""Coral human rival crw_outlook: NOAA CRW Four-Month Coral Bleaching Outlook v5 (CFSv2), its Week_20 layer.

SPEC_HUMAN.txt section 2 (Builder B). Kind I, forecast-only, tier A ("advantaged horizon") at leads 183 and 365;
no row at lead 0 (the observed product is strictly better there, research_coral.md:143).

Plain idea. For a survey on target day T we take the Outlook issue whose Week_20 window [start_time, stop_time)
holds T (that issue is 134-141 days before T, i.e. 42-49 days AFTER our lead-183 issue date: it breaks rule T1 on
purpose, so the row can only be tier A). At the site's 0.5 degree cell (land -> the nearest ocean ring within 3
rings, the MAXIMUM alert in that ring; coral_crw.py:103-131 logic, re-written) we read:
  x__baa060_w20  the Week_20 alert level (0..4) of the 60% file;
  x__baa4p_w20   the mean Week_20 level over the 010, 030, 060 and 090 files (NaN if any is missing).
info_end = the issue's `time` = icwk + 7 days (NOAA's stamp; proleptic ordinal); target_obs_end = NaN (no label read).
Targets with no Outlook issue (before the archive starts, 2011-11-14, or a missing week) are NaN = not covered.

Every file read is checked: the `time` value equals the file name's icwk + 7 days, the Week variable's start_time /
stop_time equal icwk + 1 + 7 (w - 1) and + 7 w days, and every row's T lies in [start, stop).

AdapterCtx calls used: ctx.keys("stage"), ctx.product_files(pid), ctx.open_product(pid, name), ctx.log, and the
coral store join of coral_crw.load_store_rows (site latitude / longitude of each visit).
"""
# Provenance: research_coral.md:110-142 (R2), coral_crw.py:103-131 (_grid_index, _nearest_ocean), :186-193 (window
# attribute check), SPEC_HUMAN.txt section 2 "Outlook".

import datetime as dt
import re
from typing import Any, Dict, List, Mapping, Optional, Tuple

import numpy as np
import pandas as pd

from adapters import coral_crw as CC

ADAPTER_FORMAT = "human-adapter-coral-outlook/1"
KEYS = CC.KEYS
NAME_RE = re.compile(r"outlook-(\d{3})perc_.*_icwk(\d{8})_")
# NOAA's convention, verified on all 1,984 archive files (2026-10-23): the `time` value is the file name's icwk + 7 days
# (the Week_NN windows start at icwk + 1 + 7 (NN - 1)). The issue is taken as available at that `time`
# (the later of the two dates: conservative), so info_end = icwk + 7.
OUTLOOK_TIME_MINUS_ICWK = 7
FILL = -5                        # land / missing / ice in every BAA layer (file attribute _FillValue)
RING_MAX = 3                     # research_coral.md:125
TIME_EPOCH = dt.datetime(1981, 1, 1)


class OutlookRefusal(RuntimeError):
    """An Outlook adapter rule refused (fail loud)."""


def _refuse(message: str, fix: Optional[str] = None):
    raise OutlookRefusal("refused [coral outlook]: " + message + ("" if not fix else "  FIX: " + fix))


def grid_index(lat: float, lon: float, nlat: int = 360, nlon: int = 720) -> Tuple[int, int]:
    """0.5 deg CRW grid: lat 89.75 -> -89.75, lon 0.25 -> 359.75 (coral_crw.py:103-107)."""
    i = int(np.clip(np.rint((89.75 - lat) / 0.5), 0, nlat - 1))
    j = int(np.clip(np.rint(((lon % 360.0) - 0.25) / 0.5), 0, nlon - 1))
    return i, j


def nearest_ocean(arr: np.ndarray, i: int, j: int, maxring: int = RING_MAX) -> Tuple[int, int]:
    """(value, ring): the cell itself if ocean; else the MAXIMUM alert over the first ring (Chebyshev, lon wraps)
    holding any ocean cell, rings 1..maxring; (-5, -1) when none (coral_crw.py:110-131)."""
    nlat, nlon = arr.shape
    if arr[i, j] >= 0:
        return int(arr[i, j]), 0
    for r in range(1, maxring + 1):
        best = FILL
        for di in range(-r, r + 1):
            for dj in range(-r, r + 1):
                if max(abs(di), abs(dj)) != r:
                    continue
                a, b = i + di, (j + dj) % nlon
                if 0 <= a < nlat and arr[a, b] >= 0:
                    best = max(best, int(arr[a, b]))
        if best >= 0:
            return best, r
    return FILL, -1


def index_files(names: List[str]) -> Dict[Tuple[int, str], str]:
    """{(icwk ordinal, percentile): file name} from the product's file list; a repeated pair refuses."""
    out: Dict[Tuple[int, str], str] = {}
    for n in names:
        m = NAME_RE.search(n)
        if not m:
            continue
        key = (dt.datetime.strptime(m.group(2), "%Y%m%d").date().toordinal(), m.group(1))
        if key in out:
            _refuse("two Outlook files for icwk %s percentile %s: %s and %s"
                    % (dt.date.fromordinal(key[0]), key[1], out[key], n))
        out[key] = n
    if not out:
        _refuse("the Outlook product lists no file named like '...outlook-<ppp>perc_..._icwk<yyyymmdd>_...'")
    return out


def _attr_day(text: str) -> int:
    return dt.datetime.strptime(str(text)[:8], "%Y%m%d").date().toordinal()


def read_week(path: Any, icwk: int, week: int) -> Tuple[np.ndarray, int, int]:
    """(int8 array lat x lon, start ordinal, stop ordinal) of CRW_BAA_Week_<ww>; all attributes asserted."""
    import netCDF4
    var = "CRW_BAA_Week_%02d" % week
    with netCDF4.Dataset(str(path)) as ds:
        ds.set_auto_maskandscale(False)
        tv = int(np.asarray(ds.variables["time"][:]).ravel()[0])
        t_day = (TIME_EPOCH + dt.timedelta(seconds=tv)).date().toordinal()
        if t_day != icwk + OUTLOOK_TIME_MINUS_ICWK:
            _refuse("%s: time %s is not the file name's icwk %s + %d days" % (path, dt.date.fromordinal(t_day),
                                                                            dt.date.fromordinal(icwk),
                                                                            OUTLOOK_TIME_MINUS_ICWK))
        if var not in ds.variables:
            _refuse("%s has no %s" % (path, var))
        v = ds.variables[var]
        start, stop = _attr_day(v.getncattr("start_time")), _attr_day(v.getncattr("stop_time"))
        if start != icwk + 1 + 7 * (week - 1) or stop != icwk + 1 + 7 * week:
            _refuse("%s: %s window %s..%s is not icwk + %d .. + %d days" % (
                path, var, dt.date.fromordinal(start), dt.date.fromordinal(stop), 1 + 7 * (week - 1), 1 + 7 * week))
        fill = int(v.getncattr("_FillValue"))
        if fill != FILL:
            _refuse("%s: %s _FillValue %d, expected %d" % (path, var, fill, FILL))
        arr = np.asarray(v[0] if v.ndim == 3 else v[:]).astype("int16")
        lat = np.asarray(ds.variables["lat"][:], dtype="float64")
        lon = np.asarray(ds.variables["lon"][:], dtype="float64")
    if abs(lat[0] - 89.75) > 1e-6 or abs(lat[1] - lat[0] + 0.5) > 1e-6 or abs(lon[0] - 0.25) > 1e-6 or \
            abs(lon[1] - lon[0] - 0.5) > 1e-6:
        _refuse("%s: the grid is not lat 89.75 step -0.5 / lon 0.25 step 0.5" % path)
    return arr, start, stop


def build(ctx: Any, rival: Mapping[str, Any], lead: int, stage: str) -> pd.DataFrame:
    """The crw_outlook index table of one lead (SPEC_HUMAN 2)."""
    if stage != "all":
        _refuse("crw_outlook reads no target observation; it is built in one go (stage 'all'), not %r" % stage)
    pid = CC._opt(rival, "outlook_product")
    week = int(CC._opt(rival, "week"))
    percs = [str(p) for p in CC._opt(rival, "percentiles")]
    main = str(CC._opt(rival, "main_percentile"))
    stat_main, stat_mean = CC._opt(rival, "stat_main"), CC._opt(rival, "stat_mean")
    ring_max = int(CC._opt(rival, "ring_max", RING_MAX))
    if main not in percs:
        _refuse("main percentile %s is not among %s" % (main, percs))
    keys = ctx.keys("stage")[list(KEYS)].reset_index(drop=True)
    rows, info, _, _ = CC.load_store_rows(ctx, rival, lead, keys)
    files = index_files(list(ctx.product_files(pid)))
    issues = sorted({k[0] for k in files})

    T = keys["time"].astype("int64").values
    lo_off, hi_off = 1 + 7 * (week - 1), 1 + 7 * week          # window = [icwk + lo_off, icwk + hi_off)
    pick = np.full(len(T), -1, dtype="int64")
    iss_arr = np.array(issues, dtype="int64")
    for k, t in enumerate(T):
        a = int(np.searchsorted(iss_arr, t - hi_off + 1, side="left"))
        b = int(np.searchsorted(iss_arr, t - lo_off, side="right"))
        if b - a > 1:
            _refuse("target %s lies in the Week_%02d window of %d issues" % (dt.date.fromordinal(int(t)), week, b - a))
        if b - a == 1:
            pick[k] = iss_arr[a]

    n = len(T)
    vals = {p: np.full(n, np.nan) for p in percs}
    cell = np.array(["none"] * n, dtype=object)
    src = np.array([""] * n, dtype=object)
    counts = {"no_issue": int((pick < 0).sum()), "issue_missing_percentile": 0, "land_no_ocean": 0, "rings": {}}
    for ic in sorted(set(pick[pick >= 0].tolist())):
        sel = np.where(pick == ic)[0]
        names = {p: files.get((ic, p)) for p in percs}
        if names[main] is None:
            counts["issue_missing_percentile"] += len(sel)
        arrays = {}
        for p, name in names.items():
            if name is None:
                continue
            arr, start, stop = read_week(ctx.open_product(pid, name), ic, week)
            if not ((T[sel] >= start) & (T[sel] < stop)).all():
                _refuse("issue %s: a target falls outside its Week_%02d window" % (dt.date.fromordinal(ic), week))
            arrays[p] = arr
        for k in sel:
            i, j = grid_index(float(rows["lat"].iloc[k]), float(rows["lon"].iloc[k]))
            ring = None
            for p, arr in arrays.items():
                v, r = nearest_ocean(arr, i, j, ring_max)
                if ring is not None and r != ring:
                    _refuse("issue %s: the land mask differs between percentile files at cell %d,%d"
                            % (dt.date.fromordinal(ic), i, j))
                ring = r
                if v >= 0:
                    vals[p][k] = float(v)
            if ring == -1:
                counts["land_no_ocean"] += 1
            counts["rings"][str(ring)] = counts["rings"].get(str(ring), 0) + 1
            cell[k] = "o_%d_%d_r%s" % (i, j, ring)
            src[k] = ";".join(names[p] for p in percs if names[p] is not None)
    stack = np.vstack([vals[p] for p in percs])
    out = keys.copy()
    out[stat_main] = vals[main]
    with np.errstate(invalid="ignore"):
        out[stat_mean] = np.where(np.isfinite(stack).all(axis=0), stack.mean(axis=0), np.nan)
    # an uncovered row read nothing; it carries info_end = our issue day, which breaks T1 (boundary issue - 1), so
    # it can never pass as a P row by accident
    out["info_end"] = np.where(pick >= 0, pick + OUTLOOK_TIME_MINUS_ICWK,
                               keys["issue"].astype("int64").values).astype("int64")   # available at the file's `time`
    out["target_obs_end"] = np.full(n, np.nan)
    out["product_cell"] = cell.astype(str)
    out["src"] = src.astype(str)
    covered = np.isfinite(out[stat_main].values)
    if covered.any() and not (out["info_end"].values[covered] > keys["issue"].astype("int64").values[covered]).all():
        ctx.log("crw_outlook lead %d: some covered rows are issued on or before our issue date" % lead)
    report = {"format": ADAPTER_FORMAT, "rival": rival.get("id"), "lead": int(lead), "stage": stage, **info,
              "week": week, "percentiles": percs, "issues_on_disk": len(issues), "counts": counts,
              "covered_main": int(covered.sum()), "covered_mean": int(np.isfinite(out[stat_mean].values).sum()),
              "issue_minus_our_issue_days": ([int(x) for x in np.percentile(
                  (pick + OUTLOOK_TIME_MINUS_ICWK - keys["issue"].astype("int64").values)[pick >= 0], [0, 50, 100])] if (pick >= 0).any()
                  else None)}
    out.attrs["adapter_report"] = report
    ctx.log("crw_outlook lead %d: %d rows, covered %d (%s), mean-of-4 covered %d, no issue %d"
            % (lead, n, report["covered_main"], stat_main, report["covered_mean"], counts["no_issue"]))
    return out
