# INTEGRATE_REPORT: the lean common-rival board, three builds joined

Written 2026-10-20. All writes under `D:\treeroute\rivals_build`. No LIVE engine, package or run file was changed
(checked: no file in the engine folder or under `D:/treeroute/runs` is newer than SPEC_RIVALS.md; `D:/treeroute/tmp`
is empty). No rival test score exists. No test label was read by any rival step.

## Summary

- **Tests:** the full suite passes: 83 passed, 3 skipped (the real-data tests, which are opt-in) (`pt\integ\t05.log`).
  The three real-data tests also pass with `RIVALS_REAL=1` (`pt\integ\real01.log`).
  Three integration defects were found, all in test or config files. All three are fixed.
- **Parity proof (fire, R21 smoke groups):** I made a LIVE-engine smoke run under `rivals_build\runs`. It is
  byte-identical to the recorded no-op smoke. I exported it at leads 0, 6 and 12.
  - Every identity check (I1-I9) and every parity check (P1-P14) passes.
  - An independent re-check from the run's own files also passes: row keys, counts, columns, y on the score rows,
    test keys and normals.
  - The export took 137 s at a peak of 1.53 GiB.
- **Coral dry pass:** export, then tune of all 5 rivals (47 trials), then lock. It STOPPED at the lock: no `test/`
  folder, no scores, no test-label record.
  - Tuning took 136 s. Per rival: hgb_l1 76 s, lgbm 24 s, lgbm_tweedie 16 s, rf 9 s, ridge 0.5 s.
  - No extension was triggered, and no pick is flagged.
  - I ran it twice and also compared with builder B's earlier pass. All three give byte-equal picks, and all 47
    trial prediction files are byte-equal. The picks are labelled DRY.
- **Time plan (lean board, re-estimated):**
  - Fitting: about 12-24 h, plus about 14-26 h of export. That is about 26-50 h of machine time, over about 5-8
    overnight sessions. The plan said 53-98 h.
  - Worst case: every boosting pick lands on the 800 edge. That adds up to about 29 h (upper).
- **ATTENTION, pm25 is blocked:** its export refuses at I4 (and would refuse at I5). The owner must choose:
  re-run pm25 under LIVE, or rule that the differences are acceptable. See section 5.

## 1. What was joined

| build | files | state |
|---|---|---|
| A, export | `rivals\export.py`, `rivals\layout.py`, `engine_lineage.json` | Works as built. |
| B, harness | `rivals\harness.py`, `rivals\models.py`, `rivals\cli.py`, `rivals\__init__.py`, `rivals.yaml` | Works as built. The CLI dispatches `export` before numpy loads (B-A1 is met). |
| C, tests | `rivals\tests\*`, `pytest.ini`, `_machine\*` | Two test fixes and one config fix (section 2). |

No code under `rivals\*.py` was edited. So the harness code sha is unchanged: 3d655ea4 (picks.json).

## 2. Step 1: tests and the fixes

| run | result |
|---|---|
| t01 (stops at the first failure) | T3 failed (`test_leak_lock.py:79`). |
| t03, full suite | 82 passed, 1 failed (T3), 3 skipped. |
| t04: resume + T3 + T13 after fix 1 | 5 passed. |
| real01: `RIVALS_REAL=1 test_realdata.py` | 3 passed (defo smoke, fire smoke, coral dry pass). Coral peak working set 2.38 GiB. |
| **t05, final full suite** | **83 passed, 3 skipped (real-data, opt-in), 0 failed**, 521 s. |

Fixes:

1. **T3 failure (also the cause of builder B's T12 note C2).**
   - **Cause:** `test_export_resume_skips_finished_files_and_is_byte_equal` re-exported the SHARED toy table export
     with `--resume`. A resume rewrites `export_manifest.json` (new timings), so its sha changes. The harness boards
     of flows A and B were initialised on that export, so every later board command refuses, as designed
     (`harness.py:698`, "the lead-0 export manifest changed since init").
   - **Fix:** the resume test now uses its own export root (`tests\test_export_parity.py:162-177`). The harness was
     right; the test was wrong.
2. **C-A2:** the real-data tests exported into the shared `_export` without resume, so a second run refused with
   RESUME. They now pass `resume=True` (`tests\test_realdata.py:72, :95, :115`). A resume rebuilds the files and
   refuses on any byte change (D10), so it is the stronger check.
3. **New defect: I4 refused every older-engine grid run under the `_machine` configs.**
   - **Cause:** `layout.lineage_file` (`layout.py:106-114`) looks for `engine_lineage.json` next to the config
     file. `_machine\` has none. So `check_engine` refused ndvi, fire and defo ("no lineage file exists at
     ...\_machine\engine_lineage.json").
   - **Fix:** `engine_lineage: 'D:/treeroute/rivals_build/engine_lineage.json'` was added to
     `_machine\rivals_smoke.yaml`, `_machine\rivals_dryrun.yaml` and `pt\integ\integ_smoke.yaml`.
   - **Re-checked:** ndvi, fire and defo pass I4 with 2 hops; pm25 still refuses; coral is LIVE.
   - **For production:** the owner's production rivals.yaml must name `engine_lineage` too, or sit beside the
     lineage file.

## 3. Step 2: the smoke-size parity proof (fire, per-unit kind with context)

- **Engine smoke:**
  - Command: `py -3.9 -B pt\integ\smoke_run.py <engine>\datasets\fire`.
  - It is the CLI `smoke` entry (`treeroute/cli.py:197-205`) with the test machine, so the temp folder and the
    heavy-job lock stay under rivals_build. It pins threads first and writes no .pyc.
  - Result: `runs\fire\smoke\20261020_ee5cd20a`, 197 s, engine stripped hash 85c64b55 (LIVE).
  - Its 24 prediction and score files and its derived.json are byte-identical to the recorded no-op smoke
    `coral_build_v6b\noop\new\fire\smoke\20261020_ee5cd20a`.
- **Export:** `py -3.9 -B -m rivals.cli export --run <smoke> --package <fire> --lead all --config pt\integ\integ_smoke.yaml --resume`.
  - Output: `pt\integ\_export_smoke\fire\20261020_ee5cd20a\lead_{0,6,12}`.
  - 137 s in all: read 37.5 s, derive 53.0 s, rows about 8.7 s per lead, files about 5 s per lead. Peak 1.53 GiB.
  - The groups are the 4 R21 smoke groups: alaska_interior_taiga, amazon_basin_brazil, angola_zambia_fire_belt,
    australian_bushfire_belt (160 units).
- **Independent proof:** `pt\integ\parity_proof.py`; result in `pt\integ\parity_fire_smoke.json`. It reads only the
  run's own saved files, and test_preds only through its key and normal columns.

| lead | refit | tune / guard-fit | inner / guard | test | columns x / c / h / links | guard-cut identity normal vs saved trees-off (max gap; R36 tolerance 9e-7) | I1-I9, P1-P14 | independent |
|---|---|---|---|---|---|---|---|---|
| 0 | 30,413 | 24,680 | 5,573 | 7,680 | 131 / 2 / 6 / 3 | 6.1e-7 | all pass | pass |
| 6 | 29,613 | 23,881 | 4,773 | 7,680 | 131 / 2 / 6 / 3 | 6.6e-7 | all pass | pass |
| 12 | 28,670 | 22,926 | 3,830 | 7,680 | 131 / 2 / 6 / 3 | 6.6e-7 | all pass | pass |

What the independent proof checks:

- **Row keys:** the row-key hashes and counts of refit, tune and guard-fit rows equal fitctx_log (bank,
  bank_inner, bank_guard). So do their max label times.
- **Score rows:** the inner and guard rows and their y equal inner_preds and guard_preds, byte for byte.
- **Test rows:** the test keys equal the saved test_preds as a set, with no duplicate.
- **Normals:** the identity fit-cut normal on the test rows equals the saved `normal`, byte for byte.
- **Columns:** x columns equal `manifest.feature_list`; c columns equal plan.json `context`; h columns equal plan.json
  `history_columns`.
- **guardside:** its rows are the train subset, in the same order.
- **Groups:** the group sets equal the manifest's.
- **The normal gaps:** the guard-cut normal is within the engine's own rounding tolerance (decision_checks.json
  R36: floor 9e-7). About 40% of the rows differ at the 1e-7 level. That is float rounding in the saved trees-off,
  not a different normal.

## 4. Step 3: the coral TUNE-ONLY dry pass (real headline run 20261020_f3b8e3da)

Commands (config `_machine\rivals_dryrun.yaml`); logs in `pt\integ\dry_*.log`:

| step | wall time | result |
|---|---|---|
| `export --lead 0 --roles tune,inner --resume` | 42 s | 167 files. No `test/` folder. P1-P14 pass; P6 and P9 are "skipped: dry pass". Tune 9,292 rows, inner 2,046. Zero share of refit y 0.402, legal [0, 100], links identity / log_c / arcsine. |
| `init --extra-learners hgb_l1` | 5 s | 5 learners, 47 trials. Our layer had 424 inner candidates. Threads 8. |
| `tune --resume` | 138 s (tuning 135.9 s) | All 47 trials saved. No extension. |
| `lock` | 7 s | picks.json and its lock file written. Then STOP. |

Per-rival tuning time (from `rivals.log`; peak RSS of the process in each case):

| rival | trials | seconds | peak RSS | pick (inner window only) | inner MAE | N2 at lead 0 vs donor median 9.742 |
|---|---|---|---|---|---|---|
| ridge | 3 fits (24 candidates) | 0.5 | 0.22 GiB | log_c, alpha 1 | 6.350 | eligible |
| rf | 12 | 9.4 | 0.27 GiB | arcsine, max_features 0.5, min leaf 50 | 6.684 | eligible |
| lgbm | 12 | 24.4 | 0.28 GiB | arcsine, 31 leaves, min child 200, 200 rounds | 6.439 | eligible |
| lgbm_tweedie | 8 | 16.3 | 0.28 GiB | power 1.2, 127 leaves, min child 200, 400 rounds | 6.565 | eligible |
| hgb_l1 (timid-prone label) | 12 | 76.2 | 0.28 GiB | arcsine, 127 leaf nodes, min leaf 20, 400 iterations | 6.355 | eligible |

- These are inner-window (decision-surface) MAEs, used for tuning only. They are NOT test scores.
- **Flags:** none. One hgb_l1 trial had its own best at 800, but the learner's pick was at 400, so no extension ran
  (Y2).
- **Leak checks:**
  - No `test/` folder under `_export`.
  - No `scores/` folder, no `lead_*` folder and no `test_labels_opened_rivals*` file in the board.
  - In the pytest run, the T1 read spy saw no test-file read, no test_preds `y` request and no
    `open_test_labels` call.
- **Determinism:** three dry passes give equal picks and an equal trials.csv sha, and all 47 trial
  `inner_preds.parquet` files are byte-equal. The three passes are builder B's (`pt\harness\dry`), my CLI pass
  (moved aside to `_moved\20261020T155728280860`) and the pytest pass (now in `_dryrun`).
- **The lock:** the board now in `_dryrun\coral\20261020_f3b8e3da` has picks.json sha 0877fccb. It is labelled DRY:
  the board's real coral tune runs after the owner signs the rival Part, and it must reproduce these picks.

## 5. Owner items (carried from the builds; checked here)

| id | item | status |
|---|---|---|
| **O-A1 (blocking pm25)** | I4: no proof hop 7b508557 -> ... -> 65a177bc (re-checked here: "reachable ['7b508557']"). I5: pm25 `engine_constants_sha256` is d1592748; LIVE and every other run have 3ef147e5. `s_20261016\smokes\compare_pm25_*.txt` show 1 must-match difference (`per_group_schedule.json`: `reader_builds` 24 vs 16, a resume record). | Owner: re-run pm25 under LIVE (the last headline ran from 23:38 to 15:06 in its log), or rule the differences acceptable. |
| S1 / O-1 | The RF stride budget is 4.5 GiB (`models.py:43`). The formula gives ndvi 3, not the plan's 4. | Owner picks. Time is unaffected (RF cost per tree does not depend on rows). |
| S1 / O-2 | The stride is computed per fit set, so defo tunes with 2 and refits with 3. | Owner: one stride per problem, or one per fit set. |
| O-3, O-4 | LightGBM residual label with a zero init score; one Dataset per (fit set, link) (`models.py:357`). | Approve. |
| O-6, O-7 | The watchdog counts memmap pages. A declined nowcast takes the decline target as "ours". | Note. |
| NEW | The lineage file must be named in the production rivals.yaml (section 2, fix 3). | Do it when the production config is written. |
| NEW | A Y2 extension refits from scratch to 1600 (R-Y2 a). That doubles the extended trials' cost; worst case in section 6. | Note only. A continued fit would halve it, but the spec's byte check of rounds 100-800 is then trivially true. |

## 6. Step 4: the time plan, re-estimated (lean board: Ridge, RF, LightGBM, Tweedie where the rule fires)

**How:**

- **Coral:** measured.
- **Grid fitting:** extrapolated (x) from the plan's own units (plan 5a-5c): LightGBM upper about 8.5 min per
  (1M rows x 300 columns) at 800 rounds (half the plan's 1600-round 17 min); low = 0.35 x upper. RF and Ridge as in
  plan 5c (they do not depend on rounds).
- **Fit counts:** tune trials as in 5b, plus refits (one per lead) and guard fits (one per non-zero lead).
- **Why coral cannot price the grids:** at 9.3k rows its times are mostly fixed cost. For example, LightGBM takes
  2.0 s per 800-round trial.
- **Grid export:** the engine's own logged derive times (SPEC 2.9) plus the smoke-measured per-lead export cost,
  scaled by rows. For fire that is 13.7 s per lead x 24.7 = about 6 min per lead, plus a pool fill of about 9 min.

| problem | export (x) | Ridge | RF | LightGBM (upper / low) | Tweedie (upper / low) | fitting upper | fitting low | worst-case Y2 extension (upper) | peak RAM |
|---|---|---|---|---|---|---|---|---|---|
| coral | ~1 min (measured 42 s for 2 roles) | measured | measured | measured | measured | **~0.1 h** (tune 2.3 min measured; refits and scores about 2-4 min) | same | 0 (none triggered) | 0.3 GiB fit; 2.4 GiB with the export |
| fire | ~2.6 h (census 826 s + derive 5,841 s + 3 x ~15 min) | 0.05 | 0.9 | 0.7 / 0.25 | 0.55 / 0.19 | **2.2 h** | 1.4 h | +2.0 h | export 8.3 GiB (owner command, apps closed); fit ~2 GB |
| defo | ~3.5 h (census 90 s + derive 1,052 s + 2 pool fills ~1.6 h) | 0.2 | 1.8 | 5.5 / 1.9 | 4.1 / 1.4 | **11.6 h** | 5.3 h | +16.6 h | ~4.7 GiB |
| ndvi | 2.5-15 h (one lead at a time) | 0.3 | 2.0 | 5.1 / 1.8 | - | **7.4 h** | 4.1 h | +7.2 h | export 6.1 GiB; fit ~4.5 GB |
| pm25 (blocked, O-A1) | ~5 h (derive 4.4 h), after a LIVE re-run if chosen | 0.1 | 0.7 | 1.7 / 0.6 | - | **2.5 h** | 1.4 h | +2.75 h | ~4.3 GB |
| **all** | **~14-26 h** | 0.7 | 5.4 | 13.0 / 4.6 | 4.7 / 1.6 | **~24 h** | **~12 h** | **+~29 h** | |

> **Superseded 2026-10-21 (ruling Z; Z_REPORT.md).** pm25 is NOT re-run (Z1): its export of the existing headline
> runs the forced P15 check, **+~2.5 h** (6 bank fits of ~21-25 min, run.log:1317-1321), so pm25 export is ~7.5 h.
> The RF column above assumed a row stride; the out-of-core RF (Z2) sees all rows and costs about: fire 2.0-2.8 h,
> defo 5.5-6.8 h, ndvi 7.2-11.6 h, pm25 1.4-2.2 h (cold disk read 118.9 MB/s; `_bench\z2_rf_bench_results.json`).
> New fitting total about 23-42 h; with the exports about 40-70 h (+29 h worst-case extension).
> RIVALS_OWNER_COMMANDS.md section 8 has the current table.

- **Grand total:** about 26-50 h of machine time (plan: 53-98 h). Dropping XGBoost and capping the base at 800
  rounds halve it. That is about 5-8 overnight sessions, one heavy job at a time.
- **pm25:** if it is re-run under LIVE, add one pm25 headline run first (its last log ran 23:38 to 15:06).
- **The extension column** is the case where every boosting learner picks 800: its 800-best trials refit from
  scratch to 1600, and the refits and guards run to 1600. Defo carries most of that risk (+16.6 h). On coral no
  learner was extended.
- **Order (Y4):**
  1. Coral end to end, after the rival Part is signed. It must reproduce the dry picks.
  2. Fire. Time its export, then run `probe` before `tune` and re-price from the probe.
  3. pm25 (if unblocked), then defo, then ndvi.
- **The fire probe matters:** it is the first real-shape timing of the harness. Every grid number above is still
  extrapolated (x).

## 7. Files

- `D:\treeroute\rivals_build\INTEGRATE_REPORT.md` (this file)
- Logs: `pt\integ\t01-t05.log`, `real01.log`, `smoke_fire.log`, `export_fire_smoke.log`, `dry_export.log`,
  `dry_init.log`, `dry_tune.log`, `dry_lock.log`
- Proof: `pt\integ\smoke_run.py`, `pt\integ\parity_proof.py`, `pt\integ\parity_fire_smoke.json`,
  `pt\integ\integ_smoke.yaml`
- Engine smoke: `runs\fire\smoke\20261020_ee5cd20a`; its export: `pt\integ\_export_smoke\fire\20261020_ee5cd20a`
- Dry pass: `_export\coral\20261020_f3b8e3da\lead_0`, `_dryrun\coral\20261020_f3b8e3da` (picks.json and its lock
  file); earlier copies in `_moved\` (nothing deleted)
- Edited: `rivals\tests\test_export_parity.py:162-177`, `rivals\tests\test_realdata.py:72,95,115`,
  `_machine\rivals_smoke.yaml`, `_machine\rivals_dryrun.yaml` (the `engine_lineage` key)
