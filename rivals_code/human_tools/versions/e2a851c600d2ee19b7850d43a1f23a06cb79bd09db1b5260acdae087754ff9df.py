"""Generic downloader for the human-rival products (owner ruling AB, OWNER_RULINGS_2026-10-06.md:170-177).

Plain words:
  * One registry entry per APPROVED download (D0', D1, D2, D3, D4, D6). D5 is not approved and is not here.
  * Each product goes into its OWN folder D:/treeroute/human_products/<product>/<version>/ that must be new and
    empty on the first run. The folder holds only the downloaded files and product_manifest.json
    (source URL, exact request, file list, sizes, SHA-256, times). No script is ever written there.
  * Resumable per request: a file that is listed in the manifest AND whose SHA-256 still matches is skipped.
    Downloads go to "<file>.part" and are renamed only after they finish and pass a format check.
  * Free-disk check before every request; refuses below --min-free-gb (default 12 GB) after the request.
  * Copernicus products (D0', D1, D2, D3) use cdsapi with the OWNER'S OWN key file for that store:
    ~/.adsapirc for ADS (D1), ~/.ewdsapirc for EWDS (D0', D2, D3). If the file is missing the script refuses
    with a plain message. This script never opens, prints, copies or creates a key file; it only points
    cdsapi at the file (CDSAPI_RC) and checks the store URL cdsapi parsed.
  * --dry-run prints every request with its expected size and touches nothing (D4 asks the server for sizes
    with HEAD unless --no-network).

Run it isolated, because it reads (hashes) downloaded files:
    py -3.9 -I D:\\treeroute\\human_tools\\fetch_products.py --list
    py -3.9 -I D:\\treeroute\\human_tools\\fetch_products.py --dry-run D0p D1 D2 D3
    py -3.9 -I D:\\treeroute\\human_tools\\fetch_products.py --prepare-d6      # site-days from the coral store
    py -3.9 -I D:\\treeroute\\human_tools\\fetch_products.py --run D4
    py -3.9 -I D:\\treeroute\\human_tools\\fetch_products.py --run D6
    py -3.9 -I D:\\treeroute\\human_tools\\fetch_products.py --run D2            # owner command (EWDS key)
    py -3.9 -I D:\\treeroute\\human_tools\\fetch_products.py --prepare-d6 --d6-set v2
    py -3.9 -I D:\\treeroute\\human_tools\\fetch_products.py --run D6 --d6-set v2 --d6-server pifsc
  Owner commands with all options and expected sizes: D:\\treeroute\\human_tools\\DOWNLOAD_COMMANDS.md.

Added 2026-10-21 after the skeptic review: every run copies this script to versions\\<sha256>.py; keyed runs
refuse above the AB1 size bound x 1.10 unless --approved-gb is given; --probe-year (D0'); --timeout (HTTP);
D6 v2 (d* = C - g - 1, SST-cache pixel, train + test site-days, PIFSC).

Sources of every request (cite):
  D0'/D3  RIVALS_PLAN_HUMAN.md:157,160,169-173; research_fire.md:31-41 (start = 1st of M-5, daily leads
          150-184, members 0-24, 240 starts 2002-08..2022-07, FWI only, release 5).
  D1      RIVALS_PLAN_HUMAN.md:158; research_pm25.md:49-64,187 (one request, pm2p5, monthly mean, 2003-01..2023-12,
          global, netCDF).
  D2      RIVALS_PLAN_HUMAN.md:159; research_fire.md:20-29; fire_cems.py:198-204 (reanalysis, consolidated,
          system 4_1, grid 0.25, FWI only, 2003-2022, 5-year blocks).
  D4      RIVALS_PLAN_HUMAN.md:161; research_defo.md:59,101,123,174 (GADM 3.6, level 2, defo countries).
  D6      RIVALS_PLAN_HUMAN.md:162; research_coral.md:69,81-84,188-191 (ERDDAP NOAA_DHW point values at d*).
  Boxes   D:/fire/region_bbox.csv padded/snapped as fire_cems.py:96-105; merged under a 45-degree span cap
          (FIRE_EXPERIMENTS.md:180-184), by least added area.
Request keys checked against the public EWDS/ADS catalogue forms on 2026-10-21 (form.json of each dataset).
"""
import argparse
import datetime as _dt
import hashlib
import json
import os
import shutil
import sys
import time
import urllib.request

TOOLS = r"D:\treeroute\human_tools"
PRODUCTS_ROOT = r"D:\treeroute\human_products"
PROTECTED_LIST = r"D:\treeroute\registry\protected_roots.txt"
FIRE_BBOX = r"D:\fire\region_bbox.csv"
CORAL_STORE_LEAD0 = r"D:\treeroute\coral_build\coral_store\20261020_014201\lead_0.parquet"
D6_SITEDAYS = os.path.join(TOOLS, "d6_sitedays.csv")
D6_SITEDAYS_V2 = os.path.join(TOOLS, "d6_sitedays_v2.csv")
VERSIONS_DIR = os.path.join(TOOLS, "versions")
MANIFEST = "product_manifest.json"
# Approved size upper bounds in GB (owner ruling AB1, OWNER_RULINGS_2026-10-06.md:176). A keyed run refuses when
# its expected total is above bound x APPROVAL_SLACK (the expected sizes are themselves upper bounds), unless the
# owner re-approves a larger size and passes it with --approved-gb.
APPROVED_GB = {"D0p": 0.6, "D1": 0.12, "D2": 2.2, "D3": 6.3, "D4": 1.5}
APPROVAL_SLACK = 1.10
HOME = os.path.expanduser("~")
STORES = {
    "ads": {"rc": os.path.join(HOME, ".adsapirc"), "host": "ads.atmosphere.copernicus.eu",
            "name": "Atmosphere Data Store (ADS)"},
    "ewds": {"rc": os.path.join(HOME, ".ewdsapirc"), "host": "ewds.climate.copernicus.eu",
             "name": "Early Warning Data Store (EWDS)"},
}

# Measured bytes per value (upper bounds; compression and ocean masks make real files smaller).
BPV_HIST = 1.37e6 / (1826 * 15 * 19)    # D:/fire/cems/batch_test.log line A: 1.37 MB, 1826 d x 15 x 19 pts
BPV_SEAS = 3.9                           # research_fire.md:39 (seas_canadian_taiga_2019.nc, 14.7 MB)
SEAS_LEADS = list(range(150, 185))       # daily leads 150..184 (35 days), research_fire.md:34,39
GADM_COUNTRY_URL = "https://geodata.ucdavis.edu/gadm/gadm3.6/gpkg/gadm36_{iso}_gpkg.zip"
ERDDAP = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/NOAA_DHW"
D6_VARS = ["CRW_SST", "CRW_HOTSPOT", "CRW_DHW", "CRW_BAA", "CRW_BAA_7D_MAX"]
D6_N = 200

