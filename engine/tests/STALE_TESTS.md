# The 33 out-of-date engine tests

Written for the public archive on 2026-11-18 and revised on 2026-11-23. This note lists the 33 tests that failed in the
recorded full run of the engine's test suite on 930d961c, each with the reason that the run's log gives. It changes
no test file.

## The record

- **The run.** The full test suite on a build copy of the engine whose code hash is 930d961c, on 2026-10-20,
  before that version was installed as the project's engine (`engine/PENDING_PARTS.md`, Parts 594 and 595). It
  gave 3,500 passed, 33 failed and 62 expected failures. The paper calls the 33 failures stale package and draft
  tests, and its fact sheet records that none of this changes a reported number (fact M2 of
  `records/fact_sheet/PAPER_FACTS.md`).
- **Its log** stays in the project's folder of that build copy, which the archive does not hold. The table below
  gives the 33 tests in the order of that log.
- **An archived log of the same failures.** The full suite on the earlier build 704c8aea, archived as
  `coral_build/fullsuite2.log` (3,483 passed, 33 failed and 62 expected failures; Part 593), failed the same 33
  tests in the same order, with the same errors.

## The tests

Each test is in `engine/tests/`, with its `def` at the line given. A draft is a package's draft copy,
`engine/datasets/<package>_draft/`, which the generator `engine/datasets/_tools/refresh_drafts.py` writes from the
package with a DRAFT stamp.

