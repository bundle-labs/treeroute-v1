"""Stage 2 of the coral table builder: one feature table per lead (package-side, not engine code).

SENSITIVITY COPY (2026-10-28, owner ruling AN3; declared coral 2017-2020 sensitivity row, ruling V3,
engine/PREREGISTRATION_DRAFT_coral.md 4.2 step 2). Copied from D:/treeroute/coral_build/coral_tables/build_tables.py
(SHA-256 b1f22ee7...). The ONLY changes are the declared option `--visits-dir DIR` (REQUIRED here, and it must lie under
D:/treeroute/analysis/coral_sens_2017_2020): it sets the visit table (DIR/visits.parquet), the output folder
(DIR/<build>/) and the _moved folder (DIR/_moved/); and --publish is refused (the declaration publishes nothing; the
store under coral_build is a protected root). Feature code, constants, proofs and canary are unchanged.

    py -3.9 -u build_tables.py --build full --visits-dir D:/treeroute/analysis/coral_sens_2017_2020/coral_data

Original usage (headline copy):
    py -3.9 -u build_tables.py --build tiny [--groups "<a>;<b>;..."]     # 4 default groups, every row canaried
    py -3.9 -u build_tables.py --build full                              # owner command (about 25-35 min)
    py -3.9 -u build_tables.py --publish full                            # copy a finished full build to coral_store

Written 2026-10-19 for D:/treeroute/coral_build/SPEC_CORAL_TABLES.md (sections 1.4, 3, 4, 5). Table contract:
D:/treeroute/coral_build/SPEC_TABLE_MODE.md section 1. Inputs (all read only):
  - coral_data/visits.parquet (stage 1, build_visits.py): one row per visit with keys, label, mark, anchor and the
    stage-1 SST-history flags per lead;
  - D:/coral/drivers/sst_compact_all.npz, members uk/start/end/day/sst, memory-mapped by byte offset (npz_map.py).
    Only the needed sites, and per site only the days before its latest cut, are read. sst_full_merged.parquet and
    sst_compact.npz are never opened;
  - D:/coral/drivers/static/IBTrACS.ALL.v04r01.nc (lat, lon, time, usa_wind);
  - D:/coral/drivers/climate/nina34.txt and dmi.txt (PSL monthly format);
  - D:/coral/target/events_dated.parquet (raw lat/lon per Sample_ID, for the replay copy only; never written);
  - project root forecast_features_L0.parquet / _L365.parquet (the replay check only).
Writes only under coral_data/<build>/ (and, for --publish, a new coral_store/<stamp>/ folder).

The timing rule (SPEC_CORAL_TABLES.md 3.1). T target date, A feature anchor (= T, or the month's first day for a
month-precision visit), L lead in days, issue date = T - L, C = A - L. Every data value used is dated strictly before
C. SST and IBTrACS days are UTC, survey dates local, so their windows end before C - g (g = --sst-gap-days, default
1). Index months are counted back from C's month, past the content reach (+2 months nino34a, ruling R-A; +1 month
dmi, the proposed bound {3, month, centred}). feature_end (key column) = the largest window end; it is a bound
computed before any data is read (P24).

Legacy code reused (project root, read only):
  - coral_mhw_features.thresholds / events / doy_of (coral_mhw_features.py:68-107), imported;
  - coral_extra_drivers.psl_index / hav (coral_extra_drivers.py:39-67), imported; the IBTrACS loading lines
    (:71-88) are copied into load_ibtracs();
  - coral_dhw_model.mmm_from (coral_dhw_model.py:69-93) is COPIED verbatim below, because that module imports
    sklearn and coral_smoke_rf at load;
  - the per-event loops of coral_forecast.py:105-175 and coral_extra_drivers.py:70-122 are ported with C (and g) in
    place of the event date. Changes: mean_w / std_w are not computed (not written); days_since_dhw4 capped at 3650
    (legacy 99999); cyc_mindist capped at 9999 km; cyc_days_since_close capped at 3650.

Proof (SPEC_CORAL_TABLES.md 3.4), written to build_manifest.json; any breach stops the build:
  1. asserts per row and lead: last SST day < C - g; every cyclone point < C - g; every index month's content end
     < C; every source day <= feature_end < issue date;
  2. the largest "source day minus issue day" per family and lead;
  3. the look-ahead canary: a stride sample of rows (every 50th by row_id; every row in tiny mode) is rebuilt from
     sources physically truncated at C - g (SST slice, IBTrACS points) and at C (index tables); equal in bytes;
  4. the replay check: visits with one Sample_ID, day precision and day <= 28 are computed again with g = 0 at lead 0
     and lead 365 (a side copy, never written) and compared with the legacy forecast_features files.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sys
import time

ROOT = r"C:\Users\moh the ghost\Desktop\data set for reserch paper"
sys.path.insert(0, ROOT)  # coral_safe, coral_mhw_features, coral_extra_drivers (read only)
from coral_safe import cap_threads, guard, mem_str  # noqa: E402

cap_threads(4)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

import coral_extra_drivers as E  # noqa: E402  (imports io, os, numpy, pandas only)
import coral_mhw_features as M  # noqa: E402  (imports coral_safe, numpy, pandas only)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from columns import WINDOWS, written_columns  # noqa: E402
from npz_map import member_map  # noqa: E402

BUILD_ROOT = r"D:\treeroute\coral_build"
DATA = os.path.join(BUILD_ROOT, "coral_data")
STORE = os.path.join(BUILD_ROOT, "coral_store")
DRAFT = os.path.join(BUILD_ROOT, "engine", "datasets", "coral_draft")
VISITS = os.path.join(DATA, "visits.parquet")
COMPACT = r"D:\coral\drivers\sst_compact_all.npz"
IBT = E.IBT                                      # D:\coral\drivers\static\IBTrACS.ALL.v04r01.nc
NINO = E.NINO                                    # D:\coral\drivers\climate\nina34.txt
DMI = E.DMI                                      # D:\coral\drivers\climate\dmi.txt
EV = r"D:\coral\target\events_dated.parquet"
LEGACY = {0: os.path.join(ROOT, "forecast_features_L0.parquet"), 365: os.path.join(ROOT, "forecast_features_L365.parquet")}

LEADS = (0, 183, 365)                            # ruling I1 (OWNER_RULINGS_2026-09-28.md:104); R10 events
MIN_SST_VALUES = 365 * 10 // 2                   # coral_forecast.py:64, 111
EPOCH_DAY = dt.date(1970, 1, 1)                  # sst_compact day = int days since 1970-01-01
CAP_DHW4 = 3650                                  # SPEC_CORAL_TABLES.md P12 (legacy 99999, coral_forecast.py:147)
CAP_CYC_DAYS = 3650                              # coral_extra_drivers.py:116-118 (3650 when none); P12
CAP_MINDIST = 9999.0                             # coral_extra_drivers.py:102 (9999 when none); P12
CYC_DAYS = (30, 90, 365)                         # coral_extra_drivers.py:96
CYC_RAD = (200, 500)                             # coral_extra_drivers.py:99
CYC_LOOKBACK = 3650                              # coral_extra_drivers.py:111
ENSO_LAGS, ENSO_REACH = (3, 6, 9), 2             # SPEC 3.2: R-A content reach +2 months (OWNER_RULINGS_2026-09-28.md:24)
DMI_LAGS, DMI_REACH = (2, 5, 8), 1               # SPEC 3.2: proposed bound {3, month, centred}, reach +1 (P14)
ENSO_BASE = (1951, 1980)                         # SPEC 3.2 / P13: fixed anomaly base before the first visit (1994)
CANARY_STRIDE_FULL = 50                          # SPEC 3.4 item 3
REPLAY_RTOL = 1e-9                               # SPEC 3.4 item 4
TINY_GROUPS = ("Andaman Sea", "Maldive Islands", "Moreton Bay, eastern Australia", "North and central Red Sea")  # P19
GUARD_GB = 2.5                                   # coral_safe.guard limit (coral_safe.py:57)
STRING_COLS = ("row_id", "unit_id", "group", "mark", "programme")
DATE_COLS = ("target_date", "issue_date", "feature_end")
CODE_FILES = [os.path.join(HERE, f) for f in ("columns.py", "build_visits.py", "build_tables.py", "npz_map.py")] + \
             [os.path.join(ROOT, f) for f in ("coral_safe.py", "coral_mhw_features.py", "coral_extra_drivers.py")]

HEAT = ["%s_%d" % (p, w) for w in WINDOWS for p in ("dhw", "hs_max", "n_above_mmm", "n_above_mmm1", "cool")]
HIST = ["days_since_max_hs", "slope_90", "lifetime_dhw", "n_dhw_ge4_before", "n_dhw_ge8_before", "max_dhw_before",
        "days_since_dhw4"]
MHW = ["mhw_days_365", "mhw_days_90", "mhw_days_30", "mhw_icum_90", "mhw_imax_90", "mhw_nev_365", "mhw_durmax_365",
       "mhw_since_end", "mhw_cat_max_90", "mhw_thr_gap"]
CYC = ["cyc_mindist_%d" % d for d in CYC_DAYS] + ["cyc_%s_%d_%d" % (k, r, d) for d in CYC_DAYS for r in CYC_RAD
                                                   for k in ("maxw", "n")] + ["cyc_days_since_close"]
IDX = ["nino34a_lag%d" % k for k in ENSO_LAGS] + ["dmi_lag%d" % k for k in DMI_LAGS]
CTX = ["ctx_month", "ctx_doy_sin", "ctx_doy_cos", "ctx_abslat", "ctx_mmm"]
FEATURES = CTX + HEAT + HIST + MHW + CYC + IDX

_LOG = []


def log(m):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), m)
    print(line, flush=True)
    _LOG.append(line)


class TimingBreach(RuntimeError):
    """A value dated on or after its window bound, a canary mismatch or a replay mismatch: the build stops."""


# ---------------------------------------------------------------------------------------------------------------
# copied verbatim from coral_dhw_model.py:64-65, 69-93 (that module imports sklearn and coral_smoke_rf at load)
EPOCH = 1988.2857
MIN_YEARS = 10


def mmm_from(h, epoch=EPOCH):
    """Re-centred maximum monthly mean from a pre-t history. Returns (mmm, n_years) or (nan, 0)."""
    if len(h) < 365:
        return np.nan, 0
    yr = h["yr"].values
    mo = h["mo"].values
    s = h["sst"].values
    nyr = len(np.unique(yr))
    if nyr < MIN_YEARS:
        return np.nan, nyr
    best = -1e9
    for m in range(1, 13):
        sel = mo == m
        if sel.sum() < 60:
            continue
        yy, ss = yr[sel], s[sel]
        uy = np.unique(yy)
        if len(uy) < 3:
            continue
        means = np.array([ss[yy == u].mean() for u in uy])
        b, a = np.polyfit(uy.astype(float), means, 1)   # slope, intercept
        v = a + b * epoch
        if v > best:
            best = v
    return (best if best > -1e8 else np.nan), nyr
# ---------------------------------------------------------------------------------------------------------------


def day_of(d):
    return (d - EPOCH_DAY).days


def date_of(n):
    return EPOCH_DAY + dt.timedelta(days=int(n))


def month_index(n):
    d = date_of(n)
    return d.year * 12 + d.month - 1


def month_last_day(idx):
    """Last day (int days since 1970) of month index idx = year * 12 + month - 1."""
    y, m = divmod(idx + 1, 12)
    return day_of(dt.date(y, m + 1, 1)) - 1


def feature_end_of(C, g):
    """The window bound per row and lead (SPEC 3.1, P24), computed from C and g only, before any data is read."""
    cm = month_index(C)
    ends = [C - g - 1, C - g - 1]                                    # SST, cyclones
    ends += [month_last_day(cm - k + ENSO_REACH) for k in ENSO_LAGS]
    ends += [month_last_day(cm - k + DMI_REACH) for k in DMI_LAGS]
    return max(ends)


def sha256_file(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def peak_rss_gb():
    try:
        import psutil
        mi = psutil.Process(os.getpid()).memory_info()
        return getattr(mi, "peak_wset", getattr(mi, "rss", 0)) / 1e9
    except Exception:
        return float("nan")


# ---------------------------------------------------------------------------------------------------------------
# sources
def load_ibtracs():
    """Copied from coral_extra_drivers.py:71-88 (the loading half of cyclone_feats): points sorted by UTC day."""
    from netCDF4 import Dataset
    ds = Dataset(IBT)
    lat = np.ma.filled(ds.variables["lat"][:], np.nan).astype("float32")
    lon = np.ma.filled(ds.variables["lon"][:], np.nan).astype("float32")
    _w = ds.variables["usa_wind"][:]          # int16 with a masked fill -> cast BEFORE filling
    wnd = np.ma.filled(_w.astype("float32"), np.nan)
    tim = np.ma.filled(ds.variables["time"][:], np.nan).astype("float64")
    tu = ds.variables["time"].units
    ds.close()
    base = pd.Timestamp(tu.split("since")[-1].strip().split()[0])
    ok = np.isfinite(lat) & np.isfinite(lon) & np.isfinite(tim)
    la, lo = lat[ok], lon[ok]
    t = base + pd.to_timedelta(tim[ok], unit="D")
    w = np.where(np.isfinite(wnd[ok]), wnd[ok], 0.0)
    lo = ((lo + 180) % 360) - 180
    tn = t.values.astype("datetime64[D]").astype(int)
    order = np.argsort(tn)
    la, lo, w, tn = la[order], lo[order], w[order], tn[order]
    log("IBTrACS track points usable: %s (%s .. %s)" % (format(len(tn), ","), t.min().date(), t.max().date()))
    return dict(tn=tn, la=la, lo=lo, w=w)


def load_indices():
    """{month index: value} per index, with the content end day of each month (month end + reach)."""
    n34 = E.psl_index(NINO)
    base = n34[(n34.yr >= ENSO_BASE[0]) & (n34.yr <= ENSO_BASE[1])].groupby("mo").v.mean()
    n34 = n34.assign(v=n34.v.values - n34.mo.map(base).values)
    dmi = E.psl_index(DMI)
    out = {}
    for name, d, reach in (("nino34a", n34, ENSO_REACH), ("dmi", dmi, DMI_REACH)):
        idx = (d.yr.values * 12 + d.mo.values - 1).astype(int)
        out[name] = {"v": dict(zip(idx.tolist(), d.v.values.astype("float64").tolist())), "reach": reach,
                     "end": {i: month_last_day(i + reach) for i in idx.tolist()}}
    out["meta"] = {"nino34a_base": list(ENSO_BASE), "nino34a_months": int(np.isfinite(n34.v).sum()),
                   "dmi_months": int(np.isfinite(dmi.v).sum()),
                   "dmi_base_period": "not stated in dmi.txt (its footer names no base period); P14 open"}
    return out


def truncate_indices(tabs, C):
    """Index tables physically cut to the months whose content end is before C (the canary's sources)."""
    out = {}
    for name in ("nino34a", "dmi"):
        t = tabs[name]
        keep = [i for i in t["v"] if t["end"][i] < C]
        out[name] = {"v": {i: t["v"][i] for i in keep}, "reach": t["reach"], "end": {i: t["end"][i] for i in keep}}
    return out


def truncate_cyc(cyc, end):
    k = int(np.searchsorted(cyc["tn"], end, side="left"))
    return {key: v[:k] for key, v in cyc.items()}


# ---------------------------------------------------------------------------------------------------------------
# per-row features (ports of coral_forecast.py:105-175 and coral_extra_drivers.py:92-119, cut at C - g / C)
def sst_features(d, s, yr, mo, C, g):
    """SST heat, history, Hobday and MMM from the site slice, every value dated before C - g.

    Returns (features, last SST day used, n values before C - g) or (None, reason, n)."""
    cut = C - g
    j = int(np.searchsorted(d, cut, side="left"))
    if j < MIN_SST_VALUES:
        return None, "stage2_short_history", j
    t = s[:j]
    mmm, nyr = mmm_from(pd.DataFrame({"yr": yr[:j], "mo": mo[:j], "sst": t}))
    if not np.isfinite(mmm):
        return None, "stage2_mmm_rule", j
    hs_all = t - mmm
    f = {"ctx_mmm": mmm}
    for w in WINDOWS:
        hs = hs_all[-w:]
        if len(hs) < max(10, w // 4):
            continue
        f["dhw_%d" % w] = np.where(hs >= 1.0, np.clip(hs, 0, None), 0.0).sum() / 7.0
        f["hs_max_%d" % w] = float(np.max(hs))
        f["n_above_mmm_%d" % w] = int((hs > 0).sum())
        f["n_above_mmm1_%d" % w] = int((hs >= 1).sum())
        f["cool_%d" % w] = float(np.clip(-hs, 0, None).sum() / 7.0)
    y365 = hs_all[-365:] if len(hs_all) >= 365 else hs_all
    f["days_since_max_hs"] = int(len(y365) - 1 - int(np.argmax(y365)))
    f["slope_90"] = (np.polyfit(np.arange(min(90, len(t))), t[-90:], 1)[0] if len(t) >= 90 else 0.0)
    gated = np.where(hs_all >= 1.0, np.clip(hs_all, 0, None), 0.0)
    roll = pd.Series(gated).rolling(84, min_periods=84).sum().values / 7.0
    roll = roll[np.isfinite(roll)]
    f["lifetime_dhw"] = float(gated.sum() / 7.0)
    f["n_dhw_ge4_before"] = int((roll >= 4).sum())
    f["n_dhw_ge8_before"] = int((roll >= 8).sum())
    f["max_dhw_before"] = float(roll.max()) if len(roll) else 0.0
    last = np.where(roll >= 4)[0] if len(roll) else []
    f["days_since_dhw4"] = min(int(len(roll) - 1 - last[-1]), CAP_DHW4) if len(last) else CAP_DHW4
    # Hobday on the same cut (coral_forecast.py:149-175)
    pt, pv = d[:j], t
    thr = M.thresholds(M.doy_of(pt.astype("int64")), pv.astype("float64"))
    w365 = slice(max(0, j - 365), j)
    tw, vw = d[w365], s[w365].astype("float64")
    th = thr[M.doy_of(tw.astype("int64"))]
    ok = np.isfinite(th)
    if ok.sum() >= 60:
        exc = np.zeros(len(tw), bool)
        exc[ok] = vw[ok] > th[ok]
        anom = np.where(ok, vw - th, 0.0)
        e90, a90 = exc[-90:], anom[-90:]
        f["mhw_days_365"] = int(exc.sum())
        f["mhw_days_90"] = int(exc[-90:].sum())
        f["mhw_days_30"] = int(exc[-30:].sum())
        f["mhw_icum_90"] = float(a90[e90].sum() / 7.0) if e90.any() else 0.0
        f["mhw_imax_90"] = float(a90[e90].max()) if e90.any() else 0.0
        s_, ln = M.events(exc)
        f["mhw_nev_365"] = len(s_)
        f["mhw_durmax_365"] = int(ln.max()) if len(ln) else 0
        f["mhw_since_end"] = int(len(exc) - (s_[-1] + ln[-1])) if len(s_) else 365
        gap = th - mmm
        gg = np.where(np.isfinite(gap) & (gap > 0.05), gap, np.nan)
        with np.errstate(invalid="ignore"):
            cat = np.where(e90, a90 / gg[-90:], 0.0)
        f["mhw_cat_max_90"] = float(np.nanmax(cat)) if np.isfinite(cat).any() else 0.0
        f["mhw_thr_gap"] = float(np.nanmedian(gg)) if np.isfinite(gg).any() else np.nan
    return f, int(d[j - 1]), j


def cyc_features(lat, lon, C, g, cyc):
    """Cyclone columns over windows [C - g - days, C - g) (coral_extra_drivers.py:92-119). Returns (f, last day)."""
    tn, la, lo, w = cyc["tn"], cyc["la"], cyc["lo"], cyc["w"]
    # np.float64 scalars, as the legacy loop passed (ev.lat.values[i]): under numpy 2 (NEP 50) a plain Python float
    # with the float32 track arrays makes hav run in float32 (measured 2026-10-19: cyc_mindist off by 5e-5 relative)
    lat, lon = np.float64(lat), np.float64(lon)
    end = C - g
    f, last = {}, None
    for days in CYC_DAYS:
        lo_i, hi_i = np.searchsorted(tn, [end - days, end])
        if hi_i <= lo_i:
            for rad in CYC_RAD:
                f["cyc_maxw_%d_%d" % (rad, days)] = 0.0
                f["cyc_n_%d_%d" % (rad, days)] = 0
            f["cyc_mindist_%d" % days] = CAP_MINDIST
            continue
        last = max(last or -10 ** 9, int(tn[hi_i - 1]))
        dd = E.hav(lat, lon, la[lo_i:hi_i], lo[lo_i:hi_i])
        ww = w[lo_i:hi_i]
        f["cyc_mindist_%d" % days] = min(float(dd.min()), CAP_MINDIST)
        for rad in CYC_RAD:
            m = dd <= rad
            f["cyc_maxw_%d_%d" % (rad, days)] = float(ww[m].max()) if m.any() else 0.0
            f["cyc_n_%d_%d" % (rad, days)] = int(m.sum())
    lo_i = np.searchsorted(tn, end - CYC_LOOKBACK)
    hi_i = np.searchsorted(tn, end)
    if hi_i > lo_i:
        last = max(last or -10 ** 9, int(tn[hi_i - 1]))
        dd = E.hav(lat, lon, la[lo_i:hi_i], lo[lo_i:hi_i])
        near = np.where(dd <= 200)[0]
        f["cyc_days_since_close"] = (min(float(C - tn[lo_i:hi_i][near].max()), float(CAP_CYC_DAYS))
                                     if len(near) else float(CAP_CYC_DAYS))
    else:
        f["cyc_days_since_close"] = float(CAP_CYC_DAYS)
    return f, last


def idx_features(C, tabs):
    """Index columns: month = C's month minus the lag; returns (f, latest content end used)."""
    cm = month_index(C)
    f, last = {}, None
    for name, lags in (("nino34a", ENSO_LAGS), ("dmi", DMI_LAGS)):
        t = tabs[name]
        for k in lags:
            i = cm - k
            f["%s_lag%d" % (name, k)] = t["v"].get(i, np.nan)
            if i in t["v"]:
                last = max(last or -10 ** 9, t["end"][i])
    return f, last


def ctx_season(C, lat):
    c = date_of(C)
    doy = c.timetuple().tm_yday
    return {"ctx_month": c.month, "ctx_doy_sin": np.sin(2 * np.pi * doy / 365.25),
            "ctx_doy_cos": np.cos(2 * np.pi * doy / 365.25), "ctx_abslat": abs(lat)}


def row_features(d, s, yr, mo, C, g, lat, lon, cyc, tabs):
    f, last_sst, n = sst_features(d, s, yr, mo, C, g)
    if f is None:
        return None, last_sst, n
    fc, last_cyc = cyc_features(lat, lon, C, g, cyc)
    fi, last_idx = idx_features(C, tabs)
    f.update(fc)
    f.update(fi)
    f.update(ctx_season(C, lat))
    return f, {"sst": last_sst, "cyclone": last_cyc, "index": last_idx}, n


def as_f64(f):
    return {k: np.float64(f.get(k, np.nan)) for k in FEATURES}


def same_bytes(a, b):
    return all(a[k].tobytes() == b[k].tobytes() for k in FEATURES)


# ---------------------------------------------------------------------------------------------------------------
def select_visits(groups):
    v = pd.read_parquet(VISITS)
    known = set(v.group.unique())
    if groups is not None:
        bad = [g for g in groups if g not in known]
        if bad:
            raise SystemExit("refused: unknown group(s) %s" % bad)
        v = v[v.group.isin(groups)]
    return v.reset_index(drop=True)


def inputs_meta(with_sha=True):
    out = {}
    for p in (VISITS, COMPACT, IBT, NINO, DMI, EV, LEGACY[0], LEGACY[365]):
        st = os.stat(p)
        out[p] = {"size": st.st_size, "mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(st.st_mtime))}
        if with_sha:
            out[p]["sha256"] = sha256_file(p)
    return out


def run_key(meta, code, params):
    return hashlib.sha256(json.dumps([meta, code, params], sort_keys=True).encode()).hexdigest()


def build(A):
    t_start = time.time()
    out_dir = os.path.join(DATA, A.build)
    os.makedirs(out_dir, exist_ok=True)
    groups = None
    if A.build == "tiny":
        groups = [x.strip() for x in A.groups.split(";")] if A.groups else list(TINY_GROUPS)
    elif A.groups:
        raise SystemExit("refused: --groups is for --build tiny only")
    g = int(A.sst_gap_days)
    if g < 0:
        raise SystemExit("refused: --sst-gap-days must be >= 0")
    stride = 1 if A.build == "tiny" else CANARY_STRIDE_FULL
    params = {"build": A.build, "groups": groups, "sst_gap_days": g, "leads": list(LEADS), "canary_stride": stride,
              "min_sst_values": MIN_SST_VALUES, "caps": {"days_since_dhw4": CAP_DHW4, "cyc_days_since_close":
                                                         CAP_CYC_DAYS, "cyc_mindist": CAP_MINDIST,
                                                         "mhw_since_end": 365},
              "enso": {"lags": list(ENSO_LAGS), "reach_months": ENSO_REACH, "base": list(ENSO_BASE)},
              "dmi": {"lags": list(DMI_LAGS), "reach_months": DMI_REACH}}
    log("BUILD %s | groups %s | g %d | %s" % (A.build, groups or "all", g, mem_str()))
    meta = inputs_meta()
    code = {p: sha256_file(p) for p in CODE_FILES}
    key = run_key(meta, code, params)
    man_path = os.path.join(out_dir, "build_manifest.json")
    old = json.load(open(man_path)) if os.path.exists(man_path) else None
    todo = []
    for L in LEADS:
        fp = os.path.join(out_dir, "lead_%d.parquet" % L)
        ok = (old is not None and old.get("run_key") == key and os.path.exists(fp)
              and old.get("files", {}).get("lead_%d.parquet" % L) == sha256_file(fp))
        if not ok:
            todo.append(L)
    if not todo:
        log("every lead file matches the manifest (inputs, code, parameters): nothing to rebuild")
        if A.build == "tiny":
            write_tiny_package(out_dir, sorted(groups))   # refresh the smoke copy from the current coral_draft
        return 0
    stamp = time.strftime("%Y%m%d_%H%M%S")
    moved = os.path.join(DATA, "_moved", stamp, A.build)
    for name in ["lead_%d.parquet" % L for L in LEADS] + ["build_manifest.json", "rows_audit.parquet",
                                                           "dropped_rows.csv", "build.log", "check_report.json"]:
        p = os.path.join(out_dir, name)
        if os.path.exists(p):
            os.makedirs(moved, exist_ok=True)
            shutil.move(p, os.path.join(moved, name))
            log("moved stale %s -> %s" % (name, moved))

    v = select_visits(groups)
    n_all = len(v)
    dropped = []
    for r in v.itertuples(index=False):
        if r.mark == "unused":
            dropped.append((r.row_id, r.group, r.mark, "all", "after_test_window"))
        elif not r.has_sst_series:
            dropped.append((r.row_id, r.group, r.mark, "all", "no_sst_series"))
        elif not r.present_L0:
            dropped.append((r.row_id, r.group, r.mark, "all", "stage1_short_history_L0"))
    v = v[(v.mark != "unused") & v.present_L0].copy()
    v["T"] = [day_of(x) for x in v.target_date]
    v["A"] = [day_of(x) for x in v.anchor_date]
    rid_sorted = sorted(v.row_id)
    rank = {r: i for i, r in enumerate(rid_sorted)}
    v["canary"] = [rank[r] % stride == 0 for r in v.row_id]
    log("visits %d in scope, %d candidate samples (%d groups, %d sites) | %s"
        % (n_all, len(v), v.group.nunique(), v.site_key.nunique(), mem_str()))

    # replay eligibility (SPEC 3.4 item 4): one Sample_ID, day precision, day <= 28, sid in the legacy files
    leg = {L: pd.read_parquet(LEGACY[L]).set_index("sid") for L in (0, 365)}
    ev = pd.read_parquet(EV, columns=["lat", "lon"])
    v["sid1"] = [int(s) if ";" not in s else -1 for s in v.sids]
    v["replay"] = ((v.n_samples == 1) & (v.date_precision == "day")
                   & np.array([x.day <= 28 for x in v.target_date]) & v.sid1.isin(ev.index))

    cyc = load_ibtracs()
    tabs = load_indices()
    uk = np.asarray(member_map(COMPACT, "uk.npy"))
    st = np.asarray(member_map(COMPACT, "start.npy"))
    en = np.asarray(member_map(COMPACT, "end.npy"))
    DAY = member_map(COMPACT, "day.npy")
    SST = member_map(COMPACT, "sst.npy")
    pos = np.searchsorted(uk, v.site_key.values)
    if not (uk[np.minimum(pos, len(uk) - 1)] == v.site_key.values).all():
        raise SystemExit("a candidate visit has no SST series (stage 1 says it has)")
    v["pos"] = pos
    v = v.sort_values(["pos", "row_id"], kind="mergesort").reset_index(drop=True)

    rows = {L: {} for L in LEADS}
    audit = {}
    worst = {L: {"sst": -10 ** 9, "cyclone": -10 ** 9, "index": -10 ** 9, "feature_end": -10 ** 9} for L in LEADS}
    n_assert = n_canary = 0
    canary_bad = []
    replay = {0: {}, 365: {}}
    replay_none = []
    t0 = time.time()
    done = 0
    for k, grp in v.groupby("pos", sort=True):
        a0, b0 = int(st[k]), int(en[k])
        d_full = np.asarray(DAY[a0:b0])
        # only the days before the site's latest C (lead 0; the g = 0 replay copy needs the most): SPEC 4.4
        n_need = int(np.searchsorted(d_full, int(grp.A.max()), side="left"))
        d = d_full[:n_need]
        s = np.asarray(SST[a0:a0 + n_need])
        yr = (d.astype("int64").astype("datetime64[D]").astype("datetime64[Y]").astype("int64") + 1970).astype("int32")
        mo = (d.astype("int64").astype("datetime64[D]").astype("datetime64[M]").astype("int64") % 12 + 1).astype("int8")
        for r in grp.itertuples(index=False):
            au = {"row_id": r.row_id, "sids": r.sids, "n_samples": int(r.n_samples), "label_min": float(r.y_min),
                  "label_max": float(r.y_max), "date_precision": r.date_precision, "anchor_date": r.anchor_date}
            for L in LEADS:
                C = int(r.A) - L
                issue = int(r.T) - L
                fe = feature_end_of(C, g)
                if not fe < issue:
                    raise TimingBreach("%s L%d: feature_end %s not before issue %s" % (r.row_id, L, date_of(fe),
                                                                                       date_of(issue)))
                au["feature_end_L%d" % L] = date_of(fe)
                if L != 0 and r.row_id not in rows[0]:
                    au["sst_n_L%d" % L] = -1
                    dropped.append((r.row_id, r.group, r.mark, L, "not_written_at_lead_0"))
                    continue
                if not getattr(r, "present_L%d" % L):
                    au["sst_n_L%d" % L] = int(getattr(r, "sst_n_before_L%d" % L))
                    dropped.append((r.row_id, r.group, r.mark, L, "stage1_short_history_L%d" % L))
                    continue
                f, used, n = row_features(d, s, yr, mo, C, g, np.float64(r.lat), np.float64(r.lon), cyc, tabs)
                au["sst_n_L%d" % L] = n
                if f is None:
                    dropped.append((r.row_id, r.group, r.mark, L, used))
                    continue
                # proof 1: asserts per row and lead
                if not used["sst"] < C - g:
                    raise TimingBreach("%s L%d: SST day %s not before C - g" % (r.row_id, L, date_of(used["sst"])))
                if used["cyclone"] is not None and not used["cyclone"] < C - g:
                    raise TimingBreach("%s L%d: cyclone day not before C - g" % (r.row_id, L))
                if used["index"] is not None and not used["index"] < C:
                    raise TimingBreach("%s L%d: index content end not before C" % (r.row_id, L))
                for fam, day in used.items():
                    if day is None:
                        continue
                    if not day <= fe:
                        raise TimingBreach("%s L%d: %s day %s after feature_end %s"
                                           % (r.row_id, L, fam, date_of(day), date_of(fe)))
                    worst[L][fam] = max(worst[L][fam], day - issue)
                worst[L]["feature_end"] = max(worst[L]["feature_end"], fe - issue)
                n_assert += 1
                f64 = as_f64(f)
                # proof 3: the canary, from sources physically truncated at C - g (SST, IBTrACS) and C (indices)
                if r.canary:
                    jc = int(np.searchsorted(d, C - g, side="left"))
                    fc, _, _ = row_features(d[:jc].copy(), s[:jc].copy(), yr[:jc].copy(), mo[:jc].copy(), C, g,
                                            np.float64(r.lat), np.float64(r.lon), truncate_cyc(cyc, C - g),
                                            truncate_indices(tabs, C))
                    n_canary += 1
                    if fc is None or not same_bytes(f64, as_f64(fc)):
                        canary_bad.append((r.row_id, L))
                rows[L][r.row_id] = (r, issue, fe, f64)
            # proof 4: the replay copy (g = 0, raw lat/lon of the one Sample_ID); never written
            if r.replay and r.date_precision == "day":
                la_raw, lo_raw = np.float64(ev.lat.loc[r.sid1]), np.float64(ev.lon.loc[r.sid1])
                for L in (0, 365):
                    if r.sid1 not in leg[L].index:
                        continue
                    fr, _, _ = row_features(d, s, yr, mo, int(r.A) - L, 0, la_raw, lo_raw, cyc, tabs)
                    if fr is None:
                        replay_none.append((r.row_id, L))
                    else:
                        fr = as_f64(fr)
                        fr["ctx_abslat"] = np.float64(abs(la_raw))
                        replay[L][r.sid1] = fr
            audit[r.row_id] = au
        done += 1
        if done % 200 == 0:
            guard(GUARD_GB, "build_tables sites")
            log("  %d/%d sites | %.1f min | %s" % (done, v.pos.nunique(), (time.time() - t0) / 60, mem_str()))
    t_feat = time.time() - t0
    log("features done: %d sites in %.1f min | asserts %d | canary %d rows | %s"
        % (done, t_feat / 60, n_assert, n_canary, mem_str()))
    if canary_bad:
        raise TimingBreach("look-ahead canary: %d row-leads differ, first %s" % (len(canary_bad), canary_bad[:5]))

    # proof 4: replay comparison
    rep = replay_compare(replay, leg, replay_none)

    # assemble and write
    guard(GUARD_GB, "before assembly")
    cols = written_columns()
    files = {}
    counts = {}
    for L in LEADS:
        ids = sorted(rows[L])                         # plain code-point order (SPEC 1.3)
        data = {c: [] for c in cols}
        for rid in ids:
            r, issue, fe, f64 = rows[L][rid]
            data["row_id"].append(r.row_id)
            data["unit_id"].append(r.unit_id)
            data["group"].append(r.group)
            data["lat"].append(float(r.lat))
            data["lon"].append(float(r.lon))
            data["target_date"].append(int(r.T))
            data["issue_date"].append(issue)
            data["feature_end"].append(fe)
            data["mark"].append(r.mark)
            data["pct_bleached"].append(float(r.y))
            data["programme"].append(r.programme)
            for c in FEATURES:
                data[c].append(f64[c])
        arrays, fields = [], []
        for c in cols:
            if c in STRING_COLS:
                a = pa.array(data[c], type=pa.string())
            elif c in DATE_COLS:
                a = pa.array(np.asarray(data[c], dtype="int32"), type=pa.int32()).cast(pa.date32())
            else:
                a = pa.array(np.asarray(data[c], dtype="float64"), type=pa.float64())
            arrays.append(a)
            fields.append(pa.field(c, a.type, nullable=True))
        tab = pa.Table.from_arrays(arrays, schema=pa.schema(fields))
        fp = os.path.join(out_dir, "lead_%d.parquet" % L)
        tmp = fp + ".tmp"
        pq.write_table(tab, tmp)
        os.replace(tmp, fp)
        files["lead_%d.parquet" % L] = sha256_file(fp)
        marks = pd.Series(data["mark"])
        counts["lead_%d" % L] = {"rows": len(ids), "train": int((marks == "train").sum()),
                                 "test": int((marks == "test").sum()), "groups": len(set(data["group"])),
                                 "units": len(set(data["unit_id"]))}
        log("wrote lead_%d.parquet: %s" % (L, counts["lead_%d" % L]))

    au = pd.DataFrame(list(audit.values()))
    au.to_parquet(os.path.join(out_dir, "rows_audit.parquet"), index=False)
    dr = pd.DataFrame(dropped, columns=["row_id", "group", "mark", "lead", "reason"])
    dr["lead"] = dr["lead"].astype(str)
    dr.to_csv(os.path.join(out_dir, "dropped_rows.csv"), index=False)
    t_total = time.time() - t_start
    man = {"build": A.build, "stamp": stamp, "run_key": key, "written": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "spec": "D:/treeroute/coral_build/SPEC_CORAL_TABLES.md", "inputs": meta, "code_sha256": code,
           "params": params, "columns": cols, "files": files, "counts": counts,
           "dropped_by_reason": dr.groupby(["lead", "reason"]).size().rename("n").reset_index()
                                  .to_dict(orient="records"),
           "indices": tabs["meta"],
           "proof": {"asserts_passed_row_leads": n_assert,
                     "max_source_day_minus_issue_day": {"lead_%d" % L: worst[L] for L in LEADS},
                     "canary": {"stride": stride, "row_leads": n_canary, "mismatches": 0},
                     "replay": rep},
           "timing": {"features_min": round(t_feat / 60, 3), "total_min": round(t_total / 60, 3),
                      "sites": int(done), "peak_working_set_gb": round(peak_rss_gb(), 3)}}
    for L in LEADS:
        for fam, x in worst[L].items():
            if x != -10 ** 9 and not x < 0:
                raise TimingBreach("lead %d family %s: source day minus issue day = %d (must be < 0)" % (L, fam, x))
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump(man, f, indent=1, default=str)
    log("manifest written | total %.1f min | peak working set %.2f GB" % (t_total / 60, peak_rss_gb()))
    if A.build == "tiny":
        write_tiny_package(out_dir, sorted(set(v.group)))
    with open(os.path.join(out_dir, "build.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(_LOG) + "\n")
    return 0


def replay_compare(replay, leg, replay_none):
    """SPEC 3.4 item 4: the g = 0 copy against the legacy files, relative tolerance 1e-9. A mismatch stops."""
    cols = HEAT + HIST + MHW + CYC + ["ctx_mmm", "ctx_abslat"]
    legacy_name = {"ctx_mmm": "mmm", "ctx_abslat": "abslat", "ctx_month": "month", "ctx_doy_sin": "doy_sin",
                   "ctx_doy_cos": "doy_cos"}
    out = {"rows_without_features_in_copy": len(replay_none), "per_lead": {}}
    bad = []
    if replay_none:
        bad.append(("copy has no features where legacy has a row", replay_none[:5]))
    for L in (0, 365):
        cl = cols + (["ctx_month", "ctx_doy_sin", "ctx_doy_cos"] if L == 0 else [])
        sids = sorted(replay[L])
        worst = {}
        for c in cl:
            lc = legacy_name.get(c, c)
            a = np.array([replay[L][s][c] for s in sids], dtype="float64")
            b = leg[L].loc[sids, lc].to_numpy(dtype="float64") if sids else np.zeros(0)
            if c == "days_since_dhw4":
                b = np.minimum(b, CAP_DHW4)
            if c.startswith("cyc_mindist"):
                b = np.minimum(b, CAP_MINDIST)
            both_nan = np.isnan(a) & np.isnan(b)
            scale = np.maximum(np.abs(a), np.abs(b))
            diff = np.where(both_nan, 0.0, np.abs(a - b))
            okk = both_nan | (diff <= REPLAY_RTOL * scale)
            rel = np.where(scale > 0, diff / np.where(scale > 0, scale, 1), diff)
            worst[c] = float(np.nanmax(np.where(both_nan, 0, rel))) if len(a) else 0.0
            if not okk.all():
                i = int(np.where(~okk)[0][0])
                bad.append((L, c, int((~okk).sum()), sids[i], float(a[i]), float(b[i])))
        out["per_lead"]["lead_%d" % L] = {"rows": len(sids), "columns": len(cl),
                                         "max_rel_diff": max(worst.values()) if worst else 0.0,
                                         "worst_column": max(worst, key=worst.get) if worst else None}
        log("replay lead %d: %d rows x %d columns, max rel diff %.3g (%s)"
            % (L, len(sids), len(cl), out["per_lead"]["lead_%d" % L]["max_rel_diff"],
               out["per_lead"]["lead_%d" % L]["worst_column"]))
    if bad:
        for b in bad[:20]:
            log("REPLAY MISMATCH %s" % (b,))
        raise TimingBreach("replay check: %d column mismatches; first %s" % (len(bad), bad[0]))
    out["mismatches"] = 0
    return out


def write_tiny_package(out_dir, groups):
    """coral_data/tiny/package/: a copy of coral_draft pointing at the tiny files, no exclusion (SPEC 5)."""
    import yaml
    pkg = os.path.join(out_dir, "package")
    os.makedirs(os.path.join(pkg, "ingest"), exist_ok=True)
    for name in ("catalog.yaml", "ban.yaml", "exceptions.yaml", "AUDIT_CHECKLIST.md", os.path.join("ingest", "README.md")):
        shutil.copyfile(os.path.join(DRAFT, name), os.path.join(pkg, name))
    ds = open(os.path.join(DRAFT, "dataset.yaml"), encoding="utf-8").read()
    old = "  target: 'D:/treeroute/coral_build/coral_data/full/lead_{lead}.parquet'"
    if old not in ds:
        raise SystemExit("coral_draft/dataset.yaml has no full-build target line to repoint")
    tiny_target = out_dir.replace("\\", "/") + "/lead_{lead}.parquet"
    ds = ds.replace(old, "  target: '%s'" % tiny_target).replace("name: coral_draft", "name: coral_draft_tiny")
    ds = ("# GENERATED by coral_tables/build_tables.py --build tiny (%s): the tiny SMOKE copy of coral_draft. Smoke only,\n"
          "# smoke-watermarked, no score is reported or used (SPEC_CORAL_TABLES.md 5, P26). Do not edit; rebuild.\n"
          % time.strftime("%Y-%m-%d")) + ds
    with open(os.path.join(pkg, "dataset.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(ds)
    head = ("# split.yaml -- coral_draft_tiny (GENERATED by build_tables.py --build tiny, %s). No exclusion: the %d tiny\n"
            "# groups each pass the engine defaults (SPEC_CORAL_TABLES.md 5). All were seen during design (legacy runs).\n"
            % (time.strftime("%Y-%m-%d"), len(groups)))
    with open(os.path.join(pkg, "split.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(head)
        f.write(yaml.safe_dump({"excluded": {}, "seen_during_design": list(groups)}, sort_keys=False, width=4096))
    log("wrote the tiny smoke package %s (%d groups)" % (pkg, len(groups)))


def publish(name):
    """Copy a finished full build to coral_store/<stamp>/ (SPEC 4.1); never writes there again."""
    if name != "full":
        raise SystemExit("refused: only a full build is published")
    src = os.path.join(DATA, name)
    man = json.load(open(os.path.join(src, "build_manifest.json")))
    if man["proof"]["canary"]["mismatches"] != 0 or man["proof"]["replay"].get("mismatches") != 0:
        raise SystemExit("refused: the build's proof did not pass")
    for fn, sha in man["files"].items():
        if sha256_file(os.path.join(src, fn)) != sha:
            raise SystemExit("refused: %s changed since its manifest" % fn)
    dest = os.path.join(STORE, man["stamp"])
    if os.path.exists(dest):
        raise SystemExit("refused: %s exists; the store is written once" % dest)
    os.makedirs(dest)
    for fn in list(man["files"]) + ["build_manifest.json"]:
        shutil.copyfile(os.path.join(src, fn), os.path.join(dest, fn))
        if sha256_file(os.path.join(dest, fn)) != sha256_file(os.path.join(src, fn)):
            raise SystemExit("copy of %s does not match its source" % fn)
    log("published %s -> %s" % (src, dest))
    log("next: set coral_draft/dataset.yaml stores.target to '%s/lead_{lead}.parquet' and add %s to "
        "D:/treeroute/registry/protected_roots.txt (owner)" % (dest.replace("\\", "/"), STORE.replace("\\", "/")))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", choices=("tiny", "full"))
    ap.add_argument("--groups", default=None, help='tiny only: "<a>;<b>;..." (names may hold commas)')
    ap.add_argument("--sst-gap-days", default=1, type=int, help="g: SST and cyclone windows end before C - g (P17)")
    ap.add_argument("--publish", choices=("full",))
    ap.add_argument("--visits-dir", required=True,
                    help="sensitivity copy: the folder holding visits.parquet (stage 1); output goes to DIR/<build>/")
    A = ap.parse_args()
    if bool(A.build) == bool(A.publish):
        raise SystemExit("give exactly one of --build or --publish")
    if A.publish:
        raise SystemExit("refused: the sensitivity copy publishes nothing (the declaration has no publish step; "
                         "coral_store is a protected root)")
    global DATA, VISITS
    vd = os.path.abspath(A.visits_dir)
    if not vd.lower().startswith(r"d:\treeroute\analysis\coral_sens_2017_2020".lower()):
        raise SystemExit("refused: --visits-dir must be under D:\\treeroute\\analysis\\coral_sens_2017_2020")
    DATA = vd
    VISITS = os.path.join(DATA, "visits.parquet")
    if not os.path.isfile(VISITS):
        raise SystemExit("refused: %s does not exist (run stage 1 first)" % VISITS)
    log("sensitivity copy: visit table %s; output %s" % (VISITS, os.path.join(DATA, A.build)))
    return build(A)


if __name__ == "__main__":
    raise SystemExit(main())
