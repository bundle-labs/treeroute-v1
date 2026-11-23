# Common rivals (type 1): list, protocol, time and resources

Written 2026-10-20. Revised 2026-10-20 after three reviews (fairness, feasibility, completeness); see the REVIEW LOG at the end.
Status: PLAN ONLY. Nothing has been run, exported or installed.
Scope: type 1 only (common learners). Type 2 (the method people actually use for each problem) comes later. Ruling C11 (coral: lagged DHW and the real NOAA Outlook; QUESTIONS_ROUND3_HANDOFF.md:472) belongs to the type-2 plan and moves there.
Builds on: ruling D (OWNER_RULINGS_2026-09-28.md:52-55) and APP_PLAN.md 4.6 (:575-591). Ruling L3 deferred the rival details to M8 and said "the plan's defaults stand for now" (OWNER_RULINGS_2026-09-28.md:67). This file fills in those details for the owner to sign.

---

## 1. SUMMARY

- **Core set:** Ridge, Random Forest, XGBoost and LightGBM on all 5 problems. Plus LightGBM-Tweedie on every zero-heavy target (now fire, defo, coral), and hgb_l1 on coral only (ruling C12).
- **Optional:** the donor-only 10-fold board (the signed default of ruling D; phase 2), Board B (per-unit MOS), CatBoost, an MLP, kNN on coral.
- **Own-history rival rows:** the normals (board N) and damped persistence. **Reference rows:** guess-normal, predict-zero, persistence, coral donor median.
- **One rule set for every rival:** same rows, same columns, the normal given as a fixed offset (as our router has it), tuned only on the inner window with leak-free normals, links read from each run, `random_state=0` fixed, MAE decides, region jackknife, pre-registered before any test score.
- **Time for the core set:** about 36-65 h of fitting, plus 14-30 h of export, plus ~3 h of smokes. So about **53-98 h of machine time, over about 8-12 overnight sessions**, one heavy job at a time. Coral takes minutes. All times except coral and RF are extrapolated (x).
- **ATTENTION, RAM:** Random Forest with full rows needs about 14-15 GB on NDVI and about 10 GB on defo. That does not fit. The plan uses a fixed bank-unit stride for RF on those two (decision Q9).
- **ATTENTION, disk:** NDVI must be exported and fitted one lead at a time. The engine's own temp folder peaks at 15.3 GiB during its build.
- **Nothing is missing.** xgboost 2.1.4, lightgbm 4.6.0 (with `lgb.Sequence`), sklearn 1.6.1 + scikit-learn-intelex 2025.10.0 (pip version; `sklearnex.__version__` prints a placeholder 2199.9.9), catboost 1.2.10 and torch 2.8.0 are installed.

---

## 2. THE COMMON RIVAL LIST

### 2a. CORE set

| # | Rival | Runs on | What it is | Why reviewers expect it | Library | Small tuning grid |
|---|---|---|---|---|---|---|
| C1 | **Ridge** | all 5 | A straight-line model with a penalty on large weights. | The simplest learned baseline. It shows what the trees add over a weighted sum. | sklearn 1.6.1. Chunked X'X fit. | alpha {0.1, 1, 10, 100, 1e3, 1e4, 1e5, 1e6} = 8 values, all from one X'X pass. Columns standardised on the fit's own train rows. Missing values: train-row mean + a missing-flag column (Q7). |
| C2 | **Random Forest** | all 5 | Many deep trees on bootstrap samples, averaged. | The default tabular baseline in environmental forecasting. The owner named it. | sklearnex (oneDAL) RandomForestRegressor. Disclosed. | 300 trees fixed. max_features {0.2, 0.5} x min_samples_leaf {5, 50} = 4. Each tree sees about 200k rows (`max_samples` as a FRACTION, R5). NDVI and defo use a fixed bank-unit stride (Q9). |
| C3 | **XGBoost** | all 5 | Gradient-boosted trees, level-wise. | The most cited boosting library. | xgboost 2.1.4, `tree_method=hist`, `QuantileDMatrix` from the per-group files. | max_depth {6, 8} x min_child_weight {1, 50} = 4 (Q19). eta 0.1, colsample_bytree 0.5, subsample 1.0. Rounds staged at {100, 200, 400, 800, 1600} (Q4). |
| C4 | **LightGBM** | all 5 | Gradient-boosted trees, leaf-wise, histogram-based. | The fastest strong tabular learner; the old PM2.5 board's G and H. | lightgbm 4.6.0, `deterministic=True, force_row_wise=True, feature_pre_filter=False`, Dataset from `lgb.Sequence` over the per-group files. | num_leaves {31, 127} x min_child_samples {20, 200} = 4. learning_rate 0.1, feature_fraction 0.5, no bagging. Rounds staged at {100, 200, 400, 800, 1600}. |
| C5 | **LightGBM-Tweedie** (labelled row) | every target with legal_min = 0 and at least 20% zero train labels; today fire, defo, coral (pm25 has 0% zeros, NDVI has negatives) | LightGBM with a loss made for many zeros plus a skewed tail. | Reviewers expect a zero-inflated loss on these targets. It beat us once on corr2 under the old setup (defo per-region, CLAIMS_LEDGER.md:93). Since then MAE is the ruled criterion and ours won on MAE (+0.000524, PROJECT_HANDOFF.md:1492-1494). | lightgbm 4.6.0, `objective=tweedie`. | C4's 4 settings x power {1.2, 1.5} = 8. No extra link (the log is built in). Offset: init_score = log(max(normal, c)), with the run's own c. Never replaces C4. |
| C6 | **hgb_l1** (coral only, ruling C12) | coral | sklearn HistGradientBoosting with `loss='absolute_error'`. The only rival trained on the headline metric (MAE). | Ruled in by C12 (QUESTIONS_ROUND3_HANDOFF.md:473). | sklearn 1.6.1. | max_leaf_nodes {31, 127} x min_samples_leaf {20, 200} = 4, learning_rate 0.1, iterations staged {100, 200, 400, 800, 1600}, same links as C1-C4. **Labelled timid-prone** (PROJECT_HANDOFF.md:1486-1488). |

- **Links on offer: read from each run, never from a hand list.** The harness reads `derived.json` R22 `value` and the run's own c (R23). Today that gives:
  - pm25: identity, log_c (2 links).
  - ndvi: identity only (1 link). NDVI has no derived c, so no log link is offered.
  - fire, defo, coral: identity, log_c, arcsine (3 links).
