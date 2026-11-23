# BUILD NOTES: table mode (builder key `table`)

Written 2026-10-19. Scope: the table option of SPEC_TABLE_MODE.md (owner ruling U). Paths are under
`D:\treeroute\coral_build\engine\` unless they start with a drive letter. Nothing outside `D:\treeroute\coral_build`
was written. LIVE was only read (the two LIVE comparisons in the tests import it with no bytecode written).

## Files

New (engine, all under treeroute/, none names a problem):

| File | What it holds |
|---|---|
| treeroute/package/table.py | TABLE_KEY_ROLES, TableSpec / table_spec (roles, verdicts, target facts 1.5, T-NAMES), table_leads (R10), lead_files (T-FILES), read_tables (T-COLUMNS ... T-FINITE, T-LEADSET; the row grid), table_groups, table_ram_bytes, U2_VOUCHED, is_table_package (the guarded read) |
| treeroute/labels/rows.py | RowLabelView(LabelView): days for steps, decision_surface on rows, asof_rows refused, for_lead, last_label_before, test_window_reads; build_row_vault |
| treeroute/derive/table.py | derive_all_table (3.5), check_marks (T-MARK), fold_c_entry (R23 per fold) |
| treeroute/pipeline/table_run.py | TablePipeline(Pipeline), TABLE_LIMITS, TABLE_DEPARTURES, VaultRows |
| treeroute/pipeline/table_passes.py | TableRunState(RunState): pool, fits (+ fold c / median / GLS), S1, decision, test pass, hit tolerance, strata, report |
| treeroute/pipeline/table_router.py | NeighbourPass (3.8): candidates + G1, scalers, Z, parts, pools, dense answers, kernels, pools file, G-PLUMB |
| treeroute/pipeline/table_ladder.py | TableLadder (3.9): lead-0 contract, per lead fit/guard objects, guard, persistence, lock, test pass, ladder table |
| treeroute/check/table.py | run_table_quick / run_table_deep |

Changed shared files (each gated or additive; section 5 of the spec):

| File | Change | Why grids do not move |
|---|---|---|
| package/schema.py | `DatasetFile.input` (default grid) + `_input_kind` validator; `StorePaths.static` Optional; 6 roles added to ROLES/Role; TABLE_ONLY_ROLES; LEAD_PLACEHOLDER | a valid grid dataset.yaml validates to the same fields; no grid column has a new role |
| package/load.py | `check_input_roles` (cross-file rule), called after the YAML files validate | passes untouched when no table role is declared |
| pipeline/run.py | `run_pipeline` / `plan_pipeline` try `_is_table` first (guarded, any error = grid) | grid -> the same `Pipeline(...)` call |
| derive/router_rules.py | R17: `is_events` and neighbour -> the empty spec before the M8 raise | inside `if is_events:`; grids pass False |
| route/solve.py | keyword `n_unpenalised=UNPENALISED_COLUMNS` on all ten solvers, forwarded everywhere; `o = n_unpenalised` | default is the same int 2; no operation reordered (tested against LIVE's bytes) |
| fit/context.py | ADD `FitContext.donor_rows_outside` | additive |
| fit/weights.py | ADD `weight_models_for_folds` (+ `__all__`) | additive; `weight_model_for_cut` not edited |
| check/quick.py, check/deep.py | first line: guarded dispatch to check/table.py | grid packages take the old path |
| check/report.py | `package_smoke_groups`: table branch on `dataset.input == "table"` | grid branch unchanged |
| route/__init__.py | docstring only (the neighbour builder's request) | text |
| treeroute_report/table.py | `_read_strata` skips the edge check for a stratum whose record has values and no edges; `_verdict_of` uses `REFERENCE_DONOR_ROW_MEDIAN` when verdict.json says `reference_rule: donor_row_median`; `_stratum_md_rows` prints "per value" when there are no edge columns | grid verdicts always record edges and never `reference_rule` |

New tests and fixtures: tests/table_toy.py (the toy builder + run helpers), tests/test_table_mode_contract.py,
tests/test_table_mode_vault_derive.py, tests/test_table_mode_solve.py, tests/test_table_mode_fold_gls.py,
tests/test_table_mode_pipeline.py.

## How the table pipeline calls the neighbour kind

Through route/neighbour.py as built by the neighbour builder (BUILD_NOTES_neighbour.md), not the kinds.py stubs:
`pool_feature_z`, `NeighbourRows`, `neighbour_pools` (once per part, shared by every arm), `pool_records`,
`dense_answers`, `_route_neighbour_grid` / `_route_neighbour_at` (with `pools=`), `_trees_off_neighbour_pass` (a
decline link's trees-off when no arm of that link is routed). `design` = `derived["R14"].value`; `tol` = the pass's
R36 tolerance of the arm's link. Request to the neighbour builder: keep these names and keywords stable.

## Deviations from SPEC_TABLE_MODE.md (smallest the code forced; reason each)

1. **T-MARK's record is the derived entry `R5:marks`**, not `T-MARK`: derived.json names every entry by its rule id
   (derive/derived.py refuses another name).
2. **`weight_models_for_folds` has no `matrix_dir`** (spec 5.12 lists one): the fold models' donor matrix is held in
   RAM, with the RAM wait (Q1). A table's guard-cut rows are few (coral about 9k rows).
3. **The per-pass "largest pool day minus issue day"** is in each pass's `neighbour` record (decision_checks.json,
   test_pass_router.json, lead.json router records), not a separate fitctx_log row (spec 2.3). The kernel computes it.
4. **Persistence reads at a lead go through the nowcast row vault** (every label, D54 a). `lock_lead_adoption` prints
   no read totals (only `lock_adoption` does), so lead.json records `persistence_reads_before_lock` (the vault's
   `test_window_reads()` right before the lead's lock).
5. **Damped persistence pairs** come from the lead's fit-cut DonorRows (train rows present at that lead, at or
   before its fit cut). A label of a row absent from the lead's file is in no pair (departure table_absent_rows).
6. **T-NAMES also refuses the prefix `placebo__`** (the spec lists arm__, pre__, base__): score_table reads any
   `placebo__` column as a placebo.
7. **A grid dataset.yaml without `static`** is still refused (PackageError, exit 5), but the text is now the
   validator's "stores.static: Field required (a grid package names its static table)" instead of pydantic's
   own "Field required" line at stores.static.
8. **R18's scored lists name every group** (an empty tuple for a group with no test row). `check_scored_units`
   then refuses such a group at the report (G-SPLIT). See owner item O28.
9. **A decision-surface fold whose group has no surface row is skipped** (no part); its trees still serve the others.
10. **R30's test-year shares** are over every row of the lead-0 file dated in a test year, tree features only (as
    grids measure tree features only).
11. **check/table.py's G-FACTS flags** (does not refuse) an unverified target fact (O21's default reading).

## Owner items found or sharpened by this build

- **O28 (new): a group with no test row.** Under LORO every group is tested; a table group with no test-marked row
  cannot be scored, and the report's G-SPLIT check refuses the run. Alternatives: exclude such groups in split.yaml
  (package side), or let a group with no scored row leave the scored lists (engine side, a reading of R18 for tables).
- **O29 (new): with the signed pool-drop default, small pools drop every tree.** A row whose pool spans every group
  drops every tree and takes its trees-off (O8). On the tiny coral smoke (4 groups, 897 rows) 46 of the 81
  decision-surface rows and 4 of 96 test rows had no tree left. On the first toy (no group signal in Z) EVERY row had
  no tree, so every tree arm equalled its trees-off and R35 refused the band ("no finite contrast SE"). The toy now
  gives two features a group offset. A full coral run has more rows per group, so this should shrink; measure it.
- **O30 (new): G-PLUMB's tolerance is tight.** C9.guard_tolerance_k is set (5.2e-8), so the neighbour G-PLUMB pairs
  (trees-off vs an un-jittered closed form; the base column vs a one-point solve) must agree within
  max(k x s, 9e-7). They did on the toy and the tiny coral smoke. A larger pool or design may move the gap; watch it.
- O13, O14, O15, O17, O18 are built at the listed defaults and tested (empty group at a cut, one-site group, H4 at
  lead 365, guard row absent refuses, damped persistence normal, string strata).

## Tests run (from `D:\treeroute\coral_build\engine`, `py -3.9 -m pytest -q ...`)

| Tests | Result |
|---|---|
| tests/test_table_mode_contract.py (input field, roles, 23 refusal variants, keys never reach apply_verdicts, every datasets/ package loads identically under LIVE and the build) | 31 passed |
| tests/test_table_mode_vault_derive.py | 5 passed |
| tests/test_table_mode_solve.py (keyword omitted = LIVE's bytes for all ten solvers; n_unpenalised=1 = brute force) | 8 passed |
| tests/test_table_mode_fold_gls.py | 3 passed |
| tests/test_table_mode_pipeline.py (smoke e2e, lock order, scored rows, verdict reference, plan/run records, pool audit, leak probe, resume, dispatch, no grid helper reached, check quick/deep, guard-row refusal, plan, report table, nonames on the report additions) | 13 passed (about 1.5 min) |
| tests/test_pipeline.py (grid pipeline, synthetic package) | 31 passed (7 min) |
| tests/test_route_solve.py, test_route_weighted.py, test_derive_loro_rules.py, test_fit_context.py, test_schema.py, test_load.py, test_nonames.py, test_vault.py, test_packages_declarative.py, test_noknob.py | passed |
| tests/test_check_cli.py, test_report_table.py, test_fit_weights.py, test_fit_weights_blocks.py, test_derive_all.py, test_route_neighbour_fit.py, test_route_neighbour_pool.py, test_vault_lock.py | 1052 passed |
| tests/test_check_deep.py, test_report_freeze.py, test_s1_score_context.py | 100 passed |
| tests/test_route_kinds.py | 1 failure, pre-existing and not mine: test_the_r36_tolerance_refuses_until_k_is_set (C9 is set by ruling N; BUILD_NOTES_neighbour.md says it fails in LIVE too) |
| A tiny coral smoke through the table pipeline (coral_data/tiny/package, read in place; run root in my scratchpad) | finished in 14.5 s: adopted log_c_plain_unweighted, verdict does_not_help_equivalent (smoke: no sign information), ladder 183/365 declined, 0 rows absent at the leads |

The full suite was not run (the Fix phase runs it once). The grid tripwire (5.10) is not run (Fix phase).

## Open items

- The Fix phase: the grid tripwire (spec 5.10) and the full suite.
- `treeroute_report/continuity_groups.yaml` needs the coral package's entry before `treeroute report` builds its
  table (report tooling may name packages; I did not add one for a draft package).
- treeroute_report/*.py already fails the G-NONAMES scan today (freeze.py and table.py: a year and a package name in
  their module docstrings); the test scans only the table additions there.
- TABLE_DEPARTURES are not-headline reasons until the owner accepts them (O26).
