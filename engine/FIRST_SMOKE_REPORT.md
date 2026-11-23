# First end-to-end smoke: pm25_draft

> **Note added 2026-10-05:** the forecast ladder now exists. `smoke` and `run` now run the nowcast and
> then the forecast ladder (the lead-0 contract, then every derived lead: 1, 3, 6 and 12 on a monthly
> package). Where this report says only the nowcast is built (row R11 below), it describes this run of
> 2026-09-29, not the engine today. The smokes that ran the ladder are in SMOKES_REPORT.md.

Date: 2026-09-29. Command, run from `engine/` through the engine launcher:

```
py -3.9 -m treeroute smoke datasets/pm25_draft
```

**Result: it worked.** The command exited with code 0 after 38 seconds and wrote nothing to stderr.
Run folder: `D:\treeroute\runs\pm25_draft\smoke\20260929_8b651bdd` (run fingerprint `8b651bdd...`).
No engine code was changed.

Before the run I checked that no other Python job was running. Free RAM was 11 GB of 16 and D: had
53 GB free. The engine made its temp folder `D:\treeroute\tmp\treeroute_run_8b651bdd_30936`, then
removed it and the empty `D:\treeroute\tmp` above it. It released the heavy-job lock when it finished.

This is a smoke run of a DRAFT package, so every number below is a plumbing check only. Smoke numbers
say nothing about which way the real result will go. The run record marks the run "not
headline-eligible" and gives 9 reasons: the DRAFT stamp, the smoke kind, the stand-in guard tolerance,
and 6 build departures (quick checks not run, GLS arms not routed, private router kernels, the run's
own band, report rows not built, and the pre-Y0 label reading).

---

## 1. What the smoke ran on

- Groups: 127 in the data and 127 after exclusions. The smoke takes the first 4 in sorted order:
  alaska_interior_taiga, amazon_basin_brazil, anatolian_plateau, andes_puna.
- 40 units per group (160 in total). Each unit is both a bank unit and a scored unit.
- 12 trees per group, so the bank holds 48 trees.
- Target: 42,240 rows kept, out of 18.8 million rows in the 88 files read.
- Both driver stores covered every target row: the monthly panel (92 columns) and GFED burn
  (1 column). The package's feature script added burn_lag1, ctx:lat and ctx:month.
- Pool: 40,320 grid rows (160 units x 252 months). It has 99 tree columns (93 features plus 6
  own-history columns) and 2 context columns (ctx:month, ctx:lat).

## 2. The derived settings it used (derived.json, 36 entries)