- **Trials per learner** = 4 settings x links: pm25 8, ndvi 4, fire/defo/coral 12. C5: 8 (no links). Ridge: 8 alphas x links, from one X'X pass.
- **Our layer's candidate count is printed beside the trial count**, so readers can compare tuning effort.
- **Why the grids are small:** the old 48-trial LightGBM grid was stopped after 4 trials (pm25_rivals.py:66-67; D:/pm25_rivals/full/rivals.log:41-42). A finished small grid is better than an unfinished big one. Untuned defaults are not allowed either: defo XGBoost defaults gave R2 -2.65 (_rivals.log:1177).
- **Why the rounds and alphas are wider than the first draft:** the old picks sat at the 1000-round edge at learning rate 0.1 (rivals.log:34, :36, :61-65), and the old Ridge pick sat at the alpha 1e4 edge (rivals.log:19-20). So rounds now go to 1600 at 0.1, and alpha to 1e6.

### 2b. OPTIONAL set (owner decides, section 6)

| # | Rival | What it is | Why | Grid | Notes |
|---|---|---|---|---|---|
| O2 | **Donor-only fold board** (Ridge + LightGBM, as old boards R and G) | Refitted on 10 region folds. Each group is scored by the fold model that never saw it. | Ruling D names it (OWNER_RULINGS_2026-09-28.md:55), and L3 kept it as the default (APP_PLAN.md:582). Dropping it needs a deviation note. | Tuning per Q17. | Phase 2, after the core board. **Disclosed (APP_PLAN.md:588, 4.6):** "hyperparameters tuned once on pre-cut rows of groups that a fold model later never saw." The same text goes into the pre-registration Part. |
| O2b | **Board B** (per-unit MOS) | Each unit's own linear correction of a rival column z. | Q44 put every PM2.5 board on every problem (HEADLINE_QUESTIONS_AND_FIXES.md:51). | Q18. | Needs O2 (z comes from the fold models). Cannot run on coral (HEADLINE_QUESTIONS_AND_FIXES.md:460). |
| O3 | **CatBoost** | Boosting with symmetric trees. | Some reviewers know it. | depth {6, 8} x l2_leaf_reg {3, 30}. | Ruling C12 REMOVED it. It cannot run out-of-core (about 3.4 GB at 1M x 300). |
| O4 | **MLP** | A small 2-layer neural network (256-256), CPU only. | It answers "did you try a neural net?". The ledger flags "no neural rival" as a weakness (CLAIMS_LEDGER.md:157, :231). | weight decay {0, 1e-4} x epochs staged {10, 30}. | Cost (x): coral minutes, fire ~0.4 h, pm25 ~1.1 h, defo ~3 h, ndvi ~3.7 h; ~8 h total. |
| O5 | **kNN** (coral only) | Averages the k most similar survey rows. | It was on the coral benchmark (CORAL_EXPERIMENTS.md Part 445). | k {10, 25, 50}. | Too slow on grids. Close to our neighbour router's pool step, so it gets a label. |

- **Left out on purpose:**
  - sklearn HistGradientBoosting with squared loss duplicates LightGBM.
  - ExtraTrees duplicates RF.
  - The fractional logit is numerically unstable (CORAL_EXPERIMENTS.md:3185-3192).

### 2c. OWN-HISTORY RIVAL ROWS and REFERENCE ROWS (printed beside every board)

| Row | Kind | What | Source |
|---|---|---|---|
| Normals (board N: guess-normal, last-5-years normal) | own-history rival (APP_PLAN.md:580; Q44) | Each unit's own normal, as the run built it | HEADLINE_MODEL_TABLE.md:7; PREREGISTRATION_DRAFT.md:120-140 |
| Damped persistence | own-history rival (APP_PLAN.md:580) | Persistence pulled toward the normal. It beats the declined answers on PM2.5 lead 12 (3.835 vs 4.084) and NDVI leads 6/12 | PENDING_PARTS.md:173, :261 |
| Predict-zero | reference only | Always 0. On fire it beats our MAE: 0.00428 vs 0.00439 | HEADLINE_MODEL_TABLE.md:26 |
| Persistence | reference only | Last observed value at the issue date | PREREGISTRATION_DRAFT.md:123-124 |
| Donor median (coral) | reference only | Coral's "normal": one constant, 8.294 MAE | HEADLINE_MODEL_TABLE.md:15-18 |

- Predict-zero and plain persistence are excluded from rival tables by ruling (PROJECT_HANDOFF.md:1481-1485). They are printed as context.
- PROJECT_HANDOFF.md:1486-1488 also excludes hgb_l1; the later ruling C12 keeps it on coral only, so it is C6 with a timid-prone label.

---

## 3. THE UNIFORM PROTOCOL (one rule set for every rival, problem and lead)

0. **Plug and predict.** The harness takes only a run folder (or package path). It names no problem. It reads links (R22), c (R23), cuts, legal bounds, the report stratum (run_record), seen_during_design (split.yaml), the zero-heavy test for C5, and the coral store path from the run and its package. Per-problem values in this file are what it reads today, for checking only.
1. **Information parity.** The main board is "gauged global": one fit per lead on every kept group's bank units, up to the cut. This includes the target region's own past, the same information our router gets (ruling D, OWNER_RULINGS_2026-09-28.md:54). Scored units are a subset of bank units (split.py:370-476), so each scored unit's own history is in the fit. Disclosed:
   - the rival also sees other units of its own group (APP_PLAN.md:582);
   - no unit ID is given to any rival;
   - our fire and coral arms use GLS weights and correctors (HEADLINE_MODEL_TABLE.md:16, :19); rivals get links and the normal offset only.
   - Exact per-region LORO refits are rejected (Q1 c).
2. **Same test rows.** Score on exactly the saved `test_preds.parquet` rows (plus `ladder/lead_L/test_preds.parquet`). Join on (unit, time, lead). Rows our run dropped (H4, S1) stay dropped. Test y is checked only at scoring time (rule 15).
3. **Same train rows.** Bank units' rows with a valid label at or before the cut (fit/context.py:582-596). Assert the train row-key hash equals `fitctx_log.row_key_hash` (bank, lead 0; bank_inner for tuning) and `lead.json.donor_row_key_hash` (other leads).
4. **Same columns.**
   - The kept tree columns + history columns + the declared router context + the unit's normal. No unit ID, no extra geography.
   - Assert `manifest.feature_list_hash` on the tree + history block only (it holds tree + history columns: pm25 122, ndvi 498, fire 131, defo 308, coral 63). Check the context columns against plan.json `context` separately. Record where each normal came from (context and cut).
   - Missing values: tree rivals get the engine's 0-fill (R30, pipeline/stages.py:161-171). Ridge gets the train-row mean + a missing-flag column, disclosed (Q7).
