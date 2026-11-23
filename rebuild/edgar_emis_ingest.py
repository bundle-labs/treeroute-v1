"""Ingest EDGAR v8.1 anthropogenic emissions onto the panel's cells. The missing source term.

WHY. The panel's only anthropogenic signal is PROXIES -- nighttime lights, population, gdp, road
density, distance to a power plant. None of those is a quantity of pollutant released. PM2.5 is
emissions modulated by dispersion; the panel has dispersion in 78 monthly columns and nothing for
the source term. EDGAR is bottom-up (activity data x emission factor), so no aerosol observation
enters it -- a top-down INVERTED inventory would be a hard leak, this is not one.

PRECURSORS, NOT PRIMARY PM2.5. SO2 -> sulfate, NOx -> nitrate, NH3 -> ammonium (the driver of
European and Chinese secondary PM2.5, for which the panel has only fert_n and livestock counts),
plus BC and OC. EDGAR's own PM2.5 field is deliberately NOT taken by default: "PM2.5 emissions
predict PM2.5" reads badly even where it is legitimate, and it is the most suspect column in the
set. --with-pm25 adds it, and it should be the FIRST thing ablated.

ANNUAL, NOT MONTHLY, AND THE REASON IS CIRCULARITY. EDGAR distributes a monthly dimension, but it
is an annual total redistributed by country-level temporal profiles -- and the BUILDINGS seasonal
cycle is computed from ERA5 2 m temperature. Taking EDGAR monthly would inject this panel's own
meteorology back in through the source term. The twelve monthly layers are summed to an annual
total on the fly, in the same pass that decompresses them, and the monthly dimension is discarded.

LEAK STATUS: PHYSICS-UPSTREAM with a fitted second hop, and it is the weakest of the cleared
drivers. ACAG's GEOS-Chem consumes an anthropogenic inventory of this family, so EDGAR sits
upstream -- as a flux into a simulation, not as a GWR predictor. The second hop is real and must be
written down: the V5 GWR's own predictors include the SIMULATED RELATIVE CONTRIBUTIONS of sulfate,
nitrate, OC and SOA, so a sector-resolved precursor field is a partial reconstruction of the
calibration model's covariates. Rank this last, and test it against a scrambled-residual placebo
before believing any gain.

EMITTED PER AREA, NOT PER GRID CELL. The raw unit is Tonnes per 0.1-degree cell per month, which is
not comparable between latitudes -- a 0.1-degree cell at 60N has half the area of one at the
equator. Everything is converted to tonnes per km2 per year so the column means the same thing
everywhere.

2023 IS NOT IN EDGAR. The air-pollutant series stops at 2022; the 2025 fast-track release is
greenhouse gases only. 2022 is carried forward for test year 2023 and the carried rows are FLAGGED,
not silently duplicated. Inventories are smooth year to year and this is one of four test years.

    py -3.9 -u edgar_emis_ingest.py --plan     list what would be fetched, no download
    py -3.9 -u edgar_emis_ingest.py --smoke    one species, one sector, three years
    py -3.9 -u edgar_emis_ingest.py           all species and sectors, 2002-2023
"""
import io
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

BASE = ("https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/EDGAR/datasets/"
        "v81_FT2022_AP_new/monthly/%s/bkl_%s/bkl_%s_emi_nc.zip")
OUT = "D:/edgar_emis"
TMP = os.path.join(OUT, "_tmp")

SPECIES = ["SO2", "NOx", "NH3", "BC", "OC"]
PM25 = "PM2.5"
SECTORS = ["AGRICULTURE", "BUILDINGS", "FUEL_EXPLOITATION", "IND_COMBUSTION",
           "IND_PROCESSES", "POWER_INDUSTRY", "TRANSPORT", "WASTE"]
YEARS = list(range(2002, 2023))          # EDGAR AP ends 2022
CARRY_TO = 2023                          # 2022 carried forward, flagged
R_EARTH = 6371.0088                      # km


def log(m):
    print(m, flush=True)


def cell_area_km2(lat_edges_lo, lat_edges_hi, dlon_deg):
    """Area of a lat/lon box. Needed because Tonnes per 0.1-degree cell is not comparable
    between latitudes -- a cell at 60N has half the area of one at the equator."""
    return (R_EARTH ** 2 * np.radians(dlon_deg)
            * (np.sin(np.radians(lat_edges_hi)) - np.sin(np.radians(lat_edges_lo))))


def fetch(url, dest):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=900) as src, open(dest, "wb") as dst:
                nb = 0
                while True:
                    c = src.read(1 << 22)
                    if not c:
                        break
                    dst.write(c)
                    nb += len(c)
            return nb
        except Exception:
            if attempt == 3:
                raise
            time.sleep(4 * (attempt + 1))


