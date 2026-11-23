# NDVI: human rivals per lead (research note, 2026-10-21)

Read-only research. Nothing was downloaded or installed. Every claim cites a file:line or a URL.

## 0. Bottom line

| Lead | Primary human rival | Optional (at most one) | Plain verdict |
|---|---|---|---|
| 0 (nowcast) | **H1: per-cell ARDL** (Bayesian autoregressive distributed lag on the NDVI anomaly with lagged NDVI and climate; the Sussex/NDMA "AstroCast" method family) | Kraft 2019 global LSTM (climate only), re-run on the headline rows | A real, published, piloted-operational method exists for short leads. Legitimate. |
| 6 months | **H1 at a direct 6-month horizon** (same code, predictors at the issue month) | H1 + SEAS5 lead-month-6 climate anomalies (seasonal-forecast-driven form; needs a CDS download) | No operational 6-month NDVI forecaster exists. H1-direct is a published statistical method stretched past its published 10-week range: say so. |
| 12 months | **None legitimate as "operational".** The reference rows stand (guess-normal, last-5-years normal, persistence, damped persistence). | H1 at h=12, labelled "statistical extension, not a published 12-month method" (zero extra cost) | No seasonal climate forecast in the C3S archive reaches month 12; no published NDVI method claims 12 months. |

Cost on this PC (Section 7): primary only about 1-2 h of machine time plus about 1 day of code and tests. With both optionals: about 4-8 h of machine time plus 3-12 h of CDS queue wall time.

## 1. Our design (what any rival must match)

- Run: D:/treeroute/runs/ndvi/headline/20261016_d1de3158 (plan.json windows: inner fit 2003-2016, inner score 2017-2019, train_end 2019, test 2020-2023).
- Target: MOD13C2.061 CMG 0.05 deg monthly NDVI, panel column V11_mean_ndvi on 4 km panel cells (engine/datasets/ndvi/ingest/target_reader.py:3-5; dataset.yaml:31).
- Rows: 133 groups, LORO, 15 scored units per group (PREREGISTRATION_DRAFT_ndvi.md:71-73, 120-124). Saved rows: 95,184 per lead, 94,527 labelled, 1,983 units (counted from test_preds.parquet and ladder/lead_6, lead_12 test_preds.parquet).
- Unit ids carry the grid index; lat/lon are in engine/datasets/ndvi/data/static/part-0.parquet (2,289,236 cells; columns cell_id, region, lat, lon, grid_ix, grid_iy).
- Information at issue (checked on disk):
  - Lead L issue step = target step minus L (time - issue = 0, 6, 12 in the three files).
  - Latest NDVI known = issue minus 1. Checked: at lead 6, base__persistence equals y at t-7 on 80,749 of 80,749 matched rows (0 of them at t-6 or t-8). derived.json R17: start_offset_steps 1, target reach 15 days each side. The rival must use the same offset as the engine's history block; the designer should confirm it once more for lead 0.
  - Climate: features end at the issue step (features/build.py:1-4). At lead 0 the row sees the target month's climate (router context holds unlagged era5l_d2m and V01_mean_temp_C: plan.json context).
- Reference rows already saved: guess_normal, last5_normal, predict_zero at every lead; persistence and damped_persistence at leads 6 and 12 (columns of ladder/lead_6/test_preds.parquet). Lead 0 has no persistence row.
- Metrics: MAE headline, anomaly R2, corr2, hit rate (PREREGISTRATION_DRAFT_ndvi.md:128-136). Engine result: lead 0 MAE 0.0315 vs normal 0.0394, anomaly R2 0.317; leads 6 and 12 declined to the normal (HEADLINE_MODEL_TABLE.md:14-16).
- Parity rule for rivals, simplest form: a rival may use only columns the NDVI ban list keeps, at the same lag the engine uses at that issue step, plus the target history up to issue minus 1.

## 2. Candidate landscape (verified and extended)

