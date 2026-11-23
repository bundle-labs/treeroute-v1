"""Assemble the CURATED ~15 human/economic drivers onto region panels, keyed to each region's cells. Each driver
is an INDEPENDENT handler wrapped in try/except (a failure is logged + skipped, never kills the run) and cached
per region+driver at D:\\human_drivers\\<region>__<driver>.parquet; the merged per-region output is
D:\\human_drivers\\<region>.parquet. Global spatial indices (power plants, coal mines, dams, oil&gas wells, UCDP
events, WDPA) are built ONCE per process and reused across regions.

Driver columns (35 features): gdp_pc, ntl, hdi, luh2 {cropland,pasture,range,urban,forest,secondary}, fert {n,p},
aglw_{cattle,buffalo,horse,sheep,goats,total_lsu} (NEW annual livestock), road_density, travel_time,
dist_{powerplant,thermal,coal_mine,dam,reservoir,oilgas_well}, dist_pa, conflict_events, conflict_deaths, co2,
food_price {index,meat,dairy,cereals,oils,sugar}. (authoritative lists: required_sources() / output_columns())
HEAVY files (OGIM 2.75GB, WDPA 2.2GB, LUH2 6.7GB) -> distance drivers use BallTree(haversine) over feature POINTS
(memory-bounded). Crash-safe/resumable (per region+driver cache; finished regions skip).

RUN (YOUR terminal, resumable):
  py -3.9 presplit_cc/assemble_human_drivers.py --all       # ALL 133 split regions (89 train + 44 test)
  py -3.9 presplit_cc/assemble_human_drivers.py --train     # 89 train/donor regions only
  py -3.9 presplit_cc/assemble_human_drivers.py --test      # 44 held-out test regions only
  py -3.9 presplit_cc/assemble_human_drivers.py <region>... # explicit region name(s)
  (no args -> the original 11 bundle regions; add --force to rebuild an already-done region)
  needs: rasterio xarray pandas numpy scipy pyogrio openpyxl
"""
import glob
import os
import sys
import time
import zipfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import monthly_loader as ML  # noqa: E402

PANEL = ML.PANEL_DIR
DR = r"D:\ndvi_drivers"
OUT = r"D:\human_drivers"
os.makedirs(OUT, exist_ok=True)
REGIONS = ["chihuahuan_desert", "mojave_desert", "kalahari_woodland", "taimyr_peninsula", "yamal_peninsula",
           "argentine_monte", "sahel", "mongolian_steppe", "great_sandy_desert_au", "central_chile", "thar_desert"]
YEARS = list(range(2002, 2024))
_IDX = {}  # cached global feature point-sets: name -> (lat[], lon[], value[])


def cells(region):
    f = sorted(glob.glob(os.path.join(PANEL, f"{region}_monthly_*.parquet")))[0]
    return pd.read_parquet(f, columns=["cell_id", "lon", "lat"]).groupby("cell_id", as_index=False).first()


def _balltree_km(flat, flon, clat, clon):
    """km from each cell (clat,clon) to nearest feature (flat,flon) via haversine BallTree."""
    from sklearn.neighbors import BallTree
    ok = np.isfinite(flat) & np.isfinite(flon)
    flat, flon = flat[ok], flon[ok]
    if len(flat) == 0:
        return np.full(len(clat), np.nan)
    t = BallTree(np.radians(np.c_[flat, flon]), metric="haversine")
    d, _ = t.query(np.radians(np.c_[clat, clon]), k=1)
    return d[:, 0] * 6371.0


# ---------- raster / scalar helpers ----------
def _sample_tif(path, lons, lats, band=1):
    """Fast nearest-sample: read only the cells' bbox window once, then vectorized row/col lookup."""
    import rasterio
    from rasterio.windows import from_bounds
    lons = np.asarray(lons, "float64"); lats = np.asarray(lats, "float64")
    with rasterio.open(path) as s:
        b = s.bounds
        win = from_bounds(max(lons.min() - 0.5, b.left), max(lats.min() - 0.5, b.bottom),
                          min(lons.max() + 0.5, b.right), min(lats.max() + 0.5, b.top),
                          s.transform).round_offsets().round_lengths()
        arr = s.read(band, window=win).astype("float64")
        wt = s.window_transform(win)
    rows, cols = rasterio.transform.rowcol(wt, lons, lats)
    rows, cols = np.asarray(rows), np.asarray(cols)
    h, w = arr.shape
    ok = (rows >= 0) & (rows < h) & (cols >= 0) & (cols < w)
    out = np.full(len(lons), np.nan)
    out[ok] = arr[rows[ok], cols[ok]]
    return out


