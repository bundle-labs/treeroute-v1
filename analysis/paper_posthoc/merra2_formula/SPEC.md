# POST HOC re-score of the MERRA-2 PM2.5 rivals with the GMAO formula (owner ruling AM1, 2026-10-27)

## Why
The locked PM2.5 human rivals `merra2_lag1` (tier P, deciding), `merra2_same` (tier A) and `merra2_lag1_placebo`
(tier X) built their input x__pm25 from MERRA-2 as
`DUSMASS25 + SSSMASS25 + BCSMASS + 1.4*OCSMASS + 1.375*SO4SMASS` (kg m-3 x 1e9 -> ug m-3)
(`human/registry/pm25.yaml` options.variables; `pm25_products_map.py` in the project root).
NASA GMAO's MERRA-2 FAQ (https://gmao.gsfc.nasa.gov/gmao-products/merra-2/faq_merra-2) gives
`PM2.5 = DUSMASS25 + OCSMASS + BCSMASS + SSSMASS25 + SO4SMASS*(132.14/96.06)` and says no organic-carbon factor is
applied for MERRA-2. 132.14/96.06 = 1.37560 vs the locked 1.375: keep the sulfate factor EXACTLY as locked (1.375)
in the primary result, so the ONLY change is OCSMASS 1.4 -> 1.0; report the 132.14/96.06 variant as a one-line
side check only if cheap.

The locked verdicts never change. This is a post hoc sensitivity.

## Locked inputs (READ ONLY - never write, move, rename or touch anything here)
- Board run folder: `D:/treeroute/rivals_human/pm25/20261007_74e67609/` (lead_0/: preds_*.parquet, map_*.json,
  guard_*.parquet, coverage_*.parquet, done_*.json, refs.*; plus the board's own top-level files).
- Index tables: `D:/treeroute/human_index/pm25/20261007_74e67609/{merra2_lag1,merra2_same,merra2_lag1_placebo}/lead_0.parquet` (+ .json).
- Product files: `D:/pm25_products/merra2/aer_YYYYMM.nc` (252 monthly files 2003-2023; components DUSMASS25,
  SSSMASS25, BCSMASS, OCSMASS, SO4SMASS).
- Engine run: `D:/treeroute/runs/pm25/headline/20261007_74e67609/` (test_preds.parquet, verdict.json, slims).
- Human tool code: `D:/treeroute/human_rivals_build/human/` (rivals_human/*.py, adapters/pm25_reanalysis.py,
  registry/pm25.yaml, registry/_products.yaml). NOTE: the tool code changed AFTER the PM2.5 board ran
  (Part B, Parts 620-621: tool hash cd956f1d -> 16a2d736 -> 6a635858; the maps.py F6 edit is fire-only; the
  pre-edit baseline copy is in `D:/treeroute/human_rivals_build/_moved/20261025T194657Z_partB_baseline/`).
  Use code paths that are unchanged since the board ran, or the baseline copy; the reproduction gates below prove it.
- Engine code (read-only import allowed): `C:/Users/moh the ghost/Desktop/data set for reserch paper/engine/treeroute/`.
- Template for scoring (Part 623): `D:/treeroute/analysis/paper_posthoc/merra2_runaway/sens_A.py` and `sens_B.py`
  (reproduce the deciding contrast exactly with the tool's/engine's code path: covered rows, groups with >= 10 rows,
  per-group MAE, region jackknife, equivalence band -> verdict).
- Facts: `C:/Users/moh the ghost/Desktop/data set for reserch paper/paper/PAPER_FACTS.md` (RH4, RH6, K71, M14);
  `.../engine/PENDING_PARTS.md` Parts 617, 622, 623.

## What to compute (each implementer separately)
Gate 0a. Rebuild x__pm25 from the product files with the LOCKED formula (OC x1.4) at every row of each index table
   (same month offset, same unit centres, same interpolation as adapters/pm25_reanalysis.py). It must equal the
   locked index column (report max abs diff; must be <= 1e-6 relative, else STOP and report).
Gate 0b. From the locked index, re-run the locked procedure for merra2_lag1 lead 0 (candidate families, fit/score
   sets, pick rule, refit, skill guard, guarded test predictions) and reproduce preds_merra2_lag1.parquet's guarded
   column and the done file's guard numbers (rival_mae 3.5208945819429056, comparator_mae 3.5256518387286944,
   rows 68559, passed true; picked family F5 log_c). Report max abs diff. If it cannot be reproduced exactly, STOP and
   report what differs (do not continue on an unreproduced pipeline).
Gate 0c. Reproduce the locked deciding contrast for merra2_lag1: d +4.85562 [-4.146349, +13.857588], CANNOT TELL,
   rival MAE 8.444332, ours 3.588091 on 91,440 rows / 127 groups (RIVALS_TABLE row).
1. Corrected input: x__pm25 with OCSMASS x1.0 (everything else identical).
2. (i) FULL procedure on the corrected input: the same candidate families and pick rule (the pick may change),
   refit, guard, guarded test predictions. (ii) FORCED F5 log_c (the locked family) on the corrected input.
   For each: picked family, guard numbers (rival_mae, comparator_mae, rows, passed), test rival MAE, ours on the same
   rows, d with the region-jackknife interval and the verdict tag (same band and code path as the board), raw
   (unguarded) contrast too, calibration ratio and corr2 if the board's code gives them cheaply.
3. Same for merra2_same (tier A) and merra2_lag1_placebo (tier X): full procedure only.
4. For merra2_lag1 (i) and (ii): the largest guarded forecast (value, unit, month, x) and the count of forecasts
   > 1,000 ug/m3; the yakutia_larch_3553_2232 / 2021-08 row (locked: forecast 418,377.52 from x 1,698.28).
5. How much the correction moves x: median and 99th percentile of x_new/x_locked over test rows; share of rows where
   it moves by > 10%.

## Outputs
Write ONLY inside your own folder `D:/treeroute/analysis/paper_posthoc/merra2_formula/<A or B>/`:
script(s), `result_<A|B>.json` (every number above, full precision, plus sha256 of every input file read and of your
script), and row-level predictions `preds_<rival>_<variant>.parquet` (keys, x_new, raw, guarded) - always save
row-level predictions. Print a short plain-words summary at the end.

## Rules
- Run Python with `py -3.9 -I` (the tool's interpreter). `sys.dont_write_bytecode = True` before any import of tool
  or engine code, so no __pycache__ appears in locked folders.
- No seed variation: use the tool's fixed random_state wherever the procedure has one.
- One light job: the machine has 15.8 GB RAM and a download is running; read columns selectively; no parallel
  heavy jobs. Never write under D:/adaptation, D:/pm25_adapt, D:/pm25_forecast, D:/pm25_rivals, D:/run89full,
  D:/defo_corrector/banks, D:/defo_tier2/banks, D:/treeroute/coral_build/coral_store, the board folders,
  human_index, human_products, pm25_products or the build folder.
- Never delete any file. Never run the tool CLI (init/tune/lock/refit/board/join) or fetch_products.py.
- Do not read the other implementer's folder.
- Never name a cause for the runaway forecast (e.g. smoke) - report numbers only.
