"""Ingest GFED500m monthly burned fraction onto the panel's cells. The missing smoke driver.

WHY THIS PRODUCT AND NOT THE OBVIOUS TWO.
  NOT the panel's own burn columns. V20_burned_binary, burn_month_count and burn_doy_mean are
  CONSTANT WITHIN THE YEAR for 100% of cells -- annual aggregates stamped onto twelve months, so
  January already knows when August burned. Measured |r| with PM2.5: 0.092, 0.053, 0.042. They
  carry look-ahead and pay nothing for it.
  NOT GFED4.1s. After 2016 it stops deriving emissions from burned area and switches to active-fire
  detections with a conversion calibrated on 2003-2016; every 2017-2023 file is labelled _beta.
  That mechanism change sits INSIDE the 2020-2023 test window.
  NOT raw MCD64A1. 268 granules/month, ~125-130 GB for the window, an Earthdata login, and the
  unmapped-vs-unburned mask trap.
GFED500m (van Wees et al., Zenodo 17338226) covers 2002-2023 exactly, at 500 m, with no mid-series
mechanism change and no credentials.

BURNED AREA ONLY, AND CARBON DELIBERATELY LEFT BEHIND. The product also ships C_AG_TOT and
C_BG_TOT, which are closer to the smoke flux that actually makes PM2.5. They are not taken, because
GFED500m's fuel model carries MCD12Q1, MOD44B, MCD15A2H, Hansen forest loss, GLEAM and ERA5-LAND
inside it. Taking carbon would import this panel's own era5l_* drivers back through the target's
driver. BA_TOT is a burned-area retrieval and is the cleaner column.

LEAK STATUS: PHYSICS-UPSTREAM, and the paper must say so. ACAG's GEOS-Chem is driven by GFED4 open
fire emissions whose burned-area provenance is MCD64A1, which is also GFED500m's provenance. So
this driver sits upstream of the target -- but as an EMISSION FLUX CONSUMED BY A SIMULATION, not as
a predictor in the fitted GWR step. The V5 GWR's eleven predictors contain no fire variable at all
(van Donkelaar et al. 2021 SI S3). Second hop to disclose: the GWR's simulated-OC compositional
predictor is partly a function of those fire emissions.

HOW IT DOWNLOADS, AND WHY NOT SELECTIVELY. The obvious design -- Zenodo serves HTTP range
requests, a zip's central directory sits at its end, so read only the tiles these regions touch --
was built and MEASURED, and it does not pay. The 127 regions are scattered globally enough to touch
216 of the 226 tiles in a year, so ranged reads pull 484 MB against a 489 MB zip: no saving, bought
with 216 round trips instead of one sequential transfer, which timed at 254 s for a single year.
Identical finding to the ACAG chunk experiment. So the year zip is fetched once, sequentially, to
D: (C: is full) and deleted as soon as the year is written. Peak disk is one zip, peak memory one
tile. RangeFile is kept because --plan uses it to list members for a few KB.

    py -3.9 -u gfed_burn_ingest.py --plan      which tiles are needed, and the download estimate
    py -3.9 -u gfed_burn_ingest.py --smoke     one year, to verify before committing
    py -3.9 -u gfed_burn_ingest.py             all 22 years
    py -3.9 -u gfed_burn_ingest.py --assemble  -> D:/gfed_burn/{region}_burn_{year}.parquet
"""
import io
import json
import os
import sys
import time
import traceback
import urllib.request
import zipfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acag_pm25_ingest as ing

ZENODO = "https://zenodo.org/api/records/17338226"
OUT = "D:/gfed_burn"
MON = os.path.join(OUT, "_monthly")
VAR = "MOD_Grid/burned_area/BA_TOT"

# MODIS sinusoidal grid constants. Not guessed -- these are the fixed definition of the grid the
# 2400x2400 tiles live on, and every one is exact.
R = 6371007.181            # sphere radius, m
TILE = 1111950.5196666666  # tile edge, m
X0 = -20015109.354         # left edge of tile h=0
Y0 = 10007554.677          # top edge of tile v=0
NPIX = 2400
PIX = TILE / NPIX          # 463.31271653 m

YEARS = list(range(2002, 2024))
SMOKE_YEARS = [2015]
SMOKE_REGIONS = ["borneo_peat_fires", "angola_zambia_fire_belt", "miombo_woodland_zambia",
                 "northern_australia_monsoon", "sahel", "thar_desert"]


