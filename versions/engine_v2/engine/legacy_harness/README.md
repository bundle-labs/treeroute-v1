# Legacy harness (APP_PLAN.md 4.4)

The harness proves that code moved into the engine still computes what the shipped scripts computed. It sits **outside the product**. The engine never imports it (G-IMPORT, `tests/test_import.py`), and it is not a way to run old settings in the product. It may name problems; the engine may not.

The first piece is here: a pinned launcher and the **goldens**. A golden is a saved output of a shipped script that a later replay must match. The replays themselves come with the engine modules: PM2.5 in M2, defo in M3, fire in M4.

Fences:
- New harness outputs go only under `D:/treeroute/golden/`. The launcher refuses any other folder, and any folder that already holds files.
- Nothing is ever written under a protected root (`D:/treeroute/registry/protected_roots.txt`). The launcher snapshots those roots before and after each run and exits 5 if anything changed.
- `run_defo` is never run. It deletes and rebuilds caches.

## Files

| File | What it is |
|---|---|
| `launch_pinned.py` | Runs a shipped script, or its rooted copy, with every thread pool pinned before numpy loads: BLAS 1 thread, OpenMP 4. Writes `launcher.json` and `console.txt` next to the outputs. It generalises `engine/speedproof/run_shipped_blas1.py`. `--check-only` runs the pre-flight alone. |
| `adaptation_rooted.py` | A copy of the shipped `adaptation.py`. Its only change is line 139: `OUT_ROOT = os.environ.get("ADAPTATION_OUT_ROOT", "D:/treeroute/golden")`. The shipped line is `OUT_ROOT = "D:/adaptation"`, which is a protected root. |
| `rooted_copy.py` | `check` proves the copy differs from `adaptation.py` by exactly that one line, and that both sha256 values match the newest registry (read-only). `make` wrote the copy and refuses to overwrite it. The launcher's `--copy-of` uses the same check. |
| `goldens.json` | Registry **version 1**: every golden's path, size and sha256, with its provenance and the gates it serves. Written once by `goldens.py build`. |
| `goldens_v2.json` | Registry **version 2** (fix round 1). The PM2.5 and defo goldens are carried over unchanged. The fire block is regenerated: the RAM threshold is recorded as a choice, and the commands are new. The launcher record points to the fixed launcher and its new self-test. Written once by `goldens.py next`. |
| `goldens.py` | `build` wrote version 1. `next` writes the next version, and can fold a captured fire run into it. `verify` reads the **newest** version, re-hashes every registered file, and checks the fire run's record (read-only). |
| `selftest_target.py` | A few-second self-test target for the launcher. It reads no data. |
| `tests/test_harness_tools.py` | 62 unit tests for the helpers, including the fold path. Run `py -3.9 -m pytest legacy_harness/tests -q` from `engine/`. The engine's own `py -3.9 -m pytest` does not collect them. |

## The goldens

| Id | What | Where | Threads | Status |
|---|---|---|---|---|
| `pm25_u2_smoke` | Shipped `pm25_adaptation.py`, U2 smoke: 12 trees/donor, one-point grid (10, 0.0625), primal path. Adopted `treesoff`. | `D:/treeroute/speedproof/golden_smoke/` (8 files + console) | **not pinned**: numpy BLAS 16, scipy 4, OpenMP 4 | registered, not re-run |
| `pm25_wide_smoke_blas1` | Shipped `pm25_adaptation.py`, wide smoke: 400 trees/donor (3,200 trees), 35-point grid. Reaches the dual solve, NVERIFY and the contract check. Adopted `log_corrector`. | `D:/treeroute/speedproof/wide_golden_blas1/` (9 files incl. `launcher.json`, + console) | pinned: every BLAS 1, OpenMP 4 | registered, not re-run |
| `fire_smoke` | `adaptation.py` fire nowcast in its shipped configuration (`--problem=fire --calib=strict --smoke=1`), all five arms. | `D:/treeroute/golden/fire_smoke/` (first attempt) | pinned by `launch_pinned.py` | **PENDING**: the owner picks the RAM threshold, see below |
| `defo_link_corrector` | The cached `link_corrector` / `inner_link_corrector` arrays, one npz per test region (17), plus the 25 lead-0 pair banks and 25 placebo banks the replay needs. | `D:/adaptation/defo/*_c4000.npz`; backup copies in `D:/treeroute/registry/backup_20260928/defo/` | n/a (cached) | registered from shipped.json, re-hashed; backups identical |

