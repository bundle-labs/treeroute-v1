# Post hoc SHAP analysis of the treeroute v1 headline runs and their rivals: protocol

Version 3, 2026-11-12. Version 1 was written before any SHAP value was computed on a real data row. The v2 and v3 smoke
tests then computed SHAP values on 40-250 rows of the real coral headline and on synthetic engine smoke worlds, as
plumbing (2 regions; no statistic was read as a result). v3 changes sections 3 and 8 after those smokes, because two
design reviewers found that the code and the text disagreed and that several statistics were biased. The changes and
their reasons are in section 14. Sections 3 (the sample) and 8 (the statistics) are frozen once the first sample file is
registered in `SAMPLE_REGISTER.txt` (the coral sample was registered on 2026-11-12, the fire and PM2.5 samples on
2026-11-13 and the defo sample on 2026-11-14). Every smoke used its own register under `smoke/`, except the real-data
steps of the ridge smoke of 2026-11-14 and of its independent check, which read the registered fire and coral samples
and wrote only under `smoke/` (section 14). The loaders of two rivals, ridge outside coral and BARDL, were added after
the freeze, with no change to sections 3 and 8 (section 14).

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
- **Scope.** Which leads are in scope is the owner's choice (AW5). Section 2 gives the options and their costs. The v3
  round only designed and smoke-tested the analysis; the runs began with the coral pilot (2026-11-12 23:49 to
  2026-11-13 00:06). The long computations are commands for the owner (`RUN_COMMANDS.md`). The owner chose scope (i) on
  2026-11-13 (AY1).
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
columns (`rival_shap.py` checks the pre-clip column only: section 4.2). Every model here is deterministic given its
inputs, library versions and thread settings, so a last-bit difference means some input, library, thread setting or
math function differs. A model that fails gets no SHAP value; the report names it and the gate. A looser tolerance
applies only by an explicit owner ruling, recorded here (D8).

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

### 4.2 Rivals (`scripts/rival_shap.py`; ridge outside coral: `scripts/ridge_shap.py`; BARDL: `scripts/bardl_shap.py`)

Every rival runs in `py -3.9 -I -B` with the boards' pins (OMP, OPENBLAS, MKL, NUMEXPR = 8 before numpy loads) and the
boards' own code from `D:/treeroute/rivals_build` (imported read-only, bytecode off). S-ENV (v3): before any data is
read, the installed library versions and the thread pins must equal the board's `board.json` (`versions`, `threads`).
BARDL's board, code and inputs are the human tool's instead (below).

| Rival | Problems | Kept model | Load or rebuild | Check against |
|---|---|---|---|---|
| ridge | all | `model_ridge.json` | the board's own scoring (`rivals/models.py` `_fit_ridge`): the whole test set in the export's read order; per 65,536-row block a fresh design block (`RidgeDesign.block`) minus the saved means, times the saved coefficients of the pinned alpha, plus the intercept, with numpy's BLAS at the board's 8 threads. Fire, PM2.5, defo, NDVI: `scripts/ridge_shap.py` (below). Coral: `rival_shap.py`, which copies the same blocks into one row-ordered array (it passed there: with no missing flags the blocks are row-ordered too) | `preds_ridge.parquet` `pre__rival_ridge` and its legal clip `arm__rival_ridge_raw`, every test row (`rival_shap.py`: `pre__rival_ridge` only) |
| LightGBM | all | `model_lgbm.txt` | lightgbm 4.6.0 Booster at the pinned iteration | `preds_lgbm.parquet`, every test row |
| LightGBM Tweedie | coral, fire, defo | `model_lgbm_tweedie.txt` | as LightGBM, offset log(max(normal, c)) | `preds_lgbm_tweedie.parquet` |
| HistGradientBoosting L1 | coral | `model_hgb_l1.pkl` | scikit-learn 1.6.1 unpickle | `preds_hgb_l1.parquet` |
| random forest (RF) | all | not kept (plan 5c) | rebuilt with the board's own `rf_forest` (same draws, same out-of-core batches, oneDAL at 8 threads); every fitted tree is saved | `preds_rf.parquet` and `done_rf.json` `fit_info.samples_sha256` |
| BARDL (published) | NDVI | `map_bardl_h1.json` (per unit: the BayesianRidge coefficients and intercept, the mean and standard deviation of each standardised predictor; the unit x month climate means) | `scripts/bardl_shap.py` (below): the adapter's own `predict()` on the whole slim test copy, with the minimal context of the human tool's own test (`human_rivals_build/human/rivals_human/tests/test_h19_ndvi.py`) | `preds_bardl_h1.parquet` `pre` and its legal clip `raw`, bit for bit on every test row (95,184 at lead 0) |
| Kraft LSTM (published) | NDVI lead 0 | weights in `map_kraft_lstm.json` | torch is not installed; a numpy forward pass gives max abs diff 5.2e-7, not bit-identical | owner decision D7 |

