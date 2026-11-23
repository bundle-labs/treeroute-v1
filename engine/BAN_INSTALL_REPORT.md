# Ban install acceptance report (2026-10-05)

What this checks: the ban lists installed under ruling J (OWNER_RULINGS_2026-10-05.md, with the AMENDED J3) on the
four real packages: datasets/pm25, fire, defo and ndvi. Written by the acceptance agent. Nothing here is signed. I
marked no timing fact verified or signed. Where a ruling sets a bound, the fact says "assumed".

## 1. Short answer

- **Defo works end to end.** Its smoke finished (exit 0). derive_all on the real data matches every value in
  expected_derived.json that a unit sample can test.
- **PM2.5 and NDVI cannot run yet.** Both stop at R8 (G-LAG) on the first kept index column whose window is not
  signed (`ao`). Their smokes exit 4 with that message.
- **Fire cannot run yet, for two reasons.** Its static table (the key map `datasets/fire/data/static/part-0.parquet`)
  is not built, so its own target reader stops first (smoke exit 1, with a traceback). Behind that, R8 refuses the
  same unsigned index windows.
- **Livestock follows the amended J3 on all four.** The six aglw_* columns are 'watch', lagged one year by R8, never
  frozen, never banned. No package has a freeze column.
- **Full test suite, run once:** 3,034 passed, 17 failed, 62 xfailed, 4 skipped (31.8 min). All 17 failures are tests
  that still expect the state before the install. None is an engine fault (section 7).
- **Include hashes:** every `dataset.yaml` sha256 include matches its store catalog as it is now (all 8 packages
  load).
- **ATTENTION: your signatures are the blocker.** 13 index windows must be signed before PM2.5, fire (12 each) or
  NDVI (13, which is 78 columns with their lags) can run. Section 8 lists everything still unsigned.
- **PM2.5 derives the provisional values in its expected file** (Y0 2004, inner fit 2004-2016, h 156), with the
  unsigned windows held out (stand-in). One new flag: on a 24-group sample, R30 flags phenology_sos_doy (27.8% of
  its donor rows are missing; the threshold is 25%). The full 127-group derive must confirm it.
- **ATTENTION: fire's expected Y0 is out of date.** With phenology_sos_doy kept (J2 b), fire derives Y0 2004, not
  2003, exactly as PM2.5 does. Fire's expected_derived.json still says 2003. You still have to decide on phenology
  for both packages (section 9).

## 2. What I ran

| Step | How | Output |
|---|---|---|
| Full test suite, once | `py -3.9 -m pytest -q` from engine/, started 20:49:57. No engine, package or test file changed after that. | `acc_full_suite.log` in the acceptance folder below |
| Counts and R8 from the catalog facts (no data) | acc_facts.py over the 4 packages and their 4 drafts | `D:/treeroute/runs/_acceptance_ban_install_20261005/` |
| derive_all on the real stores (read-only) | acc_derive.py, then acc_compare.py against expected_derived.json | same folder: `<package>/summary.json`, `derived_*.json` (every entry, with inputs), `compare.json` |
| Smokes | `py -3.9 -m treeroute smoke datasets/<p>`, one at a time, with no other python job running | defo's run folder `D:\treeroute\runs\defo\smoke\20261005_9a9e4954`; `acc_smoke_<p>.log` in the acceptance folder |

How derive_all was run (acc_derive.py):

1. **The installed package first.** derive_all on `datasets/<p>` exactly as installed. If it refuses, the exact
   refusal is recorded.
2. **Then stand-ins, only where needed, on a scratch copy** (never in datasets/):
   - **S1:** every kept column that R8 refuses on its own is set 'conditional', as if left out until you sign its
     window. These columns are found from the catalog facts, not typed by hand.
   - **S0:** if the package's own static table is not built, the scratch copy borrows the draft package's table
     (`datasets/<p>_draft/data/static`).
3. **Labels are read twice, as the pipeline does.** The second pass withholds labels before Y0.
4. **Units are an evenly spaced stride** over each group's units with a valid label.

The D: disk was shared with another task's gate and census jobs from 21:34 onward. So I sampled groups for PM2.5 and
NDVI (24 and 26 groups) to finish in time. Defo and fire read every group. Values that depend on the sample are
marked "sample" in the tables.

## 3. Counts per package (as installed)