def log(m):
    print(m, flush=True)


class RangeFile(io.RawIOBase):
    """Seekable file-like backed by HTTP range requests, so a zip member can be read alone."""

    def __init__(self, url):
        self.url, self.pos, self.n_bytes = url, 0, 0
        r = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(r, timeout=90) as h:
            self.size = int(h.headers["Content-Length"])

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off)
        return self.pos

    def read(self, size=-1):
        if size < 0:
            size = self.size - self.pos
        if size <= 0:
            return b""
        hi = min(self.pos + size, self.size) - 1
        for attempt in range(4):
            try:
                req = urllib.request.Request(self.url,
                                             headers={"Range": "bytes=%d-%d" % (self.pos, hi)})
                with urllib.request.urlopen(req, timeout=300) as h:
                    b = h.read()
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(3 * (attempt + 1))
        self.n_bytes += len(b)
        self.pos += len(b)
        return b

    def readinto(self, buf):
        d = self.read(len(buf))
        buf[:len(d)] = d
        return len(d)


def lonlat_to_tile(lat, lon):
    """Which sinusoidal tile does this lat/lon fall in?"""
    la = np.radians(lat)
    x = R * np.radians(lon) * np.cos(la)
    y = R * la
    h = np.floor((x - X0) / TILE).astype(int)
    v = np.floor((Y0 - y) / TILE).astype(int)
    return h, v


def tiles_for(g, pad=1):
    """Tiles a region's cell grid touches. Sampled on a dense lat/lon lattice because a lat/lon
    rectangle maps to a CURVED patch in sinusoidal coordinates -- the four corners are not enough.
    """
    la = np.linspace(g["lat_edges"][0], g["lat_edges"][-1], 60)
    lo = np.linspace(g["lon_edges"][0], g["lon_edges"][-1], 60)
    LA, LO = np.meshgrid(la, lo, indexing="ij")
    h, v = lonlat_to_tile(LA.ravel(), LO.ravel())
    out = set()
    for hh, vv in zip(h, v):
        for dh in range(-pad, pad + 1):
            for dv in range(-pad, pad + 1):
                if 0 <= hh + dh < 36 and 0 <= vv + dv < 18:
                    out.add((int(hh + dh), int(vv + dv)))
    return out


def tile_lat_lon(h, v):
    """Centre lat (per row) and lon (per row, per column) of every pixel in one tile.

    lat depends only on the row; lon depends on both, because sinusoidal x is scaled by cos(lat).
    """
    i = np.arange(NPIX)
    y = Y0 - v * TILE - (i + 0.5) * PIX
    lat = np.degrees(y / R)
    x = X0 + h * TILE + (np.arange(NPIX) + 0.5) * PIX
    return lat, x


def accumulate(ba, h, v, prep, sums, cnts):
    """Bin one tile's 12 monthly burned-fraction grids into the panel's cells.

    Every pixel is assigned to exactly one cell by digitising its coordinates into the region's own
    cell EDGES, so the result is an honest area mean rather than a nearest-neighbour sample. Cell
    size varies by region (4.00 km at the equator, 1.45 km in Lapland), which is why edges are used
    instead of a fixed window.
    """
    lat, x = tile_lat_lon(h, v)
    # LON IS A PROPERTY OF THE TILE, NOT OF THE REGION. The first version computed this (2400,2400)
    # array inside the region loop, so a tile shared by five regions built it five times. Hoisted.
    cl = np.cos(np.radians(lat))
    cl[np.abs(cl) < 1e-12] = 1e-12
    LON = np.degrees(x[None, :] / (R * cl[:, None]))          # (2400, 2400), ~46 MB
    for reg, (g, fi, nr, nc) in prep.items():
        la0, la1 = g["lat_edges"][0], g["lat_edges"][-1]
        lo0, lo1 = g["lon_edges"][0], g["lon_edges"][-1]
        rows = np.where((lat >= la0) & (lat <= la1))[0]
        if not rows.size:
            continue
        ri = np.searchsorted(g["lat_edges"], lat[rows]) - 1
        okr = (ri >= 0) & (ri < nr)
        if not okr.any():
            continue
        rows, ri = rows[okr], ri[okr]
        lon = LON[rows]
        inlon = (lon >= lo0) & (lon <= lo1)
        if not inlon.any():
            continue
        ci = np.searchsorted(g["lon_edges"], lon) - 1
        good = inlon & (ci >= 0) & (ci < nc)
        if not good.any():
            continue
        flat = (ri[:, None] * nc + ci)[good]
        n = nr * nc
        for m in range(12):
            vals = ba[m][rows][good].astype(np.float64)
            fin = np.isfinite(vals) & (vals >= 0)
            if not fin.any():
                continue
            sums[reg][m] += np.bincount(flat[fin], weights=vals[fin], minlength=n)
            cnts[reg][m] += np.bincount(flat[fin], minlength=n)