# D4 country list. Region boxes are read from disk (D:/monthly_panel/<region>_monthly_2010.parquet, the same
# file defo_ingest.py:99-104 reads; 42 regions = D:/defo_target/*.parquet). There is no country map on disk,
# so the candidate countries per box were assigned by hand from the box coordinates, generously at borders;
# gadm_coverage_check.py then proves every cell falls in a fetched country and flags fetched countries
# that no cell touches. Boxes (lat S..N, lon W..E) are printed by --list.
D4_REGION_COUNTRIES = {
    "amazon_basin_brazil": ["BRA"],
    "andes_puna": ["BOL", "PER", "CHL"],
    "angola_zambia_fire_belt": ["AGO", "ZMB", "COD"],
    "atlantic_forest_brazil": ["BRA"],
    "australian_bushfire_belt": ["AUS"],
    "bc_inland_rainforest": ["CAN"],
    "bolivia_beni_savanna": ["BOL", "BRA"],
    "borneo_peat_fires": ["IDN"],
    "borneo_rainforest": ["MYS", "IDN", "BRN"],
    "canadian_taiga": ["CAN"],
    "caucasus_highlands": ["RUS", "GEO", "AZE"],
    "congo_basin_drc": ["COD"],
    "costa_rica": ["CRI", "NIC", "PAN"],
    "eastern_us_deciduous": ["USA"],
    "gran_chaco": ["PRY", "BOL", "BRA", "ARG"],
    "greece_mainland": ["GRC", "ALB"],
    "idaho_montana_wildfire": ["USA"],
    "ireland": ["IRL", "GBR"],
    "japan_central_honshu": ["JPN"],
    "llanos_venezuela": ["VEN", "COL"],
    "miombo_woodland_zambia": ["ZMB", "COD", "MOZ"],
    "new_guinea_papua": ["PNG"],
    "new_zealand_fiordland": ["NZL"],
    "new_zealand_north_island": ["NZL"],
    "northeast_china_broadleaf": ["CHN", "PRK"],
    "northern_thailand": ["THA", "MMR", "LAO"],
    "pacific_nw_coast": ["USA", "CAN"],
    "pantanal": ["BRA", "BOL"],
    "pearl_river_delta": ["CHN", "HKG", "MAC"],
    "poland_central": ["POL", "CZE"],
    "russian_far_east_primorye": ["RUS", "CHN"],
    "siberian_taiga": ["RUS"],
    "southern_chile_rainforest": ["CHL", "ARG"],
    "tasmania_western": ["AUS"],
    "tierra_del_fuego": ["CHL", "ARG"],
    "tongass_alaska": ["USA", "CAN"],
    "trans_baikal_steppe": ["RUS", "MNG"],
    "vietnam_central_highlands": ["VNM", "LAO", "KHM"],
    "west_africa_monsoon_guinea": ["SLE", "GIN", "LBR"],
    "western_europe_temperate": ["FRA", "BEL", "LUX", "DEU", "CHE"],
    "western_scotland": ["GBR"],
    "yucatan_peninsula": ["MEX"],
}


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def now_iso():
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def gb(n):
    return n / 1e9


def human(n):
    if n is None:
        return "unknown"
    for unit, s in (("GB", 1e9), ("MB", 1e6), ("KB", 1e3)):
        if n >= s:
            return "%.2f %s" % (n / s, unit)
    return "%d B" % n


# ------------------------------------------------------------------------------------------------------------
# Fire boxes
# ------------------------------------------------------------------------------------------------------------
def fire_region_boxes():
    """Per-region [N, W, S, E], padded half a degree and snapped outward to 0.25 (fire_cems.py:96-105)."""
    import csv
    import math
    out = {}
    with open(FIRE_BBOX, newline="") as f:
        for r in csv.DictReader(f):
            N, W, S, E = (float(r[k]) for k in ("N", "W", "S", "E"))
            out[r["region"]] = [math.ceil((N + 0.5) * 4) / 4, math.floor((W - 0.5) * 4) / 4,
                                math.floor((S - 0.5) * 4) / 4, math.ceil((E + 0.5) * 4) / 4]
    if len(out) != 40:
        raise SystemExit("expected 40 fire regions in %s, found %d" % (FIRE_BBOX, len(out)))
    return out


def npts(b, res):
    N, W, S, E = b
    return (int(round((N - S) / res)) + 1) * (int(round((E - W) / res)) + 1)


def merged_boxes(lim=45.0):
    """Agglomerative merge: join the pair whose union adds the fewest 0.25-degree points, while the union
    spans at most `lim` degrees in latitude and longitude. Deterministic (regions sorted, strict '<')."""
    bx = fire_region_boxes()

    def U(a, b):
        return [max(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2]), max(a[3], b[3])]

    cl = [{"b": list(bx[r]), "r": [r]} for r in sorted(bx)]
    while True:
        best = None
        for i in range(len(cl)):
            for j in range(i + 1, len(cl)):
                u = U(cl[i]["b"], cl[j]["b"])
                if u[0] - u[2] <= lim and u[3] - u[1] <= lim:
                    g = npts(u, .25) - npts(cl[i]["b"], .25) - npts(cl[j]["b"], .25)
                    if best is None or g < best[0]:
                        best = (g, i, j, u)
        if best is None:
            break
        _, i, j, u = best
        cl[i] = {"b": u, "r": sorted(cl[i]["r"] + cl[j]["r"])}
        del cl[j]
    cl.sort(key=lambda c: c["r"][0])
    return {"box%02d" % (k + 1): c for k, c in enumerate(cl)}


def fire_boxes(mode):
    if mode == "merged":
        return {k: (v["b"], v["r"]) for k, v in merged_boxes().items()}
    return {r: (b, [r]) for r, b in sorted(fire_region_boxes().items())}


# ------------------------------------------------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------------------------------------------------
def seas_request(box, year, months):
    return {"variable": ["fire_weather_index"], "release_version": ["5"],
            "year": [str(year)], "month": ["%02d" % m for m in months], "day": ["01"],
            "leadtime_hour": [str(12 + 24 * k) for k in SEAS_LEADS],
            "area": box, "data_format": "netcdf"}


def seas_members(year):
    # GEFF-SEAS5: re-forecasts to 2016 have 25 members, real-time 2017 on has 51 (research_fire.md:31).
    # The form has no member selector, so all members come; members 0-24 are kept at processing time.
    return 25 if year <= 2016 else 51


def seas_bytes(box, year, nstart):
    return int(npts(box, 1.0) * nstart * len(SEAS_LEADS) * seas_members(year) * BPV_SEAS)


def d3_starts():
    """240 monthly starts 2002-08 .. 2022-07, grouped by calendar year (one request per box and year)."""
    out = []
    for y in range(2002, 2023):
        ms = [m for m in range(1, 13) if (y, m) >= (2002, 8) and (y, m) <= (2022, 7)]
        out.append((y, ms))
    assert sum(len(m) for _, m in out) == 240
    return out