Each tree model's walk evaluator is checked against the model's own predict (raw scores) on every explained AND every
background row, within 1e-9 link units (S-EVAL); the resume identity of a learner holds the sample, the background
file, the model files, the board's records and every helper module's SHA-256. `rival_shap.py` compares the pre-clip
column `pre__rival_<learner>` only; the saved clipped column `arm__rival_<learner>_raw` is the board's legal clip of it
(`rivals/harness.py` 1298-1299, 2245). The loaders of ridge outside coral and of BARDL check both columns, and their
evaluator checks and resume identities are given below.

Two rivals have scripts of their own, added after the freeze (section 14). They are new files: `rival_shap.py`,
`run_shap.py`, `compare_shap.py` and the shared helpers are unchanged, so every finished piece keeps its resume
identity.

**Ridge outside coral: `scripts/ridge_shap.py`** (fire, PM2.5, defo, NDVI), run after the problem's `run_shap.py`.

- **Why.** `rival_shap.py` copies the design blocks into one array stored row by row, then multiplies. The board
  multiplied each block as it was made. When the model has missing flags (fire 45, PM2.5 45, defo 145, NDVI 222), that
  block is stored column by column. numpy then calls another BLAS routine, which adds the same terms in another order,
  so the last bit can differ. Memory alignment does not matter. Coral's ridge has no flags, so its blocks are stored
  row by row too: `rival_shap.py` passed there (2,312 of 2,312 rows), and coral keeps that piece.
- **`rival_shap.py`'s ridge stops (expected).** On these four problems it stops at S-EXACT, and `run_shap.py` reports
  its rivals step as "stopped at a gate". Observed on fire (95,711 of 96,000 test rows bit-equal) and PM2.5 (70,795 of
  91,440); expected on defo and NDVI, where the same row-by-row arithmetic gives 303,967 of 369,096 and 17,451 of
  95,184. The board's own scoring reproduces every test row of all four.
