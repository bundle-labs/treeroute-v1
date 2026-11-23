"""The coral table columns: ONE list for the builder (build_tables.py) and the package draft files (make_draft.py).

Package-side, not engine code. Written 2026-10-19 for D:/treeroute/coral_build/SPEC_CORAL_TABLES.md section 3.
Each entry: name, role (SPEC_TABLE_MODE.md 1.3), family, verdict / reason / evidence (ban.yaml; schema
treeroute/package/schema.py:446-474), and provenance (source, window, computation, lead rule).

Words used in the provenance texts:
  T   the target date (the survey day; for a month-precision visit the month's last day)
  A   the feature anchor (= T; for a month-precision visit the month's FIRST day)
  L   the lead in days (0, 183, 365); the issue date is T - L
  C   the feature cut, C = A - L. Every data value used is dated strictly before C (C <= T - L, the issue date)
Verdict sources: CORAL_ENGINE_PLAN.md:153-176 (section C3, the science-rules review; unsigned until Q9/Q10/Q22 are
answered), OWNER_RULINGS_2026-09-28.md:24-25 (R-A, R-B), OWNER_RULINGS_2026-10-06.md:37 (N2), :41 (S29).
"""

SST_SRC = ("CoralTemp daily SST per site, D:/coral/drivers/sst_compact_all.npz (members uk/start/end/day/sst, read by "
           "byte-offset memory map, npz_map.py; site key coral_safe.site_key at 4 decimals)")
MMM_TXT = ("MMM(C) = coral_dhw_model.mmm_from (coral_dhw_model.py:69-93) on the SST values before C: per calendar "
           "month a linear trend of the monthly means, read at epoch 1988.2857; the largest month; needs 365 values "
           "and 10 distinct years")
CUT_TXT = "every SST value used is dated strictly before C = A - L (coral_forecast.py:110: searchsorted 'left')"
WINDOWS = (30, 56, 84, 90, 180, 365)
C3 = "CORAL_ENGINE_PLAN.md:157 (C3: relative to the leak-free MMM; windows end before the cut); unsigned (Q22)"

COLUMNS = []


def _add(name, role, family, verdict=None, reason=None, evidence=None, provenance=None, **extra):
    COLUMNS.append(dict(name=name, role=role, family=family, verdict=verdict, reason=reason, evidence=evidence,
                        provenance=provenance, **extra))


# ---- keys (never a feature; no verdict: SPEC_TABLE_MODE.md 1.3-1.4)
_add("row_id", "key_row", "key", provenance="'<unit_id>|<T as YYYY-MM-DD>'; the same id is the same visit in every lead file")
_add("unit_id", "key_unit", "key", provenance="'<GCBD ecoregion id, 3 digits>_<lat>_<lon>' with lat/lon at 4 decimals from coral_safe.site_key (coral_safe.py:97-107)")
_add("group", "key_group", "key", provenance="ecoregion NAME from GCBD Ecoregion_Name_LUT (Site_Info_tbl.Ecoregion_Name is its integer key)")
_add("lat", "key_lat", "key", provenance="site latitude rebuilt from the 4-decimal site key (EPSG:4326)")
_add("lon", "key_lon", "key", provenance="site longitude rebuilt from the 4-decimal site key (EPSG:4326)")
_add("target_date", "key_time", "key", calendar_part="date",
     provenance="T: GCBD Sample_Event_tbl Date_Year/Month/Day (not events_dated.date, which clamps the day at 28, "
                "CORAL_STATE.md:148-151); month-precision visits (Donner or Safaie with day 15, CORAL_DATA_AUDIT.md:65-69) "
                "take the month's last day")
_add("issue_date", "key_issue", "key", provenance="T - L days, exactly (T-ISSUE)")
_add("feature_end", "key_feature_end", "key",
     provenance="the last content day any feature window of the row may read at this lead (a window bound computed "
                "before any data is read, P24): the largest of the SST window end (C - g - 1), the cyclone window "
                "end (C - g - 1) and each index month's last content day (month end + reach: +2 months nino34a, "
                "+1 month dmi). g = --sst-gap-days (default 1; UTC source days vs local survey dates). Always "
                "before the issue date (T-FEATEND); build_tables.py asserts every value read is on or before it")
_add("mark", "key_mark", "key", provenance="'train' when T is before 1 January of the first test year; 'test' inside the test years "
                                          "(package parameter, default 2016-2019); later visits are not written")

