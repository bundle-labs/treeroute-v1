# Z_CHECK_REPORT: full test suite and coral dry pass after the Z1 + Z2 builds

Written 2026-10-21. All writes are under `D:\treeroute\rivals_build`. Nothing was deleted. The LIVE engine was only
read. No rival test score was made or read, no test label was opened, and the pm25 headline was not re-run or
retrained.

## Result

- **Tests: all 141 pass (138 + 3 real-data), 0 failed.**
- **Coral dry pass: the picks did not change.** Picks content is `3b5a33f101f02a78...`, the same as before Z2 and
  the same as the check value in RIVALS_OWNER_COMMANDS.md section 2. The RF pick is the same setting. Only its inner
  MAE moved a little (6.6835 -> 6.6897).
- **Other learners are unchanged:** all 43 of their trial prediction files are byte-equal to the pre-Z2 pass.
- **Harness code hash:** `a595a9b182482765f5a469a54bdac1c9b87079791e2abf6dab3ce6fb7f07e1f5`. It is the same before
  and after the runs. The `rivals\*.py` files were not changed during the check.

## 1. Test suite

Run from `D:\treeroute\rivals_build`, with `--basetemp` under `pt\z` (parent created first).

| run | command | result | log |
|---|---|---|---|
| full1 | `py -3.9 -B -m pytest rivals/tests --basetemp pt\z\full1 -rA --durations=30` | **138 passed, 3 skipped**, 760 s | `pt\z\full1.log` |
| real1 | `RIVALS_REAL=1`, `pytest rivals/tests/test_realdata.py --basetemp pt\z\real1` | **3 passed**, 531 s | `pt\z\real1.log` |

- **Why there are two runs:** in full1 the 3 skipped tests are the real-data tests. I set the variable with cmd's
  `set RIVALS_REAL=1 && ...`, which leaves a trailing space in the value. conftest.py:53 needs exactly `"1"`, so the
  tests skipped. real1 sets the variable correctly and runs those 3 tests alone, as in INTEGRATE_REPORT.md:48. Every
  test passed in one of the two runs.
- **Real-data timings:**
  - Defo smoke export parity: 63 s.
  - Fire smoke export parity: 155 s.
  - Coral dry pass: 311 s.
- **Warnings:** only library deprecation warnings (pandas concat, pyparsing via matplotlib). There are no test
  warnings.
- **Moved aside by the real-data tests** (C-A2 / move_aside, not deleted):
  - The earlier smoke exports, under `_moved\20261021T024409_753695Z\defo`, `_moved\20261021T024511_785766Z\fire` and
    `_moved\20261021T024746_331240Z\coral`.
  - The pre-Z2 dry board, under `_moved\20261021T024741920835\20261020_f3b8e3da`, by test_realdata.py:113.

## 2. Coral tune-only dry pass (stopped at the lock)

This is the re-run inside real1 (test_realdata.py:103). The new board is `_dryrun\coral\20261020_f3b8e3da`.

- It stopped at the lock: the picks are locked, with picks.json sha `d73d14b0...` and content `3b5a33f1...`.
- **Nothing beyond the lock was made or read:**
  - The export has no `test/` folder.
  - The board has no `scores/` folder.
  - The read spy saw no test-file read and no test `y` request.
- There were 55 fits. Trials per learner: ridge 3, rf 12, lgbm 12, lgbm_tweedie 10, hgb_l1 18.
- Peak working set was 1.35 GiB.

Three boards were compared (script: scratchpad `cmp_dry.py`, read-only):
- **old:** the pre-Z2 pass (harness c298611e).
- **z2:** the Z2 builder's pass (`_dryrun_z2`, a595a9b1).
- **new:** this check's pass (a595a9b1).

### Picks (old -> new)

| learner | pick (same in old, z2 and new) | checkpoint | inner MAE old -> new |
|---|---|---|---|
| ridge | log_c, alpha 1.0 | 1.0 | 6.349655 -> 6.349655 |
| lgbm | arcsine, num_leaves 31, min_child 200 | 200 | 6.438774 -> 6.438774 |
| lgbm_tweedie | own_log, leaves 127, min_child 200, power 1.2 | 400 | 6.564923 -> 6.564923 |
| hgb_l1 | arcsine, max_leaf_nodes 127, min leaf 20 | 400 | 6.354853 -> 6.354853 |
| **rf** | **arcsine, max_features 0.5, min leaf 50** | 300 | **6.683543 -> 6.689709** |

