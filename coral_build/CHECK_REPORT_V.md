# CHECK REPORT: ruling V builds (v1-engine, package, v7-replay)

Written 2026-10-19 by the check agent. Everything written is under `D:\treeroute\coral_build`. LIVE was only read.
Ruling: `OWNER_RULINGS_2026-10-06.md` section V (V1-V12).

## ATTENTION (read first)

1. **`layer/decide.py` changed, and grid runs DO load it.** It is in the module list of every grid smoke (defo manifest,
   74 modules). The edit is gated: grid callers pass no `decline_baseline`, so the old code runs. I re-ran the defo grid
   smoke on the new build. It is byte-identical to the LIVE defo smoke (section 4). **The owner still needs to run
   `run_noop_proof.ps1` for all four grids**, because the last full proof was at hash `a4900984...`.
2. **One test fails, and it is old.** `tests/test_layer_shapes.py::test_functions_take_the_approved_parameters` fails on
   `weight_model_for_cut`'s `matrix_dir` parameter (`treeroute/fit/weights.py:526`). LIVE has the same function and the
   same test (diff: identical), so LIVE fails it too. It is not caused by the V builds. I did not fix it. Approving
   `matrix_dir` is a signature decision for the owner.
3. **On the tiny data the donor-row median is 0 everywhere.** So "decline to the donor median" and "predict zero" give
   the same numbers there (3.8957). The tiny smoke cannot tell the two apart. The V1 tests (`test_table_v1_decline.py`)
   cover the logic.
4. **V2: almost no trees are left on the guard rows.** The pool tree drop leaves no tree on 69 of 71 guard rows at
   lead 183 and 44 of 60 at lead 365. Each lead guard is mostly a trees-off test. Tiny numbers only.
5. **Package open item (from the package build):** V6 takes 46 train-only groups (1,874 visits) out of the banks and
   out of every neighbour pool, not just out of the scored lists. Confirm that this is what V6 meant.

## Gate

- `noop\noop_summary.txt` (written 22:10:03) line 73: `RESULT: PASS. All four grid smokes are identical under LIVE and
  the build copy.` No process had `treeroute smoke` in its command line. I checked again just before my one edit.
- That proof was at build hash `a49009845eb7...`. It does not cover the V1 edits.

## 1. Tests