def assemble():
    """Monthly all-region files -> one file per region-year, matching the PM2.5 layout.

    WHY THIS EXISTS. The screening script first read all 264 global monthly files once PER REGION
    to pull that region's rows -- 127 x 264 file reads of 2 million rows each, off a 7200 RPM disk.
    Pivoting the layout once turns that into one small read per region-year.
    """
    import glob as _g
    fs = sorted(_g.glob(os.path.join(MON, "*.parquet")))
    if not fs:
        log("nothing in %s" % MON)
        return 0
    os.makedirs(OUT, exist_ok=True)
    by_year = {}
    for f in fs:
        by_year.setdefault(int(os.path.basename(f)[:4]), []).append(f)
    for y in sorted(by_year):
        d = pd.concat([pd.read_parquet(f) for f in sorted(by_year[y])], ignore_index=True)
        for reg, g in d.groupby("region", sort=True):
            g.drop(columns=["region"]).to_parquet(
                os.path.join(OUT, "%s_burn_%d.parquet" % (reg, y)),
                index=False, compression="zstd")
        log("  %d: %s rows -> %d regions (%.1f%% mapped)"
            % (y, format(len(d), ","), d.region.nunique(),
               100.0 * np.isfinite(d.burn_frac).mean()))
        del d
    log("done -> %s" % OUT)
    return 0