# ---------- driver handlers (return cell-keyed frames) ----------
def d_gdp(cd):
    import rasterio
    p = os.path.join(DR, "gdp", "gdp_perCapita_1990_2024_v4.tif")
    with rasterio.open(p) as s:
        desc = {d: i + 1 for i, d in enumerate(s.descriptions) if d}
    rows = []
    for y in YEARS:
        b = desc.get(f"gdp_pc_{y}", y - 1990 + 1)
        rows.append(pd.DataFrame({"cell_id": cd.cell_id.values, "year": y,
                                  "gdp_pc": np.log1p(np.clip(_sample_tif(p, cd.lon, cd.lat, b), 0, None))}))
    return pd.concat(rows, ignore_index=True)


def d_ntl(cd):
    rows = []
    for y in YEARS:
        prod = "calDMSP" if y <= 2013 else "simVIIRS"
        p = os.path.join(DR, "lights", f"Harmonized_DN_NTL_{y}_{prod}.tif")
        rows.append(pd.DataFrame({"cell_id": cd.cell_id.values, "year": y,
                                  "ntl": np.log1p(np.clip(_sample_tif(p, cd.lon, cd.lat), 0, None))}))
    return pd.concat(rows, ignore_index=True)


def d_hdi(cd):
    import xarray as xr
    ds = xr.open_dataset(os.path.join(DR, "wealth", "HDI_1990_2015_v2.nc"))
    lo = xr.DataArray(cd.lon.values, dims="c"); la = xr.DataArray(cd.lat.values, dims="c")
    rows = []
    for y in YEARS:
        v = ds["HDI"].sel(time=min(y, 2015)).sel(longitude=lo, latitude=la, method="nearest").values
        rows.append(pd.DataFrame({"cell_id": cd.cell_id.values, "year": y, "hdi": v}))
    ds.close()
    return pd.concat(rows, ignore_index=True)


def d_luh2(cd):
    import xarray as xr
    ds = xr.open_dataset(os.path.join(DR, "landuse", "LUH2-GCB2025_states.nc"), chunks={"time": 1}, decode_times=False)
    lo = xr.DataArray(cd.lon.values, dims="c"); la = xr.DataArray(cd.lat.values, dims="c")
    grp = {"luh2_cropland": ["c3ann", "c4ann", "c3per", "c4per", "c3nfx"], "luh2_pasture": ["pastr"],
           "luh2_range": ["range"], "luh2_urban": ["urban"], "luh2_forest": ["primf", "secdf"],
           "luh2_secondary": ["secdf", "secdn"]}
    rows = []
    for y in YEARS:
        sl = ds.isel(time=y - 850)
        d = pd.DataFrame({"cell_id": cd.cell_id.values, "year": y})
        for col, vs in grp.items():
            tot = None
            for v in vs:
                a = sl[v].sel(lon=lo, lat=la, method="nearest").values
                tot = a if tot is None else tot + a
            d[col] = tot
        rows.append(d)
    ds.close()
    return pd.concat(rows, ignore_index=True)


def d_fert(cd):
    import rasterio
    z = os.path.join(DR, "fertilizer", "Lu-Tian_2016_NP_fertilizer.zip")
    rows = []
    for y in YEARS:
        yy = min(y, 2013)
        out = {"cell_id": cd.cell_id.values, "year": y}
        for var, pre in [("fert_n", "Nfer_ASCII/nfery"), ("fert_p", "Pfer_ASCII/pfery")]:
            a = _sample_tif(f"/vsizip/{z}/Lu-Tian_2016/{pre}{yy}.asc", cd.lon, cd.lat)
            a[a <= -9998] = np.nan
            out[var] = a
        rows.append(pd.DataFrame(out))
    return pd.concat(rows, ignore_index=True)


