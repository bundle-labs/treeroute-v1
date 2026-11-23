# Pre-registration Part: the common rivals (type 1), the lean board

> **Status: DRAFT, UNSIGNED.** Written 2026-10-20 by the rivals build task, from RIVALS_PLAN_COMMON.md, owner
> ruling Y (OWNER_RULINGS_2026-10-06.md section Y, Y1-Y4) and the three reviews of the build (leak-fairness,
> parity, robustness). Updated 2026-10-21 for owner ruling Z (Z1-Z4: the pm25 accepted engine difference, the
> out-of-core Random Forest, the rest as recommended) and the two Z checks, and again on 2026-10-21 for owner ruling
> AA (AA1-AA5: no donor-only board, early stopping in the LightGBM tuning, the lean export; its 63-bin tuning is
> withdrawn), the AA check and the two AA reviews, and again on 2026-10-21 for owner ruling AC (AC1-AC4: 255 bins in
> tuning and refit, the extension only for a trial that ran to the 800 cap, the out-of-core Random Forest kept) and
> the AC check (change notes at the end). Nothing here is signed. Where this text and a ruling differ, the ruling
> wins.
>
> **What it covers.** The common rival board of the five finished headline runs: pm25, ndvi, fire, defo (grids)
> and coral (table). It is signed BEFORE any rival test score (rulings Y4, Z4). No rival test score exists when it
> is signed: the only rival numbers so far are inner-window (tuning) numbers of the coral DRY pass, which reads no
> test row.
>
> **What it leaves out, on purpose:** type-2 rivals (the method each field uses; ruling C11 belongs there); phase 2
> (the donor-only 10-fold board and Board B; ruling Y3 Q1 b, Q17, Q18 b; dropped by ruling AA1, section 9 item 4);
> XGBoost (dropped, Y1); CatBoost and the MLP (Q6 a, Q10 a).
>
> **Open items:** none. Ruling Y's items were settled by ruling Z (section 10); rulings AA and AC are built into the
> code of section 1 (sections 10a and 10b).

## 1. The frozen state

- Rival code (the files the board runs; `rivals/tests` excluded). SHA-256 of each file's bytes:

| File | SHA-256 |
|---|---|
| rivals/__init__.py | a4540fb8d6de819c545ba4ab961eceb47b1766b3e2d46f4047090fd5edd1279c |
| rivals/cli.py | 8b29a22abaa86bca8944f9431d38cc4ae6442f456f6dd0e73609fb878360967b |
| rivals/export.py | 826b8740ded502650287f9df00953981af2da33a2d70f6d246648825d7b60511 |
| rivals/harness.py | 372dc6c27605ca11fdab64a5151002e8c76485fae1127f006aff8012c01a5cdc |
| rivals/layout.py | b4004c1212a8b0d21c66a0246f447294218309a689ce46da23453cb9daa04168 |
| rivals/models.py | adfc8d06ed25ef6aae40aab12ad63f03255cd6334ea216047afa38e79b598e42 |

- Harness code hash (`harness.harness_code_sha()`, the hash every board.json records and every later command
  re-checks): **46d0306af3b67f15edf36d8c1fd6ac5e47a1fac06bdf33548b9c88f4decc9485**.
- Engine: LIVE, file sha **930d961c** (stripped 85c64b55). The export records it; every board pins it at init and
  refuses any later command if LIVE changes (parity review 1). The engine is read-only to the rivals.
- Libraries: lightgbm 4.6.0, scikit-learn 1.6.1, scikit-learn-intelex 2025.10.0 (sklearn patched, ruling C),
  numpy, pandas, pyarrow and threadpoolctl as recorded in each board.json. 8 threads for the whole board.
