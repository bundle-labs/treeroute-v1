"""Coral human rival crw_dhw: NOAA Coral Reef Watch 5 km v3.1 heat stress (DHW and 7-day-max alert level).

SPEC_HUMAN.txt section 2 (Builder B). Kind I. One index table per lead (SPEC_HUMAN 1.4): keys, x__dhw, x__baa7d,
info_end, target_obs_end, product_cell, src.

Plain idea. For each survey visit we read NOAA's own heat-stress rule at the last SST day our features read (d*):
  HotSpot(d) = SST(d) - MMM, MMM = NOAA's official climatology value at the site's 5 km pixel;
  DHW(d*)    = (sum of HotSpot(d) over the 84 days d*-83..d* where HotSpot >= 1) / 7;
  BAA level per day 0..4 (the 5 levels in use 2016-2019), x__baa7d = the highest level of the 7 days d*-6..d*.
No label is read (target_obs_end = NaN). info_end = d* (days, proleptic ordinal, the run's time unit).

d* (deviation from the spec text, see BUILD_NOTES_B_coral_defo.txt): d* = C - g - 1, the last SST day of our own
windows (SPEC_CORAL_TABLES.md:163-168; research_coral.md:83), NOT the store's feature_end: feature_end is the
LATEST of all window ends, index months included (build_tables.py:184-190), so it is C - 1 when C is the first of
a month (341 lead-0 day rows) and on every month-precision row. C is recovered per row and PROVED: the store's
feature_end must equal max(C - g - 1, every index month's last content day) recomputed from the store's own
build_manifest params, on every row (else refuse). Same d* as the D6 site-days (fetch_products.py:900-915).

Two checks must pass before the index is returned (SPEC_HUMAN 2 "Checks"; refuse otherwise):
  D6      our recomputed DHW / BAA7d at NOAA's 300 site-days equal NOAA's served values (|DHW diff| <= 0.005 + 1e-6;
          BAA equal after merging NOAA levels >= 4 into 4). The site-day list is the D6 manifest's own `requests`.
  REPLAY  with the package MMM (slim extra c__ctx_mmm) in place of NOAA's, the package rule (last 84 values before
          C - g; build_tables.py:273-292) reproduces the export's x__dhw_84 and x__hs_max_84 to relative 1e-9 on
          every slim train row; and on rows whose 84 calendar days are complete, this adapter's own DHW function
          (calendar window) gives the same numbers.

AdapterCtx calls used (BUILD_NOTES_shared.txt "ADAPTER CONTRACT"):
  ctx.keys("stage"), ctx.extras("train"), ctx.open_product(pid, name), ctx.product_files(pid), ctx.run (plan.json
  max_feature_end_minus_issue_day), ctx.log(message).
Never imports the common harness or the engine. Never reads the label column of the store (reader refuses it).
"""
# Provenance: coral_safe.py:97-107 (site_key, copied), D:/treeroute/coral_build/coral_tables/npz_map.py:17-44
# (stored-member memory map, re-implemented), build_tables.py:184-190 (feature_end), :273-292 (package heat rule),
# D:/treeroute/human_tools/fetch_products.py:865-897 (SST cache pixel rule), :900-915 (d*), research_coral.md:65-92.

import csv
import datetime as dt
import io
import math
import struct
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

ADAPTER_FORMAT = "human-adapter-coral-crw/1"
KEYS = ("unit", "group", "time", "issue", "lead")
X_DHW = "x__dhw"
X_BAA = "x__baa7d"
DHW_DAYS = 84                    # NOAA: 12 weeks
BAA_DAYS = 7                     # 7-day maximum
HS_DHW_MIN = 1.0                 # NOAA: only HotSpots >= 1 deg C accumulate
BAA_TOP = 4                      # Q13: the 5-level scale of 2016-2019 (0..4); NOAA's later levels merge into 4
DHW_ALERT = (4.0, 8.0)           # Alert 1 at DHW >= 4, Alert 2 (top level here) at DHW >= 8
MMM_RING_MAX = 3                 # masked MMM pixel -> nearest valid pixel within 3 cells (pre-registered)
D6_DHW_TOL = 0.005 + 1e-6        # NOAA serves DHW to 2 decimals (SPEC_HUMAN 2 "Checks")
REPLAY_RTOL = 1e-9               # SPEC_HUMAN 2 / SPEC_CORAL_TABLES.md:239-242
EPOCH_ORDINAL = dt.date(1970, 1, 1).toordinal()   # the SST cache's day = days since 1970-01-01 (build_tables.py:88)
SITE_SEP = "|"                   # export unit = "<store unit_id>|<target date ISO>" (checked per row)
STORE_KEY_COLUMNS = ("unit_id", "lat", "lon", "target_date", "issue_date", "feature_end", "mark")
_LOCAL_HEADER = 30               # zip local file header (PKWARE APPNOTE 4.3.7), as npz_map.py:14


class CoralAdapterRefusal(RuntimeError):
    """A coral adapter rule refused (fail loud; nothing catches it)."""


def _refuse(message: str, fix: Optional[str] = None):
    raise CoralAdapterRefusal("refused [coral]: " + message + ("" if not fix else "  FIX: " + fix))


def _opt(rival: Mapping[str, Any], name: str, default: Any = None) -> Any:
    opts = rival.get("options") or {}
    if name in opts:
        return opts[name]
    if default is None:
        _refuse("rival %s has no registry option %r" % (rival.get("id"), name))
    return default