Notes:
- **PM2.5 U2 smoke.** It was run straight from the shell, not through a launcher, so it is not captured under the pins. At that width the router solves are too small for OpenBLAS to use a second thread. Gate G10 shows it bit-identical to the copy run with every BLAS at 1 thread. It is also bit-identical to the shipped `D:/pm25_adapt/u2_smoke`.
- **PM2.5 wide smoke.** The shipped script as normally launched (`wide_golden`) differs from this golden by at most 3.55e-13 ug/m3, and every decision is the same (G8). All of that gap comes from the BLAS thread count.
- **Defo caches.** `add_linkcorr.py` added the `link_corrector` keys in place after `run_defo` wrote the caches (see `D:/adaptation/defo/_addarm.log`). So a defo replay must follow `add_linkcorr.py`'s fit (the ridge on G(y) with the corrector columns, then GINV), not `run_defo`'s arms.
  - The glob `*_c4000.npz` also matches `_rival_L0_c4000.npz`. That file is a rival-board cache with no `link_corrector` key. It is registered with that role.
  - Rows per region are in the registry: 16,000 test and 8,000 inner rows, except costa_rica (10,172 / 7,629) and tongass_alaska (15,752 / 10,589).
- **Fire shipped references.** These are not the golden. `D:/adaptation/fire_strict_smoke/` was run on 2026-09-21 with `--arms=base`, before the sentinel fix in `fire_architecture.py`, at BLAS 16/4. `D:/adaptation/fire_strict/_preds.npz` is the full shipped nowcast: `link_corrector` test MAE 0.003993 over 59,892 rows. The prefix match also picked up `fire_strict/_preds.npz.bak`, which holds the pre-sentinel-fix predictions (same sha256 as `D:/adaptation/fire/_preds.npz`).

## RAM threshold for the fire golden (the owner decides)

The fire golden was not captured on 2026-09-28. The launcher refused at 5.70 GB of available RAM because the agent had chosen `--min-avail-gb 8.5`. **8.5 GB is a caution choice, not a measured requirement.** The shipped logs point both ways:

| Log block | RAM before the pool build | RAM before the bank | Outcome |
|---|---|---|---|
| `D:/adaptation/fire_strict/_adaptation.log`, 00:27:51 (2026-09-22; full width, npd 300, all arms). **This run produced the registered reference `fire_strict/_preds.npz`.** | 5.7 GB | 5.1 GB | finished: link_corrector 0.003993, adopted |
| same log, 14:04:08 (npd 300, `--sweeponly`) | 6.2 GB | 3.8 GB | finished its routing |
| `D:/adaptation/fire_strict_smoke/_adaptation.log`, 22:47:10 (the shipped smoke, `--arms=base`) | 8.7 GB | 4.9 GB | finished |
| `D:/adaptation/fire_strict/_adaptation.log`, 02:51:23 (a **smoke**) | 7.2 GB | never logged | died: the next line is a new run at 03:13:34 |

