# Smokes of the four draft packages (nowcast + forecast ladder)

Date: 2026-10-05. One smoke at a time, from `engine/`, with the engine launcher:

```
py -3.9 -m treeroute smoke datasets/<package>
```

No engine code and no package file was changed. Before each smoke a small watcher checked that no other
Python job was running (none was), then started the smoke and sampled the RAM of its whole process tree
every 0.25 s. Every number below comes from a DRAFT package at smoke size (4 groups, 40 units per group,
12 trees per group), so it is a plumbing check only. Smoke numbers say nothing about which way a real
result will go. Every run record says "not headline-eligible".

| Package | Result | Wall time | Peak RAM | Run folder (under `D:\treeroute\runs\`) |
|---|---|---|---|---|
| pm25_draft | **ran**: nowcast + ladder (leads 1, 3, 6, 12) | 72 s | 3.0 GB | `pm25_draft\smoke\20261005_e29986c7` |
| fire_draft | **ran**: nowcast + ladder (leads 1, 3, 6, 12) | 99 s | 3.0 GB | `fire_draft\smoke\20261005_98c6856d` |
| defo_draft | **ran**: nowcast + ladder (lead 1, the only annual lead) | 34 s | 0.4 GB | `defo_draft\smoke\20261005_414d3a96` |
| ndvi_draft | **failed at ladder lead 12** (exit code 4). Nowcast and leads 1, 3, 6 finished and saved. | 150 s | 3.8 GB | `ndvi_draft\smoke\20261005_a2c1ec14` |

The defo feature store `D:\defo_features` exists and is complete (924 group-year files = 42 groups x 22
years, each with its build record, plus the static table), so defo_draft was run, not skipped.

The lowest free RAM seen during any smoke was 6.9 GB of 15.8 (NDVI). Each run removed its own temp
folder and released the heavy-job lock, the failed NDVI run included.

---

## Must-reads

**ATTENTION 1: NDVI's ladder stops at lead 12.** The exact message:

```
treeroute smoke refused: RouteRefusal: [R20] the context on fit rows holds 1160 missing or infinite
value(s) Fix: leave rows with a missing label out of the fit rows (R30); normals, context and tree
answers must be finite
```

It happened in the lead-12 N2 guard, at the router fit, after the lead-12 bank was fitted. The cause, in
plain words: at a lead, the router's context columns are read at the issue step (12 months earlier). The
fit rows start in January 2003 (Y0), so their issue steps fall in 2002, the first year the panel has.
Three of NDVI's context columns are lagged drivers: `sph_kgkg_lag6`, `era5l_slhf_lag1` and
`V07_total_ref_ET_mm_lag1`. At an issue step in early 2002 they need months from 2001, which do not
exist, so those values are empty. The trees get such gaps filled with 0 (R30), but the router refuses
empty context. I recounted it from the panel, read-only: sph_kgkg_lag6 is empty on 920 labelled fit rows
(January to June 2003), and the two lag-1 columns on 120 each (January 2003). That makes 1160, the exact
number in the message. At lead 6 the same count is 0, because 6 + 6 months still lands inside 2002.
pm25 and fire never hit this: their context (`ctx:month`, `ctx:lat`) has no lags. Defo has no context.
So this is the first package with lagged context, and any lead plus context lag of more than 12 months
will do the same on the headline run. Options for you to choose from (I have not picked one):
- (a) Leave a fit row out of a lead's router fit when its issue-step context is empty, as R30 already does
  for a missing label, and record the count. The test rows (2020-2023) are not affected.
- (b) Fill empty issue-step context with a stated fallback, for example the donor-row mean at the lead's
  fit cut, as the history block's fallbacks already do. This is a new rule.
- (c) Start each lead's fit rows only where the context is complete, that is, once the lead plus the
  largest context lag reaches back no further than January 2002. At lead 12 that drops January to June
  2003.
- (d) Change the package, not the engine: no lagged columns in NDVI's context, or a later Y0. This
  changes the disclosed top-5 water drivers ruling.

**ATTENTION 2: D: has only 2.0 GB free** (2.05 GB before the first smoke, 1.97 GB after the last). At the
first smoke on 2026-09-29 it had 53 GB. The smokes needed 0.01 to 0.21 GB of temp disk and wrote about
80 MB to the run folders in total (pm25 36 MB, fire 23 MB, NDVI 19 MB, defo 1.5 MB), so they are not the
cause. A headline run will need far more temp disk
than this. I did not touch anything outside my run folders.

**ATTENTION 3: fire's adopted arm is clipped often.** For log_c corrector GLS, 1,444 of 7,680 test
predictions (18.8%) were below 0 before the clip to the legal range [0, 1]. On the decision surface the
log_c arms had 27-28% of predictions below 0, and the identity arms 16-18%. The arcsine arms had none.
On fire, MAE and anomaly R2 also point opposite ways: the adopted arm has the best MAE (0.00730 against
guess-normal 0.00805) but anomaly R2 -0.064. This is the "MAE rewards timid predictions on a mostly-zero
target" pattern. You have ruled MAE as the selection rule, so this is a flag, not a fault. Defo's identity
arms show the same thing on test: 20-24% clipped (not the adopted arm).

**ATTENTION 4: edge picks.** Most best grid points sit on an edge of the penalty grid. The engine flags an
edge pick and does not extend the grid (Q13 a). On pm25 every tree arm picked the top ratio (1.0). On fire
every identity and log_c arm picked the top level (100), the strongest penalty, which means "almost no
trees". On defo the log_c and arcsine arms picked the bottom level (0.1). On NDVI only identity plain GLS
sat on an edge. This means little at smoke size. If the headline runs show the same, it is a question
about the grid.

**ATTENTION 5: 65 NDVI driver columns are left out by a missing fact, not by a verdict.** These are 13 bases
x 5 lags: ao, epo, grace_lwe, iod, nao, noi, pdo, pna, sam, soi, tna, tsa and wp. Their shipped verdict is
"keep", but their facts give an unknown window with no signed bound, so R8 refuses them at lag 0 (G-LAG).
A further 30 are banned on purpose (spei_01m/03m/06m/24m, V06_spei_12m and amo, which are incomplete in
2023). So NDVI's trees see 340 of run89's 435 driver lags (68 of the 87 bases). Signing those 13 bounds
is a catalog item for you.

---

## What is the same in all four runs

- **Departures (8, recorded in each run record):** quick checks not built; GLS arms use a NEW weighted
  per-unit solve awaiting your review; private router kernels; the band is the run's own; report rows not
  built; the ladder guard reads each lead's fit-cut bank; the ladder readings await your ruling; the
  pre-Y0 label reading. The guard tolerance is the smoke stand-in (C9.guard_tolerance_k is unset).
- **Threads:** BLAS, OpenMP and oneDAL were each pinned to 4 threads, sklearn was patched by sklearnex
  2025.10.0, there were 8 router workers with 1 BLAS thread each, and 8 tree-predict workers.
- **Bank:** 48 trees (12 per group), 40 bank units and 40 scored units per group (flagged "capped": the
  smoke's fixed count), correctors at depth 6 and leaf 10 fitted on out-of-bag rows, and a refit at the
  inner cut for the decision (L6 b).
- **Own-block drop confirmed in every run:** all 20 tree-answer tables (12 at the fit cut: plain, corrector
  and placebo x 4 groups; 8 at the inner cut) record `own_trees_dropped: 12` and 36 columns out of 48
  trees. guard_report G-DISJOINT reads "each router drops its own overlap block's tree columns", and
  route.kinds checks it at every router fit. Each run has 4 single-group overlap blocks with no linked
  pairs, so "own block" means "own group" here.
- **Lock before labels confirmed for every lead that ran:** for each lead, the file on disk hashes to the
  SHA-256 in its lock, and the opened-labels record carries the same hash. The write order is always:
  adoption, then lock, then labels opened, then test_preds. The nowcast lock also records that every
  pre-lock read of test-window labels came through the D54 (a) as-of door: 360,960 rows for pm25, 345,920
  for fire and for NDVI, and 1,920 for defo. These are history and persistence inputs, not the scored
  labels. NDVI's lead 12 was never locked, and its test labels were never opened.
- **Lead-0 contract holds in all four:** the ladder's own lead path at lead 0 equals the nowcast byte for
  byte. That covers the pool, the bank's donor-row inputs (keys, grid rows, features, labels), c, the
  tolerances, the donor-row link means (and the GLS weight model for fire, whose pin is weighted), and
  every saved column it assembles: 19 columns (17 for NDVI, which has one link). The largest gap was 0.0.
- **G-PLUMB passed for every link:** trees-off equals the normal, each gap inside its tolerance. The
  largest gap was 6.1e-7, for fire's identity link, against a tolerance of 1e-6. The others were between
  1.7e-10 and 7.8e-8. The base grid point reproduces the unswept router exactly. Wherever GLS arms ran
  (pm25, fire, NDVI), the weighted router with equal weights equals the unweighted one (gap 8.4e-14 at
  most).
- **Rows saved:** every run writes `test_preds.parquet` (every row of every arm, before and after the clip,
  plus the baselines), `inner_preds.parquet` (every decision candidate), and per ladder lead
  `ladder/lead_<L>/test_preds.parquet` and `guard_preds.parquet`, plus `fitctx_log.parquet` and the score
  tables. The counts are listed per package below.

Persistence and damped persistence exist only on the ladder (R31: a lead of at least one step), so the
nowcast tables show predict-zero, guess-normal and the last-5-years normal. Anomaly R2 is measured against
the normal that guess-normal uses, which is why guess-normal and the identity trees-off score exactly 0.

---

## 1. pm25_draft

**Data.** 127 groups, the smoke took 4: alaska_interior_taiga, amazon_basin_brazil, anatolian_plateau,
andes_puna. Target: 42,240 rows. Drivers: the monthly panel (92 columns) and GFED burn (1 column),
covering every row. Pool: 40,320 grid rows (160 units x 252 months) with 99 tree columns (6 of them
history) and 2 context columns.

**Derived settings (36 entries).** Monthly data, with the month of the year as the season. Y0 is 2003 and
the last year 2023. Training ends in 2019. The test years are 2020-2023, the inner fit 2003-2016 and the
inner score 2017-2019. Per-unit router with columns intercept, normal (both unpenalised), context and
trees. The grid is 7 levels x 5 ratios. Links: identity and log_c, with c = 3.340 at lead 0. The legal
range is 0 to infinity. History: the last 1, 2 and 3 values plus 12-month, 60-month and all-history means,
ending at t-1. Driver lags: 47 at lag 0, 13 at 1, 12 at 2 and 2 at 3; all 74 have
`co_measured_with_target` unanswered. Leads: 1, 3, 6 and 12 steps.

**Timings.** Target read 9 s, stores 4 s, derive_all 4.0 s, run folder 2 s. Inside the run: pool 0.9 s,
fits 5.2 s, decision 9.1 s, test pass 3.2 s, report 0.7 s. Ladder: lead-0 contract 1.5 s, then leads 1,
3, 6 and 12 at 5.3-5.8 s each, then the ladder table 4 s. Peak RAM 3.0 GB.

**Adoption.** log_c link, corrector tool, unweighted, at penalty level 0.3 and ratio 1.0. The N2 guard
passed with 8 of 8 tree arms eligible. There were 282 candidates on 5,759 decision rows. This is the same
arm, penalty and test MAE as the first smoke on 2026-09-29. The 4 GLS arms are now routed (they were
missing then) and none of them won.

**Test window (2020-2023, 7,678 labelled rows).**

| Column | MAE | Anomaly R2 | Hit rate |
|---|---|---|---|
| **Adopted: log_c corrector** | **3.723** | **0.215** | 0.337 |
| log_c trees-off (reference) | 4.111 | 0.031 | 0.299 |
| Guess-normal | 4.254 | 0.000 | 0.288 |
| Last-5-years normal | 3.729 | 0.126 | 0.376 |
| Predict-zero | 21.888 | -15.48 | 0.002 |

Verdict: "helps" (contrast 0.388, from 0.123 to 0.653, against a band of 0.092; all 4 groups better).

**Ladder (common rows, 7,678).** The `*` marks what that lead adopted.

| Lead | Adopted arm | Its trees-off | Guess-normal | Last-5 normal | Persistence | Damped persistence | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | *log_c corrector 3.956 (R2 0.111) | 4.111 | 4.254 | 3.729 | 5.586 (R2 -0.71) | 3.679 (R2 0.219) | helps |
| 3 | *log_c corrector 4.151 (0.052) | 4.144 | 4.285 | 3.791 | 9.077 | 4.180 | equivalent |
| 6 | *log_c corrector 4.147 (0.019) | 4.157 | 4.302 | 3.855 | 10.181 | 4.255 | equivalent |
| 12 | guard failed: *identity trees-off 4.323 (0.000) | - | 4.323 | 3.870 | 4.113 | 4.025 | declined |

Predict-zero is 21.888 at every lead.

**Rows saved.** test_preds 7,680 x 41; inner_preds 5,759 x 568; ladder test_preds 7,680 rows per lead
(21-23 columns); guard_preds 5,759 / 5,439 / 4,959 / 3,999 rows; fitctx_log 7,064 records.

## 2. fire_draft

**Data.** 40 groups, the smoke took 4: alaska_interior_taiga, amazon_basin_brazil,
angola_zambia_fire_belt, australian_bushfire_belt. Target: 40,320 rows. The target reader logged
unit-months absent from the file (NaN labels; up to 288 a year in Alaska 2002-2012) and dropped rows of
cells that are not units (7,740 a year in Alaska, about 2,850 in Australia). Driver: the monthly panel, 99
columns, covering every row. Pool: 38,400 grid rows (160 x 240 months) with 104 tree columns (6 history)
and 2 context columns.

**Derived settings (36 entries).** Monthly data. Y0 is 2003 and the last year 2022. Training ends in 2018.
The test years are 2019-2022, the inner fit 2003-2015 and the inner score 2016-2018. Per-unit router, the
same columns and grid as pm25. Links: identity, log_c and arcsine, with c = 0.0128. The legal range is
[0, 1]. **History starts at t-2** (R17 start offset 1, as ruled in R-D): the history block ends at t-1
for a nowcast and starts one step further back. 58.75% of the units have a constant fit history (report
only). Driver lags: 50 at lag 0, 15 at 1, 12 at 2 and 2 at 3. cloud_frequency_pct is held at lag 1 as
co-measured. Leads: 1, 3, 6 and 12.

**Timings.** Target read 10 s, driver store 19 s, derive_all 3.6 s. Inside the run: pool 0.9 s, fits
4.7 s, decision 12.5 s, test pass 4.2 s, report 0.8 s. Ladder: contract 3.2 s, then 6.7-6.9 s per lead,
then the table 4 s. Peak RAM 3.0 GB.

**Adoption.** log_c link, corrector tool, **GLS-weighted**, at penalty level 100 and ratio 1.0 (both edges).
The N2 guard passed, with 8 of 12 tree arms eligible: the unweighted identity and log_c arms (plain and
corrector) did not beat their own trees-off. There were 423 candidates on 5,573 decision rows.

**Test window (2019-2022, 7,633 labelled rows).**

| Column | MAE | Anomaly R2 | Hit rate |
|---|---|---|---|
| **Adopted: log_c corrector GLS** | **0.007303** | **-0.064** | 0.924 |
| log_c trees-off (reference) | 0.007321 | -0.063 | 0.919 |
| Guess-normal | 0.008052 | 0.000 | 0.908 |
| Last-5-years normal | 0.007620 | 0.024 | 0.920 |
| Predict-zero | 0.008635 | -0.605 | 0.956 |

Verdict: "helps" (contrast 1.7e-5, from 1.4e-7 to 3.4e-5, against a band of 3.1e-6; all 4 groups better).
A difference this small at smoke size carries no information.

**Ladder (common rows, 7,633).** The pinned arm failed the guard at every lead, so every lead adopted the
decline target (identity trees-off, which is the guess-normal).

| Lead | Adopted (identity trees-off) | Pinned log_c corrector GLS (shown) | Last-5 normal | Persistence | Damped persistence | Verdict |
|---|---|---|---|---|---|---|
| 1 | 0.008052 | 0.007365 | 0.007620 | 0.01632 (R2 -2.10) | 0.008099 | declined |
| 3 | 0.008048 | 0.007251 | 0.007608 | 0.01734 | 0.008099 | declined |
| 6 | 0.008122 | 0.007317 | 0.007746 | 0.01705 | 0.008172 | declined |
| 12 | 0.008179 | 0.007531 | 0.007828 | 0.01413 | 0.008289 | declined |

Predict-zero is 0.008635 at every lead.

**Rows saved.** test_preds 7,680 x 55; inner_preds 5,573 x 850; ladder test_preds 7,680 rows per lead;
guard_preds 5,573 / 5,253 / 4,773 / 3,830 rows; fitctx_log 7,389 records.

## 3. defo_draft

**Data.** 42 groups, the smoke took 4: amazon_basin_brazil, andes_puna, angola_zambia_fire_belt,
atlantic_forest_brazil. The target comes from `D:/defo_target` (4,000 rows). The features store
`D:/defo_features`, built from the monthly panel by defo's own build script, holds all 257 kept columns
and covers 3,520 of the 4,000 target rows (2002-2023). The monthly panel, also listed as a driver store,
was not opened, because every kept column was already found in the features store. Nothing was read from
D:/defo_matrix (the manifest names only D:/defo_features and D:/treeroute). Pool: 3,520 grid rows (160 x
22 years) with 262 tree columns (5 history) and no context.

**Rulings visible in the run.**
- `h_nbr1`, `h_nbr2`, `h_nbr_cum` and `h_yrs_since` are tree features. `h_lag1`, `h_lag2`, `h_lag3` and
  `h_cum` are absent. The engine's history block replaces them: hist_last_1/2/3, hist_mean_5 and
  hist_mean_all, with hist_mean_1 dropped as a duplicate of hist_last_1.
- Region router: columns intercept, normal and trees, with **intercept and normal unpenalised**. The fit
  row cap is **60,000** (each group fitted all 40 of its capped units whole). The router record reads
  "one tree-block Gram per group and table, **shared across the links** (L4)". The grid is 7 levels, no
  ratio, centre 100. The run does not record which thread mode the region solve used. The 1e-9 golden
  check of the 4-thread mode is a test, not part of a smoke.
- The 6 GLS arms are absent, with the declared reason: the region router has no weighted solve yet. The
  GLS weight model is not fitted for a region package.

**Derived settings (34 entries).** Annual data (season constant). Y0 is 2002 and the last year 2023.
Training ends in 2019. The test years are 2020-2023, the inner fit 2002-2016 and the inner score
2017-2019. Links: identity, log_c and arcsine, with c = 4.9e-5. The legal range is [0, 1]. Driver lags:
160 at lag 0 and 75 at lag 1 (21 of them co-measured). Leads: only 1 step. The 6- and 12-month leads merge
into it, and the 1- and 3-month leads cannot be supplied on annual data. R30 flags 9 columns for their
missing share: esacci_sm, nighttime_lst and snow_cover_fraction (max, mean, min), and snow_cover also
vanishes in 2023. Report stratum: forest2000_px. 11.9% of the units have a constant fit history.

**Timings.** Target read 1 s, features store 13 s, derive_all 1.2 s. Inside the run: pool 0.1 s, fits
1.3 s, decision 2.3 s, test pass 2.3 s, report 0.5 s. Ladder: contract 0.7 s, lead 1 3.2 s. Peak RAM 0.4 GB.

**Adoption.** arcsine link, plain tool, unweighted, at penalty level 0.1 (edge: the bottom level). The N2
guard passed with 6 of 6 tree arms eligible. There were 45 candidates on 480 decision rows.

**Test window (2020-2023, 640 labelled rows).**

| Column | MAE | Anomaly R2 | Hit rate |
|---|---|---|---|
| **Adopted: arcsine plain** | **0.002759** | **0.086** | 0.725 |
| arcsine trees-off (reference) | 0.002802 | 0.084 | 0.727 |
| Guess-normal | 0.003599 | 0.000 | 0.655 |
| Last-5-years normal | 0.004209 | -0.083 | 0.642 |
| Predict-zero | 0.003082 | 0.039 | 0.745 |

Verdict: "cannot tell" (contrast 4.3e-5, from -1.9e-5 to 1.05e-4, against a band of 2.1e-5; 3 of 4 groups
better). On test, the log_c arms scored a lower MAE (0.00265) than the adopted arcsine arm. That is a
smoke number with no sign information.

**Ladder (lead 1, 640 common rows).** The pinned arm failed the guard (0.0034572 against 0.0034563), so
the lead adopted identity trees-off: MAE 0.003599. The pinned arm shown beside it scored 0.002804. The
last-5-years normal scored 0.004209, persistence 0.002744 (R2 0.067), damped persistence 0.003372 and
predict-zero 0.003082. Verdict: declined.

**Rows saved.** test_preds 640 x 37; inner_preds 480 x 94; ladder lead 1 test_preds 640 x 23 and
guard_preds 480 rows; fitctx_log 3,547 records.

## 4. ndvi_draft (nowcast and leads 1, 3, 6; lead 12 refused)

**Data.** 133 groups, the smoke took 4: alaska_interior_taiga, alaska_north_slope, amazon_basin_brazil,
anatolian_plateau (greece_mainland and thar_desert are held back as "seen during design"). The target is
V11_mean_ndvi from the monthly panel: 42,240 rows. Drivers: the monthly panel (129 columns, every row) and
GFED burn (31,680 of 42,240 rows; alaska_north_slope has no GFED file, as the store facts declare). The
feature script built 472 outputs. Pool: 40,320 grid rows with 485 tree columns (6 history) and 9 context
columns.

**Rulings visible in the run.**
- Identity link only (R22 = identity), legal range [-0.2, 1].
- None of V11, V12, clf_dry or clf_wet is a feature.
- burn_frac and V20_burned_binary are at lag 1, floor "co_measured".
- run89's lags are rebuilt date-safe by the feature script: 340 lag columns (68 bases x lags 1, 2, 3, 6
  and 12) and 50 water-memory columns (rolls, water-year sums, API, dry-spell counts) reach the trees. The
  95 that do not are explained in ATTENTION 5.
- Context = 4 harmonics (sin1, cos1, sin2, cos2) plus the top-5 water drivers: sph_kgkg_lag6,
  era5l_slhf_lag1, V07_total_ref_ET_mm_lag1, era5l_d2m and V01_mean_temp_C. No column copies the normal;
  the router's normal column is the engine's.
- History starts at t-2 (R17 start offset 1).

**Derived settings (32 entries).** Monthly data. Y0 is 2003 and the last year 2023. Training ends in 2019.
The test years are 2020-2023, the inner fit 2003-2016 and the inner score 2017-2019. Per-unit router, the
same columns and grid as pm25. Driver lags: 419 at lag 0, 33 at 1, 14 at 2 and 2 at 3. R30 flags 12
columns for their missing share (the aridity_index family among them) and marks 6 more borderline. Leads: 1, 3, 6 and 12.

**Timings.** Target read 16 s, stores and feature script 17 s, derive_all 12.3 s. Inside the run: pool
1.9 s, fits 25.3 s, decision 5.7 s, test pass 2.7 s, report 0.6 s. Ladder: contract 2.8 s, then leads 1,
3 and 6 at 14.2-14.5 s each. Lead 12 fitted its bank (9 s), then was refused. Peak RAM 3.8 GB.

**Adoption.** identity link, plain tool, unweighted, at penalty level 0.3 and ratio 0.125 (not an edge).
The N2 guard passed with 4 of 4 tree arms eligible. There were 141 candidates on 5,387 decision rows.

**Test window (2020-2023, 7,336 labelled rows).**

| Column | MAE | Anomaly R2 | Hit rate |
|---|---|---|---|
| **Adopted: identity plain** | **0.03871** | **0.021** | 0.430 |
| identity trees-off (reference = guess-normal) | 0.03807 | 0.000 | 0.448 |
| Last-5-years normal | 0.03913 | -0.160 | 0.451 |
| Predict-zero | 0.42797 | -65.2 | 0.045 |

Verdict: "cannot tell" (contrast -6.9e-4, from -2.0e-3 to 6.1e-4, against a band of 6.2e-4; 1 of 4 groups
better).

**Ladder.** The ladder table was not built, because the run stopped at lead 12. I scored the saved lead
files myself on all labelled rows (7,336), with the engine's formulas. My formulas reproduce pm25's ladder
table exactly.

| Lead | Adopted | Pinned identity plain | Guess-normal | Last-5 normal | Persistence | Damped persistence |
|---|---|---|---|---|---|---|
| 1 | guard passed: *identity plain 0.03888 (R2 -0.002) | same | 0.03807 | 0.03913 | 0.1535 (R2 -13.2) | 0.03841 (R2 0.033) |
| 3 | guard failed: *identity trees-off 0.03803 | 0.03942 | 0.03803 | 0.03942 | 0.2363 | 0.03793 |
| 6 | guard failed: *identity trees-off 0.03818 | 0.03872 | 0.03818 | 0.03977 | 0.2575 | 0.03850 |

Persistence is poor on NDVI because it copies a label from 2 or more months back, across the seasonal
swing.

**Rows saved (up to the refusal).** test_preds 7,680 x 27; inner_preds 5,387 x 286; ladder test_preds
7,680 x 19 for leads 1, 3 and 6; guard_preds 5,387 / 5,071 / 4,591 rows. There is no DONE.json, and
status.json reads "failed" at phase ladder_lead_12. The per-phase fitctx logs are under phases/. The
run-level fitctx_log.parquet and the ladder table are written only at the end, so they are absent.

---

## Small things seen (none stopped a run)

- Fire and defo printed pandas "DataFrame is highly fragmented" warnings from `pipeline/data.py` (lines
  546, 614, 696). They are speed warnings only.
- On pm25 the last-5-years normal is again nearly as good as the adopted arm on test (3.729 against
  3.723), and it is better than the adopted arm at every ladder lead.
- On fire, predict-zero has the highest hit rate (0.956), as expected on a mostly-zero target.

---

## 5. ndvi_draft re-run with owner ruling G1 (2026-10-05, later the same day)

**Result: it ran end to end, nowcast and all four leads, lead 12 included.** Exit code 0, 197 s, peak
RAM of the process tree 4.2 GB. Run folder: `D:\treeroute\runs\ndvi_draft\smoke\20261005_59c97d93`
(19 MB). Same command, from `engine/`:

```
py -3.9 -m treeroute smoke datasets/ndvi_draft
```

Before it started, the watcher found no other Python job running (the full test suite had finished). It
then sampled RAM every 0.25 s. Free RAM was 6.7 GB at the start and 2.6 GB at the lowest, so another
program was holding a lot of memory. D: had 49.7 GB free before and after: space was freed since the
first round (2.0 GB then), not by me. The run removed its temp folder and released the heavy-job lock.

**What changed in the engine (G1, `treeroute/pipeline/`).** At every router pass (each lead's guard and
test pass, and the nowcast's), a fit row whose router context is missing or not finite now leaves the
router's fit, as a row with no label does (R30). Nothing is filled. The count is printed per unit, with
a flag above 5% of a unit's fit rows, and saved in `lead.json` (`context_missing`) and `ladder.json`
(`context_rows_left_out`). A scored row with missing context still refuses (`[G1]`), and route.kinds'
R20 refusal is unchanged behind it. See ATTENTION G1-a below for one thing the ruling did not spell out.

### Lead 12

**Rows G1 left out.** The same 920 fit rows at the guard pass (of 23,842) and at the test pass (of
29,347). All 160 scored units lose rows: 120 units lose 6 (January to June 2003) and 40 units lose 5
(they have no January 2003 label). Only the early fit months are hit: steps 24037-24042, which are
January to June 2003. By column: `sph_kgkg_lag6` 920, `era5l_slhf_lag1` 120,
`V07_total_ref_ET_mm_lag1` 120. Those are the 1,160 values of the earlier refusal. I checked read-only
that the panel holds exactly 920 labelled rows for these units in January to June 2003.

| Pass | Fit rows per unit | Share left out per unit | Flagged (above 5%) | Units moved to the fallback |
|---|---|---|---|---|
| Guard (cut January 2016) | 117-156 | 3.8%-4.3% | none | none |
| Test (cut January 2019) | 144-192 | 3.1%-3.5% | none | none |

**Adoption and guard.** The pinned arm is identity plain, level 0.3, ratio 0.125. On the guard surface
(3,671 rows) it scored MAE 0.044191 against its own trees-off 0.043909, so it **failed the guard** and
lead 12 adopted the decline target (identity trees-off). The adoption was locked before the lead's test
labels opened. The placebo was built, since 12 is the longest lead.

**Test window (7,336 labelled rows, the common rows of every lead).**

| Column | MAE | Anomaly R2 | Hit rate |
|---|---|---|---|
| **Adopted: identity trees-off (= guess-normal)** | **0.038169** | **0.000** | 0.445 |
| Pinned identity plain (shown) | 0.038370 | -0.005 | 0.442 |
| Its placebo | 0.038289 | -0.001 | 0.442 |
| Last-5-years normal | 0.039682 | -0.164 | 0.441 |
| Damped persistence (7,164 rows) | 0.038558 | 0.011 | 0.437 |
| Persistence (7,164 rows) | 0.087350 | -4.69 | 0.300 |
| Predict-zero | 0.427973 | -65.1 | 0.045 |

Verdict: declined. A smoke number at this size carries no sign information.

### Leads 0-6 are unchanged

I compared the new run with the earlier one (`20261005_a2c1ec14`), read-only, file by file. These are
**the same bytes**: `inner_preds.parquet`, `test_preds.parquet`, `adoption.json`,
`inner_candidates.csv`, `score_pooled.csv`, `per_group.csv`, and for each of leads 1, 3 and 6
`adoption_lead_<L>.json`, `ladder/lead_<L>/test_preds.parquet` and `ladder/lead_<L>/guard_preds.parquet`.
`verdict.json` differs only in the run fingerprint and the phase timings. At the nowcast and at leads 1,
3 and 6, every pass printed "none left out".

**The ladder table now exists** (common rows 7,336; adopted arm's MAE): lead 0 identity plain 0.038714
(cannot tell), lead 1 identity plain 0.038898 (cannot tell), lead 3 trees-off 0.038030 (declined),
lead 6 trees-off 0.038244 (declined), lead 12 trees-off 0.038169 (declined).

### Must-reads from the G1 build

**ATTENTION G1-a: G1 also takes the row out of that pass's normal.** My first build left the row in the
unit's normal. The router then stopped at R16 (trees-off must equal the normal): on the test package the
gap was 0.0075 against a tolerance of 1e-7. That is because R15 defines the normal as the mean over the
unit's own fit rows. A row with no label is in neither, so the build now takes the row out of both, but
only for the units that lost rows and only in that pass. What this does at NDVI lead 12: for the January
to June months, the normal leaves out 2003. That normal is also guess-normal, the decline target, the
saved `normal` column and damped persistence's normal. My estimate of the shift over the 920
unit-months: median 0.0014 NDVI, 90th percentile 0.006, largest 0.027. It assumes 15-16 kept years per
month. Leads 0-6 are not touched. Your options:
- (i) Keep it as built: one normal per pass, the same rows as the router's fit.
- (ii) Keep the all-label normal for guess-normal and the saved column, and use the fit-row normal only
  inside the router. That gives one router column two definitions. I did not build this.
- (iii) Rule something else.

**ATTENTION G1-b: the 5% flag share is in the wrong file.** It lives in `pipeline/stages.py`
(`CONTEXT_MISSING_FLAG_SHARE = 0.05`) because `engine_constants.py` was outside this build's write
scope. It should move there with an id, for example `C10.context_missing_flag_share`.

**G1-c (a reading, please confirm):** G1 filters only the per-unit router's fit rows, the one router that
reads context. The region kernels (the region kind, and the R12 fallback router for short-history units)
read no context, so their fit rows are not filtered.

---

## 6. ndvi_draft re-run after the review fixes to G1 (2026-10-05, later again)

**Result: it ran end to end again, and every number is the same as in section 5.** Exit code 0, 354 s,
peak working set of the Python processes 3.8 GB, lowest free RAM 3.0 GB. The run took longer than the
197 s of section 5; the RAM sampler polled a heavier system query every 0.25 s this time. No other Python
job was running when it started. The run emptied its temp folder (`D:\treeroute\tmp`) and left no lock.
Run folder: `D:\treeroute\runs\ndvi_draft\smoke\20261005_527dc8b0` (20 MB). Same command, from `engine/`:

```
py -3.9 -m treeroute smoke datasets/ndvi_draft
```

**What the fixes changed (`treeroute/pipeline/` only).**
- **The fit log now matches what lead 12 fitted.** Before, lead 12's `fitctx_log.parquet` had no
  `normal` entry at all, and its router entries still showed the rows from before G1. Now each unit's
  normal history is read through FitContext (`unit_history`, so it is logged as at every other lead) and
  then trimmed. The engine checks that the trimmed history is exactly the unit's kept fit rows. Each
  trimmed hand-out is followed in the log by a twin row whose purpose ends in `:g1_kept`, with the kept
  rows' count, newest label step and row-key hash.
- **Every row G1 leaves out is saved.** For each pass that left rows out, the rows are in
  `context_missing/<pass>.parquet`: pass, purpose, lead, cut, unit, label step, issue step, grid position,
  and one `missing__<column>` flag per context column. The pass's record in `lead.json` names the file
  (`rows_file`). A pass that left nothing out writes no file.
- **The G1-a question is now disclosed in the run.** `ladder.json` has a new reading, `g1_normal`, and
  the G1 record's `normal` text now says it too: guess-normal and damped persistence's normal follow
  the kept fit rows, while damped persistence's phi is still fitted on every label.

**Checked on this run.**

| Lead 12 | Guard pass | Test pass |
|---|---|---|
| Router rows handed out, then kept (`:g1_kept` twin) | 23,842, then 22,922 | 29,347, then 28,427 |
| `normal` entries (one per unit), each followed by its twin | 160 | 160 |
| Twins' row counts equal `fit_rows - left_out` from `lead.json`, for every unit | yes | yes |
| Rows saved in `context_missing/` | 920 (`lead_12_guard.parquet`) | 920 (`lead_12_test_pass.parquet`) |

The saved rows: 160 units (120 lose 6 rows, 40 lose 5), steps 24037-24042 only, issue step = step - 12.
Missing by column: `sph_kgkg_lag6` 920, `era5l_slhf_lag1` 120, `V07_total_ref_ET_mm_lag1` 120; the
other 6 context columns are never missing. Every log row is dated at or before its cut. Only lead 12 has
`:g1_kept` rows; at the nowcast and leads 1, 3 and 6 every pass printed "none left out".

**Same bytes as before.** Compared read-only, by SHA-256, with section 5's run (`20261005_59c97d93`):
every prediction and adoption file is identical (`inner_preds`, `test_preds`, `adoption.json`, the
score tables, and for leads 1, 3, 6 and 12 the adoption file, `test_preds` and `guard_preds`), and so are
`ladder_table.csv` and the fit-log parts of the nowcast and of leads 0-6. Against the run from before G1
(`20261005_a2c1ec14`), the nowcast and leads 1-6 are identical too. The only differences are the added
rows in lead 12's log part and text in the JSON records: the new `normal` text in every pass record,
the new `rows_file` key (empty where nothing was left out) and the new reading. I compared the JSON
files value by value; no number changed.

One small thing: at lead 12 the fit-cut context logs 160 `normal` entries, where lead 6 logs 320. When
G1 left rows out, damped persistence reuses the test pass's normal (the same normal), so it makes no
second hand-out.

The must-reads of section 5 still stand: ATTENTION G1-a and G1-b, and G1-c.

---

## 7. The four drafts re-run with owner rulings H2-H5 and I1 (2026-10-05, later again)

**Result: all four ran end to end.** Same command, from `engine/`, one smoke at a time. Before each, the watcher
checked that no other Python job was running (none was), then sampled the RAM of the process tree every 0.25 s.
D: had 49.6 GB free before the first. Each run removed its temp folder and left no lock.

| Package | Result | Wall time | Peak RAM | Run folder (under `D:\treeroute\runs\`) |
|---|---|---|---|---|
| pm25_draft | **ran**: nowcast + leads 6 and 12 | 95 s | 3.0 GB | `pm25_draft\smoke\20261005_34f86f41` |
| fire_draft | **ran**: nowcast + leads 6 and 12 | about 86 s (83 s in run.log) | not captured (see below) | `fire_draft\smoke\20261005_f01451aa` |
| defo_draft | **ran**: nowcast + one 1-year lead (6 and 12 months merge) | 35 s | 0.4 GB | `defo_draft\smoke\20261005_6912fd36` |
| ndvi_draft | **ran**: nowcast + leads 6 and 12 | 143 s | 3.9 GB | `ndvi_draft\smoke\20261005_47f02e3d` |

The lowest free RAM was 6.95 GB of 15.8 (NDVI). For fire, my output filter dropped the watcher's summary line, so
its peak RAM is not known; the wall time comes from run.log. A second start of the fire smoke (my slip, a mistyped
command) wrote nothing: the finished folder is unchanged (last write 06:59:20) and no other folder appeared.

**What changed in the engine.**
- **I1 (leads):** the lead constant `C6.lead_months` is now (6, 12), plus lead 0 as the contract. R10 gives
  6 and 12 steps on monthly data and one merged 1-year lead on annual data (events: 183 and 365 days). The
  four expected_derived.json files say the same. The pinned placebo stays at the longest lead (12; defo's 1).
- **H2 (guard bank):** each lead fits a SECOND bank, with its correctors and placebo correctors, at the lead's
  GUARD cut, and builds the guard's history block there, as the nowcast's inner decision does. The guard is
  routed through that bank. The run asserts that no guard row is dated at or before that bank's newest label,
  and records the count (`guard_rows_in_bank_label_window`, always 0). The guard objects are released after the
  guard. As at the nowcast, the guard reads the lead's fit-cut c, tolerances and GLS weight model.
- **H3:** kept as built (context moves with the whole feature row).
- **H4 (missing issue row):** a test row whose issue row t - L is absent is left out of scoring. It is never
  routed, it is not in that lead's `test_preds.parquet` (so no score and no common row holds it), it is saved in
  `ladder/lead_<L>/issue_missing_rows.parquet` with the flag `issue_features_missing`, and it is counted per
  unit and lead (`lead.json` `issue_features_missing`, `ladder.json` `issue_rows_left_out`).
- **H5 (fallback level):** each lead's guard searches its own R12 fallback level on its own surface (the lambda
  centre below 10 fallback units). The lead's test pass reads that level. At the longest lead a plain pin's guard
  also searches its corrector table's level, because the placebo takes its corrector's level. Lead 0 (the
  contract) keeps the nowcast's levels.
- **G1-b:** the 5% flag share is now the engine constant `C10.context_missing_flag_share`. G1-a is unchanged.
- **Departures:** `ladder_guard_bank` and `ladder_readings` are gone (ruled). One new departure,
  `ladder_h_readings`, holds my readings of H2 and H4 (ATTENTION H-2).

**Checked on these runs (read-only, by SHA-256 against the section 1-6 runs).**

| Check | pm25 | fire | defo | NDVI |
|---|---|---|---|---|
| Lead-0 contract: pool, pre-clip, trees-off identical; largest gap | yes; 0.0 | yes; 0.0 | yes; 0.0 | yes; 0.0 |
| Nowcast files (inner_preds, test_preds, adoption, candidates, score_pooled, per_group): same bytes as before | yes | yes | yes | yes |
| Each lead's `test_preds.parquet`: same bytes as before | yes (6, 12) | yes (6, 12) | yes (1) | yes (6, 12) |
| Guard bank cut = the lead's guard cut | yes | yes | yes | yes |
| Guard rows inside the guard bank's label window | 0 and 0 | 0 and 0 | 0 | 0 and 0 |
| The same count before H2 (fit-cut bank) | 4,959 of 4,959; 3,999 of 3,999 | 4,773; 3,830 (all) | 480 of 480 | 4,591; 3,671 (all) |
| Test rows left out by H4 | 0 | 0 | 0 | 0 |
| Anything of a 1- or 3-month lead written (lock, opened labels, lead folder, phase) | no | no | no (its `lead_1` is the 1-year lead) | no |

So the rulings moved only the guards: every nowcast file and every lead's saved test rows are the same bytes as
before. No guard surface had a short-history unit, so every searched fallback level is the lambda centre with
0 fallback units. NDVI's lead 12 (plain pin, longest lead) also records the corrector table's level. G1 at NDVI
lead 12 is unchanged: 920 fit rows left out at the guard and 920 at the test pass, the same steps and columns.

**The guards, before (fit-cut bank) and now (guard-cut bank).** Guard-surface MAE of the pinned arm against its
own trees-off. The trees-off MAE is the same in both, because trees-off reads no tree.

| Package, lead | Before H2 | Now |
|---|---|---|
| pm25, 6 | 3.28633 vs 3.37080: **passed** | 3.47812 vs 3.37080: **failed** |
| pm25, 12 | 3.41335 vs 3.29699: failed | 3.40921 vs 3.29699: failed |
| fire, 6 | 0.0050952 vs 0.0049682: failed | 0.0051300 vs 0.0049682: failed |
| fire, 12 | 0.0055323 vs 0.0054375: failed | 0.0055323 vs 0.0054375: failed |
| defo, 1 year | 0.0034572 vs 0.0034563: **failed** | 0.0034534 vs 0.0034563: **passed** |
| NDVI, 6 | 0.043037 vs 0.042768: failed | 0.043363 vs 0.042768: failed |
| NDVI, 12 | 0.044191 vs 0.043909: failed | 0.044517 vs 0.043909: failed |

**Ladder tables (common rows; MAE of the adopted column).**
- pm25 (7,678 rows): lead 0 log_c corrector 3.7231 (helps); lead 6 declined, identity trees-off 4.3020 (pinned
  arm shown 4.1466); lead 12 declined, 4.3229 (pinned 4.0431, its placebo 4.0715).
- fire (7,633 rows): lead 0 log_c corrector GLS 0.007303 (helps); leads 6 and 12 declined, 0.008122 and 0.008179
  (pinned 0.007317 and 0.007530).
- defo (640 rows): lead 0 arcsine plain 0.002759 (cannot tell); 1-year lead arcsine plain 0.002804 against its
  trees-off 0.002802 (cannot tell); persistence 0.002744, predict-zero 0.003082.
- NDVI (7,336 rows): lead 0 identity plain 0.038714 (cannot tell); leads 6 and 12 declined, 0.038244 and 0.038169.

**Timings per lead** (two banks now): pm25 7.6-7.8 s (was 5.3-5.8 with one bank), fire 8.8-9.0 s (was 6.7-6.9),
defo 4.0 s (was 3.2), NDVI 22.9-23.4 s (was 14.2-14.5). Run folders: pm25 36 MB, fire 23 MB, defo 1.5 MB, NDVI
19 MB. Every `lead.json` now also holds `guard_fits` (the guard bank, its cut, its history block),
`fallback_levels` and `issue_features_missing`. No `issue_missing_rows.parquet` was written, because no row was
left out.

**Tests.** The full suite passes: 2,900 passed, 2 skipped, 74 expected failures (the known real-package derive items), 0 failed, in 21 min (`py -3.9 -m pytest` from `engine/`). New tests: the I1 lead set (and nothing of a
lead 1 or 3 written); H4 with planted absent issue rows (absent from the scores and common rows, present in the
saved rows with the flag, counted per unit and lead, and their NaN context never reaches G1's refusal); a guard
row without its issue row refuses; the H2 assertion is live (a guard handed the fit-cut bank refuses); H5 on the
sparse package with the search threshold stood in at 1 unit (each lead's level is the argmin of its own surface,
and the test pass and the placebo read it).

### Must-reads from the H build

**ATTENTION H-1: H2 flipped two smoke guards.** pm25's lead 6 now FAILS its guard (it passed with the fit-cut
bank). Defo's 1-year lead now PASSES (it failed). pm25's flip is the pattern H2 removes: with a bank that had
seen the guard rows' labels, the pinned arm looked 2.5% better than its trees-off on the guard; without that,
it is 3.2% worse. These are smoke-size numbers and carry no sign information.

**ATTENTION H-2: three readings of the rulings await you** (departure `ladder_h_readings`; `ladder.json`
readings):
- (a) H2 names the bank, the correctors and the guard history block. I kept the guard's c, R36 tolerances and GLS
  weight model at the lead's FIT cut, exactly as the nowcast's inner decision reads them under L6 b.
- (b) I read H4 as "the issue row t - L is absent" (the case departure ladder_readings c described). A test row
  whose issue row exists keeps R30's 0-fill for a missing tree feature and G1's refusal for missing context.
  Under the dense census, a test row's issue row always lies inside the coverage at leads up to 12 months, so
  the count is 0 on all four packages by construction. Only the planted test exercises the path.
- (c) H4 names test rows. A GUARD-surface row whose issue row is absent refuses loudly (never scored on NaN
  features, never left out without a ruling). Rule whether H4 also leaves such guard rows out.

**ATTENTION H-3: APP_PLAN.md outside Sections 4.5 and 8.0 still carries the old leads and hours.** My write scope
was 4.5's hours and the 8.0 run row only. These lines still say 1/3/6/12 or 42.5-55 h: "In short" (lines 24, 26,
36), 2.1 R10 (230), 3.1 C6 (289), 3.2 leads row (323), 8.1 M6 (799) and its note (810), 9.1 item 6a (852) and the
risks list (895). The re-priced total is 41.3 / 53.8 h. If every ladder bank is priced as the full bank the
engine fits (placebo correctors included), with 2 router arms per lead, it is 46.2 / 58.7 h.

The must-reads of sections 5 and 6 that still stand: G1-c (G1 filters only the per-unit router's fit rows).
G1-a stays as built, and G1-b is done.

## 8. The four drafts re-run after the review of the H build (2026-10-05, later again)

The review of section 7 raised seven items. This build fixes the ones that needed no owner answer, narrows one of
the readings with an earlier ruling, and counts what the owner needs to decide the rest. No number moved: every
nowcast file, every lead's guard rows and every lead's saved test rows are the same bytes as in section 7.

| Package | Result | Wall time | Peak RAM | Run folder (under `D:\treeroute\runs\`) |
|---|---|---|---|---|
| pm25_draft | **ran**: nowcast + leads 6 and 12 | 70 s | 3.07 GB | `pm25_draft\smoke61005_e81504ec` |
| fire_draft | **ran**: nowcast + leads 6 and 12 | 70 s | 3.02 GB | `fire_draft\smoke61005_8dbce268` |
| defo_draft | **ran**: nowcast + one 1-year lead (6 and 12 months merge) | 24 s | 0.42 GB | `defo_draft\smoke61005_dbb684e3` |
| ndvi_draft | **ran**: nowcast + leads 6 and 12 | 131 s | 3.87 GB | `ndvi_draft\smoke61005_9e27b901` |

The lowest free RAM was 6.95 GB of 15.8 (NDVI). Peak RAM is the same as in section 7 (a smoke bank is only 48
trees). Earlier this morning a first pass of these smokes ran on the same code less one docstring edit
(`pm25_draft\smoke61005_30f08930`, `fire_draft\smoke61005_471e34d4`, `defo_draft\smoke61005_683e30af`,
`ndvi_draft\smoke61005_86517fd3`). Every prediction and record file in them has the same bytes as in the runs
above; only the run-identity files differ (fingerprint, locks, timings). They are superseded, and I did not delete
them.

**What changed in the engine.**
- **The nowcast's banks are released before the leads run** (review item 7). `RunState.release_bank` closes a
  nowcast bank's store (its temp files are deleted, loudly), empties that bank's own exit stack so no reference
  to its trees survives, and drops the bank, store and masks from the run state. `Ladder.run` releases the
  inner-cut bank when the ladder starts (the decision is locked and the test pass has written `tables.json`),
  and the fit-cut bank once the lead-0 contract is done (or found done on resume). So while a lead's guard runs
  there are two banks in memory (the lead's fit-cut bank and its H2 guard-cut bank), the same as the nowcast's
  decision (fit-cut and inner-cut), not four. Recorded per lead (`lead.json` guard `nowcast_banks_held` = [],
  `banks_in_memory` = 2) and in run.log (two "released the nowcast's ..." lines, before the contract and before
  the first lead). With A7's inner refit off (L6 a) the inner names alias the fit-cut bank, and releasing them
  drops only the alias. At smoke size a bank is 48 trees, so peak RAM did not move; bank RAM at headline size is
  still unmeasured, and the RAM preflight still counts no bank.
- **Reading (a) is narrowed by an earlier ruling.** The guard's fit-cut c is not a reading: ruling D63 a (one c
  per lead, from its FIT cut, serves that lead's guard surface and its test pass) puts it there, and
  `layer.c_for_cut` already refuses guard-cut donor rows. R36's tolerances are the identity-check tolerances and
  move no prediction. What is left is one item: a weighted pin's guard GLS weight model reads its error target's
  tree answers from the lead's fit-cut bank, exactly as the nowcast's inner decision does
  (`fit.weights.L6_ANSWERS_DISCLOSURE`, "owner ruling pending"). L6 b as ruled names the bank and correctors;
  L6's add-on (the inner GLS target on the refit bank, +0.9-2.4 h over the nowcasts) was priced separately and is
  not ruled. One owner answer covers the nowcast and every lead. The reading is now `guard_gls_answers`
  (`guard_c_tolerances` is gone), and only fire's pin is weighted among the four drafts.
- **Reading (b) now has numbers.** Each lead counts the test rows whose issue row EXISTS but holds a non-finite
  moved tree feature (read 0-filled by the trees, R30, and scored) or context value (refused if scored, G1):
  `lead.json` fits `issue_features_partly_missing` (by column), the contract record for lead 0, and
  `ladder.json` `issue_features_partly_missing` by lead. Nothing is left out for them.
- Readings (c) (a guard row without its issue row refuses) and the separate H4 file stay as built: they need the
  owner or a change in report/.
- `APP_PLAN.md`: the 14 lines outside 4.5 and 8.0 that still said 1/3/6/12, 30/91/183/365 or 42.5 / 54.8 h now say
  6 and 12 months plus the nowcast, 183 and 365 days, and 41.3 / 53.8 h (46.2 / 58.7 h as built), each with
  "re-priced 2026-10-05" or "owner ruling I1, 2026-10-05" and the old value beside it. The run end at 8 machine
  hours a day moves from "Thu 5 - Sun 8 Nov" to "Thu 5 - Sat 7 Nov" (61-80 h with the buffer, was 62-87 h).
- The re-pricing script and its CSV are now kept at `D:\treeroute\loro_measure\reprice_h2_i1.py` and `.csv`. The
  script runs the cost model from a temporary copy, so `loro_cost_model.py`, `units_census.csv` and
  `loro_components.csv` are never rewritten (their SHA-256 and dates are unchanged). Re-run there, it gives
  41.3 / 53.8 and 46.2 / 58.7 h again, and the same CSV byte for byte as the session copy.

**Test rows whose issue row exists but holds a non-finite feature** (all with finite context; out of 7,680 test
rows, 640 on defo):

| Package | Lead 0 (the nowcast's own rows) | Lead 6 (defo: 1 year) | Lead 12 | Main columns at the leads |
|---|---|---|---|---|
| pm25 | 0 | 3 | 3 | spi_01m |
| fire | 1,366 | 1,217 | 1,205 | aridity_index_p_pet (987 / 974), snow_cover_fraction (343 / 344), deeprec_twsa, fert_n, fert_p, travel_time (48 each) |
| defo | 506 of 640 | 455 of 640 | (one lead) | esacci_sm_max, _mean, _min (313 each), nighttime_lst_C_max (273) |
| NDVI | 5,635 | 5,706 | 5,740 | the esacci_sm lags (about 3,570-3,705 rows each) |

**Checked on these runs (read-only, by SHA-256 against the section 7 runs).**

| Check | pm25 | fire | defo | NDVI |
|---|---|---|---|---|
| Lead-0 contract: pool, pre-clip, trees-off identical; largest gap | yes; 0.0 | yes; 0.0 | yes; 0.0 | yes; 0.0 |
| Nowcast files, each lead's test_preds, guard_preds and lead adoption, the ladder table: same bytes as section 7 | yes (14 files) | yes (14) | yes (11) | yes (14) |
| verdict.json: only the departure text, the run fingerprint and the timings differ | yes | yes | yes | yes |
| lead.json / ladder.json / contract: only added fields, plus the H2 rule text and the readings | yes | yes | yes | yes |
| Inner-cut bank released before the contract, fit-cut bank before the first lead (run.log) | yes | yes | yes | yes |
| Banks in memory at each guard (lead.json) | 2 and 2 | 2 and 2 | 2 | 2 and 2 |
| Guard rows inside the guard bank's label window | 0 and 0 | 0 and 0 | 0 | 0 and 0 |
| Test rows left out by H4 | 0 | 0 | 0 | 0 |
| Guard results (pass or fail, MAEs) | as section 7 | as section 7 | as section 7 | as section 7 |
| Anything of a 1- or 3-month lead written | no | no | no (its `lead_1` is the 1-year lead) | no |

**Tests.** The full suite passes: 2,904 passed, 2 skipped, 74 expected failures (the known real-package derive
items), 0 failed, in 21.5 min (`py -3.9 -m pytest` from `engine/`). One docstring edit in pipeline/ladder.py landed
while the suite ran; the final smokes above ran after it. Four new tests: the bank release (weak references to a
released bank's trees and store die, a second release is a no-op, an unknown name refuses, every temp file is
gone); the run.log order of the releases on the synthetic package; the L6 a alias case; and the partly-missing
count on four planted test rows (counted by column, kept, the issue row still present). The ladder smoke test now
also checks `banks_in_memory` = 2, the new readings and the per-lead counts.

### Must-reads from the review fixes

**ATTENTION R-1: H4's reading (b) decides whether a large share of rows leaves the leads.** Read narrowly (as
built), H4 leaves out a test row only when its issue row t - L is absent: 0 rows on all four packages. Read
broadly ("issue-step features are missing" = any non-finite feature), it would leave out the rows in the table
above: about 1 in 6 of fire's lead rows, 7 in 10 of defo's and NDVI's, and 3 of pm25's. The nowcast scores the
same kind of rows (lead 0 column), so a broad H4 applied only at the leads would score the nowcast and the leads
on different row rules and shrink the common rows the ladder compares on; applied to the nowcast too, it would
remove 18% of fire's, 79% of defo's and 73% of NDVI's nowcast rows. Departure ladder_readings c, which H4 answers, asked about the
absent issue row only. Please confirm the narrow reading, or rule the broad one (and whether it covers lead 0).

**ATTENTION R-2: one H2 item is left, the weighted pin's GLS answers** (`guard_gls_answers`; the nowcast's
`L6_ANSWERS_DISCLOSURE` is the same question). Confirm the fit-cut bank's answers, or move both the nowcast and the
leads to the refit bank (+0.9-2.4 h over the nowcasts by the 2026-09-28 pricing; the ladder's share is not priced).

Still open from before: reading (c) (guard rows without an issue row refuse), the H4 rows' separate file, G1-c.

---

## 9. Smokes on the final code (2026-10-05, 09:04-09:11)

**Result: all four ran end to end on the final code. Every saved prediction and score file has the same bytes
as in section 8.** The engine code has not changed since section 8's runs. The newest engine file is
pipeline/ladder.py, edited at 08:34, and section 8's runs started at 08:56. So the run fingerprints are the same.

**ATTENTION 9-1: the command as given refuses, by design.** `py -3.9 -m treeroute smoke datasets/pm25_draft`
stopped after 20 s with exit code 4, before any fit:

```
treeroute smoke refused: ResumeRefusal: [G-NOOVERWRITE] the run with this fingerprint already finished:
D:\treeroute\runs\pm25_draft\smoke\20261005_e81504ec Fix: nothing to do; its outputs are final
```

It wrote nothing: no folder and no lock, and the temp folder stayed empty. The other three would refuse the same
way, because section 8's runs already hold their fingerprints. To get a fresh run of the final code, I ran each
smoke once into a separate run root, using the engine's own option:

```
py -3.9 -m treeroute smoke datasets/<package> --run-root D:/treeroute/runs_final_check
```

I did not add a second folder to `D:\treeroute\runs`. Two folders with one fingerprint in the same kind folder
make every later start there refuse ("more than one run folder matches"). The new root holds 77 MB. Nothing else
was written apart from this section and scratch files.

| Package | Result | Leads run | Wall time | Peak RAM (process tree) | Lowest free RAM | Run folder (under `D:\treeroute\runs_final_check\`) |
|---|---|---|---|---|---|---|
| pm25_draft | **ran**, exit 0 | nowcast (lead-0 contract) + 6 + 12 | 62 s | 3.22 GB | 8.4 GB | `pm25_draft\smoke\20261005_e81504ec` |
| fire_draft | **ran**, exit 0 | nowcast (lead-0 contract) + 6 + 12 | 69 s | 3.22 GB | 8.4 GB | `fire_draft\smoke\20261005_8dbce268` |
| defo_draft | **ran**, exit 0 | nowcast (lead-0 contract) + one 1-year lead (6 and 12 months merge) | 23 s | 0.49 GB | 11.1 GB | `defo_draft\smoke\20261005_dbb684e3` |
| ndvi_draft | **ran**, exit 0 | nowcast (lead-0 contract) + 6 + 12 | 131 s | 4.11 GB | 7.5 GB | `ndvi_draft\smoke\20261005_9e27b901` |

How the runs were watched:
- Before each smoke, the watcher checked that no other Python job was running. None was.
- It then sampled the working set of the whole process tree every 0.25 s. The private-bytes peaks were 3.52,
  3.49, 0.75 and 4.37 GB.
- Free RAM was 11.6 GB at each start. D: had 49.4 GB free before the first smoke and 49.3 GB after the last.
- Each run emptied `D:\treeroute\tmp` and left no lock.
- The peaks are 0.07-0.24 GB above section 8's for the same computation. Working-set peaks vary from run to run.

**Same bytes as section 8.** I compared each file read-only by SHA-256 against section 8's folder with the same
fingerprint.
- Every parquet and CSV file is identical in all four runs. In total, 37 of 59 files are identical for pm25,
  39 of 61 for fire, 33 of 52 for defo and 39 of 61 for NDVI.
- The files that differ (22; 19 for defo) are run-identity files. I compared them value by value. What changed:
  - timestamps (created, locked, labels opened, finished);
  - the process id;
  - the phase timings and the store build seconds;
  - the temp-store paths;
  - two added argv entries (`--run-root ...`) in manifest.json.
- No other value changed. Each lead's adoption file, `test_preds`, `guard_preds` and `lead.json` are identical.
  So are `ladder.json`, the contract record and the ladder table.

**Guard banks and adoption per lead (H2, H5).** Each lead refit its bank at the lead's guard cut (`refit: true`,
48 trees). It held 2 banks in memory at the guard and none of the nowcast's banks. Its `lead.json` carries the H2
assertion. The lead-0 contract holds in all four runs (largest gap 0.0).

| Package | Lead | Fit cut | Guard cut = guard bank cut (bank's newest label) | First guard row | Guard rows in that bank's label window | Guard: pinned arm vs its own trees-off (guard MAE) | Adopted at the lead | H5 fallback level |
|---|---|---|---|---|---|---|---|---|
| pm25 | 6 | 2019-07 | 2016-07 (2016-07) | 2017-01 | 0 of 4,959 | log_c corrector 3.4781 vs 3.3708: failed | identity trees-off (decline target) | 1.0, the centre (0 fallback units) |
| pm25 | 12 | 2019-01 | 2016-01 (2016-01) | 2017-01 | 0 of 3,999 | 3.4092 vs 3.2970: failed | identity trees-off; placebo built | 1.0, the centre (0) |
| fire | 6 | 2018-07 | 2015-07 (2015-06) | 2016-01 | 0 of 4,773 | log_c corrector GLS 0.0051300 vs 0.0049682: failed | identity trees-off | 1.0, the centre (0) |
| fire | 12 | 2018-01 | 2015-01 (2014-12) | 2016-01 | 0 of 3,830 | 0.0055323 vs 0.0054375: failed | identity trees-off; placebo built | 1.0, the centre (0) |
| defo | 1 year | 2019 | 2016 (2016) | 2017 | 0 of 480 | arcsine plain 0.0034534 vs 0.0034563: **passed** | arcsine plain; placebo built | none (region router: no R12 fallback; the nowcast records none either) |
| NDVI | 6 | 2019-07 | 2016-07 (2016-06) | 2017-01 | 0 of 4,591 | identity plain 0.043363 vs 0.042768: failed | identity trees-off | 1.0, the centre (0) |
| NDVI | 12 | 2019-01 | 2016-01 (2015-12) | 2017-01 | 0 of 3,671 | 0.044517 vs 0.043909: failed | identity trees-off; placebo built | plain and corrector: 1.0, the centre (0) |

In fire and NDVI, whose history starts at t-2 (R17), a bank's newest label sits one step before its cut. This holds
for the fit-cut banks too.

Time per lead (two banks each): pm25 7.2 and 7.5 s, fire 8.5 and 8.8 s, defo 3.8 s, NDVI 22.7 and 22.9 s.

**H4 counts.**
- Test rows left out because their issue row is absent: 0 at every lead in all four packages. No
  `issue_missing_rows.parquet` was written.
- Guard rows without an issue row: 0.
- Test rows whose issue row exists but holds a non-finite tree feature (reading (b): counted, kept and scored):

  | Package | Lead 0 | Lead 6 (defo: 1 year) | Lead 12 |
  |---|---|---|---|
  | pm25 | 0 | 3 | 3 |
  | fire | 1,366 | 1,217 | 1,205 |
  | defo | 506 of 640 | 455 | - |
  | NDVI | 5,635 | 5,706 | 5,740 |

  No such row had a non-finite context value. These counts are the same as in section 8.
- G1 fired only at NDVI lead 12:
  - 920 fit rows were left out at the guard (of 23,842) and 920 at the test pass (of 29,347). All 160 units lost
    rows.
  - No unit was flagged. The record names the constant `C10.context_missing_flag_share` (0.05).
  - The rows are saved in `context_missing/lead_12_guard.parquet` and `lead_12_test_pass.parquet`.

**Test MAE beside the baselines (common rows; plumbing only).** At smoke size these numbers carry no sign
information. `*` marks the adopted column. Persistence is defined only for leads of at least one step.

| Package (rows) | Lead | *Adopted | Pinned arm shown | Its trees-off | Guess-normal | Last-5 normal | Persistence | Damped persistence | Predict-zero | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| pm25 (7,678) | 0 | log_c corrector 3.7231 | - | 4.1108 | 4.2540 | 3.7293 | - | - | 21.888 | helps |
| | 6 | identity trees-off 4.3020 | 4.1466 | - | 4.3020 | 3.8551 | 10.181 | 4.2549 | 21.888 | declined |
| | 12 | identity trees-off 4.3229 | 4.0431 (placebo 4.0715) | - | 4.3229 | 3.8702 | 4.1130 | 4.0248 | 21.888 | declined |
| fire (7,633) | 0 | log_c corrector GLS 0.007303 | - | 0.007321 | 0.008052 | 0.007620 | - | - | 0.008635 | helps |
| | 6 | identity trees-off 0.008122 | 0.007317 | - | 0.008122 | 0.007746 | 0.017054 | 0.008172 | 0.008635 | declined |
| | 12 | identity trees-off 0.008179 | 0.007530 (placebo 0.007530) | - | 0.008179 | 0.007828 | 0.014130 | 0.008289 | 0.008635 | declined |
| defo (640) | 0 | arcsine plain 0.002759 | - | 0.002802 | 0.003599 | 0.004209 | - | - | 0.003082 | cannot tell |
| | 1 year | arcsine plain 0.002804 | (adopted; placebo 0.002806) | 0.002802 | 0.003599 | 0.004209 | 0.002744 | 0.003372 | 0.003082 | cannot tell |
| NDVI (7,336) | 0 | identity plain 0.038714 | - | 0.038072 | 0.038072 | 0.039128 | - | - | 0.42797 | cannot tell |
| | 6 | identity trees-off 0.038244 | 0.038666 | - | 0.038244 | 0.039782 | 0.25753 | 0.038453 | 0.42797 | declined |
| | 12 | identity trees-off 0.038169 | 0.038370 (placebo 0.038289) | - | 0.038169 | 0.039682 | 0.087350 | 0.038558 | 0.42797 | declined |

Some persistence columns cover fewer rows. They lack a readable issue label: pm25 lead 6 has 7,677, fire 7,590
and 7,605, NDVI 6,992 and 7,164.

**Small things seen (no fault).**
- `manifest.json` `machine.run_root` records the machine file's `D:/treeroute/runs`, while the run went to the
  `--run-root` folder. Only `argv` records the override, so a reader of the manifest alone would look in the
  wrong root.
- The run-folder paths in section 8's table are garbled (`smoke61005_...` stands for `smoke\20261005_...`). This
  section is append-only, so I left them.

Still open from section 8: R-1 (the scope of H4 reading (b)), R-2 (the weighted pin's GLS answers), reading (c)
(guard rows without an issue row refuse), the H4 rows' separate file, and G1-c.

## 10. pm25_draft plan at full size on the streaming census (2026-10-06, 03:38-04:56)

**Result: the old refusal is gone, but the plan now stops at the next RAM check.**
`py -3.9 -m treeroute plan datasets/pm25_draft` read the whole target file by file and passed the census RAM
check. After 31 minutes it refused (exit code 4) at a second check: the picked units' column reader would need
16.4 GB. It wrote nothing. I did not start `treeroute run`.

Before the run, a watcher checked that no other Python job was running. It waited until no Python process had
run for 3 minutes, because another workflow was running smokes and tests. At the start, 11.0 GB of RAM was
available and D: had 49.1 GB free.

| Step | Time | Result |
|---|---|---|
| Load, groups, census pre-flight | 15 s | 127 groups; census estimate 3.83 GB: go. A report-only line already warned: "at the per-unit kind ... 16.4 GB at its peak, 9.8 GB available now; WARNING: at the per-unit kind this run will be refused after the census" |
| Census (every target row, one file at a time) | 1,398 s (23.3 min) | 537,232,608 rows, 2,034,972 units, 127 groups, 264 months; 2,794 target files, 5,588 driver key files |
| Derive up to the unit picks (R1-R18) | 435 s | router per_unit; 12,700 bank units |
| RAM check before the picked units' rows are read | - | **refused** |

```
treeroute plan refused: PipelineRefusal: [G-DISK] the picked units' working set (3352800 target rows, 102 frame
columns, a column reader at its peak) needs about 16.4 GB of RAM ([G-DISK] RAM needs 16.4 GB, 8.6 GB available:
free 7.9 GB (close other programs) ...) Fix: free RAM (close other programs); the run size is never reduced;
nothing is computed and no run folder is opened
```

- **Peak RAM of the plan** (whole process tree, sampled every 0.25 s): 3.16 GB working set and 3.80 GB private
  bytes (2.94 and 3.54 GiB), both during the census. After the census the peak was 2.36 GB. The engine prints GiB
  (2^30 bytes) as "GB", so its 3.83 estimate covers the 3.54 GiB measured. The lowest free RAM was 7.8 GB.
- Nothing was left behind. There is no folder under `D:\treeroute\runs\pm25_draft\headline`, `D:\treeroute\tmp` is
  empty, the lock was released, and D: had 49.11 GB free before and after.

**Does it pass G-DISK now? Partly.** The check that stopped the owner's command is gone: it held the whole target
in RAM (about 60 GB), and the census held at most 3.8 GB. The plan still fails the next G-DISK check. Closing
programs cannot help: 16.4 GB is more than the machine's 15.8 GB in total.

**ATTENTION 10-1: the picked units' column reader does not fit this machine.**
- What it is: R30 needs the tree features (lagged, last-value filled) on the bank units' rows. The engine reads
  them through ONE reader that holds every picked unit's whole history: 127 groups x 100 bank units (C7) x 264
  months = 3,352,800 rows, with 102 columns. The run would later read the same reader for the pool and the ladder.
- Its size: 16.4 GB by the engine's estimate, or 12.6-13.2 GiB by the measured bytes per row (4.05-4.24 KB at the
  peak). Once built it holds about half that.
- This build already lists it as a limit ("the reader is not built in unit chunks"), and the pre-flight warned
  before the census. So the guard did its job; this is not a bug.
- Options (owner's choice):
  - (a) **Build the reader in unit chunks.** R30's donor shares and the last-value counts become counts summed over
    chunks and divided once, as R30's test-year count already does. The pool and the ladder would be written
    chunk by chunk. This gives the same bytes ONLY if each unit's feature-script outputs depend on that unit's
    rows alone. The pm25 script says so (same-unit lag), but the engine does not check it, so this needs a check
    like the test-year window check. It is a new build covering plan, pool and ladder.
  - (b) Make the reader leaner. It peaks at about twice what it holds, and even the held size (6.4-7 GB) beside
    the census and the banks is not enough alone.
  - (c) Fewer bank units per group (C7 = 100). That changes numbers, so it needs an owner ruling.
  - (d) A machine with 32 GB of RAM or more.

**Derived settings (from a scratch script, not from the plan command).** The plan writes no derived.json when it
stops. To show the settings anyway, I ran the engine's own steps 1-2 in a scratch script (`derive_to_r30.py`:
read-only, no lock, no run folder). It ran the same census and both derive passes; the second pass withholds the
labels before Y0. Two things differ from the plan:
- The RAM guard ran and its refusal was recorded (the same message), but the picked units' LABEL rows, which are
  small, were read anyway.
- Each pass stopped where R30 asks for the column reader. So R30 is not derived; the 30 entries before it are.

I checked the script first on 4 whole groups (71,390 units): its 30 entries equal the engine's own full derive,
value for value. Its price block there used 100 trees per group, before I fixed it to read the run's tree count;
the smoke's 12 trees give the engine's 0.28 GB. The full-size pass took 2,455 s, with a peak of 2.97 GiB.

| Setting | Value |
|---|---|
| Cadence (R1), season (R2) | monthly, month of year |
| Y0 (R4), coverage end (R3) | 2003, 2023 (R4 carries the flag lag_operation_not_counted) |
| Windows (R5-R7) | inner fit 2003-2016, inner score 2017-2019, train end 2019, test years 2020-2023 |
| Leads (R10), cuts (R11) | 6 and 12 months plus the lead-0 contract; fit cuts 24240 / 24235 / 24229, guard cuts 24204 / 24199 / 24193 (leads 0 / 6 / 12) |
| Lags (R8) | 74 columns: 45 at 0, 14 at 1, 12 at 2 and 3 at 3 months |
| Router kind (R12) | per_unit: 2,028,667 candidate units, median 168 inner rows (minimum 83), 0 fallback units; constant-history share 0.0 |
| Router design (R14) | 35 grid points, centre trees 0.5 / context 0.25; context ctx:month, ctx:lat |
| History columns (R17) | hist_last_1-3, hist_mean_12, hist_mean_60, hist_mean_all |
| Units (R18) | 100 bank units in each of the 127 groups (12,700) and 15 scored units in each (1,905), K = 20 group equivalents; event rate 0.09999 (q90 42.64 over 413,787,522 donor rows) |
| Bank (R19) | 100 trees per group (12,700 trees); bag 10,200 rows (10,199 in 3 groups, 10,178 in 1); inner-cut refit bag 8,400 |
| Batching (R20) | per group; fallback rows: none |
| Links (R22), log_c c (R23) | identity and log_c; c = 1.5 at every lead |
| Clip (R28) | [0, inf) |
| Labels before Y0 withheld (second pass) | 24,419,664 rows (24,343,717 valid) |

These are the settings the cost model assumed for pm25:
- 127 groups, with 100 bank and 15 scored units per group;
- 168 / 36 / 204 / 48 / 252 rows per unit;
- 2 links, a bag of 10,200 and 2 leads.

Only the feature count is lower: 93 tree features plus 6 history columns make 99, where the model has 111.

**Price of the full run.**
- **Machine hours.**
  - Compute: 8.6 h measured / 11.7 h conservative (the cost model, re-priced 2026-10-05: nowcast 4.9 / 6.4,
    ladder 3.2 / 4.5, lead-12 placebo 0.5 / 0.8). Add 1.0 / 2.2 h of weight refits only if a weighted pin is
    adopted. With 99 features instead of 111, the bank lines are about 11% high.
  - On top come the streamed data passes. Every command makes them: run repeats plan's steps 1-2 and checks
    derived.json. Measured today: 31 min up to the picks (the census took 22-23 min).
  - Not measured: R30's test-year count (about 1.5 h, scaled from 188 s on 4 whole groups) and the build of the
    picked reader. So each command adds about 2-2.5 h, and plan plus run add about 4-5 h.
  - In all: about 13-14 h measured / 16-17 h conservative. That assumes the RAM and disk checks pass, which they
    do not.
- **RAM.**
  - Census: 3.2 GB (measured).
  - Picked column reader: 16.4 GB (estimated; does not fit).
  - R30's test-year blocks: sized to half the free RAM, so they adapt.
  - Banks of 12,700 trees: not measured (the RAM pre-flight counts none).
- **Disk.** On these settings the run's own disk pre-flight asks for **638.5 GB** in `D:\treeroute\tmp`, with 45.7
  GB free, and would refuse:
  `[G-DISK] disk at D:\treeroute\tmp needs 638.5 GB, 45.7 GB free: free 592.8 GB`.
  The parts (GB):
  - the pool: 1.3;
  - tables over the scored rows (5 kinds): 113.6;
  - tables over the bank rows: 151.4;
  - one forecast lead: 372.2, of which 302.8 are two more bank-row tables.

**ATTENTION 10-2: even with the RAM fixed, `treeroute run` would refuse at its disk check.**
- The bank-row tables, 454 GB of the 638.5, are counted for every group. The per-unit router needs them only for
  fallback groups, and this run has none (R20:fallback_rows is empty). Without them the run still needs 184 GB:
  four times the free space.
- The cost model assumed the tables are rebuilt to fit a 47 GB budget. The engine builds every group's tables of
  a kind and keeps them all on disk at once.
- Options: build and drop the tables group by group (or the rebuild rule the model priced); count the bank-row
  tables only for fallback groups; or add disk. These are build items, not changes to numbers.

**Tests.**
- `tests/test_census.py` and `tests/test_pipeline_census.py`: 40 passed (04:57, after these runs).
- The full suite from 02:24, before these runs: 3,068 passed and 17 failed. All 17 are package tests of datasets/
  (defo catalog, ban lists, draft copies, closed world), which another workflow was editing at the time. None is
  in the census, stream or pipeline tests.

**Files.** No engine code changed in this session. The plan's log and watcher summary, the two scripts and the
scratch derive's outputs (`derived_to_r30.json` and `summary.json`, at full size and for the 4-group self-check)
are kept in `D:\treeroute\runs\_G_DISK_plan_pm25_20261006\`.

## 11. Acceptance: 3-group full-width probes, ruling-M2 checks and the full suite (2026-10-06, 16:45-19:40)

Owner rulings M1-M3 (OWNER_RULINGS_2026-10-06.md). Everything below ran on a FROZEN SNAPSHOT of the engine and the
packages, taken at 16:45:41: `D:\treeroute\acceptance_20261006\snap\engine` (engine_code_sha256 a9a1b1870009, the
same as the live engine at that moment). It holds the packages and the engine BEFORE ruling N (the sign-off answers,
19:21), which the other workflow began writing into the live tree at 19:36.

- Scratch: `D:\treeroute\acceptance_20261006\` (0.97 GB: snapshot 230 MB, probes 277 MB, suite basetemp 460 MB, checks 1 MB).
- I changed no engine file, no package and no live constant, wrote nothing under a protected root and deleted
  nothing.

| Step | Result |
|---|---|
| Probe pm25_draft (3 groups, full width) | **ran end to end**, exit 0, 1,420 s (23.7 min), peak 4.17 GB |
| Probe defo_draft (3 groups, full width) | **ran end to end**, exit 0, 2,963 s (49.4 min), peak 6.28 GB |
| Probe ndvi_draft (3 groups, full width) | **did not finish**: exit 4 after 5,675 s (94.6 min). G-DISK refused a block of R30's count when a web browser opened and free RAM fell to 0.3 GB. It was still in derive, and nothing was written |
| Quick check, four real packages | all exit 4, only on owner items (5.4-13.9 s each) |
| Deep check (ruling-M2 R21 subset), four real packages | all exit 4, only on owner items: fire 256 s, pm25 299 s, defo 96 s, NDVI 398 s; each names its 4 R21 groups |
| Full test suite (once) | **3,357 passed, 0 failed**, 4 skipped (opt-in heavy checks), 68 xfailed (known); 43.5 min |

---

### Must-reads

**ATTENTION 11-1: on NDVI, R30's test-year count takes 8-13 hours per command, and the cost model does not count
it** (11.3).
- On NDVI the count reads every unit's whole record. Its window starts before the record because of four
  long-memory feature outputs: api_precip, api_soilmoist, consec_dry_months and months_since_sig_rain.
- Each unit block re-reads its whole group's driver files.
- Measured: 14-15 s a block for a 7-9 M-row group, 26-29 s for yakutia_larch. Scaled to all 133 groups that is 8-13 h,
  on top of NDVI's modelled 14.8-18.2 h. PM2.5's count scales to 1.5-3.3 h.
- Option (a), stop re-reading the group for every block, is a build item gated by byte identity. Otherwise the hours
  stand; skipping a separate `plan` saves one count.

**ATTENTION 11-2: the NDVI probe did not finish: G-DISK refused it after 94.6 minutes, still in derive, when a web
browser opened on the machine and free RAM fell to 0.3 GB** (18:31-18:33).
- The engine refused correctly and wrote nothing.
- So NDVI's fits, router, ladder and scores were NOT proven at full width by a probe. The smokes cover them at smoke
  size (section 9 on the drafts, Part 580 on the real packages).
- I did not re-run it: it needs about 1.5-2 hours with the machine to itself, and the browser was still open. To
  re-run it yourself, with the browser closed:

  ```
  cd D:\treeroute\acceptance_20261006\probes\engine_ndvi\engine
  py -3.9 -u -m treeroute run D:/treeroute/acceptance_20261006/probes/ndvi_draft --run-root D:/treeroute/acceptance_20261006/probes/runs
  ```

  It writes only under `D:\treeroute\acceptance_20261006\probes`.

**ATTENTION 11-3: the derive step's real RAM peak is the census plus up to half the free RAM, not the derive peak the
plan prints.**
- R30's unit blocks are sized to half the RAM free when each group starts. Measured peaks: pm25 3.88 GiB against
  3.69 listed; defo 5.85 against 3.89; NDVI 5.17 against 4.24.
- This is safe while the machine is otherwise quiet, because each block is checked before it is read. But anything
  that grows during a group (a second run, a browser) can make the run refuse, as it did to NDVI.
- Run the headline runs one at a time with nothing heavy beside them. Running several at once is not safe (11.3).

**ATTENTION 11-4: C9 k was UNSET at the snapshot (16:45), so the probes ran on scratch copies of the engine with
k = 5.230771281733543e-08 (the measured candidate).** I never edited the live constant. Since then you answered the
sign-off sheet (ruling N, 19:21, S12 a). At 19:37:45 the other workflow's apply_signoff run set the live constant to
the same value, so the probes used the headline k. The live engine's code hash is now ec584edecb17, no longer the
snapshot's a9a1b1870009.

- pm25 and defo ran end to end at full width on 3 groups (exit 0; 23.7 and 49.4 min). Every row-level prediction file
  exists, the lead-0 contract held byte for byte, and the measured temp disk matched the pre-flight (0.11 and
  0.80 GiB).
- Checks: all four packages are red only on owner items (G-FACTS everywhere, G-CLOSED on fire, defo and NDVI, G-EPOCH
  on fire). Fire's package changed at 18:52 when your history build added
  `ingest/fire_history_store_catalog.yaml`, so its reports are already stale.
- Full suite on the snapshot: 3,357 passed, 0 failed, 4 skipped, 68 xfailed (43.5 min). At 19:36, after it finished, the other workflow started applying the sign-off answers to the live packages (`apply_signoff.py ... --apply`). So the live packages no longer match this snapshot, and every check (and the suite) must run again on the final packages before the freeze.

---

### 11.1 How the probes were set up

- **Packages.** `probes\pm25_draft`, `probes\ndvi_draft` and `probes\defo_draft` are copies of the snapshot's drafts
  (still DRAFT-stamped, never inside `datasets\`). Only split.yaml changed: every group but three is EXCLUDED, with a
  reason, through the package's own `excluded:` list (no new knob). The three groups: the group with the most target
  rows (parquet footer rows of its target files, through the engine's own listing) plus the first 2 in sorted order.

  | Probe | Kept groups (target rows) | Excluded | Rows read by the census |
  |---|---|---|---|
  | pm25_draft | yakutia_larch (22,223,520; the most), alaska_interior_taiga (7,073,880), amazon_basin_brazil (5,174,400) | 124 of 127 | 34,471,800 of 537,232,608 |
  | ndvi_draft | yakutia_larch (22,223,520; the most), alaska_interior_taiga (7,073,880), alaska_north_slope (9,371,736) | 130 of 133 | 38,669,136 of 604,358,304 |
  | defo_draft | siberian_taiga (1,984,975; the most), amazon_basin_brazil (490,000), andes_puna (248,600) | 39 of 42 | 2,723,575 of 14,795,225 |

  - No hash had to be fixed: the loader fingerprints split.yaml but no file pins its hash.
  - NDVI's two `seen_during_design` groups (greece_mainland, thar_desert) were dropped from that list in the copy,
    because G-SPLIT refuses a reported group that is also excluded. The copy's split.yaml says so in a comment.
- **C9 k was UNSET in the snapshot, and `treeroute run` refuses then** (`K.get("C9.guard_tolerance_k")` in
  Pipeline._load). **The probes therefore ran on three scratch copies of the snapshot engine**
  (`probes\engine_<pkg>\engine`) in which line 159 of engine_constants.py sets k = 5.230771281733543e-08 (the
  measured candidate, option a; status 'proposed'). I never edited the live constant. At 19:37:45 the other
  workflow set it to the same value under ruling N (S12 a).
- **Running three at once.** The engine allows one heavy job per temp folder (HeavyJobLock in the machine file's
  temp_dir). Each probe copy has its own config\machine.yaml: run root `probes\runs`, temp folder `probes\tmp_<pkg>`,
  and the real registry (read only, for the protected-roots check). Each run removed its own temp folder at the end.
- **Command** (from each probe engine folder): `py -3.9 -u -m treeroute run <probe package> --run-root
  D:/treeroute/acceptance_20261006/probes/runs`, all three started at 16:58:51 by `probes\watch_probes.py`, which
  sampled each run's process tree (working set and private bytes), its temp folder, free RAM, D: free space and CPU
  every 0.5 s. RAM figures are GB (10^9 bytes) unless marked GiB.

### 11.2 The probes, run by run

**Time per phase** (seconds, from the run's own log lines; the three ran at the same time, so these are shared-machine
times):

| Phase | pm25_draft | defo_draft | ndvi_draft |
|---|---|---|---|
| Load, groups, census pre-flight | 3.5 | 4.7 | 4.3 |
| Census (every target row of the 3 groups) | 113.5 (34.5 M rows) | 15.7 (2.7 M rows) | 118.4 (38.7 M rows) |
| Separability check (R20) | 126.5 | 25.1 | 124.9 |
| R30's test-year count (unit blocks) | 765.3 (31 blocks) | 88.1 (6 blocks) | 5,426 and not finished: 72 + 79 + 117 of about 163 blocks, then refused |
| Group readers, rest of derive_all | 46.9 | 24.4 | - |
| Open the run, pool | 19.3 | 121.4 | - |
| History blocks | 0.6 | 23.0 | - |
| Fits: bank at the fit cut, GLS weight model, bank refit at the inner cut | 81.9 (42 + 5 + 35) | 747.2 (408 + none + 331) | - |
| Decision surface and adoption | 28.9 | 240.7 | - |
| Test pass and scores | 14.2 | 345.9 | - |
| Ladder: lead-0 contract | 16.9 | 192.7 | - |
| Ladder: lead 6 / lead 12 with the placebo (defo: the one merged 1-year lead) | 95.8 / 96.4 | 1,062.9 | - |
| Ladder table, report | 9.5 | 70.1 | - |
| **Total** | **1,419.7 (23.7 min)**, exit 0 | **2,962.5 (49.4 min)**, exit 0 | **5,675.0 (94.6 min)**, exit 4 |
| Of which the data passes (census, separability, R30 count, readers) | 1,052 (74%) | 153 (5%) | 5,670 (all) |

Each bank of 300 trees (100 per group, with correctors and placebo correctors): pm25 32-42 s (0.11-0.14 s a tree;
plan 4.5's logged rate is 0.147), defo 299-408 s (1.0-1.4 s a tree; the cost model prices defo's bank at 1.67 s a
tree). Each run fits 6 banks (pm25: fit cut, inner cut, and a lag bank plus a guard bank per lead) or 4 (defo).

**RAM, temp disk and the pre-flight estimates**

| | pm25_draft | defo_draft | ndvi_draft |
|---|---|---|---|
| Census RAM estimate (go) | 2.48 GiB | 2.40 GiB | 2.49 GiB |
| Derive peak the plan lists (census + the largest group's reader) | 3.69 GiB | 3.89 GiB | 4.24 GiB (report-only line) |
| GLS peak the plan lists | 0.07 GiB (matrix 0.02 GiB) | none (region kind) | - |
| **Measured peak, whole process tree** (working set / private) | **3.88 GiB** / 4.47 GiB (4.17 / 4.80 GB) | **5.85 GiB** / 6.24 GiB (6.28 / 6.70 GB) | **5.17 GiB** / 6.05 GiB (5.55 / 6.49 GB) |
| Where the peak fell | R30's test-year blocks | R30's test-year blocks | R30's test-year blocks |
| Temp disk estimate (per-group schedule) | 0.11 GiB | 0.80 GiB | - |
| **Measured temp disk peak** | **0.11 GiB** (0.118 GB) | **0.80 GiB** (0.853 GB) | 0 (no run folder opened) |
| Run folder | 66.8 MB | 80.7 MB | none |

The measured peaks are above the listed derive peak (pm25 +0.2 GiB, defo +2.0 GiB). The cause is by design, but the
plan does not list it: R30's test-year count sizes each unit block to half the RAM free at the start of each group
(pipeline/run.py `_block_row_budget`), on top of the census. So the derive peak is the census plus up to half the free
RAM, and it adapts to whatever else runs. Each block is still checked against the RAM free just before it is read; that
check is what stopped NDVI.

**Derived settings** (from each run's derived.json)

| Setting | pm25_draft | defo_draft |
|---|---|---|
| Cadence, season (R1, R2) | monthly, month of year | yearly, constant |
| Y0, coverage end (R4, R3) | 2003, 2023 | 2004 (flag store_first_year_moved_y0), 2023 |
| Windows (R5-R7) | inner fit 2003-2016, inner score 2017-2019, train end 2019, test 2020-2023 | inner fit 2004-2016, inner score 2017-2019, train end 2019, test 2020-2023 |
| Leads (R10), cuts fit / guard (R11) | 6 and 12 + the lead-0 contract; 24240/24204, 24235/24199, 24229/24193 | one merged 1-year lead (6 + 12); 2019/2016 at both |
| Router (R12, R14) | per_unit, constant-history share 0.0; 35 grid points, centre 0.5/0.25; context ctx:month, ctx:lat | region, constant-history share 0.275; 7 grid points, centre 100, fit-row cap 60,000; no context |
| Overlap blocks (R14) | 3 single-group blocks | 3 single-group blocks |
| History (R17) | hist_last_1-3, hist_mean_12, hist_mean_60, hist_mean_all | hist_last_1-3, hist_mean_5, hist_mean_all |
| Units (R18) | 100 bank units per group; scored 100 per group (K = 20 gives 666 over 3 groups, capped at the bank's 100: flag scored_capped) | 4,615 bank units per group (the region kind's R18 count; 4,285 at full size); scored 4,615 (capped) |
| Bank (R19) | 300 trees; bag 10,200 rows (inner cut 8,400) | 300 trees; bag 36,920 (inner cut 29,997) |
| Links, c (R22, R23) | identity, log_c; c = 1.0 at every lead (1.5 at full size) | identity, log_c, arcsine; c = 4.86e-05 |
| Clip (R28), R30 flags | [0, inf); none | [0, 1]; 6 columns over the threshold (V14_mean_albedo_max/mean/min, nighttime_lst_C_max/mean/min) |
| Lags (R8) | 99 columns: 51 at 0, 33 at 1, 12 at 2, 3 at 3 months | 291 columns: 172 at 0, 119 at 1 year |
| Fallback rows (R20) | none | none |

**Every row-level prediction file exists** (rows from the parquet footers):

| File | pm25_draft | defo_draft |
|---|---|---|
| test_preds.parquet | 14,400 rows (300 units x 48 months), 41 columns | 55,380 rows (13,845 units x 4 years), 37 columns |
| inner_preds.parquet | 10,800 rows, 568 columns | 41,535 rows, 94 columns |
| fitctx_log.parquet | 9,015 rows | 318,456 rows |
| ladder/lead_6/test_preds.parquet, guard_preds.parquet | 14,400 and 9,300 rows | - |
| ladder/lead_12/test_preds.parquet, guard_preds.parquet | 14,400 and 7,500 rows | - |
| ladder/lead_1/test_preds.parquet, guard_preds.parquet | - | 55,380 and 41,535 rows |

Both runs also wrote adoption.json with its lock for every lead, test_labels_opened per lead, the score tables, the
guard report, verdict.json and DONE.json. The lead-0 contract held byte for byte in both (pm25 19 columns of 14,400
rows; defo 19 columns of 55,380 rows). H4: no test row lacked its issue row. G1: no fit row was left out (pm25;
defo's region router has no context).

**Results (DRAFT, 3 groups: not headline-eligible, plumbing and timing only).**
- pm25: adopted log_c plain unweighted at level 1.0 ratio 0.0625 (an edge pick). Pooled test MAE 5.494 against its
  trees-off 5.953, guess-normal 6.085, last-5-years normal 5.407 and predict-zero 15.53. Verdict "helps" against its
  trees-off. Leads 6 and 12: the guard failed (4.787 vs 4.488 and 4.432 vs 4.242), so both declined to identity
  trees-off.
- defo: adopted log_c corrector unweighted at level 0.1 (an edge pick). Pooled test MAE 0.002584 against its trees-off
  0.002602, predict-zero 0.002890 and guess-normal 0.004891. Verdict "does not help, equivalent". The 1-year lead's
  guard passed (0.0041664 vs 0.0041760).

**ndvi_draft: refused, honestly, when the machine ran out of free RAM.**
- It ran 94.6 minutes and never got past derive: the census (118 s), the separability check (125 s, 394 feature
  outputs), then R30's test-year count. alaska_interior_taiga took 72 blocks (1,009 s) and alaska_north_slope 79
  blocks (1,178 s). In yakutia_larch, 117 of about 163 blocks were done (3,240 s).
- At 18:33:25 the next block was refused:

  ```
  treeroute run refused: PipelineRefusal: [G-DISK] the picked units' working set (136752 target rows, 900 frame
  columns, a column reader at its peak) needs about 3.52 GiB of RAM ([G-DISK] RAM needs 3.52 GiB, 3.47 GiB
  available: free 0.05 GiB (close other programs) ...) Fix: free RAM (close other programs); the run size is never
  reduced; nothing is computed and no run folder is opened
  ```

- The cause was outside the engine. At 18:31 a web browser (Opera GX) started on this machine. Two minutes later its
  39 processes held about 5.0 GB private (10.8 GB working set), and free RAM fell from 8.7 GB at 18:29 to 0.3 GB.
  Nothing of mine was running then; pm25 and defo had finished. At 18:34-18:38 the fire history build
  (`datasets/fire/ingest/build_history.py datasets/fire D:/fire_history_lag2`, sign-off item S9 a) also ran.
- The engine did what it should: it refused before the block, wrote nothing and left no lock. Its temp folder was
  removed.
- Not re-run. With the machine to itself it needs about 1.5-2 hours, and the owner's browser and then a game were using 5-6 GB. The command is in ATTENTION 11-2.

### 11.3 Was running several at once safe?

**Short answer: it worked for pm25 and defo, but it is not safe for full-size runs. Run the headline runs one at a
time, with nothing heavy beside them.**

What the watcher measured while the three probes ran (16:58:51-18:33:26):

| Resource | Measured | Verdict |
|---|---|---|
| CPU (16 logical) | mean 17%, 90th percentile 28%, peak 98% | never the limit |
| Disk space | temp folders peaked at 0.12 GB (pm25) and 0.85 GB (defo); D: free went from 34.82 to at least 33.77 GB | no problem at probe size |
| Disk reads (HDD) | each R30 block re-reads its group's driver files | the shared resource; see the slowdowns below |
| RAM | the three runs together peaked at 9.47 GB working set (11.04 GB private). Lowest free RAM: about 4.8 GB with only the probes running; 1.7 GB while I ran fire's deep check beside the NDVI probe (17:51-17:55); 0.3 GB when the browser opened (18:33) | the limit; it stopped NDVI |

Why running several at once is not safe at full size:
- The engine allows one heavy job per temp folder (the heavy-job lock, by design: "one heavy job per machine"). The
  probes got around it only because each scratch engine copy had its own temp folder. The real packages share one
  machine file, so a second `treeroute run` refuses at once.
- Every RAM check is taken at a moment: R30's blocks take half the RAM free when a group starts, and the GLS weight
  model checks its peak just before its matrix is built. A job (or a browser) that grows later makes the other refuse.
  That is what happened to NDVI.
- The slowdown from sharing the HDD was modest at probe size:
  - The census read 308,000 rows a second (pm25) and 332,000 (NDVI), against 384,000 alone (Part 581's full pm25
    census): 1.15-1.25x slower.
  - yakutia_larch's R30 blocks took 29.4 s each while defo ran, 31 s while my deep checks ran and 26.4 s alone: about
    1.1x.
  - Less free RAM means smaller blocks, and each block re-reads the group's files. NDVI's alaska_interior_taiga blocks
    held 372 units with three runs going; yakutia_larch's held 518 with two.

**Slowdown against the cost model's per-group share (plan 4.5, re-priced 2026-10-05).** The share is the package's
modelled hours times 3 / G (its group count):

| Probe | Share (measured / conservative model) | Probe wall time | Ratio | What the ratio hides |
|---|---|---|---|---|
| pm25 | 12.2 / 16.6 min (8.6 / 11.7 h x 3/127) | 23.7 min | 1.9x / 1.4x | 74% of the probe was the data passes (17.5 min), which the model leaves out. The compute alone (run folder to finish) took 6.1 min, 0.5x the share: the probe's routers see 200 tree columns, not 12,600, and its tables 300 trees, not 12,700 |
| defo | 62.7 / 85.2 min (14.6 / 19.9 h x 3/42) | 49.4 min | 0.79x / 0.58x | the banks took 48% (1.0-1.4 s a tree, inside the model's 1.67); the region router sees 200 tree columns, not 4,101, so its share of the model is not tested |
| ndvi | 20.0 / 24.6 min (14.8 / 18.2 h x 3/133) | 94.6 min, refused in the data passes | at least 4.7x | everything was R30's test-year count (next paragraph) |

**R30's test-year count in detail (ATTENTION 11-1): the slowest step on NDVI, and not in the cost model.**
- What it is: before any fit, every command (`plan`, and `run` again) counts R30's per-test-year missing shares over
  every target row. It does this group by group, in unit blocks, and each block builds a column reader that re-reads
  the group's driver files.
- On NDVI the count reads each unit's WHOLE record, not just the years near the test window. The window's first year
  comes out as 1997, before the record starts in 2002. The binding columns are the feature outputs api_precip,
  api_soilmoist, consec_dry_months and months_since_sig_rain: their declared backward reach is about 22 years.
  pm25's window starts in 2016, set by spei_24m_lag12.
- NDVI is also wide (900 frame columns, 27,600 bytes a row at a reader's peak, against pm25's 139 columns and 6,292
  bytes), so a block holds few units (372-518 here).
- Measured block times: 14-15 s for the 7-9 M-row groups and 26-29 s for yakutia_larch (22 M rows).
- Scaled to all 133 groups, with blocks sized by 10 GB of free RAM (686 units): about 3,400 blocks and **8-13 hours
  per command**. At the probes' measured block size (518 units) it would be 17.5 h. pm25 by the same method: 1.5-3.3 h
  per command, against Part 581's 1.5 h. Fire: 0.6-1.6 h (236.6 M rows). Defo: minutes.
- So a full NDVI `run` is about 14.8-18.2 h of modelled compute plus 8-13 h of this count, plus the census (about 26
  min) and the group-reader rebuilds. A separate `plan` before it would add the count again.
- Owner's choice (a build item, not a number change):
  - (a) Stop re-reading the whole group for every block. For example, split each group's driver files by unit block
    once (on D:), so each block reads only its own units' rows. The counts are per column and test year, and the lags
    and the last-value fill stay inside a unit, so the result cannot change. It still needs its own byte-identity gate
    against today's count.
  - (b) Accept the hours.
  - (c) Run `run` without a separate `plan`: that saves one count. The freeze's F-PLAN only checks a plan if one
    exists.

### 11.4 Checks on the four real packages (ruling M2)

Command, from the snapshot's engine folder, one at a time: `py -3.9 -m treeroute check datasets/<pkg> --run-root
D:/treeroute/acceptance_20261006/checks/runs`, then the same with `--deep`. Every report carries engine_code_sha256
a9a1b1870009, which equals the live engine as of 18:55. The deep reports name their groups (checked_groups: the R21
smoke groups, ruling M2). That hash held until 19:37:45, when the other workflow changed engine_constants.py (C9 k,
ruling N); the live hash is now ec584edecb17, so F-CHECK-MATCH will need fresh reports anyway. The engine does not
time each guard; the times below are the whole command and its passes.

| Package | Quick check | Deep check (ruling-M2 subset): time, peak RAM | Deep groups (R21) | Refused (deep) |
|---|---|---|---|---|
| fire | exit 4, 6.0 s | exit 4, 256 s (pass 1 224 s, sample 18 s), 5.90 GB; ran beside the NDVI probe | alaska_interior_taiga, amazon_basin_brazil, angola_zambia_fire_belt, australian_bushfire_belt (4 of 40) | G-CLOSED, G-FACTS, G-EPOCH |
| pm25 | exit 4, 5.4 s | exit 4, 299 s (pass 1 259 s, sample 18 s), 5.50 GB | alaska_interior_taiga, amazon_basin_brazil, anatolian_plateau, andes_puna (4 of 127) | G-FACTS |
| defo | exit 4, 6.4 s | exit 4, 96 s (pass 1 82 s, sample 4 s), 1.71 GB; ran beside the NDVI probe | amazon_basin_brazil, andes_puna, angola_zambia_fire_belt, atlantic_forest_brazil (4 of 42) | G-CLOSED, G-FACTS |
| ndvi | exit 4, 13.9 s | exit 4, 398 s (pass 1 324 s, sample 51 s), 5.69 GB | alaska_interior_taiga, alaska_north_slope, amazon_basin_brazil, anatolian_plateau (4 of 133) | G-CLOSED, G-FACTS |

Each guard's status (quick check / deep check; "-" = not part of that check):

| Guard | fire | pm25 | defo | ndvi |
|---|---|---|---|---|
| G-SPLIT | pass / pass | pass / pass | pass / pass | pass / pass |
| G-LINEAGE | flag / flag (13) | flag / flag (13) | flag / flag (27) | flag / flag (12) |
| G-CLOSED | **REFUSE / REFUSE** | pass / pass | **REFUSE / REFUSE** | **REFUSE / REFUSE** |
| G-KEYS | pass / pass | pass / pass | pass / pass | pass / pass |
| G-LAG | pass / pass | pass / pass | flag / flag (the K5 lag-2 note on Y0) | pass / pass |
| G-HIST | pass / pass | pass / pass | pass / pass | pass / pass |
| G-SUPPORT | pass / pass | pass / pass | pass / pass | pass / pass |
| G-FACTS | **REFUSE / REFUSE** | **REFUSE / REFUSE** | **REFUSE / REFUSE** | **REFUSE / REFUSE** |
| G-EPOCH | flag / **REFUSE** | flag / flag | flag / flag | flag / flag |
| G-MISSING (R30) | flag (not judged) / pass | flag (not judged) / pass | flag (not judged) / flag (6 ruled) | flag (not judged) / flag (burn_frac, ruled) |
| G-DERIVED (static scan) | pass / pass | pass / pass | pass / pass | pass / pass |
| deep groups (ruling M2) | - / pass | - / pass | - / pass | - / pass |
| G-MISSING (files) | - / pass | - / pass | - / pass | - / pass |
| windows (R3-R11) | - / pass | - / pass | - / pass | - / pass |
| G-SENTINEL (deep) | - / flag (wbal_roll* -999) | - / flag | - / flag | - / flag |
| G-RANGE | - / flag (luh2_forest) | - / flag | - / flag | - / flag |
| G-CADENCE | - / pass | - / flag (burn_npix, never enters) | - / pass | - / flag (burn_npix, never enters) |
| G-JOIN | - / flag | - / pass | - / flag | - / pass |
| G-MISSING (deep) | - / flag | - / flag | - / flag | - / flag |
| G-SUPPORT (deep) | - / pass | - / flag (no all-zero unit) | - / pass | - / flag (no all-zero unit) |
| G-CALENDAR | - / pass | - / pass | - / pass | - / pass |
| G-DERIVED (recompute) | - / pass (14) | - / pass (15) | - / pass (24) | - / pass (394) |
| G-HIST (sample) | - / pass | - / pass | - / pass | - / pass |
| G-LINEAGE (deep) | - / pass | - / pass | - / pass | - / pass |

The windows each deep check derived equal the expected ones: pm25 and NDVI Y0 2003, end 2023, train end 2019; fire
2003, 2022, 2018; defo Y0 2004 (store_first_year_moved_y0), 2023, 2019. These are the same refusals and flags agent F
found this afternoon (D:/treeroute/F_20261006/gate2), on the engine before G's changes.

**What still blocks each package.** No refusal comes from an engine fault. These are the blockers on the snapshot
(16:45). Most are answered by ruling N (19:21, every recommended answer of FREEZE_SIGNOFF_SHEET.md accepted), which the other workflow
started writing into the live packages and engine at 19:36. The sign-off sheet's IDs are given for each item, so you
can tick them off. After that work, run the checks again; these reports will then be stale.

- **Every package:**
  - C9 k unset in the snapshot: `run` refuses and the freeze refuses (F-CONSTANTS). Since 19:37 the live engine has
    it set (S12 a).
  - The freeze's own preconditions: F-BAN-OPEN (20 open ban-list notes), F-PREREG (12 markers, S22), and
    F-CHECK-GREEN (green deep reports on the final packages and engine).
  - Build departures that make every run not headline-eligible (S21).
- **fire:**
  - G-CLOSED: 19 catalog rows of the burn-history store that no declared store holds (S9). The owner built
    D:/fire_history_lag2 at 18:34-18:38, so after that build the live fire package has a new file,
    `ingest/fire_history_store_catalog.yaml`. The store still has to be declared in dataset.yaml. These reports are
    for the package as it was at 16:45 (fingerprint 9d902f98ec33; the live one is now 9b6754f95509).
  - G-FACTS: 91 kept columns unverified, 6 'assumed' with no reviewer, 98 with co_measured unanswered (S1-S6).
  - G-EPOCH: travel_time, a static 2015 map after the lead-6 and lead-12 guard cuts (S27).
- **pm25:** G-FACTS only: 90 unverified, 7 'assumed' with no reviewer (the six aglw_*_hold2021 and burn_lag1), 99
  co_measured unanswered, and the target's legal_range_source missing (S1-S7).
- **defo:**
  - G-CLOSED: `month` and `grace_lwe` have no catalog row, and 10 banned rows name columns no store holds (S10).
  - G-FACTS: 261 unverified, 48 'assumed' with no reviewer, 266 co_measured unanswered (S1-S6, S18).
  - Y0 2004 also waits on S17, and the two new leaks on S28 and S29.
- **ndvi:**
  - G-CLOSED: the empty ctx:climatology row (S11).
  - G-FACTS: 387 unverified, 91 'assumed' with no reviewer, 479 co_measured unanswered, and the 5 ctx:top5:*
    data-selected lists whose test-exposure entries are unsigned (S1-S6, S8).

### 11.5 Full test suite

**Result: 3,357 passed, 0 failed, 0 errors, 4 skipped, 68 xfailed. 3,429 collected, 43.5 minutes (18:51:27-19:35:03),
exit 0.**

- Command, run once on the snapshot (`D:\treeroute\acceptance_20261006\suite\run_suite.sh`):
  `py -3.9 -m pytest -p no:cacheprovider --basetemp D:/treeroute/acceptance_20261006/suite/pt -rfEX --durations=30
  --junitxml D:/treeroute/acceptance_20261006/suite/junit.xml`, from the snapshot's engine folder.
- The snapshot also holds the six legacy scripts and presplit_cc/fetch_livestock_extend.py that some tests read from
  the research folder (copied read-only, unchanged).
- The basetemp holds 460 MB. Nothing was written on C:.
- It ran alone, apart from the owner's browser and game.
- The 4 skips are the opt-in heavy real-data derive checks. Each needs an environment variable: FIRE_DRAFT_DERIVE_CHECK,
  NDVI_DRAFT_DERIVE_CHECK, NDVI_DERIVE_CHECK, PM25_DERIVE_CHECK.
- The 68 xfails are the known ones:
  - 63 in test_derive_acceptance (the KNOWN entries, including defo's pending-owner fields);
  - 5 in test_route_region_defo_package (the seed-catalog entries C1 left on purpose).
- The snapshot included the other workflow's tests/test_apply_signoff.py as it stood at 16:45: 28 passed.
- Slowest: test_derive_acceptance's cadence cases (ndvi 337 s, pm25 200 s, fire 67 s, defo 45 s) and the pipeline
  smokes (22-89 s each).

### 11.6 The owner's next commands

Nothing full-size was started by me. In order, from the engine folder, in your own terminal, one at a time, with the
browser and games closed (the RAM checks are taken at the moment, see 11.3):

**Before any headline run** (each of these must be true first):
1. Ruling N's answers are in the packages and the engine. The other workflow's apply_signoff run started at 19:36 and
   set C9 k at 19:37. It also has to declare fire's history store (S9 a, built 18:34-18:38), refresh the drafts and
   update the tests that check the unsigned state. I did not touch any of it.
2. You read and sign S8's 17 refreshed disclosures (ruling N: "signed only after the owner reads them in short form").
3. After the last engine or package change, the checks and the suite, which must come out green:

```
py -3.9 -m treeroute check datasets\fire --deep          (about 4-5 min; the quick checks on the whole package are included)
py -3.9 -m treeroute check datasets\pm25 --deep          (about 5 min)
py -3.9 -m treeroute check datasets\defo --deep          (about 2 min)
py -3.9 -m treeroute check datasets\ndvi --deep          (about 7 min)
py -3.9 -m pytest -p no:cacheprovider --basetemp D:/treeroute/suite_final          (about 45 min)
py -3.9 -m treeroute_report.freeze datasets\fire datasets\pm25 datasets\defo datasets\ndvi          (minutes; round 2 hashes about 6 GiB of store files)
```

**The headline runs, cheapest first** (ruling M3). Each needs the freeze lock above, nothing else heavy running, and
about 10 GB of free RAM. Do not run a separate `plan` first: `run` does its steps itself, and a `plan` would repeat
the census and R30's count (NDVI: 8-13 h more).

```
py -3.9 -u -m treeroute run datasets\fire          (about 4.5-6.5 h)
py -3.9 -u -m treeroute run datasets\pm25          (about 12.5-17.5 h)
py -3.9 -u -m treeroute run datasets\defo          (about 15-20.5 h)
py -3.9 -u -m treeroute run datasets\ndvi          (about 24-35 h)
```

Where the hours come from (modelled = plan 4.5's re-priced cost model, measured / conservative; the rest measured or
scaled today):

| Run | Modelled compute | Census | R30's test-year count | Reader rebuilds and the rest | About |
|---|---|---|---|---|---|
| fire | 3.3 / 4.1 h | 10 min (236.6 M rows) | 0.6-1.6 h (scaled from the pm25 probe's block times) | about 0.4 h | 4.5-6.5 h |
| pm25 | 8.6 / 11.7 h | 23 min (Part 581) | 1.5-3.3 h | about 1.2 h (agent A) + L6 b 0.65-1.0 h | 12.5-17.5 h |
| defo | 14.6 / 19.9 h | 1 min | minutes | small; the probe's banks ran at 1.0-1.4 s a tree, inside the model's 1.67 | 15-20.5 h |
| ndvi | 14.8 / 18.2 h | 26 min (604 M rows) | **8-13 h** (ATTENTION 11-1) | not measured (the probe stopped before it); NDVI's GLS peak alone is estimated at 6.34 GiB | 24-35 h |

- Total: about 56-80 machine hours, against the sign-off sheet's 51-65.
- The difference is mostly NDVI's R30 count. Option (a) of ATTENTION 11-1 would remove most of it.
- On measured-model hours defo (14.6) is cheaper than NDVI (14.8), and with today's data passes it is clearly cheaper,
  so the order fire, pm25, defo, ndvi holds.