# ---------------------------------------------------------------------------------------------------- sites, pixels
def site_key(lat, lon, dp=4):
    """Copied from coral_safe.py:97-107: one int64 per site (1e-4 degree), the key of the SST cache."""
    s = 10 ** dp
    a = np.rint((np.asarray(lat, dtype="float64") + 90.0) * s).astype("int64")
    b = np.rint((np.asarray(lon, dtype="float64") + 180.0) * s).astype("int64")
    return a * (360 * s + 1) + b


def _grid_axis(lo: float, hi: float, lon360: bool = False) -> List[float]:
    """The ERDDAP 0.05 deg axis values around [lo, hi] as the SST fetch parsed them (fetch_products.py:865-881)."""
    out = []
    k0, k1 = int(math.floor((lo - 0.025) / 0.05)) - 1, int(math.ceil((hi - 0.025) / 0.05)) + 1
    for k in range(k0, k1 + 1):
        c = 0.025 + 0.05 * k
        if lon360:
            x = float("%.3f" % (c % 360.0))
            out.append(((x + 180) % 360) - 180)
        else:
            out.append(float("%.3f" % c))
    return sorted(set(out))


def sst_pixel(lat: float, lon: float) -> Tuple[float, float]:
    """The 5 km pixel centre the SST cache took for a site: first minimum of |axis - site| over the ascending axis
    (coral_fetch_sst_full.py:134-139, re-stated in fetch_products.py:884-897). The MMM is read at the same pixel."""
    la_ax = np.array(_grid_axis(lat - 0.2, lat + 0.2))
    lo_ax = np.array(_grid_axis(lon - 0.2, lon + 0.2, lon360=True))
    return float(la_ax[np.abs(la_ax - lat).argmin()]), float(lo_ax[np.abs(lo_ax - lon).argmin()])


# ---------------------------------------------------------------------------------------------------- SST cache
def member_map(path: Any, member: str) -> np.ndarray:
    """np.memmap (mode 'r') of one STORED .npy member of a .npz file (re-implements npz_map.py:17-44). Never writes;
    a compressed member refuses (it cannot be mapped)."""
    path = str(path)
    with zipfile.ZipFile(path) as z:
        info = z.getinfo(member)
        if info.compress_type != zipfile.ZIP_STORED:
            _refuse("%s:%s is compressed (type %d); it cannot be memory-mapped" % (path, member, info.compress_type))
        offset = info.header_offset
    with open(path, "rb") as f:
        f.seek(offset)
        head = f.read(_LOCAL_HEADER)
        if head[:4] != b"PK\x03\x04":
            _refuse("%s:%s has no local file header at %d" % (path, member, offset))
        name_len, extra_len = struct.unpack("<HH", head[26:30])
        f.seek(offset + _LOCAL_HEADER + name_len + extra_len)
        version = np.lib.format.read_magic(f)
        if version == (1, 0):
            shape, fortran, dtype = np.lib.format.read_array_header_1_0(f)
        elif version == (2, 0):
            shape, fortran, dtype = np.lib.format.read_array_header_2_0(f)
        else:
            _refuse("%s:%s has .npy version %r" % (path, member, version))
        data_offset = f.tell()
    if fortran or dtype.hasobject:
        _refuse("%s:%s is Fortran-ordered or holds objects" % (path, member))
    return np.memmap(path, dtype=dtype, mode="r", offset=data_offset, shape=shape, order="C")


class SstCache(object):
    """Daily SST per site (uk/start/end/day/sst members, memory-mapped; RAM stays low)."""

    def __init__(self, path: Any):
        self.path = str(path)
        self.uk = np.asarray(member_map(path, "uk.npy")).astype("int64")
        self.start = np.asarray(member_map(path, "start.npy")).astype("int64")
        self.end = np.asarray(member_map(path, "end.npy")).astype("int64")
        self.day = member_map(path, "day.npy")
        self.sst = member_map(path, "sst.npy")
        if not (np.diff(self.uk) > 0).all():
            _refuse("%s: uk.npy is not strictly increasing" % self.path)

    def position(self, key: int) -> int:
        i = int(np.searchsorted(self.uk, key))
        if i >= len(self.uk) or int(self.uk[i]) != int(key):
            return -1
        return i

    def series(self, pos: int) -> Tuple[np.ndarray, np.ndarray]:
        a, b = int(self.start[pos]), int(self.end[pos])
        d = np.asarray(self.day[a:b]).astype("int64")
        s = np.asarray(self.sst[a:b])
        if len(d) > 1 and not (np.diff(d) > 0).all():
            _refuse("%s: site %d has unsorted or repeated days" % (self.path, int(self.uk[pos])))
        return d, s