- The shipped guards ask for 5.0 GB before the pool build and 3.0 GB before the bank (`guard(5.0)` / `guard(3.0)` in `run_fire`). The throttle `FA.wait_mem` then waits instead of dying: before the pool build while under 2.5 GB, and between regions while under 1.2 GB.
- The `adaptation.py` comment at the pool build records a fall from 7.2 to 1.2 GB on a smoke, "the level this machine has hung at twice".
- The logs cannot show whether a run paused, because `fire_architecture` prints its PAUSED/RESUMED lines to the console only. The 00:27 pool build took 18 minutes, inside the 11.5 to 20 minute range of the other blocks.
- The smoke builds the same 40-region pool as the full run (npd changes only the bank), so its pool build needs the same memory.

Options:
1. **Caution:** close the browser (it held about 5 GB) and run at `--min-avail-gb 8.5`.
2. **Shipped guard:** run at a lower value, for example `--min-avail-gb 5.0` (the shipped guard; 00:27 succeeded from 5.7 GB). The shipped in-script guards still apply.

At the fix-round check, 5.77 GB was available and no other python job was running.

## Registry versions (write-once series)

`goldens.json` is version 1, `goldens_v2.json` is version 2, and so on. Each file is written once and never changed. A new version names the version it supersedes and lists what changed. `goldens.py verify` and `rooted_copy.py check` always read the **newest** version (`--registry FILE` verifies an older one).

Where the fire golden's hashes live after a run is **the owner's decision**. Both options are built; neither happens by itself:
- **A. Fold into the registry.** After a good run, `py -3.9 goldens.py next --fire-run <run folder> --note "..."` writes the next version (v3) with `fire_smoke` set to CAPTURED and every output's sha256 in `files`. It refuses a run whose record fails any check. `verify` then re-hashes those files from the registry, like every other golden.
- **B. The run's `launcher.json` is the registry.** The launcher writes it once, with the size and sha256 of every output. `verify` re-hashes the outputs listed there. It reads the default folder `D:/treeroute/golden/fire_smoke`, or `--fire-run <folder>` after a retry.

## Commands

All commands run from this folder unless noted:

```
cd "C:\Users\<user>\Desktop\data set for reserch paper\engine\legacy_harness"
```

**Check the registry (read-only).** This re-hashes every golden file and reports the fire run:

```
py -3.9 goldens.py verify
py -3.9 goldens.py verify --deep      # also re-hashes the 50 defo bank files (about 3.7 GB)
```

**Check the rooted copy (read-only):**

```
py -3.9 rooted_copy.py check
```

**Capture the fire golden (about 25 minutes; the owner runs it).** Run the pre-flight alone first. It checks everything, runs nothing and writes nothing:

```
py -3.9 -u launch_pinned.py --check-only --script adaptation_rooted.py --copy-of ../../adaptation.py --out-dir D:/treeroute/golden/fire_smoke --env ADAPTATION_OUT_ROOT=D:/treeroute/golden/fire_smoke --redirect-prefix D:/fire/pool_features_ --redirect-prefix D:/fire/lead1_pool_ --redirect-prefix D:/fire/A_ --watch D:/fire --watch D:/joblib_tmp --min-avail-gb 8.5 -- --problem=fire --calib=strict --smoke=1
```

Then run the same line without `--check-only`, with the threshold you chose (8.5 or 5.0 are the two options above), and verify:

```
py -3.9 -u launch_pinned.py --script adaptation_rooted.py --copy-of ../../adaptation.py --out-dir D:/treeroute/golden/fire_smoke --env ADAPTATION_OUT_ROOT=D:/treeroute/golden/fire_smoke --redirect-prefix D:/fire/pool_features_ --redirect-prefix D:/fire/lead1_pool_ --redirect-prefix D:/fire/A_ --watch D:/fire --watch D:/joblib_tmp --min-avail-gb 8.5 -- --problem=fire --calib=strict --smoke=1
py -3.9 goldens.py verify
```

- **What it writes.** Everything goes under the `--out-dir` folder:
  - `fire_strict_smoke/_adaptation.log`, `_preds.npz` and `_verdicts.csv` (the golden);
  - `console.txt`;
  - `launcher.json`, which holds the size and sha256 of every output. It is written once and never overwritten.
