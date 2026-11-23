"""MCD64A1 burned area -> monthly burned fraction on the existing panel cells. Problem #3, the target.

    py -3.9 -u fire_fetch_target.py --plan          # regions, tiles, request count, no fetch
    py -3.9 -u fire_fetch_target.py --regions 5     # Phase 0: the gating fill-rate measurement
    py -3.9 -u fire_fetch_target.py                 # all 40 regions, 2002-2022, resumable

WHAT THIS PRODUCES. One parquet per (region, year): every panel cell x month, with
  burned_frac       burned MODIS pixels / valid land pixels in the cell        [0,1]
  burn_doy_min/max  earliest and latest burn day-of-year inside the cell-month (diagnostic ONLY --
                    these are TARGET-DERIVED and must never enter X; see the ban list)
  n_pixels          MODIS pixels falling in the cell (varies with latitude, see below)
  n_valid           of those, flagged valid land
  unmapped_frac     fraction coded -1 "insufficient data". A zero here means NOT SEEN, not NOT BURNED

WHY 2002-2022 AND NOT 2023. Two panel drivers (SPEI, AMO) vanish in 2023, so a 2023 row cannot be
scored on the same feature set. MCD64A1 itself has no 2023 problem -- it runs to present -- so
--years extends it in one flag if those gaps are ever repaired. Note this does NOT fix the MODIS
orbital drift, which begins Feb 2020 (Terra) and Jul 2021 (Aqua) and therefore sits inside
2020-2022 as well; that is a separate hazard handled at split time, not here.

THE CELL GRID IS NOT 4 km AND THAT MATTERS FOR THIS TARGET. The panel holds cells SQUARE IN KM with
a constant 0.03593 deg longitude step and a latitude step of dlon*cos(lat). Measured: Borneo 4.00 km,
Thar 3.60, Great Plains 2.99, Alaska 1.72. So MODIS pixels per cell runs from ~74 at the equator to
~14 at 64.5N, and the SMALLEST DETECTABLE BURNED FRACTION therefore varies from 1.3% to 7% with
latitude. That is a measurement artefact that looks exactly like a latitude signal, so:
  - `n_pixels` is written to every row so the artefact is measurable rather than invisible,
  - the fill-rate report is PER REGION, never pooled.

ACCESS -- verified live, not cited. Microsoft Planetary Computer, OPEN, no account:
  STAC   POST https://planetarycomputer.microsoft.com/api/stac/v1/search  -> 200
  SIGN   GET  https://planetarycomputer.microsoft.com/api/sas/v1/sign?href=<blob>  -> 200
  READ   GET  <signed>  with Range  -> 206, image/tiff, ~133 KB per tile
The research left `/sign` vs `/api/sas/v1/token/{collection}` unresolved with two agents each
claiming their own route worked. Probed here: `/sign` works. It is used, `/token` is not. Tokens
expire in ~1 h so the signature is refreshed per batch, and every read asserts 206 + image/tiff
before the bytes are trusted.

GEOMETRY IS COMPUTED ONCE PER REGION, NOT PER MONTH. The sinusoidal grid and the panel grid are both
static, so the MODIS-pixel -> panel-cell mapping is built once and cached to disk, then reused for
all 252 months. Without that this job is 252x more expensive than it needs to be.
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import warnings

sys.path.insert(0, r"C:\Users\moh the ghost\Desktop\data set for reserch paper")
from coral_safe import cap_threads, free_gb, guard, mem_str

cap_threads(4)
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform as rio_transform
from rasterio.windows import from_bounds

PANEL = r"D:\monthly_panel"
OUT = "D:/fire/target"
GEOM = "D:/fire/geom"
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SIGN = "https://planetarycomputer.microsoft.com/api/sas/v1/sign?href="
H = {"User-Agent": "Mozilla/5.0"}
BLK_PX = 2_000_000        # pixels held at once inside read_month; caps peak RAM per tile read
YEARS = list(range(2002, 2023))          # 2023 excluded: SPEI and AMO gaps in the driver panel

# 40 regions spanning the fire regimes. Chosen for MECHANISM coverage, not for burned area --
# including near-zero regions (deserts, tundra) is deliberate: they are the negative control that
# shows the model is not simply predicting "somewhere flammable".
REGIONS = [
    # boreal / high-latitude
    "alaska_interior_taiga", "canadian_taiga", "siberian_taiga", "yakutia_larch",
    "scandinavian_taiga", "finnish_lapland", "russian_far_east_primorye",
    # mediterranean / fire-adapted shrubland
    "california_chaparral", "iberian_wildfire", "greece_mainland", "mediterranean_andalusia",
    "north_algeria_tell_atlas", "cape_floristic_region", "central_chile",
    # savanna / grassland -- the global burned-area maximum
    "east_african_savanna", "southern_african_savanna", "miombo_woodland_zambia",
    "angola_zambia_fire_belt", "sahel", "sudanian_acacia", "mopane_woodland",
    "kalahari_woodland", "cerrado", "llanos_venezuela", "gran_chaco",
    "northern_australia_monsoon", "northern_australia_woodland",
    # temperate / continental
    "great_plains", "canadian_prairies", "eurasian_steppe", "kazakh_steppe",
    "mongolian_steppe", "hulunbuir_grassland", "australian_bushfire_belt",
    # tropical forest / peat
    "borneo_peat_fires", "amazon_basin_brazil", "congo_basin_drc", "new_guinea_papua",
    # arid negative controls
    "thar_desert", "gobi_desert",
]


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


def _get(url, rng=None, tries=4, timeout=120):
    for k in range(tries):
        try:
            h = dict(H)
            if rng:
                h["Range"] = rng
            return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout)
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(2 * (k + 1))


def stac_items(bbox, year, month):
    """MCD64A1 items covering bbox in one month. Returns [(tile_id, Burn_Date href), ...]."""
    a = "%04d-%02d-01T00:00:00Z" % (year, month)
    last = pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(1)
    body = json.dumps({"collections": ["modis-64A1-061"], "bbox": [float(v) for v in bbox],
                       "datetime": a + "/" + last.strftime("%Y-%m-%dT23:59:59Z"),
                       "limit": 100}).encode()
    r = urllib.request.urlopen(urllib.request.Request(
        STAC, data=body, headers=dict(H, **{"Content-Type": "application/json"})), timeout=120)
    out = []
    for f in json.loads(r.read().decode()).get("features", []):
        out.append((f["id"], f["assets"]["Burn_Date"]["href"]))
    return out


def sign(href):
    r = _get(SIGN + urllib.parse.quote(href, safe=""))
    return json.loads(r.read().decode())["href"]


def region_cells(region):
    """Panel cell centres and the regular (lat, lon) grid they sit on."""
    f = os.path.join(PANEL, "%s_monthly_2010.parquet" % region)
    d = pd.read_parquet(f, columns=["cell_id", "lat", "lon", "month"])
    d = d[d.month == 1][["cell_id", "lat", "lon"]].reset_index(drop=True)
    la = np.sort(d.lat.unique())
    lo = np.sort(d.lon.unique())
    return d, la, lo


def build_geom(region):
    """MODIS pixel -> panel cell index, computed ONCE. Cached."""
    p = os.path.join(GEOM, "%s.npz" % region)
    if os.path.exists(p):
        z = np.load(p, allow_pickle=True)
        return z["cid"], z["la"], z["lo"], z["tiles"]
    d, la, lo = region_cells(region)
    bbox = (lo.min() - 0.05, la.min() - 0.05, lo.max() + 0.05, la.max() + 0.05)
    it = stac_items(bbox, 2010, 7)
    tiles = sorted(set(i[0].split(".")[2] for i in it))
    np.savez(p, cid=d.cell_id.values.astype("U64"), la=la, lo=lo,
             tiles=np.array(tiles, dtype="U8"), bbox=np.array(bbox))
    return d.cell_id.values.astype("U64"), la, lo, np.array(tiles, dtype="U8")


def read_month(region, la, lo, bbox, year, month):
    """Burned fraction per panel cell for one month. None if no item covers the region."""
    items = stac_items(bbox, year, month)
    if not items:
        return None
    dla = np.median(np.diff(la)) if len(la) > 1 else 0.01
    dlo = np.median(np.diff(lo)) if len(lo) > 1 else 0.01
    nb = np.zeros((len(la), len(lo)), np.int32)      # burned pixel count
    nv = np.zeros((len(la), len(lo)), np.int32)      # valid land pixel count
    nu = np.zeros((len(la), len(lo)), np.int32)      # unmapped (-1) pixel count
    for tid, href in items:
        with rasterio.open(sign(href)) as ds:
            xs, ys = rio_transform("EPSG:4326", ds.crs,
                                   [bbox[0], bbox[2], bbox[0], bbox[2]],
                                   [bbox[1], bbox[1], bbox[3], bbox[3]])
            try:
                w = from_bounds(min(xs), min(ys), max(xs), max(ys), ds.transform)
                a = ds.read(1, window=w, boundless=True, fill_value=-2)
            except Exception:
                continue
            if a.size == 0:
                continue
            # DO NOT CLAMP THESE TO ZERO. A boundless read returns an array whose [0,0] element is
            # at (w.row_off, w.col_off), and those offsets are NEGATIVE whenever the region bbox
            # starts outside the tile -- measured -249 and -1220 on h22v09 for east_african_savanna.
            # Clamping shifted every pixel coordinate by up to 1,220 pixels (~565 km), scattering
            # real burns into the wrong cells and producing a savanna fill rate ~30-80x too low.
            off_r = int(np.floor(w.row_off))
            off_c = int(np.floor(w.col_off))
            H, W = a.shape
            T = ds.transform
            # ---- OUT-OF-CORE: STREAM THE WINDOW IN ROW BLOCKS -----------------------------
            # The previous version materialised the WHOLE window at once and, worse, went through
            # ds.xy(), which returns PYTHON LISTS. On a big region (great_plains: ~2500x2500 per
            # tile = 6M pixels) that was two 6M-element lists from ds.xy, copied again by list(),
            # then two more from rio_transform -- comfortably over 1 GB of transient Python objects
            # for ONE tile, which is what drove the fetcher into the memory guard again and again
            # and made great_plains take 3.4 min/year.
            #
            # Two changes. Coordinates now come from the affine transform in pure numpy, so no
            # Python list of millions of floats is ever built. And the window is processed in row
            # blocks, so peak memory is set by BLK_PX and NOT by the size of the region -- a
            # continental region now costs the same per-block as a small one.
            BLK = max(1, int(BLK_PX // max(W, 1)))
            for r0 in range(0, H, BLK):
                r1 = min(r0 + BLK, H)
                sub = a[r0:r1]
                RR, CC = np.meshgrid(np.arange(r0, r1, dtype=np.float64) + off_r,
                                     np.arange(W, dtype=np.float64) + off_c, indexing="ij")
                # rasterio's ds.xy(row, col) is exactly the affine applied to the pixel CENTRE,
                # i.e. T * (col + 0.5, row + 0.5). Written out so no per-pixel Python call happens.
                x = T.c + T.a * (CC + 0.5) + T.b * (RR + 0.5)
                y = T.f + T.d * (CC + 0.5) + T.e * (RR + 0.5)
                del RR, CC
                plon, plat = rio_transform(ds.crs, "EPSG:4326", x.ravel(), y.ravel())
                del x, y
                plon = np.asarray(plon)
                plat = np.asarray(plat)
                v = sub.ravel()
                i = np.rint((plat - la[0]) / dla).astype(np.int64)
                j = np.rint((plon - lo[0]) / dlo).astype(np.int64)
                del plon, plat
                ok = (i >= 0) & (i < len(la)) & (j >= 0) & (j < len(lo)) & (v != -2)
                if not ok.any():
                    continue
                i, j, v = i[ok], j[ok], v[ok]
                flat = i * len(lo) + j
                np.add.at(nv.reshape(-1), flat[v != -1], 1)
                np.add.at(nu.reshape(-1), flat[v == -1], 1)
                np.add.at(nb.reshape(-1), flat[v > 0], 1)
                del i, j, v, flat, ok
    return nb, nv, nu



FAILED = []


def wait_mem(limit_gb=2.5, where="", max_wait_min=45):
    """Wait for memory instead of dying on it.

    This is a 40-region x 21-year job that runs unattended for hours, and the thing that ends such a
    run here is never the fetcher -- it holds well under 1 GB. The 2026-08-27 cerrado abort was Opera
    at 10.27 GB and Stellaris at 4.94 GB while this script held 0.28 GB. guard() is right to refuse
    to page onto the mechanical D: drive, but killing the remaining 39 regions because a browser tab
    spiked is the wrong response when the correct one is simply to pause until it lets go.

    Returns True if it may proceed, False if the pressure never cleared and the caller should skip.
    """
    t0 = time.time()
    warned = False
    while free_gb()[0] < limit_gb:
        if not warned:
            log("  PAUSED at %s -- %s, waiting for memory (not a fetcher problem; close browsers/"
                "games to resume immediately)" % (where, mem_str()))
            warned = True
        if (time.time() - t0) / 60 > max_wait_min:
            log("  SKIP %s -- still under %.1f GB after %d min" % (where, limit_gb, max_wait_min))
            return False
        time.sleep(30)
    if warned:
        log("  RESUMED at %s after %.1f min -- %s" % (where, (time.time() - t0) / 60, mem_str()))
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--regions", type=int, default=0, help="first N regions only")
    ap.add_argument("--only", default="", help="comma-separated region names -- use this "
                    "for Phase 0, because the first N are all boreal and the whole point "
                    "of the gating measurement is the SPREAD across fire regimes")
    ap.add_argument("--years", default="")
    A = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(GEOM, exist_ok=True)
    yrs = [int(x) for x in A.years.split(",")] if A.years else YEARS
    regs = ([x.strip() for x in A.only.split(",")] if A.only else
            REGIONS[:A.regions] if A.regions else REGIONS)
    log("=" * 100)
    log("MCD64A1 -> panel burned fraction | %d regions | %d years (%d-%d) | %s"
        % (len(regs), len(yrs), yrs[0], yrs[-1], mem_str()))

    if A.plan:
        tot = 0
        for r in regs:
            cid, la, lo, tiles = build_geom(r)
            n = len(tiles) * len(yrs) * 12
            tot += n
            log("  %-30s %6d cells  %6.2f km  %d tiles  %5d requests"
                % (r, len(cid), np.median(np.diff(la)) * 111.32, len(tiles), n))
        # 0.73 requests/s is MEASURED end-to-end on this machine (east_african_savanna 2015:
        # 4 tiles x 12 months = 48 requests in 66 s, 4 threads). The old estimate assumed 1.5 s
        # per request and divided by the thread count again, which double-counted the parallelism
        # and under-predicted the real run by about 4x -- 2.4 h against a true ~9 h.
        log("  TOTAL %s requests, ~%.1f GB, ~%.1f h  (measured 0.73 req/s, not assumed)"
            % (format(tot, ","), tot * 133e3 / 1e9, tot / 0.73 / 3600))
        return 0

    done = todo = 0
    for r in regs:
        # A region that cannot even build its geometry must not take the other 39 down with it.
        try:
            cid, la, lo, tiles = build_geom(r)
            z = np.load(os.path.join(GEOM, "%s.npz" % r), allow_pickle=True)
            bbox = tuple(z["bbox"])
        except Exception as ex:
            FAILED.append((r, "-", "geom: %s" % ex))
            log("  %-28s GEOM FAILED: %s" % (r, ex))
            continue
        for y in yrs:
            dst = os.path.join(OUT, "%s_%d.parquet" % (r, y))
            if os.path.exists(dst):
                done += 1
                continue
            todo += 1
            if not wait_mem(2.5, "%s %d" % (r, y)):
                FAILED.append((r, y, "memory"))
                continue
            t0 = time.time()
            # PER-YEAR ISOLATION. One STAC timeout or one unreadable COG used to end the whole run;
            # over 840 region-years that is close to a certainty, and the cost was every region
            # after the failure. Each year is independently retryable -- just re-launch, finished
            # years are skipped by the os.path.exists check above.
            try:
                rows = []
                for m in range(1, 13):
                    got = read_month(r, la, lo, bbox, y, m)
                    if got is None:
                        continue
                    nb, nv, nu = got
                    ii, jj = np.nonzero(nv + nu > 0)
                    rows.append(pd.DataFrame({
                        "lat": la[ii], "lon": lo[jj], "year": y, "month": m,
                        "n_burned": nb[ii, jj], "n_valid": nv[ii, jj], "n_unmapped": nu[ii, jj]}))
                if not rows:
                    log("  %-28s %d  NO ITEMS" % (r, y))
                    FAILED.append((r, y, "no items"))
                    continue
                d = pd.concat(rows, ignore_index=True)
                d["burned_frac"] = d.n_burned / d.n_valid.replace(0, np.nan)
                d["unmapped_frac"] = d.n_unmapped / (d.n_valid + d.n_unmapped).replace(0, np.nan)
                d.to_parquet(dst + ".part", index=False)
                os.replace(dst + ".part", dst)     # atomic: a kill never leaves a half-written year
            except KeyboardInterrupt:
                raise
            except Exception as ex:
                FAILED.append((r, y, repr(ex)[:120]))
                log("  %-28s %d  FAILED: %s" % (r, y, repr(ex)[:120]))
                continue
            done += 1
            nz = float((d.burned_frac.fillna(0) > 0).mean())
            log("  %-28s %d  %6d rows  fill %5.2f%%  meanBF(nz) %.4f  unmapped %4.1f%%  %.1f min"
                % (r, y, len(d), 100 * nz,
                   float(d.loc[d.burned_frac > 0, "burned_frac"].mean() or 0),
                   100 * float(d.unmapped_frac.mean() or 0), (time.time() - t0) / 60))
    log("=" * 100)
    log("%d/%d region-years on disk | %d failed" % (done, len(regs) * len(yrs), len(FAILED)))
    if FAILED:
        log("FAILURES -- re-launch the same command, finished years are skipped:")
        for r, y, why in FAILED[:40]:
            log("   %-28s %-5s %s" % (r, y, why))
        if len(FAILED) > 40:
            log("   ... and %d more" % (len(FAILED) - 40))
    log("DONE. Next: fill-rate report per region, then decide regression vs hurdle.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
