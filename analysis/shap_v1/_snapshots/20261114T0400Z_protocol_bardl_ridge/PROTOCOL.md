# Post hoc SHAP analysis of the treeroute v1 headline runs and their rivals: protocol

Version 3, 2026-11-12. Version 1 was written before any SHAP value was computed on a real data row. The v2 and v3 smoke
tests then computed SHAP values on 40-250 rows of the real coral headline and on synthetic engine smoke worlds, as
plumbing (2 regions; no statistic was read as a result). v3 changes sections 3 and 8 after those smokes, because two
design reviewers found that the code and the text disagreed and that several statistics were biased. The changes and
their reasons are in section 14. Sections 3 (the sample) and 8 (the statistics) are frozen once the first sample file is
registered in `SAMPLE_REGISTER.txt` (no sample is registered yet: every smoke used its own register under `smoke/`).

## 1. Rulings and status

- Owner rulings of 2026-11-12, section AW of `engine/OWNER_RULINGS_2026-10-06.md`:
  - AW1: SHAP on the treeroute v1 headline runs of all five problems; the results go into the paper.
  - AW2: SHAP on every rival it can be run on; the paper says which rivals were left out and why.
  - AW3: a table of how the models disagree in their SHAP results, problem by problem.
  - AW4: several agreement statistics, Spearman's rank correlation among them, with uncertainty from a bootstrap
    over regions.
  - AW5: a fixed sample of N = 1,000 test rows per problem and lead in scope, the same rows for every model.
- Owner rulings of 2026-11-13, section AY of the same file (the answer "Scope (i), as advised"):
  - AY1: scope (i), the nowcast (lead 0) of each problem (section 2).
  - AY2: D14 (b), `--recorded-path-map` (section 12).
  - AY3: D8's alternative, a true relative 1e-12 on arcsine arms only (section 12); the coral pilot had already run
    with it.
- **Post hoc (ruling AK).** Every table, figure and sentence from this analysis is labelled post hoc. No reported
  headline number changes: the analysis reads the saved predictions and decisions and never re-decides anything.
- **Scope.** Which leads are in scope is the owner's choice (AW5). Section 2 gives the options and their costs. This
  round only designed and smoke-tested the analysis. The long computations are commands for the owner (`RUN_COMMANDS.md`).
  The owner chose scope (i) on 2026-11-13 (AY1).
- **Where things are written.** Everything goes under `D:/treeroute/analysis/shap_v1` (the scripts refuse any other
  target, junctions resolved). Run folders, the registry, rival boards, exports, the engine folder and the paper folder
  are only read.

## 2. Scope options and costs (owner decision)

Trees decide the kept (reported) prediction at 7 of the 14 reported problem-leads: coral 0 and 183, PM2.5 0 and 6,
NDVI 0, burned fraction (fire) 0, forest loss (defo) 0 and 1. At the other 7 the kept prediction is a feature-free
baseline, so treeroute has no feature attribution there: coral 365 keeps the donor-row median; PM2.5 12, NDVI 6 and 12,
and fire 6 and 12 keep identity trees-off, which equals the seasonal normal exactly. The rivals are still explained at
those leads.

Wall times per problem for N = 1,000, single job on the owner's machine, v3 figures (two SHAP walks per tree: the
feature and the variable level). The per-step breakdown, RAM and disk are in `RUN_COMMANDS.md`. All the tree leads of a
problem are rebuilt in one engine process, so the census and derive run once.

| Problem | (i) nowcast | + (ii) one forecast lead | + (iii) every reported lead |
|---|---|---|---|
| coral | 17-22 min | + 15-19 min (lead 183) | + 7 min (lead 365: rivals only) |
| PM2.5 | 6.9-7.5 h | + 2.4-3.1 h (lead 6) | + 0.9-1.3 h (lead 12: rivals only) |
| NDVI | 21-25 h (fresh census; D9 is not available as first designed, see D9) | + 2.0-2.8 h (lead 6: rivals only) | + 2.0-2.8 h (lead 12: rivals only) |
| fire | 2.8-3.3 h | + 0.4 h (lead 6: rivals only) | + 0.4 h (lead 12: rivals only) |
| defo | 12-14 h (42 regions; 21 regions save about 1.75 h) | + 7-9 h (lead 1) | none |
| **total** | **43-50 h** | **55-66 h** | **59-71 h** |

