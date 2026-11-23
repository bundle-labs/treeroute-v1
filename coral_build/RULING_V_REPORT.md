# RULING V REPORT: the coral build after owner ruling V (V1-V12)

Written 2026-10-19. Ruling: `OWNER_RULINGS_2026-10-06.md` section V (LIVE, read only). Everything written is under
`D:\treeroute\coral_build`. LIVE was not touched. Nothing was deleted (old copies are in `_moved\`).

## ATTENTION (read first)

1. **Run `run_final_checks.ps1` before anything else (about 75-80 min).** The last full grid no-op proof was at
   hash `a4900984...`. Since then `layer/decide.py` changed. It is shared with grid runs. Its new code runs only when a
   decline baseline is passed, and grid callers pass none. The defo smoke was re-run and is byte-identical to LIVE
   (`CHECK_REPORT_V.md` section 4). pm25, fire and ndvi wait for this proof. It must end `RESULT: PASS`.
2. **Confirm V6 (your choice).** Leaving out the 46 groups with no test row also takes their 1,874 train visits out of
   every bank, the decision surface and every neighbour pool (`package/table.py:504-507`). The option you signed did
   not give this count. (a) keep it as built; (b) keep them as train and pool rows and drop them only from the scored
   lists (an engine change).
3. **One old test failure stays: `test_layer_shapes.py::test_functions_take_the_approved_parameters`.** It fails on
   `weight_model_for_cut`'s `matrix_dir` parameter (`fit/weights.py:526`). LIVE fails it too. Approving `matrix_dir`
   is your signature decision.
4. **The tiny smoke cannot tell "donor median" from "predict zero".** The tiny donor-row median is 0. So both give
   3.8957. The V1 logic is covered by tests instead (below).
5. **Information: the engine's ridge grid is narrower in levels than the legacy default.** Legacy default: 15 levels
   x 1 ratio (0.5). Engine: 7 levels (0.1-100) x 5 ratios (0.0625-1). Every engine level is a legacy level; the
   legacy ratio is in the engine grid. Not a fault; reported by the replay (`replay\REPLAY_REPORT.md` ATTENTION 4).
6. **On the tiny data almost no trees are left on the guard rows** (V2): 69 of 71 rows at lead 183 and 44 of 60 at
   lead 365. So each lead guard there is mostly trees-off against the median. Read the share on the full smoke.

## Gate

- `noop\noop_summary.txt` held `RESULT: PASS. All four grid smokes are identical under LIVE and the build copy.`
  No process had `treeroute smoke` in its command line. Seen before the first engine edit and again before this
  round of fixes.

## What changed, per V item

| Item | Change | Where |
|---|---|---|
| V1 | Neighbour kind only: every decline (nowcast and each lead) adopts `base__donor_median`. Every guard and decline check compares with that same median. Gated on the router kind read from the data (R12), never a package name. Grid kinds unchanged. | `layer/decide.py` (`DeclineBaseline`, keyword-only `baseline` / `decline_baseline`, default None); `pipeline/table_passes.py:59-64, :127`; `pipeline/table_ladder.py` `_guard` and `run_lead`; `pipeline/table_router.py` `fallback_median_rows`; `treeroute_report/table.py:178-181` |
| V1 (review fix) | The median's rows are now checked by mark, not only by date. A test-marked fallback donor row is refused (G-FITCUT). | `pipeline/table_router.py:193-202` |
| V1 (review fix) | The lead-guard safety check was a value compared with itself. It now recomputes the median from the pass's own fallback rows and checks their units, oldest and newest label days and cut against the guard bank's manifest. | `pipeline/table_ladder.py:336-353` |
| V2, V4, V8, V9, V10, V12 | No code. Disclosure text only. | `datasets\coral_draft\ingest\README.md:62-105` |
| V3 | Test window 2016-2019: the 38 visits of 2020 are not written. 2017-2020 is declared as a sensitivity row. Its steps are written down, not run. | `dataset.yaml:17-18`; `exceptions.yaml:116-121`; `ingest\README.md:78-81, :107-126` |
| V5 / V6 | split.yaml leaves out 57 groups: 11 the defaults refuse (V5: 4 with 0 train rows at a bank cut, 8 with one site, one is both) and 46 with no test row in the lead files (V6). 37 groups remain: 9,464 train and 2,312 test visits at lead 0. Verified against the data by `coral_tables\make_split.py --check` (PASS). | `split.yaml`; `exceptions.yaml:122-127`; `coral_tables\make_split.py` |
| V7 | Toy-only legacy replay harness, outside the engine. | `replay\run_replay.py`, `legacy_lines.py`, `toy.py`, `REPLAY_REPORT.md` |
| V11 | The r36 test asserts `r36_tolerance(1.0) == max(K.GUARD_TOLERANCE_K, r36_floor())`. | `engine\tests\test_route_kinds.py:175-178` |

Fixes from the two skeptic reviews (this round):

- README commands had broken paths. Backslash sequences had become TAB, form-feed and vertical-tab characters
  (lines 44, 105, 106, 108, 114). Fixed in the draft and in the tiny copy. A scan finds no control character left in
  any package, builder, replay or report file.
- "No test-window visit" now reads "no test row in the lead files". Gulf of Thailand has 10 test-window visits but
  none is written (no lead-0 SST history). Changed in make_split.py, split.yaml (rewritten, same groups),
  exceptions.yaml, README and AUDIT_CHECKLIST.
- make_split.py takes the package name from `--split` and the decision-surface years from the test years, so it
  writes correct text for the 2017-2020 row (`make_split.py:129-135, :193-199`).
- README now says (`ingest\README.md:70-75`): the nowcast baseline leaves the fold's group out; each lead's guard
  baseline uses all kept groups. And the locked lead file of a declined lead holds only `guard_passed` false and
  `adopted` null. The decline target is in `lead.json`.
- `dataset.yaml:6-8` now says `input: table` fails only under LIVE. Drop those lines at the install.
- V11 line cites corrected to `:175-178`. `SPEC_NEIGHBOUR.md` now names the donor-row median as the neighbour decline
  target and marks N18 as built. `BUILD_REPORT.md` item 7 points to the replay.
- Replay: new check P0 fails the run if K, MINOK, ALPHA or A_CTX differ from the engine. `grid_equal` is renamed
  `grid_parsed` (it only shows the legacy loop parsed the engine grid). The legacy default grid is copied verbatim
  (`adaptation.py:153-154`) and reported. REPLAY_REPORT lists the harness-written legacy steps under Limits.
- `run_noop_proof.ps1` no longer uses Tee-Object. Every summary and log line is written with
  `Add-Content -Encoding utf8` and shown with Write-Host.

Not changed, by choice: the lead lock gets no new key (`decide.py` is shared; the target is rebuilt from the
fingerprinted R12 kind). The parameter name `own_trees_off_mae_guard` stays; its docstring says it carries the median's
MAE for the neighbour kind.

## Tests (only the affected ones; the full suite is yours)

| Run | Result |
|---|---|
| `test_table_v1_decline.py` (14, one new: a test-marked fallback row is refused), `test_table_router_leads.py`, `test_nonames.py`, `test_noknob.py`, `test_table_mode_pipeline.py` | 76 passed, 2.4 min |
| Reviewer's adversarial tests, `review_tests_v\` (grid byte-identity of `decide.py`, fresh-interpreter grid imports load no table module, four toy runs with a leak probe) | 29 passed, 1.4 min |
| Earlier in ruling V (`CHECK_REPORT_V.md`): core table and layer files; grid users of `decide` (`test_vault*`, `test_pipeline_g1`, `test_pipeline`); `test_pipeline_ladder`; `test_route_kinds` | 285 passed + 1 old failure (ATTENTION 3); 80 passed; 28 passed; 33 passed |

Grid identity: this round edited only `table_router.py` and `table_ladder.py`. Grid runs never import them (the
reviewer's fresh-interpreter test, re-run above). Package, builder, replay and test files are outside the hash.

## Tiny coral smoke (plumbing only; tiny numbers carry no sign information)

Run `runs\coral_draft_tiny\smoke\20261019_9fa87a46` (23.6 s, exit 0, log `logs_check\tiny_smoke_fix.log`). Every
prediction, score, ladder and adoption file is byte-identical to the run before this round (`20261019_fdd63405`).
Only lock times and the fingerprint differ. 96 test rows at every lead. MAE on the test rows:

| Lead | Guard / decision | Adopted column | Adopted MAE | Donor median | Identity trees-off (old decline target) |
|---|---|---|---|---|---|
| 0 | arm adopted: `log_c_plain_gls` beat the fold medians (surface MAE 2.7419) | `arm__log_c_plain_gls` | 3.7788 | 3.8957 | 4.3419 |
| 183 | guard PASS: pinned 2.1427 < median 2.1967 (71 rows, 179 donor rows) | `arm__log_c_plain_gls` | 3.9040 | 3.8957 | 7.4413 |
| 365 | guard FAIL: pinned 2.1937 > median 2.1786 (60 rows, 168 donor rows) | `base__donor_median` | 3.8957 | 3.8957 | 7.1320 |

`verdict.json`: `decline_target: base__donor_median`. Lead 365 declined to the median. Before V1 it fell back to the
identity trees-off (7.13).

## Replay (V7)

`replay\out\20261019_232417`: **RESULT: PASS (P0-P5; P6 met)**, 22.3 s, exit 0. Log `logs_check\replay_fix.log`.

- P0: legacy K, MINOK, ALPHA, A_CTX equal the engine constants.
- P1: pools and drop sets differ on 0 of 87 rows (lead 0) and 0 of 83 (lead 365).
- P2: with the same pool and columns, the ported local fit equals the legacy fit: max difference 0, and 4.4e-13 in
  the 40-tree case (27 rows take the k-space dual). Bar 1e-9.
- P3: trees-off max difference 0 (14 and 17 rows with every tree dropped).
- P4: fallback at 11 candidates and a normal fit at 12: ok. P5: 7 copied legacy spans equal the legacy files.
- The strict pool changes the result: the legacy mask changes 80 pools at lead 0 and 79 at lead 365 (toy only).
- Row files and `differences.csv` are byte-identical to the runs at hashes `b0ddaf81...` and `a539fa71...`.

## Engine hash

Build `engine_code_sha256` now: **`704c8aea89d77ba3fa8192346152ff04756b7ef13dcc38a53292424e590076ed`**
(was `a539fa71...` after V1, `a4900984...` at the last full proof). LIVE stays `65a177bc...`.

## The owner's next commands (PowerShell, in order)

Close games and large programs. One heavy job at a time.

1. **Final checks (about 75-80 min).** From a fresh PowerShell window:
   ```powershell
   powershell -ExecutionPolicy Bypass -File D:\treeroute\coral_build\run_final_checks.ps1
   ```
   It moves `noop\` aside to `_moved\noop_<time>` (and an old `pt\full`, `fullsuite.xml`), runs
   `run_noop_proof.ps1` (four grid smokes, LIVE vs build, byte comparison; 30-35 min), then the full suite with
   `--junitxml D:\treeroute\coral_build\fullsuite.xml` (about 45 min). It ends with one line:
   `FINAL: proof RESULT: ... | suite: N passed, F failed, ...`. Logs: `final_checks_<time>.log`,
   `fullsuite_<time>.log`, `noop\noop_summary.txt`.
   - The proof must say `RESULT: PASS`. If not: stop, do not install.
   - Expected suite failures, all old: `test_layer_shapes` `matrix_dir` (1), `test_catalog_timing_facts.py` (3), the
     defo package tests (6). Seven launcher tests fail only in a subset order; in the full order they should pass.
     Any other failure is new: stop and report it.
2. **Answer ATTENTION 2 (V6) and 3 (`matrix_dir`).**
3. **Install into LIVE** (only after step 1 passes). Move aside to `LIVE\_moved_coral_<date>\`, by explicit name:
   the 13 changed engine files (`check\deep.py`, `check\quick.py`, `check\report.py`, `derive\router_rules.py`,
   `fit\context.py`, `fit\weights.py`, `layer\decide.py`, `package\load.py`, `package\schema.py`, `pipeline\run.py`,
   `route\__init__.py`, `route\kinds.py`, `route\solve.py`), `treeroute_report\table.py`, and
   `tests\test_layer_shapes.py`, `tests\test_route_kinds.py`. Then copy in, by explicit name (no recursive copy):
   those 16 files, the 9 new engine files (`check\table.py`, `derive\table.py`, `labels\rows.py`, `package\table.py`,
   `pipeline\table_ladder.py`, `pipeline\table_passes.py`, `pipeline\table_router.py`, `pipeline\table_run.py`,
   `route\neighbour.py`) and the 11 new test files (`table_toy.py`, `test_report_table_edges.py`,
   `test_route_neighbour_fit.py`, `test_route_neighbour_pool.py`, `test_table_mode_contract.py`,
   `test_table_mode_fold_gls.py`, `test_table_mode_pipeline.py`, `test_table_mode_solve.py`,
   `test_table_mode_vault_derive.py`, `test_table_router_leads.py`, `test_table_v1_decline.py`). Do not copy
   `tests\_pytest_tmp\`. Verify from LIVE: `engine_code_sha256()` prints `704c8aea...76ed`, and
   `py -3.9 -m pytest -q tests/test_nonames.py tests/test_noknob.py` passes.
4. **Full coral table build** (about 26-30 min build + 6 min check, about 1 GB RAM):
   ```powershell
   Set-Location D:\treeroute\coral_build\coral_tables
   py -3.9 -u build_tables.py --build full *>&1 | Tee-Object -FilePath D:\treeroute\coral_build\coral_data\full_build_console.log
   py -3.9 -u check_tables.py --build full *>&1 | Tee-Object -FilePath D:\treeroute\coral_build\coral_data\full_check_console.log
   py -3.9 -u make_split.py --lead-dir D:\treeroute\coral_build\coral_data\full --check
   py -3.9 -u build_tables.py --publish full
   ```
   If `make_split.py --check` fails (stage 2 dropped rows and a group changed list), run it again with `--write`
   instead of `--check` and re-read the counts. `--publish` prints the store line; it edits nothing.
5. **Coral package**: in `datasets\coral_draft\dataset.yaml` set `stores.target` to the printed line and drop the
   ATTENTION lines 6-8. Add `D:/treeroute/coral_build/coral_store` to `D:\treeroute\registry\protected_roots.txt`.
   Copy the package into `LIVE\datasets\`. Add its entry to `treeroute_report\continuity_groups.yaml`.
6. **Checks and a full-data smoke** from LIVE: `py -3.9 -m treeroute check <pkg>`, then with `--deep`, then
   `py -3.9 -m treeroute smoke <pkg>`. Read there: the no-tree share (V2) and the decline baseline (V1, in
   `lead.json` `guard.baseline_*` and `decision_checks.json`).
7. **Coral pre-registration Part**: ruling V (V1-V12), the V3 window and the declared 2017-2020 sensitivity row
   (steps in `ingest\README.md:107-126`), the V5/V6 counts, TABLE_DEPARTURES (V4), the U2 vouching statement, the new
   engine hash `704c8aea...`, and that the four grid headline runs keep their old hash (U5).
8. **Plan and freeze**: `py -3.9 -m treeroute plan <pkg>` (heavy, alone), then
   `py -3.9 -m treeroute_report.freeze <pkg> --prereg PREREGISTRATION_DRAFT_coral.md` and
   `py -3.9 -m treeroute_report.freeze verify`. You sign.
9. **Headline run**: `py -3.9 -m treeroute run <pkg>`, then `py -3.9 -m treeroute report`.

## Files written or changed in this round

- Engine (in the hash): `engine\treeroute\pipeline\table_router.py`, `engine\treeroute\pipeline\table_ladder.py`.
- Engine tests: `engine\tests\test_table_v1_decline.py` (one new test).
- Package: `engine\datasets\coral_draft\{split.yaml, exceptions.yaml, dataset.yaml, AUDIT_CHECKLIST.md,
  ingest\README.md}`; tiny copy refreshed in `coral_data\tiny\package\` (split.yaml unchanged).
- Builder side: `coral_tables\make_split.py`.
- Replay: `replay\run_replay.py`, `replay\legacy_lines.py`, `replay\REPLAY_REPORT.md`, `replay\README.md`, new run
  `replay\out\20261019_232417\`.
- Scripts: `run_final_checks.ps1` (new, not run), `run_noop_proof.ps1` (UTF-8 fix, not run).
- Docs: `SPEC_NEIGHBOUR.md`, `BUILD_REPORT.md` (item 7), `BUILD_NOTES_V_package.md` (line cite), this report.
- Old copies: `_moved\v_fix_review\`, `_moved\v_split_20261019_232206\`.
- New run and test folders: `runs\coral_draft_tiny\smoke\20261019_9fa87a46\`, `_pytest_fix\`.
