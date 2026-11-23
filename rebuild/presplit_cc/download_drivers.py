"""Download the VERIFIED, open-access NDVI-driver datasets to D:\\ndvi_drivers\\.
(URLs/coverage confirmed by the verify-41-drivers workflow; see DRIVERS_TO_ADD.md.)

* Resumable + crash-safe: skips files already fully downloaded (size match), resumes partial files
  via HTTP Range, retries on failure. Safe to re-run -- it only fetches what's missing/incomplete.
* Outputs to the HDD (D:), one folder per category.
* GATED datasets (API keys / forms / paywalls) CAN'T be scripted -> printed as MANUAL TODOs at the end.
* Multi-GB total -> run in YOUR terminal, do NOT background.

Run:
  py -3.9 presplit_cc/download_drivers.py            # core open set (~6 GB) + harmonized nightlights
  py -3.9 presplit_cc/download_drivers.py --huge     # also LUH2 29GB / cropping-intensity 3.8GB / CIrrMap250
  py -3.9 presplit_cc/download_drivers.py --list      # dry-run: show what would be fetched, download nothing
"""
import os
import re
import sys
import time

import requests

ROOT = r"D:\ndvi_drivers"
HUGE = "--huge" in sys.argv
LIST = "--list" in sys.argv
UA = {"User-Agent": "Mozilla/5.0 (research data fetch; contact via project)"}

# (category, filename, url, approx_MB, huge?)
JOBS = [
    ("co2",            "co2_mm_gl.txt",                       "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_gl.txt", 0.03, False),
    ("prices",         "fao_food_price_indices.csv",          "https://www.fao.org/media/docs/worldfoodsituationlibraries/default-document-library/food_price_indices_data.csv?sfvrsn=523ebd2a_80&download=true", 0.05, False),
    ("worldbank",      "fdi_BX.KLT.DINV.CD.WD.zip",           "https://api.worldbank.org/v2/en/indicator/BX.KLT.DINV.CD.WD?downloadformat=csv", 0.2, False),
    ("worldbank",      "tourism_ST.INT.ARVL.zip",             "https://api.worldbank.org/v2/en/indicator/ST.INT.ARVL?downloadformat=csv", 0.2, False),
    ("gdp",            "gdp_perCapita_1990_2024_v4.tif",      "https://zenodo.org/records/18429133/files/rast_adm2_gdp_perCapita_1990_2024.tif?download=1", 130, False),
    ("gdp",            "DOSE_V2.9.csv",                       "https://zenodo.org/api/records/13773040/files/DOSE_V2.9.csv/content", 15, False),
    ("gdp",            "DOSE_shapefiles.gpkg",                "https://zenodo.org/api/records/7573249/files/DOSE_shapefiles.gpkg/content", 336, False),
    ("wealth",         "HDI_1990_2015_v2.nc",                 "https://zenodo.org/records/4972425/files/HDI_1990_2015_v2.nc?download=1", 11, False),
    ("wealth",         "relative_wealth_index_2021.csv",      "https://data.humdata.org/dataset/76f2a2ea-ba50-40f5-b79c-db95d668b843/resource/bff723a4-6b55-4c51-8790-6176a774e13c/download/relative-wealth-index-93-low-and-middle-income-countries-with-quadkeys-april-2021.csv", 60, False),  # Meta replaced the .zip with per-country + this combined CSV (93 LMICs only)
    ("conflict",       "ucdp_ged261.csv.zip",                 "https://ucdp.uu.se/downloads/ged/ged261-csv.zip", 60, False),
    # N-deposition (ISIMIP3a ndep, NHx+NOy monthly to 2021): exact files.isimip.org path 404s -> see GATED/manual list.
    ("deforestation",  "DeDuCE_deforestation_2001-2023.xlsx", "https://zenodo.org/api/records/18953516/files/1.%20DeDuCE_Deforestation_attributed%20to%20agricultural%20and%20forestry%20commodities%20(2001-2023).xlsx/content", 22, False),
    ("deforestation",  "drivers_forest_loss_1km_2001_2022.tif", "https://zenodo.org/records/15224684/files/drivers_forest_loss_1km_2001_2022_v1.tif", 281, False),
    ("deforestation",  "GlobalOilPalm_OP-YoP.zip",            "https://zenodo.org/api/records/11034131/files/GlobalOilPalm_OP-YoP.zip/content", 310, False),
    ("energy",         "global_power_plant_database.csv",     "https://raw.githubusercontent.com/wri/global-power-plant-database/master/output_database/global_power_plant_database.csv", 11, False),
    ("energy",         "OGIM_v1.gpkg",                        "https://zenodo.org/records/7466758/files/OGIM_v1.gpkg?download=1", 2800, False),
    ("mining",         "global_mining_polygons_v2.gpkg",      "https://download.pangaea.de/dataset/942325/files/global_mining_polygons_v2.gpkg", 24, False),
    ("mining",         "Global_mine_polygons_74726.zip",      "https://zenodo.org/records/17085099/files/Global_mine_polygons_74726.zip?download=1", 33, False),
    ("water",          "GDW_v1_gdb.zip",                      "https://ndownloader.figshare.com/files/47913742", 110, False),
    ("water",          "GDW_v1_shp.zip",                      "https://ndownloader.figshare.com/files/47913754", 20, False),
    ("infrastructure", "GRIP4_density_total.zip",             "https://zenodo.org/api/records/6420961/files/GRIP4_density_total.zip/content", 4, False),
    ("infrastructure", "travel_time_to_cities_2015.zip",      "https://data.malariaatlas.org/geoserver/ows?service=CSW&version=2.0.1&request=DirectDownload&ResourceId=Explorer:2015_accessibility_to_cities_v1.0", 350, False),
    ("crops",          "CROPGRIDS.zip",                       "https://ndownloader.figshare.com/files/44950942", 800, False),
    ("disasters",      "emdat_archive.xlsx",                  "https://dataverse.uclouvain.be/api/access/datafile/38893", 8, False),
    ("disasters",      "idmc_internal_displacements.csv",     "https://data.humdata.org/dataset/459fc96c-f196-44c1-a0a5-1b5a7b3592dd/resource/0fb4e415-abdb-481a-a3c6-8821e79919be/download/internal-displacements-new-displacements-idps.csv", 1, False),
    ("covid",          "Global_Mobility_Report.csv",          "https://www.gstatic.com/covid19/mobility/Global_Mobility_Report.csv", 1140, False),
    ("covid",          "OxCGRT_stringency.csv",               "https://raw.githubusercontent.com/OxCGRT/covid-policy-dataset/main/data/timeseries_indices/OxCGRT_timeseries_StringencyIndex_v1.csv", 2, False),
    # ---- HUGE (only with --huge) ----
    ("landuse",        "LUH2-GCB2025_states.nc",              "https://zenodo.org/records/15557904/files/states4.nc", 29000, True),
    ("crops",          "cropping_intensity_GCI_QC.rar",       "https://ndownloader.figshare.com/files/26634299", 3800, True),
]