The estimates exclude waiting for room (the engine's RAM and disk waits). The coral pilot's log refines the SHAP-step
rates before any longer command is given a firm time. PM2.5, NDVI and fire also need owner decision D14 (section 12);
without it their rebuild stops at the input pre-check E3a within 15 s to 3.5 min, not after hours.

**Ruled 2026-11-13 (AY1): scope (i)**, the nowcast of each problem (43-50 h in all); the coral nowcast pilot is part of
it.

## 3. The sample (AW5) - frozen with the first registered sample

- **Frame.** For each problem, the test rows that every model in the comparison covers at every lead in scope, keyed by
  (unit, time = target step). That means rows present in the headline run's saved test predictions of every reported
  lead, with a finite label, and in every included rival's saved predictions at those leads. The sample is
  lead-invariant: the same (unit, time) keys are explained at every lead.
- **Generator.** No library random stream is used. Every choice sorts candidates by SHA-256 of the text
  `shap_v1|AW5|<problem>|<what>|<key>` (first 8 bytes, big-endian) and takes them in that order. This generator is
  fixed, recorded and does not depend on a library version.
- **Gridded problems (PM2.5, NDVI, fire, defo).**
  - Strata are region x test year.
  - Per region, n_loc = ceil(N / (G x Y)) scored units are taken in hash order among the units that have a frame row in
    every test year (G regions, Y = 4 test years). For each chosen unit and test year, one row is taken: the first in
    hash order among that unit-year's frame rows. On monthly problems this picks the month at random, independently per
    unit-year.
  - The result is trimmed to exactly N rows by dropping rows in reverse hash order. A region keeps at least one unit.
  - PM2.5 (G = 127) and NDVI (G = 133) give 2 units per region; fire (G = 40) gives 7; defo (G = 42) gives 6. For
    defo, G is an owner parameter (D10): the default is all 42 regions; with 21 regions (the first 21 in hash order),
    each region gets 12 units.
  - Few locations with several time steps each: each sampled unit is explained in all 4 test years, so the routers are
    rebuilt for few units.
- **Coral (table rows).**
  - Strata are region x test year over the 37 regions with test rows.
  - Allocation is equal per region, capped by availability, and the rows left over are given in turn to the regions
    that still have rows (water-filling).
  - Within a region, years take turns (round robin in year order) and rows are taken in hash order within each year.
- **The background keys (B2, section 5).** Written per lead with the sample. A key the run's own test pass left out of
  the treeroute router fit for missing context (`context_missing/test_pass.parquet` at lead 0,
  `lead_<L>_test_pass.parquet` at a forecast lead, rows with cut kind `fit`) is removed for every model before
  registration; the count is recorded (smoke: 0 at every lead of PM2.5, fire, defo and coral, 491 keys at NDVI lead 12).
- **Exclusions, decided before any SHAP value.** A row is dropped from the frame if any explained or background row of
  it holds a feature with |value| >= 2^31 - 1 (the int32 NoData sentinel, in any model's inputs), or if it has no
  background row left. Both counts are recorded.
- **Registration.** `scripts/make_sample.py` writes `sample/<problem>/sample.parquet` and `background_lead_<L>.parquet`
  and appends their SHA-256, N, the defo regions and the parameters to `SAMPLE_REGISTER.txt` before any SHAP script may
  run. A problem's sample is registered once per folder: a second run with identical content writes nothing, one with
  other content is refused; a new sample needs a new `--tag`, which names a new folder `sample/<problem>__<tag>/`. Every
  SHAP script refuses a sample or background file whose hash is not the registered one, and the runner refuses a
  command whose `--n` or `--defo-regions` differ from the registered sample's. N is an argument of every script
  (default 1,000).
- **Exactness rows.** The exactness check covers every test row of every sampled unit (every location's 48 monthly or
  4 annual test rows; all 2,312 coral visits), not only the N explained rows.

## 4. Rebuild or load, with the exactness check (stop rule S-EXACT)

A model gets SHAP values only after it reproduces its saved predictions. **The tolerance is bit identity** (max
|rebuilt - saved| = 0, NaN and +-inf in the same places) on every checked row, for both the pre-clip and the clipped
columns. Every model here is deterministic given its inputs, library versions and thread settings, so a last-bit
difference means some input, library, thread setting or math function differs. A model that fails gets no SHAP value;
the report names it and the gate. A looser tolerance applies only by an explicit owner ruling, recorded here (D8).

### 4.1 treeroute v1 (`scripts/tr_rebuild.py`)

The fitted trees were not kept: the engine deletes its checkpoint folders when a run finishes. Each problem is rebuilt
outside the run folders by the engine's own code:

- **Engine code.** Each run's own engine snapshot, checked by the engine's code hash against the run manifest (D1):
  PM2.5 `D:/treeroute/ckpt_20261013/engine_before` (6d19c3e2); NDVI, fire, defo
  `D:/treeroute/analysis/ablation_perlocation/ckproof/engine_65a177bc` (13838e41); coral
  `D:/treeroute/engine_v2/engine_v1_ref` (85c64b55, equal to LIVE). The packages are read from the LIVE engine's
  `datasets` folder (or, under D14 (a), from a copy at the recorded path).
- **Interpreter.** `py -3.9 -I -B` with the engine's launcher pins: BLAS 4, oneDAL 4 threads, router workers 8 at
  BLAS 1. The library versions must equal the manifest's `versions` block (E2).
- **Machine file.** `machine_shap.yaml` puts the run root and the temp folder inside this folder. Never run another
  engine job at the same time: the temp-folder lock here does not see `D:/treeroute/tmp`.
- **Steps.**
  1. The engine's own steps: lock, load, groups, target listing (the RAM pre-flight), then the input pre-check E3a, then
     read, derive, open, temp.
  2. The nowcast pool, or the lead's pool with features moved to t - L.
  3. The bank that made the kept predictions: the fit-cut bank of the nowcast, or the lead's fit-cut ("lagtrain") bank.
     The inner-cut and guard-cut banks are not rebuilt.
  4. The GLS weight model, only for a weighted arm (coral 0 and 183, fire 0).
  5. The kept arm routed at the adopted penalty for the sampled units only. The run's own decision (arm, penalty, guard
     outcome, fallback levels) is read from `adoption*.json`, `decision_checks.json` and `ladder/lead_<L>/lead.json`,
     never recomputed.
  6. No scoring and no decision step runs. Test labels are never opened.
- **Gates.** They run in this order; each failure stops the problem-lead (exit 3):
  - E1: the engine code hash (`engine_code_hash`, comments stripped) equals the manifest's.
  - E2: the library versions and Python equal the manifest's.
  - E0: the engine's own RAM pre-flight does not predict a refusal after the census (fire needs about 8.4 GiB free;
    the override is `--ignore-ram-warning`).
  - E3a (v3), before the target is read: the package fingerprint, kind, package, groups, trees per group, engine
    constants, the target and static file lists, context, strata, draft and the tree-feature list, key by key against
    the manifest's config.
  - E3m (only under D14 (b)): every file the recorded path map renamed has today's content SHA-256, size and mtime
    equal to every freeze-lock record of its recorded path (`D:/treeroute/registry/freeze/FREEZE_*.lock.json`).
  - E3, after the derive: the package fingerprint, `derived_sha256` and the run fingerprint equal the manifest's.
  - E4: the donor rows (count and row-key hash) equal `fitctx_log.parquet` / `lead.json`.
  - E5, informational only: the bank fingerprint (SHA-256 over every node array of every tree, corrector and placebo).
    It moved on coral at leads 0 and 183 while every tree answer stayed bit-identical (E5a, E8 on identity and log_c
    arms, E10). The cause is NOT established (impurity, weighted node counts and missing_go_to_left all enter the
    fingerprint; the rebuilt features are bit-identical to the old export). The answer-level gates decide.
  - E5a: for an arcsine arm, its identity-link twin from the same pass (same tool and weighting, saved in the run's
    nowcast `test_preds.parquet`) is bit-identical on every checked row: the bank, correctors, GLS weights and solver
    without the arcsine math.
  - E5b: at a lead where the twin is not saved (coral 183), the lead's identity trees-off arm (the pass's own
    trees-off kernel) is bit-identical on every checked row: a partial twin (intercept and context, no trees).
  - E6: c and the guard tolerances equal the run's records.
  - E7: the GLS weight model's record equals `gls_weight_model.json` (weighted arms).
  - E9: the captured coefficients reproduce the engine kernel's own output bit for bit. Per-unit and neighbour kinds:
    X b equals the kernel's prediction on every fit. Region kind (v3): the engine's `region_predict` with the captured
    fit gives the pass's eta bit for bit on every sampled score row, both on the store's answers and on our exported
    trees' answers.
  - E8: `pre__<arm>` and `arm__<arm>` are bit-identical on every test row of every sampled unit. For an arcsine arm
    only, and only under owner decision D8, a TRUE relative tolerance applies: |rebuilt - saved| <= tol x |saved|
    (`--arcsine-tolerance`, proposed 1e-12), exact equality where saved is 0, NaN in the same places. It is licensed
    only by E5a at this lead, or (no saved twin) by a passing lead-0 E5a in this process or in lead 0's `gates.json`
    under the same engine code, libraries, run fingerprint and identity, together with E5b. `gates.json` records which
    evidence licensed it.
  - E10: our exported tree arrays and evaluator reproduce the engine's float32 tree-answer store bit for bit:
    per-unit and neighbour kinds on a sampled unit or visit (all its fit and test rows, all its trees, correctors
    included); region kind on every sampled unit's score rows and rows at or before the cut, every tree of the region.
