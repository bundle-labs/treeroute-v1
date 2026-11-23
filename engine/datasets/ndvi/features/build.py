"""NDVI package: the feature script (plan 1.5). It rebuilds run89's engineered tree columns and its router
context DATE-SAFE: every output is a trailing function of driver columns ending at the row's own step,
declared with its store facts, so the engine's R8 lags it from those facts and, at a lead, moves it to
the issue step with the rest of the feature row (plan 1.5 'Trailing only'; ruling Q33).

Outputs (each declared in OUTPUTS with derived_from, operation, a backward-only window, reads_target):
  - the 345 driver lags of run89's builder: <base>_lag<k> for the 69 bases of LAG_BASES and k in
    LAG_ORDERS = (1, 2, 3, 6, 12); the base's value of the SAME unit k calendar months earlier.
    LAG_BASES is run89's 87 bases (RUN89_LAG_BASES) minus the 18 that ban.yaml bans (DROPPED_LAG_BASES;
    owner ruling J4, OWNER_RULINGS_2026-10-05.md: "NDVI features/build.py drops the banned lag bases");
  - the 6 engineered lag-12 columns <base>_lag12 of LAG12_BASES (owner ruling J2 a): the SPEI block and
    AMO are missing in the test year 2023, so their raw columns stay banned (incomplete) and each is kept
    through one lag-12 column only, which reads the same calendar month a year earlier (2022 for 2023);
  - the 28 water-memory columns: <v>_roll<w> (trailing mean over w months, w = 3, 6, 12, of the 6
    WATER_VARS), precip_wytd and <v>_wytd (sum since the start of the June water year), api_precip and
    api_soilmoist (exponentially weighted mean, alpha 0.1), consec_dry_months and months_since_sig_rain
    (months since the last month with precipitation >= 10 mm / >= 30 mm);
  - the router context: the 4 seasonal harmonics ctx:sin1, ctx:cos1, ctx:sin2, ctx:cos2 of the
    calendar month, and the 5 top-5 context columns ctx:top5:* (the shipped list, frozen and disclosed:
    catalog.yaml data_selected, exceptions.yaml). The sixth run89 context column, a copy of the normal
    (ctx:climatology), is NOT built: it reads the target, and the engine's unpenalised normal column
    replaces it (plan 1.5, 'replaced_by_engine').

Contract with the engine (treeroute/pipeline/data.py, 'feature script hook'): OUTPUTS {column: store
facts in the store-catalog schema} and build(frame, keys) -> DataFrame with exactly the OUTPUTS columns,
one row per frame row in the frame's order. frame is sorted by unit then step and holds the key columns,
the engine's integer step and every derived_from source, with sentinels masked and NO lag applied.

HOW THE FACTS ARE MADE (derived, never typed). Each output's facts are COMPOSED from its source's facts
in the store catalogs dataset.yaml includes (read through treeroute.package.load.load_includes, which
checks their sha256): for every month of the timing rules' reference calendar, the content the output
describes is the union of timing.content_interval over the source periods it reads (t-k for a lag,
t-w+1..t for a trailing window, the water year to t, and every earlier step for the unbounded
operations). The output is then declared stamp period_end, align backward, over the months that union
spans (a superset where the source's content is shorter than its month), plus reach_after_max when the
source's content reaches past the end of the newest month read: in whole months when every reference
month gives the same whole-month reach (the ruled index reaches of rulings R-A a, R-C a), else the
largest reach in days (never too early). So a lag of a centred or filtered index keeps what is left of
its forward reach (nino34_lag1 reaches one month past its row: R8 gives it lag 1), and a column whose
source has an unknown window and no signed bound is declared unknown too (R8 refuses it at lag 0,
G-LAG), exactly like its source. A bound the owner signs on the source flows into its outputs here.
Legal range: a lag, trailing mean or weighted mean inherits the source's; a water-year sum spans
[min(lo, 12 lo), max(hi, 12 hi)] (up to 12 months; D35's sum rule); the run-length counts are [0, inf].

TRAILING ONLY AND CALENDAR ONLY (G-CALENDAR). Every look-back reads the SAME unit's earlier CALENDAR steps
on a dense (unit x step) grid built from the frame's own step column (a repeated (unit, step) is
refused); a missing step is missing, never the neighbouring row. No output reads the target, fits a
model or draws a random number.

DEPARTURES FROM run89's BUILD (bundle_lag_compare.build_feats_ext; OWNER REVIEW, dataset science):
  1. Sentinels are masked BEFORE the build (the engine's reader). run89 built its lags, rolls and sums
     on the unmasked panel and scrubbed the sentinels only afterwards (leak_audit.impute_masked), so in
     the 47 coastal regions whose V02_total_precip_mm carries -2^31 its water-memory columns were
     computed from the fill value.
  2. The run-length counts (consec_dry_months, months_since_sig_rain) are NaN until the unit's first
     event and after a month whose precipitation is missing, until the next event: the ruled default
     for 'years since' with no earlier event (io_science.recompute_declared_operation, OWNER DECISION
     'NaN (propose)', accepted by OWNER_RULINGS_2026-09-28.md A). run89 counted from the panel's first
     month (in a never-wet cell a clock of months since 2002-01, a time index) and counted a missing
     month as dry.
  3. The water-year sums and the weighted means keep pandas' semantics exactly (cumsum: NaN at a
     missing month, the finite months summed; ewm(alpha=0.1, adjust=False): a missing month decays the
     old weight), but on CALENDAR steps: a unit's absent month is a missing month (run89's rows were
     the dense panel, so the two agree wherever no month is absent).
  4. The lags run on calendar steps as run89's merge on t did; nothing else changes.
  5. (owner rulings J2 a and J4, 2026-10-05) The 18 bases ban.yaml bans are not lagged: their lags would
     take the base's ban (plan 1.4 family), and the engine refuses a feature built from a column banned for
     a leak reason (treeroute/pipeline/data.py check_feature_lineage). Of the six incomplete parents of the
     J2 (a) rule only the lag-12 column is built (its lags 1-6 read 2023 months, which are missing).
Everything else is run89's: the bases and 5 lag orders (the saved feature list, below), the windows
(3, 6, 12), the thresholds (10 mm, 30 mm), the June water year, alpha 0.1, the harmonics
sin/cos(2 pi (month - 0.5) / 12) and of twice that angle, and the top-5 context list.
CHECKED (tests/test_ndvi_package.py): on the 64 thar_desert cells x 264 months run89 saved
(D:/run89full/sandbox/sandbox_thar_desert.npz), all 379 lag and water-memory columns (345 + 6 lag-12 + 28; every
one is a run89 saved feature) equal run89's saved values wherever both are finite, up to run89's power-of-two
float16 column divisor (cross_region_full.get_colscale).

THE LIVESTOCK HOLD (owner ruling L3, OWNER_RULINGS_2026-10-05.md section L, 2026-10-06). The store's 2022 and 2023
aglw_* layers are not observations: they are the 2021 layer times INDIA's FAOSTAT ratios, written for every region
(the panel store catalog's provenance; observed_through 2021). L3: "Each package builds an engineered column that
holds the real 2021 layer for 2022-2023 (backward-only, declared). The raw aglw_* are banned ... The fixed columns
are 'watch', lagged one year by R8, and the hold is disclosed." So for each of the six HOLD_PARENTS:
  <parent>_hold2021  the parent's value on rows of a year up to HOLD_THROUGH_YEAR (2021); on a row of a later year
             the SAME unit's value in HOLD_THROUGH_YEAR at the same calendar month (calendar predecessor
             12 x (year - 2021) steps back, treeroute.io.steps.predecessor_index; a missing predecessor gives NaN,
             R30 decides). Backward only. HOLD_THROUGH_YEAR must equal the parent's store fact observed_through,
             or the script refuses (fail loudly).
Its facts are the parent's (dtype, units, cadence {1, year}, scope, stamp, window, legal range, product family,
observed_through, lineage and fact_status), so R8 lags it one year
exactly as it lagged the parent. The declared window is the parent's own year; a held row's content (2021) ends
earlier, so the declaration can only raise a lag. operation 'hold_last_observed through_year=2021 unit=year' (not a
lag k: R4 counts only 'lag k=<k> unit=<unit>' operations). The raw parents are banned 'incomplete' in ban.yaml
(ruling L3 names post_window_snapshot: see the ban.yaml header for why the reason word differs).
NOT SIGNED: the hold's facts drop the parent's reviewed_by and date. L1 (c) signs the parent aglw_* yearly facts;
the hold column and its operation are L3's, drafted by the agent, and L1 does not list them, so the column keeps
the parent's fact_status ('assumed') with no reviewer (defo's hold columns are written the same way). R8 reads
the window, cadence and stamp, not the reviewer, so the lag is the same either way.
The J2 (a) lag-12 columns carry the owner's signature of their composed window (ruling L1 c: 'the windows of the
engineered lag columns'): fact_status 'assumed' + reviewed_by owner + date 2026-10-06 (plan 1.3's spelling).
"""
# Provenance:
#   presplit_cc/bundle_lag_compare.py:50-81 (build_feats_ext: the lags, the rolls, precip_wytd, api_precip,
#     api_soilmoist, the <v>_wytd sums, consec_dry_months, months_since_sig_rain);
#   presplit_cc/experiment_thar_regime_full.py:34-37 (WATERVARS, WINDOWS = [3, 6, 12], PRECIP);
#   presplit_cc/experiment1_cellrouting_bundle.py:52 (LAG_ORDERS = (1, 2, 3, 6, 12));
#   presplit_cc/cross_region_run89.py:1541 (LAGV = the lag bases), :887-889 (top5 = argsort of the helpers'
#     mean importance; th = 2 pi (mo - 0.5) / 12; ctx = [clim, sin th, cos th, sin 2th, cos 2th, X[:, top5]]);
#   D:/run89full/sandbox/sandbox_thar_desert.npz 'feats' (the 612 features run89 fed: 177 base + the 435
#     lags of the 87 bases of RUN89_LAG_BASES below, in this order; read-only, 2026-09-29);
#   OWNER_RULINGS_2026-10-05.md J2 (a) and J4 (LAG12_BASES, DROPPED_LAG_BASES).

