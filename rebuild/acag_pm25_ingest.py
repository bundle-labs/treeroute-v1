"""Ingest ACAG V5.GL.06 monthly surface PM2.5 onto the panel's cells. Problem #5's target.

WHY THIS PRODUCT, in one paragraph. Every gridded air-quality product is circular with this panel's
meteorological drivers to some degree (Part 537). V5.GL.06 is the least-bad point on that curve that
is also usable: meteorology enters only through GEOS-Chem's AOD-to-PM2.5 ratio, never as a direct
predictor -- unlike V6.GL.03, which feeds MERRA-2 PBLH/RH/u/v/T straight into its CNN, and unlike
GHAP, which uses 19 ERA5 fields plus MODIS NDVI plus SRTM elevation and is therefore a hard leak
against this project's own rulings. V5.GL.06 is also the only global line shipping a per-cell
monthly UNCERTAINTY field, which is the instrument for the monitor-density confound.

WHY NOT THE 0.05 DEGREE VARIANT, which is 1.74 GB against this one's 29.75 GB. The panel's cells
are not 4 km everywhere: longitude step is a constant 0.0359 deg and latitude tracks it to keep
cells square, so a cell is 4.00 km at the equator, 3.60 km at Thar and 1.45 km in Lapland. At
5.57 km the coarse product is coarser than EVERY cell in the panel, and its grid stops at 67.975N.
The fine product's 1.11 km pixel is finer than all of them.

THE FILL VALUE IS 9.96921e+36 AND THAT IS THE DANGEROUS PART. It was read from the file header, not
inferred -- the survey had guessed -999, which is wrong in a way that matters: the real value is
POSITIVE, so a `< 0` guard never sees it, and it is FINITE, so `np.isfinite` passes it straight
through. That is exactly how -32768 survived every guard in this project and flattened a 27M-row
correlation to r2 0.0004 (Part 535). It is masked here at the point of read, before any arithmetic.

WHAT THIS CANNOT REACH. ACAG's grid is lat -54.995..67.995. taimyr_peninsula and alaska_north_slope
fall entirely outside it; finnish_lapland loses 82%, yamal_peninsula 77%, canadian_arctic_nunavut
20%, tierra_del_fuego 3%. 7.85% of all cells. The script reports this per region rather than
silently writing NaN, so the region list used downstream is a decision, not an accident.

HOW IT DOWNLOADS, AND WHY NOT LAZILY. Nothing is written to disk but the output. The obvious design
-- h5py over s3fs, fetching only the gzip chunks the region boxes touch -- was built and MEASURED,
and it is worse: 317 MB pulled per 127 MB file, 2.5x the archive, because the files are chunked at
1119 x 3273 (11.2 x 32.7 degrees, only 121 chunks globally), 127 scattered regions keep landing in
the same chunks, and fsspec's read-ahead cache is not a chunk cache, so chunks are re-fetched. Over
264 months that is 83.7 GB to obtain a 29.75 GB archive. Reading each file once into memory costs
exactly its size, needs ~130 MB of RAM, and is faster -- one sequential transfer per month instead
of thousands of ranged round trips.

RESUMABLE BY CONSTRUCTION. One output file per month; an existing file is skipped. Kill it and
restart and it picks up where it stopped. Outputs go to D: because C: is full.

    py -3.9 -u acag_pm25_ingest.py --smoke      3 months, 6 regions -- run this FIRST
    py -3.9 -u acag_pm25_ingest.py              all 264 months, all regions
    py -3.9 -u acag_pm25_ingest.py --assemble   monthly files -> per-region-year panel files
    py -3.9 -u acag_pm25_ingest.py --uncertainty  the PM25 uncertainty layer (14.57 GB), same shape
"""
import glob
import io
import os
import sys
import time
import traceback

import numpy as np
import pandas as pd

PANEL = "D:/monthly_panel"
OUT = "D:/pm25_acag"
MON = os.path.join(OUT, "_monthly")

BUCKET = "satpmdata"
# Two products, identical grid and naming pattern. The uncertainty layer is the companion to the
# PM2.5 layer and exists only on the V5 GWR line -- V6 ships none.
PRODUCTS = {
    "pm25": ("V5GL06/GWRPM25/Monthly/Global", "V5GL06.HybridPM25.Global.%s-%s.nc", "GWRPM25"),
    "unc": ("V5GL06/GWRPM25Uncertainty/Monthly/Global", "V5GL06.HybridPM25E.Global.%s-%s.nc",
            None),
}