- **Coefficients.** The router's coefficients are captured while the engine's own kernel solves: the kernel's
  `route.solve.solve_point` and `solve_point_weighted` (and `region_ridge` and `region._route` for defo) are wrapped, the
  engine's outputs are returned unchanged, and E9 checks them. Non-sampled units are skipped at the router's work list,
  after the pass's unit plan and context standardisation were formed over every scored unit; each unit's bytes do not
  depend on the others (smoke: restricted and full routing give the same bytes).
- **Resume.** A finished lead (`DONE.json`) is reused only under the same identity: the registered sample's SHA-256,
  the engine folder, the path decision (D14), the script's own SHA-256, and the D8 tolerance unless its E8 was
  bit-identical (a D8 reversal or a new sample redoes the lead).

### 4.2 Rivals (`scripts/rival_shap.py`)

Every rival runs in `py -3.9 -I -B` with the boards' pins (OMP, OPENBLAS, MKL, NUMEXPR = 8 before numpy loads) and the
boards' own code from `D:/treeroute/rivals_build` (imported read-only, bytecode off). S-ENV (v3): before any data is
read, the installed library versions and the thread pins must equal the board's `board.json` (`versions`, `threads`).

| Rival | Problems | Kept model | Load or rebuild | Check against |
|---|---|---|---|---|
| ridge | all | `model_ridge.json` | the harness's per-block design (`RidgeDesign.block`, 65,536-row blocks) | `preds_ridge.parquet` `pre__rival_ridge`, every test row |
| LightGBM | all | `model_lgbm.txt` | lightgbm 4.6.0 Booster at the pinned iteration | `preds_lgbm.parquet`, every test row |
| LightGBM Tweedie | coral, fire, defo | `model_lgbm_tweedie.txt` | as LightGBM, offset log(max(normal, c)) | `preds_lgbm_tweedie.parquet` |
| HistGradientBoosting L1 | coral | `model_hgb_l1.pkl` | scikit-learn 1.6.1 unpickle | `preds_hgb_l1.parquet` |
| random forest (RF) | all | not kept (plan 5c) | rebuilt with the board's own `rf_forest` (same draws, same out-of-core batches, oneDAL at 8 threads); every fitted tree is saved | `preds_rf.parquet` and `done_rf.json` `fit_info.samples_sha256` |
| BARDL (published) | NDVI | `map_bardl_h1.json` (per-unit BayesianRidge coefficients) | the adapter's own `design()` | `preds_bardl_h1.parquet` `pre`, every test row (loader NOT built yet) |
| Kraft LSTM (published) | NDVI lead 0 | weights in `map_kraft_lstm.json` | torch is not installed; a numpy forward pass gives max abs diff 5.2e-7, not bit-identical | owner decision D7 |

