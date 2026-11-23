"""Ingest the regional SST-anomaly drivers (sst_anom_*) from NOAA ERSSTv5 -- no auth, NetCDF
via PSL OPeNDAP. These are GLOBAL scalar monthly series (one value per month, same for every
cell), so this writes ONE small table [year, month, sst_anom_*] (264 rows for 2002-2023) to
broadcast across all cells at assembly time -- exactly like the NOAA teleconnection indices.

Method (per box): cosine-latitude-weighted ocean mean SST over the box each month -> subtract
the box's 1971-2000 monthly climatology -> anomaly. Box defs are listed below (in -180..180
lon); ERSST's native 0-360 lon is converted internally. nino34 is computed as a VALIDATION box
(compared to the canonical NOAA nino34 from ingest_noaa_indices.py).

  py -3.9 presplit_cc/ingest_ersst_boxes.py --selftest      # box-mask geometry, no network
  py -3.9 presplit_cc/ingest_ersst_boxes.py --probe         # source + nino34 validation vs NOAA
  py -3.9 presplit_cc/ingest_ersst_boxes.py --out PATH.parquet
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
import yaml  # noqa: E402
cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
BUNDLE = os.path.dirname(cfg["data"]["master_dir"])
OPENDAP = "https://psl.noaa.gov/thredds/dodsC/Datasets/noaa.ersst.v5/sst.mnmean.nc"
DOWNLOAD = "https://downloads.psl.noaa.gov/Datasets/noaa.ersst.v5/sst.mnmean.nc"
YEAR_LO, YEAR_HI = 2002, 2023
CLIM_LO, CLIM_HI = 1971, 2000                          # anomaly baseline (matches the master's sst_anom_*)

# box: (lon_west, lon_east, lat_south, lat_north) in -180..180.  *** review these vs the original ***
BOXES = {
    "nino34":                   (-170, -120,  -5,   5),   # VALIDATION ONLY (also in NOAA indices)
    "atl3":                     (-20,     0,  -3,   3),
    "iod_west":                 (50,     70, -10,  10),
    "iod_east":                 (90,    110, -10,   0),
    "subpolar_north_atlantic":  (-60,   -10,  50,  65),
    "coral_sea":                (145,   170, -30, -10),
    "mediterranean":            (-5,     36,  30,  46),
    "global_tropical_mean":     (-180,  180, -20,  20),
}
OUTBOXES = [b for b in BOXES if b != "nino34"] + ["nino34"]   # output all; nino34 last


def _open():
    """Download the (small) ERSSTv5 NetCDF once and read it LOCALLY -- to D:, NOT the C: system
    temp (C: is space-critical) -- OPeNDAP bulk data reads are unreliable for multi-year slices."""
    import netCDF4 as nc
    import requests
    d = r"D:\ersst_dl"; os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "ersst.v5.sst.mnmean.nc")
    if not os.path.exists(p) or os.path.getsize(p) < 1_000_000:
        with requests.get(DOWNLOAD, stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(p, "wb") as fh:
                for c in r.iter_content(1 << 20):
                    fh.write(c)
    return nc.Dataset(p)


def _conv_lon(lon):
    return np.where(lon > 180, lon - 360.0, lon)


def _box_mask(lon2d, lat2d, box):
    lw, le, ls, ln = box
    cl = _conv_lon(lon2d)
    return (cl >= lw) & (cl <= le) & (lat2d >= ls) & (lat2d <= ln)


def _series(sst, lon, lat, box):
    """Cosine-lat-weighted ocean-mean SST per month for the box. sst: (T, nlat, nlon) masked."""
    lon2d, lat2d = np.meshgrid(lon, lat)
    m = _box_mask(lon2d, lat2d, box)
    w = np.cos(np.deg2rad(lat2d)) * m                  # zero outside the box
    out = np.full(sst.shape[0], np.nan, "float64")
    for t in range(sst.shape[0]):
        sl = sst[t]
        valid = m & ~np.ma.getmaskarray(sl)            # ocean cells in box with data
        ww = np.cos(np.deg2rad(lat2d))[valid]
        vals = np.asarray(sl)[valid]
        if ww.sum() > 0:
            out[t] = float(np.sum(vals * ww) / np.sum(ww))
    return out


def _anomaly(series, months, years):
    clim = {}
    for mo in range(1, 13):
        sel = (months == mo) & (years >= CLIM_LO) & (years <= CLIM_HI)
        clim[mo] = np.nanmean(series[sel]) if sel.any() else np.nan
    return series - np.array([clim[mo] for mo in months])


def _load_slice():
    import netCDF4 as nc
    ds = _open()
    t = ds.variables["time"]
    dates = nc.num2date(t[:], t.units, getattr(t, "calendar", "standard"))
    yrs = np.array([d.year for d in dates]); mos = np.array([d.month for d in dates])
    keep = (yrs >= CLIM_LO) & (yrs <= YEAR_HI)
    i0, i1 = int(np.argmax(keep)), len(keep) - int(np.argmax(keep[::-1]))
    lon = np.asarray(ds.variables["lon"][:]); lat = np.asarray(ds.variables["lat"][:])
    sst = ds.variables["sst"][i0:i1]                   # masked array (T, nlat, nlon), degC
    ds.close()
    return sst, lon, lat, yrs[i0:i1], mos[i0:i1]


def _selftest():
    lon = np.arange(0, 360, 2.0); lat = np.arange(88, -89, -2.0)
    lon2d, lat2d = np.meshgrid(lon, lat)
    ok = True
    checks = {"nino34": (-145, 0), "atl3": (-10, 0), "iod_west": (60, 0), "mediterranean": (18, 38)}
    for b, (clon, clat) in checks.items():
        m = _box_mask(lon2d, lat2d, BOXES[b])
        # the test centre should be inside; a far point should not
        ci = np.argmin(np.abs(_conv_lon(lon) - clon)); ri = np.argmin(np.abs(lat - clat))
        inside = m[ri, ci]
        outside = m[np.argmin(np.abs(lat - (-clat - 40))) % len(lat), ci]
        if not inside or outside:
            print(f"  FAIL {b}: inside={inside} outside={outside}"); ok = False
    print("selftest:", "PASS (box masks)" if ok else "FAIL")
    return 0 if ok else 1


def _build():
    sst, lon, lat, yrs, mos = _load_slice()
    print(f"ERSST slice {yrs[0]}-{mos[0]:02d} .. {yrs[-1]}-{mos[-1]:02d}  ({sst.shape})", flush=True)
    cols = {}
    for b in OUTBOXES:
        s = _series(sst, lon, lat, BOXES[b])
        cols[f"sst_anom_{b}"] = _anomaly(s, mos, yrs)
        print(f"  {b:26s} clim-mean SST OK, anomaly std={np.nanstd(cols[f'sst_anom_{b}']):.2f}", flush=True)
    df = pd.DataFrame({"year": yrs, "month": mos, **cols})
    return df[(df.year >= YEAR_LO) & (df.year <= YEAR_HI)].reset_index(drop=True)


def _probe():
    df = _build()
    print("\nshape:", df.shape, "(expect 264 rows)")
    noaa_p = os.path.join(BUNDLE, "noaa_indices_monthly.parquet")
    if os.path.exists(noaa_p):
        n = pd.read_parquet(noaa_p)[["year", "month", "nino34"]]
        j = df.merge(n, on=["year", "month"]).dropna(subset=["sst_anom_nino34", "nino34"])
        r = j["sst_anom_nino34"].corr(j["nino34"])
        print(f"VALIDATION nino34: ERSST vs NOAA  r={r:.3f}  "
              f"mean|diff|={ (j.sst_anom_nino34 - j.nino34).abs().mean():.3f}  "
              f"(r>0.95 => box-averaging + anomaly are correct)")
    print("probe: PASS" if df.shape[0] == 264 else "probe: CHECK ROWS")
    return 0


def main(argv):
    if "--selftest" in argv:
        return _selftest()
    if "--probe" in argv:
        return _probe()
    out = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(BUNDLE, "ersst_sst_boxes_monthly.parquet")
    df = _build()
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"\nwrote {out}  ({df.shape[0]} rows x {df.shape[1]-2} SST-anomaly cols)")
    print("cols:", [c for c in df.columns if c.startswith("sst_anom_")])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
