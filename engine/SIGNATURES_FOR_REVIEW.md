# Proposed science signatures: owner review checklist

Written Mon 28 Sep by the signatures agent and revised the same day after a verification pass (what changed is listed at the end). For same-day approval (plan 8.0: "science modules are drafted as PROPOSED signatures for same-day owner approval, and no science body is written before approval").

- **What:** 170 proposed science functions in 12 modules under `engine/treeroute/_proposed/`, plus shared types in `common.py`. Every body is one line, `raise NotImplementedError("PROPOSED signature -- awaiting owner approval")`. Nothing runs.
- **How to review:** for each row, approve, edit or reject. Edit the docstring in place, or write your answer next to the decision number below. **77 rows need a decision** (101 decision lines, numbered D1-D101 under the table). 2 of those rows are module-wide conventions (marked `(module-wide)`), which apply to every function in their module. Everything else is copied from the plan.
- **Order:** rows are sorted by the day the module is needed (plan 8.0), so the Tuesday rows come first. Tuesday is derive v1 (which now reads labels through the vault's plan-time methods), the quick checks, split and the io transformations. Plan 8.1 (M0) asks for derive/, timing/, FitContext, layer/, the GLS model and the verdict in the first session; the rest can follow at the start of the milestone that builds each module.
- **If a docstring and APP_PLAN.md disagree, the plan wins.** Please flag the row; the docstring is the one that gets fixed.
- **Where the sources are:** each function's `file:line` provenance is a comment directly above it. G-NONAMES refuses dataset names and 4-digit numbers inside engine strings, so docstrings cite rule ids and plan sections only.
- **Not invented:** where the plan leaves a choice, the docstring says OWNER DECISION and proposes the shipped source's behaviour where one exists. Where the plan's wording and the source disagree, no default is proposed (the verdict, D74). The table's contract column is the docstring's first sentence.

**ATTENTION: must-answer before the named bodies can be written** (the plan gives no number or rule, or the plan and the source disagree):

- Tue 29 Sep, `timing` (module-wide) (D19): whole-day closed intervals, with 'at or before' inclusive, as the time resolution of every timing rule. It governs the R8 lags, R9 freezes and R11 cuts.
- Tue 29 Sep, `derive_r03_coverage_end` (D6): count census rows or valid-label rows? On a complete census, counting census rows just returns the table's last year.
- Tue 29 Sep, `compute_lag` (D22, D23, D24, D25): lags counted in the column's own steps; the largest lag across positions in the year; the max of the nowcast and issue references; 9.1 item 3 (a) or (b).
- Tue 29 Sep, `derive_r12_router_kind` (D9): is h taken over all candidate test units before the pick (the pick size depends on the kind)?
- Tue 29 Sep, `derive_r18_unit_count` (D13, D14, D15): the event-floor formula; which donor rows give the event rate; which columns count as router columns for the 'thin' flag (with tree columns included, nearly every per-unit group is thin).
- Tue 29 Sep, `derive_r22_links` (D16): which donor units the plan-time and run-time donor rules read (proposed: the picked units for R19, R22, R23 and R30; every donor unit only for the R18 event rate).
- Wed 30 Sep, `check_oob_share` (D51): the tolerance around the expected held-out share (none in the plan).
- Wed 30 Sep, `name_seed` (D47): which checksum (proposed: first 4 bytes of SHA-256 of 'name|tree|role').
- Sat 3 Oct, `c_for_cut` (D63): one c per lead cut serving that lead's guard surface and test pass (proposed, as the source), or a separate c at each guard cut.
- Sat 3 Oct, `LabelView.asof_rows` (D54): can test rows' history and persistence read test-window labels before the pass's adoption lock? (history is built in step 4, the lock is step 8). The same answer decides which rows G-DERIVED samples for target-derived columns.
- Sun 4 Oct, `single_verdict` (D74): the plan says the band decides HELPS and HURTS; the source used the band only for 'equivalent'. No default is proposed.
- Sun 4 Oct, `equivalence_band` (D75): which contrasts feed the median (the source's set named an inherited penalty and log1p, which the engine no longer has).
- Sun 4 Oct, `guard_tolerance` (D76): the value of k, fixed once off-engine.
- Sun 4 Oct, `mae` (D67): what a non-finite pair does: refuse (proposed; the caller picks the rows and prints the count) or drop and return the count. The same policy covers anomaly R2, corr2, calibration and hit rate.
- Sat 10 Oct, `check_g_derived` (D92, D93), `check_g_hist_sample` (D79; needed Mon 5 Oct), `check_g_range` (D95): sample sizes, match tolerances, which rows are sampled, and whether an out-of-range input is refused or flagged.

## Rows per day

- Tue 29 Sep: 69 rows (package contract + derive v1 (with the vault's plan-time reads); quick checks; split; io transformations (M1))
- Wed 30 Sep: 19 rows (pool reader, bank primitives with name seeds, FitContext, the vault's as-of view)
- Fri 2 Oct: 8 rows (per-unit router + unpenalised normal column + grid)
- Sat 3 Oct: 18 rows (layer: links, arms, placebo, trees-off, guard, clip, MAE selection, GLS tool; vault lock)
- Sun 4 Oct: 20 rows (scoring and report metrics; every row saved)
- Mon 5 Oct: 1 row (first package (features))
- Tue 6 Oct: 4 rows (region router + normal column; short-history fallback)
- Thu 8 Oct: 1 row (history block for all)
- Fri 9 Oct: 10 rows (generic forecast ladder (with the per-lead adoption lock))
- Sat 10 Oct: 10 rows (freeze: check --deep green)
- M4: 4 rows (Type-3 slot (8.1 M4; not on the 8.0 day list))
- M8: 8 rows (event rules and neighbour track (fast track: after the headline))

## Checklist

| # | Needed | Module | Function | One-line contract | Rule | Owner decision |
|---|---|---|---|---|---|---|
| 1 | Tue 29 Sep (derive v1) | derive_rules | `borderline_flags` | Margin of a derived value to each of its thresholds, and a 'borderline' flag within 20%. | Section 2 (all rules) | yes (D1) |
| 2 | Tue 29 Sep (derive v1) | derive_rules | `derive_r01_cadence` | The target's cadence and step: one regular step (grid), a composite-of-year grid, or events. | R1 | yes (D2, D3) |
| 3 | Tue 29 Sep (derive v1) | derive_rules | `derive_r02_season_key` | The season key (a step's position within its year) and the number of steps per year. | R2 | yes (D4, D5) |
| 4 | Tue 29 Sep (derive v1) | derive_rules | `derive_r03_coverage_end` | Y_end: the last year in which at least half the test groups have at least 90% of their usual yearly rows. | R3 | yes (D6, D7) |
| 5 | Tue 29 Sep (derive v1) | derive_rules | `derive_r04_first_year` | Y0: the first data year plus the largest computed lag, rounded up to whole years. | R4 | yes (D8) |
| 6 | Tue 29 Sep (derive v1) | derive_rules | `derive_r05_test_window` | The test window: the last 4 years up to Y_end, with the short-record ladder. | R5 | no |
| 7 | Tue 29 Sep (derive v1) | derive_rules | `derive_r06_train_end` | Donor train end: the year before the test window. | R6 | no |
| 8 | Tue 29 Sep (derive v1) | derive_rules | `derive_r07_inner_windows` | Inner windows: score = the years before the test window; fit = Y0 to the year before score. | R7 | no |
| 9 | Tue 29 Sep (derive v1) | derive_rules | `derive_r08_feature_lags` | One computed lag for every kept, time-varying non-key column. | R8 | no |
| 10 | Tue 29 Sep (derive v1) | derive_rules | `derive_r09_freeze_epochs` | The frozen epoch of every 'freeze' column at both cuts of every lead. | R9 | no |
| 11 | Tue 29 Sep (derive v1) | derive_rules | `derive_r10_leads` | Leads: 1, 3, 6 and 12 months in the data's own step, rounded half up, merged when equal. | R10 | no |
| 12 | Tue 29 Sep (derive v1) | derive_rules | `derive_r11_cuts` | Both cuts for every lead, lead 0 included, written to derived.json. | R11 | no |
| 13 | Tue 29 Sep (derive v1) | derive_rules | `count_valid_rows_per_unit` | Number of VALID target rows per unit inside [first_step, last_step]. | R12, R18 | no |
| 14 | Tue 29 Sep (derive v1) | derive_rules | `constant_history_share` | Share of units whose whole fit history is one value (report only). | R12 | no |
| 15 | Tue 29 Sep (derive v1) | derive_rules | `derive_r12_router_kind` | Router kind by one rule: per-unit if h >= 24, region if 2 <= h < 24, neighbour if h < 2. | R12 | yes (D9, D10) |
| 16 | Tue 29 Sep (derive v1); folds used only in M8 (neighbour track) | derive_rules | `derive_r13_decision_surface` | Decision surface: the inner window (per-unit, region) or K donor folds (neighbour). | R13 | no |
| 17 | Tue 29 Sep (derive v1); used Fri 2 Oct (per-unit) and Tue 6 Oct (region) | derive_rules | `derive_r14_router_design` | The router's column layout, unpenalised columns, penalty grid and fit-row cap. | R14 | yes (D11) |
| 18 | Tue 29 Sep (derive v1); block built Thu 8 Oct | derive_rules | `derive_r17_history_spec` | Which own-history columns the engine builds, and where the block starts. | R17 | yes (D12) |
| 19 | Tue 29 Sep (derive v1) | derive_rules | `derive_r18_unit_count` | Units per group, from the data only (never the disk). | R18 | yes (D13, D14, D15) |
| 20 | Tue 29 Sep (derive v1); bank built Wed 30 Sep | derive_rules | `derive_r19_bank_plan` | The bank recipe as data: trees per donor, bag size per donor group, tree and corrector constants, and the seed formula id. | R19 | no |
| 21 | Tue 29 Sep (derive v1); store built Thu 1 Oct | derive_rules | `derive_r20_batching` | Matrix batching: tree-answer tables per test group, in row blocks, keyed by row. | R20 | no |
| 22 | Tue 29 Sep (derive v1) | derive_rules | `derive_r21_smoke_plan` | The fixed smoke plan: 40 units per group, 12 trees per donor, the first 2 donor and 2 test groups in sorted order. | R21 | no |
| 23 | Tue 29 Sep (derive v1) | derive_rules | `derive_r22_links` | The link set: identity always; log(y+c) and arcsine only when the facts and donor rows allow. | R22, G-DONOR | yes (D16) |
| 24 | Tue 29 Sep (derive v1; quick-check listing) | derive_rules | `derive_r30_missing_flags` | Missing-value flags: a column over 25% missing in donor training rows, or vanishing in a test year, needs an explicit verdict in the Q34 review. | R30 | yes (D17, D18) |
| 25 | Tue 29 Sep (derive v1) | derive_rules | `derive_all` | Run every plan-time rule in dependency order and return the derived.json content. | R1-R22, R30 (orchestration) | no |
| 26 | Tue 29 Sep (derive v1) | timing | `(module-wide)` | Calendar convention for every timing rule: whole-day closed intervals, 'at or before' inclusive. | R8, R9, R11 | yes (D19) |
| 27 | Tue 29 Sep (derive v1) | timing | `content_interval` | First and last day of content that a value stored for one period actually describes. | R8 (input) | yes (D20) |
| 28 | Tue 29 Sep (derive v1) | timing | `forward_reach_days` | How many days a column's content reaches past the end of its own stored period. | R8, G-LAG, A5 | yes (D21) |
| 29 | Tue 29 Sep (derive v1) | timing | `reference_day` | The instant a feature row must not look past: end of the target's own window (nowcast) or end of the issue step (lead L). | R8 | no |
| 30 | Tue 29 Sep (derive v1) | timing | `compute_lag` | The one fixed lag of a column: the smallest whole number of the column's steps that puts its newest content at or before the reference instant. | R8 | yes (D22, D23, D24, D25) |
| 31 | Tue 29 Sep (derive v1) | timing | `fit_cut_step` | Grid fit cut for lead L: the donor train end moved back by L-1 steps, never later than it. | R11 | no |
| 32 | Tue 29 Sep (derive v1) | timing | `guard_cut_step` | Grid cut of the inner guard at lead L: the same rule as fit_cut_step, from the inner-fit end. | R11 | no |
| 33 | Tue 29 Sep (derive v1) | timing | `latest_label_step` | The newest label a row predicting step t may read at lead L (history, persistence). | R11, R17 | no |
| 34 | Tue 29 Sep (derive v1) | timing | `label_usable` | True if a label may enter a fitted object at this cut. | R11, G-FITCUT | yes (D26) |
| 35 | Tue 29 Sep (derive v1) | timing | `cuts_for_leads` | Both cuts (fit and inner guard) for lead 0 and every derived lead. | R11 | no |
| 36 | Tue 29 Sep (derive v1) | timing | `freeze_epoch` | The epoch a 'freeze' column is held at: its last content epoch at or before the fit cut. | R9 | yes (D27) |
| 37 | Tue 29 Sep (M1) | io_science | `step_index` | Integer step index (int64) for every row, from its calendar parts. Never a timestamp. | R1 | yes (D28, D29) |
| 38 | Tue 29 Sep (M1) | io_science | `step_bounds` | First and last calendar day (Day ordinals) covered by each integer step. | R1, R8 | no |
| 39 | Tue 29 Sep (M1) | io_science | `mask_sentinels` | Mask declared fill values and abs >= 1e30 to NaN at read, before anything is derived; flag abs >= 2^30. | G-SENTINEL (read) | yes (D30) |
| 40 | Tue 29 Sep (M1) | io_science | `join_one_to_one` | Join 1:1 on keys with a row-count assert. | G-JOIN (runtime) | yes (D31) |
| 41 | Tue 29 Sep (M1) | io_science | `join_coarser_column` | Join a column stored at a finer table but declared at a coarser cadence (an annual column inside monthly rows), after asserting it is constant within each unit x coarse period, with its R8 lag applied to the collapsed table before the join. | G-CADENCE (annual joins), R8, G-CALENDAR | no |
| 42 | Tue 29 Sep (M1) | io_science | `apply_lags` | Move each column that lives at the target's own step back by its computed lag, through predecessor_index. | R8, G-CALENDAR | no |
| 43 | Tue 29 Sep (M1) | io_science | `apply_verdicts` | Decide where every non-key column goes: tree features, router context, report only, or out. | plan 1.4, G-CLOSED, G-KEYS | no |
| 44 | Tue 29 Sep (M1) | io_science | `apply_freezes` | Hold each 'freeze' column at its computed epoch. | R9 | yes (D32, D33) |
| 45 | Tue 29 Sep (M1) | io_science | `check_column_set` | The observed column set of a table must equal its catalog's column set. | G-JOIN, G-CLOSED | no |
| 46 | Tue 29 Sep (M1) | io_science | `check_missing_files` | Expected (group, period) pairs from the target against the files found in a store. | G-MISSING (files) | no |
| 47 | Tue 29 Sep (derive v1 builds the vault on it) | io_science | `build_dense_grid` | Build the KEYS-ONLY dense unit x step grid over every row of the target census. | R30, G-SUPPORT (census), G-LOCK | no |
| 48 | Tue 29 Sep (M1) | io_science | `aggregate_time` | Aggregate a finer column to the target's step (monthly to annual, or to a growing season). | plan 1.5 aggregate_time | yes (D34, D35) |
| 49 | Tue 29 Sep (M1; reserved, no current package uses it) | io_science | `aggregate_space` | Aggregate source units to package units through the unit_map (grid cells to polygons). | plan 1.5 aggregate_space | yes (D36) |
| 50 | Tue 29 Sep (M1) | split | `as_sorted_set` | Turn a declared list into a set sorted by name. | plan 1.2, 1.7, G-SPLIT | yes (D37) |
| 51 | Tue 29 Sep (M1) | split | `split_differences` | Every difference between the split's sets and the data's groups. | G-SPLIT | yes (D38, D39) |
| 52 | Tue 29 Sep (M1) | split | `candidate_units` | Candidate units of one group: at least one valid target row at or before the train end. | R18 | no |
| 53 | Tue 29 Sep (M1) | split | `stride_pick` | Deterministic stride over sorted unit ids. No seed, no draw. | R18, G-NODRAW | yes (D40) |
| 54 | Tue 29 Sep (M1) | split | `pick_units` | Pick units for every donor and test group with the same count, capped at what is available. | R18 | no |
| 55 | Tue 29 Sep (quick checks) | validators | `check_g_closed` | G-CLOSED: every non-key column has facts and a verdict (closed world). | G-CLOSED, A5 | yes (D41) |
| 56 | Tue 29 Sep (quick checks) | validators | `check_g_lag` | G-LAG: every lag is COMPUTED from facts (R8); nothing types a lag; an unknown window is refused. | G-LAG, R8 | no |
| 57 | Tue 29 Sep (quick checks) | validators | `check_g_epoch` | G-EPOCH: a column whose content is observed after the cut is refused unless 'freeze'; a target calibrated past the donor train end is refused unless recalibrated or disclosed. | G-EPOCH, R9 | yes (D42) |
| 58 | Tue 29 Sep (quick checks) | validators | `check_g_lineage` | G-LINEAGE (quick): provenance facts checked against the target. | G-LINEAGE | no |
| 59 | Tue 29 Sep (quick checks) | validators | `list_co_measured_candidates` | Every column that must carry an explicit co_measured_with_target answer. | G-LINEAGE, G-FACTS, R8 | yes (D43) |
| 60 | Tue 29 Sep (quick checks) | validators | `check_g_hist_declared` | G-HIST (quick): refuse dataset columns DECLARED as a lag, trailing or cumulative sum or mean of the unit's own target. | G-HIST, R17 | no |
| 61 | Tue 29 Sep (quick checks) | validators | `check_g_keys` | G-KEYS: keys are never tree features; a key-derived column may only be router context. | G-KEYS | no |
| 62 | Tue 29 Sep (quick checks) | validators | `check_g_split` | G-SPLIT (quick): split lists are sets, sorted by the engine; the data's groups equal the split's. | G-SPLIT | no |
| 63 | Tue 29 Sep (quick checks) | validators | `check_g_support` | G-SUPPORT: enough support to learn and to judge. | G-SUPPORT, C15 | yes (D44, D45) |
| 64 | Tue 29 Sep (quick checks); BLOCKS at the freeze (Sat 10 Oct) | validators | `check_g_facts` | G-FACTS: unsigned timing facts cannot enter the headline. | G-FACTS | no |
| 65 | Tue 29 Sep (quick checks) | validators | `check_g_missing` | G-MISSING (quick): every column R30 flags carries keep-with-evidence or ban. | G-MISSING, R30 | no |
| 66 | Tue 29 Sep (derive v1) | vault | `LabelView.__init__` | Take the target table's labels into the vault, aligned to the dense grid (or kept per visit for events). | A6, G-LOCK | no |
| 67 | Tue 29 Sep (derive v1) | vault | `LabelView.validity` | Label validity (valid or NaN) of every row inside [first_time, last_time]; never a value. | R3, R12, R18, G-LOCK | no |
| 68 | Tue 29 Sep (derive v1) | vault | `LabelView.donor_labels` | Label-only donor rows at or before a cut, for plan-time rules. | R11, G-DONOR; R18, R19, R22, R30 | no |
| 69 | Tue 29 Sep (M1; with the first functions) | common | `(module-wide)` | The shared shapes (enums, frozen dataclasses, protocols) every module passes. | all rules (shared shapes) | yes (D46) |
| 70 | Wed 30 Sep (pool reader) | io_science | `predecessor_index` | Position of each row's predecessor exactly k steps back in the same unit, or -1. | G-CALENDAR | no |
| 71 | Wed 30 Sep (bank) | split | `assert_bank_disjoint` | Refuse a bank that saw a test group, its own held-out fold, or a label after its cut. | G-DISJOINT | no |
| 72 | Wed 30 Sep (FitContext reads it); vault complete Sat 3 Oct | vault | `LabelView.asof` | Every label dated at or before the cut whose own window has ended by then. | R11, G-FITCUT | no |
| 73 | Wed 30 Sep (bank) | fit_context | `FitContext.__init__` | Bind one cut from derived.json; never compute a cut here. | R11, R13 | no |
| 74 | Wed 30 Sep (bank) | fit_context | `FitContext.cut_pair` | Both cuts of this context's lead, from derived.json. | R11 | no |
| 75 | Wed 30 Sep (bank) | fit_context | `FitContext.donor_rows` | Donor-group rows with valid labels at or before this context's cut. | R11, G-DONOR, G-FITCUT | no |
| 76 | Wed 30 Sep (bank); used Fri 2 Oct (normals) | fit_context | `FitContext.unit_history` | One unit's own labelled rows at or before this context's cut. | R15, R17, G-DONOR | no |
| 77 | Wed 30 Sep (bank) | fit_context | `FitContext.log` | Every row hand-out this context made, for fitctx_log.parquet. | G-FITCUT | no |
| 78 | Wed 30 Sep (bank primitives with name seeds) | bank_recipe | `name_seed` | The fixed seed of one tree role, from the donor's NAME and the tree number. | R19 | yes (D47) |
| 79 | Wed 30 Sep (bank) | bank_recipe | `bag_size` | Bag size of every tree of a donor group: max(30, half the group's rows). | R19 | no |
| 80 | Wed 30 Sep (bank) | bank_recipe | `draw_bag` | Draw one bag: bag_size(n) row positions from 0..n-1, with replacement. | R19, G-NODRAW | yes (D48) |
| 81 | Wed 30 Sep (bank primitives) | bank_recipe | `fit_one_tree` | PRIMITIVE: fit one bank tree on the given rows with the given random_state value. | R19, G-NOKNOB (primitive signature) | yes (D49) |
| 82 | Wed 30 Sep (bank) | bank_recipe | `fit_one_corrector` | PRIMITIVE: fit one corrector tree (depth 6, leaf 10) on given rows and residuals. | R19 | no |
| 83 | Wed 30 Sep (bank) | bank_recipe | `oob_rows` | The tree's out-of-bag rows: its own donor group's rows that are not in its bag. | R19 | no |
| 84 | Wed 30 Sep (bank) | bank_recipe | `expected_oob_share` | Expected out-of-bag share of a bag of size b drawn with replacement from n rows. | R19 | yes (D50) |
| 85 | Wed 30 Sep (bank) | bank_recipe | `check_oob_share` | Refuse a bank whose observed held-out share per donor group is far from the expected share. | R19 | yes (D51) |
| 86 | Wed 30 Sep (bank) | bank_recipe | `fit_corrector` | Fit a tree's corrector on its out-of-bag residuals. | R19, R24 | yes (D52) |
| 87 | Wed 30 Sep (bank) | bank_recipe | `fit_placebo_corrector` | Fit the placebo corrector: the same construction on a scrambled residual. | R19, R24 | no |
| 88 | Wed 30 Sep (bank) | bank_recipe | `fit_donor_bank` | Fit the whole bank from DonorRows: per donor group, in sorted order, trees, correctors and placebo correctors with name seeds. | R19, G-DISJOINT, G-FITCUT | no |
| 89 | Fri 2 Oct (per-unit router) | fit_context | `FitContext.router_rows` | The router's fit rows (and the only rows a scaler may see) for the listed units. | R11, R14, R20, G-FITCUT | no |
| 90 | Fri 2 Oct (per-unit router + normal column) | route_kinds | `unit_season_normal` | R15: the unit's normal per season key: the mean of link(y) over its own fit rows at or before the cut, however few. | R15, G-DONOR | no |
| 91 | Fri 2 Oct (per-unit router + normal column) | route_kinds | `donor_link_mean` | The donor-row mean of link(y) at a cut: the last fallback of the normal. | R15, G-DONOR | no |
| 92 | Fri 2 Oct (per-unit router) | route_kinds | `build_column_block` | Build one router design matrix in the layout R14 names for the kind. | R14, G-PLUMB (layout) | no |
| 93 | Fri 2 Oct (per-unit router) | route_kinds | `router_standardisation` | Mean and standard deviation of each context column over the router's fit rows at the cut. | R20, G-DONOR (scalers) | yes (D53) |
| 94 | Fri 2 Oct (per-unit router + normal column) | route_kinds | `trees_off_with_normal` | R16 trees-off for kinds with a normal: intercept + normal only, unweighted, context dropped. | R16, G-PLUMB | no |
| 95 | Fri 2 Oct (per-unit router + normal column) | route_kinds | `reference_predictions` | R16 references: the guard reference per link and the one decline target, in y units. | R16, R27, R34 | no |
| 96 | Fri 2 Oct (per-unit router + grid + parallel units) | route_kinds | `route_per_unit` | Per-unit router: one block-penalised ridge per test unit on its own history at or before the cut, solved at every grid point, plus trees-off. | R12, R14, R15, R16, R23, G-FITCUT | no |
| 97 | Sat 3 Oct (vault); used Mon 5 Oct (G-HIST) and Thu 8 Oct (history) | vault | `LabelView.asof_rows` | Per-row as-of reads: for each row, the same unit's label exactly k_back steps before its newest readable step, or NaN. | R17, R31, G-LOCK, G-CALENDAR | yes (D54) |
| 98 | Sat 3 Oct (nowcast pass); per lead Fri 9 Oct | vault | `LabelView.open_test_labels` | Release the test-window labels for ONE scoring pass, only against the hash of the adoption that pass uses. | R27, R29, G-LOCK | no |
| 99 | Sat 3 Oct (vault + adoption lock) | vault | `lock_adoption` | Write the nowcast's adoption.json once and return its SHA-256; after this the nowcast adoption cannot change. | R27, G-LOCK | no |
| 100 | Sat 3 Oct (layer: GLS tool) | weights_gls | `cross_region_error` | The weight model's target: \|y - mean answer of the trees from the OTHER donor groups\|, per donor row. | R25 | yes (D55, D56) |
| 101 | Sat 3 Oct (layer: GLS tool) | weights_gls | `fit_weight_model` | Fit the sigma model: a random forest from the kept tree features to the cross-region error. | R25, G-DONOR, G-NODRAW | yes (D57) |
| 102 | Sat 3 Oct (layer: GLS tool) | weights_gls | `sigma_floor` | The floor on predicted sigma: 1% of the donor spread. | R25, R36 | yes (D58) |
| 103 | Sat 3 Oct (layer: GLS tool) | weights_gls | `sigma_clip_bounds` | The clip bounds of sigma: its 5th and 95th percentiles on the donor rows the model was fitted on. | R25, G-DONOR | yes (D59) |
| 104 | Sat 3 Oct (layer: GLS tool) | weights_gls | `row_weights` | Router row weights from predicted sigma: floor, clip, 1/sigma^2, max/min ratio capped at 100. | R25 | yes (D60) |
| 105 | Sat 3 Oct (layer: GLS tool) | weights_gls | `weight_model_for_cut` | Build one cut's weight model end to end: donor rows, the donor-row pass, the error target, the forest, the floor and the clip bounds. | R25, G-FITCUT, G-DONOR | no |
| 106 | Sat 3 Oct (layer) | layer | `link_forward` | Transform y into a link's space. | R22 | yes (D61) |
| 107 | Sat 3 Oct (layer) | layer | `link_inverse` | Back-transform link-space predictions to y units (clipping happens in clip_to_legal). | R22, R28 | no |
| 108 | Sat 3 Oct (layer) | layer | `c_for_cut` | R23: c = the 1st percentile of positive donor-row y at or before the cut. | R23, G-DONOR | yes (D62, D63) |
| 109 | Sat 3 Oct (layer) | layer | `candidate_arms` | R24: the nowcast candidate list. | R24 | no |
| 110 | Sat 3 Oct (layer) | layer | `penalty_search` | R26: score every grid point of one arm on the decision surface by MAE and keep the best. | R26 | no |
| 111 | Sat 3 Oct (layer) | layer | `n2_eligible` | N2 guard: an arm is eligible only if it beats its own-link trees-off on the decision surface. | R27 (N2) | yes (D64) |
| 112 | Sat 3 Oct (layer) | layer | `select_adoption` | R27: rank eligible tree arms by decision-surface MAE; decline to the arithmetic normal when none is eligible. | R27, G-LOCK | yes (D65) |
| 113 | Sat 3 Oct (layer) | layer | `clip_to_legal` | R28: clip to the target's legal range and report the pre-clip rate and the NaN count. | R28, G-CLIP | no |
| 114 | Sat 3 Oct (layer); lead-0 identity Fri 9 Oct | layer | `check_plumbing` | G-PLUMB: the plumbing identities asserted at runtime. | G-PLUMB, R36 | no |
| 115 | Sun 4 Oct (scoring; every row saved) | split | `check_scored_units` | The units present in saved predictions must equal the derived unit lists, per group. | G-SPLIT (outputs) | no |
| 116 | Sun 4 Oct (scoring) | metrics | `baseline_predict_zero` | predict-zero, clipped to the legal range. | R31, R28 | no |
| 117 | Sun 4 Oct (scoring) | metrics | `baseline_guess_normal` | guess-normal: the per-unit arithmetic normal (the R16 decline target), clipped. | R31, R16, R28 | no |
| 118 | Sun 4 Oct (scoring) | metrics | `baseline_last5_normal` | The last-5-years normal, printed beside guess-normal (Q26). | R31 | yes (D66) |
| 119 | Sun 4 Oct (scoring) | metrics | `mae` | Mean absolute error in y units. | R34 | yes (D67) |
| 120 | Sun 4 Oct (scoring) | metrics | `anomaly_r2` | Anomaly R2 against the per-unit normal: 1 - SSE(p) / SSE(normal). | R34 | yes (D68, D69) |
| 121 | Sun 4 Oct (scoring) | metrics | `corr2` | Squared Pearson correlation between labels and predictions. | R34, R27 (printed beside) | no |
| 122 | Sun 4 Oct (scoring) | metrics | `calibration_ratio` | Calibration ratio: mean prediction / mean truth. | R28, R34, G-RANGE | yes (D70) |
| 123 | Sun 4 Oct (scoring) | metrics | `preclip_rate` | Share of predictions outside the legal range before the clip. | R28, R34 | no |
| 124 | Sun 4 Oct (scoring) | metrics | `hit_tolerance` | R32: half the donor rows' MEAN absolute deviation from their own normal (neighbour: from the donor-row median). | R32, G-DONOR | yes (D71) |
| 125 | Sun 4 Oct (scoring) | metrics | `hit_rate` | Share of rows within +/- tol of the truth (inclusive). | R32, R34 | no |
| 126 | Sun 4 Oct (scoring) | metrics | `top10_detection` | R33: the one strict top-10% detection score. | R33, U-3 | yes (D72) |
| 127 | Sun 4 Oct (scoring) | metrics | `stratum_edges` | Quartile edges of a declared report_stratum column, from donor rows. | R34, G-DONOR | yes (D73) |
| 128 | Sun 4 Oct (scoring) | metrics | `score_table` | Scoring table over saved rows, one line per arm x (by-key), with pooled and macro lines. | R34 | no |
| 129 | Sun 4 Oct (scoring) | metrics | `group_jackknife` | Leave-one-group-out jackknife at 1.96 over per-group values. | R34, Q19 a | no |
| 130 | Sun 4 Oct (scoring) | metrics | `single_verdict` | R34: the ONE verdict -- the adopted arm against its own link-matched trees-off (or the donor-row median without a normal), judged with the package's nowcast band. | R34, R35, G-DECIDE | yes (D74) |
| 131 | Sun 4 Oct (scoring) | metrics | `equivalence_band` | R35: the band = the median jackknife SE of the arm contrasts in the package's first headline run. | R35 | yes (D75) |
| 132 | Sun 4 Oct (scoring; used by G-PLUMB from Fri 2 Oct) | metrics | `guard_tolerance` | R36: the relative guard tolerance of one link, k x s, with s = the donor-row standard deviation of link(y). | R36, U-4, G-DONOR | yes (D76) |
| 133 | Sun 4 Oct (scoring) | metrics | `sign_flip_groups` | Groups whose contrast sign differs from the pooled sign (flagged, report only). | R34, G-DECIDE | yes (D77) |
| 134 | Sun 4 Oct (scoring) | metrics | `trend_flag` | Report-only trend flag: the median per-unit slope of y over time in donor rows. | R34 | yes (D78) |
| 135 | Mon 5 Oct (first package's features) | validators | `check_g_hist_sample` | G-HIST (runtime): refuse any dataset column that MATCHES a lag or trailing mean of the unit's own target on a sample, whatever its declaration says. | G-HIST, G-LOCK | yes (D79) |
| 136 | Tue 6 Oct (region router) | route_kinds | `region_cap_units` | The region router's fit cap: the largest set of evenly spaced WHOLE units whose pooled fit rows stay within the budget. | R14, C7 | yes (D80) |
| 137 | Tue 6 Oct (region router + normal column) | route_kinds | `route_region` | Region router: one pooled ridge per test group on its capped whole units, with the per-unit normal as an unpenalised column, solved at every level, plus trees-off. | R12, R14, R15, R16, U-1 | yes (D81) |
| 138 | Tue 6 Oct (region router serves short-history units) | route_kinds | `fallback_units` | Units of a per-unit dataset with fewer than 24 valid fit rows, and their share. | R12, C10 | no |
| 139 | Tue 6 Oct (region router serves short-history units) | route_kinds | `search_fallback_level` | The fallback region router's level: searched once, pooled across groups, or the centre when fewer than 10 fallback units have inner score rows. | R12, C15 | yes (D82) |
| 140 | Thu 8 Oct (history block for all; signature at M2 start) | io_science | `history_block` | The engine's own-history block for each target row, ending at the issue step. | R17, G-HIST, G-CALENDAR, G-LOCK | yes (D83, D84, D85) |
| 141 | Fri 9 Oct (forecast ladder) | io_science | `features_at_issue_step` | At lead L, give each target row the feature row of its issue step t - L (same unit). | R8, R11 | no |
| 142 | Fri 9 Oct (forecast ladder) | vault | `lock_lead_adoption` | Write one forecast lead's adoption file once and return its SHA-256, before any of that lead's test rows is scored. | R29, R27 (N2), G-LOCK | no |
| 143 | Fri 9 Oct (forecast ladder) | fit_context | `FitContext.check_inner_score_rows` | Assert every inner score row is issued at or after the inner guard's cut. | G-FITCUT | no |
| 144 | Fri 9 Oct (forecast ladder) | fit_context | `FitContext.for_lead` | A new context at another lead and cut kind, same split, grid, features, picks and vault. | R11, R29 | no |
| 145 | Fri 9 Oct (forecast ladder) | layer | `lead_arms` | The arms built at one forecast lead: the pinned arm and its link's trees-off; its placebo only at the longest lead. | R24, R29 | no |
| 146 | Fri 9 Oct (forecast ladder) | layer | `forecast_adoption` | R29: the adoption at one lead, pinned to the nowcast's link, tool, weighting and penalty, with the N2 guard run on the inner guard's cut. | R29, R27 (N2), G-LOCK | yes (D86) |
| 147 | Fri 9 Oct (forecast ladder) | metrics | `baseline_persistence` | Persistence: the unit's label at the issue step (events: the last valid label before the issue date), clipped. | R31, R28 | yes (D87) |
| 148 | Fri 9 Oct (forecast ladder) | metrics | `damped_persistence_phi` | Damped-persistence phi per unit, from (label, predecessor) pairs at or before the cut. | R31, U-2 | yes (D88) |
| 149 | Fri 9 Oct (forecast ladder) | metrics | `baseline_damped_persistence` | Damped persistence: normal(t) + phi x (y_issue - normal(issue)), clipped. | R31, R28 | no |
| 150 | Fri 9 Oct (forecast ladder) | metrics | `common_rows` | Row keys present at every lead of the ladder. | R34 | no |
| 151 | Sat 10 Oct (check --deep green) | io_science | `recompute_declared_operation` | Recompute one engineered column on given rows from its declaration (the reference G-DERIVED compares the feature script against). | plan 1.5, G-DERIVED, G-LOCK | yes (D89, D90) |
| 152 | Sat 10 Oct (check --deep green) | validators | `check_g_missing_deep` | G-MISSING (deep): missing shares per column x group x year, with store-declared absences separated. Report only. | G-MISSING, R30 | no |
| 153 | Sat 10 Oct (check --deep green) | validators | `check_g_cadence` | G-CADENCE: declared versus observed step on every unit; fake-fine columns refused. | G-CADENCE | yes (D91) |
| 154 | Sat 10 Oct (check --deep green) | validators | `check_g_derived` | G-DERIVED (recompute): every engineered column recomputed on a stride sample from its declaration. | G-DERIVED, plan 1.5, G-LOCK | yes (D92, D93) |
| 155 | Sat 10 Oct (check --deep green) | validators | `scan_feature_script` | G-DERIVED (static): refuse a feature script that fits a model. | G-DERIVED, plan 1.5 | no |
| 156 | Sat 10 Oct (check --deep green; the lookup asserts from Wed 30 Sep) | validators | `check_g_calendar` | G-CALENDAR: every look-back read is in the same unit and exactly where it should be. | G-CALENDAR | no |
| 157 | Sat 10 Oct (check --deep green) | validators | `check_g_sentinel_deep` | G-SENTINEL (deep): known fill codes present but undeclared; near-sentinel magnitudes. | G-SENTINEL | yes (D94) |
| 158 | Sat 10 Oct (check --deep green) | validators | `check_g_range` | G-RANGE: units and legal ranges on inputs and outputs; one unit per physical quantity. | G-RANGE | yes (D95, D96) |
| 159 | Sat 10 Oct (check --deep green; runtime asserts from Tue 29 Sep) | validators | `check_g_join` | G-JOIN (deep): every join was 1:1 with an unchanged row count; every table's column set equals its catalog. | G-JOIN | no |
| 160 | Sat 10 Oct (check --deep green) | validators | `flag_lineage_reconstructions` | G-LINEAGE (deep): flag kept columns that reconstruct a banned one. | G-LINEAGE | yes (D97) |
| 161 | M4 (Type-3 donor-fold service); M8 (neighbour track) | split | `make_donor_folds` | Donor folds, round-robin over the sorted donor names. | R13, plan 1.6 | no |
| 162 | M4 (Type-3 folds); M8 (neighbour decision surface) | fit_context | `FitContext.for_fold` | A context for donor fold i: donor rows from the OTHER donor groups only. | R13, plan 1.6, G-DISJOINT | no |
| 163 | M4 (Type-3 slot; not on the 8.0 day list) | fit_context | `FitContext.fit_bank` | Type-3 service: fit the engine bank recipe on donor rows at this cut, optionally on a declared transform of y. | plan 1.6, R19, G-FITCUT | no |
| 164 | M4 (Type-3 slot; not on the 8.0 day list) | fit_context | `FitContext.donor_fold_predict` | Type-3 service: tree predictions for donor rows from banks that did not see those rows' donor groups (donor folds). | plan 1.6, R13 folds | yes (D98) |
| 165 | M8 (event rules; fast track) | timing | `event_fit_cut_day` | Event fit cut for a lead in days: the first day of the test window minus L days. | R11 (events) | no |
| 166 | M8 (event rules; fast track) | timing | `event_guard_cut_day` | Event cut of the inner guard: the same rule from the first day of the inner score window. | R11 (events) | yes (D99) |
| 167 | M8 (event rules; fast track) | io_science | `event_history_block` | Own-history block for events with repeat visits, read from the as-of label view. | R17 (events) | no |
| 168 | M8 (event rules; fast track) | io_science | `asof_driver_join` | For each event row, the newest driver value whose content ends at or before the row's issue date. | R8 (events), G-JOIN | no |
| 169 | M8 (neighbour track) | route_kinds | `trees_off_neighbour` | R16 trees-off for the neighbour kind: intercept + context, fitted on the row's pool. | R16 | no |
| 170 | M8 (neighbour track) | route_kinds | `neighbour_pool` | The strict pool of one neighbour-kind row, or None when fewer than 12 rows qualify. | R14 (neighbour), C11 | yes (D100, D101) |
| 171 | M8 (neighbour track) | route_kinds | `route_neighbour` | Neighbour router: per row, a ridge on its strict pool (intercept, context, trees) at every grid point, plus trees-off; the donor-row median when the pool is too small. | R12, R14, R16, R23 | no |
| 172 | M8 (neighbour track) | metrics | `baseline_donor_median` | The donor-row median of y: the neighbour kind's reference and pool fallback. | R31, R34, G-DONOR | no |

## Owner decisions (D1-D101), in table order

- **D1** `derive_rules.borderline_flags` (Tue 29 Sep): "within 20%" is proposed as |value - threshold| <= 0.2 x |threshold|, i.e. relative to the threshold; a zero threshold then uses the absolute margin only.
- **D2** `derive_rules.derive_r01_cadence` (Tue 29 Sep): units that are each regular but with DIFFERENT steps fit neither outcome; propose a refusal (plan names only 'all share one step' -> grid and 'irregular' -> events).
- **D3** `derive_rules.derive_r01_cadence` (Tue 29 Sep): the calendar-part list has no 'composite number'; propose the composite number comes from day_of_year and the composite length from the observed within-year spacing.
- **D4** `derive_rules.derive_r02_season_key` (Tue 29 Sep): "365.25 / N rounded" -- propose round half up, as R10 rounds.
- **D5** `derive_rules.derive_r02_season_key` (Tue 29 Sep): the season key of a regular N-day step WITHOUT a year reset is not defined by the plan (steps drift across years); a definition is needed before such data can run.
- **D6** `derive_rules.derive_r03_coverage_end` (Tue 29 Sep): on a complete census every unit x step is a row (NaN labels included), so counting census rows gives the table's last year; propose counting rows with a VALID (non-NaN) label, which reads NaN-ness only -- confirm this is within "never their values".
- **D7** `derive_rules.derive_r03_coverage_end` (Tue 29 Sep): "their own median yearly count" -- propose the median over every calendar year from the group's first to its last row, zero-row years included.
- **D8** `derive_rules.derive_r04_first_year` (Tue 29 Sep): "first data year" is proposed as the first year of the target table (the shipped reading, where that year is read only as the lag source).
- **D9** `derive_rules.derive_r12_router_kind` (Tue 29 Sep): which test units enter h -- propose ALL candidate test units (R18 candidates) before the stride pick, because the pick size itself depends on the router kind.
- **D10** `derive_rules.derive_r12_router_kind` (Tue 29 Sep): median of an even count -- propose the midpoint (numpy median), so h may be a half-integer.
- **D11** `derive_rules.derive_r14_router_design` (Tue 29 Sep): the plan gives the level RANGE only; propose the source values (0.1, 0.3, 1, 3, 10, 30, 100), not log-even values, on every grid including the region's.
- **D12** `derive_rules.derive_r17_history_spec` (Tue 29 Sep): "one more step back" versus "computed from the window fact" -- propose the offset = the number of whole steps the target window reaches past its step, rounded up (1 for a composite that spills into the next month).
- **D13** `derive_rules.derive_r18_unit_count` (Tue 29 Sep): the event floor's formula -- propose count >= ceil(10 / (test_window_rows_per_unit x the donor event rate)), i.e. expected events = units x test rows per unit x rate.
- **D14** `derive_rules.derive_r18_unit_count` (Tue 29 Sep): which donor rows give the event rate -- propose every labelled donor-group row at or before the train end (the nowcast fit cut), before any pick (the pick size depends on it): donor_all is LabelView.donor_labels with unit_ids None.
- **D15** `derive_rules.derive_r18_unit_count` (Tue 29 Sep): which columns count as "router columns" for the thin flag -- all columns including the tree block (then nearly every per-unit group is thin), or the non-tree columns only.
- **D16** `derive_rules.derive_r22_links` (Tue 29 Sep): which donor units the donor-row rules read. Propose: R22 links, R23 c, the R19 bag sizes and the R30 shares read the PICKED donor units' rows (the rows the bank and the router actually see; derive_all computes the picks right after R18); only the R18 event rate reads EVERY donor-group unit, because the pick size depends on it. The alternative reads every donor-group unit everywhere at plan time, which can disagree with the c that FitContext computes on the picked units.
- **D17** `derive_rules.derive_r30_missing_flags` (Tue 29 Sep): sign the 25% threshold (9.1 item 2f).
- **D18** `derive_rules.derive_r30_missing_flags` (Tue 29 Sep): "vanishes (pooled over groups)" -- propose 100% missing over ALL groups' rows of that test year (donor and test groups together).
- **D19** `timing.(module-wide)` (Tue 29 Sep): approve whole-day closed intervals as the time resolution of every timing rule, with 'at or before' inclusive (the alternative is a finer resolution or an exclusive bound; either changes which content counts as known at a reference instant).
- **D20** `timing.content_interval` (Tue 29 Sep): for align=UNKNOWN with a signed max_length w, take the worst case, a FORWARD window of length w starting at the stamp (plan says only "R8 then lags by the bound").
- **D21** `timing.forward_reach_days` (Tue 29 Sep): forward reach is measured on every period the column has in the data and the MAXIMUM is reported (centred windows and uneven month lengths vary by period).
- **D22** `timing.compute_lag` (Tue 29 Sep): lags are counted in the COLUMN's own steps (an annual column on a monthly target is 1 year back, which is how "year -1" reads), not in target steps.
- **D23** `timing.compute_lag` (Tue 29 Sep): when the needed lag differs across the target's positions in the year (a quarterly column on a monthly target), take the LARGEST, so the lag stays one fixed number.
- **D24** `timing.compute_lag` (Tue 29 Sep): "one fixed lag per column" versus two references: propose the lag is the larger of the NOWCAST and ISSUE_STEP results, so the same number is safe at every lead.
- **D25** `timing.compute_lag` (Tue 29 Sep): 9.1 item 3 -- default (a) keeps same-year annual values at lag 0 on an annual target; alternative (b) lags every year-stamped annual product one year.
- **D26** `timing.label_usable` (Tue 29 Sep): the plan writes the window-ended clause under Events; propose it applies to grid cuts too, which drops the cut step's own label when the target window reaches past its step (overlapping composites).
- **D27** `timing.freeze_epoch` (Tue 29 Sep): the plan names only "the fit cut of that lead"; propose the inner guard and the inner decision surface use the epoch at or before THEIR OWN cut (so no value observed after the guard cut enters the guard's fit). derive_r09 keys its epochs by (column, lead, cut kind), so derived.json holds both.
- **D28** `io_science.step_index` (Tue 29 Sep): index origin -- propose the source form (monthly: year x months-per-year + month, without subtracting 1) so the harness compares integers directly.
- **D29** `io_science.step_index` (Tue 29 Sep): origin of a regular N-day step without a year reset -- propose the first observed day of the whole target table.
- **D30** `io_science.mask_sentinels` (Tue 29 Sep): the target column -- propose it is never masked but REFUSED if it holds a declared fill or abs >= 1e30 (the ingest must write invalid labels as NaN; the source never masked targets).
- **D31** `io_science.join_one_to_one` (Tue 29 Sep): unmatched left rows -- propose they are allowed as NaN and counted (they then fall under R30), as the source's left join does; the alternative refuses any unmatched row.
- **D32** `io_science.apply_freezes` (Tue 29 Sep): propose ALL rows take the epoch value (the source rule is "ONE pre-window epoch"); the alternative keeps each earlier row's own value and freezes only later rows.
- **D33** `io_science.apply_freezes` (Tue 29 Sep): a unit missing a value at the epoch -- propose NaN, counted (R30).
- **D34** `io_science.aggregate_time` (Tue 29 Sep): missing values inside a period -- propose NaN if any sub-period is missing (strict), versus aggregating over the available sub-periods.
- **D35** `io_science.aggregate_time` (Tue 29 Sep): legal range of a SUM -- not inherited by the plan; propose computed as [n x min, n x max] for n sub-periods, or require a declaration.
- **D36** `io_science.aggregate_space` (Tue 29 Sep): how weights enter -- propose a weighted mean for MEAN and weighted sum for SUM; MIN and MAX ignore weights.
- **D37** `split.as_sorted_set` (Tue 29 Sep): sort order -- propose plain code-point order of the UTF-8 strings (what Python and numpy sort give), recorded in the manifest.
- **D38** `split.split_differences` (Tue 29 Sep): "the split's groups" -- propose donor + test + excluded, so an excluded group present in the data is not a difference.
- **D39** `split.split_differences` (Tue 29 Sep): seen_during_design -- propose it must be a subset of the test groups.
- **D40** `split.stride_pick` (Tue 29 Sep): the source sorted factorised integer codes in one script (order of first appearance in the pool) and id strings in another; the engine sorts id STRINGS. The M1 gate checks that this reproduces the shipped picks, or flags the difference.
- **D41** `validators.check_g_closed` (Tue 29 Sep): does keep_unreviewed need an evidence Part? Propose NO, as package/schema.py already does: the verdict is unreviewed by definition, so plan 1.4's "each verdict carries a reason and evidence" reads as every REVIEWED verdict (keep, freeze, ban, conditional, watch). The alternative refuses keep_unreviewed without a Part, and schema.py changes.
- **D42** `validators.check_g_epoch` (Tue 29 Sep): "observed after the cut" -- propose: observed_through (or a snapshot's content epoch) later than the cut, checked against EVERY cut the column is used at (each lead's fit cut and guard cut).
- **D43** `validators.list_co_measured_candidates` (Tue 29 Sep): "sensor lineage" has no dedicated fact; propose: same product_family, or the target's product family appears in lineage_assimilates or lineage_trained_on, at a cadence no coarser than the target's.
- **D44** `validators.check_g_support` (Tue 29 Sep): sign the thresholds (3 / 2 refuse; 14 / 5 flag); the alternative flags under 10 test groups instead of 14.
- **D45** `validators.check_g_support` (Tue 29 Sep): the plan states the presence-only refusal but not its test; the census check covers grids, and an event rule is needed (for example: no zero observation at all while the legal minimum is 0). Both label counts (zero observations, all-zero units) are proposed on labels at or before the donor train end (LabelView.asof), so the check reads no test-window label.
- **D46** `common.(module-wide)` (Tue 29 Sep): approve these shapes together with the functions that use them. They are the contract between the science modules. The package schema must be able to fill every field.
- **D47** `bank_recipe.name_seed` (Wed 30 Sep): which checksum -- propose the first 4 bytes (big-endian) of SHA-256 of the UTF-8 string "<donor_name>|<tree_number>|<role value>".
- **D48** `bank_recipe.draw_bag` (Wed 30 Sep): generator -- propose numpy RandomState(seed).choice(n, size, replace=True), as the source, so the harness can reproduce legacy bags from seed values alone.
- **D49** `bank_recipe.fit_one_tree` (Wed 30 Sep): legacy variants that need OTHER tree settings (the optional track's max_features 0.15) build their trees inside the harness, since this primitive takes none.
- **D50** `bank_recipe.expected_oob_share` (Wed 30 Sep): the exact form (1 - 1/n)^b versus the source comment's exp(-b/n); and the TOLERANCE for comparing observed with expected (the plan gives none) -- see check_oob_share.
- **D51** `bank_recipe.check_oob_share` (Wed 30 Sep): the tolerance (not stated in the plan) -- a number is needed before this can run.
- **D52** `bank_recipe.fit_corrector` (Wed 30 Sep): the source skips a corrector with fewer than 50 out-of-bag rows; the plan does not mention it -- keep 50 (propose) or drop the minimum.
- **D53** `route_kinds.router_standardisation` (Fri 2 Oct): the source adds 1e-9 to sd; propose keeping it (a constant context column then standardises to 0 instead of failing).
- **D54** `vault.LabelView.asof_rows` (Sat 3 Oct): test rows' history and persistence need test-window labels BEFORE each row's issue step, and the plan builds history (4.1 step 4) before the adoption hash (step 8). Option (a): asof_rows serves them before the hash, because each is known at its row's issue time and decide() never sees test rows. Option (b): test rows' history and persistence are built only after that pass's lock.
- **D55** `weights_gls.cross_region_error` (Sat 3 Oct): sign this error target (9.1 item 2b).
- **D56** `weights_gls.cross_region_error` (Sat 3 Oct): which answers -- propose the PLAIN tree answers (not tree + corrector); the plan says "the mean of the trees".
- **D57** `weights_gls.fit_weight_model` (Sat 3 Oct): "the inner-fit end of its cut" at a forecast lead -- propose that lead's guard cut (the plan defines it only for the nowcast).
- **D58** `weights_gls.sigma_floor` (Sat 3 Oct): R36 has one s per link; propose the IDENTITY-link s, because sigma is on the y scale.
- **D59** `weights_gls.sigma_clip_bounds` (Sat 3 Oct): percentile method -- propose numpy's default (linear), as the source.
- **D60** `weights_gls.row_weights` (Sat 3 Oct): order and cap mechanics -- propose floor, then clip, then weights, then cap the ratio by raising the smallest weights to (largest / 100).
- **D61** `layer.link_forward` (Sat 3 Oct): the arcsine formula is not written in the plan; propose forward = arcsin(sqrt(y / UB)), matching the source's inverse.
- **D62** `layer.c_for_cut` (Sat 3 Oct): percentile method -- propose numpy's default linear interpolation, as the source.
- **D63** `layer.c_for_cut` (Sat 3 Oct): which cuts get their own c. Option (a), proposed: one c per LEAD cut, from donor rows at that lead's FIT cut (plus one per fold on the donor-fold surface), serving that lead's decision or guard surface AND its test pass -- the source's one-c-per-run rule, and the same pairing R25 uses for the weight model. Option (b): a separate c at each guard cut, so the guard surface and the test pass of one lead use different transforms.
- **D64** `layer.n2_eligible` (Sat 3 Oct): "beats" = strictly lower MAE (the source), versus lower by more than the R36 tolerance.
- **D65** `layer.select_adoption` (Sat 3 Oct): a tie in MAE between two eligible arms -- propose the first in candidate_arms order (the source's min() behaviour).
- **D66** `metrics.baseline_last5_normal` (Sun 4 Oct): "last 5 years" -- propose the 5 calendar years ending with the cut's year; a unit-season with no row there takes the R15 fallback chain.
- **D67** `metrics.mae` (Sun 4 Oct): non-finite pairs. Option (a), proposed: mae refuses any non-finite pair (fail loudly); the caller (score_table) selects the rows each column is scored on and prints that count -- a baseline that is NaN on some rows (persistence without an issue label) is scored on the rows where it exists, beside the arms on the same rows. Option (b): mae drops non-finite pairs itself and returns (value, rows used). The same policy applies to anomaly_r2, corr2, calibration_ratio and hit_rate. The source propagated NaN.
- **D68** `metrics.anomaly_r2` (Sun 4 Oct): which normal -- propose the ARITHMETIC (identity-link) normal for every arm.
- **D69** `metrics.anomaly_r2` (Sun 4 Oct): the source returns nothing under 10 rows; propose NaN under 10 finite rows.
- **D70** `metrics.calibration_ratio` (Sun 4 Oct): the plan names the ratio but not its formula; propose mean(p) / mean(y) from the earlier plans, and confirm whether the 0.5-2.0 flag band (Q51: flag only) is kept.
- **D71** `metrics.hit_tolerance` (Sun 4 Oct): sign the MEAN form (9.1 item 2c).
- **D72** `metrics.top10_detection` (Sun 4 Oct): quantile method -- propose numpy's default linear interpolation, as the source.
- **D73** `metrics.stratum_edges` (Sun 4 Oct): bin edges inclusive on the right or left -- propose right-closed bins.
- **D74** `metrics.single_verdict` (Sun 4 Oct): how the band decides HELPS and HURTS -- no default is proposed. Option (a), the shipped verdict rule: HELPS when the interval's low end is above 0, HURTS when its high end is below 0 (the band enters only through EQUIVALENT). Option (b), the plan's wording read literally: HELPS when the low end is above +band, HURTS when the high end is below -band.
- **D75** `metrics.equivalence_band` (Sun 4 Oct): which contrasts feed the median -- the source used penalty sweep, tool worth, each arm vs its placebo and log-vs-log1p; the engine has no inherited penalty or log1p, so the set must be named (propose: each tree arm vs its own trees-off, and each arm vs its placebo).
- **D76** `metrics.guard_tolerance` (Sun 4 Oct): the value of k (computed once off-engine from the first shipped package's donor s, stored in engine_constants.py with its origin comment) and the standard-deviation convention (propose ddof = 0).
- **D77** `metrics.sign_flip_groups` (Sun 4 Oct): a contrast of exactly 0 -- propose it is not a flip.
- **D78** `metrics.trend_flag` (Sun 4 Oct): the slope -- propose an ordinary least-squares slope of y on time (in years) per donor unit.
- **D79** `validators.check_g_hist_sample` (Mon 5 Oct): which look-backs are tested (propose lags 0 to 3 and the R17 trailing windows), the match tolerance, and the sample rows (propose stride rows at or before the donor train end, so no test-window label is read before any adoption lock).
- **D80** `route_kinds.region_cap_units` (Tue 6 Oct): m = 1 makes the formula divide by zero; propose position 0 (the first unit).
- **D81** `route_kinds.route_region` (Tue 6 Oct): the shipped ridge had no normal column; propose the unpenalised normal enters by projecting intercept and normal out first (as the per-unit dual path does) with the trace normalisation taken over the tree block only.
- **D82** `route_kinds.search_fallback_level` (Tue 6 Oct): sign the 10-unit threshold (9.1 item 2f).
- **D83** `io_science.history_block` (Thu 8 Oct): trailing means use AVAILABLE steps only with no minimum count (the source rule); confirm, or set a minimum.
- **D84** `io_science.history_block` (Thu 8 Oct): "mean of all history so far" -- propose it starts at the first step of the dense grid (the first data year), not at Y0.
- **D85** `io_science.history_block` (Thu 8 Oct): test rows need test-window labels before their issue step; the plan builds the block (4.1 step 4) before the adoption hash (step 8) -- see vault.LabelView.asof_rows.
- **D86** `layer.forecast_adoption` (Fri 9 Oct): a pinned arm that FAILS the guard at a lead -- propose that lead adopts the decline target (as R27 does at the nowcast); the plan does not restate it in R29.
- **D87** `metrics.baseline_persistence` (Fri 9 Oct): the source also computes anomaly persistence (normal(t) + y_issue - normal(issue), and its log form); the plan names only persistence and damped persistence -- keep them as extra printed baselines, or drop.
- **D88** `metrics.damped_persistence_phi` (Fri 9 Oct): minimum counts. Shared season key: more than 2 labels in the shared mean, else NaN and the pair is dropped (the source). Separate season keys: propose at least 2 labels in each unit-season, else NaN and the pair is dropped. The source's max(C - 1, 1) gives a leave-one-out mean of 0 for a single-label unit-season, so its 'anomaly' is the raw label; porting that as-is would carry the quirk over silently.
- **D89** `io_science.recompute_declared_operation` (Sat 10 Oct): "years since" with no earlier event -- NaN (propose) or a declared cap.
- **D90** `io_science.recompute_declared_operation` (Sat 10 Oct): grid neighbour aggregate -- which neighbours (propose the 8 surrounding cells by grid_ix, grid_iy) when no adjacency table is given.
- **D91** `validators.check_g_cadence` (Sat 10 Oct): "next-coarser period" per cadence -- propose month -> year, N-day composite -> month, year -> none (annual columns cannot be fake-fine).
- **D92** `validators.check_g_derived` (Sat 10 Oct): the stride sample size and the match tolerance (the plan names neither).
- **D93** `validators.check_g_derived` (Sat 10 Oct): which rows a TARGET-derived column is sampled on. check --deep runs before any adoption exists, so a test-window row's recompute reads test-window labels before any lock. Follow the vault decision (LabelView.asof_rows): under (a) the sample spans every row; under (b) target-derived columns are sampled only on rows at or before the donor train end. Driver-derived columns are sampled on every row either way.
- **D94** `validators.check_g_sentinel_deep` (Sat 10 Oct): the list of "known codes" the deep scan looks for must be an engine constant (propose the common integer and float fill values, each with its origin comment).
- **D95** `validators.check_g_range` (Sat 10 Oct): refuse or flag an out-of-range input, and at what share (the plan gives no tolerance).
- **D96** `validators.check_g_range` (Sat 10 Oct): how a "physical quantity" is identified from UDUNITS strings (propose: UDUNITS dimension equality).
- **D97** `validators.flag_lineage_reconstructions` (Sat 10 Oct): the reconstruction test is not specified; propose checking declared sum groups only (a banned member recoverable as the group total minus the kept members).
- **D98** `fit_context.FitContext.donor_fold_predict` (M4): the plan does not state this service's return (mean tree answer, or routed prediction); the Type-3 plug-in's author must declare it.
- **D99** `timing.event_guard_cut_day` (M8): at lead 0 the plan does not state the event guard cut; propose the last day of the inner-fit end year, by analogy with the fit cut's lead-0 clause.
- **D100** `route_kinds.neighbour_pool` (M8): distance -- propose great-circle (haversine), as the source.
- **D101** `route_kinds.neighbour_pool` (M8): feature standardisation constants -- propose donor rows at or before the cut.

## Also approve: the shared shapes

These dataclasses, enums and protocols hold no logic. They are the contract between the modules, and the package schema (boilerplate) must be able to fill every field. Protocols marked boilerplate-owned are implemented by boilerplate modules; they are listed so the science signatures can name them.

- `derive_rules.py`: MissingShares, MissingShareReader (boilerplate-owned)
- `io_science.py`: SentinelReport, JoinReport, ColumnSets, MissingFileReport
- `split.py`: SplitDiff
- `vault.py`: LabelSlice, DonorLabels, TestLabels
- `fit_context.py`: DonorRows, UnitHistory, RouterRows
- `weights_gls.py`: WeightModel
- `route_kinds.py`: NormalTable, DesignMatrix, RouteOutput
- `metrics.py`: DetectionScore, JackknifeResult, VerdictResult
- `common.py`: Refusal (boilerplate-owned), CadenceKind, StepUnit, CalendarPart, Scope, Stamp, Align, FactStatus, Role, Verdict, BanReason, OperationKind, AggStat, RouterKind, SurfaceKind, FoldPurpose, SeasonKeyKind, ReferenceKind, LeadUnit, CutKind, Link, Tool, Weighting, SeedRole, GuardStatus, VerdictTag, RunKind, Cadence, Window, OperationDecl, DataSelected, ColumnFacts, TargetFacts, VerdictDecl, SplitSets, ExceptionEntry, TargetTable, DenseGrid, FeatureSource (boilerplate-owned), Derived, SeasonKeySpec, TestWindowPlan, Windows, Lag, LeadPlan, CutPair, GridPoint, RouterDesign, HistorySpec, ArmSpec, GuardResult, BankManifest, FitCtxLogRow, FittedTree (boilerplate-owned), TreeAnswerStore (boilerplate-owned), PackageView (boilerplate-owned), Bank, PenaltyPick, Adoption, LeadAdoption

## Not in this batch (and why)

- **Boilerplate guards** (not science in plan 4.2): G-NOKNOB, G-NONAMES, G-IMPORT, G-THREADS, G-NOOVERWRITE, G-FINGERPRINT, G-DISK, G-LEGACY, G-NODRAW (static scan).
- **Runtime guards enforced inside the science modules above:** G-DISJOINT (`split.assert_bank_disjoint`), G-FITCUT and G-DONOR (`FitContext`, `vault.DonorLabels`), G-LOCK (`vault`: `LabelView`, `lock_adoption`, `lock_lead_adoption`), G-CLIP and G-PLUMB (`layer`), G-DECIDE (`metrics.single_verdict`).
- **Moved as-is, gated by the harness rather than by a new signature:** `route/solve.py` (solve_local, the dual and shared-Gram solves, the trace-normalised ridge).
- **Boilerplate gated by byte identity:** the row-keyed tree-answer store and its parallel writer (Thu 1 Oct), the out-of-core feature pool reader behind `FeatureSource` (Wed 30 Sep), and the parallel router-unit loop.
- **Engine constants** (C1-C15, `engine_constants.py`): the owner reviews them once, separately. The docstrings name them by id.
- **The planted-fault list** (M4) and the Type-3 plug-ins (dataset science, reviewed per package).

## What changed in the fix pass (Mon 28 Sep)

A verification pass of the first version found 1 high, 5 medium and 10 low problems. All are fixed in the files and in this table:

- **The label lock is now structural (high).** `DenseGrid` holds keys only. The target table's labels go only into `vault.LabelView`, and every own-target read (history block, target-derived recompute, G-HIST and G-DERIVED samples) takes the `LabelView`. `FitContext` now gets an explicit label-free `FeatureSource` (the origin of `DonorRows.X`) and the R18 unit picks.
- **A lock for each forecast lead.** New `vault.lock_lead_adoption` hashes each lead's adoption before that lead's test rows are scored. `open_test_labels` now opens one scoring pass at a time, against that pass's hash.
- **Plan-time donor labels.** New `vault.DonorLabels` (label-only, same cut rule, no features, no run folder) feeds R18's event rate, R19's bag sizes, R22's links, R30's row set, G-SUPPORT and G-RANGE. `LabelView` takes an optional run folder. `derive_all` now takes the target table and a reader for the R30 shares. A new decision names which donor units each rule reads.
- **G-MISSING deep is report-only.** The file-level stop stays in `check_missing_files`. An all-NaN column inside files that exist feeds the R30 flags, as plan 3.2 and 3.3 flag 7 require.
- **New decisions:** which cuts get their own c (`c_for_cut`); the timing module's calendar convention is now numbered and tabled; keep_unreviewed evidence (`check_g_closed`); which rows G-DERIVED samples for target-derived columns; mae's NaN policy; the phi minimum count for a single-label unit-season.
- **Smaller fixes:** Type-3 fold contexts work on any surface (`FoldPurpose`); coarse-column lags are applied before the 1:1 join (`join_coarser_column` takes the lag); `clip_to_legal` passes baseline NaN through, counted; `VerdictDecl` carries a free-text reason plus a ban label (aligned with package/schema.py); freeze epochs are keyed by cut kind; `weight_model_for_cut` takes the guard context; the normals take the router kind, and the routers take c, ub and the normals explicitly; `score_table` stamps the run kind (the headline-table builder refuses smoke rows); the verdict's contract no longer states a default against the plan; `Bank`, `Adoption`, `LeadAdoption` and `PenaltyPick` moved to `common.py`, so every signature's types resolve without TYPE_CHECKING imports.

