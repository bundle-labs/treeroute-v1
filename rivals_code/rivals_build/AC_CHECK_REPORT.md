# AC_CHECK_REPORT: full test suite, two coral dry passes and a skeptic check after the AC build

Written 2026-10-21. Everything I wrote is under `D:\treeroute\rivals_build` (`pt\ac\...` and this file). Nothing was
deleted; earlier boards were moved aside by the test itself. The LIVE engine was only read: no file under it changed
during this check (a `find -newermt` scan after the runs found none). No rival test score was made or read, and no
test label was opened. The only real-data runs were the defo smoke export and the coral TUNE-ONLY dry pass (twice).

## Result

- **Harness code hash: `bc62c8056bcabb83ca3f4abb704499685658b3a0ba8738e31231883cbdbc9057`.** It was the same
  before the runs, after the full suite and after the second coral pass. It matches the builder's hash.
- **Full suite with `RIVALS_REAL=1`: 170 passed, 2 skipped, 0 failed** (24.4 min, `pt\ac\check_full.log`).
  - Skip 1, because of RAM: the fire smoke export test. Only 3.9 GiB was free, and it needs more than 5 GiB
    (`test_realdata.py:91-92`). Browser windows were using the rest. It is the only real-data test that did not
    run. To run it later, close apps first, then run
    `$env:RIVALS_REAL='1'; py -3.9 -B -m pytest rivals/tests/test_realdata.py -k fire --basetemp pt\ac\fire1`.
  - Skip 2: the opt-in heavy synthetic RF test (`RIVALS_HEAVY=1`). It is not a real-data test.
  - These real-data tests ran and passed: the defo smoke export parity (29 s), the coral dry pass (252 s) and the
    AA4 lean-vs-full defo smoke (222 s).
- **AA review folder re-run:** 29 of 29 passed (`pt\ac\check_review_aa.log`).
- **Two coral dry passes, with identical picks and trial files.**
  - The picks content is `14b18f1138ad3beac55db2cfa77a6a259b0c589208fa45eba287b7a040e7ca0f` in both passes.
  - trials.csv is byte-equal.
  - The 53 inner_preds files are byte-equal.
  - The 53 trial.json files are equal apart from their timing fields.
- **No extension ran on an early-stopped trial.** In both passes, all 20 LightGBM and Tweedie trials stopped by
  patience. No trial ran to the 800 cap, and no trial was extended. The log says "extended (ran to the 800 cap
  without a patience stop, AC2): none" for both learners.
- **Every LightGBM and Tweedie trial used 255 bins** in both passes (fit_info and the tuning record).

## ATTENTION (owner item): patience 50 still cuts the Tweedie rival short on coral

AC fixed the bins, but the pick is still not always the best model on the inner window. The AA bins probe
(`pt\aa\coral_bins_probe.json`) holds 800-round, 255-bin, no-patience traces for three coral settings, on inner rows
only. The traces in this pass match the probe round for round, so the two can be compared:

| trial | best round with no patience | best round with patience 50 |
|---|---|---|
| lgbm arcsine, 31 leaves, min child 200 | 83 (6.3872) | 83 (6.3872): the same |
| lgbm arcsine, 127 leaves, min child 200 (the new pick) | 41 (6.3845) | 41 (6.3845): the same |
| **Tweedie, 127 leaves, min child 200, power 1.2** | **320 (6.5330)** | **175 (6.5676), stopped at round 225** |

The no-patience Tweedie trial (6.5330) would beat the Tweedie pick that was locked (6.5664). So with patience 50,
the Tweedie rival is about 0.033 MAE weaker on the inner window than its own grid allows. LightGBM is not affected
on the two settings that were probed.
- This is option (b) of AA_CHECK_REPORT.md (a larger patience, 100-200). Ruling AC did not change the patience.
  It is pre-registered, so it must be settled before the Part is signed.
- With patience 150, this trial would have run on to round 320 and past it. On coral the extra cost is seconds.

## 1. Test runs

