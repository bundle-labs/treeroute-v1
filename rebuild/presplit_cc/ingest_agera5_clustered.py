"""Ingest the 11 AgERA5 day-count drivers via REGION-CLUSTERED big-box requests. Covers all 133
regions with ~22 continental boxes (<=~48deg span, under CDS's data-volume ceiling), at FULL 0.1deg
resolution -- ~6x fewer requests than per-region (~2-3 days vs ~2 weeks), no resolution compromise.

Per box: for each year (year-chunked for CDS's per-request file-count limit) fetch the 6 variable
groups over the WHOLE box -> derive that year's 12 monthly cols on the box grid -> sample EACH
region's real cells -> accumulate. After all years, write one parquet per region. Memory-bounded
(one year of the box held at a time). Crash-safe (skip regions whose parquet exists). Shardable by
box (--shard i/n). Everything on D:. Reuses the request/derive logic from ingest_agera5_daycounts.

  py -3.9 presplit_cc/ingest_agera5_clustered.py --shard 0/3 --out D:\agera5_daycounts --tmp D:\agera5_dl
"""
import glob
import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ingest_agera5_daycounts import (CC, GROUPS, OUTCOLS, YEARS, _derive, _masters,  # noqa: E402
                                     _read_group, _retrieve, cfg, grid_indices)

TILE = 45            # deg: bin region centroids into tiles; box = union bbox of a tile's regions
PAD = 0.15
TMP_DEFAULT = r"D:\agera5_dl"
OUT_DEFAULT = r"D:\agera5_daycounts"


def _cluster(regs, ext):
    bins = {}
    for r in regs:
        clo = (ext[r][0] + ext[r][1]) / 2.0
        cla = (ext[r][2] + ext[r][3]) / 2.0
        bins.setdefault((int(np.floor(clo / TILE)), int(np.floor(cla / TILE))), []).append(r)
    return [(k, v) for k, v in sorted(bins.items())]


def main(argv):
    def opt(flag, d=None):
        return argv[argv.index(flag) + 1] if flag in argv else d
    tmp = opt("--tmp", TMP_DEFAULT); out_dir = opt("--out", OUT_DEFAULT)
    years = [int(y) for y in opt("--years", ",".join(map(str, YEARS))).split(",")]
    os.makedirs(tmp, exist_ok=True); os.makedirs(out_dir, exist_ok=True)
    nmon = len(years) * 12
    months = [(y, m) for y in years for m in range(1, 13)]
    accols = [c for c in OUTCOLS if c != "sph_kgkg"] + ["vp_mean"]

    masters = _masters(); regs = sorted(masters)
    cells = {}; ext = {}
    for r in regs:
        c = pd.read_parquet(masters[r], columns=[CC, "lon", "lat", "V25_elevation_m"]).drop_duplicates(CC)
        cells[r] = c
        ext[r] = (float(c.lon.min()), float(c.lon.max()), float(c.lat.min()), float(c.lat.max()))
    boxes = _cluster(regs, ext)
    shard = opt("--shard")
    if shard:
        i, n = (int(x) for x in shard.split("/"))
        boxes = [b for k, b in enumerate(boxes) if k % n == i]
    only = opt("--region")                              # validation: process only this region's box, write only it
    if only:
        boxes = [(k, v) for k, v in boxes if only in v]
    print(f"AgERA5 clustered -> {len(boxes)} boxes ({sum(len(b) for _, b in boxes)} regions) x {len(years)} yrs -> {out_dir}", flush=True)

    import cdsapi
    s = cdsapi.Client()
    for key, bregs in boxes:
        todo = [r for r in bregs if not os.path.exists(os.path.join(out_dir, f"{r}_agera5.parquet"))]
        if only:
            todo = [r for r in bregs if r == only]
        if not todo:
            print(f"  box {key}: all {len(bregs)} done, skip", flush=True); continue
        N = max(ext[r][3] for r in bregs) + PAD; S = min(ext[r][2] for r in bregs) - PAD
        W = min(ext[r][0] for r in bregs) - PAD; E = max(ext[r][1] for r in bregs) + PAD
        # round OUTWARD to the 0.1deg AgERA5 grid: a deterministic, grid-aligned bbox that never loses
        # coverage -- and, being a different request hash, sidesteps any stale/broken CDS cache object
        # keyed to the old full-precision bbox (the 2026-06-20 AccessDenied cache that stuck box(-2,0)).
        bbox = [math.ceil(N * 10) / 10, math.floor(W * 10) / 10, math.floor(S * 10) / 10, math.ceil(E * 10) / 10]
        print(f"  box {key}: {len(bregs)} regions ({len(todo)} todo)  bbox~{int(E-W)}x{int(N-S)}deg", flush=True)
        try:
            accbox = None; glat0 = glon0 = None       # monthly cols accumulated on the box 0.1deg grid
            for yi, year in enumerate(years):
                daily = {}
                for g, gspec in GROUPS.items():
                    zips = _retrieve(s, gspec, bbox, [year], tmp, f"box{key[0]}_{key[1]}_{g}")
                    gd, glat, glon = _read_group(zips, gspec["roles"])
                    daily.update(gd)
                    for z in zips:
                        try:
                            os.remove(z)
                        except OSError:
                            pass
                grids = _derive(daily, glat, glon, [year])      # this year's 12 monthly box grids
                if grids is None:
                    print(f"    {year}: NO DATA, skip", flush=True); del daily; continue
                if accbox is None:
                    _, ny, nx = grids[accols[0]].shape
                    accbox = {c: np.full((nmon, ny, nx), np.nan, "float32") for c in accols}
                    glat0, glon0 = glat, glon
                for c in accols:
                    accbox[c][yi * 12:(yi + 1) * 12] = grids[c]
                del daily, grids
                print(f"    {year}: sampled", flush=True)
            if accbox is None:
                print(f"  box {key}: NO DATA at all, skip", flush=True); continue
            for r in todo:
                ncell = len(cells[r])
                il, ia = grid_indices(cells[r].lon.to_numpy(), cells[r].lat.to_numpy(), glon0, glat0)
                rows = {CC: np.repeat(cells[r][CC].to_numpy(), nmon),
                        "year": np.tile([y for y, m in months], ncell),
                        "month": np.tile([m for y, m in months], ncell)}
                for c in OUTCOLS:
                    if c == "sph_kgkg":
                        continue
                    rows[c] = accbox[c][:, ia, il].T.reshape(-1)
                e = accbox["vp_mean"][:, ia, il].T.reshape(-1) * 100.0     # hPa -> Pa
                elev = np.repeat(cells[r]["V25_elevation_m"].to_numpy(), nmon)
                p = 101325.0 * np.power(np.clip(1 - 2.25577e-5 * np.nan_to_num(elev), 0.1, 1.2), 5.25588)
                with np.errstate(invalid="ignore", divide="ignore"):
                    rows["sph_kgkg"] = (0.622 * e / np.maximum(p - 0.378 * e, 1.0)).astype("float32")
                pd.DataFrame(rows).to_parquet(os.path.join(out_dir, f"{r}_agera5.parquet"), index=False)
                print(f"    wrote {r} ({ncell} cells)", flush=True)
            del accbox
        except Exception as ex:
            print(f"  box {key} ERROR {type(ex).__name__}: {str(ex)[:180]}", flush=True)
    print("done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