# ---- target
_add("pct_bleached", "target", "target", "ban", "label",
     "the target: forced ban as a feature | APP_PLAN.md 1.4 (the target and its twins are forced to ban); "
     "coral_smoke_regress.py:56-77",
     "percent of coral bleached per visit: Reef_Check Population rows (level 1) -> mean of S1..S4; AGRRA, FRRP, "
     "McClanahan, Donner -> Percent_Bleached; Kumagai and Safaie excluded (ordinal only); mean per Sample_ID, then "
     "mean over the Sample_IDs of one visit (unit, T); rows outside [0, 100] dropped (coral_smoke_regress.py:65-76)")

# ---- report stratum
_add("programme", "report_stratum", "stratum", "ban", "structural",
     "report only: the survey programme fixes the protocol and the label scale (CORAL_STATE.md:30-34: "
     "programme mix drives pooled scores); pipeline/data.py strata read the role whatever "
     "the verdict",
     "GCBD Data_Source_LUT via Site_Info_tbl.Data_Source; 'mixed' when one visit merges Sample_IDs of two programmes")

# ---- router context (ruling H3: read at the issue step; here at C, which equals the issue date on day-precision rows)
_add("ctx_month", "router_context", "context", "keep",
     "router context only (a calendar column is allowed only here, G-KEYS); legacy context",
     "coral_forecast.py:228 (ctxc = month, doy_sin, doy_cos, abslat); ruling H3 (OWNER_RULINGS_2026-09-28.md:96)",
     "calendar month of C (H3: the issue step; legacy read the TRUE date, coral_forecast.py:121)")
_add("ctx_doy_sin", "router_context", "context", "keep",
     "router context only (G-KEYS); legacy context", "coral_forecast.py:122, 228; ruling H3",
     "sin(2 pi dayofyear(C) / 365.25)")
_add("ctx_doy_cos", "router_context", "context", "keep",
     "router context only (G-KEYS); legacy context", "coral_forecast.py:123, 228; ruling H3",
     "cos(2 pi dayofyear(C) / 365.25)")
_add("ctx_abslat", "router_context", "context", "keep",
     "router context only; banned as a tree column (location fingerprint, Part 415)",
     "CORAL_ENGINE_PLAN.md:172 (C3: abslat, mmm ban as tree columns, keep as penalised router context); coral_forecast.py:120, 228",
     "|lat| of the site (static, a physical location)")
_add("ctx_mmm", "router_context", "context", "keep",
     "router context only; an absolute temperature, banned from the trees; in context it is a DISCLOSED departure "
     "from the absolute-temperature ban (owner item)",
     "CORAL_ENGINE_PLAN.md:172 (C3) and :267 (Q22 a); legacy used MMM_i - mean(MMM_pool) unpenalised (coral_glorys2_ab.py:100-102)",
     MMM_TXT + "; " + CUT_TXT)

# ---- SST heat, 30 columns (coral_forecast.py:124-134); mean_w / std_w are NOT written (absolute temperature, Part 415)
for w in WINDOWS:
    last = "the last %d daily SST values before C; hs = SST - MMM(C)" % w
    _add("dhw_%d" % w, "engineered", "sst_heat", "keep", "heat stress relative to the leak-free MMM", C3,
         SST_SRC + "; " + last + "; sum of hs over days with hs >= 1, divided by 7")
    _add("hs_max_%d" % w, "engineered", "sst_heat", "keep", "heat stress relative to the leak-free MMM", C3,
         SST_SRC + "; " + last + "; max(hs)")
    _add("n_above_mmm_%d" % w, "engineered", "sst_heat", "keep", "heat stress relative to the leak-free MMM", C3,
         SST_SRC + "; " + last + "; count of hs > 0")
    _add("n_above_mmm1_%d" % w, "engineered", "sst_heat", "keep", "heat stress relative to the leak-free MMM", C3,
         SST_SRC + "; " + last + "; count of hs >= 1")
    _add("cool_%d" % w, "engineered", "sst_heat", "keep", "cool relief relative to the leak-free MMM", C3,
         SST_SRC + "; " + last + "; sum of max(-hs, 0), divided by 7")

# ---- heat history, 7 columns (coral_forecast.py:135-147)
H = SST_SRC + "; hs_all = every SST value before C minus MMM(C); "
_add("days_since_max_hs", "engineered", "sst_history", "keep", "short window, not a level",
     "CORAL_ENGINE_PLAN.md:158 (C3)", H + "days from the max of the last 365 hs values to the last value (coral_forecast.py:135-136)")
_add("slope_90", "engineered", "sst_history", "keep", "short window; a slope is not a level",
     "CORAL_ENGINE_PLAN.md:158 (C3)", H + "least-squares slope of the last 90 SST values (np.polyfit; 0 under 90 values; coral_forecast.py:137-138)")