| | PM2.5 | Fire | Defo | NDVI |
|---|---|---|---|---|
| Verdicts (one per column: closed world) | 184 | 202 | 399 | 557 |
| keep | 102 | 110 | 250 | 465 |
| watch (kept, listed in every report) | 19 | 11 | 18 | 37 |
| **Kept in all** | **121** | **121** | **268** | **502** |
| of which tree features / router context | 119 / 2 | 119 / 2 | 268 / 0 | 493 / 9 |
| conditional (left out until its condition is met) | 22 | 16 | 33 | 0 |
| **Banned** | **41** | **65** | **98** | **55** |
| **Frozen** | **0** | **0** | **0** | **0** |
| **Lagged by R8 (lag above 0)** | **37** | **35** | **76** | **52** |
| at lag 0 (time-varying) | 51 | 53 | 172 | 352 |
| static (no lag) | 21 | 21 | 20 | 20 |
| **Refused by R8 today (unsigned window)** | **12** | **12** | **0** | **78** |
| Tree features that can enter today | 107 | 107 | 268 | 415 |

The lags R8 gives (from the facts; the same in the derive runs):

- **PM2.5:**
  - 1 month: burn_frac.
  - 2 months: nino*, the 8 sst_anom_*.
  - 3 months: oni, tni, deeprec_twsa.
  - 1 year: 20 annual columns, among them aglw_* (6), snow_duration_days, luh2_*, hdi, ntl, gdp_pc,
    population_density.
  - 2 years: phenology_sos_doy.
  - 0: the lag-12 columns, which already hold month t-12.
- **Fire:** as PM2.5, without burn_frac. Plus cloud_frequency_pct at 1 month, and phenology_sos_doy at 2 years.
- **Defo:** 76 columns at 1 year: aglw_* (6), the window-reaching aggregates (22 parents x mean/min/max), ntl,
  burn_doy_mean, burn_month_count, phenology_sos_doy. Everything else is at 0. This is exactly the 76-column list
  in defo's `j_state_2026_10_05` annotation.
- **NDVI:**
  - 1 month: 17 columns (burn_frac, cloud_frequency_pct, snow_cover_fraction and lag columns).
  - 2 months: 14 columns.
  - 3 months: 3 columns.
  - 1 year: 18 columns, aglw_* among them.

Ban reasons:

| | PM2.5 | Fire | Defo | NDVI |
|---|---|---|---|---|
| incomplete | 13 | 17 | 39 | 10 |
| trend_proxy | 10 | 13 | 24 | 11 |
| structural | 9 | 5 | 3 | 9 |
| post_window_snapshot | 8 | 8 | 8 | 8 |
| post_event_state | - | 9 | 4 | - |
| target_derived | - | 9 | 3 | 2 |
| coproduct | - | - | 11 | 13 |
| label | 1 | 4 | 2 | 1 |
| replaced_by_engine | - | - | 4 | 1 |

## 4. What changed from the draft packages

**PM2.5** (draft 178 verdicts and 93 tree features -> installed 184 and 119):

- **New:** 6 engineered lag-12 columns (J2 a). Five are keep; spei_24m_lag12 is watch.
- **ban -> keep:** snow_duration_days (J2 c).
- **ban -> watch:**
  - aglw_* (6), under amended J3;
  - phenology_sos_doy (J2 b).
- **conditional -> keep:** 12 index columns: ao, epo, iod, nao, noi, pdo, pna, sam, soi, tna, tsa, wp. All 12 are
  refused by R8 until their windows are signed.
- **keep -> watch:** burn_frac, burn_lag1, deeprec_twsa, luh2_urban, population_density, spi_24m.
- **Against the proposal:**
  - epo ban -> keep (J2 d);
  - aglw_*, deeprec_twsa and phenology_sos_doy ban -> watch;
  - plus the 6 lag-12 columns.

**Fire** (196 / 98 -> 202 / 119):

- **New:** 6 lag-12 columns. Four are keep; V06_spei_12m_lag12 and spei_24m_lag12 are watch.
- **ban -> keep:** phenology_sos_doy, snow_duration_days.
- **ban -> watch:** aglw_* (6).
- **conditional -> keep:** 11 index columns (as PM2.5, without epo). **conditional -> watch:** grace_lwe. All 12
  are refused by R8.
- **conditional -> ban:** 9 columns: agb_contrast, agb_lag1y, last_burn_month, lgt_density, lgt_is_zero,
  lgt_missing, vod_anom, vod_d1, vod_lag2.