- **Scratch files.** `fire_architecture.py` puts its pool and tree matrices in `D:/fire/pool_features_<pid>.f32` and `D:/fire/A_<tag>_<pid>.f16`. The launcher redirects those names to `D:/treeroute/golden/_scratch/`, so the shipped stale-file sweep looks only there.
- **D:/fire and D:/joblib_tmp.** Nothing is *expected* to be written there. This comes from a trace of `run_fire`: `adaptation.py` only `setdefault`s `JOBLIB_TEMP_FOLDER`, and the launcher sets it first. The `--watch D:/fire --watch D:/joblib_tmp` diff checks it and exits 5 on any change. No run has shown it yet.
- **Refusals.** The launcher refuses, exit 2 with nothing written, if:
  - another heavy python job is running;
  - the scratch folder or the output folder already holds files;
  - `ADAPTATION_OUT_ROOT` (any `--env` path) is not inside `--out-dir`;
  - a runtime variable other than the pins is set in the shell (a shell value of a pinned variable is overwritten by the pin and recorded in `env_before_pins`);
  - `adaptation_rooted.py` is not exactly the one-line OUT_ROOT copy of `adaptation.py`;
  - and, checked last, RAM is below `--min-avail-gb`.

**Retry after a failed fire attempt.** A failed attempt (for example the shipped `guard(5.0)` / `guard(3.0)` exit, or Ctrl+C) still leaves its folder and its `launcher.json` with a non-zero exit. Nothing is overwritten. For a retry:
1. **Use a new folder for BOTH `--out-dir` and `ADAPTATION_OUT_ROOT`**, for example `D:/treeroute/golden/fire_smoke_2` in both places. The launcher refuses an `--env` path outside `--out-dir`, so a retry can no longer write into the old folder.
2. **Clear the scratch leftovers by hand.** A failed run can leave a multi-GB pool file in `D:/treeroute/golden/_scratch/`, and the launcher refuses a scratch folder that holds files. Delete them yourself (the harness never deletes), or pass `--scratch D:/treeroute/golden/_scratch_2` (D: had 53 GB free).
3. **Verify the new folder:** `py -3.9 goldens.py verify --fire-run D:/treeroute/golden/fire_smoke_2`. Plain `verify` checks the default folder and lists every other fire attempt it finds.

**Launcher self-test (seconds).** The current launcher's record is `D:/treeroute/golden/_launcher_selftest_fix1/launcher.json`. The first launcher's record is in `D:/treeroute/golden/_launcher_selftest/`. A re-run needs two new folder names:

```
py -3.9 -u launch_pinned.py --script selftest_target.py --out-dir D:/treeroute/golden/_launcher_selftest_fix2 --scratch D:/treeroute/golden/_launcher_selftest_fix2_scratch --redirect-prefix D:/treeroute/_absent_selftest_source/tmp_ --watch D:/treeroute/_absent_selftest_source --watch D:/fire --env SELFTEST_OUT=D:/treeroute/golden/_launcher_selftest_fix2/target -- --source-prefix D:/treeroute/_absent_selftest_source/tmp_ --out D:/treeroute/golden/_launcher_selftest_fix2/target
```

**How the PM2.5 goldens were made (provenance only; do not re-run):**

```
cd "C:\Users\<user>\Desktop\data set for reserch paper"
py -3.9 -u pm25_adaptation.py --smoke --links identity,log,logc --levels 10 --ratios 0.0625 --run-dir D:/treeroute/speedproof/golden_smoke --expect-from D:/pm25_adapt/smoke/inner_candidates.csv
cd engine\speedproof
py -3.9 -u run_shipped_blas1.py --smoke --npd 400 --links identity,log,logc --run-dir D:/treeroute/speedproof/wide_golden_blas1
```

## What the launcher pins and records