# AGLW annual livestock: (file-prefix, out-col, FAO Livestock-Unit weight). NEW true-annual (2002-2023,
# FAOSTAT-disaggregated GLW) density [head/km2] upgrade of the panel's static livestock_*_per_km2 (adds buffalo).
# LSU weights MATCH the panel's livestock_total_lsu_per_km2 (cattle 1.0 / horse 0.8 / sheep,goat 0.1); buffalo has
# no standard LSU coeff -> treated as a large bovine = cattle (1.0). => aglw_total_lsu is comparable to the panel total.
SPECIES = [("Cattl", "aglw_cattle", 1.00), ("Buffa", "aglw_buffalo", 1.00), ("Horse", "aglw_horse", 0.80),
           ("Sheep", "aglw_sheep", 0.10), ("Goats", "aglw_goats", 0.10)]


def d_livestock(cd):
    rows = []
    for y in YEARS:
        out = {"cell_id": cd.cell_id.values, "year": y}
        lsu = None
        for sp, col, w in SPECIES:
            a = np.nan_to_num(np.clip(_sample_tif(os.path.join(DR, "livestock_aglw", f"{sp}_{y}.tif"),
                                                  cd.lon, cd.lat), 0, None), nan=0.0)     # nodata/absent species -> 0 density
            out[col] = np.log1p(a)
            lsu = w * a if lsu is None else lsu + w * a
        out["aglw_total_lsu"] = np.log1p(lsu)                                # LSU-weighted total grazing pressure
        rows.append(pd.DataFrame(out))
    return pd.concat(rows, ignore_index=True)


def d_road(cd):
    p = f"/vsizip/{os.path.join(DR, 'infrastructure', 'GRIP4_density_total.zip')}/grip4_total_dens_m_km2.asc"
    a = _sample_tif(p, cd.lon, cd.lat); a[a <= -9998] = np.nan
    return pd.DataFrame({"cell_id": cd.cell_id.values, "road_density": np.log1p(np.clip(a, 0, None))})


def d_travel(cd):
    p = (f"/vsizip/{os.path.join(DR, 'infrastructure', 'travel_time_to_cities_2015.zip')}"
         "/2015_accessibility_to_cities_v1.0.tif")
    a = _sample_tif(p, cd.lon, cd.lat); a[a <= -9998] = np.nan
    return pd.DataFrame({"cell_id": cd.cell_id.values, "travel_time": np.log1p(np.clip(a, 0, None))})


def _pts_powerplants():
    df = pd.read_csv(os.path.join(DR, "energy", "global_power_plant_database.csv"),
                     usecols=["latitude", "longitude", "primary_fuel"], low_memory=False)
    return df


def d_powerplant(cd):
    df = _IDX.setdefault("pp", _pts_powerplants())
    th = df[df.primary_fuel.isin(["Coal", "Gas", "Oil"])]
    return pd.DataFrame({"cell_id": cd.cell_id.values,
                         "dist_powerplant": _balltree_km(df.latitude.values, df.longitude.values, cd.lat.values, cd.lon.values),
                         "dist_thermal": _balltree_km(th.latitude.values, th.longitude.values, cd.lat.values, cd.lon.values)})


def d_coalmine(cd):
    def load():
        p = glob.glob(os.path.join(DR, "energy", "gem_coal_mine", "*Coal Mine Tracker*.xlsx"))[0]
        x = pd.read_excel(p, sheet_name="Non-closed mines")
        latc = [c for c in x.columns if str(c).strip().lower() == "latitude"][0]
        lonc = [c for c in x.columns if str(c).strip().lower() == "longitude"][0]
        return pd.to_numeric(x[latc], errors="coerce").values, pd.to_numeric(x[lonc], errors="coerce").values
    la, lo = _IDX.setdefault("mine", load())
    return pd.DataFrame({"cell_id": cd.cell_id.values, "dist_coal_mine": _balltree_km(la, lo, cd.lat.values, cd.lon.values)})


