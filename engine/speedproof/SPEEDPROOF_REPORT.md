# Speed proof: speedups 2 and 3 on a copy of the PM2.5 script (APP_PLAN.md 4.5)

Date: 2026-09-28. Round 2, revised after review. Everything below was measured on this machine today, at smoke scale, from saved outputs.
The shipped `pm25_adaptation.py` was not edited (sha256 `cf2f2357...1f11057` before and after both rounds).

## In short

- **Both speedups keep the results exactly, and every gate the plan names has now been run.** The table is in section 3.
  - The final file (sha256 `a5bf8a57...4333e`, recorded in each run folder) gives bit-identical output at 1 and 8 workers, with the scan-once flag off and on. That now includes the **float64** inner surfaces.
  - **Speedup 2 plan gate: passed.** 8 tree threads, with sklearn's per-tree scan and the shipped router, give bytes identical to the unpatched script (G5).
  - **Speedup 3 plan gate: passed.** The unpatched script run with every BLAS library pinned to 1 thread is byte-identical to the copy's router on 8 workers at BLAS 1 (G7). So the whole gap to today's script comes from the BLAS thread count, and nothing else.
- **Worker-count invariance holds as the plan says. The gap and the speed do not.**
  - The gap to today's script is **3.6e-13 ug/m3**. The plan says about 2e-15, so it is about 180x larger. It is still about 2,800x inside the 1e-9 replay target, and every decision is unchanged.
  - The router speedup is **1.7-1.8x** at smoke width. The plan counts 2-3x.
- **ATTENTION: speedup 2 as planned (threads only) gives about 1.1x.** Almost all of the speed comes from moving one sklearn input check. So it is "threads + scan once per block". Owner decision, open item 1.
  - `fire_architecture.py` calls sklearnex `patch_sklearn()`. That swaps sklearn's finiteness check for daal4py's, which holds Python's global lock and re-scans the whole row block for every tree.
  - Split of tree-answer time on 8 threads (new this round): prediction 164 s, disk copy 17 s. With the scan once per block: prediction 9.4 s, disk copy 16 s.
  - Tree answers in total: threads alone 1.07-1.14x; scan once per block alone 4.8-5.2x; both **8.1x**. Threads add 1.6-1.7x on top of the scan. At this size the disk copy is now 63% of what remains.
- **ATTENTION: today's router does not run "BLAS on 4 threads", as the plan says.** It runs numpy's BLAS on **16** threads and scipy's on **4**. The reason: numpy is imported before `cap_threads(4)` sets the thread variables, and OpenBLAS reads them only when it loads.
- **Correction to round 1: the inner surfaces were not "unchanged".** `inner_preds.npz` is float32 by the shipped design, so it cannot show a 1e-13 difference. The float64 scores computed from those surfaces do move: in `inner_candidates.csv`, 96 of 213 rows differ on MAE, 111 on R2 and 107 on pattern-R2, by at most 1.8e-15. Both passes move; only the test pass stores its rows in float64.

## 0. What this round fixed (review findings)

