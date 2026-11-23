# Q34 ban-list review: the agent's recommendations (merged), 2026-10-05

**Status: PROPOSAL, NOT SIGNED.** You asked the agent to make the ban list with its recommendations and to report them. This is that
list. No package file was changed: every `ban.yaml`, `catalog.yaml` and store catalog still carries its Sep 28-Oct 4
date. Each package got a first-pass proposal, then an independent skeptic check. Every high- and medium-severity
skeptic finding is merged into the files below. The low ones are listed at the end.

| Package | Row-by-row sheet (reason, evidence, timing fact, question) | Ready-to-copy ban list |
|---|---|---|
| PM2.5 | `pm25_columns_proposed.csv` | `pm25_ban_proposed.yaml` |
| Fire | `fire_columns_proposed.csv` | `fire_ban_proposed.yaml` |
| Defo | `defo_columns_proposed.csv` | `defo_ban_proposed.yaml` (adopt it together with the catalog cleanup, see Defo) |
| NDVI | `ndvi_columns_proposed.csv` | `ndvi_ban_proposed.yaml` |

**Validation.** Each YAML was copied into a scratch package under `D:/treeroute/ban_review/merge_2026-10-05/scratch/`
and checked there: the `BanFile` schema, `load_package`, and `package_spec` / `apply_verdicts`. The last one is the
closed-world check (every column has exactly one verdict) and the forced ban on the target and its twins. All four
passed. The un-merged first-pass files are kept in `.../merge_2026-10-05/originals/`. The new lags quoted below were
recomputed with the engine's own `lag_trace`.

**How to read the verdicts.**
- **keep** and **watch** go into the trees. A watch column is also named in every report.
- **conditional** stays out of the headline run until the named condition is met.
- **ban** always gives one reason word from the engine's list.
- There is no "lag" verdict. The engine works out each lag (rule R8) from the timing facts you sign.
- There are no **freeze** verdicts. The 14 FREEZE columns are banned as `post_window_snapshot` (ruling A3).

---

## 1. PM2.5

**Counts (178 columns, one YAML verdict each):**
- keep 96, watch 10, conditional 22, ban 50.
- The trees read **104** columns; the router reads 2 (ctx:month, ctx:lat).
- **31 kept columns are lagged by rule:**
  - 12 index columns at lag 2 (nino*, sst_anom_*), plus pdo at lag 2.
  - oni and tni at lag 3.
  - noi and burn_frac at lag 1.
  - 14 annual columns at lag 1 year.
- **The 50 bans by reason:** post_window_snapshot 14, incomplete 13, structural 10, trend_proxy 10,
  lookahead_unfixable 2, label 1.

**Changes vs the shipped verdicts:**
- **snow_duration_days: ban to keep.** It counts snow days over a calendar year, and R8 lags it one year, which removes
  the look-ahead behind the shipped ban. It is ERA5-Land reanalysis with 0% missing. This is the only column added to
  the shipped feature set.
- **burn_frac and burn_lag1: keep to watch.** GFED's burned area is upstream of ACAG's own GEOS-Chem simulation
  (gfed_burn_ingest.py:22-28). **burn_frac also moves to lag 1** (see Q1).