- Production config: `D:\treeroute\rivals_build\rivals_production.yaml` (the engine's own machine file, so the
  heavy-job lock is the engine's). It also holds, as DATA, the one accepted engine difference (pm25, ruling Z1;
  section 3 item 18). Its evidence files are kept in `D:\treeroute\rivals_build\evidence\z1\` and pinned by
  SHA-256. Outputs: exports under `D:/treeroute/rival_export`, boards under `D:/treeroute/rivals/<package>/<run>`,
  fit-set copies under `D:/treeroute/rivals_scratch`.
- The runs (read-only):

| Problem | Run | Links (R22) | c (R23, lead 0) | Band (verdict.json) | Groups (jackknife) |
|---|---|---|---|---|---|
| pm25 | runs/pm25/headline/20261007_74e67609 | identity, log_c | from the run | 0.0462 | 127 |
| ndvi | runs/ndvi/headline/20261016_d1de3158 | identity | none | 0.000597 | 133 |
| fire | runs/fire/headline/20261017_869d1f38 | identity, log_c, arcsine | from the run | 1.36e-5 | 40 |
| defo | runs/defo/headline/20261017_d71c61f4 | identity, log_c, arcsine | from the run | 1.10e-4 | 42 |
| coral | runs/coral/headline/20261020_f3b8e3da | identity, log_c, arcsine | 0.1084375 | 0.918 | 37 |

  Every value in this table is read by the code from the run; the table is for checking only (plug and predict:
  no problem name is in the rival code; a test scans for one). The pm25 headline is the run of 2026-10-07; it is
  NOT re-run or retrained (ruling Z1).

## 2. The lean board (ruling Y1)

| # | Rival | Runs on | Loss | Grid (tuned on the inner window only) | Fixed |
|---|---|---|---|---|---|
| C1 | Ridge | all 5 | squared error | alpha {0.1, 1, 10, 100, 1e3, 1e4, 1e5, 1e6} x each R22 link (one X'X pass per link) | float64 chunked X'X, numpy Cholesky; columns standardised on the fit's own rows; train-row mean + a missing flag per column (Q7 a); intercept unpenalised |
| C2 | Random Forest | all 5 | squared error | max_features {0.2, 0.5} x min_samples_leaf {5, 50} x each link | out of core (ruling Z2, section 3 item 19): 300 trees; each tree is one sklearnex (oneDAL) RandomForestRegressor(n_estimators=1, bootstrap=False) fitted on its OWN sample of min(200,000, n_fit) rows drawn with replacement from ALL fit-set rows; the draws come from one generator, random_state 0; 8 threads; RF RAM budget 4.5 GiB |
| C4 | LightGBM | all 5 | squared error | num_leaves {31, 127} x min_child_samples {20, 200} x each link; the round count: any round of one tuning fit per trial, cap 800, stopped early with patience 150 on the inner window (AA2 as amended by AD, section 3 item 20) | learning rate 0.1, feature_fraction 0.5, no bagging, deterministic, force_row_wise, feature_pre_filter off, seed 0, 8 threads; LightGBM's default 255 histogram bins in tuning AND in every final fit (AC1, section 3 item 21) |
| C5 | LightGBM-Tweedie | a target with legal_min 0 AND at least 20% zero lead-0 refit labels (a data rule; today fire, defo, coral) | Tweedie | C4's 4 settings x power {1.2, 1.5} (no link: its log link is built in) | as C4; offset log(max(normal, c)) with the run's own c |
| C6 | hgb_l1 (labelled "timid-prone") | coral only (ruling C12; owner flag `--extra-learners hgb_l1`) | absolute error | max_leaf_nodes {31, 127} x min_samples_leaf {20, 200} x each link; iterations {100, 200, 400, 800} | sklearn HistGradientBoosting, learning rate 0.1, no early stopping, random_state 0 |

- **Dropped: XGBoost (C3), to save machine time (Y1).** LightGBM is the boosting rival. Disclosed (section 9).
- Trials per learner = settings x links: on a 3-link run Ridge 3 fits (24 candidates), RF 12, LightGBM 12,
  Tweedie 8, hgb_l1 12. Our own layer's inner candidate count is printed beside (coral: 424).

## 3. The protocol (one rule set for every rival, problem and lead)

1. **Same rows.** The rivals fit on the run's own bank-unit rows up to each cut. The export rebuilds them with the
   engine's own builders and refuses unless the row-key hashes, counts and newest label equal the run's fitctx_log
   (P1-P3). The test rows are exactly the run's saved test rows, joined on (unit, time, lead) (P6, F65). Every
   rival, the Random Forest included, sees ALL of these rows (no row stride; ruling Z2).
2. **Same columns.** The run's kept tree columns + history columns + the declared router context + the unit's
   normal. No unit ID. Context (lat on pm25 and fire included) is given to rivals because our router uses it (Q8 a).
3. **Same normal, leak-free.** Fit-cut normal (and history block) on refit and test rows; guard-cut normal (and
   history block) on tune, inner, guard-fit and guard rows. The normal is a fixed OFFSET (LightGBM: residual label
   with a zero init score, the same squared-error fit as init_score = normal (ruling Z3); Tweedie: init_score; RF
   and Ridge: target minus the normal, added back) AND the last column (Q16 a).
4. **Same cuts.** Cuts are read from derived.json R11 and apply to the label step. The harness re-checks every row
   it reads: refit <= fit cut; tune and guard-fit <= the lead's guard cut; inner and guard after the nowcast guard
   cut and <= the lead's fit cut; test after the fit cut; issue = time - lead; no key in both a fit set and its
   score set. Any breach refuses.
5. **Same export bytes.** Every export file is checked against the SHA-256 its manifest lists before it is read; a
   stray, missing or edited file refuses. A board is bound to its lead-0 export's CONTENT hash (files, columns,
   counts, row-key hashes, cuts, c, identity; not timings), so a rebuilt export with the same bytes is accepted and
   any other is refused. Every lead's export must share lead 0's identity (run, package, engine, export code,
   derived.json, links, legal range, and the accepted engine difference record, if any) and the run's c for that
   lead.
6. **Missing values.** Trees get the engine's 0-fill (R30); Ridge gets the fit-row mean + a missing flag (Q7 a).
7. **Bins and scaling** come from each fit's own rows only (one LightGBM Dataset per fit set and link, ruling Z3;
   always 255 bins, item 21).
8. **Tuning: lead 0 only, inner window only, once.** Each trial fits on the tune rows (labels <= the nowcast guard
   cut) and is scored on our layer's own decision rows (inner_preds). The pick is the lowest inner MAE of the
   CLIPPED prediction over setting x link x checkpoint (LightGBM and Tweedie: any round the trial ran; hgb_l1: the
   stages; Ridge: the alphas; RF: 300 trees); ties: R22 link order, grid order, smaller checkpoint. The
   pick (setting, link, rounds or alpha) is pinned at every lead (Q12 a). Tuning reads the lead's fit-cut c (as
   the engine does, D63 a; disclosed in section 9).
9. **The extension rule (Y2; reading R-Y2 b, ruled by Z3; with AA2 and AC2).** The base cap is 800 rounds (hgb_l1
   is scored at the stages {100, 200, 400, 800}).
   - hgb_l1: EVERY trial whose own best inner MAE up to 800 is at 800 is extended (Z3, reading b).
   - LightGBM and Tweedie (ruling AC2): only a trial that ran to the 800 cap WITHOUT a patience stop is extended
     (its best round then lies in the last stage before the cap, (400, 800]; with patience 150, in (650, 800]). A
     trial stopped by patience is never extended: its extension would repeat it unchanged. Code: `models.ran_to_cap`
     (`models.py:212-227`; true only with no patience stop and iterations run = the cap; a missing or
     self-contradicting record refuses), `harness._extension_ids` (`harness.py:1819-1834`; a trial without an
     early-stopping record refuses) and `trials_to_extend` (`harness.py:1230-1242`). Edge case: a trial whose best is
     round 750 and that reaches 50 rounds without gain exactly at round 800 counts as stopped by patience and is not
     extended (a cap-1600 refit would stop at round 800 again).
   - An extended trial is refit FROM SCRATCH with cap 1600 (ruling Z3; LightGBM and Tweedie with the same
     patience), scored on the inner rows only; every round its base trial kept must reproduce byte for byte
     (LightGBM and Tweedie: the per-round inner MAE too); the learner is then re-picked over all its trials. A pick
     in (1200, 1600] is flagged and never extended. Ridge alphas and the RF tree count are not extended.
   - On the coral dry pass under AC no LightGBM or Tweedie trial was extended (all 20 stopped by patience, at
     rounds 85-255; the log says "extended (ran to the 800 cap without a patience stop, AC2): none"); 6 hgb_l1
     trials were, and none overtook its pick.
10. **Edge flags (printed, never acted on):** edge_rounds_100 (hgb_l1 at its first stage), edge_round_1 (LightGBM
    or Tweedie at round 1, the lowest round they can pick), edge_rounds_1600, edge_alpha_0.1, edge_alpha_1e6.
11. **Links.** Read from R22 and R23 of each run, never a hand list. Back-transform without smearing; clip to the
    run's legal range; the pre-clip value is saved.
12. **Randomness.** random_state / seed 0 everywhere, never varied. 8 threads; the thread pools are recorded at
    init and every later command refuses if they differ.
13. **Our safety net on every rival (O2 c, Q11 c).** Each rival gets our N2 guard on its own guard rows: lead 0 on
    the inner rows against the run's saved `<link>_trees_off_unweighted`; a lead L on the lead's guard rows against
    the run's saved `arm__<link>_trees_off_unweighted` (key-joined, labels checked byte for byte), rebuilt from the
    guard-cut normal only for a link the run did not save (the source is recorded per rival). Pass iff the rival's
    MAE is strictly below (engine `n2_eligible`). Guarded = raw if passed, else the run's own decline target
    (coral: the donor median). **Guarded vs our headline decides; raw vs our pinned model is printed beside.** The
    lead-0 guard model of EVERY rival, LightGBM and Tweedie included, is the tuning trial at the pick: its saved
    inner predictions at the picked checkpoint (`harness.py:2179-2194`). For LightGBM and Tweedie this is the final
    model fitted on the tune rows, because the tuning trial is binned like every final fit (255 bins, item 21) and
    the early stop only reads the trees; the refit refuses a tuning trial whose recorded bin count is not 255
    (`harness.py:2185-2190`). At a lead L >= 1 the guard model is a fit on the guard-fit rows with the final-fit
    options, scored on the guard rows. **The rival's lead-0 inner MAE and N2 verdict quoted in the paper are that
    guard's** (`lead_0/done_<learner>.json` `guard.rival_mae`, `guard.passed`); they equal the `inner_mae` and
    `n2_lead_0` of picks.json (picks.json: `inner_mae_and_n2_are_of` = "the tuning model, which is the reported
    model's lead-0 guard model").
14. **The lock.** The picks are written to picks.json and hashed into picks.json.lock.json before any test file
    or test label is read. Tune and lock refuse once any test trace exists in the board (a test-label record or a
    lead's predictions). Every lock and every test-label opening is appended to the run's ledger
    (`<out root>/_ledger/<run fingerprint>.jsonl`, outside the board folder). A lock whose picks differ from picks
    under which test labels were already opened is refused, in any board; a later board that reproduces the same
    picks may lock. Test labels are read only by `open_test_labels_rivals`, after the lock, and each opening is
    recorded with the picks hash and the test file's hash.
15. **Save everything.** Every trial's inner predictions and trial.json; trials.csv; picks; per lead and rival a
    parquet keyed like test_preds with pre-clip, raw and guarded predictions and the guard result; GBM and Ridge
    models (RF models are not saved; their predictions are); every score table.
16. **One heavy job at a time.** Every command takes the engine's heavy-job lock and refuses when it is held. A RAM
    watchdog stops a job at 12 GiB of PRIVATE memory (pages read through a memory-mapped file are not counted).
    Before every fit a go / refuse check compares the fit's planned RAM with the free RAM; for the RF it counts the
    fit rows AND the rows it predicts (Z2 check 3).
17. **No rival selection on test.** Every rival is reported. There is no "best rival" headline. Nothing is
    re-tuned after a test number is seen.
18. **The pm25 accepted engine difference (ruling Z1).** The pm25 headline (run id 20261007_74e67609) is NOT re-run
    or retrained. Its export would refuse on two engine-identity checks: I4 (no recorded no-op proof hop from its
    engine 7b508557 to LIVE) and I5 (its run config key `engine_constants_sha256` is d1592748, LIVE's is 3ef147e5:
    LIVE's constants table is the run's 117 entries unchanged plus 11 added run-mechanics constants). The owner
    ruled both acceptable for THAT run only. This is recorded as DATA in the rival config, one entry per run id,
    pinned by the run's fingerprint, the LIVE engine (930d961c), the three accepted hops (7b508557 -> 1f257395 ->
    7a0341ef -> 65a177bc; each pinned by the SHA-256 of its evidence files) and the one accepted config key at its
    exact run and LIVE values. No problem name, run id or engine sha is in the rival code. Any other difference
    still refuses. **The condition:** every byte parity check P1-P15 must pass at EVERY lead, at every level of its
    record (a nested "not checkable" or "skipped" is not a pass). P15 (the engine's own bank fit on the exported fit
    sets must reproduce the run's 6 recorded bank fingerprints) cannot be switched off for this run. The export of
    an accepted run must name every lead in one call; if any check fails, or the export stops for any reason, every
    lead manifest written so far is moved aside (never deleted), so no lead is usable, and the owner is asked. Only
    when all leads pass is a seal file written last (`ACCEPTED_ALL_LEADS.json`, listing each lead's manifest
    SHA-256); the harness refuses to start or continue a board on an accepted run without a seal that covers every
    lead and matches every lead's manifest. An entry that is not needed (the run passes I4 and I5 without it)
    refuses. The record (ruling, run id, fingerprint, the hops and the key accepted) is written into every lead's
    export manifest, board.json and board.md.
19. **The Random Forest out of core (ruling Z2).** For each RF fit, one generator (`numpy default_rng(0)`) draws,
    tree by tree in order, the tree's rows (min(200,000, n_fit) positions in [0, n_fit), with replacement, sorted)
    and then the tree's own random_state. The draws do not depend on the RAM budget, the batch sizes or a resume.
    The fit set stays on disk as a row-major float32 file (the board's fit-set copy, never written column-wise).
    Trees are taken in order into a batch while the union of the batch's rows fits in the RF budget (4.5 GiB); the
    file is read ONCE per batch, front to back, in 64 MiB row blocks, keeping only those rows (0-filled, the normal
    appended). Each tree is then fitted on exactly its own sample (oneDAL tree, bootstrap off: the draw is ours),
    predicts every score set in row blocks into a float64 sum in tree order, and is dropped. The forest prediction
    is the sum / 300. A checkpoint every 10 trees lets a killed fit resume from the last checkpoint with the same
    result. **Tested:** the trees equal those of an in-RAM fit on the same per-tree samples (node arrays and
    predictions byte-equal), also against plain sklearnex trees built by the test itself from a re-implementation
    of the draw rule; two fresh processes give byte-equal predictions across read paths, budgets, block sizes and
    thread settings; no row outside the fit set reaches a tree; RAM stays within the budget at the NDVI shape
    (200,000 rows per tree, 508 columns, a 95,184-row score set: private memory grew 1.44 GiB against a 2.25 GiB
    test budget).
20. **Early stopping in the LightGBM and Tweedie tuning (ruling AA2).** Each tuning trial of lgbm and lgbm_tweedie
    scores the inner window after every round (the engine's MAE of the clipped prediction, inner labels only) and
    stops once **150 rounds in a row** (`PATIENCE_ROUNDS`, `models.py:78`; ruling AD, was 50 under AA2) bring no strictly lower inner MAE, or at
    the cap (800; 1600 when extended). The trial's pick is its best round (ties: the earlier round; an equal value
    does not reset the patience; a round where LightGBM finds no split counts as a round without improvement). A
    tuning fit is only ever given the inner score set (`harness.py` `_run_trial` refuses any other); no test row is
    read. trial.json keeps the per-round inner MAE, and at every kept round the finished model's own prediction
    must give that MAE bit for bit. Tested: a decoy test set, or every test file overwritten with garbage, changes
    no trace, round or pick; a crash in the middle of the grid and a resume give byte-identical trials.csv, records
    and picks.
21. **Histogram bins (ruling AC1, replaces AA3).** Every fit of lgbm and lgbm_tweedie, the tuning trials AND every
    final fit (the refit at each lead's fit cut and every guard fit), bins the features into LightGBM's default
    **255** bins. One constant sets it for all of them (`LGBM_MAX_BIN = 255`, `models.py:79`; used by the tuning
    trial `harness.py:1639`, the probe `:2051` and the guard fits and refits `:2176`, `:2203-2204`). A final fit
    differs from its tuning trial only by running the picked round count with no early stopping. Each trial's
    config hash includes the bin count (`harness.py:1168-1170`, `models.py:186-199`), so a trial binned any other
    way is never reused on resume. The 63-bin tuning of AA3 is withdrawn; its code is kept, not run, in
    `_moved/20261021_preAC_code`.
22. **The lean export (ruling AA4).** The export takes two engine steps that only guard, and change no exported
    value, from the run's own record instead of measuring them again: R30's test-year missing count over every
    census row (from `derived.json` R30, only when the count would run) and the per-group separability check on a
    sample (from `per_group_plan.json`, only when it shows a pass). I5-I7 and P1-P14 always run and decide; P15
    runs with `--p15` and always on a run with an accepted engine difference (pm25, item 18). The exported files
    are byte-identical to a full export (tested on a grid toy and the defo smoke export; the AA review's own test
    ran the engine's real count path in the full export). The export switch `--full-engine-checks` runs every
    engine step; it is not used by default (section 9 item 17).

## 4. What "our model beats rival X" means

- For each scored group g: d_g = MAE_rival(g) - MAE_ours(g), every group weighted the same (engine
  `report.metrics._paired_contrast`, per-group MAE from `score_table` / `metric_by_key`).
- The tag comes from the engine's own `contrast_tag(d, band)` (rule D74), with the run's own band from verdict.json
  (the nowcast band at every lead) and the leave-one-group-out jackknife at z = 1.96 (`group_jackknife`, no
  multiplicity correction):
  - **BEATS** (engine HELPS): the interval's low end is above 0 AND the mean is at or above +band.
  - **LOSES** (HURTS): the high end is below 0 AND the mean is at or below -band.
  - **EQUIVALENT**: the whole interval lies inside [-band, +band].
  - **CANNOT TELL**: otherwise (and with fewer than 3 groups). **IDENTICAL**: every |d_g| <= 1e-12.
- **The deciding contrast:** the rival's GUARDED column vs OUR HEADLINE answer (the normal output at a lead where
  our own guard failed). Raw vs raw (the rival's raw vs our pinned model) is printed beside.
- The blocked jackknife (overlap blocks, R14) is printed beside where the run has blocks; report only.
- **Our side is tied to the run:** at lead 0 the board refuses unless our pooled MAE and every per-group MAE equal
  the run's own score_pooled.csv and score_by_group.csv (relative 1e-12). At a lead the run keeps no score file, so
  our columns are the lead's saved test_preds columns (recorded as "not checkable").
- Printed on every row: pooled MAE, corr2, calibration ratio and hit rate at the run's own tolerance, for both
  sides; predict-zero; per year and per group tables; the per-stratum tables with the run's own edges; NDVI also
  without its seen-during-design groups.
- **Timid-win flag:** a rival MAE win with calibration ratio < 0.5 or corr2 below half of ours is flagged. The
  verdict is not changed.

## 5. Order and sizes (ruling Y4)

1. coral (end to end; its real tune must reproduce the dry picks, section 7), 2. fire (export timed for real, its
`derive` time checked against the lean export's saving; `probe` before `tune`; re-price), 3. pm25 (the existing headline, under the accepted difference of section 3 item
18; all leads exported in one call), 4. defo, 5. ndvi one lead at a time (nowcast first). Each step is an owner
command (RIVALS_OWNER_COMMANDS.md). After every scored problem: the board table. After all: one full test suite.

## 6. Per-problem notes (read from the runs; printed by the harness)

| Problem | Links | Tweedie (data rule) | hgb_l1 | RF rows | Notes |
|---|---|---|---|---|---|
| pm25 | identity, log_c | no (0% zeros) | no | all fit rows | The existing headline under the accepted engine difference (section 3 item 18). Its export runs P15 (6 bank fits). |
| ndvi | identity | no (negative values) | no | all fit rows (25-30 file sweeps per RF fit) | Exported and fitted one lead at a time. Prints the row without the seen-during-design groups. |
| fire | identity, log_c, arcsine | yes (96.8% zeros) | no | all fit rows | Predict-zero beats our MAE on fire (0.00428 vs 0.00439): read every rival "win" with the timid flag. At leads 6 and 12 the run saved no arcsine trees-off, so that link's guard comparator is rebuilt from the guard-cut normal. |
| defo | identity, log_c, arcsine | yes (62% zeros) | no | all fit rows (4-13 file sweeps per RF fit) | Prints the per-stratum (forest2000_px) table. |
| coral | identity, log_c, arcsine | yes (40% zeros in the refit labels) | yes, labelled timid-prone | all fit rows | Train rows of all 83 kept groups (46 donor-only); the 11 V5 groups stay out. Report per programme first; FRRP and AGRRA (1 group each) can only be CANNOT TELL. The guard comparator and fallback are the donor median. |

## 7. The coral dry pass (inner window only; DRY, not a result)

The dry pass ran export (roles tune and inner only: no test folder), init, tune and lock, and stopped. No test row
was read and no test-label record exists. Picks under this code (picks content hash
**5ad9502f975c771ecbc7406d98a57eaba5b308d3920fbd5d77f8269e2567639b**, ruling AD, two identical passes), inner MAE:

| Rival | Pick | Inner MAE |
|---|---|---|
| Ridge | log_c, alpha 1 | 6.350 |
| RF | arcsine, max_features 0.5, min leaf 50, 300 trees | 6.690 |
| LightGBM | arcsine, 127 leaves, min child 200, round 41 | 6.385 |
| Tweedie | power 1.2, 127 leaves, min child 200, round 320 | 6.533 |
| hgb_l1 | arcsine, 127 leaf nodes, min leaf 20, 400 iterations (6 of its trials were extended) | 6.355 |

All are N2-eligible at lead 0 against the donor median (9.742). No flag. Under AC every one of these numbers is
that of the reported model's lead-0 guard (section 3 item 13), LightGBM and Tweedie included. Two passes on this
code gave the same picks content, a byte-equal trials.csv and 53 byte-equal inner prediction files (AC_CHECK_REPORT.md
section 2).

History (inner window only):
- Before ruling AA (code fb8656a9; picks content 3b5a33f1): LightGBM arcsine, 31 leaves, min child 200, 200 rounds
  (6.439); Tweedie power 1.2, 127 leaves, min child 200, 400 rounds (6.565, 2 trials extended).
- Under ruling AA (code c52babae; picks content 2a3e224e; 63-bin tuning): LightGBM arcsine, 127 leaves, min child
  200, round 63 (6.546) and Tweedie power 1.5, 31 leaves, min child 20, round 181 (6.452). Both were numbers of the
  63-bin tuning model, not of the 255-bin model AA would have reported; at 255 bins that Tweedie setting reaches
  only 6.782 (best round 134).
- Ridge, RF and hgb_l1 picked the same under all three codes, with byte-equal inner prediction files.

The board's real coral tune must reproduce the AC picks; the ledger refuses a lock with other picks once a test
label was opened.

## 8. What counts as a bug fix after signing

- A change to any file in section 1 changes the harness code hash: every board refuses it, and a new board must be
  initialised and re-tuned. A fix is allowed only if (a) it changes no pick (the ledger refuses other picks once a
  test label was opened), or (b) the owner rules on it in writing before any further test label is opened.
- A fix is logged as a new Part with the old and new code hashes, the reason and the diff.

## 9. Disclosures

1. **XGBoost was dropped to save machine time (Y1).** The boosting rival is LightGBM.
2. **The Random Forest is out of core (ruling Z2; replaces the row stride of Q9 b and item O-1).** Every RF fit sees
   all its fit-set rows; there is no bank-unit stride. Each of the 300 trees is fitted on its own sample of
   min(200,000, n_fit) rows drawn with replacement from all fit rows, from one seeded generator, so a tree's sample
   is the same as the in-RAM forest would give for the same draw. This differs from the stock RF in one way: the
   per-tree draw is ours (one generator, sorted rows) and each tree is a one-tree oneDAL forest with bootstrap off,
   not sklearn's internal bootstrap. On coral (where the old RF already used all rows) the inner MAE of the pick
   moved from 6.684 to 6.690 and three middle ranks swapped; the pick is the same. The method costs time, not
   rows: about 16-23 h of RF fitting over the four grid problems, most on NDVI (section 6, owner commands). Ruling
   AC3 kept it as built (the AC build left the RF code and the coral RF picks and predictions unchanged).
3. **The pm25 headline is not re-run (ruling Z1).** pm25's rivals are fitted on the exports of the existing
   headline run (2026-10-07, engine 7b508557), under an accepted engine difference (section 3 item 18). Two
   engine-identity checks are accepted for that run only: I4 (the hops 7b508557 -> 1f257395 -> 7a0341ef ->
   65a177bc have no parsable no-op proof; their evidence is pinned by SHA-256) and I5 (the config key
   `engine_constants_sha256`, d1592748 vs 3ef147e5; LIVE only added 11 constants). **Wording:** the text of ruling
   Z1 names I5 as "the per_group_schedule reader_builds count 24 vs 16". In the export, reader_builds 24 vs 16 is
   the one must-match difference of I4 hop 7a0341ef -> 65a177bc (a record of a resumed smoke, not a number of the
   run), and the I5 refusal is the constants hash. Both are accepted; the rulings file records this reading as a correction under ruling Z (the decision unchanged).
   The condition is byte parity P1-P15 at every lead, P15 included; if any check fails the export refuses and the
   owner is asked.
4. **Phase 2 is dropped (ruling AA1).** There is no donor-only 10-fold board and no Board B (the per-unit MOS).
   The main board is "gauged global": each rival fits on every kept group's bank units, including the target
   region's own past, as our router does. Disclosed as a departure from ruling D's default, which named the
   donor-only fold board (OWNER_RULINGS_2026-09-28.md:55) and was kept as the default by L3 (`:67`), and from Q44,
   which put every PM2.5 board, Board B included, on every problem (HEADLINE_QUESTIONS_AND_FIXES.md:51). The plan
   RIVALS_PLAN_COMMON.md (in the engine folder, read-only to this build) still lists phase 2: lines 13, 49-50 (O2,
   O2b), 215-216 (their time rows), 233, 258 (Q1) and 274 (Q17). Those items are superseded by ruling AA1.
5. **Old rival numbers are not comparable.** D:/pm25_rivals, the 12-cell board and coral Parts 445/450 used other
   rows, cuts, normals and tuning. They are history only and are never paired with these runs.
6. **Tuning reads the lead's fit-cut c** (A3, D63 a, as the engine does), so inner-window labels touch the tuning
   link's c. Measured: fit-cut c vs a tune-rows-only c, ratio 1.0000 (fire smoke) and 1.0019 (defo smoke).
7. **Coral's offset and c.** The coral rival's normal is one tune-row donor median (the guard-cut median); our inner
   rows use per-fold medians (export P10 prints the gap and does not compare it, reading R-CN). The rivals use one
   fit-cut c at lead 0, where the engine back-transforms each decision row with its own fold's c.
8. **Information parity.** Rivals see the router context (lat included on pm25 and fire; lat is banned from our
   trees). No unit ID. Our fire and coral arms use GLS weights and correctors; rivals get links and the normal
   offset only.
9. **Implementation choices (owner items O-3, O-4; ruled by Z3):** LightGBM gets the residual label link(y) - normal
   with a zero init score (the same fit, exact in float64); one binned Dataset per (fit set, link).
10. **sklearnex is patched** (ruling C); oneDAL RF does not equal stock sklearn at the same seed.
11. **The memory watchdog** counts private memory, not the resident set, so a large memory-mapped fit set does not
    stop a healthy job; all "peak GiB" numbers in rival logs are private memory. It stops a job at 12 GiB; the RF
    alone stays within its 4.5 GiB budget, and the whole NDVI RF job is estimated at about 5.2-5.8 GiB.
12. **Extension rule reading b (ruling Z3), with AC2.** Every trial that qualifies is extended, not only the
    learner's pick; this gives the rivals more tuning, never less. For hgb_l1 a trial qualifies when its own best is
    800; for LightGBM and Tweedie when it ran to the 800 cap without a patience stop (AC2, item 18).
13. **Fit-set copies are deleted by the owner (ruling Z3).** They are rebuildable caches; their hashes stay in the
    board. The code never deletes; it prints "may delete" lines after each scored lead.
14. **Early stopping, patience 150 (ruling AA2 as amended by AD; section 3 item 20).** A finite patience can stop a
    trial before a later, better round. Under patience 50 this was measured on coral (inner rows only, 255 bins): the
    Tweedie trial with 127 leaves, min child 200, power 1.2 stopped at round 225 with its best at round 175 (6.5676),
    while run on its best is round 320 (6.5330; `pt/aa/coral_bins_probe.json`). Owner ruling AD (2026-10-21) raised
    the patience to 150 before any rival test score; on the coral dry pass that trial now reaches round 320 (6.5330)
    and becomes the Tweedie pick. A patience can still, in principle, stop a trial before a later improvement; this
    is disclosed. The two LightGBM settings of the diagnostic were not affected either way.
15. **The pick is any round (AA2).** The round is chosen from up to 800 per trial (before AA, from 4 stages) on the
    same inner rows the lead-0 guard uses later. This makes the rival's lead-0 inner MAE a little optimistic and its
    guard a little easier to pass: a small tilt in the RIVAL's favour.
16. **255 bins in tuning and in every final fit (ruling AC1; section 3 item 21).** LightGBM and Tweedie are tuned
    and refit at LightGBM's default 255 histogram bins, so the reported model is the model that was tuned (the
    setting and the round count are chosen at the bins they are reported at). Ruling AA3 had tuned at 63 bins; it
    was withdrawn by AC1 before any rival test score, because a round count picked at 63 bins did not carry to a
    255-bin refit. What is checked only on toy data: that a fresh 255-bin fit at the picked round equals the tuning
    trial byte for byte (`test_aa_speedups.py:242`, both learners). On real data this equality is not checked,
    because a fresh fit's check would need a refit, which reads test files; the early-stop callback only reads the
    trees (`models.py:532-560`).
17. **The lean export (AA4; section 3 item 22).** It skips only the two engine guard steps; a wrong copied R30
    share could only make the export refuse, never change an exported value (R30 feeds a refusal gate, engine
    `derive/unit_rules.py:526-540`). The copied shares are protected by I5's data-file check and the
    `first_pass_sha256` cross-check of derived.json, not by I7 (I7 compares the copy with its own source). On pm25
    (the accepted engine difference) the shares come from the 2026-10-07 run, so the lean export cannot show an R30
    difference that LIVE's own count would give; the exported values are not affected (P15 is forced there), and
    `--full-engine-checks` (about +2.7 h on pm25) would run that audit. NDVI's own count was never timed (its
    headline loaded it from a checkpoint) and is estimated at 7-23 h, so `--full-engine-checks` is not used on NDVI.
18. **Only a trial that ran to the cap is extended (ruling AC2, amends Y2, Z3 b and AA2).** Under AA a LightGBM or
    Tweedie trial whose best round was in (400, 750] had already stopped by patience before 800, yet was refit
    from scratch to the 1600 cap, where it stopped at the same round with the same predictions. AC2 removes that
    repeat: a trial stopped by patience is never extended. This saves time and cannot change a pick, since only a
    trial that reaches the 800 cap can gain from its extension. For these two learners AC2 replaces Y2's trigger
    ("the best inner-window round count is the 800 edge") with "ran to the 800 cap without a patience stop".

## 10. Items settled by ruling Z (2026-10-21)

1. **pm25 (O-A1): settled by Z1, answer (b).** Ruling text: "(b): the pm25 headline run is NOT re-run or retrained.
   The export's engine-identity refusals for that run (I4: no recorded no-op hop from engine 7b508557; I5: the
   per_group_schedule reader_builds count 24 vs 16) are ruled acceptable for that one run, recorded as an accepted
   engine difference in the rival config (data, not code). The condition: every byte-level parity check (P1-P15
   ...) must pass. If any fails, the pm25 export refuses and the owner is asked. Disclosed in the rival Part."
   Built as section 3 item 18; disclosed as section 9 item 3 (with the I4 / I5 wording map).
2. **RF budget (O-1): replaced by Z2.** Ruling text: "No bank-unit stride. The RF rival sees ALL fit-set rows. Each
   tree draws its own row sample (the capped sample size of the plan, fixed random_state sequence) from the full
   fit set, which stays on disk as a memory-mapped file and is read in row blocks, so RAM stays within the RF
   budget. The method must give the same trees as the in-memory RF for the same per-tree samples (tested).
   Disclosed." Built as section 3 item 19 (RF budget 4.5 GiB); disclosed as section 9 item 2.
3. **R-Y2: settled by Z3, reading b** ("every trial whose own best is 800 extends"). Section 3 item 9.
4. **Deleting caches: settled by Z3** ("the owner deletes each scored lead's fit-set copies by hand (the code prints
   'may delete' lines)"). Section 9 item 13; commands in RIVALS_OWNER_COMMANDS.md section 7.
5. **Extension cost: settled by Z3** ("an extended trial is refit from scratch"). Section 3 item 9.

## 10a. Items settled by ruling AA (2026-10-21, "A + B + D + C")

1. **AA1, no donor-only board:** section 9 item 4 (the departure from ruling D, L3 and Q44).
2. **AA2, early stopping in the LightGBM tuning:** patience **50** rounds, inside the 800 cap; the pick is the best
   round on the inner window; never on test rows. Section 3 items 9 and 20; section 9 items 14 and 15. Its
   extension wording is amended by AC2 (section 10b).
3. **AA3, coarser bins: withdrawn by AC1** (section 10b). No fit uses 63 bins.
4. **AA4, lean export:** two engine guard steps skipped (the R30 test-year count, the separability check); the
   check of the time saving is the defo smoke (about 5 s saved, the separability check alone; the files
   byte-identical) and the headline logs (the R30 count: 590 s defo, 4,153 s fire, 9,830 s pm25). Section 3 item
   22; section 9 item 17.
5. **AA5, order:** built after the Z build; this draft updated; the owner signs before any rival test score.

## 10b. Items settled by ruling AC (2026-10-21, "yes to all, keep the out of core random forest")

1. **AC1, bins (replaces AA3):** LightGBM and Tweedie tune AND refit at **255** bins; the 63-bin tuning path is
   removed (its code kept in `_moved/20261021_preAC_code`). Section 2 (C4); section 3 items 7, 13 and 21; section 9
   item 16.
2. **AC2, extension (amends Y2, Z3 b and AA2):** only a LightGBM or Tweedie trial that ran to the 800 cap without a
   patience stop is extended to 1600; a trial stopped by patience never is. hgb_l1 keeps Z3 b. Section 3 item 9;
   section 9 items 12 and 18.
3. **AC3, Random Forest:** ruling Z2 stands; the out-of-core RF on all rows is kept as built (code unchanged by the
   AC build). Section 3 item 19; section 9 item 2.
4. **AC4, order:** rebuilt (harness bc62c805), the rival tests and the coral tune-only dry pass re-run (section 7;
   change notes), the new hash written here (sections 1 and 11); the owner signs before any rival test score.

## 11. Signature

- Signed by: ____________________ (owner)
- Date: ____________________
- Rival code hash at signing (section 1): 46d0306af3b67f15edf36d8c1fd6ac5e47a1fac06bdf33548b9c88f4decc9485
- SHA-256 of this file: written into the Part log by the owner after signing.
- Part number: assigned when the Part is logged (the next free number after 597 when this was written).

## Change notes

- **2026-10-21 (ruling Z build and the two Z checks; harness c298611e -> a595a9b1 -> fb8656a9).**
  - Z1: the pm25 accepted engine difference (config data, `rivals_production.yaml`). After the Z1 check: an
    accepted run must export every lead in one call (`export.py:1545-1549`); any failure moves every lead manifest
    aside (`export.py:1700-1707`, `withdraw_accepted_leads` `:1733`); a seal is written last (`write_accept_seal`
    `:1712`); the harness refuses an accepted run without a matching seal (`harness.py:595` `check_accept_seal`,
    called at `:938` export_lead and `:1368` init); the accepted record is part of every lead's identity
    (`harness.py:590`); the ACCEPT gate reads nested results (`export.py:1315` `parity_results`); an entry that
    carries nothing refuses (`export.py:1644-1650`); P15 records the peak RAM after each bank fit (`:1353`). The evidence files moved out of test-temp and scratch folders to `evidence\z1\` (same SHA-256), and
    the config note maps the Z1 wording (I5 named as reader_builds) to the two refusals.
  - Z2: the out-of-core Random Forest (`models.py` rf_forest; tests OOC1-OOC10). After the Z2 check: the RF RAM
    check counts the score rows (`harness.py:1089` ram_check, called at `:1587`, `:2096`, `:2122` with the inner,
    guard and test row counts; the refit check now runs after the test rows are loaded); the independent draw / gather / plain-sklearnex tests
    moved into `rivals/tests/test_rf_out_of_core.py` (OOC6-OOC9) and the NDVI-shape RAM test was added as OOC10
    (opt-in, RIVALS_HEAVY=1; passed: 1.44 GiB growth against a 2.25 GiB budget, 15.4 s per tree); the bench now
    measures the disk with unbuffered reads (`_bench/z2_rf_bench.py --estimate`, 118.9 MB/s; the earlier "sweep"
    rate of 2,483 MB/s was the page cache) and estimates RF time from it.
  - Z3: the items of section 10 settled as recommended.
  - Sections 1, 2, 3 (items 1, 3, 5, 7, 9, 16, 18, 19), 5, 6, 7, 9, 10 and 11 updated.
  - Tests: the full suite passed on harness 6a0bdba2 (149 passed, 4 opt-in skipped; `pt/zfin/full1.log`), OOC10
    passed with RIVALS_HEAVY=1, the defo smoke export passed (the fire smoke skipped: 4.4 GiB free RAM, it needs 5).
    Then one code comment naming the ruling id was removed (the Z1 review's no-names scan), giving fb8656a9; the
    coral dry pass, test_nonames and the Z1 review's files-only tests were re-run on fb8656a9 and pass.
  - At the time of this note ruling AA was not yet built; it is built now (next note).

- **2026-10-21 (ruling AA build, the AA check and the two AA reviews; harness fb8656a9 -> e5032ad5 -> c52babae).**
  - AA build (e5032ad5): early stopping with patience 50 and 63 bins in the LightGBM and Tweedie tuning, 255 bins
    and the picked round count in every final fit, a new 255-bin lead-0 guard fit, the lean export and the
    `--full-engine-checks` switch (SPEC_RIVALS.md 2.10, 3.4a, section 7). The AA check: full suite 166 passed, 1
    opt-in skipped (`pt/aa/check_full.log`); the coral dry pass twice, identical picks (AA_CHECK_REPORT.md).
  - AA reviews (no leak found): the "not weakened" claim of AA3 is withdrawn and disclosed (section 9 item 16);
    the any-round tilt (item 15) and the repeated extension (item 18) are disclosed; the lower-edge flag of
    LightGBM and Tweedie is now `edge_round_1` (`harness.py` `pick_flags`); picks.json names whose numbers it
    holds (`inner_mae_and_n2_are_of`), and the Part quotes the guard's numbers (section 3 item 13); the export's
    text no longer claims P15 always runs or that I5-I7 check a copied R30 share (`export.py` module text, lean
    comment and log line); the AA4 timing test keeps a time-stamped evidence file. SPEC_RIVALS.md section 7a.
  - Sections 1, 2, 3 (items 7-10, 13, 20-22), 5, 7, 9 (items 4, 14-18), 10a and 11 updated.
  - Tests on c52babae: full suite with the real-data tests 166 passed, 1 opt-in skipped (`pt/aafix/full1.log`,
    25 min); the AA review folder 26 passed, 1 xfailed (the xfail is the review's record of the AA3 weakening of
    section 9 item 16; `pt/aafix/review_aa1.log`); the coral dry pass inside the suite gave picks content 2a3e224e
    again, with trials.csv and all 53 inner prediction files byte-equal to the e5032ad5 pass.
  - Not changed, as ruled: the final fit keeps the 63-bin round count (AA3, "the picked round count"); a
    patience-stopped trial is still extended (AA2). Changing either needs a new owner ruling and a new code hash.
    (Both were changed by ruling AC; next note.)

- **2026-10-21 (ruling AC build and the AC check; harness c52babae -> bc62c805).**
  - AC1: one bin constant `LGBM_MAX_BIN = 255` (`models.py:79`) for tuning, probe, guard fits and refits;
    `TUNE_MAX_BIN` (63) and the AA3 second 255-bin lead-0 guard fit are removed; the lead-0 guard of every learner
    is the tuning trial at the pick, after a check of its recorded bins (`harness.py:2179-2194`).
  - AC2: `models.ran_to_cap` and the AC2 branch of `trials_to_extend` / `_extension_ids`; the tune log names the
    rule per learner.
  - AC3: the RF code is unchanged (no diff hunk in its part of `models.py`; `cli.py`, `export.py`, `layout.py`
    byte-equal to the pre-AC copies); the coral RF pick and inner predictions are unchanged.
  - Sections 1, 2 (C4), 3 (items 7, 9, 13, 20, 21), 7, 9 (items 2, 12, 14, 16, 18), 10a, 10b (new) and 11 updated.
    The 63-bin weakness disclosure (old section 9 item 16) is removed: the weakness no longer exists. Section 9 item
    14 now gives the 255-bin coral measurement of the patience cut.
  - Tests on bc62c805 (AC_CHECK_REPORT.md): full suite with the real-data tests 170 passed, 2 skipped
    (`pt/ac/check_full.log`, 24.4 min); the two skips were the opt-in heavy RF test and the fire smoke export
    (RAM: 3.9 GiB free). The fire smoke export was then run on its own with 5.5 GiB free and passed
    (`pt/ac/fire1.log`, 116 s; P1-P14 pass at every lead). The AA review folder 29 of 29 passed
    (`pt/ac/check_review_aa.log`). The coral dry pass twice: picks content 14b18f11 both times, trials.csv and all
    53 inner prediction files byte-equal; no test or scores folder; the read spy saw no test read; no LightGBM or
    Tweedie trial extended. The LIVE engine was unchanged.

- **2026-10-21 (ruling AD; harness bc62c805 -> 46d0306a).** PATIENCE_ROUNDS 50 -> 150 (`models.py:78`), two test
  expectations and two comments updated (old files in `_moved/<stamp>_preAD`). Tests: test_aa_speedups.py,
  test_tuning_rules.py and test_nonames.py 32 passed, 1 skipped (real-data, run separately); the coral tune-only
  dry pass twice (RIVALS_REAL=1): both passes picks content 5ad9502f..., 53 fits, peak 0.32 GiB. The Tweedie pick
  changed (power 1.2, 127 leaves, min child 200, round 320, 6.533); the other picks are unchanged. Section 9 item 14
  rewritten; the hashes in section 1 and the signature block updated. The full suite last ran on bc62c805 (170
  passed); only the patience constant and comments changed since.