def spec_D0p(opts):
    boxes = merged_boxes()
    name = max(sorted(boxes), key=lambda k: npts(boxes[k]["b"], 1.0))
    b, regs = boxes[name]["b"], boxes[name]["r"]
    year = opts.probe_year           # 2016 (25 members, re-forecast); a year >= 2017 times the 51-member requests
    req = seas_request(b, year, list(range(1, 13)))
    return {
        "key": "D0p", "label": "D0' SEAS5 timing probe", "product": "cems_fire_seasonal_probe",
        "version": "geff_seas5_r5_fwi_%s_%d" % (name, year), "kind": "copernicus", "store": "ewds",
        "dataset": "cems-fire-seasonal",
        "source_url": "https://ewds.climate.copernicus.eu/datasets/cems-fire-seasonal",
        "licence": "CC-BY-4.0 (accept on the EWDS dataset page)",
        "note": "ONE full-size merged-box request: the largest merged box (%s, %d regions), 12 starts of %d, "
                "daily leads 150-184, %d members (%s). Times the EWDS queue for D3 "
                "(RIVALS_PLAN_HUMAN.md:157,169-173)." % (name, len(regs), year, seas_members(year),
                                                         "re-forecast year" if year <= 2016 else
                                                         "real-time year, all 51 members arrive"),
        "requests": [{"id": "%s_%d" % (name, year), "file": "seas_%s_%d.nc" % (name, year),
                      "request": req, "expected_bytes": seas_bytes(b, year, 12), "regions": regs,
                      "check": "netcdf"}],
    }


def spec_D1(opts):
    req = {"variable": ["particulate_matter_2.5um"], "product_type": ["monthly_mean"],
           "year": [str(y) for y in range(2003, 2024)], "month": ["%02d" % m for m in range(1, 13)],
           "data_format": "netcdf_zip"}
    return {
        "key": "D1", "label": "D1 CAMS EAC4 monthly PM2.5", "product": "cams_eac4_monthly_pm2p5",
        "version": "eac4_monthly_mean_2003-2023", "kind": "copernicus", "store": "ads",
        "dataset": "cams-global-reanalysis-eac4-monthly",
        "source_url": "https://ads.atmosphere.copernicus.eu/datasets/cams-global-reanalysis-eac4-monthly",
        "licence": "CC-BY-4.0 / CAMS licence (accept on the ADS dataset page)",
        "note": "One request, pm2p5 monthly mean, 2003-01..2023-12, global 0.75 deg, netCDF (zipped; the ADS "
                "form offers grib or netcdf_zip).",
        "requests": [{"id": "pm2p5_2003-2023", "file": "eac4_pm2p5_monthly_2003-2023.zip", "request": req,
                      "expected_bytes": int(252 * 480 * 241 * 4), "check": "zip"}],
    }


BOX_NOTE = {
    "merged": "Merged boxes: 10 boxes, 119,032 points at 0.25 deg, against the plan's ~114,165 (+4.3%) because the "
              "merge rule differs (fewest added points per join here; the plan used a greedy merge, "
              "RIVALS_PLAN_HUMAN.md:166, FIRE_EXPERIMENTS.md:180-184). Harmless: every fire region box is inside "
              "its merged box; only the download is slightly larger.",
    "region": "Per-region boxes: one box per fire region (40), padded half a degree and snapped to 0.25 "
              "(fire_cems.py:96-105).",
}


def spec_D2(opts):
    mode = opts.boxes
    blocks = [list(range(y, y + 5)) for y in (2003, 2008, 2013, 2018)]
    reqs = []
    for name, (b, regs) in fire_boxes(mode).items():
        for blk in blocks:
            ndays = (_dt.date(blk[-1], 12, 31) - _dt.date(blk[0], 1, 1)).days + 1
            req = {"product_type": ["reanalysis"], "variable": ["fire_weather_index"],
                   "dataset_type": "consolidated_dataset", "system_version": ["4_1"],
                   "year": [str(y) for y in blk], "month": ["%02d" % m for m in range(1, 13)],
                   "day": ["%02d" % d for d in range(1, 32)], "grid": "0.25/0.25", "area": b,
                   "data_format": "netcdf"}
            reqs.append({"id": "%s_%d-%d" % (name, blk[0], blk[-1]),
                         "file": "hist_%s_%d-%d.nc" % (name, blk[0], blk[-1]), "request": req,
                         "expected_bytes": int(npts(b, .25) * ndays * BPV_HIST), "regions": regs,
                         "check": "netcdf"})
    return {
        "key": "D2", "label": "D2 CEMS GEFF-ERA5 FWI", "product": "cems_fire_historical_fwi",
        "version": "geff_era5_v4_1_consolidated_fwi_2003-2022_%s" % mode, "kind": "copernicus",
        "store": "ewds", "dataset": "cems-fire-historical-v1",
        "source_url": "https://ewds.climate.copernicus.eu/datasets/cems-fire-historical-v1",
        "licence": "CC-BY-4.0 (accept on the EWDS dataset page)",
        "note": "FWI only, reanalysis, consolidated, system 4_1, 0.25 deg, 2003-2022 in 5-year blocks, %s boxes "
                "(measured 1,590 s per 5-year request, batch_test.log line A). %s" % (mode, BOX_NOTE[mode]),
        "requests": reqs,
    }


def spec_D3(opts):
    mode, ypr = opts.boxes, max(1, opts.seas_years_per_request)
    starts = d3_starts()
    groups = [starts[i:i + ypr] for i in range(0, len(starts), ypr)]
    reqs = []
    for name, (b, regs) in fire_boxes(mode).items():
        for g in groups:
            # One request per calendar year of starts (the form crosses year x month, so a request may not
            # mix the partial first/last years with full ones). ypr > 1 is only legal for full years.
            if ypr > 1 and any(len(ms) != 12 for _, ms in g):
                for y, ms in g:
                    reqs.append(_seas_req(name, b, regs, [(y, ms)]))
            else:
                reqs.append(_seas_req(name, b, regs, g))
    return {
        "key": "D3", "label": "D3 CEMS GEFF-SEAS5 FWI", "product": "cems_fire_seasonal_fwi",
        "version": "geff_seas5_r5_fwi_starts200208-202207_L150-184_%s_y%d" % (mode, ypr), "kind": "copernicus",
        "store": "ewds", "dataset": "cems-fire-seasonal",
        "source_url": "https://ewds.climate.copernicus.eu/datasets/cems-fire-seasonal",
        "licence": "CC-BY-4.0 (accept on the EWDS dataset page)",
        "note": "FWI only, release 5, 240 starts 2002-08..2022-07 (day 01), daily leads 150-184 "
                "(leadtime_hour 3612..4428), %s boxes. All members arrive (25 to 2016, 51 from 2017); members "
                "0-24 are kept at processing (research_fire.md:37). %s" % (mode, BOX_NOTE[mode]),
        "requests": reqs,
    }


def _seas_req(name, b, regs, g):
    years = [y for y, _ in g]
    months = g[0][1]
    req = seas_request(b, years[0], months)
    req["year"] = [str(y) for y in years]
    tag = "%d" % years[0] if len(years) == 1 else "%d-%d" % (years[0], years[-1])
    nbytes = sum(seas_bytes(b, y, len(ms)) for y, ms in g)
    return {"id": "%s_%s" % (name, tag), "file": "seas_%s_%s.nc" % (name, tag), "request": req,
            "expected_bytes": nbytes, "regions": regs, "check": "netcdf",
            "starts": sum(len(ms) for _, ms in g)}