Each tree model's walk evaluator is checked against the model's own predict (raw scores) on every explained AND every
background row, within 1e-9 link units (S-EVAL); the resume identity of a learner holds the sample, the background
file, the model files, the board's records and every helper module's SHA-256.

## 5. Attribution method

- **Value function (decision D3).** Interventional (baseline) Shapley values with a per-row background shared by every
  model. For explained row x and background rows B(x), the value of a set S of players is the mean over b in B(x) of
  f(x_S, b_rest), the model's link-space output when the players in S take x's values.
  - **B2 (primary).** The explained row's own unit: rows labelled at or before the lead's fit cut, with the same season
    key as the explained row's target step (calendar month; defo is annual, so all of the unit's rows), that are
    treeroute router fit rows (section 3 removes the rows the run left out for missing context, for every model). For
    coral, B2 is the visit's saved 50-visit router pool (`pools_test_pass.parquet` of the lead): other sites' visits.
    About 17 rows on PM2.5 and NDVI, 13-16 on fire and up to 19 on defo. Every model writes its background keys
    (`background_keys.parquet`) and the comparison refuses models whose keys differ (S-BG).
  - What B2 means: on the gridded problems the attributions explain how this 2020-2023 forecast differs from the same
    location's forecasts for the same calendar month (defo: all years) of the training years. Columns that are constant
    within a unit (static columns, latitude, the month, the seasonal normal) are then exactly 0, and trending columns
    take credit for level shifts. Coral is the exception: its background is a pool of other sites, so static and
    calendar columns are not zero there.
  - **B1 (sensitivity, treeroute only).** All of the unit's router fit rows at or before the cut (it carries the
    seasonal cycle); written to `treeroute_B1/`, never pooled with the B2 models. Not defined for coral.
  - LightGBM's built-in `pred_contrib` (path-dependent) is a cross-check only.
- **Exact interventional TreeSHAP** (`scripts/shapv1_treeshap.py`). It walks the hybrid points of every (x, b) pair,
  exactly, for any map of columns to players. Checked against brute-force Shapley values over every coalition on
  scikit-learn, oneDAL, LightGBM and HistGradientBoosting trees, on a LightGBM model trained with a duplicated column
  (merged player), on a per-node-draw tree using both copies, and on a grouped game (smoke S2: max error 4.4e-16). No
  package is installed.