import math
from pathlib import Path

import numpy as np
import pandas as pd

from treeroute.io.steps import predecessor_index
from treeroute.package.load import load_dataset_file, load_includes
from treeroute.timing import TimingRefusal, content_interval
from treeroute.timing.calendar import (REFERENCE_FIRST_YEAR, REFERENCE_YEARS, month_first_day,
                                       month_index)

PACKAGE_ROOT = Path(__file__).resolve().parent.parent

# origin: D:/run89full/sandbox/sandbox_thar_desert.npz 'feats' (the lag bases, in run89's order; the rule
# that picked them is bundle_lag_compare.py:55-58 on thar_desert's first 200 cells, cross_region_run89.py:1541)
RUN89_LAG_BASES = (
    "V01_mean_temp_C", "diurnal_temp_range_C", "V02_total_precip_mm", "V07_total_ref_ET_mm", "aet_total_mm",
    "climate_water_deficit_mm", "soil_water_tc_mm", "V05_mean_vpd_kPa", "V09_mean_wind_ms",
    "solar_radiation_Wm2", "aridity_index_p_pet", "tc_vapor_pressure", "cloud_frequency_pct", "V06_spei_12m",
    "spei_01m", "spei_03m", "spei_06m", "spei_24m", "heatwave_days_gt35C", "gdd5_degC_days", "wet_day_count",
    "V03_max_daily_precip_mm", "precip_intensity_mm", "vpd_max_daily", "vpd_days_gt_2kpa",
    "vpd_warm_season_mean", "rmin_pct", "sph_kgkg", "V30_soil_moisture_pct", "sst_anom_atl3",
    "sst_anom_iod_west", "sst_anom_iod_east", "sst_anom_subpolar_north_atlantic", "sst_anom_coral_sea",
    "sst_anom_mediterranean", "sst_anom_global_tropical_mean", "sst_anom_nino34", "nino12", "nino3", "nino4",
    "nino34", "oni", "soi", "tni", "pdo", "amo", "tna", "tsa", "iod", "noi", "ao", "nao", "pna", "wp", "epo",
    "sam", "co2", "food_price_index", "food_meat", "food_dairy", "food_cereals", "food_oils", "food_sugar",
    "grace_lwe", "deeprec_twsa", "era5l_pev", "era5l_sro", "era5l_ssro", "era5l_slhf", "era5l_sshf",
    "era5l_ssr", "era5l_str", "era5l_d2m", "era5l_stl1", "esacci_sm", "scpdsi", "spi_01m", "spi_03m",
    "spi_06m", "spi_12m", "spi_24m", "eddi", "wbal_mm", "wbal_roll3", "wbal_roll6", "wbal_roll12",
    "wbal_roll24")
