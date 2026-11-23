# BUILD REPORT: the table option and the neighbour router (ruling U)

Written 2026-10-19 by the report agent. Everything is under `D:\treeroute\coral_build`. LIVE was only read.
Sources: INTEGRATE_REPORT.md, BUILD_NOTES_table.md, BUILD_NOTES_neighbour.md, BUILD_NOTES_coral_tables.md,
coral_tables\README.md, the three SPEC_*.md files, and the fix agent's review (workflow journal).

## ATTENTION (read first)

1. **The fix phase did not finish.** There is no FIX_REPORT.md. The fix agent applied its two fixes, then stopped
   while "still waiting on the suite". **The full suite stopped at 4%** (log `review_tests\fullsuite_fix.log`,
   last write 21:29; no Python process alive). Its 3 failures so far are old: they fail on LIVE too (section 2).
   **You must run the full suite once** (command in 4c, about 45 min).
2. **The no-op proof on the FINAL engine is only partly done.** The fix agent compared all four grid smokes (LIVE vs
   build) at 20:02 and they matched. The engine changed after that (fixes at 21:18-21:21, incl. shared
   `check/quick.py`). Only defo was re-run on the final engine: it matches, module list included. **Run
   `run_noop_proof.ps1` (4a) before the install.**
3. **A1: a declined coral lead falls to a bad baseline.** At leads 183 and 365 the ladder declines to the *identity
   neighbour trees-off*. That scored MAE 7.44 and 7.13. The donor median scored 3.90. Needs a ruling (item 1 in
   section 3).
4. **A2: the lead guard has almost nothing to test.** The signed pool-drop rule removes every tree from 69 of 71
   guard rows (lead 183) and 44 of 60 (lead 365). The guard failed at both leads. Item 2 in section 3.
5. **P1 (test window 2016-2019) must be signed before any full coral smoke or run** (SPEC_CORAL_TABLES.md:369).

## 1. What was built