# ---------------------------------------------------------------------------------------------------- NOAA MMM
class OfficialMmm(object):
    """NOAA CRW v3.1 maximum monthly mean (sst_clim_mmm, scale 0.01) and its pixel mask (0 = valid water)."""

    def __init__(self, path: Any, ring_max: int = MMM_RING_MAX):
        import netCDF4
        self.path = str(path)
        self.ring_max = int(ring_max)
        with netCDF4.Dataset(self.path) as ds:
            ds.set_auto_maskandscale(False)
            self.lat = np.asarray(ds.variables["lat"][:], dtype="float64")
            self.lon = np.asarray(ds.variables["lon"][:], dtype="float64")
            v = ds.variables["sst_clim_mmm"]
            raw = np.asarray(v[0] if v.ndim == 3 else v[:])
            fill = int(v.getncattr("_FillValue"))
            scale = float(v.getncattr("scale_factor"))
            offset = float(v.getncattr("add_offset")) if "add_offset" in v.ncattrs() else 0.0
            mask = np.asarray(ds.variables["mask_for_sst_clim_mmm"][0])
        self.valid = (raw != fill) & (mask == 0)
        # int16 hundredths -> float64 exactly as NOAA's 2-decimal value (n / 100, not n * float32(0.01))
        if abs(scale - 0.01) > 1e-9 or offset != 0.0:
            _refuse("%s: sst_clim_mmm scale %r offset %r; the adapter expects 0.01 and 0" % (self.path, scale, offset))
        self.mmm = np.where(self.valid, raw.astype("float64") / 100.0, np.nan)
        # the step over the FULL span: the file stores float32 centres, so lat[1] - lat[0] is -0.04998779 (not -0.05)
        # and its error grows to one whole row by -18 deg (Part 613 addendum, 2026-10-23: D6 refused (-17.975, -38.675))
        self.dlat = float((self.lat[-1] - self.lat[0]) / (len(self.lat) - 1))
        self.dlon = float((self.lon[-1] - self.lon[0]) / (len(self.lon) - 1))

    def index(self, px_lat: float, px_lon: float) -> Tuple[int, int]:
        i = int(round((px_lat - self.lat[0]) / self.dlat))
        j = int(round((((px_lon - self.lon[0]) % 360.0)) / self.dlon)) % len(self.lon)
        if not (0 <= i < len(self.lat)) or abs(self.lat[i] - px_lat) > 1e-4 or \
                abs(((self.lon[j] - px_lon + 180.0) % 360.0) - 180.0) > 1e-4:
            _refuse("%s: no climatology pixel centre at (%.4f, %.4f)" % (self.path, px_lat, px_lon))
        return i, j

    def at(self, px_lat: float, px_lon: float) -> Tuple[float, int, int, int]:
        """(MMM, i, j, ring): the pixel itself (ring 0), else the nearest valid pixel within ring_max cells
        (Chebyshev ring by ring; inside a ring the smallest Euclidean index distance; ties: lowest i, then j);
        NaN and ring -1 when none."""
        i, j = self.index(px_lat, px_lon)
        if self.valid[i, j]:
            return float(self.mmm[i, j]), i, j, 0
        nlat, nlon = self.valid.shape
        for r in range(1, self.ring_max + 1):
            best = None
            for di in range(-r, r + 1):
                for dj in range(-r, r + 1):
                    if max(abs(di), abs(dj)) != r:
                        continue
                    a, b = i + di, (j + dj) % nlon
                    if 0 <= a < nlat and self.valid[a, b]:
                        cand = (di * di + dj * dj, a, b)
                        if best is None or cand < best:
                            best = cand
            if best is not None:
                return float(self.mmm[best[1], best[2]]), best[1], best[2], r
        return float("nan"), i, j, -1


# ---------------------------------------------------------------------------------------------------- the rule
def baa_level(hs: float, dhw: float, alert_needs_hotspot: bool = True) -> int:
    """NOAA BAA, 5 levels (0 No Stress, 1 Watch, 2 Warning, 3 Alert 1, 4 Alert 2 and above).
    alert_needs_hotspot=True is NOAA's methodology page (Warning and Alerts need HotSpot >= 1); False is the literal
    SPEC_HUMAN 2 wording (alerts from DHW alone). The D6 check reports both and decides on the registered one."""
    if not hs > 0.0:
        return 0
    if alert_needs_hotspot and hs < HS_DHW_MIN:
        return 1
    if dhw >= DHW_ALERT[1]:
        return BAA_TOP
    if dhw >= DHW_ALERT[0]:
        return 3
    return 2 if hs >= HS_DHW_MIN else 1


def _dense_window(days: np.ndarray, sst: np.ndarray, first: int, last: int) -> np.ndarray:
    """SST float64 for every calendar day first..last (NaN where the cache has no value)."""
    out = np.full(last - first + 1, np.nan)
    a = int(np.searchsorted(days, first, side="left"))
    b = int(np.searchsorted(days, last, side="right"))
    if b > a:
        d = days[a:b]
        v = np.asarray(sst[a:b], dtype="float64")
        out[d - first] = v
    return out


def _dhw_from(hs: np.ndarray) -> float:
    """DHW from 84 daily HotSpots (the package's expression, build_tables.py:291)."""
    return float(np.where(hs >= HS_DHW_MIN, np.clip(hs, 0, None), 0.0).sum() / 7.0)


