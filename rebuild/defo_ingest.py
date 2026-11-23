"""Problem #4 (deforestation) -- STEP 2: aggregate Hansen 30 m to the 4 km panel grid.

WHAT IT PRODUCES, per region, one parquet:
    cell_id, year (2001..2025), loss_px, forest2000_px, land_px, loss_frac

    loss_frac = loss_px / forest2000_px   -- the TARGET.

TARGET DEFINITION, and why each piece is there:
    forest2000_px  = 30 m pixels in the cell with treecover2000 >= 30 AND datamask == 1 (land).
                     This is the DENOMINATOR and the MASK. treecover2000 is a co-product of the same
                     model run that emits lossyear, so it must never be a predictor -- but it is a
                     single year-2000 epoch fixed before the panel window opens, so as an offset it
                     carries zero temporal look-ahead. See DEFORESTATION_SCOPE.md section 4.
    loss_px[y]     = pixels with lossyear == (y - 2000), restricted to that same forest mask.
    land_px        = pixels with datamask == 1. Without it, permanent water and no-data both read as
                     "no loss" and inflate the zero mass.

WHAT IS DELIBERATELY NOT COMPUTED. Nothing is read off the lossyear raster's own VALUE -- no
"years since loss", no forest age, no cumulative-loss-to-date. That raster is a SINGLE STATIC layer
encoding 2001-2025 including the test window, so any feature derived from its value is the
time-since-last-fire trap. Loss is only ever binarised per year here; any cumulative feature must be
built downstream from these per-year counts and truncated at the last training year.

PIXEL -> CELL MAPPING. The panel cells sit on a regular ~0.0359 degree grid, but rather than
reconstruct it analytically this maps each 30 m pixel onto the region's OWN sorted unique cell
centres with searchsorted over midpoint edges. That is exact and survives any small irregularity in
the grid spacing.

MEMORY AND DISK. Granules are 40000x40000; one is 1.6 GB uncompressed, so nothing is ever read whole.
Each region reads only its bounding window, in horizontal strips, three layers at a time (~30 MB per
strip). D: is a 7200 rpm HDD -- strips are sequential reads, which is the access pattern it likes.

RESUMABLE. One parquet per region, skipped if present. Safe to Ctrl-C and restart.

RUN IT:
    py -3.9 -u defo_ingest.py                 # all 42 forested regions
    py -3.9 -u defo_ingest.py --region=congo_basin_drc
    py -3.9 -u defo_ingest.py --smoke          # one small region, to time it
"""
import os
import sys
import glob
import time
import gc
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window

HANSEN = "D:/hansen"
PANEL = "D:/monthly_panel"
OUT = "D:/defo_target"
VERSION = "GFC-2025-v1.13"
PREFIX = "Hansen_%s" % VERSION

TC_THRESH = 30          # Hansen "forest" convention, and what the forest census used
PX = 0.00025            # 1 arc-second
STRIP = 2048            # raster rows per read
YEAR0, YEAR1 = 2001, 2025

ARG = dict(a.split("=", 1) if "=" in a else (a, "1") for a in sys.argv[1:])
os.makedirs(OUT, exist_ok=True)


def log(m):
    print(m, flush=True)
    with open(os.path.join(OUT, "_ingest.log"), "a", encoding="utf-8") as f:
        f.write(m + "\n")


def tile_name(lat, lon):
    ns = "%02dN" % lat if lat >= 0 else "%02dS" % abs(lat)
    ew = "%03dE" % lon if lon >= 0 else "%03dW" % abs(lon)
    return "%s_%s" % (ns, ew)


def tiles_for(lon0, lon1, lat0, lat1):
    out = []
    for tlat in range(80, -60, -10):
        if tlat <= lat0 or tlat - 10 >= lat1:
            continue
        for tlon in range(-180, 180, 10):
            if tlon >= lon1 or tlon + 10 <= lon0:
                continue
            out.append((tlat, tlon))
    return out


def edges(vals):
    """Midpoint bin edges for a sorted array of cell centres."""
    v = np.asarray(vals, np.float64)
    mid = (v[:-1] + v[1:]) / 2.0
    return mid