5. **The normal: leak-free, per lead, per link, and given as an offset.**
   - The engine builds each normal at one cut and one link, and refuses a mismatch (pipeline/stages.py:208-229). Bank-unit normals exist only at the fit cut (fitctx_log: `ctx_fit normal` 16,510 entries = 12,700 bank + 3,810 scored on pm25; `ctx_inner normal` 3,810 = scored units only).
   - So the export builds the normal itself, with the engine's `unit_normals`, per lead and in each trial's link:
     - **fit-cut normal** for refit rows and test rows;
     - **guard-cut normal** for tuning-fit rows, inner (decision) rows and guard rows (the inner context at lead 0, the guard context at each lead L).
   - The history block and c follow the same rule.
   - Assert that no tuning or guard feature comes from a label after guard_cut (fitctx `max_label_time`).
   - **Offset (Q16).** Our router carries the normal as an unpenalised column, so trees-off equals the normal (PREREGISTRATION_DRAFT.md:71-72). Rivals get the same: the link-space normal is a fixed offset. GBMs: `init_score` / `base_margin`. RF and Ridge: target = link(y) - link-normal, added back after. The normal also stays as an ordinary column.
6. **Same cuts.** Read `fit_cut`, `guard_cut` and `inner_fit_end_step` per lead from each run's `derived.json`. Never derive new ones. **The cut applies to the label (target) step, not the issue step**, as the engine does (ladder.py:769-772). Assert per row that no label after the cut enters a fit.
7. **Leads.** At lead L, the whole feature row is taken at the issue step t-L (H3, OWNER_RULINGS_2026-09-28.md:97). One fit per lead at that lead's fit_cut. Leads: pm25, ndvi, fire 0/6/12 months; defo 0/1 year; coral 0/183/365 days (from `lead_{0,183,365}.parquet` as published).
8. **Tuning on the inner window only.**
   - Every trial fits on rows up to the inner-fit end and is scored on the same decision rows our layer used (`inner_preds.parquet`: pm25 68,559; ndvi 68,999; fire 68,901; defo 276,822; coral 2,046).
   - The pick is the lowest inner MAE over setting x link x checkpoint. corr2 and predict-zero are logged beside each trial.
   - Round checkpoints come from one staged fit, scored on inner rows only, so they are leak-free.
   - **One pre-registered extension:** if the pick is at the last checkpoint (1600), the same staged fit continues once to 3200, still scored on inner rows only. The pick is flagged either way. No other extension.
   - A pick at the alpha edge (1e6) is flagged; the grid is not extended.
   - Tuning is done once, on the nowcast. The pick (setting + link + rounds) is pinned at every lead, as our arm is (O4 a).
9. **Bins and scaling.** Bin edges (LightGBM, XGBoost) and standardisation (Ridge, MLP) are built from each fit's own train rows only. Tuning fits use rows up to the inner-fit end; refits use rows up to the fit cut. Within one fit's rows, one binned set is reused across settings and links (`set_label`, `set_init_score` / `set_base_margin`).
10. **Links.** Back-transform with no smearing. Clip to each row's `legal_min`/`legal_max` and save the pre-clip value. NEVER import rivals.py `_clip`, which caps every non-coral target at 1 (rivals.py:145-148). The loss is squared error, except the labelled C5 (Tweedie) and C6 (L1).
11. **Randomness.** `random_state=0` everywhere, never varied. One fixed thread count (8) for the whole board, with `threadpool_info` saved. sklearnex is patched and disclosed (ruling C), with its pip version in the manifest.
12. **Safety net, same as ours (O2 c).** Each rival gets our N2 guard on its own guard rows (with guard-cut normals, rule 5).
    - Comparator: inner_preds `<link>_trees_off_unweighted` for the rival's chosen link, as our guard does (ladder.py:839-844).
    - Test fallback: test_preds `arm__<link>_trees_off_unweighted` (coral: the donor median).
    - Guarded-vs-headline decides. Raw-vs-raw is printed beside it.
13. **Metrics.** The LIVE engine's own functions, imported read-only: `anomaly_r2` (report/metrics.py:580), `calibration_ratio` (:623), `hit_tolerance` (:665), `group_jackknife` (:1032), `contrast_tag` (:1097). Print MAE (headline), anomaly-R2 (not coral), corr2, hit rate at the run's own tolerance, and the 2c rows. Pooled, macro, per year and per group. NDVI also gets the row without its seen_during_design groups.
14. **Zero-heavy guard.** Fire is 96.8% zeros, defo 62%, coral 57%. Print predict-zero MAE, detection, calibration ratio and corr2 on every row. A rival MAE win with calibration ratio < 0.5, or corr2 below half of ours, gets a "timid win" flag. The verdict is not changed.
15. **What "ours beats rival X" means.** d_g = MAE_rival(g) - MAE_ours(g) per scored group, all groups weighted the same. Group jackknife over 127 / 133 / 40 / 42 / 37 groups. The tag comes from `contrast_tag` with each run's own band from `verdict.json`: pm25 0.0462, ndvi 0.000597, fire 1.36e-5, defo 1.10e-4, coral 0.918. BEATS = HELPS, LOSES = HURTS, otherwise EQUIVALENT or CANNOT TELL. The nowcast band decides at every lead.
16. **No rival selection on test.** Every rival is reported. No "best rival" headline.
17. **Pre-registration and the test-label lock.**
    - A new Part (next free number after 597) records the list, grids, links, threads, row-key and column hashes, the cut table, bands, code hash, output root and the 4.6 disclosure.
    - Each rival's inner pick is written to a lock file before its test labels are read.
    - The export checks test keys only. y equality (max|y difference| = 0, same row order; F65, APP_PLAN.md:589) is asserted at scoring time, after the lock, and a `test_labels_opened` record is written, as the engine does.
    - Nothing is re-tuned after a test number is seen.
18. **Save everything.** Per rival x problem x lead, one parquet keyed like `test_preds`, with y, normal, pred and pre-clip. Also every inner trial's predictions, the trial CSV, the manifest and the fold map (O2). New root `D:/treeroute/rivals/<pkg>/<stamp>/`. Never write to D:/pm25_rivals (protected) or into the headline run folders.
19. **Notes the harness prints (read from the run, not hand-set).**
    - Coral: train rows of all 83 kept groups (46 donor-only included); the 11 V5 groups stay out. Report per programme first. FRRP and AGRRA (1 group each) can only be CANNOT TELL.
    - Defo: the per-stratum (forest2000_px) table.
    - Old rival numbers (D:/pm25_rivals, the 12-cell board, coral Parts 445/450) are history only. They are never paired with the new runs.

---

## 4. HOW THE DATA GETS TO THE RIVALS

