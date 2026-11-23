# Files kept out of the archive

This file lists every group of files that the archive leaves out on purpose, why, and how it is rebuilt where its
sources are recorded. A kept-out file is named by the archive path it would have had. Counts and sizes are those
listed on 2026-11-11 (sections A-H and the published-rival input slims) and on 2026-11-17 (section I). The rulings
named here are the author's, in `engine/OWNER_RULINGS_2026-10-06.md`; fact IDs (L2, D51 ...) are those of the
frozen fact sheet, `records/fact_sheet/PAPER_FACTS.md`.

**One keep-out rule.** Per-location values of an input whose licence is not stated or not yet read stay out
(TerraClimate, the GPCC SPI, ERSST, the NOAA indices, GMIA, IBTrACS and the unrecorded static sources), and so do
per-visit values and fitted models derived from CoralTemp (fact L2's clause on derived products; ruling AT7).
Aggregate statistics over all rows (model files' feature ranges and split values, ridge means and spreads, the build
records' check differences) stay in, and so do the coral run's and the rival boards' records and aggregate scores
(ruling AT7). Ruling AV10 keeps the inputs whose licence call in Supplement S9 read "Not until confirmed" out:
cited, not shared. A rebuild may not reproduce a kept-out file byte for byte: some sources revise their history
(IBTrACS revises its best tracks after each season; each Hansen release re-derives the loss years), and some sources
are not recorded (`REBUILD.md`).

| Section | What | Files | Bytes |
|---|---|---:|---:|
| A | coral bleaching per-visit answers, ours and the rivals', with the coral lists of neighbour-router fit rows | 766 | 159,156,063 |
| B | VT0007 per-location answers and maps tied to GADM | 2,347 | 29,084,536,632 |
| C | rival input exports with per-location values of CoralTemp- or TerraClimate-derived inputs | 12,785 | 14,227,450,347 |
| D | the per-visit cyclone columns and the other coral tables built on CoralTemp | 35 | 35,638,062 |
| E | NOAA Coral Reef Watch values of the D6 check | 9 | 485,415 |
| F | pickles | 6 | 34,921,098 |
| G | further files kept out by ruling AV6 (the coral fit-row lists are counted in A) | 753 | 93,758,099 |
| H | two test reports that hold a host name | 2 | 1,728,940 |
| A-H | | 16,703 | 43,637,674,656 |
| I | files of the post hoc SHAP analysis (Part 628) | 3,574 | 4,755,149,138 |
| A-I | | 20,277 | 48,392,823,794 |
| | the published-rival input slims of PM2.5 and forest loss (end of this file) | 2,799 | 655,986,362 |

## A. Coral bleaching per-visit answers (ruling AT7, item 1)

The coral answers for each survey visit, ours and the rivals', are built on CoralTemp, so they stay out. With them
stay the lists of neighbour-router fit rows of the coral run and of the coral 2017-2020 row (12 files, 5,919,787
bytes; ruling AV6): for each routed survey visit, the ids and days of the earlier visits that its neighbour router
was fitted on, the regions whose trees it left out, a fallback flag and a part tag. Their ids carry each visit's
coordinates and date from the Global Coral Bleaching Database (CC0); they hold no CoralTemp value and no label.

| Would have been | Files | Bytes |
|---|---:|---:|
| `runs/coral/headline/20261020_f3b8e3da/`: `test_preds.parquet`, `ladder/lead_183/test_preds.parquet`, `ladder/lead_365/test_preds.parquet`, `inner_preds.parquet`, `ladder/lead_183/guard_preds.parquet`, `ladder/lead_365/guard_preds.parquet` | 6 | 17,922,459 |
| the same run's lists of neighbour-router fit rows: `pools_decision_surface.parquet`, `pools_test_pass.parquet`, `ladder/lead_183/pools_guard.parquet`, `ladder/lead_183/pools_test_pass.parquet`, `ladder/lead_365/pools_guard.parquet`, `ladder/lead_365/pools_test_pass.parquet` | 6 | 3,212,047 |
| `rival_boards/rivals/coral/20261020_f3b8e3da/`: `lead_*/preds_*.parquet`, `lead_*/guard_*.parquet`, `trials/*/inner_preds.parquet` | 83 | 10,104,438 |
| `rival_boards/rivals_build/_moved/coral_board_pre_fix599_20261021_160319/`: the same per-visit Parquet files of the first coral common-rival board | 83 | 10,104,438 |
| `rival_boards/rivals_human/coral/20261020_f3b8e3da/`: `lead_0/`, `lead_183/`, `lead_365/`, `trials/` (the NOAA degree-heating-week rule's and the Coral Reef Watch Outlook's answers; ruling AV11 treats the Outlook's answers as built on CoralTemp) | 154 | 2,896,997 |
| `rival_boards/human_index/coral/` (the `crw_dhw` and `crw_outlook` per-visit index files) | 12 | 2,283,440 |
| `analysis/paper_posthoc/v2_replay/A/` and `B/`: `rows_coral_lead_0.parquet` and `rows_coral_lead_365.parquet` (036f0c4f and 66837187 in Table S4.14), and `A/tool_rerun/rows/coral_20261020_f3b8e3da_lead_{0,183,365}.parquet` | 7 | 750,937 |
| `evidence/engine_v2/replay_af2_20261021/rows/coral_*` (3) and `versions/engine_v2/_moved/replay_trial_coral_20261021/` (4) | 7 | 520,714 |
| `analysis/coral_sens_2017_2020/`: `coral_data/` (7 files: `visits.parquet`, `month_precision_rows.csv` and the full build's tables and row lists), `validate/preview_tables/` (3), `validate/tiny_check/` (14: its visit table, group list, tables, row lists and package copy), and the run's `test_preds` (26474c84 in Table S4.14), `inner_preds`, `guard_preds` and `pools_*` Parquet files (12; the 6 `pools_*` files, 2,707,740 bytes, are this row's lists of neighbour-router fit rows). Its 9 `fitctx_log.parquet` files and the 8 record files of its table builds are archived | 36 | 45,736,632 |
| `analysis/coral_choice/`: every data file (166 `.dat`, 186 `.json`, 8 `.parquet`, 4 `.csv`, 3 `.npy`, 2 `.txt`, 1 `.log` and 1 `DONE` marker); its 8 scripts and notes are archived | 371 | 65,143,201 |
| `analysis/guidance/coral/method_preds_coral.parquet` | 1 | 480,760 |

**Rebuild.** The coral run, the coral 2017-2020 row and the coral rival boards are re-run by the archived engine and
rival code from coral tables rebuilt from the public sources (`REBUILD.md`, coral bleaching), though not always byte
for byte. The three Table S4.14 values above cannot be checked from the archive (`HASH_REGISTER.md`).

## B. VT0007 per-location answers and maps tied to GADM (ruling AT7, item 2)

| Would have been | Files | Bytes |
|---|---:|---:|
| `rival_boards/rivals_human/defo/20261017_d71c61f4/`: `lead_0/`, `lead_1/`, `trials/` (the `preds`, `guard`, `coverage` and `refs` files and `map_vt0007_*.json`) | 57 | 259,807,941 |
| `rival_boards/human_index/defo/` (the VT0007 index files and the `_work` maps, up to 223 MB each) | 2,290 | 28,824,728,691 |

**Rebuild.** The published-rival tool rebuilds them with the GADM boundaries, which are not redistributed. The board's
records and aggregate scores are archived.

## C. Rival input exports with per-location values of licence-unclear inputs (ruling AT7, item 3)

The columns were read from the Parquet footers and the slim and export manifests.

| Would have been | Files | Bytes | Why |
|---|---:|---:|---|
| `rival_boards/rivals_human/coral/20261020_f3b8e3da/slim/`, the data files (its 6 manifests are archived) | 1,223 | 7,309,615 | CoralTemp: `dhw_84`, `hs_max_84`, `ctx_mmm` |
| `rival_boards/rivals_human/ndvi/20261016_d1de3158/slim/`, the data files (its 6 manifests are archived) | 2,399 | 544,220,063 | TerraClimate: `V02_total_precip_mm` |
| `rival_boards/rival_export/pm25/20261007_74e67609/` | 2,303 | 1,611,216,747 | 11 TerraClimate columns among 122 inputs |
| `rival_boards/rival_export/ndvi/20261016_d1de3158/` | 2,410 | 8,288,928,604 | 12 TerraClimate columns |
| `rival_boards/rival_export/fire/20261017_869d1f38/` | 736 | 448,384,566 | 12 TerraClimate columns |
| `rival_boards/rival_export/defo/20261017_d71c61f4/` | 515 | 2,255,484,007 | annualised TerraClimate columns |
| `rival_boards/rival_export/coral/20261020_f3b8e3da/` | 1,234 | 16,482,384 | CoralTemp degree-heating-week features |
| `rival_boards/rival_export/_engine_run_root/` (export checkpoints) | 1,699 | 1,019,423,675 | the same inputs |
| `rival_boards/human_index/ndvi/20261016_d1de3158/_work/` (the Kraft LSTM input store; its build record is archived) | 266 | 36,000,686 | TerraClimate columns |

**Rebuild.** The archived rival code writes them again from the runs and from rebuilt inputs (`REBUILD.md`).

## D. The per-visit cyclone columns and the other coral tables built on CoralTemp (ruling AT7, item 4; fact L2)

| Would have been | Files | Bytes |
|---|---:|---:|
| `coral_build/coral_store/20261020_014201/`: the store's three lead tables | 3 | 10,563,839 |
| `coral_build/coral_data/`: `visits.parquet`, the full build's lead tables, `rows_audit.parquet` and `dropped_rows.csv`, `month_precision_rows.csv`, and the tiny smoke build with its moved copy | 30 | 14,402,848 |
| `rebuild/forecast_features_L0.parquet` and `rebuild/forecast_features_L365.parquet`, the two legacy feature tables that the coral table builder checks against | 2 | 10,671,375 |

- The build records of these tables are archived, and they hold no per-visit value: in `coral_build/` the store's
  `coral_store/20261020_014201/build_manifest.json` (fact D56), and in `coral_build/coral_data/` the census
  `visits_census.json` (fact D51), the full build's `full/build_manifest.json`, `full/check_report.json` and
  `full/build.log`, and `full_build_console.log` and `full_check_console.log`. The same records of the coral
  2017-2020 row are in `analysis/coral_sens_2017_2020/`.
- `dropped_rows.csv` and `month_precision_rows.csv` hold only keys of the Global Coral Bleaching Database (CC0).
  Nothing in the paper cites them, so they stay out with the tables.
- The two legacy feature tables hold CoralTemp-derived features per survey event and per-event cyclone columns.
  Their recorded sizes and SHA-256, the targets of a rebuild:

| Table | Rows | Bytes | SHA-256 |
|---|---:|---:|---|
| `forecast_features_L0.parquet` | 21,430 | 5,385,108 | `4ef950db3d64062a51bedd70136c14590dd20789f25167209eb8a5e151409c52` |
| `forecast_features_L365.parquet` | 21,412 | 5,286,267 | `fa213246fe6df283385814aa01cf2018af54c28de6494463db6d4912b745c0eb` |

**Rebuild.** `rebuild/coral_forecast.py` rebuilds the two legacy tables, and the coral table builders
(`coral_build/coral_tables/build_visits.py`, then `build_tables.py`) rebuild the coral tables (`REBUILD.md`, coral
bleaching, steps 6 and 7).

## E. NOAA Coral Reef Watch values of the D6 check (fact L2)

The summaries and logs of the D6 check (ruling AH), 9 files: `rivals_code/human_tools/reports/d6_summary.csv`,
`d6_v2_summary.csv`, `d6_v2_summary.log`, `run_D6_pfeg.log`, `run_D6_pfeg_close.log`, `run_D6_pifsc.log`,
`run_D6_pifsc_2.log`, `run_D6_v2_pifsc.log` and `verify_D6_pifsc.log`.

**Rebuild.** The archived scripts `rivals_code/human_tools/d6_summary.py` and `d6_summary_v2.py` rebuild the
summaries. The two site-day lists of the check, `rivals_code/human_tools/d6_sitedays.csv` and `d6_sitedays_v2.csv`,
hold no Coral Reef Watch or CoralTemp value and are archived.

## F. Pickles

Loading a pickle runs code, so none is archived: `rival_boards/rivals/coral/20261020_f3b8e3da/lead_{0,183,365}/model_hgb_l1.pkl`
(17,460,549 bytes) and the same three in the first coral common-rival board,
`rival_boards/rivals_build/_moved/coral_board_pre_fix599_20261021_160319/` (17,460,549 bytes).

**Rebuild.** The common-rival harness refits the coral board's models from rebuilt coral inputs.

## G. Further files kept out by ruling AV6

Ruling AV6 keeps every file of this section out. The coral lists of neighbour-router fit rows belong here too; they
are counted in section A, beside the per-visit files they belong to.

- **The burned-fraction published rivals' unused input slims:** the data files of
  `rival_boards/rivals_human/fire/20261017_869d1f38/slim/`, 725 files, 44,243,624 bytes (363 Parquet, 361 JSON and
  1 log; their 6 slim and export manifests are archived). They were prepared for the burned-fraction published
  rivals, which were not run. Their Parquet files hold per-location GPCC SPI values (`x__spi_01m` to `x__spi_24m`)
  and the ONI series, both "Kept out: cited, not shared" (ruling AV10), besides label-derived history columns.
- **The coral common-rival boards' model files:** `lead_{0,183,365}/model_lgbm.txt`, `model_lgbm_tweedie.txt` and
  `model_ridge.json` in `rival_boards/rivals/coral/20261020_f3b8e3da/` and in the first coral board's folder, 18
  files, 10,291,350 bytes. They are models fitted on CoralTemp-derived inputs, so derived CoralTemp products (fact
  L2). The gridded boards' model files hold only aggregate statistics of their inputs and are archived.
- **The GADM coverage report:** `rivals_code/human_tools/reports/gadm_coverage.json` and `gadm_coverage.log`, 2
  files, 37,739 bytes; derived from GADM and not cited.
- **The NDVI published rivals' BARDL maps:** 8 files, 39,185,386 bytes. Each holds per-location calendar-month means
  of TerraClimate precipitation (`V02_total_precip_mm`; TerraClimate's page states no licence) and of ERA5-Land soil
  moisture (`V30`), and per-location BayesianRidge coefficients and feature means. The two boards' copies are
  byte-identical:

| File (in `rival_boards/rivals_human/ndvi/20261016_d1de3158/` and in `rival_boards/rivals_human/_moved/20261025_ndvi_board_pre_part618/`) | Bytes | SHA-256 |
|---|---:|---|
| `lead_0/map_bardl_h1.json` | 4,900,936 | `26bc37552579f5f2d7c52ee102f3950e46ebf4d006b0943416e1523bf2035586` |
| `lead_6/map_bardl_h1.json` | 4,903,467 | `03e3ee612d67df8bf673eb4e7a9caae506032d530a62b44a80e1116f21141dec` |
| `lead_12/map_bardl_h1.json` | 4,887,032 | `eb5c9b0e82a336ee1911f5e417ef6b3c4d73c83e22cd855a0f8aec58be1d0f73` |
| `trials/bardl_h1/method.map.json` | 4,901,258 | `03d2b835d74c8f0e15433552a360548f6761cae21df84d4ab8c5a10f0cdd2b4f` |

**Rebuild.** The published-rival tool rebuilds the burned-fraction slims from rebuilt inputs, and the BARDL maps
(adapter `rivals_code/human_rivals_build/human/adapters/ndvi_bardl.py`) from a rebuilt panel; the common-rival
harness refits the coral model files from rebuilt coral inputs; none of them always byte for byte. The trial map's SHA-256 is recorded in
`trials/bardl_h1/method.json` and in `human_picks.json` on both boards (all archived), so a rebuilt map can be
matched against it. Each lead's `done_bardl_h1.json` also records a `hash`, but that is the refit's resume key, not
a hash of the map.

## H. Two test reports that hold a host name

`coral_build/fullsuite.xml` and `coral_build/fullsuite2.xml` (2 files, 1,728,940 bytes): test reports whose
`hostname` attribute holds the host name of the machine that ran the tests. Nothing in the paper cites them. Running the test suite
writes new reports.

## I. The post hoc SHAP analysis (Part 628)

| Would have been | Files | Bytes | Why |
|---|---:|---:|---|
| coral bleaching's row-level files: `analysis/shap_v1/out/coral/lead_0/<model>/rows.parquet` and `background_keys.parquet` (6 pieces), the sample and background files of `analysis/shap_v1/sample/coral/` (4), and `preds_check.parquet`, `rows.parquet` and `rows_index.csv` of `analysis/shap_v1/rebuild/coral/lead_0/` | 19 | 6,856,651 | the SHAP protocol's decision D13 and its section 9: row-level coral files stay out, as the coral per-visit answers do (section A); their keys carry each survey visit's coordinates and date |
| the row-level SHAP values of the four gridded problems, `analysis/shap_v1/out/<problem>/lead_0/<model>/rows.parquet` (burned fraction 6 pieces, PM2.5 5, forest loss 6, NDVI 6) | 23 | 59,524,068 | kept out by default: for the linear rivals each value is proportional to its input's difference from the input's mean over the location's training-year rows with the same season key, so with the archived ridge model files these files would give per-location values derived from inputs whose licence is not stated (TerraClimate, the GPCC SPI and the NOAA indices among them; the keep-out rule; ruling AV10). Every number the paper reports from them is in the archived `compare/` files and the re-computation's results |
| `analysis/shap_v1/engine_runs/`, the engine's run and checkpoint folders of the five rebuilds | 1,994 | 1,515,695,471 | privacy, as in H: their checkpoint `key.json` files record input paths of the run machine that hold a Windows account name |
| the rebuilt models: the rebuilt tree banks and the sampled locations' routers (`analysis/shap_v1/rebuild/<problem>/lead_0/bank.npz` and `routers.npz`: 10 files, 727,824,592 bytes) and the rebuilt random forests (`analysis/shap_v1/work/<problem>/lead_0/rf_trees/`: 300 trees and a checkpoint per problem, 1,505 files, 1,721,464,842 bytes) | 1,515 | 2,449,289,434 | the banks hold the engine's fitted trees, none of which is archived; coral bleaching's bank, routers and forest are derived CoralTemp products (fact L2); and the archive holds no NumPy file |
| NumPy and compressed record files: `analysis/shap_v1/out/<problem>/lead_0/compare/bootstrap_draws.npy` (5), the per-draw values of `analysis/shap_v1/verify_v1/A/draws/` and `analysis/shap_v1/verify_v1/B/draws/` with one work file of the re-computation's checks of its numbers, in `analysis/shap_v1/verify_v1/` (17 `.npz`), and `analysis/shap_v1/verify_v1/reconcile/work/no_number_keys.json.gz` (1) | 23 | 723,783,514 | the archive holds no NumPy or compressed file |

**Rebuild.** The archived scripts (`analysis/shap_v1/scripts/`) rebuild the models from inputs that the archive does
not hold, and check them bit for bit against the saved predictions. The region draws are regenerated from their
SHA-256 generator and checked against the SHA-256 that each `per_lead.json` records (the SHAP protocol, sections 8
and 9). A's and B's per-draw values are working files behind their archived `results.json`, and the compressed key list is
a work file that nothing cites.

## The published-rival input slims of PM2.5 and forest loss (ruling AV6)

| Would have been | Files | Bytes | Licence of the values |
|---|---:|---:|---|
| `rival_boards/rivals_human/pm25/20261007_74e67609/slim/`, the data files (own-history columns built from the ACAG labels only; the 6 manifests are archived) | 2,291 | 404,954,209 | CC BY 4.0, with attribution |
| `rival_boards/rivals_human/defo/20261017_d71c61f4/slim/`, the data files (own-history columns built from Hansen only; the 4 manifests are archived) | 508 | 251,032,153 | CC BY 4.0, with the display credit |

Their licences would allow sharing, but no paper text cites them, their only third-party values are the labels,
which the archived predictions already hold where the paper uses them, and the archived slim manifests record each
slim file's columns and SHA-256. **Rebuild.** The published-rival tool rebuilds them from the label stores (forest
loss's only as far as Hansen's current release matches: each release re-derives the loss years).

## Also not redistributed

- The raw third-party products that the published-rival tool fetched (`rival_boards/human_products/`: 1,944 files,
  2,500,069,650 bytes): GADM, CoralTemp sea-surface temperature, Coral Reef Watch, MERRA-2, Hansen and the CEMS
  fire-weather download. Only two of their product manifests are archived (gadm36_defo42 and noaa_crw_dhw_sitedays).
- The 44 GB monthly panel of the run machine (2,926 files, 43,957,974,336 bytes; fact D1), the other source stores of
  the inputs, and the GSHHG zip that the region map reads. `REBUILD.md` names the scripts that fetch or rebuild them
  where their sources are recorded.