- **Refusals** (exit 1; nothing is written but its log line), before any data is read: a heavy-job lock
  (`D:/treeroute/tmp/` or this folder's `engine_tmp/`); another SHAP step at work, that is a Python process whose
  command line names `run_shap`, `tr_rebuild`, `tr_shap`, `rival_shap`, `compare_shap`, `make_sample`, `bardl_shap` or
  `ridge_shap` (`run_shap.py`'s later steps hold no lock); no ridge record on the board; a done record that cannot be
  read; a changed source of a copied `rival_shap.py` function (the drift guard). Its own lineage never counts: the
  processes psutil's walk shows started it (the py launcher, the shell), or, only when that walk fails, its direct
  parent (`os.getppid()`). psutil must be importable.
- **S-ENV** also checks, before any data is read, that numpy's BLAS pool runs the board's 8 threads and that
  `board.json` `threadpool_info` lists it with that count. On synthetic blocks of the real shapes, 1 thread instead of
  8 changed a few link-space rows in the last blocks of PM2.5, NDVI and defo (10, 15 and 6 rows when stored column
  by column), never in a full block and never in fire's or coral's blocks; so this gate, not S-EXACT, guards the
  thread count. The OpenBLAS version, its CPU kernel and `OPENBLAS_CORETYPE` are recorded, not gated: a change there
  that alters any bit stops ridge at S-EXACT.
- **S-EXACT**, with no tolerance, in four stages. Inputs and bits run before the background is read; reread and repeat
  run after it, before any SHAP value:
  - inputs: the board's records agree with each other and with the export (`done_ridge.json`, `model_ridge.json`,
    `picks.json`, the SHA-256 of `preds_ridge.parquet`, `board.json`, `lead_<L>/export.json`, the export's content
    and files hashes; 20 checks at lead 0);
  - bits: the board's own scoring of the whole test set (the table above) reproduces `pre__rival_ridge` and its legal
    clip `arm__rival_ridge_raw` bit for bit on every row, with the same keys (equal values, NaN and +-inf in the same
    places). The saved ridge values are always finite (the board's inverse link and clip refuse NaN and +-inf), so a
    non-finite value on this side is the engine's refusal, recorded as an S-EXACT stop;
  - reread: the test set read for the SHAP values is the one checked, bit for bit;
  - repeat: a second scoring of the whole test set equals the first, bit for bit.
- **Its record**, `ridge_shap_exactness.json`, is written at every S-EXACT, pass or fail: the stage and the pass, the
  record checks, the bit counts of pre and raw, the keys found on one side only, each block's rows and memory order,
  the rows clipped and the SHA-256 of the link-space output. As information only, never a gate: the row-by-row copy's
  count (`rival_shap.py`'s arithmetic), `rival_shap.py`'s own counts, the full BLAS pool listing (S-ENV gates only
  numpy's pool count) and the thread and kernel switches, the board's and the LIVE engine's code hashes, and, on a
  FAIL, where the differing rows sit.
- **SHAP values.** The SHAP values, base and eta are `rival_shap.py`'s ridge arithmetic. Its functions are called. The
  lines that cannot be called alone are copied (`rival_shap.py` 312-321, adapted in 2 lines; 355-386, word for word),
  and the drift guard keeps them equal to `rival_shap.py`'s.
- **The model's own value (S-EVAL).** At an explained row, eta_model is the link value of the board's whole-test-set
  scoring; its back-transform equals the saved `pre__rival_ridge` bit for bit. At a background row it is the board's
  scoring code run on that row (the board never scored those rows). First, the evaluator's design values at the
  explained rows must equal the board's design blocks there, bit for bit. Then the shared writer checks our evaluator
  against both values within 1e-9. Coral's piece from `rival_shap.py` compares its evaluator with itself and has no
  background check; on coral the loader's model value equals that piece's, bit for bit.
- **Options.** `--n` is optional: the registered N is used, and a given N must equal it. `--exactness-only` runs S-ENV
  and S-EXACT only (no sample needed) and writes only `ridge_shap_exactness.json`; an S-EXACT stop also writes
  `FAILED.json` and removes this script's done record. `--rows` (smokes only) is refused without `--out-root`: a piece
  of K rows in `out/` would make the comparison refuse.
- **Stops (exit 3).** S-ENV, and S-SAMPLE on the sample's identity or on `--n`, write nothing but their log lines and
  leave a finished piece as it is: they come before the piece's identity is known, and a mistyped option or path does
  not disprove the piece (`compare_shap.py` checks the sample itself). The other stops (S-SAMPLE while the sample is
  read, S-EXACT,
  S-BG, S-EVAL) remove this script's own done record (never another script's), write `FAILED.json` naming the gate
  and exit 3. The shared writer's stops (S-ADD, S-EVAL, S-ZERO, S-RESID) name the failed checks in `FAILED.json`'s
  `checks_passed`. In a folder that holds another script's finished piece no stop writes anything. A passing S-EXACT
  removes this script's `FAILED.json` of an earlier S-EXACT stop at stage inputs or bits (the checks it has just
  repeated) and no other; the shared writer removes `FAILED.json` when a full run passes.
- **Records and folders.** The resume identity is `rival_shap.py`'s (problem, lead, learner, rows, the sample and
  background files, the model files, the board, the export manifest) plus the SHA-256 of `ridge_shap.py`, of every
  `rival_shap.py` helper, of the boards' scoring code and of the LIVE engine's code. The done record names the
  script. The piece is `out/<problem>/lead_<L>/rival_ridge/`; `compare_shap.py` finds it by the folder's name.
  `ridge_shap.py` never writes, moves or removes `rival_shap.py`'s `exactness.json` there, and never writes into a
  folder that holds another script's finished piece: on coral, whose piece is current under `rival_shap.py`'s own
  identity, it logs "nothing to do" and exits 0; another script's stale piece is refused (exit 1), and so is
  `--exactness-only` in such a folder. A later `run_shap.py` of the same problem stops ridge at S-EXACT again and
  rewrites only `exactness.json`; the loader's piece stays, and that run's comparison includes it.

**BARDL: `scripts/bardl_shap.py`**, the published NDVI rival, run after NDVI's `run_shap.py`. It runs like the others
(`py -3.9 -I -B`, the pins at 8), with the human tool's board, code and inputs:

- **S-ENV**, before any data table is parsed, compares the installed versions with the `versions` of its own board,
  `D:/treeroute/rivals_human/ndvi/20261016_d1de3158/human_board.json`, and the pins with that board's
  `constants.threads` (8). A board without `versions` fails.
- **Code.** It runs the human tool's adapter `D:/treeroute/human_rivals_build/human/adapters/ndvi_bardl.py` from the
  very bytes whose SHA-256 it records (in `exactness.json` and the resume identity; no board record holds that hash
  alone), with no package lookup and bytecode off. The rival's options come from
  `D:/treeroute/human_rivals_build/human/registry/ndvi.yaml`, whose SHA-256 must equal the board's
  `registry.registry` before the file is parsed. As information only, the human tool's own code hash, recomputed over
  today's files (the one file changed after the board taken from its kept copy, the five adapters added after it left
  out), equals the board's record (21 files).