- **Coral: no export.**
  - Read the coral store path named by the run (today `D:/treeroute/coral_build/coral_store/20261020_014201/lead_{0,183,365}.parquet`) read-only (a protected root).
  - Keep the run's 83 groups, join `row_id` = `test_preds.unit` (checked 100% match), apply the 0-fill (trees) or mean + flag (Ridge). Coral leads are date-safe (feature end before the issue day at every lead).
- **Grids (pm25, ndvi, fire, defo): one small read-only export script, outside the engine.**
  - It calls the engine's own builders: Pipeline `_lock`, `_load`, `_groups`, `_preflight_target`, `_read`, `_derive` (run.py:271-298, 728-966).
  - It refuses unless the derived document equals the run's `derived.json`.
  - It never calls `_open`, because `_open` writes into the run folder (run.py:1113-1203).
  - Pools come from `RunState.build_pool` (passes.py:371-434); lead pools as in `Ladder._objects`/`_history` (ladder.py:618-645, 471-481). The pools go to the engine temp folder D:/treeroute/tmp (passes.py:397; config/machine.yaml:7).
  - It writes `D:/treeroute/rival_export/<pkg>/<run>/lead_L/<group>.parquet` with: unit, group, step, a flag (train / guard / inner / test), y for pre-cut rows, the tree + history + context columns (NaN kept raw), and **the normal per link: fit-cut and guard-cut versions** (rule 5), plus the guard-cut history block as a side file.
  - Test rows carry keys only. Test y comes from the saved `test_preds`, read only at scoring time (rule 17).
  - Fail-loud checks: row-key hashes, the tree + history column hash, context columns vs plan.json, test keys row for row, and no tuning/guard feature after guard_cut.
  - **Resumable:** each (lead, group) file is written atomically (temp file + rename) with its hash; a rerun skips finished files. The census/derive stage restarts from zero after a crash (pm25: 2,970 s + 12,733 s, about 4.4 h; pm25 run.log:33, :928).
  - **One lead at a time on NDVI** (and on any problem where disk is short): export lead 0, fit, score, delete; then the next lead. The export refuses to start unless free space on D: is at least the engine pool + one lead's export + 3 GB.
- **Sizes and export time** (float32, need-only rows; export times are EXTRAPOLATED from headline run logs that include fitting, never measured as an export):

| Problem | Columns given to rivals | Train rows (lead 0, fit cut) | Export, all leads | Export time (x) | Engine derive peak RAM |
|---|---|---|---|---|---|
| pm25 | 122 + 2 ctx + normal = 125 | 2,590,280 | 4.08 GB | ~5 h (derive alone 4.4 h: no slack) | (not logged) |
| ndvi | 498 + 9 ctx + normal = 508 | 2,680,841 | 16.66 GB (~5.6 GB per lead) | 2.5-5 h, up to +5-10 h if the derive must repeat per lead | ~6.2 GiB |
| fire | 131 + 2 ctx + normal = 134 | 751,508 | 1.38 GB | ~2.2 h | ~8.3 GiB |
| defo | 308 + 0 ctx + normal = 309 | 3,011,184 | 8.46 GB | 4-8 h | (not logged) |
| coral | 63 + 5 ctx + normal = 69 | 11,338 | 0 (reads store) | 0 | <0.5 GB |

- Ridge's missing-flag columns are added in the harness, not exported.
- **Fire's export is timed first and the plan is re-priced before pm25.**
- **Disk:** D: has about 31-33 GB free and C: 17 GB. NDVI peak = engine temp 15.3 GiB (ndvi run.log:303) + one lead's export ~5.6 GB + outputs <1 GB, so about 22-25 GB. The owner deletes each export after its scores and hashes are recorded. The export is deterministic and can be rebuilt.
- **RAM during export:** fire (~8.3 GiB) and ndvi (~6.2 GiB) are the engine's own derive. Owner command, other apps closed.

---

## 5. TIME AND RESOURCES

### 5a. How times were made

- **Measured on this PC, 8 threads** (D:\treeroute\rivals_plan\bench\results.csv and D:\treeroute\rivals_plan\verify\results.csv):
  - LightGBM: 0.633 s/round + 5.5 s at 1M x 300 (bench). 127 leaves, 40 rounds incl. Dataset build: 25.2 s, 2.50 GB (verify).
  - XGBoost at 1M x 300, colsample 0.5: depth 6 0.375 s/round, 2.88 GB; depth 10 1.00 s/round, 4.69 GB (verify). Depth 8 is taken as 0.6 s/round (bench depth 8, colsample 1.0: an upper value). 500k x 600 at depth 10 went over 4 GB in 17 s.
  - RF oneDAL, `max_samples=0.2`: 1.8 s/tree at max_features 0.5, ~0.6 s at 0.2, plus ~21 s fixed per 1M x 300. Cost per tree does not depend on total rows (36.7 s vs 38.9 s). Peak RAM is about 2.6 x the data (1M x 150: 1.77 GB; 2M x 150: 3.19 GB; old bench 1M x 300: 3.53 GB, results_raw.csv:30).
  - Ridge: 1.4 s at 1M x 300.
  - Coral-sized (12k x 70): LightGBM 2.1 s, XGBoost 8.4 s, RF 1.8 s, Ridge 0.02 s.
- **Real-data checks:**
  - LightGBM: the old gauged H trial took 1.6-2.9 min per 1000-round trial on 2.13M rows x ~107 columns (rivals.log:60-62). The bench rule predicts ~7.9 min. So "low" for LightGBM (and C5) = 0.35 x upper.
  - XGBoost: depth 6, 6.56M x 322, 400 rounds: ~15 min training + 7.8 min HDD binning (D:/defo_rivalmax/_rivalmax.log:70-72), about 0.32 s/round per 1M x 300, close to the measured 0.375. So "low" for XGBoost = 0.75 x upper. HDD binning is added at ~1.1 min per 1M x 300 per build.
  - RF: low = upper (measured at real shapes).
- **EXTRAPOLATED (x):** every grid-size number. Time scales linearly with rows x columns from the 1M x 300 points, at 1600 rounds for every GBM fit (refits run only to the pinned rounds, so this is an upper value). RF scales with columns only (fixed ~200k rows per tree).
- The old 10.5-18.6 min LightGBM G trials (rivals.log:34-37) included Board B's per-cell solve, so they are not fit times.

### 5b. Fits per learner per problem

| Problem | Links | Tuning trials (guard-cut rows) | Refits (fit cut, one per lead) | Guard fits (one per non-zero lead) |
|---|---|---|---|---|
| pm25 | 2 | 8 on 2,133,214 rows | 3 | 2 |
| ndvi | 1 | 4 on 2,205,498 rows | 3 | 2 |
| fire | 3 | 12 on 609,838 rows | 3 | 2 |
| defo | 3 | 12 on 2,446,587 rows | 2 | 1 |
| coral | 3 | 12 on 9,292 rows | 3 | 2 |