| # | Test | Line of its `def` | Reason in the record |
|---:|---|---:|---|
| 1 | `engine/tests/test_catalog_timing_facts.py::test_defo_aggregates_cover_every_monthly_driver_and_are_engineered` | 377 | Expects defo's annual aggregates to come from 101 monthly panel columns; they come from 100. |
| 2 | `engine/tests/test_catalog_timing_facts.py::test_defo_aggregate_store_facts_are_declared_and_inherited` | 399 | The seed catalog `engine/datasets/_stores/defo_annual_features_schema_catalog.yaml` gives V01_mean_temp_C_mean the fact status 'unverified'; its monthly parent in the panel catalog has 'assumed', and the test's list of known differences does not name it. |
| 3 | `engine/tests/test_catalog_timing_facts.py::test_co_measured_answer_decides_the_lag_parents_aggregates` | 463 | defo's catalog marks V11_mean_ndvi_mean as co-measured with the target; the test expects that answer only on the aggregates of the four parents that ruling J4 names. |
| 4 | `engine/tests/test_defo_k_ruling.py::test_k_verdicts_as_ruled` | 246 | Expects defo's disclosure of the G-LINEAGE stand-in to be unsigned; the author signed it on 2026-10-06 (ruling N). |
| 5 | `engine/tests/test_fire_package.py::test_the_draft_copies_are_byte_identical_to_the_package_files` | 118 | The fire draft is not what the generator writes from the fire package: five files differ, ban.yaml first. |
| 6 | `engine/tests/test_fire_package_bans.py::test_the_disclosures_of_kept_defects_are_present_and_unsigned` | 494 | Looks for one fire disclosure of the amended ruling J3 (the livestock columns kept as watch columns) by the start of its check text; no entry matches. |
| 7 | `engine/tests/test_layer_shapes.py::test_functions_take_the_approved_parameters` | 123 | `weight_model_for_cut` has a parameter `matrix_dir` that the test's list of approved additions does not name (brought up to date since; see below). |
| 8 | `engine/tests/test_ndvi_package_ban.py::test_j2d_the_last_value_columns_are_kept_and_disclosed` | 275 | Expects the ndvi disclosure of snow_cover_fraction to be unsigned; the author signed it on 2026-10-06 (ruling N). |
| 9 | `engine/tests/test_ndvi_package_ban.py::test_j3_livestock_is_a_lagged_watch_column_never_frozen` | 337 | Expects the ndvi disclosure of aglw_cattle to be unsigned; the author signed it on 2026-10-06 (ruling N). |
| 10 | `engine/tests/test_ndvi_package_draft.py::test_the_ndvi_draft_is_the_installed_package_stamped` | 35 | The ndvi draft is not what the generator writes from the ndvi package: ban.yaml and exceptions.yaml differ. |
| 11 | `engine/tests/test_packages_declarative.py::test_defo_catalog_against_the_matrix_columns` | 444 | 40 columns of the defo matrix files are not declared in the catalog (h_cum first); the test allows only the 33 lag1_* columns. |
| 12 | `engine/tests/test_packages_declarative.py::test_catalog_covers_the_review_sheet[defo]` | 562 | The defo review sheet has columns (h_cum, h_lag1, h_lag2, h_lag3, land_px and others) that are neither in the catalog nor among the rows the test expects to be left out. |
| 13 | `engine/tests/test_packages_declarative.py::test_drafted_owner_fields_are_marked_unsigned[defo]` | 720 | Accepts only unsigned entries and the signatures of 2026-10-06 (ruling N); defo's entry for the scPDSI look-ahead was signed on 2026-10-17 (ruling T). |
| 14 | `engine/tests/test_packages_declarative.py::test_expected_derived_values_the_plan_names` | 779 | Expects 4,285 bank and 2,040 scored units per defo group; defo's `expected_derived.json` has 4,615 and 2,197, the values of the defo run after its first year moved to 2004 (fact C2). |
| 15 | `engine/tests/test_packages_pm25_bans.py::test_j3_the_extension_used_india_ratios_for_every_region` | 470 | File not found: the test reads `presplit_cc/fetch_livestock_extend.py` from the folder that holds the engine folder, and the build copy had no such script beside it (the archive holds the script as `rebuild/presplit_cc/fetch_livestock_extend.py`). |
| 16 | `engine/tests/test_packages_pm25_bans.py::test_the_j_disclosures_are_present_and_unsigned` | 563 | The pm25 disclosure of aglw_cattle lacks the wording that the test looks for. |
| 17 | `engine/tests/test_pipeline_draft.py::test_the_draft_is_what_the_generator_writes_from_the_real_package[pm25]` | 47 | The pm25 draft is not what the generator writes from the package: ban.yaml and exceptions.yaml differ. |
| 18 | `engine/tests/test_pipeline_draft.py::test_the_draft_is_what_the_generator_writes_from_the_real_package[fire]` | 47 | The fire draft is not what the generator writes from the package: five files differ, ban.yaml first. |
| 19 | `engine/tests/test_pipeline_draft.py::test_the_draft_is_what_the_generator_writes_from_the_real_package[ndvi]` | 47 | The ndvi draft is not what the generator writes from the package: ban.yaml and exceptions.yaml differ. |
| 20 | `engine/tests/test_pipeline_draft.py::test_the_draft_is_what_the_generator_writes_from_the_real_package[defo]` | 47 | The defo draft is not what the generator writes from the package: exceptions.yaml differs. |
| 21 | `engine/tests/test_pipeline_draft.py::test_the_draft_copies_are_byte_identical_to_the_package_code[pm25]` | 52 | The pm25 draft's exceptions.yaml has LF line endings where the package's has CRLF. |
| 22 | `engine/tests/test_pipeline_draft.py::test_the_draft_copies_are_byte_identical_to_the_package_code[fire]` | 52 | The fire draft's exceptions.yaml has LF line endings where the package's has CRLF. |
| 23 | `engine/tests/test_pipeline_draft.py::test_the_draft_copies_are_byte_identical_to_the_package_code[ndvi]` | 52 | The ndvi draft's exceptions.yaml has LF line endings where the package's has CRLF. |
| 24 | `engine/tests/test_pipeline_draft.py::test_the_draft_copies_are_byte_identical_to_the_package_code[defo]` | 52 | The defo draft's exceptions.yaml has LF line endings where the package's has CRLF. |
| 25 | `engine/tests/test_pipeline_draft.py::test_the_draft_loads_with_todays_ban_list_and_every_verdict_stamped[pm25]` | 71 | Loaded, the pm25 draft's disclosures (exceptions.yaml) differ from the package's; its catalog and split match. |
| 26 | `engine/tests/test_pipeline_draft.py::test_the_draft_loads_with_todays_ban_list_and_every_verdict_stamped[fire]` | 71 | Loaded, the fire draft's disclosures (exceptions.yaml) differ from the package's; its catalog and split match. |
| 27 | `engine/tests/test_pipeline_draft.py::test_the_draft_loads_with_todays_ban_list_and_every_verdict_stamped[ndvi]` | 71 | Loaded, the ndvi draft's disclosures (exceptions.yaml) differ from the package's; its catalog and split match. |
| 28 | `engine/tests/test_pipeline_draft.py::test_the_draft_loads_with_todays_ban_list_and_every_verdict_stamped[defo]` | 71 | Loaded, the defo draft's disclosures (exceptions.yaml) differ from the package's; its catalog and split match. |
| 29 | `engine/tests/test_route_region_defo_package.py::test_the_draft_is_defo_as_installed_and_every_verdict_is_stamped` | 1011 | The defo draft is not what the generator writes from the package: exceptions.yaml differs. |
| 30 | `engine/tests/test_route_region_defo_package.py::test_the_draft_copies_and_stores_match_the_package` | 1031 | The defo draft's exceptions.yaml has LF line endings where the package's has CRLF. |
| 31 | `engine/tests/test_timing_schema.py::test_timing_on_the_declared_packages[pm25]` | 73 | Expects each index column of ruling L1 (b) to lag one month on pm25; pdo lags two months. |
| 32 | `engine/tests/test_timing_schema.py::test_timing_on_the_declared_packages[fire]` | 73 | Expects each index column of ruling L1 (b) to lag one month on fire; pdo lags two months. |
| 33 | `engine/tests/test_timing_schema.py::test_timing_on_the_declared_packages[ndvi]` | 73 | Expects each index column of ruling L1 (b) to lag one month on ndvi; pdo lags two months. |

In short: 16 tests (5, 10 and 17-30) find that the package drafts no longer match their packages; 4 (4, 8, 9 and
13) expect disclosures to be unsigned that the author has since signed; 8 (1-3, 6, 11, 12, 14 and 16) find a
count, a column list, a fact or a wording other than the one they expect; test 7 checks a list of approved
parameters, test 15 reads a script that was not beside the build copy, and tests 31-33 check the lag of pdo.

Tests 11 and 15 also read files at fixed paths on the project's machine (`D:/defo_matrix/` and
`D:/ndvi_drivers/livestock_aglw/`); on a machine without them, they are skipped.

## Since the recorded run

- The file of test 7 was brought up to date later on 2026-10-20: its list of approved additions now names
  `matrix_dir` (ruling X1) and the logging-only keyword `echo`, and the file's 6 tests then passed, test 7 among
  them (Part 596). The archive holds that later file.
- The other 11 test files, the four gridded packages and their drafts, the store catalogs and the generator are
  the same in the project as in the run. The archive's own text changes to these test files and to the generator
  are in docstrings and one comment only (`CHANGES_FOR_ARCHIVE.md`), and the packages and drafts are archived
  unchanged.
- No later full run of the suite is recorded.
