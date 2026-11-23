"""Defo VT0007 prep: forest-edge distance maps on the Hansen 30 m tiles, reduced to small count tables (staged).

SPEC_HUMAN.txt section 3 and 8 (O10, O11) (Builder B). OWNER COMMAND ONLY on the real tiles (hours, ~2 GB RAM per
worker; never run by a builder while another heavy job runs). Builders run it on toy rasters only.

What one "map pass" does (one region x one map year T; VT0007 5.3.1 with the SPEC_HUMAN 3 choices):
  forest(T)   = treecover2000 >= 30 AND datamask == 1 (land) AND NOT (1 <= lossyear <= T - 2000).
  source(T)   = land pixels that are not forest(T) (water and no-data are never a source: Q15 "land only").
  distance    = Euclidean distance in metres from each forest(T) pixel centre to the nearest source pixel centre,
                scipy.ndimage.distance_transform_edt with anisotropic spacing (dy, dx) per block (dx = dy cos(latitude
                of the block centre); R-DEF:105-106), on the block plus a margin of at least d_max metres read from
                the whole mosaic of tiles (a margin in a tile we do not hold is counted and disclosed).
  counts      = per (cell, fine distance bin): forest(T) pixels; per (cell, fine bin, loss year y) for the asked loss
                years: forest(T) pixels whose lossyear is y (they feed the HRP loss frequencies when T = t - 11).
  parity      = per cell forest2000 pixels and per (cell, year <= ymax) loss pixels, compared with D:/defo_target
                cell by cell (stops on any mismatch; SPEC_HUMAN 3 "Parity check").
Distances are stored on a fixed fine LOG grid (n_bins bins from d_lo to d_max metres; one overflow bin beyond
d_max). The VT0007 classes (defo_vt0007.py) are unions of fine bins; the NRT is snapped up to a fine-bin edge
(about 2% resolution at the default 512 bins over 1 m..20 km; disclosed). A NRT beyond d_max refuses there.

Look-ahead guards (PLAN R8): every lossyear value above ymax - 2000 is set to 0 ("not yet lost") before anything
reads it, and the pass asserts max(lossyear used) <= ymax - 2000. Stage "train": ymax = the run's fit-cut year
(lead 0); stage "test" (after the human lock only): ymax = last test issue year - 1. The gain layer is never read.
Pixel -> cell: the exact rule of defo_ingest.py:100-200 (searchsorted over midpoint edges of the region's own sorted
cell centres, per tile, half a cell of padding), so parity with D:/defo_target holds by construction.

Divisions (d4_processing_rules.md): each cell goes to the GADM 3.6 level-2 unit its footprint overlaps most; else the
nearest unit within half a cell; else "none". A country file without level 2 uses level 1 (IRL, HKG; data-driven).

Entry point for the tool: run_stage(ctx, rival, stage, workers) (a `prep` hook in the cli; BUILD_NOTES request).
AdapterCtx calls used: ctx.run (cuts), ctx.keys("train"/"test"), ctx.product_files, ctx.open_product,
ctx.product_root, ctx.work_dir, ctx.write_bytes, ctx.log, and ctx.require_human_lock (stage test).
"""
# Provenance: defo_ingest.py:66-215 (tile names, tiles_for, edges, window and pixel->cell rule, missing granules),
# research_defo.md:64-106, SPEC_HUMAN.txt 3 and 8, D:/treeroute/human_tools/reports/d4_processing_rules.md.

import hashlib
import io
import json
import math
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

PREP_FORMAT = "human-defo-prep/1"
TC_THRESH = 30                   # Hansen forest convention (defo_ingest.py:57)
LOSS_BASE_YEAR = 2000            # lossyear value v = loss in year 2000 + v
DM_LAND = 1                      # datamask: 1 land, 2 water, 0 no data
EARTH_RADIUS_M = 6371008.8       # mean Earth radius (IUGG); metres per degree = pi R / 180
M_PER_DEG = math.pi * EARTH_RADIUS_M / 180.0
TILE_DEG = 10                    # Hansen granules are 10 x 10 degrees (defo_ingest.py:74-84)
LAYERS = ("treecover2000", "datamask", "lossyear")
NAME_RE = re.compile(r"^(?P<prefix>.+)_(?P<layer>treecover2000|datamask|lossyear|gain)_(?P<tile>\d{2}[NS]_\d{3}[EW])"
                     r"\.tif$")
NONE_DIVISION = "<none>"
DIVISION_FILE = "divisions.parquet"
MAP_FILE = "map_T%d__%s.npz"
META_FILE = "map_T%d__%s.json"
MANIFEST_FILE = "prep_manifest_%s.json"


class DefoPrepRefusal(RuntimeError):
    """A defo prep rule refused (fail loud)."""


def _refuse(message: str, fix: Optional[str] = None):
    raise DefoPrepRefusal("refused [defo prep]: " + message + ("" if not fix else "  FIX: " + fix))


def opt(rival: Mapping[str, Any], name: str, default: Any = None) -> Any:
    opts = rival.get("options") or {}
    if name in opts:
        return opts[name]
    if default is None:
        _refuse("rival %s has no registry option %r" % (rival.get("id"), name))
    return default