def spec_D4(opts):
    isos = sorted({c for v in D4_REGION_COUNTRIES.values() for c in v})
    reqs = []
    for iso in isos:
        url = GADM_COUNTRY_URL.format(iso=iso)
        regs = sorted(r for r, v in D4_REGION_COUNTRIES.items() if iso in v)
        reqs.append({"id": iso, "file": "gadm36_%s_gpkg.zip" % iso, "url": url, "expected_bytes": None,
                     "regions": regs, "check": "zip"})
    return {
        "key": "D4", "label": "D4 GADM 3.6 level 2 (defo countries)", "product": "gadm",
        "version": "3.6_gpkg_defo42", "kind": "http", "store": None, "dataset": "GADM 3.6 country GeoPackage",
        "source_url": "https://gadm.org/download_country_v3.html (files on geodata.ucdavis.edu/gadm/gadm3.6)",
        "licence": "GADM: free for academic / non-commercial use, no redistribution (https://gadm.org/license.html)",
        "note": "GADM 3.6 is published per country as one GeoPackage holding every level (0..n); level 2 is "
                "the layer gadm36_<ISO>_2. %d countries for the 42 defo regions (country list: hand-assigned "
                "from the region boxes, verified by gadm_coverage_check.py)." % len(isos),
        "requests": reqs,
    }


def spec_D6(opts):
    if opts.d6_set == "v2":
        return spec_D6_v2(opts)
    import csv
    if not os.path.exists(D6_SITEDAYS):
        raise SystemExit("D6 needs %s; build it first with --prepare-d6" % D6_SITEDAYS)
    reqs = []
    server = opts.d6_server
    with open(D6_SITEDAYS, newline="") as f:
        for r in csv.DictReader(f):
            t = "%sT12:00:00Z" % r["day"]
            sel = "[(%s)][(%s)][(%s)]" % (t, r["lat"], r["lon"])
            base = {"row_id": r["row_id"], "lat": float(r["lat"]), "lon": float(r["lon"]), "day": r["day"],
                    "check": "erddap_csv", "expected_bytes": 400}
            if server == "pfeg":
                url = "%s.csv?%s" % (ERDDAP, ",".join(v + sel for v in D6_VARS))
                reqs.append(dict(base, id=r["n"], file="dhw_%s.csv" % r["n"], url=url))
            else:
                # PIFSC grids run 0..360 east (actual_range 0.025..359.975); -72.2 asked as 287.8 (404 otherwise)
                sel360 = "[(%s)][(%s)][(%.4f)]" % (t, r["lat"], float(r["lon"]) % 360.0)
                for tag, (ds, var) in PIFSC_D6.items():
                    url = "%s/%s.csv?%s%s" % (PIFSC_ERDDAP, ds, var, sel360)
                    reqs.append(dict(base, id="%s_%s" % (r["n"], tag), file="crw_%s_%s.csv" % (r["n"], tag),
                                     url=url))
    if server == "pfeg":
        dataset, src, ver = ("ERDDAP griddap NOAA_DHW (CRW 5 km v3.1)",
                             "https://coastwatch.pfeg.noaa.gov/erddap/info/NOAA_DHW/index.html", "")
        what = ",".join(D6_VARS)
    else:
        dataset = "ERDDAP griddap %s (CRW 5 km, product_version 3.1; NOAA PIFSC OceanWatch mirror)" % ",".join(
            ds for ds, _ in PIFSC_D6.values())
        src, ver = "https://oceanwatch.pifsc.noaa.gov/erddap/griddap/CRW_dhw_v1_0.html", "_pifsc"
        what = ",".join(var for _, var in PIFSC_D6.values())
    return {
        "key": "D6", "label": "D6 NOAA CRW DHW site-days (%s)" % server, "product": "noaa_crw_dhw_sitedays",
        "version": "v3.1_train_sitedays_n%d%s" % (len(reqs) // (1 if server == "pfeg" else len(PIFSC_D6)), ver),
        "kind": "http", "store": None, "dataset": dataset, "source_url": src,
        "licence": "NOAA CRW: public, no restriction; credit requested",
        "note": "Point values of %s at the 0.05-deg pixel ERDDAP picks for the site's own coordinates, on the "
                "store's feature_end day. CAUTION: feature_end is the latest of all window ends "
                "(SPEC_CORAL_TABLES.md:170-173), not always d* = C-g-1 (research_coral.md:83): 40 of the 200 "
                "days are one day after d*, and 3 sites sit on a pixel edge. Use this set only as a plain check "
                "date (compute our DHW at the same day and pixel); the corrected set is D6 --d6-set v2. "
                "Site-days stride-picked from the coral store's TRAIN rows (locations and dates only, no labels): "
                "%s." % (what, D6_SITEDAYS),
        "requests": reqs,
    }


def spec_D6_v2(opts):
    """D6 v2: corrected day d* = C - g - 1, the SST cache's own pixel, train AND test site-days, PIFSC only."""
    import csv
    if not os.path.exists(D6_SITEDAYS_V2):
        raise SystemExit("D6 v2 needs %s; build it first with --prepare-d6 --d6-set v2" % D6_SITEDAYS_V2)
    if opts.d6_server != "pifsc":
        raise SystemExit("D6 v2 is fetched from the PIFSC server only (pass --d6-server pifsc)")
    reqs = []
    with open(D6_SITEDAYS_V2, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        t = "%sT12:00:00Z" % r["day"]
        sel360 = "[(%s)][(%s)][(%s)]" % (t, r["px_lat"], "%.3f" % (float(r["px_lon"]) % 360.0))
        for tag, (ds, var) in PIFSC_D6_V2.items():
            url = "%s/%s.csv?%s%s" % (PIFSC_ERDDAP, ds, var, sel360)
            reqs.append({"row_id": r["row_id"], "mark": r["mark"], "lat": float(r["lat"]), "lon": float(r["lon"]),
                         "px_lat": float(r["px_lat"]), "px_lon": float(r["px_lon"]), "day": r["day"],
                         "check": "erddap_csv", "expected_bytes": 400, "id": "%s_%s" % (r["n"], tag),
                         "file": "crw_%s_%s.csv" % (r["n"], tag), "url": url})
    ntr = sum(r["mark"] == "train" for r in rows)
    nte = sum(r["mark"] == "test" for r in rows)
    return {
        "key": "D6", "label": "D6 NOAA CRW DHW site-days v2 (pifsc)", "product": "noaa_crw_dhw_sitedays",
        "version": "v3.1_sitedays_v2_train%d_test%d_pifsc" % (ntr, nte),
        "kind": "http", "store": None,
        "dataset": "ERDDAP griddap %s (CRW 5 km, product_version 3.1; NOAA PIFSC OceanWatch, the server our SST "
                   "came from, coral_fetch_sst.py:42)" % ",".join(ds for ds, _ in PIFSC_D6_V2.values()),
        "source_url": "https://oceanwatch.pifsc.noaa.gov/erddap/griddap/CRW_dhw_v1_0.html",
        "licence": "NOAA CRW: public, no restriction; credit requested",
        "note": "Point values of %s at day d* = C - g - 1 with g = 1 (research_coral.md:83; "
                "SPEC_CORAL_TABLES.md:163-168): d* = issue_date - 2 on day-precision rows (issue - feature_end "
                "of 1-2 days) and the first day of the issue month - 2 on month-precision rows (gap 28+ days), "
                "computed by --prepare-d6 --d6-set v2. Queried at the SST cache's own pixel centre, reproduced "
                "with the cache's float rule (coral_fetch_sst_full.py:134-139), so no edge site can land on a "
                "neighbour pixel; analysed_sst at that pixel is fetched too so the compare can prove the pixel "
                "(it must equal our cached SST). %d train + %d test site-days, stride-picked from the coral store "
                "(row_id, lat, lon, target/issue date, feature_end, mark only; no label is read; rule H16 bans test "
                "scores, not test coordinates): %s." % (",".join(v for _, v in PIFSC_D6_V2.values()), ntr, nte,
                                                        D6_SITEDAYS_V2),
        "requests": reqs,
    }


# NOAA PIFSC OceanWatch serves the same CRW v3.1 daily grids (attribute product_version "3.1"); it is the server
# the coral SST already came from (coral_fetch_sst.py:42). Used only when pfeg NOAA_DHW is unavailable.
PIFSC_ERDDAP = "https://oceanwatch.pifsc.noaa.gov/erddap/griddap"
PIFSC_D6 = {"dhw": ("CRW_dhw_v1_0", "degree_heating_week"),
            "baa7d": ("CRW_baa_max_7d_v1_0", "bleaching_alert_area"),
            "hs": ("CRW_hs_v1_0", "hotspot")}
PIFSC_D6_V2 = dict(PIFSC_D6, sst=("CRW_sst_v3_1", "analysed_sst"))


REGISTRY = {"D0p": spec_D0p, "D1": spec_D1, "D2": spec_D2, "D3": spec_D3, "D4": spec_D4, "D6": spec_D6}
ALIASES = {"D0'": "D0p", "D0P": "D0p", "D0": "D0p"}


# ------------------------------------------------------------------------------------------------------------
# Safety helpers
# ------------------------------------------------------------------------------------------------------------
def norm(p):
    return os.path.normcase(os.path.abspath(p))


def protected_roots():
    out = []
    if os.path.exists(PROTECTED_LIST):
        with open(PROTECTED_LIST) as f:
            out = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    return out + [r"D:\treeroute\rivals_build", r"D:\coral", r"D:\fire"]


def assert_writable(path):
    p = norm(path)
    root = norm(PRODUCTS_ROOT)
    if os.path.commonpath([p, root]) != root:
        raise SystemExit("REFUSED: %s is outside %s" % (path, PRODUCTS_ROOT))
    for pr in protected_roots():
        q = norm(pr)
        if os.path.commonpath([p, q]) == q:
            raise SystemExit("REFUSED: %s is inside protected root %s" % (path, pr))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def free_bytes(path):
    d = path
    while not os.path.exists(d):
        d = os.path.dirname(d)
    return shutil.disk_usage(d).free


def check_format(path, kind):
    with open(path, "rb") as f:
        head = f.read(512)
    if kind == "netcdf":
        ok = head[:3] == b"CDF" or head[:8] == b"\x89HDF\r\n\x1a\n" or head[:4] == b"GRIB"
    elif kind == "zip":
        ok = head[:4] == b"PK\x03\x04"
    elif kind == "erddap_csv":
        ok = head.startswith(b"time,latitude,longitude,")
    else:
        ok = True
    if not ok:
        raise RuntimeError("downloaded file is not the expected format (%s); first bytes %r" % (kind, head[:40]))


def load_manifest(folder):
    p = os.path.join(folder, MANIFEST)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_manifest(folder, man):
    p = os.path.join(folder, MANIFEST)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(man, f, indent=1)
    os.replace(tmp, p)


def prepare_folder(spec):
    folder = os.path.join(PRODUCTS_ROOT, spec["product"], spec["version"])
    assert_writable(folder)
    if not os.path.exists(folder):
        os.makedirs(folder)
        log("new empty folder %s" % folder)
        return folder
    man = load_manifest(folder)
    present = set(os.listdir(folder))
    if man is None:
        if present:
            raise SystemExit("REFUSED: %s exists, is not empty and has no %s" % (folder, MANIFEST))
        return folder
    allowed = {MANIFEST} | {r["file"] for r in spec["requests"]} | {r["file"] + ".part" for r in spec["requests"]}
    extra = sorted(present - allowed)
    if extra:
        raise SystemExit("REFUSED: %s holds files this product never writes: %s" % (folder, extra[:10]))
    log("resuming in %s" % folder)
    return folder


def tool_fingerprint():
    me = os.path.abspath(__file__)
    return {"path": me, "sha256": sha256_file(me), "python": sys.version.split()[0],
            "isolated_mode": bool(sys.flags.isolated)}


# ------------------------------------------------------------------------------------------------------------
# Fetchers
# ------------------------------------------------------------------------------------------------------------
def http_get(url, dst, timeout=120, tries=4):
    last = None
    for t in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "treeroute-human-products/1.0"})
            h = hashlib.sha256()
            n = 0
            with urllib.request.urlopen(req, timeout=timeout) as r, open(dst, "wb") as f:
                want = r.headers.get("Content-Length")
                final_url = r.geturl()
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
                    h.update(chunk)
                    n += len(chunk)
            if want is not None and int(want) != n:
                raise RuntimeError("short read: %d of %s bytes" % (n, want))
            return n, h.hexdigest(), final_url
        except Exception as e:                       # network errors: retry, then fail loud
            last = e
            if os.path.exists(dst):
                os.remove(dst)
            log("    try %d/%d failed: %s" % (t, tries, str(e)[:160]))
            time.sleep(5 * t)
    raise RuntimeError("download failed after %d tries: %s" % (tries, last))


