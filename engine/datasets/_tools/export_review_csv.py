"""export_review_csv.py -- build the owner's Q34 ban-list / column-fact REVIEW CSVs and seed the store catalogs.

    py -3.9 "engine/datasets/_tools/export_review_csv.py"                       # write to engine/datasets/
    py -3.9 "engine/datasets/_tools/export_review_csv.py" --out-dir D:/treeroute/review-csv/try1
    py -3.9 "engine/datasets/_tools/export_review_csv.py" --refresh-cache       # re-read the parquet footers

WHERE THIS SITS. Dataset-side tooling under engine/datasets/, OUTSIDE the engine. It may name problems, years
and drives (G-NONAMES scans engine code only). It is not science code: it transforms no data that a model
reads. It reads the SHIPPED ban modules and feature lists, parquet FOOTERS, and a tiny cadence sample, and it
writes review sheets for a human. Every fact it writes is marked fact_status 'unverified'.

WHAT IT WRITES (new files only; it REFUSES to overwrite, so an owner's filled-in sheet can never be lost):
    <out>/review/{pm25,fire,defo,ndvi}_columns.csv        one row per candidate input column of that problem
    <out>/_stores/monthly_panel_v170.yaml                 one entry per panel column (physical store facts)
    <out>/_stores/{gfed_burn,edgar_emis,fire_history,fire_drivers}_catalog.yaml   side-store seeds
and two caches (named by an input fingerprint, so a refresh writes a NEW file and never overwrites):
    D:/treeroute/review-csv/footers_<store>_<fp>.parquet   parquet-footer statistics (null_count / min / max)
    D:/treeroute/review-csv/cadence_probe_<fp>.json        a 5-region x 2-year within/between-year sample

READ-ONLY on everything else. It never writes under a root listed in D:/treeroute/registry/protected_roots.txt.

SOURCES (each row's source_locator points at the exact file:line):
    PM2.5  pm25_ban.py (lists), pm25_architecture.py (burn/EDGAR blocks), D:/pm25_adapt/u2/run.log line 9 (the
           105 features that reached the model), pm25_split.py (groups)
    fire   fire_ban.py, fire_architecture.py (HIST_DROP, apply_ban(drop_conditional=True), sidecar blocks),
           adaptation.py:2182 (USE_HISTORY, USE_DRIVERS = 1, 1), sidecar footers under D:/fire, the pool width
           logged in D:/adaptation/_fire_postfix.log
    defo   defo_ban.py, defo_matrix.py, D:/defo_matrix footers, defo_train.py MASK, defo_corrector.py arm 'hist'
    NDVI   presplit_cc/experiment_thar_regime_full.py REMOVE (the 11) and GEO, presplit_cc/run89_outputs.py
           DEFAULT_DROP, presplit_cc/bundle_lag_compare.py (lags + water memory), leak_audit LAG_ORDERS,
           presplit_cc/cross_region_fast.py:767-771 (router context)
    Owner rulings applied: APP_PLAN.md 'Rulings built in' and HEADLINE_QUESTIONS_AND_FIXES.md top sections
    (Q2 oni/tni lagged, Q3 a, Q12, Q35 a, Q38 b, A1-A5, plan 3.3 flag 7). Each is tagged [ruling ...].

FAIL LOUD. Any panel column without facts, any list member absent from the panel, any mismatch between a
reconstructed feature list and the shipped count, or an existing output file stops the run with the cause.
"""
import argparse
import ast
import collections
import csv
import datetime
import hashlib
import json
import math
import os
import re
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))   # the research folder (engine/..)
PC = os.path.join(ROOT, "presplit_cc")
DEFAULT_OUT = os.path.abspath(os.path.join(HERE, ".."))          # engine/datasets
DEFAULT_CACHE = "D:/treeroute/review-csv"
PROTECTED = "D:/treeroute/registry/protected_roots.txt"

PANEL_DIR = "D:/monthly_panel"
GFED_DIR = "D:/gfed_burn"
EDGAR_DIR = "D:/edgar_emis"
PM25_TARGET_DIR = "D:/pm25_acag"
FIRE_TARGET_DIR = "D:/fire/target"
FIRE_HIST_DIR = "D:/fire/history"
FIRE_DRV_DIR = "D:/fire/drivers/joined"
DEFO_MATRIX_DIR = "D:/defo_matrix"
DEFO_TARGET_DIR = "D:/defo_target"
PM25_RUNLOG = "D:/pm25_adapt/u2/run.log"
FIRE_POOL_LOG = "D:/adaptation/_fire_postfix.log"
DEFO_MATRIX_LOG = "D:/defo_matrix/_matrix.log"
NDVI_SPLIT = "D:/run89full/ndvi_split.txt"
FOREST_CENSUS = "D:/run89full/forest_census.csv"
FIRE_SIZES = "D:/fire/region_sizes.csv"

FILLS = (-32768.0, -32767.0, -2147483648.0, -2147483647.0)
CSV_COLUMNS = ["column", "store", "current_verdict", "current_reason", "source_locator", "cadence", "stamp",
               "window_length", "window_align", "units", "legal_min", "legal_max", "fact_status", "lag_note",
               "co_measured_candidate", "missing_share_note", "owner_verdict", "owner_timing_signed", "notes"]
VERDICTS = {"keep", "ban", "freeze", "conditional", "watch", "lagged"}
KEY_COLS = ("cell_id", "region", "year", "month")

# windows per problem: donor-row years (Y0..train end) and test years, as the plan's rules give them (3.2)
WINDOWS = {
    "pm25": dict(donor_years=list(range(2003, 2020)), test_years=[2020, 2021, 2022, 2023], target="monthly"),
    "fire": dict(donor_years=list(range(2003, 2019)), test_years=[2019, 2020, 2021, 2022], target="monthly"),
    "defo": dict(donor_years=list(range(2003, 2020)), test_years=[2020, 2021, 2022, 2023], target="annual"),
    "ndvi": dict(donor_years=list(range(2003, 2020)), test_years=[2020, 2021, 2022, 2023], target="monthly"),
}
PROBE_REGIONS = ["thar_desert", "tongass_alaska", "costa_rica", "mesopotamia", "okavango_delta"]
PROBE_YEARS = [2010, 2015]


def log(m):
    print(m, flush=True)


def rel(path):
    """Repo-relative path for code files, forward slashes."""
    p = os.path.abspath(path)
    if p.lower().startswith(ROOT.lower()):
        p = p[len(ROOT) + 1:]
    return p.replace("\\", "/")


# ================================================================================================
# 1. SOURCE READERS (AST, never import: several shipped modules parse argv or pull heavy deps)
# ================================================================================================
_AST_CACHE = {}


def _strings(node):
    """[(value, lineno)] for a list/tuple/set literal of string constants, else None."""
    if isinstance(node, ast.Call) and getattr(node.func, "id", None) in ("list", "tuple", "set") and node.args:
        return _strings(node.args[0])
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        out = []
        for e in node.elts:
            if isinstance(e, ast.Constant) and isinstance(e.value, str):
                out.append((e.value, e.lineno))
            else:
                return None
        return out
    return None


def module_lists(path):
    """{NAME: [(str, lineno), ...]} for module-level string-list assignments, incl. A + B + C concatenations
    of earlier names and tuple unpacking ``A, B = "x", ["y"]``."""
    if path in _AST_CACHE:
        return _AST_CACHE[path]
    tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
    out = {}

    def concat(node):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            a, b = concat(node.left), concat(node.right)
            return None if a is None or b is None else a + b
        if isinstance(node, ast.Name):
            return out.get(node.id)
        return _strings(node)

    for st in tree.body:
        if not isinstance(st, ast.Assign):
            continue
        for tgt in st.targets:
            if isinstance(tgt, ast.Name):
                v = concat(st.value)
                if v is not None:
                    out[tgt.id] = v
            elif isinstance(tgt, ast.Tuple) and isinstance(st.value, ast.Tuple):
                for t_, v_ in zip(tgt.elts, st.value.elts):
                    if isinstance(t_, ast.Name):
                        v = _strings(v_)
                        if v is not None:
                            out[t_.id] = v
    _AST_CACHE[path] = out
    return out


def need(d, name, path):
    if name not in d:
        raise SystemExit("export_review_csv: list %s not found in %s -- the shipped module changed; fix the reader"
                         % (name, rel(path)))
    return d[name]


def grep_line(path, pattern, default=None):
    """First 1-based line number whose text matches the regex, else default."""
    rx = re.compile(pattern)
    with open(path, encoding="utf-8", errors="replace") as f:
        for i, ln in enumerate(f, 1):
            if rx.search(ln):
                return i
    return default


def loc(path, pattern):
    n = grep_line(path, pattern)
    if n is None:
        raise SystemExit("export_review_csv: pattern %r not found in %s" % (pattern, rel(path)))
    return "%s:%d" % (rel(path) if not path.startswith("D:") else path, n)


# ================================================================================================
# 2. PHYSICAL FACTS OF THE 170 PANEL COLUMNS (seeds, every one 'unverified')
# ================================================================================================
# window kinds -> how R8 would read them. The CSV/YAML write them out in words.
#   static | month | month_instant | trailing_N | centred_N | unknown | year | year_doy65 | month_pad8 |
#   mod13c2 | recursive | year_unknown | grace | key
AM = "presplit_cc/assemble_monthly_panel.py"
AH = "presplit_cc/assemble_human_drivers.py"
IM = "presplit_cc/ingest_modis_cmg_local.py"