def require_lock(ctx: Any, what: str) -> None:
    """Stage test needs the human lock: ctx.require_human_lock() when the tool offers it, else the lock token the tool
    hands the AdapterCtx (rivals_human/index.py:189-192, :476-479; lockfile.require_token)."""
    fn = getattr(ctx, "require_human_lock", None)
    if fn is not None:
        fn()
        return
    from rivals_human import lockfile
    lockfile.require_token(getattr(ctx, "_token", None), ctx.run.fingerprint, what)


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------------------------------------------- fine bins
class FineBins(object):
    """n_bins log-spaced distance bins between d_lo and d_max metres; bin n_bins = overflow (> d_max or no source).
    Distances below d_lo fall in bin 0."""

    def __init__(self, d_lo: float, d_max: float, n_bins: int):
        if not (0 < d_lo < d_max) or int(n_bins) < 2:
            _refuse("bad fine bins d_lo %r d_max %r n_bins %r" % (d_lo, d_max, n_bins))
        self.d_lo, self.d_max, self.n = float(d_lo), float(d_max), int(n_bins)
        self.edges = self.d_lo * (self.d_max / self.d_lo) ** (np.arange(self.n + 1) / float(self.n))
        self.edges[-1] = self.d_max

    def bin_of(self, d: np.ndarray) -> np.ndarray:
        d = np.asarray(d, dtype="float64")
        b = np.searchsorted(self.edges, d, side="right") - 1
        b = np.clip(b, 0, self.n - 1)
        b[~(d <= self.d_max)] = self.n
        return b.astype("int64")

    def upper(self) -> np.ndarray:
        """Upper edge of every bin (overflow: +inf)."""
        return np.append(self.edges[1:], np.inf)

    def as_dict(self) -> Dict[str, Any]:
        return {"d_lo": self.d_lo, "d_max": self.d_max, "n_bins": self.n}


# ---------------------------------------------------------------------------------------------------- tiles (defo_ingest)
def tile_name(lat: int, lon: int) -> str:
    """defo_ingest.py:66-69."""
    ns = "%02dN" % lat if lat >= 0 else "%02dS" % abs(lat)
    ew = "%03dE" % lon if lon >= 0 else "%03dW" % abs(lon)
    return "%s_%s" % (ns, ew)


def tiles_for(lon0: float, lon1: float, lat0: float, lat1: float) -> List[Tuple[int, int]]:
    """defo_ingest.py:72-81: the 10-degree granules (top-left lat, lon) a lon/lat box touches."""
    out = []
    for tlat in range(80, -60, -10):
        if tlat <= lat0 or tlat - 10 >= lat1:
            continue
        for tlon in range(-180, 180, 10):
            if tlon >= lon1 or tlon + 10 <= lon0:
                continue
            out.append((tlat, tlon))
    return out


def mid_edges(vals: Any) -> np.ndarray:
    """defo_ingest.py:84-88: midpoint bin edges of sorted cell centres."""
    v = np.asarray(vals, np.float64)
    return (v[:-1] + v[1:]) / 2.0


def index_tiles(names: Iterable[str]) -> Tuple[str, Dict[str, Dict[str, str]]]:
    """(prefix, {layer: {tile: file name}}) from the Hansen product's file list. One prefix only."""
    prefixes, out = set(), {k: {} for k in LAYERS}
    for n in names:
        m = NAME_RE.match(os.path.basename(n))
        if not m:
            continue
        prefixes.add(m.group("prefix"))
        if m.group("layer") in out:
            out[m.group("layer")][m.group("tile")] = n
    if len(prefixes) != 1:
        _refuse("the Hansen product holds %d file prefixes %s; one version only" % (len(prefixes), sorted(prefixes)))
    return prefixes.pop(), out


def region_grid(cell_id: Sequence[str], lon: Any, lat: Any) -> Dict[str, Any]:
    """The region's cell grid exactly as defo_ingest.py:103-131 (ordinal = position in the given order)."""
    lon = np.asarray(lon, np.float64)
    lat = np.asarray(lat, np.float64)
    if not (np.isfinite(lon).all() and np.isfinite(lat).all()):
        _refuse("a cell has no finite centre")
    ulon, ulat = np.sort(np.unique(lon)), np.sort(np.unique(lat))
    ex, ey = mid_edges(ulon), mid_edges(ulat)
    ii, jj = np.searchsorted(ex, lon), np.searchsorted(ey, lat)
    grid = np.full((len(ulat), len(ulon)), -1, np.int32)
    if (grid[jj, ii] != -1).any() or len(set(zip(ii.tolist(), jj.tolist()))) != len(lon):
        _refuse("two cells share one grid position")
    grid[jj, ii] = np.arange(len(lon), dtype=np.int32)
    # The region window edges exactly as defo_ingest.py computed them: it read the panel's float32 centres (pandas
    # keeps float32), so hx = median of float32 differences / 2 and lon0 = ulon.min() - hx are float32 values (NumPy 2
    # casts the Python float to float32). With float64 edges, 2 of 168 region edges fell one 30 m pixel column off the
    # target (2026-10-24: the west edges of japan_central_honshu and new_guinea_papua failed PARITY; the other 166
    # edges are identical either way). The midpoint edges ex / ey stay float64 (defo_ingest.py edges() casts too).
    u32, v32 = ulon.astype(np.float32), ulat.astype(np.float32)
    if not ((u32.astype(np.float64) == ulon).all() and (v32.astype(np.float64) == ulat).all()):
        _refuse("cell centres are not float32 values; the target's float32 window rule cannot be replicated")
    hx = float(np.median(np.diff(u32))) / 2 if len(ulon) > 1 else 0.02
    hy = float(np.median(np.diff(v32))) / 2 if len(ulat) > 1 else 0.02
    f32 = np.float32
    return {"cell_id": np.asarray(cell_id).astype(str), "ex": ex, "ey": ey, "grid": grid, "ncell": len(lon),
            "hx": hx, "hy": hy, "lon0": float(f32(u32.min()) - f32(hx)), "lon1": float(f32(u32.max()) + f32(hx)),
            "lat0": float(f32(v32.min()) - f32(hy)), "lat1": float(f32(v32.max()) + f32(hy))}