- **keep -> ban:** aridity_index_p_pet, cropland_fraction, gdp_pc, population_density.
- **keep -> conditional:** snow_cover_fraction.
- **keep -> watch:** spi_12m, spi_24m.
- **Stays conditional:** epo. It is keep on PM2.5 and NDVI (section 9).

**Defo** (381 / 257 -> 399 / 268):

- **New:** 18 engineered lag-1 columns: the yearly spei/amo aggregates lagged one year (J2 a).
- **ban -> keep:** phenology_sos_doy, snow_duration_days.
- **ban -> watch:** aglw_* (6), through the co-measured fact (amended J3).
- **conditional -> ban:** epo_* and grace_lwe_* (6).
- **keep -> ban:** 15 columns: aridity_index_p_pet_*, eddi_*, esacci_sm_*, snow_cover_fraction_*, gdp_pc, lat, lon.
- **keep -> watch:** 12 static soil and terrain columns.
- **Against the proposal:** 15 columns go conditional -> keep in the same change as their J4 fact: V13_mean_lst_C_*,
  V20_burned_binary_*, burn_doy_mean, burn_month_count, cloud_frequency_pct_*, nighttime_lst_C_*, ntl.

**NDVI** (641 / 479 -> 557 / 493):

- **Removed:** 84 lag rows of banned bases (J4: features/build.py drops them).
- **ban -> keep:** the 6 lag-12 columns, snow_duration_days.
- **ban -> watch:** aglw_* (6).
- **conditional -> keep:** 66 columns (11 index columns and their lags, epo included). **conditional -> watch:** 12
  columns (grace_lwe, tsa and their lags). All 78 are refused by R8.
- **keep -> ban:** 17 columns: V20_burned_binary, aridity_index_p_pet, co2, cropland_fraction, eddi, eddi_observed,
  esacci_sm, the 6 food price columns, gdp_pc, population_density, scpdsi, sst_anom_mediterranean.
- **keep -> watch:** 19 columns (snow_cover_fraction, and spi_24m, sst_anom_atl3, sst_anom_coral_sea with their lags).
- **Still banned as a co-product:** phenology_sos_doy (J2 b).

## 5. Derived values against expected_derived.json

How to read the Result column:

- **match:** the derived value equals the expected value.
- **DIFFERS:** the value in the file is out of date or wrong.
- **sample:** the value depends on how many units or groups were read. Its rule value is given in the row next to it.
- **known reading:** the difference that expected_derived.json already notes itself. R14 lists the intercept among
  the unpenalised blocks; you rule on this reading.

R8 rows that match are folded into one line per table.

#### pm25 (S1 run)

