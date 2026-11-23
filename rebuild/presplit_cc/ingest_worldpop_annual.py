"""Ingest WorldPop ANNUAL 1 km population (2000-2020 mosaics; use 2002-2020, hold 2020 -> 2021-2023) to REPLACE
the panel's STATIC population_density with an ANNUAL one. Streams one ~1.1 GB global GeoTIFF per year to
D:\\worldpop_dl (deleted after each year), windowed-samples each region's cells (memory-light, per-region bbox),
writes D:\\worldpop_annual\\pop_{year}.parquet [cell_id, population_density]. Then --inject overwrites the panel
column in place (atomic, per year-file). Crash-safe (done years / done year-files skip), all output on D:.
RUN (YOUR terminal, ~22 GB download, resumable):
  py -3.9 presplit_cc/ingest_worldpop_annual.py            # PHASE 1: download + sample all years -> sidecars
  py -3.9 presplit_cc/ingest_worldpop_annual.py --inject   # PHASE 2: overwrite panel population_density (annual)
"""
import glob
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import monthly_loader as ML  # noqa: E402
from assemble_human_drivers import _sample_tif, cells  # noqa: E402  cells(region) -> [cell_id, lon, lat]

PANEL = ML.PANEL_DIR
DL = r"D:\worldpop_dl"
OUT = r"D:\worldpop_annual"
URL = "https://data.worldpop.org/GIS/Population/Global_2000_2020/{y}/0_Mosaicked/ppp_{y}_1km_Aggregated.tif"
YEARS_OBS = list(range(2002, 2021))          # WorldPop mosaics exist 2000-2020
YEARS_HOLD = list(range(2021, 2024))         # 2021-2023 -> hold 2020 forward
COL = "population_density"
for _d in (DL, OUT):
    os.makedirs(_d, exist_ok=True)


def rfiles(r):
    return sorted(glob.glob(os.path.join(PANEL, f"{r}_monthly_*.parquet")))


def download(y, tries=5):
    """curl with RESUME (-C -) + live progress bar (-#) + retries. Migrates any old urllib .part so it resumes."""
    dst = os.path.join(DL, f"ppp_{y}.tif")
    part = dst + ".part"
    if os.path.exists(part) and not os.path.exists(dst):         # reuse a previous partial download (no re-fetch)
        os.replace(part, dst)
    url = URL.format(y=y)
    for a in range(tries):
        rc = subprocess.run(["curl", "-L", "-C", "-", "--retry", "5", "--retry-delay", "10",
                             "--retry-all-errors", "--connect-timeout", "60", "-#", "-o", dst, url]).returncode
        sz = os.path.getsize(dst) if os.path.exists(dst) else 0
        if rc == 0 and sz > 8e8:                                 # ~1.1 GB files; complete = curl rc 0 + > 800 MB
            return dst
        print(f"    curl {y}: rc={rc}, {sz/1e6:.0f} MB so far — retry {a+1}/{tries}", flush=True)
        time.sleep(10 * (a + 1))
    raise RuntimeError(f"WorldPop {y} download failed after {tries} tries")


def all_cells():
    donors, test = ML.split_regions()
    regions = [r for r in (list(donors) + list(test)) if rfiles(r)]
    frames = [cells(r).assign(region=r) for r in regions]
    return pd.concat(frames, ignore_index=True)


def sample_phase():
    t0 = time.time()
    cd = all_cells()
    grp = list(cd.groupby("region"))
    print(f"WorldPop annual | {len(cd):,} cells / {len(grp)} regions | years {YEARS_OBS[0]}-{YEARS_OBS[-1]} (+hold {YEARS_HOLD})", flush=True)
    for y in YEARS_OBS:
        outp = os.path.join(OUT, f"pop_{y}.parquet")
        if os.path.exists(outp):
            print(f"  {y}: sampled -> skip", flush=True); continue
        yt = time.time()
        path = download(y)
        print(f"  {y}: downloaded ({(time.time()-yt):.0f}s), sampling {len(grp)} regions ...", flush=True)
        parts = []
        for region, sub in grp:
            v = _sample_tif(path, sub.lon.values, sub.lat.values)
            v = np.clip(np.nan_to_num(v, nan=0.0), 0, None)          # nodata/ocean/neg -> 0 people
            parts.append(pd.DataFrame({"cell_id": sub.cell_id.values, COL: v.astype("float32")}))
        pd.concat(parts, ignore_index=True).to_parquet(outp, index=False)
        try:
            os.remove(path)
        except OSError:
            pass
        print(f"  {y}: sampled + raster deleted ({(time.time()-yt):.0f}s, total {(time.time()-t0)/60:.0f}m)", flush=True)
    # hold 2020 forward for 2021-2023
    base = pd.read_parquet(os.path.join(OUT, "pop_2020.parquet"))
    for y in YEARS_HOLD:
        outp = os.path.join(OUT, f"pop_{y}.parquet")
        if not os.path.exists(outp):
            base.to_parquet(outp, index=False)
            print(f"  {y}: held from 2020", flush=True)
    print(f"SAMPLE DONE ({(time.time()-t0)/60:.0f}m). sidecars in {OUT}")


def inject_phase():
    t0 = time.time()
    donors, test = ML.split_regions()
    regions = list(donors) + list(test)
    pop = {y: pd.read_parquet(os.path.join(OUT, f"pop_{y}.parquet")).set_index("cell_id")[COL]
           for y in YEARS_OBS + YEARS_HOLD}
    print(f"INJECT annual {COL} -> panel | {len(regions)} regions", flush=True)
    nw = ns = lk = 0
    for i, region in enumerate(regions, 1):
        for f in rfiles(region):
            year = int(os.path.basename(f).rsplit("_", 1)[1].split(".")[0])
            df = pd.read_parquet(f)
            newvals = df["cell_id"].map(pop[year]).astype("float32")
            if COL in df.columns and np.allclose(df[COL].fillna(-1), newvals.fillna(-1), atol=1e-4):
                ns += 1; continue
            df[COL] = newvals                                        # overwrite static -> annual
            tmp = f + ".pop.tmp"; df.to_parquet(tmp, index=False)
            ok = False
            for a in range(4):
                try:
                    os.replace(tmp, f); ok = True; break
                except PermissionError:
                    time.sleep(1.5 * (a + 1))
            if ok:
                nw += 1
            else:
                lk += 1
                try:
                    os.remove(tmp)
                except OSError:
                    pass
        if i % 20 == 0:
            print(f"  ...{i}/{len(regions)} | {nw} written, {ns} already-annual, {lk} locked ({(time.time()-t0)/60:.0f}m)", flush=True)
    print(f"INJECT DONE: {nw} year-files updated, {ns} already-annual, {lk} locked ({(time.time()-t0)/60:.0f}m)")
    print("WORLDPOP_DONE")


if __name__ == "__main__":
    inject_phase() if "--inject" in sys.argv else sample_phase()