YEAR0, YEAR1 = 2002, 2023
# ACAG V5.GL.06 grid bounds, READ from the file header, not from documentation.
GRID_LO, GRID_HI = -54.995, 67.995
FILL = 9.96921e36
# Anything at or above this is the fill value or arithmetic on it. A plain equality test would miss
# a value that has been through a float32->float64 conversion, and PM2.5 never exceeds ~1000 ug/m3.
FILL_FLOOR = 1e30

SMOKE_REGIONS = ["thar_desert", "ganges_plain", "north_china_plain",
                 "sahel", "borneo_peat_fires", "poland_central"]


class Counting(io.RawIOBase):
    """Wraps the S3 file object so the bytes actually pulled can be reported."""

    def __init__(self, f):
        self.f, self.n = f, 0

    def read(self, size=-1):
        b = self.f.read(size)
        self.n += len(b)
        return b

    def readinto(self, buf):
        d = self.f.read(len(buf))
        buf[:len(d)] = d
        self.n += len(d)
        return len(d)

    def seek(self, o, w=0):
        return self.f.seek(o, w)

    def tell(self):
        return self.f.tell()

    def seekable(self):
        return True

    def readable(self):
        return True


def log(m):
    print(m, flush=True)


def region_grids():
    """Per region: cell ids and the EDGES of their lat/lon grid.

    Edges, not centres, because the target for a cell is the mean of the ACAG pixels that fall
    INSIDE it, and cell size varies by region (4.00 km at the equator down to 1.45 km in Lapland).
    Digitising pixel coordinates into these edges assigns every pixel to exactly one cell without
    assuming a fixed window size.
    """
    out = {}
    for f in sorted(glob.glob(os.path.join(PANEL, "*_monthly_2015.parquet"))):
        reg = os.path.basename(f).split("_monthly_")[0]
        d = pd.read_parquet(f, columns=["cell_id", "lat", "lon"]).drop_duplicates("cell_id")
        la = np.sort(d.lat.unique())
        lo = np.sort(d.lon.unique())
        dla = np.median(np.diff(la)) if len(la) > 1 else 0.0359
        dlo = np.median(np.diff(lo)) if len(lo) > 1 else 0.0359
        out[reg] = {
            "cell_id": d.cell_id.to_numpy(),
            "lat": d.lat.to_numpy(), "lon": d.lon.to_numpy(),
            "lat_edges": np.concatenate([[la[0] - dla / 2], (la[:-1] + la[1:]) / 2,
                                         [la[-1] + dla / 2]]),
            "lon_edges": np.concatenate([[lo[0] - dlo / 2], (lo[:-1] + lo[1:]) / 2,
                                         [lo[-1] + dlo / 2]]),
            "lat_vals": la, "lon_vals": lo,
        }
    return out


def cell_index(g):
    """Map each cell onto its (row, col) in the region's own lat/lon grid, once."""
    ri = np.searchsorted(g["lat_vals"], g["lat"])
    ci = np.searchsorted(g["lon_vals"], g["lon"])
    ri = np.clip(ri, 0, len(g["lat_vals"]) - 1)
    ci = np.clip(ci, 0, len(g["lon_vals"]) - 1)
    return ri * len(g["lon_vals"]) + ci


def extract(d, lat, lon, g, flat_idx, nr, nc):
    """Mean of the ACAG pixels falling inside each cell of one region.

    Returns NaN for cells that the ACAG grid does not reach (outside its latitude range) and for
    cells whose every pixel is fill -- those are two different kinds of missing and both must stay
    missing rather than becoming zero.
    """
    la0, la1 = g["lat_edges"][0], g["lat_edges"][-1]
    lo0, lo1 = g["lon_edges"][0], g["lon_edges"][-1]
    if la1 <= lat[0] or la0 >= lat[-1]:
        return np.full(len(g["cell_id"]), np.nan, np.float64), 0

    i0 = max(0, int(np.searchsorted(lat, la0)) - 1)
    i1 = min(len(lat), int(np.searchsorted(lat, la1)) + 1)
    j0 = max(0, int(np.searchsorted(lon, lo0)) - 1)
    j1 = min(len(lon), int(np.searchsorted(lon, lo1)) + 1)
    if i1 <= i0 or j1 <= j0:
        return np.full(len(g["cell_id"]), np.nan, np.float64), 0

    box = d[i0:i1, j0:j1].astype(np.float64)
    # MASK THE FILL VALUE BEFORE ANY ARITHMETIC. 9.96921e+36 is positive and finite; one of them
    # inside a mean makes the result ~1e36 and no isfinite or <0 guard would catch it.
    box[box >= FILL_FLOOR] = np.nan
    box[~np.isfinite(box)] = np.nan

    blat, blon = lat[i0:i1], lon[j0:j1]
    # -1 so that a pixel below the first edge lands outside the grid rather than in cell 0
    ri = np.searchsorted(g["lat_edges"], blat) - 1
    ci = np.searchsorted(g["lon_edges"], blon) - 1
    okr = (ri >= 0) & (ri < nr)
    okc = (ci >= 0) & (ci < nc)
    if not okr.any() or not okc.any():
        return np.full(len(g["cell_id"]), np.nan, np.float64), 0

    sub = box[np.ix_(okr, okc)]
    flat = (ri[okr][:, None] * nc + ci[okc][None, :]).ravel()
    vals = sub.ravel()
    good = np.isfinite(vals)
    n = nr * nc
    s = np.bincount(flat[good], weights=vals[good], minlength=n)
    k = np.bincount(flat[good], minlength=n)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(k > 0, s / np.maximum(k, 1), np.nan)
    return mean[flat_idx], int(good.sum())