| Value | Expected | Derived | Result |
|---|---|---|---|
| R1 cadence | ["regular", 1, "month"] | ["regular", 1, "month"] | match |
| R2 season key | ["month_of_year", 12] | ["month_of_year", 12] | match |
| R3-R7 y0 | 2004 | 2004 | match |
| R3-R7 y_end | 2023 | 2023 | match |
| R3-R7 test_years | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | match |
| R3-R7 train_end | 2019 | 2019 | match |
| R3-R7 inner_fit | [2004, 2016] | [2004, 2016] | match |
| R3-R7 inner_score | [2017, 2018, 2019] | [2017, 2018, 2019] | match |
| R4 set by (first pass) | - | ["phenology_sos_doy"] | info |
| R10 leads | [6, 12] | [6, 12] | match |
| R10 merged | {} | {} | match |
| R10 not_supplied | [] | [] | match |
| R10 contract_lead_zero | true | true | match |
| R12 router kind | "per_unit" | "per_unit" | match |
| R12 h = median valid rows per unit over the inner fit | 156 | 156 | match |
| LORO n_groups (derive_all's groups) | 127 | 24 | sample: 24 of the 127 groups read |
| Groups after the split (listing of the target store) | 127 | 127 | match |
| R13 decision surface | "inner_window" | "inner_window" | match |
| R14 kind | "per_unit" | "per_unit" | match |
| R14 columns | ["intercept", "normal", "context", "trees"] | ["intercept", "normal", "context", "trees"] | match |
| R14 unpenalised | ["normal"] | ["intercept", "normal"] | known reading: (expected file's own note): derive lists the intercept too |
| R14 centre | [0.5, 0.25] | [0.5, 0.25] | match |
| R14 grid points | 35 | 35 | match |
| R14 fit_row_cap | - | - | match |
| R22 links | ["identity", "log_c"] | ["identity", "log_c"] | match |
| R17 columns | 6 | 6 | match |
| R17 last values | 3 | 3 | match |
| R17 trailing steps | [12, 60] | [12, 60] | match |
| R17 all-history mean | true | true | match |
| R17 start offset | 0 | 0 | match |
| R18 bank per group | 100 | [40] | sample: capped at the 40 units read per group |
| R18 scored per group | 15 | [40] | sample: follows the capped bank |
| R18 rule: bank count (C7, before the cap) | 100 | 100 | match |
| R18 rule: scored budget per group before the event floor | 15 | 83 | sample: floor(20 x bank count / groups) over the groups read |
| R14 tree columns (bank trees) | 12700 | 2400 | sample: 24 groups x 100 trees; 127 groups give 12700 |
| R18 scored budget, the same rule over every group (arithmetic, not derived) | 15 | 15 | match |
| R9 freeze columns | {} | {} | match |
| R28 legal range | - | [0.0, "inf"] | info |
| R30 flags | none known | ["borderline:phenology_sos_doy", "flagged:phenology_sos_doy"] | NEW, sample: see the PM2.5 note below the tables |
| R8 co2 | 1 | - | not checked: NOT kept / not lagged in this run |
| R8 lags of the 32 columns the expected file names | as listed | same | match (all 32) |

#### fire (S1 run)

| Value | Expected | Derived | Result |
|---|---|---|---|
| R1 cadence | ["regular", 1, "month"] | ["regular", 1, "month"] | match |
| R2 season key | ["month_of_year", 12] | ["month_of_year", 12] | match |
| R3-R7 y0 | 2003 | 2004 | DIFFERS |
| R3-R7 y_end | 2022 | 2022 | match |
| R3-R7 test_years | [2019, 2020, 2021, 2022] | [2019, 2020, 2021, 2022] | match |
| R3-R7 train_end | 2018 | 2018 | match |
| R3-R7 inner_fit | [2003, 2015] | [2004, 2015] | DIFFERS |
| R3-R7 inner_score | [2016, 2017, 2018] | [2016, 2017, 2018] | match |
| R4 set by (first pass) | - | ["phenology_sos_doy"] | info |
| R10 leads | [6, 12] | [6, 12] | match |
| R10 merged | {} | {} | match |
| R10 not_supplied | [] | [] | match |
| R10 contract_lead_zero | true | true | match |
| R12 router kind | "per_unit" | "per_unit" | match |
| R12 h = median valid rows per unit over the inner fit | 156 | 144 | DIFFERS |
| LORO n_groups (derive_all's groups) | 40 | 40 | match |
| R13 decision surface | "inner_window" | "inner_window" | match |
| R14 kind | "per_unit" | "per_unit" | match |
| R14 columns | ["intercept", "normal", "context", "trees"] | ["intercept", "normal", "context", "trees"] | match |
| R14 unpenalised | ["normal"] | ["intercept", "normal"] | known reading: (expected file's own note): derive lists the intercept too |
| R14 centre | [0.5, 0.25] | [0.5, 0.25] | match |
| R14 grid points | 35 | 35 | match |
| R14 fit_row_cap | - | - | match |
| R22 links | ["identity", "log_c", "arcsine"] | ["identity", "log_c", "arcsine"] | match |
| R17 columns | 6 | 6 | match |
| R17 last values | 3 | 3 | match |
| R17 trailing steps | [12, 60] | [12, 60] | match |
| R17 all-history mean | true | true | match |
| R17 start offset | 1 | 1 | match |
| R18 bank per group | 100 | [100] | match |
| R18 scored per group | 50 | [50] | match |
| R18 rule: bank count (C7, before the cap) | 100 | 100 | match |
| R18 rule: scored budget per group before the event floor | 50 | 50 | match |
| R14 tree columns (bank trees) | 4000 | 4000 | match |
| R9 freeze columns | {} | {} | match |
| R28 legal range | - | [0.0, 1.0] | info |
| R30 flags | - | [] | info: (expected file lists the review sheet's day-1 flags, all banned) |
| R8 co2 | 1 | - | not checked: NOT kept / not lagged in this run |
| R8 lags of the 16 columns the expected file names | as listed | same | match (all 16) |

#### defo (installed run)

| Value | Expected | Derived | Result |
|---|---|---|---|
| R1 cadence | ["regular", 1, "year"] | ["regular", 1, "year"] | match |
| R2 season key | ["constant", 1] | ["constant", 1] | match |
| R3-R7 y0 | 2003 | 2003 | match |
| R3-R7 y_end | 2023 | 2023 | match |
| R3-R7 test_years | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | match |
| R3-R7 train_end | 2019 | 2019 | match |
| R3-R7 inner_fit | [2003, 2016] | [2003, 2016] | match |
| R3-R7 inner_score | [2017, 2018, 2019] | [2017, 2018, 2019] | match |
| R4 set by (first pass) | - | 94 items | info |
| R10 leads | [1] | [1] | match |
| R10 merged | {"1": [6, 12]} | {"1": [6, 12]} | match |
| R10 not_supplied | [] | [] | match |
| R10 contract_lead_zero | true | true | match |
| R12 router kind | "region" | "region" | match |
| R12 h = median valid rows per unit over the inner fit | 14 | 14 | match |
| LORO n_groups (derive_all's groups) | 42 | 42 | match |
| R13 decision surface | "inner_window" | "inner_window" | match |
| R14 kind | "region" | "region" | match |
| R14 columns | ["intercept", "normal", "trees"] | ["intercept", "normal", "trees"] | match |
| R14 unpenalised | ["normal"] | ["intercept", "normal"] | known reading: (expected file's own note): derive lists the intercept too |
| R14 centre | [100.0] | [100.0] | match |
| R14 grid points | 7 | 7 | match |
| R14 fit_row_cap | 60000 | 60000 | match |
| R22 links | ["identity", "log_c", "arcsine"] | ["identity", "log_c", "arcsine"] | match |
| R17 columns | 5 | 5 | match |
| R17 last values | 3 | 3 | match |
| R17 trailing steps | [1, 5] | [1, 5] | match |
| R17 all-history mean | true | true | match |
| R17 start offset | 0 | 0 | match |
| R18 bank per group | 4285 | [100] | sample: capped at the 100 units read per group |
| R18 scored per group | 2040 | [100] | sample: follows the capped bank |
| R18 rule: bank count (C7, before the cap) | 4285 | 4285 | match |
| R18 rule: scored budget per group before the event floor | 2040 | 2040 | match |
| R14 tree columns (bank trees) | 4200 | 4200 | match |
| R9 freeze columns | {} | {} | match |
| R28 legal range | - | [0.0, 1.0] | info |
| R30 flags | - | [] | info: (expected file lists the review sheet's day-1 flags, all banned) |

#### ndvi (S1 run)

| Value | Expected | Derived | Result |
|---|---|---|---|
| R1 cadence | ["regular", 1, "month"] | ["regular", 1, "month"] | match |
| R2 season key | ["month_of_year", 12] | ["month_of_year", 12] | match |
| R3-R7 y0 | 2003 | 2003 | match |
| R3-R7 y_end | 2023 | 2023 | match |
| R3-R7 test_years | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | match |
| R3-R7 train_end | 2019 | 2019 | match |
| R3-R7 inner_fit | [2003, 2016] | [2003, 2016] | match |
| R3-R7 inner_score | [2017, 2018, 2019] | [2017, 2018, 2019] | match |
| R4 set by (first pass) | - | 324 items | info |
| R10 leads | [6, 12] | [6, 12] | match |
| R10 merged | {} | {} | match |
| R10 not_supplied | [] | [] | match |
| R10 contract_lead_zero | true | true | match |
| R12 router kind | "per_unit" | "per_unit" | match |
| R12 h = median valid rows per unit over the inner fit | 168 | 168 | match |
| LORO n_groups (derive_all's groups) | 133 | 26 | sample: 26 of the 133 groups read |
| Groups after the split (listing of the target store) | 133 | 133 | match |
| R13 decision surface | "inner_window" | "inner_window" | match |
| R14 kind | "per_unit" | "per_unit" | match |
| R14 columns | ["intercept", "normal", "context", "trees"] | ["intercept", "normal", "context", "trees"] | match |
| R14 unpenalised | ["normal"] | ["intercept", "normal"] | known reading: (expected file's own note): derive lists the intercept too |
| R14 centre | [0.5, 0.25] | [0.5, 0.25] | match |
| R14 grid points | 35 | 35 | match |
| R14 fit_row_cap | - | - | match |
| R22 links | ["identity"] | ["identity"] | match |
| R17 columns | 6 | 6 | match |
| R17 last values | 3 | 3 | match |
| R17 trailing steps | [12, 60] | [12, 60] | match |
| R17 all-history mean | true | true | match |
| R17 start offset | 1 | 1 | match |
| R18 bank per group | 100 | [30] | sample: capped at the 30 units read per group |
| R18 scored per group | 15 | [30] | sample: follows the capped bank |
| R18 rule: bank count (C7, before the cap) | 100 | 100 | match |
| R18 rule: scored budget per group before the event floor | 15 | 76 | sample: floor(20 x bank count / groups) over the groups read |
| R14 tree columns (bank trees) | 13300 | 2600 | sample: 26 groups x 100 trees; 133 groups give 13300 |
| R18 scored budget, the same rule over every group (arithmetic, not derived) | 15 | 15 | match |
| R9 freeze columns | {} | {} | match |
| R28 legal range | - | [-0.2, 1.0] | info |
| R30 flags | - | [] | info: (expected file lists the review sheet's day-1 flags, all banned) |
| R8 co2 | 1 | - | not checked: NOT kept / not lagged in this run |
| R8 sst_anom_mediterranean | 2 | - | not checked: NOT kept / not lagged in this run |
| R8 lags of the 15 columns the expected file names | as listed | same | match (all 15) |

Notes on the derive runs:

- **Defo:** the installed package, read in full: all 42 groups, 100 units per group, 105,000 target rows. No
  stand-in. 268 tree features; no R9 entry and nothing frozen. The last-value rule fills nothing on defo, because
  its 2-month maximum is 0 annual steps. 200 s.
- **Fire:** the installed package refuses at R8 (G-LAG, ao). Its own target reader fails without the static table.
  - The values above come from S0 + S1 (12 columns), all 40 groups, 120 units per group, 1,209,600 rows,
    107 tree features.
  - Y0 2004 is set by phenology_sos_doy alone: the first driver year 2002, plus its 2-year lag.
  - The R8 lags are identical, column by column, to the fire fixer's run of 19:51. That run used the code before
    the R4 lag-operation change, so the change does not move fire.
  - The last-value rule filled 1,109 rows in 5 columns (most in spi_01m: 568). 58,212 rows in longer gaps go to R30.
  - 53 min on the busy disk.
- **NDVI:** the installed package refuses at R8 (G-LAG, ao).
  - The values above come from S0 + S1 (78 columns), 26 of the 133 groups, 30 units per group, 205,920 rows,
    415 tree features. The 26 groups are an evenly spaced stride over the names, plus greece_mainland and
    thar_desert, which split.yaml names.
  - Group-count values follow the sample. The same rules over 133 groups give 15 scored units per group and
    13,300 bank trees, as expected.
  - The last-value rule filled 8,156 rows in 21 columns; 6,216 of them are snow_cover_fraction. 953 rows in longer
    gaps go to R30.
  - co2 and sst_anom_mediterranean are banned, so their expected lags are not checked.
- **PM2.5:** the installed package refuses at R8 (G-LAG, ao).
  - The values above come from S0 + S1 (12 columns), 24 of the 127 groups (evenly spaced stride), 40 units per
    group, 253,440 rows, 107 tree features.
  - Y0 2004 is set by phenology_sos_doy alone (2002 plus its 2-year lag); inner fit 2004-2016 and h 156 follow. These
    equal the PROVISIONAL values in expected_derived.json.
  - Group-count values follow the sample. The same rules over 127 groups give 15 scored units per group and
    12,700 bank trees, as expected.
  - **New: R30 flags phenology_sos_doy** ('over_threshold', also 'borderline'). 27.8% of its donor rows are filled
    (the limit is 25%), and 25-29% of each test year's rows are missing. The expected file says 'none known' for
    R30. On fire (all 40 groups) R30 flags nothing. The share is near the limit and comes from a 24-group sample,
    so the full 127-group derive must confirm it.
  - The last-value rule filled 347 rows in 5 columns; 9,319 rows in longer gaps go to R30.
  - 19 min on the busy disk. A first run over all 127 groups was stopped after 47 min, still reading the panel.

## 6. Smoke outcomes (one at a time, no other python job running)

| Package | Exit | Time | Outcome |
|---|---|---|---|
| pm25 | 4 (refused) | 50 s | Census of the 4 smoke groups done (42,240 rows, 160 units), then: `treeroute smoke refused: TimingRefusal: [G-LAG] column ao: unknown window with no signed bound; the column is refused at lag 0 (R8) Fix: find the window, or sign a bound (align: unknown, max_length, fact_status: assumed)` |
| fire | 1 (traceback) | 5 s | `TargetReadError: the key map ...\engine\datasets\fire\data\static\part-0.parquet does not exist: run ingest/build_static.py on the package first`, raised by `datasets/fire/ingest/target_reader.py:116` during the census pick |
| defo | 0 (finished) | 51 s | Run folder `D:\treeroute\runs\defo\smoke\20261005_9a9e4954` (details below) |
| ndvi | 4 (refused) | 52 s | Census of the 4 smoke groups done, then the same G-LAG refusal on `ao` |

Defo smoke details (plumbing only; smoke deltas carry no sign information):

- **Size:** 4 groups (amazon_basin_brazil, andes_puna, angola_zambia_fire_belt, atlantic_forest_brazil), 40 units
  and 12 trees per group.
- **Pool:** 3,360 rows x 273 tree columns (268 features + 5 history).
- **Derived:** Y0 2003, test years 2020-2023, leads [1] (6 and 12 months merged), region router, links identity /
  log_c / arcsine.
- **Nowcast:** adopted arcsine_corrector_unweighted; verdict cannot_tell. **Lead 1:** guard passes; verdict
  does_not_help_equivalent.
- **Lead-0 contract:** held byte for byte.
- **Not headline-eligible:** the smoke kind, the R36 stand-in tolerance, and 7 declared departures.

Before the first smoke, the engine refused with `[G-DISK] stale heavy-job lock D:\treeroute\tmp\treeroute_heavy_job.lock
from dead pid 4904`. That lock was written at 16:19. Pid 4904 no longer existed, and no python process was running.
I copied the lock to the acceptance folder (acc_stale_heavy_job.lock.bak), then removed it, as the refusal's fix text says.
Every smoke after that released its own lock.

## 7. Full test suite (run once)

`3034 passed, 17 failed, 4 skipped, 62 xfailed in 1908.57s`. Each of the 17 failures expects the state before the
install, and each was already reported by a build task. The fix belongs to a test file, not to the engine:

| Test | Failures | Why it fails now |
|---|---|---|
| test_catalog_timing_facts.py (defo aggregates) | 4 | The shared seed catalog defo_annual_features_schema_catalog.yaml does not inherit J4 (V30 minimum -1e-12) or the deeprec reach. The test still expects 101 lag parents and the removed lag1_* rows. |
| test_derive_acceptance.py::test_derive_all_stops_at_the_closed_world | 4 | derive_all now gets past the closed world. Called without the feature script's outputs, it stops at R8: pm25 9, fire 8, defo 18, ndvi 388 columns without store facts. |
| test_packages_declarative.py::test_catalog_covers_the_review_sheet | 2 (fire, ndvi) | The package catalogs hold the lag-12 and lag rows, which the review sheet does not list. |
| test_pipeline_draft.py | 3 | Still coupled byte for byte to pm25 (spei_01m_lag12 KeyError; catalog.yaml differs). |
| test_pipeline_pm25.py::test_the_feature_script_makes_the_shipped_context_and_burn_lag1 | 1 | The expected outputs lack the 6 lag-12 columns. |
| test_timing_schema.py::test_timing_on_the_declared_packages | 3 (pm25, fire, ndvi) | It expects deeprec_twsa at lag 0. R8 now gives 3 (J2 b). |

## 8. What you still have to sign

None of these is signed. All store facts behind the kept columns are 'unverified' (PM2.5 114, fire 116, defo 263,
NDVI 477) or 'assumed' (PM2.5 7, fire 5, defo 5, NDVI 25). No fact is verified.

**A. Index windows: they block PM2.5, fire and NDVI today (G-LAG)**

- soi, tna, tsa, iod, ao, nao, pna, wp, sam: none written. {1, month, centred} is proposed.
- noi: J1 sets an assumed {3, month, centred} (lag 1), but it is not written in the store catalog.
- pdo: none written. {1, month, centred} with a 2-month reach is proposed.
- epo: no ruling. {1, month, centred} is proposed. It is kept on PM2.5 and NDVI; conditional on fire.
- grace_lwe (fire, NDVI): none written.
- Defo's 33 index aggregates stay conditional until these are signed.

Writing them is one shared catalog edit. All 8 dataset.yaml include hashes must be re-pinned in the same change.

**B. Bounds a ruling set, stored as 'assumed'**

- deeprec_twsa: reach 3 months (J2 b).
- phenology_sos_doy: window {1, year, centred} plus a 1-year reach (J2 b). This gives lag 2 years on the monthly
  targets and 1 year on defo.
- burn_frac (GFED): reach 1 month (J1).
- nitrogen_gkg: units cg/kg, range [0, 5000] (J4).
- V30_soil_moisture_pct: legal minimum -1e-12 (J4).
- tni: {7, month, centred}. Ruling R-B says "sign the bound", but the store still holds it as 'assumed'.
- co2: {3, month, centred} (R-C a). co2 is banned on all four packages now, so no run reads this fact.

**C. Facts behind a lag, 'unverified'**

- aglw_* (6): cadence 1 year, window {1, year, backward}. These give the 1-year lag on all four packages.
- co_measured_with_target:
  - answered 'true' on defo's 15 J4 columns and 6 aglw_*, and on 3 NDVI columns (cloud_frequency_pct,
    snow_cover_fraction, burn_frac);
  - on fire, one kept column carries 'true' (cloud_frequency_pct);
  - every other kept time-varying column has no answer (PM2.5: none at all). G-FACTS will block once it is built.
- The windows of defo's 18 lag-1 columns, and of the lag-12 columns on PM2.5, fire and NDVI. They are derived from
  their parents' facts.

**D. Engine readings (from the engine task)**

- J2 d last value:
  1. It works per gap: a gap longer than the maximum goes whole to R30.
  2. 2 months is rounded down to steps: monthly 2, composite 7, annual 0.
  3. Disclosure: a fill depends on whether a later value is present, never on its size. Near a cut, backtest and
     live use can differ.
  4. Constant C18.last_value_max_months = 2.
- J5 (R4):
  1. The latest store first year is used for every column.
  2. Store first years are measured on the target's rows.
  3. Whole years only.
  4. Only operations written as 'lag k=<k> unit=<unit>' are counted.

**E. Disclosures:** all 42 exceptions.yaml entries are UNSIGNED: PM2.5 11, fire 8, defo 6, NDVI 17.

## 9. Owner decisions still open (not timing facts)

1. **phenology_sos_doy on PM2.5 and fire.**
   - Kept (installed): Y0 2004, one training year less.
   - Conditional or banned: Y0 2003 (ruling F3).
   - Fire's expected_derived.json still says 2003, 2003-2015 and h 156. Derive gives 2004, 2004-2015 and h 144.
   - PM2.5's file already marks these values PROVISIONAL.
   - On PM2.5 the column is also near R30's missing-share limit (27.8% on a 24-group sample, limit 25%).
2. **aglw_* 2022-23 data:** those layers are the 2021 layer times INDIA's FAOSTAT ratios, for every region. The 2023
   test rows read the 2022 layer (PM2.5, defo, NDVI; fire never reads it). Options: rebuild with each country's
   ratio, carry 2021 forward, or keep and disclose (disclosed now, unsigned).
3. **epo differs by package:** keep on PM2.5 and NDVI, conditional on fire. All three wait for its window anyway.
4. **snow_cover_fraction on NDVI:** in 5 Arctic groups the polar-night gaps are longer than 2 months, so R30
   zero-fills February and March. Options: watch (installed), ban, or conditional.
5. **The other open questions from the package tasks:**
   - burn_lag1 on PM2.5 (duplicates month t-1);
   - wbal_roll12 / wbal_roll24 on fire (year-clock scores as high as spi_12m / spi_24m);
   - defo's eddi_observed annual aggregates are kept, although J2 d says eddi_observed stays banned;
   - defo's phenology at lag 1 vs 2.

## 10. Other things I noticed

- **Fire's missing static table exits 1 with a traceback.** The package's TargetReadError is not one of the
  engine's refusal types, so the CLI treats it as a bug (exit 1) rather than a refusal (exit 4 or 5). The message is
  loud and names the fix: run `ingest/build_static.py` on the package (fire's owner task). The PM2.5 and NDVI static
  tables (`data/static/part-0.parquet`) are not built either. Their target readers do not need them, so their smokes
  reached R8 first. I did not test where a later step would need them.
- **Plans saved before today will not match.** A derived.json written before the R4 lag-operation change will not
  match a new derive, so re-plan rather than resume (engine task's note).
- **Full-size derives are still to run.** Run them yourself when the disk is quiet, after the signatures:
  - PM2.5: all 127 groups;
  - NDVI: all 133 groups;
  - defo's R18 bank needs all 4,285 units per group.

  The commands are in the package tasks' reports. The scripts used here are in
  `D:/treeroute/runs/_acceptance_ban_install_20261005/`:
  - `acc_derive.py <engine> <out> <package> <units per group> [groups]`
  - `acc_compare.py`
  - `acc_tables.py`