# origin: owner ruling J4 (OWNER_RULINGS_2026-10-05.md: "NDVI features/build.py drops the banned lag bases"):
# run89's bases that ban.yaml bans, with the ban (reason word) that drops them. tests/test_ndvi_package_ban.py checks
# this list against ban.yaml both ways (every dropped base is banned there, every banned run89 base is here).
DROPPED_LAG_BASES = (
    "aridity_index_p_pet",                                   # structural (seasonal missing mask)
    "V06_spei_12m", "spei_01m", "spei_03m", "spei_06m", "spei_24m", "amo",  # incomplete (empty in 2023): J2 a
    "sst_anom_mediterranean", "co2", "food_price_index", "food_meat", "food_dairy", "food_cereals",
    "food_oils", "food_sugar", "scpdsi",                      # trend_proxy
    "esacci_sm",                                             # incomplete (30% missing in donor rows)
    "eddi")                                                  # structural (seasonal missing mask)
LAG_BASES = tuple(b for b in RUN89_LAG_BASES if b not in DROPPED_LAG_BASES)
# origin: owner ruling J2 (a): a column missing in a test year (the SPEI block, AMO) is kept through ONE
# dataset-owned engineered lag-12 column (derived_from the parent, operation lag 12); the raw parent stays banned
LAG12_BASES = ("V06_spei_12m", "spei_01m", "spei_03m", "spei_06m", "spei_24m", "amo")
LAG12_ORDER = 12
# origin: experiment1_cellrouting_bundle.py:52
LAG_ORDERS = (1, 2, 3, 6, 12)
# origin: experiment_thar_regime_full.py:34-37
WATER_VARS = ("V02_total_precip_mm", "soil_water_tc_mm", "V30_soil_moisture_pct", "V07_total_ref_ET_mm",
              "aet_total_mm", "climate_water_deficit_mm")
ROLL_WINDOWS = (3, 6, 12)
PRECIP = "V02_total_precip_mm"
SOIL_MOISTURE = "V30_soil_moisture_pct"
# origin: bundle_lag_compare.py:69-75 (wy = year - (month < 6): the water year starts in June)
WATER_YEAR_START_MONTH = 6
WYTD = (("precip_wytd", PRECIP),) + tuple(("%s_wytd" % v, v) for v in (
    "soil_water_tc_mm", "V30_soil_moisture_pct", "V07_total_ref_ET_mm", "aet_total_mm",
    "climate_water_deficit_mm"))
# origin: bundle_lag_compare.py:71-72 (ewm(alpha=0.1, adjust=False).mean() per cell)
API_ALPHA = 0.1
API = (("api_precip", PRECIP), ("api_soilmoist", SOIL_MOISTURE))
# origin: bundle_lag_compare.py:76-79 (wet10 = precip >= 10; sig30 = precip >= 30)
RUN_LENGTHS = (("consec_dry_months", PRECIP, 10.0), ("months_since_sig_rain", PRECIP, 30.0))
# origin: cross_region_run89.py:888-889 (th = 2 pi (mo - 0.5) / 12; sin th, cos th, sin 2th, cos 2th)
HARMONICS = (("ctx:sin1", np.sin, 1), ("ctx:cos1", np.cos, 1), ("ctx:sin2", np.sin, 2), ("ctx:cos2", np.cos, 2))
# origin: cross_region_run89.py:887 (top5, frozen as shipped: catalog.yaml data_selected; exceptions.yaml);
# (column, source, k): k = 0 is the source itself under its context name
TOP5 = (("ctx:top5:sph_kgkg_lag6", "sph_kgkg", 6), ("ctx:top5:era5l_slhf_lag1", "era5l_slhf", 1),
        ("ctx:top5:V07_total_ref_ET_mm_lag1", "V07_total_ref_ET_mm", 1), ("ctx:top5:era5l_d2m", "era5l_d2m", 0),
        ("ctx:top5:V01_mean_temp_C", "V01_mean_temp_C", 0))
# The unbounded operations (the weighted means, the run lengths) read every earlier step of the unit: their
# declared window spans the store's record, 22 years 2002-01..2023-12 (monthly_panel_v170: one file per
# group-year, 2002-2023; its store catalog description). R8 reads only a window's forward edge, so this
# length never moves a lag; it states how far back the content can reach.
RECORD_MONTHS = 264
MONTHS = 12
UNIT_BLOCK = 4096            # units per block of the dense-grid build (memory only; results do not depend on it)
_SHOW = 5


class FeatureBuildError(Exception):
    """The feature script refuses (fail loudly; nothing is guessed)."""


def lag_column(base, k):
    return "%s_lag%d" % (base, k)


def roll_column(var, w):
    return "%s_roll%d" % (var, w)


# Owner ruling L3: the yearly livestock columns whose 2022-2023 layers are not observations (store observed_through
# 2021); each is kept through <parent>_hold2021 (the raw parents are banned in ban.yaml).
HOLD_PARENTS = ("aglw_cattle", "aglw_buffalo", "aglw_horse", "aglw_sheep", "aglw_goats", "aglw_total_lsu")
HOLD_THROUGH_YEAR = 2021
# Owner ruling L1 (c): the owner signs the windows of the engineered lag columns (the six J2 a lag-12 columns),
# written in plan 1.3's spelling of a signed fact (the schema has no 'signed' fact_status).
# NOT signed: the other 350 lag outputs (345 driver lags and the 5 frozen top-5 context lags), the rolls, sums and
# harmonics. The list 'yes to all' answered (BAN_INSTALL_REPORT.md section 8 C) names the windows of the lag-12
# columns on PM2.5, fire and NDVI and of defo's 18 lag-1 columns only; these copy their source's fact_status
# (270 'unverified', 80 'assumed') with no reviewer. OWNER QUESTION: does L1 (c) cover them too?
LAG12_SIGNATURE = {"fact_status": "assumed", "reviewed_by": "owner", "date": "2026-10-06"}
LAG12_SIGNATURE_NOTE = ("window signed by the owner 2026-10-06 (ruling L1 c: 'the windows of the engineered lag "
                        "columns'), written fact_status 'assumed' + reviewed_by owner + date")