def months(smoke):
    ms = [(y, m) for y in range(YEAR0, YEAR1 + 1) for m in range(1, 13)]
    return ms[6:9] if smoke else ms


def run(which, smoke):
    import fsspec
    import h5py

    prefix, pat, _ = PRODUCTS[which]
    outdir = MON if which == "pm25" else MON + "_unc"
    if smoke:
        # A smoke month holds 6 regions. Writing it into the real directory would make the
        # resume check skip it as done, silently leaving 3 months with 127 regions missing.
        outdir += "_smoke"
    os.makedirs(outdir, exist_ok=True)

    grids = region_grids()
    if "--full-only" in sys.argv[1:]:
        # Regions only PARTLY inside the grid would carry a latitude-shaped hole in the target,
        # which is a selection on a driver (lat) rather than honest missingness.
        keep = {r: g for r, g in grids.items()
                if g["lat"].min() >= GRID_LO and g["lat"].max() <= GRID_HI}
        log("--full-only: %d of %d regions kept, %d dropped" % (len(keep), len(grids),
                                                                len(grids) - len(keep)))
        for r in sorted(set(grids) - set(keep)):
            log("    dropped %s" % r)
        grids = keep
    if smoke:
        grids = {k: v for k, v in grids.items() if k in SMOKE_REGIONS}
    log("regions: %d   cells: %s"
        % (len(grids), format(sum(len(g["cell_id"]) for g in grids.values()), ",")))

    prep = {}
    for reg, g in grids.items():
        nr, nc = len(g["lat_vals"]), len(g["lon_vals"])
        prep[reg] = (g, cell_index(g), nr, nc)

    fs = fsspec.filesystem("s3", anon=True)
    todo = months(smoke)
    if "--nmonths" in sys.argv[1:]:
        todo = todo[:int(sys.argv[sys.argv.index("--nmonths") + 1])]
    log("months: %d (%d-%02d .. %d-%02d)   product: %s"
        % (len(todo), todo[0][0], todo[0][1], todo[-1][0], todo[-1][1], which))
    log("output: %s" % outdir)
    log("")

    t_start = time.time()
    total_bytes = 0
    done = 0
    for y, m in todo:
        tag = "%04d%02d" % (y, m)
        op = os.path.join(outdir, "%s.parquet" % tag)
        if os.path.exists(op):
            continue
        key = "s3://%s/%s/%s" % (BUCKET, prefix, pat % (tag, tag))
        t0 = time.time()
        try:
            # FETCH THE WHOLE FILE ONCE, THEN EXTRACT LOCALLY.
            # Lazy chunk reads over S3 were MEASURED at 317 MB per 127 MB file -- 2.5x the archive
            # -- because 127 scattered region boxes seek back and forth across the same gzip chunks
            # and fsspec's read-ahead cache is not a chunk cache, so chunks are re-fetched. Reading
            # the file once costs exactly its size, uses ~127 MB of RAM, and is faster because it
            # is one sequential transfer instead of thousands of ranged round trips.
            with fs.open(key, "rb") as fh:
                buf = fh.read()
            nbytes = len(buf)
            h = h5py.File(io.BytesIO(buf), "r")
        except Exception as e:
            log("  [%s] OPEN FAILED: %s" % (tag, str(e)[:110]))
            continue
        try:
            name = next(k for k in h.keys() if "PM" in k.upper())
            d = h[name]
            lat, lon = h["lat"][:], h["lon"][:]
            frames = []
            for reg, (g, fi, nr, nc) in prep.items():
                v, npix = extract(d, lat, lon, g, fi, nr, nc)
                frames.append(pd.DataFrame({
                    "region": reg, "cell_id": g["cell_id"],
                    "year": np.int16(y), "month": np.int8(m),
                    "pm25_ugm3": v.astype(np.float32)}))
            out = pd.concat(frames, ignore_index=True)
            tmp = op + ".tmp"
            out.to_parquet(tmp, index=False, compression="zstd")
            os.replace(tmp, op)
            total_bytes += nbytes
            done += 1
            cov = 100.0 * np.isfinite(out.pm25_ugm3).mean()
            log("  [%s] %s cells  %5.1f%% valid  mean %6.2f  %5.1f MB  %4.1fs"
                % (tag, format(len(out), ","), cov,
                   np.nanmean(out.pm25_ugm3) if cov else float("nan"),
                   nbytes / 1e6, time.time() - t0))
        except Exception:
            log("  [%s] FAILED:\n%s" % (tag, traceback.format_exc()[-600:]))
        finally:
            try:
                h.close()
            except Exception:
                pass

    el = time.time() - t_start
    log("")
    log("%d months written, %.2f GB pulled, %.1f min" % (done, total_bytes / 1e9, el / 60.0))
    if done and not smoke:
        log("next: py -3.9 -u acag_pm25_ingest.py --assemble")


