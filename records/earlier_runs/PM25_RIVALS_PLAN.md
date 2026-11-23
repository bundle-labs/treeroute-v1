# Plan: PM2.5 nowcast rivals (2026-09-25)

Designed read-only by 9 agents: 4 scouts, 4 skeptics and 1 designer. **Nothing has been run or edited.**

## Summary

This is a design for a benchmark of rivals against the PM2.5 nowcast. It is read-only: nothing was edited or run. Eight rivals: four core (recent-level/trend normals, a land-use-regression-style ridge, LightGBM, random forest), three optional (space-time extra-trees, a Di-style blend, the per-region weather-normalisation model the LOCAL plan already designs) and one needs-owner-download (CAMS EAC4, with MERRA-2 as a second arm). None of the operational products can run on our inputs. They all calibrate satellite AOD or a chemistry model against same-period monitors, and our target is one of them (ACAG's GWR). So the fair rivals are the learning ENGINES those products use, run on our 103 clean drivers. The paper must call them that, not 'operational methods'.

Every rival is scored on the same 95,856 rows against nowref (MAE 4.1563, anomaly-R2 +0.060, hit 0.494; guess-normal 4.5334, geometric normal 4.3668; D:/pm25_forecast/full/L1/predictions.parquet). It is not scored against 4.100, which carries the oni/tni look-ahead.

There are two main boards. On Board A the rivals are fitted on donors only and never see the test cells: it measures what local history is worth. On Board B each rival gets the SAME per-cell log-link calibration (MOS, a per-cell regression on the cell's own history) on each cell's 203 pre-2020 rows. Dropping the rival column from that calibration gives back the geometric normal, so the bar is nowref's 0.2105 ug/m3 below it. Two separate labelled boards hold the input-advantaged products (C) and the local-only model (L).

Tuning is on the inner window only: trials fitted up to 2016 and picked on 2017-2019 MAE, full grids, deterministic settings, every trial logged. Uncertainty is the leave-one-region-out jackknife, and results are read with the R5 rule and its 0.0395 ug/m3 band. Every row is saved to D:/pm25_rivals.

ATTENTION 1: rivals.py cannot be pointed at PM2.5. Its _clip (rivals.py:145-148, and inside every rival body) would silently cap every prediction at 1 ug/m3. Its metrics, seeded bootstrap and output folder also break the PM2.5 rules. The route is a standalone pm25_rivals*.py that imports pm25_adaptation.score() and adaptation.jack().
ATTENTION 2: the owner put the PM2.5 rival and ladder plan ON HOLD and deferred the tuning level (LOCAL_RIVAL_AND_LADDER_PLAN.md:3-9). This request needs an explicit resume ruling before any code body is written.
ATTENTION 3: Board B has two traps that would unfairly flatten the rivals. Reusing solve_local at the frozen (10, 0.0625) shrinks a single rival column to about 0.004 of its OLS value. Reusing rivals.py _recal gives no climatology term.
ATTENTION 4: the products observe the test month's aerosol through the same MODIS AOD as the target. Losing to them measures what that observation is worth; it is not an architecture failure.
Machine time is estimated at about 4-13 h for the core set. That is extrapolated from defo timings and not measured, so a timing smoke comes first. The owner runs it as separate commands, one heavy job at a time.

## Rivals

| Rival | Plain description | Why it is a fair operational rival | Board | Time | Priority |
|---|---|---|---|---|---|
| Recent-level and trend normals (no-model operational baseline) | Predicts each cell's month from its own past only: the average of the last few years for that month, or a straight-line trend carried forward. | This is what someone with a past record and no model would issue. It is also the direct test of the documented train-to-test level shift: 82 regions fell and 45 rose, about half a test SD (pm25_adaptation.py:74-77). It uses only pre-2020 target rows, the same history the router gets and nothing more. | Board B (local information), printed as a floor beside guess-normal and the geometric normal | Seconds to run. About 1 h to code and review. | core |
| Land-use-regression-style linear model (ridge; ESCAPE / CACES shape) | A straight-line model of PM2.5 on the drivers (land, population, terrain, weather), fitted on the donor regions. | Land-use regression is the classic exposure model of European (ESCAPE, Eeftens 2012) and US (CACES) cohort studies, and it runs on map and weather predictors without AOD. It is the transparent classical-statistics opponent. Label it 'LUR-style linear engine': it has no stepwise selection and it includes monthly weather. | A and B | About 15-30 min for 12 trials + 2 refits. Extrapolated from defo's ridge (0.3 min on 400k x 322); not measured. | core |
| Gradient boosting, LightGBM (Zhong et al. 2021 / Chen et al. 2019 shape) | Many small decision trees added one after another, each fixing the mistakes of the ones before, fitted on the donor regions' drivers. | Boosting is the most-used engine in national PM2.5 mapping. Zhong et al. 2021 (National Science Review) mapped PM2.5 from meteorology alone, with no AOD and no lagged PM2.5. That is the closest published match to a drivers-only nowcast, which makes this the headline strong rival. | A and B | Extrapolated at 1-15 min per trial, so about 1-8 h for 48 trials + 2 refits. The basis is defo's LightGBM, 400 trees in 1.3 min; it is not measured on PM2.5. The timing smoke comes first, and the owner runs the command. | core |
| Random forest (Hu et al. 2017 shape) | Hundreds of decision trees, each grown on a resampled copy of the donor rows, then averaged. | It is the most common engine in the satellite-PM2.5 literature. Hu et al. 2017 (ES&T) used it for US daily PM2.5. Here it runs on our drivers without AOD. | A and B | With sklearnex, about 5-15 min per trial, or about 1-2 h with refits. Stock sklearn: about 8-12 h. Both are extrapolated from defo's RF at 33.9 min; neither is measured. | core |
| Space-time extra-trees (STET; Wei et al. 2020, ChinaHighPM2.5 / CHAP) | Like a random forest, but the split points are drawn at random. Wei adds distance and day-of-year terms so the model knows where and when it is. | It is the engine behind ChinaHighPM2.5, a product widely used in health studies, so it is a named operational method whose engine runs on our drivers. | A and B | Extrapolated at 0.5-3 h per variant; not measured. Extra-trees is not guaranteed faster than RF. | optional |
| Blended ensemble (Di et al. 2019 shape: boosting + forest + linear/NN) | Combines the boosting, forest and linear models' predictions with fixed weights learned before the test years. | Di et al. 2019 (Environment International; Harvard group, distributed by NASA SEDAC) blend a neural network, a random forest and gradient boosting. The blend tests whether combining the engines beats each of them alone. | A and B | Minutes without the MLP. With it, 1-3 h more (not measured). | optional |
| Per-region weather-normalisation model (Grange et al. 2018 rmweather shape; the LOCAL plan's local rival) | Learns how PM2.5 in one test region reacts to weather from that region's own 2003-2019 record, then applies that to the 2020-2023 weather. | Agencies use per-site weather normalisation for trend and intervention work (Grange 2018, on PM10 at 31 Swiss sites; npj 2023 intercomparison). It is the 'local statistician' opponent: a model built only from the place's own past. | Board L (local-only), separate | Never timed. Extrapolated at about 0.5-1.5 h for 20 regions, since each fit is about 100x smaller than a donor fit. A 3-region smoke comes first. | optional |
| Aerosol reanalysis product: CAMS EAC4 first, MERRA-2 as a second arm | Takes the surface PM2.5 that ECMWF's (or NASA's) global aerosol reanalysis already computes for each month, moves it onto our cells, and optionally corrects its bias. | It is the standard fallback where there are no monitors, and the owner already ruled EAC4 the nowcast's operational baseline, 'fitted on donors only' (D4(a), QUESTIONS_ROUND3_HANDOFF.md:375-378, 478). It observes the test month's aerosol by assimilating MODIS AOD from the same instruments as the target, so it is INPUT-ADVANTAGED. The required wording (D1) is 'assimilates the same satellite AOD but zero ground monitors'. | Board C (input-advantaged). Never pooled into A or B. | EAC4: minutes after the owner's licence click, and minutes to score. MERRA-2: about 1-2 h over OPeNDAP (not measured). | needs-owner-download |

### Implementation and tuning, per rival

- **Recent-level and trend normals (no-model operational baseline)**  
  *Implementation:* New, about 40 lines. For each cell and month, take the geometric (log1p) and arithmetic mean over the last k years. Separately, fit a per-cell OLS trend on log1p(y) with optional damping. Keys, y and clim come from D:/pm25_forecast/full/L1/predictions.parquet, and the history comes from calib_rows.parquet (203 rows per cell, the same rows nowref used). No drivers and no donors are needed.  
  *Tuning:* k in {1,2,3,5} x scale {log, raw} x trend damping {0 = flat recent level, 0.5, 1}. Build on 2003-2016, pick the lowest MAE on the test cells' 2017-2019 rows (71,892), rebuild through 2019 and score 2020-2023 once. Fully deterministic.
- **Land-use-regression-style linear model (ridge; ESCAPE / CACES shape)**  
  *Implementation:* Copy the body of rivals.py r_ridge (176-184) WITHOUT its _clip. Standardise, then fit ridge on the 103 clean features + month (12 dummies) + lat. For the log1p link, back-transform with expm1 and no smearing, as the architecture does.  
  *Tuning:* alpha in {0.1, 1, 10, 100, 1e3, 1e4} x link {y, log1p} = 12 trial fits on donors up to 2016. Board A picks by MAE on the donor holdout's 2017-2019 rows; Board B picks by post-MOS inner MAE. Refit both picks on all donors up to 2019. Closed form, no randomness.
- **Gradient boosting, LightGBM (Zhong et al. 2021 / Chen et al. 2019 shape)**  
  *Implementation:* New function in pm25_rivals.py, modelled on the rivals.py qmap / lgbm_tweedie bodies but without _clip. Fit on y or on log1p(y) and back-transform with expm1. Staged predictions at fixed round checkpoints give every round count from one fit.  
  *Tuning:* The full 24-setting grid already used in the project (presplit_cc/bench_trees.py:818-827: num_leaves 31/127/511 x lr 0.1/0.03 x min_child 20/100 x colsample 0.3/0.8) x link {y, log1p} = 48 trials, with rounds read from staged predictions. subsample 1.0; colsample under ONE constant random_state that is never varied; deterministic=True, force_row_wise=True, fixed num_threads (LOCAL plan option b). Same pick rules as ridge.
- **Random forest (Hu et al. 2017 shape)**  
  *Implementation:* Template: rivals.py r_rf (217-223), without _clip. 200 trees with a depth cap: my arithmetic, not measured, says a fully grown forest on 1.8M rows could need about 10 GB. Recommended engine: scikit-learn-intelex, about 11x faster on this machine. It gives slightly different numbers from stock sklearn, so disclose it.  
  *Tuning:* max_features {0.3, 0.6} x max_depth {12, 16} x link {y, log1p} = 8 trials, min_samples_leaf 5. The bootstrap uses ONE constant random_state=0, never varied. Same pick rules.
- **Space-time extra-trees (STET; Wei et al. 2020, ChinaHighPM2.5 / CHAP)**  
  *Implementation:* sklearn ExtraTreesRegressor with depth and leaf caps. The defaults (all features, unlimited depth, no bootstrap) risk running out of RAM on 1.8M rows. Two variants: (1) drivers + month + lat; (2) '+space', adding lon and Wei's Haversine space and time-radian terms. Copy their exact form from the paper when coding. Label variant (2) as having more geography than the architecture's trees.  
  *Tuning:* max_features {0.3, 1.0} x max_depth {12, 16} x link {y, log1p} = 8 trials per variant, with one constant random_state. Same pick rules.
- **Blended ensemble (Di et al. 2019 shape: boosting + forest + linear/NN)**  
  *Implementation:* No new base fits: it reuses the saved tuned LightGBM, RF and ridge predictions. An MLP is an optional fourth learner. The blender is a set of non-negative weights summing to 1, fitted on the Board-A selection rows. Di's geographic GAM blender is dropped because it would extrapolate into the 20 held-out regions. On Board B the blend enters the MOS as ONE column; three separate columns would turn it into a mini-router, which is the stack_models control.  
  *Tuning:* The weights are the only fitted part and use pre-2020 rows. If the MLP is included, it gets a small grid under the same rules.
- **Per-region weather-normalisation model (Grange et al. 2018 rmweather shape; the LOCAL plan's local rival)**  
  *Implementation:* Already designed as pm25_local_rival.py (LOCAL_RIVAL_AND_LADDER_PLAN.md:55, 116-127): one LightGBM per test region on its 99-100 scored cells (about 20.4k rows), joined to the keys with y asserted equal. It breaks rivals.py rule 1 (base models see donor units only), so it gets its own board.  
  *Tuning:* As in the LOCAL plan: the 24-setting LightGBM grid x link, fit up to 2016, pick on 2017-2019 by MAE, refit up to 2019. Same determinism settings.
- **Aerosol reanalysis product: CAMS EAC4 first, MERRA-2 as a second arm**  
  *Implementation:* New pm25_products.py. EAC4: monthly pm2p5 at 0.75 deg for 2003-2023 (about 0.1 GB), via cdsapi pointed at the ADS URL with the ADS token. MERRA-2: the 5 species of M2TMNXAER via an adapted presplit_cc/fetch_dust_aod.py, run globally (about 1 GB); the Earthdata login already exists; MERRA-2 has no nitrate. Interpolate bilinearly to cell centres and multiply by 1e9 to get ug/m3. Arms: R0 = raw product; R1 = a 2-parameter log mapping fitted on the 107 donor regions for 2003-2019 (the ruled variant); R2 = the Board-B MOS with the product as the column (needs a ruling). Plus a time-shifted placebo: the same cell and month, but the product anomaly from another year.  
  *Tuning:* R1 has no hyperparameters. R2's shrink is picked on the inner window, as on Board B. Nothing touches 2020-2023.

## Protocol

- 0. Rulings first. The owner resumes the on-hold rival plan for this scope and answers the decisions below. Then pre-register the rival list, grids, MOS form, pick rules, metrics and reading rule as a new Part in EXPERIMENT_SUMMARY.md BEFORE any number is computed. Log each later step as its own Part.
- 1. Fixed rows, all read from D:/pm25_forecast/full/L1:
- TEST: the 95,856 rows of predictions.parquet (20 regions, 1,997 cells, 2020-2023).
- LOCAL CALIBRATION: calib_rows.parquet, 405,391 rows = 1,997 x 203, the same rows nowref used.
- INNER: the 71,892 test-cell rows for 2017-2019.
- DONORS: donor_rows.parquet, 2,177,990 rows up to 2019 and 1,793,679 up to 2016. These are the nowcast bank's rows; the has_predecessor flag marks the lag bank.
These files hold keys only, so the features are re-read from the panel once and cached on D:.
- 2. Gates, checked before any rival number is read; any failure stops the run:
- exact row counts;
- the join on (cell_id, year, month) gives max|y diff| = 0;
- ONE clim for the whole board: the L1 file's;
- 20 regions and 1,997 cells;
- no fitted object reads a row after 2019 (month-level asserts);
- no rival prediction is clipped at 1 (guards against the rivals.py _clip bug).
- 3. Features: the clean 103 (verdict.json:9-113; the centred means oni and tni dropped), plus month and lat. Those two are the router's own context (pm25_adaptation.py:195), so the rivals get no more geography than the architecture. No lon or distance terms, except in the labelled STET '+space' variant.
- 4. The architecture row is nowref: 4.1563 / +0.060 / hit 0.494, with guess-normal 4.5334 and geometric normal 4.3668 on the same rows. Describe it as 'a log-link router over donor trees', since its corrector is equivalent to its placebo. Print the 105-feature 4.100 only with the oni/tni look-ahead flag, and never pair a rival against it. Disclose that nowref's arm and penalty were inherited from the 105-feature decision, and that the penalty is an edge pick.
- 5. Board A (donor-only, 'ungauged vs gauged'): each rival is fitted on donors and never sees a test-cell label. Its hyperparameters are picked by MAE on the 2017-2019 rows of a fixed donor holdout: every 4th donor region in the frozen pm25_split order, no seed. Board A measures what local history is worth, not which base model is better. Do not build the unrouted-bank architecture row unless the owner asks.
- 6. Board B (the same local calibration for everyone): per cell, fit log1p(y) ~ [1, lclim_c - mean, standardised month, log1p(p_rival)] on the cell's 203 calibration rows, then back-transform with expm1 and no smearing. For a log1p-target rival, feed its log prediction straight in. The shrink on the rival column comes from a grid that includes 0 (plain OLS) and is picked by inner MAE, with the MOS fitted on 2003-2016 and lclim built from those rows only. N2 guard: if a rival+MOS does not beat the geometric normal on the inner window, it falls back to the arithmetic normal, exactly as the architecture does (DECLINE_TO='treesoff'). NEVER build Board B with solve_local at (10, 0.0625) or with rivals.py _recal. Check: removing the rival column must reproduce the geometric normal exactly.
- 7. Boards C (products: R0, R1, R2 plus a time-shifted placebo) and L (the local-only model) are printed separately, with their information level stated. They never enter the Board A or B win/tie/loss counts. The lead-1 persistence rows from Part 561 appear only as labelled reference rows, because they use y(t-1). Damped persistence is 4.2632 / +0.087.
- 8. Tuning:
- Inner window only. Each trial is fitted ONCE on donors up to 2016, excluding the Board-A holdout, and that fit serves both boards' picks.
- Refit the two picks on all donors up to 2019 with the same number of rounds, and score 2020-2023 once. Nothing is re-tuned after a test number is seen.
- Every trial goes in a trial CSV; print the rival trial counts beside the architecture's 142 inner candidates.
- Determinism: fixed thread count recorded with threadpool_info, and one constant random_state where the method needs randomness. First run a LightGBM 2-vs-6-thread determinism check on synthetic data, and never change the thread count mid-run.
- 9. Metrics come from pm25_adaptation.score() (263-307): MAE (primary), anomaly-R2 against the L1 clim, and hit rate within +-2 ug/m3 with hit0. Guess-normal and the geometric normal sit beside every row. Also report:
- per-region anomaly corr^2;
- the level ratio mean(p)/mean(y);
- a per-year table (2020-2023; 2023 had no skill) and a per-region table;
- inner corr^2 logged beside inner MAE for every trial, flagged whenever the MAE pick and the corr^2 pick differ.
- 10. Uncertainty: for each region, contrast = MAE(rival) - MAE(nowref), all regions weighted equally. Take the leave-one-region-out jackknife over the 20 test regions (adaptation.jack, adaptation.py:530-537). No bootstrap and no seeds (ruling A10).
- 11. Reading rule, R5 with EQ = 0.0395 ug/m3:
- ARCHITECTURE BETTER: CI above 0 and point estimate at least 0.0395.
- RIVAL BETTER: CI below 0 and point estimate at most -0.0395.
- EQUIVALENT: the whole CI inside +-0.0395.
- Otherwise CANNOT TELL.
Check the band BEFORE the HURTS branch; the current verdict prints HURTS first. For each board, the W/T/L table counts rivals under each outcome, and the per-region win counts are printed. Smoke deltas under 0.01 are never read.
- 12. Controls:
- For any MAE win, a scale control: rescale the loser by a scalar taken from pre-test rows only.
- The Board C placebo.
- For Board B, each rival's MOS slope on the inner window vs the test window (month memorisation).
- Report every rival on every board: no best-on-test headline and no automatic selector across families.
- 13. Save every row. Each rival and board gets D:/pm25_rivals/<board>/<rival>.parquet with reg, cell_id, year, month, y, clim, p_geo_normal, p_<rival> and the per-cell MOS coefficients. Also save the inner-trial predictions, the trial CSV, threadpool_info and a config/code fingerprint. Never write into D:/pm25_adapt/full or D:/adaptation/_rivals.
- 14. Run order, one heavy job at a time, each as a command the owner runs (close Opera and Riot first):
(1) build the cache;
(2) timing smoke: one trial per engine on the full donor rows up to 2016, logging minutes and peak RAM;
(3) the normals and ridge;
(4) LightGBM;
(5) RF;
(6) the optional rivals;
(7) Board C, after the downloads are approved;
(8) the report.

## Code plan

- **pm25_rivals_data.py (new)** (boilerplate): Builds the cache.
- Imports safely: reads its own flags, then sets sys.argv before importing pm25_adaptation, pm25_architecture or adaptation (the rivals_final.py:38-52 pattern).
- Reads the L1 keys (donor_rows, calib_rows, predictions) and loads the 103 features plus month and lat per region.
- Asserts every row count.
- Writes float32 .npy files to D:/pm25_rivals/cache.
- Cleans up in a finally block: drops memmap references and runs gc, then removes any D:/pm25 pool files, so no orphan blocks the next pm25_adaptation run.
- **pm25_rivals.py (new): harness** (boilerplate): Rival registry, trial loop, staged-prediction checkpoints, the trial CSV and threadpool_info. Caching checks KEYS, not just length. Saves keyed parquet files. Has no _clip, or a pm25 bound of [0, inf).
- **pm25_rivals.py (new): engine bodies** (science): Ridge, LightGBM, RF, ExtraTrees (plus the '+space' variant), the blend weights, and the optional MLP: their grids, link handling and determinism settings. The owner writes the function signatures, the agent fills the bodies, and the owner reviews them.
- **pm25_rivals.py (new): Board-A donor holdout and pick rule** (science): Fixed holdout: every 4th donor region in the frozen pm25_split order, no seed. Pick by MAE on 2017-2019.
- **pm25_rivals_mos.py (new)** (science): The per-cell log-link MOS: [1, lclim - mean, standardised month, log1p(p)] with a shrink grid that includes 0, the inner-window decision, the N2 guard and the fall-back to the arithmetic normal. Unit test on synthetic data: with the rival column removed it must reproduce the geometric normal exactly. Also a test that it does NOT go through solve_local.
- **pm25_rivals.py (new): recent-level and trend normals** (science): k-year recent means (log and raw) and a per-cell damped trend, built only from pre-2020 rows.
- **pm25_products.py (new, only after owner approval)** (boilerplate (ingest) + science (R1/R2/placebo)): Boilerplate: EAC4 download via cdsapi at the ADS URL, and a MERRA-2 global 5-species fetch adapted from presplit_cc/fetch_dust_aod.py; bilinear interpolation to cell centres, x1e9, handling 0-360 longitudes and descending latitudes. Science: the R1 donor mapping, the R2 MOS arm and the time-shifted placebo.
- **pm25_rivals_report.py (new)** (boilerplate): Imports pm25_adaptation.score() and adaptation.jack(). Computes the per-region contrasts against p_nowref and applies the R5 verdict with the band checked before HURTS. Writes the per-year and per-region tables, the Board A/B/C/L tables and W/T/L counts, and the scale-control and MOS-slope diagnostics. Output goes to D:/pm25_rivals/report.
- **scratchpad determinism_check.py (new)** (boilerplate): Runs LightGBM on synthetic data at 2 vs 6 threads with deterministic=True and force_row_wise=True; ExtraTrees and RF at a constant random_state; and asserts the outputs are identical.
- **rivals.py / rival_data.py** (boilerplate): NO edits. The 12-cell FULL_BOARD and FINAL_TABLE depend on them, and a pending C6 rebuild still needs them.
- **EXPERIMENT_SUMMARY.md** (boilerplate): A pre-registration Part before any number, then one Part per run step with its explanation and result.

## Total time

None of these times is measured; they are extrapolated from defo timings, and a timing smoke comes first.

Coding: about one agent session for the boilerplate, plus the owner's review of about 5 science bodies.

Machine time, core set: about 4-13 h in total.
- Cache build: about 0.7-1 h. The pool build measured 35-44 min.
- Normals and ridge: 0.5 h or less.
- LightGBM, 48 trials plus refits: 1-8 h.
- RF on sklearnex: 1-2 h. Stock sklearn would be 8-12 h.
- MOS and scoring: under 0.5 h.

Optional set: about 2-8 h more (STET 0.5-3 h per variant, the blend in minutes or 1-3 h with an MLP, Board L 0.5-1.5 h).

Board C: minutes for EAC4 after the licence click; about 1-2 h for the MERRA-2 fetch.

The owner runs this as 3-5 separate commands, one heavy job at a time.

## Owner decisions

### The PM2.5 rival and ladder plan is ON HOLD, and the rival tuning level was deferred (LOCAL_RIVAL_AND_LADDER_PLAN.md:3-9). What should this request resume?
- (a) Resume only the donor-side rivals (Boards A and B) plus the cheap normals; keep the local-only rival and the ladder on hold
- (b) Resume the whole LOCAL plan, including Board L and the ladder
- (c) Keep everything on hold
- **Recommendation:** (a). It answers the request with the least new machinery. Board L can follow once A and B are read.

### Which feature set, and which architecture row, do the rivals pair against?
- (a) The clean 103 features (oni/tni dropped) vs nowref 4.1563 / +0.060
- (b) The 105 features including the oni/tni look-ahead vs log_corrector 4.100 / +0.090
- (c) Both (doubles every fit)
- **Recommendation:** (a). The 4.100 carries a 1-2 month look-ahead and can only be quoted with a flag.

### How much geography do the rivals get?
- (a) month + lat, the same as the router's context
- (b) none, drivers only
- (c) also lon and Haversine distance terms
- **Recommendation:** (a). Use (c) only as the labelled STET '+space' variant, because it gives the rivals more geography than the architecture has.

### What tuning budget do the rivals get?
- (a) Fixed library defaults, as in the 12-cell benchmark
- (b) Full grids by trial count: LightGBM 24 x link 2 = 48, ridge 12, RF 8, STET 8 per variant
- (c) Reduced grids
- **Recommendation:** (b). The architecture chose among 142 inner candidates, so untuned rivals would be an unequal fight.

### Which rows pick Board A's hyperparameters?
- (a) A fixed donor-region holdout (every 4th donor region), 2017-2019: stays donor-only
- (b) The test cells' own 2017-2019 labels, with the board labelled 'test-cell-tuned'
- **Recommendation:** (a). Option (b) breaks rivals.py rule 1.

### Randomness under the no-seeds rule.
- (a) LOCAL plan option (b): subsample 1.0; one constant random_state for colsample, RF bootstrap and ExtraTrees cuts; deterministic=True; fixed thread count
- (b) No randomness at all: drop the colsample axis, RF and ExtraTrees
- (c) subsample 0.8 with random_state 0
- **Recommendation:** (a). The state is set once and never varied.

### Which random-forest engine?
- (a) scikit-learn-intelex (about 11x faster; numbers differ slightly from stock)
- (b) Stock sklearn (about 8-12 h extrapolated)
- **Recommendation:** (a), disclosed in the Part.

### What shrink does the Board B calibration use?
- (a) Plain OLS only
- (b) A shrink grid that includes 0, picked on inner MAE (as the architecture's penalty was)
- **Recommendation:** (b). Never the frozen (10, 0.0625) through solve_local, which flattens a single column to about the normal.

### Should the product rivals (Board C) run this round?
- (a) EAC4 R0 + R1 (the ruled variant) + R2 labelled, with MERRA-2 as a second arm (about 1 GB, needs its own download approval)
- (b) EAC4 R1 only, strictly per D4(a)
- (c) Skip products this round
- **Recommendation:** (a) if you accept the EAC4 licence on the ADS Download tab (G6) and approve the MERRA-2 fetch; otherwise (c). The donor boards do not wait on this.

### Which harness route?
- (a) New standalone pm25_rivals*.py writing to D:/pm25_rivals, with rivals.py untouched
- (b) Extend rivals.py with --problem pm25 and a _clip fix
- **Recommendation:** (a). Option (b) risks the 1 ug/m3 clamp and breaks the 12-cell table rebuild.

### Which uncertainty method?
- (a) Leave-one-region-out jackknife only (ruling A10)
- (b) The LOCAL plan's A3: region bootstrap plus jackknife
- **Recommendation:** (a). A10 governs PM2.5.

### Should Board A get a like-for-like architecture row (the unrouted donor-bank mean)?
- (a) No: label Board A 'ungauged vs gauged'
- (b) Yes: pool + 103-feature bank rebuild + matrix pass, more than 2.5-3.2 h, and the plan calls it 'a different estimator'
- **Recommendation:** (a)

## Risks

- rivals.py's _clip caps every non-coral prediction at 1 ug/m3 (rivals.py:145-148, and inside every rival body). Importing rivals.py, pm25_adaptation or adaptation also reads or overwrites sys.argv, and rivals.py creates D:/adaptation/_rivals. Copy the model bodies; never import rivals.py for PM2.5.
- Output collisions: any file in D:/adaptation/_rivals crashes the rebuild of the 12-cell FULL_BOARD and FINAL_TABLE. A crashed loader that leaves D:/pm25/pool_*.f32 behind blocks the next pm25_adaptation run. Delete memmaps only after dropping references and running gc (Windows).
- Board B traps, both of which would unfairly flatten the rivals toward the normal. solve_local at (10, 0.0625) shrinks a single column to about 0.004 of its OLS value (illustrative arithmetic). rivals.py _recal has no climatology term and works on the raw scale.
- MAE rewards the median. About 44% of nowref's gain over guess-normal is the log normal alone (0.1666 of 0.3771), so a log1p rival can look good on MAE through timidity alone. Always show corr^2 and anomaly-R2, both normals, and the scale control.
- Month memorisation: a high-capacity rival can fit the 2003-2019 history rows better than it predicts 2020-2023, and the MOS would then over-trust it. Report the MOS slope on the inner window vs the test window.
- Framing: these are the ENGINES of published methods run on drivers-only inputs, not the operational products. Published skill (CV R2 0.80-0.93, with AOD, within-network CV) must never share a table with our held-out-region scores.
- Board C is circular and not homogeneous in time. EAC4 and MERRA-2 assimilate the same MODIS AOD as the target. EAC4 loses AATSR in March 2012; MERRA-2 reportedly stops assimilating AERONET after 2014 (unverified), and its emission inventories end in 2006 and 2008. CAMS near-real-time is excluded: its model changed 4 times inside 2020-2023.
- Costs are unmeasured, and RAM is 15.8 GB. Uncapped RF or ExtraTrees on 1.8M rows can run out of memory. Run one heavy job at a time, never change the thread count mid-run, and time before any full run.
- The existing R5 verdict prints HURTS before it checks the equivalence band. The new report must check the band first, or it will mislabel near-ties.
- On these exact rows, lead-1 damped persistence already has a higher anomaly-R2 than nowref (+0.087 vs +0.060). It uses y(t-1), so it must stay a labelled reference row, or it will be misread as a nowcast rival that beats the architecture.
- nowref has no 103-feature inner-window predictions, so the inner-window ledger cannot put it beside the rivals. 2023 had no skill, so read the per-year tables before any pooled claim.
- Multiplicity: 8 rivals across several boards and links. Report all of them, with no best-on-test headline and no automatic selector (a measured selector was worse: 0.821/0.823 vs a fixed 0.830). Smoke deltas under 0.01 carry no sign information.