ROLL = "rolling 84-value sums of hs (hs >= 1 only) / 7 over the whole record before C (coral_forecast.py:139-145); "
_add("lifetime_dhw", "engineered", "sst_history", "ban", "trend_proxy",
     "a running total since 1985 grows with the year (pooled r with year 0.83-0.93); CORAL_ENGINE_PLAN.md:161 (C3), :255 (Q10 b)",
     H + "sum of gated hs over the whole record / 7 (coral_forecast.py:142)")
_add("n_dhw_ge4_before", "engineered", "sst_history", "ban", "trend_proxy",
     "running count since 1985; CORAL_ENGINE_PLAN.md:161 (C3), :255 (Q10 b)", H + ROLL + "count of sums >= 4")
_add("max_dhw_before", "engineered", "sst_history", "ban", "trend_proxy",
     "running max since 1985; CORAL_ENGINE_PLAN.md:161 (C3), :255 (Q10 b)", H + ROLL + "max of the sums (0 when none)")
_add("n_dhw_ge8_before", "engineered", "sst_history", "watch",
     "same family as the banned running totals, weaker; listed in reports",
     "CORAL_ENGINE_PLAN.md:162 (C3), :255 (Q10 b)", H + ROLL + "count of sums >= 8")
_add("days_since_dhw4", "engineered", "sst_history", "watch",
     "fixed declared cap 3,650 instead of the 99999 code (CORAL_DATA_AUDIT.md:243); its observable maximum grows "
     "with the record length (a partial clock)", "CORAL_ENGINE_PLAN.md:163 (C3), :267 (Q22 a)",
     H + ROLL + "values since the last sum >= 4, capped at 3650; 3650 when none (legacy wrote 99999, coral_forecast.py:146-147)")

# ---- Hobday marine heatwave, 10 columns (coral_forecast.py:149-175; coral_mhw_features.py:74-107)
HB = (SST_SRC + "; day-of-year p90 threshold from the SST values before C (11-day window, >= 20 values; "
      "coral_mhw_features.py:74-95); over the last 365 values before C: exceedance = SST > threshold; ")
HBK = "the one confirmed driver win; relative to the site's own prior climate"
HBE = "CORAL_ENGINE_PLAN.md:159 (C3)"
_add("mhw_days_365", "engineered", "mhw", "keep", HBK, HBE, HB + "count of exceedance days")
_add("mhw_days_90", "engineered", "mhw", "keep", HBK, HBE, HB + "count in the last 90 values")
_add("mhw_days_30", "engineered", "mhw", "keep", HBK, HBE, HB + "count in the last 30 values")
_add("mhw_icum_90", "engineered", "mhw", "keep", HBK, HBE, HB + "sum of (SST - threshold) on exceedance days of the last 90 values / 7")
_add("mhw_imax_90", "engineered", "mhw", "keep", HBK, HBE, HB + "max of (SST - threshold) on exceedance days of the last 90 values")
_add("mhw_nev_365", "engineered", "mhw", "keep", HBK, HBE, HB + "number of runs of >= 5 exceedance days (coral_mhw_features.py:98-107)")
_add("mhw_durmax_365", "engineered", "mhw", "keep", HBK, HBE, HB + "longest such run")
_add("mhw_since_end", "engineered", "mhw", "keep", HBK + "; declared cap 365", HBE,
     HB + "values since the last run ended; 365 when none (a declared cap, not a fill code)")
_add("mhw_cat_max_90", "engineered", "mhw", "keep", HBK, HBE,
     HB + "max over the last 90 values of (SST - threshold) / (threshold - MMM(C)), gap > 0.05 only")
_add("mhw_thr_gap", "engineered", "mhw", "watch", "quasi-static site climate; listed in reports",
     "CORAL_ENGINE_PLAN.md:160 (C3, Q22)", HB + "median of (threshold - MMM(C)) where > 0.05")

# ---- cyclones, 16 columns (coral_extra_drivers.py:70-122), every window [C - d, C)
CY = ("IBTrACS v04r01 track points, D:/coral/drivers/static/IBTrACS.ALL.v04r01.nc (lat, lon, time, usa_wind); "
      "points whose day is in [C - %d, C); great-circle km (R = 6371)")