FAMILIES = [
    # ---- keys ----
    dict(cols=["cell_id", "region", "year", "month"], kind="key", cadence="key", scope="unit", src=[AM],
         product="panel keys", family="keys", notes="key roles live in each package catalog, never here"),
    # ---- static geography ----
    dict(cols=["lat", "lon"], kind="static", scope="unit", src=[AM], product="panel grid cell centre (EPSG:4326)",
         family="grid", units={"lat": "degrees_north", "lon": "degrees_east"},
         legal={"lat": (-90, 90), "lon": (-180, 180)}),
    dict(cols=["V25_elevation_m", "V26_slope_deg", "V27_southness", "V28_CTI"], kind="static", scope="unit",
         src=[AM], product="master-bundle terrain layers (feature_definitions.json; DEM source not recorded here)",
         family="terrain"),
    dict(cols=["clay_pct", "sand_pct", "silt_pct", "soil_organic_carbon_gkg", "nitrogen_gkg", "soil_ph",
               "awc_cm3cm3", "bulk_density_gcm3", "cec_cmolkg", "coarse_fragments_pct"], kind="static",
         scope="unit", src=[AM], product="master-bundle soil layers (SoilGrids-type)", family="soil",
         notes="AUDIT_REPORT.md item 3: awc_cm3cm3 max 0.93 and nitrogen_gkg max 267 are physically impossible"),
    dict(cols=["hand_m", "upstream_area_km2"], kind="static", scope="unit", src=[AM], product="MERIT Hydro",
         family="MERIT", notes="MERIT's flow routing uses Hansen tree density (year 2000) -- a lineage link to the "
         "defo target's product family, measured admissible with disclosure (Part 508)"),
    dict(cols=["irrigation_pct_gmia"], kind="static", scope="unit", src=[AM], product="GMIA irrigated area share",
         family="GMIA"),
    dict(cols=["dist_to_coast_km"], kind="static", scope="unit", src=[AM], product="distance to coast",
         family="coast"),
    # ---- MODIS land products carried from the master ----
    dict(cols=["tree_cover_pct", "V15_bare_ground_pct", "V17_herb_cover_pct"], kind="year_doy65", scope="unit",
         src=["defo_ban.py", AM], product="MOD44B VCF (product year starts DOY 65, runs to DOY 64 of the next year)",
         family="MODIS MOD44B", sensor="MODIS", sum_group="MOD44B (V15 + V17 + tree = 100, defo_ban.py:30-32)",
         notes="carried from the master to all 12 months (assemble_monthly_panel.py CARRY)"),
    dict(cols=["modis_landcover_class", "cropland_fraction", "shrub_cover_pct_global"], kind="year", scope="unit",
         src=[AM], product="MCD12Q1 IGBP land cover (cropland = class 12, shrub = classes 6+7; defo_ban.py:36-38)",
         family="MODIS MCD12Q1", sensor="MODIS",
         notes="carried from the master; modis_landcover_class is a categorical code stored as float"),
    dict(cols=["modis_landcover_annual"], kind="year", scope="unit", src=[IM, AM],
         product="MCD12C1 v061 annual majority IGBP class (covers 2001-2022; 2023 is NaN, ingest_modis_cmg_local.py:80-84)",
         family="MODIS MCD12C1", sensor="MODIS", notes="categorical IGBP code stored as float; empty in 2023"),
    dict(cols=["phenology_sos_doy"], kind="year_unknown", scope="unit", src=[AM],
         product="MCD12Q2 start of season (master)", family="MODIS MCD12Q2", sensor="MODIS",
         notes="the season is known only after it happens; detection window beyond the calendar year not recorded"),
    # ---- population / built ----
    dict(cols=["population_density"], kind="year", scope="unit", src=["presplit_cc/ingest_worldpop_annual.py", AM],
         product="WorldPop Global1 annual 1 km persons per pixel (observed 2002-2020)", family="WorldPop",
         units={"population_density": "persons per 1-km pixel"},
         notes="CONTRADICTION: ingest_worldpop_annual.py:1-2 says 2020 is HELD for 2021-2023; defo_ban.py:106-111 "
               "says 2021-2023 rise (extrapolated). AUDIT_REPORT.md item 3: max 368,684 is impossible as a density"),
    dict(cols=["built_surface_fraction"], kind="year", scope="unit", src=["defo_ban.py", AM],
         product="GHS-BUILT-S R2023A (observed epochs 1975/1990/2000/2014/2018; interpolated between; 2020+ projected)",
         family="GHSL", sensor="Landsat/Sentinel-2",
         notes="defo_ban.py:89-91: 2020+ are PROJECTIONS -> FREEZE family"),
    # ---- human annual (assemble_human_drivers.py) ----
    dict(cols=["gdp_pc"], kind="year", scope="unit", src=[AH], product="gridded GDP per capita 1990-2024 v4, stored as log1p",
         family="GDP", units={"gdp_pc": "log1p(GDP per capita)"}, legal={"gdp_pc": (0, None)},
         notes="stored as log1p (assemble_human_drivers.py:93); the audit spec's USD range does not apply"),
    dict(cols=["ntl"], kind="year", scope="unit", src=[AH],
         product="harmonised night lights DN, stored as log1p: calDMSP <= 2013, simVIIRS >= 2014", family="night lights",
         units={"ntl": "log1p(DN)"}, legal={"ntl": (0, None)},
         notes="SENSOR SWITCH 2013 -> 2014 (assemble_human_drivers.py:100); stored as log1p"),
    dict(cols=["hdi"], kind="year", scope="unit", src=[AH], product="HDI_1990_2015_v2, HELD at 2015 for 2016-2023",
         family="HDI", units={"hdi": "1"}, legal={"hdi": (0, 1)},
         notes="min(y, 2015) at assemble_human_drivers.py:113: every row after 2015 carries 2015's value; "
               "AUDIT_REPORT.md: hdi = 1.0 exactly looks like a clip"),
    dict(cols=["luh2_cropland", "luh2_pasture", "luh2_range", "luh2_urban", "luh2_forest", "luh2_secondary"],
         kind="year", scope="unit", src=[AH], product="LUH2-GCB2025 annual states (sums of LUH2 state classes)",
         family="LUH2", units={c: "1" for c in ["luh2_cropland", "luh2_pasture", "luh2_range", "luh2_urban",
                                                "luh2_forest", "luh2_secondary"]},
         legal={c: (0, 1) for c in ["luh2_cropland", "luh2_pasture", "luh2_range", "luh2_urban", "luh2_forest",
                                    "luh2_secondary"]},
         notes="Hurtt et al. 2020: LUH2 forest transitions are constrained by Hansen loss (defo_ban.py:43-47); "
               "GCB2025 adds MapBiomas for Brazil and Indonesia"),
    dict(cols=["fert_n", "fert_p"], kind="year", scope="unit", src=[AH],
         product="Lu & Tian 2016 N/P fertiliser, HELD at 2013 for 2014-2023", family="fertiliser",
         units={"fert_n": "g N m-2 (as in Lu & Tian; audit spec says kg/ha)", "fert_p": "g P m-2 (as in Lu & Tian; audit spec says kg/ha)"},
         notes="min(y, 2013) at assemble_human_drivers.py:145: every row after 2013 carries 2013's value; units unconfirmed"),
    dict(cols=["aglw_cattle", "aglw_buffalo", "aglw_horse", "aglw_sheep", "aglw_goats", "aglw_total_lsu"],
         kind="year", scope="unit", src=[AH], product="GLW annual livestock (FAOSTAT-disaggregated), stored as log1p",
         family="GLW", units=None,
         notes="stored as log1p (assemble_human_drivers.py:171-174); post-2021 values are the 2021 layer rescaled "
               "(defo_ban.py:93-95) -> FREEZE family"),
    dict(cols=["road_density"], kind="static", scope="unit", src=[AH], product="GRIP4 road density, stored as log1p",
         family="GRIP4", units={"road_density": "log1p(m km-2)"}, legal={"road_density": (0, None)}),
    dict(cols=["travel_time"], kind="static", scope="unit", src=[AH],
         product="travel time to cities 2015, stored as log1p", family="accessibility",
         units={"travel_time": "log1p(minutes)"}, legal={"travel_time": (0, None)}),
    dict(cols=["dist_powerplant", "dist_thermal", "dist_coal_mine", "dist_dam", "dist_reservoir", "dist_oilgas_well",
               "dist_pa"], kind="static", scope="unit", src=[AH],
         product="distance to nearest feature in a snapshot (GPPD, GEM coal May 2026, GDW, OGIM, WDPA June 2026)",
         family="infrastructure snapshots", units=None,
         notes="snapshots dated after the window (defo_ban.py:80-87) -> FREEZE family; dist_pa uses PA bounding-box "
               "centres, so a cell inside a park can score far (defo_ban.py:84-85)"),
    dict(cols=["conflict_events", "conflict_deaths"], kind="month", scope="unit", src=[AH],
         product="UCDP GED 26.1 events within 50 km, by the month of date_start, ZERO-filled",
         family="UCDP", units={"conflict_events": "count", "conflict_deaths": "count"},
         legal={"conflict_events": (0, None), "conflict_deaths": (0, None)},
         notes="MONTHLY, zero-filled (assemble_human_drivers.py:254-276; pm25_ban.py:139-140). AUDIT_REPORT.md item 5 "
               "called it annual-broadcast from an all-zero region; the cadence sample shows within-year variation "
               "where conflict exists (mesopotamia). Zero means 'no event within 50 km', never 'not measured'"),
    dict(cols=["co2"], kind="month", scope="global", src=[AH], product="NOAA global monthly mean CO2 (co2_mm_gl)",
         family="NOAA GML", units={"co2": "ppm"}, legal={"co2": (0, None)}),
    dict(cols=["food_price_index", "food_meat", "food_dairy", "food_cereals", "food_oils", "food_sugar"],
         kind="month", scope="global", src=[AH], product="FAO food price indices, monthly (2014-2016 = 100)",
         family="FAO FFPI", units=None),
    # ---- TerraClimate ----
    dict(cols=["V01_mean_temp_C", "diurnal_temp_range_C", "V02_total_precip_mm", "V07_total_ref_ET_mm", "aet_total_mm",
               "climate_water_deficit_mm", "V05_mean_vpd_kPa", "V09_mean_wind_ms", "solar_radiation_Wm2",
               "aridity_index_p_pet", "tc_vapor_pressure"], kind="month", scope="unit",
         src=[AM, "presplit_cc/ingest_terraclimate_monthly.py"], product="TerraClimate monthly (1/24 deg)",
         family="TerraClimate",
         notes="47 coastal regions carry -32768 (9 cols) or -2^31 (V02) as ordinary numbers (Part 248, "
               "reference_panel_nodata_sentinel)"),
    dict(cols=["soil_water_tc_mm", "swe_mean_mm"], kind="month_instant", scope="unit",
         src=[AM, "presplit_cc/ingest_terraclimate_monthly.py"], product="TerraClimate monthly (1/24 deg)",
         family="TerraClimate",
         notes="TerraClimate documents soil moisture and SWE as END-OF-MONTH values (verify); -2^31 fill in swe"),
    # ---- SPEI ----
    dict(cols=["spei_01m", "spei_03m", "spei_06m", "V06_spei_12m", "spei_24m"], kind="trailing", scope="unit",
         src=[AM, "presplit_cc/ingest_spei_monthly.py"], product="CSIC SPEIbase v2.9 (0.5 deg); ends 2022-12",
         family="SPEIbase", trailing={"spei_01m": 1, "spei_03m": 3, "spei_06m": 6, "V06_spei_12m": 12, "spei_24m": 24},
         baseline="standardised over the SPEIbase record (calibration period not recorded here)",
         notes="100% NaN in 2023 in all 133 regions (AUDIT_REPORT.md item 1)"),
    # ---- drought tier ----
    dict(cols=["scpdsi"], kind="recursive", scope="unit", src=["presplit_cc/ingest_drought_indices.py"],
         product="scPDSI, CRU TS 4.09 (0.5 deg)", family="CRU scPDSI", units={"scpdsi": "1"},
         notes="STATIC SPATIAL mask over hyper-arid land (0% or 100% NaN per cell); range [-11.25, 22.15] on a "
               "nominal +-4 index; trend-loaded (reference_drought_tier_hazards)"),
    dict(cols=["spi_01m", "spi_03m", "spi_06m", "spi_12m", "spi_24m"], kind="trailing", scope="unit",
         src=["presplit_cc/ingest_drought_indices.py"], product="GPCC SPI (gamma), 1.0 deg", family="GPCC SPI",
         trailing={"spi_01m": 1, "spi_03m": 3, "spi_06m": 6, "spi_12m": 12, "spi_24m": 24},
         units={c: "1" for c in ["spi_01m", "spi_03m", "spi_06m", "spi_12m", "spi_24m"]},
         notes="covers 2023 (the SPEI replacement for the test window, Part 324); spi_24m trend-loaded"),
    dict(cols=["eddi"], kind="month", scope="unit", src=["presplit_cc/ingest_drought_indices.py"],
         product="NOAA PSL EDDI, NCEP stream, 1-month timescale ending on the month's last day "
                 "(ingest_drought_indices.py:55, 262)", family="EDDI", units={"eddi": "1"},
         notes="SEASONAL mask: Oct-Feb missing at high latitude; a median fill smuggles the month key back "
               "(reference_drought_tier_hazards)"),
    dict(cols=["eddi_observed"], kind="month", scope="unit", src=["presplit_cc/add_drought_wbal_all_regions.py"],
         product="isfinite(eddi) indicator (Part 342)", family="EDDI", units={"eddi_observed": "1"},
         legal={"eddi_observed": (0, 1)}, derived_from="eddi"),
    dict(cols=["wbal_mm"], kind="month", scope="unit", src=["presplit_cc/add_drought_wbal_all_regions.py"],
         product="V02_total_precip_mm - V07_total_ref_ET_mm, sentinels masked before subtracting", family="derived",
         units={"wbal_mm": "mm month-1"}, derived_from="V02_total_precip_mm, V07_total_ref_ET_mm",
         notes="-2^31 - (-32768) = -2147450880 escapes both fill codes if unmasked (Part 340)"),
    dict(cols=["wbal_roll3", "wbal_roll6", "wbal_roll12", "wbal_roll24"], kind="trailing", scope="unit",
         src=["presplit_cc/add_drought_wbal_all_regions.py"], product="trailing SUMS of wbal_mm across year files",
         family="derived", trailing={"wbal_roll3": 3, "wbal_roll6": 6, "wbal_roll12": 12, "wbal_roll24": 24},
         units={c: "mm" for c in ["wbal_roll3", "wbal_roll6", "wbal_roll12", "wbal_roll24"]},
         derived_from="wbal_mm", notes="min_periods = window, so the first w-1 months of 2002 are NaN"),
    # ---- MODIS monthly CMG ----
    dict(cols=["V11_mean_ndvi"], kind="mod13c2", scope="unit", src=[IM], product="MOD13C2 v061 monthly CMG NDVI",
         family="MODIS MOD13C2", sensor="MODIS Terra", units={"V11_mean_ndvi": "1"},
         legal={"V11_mean_ndvi": (-0.2, 1.0)},
         notes="valid_range -2000..10000 x 1e-4 (ingest_modis_cmg_local.py:57); monthly composite built from 16-day "
               "inputs that overlap the month -- the M0 V11 window audit decides the reach past month end"),
    dict(cols=["V12_mean_evi"], kind="mod13c2", scope="unit", src=[IM], product="MOD13C2 v061 monthly CMG EVI (same file as NDVI)",
         family="MODIS MOD13C2", sensor="MODIS Terra", units={"V12_mean_evi": "1"}, legal={"V12_mean_evi": (-0.2, 1.0)}),
    dict(cols=["V13_mean_lst_C", "nighttime_lst_C"], kind="month", scope="unit", src=[IM],
         product="MOD11C3 v061 monthly CMG LST (day / night), Kelvin converted to Celsius", family="MODIS MOD11C3",
         sensor="MODIS Terra", units={"V13_mean_lst_C": "degC", "nighttime_lst_C": "degC"},
         legal={"V13_mean_lst_C": (-90, 80), "nighttime_lst_C": (-90, 60)},
         notes="MOD11C3 composites the calendar month from daily MOD11C1 (fire_ban.py:65-66 describes 8-day)"),
    dict(cols=["snow_cover_fraction"], kind="month", scope="unit", src=[IM], product="MOD10CM v61 monthly CMG snow cover",
         family="MODIS MOD10", sensor="MODIS Terra", units={"snow_cover_fraction": "1"},
         legal={"snow_cover_fraction": (0, 1)}, notes="raw 0-100 % scaled to a 0-1 fraction (ingest_modis_cmg_local.py:88-91)"),
    dict(cols=["cloud_frequency_pct"], kind="month", scope="unit", src=[IM],
         product="MOD08_M3 v6.1 monthly 1-degree Cloud_Fraction_Mean_Mean", family="MODIS MOD08 (atmosphere)",
         sensor="MODIS Terra", units={"cloud_frequency_pct": "percent"}, legal={"cloud_frequency_pct": (0, 100)},
         notes="1-degree atmosphere product (the MODIS L3 family that also carries aerosol); smoke can be flagged "
               "as cloud (pm25_ban.py:68-70)"),
    dict(cols=["V14_mean_albedo"], kind="month_pad8", scope="unit", src=[IM],
         product="MCD43C3 v061 daily white-sky shortwave albedo -> monthly mean", family="MODIS MCD43",
         sensor="MODIS Terra+Aqua", units={"V14_mean_albedo": "1"}, legal={"V14_mean_albedo": (0, 1)},
         notes="each daily MCD43 value uses a 16-day window CENTRED on its day (fire_ban.py:33-37)"),
    dict(cols=["gpp_kgC_m2"], kind="month_pad8", scope="unit", src=["presplit_cc/ingest_fluxsat_gpp.py"],
         product="FluxSat v2.2 daily GPP (0.625 x 0.5 deg) -> monthly kgC m-2", family="FluxSat",
         sensor="MODIS (MCD43 NBAR inputs)", units={"gpp_kgC_m2": "kg C m-2 month-1"}, legal={"gpp_kgC_m2": (0, None)},
         notes="FluxSat is driven by MODIS MCD43 reflectances (16-day windows) -- the 8-day reach is assumed from "
               "that; ~60 km native, 55 distinct values in a borneo region (defo_ban.py:142-145)"),
    # ---- AgERA5 day counts ----
    dict(cols=["frost_days", "heatwave_days_gt35C", "gdd5_degC_days", "wet_day_count", "V03_max_daily_precip_mm",
               "precip_intensity_mm", "vpd_max_daily", "vpd_days_gt_2kpa", "vpd_warm_season_mean", "sph_kgkg",
               "rmin_pct"], kind="month", scope="unit", src=["presplit_cc/ingest_agera5_daycounts.py", AM],
         product="AgERA5 (CDS sis-agrometeorological-indicators) daily fields -> monthly statistics", family="AgERA5",
         sensor="reanalysis (ERA5)",
         notes="vpd_warm_season_mean is the plain MONTHLY mean VPD despite its name (ingest_agera5_daycounts.py:169)"),
    # ---- ERA5-Land ----
    dict(cols=["V30_soil_moisture_pct"], kind="month", scope="unit", src=["presplit_cc/ingest_era5land_soilmoisture.py"],
         product="ERA5-Land monthly means swvl1 (0-7 cm) x 100", family="ERA5-Land", sensor="reanalysis (ERA5-Land)",
         units={"V30_soil_moisture_pct": "percent (volumetric)"}, legal={"V30_soil_moisture_pct": (0, 100)}),
    dict(cols=["era5l_pev", "era5l_sro", "era5l_ssro", "era5l_smlt", "era5l_slhf", "era5l_sshf", "era5l_ssr",
               "era5l_str", "era5l_d2m", "era5l_stl1"], kind="month", scope="unit",
         src=["presplit_cc/ingest_era5land_extra.py"], product="ERA5-Land monthly means (0.1 deg)", family="ERA5-Land",
         sensor="reanalysis (ERA5-Land)",
         notes="era5l_d2m and era5l_stl1 are KELVIN while every other temperature column is Celsius (AUDIT_REPORT.md item 6)"),
    # ---- snow phenology (ERA5-Land daily) ----
    dict(cols=["snow_onset_doy", "snow_disappearance_doy", "snow_duration_days", "snow_max_doy"], kind="year",
         scope="unit", src=["presplit_cc/ingest_era5land_snowphen.py", AM],
         product="ERA5-Land daily snow_cover >= 50% per CALENDAR year, split at DOY 200, broadcast to 12 months",
         family="ERA5-Land", sensor="reanalysis (ERA5-Land)",
         notes="calendar-year summaries (ingest_era5land_snowphen.py:4-8): an end-of-year fact on every month"),
    # ---- burned area (FireCCI / C3S) ----
    dict(cols=["V20_burned_binary"], kind="month", scope="unit", src=["presplit_cc/ingest_firecci_fire.py", AM],
         product="FireCCI 0.25 deg burned area: 1 if the month burned (esa_cci/MODIS <= 2019, C3S/OLCI >= 2020)",
         family="FireCCI", sensor="MODIS <= 2019, OLCI >= 2020", units={"V20_burned_binary": "1"},
         legal={"V20_burned_binary": (0, 1)},
         notes="CONTRADICTION: ingest_firecci_fire.py:7 says MONTHLY; pm25_ban.py:34 says annual -- see the observed "
               "cadence sample. SENSOR SWITCH exactly at the 2019/2020 split (ingest_firecci_fire.py:28, 37-40)"),
    dict(cols=["burn_month_count", "burn_doy_mean"], kind="year", scope="unit",
         src=["presplit_cc/ingest_firecci_fire.py", AM],
         product="FireCCI annual summary broadcast to 12 months (count of burned months / area-weighted mid-month DOY)",
         family="FireCCI", sensor="MODIS <= 2019, OLCI >= 2020",
         units={"burn_month_count": "count", "burn_doy_mean": "day of year"},
         legal={"burn_month_count": (0, 12), "burn_doy_mean": (0, 366)},
         notes="SENSOR SWITCH at the 2019/2020 split; burn_doy_mean is 0 when no fire"),
    # ---- global SST boxes / teleconnections ----
    dict(cols=["sst_anom_atl3", "sst_anom_iod_west", "sst_anom_iod_east", "sst_anom_subpolar_north_atlantic",
               "sst_anom_coral_sea", "sst_anom_mediterranean", "sst_anom_global_tropical_mean", "sst_anom_nino34"],
         kind="month", scope="global", src=["presplit_cc/ingest_ersst_boxes.py", AM],
         product="ERSSTv5 box means minus the 1971-2000 monthly climatology", family="ERSSTv5",
         baseline="1971-2000 (ingest_ersst_boxes.py:23)", units=None),
    dict(cols=["oni"], kind="centred", centred={"oni": 3}, scope="global", src=["presplit_cc/ingest_noaa_indices.py"],
         product="PSL oni.data (CPC ONI: 3-month running mean of Nino3.4 anomalies)", family="NOAA indices",
         units={"oni": "K (anomaly)"},
         notes="centred 3-month mean by the CPC definition; owner ruling Q2: kept, lagged by the computed rule"),
    dict(cols=["tni"], kind="unknown", scope="global", src=["presplit_cc/ingest_noaa_indices.py"],
         product="PSL tni.data (Trans-Nino Index)", family="NOAA indices", units={"tni": "1"},
         notes="described as a CENTRED running mean (Q2); Trenberth & Stepaniak 2001 smooth over 5 months -- the F10 "
               "audit (tni first) decides; owner ruling Q2: kept, lagged"),
    dict(cols=["amo"], kind="month", scope="global", src=["presplit_cc/ingest_noaa_indices.py"],
         product="PSL amon.us.data (Kaplan SST V2 AMO, 'us' = unsmoothed by PSL's file naming)", family="NOAA indices",
         units={"amo": "K (anomaly)"},
         notes="source ends January 2023: Feb-Dec 2023 empty (pm25_ban.py:114-117); 'unsmoothed' to be confirmed by F10"),
    dict(cols=["nino12", "nino3", "nino4", "nino34", "soi", "pdo", "tna", "tsa", "iod", "noi", "ao", "nao", "pna",
               "wp", "epo", "sam"], kind="unknown", scope="global", src=["presplit_cc/ingest_noaa_indices.py"],
         product="PSL / CPC monthly index files (ingest_noaa_indices.py:31-51)", family="NOAA indices", units=None,
         notes="smoothing undocumented (HEADLINE_QUESTIONS_AND_FIXES.md F10) -> R8 refuses these at lag 0 until a "
               "window or a signed maximum exists"),
    # ---- water storage / soil moisture / regimes ----
    dict(cols=["grace_lwe"], kind="grace", scope="unit", src=["presplit_cc/ingest_grace_monthly.py"],
         product="JPL GRACE/GRACE-FO mascon lwe_thickness", family="GRACE", units={"grace_lwe": "cm"},
         notes="GRACE -> GRACE-FO gap about 2017-06..2018-05 (58% NaN 2017-18, AUDIT_REPORT.md item 4)"),
    dict(cols=["deeprec_twsa"], kind="month", scope="unit", src=["presplit_cc/ingest_deeprec_tws.py"],
         product="DeepRec GRACE reconstruction (mixture_CSR_ERA5-ONI-HI), gap-free monthly", family="DeepRec",
         units={"deeprec_twsa": "cm"},
         notes="its predictors include ONI (a centred index) and ISIMIP land use from LUH2 (defo_ban.py:51-53)"),
    dict(cols=["esacci_sm"], kind="month", scope="unit", src=["presplit_cc/ingest_esacci_sm.py"],
         product="ESA CCI soil moisture COMBINED v09.2, daily -> monthly mean", family="ESA CCI SM",
         sensor="microwave (active+passive)", units={"esacci_sm": "m3 m-3"}, legal={"esacci_sm": (0, 1)},
         notes="jointly retrieved with VOD from the same brightness temperatures, so it partly reads greenness "
               "(fire_ban.py:51-53); 27.4% of rows missing (pm25_ban.py:108)"),
    dict(cols=["clf_dry", "clf_wet"], kind="year", scope="unit", src=["presplit_cc/save_regime_to_panel.py"],
         product="annual regime probabilities from a classifier TRAINED ON NDVI tertiles (<= 2019 OOF; 2020-23 predicted)",
         family="regime classifier", units={"clf_dry": "1", "clf_wet": "1"}, legal={"clf_dry": (0, 1), "clf_wet": (0, 1)},
         notes="trained_on V11_mean_ndvi (save_regime_to_panel.py:1-5): a G-LINEAGE flag for any NDVI target"),
    dict(cols=["V04_precip_seasonality"], kind="year", scope="unit", src=[AM],
         product="CV of the 12 monthly V02 values of the calendar year, broadcast to all months "
                 "(assemble_monthly_panel.py:148-163)", family="derived", units={"V04_precip_seasonality": "1"},
         legal={"V04_precip_seasonality": (0, None)}, derived_from="V02_total_precip_mm",
         notes="an annual summary of the year's own rainfall (pm25_ban.py:136-137)"),
]