- **Before numpy loads.** It sets OPENBLAS, MKL, BLIS and VECLIB to 1 thread, and OMP and NUMEXPR to 4. Four is the shipped `cap_threads(4)` (`coral_safe.py:29-34`) and plan C14's forest threads.
- **Then.** It imports numpy and `scipy.linalg`, so both OpenBLAS copies load at 1 thread, and holds threadpoolctl BLAS = 1 for the whole process.
- **Plan A8 (an owner question).** A8/C14 run only router units at BLAS 1, and "any BLAS outside router units" at 4. Holding BLAS 1 for the whole process follows the harness task's wording. It matches A8 for fire, which routes per cell (router units), but not for a region solve: defo's region router runs at BLAS 4 under A8. A defo region-solve replay under this launcher would therefore not match the engine's BLAS-4 solve bit for bit. Either it runs the region solve at BLAS 4, or the gate accepts a rounding-level tolerance.
- **sklearn is not imported early.** The shipped code imports it itself, after its own `cap_threads(4)`, as it does when launched normally.
- **`launcher.json` records:**
  - the thread pools as loaded, after the pin and at the end;
  - the script's sha256 before and after, and for a rooted copy the `rooted_copy.check` result (source sha256, the changed line, the diff);
  - versions, the threshold used, and the environment the script left behind;
  - every redirect and any scratch leftovers;
  - the other python processes seen at start;
  - the three leak diffs (protected roots, redirect-source names, watched folders);
  - every output with its sha256.
- **Exit codes:**
  - the script's own code;
  - 2 = refused before starting;
  - 3 = a BLAS pool not at 1 thread, or an OpenMP pool not at 4, at the end (INVALID);
  - 4 = the script or its source changed during the run;
  - 5 = a leak diff is not empty.
- **What the leak diffs cover.** Each compares size and mtime before and after the run, not content:
  - every file under the protected roots;
  - files under a redirect-source folder whose **names start with a `--redirect-prefix`**;
  - every file and every folder mtime under each `--watch` folder. A folder's mtime catches a file created and deleted during the run.
  
  A write anywhere else on D: (outside the protected roots and the watched folders, and not prefix-named) is neither redirected nor detected.
- **Hooks.** The redirect hooks only numpy's memmap `open`, `os.remove`/`os.unlink` and `glob.glob`. A prefix-named scratch file written another way is not redirected. It is caught (exit 5) by the redirect-source diff if it is still there after the run, and by the folder mtime if its folder is watched.
- **Leftovers.** The launcher never deletes anything. Scratch leftovers are listed in `launcher.json`, and the next launch refuses until they are cleared by hand or a new `--scratch` folder is given.

## Gates these goldens serve (plan 4.4, 4.5, 8)

| Gate | Golden | When |
|---|---|---|
| PM2.5 replay equals the golden smoke captured under the pins (target 1e-9, hard stop 1e-4) | `pm25_wide_smoke_blas1` (pinned, dual path); `pm25_u2_smoke` for the U2 / primal configuration | M2; checkpoint Tue 6 Oct |
| Tier-2 re-score of Part 556/558 (4.100192, `D:/pm25_adapt/full/verdict.json`) | not a golden here: that file is in shipped.json under `D:/pm25_adapt` | M2 |
| The engine's region solver on defo's shipped banks equals the cached link_corrector arrays, with matching row counts | `defo_link_corrector` (arrays + 50 banks) | M3; kill switch Tue 13 Oct |
| Fire replay equals its golden (shipped test MAE 0.003993) | `fire_smoke` (pinned byte-level smoke golden, once captured); `fire_strict/_preds.npz` as the full-width reference | M4 |
| Speedups 1-3 byte-identical (their own gates, 4.5) | `pm25_u2_smoke` (G10), `pm25_wide_smoke_blas1` (G7) | passed on the speed-proof copy; re-run in the engine in M4 |
| Coral replay equals the shipped `_preds.npz` (optional track) | not captured | M6b / M8 |
