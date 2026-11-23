# Parts waiting to be appended to EXPERIMENT_SUMMARY.md

The log file at C:/Users/<user>/Downloads/desertflow/desertflow_bundle_global/EXPERIMENT_SUMMARY.md was not found on 2026-10-05 (the Downloads/desertflow folder is gone). Append these once its new location is known.

## Part 579 - LADDER RULES H2-H5 + THREE LEADS (I1) + G1 BUILT; ALL FOUR DRAFT SMOKES PASS; RE-PRICED TO ~41 MACHINE HOURS.

2026-10-05.

- **G1 (NDVI lead 12):** fit rows with empty router context leave that lead's fit. That is 920 rows, Jan-Jun 2003 only, 3-4% per unit. Leads 0-6 are byte-identical to before. The dropped rows also leave that pass's normal (R15).
- **I1:** lead constant C6 = (6, 12) months, plus the lead-0 contract. Defo gets one merged 1-year lead.
- **H2:** each lead fits its guard bank (plus correctors, placebo and guard history) at its GUARD cut.
  - 0 guard rows sit inside the bank's label window at every lead (before H2: all of them).
  - H2 flipped two smoke-size guards: pm25 lead 6 now fails, defo 1-year now passes. That is the bias it removes; there is no sign information at smoke size.
- **H4:** test rows without issue-step features are never scored. They are saved flagged in issue_missing_rows.parquet (0 on all four).
- **H5:** per-lead fallback level.
- **Suite:** 2,900 passed, 0 failed.
- **Smokes:** pm25 95 s / 3.0 GB, fire ~86 s, defo 35 s / 0.4 GB, ndvi 143 s / 3.9 GB.
  - The lead-0 contract is byte-identical on all four.
  - The nowcast and each lead's test_preds are unchanged by H2; only the guards moved.
- **Re-priced:** the cost model first reproduces the old 42.5 / 54.8 h. New total: 41.3 h measured / 53.8 h conservative.
  - pm25 8.6, fire 3.3, defo 14.6, ndvi 14.8.
  - Two leads instead of four, but one extra guard bank per lead.

## Part 580 - BAN LISTS INSTALLED, SIGNED TIMING FACTS, LAG RULE, LIVESTOCK HOLD: ALL FOUR REAL PACKAGES RUN (SMOKE)

2026-10-06. Rulings J, K, L (engine/OWNER_RULINGS_2026-10-05.md).

**Ban lists installed** per package (kept / banned):
- PM2.5 121/41; fire 121/65; defo 260 kept + 18 watch / 48 banned / 33 conditional (index families); NDVI 502/55.
- Owner lag rule:
  - missing-year columns kept via engineered lag-12 (or lag-1-year) columns;
  - unknown windows signed with cautious bounds;
  - new generic last-value rule (a missing month takes the previous value, at most 2 months back, never later; wired into ColumnReader.lagged);
  - long seasonal masks stay banned.

**Facts and fixes:**
- Livestock: the raw aglw_* are banned; aglw_*_hold2021 columns are kept (watch, lag 1 year). The 2022-23 layers apply India's FAOSTAT ratios to every region and are never read.
- 13 index windows signed {3, month, centred} (lag 1).
- phenology_sos_doy out on pm25/fire (Y0 2003).
- R4 now counts from the driver stores' first year.
- Defo (K): spei/amo lag-1-year, epo after the last-value fill, deeprec and MCD12Q1 lagged one year, MOD44B lag 2 years (moves defo Y0 to 2004, an owner decision).
- Static tables built for pm25/fire/ndvi.

**Real-package smokes:** pm25 159 s / 1.3 GB; fire 141 s / 1.1 GB; ndvi 209 s / 1.9 GB; defo exit 0. All show Y0 2003 and leads 6/12. Forecast guards mostly decline at smoke size (no sign information).

## Part 581 - STREAMING CENSUS: THE FULL PM2.5 TARGET (537M ROWS) NOW READS IN 2.7-3.2 GB INSTEAD OF ~60 GB; FULL-SIZE PLAN STILL STOPS ON THE PICKED-UNIT READER (16.4 GiB) AND THE RUN'S DISK PRE-FLIGHT

2026-10-06.

**Streaming build:**
- Built: derive/census.py (file-by-file census), pipeline/stream.py, a vault of picked units only, and the last-value wiring.
- Byte-identical to the in-memory path on all four drafts. A planted later label in an unpicked unit never reaches the vault.

**Full-size plan on pm25_draft:**
- The census read all 537,232,608 rows (2,034,972 units, 2,794 files) in 23 min at 3.16 GB peak.
- It then refused at G-DISK: the picked units' column reader (3,352,800 rows x 102 columns, all held at once) needs ~16.4 GiB.
- With that fixed, the run's disk pre-flight would ask 184-638 GB, because tables are counted for all groups at once rather than one group at a time.

**Next:** per-group processing of the picked-unit reader and of the tree-answer tables. That was already the plan's R20 design.

**Re-priced:** PM2.5 full run ~13-14 h measured (16-17 conservative), including about 4-5 h of streamed data passes.

## Part 582 - PER-GROUP READERS, CHECKS, FREEZE TOOL, GLS MEMORY FIXES; FULL-WIDTH PROBES: PM2.5 AND DEFO RUN END TO END, NDVI STOPPED BY RAM; NDVI'S R30 COUNT TAKES 8-13 H PER COMMAND

2026-10-06. Workflow <id>-588 (agents A, B, C1, C2 and their reviews) and the follow-up workflow (agents G and
F, and the acceptance stage). Owner rulings M1-M3 (engine/OWNER_RULINGS_2026-10-06.md). Details: engine/SMOKES_REPORT.md
section 11.

**Built (<id>-588):**
- A, per-group batching (plan R20) made real:
  - each group's picked-unit column reader, tables and GLS donor-row table are built, used and dropped one group at a
    time;
  - full-size pm25 temp disk at peak: 638.5 GB before, about 5.5 GiB after;
  - a RAM go/refuse (G-DISK) before the GLS weight model's donor matrix;
  - byte-identical to the whole-frame path on the pm25, fire, ndvi and wide pm25 smokes.
- B, the validators and `check` / `check --deep`: the bodies of all 21 approved guard signatures; the donor windows
  derived with the engine's own rules; G-EPOCH at every cut; 34 planted faults caught.
- C1:
  - C9 k measured (candidate 5.230771281733543e-08) and NOT set;
  - the defo K store script (the owner built D:/defo_features_k, 42 groups x 22 years);
  - drafts refreshed and stale tests fixed.
- C2: the freeze tool (treeroute_report/freeze.py: preconditions, lock, verify), PREREGISTRATION_DRAFT.md and the
  table builder.

**Built (this workflow):**
- G, GLS memory:
  - the lazy feature read is back to 8.18 bytes a value (round 1 had 12.18);
  - the blocked build's constant origin is corrected (9 bytes a value, about 10% headroom);
  - the store read's per-row cost is counted (P2.gls_answer_read_bytes_per_row = 64);
  - every smoke stayed byte-identical;
  - the full-size NDVI GLS peak is still estimated at 6.34 GiB (owner options a/b).
- F, ruling M2:
  - `check --deep` checks only the package's R21 smoke groups and names them (checked_groups);
  - the freeze accepts a deep report only on exactly those groups (F-CHECK-GROUPS);
  - the lock format is now treeroute_report.freeze/3.