def hold_column(parent):
    return "%s_hold%d" % (parent, HOLD_THROUGH_YEAR)


def _hold_facts(name, facts):
    """The facts of <parent>_hold2021: the parent's, with derived_from and the hold operation (ruling L3)."""
    cad = facts.cadence
    if not (_value(cad.kind) == "regular" and cad.length == 1 and _value(cad.unit) == "year"):
        raise FeatureBuildError("hold parent %r has cadence %s; the L3 hold is for yearly columns" % (name, cad))
    if str(facts.observed_through) != str(HOLD_THROUGH_YEAR):
        raise FeatureBuildError("hold parent %r: store observed_through %r is not HOLD_THROUGH_YEAR %d; the hold "
                                "must keep the last observed year" % (name, facts.observed_through, HOLD_THROUGH_YEAR))
    out = facts.model_dump(exclude_none=True, exclude_defaults=True)
    for field in ("fill_values", "near_sentinel_optout"):       # the frame arrives with sentinels masked
        out.pop(field, None)
    for field in ("reviewed_by", "date"):     # the owner signed the parent (L1 c), not this L3 column
        out.pop(field, None)
    out.update({"derived_from": [name], "reads_target": False,
                "operation": "hold_last_observed through_year=%d unit=year" % HOLD_THROUGH_YEAR})
    out["provenance"] = (
        "owner ruling L3 (OWNER_RULINGS_2026-10-05.md section L): %s on rows up to %d; on a row of a later year the "
        "same unit's %d value (calendar predecessor, backward only), so the 2022-2023 layers (the 2021 layer times "
        "India's FAOSTAT ratios) are never read; facts are the parent's without its owner signature (L1 c signs the parent; L1 does not list this column, so it is unsigned); "
        "features/build.py" % (name, HOLD_THROUGH_YEAR, HOLD_THROUGH_YEAR))
    return out


def _held(frame, year_col, codes, steps, source):
    """<source>_hold2021 on the frame's rows: rows up to 2021 the source itself; a later row the same unit's 2021
    row at the same calendar month (backward only; a missing predecessor gives NaN)."""
    years = frame[year_col].to_numpy().astype(np.int64)
    after = years > HOLD_THROUGH_YEAR
    values = np.asarray(frame[source].to_numpy(), dtype=np.float64)
    out = np.where(after, np.nan, values)
    for gap in np.unique(years[after] - HOLD_THROUGH_YEAR):
        rows = years - HOLD_THROUGH_YEAR == gap
        prev = predecessor_index(codes, steps, int(gap) * MONTHS)
        ok = rows & (prev >= 0)
        out[ok] = values[prev[ok]]
    return out


# ---------------------------------------------------------------------------------------------------
# The source facts (store catalogs included by dataset.yaml, sha256-checked by load_includes)
def _source_facts():
    dataset = load_dataset_file(PACKAGE_ROOT)
    stores, _ = load_includes(PACKAGE_ROOT, dataset)
    out = {}
    for path, catalog in sorted(stores.items()):
        for column, facts in catalog.columns.items():
            if column in out:
                raise FeatureBuildError("column %r is declared by two included store catalogs" % column)
            out[column] = facts
    return out


class _Named(object):
    """A store-column fact object with a name, for the timing helpers' messages."""

    def __init__(self, name, facts):
        self.name = name
        self._facts = facts

    def __getattr__(self, item):
        return getattr(self._facts, item)


def _value(x):
    return getattr(x, "value", x)


def _reference_months():
    first = REFERENCE_FIRST_YEAR * MONTHS
    return range(first, first + REFERENCE_YEARS * MONTHS)


def _month_period(index):
    return month_first_day(index), month_first_day(index + 1) - 1


class _Content(object):
    """content_interval of one monthly source, cached per month index."""

    def __init__(self, name, facts):
        self.name = name
        self.facts = facts
        self.view = _Named(name, facts)
        self._cache = {}

    def __call__(self, index):
        if index not in self._cache:
            self._cache[index] = content_interval(self.view, _month_period(index))
        return self._cache[index]


def _check_monthly(name, facts):
    cad = facts.cadence
    if not (_value(cad.kind) == "regular" and cad.length == 1 and _value(cad.unit) == "month"):
        raise FeatureBuildError("source %r has cadence %s; the NDVI feature script reads monthly columns only"
                                % (name, cad))


def _composed_window(content, offsets_of, unbounded):
    """(window dict, stamp) of an output that reads, at month M, the source months M - j for j in
    offsets_of(M) (see the module docstring)."""
    reach_months, month_ends, reach_days = set(), True, []
    back = 0
    for m in _reference_months():
        spans = [content(m - j) for j in offsets_of(m)]
        first = min(a for a, _ in spans)
        last = max(b for _, b in spans)
        reach_days.append(last - _month_period(m)[1])
        last_month = month_index(last)
        if last == _month_period(last_month)[1]:
            reach_months.add(last_month - m)
        else:
            month_ends = False
        back = max(back, m - month_index(first))
    window = {"length": RECORD_MONTHS if unbounded else back + 1, "unit": "month", "align": "backward"}
    if month_ends and len(reach_months) == 1:
        r = reach_months.pop()
        if r > 0:
            window["reach_after_max"] = {"value": r, "unit": "month"}
    else:
        d = max(reach_days)
        if d > 0:
            window["reach_after_max"] = {"value": d, "unit": "day"}
    return window, "period_end"