- C5 Tweedie: 8 tuning trials (no links) + the same refits and guard fits. The nowcast guard reuses the tuning fit.
- Upper per GBM fit (x): LightGBM ~17 min and XGBoost ~13-16 min per (1M rows x 300 columns) at 1600 rounds. NDVI fit-cut size = 4.5 of those units; defo 3.1; pm25 1.1; fire 0.34.

### 5c. Totals (hours of fitting; upper / low; all x except coral)

| Problem | Ridge | RF | XGBoost | LightGBM | C5 Tweedie | Core total (upper) | Core total (low) | Peak RAM, fitting (x) | Disk peak |
|---|---|---|---|---|---|---|---|---|---|
| pm25 | 0.1 | 0.7 | 3.0 / 2.3 | 3.4 / 1.2 | - | 7.2 | 4.3 | GBMs ~2-3 GB; RF ~4.3 GB | ~4.1 GB export + engine temp |
| ndvi | 0.3 | 2.0 (stride 4) | 9.5 / 7.1 | 10.2 / 3.6 | - | 22.0 | 13.0 | LightGBM ~3 GB; **XGBoost ~5-6 GB (smoke decides)**; RF ~4.5 GB (stride) | **~22-25 GB** (per lead) |
| fire | 0.05 | 0.9 | 1.2 / 0.9 | 1.4 / 0.5 | 1.1 / 0.4 | 4.7 | 2.8 | ~1.5-2 GB | ~1.4 GB export + engine temp |
| defo | 0.2 | 1.8 (stride 3) | 9.3 / 6.9 | 11.0 / 3.9 | 8.2 / 2.9 | 30.5 | 15.7 | XGBoost ~4-5 GB; RF ~4.2 GB (stride) | ~8.5 GB export + engine temp |
| coral (incl. C6) | ~0 | ~0 | ~0 | ~0 | ~0 | <0.2 | <0.2 | <0.5 GB (measured 0.44) | ~0 |
| **All** | **~0.7** | **~5.4** | **~23 / ~17** | **~26 / ~9** | **~9.3 / ~3.3** | **~65 h** | **~36 h** | **fitting ~6 GB; export ~8.3 GiB (fire derive)** | **~25 GB (NDVI, one lead)** |

- **Plus export:** 14-20 h (x), up to ~30 h if NDVI's derive must repeat per lead. **Plus smokes and timing checks:** ~3 h.
- **CORE GRAND TOTAL: ~53 h (low) to ~98 h (upper) of machine time, over about 8-12 overnight sessions.** Q4(b) (rounds capped at 800) would cut about 25 h from the upper value.
- **RAM notes (x):**
  - RF peak = 2.6 x the float32 data + trees (300 trees x ~3 MB at min leaf 5). Full rows: pm25 1.30 GB data -> ~4.3 GB; fire 0.40 GB -> ~2 GB; ndvi 5.45 GB -> ~14-15 GB; defo 3.72 GB -> ~10 GB. So NDVI uses every 4th bank unit (1.36 GB data) and defo every 3rd (1.24 GB), for RF only, disclosed (Q9). Each tree still sees about 200k rows.
  - XGBoost's histogram cache grows with depth and columns, and chunked loading does not shrink it. Depth is capped at 8 (Q19). A 20-round smoke at the real shape records the peak before tuning; if it is over ~8 GB, `max_cached_hist_node` is lowered, disclosed.
  - LightGBM is built from `lgb.Sequence` over the per-group files, never from a full in-RAM matrix (that would need ~7.5 GB on NDVI).
  - Ridge is chunked X'X, under 1 GB.
- **Disk outputs:** small. GBM model files are saved (tens of MB each). RF models are NOT saved (~1 GB each); their predictions are.
- **Optional add-ons (x, upper / low):**

| Add-on | Extra hours | Notes |
|---|---|---|
| O2 donor-only folds: LightGBM (10 folds x leads, refits at the pinned pick) | ~61 h upper / ~21 h low | ndvi ~35 h and defo ~16 h upper are most of it. Ridge folds <1 h. |
| Q17(a) donor-only tuning on the every-4th-block holdout | ~12 h upper / ~4 h low | Only if O2 and Q17(a). |
| O2b Board B | (b) ~1-2 h; (c) +~15 h on PM2.5 alone (APP_PLAN.md:589) | Needs O2. No coral. |
| O3 CatBoost (C12 removed it) | ~9.5 h (at 800 rounds) | NDVI and defo would need a row stride. |
| O4 MLP (CPU) | ~8 h | coral minutes, fire 0.4, pm25 1.1, defo 3.0, ndvi 3.7. |
| O5 kNN (coral only) | <0.1 h | Labelled near-copy of the router's pool step. |

### 5d. Schedule (one heavy job at a time; each grid step is an OWNER command)

| Step | What | Who | Time (low-upper, x) | Resume |
|---|---|---|---|---|
| 0 | Owner signs section 6. Write the pre-registration Part. Build the harness + export script. Unit tests on coral. | agent writes, owner signs | 1 day of work | n/a |
| 1 | **Coral**, all core rivals (C1-C6), all 3 leads. End-to-end proof: pairing, normals, locks, metrics. | owner command | <15 min | trial-level files |
| 2 | **Fire:** export (timed for real), smoke, tune, lock, refits, score. Then re-price the plan. | owner commands | 2.2 h export + 3-5 h | per-trial parquet + CSV row; skips finished trials by config hash |
| 3 | **PM2.5:** same steps. | owner commands | 5 h + 4-7 h | same |
| 4 | **Defo:** same steps. Delete the fire and pm25 exports first if disk is short. | owner commands | 4-8 h + 16-31 h | same |
| 5 | **NDVI**, one lead at a time, nowcast first (tuning lives there). Delete the defo export first. | owner commands | 2.5-15 h + 13-22 h | same |
| 6 | One board table across the 5 problems. Then the full test suite once. | agent | <1 h | n/a |
| 7 | Phase 2 (only if signed): O2 donor-only folds, Board B, O4. | owner commands | section 5c add-ons | same |

- **Owner commands** (written and tested before signing; every one is resumable and takes the lock):
  - `py -3.9 rivals_common.py export --run <run folder> --lead 0 --resume`
  - `py -3.9 rivals_common.py smoke  --run <run folder> --lead 0`
  - `py -3.9 rivals_common.py tune   --run <run folder> --resume`
  - `py -3.9 rivals_common.py lock   --run <run folder>`
  - `py -3.9 rivals_common.py refit  --run <run folder> --lead L --resume`
  - `py -3.9 rivals_common.py score  --run <run folder> --lead L`