| Rule | What it settled on |
|---|---|
| R1, R2 | Monthly data. The season is the month of the year (12 steps per year). |
| R4, R3 | First model year 2003 and last year 2023. Labels before 2003 are held back and used only as lag sources (first model step 24037). |
| R6, R5, R7 | Training ends in 2019. The test years are 2020-2023. The inner fit covers 2003-2016 and the inner score covers 2017-2019. |
| R11 (lead 0) | Fit cut 24240 (end of 2019). Guard / inner cut 24204 (end of 2016). The lead cuts for 1, 3, 6 and 12 are also derived, but only the nowcast is built. |
| R12 | Per-unit router. Every unit had 168 valid rows, so no unit needed the region fallback. |
| R14 | Router columns: intercept, normal, context, trees. The penalty grid has 7 levels (0.1, 0.3, 1, 3, 10, 30, 100) x 5 ratios (0.0625 to 1), giving 35 points. Centres are 0.5 (trees) and 0.25 (context). |
| R14 overlap blocks | 4 blocks, one per group. No two smoke groups are linked. |
| R17 | 6 own-history columns: the last 1, 2 and 3 values, the 12-month mean, the 60-month mean and the all-history mean. |
| R18 | 40 bank units and 40 scored units per group, flagged "capped" (the smoke's fixed count). |
| R19 (smoke) | 48 trees. Each group has 8,160 rows at the fit cut (bags of 4,080) and 6,720 at the inner cut (bags of 3,360). The expected out-of-bag share is 0.607. Correctors: depth 6, leaf 10, fitted on out-of-bag rows. |
| R22 | Two links: identity and log_c. |
| R23 | c = 3.3397 at lead 0 (one c per lead cut, D63). |
| R28 | Legal range 0 to infinity. |
| R8 | 74 lagged driver columns: 47 at lag 0, 13 at lag 1, 12 at lag 2, 2 at lag 3. |
| R9 | No freeze columns. |

## 3. Phase timings

| Step | Seconds |
|---|---|
| Launcher start (pins, sklearnex patch) | about 3 |
| Package load, group list, RAM preflight | under 1 |
| Read the target (88 files) | about 9 |
| Driver stores and feature script | about 3 |
| derive_all (two passes), static table, overlap blocks | 4.1 |
| Open run folder, manifest, disk preflight | about 3 |
| pool | 0.84 |
| fits (fit-cut bank, GLS weight model, inner-cut bank refit) | 5.47 |
| decision | 5.0 |
| test_pass | 2.6 |
| report | 0.54 |
| **Total wall time** | **38** |

The launch record confirms these settings: BLAS, OpenMP and oneDAL were each pinned to 4 threads,
sklearn was patched by sklearnex 2025.10.0, and the router and tree-predict pools used 8 workers,
as C14 sets.

## 4. The adoption (adoption.json)

- **Adopted arm:** log_c link, corrector tool, unweighted.
- **Penalty:** level 0.3, ratio 1.0.
- **N2 guard:** passed, and the layer did not decline. All 4 tree arms beat their own link's trees-off
  on the decision surface, so all 4 were eligible.
- **How it chose:** it picked the lowest MAE on the inner decision surface. That surface held 5,759
  rows from 2017-2019, scored by the bank refitted at the inner cut (L6 b). There were 142 candidates:
  4 arms x 35 grid points, plus 2 trees-off arms.

| Arm (decision surface) | Best MAE | Where on the grid | corr2 (shown only, not used) |
|---|---|---|---|
| log_c corrector | **3.2067** | 0.3 / 1.0 (edge: top ratio) | 0.820 |
| log_c plain | 3.2169 | 0.1 / 1.0 (edge: bottom level, top ratio) | 0.821 |
| identity plain | 3.5001 | 0.3 / 1.0 (edge: top ratio) | 0.798 |
| identity corrector | 3.5012 | 0.3 / 1.0 (edge: top ratio) | 0.794 |
| log_c trees-off | 3.3602 | no grid | 0.805 |
| identity trees-off | 3.6068 | no grid | 0.778 |
| predict-zero (shown only) | 21.0048 | | |

- **Weighting:** only unweighted arms ran. The 4 GLS arms are listed as missing, and the run records
  why: there is no weighted per-unit router kernel yet. The GLS weight model itself was fitted and
  saved (gls_weight_model.json).
- **Plumbing identities (G-PLUMB), both links passed:**
  - Trees-off equals the normal: largest gap 2.4e-9 (identity) and 9.8e-10 (log_c).
  - The base grid point reproduces the unswept router exactly.
- **Legal clip:** 35 and 25 decision-surface predictions of the two identity arms fell below 0 and
  were clipped. No log_c prediction was clipped, and no test prediction was clipped.

## 5. Test window (2020-2023): plumbing numbers only

7,680 rows (160 units x 48 months), of which 7,678 have a label. All four groups are pooled.

| Column | MAE | Anomaly R2 | Hit rate |
|---|---|---|---|
| **Adopted: log_c corrector** | **3.723** | **0.215** | 0.337 |
| log_c trees-off (the verdict's reference) | 4.111 | 0.031 | 0.299 |
| Guess-normal | 4.254 | 0.000 | 0.288 |
| Predict-zero | 21.888 | -15.48 | 0.002 |
| Last-5-years normal (a baseline) | 3.729 | 0.126 | 0.376 |

Anomaly R2 is measured against the same normal that guess-normal uses, which is why guess-normal
scores exactly 0.

Verdict (D74 rule): "helps". The contrast is 0.388, from 0.123 to 0.653, against a band of 0.097. All
4 groups did better and none flipped sign. The band comes from this run's own D75 pairs:

- Each tree arm against its own trees-off: all four say "helps".
- Each corrector against its placebo: both say "cannot tell". At smoke size, the corrector's gain over
  its scrambled copy is inside the noise.

Again, smoke deltas carry no sign information.

## 6. Saved rows (every row-level prediction is on disk)

- `test_preds.parquet`: **7,680 rows x 29 columns**. For each of the 8 arms (tree arms, trees-off and
  both placebos) it holds the clipped and the pre-clip prediction. It also holds the 3 baselines, y,
  the normal and the legal bounds.
- `inner_preds.parquet`: **5,759 rows x 288 columns**. For each of the 142 decision candidates it holds
  the clipped and the pre-clip prediction, plus the key columns.
- `fitctx_log.parquet`: 1,285 hand-out records, one per data hand-out, with its cut and row-key hash.
- Score tables: score_pooled, score_by_group, per_year, per_group, preclip, jackknife. Also
  guard_report.json and verdict.json.

## 7. Own-block columns were dropped

- tables.json: all 20 tree-answer tables (12 at the fit cut, 8 at the inner cut) record
  `own_trees_dropped: 12` and 36 columns out of 48 trees. Each group's router therefore never saw its
  own group's 12 trees.
- guard_report.json, G-DISJOINT: "each router drops its own overlap block's tree columns". route.kinds
  checks this at every router fit.
- With 4 single-group blocks, "own block" means "own group" in this smoke.

## 8. The adoption was locked before any test label opened

The files were written in this order (write times from the run folder):

1. `adoption.json` at 06:47:01.99
2. `adoption.json.lock.json` at 06:47:02.03. Its SHA-256 is `23e09d1e...`, and the file on disk still
   hashes to the same value.
3. `manifest_adoption.json` at 06:47:02.06. This addendum holds the adoption hash and is written once.
4. `test_labels_opened_lead_0.json` at 06:47:02.13. It opens 7,680 rows against the same hash.
5. `test_preds.parquet` at 06:47:04.57.

The vault's `open_test_labels` refuses to open unless a lock exists and the lock, the file on disk and
the caller all agree on the hash.

The lock file also records 360,960 label reads made before the lock. All of them came through the
D54 (a) as-of door, which serves only the labels known at each row's issue step. These reads build
the own-history columns, including the history columns of test-window rows. They are not the test
labels being scored.

---

## Worth a look (none of these stopped the run)

- **ATTENTION: edge picks.** On the decision surface, every tree arm's best point sits on the edge of
  the penalty grid: the top ratio (1.0) for all four, and also the bottom level (0.1) for log_c plain.
  The engine flags an edge pick and does not extend the grid (Q13 a). At smoke size this means little.
  If the headline run shows the same, it is a question about the grid.
- **ATTENTION: an unanswered catalog fact.** All 74 lagged driver columns have
  `co_measured_with_target` unanswered (null, fact status "unverified"). R8 therefore set their lags
  without that fact (47 of them at lag 0) and flagged each one in derived.json. This is a catalog item
  for the owner, not an engine fault.
- **The last-5-years normal is nearly as good as the adopted arm on test** (MAE 3.729 against 3.723),
  and it has a higher hit rate (0.376 against 0.337). The verdict's reference is trees-off (MAE 4.111),
  which uses the full-history normal. This is a smoke number, but it may be worth watching on the
  headline, because PM2.5 has trends.
- **The "filled share" line in the log** (for example, hist_last_1 0.0040) is the share of rows that
  needed the fallback fill: about 0.4%, the first month or two of each unit. It is not the share of
  rows that have a value. The history columns are about 99.6% real values.