- **Inputs.** The board's slim copy (`slim/lead_0`). `slim_manifest.json` must have the SHA-256 the board records.
  Every slim file must have the SHA-256 its manifest lists (checked at every read), and its recorded source SHA-256
  must equal the common export's file of the same part and group (266 of 266 files at lead 0), so BARDL's nine `x__`
  columns are the columns the other models read.
- **Records.** The saved predictions, the locked coverage mask (`preds_bardl_h1.parquet`,
  `coverage_bardl_h1.parquet`) and the run's `derived.json` must have the SHA-256 the board records, and the mask
  must match the predictions' keys and covered rows. The common board's SHA-256 and its run fields (fingerprint, c,
  ub, links, legal) must equal the human board's records, so BARDL's link key is the common NDVI rivals'
  (`identity|c=-|ub=1`).
- **S-EXACT** always predicts the whole slim test set, in the tool's own per-unit blocks, never a subset of rows: a
  row's BLAS dot can differ in the last bit with its block.
- **The model's own value (S-EVAL).** BARDL's evaluator (the sum of its terms, which its attributions add up to) is
  checked within 1e-9 against the saved `pre` on every explained row and against the adapter's own `predict()` on
  every background row.
- **Background rows (S-BG).** A background row is evaluated as the model evaluates a scored row: with the unit's
  table of monthly normals at prediction (the test set's). The background rows are designed together with their
  units' whole test sets. The test rows' design and the table must not change, the background and explained rows' own
  normals must equal the table bit for bit, and the NDVI lag values set to 0 must be exactly the missing ones, or the
  script stops at S-BG. The S-EVAL reference at the background rows is the adapter's `predict()` on those test rows
  together with the background rows; its test part can then differ from the saved `pre` by about 1e-16 (the same
  block effect). `meta.json` records this under `background_design` as information only; it is not a failure.
- **Resume identity.** The problem, lead, learner and rows, and the SHA-256 of:
  - the sample and the background file;
  - `done_bardl_h1.json`, `preds_bardl_h1.parquet`, `coverage_bardl_h1.parquet` and `map_bardl_h1.json`. No board
    record holds the map's SHA-256; S-EXACT on every test row is its proof;
  - the board's records: `human_board.json`, `human_picks.json`, the registry, `slim_manifest.json`, the run's
    `derived.json`, the export manifest and the common board;
  - the adapter, `bardl_shap.py` and its three helper modules.
- **Stops (exit 3).** No BARDL gate stop leaves a done record: a recompute removes the old one when it starts, and
  every gate stop, S-ENV and S-SAMPLE included, removes it first. Every gate stop writes `FAILED.json`, which names
  the gate, except after the writer's checks (S-ADD, S-EVAL, S-ZERO, S-RESID): it then records them under
  `checks_passed` (the failed ones false), with no gate field. An S-EXACT stop at the records or the test rows also
  writes `exactness.json` (pass false).
- A slim train file whose bytes differ from its manifest is found only while the background rows are read. The run
  then stops at S-EXACT (`FAILED.json`, detail beginning `inputs: slim file`), even though `exactness.json`, written
  earlier, says pass true. `FAILED.json` is the record that counts.

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
  (Tweedie in log mu). Ridge and BARDL: exact linear SHAP.
  - BARDL's players are the nine export columns its adapter reads (`x__hist_last_1` to `_3`; `x__V02_total_precip_mm`
    and its lags 1 and 2; `x__V30_soil_moisture_pct` and its lags 1 and 2), plus `normal` (its offset, the seasonal
    normal).
  - Each of its 11 predictors is a function of one player, except the two 3-month means, which are functions of their
    three lag players.
  - A 3-month mean is split exactly over its three lag players. Per (x, b) pair, its value is the exact Shapley value
    of that three-player term over its 8 coalitions, under the adapter's missing-value rule: a missing climate anomaly
    is 0 (ruling AG3), and a 3-month mean with a missing month is 0. When all six anomalies of the pair are present,
    this is the linear split: each lag gets a third of the term's slope times its own change.
  - At the variable level each mean term goes whole to its variable.
  - Under B2, BARDL's normals (its offset and the normals inside its NDVI-lag anomalies, all equal to the unit's
    prediction-time table, section 4.2), climate means and coefficients are the same for an explained row and its
    background rows. So its `normal` player is exactly 0, and the lag normals carry no attribution.
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
  - Ridge, LightGBM and RF on all five problems; ridge outside coral through `scripts/ridge_shap.py` (section 4.2).
  - LightGBM Tweedie on coral, fire and defo.
  - HistGradientBoosting L1 on coral.
  - BARDL on NDVI. Its rebuild was verified bit for bit by the rival map (`adapters/ndvi_bardl.design()`, 95,184 of
    95,184 rows at leads 0, 6 and 12). Its loader is `scripts/bardl_shap.py`, a script of its own, added on 2026-11-13
    after the freeze and the coral pilot and before any NDVI SHAP value. Its smoke ran on real data on 2026-11-14, on
    29 rows of the NDVI smoke sample (expected to equal the NDVI sample still to be registered) under their own
    register, as plumbing (section 14). Its guard passed at the nowcast, so it carries no D6 label.
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

