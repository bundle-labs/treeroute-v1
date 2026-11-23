"""Add the three already-fetched drivers to the feature table: cyclones, ENSO/IOD, and the CRW mask.

    py -3.9 -u coral_extra_drivers.py

These three are on disk and were never used. None needs a download.

  C8  IBTrACS cyclones  -- a storm's cold wake can rescue a reef mid-heatwave, and its waves can
      destroy the framework. Every track point is DATED, so any window ending before the dive is
      clean by construction. Features: max sustained wind and minimum approach distance for storms
      passing within 200/500 km over 30/90/365 days, plus days since the last close pass.
  C16 ENSO Nino 3.4 + IOD DMI -- basin-scale state, the standard non-thermal covariate in this
      literature. Joined on the observation's year-month, plus 3- and 6-month lags. The index files
      are raw anomalies on a FIXED historical base, so no centred-window statistic leaks the future.
  C3  CRW land/water mask -- not predictive. A QC pair: distance from the site to the nearest
      valid-water pixel, and how many of the surrounding pixels are land. Flags the inshore and
      fringing reefs where a 5 km pixel misrepresents the reef, which is where coordinate matching
      is known to fail 10-20% of the time.

Output: dhw_features_plus.parquet -- the existing columns plus these, so an A/B against the
SST-only model is a column subset rather than a re-run.
"""
import io
import os
import warnings

warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

FEAT = "dhw_features.parquet"
EV = r"D:\coral\target\events_dated.parquet"
IBT = r"D:\coral\drivers\static\IBTrACS.ALL.v04r01.nc"
CLIM = r"D:\coral\drivers\static\ct5km_climatology_v3.1.nc"
NINO = r"D:\coral\drivers\climate\nina34.txt"
DMI = r"D:\coral\drivers\climate\dmi.txt"
R = 6371.0


def hav(la1, lo1, la2, lo2):
    p = np.pi / 180.0
    a = (np.sin((la2 - la1) * p / 2) ** 2
         + np.cos(la1 * p) * np.cos(la2 * p) * np.sin((lo2 - lo1) * p / 2) ** 2)
    return 2 * R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def psl_index(path):
    """PSL monthly index: a year followed by 12 values, with a trailing missing-value sentinel."""
    rows, miss = [], None
    for ln in io.open(path, encoding="utf-8", errors="replace"):
        p = ln.split()
        if len(p) == 13:
            try:
                y = int(p[0])
            except ValueError:
                continue
            for m, v in enumerate(p[1:], 1):
                rows.append((y, m, float(v)))
        elif len(p) == 1:
            try:
                miss = float(p[0])
            except ValueError:
                pass
    d = pd.DataFrame(rows, columns=["yr", "mo", "v"])
    if miss is not None:
        d.loc[np.isclose(d.v, miss), "v"] = np.nan
    d.loc[d.v < -900, "v"] = np.nan
    return d


def cyclone_feats(ev):
    from netCDF4 import Dataset
    ds = Dataset(IBT)
    lat = np.ma.filled(ds.variables["lat"][:], np.nan).astype("float32")
    lon = np.ma.filled(ds.variables["lon"][:], np.nan).astype("float32")
    _w = ds.variables["usa_wind"][:]          # int16 with a masked fill -> cast BEFORE filling
    wnd = np.ma.filled(_w.astype("float32"), np.nan)
    tim = np.ma.filled(ds.variables["time"][:], np.nan).astype("float64")
    tu = ds.variables["time"].units
    ds.close()
    base = pd.Timestamp(tu.split("since")[-1].strip().split()[0])
    ok = np.isfinite(lat) & np.isfinite(lon) & np.isfinite(tim)
    la, lo = lat[ok], lon[ok]
    t = base + pd.to_timedelta(tim[ok], unit="D")
    w = np.where(np.isfinite(wnd[ok]), wnd[ok], 0.0)
    lo = ((lo + 180) % 360) - 180
    tn = t.values.astype("datetime64[D]").astype(int)
    order = np.argsort(tn)
    la, lo, w, tn = la[order], lo[order], w[order], tn[order]
    print("   IBTrACS track points usable: %s (%s .. %s)"
          % (format(len(tn), ","), t.min().date(), t.max().date()))

    out = []
    ed = ev.date.values.astype("datetime64[D]").astype(int)
    for i in range(len(ev)):
        f = {}
        for days in (30, 90, 365):
            lo_i, hi_i = np.searchsorted(tn, [ed[i] - days, ed[i]])
            if hi_i <= lo_i:
                for rad in (200, 500):
                    f["cyc_maxw_%d_%d" % (rad, days)] = 0.0
                    f["cyc_n_%d_%d" % (rad, days)] = 0
                f["cyc_mindist_%d" % days] = 9999.0
                continue
            d = hav(ev.lat.values[i], ev.lon.values[i], la[lo_i:hi_i], lo[lo_i:hi_i])
            ww = w[lo_i:hi_i]
            f["cyc_mindist_%d" % days] = float(d.min())
            for rad in (200, 500):
                m = d <= rad
                f["cyc_maxw_%d_%d" % (rad, days)] = float(ww[m].max()) if m.any() else 0.0
                f["cyc_n_%d_%d" % (rad, days)] = int(m.sum())
        lo_i = np.searchsorted(tn, ed[i] - 3650)
        hi_i = np.searchsorted(tn, ed[i])
        if hi_i > lo_i:
            d = hav(ev.lat.values[i], ev.lon.values[i], la[lo_i:hi_i], lo[lo_i:hi_i])
            near = np.where(d <= 200)[0]
            f["cyc_days_since_close"] = float(ed[i] - tn[lo_i:hi_i][near].max()) if len(near) else 3650.0
        else:
            f["cyc_days_since_close"] = 3650.0
        out.append(f)
        if (i + 1) % 2000 == 0:
            print("   ... cyclones %d/%d" % (i + 1, len(ev)), flush=True)
    return pd.DataFrame(out, index=ev.index)


