"""Ingest DeepRec deep-learning GRACE/GRACE-FO reconstruction (twsa, cm) into per-region-year sidecar parquet for the
monthly panel. UNLIKE the raw GRACE mascon (grace_lwe, which has the ~11-month 2017-18 GRACE->GRACE-FO gap + scattered
missing months), DeepRec is GAP-FREE monthly 1941-2023 -- a continuous total-water-storage (deep soil water + groundwater)
signal that fully covers the 2002-2023 panel window. Reads the ALREADY-DOWNLOADED Zenodo NetCDF at
D:\\deeprec\\DeepRec_mixture_CSR_ERA5-ONI-HI.nc (0.5deg, lon 0-360), samples each 4km cell at its nearest 0.5deg cell per
(year,month). LIGHT + LOCAL (no network). Resumable (skips existing region-year files). Mirrors ingest_grace_monthly.py.
RUN: py -3.9 presplit_cc/ingest_deeprec_tws.py [--region <name>]
OUT: D:\\deeprec_monthly\\{region}_deeprec_{year}.parquet  (column deeprec_twsa)  -> then add_evi_to_panel.py to fold in.
"""
import glob
import os
import sys

import numpy as np
import pandas as pd
import xarray as xr
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
NC = r"D:\deeprec\DeepRec_mixture_CSR_ERA5-ONI-HI.nc"
VAR, COL = "twsa", "deeprec_twsa"
OUT = r"D:\deeprec_monthly"
YEARS = list(range(2002, 2024))
ONLY = sys.argv[sys.argv.index("--region") + 1] if "--region" in sys.argv else None


def _masters():
    m = {}
    for d in (cfg["data"]["master_dir"], cfg["forecast"]["regions_dir"]):
        for p in glob.glob(os.path.join(d, "*_master_*.parquet")):
            if ".bak." not in p:
                m.setdefault(os.path.basename(p).split("_master_")[0], p)
    return m


def main():
    if not os.path.exists(NC):
        raise SystemExit(f"FAIL-LOUD: DeepRec NetCDF not found at {NC}")
    g = xr.open_dataset(NC)[VAR].load()                          # ~1GB in-memory -> fast repeated sampling
    gy, gm = g["time.year"].values, g["time.month"].values
    ym2i = {(int(y), int(mm)): i for i, (y, mm) in enumerate(zip(gy, gm))}
    os.makedirs(OUT, exist_ok=True)
    M = _masters(); regs = sorted(M)
    if ONLY:
        regs = [r for r in regs if r == ONLY]
    present = sum(1 for y in YEARS for mm in range(1, 13) if (y, mm) in ym2i)
    print(f"DeepRec {VAR}: {len(ym2i)} monthly slices | {present}/264 panel months covered (gap-free) | {len(regs)} regions", flush=True)
    for r in regs:
        cells = pd.read_parquet(M[r], columns=["cell_id", "lon", "lat"]).drop_duplicates("cell_id").reset_index(drop=True)
        lon_da = xr.DataArray(cells.lon.to_numpy() % 360, dims="c")     # DeepRec lon is 0-360
        lat_da = xr.DataArray(cells.lat.to_numpy(), dims="c")
        wrote = 0
        for y in YEARS:
            outf = os.path.join(OUT, f"{r}_deeprec_{y}.parquet")
            if os.path.exists(outf):
                continue
            buf = np.full((len(cells), 12), np.nan, "float32")
            for mm in range(1, 13):
                if (y, mm) in ym2i:
                    buf[:, mm - 1] = g.isel(time=ym2i[(y, mm)]).sel(lon=lon_da, lat=lat_da, method="nearest").to_numpy()
            rows = {"cell_id": np.repeat(cells.cell_id.to_numpy(), 12), "year": y,
                    "month": np.tile(np.arange(1, 13), len(cells)), COL: buf.reshape(-1)}
            pd.DataFrame(rows).to_parquet(outf, index=False); wrote += 1
        print(f"  {r}: {wrote} year-files ({len(cells)} cells)", flush=True)
    print("DEEPREC_INGEST_DONE", flush=True)


if __name__ == "__main__":
    main()