def lossyear_guard(ly: np.ndarray, ymax: int) -> np.ndarray:
    """Every lossyear above ymax - 2000 becomes 0 ('not yet lost'); asserted (PLAN R8)."""
    cap = int(ymax) - LOSS_BASE_YEAR
    out = np.where(ly <= cap, ly, 0).astype(np.uint8)
    if out.size and int(out.max()) > cap:
        _refuse("lossyear guard failed: %d > %d" % (int(out.max()), cap))
    return out


# ---------------------------------------------------------------------------------------------------- mosaic reader
class Mosaic(object):
    """Reads a global-pixel window (rows from 90N, cols from 180W, all tiles share the pixel size) across tiles.
    A tile without treecover2000 or datamask is missing: treecover 0, datamask 0 (no data, never a source), counted.
    A held tile without lossyear reads lossyear 0 (defo_ingest.py:149-155: Hansen omits it where there is no loss)."""

    def __init__(self, paths: Mapping[str, Mapping[str, str]], px: float):
        import rasterio
        self._rio = rasterio
        self.paths = paths
        self.px = float(px)
        self.open: Dict[Tuple[str, str], Any] = {}
        self.missing_px = 0

    def _ds(self, layer: str, tile: str):
        k = (layer, tile)
        if k not in self.open:
            self.open[k] = self._rio.open(self.paths[layer][tile])
        return self.open[k]

    def close(self):
        for d in self.open.values():
            d.close()
        self.open = {}

    def offset(self, tile: str) -> Tuple[int, int, int, int]:
        """(row0, col0, height, width) of a held tile in global pixels; the transform is checked."""
        d = self._ds("treecover2000", tile)
        T = d.transform
        if abs(T.a - self.px) > 1e-12 or abs(-T.e - self.px) > 1e-12:
            _refuse("tile %s pixel size %r differs from %r" % (tile, (T.a, T.e), self.px))
        r0, c0 = (90.0 - T.f) / self.px, (T.c + 180.0) / self.px
        if abs(r0 - round(r0)) > 1e-6 or abs(c0 - round(c0)) > 1e-6:
            _refuse("tile %s is not on the global pixel grid" % tile)
        return int(round(r0)), int(round(c0)), d.height, d.width

    def read(self, gr0: int, gr1: int, gc0: int, gc1: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, int]:
        from rasterio.windows import Window
        h, w = gr1 - gr0, gc1 - gc0
        tc = np.zeros((h, w), np.uint8)
        dm = np.zeros((h, w), np.uint8)
        ly = np.zeros((h, w), np.uint8)
        filled = np.zeros((h, w), bool)
        lat_top, lat_bot = 90.0 - gr0 * self.px, 90.0 - gr1 * self.px
        lon_l, lon_r = -180.0 + gc0 * self.px, -180.0 + gc1 * self.px
        for (tlat, tlon) in tiles_for(lon_l, lon_r, lat_bot, lat_top):
            tn = tile_name(tlat, tlon)
            if tn not in self.paths["treecover2000"] or tn not in self.paths["datamask"]:
                continue
            r0, c0, th, tw = self.offset(tn)
            a0, a1 = max(gr0, r0), min(gr1, r0 + th)
            b0, b1 = max(gc0, c0), min(gc1, c0 + tw)
            if a1 <= a0 or b1 <= b0:
                continue
            win = Window(b0 - c0, a0 - r0, b1 - b0, a1 - a0)
            sl = (slice(a0 - gr0, a1 - gr0), slice(b0 - gc0, b1 - gc0))
            tc[sl] = self._ds("treecover2000", tn).read(1, window=win)
            dm[sl] = self._ds("datamask", tn).read(1, window=win)
            if tn in self.paths["lossyear"]:
                ly[sl] = self._ds("lossyear", tn).read(1, window=win)
            filled[sl] = True
        miss = int((~filled).sum())
        self.missing_px += miss
        return tc, dm, ly, miss