| Part | Where | What |
|---|---|---|
| Table option | `engine\treeroute\package\table.py`, `labels\rows.py`, `derive\table.py`, `pipeline\table_run.py`, `table_passes.py`, `table_ladder.py`, `check\table.py` | `input: table` in dataset.yaml. Ready rows, one file per lead. Grid-only steps skipped. Date checks kept (T-FILES ... T-MARK). |
| Neighbour router | `engine\treeroute\route\neighbour.py` (+ `pipeline\table_router.py`) | 150 nearest earlier rows by map, then 50 nearest in feature space. Under 12 rows: donor-row median (C11). Strict pool: train rows dated before the issue day, never a test row. Pool groups' trees dropped (signed default). |
| Coral tables builder | `coral_tables\` (`build_visits.py`, `build_tables.py`, `check_tables.py`, `columns.py`) | Package-side, not engine code. Tiny build done: 897 rows per lead, look-ahead canary 0 mismatches, legacy replay exact, checker 52/52 pass, negative control sees a 1-day leak. Full build NOT run. |
| Package draft | `engine\datasets\coral_draft\` (+ tiny copy `coral_data\tiny\package\`) | 85 columns (69 tree, 5 context), ban 76 verdicts, 17 exceptions, AUDIT_CHECKLIST. Store points at `coral_data/full/`, not built yet. |

Files changed against LIVE (diff run today):

- New engine files (9): `check/table.py`, `derive/table.py`, `labels/rows.py`, `package/table.py`,
  `pipeline/table_ladder.py`, `table_passes.py`, `table_router.py`, `table_run.py`, `route/neighbour.py`.
- Changed shared engine files (12): `check/deep.py`, `check/quick.py`, `check/report.py`, `derive/router_rules.py`,
  `fit/context.py`, `fit/weights.py`, `package/load.py`, `package/schema.py`, `pipeline/run.py`, `route/__init__.py`,
  `route/kinds.py`, `route/solve.py`. Each is gated on the table option or is additive (INTEGRATE_REPORT.md section 5).
- Report tooling (1): `treeroute_report/table.py`.
- Tests: 10 new (`table_toy.py`, `test_table_mode_*.py` x5, `test_route_neighbour_pool.py`,
  `test_route_neighbour_fit.py`, `test_report_table_edges.py`, `test_table_router_leads.py`), 1 changed
  (`test_route_kinds.py`).
- Fix-phase changes (applied): `is_table_package` moved to `package/load.py:297`, so grid runs load no new module
  (`run.py:1504`, `quick.py:250`, `deep.py:1099`); report "per value" label fixed (`treeroute_report/table.py:673`).

| Hash | Value |
|---|---|
| LIVE `engine_code_sha256` | `65a177bc7cdd47bacca806582bd13be52706ba3da385bb468fe1f0f24b81a0ff` |
| **Build `engine_code_sha256` (final, computed now)** | **`a49009845eb7f7c5351443666e75a95c6037913aae59d3624ff71df0fe720e5e`** |
| Build `engine_code_hash` (ignores comments) | `a1471f17e34ee681fd9366e003759788dd085e94a83c0f4789e77a032759e688` |

INTEGRATE_REPORT.md's hash `53025a49...` is out of date (it was taken before the fixes).

## 2. Test results

- **Full suite: not completed.** 3,592 tests collected. The run stopped at about 4%. The 3 failures seen
  (`test_catalog_timing_facts.py`: two defo aggregate tests and `test_co_measured_answer...`) fail the same on LIVE
  (I ran that file against both: 3 failed, 113 passed each).
- Relevant tests during the build (INTEGRATE_REPORT.md section 2): 362 + 1322 + 44 passed. Failures were all old:
  `test_route_kinds.py::test_the_r36_tolerance_refuses_until_k_is_set` (C9 set by ruling N), 6 defo package tests
  (package data), and 7 launcher tests that fail only in a subset order (sklearn sets KMP_* first).
- Fix agent's grid-path tests: 1,609 passed, 8 failed; the same 8 fail on a LIVE copy.
- Grid byte-identity so far: pm25, fire, defo, ndvi smokes (signed packages) identical LIVE vs build at 20:02 in
  every parquet/CSV, derived.json and every cleaned JSON record (I re-checked them with `tools\compare_runs.py`:
  all exit 0). defo re-run on the final engine (21:25): identical. Headline-table tool: 11 files identical.

### Tiny coral smoke (final engine, run `runs\coral_draft_tiny\smoke\20261019_6a40c185`)

**Only 4 ecoregions** (Andaman Sea, Maldive Islands, Moreton Bay, North and central Red Sea), 96 test rows.
**This is a plumbing test, not a result. Smoke deltas carry no sign information.** Pooled test MAE:

| Lead | Scored (adopted) | Pinned tree arm | Its trees-off | Identity trees-off | Donor median | Predict-zero |
|---|---|---|---|---|---|---|
| 0 (nowcast) | log_c_plain_gls 3.779 | (same) | 3.837 | 4.342 | 3.896 | 3.896 |
| 183 | **declined: identity trees-off 7.441** | log_c_plain_gls 3.904 | 3.890 | 7.441 | 3.896 | 3.896 |
| 365 | **declined: identity trees-off 7.132** | log_c_plain_gls 4.557 | 3.933 | 7.132 | 3.896 | 3.896 |

- Lead-0 verdict: `does_not_help_equivalent` against the donor median (3 of 4 groups better).
- The donor median equals predict-zero here: the median donor label is 0.
- Persistence / damped persistence: lead 183: 5.604 / 4.788 (71 rows); lead 365: 5.813 / 4.034 (64 rows).
- Pools (first smoke): 0 fallbacks; every pool 50 rows; newest pool day always at least 20 days before the issue day.
- Run time 23 s, peak 0.21 GB.

## 3. OWNER ITEMS (answer before the coral freeze)

Until answered, the engine follows the signed rules and the drafted defaults below.

1. **A1. Decline target at a coral lead.** (a) identity neighbour trees-off, as built (copied from grids, where it
   equals guess-normal); (b) the donor-row median, the signed R34 reference; (c) the own-link trees-off of the
   pinned arm. **Recommend (b).** On the neighbour kind (a) is a local ridge, not "normal", and it scored 7.4 vs 3.9.
2. **A2 / O29. Pool drop removes every tree in small pools.** (a) keep the signed default and measure the
   no-tree share on the full build; (b) drop only the row's own group block (N7; needs a signature).
   **Recommend (a)** now; revisit only if the full build still shows most guard rows with no tree.
3. **P1. Test window.** (a) 2016-2019 as drafted, 2017-2020 as the declared sensitivity row; (b) R3 on all data
   (2017-2020). **Recommend (a).** Must be signed before any full coral smoke or run.
4. **O26. TABLE_DEPARTURES** (absent rows, pool horizon, etc.). (a) accept at the coral freeze, as S21; (b) keep them
   as not-headline reasons. **Recommend (a)**, listed in the pre-registration.
5. **O13 / P23 / P6. Groups the defaults refuse** (0 rows at a bank cut; one-site groups; 11 groups, 35 test
   visits). (a) exclude in split.yaml, disclosed (drafted); (b) engine change so they still lend pool rows.
   **Recommend (a).**
6. **O28. A group with no test row.** (a) exclude it in split.yaml (package side); (b) let it leave the scored
   lists (engine reading of R18). **Recommend (a).**
7. **N18. Legacy replay harness** (SPEC_NEIGHBOUR.md section 8) was never built. (Update 2026-10-19: built by
   ruling V7; see replay/REPLAY_REPORT.md and RULING_V_REPORT.md.) (a) build the toy-only harness
   before the full run (small job); (b) skip it, rely on the brute-force solver tests. **Recommend (a).**
8. **N17. Season in the feature-space step.** (a) tree features only, season enters as router context (H3), as
   built; (b) add the context to Z like legacy. **Recommend (a).**
9. **P17 / P13 / P14. Source timing.** g = 1 day SST/cyclone gap (UTC vs local dates); ERSST V6 reach assumed
   from R-A; DMI stays conditional. **Recommend keeping all three as drafted**, disclosed.
10. **A5. Checker coverage.** `check_tables.py` recomputes 53 of 74 columns; 21 rest on the builder's canary
    (which rebuilds every row from truncated sources). (a) accept, disclosed; (b) extend the checker.
    **Recommend (a).**
11. **A4. Correctors at the inner cut.** On the tiny build no tree has 50 out-of-bag rows, so corrector arms equal
    plain arms on the decision surface (the run records this per bank). Information only; measure on the full build.
12. **A3. Stale LIVE tests** (r36 test; defo package tests; catalog timing tests). (a) leave them, list them as
    known failures; (b) fix the r36 assertion to `r36_tolerance(1.0) == max(K.GUARD_TOLERANCE_K, r36_floor())`
    (test only, not hashed). **Recommend (b)** for r36 and (a) for the package-data tests.
13. **O19.** kinds.py: only `trees_off_neighbour` delegates; the other approved names raise and name the built body
    (a pinned test fixes their parameter lists). **Recommend accept.**

Other drafted defaults stand as written: O1-O27 (SPEC_TABLE_MODE.md:762-784), N3-N16 (SPEC_NEIGHBOUR.md:416-424),
P2-P26 (SPEC_CORAL_TABLES.md:369-394).

## 4. THE OWNER'S NEXT COMMANDS (PowerShell, in order)

Close games and large programs first. One heavy job at a time.

### a. The no-op proof (about 30-35 min)

```powershell
powershell -ExecutionPolicy Bypass -File D:\treeroute\coral_build\run_noop_proof.ps1
```

- It checks each engine imports its own `treeroute`, prints both hashes (build must print `a4900984...0e5e`).
- It runs the smokes of `pm25`, `fire`, `defo`, `ndvi` from `LIVE\datasets` one after another: LIVE into
  `D:\treeroute\coral_build\noop\old`, then the build into `...\noop\new` (the same package folders for both).
- It then runs `tools\compare_runs.py` on each pair: every parquet/CSV and derived.json byte for byte; every other
  JSON after removing only times, pids, paths, engine hashes and fingerprints.
- Output: `noop\noop_summary.txt`, logs in `noop\logs\`. **It must end "RESULT: PASS" (exit 0).** Only `run.log`
  and `phases\*\DONE` may be listed as "other files that differ". If anything else differs: STOP, do not install.
- `tools\compare_runs.py` is a verbatim copy of `D:\treeroute\engine_next\tools\compare_runs.py` (same SHA-256).
  Tested: two copies of one defo smoke folder give exit 0; a copy with one parquet byte and one JSON value changed
  gives exit 1 and names both files (`tools\_selftest\`). A dry run of the script with fake smokes passed.
- Time: today the same 8 smokes took 28 min (defo ~1 min, pm25 ~2, fire ~3, ndvi ~4-5 each, per engine).

Then the one full suite in the build (about 45 min):

```powershell
Set-Location D:\treeroute\coral_build\engine
py -3.9 -m pytest -q -p no:cacheprovider --basetemp D:\treeroute\coral_build\pt\full *>&1 | Tee-Object D:\treeroute\coral_build\fullsuite_owner.log
```

Expected failures: only the old ones in section 2 (r36, defo package tests, catalog timing tests).

### b. The full coral table build (about 26-30 min build + 6 min check, about 1 GB RAM)

Ruling U6 puts this after the install (c1). The builder does not import the engine, so the order does not change
the tables. Sign P1 first.

```powershell
Set-Location D:\treeroute\coral_build\coral_tables
py -3.9 -u build_tables.py --build full *>&1 | Tee-Object -FilePath D:\treeroute\coral_build\coral_data\full_build_console.log
py -3.9 -u check_tables.py --build full *>&1 | Tee-Object -FilePath D:\treeroute\coral_build\coral_data\full_check_console.log
py -3.9 -u build_tables.py --publish full
```

An interrupted build restarts from the beginning. `--publish` prints the store line; it edits nothing.

### c. After that (not run; for the owner)

1. **Install into LIVE** (only after 4a passes and the full suite shows no new failure). As in
   `D:\treeroute\engine_next\INSTALL_AFTER_NDVI.md` step c: move the 12 changed engine files, `treeroute_report\table.py`
   and `tests\test_route_kinds.py` aside to `LIVE\_moved_coral_<date>\`; copy the 22 engine/report files and 11 test
   files of section 1 in by explicit name (no recursive copy). Verify from LIVE: `engine_code_sha256()` prints
   `a4900984...0e5e`, no new nested folder, and `tests/test_nonames.py tests/test_noknob.py` pass.
2. **Coral package**: set `stores.target` in `datasets\coral_draft\dataset.yaml` to the line `--publish` printed;
   add `D:/treeroute/coral_build/coral_store` to `D:\treeroute\registry\protected_roots.txt`; copy the package into
   `LIVE\datasets\`; add its entry to `treeroute_report\continuity_groups.yaml`.
3. **Checks and a full-data smoke** from LIVE: `py -3.9 -m treeroute check <pkg>`, then `--deep`, then
   `py -3.9 -m treeroute smoke <pkg>`. Read the no-tree share (A2) and the decline baseline (A1) there.
4. **Pre-registration Part** for coral: the answers to section 3, the U2 vouching statement, TABLE_DEPARTURES, the new
   engine hash, and the disclosure that the four grid headline runs keep their old hash (U5).
5. **Plan and freeze**: `py -3.9 -m treeroute plan <pkg>` (heavy, alone), then
   `py -3.9 -m treeroute_report.freeze <pkg> --prereg PREREGISTRATION_DRAFT_coral.md` and
   `py -3.9 -m treeroute_report.freeze verify`. The owner signs.
6. **Headline run**: `py -3.9 -m treeroute run <pkg>`, then `py -3.9 -m treeroute report`.

## Files written by this step

- `D:\treeroute\coral_build\BUILD_REPORT.md` (this file)
- `D:\treeroute\coral_build\run_noop_proof.ps1` (not run)
- `D:\treeroute\coral_build\tools\compare_runs.py` (copy of the engine_next tool)
- `D:\treeroute\coral_build\tools\_selftest\` (compare self-test folders, about 3 MB, and the dry-run script)
