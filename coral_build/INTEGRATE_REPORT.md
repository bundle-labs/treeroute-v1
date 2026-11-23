# INTEGRATE REPORT: table option + neighbour router + coral tables

Written 2026-10-19 by the integrate agent. Everything here is under `D:\treeroute\coral_build`.
LIVE was only read. Engine paths are under `D:\treeroute\coral_build\engine\`.

## Summary

- The three builds were already joined. I wired nothing new and removed no test double (step 1).
- I changed one file: `treeroute/fit/weights.py` got back its CRLF line ends. Its diff against LIVE now shows only additions, plus the one `__all__` line. The old LF copy is at `_moved/integrate/weights.py.lf`.
- Relevant tests: every failure is also in LIVE, or comes from test order. None comes from the build (step 2).
- The toy end-to-end test passed. The tiny coral smoke ran end to end in 22.6 s, with a peak of 0.21 GB (step 3).
- Pool fallback count: **0** in every pass. Every pool held 50 rows. Every pool day was at least 20 days before its issue day.
- New engine hash `engine_code_sha256` = **53025a4987e26a68c491cd0da90be45fbbdc51642668e723741b8ebdeed7d947**. LIVE is 65a177bc... (step 4).
- 21 engine files differ from LIVE: 9 new, 12 changed. One report-tooling file changed. Every shared change is gated or additive (step 5).
- **ATTENTION A1:** at leads 183 and 365, a declined lead takes the *identity neighbour trees-off*. On the smoke this scored MAE 8.08 and 7.15. The donor median scored 3.90. On grids the identity trees-off equals guess-normal, but on the neighbour kind it does not. This is an owner item (see below).
- **ATTENTION A2:** owner item O29 also hits the ladder guard. 69 of 71 guard rows at lead 183 had no tree left, and 44 of 60 at lead 365. So the guard compares an arm with almost the same trees-off, and it failed at both leads.

## 1. Cross-file requests (BUILD_NOTES_*.md)

| Request | From | State |
|---|---|---|
| `route/__init__.py` docstring says the neighbour kind raises | neighbour | Done by the table builder (`route/__init__.py:16-23`). |
| Remove "2026" from the line-1 docstrings of the five table files | neighbour, coral_tables | Done before I started. `tests/test_nonames.py` passes: 43 passed. |
| Table pipeline calls `route/neighbour.py`, not the kinds.py stubs | table | Already wired: `pipeline/table_router.py:97` imports `treeroute.route.neighbour`. It calls `pool_feature_z` (:169), `NeighbourRows` (:215), `neighbour_pools` (:227), `dense_answers` (:244), `_route_neighbour_grid` / `_route_neighbour_at` (:277, :280, :396), `_trees_off_neighbour_pass` (:299), `pool_records` (:331) and `neighbour_base_point` (:380). |
| kinds.py stubs | neighbour | Left as built. `trees_off_neighbour` delegates (`route/kinds.py:1245-1249`). The other four approved names raise and name the built body. Reason: `tests/test_route_kinds.py` pins each approved parameter list, and `neighbour_pool_loro` cannot take the issue day there (owner item O19). |
| SPEC_TABLE_MODE.md 5.9 says kinds.py is not edited | neighbour | Not edited (it is a reviewed spec). Recorded here instead: kinds.py changed in the neighbour stubs and docstrings only (+41 -13 lines, no grid line). |
| Test doubles | task | None removed. The only double is `_FakeStore` (`tests/test_route_neighbour_fit.py:383`). It plants bad stores to test the G-DISJOINT and R20 refusals of `dense_answers`, and the real store cannot be made to fail that way. Its interface matches the real one (`fit/tables.py:650, :661, :936`). The real store is used end to end by the toy and the smoke. |
| `fit/weights.py` lost its CRLF line ends (whole-file diff) | found here | Fixed: line ends put back. Bytes otherwise the same. `test_fit_weights`, `test_fit_weights_blocks` and `test_table_mode_fold_gls` pass: 35 passed. |

## 2. Tests run (from `D:\treeroute\coral_build\engine`, `py -3.9 -m pytest -q -p no:cacheprovider`)

| Tests | Result |
|---|---|
| test_route_neighbour_pool, test_route_neighbour_fit, test_route_kinds, test_nonames, test_table_mode_contract, _vault_derive, _solve, _fold_gls, test_route_solve, test_route_weighted, test_route_region* | 362 passed, 18 skipped, 5 xfailed, 3 failed (all in LIVE too, below) |
| test_check_cli, test_check_deep, test_constants, test_derive_all, test_derive_loro_rules, test_fit_context, test_fit_weights, test_fit_weights_blocks, test_launch, test_load, test_noknob, test_packages_declarative, test_report_freeze, test_report_table, test_s1_score_context, test_schema, test_vault, test_vault_lock, test_vault_world, test_cli_allowlist | 1322 passed, 1 skipped, 11 failed (in LIVE too, or caused by test order, below) |
| test_table_mode_pipeline (toy end to end, leak probe, resume, pool audit, no grid helper reached, check quick/deep, report table) + test_pipeline (grid pipeline) | 44 passed in 8 min 45 s |

Failures, and why none comes from the build:

- `test_route_kinds.py::test_the_r36_tolerance_refuses_until_k_is_set` (`tests/test_route_kinds.py:176-178`). It expects C9 to be unset. Ruling N set it (`engine_constants.py:159`). The test file is the same as LIVE apart from the neighbour pins. I left it alone because it is a LIVE test. Suggested fix for the owner: assert `r36_tolerance(1.0) == max(K.GUARD_TOLERANCE_K, r36_floor())`.
- Six defo package tests fail with **LIVE's code too**:
  - `test_route_region_defo_package.py`: 2 tests;
  - `test_packages_declarative.py`: `test_defo_catalog_against_the_matrix_columns`, `test_catalog_covers_the_review_sheet[defo]`, `test_drafted_owner_fields_are_marked_unsigned[defo]` and `test_expected_derived_values_the_plan_names`.
  - I ran the same two files with LIVE's `treeroute` on the path, with no bytecode written and a scratch basetemp: the same 6 failed.
  - Causes: `datasets/defo_draft/exceptions.yaml` has LF line ends where `datasets/defo/exceptions.yaml` has CRLF (the same bytes as LIVE). The defo shape is (4615, 2197) against a planned (4285, 2040). These are package data, not engine code.
- `test_launch.py` (2 tests) and `test_cli_allowlist.py` (5 tests) failed only in my subset. In that subset `test_fit_weights` imports sklearn first, and sklearn sets `KMP_DUPLICATE_LIB_OK` and `KMP_INIT_AT_FORK`. The launcher then refuses (`launch.py:86`). With `test_fit_bank_primitives` first, as in the full suite's order, all 87 pass. The test files are the same as LIVE.

## 3. Toy end to end and the tiny coral smoke

- Toy: `tests/test_table_mode_pipeline.py` passed (13 tests, in the 44 above).
- Smoke command, from `D:\treeroute\coral_build\engine`:
  `py -3.9 -m treeroute smoke D:/treeroute/coral_build/coral_data/tiny/package --run-root D:/treeroute/coral_build/runs`
- Package: `coral_data/tiny/package` is the generated copy of `datasets/coral_draft`. It differs only in its name (`coral_draft_tiny`), a header comment, the store line (it points at `coral_data/tiny/lead_{lead}.parquet`) and a short split.yaml. `datasets/coral_draft` itself points at `coral_data/full/`, which is not built (U6). So the smoke ran on the tiny copy.
- No grid-only step blocked the run. No branch fix was needed.
- Run folder: `D:\treeroute\coral_build\runs\coral_draft_tiny\smoke\20261019_f60f582e`. Log: `D:\treeroute\coral_build\runs\smoke_tiny_1.log`.
- Run time 22.6 s. Peak RAM of the process tree 0.206 GB (sampled every 0.25 s). Lowest free RAM 4.99 GB. Exit 0.
- `manifest.json` records `engine_code_hash` bd770479... (the hash that ignores comments). The file hash is in step 4.

Smoke data: 4 groups, 372 rows at lead 0, 63 tree columns, 5 context columns, 96 test rows, 12 trees per group.

Scores (pooled test MAE on 96 rows; persistence only on rows that have an earlier label). Smoke size: no sign information.

| Lead | Adopted (what is scored) | Pinned tree arm | Its trees-off | Identity trees-off | Donor median | Predict-zero | Persistence / damped |
|---|---|---|---|---|---|---|---|
| 0 (nowcast) | log_c_plain_unweighted, 3.8359 | (same) | log_c trees-off 3.8373 | 4.3419 | 3.8957 | 3.8957 | n/a |
| 183 | decline: identity trees-off, 8.0796 | log_c_plain_unweighted, 6.0291 | guard rows: 2.14208 vs arm 2.14241 (71 rows), FAILS | 8.0796 | 3.8957 | 3.8957 | 5.6040 / 4.7884 (71 rows) |
| 365 | decline: identity trees-off, 7.1521 | log_c_plain_unweighted, 3.4658 | guard rows: 2.18401 vs arm 2.18736 (60 rows), FAILS | 7.1521 | 3.8957 | 3.8957 | 5.8126 / 4.0339 (64 rows) |

- Lead-0 verdict: `does_not_help_equivalent` against `base__donor_median` (reference_rule donor_row_median). Contrast 0.0463 [-0.0200, 0.1126], band 0.1676. 3 of 4 groups better. Sign flip: North and central Red Sea.
- The donor median equals predict-zero here, because the median label of the donor rows is 0.
- G-PLUMB: every checked pair passed within 9e-7. The largest gap was 2.1e-9 (identity trees-off vs the closed form).

Pool fallbacks and rows with no tree left:

| Pass | Rows | Pool fallback (<12 rows) | Rows with no tree left |
|---|---|---|---|
| nowcast decision surface | 81 | 0 | 46 |
| nowcast test pass | 96 | 0 | 4 |
| lead 183 guard | 71 | 0 | 69 |
| lead 183 test pass | 96 | 0 | 0 |
| lead 365 guard | 60 | 0 | 44 |
| lead 365 test pass | 96 | 0 | 0 |

Every pool held exactly 50 rows. The latest pool day was always before the issue day. Across all 71 kernel records, the largest `max_pool_day_minus_issue_day` was -20 days.

## 4. Engine hash

`engine_code_sha256` from `D:\treeroute\coral_build\engine` = `53025a4987e26a68c491cd0da90be45fbbdc51642668e723741b8ebdeed7d947`.
LIVE = `65a177bc7cdd47bacca806582bd13be52706ba3da385bb468fe1f0f24b81a0ff`. The move is expected (ruling U5). The report-tooling hash also moves, because `treeroute_report/table.py` changed.

## 5. Diff against LIVE (treeroute + treeroute_report, `.py` files; `_proposed` is the same)

New files (no grid module imports them at import time):

| File | Lines |
|---|---|
| treeroute/check/table.py | 125 |
| treeroute/derive/table.py | 293 |
| treeroute/labels/rows.py | 217 |
| treeroute/package/table.py | 594 |
| treeroute/pipeline/table_ladder.py | 647 |
| treeroute/pipeline/table_passes.py | 600 |
| treeroute/pipeline/table_router.py | 408 |
| treeroute/pipeline/table_run.py | 417 |
| treeroute/route/neighbour.py | 942 |

Changed shared files (lines LIVE -> build, added / removed per `diff`):

| File | LIVE -> build | +/- | Why grids are unaffected |
|---|---|---|---|
| check/deep.py | 1303 -> 1309 | +6 -0 | A guarded branch at :1099-1106 runs only when `is_table_package` is true or `ctx.input == "table"`. `is_table_package` only reads dataset.yaml, and any error gives False (`package/table.py:121-130`). |
| check/quick.py | 377 -> 385 | +9 -1 | The same guarded dispatch (:250-255). The -1 is the docstring. |
| check/report.py | 214 -> 221 | +7 -0 | The branch at :96 runs only when `dataset.input == "table"`. Grid datasets default to "grid". |
| derive/router_rules.py | 386 -> 392 | +6 -0 | Inside `if bool(is_events):` (:338-344). Grids pass `is_events=False`. CRLF kept. |
| fit/context.py | 782 -> 815 | +33 -0 | Adds the method `donor_rows_outside` (:650). No existing line changed. Only the table pipeline calls it. |
| fit/weights.py | 686 -> 772 | +87 -1 | Adds `weight_models_for_folds` (:652). The -1 is `__all__`. `weight_model_for_cut` is not edited. CRLF restored (this integration). |
| package/load.py | 271 -> 291 | +20 -0 | `check_input_roles` (:240, called at :271) returns at once for a grid package that declares no table key role. |
| package/schema.py | 554 -> 601 | +52 -5 | `input` defaults to "grid" (:268). `static` became Optional (:234), but `_input_kind` (:273) refuses a grid package without it. Six roles are added to ROLES, and they are allowed only in table packages (:433, load.py:240). No `model_dump` of DatasetFile reaches any output (only store catalogs are dumped: `derive/orchestrate.py:107`, `check/facts.py:30`). Message-only change: a grid dataset.yaml without `static` is still refused, with new text. CRLF kept. |
| pipeline/run.py | 1524 -> 1543 | +20 -1 | `_is_table` (:1500) is checked first in `run_pipeline` (:1481) and `plan_pipeline` (:1493). On a grid package it is False, and the same `Pipeline(...)` call follows. The -1 is the docstring. |
| route/__init__.py | 22 -> 28 | +8 -2 | Docstring only. |
| route/kinds.py | 1272 -> 1300 | +41 -13 | Only the five neighbour stubs, `_NEIGHBOUR` and docstrings. `trees_off_neighbour` imports `route.neighbour` lazily, and no grid path calls it. |
| route/solve.py | 332 -> 336 | +30 -26 | Adds the keyword `n_unpenalised=UNPENALISED_COLUMNS` (still 2) to all ten solvers. `o = n_unpenalised` (:76, :101, :133). It is forwarded through the internal calls, and no operation is reordered. Grid callers never pass it. `test_table_mode_solve` checks LIVE's exact bytes for all ten solvers with the keyword left out. |
| treeroute_report/table.py | 850 -> 858 | +11 -3 | :239-242 skip only a stratum record that has `values` and no `edges`. :374 uses the donor median only when verdict.json says `reference_rule: donor_row_median`. :666 prints "per value" only when the edge columns are absent. Grid verdicts always record edges and never `reference_rule`. |

Grid evidence so far:

- `test_pipeline.py` passes: 31 tests on the synthetic grid package.
- `test_table_mode_contract.py` loads every package in `datasets/` the same under LIVE and the build.
- `test_table_mode_solve.py` checks the solver bytes.

**Not yet run:** the byte-for-byte grid tripwire of SPEC_TABLE_MODE.md 5.10 (the four `*_draft` smokes plus the synthetic grid package, LIVE against the build). The full suite was not run either. Both belong to the Fix phase.

## Owner items found or sharpened here

- **A1 (new): the decline target of a neighbour lead.** `pipeline/table_ladder.py:25, :139, :261` use the identity trees-off as the decline target, copied from grids (SPEC_TABLE_MODE.md:445, :525). On grids that equals guess-normal. On the neighbour kind it is a local ridge on 50 pool rows. On the smoke it scored 8.08 / 7.15 against the donor median's 3.90 (the signed R34 reference). The alternative: decline to the donor-row median. I changed nothing; this needs a ruling.
- **A2 (sharpens O29): the guard has nothing to test when no tree is left.** At the ladder guard cuts, most rows lose every tree (69/71 and 44/60), so the arm and its trees-off almost match, and the guard fails. A full run has more rows per group, so this should shrink. Measure it on the full build.
- **A3: stale LIVE tests.** The r36 test and the six defo package tests fail on LIVE code too. They are not part of this build. They will show in the Fix-phase full suite.
- O19 (partial kinds.py wiring), O28 to O30, P1 (2016-2019 test window) and the rest stand as the builders wrote them.
- Added in the fix phase (FIX_REPORT.md): N17 (season in Z), N18 (the legacy replay harness of SPEC_NEIGHBOUR.md
  section 8 was never built), A4 (correctors at the inner cut: no tree there has 50 out-of-bag rows on the tiny
  build, so every corrector arm equals its plain arm on the decision surface; the run now records it per bank),
  A5 (check_tables.py Part B recomputes 53 of 74 columns; 21 rest on the builder's canary only).