def do_region(reg):
    dst = os.path.join(OUT, "%s.parquet" % reg)
    if os.path.exists(dst):
        return "skip"

    pf = os.path.join(PANEL, "%s_monthly_2010.parquet" % reg)
    if not os.path.exists(pf):
        log("  %-34s NO PANEL FILE" % reg)
        return "nopanel"
    d = pd.read_parquet(pf, columns=["cell_id", "lon", "lat"]).drop_duplicates("cell_id")
    d["lon"] = pd.to_numeric(d.lon, errors="coerce")
    d["lat"] = pd.to_numeric(d.lat, errors="coerce")
    d = d[np.isfinite(d.lon) & np.isfinite(d.lat)].reset_index(drop=True)
    if not len(d):
        return "nocells"

    ulon = np.sort(d.lon.unique())
    ulat = np.sort(d.lat.unique())
    ex, ey = edges(ulon), edges(ulat)
    ni, nj = len(ulon), len(ulat)

    # cell (i,j) -> compact ordinal
    ii = np.searchsorted(ex, d.lon.values)
    jj = np.searchsorted(ey, d.lat.values)
    grid = np.full((nj, ni), -1, np.int32)
    grid[jj, ii] = np.arange(len(d), dtype=np.int32)
    ncell = len(d)

    nyr = YEAR1 - YEAR0 + 1
    loss = np.zeros((ncell, nyr), np.int64)
    forest = np.zeros(ncell, np.int64)
    land = np.zeros(ncell, np.int64)

    # half a cell of padding so edge pixels are not dropped
    hx = float(np.median(np.diff(ulon))) / 2 if ni > 1 else 0.02   # matches PAD in defo_fetch.py
    hy = float(np.median(np.diff(ulat))) / 2 if nj > 1 else 0.02
    lon0, lon1 = ulon.min() - hx, ulon.max() + hx
    lat0, lat1 = ulat.min() - hy, ulat.max() + hy

    tl = tiles_for(lon0, lon1, lat0, lat1)
    t0 = time.time()
    npx = 0
    for (tlat, tlon) in tl:
        tn = tile_name(tlat, tlon)
        paths = {k: os.path.join(HANSEN, "%s_%s_%s.tif" % (PREFIX, k, tn))
                 for k in ("lossyear", "treecover2000", "datamask")}
        # treecover2000 + datamask are REQUIRED: without them there is no denominator and no land
        # mask, so the granule genuinely cannot be scored.
        if not (os.path.exists(paths["treecover2000"]) and os.path.exists(paths["datamask"])):
            log("    %-34s MISSING GRANULE %s -- region will be INCOMPLETE" % (reg, tn))
            continue
        # lossyear absent is NOT an error. Hansen omits it for granules with no loss to report --
        # verified on 20S_040W, which is entirely ocean (treecover2000 all zero, datamask carries no
        # land value at all). Treat it as zero loss rather than dropping the granule, which would
        # silently discard that granule's forest and land counts from the denominator.
        has_loss = os.path.exists(paths["lossyear"])
        with rasterio.open(paths["treecover2000"]) as rt, \
             rasterio.open(paths["datamask"]) as rd:
            rl = rasterio.open(paths["lossyear"]) if has_loss else None
            T = rt.transform
            # pixel column/row range covering the region bbox within this granule
            c0 = int(np.floor((lon0 - T.c) / PX))
            c1 = int(np.ceil((lon1 - T.c) / PX))
            r0 = int(np.floor((T.f - lat1) / PX))
            r1 = int(np.ceil((T.f - lat0) / PX))
            c0 = max(0, min(c0, rt.width))
            c1 = max(0, min(c1, rt.width))
            r0 = max(0, min(r0, rt.height))
            r1 = max(0, min(r1, rt.height))
            if c1 <= c0 or r1 <= r0:
                continue
            w = c1 - c0
            # pixel-centre longitudes for this column span, constant down the strip
            plon = T.c + (np.arange(c0, c1) + 0.5) * PX
            pi = np.searchsorted(ex, plon).astype(np.int32)
            for rs in range(r0, r1, STRIP):
                re_ = min(rs + STRIP, r1)
                win = Window(c0, rs, w, re_ - rs)
                a_t = rt.read(1, window=win)
                a_l = rl.read(1, window=win) if rl is not None else np.zeros_like(a_t)
                a_d = rd.read(1, window=win)
                plat = T.f - (np.arange(rs, re_) + 0.5) * PX
                pj = np.searchsorted(ey, plat).astype(np.int32)
                cell = grid[pj[:, None], pi[None, :]]          # (rows, cols) ordinal, -1 = outside
                ok = cell >= 0
                if not ok.any():
                    continue
                cid = cell[ok]
                dm = a_d[ok]
                tc = a_t[ok]
                ly = a_l[ok]
                island = dm == 1
                if island.any():
                    land += np.bincount(cid[island], minlength=ncell).astype(np.int64)
                fmask = island & (tc >= TC_THRESH)
                if fmask.any():
                    forest += np.bincount(cid[fmask], minlength=ncell).astype(np.int64)
                    lf = ly[fmask]
                    cf = cid[fmask]
                    hit = lf > 0
                    if hit.any():
                        # one flat bincount over cell*nyr + yearindex
                        flat = cf[hit].astype(np.int64) * nyr + (lf[hit].astype(np.int64) - 1)
                        bc = np.bincount(flat, minlength=ncell * nyr)
                        loss += bc.reshape(ncell, nyr)
                npx += int(ok.sum())
                del a_l, a_t, a_d, cell, ok, cid, dm, tc, ly
            if rl is not None:
                rl.close()
        gc.collect()

    # long format
    cid_rep = np.repeat(d.cell_id.values, nyr)
    yr_rep = np.tile(np.arange(YEAR0, YEAR1 + 1), ncell)
    lp = loss.ravel()
    fp = np.repeat(forest, nyr)
    ld = np.repeat(land, nyr)
    with np.errstate(divide="ignore", invalid="ignore"):
        frac = np.where(fp > 0, lp / np.maximum(fp, 1), np.nan)
    R = pd.DataFrame({"cell_id": cid_rep, "year": yr_rep.astype(np.int16),
                      "loss_px": lp.astype(np.int32), "forest2000_px": fp.astype(np.int32),
                      "land_px": ld.astype(np.int32), "loss_frac": frac.astype(np.float32)})
    R.to_parquet(dst, index=False)

    el = time.time() - t0
    fc = int((forest > 0).sum())
    nz = float((R[R.forest2000_px > 0].loss_frac > 0).mean()) if fc else 0.0
    log("  %-34s %6d cells (%5d forested) | %2d granules | %6.1f Mpx | %5.1f s | non-zero cell-years %.1f%%"
        % (reg, ncell, fc, len(tl), npx / 1e6, el, 100 * nz))
    del loss, forest, land, R
    gc.collect()
    return "ok"


def main():
    C = pd.read_csv("D:/run89full/forest_census.csv")
    regs = C[C.frac_tc30 >= 0.25].sort_values("cells").region.tolist()
    if "--region" in ARG:
        regs = [ARG["--region"]]
    elif "--smoke" in ARG:
        regs = regs[:1]

    log("=" * 104)
    log("HANSEN -> 4 km INGEST | %d regions | forest threshold tc2000 >= %d | %s"
        % (len(regs), TC_THRESH, VERSION))
    t0 = time.time()
    n = {"ok": 0, "skip": 0}
    for k, reg in enumerate(regs, 1):
        r = do_region(reg)
        n[r] = n.get(r, 0) + 1
        if r == "ok":
            el = (time.time() - t0) / 60
            log("      %d/%d done | %.1f min elapsed | ~%.0f min left"
                % (k, len(regs), el, el / max(n["ok"], 1) * (len(regs) - k)))
    log("INGEST DONE | %s | %.1f min" % (n, (time.time() - t0) / 60))


if __name__ == "__main__":
    main()