All runs used `--basetemp` under `D:\treeroute\coral_build\_pytest_check\`.

| Run | Files | Result |
|---|---|---|
| core | `test_table_mode_{contract,fold_gls,pipeline,solve,vault_derive}`, `test_route_neighbour_{fit,pool}`, `test_route_kinds` (the r36 file), `test_nonames`, `test_noknob`, `test_layer_decide`, `test_layer_shapes`, `test_report_table`, `test_report_table_edges`, `test_table_router_leads`, `test_table_v1_decline` | 285 passed, 1 failed (old, ATTENTION 2), 3 min |
| grid users of decide | `test_vault`, `test_vault_lock`, `test_vault_world`, `test_pipeline_g1`, `test_pipeline` | 80 passed, 8.7 min |
| (V1 agent, after its last edit at 22:28) | `test_pipeline_ladder` | 28 passed (its notes; pytest folder `_pytest_v1\k`, 22:28-22:37) |

My first core run showed 77 errors. They came from my own setup: the `--basetemp` parent folder did not exist. Not a
code fault.

**One integration fix.** `tests/test_layer_shapes.py:53-56`. V1 added the keyword `baseline` to `select_adoption`
(`treeroute/layer/decide.py:386`). The shape test only allows approved additions, so it failed on `baseline`. I added
`baseline` to the `ADDED` list, with a comment that cites V1 and `decide.py:386, :401-405`. The parameter is keyword-only,
so `test_every_addition_is_keyword_only` covers it. Old copy: `_moved\v_check\engine_tests\test_layer_shapes.py`.
It is a test file, so the engine hash does not move.

## 2. Tiny coral smoke

The same command into `--run-root D:\treeroute\coral_build\runs` is refused (G-NOOVERWRITE). The V1 agent's run
`runs\coral_draft_tiny\smoke\20261019_fdd63405` already has this fingerprint (same code and package). So I re-ran into a
fresh root: `runs_check\coral_draft_tiny\smoke\20261019_fdd63405` (25 s, exit 0, log `logs_check\tiny_smoke_check.log`).
Every prediction file, adoption file, `ladder_table.csv`, `score_pooled.csv`, `derived.json` and the pools file is
byte-identical to the first run. `verdict.json` differs only in `timings_seconds`.

Test rows: 96 at every lead. MAE on the test rows:

| Lead | Guard / decision | Adopted column | Model | Its own trees-off | Donor median | Predict-zero | Identity trees-off |
|---|---|---|---|---|---|---|---|
| 0 | adopted `log_c_plain_gls` (8 of 12 arms beat the median 2.7419 on the surface) | `arm__log_c_plain_gls` | 3.7788 | 3.8373 | 3.8957 | 3.8957 | 4.3419 |
| 183 | guard PASS: pinned 2.1427 < median 2.1967 (71 rows) | `arm__log_c_plain_gls` | 3.9040 | 3.8903 | 3.8957 | 3.8957 | 7.4413 |
| 365 | guard FAIL: pinned 2.1937 > median 2.1786 (60 rows) | `base__donor_median` | 3.8957 (pinned arm would be 4.5571) | 3.9332 | 3.8957 | 3.8957 | 7.1320 |

- **Decline target.** Lead 365 declined. It adopted `base__donor_median` (`ladder/lead_365/lead.json`
  `test.adopted_column`; `ladder_table.csv` adopted row). `verdict.json` has `decline_target: base__donor_median`.
  Before V1 it scored 7.13 with the identity trees-off.
- **Guard baseline.** Both lead guards compared with `base__donor_median` (`guard.baseline_column`), value 0, from 179
  and 168 guard-bank donor rows.
- **Rows with no tree left** (adopted or pinned arm): lead 0 test 4 of 96 (4%). Lead 183 test 0 of 96, guard 69 of 71
  (97%). Lead 365 test 0 of 96, guard 44 of 60 (73%).
- **Pool fallbacks** (under 12 candidates): 0 at every lead and every pass.
- Lead 183's model (3.9040) is a little worse than the donor median (3.8957) on the test rows, though it beat the median
  on the guard rows. Tiny numbers; they say nothing about coral.

## 3. Replay harness (V7)

`py -3.9 replay\run_replay.py` at hash `a539fa71...`: **RESULT: PASS** (P1-P5 pass; P6 met), 23 s, exit 0.
Run folder `replay\out\20261019_224949`, log `logs_check\replay_check.log`.

- P1: pools and drop sets differ on 0 of 87 rows (lead 0) and 0 of 83 (lead 365).
- P2: local fit max difference 0, and 4.4e-13 in the 200-tree case (27 dual-regime rows).
- P3: trees-off max difference 0 (14 and 17 rows with every tree dropped).
- P4: fallback at 11 candidates and normal fit at 12: ok.
- Its row files and `differences.csv` are byte-identical to the earlier run `replay\out\20261019_222733`.

## 4. Engine hash and grid imports

New `engine_code_sha256` of `D:\treeroute\coral_build\engine`:
**`a539fa71a2b43846deaa6a213e060084918b19db53faf4dc057e4dbc3d794aa8`**.

Proof the list below is complete for the hash: I copied `treeroute\`, put back the five old files from
`_moved\v_v1_engine\`, and the hash became `a49009845eb7...0e5e` again.

Files changed since `a4900984...`:

| File | In the hash | Loaded by a grid smoke |
|---|---|---|
| `treeroute/layer/decide.py` | yes | **YES** (shared; gated, see below) |
| `treeroute/pipeline/table_ladder.py` | yes | no |
| `treeroute/pipeline/table_passes.py` | yes | no |
| `treeroute/pipeline/table_router.py` | yes | no |
| `treeroute/route/neighbour.py` (docstring only, :960-962) | yes | no |
| `treeroute_report/table.py` (:178-181) | no | no (report tool; loaded only when a report is rendered) |
| `tests/test_route_kinds.py` (V11, :175-178), `tests/test_table_v1_decline.py` (new), `tests/test_layer_shapes.py` (my fix) | no | no |
| `datasets/coral_draft/{split,exceptions,dataset}.yaml`, `ingest/README.md`, `AUDIT_CHECKLIST.md` | no | no (coral package) |

How I checked the imports:

- Defo grid smoke on the new build: `check_v\defo_new\defo\smoke\20261019_bf152a31` (1.4 min, exit 0, log
  `logs_check\defo_smoke_check.log`). Its `manifest.json` `loaded_engine_modules` (74) equals the LIVE defo smoke's list
  (`noop\old\defo\smoke\20261019_0e998372`).
- `py -3.9 -c` imported those 74 modules. Afterwards `sys.modules` held exactly 74 treeroute modules. `layer.decide` is
  loaded. `table_ladder`, `table_passes`, `table_router`, `route.neighbour` (and `package.table`, `table_run`,
  `derive.table`, `check.table`, `labels.rows`) are not. No `treeroute_report` module was loaded.
- `tools\compare_runs.py` LIVE defo vs new defo: 22 prediction and score files and `derived.json` byte-identical,
  24 other JSON records identical, 0 must-match files differ (log `logs_check\defo_compare.log`).

Why `decide.py` is a no-op for grids: the grid nowcast calls `LD.decide(...)` with no `decline_baseline`
(`pipeline/passes.py:772`). With None, `decide` skips the V1 block (`decide.py:988`) and `select_adoption` takes the old
branch (`decide.py:459`). The grid ladder calls `LD.forecast_adoption` (`pipeline/ladder.py:825`); that function got a
docstring change only (`decide.py:577-579`). The defo byte match above agrees. Only defo was re-run; pm25, fire and ndvi wait for the owner's proof.

Why `treeroute_report/table.py` is a no-op for grids: it reads `verdict.get("adopted_column")` first. The new defo
`verdict.json` has no such key (checked), so the old expression runs.

## 5. Package side (V3, V5, V6)

- `coral_tables\make_split.py --check`: PASS. Test years 2016-2019. V5: 11 groups (35 test, 9 train visits). V6: 46
  groups (1,874 train visits, 0 test). Kept: 37 groups, 9,464 train and 2,312 test visits.
- The tiny package's split.yaml stays `excluded: {}` (all 4 tiny groups have test rows).

## 6. Other writes and notes

- The engine writes a GLS temp matrix under `D:\treeroute\tmp\` during a smoke and removes it. That folder is empty now.
  It is the engine's default and is outside `coral_build`; earlier smokes did the same.
- New folders from this check: `runs_check\`, `check_v\defo_new\`, `logs_check\`, `_pytest_check\`,
  `replay\out\20261019_224949\`, `_moved\v_check\`. Nothing deleted.
- Stale docs I did not edit (not mine): `SPEC_NEIGHBOUR.md:278` still names the identity trees-off as the decline
  target. `SPEC_NEIGHBOUR.md:425` and `BUILD_REPORT.md:104` still say N18 is not built (see `replay\REPLAY_REPORT.md`).
- `dataset.yaml:6-8` of the coral draft still says `input: table` does not load. True for LIVE only.

## Owner steps

1. Run `run_noop_proof.ps1` (move `noop\old` and `noop\new` aside first). It must end `RESULT: PASS`.
2. Decide on `matrix_dir` in `test_layer_shapes.py` (old failure, also in LIVE).
3. Confirm the V6 reading (ATTENTION 5).
4. Run the one full suite.