- **Why the picks hash did not change although the RF MAE did:** picks content hashes only trial_id, extended,
  link, setting and checkpoint, not the MAE (`harness.py:1300`).

### Byte checks on the trial prediction files

| learner | old vs new | z2 vs new |
|---|---|---|
| ridge | 3/3 byte-equal | 3/3 |
| lgbm | 12/12 byte-equal | 12/12 |
| lgbm_tweedie | 10/10 byte-equal | 10/10 |
| hgb_l1 | 18/18 byte-equal | 18/18 |
| rf | 0/12 (expected: new method) | **12/12 byte-equal** (RF is deterministic across two runs) |

### RF trials, old vs new (inner MAE, rank among the 12, seconds)

| setting | old MAE (rank) | new MAE (rank) | sec old -> new |
|---|---|---|---|
| arcsine mf0.5 leaf50 | 6.6835 (1) | 6.6897 (1) | 0.6 -> 7.0 |
| arcsine mf0.2 leaf50 | 6.8783 (2) | 6.7882 (2) | 0.4 -> 5.2 |
| arcsine mf0.2 leaf5 | 7.0290 (3) | 6.9471 (3) | 0.6 -> 7.7 |
| arcsine mf0.5 leaf5 | 7.1199 (4) | 7.1250 (4) | 1.4 -> 11.1 |
| log_c mf0.5 leaf5 | 7.5593 (5) | 7.5239 (5) | 1.3 -> 10.7 |
| identity mf0.5 leaf50 | 7.6637 (6) | 7.6186 (6) | 0.6 -> 6.7 |
| identity mf0.2 leaf50 | 7.6689 (7) | 7.7076 (8) | 0.4 -> 5.1 |
| log_c mf0.2 leaf5 | 7.6962 (8) | 7.7198 (9) | 0.6 -> 6.7 |
| log_c mf0.5 leaf50 | 7.7700 (9) | 7.6997 (7) | 0.5 -> 6.4 |
| log_c mf0.2 leaf50 | 7.8716 (10) | 7.8538 (10) | 0.3 -> 4.7 |
| identity mf0.2 leaf5 | 8.0896 (11) | 8.0223 (11) | 0.7 -> 7.4 |
| identity mf0.5 leaf5 | 8.2161 (12) | 8.2343 (12) | 1.6 -> 11.7 |

- **Why the RF numbers moved on coral:** on coral the old stride was already 1 (old trials.csv `rf_stride` = 1; old
  board.json `rf_stride.stride` 1). The old RF also used all 9,292 fit rows (`max_samples` 1.0). So the small changes
  come only from the new way each tree draws its sample (its own seeded draw, with replacement), not from more rows.
  - Three middle ranks swapped: 7, 8 and 9.
  - The top 6 ranks are the same.
- **RF fit details (new):** 1 batch, 9,292 rows per tree, 300 trees, read 0.002 GiB, fit 4.0 s.

### Tuning time per learner (seconds, summed from rivals.log)

| learner | old | z2 | new |
|---|---|---|---|
| ridge | 0.3 | 0.6 | 0.4 |
| lgbm | 24.9 | 24.8 | 23.5 |
| lgbm_tweedie | 22.1 | 21.6 | 21.1 |
| hgb_l1 | 124.4 | 121.0 | 120.5 |
| **rf** | **9.5** | 95.4 | **91.5** |
| tune total | 187.2 | 272.4 | 264.1 |

RF tuning is about 10x slower on coral (9.5 s -> 91.5 s). This matches the build report's one-tree-per-call cost
(ATTENTION 1 there). The other learners' times are unchanged within noise.

## 3. Notes

- **Cosmetic:** the board's export code hash differs from the build report's quick label. A plain sha256 of
  `rivals\export.py` is `379ca9d1...`, while the Z1 report quotes "export 8776baf2". That is probably a different
  hash (the export's own code hash over its files). I did not check it further. It is not a failure: the export
  tests and the real-data parity checks all pass.
- **Doc updates the Z2 builder listed (not done here, not my task):**
  - SPEC_RIVALS.md lines 344-346, 391 and 476.
  - PREREGISTRATION_DRAFT_rivals_common.md lines 163, 191 and 220-221. Z4 needs hash a595a9b1.
  - INTEGRATE_REPORT.md lines 151-152.
  - RIVALS_BUILD_REPORT.md lines 21 and 71.
- **The RAM check refers to the machine, not to a test:** about 5.1-5.8 GiB was free during the runs. The fire
  real-data test needs more than 5 GiB available, and it ran.