def http_head_size(url, timeout=60):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "treeroute-human-products/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            v = r.headers.get("Content-Length")
            return int(v) if v is not None else None
    except Exception as e:
        log("    HEAD failed for %s: %s" % (url, str(e)[:120]))
        return None


def key_file_status(store):
    s = STORES[store]
    return os.path.exists(s["rc"]), s["rc"]


def copernicus_client(store):
    s = STORES[store]
    ok, rc = key_file_status(store)
    if not ok:
        raise SystemExit(
            "REFUSED: this product comes from the %s and needs the owner's own key file %s, which is missing.\n"
            "The owner creates it (two lines: 'url: https://%s/api' and 'key: <personal access token>' from the "
            "store's profile page) and accepts the dataset licence on the dataset page. This script never "
            "creates, reads or copies a key file." % (s["name"], rc, s["host"]))
    for v in ("CDSAPI_URL", "CDSAPI_KEY"):
        if v in os.environ:
            log("note: ignoring environment variable %s so the %s file decides the store" % (v, rc))
            os.environ.pop(v)
    os.environ["CDSAPI_RC"] = rc
    import cdsapi                                         # system site-packages; works under -I
    c = cdsapi.Client(quiet=False, progress=False, debug=False)
    url = getattr(c, "url", None)
    if not url or s["host"] not in str(url):
        raise SystemExit("REFUSED: the key file %s does not point at %s (cdsapi parsed url %r). The owner must "
                         "fix the 'url:' line." % (rc, s["host"], url))
    log("using %s (url from the owner's key file; key not read by this script)" % s["name"])
    return c