CYK = "dated tracks; windows end before the cut; fixed caps, no fill codes"
CYE = "CORAL_ENGINE_PLAN.md:166 (C3)"
for d in (30, 90, 365):
    _add("cyc_mindist_%d" % d, "engineered", "cyclone", "keep", CYK, CYE,
         (CY % d) + "; nearest point distance, capped at 9999 km; 9999 when no point (legacy wrote 9999 only when the "
                    "window was empty and could exceed it otherwise)")
    for rad in (200, 500):
        _add("cyc_maxw_%d_%d" % (rad, d), "engineered", "cyclone", "keep", CYK, CYE,
             (CY % d) + "; max usa_wind (knots, missing = 0) of points within %d km; 0 when none" % rad)
        _add("cyc_n_%d_%d" % (rad, d), "engineered", "cyclone", "keep", CYK, CYE,
             (CY % d) + "; count of points within %d km" % rad)
_add("cyc_days_since_close", "engineered", "cyclone", "keep", CYK + "; declared cap 3650", CYE,
     (CY % 3650) + "; C minus the day of the last point within 200 km; 3650 when none")

# ---- ENSO anomaly, 3 columns: REPLACE the banned absolute nino34_lag0/3/6 (coral_forecast.py:186-194)
EN = ("Nino-3.4 monthly SST, D:/coral/drivers/climate/nina34.txt (ERSST V6, ABSOLUTE values, PSL format, read by "
      "coral_extra_drivers.psl_index, :46-67); anomaly = value minus that calendar month's 1951-1980 mean (a fixed base "
      "that ends before every visit, the first visit being 1994); month = the month %d months before C's month: the "
      "content reach of +2 months (ruling R-A) then ends before C's month starts")
ENK = ("replaces the absolute Nino-3.4 (banned structural: an absolute temperature carrying the season, "
       "CORAL_ENGINE_PLAN.md:164); reach +2 months per ruling R-A, assumed to hold for ERSST V6")
for k in (3, 6, 9):
    _add("nino34a_lag%d" % k, "engineered", "enso", "keep", ENK,
         "OWNER_RULINGS_2026-09-28.md:24 (R-A a); CORAL_ENGINE_PLAN.md:164, :267 (Q22 a)", EN % k)

# ---- IOD, 3 columns (coral_forecast.py:186-194 read the cut month itself: lag 0 looked ahead, L8)
DM = ("Dipole Mode Index monthly anomaly, D:/coral/drivers/climate/dmi.txt (HadISST1.1, PSL format, -9999 = missing); "
      "month = the month %d months before C's month: under the proposed bound {3, month, centred} (reach +1 month) "
      "its content ends before C's month starts")
for k in (2, 5, 8):
    _add("dmi_lag%d" % k, "engineered", "iod", "conditional",
         "out of every run until the owner signs the window bound {3, month, centred} (R8 refuses an unknown window; "
         "precedent R-B signed tni's bound)",
         "CORAL_ENGINE_PLAN.md:165 (C3), :267 (Q22 a); OWNER_RULINGS_2026-09-28.md:25 (R-B)", DM % k)

# Columns of the legacy 77 frame that are NOT written, and why (they cannot be vouched or are banned; U2 covers
# every written column, so a column whose timing cannot be vouched is not written at all):
NOT_WRITTEN = {
    "month, doy_sin, doy_cos (as tree columns)": "moved to router context (G-KEYS; ruling H3); CORAL_ENGINE_PLAN.md:168",
    "nino34_lag0, nino34_lag3, nino34_lag6": "absolute temperature (ban structural) and lag 0 reads the cut month "
                                             "(coral_forecast.py:186-194; L8); replaced by nino34a_lag3/6/9",
    "dmi_lag0, dmi_lag3, dmi_lag6": "lag 0 reads the cut month (look-ahead); replaced by dmi_lag2/5/8",
    "mask_is_water, mask_land_frac_7x7": "static geography as a main effect from a data-product mask (CRW ct5km "
                                         "climatology v3.1), not a physical map under N2; ban (CORAL_ENGINE_PLAN.md:167)",
    "pop_ratio_5_50, pop_grad_5_25, pop_growth_20y": "GHS-POP R2023A: every epoch is rescaled to UN WPP 2022 and WUP 2018 "
                                                     "and disaggregated with GHS-BUILT-V R2023A (Sentinel-2 2018); content "
                                                     "dated after every cut (GHSL_Data_Package_2023.pdf pp. 46-47; ruling N2; "
                                                     "precedent S29)",
    "mean_<w>, std_<w>, mmm_n_years, pop levels, lat, lon (as features)": "outside the 77 frame: absolute temperature, "
                                                                          "year clock, location (Part 415; CORAL_ENGINE_PLAN.md:170-173)",
}


def tree_columns():
    return [c["name"] for c in COLUMNS if c["role"] == "engineered"]


def context_columns():
    return [c["name"] for c in COLUMNS if c["role"] == "router_context"]


def written_columns():
    return [c["name"] for c in COLUMNS]