| run | command (from `D:\treeroute\rivals_build`) | result | log |
|---|---|---|---|
| check_full | `$env:RIVALS_REAL='1'; py -3.9 -B -m pytest rivals/tests --basetemp pt\ac\check_full -rA --durations=40` | **170 passed, 2 skipped**, 1,465 s | `pt\ac\check_full.log` |
| check_coral2 | the same variable; `pytest rivals/tests/test_realdata.py -k coral --basetemp pt\ac\check_coral2 -rA -s` | 1 passed, 254 s | `pt\ac\check_coral2.log` |
| check_review_aa | `py -3.9 -B -m pytest review_tests_aa --basetemp pt\ac\check_review_aa -q` | 29 passed, 279 s | `pt\ac\check_review_aa.log` |

- The builder's toy run had 167 passed and 5 skipped. The 3 extra passes here are the three real-data tests that
  ran.
- The coral dry pass peaked at 0.83 GiB of working set in pass 1 and 0.32 GiB in pass 2. The limit is 6
  (`test_realdata.py:137`).
- Pass 1 made 53 fits, pass 2 made 53.

## 2. Coral TUNE-ONLY dry pass, twice (stopped at the lock)

The boards were compared with a read-only script, `pt\ac\cmp_ac.py`. Its output is in `pt\ac\cmp_ac_out.txt`.

| name | board | harness | picks content | tune total |
|---|---|---|---|---|
| pre-AA | `_moved\20261021T045638546750\20261020_f3b8e3da` | fb8656a9 | 3b5a33f1 | 266.3 s |
| AA (63-bin tuning) | `_moved\20261021T104020649632\20261020_f3b8e3da` (moved aside by pass 1) | c52babae | 2a3e224e | 222.8 s |
| **AC pass 1** | `_moved\20261021T104640505029\20261020_f3b8e3da` (moved aside by pass 2) | bc62c805 | **14b18f11** | 226.6 s |
| **AC pass 2** | `_dryrun\coral\20261020_f3b8e3da` (current) | bc62c805 | **14b18f11** | 230.3 s |

**Pass 1 against pass 2:**
- There are 106 trial files.
  - 53 are byte-equal: all the inner_preds files.
  - 53 are equal once the timing fields are removed: the trial.json files. The timing fields are `seconds`,
    `utc` and the RF `fit_info` read, fit and predict seconds.
  - No file differs in any other way, and no file exists on only one side.
- trials.csv is byte-equal (`bebd123c`).
- picks.json differs only in its bytes (`0bdb0287` against `d6b94d85`). It stores the board.json sha, and that
  changes with the export manifest's timing fields, as it did in the AA check. The picks themselves are identical.
- **Nothing ran past the lock:** neither board has a `test/` folder or a `scores/` folder. The read spy saw no
  test-file read and no test `y` request (`test_realdata.py:124-129`).

### Picks: pre-AA, then AA, then AC (inner window only)

| learner | pre-AA | AA (63-bin tuning) | **AC (both passes)** |
|---|---|---|---|
| ridge | log_c, alpha 1: 6.349655 | same | same |
| rf | arcsine, mf 0.5, leaf 50, 300: 6.689709 | same | same |
| hgb_l1 | arcsine, 127 nodes, leaf 20, 400: 6.354853 | same | same |
| **lgbm** | arcsine, 31 leaves, min child 200, round 200: **6.438774** | arcsine, 127 leaves, min child 200, round 63: **6.546261** | **arcsine, 127 leaves, min child 200, round 41: 6.384508** |
| **lgbm_tweedie** | own log, 127 leaves, min child 200, power 1.2, round 400 (2 trials extended): **6.564923** | own log, 31 leaves, min child 20, power 1.5, round 181: **6.452232** | **own log, 31 leaves, min child 200, power 1.5, round 146: 6.566415** |

**LightGBM** is now the best of the three: 6.3845, against 6.5463 under AA and 6.4388 before AA.
- It equals the best 255-bin round in the AA probe (41, 6.3845).
- AC1 says "6.385 for the best 255-bin round", and this matches it.