def _inherited(name, facts):
    out = {"dtype": facts.dtype, "units": facts.units,
           "cadence": {"kind": "regular", "length": 1, "unit": "month"},
           "scope": _value(facts.scope), "fact_status": _value(facts.fact_status),
           "reads_target": False, "derived_from": [name]}
    for field in ("product_family", "observed_through", "baseline_period"):
        v = getattr(facts, field, None)
        if v is not None:
            out[field] = list(v) if isinstance(v, tuple) else v
    if facts.lineage is not None:
        out["lineage"] = facts.lineage.model_dump()
    if facts.absent_groups:
        out["absent_groups"] = dict(facts.absent_groups)
    return out


def _composed(name, facts, content, offsets_of, unbounded, operation, dtype, legal_range, units, provenance):
    _check_monthly(name, facts)
    out = _inherited(name, facts)
    try:
        out["window"], out["stamp"] = _composed_window(content, offsets_of, unbounded)
    except TimingRefusal as err:
        if err.rule != "G-LAG":
            raise
        # the source's content is unknown (no bound, or a bound nobody signed): the output's is unknown too,
        # declared with the source's own window, so R8 refuses both at lag 0 (G-LAG)
        out["window"] = facts.window.model_dump(exclude_none=True)
        out["stamp"] = _value(facts.stamp)
    out["dtype"] = dtype
    out["operation"] = operation
    if units is not None:
        out["units"] = units
    if legal_range is not None:
        out["legal_range"] = [float(legal_range[0]), float(legal_range[1])]
    out["provenance"] = provenance
    return out


def _source_range(facts):
    r = facts.legal_range
    return None if r is None else (float(r[0]), float(r[1]))


def _sum_range(facts, n):
    r = _source_range(facts)
    if r is None:
        return None
    lo, hi = r
    return min(lo, n * lo), max(hi, n * hi)


def _declare():
    facts = _source_facts()
    contents = {}

    def src(name):
        if name not in facts:
            raise FeatureBuildError("source %r is in no store catalog dataset.yaml includes" % name)
        if name not in contents:
            contents[name] = _Content(name, facts[name])
        return facts[name], contents[name]

    out = {}

    def lag_facts(base, k, column, why):
        f, c = src(base)
        return _composed(base, f, c, lambda m, k=k: (k,), False, "lag k=%d unit=month" % k,
                         "float32" if f.dtype == "float32" else "float64", _source_range(f), None,
                         "%s: %s (k = %d months, same unit, calendar predecessor); features/build.py"
                         % (why, "lag %d of %s" % (k, base) if k else "the store column %s itself" % base, k))

    for k in LAG_ORDERS:
        for base in LAG_BASES:
            out[lag_column(base, k)] = lag_facts(base, k, lag_column(base, k),
                                                 "run89 driver lag (bundle_lag_compare.py:59-63)")
    for base in LAG12_BASES:
        column = lag_column(base, LAG12_ORDER)
        if column in out:
            raise FeatureBuildError("%r is declared twice (a lag-12 base is also a LAG_BASES base)" % column)
        out[column] = lag_facts(base, LAG12_ORDER, column,
                                "owner ruling J2 (a): engineered lag-12 column of a parent missing in a test "
                                "year (the parent stays banned, incomplete); run89 built the same lag "
                                "(bundle_lag_compare.py:59-63)")
        out[column]["provenance"] += "; " + LAG12_SIGNATURE_NOTE
        out[column].update(LAG12_SIGNATURE)
    for v in WATER_VARS:
        f, c = src(v)
        for w in ROLL_WINDOWS:
            out[roll_column(v, w)] = _composed(
                v, f, c, lambda m, w=w: tuple(range(w)), False,
                "trailing_mean w=%d unit=month min_count=1" % w, "float64", _source_range(f), None,
                "run89 water memory (bundle_lag_compare.py:64-67): mean of the finite values of %s over the "
                "%d months ending at the row (pandas rolling(%d, min_periods=1)); features/build.py" % (v, w, w))
    for column, v in WYTD:
        f, c = src(v)
        out[column] = _composed(
            v, f, c, lambda m: tuple(range((m % MONTHS + 1 - WATER_YEAR_START_MONTH) % MONTHS + 1)), False,
            "cumulative stat=sum reset_month=%d unit=month" % WATER_YEAR_START_MONTH, "float64",
            _sum_range(f, MONTHS), None,
            "run89 water memory (bundle_lag_compare.py:69-75): sum of %s since the start of the water year "
            "(June), NaN at a missing month (pandas cumsum per cell and water year); features/build.py" % v)
    for column, v in API:
        f, c = src(v)
        out[column] = _composed(
            v, f, c, lambda m: (0,), True, "cumulative stat=ewm_mean alpha=%g adjust=false unit=month" % API_ALPHA,
            "float64", _source_range(f), None,
            "run89 water memory (bundle_lag_compare.py:71-72): exponentially weighted mean of %s, alpha %g, "
            "pandas ewm(adjust=False, ignore_na=False) on calendar steps; reads every earlier month; "
            "features/build.py" % (v, API_ALPHA))
    for column, v, threshold in RUN_LENGTHS:
        f, c = src(v)
        out[column] = _composed(
            v, f, c, lambda m: (0,), True,
            "years_since event='%s >= %g' unit=month no_event=nan" % (v, threshold), "float64",
            (0.0, math.inf), "month",
            "run89 water memory (bundle_lag_compare.py:76-79): months since the last month with %s >= %g "
            "(0 in such a month); NaN before the unit's first such month and after a missing month until "
            "the next one (departure 2 of the module docstring); features/build.py" % (v, threshold))
    for column, source, k in TOP5:
        out[column] = lag_facts(source, k, column, "run89 top-5 router context (cross_region_run89.py:887), "
                                                   "frozen as shipped and disclosed")
    for parent in HOLD_PARENTS:
        if parent not in facts:
            raise FeatureBuildError("hold parent %r is in no store catalog dataset.yaml includes" % parent)
        out[hold_column(parent)] = _hold_facts(parent, facts[parent])
    for column, fn, order in HARMONICS:
        out[column] = {
            "dtype": "float64", "units": "1", "cadence": {"kind": "regular", "length": 1, "unit": "month"},
            "scope": "global", "stamp": "period_end",
            "window": {"length": 1, "unit": "month", "align": "backward"},
            "legal_range": [-1.0, 1.0], "derived_from": ["month"], "reads_target": False,
            "operation": "calendar_harmonic %s order=%d angle=2*pi*(month-0.5)/12" % (fn.__name__, order),
            "fact_status": "unverified",
            "provenance": "router context: %s(%d x 2 pi (month - 0.5) / 12) of the calendar month, from the "
                          "key_time column month (cross_region_run89.py:888-889); features/build.py"
                          % (fn.__name__, order)}
    return out