| Finding | Fix | Where |
|---|---|---|
| Runs credited to "the final file" were made by earlier versions of it | Re-ran the saved file at wide flags, 8 workers, scan-once off and on (G1, G2), plus 1 worker (G3) and the U2 flags (G9, G10). The copy now writes its own sha256 into `verdict.json["speedproof"]` and the pre-flight log line. Section 2 lists the code version of every run. | `pm25_adaptation_fast.py` (g) |
| "Inner surfaces move by exactly 0" was a float32 artefact | The copy also saves the float64 inner surfaces (plus the contract check's single-penalty route) to `speedproof_inner_f64.npz`. `inner_preds.npz` is unchanged. compare.py compares that file and counts the differing rows in every CSV. The report is corrected. | (g); `compare.py` |
| The plan's speedup-3 gate was never run | New `run_shipped_blas1.py` runs the unpatched file with both OpenBLAS copies pinned to 1 thread for the process lifetime. G7: identical. G8: the shipped script as launched vs at BLAS 1 reproduces the whole 3.6e-13 gap. | `run_shipped_blas1.py` |
| "It should scale better at full width" was untested and may point the wrong way | Removed. Section 5 explains the HDD risk and proposes a serial prefetch. | this report |
| Speedup 2 alone was never compared with the shipped script | Ran `--tree-workers 8 --router-workers 1 --router-pin 0 --finite-once 0`: identical to the shipped script (G5). Tree-answer seconds are now split into row-matrix build, prediction and memmap copy + flush. | (g) |
| (e) relies on private sklearn / daal4py internals; the probe's pool escaped the orphan check | The probe now checks inf and NaN injection (G-a to G-c) and prints the library versions. Its pool is named `pool_probe_*.f32`, so the copy's orphan check sees it. The probe also refuses to start beside a run. Version pins are in open item 1. | `probe_finite_scan.py` |
| Docstring said "FOUR" changes; finding 4 gave the wrong reason | "SIX changes (a)-(f) and the copy-only records (g)". Finding 4 is reworded. | both |
| Not logged as a Part | A draft Part is in section 9, for the owner or orchestrator to paste. EXPERIMENT_SUMMARY.md is outside this task's scope. | section 9 |

## 1. What the copy changes

File: `engine/speedproof/pm25_adaptation_fast.py`, final sha256 `a5bf8a57d62e1eb431ee4d11f437ac411800578c2a35ff3782636c6378e4333e`. None of the changes touches a formula, a row, a seed or an order of operations.

| | Change | Default |
|---|---|---|
| (a) speedup 2 | `columns()`: each row block's trees are split into contiguous column ranges, one per thread. Each thread runs exactly the shipped per-tree lines into the same block buffer. The block goes to disk as one slab, as before. | on, 8 workers |
| (b) speedup 3 | `route_percell` / `route_sweep`: the cell list, the fallback rule and the NVERIFY cells are fixed serially, in the shipped order. Each cell's shipped body runs in a worker, and results are written back in cell order. BLAS is pinned to 1 thread (threadpoolctl) for the whole solve at any worker count. | on, 8 workers |
| (c) | `--workers N` sets both counts; `--tree-workers` / `--router-workers` override one. `--workers 1` = both loops serial in the main thread. | 8 |
| (d) | The project folder goes on `sys.path`. Temp matrices and the pool go to `D:/treeroute/speedproof/tmp`, and the pre-flight checks both that folder and `D:/pm25`. | on |
| (e) | `--finite-once 1`: the finiteness scan runs once per block in the main thread. It is the same patched function `predict()` calls, with the same `allow_nan`, so bad input still stops the run. The trees then predict under sklearn's thread-local `assume_finite`. | **off** |
| (f) test only | `--router-pin 0` (needs `--router-workers 1`): the router runs the shipped serial loop in the shipped BLAS state. | off |
| (g) records, new this round | The copy's own sha256 goes into `verdict.json["speedproof"]` and the pre-flight line. Float64 inner surfaces go to `speedproof_inner_f64.npz`, beside the shipped outputs. Tree-answer seconds are split into row-matrix build (Vm), prediction and memmap copy + flush. | on |

`config` in verdict.json is left as shipped; the copy's settings live in the separate `speedproof` block, which compare.py ignores.

## 2. Runs, and the code version each used (all under `D:/treeroute/speedproof/`, one at a time)

U2 smoke flags: `--smoke --links identity,log,logc --levels 10 --ratios 0.0625 --expect-from D:/pm25_adapt/smoke/inner_candidates.csv`.
Wide smoke flags: `--smoke --npd 400 --links identity,log,logc`. That is 3,200 trees and the default 35-point grid, so the dual solve, NVERIFY and the contract check all run.

Code versions:
- **S** = shipped `pm25_adaptation.py`, sha `cf2f2357...`.
- **V1, V2** = earlier versions of the copy. They were overwritten, and their sha256 was never recorded. V1 existed before (e)/(f); V2 had (e).
- **V3** = sha `6ef195da...`, written whole at 13:10:34.
- **V4** = sha `a5bf8a57...`, this round. V4 differs from V3 only by (g) and docstrings, and each V4 folder records its sha.

| Folder | Time | Code | Workers | Extra flags |
|---|---|---|---|---|
| golden_smoke | 11:55 | S | - | U2 |
| fast_w1 / fast_w8 | 11:59 / 12:03 | V1 | 1 / 8 | U2 |
| wide_golden | 12:08 | S | - | wide |
| wide_w1 / wide_w8 | 12:17 / 12:29 | V1 | 1 / 8 | wide |
| wide_fo_w8 / wide_fo_w1 / wide_fo_w3 | 12:50-13:05 | V2 | 8 / 1 / 3 | wide + `--finite-once 1` |
| final_u2_w8 | 13:05 | V2 (not the final file, as round 1 said) | 8 | U2 |
| wide_trees8_unpinned | 13:10 | V3 | trees 8, router 1 | wide + `--finite-once 1 --router-pin 0` |
| **wide_final_fo_w8** | 13:40 | V4 | 8 | wide + `--finite-once 1` |
| **wide_final_w8** | 13:45 | V4 | 8 | wide (default path) |
| **wide_final_fo_w1** | 13:52 | V4 | 1 | wide + `--finite-once 1` |
| **wide_final_trees8_fo0** | 13:57 | V4 | trees 8, router 1 | wide + `--router-pin 0 --finite-once 0` |
| **wide_golden_blas1** | 14:05 | S via `run_shipped_blas1.py` | - | wide; every BLAS at 1 thread |
| **final2_u2_w8** | 14:13 | V4 | 8 | U2 (default path) |

Bold = this round (the list and the status per run are in `fix_round_status.txt`). Every run exited 0. After each run, `tmp/` and `D:/pm25` were empty.

**The launcher run (wide_golden_blas1).** It executes the shipped file itself with runpy.
- **BLAS pin.** numpy and `scipy.linalg` are imported first, so both OpenBLAS copies are loaded (at 16 and 16 threads, as loaded). Then threadpoolctl pins both to 1. `launcher.json` records the BLAS state at the end: 1 and 1, with OpenMP at the shipped 4. sklearn is not imported early, so OpenMP keeps its shipped setting.
- **Temp files.** The shipped temp paths (`D:/pm25/...`) are redirected, by file name only, to `tmp/`. Six redirects are recorded (the pool and five matrices). Nothing was written to `D:/pm25`.
- **Check.** The shipped file's sha256 is identical before and after the run.

## 3. Results: identity (`compare.py --gates`, printout in `compare_gates_final.txt` / `.json`)

| Gate | A | B | Expected | Result |
|---|---|---|---|---|
| G1 final file, default path == copy serial reference | wide_w1 (V1) | wide_final_w8 (V4) | IDENTICAL | **PASS** |
| G2 final file + scan once, 8 workers == serial reference | wide_w1 | wide_final_fo_w8 | IDENTICAL | **PASS** |
| G3 1 vs 8 workers, float64 inner surfaces included | wide_final_fo_w1 | wide_final_fo_w8 | IDENTICAL | **PASS** |
| G4 scan-once off vs on, float64 inner surfaces included | wide_final_w8 | wide_final_fo_w8 | IDENTICAL | **PASS** |
| G5 **speedup 2 plan gate**: threads only, shipped router == shipped script | wide_golden (S) | wide_final_trees8_fo0 | IDENTICAL | **PASS** |
| G6 threads + scan once, shipped router == shipped script | wide_golden | wide_trees8_unpinned (V3) | IDENTICAL | **PASS** |
| G7 **speedup 3 plan gate**: shipped at BLAS 1 == copy, 8 router workers at BLAS 1 | wide_golden_blas1 (S) | wide_final_w8 | IDENTICAL | **PASS** |
| G8 the gap is the BLAS thread count: shipped as launched vs shipped at BLAS 1 | wide_golden | wide_golden_blas1 | gap, decisions equal | 3.55e-13; **decisions equal** |
| G9 final file at U2 flags (primal path, Part 556 gate) == earlier copy | fast_w1 (V1) | final2_u2_w8 | IDENTICAL | **PASS** |
| G10 final file at U2 flags == shipped script | golden_smoke (S) | final2_u2_w8 | IDENTICAL | **PASS** |

IDENTICAL means bit for bit on:
- predictions.parquet (every column);
- every array in inner_preds.npz;
- the sha256 of the three CSVs;
- every non-clock verdict.json leaf;
- `speedproof_inner_f64.npz`, where both folders have it.

In final2_u2_w8, the Part 556 regression gate passed at 8.88e-16. Round 1 also showed that golden_smoke reproduces the shipped `D:/pm25_adapt/u2_smoke` bit for bit.

**The gap (G8, and the same numbers for wide_golden vs wide_w1), max |difference| in ug/m3:**

| Arm | Test pass (float64 rows) | Inner surface in inner_preds.npz (float32 rows) |
|---|---|---|
| base / base_inherited / corrector / placebo | 5.7e-14 / 8.5e-14 / 7.1e-14 / 7.1e-14 | 0 / - / 0 / - |
| log / log_corrector / log_placebo | 3.4e-13 / 2.6e-13 / 2.7e-13 | 0 / 0 / - |
| logc / logc_corrector / logc_placebo | 3.6e-13 / 2.7e-13 / 2.1e-13 | 0 / 0 / - |
| treesoff / log_treesoff / logc_treesoff | 0 / 0 / 0 | 0 / 0 / 0 |

- **The "0" in the inner column is a storage artefact.** The shipped script saves the inner surfaces as float32 (`SURF[name] = P.astype(np.float32)`). A float32 value near 10-100 ug/m3 has a step of about 1e-6, so a 1e-13 move rounds away.
- **The float64 inner surfaces did move.** The scores computed from them in `inner_candidates.csv` differ in 96 (MAE), 111 (R2) and 107 (pattern-R2) of 213 rows, by at most 1.8e-15.
- Other files: per_region.csv at most 1.8e-15, per_year.csv 1.3e-15, verdict.json numbers 1.9e-15.
- **So the gap is in both passes.** It looks test-only because only the test pass stores rows in float64. The row-level float64 size of the inner gap is not measured, because the shipped script does not save float64 inner rows.
- **Float64 inner identity across worker counts** is now shown at row level (G3, G4). Before this round it rested on the CSV aggregates only.

Identical in every run, the shipped one included:
- adopted `log_corrector` at (mlt 3, rho 1);
- 6 of 6 arms eligible;
- contrasts HELPS / CANNOT TELL / CANNOT TELL / HURTS / HURTS / CANNOT TELL;
- every MAE to 6 decimals.

## 4. Results: speed (wide smoke, seconds, from run.log)

Tree answers (5 matrices, 3,200 trees, 24,480-30,240 rows each):

| Run | Code | Tree threads | Scan | Total | Vm build | Predict | Memmap copy + flush |
|---|---|---|---|---|---|---|---|
| wide_golden | S | 1 | per tree | ~210 | - | - | - |
| wide_w1 | V1 | 1 | per tree | 207.2 | - | - | - |
| wide_w8 | V1 | 8 | per tree | 192.9 | - | - | - |
| wide_final_w8 | V4 | 8 | per tree | 181.1 | 0.1 | 164.3 | 16.6 |
| wide_final_trees8_fo0 | V4 | 8 | per tree | 187.8 | 0.1 | 168.5 | 19.1 |
| wide_fo_w1 / wide_final_fo_w1 | V2 / V4 | 1 | once per block | 40.2 / 43.5 | 0.1 | 24.1 | 18.9 |
| wide_fo_w3 | V2 | 3 | once per block | 27.7 | - | - | - |
| wide_fo_w8 / wide_final_fo_w8 | V2 / V4 | 8 | once per block | 25.6 / 25.8 | 0.1 | 9.4 | 16.3 |

Router solves (all arms) and whole run:

| | shipped (S, BLAS 16/4) | S at BLAS 1 | copy, 1 worker, BLAS 1 | copy, 8 workers, BLAS 1 |
|---|---|---|---|---|
| router solves | 61.1-61.3 (timed in the copy with `--router-pin 0`) | not logged | 50.3-54.3 | 33.7-35.8 |
| routers + scoring (derived) | 62-65 | 54 | 52-55 | 34-36 |

Wall time, pre-flight to saved:
- golden: 501 s;
- wide_final_fo_w8: 273 s;
- without the pool (66-68 s in both): 435 s to 205 s (2.1x).

The bank fit (about 145-160 s) is now the largest phase at smoke. Pool times ranged 66-281 s between identical runs (page cache), so they are excluded from every speed claim.

In plain words:
- **Tree answers: speedup 2 = threads + scan once per block.**
  - Threads alone: 1.07-1.14x.
  - Scan once per block alone, on one thread: 4.8-5.2x. The prediction part goes from about 190 s (207 s total minus about 17 s of disk copy; not split in that run) to 24 s.
  - Both: **8.1x** (207 s to 25.7 s).
  - Threads on top of the scan: 1.6-1.7x overall. On the prediction itself it is 2.6x (24.1 s to 9.4 s).
  - **The disk copy is now the floor at smoke.** Copying each block into the memmap and flushing it takes 16-19 s whatever the thread count. That is 63% of the fastest run's tree-answer time. Round 1 guessed that the remainder was disk writes; it is now measured.
- **Router.** 8 workers at BLAS 1 take 34-36 s, against 61 s for the shipped router: **1.7-1.8x**. That is below the plan's counted 2-3x. One worker at BLAS 1 (50-54 s) is already faster than the shipped 16/4-thread BLAS: the shipped router's threads mostly get in each other's way.
- **U2 smoke** (final2_u2_w8): tree answers 5.7 s (prediction 4.9, disk 0.7), router 0.9 s, wall 80 s. That size says nothing about speed.

## 5. Findings

1. **The sklearnex finiteness scan (root cause of "speedup 2 = 1.1x").**
   - `probe_finite_scan.py`, re-run this round, uses real smoke rows, a 400-tree bank with the shipped recipe, and one 12,288-row block.
   - Shipped per-tree call: 1.24 s on 1 thread, 1.08 s on 8. Scan once per block: 0.18 s on 1 thread, 0.06 s on 8 (19.9x). All byte-identical.
   - The profile shows `daal4py.sklearn.utils.validation._assert_all_finite` at 0.24 s of 100 predicts.
   - The plan's synthetic bench (plain sklearn, random rows) scaled 5-6.6x because it never had the patch.
   - **Guard checks (new).** An injected inf makes both the shipped per-tree predict and the once-per-block scan raise. A predict under `assume_finite` alone does not raise, so the scan must never be skipped. An injected NaN passes both paths the same way: the trees support missing values, and the rows are `fillna(0)` before they reach the trees anyway. Probe verdict: GUARD PASS.
   - Versions: scikit-learn 1.6.1, scikit-learn-intelex 2025.10.0 (its module reports the placeholder `__version__` 2199.9.9), numpy 2.0.2, scipy 1.13.1, threadpoolctl 3.6.0.
2. **The shipped script's rows are Fortran-ordered.** pandas `.values`, then `astype`, then `np.vstack` keeps column order, so each row block handed to `predict()` is non-contiguous. That makes daal4py's scan about 3.7x dearer than on synthetic rows. It is harmless for results.
3. **BLAS state of the shipped PM2.5 script** (threadpoolctl, the M0 snapshot item): numpy OpenBLAS 16 threads, scipy OpenBLAS 4, OpenMP 4.
   - An environment variable cannot pin the shipped script: a shell `OPENBLAS_NUM_THREADS=1` would pin numpy but leave scipy at 4, because `cap_threads(4)` overwrites the variable before scipy loads.
   - The launcher pins both after loading them.
4. **What each smoke width can test.**
   - The NVERIFY check runs only on the dual path, which needs more design columns than fit rows: trees per donor x 8 + 4 > 204 at smoke, so at least 26 trees per donor.
   - The contract check runs only when the (1.0, 0.5) grid point is in the grid.
   - The U2 smoke (12 trees per donor, one-point grid at (10, 0.0625)) runs neither. Its router solves are too small for OpenBLAS to use more than one thread, so it cannot show a BLAS effect.
   - At full U2 width (also a one-point grid, but on the dual path), NVERIFY does run; only the contract check does not.
5. **The tree tables themselves are not compared.** They are temp files the script deletes. Identity rests on every saved array downstream of them being bit-identical, including every float64 inner surface (V4 runs) and every test prediction.
6. **Full width may be I/O-bound on the router side; not measured.**
   - At smoke the tree matrices (313-387 MB) sit in the page cache, so no router timing here includes disk reads.
   - At full width one matrix is 17.5-21.5 GB, more than the 15.8 GB of RAM. Eight workers would then read different cells' row blocks from the HDD memmap at the same time.
   - The shipped docstring measured scattered reads at 10.9 s against 1.75 s contiguous. So the full-width router could scale worse than at smoke, not better.
   - **Proposed engine design:** read each cell's A rows serially, in cell order, in the main thread (a small prefetch queue), and give only the solve to the workers. The bytes stay identical and the HDD access stays sequential.

## 6. Open items for the owner

1. **ATTENTION: speedup 2 in the engine.** Choose how the tree-answer writer avoids the per-tree scan:
   - (a) scan once per block + thread-local `assume_finite`: measured end to end here, byte-identical (G2-G4, G6); 8.1x at smoke;
   - (b) `predict(check_input=False)` with the engine's own once-per-block check: byte-identical in the probe, not run end to end;
   - (c) keep threads only: about 1.1x, so the table estimate in 4.5 does not hold.

   Recommended: (a). It depends on private internals: sklearn's `_assert_all_finite` and `_support_missing_values`, sklearn 1.6.1's thread-local config, and daal4py honouring `assume_finite`.
   - So pin scikit-learn 1.6.1 and scikit-learn-intelex 2025.10.0 in the lock file. Pin sklearnex by distribution metadata or wheel hash, since its module reports a placeholder version.
   - Carry the probe's guard checks (byte identity on a sample block; an inf must raise in the once-per-block scan) as an engine guard test. That test is a validator, so its signature needs your approval first.
2. **Plan text corrections (APP_PLAN 4.5, A8, the 8.0 schedule row for Fri 2 Oct).**
   - "Today's router uses BLAS 4": it uses numpy 16 / scipy 4.
   - The "about 2e-15" / "about 1e-15" gap: 3.6e-13 at 3,200 trees on the test pass (float64), with decisions unchanged. Full width is not measured.
   - Router speedup: 1.7-1.8x measured at smoke width; full width not measured and possibly I/O-bound (finding 6).
   - Speedup 2: threads alone about 1.1x while sklearnex is patched; the 8.1x needs the scan moved (item 1).
   - The speedup-3 gate as written in 4.5 is now shown runnable (`run_shipped_blas1.py`) and passes at smoke.
3. **Smoke gates for speedup 3 must use a width that reaches the dual solve** (finding 4). The wide flags above do.
4. **Full-scale measurement (your run; the U2 full nowcast took 7.3 h; needs about 22 GB free on D:).**

   ```
   cd "C:\Users\<user>\Desktop\data set for reserch paper\engine\speedproof"
   py -3.9 -u pm25_adaptation_fast.py --npd 100 --links identity,log,logc --levels 10 --ratios 0.0625 --run-dir D:/treeroute/speedproof/u2_full_fo_w8 --expect-from D:/pm25_adapt/full/inner_candidates.csv --workers 8 --finite-once 1
   py -3.9 compare.py --pair D:/pm25_adapt/u2 D:/treeroute/speedproof/u2_full_fo_w8
   ```

   - It logs, per matrix, the row-matrix build, prediction and disk copy seconds, and the router seconds per arm at 8 workers with the matrices out of the page cache. Compare those with the shipped U2 log's phases.
   - A 1-worker router number at full width needs a second full run (`--router-workers 1`), or the engine's M4 timing probe. That probe should log router seconds at 1 and 8 workers uncached, as the review asked.
   - The regression gate inside the run stops it if any inner MAE moves more than 1e-4.
5. **Log this as a Part in EXPERIMENT_SUMMARY.md.** That file is outside this task's write scope; section 9 has a draft.
6. **Temp files.** In round 1 the two golden runs of the shipped script wrote and deleted their pool and matrices in `D:/pm25`, because the path is hard-coded there. This round the launcher redirected them to `tmp/`. `D:/pm25` is not a protected root and is empty. No file under any protected root has changed since 13:20 today (checked with `find -newermt`).

## 7. Known limits

- **Scale.** Smoke only: 3 test regions, 8 donors, at most 3,200 trees. The full width (10,700 columns, 2,000 cells, 17-22 GB tables that do not fit in the page cache) is not measured, and the router may behave differently there (finding 6).
- **Timing noise.** One run per setting, on one machine, so timings carry perhaps +-10% noise. Where two versions ran the same setting, they agree within 1-8% (tree answers 25.6 / 25.8 s; 40.2 / 43.5 s).
- **Worker counts tested:** 1, 3 and 8 (3 only with V2), not 16.
- **File versions.** V1 and V2 were never hashed. Their runs are consistent with V4, because every V1/V2 output the gates touch is bit-identical to a V4 output (G1, G2, G9). Only V4 runs record their code.
- **Float64 inner rows vs the shipped script.** That comparison is not possible, because the shipped script saves float32. The inner-side gap to today's script is known only through float64 aggregates (at most 1.8e-15).
- **BLAS state depends on the shell.** The gap applies to the shipped BLAS state as launched from a shell with no thread variables. A shell that sets `OPENBLAS_NUM_THREADS` changes numpy's BLAS threads, and with them the shipped router's rounding.
- **What the launcher changes.** It pins BLAS for the whole process, scoring included. G7 passing shows that scoring does not depend on BLAS threads at this size. The launcher also redirects temp file names; bytes are unaffected.

## 8. Re-running the comparison

```
cd "C:\Users\<user>\Desktop\data set for reserch paper\engine\speedproof"
bash run_fix_round.sh                 # the six runs of this round, one at a time; skips finished ones
py -3.9 compare.py --gates --json D:/treeroute/speedproof/compare_gates_final.json
py -3.9 compare.py --pair D:/treeroute/speedproof/wide_golden D:/treeroute/speedproof/wide_w1
py -3.9 -u probe_finite_scan.py
```

compare.py reads only saved outputs. It writes nothing unless `--json` is given. Round-1 printouts (`compare_u2smoke_final.txt`, `compare_wide.txt`, `compare_wide_trees8_unpinned.txt`) are kept as they were.

## 9. Draft Part for EXPERIMENT_SUMMARY.md (for the owner or orchestrator to paste)

> **Part N: Speed proof for APP_PLAN 4.5 speedups 2 and 3 on a copy of pm25_adaptation.py (2026-09-28)**
>
> **What.** A patched copy (`engine/speedproof/pm25_adaptation_fast.py`, final sha256 a5bf8a57...) runs:
> - the tree answers on 8 threads (speedup 2);
> - the per-cell routers on 8 workers with BLAS pinned to 1 thread (speedup 3);
> - optionally, sklearn's input finiteness scan once per row block instead of once per tree per block.
>
> It was run at smoke size against the unpatched script. The wide smoke is `--smoke --npd 400 --links identity,log,logc`: 3,200 trees, the dual solve and the 35-point grid.
>
> **Identity.** All ten gates pass (`compare_gates_final.txt`):
> - 1 vs 8 workers and scan-once off vs on are bit-identical, float64 inner surfaces included.
> - Speedup 2 with threads only is bit-identical to the shipped script.
> - The plan's speedup-3 gate passes: the shipped script run with every BLAS at 1 thread (`run_shipped_blas1.py`) is bit-identical to the copy on 8 router workers.
> - The shipped script as launched differs by at most 3.6e-13 ug/m3 on test predictions (about 180x the plan's 2e-15), and all of it is the BLAS thread count. Every decision is unchanged.
> - Round 1 said the inner surfaces were unchanged. That was a float32-storage artefact: the float64 inner scores differ by at most 1.8e-15.
> - Round 1 also credited some runs to a file version that did not make them. The copy now records its sha256 in every run.
>
> **Speed (wide smoke).**
> - Threads alone: 1.07-1.14x on tree answers. The cause: sklearnex's `_assert_all_finite` holds the GIL and re-scans the block for every tree, 78% of predict time.
> - Scanning once per block gives 5x on one thread and 8.1x with 8 threads (207 s to 25.7 s). The memmap copy + flush (16-19 s) is then the floor.
> - Router: 1.7-1.8x (61 s to 34-36 s), below the plan's 2-3x.
> - Today's router runs numpy BLAS 16 / scipy BLAS 4, not "BLAS 4".
>
> **Conclusion.** Both speedups are safe (byte gates pass). Speedup 2 needs the scan moved to pay off, which is an owner choice between (a), (b) and (c), plus version pins and a guard test. Full-width timing (tables larger than RAM; router possibly I/O-bound) is not measured; the owner runs it.
>
> Scripts: pm25_adaptation_fast.py, run_shipped_blas1.py, compare.py, probe_finite_scan.py, run_fix_round.sh (engine/speedproof/). Outputs: D:/treeroute/speedproof/.