**Acceptance.** On a frozen snapshot taken at 16:45, engine_code_sha256 a9a1b1870009 (equal to the live engine until
19:37).
- Probes (ruling M1): DRAFT copies keeping 3 groups each through split.yaml exclusions (the group with the most target
  rows plus the first 2 in sorted order), run with `treeroute run` at the same time.
  - C9 k was unset in the snapshot, so each probe ran on its own scratch engine copy with k = the candidate. I never
    touched the live constant.
  - Each copy had its own temp folder (the heavy-job lock is per temp folder).
  - pm25_draft: exit 0, 23.7 min, peak 3.88 GiB, temp 0.11 GiB (the pre-flight said 0.11). 74% of the time was data
    passes (the census, the separability check, R30's test-year count).
  - defo_draft: exit 0, 49.4 min, peak 5.85 GiB, temp 0.80 GiB (the pre-flight said 0.80). Banks ran at 1.0-1.4 s a
    tree (the model: 1.67).
  - Both: every row-level prediction file exists, and the lead-0 contract held byte for byte.
  - ndvi_draft: exit 4 after 94.6 min, still in R30's count. G-DISK refused a block (needs 3.52 GiB, 3.47 GiB free)
    after a web browser opened on the machine. The refusal was correct and nothing was written. Not re-run (it needs
    about 1.5-2 h with the machine to itself).
- Checks on the four real packages (ruling M2): quick 5-14 s each; deep 96-398 s. All exit 4 on owner items only:
  G-FACTS everywhere, G-CLOSED on fire, defo and NDVI, and G-EPOCH on fire (travel_time).
- Full test suite (once, on the snapshot): 3,357 passed, 0 failed, 4 skipped (opt-in heavy real-data checks), 68
  xfailed (known); 43.5 min.
- All of this ran on the state BEFORE ruling N (the sign-off answers, 19:21). At 19:36-19:37 the other workflow
  started writing them into the live tree: C9 k is now set to the same candidate (engine hash ec584edecb17), so every
  check and the suite must run again on the final tree before the freeze.

**ATTENTION:**
- NDVI's R30 test-year count reads every unit's whole record. The window starts before 2002 because of the
  long-memory outputs api_precip, api_soilmoist, consec_dry_months and months_since_sig_rain. It also re-reads the
  group's files for every unit block. Scaled from the probe: 8-13 h per command (PM2.5 1.5-3.3 h), none of it in plan
  4.5. Option: read each block's own rows only (a build item, byte-identity gated).
- The derive RAM peak is the census plus up to half the free RAM (R30's blocks), more than the plan prints (defo 5.85
  vs 3.89 GiB). Run the headline runs one at a time, alone on the machine.
- Running the probes at once worked for pm25 and defo: CPU mean 17%, the HDD the shared resource. It is not safe for
  full-size runs: the RAM checks are made at the moment they run, and a second job can make the first refuse.
- Estimated headline hours with today's data passes: fire 4.5-6.5, pm25 12.5-17.5, defo 15-20.5, NDVI 24-35. About
  56-80 in all, against the sign-off sheet's 51-65.

## Part 583 - SIGN-OFF APPLIED (RULINGS N + O), ENGINE O4 FLOOR + S23, PM2.5 FROZEN ALONE (DRAFT)

2026-10-06 evening.

- **Engine (before the freeze):**
  - O4: every R36 tolerance is max(k x s, C9.k_min_multiple_of_arith_error x C9.measured_arith_error) = max(k x s, 9e-7). Code: route/kinds.r36_floor and r36_tolerance, pipeline/stages.guard_tolerances (floor and rule written into the tolerance record).
  - S23: check_g_epoch no longer flags a regular or composite column's observed_through. It is the record end, listed only. An unreadable date still refuses.
  - Year strings removed from 4 docstrings (test_nonames); the run.py ones came from the S21 stage.
  - Tests: 4 stale tests updated (3 now stand in the unset-k state, 1 expects departures == []), plus the G-EPOCH test. 159 passed, 0 failed (test_pipeline, test_pipeline_pm25, test_constants, test_c9_guard_tolerance, test_check_guards, test_nonames, test_noknob, test_import). test_the_arcsine_link_runs_on_a_fraction_target passes now (it failed at 6.26e-09 vs 6.10e-09).
  - PM2.5 no-op gate: the new smoke's 23 prediction and score files (parquet, csv) are byte-identical to the smoke before the change. Only the JSON records differ: timestamps, fingerprint, and the tolerances, now floored (smoke identity 6.49e-7 -> 9e-7, log_c 2.43e-8 -> 9e-7).
- **S8 (O1):** the 17 refreshed exceptions.yaml entries were installed in all four packages (old files: datasets/_moved_s8_20261006/<package>/) and signed by apply_signoff.py. The dry run planned exactly 17 signatures; apply moved the old files to datasets/_moved_signoff_20261006T182204Z. All 45 entries are signed now (pm25 11, fire 8, defo 9, ndvi 17).
- **Pre-registration (O3):** PREREGISTRATION_DRAFT_pm25.md, a PM2.5-only copy. Items 7 and 11 are settled for PM2.5, the other three packages are marked not in this freeze, and the signature line reads "Signed by the owner (ruling O3, 2026-10-06)". The undrafted S1/S3/S6 disclosures are defo items only.
- **Checks (default run root):** pm25 fingerprint 625f4951..., quick green, deep green (332 s, R21 smoke groups). G-EPOCH now passes.
- **Freeze (PM2.5 alone, real registry):**
  - lock D:/treeroute/registry/freeze/FREEZE_20261006T203115Z.lock.json, sha256 cb41d40c500aa13cea87f8c117598a58f0162fc4e9933c8e2bf919f519f05c9b
  - filled pre-registration D:/treeroute/registry/freeze/PREREGISTRATION_20261006T203115Z.md, sha256 d1d6abaadf200bd2e8b76ce5ffeba2818d15816325d4648bfea811ee4a87a12d
  - engine_code_sha256 7b5085572574d767e7ef13a2248ac03af9e5f103f0ef49f5e85e9994d9344dbb
  - freeze verify: no drift.
- **Not done:** `treeroute plan datasets/pm25` was stopped by the agent tool's 2 h limit after the census (45 min) and 22 of 127 groups of R30's test-year count. So the lock records no derived.json/plan.json, and the filled copy marks DERIVED_SHA256/PLAN_SHA256/DERIVED_SETTINGS for pm25 NOT FILLED. The run does its own plan phase. The dead plan's heavy-job lock was moved, not deleted, to D:/treeroute/pm25fast_20261006/stale_heavy_lock/.
- **Next:** `py -3.9 -u -m treeroute run datasets/pm25` in the owner's own terminal (hours; resumable).

## Part 584 - HEADLINE RUN 1/4: PM2.5 (LEAVE-ONE-REGION-OUT, 127 GROUPS, 1,905 SCORED CELLS) - NOWCAST HELPS (MAE 3.588 vs trees-off 3.853, normal 4.032); LEAD 6 CANNOT TELL; LEAD 12 DECLINED

2026-10-07.
- Run D:/treeroute/runs/pm25/headline/20261007_74e67609 (run fingerprint 74e676096559d7c9, package 625f495161572b8b), under freeze lock FREEZE_20261006T203115Z (engine 7b508557).
- About 15.5 h wall time: data passes until 04:37, nowcast fits and router until about 10:30, lead 6 until 12:55, lead 12 until 15:02.
- 91,440 test rows, 2020-2023. Tables (from the saved rows; every verdict recomputed equal): D:/treeroute/runs/_headline_tables/headline_f191048b1853.md.

**Pooled results** (adopted arm vs own-link trees-off, guess-normal, last-5-years normal):

| Lead | Adopted | MAE | Anomaly R2 | Hit rate | Verdict |
|---|---|---|---|---|---|
| 0 | log_c corrector | 3.588 (vs 3.853 / 4.032 / 3.972) | 0.185 (trees-off 0.079) | 0.457 (normal 0.415) | HELPS |
| 6 | log_c corrector | 3.846 (vs 3.879 / 4.054 / 4.051) | 0.069 (trees-off 0.071) | - | CANNOT TELL |
| 12 | declined to identity trees-off (the guard failed: 3.581 vs 3.553 on the guard rows) | 4.084 | 0 | - | DECLINED |

- **Lead 0 detail:**
  - contrast 0.265, jackknife SE 0.045 over 127 groups, CI [0.177, 0.353];
  - band 0.0462, this run's own;
  - better than trees-off in 108 of 127 groups and better than guess-normal in 110;
  - per year, anomaly R2 2020 0.251, 2021 0.182, 2022 0.232, 2023 0.097.
- **Rival note:** damped persistence beats the declined lead-12 answer: MAE 3.835 vs 4.084. At lead 6 the adopted arm beats damped persistence, 3.846 vs 3.975. Report this beside lead 12. Same-month-last-year persistence carries the PM2.5 trend that the long-run normal misses.
- **Not comparable to Part 556** (hard split, 20 test regions, MAE 4.10 vs 4.54): the split, the region count and the bans differ.

## Part 585 (DRAFT) - FIRE, DEFO, NDVI PREPARED; FIRE AND NDVI FROZEN ALONE; DEFO WAITS FOR 5 OWNER SIGNATURES

2026-10-07. No engine code or shared catalog changed (engine 7b508557, as PM2.5's lock).
- **Fire, ruling O2:** the operation texts of the 7 history look-backs (build_history.py FUEL_OPERATIONS) now say "event count" or "count of months since the last event", at label lag 2. Text only: the original build_history.py was rebuilt from the edit and its sha256 equals the store manifest's (b6fde686...), and the store was not rebuilt. The catalog was regenerated, then its 9 kept columns re-signed (apply_signoff.py, fire-only copy of the ruling N answers, datasets/_tools/signoff_answers_2026-10-07_fire_O2.yaml; dry run planned exactly 9 S5 signatures). It differs from the old signed catalog only in those 7 operation and provenance texts. dataset.yaml now pins c93a2bd7... Old files: datasets/_moved_o2_20261007/, datasets/_moved_signoff_20261007T125758Z/. G-HIST now passes.
- **Checks (default run root), smokes (D:/treeroute/prep3_20261007, all exit 0, prediction files written):**

| Package | Fingerprint | Quick | Deep (R21 groups) | Smoke |
|---|---|---|---|---|
| fire | 18c7bbb8634c | green | green, 306 s | 161 s |
| defo | d109c36c0c4f | green | green, 88 s | 58 s |
| ndvi | edbc45b52643 | green | green, 388 s | 264 s |

- **Freezes (each package alone, real registry, its own PREREGISTRATION_DRAFT_<pkg>.md with items 7 and 11 rewritten and the O3 signature line):**
  - fire: D:/treeroute/registry/freeze/FREEZE_20261007T130812Z.lock.json, sha256 d77da0b854f86e0c96b3e2a994d942f2d5199cd8cdaba5d9c9ec55df0d368d66; filled PREREGISTRATION_20261007T130812Z.md, sha256 347d031107b1ab0bb1d972d705f96f5ae5a9ac12a4586872cb389db48a904197
  - ndvi: D:/treeroute/registry/freeze/FREEZE_20261007T132431Z.lock.json, sha256 7b34725519b5d9332f094ede777a35f000b5427af130b256871ad250d73a0744; filled PREREGISTRATION_20261007T132431Z.md, sha256 8c3003344d350b71ce0b84aeecc2aa1979e827a5be2b14d35ad032cfbff46866
  - freeze verify: no drift on the fire, ndvi and PM2.5 (FREEZE_20261006T203115Z) locks.
  - As with PM2.5, no plan exists yet, so DERIVED/PLAN fields read NOT FILLED; each run does its own plan phase.
- **Defo not frozen:** the 5 disclosures for ruling N's defo changes (S1, S3, S6 vegetation, S6 population_density, S28) are drafted UNSIGNED as exceptions.yaml entries 10-14 (old file in datasets/_moved_o2_20261007/defo/). Short owner list: engine/DEFO_NEW_DISCLOSURES.md. Pre-registration item 7 cannot be settled while they are unsigned. Signing changes defo's fingerprint, so quick and deep checks must be re-run, then defo is frozen alone.
- **Open:** last_burn_size is the size of the last event, so it equals a past target value at a varying lag. Its text says so plainly, under ruling O2. Tests: the 6 catalog and history tests of tests/test_fire_package.py pass; no full suite was run (lean testing).
- **Next:** `py -3.9 -u -m treeroute run datasets/fire; py -3.9 -u -m treeroute run datasets/ndvi`, then defo after its signatures and freeze.

## Part 586 (DRAFT) - CRASH-SAFE SAVING INSIDE THE CENSUS AND R30 (RULING P); FIRE AND NDVI RE-FROZEN UNDER ENGINE 1f257395

2026-10-13. Owner ruling P (OWNER_RULINGS_2026-10-06.md, section P), lean scope.
- **Why:** every restart derived again from zero. On NDVI that is the census (2,926 files, about 35 min) plus R30's test-year count (133 regions, about 17 h); a stop at region 83 lost about 12 h.
- **Engine (7b508557 -> 1f2573957b10b4ddea76bfa38598e35edbc3a593cf2b5eb7b33d1d8e9f386ae1):** new treeroute/runs/checkpoint.py; edits in derive/census.py, pipeline/stream.py, pipeline/run.py, runs/atomic.py; engine_constants.py block P6 (6 constants, each with an origin; no problem names).
  - Only two steps save as they go: the census pass (a record after every 1/100 of the target files, or every 60 s) and R30's count (a record per region as soon as it is counted). Later phases already save at their ends and were not touched.
  - Key = SHA-256 of the package fingerprint, engine_code_sha256, library and Python versions, and path/size/mtime_ns of every target, driver and static file; R30 adds the lag map, the test years, the donor-row hash and the picked units. Anything else changed -> nothing reused, the log names what changed.
  - Writes are temp file + fsync + rename; each record carries its own SHA-256. A bad record prints CHECKPOINT CORRUPT, is moved aside (not deleted) and recomputed.
  - Store: D:/treeroute/runs/<pkg>/_checkpoints/<step>-<16 hex of key>/ (key.json holds the full key). Removed by the engine after DONE.json.
- **Stale-key review (this part):** the key was read against everything the census and R30 read (target reader hooks, static table, driver plan, picked rows, both derive passes). No route found by which an old checkpoint is reused after the data, package, engine or settings change. No code change, so T3 was not re-run.
- **Gates (M5 no-op evidence, lean):** T1 PM2.5 smoke, old vs new engine: all 15 gate files byte-identical (derived.json, every preds parquet, every score/table csv). T2 hard kill mid-R30, then resume: the same 15 files byte-identical. T3 tests/test_checkpoint.py with test_nonames/noknob/import: 58 passed. Not run by any test: NDVI's R30 count over unpicked rows (the PM2.5 smoke picks every row); checked by reading only.
- **Re-freeze (ruling P3), each package alone, default run root:**

| Package | Fingerprint | Quick | Deep (R21 groups) | Lock | Verify |
|---|---|---|---|---|---|
| fire | 18c7bbb8634c | green | green, 262 s | FREEZE_20261013T102938Z.lock.json, sha256 204040c8f1194131c1903c17abd855521f4db122053a59a3c2975ebe24cd5d93 | no drift |
| ndvi | edbc45b52643 | green | green, 370 s | FREEZE_20261013T103700Z.lock.json, sha256 4b4606e59443e24123c05694fa186d36ec0b4e790a03f89cc33c70ff607289d9 | no drift |

  - Filled pre-registrations: PREREGISTRATION_20261013T102938Z.md (sha256 1654e538625da509e641dd69bf0bf098e64a98a7e18f6506cce03e4e7abf22b9) and PREREGISTRATION_20261013T103700Z.md (sha256 9bd51d5529b4459f3432611c94a97ec0a9a4c94b371c1c1932013cdeac55ae09), from the unchanged drafts. Both locks record engine 1f257395...; no constant awaits the owner.
  - PM2.5's lock (FREEZE_20261006T203115Z) now shows engine drift (checkpoint.py added, atomic.py changed, 6 P6 constants added). Covered by T1 under the M5 no-op rule; to disclose.
  - Old check reports kept at D:/treeroute/ckpt_20261013/refreeze/old_check_reports/.
- **NDVI's old plan moved aside:** the first NDVI freeze attempt refused F-PLAN: the latest plan, headline/20261012_eb4cde0b, was made by the old engine. That folder is the NDVI run that ruling P3 stops and restarts under the new engine. It was moved (not deleted) to D:/treeroute/ckpt_20261013/superseded_ndvi_plan/20261012_eb4cde0b, and the freeze then held. Its derived_sha256 is e2836c5eda7ac7ae280e2cd91e7043beaf8a1a8c0d6517ed7fa6fb82faf86cec: the restarted run's derived_sha256 (run_record.json) should equal it. That is a free full-size check that no number changed.
- **Next:** `py -3.9 runner/run_headline.py ndvi fire defo` from the engine folder. NDVI starts from zero once (the old runs saved no checkpoints). Defo still waits for its 5 signatures and its own freeze.

## Part 587 - RAM-SAVING ENGINE INSTALLED (RULINGS Q, R): WAIT INSTEAD OF STOP, NUMBER-NEUTRAL RAM TACTICS, PROVEN BYTE-IDENTICAL; NDVI CHECKPOINTS MIGRATED BY COPY; NDVI AND FIRE RE-FROZEN

2026-10-15/16.
- **Engine 7a0341ef** (was 1f257395).
  - In-run RAM and temp-disk checks now WAIT (poll 30 s, note every 10 min, refuse after 12 h).
  - The GLS donor matrix sits in a disk-backed memmap; the forest is byte-identical on it.
  - Memory is released and the working set trimmed before big steps.
  - Frames are built in one go where that lowers the peak; driver files are read in batches.
- **No-op proofs** (D:/treeroute/install_20261015/smokes):
  - pm25 smoke: 24 prediction/score files and derived.json byte-identical, plus 28 JSON records equal apart from times, paths and hashes;
  - ndvi smoke: 26 files plus 28 records identical;
  - ndvi smoke peak commit 2.14 to 2.06 GiB (small at smoke size; the saving scales with the GLS matrix).
- **Checkpoint proof** (CHECKPOINT_PROOF.md): census and both R30 passes give byte-identical payloads, old vs new engine, on the smoke groups and on 3 groups at headline kind (the count_part branch NDVI used).
- **Migration by copy** (ruling R2): migration.json. Verified: a derive under the new engine reads the census whole from its checkpoint and loads all 133 R30 groups.
- **Full suite:** 33 failed, 3363 passed. 32 of the failures fail on the old engine too (stale tests). The one new failure, test_layer_shapes approved parameters, is a signature list to update for the new plumbing argument.
- **Re-frozen:**
  - ndvi: FREEZE_20261016T012320Z (sha b2da313a). The old plan folder 20261014_4e505c2b was moved to _moved_install_20261015.
  - fire: FREEZE_20261016T012828Z (sha 184e9c7c).
  - PM2.5's finished run is covered by the pm25 no-op proof.

## Part 588 (DRAFT) - RULING S: SCORED ROWS WITH MISSING ROUTER CONTEXT ARE LEFT OUT, NOT REFUSED; PER-GROUP TREE CHECKPOINTS; NDVI CHECKPOINTS MIGRATED; NDVI AND FIRE RE-FROZEN

2026-10-16. NDVI stopped at its decision surface: G1 refused 365 scored rows of 12 coastal cells whose ERA5-Land and TerraClimate context is empty. Engine 65a177bc (was 7a0341ef) applies ruling S1, which extends H4: a scored row with missing context (decision surface, test pass, each lead's guard and test pass) is now left out of scoring and never filled. Each such row is saved with a flag in context_missing/<pass>_scored.parquet and counted per unit and lead in run.log and run_record.json (key score_context_left_out, written only when a row is left out). A unit with no scored row left is listed as unscored, and G-SPLIT plus treeroute_report/table.py tolerate and disclose it. Fit rows keep G1. The recorded G1_RULE, PARTLY_MISSING_NOTE and READINGS texts are unchanged, for byte identity; S1_RULE supersedes their "refuses" wording. Also new, at the owner's request: every bank (fit-cut, inner-cut, each lead's lagtrain and guard) saves each group's trees, correctors and placebos as it finishes (checkpoint step "bank"). A restart loads them after checking every tree's node-array fingerprint. The GLS model and the pool are not checkpointed. The one test was a pm25 smoke, hard-killed right after its first bank group was saved and then restarted ("bank fit-cut: 1 of 4 groups loaded"). Against the 7a0341ef pm25 smoke, all 24 prediction/score files and derived.json are byte-identical, the 27 other JSON records match, and all 6 bank fingerprints are equal. The only must-match difference is per_group_schedule.json's reader-build counts, a process record of the restart (R30 loaded from its checkpoint). CODE_DIFF_PROOF.md (D:/treeroute/s_20261016) shows that every file the census and R30 read is byte-identical (7 files changed, none in that path). NDVI's census and both R30 folders were copy-migrated (D:/treeroute/s_20261016/migration.json). The stale run 20261016_580c5b6f was moved to D:/treeroute/_moved_s_20261016/. Re-frozen: ndvi FREEZE_20261016T090651Z (sha 960bc7d5) and fire FREEZE_20261016T091126Z (sha f8c297e5). Both have green deep checks and verify reports no drift. The late-refusal scan was skipped by owner override. Next: `py -3.9 runner/run_headline.py ndvi fire`.

## Part 589 - HEADLINE RUN 2/4: NDVI (133 GROUPS, 1,995 SCORED CELLS) - NOWCAST HELPS (MAE 0.0315 vs NORMAL 0.0394, ANOMALY R2 0.317, 122/133 GROUPS); LEADS 6 AND 12 DECLINED

2026-10-17.
- Run D:/treeroute/runs/ndvi/headline/20261016_d1de3158. Engine 65a177bc (rulings P, Q, R, S), lock FREEZE_20261016T090651Z.
- The run took 19.3 h from the checkpointed derive (13:13 to 08:33). Every bank checkpoint was saved; the run removed its 3.5 GiB of checkpoints at the end.
- Tables: D:/treeroute/runs/_headline_tables/ndvi/.

**Results:**
- **Nowcast:** adopted identity plain unweighted.
  - Pooled MAE 0.0315, against 0.0394 for own-link trees-off and for guess-normal (identical here, the climatology identity) and 0.0393 for the last-5-years normal.
  - Anomaly R2 0.317 (normal 0).
  - Hit rate 0.461 vs 0.389.
  - Contrast 0.00792, CI [0.00675, 0.00909], band 0.000597.
  - Better than the normal in 122 of 133 groups.
  - Anomaly R2 per year: 2020 0.352, 2021 0.290, 2022 0.339, 2023 0.283.
- **Leads 6 and 12:** the guards failed (lead 6: 0.03718 vs trees-off 0.03690; lead 12: 0.03753 vs 0.03672), so both DECLINED to the normal (MAE 0.0396).
- **Rival note:** damped persistence beats the declined answer at both leads (0.0386 at lead 6, 0.0388 at lead 12, vs 0.0396). Report it beside the forecast rows, as for PM2.5.
- **Ruling S1:** 12 coastal cells (empty ERA5-Land and TerraClimate context) were left unscored. 365 decision rows and 576 test rows per pass were left out and counted; G1 left those cells' fit rows out. At lead 12, G1 also left out 13,481 fit rows across all units, mostly ctx:top5:sph_kgkg_lag6 (the lag-6 context reaches before the record). Disclose.

## Part 590 - HEADLINE RUN 3/4: FIRE (40 GROUPS, 2,000 SCORED CELLS) - NOWCAST HELPS BY A HAIR (ARCSINE CORRECTOR GLS 0.00439 vs ARCSINE TREES-OFF 0.00443); LEADS 6 AND 12 DECLINED TO THE IDENTITY NORMAL (0.00631); PREDICT-ZERO 0.00428 BEATS ALL ON MAE

2026-10-17.
- Run D:/treeroute/runs/fire/headline/20261017_869d1f38 (engine 65a177bc, lock FREEZE_20261016T091126Z). It took 4.3 h, the derive 1.6 h of that. Tables: D:/treeroute/runs/_headline_tables/fire/.

**Nowcast:**
- Contrast 4.23e-05, CI [1.5e-07, 8.4e-05] (barely above 0), band 1.36e-05. Better than trees-off in 23 of 40 groups.
- Anomaly R2 0.026 (trees-off 0.023); corr2 0.222 (normal 0.219).
- Hit rate 0.948 vs 0.913; strict top-10% detection 0.836 vs 0.837.
- MAE: identity normal 0.00626, predict-zero 0.00428.

**Leads 6 and 12:**
- The guards failed (lead 6: 0.004172 vs 0.004110; lead 12: 0.004368 vs 0.004319), so both declined to the D86 target, the IDENTITY trees-off (MAE 0.00631).
- That target is worse than the arcsine trees-off (0.00446) and than predict-zero (0.00428). The decline target is the plain normal, not the adopted link's trees-off: a design point to disclose and discuss.
- The model's (not adopted) lead forecasts: 0.00452 (lead 6), 0.00450 (lead 12).

**Caveat:** on this mostly-zero target, MAE rewards timidity (predict-zero wins). Report corr2, anomaly R2 and detection beside it (feedback memory: MAE ranks timidity on mostly-zero targets).

## Part 591 (DRAFT) - RULING T: DEFO'S 5 DISCLOSURES SIGNED; DEFO CHECKED GREEN AND FROZEN ALONE UNDER ENGINE 65a177bc

2026-10-17. datasets/defo/exceptions.yaml: the 5 ruling-N disclosures (S1, S3, S6 x2, S28) signed per ruling T and the G-LINEAGE stand-in entry marked approved (O1); old file in D:/treeroute/_moved_t_20261017/. Fingerprint d607314e8d57: quick green, deep green (R21 groups; G-FACTS, G-EPOCH pass; Y0 2004, leads [0, 1]). No engine code changed.
Frozen alone with PREREGISTRATION_DRAFT_defo.md: FREEZE_20261017T105545Z.lock.json (sha256 a59408bb2f40a8987b3cc407930ab6d944dc3fe2a92c32cb19c3a9766d26e0e9); filled PREREGISTRATION_20261017T105545Z.md (sha256 20e879c198257e5a03f8697eabc18db4bcc77c704760f09a1b90658654c2df92); verify no drift. Plan fields NOT FILLED (no plan yet, as for the other packages).
Next: `py -3.9 runner/run_headline.py defo` (headline run 4/4).

## Part 592 - HEADLINE RUN 4/4: DEFO (42 GROUPS, 92,274 SCORED CELLS, REGION ROUTER) - NOWCAST AND 1-YEAR FORECAST BOTH ADOPT THE MODEL (LOG CORRECTOR): MAE 0.00542 / 0.00541 vs NORMAL 0.00841, TREES-OFF 0.00572, PREDICT-ZERO 0.00612

2026-10-19.
- Run D:/treeroute/runs/defo/headline/20261017_d71c61f4 (engine 65a177bc, lock FREEZE_20261017T105545Z). About 47 h: derive 17 min; each training-table build 4.5-6 h; region-router passes 6.6-7.2 h.
- The model choice was log corrector unweighted at level 0.1, with 6 of 6 arms eligible; the region kind has no GLS solve.
- The lead-0 contract held byte for byte.
- **Lead 1 guard PASSED** (0.005814 vs trees-off 0.006103), so the model was adopted at the 1-year lead.
- **Scores (from the saved rows):**
  - nowcast: anomaly R2 0.052, corr2 0.017;
  - lead 1: anomaly R2 0.050, corr2 0.016;
  - the model beats predict-zero by 11.5% and its own-link trees-off by 5.2%.
- Low correlation: a cell's yearly forest loss is hard to predict; most cells lose almost nothing.
- **Final verdict** (DONE 2026-10-19 15:02:59): helps. The adopted log_c_corrector_unweighted vs its trees-off gives contrast 0.000299 [8.7e-05, 5.1e-04], band 0.000110, pooled MAE 0.0054158 vs 0.0057146. Ladder lead 1: helps, contrast 0.000307, on 369,096 common rows. Lead 1 has 103,823 test rows with an issue-row non-finite tree feature (R30: 0-filled, counted, not left out).

## Part 593 - CORAL INTO THE ENGINE (RULING U): TABLE OPTION + PORTED NEIGHBOUR ROUTER BUILT IN A COPY; TINY SMOKE RUNS END TO END (PLUMBING ONLY); GRID NO-OP PROOF PASSED ON AN EARLIER BUILD, FINAL RE-PROOF PENDING

2026-10-19.
- **Scope:** owner ruling U replaced CORAL_ENGINE_PLAN.md (28-33 agent days) with a lean design.
  - A generic table input: the package supplies per-lead feature tables with train/test marks, and the owner vouches for the feature timing.
  - The legacy neighbour router is ported with a strict pool: 150 nearest by map distance, then the 50 most similar by features; fewer than 12 rows falls back to the donor median.
  - Only train rows dated strictly before the issue date enter a pool.
  - The trees of every group in the pool are dropped (signed default).
- **Build:** D:/treeroute/coral_build/engine (workflow <id>-90f, 16 agents).
  - Reports: SPEC_TABLE_MODE.md, SPEC_NEIGHBOUR.md, SPEC_CORAL_TABLES.md, INTEGRATE_REPORT.md, BUILD_REPORT.md.
  - Engine changes: 9 new engine files, 12 shared files with gated or additive changes, and treeroute_report/table.py.
  - Build engine_code_sha256 a49009845eb7f7c5351443666e75a95c6037913aae59d3624ff71df0fe720e5e. LIVE is still 65a177bc.
- **Coral tables, tiny build (4 ecoregions, 897 rows per lead):**
  - The look-ahead canary found 0 mismatches.
  - The checker passed 52/52, and its negative control detects a one-day leak.
  - The full build has not been run (about 30 min, owner command).
- **Tiny coral smoke** (runs/coral_draft_tiny/smoke/20261019_6a40c185; 96 test rows; NO sign information). Test MAE:
  - lead 0: model 3.779, own trees-off 3.837, donor median 3.896;
  - leads 183 and 365: guard failed, declined to the identity neighbour trees-off at 7.441 / 7.132, against a donor median of 3.896 (owner item A1);
  - most guard rows had every tree dropped (69/71 and 44/60) because, with only 4 groups, pools span every group (A2).
- **Grid no-op:**
  - The four grid smokes, LIVE vs build at 20:02, are byte-identical. After the last fixes only defo was re-run, and it is identical.
  - The final four-smoke re-proof (run_noop_proof.ps1) and the full suite are pending as owner commands. The suite in the fix phase stopped at about 4%.
- **Grid no-op on the build hash a4900984 (2026-10-19, 22:10): RESULT: PASS.** The owner ran run_noop_proof.ps1. pm25, fire, defo and ndvi smokes, LIVE vs build:
  - every prediction and score file and derived.json is byte-identical (24 / 24 / 22 / 26 files);
  - every other JSON record is identical once times, pids, paths, hashes and fingerprints are removed;
  - only run.log and the phases/*/DONE markers differ.
  - Ruling V changes follow, so the proof is re-run once on the final hash (run_final_checks.ps1).
- **Ruling V applied (2026-10-19/20), and V4 built.** V4 moves the table departures to TABLE_ACCEPTED_DEPARTURES, recorded in the run record; this mirrors S21.
- **Final checks on the build** (the V4 delta touches only table_run.py):
  - full suite on 704c8aea: 3,483 passed, 33 failed, 62 xfailed. The 33 failures are exactly the 33 that fail on LIVE 65a177bc (stale package/draft tests, CRLF, pdo lag 2, matrix_dir).
  - The first suite attempt errored 620 tests because the basetemp parent folder was missing. That was a script bug.
  - Table tests 107 passed, plus the 29 isolation/adversarial tests.
  - Grid no-op proof on dd7c0984: RESULT: PASS (pm25 24, fire 24, defo 22, ndvi 26 files byte-identical; 0 must-match differ).
- **INSTALLED into LIVE 2026-10-20 01:41:** 16 changed and 20 new files, by explicit list (tools/install_into_live.py).
  - The old files were moved to engine/_moved_coral_20261020_014111 (INSTALL_MANIFEST.json).
  - **LIVE engine_code_sha256 is now dd7c0984d3044aac6cf06d7614df7bd7e8622942580a5f1f0bb08c32ed085d38.**
  - The treeroute file sets are equal. nonames, noknob, table contract and route_kinds: 110 passed from LIVE.
  - The four grid headline runs keep their engine hashes (U5).
- **V6(b) option prepared, NOT installed:** D:/treeroute/coral_build_v6b, hash 930d961c with V4. The 46 no-test groups become train-only donors. V6B_REPORT.md has counts only; no test score was compared.

## Part 594 - CORAL FULL TABLES BUILT AND PUBLISHED; PACKAGE IN LIVE; QUICK + DEEP CHECKS GREEN; FULL-DATA SMOKE RUNS END TO END (PLUMBING ONLY)

2026-10-20, owner away (the owner had asked that the remaining work be finished).
- **Full tables** (coral_tables/build_tables.py --build full; 26.4 min; peak 1.39 GB):
  - lead 0: 13,694 rows (11,347 train, 2,347 test; 94 groups; 8,157 sites); leads 183 and 365: 13,686 rows.
  - Proof: 41,066 asserts; canary 0 mismatches on 822 row-leads; replay against the legacy feature files gives max relative difference 0.
  - Independent checker: PASS 52/52. The look-ahead recompute on all 41,066 row-leads x 53 columns finds 0 differing cells.
  - make_split --check: PASS, counts unchanged from stage 1.
    - (a): 37 groups, 9,464 train, 2,312 test, 1,935 decision rows.
    - V5: 11 groups; V6: 46 groups with 1,874 train rows and 0 test rows.
- **Published** write-once to D:/treeroute/coral_build/coral_store/20261020_014201. The store root was added to protected_roots.txt by the session; owner to confirm.
- **LIVE datasets/coral_draft** (DRAFT, unsigned; fingerprint dfa07650...) points at the store.
  - check quick GREEN (G-FACTS flag: target facts unsigned).
  - check --deep GREEN on the R21 groups: Andaman Islands, Andaman Sea, Bahamas and Florida Keys, Banda Sea and Molucca Islands. The router is neighbour (R12) and the test years are 2016-2019.
- **Full-data smoke from LIVE** (runs_live_smoke, 0.4 min, exit 0, every phase DONE).
  - Pool records: 50 rows in every pool, 0 fallbacks.
  - **Disclosure:** the smoke's log prints its test verdict line, and one agent saw it while checking the log. No number from it is recorded or used. The V6 recommendation was withdrawn from the owner sheet for that reason. The tiny smoke's test MAE was also visible when V1 was decided.
- V6(b) copy (930d961c): its grid no-op proof and suite are running.
- Owner sheet: D:/treeroute/coral_build/CORAL_MORNING_SHEET.md. The pre-registration draft is updated: D:/treeroute/coral_build/PREREGISTRATION_DRAFT_coral.md.
- **V6(b) copy checked (930d961c):**
  - grid no-op proof against LIVE dd7c0984: RESULT: PASS (0 must-match differ in all four);
  - full suite: 3,500 passed, 33 failed (exactly the 33 old LIVE failures), 62 xfailed.
  - It is ready to install if the owner chooses V6(b).

## Part 595 - V6 (b) CHOSEN AND INSTALLED: 46 NO-TEST GROUPS KEPT AS TRAIN-ONLY DONORS; LIVE ENGINE 930d961c; DEEP CHECK GREEN; FULL-DATA SMOKE PLUMBING OK

2026-10-20 06:44. Owner ruling W: the owner confirmed option (b). No further grid re-runs, as the owner asked.
- **Install:** 9 changed files and 1 new file, from D:/treeroute/coral_build_v6b; old files in engine/_moved_coral_20261020_064437.
  - **LIVE engine_code_sha256 = 930d961cdfdd219c36b113174e6c865096f973068e30696850f13d5ec4a60814.**
  - Before the install, this hash had passed the grid no-op proof against dd7c0984 and the full suite (3,500 passed; the same 33 old LIVE failures).
- **Package:** the (b) split.yaml, exceptions.yaml, ingest/README.md and AUDIT_CHECKLIST.md were copied into LIVE datasets/coral_draft; the old copies are in coral_build/_moved/live_coral_draft_pre_v6b_20261020_064456.
  - make_split (b) --check on the published tables: PASS.
  - Counts: 83 kept groups (37 scored + 46 donor-only), 11,338 train and 2,312 test visits, 2,046 decision rows in 33 groups.
- **check --deep from LIVE: GREEN** (check_deep_04b9aab0fb5a.json).
  - R21 smoke groups: Andaman Islands, Andaman Sea, Austral Islands (donor-only), Bahamas and Florida Keys.
  - Router: neighbour.
- **Full-data smoke** (coral_build_v6b/runs_live_smoke, 0.3 min, exit 0, every phase DONE). Only pool records were read:
  - every pool held 50 rows, with 0 fallbacks;
  - rows with no tree left: 0/24 surface, 2/18 at the lead-183 guard, 0/14 at the lead-365 guard;
  - run_record donor_only_groups lists Austral Islands (5 train rows).
- **Remaining (owner):** matrix_dir; continuity_groups (recommended []); confirm the protected root; the signatures; then the signed package 'coral', plan, freeze and the headline run.
- **Added after review:**
  - The (b) smoke opened the test labels of 42 surveys in 3 groups. No score was read.
  - G-FACTS (target facts unsigned) is still flagged.
  - Report-only script coral_report.py (SHA-256 7fb3a477...) is tested on toy runs only: 34 passed, 1 skipped.
  - The signing tool make_signed_coral.py was dry-run only. A blank template is refused (144 items).
- **Report script 1.2.0** (SHA-256 4ce7e69e...): it now prints the 5 promised outputs (guard reference, R30/MHW NaN, month-precision pools, grid-edge picks, per-programme blocked jackknife) and both flattening edges. Toy runs only: 62 passed, 1 skipped.
- One coral_draft disclosure text was corrected: month-precision pools are counted by the report script, not the engine. The new draft fingerprint cda2b2b6 has quick and deep checks GREEN.
- The signing dry run with dummy answers works.

## Part 596 - CORAL SIGNED AND FROZEN (RULING X): PACKAGE `coral` 5b9383f0, CHECKS GREEN, PLAN HEADLINE-ELIGIBLE, LOCK FREEZE_20261020T100907Z

2026-10-20. The owner accepted all items, chose option (b) and signed as drafted, then approved the apply step. Ruling X: X1 matrix_dir approved; X2 continuity []; X3 protected root confirmed; X4 flattening edge (b); X5 signatures as drafted; X6 the Part is signed on the filled copy.
- **Report script.** coral_report.py now defaults to edge (b) (SHA-256 063be402...). Toy tests: 62 passed, 1 skipped.
- **Shape test.** tests/test_layer_shapes.py approves matrix_dir, plus the logging-only echo keyword, shown to the owner. 6 passed. The engine hash is unchanged.
- **Signing.** make_signed_coral.py --apply wrote datasets/coral (fingerprint 5b9383f0446df0f12e460cccb2bcd2e58d09fbf22b234cf2943a07aac14644c9).
  - 90 changes in 7 files; the stale-text scan is clean; Q1-Q22 are confirmed.
  - Record: D:/treeroute/coral_build/tools/signoff_records/coral_signoff_record_20261020_130714.json.
- **Continuity.** continuity_groups.yaml gained the coral entry (empty). test_packages_declarative shows only its 4 old failures.
- **Pre-registration.** Every OPEN BEFORE FREEZE marker is settled, and the U2 statement is signed. The draft was copied to engine/PREREGISTRATION_DRAFT_coral.md.
- **Checks on `coral`:**
  - quick GREEN (G-FACTS pass) and deep GREEN on the R21 groups;
  - plan: D:/treeroute/runs/coral/headline/20261020_f3b8e3da;
  - headline_eligible true, not_headline_reasons [];
  - 5 accepted departures; 46 donor-only groups; 78 overlap blocks; router neighbour; leads 183 and 365.
- **Freeze.**
  - Lock: D:/treeroute/registry/freeze/FREEZE_20261020T100907Z.lock.json (sha256 70b163cd...).
  - Filled pre-registration: registry/freeze/PREREGISTRATION_20261020T100907Z.md (sha256 2b644584...). The owner signs it.
  - Engine 930d961c.
- **Next:** the owner signs the filled Part, then the headline run (runner: py -3.9 runner/run_headline.py coral).

## Part 597 - CORAL HEADLINE RUN: NOWCAST HELPS (MAE 6.70 vs DONOR MEDIAN 8.29, PREDICT-ZERO 8.10); 183 d GUARD PASSES (7.71); 365 d DECLINES TO THE DONOR MEDIAN; SEVERE EVENTS STRONGLY FLATTENED

2026-10-20 13:15-13:52 (about 35 min).
- **Run:** D:/treeroute/runs/coral/headline/20261020_f3b8e3da; engine 930d961c; lock FREEZE_20261020T100907Z. The owner started it before signing the filled Part in chat. The Part's content was frozen and hashed at 10:09Z, before the run, and the signature is still to be written.
- **Nowcast:**
  - Adopted arcsine_corrector_gls at level 100, ratio 1.
  - Verdict helps against base__donor_median: contrast 5.21 [1.97, 8.44], band 0.918.
  - Pooled MAE 6.698 vs 8.294; corr2 0.464; predict-zero 8.100; arcsine trees-off 7.536.
- **Lead 183:**
  - The guard passes (6.679 vs the median's 6.932 on 1,554 rows).
  - Test MAE 7.710; corr2 0.139.
- **Lead 365:**
  - The guard fails (8.181 vs 7.835 on 1,283 rows), so the lead declines to the donor-row median (V1).
  - The model's own test MAE is 8.281; corr2 0.038.
- **Per programme at the nowcast** (coral_report.py, hash 063be402, matching the pre-registered hash):
  - McClanahan 35.06 vs predict-zero 54.82;
  - FRRP 7.66 vs 11.74;
  - Reef_Check 3.83 vs 3.17: predict-zero wins on 1,932 rows, as in the legacy record.
- **Flattening guard** (edge b, q75 of positive donor labels at about 22-24%; severe rows' observed mean 56-58%): mean prediction 17.8 at the nowcast, 5.6 at 183 days, 4.4 at 365 days. Severe events are under-predicted by a factor of 3 to 13. The legacy (leaky-pool) model reached about 52.
- **Correctors:** 5,915-6,384 of the 8,300 trees per bank have no corrector (fewer than 50 out-of-bag rows).
- **Tables:** D:/treeroute/runs/_headline_tables/coral (engine table builder) and .../coral/coral_report (17 files).
- **Part signed** by the owner 2026-10-20 (in chat), after the run. The signature record is D:/treeroute/registry/freeze/PREREGISTRATION_20261020T100907Z.SIGNED.md; the signed file's SHA-256 is 2b644584910b55cd785f0d6f52d11bd5df9a8899de1f66e4e54a57599fd740f4, unchanged since the freeze.

## Part 598 - COMMON RIVAL BOARD PRE-REGISTERED AND SIGNED (rulings Y, Z, AA, AC, AD); CORAL RIVALS RUN NEXT

2026-10-21. The owner signed the common-rival Part in chat:
- signed file: D:/treeroute/registry/rivals/PREREGISTRATION_rivals_common_20261021T125123Z.md (SHA-256 91c62b07dbc9505dcc3b7391cef3722ece97c29b6140de7e73e8b1b83dd95bb5);
- signature record beside it;
- harness 46d0306a.

The lean board:
- Ridge;
- RF, out of core on all rows;
- LightGBM at 255 bins, lr 0.1, patience 150, cap 800, extension to 1600 only for cap-reaching trials;
- LightGBM-Tweedie on fire, defo and coral;
- hgb_l1 on coral only.

XGBoost is dropped. The donor-only board is dropped. pm25's headline is NOT re-run (Z1, gated by P1-P15). The coral dry picks (content 5ad9502f) were locked under this code.

## Part 599 - RIVAL HARNESS BUG FIX AFTER SIGNING (rule 8 a: changes no pick, no score): EMPTY "UNSEEN" TABLE ON CORAL; HARNESS 46d0306a -> 71457aa9

2026-10-21.
- **Bug.** `score` built the group_unseen and pooled_unseen tables from rows of units not seen during design. On coral every kept group is seen_during_design (ruling W), so the frame was empty, and the engine's score_table refused it with R34 ("0 minima, 0 maxima").
- **Fix.** The unseen tables are skipped when there are no unseen rows, and a log line says so (rivals/harness.py, score). Old file: rivals_build/_moved/<stamp>_preUnseenFix/harness.py.
- **Tests.** test_review_fixes.py and test_nonames.py: 22 passed.
- **The first coral board refused at score**, after test labels had been opened. No score was computed or seen; the "ours" check had passed. That board was moved aside (rivals_build/_moved/coral_board_pre_fix599_<stamp>).
- **A new board under 71457aa9** was initialised and tuned, and locked the SAME picks (content 5ad9502f, matching the signed Part's dry picks).
- **PowerShell note.** The commands file's helper `R` (and `RV`) collide with built-in aliases (Invoke-History, Remove-Variable). It was renamed to `rivcli` in RIVALS_OWNER_COMMANDS.md.

## Part 600 - CORAL COMMON-RIVAL BOARD: NO COMMON RIVAL BEATS US SIGNIFICANTLY; THE CORAL-ONLY L1 BOOSTER (hgb_l1) BEATS US AT THE NOWCAST

2026-10-21. Board D:/treeroute/rivals/coral/20261020_f3b8e3da (harness 71457aa9; picks 5ad9502f). Verdicts are per-group paired contrasts with the run's band 0.918. d = rival MAE - our MAE.

**Nowcast, pooled test MAE (2,312 surveys):**
- ours 6.698 (corr2 0.464);
- hgb_l1 6.356 (corr2 0.521);
- LightGBM 7.146 (0.481);
- Ridge 7.198;
- Tweedie 7.255;
- RF 7.376;
- predict-zero 8.100.

**Verdicts:**
- vs Ridge, RF, LightGBM, Tweedie: CANNOT TELL at every lead;
- vs hgb_l1: **LOSES at the nowcast** (d mean -2.30 [-4.21, -0.39]);
- 183 d: ours 7.710 is the lowest pooled MAE (rivals 7.82-8.12); every verdict is CANNOT TELL;
- 365 d: ours (headline = donor median) 8.29, pinned model 8.28; rivals 7.94-8.25; CANNOT TELL; flagged timid.

**Per programme, nowcast MAE:**
- McClanahan (the 2016 event): hgb_l1 28.57, LightGBM 33.94, ours 35.06, predict-zero 54.82;
- FRRP: ours 7.66 is best (hgb_l1 8.33, LightGBM 9.08);
- Reef_Check: ours 3.83, hgb_l1 3.99, LightGBM 4.33; predict-zero 3.17 beats all.

**Reading.** hgb_l1 fits an L1 (MAE) loss and the board is MAE-ruled, so it targets the scoring rule directly. It was ruled in for coral only (C12, "timid-prone"), but at the nowcast it is not timid. Its corr2 is also higher (0.52 vs 0.46). On coral our architecture is not the best model. Its edge over the common rivals is real in pooled MAE but not significant.

## Part 601 - POST-HOC: WHY CORAL'S LAYER PICKED arcsine+GLS (6.70) OVER ITS UNWEIGHTED TWIN (6.15 ON TEST)

2026-10-21. D:/treeroute/analysis/coral_choice/EXPLANATION.md (workflow <id>-d62; skeptic corrections applied).
- **The surface margin was small but stable.** It was 0.077 MAE; GLS won in 98% of group resamples and in every surface year. The strict-lowest rule picked GLS correctly.
- **The test reversal is entirely the 2016 Indo-Pacific mass bleaching** (McClanahan, 130% of the gap).
  - Its pools held past mass-bleaching reefs (Donner 2010, 1998), which GLS down-weighted about 4x, so severe predictions came out at 22 vs 35, against a truth of 75.
  - The surface (mostly Florida 2014-15 severe rows) had almost no such pools (16 vs 105 rows), so it held no evidence.
- **No weight-model drift** (same 2012 cutoff, sigma correlation 0.996). The earlier chat claim of drift is withdrawn.
- **Next-version options (owner):** A (GLS must beat its twin beyond a band), C (a stability flag), E2 (a label-free twin-disagreement flag), E3 (always save pools). Post-hoc. The headline is unchanged.

## Part 602 - POST-HOC: ADVERSARIAL-VALIDATION TOOL CHOICE (weight tuning rows by resemblance to the target period) - NO ROBUST HONEST GAIN

2026-10-21. D:/treeroute/analysis/adv_validation (PROTOCOL.txt fixed and hashed before results; RESULT.txt with the skeptic addendum).
- **The idea changed the tool only on coral.** pm25, ndvi, defo and fire kept their picks; fire's penalty-point moves also appear in the placebo.
- **Coral:**
  - V1, the transductive upper bound (not deployable), gives 6.359 vs 6.698.
  - V2, rolling and honest, gives 6.520, but it is fragile: 6.616 with reef-site folds, and it fails the ESS gate with the literal 66-feature list.
  - V3, recency, gives 6.736, which is worse.
- **The weights tilt toward low-bleaching rows (a calendar effect), not toward look-alike conditions.**
- **Verdict:** no robust improvement. At most a weak lead for a pre-registered test in the next engine version. The headline is unchanged.

## Part 603 - POST-HOC: LABEL-FREE WAYS TO GUIDE THE TOOL CHOICE WITH TEST-PERIOD INPUTS (disagreement guard, blend)

2026-10-21. Computed from the saved test_preds and inner_preds of the 5 runs. No labels are used by the rules; labels are used only to score them post-hoc.

**Disagreement guard.** The test/surface ratio of the mean |chosen minus its weighting twin| prediction gap is checked; when it exceeds 2x, the run uses the unweighted twin.
- It fires only on coral (4.29x); pm25 1.00x, ndvi 1.19x, fire 0.90x, defo has no twin.
- Coral then gets 6.147 (vs 6.698); the others are unchanged.

**50/50 blend of the chosen arm and its weighting twin:**
- pm25 3.584 (both arms 3.588 / 3.587);
- ndvi 0.0314608 (same);
- fire 0.004409 (chosen 0.004385, +0.5%);
- coral 6.394 (vs 6.698).

**Caveat.** Both rules were inspired by the coral failure (circular on coral). They are options for the next engine version, to be pre-registered and tested on new data. The headline is unchanged.

## Part 604 - POST-HOC: 7 LABEL-FREE GUIDANCE METHODS ON 5 RUNS - ONLY THE DISAGREEMENT ALARM (M1/M2) PASSES; CIRCULAR ON CORAL

2026-10-21. D:/treeroute/analysis/guidance (PROTOCOL.txt hashed c51fc39a before results; RESULT.txt with the skeptic addendum).
- **Change in bands vs the original pick** (negative is better):

| Method | Effect | Verdict |
|---|---|---|
| M1 alarm -> twin | coral -0.600; others unchanged (never fired) | passes |
| M2 alarm -> blend | coral -0.331; others unchanged | passes |
| M3 always blend | hurts fire +1.73 | fails |
| M4 mean of eligible | hurts pm25 +1.35, defo +7.39 | fails |
| M5 learned blend | never moved | fails |
| M6 / M6s per-row chooser | hurt fire; lose to their placebo on coral | fail |

- **Caveats.**
  - The alarm was designed from the coral failure (circular).
  - Its coral gain is McClanahan 2016 alone.
  - In the one measurable wrong-fire case (fire), M1 costs 3.5 bands and M2 1.7.
- **Next-engine option:** M1/M2 plus a second safeguard (the twin must be eligible on the surface), pre-registered and judged on new problems or years. No claim from this run.

## Part 605 - TWIN-DISAGREEMENT ALARM BUILT IN ENGINE v2 (ruling AE); POST-HOC REPLAY ON THE FIVE v1 RUNS (designed after them, AE3)

2026-10-21. Built in D:/treeroute/engine_v2/engine (v2 engine hash 663ab8ef; NOT installed; LIVE is still 930d961c, which the rival boards pin). Report: D:/treeroute/engine_v2/ALARM_REPORT.txt. Replay: replay/WITH_WITHOUT.csv, recomputed independently by the skeptic.
- **Coral nowcast:** 6.698 -> 6.120 (11 of 33 month-batches fire, 737 of 2,312 rows).
  - Bleached rows: 13.37 -> 11.84. Rows with y >= 50: 53.13 -> 40.99.
  - By year: 2016 12.41 -> 10.68; 2017 3.57 -> 3.69 (worse); 2018 unchanged; 2019 4.81 -> 5.04 (worse).
- **Silent at the nowcast** of pm25 (largest ratio 1.75), ndvi (1.75), fire (1.85; twin not eligible) and defo (1.17).
- **Not replayable:** defo lead 1 and coral lead 183 (v1 saved no twin at a lead).
- **Tests:** 205 passed plus 16 new verify tests; T6/T7 toys; prediction files equal v1 when the alarm is silent. The full suite runs at install.
- **Open owner items:** a zero reference gap (built: "not tested"); where the twin's eligibility is judged at the nowcast (own best point vs the adopted point).

## Part 606 - FIRE COMMON-RIVAL BOARD: OUR MODEL RANKS BEST (corr2), BUT TIMID RIVALS (Tweedie) WIN ON MAE; PREDICT-ZERO ALSO BEATS US ON MAE

2026-10-21. Board D:/treeroute/rivals/fire/20261017_869d1f38 (harness 71457aa9; picks 84fa9432). Export 5,388 s; the lean derive took 2,197 s vs 5,841 s in the headline.

**Lead 0, pooled test MAE / corr2:**

| Model | MAE | corr2 |
|---|---|---|
| ours | 0.004385 | **0.222** (highest) |
| predict-zero | 0.004284 | - |
| Tweedie | 0.004043 | 0.198 |
| RF | 0.004266 | 0.213 |
| LightGBM | 0.004292 | 0.213 |
| Ridge raw | 0.004299 | 0.210 |
| Ridge guarded | 0.006259 | - |

- Verdicts: BEATS Ridge (guarded). CANNOT TELL vs RF and LightGBM (both flagged TIMID). LOSES to Tweedie (TIMID).

**Leads 6 and 12:** our headline (declined to the normal) 0.00631; our pinned model 0.00452 / 0.00450 (corr2 0.214, the highest).
- Ridge, RF and LightGBM also failed their guards, so they are IDENTICAL to ours.
- Tweedie passed: 0.00416 / 0.00412 (corr2 0.171 / 0.169), so we LOSE (TIMID rival win).

**Reading.** On fire the MAE winner is the model that predicts near zero (Tweedie: hit 0.968; predict-zero beats every model but Tweedie). Our model ranks fire risk best (corr2). This is "MAE ranks timidity" again; report MAE and corr2 together.
- **Part 606 addendum.** On active fire cells (y > 0; 1,759 rows, 33 regions), ours beats Tweedie: MAE 0.191 vs 0.201. The per-region contrast is +0.0047 [+0.0024, +0.0071], and ours is better in 25 of 33 regions. This is an outcome-conditional stratum, reported beside the pooled loss. The owner asked that it be in the paper: engine/PAPER_NOTES_RIVALS.md.
- **Part 605 addendum (ruling AF built, 2026-10-21).** At the nowcast, the twin's eligibility is now judged at the adopted point (alarm.py twin_eligible_at_point). Every record names its rulings, AE1 and AF1-AF3.
  - Engine v2 hash 88f4db2c (was 663ab8ef). Not installed; LIVE is still 930d961c.
  - Tests: 10 new unit tests and 2 pipeline toys (split/reverse). 86 of 86 passed in the affected re-run.
  - Replay re-run: identical numbers on all 5 runs (coral 6.698 -> 6.120); AF2 changes no twin's eligibility there.
  - Skeptic: one minor note (decline_baseline_key could also check adoption.json's lock hash). Not blocking.

## Part 607 - HUMAN-RIVAL TOOL (PART A: coral, defo, PM2.5, NDVI) BUILT; TOY TESTS PASS; PART A DRAFT READY; NO REAL-DATA RUN YET

2026-10-22. D:/treeroute/human_rivals_build (workflow <id>-e46; tool hash 8f66da6a). Plan RIVALS_PLAN_HUMAN.md; ruling AB.
- **Tests:** 224 passed and 4 skipped (real-data); HUMAN_REAL registry checks 11 passed; review tests 60 passed (12 former xfails fixed).
- **Nothing ran on real data**, because the pm25 common-rival export was using the PC.
- **Files:** PREREGISTRATION_DRAFT_human_partA.txt (DRAFT, unsigned) and HUMAN_OWNER_COMMANDS.txt (ordered around the common runs).
- **Six owner decisions before signing:**
  1. EAC4 download (D1) or plan R2 (MERRA-2 as the parity row);
  2. NDVI H1 standardize (the review recommends true);
  3. H1's missing-climate rule;
  4. the coral BAA alert rule;
  5. the VT0007 class-edge and water-filling wording;
  6. the BoM ACCESS-S archive check.
- **Order constraint:** make the human `slim` copies of each common export BEFORE that export is deleted.

## Part 608 - RIVAL HARNESS FIX AFTER SIGNING (rule 8 a: no pick exists for pm25; bounded targets unchanged): OPEN UPPER BOUND; HARNESS 71457aa9 -> b6ea97b7

2026-10-22.
- **Bug.** board.json stores the run's legal range, and an open bound (pm25 R28: "never negative; no upper bound" = (0, inf)) is written as null by the canonical JSON writer. tune / refit / score read it back with float(None) and crashed: TypeError at harness.py export_lead.
- **What it hit.** Both the owner's pm25 chain and the agent's follower stopped at `tune`, before any pick or any test label.
- **Fix.** A new `board_legal(board)` reads null as -inf/+inf; it is used at the four read sites. Bounded targets (coral, fire, defo, ndvi) take the same values as before. Old file: rivals_build/_moved/<stamp>_preLegalFix/harness.py.
- **Tests.** A unit check of board_legal; test_review_fixes, test_tuning_rules and test_nonames: 35 passed.
- **The pm25 board** (init only, no trials) is moved aside and re-initialised under b6ea97b7. Its export (ACCEPTED_ALL_LEADS, P1-P15) is unchanged and reused.

## Part 609 - DISK CLEANUP, TIER 1 STAGED (no result, board, run or engine file changed; nothing deleted by the agent)

2026-10-22. The owner asked to free disk (D: had 12.2 GB free; defo and NDVI rival boards need ~15-25 GB).
- **Audit.** Workflow <id>-bc7 classified ~130 items (every D: folder >= 0.3 GB, ~370 GB, plus the pipeline's own temp folders). Each "safe" verdict was attacked by skeptics: 2 lenses (pending work, research record) for D:\treeroute, 1 for the rest. Full results: D:\treeroute\disk_cleanup\CLEANUP_REPORT.md.
- **Tier 1 staged (27.62 GB, 171 items)**, moved with a rename into D:\_TO_DELETE_20261022 by D:\treeroute\disk_cleanup\stage_tier1.py. Manifest: MOVED_MANIFEST_20261022_082821.csv. Undo: RESTORE_20261022_082821.ps1.
  - Pytest basetemp SUBFOLDERS only: rivals_build\pt\{zfin, aa, ac, z2, fix, aafix, z, tests, export, legalfix, fix598, harness}, coral_build\{pt, _pytest_*}, coral_build_v6b\_pt, install_20261015\pt, and human_rivals_build\pt\<6>\<basetemps>.
  - The two synthetic 1 GB ndvi_width.f32 files (section 7 of the commands file).
  - rivals_build\_moved\{20261021_z2_bench_data, skeptic_rc_probe}.
  - The fire board's fit-set .f32/.index.parquet copies (board done).
  - rival_export\_engine_run_root\fire (resume checkpoints).
  - D:\fire\pool_features.f32 (a stale Aug-28 scratch memmap).
- **Kept because the skeptics refuted them.**
  - Every loose log or json cited by the signed rival Part, the reports or the human Part A draft (e.g. pt\zfin\full1.log, heavy1\...\ooc10_ram.json, pt\aa\coral_bins_probe.json).
  - pt\fix\_export_l6 and pt\harness\dry, which back report claims.
  - The fire fit-set lead_*.json files, the only record of the fit-set sha256.
  - engine_v2\pt, read by the v2 review suite.
  - rival_export\fire (human fire Part B needs a slim first).
  - review_tests* code.
  - The coral_build noop and smoke folders, _moved_install_20261015 (it holds the only copies of two check reports whose hashes freeze locks pin), runs_final_check and runs_gate.
- **Checked after the move:** 20 cited files and folders are still in place, and the running pm25 board is unaffected (it was at refit lead 0).
- **Owner step:** delete D:\_TO_DELETE_20261022 to free the space. Tiers 2 and 3 (old experiments ~64 GB, unused raw downloads ~74 GB) are listed in CLEANUP_REPORT.md for the owner to decide.

## Part 610 - PM2.5 COMMON-RIVAL BOARD (pre-registered, rival Part 598; board D:/treeroute/rivals/pm25/20261007_74e67609)

2026-10-22, 09:27.
- **Run.** The headline run 20261007_74e67609 was not re-run (ruling Z1). The export passed P1-P15 at every lead, and the board prints the ACCEPTED ENGINE DIFFERENCE line. Harness b6ea97b7 (Part 608). Steps: tune 1 h 10 min, lock, refits 0/6/12 about 1 h, scores and board under 1 min. 127 groups; band 0.0462.
- **Locked picks** (picks.json sha 4b567830; content 714f7e2e; all log_c):
  - Ridge alpha 1000;
  - RF max_features 0.5, min_samples_leaf 5, 300 trees (out of core);
  - LightGBM num_leaves 127, min_child_samples 200, 961 rounds (it hit the 800 cap and was extended under AC2).
- **Verdicts (MAE; d = rival - ours, per-group jackknife).**
  - Lead 0: ours 3.588.
    - Ridge 3.426: CANNOT TELL (d -0.162 [-0.342, +0.019]).
    - RF 3.692: BEATS.
    - LightGBM 3.552: CANNOT TELL.
  - Lead 6: ours 3.846 (headline = pinned).
    - Ridge 3.600: **LOSES** (-0.247 [-0.422, -0.071]).
    - RF 3.822: CANNOT TELL.
    - LightGBM: its own guard FAILED. Its guarded answer 4.054 is BEATEN by ours; raw 3.842 is EQUIVALENT.
  - Lead 12: our headline is the normal, 4.084 (our guard declined); our pinned model is 3.840.
    - Guarded vs headline: ours LOSES to all three (Ridge 3.656, RF 3.890, LightGBM 3.844).
    - Raw vs raw: Ridge LOSES (-0.184 [-0.326, -0.043]); RF BEATS (+0.050); LightGBM EQUIVALENT.
  - corr2: ours 0.852 / 0.830 / 0.831. Ridge 0.852 / 0.841 / 0.839; RF 0.842 / 0.833 / 0.828; LightGBM 0.849 / 0.831 / 0.828.
  - No TIMID flags.
- **Reading.**
  - On PM2.5 the strongest rival is the simplest one: Ridge on the log link with the normal as offset. It is significantly better at leads 6 and 12, and better but not significant at the nowcast.
  - Against the tree rivals ours is level or better, except where our lead-12 guard declined to the normal.
  - The mechanism is NOT yet tested. Hypothesis: PM2.5 has strong multi-year trends (falling in China/US) that a linear model extrapolates and trees cannot. To check: the residual by test year and the residual vs the train-period trend; a post-hoc check, labelled so.
- **NDVI smoke check.** The smoke run finished, 327.8 s, folder rivals_build/runs/ndvi/smoke/20261022_9b1ee548. The follower then stopped on ITS OWN parsing bug: it read the folder with the trailing " in 327.8 s". The follower is fixed. The export and P15 are re-run by rivals_build/finish_ndvi_smoke.ps1.
- **Addendum (09:38).** NDVI smoke check PASSED. The export passed P1-P14 at leads 0/6/12, then P15 pass (log: rivals_build/logs_owner/finish_ndvi_smoke_*.log). D: had 32.6 GB free.
- The defo common-rival board was launched by the agent at about 09:45, at the owner's request to start the remaining scripts. Script: rivals_build/follow_defo.ps1 (section 5 steps, resumable; stops at the first failure; pauses before refit 1 if D: < 9 GB; deletes nothing).

## Part 611 - IS RIDGE'S PM2.5 WIN LEAK-FREE AND FAIR? AUDIT (post-hoc; read-only; workflow <id>-4a7)

2026-10-22. The owner asked whether Ridge's win (Part 610) could come from a leak.
- **Method.** 4 audits (code: data path; code: fit/tune/score; data: byte-level time alignment; data: model diagnosis), then 2 skeptics (leak lens, fairness lens) who re-checked the key claims on the files. Results: D:/treeroute/analysis/pm25_ridge_audit/ (RESULT.json, SUMMARY.txt, scripts/).
- **Verdict: NO LEAK, and the comparison is fair** (all 6 agents; both skeptics "real, high confidence").
  - All 6 history columns were recomputed from labels in all 127 groups at leads 0/6/12. They match the rule "newest label = t-1 at lead 0, t-L at lead L" on 100% of training and test rows; a version including y(t) matches only chance ties.
  - All 116 driver columns were compared with D:/monthly_panel and D:/gfed_burn (14,732 group x column cells): 100% match at the R8 lag.
  - At leads 6/12 every feature equals the lead-0 value at the issue step (91,439/91,440 and 91,438/91,440 rows; the rest have no issue row).
  - The normal on test rows equals the per unit-month mean of labels up to the cut (max diff 0).
  - Training labels end at the run's fit cuts (24240/24235/24229).
  - Picks were locked at 05:21:41Z; test labels were first opened at 06:27:13Z.
  - Re-scoring from the saved row-level predictions reproduces the board exactly.
  - Ridge rebuilt from sufficient statistics of the .f32 fit sets matches model_ridge.json (coefficients to 1e-9 relative).
- **Fairness variants** (exact refits; d = Ridge - ours; 95% group-jackknife):
  - Leave-one-group-out: lead 0 d -0.136; lead 6 d -0.238 [-0.412, -0.063]; lead 12 -0.17x.
  - Strict variant, where Ridge sees exactly what our router sees (group removed, the scored unit's own rows added back, no ctx:lat, no missing flags): lead 0 d -0.139 [-0.322, +0.044]; lead 6 d -0.237 [-0.413, -0.060] (85/127 groups); lead 12 d -0.175 [-0.314, -0.037].
  - Every extra advantage Ridge had moves MAE by <= 0.026. **No verdict changes.**
- **Why Ridge wins** (post-hoc; tested by ablation): a LINEAR reading of the history block that both models receive.
  - Top standardised coefficients: hist_mean_all -0.32, hist_mean_60 +0.20, hist_mean_12 +0.12. That is "recent level minus long-run level", which pulls the forecast below the 2003-2019 normal (frozen at 2019) where PM2.5 had been falling.
  - Ridge refit WITHOUT the 6 history columns loses its edge: lead 0 d +0.147 [+0.067, +0.228] (ours better); lead 6 -0.028 [-0.073, +0.018]; lead 12 +0.008 [-0.042, +0.057].
  - Our trees get the same history columns in raw ug/m3, are trained leave-one-region-out and cannot extrapolate; our router sees only tree answers. It is a model-form difference, not a data advantage.
  - A naive recent-level baseline (last5_normal 3.97/4.05/4.12) is worse than ours.
- **Where.**
  - Lead 0: concentrated in China. north_china_plain: ours 16.30 vs Ridge 6.85; our 2023 forecast ~57.6 vs observed 40.1, normal 62.4. Without the 3 Chinese groups, d -0.042 [-0.128, +0.043] and Ridge wins 65/127 groups (a coin flip).
  - Leads 6/12: broad. Ridge wins 85/127 and still wins without China (lead 6 d -0.130 [-0.192, -0.069]; lead 12 -0.093 [-0.153, -0.034]).
  - Ridge's edge grows with the pre-2020 decline slope (Spearman -0.26 to -0.31) and with test year (lead 0 by year: -0.04 in 2020 to -0.31 in 2023).
- **Visible before the test period (pre-registration safe).** Inner window at lead 0: Ridge 3.3275 vs our adopted arm 3.3395. Guard window at lead 6: Ridge 3.356 vs 3.470.
- **Open owner points** (none changes a verdict):
  1. Reading of rule AA1: may a pooled rival use the test group's other units? Measured effect 0.010-0.026.
  2. Should slow climate indices that move the level linearly in 2020-23 (pdo, sst_anom_global_tropical_mean, nino34) be reviewed as trend proxies? Both models get them; they move Ridge about -2 to -6% on test rows.
  3. R11 lets training labels reach the first test issue step at leads 6/12. Same for both; confirm it is the intended convention.
  4. Disclosure: training-row normals are in-sample (R15), the same for both.
- **Lesson for the engine (NOT applied; any change would need a new pre-registration and new data):** our model does not use unit-relative recent level. On strongly trending units it stays anchored to a stale normal.
- **Addendum (owner question: would a lambda help?).** The engine already tunes one.
  - The per-unit router is a ridge regression. Its inputs are an intercept and the normal (both unpenalised), plus ctx columns and tree answers (penalised).
  - R26 searches 7 strengths (0.1-100) x 5 context/tree ratios (0.0625-1) on the 2017-19 inner window.
  - pm25 adopted arm log_c_corrector_unweighted, inner MAE by strength (ratio has <= 0.0007 effect): 0.1: 3.556; 1: 3.502; 10: 3.361; **30: 3.340 (picked, interior optimum)**; 100: 3.380.
  - So lambda is worth 0.22 MAE to us and is already used. Ridge's own alpha was worth only 0.01 (3.337 to 3.327).
  - The remaining gap is the INPUTS: the router never sees the history columns. No lambda value can add that signal. Source: run inner_candidates.csv.

## Part 612 - PM2.5: OURS vs RIDGE ON LOCATIONS WITHOUT A FALLING TREND (POST-HOC, owner question; read-only)

2026-10-22. Script: D:/treeroute/analysis/pm25_ridge_audit/trend_strata.py, plus _robust.py; outputs in *_out.txt and trend_strata.csv.
- **Method.** Each of the 1,905 scored units is grouped by information known BEFORE the test years:
  - S1: OLS slope of its yearly mean over 2013-19, in %/yr;
  - S2: its 2017-19 mean departure from its 2003-19 unit-month normal.
  - A test-years grouping (S3) is OUTCOME-CONDITIONAL and is only printed beside.
  - d = Ridge MAE - ours (>0 = ours better), averaged over regions, with a LOGO jackknife 95% interval (board method). The all-rows row reproduces the board exactly at every lead.
  - Cut points are mine (+/-1 and +/-3 %/yr). Terciles and Spearman give the same picture. Many strata: no multiplicity correction.
- **Nowcast (lead 0): the owner's idea holds.** Ridge's nowcast advantage comes from falling places only.
  - Falling >3%/yr (298 units / 48 regions): d -0.50 [-0.96, -0.04].
  - Flat within 1%/yr (604/101): d +0.008 [-0.09, +0.11], a tie; ours better in 344/604 units.
  - Rising 1-3%: +0.057 (n.s.; 213/341).
  - Rising >3%: **+0.22 [+0.09, +0.35], ours significantly better** (74/88 units).
  - Terciles: falling -0.54, middle +0.006, rising +0.051.
- **6 months: mostly the trend, but not only.**
  - Falling >3%: -0.55 (sig); falling 1-3%: -0.27 (sig).
  - Flat: **-0.10 [-0.165, -0.040]**, Ridge still slightly better.
  - Rising: tie (-0.06 and -0.004, n.s.).
  - Terciles: -0.57 / -0.09 / -0.08.
- **12 months.**
  - Our answer (the normal; the guard failed): Ridge better everywhere except rising places (ties).
  - Our rejected model (secondary): falling >3% -0.47 (sig); flat **-0.075 [-0.135, -0.015]**; rising +0.004 / +0.043 (ties). Terciles -0.46 / -0.09 / -0.01.
- **Threshold-free check:** Spearman(unit pre-test slope, gap) = +0.31 (lead 0), +0.24 (lead 6), +0.52 (lead 12 answer) and +0.24 (lead 12 model).
- **Reading.**
  - At the nowcast our architecture is level with Ridge where PM2.5 is flat, and better where it was rising.
  - At 6 and 12 months the falling trend explains most, but not all, of Ridge's lead. On flat places Ridge keeps a small edge (~0.08-0.10).
- **Outcome-conditional S3** (label it so if used): on units whose 2020-23 level stayed within 5% of normal, ours is better at the nowcast (+0.127 [+0.063, +0.191]) and ties at 6/12 months.
- **Addendum: why ours beats Ridge on rising places at the nowcast** (rising_why.py / _out.txt). Post-hoc. A "spike month" is defined by the outcome (y above the unit's own 2003-19 90th percentile), so it is conditional.
  1. **Spikes.** The rising >3%/yr units are mostly fire, smoke and dust regions: BC inland rainforest, Australian bushfire belt, Yakutia larch, Amazon, Beni savanna, Sahel, Arabian Peninsula, Tanezrouft.
     - Rising units: spike months, ours 10.52 vs Ridge 11.15 (+0.62); ordinary months, +0.09.
     - Spike months favour ours in EVERY trend group: flat +1.63, falling >3% +1.87, rising 1-3% +0.74.
     - Ordinary months favour Ridge on flat (-0.15) and falling (-1.12) units.
     - So the trees' strength is the big event months; Ridge's strength is the level of ordinary months.
  2. **Ridge pulls everything down.** One pooled linear model learns a downward shift (mostly from the falling regions and slow climate indices) and applies it everywhere.
     - Ridge bias: flat units -1.06 (ours +0.29); rising 1-3% -1.23 (ours -0.53).
     - On rising units this pull goes the wrong way (2020: Ridge -1.60 vs ours -1.24).
  - The rising >3% group is small (88 units / 26 regions); 5 of its 26 regions favour Ridge.
- **Addendum: spike months, all units, with CIs** (spike_months.py; outcome-conditional; thresholds p75/p90/p95).
  - Ours beats Ridge on spikes at every lead and threshold. At p90:
    - lead 0: +1.35 [+0.99, +1.71];
    - lead 6: +0.82 [+0.57, +1.07];
    - lead 12, our answer: +1.04 [+0.81, +1.28];
    - lead 12, our model: +0.52 [+0.33, +0.70].
  - Ridge wins ordinary months at every lead.
  - **BUT the plain normal also beats Ridge on spikes.** Ours vs the normal on spikes: lead 0 +0.03 [-0.18, +0.25] (tie); lead 6 -0.53 [-0.75, -0.32]; lead 12 model -0.53 [-0.74, -0.32].
  - **Correction of the agent's earlier chat explanation:** "the trees push spike forecasts up more" is NOT supported against the normal. The spike-month win over Ridge comes mostly from Ridge's systematic downward shift (bias on spikes: Ridge -9.84, normal -8.63, ours -8.41 at the nowcast).

## Part 613 - HUMAN-RIVAL TOOL, PRE-SIGNING CHANGES UNDER RULING AG (no human score exists; nothing ran on real data)

2026-10-22. Ruling AG (OWNER_RULINGS section AG): PM2.5 P row = MERRA-2 (PLAN R2); NDVI H1 standardize true; the rest of Part A section 11 confirmed; BoM ACCESS-S rejected in writing; human steps 2-4 after the defo board; older-harness boards accepted (AG5).
- **Problem found before any run.** The human tool pinned the common harness 71457aa9. After the Part 608 fix the importable harness is b6ea97b7, so every human command would have refused. The build config was also stale: the toy flow tests had refused since Part 608, giving 18 errors, which were found and fixed here.
- **Change (AG5).** The tool pins b6ea97b7 for the harness it imports (strict, as before). A common board may be under the pin, OR under an older harness listed in the new config mapping common_harness_accepted_boards {sha256: written reason}.
  - An accepted board must have a legal range bounded at both ends: AG5's premise, checked generically.
  - The reason must be a non-empty string; the pin itself may not be listed.
  - init records common_board.harness_accepted_as.
  - join checks that the human board's harness equals the pin, that the recorded common-board harness and acceptance match, and prints a provenance section in RIVALS_TABLE.md (fire, which is pending, included).
  - cli shas prints the common board's harness and acceptance.
  - Files: rivals_human/config.py, common.py, board.py, join.py, cli.py; tests hooks.py, test_h01, the new test_h01b, test_h15 (+4 cases).
  - Configs: build human_rivals.yaml re-pinned, deliberately with no acceptance; production and DRY created from the drafts with the mapping. SPEC_HUMAN.txt has an amendment note.
- **AG5 claim verified by both reviewers:**
  - The harness diff is board_legal plus its 4 call sites only.
  - The old harness.py with today's other files hashes to exactly 71457aa9.
  - The coral/fire boards store float bounds [0,100] / [0,1], so the old and new code pass identical tuples.
  - Both boards were finished before the fix.
- **Registry:** ndvi.yaml standardize false -> true (AG2).
- **Part A draft:** pin b6ea97b7 plus the accepted older harness; section 11 decisions recorded; the old draft is kept as _moved/PREREGISTRATION_DRAFT_human_partA.before_AG_20261022.txt.
- **Review:** workflow <id>-f85 (code + protocol lenses): both "ok_with_minor". Both should-fix items (join provenance, missing tests) and the minor ones (bounded-range check, string reason, init/join acceptance match, docstrings, yaml headers, shas, spec note) were applied.
- **Tests:**
  - Targeted: 30 passed (h01, h01b, h15).
  - Full suite before the review fixes: 231 passed, 4 skipped (real-data).
  - Review tests: 60 passed.
  - Final full re-run: see the addendum.
- **Real-board check** (read-only, check_common_board): production/DRY accept coral and fire with the AG5 reason, pm25 = pin; the build config refuses coral and fire (intended).
- **Human tool code hash:** 8f66da6a -> 64dff6b5ddca26b9 (re-printed at signing).
- **Runner prepared:** D:/treeroute/rivals_build/follow_human_pre.ps1 (steps 2-4 after the defo board; no EAC4; reads no test label).
- **Addendum (final test run, defo export running).** rivals_human tests: 209 passed, 4 skipped, 27 setup errors. All 27 are one harness RAM-guard refusal in the toy-flow fixtures ("lgbm needs about 2.00 GiB ... 1.65 GiB is available"), caused by the defo export holding memory, NOT a code failure. Review tests: 60 passed. The full suite before the review fixes was 231 passed. The targeted run after the fixes was 30 passed, including the full table toy flow and join.
  - To close the gap, follow_human_pre.ps1 now re-runs the full suite and the review tests FIRST, with the machine free after the defo board, and stops on any failure. Launched 2026-10-22 about 14:20 local; it waits for the defo board.

## Defo common-rival board: progress note (no result yet)

2026-10-23.
- **Overnight.**
  - Export: lead 0 P1-P14 pass at 20:00 on 2026-10-22; lead 1 followed.
  - Then init, probe, tune (13,936 s) and lock.
  - Picks are locked (picks.json sha 08b16787; content e8063065): Ridge log_c alpha 1e6 (flag edge_alpha), RF log_c mf0.5/leaf5, LightGBM log_c leaves31/mcs200 at 253 rounds, Tweedie (own log) leaves127/mcs20/power1.5 at 1594 (extended under AC2).
- **Refit lead 0.** Ridge was done. RF REFUSED at 06:56 on its RAM guard: "needs about 4.50 GiB ... 4.40 GiB is available". It was a memory shortfall, not an error, and no test label had been opened.
- **Runner fix.** follow_defo.ps1 now skips probe, tune and lock once picks.json.lock.json exists (lock is write-once and would refuse), and skips a lead already scored. A stray backspace character, introduced by the agent's edit, was found and fixed before launch.
- **Restart.** Relaunched 06:57 with 9.7 GB free. The human pre-signing runner (it had stopped on seeing STOPPED, by design) was relaunched after it.
- **07:46.**
  - Lead 0 refit and score are done: ours vs Ridge BEATS, RF CANNOT TELL, LightGBM EQUIVALENT, Tweedie BEATS. Reported with the board.
  - Refit lead 1 hit the same RAM guard (Ridge's two fit-set copies stay in memory within the process; RF then needed 4.5 GiB with 1.48 available).
  - follow_defo.ps1 now retries a refit up to 2 times in a fresh process when it sees exactly that RAM-guard refusal; finished learners are skipped under the same hash. Any other failure still stops.
  - Relaunched 07:46. The human runner kept waiting, because the new defo log is the latest.

## Part 614 - DEFO COMMON-RIVAL BOARD (pre-registered, rival Part 598; board D:/treeroute/rivals/defo/20261017_d71c61f4)

2026-10-23, 09:12.
- **Run.** Engine identity checks I1-I9 passed with no accepted difference. Harness b6ea97b7. 42 groups; band 0.000110.
  - Picks: Ridge log_c alpha 1e6 (edge flag); RF log_c mf0.5/leaf5; LightGBM log_c leaves31/mcs200 at 253; Tweedie own-log leaves127/mcs20/p1.5 at 1594.
  - Two RAM-guard stops were resumed (see the progress note).
- **Nowcast** (ours 0.00542 = headline; -35.6% vs the normal; predict-zero 0.00612):
  - Ridge 0.00581: **BEATS** (d +0.00039 [+0.00009, +0.00069]).
  - RF 0.00549: CANNOT TELL (+0.000073 [+0.000030, +0.000115]: positive, but under/over the band).
  - LightGBM 0.00547: EQUIVALENT.
  - Tweedie 0.00631: **BEATS**.
  - **Ours has the lowest MAE of all.**
  - corr2: ours 0.0169; LightGBM 0.0193, RF 0.0172, Tweedie 0.0109, Ridge 0.0015.
  - Hit rate: ours 0.834 (the highest; rivals 0.757-0.827).
- **1 year** (ours 0.00541, guard passed):
  - Ridge 0.00567: **BEATS** (+0.00026 [+0.00004, +0.00048]).
  - RF 0.00538: EQUIVALENT, TIMID rival win.
  - LightGBM 0.00536: EQUIVALENT, TIMID rival win (d -0.00005 [-0.00009, -0.00001], inside the band).
  - Tweedie 0.00620: **BEATS**.
  - corr2: ours 0.0158; LightGBM 0.0191, RF 0.0175, Ridge 0.0107, Tweedie 0.0101.
  - Hit rate: ours 0.835; LightGBM 0.837, RF 0.835.
- **Reading.**
  - On defo, our model is never beaten by a rival. It beats Ridge and Tweedie at both leads and is equivalent to (or cannot be told apart from) RF and LightGBM.
  - At 1 year the tree rivals' nominal edges are inside the band and flagged TIMID. On corr2 the two tree rivals are slightly higher.
  - Contrast with PM2.5: here Ridge is clearly worst-but-one. That is consistent with Part 611: no smooth, unit-relative level drift for a linear contrast to exploit (post-hoc reading, not tested here).
- **Owner (disk, section 7).** The 4 defo fit-set copies in rivals_scratch/defo (about 12.5 GB) may be deleted now. Keep the defo EXPORT until the human runner's defo slim (step 4) has run.
- **Human runner incident (2026-10-23 09:27; agent error).** After the defo board, follow_human_pre.ps1 ran the full human suite and the review tests: both PASSED with the machine free, which closes Part 613's 27 RAM-guard setup errors.
  - **Not one step then ran**, although the log ends "HUMAN PRE-SIGNING STEPS 2-4 DONE". The step function was named `H`, which PowerShell resolves to its built-in alias for Get-History (alias before function), so every step silently called Get-History. Nothing was written. That "DONE" line in logs_owner/follow_human_20261023_065722.log is FALSE.
  - **Fix:** renamed to Invoke-HumanStep; the script refuses unless the name resolves to its own function, and refuses "DONE" unless at least 30 steps ran.
  - Re-launched at about 09:35.
- **Adapter fix (2026-10-23 09:45; before signing; no index table had been written).** O7 `adapt crw_dhw` refused inside its D6 check: "ct5km_climatology_v3.1.nc: no climatology pixel centre at (-17.9750, -38.6750)".
  - **Cause:** OfficialMmm took the grid step from lat[1] - lat[0] = -0.04998779 (NOAA stores float32 centres). Over 2,160 rows the error reached a whole row, so the lookup landed on -18.025 and refused.
  - **Fix:** step over the full span, (ax[-1] - ax[0]) / (n - 1). The same latent pattern in pm25_reanalysis.Grid was fixed too; MERRA-2's float64 axes give an identical step there.
  - **Checks:** on the real file the failing site maps to (2159, 2826), MMM 26.93; every sampled row and column maps back to itself.
  - **Tests:** new regression test test_h16_mmm_index_holds_on_a_global_float32_axis; coral and PM2.5 adapter tests 45 passed.
  - The tool code hash changed again (re-printed at signing). The product manifests written at 09:43-09:45 record the earlier tool hash; they only hash products, and no later step compares it.
  - Runner restarted at about 09:55; it re-runs the full suite first.
- **Coral D6 (2026-10-23 10:02, before any index table was written).** O7 `adapt crw_dhw` refused: "D6: 24 of 300 site-days differ from NOAA".
  - **Diagnosis** (D:/treeroute/analysis/coral_d6/, scripts and outputs).
    - Our SST equals NOAA's served analysed_sst on the check day at 300/300 site-days. The agent's first script compared the wrong day (its own off-by-one) and was corrected before any conclusion.
    - 16 of the 24 were float arithmetic: NOAA HotSpot 1.00 computed as 0.99999.
    - NOAA's 2-decimal arithmetic gives DHW 292/300, BAA7d 300/300 and HotSpot 300/300 (the other alert rule: 288/300, confirming AG3's HotSpot rule).
    - The 8 left are not explained by SST, MMM (+/-0.30 shifts) or a one-day window shift. The most likely cause is NOAA's archive using an earlier SST record.
  - **Ruling AH:** the hundredths arithmetic (AH1); pass rule = BAA and HotSpot on every site-day, DHW on >= 97% (registry d6_min_dhw_equal_share 0.97); the 8 listed.
  - **Code:** adapters/coral_crw.py (heat_stats hundredths, d6_check rule, the build logs every accepted difference); tests oracles.py (hundredths), test_h16 (2-decimal toy SST + the new test_h16_a_hotspot_of_exactly_one_degree_counts_in_float32).
  - **Real data:** d6_check with 0.97 passes; report d6_report_after_fix.json.
- **Coral replay (2026-10-23 10:58; D6 had passed under AH, with the 8 differences logged).** The replay check refused: "row 066_-28.1092_153.4758|2008-08-03: package rule gives hs_max_84 -2.51902198792, the export holds -2.5190217495" (difference 2.4e-7).
  - **Cause:** the export stores x__dhw_84, x__hs_max_84 and c__ctx_mmm as float32 (checked in the slim schema). The replay subtracts the float32 MMM, and the old tolerance was rel 1e-9.
  - **Fix:** with float32 columns, the tolerance is one float32 step of each magnitude involved (hs_max: MMM + value; DHW: 84/7 MMM steps + value). It stays at 1e-9 for float64 columns. The report now records max_abs_diff_dhw / hs_max.
  - Tests: coral 28 passed; the tamper test still refuses.
  - Runner restarted.
- **Coral outlook (2026-10-23 11:13).** crw_dhw is BUILT: D6 passed under AH, the replay passed, and the index tables were written. Then O8 `adapt crw_outlook` refused: "...icwk20110703...: time 2011-07-10 is not the file name's icwk 2011-07-03".
  - **Scan of all 1,984 Outlook files** (analysis/coral_outlook/outlook_dates.py): `time` = icwk + 7 days in 1,984/1,984; Week_01 starts at icwk + 1 and Week_20 at icwk + 134 in 1,984/1,984. It is NOAA's convention, not damage; the adapter's assumption time == icwk was wrong.
  - **Fix:** the adapter asserts time == icwk + 7 (OUTLOOK_TIME_MINUS_ICWK). It takes the issue as available from that `time`, the later and conservative date, so info_end = icwk + 7 and the reported "issue minus our issue" uses it.
  - This is an A-tier row (advantaged horizon, never decides): its disclosed lead is now 49-56 / ~232 days after our issue date (was 42-49 / ~225). The registry label and the Part A draft are updated.
  - Toy writers (time = icwk + 7) and tests updated; coral tests 28 passed.

## Part 615 - DISK CLEANUP, ZERO-RISK TIER STAGED (owner, 2026-10-23: free disk space only where nothing is at risk)

- **Staged:** 35 items, 84.49 GB, moved (renamed) into D:\_TO_DELETE_20261023 by D:\treeroute\disk_cleanup\stage_zero_risk.py. Nothing was deleted by the agent.
  - Manifest: MOVED_MANIFEST_zero_risk_20261023_175235.csv. Undo: RESTORE_zero_risk_20261023_175235.ps1.
- **Selection rule:** only SAFE_CACHE / high-confidence verdicts of the 2026-10-22 audit (<id>-bc7) that their skeptic did not refute; no running process referenced any path.
  - **B, scratch caches of old experiments:** idea_leaf, regime_test_frames, smart_trainer_cache, bundle_transfer_*.npz (3), lag_compare_frames, regime_stream_test_*.parquet (3), ideas_smoke, smart_combiner_smoke500, thar_lag_Pall.npy.
  - **C, downloads never used by any model, or raw downloads whose processed copy is kept:** pml_et (30.6), ndvi_drivers\{hansen (old v1.11 duplicate), crops, cirrmap, covid}, esacci_sm (raw daily; the monthly copy is kept), env_noauth_dl (the 931 sidecars are kept), drought_dl, coral GHS-POP / GHS-BUILT zips (the processed parquets are kept).
  - **A, the pm25 fit-set copies:** were already gone (the owner had deleted them).
- **Excluded as not zero-risk:** old experiment results, medium-confidence items, D:\data, every source read by the engine, rivals or human rivals, the fire and defo exports, and personal files.
- **Owner step:** delete D:\_TO_DELETE_20261023. D: then has about 115 GB free, so NDVI can run all three leads without pausing for deletions.
- **Defo prep (2026-10-23).** The coral and PM2.5 pre-signing steps finished: the coral DRY picks content is ebef5359; the pm25 slims plus the merra2_lag1 / merra2_same / merra2_lag1_placebo index tables were written. The defo slims (leads 0 and 1) finished after the step order was fixed (the prep reads the slim).
  - **13:03:** O10 `prep --stage train` (3 workers) was stopped by the harness RAM watchdog (12.02 GiB process tree) on bolivia_beni_savanna, about 3.8 GiB per worker on 147 M core pixels.
  - **The runner then hung until 20:19.** The three multiprocessing workers outlived their stopped parent and held the output pipe. They were confirmed as orphans (parent gone, multiprocessing.spawn) and stopped by the agent; no data is touched by stopping them.
  - **Fix:** registry defo.yaml prep_workers 3 -> 2. Results do not depend on the worker count (tests_builder_b test_two_workers_give_the_same_files). The prep resumes per region x map, keeping the 6 regions done.
  - Runner relaunched about 20:22. Note: D: has 109.6 GB free after the owner deleted the zero-risk folder (Part 615).
- **Defo prep, second stop (22:48, 2026-10-23).** The RAM watchdog fired again (12.22 GiB) at eastern_us_deciduous, and the runner hung again on orphaned workers until 07:44 on 2026-10-24.
  - **Root cause, from the per-region logs:** tree RSS does NOT follow region size. canadian_taiga (806 M core px) peaked at 9.9 GiB, while later small regions sat at 10.6 GiB. It rose steadily through each run: 5.9 -> 12.2 GiB in about 2.3 h. defo_prep.run_stage submitted every map pass up front and kept all futures in `futs`, so every finished map's result stayed in the parent's memory.
  - **Fix (tool code, pre-signing):** `futs.pop(fu)` releases each future after its map is written. The written files and results are unchanged; tests_builder_b prep/defo tests 15 passed, including test_two_workers_give_the_same_files. prep_workers stays 2.
  - **Runner fix:** Invoke-HumanStep now waits for the PROCESS (Start-Process + WaitForExit, output to temp files) instead of the pipe, then stops multiprocessing workers whose parent_pid is gone. A watchdog stop can no longer hang the runner.
  - 2 + 3 orphans were stopped by hand (parents confirmed dead). The prep resumes per map; about 261 of 714 map passes were done.
  - Relaunched 2026-10-24 about 07:46; the full human test suite re-runs first, because the tool code changed.
- **Defo prep PARITY (2026-10-24 14:00).**
  - The memory fix held: all 714 map passes finished in 6 h with no watchdog stop and no hang.
  - Then parity_check refused: "japan_central_honshu: forest2000 of japan_central_honshu_3784_1040 is 6368 here, 6377 in the target".
  - **Full parity over all 42 regions** (analysis/defo_parity/): 40 regions are exact. japan_central_honshu has 20 cells off (-9 to -117 px each); new_guinea_papua has 113 cells (+142/+143 px, loss 505 px). In all 0.0003% of forest pixels.
  - **Every differing cell lies in the region's WESTERNMOST cell column**, one 30 m pixel column.
  - **Cause:** defo_ingest.py (which built D:/defo_target) reads the panel's float32 centres, so its window edge lon0 = ulon.min() - hx is a float32 value (NumPy 2). The prep computed it in float64. Those two west edges sit within 0.007 / 0.002 px of a pixel boundary, so floor() differs by one column (japan builder 1263875 vs prep 1263876; papua 7879 vs 7878 in-tile). Checked over all 168 region edges: only these 2 differ.
  - **Fix:** region_grid computes hx/hy and the four window edges in the builder's float32 arithmetic, and refuses if the centres are not float32 values. ex/ey stay float64 (the builder casts there too). The real regions now give the builder's columns.
  - **Tests:** the new tests_builder_b/test_defo_window_float32.py (2) and the defo prep/defo tests (15) pass.
  - The 40 train maps of the two regions were moved aside to rivals_human/_moved/20261024_parity_fix (divisions kept); the other 40 regions' maps are unaffected (their edges are identical).
  - Runner relaunched to recompute the 2 regions, then parity on all 42.
- **NDVI common board runner prepared and launched (2026-10-24, about 14:40), at the owner's request to start the remaining scripts.** Script: D:/treeroute/rivals_build/follow_ndvi.ps1. Log: logs_owner/follow_ndvi_*.log.
  - It waits until no human pre-signing runner is alive, then 5 quiet minutes.
  - Then, lead by lead: export (never --full-engine-checks) -> human NDVI slim -> (lead 0: init, probe, tune, lock) -> refit -> score; then the board.
  - Resumable; finished steps are skipped. A RAM-guard refusal of tune or refit is retried in a fresh process (up to 2); any other failure stops. It pauses only if D: < 25 GB before an export. Deletes nothing.
- **HUMAN PRE-SIGNING STEPS 2-4 DONE (2026-10-24 15:55; 38 steps; log logs_owner/follow_human_20261024_140524.log).**
  - The defo prep stage train finished at 15:01 (2,290 s for the two rebuilt regions); parity equal on all 42 regions.
  - vt0007_shipped / _cal / _frozen2019 train-side index tables and checks passed (T1/T2 breaks 0).
  - Remaining before the Part A signature: the NDVI slims (inside follow_ndvi.ps1, one per NDVI lead export), then `cli shas` per run and the TO FILL lines.

## Part 616 - NDVI COMMON-RIVAL BOARD (pre-registered, rival Part 598; board D:/treeroute/rivals/ndvi/20261016_d1de3158) - ALL FIVE COMMON BOARDS DONE

2026-10-25, 09:39.
- **Run.** Engine identity checks I1-I9 passed with no accepted difference. Harness b6ea97b7. 133 groups; band 0.000597.
  - Picks: Ridge identity alpha 0.1; RF identity mf0.5/leaf5; LightGBM identity leaves127/mcs200 at 1600 (extended under AC2).
  - Export P1-P14 passed at leads 0/6/12. Human NDVI slims were made after each export.
  - Refits 6 and 12 hit the RAM guard once each; the runner retried in a fresh process and both passed.
- **Nowcast** (ours 0.03146 = headline, -20.2% vs the normal):
  - Ridge 0.0429: **BEATS** (d +0.0115 [+0.0105, +0.0124]).
  - RF 0.0352: **BEATS** (+0.0037 [+0.0031, +0.0044]).
  - LightGBM 0.0320: CANNOT TELL (+0.0005 [+0.0001, +0.0009]; favours ours, under the band).
  - corr2: ours 0.963 (highest; LightGBM 0.963, RF 0.956, Ridge 0.948). Hit rate: ours 0.461 (highest).
- **6 months.** Our guard failed, so our headline is the normal (0.0396).
  - Ridge, whose guard passed (0.0384): **LOSES** (d -0.0012 [-0.0016, -0.0007]).
  - RF and LightGBM guards failed too, so they are IDENTICAL (normal).
  - Raw: our pinned model 0.0392 vs Ridge LOSES; vs RF and LightGBM EQUIVALENT.
- **12 months.** Every guard failed, so all are IDENTICAL (normal 0.0396).
  - Raw: ours 0.0400 vs Ridge 0.0389 LOSES, RF 0.0393 LOSES, LightGBM EQUIVALENT.
- **Reading.**
  - On NDVI our model is the best or level at the nowcast (it beats Ridge and RF; LightGBM cannot be told apart and points our way), with the highest corr2 and hit rate.
  - At 6 and 12 months no model adds much over the normal; most guards decline.
  - Ridge is again the rival that holds up at longer leads, as on PM2.5. This is a post-hoc observation only; the trend mechanism of Part 611 has NOT been tested on NDVI.
- **All five common-rival boards are done:** coral (600), fire (606), pm25 (610), defo (614), NDVI (616).
- **Part A preparation (2026-10-25).**
  - `cli shas` was re-printed for the four runs (human_rivals_build/SHAS_FOR_PART_A_20261025.txt). Part A section 1 is filled from it: tool 32ec5df0 (full suite + review tests passed on it), current registry and file hashes, product manifests. Old draft kept as _moved/...before_shas_20261025.txt.
  - Section 11 item 7 is recorded as done.
  - Ruling AI: the optional Kraft LSTM is included. Its prep was launched via rivals_build/follow_kraft.ps1 (monthly_panel manifest, prep kraft_lstm, ndvi_kraft_store manifest, then NDVI shas).
- **Kraft prep DONE (2026-10-25 12:58; ruling AI).** monthly_panel manifest d946f63e (19.7 min), prep kraft_lstm (20.5 min), ndvi_kraft_store manifest 3ebc2dad (133 files).
  - Part A section 1 now has no TO FILL line. The draft's SHA-256 before signing is 4db899658f22e30d50e12980b4db66e947b9cdb519fab8b52817968e477360b8.
  - Waiting for the owner's signature.

## Part 617 - HUMAN RIVALS PART A SIGNED (coral, defo, PM2.5, NDVI)

2026-10-25.
- **The owner signed in chat** and asked for the table of the finished rival results.
- **Signed file:** D:/treeroute/registry/rivals/PREREGISTRATION_human_partA_20261025T105940Z.txt, SHA-256 4db899658f22e30d50e12980b4db66e947b9cdb519fab8b52817968e477360b8. It is byte-identical to the draft sent to the owner. The signature record is in .SIGNED.txt beside it.
- **Frozen at signing:** human tool code 32ec5df06e8022be17393cbd1e6fa2e0929876a1f9835a8b8e707761a13133a5; common harness b6ea97b7 (accepted older 71457aa9, AG5). Rulings AG, AH and AI apply.
- **No human-rival test score existed before the signature.** Any later code change follows Part A section 12.
- **The boards** (HUMAN_OWNER_COMMANDS step 7) and the join (step 8, fire pending, Part B) were launched via D:/treeroute/rivals_build/follow_hboards.ps1.
  - The coral picks must equal the DRY pass (ebef5359), else it stops.
  - The pm25 lock uses --without eac4_lag1 eac4_same eac4_lag1_placebo with the AG1 decision text.

## Part 618 - HUMAN TOOL FIX AFTER THE PART A SIGNATURE (Part A section 12: changes no pick; reference rows only): NDVI PERSISTENCE PARITY

2026-10-25.
- **Board status.** The coral, defo and pm25 human boards are DONE under tool 32ec5df0 (coral picks = DRY ebef5359).
- **What failed.** The NDVI board stopped at `refs 12`: "parity proof failed at lead 12 (persistence DIFFERS on 1900 rows, damped DIFFERS on 57304 rows)". Lead 6 was the same.
- **Diagnosis** (analysis/ndvi_refs/refs_diag*.py, read-only):
  1. The 1,900 persistence rows read the label AT the lead-0 fit cut (Dec 2019, step 24240). NDVI has an R17 start offset of 1, so every export row set stops at 24239, and the engine reads 24240 from its vault. PM2.5 has offset 0 and passed.
  2. The damped differences come only from phi. The implied engine phi is constant within all 1,851 units, so the normals agree. The engine's phi history ends at fit_cut - offset (a history window ending at fit_cut - 1 matches 1,851/1,851 units; fit_cut matches 600; adding 2002 makes it worse).
- **Fix** (rivals_human/refs.py; registry ndvi.yaml refs_label_store; _schema.yaml adds that optional field):
  - The phi history ends at fit_cut - run_offset.
  - Training-period labels the slims lack, in (newest held training step, lead-0 fit cut], are read from the package's own target store (D:/monthly_panel V11_mean_ndvi, the engine's stores.target). Files are sha-checked against the manifest.
  - Every overlapping held label must be byte-equal, else refuse: 401,977/401,977 were equal in the diagnosis. No test step is ever read.
- **Real-data check (read-only):** persistence AND damped persistence are byte-EQUAL to the run's saved columns at leads 6 and 12. The parity proof is kept in full.
- **Tool code:** 32ec5df0 -> cd956f1dbd0f9b0f. Old refs.py kept at human_rivals_build/_moved/refs.py.before_offset_fix_20261025.
  - The coral, defo and pm25 boards stay as made under 32ec5df0: their refs passed, and they are unchanged by this fix (offset 0, or the tables path).
  - The old NDVI board files were moved aside to rivals_human/_moved/20261025_ndvi_board_pre_part618 (slims kept). NDVI is re-initialised under the fixed tool; picks must be the same (shared ledger). No pick changes; reference rows never decide.
- **Runner:** rivals_build/follow_hboard_ndvi.ps1 runs the full human suite first, then the NDVI board, then the join (coral, defo, pm25, ndvi; fire pending).

## Part 619 - FINAL RIVAL TABLE (common + human; fire human = Part B, pending)

2026-10-25.
- **What ran.** rivals_build/follow_hboard_ndvi.ps1 ran the full human test suite, then the NDVI human board under the Part 618 tool (cd956f1dbd0f9b0f), then the join. Finished 19:23 with the log line "NDVI HUMAN BOARD AND JOIN DONE (14 steps)". The refs parity proof passed at leads [12], [6] and [6, 12].
- **The join.** D:/treeroute/rivals_table/20261025T162302876402Z (RIVALS_TABLE.md / .csv, csv sha256 1ccac0e7…78ba; inputs in inputs_sha256.txt).
  - Rows: common 106, human 56, own_history 37, ours 14, reference 14.
  - The interim join 20261025T153132510251Z is superseded; it was made before the NDVI human board.
- **Compact view.** engine/RIVALS_TABLE_FINAL.md (sha256 f22a6a24…87d6), made by analysis/final_table.py (read-only).
  - Common, deciding contrast: WIN 9, loss 9, ? 21, = 3, same 11.
  - Human, deciding rows (tier P/L): WIN 9, ? 2, same 1.
- **Human results (deciding = rival's guarded answer vs our headline; the human cell compares on the rival's own rows).**
  - **Coral, NOAA crw_dhw on 2,312 site-days.** These are a subset; ours is 6.471 on them vs 6.698 on all rows.
    - Nowcast: CANNOT TELL (8.089 vs 6.471).
    - 183 d: BEATS. The rival's guard FAILED, so its answer is the normal (7.977 vs 7.397). d 1.85 [0.0019, 3.70] is barely clear. Raw 9.248 also BEATS.
    - 365 d: IDENTICAL. Both answers are the normal.
    - The crw_outlook (A tier, never decides) at 183 d is CANNOT TELL.
  - **Defo, VT0007 (all three forms).** The guard FAILED for every form, so the deciding WIN is "ours vs the normal" (0.00840 vs 0.00542/0.00541).
    - Raw also BEATS every form. The calibrated form is closest: 0.005676, d 0.00026 [0.00013, 0.00039].
    - The pre-registered joint claim "ours beats VT0007" is YES at leads 0 and 1.
  - **PM2.5, MERRA-2 lag 1:** CANNOT TELL (8.444 vs 3.588). d 4.86 [-4.15, 13.86] over 127 groups; the region spread is huge. merra2_same (A tier) is slightly better than ours. This was already known from Part 617.
  - **NDVI nowcast:**
    - Rain-lag BARDL H1: BEATS (0.0342 vs 0.0315, d 0.00275 [0.00224, 0.00326]).
    - Kraft LSTM: the guard FAILED (its answer = the normal, 0.0394) and ours BEATS it. Raw Kraft 0.0607 is far worse than the normal.
    - Leads 6/12 have no published rival. The H1 extension (X) LOSES at 6 and is IDENTICAL at 12, and never decides.
- **Honesty rule for the paper.** Of the 9 human WINs, 7 are wins over a rival whose own guard fell back to the normal: coral 183, defo ×6, NDVI Kraft. They must be written as "the rival did not beat the normal; ours did". Only NDVI H1 is a WIN over a rival that beat the normal.
- **Still open:** fire human rivals (Part B). Needs ~/.ewdsapirc and the licence click by the owner, then the D2/D3 downloads. Cut-off 18 Nov.

## Part 620 - FIRE HUMAN RIVALS (PART B): WHAT ALREADY EXISTS (read-only audit, workflow <id>-116)

2026-10-25. The owner recalled that the fire human rivals might have been done in another session and asked for the files to be checked. Method: 5 read-only sweeps (data on disk, old results, other session transcripts, tool/plan, reuse fit), 5 skeptics, 1 completeness critic. No file was changed, nothing was downloaded, and no key file was read.

- **What the owner remembers is the PRE-FREEZE work. No fire human rival has ever run under the frozen protocol.**
  - Parts 496-498 (1-5 Sep, sessions <id> / <id> / <id>): FIRE_CEMS_REPORT.md, CEMS GEFF-SEAS5 FWI against the OLD model. One region (northern_australia_monsoon, 2021-22, 124 cells), leads 0-1 month, link fitted on rows inside today's test window. Lead 1: MAE 0.025443, anomaly-R2 +0.0195.
  - Part 491: our own danger indices (MDC, KBDI, Fosberg, ...), old 30/10 split.
  - fire_danger / fire_danger_local (rivals.py, 15-24 Sep, sessions <id> / <id>; D:/adaptation/_rivals/fire_L*.npz). Our own Fosberg/FFDI-style index; L0 MAE 0.006715, R2 +0.0408. Old split.
  - Part 501: an ML rival (XGB Tweedie), not a human rival.
  - None of these is a paper row: different split, test years, leads and 'ours'. At most they are history for the R10 "not blind" note. That note must ADD fire_danger_local; the plan's R10 lists only Parts 496-498.
- **Data on disk cannot replace the downloads.**
  - D:/fire/cems/raw holds 26 netCDF files, 216 MB.
  - SEAS5: 12 regions, starts in 2019/2021/2022 only, 51 members, daily leads that stop at day 61 or 91. D3 needs days 150-184 for 240 starts 2002-08..2022-07 in 40 regions, so 0% is covered.
  - ERA5-FWI: greece_mainland 2018-2022 and yakutia_larch 2020. Same product settings as D2 (consolidated, system 4_1, 0.25 deg); covers 6 of 800 region-years.
  - fwi_c7 / fwi_smoke / fwi_dl hold our own AgERA5 FWI (Greece), not CEMS.
  - Useful only as reader test files and as a bit-check of the new D2 download.
- **Old code hazard:** fire_cems.py nearest-grid matching has a 0-360 longitude bug. All western-hemisphere cells snap to one column. Do not reuse it; write the new extractor with an explicit longitude wrap.
- **What Part B already has:**
  - fetch_products.py implements D0', D2 and D3 (never run for fire). Its reports/locks are empty.
  - The shared human tool, with the F6 map (no test yet) and `join --pending`.
  - Acceptance of the fire common board (71457aa9).
  - The fire common export, still on disk (rival_export/fire/20261017_869d1f38, 431 MB, 3 leads, 96,000 test rows per lead; has x__oni, x__tni, x__nino*, x__spi_01m..24m).
- **What is missing:** ~/.ewdsapirc (owner); D0', D2 and D3 with hashed manifests; registry/fire.yaml (without it `slim` refuses: config.py:342); the D2/D3 reader adapter; the x__fwi_pct stat; the ENSO-lag and Turco SPI-lag runners; a Turco functional form (in no plan file); the Part B draft.
- **Hazards:**
  - **Do NOT delete the fire export before the fire slim.** HUMAN_OWNER_COMMANDS.txt:16 says delete it; that line is stale.
  - The fetcher sends ONE request at a time (lock per product). Per-region D3 is 840 requests (1.94 GB, approved), about 28-210 h. Merged D3 is 210 requests (8.22 GB, needs --approved-gb 8.3), about 7-52 h. D0' measures the real pace.
  - C: is 99% full (5.0 GB free).
  - spi_03m is NaN for some scored units in test years. One greece_mainland unit carries the -2^31 precipitation sentinel.
- **Open owner rulings:**
  1. D3 box choice (after D0').
  2. May Part B be signed on D2 alone if D3 misses 18 Nov (lead 6 then "pending")?
  3. Add fire_danger_local to R10.
  4. The Turco SPI-lag form (drafted in Part B).

## Part 621 - HUMAN TOOL CHANGE FOR PART B (fire), Part A section 12: TOOL cd956f1d -> 16a2d736, _products.yaml 4e479759 -> 6d97a17b; NO PART A PICK, BOARD OR SCORE RE-RUN

2026-10-25/26. Built by workflow <id>-d82 (at the owner's request to work on the fire human rivals). Steps: spec, 2 skeptic reviews (18 issues, 1 blocker, all resolved in the spec), 4 builders on disjoint files, integration, adversarial code review, ONE full suite. Spec: D:/treeroute/human_rivals_build/SPEC_HUMAN_PARTB.txt. Notes: BUILD_NOTES_fire*.txt. Draft: PREREGISTRATION_DRAFT_human_partB.txt (UNSIGNED). Owner commands: HUMAN_OWNER_COMMANDS_partB.txt.
- **Why.** Part B (fire human rivals; ruling AB, Q22 a) goes into the same human tool. Adding fire files plus one shared edit changes two Part A section-1 hashes; this Part logs it, as Part 618 did.
- **Tool code:** cd956f1dbd0f9b0f2ada37c1a27f8212768d94fc6242cab0686bf7c71608a273 -> 16a2d7362b83d7d8ddf539a5fe4b75f8166fa56976be3f13d88770fbfd68f591.
  - Added (fire only; no problem name in rivals_human/), with sha256 prefixes:
    - adapters/fire_geff.py 33fd951a. Reads the fetcher's D2/D3 layout with manifest checks, an explicit longitude wrap and sea-point substitution, members 0-24, and x__fwi_pct (mid-rank against the unit's same-month FWI up to the lead's guard cut, own month left out).
    - adapters/fire_refs_prep.py 98fad293
    - adapters/fire_enso.py 7ba939c8 (ENSO-lag, forms E1/E2/E3)
    - adapters/fire_turco.py 7dfe5835 (Turco SPI-lag, forms T1/T2/T3)
    - adapters/fire_lag_common.py 718a68e6
  - The ONE shared edit (spec 4.4; owner decision OD-14 still OPEN): rivals_human/maps.py f38d7ce7 -> 6b4bb064.
    - F6 is fitted as research C-A states it: a leave-year-out normal from the cell sum on fit rows, then an N_loo^2-weighted isotonic ratio.
    - Iso.fit gains an optional weights argument; with None it makes the old call.
    - Baseline kept at human_rivals_build/_moved/20261025T194657Z_partB_baseline/.
- **Registries.** fire.yaml is new (bf0b8e55; rivals geff_era5, geff_seas5, enso_lag, turco_spi). _products.yaml 4e479759 -> 6d97a17b: the fire block is appended; its D2/D3 folders are UNSET_OD6 placeholders until the box decision. _schema, coral, defo, pm25 and ndvi yaml are unchanged (T-F15 b).
- **Tests on the final code:**
  - Full suite: "376 passed, 10 skipped, 16 warnings in 439.79s"; review_tests: "60 passed". 0 failed.
  - The 10 skips are realdata tests (HUMAN_REAL=1 not run yet).
  - Logs: human_rivals_build/pt/tests/final_full_20261025T2057Z.log and final_review_20261025T2105Z.log.
  - Proofs inside the suite:
    - T-F15 a: hash with the baseline maps.py == cd956f1d, so no other file changed.
    - T-F15 e: the maps.py diff is limited to F6, Iso.fit and the constants.
    - T-F10: Iso.fit without weights, F2 and F4 are byte-equal to the baseline.
  - **NOT yet run:** T-F15 d, the realdata re-join byte-equal to Part 619's table, and T-F18.
- **Part A effect: none.** No Part A pick, board or score was re-run. The finished boards keep their hashes (32ec5df0, and cd956f1d for NDVI). The joiner never compares tool hashes.
- **Code review: 4 MINOR findings, not fixed (open):**
  1. The OD-7 "tier-A ERA5 ceiling" alternative would need a code change, not just a yaml edit.
  2. The manifest-vs-folder check compares the manifest with itself in production. A stray file in the D2/D3 folder would not be detected (T-F01 passes only through its fixture).
  3. The non-monotonic prime-meridian test fixture is monotonic after the wrap, so the 0..25.5 + 350..359.75 branch (box10/sahel) is untested.
  4. T-F19's "not blind" check is vacuous.
- **Owner progress seen:** ~/.ewdsapirc now exists. The owner ran D0' at 22:34-22:44 local: 1 merged-box request (box04, 12 starts of 2016) gave 29.84 MB (the plan expected 67) in 627 s (10.4 min), sha256 42b57963e6e3c289.
- **Open owner decisions OD-1..OD-14** (PREREGISTRATION_DRAFT_human_partB.txt section 11). Key ones:
  - OD-1 Turco form (T1 recommended; NOT checked against the paper).
  - OD-2 ENSO form (E1).
  - OD-4.1 sign on D2 alone if D3 misses 18 Nov (rec. yes).
  - OD-5 R10 adds fire_danger_local.
  - OD-6 D2/D3 boxes.
  - OD-14 the F6 shared edit (rec. yes).
  - The F0-F6 vs F2-F6 families mismatch with the plan (F0/F1 would read FWI 0-220 as a burned fraction).

## Part 621 addendum - HEADLINE_MODEL_TABLE rounding fix (2026-10-26)
- PM2.5 lead 12, pinned model MAE: 3.841 -> 3.840, change -5.9% -> -6.0%. Source: the common board raw_vs_raw "our MAE (pinned model)" is 3.84046, and (3.84046 - 4.083558) / 4.083558 = -5.95%. Text only; no number in any board changes.

## Part 621 addendum 2 - fire F1-F3 done, realdata tests passed, review finding 2 fixed (2026-10-26)
- **F1-F3** (runner rivals_build/follow_fire_f123.ps1; the setup block copied verbatim into rivals_build/fire_setup_partB.ps1; log logs_owner/follow_fire_f123_20261026_120831.log) ran 12:08-12:10:
  - F1: fire slims for leads 0/6/12.
  - F2: manifests for fire_static_cells and fire_target_2018.
  - F3: prep geff_era5 --stage train, the fire_refs_label_store manifest, and T-F18, which passed: the 2018 training labels are byte-equal to the held labels.
  - No test label was read for scoring. The fire common export can now be deleted by the owner (the slims hold what Part B needs).
- **Realdata command** (HUMAN_REAL=1, tests_fire -m realdata): "6 passed, 136 deselected in 6.90s". These are T-F11 x4, T-F15 d and T-F18. T-F15 d is the re-join of coral/defo/pm25/ndvi with fire pending, byte-equal to Part 619's RIVALS_TABLE.csv (sha 1ccac0e7...78ba). Log: human_rivals_build/pt/tests/realdata_20261026_121017.log.
- **Review finding 2 fixed** (adapters/fire_geff.py check_manifest).
  - The problem: the real ctx.product_files is built from the manifest itself, so a stray file in a D2/D3 folder was never seen.
  - The fix: the folder is now also listed on disk, and anything besides the manifest's files and product_manifest.json refuses, including a leftover .part file or a subfolder. The fetcher writes nothing else there (fetch_products.py:6-9).
  - Two regression tests were added to test_f01_manifest.py.
  - tests_fire: "138 passed, 6 skipped".
  - fire_geff.py 33fd951a -> 83eb0845. Tool code 16a2d736 -> 6a635858 (6a6358588fa28db55a0ec819002ebbfd53867e0fd17ea76e912b640fd0e1490a).
  - The ONE full suite is re-run once more before F7, after any further Part B code change.
- **Still open from the review:** findings 1, 3 and 4, all minor.
  - 1: the OD-7 alternative needs code. Moot if OD-7 = none, the recommendation.
  - 3: the box10 prime-meridian branch is untested. Moot for D2 merged if no merged box crosses 0 deg; check after D2.
  - 4: T-F19 "not blind" is vacuous; test quality only.

## Part 619 correction (2026-10-26; found by the paper fact-sheet review, <id>-467, items C4/C5)
- "7 of the 9 human WINs" is wrong: it is **8 of 9** (coral 183 d, defo x6, NDVI Kraft; RIVALS_TABLE.csv guard_passed False). Only NDVI BARDL H1 is a win over a rival that passed its guard.
- "Coral, NOAA crw_dhw on 2,312 site-days. These are a subset" is wrong: crw_dhw covers **2,312 of 2,312** rows (human_board.md). The deciding contrast uses 2,290 rows in 32 of 37 ecoregions (groups with >= 10 rows); "ours 6.471" is our MAE on those 2,290 rows.
- Added: on the COMMON board, 2 of the 9 WINs are over rivals whose guard failed (fire lead 0 Ridge; PM2.5 lead 6 LightGBM).
- Also fixed: HEADLINE_MODEL_TABLE.md header said "test years 2020-2023" for all problems; fire is 2019-2022 and coral 2016-2019 (derived.json R5).
- Files corrected: PAPER_NOTES_RIVALS.md, HEADLINE_MODEL_TABLE.md header, RIVALS_TABLE_FINAL.md (regenerated by analysis/final_table.py: common guard-failed rows marked *, coral note fixed). No number in any board changes.

## Part 621 addendum 3 - D2 started, F4b done (2026-10-26)
- The owner started D2 (merged boxes, ruling AJ1) at 13:48:32 in their own window: 40 requests, expected 2.29 GB.
  - Folder: human_products/cems_fire_historical_fwi/geff_era5_v4_1_consolidated_fwi_2003-2022_merged.
  - Log: human_tools/reports/run_D2.log.
- F4b (Set-FireProductFolder cems_geff_era5_fwi merged) ran at 13:49:05.
  - It changes only the cems_geff_era5_fwi manifest line in registry/_products.yaml: 6d97a17b -> c7f1ff03.
  - The previous file is kept in human_rivals_build/_moved/20261026T104905Z_F4b_cems_geff_era5_fwi/.
  - The D3 entry stays as the UNSET_OD6 placeholder; D3 is not downloaded (AJ1).

## Part 622 - PAPER FACTS RE-COMPUTED POST HOC (rulings AK3, AK4(a)); TWO INDEPENDENT SCRIPTS AGREE

2026-10-26. POST HOC: computed after the test labels were opened; report-only; no pre-registered verdict changes.
Folder D:/treeroute/analysis/paper_posthoc (POSTHOC_REPORT.md, SPEC.json, posthoc_A.py, posthoc_B.py, reconcile_AB.py, *.json).
- **Method.** Two scripts (A sha256 0cee249c0834dc2b, B 6b781c848bd84391) were written independently from one spec and re-computed the provisional facts from saved predictions and frozen engine CSVs (light; no refit). reconcile_AB.py compared 3,917 leaves: 0 disagreements (every full-precision float bit-identical). A ran 1,327 checks, B 1,738; 0 failed. All 82 input files match their sha256 prefixes. No script needed a fix.
- **M34 (identity trees-off = guess-normal).** MAE equal to 6 significant digits in all four: PM2.5 4.03161, NDVI 0.0394141, fire 0.00625876 (added), defo 0.00840486. Relative differences -5.4e-11 / -6.2e-09 / 2.1e-08 / 4e-11; largest row difference 4.1e-09 / 1.76e-07 / 8.09e-07 / 4.76e-09, all inside the identity tolerance; guess-normal == clip(normal) exactly. **Wording fix:** 'within 1e-8 relative' is false for fire; say 'within 2.1e-8 relative' or 'equal to 6 significant digits'.
- **R12 (fire nowcast ordering).** Confirmed: log trees-off 0.004281 < predict-zero 0.004284 < four log arms 0.004296-0.004322 < adopted 0.004385 < arcsine trees-off 0.004428 < identity normal 0.006259. New, report-only (40 regions): adopted vs log trees-off d -0.000103 [-0.000231, +2.51e-05] CANNOT TELL (adopted better in 25/40); vs predict-zero d -0.000104 [-0.00062, +0.000413] CANNOT TELL (3/40).
- **R13 (corrector / placebo / plain).** Confirmed for all five runs; all 21 placebo pairs of jackknife.csv re-derived exactly: EQUIVALENT except defo identity unweighted (CANNOT TELL) and fire's two identity pairs (HURTS).
- **R14 (penalties).** Confirmed: PM2.5 a_tree 15 / a_ctx 15; NDVI 0.5 / 0.03125; fire 50 / 50; defo lambda 10; coral 50 / 50. M47 (same point at later leads) not re-checked.
- **R15 = AK4(a) ablation table.** Every saved column scored (89 columns, all equal to score_pooled.csv). Regret of the adopted arm: PM2.5 0.00061 (0.017%), NDVI 0, fire 8.93e-05 (+2.08%), defo 0, coral 0.5505 (+8.95%). Not a test of the per-unit axis (M56); AK4(b) is still open. Wording: defo adopted 0.0054158 vs log plain 0.0054164 is '<', not '='.
- **P29 (interval method).** With t(G-1) instead of z = 1.96, exactly 2 of the 79 deciding verdicts change: fire nowcast HELPS -> CANNOT TELL (t39 2.023, CI [-1.2e-06, +8.58e-05], p_t 0.0564 vs p_z 0.0492); coral CRW lead 183 BEATS -> CANNOT TELL (32 regions, t31 CI [-0.07307, +3.773], p_t 0.0588 vs p_z 0.0498). Holm over the five nowcasts: all survive with z (fire last, 0.0492); with t fire fails (0.0564). Band share of the reference MAE: PM2.5 1.20%, NDVI 1.52%, fire 0.31%, defo 1.93%, coral 11.06%. Count is 79, not 'about 80'.
- **R3b (model vs best naive).** Fire +2.42% vs log trees-off and +2.36% vs predict-zero (worse); PM2.5 -6.88%, NDVI -20.02%, defo -5.23%, coral -17.31%.
- **RC12 (coral by magnitude, outcome-defined).** 'L1 wins on every bleached stratum' is NOT reproduced. Ours is lower in B1-B3 (e.g. B3 8.40 vs 9.47); hgb_l1 is lower only above q75 (41.05 vs 31.15, d -6.16 [-9.49, -2.83] HURTS) and at y >= 50 (53.13 vs 38.66, HURTS). Ours under-predicts the largest events (above q75: mean prediction 17.8 vs truth 58.4; L1 29.3).
- **A1 (fire active cells vs Tweedie, outcome-defined).** Confirmed. y > 0 (1,759 cells, 33 regions): ours 0.191 vs 0.201, d +0.00472 [+0.00237, +0.00706] HELPS. Top 1% (y >= q99 = 0.102941 from test labels; 949 cells): 0.308 vs 0.335, HELPS. Zero rows (98.14%): ours predicts 0.00085 on average vs 0.00032, d -0.000549 HURTS. Ridge's guarded column is the identity trees-off, not guess-normal exactly.
- **A2 (coral bleached visits vs rivals, outcome-defined).** Confirmed: 1,024 visits, 36 regions; ours 13.37 is mid-pack (L1 11.69, LightGBM 12.70, RF 12.87 lower; Tweedie 13.62, Ridge 14.48 higher); all five per-region contrasts CANNOT TELL.
- **Fact-sheet edits:** M34 wording (+ add fire); RC12 'every bleached stratum' -> 'the top quartile and y >= 50'; P29 'about 80' -> 79; R15 defo '=' -> '<'; A1 spec: Ridge guarded = identity trees-off. Everything else matches.
- **Owner ruling:** AK3 / AK4(a) (2026-10-26: the recommended answers, to log the numbers and then use them, and to make the cheap table now and the real ablation if time allows). Every number here is labelled post hoc in the paper. Fact-sheet edits are applied to paper/PAPER_FACTS.md once the drafting workflow that is editing it finishes.

## Paper drafting progress note (2026-10-26; not a result Part)
- Drafts in paper/draft/. All went through writer, record-fidelity skeptic, reviewer skeptic, then revision.
  - 02_method.md: 2,300 words.
  - 03_protocol.md: 1,430 words.
  - 04_results.md: 1,974 words.
  - 05_rivals.md: 1,524 words.
  - 06_limitations.md: 1,170 words.
  - Supplements S7 and S8 hold the cut detail verbatim.
  - The fact sheet gained K1-K61 (code facts), and Part 622 has been applied.
- PAPER_NOTES_RIVALS.md coral-strata line corrected (C16, from Part 622).
- Open: a consolidation pass (wf paper-consolidate-2-6), a MERRA-2 runaway-forecast sensitivity (to be logged as a post-hoc Part if both independent scripts agree), Introduction / Discussion / Conclusions / Abstract / availability, the citation check, the owner's region-selection rule and author list, and the fire published-rival board.

## Part 623 - PM2.5 PUBLISHED RIVAL MERRA-2 (lagged 1 month): ONE RUNAWAY FORECAST DRIVES "CANNOT TELL" (post hoc, report-only; ruling AK3)

2026-10-26. POST HOC: computed after the locked results were seen. The locked verdict stays CANNOT TELL. Folder: D:/treeroute/analysis/paper_posthoc/merra2_runaway (sens_A.py 7a6588b8, sens_B.py 5b66f667, sens_A.json c826c410, sens_B.json 0679a45e).
- **Method.** Two independent scripts each reproduced the board's deciding contrast first, bit-exactly: d 4.855619585591441 [-4.146349, 13.857588], 127 regions, 91,440 deciding rows (91,428 labelled). The rival's MAE is 8.4443 and ours 3.5881. They used the tool's own join, score and jackknife path; the band is 0.0462119.
- **The runaway forecast** (both scripts):
  - The rival forecast is **418,377.52 ug/m3** for unit yakutia_larch_3553_2232 (62.297N 127.687E, MERRA-2 cell r304_c203), target month 2021-08.
  - Its input, the July 2021 MERRA-2 PM2.5, is 1,698.28. The observed value is 188.37; ours forecast 23.71.
  - The legal range is [0, inf), so nothing clipped it.
  - This one row is 54.2% of all the rival's absolute error, and it adds 4.594 to the mean d.
  - The next-largest rival forecast is 2,243.76 (australian_bushfire_belt, 2020-01). 4 rival forecasts exceed 1,000.
- **Sensitivities** (ours better in all; the two scripts give identical numbers):
  1. Drop that one row from both sides (91,427 scored rows, 127 regions): d **+0.2841 [+0.1457, +0.4225]**, which would read BEATS. Pooled MAE: rival 3.8704, ours 3.5863.
  2. Clip rival forecasts to the largest label in the rival's own refit training rows. That is 583.275 (borneo_peat_fires, 2015-09), and 6 rows are clipped: d **+0.2383 [+0.1533, +0.3233]**, which would read BEATS. Pooled MAE: rival 3.8264.
  3. Script A only, extra: clip each region to its own training maximum (27 rows clipped): d +0.2003 [+0.1371, +0.2636].
- **Paper wording.** "The locked verdict against lagged MERRA-2 is inconclusive. This is driven by one forecast of 418,378 ug/m3, produced from an extreme July MERRA-2 value of 1,698 ug/m3. Post hoc, dropping that row, or clipping the rival to its training maximum, gives ours lower error (d +0.28 [+0.15, +0.42]; +0.24 [+0.15, +0.32])."
  - Do NOT name a cause (e.g. smoke): no project file records one.
  - The calibration map gave no protection on an open-ended legal range. Disclose this as a property of the rival setup: its legal upper bound is +inf (Part 608).

## Part 621 addendum 4 - D2 stopped at 13/40 by a reboot; resume allowed (2026-10-27)
- The fire D2 download (merged boxes, ruling AJ1) last wrote at 2026-10-26 21:15:05: file 13/40 (hist_box04_2003-2007.nc, 67.47 MB) finished, then 14/40 was requested.
- The PC rebooted at 2026-10-27 11:56:55, and no fetch_products process is running. No .part file is left.
- Assert-FetcherRerunAllowed D2 says: "OK: no fire human board exists yet: a stopped D2 run may be resumed with the SAME command". Rule B8 applies: resuming is allowed only before the first fire init.
- The owner resumes with the same command in their own window. Finished files are skipped.
- 2026-10-27 16:14: the owner's resume was REFUSED by the fetcher's stale lock (locks/cems_fire_historical_fwi__geff_era5_v4_1_consolidated_fwi_2003-2022_merged.lock, "pid 14924 started 2026-10-26T13:48:33"). PID 14924 is not running and no fetch_products process exists (the 11:56 reboot killed the run). The agent MOVED the lock (not deleted) to human_tools/_moved/stale_lock_20261027_reboot/, as the fetcher's own message allows. The owner re-runs the same command.

- **Paper drafting progress, 2026-10-27 ~17:30 (front/back matter done).** Workflow <id>-64e (resumed after the session-limit failure) finished: 11 agents, 0 errors. New: paper/draft/00_abstract.md (250 words), 00_title_options.md, 01_introduction.md (1,686), tables/table_0.md, 07_discussion.md (886), 08_conclusions.md (307), 09_availability.md (254), REFERENCES.md (231 refs checked against Crossref/DataCite; 20 corrected or marked do-not-cite, none of the do-not-cite keys is cited in the text). Main text now ~12,181 words (ruling AL2: trim after the journal). Review log: paper/draft/review_logs/frontback_review_log.md. Agent fixes after the workflow (pre-edit copies in paper/draft/_snapshots/20261027T142214Z_postwf_fixes/): PAPER_FACTS M14 gains the library versions read from all five headline manifests (scikit-learn 1.6.1, scikit-learn-intelex 2025.10.0, daal 2025.10.0, numpy 2.0.2, Python 3.9.13; identical), so the two [PENDING: version check] markers (02 §2.9, 09) are filled; 02 'Windows and cuts' and S7 (two places) now name coral bleaching's hand-set 2016-2019 test window (M6) instead of "the last four years"; the S7/S8 [CITE] markers are filled with the keys the main text already uses. The workflow's ATTENTION on ruling AL1 is stale (AL1 was already corrected to four cases on 2026-10-27).
- **ATTENTION, MERRA-2 PM2.5 formula (found by the reference check, verified by the agent 2026-10-27).** pm25_products_map.py lines 3-4, 34 and human/registry/pm25.yaml (merra2_lag1 / merra2_same / placebo, options.variables OCSMASS: 1.4) build MERRA-2 PM2.5 with 1.4 x OCSMASS and credit Buchard et al. 2016. NASA GMAO's MERRA-2 FAQ (https://gmao.gsfc.nasa.gov/gmao-products/merra-2/faq_merra-2, read 2026-10-27) gives PM2.5 = DUSMASS25 + OCSMASS + BCSMASS + SSSMASS25 + SO4SMASS x 132.14/96.06 and says no organic-carbon factor is applied because the model already handles it; Buchard 2016 is about MERRAero. So the rival's input over-counts organic matter by 40% of its OC part. The picked family is F5 (per-unit log MOS, log_c; PAPER_FACTS K-section line ~1122), which absorbs a constant factor per unit but not month-to-month changes in the OC share (smoke months). Affects Table 6 MERRA-2 rows (RH4, RH6, K71). Nothing changed; owner decision pending (keep and disclose, or a post-hoc re-score with the GMAO formula logged as a Part; the locked verdict cannot change either way).
- **Owner decision pending, published-rival count.** The front/back review changed the abstract, 1.3 item 4 and 5.2 to "five published methods decided", counting NOAA's degree-heating-week rule once (its tier-L 183-day entry was counted as a separate method before). PAPER_FACTS RH4's by-method list still reads "three methods did not beat the seasonal normal" (VT0007, the Kraft LSTM, NOAA's rule fed old heat). Old wording is in paper/draft/_snapshots/20261027T140804Z_frontback/.
- **Part 621 addendum 4, continued:** the owner's re-run started 2026-10-27 16:15:25 (fetcher PIDs 9496/18140); files 1-13 skipped as 'done before (hash matches)'; 14/40 and 15/40 downloaded; 16/40 requested at 16:17:47.

## Part 624 (POST HOC) - MERRA-2 PM2.5 rivals re-scored with the GMAO formula (owner ruling AM1, 2026-10-27) - DONE: NO VERDICT CHANGES; TWO INDEPENDENT IMPLEMENTATIONS AGREE BIT FOR BIT
- Why: the locked PM2.5 rivals merra2_lag1 (P, deciding), merra2_same (A) and merra2_lag1_placebo (X) built x__pm25 with 1.4 x OCSMASS (human/registry/pm25.yaml options.variables; pm25_products_map.py, crediting Buchard et al. 2016). NASA GMAO's MERRA-2 FAQ (read 2026-10-27) applies no organic-carbon factor for MERRA-2. Found by the paper's reference check (paper/draft/REFERENCES.md, ATTENTION 1).
- What: the only change is OCSMASS 1.4 -> 1.0. (i) the full locked procedure re-run on the corrected input (pick may change); (ii) the locked family F5 log_c forced. Locked verdicts unchanged (merra2_lag1 CANNOT TELL, d +4.85562 [-4.146349, +13.857588]).
- How: spec D:/treeroute/analysis/paper_posthoc/merra2_formula/SPEC.md; two independent implementers (A: tool path; B: own code) in .../merra2_formula/A and /B, each gated on reproducing the locked x, the locked guarded predictions and the locked contrast. Nothing under the board, index, product or build folders is written. Results to be reconciled here.
- **Gates (A and B):** x rebuilt with the locked formula = all three index tables bitwise (252 MERRA-2 file hashes equal those recorded at index build); locked pick F5 log_c, guard 3.5208945819429056 vs 3.5256518387286944 (68,559 rows) and guarded test column reproduced bitwise (all 11 trial MAEs match trials.csv); locked contrast d +4.85562 [-4.146349, +13.857588] reproduced exactly (max diff vs RIVALS_TABLE 1.8e-15, its printed digits). A used the tool's own functions with the pre-Part-B baseline maps.py and pre-Part-618 refs.py (tool code hash = the board's 32ec5df0); B wrote its own code from the baseline source and needed BLAS fixed at 8 threads, as the tool does, for bit equality (6e-14 otherwise).
- **merra2_lag1 (P), OCSMASS x1.0:** pick unchanged (F5 log_c; inner 3.518367, next F4 log_c 3.546821); guard passed 3.5183670030839416 vs 3.5256518387286944; test MAE 8.199033 vs ours 3.588091 (91,440 rows, 127 groups); d +4.610353 [-3.951925, +13.172631], CANNOT TELL; forced F5 identical. Largest forecast 397,947.05 at yakutia_larch_3553_2232 2021-08 from x 1,229.55 (locked 418,377.52 from 1,698.28); 4 forecasts > 1,000 (as locked).
- **merra2_same (A):** F5 identity; guard passed 3.294111 vs 3.652064; d -0.137398 [-0.249893, -0.024903], LOSES (as locked). **Placebo (X):** guard fails 3.814827 vs 3.525652; guarded d +0.443505, BEATS (as locked).
- **Input change:** median x_new/x_locked 0.9286, p99 0.9986, min 0.724; 31,002 of 91,440 test rows (33.9%) fell by > 10%. **Sulfate side check (132.14/96.06 too):** d +4.610224, CANNOT TELL.
- **Reconciliation:** reconcile/reconcile_AB.py (f3e4bfcb) compares A's and B's six prediction sets (x_locked, x_new, raw, guarded): 0 rows only in one side, max abs diff 0 everywhere, 0 NaN mismatches. Files: merra2_formula/A (rescore_A.py e7187fb7, result_A.json d5617cc8), B (rescore_B.py 61c83af4, result_B.json 6dedad95), reconcile/reconcile_AB.json. Nothing outside those folders was written.
- **Paper:** PAPER_FACTS K83; Section 5.2 one sentence and Table 6 note (c) disclose the formula error and the post hoc re-score; REFERENCES.md gains GMAO_MERRA2_FAQ; pre-edit copies in paper/draft/_snapshots/20261027T151759Z_part624/. S3 (post hoc register) and S6 get the Part 624 entry after the figures/supplements workflow (<id>-c30) finishes, to avoid editing files it is building.
- **Part 621 addendum 4, continued (2026-10-28 12:25):** D2 reached 17/40 (hist_box05_2003-2007.nc, 42.99 MB, 23:38:30; file 16 took about 6 h and file 17 about 1.5 h in the provider's queue), then 18/40 was requested. The PC was powered off at 2026-10-27 23:55:50 (System event 1074: RuntimeBroker.exe, on behalf of the owner's account, "power off", i.e. a Start-menu shut down; the 2026-10-26 21:27:20 stop was the same kind) and booted at 2026-10-28 08:54:09. No fetch_products process runs; no .part file is left; 17 .nc files plus the manifest are on disk. The agent MOVED the stale lock ("pid 18140 started 2026-10-27T16:15:26") to human_tools/_moved/stale_lock_20261028_poweroff/ (not deleted). Rule B8 still allows the resume (no fire init yet); the owner re-runs the same command and leaves the PC on.

## Part 597 addendum (2026-10-28) - coral trees without a corrector: 5,851-6,384 per bank, not 5,915-6,384
- Part 597's "Correctors" line (5,915-6,384 of the 8,300 trees per bank) left out the nowcast's fit-cut bank. The coral run fitted six banks of 8,300 trees (83 groups x 100). Its run.log (D:/treeroute/runs/coral/headline/20261020_f3b8e3da/run.log) gives the trees with fewer than 50 out-of-bag rows (no corrector) in each:
  - nowcast fit-cut bank (cut 735963): **5,851**; 56 of 83 groups have none at all (line 27);
  - nowcast inner-cut bank (cut 734868): 6,193; 60 groups (line 35);
  - lead-183 bank (fit cut 735781): 5,915; 57 groups (line 155);
  - lead-183 guard-cut bank (cut 734686): 6,345; 60 groups (line 162);
  - lead-365 bank (fit cut 735599): 5,932; 57 groups (line 170);
  - lead-365 guard-cut bank (cut 734504): 6,384; 61 groups (line 177).
  - Line 182: the run removed its 6 bank checkpoint folders, so there is no other bank.
- Corrected range: **5,851-6,384** of the 8,300 trees per bank (56-61 of 83 groups with no corrector at all). At least 70.5% of each bank's trees have no corrector (5,851/8,300), so "most coral trees have no corrector" still holds. No score, pick or verdict changes.
- Found by the figure/supplement completeness critic (paper/draft/review_logs/figsupp_critic_report.md, ATTENTION 1 / M1). The agent confirmed it by re-reading the run log (read-only). Paper edits proposed, not applied by the agent: PAPER_FACTS M15 (and new conflict C17), Section 2.2, S7.2, S1 RL5, and the fig1.py check text with fig1_data.csv (they must change together with M15, or fig1.py stops on its fact check).
- Applied 2026-10-28 in the fixes1 pass (paper/draft/review_logs/fixes1_apply_log.md, edits 12-19; pre-edit copies in paper/draft/_snapshots/20261028T0930Z_fixes1/apply/), so the bullet above is out of date: PAPER_FACTS M15 and C17, Section 2.2, S7.2, S1 RL5, fig1.py and fig1_data.csv all read 5,851-6,384. (Noted 2026-10-28 by the fixes1 fix pass; paper/draft/review_logs/fixes1_fix_log.md.)

## Record check C18 (2026-10-28) - the short-history fallback routed no scored row (read-only; not a new Part)
- Question: did the short-history fallback (R12: a scored unit with fewer than 24 valid fit rows is routed by its group's region router) route any scored row? Paper fact M29 and several passages said 75 NDVI and 317 fire locations were routed. S7.10 and the fixes1 fix pass read the run files as none (conflict C18).
- Answer: no scored row was routed by it, in any of the three per-unit runs (PM2.5 20261007_74e67609, NDVI 20261016_d1de3158, fire 20261017_869d1f38). Their derived.json files (sha256 3e2d692b, 8ecc92b5 and 9255562c, as in Table S4.14) give:
  - R12: 0 of 2,028,667 (PM2.5), 75 of 2,289,116 (NDVI) and 317 of 925,710 (fire) candidate units ('every candidate unit of every group') have fewer than 24 valid labels from Y0 to the inner-fit end.
  - R20:fallback_rows (scored units at every lead's fit and guard cut): groups_with_fallback 0, short_at_cuts {}, extra_rows 0. The earliest of these cuts (NDVI 24193, fire 24181) comes before R12's window end (24204, 24192), and a count at an earlier cut is never larger, so a scored unit among the 75 or 317 would have been listed.
  - Run time: decision_checks.json has fallback null. Every fallback_levels entry on the decision surface and on each lead's guard surface has fallback_units_scored 0, used_centre true and surface_mae_by_level null (pipeline/router.py takes this path only when there is no short unit).
  - No fallback or all_short record exists in test_pass_router.json, ladder/contract_lead_0.json, or the guard and test records of lead_6/lead_12 lead.json. test_preds.parquet has no per-row router column (NDVI 27 columns, fire 55).
- Script: scratchpad c18/c18_check.py (C:/Users/<user>/AppData/Local/Temp/claude/<session-folder>/<session-folder>/scratchpad/c18/), read-only, with output c18_check_output.txt beside it. Nothing was written under D:/treeroute, no engine file was edited, and no score, pick or verdict changes.
- Paper: edits proposed (not applied by the agent) to M29, C18, Section 2.4, S7.4 (two places), S8.2 (iv), S1 RL12/DE5/DE6, the Figure 2 caption and spec, the S7.10 header/marker/comment and GLOSSARY. Table 1 makes no fallback claim. Owner confirms C18.
- Applied 2026-10-28 in the round-2 apply (paper/draft/review_logs/round2_apply_log.md, edits 18-33; pre-edit copies in paper/draft/_snapshots/20261028T1300Z_round2/apply/), so the bullet above is out of date. The round-2 fix pass then also aligned the Figure 1 caption (and its copy in S7.1) and shortened the Section 2.4 sentence. Still open for the owner: (1) confirm C18 (PAPER_FACTS M29 is now headed "final for the counts; the scored-row reading pending owner confirmation, C18"); (2) the script and its output exist only in the session scratchpad named above, which is not a durable location; copying both, with their sha256, to a durable analysis folder (for example D:/treeroute/analysis/paper_posthoc/c18/) needs the owner's approval. (Noted 2026-10-28 by the round-2 fix pass; paper/draft/review_logs/round2_fix_log.md.)
- **AO addendum (2026-10-28; added by the AO fix pass, paper/draft/review_logs/AO_edit_log.md Part 3; the bullets above are kept as written).** Both items "still open for the owner" above are closed.
  - (1) The owner confirmed the reading in ruling AO3 (engine/OWNER_RULINGS_2026-10-06.md, section AO: "Confirmed: the short-history fallback is in the design but routed no scored row in any run. C18 and M29 are resolved"). The AO edit applied it to PAPER_FACTS M29 and conflict C18, S7.10, and the comments of Section 2.4, S7.1 and the Figure 1 caption (AO_edit_log.md items 15-23).
  - (2) The same ruling keeps the script and its output in D:/treeroute/analysis/paper_posthoc/c18/. The main agent of the orchestrating Claude Code session (<id>, not a subagent) copied them there from the scratchpad named above at 2026-10-28 16:30:02 +0300 (13:30:02Z), in the same command that recorded ruling AO in OWNER_RULINGS (session transcript, tool result at 2026-10-28T13:30:02.214Z; a plain copy, so the folder and file times are the copy time). Files: c18_check.py sha256 18bdaffefd90b2bfdbed3cba02dceee9a8d99019d8d1aa88597b6ff0c839d16e (4,874 bytes) and c18_check_output.txt sha256 44f6886db32a39097039f7779277fd1d6ca93b76005a67e858278e423fc72373 (23,016 bytes); nothing else is in the folder. Both hashes equal the scratchpad files; the AO audit checked this again, and so did the AO fix pass.
  - "C18" in this record is the conflict (PAPER_FACTS section 12), not the last-value fill constant C18 = 2 months (K24).

## Part 625 (POST HOC) - engine-v2 alarm replay re-computed twice (owner ruling AN2, 2026-10-28)

2026-10-28. POST HOC: the alarm was specified after the five v1 runs had been locked, run and scored, with their test labels opened (AE3; V2, A8). Every coral number is also CIRCULAR, because the rule was designed from the same coral test window (A8; Parts 603-604). Coral's 2016-2019 window was set by hand. Report-only: no locked number, verdict or adoption changes, and the alarm has never run on new data. Folder D:/treeroute/analysis/paper_posthoc/v2_replay/ (SPEC.md, INPUTS_SHA256.txt, A/, B/, reconcile/). Nothing was written outside A/, B/ and reconcile/. No file was deleted.
- **Why.** Ruling AN2: the engine-v2 replay numbers (V3, provisional since Part 605) become final, post hoc only after two independent re-computations from the saved files, logged as one post hoc Part. S5.3 had been [PENDING] on this.
- **How.**
  - One spec: SPEC.md 9e674313, listing 108 input files with their hashes in INPUTS_SHA256.txt 90deaa81.
  - A (engine path, `py -3.9 -I -B`): verified engine v2 88f4db2c and LIVE 930d961c, and re-ran tools/alarm_replay.py and tools/alarm_with_without.py into a fresh A/tool_rerun. It then used alarm.batch_keys and decide_alarm, metrics.score_table and alarm_pass.verdict_with.
  - B (independent, `py -3.9 -I -B`, numpy/pandas/pyarrow only): wrote the rule from SPEC section 2 and opened no engine or tool code (read_engine_code []).
  - Both: numpy 2.0.2, pandas 2.3.3, pyarrow 21.0.0. Each took about 2 minutes and well under 1 GB of RAM. No seed was used, and neither read the other's folder.
- **Gates: G0-G9 all pass in A and in B.**
  - G0: A checked all 108 listed files and B the 91 it read; B did not open 17 listed engine, tool and report files.
  - G1: all 23 lines of WITH_WITHOUT.csv match.
  - G2: every batch record, eligibility basis and reference matches.
  - G3: every pooled, year and group score line matches.
  - G4: coral has 15 batches below 30 rows, 275 rows in all; 2016-07 has ratio 25.529655201638473 on 16 rows. No other nowcast has any.
  - G5: all 14 gate row files match.
  - G6: at coral threshold 1.5 the MAE is 6.10878452237827; at 2.5 and 3.0 it is 6.099749549737929. Defo switches nothing at any threshold.
  - G7: the with-alarm verdict blocks match for all five packages.
  - G8, the Part 604 cross-check: method C per programme is AGRRA 1 / 5.540752183604888, FRRP 190 / 7.659652365514182, McClanahan 189 / 35.05979452499404 and Reef_Check 1932 / 3.829490304207522. T = M1 = 6.14748576299595, M2 = M3 = 6.393951387338696, and the whole-window ratio is 4.2913410523963345.
  - G9: replay/WITH_WITHOUT.csv equals the gate file except the 'note' column.
  - B was bit-equal on every gate value and used no 1e-12 tolerance.
  - G7 note from B: SPEC section 4 did not define every verdict field. B took the tag order from engine/PREREGISTRATION_DRAFT.md section 7 and P14, the block valuation from K47 and the blocked-flag rule from that draft's section 8. It inferred groups_better, sign_flip_groups and pooled_contrast from the gate record. All matched bit for bit.
- **Results (POST HOC; coral CIRCULAR). Full values are in PAPER_FACTS K90.**
  - Status (Table S5.1a confirmed):
    - Coral and defo nowcasts: active.
    - pm25 nowcast, pm25 lead 6 and ndvi nowcast: inert_twin_not_simpler.
    - fire nowcast: inert_twin_not_eligible (0.004386949584483835 vs 0.00436777286420139).
    - pm25 12, ndvi 6 and 12, fire 6 and 12, coral 365: declined.
    - defo 1 and coral 183: not_replayable_twin_not_saved.
  - **Coral nowcast:**
    - The twin is arcsine_corrector_unweighted (weighting); its guard is 7.287182963109116 vs base__donor_median 9.74151323420556.
    - R = 0.34056479282671 on 2,046 rows.
    - 48 batches, 33 tested, 11 switched: 2016-01 to 2016-06, 2016-08, 2017-03, 2017-12, 2019-05 and 2019-06.
    - 737 of 2,312 visits switched; 726 changed value.
    - The largest tested ratio is 29.105817502602708.
    - MAE 6.69798924506233 -> 6.119956002798195 (-0.5780332422641354; -8.62995178277203%; -0.6299690271443118 band units).
    - By each batch's own MAE, 4 switched batches were better (2016-03 to 2016-06) and 7 were worse.
  - **Coral by year:**
    - 2016 12.406328256098309 -> 10.681069664805374 (7 batches, 545 visits switched).
    - 2017 3.5692507744181308 -> 3.6880301411805525, worse (2 batches, 80 visits).
    - 2018 1.280418254929322, unchanged bitwise.
    - 2019 4.805509495430039 -> 5.043624464950422, worse (2 batches, 112 visits).
    - Only coral 2017 and 2019 got worse. Every other replayable pass is bitwise unchanged in every year.
  - **Coral by survey programme (NEW for the per-batch rule):**
    - McClanahan (189 visits, 2016): 35.05979452499404 -> 26.64835517575011; 179 switched; contribution -0.6876133378058404, which is 118.96% of the net change.
    - Reef_Check (1,932 visits, all of 2017-2019): 3.829490304207522 -> 3.9568502777756454, worse; 513 switched; +0.1064271059401445 (-18.41%). Its 2016 visits went 5.565007506528706 -> 5.719818003180959; it was worse in 2017 and 2019 and unchanged in 2018.
    - FRRP (190): 7.659652365514182 -> 7.722607016988904, worse; 44 switched; +0.0051736089014693416 (-0.90%).
    - AGRRA (1 visit, not interpretable): 5.540752183604888 -> 0.8690803622182504; contribution -0.0020206192999077154 (0.35%).
    - The contributions leave a residual of 1.1e-15.
  - **Coral outcome-defined subsets, each with its complement:**
    - y>0 (1,024): 13.370101628934457 -> 11.835788785619453; y=0 (1,288): 1.393452691424863 -> 1.5756914301204252.
    - y>=50 (140): 53.12512328455528 -> 40.9865068947793; y<50 (2,172): 3.705448376955049 -> 3.87257242780862.
    - y>23.9575 (239): 41.05202467908258 -> 33.27844301061296; y<=23.9575 (2,073): 2.737249028597863 -> 2.988803858626593.
  - **Defo nowcast:**
    - The twin is log_c_plain_unweighted (tool); its guard is 0.005808902179729096 vs 0.006102746693604387.
    - R = 0.00013719429872479928 on 276,822 rows.
    - 4 batches, all tested, with ratios 1.0619900383296395, 0.9390092273648379, 1.0320192851723704 and 1.1659792695776747. None switched.
    - MAE 0.005415798421978487 with and without.
  - **Unchanged passes (with = without):**
    - pm25: 3.588091134093021, 3.846310424132128 and 4.083558322865165.
    - ndvi: 0.03146059686292064, 0.03956835866470208 and 0.039583272201769236.
    - fire: 0.004385064558301006, 0.006312458723027394 and 0.006310978468756987.
    - coral 365: 8.294498353993655.
    - The inert nowcasts' largest computed ratios (information only, 0 tested) are pm25 1.753861864808271, ndvi 1.749949522314697 and fire 1.847279910383901.
  - **Not replayable:**
    - defo 1: MAE without 0.005407746164567043; 4 batches, all with 30 or more rows.
    - coral 183: MAE without 7.709698984777605; 49 batches, 32 with 30 or more rows; the 17 smaller batches hold 300 rows.
    - The with-MAE, tested and switched values are null.
  - **Information only:**
    - If the 3 small coral batches with ratio > 2.0 had also switched (2016-07, 2017-02, 2019-02; 63 visits), the MAE would be 6.140019322890241 (14 batches, 800 visits).
    - Thresholds: coral 1.5 gives 13 batches, 976 visits and 6.10878452237827; 2.5 and 3.0 give 9 batches, 670 visits and 6.099749549737929. Defo switches nothing at any of the four.
    - Coral forms: F2 per-batch blend 6.382019265777694; F3 = M1 6.14748576299595; F4 = M2 = M3 6.393951387338696.
    - Coral verdict with the alarm: HELPS, 7.873171654763077 [2.405477799042173, 13.34086551048398], 23 of 37 better. Blocked: 8.016229062074508 [2.3522839485988065, 13.68017417555021], flag false. The locked verdict without the alarm is HELPS, 5.206781299700313 [1.9722236985140444, 8.441338900886581]. Regions: 16 better, 6 same, 15 worse.
- **Reconciliation.** reconcile/reconcile_AB.py (`py -3.9 -I -B`, run once without flags; a --dev flag used during writing skips the input re-hash and writes nothing in the folder) gives VERDICT AGREE.
  - 850 checks, 0 failed.
  - All 108 inputs were re-hashed now, with 0 mismatches.
  - The script hashes recorded in A and B and their row-file hashes equal the files on disk.
  - All 25 files of A/tool_rerun are byte-identical to the 2026-10-21 gate targets.
  - 5,270 leaves are present in both result files, after a fixed map of B's field names onto A's:
    - 1,616 floats are bit-equal and 3,434 integers, flags and codes are equal.
    - 0 numbers or codes differ, and the max abs diff is 0.
    - 220 differ only in free-text wording (batch notes, subset and form labels, one formula text, one region note).
  - 183 cross-stored pairs agree, for example B's subset mae_F2-F4 against A's forms and B's recomputed verdict without the alarm against A's locked one.
  - One-sided leaves (A 485, B 1,777): every number or flag among them is confirmed by the recomputation or a cross pair, with 0 unconfirmed.
  - 12 row files are byte-identical in A and B, every column bitwise equal (max abs diff 0). Every column they share with the 14 gate row files is bitwise equal.
  - The script's own recomputation of 5,280 values from the row files (and from the gate row files for defo 1 and coral 183):
    - Against A: 4,036 compared, 0 differ; 3 share percentages are within 1.2e-16 relative (max abs 8.881784197001252e-16).
    - Against B: 5,016 compared, all equal.
- **Files (sha256), all under v2_replay/:**
  - SPEC.md 9e6743133d75e94b0d3bc4dd1debb5b20f31615fb2c6188d59189abb6ec8d00e
  - INPUTS_SHA256.txt 90deaa81977de57867560234975a0725ae3c7a1124b226cb9a629ff16bb7ba79
  - A/replay_A.py df5d0306879753fafb9c235fd006b9b9645fd39c616462ed5a860d11ceb41316
  - A/result_A.json 3d04553cf50e19c57f40eab66c9d223fe1fd21e91c48da939111ad216167d7e5
  - A/run1.log 41ba90bf47e995bca3b34d95a86565fe1c4dc8637f496e1ee5fba476be1d451e
  - B/replay_B.py 42a97b0fa9a8c47833d805e2fa44ef3aa86c352fa9819435a86953f5e9563924
  - B/result_B.json 258f5c1f7b2a1b7d28452a98b28d07bde4980b773213a92f3a945211ba775a5f
  - reconcile/reconcile_AB.py 6f1fdd715354c377c6f3babc57f29af9cbd78d16b16faaa242287f3ff3fcd620
  - reconcile/reconcile_AB.json 212dcce934d891641d8572c2203ed3f75c01dc263a78b4b3e4e7826ea60284ae
  - reconcile/reconcile_AB.log 837f3a273afb25b562aa2a77126921b961ff6f6bf506d52fd0c7a4b1730f0145
  - Row files, A = B:
    - rows_pm25_lead_0 75a95cc6..., lead_6 8c550e1a..., lead_12 581c3109...
    - rows_ndvi_lead_0 a27750f6..., lead_6 97fb2710..., lead_12 841a9835...
    - rows_fire_lead_0 4d039974..., lead_6 9807f747..., lead_12 9a878766...
    - rows_defo_lead_0 52c71652...
    - rows_coral_lead_0 036f0c4f..., lead_365 66837187...
    - Full values are in reconcile_AB.json environment.file_sha256.
- **Paper (proposed; to be applied by the drafting step):**
  - PAPER_FACTS: K90 (new); V3 re-statused to final, post hoc (Part 625), with the 'silent at the other four nowcasts' wording split per SPEC O5; a pointer in fact S5.
  - S5: S5.3 filled with Tables S5.1b-S5.4, each labelled post hoc, coral circular, window set by hand, never run on new data.
  - S3: S3.12 and an index row, with no alarm number.
  - S1: PH17 updated and PH21 added (post hoc 20 -> 21, total 169 -> 170).
  - S4: header, timeline, S4.3, Table S4.11 row 625 and 20 register rows in Table S4.14.
- **Owner items (SPEC section 11, open):**
  - O1: should the F2 per-batch blend go in S5?
  - O2: should the with-alarm verdict and region counts go in S5?
  - O3: should the small-batch counterfactual and threshold check go in S5 text, or stay in the Part only?
  - O4: should the q75 subset go in S5?
  - O5 wording (applied in the V3 proposal): to be confirmed.
- **Round-2 fix pass addendum (2026-10-28; paper/draft/review_logs/round2_fix_log.md; no file under v2_replay/ changed).**
  - Applied 2026-10-28 in the round-2 apply (paper/draft/review_logs/round2_apply_log.md, edits 34-60; pre-edit copies in paper/draft/_snapshots/20261028T1300Z_round2/apply/), so "Paper (proposed; to be applied by the drafting step)" above is out of date.
  - How, run time and RAM: only A's run time is recorded (A/result_A.json elapsed_seconds 86.57, about 87 s). B/result_B.json has no run time, and A, B and A/run1.log hold no peak-RAM record. "Each took about 2 minutes and well under 1 GB of RAM" rests only on A's 87 s; B's time and both RAM figures have no record.
  - Reconciliation, one pair is not like for like: the 'silence' map of reconcile_AB.py pairs B's largest_ratio_computed_information (B/replay_B.py line 600: the maximum over ALL batches, small ones included) with A's largest_ratio_ge30_information (A/replay_A.py line 1304: the maximum over batches with at least 30 rows). The 5 values agree only because of the data: coral's largest ratio, 29.105817502602708 (batch 2016-06, 51 rows), is above its small-batch maximum (2016-07, 25.529655201638473), and no other nowcast has a batch under 30 rows. No reported number is wrong, but these 5 leaves are not a like-for-like match.
  - Recomputation, exact wording: the script recomputed 5,280 values; the 4,036 that A reports and the 5,016 that B reports were compared and all agree (3 share percentages within 8.881784197001252e-16); 20 values (batches_spanning_two_years by year) are in neither file. PAPER_FACTS K90 and S3.12 said the 5,280 values "equal both"; both are reworded.
  - B's independence: per the G7 note above, B also used engine/PREREGISTRATION_DRAFT.md sections 7-8, P14 and K47 for the verdict fields, and inferred groups_better, sign_flip_groups and pooled_contrast from the gate record, so B's with-alarm verdict (owner item O2) is not fully independent of the earlier replay. S5.3 and S1 PH21 no longer say "from the specification alone"; they say A and B agree on every number, flag and code they both report (220 free-text entries differ in wording).
- **AO addendum (2026-10-28; added by the AO fix pass, paper/draft/review_logs/AO_edit_log.md Part 3; the bullets above are kept as written).** The owner items listed above as open (O1-O4, and O5 "to be confirmed") are settled by ruling AO2 (engine/OWNER_RULINGS_2026-10-06.md, section AO):
  - S5 shows all four extra post hoc items, each labelled post hoc and, on coral, circular: O1 the per-batch even blend; O2 the verdict with the alarm and its region counts; O3 the small-batch counterfactual and the threshold check; O4 the upper-quartile subset beside its complement.
  - O5: the wording "cannot act" vs "could act, nothing switched" is accepted.
  - Applied in S5.3 and in PAPER_FACTS V3 and K90 by the AO edit (AO_edit_log.md items 1-14), with wording fixes after the AO audit (same log, Part 3). No number of this Part changed. Nothing under v2_replay/ was written, so SPEC.md section 11 (read-only) still lists O1-O5 as open.

## Part 626 (BUILD) - per-location ablation built and timed (owner rulings AK4(b), AN4)

2026-10-28. BUILD only: no full run was started (ruling AN4: the agent reports the time to the owner first). The design is post hoc: it was built after the test results were seen. Nothing here is a result.
- **What is saved.** No headline run saved tree answers per row:
  - the tree-answer tables were temp memmaps, deleted during the run;
  - each run removed its own bank checkpoints at the end (runs/ndvi/_checkpoints keeps only older census and R30 folders);
  - inner_preds.parquet and test_preds.parquet hold router outputs, not tree answers;
  - the AK4(a) saved-arm table (Part 622, R15) does not vary the pooling axis.
  So the ablation must refit the trees in a full nowcast refit. Refitting only the routers is not possible.
- **Built.** Folder D:/treeroute/analysis/ablation_perlocation:
  - files: ablation.py (sha256 19df9542), test_math.py (828ca714), bench_kernels.py (db2e7707), machine_ablation.yaml (d73638f2), PLAN_AND_TIMING.md;
  - engine use: it imports the LIVE engine (930d961c) read-only, through the engine's own launcher, Pipeline and RunState steps. The GLS weight model is not fitted. Every engine-made file goes under that folder (engine_runs/, engine_tmp/).
- **Four arms.** All at the nowcast, on the same test rows, with the adopted link and answer type:
  1. plain average of the tree answers each row may use;
  2. one ridge pooled over all regions, with the region router's estimator and the normal unpenalised; masked answers are filled with the row's plain average;
  3. one ridge per region;
  4. the per-location router (the engine's PassRouter, at the locked headline penalty).
  Arms 2 and 3 pick their level on the decision surface, over the region grid (lambda = 100 x level, 7 levels). Their default fit rows are the scored locations' own router fit rows (--fit-rows scored). The option --fit-rows bank runs the engine's region router on capped bank locations.
- **Gates.**
  - 0: both refitted banks' fingerprints and c equal the headline's; checked right after each bank fit (fail fast).
  - S: the decision-surface rows and labels equal the headline's.
  - A: arm 4 at all 35 grid points equals inner_preds.parquet (max abs diff 0).
  - R: the test rows equal the headline's.
  - B: arm 4's test predictions equal the headline column (max abs diff 0), checked before any other arm is scored.
- **Gate result.** The headline gate was NOT run: it needs the full refit.
  - On the engine's smoke worlds (4 regions x 40 locations x 12 trees), all five gates passed with max abs diff 0: PM2.5 under both fit-row options, and NDVI. They passed both through the engine's own fit and through the ablation's headline fit path.
  - test_math.py: arm 3 matches the engine's region_ridge to at most 2.3e-8 relative; arm 2 matches a dense float64 solve to 1.7e-15.
  - On the PM2.5 smoke, arm 3 matches the engine's region router to 1.0e-6 relative.
  - Smoke arm MAEs carry no sign information and are not results.
  - The first smoke run had an arm-2 bug. test_math.py found it, and it is fixed; the folder is kept and marked superseded.
- **Time.** Estimated from the headline runs' own logged step times on this machine, plus kernel timings at full shape.
  - PM2.5: about 7.3 h (census 50 min, derive 3.5 h, pool 39 min, two banks 47 min, two router walks about 1.4 h).
  - NDVI with a fresh derive: about 24 h (R30 about 17.8 h).
  - NDVI with the old NDVI census and R30 checkpoints migrated by copy: about 6.6 h. That needs a ruling like R2.
  - --fit-rows bank adds about 22.5 h (PM2.5) and about 23.5 h (NDVI): the shipped region solve takes about 60 s per level at 12,600 trees.
- **RAM and disk.**
  - Peak RAM: about 6 GB (PM2.5) and about 6.5 GB (NDVI). Start with at least 9 GB free.
  - Disk: engine temp about 3 GiB (PM2.5) and 8 GiB (NDVI). The kept checkpoints take about 1.5-2 GB per problem. D: has 41 GB free.
- **Owner items (PLAN_AND_TIMING.md section 7):**
  - D1: the fit rows of arms 2-3;
  - D2: the arm-2 fill rule;
  - D3: the router context is in arm 4 only;
  - D4: edge picks on the region grid;
  - D5: NDVI fresh derive, or checkpoint migration;
  - D6: whether and when to run (before about 12 Nov, per AK4);
  - D7: the wording (post hoc, every arm reported).
- The commands are in PLAN_AND_TIMING.md section 6.
- **Round-2 fix pass addendum (2026-10-28; paper/draft/review_logs/round2_fix_log.md). Text only: nothing rebuilt or run; ablation.py unchanged (19df9542); PLAN_AND_TIMING.md edited, its pre-edit copy PLAN_AND_TIMING.md.before_fix beside it.**
  - Three run risks that PLAN_AND_TIMING.md states and this entry did not:
    1. The LIVE engine (930d961c) is not the code that made the PM2.5 and NDVI headline runs (code hashes 7b508557 and 65a177bc, comment-stripped 6d19c3e2 and 13838e41; fact M1). Gates 0 and B on the real headline therefore rest on evidence (every later engine change passed a byte-identical smoke no-op proof), not on proof.
    2. Gate 0 is first reached about 5.6 h (PM2.5) or about 22 h (NDVI, fresh derive) into a run, so "fail fast" means failing at the first bank fit, not at the start.
    3. The ablation uses its own temp root (engine_tmp/), so the engine's heavy-job lock in D:/treeroute/tmp cannot see it; no other engine job may start while it runs.
  - Correction to "the folder is kept and marked superseded" (Gate result): the first smoke folder, out/pm25_smoke_scored_20261028_145514, carries no mark itself and still holds its arm-2 outputs from before the fix. It is listed as superseded in PLAN_AND_TIMING.md section 4 only.
  - Correction to "Four arms", arm 1: as built, arm 1 is an UNANCHORED plain average, with no intercept, no normal and no fit (ablation.py GroupHook.on_group: As.mean(axis=1)). PAPER_OUTLINE O26 describes "a uniform average of the masked trees anchored to the normal", and before the round-2 apply it said "plus the normal offset". The build took a third option that D1-D7 did not list. Against arm 4, arm 1 as built changes anchoring and per-location weighting at once.
  - Arms 3 and 4 differ in more than pooling, even with --fit-rows scored: router context (arm 4 only, D3), penalty form (one trace-normalised lambda on the 7-level region grid, against two blocks a_tree/a_ctx on the 35-point grid), search breadth, and whether the intercept and the normal's weight are shared per region or fitted per location. Arm 2 adds the row-average fill (D2). D1's "It isolates pooling" is reworded in PLAN section 7: "It holds the fit rows equal; pooling is still confounded with context and penalty form unless arm 5 (D9) is added."
  - Tuning: arms 2 and 3 search a region grid centred at lambda 100, which is test-exposed (fact M24; engine constant C12); both smoke worlds picked its lowest level, so the pooled arms may be over-shrunk. Arms 1-3 use the link and answer type that the adaptation layer adopted for arm 4, and arm 4's test score is already known (the headline). Scope (AN4): PM2.5 and NDVI nowcast only; burned fraction is not in the build, as its adopted arm is error-weighted and the GLS weight model is not fitted; NDVI's architecture was chosen on its test years (N11).
  - New owner items (full text in PLAN_AND_TIMING.md section 7):
    - D8: arm 1's anchor. (a) no normal, as built (label it "unanchored plain average"); (b) the normal added as it is, weight fixed; (c) the normal with its weight fitted (proposed "arm 1b": per location, an unpenalised fit of [1 | n_u - mean(n_u) | mean of the allowed T] on the same router fit rows). Also: report arm 0, the trees-off fit, as each problem's reference row; it is saved in the headline test_preds.parquet and needs no refit. (b), (c) and arm 0 are not built. PAPER_OUTLINE O26 is aligned to whatever the owner rules.
    - D9: arm 5, the region-router estimator fitted per location (region_ridge_dual with the group set to one location, no context, the same 7-level surface search), so that arms 2, 3 and 5 differ only in pooling scope and arm 5 vs arm 4 measures context plus penalty form. Not built; its cost is not measured (time it with bench_kernels.py first).
    - D10: a reading rule written before the run: (a) a surface-only grid extension for every searched arm (extend downward by factors of 10 until the pick is interior, at most 3 extra levels; record surface MAE by level and edge status for every arm, arm 4 included); (b) primary contrasts arm 2 vs 4, arm 3 vs 4 (and arm 5 vs 4), with pooled MAE, the per-region contrast_tag with the headline band, region counts better/same/worse, anomaly R2 and hit rate against the normal; (c) the shared-link disclosure; (d) the scope above.
  - D7 wording addition: with --fit-rows scored, call arm 3 "one ridge per region with the region router's estimator on the scored locations' rows", not "the region router".
  - Owner items are now D1-D10. Do not start the 7-31 h run before D8-D10 are decided.

- **Ruling AP addendum (2026-10-28; workflow <id>-d8c: build, 3 independent verifiers, fix, readiness check). BUILD ONLY: no real-data run; everything post hoc.**
  - **Design (AP1):** seven arms on the headline nowcast test rows, all reading the same masked tree answers with arm 4's link and answer type: arm 0 the saved trees-off column (a fatal check requires the run's own trees-off to equal it); arm 1 the unanchored plain average; arm 1b per location an unpenalised fit of [1, normal, plain average]; arm 2 one global ridge; arm 3 one ridge per region; arm 4 the headline per-location router at its locked point; arm 5 one ridge per region with arm 4's context columns. Arms 1b, 2, 3, 5 fit on the per-location routers' own fit rows (D1 a). Scoring uses the engine's own path (score_table, group jackknife, contrast_tag, each problem's headline band); check V requires arm 0 vs arm 4 to reproduce the locked headline verdict exactly, and a failed V means no tag is read.
  - **Smoke gates (LIVE 930d961c, ablation.py da358596, re-run 18:36-18:41):** gates 0, S, A (35 points), R, B and the arm 0 checks max abs diff 0 on PM2.5 scored, NDVI scored and PM2.5 bank; arm 1b plumbing <= 2.3e-8 (limit 1.8e-6); check V all 0; test_math.py ALL OK. Real-data gates are reached only inside the full runs. Smoke numbers are not results.
  - **NDVI checkpoint proof (D5): PROVEN** (checkpoint_proof.py ea3b184b): only the engine-code key part differs (R30: plus the census key); old keys recovered exactly with the old values; engines 65a177bc and dd7c0984 rebuilt and hash exactly; every one of the 14 census/R30 code changes 7a0341ef -> 930d961c has a written no-effect reason; probe payloads byte-identical; the old folders are the headline's own inputs (98/98, 133/133, 133/133 records). Caveat: R30 pass-1 RAM-dependent counters differ, as between two runs of one engine. Not copied yet (BLOCK 2 copies, never moves).
  - **Reading rule (D10):** READING_RULE.md sha256 3e24e9c3d20415a3e356d5b22f0598f2b93b25e229a14dc95d205fcec1c84618 (first version 870f3894 kept as .before_AP), pinned in ablation.py and check_run.py (a run refuses on mismatch). Primary contrast arm 5 vs arm 4 per problem; section 4a: a HELPS against an edge-picked arm 5 is not read as support; 4b maps each tag to what the paper says.
  - **Verifier finding (blocker, owner decision, OPEN):** arm 5 differs from arm 4 in its penalty form as well as in pooling (centred region-level scaling vs arm 4's raw per-location scaling, K16; lambda = 100 x level on 7 levels vs a_tree = 0.5 x level on 35 points). On the PM2.5 smoke about two-thirds of the arm 5 - arm 4 gap came from the penalty form (0.170 -> 0.054-0.063). Options (FIX_LOG_AP.md): A as built, disclosed; B the engine's per-location solver fitted on each region's pooled rows (+20 min PM2.5, +29 min NDVI, measured); C both, B primary; b extend the grid. The owner's agreement to run it predates the finding. No run starts before the owner answers.
  - **Files:** ablation.py da358596, check_run.py 74a2d73c, checkpoint_proof.py ea3b184b, test_math.py 070ddd92, RUN_COMMANDS.txt 78d03643, READY_REPORT.md, FIX_LOG_AP.md; each changed file has a .before_AP copy; nothing written outside D:/treeroute/analysis/ablation_perlocation; nothing deleted.

- **PAUSED 2026-10-28 19:46 by the owner, who asked, because of the usage limit, for the work to be stopped and saved until the next week or until the owner gives the word.** The ruling AQ rebuild (workflow <id>-7dc, task <id>) was stopped by the agent while its FIX step was running: build and both verifiers had finished; the fix agent had begun editing at 19:40 (ablation.py 19:42, READING_RULE.md 19:41 and test_math.py 19:10 differ from their .before_AQ copies, which hold the pre-AQ state). The folder is therefore MID-FIX and NOT READY: the reading-rule hash pins may not match and the smoke gates were not re-run after the last edits. Do NOT start any ablation block. To resume: Workflow resume with resumeFromRunId <id>-7dc (build and verify replay from cache; the fix step re-runs and must first re-check each issue against the current, partly fixed files), then the Ready step. Nothing was deleted; the LIVE engine was not touched.

- **DROPPED FOR SUBMISSION 2026-11-09 (owner ruling AR: the owner agreed to drop it).** No ablation block runs before submission. The folder stays MID-FIX and untouched; nothing was deleted. For a run in the revision, see ruling AR2: a new workflow finishes the AQ fix; the owner removes engine_tmp's stale lock and the orphan .mm files by hand; under the new machine's junction, NDVI needs a fresh derive (about 25 h) unless the project sits in a real folder at the old path.

## Part 627 (SIGNED BY THE OWNER 2026-10-28; RUN 2026-10-29, ALL 12 CHECKS PASSED) - coral 2017-2020 sensitivity row (owner rulings AN3, AO1)

2026-10-28. PREPARED, NOT RUN. No model was fitted and no test score was read. AN3 (owner, 2026-10-28): "The declared coral 2017-2020 sensitivity row is run now, as declared, and reported whatever it shows (post hoc in timing, labelled so). It runs from a copy of the settings; no LIVE engine file is edited." Folder: D:/treeroute/analysis/coral_sens_2017_2020 (RUN_COMMAND.txt, SENS_LOCK_PREPARED.json, builder/, coral_data/, package/coral_sens_2017_2020/, tools/, validate/, run/ empty).

- **The declaration** (engine/PREREGISTRATION_DRAFT_coral.md 4.2; ruling V3, OWNER_RULINGS_2026-10-06.md:105: "2017-2020 is a declared sensitivity row"):
  - "Declared now, never the headline. It is reported beside the headline after the headline run, one heavy job at a time. It cannot change the verdict, the adoption or any choice."
  - "the sensitivity row gets its own short Part and lock before its run (builder hash, package fingerprint, engine hash)."
  - "The sensitivity Part must therefore name how the mark is made: a DRAFT stamp with a lock written outside the freeze tool, or a named not-headline reason (an engine change, needing its own no-op proof). It is decided in that Part, never from a result."
  - Steps: (1) `build_visits.py --test-years 2017-2020 --out D:\treeroute\coral_build\coral_data\sens_2017_2020`; "The 2020 visits are then written as test rows." (2) "A small builder option `--visits-dir DIR` for stage 2 and the checker". (3) `build_tables.py --build full` and `check_tables.py --build full` with it. (4) make_split: "the V5/V6 lists are recomputed for that window ... under V6 (b) (ruling W), with the (b) make_split.py ... (SHA-256 a69e1c8c...)". (5) "A package copy `coral_sens_2017_2020` with its own name, store line and split.yaml, its header saying \"declared sensitivity row (V3); never the headline\". R3 gives 2020, R5 2017-2020; every cut moves one year later." (6) "From LIVE: check, smoke, run, at the same engine hash as the headline run."
  - Section 7: "Not a verdict: the sensitivity row". The ingest README: "Reported with a not-headline reason".
  - **Re-fitted:** the marks, the lead tables, the V5/V6 lists, and every engine fit at cuts one year later. **Held fixed:** the engine hash, the features and their code, and every package file except the name, the store line, split.yaml and the header.
  - **Reported:** not specified beyond "beside the headline" (outline: one sentence).
- **Settings diff** (validate/settings_diff.txt):
  - Builder copies:
    - build_visits.py (95a079bc; original fede282d): only the --out guard and default changed, to the analysis folder.
    - build_tables.py (a035122f; original b1f22ee7): the declared --visits-dir (required; must lie under the analysis folder; it sets the visit table, the output folder and _moved), and --publish refused.
    - check_tables.py (5e909627; original 13756d9b): --visits-dir.
    - make_split.py (760ef98d; original the (b) file a69e1c8c): the write guard and defaults name the analysis folder; the header cites ruling W1 and adds "Declared sensitivity row (V3); never the headline". The rules are unchanged.
    - columns.py and npz_map.py: byte copies.
  - Package coral_sens_2017_2020 (fingerprint 6a8509e3...; headline coral 5b9383f0...):
    - name and store line (coral_data/full/lead_{lead}.parquet);
    - a new header (the old one kept verbatim below it);
    - description prefixed "DRAFT -- declared coral 2017-2020 sensitivity row (ruling V3; run under ruling AN3), never the headline." This is the not-headline mark;
    - split.yaml regenerated;
    - catalog, ban, exceptions, AUDIT_CHECKLIST and ingest/README are byte copies.
- **Stage 1** (run by the agent, seconds; builder copy, `--test-years 2017-2020`):
  - The same 14,839 visits as the headline stage 1, every column equal except `mark`: 942 visits of 2016 test->train, 38 of 2020 unused->test.
  - Census cuts: L0 fit 2016-12-31, inner 2013-12-31; L183 fit 2016-07-02, guard 2013-07-02; L365 fit 2016-01-02, guard 2013-01-01.
  - SHA-256: visits.parquet 620affd3; census 3995e9a5; month list cfa18268 (= the headline list coral_report.py pins).
- **Split** (make_split copy --write, then --check: CHECK PASS):
  - V5: the same 11 groups (25 test, 19 train visits).
  - V6 (b): 57 donor-only groups (headline 46).
  - Scored: 26 ecoregions, 1,468 test visits on 763 sites (2017 565, 2018 443, 2019 431, 2020 29), **all Reef Check**. The headline's FRRP 190, McClanahan 189 and AGRRA 1 test visits were all in 2016.
  - 12,211 train visits; 2,277 decision-surface rows (2014-2016).
  - 1,439 of the 1,468 test visits are headline test visits, whose labels the headline run opened.
  - 11 headline-scored ecoregions become donor-only; none is new.
- **Validation** (no fit, no test score):
  - (a) Tiny build through the copy (176 visits: all 2020 visits plus every 100th row; 0.7 min) and its checker: RESULT PASS, 52 checks.
  - (b) Bit-for-bit comparison with the published headline lead tables: 138 common rows x 3 leads, 0 differing non-mark cells; mark changes only in 2016; the 29 extra rows are all 2020. The builder inputs' SHA-256 equal the headline build manifest's.
  - (c) The engine's own loader: name, fingerprint, DRAFT stamp read as the not-headline reason.
  - (d) Engine `check` (quick) and `plan` (dry run) on a VALIDATION PREVIEW copy (headline rows re-marked plus the 29 tiny-built 2020 rows; validate/preview_*):
    - green;
    - R3 2020, R4 1994, R5 2017-2020, R6 2016, R7 inner fit 1994-2013, inner score 2014-2016;
    - T-MARK 12,211 train / 1,468 test; 83 groups; router neighbour; leads 183/365;
    - not_headline_reasons = [DRAFT package ...];
    - 99 of 120 derived entries equal the headline's; the 21 that differ are the window, cuts, marks, donor-only, units, bank plans, R23 and U1;
    - the manifest engine hash, modules, constants, versions, launch backend and threads equal the headline's;
    - preview derived_sha256 574d0805.
  - (e) **The declared check --deep and smoke REFUSE by construction:** [R5] T-MARK, "test years [2016, 2017, 2018, 2019]". Both derive the window on the four R21 groups (Andaman Islands, Andaman Sea, Austral Islands, Bahamas and Florida Keys), none of which has a 2020 visit (validate/preview_check_deep.log; smoke plan probe, no fit: validate/probe_smoke_fulldeep.log). A full-size deep check on all 83 groups (side record, ruling M2) is GREEN.
- **LIVE engine untouched:**
  - engine_code_sha256 930d961c... and engine_code_hash 85c64b55... before and after.
  - hash_tree over 9 roots (engine/treeroute 241 files, treeroute_report, runner, config, datasets/coral, both builder originals, the headline store, the headline run folder): UNCHANGED, mtimes included (validate/compare_hashes.log).
  - Every engine call ran with `py -3.9 -I -B` through tools/launch_engine.py (sys.dont_write_bytecode), so no .pyc was written.
- **Lock:** SENS_LOCK_PREPARED.json (SHA-256 d0d6bb85...). It is written outside the freeze tool, binds on the owner's signature of this Part, and pins the builder, package, stage-1 and tools hashes.
- **Owner's run:** RUN_COMMAND.txt (SHA-256 9cb10e1b...).
  - Stage 2: about 26 min (headline 26.4).
  - Checker: 6-10 min.
  - Split, feature and engine checks: seconds.
  - Full-size deep check, plan, then run: about 35 min (headline run 35.7 min; not measured for this window).
  - check_after_run.py, then a hash re-check.
  - Resume: re-run the same command.
- **Owner items (open):**
  1. Accept the deep-check/smoke substitute: full-size deep check, smoke skipped.
  2. Confirm the DRAFT stamp + outside lock as the not-headline mark. The other option needs an engine edit, which AN3 and step 6 exclude.
  3. Accept the location: analysis folder and builder copies, not coral_build/coral_data/sens_2017_2020.
  4. The package texts kept verbatim still describe 2016-2019 and its counts.
  5. Which numbers the one sentence reports. coral_report.py and the headline-table builder refuse a DRAFT run.
  6. Disclose: the test set is Reef Check only, 26 ecoregions, 98% headline test visits.
  7. Sign this Part before the run.
- **Round-2 fix pass addendum (2026-10-28; paper/draft/review_logs/round2_fix_log.md). No file in the coral_sens_2017_2020 folder was changed; the lock and tool hashes above stand.**
  - Machine-file use not recorded above: the preview `plan` (validate/preview_plan.log, from 14:49:20) and the smoke-plan probe (tools/probe_smoke_and_fulldeep.py, which calls TablePipeline(..., load_machine(), ...); validate/probe_smoke_fulldeep.log, from 14:51:08) ran with the engine's default machine file (engine/config/machine.yaml, temp_dir D:/treeroute/tmp). The engine's plan step takes its heavy-job lock in that folder and releases it (pipeline/run.py, Pipeline.plan -> _lock), and the engine removed what it made: D:/treeroute/tmp is empty, folder time 14:51:08. The engine's check (quick and --deep) takes no lock. D:/treeroute/tmp is not a protected root, and no engine or run file changed (hash_tree above). This was the unnamed source of that folder time in the ablation's PLAN_AND_TIMING.md section 3 (now corrected there).
  - Item 5 should be settled before the run, not after it. As it stands, check_after_run.py prints each run on its own test set, so the 2016-dominated headline (2016 MAE 12.406 inside a pooled 6.698; fact K90) would sit beside the quieter 2017-2020 years, mixing the change of window with the method's behaviour. A proposal for the owner (not decided here): report both runs on the 1,439 visits they both score (2017-2019; the headline's 565 + 443 + 431 test visits): each run's final answer, its training median and predict-zero; beside that, the sensitivity row on its full 1,468 visits (verdict tag, contrast and interval). That needs a new read-only matched-visit tool in this folder. It is not written: SENS_LOCK_PREPARED.json pins each of the 14 tool files by hash, so adding a tool means re-writing the prepared lock or adding to it (owner).
  - Item 6, proposed full disclosure for the one sentence: 2016 lies in this row's inner score window (2014-2016, 2,277 decision-surface rows) and in its training (942 visits of 2016 moved from test to train), and 2016 is the year the post hoc diagnosis (A7, Part 601) linked to the headline's arm reversal; the test set is Reef Check only (26 ecoregions); 1,439 of its 1,468 test visits (98%) were headline test visits whose labels were already opened; so the row is not independent of the headline.
- **OWNER SIGNATURE (2026-10-28).** The agent asked: "Coral 2017-2020 check (Part 627) is ready. It needs: a full deep check instead of the two declared checks that can't work; a 'DRAFT, never headline' mark; files in the analysis folder instead of the protected coral folder; the disclosure that 1,439 of its 1,468 visits were already scored and all are Reef Check. Approve and sign so you can run it (~75 min)?" The owner chose the recommended option, to approve all and sign Part 627. That option read: "I record your words as the signature, write the reported numbers into the Part (verdict, contrast with interval, MAE vs the median and predict-zero, beside the headline), and give you the command." Recorded as owner ruling AO1.
  - Items 1 (full-size deep check; smoke skipped), 2 (DRAFT stamp + the lock SENS_LOCK_PREPARED.json d0d6bb85 written outside the freeze tool as the not-headline mark), 3 (analysis folder and builder copies), 4 (package texts kept verbatim), 6 (disclosure) are approved; item 7 is this signature. The lock binds from now.
  - **Item 5, the reported numbers, fixed before the run (no result has been read):** (i) the row's verdict tag, contrast d and interval against the training median, as check_after_run.py prints them; (ii) pooled MAE of our final answer, the training median and predict-zero on the row's own 1,468 test visits; (iii) per-year MAE of our final answer and the median for 2017, 2018, 2019 and 2020, printed beside the headline's own per-year values for 2017-2019 (already in the record: fact K90 / Figure 4b), so years are compared with years and the 2016-heavy headline pool is never set beside the quieter 2017-2020 pool; (iv) the 183- and 365-day ladder as check_after_run.py prints it; (v) the disclosure: Reef Check only, 26 ecoregions, 1,439 of 1,468 test visits are headline test visits whose labels were opened, 2016 is in this row's training and inner score window. The shared-visit comparison tool proposed in the round-2 fix pass is NOT built (it would change the signed lock). Per-year values (iii) are computed after the run by a small read-only script from the run's test_preds.parquet, logged in this Part.
  - The run is the owner's: RUN_COMMAND.txt (9cb10e1b) in their own window, one heavy job at a time, browser closed (the runner waits for 7 GB free RAM), PC left on.
- **Part 621 addendum 4, continued (logged 2026-10-29):** D2 FINISHED at 2026-10-29 00:40:03 (run_D2.log): 23 new, 17 already done, 0 failed, 40 of 40 files on disk, 1.73 GB, 495.8 min. Lock released (locks folder empty). Next fire Part B steps (owner OD rulings, F5, full suite, F7 DRY) wait for the session to resume.
- **RUN (2026-10-29 12:08-13:15, the owner's window, D:/treeroute/analysis/coral_sens_runner/RUN_ALL.ps1 = the RUN_COMMAND.txt steps in one script; 67 min).** All 12 steps passed: stage 2 build (26.0 min, peak 1.38 GB; lead files 13,723 / 13,715 / 13,715 rows, 1,493 test); checker RESULT PASS (52 checks); split CHECK PASS (26 kept, 57 donor-only, 1,468 kept test rows); features bit-for-bit vs the headline (0 differing cells; 883 mark changes all in 2016; 29 extra rows all 2020); engine check quick green; full-size deep check GREEN (83 groups, 0 refusals); plan 20261029_75f66839 (R5 2017-2020, T-MARK 1,468 test / 12,211 train, DRAFT reason present); run finished (run folder D:/treeroute/analysis/coral_sens_2017_2020/run/coral_sens_2017_2020/headline/20261029_75f66839); check_after_run PREPARED-AS-DECLARED CHECKS: PASS (engine 85c64b55, modules/constants/versions/launch/threads equal the headline's); protected folders RESULT: UNCHANGED (engine treeroute tree 674ae64d, headline run folder db64d2a6). Console logs in D:/treeroute/analysis/coral_sens_2017_2020/logs/. The keep-awake call in RUN_ALL.ps1 failed (UInt32 cast; non-fatal; fixed in the file afterwards, copy RUN_ALL.ps1.before_fix); the owner kept the PC awake from a second window.
- **RESULT (sensitivity row, post hoc in timing, DRAFT, never the headline; the locked headline verdict is unchanged):** adopted arcsine_corrector_unweighted at level 30, ratio 1.0 (headline: arcsine_corrector_gls); not declined. Nowcast verdict **CANNOT TELL**, contrast **-0.700 [-1.943, +0.543]** (band 0.1664; 26 groups; 1,468 test rows). Pooled MAE: our final answer **3.4829**, training (donor-row) median **3.1531**, **predict-zero 2.6662**, adopted-link trees-off 3.4116. Ladder: 183 d CANNOT TELL (guard passed: 13.8147 vs median 15.4342 on 1,915 rows), 365 d CANNOT TELL (guard passed: 11.1144 vs 12.613 on 1,404 rows). Headline beside it (2016-2019, check_after_run): HELPS +5.207 [+1.972, +8.441], 37 groups, 2,312 rows, MAE 6.6980 vs median 8.2945, predict-zero 8.0998.
  - Plain reading (agent): on 2017-2020 our final answer's MAE is about 10% ABOVE the median's and predict-zero is lowest; the interval includes zero. The headline coral win does not carry over to the window without 2016. Disclosure as signed: Reef Check only, 26 ecoregions, 1,439 of 1,468 test visits already scored in the headline, 2016 inside this row's training and inner score window.
  - Still to do (on resume): item (iii) per-year MAE 2017-2020 beside the headline's per-year values (small read-only script on test_preds.parquet); the run-folder hashes; PAPER_FACTS fact; the one sentence in Section 4 plus S3/S1/Table 4 entries.
  - **Item (iii) per-year values (2026-11-09, read-only, from the run's own per_year.csv, sha256 b6c43c5c..., line "key").** Weighting the per-year values by n reproduces the pooled MAEs exactly (3.4829, 3.1531, 2.6662 on 1,468 visits).

    | Year | n | Ours, sensitivity row | Training median | Predict-zero | Headline ours (2016-2019 run) | Headline median |
    |---|---|---|---|---|---|---|
    | 2016 | 873 | not in this window | | | 12.406 | 16.826 |
    | 2017 | 565 | 3.392 | 3.253 | 2.808 | 3.569 | 3.231 |
    | 2018 | 443 | 1.408 | 1.539 | 0.844 | 1.280 | 1.507 |
    | 2019 | 431 | 5.383 | 4.644 | 4.304 | 4.806 | 4.627 |
    | 2020 | 29 | 8.724 | 3.707 | 3.410 | not in that window | |

    Headline values: D:/treeroute/runs/_headline_tables/coral/per_year_7dde14b4e308.csv, lead 0, rows all (fact K90). The sensitivity row's columns are arm__arcsine_corrector_unweighted (its adopted arm, not declined), base__donor_median and base__predict_zero. Plain reading (agent): year by year, both runs are worse than their training median in 2017 and 2019 and better only in 2018; the sensitivity row is also worse in 2020 (29 visits). The parquet cross-check named in the signature ran on 2026-11-09 at 22:55, after the new machine's setup passed all 8 checks (D:/treeroute/analysis/coral_sens_2017_2020_report/peryear_from_parquet.py, run with py -3.9 -I -B; output peryear_from_parquet.csv beside it). It read the 1,468 labelled test rows of test_preds.parquet and recomputed the per-year and pooled MAE of the three columns: RESULT: MATCH (all 15 values to 4 decimals). Item (iii) is DONE.
  - **Run-folder hashes (2026-11-09, read-only):** SHA-256 of all 68 files is in D:/treeroute/analysis/coral_sens_2017_2020_report/run_folder_hashes.json (file sha256 3db58419...). Key files: manifest.json 393e6c2e2da02cb3..., test_preds.parquet 26474c84991676ab..., per_year.csv b6c43c5cea2b8b8e..., jackknife.csv 56606afb22573cc5..., score_pooled.csv dbc93658513b3910..., ladder/ladder_table.csv ab0359a7b46fa895.... Nothing in the run folder was changed.

## Part 621 addendum 5 - fire published rivals (Part B) DROPPED for submission (owner ruling AS, 2026-11-09)

The owner agreed to drop it when asked "Drop the fire published-rival comparison for submission too?" (ruling AS, which amends AJ1-AJ3; outline O7 option (c)). Nothing was run, deleted or edited in the Part B tool, its configs or registries, or D:/treeroute/human_products.
- The paper wording (AS1): "The fire published-rival comparison was not completed by submission; the CEMS seasonal FWI was not run (time)." The SEAS5-not-run disclosure stays. The 79 deciding verdicts and the five-method count are unchanged.
- State kept for a revision (AS2): the D2 download is complete (40 of 40 files, 1.73 GB, 2026-10-29; addendum 4, continued); Part B is unsigned; OD-1, 2, 3, 4.2, 5, 7-12 and 14 are unruled, and OD-13 is unconfirmed; F5-F10 are not run. The fetcher must not run again (rule B8). A revision run needs the OD rulings, the signature, the -WithFullSuite extras for the ONE full suite, and the new machine's junction at the old path.

## Part 628 (DRAFT 2026-11-12; RUN 2026-11-12 TO 2026-11-16 AT SCOPE (i), B1 INCLUDED, EVERY PIECE FINISHED, E5 INFORMATIONAL; RE-COMPUTED INDEPENDENTLY 2026-11-16; WRITTEN UP 2026-11-17, SUPPLEMENT S3.13 AND TABLE 9) - POST HOC SHAP (rulings AW1-AW5, AY1-AY3, AZ1, BA1-BA3, BB1-BB6, BC9): DESIGN v3 AFTER TWO ADVERSARIAL REVIEWS, ALL SMOKES PASS; NOTHING RUN AT SCALE (2026-11-12); RULINGS D8 AND D14 NEEDED FIRST (RULED 2026-11-13: AY3 AND AY2); THE NOWCAST COSTS 43-50 MACHINE HOURS (ESTIMATE OF 2026-11-12)

2026-11-12. Post hoc (ruling AK). No headline number changes. A design workflow (8 agents: 4 maps, the design, 2 adversarial reviews, the fix; 0 errors; 17:33-22:24 Paris) wrote everything under D:/treeroute/analysis/shap_v1: PROTOCOL.md v3, RUN_COMMANDS.md, scripts/ and smoke/ (0.61 GB, plumbing only). No sample is registered. Runs, registry, boards, exports, the engine and the paper are untouched. Reports: _archive_plan/_review_2026-11-12_shap/shap_01..08_*.json (scrubbed).

- **What can be explained.** Trees decide the kept prediction at 7 of the 14 reported problem-leads: coral 0 and 183, PM2.5 0 and 6, NDVI 0, fire 0, defo 0 and 1. At the other 7 the kept value is feature-free (coral 365 the donor median; the others identity trees-off, which equals the seasonal normal). There treeroute gets "no feature attribution" and the rivals are still explained.
- **Rebuild first.** treeroute's trees were not kept, so each lead's kept bank and the sampled units' routers are rebuilt with the run's own engine snapshot (gated by its code hash). They must reproduce the saved predictions (stop rule S-EXACT) before any SHAP value is computed.
- **Reviews: 27 findings** (method and statistics: 2 blockers, 5 majors, 8 minors; reproducibility: 1 blocker, 5 majors, 6 minors). Each was checked before it was fixed. All were confirmed except one nuance: merging duplicate columns changes nothing under LightGBM's per-tree feature draw but matters under per-node draws such as RF's, so the merge is applied to every model.
  - Blocker 1, moved package: PM2.5, NDVI and fire hash their static table with its full path, which moved with the 2026-11-08 reinstall (same content, size and time stamp). The v2 commands would have stopped at E3 after 1.9-17 h. Gate E3a now checks the inputs before the read (15 s to 3.5 min). Owner decision D14 chooses between (b) `--recorded-path-map`, accepted by gate E3m only when the file's content SHA-256, size and mtime equal the freeze locks' records (smoke: PASS for all three), and (a) a real copy at the recorded path.
  - Blocker 2, structural zeros: v2's linear and offset terms left 1-ulp noise, so constant players entered the active set and inflated rho, tau-b and W. Per-pair differences now give exact zeros (gate S-ZERO; coral now lists `normal` and four constant cyclone columns as structural zeros).
  - Blocker 3, section 8 against the code: the statistics text and the code were made to agree before the freeze. Added: the variable level (main text) and families; same-link and cross-link sets; RBO on full rankings; the directly computed mean rho; every main-row number bootstrapped; signs counted only when determined by their bootstrap interval; finite-replicate counts. "Noise ceiling" is renamed stability under region resampling, with no ceiling claim. The y-unit view is removed.
- **Smoke proofs** (each under 8 min, under smoke/ only):
  - unit checks 40 of 40;
  - coral, the real headline, leads 0 and 183 in one engine process (6.6 min, peak 1.3 GB). Every gate passes except E5 (informational); lead 183 has no saved identity twin (E5a), and its trees-off twin E5b passes. Lead 0: 2,228 of 2,312 rows bit-equal, the rest at most 1.06e-15 relative (8 ulps). Lead 183: 2,232 of 2,312, at most 9.3e-15 relative (58 ulps). The identity twin (lead 0) and the trees-off twin (lead 183): 2,312 of 2,312;
  - coral rivals (ridge, LightGBM, Tweedie, HGB L1, the rebuilt RF) bit-identical on 2,312 of 2,312 at both leads;
  - samples and input pre-checks on the four gridded exports; engine smoke worlds (PM2.5, fire GLS corrector, defo arcsine, the defo log_c corrector restricted to the sample) bit-identical, with 0 S-ZERO violations;
  - SHAP values were computed on 40-250 real coral rows in 2 regions as plumbing. No statistic was read as a result (protocol section 14).
- **The lead's checks after the workflow (2026-11-12):**
  - unit smoke re-run: 40 of 40 (4.8 s);
  - the final coral gate files re-read (the numbers above);
  - E3m PASS in the PM2.5, NDVI and fire pre-check logs;
  - a read-only scan of the project folder and D:/treeroute (272,323 entries) found nothing changed since 17:30 outside shap_v1, except shap_v1's creation and the new review folder;
  - no account or host name in any shap_v1 file outside the engine-written folders.
- **E5 (open).** At both coral leads the rebuilt bank's fingerprint (8,300 trees) differs from the run's, while every checked prediction matches: E5a or E5b, E8, and E10 (every tree on the first fitted row's pool and test row). The cause is not established. The answer-level gates decide, and S3.13 discloses it.
- **D8 (open).** The arcsine link itself changed in the last bit with the reinstall: today's numpy recomputes the stored fire arcsine normals bit for bit on only 3,590 of 3,597 unit-months, against all log, log_c and identity normals. Proposal: a true relative 1e-12 on arcsine arms only, licensed by the twin proofs. Without it, coral 0 and 183 and fire 0 stop at E8.
- **Costs** (N = 1,000; extrapolated from the run logs and the coral measurements; the pilot refines them):
  - scope (i) nowcast: 43-50 h;
  - scope (ii), plus one forecast lead: 55-66 h;
  - scope (iii), every lead: 59-71 h.
  - NDVI's fresh census is most of its 21-25 h. The census copy D9 (15-17 h less) needs D14 (a). The old-path junction of 2026-11-09 sits where (a)'s real folder would go.
  - The lead's earlier estimate (about 10-17 h for the nowcast, 2026-11-12) left out the census, derive and pool steps that every rebuild repeats. It was wrong.
- **RAM.** Free RAM needed after the census: fire about 8.4 GiB, NDVI 6.2, PM2.5 5.4, defo 2.9. Gate E0 stops a run that is short of RAM in its first minute.
- **Rivals covered (exact):**
  - ridge (all 5);
  - LightGBM (all 5);
  - LightGBM Tweedie (coral, fire, defo), explained in log mu and so always cross-link;
  - HGB L1 (coral);
  - RF, rebuilt through each board's rf_forest (all 5).
  - BARDL (NDVI) is exact linear, but its loader is not built. The Kraft LSTM (NDVI lead 0) is left out until D7.
- **Left out, with the reasons the paper prints:**
  - one-input maps: CRW DHW, CRW Outlook (D15), MERRA-2 in all three forms, VT0007 calibrated;
  - VT0007 as shipped and frozen, which are not functions of the rows' inputs;
  - the baselines, which have no input features;
  - the rivals that were never run: EAC4 and the fire published rivals.
- **Owner decisions open:**
  - D8 (before coral 0 and 183 and fire 0);
  - D14 (before PM2.5, NDVI and fire);
  - the scope;
  - D3, D5, D7, D10 and D15;
  - confirming E5 as informational;
  - section 8 v3 as written (frozen by the pilot's sample registration).
- **Not built:** the BARDL loader, the Kraft LSTM, D9. **Not run:** defo lead 1; rivals beyond coral; the RF memmap path; the last per-unit guard edit (its smoke stopped at E0 for lack of RAM).
- **Privacy:** engine-written checkpoint key.json files hold the account name (one so far). engine_runs/ and engine_tmp/ stay out of any archive or share (D13).
- **Pilot** (owner command, only after D8): `py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\run_shap.py --problem coral --scope i --arcsine-tolerance 1e-12`. It takes 17-22 min, with 1.5 GB peak RAM, 0.2 GB kept on disk and 2.5 GiB of temp space. It registers the coral sample and so freezes protocol sections 3 and 8.
- **Addendum (2026-11-17; the S3.13 write-up; pre-edit copy in paper/draft/_snapshots/20261117T1557Z_s3_13/). RUN, RE-COMPUTED AND WRITTEN UP: post hoc (ruling AK); no headline number changes.** The heading's status words are updated; the text above is the state of 2026-11-12. The record since then is D:/treeroute/analysis/shap_v1/PROTOCOL.md (sections 1, 2, 10 and 12, and the change log, section 14) and RUN_COMMANDS.md; the paper's numbers are the facts of PAPER_FACTS.md section 9 from A9 on.
  - **Rulings.** AY (2026-11-13, the owner chose scope (i) and the agent's advice on the other points): AY1 scope (i), the nowcast (lead 0) of each problem; AY2 decision D14 (b), the recorded path map, accepted by gate E3m; AY3 decision D8's alternative, a true relative tolerance of 1e-12 on arcsine arms only (the coral pilot had already run with it). AZ1 (2026-11-14, the owner's answer): the owner had not opened the burned-fraction comparison of 2026-11-13 21:18 before ridge was added. BA (2026-11-15, the owner agreed to open the results and to run B1): BA1 BARDL stays in the NDVI main set (decision D16's default, the frozen plan); BA2 the comparison results may be opened, for the independent re-computation and the write-up; BA3 treeroute's B1 sensitivity is run on fire, PM2.5 and NDVI and reported only as a labelled sensitivity in S3.13. BB (2026-11-16, the owner accepted all six recommendations): BB1-BB6, how S3.13 and the main-text table present the numbers. The other decisions keep their defaults, among them D7 (the Kraft LSTM left out) and D10 (N = 1,000 in all regions) (facts A9, A10, A14).
  - **Runs (scope (i); facts A9, A14).** The coral pilot 2026-11-12 23:49 to 2026-11-13 00:06; then fire, PM2.5, defo and NDVI, the last nowcast comparison (NDVI, five models) at 2026-11-15 19:11:39. Samples: 1,000 test rows per problem, registered from 2026-11-12 to 2026-11-14. Fire's first two runs stopped treeroute at gate E0 (RAM), and the third ran with --ignore-ram-warning. Outside coral, rival_shap.py stopped ridge at S-EXACT, as expected, and the ridge loader (ridge_shap.py, the board's own scoring) made those pieces; NDVI's BARDL piece came from the BARDL loader (bardl_shap.py); both loaders were built after the freeze, with no change to protocol sections 3 and 8 (fact A15), and each comparison was run again with them. The logged times are in PROTOCOL.md section 2.
  - **Gates (fact A12).** Every rebuild passed its gates but E5, which stays informational: the rebuilt bank's fingerprint differs from the run's on all five problems, while every checked tree answer and prediction matches. treeroute v1 bit-identical on PM2.5 (12,192 of 12,192 rows), NDVI (12,768 of 12,768) and forest loss (1,008 of 1,008); its arcsine arms bit-identical on 13,056 of 13,440 rows (burned fraction) and 2,228 of 2,312 (coral bleaching), the rest within D8, licensed by gate E5a. Every rival bit-identical on every checked row. S-ADD, S-EVAL, S-RESID and S-ZERO passed for all 25 models, with 0 S-ZERO violations. On coral bleaching E3a compares no data file before the labels are read, and E8 covers all 2,312 test survey visits.
  - **B1 (ruling BA3; facts A9, A21).** The command ran from 2026-11-15 23:06:16 to 2026-11-16 08:14:14: defo, fire, PM2.5 and NDVI, all finished. Defo's identity check (defo is annual, so its B1 background equals its main run's): the largest difference is 0 at both levels, with the same rows, players and variables, so the fire, PM2.5 and NDVI B1 numbers are reported.
  - **Independent re-computation (round 14, ruling BA2; 2026-11-16, 17:09 to about 19:20; facts A9, A23).** Implementers A and B, each with its own code written from the protocol and blind to compare_shap.py and the compare outputs, and a reconciliation: every number that the compare files hold and A and B also hold equals theirs within 1e-9, and the per-draw values of bootstrap_stats.parquet equal A's and B's on all 2,000 draws, except in three explained groups (a family with no variable; burned fraction's undefined Kendall's W and mean pairwise Spearman; the sign agreement's intervals). compare_shap.py writes neither burned fraction's treeroute top 3 nor its own-history share [CI] in the main-text row, does not evaluate the sign agreement on the draws and gives no feature-level family-share distance. By rulings BB1 and BB2, S3.13 takes the first two from verify_v1/A/results.json (A = B), as Table 9 does for burned fraction's two cells, and prints the third as the variable-level value. No SHAP script was edited or run, and the compare files are unchanged. The reconciliation's report is verify_v1/reconcile/report.md (fourth version).
  - **What the paper reports, and where (written 2026-11-17, labelled post hoc).** Supplement S3.13: the method and what is not claimed; Tables S3.18-S3.30, with the models explained and the rivals left out with reasons, the samples and active sets, the exactness checks and rebuild gates (E5 disclosed as informational), the main-text row with its components, each problem's comparison at both levels (with the arcsine models' rows with a forecast above 0) and treeroute's B1 sensitivity, kept apart; the re-computation and the notes of rulings BB1-BB6. Main-text Table 9, with a short paragraph in Section 5.4. The tables are copied from paper/supp_build/s3_13/reconcile/tables_agreed.md (version 5: two independent builders from the stored values with one rounding step, reconciled and checked; versions 2 to 5 changed no number). Main reading, variable level, nowcast: Kendall's W of the main set from 0.62 [0.61, 0.62] (NDVI) to 0.85 [0.85, 0.86] (PM2.5), undefined for burned fraction, whose main set is treeroute v1 alone (fact A16); treeroute v1's median top-20-union Spearman correlation with its same-link rivals -0.02 [-0.08, 0.07] (PM2.5), 0.07 [-0.01, 0.12] (NDVI), 0.20 [0.14, 0.29] (forest loss) and 0.48 [0.39, 0.55] (coral bleaching) (fact A17). SHAP shows what a model uses, not what causes the outcome, and agreement between rankings is not correctness. The read of coral's AW4_table.md on 2026-11-13 at about 15:31, before the re-computation, is disclosed (ruling BB6; fact A25); Supplements S1 (S1.7) and S4 record the provenance.
  - **Archive (plan only).** _archive_plan/ARCHIVE_MANIFEST_DRAFT.md (2.5, 4.1 and 4.2 I): the code, the records, the logs, the compare outputs and the re-computation in; coral's row-level files (decision D13), the gridded row-level SHAP values (a default, kept by ruling BC9), engine_runs/ (it holds the account name; D13), the rebuilt banks, routers and random forests, and the NumPy and compressed files out; smoke/ left out, smoke/bardl_fix/ with it by rule, not entered.
  - **Still open:** D7 (the Kraft LSTM stays out until ruled; ruled 2026-11-18, next bullet); the cause of E5 is not established.
  - **Ruled 2026-11-18 (ruling BC9; pre-edit copy in paper/draft/_snapshots/20261118T0416Z_b_items/):** the Kraft LSTM is left out (decision D7, ruled 2026-11-18), as final; the protocol's other section-12 settings, D1 to D6, D9 to D13 and D15, are confirmed as run, and D8, D14 and D16 were ruled before (AY3, AY2 and BA1), so no section-12 decision is open. The gridded row-level SHAP values stay out of the archive.