OUTPUTS = _declare()


# ---------------------------------------------------------------------------------------------------
# The build
def _month_of_step(steps):
    """Calendar month (1..12) of monthly steps year x 12 + month (io.steps.step_index, D28)."""
    steps = np.asarray(steps, dtype=np.int64)
    return steps - MONTHS * ((steps - 1) // MONTHS)


def _dense(values, rows_u, rows_s, n_units, n_steps):
    grid = np.full((n_units, n_steps), np.nan)
    grid[rows_u, rows_s] = values
    return grid


def _lag(grid, k):
    out = np.full_like(grid, np.nan)
    if k == 0:
        out[:] = grid
    elif k < grid.shape[1]:
        out[:, k:] = grid[:, :-k]
    return out


def _trailing_mean(grid, w):
    total = np.zeros_like(grid)
    count = np.zeros(grid.shape, dtype=np.int64)
    for j in range(w):
        shifted = _lag(grid, j)
        ok = np.isfinite(shifted)
        total[ok] += shifted[ok]
        count += ok
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(count > 0, total / np.maximum(count, 1), np.nan)


def _water_year_sum(grid, months):
    """pandas' cumsum per unit and water year: at a finite month the sum of the finite months of the water
    year so far, NaN at a missing month; the sum restarts in the water year's first month."""
    out = np.full_like(grid, np.nan)
    state = np.zeros(grid.shape[0])
    for s in range(grid.shape[1]):
        if s == 0 or months[s] == WATER_YEAR_START_MONTH:
            state = np.zeros(grid.shape[0])
        v = grid[:, s]
        ok = np.isfinite(v)
        state = state + np.where(ok, v, 0.0)
        out[ok, s] = state[ok]
    return out


def _ewm_mean(grid, alpha):
    """pandas' ewm(alpha, adjust=False, ignore_na=False).mean() along each unit's calendar steps (a missing
    month decays the old weight; NaN until the first observation)."""
    out = np.full_like(grid, np.nan)
    weighted = np.full(grid.shape[0], np.nan)
    old_wt = np.ones(grid.shape[0])
    factor = 1.0 - alpha
    for s in range(grid.shape[1]):
        cur = grid[:, s]
        obs = np.isfinite(cur)
        has = np.isfinite(weighted)
        old_wt = np.where(has, old_wt * factor, old_wt)
        upd = has & obs & (weighted != cur)
        weighted = np.where(upd, (old_wt * weighted + alpha * cur) / (old_wt + alpha), weighted)
        old_wt = np.where(has & obs, 1.0, old_wt)
        weighted = np.where(~has & obs, cur, weighted)
        out[:, s] = weighted
    return out


def _months_since(grid, threshold):
    """Months since the last month >= threshold (0 in such a month); NaN before the first one and after a
    missing month until the next one."""
    out = np.full_like(grid, np.nan)
    count = np.full(grid.shape[0], np.nan)
    for s in range(grid.shape[1]):
        v = grid[:, s]
        obs = np.isfinite(v)
        event = obs & (v >= threshold)
        count = np.where(event, 0.0, np.where(obs, count + 1.0, np.nan))
        out[:, s] = count
    return out


def build(frame, keys):
    """Every OUTPUTS column on the frame's rows (see the module docstring)."""
    unit_col, step_col = keys["unit"], keys["step"]
    month_col = [c for c, part in keys["time"].items() if part == "month"]
    if len(month_col) != 1:
        raise FeatureBuildError("the catalog must hold one key_time column with calendar part 'month', got %s"
                                % month_col)
    n = len(frame)
    sources = sorted({s for f in OUTPUTS.values() for s in f["derived_from"]} - {month_col[0]})
    missing = [s for s in sources if s not in frame.columns]
    if missing:
        raise FeatureBuildError("the frame lacks the sources %s" % missing[:_SHOW])
    steps = frame[step_col].to_numpy().astype(np.int64)
    months = frame[month_col[0]].to_numpy().astype(np.int64)
    if n and not np.array_equal(_month_of_step(steps), months):
        raise FeatureBuildError("the step column does not hold the rows' calendar months (monthly steps "
                                "year x 12 + month expected)")
    codes = pd.factorize(frame[unit_col].to_numpy(), sort=False)[0].astype(np.int64)
    if n and ((np.diff(codes) < 0).any() or ((np.diff(codes) == 0) & (np.diff(steps) <= 0)).any()):
        # sorted by unit (in order of first appearance) then strictly increasing step: no repeated (unit, step)
        raise FeatureBuildError("the frame is not sorted by unit then step, or repeats a (unit, step)")

    out = {}
    for column, f in OUTPUTS.items():
        out[column] = np.full(n, np.nan, dtype=np.float32 if f["dtype"] == "float32" else np.float64)
    # the harmonics: a function of the row's own calendar month
    theta = 2.0 * np.pi * (months - 0.5) / MONTHS
    for column, fn, order in HARMONICS:
        out[column][:] = fn(order * theta)
    if n == 0:
        return pd.DataFrame(out, index=frame.index, copy=False)

    s_min, s_max = int(steps.min()), int(steps.max())
    n_steps = s_max - s_min + 1
    grid_months = _month_of_step(np.arange(s_min, s_max + 1))
    by_source = {}
    held = {hold_column(p): p for p in HOLD_PARENTS}
    for column, f in OUTPUTS.items():
        if f["derived_from"] != [month_col[0]] and column not in held:
            (source,) = f["derived_from"]
            by_source.setdefault(source, []).append(column)
    lag_of = {lag_column(b, k): k for k in LAG_ORDERS for b in LAG_BASES}
    lag_of.update({lag_column(b, LAG12_ORDER): LAG12_ORDER for b in LAG12_BASES})
    lag_of.update({c: k for c, _, k in TOP5})
    roll_of = {roll_column(v, w): w for v in WATER_VARS for w in ROLL_WINDOWS}
    wytd = dict(WYTD)
    api = dict(API)
    runs = {c: t for c, _, t in RUN_LENGTHS}
    starts = np.flatnonzero(np.r_[True, codes[1:] != codes[:-1]])
    n_units = len(starts)
    bounds = np.r_[starts, n]
    for b0 in range(0, n_units, UNIT_BLOCK):
        b1 = min(b0 + UNIT_BLOCK, n_units)
        r0, r1 = int(bounds[b0]), int(bounds[b1])
        rows_u = codes[r0:r1] - codes[r0]
        rows_s = steps[r0:r1] - s_min
        nu = b1 - b0
        if rows_u.min() < 0 or rows_u.max() >= nu:
            raise FeatureBuildError("internal: unit codes of a block are not contiguous")
        for source, columns in by_source.items():
            grid = _dense(np.asarray(frame[source].to_numpy()[r0:r1], dtype=np.float64), rows_u, rows_s, nu,
                          n_steps)
            for column in columns:
                if column in lag_of:
                    result = _lag(grid, lag_of[column])
                elif column in roll_of:
                    result = _trailing_mean(grid, roll_of[column])
                elif column in wytd:
                    result = _water_year_sum(grid, grid_months)
                elif column in api:
                    result = _ewm_mean(grid, API_ALPHA)
                elif column in runs:
                    result = _months_since(grid, runs[column])
                else:
                    raise FeatureBuildError("internal: no builder for %r" % column)
                out[column][r0:r1] = result[rows_u, rows_s]
    year_col = [c for c, part in keys["time"].items() if part == "year"]
    if len(year_col) != 1:
        raise FeatureBuildError("the catalog must hold one key_time column with calendar part 'year', got %s"
                                % year_col)
    for column, parent in held.items():
        out[column][:] = _held(frame, year_col[0], codes, steps, parent)
    for column, values in out.items():
        if np.isinf(values).any():
            raise FeatureBuildError("output %r holds infinite values" % column)
    return pd.DataFrame(out, index=frame.index, copy=False)


# >>> SIGNOFF BLOCK (written by datasets/_tools/apply_signoff.py; do not edit by hand) >>>
# The owner signed the composed timing facts of these outputs (FREEZE_SIGNOFF_SHEET.md S5): fact_status 'assumed' + reviewed_by
# owner + date, plan 1.3's spelling of a signed fact. Each entry: column -> (ruling id, date, rulings file).
# The parents' facts were signed first (S1-S4 or earlier rulings); a renamed or removed output fails
# loudly here (KeyError). Written by datasets/_tools/apply_signoff.py; edit the answers, not this block.
SIGNOFF_COLUMNS = {
    'V01_mean_temp_C_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V01_mean_temp_C_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V01_mean_temp_C_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V01_mean_temp_C_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V01_mean_temp_C_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V02_total_precip_mm_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V02_total_precip_mm_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V02_total_precip_mm_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V02_total_precip_mm_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V02_total_precip_mm_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V02_total_precip_mm_roll12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V02_total_precip_mm_roll3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V02_total_precip_mm_roll6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V03_max_daily_precip_mm_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V03_max_daily_precip_mm_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V03_max_daily_precip_mm_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V03_max_daily_precip_mm_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V03_max_daily_precip_mm_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V05_mean_vpd_kPa_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V05_mean_vpd_kPa_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V05_mean_vpd_kPa_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V05_mean_vpd_kPa_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V05_mean_vpd_kPa_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V07_total_ref_ET_mm_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V07_total_ref_ET_mm_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V07_total_ref_ET_mm_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V07_total_ref_ET_mm_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V07_total_ref_ET_mm_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V07_total_ref_ET_mm_roll12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V07_total_ref_ET_mm_roll3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V07_total_ref_ET_mm_roll6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V07_total_ref_ET_mm_wytd': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V09_mean_wind_ms_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V09_mean_wind_ms_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V09_mean_wind_ms_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V09_mean_wind_ms_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V09_mean_wind_ms_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V30_soil_moisture_pct_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V30_soil_moisture_pct_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V30_soil_moisture_pct_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V30_soil_moisture_pct_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V30_soil_moisture_pct_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V30_soil_moisture_pct_roll12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V30_soil_moisture_pct_roll3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V30_soil_moisture_pct_roll6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V30_soil_moisture_pct_wytd': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aet_total_mm_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aet_total_mm_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aet_total_mm_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aet_total_mm_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aet_total_mm_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aet_total_mm_roll12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aet_total_mm_roll3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aet_total_mm_roll6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aet_total_mm_wytd': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aglw_buffalo_hold2021': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aglw_cattle_hold2021': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aglw_goats_hold2021': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aglw_horse_hold2021': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aglw_sheep_hold2021': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aglw_total_lsu_hold2021': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'ao_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'ao_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'ao_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'ao_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'ao_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'api_precip': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'api_soilmoist': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'climate_water_deficit_mm_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'climate_water_deficit_mm_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'climate_water_deficit_mm_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'climate_water_deficit_mm_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'climate_water_deficit_mm_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'climate_water_deficit_mm_roll12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'climate_water_deficit_mm_roll3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'climate_water_deficit_mm_roll6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'climate_water_deficit_mm_wytd': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'cloud_frequency_pct_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'cloud_frequency_pct_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'cloud_frequency_pct_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'cloud_frequency_pct_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'cloud_frequency_pct_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'consec_dry_months': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'ctx:cos1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'ctx:cos2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'ctx:sin1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'ctx:sin2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'ctx:top5:V01_mean_temp_C': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'ctx:top5:V07_total_ref_ET_mm_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'ctx:top5:era5l_d2m': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'ctx:top5:era5l_slhf_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'ctx:top5:sph_kgkg_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'deeprec_twsa_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'deeprec_twsa_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'deeprec_twsa_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'deeprec_twsa_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'deeprec_twsa_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'diurnal_temp_range_C_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'diurnal_temp_range_C_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'diurnal_temp_range_C_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'diurnal_temp_range_C_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'diurnal_temp_range_C_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'epo_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'epo_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'epo_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'epo_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'epo_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_d2m_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_d2m_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_d2m_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_d2m_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_d2m_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_pev_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_pev_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_pev_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_pev_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_pev_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_slhf_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_slhf_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_slhf_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_slhf_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_slhf_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_sro_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_sro_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_sro_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_sro_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_sro_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_sshf_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_sshf_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_sshf_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_sshf_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_sshf_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_ssr_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_ssr_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_ssr_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_ssr_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_ssr_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_ssro_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_ssro_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_ssro_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_ssro_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_ssro_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_stl1_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_stl1_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_stl1_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_stl1_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_stl1_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_str_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_str_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_str_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_str_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'era5l_str_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'gdd5_degC_days_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'gdd5_degC_days_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'gdd5_degC_days_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'gdd5_degC_days_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'gdd5_degC_days_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'grace_lwe_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'grace_lwe_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'grace_lwe_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'grace_lwe_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'grace_lwe_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'heatwave_days_gt35C_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'heatwave_days_gt35C_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'heatwave_days_gt35C_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'heatwave_days_gt35C_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'heatwave_days_gt35C_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'iod_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'iod_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'iod_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'iod_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'iod_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'months_since_sig_rain': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nao_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nao_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nao_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nao_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nao_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nino12_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nino12_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nino12_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nino12_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nino12_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nino34_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nino34_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nino34_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nino34_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nino34_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nino3_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nino3_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nino3_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nino3_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nino3_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nino4_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nino4_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nino4_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nino4_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'nino4_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'noi_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'noi_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'noi_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'noi_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'noi_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'oni_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'oni_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'oni_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'oni_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'oni_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'pdo_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'pdo_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'pdo_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'pdo_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'pdo_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'pna_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'pna_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'pna_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'pna_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'pna_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'precip_intensity_mm_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'precip_intensity_mm_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'precip_intensity_mm_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'precip_intensity_mm_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'precip_intensity_mm_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'precip_wytd': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'rmin_pct_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'rmin_pct_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'rmin_pct_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'rmin_pct_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'rmin_pct_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sam_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sam_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sam_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sam_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sam_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'soi_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'soi_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'soi_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'soi_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'soi_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'soil_water_tc_mm_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'soil_water_tc_mm_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'soil_water_tc_mm_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'soil_water_tc_mm_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'soil_water_tc_mm_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'soil_water_tc_mm_roll12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'soil_water_tc_mm_roll3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'soil_water_tc_mm_roll6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'soil_water_tc_mm_wytd': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'solar_radiation_Wm2_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'solar_radiation_Wm2_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'solar_radiation_Wm2_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'solar_radiation_Wm2_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'solar_radiation_Wm2_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sph_kgkg_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sph_kgkg_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sph_kgkg_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sph_kgkg_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sph_kgkg_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_01m_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_01m_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_01m_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_01m_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_01m_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_03m_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_03m_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_03m_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_03m_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_03m_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_06m_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_06m_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_06m_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_06m_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_06m_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_12m_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_12m_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_12m_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_12m_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_12m_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_24m_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_24m_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_24m_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_24m_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spi_24m_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_atl3_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_atl3_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_atl3_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_atl3_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_atl3_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_coral_sea_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_coral_sea_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_coral_sea_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_coral_sea_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_coral_sea_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_global_tropical_mean_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_global_tropical_mean_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_global_tropical_mean_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_global_tropical_mean_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_global_tropical_mean_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_iod_east_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_iod_east_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_iod_east_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_iod_east_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_iod_east_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_iod_west_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_iod_west_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_iod_west_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_iod_west_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_iod_west_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_nino34_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_nino34_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_nino34_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_nino34_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_nino34_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_subpolar_north_atlantic_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_subpolar_north_atlantic_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_subpolar_north_atlantic_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_subpolar_north_atlantic_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'sst_anom_subpolar_north_atlantic_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'tc_vapor_pressure_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'tc_vapor_pressure_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'tc_vapor_pressure_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'tc_vapor_pressure_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'tc_vapor_pressure_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'tna_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'tna_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'tna_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'tna_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'tna_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'tni_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'tni_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'tni_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'tni_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'tni_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'tsa_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'tsa_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'tsa_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'tsa_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'tsa_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'vpd_days_gt_2kpa_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'vpd_days_gt_2kpa_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'vpd_days_gt_2kpa_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'vpd_days_gt_2kpa_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'vpd_days_gt_2kpa_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'vpd_max_daily_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'vpd_max_daily_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'vpd_max_daily_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'vpd_max_daily_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'vpd_max_daily_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'vpd_warm_season_mean_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'vpd_warm_season_mean_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'vpd_warm_season_mean_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'vpd_warm_season_mean_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'vpd_warm_season_mean_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_mm_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_mm_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_mm_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_mm_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_mm_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_roll12_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_roll12_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_roll12_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_roll12_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_roll12_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_roll24_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_roll24_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_roll24_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_roll24_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_roll24_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_roll3_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_roll3_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_roll3_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_roll3_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_roll3_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_roll6_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_roll6_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_roll6_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_roll6_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wbal_roll6_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wet_day_count_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wet_day_count_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wet_day_count_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wet_day_count_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wet_day_count_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wp_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wp_lag12': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wp_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wp_lag3': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'wp_lag6': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
}
for _signoff_column, (_signoff_ruling, _signoff_date, _signoff_file) in SIGNOFF_COLUMNS.items():
    _signoff_facts = OUTPUTS[_signoff_column]
    _signoff_facts.update({'fact_status': 'assumed', 'reviewed_by': 'owner', 'date': _signoff_date})
    _signoff_facts['provenance'] = '; '.join(x for x in (_signoff_facts.get('provenance'), 'signed by the owner %s (ruling %s, %s, FREEZE_SIGNOFF_SHEET.md S5)' % (_signoff_date, _signoff_ruling, _signoff_file)) if x)
del _signoff_column, _signoff_ruling, _signoff_date, _signoff_file, _signoff_facts
# <<< SIGNOFF BLOCK <<<