# per-column units/legal ranges for two families, set here to keep the table above readable
for _f in FAMILIES:
    if _f["cols"][0] == "aglw_cattle":
        _f["units"] = {c: "log1p(head km-2)" for c in ["aglw_cattle", "aglw_buffalo", "aglw_horse", "aglw_sheep",
                                                       "aglw_goats"]}
        _f["units"]["aglw_total_lsu"] = "log1p(LSU km-2)"
        _f["legal"] = {c: (0, None) for c in _f["cols"]}
    if _f["cols"][0] == "dist_powerplant":
        _f["units"] = {c: "km" for c in _f["cols"]}
        _f["legal"] = {c: (0, None) for c in _f["cols"]}

UNIT_CANON = {"degc": "degC", "c": "degC", "degc_anomaly": "K (anomaly)", "k": "K", "kelvin": "K",
              "percent": "percent", "%": "percent", "pct": "percent", "pct_0_100": "percent",
              "mm": "mm", "kpa": "kPa", "m/s": "m s-1", "m_per_s": "m s-1", "m s-1": "m s-1",
              "w/m2": "W m-2", "w m-2": "W m-2", "w_per_m2": "W m-2", "days": "day", "doy": "day of year",
              "day_of_year": "day of year", "day-of-year": "day of year", "count": "count", "index": "1",
              "zscore": "1", "z": "1", "fraction": "1", "frac": "1", "fraction_0_1": "1", "kg/kg": "kg kg-1",
              "kg_per_kg": "kg kg-1", "m": "m", "j/m2": "J m-2", "j_per_m2": "J m-2", "g/kg": "g kg-1",
              "cmol/kg": "cmol kg-1", "g/cm3": "g cm-3", "cm3/cm3": "cm3 cm-3", "km": "km", "km2": "km2",
              "deg": "degree", "degrees": "degree", "ph": "pH", "cos": "1", "ratio": "1", "cm": "cm",
              "m3/m3": "m3 m-3", "ppm": "ppm", "kgc/m2": "kg C m-2", "kgc/m2/month": "kg C m-2 month-1",
              "degc-days": "degC day", "degc_days": "degC day", "mm/day": "mm day-1", "mm/month": "mm month-1",
              "standardized": "1", "binary": "1", "prob": "1", "probability": "1", "category_code": "1",
              "class": "1", "head/km2": "head km-2", "cm_water_equiv": "cm"}
MONTHLY_MM = {"V02_total_precip_mm", "V07_total_ref_ET_mm", "aet_total_mm", "climate_water_deficit_mm"}


def audit_units():
    """Seed units and a 'hard' legal range from presplit_cc/audit/_check_spec.json (several agents' specs per
    column): the most common unit after normalising the spelling, and the WIDEST hard range."""
    p = os.path.join(PC, "audit", "_check_spec.json")
    cs = json.load(open(p, encoding="utf-8"))["column_specs"]
    out = {}
    for c, specs in cs.items():
        cnt = collections.Counter()
        for s in specs:
            u = s.get("unit")
            if u is None:
                continue
            cnt[UNIT_CANON.get(str(u).strip().lower(), str(u).strip())] += 1
        lo = [s["hard_min"] for s in specs if s.get("hard_min") is not None]
        hi = [s["hard_max"] for s in specs if s.get("hard_max") is not None]
        unit = cnt.most_common(1)[0][0] if cnt else ""
        if c in MONTHLY_MM:
            unit = "mm month-1"
        out[c] = dict(unit=unit, lo=min(lo) if lo else None, hi=max(hi) if hi else None, n=len(specs))
    return out, "presplit_cc/audit/_check_spec.json"


def panel_facts(panel_cols, panel_dtypes):
    """One fact dict per panel column. Fail loudly if a column has no family or two."""
    au, au_src = audit_units()
    facts, seen = {}, collections.Counter()
    for fam in FAMILIES:
        for c in fam["cols"]:
            seen[c] += 1
    dup = [c for c, n in seen.items() if n > 1]
    missing = [c for c in panel_cols if c not in seen]
    extra = [c for c in seen if c not in panel_cols]
    if dup or missing or extra:
        raise SystemExit("export_review_csv: panel facts table out of step with the panel schema\n"
                         "  duplicated: %s\n  panel columns with no facts: %s\n  facts for absent columns: %s"
                         % (dup, missing, extra))
    for fam in FAMILIES:
        for c in fam["cols"]:
            f = dict(name=c, dtype=panel_dtypes[c], kind=fam["kind"], scope=fam["scope"], product=fam["product"],
                     family=fam["family"], sensor=fam.get("sensor", ""), notes=fam.get("notes", ""),
                     baseline=fam.get("baseline"), derived_from=fam.get("derived_from"),
                     sum_group=fam.get("sum_group"))
            if fam["kind"] == "trailing":
                f["n"] = fam["trailing"][c]
            if fam["kind"] == "centred":
                f["n"] = fam["centred"][c]
            # units: family override > audit spec > blank
            uo = (fam.get("units") or {}).get(c)
            a = au.get(c)
            if uo:
                f["units"], f["units_source"] = uo, "hand seed from the ingest code / product (see provenance)"
            elif a and a["unit"]:
                f["units"], f["units_source"] = a["unit"], "%s (most common of %d specs)" % (au_src, a["n"])
            else:
                f["units"], f["units_source"] = "", "unknown"
            lo = (fam.get("legal") or {}).get(c)
            if lo is not None:
                f["legal"], f["legal_source"] = lo, "hand seed (physical bound of the stored quantity)"
            elif a and (a["lo"] is not None or a["hi"] is not None) and fam["kind"] != "key":
                f["legal"], f["legal_source"] = (a["lo"], a["hi"]), \
                    "%s (widest hard range of %d specs; not a cited product range)" % (au_src, a["n"])
            else:
                f["legal"], f["legal_source"] = (None, None), "unknown"
            # provenance locator: first line naming the column in the family's source files
            f["provenance"] = ""
            for s in fam["src"]:
                path = os.path.join(ROOT, s)
                if not os.path.exists(path):
                    continue
                n = grep_line(path, r"[\"']%s[\"']" % re.escape(c)) or grep_line(path, r"\b%s\b" % re.escape(c))
                if n:
                    f["provenance"] = "%s:%d" % (s, n)
                    break
            if not f["provenance"]:
                f["provenance"] = "%s (column not named in source; family product: %s)" % (fam["src"][0], fam["product"][:50])
            facts[c] = f
    return facts


def timing_words(f):
    """(cadence, stamp, window_length, window_align, window_dict) in words for one column's facts."""
    k = f["kind"]
    if k == "key":
        return "key", "n/a", "n/a", "n/a", dict(length=None, unit=None, align="n/a")
    if k == "static":
        return "static", "n/a", "n/a", "n/a", dict(length=None, unit=None, align="n/a")
    if k == "month":
        return "1 month", "period_end", "1 month", "backward", dict(length=1, unit="month", align="backward")
    if k == "month_instant":
        return "1 month", "period_end", "instant (end of month)", "backward", \
            dict(length=0, unit="month", align="backward", text="instant at month end")
    if k == "trailing":
        return "1 month", "period_end", "%d month" % f["n"], "backward", dict(length=f["n"], unit="month", align="backward")
    if k == "centred":
        return "1 month", "period_centre", "%d month" % f["n"], "centred", dict(length=f["n"], unit="month", align="centred")
    if k == "unknown":
        return "1 month", "unknown", "unknown", "unknown", dict(length=None, unit="month", align="unknown", max_length=None)
    if k == "year":
        return "1 year", "period_end", "1 year", "backward", dict(length=1, unit="year", align="backward")
    if k == "year_doy65":
        return "1 year", "period_start", "1 year from DOY 65", "forward", \
            dict(length=1, unit="year", align="forward", offset="starts day-of-year 65")
    if k == "year_unknown":
        return "1 year", "unknown", "about 1 year (detection window unknown)", "unknown", \
            dict(length=None, unit="year", align="unknown", max_length=None)
    if k == "month_pad8":
        return "1 month", "period_centre", "1 month + 8 day each side", "centred", \
            dict(length=1, unit="month", align="centred", pad_days_each_side=8)
    if k == "mod13c2":
        return "1 month", "unknown", "1 month from overlapping 16-day composites", "unknown", \
            dict(length=1, unit="month", align="unknown", note="reach past month end set by the M0 V11 audit")
    if k == "recursive":
        return "1 month", "period_end", "unbounded (Palmer recursion)", "backward", \
            dict(length=None, unit="month", align="backward", text="recursive, long memory, never forward")
    if k == "grace":
        return "1 month", "unknown", "about 1 month (solution dates vary)", "unknown", \
            dict(length=1, unit="month", align="unknown", max_length=None)
    raise SystemExit("export_review_csv: unknown window kind %r" % k)


# ================================================================================================
# 3. CHEAP MEASUREMENTS: parquet footers and a tiny cadence sample (both cached on D:, new files only)
# ================================================================================================
def fingerprint(files):
    h = hashlib.sha1()
    for p in sorted(files):
        st = os.stat(p)
        h.update(("%s|%d|%d\n" % (os.path.basename(p), st.st_size, int(st.st_mtime))).encode())
    return h.hexdigest()[:12]


def list_store(d, rx):
    """[(group, year_or_None, path)] for files in d whose name matches rx (group[, year])."""
    out = []
    if not os.path.isdir(d):
        return out
    r = re.compile(rx)
    for e in os.scandir(d):
        if not e.is_file():
            continue
        m = r.match(e.name)
        if m:
            g = m.group(1)
            y = int(m.group(2)) if m.lastindex and m.lastindex >= 2 else None
            out.append((g, y, e.path))
    return sorted(out)


def scan_footers(name, entries, cache_dir, refresh):
    """Long table (group, year, column, rows, nulls, vmin, vmax) from parquet footers only."""
    if not entries:
        return pd.DataFrame(columns=["group", "year", "column", "rows", "nulls", "vmin", "vmax"])
    fp = fingerprint([p for _, _, p in entries])
    cache = os.path.join(cache_dir, "footers_%s_%s.parquet" % (name, fp))
    if os.path.exists(cache) and not refresh:
        return pd.read_parquet(cache)
    log("  reading %d parquet footers for %s (metadata only) ..." % (len(entries), name))
    recs = []
    for i, (g, y, p) in enumerate(entries):
        md = pq.ParquetFile(p).metadata
        ncol = md.num_columns
        acc = {}
        for rgi in range(md.num_row_groups):
            rg = md.row_group(rgi)
            for ci in range(ncol):
                c = rg.column(ci)
                nm = c.path_in_schema
                a = acc.setdefault(nm, [0, 0, None, None, True])
                a[0] += rg.num_rows
                s = c.statistics
                if s is None or not s.has_null_count:
                    a[4] = False
                    continue
                a[1] += s.null_count
                if s.has_min_max and isinstance(s.min, (int, float)) and not isinstance(s.min, bool):
                    a[2] = s.min if a[2] is None else min(a[2], s.min)
                    a[3] = s.max if a[3] is None else max(a[3], s.max)
        for nm, (rows, nulls, vmin, vmax, ok) in acc.items():
            recs.append((g, -1 if y is None else y, nm, rows, nulls if ok else -1,
                         np.nan if vmin is None else float(vmin), np.nan if vmax is None else float(vmax)))
        if (i + 1) % 500 == 0:
            log("    %d / %d" % (i + 1, len(entries)))
    df = pd.DataFrame(recs, columns=["group", "year", "column", "rows", "nulls", "vmin", "vmax"])
    safe_write_new(cache, lambda t: df.to_parquet(t, index=False))
    return df


def cadence_probe(cache_dir, refresh, cols):
    """Within-year and between-year behaviour of every panel column on 5 small regions x 2 years.
    A SAMPLE, not a verification: it says what the stored numbers do, not what the product is."""
    files = [os.path.join(PANEL_DIR, "%s_monthly_%d.parquet" % (r, y)) for r in PROBE_REGIONS for y in PROBE_YEARS]
    files = [p for p in files if os.path.exists(p)]
    fp = fingerprint(files)
    cache = os.path.join(cache_dir, "cadence_probe_raw_%s.json" % fp)   # raw numbers only; summary rebuilt each run
    if os.path.exists(cache) and not refresh:
        with open(cache, encoding="utf-8") as fh:
            raw = json.load(fh)
        return summarise_probe(raw, cols, files)
    log("  cadence probe: %d small panel files (%s x %s) ..." % (len(files), PROBE_REGIONS, PROBE_YEARS))
    per = {c: {} for c in cols}
    lagv_thar = None
    for r in PROBE_REGIONS:
        frames = {}
        for y in PROBE_YEARS:
            p = os.path.join(PANEL_DIR, "%s_monthly_%d.parquet" % (r, y))
            if os.path.exists(p):
                d = pd.read_parquet(p)
                for c in d.columns:
                    if d[c].dtype.kind == "f":
                        v = d[c].to_numpy()
                        bad = np.isin(v, FILLS) | (np.abs(v) >= 1e30)
                        if bad.any():
                            d.loc[bad, c] = np.nan
                frames[y] = d
        if not frames:
            continue
        num = [c for c in cols if c not in KEY_COLS and c in next(iter(frames.values())).columns
               and next(iter(frames.values()))[c].dtype.kind in "fiu"]
        within = {}
        firsts = {}
        for y, d in frames.items():
            g = d.groupby("cell_id", sort=True)
            nun = g[num].nunique(dropna=True)
            within[y] = {c: float((nun[c] > 1).mean()) for c in num}
            firsts[y] = g[num].first()
            if r == "thar_desert" and y == max(frames):
                # run89 computes its lag parents on thar_desert's first 200 cells: median nunique within cell-year > 1
                sub = nun.iloc[:200]
                lagv_thar = sorted(c for c in num if float(sub[c].median()) > 1)
        ys = sorted(frames)
        for c in num:
            allnull = all(frames[y][c].isna().all() for y in ys)
            wv = max(within[y][c] for y in ys)
            bv = None
            if len(ys) == 2:
                a, b = firsts[ys[0]][c], firsts[ys[1]][c]
                j = a.index.intersection(b.index)
                aa, bb = a.loc[j].to_numpy(np.float64), b.loc[j].to_numpy(np.float64)
                ok = np.isfinite(aa) & np.isfinite(bb)
                bv = float((np.abs(aa[ok] - bb[ok]) > 1e-6).mean()) if ok.any() else None
            zero = (not allnull) and all(float(np.nanmax(np.abs(frames[y][c].to_numpy(np.float64)))) == 0.0
                                         for y in ys if frames[y][c].notna().any())
            per[c][r] = dict(all_null=bool(allnull), within_year_varying_share=round(wv, 7),
                             between_year_changed_share=None if bv is None else round(bv, 7), all_zero=bool(zero))
    raw = dict(per=per, lagv=lagv_thar)

    def dump(t):
        with open(t, "w", encoding="utf-8") as fh:
            json.dump(raw, fh, indent=1)
    safe_write_new(cache, dump)
    return summarise_probe(raw, cols, files)


def summarise_probe(raw, cols, files):
    per, lagv_thar = raw["per"], raw["lagv"]
    summary = {}
    for c in cols:
        if c in KEY_COLS:
            continue
        rs = per.get(c, {})
        if not rs:
            summary[c] = dict(observed="not numeric / absent in sample", regions=rs)
            continue
        live = {r: v for r, v in rs.items() if not v["all_null"]}
        # copies of an annual or static value are EXACT copies, so any non-zero share is evidence; the share
        # is printed so a reader can judge a sparse signal (monthly conflict counts vary in few cells)
        wmax = max([v["within_year_varying_share"] for v in live.values()] or [0.0])
        bmax = max([(v["between_year_changed_share"] or 0.0) for v in live.values()] or [0.0])
        nw = sum(1 for v in live.values() if v["within_year_varying_share"] > 0)
        if not live:
            obs = "all-null in the sample"
        elif wmax > 0:
            obs = "varies within a year (monthly) in %d/%d sampled regions (max %.2f%% of cells)" % (nw, len(live), 100 * wmax)
        elif bmax > 0:
            obs = "constant within each year, changes between years (annual; max %.2f%% of cells changed)" % (100 * bmax)
        else:
            obs = "constant within and between the sampled years (static in sample)"
        nz = sum(1 for v in live.values() if v["all_zero"])
        if live and nz == len(live):
            obs += "; all zero in the sample"
        elif nz:
            obs += "; all zero in %d/%d regions" % (nz, len(live))
        nn = sum(1 for v in rs.values() if v["all_null"])
        if nn and live:
            obs += "; all-null in %d/%d regions" % (nn, len(rs))
        summary[c] = dict(observed=obs, regions=rs)
    out = dict(sample=dict(regions=PROBE_REGIONS, years=PROBE_YEARS, files=[p.replace("\\", "/") for p in files],
                           rule="within-year varying = any cell with >1 distinct value in a year; between-year "
                                "changed = any cell whose first value differs between the two years (shares "
                                "printed); fills -32768/-32767/-2^31/-2^31+1 and |x|>=1e30 masked first"),
               columns=summary, run89_lag_parents_thar=lagv_thar)
    return out


