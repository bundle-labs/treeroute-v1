# SPEC: the coral table builder and the coral package draft

Written 2026-10-19 under owner ruling U (engine/OWNER_RULINGS_2026-10-06.md:84-95). Package side only: nothing here
is engine code. The table contract is D:\treeroute\coral_build\SPEC_TABLE_MODE.md (called "SPEC" below).
Paths: builder `D:\treeroute\coral_build\coral_tables\`, working tables `D:\treeroute\coral_build\coral_data\`,
published full tables `D:\treeroute\coral_build\coral_store\` (section 4.1), package draft
`D:\treeroute\coral_build\engine\datasets\coral_draft\`. "Project root" = `C:\Users\<user>\Desktop\data set for
reserch paper\` (read only). All counts come from stage 1 (`coral_tables/build_visits.py`), run today in 7 seconds;
its output is `coral_data/visits_census.json`. Revised the same day after three skeptic reviews; the REVIEW LOG is at
the end.

**ATTENTION (read first)**
- **Stage 1 is built and run. Stage 2 (the feature tables) is designed here, not built.** The full stage-2 build is
  an owner command (about 25-35 minutes, section 4.3).
- **Order (ruling U6).** The full stage-2 build, the full coral smoke and any coral run wait until the engine's
  table option has passed its tests, the no-op proof and the install. Stage 1 and the draft are preparation only.
  The tiny build and tiny smoke may run on the build copy as an engine acceptance test, smoke-watermarked, no score
  reported (P26).
- **The test window 2016-2019 is set by leaving the 38 visits of 2020 out.** With them, signed R3 gives 2017-2020.
  So P1 is a departure from R3 (CORAL_ENGINE_PLAN.md Q6 c, unanswered). It must be signed, or Q6 answered, before
  any full coral smoke or run. 2017-2020 is the declared sensitivity row.
- **One more key column:** `feature_end` (role `key_feature_end`), the last content day any feature window of the
  row may read at that lead. The engine refuses a row whose feature_end is not before its issue date (SPEC 2.1
  T-FEATEND). 85 columns in all.
- **SST and cyclone windows end one day earlier by default** (`--sst-gap-days 1`): source days are UTC, survey
  dates are local (P17).
- **11 ecoregions are excluded in split.yaml only because the engine's built defaults would refuse them** (SPEC 7:
  O13 zero rows at a bank cut, O14 one site). They hold 35 test and 9 train visits. If the owner picks the O13/O14
  alternatives, the list empties with no rebuild.
- **Four 77-frame column families are NOT written**, because U2 makes the owner vouch for every written column:
  the GHS-POP shape columns (every R2023A epoch carries 2018-2022 content, GHSL_Data_Package_2023.pdf pp. 46-47),
  the CRW mask pair, the absolute Nino-3.4 and every lag-0 index column. Replacements: a Nino-3.4 anomaly at lags
  3/6/9 months and DMI at lags 2/5/8 months (DMI stays `conditional` until the owner signs its window bound).
- **Test window 2016-2019 holds 2,312 visits in 37 groups** after the exclusions: Reef_Check 1,932, FRRP 190,
  McClanahan 189, AGRRA 1, Donner 0. Pooled scores will mostly measure Reef_Check.
- **The draft does not load on today's engine.** It needs the table option (SPEC 1.1-1.3).

---

## 1. ROWS

### 1.1 Sources and recipe

| Item | Rule | Source |
|---|---|---|
| Label source | GCBD SQLite, opened read-only (`?mode=ro`) | D:/coral/target/raw/gcbd/Global_Coral_Bleaching_Database_SQLite_11_24_21.db |
| Label recipe | Reef_Check Population rows (Bleaching_Level 1): mean of S1-S4. AGRRA, FRRP, McClanahan, Donner: Percent_Bleached. Kumagai and Safaie excluded (ordinal only). Mean per Sample_ID. Rows outside [0, 100] dropped, not clipped | project root coral_smoke_regress.py:56-77 (reused unchanged in build_visits.py `label_per_sample`) |
| Keys | lat, lon from Site_Info_tbl; ecoregion id from Site_Info_tbl.Ecoregion_Name; date from Sample_Event_tbl Date_Year/Month/Day | same SQLite |
| Cross-check | D:/coral/target/events_dated.parquet, joined on Sample_ID: 0 mismatches in lat, lon, ecoregion, year, month, day; 2 labelled samples absent from it | build_visits.py `cross_check` |
| Not used | events_dated `date` (clamps the day at 28, 1,324 events; CORAL_STATE.md:148-151); gcbd_bleaching_joined.parquet (no site, no date) | |

Counts: 34,846 bleaching rows; 20,244 labelled samples (Reef_Check 11,297, Donner 3,488, AGRRA 2,847, FRRP 2,394,
McClanahan 218); 0 out of range; 12 samples average more than one label row; 0 samples lack an ecoregion.

### 1.2 Visit, site, group

- **Site (package unit).** `coral_safe.site_key(lat, lon)` at 4 decimals: one int64, about 11 m
  (project root coral_safe.py:97-107). It is the key the SST compact uses. unit_id = `<ecoregion id, 3 digits>_<lat>_<lon>`,
  with lat/lon rebuilt from the key, so every visit of a site has the same coordinates. No site key falls in two
  ecoregions (measured).
- **Visit (sample row).** (unit, target date T). Samples at one visit are averaged (CORAL_ENGINE_PLAN.md:252, Q7 a).
  Merges: 3,080 visits merge 2 or more samples (5,405 samples absorbed); 1,282 of them disagree on the label;
  5 merge two programmes. 14,839 visits in all.
- **row_id** = `<unit_id>|<T as YYYY-MM-DD>`. Unique by construction (T-ROWID, T-UNITTIME).
- **Group** = ecoregion NAME from Ecoregion_Name_LUT (117 names; Site_Info_tbl.Ecoregion_Name is its integer key).
  This is the legacy join: coral_smoke_regress.py:58-64 joins Site_Info_tbl, and events_dated.eco holds the same
  integer (0 mismatches). Names may hold commas; the builder refuses an id that is missing from the LUT.
- **Target** = pct_bleached, legal range [0, 100] (catalog.yaml target facts).
- **Stratum** = programme (Reef_Check, FRRP, McClanahan, AGRRA, Donner; `mixed` for the 5 merged visits).

### 1.3 Date precision

- Day precision: T = the survey day; feature anchor A = T.
- **Month precision** = a Donner or Safaie sample whose day is 15 (the day was imputed and cannot be recovered;
  CORAL_DATA_AUDIT.md:65-69). Then **T = the month's last day** and **A = the month's first day**.
  - T at the month end keeps every label-side use safe: the label is surely known after T, so pools ("dated strictly
    before the issue date"), bank cuts and marks never see it early.
  - A at the month start keeps every feature-side use safe: at lead L every feature ends before C = A - L, so no
    post-survey heat enters, and C is never later than the issue date T - L.
  - A visit that merges both kinds (5 visits) takes month precision.
- **2,128 visits** have month precision. All are train rows, dated 1994-2011. None is in the inner-score years
  2013-2015 or on any guard surface, so none is ever SCORED; the row's own pool horizon (issue date = month end - L)
  therefore never matters. List: `coral_data/month_precision_rows.csv` (row_id, group, programme, T, A, mark, sids).
- Known side effect (disclosed in exceptions.yaml): their season context is read at C = A - L, a month start minus L,
  so ctx_doy_sin / ctx_doy_cos take only 12 values on these rows. The router context can tell them apart, and they are
  mostly one programme (Donner). They enter pools and scalers as candidates. The run counts, per pass, the pools that
  hold a month-precision row (from `pools_<pass>.parquet`, SPEC 3.8 step 9).

### 1.4 Which visits become samples

A visit is a sample (a row of lead_0) when all hold:
1. its target date is before the end of the test window (38 visits of 2020 are not written: "later visits unused").
   This rule sets R3's Y_end, so it is a departure from R3 that needs a signature (P1, ATTENTION);
2. its site has a CoralTemp series (1,006 visits on 576 sites have none: 747 train, 259 test, 40 ecoregions);
3. at the nowcast, at least 1,825 SST values and 10 distinct years lie before A (coral_forecast.py:106-116,
   coral_dhw_model.py:69-78). 101 more visits fail this (10 of them test).

Result: **13,694 samples in 94 groups**, first year 1994. A sample that fails rule 3 at lead L is absent from that
lead's file (SPEC 1.6): 8 train visits of 1994 at leads 183 and 365. Stage 2 applies the MMM's full rule (a month
with 60 values over 3 years) and drops and logs any extra row.

---

## 2. SPLIT

### 2.1 Rule

- Test window: **2016-2019 by default**, the stage-1 parameter `--test-years 2016-2019` (the owner may change it).
- mark = `train` when T < 1 January of the first test year; `test` when T is inside the test years. Visits after the
  window are not written, so R3 events (the last year with any valid row; derive/rules.py:620-622) gives Y_end = 2019
  and R5 (rules.py:785-834) gives exactly 2016-2019. The marks equal the derived window (T-MARK, SPEC O1). T-MARK
  then matches a window the package chose by leaving rows out, not one R3 derived from all the data. So this window
  is recorded as a departure from R3 (Q6 c) that the owner signs before any coral run (P1). On all the data R3 gives
  2017-2020; that window is the declared sensitivity row (stage 1 with `--test-years 2017-2020`, 2020 rows written).
- Scored rows: every test-marked visit (ruling U1: the package marks train and test). R18(2)'s stride pick over
  candidate units is not used. Most test sites have no label by the train end, so they would never be R18
  candidates (feasibility review recount: 783 of 1,262 kept test sites). Disclosed in exceptions.yaml and the
  pre-registration.
- Derived windows (R4-R7): Y0 1994, inner fit 1994-2012, inner score 2013-2015, train end 2015, test 2016-2019.
- The six bank cuts (R11 events, SPEC 2.2): lead 0 fit 2015-12-31 and inner 2012-12-31; lead 183 fit 2015-07-02 and
  guard 2012-07-02; lead 365 fit 2015-01-01 and guard 2012-01-02.
- R12: the median valid rows per candidate site, Y0 to the inner-fit end, is **h = 1.0**, so the neighbour kind
  (router_rules.py:149-196).

### 2.2 Counts (lead 0)

| | Before split.yaml (94 groups) | After split.yaml (83 groups) |
|---|---|---|
| Train rows / groups / sites | 11,347 / 91 / 7,356 | 11,338 / 83 / 7,348 |
| Train by programme | Reef_Check 6,383, FRRP 2,185, Donner 2,123, AGRRA 651, mixed 5 | Reef_Check 6,381, FRRP 2,185, Donner 2,116, AGRRA 651, mixed 5 |
| Test rows / groups / sites | 2,347 / 41 / 1,280 | 2,312 / 37 / 1,262 |
| Test by programme | Reef_Check 1,957, McClanahan 199, FRRP 190, AGRRA 1 | Reef_Check 1,932, FRRP 190, McClanahan 189, AGRRA 1 |
| Inner-score rows (2013-2015) | | 2,046 in 33 groups |
| Zero share of the label | train 40.2%, test 55.1% | |

Overlap blocks (computed with the build engine's `split.derive_overlap_blocks`, spacing rule, read only): 83 groups
form 78 blocks; 5 blocks hold 2 groups (Eastern coast South Africa + South Mozambique coast; Gulf of Aden + South Red
Sea; Mayotte and Comoros + North Madagascar; Moreton Bay + Southern Great Barrier Reef; Strait of Malacca + West
Sumatra).

### 2.3 Groups with 0 train rows at a bank cut (engine owner item O13)

| Group | Before the inner cut (2012-12-31) | Before the fit cut (2015-12-31) | Test rows |
|---|---:|---:|---:|
| Gulf of Guinea to Sierra Leone | 0 | 0 | 18 |
| Kimberley Coast, north-west Australia | 0 | 0 | 10 |
| North-west Arabian Sea (also one site) | 0 | 0 | 1 |
| Birds Head Peninsula, Papua | 0 | 1 | 6 |

The same four have 0 rows at the lead-183 and lead-365 guard cuts; the first three also at both lead fit cuts.
One-site groups (engine owner item O14): Ashmore Reef, Gulf of California, Houtman Abrolhos Islands, Line Islands,
North-west Arabian Sea, Pompey and Swain Reefs, South China Sea, Southern Seychelles (all train-only except
North-west Arabian Sea). All 11 are in split.yaml `excluded` with the reason (section 6). Among the 83 kept groups
the smallest count at any cut is 1 row (bags of 30 with replacement still work, fit/bank.py:198-206); 46 groups
hold under 30 rows at the inner cut.

---

## 3. FEATURES

### 3.1 Words and the one timing rule

- T target date; A feature anchor (= T, or the month's first day); L lead in days; issue date = T - L.
- **C = A - L, the feature cut. Every data value used is dated strictly before C.** C equals the issue date on every
  day-precision row (every test row) and is up to 30 days earlier on month-precision rows.
- **Day convention gap g** (`--sst-gap-days`, default 1): CoralTemp SST days and IBTrACS track times are UTC; survey
  dates are local. In the west Pacific, UTC day C - 1 runs to about midday local on day C. So the SST windows end
  before C - g, and the cyclone windows are [C - g - d, C - g). The index lags are counted in whole months before C's
  month and are not affected. g = 0 is the legacy setting (P17).
- **feature_end** (key column, role `key_feature_end`): per row and lead, the last content day any of the row's
  windows may read: the largest of the SST window end (C - g - 1), the cyclone window end (C - g - 1) and each index
  month's last content day (month end + reach). It is a window bound, computed before any data is read (P24). It is
  always before the issue date; the engine refuses a row where it is not (SPEC 2.1 T-FEATEND).
- Router context is read at C (ruling H3: context at the issue step; OWNER_RULINGS_2026-09-28.md:96).
- No feature reads any label. No column is computed from a label.
- Missing values are written as NaN. No imputation (the legacy donor-median fill, coral_final_benchmark.py:122-125,
  used donor rows of all dates: leak L10). The engine 0-fills tree NaN (R30) and leaves context NaN to G1/S1.

### 3.2 The column set (85 columns; the one list is `coral_tables/columns.py`)

Keys (9): row_id, unit_id, group, lat, lon, target_date, issue_date, feature_end, mark. Target: pct_bleached. Stratum:
programme. (columns.py today holds 84 columns; it gains `feature_end` before stage 2 is built, section 8.)
The SST and cyclone windows below end at C - g (3.1); "before C" in the table means "before C - g" for those families.

| Family | Columns | n | Verdict | Source on D:/coral | Window and computation at lead L | Legacy code reused |
|---|---|---:|---|---|---|---|
| Context: season | ctx_month, ctx_doy_sin, ctx_doy_cos | 3 | keep (context) | none (calendar) | month and day of year of C (H3) | coral_forecast.py:121-123 read the TRUE date; moved to C |
| Context: latitude | ctx_abslat | 1 | keep (context) | site key | abs(lat) | coral_forecast.py:120 |
| Context: MMM | ctx_mmm | 1 | keep (context), disclosed departure | drivers/sst_compact_all.npz | `mmm_from` on SST before C: per calendar month, a linear trend of monthly means read at epoch 1988.2857; the largest month; needs 365 values, 10 years | coral_dhw_model.py:69-93 |
| SST heat | dhw_w, hs_max_w, n_above_mmm_w, n_above_mmm1_w, cool_w for w = 30, 56, 84, 90, 180, 365 | 30 | keep | sst_compact_all.npz | last w daily values before C; hs = SST - MMM(C); dhw = sum(hs, hs >= 1)/7; cool = sum(max(-hs, 0))/7 | coral_forecast.py:124-134 (mean_w, std_w not written) |
| Heat history | days_since_max_hs, slope_90 | 2 | keep | same | last 365 hs; slope of the last 90 SST values | coral_forecast.py:135-138 |
| Heat totals | lifetime_dhw, n_dhw_ge4_before, max_dhw_before | 3 | ban trend_proxy | same | rolling 84-value DHW over the whole record before C | coral_forecast.py:139-145 |
| Heat totals | n_dhw_ge8_before | 1 | watch | same | count of rolling DHW >= 8 | coral_forecast.py:144 |
| Heat totals | days_since_dhw4 | 1 | watch | same | values since the last rolling DHW >= 4, **capped at 3650** (3650 when none) | coral_forecast.py:146-147 wrote 99999 |
| Marine heatwave | mhw_days_30/90/365, mhw_icum_90, mhw_imax_90, mhw_nev_365, mhw_durmax_365, mhw_since_end (cap 365), mhw_cat_max_90 | 9 | keep | same | day-of-year p90 from SST before C (11-day window); exceedance over the last 365 values before C; runs of >= 5 days; NaN when under 60 thresholded days | coral_forecast.py:149-175; coral_mhw_features.py:68-107 |
| Marine heatwave | mhw_thr_gap | 1 | watch | same | median of (threshold - MMM(C)) where > 0.05 | coral_forecast.py:170-175 |
| Cyclones | cyc_mindist_d, cyc_maxw_{200,500}_d, cyc_n_{200,500}_d for d = 30, 90, 365; cyc_days_since_close | 16 | keep | drivers/static/IBTrACS.ALL.v04r01.nc | track points whose day is in [C - d, C); great-circle km; mindist **capped at 9999** (9999 when none); days since the last point within 200 km in [C - 3650, C), 3650 when none | coral_extra_drivers.py:39-44, 70-122 |
| ENSO | nino34a_lag3, nino34a_lag6, nino34a_lag9 | 3 | keep | drivers/climate/nina34.txt (ERSST V6, absolute) | anomaly = value minus that calendar month's 1951-1980 mean; month = C's month minus 3, 6, 9: with R-A's +2-month reach the content ends before C's month starts | psl_index, coral_extra_drivers.py:46-67 |
| IOD | dmi_lag2, dmi_lag5, dmi_lag8 | 3 | conditional | drivers/climate/dmi.txt (HadISST1.1 anomaly) | month = C's month minus 2, 5, 8: under the proposed bound {3, month, centred} (+1 month) the content ends before C's month starts. The file names no anomaly base period (its footer: "using SST anomaly ...", no period). Before P14 is signed, the PSL base period is recorded; if it ends after 2012 (the earliest guard cut year), the anomaly is rebuilt in the package from a fixed base before 1994, as for ENSO | psl_index |

Tree columns written: 69. Entering the trees: 63 (60 keep + 3 watch); 66 once the DMI bound is signed. Context: 5.
CORAL_ENGINE_PLAN.md:176 expected 66-73.

### 3.3 Not written (77-frame columns) and why

U2 makes the owner vouch for every written column, so a column whose timing cannot be vouched is not written.

| Columns | Why | Evidence |
|---|---|---|
| month, doy_sin, doy_cos as tree columns | key-derived; router context only (G-KEYS, H3) | CORAL_ENGINE_PLAN.md:168 |
| nino34_lag0/3/6 | absolute temperature carrying the season (ban structural); lag 0 reads the cut month (L8) | CORAL_ENGINE_PLAN.md:164; coral_forecast.py:186-194 |
| dmi_lag0/3/6 | lag 0 reads the cut month | coral_forecast.py:186-194 |
| mask_is_water, mask_land_frac_7x7 | static geography from a data-product mask, not a physical map (N2) | CORAL_ENGINE_PLAN.md:167; coral_extra_drivers.py:125-147 |
| pop_ratio_5_50, pop_grad_5_25, pop_growth_20y | **checked today: fails the content-date rule.** Every R2023A epoch (1990-2020) is rescaled to UN WPP 2022 and WUP 2018 and disaggregated with GHS-BUILT-V R2023A (Sentinel-2 2018 composite); census inputs GPWv4.11. Content is dated 2018-2022, after every cut (fit cut 2015-12-31). The legacy builder also read the NEXT epoch by interpolation (L9) | D:/coral/drivers/ghspop/GHS_POP_E2015.zip: GHSL_Data_Package_2023.pdf pp. 46-47; coral_ghspop_ab.py:76-95; ruling N2 (OWNER_RULINGS_2026-10-06.md:37); precedent S29 (GRIP4 road density banned) |
| mean_w, std_w (12), mmm_n_years, pop levels, lat, lon | absolute temperature, year clock (r = 1.000), location | CORAL_ENGINE_PLAN.md:170-173 |

### 3.4 Leaks fixed, and how the builder proves its timing

| Legacy leak | Where | Fix in this builder |
|---|---|---|
| Part 458: time-blind transductive pool (other test rows' labels, any date) | coral_glorys2_ab.py:93; CORAL_EXPERIMENTS.md:3734-3757 | No pool in the package. The engine's strict pool (U4: train rows dated strictly before the issue date) uses the table's issue_date. No feature reads a label |
| C1: forecast pool cut at the target date | adaptation.py:2020, 2042 | Same: the pool is the engine's; issue_date = T - L is written on every row and checked (T-ISSUE) |
| Date clamp at day 28 | events_dated.date; coral_forecast.py:94 | dates from GCBD Date_* |
| Imputed day 15 | CORAL_DATA_AUDIT.md:65-69 | month precision (1.3) |
| L8: ENSO lag 0 reads the survey month | coral_forecast.py:186-194 | lags counted back from C's month past the content reach |
| L9: GHS-POP next epoch; POP at the true year at leads | coral_ghspop_ab.py:87-95; adaptation.py:1836 | not written (3.3) |
| L10: imputation medians over all dates | coral_final_benchmark.py:122-125 | NaN, no imputation |
| 99999 code survives isfinite | coral_forecast.py:147; CORAL_DATA_AUDIT.md:243 | fixed cap 3650 |

Proof the builder leaves (stage 2; written to build_manifest.json):
1. **Asserts per row and lead.** The last SST day used < C - g; every cyclone point used < C - g; for each index
   month m, the last content day (month end of m + reach) < C; every value's source day <= feature_end < issue date.
   A breach stops the build.
2. **Largest "source day minus issue day"** per family and lead (always below 0), like the engine's pool log (SPEC 2.3).
3. **Look-ahead canary.** A stride sample of rows per lead (every 50th row; every row in tiny mode) is rebuilt from
   sources physically truncated at C - g for SST and IBTrACS (slice cut, points filtered) and at C for the index
   tables. Every value must be equal in bytes. The canary cannot catch a provider base period that uses later years
   (DMI, 3.2); that is checked by recording the base period.
4. **Replay check.** On visits with one Sample_ID, day precision and day <= 28, the ported columns at lead 0 and lead
   365 must equal project root forecast_features_L0.parquet / _L365.parquet (matched on Sample_ID; relative
   tolerance 1e-9): the 30 SST heat, 7 history (days_since_dhw4 compared after the cap), 10 Hobday, 16 cyclone
   (cyc_mindist after the cap) columns, ctx_mmm = mmm, ctx_abslat = abslat, and at lead 0 the 3 season columns.
   ENSO and DMI are redefined and not compared. The replay rows are computed a second time with g = 0 (the legacy
   setting) by the same functions; only that copy is compared, and it is never written to a lead file. A mismatch
   stops the build and names the column.

---

## 4. ONE TABLE PER LEAD

### 4.1 Files and layout

`coral_data/<build>/lead_0.parquet`, `lead_183.parquet`, `lead_365.parquet` (SPEC 1.2). Same 85 columns in each, in
columns.py order. Rows sorted by row_id. dtypes: strings for row_id, unit_id, group, mark, programme; float64 for lat,
lon, the label, every feature and context column (counts cast to float64); date32 for target_date, issue_date and
feature_end. issue_date = target_date - L days. A lead-L file holds the samples present at L (SPEC 1.6).
Publishing: the builder writes only under `coral_data/`. When a full build has passed its proofs, `build_tables.py
--publish full` copies the three lead files and build_manifest.json to `coral_store/<build stamp>/` (content
SHA-256 checked after the copy) and never writes there again. coral_draft's dataset.yaml points at that folder, and
the owner adds `D:/treeroute/coral_build/coral_store` to protected_roots.txt (SPEC 1.2). The tiny build stays in
`coral_data/tiny/` (smoke only, not protected).
Side files (not read by the engine): `rows_audit.parquet` (row_id, sids, n_samples, label min/max, date precision,
anchor, SST counts per lead), `dropped_rows.csv` (every visit not written, with its reason), `build_manifest.json`
(inputs with size, mtime and SHA-256; code SHA-256 of columns.py, build_visits.py, build_tables.py, npz_map.py and the
legacy modules imported; parameters; counts; the 3.4 proof), `build.log`.

### 4.2 Expected rows

| Build | lead 0 | lead 183 | lead 365 |
|---|---:|---:|---:|
| full (94 groups written) | 13,694 (11,347 train, 2,347 test) | 13,686 | 13,686 |
| full after split.yaml (83 groups) | 13,650 (11,338 / 2,312) | 13,642 | 13,642 |
| tiny (4 groups) | 897 (629 / 268) | 897 | 897 |

Each file is about 5 MB. Stage 2 may drop a few more rows (MMM per-month rule); each is logged.

### 4.3 Runtime

- Stage 1: 7 seconds (measured today).
- Stage 2 full: about 25-35 minutes (estimate). Basis: the legacy builder took 8.6-10.0 minutes per lead for 21,430
  rows (project root CORAL_FORECAST.log:25, 47, 69), mostly the per-row Hobday percentiles; here 13,694 rows x 3 leads,
  plus about 2 minutes of canary and replay. **Owner command** (over the agents' 30-minute limit):

```
cd D:\treeroute\coral_build\coral_tables
py -3.9 -u build_tables.py --build full
py -3.9 -u build_tables.py --publish full
```

  Run only after the engine install (ruling U6, ATTENTION).

- Stage 2 tiny: about 2-3 minutes (897 rows x 3 leads, 384 sites, every row canaried).
- Resume: each lead file is written to a temp name and renamed when complete. A rerun skips a lead whose file and
  manifest entry match the current inputs, code and parameters, and rebuilds otherwise. Nothing is deleted; a stale
  file is moved to `coral_data/_moved/<stamp>/`.

### 4.4 RAM and the SST read

- First lines: `sys.path` gets the project root; `from coral_safe import cap_threads, guard, site_key`; `cap_threads(4)`
  before numpy; `guard(2.5)` every 200 visits and before each lead file is assembled (coral_safe.py:29-79).
- Site keys are int64 (`site_key`), never strings.
- **D:/coral/drivers/sst_full_merged.parquet and sst_compact.npz are never opened.** Only sst_compact_all.npz.
- Its members are STORED (zip type 0, measured today), so `npz_map.member_map` memory-maps uk, start, end, day and sst
  at their byte offsets (np.load would read all 889 MB; the legacy builder did, coral_forecast.py:87-88).
- **Only the needed sites and dates are read.** Visits are processed site by site in uk order (the file order, so the
  disk head moves forward). For each needed site the builder reads `day[start : start + n]` and `sst[start : start + n]`,
  where n = the number of days before that site's latest C. Tiny mode reads 384 site slices; full mode 8,157 of the
  10,254 series.
- Per site all its visits and all three leads are computed from that one slice.
- IBTrACS: lat, lon, time, usa_wind read once (about 80-100 MB), sorted by day; per row a searchsorted window.
- Peak RAM estimate: under 1 GB (slices of about 0.1 MB, IBTrACS, the row table of about 30 MB). Free RAM today
  was 4.4 of 16.9 GB with other programs open; guard() aborts cleanly at 2.5 GB free.

---

## 5. TINY MODE AND THE FULL BUILD

- `--groups "<a>;<b>;..."` (semicolon-separated, since names hold commas) builds only those ecoregions. Unknown names
  are refused.
- **Default tiny groups** (rule: the 4 smallest groups by rows that have h < 2, at least 40 sites, at least 40 train
  rows at every one of the 6 bank cuts, at least 15 inner-score rows and at least 40 test rows):
  Andaman Sea (199 rows, 63 test), Maldive Islands (182, 81), Moreton Bay, eastern Australia (246, 75), North and
  central Red Sea (270, 49). 897 rows, 268 test, 190 inner-score rows, 384 sites. Each is its own overlap block.
  Programmes: Reef_Check 863, Donner 31, McClanahan 3. With exactly 4 groups the R21 smoke takes all of them.
  (Moreton Bay shares a block with Southern Great Barrier Reef in the full build, not in tiny.)
- The tiny build also writes a smoke package: `coral_data/tiny/package/`, a copy of coral_draft whose dataset.yaml
  points at `coral_data/tiny/lead_{lead}.parquet` and whose split.yaml has no exclusion and lists the 4 groups as
  seen_during_design. Smoke command (after the table option exists):

```
cd D:\treeroute\coral_build\engine
py -3.9 -m treeroute smoke D:\treeroute\coral_build\coral_data\tiny\package
```

- Full build (owner, after the install): `py -3.9 -u build_tables.py --build full`, then `--publish full` (section
  4.3). It writes `coral_data/full/`, then the published copy `coral_store/<build stamp>/`, which coral_draft's
  dataset.yaml points at.
- The tiny smoke is an engine acceptance test on the build copy (P26): smoke-watermarked, no score is reported or
  used for any choice.
- To change the test window: rerun stage 1 with `--test-years`, then stage 2. To change exclusions: edit split.yaml
  only (no rebuild).

---

## 6. THE PACKAGE DRAFT (engine\datasets\coral_draft\)

| File | Content | Status |
|---|---|---|
| dataset.yaml | `input: table`; `stores.target: 'D:/treeroute/coral_build/coral_store/<build stamp>/lead_{lead}.parquet'` (written today with `coral_data/full/`; repointed at the published copy, 4.1); `includes: []` | written; to repoint |
| catalog.yaml | 85 columns: the 9 key roles (key_row, key_unit, key_group, key_lat, key_lon, key_time with calendar_part date, key_issue, key_feature_end, key_mark); target facts (legal_range [0, 100] with its source, window 1 day backward, stamp event_date); per column a provenance text (source, window, computation, lead rule) | generated by coral_tables/make_draft.py from columns.py; regenerated once columns.py has feature_end |
| ban.yaml | 76 verdicts: keep 65 (60 tree + 5 context), watch 3, conditional 3 (dmi), ban 5 (label 1, structural 1 = programme, trend_proxy 3); the header lists the 77-frame columns not written | generated |
| split.yaml | excluded: the 11 groups of 2.3 with reasons (owner items); seen_during_design: the other 83 (all were legacy donor or test ecoregions) | written |
| exceptions.yaml | disclosed defects (month precision, date clamp, merges, 2 mislocated sites, visits without SST); provenance flags (programme confound, IBTrACS best track, ENSO anomaly built in-package, DMI bound and base, CoralTemp reach, MMM in context); test exposure. To add: survey-triggered sampling (surveys are often made because of bleaching, so a row's existence carries outcome information and every forecast is conditional on a survey happening; coral_forecast.py:31-35; scores are also reported within each programme, per_stratum.csv); month-precision rows' 12-valued season context (1.3); the UTC day convention and the gap g (3.1); scored rows = every test visit (U1, not R18(2); 2.1); the event cut day (SPEC O27) | written; five items to add |
| AUDIT_CHECKLIST.md | 10 human checks and the owner's U2 timing statement with its open timing facts | written |
| ingest/README.md | short README (in ingest/ because the loader refuses unknown top-level files, package/load.py:4, 183) | written |

Checked today against the build engine's schema (treeroute/package/schema.py): ban.yaml, split.yaml and
exceptions.yaml validate; catalog.yaml validates except the new key roles (expected until SPEC 1.3 is built; it gains key_feature_end when regenerated);
dataset.yaml needs `input` (SPEC 1.1). No expected_derived.json (drafts carry none, tests/test_pipeline_draft.py:59).
Values it would hold: R1 irregular, R2 event month, R3 2019, R4 1994, R5 2016-2019, R7 inner fit 1994-2012 and score
2013-2015, R10 183/365, R12 neighbour (h = 1.0), 83 groups, 37 groups with test rows, 33 with inner-score rows.

---

## 7. OWNER ITEMS (package-level choices; the default used)

| # | Choice | Default (built or drafted) | Alternative |
|---|---|---|---|
| P1 | Test window (a departure from signed R3 = CORAL_ENGINE_PLAN Q6 c; **sign before any full coral smoke or run**) | 2016-2019 (stage-1 parameter); the 38 visits of 2020 not written, so R3/R5 derive this window | R3 on all the data: 2017-2020 (2020 rows written); Q6 a (new generic rule A18). The window not chosen is the declared sensitivity row (CORAL_ENGINE_PLAN.md:251) |
| P2 | Repeat surveys at one site and date | averaged into one visit (Q7 a) | site + depth or reef id as the unit (unverified that it resolves them) |
| P3 | Imputed day 15 | month precision: T = month end, features before the month start (Q20 a) | drop the 2,128 visits (all train, mostly Donner) |
| P4 | Site rounding | 4 decimals (coral_safe.site_key, about 11 m) | coarser, for example 0.01 degree, which would merge nearby transects into one site |
| P5 | Group ids | ecoregion names (Q21 a) | numeric ids |
| P6 | The 11 groups the engine defaults refuse | excluded in split.yaml (35 test, 9 train visits) | owner picks O13 / O14 alternatives in the engine; the list empties |
| P7 | Visits without SST or with short history | not written (1,107 visits, 269 of them test) | write them with NaN features (trees would 0-fill every SST column) |
| P8 | MMM | router context, disclosed departure (C3, Q22 a) | drop ctx_mmm |
| P9 | Season context | at C, the issue date (H3, Q11 a) | the true date (a departure from H3) |
| P10 | ctx_month | kept as a numeric context column (legacy) | doy_sin / doy_cos only |
| P11 | Heat totals | lifetime_dhw, n_dhw_ge4_before, max_dhw_before ban trend_proxy; n_dhw_ge8_before watch (Q10 b) | all watch; or all four banned |
| P12 | Caps | days_since_dhw4 3650; cyc_days_since_close 3650; cyc_mindist 9999 km (now also clips far storms); mhw_since_end 365 | 1.1 x the observed max (CORAL_STATE.md, data-dependent) |
| P13 | ENSO | anomaly from nina34.txt (ERSST V6), fixed 1951-1980 base, lags 3/6/9 by R-A's reach assumed for V6 | the PSL nina34.anom file of the grid packages (not on disk; download by the owner) |
| P14 | DMI | conditional until the bound {3, month, centred} is signed AND the PSL anomaly base period is recorded (3.2); lags 2/5/8 | ban; sign another bound; rebuild the anomaly from a fixed pre-1994 base |
| P15 | CRW mask pair | not written (ban) | keep with a written exception and content date |
| P16 | GHS-POP shape columns | not written: content dated 2018-2022 (N2) | a disclosed exception (would break U2's statement 1) |
| P17 | Day convention and CoralTemp reach | gap g = 1 day for SST and cyclones (`--sst-gap-days 1`): UTC source days vs local survey dates (3.1), until the owner signs a CoralTemp reach (CORAL_ENGINE_PLAN Q22) | g = 0 (legacy; U2 statement 1 then reads "content dated before C in UTC days"); a larger g |
| P18 | Two mislocated sites | not patched, disclosed | flip site A's latitude sign; drop site B |
| P19 | Tiny groups | Andaman Sea, Maldive Islands, Moreton Bay, North and central Red Sea | any 3-4 groups passing the gates |
| P20 | Report stratum | programme only (also gives within-programme scores, the survey-programme confound check) | add "site visited before". Date precision is not useful: every month-precision row is a train row, so test rows hold one value |
| P21 | Missing marine-heatwave values (under 60 thresholded days) | NaN (engine 0-fills, R30 counts) | donor-median fill (legacy; leak L10) |
| P22 | seen_during_design | all 83 kept groups | a narrower list from the saved prediction files |
| P23 | Engine item O13 for coral | the 4 groups of 2.3 (Gulf of Guinea, Kimberley Coast, North-west Arabian Sea, Birds Head) | O13 alternative keeps their 35 test rows scored |
| P24 | feature_end | the window bound per row and lead (3.1), computed before any data is read | the newest source day actually read per row |
| P25 | Where the engine reads the full tables | a published copy `coral_store/<build stamp>/`, protected; the builder never writes there again (4.1) | read `coral_data/full/` (the builder's working folder) |
| P26 | Tiny coral smoke before the engine install | allowed on the build copy as an engine acceptance test, smoke-watermarked, no score reported or used (U6 orders the coral tables after the install) | wait for the install |

---

## 8. Status of the builder files (coral_tables\)

| File | Status |
|---|---|
| npz_map.py | built: read-only memory map of a STORED .npz member |
| build_visits.py | built and run (stage 1): visits.parquet, month_precision_rows.csv, visits_census.json |
| columns.py | built: the one column list (84 columns, verdicts, provenance); **to add** the key column `feature_end` (role key_feature_end), 85 columns |
| make_draft.py | built and run: catalog.yaml and ban.yaml; to rerun after columns.py gains feature_end |
| build_tables.py | **to build** (stage 2, sections 3-5): imports thresholds / events / doy_of (coral_mhw_features.py:68-107) and psl_index / hav (coral_extra_drivers.py:39-67) from the project root (read only; both modules import only numpy, pandas and coral_safe); copies mmm_from verbatim with its origin (coral_dhw_model.py:69-93), because that module imports sklearn and coral_smoke_rf at load; ports the loops of coral_forecast.py:105-175 and coral_extra_drivers.py:70-122 with C (and the gap g) in place of the event date; writes feature_end; `--publish` copies a finished full build to coral_store (4.1) |

---

## REVIEW LOG (2026-10-19)

GS = grid-safety review, LK = leakage review, FS = feasibility review. Engine-side issues are logged in
SPEC_TABLE_MODE.md and SPEC_NEIGHBOUR.md; this log covers the package side.

| Issue | Outcome | Where / reason |
|---|---|---|
| LK2 / FS5 feature dates never checked by the engine | fixed | new key column `feature_end` (3.1, 3.2, 4.1, 6, P24); the builder asserts it (3.4 proof 1); the engine refuses a late one (SPEC T-FEATEND) |
| LK7 DMI anomaly base period unverified | fixed | 3.2 IOD row and P14: record the PSL base period before signing; rebuild from a fixed pre-1994 base if it ends after 2012; 3.4 notes the canary cannot catch it. Checked: D:/coral/drivers/climate/dmi.txt names no base period |
| LK8 UTC source days vs local survey dates | fixed | 3.1 gap g, default 1 day for SST and cyclones; P17 default changed; replay check uses g = 0 on a side copy only (3.4) |
| LK9 month-precision rows' season context | fixed in part | disclosed (1.3, exceptions.yaml) and counted from the saved pools. Rejected part: a date-precision report stratum, because every month-precision row is a train row and is never scored (P20). Reading their context at mid-month minus L would also give 12 values, so it would not fix the discreteness |
| LK11 survey-triggered sampling not disclosed | fixed | exceptions.yaml flag (6) citing coral_forecast.py:31-35; within-programme scores through the programme stratum (P20) |
| LK12 window set by leaving rows out | fixed | 1.4 rule 1, 2.1 and P1: recorded as a departure from R3 (Q6 c) to sign before any full coral smoke or run; 2017-2020 is the declared sensitivity row. The default rows are kept because stage 1 is built on them; counts for 2017-2020 come from a stage-1 rerun |
| FS10 scored rows replace R18(2) | fixed | 2.1 note and exceptions.yaml cite U1 |
| FS11 "available" vs content date | fixed | 3.1 states content dates and the UTC convention; SPEC 1.7 item 1 is a content date; IBTrACS best track and CoralTemp reach stay disclosed (6) |
| FS15 protected root is the builder's own folder | fixed | 4.1 `--publish` to `coral_store/<build stamp>/`; dataset.yaml repointed (6); P25 |
| FS18 nothing gates the rest after U6 | fixed | ATTENTION order line; 4.3 and 5 run the full build only after the install; P26 for the tiny smoke |

Counts for this file: 10 issues fixed (one in part: LK9, whose stratum part is rejected with its reason), 0 rejected
outright.