def heat_stats(days: np.ndarray, sst: np.ndarray, mmm: float, d_star: int,
               alert_needs_hotspot: bool = True) -> Tuple[float, float, int]:
    """(DHW at d*, BAA 7-day max ending d*, missing days in the 90-day window). Days are days since 1970-01-01.
    DHW needs every day d*-83..d*; BAA7d needs every day d*-89..d* (seven 84-day windows). Missing -> NaN."""
    if not np.isfinite(mmm):
        return float("nan"), float("nan"), -1
    span = DHW_DAYS + BAA_DAYS - 1
    w = _dense_window(days, sst, d_star - span + 1, d_star)
    # NOAA's arithmetic in hundredths: CoralTemp SST and the MMM are 2-decimal values, so the HotSpot is an exact
    # multiple of 0.01. Float SST - MMM can land at 0.99999 on a day NOAA counts as HotSpot 1.00 (D6, 2026-10-23: 16 of
    # 300 site-days were one or two such days short, -1/7 or -2/7 DHW).
    hs = (np.round(w * 100.0) - float(round(mmm * 100.0))) / 100.0
    n_missing = int(np.isnan(w).sum())
    tail = hs[-DHW_DAYS:]
    dhw = _dhw_from(tail) if not np.isnan(tail).any() else float("nan")
    if n_missing:
        return dhw, float("nan"), n_missing
    best = 0
    for k in range(BAA_DAYS):
        e = len(hs) - BAA_DAYS + k                      # index of day d* - 6 + k
        lvl = baa_level(float(hs[e]), _dhw_from(hs[e - DHW_DAYS + 1:e + 1]), alert_needs_hotspot)
        best = max(best, lvl)
    return dhw, float(best), 0


def package_heat(days: np.ndarray, sst: np.ndarray, mmm: float, cut: int) -> Tuple[float, float]:
    """The package rule (build_tables.py:276-292): the last 84 VALUES before the cut day (days < cut), HotSpot vs the
    given MMM; returns (dhw_84, hs_max_84). Used only by the replay check."""
    j = int(np.searchsorted(days, cut, side="left"))
    t = np.asarray(sst[:j])
    hs = (t - np.float64(mmm))[-DHW_DAYS:]
    if len(hs) < DHW_DAYS:
        return float("nan"), float("nan")
    return float(np.where(hs >= 1.0, np.clip(hs, 0, None), 0.0).sum() / 7.0), float(np.max(hs))


# ---------------------------------------------------------------------------------------------------- store and d*
def read_store(path: Any, label_column: str, columns: Sequence[str] = STORE_KEY_COLUMNS) -> pd.DataFrame:
    """The coral store lead file, key columns only. Refuses a request that names the label column (as H:363-369)."""
    cols = list(columns)
    if label_column in cols:
        _refuse("the store reader was asked for the label column %r" % label_column)
    import pyarrow.parquet as pq
    names = pq.ParquetFile(str(path)).schema_arrow.names
    missing = [c for c in cols if c not in names]
    if missing:
        _refuse("%s has no column(s) %s" % (path, missing))
    return pq.read_table(str(path), columns=cols).to_pandas()


def _ordinals(values: Any) -> np.ndarray:
    return np.array([pd.Timestamp(v).date().toordinal() for v in values], dtype="int64")


def _month_index(ordinal: int) -> int:
    d = dt.date.fromordinal(int(ordinal))
    return d.year * 12 + d.month - 1


def _month_last_ordinal(idx: int) -> int:
    y, m = divmod(idx + 1, 12)
    return dt.date(y, m + 1, 1).toordinal() - 1


def store_window_params(build_manifest: Mapping[str, Any]) -> Tuple[int, List[Tuple[int, int]]]:
    """(g, [(lag, reach_months), ...]) from the store's build_manifest params (data-driven; build_tables.py:184-190)."""
    p = build_manifest.get("params") or {}
    if "sst_gap_days" not in p:
        _refuse("the store build_manifest has no params.sst_gap_days")
    idx = []
    for name, v in sorted(p.items()):
        if isinstance(v, Mapping) and "lags" in v and "reach_months" in v:
            idx += [(int(l), int(v["reach_months"])) for l in v["lags"]]
    return int(p["sst_gap_days"]), idx


def feature_end_of(C: int, g: int, index_windows: Sequence[Tuple[int, int]]) -> int:
    """build_tables.py:184-190 on ordinals: the latest of the SST/cyclone end (C - g - 1) and each index month's end."""
    cm = _month_index(C)
    ends = [C - g - 1] + [_month_last_ordinal(cm - lag + reach) for lag, reach in index_windows]
    return max(ends)


def derive_dstar(target: np.ndarray, issue: np.ndarray, fe: np.ndarray, lead: int, g: int,
                 index_windows: Sequence[Tuple[int, int]]) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
    """Per row: C (feature cut) and d* = C - g - 1, PROVED against the store's feature_end.
    The row kind is read from the gap issue - feature_end (as fetch_products.py:900-910, generalised to leads):
    1..g+1 days -> a day row, C = issue (anchor = target day); >= 28 days -> a month row, C = first day of the
    target month - lead. Then feature_end must equal the recomputed window end of that C (else refuse). The gap is
    needed: at C = the 2nd of a month a day row and a month row share one feature_end (the month before's end)."""
    n = len(target)
    C = np.empty(n, dtype="int64")
    kinds = {"day": 0, "month": 0}
    for k in range(n):
        td = dt.date.fromordinal(int(target[k]))
        gap = int(issue[k]) - int(fe[k])
        if 1 <= gap <= g + 1:
            c, kind = int(issue[k]), "day"
        elif gap >= 28:
            c, kind = td.replace(day=1).toordinal() - int(lead), "month"
        else:
            _refuse("row %d (target %s, lead %d): issue - feature_end = %d days fits neither a day row (1..%d) nor a "
                    "month row (28+)" % (k, td, lead, gap, g + 1))
        if feature_end_of(c, g, index_windows) != int(fe[k]):
            _refuse("row %d (target %s, issue %s, lead %d, %s row): the store feature_end %s is not the window end of "
                    "C = %s" % (k, td, dt.date.fromordinal(int(issue[k])), lead, kind,
                                dt.date.fromordinal(int(fe[k])), dt.date.fromordinal(c)))
        C[k] = c
        kinds[kind] += 1
    d_star = C - g - 1
    return C, d_star, kinds