| Candidate | What it is | Who uses it / standing | Verdict |
|---|---|---|---|
| **AR on VCI / NDVI (Barrett et al. 2020)** | Linear AR(3) and Gaussian process on VCI3M history | RSE 248:111886 (https://dx.doi.org/10.1016/j.rse.2020.111886). Targets the index Kenya's NDMA uses for drought alerts. Horizons 2-6 weeks; history only; adding current rain and temperature "had little impact" (https://ar5iv.arxiv.org/html/1911.10339). | Legitimate at parity (NDVI to issue-1). Nested inside H1. |
| **BARDL (Salakpi et al. 2022)** | Bayesian ARDL: VCI lags + lagged precipitation + soil moisture | NHESS 22:2703-2723 (https://nhess.copernicus.org/articles/22/2703/2022/); code on Zenodo ("Bayesian-ARDL"). R2 0.94/0.85/0.74 at 6/8/10 weeks vs AR 0.88/0.77/0.65. Piloted in NDMA monthly bulletins in 7 Kenyan counties, short rains 2020 (https://www.sussex.ac.uk/research/centres/sussex-sustainability-research-programme/research/vegetation-condition-forecasting). | **Primary (H1).** The closest thing to an operational vegetation forecaster. |
| Kraft et al. 2019 LSTM | Global LSTM from 12-month climate windows + soil statics | Front. Big Data 2:31 (doi 10.3389/fdata.2019.00031). Research, not operational. | Optional at lead 0 only (Section 4). |
| McPhillips 2026 GP | Per-cell GP on 3- and 12-month precipitation and VPD | Remote Sensing 18(6):850 (NDVI_BASELINE_REPORT.md:80-84). | Drop: worst rival before (its ORACLE lost 44/44, NDVI_BASELINE_REPORT.md:165); dominated by H1, which holds the same climate terms. |
| Per-cell SARIMA / Holt-Winters | Seasonal time-series model of the pixel's NDVI | Standard statistics; e.g. Jiang et al. 2010, RSE 114(7):1432 (doi 10.1016/j.rse.2010.01.026; MODIS LAI per pixel, SARIMA best of three). | Drop: a deseasonalised AR is H1 without climate; SARIMA adds order search per pixel and handles gaps badly. Mention in the paper as covered. |
| SEAS5-driven impact model | Seasonal climate forecast fed into a climate-to-NDVI map | The standard operational pattern (CEMS GEFF-SEAS5 does this for fire). No NDVI product does it. | Optional at lead 6 (Section 5). |
| NOAA VHI, FAO ASIS, Copernicus Global Land, FEWS NET, Grass-Cast | Monitoring products / outlooks | NDVI_BASELINE_REPORT.md:57-65 | Not forecasters. A lagged VHI is lagged NDVI (no new information). Grass-Cast domain excludes most of our groups. Drop. |
| NMME (CanSIPS, GFDL) to 11.5 months | Seasonal ensembles that reach month 12 | IRI Data Library; **sunset notice: shutdown most likely by end of October 2026** (https://iri.columbia.edu/resources/data-library/sunset/). CPC NMME archive lists CFSv2, CMC1/2, GFDL, NASA, NCAR (https://ftp.cpc.ncep.noaa.gov/International/nmme/readme). | Not recommended for lead 12: model versions changed across our train/test years (CanCM3/4 -> CanSIPS-IC3 -> IC4), land precipitation skill at 11.5 months is near zero, and the main archive is closing. |

Change from the old report: NDVI_BASELINE_REPORT.md:63-65 excluded BARDL and the 2024 DNN because they read NDVI. Under the frozen protocol the engine itself reads NDVI history to issue-1 (plan.json history_columns hist_last_1..3, hist_mean_12/60/all). So a rival that reads NDVI to issue-1 is at parity and legitimate. The old exclusion is superseded for lagged NDVI. The target-month NDVI and its co-products stay banned.

## 3. H1: per-cell Bayesian ARDL (primary at 0 and 6; optional at 12)

- What: per unit, a Bayesian linear regression of the NDVI anomaly at month t on NDVI anomalies and climate anomalies known at the issue step. Direct (one model per lead), as BARDL does per horizon.
- Predictors at lead L (issue i = t-L):
  - NDVI anomaly at i-1, i-2, i-3 (BARDL's 3 lags; Barrett's AR order p=3).
  - Climate anomalies at i, i-1, i-2 and their 3-month mean: precipitation (V02_total_precip_mm), soil moisture (V30_soil_moisture_pct, ERA5-Land), and, as the one addition, VPD (V05_mean_vpd_kPa). All are "keep" in engine/datasets/ndvi/ban.yaml (lines 263, 275, 304, 517).
  - Calendar-month dummies are not needed: the target is already the anomaly.
- Anomaly base: the engine's per-unit calendar-month normal, from fit rows only (test_preds.parquet column normal). For climate, the per-unit calendar-month mean of rows up to the cut. Same cut as the engine: 2016 for the inner pass, 2019 for test.
- Fit: sklearn BayesianRidge (deterministic, installed) per unit and lead. No lag-order search on the test window. One pre-registered check on the inner window (fit 2003-2016, score 2017-2019) is printed and does not select anything. Final fit on all rows with target <= 2019.
- Calibration to target: none beyond the regression. It is fitted on train rows in the target's own units (NDVI anomaly; prediction = normal + anomaly). Clip to the legal range [-0.2, 1] and print the pre-clip rate, as the engine does. BARDL works on VCI. VCI is a per-cell, per-month linear rescaling of NDVI, so predicting the NDVI anomaly is the same model up to that scale. Disclose.
- Missing values (pre-register): a missing NDVI lag becomes anomaly 0 (the normal); a unit with fewer than 36 complete train rows falls back to the normal. Both are counted. Tundra and taiga winters are often NaN.
- Leak risks: low. Climate columns are TerraClimate and ERA5-Land, and neither assimilates NDVI. The one subtle risk: MOD13C2's 15-day reach (derived.json R17). Using exactly the engine's history offset closes it. Using NDVI at the issue month itself would be a leak.
- Data on disk: ALL of it. D:/monthly_panel: 2,926 files (133 groups x 2002-2023), 40.9 GB, 170 columns; V11_mean_ndvi, V02, V05, V30 present (checked thar_desert_monthly_2023.parquet). No download.
- Why it is the strongest legitimate rival: it holds the two things a human forecaster uses, vegetation memory and water memory. It nests persistence, damped persistence and the Barrett AR baseline.

## 4. Optional at lead 0: Kraft 2019 LSTM, re-run

- What: a global LSTM on 12-month windows of 6 climate drivers (V01, V02, V05, V30, solar_radiation_Wm2, V09) plus 6 soil/terrain statics; land cover dropped as a banned proxy (ndvi_kraft.py:67-68; D:/run89full/kraft_train.log).
- Standing: published research model, not operational. It reads no NDVI, so it is weaker in information than H1 and the engine. Its value is "a trained deep model", not "the human method".
- Lead 0 only: its window may end at t (the nowcast sees month-t climate). At leads 6 and 12 it needs forecast climate. Its honest arms (driver climatology, lag-12) were far below climatology before (anomaly R2 -0.376 and -0.562; NDVI_BASELINE_REPORT.md:143-144), so it is not worth running there.
- Redo design: one global model trained on all 133 groups' bank units, rows with target <= 2016; per-cell linear calibration fitted on 2017-2019 (out of sample for the LSTM, the same idea as ndvi_kraft.py:466-486); predict 2020-2023 on the 1,983 scored units. Temporal holdout is the parity condition, as for the engine's per-unit router. A region-blocked fold variant (about 5 folds by overlap block) is possible at about 5x the training cost.
- Data on disk: all inputs are in D:/monthly_panel (soil statics: clay_pct, sand_pct, soil_organic_carbon_gkg, soil_ph, awc_cm3cm3; V25_elevation_m). torch 2.8.0 is installed (CUDA available). Ruling Q14 (a), no GPU, is written for the common rivals (OWNER_RULINGS_2026-10-06.md:144); the owner should say whether it binds here. On CPU expect about 20-60 min of training.
- Outputs must NOT go to D:/run89full (it is in registry/protected_roots.txt).

## 5. Optional at lead 6: H1 + SEAS5 lead-month-6 anomalies

- What: H1 with 3 extra regressors, the SEAS5 ensemble-mean anomalies of precipitation, 2 m temperature and 2 m dewpoint (giving VPD) for month t, from the run initialised on the 1st of month t-5 (lead month 6).
- Source: CDS "seasonal-monthly-single-levels", ECMWF system 51 (https://cds.climate.copernicus.eu/datasets/seasonal-monthly-single-levels). 1 x 1 deg global; hindcasts from 1993, forecasts from 2017; GRIB (NetCDF on request); licence CC-BY (plus an extra licence only for non-European systems). System 51 is a relabelled, re-gridded SEAS5, not a new model (https://forum.ecmwf.int/t/changes-to-contribution-to-c3s-seasonal-forecast-systems-from-ecmwf/1539). Hindcasts have 25 members, forecasts 51; use the ensemble mean.
- Lead months: the C3S monthly product gives lead months 1-6 (stated from C3S documentation, not seen on the overview page). So lead 6 is covered and lead 12 is not.
- Information parity: init 00 UTC on the 1st of t-5 holds information to the end of month t-6, which is our issue step. Release is about 5 days later; the engine uses the same "information content" convention for TerraClimate. Disclose.
- Calibration (train rows only): anomaly against the system's own hindcast climatology for that start month and lead (C3S standard). Regression weights fitted on 2003-2019 rows.
- Leak risk: none from the target. Hindcasts were run after the fact with a frozen model; standard practice, disclose.
- OPEN, check at download: whether CDS serves system 51 real-time forecasts for 2017 to October 2022. If only system 5 exists there, use it (same model, half-degree grid shift) and disclose. Also the ensemble size jumps 25 to 51 between train and inner-score years.
- On disk: NOTHING for NDVI. D:/fire/cems holds CEMS fire-seasonal files only. D:/data/seasonal_climate holds observed seasonal aggregates (DJF/MAM/JJA/SON of V01, V02, V05, V30), not forecasts. A CDS client config exists (%USERPROFILE%\.cdsapirc; cdsapi installed; cfgrib/eccodes NOT installed, so request NetCDF). The owner must accept the dataset licence in the browser.
- Download size: lead month 6 only, 3 variables, inits Aug 2002 to Jun 2023: about 12,600 hindcast fields + about 12,900 forecast fields, about 3.3 GB GRIB global (about 6-7 GB NetCDF). About 21-25 requests (one per init year). Expected skill gain is small: only ENSO-linked regions, and the old oracle gap was already small (perfect precipitation and VPD worth 0.00206 MAE; NDVI_BASELINE_REPORT.md:200-201).

## 6. Old results and why they must be redone

| Old | Why it cannot be reused |
|---|---|
| Kraft and McPhillips (D:/run89full/kraft/, D:/run89full/mcphillips/; scores_3way_monthly.csv) | 44 regions scored, which were 25 test + 19 donor regions (NDVI_BASELINE_REPORT.md:5-14); old hard split with about 50% of cells, 4.4M rows, not the LORO 1,983 units x 48 months; only nowcast and 12-month tiers, no lead 6; Kraft trained on 13 regions it was scored on; NDVI history forbidden to rivals, which is stricter than today's parity. |
| BARDL / AR | Never run: excluded under the old reading of the proxy ban (NDVI_BASELINE_REPORT.md:63-65). |
| SEAS5 for NDVI | Never fetched. |

## 7. Work on this PC (15.8 GB RAM, HDD)

| Step | Download | Processing | Fitting | Notes |
|---|---|---|---|---|
| H1 data pull: 1,983 scored units, V11 + 4 drivers, 2002-2023 from 2,926 panel files | 0 | 0.5-1.5 h (HDD, column-pruned reads) | - | One pass serves all three leads |
| H1 fit + predict, 3 leads | 0 | - | 5-15 min | about 6,000 small BayesianRidge fits |
| H1 scoring through the harness | 0 | 10-20 min | - | Same metrics and region-paired contrasts |
| Kraft (optional, lead 0) | 0 | 1-2 h (sequences from 13,300 bank units) | 20-60 min CPU (5-10 min GPU); about 5x for region folds | Calibration about 10 min (old: 9.3 min, D:/run89full/kraft_calib.log) |
| SEAS5 (optional, lead 6) | 3-12 h wall (CDS queue), about 3.3 GB | about 1 h (NetCDF to 1,983 cell points, anomalies) | 5 min | Owner accepts the licence first |
| Code + toy tests | - | about 1 day of agent work | - | Outside the engine hash, like rivals_build |

Totals: primary only about 1-2 h machine. With Kraft: +2-4 h. With SEAS5: +1-2 h machine and +3-12 h queue. Grand total, everything: about 4-8 h machine plus queue time.

## 8. Decisions for the owner

1. Accept H1 (per-cell BARDL-style) as the primary NDVI human rival at leads 0 and 6? (recommended: yes)
2. Lead 12: report "no legitimate operational human rival; reference rows stand", and run H1 at h=12 as a labelled extension? (recommended: yes to both)
3. Kraft at lead 0: run it (global, temporal holdout) or leave it out? Does the no-GPU ruling apply?
4. SEAS5 at lead 6: download (about 3.3 GB, CDS licence) or leave it out?
5. VPD as a third climate predictor in H1 (BARDL used precipitation and soil moisture only): add it or keep the published two?