# ---------------------------------------------------------------------------------------------------- one map pass
def _reduce(keys: List[np.ndarray], counts: List[np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
    if not keys:
        return np.zeros(0, np.int64), np.zeros(0, np.int64)
    k = np.concatenate(keys)
    c = np.concatenate(counts)
    u, inv = np.unique(k, return_inverse=True)
    return u, np.bincount(inv.ravel(), weights=c, minlength=len(u)).astype(np.int64)


def map_pass(task: Mapping[str, Any]) -> Dict[str, Any]:
    """One region x one map year T (pure function; worker-safe). task keys: region, cell_id, lon, lat, paths
    ({layer: {tile: path}}), px, T, loss_years (contiguous ascending or empty), ymax, bins (dict), block, tc_thresh."""
    from scipy.ndimage import distance_transform_edt
    T, ymax = int(task["T"]), int(task["ymax"])
    years = [int(y) for y in task["loss_years"]]
    if T > ymax or any(y <= T or y > ymax for y in years):
        _refuse("map T%d: loss years %s must lie in (T, ymax=%d]" % (T, years, ymax))
    if years and years != list(range(years[0], years[-1] + 1)):
        _refuse("map T%d: loss years must be contiguous" % T)
    bins = FineBins(**task["bins"])
    NB1 = bins.n + 1
    g = region_grid(task["cell_id"], task["lon"], task["lat"])
    ncell, ex, ey, grid = g["ncell"], g["ex"], g["ey"], g["grid"]
    px, block, thr = float(task["px"]), int(task["block"]), int(task["tc_thresh"])
    NY = ymax - LOSS_BASE_YEAR
    y0 = years[0] if years else 0
    NYL = len(years)
    mos = Mosaic(task["paths"], px)
    parity_forest = np.zeros(ncell, np.int64)
    parity_loss = np.zeros(ncell * max(NY, 1), np.int64)
    fk, fc, lk, lc = [], [], [], []
    cnt = {"core_px": 0, "forest_T_px": 0, "overflow_px": 0, "blocks": 0, "blocks_no_source": 0,
           "missing_granules": [], "window_missing_px": 0, "max_lossyear_used": 0, "loss_px_counted": 0}
    try:
        for (tlat, tlon) in tiles_for(g["lon0"], g["lon1"], g["lat0"], g["lat1"]):
            tn = tile_name(tlat, tlon)
            if tn not in mos.paths["treecover2000"] or tn not in mos.paths["datamask"]:
                cnt["missing_granules"].append(tn)          # as defo_ingest.py:144-147: skipped, region incomplete
                continue
            ds = mos._ds("treecover2000", tn)
            Tf = ds.transform
            R0, C0, th, tw = mos.offset(tn)
            # pixel window of the region box inside this granule: defo_ingest.py:160-172 verbatim (on px)
            c0 = int(np.floor((g["lon0"] - Tf.c) / px))
            c1 = int(np.ceil((g["lon1"] - Tf.c) / px))
            r0 = int(np.floor((Tf.f - g["lat1"]) / px))
            r1 = int(np.ceil((Tf.f - g["lat0"]) / px))
            c0, c1 = max(0, min(c0, tw)), max(0, min(c1, tw))
            r0, r1 = max(0, min(r0, th)), max(0, min(r1, th))
            if c1 <= c0 or r1 <= r0:
                continue
            plon = Tf.c + (np.arange(c0, c1) + 0.5) * px
            pi_all = np.searchsorted(ex, plon).astype(np.int32)
            for rs in range(r0, r1, block):
                re_ = min(rs + block, r1)
                plat = Tf.f - (np.arange(rs, re_) + 0.5) * px
                pj = np.searchsorted(ey, plat).astype(np.int32)
                lat_c = Tf.f - ((rs + re_) / 2.0) * px
                dy = px * M_PER_DEG
                dx = dy * math.cos(math.radians(lat_c))
                mr = int(math.ceil(bins.d_max / dy)) + 1
                mc = int(math.ceil(bins.d_max / dx)) + 1
                for cs in range(c0, c1, block):
                    ce = min(cs + block, c1)
                    cell = grid[pj[:, None], pi_all[None, cs - c0:ce - c0]]
                    ok = cell >= 0
                    if not ok.any():
                        continue
                    cnt["blocks"] += 1
                    gr0, gr1 = R0 + rs - mr, R0 + re_ + mr
                    gc0, gc1 = C0 + cs - mc, C0 + ce + mc
                    tc, dm, ly_raw, miss = mos.read(gr0, gr1, gc0, gc1)
                    cnt["window_missing_px"] += miss
                    ly = lossyear_guard(ly_raw, ymax)
                    del ly_raw
                    f2000 = (dm == DM_LAND) & (tc >= thr)
                    lost = (ly >= 1) & (ly <= T - LOSS_BASE_YEAR)
                    forest_T = f2000 & ~lost
                    source = (dm == DM_LAND) & ~forest_T
                    core = (slice(mr, mr + (re_ - rs)), slice(mc, mc + (ce - cs)))
                    if source.any():
                        dist = distance_transform_edt(~source, sampling=(dy, dx))[core]
                    else:
                        cnt["blocks_no_source"] += 1
                        dist = np.full((re_ - rs, ce - cs), np.inf)
                    cid = cell[ok].astype(np.int64)
                    f2 = f2000[core][ok]
                    fT = forest_T[core][ok]
                    lyc = ly[core][ok].astype(np.int64)
                    dc = dist[ok]
                    del tc, dm, ly, f2000, lost, forest_T, source, dist
                    cnt["core_px"] += int(ok.sum())
                    if lyc.size:
                        cnt["max_lossyear_used"] = max(cnt["max_lossyear_used"], int(lyc.max()))
                    parity_forest += np.bincount(cid[f2], minlength=ncell)
                    hit = f2 & (lyc > 0)
                    if NY > 0 and hit.any():
                        parity_loss += np.bincount(cid[hit] * NY + (lyc[hit] - 1), minlength=ncell * NY)
                    if fT.any():
                        b = bins.bin_of(dc[fT])
                        cnt["forest_T_px"] += int(fT.sum())
                        cnt["overflow_px"] += int((b == bins.n).sum())
                        u, c = np.unique(cid[fT] * NB1 + b, return_counts=True)
                        fk.append(u)
                        fc.append(c.astype(np.int64))
                        if NYL:
                            yy = lyc[fT] + LOSS_BASE_YEAR
                            sel = (yy >= y0) & (yy <= years[-1])
                            if sel.any():
                                key = (cid[fT][sel] * NB1 + b[sel]) * NYL + (yy[sel] - y0)
                                u, c = np.unique(key, return_counts=True)
                                lk.append(u)
                                lc.append(c.astype(np.int64))
                                cnt["loss_px_counted"] += int(sel.sum())
    finally:
        mos.close()
    if cnt["max_lossyear_used"] > ymax - LOSS_BASE_YEAR:
        _refuse("map T%d read lossyear %d past ymax %d" % (T, cnt["max_lossyear_used"], ymax))
    fu, fn = _reduce(fk, fc)
    lu, ln = _reduce(lk, lc)
    if NYL:
        l_year = (lu % NYL) + y0
        lcb = lu // NYL
    else:
        l_year = np.zeros(0, np.int64)
        lcb = np.zeros(0, np.int64)
    return {"region": task["region"], "T": T, "ymax": ymax, "loss_years": years, "bins": bins.as_dict(),
            "forest_cell": (fu // NB1).astype(np.int32), "forest_bin": (fu % NB1).astype(np.int16),
            "forest_n": fn, "loss_cell": (lcb // NB1).astype(np.int32), "loss_bin": (lcb % NB1).astype(np.int16),
            "loss_year": l_year.astype(np.int16), "loss_n": ln, "parity_forest": parity_forest,
            "parity_loss": parity_loss.reshape(ncell, max(NY, 1))[:, :NY], "counts": cnt}


# ---------------------------------------------------------------------------------------------------- stage plan
def stage_plan(t_years: Iterable[int], hrp: int, ymax: int) -> Dict[int, List[int]]:
    """{map year T: loss years to count} for issue years t: T1 = t - hrp - 1 counts loss years t - hrp .. t - 1;
    T3 = t - 1 needs forest counts only. Refuses a loss year past ymax or past t - 1."""
    need: Dict[int, set] = {}
    for t in sorted(set(int(x) for x in t_years)):
        T1, T3 = t - hrp - 1, t - 1
        hrp_years = list(range(t - hrp, t))
        if hrp_years[-1] > ymax or T3 > ymax:
            _refuse("issue year %d needs loss up to %d, past this stage's ymax %d" % (t, t - 1, ymax))
        need.setdefault(T3, set())
        need.setdefault(T1, set()).update(hrp_years)
    return {T: sorted(v) for T, v in sorted(need.items())}


def issue_years(rival: Mapping[str, Any], stage: str, fit_cut: int, test_last: Optional[int]) -> List[int]:
    """Covered issue years of a stage (+ the frozen forms' effective year f + 1 in stage train)."""
    t_min = int(opt(rival, "first_loss_year")) + int(opt(rival, "hrp_years"))
    if stage == "train":
        ys = list(range(t_min, int(fit_cut) + 1))
        ys += [int(f) + 1 for f in (opt(rival, "frozen_years", []) or [])]
        return sorted(set(ys))
    if test_last is None:
        _refuse("stage test needs the last test issue year")
    return list(range(max(t_min, int(fit_cut) + 1), int(test_last) + 1))


# ---------------------------------------------------------------------------------------------------- divisions
def assign_divisions(cell_id: Sequence[str], lon: Any, lat: Any, hx: float, hy: float,
                     zip_paths: Sequence[Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """d4_processing_rules.md rules 1-2: largest footprint overlap; else nearest unit within half a cell; else none.
    A country GeoPackage without a level-2 layer uses its level-1 layer (level noted per cell)."""
    import geopandas as gpd
    import pyogrio
    import shapely
    import zipfile
    lon = np.asarray(lon, np.float64)
    lat = np.asarray(lat, np.float64)
    boxes = shapely.box(lon - hx, lat - hy, lon + hx, lat + hy)
    half = max(hx, hy)
    bb = (float(lon.min() - hx - half), float(lat.min() - hy - half), float(lon.max() + hx + half),
          float(lat.max() + hy + half))
    parts, levels = [], {}
    for zp in zip_paths:
        zp = str(zp)
        with zipfile.ZipFile(zp) as z:
            inner = [n for n in z.namelist() if n.lower().endswith(".gpkg")]
        if len(inner) != 1:
            _refuse("%s holds %d GeoPackages" % (zp, len(inner)))
        vsi = "/vsizip/%s/%s" % (zp.replace("\\", "/"), inner[0])
        layers = [l[0] for l in pyogrio.list_layers(vsi)]
        lv = {}
        for l in layers:
            m = re.match(r"^gadm36_([A-Z]{3})_(\d)$", l)
            if m:
                lv[int(m.group(2))] = (m.group(1), l)
        level = 2 if 2 in lv else (1 if 1 in lv else None)
        if level is None:
            continue
        iso, layer = lv[level]
        gdf = gpd.read_file(vsi, layer=layer, bbox=bb, engine="pyogrio")
        if not len(gdf):
            continue
        gid = "GID_%d" % level
        if gid not in gdf.columns:
            _refuse("%s layer %s has no %s" % (zp, layer, gid))
        levels[iso] = level
        parts.append(pd.DataFrame({"division": gdf[gid].astype(str).values, "level": level, "iso": iso,
                                   "geometry": shapely.make_valid(np.asarray(gdf.geometry.values))}))
    n = len(boxes)
    div = np.array([NONE_DIVISION] * n, dtype=object)
    lvl = np.zeros(n, np.int8)
    step = np.array(["none"] * n, dtype=object)
    if parts:
        P = pd.concat(parts, ignore_index=True)
        P = P.sort_values(["division"], kind="mergesort").reset_index(drop=True)
        geoms = np.asarray(P["geometry"].values)
        tree = shapely.STRtree(geoms)
        bi, pj = tree.query(boxes, predicate="intersects")
        if len(bi):
            area = shapely.area(shapely.intersection(boxes[bi], geoms[pj]))
            df = pd.DataFrame({"b": bi, "p": pj, "a": area})
            df = df[df["a"] > 0].sort_values(["b", "a", "p"], ascending=[True, False, True], kind="mergesort")
            first = df.drop_duplicates("b", keep="first")
            div[first["b"].values] = P["division"].values[first["p"].values]
            lvl[first["b"].values] = P["level"].values[first["p"].values]
            step[first["b"].values] = "overlap"
        rest = np.where(step == "none")[0]
        if len(rest):
            ri, rp = tree.query_nearest(boxes[rest], max_distance=half, return_distance=False, all_matches=True)
            if len(ri):
                d = shapely.distance(boxes[rest][ri], geoms[rp])
                df = pd.DataFrame({"b": rest[ri], "p": rp, "d": d}).sort_values(["b", "d", "p"], kind="mergesort")
                first = df.drop_duplicates("b", keep="first")
                div[first["b"].values] = P["division"].values[first["p"].values]
                lvl[first["b"].values] = P["level"].values[first["p"].values]
                step[first["b"].values] = "nearest"
    out = pd.DataFrame({"cell_id": np.asarray(cell_id).astype(str), "division": div.astype(str), "level": lvl,
                        "step": step.astype(str)})
    rep = {"cells": n, "overlap": int((step == "overlap").sum()), "nearest": int((step == "nearest").sum()),
           "none": int((step == "none").sum()), "level_by_country": levels,
           "level1_cells": int((lvl == 1).sum())}
    return out, rep


# ---------------------------------------------------------------------------------------------------- npz io
def result_bytes(res: Mapping[str, Any]) -> Tuple[bytes, Dict[str, Any]]:
    buf = io.BytesIO()
    np.savez(buf, **{k: np.asarray(res[k]) for k in ("forest_cell", "forest_bin", "forest_n", "loss_cell",
                                                     "loss_bin", "loss_year", "loss_n", "parity_forest",
                                                     "parity_loss")})
    meta = {k: res[k] for k in ("region", "T", "ymax", "loss_years", "bins", "counts")}
    return buf.getvalue(), meta


def load_map(path: Any) -> Dict[str, np.ndarray]:
    with np.load(str(path), allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


# ---------------------------------------------------------------------------------------------------- parity
def parity_check(region: str, cell_id: np.ndarray, forest2000: np.ndarray, loss: np.ndarray, ymax: int,
                 target_path: Any) -> Dict[str, Any]:
    """Our per-cell forest2000 and loss_px (years 2001..ymax) must equal D:/defo_target cell by cell (labels of
    years <= ymax only are read: ymax is the stage's own bound)."""
    import pyarrow.parquet as pq
    t = pq.read_table(str(target_path), columns=["cell_id", "year", "loss_px", "forest2000_px"],
                      filters=[("year", "<=", int(ymax))]).to_pandas()
    if int(t["year"].max()) > ymax:
        _refuse("parity read a year past ymax")
    want_cells = set(t["cell_id"].astype(str))
    if want_cells != set(cell_id.tolist()):
        _refuse("%s: the target cells differ from the static cells (%d vs %d)" % (region, len(want_cells),
                                                                                   len(cell_id)))
    pos = pd.Series(np.arange(len(cell_id)), index=cell_id)
    ci = pos.loc[t["cell_id"].astype(str).values].values
    f_t = t["forest2000_px"].astype("int64").values
    if not (forest2000[ci] == f_t).all():
        k = int(np.argmax(forest2000[ci] != f_t))
        _refuse("PARITY %s: forest2000 of %s is %d here, %d in the target" % (region, t["cell_id"].iloc[k],
                                                                             forest2000[ci][k], f_t[k]))
    yrs = t["year"].astype("int64").values
    sel = yrs >= LOSS_BASE_YEAR + 1
    ours = loss[ci[sel], yrs[sel] - LOSS_BASE_YEAR - 1]
    theirs = t["loss_px"].astype("int64").values[sel]
    if not (ours == theirs).all():
        k = int(np.argmax(ours != theirs))
        _refuse("PARITY %s: loss_px of %s in %d is %d here, %d in the target"
                % (region, t["cell_id"].values[sel][k], yrs[sel][k], ours[k], theirs[k]))
    return {"region": region, "cells": int(len(cell_id)), "rows_compared": int(sel.sum()), "ymax": int(ymax)}


# ---------------------------------------------------------------------------------------------------- the stage
def _static_cells(ctx: Any, rival: Mapping[str, Any]) -> pd.DataFrame:
    import pyarrow.parquet as pq
    p = ctx.open_product(opt(rival, "static_product"), opt(rival, "static_file"))
    s = pq.read_table(str(p), columns=["cell_id", "region", "lat", "lon", "forest2000_px"]).to_pandas()
    if s["cell_id"].duplicated().any():
        _refuse("the static table holds a cell twice")
    return s


def prep_dir(ctx: Any, rival: Mapping[str, Any]) -> Path:
    """The prep folder shared by the VT0007 rivals: the work dir of the rival named by option prep_rival."""
    own = Path(ctx.work_dir())
    owner = str(opt(rival, "prep_rival"))
    return own if own.name == owner else own.parent / owner


def run_stage(ctx: Any, rival: Mapping[str, Any], stage: str, workers: int = 1,
              regions: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """Build every map of a stage for every region (resumable: a finished map with the same task hash is kept).
    Owner command on real tiles. stage 'test' needs the human lock."""
    if stage not in ("train", "test"):
        _refuse("stage must be train or test, not %r" % stage)
    run = ctx.run
    fit_cut = int(run.cuts[0]["fit_cut"])
    test_last = None
    if stage == "test":
        require_lock(ctx, "defo prep stage test")
        test_last = int(ctx.keys("test")["time"].max())
    ymax = fit_cut if stage == "train" else test_last - 1
    hrp = int(opt(rival, "hrp_years"))
    t_years = issue_years(rival, stage, fit_cut, test_last)
    plan = stage_plan(t_years, hrp, ymax)
    if stage == "train" and max(max(v) if v else T for T, v in plan.items()) > fit_cut:
        _refuse("stage train plans a loss year past the fit cut %d" % fit_cut)
    bins = FineBins(float(opt(rival, "d_lo_m")), float(opt(rival, "d_max_m")), int(opt(rival, "n_bins")))
    block = int(opt(rival, "block_px"))
    out = prep_dir(ctx, rival)
    if own_name(ctx) != str(opt(rival, "prep_rival")):
        _refuse("run the prep under rival %s (the prep owner), not %s" % (opt(rival, "prep_rival"), own_name(ctx)))

    static = _static_cells(ctx, rival)
    if regions is None:
        regions = sorted(ctx.keys(stage)["group"].astype(str).unique())
    hpid = opt(rival, "hansen_product")
    prefix, names = index_tiles(ctx.product_files(hpid))
    px = float(opt(rival, "pixel_deg"))
    margin_deg = bins.d_max / M_PER_DEG
    # earlier stage maps (test stage reuses train counts where they already hold everything a map needs)
    prev: Dict[int, set] = {}
    if stage == "test":
        man_p = out / (MANIFEST_FILE % "train")
        if not man_p.is_file():
            _refuse("stage test needs the finished stage train manifest %s" % man_p)
        with open(str(man_p), encoding="utf-8") as f:
            tm = json.load(f)
        prev = {int(T): set(v) for T, v in tm["plan"].items()}
        plan = {T: v for T, v in plan.items() if not (T in prev and set(v) <= prev[T])}
    tasks, rep_regions = [], {}
    for reg in regions:
        cells = static[static["region"].astype(str) == reg].reset_index(drop=True)
        if not len(cells):
            _refuse("region %s has no static cells" % reg)
        g = region_grid(cells["cell_id"].values, cells["lon"].values, cells["lat"].values)
        need = tiles_for(g["lon0"] - margin_deg / max(0.05, math.cos(math.radians(max(abs(g["lat0"]),
                                                                                      abs(g["lat1"]))))),
                         g["lon1"] + margin_deg / max(0.05, math.cos(math.radians(max(abs(g["lat0"]),
                                                                                      abs(g["lat1"]))))),
                         g["lat0"] - margin_deg, g["lat1"] + margin_deg)
        paths = {lay: {} for lay in LAYERS}
        for (tlat, tlon) in need:
            tn = tile_name(tlat, tlon)
            for lay in LAYERS:
                if tn in names[lay]:
                    paths[lay][tn] = str(ctx.open_product(hpid, names[lay][tn]))
        rdir = out / reg
        # divisions (label-free; once)
        dpath = rdir / DIVISION_FILE
        if not dpath.is_file():
            gpid = opt(rival, "gadm_product")
            zips = [ctx.open_product(gpid, n) for n in ctx.product_files(gpid) if n.lower().endswith(".zip")]
            dv, drep = assign_divisions(cells["cell_id"].values, cells["lon"].values, cells["lat"].values,
                                        g["hx"], g["hy"], zips)
            buf = io.BytesIO()
            dv.to_parquet(buf, index=False)
            ctx.write_bytes(dpath, buf.getvalue())
            ctx.write_bytes(rdir / "divisions.json", canonical(drep))
            ctx.log("defo prep %s divisions: overlap %d, nearest %d, none %d, level-1 cells %d"
                    % (reg, drep["overlap"], drep["nearest"], drep["none"], drep["level1_cells"]))
        rep_regions[reg] = {"cells": int(len(cells)), "tiles": sorted(paths["treecover2000"])}
        for T, years in plan.items():
            task = {"region": reg, "cell_id": cells["cell_id"].astype(str).values,
                    "lon": cells["lon"].values.astype("float64"), "lat": cells["lat"].values.astype("float64"),
                    "paths": paths, "px": px, "T": int(T), "loss_years": list(years), "ymax": int(ymax),
                    "bins": bins.as_dict(), "block": block, "tc_thresh": TC_THRESH}
            th = sha256_bytes(canonical({k: (v.tolist() if isinstance(v, np.ndarray) else v)
                                         for k, v in task.items() if k != "paths"}))
            mp, jp = rdir / (MAP_FILE % (T, stage)), rdir / (META_FILE % (T, stage))
            if jp.is_file():
                with open(str(jp), encoding="utf-8") as f:
                    old = json.load(f)
                if old.get("task_sha256") != th:
                    _refuse("%s exists with another task hash; move it aside to the build's _moved folder" % jp)
                continue
            tasks.append((task, th, mp, jp))
    ctx.log("defo prep stage %s: %d regions, %d map passes to run (ymax %d, plan %s)"
            % (stage, len(regions), len(tasks), ymax, {T: (v[0], v[-1]) if v else () for T, v in plan.items()}))

    def _write(res, th, mp, jp):
        data, meta = result_bytes(res)
        ctx.write_bytes(mp, data)
        meta.update({"format": PREP_FORMAT, "stage": stage, "task_sha256": th, "npz_sha256": sha256_bytes(data)})
        ctx.write_bytes(jp, canonical(meta))
        ctx.log("defo prep %s T%d: core px %d, forest px %d, overflow %d, missing granules %s, window missing px %d"
                % (res["region"], res["T"], res["counts"]["core_px"], res["counts"]["forest_T_px"],
                   res["counts"]["overflow_px"], res["counts"]["missing_granules"],
                   res["counts"]["window_missing_px"]))

    if int(workers) <= 1:
        for task, th, mp, jp in tasks:
            _write(map_pass(task), th, mp, jp)
    else:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=int(workers)) as ex:
            futs = {ex.submit(map_pass, t[0]): t for t in tasks}
            from concurrent.futures import as_completed
            for fu in as_completed(futs):
                # pop: drop the finished future (and the result it holds) once its map is written. Keeping every
                # future in `futs` held every result in the parent, and its memory crept to the 12 GiB RAM watchdog
                # after ~100-150 maps (2026-10-23, twice); results and files are unchanged.
                _, th, mp, jp = futs.pop(fu)
                _write(fu.result(), th, mp, jp)
                del fu

    # parity per region (all maps of the stage must agree, and equal the target)
    tpid = opt(rival, "target_product")
    parity = {}
    for reg in regions:
        cells = static[static["region"].astype(str) == reg].reset_index(drop=True)
        first = None
        for T in plan:
            z = load_map(out / reg / (MAP_FILE % (T, stage)))
            if first is None:
                first = z
            elif not (np.array_equal(first["parity_forest"], z["parity_forest"])
                      and np.array_equal(first["parity_loss"], z["parity_loss"])):
                _refuse("PARITY %s: map passes of one stage count different pixels" % reg)
        if first is None:
            continue
        parity[reg] = parity_check(reg, cells["cell_id"].astype(str).values, first["parity_forest"],
                                   first["parity_loss"], ymax,
                                   ctx.open_product(tpid, opt(rival, "target_file_pattern") % reg))
    files = {}
    for p in sorted(out.rglob("*__%s.*" % stage)) + sorted(out.rglob("divisions.*")):
        with open(str(p), "rb") as f:
            files[str(p.relative_to(out)).replace("\\", "/")] = sha256_bytes(f.read())
    man = {"format": PREP_FORMAT, "stage": stage, "ymax": int(ymax), "fit_cut": fit_cut, "hrp_years": hrp,
           "issue_years": t_years, "plan": {str(T): v for T, v in stage_plan(t_years, hrp, ymax).items()},
           "bins": bins.as_dict(), "block_px": block, "pixel_deg": px, "tc_thresh": TC_THRESH,
           "hansen_prefix": prefix, "regions": rep_regions, "parity": parity, "files_sha256": files}
    ctx.write_bytes(out / (MANIFEST_FILE % stage), canonical(man))
    ctx.log("defo prep stage %s done: parity equal in %d regions" % (stage, len(parity)))
    return man


def own_name(ctx: Any) -> str:
    return Path(ctx.work_dir()).name


def prep(ctx: Any, rival: Mapping[str, Any]) -> Dict[str, Any]:
    """The registry `prep` entry (rivals_human/index.py prep: fn(ctx, rival)): the stage is the ctx's stage (train
    from `prep`; test only with a lock token), the worker count the registry option prep_workers (results do not
    depend on it: tests_builder_b test_two_workers_give_the_same_files)."""
    stage = str(getattr(ctx, "stage", "train"))
    return run_stage(ctx, rival, stage, int(opt(rival, "prep_workers", 1)))