For each `out/<problem>/lead_<L>/<model>/` (treeroute, rival_<learner>; outside coral, `rival_ridge/` is written by
`scripts/ridge_shap.py`; BARDL's folder is `rival_bardl_h1/`, written by `scripts/bardl_shap.py`):

- `rows.parquet`: keys, region, base, eta (our evaluator), eta_model (the model's own), pre (y units), R, G, the
  additivity error, the S-RESID flag, phi__<player> (feature level) and phiv__<variable> (variable level), link space;
- `background_keys.parquet`: the (row, unit, time) background keys of every explained row;
- `meta.json`: players, variables, the variable map, merged duplicates, link, guard, every check with its maximum;
- `exactness.json` (rivals) and the rebuild's `gates.json`. In `rival_ridge/` outside coral, `exactness.json` is
  `rival_shap.py`'s own failed check, kept as the record of why the loader exists; beside it,
  `ridge_shap_exactness.json` is the check that passed (section 4.2);
- `rows.parquet.done.json`: the inputs hash (sample, background file, model or rebuild files, scripts), the file hash
  and the sample's SHA-256. A finished piece whose files still have these hashes is skipped on a re-run.
  `ridge_shap.py`'s record also names the script.

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
  - BARDL reads nine columns by design: three NDVI lags, and precipitation and soil moisture at the issue month and the
    two months before (ruling AB: Q9 of `engine/RIVALS_PLAN_HUMAN.md`, published inputs only). Its zeros elsewhere mean
    "not an input". By the frozen plan it is in the NDVI main set when it shares treeroute's link and passes its guard
    (it passed at the nowcast; section 8; D16), so it counts in Kendall's W, the consensus and the main row. Its top-5,
    top-10 and top-20 sets follow name order beyond its three variables at the variable level, and beyond its nine
    columns at the feature level (section 8's tie rule). Its per-unit coefficients are not reported: its map files stay
    out of the archive (ruling AV6).
  - Fire's link-space ranks do not describe its nonzero forecasts (reported apart).
  - Own-history features stand for persistence, not a driver. Fire-neighbourhood and burn columns mean contagion or
    co-occurrence. Coral columns may identify the survey programme.
  - Single coefficients of trees or regions are not explanations.
  - Everything is post hoc, on a sample of 1,000 rows per problem and lead.

## 11. Stop rules

- **S-EXACT.** A model that does not reproduce its saved predictions bit for bit on every checked row (or, for an
  arcsine arm under D8, within the licensed relative tolerance) gets no SHAP value. The report names the gate. For
  ridge outside coral the check repeats the board's own scoring, block by block, on the whole test set (a copy of the
  blocks in another memory order is not the board's arithmetic); for BARDL it predicts the whole slim test set in the
  tool's own blocks. Both also check the clipped column (section 4.2).
- **S-ENV.** A rival whose environment is not its board's stops before reading data. `ridge_shap.py` also stops when
  numpy's BLAS does not run the board's 8 threads; its S-ENV stop writes nothing but its log lines.
- **S-SAMPLE.** No script runs on a sample or background file whose SHA-256 is not in the register; the comparison
  refuses models made for another sample or other rows.
- **S-BG.** A registered background key that is not a treeroute router fit row stops treeroute's SHAP; models with
  other background keys are not compared. A rival stops when a registered background key is not a refit row of its
  own inputs (the common rivals: the lead's export; BARDL: its slim copy, found once, of the explained row's unit and
  calendar month, with an issue of that month and the lead). BARDL also stops when its background rows' normals are
  not their unit's prediction-time table (section 4.2).
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
| D16 BARDL in the NDVI main set (new, 2026-11-14; not ruled: owner item 16, `_archive_plan/OWNER_DECISIONS_2026-11-13b.md`) | the frozen plan: BARDL in the NDVI main set when it shares treeroute's link and passes its guard; its nine-column design and the name-order fill of its top-k sets are stated in section 10 | BARDL only as labelled pairs in S3.13, out of W, the consensus and the main row; to be ruled, dated and disclosed as made after the freeze, before the NDVI comparison |

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
- 2026-11-13, no method change; sections 3 and 8 are untouched (recorded here on 2026-11-14): the BARDL loader
  `scripts/bardl_shap.py` and its smoke `scripts/tests/smoke_bardl.py`. Both were built after the freeze (after the
  coral pilot, before any NDVI SHAP value) and reviewed the same day (a design review, code and number checks, fixes
  and a recheck: `_archive_plan/_review_2026-11-13_bardl/`). They are new files; no existing script changed. Final
  SHA-256: `bardl_shap.py` 6bfc9aaf, `smoke_bardl.py` 0f7de758. The smoke's synthetic step passed the same day (40 of
  40 checks); its real-data steps are in the entry of 2026-11-14.
  - Sections 4.2, 7 and 9 name the loader; section 4.2 states its inputs, checks, resume identity and stops.
  - Section 5 states BARDL's players and how its missing-value rule is kept exact.
  - Section 10 states its nine-column design and the name-order fill of its top-k sets; section 11 adds the rivals'
    background stop; section 12 adds owner item 16 as D16, whose default keeps the frozen plan.
  - `RUN_COMMANDS.md` gains its command.
- 2026-11-13 and 2026-11-14, no method change; sections 3 and 8 are untouched (recorded here on 2026-11-14): the ridge
  loader `scripts/ridge_shap.py` and its smoke `scripts/tests/smoke_ridge.py`, built after the freeze, the coral pilot
  and the fire run. They are new files; no existing script changed.
  - Why. The fire run's rivals step stopped ridge at S-EXACT on 2026-11-13 (95,711 of 96,000 test rows bit-equal).
    The cause was the memory order of `rival_shap.py`'s copy of the design, not the model: the board's own scoring
    reproduces every row (section 4.2). Before the loader, no ridge SHAP value existed outside coral.
  - What changed. Sections 4.2, 7, 9 and 11 name the loader, its records and its added checks: the clipped column,
    the BLAS thread count, S-EVAL against the board's values and the refusal while another SHAP step runs.
    `RUN_COMMANDS.md` gains its commands. Ridge's SHAP arithmetic is `rival_shap.py`'s, and no tolerance is added.
  - Reviews (`_archive_plan/_review_2026-11-13_ridge/`). The build (a design and its review, the implementation, a
    code check and a numbers check, the fixes and a recheck) was followed by three small fixes, each reviewed
    independently, and by a wording-only version, all before any real ridge piece: v0 (the build) -> v1 (the process
    gate also skips the parent's id) -> v2 (the parent's id only when psutil's walk fails; smoke hardening) -> v3
    (smoke: a guard flag; the guard before the copies) -> v4 (wording only; its code equals v3's by a syntax-tree
    comparison). Final SHA-256: `ridge_shap.py` 866fd329, `smoke_ridge.py` c48f3f66. v0 to v3 are kept in
    `_snapshots/` (v2 rebuilt exactly from v3; its hashes equal v2's record).
- 2026-11-14, no method change; sections 3 and 8 are untouched: owner question Q1, the real-data checks of both
  loaders, the first ridge pieces, the comparisons run again and the defo registration.
  - Owner question Q1 of the ridge loader's design (`_archive_plan/_review_2026-11-13_ridge/r1_03_design.json`): had
    the owner opened or read the fire comparison written on 2026-11-13 at 21:18 (four models, without ridge:
    `AW3_table.md`, `AW4_table.md` or `AW4_main_row.json`) before ridge was added? The owner answered "Not read"
    (2026-11-14, about 04:35; ruling AZ1).
  - Separately, that comparison was opened once, on 2026-11-13 at about 21:20, before the ridge loader was built, for
    its layout only: the folder listing, `AW4_main_row.json`, `AW4_table.md`, and the models, main set and declined
    list of `per_lead.json`. With treeroute alone in the main set, `compare_shap.py` writes in the two AW4 files only
    W, undefined (NaN), the reference link, the cross-link note and the model lists; every other cell is empty (no
    top-3 variables, no shares). Its other files (`AW3_table.md`, `pairs.parquet`, `importance.parquet`,
    `families.parquet`, the bootstrap files), which hold six pairs (among them the same-link LightGBM-RF pair) and
    each model's importances, were not opened. The ridge loader has no free choice: it repeats the board's own
    scoring bit for bit.
  - Fire's first two runs (2026-11-13, 18:12 and 18:46) stopped treeroute at gate E0 (RAM). Each still wrote a
    comparison of LightGBM, Tweedie and RF (18:19 and 18:46; main set LightGBM and RF, so W and the pair statistics
    were defined there). The work log shows neither was opened: the 18:19 files were replaced at 18:46 unseen, and
    the 18:46 files were only listed (names, sizes and times) at about 20:43; the owner was asked about the 21:18
    comparison only. The third run (19:00, with `--ignore-ram-warning`) replaced them at 21:18.
  - BARDL's checks on real data (smoke label fix), all passed: S-EXACT on 95,184 of 95,184 test rows (pre and raw; 46
    board record checks; provenance 266 of 266 files); the full run on 29 explained rows of the NDVI smoke sample
    (`smoke/sample_ndvi_v3`, f2bb2a79) under its own register (24 of 24 checks; link key `identity|c=-|ub=1`; guard
    passed; `normal` exactly 0; the S-SAMPLE and S-BG refusals exit 3); the comparison step 10 of 10, without ridge.
    Independent checks also passed: every lead-0 test prediction rebuilt bit for bit by independent code (95,184 of
    95,184), the 29 rows' SHAP values checked by brute force, and the guard recomputed from the board's data. Their
    reports and scripts are kept in `_archive_plan/_review_2026-11-13_bardl/real_checks_2026-11-14/`.
  - These steps computed BARDL SHAP values on those 29 rows as plumbing. The NDVI smoke sample is expected to equal
    the NDVI sample still to be registered: `make_sample.py` has not changed since that sample was made (2026-11-12),
    and the four samples registered so far equal their smoke samples of that day (coral 6159277a, fire 1edbc3d1,
    PM2.5 ccb17021, defo 9989bd58). The smoke's comparison paired BARDL only with a declined copy of itself, so no
    agreement between different models was computed. The smoke prints every check's value on screen and keeps it in
    its report; one of them is BARDL's family shares on those 29 rows (the check that own history and local drivers
    make 100% and the seasonal normal 0). That value was not read: the screen output was shown only through a filter
    that left its line out, and the report was read only for its check counts. The smoke's comparison folder
    (`smoke/bardl_fix/out/compare/`, with BARDL's importances and family shares on those rows) is kept.
  - Ridge's checks on real data (smoke label v4), all passed: fire 15 of 15 (S-EXACT on 96,000 of 96,000 test rows;
    the row-by-row copy 95,711, `rival_shap.py`'s own count); the comparison step 5 of 5; coral 15 of 15; S-EXACT
    alone on PM2.5, defo and NDVI 11 of 11 (91,440, 369,096 and 95,184 test rows; every block column-ordered).
    Independent checks of the same: 18 of 18 and 4 of 4. The smoke and the independent checks computed ridge SHAP
    values on the registered fire and coral samples into `smoke/`, as plumbing; the smoke's coral piece equals the
    finished one bit for bit. The smoke's comparison step ran `compare_shap.py` (200 draws) on copies of fire's four
    other pieces with the smoke's ridge piece; only its structured fields were read (models, links, declined list,
    main set, pair labels), and its folder was then removed. The independent check of the fire piece records check
    values only, one of them the largest |phi| of fire's ridge on its sample (the scale of its comparison with an
    independent split); that value was shown on screen, and it is a check value, not one of section 8's statistics.
    The independent checks' reports and scripts are kept in
    `_archive_plan/_review_2026-11-13_ridge/real_checks_2026-11-14/`.
  - No script was changed after these checks (04:42-04:48): `ridge_shap.py` and `smoke_ridge.py` date from 02:46,
    `bardl_shap.py` and `smoke_bardl.py` from 2026-11-13 20:12 and 20:17, and every other script from 2026-11-12,
    before the first registration.
  - Text corrections: the preamble lists the samples registered so far and the smokes that read them; section 1 says
    when the runs began; section 4 says that `rival_shap.py` checks the pre-clip column only (it had said both
    columns for every model; the saved clipped column is the board's legal clip of it, section 4.2).
  - Fire: the ridge piece was made at 04:46:57 (3.6 s; declined by its guard, D6), and the comparison was run again
    at 04:47:14 (five models; main set treeroute alone); it replaces the 21:18 one.
  - PM2.5: the run's own comparison (04:29:34) covered three models (LightGBM, RF, treeroute), because its rivals step
    had stopped ridge at S-EXACT (70,795 of 91,440 rows), as expected. Its statistics were not read; the owner's paste
    of the run's end showed only structural lines. The ridge piece was made at 04:47:35 (9.5 s; guard passed), and a
    comparison of four models (main set LightGBM, RF, ridge and treeroute) replaced the 04:29 comparison at 04:47:52.
  - Defo: the pre-check of 04:36-04:37 registered its sample (9989bd58; 1,000 rows in all 42 regions, D10's default;
    252 units), so D10's alternative (21 regions) would now need a new sample under a new `--tag` (section 3). The
    defo run was started at 05:17; its ridge commands follow it.
  - Coral: nothing to do (its piece from `rival_shap.py` is current). NDVI: its ridge and BARDL commands follow its
    run, the last in the queue.
  - What was read. Of the comparisons in `out/`: the 21:18 fire comparison for its layout only (above); not the
    statistics of the PM2.5 one of 04:29; of those of 04:47, only their logs and `per_lead.json`'s models, main set,
    declined list, links, rows and sample hash. The smokes read structured fields of their own comparisons; the BARDL
    smoke also computed BARDL's family shares as a check value, which was not read (above). The fire comparisons of
    18:19 and 18:46 were not opened (above). No agreement statistic of fire, PM2.5, defo or NDVI was read. The owner
    was asked twice on 2026-11-14 (at about 04:40 and 04:53) not to open the comparisons before the write-up.
  - Every result of this analysis stays post hoc (ruling AK, section 1); nothing in this entry changes that label.