def coverage_report():
    """Which regions the ACAG grid cannot reach -- stated up front, not discovered later."""
    LO, HI = GRID_LO, GRID_HI
    log("=" * 84)
    log("WHAT ACAG V5.GL.06 CANNOT REACH  (grid lat %.3f .. %.3f)" % (LO, HI))
    log("=" * 84)
    tot = lost = 0
    bad = []
    for f in sorted(glob.glob(os.path.join(PANEL, "*_monthly_2015.parquet"))):
        reg = os.path.basename(f).split("_monthly_")[0]
        la = pd.read_parquet(f, columns=["lat"]).lat.to_numpy()
        n = len(la) / 12.0
        tot += n
        o = float(((la > HI) | (la < LO)).sum()) / 12.0
        if o > 0:
            lost += o
            bad.append((reg, o, n))
    bad.sort(key=lambda x: -x[1] / x[2])
    for reg, o, n in bad:
        log("  %-30s %8s / %8s  %5.1f%%"
            % (reg, format(int(o), ","), format(int(n), ","), 100.0 * o / n))
    log("  " + "-" * 60)
    log("  TOTAL %s of %s cells (%.2f%%), %d regions affected, %d lost entirely"
        % (format(int(lost), ","), format(int(tot), ","), 100.0 * lost / tot, len(bad),
           sum(1 for _, o, n in bad if o >= n * 0.999)))
    log("")


def assemble():
    """Monthly all-region files -> one file per region-year, matching the panel's layout."""
    fs = sorted(glob.glob(os.path.join(MON, "*.parquet")))
    if not fs:
        log("nothing in %s" % MON)
        return
    log("assembling %d monthly files" % len(fs))
    os.makedirs(OUT, exist_ok=True)
    by_year = {}
    for f in fs:
        by_year.setdefault(int(os.path.basename(f)[:4]), []).append(f)
    nz = 0
    for y in sorted(by_year):
        d = pd.concat([pd.read_parquet(f) for f in sorted(by_year[y])], ignore_index=True)
        # EXACT ZEROS -> NaN. PM2.5 cannot physically be zero; even pristine air carries a few
        # ug/m3 of sea salt and natural background. Measured: 66,856 of 535,568,088 rows (0.0125%),
        # concentrated in 23 very clean regions (northern_australia_woodland, pamir_plateau, karoo)
        # where the non-zero median is under 1 ug/m3 and the product's own relative uncertainty
        # approaches 100%. They are a clean-air numerical floor, not measurements. Small enough to
        # change no score, but a continuous target should not carry a zero spike into Tier 1's
        # zero-fraction test. The raw monthly files are left untouched so this is reversible.
        z = (d.pm25_ugm3 == 0.0)
        nz += int(z.sum())
        d.loc[z, "pm25_ugm3"] = np.nan
        for reg, g in d.groupby("region", sort=True):
            p = os.path.join(OUT, "%s_pm25_%d.parquet" % (reg, y))
            g.drop(columns=["region"]).to_parquet(p, index=False, compression="zstd")
        log("  %d: %s rows -> %d regions  (%.1f%% valid)"
            % (y, format(len(d), ","), d.region.nunique(),
               100.0 * np.isfinite(d.pm25_ugm3).mean()))
    log("masked %s exact zeros to NaN (clean-air floor, not measurements)" % format(nz, ","))
    log("done -> %s" % OUT)


def main():
    a = sys.argv[1:]
    os.makedirs(OUT, exist_ok=True)
    if "--assemble" in a:
        return assemble()
    coverage_report()
    if "--coverage" in a:
        return 0
    run("unc" if "--uncertainty" in a else "pm25", "--smoke" in a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