def _gdw():
    import pyogrio
    z = os.path.join(DR, "water", "GDW_v1_shp.zip")
    bar = pyogrio.read_dataframe(f"/vsizip/{z}/GDW_v1_0_shp/GDW_barriers_v1_0.shp", columns=[])
    res = pyogrio.read_dataframe(f"/vsizip/{z}/GDW_v1_0_shp/GDW_reservoirs_v1_0.shp", columns=[])
    bc = bar.geometry.representative_point(); rc = res.geometry.representative_point()
    return (bc.y.values, bc.x.values, rc.y.values, rc.x.values)


def d_dams(cd):
    bla, blo, rla, rlo = _IDX.setdefault("gdw", _gdw())
    return pd.DataFrame({"cell_id": cd.cell_id.values,
                         "dist_dam": _balltree_km(bla, blo, cd.lat.values, cd.lon.values),
                         "dist_reservoir": _balltree_km(rla, rlo, cd.lat.values, cd.lon.values)})


def d_oilgas(cd):
    def load():
        import pyogrio
        g = pyogrio.read_dataframe(os.path.join(DR, "energy", "OGIM_v1.gpkg"),
                                   layer="Oil_and_Natural_Gas_Wells", columns=[])
        return g.geometry.y.values, g.geometry.x.values
    la, lo = _IDX.setdefault("ogim", load())
    return pd.DataFrame({"cell_id": cd.cell_id.values, "dist_oilgas_well": _balltree_km(la, lo, cd.lat.values, cd.lon.values)})


def d_wdpa(cd):
    def load():
        import pyogrio
        z = os.path.join(DR, "protected_areas", "WDPA_current_global.zip")
        gdb = f"/vsizip/{z}/WDPA_WDOECM_Jun2026_Public.gdb"
        _, b = pyogrio.read_bounds(gdb, layer="WDPA_WDOECM_poly_Jun2026")  # bbox only -> fast, no geometry decode
        return (b[1] + b[3]) / 2.0, (b[0] + b[2]) / 2.0                     # (lat centers, lon centers)
    la, lo = _IDX.setdefault("wdpa", load())
    return pd.DataFrame({"cell_id": cd.cell_id.values, "dist_pa": _balltree_km(la, lo, cd.lat.values, cd.lon.values)})


def d_ucdp(cd, idx):
    def load():
        z = os.path.join(DR, "conflict", "ucdp_ged261.csv.zip")
        zf = zipfile.ZipFile(z)
        name = [n for n in zf.namelist() if n.lower().endswith(".csv")][0]
        e = pd.read_csv(zf.open(name), usecols=["latitude", "longitude", "year", "date_start", "best", "where_prec"],
                        low_memory=False)
        e = e[e.where_prec <= 4]
        e["month"] = pd.to_datetime(e.date_start, errors="coerce").dt.month
        return e.dropna(subset=["latitude", "longitude", "month"])
    e = _IDX.setdefault("ucdp", load())
    # snap events to nearest cell of THIS region (BallTree over region cells), then aggregate
    from sklearn.neighbors import BallTree
    t = BallTree(np.radians(np.c_[cd.lat.values, cd.lon.values]), metric="haversine")
    d, j = t.query(np.radians(np.c_[e.latitude.values, e.longitude.values]), k=1)
    near = (d[:, 0] * 6371.0) < 50.0  # only events within 50km of a region cell
    ev = e[near].copy(); ev["cell_id"] = cd.cell_id.values[j[near, 0]]
    ev["month"] = ev["month"].astype(int)
    agg = ev.groupby(["cell_id", "year", "month"]).agg(conflict_events=("best", "size"),
                                                       conflict_deaths=("best", "sum")).reset_index()
    out = idx.merge(agg, on=["cell_id", "year", "month"], how="left")
    out[["conflict_events", "conflict_deaths"]] = out[["conflict_events", "conflict_deaths"]].fillna(0)
    return out[["cell_id", "year", "month", "conflict_events", "conflict_deaths"]]


def d_co2():
    p = os.path.join(DR, "co2", "co2_mm_gl.txt")
    df = pd.read_csv(p, sep=r"\s+", comment="#", header=None,
                     names=["year", "month", "decimal", "co2", "unc", "trend", "trend_unc"])
    return df[["year", "month", "co2"]]


