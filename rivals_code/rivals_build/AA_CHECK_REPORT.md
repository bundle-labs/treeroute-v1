# AA_CHECK_REPORT: full test suite, real-data tests and two coral dry passes after the AA build

Written 2026-10-21. Everything written here is under `D:\treeroute\rivals_build`, and nothing was deleted. The LIVE
engine was only read. No rival test score was made or read, and no test label was opened. The only real-data runs
were the smoke-size exports and the coral TUNE-ONLY dry pass. The timing bench used synthetic (toy) data only.

## Result

- **Tests: 166 passed, 1 skipped, 0 failed** (27.3 min, `pt\aa\check_full.log`). The real-data tests were on
  (`RIVALS_REAL=1`), and all 4 ran and passed. The one skip is the opt-in heavy synthetic RF test
  (`RIVALS_HEAVY=1`). It is not a real-data test.
- **Coral dry pass, run twice: the picks are identical between the two passes.** The picks content is `2a3e224e`
  in both. All 106 trial files match. The only differences are wall-clock fields (details in section 2).
- **The picks changed from the pre-AA board:** picks content `3b5a33f1` -> `2a3e224e`.
  - LightGBM is worse on the inner window: 6.4388 -> 6.5463.
  - Tweedie is better: 6.5649 -> 6.4522.
  - Ridge, RF and hgb_l1 did not change.
- **Coral tuning time:** LightGBM 23.6 s -> 8.1-8.5 s. Tweedie 21.5 s -> 6.2-6.3 s. All tuning 266 s -> 223-227 s.
- **New total time, re-estimated:** about **33-62 h** of machine time (was 40-70 h), over about 7-12 overnight
  sessions. The worst-case extension adds up to about +28 h (was +29 h). See section 4.
- **Harness code hash: `e5032ad59af881d7cf89359b428943263cdb9618e89cfd8d4d1c930402eaffff`.** It is the same before
  and after every run. No `rivals\*.py` file changed during this check.

## ATTENTION (owner item, the same one the builder raised)

On coral, 63 bins in tuning made the LightGBM pick worse on the inner window. Patience 50 also stopped trials before
their 63-bin best round. Both of these are confirmed in `pt\aa\coral_bins_probe.json`:
- **Bins:** at each trial's own best round, 255 bins beat 63 bins by 0.14-0.21 MAE.
- **Patience:** arcsine, 31 leaves, min child 200 has its best 63-bin round at 289, but patience stopped it at 84.

The patience value is pre-registered, so it must be settled before the rival Part is signed. The builder's options
are (a) keep AA2 and AA3 as ruled, (b) a larger patience (100-200), (c) 255 bins in tuning when the tune set is small
(a data rule), or (d) tune at 255 bins.

**Time cost of each option** (my measure, section 4):
- On a grid-sized toy, 63 bins save only 14-23% per round.
- The per-round inner-window scoring adds back about 1-15% per round, depending on the inner set's size.
- So, on the grids, nearly all of AA's fitting saving comes from early stopping, not from the bins.
- Option (d) would cost about +5-10% of the LightGBM tuning time.
- Option (b) costs about 50-150 more rounds per trial.

## 1. Test suite

Run from `D:\treeroute\rivals_build`, with `--basetemp` under `pt\aa` (the parent existed).

| run | command | result | log |
|---|---|---|---|
| check_full | `$env:RIVALS_REAL='1'; py -3.9 -B -m pytest rivals/tests --basetemp pt\aa\check_full -rA --durations=40` | **166 passed, 1 skipped**, 1,641 s | `pt\aa\check_full.log` |
| check_coral2 | the same variable; `pytest rivals/tests/test_realdata.py -k coral --basetemp pt\aa\check_coral2 -rA -s` | **1 passed**, 252 s | `pt\aa\check_coral2.log` |

- **Free RAM:** about 9.2-9.5 GiB was free during the runs, so every real-data test could run:
  - the fire smoke test needs more than 5 GiB (`test_realdata.py:91`), and it ran (150 s);
  - the defo smoke export parity ran (32 s);
  - the coral dry pass ran (246 s);
  - the AA4 lean-vs-full defo smoke ran (192 s).
