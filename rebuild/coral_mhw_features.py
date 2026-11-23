"""Hobday marine-heatwave features, recomputed leak-free from the SST already on disk. Zero bytes.

    py -3.9 -u coral_mhw_features.py

WHY THIS IS NOT JUST ANOTHER DRIVER. Five consecutive driver ADDITIONS have been null or negative
(cyclones, lags, light, ocean heat content, sea state, sea surface height), and Part 423 concluded
the model is not driver-limited. This is a different class of experiment: it adds no new physical
variable at all. It RE-PARAMETERISES the one data source that demonstrably carries the signal --
`dhw_56` alone holds 32-40% of all feature importance -- and asks whether DHW is the right functional
of the SST record rather than whether we need more records.

  DHW asks   "how much cumulative heat above the local summer maximum?"           -- an ABSOLUTE excess
  Hobday asks "is today unusually hot FOR THIS DAY OF YEAR at this reef?"          -- a RELATIVE rank

Those come apart wherever the seasonal cycle is large: a reef 1.5 C above its March normal is in a
severe percentile anomaly while contributing exactly zero degree-heating-weeks, because March is
nowhere near its summer maximum. DHW is blind to that by construction, and it is the mechanism
Hobday et al. (2016) defines a marine heatwave around.

WHY WE RECOMPUTE RATHER THAN DOWNLOAD. NOAA CRW ships a marine-heatwave product (8.84 GB), but its
percentile baseline is a FIXED 1985-01-01..2012-12-31 window, which contains the survey year for the
1986-2012 majority of this corpus -- a hard leak. The same quantity is derivable from the daily SST
we already hold, with an expanding window, for zero bytes and no leak. Part 422 flagged this as the
one free win in the whole driver catalogue.

THE LEAK RULE, IMPLEMENTED. For a survey at time t the day-of-year 90th percentile is computed from
that site's observations STRICTLY BEFORE t, over an 11-day window centred on each day of year (the
Hobday window), requiring at least two prior years. Nothing at or after t contributes -- asserted at
the end. This is the same construction the MMM uses, and that one was validated against NOAA's own
`sst_clim_mmm` at a median absolute difference of 0.013 C.

WHAT IS ALREADY IN THE TABLE AND WHY IT IS NOT THIS. `mhw_p90_W8/W12/W16` exist from earlier work,
but they are DHW-shaped ACCUMULATORS against a flat percentile and correlate 0.73-0.85 with dhw_56 --
they are DHW wearing a different threshold. The genuinely new content here is (a) the day-of-year
resolution of the threshold and (b) the EVENT structure: how many discrete heatwaves, how long, how
long since the last one ended. A cumulative-intensity number cannot express any of that.

MEMORY. The SST table is 57,070,814 rows and killed this machine three times before coral_safe
existed. Read from the pre-sorted D:\\coral\\drivers\\sst_compact.npz, which carries per-site index
boundaries so no per-site DataFrame is ever built; work in flat numpy slices only.
"""
import sys

sys.path.insert(0, r"C:\Users\moh the ghost\Desktop\data set for reserch paper")
from coral_safe import cap_threads, guard, mem_str, site_key

cap_threads(4)

import warnings

warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

SST = r"D:\coral\drivers\sst_compact.npz"
FEAT = "newdriver_features.parquet"
OUT = "mhw_features.parquet"
HALF = 5            # Hobday window is 11 days centred on the day of year
PCT = 90.0
MINDUR = 5          # a marine heatwave is >= 5 consecutive days over the threshold
MINYEARS = 2


def log(m):
    print(m, flush=True)


def doy_of(days):
    """Day of year 1..366 from an int64 days-since-epoch array."""
    d = days.astype("datetime64[D]")
    return ((d - d.astype("datetime64[Y]")).astype(int) + 1)


def thresholds(pd_doy, pv):
    """p90 per day-of-year over an 11-day centred window, from PRIOR observations only.

    Returns a length-367 array (index 1..366); NaN where the window holds too little.
    """
    thr = np.full(367, np.nan)
    order = np.argsort(pd_doy, kind="mergesort")
    sd, sv = pd_doy[order], pv[order]
    lo = np.searchsorted(sd, np.arange(1, 367) - HALF, side="left")
    hi = np.searchsorted(sd, np.arange(1, 367) + HALF, side="right")
    for i in range(366):
        a, b = lo[i], hi[i]
        # wrap the window across the year boundary so 1 Jan sees late December
        if i + 1 <= HALF or i + 1 > 366 - HALF:
            w = np.r_[sv[a:b],
                      sv[np.searchsorted(sd, 366 + (i + 1) - HALF, "left"):],
                      sv[:np.searchsorted(sd, (i + 1) + HALF - 366, "right")]]
        else:
            w = sv[a:b]
        if w.size >= 20:
            thr[i + 1] = np.percentile(w, PCT)
    return thr


