"""Choose the modelling cells, once, reproducibly, before any driver is joined.

    py -3.9 -u fire_select_cells.py             # build D:/fire/cells_1000.parquet
    py -3.9 -u fire_select_cells.py --n 400     # a smaller arm

WHY THIS EXISTS AND WHY IT RUNS FIRST. The full panel is 929,533 cells x 252 months = 234,242,316
rows, which at 170 float32 columns is 159 GB on a 15.8 GB machine. The cell cap is therefore not a
tuning choice, it is the thing that makes the problem representable at all. Fixing the cell list up
front also makes every downstream driver subset ~23x cheaper, because a driver is then read at
40,000 cells instead of 929,533.

RANDOM, NOT BURN-STRATIFIED, AND THAT IS A DELIBERATE COST. Oversampling cells that burn would give
far more positive rows to learn from, but it changes the base rate -- and the base rate is the exact
quantity every zero-inflation claim in this problem rests on. A random sample keeps each region's
true fire regime, so a fill rate measured on these cells still means what it says. The price is that
the sparsest regions stay sparse: great_plains at 0.05% fill yields on the order of 130 burned
cell-months out of 252,000. That is the honest number, and if it proves too thin the answer is to
raise the cap for that region and say so, not to quietly rebalance.

SAMPLED FROM THE PANEL/TARGET INTERSECTION, NOT FROM THE PANEL ALONE. A cell we cannot observe the
target at is useless, and a cell the panel does not cover has no drivers. The geometry files were
built from the panel so the two agree almost exactly (16,087 of 16,100 in angola), but the handful
of bbox-edge cells that differ would otherwise become all-NaN rows that survive every later check.

THE SEED IS PART OF THE RESULT. Re-running with the same --n and --seed reproduces the identical
cell list; changing either produces a different panel, and any before/after comparison across such a
change is not a comparison. The seed is written into the output file's metadata columns.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, r"C:\Users\<user>\Desktop\data set for reserch paper")

import numpy as np
import pandas as pd

import fire_fetch_target as F

PANEL = "D:/monthly_panel"
OUT = "D:/fire"
REF_YEAR = 2015          # panel cell lists are identical across years -- verified on thar and alaska


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000, help="cells per region")
    ap.add_argument("--seed", type=int, default=20260827)
    A = ap.parse_args()
    log("=" * 100)
    log("CELL SELECTION | cap %d/region | seed %d" % (A.n, A.seed))
    rows, small = [], []
    for i, r in enumerate(F.REGIONS):
        p = os.path.join(PANEL, "%s_monthly_%d.parquet" % (r, REF_YEAR))
        d = pd.read_parquet(p, columns=["cell_id", "lat", "lon"]).drop_duplicates("cell_id")
        z = np.load(os.path.join("D:/fire/geom", "%s.npz" % r), allow_pickle=True)
        # Keep only cells that lie on the target's own grid. A cell is on that grid iff its lat is
        # one of the geometry's lat values AND its lon is one of its lon values -- so the two 1-D
        # membership tests below are exactly the cross-product test, without materialising the
        # cross product (which for the larger regions is millions of tuples).
        # Round first: both grids derive from the same axis vectors but reach here by different
        # float paths, and an exact == on float64 silently drops real matches.
        la = np.round(np.asarray(z["la"], np.float64), 5)
        lo = np.round(np.asarray(z["lo"], np.float64), 5)
        # CAST BOTH SIDES TO float64 BEFORE ROUNDING. The panel stores lat/lon as float32 and so
        # does the geometry, and np.round on a float32 returns a float32 -- whose nearest
        # representable value is NOT bit-equal to the float64 round of the same decimal. Rounding
        # only the geometry side matched 0 of 4,973 thar cells while looking entirely correct.
        on = (np.isin(np.round(d.lat.values.astype(np.float64), 5), la) &
              np.isin(np.round(d.lon.values.astype(np.float64), 5), lo))
        keep = d[on]
        # A per-region seed, so that adding or reordering REGIONS never reshuffles the cells of the
        # regions that did not change -- a global RNG consumed in loop order would do exactly that.
        rng = np.random.default_rng(A.seed + (abs(hash(r)) % 1_000_000))
        if len(keep) > A.n:
            keep = keep.iloc[np.sort(rng.choice(len(keep), A.n, replace=False))]
        else:
            small.append((r, len(keep)))
        keep = keep.assign(region=r)
        rows.append(keep)
        log("  %-32s panel %6d  ->  kept %5d" % (r, len(d), len(keep)))
    out = pd.concat(rows, ignore_index=True)[["region", "cell_id", "lat", "lon"]]
    out["n_cap"] = A.n
    out["seed"] = A.seed
    dst = os.path.join(OUT, "cells_%d.parquet" % A.n)
    out.to_parquet(dst, index=False)
    log("=" * 100)
    log("%s cells over %d regions -> %s" % (format(len(out), ","), out.region.nunique(), dst))
    log("cell-months 2002-2022: %s  (~%.1f GB at 170 float32 cols)"
        % (format(len(out) * 12 * 21, ","), len(out) * 12 * 21 * 170 * 4 / 1e9))
    if small:
        log("REGIONS SMALLER THAN THE CAP (they contribute fewer rows -- not an error):")
        for r, n in small:
            log("   %-32s %d" % (r, n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