def expected_kind_class(kind):
    return {"month": "monthly", "month_instant": "monthly", "trailing": "monthly", "centred": "monthly",
            "unknown": "monthly", "mod13c2": "monthly", "month_pad8": "monthly", "recursive": "monthly",
            "grace": "monthly", "year": "annual", "year_doy65": "annual", "year_unknown": "annual",
            "static": "static"}.get(kind)


def observed_class(obs):
    if obs.startswith("varies within"):
        return "monthly"
    if obs.startswith("constant within each year"):
        return "annual"
    if obs.startswith("constant within and between"):
        return "static"
    return None


# ================================================================================================
# 4. GROUPS PER PROBLEM (for the footer-based missing shares)
# ================================================================================================
def read_split_txt(path):
    sec, d = None, {"donors": [], "tests": []}
    for ln in open(path, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        if ln in ("donors", "tests"):
            sec = ln
            continue
        d[sec].append(ln)
    return d["donors"], d["tests"]


def problem_groups():
    g = {}
    L = module_lists(os.path.join(ROOT, "pm25_split.py"))
    g["pm25"] = ([v for v, _ in need(L, "DONORS", "pm25_split.py")], [v for v, _ in need(L, "TEST", "pm25_split.py")],
                 "pm25_split.py DONORS/TEST")
    # fire: complete regions (all 2002-2022 target files), donors = the 30 largest by panel_cells
    yrs = collections.defaultdict(set)
    for grp, y, _ in list_store(FIRE_TARGET_DIR, r"^(.+)_(\d{4})\.parquet$"):
        yrs[grp].add(y)
    complete = sorted(r for r, s in yrs.items() if set(range(2002, 2023)) <= s)
    size = pd.read_csv(FIRE_SIZES)
    size = size[size.region.isin(complete)].sort_values("panel_cells", ascending=False)
    ndon = int(re.search(r'N_DONORS = _num\("--donors", (\d+)', open(os.path.join(ROOT, "fire_evt_arch.py"),
                                                                     encoding="utf-8").read()).group(1))
    fd = list(size.region.head(ndon))
    g["fire"] = (fd, [r for r in size.region if r not in fd],
                 "D:/fire/region_sizes.csv top %d by panel_cells (fire_evt_arch.py N_DONORS; adaptation.py run_fire)" % ndon)
    # defo: forested regions (frac_tc30 >= 0.25, sorted by cells) intersected with ndvi_split; 25 donors, 17 tests
    dn, ts = read_split_txt(NDVI_SPLIT)
    cn = pd.read_csv(FOREST_CENSUS)
    forested = cn[cn.frac_tc30 >= 0.25].sort_values("cells").region.tolist()
    src = open(os.path.join(ROOT, "defo_corrector.py"), encoding="utf-8").read()
    nd = int(re.search(r'NDON\s*=\s*T\._a\("--donors", (\d+)', src).group(1))
    nt = int(re.search(r'NTEST\s*=\s*T\._a\("--tests", (\d+)', src).group(1))
    g["defo"] = ([r for r in forested if r in dn][:nd], [r for r in forested if r in ts][:nt],
                 "forest_census frac_tc30 >= 0.25 x ndvi_split (defo_corrector.py NDON=%d NTEST=%d)" % (nd, nt))
    g["ndvi"] = (dn, ts, "D:/run89full/ndvi_split.txt (89 donors / 44 tests; HEADLINE_RUN_PLAN.md:109 option a)")
    return g


# ================================================================================================
# 5. MISSING-SHARE NOTES (footer null_count; never a full scan)
# ================================================================================================
def share_note(ft, col, donors, tests, donor_years, test_years, per_year=True, label=""):
    """(note, flags) -- flags is a list of R30 flag strings."""
    if ft is None or ft.empty:
        return "footers not read", []
    d = ft[ft.column == col]
    if d.empty:
        return "column absent from the store footers", []
    if (d.nulls < 0).any():
        return "footer has no null_count for this column", []
    flags = []
    groups = set(donors) | set(tests)
    have = set(d.group)
    absent = sorted(groups - have)
    parts = []
    if per_year:
        dd = d[d.group.isin(donors) & d.year.isin(donor_years)]
        if dd.rows.sum() > 0:
            s = dd.nulls.sum() / dd.rows.sum()
            parts.append("donor rows %d-%d: %.1f%% null" % (min(donor_years), max(donor_years), 100 * s))
            if s > 0.25:
                flags.append("R30 FLAG: %.0f%% missing in donor rows (> 25%%)" % (100 * s))
        ty = []
        for y in test_years:
            t = d[d.group.isin(tests) & (d.year == y)]
            if t.rows.sum() > 0:
                s = t.nulls.sum() / t.rows.sum()
                ty.append("%d %.1f%%" % (y, 100 * s))
                if s > 0.9:
                    flags.append("R30 FLAG: vanishes in test year %d (%.0f%% null)" % (y, 100 * s))
            else:
                ty.append("%d no file" % y)
        parts.append("test groups by year: " + ", ".join(ty))
        win = d[d.group.isin(groups) & d.year.isin(list(donor_years) + list(test_years))]
    else:
        dd = d[d.group.isin(donors)]
        if dd.rows.sum() > 0:
            s = dd.nulls.sum() / dd.rows.sum()
            parts.append("donor groups, whole file (all years): %.1f%% null" % (100 * s))
            if s > 0.25:
                flags.append("R30 FLAG: %.0f%% missing over donor files (> 25%%; whole-period share)" % (100 * s))
        tt = d[d.group.isin(tests)]
        if tt.rows.sum() > 0:
            parts.append("test groups, whole file: %.1f%% null" % (100 * tt.nulls.sum() / tt.rows.sum()))
        win = d[d.group.isin(groups)]
    if not win.empty:
        agg = win.groupby("group").agg(rows=("rows", "sum"), nulls=("nulls", "sum"), vmin=("vmin", "min"),
                                       vmax=("vmax", "max"))
        alln = int((agg.nulls == agg.rows).sum())
        zero = int(((agg.vmin == 0) & (agg.vmax == 0) & (agg.nulls < agg.rows)).sum())
        const = int(((agg.vmin == agg.vmax) & (agg.vmin != 0) & (agg.nulls < agg.rows)).sum())
        sent = int((win.vmin.isin(FILLS) | (win.vmax.abs() >= 1e30) | win.vmax.isin(FILLS)).sum())
        extra = []
        if alln:
            extra.append("all-null in %d/%d groups" % (alln, len(agg)))
        if zero:
            extra.append("constant ZERO (not null) in %d/%d groups" % (zero, len(agg)))
        if const:
            extra.append("constant non-zero in %d/%d groups" % (const, len(agg)))
        if sent:
            extra.append("a fill code is the footer min or max in %d files (sentinel present as a number)" % sent)
        parts += extra
    if absent:
        parts.append("no file for %d groups (%s%s)" % (len(absent), ", ".join(absent[:6]), ", ..." if len(absent) > 6 else ""))
    note = (label + ": " if label else "") + "; ".join(parts)
    return note, flags


# ================================================================================================
# 6. LAG NOTES (what R8 would need to know) and co-measured candidates
# ================================================================================================
def lag_note(f, target, co_measured, verdict):
    k = f["kind"]
    pre = "banned: R8 not needed while banned. If kept: " if verdict == "ban" else ""
    cm = " Co-measured -> at least 1 step." if co_measured else ""
    if k == "key":
        return "key role, never a feature"
    if k == "static":
        return pre + "static: no time axis, lag 0; G-EPOCH compares the layer's content epoch with the cut" + cm
    if target == "monthly":
        m = {
            "month": "window = the named month; newest data = its end = the nowcast reference -> lag 0",
            "month_instant": "value at the END of the named month = the nowcast reference -> lag 0",
            "trailing": "trailing %s-month window ending at the named month -> lag 0" % f.get("n"),
            "centred": "centred %s-month window reaches %d month(s) past the named month -> lag %d"
                       % (f.get("n"), int(math.ceil((f.get("n", 1) - 1) / 2.0)), int(math.ceil((f.get("n", 1) - 1) / 2.0))),
            "unknown": "window UNKNOWN -> R8 refuses it at lag 0; the owner signs an assumed maximum window w "
                       "(lag = ceil((w-1)/2) months for a centred index) or the F10 audit supplies the window",
            "year": "calendar-year value reaches up to 11 months past a January row -> year -1 (Q3 a; PM2.5's rule)",
            "year_doy65": "product year runs to DOY 64 of the NEXT year -> Jan-early-Mar rows need year -2; one fixed "
                          "lag per column -> year -2",
            "year_unknown": "annual value whose detection window may pass the calendar year -> at least year -1; "
                            "refused until the window (or a signed bound) is known",
            "month_pad8": "monthly mean of daily values that each use a 16-day centred window -> reaches 8 days past "
                          "month end -> lag 1 month",
            "mod13c2": "monthly composite from 16-day inputs; lag 0 if the M0 V11 audit finds no reach past month end, "
                       "else lag 1",
            "recursive": "recursive index with long BACKWARD memory, never forward -> lag 0",
            "grace": "solution windows do not always match calendar months -> sign an assumed window; lag 0 or 1",
        }[k]
    else:  # annual target (defo): the feature script aggregates Jan-Dec of the target year
        m = {
            "month": "annual aggregate (mean/min/max) of Jan-Dec ends Dec 31 = the reference -> lag 0",
            "month_instant": "annual aggregate ends Dec 31 = the reference -> lag 0",
            "trailing": "trailing windows end inside the year -> annual aggregate lag 0",
            "centred": "the December value's centred window reaches into January of t+1 -> lag 1 year, unless the "
                       "feature script shifts the monthly series back first (plan 3.2)",
            "unknown": "window UNKNOWN -> refused at lag 0 until a window or a signed bound exists; with a centred "
                       "window the December value reaches past Dec 31 -> lag 1 year",
            "year": "same-year value ends Dec 31 = the reference -> lag 0 under 9.1 item 3 (a); year -1 under (b)",
            "year_doy65": "product year reaches about Mar 5 of t+1 -> lag 1 year",
            "year_unknown": "detection window may pass Dec 31 -> lag 1 year until the window is known",
            "month_pad8": "December's mean reaches Jan 8 of t+1 -> lag 1 year",
            "mod13c2": "December's composite may reach into January -> lag 0 or 1 year per the M0 V11 audit",
            "recursive": "backward memory only -> lag 0",
            "grace": "December solution may reach into January -> sign an assumed window",
        }[k]
    return pre + m + "." + cm


# ================================================================================================
# 7. ROW BUILDER
# ================================================================================================
def mk(column, store, verdict, reason, locator, facts=None, cadence="", stamp="", wl="", wa="", units="",
       lo=None, hi=None, lagn="", cm="no", miss="", notes=""):
    if verdict not in VERDICTS:
        raise SystemExit("export_review_csv: verdict %r for %s is not in %s" % (verdict, column, sorted(VERDICTS)))
    if facts is not None:
        cadence, stamp, wl, wa, _ = timing_words(facts)
        units = facts.get("units", "")
        lo, hi = facts.get("legal", (None, None))
    fmt = lambda v: "" if v is None else ("inf" if v == float("inf") else ("%g" % v))
    return dict(column=column, store=store, current_verdict=verdict, current_reason=reason, source_locator=locator,
                cadence=cadence, stamp=stamp, window_length=wl, window_align=wa, units=units,
                legal_min=fmt(lo), legal_max=fmt(hi) if hi is not None else ("inf" if lo is not None else ""),
                fact_status="unverified", lag_note=lagn, co_measured_candidate=cm, missing_share_note=miss,
                owner_verdict="", owner_timing_signed="", notes=notes)


def join_notes(*xs):
    return " | ".join(x for x in xs if x)


def probe_note(probe, f):
    c = f["name"]
    s = probe["columns"].get(c)
    if not s:
        return ""
    obs = s["observed"]
    exp, got = expected_kind_class(f["kind"]), observed_class(obs)
    out = "sample (5 regions x 2010/2015): " + obs
    if exp and got and exp != got and not (exp == "annual" and got == "static") \
            and not (exp == "monthly" and got in ("static", "annual") and "all zero" in obs):
        out += " [DIFFERS from the seeded cadence '%s' -- check]" % exp
    return out


# ------------------------------------------------------------------------------------------------
CM = {  # co-measured candidates per problem: column -> why (yes). Everything else: 'no'.
    "pm25": {
        **{c: "MODIS land product (same sensors as the MODIS AOD that ACAG V5 assimilates); atmospheric-correction "
              "channel (pm25_ban.py:64-73)" for c in ["V11_mean_ndvi", "V12_mean_evi", "V13_mean_lst_C",
                                                      "nighttime_lst_C", "V14_mean_albedo", "snow_cover_fraction",
                                                      "gpp_kgC_m2", "tree_cover_pct", "V15_bare_ground_pct",
                                                      "V17_herb_cover_pct", "modis_landcover_class",
                                                      "modis_landcover_annual", "cropland_fraction",
                                                      "shrub_cover_pct_global", "phenology_sos_doy"]},
        "cloud_frequency_pct": "MOD08_M3 is the MODIS L3 atmosphere product family that carries the aerosol "
                               "retrievals; smoke/dust flagged as cloud (pm25_ban.py:68-70)",
        **{c: "FireCCI <= 2019 is MODIS reflectance; same smoke events" for c in
           ["V20_burned_binary", "burn_month_count", "burn_doy_mean"]},
        "burn_frac": "LINEAGE check: ACAG's GEOS-Chem biomass-burning emissions are GFED-based (verify in the V5.GL "
                     "docs); GFED4s burned area is MODIS MCD64A1",
        "burn_lag1": "as burn_frac (lag 1 of the same GFED column)",
        **{c: "LINEAGE check: GEOS-Chem anthropogenic emissions in ACAG may come from EDGAR/CEDS (verify)" for c in
           ["edgar_so2", "edgar_nox", "edgar_nh3", "edgar_bc", "edgar_oc"]},
    },
    "fire": {
        **{c: "MODIS product, same sensor and month as MCD64A1; a burn scar changes it in the same month "
              "(fire_ban.py:57-60)" for c in ["V11_mean_ndvi", "V12_mean_evi", "V13_mean_lst_C", "nighttime_lst_C",
                                              "V14_mean_albedo", "snow_cover_fraction", "gpp_kgC_m2"]},
        "cloud_frequency_pct": "RULED co-measured: same-month MODIS cloud, lag 1 (Q3 a)",
        **{c: "MODIS land product; MCD12Q1 is an input to MCD64A1 (fire_ban.py:44-45)" for c in
           ["modis_landcover_class", "modis_landcover_annual", "cropland_fraction", "shrub_cover_pct_global",
            "phenology_sos_doy", "tree_cover_pct", "V15_bare_ground_pct", "V17_herb_cover_pct"]},
        **{c: "FireCCI burned area (MODIS <= 2019): the same fire event measured again" for c in
           ["V20_burned_binary", "burn_month_count", "burn_doy_mean"]},
    },
    "defo": {
        **{c: "defo_ban LAG rule: measures the clearing concurrently (defo_ban.py:116-137)" for c in
           ["V20_burned_binary", "burn_month_count", "burn_doy_mean", "V11_mean_ndvi", "V12_mean_evi",
            "V13_mean_lst_C", "nighttime_lst_C", "V14_mean_albedo", "gpp_kgC_m2", "esacci_sm",
            "snow_cover_fraction", "cloud_frequency_pct", "ntl"]},
        **{c: "tree-cover product family (MOD44B): the target read from MODIS (defo_ban.py:28-33)" for c in
           ["tree_cover_pct", "V15_bare_ground_pct", "V17_herb_cover_pct"]},
        **{c: "MODIS land cover sees the clearing in the same year (defo_ban.py:36-41)" for c in
           ["modis_landcover_class", "modis_landcover_annual", "cropland_fraction", "shrub_cover_pct_global",
            "phenology_sos_doy"]},
        "built_surface_fraction": "Landsat/Sentinel-2 lineage (GHSL), same sensor family as Hansen",
        **{c: "LINEAGE: LUH2 forest transitions constrained by Hansen loss (defo_ban.py:43-47)" for c in
           ["luh2_forest", "luh2_secondary", "luh2_cropland", "luh2_pasture", "luh2_range", "luh2_urban"]},
        "deeprec_twsa": "LINEAGE at one remove: ISIMIP land use from LUH2 (defo_ban.py:51-53)",
    },
    "ndvi": {
        "V11_mean_ndvi": "IS the target (MOD13C2 NDVI)",
        "V12_mean_evi": "target twin: same MOD13C2 file and month",
        **{c: "MODIS product, same sensor and month as MOD13C2" for c in
           ["V13_mean_lst_C", "nighttime_lst_C", "V14_mean_albedo", "snow_cover_fraction", "gpp_kgC_m2"]},
        "cloud_frequency_pct": "MODIS cloud fraction; cloud cover drives MOD13 compositing and the climatology "
                               "backfill (Part 390)",
        **{c: "MODIS land product derived from the same reflectances" for c in
           ["tree_cover_pct", "V15_bare_ground_pct", "V17_herb_cover_pct", "modis_landcover_class",
            "modis_landcover_annual", "cropland_fraction", "shrub_cover_pct_global", "phenology_sos_doy"]},
        **{c: "FireCCI <= 2019 is MODIS reflectance; a burn browns NDVI in the same month" for c in
           ["V20_burned_binary", "burn_month_count", "burn_doy_mean"]},
        "burn_frac": "RULED co-measured (Q38 b): GFED burn at lag 1 only; GFED4s burned area is MODIS MCD64A1",
    },
}


def cm_value(problem, col):
    why = CM[problem].get(col)
    return ("yes: " + why) if why else "no"


# ================================================================================================
# 8. PER-PROBLEM TABLES
# ================================================================================================
class Ctx(object):
    pass


def lists(path):
    return module_lists(os.path.join(ROOT, path))


def list_locs(path, names):
    """{column: (list_name, 'path:line')} for every member of the named lists (first list wins)."""
    L = lists(path)
    out = {}
    for n in names:
        for v, ln in need(L, n, path):
            out.setdefault(v, (n, "%s:%d" % (path, ln)))
    return out


def pm25_rows(C):
    P = "pm25_ban.py"
    L = lists(P)
    D = lists("defo_ban.py")
    idx = {}
    for n in ["BAN_LOOKAHEAD", "BAN_TREND", "DROP_INCOMPLETE", "CONDITIONAL_OPTICAL", "CONDITIONAL_MODIS_LC",
              "ANNUAL_LAG1", "WATCH_GWR", "KEYS"]:
        for v, ln in need(L, n, P):
            idx.setdefault(v, []).append((n, "%s:%d" % (P, ln)))
    for v, ln in need(D, "FREEZE", "defo_ban.py"):
        idx.setdefault(v, []).append(("BAN_FREEZE", "defo_ban.py:%d (imported at pm25_ban.py:%d)"
                                      % (ln, grep_line(os.path.join(ROOT, P), r"BAN_FREEZE = "))))
    # the 105 features that reached the model
    ln9 = open(PM25_RUNLOG, encoding="utf-8", errors="replace").read().splitlines()[8]
    m = re.search(r"(\d+) features reach the model: (.*)$", ln9)
    if not m:
        raise SystemExit("export_review_csv: %s line 9 is not the feature line" % PM25_RUNLOG)
    feats = [x.strip() for x in m.group(2).split(",")]
    if len(feats) != int(m.group(1)):
        raise SystemExit("export_review_csv: run.log line 9 lists %d names but says %s" % (len(feats), m.group(1)))
    fset = set(feats)
    rows = []
    donors, tests, _ = C.groups["pm25"]
    W = WINDOWS["pm25"]
    for c in C.panel_cols:
        if c in KEY_COLS:
            continue
        f = C.facts[c]
        hits = idx.get(c, [])
        names = [h[0] for h in hits]
        locs = "; ".join(h[1] for h in hits)
        rsn, v = "", ""
        if c in ("lat", "lon"):
            v, rsn = "ban", "coordinate: pm25_ban KEYS, never a tree feature (lat is router context, see ctx:lat)"
        elif any(n in names for n in ("BAN_LOOKAHEAD",)):
            v, rsn = "ban", "look-ahead: annual summary of within-year events (pm25_ban BAN_LOOKAHEAD)"
        elif "BAN_TREND" in names:
            v, rsn = "ban", "trend proxy / baked regime / mask (pm25_ban BAN_TREND)"
        elif "DROP_INCOMPLETE" in names:
            v, rsn = "ban", "incomplete (pm25_ban DROP_INCOMPLETE)"
            if c == "amo":
                rsn += " [ruling A5: source ends Jan 2023]"
        elif "BAN_FREEZE" in names:
            v, rsn = "ban", "post-window snapshot / projected layer: defo FREEZE list [ruling A3]"
        elif "CONDITIONAL_OPTICAL" in names or "CONDITIONAL_MODIS_LC" in names:
            v, rsn = "conditional", "excluded from the headline, later ablation arm (DROP_CONDITIONAL = True, " \
                                    "pm25_architecture.py:78) [ruling A2]"
        elif "ANNUAL_LAG1" in names:
            v, rsn = "lagged", "annual column at year(origin) - 1 (pm25_architecture.py:139-160) [ruling A1]"
            if "WATCH_GWR" in names:
                rsn += "; also WATCH_GWR: score region-blocked"
        elif "WATCH_GWR" in names:
            v, rsn = "watch", "kept, flagged: a GWR covariate of the ACAG target (pm25_ban WATCH_GWR)"
        elif c in ("oni", "tni"):
            v, rsn = "lagged", "centred index: KEPT, lagged by the computed rule [ruling Q2]; the shipped U2 " \
                               "nowcast fed it at lag 0, the forecast dropped it (Part 558)"
            locs = "%s:9; HEADLINE_QUESTIONS_AND_FIXES.md:63" % PM25_RUNLOG
        elif c in fset:
            v, rsn = "keep", "in the shipped U2 feature list"
            locs = "%s:9" % PM25_RUNLOG
        else:
            raise SystemExit("export_review_csv: PM2.5 column %s is neither banned nor in the 105-feature list" % c)
        if v in ("keep", "lagged", "watch") and c not in fset:
            raise SystemExit("export_review_csv: PM2.5 %s marked %s but absent from run.log line 9" % (c, v))
        if v in ("ban", "conditional") and c in fset:
            raise SystemExit("export_review_csv: PM2.5 %s marked %s but it reached the model" % (c, v))
        extra = ""
        if c == "V20_burned_binary":
            extra = "OWNER CHECK: pm25_ban.py:34 bans V20 as an ANNUAL look-ahead aggregate, but the stored column " \
                    "is MONTHLY (ingest_firecci_fire.py:7; cadence sample), so that reason does not hold; it plays " \
                    "the same role as GFED burn_frac (which PM2.5 keeps)"
        cmv = cm_value("pm25", c)
        miss, flags = share_note(C.ft["panel"], c, donors, tests, W["donor_years"], W["test_years"])
        rows.append(mk(c, "monthly_panel_v170", v, rsn, locs, facts=f,
                       lagn=lag_note(f, "monthly", cmv.startswith("yes"), v), cm=cmv,
                       miss=join_notes(miss, "; ".join(flags)),
                       notes=join_notes(extra, probe_note(C.probe, f), f["notes"])))
    # GFED burn block (pm25_architecture.py)
    A = "pm25_architecture.py"
    bl = loc(os.path.join(ROOT, A), r'BURN_COLS = ')
    miss, flags = share_note(C.ft["gfed"], "burn_frac", donors, tests, W["donor_years"], W["test_years"])
    gf = C.side["gfed_burn"]["burn_frac"]
    rows.append(mk("burn_frac", "gfed_burn", "keep", "GFED monthly burned fraction joined at lag 0 (USE_BURN = 1); "
                   "entered through a 2020-23 screen, disclosed [ruling Q25 b]", bl, cadence="1 month",
                   stamp="period_end", wl="1 month", wa="backward", units=gf["units"], lo=0, hi=1,
                   lagn="monthly burned fraction of the named month -> lag 0 (1 if the owner rules it co-measured/lineage)",
                   cm=cm_value("pm25", "burn_frac"), miss=join_notes(miss, "; ".join(flags)),
                   notes="6 panel groups have no GFED file (store fact absent_groups); pm25_architecture.py:170-176 "
                         "skips missing files silently today"))
    rows.append(mk("burn_lag1", "engineered (package feature script: lag 1 of burn_frac)", "keep",
                   "lag 1 of burn_frac: smoke is transported (pm25_architecture.py:178-181)", bl, cadence="1 month",
                   stamp="period_end", wl="1 month", wa="backward", units=gf["units"], lo=0, hi=1,
                   lagn="engineered lag 1 of burn_frac: operation 'lag 1', derived_from burn_frac; ends one month "
                        "before its row", cm=cm_value("pm25", "burn_lag1"), miss="as burn_frac, shifted one month",
                   notes="today built with groupby.shift on rows (pm25_architecture.py:180); the engine rebuilds it "
                         "through the dense-grid lookup (G-CALENDAR)"))
    rows.append(mk("burn_npix", "gfed_burn", "ban", "not a feature: pixel count support column (pm25_ban KEYS)",
                   loc(os.path.join(ROOT, P), r'"burn_npix"'), cadence="1 month", stamp="period_end",
                   wl="1 month", wa="backward", units="count", lo=0, hi=None, lagn="not a feature", cm="no",
                   miss="", notes="support role at most"))
    el = loc(os.path.join(ROOT, A), r'EDGAR_COLS = ')
    for c in C.side["edgar_emis"]["_order"]:
        if c == "edgar_carried":
            rows.append(mk(c, "edgar_emis", "ban", "not a feature: carry-forward flag (pm25_ban KEYS)",
                           loc(os.path.join(ROOT, P), r'"edgar_carried"'), cadence="1 year", stamp="period_end",
                           wl="1 year", wa="backward", units="1", lo=0, hi=1, lagn="not a feature", cm="no",
                           notes="marks years whose values were carried forward"))
            continue
        e = C.side["edgar_emis"][c]
        miss, flags = share_note(C.ft["edgar"], c, donors, tests, [], [], per_year=False)
        rows.append(mk(c, "edgar_emis", "conditional", "EDGAR is an ADD-ON arm, not headline (USE_EDGAR = 0, "
                       "pm25_architecture.py:76) [ruling A4]", el, cadence="1 year", stamp="period_end", wl="1 year",
                       wa="backward", units=e["units"], lo=0, hi=None,
                       lagn="annual inventory: year -1 anchored to the ORIGIN (pm25_architecture.py:184-195)",
                       cm=cm_value("pm25", c), miss=join_notes(miss, "; ".join(flags)),
                       notes="the OC species is missing a sector (pm25_architecture.py:52-53)"))
    # router context
    ctxl = "pm25_adaptation.py:%d" % grep_line(os.path.join(ROOT, "pm25_adaptation.py"), r'^CTX = ')
    rows.append(mk("ctx:month", "router_context (package feature script)", "keep",
                   "router context in the shipped run (CTX = ['month', 'lat'])", ctxl, cadence="1 month", stamp="n/a",
                   wl="n/a", wa="n/a", units="month number", lo=1, hi=12,
                   lagn="router_context: read only by the router; a key-derived column is allowed only here (G-KEYS)",
                   cm="no", notes="plan 1.5: the package keeps its shipped context script"))
    rows.append(mk("ctx:lat", "router_context (package feature script)", "keep",
                   "router context in the shipped run (CTX = ['month', 'lat'])", ctxl, cadence="static", stamp="n/a",
                   wl="n/a", wa="n/a", units="degrees_north", lo=-90, hi=90,
                   lagn="router_context, static", cm="no", notes=""))
    # target
    miss, flags = share_note(C.ft["pm25_target"], "pm25_ugm3", donors, tests, W["donor_years"], W["test_years"])
    rows.append(mk("pm25_ugm3", "pm25_acag (target store)", "ban", "TARGET (role target; forced ban as a feature)",
                   loc(os.path.join(ROOT, A), r'"pm25_ugm3"'), cadence="1 month", stamp="period_end", wl="1 month",
                   wa="backward", units="ug m-3", lo=0, hi=None,
                   lagn="target: its own window (1 month) sets R8's reference and R17's start", cm="n/a (target)",
                   miss=join_notes(miss, "NaN = declared-invalid label"),
                   notes="legal range must cite the ACAG V5.GL.06 documentation; measurement_error_floor +-2 ug m-3 "
                         "(pm25_adaptation.py:144); ACAG fill 9.96921e36 masked by the ingest"))
    return rows, feats


def fire_rows(C):
    P = "fire_ban.py"
    idx = {}
    L = lists(P)
    for n in ["BAN_LABEL", "BAN_LOOKAHEAD", "BAN_POSTFIRE", "CONDITIONAL_LAG1", "SUSPECT_TREND", "KEYS"]:
        for v, ln in need(L, n, P):
            idx.setdefault(v, []).append((n, "%s:%d" % (P, ln)))
    FA = "fire_architecture.py"
    FL = lists(FA)
    hist_drop = [v for v, _ in need(FL, "HIST_DROP", FA)]
    dropc = loc(os.path.join(ROOT, FA), r"apply_ban\(X, drop_conditional=True\)")
    flags_loc = loc(os.path.join(ROOT, "adaptation.py"), r"FA\.USE_HISTORY, FA\.USE_DRIVERS = 1, 1")
    pm = lists("pm25_ban.py")
    annual_pm = {v for v, _ in need(pm, "ANNUAL_LAG1", "pm25_ban.py")}
    freeze = {v for v, _ in need(lists("defo_ban.py"), "FREEZE", "defo_ban.py")}
    snow = {"snow_onset_doy", "snow_disappearance_doy", "snow_duration_days", "snow_max_doy"}
    amospei = {"amo", "spei_01m", "spei_03m", "spei_06m", "V06_spei_12m", "spei_24m"}
    donors, tests, _ = C.groups["fire"]
    W = WINDOWS["fire"]
    rows, shipped = [], []
    for c in C.panel_cols:
        if c in KEY_COLS:
            continue
        f = C.facts[c]
        hits = idx.get(c, [])
        names = [h[0] for h in hits]
        locs = "; ".join(h[1] for h in hits)
        extra = ""
        if c in ("lat", "lon"):
            v, rsn = "ban", "coordinate: fire_ban KEYS, never a tree feature (lat is router context, see ctx:lat)"
        elif "BAN_LABEL" in names:
            v, rsn = "ban", "the label or a transform of it (fire_ban BAN_LABEL)"
        elif "BAN_LOOKAHEAD" in names:
            v, rsn = "ban", "future data in the feature: centred 16-day window (fire_ban BAN_LOOKAHEAD)"
        elif "BAN_POSTFIRE" in names:
            v, rsn = "ban", "post-fire state (fire_ban BAN_POSTFIRE)"
        elif "SUSPECT_TREND" in names:
            v, rsn = "ban", "trend / regime / mask column (fire_ban SUSPECT_TREND, dropped by default)"
        elif "CONDITIONAL_LAG1" in names:
            v, rsn = "conditional", "dropped from the shipped build (apply_ban(drop_conditional=True)); allowed " \
                                    "only at lag >= 1 per fire_ban"
            locs = join_notes(locs, dropc)
        elif c in freeze:
            v, rsn = "ban", "post-window snapshot / projected layer (defo FREEZE list) [ruling Q3 a: PM2.5's FREEZE " \
                            "ban applies to fire]; the shipped fire run fed it"
            locs = "defo_ban.py FREEZE; HEADLINE_QUESTIONS_AND_FIXES.md:108-111"
        elif c in snow:
            v, rsn = "ban", "annual snow timing = end-of-year fact [ruling Q3 a: PM2.5's snow-DOY ban applies to " \
                            "fire]; the shipped fire run fed it"
            locs = "pm25_ban.py BAN_LOOKAHEAD; HEADLINE_QUESTIONS_AND_FIXES.md:108-111"
        elif c in amospei:
            v, rsn = "ban", "PM2.5's AMO/SPEI ban [ruling Q3 a, literal reading]; the shipped fire run fed it"
            locs = "pm25_ban.py DROP_INCOMPLETE; HEADLINE_QUESTIONS_AND_FIXES.md:108-111"
            extra = "OWNER CHECK: PM2.5's reason (empty in 2023) does not bite fire's 2003-2022 coverage; if Q3 a " \
                    "is not meant for completeness bans, this reverts to keep"
        elif c == "cloud_frequency_pct":
            v, rsn = "lagged", "same-month MODIS cloud is co-measured -> lag 1 [ruling Q3 a]; the shipped fire run " \
                               "fed it at lag 0"
            locs = "HEADLINE_QUESTIONS_AND_FIXES.md:108-111; APP_PLAN.md:286"
        elif c in ("oni", "tni"):
            v, rsn = "lagged", "centred index: KEPT, lagged by the computed rule [ruling Q2]; shipped at lag 0"
            locs = "HEADLINE_QUESTIONS_AND_FIXES.md:63"
        elif c in annual_pm or expected_kind_class(f["kind"]) == "annual":
            v, rsn = "lagged", "annual column at year -1 [ruling Q3 a]; the shipped fire run fed it at lag 0"
            locs = "pm25_ban.py ANNUAL_LAG1; HEADLINE_QUESTIONS_AND_FIXES.md:108-111"
        else:
            v, rsn = "keep", "in the shipped fire feature list (panel columns after fire_ban.apply_ban)"
            locs = dropc
        if not names and c not in ("lat", "lon"):
            shipped.append(c)          # reached the shipped fire model (whatever the rulings now say)
        cmv = cm_value("fire", c)
        miss, fl = share_note(C.ft["panel"], c, donors, tests, W["donor_years"], W["test_years"])
        rows.append(mk(c, "monthly_panel_v170", v, rsn, locs, facts=f,
                       lagn=lag_note(f, "monthly", cmv.startswith("yes"), v), cm=cmv,
                       miss=join_notes(miss, "; ".join(fl)),
                       notes=join_notes(extra, probe_note(C.probe, f), f["notes"])))
    # history sidecar (fire_architecture.py HIST_DIR; on in adaptation.py run_fire)
    hl = loc(os.path.join(ROOT, FA), r"^HIST_DROP = ")
    ghist = {
        "tslf_months": "time since last fire = 'years since the last event' type: ALLOWED target-derived (plan 1.5)",
        "tslf_censored": "censoring flag of tslf: target-derived indicator, allowed",
        "last_burn_month": "calendar month of the last burn: target-derived; check it is not a disguised key",
        "last_burn_size": "the unit's own y at its last burn: reads like a LAG of own y -> G-HIST may refuse it",
        "n_burns_12mo": "event count over 12 months: allowed target-derived (plan 1.5)",
        "n_burns_60mo": "event count over 60 months: allowed target-derived (plan 1.5)",
        "burn_rate_120mo": "share of burned months over 120 months = a trailing mean of 1{y>0}: G-HIST decides "
                           "(event count vs trailing mean of own y)",
    }
    for c in C.side["fire_history"]["_order"]:
        s = C.side["fire_history"][c]
        miss, fl = share_note(C.ft["fire_history"], c, donors, tests, [], [], per_year=False)
        if c in hist_drop:
            v, rsn, lc = "ban", "single-month neighbour ring: one fire straddling a month boundary seen from next " \
                                "door (event bleed, fire_architecture.py:127-140)", hl
            g = "neighbour aggregate of the target at a 1/3/6-month lag"
        else:
            v, rsn, lc = "keep", "shipped fire-history block (USE_HISTORY = 1)", flags_loc
            g = ghist.get(c, "neighbour aggregate over 12 months (nbr*_12mo): allowed target-derived (plan 1.5); "
                             "flat at lags 1/3/6, so not event bleed (fire_architecture.py:135-137)")
        rows.append(mk(c, "fire_history (sidecar D:/fire/history)", v, rsn, lc, cadence="1 month",
                       stamp="period_end", wl="target-derived window, ends at t-1 (Part 492)", wa="backward",
                       units=s["units"], lo=0, hi=None,
                       lagn="target-derived: every window ends at t-1 (fire_architecture.py:175-178, Part 492); at "
                            "lead L the engine moves the row to the issue step; R8 not applied, G-DERIVED/G-HIST check",
                       cm="no (target-derived; handled by G-HIST, not co-measurement)",
                       miss=join_notes(miss, "; ".join(fl)), notes="G-HIST reading: " + g))
        if v == "keep":
            shipped.append(c)
    # driver sidecar (fire_join_drivers.py)
    J = "fire_join_drivers.py"
    dnotes = {
        "lgt_density": ("WGLC lightning density, trusted from 2013 (Kaplan & Lau); NaN 2002-2012 by construction",
                        "1 month", "backward", "strokes km-2 day-1 (WGLC)", "R30: missing 2003-2012 = 10 of 16 donor "
                        "years -> flagged by construction"),
        "lgt_missing": ("1 where lightning is not measured", "1 month", "backward", "1",
                        "OWNER CHECK: wglc_cols sets it to 1 exactly when year < 2013 (WGLC is global), so it is the "
                        "YEAR key in disguise (G-KEYS / trend proxy)"),
        "lgt_is_zero": ("1 where measured lightning is zero", "1 month", "backward", "1", ""),
        "vod_lag2": ("LPDR v3 VOD level lagged 2 months (smoothing window undocumented, fire_join_drivers.py:193-195)",
                     "1 month (VOD smoothing unknown)", "unknown", "1", "10-month hole 2011-10..2012-07"),
        "vod_d1": ("VOD month-on-month difference ending 2 months back", "1 month (VOD smoothing unknown)", "unknown",
                   "1", ""),
        "vod_anom": ("VOD (lag 2) minus its cell x month climatology fitted on years <= 2018 (NORM_END)",
                     "1 month (VOD smoothing unknown)", "unknown", "1",
                     "normaliser fitted on <= 2018 driver rows: equal to fire's train end; the inner window (<= 2015) "
                     "is not respected -- driver-side, not a label leak"),
        "agb_lag1y": ("ESA CCI biomass epoch of year - 1 (no 2002-2005 or 2014 epoch)", "1 year", "backward",
                      "Mg ha-1", "missing epochs -> R30 check"),
        "agb_contrast": ("biomass(year - 1) over its 5 x 5 neighbourhood median", "1 year", "backward", "1", ""),
    }
    dl = loc(os.path.join(ROOT, J), r'"lgt_density": lg')
    for c in C.side["fire_drivers"]["_order"]:
        what, wl, wa, un, ex = dnotes.get(c, ("fire driver sidecar column", "unknown", "unknown", "", ""))
        miss, fl = share_note(C.ft["fire_drivers"], c, donors, tests, [], [], per_year=False)
        lagn = ("already lagged inside the sidecar (%s); R8 needs the source window facts (VOD smoothing is "
                "undocumented -> sign an assumed window)" % wl) if c.startswith("vod") else \
               ("annual epoch of year - 1: content ends Dec 31 of the previous year -> lag satisfied" if c.startswith("agb")
                else "monthly lightning of the named month -> lag 0")
        rows.append(mk(c, "fire_drivers (sidecar D:/fire/drivers/joined)", "keep",
                       "shipped fire driver block (USE_DRIVERS = 1)", join_notes(flags_loc, dl),
                       cadence="1 year" if c.startswith("agb") else "1 month", stamp="period_end", wl=wl, wa=wa,
                       units=un, lo=None, hi=None, lagn=lagn, cm="no (microwave / lightning / radar biomass)",
                       miss=join_notes(miss, "; ".join(fl)), notes=join_notes(what, ex)))
        shipped.append(c)
    ctxl = "fire_evt_arch.py:%d" % grep_line(os.path.join(ROOT, "fire_evt_arch.py"), r'^CTX = ')
    rows.append(mk("ctx:month", "router_context (package feature script)", "keep",
                   "router context in the shipped run (CTX = ['month', 'lat'])", ctxl, cadence="1 month", stamp="n/a",
                   wl="n/a", wa="n/a", units="month number", lo=1, hi=12,
                   lagn="router_context: read only by the router; key-derived allowed only here (G-KEYS)", cm="no"))
    rows.append(mk("ctx:lat", "router_context (package feature script)", "keep",
                   "router context in the shipped run (CTX = ['month', 'lat'])", ctxl, cadence="static", stamp="n/a",
                   wl="n/a", wa="n/a", units="degrees_north", lo=-90, hi=90, lagn="router_context, static", cm="no"))
    # target store
    tl = loc(os.path.join(ROOT, FA), r'"burned_frac", "n_valid"\]\)')
    miss, fl = share_note(C.ft["fire_target"], "burned_frac", donors, tests, W["donor_years"], W["test_years"])
    rows.append(mk("burned_frac", "fire_target (D:/fire/target)", "ban", "TARGET (role target; forced ban)", tl,
                   cadence="1 month", stamp="period_end", wl="1 month", wa="backward", units="1", lo=0, hi=1,
                   lagn="target: its own window (1 month) sets R8's reference and R17's start", cm="n/a (target)",
                   miss=miss, notes="MCD64A1 monthly burned fraction; validity n_valid > 0 lives in the ingest "
                                    "(fire_architecture.py:273-274); unmapped rows become NaN labels"))
    for c, why in [("n_burned", "numerator of the target"), ("n_valid", "validity count used by the ingest rule"),
                   ("n_unmapped", "unmapped pixel count"), ("unmapped_frac", "share of unmapped pixels")]:
        rows.append(mk(c, "fire_target (D:/fire/target)", "ban", "not a feature: %s (target-derived / support)" % why,
                       tl, cadence="1 month", stamp="period_end", wl="1 month", wa="backward",
                       units="count" if c.startswith("n_") else "1", lo=0, hi=None, lagn="not a feature",
                       cm="n/a (target store)", notes="validity lives in the ingest script (plan 1.2)"))
    return rows, shipped


def defo_rows(C):
    P = "defo_ban.py"
    L = lists(P)
    idx = {}
    for n in ["BAN_MOD44B", "BAN_LANDCOVER", "BAN_LUH2", "BAN_ASSIMILATED", "BAN_REGIME", "BAN_TREND",
              "BAN_STRUCTURAL", "FREEZE_INFRA", "FREEZE_BUILT", "FREEZE_LIVESTOCK", "LAG_FIRE", "LAG_VEG",
              "LAG_OTHER", "LOW_VALUE"]:
        for v, ln in need(L, n, P):
            idx.setdefault(v, []).append((n, "%s:%d" % (P, ln)))
    mfile = sorted(p for g, _, p in list_store(DEFO_MATRIX_DIR, r"^([a-z].*)\.parquet$"))[0]
    mcols = pq.ParquetFile(mfile).schema_arrow.names
    mask = {v for v, _ in need(lists("defo_train.py"), "MASK", "defo_train.py")}
    feats = [c for c in mcols if c not in mask]
    fam = collections.defaultdict(list)
    for c in feats:
        if c.startswith("h_"):
            fam[c].append(c)
            continue
        base = c[5:] if c.startswith("lag1_") else c
        for suf in ("_mean", "_min", "_max"):
            if base.endswith(suf) and base[:-len(suf)] in C.facts:
                base = base[:-len(suf)]
                break
        fam[base].append(c)
    unknown = [b for b in fam if b not in C.facts and not b.startswith("h_")]
    if unknown:
        raise SystemExit("export_review_csv: defo matrix columns with no panel parent: %s" % unknown)
    freeze = {v for v, _ in need(L, "FREEZE", P)}
    snow = {"snow_onset_doy", "snow_disappearance_doy", "snow_duration_days", "snow_max_doy"}
    amospei = {"amo", "spei_01m", "spei_03m", "spei_06m", "V06_spei_12m", "spei_24m"}
    donors, tests, _ = C.groups["defo"]
    W = WINDOWS["defo"]
    mloc = "defo_matrix.py:%d" % grep_line(os.path.join(ROOT, "defo_matrix.py"), r"def annualise")
    armloc = loc(os.path.join(ROOT, "defo_corrector.py"), r'ARM\s*=\s*T\._a\("--arm", "hist"\)')
    rows = []
    for c in C.panel_cols:
        if c in KEY_COLS:
            continue
        f = C.facts[c]
        hits = idx.get(c, [])
        names = [h[0] for h in hits]
        locs = "; ".join(h[1] for h in hits)
        exp = ", ".join(fam.get(c, []))
        extra = ""
        if any(n.startswith("BAN_") for n in names):
            n0 = [n for n in names if n.startswith("BAN_")][0]
            v, rsn = "ban", {"BAN_MOD44B": "the target read from MODIS / its sum group (defo_ban BAN_MOD44B)",
                             "BAN_LANDCOVER": "MODIS supervised land cover or a slice of it (defo_ban BAN_LANDCOVER)",
                             "BAN_LUH2": "LUH2: constrained by Hansen loss (defo_ban BAN_LUH2)",
                             "BAN_ASSIMILATED": "assimilates land use from LUH2 (defo_ban BAN_ASSIMILATED)",
                             "BAN_REGIME": "regime classifier trained on in-window NDVI (defo_ban BAN_REGIME)",
                             "BAN_TREND": "global scalar trend proxy (defo_ban BAN_TREND)",
                             "BAN_STRUCTURAL": "structural (defo_ban BAN_STRUCTURAL)"}[n0]
        elif any(n.startswith("FREEZE") for n in names):
            v, rsn = "ban", "defo_ban FREEZE (post-window snapshot / projection); dropped from the shipped matrix " \
                            "(defo_matrix.py:27-31) [ruling Q3 a: banned as in PM2.5; 'freeze' needs a date-filtered " \
                            "re-ingest]"
        elif c in snow:
            v, rsn = "ban", "annual snow timing [ruling Q3 a: PM2.5's snow-DOY ban applies to defo]; shipped at lag 0"
            locs = join_notes(mloc, "HEADLINE_QUESTIONS_AND_FIXES.md:108-111")
            extra = "OWNER CHECK: calendar-year window (ingest_era5land_snowphen.py:4-8) does not pass Dec 31, so on " \
                    "an ANNUAL target R8 would give lag 0 (9.1 item 3); the look-ahead reason is a monthly-target reason"
        elif c in amospei:
            v, rsn = "ban", "PM2.5's AMO/SPEI ban [ruling Q3 a]: empty in 2023, a test year for defo; shipped as " \
                            "annual aggregates"
            locs = join_notes(mloc, "HEADLINE_QUESTIONS_AND_FIXES.md:108-111")
        elif any(n.startswith("LAG_") for n in names):
            v, rsn = "lagged", "defo_ban LAG: measures the clearing concurrently -> previous year's summary (lag1_*)"
            if "LOW_VALUE" in names:
                rsn += "; also LOW_VALUE (kept in the shipped arm: drop_low_value=False)"
        elif c in ("oni", "tni"):
            v, rsn = "lagged", "centred index: KEPT, lagged [ruling Q2]; the annual aggregate of a centred index " \
                               "reaches January t+1 -> lag 1 year unless shifted first (plan 3.2)"
            locs = join_notes(mloc, "HEADLINE_QUESTIONS_AND_FIXES.md:63")
        elif c in ("conflict_events", "conflict_deaths", "eddi_observed"):
            v, rsn = "keep", "shipped (zero-filled annual aggregates); FLAGGED by the missing-value rule: needs an " \
                             "explicit keep-with-evidence or ban [plan 3.3 flag 7, R30]"
            locs = join_notes(mloc, "defo_matrix.py:%d" % grep_line(os.path.join(ROOT, "defo_matrix.py"),
                                                                   r"conflict_\* has no ACLED"), "APP_PLAN.md:305")
            extra = "FOOTER FINDING: in D:/defo_matrix this column is never NaN; it is CONSTANT (%s) in most groups " \
                    "(see missing_share_note). The '35/31 of 42 all-NaN' at defo_matrix.py:113 does not describe the " \
                    "stored matrix, and R30 as written counts MISSING values, so it would not fire; the review still " \
                    "rules (plan 3.3 flag 7)" % ("zero: no UCDP event within 50 km" if c.startswith("conflict")
                                                  else "1.0: EDDI always observed")
        elif c in fam:
            v, rsn = "keep", "in the shipped defo matrix (arm 'hist', all non-MASK columns)"
            locs = join_notes(mloc, armloc)
        else:
            raise SystemExit("export_review_csv: defo column %s is neither banned nor in the matrix" % c)
        if v in ("keep", "lagged") and c not in fam and c not in snow | amospei:
            raise SystemExit("export_review_csv: defo %s marked %s but not in D:/defo_matrix" % (c, v))
        if c in ("lat", "lon"):
            extra = join_notes(extra, "OWNER CHECK: defo feeds coordinates to the trees; PM2.5, fire and NDVI never "
                                      "do (G-KEYS treats them as static-table columns)")
        cmv = cm_value("defo", c)
        miss, fl = share_note(C.ft["panel"], c, donors, tests, W["donor_years"], W["test_years"],
                              label="panel (source of the annual aggregate)")
        mnote = ""
        if fam.get(c):
            mm, _ = share_note(C.ft["defo_matrix"], fam[c][0], donors, tests, [], [], per_year=False,
                               label="matrix %s" % fam[c][0])
            mnote = mm
        rows.append(mk(c, "monthly_panel_v170", v, rsn, locs, facts=f,
                       lagn=lag_note(f, "annual", cmv.startswith("yes"), v), cm=cmv,
                       miss=join_notes(miss, mnote, "; ".join(fl)),
                       notes=join_notes(extra, ("defo matrix columns: " + exp) if exp else "",
                                        probe_note(C.probe, f), f["notes"])))
    # history block h_*
    hloc = loc(os.path.join(ROOT, "defo_matrix.py"), r'"h_lag1": shift\(A, 1\)')
    hinfo = {
        "h_lag1": ("ban", "own loss_frac at t-1: replaced by the engine history block [ruling Q12]"),
        "h_lag2": ("ban", "own loss_frac at t-2: replaced by the engine history block [ruling Q12]"),
        "h_lag3": ("ban", "own loss_frac at t-3: replaced by the engine history block [ruling Q12]"),
        "h_cum": ("ban", "cumulative own loss up to t-1: replaced by the engine's all-history mean [ruling Q12]"),
        "h_nbr1": ("keep", "mean loss of the 8 neighbours at t-1: defo dataset feature [ruling Q12]"),
        "h_nbr2": ("keep", "mean loss of the 8 neighbours at t-2: defo dataset feature [ruling Q12]"),
        "h_nbr_cum": ("keep", "cumulative neighbourhood loss up to t-1: defo dataset feature [ruling Q12]"),
        "h_yrs_since": ("keep", "years since the cell's last non-zero loss, capped 99: defo dataset feature [ruling Q12]"),
    }
    for c in [x for x in feats if x.startswith("h_")]:
        v, rsn = hinfo[c]
        mm, fl = share_note(C.ft["defo_matrix"], c, donors, tests, [], [], per_year=False, label="matrix")
        rows.append(mk(c, "engineered (defo_matrix.py; package feature script)", v, rsn,
                       join_notes(hloc, "HEADLINE_QUESTIONS_AND_FIXES.md:39"), cadence="1 year", stamp="period_end",
                       wl="target-derived, years <= t-1", wa="backward", units="years" if c == "h_yrs_since" else "1",
                       lo=0, hi=None,
                       lagn="target-derived: uses years <= t-1 only (defo_matrix.py:54-58); G-HIST refuses own-lag "
                            "columns, allows neighbour aggregates and years-since (plan 1.5)",
                       cm="no (target-derived; G-HIST)", miss="; ".join([mm] + fl),
                       notes="plan 3.2: the engine block adds the all-history mean so h_cum's long memory is kept"
                       if c == "h_cum" else ""))
    # target store
    tl = loc(os.path.join(ROOT, "defo_matrix.py"), r'"loss_frac": "y"')
    miss, fl = share_note(C.ft["defo_target"], "loss_frac", donors, tests, [], [], per_year=False)
    rows.append(mk("loss_frac", "defo_target (D:/defo_target)", "ban", "TARGET (role target; forced ban)", tl,
                   cadence="1 year", stamp="period_end", wl="1 year", wa="backward", units="1", lo=0, hi=1,
                   lagn="target: its own window (the loss year) sets R8's reference", cm="n/a (target)", miss=miss,
                   notes="Hansen GFC annual loss / forest2000 pixels"))
    for c, why, role in [("loss_px", "numerator of the target", "target-derived"),
                         ("forest2000_px", "denominator; report stratum (forest-pixel quartiles, Q50)", "support"),
                         ("land_px", "land pixel count", "support")]:
        rows.append(mk(c, "defo_target (D:/defo_target)", "ban", "not a feature: %s (%s; defo_matrix.py:37-41)" % (why, role),
                       loc(os.path.join(ROOT, "defo_train.py"), r"^MASK = "), cadence="1 year" if c == "loss_px" else "static",
                       stamp="period_end" if c == "loss_px" else "n/a", wl="1 year" if c == "loss_px" else "n/a",
                       wa="backward" if c == "loss_px" else "n/a", units="count", lo=0, hi=None,
                       lagn="not a feature", cm="n/a (target store)",
                       notes="treecover2000 is a co-product of the target's model run (defo_matrix.py:37-41)"))
    return rows, feats


def ndvi_rows(C):
    E = "presplit_cc/experiment_thar_regime_full.py"
    R = "presplit_cc/run89_outputs.py"
    EL = lists(E)
    remove = {v: "%s:%d" % (E, ln) for v, ln in need(EL, "REMOVE", E)}
    geo = {v: "%s:%d" % (E, ln) for v, ln in need(EL, "GEO", E)}
    RL = lists(R)
    ddrop = {v: "%s:%d" % (R, ln) for v, ln in need(RL, "DEFAULT_DROP", R)}
    ban11 = {v for v, _ in need(RL, "BAN", R)}
    if set(remove) != ban11 or len(ban11) != 11:
        raise SystemExit("export_review_csv: REMOVE (%d) and run89_outputs.BAN (%d) differ -- the 9-vs-11 hazard"
                         % (len(remove), len(ban11)))
    lag_orders = re.search(r"LAG_ORDERS = \(([\d, ]+)\)", open(os.path.join(PC, "experiment1_cellrouting_bundle.py"),
                                                                 encoding="utf-8").read()).group(1)
    lag_orders = [int(x) for x in lag_orders.split(",")]
    pm = lists("pm25_ban.py")
    annual_pm = {v for v, _ in need(pm, "ANNUAL_LAG1", "pm25_ban.py")}
    freeze = {v for v, _ in need(lists("defo_ban.py"), "FREEZE", "defo_ban.py")}
    snow = {"snow_onset_doy", "snow_disappearance_doy", "snow_duration_days", "snow_max_doy"}
    amospei = {"amo", "spei_01m", "spei_03m", "spei_06m", "V06_spei_12m", "spei_24m"}
    base = [c for c in C.panel_cols if c not in KEY_COLS and c != "V11_mean_ndvi" and c not in geo and c not in remove
            and not any(t.lower() in c.lower() for t in ddrop)]
    lagv = C.probe.get("run89_lag_parents_thar") or []
    donors, tests, _ = C.groups["ndvi"]
    W = WINDOWS["ndvi"]
    b89 = "presplit_cc/bundle_lag_compare.py:%d" % grep_line(os.path.join(PC, "bundle_lag_compare.py"), r"feats94 = ")
    rows = []
    for c in C.panel_cols:
        if c in KEY_COLS:
            continue
        f = C.facts[c]
        extra = ""
        if c == "V11_mean_ndvi":
            v, rsn, locs = "ban", "TARGET (V11 is y; never a feature -- F16, ruling Q1)", "presplit_cc/monthly_loader.py:28"
        elif c in geo:
            v, rsn, locs = "ban", "coordinate (GEO): never a tree feature", geo[c]
        elif c in remove:
            v, rsn, locs = "ban", "vegetation-state proxy leak: the canonical REMOVE-11 (reference_remove_list_9_vs_11)", \
                remove[c]
            if c == "V12_mean_evi":
                rsn += "; target twin [ruling: NDVI bans V11/V12 as features]"
        elif any(t.lower() in c.lower() for t in ddrop):
            t = [t for t in ddrop if t.lower() in c.lower()][0]
            v, rsn, locs = "ban", "cross_region_fast --drop default (substring match at keep_cols)", ddrop[t]
        elif c in ("clf_dry", "clf_wet"):
            v, rsn, locs = "ban", "classifier TRAINED ON NDVI: a label leak [ruling Q35 a]", \
                "HEADLINE_QUESTIONS_AND_FIXES.md:87, 268-271"
            extra = "shipped run89 fed it"
        elif c in ("oni", "tni"):
            v, rsn, locs = "lagged", "centred index: KEPT, lagged by the computed rule [ruling Q2]; run89 fed it at " \
                                     "lag 0", "HEADLINE_QUESTIONS_AND_FIXES.md:63"
        elif c in freeze:
            v, rsn, locs = "ban", "post-window snapshot / projected layer (defo FREEZE list) [ruling Q3 a]; run89 fed it", \
                "defo_ban.py FREEZE; HEADLINE_QUESTIONS_AND_FIXES.md:108-111"
        elif c in snow:
            v, rsn, locs = "ban", "annual snow timing = end-of-year fact [ruling Q3 a]; run89 fed it", \
                "pm25_ban.py BAN_LOOKAHEAD; HEADLINE_QUESTIONS_AND_FIXES.md:108-111"
        elif c in amospei:
            v, rsn, locs = "ban", "PM2.5's AMO/SPEI ban [ruling Q3 a]: empty in 2023, an NDVI test year; run89 fed it", \
                "pm25_ban.py DROP_INCOMPLETE; HEADLINE_QUESTIONS_AND_FIXES.md:108-111"
        elif c in annual_pm or expected_kind_class(f["kind"]) == "annual":
            v, rsn = "lagged", "annual column at year -1 [ruling Q3 a]; run89 fed it at lag 0"
            locs = ("pm25_ban.py ANNUAL_LAG1" if c in annual_pm else "annual by the seeded cadence and the sample") + \
                "; HEADLINE_QUESTIONS_AND_FIXES.md:108-111"
            if c in ("cropland_fraction",):
                extra = join_notes(extra, "OWNER CHECK (Q34): an MCD12Q1 slice; Q34 option a (recommended, not yet "
                                          "ruled) would ban MCD12Q1 slices on NDVI")
        elif c in base:
            v, rsn, locs = "keep", "in run89's base features (panel minus ID keys, target, GEO, REMOVE-11, --drop)", b89
        else:
            raise SystemExit("export_review_csv: NDVI column %s unclassified" % c)
        if c in base and v != "ban":
            if c in lagv:
                extra = join_notes(extra, "run89 also fed lags %s of this column (thar lag parents)" % lag_orders)
        if c == "V20_burned_binary":
            extra = join_notes(extra, "OWNER CHECK: same-month burned area on an NDVI target -- the logic of Q38 b "
                                      "(GFED burn co-measured, lag 1) applies here too; run89 fed it at lag 0")
        cmv = cm_value("ndvi", c)
        if c in ("co2", "food_price_index", "food_meat", "food_dairy", "food_cereals", "food_oils", "food_sugar",
                 "scpdsi", "eddi", "eddi_observed"):
            extra = join_notes(extra, "OWNER CHECK (Q34): kept by REMOVE-11; PM2.5, fire and defo ban it")
        miss, fl = share_note(C.ft["panel"], c, donors, tests, W["donor_years"], W["test_years"])
        rows.append(mk(c, "monthly_panel_v170", v, rsn, locs, facts=f,
                       lagn=("target: its own window sets R8's reference and R17's start (M0 V11 audit)"
                             if c == "V11_mean_ndvi" else lag_note(f, "monthly", cmv.startswith("yes"), v)),
                       cm=cmv, miss=join_notes(miss, "; ".join(fl)),
                       notes=join_notes(extra, probe_note(C.probe, f), f["notes"])))
    # GFED burn: new for NDVI, lag 1 only (Q38 b)
    gf = C.side["gfed_burn"]["burn_frac"]
    miss, fl = share_note(C.ft["gfed"], "burn_frac", donors, tests, W["donor_years"], W["test_years"])
    rows.append(mk("burn_frac", "gfed_burn", "lagged", "GFED burn at lag 1 ONLY: co-measured with NDVI [ruling Q38 b]",
                   "HEADLINE_QUESTIONS_AND_FIXES.md:89, 283-286; APP_PLAN.md:44", cadence="1 month",
                   stamp="period_end", wl="1 month", wa="backward", units=gf["units"], lo=0, hi=1,
                   lagn="co_measured_with_target: true (signed fact) -> R8 gives lag 1", cm=cm_value("ndvi", "burn_frac"),
                   miss=join_notes(miss, "; ".join(fl)),
                   notes="not in run89; the 6 panel groups without a GFED file are a store fact (absent_groups)"))
    rows.append(mk("burn_npix", "gfed_burn", "ban", "not a feature: pixel count support column", "D:/gfed_burn footer",
                   cadence="1 month", stamp="period_end", wl="1 month", wa="backward", units="count", lo=0, hi=None,
                   lagn="not a feature", cm="no"))
    # water-memory engineered features (bundle_lag_compare.py)
    B = os.path.join(PC, "bundle_lag_compare.py")
    wv = [v for v, _ in need(EL, "WATERVARS", E)]
    wm = re.search(r"^WINDOWS = \[([\d, ]+)\]", open(os.path.join(ROOT, E), encoding="utf-8").read(), re.M)
    if not wm:
        raise SystemExit("export_review_csv: WINDOWS not found in %s" % E)
    wins = [int(x) for x in wm.group(1).split(",")]
    eng = []
    for v in wv:
        for w in wins:
            eng.append(("%s_roll%d" % (v, w), v, "trailing %d-month MEAN of %s (min_periods=1)" % (w, v),
                        "%d month" % w, grep_line(B, r"_roll\{w\}")))
    eng.append(("precip_wytd", "V02_total_precip_mm", "water-year-to-date precip sum; water year starts in June "
                "(wy = year - (month < 6))", "since June, up to 12 month", grep_line(B, r"precip_wytd")))
    eng.append(("api_precip", "V02_total_precip_mm", "antecedent precip index: EWM alpha 0.1 over all past months",
                "unbounded (EWM)", grep_line(B, r"api_precip")))
    eng.append(("api_soilmoist", "V30_soil_moisture_pct", "EWM alpha 0.1 of V30 soil moisture", "unbounded (EWM)",
                grep_line(B, r"api_soilmoist")))
    for v in ["soil_water_tc_mm", "V30_soil_moisture_pct", "V07_total_ref_ET_mm", "aet_total_mm",
              "climate_water_deficit_mm"]:
        eng.append(("%s_wytd" % v, v, "water-year-to-date cumulative sum of %s (from June)" % v,
                    "since June, up to 12 month", grep_line(B, r"\{v\}_wytd")))
    eng.append(("consec_dry_months", "V02_total_precip_mm", "run length of months with precip < 10 mm",
                "unbounded run length", grep_line(B, r"consec_dry_months")))
    eng.append(("months_since_sig_rain", "V02_total_precip_mm", "months since a month with precip >= 30 mm",
                "unbounded run length", grep_line(B, r"months_since_sig_rain")))
    for name, parent, what, wl, ln in eng:
        pf = C.facts[parent]
        rows.append(mk(name, "engineered (NDVI package feature script; run89 builder)", "keep",
                       "run89 water-memory feature; NDVI keeps its engineered features, rebuilt date-safe [ruling Q33]",
                       "presplit_cc/bundle_lag_compare.py:%s; HEADLINE_QUESTIONS_AND_FIXES.md:47" % ln,
                       cadence="1 month", stamp="period_end", wl=wl, wa="backward", units=pf.get("units", ""),
                       lo=None, hi=None,
                       lagn="driver-derived, trailing: ends at its own row (parent %s: %s); at lead L the engine moves "
                            "the whole row back to the issue step (plan 1.5)" % (parent, timing_words(pf)[2]),
                       cm="no", miss="as the parent column %s" % parent,
                       notes=join_notes(what, "derived_from %s; recomputed by G-DERIVED" % parent)))
    # router context (cross_region_fast.py:767-771 / cross_region_run89.py:887-890)
    cl = "presplit_cc/cross_region_run89.py:%d" % grep_line(os.path.join(PC, "cross_region_run89.py"), r"top5 = np\.argsort")
    rows.append(mk("ctx:climatology", "router_context (package feature script)", "ban",
                   "a copy of the normal: replaced by the engine's unpenalised normal column (replaced_by_engine) "
                   "[plan 3.3 flag 8]", cl, cadence="1 month", stamp="n/a", wl="n/a", wa="n/a", units="1",
                   lagn="n/a (replaced)", cm="no", notes="same information, fit rows only"))
    for nm in ("ctx:sin1", "ctx:cos1", "ctx:sin2", "ctx:cos2"):
        rows.append(mk(nm, "router_context (package feature script)", "keep",
                       "seasonal harmonic of the month (router context in run89)", cl, cadence="1 month", stamp="n/a",
                       wl="n/a", wa="n/a", units="1", lo=-1, hi=1,
                       lagn="router_context from the month key: allowed only as router context (G-KEYS)", cm="no"))
    rows.append(mk("ctx:top5_drivers", "router_context (package feature script)", "keep",
                   "5 driver columns picked per target by donor importance (data_selected)", cl, cadence="1 month",
                   stamp="n/a", wl="as the picked columns", wa="as the picked columns", units="as the picked columns",
                   lagn="each picked column inherits its own lag", cm="no",
                   notes="DISCLOSE test exposure: picked from a bank with 19 test regions as donors (F15; plan 3.3 "
                         "flag 8); the top-5 list is frozen and declared as data_selected"))
    return rows, base, lagv, lag_orders


# ================================================================================================
# 9. SIDE STORES
# ================================================================================================
def side_store_facts():
    side = {}
    g = list_store(GFED_DIR, r"^(.+)_burn_(\d{4})\.parquet$")
    s = pq.ParquetFile(g[0][2]).schema_arrow
    side["gfed_burn"] = {"_order": [x.name for x in s], "_dtypes": {x.name: str(x.type) for x in s},
                         "burn_frac": dict(units="1"), "burn_npix": dict(units="count")}
    e = list_store(EDGAR_DIR, r"^(.+)_edgar\.parquet$")
    s = pq.ParquetFile(e[0][2]).schema_arrow
    side["edgar_emis"] = {"_order": [x.name for x in s if x.name.startswith("edgar_")],
                          "_dtypes": {x.name: str(x.type) for x in s}}
    for x in side["edgar_emis"]["_order"]:
        side["edgar_emis"][x] = dict(units="unknown (EDGAR emission field as ingested; check the ingest)")
    h = list_store(FIRE_HIST_DIR, r"^(.+)\.parquet$")
    s = pq.ParquetFile(h[0][2]).schema_arrow
    side["fire_history"] = {"_order": [x.name for x in s if x.name not in ("lat", "lon", "year", "month")],
                            "_dtypes": {x.name: str(x.type) for x in s}}
    hu = {"tslf_months": "month", "tslf_censored": "1", "last_burn_month": "month number", "last_burn_size": "1",
          "n_burns_12mo": "count", "n_burns_60mo": "count", "burn_rate_120mo": "1"}
    for x in side["fire_history"]["_order"]:
        side["fire_history"][x] = dict(units=hu.get(x, "1"))
    d = list_store(FIRE_DRV_DIR, r"^(.+)\.parquet$")
    s = pq.ParquetFile(d[0][2]).schema_arrow
    side["fire_drivers"] = {"_order": [x.name for x in s if x.name not in ("lat", "lon", "year", "month")],
                            "_dtypes": {x.name: str(x.type) for x in s}}
    for x in side["fire_drivers"]["_order"]:
        side["fire_drivers"][x] = dict(units="")
    return side


# ================================================================================================
# 10. WRITERS (new files only)
# ================================================================================================
def protected_roots():
    if not os.path.exists(PROTECTED):
        return []
    return [ln.strip().replace("\\", "/").rstrip("/").lower() for ln in open(PROTECTED, encoding="utf-8") if ln.strip()]


def check_path(p):
    q = os.path.abspath(p).replace("\\", "/").lower()
    for r in protected_roots():
        if q == r or q.startswith(r + "/"):
            raise SystemExit("export_review_csv: REFUSED -- %s is under a protected root (%s)" % (p, r))


def safe_write_new(path, writer):
    """Write via a temp file and an atomic rename; refuse if the target exists (never overwrite)."""
    check_path(path)
    if os.path.exists(path):
        raise SystemExit("export_review_csv: REFUSED -- %s already exists; this tool never overwrites. Move your "
                         "copy aside yourself or pass --out-dir to a new folder." % path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    if os.path.exists(tmp):
        raise SystemExit("export_review_csv: REFUSED -- stale temp file %s exists" % tmp)
    writer(tmp)
    os.replace(tmp, path)


def write_csv(path, rows):
    def w(t):
        with open(t, "w", encoding="utf-8", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=CSV_COLUMNS, quoting=csv.QUOTE_MINIMAL)
            wr.writeheader()
            for r in rows:
                wr.writerow(r)
    safe_write_new(path, w)


def write_yaml(path, header, obj):
    def w(t):
        with open(t, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(header)
            yaml.safe_dump(obj, fh, sort_keys=False, allow_unicode=False, width=110, default_flow_style=False)
    safe_write_new(path, w)


def clean(v):
    """YAML-safe scalars (no numpy types, no NaN)."""
    if isinstance(v, dict):
        return {k: clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        f = float(v)
        if math.isnan(f):
            return None
        if math.isinf(f):
            return ".inf" if f > 0 else "-.inf"
        return f
    return v


def panel_yaml(C, stamp_time):
    ft = C.ft["panel"]
    cols = []
    for c in C.panel_cols:
        f = C.facts[c]
        cad, st, wl, wa, wd = timing_words(f)
        entry = dict(name=c, dtype=f["dtype"], units=f["units"] or None, units_source=f["units_source"],
                     cadence=cad, stamp=st, window=dict(wd, text=wl), scope=f["scope"])
        if f["kind"] == "key":
            entry["key_column"] = True
        else:
            lo, hi = f.get("legal", (None, None))
            entry["legal_range"] = [lo, hi if hi is not None else (".inf" if lo is not None else None)]
            entry["legal_range_source"] = f["legal_source"]
            entry["fill_values"] = "panel default (see top)" if f["dtype"].startswith(("float", "double", "int")) else None
            if c in ("wbal_mm", "wbal_roll3", "wbal_roll6", "wbal_roll12", "wbal_roll24"):
                entry["near_sentinel_note"] = "-2147450880 = -2^31 - (-32768) escapes both codes if a parent is unmasked"
        entry["product"] = f["product"]
        entry["product_family"] = f["family"]
        if f["sensor"]:
            entry["sensor_lineage"] = f["sensor"]
        if f["baseline"]:
            entry["baseline_period"] = f["baseline"]
        if f["derived_from"]:
            entry["derived_from"] = f["derived_from"]
        if f["sum_group"]:
            entry["sum_group"] = f["sum_group"]
        if c not in KEY_COLS:
            ob = C.probe["columns"].get(c, {}).get("observed")
            if ob:
                entry["observed_sample"] = ob
            d = ft[ft.column == c] if ft is not None and not ft.empty else None
            if d is not None and not d.empty and (d.nulls >= 0).all():
                agg = d.groupby("group").agg(rows=("rows", "sum"), nulls=("nulls", "sum"))
                entry["footer_stats"] = dict(
                    null_share_all_files=round(float(d.nulls.sum()) / max(1, float(d.rows.sum())), 5),
                    groups_all_null=int((agg.nulls == agg.rows).sum()), groups=int(len(agg)),
                    group_years_with_fill_code_as_min_or_max=int((d.vmin.isin(FILLS) | d.vmax.isin(FILLS)).sum()),
                    min=clean(d.vmin.min()), max=clean(d.vmax.max()))
        entry["fact_status"] = "unverified"
        entry["provenance"] = f["provenance"]
        if f["notes"]:
            entry["notes"] = f["notes"]
        cols.append(clean(entry))
    obj = dict(
        store="monthly_panel_v170",
        path_template="D:/monthly_panel/{group}_monthly_{year}.parquet",
        layout="one parquet per group-year; one row group; cells x 12 months; read in place, never copied",
        keys=dict(unit="cell_id", group="region", time=["year", "month"]),
        n_columns=len(C.panel_cols), n_files=int(len(C.panel_files)), groups=int(len({g for g, _, _ in C.panel_files})),
        years=[int(min(y for _, y, _ in C.panel_files)), int(max(y for _, y, _ in C.panel_files))],
        fill_values=[-32768, -32767, -2147483648, -2147483647],
        fill_values_provenance="panel_sentinel.py:%d (SENTINELS), confirmed for this panel only (APP_PLAN.md 1.3)"
                               % grep_line(os.path.join(ROOT, "panel_sentinel.py"), r"^SENTINELS = "),
        huge_value_rule="abs >= 1e30 is a float fill (panel_sentinel.py HUGE); abs >= 2^30 is flagged unless opted out",
        conventions=dict(
            stamp="which instant of the period named by the row key (a calendar month, or a calendar year for "
                  "annual values) anchors the window: period_start / period_centre / period_end",
            window="length + unit + align relative to that anchor: backward = the window ends at the anchor; "
                   "centred = centred on it; forward = starts at it and runs past the named period",
            fact_status="every fact here is a SEED ('unverified'); a headline run needs verified or signed "
                        "'assumed' timing facts for every kept column (G-FACTS)",
            roles="no roles here: roles are package facts (APP_PLAN.md 1.3)"),
        generated_by="engine/datasets/_tools/export_review_csv.py", generated_at=stamp_time,
        cadence_sample=C.probe["sample"],
        columns=cols)
    header = ("# monthly_panel_v170 -- shared STORE catalog (physical facts only), SEEDED "
              "%s by engine/datasets/_tools/export_review_csv.py\n"
              "# Every fact is 'unverified'. The owner verifies or signs them through the review CSVs "
              "(engine/datasets/review/).\n"
              "# Do not trust assemble_monthly_panel.py's CARRY list for cadence: it mixes static and annual columns "
              "(APP_PLAN.md 1.2).\n" % stamp_time)
    return header, obj


def side_yaml(name, C, stamp_time):
    s = C.side[name]
    meta = {
        "gfed_burn": dict(path_template="D:/gfed_burn/{group}_burn_{year}.parquet", keys=dict(unit="cell_id", time=["year", "month"]),
                          product="GFED monthly burned fraction on the panel cells (ingested for PM2.5)",
                          provenance="pm25_architecture.py:%d" % grep_line(os.path.join(ROOT, "pm25_architecture.py"), r"^BURN = "),
                          cadence="1 month", stamp="period_end", window=dict(length=1, unit="month", align="backward")),
        "edgar_emis": dict(path_template="D:/edgar_emis/{group}_edgar.parquet", keys=dict(unit="cell_id", time=["year"]),
                           product="EDGAR annual emission grids on the panel cells",
                           provenance="pm25_architecture.py:%d" % grep_line(os.path.join(ROOT, "pm25_architecture.py"), r"^EDGAR = "),
                           cadence="1 year", stamp="period_end", window=dict(length=1, unit="year", align="backward")),
        "fire_history": dict(path_template="D:/fire/history/{group}.parquet", keys=dict(unit="lat+lon (fire key)", time=["year", "month"]),
                             product="fire-history features derived from the fire TARGET (every window ends at t-1, Part 492)",
                             provenance="fire_architecture.py:%d" % grep_line(os.path.join(ROOT, "fire_architecture.py"), r'^HIST_DIR = '),
                             cadence="1 month", stamp="period_end",
                             window=dict(length=None, unit="month", align="backward", text="target-derived, ends at t-1"),
                             reads_target=True),
        "fire_drivers": dict(path_template="D:/fire/drivers/joined/{group}.parquet", keys=dict(unit="lat+lon (fire key)", time=["year", "month"]),
                             product="WGLC lightning, LPDR v3 VOD, ESA CCI biomass on the fire cells (fire_join_drivers.py)",
                             provenance="fire_join_drivers.py:%d" % grep_line(os.path.join(ROOT, "fire_join_drivers.py"), r'^OUT = '),
                             cadence="mixed (monthly; agb_* annual epochs)", stamp="period_end",
                             window=dict(length=None, unit=None, align="unknown", text="per column; VOD smoothing undocumented")),
    }[name]
    ft = C.ft.get({"gfed_burn": "gfed", "edgar_emis": "edgar", "fire_history": "fire_history",
                   "fire_drivers": "fire_drivers"}[name])
    cols = []
    for c in s["_order"]:
        e = dict(name=c, dtype=s["_dtypes"].get(c), units=s.get(c, {}).get("units") or None, fact_status="unverified")
        if ft is not None and not ft.empty:
            d = ft[ft.column == c]
            if not d.empty and (d.nulls >= 0).all():
                e["footer_stats"] = dict(null_share_all_files=round(float(d.nulls.sum()) / max(1, float(d.rows.sum())), 5),
                                         min=clean(d.vmin.min()), max=clean(d.vmax.max()))
        cols.append(clean(e))
    obj = dict(store=name, **meta, fill_values=[], fact_status_default="unverified",
               generated_by="engine/datasets/_tools/export_review_csv.py", generated_at=stamp_time)
    if name == "gfed_burn":
        panel_groups = sorted({g for g, _, _ in C.panel_files})
        gfed_groups = sorted({g for g, _, _ in list_store(GFED_DIR, r"^(.+)_burn_(\d{4})\.parquet$")})
        obj["absent_groups"] = {gname: "no GFED file for this panel group (directory listing %s)" % stamp_time[:10]
                                for gname in panel_groups if gname not in gfed_groups}
    obj["columns"] = cols
    header = "# %s -- side-store catalog SEED (physical facts only, all 'unverified'), %s\n" % (name, stamp_time)
    return header, obj


# ================================================================================================
# 11. MAIN
# ================================================================================================
def cross_notes(tables):
    """Append 'other problems: ...' to each panel-column row so per-problem differences are visible."""
    verdict = {p: {r["column"]: r["current_verdict"] for r in rows if r["store"] == "monthly_panel_v170"}
               for p, rows in tables.items()}
    for p, rows in tables.items():
        for r in rows:
            if r["store"] != "monthly_panel_v170":
                continue
            oth = ["%s=%s" % (q, verdict[q].get(r["column"], "-")) for q in ("pm25", "fire", "defo", "ndvi") if q != p]
            r["notes"] = join_notes(r["notes"], "other problems: " + ", ".join(oth))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", default=DEFAULT_OUT, help="folder that receives review/ and _stores/")
    ap.add_argument("--cache-dir", default=DEFAULT_CACHE)
    ap.add_argument("--refresh-cache", action="store_true", help="re-read footers / re-run the probe (new cache files)")
    ap.add_argument("--no-footers", action="store_true", help="skip the footer statistics (missing notes say so)")
    A = ap.parse_args(argv)
    out = os.path.abspath(A.out_dir)
    check_path(out)
    check_path(A.cache_dir)
    targets = [os.path.join(out, "review", "%s_columns.csv" % p) for p in ("pm25", "fire", "defo", "ndvi")] + \
              [os.path.join(out, "_stores", n) for n in ("monthly_panel_v170.yaml", "gfed_burn_catalog.yaml",
                                                          "edgar_emis_catalog.yaml", "fire_history_catalog.yaml",
                                                          "fire_drivers_catalog.yaml")]
    exist = [t for t in targets if os.path.exists(t)]
    if exist:
        raise SystemExit("export_review_csv: REFUSED -- these outputs already exist (an owner may have filled them):\n  "
                         + "\n  ".join(exist) + "\nPass --out-dir <new folder> to write a fresh set.")
    stamp_time = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    C = Ctx()
    C.panel_files = list_store(PANEL_DIR, r"^(.+)_monthly_(\d{4})\.parquet$")
    if not C.panel_files:
        raise SystemExit("export_review_csv: no panel files under %s" % PANEL_DIR)
    sch = pq.ParquetFile(C.panel_files[0][2]).schema_arrow
    C.panel_cols = [x.name for x in sch]
    C.panel_dtypes = {x.name: {"float": "float32", "double": "float64"}.get(str(x.type), str(x.type)) for x in sch}
    if len(C.panel_cols) != 170:
        raise SystemExit("export_review_csv: the panel has %d columns, the catalog is named v170" % len(C.panel_cols))
    C.facts = panel_facts(C.panel_cols, C.panel_dtypes)
    C.side = side_store_facts()
    C.groups = problem_groups()
    os.makedirs(A.cache_dir, exist_ok=True)
    C.ft = {}
    stores = {
        "panel": C.panel_files,
        "gfed": list_store(GFED_DIR, r"^(.+)_burn_(\d{4})\.parquet$"),
        "edgar": list_store(EDGAR_DIR, r"^(.+)_edgar\.parquet$"),
        "pm25_target": list_store(PM25_TARGET_DIR, r"^(.+)_pm25_(\d{4})\.parquet$"),
        "fire_target": list_store(FIRE_TARGET_DIR, r"^(.+)_(\d{4})\.parquet$"),
        "fire_history": list_store(FIRE_HIST_DIR, r"^(.+)\.parquet$"),
        "fire_drivers": list_store(FIRE_DRV_DIR, r"^(.+)\.parquet$"),
        "defo_matrix": list_store(DEFO_MATRIX_DIR, r"^([a-z].*)\.parquet$"),
        "defo_target": list_store(DEFO_TARGET_DIR, r"^([a-z].*)\.parquet$"),
    }
    for k, ent in stores.items():
        C.ft[k] = None if A.no_footers else scan_footers(k, ent, A.cache_dir, A.refresh_cache)
    C.probe = cadence_probe(A.cache_dir, A.refresh_cache, C.panel_cols)

    tables = {}
    tables["pm25"], pm_feats = pm25_rows(C)
    tables["fire"], fire_feats = fire_rows(C)
    tables["defo"], defo_feats = defo_rows(C)
    tables["ndvi"], nd_base, lagv, lag_orders = ndvi_rows(C)

    # ---- consistency against the shipped counts (fail loud) ----
    m = re.search(r"pool allocated: [\d,]+ x (\d+) float32", open(FIRE_POOL_LOG, encoding="utf-8", errors="replace").read())
    fire_n = int(m.group(1)) if m else None
    fire_panel = [c for c in C.panel_cols if c not in KEY_COLS and c not in ("lat", "lon")]
    fb = lists("fire_ban.py")
    fire_ban_all = {v for n in ["BAN_LABEL", "BAN_LOOKAHEAD", "BAN_POSTFIRE", "CONDITIONAL_LAG1", "SUSPECT_TREND"]
                    for v, _ in need(fb, n, "fire_ban.py")}
    fire_ship = [c for c in fire_panel if c not in fire_ban_all]
    hist_keep = [c for c in C.side["fire_history"]["_order"]
                 if c not in {v for v, _ in need(lists("fire_architecture.py"), "HIST_DROP", "fire_architecture.py")}]
    n_fire = len(fire_ship) + len(hist_keep) + len(C.side["fire_drivers"]["_order"])
    if fire_n is not None and n_fire != fire_n:
        raise SystemExit("export_review_csv: reconstructed fire feature list has %d columns, the shipped pool had %d"
                         % (n_fire, fire_n))
    m = re.search(r"\| (\d+) features \|", open(DEFO_MATRIX_LOG, encoding="utf-8", errors="replace").read())
    if m and int(m.group(1)) != len(defo_feats):
        raise SystemExit("export_review_csv: defo matrix has %d features, its log says %s" % (len(defo_feats), m.group(1)))
    n_water = sum(1 for r in tables["ndvi"] if r["store"].startswith("engineered (NDVI"))
    exp_lags = 612 - len(nd_base) - n_water
    checks = dict(
        pm25_features_run_log=len(pm_feats),
        fire_features_reconstructed=n_fire, fire_pool_width_logged=fire_n,
        defo_matrix_features=len(defo_feats),
        ndvi_base_features=len(nd_base), ndvi_water_memory_features=n_water,
        ndvi_lag_columns_implied_by_612=exp_lags, ndvi_lag_orders=lag_orders,
        ndvi_lag_parents_from_probe=len(lagv), ndvi_lag_parents_implied=exp_lags / float(len(lag_orders)),
    )
    cross_notes(tables)

    # ---- write ----
    for p in ("pm25", "fire", "defo", "ndvi"):
        cols = [r["column"] for r in tables[p]]
        dup = [c for c, n in collections.Counter(cols).items() if n > 1]
        if dup:
            raise SystemExit("export_review_csv: duplicate rows in %s: %s" % (p, dup))
        write_csv(os.path.join(out, "review", "%s_columns.csv" % p), tables[p])
    h, o = panel_yaml(C, stamp_time)
    write_yaml(os.path.join(out, "_stores", "monthly_panel_v170.yaml"), h, o)
    for name in ("gfed_burn", "edgar_emis", "fire_history", "fire_drivers"):
        h, o = side_yaml(name, C, stamp_time)
        write_yaml(os.path.join(out, "_stores", "%s_catalog.yaml" % name), h, o)

    # ---- summary ----
    log("")
    log("WROTE (new files) under %s" % out)
    for p in ("pm25", "fire", "defo", "ndvi"):
        cnt = collections.Counter(r["current_verdict"] for r in tables[p])
        fl = sum(1 for r in tables[p] if "R30 FLAG" in r["missing_share_note"])
        cmn = sum(1 for r in tables[p] if r["co_measured_candidate"].startswith("yes"))
        log("  review/%s_columns.csv  %3d rows  %s  | R30 flags %d | co-measured candidates %d"
            % (p, len(tables[p]), dict(sorted(cnt.items())), fl, cmn))
    log("  _stores/monthly_panel_v170.yaml + 4 side-store catalogs")
    log("CHECKS " + json.dumps(checks))
    diffs = [c for c in C.panel_cols if c not in KEY_COLS and "DIFFERS" in probe_note(C.probe, C.facts[c])]
    log("CADENCE SAMPLE DIFFERS FROM SEED for %d columns: %s" % (len(diffs), ", ".join(diffs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