def main():
    a = sys.argv[1:]
    smoke = "--smoke" in a
    species = SPECIES + ([PM25] if "--with-pm25" in a else [])
    sectors = SECTORS
    years = YEARS
    if smoke:
        species, sectors, years = ["SO2"], ["POWER_INDUSTRY"], [2015, 2016, 2017]
    os.makedirs(TMP, exist_ok=True)

    if "--plan" in a:
        log("species %s" % ", ".join(species))
        log("sectors %s" % ", ".join(sectors))
        log("years   %d-%d, then %d carried forward from 2022" % (years[0], years[-1], CARRY_TO))
        log("zips    %d x ~28 MB = ~%.2f GB"
            % (len(species) * len(sectors), len(species) * len(sectors) * 28e6 / 1e9))
        return 0

    grids = ing.region_grids()
    grids = {r: g for r, g in grids.items()
             if g["lat"].min() >= ing.GRID_LO and g["lat"].max() <= ing.GRID_HI}
    log("regions %d   cells %s"
        % (len(grids), format(sum(len(g["cell_id"]) for g in grids.values()), ",")))

    # EDGAR's 0.1 degree grid is COARSER than every panel cell (4.00 km at the equator down to
    # 1.45 km in Lapland), so each cell falls inside exactly one EDGAR pixel -- a lookup, not an
    # average. Index computed once; the grid is identical for every species, sector and year.
    elat = -89.95 + 0.1 * np.arange(1800)
    elon = -179.95 + 0.1 * np.arange(3600)
    area = cell_area_km2(elat - 0.05, elat + 0.05, 0.1)     # (1800,) km2 per row
    idx = {}
    for reg, g in grids.items():
        i = np.clip(np.round((g["lat"] - elat[0]) / 0.1).astype(int), 0, 1799)
        j = np.clip(np.round((g["lon"] - elon[0]) / 0.1).astype(int), 0, 3599)
        idx[reg] = (i, j)

    # region -> year -> species -> per-cell tonnes/km2/yr
    acc = {r: {y: {} for y in years} for r in grids}
    total_bytes = 0

    for sp in species:
        for sec in sectors:
            url = BASE % (sp, sec, sec)
            zpath = os.path.join(TMP, "%s_%s.zip" % (sp, sec))
            t0 = time.time()
            try:
                nb = fetch(url, zpath)
                total_bytes += nb
                z = zipfile.ZipFile(zpath)
                members = {}
                for n in z.namelist():
                    if not n.endswith(".nc"):
                        continue
                    for part in os.path.basename(n).split("_"):
                        if part.isdigit() and len(part) == 4:
                            members[int(part)] = n
                            break
                hit = 0
                for y in years:
                    nm = members.get(y)
                    if nm is None:
                        continue
                    import h5py
                    f = h5py.File(io.BytesIO(z.read(nm)), "r")
                    key = "emissions" if "emissions" in f else list(f.keys())[-1]
                    # SUM THE TWELVE MONTHS HERE, in the same pass that decompresses them. The
                    # monthly dimension is an annual total redistributed by country profiles, and
                    # the BUILDINGS profile is derived from ERA5 2 m temperature -- this panel's
                    # own driver. Discarding it here is the whole point.
                    ann = np.nansum(f[key][:], axis=0).astype(np.float64)   # (1800, 3600) Tonnes/yr
                    f.close()
                    dens = ann / area[:, None]                              # tonnes / km2 / yr
                    for reg, (i, j) in idx.items():
                        v = dens[i, j]
                        acc[reg][y][sp] = acc[reg][y].get(sp, 0.0) + v
                    hit += 1
                z.close()
                log("  %-6s %-18s %2d years  %5.1f MB  %5.1fs" % (sp, sec, hit, nb / 1e6,
                                                                  time.time() - t0))
            except Exception:
                log("  %-6s %-18s FAILED:\n%s" % (sp, sec, traceback.format_exc()[-400:]))
            finally:
                try:
                    os.remove(zpath)
                except Exception:
                    pass

    os.makedirs(OUT, exist_ok=True)
    nrow = 0
    for reg, g in grids.items():
        frames = []
        for y in years + [CARRY_TO]:
            src = 2022 if y == CARRY_TO else y
            d = pd.DataFrame({"cell_id": g["cell_id"], "year": np.int16(y),
                              "edgar_carried": np.int8(1 if y == CARRY_TO else 0)})
            for sp in species:
                col = "edgar_%s" % sp.lower().replace(".", "")
                v = acc[reg].get(src, {}).get(sp)
                d[col] = (np.full(len(g["cell_id"]), np.nan, np.float32)
                          if v is None else v.astype(np.float32))
            frames.append(d)
        out = pd.concat(frames, ignore_index=True)
        p = os.path.join(OUT, "%s_edgar.parquet" % reg)
        out.to_parquet(p, index=False, compression="zstd")
        nrow += len(out)

    log("")
    log("%.2f GB pulled   %s rows -> %s" % (total_bytes / 1e9, format(nrow, ","), OUT))
    log("NOTE: %d rows carry edgar_carried=1 (2022 values used for 2023; EDGAR AP ends 2022)."
        % (nrow // (len(years) + 1)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