GATED = [
    "ACLED conflict           -> register at https://acleddata.com/register/ , get an OAuth token, then API "
    "https://acleddata.com/api/acled/read?_format=csv&limit=5000&page=N (paginate 5000/req).",
    "WDPA protected areas     -> accept terms at https://www.protectedplanet.net/en (or wcmc.io/wdpa_current_release); File-GDB ~2GB.",
    "SPAM 2020 crop maps      -> Harvard Dataverse DOI 10.7910/DVN/SWPENT via web UI (Guestbook blocks anonymous wget).",
    "GEM Coal Mine / Plant    -> free request form at globalenergymonitor.org (Excel). (KAPSARC mirror has plants w/o dates.)",
    "Ozone (gridded monthly)  -> MERRA-2 M2TMNXCHM (Earthdata login) full-2002 cover, or CAMS EAC4-monthly (cdsapi + ADS key).",
    "Nitrogen deposition      -> ISIMIP3a ndep (NHx+NOy, monthly to 2021): the files.isimip.org path 404s; find the exact "
    ".nc at https://data.isimip.org/ (search 'ndep' -> copy the download link) then wget it into D:\\ndvi_drivers\\ndep\\.",
    "Fertilizer 1961-2019 5'  -> confirm repo DOI in the Sci-Data s41597-024-04215-x Data-Availability, then fetch.",
    "Hansen forest loss       -> per-tile from storage.googleapis.com/earthenginepartners-hansen/GFC-2023-v1.11/"
    "Hansen_GFC-2023-v1.11_lossyear_<LAT>_<LON>.tif -- needs your 133 region bboxes to pick tiles (separate step).",
    "EOG gas flaring          -> browse dir index https://eogdata.mines.edu/global_flare_data/ (filenames vary per year).",
    "GHSL built-up (age)      -> per-epoch zips under https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_BUILT_S_GLOBE_R2023A/",
    "CIrrMap250 irrigation    -> figshare 24814293 per-year (CHINA-ONLY, low priority).",
    "NPP-VIIRS 500m lights    -> Harvard Dataverse DVN/YGIVCD per-year (alt to harmonized NTL below).",
    "Commodity-attributed mining -> not distributed; needs R pipeline + paywalled S&P/OSM inputs. Skip.",
]