- **All 14 tests in `test_aa_speedups.py` passed**, including the real-data AA4 test.
- **AA4 defo smoke timings in this run** (both disk caches warm): full 50.1 s and 51.0 s; lean 45.1 s and 45.8 s.
  That is about 5 s saved, the separability check alone, as the builder found. Byte identity and P1-P15 passed.
- **Warnings (19,192):** almost all are pandas "DataFrame is highly fragmented" warnings from the LIVE engine's
  `treeroute\pipeline\data.py:619` and `:682` during the real-data exports. The rest are library deprecation
  warnings (pyparsing via matplotlib, dask). None come from a test assertion.

## 2. Coral tune-only dry pass, twice (stopped at the lock)

Four boards were compared with a read-only script, `pt\aa\cmp_aa.py`:

| name | board | harness | picks content | picks.json sha | tune total |
|---|---|---|---|---|---|
| old (pre-AA) | `_moved\20261021T045638546750\20261020_f3b8e3da` | fb8656a9 | 3b5a33f1 | ef1ed947 | 266.3 s |
| builder | `_moved\20261021T052511772321\20261020_f3b8e3da` | e5032ad5 | 2a3e224e | 3b5faa3f | 227.7 s |
| **pass 1** (in check_full) | `_moved\20261021T053127513203\20261020_f3b8e3da` | e5032ad5 | **2a3e224e** | 9ec6480e | 222.8 s |
| **pass 2** (check_coral2) | `_dryrun\coral\20261020_f3b8e3da` (current) | e5032ad5 | **2a3e224e** | f2b16641 | 227.2 s |

Each later pass moved the earlier board aside (`test_realdata.py:113`). It was not deleted.

### Pass 1 vs pass 2 (and the builder's pass)

- **trials.csv:** byte-equal in all three AA passes (sha `d8e1b44c`).
- **inner_preds files:** all 53 are byte-equal.
- **trial.json files:** all 53 are equal except for timing fields:
  - `seconds` and `utc` in every file;
  - also `fit_info.read_seconds`, `fit_info.fit_seconds` and `fit_info.predict_seconds` in the 12 RF trials.
- This includes every LightGBM early-stop record: patience, cap, best round, stop round and the full per-round MAE
  trace.
- **Why picks.json differs in its bytes:** picks.json stores `board_json_sha256`. board.json differs only in
  `export.lead_0.manifest_sha256`. The export manifest differs only in timing and machine fields: `timings_seconds`,
  `written_utc`, `peak_rss_bytes` and `identity.I8.free_bytes`. The export content hash is equal. So the picks
  themselves are identical.
- **Nothing beyond the lock:** no `test/` folder and no `scores/` folder in any board. The read spy in the test saw
  no test-file read and no test `y` request. There were 53 fits per pass.

### Picks, old -> new (inner window only)

| learner | old pick | old checkpoint / MAE | new pick (identical in builder, pass 1, pass 2) | new round / MAE |
|---|---|---|---|---|
| ridge | log_c, alpha 1 | 1.0 / 6.349655 | same | 1.0 / 6.349655 |
| rf | arcsine, mf 0.5, min leaf 50 | 300 / 6.689709 | same | 300 / 6.689709 |
| hgb_l1 | arcsine, 127 leaf nodes, min leaf 20 | 400 / 6.354853 | same | 400 / 6.354853 |
| **lgbm** | arcsine, 31 leaves, min child 200 | 200 / **6.438774** | **arcsine, 127 leaves, min child 200** | **63 / 6.546261**, flag `edge_rounds_100` |
| **lgbm_tweedie** | own log, 127 leaves, min child 200, power 1.2 | 400 / **6.564923** (2 trials extended) | **own log, 31 leaves, min child 20, power 1.5** | **181 / 6.452232**, no extension |

- **Byte checks against the old board:**
  - ridge, rf and hgb_l1: all their prediction files are byte-equal to the old pass;
  - their trial.json files differ, because every trial's config hash now includes the tuning options
    (`harness.py:1169`);
  - lgbm and Tweedie: every file differs, as expected with the new method;
  - the old board's 2 extended Tweedie trials do not exist in the new board.
- **No trial was extended under AA on coral.** Every LightGBM trial stopped by patience, at round 79-231. Its best
  round was 29-181, so no best round reached the extension stage (400, 800].
- **The new LightGBM pick has the `edge_rounds_100` flag:** its best round, 63, is in the first stage
  (`harness.py:1253`). The flag is printed only.