def keep_tool_version():
    """Copy this script to versions/<sha256>.py so the code behind every manifest's tool hash stays readable."""
    fp = tool_fingerprint()
    dst = os.path.join(VERSIONS_DIR, fp["sha256"] + ".py")
    if not os.path.exists(dst):
        os.makedirs(VERSIONS_DIR, exist_ok=True)
        shutil.copyfile(fp["path"], dst + ".tmp")
        if sha256_file(dst + ".tmp") != fp["sha256"]:
            raise SystemExit("REFUSED: copy of this script to %s does not hash back" % dst)
        os.replace(dst + ".tmp", dst)
        log("kept this tool version at %s" % dst)
    return dst


def approval_check(spec, opts):
    """Refuse a run whose expected size is above the owner's approved bound (AB1) x APPROVAL_SLACK."""
    cap = opts.approved_gb if opts.approved_gb else APPROVED_GB.get(spec["key"])
    if cap is None:
        return None
    exp = sum((r.get("expected_bytes") or 0) for r in spec["requests"]) / 1e9
    lim = cap * (1.0 if opts.approved_gb else APPROVAL_SLACK)
    msg = "%s expected %.2f GB; approved %.2f GB%s" % (spec["key"], exp, cap,
                                                      " (owner re-approval via --approved-gb)" if opts.approved_gb
                                                      else " (AB1) x %.2f slack = %.2f GB" % (APPROVAL_SLACK, lim))
    if exp > lim:
        return "OVER: " + msg
    return "ok: " + msg


def run_product(spec, opts):
    # Approval and key checks first, so a refused run leaves no folder behind.
    appr = approval_check(spec, opts)
    if appr and appr.startswith("OVER"):
        raise SystemExit(
            "REFUSED: %s.\nThe owner approved a smaller download (OWNER_RULINGS_2026-10-06.md:176). Either run the "
            "smaller option (for D3: --boxes region, 1.94 GB in 840 requests) or, after the owner re-approves the "
            "larger size, pass it explicitly, e.g. --approved-gb 8.3." % appr)
    if appr:
        log("size approval " + appr)
    tool_copy = keep_tool_version()
    client = copernicus_client(spec["store"]) if spec["kind"] == "copernicus" else None
    folder = prepare_folder(spec)
    man = load_manifest(folder) or {
        "product": spec["product"], "version": spec["version"], "label": spec["label"],
        "dataset": spec["dataset"], "source_url": spec["source_url"], "licence": spec["licence"],
        "store": spec["store"], "note": spec["note"], "created": now_iso(), "tool": tool_fingerprint(),
        "approval": "owner ruling AB1, OWNER_RULINGS_2026-10-06.md:176 ('yes to all, downloads approved')",
        "requests": {}, "files": {},
    }
    man.setdefault("runs", []).append({"started": now_iso(), "tool": tool_fingerprint(), "tool_copy": tool_copy,
                                       "argv": sys.argv[1:], "size_approval": appr})
    save_manifest(folder, man)
    reqs = spec["requests"][:opts.limit] if opts.limit else spec["requests"]
    n_new = n_skip = n_fail = streak = 0
    t00 = time.time()
    for i, r in enumerate(reqs, 1):
        dst = os.path.join(folder, r["file"])
        part = dst + ".part"
        rec = man["files"].get(r["file"])
        if rec and os.path.exists(dst):
            if os.path.getsize(dst) == rec["bytes"] and sha256_file(dst) == rec["sha256"]:
                n_skip += 1
                log("%s %d/%d %-34s done before (hash matches)" % (spec["key"], i, len(reqs), r["file"]))
                continue
            raise SystemExit("REFUSED: %s exists but its hash no longer matches the manifest" % dst)
        if os.path.exists(dst) and not rec:
            raise SystemExit("REFUSED: %s exists but is not in the manifest; inspect it by hand" % dst)
        if os.path.exists(part):
            os.remove(part)                                  # our own unfinished download
        if r.get("expected_bytes") is None and spec["kind"] == "http":
            r["expected_bytes"] = http_head_size(r["url"])
        need = r.get("expected_bytes") or 0
        free = free_bytes(folder)
        if free - need < opts.min_free_gb * 1e9:
            raise SystemExit("REFUSED: D: has %.1f GB free; this request may need %.2f GB and the margin is %.0f GB"
                             % (gb(free), gb(need), opts.min_free_gb))
        man["requests"][r["id"]] = {k: v for k, v in r.items() if k not in ("check",)}
        t0 = time.time()
        started = now_iso()
        log("%s %d/%d %-34s requesting (expected %s, D: free %.1f GB)"
            % (spec["key"], i, len(reqs), r["file"], human(r.get("expected_bytes")), gb(free)))
        try:
            if spec["kind"] == "copernicus":
                client.retrieve(spec["dataset"], r["request"], part)
                nbytes = os.path.getsize(part)
                digest = sha256_file(part)
                served = spec["source_url"]
            else:
                nbytes, digest, served = http_get(r["url"], part, timeout=opts.timeout)
            check_format(part, r["check"])
            os.replace(part, dst)
        except SystemExit:
            raise
        except Exception as e:
            n_fail += 1
            if os.path.exists(part):
                os.remove(part)
            log("%s %d/%d %-34s FAILED: %s" % (spec["key"], i, len(reqs), r["file"], str(e)[:200]))
            streak += 1
            if streak >= opts.max_fail_streak:
                log("%d requests failed in a row: the server looks down; stopping (re-run later to resume)" % streak)
                break
            continue
        streak = 0
        el = time.time() - t0
        man["files"][r["file"]] = {"request_id": r["id"], "bytes": nbytes, "sha256": digest,
                                   "started": started, "finished": now_iso(), "seconds": round(el, 1),
                                   "served_by": served}
        save_manifest(folder, man)
        n_new += 1
        log("%s %d/%d %-34s %s in %.1f s sha256 %s" % (spec["key"], i, len(reqs), r["file"], human(nbytes), el,
                                                      digest[:16]))
        if spec["kind"] == "http" and opts.pause > 0:
            time.sleep(opts.pause)
    man["runs"][-1].update({"finished": now_iso(), "new": n_new, "skipped": n_skip, "failed": n_fail})
    tot = sum(v["bytes"] for v in man["files"].values())
    man["total_bytes"] = tot
    man["complete"] = all(r["file"] in man["files"] for r in spec["requests"])
    save_manifest(folder, man)
    log("%s finished: %d new, %d already done, %d failed, %d of %d files on disk, %s total, %.1f min"
        % (spec["key"], n_new, n_skip, n_fail, len(man["files"]), len(spec["requests"]), human(tot),
           (time.time() - t00) / 60))
    if n_fail:
        log("re-run the same command: finished files are skipped and only the failed ones retry")
        return 1
    return 0