- **Players and the two levels.**
  - Feature level: one player per distinct column. A context column that is an exact copy of a tree column (the name
    rule `c__ctx:top5:<v>` -> `x__<v>`, then bitwise equality on every explained and background row) is the SAME player,
    inside the walk: for a model that splits on both copies (per-node draws: RF, scikit-learn) the sum of two separate
    players is not the merged player's Shapley value (smoke: 0.035 apart on a toy tree). For treeroute the context
    enters linearly and separately, so its merged value is the tree part plus the linear part, exactly.
  - Variable level: the exact Shapley values of the grouped game (the same walk with poc = the variable map), plus the
    linear terms per variable. The variable rule is in section 8.
  - Missing flags of ridge fold into their column; the offset (the run's link-space normal) and the normal input go to
    the player `normal`.
- **Linear terms (v3).** Every linear and offset term is coef x mean over b of (x_i - x_b), the per-pair difference
  taken first, so a player equal on every background row gets exactly 0 (the v2 form coef x (x_i - mean_b x_b) left a
  one-ulp residue on 50-78% of such rows).
- **treeroute.** For row i of unit u (per-unit kind), with router coefficients b and tree answers A_k:
  - eta_i = b0 + b1 (n_u(s_i) - nbar_u) + sum_c b_c z_ic + sum_k b_k A_k(x_i).
  - A_k = fl32(T_k) on plain arms; on corrector arms A_k = fl32(fl32(T_k) + fl32(C_k)), added in float32.
  - Tree terms: phi_ij = sum_k b_k [phi_j(T_k) + phi_j(C_k)], T_k with its leaf values rounded to float32.
  - The intercept is in the base: base_i = mean over B of eta. GLS weights change b only and have no term.
  - R_i = sum_k b_k (eps_k(x_i) - mean_B eps_k): the float32 addition residual of corrector answers, unattributed.
  - The neighbour kind (coral): b per visit, with 5 standardised context columns and no normal.
  - The region kind (defo): b per region. The engine evaluates the tree block as a float32 dot product; our evaluator
    sums in float64. G_i = eta_engine - eta_ours is reported apart from R and must lie within the float32 summation
    bound gamma_(n+1) x sum_k |w_k A_k(x_i)| (n = the region's tree columns), on every explained and background row
    (smoke: G at most 2% of its bound).
- **Rivals.** LightGBM, Tweedie, HGB and RF: exact interventional TreeSHAP of the raw model in its own link space
  (Tweedie in log mu). Ridge and BARDL: exact linear SHAP; BARDL's 3-month means split exactly over their three lag
  players.
- **Stop rules checked on every explained row** (`scripts/shapv1_rows.py`):
  - S-ADD: |base_i + sum_j phi_ij + R_i - eta_i| <= 1e-9 at both levels, and no NaN in eta, eta_model, base or phi;
  - S-EVAL: our evaluator equals the engine's or the model's link value within 1e-9 on every explained and background
    row (the region kind: G within its float32 bound);
  - S-ZERO: a player whose columns equal the explained row's on every background row has phi exactly 0, in every
    model, at both levels;
  - S-RESID: a row whose unattributed part |R_i| + |G_i| exceeds 1% of |eta_i - base_i| (+1e-9) is flagged; a model
    with more than 1% flagged rows stops.
- **Scale (decision D4, v3).** Link space only. The y-unit view of v1/v2 is removed (its error measurement on restricted
  games was never built, and its base was not a common y reference). Fire's kept nowcast is exactly 0 on 75.4% of rows
  after the arcsine inverse: link-space attributions there describe a latent value the forecast does not show, so the
  comparison also reports each arcsine model's importances on its rows with a nonzero forecast.

## 6. Approximations and their measured error

- The float32 addition residual R of corrector arms and the float32-dot gap G of defo's region router: reported per
  row, with the maximum and the share of |eta - base| (stop rule S-RESID).
- The Kraft LSTM, if approved (D7): grouped permutation Shapley with its Monte Carlo standard error per row, and its
  error against exact enumeration on 20 rows (12 groups).

Everything else is exact up to float64 rounding.

## 7. Rivals covered and left out

- **Covered (exact)**, at every lead in scope, including leads where the rival's own guard failed: such a rival is
  labelled "raw model, declined by its guard" and kept out of Kendall's W, the consensus and the main-text row (D6; at
  the nowcast: fire ridge).
  - Ridge, LightGBM and RF on all five problems.
  - LightGBM Tweedie on coral, fire and defo.
  - HistGradientBoosting L1 on coral.
  - BARDL on NDVI. Its rebuild was verified bit for bit by the rival map (`adapters/ndvi_bardl.design()`, 95,184 of
    95,184 rows at leads 0, 6 and 12), but its loader is not yet in `rival_shap.py`; it is to be added and smoke-tested
    before the NDVI run.
- **Approximate, pending the owner (D7):** Kraft LSTM, NDVI lead 0. Its guard failed. It is not bit-reproducible without
  torch 2.8.0.
- **Left out, with the reason printed in the paper:**
  - One-input maps of a product or index, whose attribution is trivially 100% on that one input: NOAA Coral Reef Watch
    DHW (isotonic map, F2) and Outlook (linear map on anomalies, F3) for coral, MERRA-2 PM2.5 in its three forms (per
    location, shrunk to linear; same month; the placebo), and VT0007 calibrated (isotonic on anomalies, F4). The CRW
    Outlook could instead be shown as a labelled reference row (D15).
  - Not a function of the rows' input columns at all: VT0007 as shipped and VT0007 frozen at 2019 (the index value as
    the product gives it, F0).
  - Baselines with no input features: the seasonal normal, the last-5-years normal, predict-zero, persistence, damped
    persistence, coral's donor-row median and last visit. There is no SHAP to compute.
  - Rivals that were never run: EAC4 (ruling AG1) and the burned-fraction published rivals (ruling AS).

## 8. Comparison and statistics (AW3, AW4) - frozen with the first registered sample