def join_store(keys: pd.DataFrame, store: pd.DataFrame) -> pd.DataFrame:
    """One store row per export key: unit = '<unit_id>|<target date>', time = the target day's ordinal. Refuses an
    unmatched key, a key matched twice, or a time that is not the unit's own date."""
    if store.duplicated(["unit_id", "target_date"]).any():
        _refuse("the store lead file holds a (unit_id, target_date) twice")
    site = keys["unit"].astype(str).str.split(SITE_SEP, n=1, regex=False)
    bad = site.str.len() != 2
    if bad.any():
        _refuse("export unit %r is not '<site>%s<date>'" % (keys["unit"][bad].iloc[0], SITE_SEP))
    k = pd.DataFrame({"_row": np.arange(len(keys)), "unit_id": site.str[0].values,
                      "_date": _ordinals(site.str[1].values)})
    t = keys["time"].astype("int64").values
    if not (k["_date"].values == t).all():
        i = int(np.argmax(k["_date"].values != t))
        _refuse("export key %r has time %d, not the ordinal of its own date" % (keys["unit"].iloc[i], t[i]))
    s = store.copy()
    s["_date"] = _ordinals(s["target_date"].values)
    m = k.merge(s, on=["unit_id", "_date"], how="left", validate="one_to_one", indicator=True)
    if (m["_merge"] != "both").any():
        i = int(np.argmax((m["_merge"] != "both").values))
        _refuse("export key %r has no store row" % keys["unit"].iloc[int(m["_row"].iloc[i])])
    m = m.sort_values("_row").reset_index(drop=True)
    iss = _ordinals(m["issue_date"].values)
    if not (iss == keys["issue"].astype("int64").values).all():
        _refuse("the store issue_date differs from the export issue on some row")
    return m


