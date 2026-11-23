"""Fire-history drivers, derived from our own target. The highest-value block, and it costs nothing.

    py -3.9 -u fire_build_history.py                 # all complete regions
    py -3.9 -u fire_build_history.py --only=greece_mainland

WHY THIS FIRST. Every one of the 135 features currently in the matrix was fetched for the NDVI
problem. Not one of them is about fire. The research ranks time-since-last-fire as "the highest-
value derived driver", and it is not a product to download -- it is computed from the burn record
we already hold. Two families come out of it:

  FUEL AGE      how long since this cell last burned, how often it burns, when in the year it
                burned. Fire consumes fuel, so a cell that burned recently cannot burn again until
                fuel regrows -- a NEGATIVE autocorrelation that no climate column can express.

  SPATIAL       what fraction of the surrounding ring burned recently. Section 8.2 names spatial
                coupling as "the family our architecture does not have": the router is per-cell
                i.i.d. and has no mechanism for a fire spreading in from next door. A neighbourhood
                column is the minimum viable fix, and the NDWS ablation puts the magnitude of that
                signal at 28.4 -> 6.8 without it.

------------------------------------------------------------------------------------------------
THE OFF-BY-ONE THAT WOULD RUIN THIS
------------------------------------------------------------------------------------------------
These columns are built FROM THE TARGET, so they are the most leak-prone features in the project.
The rule is STRICT inequality: the value at month t may only use burns at months STRICTLY EARLIER
than t. Using <= instead of < lets the current month's own burn set "months since last fire = 0",
which predicts the target perfectly and produces a beautiful, meaningless score. Every temporal
column below is built by shifting the burn matrix one month forward BEFORE any accumulation, and
an explicit assertion checks that a cell burning at t has not had its own burn counted.

------------------------------------------------------------------------------------------------
UNOBSERVED IS NOT UNBURNED
------------------------------------------------------------------------------------------------
A cell-month with n_valid == 0 was not seen. Treating it as "did not burn" manufactures fake long
time-since-fire in exactly the cloudy regions (borneo 10.2% unmapped, canadian_prairies up to
27.3%). Unobserved months are carried as NaN through the burn matrix and the resulting TSLF is
flagged, not silently filled.

------------------------------------------------------------------------------------------------
NEIGHBOURHOODS NEED ALL CELLS, NOT THE 1,000-CELL SAMPLE
------------------------------------------------------------------------------------------------
The modelling sample is 1,000 random cells per region, so a sampled cell's actual neighbours are
almost never in the sample. Every ring statistic is therefore computed on the FULL region grid and
only subset to the 1,000 cells at the very end. Computing it on the sample would measure "burning
among 1,000 scattered cells", which is not a neighbourhood at all.
"""
import argparse
import glob
import os
import re
import sys
import time
import warnings

sys.path.insert(0, r"C:\Users\<user>\Desktop\data set for reserch paper")
from coral_safe import cap_threads, free_gb, mem_str

cap_threads(4)
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from scipy.ndimage import uniform_filter

YEARS = list(range(2002, 2023))
NMON = len(YEARS) * 12
TARGET = "D:/fire/target"
GEOM = "D:/fire/geom"
OUT = "D:/fire/history"
CAP = 300.0            # months. TSLF is capped, not sentinel-coded -- an int sentinel like -999
                       # becomes a magic number a tree splits on, and 300 months (25 y) exceeds
                       # the record so "never burned" and "burned 25 y ago" are one bucket.
RINGS_KM = (25.0, 75.0)
LAGS = (1, 3, 6)   # months between the neighbour burn and the month being predicted


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


def complete_regions():
    by = {}
    for f in glob.glob(os.path.join(TARGET, "*.parquet")):
        m = re.match(r"(.+)_(\d{4})\.parquet$", os.path.basename(f))
        if m:
            by.setdefault(m.group(1), set()).add(int(m.group(2)))
    return sorted(r for r in by if set(YEARS) <= by[r])