# ------------------------------------------------------------------------------------------------------------
# Dry run, list, D6 preparation
# ------------------------------------------------------------------------------------------------------------
def dry_run(spec, opts):
    print("=" * 110)
    print("%s  ->  %s" % (spec["label"], os.path.join(PRODUCTS_ROOT, spec["product"], spec["version"])))
    print("  dataset   %s" % spec["dataset"])
    print("  source    %s" % spec["source_url"])
    print("  licence   %s" % spec["licence"])
    if spec["store"]:
        ok, rc = key_file_status(spec["store"])
        print("  key file  %s : %s" % (rc, "present" if ok else "MISSING -> a real run REFUSES until the owner "
                                                                "creates it"))
    print("  note      %s" % spec["note"])
    tot = 0
    unknown = 0
    for i, r in enumerate(spec["requests"], 1):
        size = r.get("expected_bytes")
        if size is None and spec["kind"] == "http" and not opts.no_network:
            size = http_head_size(r["url"])
        if size is None:
            unknown += 1
        else:
            tot += size
        what = json.dumps(r["request"], separators=(",", ":")) if "request" in r else r["url"]
        extra = (" regions=%s" % ",".join(r["regions"])) if r.get("regions") else ""
        print("  %4d  %-40s expect %-10s%s" % (i, r["file"], human(size), extra))
        print("        %s" % what)
    print("  TOTAL  %d requests, expected %s%s" % (len(spec["requests"]), human(tot),
                                                   (" (+%d unknown)" % unknown) if unknown else ""))
    appr = approval_check(spec, opts)
    if appr:
        print("  SIZE   %s%s" % (appr, "  -> a real run REFUSES" if appr.startswith("OVER") else ""))
    return len(spec["requests"]), tot


def do_list(opts):
    for k, f in REGISTRY.items():
        try:
            s = f(opts)
            print("%-4s %-40s %-9s %4d requests  -> %s\\%s\\%s" % (k, s["label"], s["store"] or "public",
                                                               len(s["requests"]), PRODUCTS_ROOT, s["product"],
                                                               s["version"]))
        except SystemExit as e:
            print("%-4s (not ready: %s)" % (k, e))
    print("\nfire boxes (%s):" % opts.boxes)
    for name, (b, regs) in fire_boxes(opts.boxes).items():
        print("  %-8s N%7.2f W%8.2f S%7.2f E%8.2f  pts0.25=%6d pts1=%5d  %s"
              % (name, b[0], b[1], b[2], b[3], npts(b, .25), npts(b, 1), ",".join(regs)))


CORAL_EVENTS = r"D:\coral\target\events_dated.parquet"      # the site list the SST cache was fetched for
D6_N_TEST = 100
SST_GAP_DAYS = 1                                              # g, SPEC_CORAL_TABLES.md:166 (--sst-gap-days default)


def _grid_axis(lo, hi, lon360=False):
    """CRW 0.05-deg pixel centres between lo and hi, as the SST cache saw them: ERDDAP prints 3 decimals, pandas
    parses them to float64, and longitudes (0..360 on PIFSC) go through ((x+180)%360)-180
    (coral_fetch_sst_full.py:128-135). Returned ascending, like np.sort(unique()) there."""
    import math
    out = []
    k0, k1 = int(math.floor((lo - 0.025) / 0.05)) - 1, int(math.ceil((hi - 0.025) / 0.05)) + 1
    for k in range(k0, k1 + 1):
        c = 0.025 + 0.05 * k
        if lon360:
            x = float("%.3f" % (c % 360.0))
            out.append(((x + 180) % 360) - 180)
        else:
            out.append(float("%.3f" % c))
    return sorted(set(out))


def sst_pixel(lat, lon):
    """The pixel the SST cache took for a site: first minimum of |axis - site| over the ascending axis
    (coral_fetch_sst_full.py:134-139; same rule coral_fetch_sst.py:111-112)."""
    import numpy as np
    la_ax = np.array(_grid_axis(lat - 0.2, lat + 0.2))
    lo_ax = np.array(_grid_axis(lon - 0.2, lon + 0.2, lon360=True))
    la = la_ax[np.abs(la_ax - lat).argmin()]
    lo = lo_ax[np.abs(lo_ax - lon).argmin()]
    tie_la = int((np.abs(la_ax - lat) == np.abs(la_ax - lat).min()).sum() > 1 or
                 abs(abs(la - lat) - 0.025) < 1e-9)
    tie_lo = int((np.abs(lo_ax - lon) == np.abs(lo_ax - lon).min()).sum() > 1 or
                 abs(abs(lo - lon) - 0.025) < 1e-9)
    return float(la), float(lo), tie_la, tie_lo


def d_star(issue, feature_end):
    """d* = C - g - 1 (research_coral.md:83). Day rows: C = issue date. Month rows: C = first day of the issue
    month (SPEC_CORAL_TABLES.md:163-165). The row kind is read from the gap issue - feature_end."""
    gap = (issue - feature_end).days
    if 1 <= gap <= 2:
        c = issue
    elif gap >= 28:
        c = issue.replace(day=1)
    else:
        raise SystemExit("REFUSED: issue %s - feature_end %s = %d days fits neither a day row (1-2) nor a month "
                         "row (28+)" % (issue, feature_end, gap))
    d = c - _dt.timedelta(days=SST_GAP_DAYS + 1)
    if d > feature_end:
        raise SystemExit("REFUSED: d* %s is after feature_end %s" % (d, feature_end))
    return d, gap, ("day" if gap <= 2 else "month")