- **Lock:** every step (export, smoke, tune, lock, refit, score) takes the engine's heavy-job lock (`HeavyJobLock` on D:/treeroute/tmp, run.py:296) and refuses to start if it is held.
- **Owner checklist before each session:**
  - The PC must not sleep.
  - Close games, browsers and other apps (about 9 GB was in use by other apps on 2026-10-20; Opera alone held ~3.5 GB during the bench).
  - A RAM watchdog stops a job at 12 GB.
  - Threads stay at 8 the whole time.
- Each long step is given to the owner as a command, never backgrounded by the agent.
- Each trial writes its result before the next one starts, so a crash loses at most one fit (NDVI: ~1.3 h upper).
- The lock file of picks is written after tuning and before any test label is read.

---

## 6. OWNER DECISION SHEET

| Q | Question | Options | RECOMMENDED | Why (one line) |
|---|---|---|---|---|
| 1 | Main "beats" board: which information? | (a) gauged global only; dropping donor-only folds is a departure from ruling D / L3 defaults and needs a deviation note; (b) gauged global + donor-only 10-fold board (Ridge + LightGBM), the signed default; (c) exact per-region LORO | **(b)**, with the donor-only folds run as phase 2 after the core board | Ruling D names gauged global AND donor-only folds (OWNER_RULINGS_2026-09-28.md:52-55) and L3 kept the defaults (:67); folds cost ~21-61 h; (c) costs ~23 h per learner on PM2.5 and starves rivals of own history. |
| 2 | Core list | C1-C6 as 2a (Ridge, RF, XGBoost, LightGBM on all; Tweedie on zero-heavy targets; hgb_l1 on coral); or add/remove | **As 2a** | The names reviewers expect, plus the rulings already made (C12). |
| 3 | RF was dropped from the PM2.5 board (Q45). Bring it back? | (a) yes, capped (~200k rows/tree); Q45's deviation note is withdrawn by this ruling; (b) keep it dropped | **(a)** | You named it now, and capped oneDAL RF costs ~5.4 h total. |
| 4 | Boosting rounds | (a) eta 0.1, staged {100 ... 1600}, one pre-registered extension to 3200 for edge picks; (b) eta 0.1, capped at 800, edge picks flagged | **(a)** | Old picks sat at the 1000-round edge; (b) saves ~25 h but invites "under-tuned". |
| 5 | Zero-heavy loss | (a) squared error + links only; (b) also LightGBM-Tweedie as core C5 on any target with legal_min 0 and >= 20% zeros (now fire, defo, coral) | **(b)** | Beat us on corr2 under the old setup (MAE-ruled since); a reviewer-expected zero-inflated loss. |
| 6 | CatBoost | (a) stay out (C12); (b) optional on all; (c) coral/fire/pm25 only | **(a)** | Ruled out in C12, adds little over XGB/LGBM, and cannot run out-of-core on NDVI. |
| 7 | Missing values | (a) trees get the engine's 0-fill; Ridge gets train-row mean + missing flag, disclosed; (b) 0-fill for all; (c) raw NaN for GBMs | **(a)** | Trees see our exact matrix; a linear model should not read 0 K as a real value. |
| 8 | Do rivals see the router context (incl. lat on pm25/fire)? | (a) yes; (b) tree columns only | **(a)** | Our router uses it. Disclose that lat is banned from our trees. |
| 9 | RF RAM with full rows: NDVI ~14-15 GB, defo ~10 GB (x) | (a) full rows (does not fit in 15.8 GB with the watchdog at 12 GB); (b) a fixed bank-unit stride for RF only (NDVI every 4th, defo every 3rd; data <= ~1.3 GB), disclosed; (c) min leaf 50 only (does not shrink the data) | **(b)** | Each tree sees only ~200k rows anyway; (a) cannot run. |
| 10 | MLP | (a) out of the common set; state Q47(a): re-pair Kraft (NDVI, pending) and that no other deep model was tested; (b) optional MLP on CPU, ~8 h (coral minutes, fire 0.4, pm25 1.1, defo 3.0, ndvi 3.7) | **(a)** for now, per Q47 | Kraft is NDVI only, on old rows, and below climatology (CLAIMS_LEDGER.md:294); the ledger flags no neural rival as a weakness, so (b) is the cheap fix if you want it. |
| 11 | Safety net for rivals | (a) raw only; (b) guarded only; (c) both, guarded decides | **(c)** | Our headline answer includes the decline, so the fair pair is guarded vs guarded. |
| 12 | Tuning at leads | (a) tune on nowcast, pin; (b) re-tune per lead | **(a)** | It mirrors our pinned arm. |
| 13 | Disk | (a) one problem at a time, NDVI one lead at a time, delete after (hashes kept), export refuses if space is short; (b) buy space first | **(a)** | ~31-33 GB free; NDVI alone peaks ~22-25 GB with the engine's temp. |
| 14 | Missing libraries / GPU | Nothing is missing. GPU: (a) unused; (b) test it | **(a)** | Determinism matters more than speed, and the GPU is untested. |
| 15 | Thread count | (a) 8; (b) 6 as on the old board | **(a)** | Measured at 8. Fixed for the whole board either way. |
| 16 | How rivals get the normal | (a) as a fixed offset (init_score / base_margin; offset target for RF and Ridge), and also as a column; (b) {column only, offset} as a 2-level grid choice on inner MAE (2x tuning); (c) column only | **(a)** | Our router has the normal as an unpenalised base; as one column among 125-508 it is penalised or skipped (the old H lost to the normal, 4.85 vs 4.07). |
| 17 | Donor-only tuning (only if Q1 b) | (a) the L3 default: tune once on a holdout of every 4th overlap block, refit on the 10 folds (+~4-12 h); (b) reuse the gauged pick, with a deviation note | **(b)** | Both need the 4.6 disclosure; any leak helps the rival, so (b) is conservative for our claim and cheaper. |
| 18 | Board B (per-unit MOS) | (a) drop with a deviation note; (b) APP_PLAN 4.6 option a: Board A's pick, z from the fold models only; (c) option b: all trials on all 10 folds, about +15 h on PM2.5 | **(b) if Q1 = b, else (a)** | Q44 kept every PM2.5 board; (b) is cheap once the folds exist. Coral has no Board B. |
| 19 | XGBoost depth | (a) {6, 8}; (b) {6, 10} with `max_cached_hist_node` lowered | **(a)** | Depth 10 used 4.69 GB at 1M x 300 and ran 1.7x slower; depth 8 is the common upper choice. |

---

## 7. RISKS