### Tuning time per learner (seconds, summed over the trial lines in rivals.log)

| learner | old (fb8656a9) | builder | pass 1 | pass 2 |
|---|---|---|---|---|
| ridge | 0.4 | 0.5 | 0.5 | 0.3 |
| rf | 94.3 | 91.3 | 92.4 | 92.9 |
| hgb_l1 | 117.8 | 113.5 | 108.8 | 112.6 |
| **lgbm** | **23.6** | 8.5 | 8.2 | **8.1** |
| **lgbm_tweedie** | **21.5** | 6.3 | 6.2 | **6.3** |
| tune total (`tune done` line) | 266.3 | 227.7 | 222.8 | 227.2 |

- **LightGBM tuning is about 2.9x faster on coral, and Tweedie about 3.4x.** The trials now run 79-231 rounds,
  where they used to run 800.
- **The speed-up is smaller than the round cut** (800 -> about 107-131 rounds on average, 6-7x) because coral's
  9.3k rows make each trial mostly fixed cost.
- **The refit stage was not run** (the dry pass stops at the lock). So the new 255-bin lead-0 guard fit
  (`harness.py:2151`) is not timed on coral.

## 3. AA4 lean export: what it saves at full size

The figures below come from the headline runs' own logs, which I re-read for this check.

**R30 test-year count:** the lean export takes it from `derived.json` instead of counting it again.

| problem | log line | seconds |
|---|---|---|
| defo | `D:\treeroute\runs\defo\headline\20261017_d71c61f4\run.log:207` | 590 |
| fire | `D:\treeroute\runs\fire\headline\20261017_869d1f38\run.log:191` | 4,153.4 |
| pm25 | `D:\treeroute\runs\pm25\headline\20261007_74e67609\run.log:543` | 9,830 |
| ndvi | `D:\treeroute\runs\ndvi\headline\20261016_d1de3158\run.log:160` | 3.9 (loaded from a checkpoint; there is no counting time) |

- Because NDVI's figure is a checkpoint load, the old NDVI export estimate never included the count. So there is no
  saving against that estimate. If the count would really run in the rival export, the lean export avoids a cost
  the estimate never priced.

**Separability check:** the gap from the census's last line to the separability line is an upper bound on the
check's time, since nothing else is logged in between.

| problem | lines | gap |
|---|---|---|
| defo | `run.log:35-36` | 129 s |
| fire | `run.log:27-28` | 620 s |
| pm25 | `run.log:33-34` | 1,016 s |
| ndvi | `run.log:23-24` | 1,312 s |

**Export saving against the Z estimate (16.5-28.5 h):**
- R30 count: 0.16 + 1.15 + 2.73 = **4.0 h**.
- Separability check: up to 0.85 h more.
- New export estimate: about **12-24.5 h**.