- **Players (two levels).**
  - Feature level: one player per distinct input column (`x__`, `c__`) plus `normal`; exact duplicates merged as in
    section 5.
  - Variable level (the main-text level): the variable of a column is its name with its lag (`_lag<k>`), aggregate
    (`_mean`, `_min`, `_max`) and window (`_<k>`, `_<k>m`, `_<k>mo`, `_roll<k>`, `_wytd`, `_all`) suffixes stripped
    repeatedly and a catalog code `V<nn>_` dropped; own-history columns keep their stem (`hist_last`, `hist_mean`);
    context columns are `calendar` (month and harmonics) or `ctx:<name>`; a duplicate context column is its tree
    column's variable. Examples: dhw_84 and dhw_90 -> dhw; frost_days_mean/_min/_max -> frost_days;
    V06_spei_12m_lag12 and spei_01m_lag12 -> spei. The rule may leave some variants apart (wbal_mm and wbal_roll3);
    the map of every model is written to `meta.json` and `per_lead.json`.
  - Families, for shares: own history (`hist_*`), global indices (a variable all of whose columns take one value per
    time step across every unit of the lead's test set), local drivers, context and calendar, the seasonal normal. A
    family's attribution on a row is the sum of its variables' (variable-level) phi on that row.
- **Active set J (per level).** The players to which some model gives more than 1e-12 of its total mean |phi|. The
  others are listed as structural zeros (smoke, coral: `normal` and four constant cyclone columns).
- **Importance vectors per model.** I_m(j): the region-weighted mean |phi_ij| (each region weighs 1); shares
  s_m(j) = I_m(j) / sum over J; the signed mean S_m(j); the number of nonzero players.
- **Model sets.** A pair is same-link when both models explain in the same link space (same link, c and ub), else
  cross-link. Cross-link statistics are reported and labelled "not comparable in scale or rank" (shares and ranks
  depend on the link) and never pooled. The main set is treeroute plus its same-link, guard-passing rivals; at a lead
  without treeroute SHAP, the largest same-link set of guard-passing rivals (ties by link name). Main sets in the smoke
  maps: coral treeroute, LightGBM, RF, HGB (arcsine); PM2.5 and NDVI all models (log_c; identity); defo treeroute,
  LightGBM, RF, ridge (log_c); fire treeroute alone (arcsine; every rival is log_c or log mu), so for fire the main row
  states that treeroute-against-rival agreement cannot separate the link from the model.
- **Pairwise statistics, every pair, both levels, on J:**
  - Spearman's rho on average ranks, over J and over the union of the two top-20 sets;
  - Kendall's tau-b with the tie correction;
  - Jaccard similarity of the top-5 and top-10 sets (and top-20 when J has 200 or more players), ties broken by name;
  - RBO on the full rankings over J (equal length, ties broken by name; eq. 32 of Webber, Moffat and Zobel 2010 reduces
    to its finite form), p = 0.9 and 0.95;
  - the total-variation distance between shares (feature or variable level) and between family shares;
  - sign agreement of S_m on the union of the two top-10 sets, among the players whose sign is determined in both
    models (determined: the bootstrap 95% interval of the signed mean excludes 0), with that count.
- **Per problem-lead statistics:** Kendall's W over the main set with the tie correction; the mean of the pairwise
  Spearman correlations of the main set (computed directly: (mW - 1)/(m - 1) is exact only when every ranking has the
  same ties); each model's stability under region resampling (the mean Spearman between its full-sample importances
  and its own bootstrap replicates: descriptive, not a ceiling on between-model agreement).
- **Uncertainty.** A paired cluster bootstrap over regions: B = 2,000 draws of regions with replacement, the same
  draws for every model. The draw matrix comes from the SHA-256 generator with the salt `shap_v1|AW4|<problem>|<lead>`
  and is saved with its SHA-256. The importances, every statistic and every number of the main-text row are recomputed
  per draw. Percentile 95% intervals, each with its number of finite replicates. BCa is not computed. With 37-133
  regions the intervals may under-cover; this is said.
- **Main-text row (variable level).** The main set; Kendall's W [CI]; treeroute against its same-link rivals: the
  median of the top-20-union Spearman [CI] and the range; RBO (p 0.9) of treeroute against the rivals' consensus (the
  mean of their shares, rebuilt per draw) [CI]; treeroute's top 3 variables; the consensus top 3; the own-history share
  of treeroute [CI] and of the median rival [CI]. All-J Spearman, the feature level and the cross-link pairs go to
  S3.13.
- **Arcsine models' nonzero forecasts.** For every arcsine-link model, the variable-level importances on its rows with
  a nonzero forecast (pre > 0) are also reported (fire).
- **No p-values.** If the owner wants a test, it must be specified before the first registration: for example a
  bootstrap test of rho(treeroute, rival) against the median rho among the rivals, with Holm over the family of every
  problem-lead and rival in scope.
- **The statistics code is checked on constructed examples with known answers** (smoke S1): identical, reversed and
  tied rankings against scipy, a textbook W, the mean pairwise Spearman under unequal ties, the RBO closed form, the case
  where the nonzero-list RBO of v2 overstated agreement (1.0 against 0.29), and the bootstrap path against the direct
  one.

## 9. Outputs (row level first)

For each `out/<problem>/lead_<L>/<model>/` (treeroute, rival_<learner>):