| # | Risk | What we do |
|---|---|---|
| R1 | Times are extrapolated from fake-data benches. | Low/upper from real runs (LightGBM 0.35x, XGBoost 0.75x). A smoke per learner per problem re-times before each long run. Fire is re-priced before pm25. |
| R2 | RAM: XGBoost on NDVI ~5-6 GB, RF strided ~4.5 GB, fire/ndvi exports 6-8 GiB. Only ~5.9-7.3 GB was free on test days. | Owner checklist (apps closed). Watchdog at 12 GB. RF stride (Q9). XGBoost depth cap (Q19) and real-shape smoke. |
| R3 | Disk: D: is ~94% full; the engine temp adds 15.3 GiB on NDVI. | One lead at a time on NDVI; free-space check refuses to start (section 4). |
| R4 | HDD reads slow out-of-core fits. | Bin once per fit's train rows (rule 9), reuse across settings and links with `set_label` / `set_init_score` / `set_base_margin`. LightGBM via `lgb.Sequence`, `feature_pre_filter=False` (otherwise min_child_samples 200 -> 20 on one Dataset is a Fatal error on 4.6.0). |
| R5 | **sklearnex RF bug:** integer `max_samples` fits but then FAILS at predict when fewer rows are passed. A fraction works and is repeatable at random_state 0. | Always pass `max_samples` as a fraction = 200,000 / n_train. Add a test. |
| R6 | "Timid wins" on fire, defo and coral: predict-zero already beats our MAE on fire and on Reef_Check. C6 hgb_l1 is timid-prone. | Rule 14 flags. corr2, detection and calibration printed on every row. |
| R7 | Tiny bands (fire 1.36e-5) make most verdicts EQUIVALENT or CANNOT TELL. | That is honest. Print the contrasts and CIs anyway. |
| R8 | Edge picks (at 1600/3200 rounds or alpha 1e6). | Wider grids and one pre-registered extension (rule 8); flag the rest. |
| R9 | Engine drift between the headline runs and the export (LIVE 930d961c). | The export refuses unless `derived.json`, row-key hashes and column hashes match. |
| R10 | Old rival numbers mixed into the new board. rivals.py reuses its cache by length. | New stamped root. Old results are history only. Never import rivals.py. |
| R11 | Coral programmes are unbalanced: Reef_Check is 6,381 of 11,338 train rows. | Report per programme first, disclosed. |
| R12 | Export crashes: the census/derive restarts from zero (~4.4 h on pm25); NDVI's derive may repeat per lead. | Atomic per-(lead, group) files with hashes; reruns skip finished files. Run as owner commands overnight. |
| R13 | Normal leak: a fit-cut normal on inner or guard rows contains those rows' labels. | Guard-cut normals for tuning/inner/guard rows; assert on max_label_time (rule 5). |
| R14 | A second job runs at the same time and changes timings or RAM. | Every step takes the heavy-job lock. |

---

## 8. SOURCES

- Bench: D:\treeroute\rivals_plan\bench\results.csv, results_raw.csv; re-time: D:\treeroute\rivals_plan\verify\results.csv (verify_one.py, run_guarded.py).
- Real-data timings: D:/pm25_rivals/full/rivals.log:17-20 (ridge edge), :34-37 (G trials incl. Board B), :41-42 (reduced grid), :58-66 (H trials and guard fail); D:/defo_rivalmax/_rivalmax.log:70-72 (XGBoost).
- Run facts: D:/treeroute/runs/<pkg>/headline/<run>/derived.json (R22 links: pm25 identity+log_c; ndvi identity; fire/defo/coral identity+log_c+arcsine), fitctx_log.parquet (normal contexts), inner_preds/test_preds trees-off columns, verdict.json, ndvi run.log:303, pm25 run.log:33, :928.
- Rulings: OWNER_RULINGS_2026-09-28.md:52-55 (D), :67 (L3); QUESTIONS_ROUND3_HANDOFF.md:472-473 (C11, C12); PROJECT_HANDOFF.md:1481-1494; HEADLINE_QUESTIONS_AND_FIXES.md:51 (Q42-Q52), :88 (Q37), :331-334 (Q47), :460.
- Plan: APP_PLAN.md:575-591 (4.6 rivals under LORO); PREREGISTRATION_DRAFT.md:71-73.
- Engine code: pipeline/stages.py:161-171, :208-229; pipeline/ladder.py:769-772, :839-844; pipeline/run.py:271-298; pipeline/passes.py:371-434; split.py:370-476, :951-1026; report/metrics.py:580, :623, :665, :1032, :1097; config/machine.yaml:7.
- Old rival code: rivals.py:145-148 (_clip); pm25_rivals.py:66-67; defo_rivalmax.py; coral_benchmark.py.
- Old results: CORAL_EXPERIMENTS.md Parts 445, 450; CLAIMS_LEDGER.md:93, :157, :231, :294.
- Protected roots: D:/treeroute/registry/protected_roots.txt.

---

## REVIEW LOG (2026-10-20)

Each issue was checked against the source before it was applied.

