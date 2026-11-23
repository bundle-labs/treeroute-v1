# BUILD NOTES: ruling V1 in the engine (key v1_engine)

Written 2026-10-19. Ruling: `OWNER_RULINGS_2026-10-06.md:103` (V1). Plan: `PLAN_RULING_V.md` section 1.

## Gate

- The no-op proof had ended before any engine edit. `noop\noop_summary.txt` (22:10) said:
  `RESULT: PASS. All four grid smokes are identical under LIVE and the build copy.`
- No process had "treeroute smoke" in its command line (checked 22:13).
- **The owner must run `run_noop_proof.ps1` again.** `layer/decide.py` is a shared module and it changed.

## What changed

Old copies: `_moved\v_v1_engine\` (same relative paths). Nothing deleted.

| File | Change |
|---|---|
| `treeroute/layer/decide.py` | New `DeclineBaseline` (:686). `select_adoption(..., baseline=None)` (:384-386, :414, :459-468, :488-489). `_baseline_pair` (:367). `decide(..., decline_baseline=None)` (:957, :988-1001, :1032-1050, :1076). `DecisionRecord.decline_baseline` (:785, last field, default None). `decision_lines` (:1083, :1108-1122). `decision_section` (:1158, :1178-1182). `__all__`. Docstrings. |
| `treeroute/pipeline/table_router.py` | `NeighbourPass.fallback_median_rows()` (:325-339): each scored row's part median. |
| `treeroute/pipeline/table_passes.py` | `V1_RULE`, `V1_DECLINED_ADOPTED` (:59-64). `decline_to_donor_median()` (:127), gated on `self.kind` (R12). `decision` passes the baseline (:334-337) and writes it in decision_checks.json (:355-358). `report`: a declined nowcast adopts `base__donor_median` (:553-561); own trees-off beside (:589-591); verdict.json gains `adopted_column`, `decline_target`, `decline_rule` (:622, :628). |
| `treeroute/pipeline/table_ladder.py` | `_decline_links` renamed `_beside_links` (:143). `_guard` compares with the guard pass's fallback median and refuses (G-PLUMB) if it is not `baseline_donor_median(donor_g)` (:332-358); saves `base__donor_median` in guard_preds.parquet; lead.json guard gains `baseline_*`. `run_lead`: a failed guard adopts `base__donor_median` (:510-527). `table`: lead 0 reads `verdict["adopted_column"]` (:584). Docstrings. |
| `treeroute_report/table.py` | :178-181: `verdict.get("adopted_column") or arm__<adopted>`. Grid verdicts have no such key, so the old expression runs. |
| `treeroute/route/neighbour.py` | Docstring only (:959-962). |
| `tests/test_table_v1_decline.py` | New, 13 tests. |

## Why grid outputs do not move

- Grid runs never import `table_passes`, `table_ladder` or `table_router` (BUILD_REPORT.md:44-45).
- The grid callers of `decide` (`pipeline/passes.py:772`, `pipeline/ladder.py:825`) pass no new keyword. With
  `decline_baseline=None`, every statement runs as before, in the same order. `DecisionRecord.decline_baseline` is
  None. `decision_section` adds no key. The candidate table and the printed lines are the same.
- A test proves it: `test_without_a_baseline_the_grid_decision_is_byte_identical` (adopt and decline cases).
  Another scans `passes.py` and `ladder.py`: they never name the V1 objects.
- `treeroute_report/table.py`: `.get` returns None on a grid verdict.

## Deviations from the plan

1. **No year in strings.** `tests/test_nonames.py` refuses a 4-digit year in engine text. So `V1_RULE` and the
   docstrings say "the owner rulings file, section V". The file name and line (`:103`) stay in comments
   (`table_passes.py:59`, `table_ladder.py:39`, `decide.py:60`).
2. Refusals use the rule id `V1` (plan said R27 for some). V1 is the rule that adds them.
3. decision_checks.json `decline_baseline` also holds `mae` (beside the plan's key, rule, per-fold medians).
4. `_guard` also refuses when the guard pass has more than one part (it always has one).
5. A declined lead's `own_trees_off_column` is the pinned link's trees-off (plan). For a grid-style fallback
   (not reachable: a table run is always the neighbour kind) the old identity column is kept.
6. Plan test 7 "a grid-kind ladder still behaves as before": a table run refuses any kind but neighbour
   (`table_passes.py:88-89`), so a table ladder cannot run a grid kind. The evidence is: `test_pipeline_ladder.py`
   (grid ladder) passes unchanged, `test_layer_decide.py` passes unchanged, plus the byte-identity test and the
   source scan above.
7. The report-table test checks `Run.info` (adopted column = `base__donor_median` at every lead). The rendered
   markdown does not print column names, so it is not searched for one.
8. Open choices: defaults taken (per-fold medians on the surface; `"adopted": "donor_median"` plus
   `"adopted_column"`).

## Tests run (only these)

- `test_table_v1_decline.py`: 13 passed (47 s).
- `test_layer_decide.py`, `test_table_mode_pipeline.py`, `test_table_mode_contract.py`, `test_table_mode_fold_gls.py`,
  `test_table_router_leads.py`, `test_report_table.py`, `test_report_table_edges.py`, `test_nonames.py`,
  `test_noknob.py`: 160 passed after the year fix (first run: 159 passed, 1 failed on the year text, fixed).
- `test_pipeline_ladder.py` (grid ladder): 28 passed (9 min).
- `--basetemp` was set to `D:\treeroute\coral_build\_pytest_v1\...`, so other agents' pytest folders were not touched.

## Tiny smoke (23 s)

Run folder: `D:\treeroute\coral_build\runs\coral_draft_tiny\smoke\20261019_fdd63405`
(log: `D:\treeroute\coral_build\logs_v1\tiny_smoke_v1.log`).

| Pass | Baseline MAE (guard / surface) | Pinned MAE | Old rule | Now | Scored MAE |
|---|---|---|---|---|---|
| Nowcast | 2.7419 (surface) | | adopted | adopted `log_c_plain_gls` | 3.7788 vs 3.8957 |
| Lead 183 | 2.1967 | 2.1427 | FAIL (trees-off 2.1421) | PASS | 3.9040 |
| Lead 365 | 2.1786 | 2.1937 | FAIL (trees-off 2.1840) | FAIL: adopts `base__donor_median` | **3.8957** (was 7.4 as identity trees-off) |

The tiny donor-row median is 0 at lead 365 (many zero labels).

## Hash

Build `engine_code_sha256` after my edits: `a539fa71a2b43846deaa6a213e060084918b19db53faf4dc057e4dbc3d794aa8`
(was `a4900984...0e5e`). Other V agents may move it again.

## Open items

- Owner: re-run `run_noop_proof.ps1` (must end `RESULT: PASS`), then the one full suite.
- SPEC_NEIGHBOUR.md:278 still names the identity trees-off as the decline target. I did not own the specs.
- The toy table run now declines at the nowcast (every arm loses to the donor-row median). Old toy tests still pass.