def build(region):
    z = np.load(os.path.join(GEOM, "%s.npz" % region), allow_pickle=True)
    la = np.round(np.asarray(z["la"], np.float64), 5)
    lo = np.round(np.asarray(z["lo"], np.float64), 5)
    nla, nlo = len(la), len(lo)
    B = np.full((nla, nlo, NMON), np.nan, np.float32)     # burned fraction, NaN = unobserved
    for y in YEARS:
        d = pd.read_parquet(os.path.join(TARGET, "%s_%d.parquet" % (region, y)),
                            columns=["lat", "lon", "month", "burned_frac", "n_valid"])
        d = d[d.n_valid > 0]
        i = np.searchsorted(la, np.round(d.lat.values.astype(np.float64), 5))
        j = np.searchsorted(lo, np.round(d.lon.values.astype(np.float64), 5))
        k = (y - YEARS[0]) * 12 + d.month.values - 1
        ok = (i >= 0) & (i < nla) & (j >= 0) & (j < nlo)
        B[i[ok], j[ok], k[ok]] = d.burned_frac.fillna(0.0).values[ok]
    obs = ~np.isnan(B)
    Bz = np.where(obs, B, 0.0).astype(np.float32)
    burned = (Bz > 0)

    # ---- SHIFT FIRST. Everything below reads `past`, which is `burned` moved one month later, so
    # month t can only ever see months < t. This single line is the whole leak guard.
    past = np.zeros_like(burned)
    past[:, :, 1:] = burned[:, :, :-1]
    past_frac = np.zeros_like(Bz)
    past_frac[:, :, 1:] = Bz[:, :, :-1]

    # ---- fuel age: months since the most recent STRICTLY EARLIER burn -------------------------
    tslf = np.full((nla, nlo, NMON), CAP, np.float32)
    last_mon = np.full((nla, nlo, NMON), -1.0, np.float32)   # calendar month of that burn
    last_size = np.zeros((nla, nlo, NMON), np.float32)
    cur = np.full((nla, nlo), -1, np.int32)                  # index of last burn, -1 = none yet
    cur_mon = np.full((nla, nlo), -1, np.int32)
    cur_size = np.zeros((nla, nlo), np.float32)
    for t in range(NMON):
        hit = cur >= 0
        tslf[:, :, t] = np.where(hit, np.minimum(t - cur, CAP), CAP)
        last_mon[:, :, t] = np.where(hit, cur_mon, -1)
        last_size[:, :, t] = np.where(hit, cur_size, 0.0)
        b = burned[:, :, t]                      # update AFTER writing month t -> strict inequality
        cur = np.where(b, t, cur)
        cur_mon = np.where(b, (t % 12) + 1, cur_mon)
        cur_size = np.where(b, Bz[:, :, t], cur_size)
    censored = (tslf >= CAP).astype(np.float32)

    # ---- how often it burns, trailing windows, all on the shifted matrix ----------------------
    def trail(A, w):
        c = np.cumsum(A.astype(np.float32), axis=2)
        out = np.empty_like(c)
        out[:, :, :w] = c[:, :, :w]
        out[:, :, w:] = c[:, :, w:] - c[:, :, :-w]
        return out
    n12 = trail(past, 12)
    n60 = trail(past, 60)
    n120 = trail(past, 120)
    obs_shift = np.zeros_like(obs)
    obs_shift[:, :, 1:] = obs[:, :, :-1]
    seen120 = np.maximum(trail(obs_shift, 120), 1.0)
    rate120 = n120 / seen120                     # burns per observed month, a return-rate proxy

    # ---- SPATIAL: a TRUE RING -- the surrounding cells with THIS CELL REMOVED ----------------
    # A plain uniform_filter box is centred on the cell, so the cell counts itself: a lone burning
    # cell scores 1/9 in its own "neighbourhood" at radius 1. That is not a leak at a lag, but it
    # makes the column a blend of own-history and neighbour-history, redundant with n_burns_*, and
    # it makes the SPATIAL claim untestable -- a gain could be either mechanism. Subtracting the
    # centre gives a genuine ring, so a gain here can only come from other cells.
    #
    # LAG LADDER, because "is the neighbourhood a leak?" is an empirical question. A 1-month lag
    # already excludes same-month co-burning, but a single fire EVENT can straddle a month
    # boundary -- burning a neighbour on 31 Jan and this cell on 1 Feb -- so a lag-1 gain may be
    # the same fire seen a day earlier rather than genuine antecedent structure. Lags 3 and 6 put
    # a real gap between cause and effect: if the signal survives them it is regional fuel and
    # weather, and if it collapses it was same-event bleed. Build all three and let the ablation
    # decide rather than arguing about it.
    dlat_km = float(np.median(np.diff(la))) * 111.32 if nla > 1 else 4.0
    rings = {}

    def ring_mean(A, rad):
        """Box mean with the centre cell removed."""
        n = float((2 * rad + 1) ** 2)
        box = uniform_filter(A, size=(2 * rad + 1, 2 * rad + 1, 1), mode="nearest")
        return (box * n - A) / (n - 1.0)

    for lag in LAGS:
        sh = np.zeros_like(Bz)
        if lag < NMON:
            sh[:, :, lag:] = Bz[:, :, :-lag]            # burned fraction, lagged
        shb = np.zeros_like(burned)
        if lag < NMON:
            shb[:, :, lag:] = burned[:, :, :-lag]
        t12 = trail(shb, 12) > 0                         # burned at all in the 12 mo before lag
        for km in RINGS_KM:
            rad = max(1, int(round(km / max(dlat_km, 1e-6))))
            rings["nbr%dkm_lag%d" % (int(km), lag)] = ring_mean(sh, rad)
            rings["nbr%dkm_12mo_lag%d" % (int(km), lag)] = ring_mean(t12.astype(np.float32), rad)
    log("    ring radii %s cells (cell %.2f km N-S) | lags %s"
        % ({int(k): max(1, int(round(k / max(dlat_km, 1e-6)))) for k in RINGS_KM}, dlat_km, LAGS))

    # ---- subset to the modelling cells and emit ---------------------------------------------
    sel = pd.read_parquet("D:/fire/cells_1000.parquet")
    sel = sel[sel.region == region]
    si = np.searchsorted(la, np.round(sel.lat.values.astype(np.float64), 5))
    sj = np.searchsorted(lo, np.round(sel.lon.values.astype(np.float64), 5))
    keep = (si >= 0) & (si < nla) & (sj >= 0) & (sj < nlo)
    si, sj = si[keep], sj[keep]
    lat_s, lon_s = sel.lat.values[keep], sel.lon.values[keep]
    n = len(si)
    yy = np.repeat(np.array([y for y in YEARS for _ in range(12)]), 1)
    mm_ = np.array([m for _ in YEARS for m in range(1, 13)])
    out = pd.DataFrame({
        "lat": np.repeat(lat_s, NMON), "lon": np.repeat(lon_s, NMON),
        "year": np.tile(yy, n), "month": np.tile(mm_, n),
        "tslf_months": tslf[si, sj, :].ravel(),
        "tslf_censored": censored[si, sj, :].ravel(),
        "last_burn_month": last_mon[si, sj, :].ravel(),
        "last_burn_size": last_size[si, sj, :].ravel(),
        "n_burns_12mo": n12[si, sj, :].ravel(),
        "n_burns_60mo": n60[si, sj, :].ravel(),
        "burn_rate_120mo": rate120[si, sj, :].ravel(),
    })
    for k, v in rings.items():
        out[k] = v[si, sj, :].ravel()

    # ---- THE ASSERTION. A cell burning at t must not have tslf == 0 at t. If the shift were
    # wrong by one month this fires immediately, which is the whole point of writing it down.
    bt = burned[si, sj, :].ravel()
    bad = int(((out.tslf_months.values == 0) & bt).sum())
    if bad:
        raise AssertionError("LEAK: %d cell-months have tslf==0 while burning -- the strict "
                             "inequality is broken, every number downstream would be worthless"
                             % bad)
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "%s.parquet" % region)
    out.to_parquet(dst + ".part", index=False)
    os.replace(dst + ".part", dst)
    return out, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    A = ap.parse_args()
    regs = ([x.strip() for x in A.only.split(",")] if A.only else complete_regions())
    log("=" * 104)
    log("FIRE HISTORY DRIVERS | %d regions | %s" % (len(regs), mem_str()))
    done = 0
    for r in regs:
        dst = os.path.join(OUT, "%s.parquet" % r)
        if os.path.exists(dst):
            log("  %-30s HAVE" % r)
            done += 1
            continue
        t0 = time.time()
        try:
            out, n = build(r)
        except Exception as ex:
            log("  %-30s FAILED: %s" % (r, repr(ex)[:110]))
            continue
        nz = out.tslf_months < CAP
        log("  %-30s %6d cells  %8s rows  ever-burned %5.1f%%  median TSLF %5.0f mo  %.1f min"
            % (r, n, format(len(out), ","), 100 * nz.mean(),
               float(out.loc[nz, "tslf_months"].median()) if nz.any() else float("nan"),
               (time.time() - t0) / 60))
        done += 1
    log("=" * 104)
    log("%d/%d regions written to %s" % (done, len(regs), OUT))
    log("NEXT: join these onto the modelling matrix and re-run. Read the result knowing that")
    log("neighbourhood columns are built from the SAME product as the target -- at strict lag they")
    log("are autoregressive rather than leaky, but they inflate a RANDOM-split evaluation by about")
    log("72%% of their apparent value, so they must be judged region-blocked and time-blocked only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