| Review | # | Issue | Result | Check / reason |
|---|---|---|---|---|
| fairness | 1 | Normal at the fit cut leaks into tuning and guard rows | **FIXED** (rule 5, section 4, R13) | fitctx_log pm25: bank-unit normals only in `ctx_fit` (16,510 = 12,700 bank + 3,810 scored); `ctx_inner`/`ctx_guard_lead_L` normals = 3,810 scored only. stages.py:208-229 refuses a cut/link mismatch. |
| fairness | 2 | NDVI has one link | **FIXED** (2a, 5b, 5c) | ndvi derived.json R22 value = ["identity"]. |
| fairness | 3 | Normal as one column is a straw man | **FIXED** (rule 5 offset; Q16) | PREREGISTRATION_DRAFT.md:71-72; rivals.log:61-66 (H 4.85 vs normal 4.07, guard FAILS). The {raw, offset} grid is offered as Q16(b), not the default. |
| fairness | 4 | GBMs under-boosted; Ridge alpha at edge | **FIXED** (C3/C4 eta 0.1, staged to 1600 + one pre-registered extension to 3200; alpha to 1e6; Q4) | rivals.log:34, :36, :61-65 (ck 1000 picks at lr 0.1); :19-20 (alpha 1e4 pick). Chose eta 0.1 to 1600 (= 3200 at 0.05) to halve cost vs the reviewer's 0.05 to 3200. |
| fairness | 5 | hgb_l1 missing on coral | **FIXED** (C6) | QUESTIONS_ROUND3_HANDOFF.md:473. |
| fairness | 6 | Guard comparator/fallback not tied to a link | **FIXED** (rule 12) | inner_preds has `<link>_trees_off_unweighted`; test_preds has `arm__<link>_trees_off_unweighted`; ladder.py:839-844. |
| fairness | 7 | Export reads test y before the lock | **FIXED** (rule 17, section 4) | Keys only at export; y at scoring after the lock; `test_labels_opened` record (run folders hold test_labels_opened_lead_*.json). |
| fairness | 8 | Column-hash assert cannot pass | **FIXED** (rule 4) | Hash on tree + history block; context vs plan.json separately. |
| fairness | 9 | Cut step not stated | **FIXED** (rule 6) | ladder.py:769-772 uses label steps. |
| fairness | 10 | Bins could use inner/test rows | **FIXED** (rule 9, R4) | Bins and scaling from each fit's own train rows. |
| fairness | 11 | 0-fill wrong for Ridge | **FIXED** (C1, rule 4, Q7) | Ridge: train-row mean + missing flag, disclosed; trees keep 0-fill. |
| fairness | 12 | O2 disclosure missing; Q1 overstates ruling D | **FIXED** (O2, rule 17, Q1) | OWNER_RULINGS_2026-09-28.md:52-55; APP_PLAN.md:588. |
| fairness | 13 | Tweedie should be core | **FIXED** (C5, by a data rule: legal_min 0 and >= 20% zeros) | Core by a data rule, not by problem name (plug and predict). Rationale reworded per completeness 8. |
| feasibility | 1 | RF RAM 2.6x data, NDVI/defo do not fit | **FIXED** (5c, Q9 now recommends the stride, ATTENTION line) | verify/results.csv (1.77 / 3.19 GB); results_raw.csv:30 (3.53 GB). |
| feasibility | 2 | XGBoost times not an upper bound | **FIXED** (5a, 5c) | verify/results.csv (depth 10 1.00 s/round, depth 6 0.375); _rivalmax.log:70-72. Depth capped at 8 (Q19), so the reviewer's 9-17 h became ~17-23 h at the doubled round count. |
| feasibility | 3 | XGBoost depth-10 RAM | **FIXED** (Q19 depth {6, 8}, real-shape 20-round smoke, `max_cached_hist_node` fallback) | verify/results.csv (4.69 GB; 500k x 600 killed). |
| feasibility | 4 | RF times too low | **FIXED** (5a, 5c: ~5.4 h) | verify/results.csv (1.8 s/tree at 0.5, +21 s fixed); old 0.82 s was at max_features 0.33 (results_raw.csv:21). |
| feasibility | 5 | NDVI disk peak leaves out engine temp | **FIXED** (section 4, 5c, Q13, R3) | ndvi run.log:303 (15.29 GiB peak, pools 6.41 GiB); passes.py:397; machine.yaml:7 temp_dir D:/treeroute/tmp. |
| feasibility | 6 | LightGBM in-RAM matrix; pre-filter Fatal | **FIXED** (C4, rule 9, R4) | lgb.Sequence present in lightgbm 4.6.0 (checked). Fatal error is the reviewer's test, not re-run here. |
| feasibility | 7 | Fit harness does not take the heavy-job lock | **FIXED** (5d, R14) | run.py:296 `preflight.HeavyJobLock(root)`. |
| feasibility | 8 | Only defo described as resumable | **FIXED** (section 4, R12) | pm25 run.log:33, :928. |
| feasibility | 9 | Export times never measured as an export | **FIXED** (section 4 marked x; fire timed first, re-plan before pm25) | ndvi run.log census resumed from a checkpoint. |
| feasibility | 10 | "5 owner runs" too few | **FIXED** (8-12 sessions; owner checklist) | Follows from the new totals. |
| feasibility | 11 | No owner commands | **FIXED** (5d command list) | Commands take only a run folder. |
| feasibility | 12 | sklearnex version placeholder | **FIXED** (section 1, rule 11) | pip show: scikit-learn-intelex 2025.10.0 (checked). |
| completeness | 1 | NDVI links wrong; read from R22 | **FIXED** (2a, rule 0) | Same as fairness 2. |
| completeness | 2 | Q1 misstates ruling D; donor-only is the signed default | **FIXED** (Q1 reworded; recommends (b) as phase 2) | OWNER_RULINGS_2026-09-28.md:52-55, :67; APP_PLAN.md:582. |
| completeness | 3 | O2 tuning rule and 4.6 disclosure | **FIXED** (Q17; disclosure in O2 and rule 17) | APP_PLAN.md:588. |
| completeness | 4 | Board B gone without a decision | **FIXED** (O2b, Q18; no coral) | APP_PLAN.md:589; HEADLINE_QUESTIONS_AND_FIXES.md:51, :460. |
| completeness | 5 | hgb_l1 on coral | **FIXED** (C6) | Same as fairness 5. |
| completeness | 6 | No neural rival; Q10 reason inaccurate | **FIXED** (Q10 reworded with Q47(a); per-problem MLP cost) | HEADLINE_QUESTIONS_AND_FIXES.md:331-334; CLAIMS_LEDGER.md:157, :231, :294. |
| completeness | 7 | Plug and predict | **FIXED** (rule 0; links, c, strata, store path read from the run) | Memory rule "Plug and predict". |
| completeness | 8 | O1 rationale overstated | **FIXED** (C5 wording) | CLAIMS_LEDGER.md:93 (corr2, stale `link` row); PROJECT_HANDOFF.md:1492-1494 (MAE win). |
| completeness | 9 | 2c mis-cites; N and damped persistence are rivals | **FIXED** (2c split into own-history rivals and reference rows) | APP_PLAN.md:580; PROJECT_HANDOFF.md:1481-1488 excludes only predict-zero, persistence, hgb_l1. |
| completeness | 10 | Q3 supersedes Q45 | **FIXED** (Q3 text) | HEADLINE_QUESTIONS_AND_FIXES.md:51. |
| completeness | 11 | Q9 should cover defo | **FIXED** (Q9) | Same as feasibility 1. |
| completeness | 12 | Rounds capped at 800, never extend | **FIXED** (rule 8, Q4) | Same as fairness 4. |
| completeness | 13 | Information parity not stated | **FIXED** (rule 1 disclosures: no unit ID; GLS/correctors not given to rivals) | HEADLINE_MODEL_TABLE.md:16, :19. |
| completeness | 14 | C11 is type 2 | **FIXED** (scope note) | QUESTIONS_ROUND3_HANDOFF.md:472. |

- **Rejected:** none. Two were applied in a changed form: fairness 4 (eta 0.1 to 1600 instead of eta 0.05 to 3200; the same learning budget at half the cost) and fairness 3 (offset as the default; the {raw, offset} grid is an owner option, Q16 b).
- **Not re-checked here:** the LightGBM `feature_pre_filter` Fatal error and the reviewer's RAM/time measurements were read from D:\treeroute\rivals_plan\verify\results.csv, not re-run.