def events(mask):
    """Start indices and lengths of runs of True at least MINDUR long."""
    if not mask.any():
        return np.empty(0, int), np.empty(0, int)
    d = np.diff(np.r_[0, mask.view(np.int8), 0])
    s = np.where(d == 1)[0]
    e = np.where(d == -1)[0]
    ln = e - s
    k = ln >= MINDUR
    return s[k], ln[k]


def main():
    log("=" * 92)
    X = pd.read_parquet(FEAT).reset_index(drop=True)
    n = len(X)
    ek = site_key(X.lat.values, X.lon.values)
    ed = X.date.values.astype("datetime64[D]").astype(np.int64)
    log("events %s | %s" % (format(n, ","), mem_str()))

    z = np.load(SST)
    uk, st, en = z["uk"], z["start"], z["end"]
    T, V = z["day"], z["sst"]
    log("sst %s rows | %d sites | %s" % (format(len(V), ","), len(uk), mem_str()))
    idx = np.searchsorted(uk, ek)
    idx[idx >= len(uk)] = 0
    hit = uk[idx] == ek
    log("events with an SST series: %d of %d (%.1f%%)" % (hit.sum(), n, 100 * hit.mean()))

    COLS = ["mhw_days_30", "mhw_days_90", "mhw_days_365", "mhw_icum_90", "mhw_imax_90",
            "mhw_nev_365", "mhw_durmax_365", "mhw_since_end", "mhw_cat_max_90", "mhw_thr_gap"]
    F = {c: np.full(n, np.nan) for c in COLS}
    mmm = X.mmm.values.astype("float64")
    late = 0
    used = 0

    for i in range(n):
        if not hit[i]:
            continue
        a, b = st[idx[i]], en[idx[i]]
        t, v = T[a:b], V[a:b]
        j = int(np.searchsorted(t, ed[i], side="left"))     # strictly before the survey day
        if j < 365 * MINYEARS:
            continue
        if j and t[j - 1] >= ed[i]:
            late += 1
        pt, pv = t[:j], v[:j]
        yrs = len(np.unique(pt.astype("datetime64[D]").astype("datetime64[Y]")))
        if yrs < MINYEARS:
            continue
        thr = thresholds(doy_of(pt), pv.astype("float64"))
        used += 1

        w365 = slice(max(0, j - 365), j)
        tw, vw = t[w365], v[w365].astype("float64")
        th = thr[doy_of(tw)]
        ok = np.isfinite(th)
        if ok.sum() < 60:
            continue
        exc = np.zeros(len(tw), bool)
        exc[ok] = vw[ok] > th[ok]
        anom = np.where(ok, vw - th, 0.0)

        F["mhw_days_365"][i] = exc.sum()
        F["mhw_days_90"][i] = exc[-90:].sum()
        F["mhw_days_30"][i] = exc[-30:].sum()
        e90 = exc[-90:]
        a90 = anom[-90:]
        F["mhw_icum_90"][i] = float(a90[e90].sum() / 7.0) if e90.any() else 0.0
        F["mhw_imax_90"][i] = float(a90[e90].max()) if e90.any() else 0.0
        s, ln = events(exc)
        F["mhw_nev_365"][i] = len(s)
        F["mhw_durmax_365"][i] = int(ln.max()) if len(ln) else 0
        F["mhw_since_end"][i] = int(len(exc) - (s[-1] + ln[-1])) if len(s) else 365
        # Hobday category: how many multiples of the (p90 - MMM) gap the anomaly reaches.
        gap = thr[doy_of(tw)] - mmm[i]
        g = np.where(np.isfinite(gap) & (gap > 0.05), gap, np.nan)
        with np.errstate(invalid="ignore"):
            cat = np.where(e90, a90 / g[-90:], 0.0)
        F["mhw_cat_max_90"][i] = float(np.nanmax(cat)) if np.isfinite(cat).any() else 0.0
        F["mhw_thr_gap"][i] = float(np.nanmedian(g))
        if (i + 1) % 1000 == 0:
            guard(2.5, "mhw")
            log("   %d/%d (%d built) | %s" % (i + 1, n, used, mem_str()))

    assert late == 0, "an MHW window used a day at or after the survey date"
    log("LEAK ASSERTION PASSED: no SST day at or after its own survey contributed.")
    N = pd.DataFrame(F, index=X.index)
    pd.concat([X, N], axis=1).to_parquet(OUT, index=False)
    log("=" * 92)
    log("wrote %s | %d columns | built for %d events" % (OUT, len(N.columns), used))
    base = X[["dhw_56", "dhw_90"]] if "dhw_56" in X else None
    for c in COLS:
        v = N[c]
        r = ""
        if base is not None and v.notna().sum() > 100:
            r = "  corr(dhw_56) %+.3f" % np.corrcoef(
                v.fillna(v.median()), X["dhw_56"].fillna(0))[0, 1]
        log("   %-16s coverage %.3f  median %9.3f  sd %8.3f%s"
            % (c, v.notna().mean(), np.nanmedian(v) if v.notna().any() else np.nan,
               np.nanstd(v) if v.notna().any() else np.nan, r))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
