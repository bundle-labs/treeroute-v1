"""Ingest the 3 fire drivers from FireCCI / C3S burned-area (CDS satellite-fire-burned-area, 0.25deg
GLOBAL grid, `burned_area` m2/month). Master's V20_burned_binary = MODIS MCD64A1 BurnDate>0 any-month;
we use the cleaner FireCCI grid (same MODIS burned-area concept) -> esa_cci/MODIS for <=2020,
c3s/OLCI for >=2021. Download each year's 12 global monthly files, sample ALL 133 regions (MODULO lon
-> convention-agnostic, the soil-moisture lesson), then derive:
  * V20_burned_binary  (MONTHLY): 1 if the cell's monthly burned_area > 0
  * burn_month_count   (annual -> broadcast to 12 months): # burned months in the year
  * burn_doy_mean      (annual -> broadcast): burned-area-weighted mean mid-month DOY (0 if no fire)
Single process, low concurrency, validate-on-1yr first. On D:. (3rd-to-last tier before assembly.)

  py -3.9 presplit_cc/ingest_firecci_fire.py --years 2010 --out D:\fire_test
  py -3.9 presplit_cc/ingest_firecci_fire.py --out D:\fire_monthly
"""
import glob
import os
import sys
import time
import zipfile

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ingest_agera5_daycounts import CC, _masters  # noqa: E402

DATASET = "satellite-fire-burned-area"
YEARS = list(range(2002, 2024))
MODIS_LAST = 2019                                                # esa_cci/MODIS ends 2019 (2020 invalid); OLCI for >=2020
TMP_DEFAULT = r"D:\fire_dl"
OUT_DEFAULT = r"D:\fire_monthly"
MID_DOY = np.array([15, 45, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349], "float32")  # mid-month DOY
_TRANSIENT = ("429", "too many", "500", "502", "503", "504", "timeout", "timed out", "connection",
              "remote", "bad gateway", "download", "0 byte", "incomplete", "reset", "cci2",
              "internalerror", "serviceunavailable", "slowdown", "temporarily limited", "queued requests",
              "rejected")


def _origin(year):
    if year <= MODIS_LAST:
        return {"origin": "esa_cci", "sensor": "modis", "version": "5_1_1cds"}
    return {"origin": "c3s", "sensor": "olci", "version": "1_1"}


def _retrieve(c, year, tmp, attempt=0):
    out = os.path.join(tmp, f"fire_{year}.zip")
    if os.path.exists(out) and os.path.getsize(out) > 1000 and zipfile.is_zipfile(out):
        return out
    req = dict(_origin(year))
    req.update({"year": str(year), "month": [f"{m:02d}" for m in range(1, 13)],
                "nominal_day": "01", "variable": "grid_variables", "format": "zip"})
    try:
        c.retrieve(DATASET, req, out)
        return out
    except Exception as e:
        msg = str(e).lower()
        if any(k in msg for k in _TRANSIENT) and attempt < 25:
            time.sleep(90 if ("limited" in msg or "rejected" in msg or "queued" in msg) else min(20 * (attempt + 1), 180))
            return _retrieve(c, year, tmp, attempt + 1)
        raise


def _read_zip(zp, tmp):
    """-> {(year,month): burned_area 2D (m2)}, glat, glon. Reads each monthly .nc in the year zip."""
    from netCDF4 import Dataset, num2date
    out = {}; glat = glon = None
    z = zipfile.ZipFile(zp)
    ex = os.path.join(tmp, "ex_" + os.path.basename(zp).replace(".zip", ""))
    os.makedirs(ex, exist_ok=True)
    for name in z.namelist():
        if not name.endswith(".nc"):
            continue
        z.extract(name, ex)
        ds = Dataset(os.path.join(ex, name))
        if glat is None:
            glat = np.asarray(ds.variables["lat"][:]); glon = np.asarray(ds.variables["lon"][:])
        t = num2date(ds.variables["time"][:], ds.variables["time"].units)[0]
        ba = np.ma.filled(np.squeeze(ds.variables["burned_area"][:]).astype("float32"), 0.0)
        out[(t.year, t.month)] = ba
        ds.close()
        os.remove(os.path.join(ex, name))
    try:
        os.rmdir(ex)
    except OSError:
        pass
    return out, glat, glon