def fetch(url, path, mb):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    name = os.path.basename(path)
    if LIST:
        print(f"  WOULD GET  {name:42s} (~{mb:.0f} MB)  {url[:70]}"); return "list"
    # already complete?
    rem = 0
    try:
        h = requests.head(url, headers=UA, allow_redirects=True, timeout=30)
        rem = int(h.headers.get("Content-Length", 0))
    except Exception:
        pass
    if os.path.exists(path) and rem and os.path.getsize(path) >= rem:
        print(f"  skip (complete) {name}"); return "skip"
    for attempt in range(4):
        try:
            pos = os.path.getsize(path) if os.path.exists(path) else 0
            hdr = dict(UA)
            if pos:
                hdr["Range"] = f"bytes={pos}-"
            r = requests.get(url, headers=hdr, stream=True, allow_redirects=True, timeout=90)
            if r.status_code == 416:                      # Range past EOF -> file is already complete
                print(f"  skip (complete) {name}"); return "skip"
            if r.status_code >= 400:                      # real error -> do NOT overwrite the good file with the error body
                raise requests.HTTPError(f"HTTP {r.status_code} for {name}")
            mode = "ab" if (pos and r.status_code == 206) else "wb"
            got = pos if mode == "ab" else 0
            with open(path, mode) as f:
                for chunk in r.iter_content(1 << 20):
                    if chunk:
                        f.write(chunk); got += len(chunk)
            print(f"  OK         {name}  ({got/1e6:.1f} MB)")
            return "ok"
        except Exception as e:
            print(f"  retry {attempt+1}/4 {name}: {type(e).__name__} {str(e)[:80]}")
            time.sleep(4 * (attempt + 1))
    print(f"  FAILED     {name}  ({url[:70]})")
    return "fail"


def harmonized_ntl():
    """Enumerate the per-year harmonized DMSP+VIIRS nightlights (figshare 9828827), 2002-2023."""
    print("\n[lights] harmonized DMSP+VIIRS nightlights (figshare 9828827, per-year 2002-2023)")
    try:
        files = requests.get("https://api.figshare.com/v2/articles/9828827", headers=UA, timeout=60).json().get("files", [])
    except Exception as e:
        print(f"  figshare API failed: {e}"); return {"fail": 1}
    tally = {}
    for fobj in files:
        nm = fobj.get("name", "")
        m = re.search(r"(19|20)\d{2}", nm)
        if nm.lower().endswith(".tif") and m and 2002 <= int(m.group(0)) <= 2023:
            r = fetch(fobj["download_url"], os.path.join(ROOT, "lights", nm), fobj.get("size", 0) / 1e6)
            tally[r] = tally.get(r, 0) + 1
    return tally


def main():
    print(f"=== NDVI driver downloads -> {ROOT}  {'[DRY-RUN]' if LIST else ''}{'  [+HUGE]' if HUGE else ''} ===")
    tally = {}
    for cat, fn, url, mb, huge in JOBS:
        if huge and not HUGE:
            continue
        print(f"\n[{cat}] {fn}  (~{mb:.0f} MB)")
        r = fetch(url, os.path.join(ROOT, cat, fn), mb)
        tally[r] = tally.get(r, 0) + 1
    nt = harmonized_ntl()
    for k, v in nt.items():
        tally[k] = tally.get(k, 0) + v

    print("\n================ SUMMARY ================")
    for k in ("ok", "skip", "fail", "list"):
        if tally.get(k):
            print(f"  {k}: {tally[k]}")
    print("\n---- MANUAL (gated: keys/forms/paywall — cannot script) ----")
    for g in GATED:
        print("  * " + g)
    print("\nRe-run any time; completed files are skipped. Gated items above are done by hand.")


if __name__ == "__main__":
    main()