def d_food():
    raw = pd.read_csv(os.path.join(DR, "prices", "fao_food_price_indices.csv"), header=None, skiprows=2)
    raw = raw.iloc[:, :7]
    raw.columns = ["date", "food_price_index", "food_meat", "food_dairy", "food_cereals", "food_oils", "food_sugar"]
    raw = raw.dropna(subset=["date"])
    dt = pd.to_datetime(raw["date"], errors="coerce")
    raw = raw[dt.notna()]; raw["year"] = dt[dt.notna()].dt.year; raw["month"] = dt[dt.notna()].dt.month
    for c in ["food_price_index", "food_meat", "food_dairy", "food_cereals", "food_oils", "food_sugar"]:
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    return raw[["year", "month"] + [c for c in raw.columns if c.startswith("food_")]]


STATIC = {"road": d_road, "travel": d_travel, "powerplant": d_powerplant, "coalmine": d_coalmine,
          "dams": d_dams, "oilgas": d_oilgas, "wdpa": d_wdpa}
ANNUAL = {"gdp": d_gdp, "ntl": d_ntl, "hdi": d_hdi, "luh2": d_luh2, "fert": d_fert, "livestock": d_livestock}


def required_sources():
    """{driver: [required source paths]} — single source of truth for the preflight checker (no path drift)."""
    E = os.path.join(DR, "energy"); INF = os.path.join(DR, "infrastructure")
    mine = glob.glob(os.path.join(E, "gem_coal_mine", "*Coal Mine Tracker*.xlsx"))
    return {
        "road": [os.path.join(INF, "GRIP4_density_total.zip")],
        "travel": [os.path.join(INF, "travel_time_to_cities_2015.zip")],
        "powerplant": [os.path.join(E, "global_power_plant_database.csv")],
        "coalmine": mine if mine else [os.path.join(E, "gem_coal_mine", "*Coal Mine Tracker*.xlsx")],
        "dams": [os.path.join(DR, "water", "GDW_v1_shp.zip")],
        "oilgas": [os.path.join(E, "OGIM_v1.gpkg")],
        "wdpa": [os.path.join(DR, "protected_areas", "WDPA_current_global.zip")],
        "gdp": [os.path.join(DR, "gdp", "gdp_perCapita_1990_2024_v4.tif")],
        "ntl": [os.path.join(DR, "lights", f"Harmonized_DN_NTL_{y}_{'calDMSP' if y <= 2013 else 'simVIIRS'}.tif")
                for y in YEARS],
        "hdi": [os.path.join(DR, "wealth", "HDI_1990_2015_v2.nc")],
        "luh2": [os.path.join(DR, "landuse", "LUH2-GCB2025_states.nc")],
        "fert": [os.path.join(DR, "fertilizer", "Lu-Tian_2016_NP_fertilizer.zip")],
        "livestock": [os.path.join(DR, "livestock_aglw", f"{sp}_{y}.tif") for sp, _, _ in SPECIES for y in YEARS],
        "ucdp": [os.path.join(DR, "conflict", "ucdp_ged261.csv.zip")],
        "co2": [os.path.join(DR, "co2", "co2_mm_gl.txt")],
        "food": [os.path.join(DR, "prices", "fao_food_price_indices.csv")],
    }


def output_columns():
    """{driver: [feature columns produced]} — sum = the human-driver feature count (excludes cell_id/year/month keys)."""
    return {
        "road": ["road_density"], "travel": ["travel_time"],
        "powerplant": ["dist_powerplant", "dist_thermal"], "coalmine": ["dist_coal_mine"],
        "dams": ["dist_dam", "dist_reservoir"], "oilgas": ["dist_oilgas_well"], "wdpa": ["dist_pa"],
        "gdp": ["gdp_pc"], "ntl": ["ntl"], "hdi": ["hdi"],
        "luh2": ["luh2_cropland", "luh2_pasture", "luh2_range", "luh2_urban", "luh2_forest", "luh2_secondary"],
        "fert": ["fert_n", "fert_p"],
        "livestock": ["aglw_cattle", "aglw_buffalo", "aglw_horse", "aglw_sheep", "aglw_goats", "aglw_total_lsu"],
        "ucdp": ["conflict_events", "conflict_deaths"], "co2": ["co2"],
        "food": ["food_price_index", "food_meat", "food_dairy", "food_cereals", "food_oils", "food_sugar"],
    }