def main(argv):
    def opt(f, d=None):
        return argv[argv.index(f) + 1] if f in argv else d
    tmp = opt("--tmp", TMP_DEFAULT); out_dir = opt("--out", OUT_DEFAULT)
    years = [int(y) for y in opt("--years", ",".join(map(str, YEARS))).split(",")]
    os.makedirs(tmp, exist_ok=True); os.makedirs(out_dir, exist_ok=True)
    masters = _masters(); regs = sorted(masters)
    todo = [r for r in regs if not os.path.exists(os.path.join(out_dir, f"{r}_fire.parquet"))]
    if opt("--region"):
        todo = [r for r in todo if r == opt("--region")] or [opt("--region")]
    if not todo:
        print("all regions done.", flush=True); return 0
    cells = {r: pd.read_parquet(masters[r], columns=[CC, "lon", "lat"]).drop_duplicates(CC) for r in todo}
    months = [(y, m) for y in years for m in range(1, 13)]
    midx = {ym: j for j, ym in enumerate(months)}
    ba_acc = {r: np.zeros((len(months), len(cells[r])), "float32") for r in todo}   # monthly burned_area m2
    idx = {}
    print(f"FireCCI fire -> {len(todo)} regions x {len(years)} yrs -> {out_dir}", flush=True)

    import cdsapi
    c = cdsapi.Client()
    for y in years:
        try:
            zp = _retrieve(c, y, tmp)
            data, glat, glon = _read_zip(zp, tmp)
            if not idx:
                lon0 = float(glon[0]); dlon = float(glon[1] - glon[0]); nlon = len(glon)
                lat0 = float(glat[0]); dlat = float(glat[1] - glat[0]); nlat = len(glat)
                print(f"    grid: lon[{float(np.min(glon)):.2f},{float(np.max(glon)):.2f}] n={nlon} "
                      f"lat[{float(np.min(glat)):.2f},{float(np.max(glat)):.2f}] n={nlat}", flush=True)
                for r in todo:
                    il = np.rint((cells[r].lon.to_numpy() - lon0) / dlon).astype(int) % nlon
                    ia = np.clip(np.rint((cells[r].lat.to_numpy() - lat0) / dlat).astype(int), 0, nlat - 1)
                    idx[r] = (ia, il)
            for r in todo:
                ia, il = idx[r]
                for ym, ba in data.items():
                    if ym in midx:
                        ba_acc[r][midx[ym]] = ba[ia, il]
            del data
            try:
                os.remove(zp)
            except OSError:
                pass
            print(f"    {y}: sampled all {len(todo)} regions", flush=True)
        except Exception as ex:
            print(f"    {y} ERROR {type(ex).__name__}: {str(ex)[:160]}", flush=True); return 1

    yr_of = np.array([y for y, m in months]); uyears = years
    for r in todo:
        ncell = len(cells[r]); ba = ba_acc[r]                      # (nmon, ncell)
        binary = (ba > 0).astype("float32")                       # V20 monthly
        bmc = np.zeros_like(ba); bdoy = np.zeros_like(ba)
        for y in uyears:
            sel = np.where(yr_of == y)[0]                         # 12 month-rows of year y
            cnt = binary[sel].sum(axis=0)                        # burned months per cell that year
            wsum = ba[sel].sum(axis=0)                           # total burned area that year
            wdoy = (ba[sel] * MID_DOY[:len(sel), None]).sum(axis=0)
            with np.errstate(invalid="ignore", divide="ignore"):
                dm = np.where(wsum > 0, wdoy / wsum, 0.0)        # area-weighted mean DOY, 0 if no fire
            bmc[sel] = cnt[None, :]; bdoy[sel] = dm[None, :]     # broadcast annual value to the 12 months
        rows = {CC: np.repeat(cells[r][CC].to_numpy(), len(months)),
                "year": np.tile(yr_of, ncell), "month": np.tile([m for y, m in months], ncell),
                "V20_burned_binary": binary.T.reshape(-1),
                "burn_month_count": bmc.T.reshape(-1),
                "burn_doy_mean": bdoy.T.reshape(-1)}
        pd.DataFrame(rows).to_parquet(os.path.join(out_dir, f"{r}_fire.parquet"), index=False)
        frac = binary.mean() * 100
        print(f"  wrote {r} ({ncell} cells, {frac:.2f}% burned cell-months)", flush=True)
    print("done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