# ---------------------------------------------------------------------------------------------------- D6 check
def _read_erddap_value(path: Any) -> Tuple[str, float, float, float]:
    """(time, lat, lon, value) of a one-point ERDDAP csv (two header lines)."""
    with open(str(path), newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if len(rows) != 3:
        _refuse("%s is not a one-point ERDDAP csv (%d lines)" % (path, len(rows)))
    t, la, lo, v = rows[2][:4]
    val = float(v) if v.strip() not in ("", "NaN", "nan") else float("nan")
    return t, float(la), float(lo), val


def d6_check(open_file, requests: Mapping[str, Mapping[str, Any]], sst: SstCache, mmm: OfficialMmm,
             alert_needs_hotspot: bool, max_not_comparable: int = 0, min_dhw_share: float = 1.0) -> Dict[str, Any]:
    """Compare our DHW / BAA7d (NOAA MMM) with NOAA's served values at every D6 site-day. Refuses unless BAA7d AND the
    d* HotSpot (our SST - MMM vs NOAA's served HotSpot) equal NOAA on EVERY compared site-day and DHW equals NOAA on at
    least `min_dhw_share` of them (1.0 = every one; ruling AH: 0.97, the DHW differences are listed in the report).
    open_file(name) -> path (sha-checked by the tool). requests = the D6 product manifest's `requests` block."""
    sites = {}
    for rid, r in requests.items():
        n, tag = rid.split("_", 1)
        sites.setdefault(n, {})[tag] = r
    rep = {"site_days": len(sites), "compared": 0, "dhw_equal": 0, "baa_equal": 0, "baa_equal_other_rule": 0,
           "hs_max_abs_diff": 0.0, "hs_compared": 0, "hs_equal": 0, "dhw_max_abs_diff": 0.0, "not_comparable": [],
           "mismatch": [], "rule_alert_needs_hotspot": bool(alert_needs_hotspot), "min_dhw_share": float(min_dhw_share)}
    for n in sorted(sites):
        rs = sites[n]
        if "dhw" not in rs or "baa7d" not in rs:
            _refuse("D6 site-day %s lacks a dhw or baa7d request" % n)
        r = rs["dhw"]
        lat, lon = float(r["lat"]), float(r["lon"])
        pla, plo = sst_pixel(lat, lon)
        if abs(pla - float(r["px_lat"])) > 1e-9 or abs(plo - float(r["px_lon"])) > 1e-9:
            _refuse("D6 %s: our pixel (%.3f, %.3f) differs from the request pixel (%s, %s)"
                    % (n, pla, plo, r["px_lat"], r["px_lon"]))
        day = dt.date.fromisoformat(str(r["day"])[:10]).toordinal() - EPOCH_ORDINAL
        t_d, _, _, noaa_dhw = _read_erddap_value(open_file(rs["dhw"]["file"]))
        _, _, _, noaa_baa = _read_erddap_value(open_file(rs["baa7d"]["file"]))
        if not t_d.startswith(str(r["day"])[:10]):
            _refuse("D6 %s: ERDDAP time %s is not the requested day %s" % (n, t_d, r["day"]))
        pos = sst.position(int(site_key(lat, lon)))
        m, _, _, ring = mmm.at(pla, plo)
        if pos < 0 or not np.isfinite(m):
            rep["not_comparable"].append({"n": n, "why": "no SST series" if pos < 0 else "no MMM"})
            continue
        days, s = sst.series(pos)
        dhw, baa, miss = heat_stats(days, s, m, day, alert_needs_hotspot)
        _, baa_other, _ = heat_stats(days, s, m, day, not alert_needs_hotspot)
        if "hs" in rs:
            _, _, _, noaa_hs = _read_erddap_value(open_file(rs["hs"]["file"]))
            w = _dense_window(days, s, day, day)
            if np.isfinite(noaa_hs) and np.isfinite(w[0]):
                hsd = abs((round(float(w[0]) * 100.0) - round(m * 100.0)) / 100.0 - noaa_hs)
                rep["hs_max_abs_diff"] = max(rep["hs_max_abs_diff"], hsd)
                rep["hs_compared"] += 1
                rep["hs_equal"] += int(hsd <= D6_DHW_TOL)
        if not (np.isfinite(dhw) and np.isfinite(baa) and np.isfinite(noaa_dhw) and np.isfinite(noaa_baa)):
            rep["not_comparable"].append({"n": n, "why": "missing SST days %d or NOAA NaN" % miss})
            continue
        rep["compared"] += 1
        nb = min(int(noaa_baa), BAA_TOP)
        diff = abs(dhw - noaa_dhw)
        rep["dhw_max_abs_diff"] = max(rep["dhw_max_abs_diff"], diff)
        ok_d = diff <= D6_DHW_TOL
        ok_b = int(baa) == nb
        rep["dhw_equal"] += int(ok_d)
        rep["baa_equal"] += int(ok_b)
        rep["baa_equal_other_rule"] += int(int(baa_other) == nb)
        if not (ok_d and ok_b):
            rep["mismatch"].append({"n": n, "row_id": r.get("row_id"), "day": r["day"], "ours_dhw": dhw,
                                    "noaa_dhw": noaa_dhw, "ours_baa7d": baa, "noaa_baa7d": noaa_baa, "mmm_ring": ring})
    baa_bad = rep["compared"] - rep["baa_equal"]
    hs_bad = rep["hs_compared"] - rep["hs_equal"]
    dhw_share = rep["dhw_equal"] / float(rep["compared"]) if rep["compared"] else 0.0
    if baa_bad or hs_bad or dhw_share < float(min_dhw_share) - 1e-12:
        _refuse("D6: %d of %d site-days differ from NOAA (BAA7d differs on %d, the d* HotSpot on %d of %d, DHW equal "
                "share %.4f < %.4f required; first: %s); our recomputation is not NOAA's product"
                % (len(rep["mismatch"]), rep["compared"], baa_bad, hs_bad, rep["hs_compared"], dhw_share,
                   float(min_dhw_share), rep["mismatch"][0] if rep["mismatch"] else "-"),
                fix="read the D6 report (baa_equal_other_rule tells whether the alert rule is the cause)")
    if len(rep["not_comparable"]) > int(max_not_comparable):
        _refuse("D6: %d site-days are not comparable (allowed %d): %s"
                % (len(rep["not_comparable"]), max_not_comparable, rep["not_comparable"][:5]))
    return rep


# ---------------------------------------------------------------------------------------------------- replay check
def replay_check(extras: pd.DataFrame, store_rows: pd.DataFrame, sst: SstCache, g: int,
                 cols: Mapping[str, str]) -> Dict[str, Any]:
    """Package MMM in place of NOAA's: the package rule must reproduce x__dhw_84 / x__hs_max_84 (rel 1e-9) on every
    row given; this adapter's calendar-window DHW must equal it wherever the 84 calendar days are complete."""
    rep = {"rows": int(len(extras)), "equal": 0, "calendar_complete": 0, "calendar_equal": 0, "first_bad": None,
           "max_abs_diff_dhw": 0.0, "max_abs_diff_hs_max": 0.0}
    if not len(extras):
        _refuse("the replay check got no slim rows")
    # The export stores x__/c__ columns as float32 while the package computed them in float64 (2026-10-23: the first
    # real replay differed by 2.4e-7 on hs_max_84, from the float32 MMM it must subtract). With float32 columns the
    # check is to float32 resolution: one float32 step of each magnitude involved (DHW: up to 84/7 MMM steps).
    f32 = any(np.asarray(extras[cols[c]]).dtype == np.float32 for c in ("dhw", "hs_max", "mmm"))

    def _step(v: float) -> float:
        return float(np.spacing(np.float32(abs(v)))) if f32 else 0.0
    order = np.argsort(store_rows["_pos"].values, kind="mergesort")
    cur, days, s = -1, None, None
    for k in order:
        p = int(store_rows["_pos"].iloc[k])
        if p != cur:
            days, s = sst.series(p)
            cur = p
        mm = float(extras[cols["mmm"]].iloc[k])
        cut = int(store_rows["_C"].iloc[k]) - EPOCH_ORDINAL - g
        dhw, hsm = package_heat(days, s, mm, cut)
        want_d, want_h = float(extras[cols["dhw"]].iloc[k]), float(extras[cols["hs_max"]].iloc[k])
        tol_d = REPLAY_RTOL * max(1.0, abs(want_d)) + (DHW_DAYS / 7.0) * _step(mm) + _step(want_d)
        tol_h = REPLAY_RTOL * max(1.0, abs(want_h)) + _step(mm) + _step(want_h)
        rep["max_abs_diff_dhw"] = max(rep["max_abs_diff_dhw"], abs(dhw - want_d))
        rep["max_abs_diff_hs_max"] = max(rep["max_abs_diff_hs_max"], abs(hsm - want_h))
        ok = abs(dhw - want_d) <= tol_d and abs(hsm - want_h) <= tol_h
        if not ok:
            rep["first_bad"] = {"unit": str(extras["unit"].iloc[k]), "package_rule": [dhw, hsm],
                                "export": [want_d, want_h]}
            _refuse("REPLAY: row %s: package rule gives dhw_84 %.12g hs_max_84 %.12g, the export holds %.12g %.12g"
                    % (extras["unit"].iloc[k], dhw, hsm, want_d, want_h))
        rep["equal"] += 1
        d_star = cut - 1
        w = _dense_window(days, s, d_star - DHW_DAYS + 1, d_star)
        if not np.isnan(w).any():
            rep["calendar_complete"] += 1
            own = _dhw_from(w - mm)
            if abs(own - dhw) > REPLAY_RTOL * max(1.0, abs(dhw)) or abs(float(np.max(w - mm)) - hsm) > \
                    REPLAY_RTOL * max(1.0, abs(hsm)):
                _refuse("REPLAY: row %s: the adapter's calendar DHW %.12g differs from the package rule %.12g on a "
                        "complete window" % (extras["unit"].iloc[k], own, dhw))
            rep["calendar_equal"] += 1
    return rep


# ---------------------------------------------------------------------------------------------------- build
_D6_DONE: Dict[str, Dict[str, Any]] = {}


def _manifest_requests(ctx: Any, pid: str) -> Mapping[str, Any]:
    import json
    path = ctx.product_root(pid) / "product_manifest.json"
    with open(str(path), encoding="utf-8") as f:
        man = json.load(f)
    req = man.get("requests")
    if not isinstance(req, Mapping) or not req:
        _refuse("the %s product manifest holds no `requests` block (the D6 site-day list)" % pid)
    return req


def load_store_rows(ctx: Any, rival: Mapping[str, Any], lead: int, keys: pd.DataFrame
                    ) -> Tuple[pd.DataFrame, Dict[str, Any], int, List[Tuple[int, int]]]:
    """The store rows of the export keys (order of keys) with _C (feature cut) and _dstar (ordinals), checked."""
    import json
    pid = _opt(rival, "store_product")
    bm_path = ctx.open_product(pid, "build_manifest.json")
    with open(str(bm_path), encoding="utf-8") as f:
        bm = json.load(f)
    lead_name = "lead_%d.parquet" % lead
    path = ctx.open_product(pid, lead_name)
    want = (bm.get("files") or {}).get(lead_name)
    if want is not None:
        import hashlib
        h = hashlib.sha256()
        with open(str(path), "rb") as f:
            for c in iter(lambda: f.read(1 << 22), b""):
                h.update(c)
        if h.hexdigest() != want:
            _refuse("%s differs from the sha256 its own build_manifest lists" % lead_name)
    store = read_store(path, _opt(rival, "label_column"))
    rows = join_store(keys, store)
    g, idx = store_window_params(bm)
    target = rows["_date"].values.astype("int64")
    issue = _ordinals(rows["issue_date"].values)
    fe = _ordinals(rows["feature_end"].values)
    C, d_star, kinds = derive_dstar(target, issue, fe, lead, g, idx)
    if not (d_star <= fe).all():
        _refuse("d* after feature_end on some row")
    mfe = (ctx.run.plan.get("max_feature_end_minus_issue_day") or {}).get(str(lead))
    if mfe is None:
        _refuse("plan.json has no max_feature_end_minus_issue_day for lead %d" % lead)
    if not ((fe - issue) <= int(mfe)).all() or not ((d_star - issue) <= int(mfe)).all():
        _refuse("a row reads past issue + max_feature_end_minus_issue_day (%d) (T1, SPEC_HUMAN 1.5)" % int(mfe))
    day_rows = (C == issue)
    if not (d_star[day_rows] <= issue[day_rows] - 2).all():
        _refuse("a day row has d* later than issue - 2")
    rows["_C"] = C
    rows["_dstar"] = d_star
    info = {"store_rows": int(len(rows)), "row_kinds": kinds, "sst_gap_days": g, "index_windows": idx,
            "max_dstar_minus_issue": int((d_star - issue).max()), "max_feature_end_minus_issue": int(mfe)}
    return rows, info, g, idx


def build(ctx: Any, rival: Mapping[str, Any], lead: int, stage: str) -> pd.DataFrame:
    """The crw_dhw index table of one lead (SPEC_HUMAN 2; contract BUILD_NOTES_shared.txt)."""
    if stage != "all":
        _refuse("crw_dhw reads no target observation; it is built in one go (stage 'all'), not %r" % stage)
    alert_rule = bool(_opt(rival, "baa_alert_needs_hotspot", True))
    keys = ctx.keys("stage")[list(KEYS)].reset_index(drop=True)
    if (keys["lead"].astype("int64") != int(lead)).any():
        _refuse("ctx.keys gave rows of another lead")
    rows, info, g, idx = load_store_rows(ctx, rival, lead, keys)

    sst_pid, sst_name = _opt(rival, "sst_product"), _opt(rival, "sst_file")
    clim_pid, clim_name = _opt(rival, "climatology_product"), _opt(rival, "climatology_file")
    sst = SstCache(ctx.open_product(sst_pid, sst_name))
    mmm = OfficialMmm(ctx.open_product(clim_pid, clim_name), int(_opt(rival, "mmm_ring_max", MMM_RING_MAX)))

    # D6 first (once per process and product state): our rule must be NOAA's
    d6_pid = _opt(rival, "d6_product")
    d6_key = "%s|%s|%s" % (d6_pid, sst.path, alert_rule)
    if d6_key not in _D6_DONE:
        _D6_DONE[d6_key] = d6_check(lambda name: ctx.open_product(d6_pid, name), _manifest_requests(ctx, d6_pid),
                                    sst, mmm, alert_rule, int(_opt(rival, "d6_max_not_comparable", 0)),
                                    float(_opt(rival, "d6_min_dhw_equal_share", 1.0)))
        for mm in _D6_DONE[d6_key]["mismatch"]:              # ruling AH: every accepted DHW difference is listed
            ctx.log("crw_dhw D6 DHW differs (accepted under ruling AH): site-day %s %s ours %.4f NOAA %.2f, BAA7d %s/%s"
                    % (mm["n"], mm["day"], mm["ours_dhw"], mm["noaa_dhw"], mm["ours_baa7d"], mm["noaa_baa7d"]))
        ctx.log("crw_dhw D6: %d site-days compared, DHW equal %d, BAA7d equal %d (other alert rule %d), max |DHW "
                "diff| %.4f, not comparable %d" % (_D6_DONE[d6_key]["compared"], _D6_DONE[d6_key]["dhw_equal"],
                                                   _D6_DONE[d6_key]["baa_equal"],
                                                   _D6_DONE[d6_key]["baa_equal_other_rule"],
                                                   _D6_DONE[d6_key]["dhw_max_abs_diff"],
                                                   len(_D6_DONE[d6_key]["not_comparable"])))

    # site positions in the SST cache
    sk = site_key(rows["lat"].values, rows["lon"].values)
    pos = np.array([sst.position(int(k)) for k in sk], dtype="int64")
    if (pos < 0).any():
        _refuse("%d rows have no SST series in %s (the store says every row has one)" % (int((pos < 0).sum()),
                                                                                         sst_name))
    rows["_pos"] = pos

    # replay check on the slim train rows (package MMM)
    xcols = {"dhw": _opt(rival, "replay_dhw_column"), "hs_max": _opt(rival, "replay_hs_max_column"),
             "mmm": _opt(rival, "replay_mmm_column")}
    ex = ctx.extras("train").reset_index(drop=True)
    for c in xcols.values():
        if c not in ex.columns:
            _refuse("the slim extras lack %s (registry slim_extra_columns)" % c)
    ex_rows, _, _, _ = load_store_rows(ctx, rival, lead, ex[list(KEYS)])
    ex_rows["_pos"] = np.array([sst.position(int(k)) for k in site_key(ex_rows["lat"].values,
                                                                        ex_rows["lon"].values)], dtype="int64")
    replay = replay_check(ex, ex_rows, sst, g, xcols)
    ctx.log("crw_dhw lead %d REPLAY: %d rows equal; calendar windows complete %d, equal %d"
            % (lead, replay["equal"], replay["calendar_complete"], replay["calendar_equal"]))

    # the index
    n = len(rows)
    x_dhw = np.full(n, np.nan)
    x_baa = np.full(n, np.nan)
    cell = np.empty(n, dtype=object)
    miss = {"no_mmm": 0, "missing_sst_days": 0}
    mmm_cache: Dict[Tuple[float, float], Tuple[float, int, int, int]] = {}
    order = np.argsort(pos, kind="mergesort")
    cur, days, s = -1, None, None
    for k in order:
        p = int(pos[k])
        if p != cur:
            days, s = sst.series(p)
            cur = p
        px = sst_pixel(float(rows["lat"].iloc[k]), float(rows["lon"].iloc[k]))
        if px not in mmm_cache:
            mmm_cache[px] = mmm.at(*px)
        m, i, j, ring = mmm_cache[px]
        cell[k] = "ct5km_%d_%d" % (i, j)
        if not np.isfinite(m):
            miss["no_mmm"] += 1
            continue
        d_star = int(rows["_dstar"].iloc[k]) - EPOCH_ORDINAL
        dhw, baa, nm = heat_stats(days, s, m, d_star, alert_rule)
        if nm:
            miss["missing_sst_days"] += 1
        x_dhw[k], x_baa[k] = dhw, baa
    rings = [v[3] for v in mmm_cache.values()]
    out = keys.copy()
    out[X_DHW] = x_dhw
    out[X_BAA] = x_baa
    out["info_end"] = rows["_dstar"].values.astype("int64")
    out["target_obs_end"] = np.full(n, np.nan)
    out["product_cell"] = cell.astype(str)
    out["src"] = "%s;%s" % (sst_name, clim_name)
    report = {"format": ADAPTER_FORMAT, "rival": rival.get("id"), "lead": int(lead), "stage": stage, **info,
              "d6": _D6_DONE[d6_key], "replay": replay, "not_covered": miss,
              "mmm_pixels": len(mmm_cache), "mmm_ring_counts": {str(r): rings.count(r) for r in sorted(set(rings))},
              "covered_dhw": int(np.isfinite(x_dhw).sum()), "covered_baa7d": int(np.isfinite(x_baa).sum())}
    out.attrs["adapter_report"] = report
    ctx.log("crw_dhw lead %d: %d rows, DHW covered %d, BAA7d covered %d, no MMM %d, missing SST days %d"
            % (lead, n, report["covered_dhw"], report["covered_baa7d"], miss["no_mmm"], miss["missing_sst_days"]))
    return out