- `rows.parquet`: keys, region, base, eta (our evaluator), eta_model (the model's own), pre (y units), R, G, the
  additivity error, the S-RESID flag, phi__<player> (feature level) and phiv__<variable> (variable level), link space;
- `background_keys.parquet`: the (row, unit, time) background keys of every explained row;
- `meta.json`: players, variables, the variable map, merged duplicates, link, guard, every check with its maximum;
- `exactness.json` (rivals) and the rebuild's `gates.json`;
- `rows.parquet.done.json`: the inputs hash (sample, background file, model or rebuild files, scripts), the file hash
  and the sample's SHA-256. A finished piece whose files still have these hashes is skipped on a re-run.

Aggregates in `out/<problem>/lead_<L>/compare/`: `importance.parquet`, `families.parquet`, `pairs.parquet`,
`per_lead.json`, `bootstrap_draws.npy` (SHA-256 in `per_lead.json`), `bootstrap_stats.parquet`, `AW3_table.md`,
`AW4_table.md`, `AW4_main_row.json`.

Not for any archive or share: `engine_runs/`, `engine_tmp/` and the smoke worlds' `*engine_runs*` and `*engine_tmp*`
folders. The engine writes its own files there, and its checkpoint `key.json` files record input paths that include
the Windows account name (smoke: one such file, the fire world's census key). `scripts/shapv1_common.py`
`privacy_scan()` finds account and host names in every other file (smoke: none). Row-level coral files stay out of the
public archive, as coral rows' answers do (S9.6 items 8 and 9; decision D13).

## 10. What goes into the paper, and what is not claimed

- **Main text.** One compact post hoc table, one row per problem and lead in scope, at the variable level (section 8).
- **Supplement.** A new section S3.13 (post hoc, ruling AK): the AW3 tables per problem-lead at both levels (pairs x
  statistics with intervals, same-link and cross-link labelled, declined rivals labelled; each model's top-10 with
  shares; family shares; arcsine models' nonzero rows), the AW4 statistics, the exactness gates, the rivals covered
  and left out with reasons, and the method paragraph (interventional TreeSHAP with per-row backgrounds).
- **Not claimed.**
  - SHAP shows what a model uses to move its forecast away from the background, not what causes the outcome.
  - Under B2 the statements are about how a 2020-2023 forecast differs from the same location's same-season forecasts
    of the training years: columns constant within a location are 0 by construction, not unused, and trending columns
    take credit for level shifts. Coral's background is other sites' visits, so there static and calendar columns can
    carry attribution.
  - Agreement in rankings is not correctness: models that agree may lean on the same proxies.
  - No comparison across links: cross-link pairs are not comparable in scale or rank.
  - A zero does not mean irrelevant: correlated features split attribution arbitrarily (the variable level reduces
    this), and interventional hybrids are off-manifold.
  - Fire's link-space ranks do not describe its nonzero forecasts (reported apart).
  - Own-history features stand for persistence, not a driver. Fire-neighbourhood and burn columns mean contagion or
    co-occurrence. Coral columns may identify the survey programme.
  - Single coefficients of trees or regions are not explanations.
  - Everything is post hoc, on a sample of 1,000 rows per problem and lead.

## 11. Stop rules

- **S-EXACT.** A model that does not reproduce its saved predictions bit for bit on every checked row (or, for an
  arcsine arm under D8, within the licensed relative tolerance) gets no SHAP value. The report names the gate.
- **S-ENV.** A rival whose environment is not its board's stops before reading data.
- **S-SAMPLE.** No script runs on a sample or background file whose SHA-256 is not in the register; the comparison
  refuses models made for another sample or other rows.
- **S-BG.** A registered background key that is not a treeroute router fit row stops treeroute's SHAP; models with
  other background keys are not compared.
- **S-ADD, S-EVAL, S-ZERO, S-RESID.** As in section 5.
- **S-PATH.** Every script refuses to write outside this folder, or into a protected place.
- **S-ENGINE.** A treeroute rebuild refuses an engine whose code hash differs from the run manifest's, unless the owner
  rules option A (LIVE engine for all, relying on gates E3-E10).
- **S-GLS.** A weighted arm whose GLS weight model differs from its record cannot be rebuilt exactly.

## 12. Decisions for the owner (defaults in force until ruled)

| Item | Default | Alternatives |
|---|---|---|
| D1 engine | each run's own snapshot, gated by its code hash | (A) LIVE for all, gates E3-E10 decide |
| D2 TreeSHAP | our numpy interventional TreeSHAP (no install) | the shap package in a venv inside this folder |
| D3 background | B2 (same unit, same season, router fit rows; coral the saved pool); B1 for treeroute as a sensitivity | B1 primary; coral: the region's training visits |
| D4 scale | link space only (v3) | build a y-unit view with its error measured on restricted games, before the first registration |
| D5 declined leads | treeroute "no feature attribution (feature-free baseline kept)"; rivals explained | also explain the pinned arm, labelled (about +9 h rebuild) |
| D6 rival guard failed | explain the raw model, labelled; kept out of W, the consensus and the main row | drop at those leads |
| D7 Kraft LSTM | left out until ruled (not bit-reproducible) | numpy forward within 1e-6 + grouped permutation Shapley; torch 2.8.0 venv |
| D8 tolerance | bit identity: coral 0 and 183 and fire 0 (arcsine arms) stop at E8 | a TRUE relative 1e-12 on arcsine arms only, licensed by E5a (or lead-0 E5a + E5b). Evidence below |
| D9 NDVI census copy | not available as first designed: the three census checkpoints hold the run's old engine path, so the proof tool's condition (A) fails | only with D14 (a) (the copy at the recorded path makes the key parts equal without editing the hash-pinned tool), then `checkpoint_proof.py check`; saves about 15-17 h |
| D10 sample | N = 1,000; all regions (defo 42) | defo 21 regions; coral all 2,312 visits |
| D11 statistics | as section 8 | a pre-specified test (section 8) |
| D12 keep rebuilt trees | yes (RF about 0.5 GB per large forest per lead; banks 0.1-0.4 GB) | delete after SHAP |
| D13 archive | coral row files, `engine_runs/`, `engine_tmp/` kept out of any archive or share | archive coral rows |
| D14 moved package (new) | none: PM2.5, NDVI and fire stop at E3a (their static table moved with the reinstall) | (b) `--recorded-path-map`: hash today's files under the run's recorded engine path, accepted by gate E3m; (a) a real copy of the package folder at the recorded path, made by an administrator with `robocopy /COPY:DAT /DCOPY:T`, read with `--package-dir` |
| D15 CRW Outlook | left out (one-input linear map) | a labelled reference row in AW3 |

**Ruled 2026-11-13 (rulings file, section AY):** D8 takes its alternative, the true relative 1e-12 on arcsine arms only
(AY3); D14 takes option (b), `--recorded-path-map` (AY2), so D9 stays unavailable; the scope is (i) (AY1, section 2).
Every other item keeps its default.

**D8 evidence (coral pilot, real headline, engine 85c64b55).**
- Lead 0, kept arcsine arm: 2,228 of 2,312 rows bit-equal; the rest within 2.1e-14 y units, 1.06e-15 relative, 8 ulps.
- Lead 183 (first exercised in v3): 2,232 of 2,312 bit-equal; within 1.4e-14, 9.3e-15 relative, 58 ulps.
- Every identity and log_c arm of the same passes: 2,312 of 2,312 bit-identical (lead 0 diagnosis: identity_plain,
  identity_corrector_gls, log_c_plain); the identity twin E5a at lead 0 and the trees-off twin E5b at lead 183:
  2,312 of 2,312.
- The arcsine link itself changed in the last bit after the reinstall: today's numpy recomputes the stored arcsine
  normals bit for bit on only 3,590 of 3,597 fire unit-months, against log_c 3,597 of 3,597 (fire), log 3,600 of 3,600
  (PM2.5) and identity 2,201 of 2,201 (NDVI). The forward link changes the router's targets and anchors too, so the
  arcsine arm's coefficients reproduce to within the measured last-bit level, while the identity and log_c arms
  reproduce bit for bit.
- What 1e-12 relative means: at most 4,500 ulps; for fire (values around 1e-3), at most about 1e-15 absolute; exact
  where the saved value is 0.

## 13. Sources of the costs

- Run logs (stage times, read with `log_timeline.py`) and `tables.json` store timings.
- The rival boards' `done_*.json` and the rival map's measured rebuilds: coral RF 7 s; fire RF 162 s at lead 0; PM2.5 RF
  trees of 32,100 leaves at 7-8 s each.
- The map calibration of the numpy TreeSHAP (29-61 ms per depth-8 tree for 1,000 rows x 14 background rows), doubled
  for the variable-level walk (coral measured: one walk 50 s, two walks 100 s for 250 rows).
- v3 coral measurements: rebuild of leads 0 and 183 in one process 6.6 min; treeroute SHAP 100 s and the five rivals
  93 s for 250 rows; input pre-checks 15 s (defo) to 3.5 min (NDVI).

## 14. Change log

- v1 2026-11-12: first version, before any SHAP value on a real row.
- v2 2026-11-12, after the smoke tests: E5 informational, E5a and E9 added; D8 evidence; costs for one engine process
  per problem; the BARDL loader noted as still to be built.
- v3 2026-11-12, after two design reviews. Made before any registration; the coral smokes of v2 and v3 had computed
  SHAP values on 40-250 real coral rows in 2 regions (plumbing; no statistic was read as a result), and every change
  below answers a method finding, not a value.
  - Section 2: costs for two walks per tree; NDVI and the totals without D9; D14 added (PM2.5, NDVI and fire hash
    their static table under the run's old engine path, so v2's commands would have stopped at E3 after 1.9-17 h).
  - Section 3: background keys the router left out for missing context removed for every model; a sample registered
    once per folder; the runner checks N and the defo regions against the register.
  - Section 4: E0 (RAM), E3a (before the read), E3m (D14), E5 described as unexplained, E5b, a true relative D8
    tolerance with its licence recorded, E9 and E10 made real for the region kind, resume identity, S-ENV, bit checks
    including +-inf, background-row evaluator checks.
  - Section 5: per-pair linear differences (exact structural zeros, S-ZERO); duplicates merged inside the walk; the
    variable level; G of the region kind with its float32 bound; S-RESID; the y-unit view removed; the B2 meaning and
    the coral exception stated.
  - Section 7: accurate reasons for the left-out products (VT0007 shipped and frozen are not functions of the rows'
    inputs; the CRW Outlook is a one-input linear map); D6 labels kept out of W and the consensus.
  - Section 8, before the freeze: group attribution as a sum of phi per row (v2's code summed shares of mean |phi|);
    the variable level and the families; same-link and cross-link pairs; RBO on full rankings (v2's nonzero lists
    overstated agreement); the mean Spearman computed directly; "self-agreement (noise ceiling)" renamed stability
    under region resampling, with no ceiling claim; every main-row number bootstrapped; signs determined by their
    bootstrap interval; finite-replicate counts; the global-index rule on the lead's test set (v2's text said the
    sample's rows); Jaccard top-20 only when J has 200 or more players; BCa dropped; the top-20-union Spearman in the
    main text.
  - Section 9: the privacy rule for engine-written folders.
- 2026-11-13, no method change: the owner's rulings AY1-AY3 (scope (i); D14 (b); D8's 1e-12 alternative) recorded in
  sections 1, 2 and 12. Sections 3 and 8 are untouched.