**Corrections to this section (added 2026-10-21 after the AA4 review; the old text above is kept):**
- **NDVI's count is not free, it was only never priced.** NDVI's count reads about 604M rows and 256k files
  (`runs\ndvi\headline\20261016_d1de3158\run.log:159-160`), against 195M rows for pm25's 9,830 s count. A fit of
  time to rows and files on fire, pm25 and defo (it reproduces defo's 590 s) puts NDVI's count at roughly
  **7-23 h**. So the lean export saves that much on NDVI against a full export, and an NDVI export run with
  `--full-engine-checks` would take 7-23 h more than any table says. Never use that switch on NDVI without asking.
- **The separability saving is up to about 1.58 h, not 0.85 h.** NDVI is exported one lead per call, so its check
  would run three times: 129 + 620 + 1,016 + 3 x 1,312 s.
- **The 4.0 h R30 saving is not yet measured on a real export** (the defo smoke had nothing to skip). After fire's
  export, its `export_manifest.json` `derive` time should be about 1,700 s, against 5,841 s in the headline.
- The export estimate of 12-24.5 h stands (it never contained NDVI's count).

## 4. Fitting time with AA (RF, Ridge and the export units unchanged)

### Grid-sized toy bench (`pt\aa\bins_bench.py`, result `pt\aa\bins_bench_result.json`)

- **Setup:** 600k fit rows x 300 columns, synthetic, 8 threads, the harness's LightGBM settings, 60 rounds.
- **Per-round train time, 255 -> 63 bins:**
  - 31 leaves: 0.151 -> 0.131 s (-14%);
  - 127 leaves: 0.223 -> 0.173 s (-23%).
- **Per-round early-stop scoring** (the tree read from `dump_model` and run on 277k inner-sized rows): 0.087 s
  (31 leaves) and 0.118 s (127 leaves).
  - It scales with the inner set: about 0.02-0.03 s for the 69k inner rows of fire, pm25 and ndvi.
- **Net per round, 63 bins plus scoring vs the old 255 bins:**
  - defo (2.45M tune rows, 277k inner): about 0.90-1.00x;
  - fire (610k tune rows, 69k inner): about 0.90-1.01x.
- I used **0.95x per round**. In plain words: the bins about pay for the per-round scoring, and the time saving
  comes from running fewer rounds.

### Method

- **Old LightGBM fitting:** INTEGRATE_REPORT.md section 6, rebuilt from its units: 8.5 min per (1M rows x 300
  columns) at 800 rounds; low = 0.35 x upper. The rebuild gives 17.5 h upper; the table says 17.7 h.
- **Tuning share of that old time:** fire 59-69%, defo 70-78%, ndvi 42%, pm25 59%.
- **New tuning trial cost:** old trial x (rounds run / 800) x 0.95.
- **Refits and guard fits:** unchanged. They run at 255 bins at the picked round, and I kept the 800-round upper.
- **AA3 adds one fit per LightGBM learner per problem:** a fresh 255-bin lead-0 guard fit on the tune rows
  (`harness.py:2151`). Before, this guard re-used the tuning trial's predictions. It is priced at one 800-round trial.
- **Rounds run on the grids are unknown until a grid tune runs.** Three cases:
  - "coral-like": trials stop at about 16% of 800;
  - "middle": about 45%, a best round near 300;
  - "no stop": every trial runs to 800.

### LightGBM + Tweedie fitting, all problems

| case | upper old -> new | low old -> new |
|---|---|---|
| coral-like (stop ~130) | 17.5 -> **9.6 h** | 6.1 -> 3.4 h |
| middle (stop ~350) | 17.5 -> **12.6 h** | 6.1 -> 4.4 h |
| no stop (all reach 800) | 17.5 -> **18.4 h** (slower: extra guard fit) | 6.1 -> 6.4 h |

### New totals (RF 16-23 h and Ridge unchanged)

| part | Z estimate | AA estimate (middle case; range over the three cases) |
|---|---|---|
| fitting | 23-42 h | **about 21-37 h** (20-43 h) |
| export | 16.5-28.5 h | **about 12-24.5 h** |
| **all** | **40-70 h, 8-14 sessions** | **about 33-62 h, about 7-12 sessions** |
| worst-case 1600 extension | +29 h | **about +28 h** (see below) |

- **Why the worst case barely moves:** an extended trial also stops by patience. One whose base trial stopped at
  round s in (450, 800) is refit to 1600 and stops at s again, as the builder noted. That repeat costs s rounds and
  changes no result.
- **Saving available here:** skipping an extension when the base trial already stopped by patience would save that
  repeat. It would need an owner ruling (ruling AA2 says the extension "applies"), so I did not change anything.
- **The fire probe step** (RIVALS_OWNER_COMMANDS.md) should give the first real rounds-run figure for the re-pricing.

## 5. Notes

- **Docs still to update** (not my task; the builder's list stands):
  - PREREGISTRATION_DRAFT_rivals_common.md: hash fb8656a9 -> e5032ad5, AA not built -> built, and the patience
    value once settled;
  - RIVALS_OWNER_COMMANDS.md: the coral picks check value 3b5a33f1 -> 2a3e224e, and the times in section 8;
  - RIVALS_PLAN_COMMON.md is in LIVE (read-only).
- **Not tested on a real run:** the R30 count skip. No cheap real run has census rows that are not picked
  (SPEC_RIVALS.md 2.10). It is only tested on the engine class.
- **Files from this check**, all under `pt\aa`:
  - logs: `check_full.log`, `check_coral2.log`;
  - scripts: `cmp_aa.py`, `bins_bench.py`;
  - bench result: `bins_bench_result.json`;
  - boards: the moved-aside boards listed in section 2.