**Tweedie** is about the same as before AA (6.5664 against 6.5649), but worse than AA's 6.4522. AA's number was not a
like-for-like number:
- 6.4522 was the 63-bin tuning model.
- The model AA would have reported was a 255-bin refit at round 181. Its inner MAE was never measured.
- At 255 bins, that same setting (31 leaves, min child 20, power 1.5) gives 6.7819 at its best round, 134.
- So the AA figure does not show a stronger reported Tweedie rival.
- The loss that is real is the patience cut in the ATTENTION item above.

**Early stopping in the AC passes:**
- Best rounds were 35-205, and the trials stopped at rounds 85-255.
- All 20 trials stopped by patience. None ran to the cap.
- Under AA, the best rounds were 29-181 and the stops were 79-231.

### Tuning time (seconds, summed over the trial lines in rivals.log)

| learner | pre-AA | AA | AC pass 1 | AC pass 2 |
|---|---|---|---|---|
| lgbm | 23.6 | 7.9 | 9.4 | 9.3 |
| lgbm_tweedie | 21.5 | 6.2 | 8.6 | 8.6 |
| rf / hgb_l1 / ridge | 94.3 / 117.8 / 0.4 | 91.2 / 110.5 / 0.4 | 90.7 / 111.0 / 0.4 | 87.9 / 118.5 / 0.3 |
| tune total | 266.3 | 222.8 | 226.6 | 230.3 |

- On coral, 255 bins add about 1.5 s to LightGBM and 2.4 s to Tweedie.
- AC also removes AA's extra 255-bin lead-0 guard fit, which AA priced at one 800-round trial per learner and
  problem.

## 3. Skeptic check on the change

**Is LightGBM now tuned at full strength?**
- **Bins: yes.** There is one constant, `models.py:79` (`LGBM_MAX_BIN = 255`).
  - The tuning trial passes it (`harness.py:1639`); so do the probe (`harness.py:2051`) and every guard fit and
    refit at leads 1 and above (`harness.py:2176`, `:2203-2204`, `:2234-2235`).
  - The binned Dataset is cached under a key that includes the bin count (`models.py:421`).
  - The trial's config hash includes the tuning options, with `max_bin` (`harness.py:1168-1170`,
    `models.py:186-199`). So an old 63-bin trial can never be reused on resume: its hash does not match, and it is
    moved aside.
  - No `63` bin setting or `TUNE_MAX_BIN` is left in `rivals\*.py`. The only `max_bin=63` left is a refusal test on
    ridge (`test_aa_speedups.py:140`).
- **Best round on inner rows only: yes.**
  - The early-stop set is `inner.name` (`harness.py:1636`), and its metric uses the export's inner labels
    (`:1637`).
  - The fit is handed `[inner]` only, and the harness refuses any other score set (`:1640-1643`).
  - `_fit_lgbm` refuses an early-stop set that is not among the score sets (`models.py:595-598`).
  - Each kept round's MAE must equal the per-round trace bit for bit (`models.py:633-639`, `harness.py:1657-1659`).
- **The pick is the best round, not the best stage.** On coral, the new LightGBM pick (round 41) beats every staged
  round of that setting.
- **The lead-0 guard is the tuning trial at the pick** (`harness.py:2179-2194`).
  - This is sound only if a fresh 255-bin fit at the picked round gives the same model. The toy test checks this
    byte for byte, for both learners (`test_aa_speedups.py:241-259`), and it passed.
  - The early-stop callback only reads trees (`models.py:532-560`). It does not change training.
  - The refit refuses a trial whose recorded bin count is not 255 (`harness.py:2185-2190`).
  - On real data, this equality is not checked. That would need a refit, which reads test files.
- **Not full strength:** patience 50 (`models.py:78`) cut one Tweedie trial before a better round, as shown in the
  ATTENTION item. This was option (b) in the AA check. It is unchanged by AC.

**Is the extension rule right?**
- `models.ran_to_cap` (`models.py:212-227`) returns true only when there was no patience stop and the iterations
  run equal the cap. A record with a missing field, or one that contradicts itself, refuses.
