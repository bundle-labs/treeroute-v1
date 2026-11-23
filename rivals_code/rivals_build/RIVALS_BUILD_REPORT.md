# Rivals build report: the review fixes, the Part draft and the owner commands

Written 2026-10-20. All writes are under `D:\treeroute\rivals_build`. No LIVE engine, package or run file was changed
(checked: no file in the engine folder, under `D:/treeroute/runs` or in the coral store is newer than the build).
No rival test score exists. No test label was read.

## ATTENTION

1. **The extension rule now reads "every trial" (R-Y2 b). You confirm this when you sign.** Before, a trial was
   extended to 1600 rounds only when its learner's PICK sat at 800. Now every boosting trial whose own best is 800
   is extended (leak-fairness 1). This gives the rivals more tuning, never less. On coral it extended 8 trials;
   none overtook its pick, so **the coral picks are unchanged** (Part item 10.3).
2. **pm25 is still blocked** (its export refuses at I4/I5). You choose: re-run pm25 under LIVE (~15.5 h, recommended),
   accept the difference, or leave pm25 off (Part item 10.1).
3. **Disk: D: has 27 GB free.** defo and NDVI only fit if YOU delete each lead's fit-set copies after it is scored
   (about 6.7 GB per defo lead, 10 GB per NDVI lead). The code never deletes; it prints "may delete" lines
   (Part item 10.4).
4. **Every command now needs `--config D:\treeroute\rivals_build\rivals_production.yaml`.** That file uses the
   engine's own machine file, so a rival job and an engine run can never overlap. RIVALS_OWNER_COMMANDS.md has every
   command.
5. Two smaller choices are open: the RF memory budget (ndvi stride 3, not 4) and the extension cost (Part items 10.2,
   10.5). The recommended answers change nothing.

## What I did

- Applied the valid review issues (below). The harness code hash is now **c298611e** (was 3d655ea4).
- Tests: **116 passed, 0 failed**, real-data tests included (`pt\fix\final.log`, 15.5 min). That is the old 83 + 3
  real-data, plus 30 new: 20 for the harness fixes (`rivals\tests\test_review_fixes.py`), 8 export mutation tests
  (`rivals\tests\test_export_mutations.py`), 2 tuning rules. The reviewer's own tests: **26 of 26 pass**
  (`review_tests`; it had 16 of 26). In its poisoning test I re-sign the copy's manifest, because the harness now
  refuses an edited file first.
- **Coral dry pass, re-run (tune only, stopped at the lock):** the same picks as before. The picks content hash is
  3b5a33f1 in all four dry boards. All 47 base-trial prediction files are byte-equal to the first build's. The
  8 extended trials are new. No test folder, no test-label record.
- **New direct proof that the exported feature values are the engine's (P15, parity 3):** the engine's own bank fit
  on the exported rows reproduces the run's bank fingerprint for every bank:
  - fire smoke: 6 of 6;
  - defo smoke: 4 of 4.

  See `pt\integ\parity_p15.py` and the two `parity_p15_*.json` files.
- **Lead 6 exported alone** (the NDVI path, one lead at a time): all 13 group files are byte-equal to the all-leads
  export. The new every-link P9 passes:
  - identity: gap 6.1e-7;
  - log_c: gap 1.2e-8;
  - arcsine: not checkable, because the run saved no arcsine trees-off at lead 6. This is recorded, not skipped.

## The fixes (file:line in `rivals\`)

