# Z_REPORT: ruling Z finished (pm25 not re-run; Random Forest out of core)

Written 2026-10-21. Only files under `D:\treeroute\rivals_build` were written; old versions were copied to
`_moved\20261021_preZfinish_code` first. Nothing was deleted. The LIVE engine was only read. No rival test score was
made or read, no test label was opened, and the pm25 headline was not re-run or retrained.

## ATTENTION

1. **Ruling AA is not built yet.** AA5 says: build AA (LightGBM early stopping, 63 bins in tuning, lean export)
   after Z, update the draft, then sign. Building AA changes the code hash. Your choices:
   - (a) wait, and sign once after AA is built (this matches AA5);
   - (b) sign now on hash fb8656a9, and log AA later as a fix Part with the old and new hashes.
2. **Please confirm one wording point in Z1.** The ruling calls I5 "the per_group_schedule reader_builds count 24
   vs 16". In the code, the I5 refusal is the constants hash (`engine_constants_sha256`, d1592748 vs 3ef147e5).
   reader_builds 24 vs 16 belongs to I4 (hop 7a0341ef -> 65a177bc). Both are accepted. The config note and
   disclosure 3 of the draft now name each one correctly.
3. **The Random Forest takes much longer than first thought: about 16-23 h in all** (not ~5 h). The disk reads at
   about 119 MB/s. The bench's old "2,483 MB/s" figure came from the memory cache, not the disk.
4. **RAM.** For NDVI and defo, the RF alone needs about 4.5 GiB free; the whole NDVI job needs about 5.2-5.8 GiB.
   Today this PC had only 4.4-4.8 GiB free, so the fire smoke test skipped itself. Close apps before every session.

## What changed

- **pm25 (Z1), after the Z1 check:**
  - an accepted run must export all its leads in one call (`export.py:1545`);
  - if any lead fails, every lead manifest is moved aside (`export.py:1700-1707`), so no half export can be used;
  - a seal file `ACCEPTED_ALL_LEADS.json` is written last; without it, `init` and every later step refuse
    (`harness.py:595`, called at `:938` and `:1368`);
  - a nested "not checkable" or "skipped" result now counts as a failure (`export.py:1315`);
  - a config entry that is not needed now refuses (`export.py:1644`);
  - P15 logs the peak RAM after each bank fit (`export.py:1353`);
  - the evidence files moved to `evidence\z1\` (same SHA-256).
- **Random Forest (Z2), after the Z2 check:**
  - the RAM check before each fit now counts the rows the RF predicts (`harness.py:1089`, called at `:1587`,
    `:2096`, `:2122`);
  - the review's independent tests moved into `rivals/tests/test_rf_out_of_core.py` (OOC6-OOC9);
  - a heavy RAM test at the NDVI shape was added (OOC10; runs only with `RIVALS_HEAVY=1`);
  - the bench now measures the real disk speed (`_bench\z2_rf_bench.py --estimate`).
- **Docs:**
  - the draft Part: section 10 settled by Z1-Z3 (no OWNER DECISION PENDING left), protocol items 18-19, the
    disclosures, the new hash and a change note;
  - RIVALS_OWNER_COMMANDS.md: pm25 section 4 now uses the existing run; RF times added; no new command flags;
  - the INTEGRATE_REPORT.md time table is marked as superseded.
- **Not done (your call):**
  - one disk sweep could be shared by NDVI's 4 tune settings, saving about 0.9 h; this needs the tune loop
    rebuilt;
  - the watchdog limit could be lowered from 12 GiB toward your ~6 GB ceiling (`harness.py:91`); LightGBM's needs
    would have to be checked first.

## Tests

- Full suite: **149 passed, 4 skipped** (3 real-data and 1 heavy test, which only run when switched on;
  `pt\zfin\full1.log`, 16 min).
- OOC10 heavy test: **passed**. RAM grew 1.44 GiB against a 2.25 GiB budget; one tree took 15.4 s.
- Real data:
  - defo smoke export: **passed**;
  - fire smoke export: **skipped** (only 4.4 GiB RAM was free; it needs 5);
  - coral dry pass: **passed**, run twice.
- The Z1 review's files-only tests: **12/12 pass** (the evidence-path finding is fixed).
- After the full suite I removed one code comment that named the ruling. I then re-ran the coral dry pass,
  test_nonames and those 12 tests on the final hash; all passed.
- The Z1 review's toy tests export only lead 0. They now stop on the new "export every lead" rule, so they were
  re-written with all leads in `rivals/tests/test_accepted_difference.py`, and all pass there.

## RF time per problem (whole board: tune + guard fits + refits; disk read 118.9 MB/s)

| Problem | RF hours | Disk-read share |
|---|---|---|
| NDVI | 7.2-11.6 | ~2.8 h (25-30 file sweeps per fit) |
| defo | 5.5-6.8 | ~0.6 h |
| fire | 2.0-2.8 | ~0 |
| pm25 | 1.4-2.2 | ~0 |
| coral | ~2 min (measured 94-108 s tune) | 0 |
| **All** | **~16-23 h** | |

## Coral dry picks (inner window only), old RF vs new RF

| Learner | Pick (the same under old c298611e, Z2 a595a9b1 and new fb8656a9) | Inner MAE old -> new |
|---|---|---|
| ridge | log_c, alpha 1 | 6.3497 -> 6.3497 |
| **rf** | **arcsine, max_features 0.5, min leaf 50** | **6.6835 -> 6.6897** |
| lgbm | arcsine, 31 leaves, min child 200, 200 rounds | 6.4388 -> 6.4388 |
| lgbm_tweedie | own log, 127 leaves, min child 200, power 1.2, 400 rounds | 6.5649 -> 6.5649 |
| hgb_l1 | arcsine, 127 leaf nodes, min leaf 20, 400 iterations | 6.3549 -> 6.3549 |

- The picks content hash is **3b5a33f1**, the same as before, so the owner-command check value is unchanged.
- The prediction files of the other 4 learners (43 files) are byte-equal to the old pass.
- The 12 RF trial files are byte-equal to the Z2 pass, so the RF gives the same result each time it runs.
- No test folder or scores folder exists in the board.

## New total time

- Fitting: about 23-42 h. Exports: about 16.5-28.5 h (pm25 adds about 2.5 h for P15).
- **All: about 40-70 h over 8-14 overnight sessions, plus up to 29 h in the worst case for the 1600-round
  extension.** The 15.5 h pm25 headline re-run is no longer needed.

## Ready to sign

`PREREGISTRATION_DRAFT_rivals_common.md` is still DRAFT and UNSIGNED, with no open items. The signature block holds
the harness code hash **fb8656a9aa71b8fc18f53f306cdfaf639e0f8b966a22f7f5782c88863056d5c2**. The Part is ready to sign
for ruling Z. See ATTENTION 1 about ruling AA before you sign.

## Clean-up you may do

You may delete these synthetic test files (about 1 GB each):
- `review_tests_z\_pt\heavy1`
- `pt\zfin\heavy1`