- **population_density: to watch.** The 2021-23 values are extrapolated model output.
- **spi_24m: to watch.** It is trend-loaded (r = 0.874 with the year on thar, Part 340).
- **luh2_urban: watch.** Same as shipped (it is a covariate of ACAG's GWR calibration).
- **deeprec_twsa: keep to ban (lookahead_unfixable).** *Skeptic pass.* The reconstruction is a CNN+LSTM model, and its
  input time window is documented nowhere I could read: the NetCDF attributes, the provider pages and the abstract are
  silent, and the paper returns HTTP 403. The earlier lag-3 bound covered only its ONI input. See Q3.
- **epo: keep to ban (structural).** *Skeptic pass.* CPC never issues a December EPO. R30 fills the gap with 0, so
  epo == 0 marks December exactly. This is the same mechanism that got eddi banned (Parts 340, 342).
- **Ban kept, reason corrected:**
  - V20_burned_binary, burn_month_count, burn_doy_mean become structural: FireCCI switches from MODIS to OLCI exactly at
    the 2019/2020 split.
  - The 3 snow-date columns become incomplete: 57-64% of donor rows are missing.
  - eddi and eddi_observed become structural: they are month masks, not trends.
- **12 index columns get windows from provider documents** (soi, tna, tsa, iod, noi, ao, nao, pna, wp, sam, pdo, epo).
  The draft had them conditional only because their window was "unknown". epo is now banned.

**Owner rulings applied as given:** A1-A5, oni/tni lagged not banned, R-A / R-B, and F3 (the MOD44B trio as shipped,
so Y0 stays 2003).

## 2. Fire

**Counts (214 sheet rows; the YAML covers the 196 catalog columns):**
- YAML: keep 103, watch 3, conditional 14, ban 76.
- The trees read **104** columns; the router reads 2.
- **29 kept columns are lagged by rule:** the index columns, cloud_frequency_pct (lag 1, co-measured), grace_lwe
  (lag 1) and 11 annual columns (lag 1 year).
- Once the history store exists and Q5 is answered yes, 9 more columns enter.

**Changes vs the shipped verdicts:**
- **cropland_fraction: ban (post_event_state).** It is the MCD12Q1 land-cover slice, the same product fire already
  bans. luh2_cropland still carries cropland.
- **aridity_index_p_pet: ban (incomplete).** 28% of donor rows are missing, and some values are impossible.
- **last_burn_size, nbr25km_12mo_lag1, nbr75km_12mo_lag1: ban (target_derived).** They are hidden copies of the
  target's own past at t-1, which ruling R-D (b) puts off limits.
- **lgt_density, lgt_is_zero: ban (incomplete).** The lightning data start in 2013.
- **lgt_missing: ban (trend_proxy).** It is the year key in disguise.
- **vod_lag2, vod_d1, vod_anom, agb_lag1y, agb_contrast: ban (incomplete).** 26-31% of donor rows are missing, and
  the sidecar holds only the old 1,000-cell sample.
- **9 history columns: keep/watch to conditional** (tslf_months, tslf_censored, n_burns_12mo, n_burns_60mo,
  burn_rate_120mo, nbr25/75km_12mo_lag3/lag6). *Skeptic pass, fail-safe.* No declared store holds them yet. As "keep",
  the run would refuse. After you build the store, they switch back to the verdict written in their reason (Q5).
- **last_burn_month: keep to ban (structural).** *Skeptic pass.* Together with tslf_months it gives the calendar month
  exactly, which is the same mechanism as eddi.
- **snow_cover_fraction: keep to ban (incomplete).** *Skeptic pass, extended to fire.* October 2022 is empty in all
  40 groups (I measured it). At lag 1, every November 2022 row would read a zero-fill, which means "no snow".
- **deeprec_twsa: keep to ban (lookahead_unfixable).** Same reason as PM2.5 (Q3). grace_lwe stays as the water-storage
  column.
- **epo: keep to ban (structural).** The December month key, as in PM2.5.
- **gdp_pc, population_density: keep to ban (trend_proxy).** *Skeptic pass, extended to fire.* Measured on fire's 40
  groups, they behave like the year:
  - gdp_pc: median r with the year 0.94; every test year above the group's training maximum in 18 of 40 groups.
  - population_density: median r 0.99; every test year above the training maximum in 28 of 40.

  See Q4. luh2_urban is just as year-like (it beats the training maximum in 39 of 40 groups), but it stays: the six
  LUH2 states are one sum group, and you ruled to keep luh2.
- **Moved to watch:** grace_lwe, spi_12m, spi_24m.
- **Already ruled, unchanged:** the 14 FREEZE columns, the snow-date columns, the 5 SPEI columns and amo (Q3 a; see
  Q6), and oni/tni lagged.

## 3. Defo

**Counts (178 sheet rows; the YAML has 381 verdicts once the catalog is cleaned up):**
- YAML: keep 215, watch 12, conditional 48, ban 106.
- The trees read **227** columns; there is no router context.
- **18 kept columns are lagged by rule:**
  - V11, V12, V14 and gpp at lag 1 year, from their reach facts.
  - The nino*, sst_anom_*, oni and tni annual aggregates at lag 1 year.
- **The 48 conditional entries become 275 tree columns once their conditions are met.** 15 of them then also run at
  lag 1 year.

**Changes vs the shipped verdicts:**
- **lon, lat: keep to ban (structural).** Coordinates are never tree features. At 4 km they let the trees memorise
  each cell. See Q10.
- **12 SoilGrids/MERIT static columns: to watch.** Part 508 found them admissible with disclosure. hand_m and
  upstream_area_km2 carry Hansen treecover2000 in their lineage.
- **aridity_index_p_pet, eddi, esacci_sm, snow_cover_fraction, grace_lwe, epo: ban (incomplete).** Their strict annual
  aggregates are missing in 25-68% of donor rows (snow cover is also 100% missing in 2022), or (epo) are empty in every year.
- **The 15 entries that need a one-year lag become conditional** (V13_mean_lst_C, nighttime_lst_C,
  cloud_frequency_pct and V20_burned_binary, each _mean/_min/_max, plus burn_month_count, burn_doy_mean and ntl).
  *Skeptic pass, HIGH.*
  - They are leak-safe only one year back.
  - Only `co_measured_with_target: true` in catalog.yaml gives them that lag, and it is not written yet.
  - The guard that would catch the missing fact (G-FACTS) is not built. So "keep" would let same-year burned area,
    LST, cloud and night lights reach the trees **at lag 0 with no error**.
  - Write the fact and switch them to keep **in one change**.
- **The 33 index aggregates become conditional** (soi, pdo, tna, tsa, iod, noi, ao, nao, pna, wp, sam, each
  _mean/_min/_max). *Skeptic pass.* They are not built yet: none of the 924 D:/defo_features files holds them. Sign
  their windows, rebuild, then switch them to keep.
- **gdp_pc: keep to ban (trend_proxy).** *Skeptic pass, extended to defo.* Median r with the year 0.97; every test
  year above the training maximum in 13 of 42 groups. See Q4. population_density stays (keep), because you ruled to
  keep it as an annual series (Part 437). Its year-clock numbers are disclosed.
- **Packaging (skeptic pass).** The YAML no longer bans the 101 monthly parents as "structural". The annual target
  never reads them, and a parent-level ban would contradict the family rule (APP_PLAN.md:172).
  - **Adopt it together with dropping the 101 monthly parents and the 33 lag1_* rows from catalog.yaml.** These are
    exactly the 134 rows that defo_draft/catalog.yaml already leaves out.
  - Against today's catalog, the closed-world check refuses loudly (134 columns without a verdict). Nothing leaks that
    way.
- **Owner rulings applied as given:** tree_cover_pct, luh2_forest and luh2_secondary are banned as Hansen co-products;
  the MOD44B triple is banned; h_lag1-3 and h_cum are replaced by the engine block; h_nbr* and h_yrs_since are kept.

## 4. NDVI

**Counts (206 columns, one YAML verdict each):**
- keep 136, watch 5, ban 65; no conditional.
- The trees read **132** base columns; the router reads 9 context columns.
- **28 kept columns are lagged by rule:**
  - cloud_frequency_pct and burn_frac at lag 1.
  - 11 nino*/sst_anom_* columns at lag 2, and pdo at lag 2.
  - oni and tni at lag 3.
  - noi at lag 1.
  - 11 annual columns at lag 1 year.
- The 435 engineered driver lags are counted separately. Each one takes its base column's verdict.

**Changes vs the shipped verdicts (run89):**
- **cropland_fraction: ban (coproduct).** It is MCD12Q1 optical land cover.
- **V20_burned_binary: ban (structural).** The FireCCI sensor switches at the split. GFED burn_frac at lag 1
  (ruling Q38 b) replaces it.
- **co2 and the 6 food prices: ban (trend_proxy).**
- **sst_anom_mediterranean: ban (trend_proxy).** It tracks the year (r 0.88). See Q8.
- **scpdsi: ban (trend_proxy).**
- **eddi, eddi_observed, aridity_index_p_pet: ban (structural).** They are seasonal masks that leak the month key.
- **esacci_sm: ban (incomplete).** About 30% missing. It is also retrieved jointly with vegetation optical depth.
- **snow_cover_fraction: watch to ban (incomplete).** *Skeptic pass, HIGH.* October 2022 is 100% missing in all 133
  regions. At lag 1 the November 2022 test rows would read "no snow" across the Arctic. December is also blank there
  (polar night). Re-ingesting MOD10CM 2022-10 would reopen it.
- **epo: keep to ban (structural).** *Skeptic pass.* The December month key. Also take it out of LAG_BASES.
- **deeprec_twsa: keep to ban (lookahead_unfixable).** Q3. It must leave features/build.py LAG_BASES, or the engine
  refuses its 5 lags.
- **gdp_pc, population_density: ban (trend_proxy).** *Skeptic pass.*
  - gdp_pc: median r with the year 0.96; every test year above the training maximum in 35 of 67 groups.
  - population_density: median r 0.99; the same in 49 of 67 groups.

  See Q4. luh2_urban is kept (ruling luh2 KEEP, and LUH2 is one sum group), with its numbers disclosed.
- **Moved to watch:** grace_lwe, spi_24m, tsa, sst_anom_atl3, sst_anom_coral_sea.
- **Lag changes only:** cloud_frequency_pct moves from lag 0 to lag 1 (co-measured, Q3 a).
- **Citation corrected on 11 annual rows.** "Ruling A1" was PM2.5's ruling. These rows are lagged by Q3 a, and no
  ruling says NDVI keeps them.
- **ATTENTION (dataset code, not a verdict).** Ten banned bases must leave `features/build.py` LAG_BASES, or the
  engine refuses their 50 lag outputs: co2, the 6 food prices, scpdsi, sst_anom_mediterranean and deeprec_twsa. Also
  drop epo, eddi, aridity_index_p_pet and esacci_sm from that list. Their lags are banned with them anyway.

---

## 5. Timing facts to sign (grouped; the CSV `timing_fact_proposal` column has the per-row text)

**A. Shared store-catalog fixes. They block every headline run until signed** (the D95 range check refuses a column
with more than 0.1% of values outside its legal range).

| Fact | Proposed value | Evidence |
|---|---|---|
| nitrogen_gkg units and range (all 4 packages) | units `cg kg-1`, legal_range [0, 5000] (today `g kg-1`, [0, 50]) | 13.2% of the 2019+2022 panel values are above 50 (max 267). SoilGrids stores N in cg/kg, and the C:N check agrees. Check soil_organic_carbon_gkg's units in the same change (likely dg/kg) |
| V30_soil_moisture_pct lower bound (all 4) | -1e-12, or clip \|x\| < 1e-12 to 0 at ingest | 2.3-4.8% of values are float-zero residue (min -1.07e-18) |
| burn_frac, GFED store (PM2.5, NDVI) | add reach_after_max {1, month}, assumed: lag 1 on both targets | MCD64A1's month-m label uses month m+1 observations (User Guide 3.1.2), as accepted in R-D (b). NDVI stays at lag 1 (Q38 b). Then answer co_measured false for PM2.5 |

**B. Index windows (panel store catalog; every package that keeps them):**
- **soi, tna, tsa, iod, ao, nao, pna, wp, sam:** stamp period_centre, window {1, month, centred} (a plain month).
  Lag 0 on the monthly targets and on defo's aggregates. Source: INDEX_WINDOW_AUDIT.md Table 1 [S3, S8, S11-S16] and
  the T8 data test. epo is banned, so it needs no window.
- **noi:** {3, month, centred}, assumed. Lag 1 month; lag 1 year on defo's aggregates. No provider document states its
  window (audit open item 11), so the conservative bound wins. See Q2.
- **pdo:** {1, month, centred} plus reach_after_max {2, month}. Lag 2; lag 1 year on defo. Source: the PSL pdo.data
  footer points to an ERSSTv5 projection series, so R-A (a) applies on evidence.
- **nino12/3/4/34 and the sst_anom_*:** as already merged (R-A a, F4), lag 2. **oni:** lag 3. **tni:** assumed 7-month
  window (R-B), lag 3. On defo's annual aggregates all of these are lag 1 year. Pick one unit spelling, K or degC.
- **Defo:** after signing, rebuild the 33 aggregates with features/build_store.py, update the include sha256, then
  switch them from conditional to keep.

**C. Package facts (catalog.yaml):**
- **Fire target burned_frac:** reach_after_max {1, month}, assumed (R-D b). The guide does not state the margin.
- **NDVI target V11:** the ruled form (1 month centred, reach 15 days either side).
- **co_measured_with_target: true** on:
  - fire: cloud_frequency_pct (already ruled).
  - NDVI: cloud_frequency_pct and burn_frac (Q38 b).
  - defo: the 15 conditional entries' families (evidence Part 431, defo_ban.py:116-137), **written in the same change
    that flips them to keep.**
- **co_measured_with_target: false** (with evidence) on every other kept time-varying driver in all four packages.
  Plan 1.3 gives this fact no default, and G-FACTS will refuse unanswered columns once it is built.
- **Fire catalog:** give V20_burned_binary, burn_month_count and burn_doy_mean the role `target_twin`. That forces
  their ban, as catalog.yaml:136-144 asks.
- **Defo catalog:** drop the 134 bookkeeping rows (section 3).

**D. Other drivers:**
- **grace_lwe (fire, NDVI):** {1, month, centred} plus a 15-day reach either side, assumed: lag 1. Measured from the
  provider's own time_bounds; the latest solution ends 14 days after its month.
- **14 annual columns:** period_end, 1 year backward. Lag 1 year on the monthly targets (Q3 a, R8); lag 0 on defo
  (D25 a). Record observed_through: hdi 2015, fert 2013, population 2020.
- **Monthly drivers** (TerraClimate, AgERA5, ERA5-Land, SPI, wbal, conflict): the plain month or a trailing window,
  lag 0. Sign era5l_d2m and era5l_stl1 in Kelvin.
- **20 static columns:** no window. Record a content epoch of 2019 or earlier for G-EPOCH.
- **Fire history columns:** they take their facts from the rebuilt label-lag-2 store's catalog.

## 6. Questions for you (each has a default already written into the files)

1. **Q1, PM2.5 smoke timing.** burn_frac moves to lag 1 by rule: its month-m value uses month m+1 satellite passes.
   PM2.5 loses the same-month smoke signal the shipped run used at lag 0. **Accept? (default: yes.)** burn_lag1 then
   duplicates burn_frac at lag 1. The feature script can move it to month t-2 or drop it.
2. **Q2, noi window (all 4).** Default: an assumed 3-month window, giving lag 1. The alternative is a plain month
   (lag 0), backed only by the T8 data test, with no provider document.
3. **Q3, deeprec_twsa (PM2.5, fire, NDVI).** Default: **ban**, because the model's input window is undocumented. The
   alternative is to keep it at an assumed lag 3, once the paper or code shows the LSTM reads only past months.
4. **Q4, year clocks.** gdp_pc and population_density rise smoothly, so inside each region they act as the year
   (median r 0.94-1.00 in NDVI, fire and defo; not measured on PM2.5).
   - (a) Default: ban both in NDVI and fire, and gdp_pc in defo. Keep them where your rulings say so: PM2.5 both
     (Part 539), defo population (Part 437).
   - (b) Ban them everywhere.
   - (c) Keep them as watch everywhere.
5. **Q5, fire history store.** Build it now? It takes about 2 GB and 10 minutes, and **D: has 49.6 GB free**. (The
   "2.0 GB free" in SMOKES_REPORT.md is out of date.) Then the 9 conditional history columns go back to keep/watch.
   Default: yes. last_burn_month stays banned as a month key unless you want it as watch.
6. **Q6, Q3 a family bans where the reason does not apply.**
   - The facts: fire's 5 SPEI columns and amo are complete in 2003-2022, because fire's window was cut at 2022 for
     exactly this. snow_duration_days has no look-ahead once R8 lags it; the PM2.5 proposal keeps it, while fire,
     NDVI and defo ban it.
   - (a) Default: as written.
   - (b) Lift these bans where the reason does not hold.
   - (c) Ban snow_duration_days in PM2.5 too.
7. **Q7, fire sidecars.** The fire_ndvi_lags and fire_danger stores: (a) leave them undeclared, so their 14 rows drop
   out (default); or (b) declare them and rule each row.
8. **Q8, NDVI sst_anom_mediterranean.** Ban it as a trend proxy (default; r 0.88 with the year), or keep it as watch?
   sst_anom_coral_sea is borderline and stays watch. A single written threshold would settle both.
9. **Q9, NDVI router context.** The frozen top-5 context list was chosen with the test years in view (F15). Sign the 5
   exceptions.yaml disclosures (default), or switch to harmonics-only context?
10. **Q10, defo lon/lat.** Ban them as tree features (default; no other package feeds coordinates to the trees), or
    keep them as the shipped defo run did?

## 7. Expected effect on Y0 (first usable year)

R4 sets Y0 to the first data year plus the largest computed lag on a kept column, rounded up to whole years. None of
the changes gives any kept column a lag longer than 1 year, so **Y0 does not move in any package**.

| Package | Y0 | Why |
|---|---|---|
| PM2.5 | **2003**, as now | The largest lag is the 1-year lag on the annual columns. burn_frac and noi move to 1 month, which still lands inside 2002. F3 holds |
| Fire | **2003**, as now | The same 1-year annual lag. Moving the history columns to conditional does not count for R4 |
| Defo | **2002**, as now | The target store starts in 2001. But D:/defo_features starts in 2002, so the 2002 fit rows of the lag-1-year columns (V11, V12, V14, gpp, the index aggregates) read a 2001 that does not exist and get zero-filled. The shipped matrix started in 2003. No column crosses 25% missing because of this |
| NDVI | **2003**, as now | Panel starts in 2002; largest lag 1 year. The lead-12 router-context gap is handled by ruling G |

## 8. Low-severity skeptic items, not applied (for a later pass)

- **PM2.5:**
  - Move spi_12m to watch, like spi_24m.
  - Move diurnal_temp_range_C to watch: aerosol dimming lowers daytime highs, so it partly responds to PM2.5.
  - Record SPI's 1901-2025 calibration period as a printed disclosure (Q43 a).
- **Fire:**
  - Move wbal_roll12 and wbal_roll24 to watch. Counting fire regions where \|r with the year\| > 0.6: wbal_roll24
    14 of 40, spi_24m 12, wbal_roll12 8, spi_12m 8.
  - Give the SPEI/amo and snow_duration_days bans Q3 a as their basis in the wording, rather than "incomplete" or
    "unfixable look-ahead".
  - Disclose the earlier scratch folder D:/treeroute/ban_review/fire/.
- **Defo:**
  - Relabel aglw_* to post_event_state, deeprec_twsa to coproduct, and clf_* to post_event_state. Every verdict stays
    ban.
  - Add these disclosures to exceptions.yaml: night lights switch from DMSP to VIIRS between 2013 and 2014; Hansen can
    book a late-year clearing in the next year; FireCCI switches from MODIS to OLCI in 2020; population 2021-23 is
    extrapolated; hand_m and upstream_area_km2 have Hansen lineage.
- **NDVI:**
  - Write one trend-proxy rule in the YAML header.
  - The co-measured lag-1 floor does not fully clear the target's 15-day reach for cloud. The fix would be lag 2, or a
    floor of content lag + 1.
  - Add legal ranges for the spi_* and wbal_* columns.
  - Tidy the evidence for eddi_observed, esacci_sm (it costs -0.030 anomaly R2 on thar) and the static epochs:
    road_density is about 2018, later than NDVI's 2016 inner-fit end.