| Review | Issue | Fix |
|---|---|---|
| leak 1 | Y2 extended only when the pick was at 800 | `harness.py:1169` trials_to_extend: every trial whose own best is 800 |
| leak 2 | the lock could be redone after test labels were opened | `harness.py:1786` verify_lock checks each label record's picks sha. `:1311` tune and lock refuse once a test trace exists. `:1273` a run ledger outside the board refuses other picks (`:1830` lock, `:2219` label opening) |
| leak 3 | the harness trusted the role flags | `harness.py:745` every row read is re-checked against the cuts and issue = time - lead. `:781` no key is in both a fit set and its score set |
| leak 4, parity 2 | export file hashes were never checked | `harness.py:704` groups come from the manifest's list (a stray or missing file refuses). Each file's sha256 is checked before it is read |
| leak 5 | no lower-edge flags | `harness.py:1209` edge_rounds_100 and edge_alpha_0.1 (printed only) |
| parity 1 | the LIVE engine was not pinned; lead-L exports were not checked | `harness.py:1476` load_board refuses a changed engine. `:900` every lead must share lead 0's identity and the run's c |
| parity 4 | P9 checked only the identity normal | `export.py:1563` every link within the run's tolerance; an unsaved link is recorded as not checkable |
| parity 5 | the lead-L comparator was rebuilt | `harness.py:2145` reads the run's saved trees-off column; rebuilds only when it is missing; the source is recorded |
| parity 6 | "ours" was not tied to the run | `harness.py:2292` at lead 0, pooled and per-group MAE must equal the run's score files. board.md labels "headline answer" and "pinned model" |
| parity 7 | untested refusals | `tests\test_export_mutations.py` covers I6, P2, P3, P4, P5, P8, P9, P10. The harness refusals are in test_review_fixes |
| parity 10 | run facts were not re-checked | `harness.py:1248` run files hashed at init and re-checked by every command; legal range and c checked per lead |
| robust 1 | a hard kill left a traceback and a stale lock | `cli.py:94` engine refusals print one plain line plus the fix. `harness.py:2446` `unlock` (dead process only). `:2468` `status`. Tested with a real taskkill |
| robust 2 | the default config took the test lock | `cli.py` refuses without `--config`. New `rivals_production.yaml` |
| robust 3, 7 | fit-set copies were never freed; a killed copy left a temp file | `harness.py:938` optional `scratch_root`, a free-disk check (size + 3 GiB), killed temp files moved aside. `:2398` "may delete" lines |
| robust 4 | the watchdog counted memmap pages | `harness.py:348` counts private memory; the resident set is kept |
| robust 5 | models stayed in RAM | `harness.py:2082`, `:2128` del + gc |
| robust 6 | a rebuilt export could never match | `harness.py:593` the board binds to a content hash with no timings. `:1412` the manifest and units are kept in the board, so score needs no export |
| robust 8 | the export disk check left out the engine's pools | `export.py:381` adds the run's own temp_disk_plan, per drive |
| robust 9 | export moved files aside before the lock | `export.py:828`, `:1343` checks first, moves only under the lock |
| robust 10 | a kill between picks and lock was a dead end | `harness.py:1830` lock redoes it |
| robust 12 | RF stride per fit set | `harness.py:1015` one stride per board, from the lead-0 refit rows |
| robust 13 | logs | dask warning filtered; "k/N" progress; flags and the link in pick lines; a log header |

## Not applied

- **Robust 11** (continue the saved booster instead of refitting to 1600): your choice (Part item 10.5).
- **Deleting caches**: needs your ruling (Part item 10.4); the code only prints them.
- **Disclosures only, no code** (leak 6, leak 7, parity 9): now in Part section 9.
- **Parity 8:**
  - The coral all-lead export and the NDVI smoke export are owner steps (commands, sections 2 and 6a).
  - I ran no NDVI engine smoke run.

## Note

- The watchdog's private memory reads higher than the old resident number on small jobs: coral 0.9 GiB, against
  0.28 GiB before. It is the safer number, so the 12 GiB stop now comes slightly earlier.

## Files

- `D:\treeroute\rivals_build\PREREGISTRATION_DRAFT_rivals_common.md` (DRAFT, UNSIGNED)
- `D:\treeroute\rivals_build\RIVALS_OWNER_COMMANDS.md`
- `D:\treeroute\rivals_build\rivals_production.yaml`
- Code: `rivals\harness.py`, `rivals\export.py`, `rivals\cli.py`.
- New tests: `rivals\tests\test_review_fixes.py`, `rivals\tests\test_export_mutations.py`.
- Edited test: `rivals\tests\test_tuning_rules.py` (reading b).
- Proof: `pt\integ\parity_p15.py`, `pt\integ\parity_p15_fire_smoke.json`, `pt\integ\parity_p15_defo_smoke.json`
- Logs: `pt\fix\final.log` (suite), `pt\fix\dry_*.log` (dry pass), `pt\fix\export_l6.log`
- Dry board: `_dryrun\coral\20261020_f3b8e3da`. The earlier boards are in `_moved\` (nothing deleted).
- Pre-fix code copy: `_moved\pre_fix_code_20261020\`