def mask_feats(ev):
    from netCDF4 import Dataset
    ds = Dataset(CLIM)
    vn = "mask_for_sst_clim_mmm" if "mask_for_sst_clim_mmm" in ds.variables else [v for v in ds.variables if "mask" in v.lower()][0]
    m = np.ma.filled(ds.variables[vn][:], 0)
    m = np.squeeze(m)
    la = np.ma.filled(ds.variables["lat"][:], np.nan)
    lo = np.ma.filled(ds.variables["lon"][:], np.nan)
    ds.close()
    # flag_values 0,1,2,4 = valid-water, land, missing, ice. Water is 0, NOT 1.
    water = (m == 0)
    print("   mask grid %s | water pixels %s (%.1f%%)"
          % (m.shape, format(int(water.sum()), ","), 100 * water.mean()))
    out = []
    for i in range(len(ev)):
        ii = int(np.abs(la - ev.lat.values[i]).argmin())
        jj = int(np.abs(lo - ev.lon.values[i]).argmin())
        i0, i1 = max(0, ii - 3), min(m.shape[0], ii + 4)
        j0, j1 = max(0, jj - 3), min(m.shape[1], jj + 4)
        box = water[i0:i1, j0:j1]
        out.append(dict(mask_is_water=int(water[ii, jj]),
                        mask_land_frac_7x7=float(1.0 - box.mean()) if box.size else np.nan))
    return pd.DataFrame(out, index=ev.index)


def main():
    X = pd.read_parquet(FEAT)
    ev = pd.read_parquet(EV)
    X = X.merge(ev[["lat", "lon"]], left_on="sid", right_index=True, how="left")
    print("rows %s" % format(len(X), ","))

    print("\nC16 ENSO / IOD")
    n34, dmi = psl_index(NINO), psl_index(DMI)
    print("   nino3.4 %d months (%d-%d) | dmi %d months (%d-%d)"
          % (n34.v.notna().sum(), n34.yr.min(), n34.yr.max(),
             dmi.v.notna().sum(), dmi.yr.min(), dmi.yr.max()))
    for nm, src in (("nino34", n34), ("dmi", dmi)):
        s = src.set_index(["yr", "mo"]).v
        for lag in (0, 3, 6):
            d = X.date - pd.DateOffset(months=lag)
            X["%s_lag%d" % (nm, lag)] = [s.get((y, m), np.nan)
                                         for y, m in zip(d.dt.year, d.dt.month)]

    print("\nC8 cyclones")
    X = pd.concat([X, cyclone_feats(X)], axis=1)

    print("\nC3 CRW mask")
    X = pd.concat([X, mask_feats(X)], axis=1)

    X.to_parquet("dhw_features_plus.parquet", index=False)
    new = [c for c in X.columns if c.startswith(("cyc_", "nino34_", "dmi_", "mask_"))]
    print("\nadded %d columns -> dhw_features_plus.parquet" % len(new))
    print("   %s" % ", ".join(new))
    nz = {c: float((X[c].fillna(0) != 0).mean()) for c in new}
    print("\n   non-zero rate (a column that is always 0 carries nothing):")
    for c in new:
        print("      %-26s %.3f" % (c, nz[c]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