def assemble_region(region):
    t0 = time.time()
    cd = cells(region)
    idx = pd.MultiIndex.from_product([cd.cell_id.values, YEARS, range(1, 13)],
                                     names=["cell_id", "year", "month"]).to_frame(index=False)
    print(f"\n=== {region}: {len(cd):,} cells ===", flush=True)

    def cache(tag, fn):
        p = os.path.join(OUT, f"{region}__{tag}.parquet")
        if os.path.exists(p):
            return pd.read_parquet(p)
        try:
            df = fn()
            df.to_parquet(p, index=False)
            print(f"  {tag:12s} ok ({time.time()-t0:.0f}s)", flush=True)
            return df
        except Exception as e:
            print(f"  {tag:12s} FAILED: {type(e).__name__}: {str(e)[:80]}", flush=True)
            return None

    g = idx.copy()
    for tag, fn in STATIC.items():
        d = cache(tag, lambda fn=fn: fn(cd))
        if d is not None:
            g = g.merge(d, on="cell_id", how="left")
    for tag, fn in ANNUAL.items():
        d = cache(tag, lambda fn=fn: fn(cd))
        if d is not None:
            g = g.merge(d, on=["cell_id", "year"], how="left")
    du = cache("ucdp", lambda: d_ucdp(cd, idx))
    if du is not None:
        g = g.merge(du, on=["cell_id", "year", "month"], how="left")
    for tag, fn in [("co2", d_co2), ("food", d_food)]:
        d = cache(tag, fn)
        if d is not None:
            g = g.merge(d, on=["year", "month"], how="left")

    out = os.path.join(OUT, f"{region}.parquet")
    g.to_parquet(out, index=False)
    print(f"  -> {out}  {g.shape}  ({time.time()-t0:.0f}s)", flush=True)


def _complete(r):
    """A region is done only if its merged parquet already carries the livestock columns (schema-aware skip).
    Regions built before livestock was added return False -> re-assembled, but cheaply: every other driver loads
    from its cached <region>__<driver>.parquet, so only livestock is actually computed before the re-merge."""
    p = os.path.join(OUT, f"{r}.parquet")
    if not os.path.exists(p):
        return False
    try:
        import pyarrow.parquet as pq
        names = set(pq.ParquetFile(p).schema.names)                         # metadata only, no data read
    except Exception:
        names = set(pd.read_parquet(p).columns)
    return "aglw_total_lsu" in names


def main():
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    if any(f in sys.argv for f in ("--all", "--train", "--test")):
        donors, test = ML.split_regions()
        regs = []
        if "--all" in sys.argv or "--train" in sys.argv:
            regs += list(donors)
        if "--all" in sys.argv or "--test" in sys.argv:
            regs += list(test)
    else:
        regs = only if only else REGIONS
    seen = set(); regs = [r for r in regs if not (r in seen or seen.add(r))]     # de-dup, keep order
    t_all = time.time(); n_run = n_done = n_skip = 0
    print(f"{len(regs)} regions to consider | out -> {OUT}\n", flush=True)
    for i, r in enumerate(regs, 1):
        if _complete(r) and "--force" not in sys.argv:
            print(f"[{i}/{len(regs)}] {r}: done (has livestock) -> skip", flush=True); n_done += 1; continue
        if not glob.glob(os.path.join(PANEL, f"{r}_monthly_*.parquet")):
            print(f"[{i}/{len(regs)}] {r}: no panel -> skip", flush=True); n_skip += 1; continue
        tag = "top-up livestock" if os.path.exists(os.path.join(OUT, f"{r}.parquet")) else "START"
        print(f"[{i}/{len(regs)}] {r}: {tag}", flush=True)
        assemble_region(r); n_run += 1
        el = time.time() - t_all; eta = (el / n_run) * (len(regs) - i)
        print(f"[{i}/{len(regs)}] {r}: DONE | {n_run} this run, {el/60:.0f}m elapsed, ~{eta/3600:.1f}h ETA", flush=True)
    print(f"\nALL DONE. {n_run} assembled this run, {n_done} already done, {n_skip} no-panel. Parquets in {OUT}")


if __name__ == "__main__":
    main()