def prepare_d6_v2(opts):
    """D6 v2 site-days: the same 200 train picks as v1 plus D6_N_TEST test picks, with d* and the SST pixel.
    Reads only row_id, group, programme, lat, lon, target_date, issue_date, feature_end, mark (never a label)."""
    import pandas as pd
    cols = ["row_id", "group", "programme", "lat", "lon", "target_date", "issue_date", "feature_end", "mark"]
    d = pd.read_parquet(CORAL_STORE_LEAD0, columns=cols)
    if (d["target_date"].astype(str) != d["issue_date"].astype(str)).any():
        raise SystemExit("REFUSED: lead_0 rows with issue_date != target_date; d* rule assumes the nowcast")
    picks = []
    for mark, n_pick in (("train", D6_N), ("test", D6_N_TEST)):
        m = d[d["mark"] == mark].sort_values("row_id").reset_index(drop=True)
        idx = [(i * len(m)) // n_pick for i in range(n_pick)]       # fixed stride, no seed
        s = m.iloc[idx].reset_index(drop=True)
        s.insert(0, "n", [("%03d" if mark == "train" else "t%03d") % (i + 1) for i in range(len(s))])
        picks.append(s)
    s = pd.concat(picks, ignore_index=True)
    v1 = pd.read_csv(D6_SITEDAYS, dtype=str)
    if list(v1["row_id"]) != list(s.loc[s["mark"] == "train", "row_id"]):
        raise SystemExit("REFUSED: the v2 train picks differ from %s" % D6_SITEDAYS)
    ev = pd.read_parquet(CORAL_EVENTS, columns=["lat", "lon"]).drop_duplicates()
    ev["k"] = ev["lat"].round(4).map("%.4f".__mod__) + "," + ev["lon"].round(4).map("%.4f".__mod__)
    raw = ev.groupby("k").agg(rlat=("lat", "first"), rlon=("lon", "first"), nraw=("lat", "size"))
    out = []
    for _, r in s.iterrows():
        k = "%.4f,%.4f" % (round(r["lat"], 4), round(r["lon"], 4))
        if k in raw.index and raw.loc[k, "nraw"] == 1:
            la_s, lo_s, src = float(raw.loc[k, "rlat"]), float(raw.loc[k, "rlon"]), "events_dated"
        else:
            la_s, lo_s, src = float(r["lat"]), float(r["lon"]), "store_rounded"
        px_la, px_lo, tla, tlo = sst_pixel(la_s, lo_s)
        issue = _dt.date.fromisoformat(str(r["issue_date"])[:10])
        fe = _dt.date.fromisoformat(str(r["feature_end"])[:10])
        ds, gap, kind = d_star(issue, fe)
        out.append({"n": r["n"], "row_id": r["row_id"], "group": r["group"], "programme": r["programme"],
                    "mark": r["mark"], "lat": "%.4f" % r["lat"], "lon": "%.4f" % r["lon"],
                    "issue_date": issue.isoformat(), "feature_end": fe.isoformat(), "gap_days": gap,
                    "row_kind": kind, "day": ds.isoformat(),
                    "day_moved_from_v1": (str(fe != ds) if r["mark"] == "train" else "n/a"),
                    "px_lat": "%.3f" % px_la, "px_lon": "%.3f" % px_lo, "site_coord_source": src,
                    "edge_lat": tla, "edge_lon": tlo})
    o = pd.DataFrame(out).astype(str)
    if os.path.exists(D6_SITEDAYS_V2):
        old = pd.read_csv(D6_SITEDAYS_V2, dtype=str)
        if not old.equals(o):
            raise SystemExit("REFUSED: %s exists and differs from a fresh pick" % D6_SITEDAYS_V2)
        log("%s already exists and matches" % D6_SITEDAYS_V2)
        return 0
    o.to_csv(D6_SITEDAYS_V2, index=False)
    tr = o[o["mark"] == "train"]
    log("wrote %s: %d train + %d test site-days; train days moved from v1: %d; edge sites (lat/lon): %d/%d; "
        "site coords from events_dated %d, store-rounded %d; test days %s..%s"
        % (D6_SITEDAYS_V2, len(tr), (o["mark"] == "test").sum(), (tr["day_moved_from_v1"] == "True").sum(),
           (o["edge_lat"] == "1").sum(), (o["edge_lon"] == "1").sum(), (o["site_coord_source"] == "events_dated").sum(),
           (o["site_coord_source"] == "store_rounded").sum(), o.loc[o["mark"] == "test", "day"].min(),
           o.loc[o["mark"] == "test", "day"].max()))
    return 0


def prepare_d6(opts):
    """Pick D6_N train site-days from the coral store: locations and dates only (no label column is read)."""
    if opts.d6_set == "v2":
        return prepare_d6_v2(opts)
    import pandas as pd
    cols = ["row_id", "group", "programme", "lat", "lon", "feature_end", "mark"]
    d = pd.read_parquet(CORAL_STORE_LEAD0, columns=cols)
    d = d[d["mark"] == "train"].sort_values("row_id").reset_index(drop=True)
    n = len(d)
    idx = [(i * n) // D6_N for i in range(D6_N)]               # fixed stride, no seed
    s = d.iloc[idx].reset_index(drop=True)
    s.insert(0, "n", ["%03d" % (i + 1) for i in range(len(s))])
    s["lat"] = s["lat"].round(4).map(lambda v: "%.4f" % v)      # store sites carry 1e-4 deg (coral_safe.py:97)
    s["lon"] = s["lon"].round(4).map(lambda v: "%.4f" % v)
    s = s.rename(columns={"feature_end": "day"})[["n", "row_id", "group", "programme", "lat", "lon", "day"]]
    if os.path.exists(D6_SITEDAYS):
        old = pd.read_csv(D6_SITEDAYS, dtype=str)
        if not old.equals(s.astype(str)):
            raise SystemExit("REFUSED: %s exists and differs from a fresh pick" % D6_SITEDAYS)
        log("%s already exists and matches" % D6_SITEDAYS)
        return 0
    s.to_csv(D6_SITEDAYS, index=False)
    log("wrote %s: %d site-days from %d train rows (stride %d), %d distinct sites, %d groups, days %s..%s"
        % (D6_SITEDAYS, len(s), n, n // D6_N, s.groupby(["lat", "lon"]).ngroups, s["group"].nunique(),
           s["day"].min(), s["day"].max()))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true")
    g.add_argument("--dry-run", nargs="+", metavar="PRODUCT")
    g.add_argument("--run", metavar="PRODUCT")
    g.add_argument("--prepare-d6", action="store_true")
    ap.add_argument("--boxes", choices=["merged", "region"], default="merged",
                    help="D2/D3 area: merged 45-degree boxes (default) or one box per fire region")
    ap.add_argument("--seas-years-per-request", type=int, default=1, help="D3: start years per request")
    ap.add_argument("--min-free-gb", type=float, default=12.0)
    ap.add_argument("--limit", type=int, default=0, help="only the first N requests (testing)")
    ap.add_argument("--pause", type=float, default=0.5, help="seconds between public HTTP requests")
    ap.add_argument("--max-fail-streak", type=int, default=5, help="stop after N failures in a row")
    ap.add_argument("--no-network", action="store_true", help="dry run: do not ask servers for sizes")
    ap.add_argument("--d6-server", choices=["pfeg", "pifsc"], default="pfeg",
                    help="D6: coastwatch.pfeg NOAA_DHW (named in the plan) or the NOAA PIFSC mirror of the same "
                         "CRW v3.1 grids (separate version folder)")
    ap.add_argument("--d6-set", choices=["v1", "v2"], default="v1",
                    help="D6 site-day list: v1 = d6_sitedays.csv (train only, day = feature_end, site coords); "
                         "v2 = d6_sitedays_v2.csv (train + test, day = d*, SST cache pixel; PIFSC only)")
    ap.add_argument("--probe-year", type=int, default=2016,
                    help="D0': start year of the probe (2016 = 25 members; 2017-2022 = 51 members)")
    ap.add_argument("--timeout", type=float, default=120.0, help="seconds per public HTTP request")
    ap.add_argument("--approved-gb", type=float, default=0.0,
                    help="owner re-approved size in GB for this product (default: the AB1 bound x 1.10)")
    opts = ap.parse_args()
    if not sys.flags.isolated:
        log("note: run with 'py -3.9 -I' (isolated mode) because this script reads downloaded files")
    if opts.list:
        return do_list(opts)
    if opts.prepare_d6:
        return prepare_d6(opts)
    if opts.dry_run:
        print("DRY RUN %s  (nothing is downloaded or written)  boxes=%s seas_years_per_request=%d  D: free %.1f GB"
              % (now_iso(), opts.boxes, opts.seas_years_per_request, gb(free_bytes(PRODUCTS_ROOT))))
        grand_n = grand_b = 0
        for p in opts.dry_run:
            k = ALIASES.get(p, p)
            if k not in REGISTRY:
                raise SystemExit("unknown product %s (known: %s; D5 is not approved)" % (p, ", ".join(REGISTRY)))
            n, b = dry_run(REGISTRY[k](opts), opts)
            grand_n += n
            grand_b += b
        print("=" * 110)
        print("ALL  %d requests, expected %s" % (grand_n, human(grand_b)))
        return 0
    k = ALIASES.get(opts.run, opts.run)
    if k not in REGISTRY:
        raise SystemExit("unknown product %s (known: %s; D5 is not approved)" % (opts.run, ", ".join(REGISTRY)))
    return run_product(REGISTRY[k](opts), opts)


if __name__ == "__main__":
    sys.exit(main())