def main():
    a = sys.argv[1:]
    os.makedirs(MON, exist_ok=True)
    if "--assemble" in a:
        return assemble()
    smoke = "--smoke" in a

    grids = ing.region_grids()
    # Align to the SAME 127 regions the PM2.5 target covers. GFED is global sinusoidal with no
    # latitude cut, so it would happily produce all 133 -- but six of those have no target, and a
    # driver without a target is wasted work plus an invitation to a mismatched join later.
    grids = {r: g for r, g in grids.items()
             if g["lat"].min() >= ing.GRID_LO and g["lat"].max() <= ing.GRID_HI}
    if smoke:
        grids = {k: g for k, g in grids.items() if k in SMOKE_REGIONS}
    prep, need = {}, {}
    for reg, g in grids.items():
        prep[reg] = (g, ing.cell_index(g), len(g["lat_vals"]), len(g["lon_vals"]))
        for t in tiles_for(g):
            need.setdefault(t, []).append(reg)
    log("regions %d   cells %s   sinusoidal tiles needed %d of 648 possible"
        % (len(grids), format(sum(len(g["cell_id"]) for g in grids.values()), ","), len(need)))

    with urllib.request.urlopen(ZENODO, timeout=90) as h:
        rec = json.loads(h.read().decode("utf-8"))
    files = {f["key"]: f["links"]["self"] for f in rec["files"]}
    sizes = {f["key"]: f["size"] for f in rec["files"]}

    if "--plan" in a:
        k = "500m_2015.zip"
        rf = RangeFile(files[k])
        z = zipfile.ZipFile(rf)
        members = {}
        for n in z.namelist():
            if n.endswith(".nc"):
                base = os.path.basename(n)
                tag = [p for p in base.split("_") if p.startswith("h") and "v" in p]
                if tag:
                    members[tag[0]] = z.getinfo(n).compress_size
        want = ["h%02dv%02d" % (hh, vv) for hh, vv in need]
        have = [t for t in want if t in members]
        comp = sum(members[t] for t in have)
        log("  tiles present in archive : %d of %d requested" % (len(have), len(want)))
        log("  compressed bytes needed  : %.0f MB per year  (whole zip is %.0f MB)"
            % (comp / 1e6, sizes[k] / 1e6))
        log("  ESTIMATED TOTAL DOWNLOAD : %.2f GB for 22 years  (vs %.2f GB for all zips)"
            % (comp * 22 / 1e9, sum(v for k2, v in sizes.items() if k2.startswith("500m_")) / 1e9))
        return 0

    years = SMOKE_YEARS if smoke else YEARS
    total = 0
    for y in years:
        outs = [os.path.join(MON, "%04d%02d.parquet" % (y, m + 1)) for m in range(12)]
        if all(os.path.exists(p) for p in outs):
            continue
        key = "500m_%d.zip" % y
        if key not in files:
            log("  [%d] NOT IN ARCHIVE" % y)
            continue
        t0 = time.time()
        sums = {r: [np.zeros(len(g["lat_vals"]) * len(g["lon_vals"])) for _ in range(12)]
                for r, (g, _, _, _) in prep.items()}
        cnts = {r: [np.zeros(len(g["lat_vals"]) * len(g["lon_vals"])) for _ in range(12)]
                for r, (g, _, _, _) in prep.items()}
        tmpzip = os.path.join(MON, "_%d.zip.part" % y)
        nb = 0
        try:
            # WHOLE ZIP, NOT RANGED MEMBER READS. Measured with --plan: these regions touch 216 of
            # the 226 tiles, so ranged reads pull 484 MB against a 489 MB zip -- no saving at all,
            # paid for with 216 round trips instead of one sequential transfer, which measured
            # 254 s for a single year. Identical finding to the ACAG chunk experiment. The zip
            # lands on D: because C: is full, and is deleted as soon as the year is done.
            with urllib.request.urlopen(files[key], timeout=900) as src:
                with open(tmpzip, "wb") as dst:
                    while True:
                        chunk = src.read(1 << 22)
                        if not chunk:
                            break
                        dst.write(chunk)
                        nb += len(chunk)
            t_dl = time.time() - t0
            z = zipfile.ZipFile(tmpzip)
            bytile = {}
            for n in z.namelist():
                if not n.endswith(".nc"):
                    continue
                tg = [p for p in os.path.basename(n).split("_") if p.startswith("h") and "v" in p]
                if tg:
                    bytile[tg[0]] = n
            got = 0
            for (hh, vv) in sorted(need):
                nm = bytile.get("h%02dv%02d" % (hh, vv))
                if nm is None:
                    continue
                import h5py
                try:
                    f = h5py.File(io.BytesIO(z.read(nm)), "r")
                except Exception:
                    continue
                if VAR not in f:
                    f.close()
                    continue
                ba = f[VAR][:]
                sub = {r: prep[r] for r in need[(hh, vv)] if r in prep}
                if sub:
                    accumulate(ba, hh, vv, sub, sums, cnts)
                f.close()
                got += 1
            total += nb
            frames = {m: [] for m in range(12)}
            for reg, (g, fi, nr, nc) in prep.items():
                for m in range(12):
                    c = cnts[reg][m]
                    with np.errstate(invalid="ignore", divide="ignore"):
                        mean = np.where(c > 0, sums[reg][m] / np.maximum(c, 1), np.nan)
                    frames[m].append(pd.DataFrame({
                        "region": reg, "cell_id": g["cell_id"],
                        "year": np.int16(y), "month": np.int8(m + 1),
                        "burn_frac": mean[fi].astype(np.float32),
                        "burn_npix": c[fi].astype(np.int32)}))
            for m in range(12):
                d = pd.concat(frames[m], ignore_index=True)
                tmp = outs[m] + ".tmp"
                d.to_parquet(tmp, index=False, compression="zstd")
                os.replace(tmp, outs[m])
            cov = 100.0 * np.mean([np.isfinite(pd.read_parquet(outs[0]).burn_frac).mean()])
            log("  [%d] %d tiles  %s cells  %4.1f%% mapped  %6.1f MB  dl %5.1fs + proc %5.1fs = %5.1fs"
                % (y, got, format(len(d), ","), cov, nb / 1e6, t_dl,
                   time.time() - t0 - t_dl, time.time() - t0))
        except Exception:
            log("  [%d] FAILED:\n%s" % (y, traceback.format_exc()[-700:]))
        finally:
            try:
                z.close()
            except Exception:
                pass
            try:
                if os.path.exists(tmpzip):
                    os.remove(tmpzip)
            except Exception:
                pass

    log("")
    log("%.2f GB pulled" % (total / 1e9))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