- `harness._extension_ids` (`harness.py:1819-1834`) builds the ran-to-cap record for every lgbm and Tweedie base
  trial. A trial without an early-stopping record refuses.
- `trials_to_extend` (`harness.py:1230-1242`) skips every trial stopped by patience. It refuses if any trial lacks a
  record. A trial that is already extended is never extended again.
- **Edge case:** take a trial whose best is round 750, with no gain in rounds 751-800. After round 800,
  `since_best` reaches 50, so the trial is marked stopped by patience (`models.py:555-557`). It is not extended.
  - This is right: a fresh refit with cap 1600 would stop at round 800 again, so the result would be unchanged.
    That is AC2's own reason.
  - The review test `test_aa_skeptic_*` covers this case (best 750, patience stop at 800), and it passed.
- With patience 50, any trial that ran to the cap has its best round in (750, 800], so it is always in the last
  stage. The extra `in_last_stage` test (`harness.py:1241`) is redundant but harmless.
- hgb_l1 keeps its own rule (own best at 800), and its 6 extension trials on coral are unchanged.
- **Flow-A test caveat:** `test_ac2_patience_stopped_trials_are_not_extended_on_flow_a` checks that the extensions
  equal the trials that ran to the cap. If no toy trial ran to the cap, it only shows "none extended".
  - The positive case is covered elsewhere: `test_tuning_rules.py::test_t7_ac2_...` uses designed rows, and the
    forced fixture (`test_aa_speedups.py:263-290`) runs the extension code path.
  - Both passed.

**Any test-row read?**
- No.
  - Tuning loads only the "tune" fit set and the "inner" score set (`harness.py:1765-1766`).
  - The lead-0 guard reads only inner keys and labels (`harness.py:2192`).
  - Test files are first read in `refit` after `verify_lock` (`harness.py:2120`, `:2226`).
- In both coral passes, the read spy saw no test-label open, no test-file read and no test `y` request. Neither
  board has a `test/` or `scores/` folder.
- The AA probe file I used in the ATTENTION item was written in the AA check, on inner rows only. I made no new fit
  beyond the two dry passes.

**AC3 (out-of-core RF kept as it is): confirmed.**
- `models.py` changed only in its LightGBM parts. All diff hunks against `_moved\20261021_preAC_code` are at lines
  19-227, 416, 568 and 1221-1283. The RF code (from line 649) has no hunk.
- `harness.py` hunks touch only bins, extension, picks text and the guard.
- `cli.py`, `export.py` and `layout.py` are byte-equal to the pre-AC copies.
- The RF picks and inner_preds are the same in the AA and AC passes.

## 4. Still to do for AC4 (not done here, as the task asked)

- **PREREGISTRATION_DRAFT_rivals_common.md** still carries the old hash (c52babae / e5032ad5), the 63-bin tuning text
  and the old extension rule (19 hits). Write in `bc62c8056bcabb83ca3f4abb704499685658b3a0ba8738e31231883cbdbc9057`,
  AC1, AC2, and the patience decision once it is settled.
- **RIVALS_OWNER_COMMANDS.md** needs these changes:
  - The coral picks check value becomes `14b18f1138ad3beac55db2cfa77a6a259b0c589208fa45eba287b7a040e7ca0f` (it says
    2a3e224e...).
  - The refit note "lead 0 adds a 255-bin LightGBM guard fit" no longer applies.
  - The 63-bin wording, 3 hits.
  - If the patience changes, the coral picks change again. Then the dry pass must be re-run, and this check value
    with it.
- **The fire smoke export test** was skipped because of RAM (3.9 GiB free). Run it after closing apps (command in
  the Result section).

## 5. Files from this check (all under `D:\treeroute\rivals_build`)

- Logs: `pt\ac\check_full.log`, `pt\ac\check_coral2.log`, `pt\ac\check_review_aa.log`.
- Compare script and output: `pt\ac\cmp_ac.py`, `pt\ac\cmp_ac_out.txt`.
- Boards: as listed in section 2. The AA board's dry export folder was moved to
  `_moved\20261021T104024_946801Z\coral` by pass 1's export.
