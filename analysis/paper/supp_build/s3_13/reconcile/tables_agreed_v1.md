<!-- Draft tables of Supplement S3.13 (Tables S3.18 to S3.30) and of the main-text Table 9: the post hoc SHAP comparison of scope (i), the nowcast of each problem. Built from the stored values with one rounding step per printed number, by the rules of paper/supp_build/s3_13/spec/TABLE_SPEC.md; every printed number is listed in cells.json beside this file. Captions and notes are drafts: the text writers may polish the wording, never the numbers. Rulings AK (post hoc), BA1-BA3 and BB1-BB6 (engine/OWNER_RULINGS_2026-10-06.md). -->

## Main text: Table 9 (Section 5.4, Post hoc analyses)

**Table 9.** SHAP agreement between treeroute v1 and its rivals at the nowcast, variable level (post hoc). Computed after the test labels were opened, on a fixed sample of 1,000 test rows per problem; report-only, never deciding, and not headline results. Each model is explained in its own link space against a background of the same location's router fit rows of the same calendar month (forest loss, annual: all of them; coral bleaching: other sites' survey visits). Main set: treeroute v1 and its rivals that explain in its link and passed their skill guard. W: Kendall's W of the main set's rankings. Spearman: rank correlation over the union of two models' top-20 variables, here of treeroute v1 with each same-link rival. RBO: rank-biased overlap of treeroute v1's full ranking with the rivals' consensus (the mean of their shares). Own-history share: the share of a model's total mean absolute SHAP value that goes to the location's own lagged labels. Percentile 95% intervals over 2,000 paired bootstrap draws of regions. Every pair, at both levels: Supplement S3.13. <!-- src: D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/compare/AW4_main_row.json (every number but the two cells marked with a dagger); D:/treeroute/analysis/shap_v1/verify_v1/A/results.json problems.fire.main_row (the cells marked with a dagger, ruling BB1); pairs.parquet, importance.parquet and families.parquet for checks only; rulings AK, BA1, BB1, BB4 -->

| Problem | Main set | W [95% CI] | Spearman of treeroute v1 with its same-link rivals: median [95% CI] (range) | RBO with the rivals' consensus, p = 0.9 [95% CI] | treeroute v1's top 3 | Consensus top 3 | Own-history share, treeroute v1 [95% CI] | Own-history share, median of the rivalsᶜ [95% CI] |
|---|---|---|---|---|---|---|---|---|
| PM2.5 | treeroute v1, Ridge, random forest, LightGBM | 0.85 [0.85, 0.86] | −0.02 [−0.08, 0.07] (−0.12 to 0.08) | 0.37 [0.36, 0.57]ᵇ | `hist_last`, `spei`, `wbal` | `spi`, `sst_anom_global_tropical`, `hist_last` | 0.19 [0.16, 0.21] | 0.30 [0.28, 0.32] |
| NDVI | treeroute v1, Ridge, random forest, LightGBM, BARDL | 0.62 [0.61, 0.62] | 0.07 [−0.01, 0.12] (−0.41 to 0.38) | 0.40 [0.38, 0.43] | `hist_mean`, `hist_last`, `era5l_slhf` | `soil_moisture_pct`, `spi`, `hist_last` | 0.24 [0.22, 0.27] | 0.26 [0.24, 0.28] |
| Burned fraction | treeroute v1 onlyᵃ | undefined | – | – | `hist_mean`, `spei`, `tslf_months`† | – | 0.14 [0.11, 0.16]† | – |
| Forest loss | treeroute v1, Ridge, random forest, LightGBM | 0.80 [0.78, 0.81] | 0.20 [0.14, 0.29] (0.01 to 0.47) | 0.63 [0.61, 0.75] | `hist_last`, `h_nbr1`, `spei` | `hist_last`, `hist_mean`, `spi` | 0.29 [0.25, 0.33] | 0.35 [0.32, 0.40] |
| Coral bleaching | treeroute v1, random forest, LightGBM, absolute-error booster | 0.73 [0.69, 0.76] | 0.48 [0.39, 0.55] (0.41 to 0.49) | 0.67 [0.61, 0.78] | `nino34a`, `hs`, `dhw` | `n_above_mmm1`, `dhw`, `nino34a` | 0.00 [0.00, 0.00] (no own-history input) | 0.00 [0.00, 0.00] (no own-history input) |

ᵃ Burned fraction: every rival explains in another link (LightGBM, the random forest and Ridge in log(y + c), the Tweedie booster in log μ), and Ridge also failed its skill guard, so the main set is treeroute v1 alone. W needs two models and is undefined, and the cells that need a rival are empty (–): agreement between treeroute v1 and a rival cannot separate the link from the model there. The cross-link pairs are in Table S3.25.
ᵇ PM2.5: the interval of the RBO with the consensus is asymmetric because the consensus's top variable changes across the region draws.
ᶜ The median of the main-set rivals' own-history shares: on PM2.5 and forest loss LightGBM's share; on NDVI, with four rivals, the mean of the two middle shares.
† From the independent re-computation of the comparison (two implementations that agree): the comparison's output files leave these two cells empty, because they are written only when treeroute v1 has a same-link rival.

## Supplement S3.13: SHAP comparison of the main runs

**Table S3.18 (post hoc).** The models explained at the nowcast (a), and the rivals left out, with the reason (b). <!-- src: D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/compare/per_lead.json (models, links, main_set, declined_by_guard); D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/<model>/meta.json (guard.passed); D:/treeroute/analysis/shap_v1/PROTOCOL.md sections 5 and 7 and engine/PENDING_PARTS.md Part 628 (methods; rivals left out and why); rulings AW2, AY1, BA1 -->

**a. Explained models.**

| Problem | Model (data name) | Model and SHAP method | Link | Skill guard at the nowcast | In the main set |
|---|---|---|---|---|---|
| PM2.5 | treeroute v1 (`treeroute`) | the adopted arm: tree bank and router; exact interventional TreeSHAP of the trees, router terms exactly linear | log(y + c) | passed (the kept arm) | yes |
| PM2.5 | Ridge (`rival_ridge`) | ridge regression; exact linear SHAP | log(y + c) | passed | yes |
| PM2.5 | random forest (`rival_rf`) | random forest, rebuilt from the board's records; exact interventional TreeSHAP | log(y + c) | passed | yes |
| PM2.5 | LightGBM (`rival_lgbm`) | LightGBM; exact interventional TreeSHAP | log(y + c) | passed | yes |
| NDVI | treeroute v1 (`treeroute`) | the adopted arm: tree bank and router; exact interventional TreeSHAP of the trees, router terms exactly linear | identity | passed (the kept arm) | yes |
| NDVI | Ridge (`rival_ridge`) | ridge regression; exact linear SHAP | identity | passed | yes |
| NDVI | random forest (`rival_rf`) | random forest, rebuilt from the board's records; exact interventional TreeSHAP | identity | passed | yes |
| NDVI | LightGBM (`rival_lgbm`) | LightGBM; exact interventional TreeSHAP | identity | passed | yes |
| NDVI | BARDL (`rival_bardl_h1`) | published rain-lag Bayesian distributed-lag model, per location; exact linear SHAP over its nine input columns | identity | passed | yes |
| Burned fraction | treeroute v1 (`treeroute`) | the adopted arm: tree bank and router; exact interventional TreeSHAP of the trees, router terms exactly linear | arcsine | passed (the kept arm) | yes |
| Burned fraction | Ridge (`rival_ridge`) | ridge regression; exact linear SHAP | log(y + c) | failedᵃ | no: another link; skill guard failed |
| Burned fraction | random forest (`rival_rf`) | random forest, rebuilt from the board's records; exact interventional TreeSHAP | log(y + c) | passed | no: another link |
| Burned fraction | LightGBM (`rival_lgbm`) | LightGBM; exact interventional TreeSHAP | log(y + c) | passed | no: another link |
| Burned fraction | Tweedie booster (`rival_lgbm_tweedie`) | LightGBM with a Tweedie loss; exact interventional TreeSHAP | log μ | passed | no: another link |
| Forest loss | treeroute v1 (`treeroute`) | the adopted arm: tree bank and router; exact interventional TreeSHAP of the trees, router terms exactly linear | log(y + c) | passed (the kept arm) | yes |
| Forest loss | Ridge (`rival_ridge`) | ridge regression; exact linear SHAP | log(y + c) | passed | yes |
| Forest loss | random forest (`rival_rf`) | random forest, rebuilt from the board's records; exact interventional TreeSHAP | log(y + c) | passed | yes |
| Forest loss | LightGBM (`rival_lgbm`) | LightGBM; exact interventional TreeSHAP | log(y + c) | passed | yes |
| Forest loss | Tweedie booster (`rival_lgbm_tweedie`) | LightGBM with a Tweedie loss; exact interventional TreeSHAP | log μ | passed | no: another link |
| Coral bleaching | treeroute v1 (`treeroute`) | the adopted arm: tree bank and router; exact interventional TreeSHAP of the trees, router terms exactly linear | arcsine | passed (the kept arm) | yes |
| Coral bleaching | Ridge (`rival_ridge`) | ridge regression; exact linear SHAP | log(y + c) | passed | no: another link |
| Coral bleaching | random forest (`rival_rf`) | random forest, rebuilt from the board's records; exact interventional TreeSHAP | arcsine | passed | yes |
| Coral bleaching | LightGBM (`rival_lgbm`) | LightGBM; exact interventional TreeSHAP | arcsine | passed | yes |
| Coral bleaching | Tweedie booster (`rival_lgbm_tweedie`) | LightGBM with a Tweedie loss; exact interventional TreeSHAP | log μ | passed | no: another link |
| Coral bleaching | absolute-error booster (`rival_hgb_l1`) | gradient booster on absolute error; exact interventional TreeSHAP | arcsine | passed | yes |

**b. Rivals left out.**

| Problem | Rival | Why it has no SHAP value |
|---|---|---|
| PM2.5 | MERRA-2 PM2.5: lagged one month, same month, and the placebo entry | One-input calibration maps of the product, fitted per location: the attribution would be 100% on that one input. |
| PM2.5 | CAMS EAC4 | Never run: not obtained (ruling AG1). |
| NDVI | LSTM of Kraft et al. (2019) | Not bit-reproducible without its original deep-learning library, so left out until the owner rules (decision D7); its skill guard failed at the nowcast. |
| Burned fraction | The published rivals, among them the CEMS seasonal fire weather index forecast (SEAS5) | Never run (ruling AS). |
| Forest loss | VT0007, calibrated | One-input map (isotonic on anomalies): the attribution would be 100% on that one input. |
| Forest loss | VT0007, as shipped; VT0007, frozen at 2019 | Not a function of the rows' input columns: the index value as the product gives it. |
| Coral bleaching | NOAA Coral Reef Watch degree heating weeks (nowcast rule) | One-input map (isotonic on degree heating weeks): the attribution would be 100% on that one input. |
| Coral bleaching | CRW Outlook | One-input linear map on anomalies; it could instead be shown as a labelled reference row (decision D15, left at its default). |
| All five | The baselines: the seasonal normal, the last-5-years normal, predict-zero, persistence and damped persistence; on coral bleaching the training median and the last visit | No input feature: there is no SHAP value to compute. |

ᵃ Failed: the raw model is explained, labelled, and kept out of Kendall's W, the consensus and the main-text row (decision D6).
Links: identity; log(y + c), with c the problem's constant; log μ, the log of the Tweedie booster's mean; arcsine, the arcsine square root. Within each problem every model has the same c and upper bound, so two models are same-link exactly when their links are the same. The main set is treeroute v1 with its same-link rivals that passed their skill guard.

**Table S3.19 (post hoc).** The registered samples, their backgrounds and the active sets, nowcast. J: the players to which some model gives more than 10⁻¹² of its total mean absolute SHAP value; the others are structural zeros. <!-- src: D:/treeroute/analysis/shap_v1/SAMPLE_REGISTER.txt (n, sample); D:/treeroute/analysis/shap_v1/sample/<problem>/sample_manifest.json (frame_rows, regions_in_sample, units_in_sample, background_rows); D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/treeroute/meta.json (pairs); D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/compare/per_lead.json (players, active, structural_zero) -->

| Problem | Frame rowsᵃ | Sample rows | Regions | Locationsᵇ | Background rows per sample rowᶜ | Background pairs | Feature level: players / J / structural zeros | Variable level: players / J / structural zeros |
|---|---|---|---|---|---|---|---|---|
| PM2.5 | 91,428 | 1,000 | 127 | 254 | 17 | 17,000 | 125 / 103 / 22 | 111 / 89 / 22 |
| NDVI | 94,527 | 1,000 | 133 | 266 | 16–17 (median 17) | 16,914 | 503 / 479 / 24 | 117 / 96 / 21 |
| Burned fraction | 94,702 | 1,000 | 40 | 280 | 2–16 (median 16) | 15,759 | 134 / 111 / 23 | 117 / 94 / 23 |
| Forest loss | 369,096 | 1,000 | 42 | 252 | 16 | 16,000 | 309 / 280 / 29 | 121 / 99 / 22 |
| Coral bleaching | 2,312 | 1,000 | 37 | 1,000 | 50 | 50,000 | 69 / 68 / 1 | 26 / 25 / 1 |

ᵃ Frame: the labelled test rows that every compared model covers; the sample is drawn from it, stratified by region and test year.
ᵇ Coral bleaching: a location is a survey visit.
ᶜ Background (B2): the same location's router fit rows of the sample row's calendar month at or before the cut (forest loss, annual: all of them); coral bleaching: the visit's saved pool of other sites' visits. Shown as the lowest to highest number per sample row, with the median.
Structural zeros (exactly 0 in every model at that level, so outside J):
PM2.5: variable level (22) `CTI`, `awc_cm3cm3`, `bulk_density_gcm3`, `calendar`, `cec_cmolkg`, `clay_pct`, `coarse_fragments_pct`, `ctx:lat`, `dist_to_coast_km`, `elevation_m`, `hand_m`, `irrigation_pct_gmia`, `nitrogen_gkg`, `normal`, `sand_pct`, `silt_pct`, `slope_deg`, `soil_organic_carbon_gkg`, `soil_ph`, `southness`, `travel_time`, `upstream_area_km2`; feature level (22) `c__ctx:lat`, `c__ctx:month`, `normal`, `x__V25_elevation_m`, `x__V26_slope_deg`, `x__V27_southness`, `x__V28_CTI`, `x__awc_cm3cm3`, `x__bulk_density_gcm3`, `x__cec_cmolkg`, `x__clay_pct`, `x__coarse_fragments_pct`, `x__dist_to_coast_km`, `x__hand_m`, `x__irrigation_pct_gmia`, `x__nitrogen_gkg`, `x__sand_pct`, `x__silt_pct`, `x__soil_organic_carbon_gkg`, `x__soil_ph`, `x__travel_time`, `x__upstream_area_km2`.
NDVI: variable level (21) `CTI`, `awc_cm3cm3`, `bulk_density_gcm3`, `calendar`, `cec_cmolkg`, `clay_pct`, `coarse_fragments_pct`, `dist_to_coast_km`, `elevation_m`, `hand_m`, `irrigation_pct_gmia`, `nitrogen_gkg`, `normal`, `sand_pct`, `silt_pct`, `slope_deg`, `soil_organic_carbon_gkg`, `soil_ph`, `southness`, `travel_time`, `upstream_area_km2`; feature level (24) `c__ctx:cos1`, `c__ctx:cos2`, `c__ctx:sin1`, `c__ctx:sin2`, `normal`, `x__V25_elevation_m`, `x__V26_slope_deg`, `x__V27_southness`, `x__V28_CTI`, `x__awc_cm3cm3`, `x__bulk_density_gcm3`, `x__cec_cmolkg`, `x__clay_pct`, `x__coarse_fragments_pct`, `x__dist_to_coast_km`, `x__hand_m`, `x__irrigation_pct_gmia`, `x__nitrogen_gkg`, `x__sand_pct`, `x__silt_pct`, `x__soil_organic_carbon_gkg`, `x__soil_ph`, `x__travel_time`, `x__upstream_area_km2`.
Burned fraction: variable level (23) `CTI`, `awc_cm3cm3`, `bulk_density_gcm3`, `calendar`, `cec_cmolkg`, `clay_pct`, `coarse_fragments_pct`, `conflict_deaths`, `conflict_events`, `ctx:lat`, `dist_to_coast_km`, `elevation_m`, `hand_m`, `irrigation_pct_gmia`, `nitrogen_gkg`, `normal`, `sand_pct`, `silt_pct`, `slope_deg`, `soil_organic_carbon_gkg`, `soil_ph`, `southness`, `upstream_area_km2`; feature level (23) `c__ctx:lat`, `c__ctx:month`, `normal`, `x__V25_elevation_m`, `x__V26_slope_deg`, `x__V27_southness`, `x__V28_CTI`, `x__awc_cm3cm3`, `x__bulk_density_gcm3`, `x__cec_cmolkg`, `x__clay_pct`, `x__coarse_fragments_pct`, `x__conflict_deaths`, `x__conflict_events`, `x__dist_to_coast_km`, `x__hand_m`, `x__irrigation_pct_gmia`, `x__nitrogen_gkg`, `x__sand_pct`, `x__silt_pct`, `x__soil_organic_carbon_gkg`, `x__soil_ph`, `x__upstream_area_km2`.
Forest loss: variable level (22) `CTI`, `awc_cm3cm3`, `bulk_density_gcm3`, `cec_cmolkg`, `clay_pct`, `coarse_fragments_pct`, `conflict_deaths`, `conflict_events`, `dist_to_coast_km`, `elevation_m`, `hand_m`, `irrigation_pct_gmia`, `nitrogen_gkg`, `normal`, `sand_pct`, `silt_pct`, `slope_deg`, `soil_organic_carbon_gkg`, `soil_ph`, `southness`, `travel_time`, `upstream_area_km2`; feature level (29) `normal`, `x__V20_burned_binary_min`, `x__V25_elevation_m`, `x__V26_slope_deg`, `x__V27_southness`, `x__V28_CTI`, `x__awc_cm3cm3`, `x__bulk_density_gcm3`, `x__cec_cmolkg`, `x__clay_pct`, `x__coarse_fragments_pct`, `x__conflict_deaths_max`, `x__conflict_deaths_mean`, `x__conflict_deaths_min`, `x__conflict_events_max`, `x__conflict_events_mean`, `x__conflict_events_min`, `x__dist_to_coast_km`, `x__hand_m`, `x__heatwave_days_gt35C_min`, `x__irrigation_pct_gmia`, `x__nitrogen_gkg`, `x__sand_pct`, `x__silt_pct`, `x__soil_organic_carbon_gkg`, `x__soil_ph`, `x__swe_mean_mm_min`, `x__travel_time`, `x__upstream_area_km2`.
Coral bleaching: variable level (1) `normal`; feature level (1) `normal`.

**Table S3.20 (post hoc).** Checks of every explained model, nowcast: the rebuild or reload reproduces the saved predictions (S-EXACT), the attributions add up to the model's output (S-ADD), its evaluator equals the model (S-EVAL), the unattributed part stays small (S-RESID), and a player that equals the explained row on every background row gets exactly 0 (S-ZERO). <!-- src: D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/<model>/exactness.json, ridge_shap_exactness.json (Ridge outside coral bleaching) and meta.json; D:/treeroute/analysis/shap_v1/rebuild/<problem>/lead_0/gates.json (treeroute v1, gate E8); D:/treeroute/analysis/shap_v1/PROTOCOL.md sections 4 and 11 -->

| Problem | Model | Rows checkedᵃ | Bit-identical rows, pre-clip / clippedᵃ | Largest absolute difference, rebuilt − saved (pre-clip, y units) | S-EXACT | Largest additivity error, feature / variable level | S-ZERO violations | S-ADD, S-EVAL, S-RESID, S-ZERO | Skill guard |
|---|---|---|---|---|---|---|---|---|---|
| PM2.5 | treeroute v1 | 12,192 | 12,192 / 12,192 | 0 | bit-identical | 6.2 × 10⁻¹⁵ / 6.2 × 10⁻¹⁵ | 0 | all passed | passed (the kept arm) |
| PM2.5 | Ridgeᵇ | 91,440 | 91,440 / 91,440 | 0 | bit-identical | 1.8 × 10⁻¹⁵ / 1.8 × 10⁻¹⁵ | 0 | all passed | passed |
| PM2.5 | random forest | 91,440 | 91,440 / – | 0 | bit-identical | 1.8 × 10⁻¹⁵ / 1.8 × 10⁻¹⁵ | 0 | all passed | passed |
| PM2.5 | LightGBM | 91,440 | 91,440 / – | 0 | bit-identical | 1.8 × 10⁻¹⁵ / 1.8 × 10⁻¹⁵ | 0 | all passed | passed |
| NDVI | treeroute v1 | 12,768 | 12,768 / 12,768 | 0 | bit-identical | 5.4 × 10⁻¹⁵ / 5.6 × 10⁻¹⁵ | 0 | all passed | passed (the kept arm) |
| NDVI | Ridgeᵇ | 95,184 | 95,184 / 95,184 | 0 | bit-identical | 4.4 × 10⁻¹⁶ / 4.4 × 10⁻¹⁶ | 0 | all passed | passed |
| NDVI | random forest | 95,184 | 95,184 / – | 0 | bit-identical | 3.3 × 10⁻¹⁶ / 3.3 × 10⁻¹⁶ | 0 | all passed | passed |
| NDVI | LightGBM | 95,184 | 95,184 / – | 0 | bit-identical | 3.6 × 10⁻¹⁶ / 3.6 × 10⁻¹⁶ | 0 | all passed | passed |
| NDVI | BARDL | 95,184 | 95,184 / 95,184 | 0 | bit-identical | 3.3 × 10⁻¹⁶ / 3.3 × 10⁻¹⁶ | 0 | all passed | passed |
| Burned fraction | treeroute v1 | 13,440 | 13,056 / 13,056 | 5.0 × 10⁻¹⁶ | within the D8 toleranceᶜ (largest relative difference 2.4 × 10⁻¹³) | 2.2 × 10⁻¹⁶ / 2.2 × 10⁻¹⁶ | 0 | all passed | passed (the kept arm) |
| Burned fraction | Ridgeᵇ | 96,000 | 96,000 / 96,000 | 0 | bit-identical | 1.8 × 10⁻¹⁵ / 1.8 × 10⁻¹⁵ | 0 | all passed | failedᵈ |
| Burned fraction | random forest | 96,000 | 96,000 / – | 0 | bit-identical | 1.8 × 10⁻¹⁵ / 1.8 × 10⁻¹⁵ | 0 | all passed | passed |
| Burned fraction | LightGBM | 96,000 | 96,000 / – | 0 | bit-identical | 1.8 × 10⁻¹⁵ / 1.8 × 10⁻¹⁵ | 0 | all passed | passed |
| Burned fraction | Tweedie booster | 96,000 | 96,000 / – | 0 | bit-identical | 9.2 × 10⁻¹⁴ / 8.5 × 10⁻¹⁴ | 0 | all passed | passed |
| Forest loss | treeroute v1 | 1,008 | 1,008 / 1,008 | 0 | bit-identical | 8.9 × 10⁻¹⁵ / 8.9 × 10⁻¹⁵ | 0 | all passed | passed (the kept arm) |
| Forest loss | Ridgeᵇ | 369,096 | 369,096 / 369,096 | 0 | bit-identical | 3.6 × 10⁻¹⁵ / 3.6 × 10⁻¹⁵ | 0 | all passed | passed |
| Forest loss | random forest | 369,096 | 369,096 / – | 0 | bit-identical | 5.3 × 10⁻¹⁵ / 5.3 × 10⁻¹⁵ | 0 | all passed | passed |
| Forest loss | LightGBM | 369,096 | 369,096 / – | 0 | bit-identical | 3.6 × 10⁻¹⁵ / 3.6 × 10⁻¹⁵ | 0 | all passed | passed |
| Forest loss | Tweedie booster | 369,096 | 369,096 / – | 0 | bit-identical | 6.0 × 10⁻¹⁴ / 6.0 × 10⁻¹⁴ | 0 | all passed | passed |
| Coral bleaching | treeroute v1 | 2,312 | 2,228 / 2,228 | 2.1 × 10⁻¹⁴ | within the D8 toleranceᶜ (largest relative difference 1.1 × 10⁻¹⁵) | 3.7 × 10⁻¹⁵ / 4.1 × 10⁻¹⁵ | 0 | all passed | passed (the kept arm) |
| Coral bleaching | Ridge | 2,312 | 2,312 / – | 0 | bit-identical | 1.0 × 10⁻¹⁴ / 9.0 × 10⁻¹⁵ | 0 | all passed | passed |
| Coral bleaching | random forest | 2,312 | 2,312 / – | 0 | bit-identical | 2.2 × 10⁻¹⁶ / 3.3 × 10⁻¹⁶ | 0 | all passed | passed |
| Coral bleaching | LightGBM | 2,312 | 2,312 / – | 0 | bit-identical | 5.6 × 10⁻¹⁶ / 4.4 × 10⁻¹⁶ | 0 | all passed | passed |
| Coral bleaching | Tweedie booster | 2,312 | 2,312 / – | 0 | bit-identical | 8.9 × 10⁻¹⁵ / 9.8 × 10⁻¹⁵ | 0 | all passed | passed |
| Coral bleaching | absolute-error booster | 2,312 | 2,312 / – | 0 | bit-identical | 2.2 × 10⁻¹⁵ / 2.0 × 10⁻¹⁵ | 0 | all passed | passed |

ᵃ Rows checked: every test row of the rival's saved predictions; for treeroute v1, every test row of every sampled location (coral bleaching: every test survey visit). Pre-clip: the prediction before the declared bounds are applied; clipped: after. The comparison script checks a rival's pre-clip column only (–: not read).
ᵇ Ridge outside coral bleaching is explained by a loader that repeats the rival board's own block-wise scoring, which reproduces every saved prediction. The comparison script's own check of its row-by-row copy of the design, kept as a record, matched 70,795 of 91,440 rows on PM2.5, 17,451 of 95,184 on NDVI, 95,711 of 96,000 on burned fraction and 303,967 of 369,096 on forest loss, because that copy adds the same terms in another order.
ᶜ D8: on the arcsine arms of burned fraction and coral bleaching the owner allowed a relative difference of at most 10⁻¹² (ruling AY3), licensed by the bit-identical identity-link twin (gate E5a, Table S3.21).
ᵈ Failed: the raw model is explained, labelled, and kept out of Kendall's W, the consensus and the main-text row (decision D6).

**Table S3.21 (post hoc).** treeroute v1's rebuild gates, nowcast, in the order they run. The fitted trees were not kept, so each problem's tree bank and the sampled locations' routers were rebuilt with the run's own engine code; a failed gate stops the problem, except E5, which is informational. <!-- src: D:/treeroute/analysis/shap_v1/rebuild/<problem>/lead_0/gates.json (result; gates.<gate>.pass and .values); D:/treeroute/analysis/shap_v1/PROTOCOL.md sections 4.1 and 11; rulings AY2 (path map, gate E3m) and AY3 (D8) -->

| Gate | What it checks | PM2.5 | NDVI | Burned fraction | Forest loss | Coral bleaching |
|---|---|---|---|---|---|---|
| Kept arm | link, answer type and weighting; router type | log(y + c), corrected answers, uniformly weighted; per-location router | identity, plain answers, uniformly weighted; per-location router | arcsine, corrected answers, error-weighted; per-location router | log(y + c), corrected answers, uniformly weighted; region router | arcsine, corrected answers, error-weighted; neighbour router |
| E1 | engine code hash equals the run manifest's | passed | passed | passed | passed | passed |
| E2 | library versions and Python equal the manifest's | passed | passed | passed | passed | passed |
| E0 | the engine's RAM pre-flight predicts no refusal | passed | passed | passed (warning overridden) | passed | passed |
| E3a | inputs before the read equal the manifest's (package, groups, constants, file lists, features) | passed | passed | passed | passed | passed |
| E3m | a moved package file has the content, size and time that the freeze locks record (path map) | passed (1 file) | passed (1 file) | passed (1 file) | not used (no moved file) | not used (no moved file) |
| E3 | package fingerprint, derived settings and run fingerprint after the derive | passed | passed | passed | passed | passed |
| E4 | training rows: count and row-key hash | passed (2,590,280 rows) | passed (2,680,841 rows) | passed (751,508 rows) | passed (3,011,184 rows) | passed (11,338 rows) |
| E5ᵃ | bank fingerprint over every tree array (informational) | differs (informational) | differs (informational) | differs (informational) | differs (informational) | differs (informational) |
| E5a | arcsine arm only: its identity-link twin is bit-identical on every checked row | not applicable | not applicable | passed (13,440 of 13,440 rows) | not applicable | passed (2,312 of 2,312 rows) |
| E6 | c and the guard tolerances equal the run's records | passed | passed | passed | passed | passed |
| E7 | error-weighted arm only: the error-weight model equals its record | not applicable | not applicable | passed | not applicable | passed |
| E9 | captured router coefficients reproduce the engine's kernel bit for bit | passed (all 254 fits) | passed (all 266 fits) | passed (all 280 fits) | passed (all 42 region fits; region proof on 1,008 score rows and 4,032 background rows) | passed (all 2,312 fits) |
| E8 | kept predictions, pre-clip and clipped, on every test row of every sampled location | bit-identical (12,192 of 12,192 rows) | bit-identical (12,768 of 12,768 rows) | 13,056 of 13,440 rows bit-identical; the rest within the D8 tolerance (largest relative difference 2.4 × 10⁻¹³) | bit-identical (1,008 of 1,008 rows) | 2,228 of 2,312 rows bit-identical; the rest within the D8 tolerance (largest relative difference 1.1 × 10⁻¹⁵) |
| E10 | exported trees and evaluator reproduce the engine's tree answers bit for bit | passed (252 rows, 12,600 trees) | passed (251 rows, 13,200 trees) | passed (215 rows, 3,900 trees) | passed (every sampled location of the 42 regions) | passed (51 rows, 7,700 trees) |

ᵃ E5 is informational: the rebuilt bank's fingerprint differs from the run's on all five problems, while every checked prediction matches (E5a, E8, E10); the cause is not established.
D8 (gate E8 on burned fraction and coral bleaching): a relative difference of at most 10⁻¹² on arcsine arms only (ruling AY3), licensed at this lead by gate E5a.

**Table S3.22 (post hoc).** The main-text row (Table 9) with its components, nowcast, variable level. From the comparison's output files, except the cells marked †. <!-- src: D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/compare/AW4_main_row.json; pairs.parquet (spearman_top20_union of treeroute v1 with each same-link rival); families.parquet (each same-link rival's own-history share); D:/treeroute/analysis/shap_v1/verify_v1/A/results.json problems.fire.main_row (the cells marked with a dagger, ruling BB1); rulings BB1, BB4, BB6 -->

| Quantity | PM2.5 | NDVI | Burned fraction | Forest loss | Coral bleachingᵈ |
|---|---|---|---|---|---|
| Link of the main set | log(y + c) | identity | arcsine | log(y + c) | arcsine |
| Main set | treeroute v1, Ridge, random forest, LightGBM | treeroute v1, Ridge, random forest, LightGBM, BARDL | treeroute v1 onlyᵃ | treeroute v1, Ridge, random forest, LightGBM | treeroute v1, random forest, LightGBM, absolute-error booster |
| Rivals in another link | none | none | random forest, LightGBM, Tweedie booster | Tweedie booster | Ridge, Tweedie booster |
| Rivals declined by their skill guard | none | none | Ridge | none | none |
| Kendall's W of the main set [95% CI] | 0.85 [0.85, 0.86] | 0.62 [0.61, 0.62] | undefined | 0.80 [0.78, 0.81] | 0.73 [0.69, 0.76] |
| Spearman of treeroute v1 with each same-link rival | Ridge −0.12; random forest −0.02; LightGBM 0.08 | Ridge −0.41; random forest −0.02; LightGBM 0.16; BARDL 0.38 | – | Ridge 0.01; random forest 0.20; LightGBM 0.47 | random forest 0.49; LightGBM 0.41; absolute-error booster 0.48 |
| Median of those [95% CI] | −0.02 [−0.08, 0.07] | 0.07 [−0.01, 0.12] | – | 0.20 [0.14, 0.29] | 0.48 [0.39, 0.55] |
| Range (lowest to highest) | −0.12 to 0.08 | −0.41 to 0.38 | – | 0.01 to 0.47 | 0.41 to 0.49 |
| RBO with the rivals' consensus, p = 0.9 [95% CI] | 0.37 [0.36, 0.57]ᵇ | 0.40 [0.38, 0.43] | – | 0.63 [0.61, 0.75] | 0.67 [0.61, 0.78] |
| treeroute v1's top 3 | `hist_last`, `spei`, `wbal` | `hist_mean`, `hist_last`, `era5l_slhf` | `hist_mean`, `spei`, `tslf_months`† | `hist_last`, `h_nbr1`, `spei` | `nino34a`, `hs`, `dhw` |
| Consensus top 3 | `spi`, `sst_anom_global_tropical`, `hist_last` | `soil_moisture_pct`, `spi`, `hist_last` | – | `hist_last`, `hist_mean`, `spi` | `n_above_mmm1`, `dhw`, `nino34a` |
| Own-history share, treeroute v1 [95% CI] | 0.19 [0.16, 0.21] | 0.24 [0.22, 0.27] | 0.14 [0.11, 0.16]† | 0.29 [0.25, 0.33] | 0.00 [0.00, 0.00] (no own-history input) |
| Own-history share of each same-link rival | Ridge 0.38; random forest 0.25; LightGBM 0.30 | Ridge 0.26; random forest 0.04; LightGBM 0.25; BARDL 0.35 | – | Ridge 0.12; random forest 0.37; LightGBM 0.35 | random forest 0.00; LightGBM 0.00; absolute-error booster 0.00 (no own-history input) |
| Own-history share, median of the rivalsᶜ [95% CI] | 0.30 [0.28, 0.32] | 0.26 [0.24, 0.28] | – | 0.35 [0.32, 0.40] | 0.00 [0.00, 0.00] (no own-history input) |

ᵃ Burned fraction: every rival explains in another link (LightGBM, the random forest and Ridge in log(y + c), the Tweedie booster in log μ), and Ridge also failed its skill guard, so the main set is treeroute v1 alone. W needs two models and is undefined, and the cells that need a rival are empty (–): agreement between treeroute v1 and a rival cannot separate the link from the model there.
ᵇ PM2.5: the interval of the RBO with the consensus is asymmetric because the consensus's top variable changes across the region draws.
ᶜ The median of the main-set rivals' own-history shares: on PM2.5 and forest loss LightGBM's share; on NDVI, with four rivals, the mean of the two middle shares.
ᵈ Coral bleaching's table of these statistics (AW4_table.md, written on 2026-11-13 at 00:06) was read by an agent on 2026-11-13 at about 15:31, before the independent re-computation; the re-computation's implementers A and B never opened it (ruling BB6).
† From the independent re-computation of the comparison (two implementations that agree): the comparison's output files leave these cells empty, because they are written only when treeroute v1 has a same-link rival (ruling BB1).

**Table S3.23 (post hoc).** PM2.5, nowcast: agreement of the models' SHAP attributions, every pair at the variable level (a) and at the feature level (b); the main set's agreement and each model's stability (c); each model's top 10 at both levels (d, e) and its family shares (f). Link space. Percentile 95% intervals over 2,000 paired region draws, with the number of finite draws where a statistic is defined on fewer of them. Same-link pairs are comparable; cross-link pairs are shown for completeness and are not comparable in scale or rank. Shares are of a model's total mean absolute SHAP value over J, without intervals, as in the comparison's files. <!-- src: D:/treeroute/analysis/shap_v1/out/pm25/lead_0/compare/pairs.parquet, per_lead.json, importance.parquet and families.parquet; D:/treeroute/analysis/shap_v1/verify_v1/A/results.json problems.pm25.levels.<level>.pairs (the sign agreement's intervals, ruling BB1); rulings BB1, BB2, BB5 -->

**a. Variable level: every pair.**

| Pair | Link | Spearman over J | Spearman, top-20 union | Kendall's tau-b | Jaccard top 5 | Jaccard top 10 | RBO, p = 0.9 | RBO, p = 0.95 | Share distance (TV) | Family-share distance (TV) | Sign agreement, top-10 union (signs)† |
|---|---|---|---|---|---|---|---|---|---|---|---|
| treeroute v1 vs Ridge | same-link | 0.69 [0.67, 0.72] | −0.12 [−0.17, −0.02] | 0.50 [0.48, 0.52] | 0.00 [0.00, 0.25] | 0.25 [0.25, 0.25] | 0.26 [0.24, 0.34] | 0.41 [0.40, 0.46] | 0.49 [0.48, 0.50] | 0.29 [0.26, 0.32] | 1.00 [0.75, 1.00] (4 signs) |
| treeroute v1 vs random forest | same-link | 0.85 [0.83, 0.86] | −0.02 [−0.08, 0.07] | 0.68 [0.65, 0.69] | 0.25 [0.11, 0.43] | 0.25 [0.25, 0.25] | 0.42 [0.39, 0.54] | 0.53 [0.50, 0.60] | 0.36 [0.34, 0.37] | 0.15 [0.12, 0.18] | 1.00 [0.80, 1.00] (5 signs) |
| treeroute v1 vs LightGBM | same-link | 0.85 [0.83, 0.87] | 0.08 [0.01, 0.19] | 0.68 [0.65, 0.70] | 0.11 [0.11, 0.43] | 0.33 [0.25, 0.43] | 0.53 [0.50, 0.64] | 0.60 [0.58, 0.66] | 0.24 [0.23, 0.25] | 0.18 [0.15, 0.20] | 0.80 [0.67, 1.00] (5 signs) |
| Ridge vs random forest | same-link | 0.73 [0.71, 0.75] | 0.21 [0.15, 0.28] | 0.55 [0.53, 0.56] | 0.25 [0.25, 0.25] | 0.33 [0.33, 0.33] | 0.40 [0.37, 0.41] | 0.52 [0.51, 0.53] | 0.43 [0.42, 0.45] | 0.14 [0.11, 0.18] | 0.78 [0.78, 0.80] (9 signs) |
| Ridge vs LightGBM | same-link | 0.73 [0.72, 0.75] | 0.14 [0.11, 0.23] | 0.54 [0.52, 0.55] | 0.11 [0.11, 0.25] | 0.33 [0.25, 0.33] | 0.37 [0.36, 0.44] | 0.51 [0.50, 0.55] | 0.41 [0.41, 0.42] | 0.11 [0.08, 0.15] | 0.67 [0.67, 0.78] (9 signs) |
| random forest vs LightGBM | same-link | 0.98 [0.97, 0.98] | 0.69 [0.59, 0.74] | 0.87 [0.85, 0.87] | 0.25 [0.25, 0.43] | 0.67 [0.54, 0.67] | 0.66 [0.60, 0.75] | 0.76 [0.73, 0.81] | 0.22 [0.21, 0.23] | 0.05 [0.03, 0.07] | 1.00 [1.00, 1.00] (8 signs) |

**b. Feature level: every pair.**

| Pair | Link | Spearman over J | Spearman, top-20 union | Kendall's tau-b | Jaccard top 5 | Jaccard top 10 | RBO, p = 0.9 | RBO, p = 0.95 | Share distance (TV) | Family-share distance (TV)§ | Sign agreement, top-10 union (signs)† |
|---|---|---|---|---|---|---|---|---|---|---|---|
| treeroute v1 vs Ridge | same-link | 0.61 [0.59, 0.63] | −0.43 [−0.48, −0.34] | 0.43 [0.41, 0.45] | 0.11 [0.00, 0.11] | 0.11 [0.11, 0.18] | 0.16 [0.15, 0.21] | 0.30 [0.29, 0.33] | 0.50 [0.49, 0.51] | 0.29 [0.26, 0.32] | 0.71 [0.71, 0.86] (7 signs) |
| treeroute v1 vs random forest | same-link | 0.78 [0.75, 0.80] | −0.31 [−0.37, −0.22] | 0.60 [0.58, 0.62] | 0.11 [0.11, 0.25] | 0.11 [0.11, 0.18] | 0.42 [0.40, 0.45] | 0.48 [0.46, 0.51] | 0.35 [0.34, 0.37] | 0.15 [0.12, 0.18] | 1.00 [0.75, 1.00] (4 signs) |
| treeroute v1 vs LightGBM | same-link | 0.78 [0.75, 0.80] | −0.26 [−0.34, −0.16] | 0.61 [0.58, 0.63] | 0.11 [0.11, 0.25] | 0.11 [0.11, 0.18] | 0.42 [0.33, 0.46] | 0.48 [0.44, 0.51] | 0.25 [0.24, 0.26] | 0.18 [0.15, 0.20] | 0.83 [0.67, 1.00] (6 signs) |
| Ridge vs random forest | same-link | 0.70 [0.69, 0.72] | −0.05 [−0.10, −0.02] | 0.51 [0.50, 0.53] | 0.11 [0.11, 0.11] | 0.18 [0.18, 0.18] | 0.30 [0.28, 0.32] | 0.44 [0.42, 0.45] | 0.45 [0.44, 0.46] | 0.14 [0.11, 0.18] | 0.82 [0.73, 0.83] (11 signs) |
| Ridge vs LightGBM | same-link | 0.73 [0.71, 0.74] | −0.02 [−0.08, 0.05] | 0.53 [0.52, 0.54] | 0.00 [0.00, 0.11] | 0.18 [0.11, 0.25] | 0.25 [0.23, 0.31] | 0.42 [0.40, 0.45] | 0.40 [0.40, 0.41] | 0.11 [0.08, 0.15] | 0.73 [0.73, 0.82] (11 signs) |
| random forest vs LightGBM | same-link | 0.96 [0.96, 0.97] | 0.51 [0.45, 0.61] | 0.84 [0.83, 0.85] | 0.25 [0.11, 0.43] | 0.67 [0.54, 0.67] | 0.65 [0.55, 0.71] | 0.73 [0.68, 0.76] | 0.23 [0.22, 0.24] | 0.05 [0.03, 0.07] | 1.00 [1.00, 1.00] (8 signs) |

**c. Agreement within the main set, and each model's stability.**

| Statistic | Variable level | Feature level |
|---|---|---|
| Kendall's W of the main set [95% CI] | 0.85 [0.85, 0.86] | 0.82 [0.81, 0.83] |
| Mean pairwise Spearman of the main set [95% CI] | 0.81 [0.80, 0.82] | 0.76 [0.75, 0.77] |
| Stability under region resampling: treeroute v1 | 0.99 | 0.99 |
| Stability under region resampling: Ridge | 1.00 | 1.00 |
| Stability under region resampling: random forest | 1.00 | 1.00 |
| Stability under region resampling: LightGBM | 1.00 | 1.00 |

**d. Variable level: each model's top 10 (share).**

| Rank | treeroute v1 | Ridge | Random forest | LightGBM |
|---|---|---|---|---|
| 1 | `hist_last` 5.0% | `sst_anom_global_tropical` 14.8% | `spi` 12.8% | `hist_last` 7.1% |
| 2 | `spei` 3.3% | `hist_mean` 10.4% | `hist_last` 11.6% | `spi` 5.9% |
| 3 | `wbal` 3.2% | `nino12` 7.2% | `sst_anom_global_tropical` 6.5% | `hist_mean` 5.5% |
| 4 | `era5l_str` 3.2% | `pdo` 7.2% | `nino4` 5.6% | `sst_anom_atl3` 3.4% |
| 5 | `sst_anom_mediterranean` 3.1% | `nino4` 6.5% | `sst_anom_mediterranean` 4.6% | `hdi` 3.2% |
| 6 | `spi` 3.1% | `spi` 5.7% | `sst_anom_iod_west` 4.1% | `sst_anom_mediterranean` 3.1% |
| 7 | `pdo` 3.0% | `hist_last` 4.6% | `spei` 3.2% | `sst_anom_coral_sea` 3.0% |
| 8 | `hist_mean` 2.7% | `tni` 3.9% | `sst_anom_atl3` 3.2% | `spei` 3.0% |
| 9 | `tna` 2.5% | `nino3` 3.7% | `sst_anom_coral_sea` 2.8% | `nino4` 2.9% |
| 10 | `era5l_sshf` 2.1% | `sst_anom_iod_west` 2.9% | `sst_anom_subpolar_north_atlantic` 2.7% | `sst_anom_iod_west` 2.8% |
| Nonzero variables | 88 | 89 | 87 | 87 |

**e. Feature level: each model's top 10 (share).**

| Rank | treeroute v1 | Ridge | Random forest | LightGBM |
|---|---|---|---|---|
| 1 | `x__hist_last_1` 4.0% | `x__sst_anom_global_tropical_mean` 12.1% | `x__hist_last_1` 10.0% | `x__hist_last_1` 5.9% |
| 2 | `x__era5l_str` 2.9% | `x__hist_mean_60` 7.2% | `x__spi_03m` 8.1% | `x__hist_mean_12` 5.2% |
| 3 | `x__sst_anom_mediterranean` 2.9% | `x__hist_mean_all` 6.3% | `x__sst_anom_global_tropical_mean` 5.9% | `x__sst_anom_atl3` 3.0% |
| 4 | `x__pdo` 2.8% | `x__nino12` 5.9% | `x__nino4` 5.2% | `x__hdi` 2.8% |
| 5 | `x__tna` 2.4% | `x__pdo` 5.9% | `x__spi_01m` 4.3% | `x__spi_03m` 2.7% |
| 6 | `x__wbal_roll3` 2.3% | `x__hist_mean_12` 5.5% | `x__sst_anom_mediterranean` 4.2% | `x__sst_anom_mediterranean` 2.7% |
| 7 | `x__era5l_sshf` 2.0% | `x__nino4` 5.3% | `x__sst_anom_iod_west` 3.8% | `x__spi_01m` 2.7% |
| 8 | `x__amo_lag12` 1.9% | `x__hist_last_1` 4.0% | `x__sst_anom_atl3` 3.0% | `x__sst_anom_coral_sea` 2.7% |
| 9 | `x__deeprec_twsa` 1.9% | `x__tni` 3.2% | `x__sst_anom_subpolar_north_atlantic` 2.5% | `x__nino4` 2.6% |
| 10 | `x__climate_water_deficit_mm` 1.9% | `x__nino3` 3.0% | `x__sst_anom_coral_sea` 2.5% | `x__sst_anom_iod_west` 2.5% |
| Nonzero players | 102 | 103 | 101 | 101 |

**f. Family shares (sums of the variable-level attributions per row).**

| Family | treeroute v1 | Ridge | Random forest | LightGBM |
|---|---|---|---|---|
| Own history | 18.5% | 38.2% | 25.2% | 29.8% |
| Global indices | 32.2% | 41.3% | 40.8% | 38.9% |
| Local drivers | 49.2% | 20.5% | 34.0% | 31.3% |
| Context and calendar | 0.0% | 0.0% | 0.0% | 0.0% |
| Seasonal normal | 0.0% | 0.0% | 0.0% | 0.0% |

Sign agreement: of the players in the union of the two top-10 sets whose sign is determined in both models (the bootstrap 95% interval of the signed mean excludes 0), the share whose signs agree; in brackets, the number of such players ("signs") and, where fewer than 2,000, the number of draws on which the statistic is defined. Undefined: no player qualifies on the full sample.
† The sign agreement's interval is from the independent re-computation of the comparison (two implementations, A and B, that agree; ruling BB1): the comparison script evaluates the sign agreement on the full sample only, so its files hold no interval. The value and its number of signs are the comparison's.
§ Families are sums of variable-level attributions, so at the feature level the family-share distance is the variable-level value repeated (ruling BB2).
Stability (panel c): the mean Spearman of a model's full-sample importances with its own bootstrap replicates; descriptive, not a ceiling on between-model agreement. Nonzero (panels d and e): the players of J to which the model gives a nonzero share.

**Table S3.24 (post hoc).** NDVI, nowcast: agreement of the models' SHAP attributions, every pair at the variable level (a) and at the feature level (b); the main set's agreement and each model's stability (c); each model's top 10 at both levels (d, e) and its family shares (f). Link space. Percentile 95% intervals over 2,000 paired region draws, with the number of finite draws where a statistic is defined on fewer of them. Same-link pairs are comparable; cross-link pairs are shown for completeness and are not comparable in scale or rank. Shares are of a model's total mean absolute SHAP value over J, without intervals, as in the comparison's files. <!-- src: D:/treeroute/analysis/shap_v1/out/ndvi/lead_0/compare/pairs.parquet, per_lead.json, importance.parquet and families.parquet; D:/treeroute/analysis/shap_v1/verify_v1/A/results.json problems.ndvi.levels.<level>.pairs (the sign agreement's intervals, ruling BB1); D:/treeroute/analysis/shap_v1/verify_v1/_lead/outputs/bardl_maxima.txt (the collation moves of the footnote, ruling BB3); rulings BB1, BB2, BB3, BB5 -->

**a. Variable level: every pair.**

| Pair | Link | Spearman over J | Spearman, top-20 union | Kendall's tau-b | Jaccard top 5 | Jaccard top 10 | RBO, p = 0.9 | RBO, p = 0.95 | Share distance (TV) | Family-share distance (TV) | Sign agreement, top-10 union (signs)† |
|---|---|---|---|---|---|---|---|---|---|---|---|
| treeroute v1 vs Ridge | same-link | 0.61 [0.58, 0.63] | −0.41 [−0.44, −0.34] | 0.43 [0.41, 0.45] | 0.00 [0.00, 0.11] | 0.11 [0.11, 0.18] | 0.17 [0.15, 0.19] | 0.33 [0.31, 0.35] | 0.48 [0.47, 0.49] | 0.05 [0.03, 0.08] | 0.75 [0.50, 0.80] (4 signs) |
| treeroute v1 vs random forest | same-link | 0.71 [0.68, 0.73] | −0.02 [−0.11, 0.03] | 0.53 [0.50, 0.55] | 0.25 [0.00, 0.25] | 0.33 [0.25, 0.54] | 0.31 [0.26, 0.34] | 0.44 [0.40, 0.46] | 0.47 [0.45, 0.49] | 0.20 [0.18, 0.23] | 0.75 [0.75, 0.75] (4 signs) |
| treeroute v1 vs LightGBM | same-link | 0.70 [0.66, 0.72] | 0.16 [0.08, 0.23] | 0.52 [0.49, 0.54] | 0.43 [0.25, 0.67] | 0.43 [0.33, 0.54] | 0.51 [0.46, 0.54] | 0.56 [0.53, 0.58] | 0.30 [0.29, 0.31] | 0.09 [0.07, 0.11] | 0.75 [0.67, 0.80] (4 signs) |
| treeroute v1 vs BARDL‡ | same-link | 0.28 [0.27, 0.28] | 0.38 [0.34, 0.41] | 0.23 [0.22, 0.23] | 0.25 [0.25, 0.43] | 0.25 [0.18, 0.25] | 0.37 [0.31, 0.39] | 0.40 [0.37, 0.42] | 0.88 [0.87, 0.89] | 0.11 [0.08, 0.14] | 1.00 [0.00, 1.00] (1 sign) |
| Ridge vs random forest | same-link | 0.53 [0.51, 0.55] | −0.66 [−0.71, −0.63] | 0.37 [0.35, 0.38] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.05] | 0.08 [0.07, 0.09] | 0.22 [0.21, 0.23] | 0.61 [0.59, 0.62] | 0.22 [0.19, 0.24] | 0.83 [0.80, 0.86] (6 signs) |
| Ridge vs LightGBM | same-link | 0.58 [0.56, 0.60] | −0.51 [−0.58, −0.49] | 0.42 [0.40, 0.44] | 0.00 [0.00, 0.11] | 0.11 [0.05, 0.11] | 0.13 [0.11, 0.15] | 0.28 [0.26, 0.29] | 0.51 [0.50, 0.52] | 0.04 [0.03, 0.07] | 0.86 [0.83, 0.86] (7 signs) |
| Ridge vs BARDL‡ | same-link | 0.15 [0.14, 0.16] | 0.03 [0.00, 0.04] | 0.13 [0.11, 0.13] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.05] | 0.05 [0.05, 0.06] | 0.15 [0.15, 0.16] | 0.96 [0.95, 0.96] | 0.11 [0.11, 0.13] | 1.00 [1.00, 1.00] (1 sign) |
| random forest vs LightGBM | same-link | 0.91 [0.88, 0.92] | 0.47 [0.36, 0.56] | 0.78 [0.75, 0.79] | 0.43 [0.25, 0.43] | 0.54 [0.43, 0.67] | 0.69 [0.64, 0.71] | 0.74 [0.71, 0.76] | 0.28 [0.27, 0.30] | 0.25 [0.23, 0.27] | 1.00 [1.00, 1.00] (6 signs) |
| random forest vs BARDL‡ | same-link | 0.16 [0.15, 0.17] | 0.16 [0.12, 0.18] | 0.13 [0.12, 0.14] | 0.11 [0.00, 0.11] | 0.18 [0.11, 0.18] | 0.15 [0.12, 0.19] | 0.24 [0.21, 0.27] | 0.96 [0.95, 0.96] | 0.31 [0.28, 0.35] | undefined (0 signs) |
| LightGBM vs BARDL‡ | same-link | 0.16 [0.12, 0.19] | 0.11 [0.07, 0.11] | 0.13 [0.10, 0.15] | 0.11 [0.11, 0.11] | 0.05 [0.05, 0.11] | 0.20 [0.16, 0.22] | 0.25 [0.23, 0.27] | 0.91 [0.90, 0.92] | 0.16 [0.14, 0.17] | undefined (0 signs) |

**b. Feature level: every pair.**

| Pair | Link | Spearman over J | Spearman, top-20 union | Kendall's tau-b | Jaccard top 5 | Jaccard top 10 | Jaccard top 20 | RBO, p = 0.9 | RBO, p = 0.95 | Share distance (TV) | Family-share distance (TV)§ | Sign agreement, top-10 union (signs)† |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| treeroute v1 vs Ridge | same-link | 0.17 [0.15, 0.18] | −0.48 [−0.59, −0.40] | 0.12 [0.10, 0.13] | 0.00 [0.00, 0.00] | 0.18 [0.00, 0.18] | 0.14 [0.11, 0.14] | 0.12 [0.06, 0.16] | 0.19 [0.13, 0.21] | 0.54 [0.53, 0.55] | 0.05 [0.03, 0.08] | 0.67 [0.56, 0.67] (9 signs) |
| treeroute v1 vs random forest | same-link | 0.27 [0.24, 0.30] | −0.65 [−0.70, −0.61] | 0.19 [0.17, 0.21] | 0.00 [0.00, 0.00] | 0.05 [0.00, 0.05] | 0.11 [0.05, 0.18] | 0.08 [0.05, 0.10] | 0.15 [0.12, 0.17] | 0.45 [0.44, 0.47] | 0.20 [0.18, 0.23] | 1.00 [1.00, 1.00] (3 signs) |
| treeroute v1 vs LightGBM | same-link | 0.28 [0.25, 0.30] | −0.11 [−0.19, −0.04] | 0.19 [0.17, 0.21] | 0.25 [0.25, 0.25] | 0.33 [0.25, 0.33] | 0.25 [0.18, 0.25] | 0.53 [0.41, 0.55] | 0.46 [0.39, 0.47] | 0.34 [0.33, 0.35] | 0.09 [0.07, 0.11] | 1.00 [1.00, 1.00] (2 signs) |
| treeroute v1 vs BARDL‡ | same-link | 0.18 [0.18, 0.19] | −0.06 [−0.11, −0.03] | 0.15 [0.14, 0.15] | 0.11 [0.11, 0.11] | 0.11 [0.11, 0.11] | 0.11 [0.11, 0.14] | 0.31 [0.16, 0.32] | 0.26 [0.18, 0.27] | 0.93 [0.92, 0.93] | 0.11 [0.08, 0.14] | undefined (0 signs) |
| Ridge vs random forest | same-link | 0.27 [0.25, 0.29] | −0.72 [−0.75, −0.67] | 0.19 [0.17, 0.20] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.03 [0.03, 0.05] | 0.01 [0.01, 0.02] | 0.04 [0.03, 0.05] | 0.62 [0.61, 0.63] | 0.22 [0.19, 0.24] | 1.00 [0.83, 1.00] (7 signs) |
| Ridge vs LightGBM | same-link | 0.31 [0.29, 0.33] | −0.53 [−0.63, −0.45] | 0.21 [0.20, 0.23] | 0.00 [0.00, 0.00] | 0.11 [0.00, 0.11] | 0.11 [0.08, 0.14] | 0.09 [0.05, 0.13] | 0.14 [0.10, 0.17] | 0.55 [0.54, 0.56] | 0.04 [0.03, 0.07] | 1.00 [1.00, 1.00] (6 signs) |
| Ridge vs BARDL‡ | same-link | 0.03 [0.02, 0.03] | −0.47 [−0.48, −0.46] | 0.02 [0.02, 0.03] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.01 [0.01, 0.01] | 0.03 [0.02, 0.03] | 0.99 [0.99, 0.99] | 0.11 [0.11, 0.13] | 1.00 [1.00, 1.00] (1 sign) |
| random forest vs LightGBM | same-link | 0.84 [0.82, 0.85] | 0.06 [−0.01, 0.13] | 0.67 [0.65, 0.68] | 0.25 [0.25, 0.25] | 0.43 [0.33, 0.43] | 0.43 [0.33, 0.48] | 0.43 [0.40, 0.45] | 0.52 [0.49, 0.53] | 0.27 [0.26, 0.29] | 0.25 [0.23, 0.27] | 1.00 [1.00, 1.00] (3 signs) |
| random forest vs BARDL‡ | same-link | 0.05 [0.04, 0.07] | −0.31 [−0.36, −0.28] | 0.04 [0.03, 0.05] | 0.00 [0.00, 0.00] | 0.05 [0.00, 0.05] | 0.03 [0.03, 0.05] | 0.05 [0.02, 0.06] | 0.06 [0.04, 0.07] | 0.98 [0.97, 0.98] | 0.31 [0.28, 0.35] | 1.00 [0.00, 1.00] (1 sign) |
| LightGBM vs BARDL‡ | same-link | 0.06 [0.05, 0.07] | −0.18 [−0.24, −0.17] | 0.05 [0.04, 0.06] | 0.11 [0.11, 0.11] | 0.11 [0.05, 0.11] | 0.05 [0.05, 0.05] | 0.28 [0.12, 0.28] | 0.20 [0.11, 0.20] | 0.94 [0.93, 0.95] | 0.16 [0.14, 0.17] | 1.00 [1.00, 1.00] (1 sign) |

**c. Agreement within the main set, and each model's stability.**

| Statistic | Variable level | Feature level |
|---|---|---|
| Kendall's W of the main set [95% CI] | 0.62 [0.61, 0.62] | 0.42 [0.41, 0.43] |
| Mean pairwise Spearman of the main set [95% CI] | 0.48 [0.47, 0.49] | 0.25 [0.24, 0.25] |
| Stability under region resampling: treeroute v1 | 0.99 | 0.99 |
| Stability under region resampling: Ridge | 1.00 | 1.00 |
| Stability under region resampling: random forest | 1.00 | 0.99 |
| Stability under region resampling: LightGBM | 0.99 | 0.99 |
| Stability under region resampling: BARDL | 1.00 | 1.00 |

**d. Variable level: each model's top 10 (share).**

| Rank | treeroute v1 | Ridge | Random forest | LightGBM | BARDL‡ |
|---|---|---|---|---|---|
| 1 | `hist_mean` 7.3% | `sst_anom_nino34` 12.5% | `spi` 35.2% | `spi` 12.2% | `soil_moisture_pct` 45.7% |
| 2 | `hist_last` 6.4% | `nino34` 9.8% | `climate_water_deficit_mm` 3.5% | `hist_last` 6.8% | `hist_last` 29.5% |
| 3 | `era5l_slhf` 5.6% | `oni` 4.9% | `sst_anom_subpolar_north_atlantic` 2.9% | `hist_mean` 5.6% | `total_precip_mm` 24.8% |
| 4 | `aet_total_mm` 4.7% | `era5l_ssr` 4.6% | `wbal` 2.9% | `wbal` 2.7% | `aet_total_mm` 0.0% |
| 5 | `wbal` 2.9% | `mean_vpd_kPa` 3.8% | `hist_last` 2.3% | `grace_lwe` 2.4% | `aglw_buffalo_hold2021` 0.0% |
| 6 | `total_precip_mm` 2.9% | `sph_kgkg` 3.8% | `sst_anom_global_tropical` 2.0% | `era5l_slhf` 2.3% | `aglw_cattle_hold2021` 0.0% |
| 7 | `era5l_str` 2.8% | `hist_mean` 3.5% | `grace_lwe` 2.0% | `sst_anom_subpolar_north_atlantic` 2.0% | `aglw_goats_hold2021` 0.0% |
| 8 | `soil_moisture_pct` 2.5% | `vpd_warm_season` 3.4% | `aet_total_mm` 1.9% | `climate_water_deficit_mm` 1.9% | `aglw_horse_hold2021` 0.0% |
| 9 | `spi` 2.5% | `solar_radiation_Wm2` 3.2% | `swe_mean_mm` 1.7% | `sst_anom_global_tropical` 1.7% | `aglw_sheep_hold2021` 0.0% |
| 10 | `soil_water_tc_mm` 2.4% | `era5l_str` 3.0% | `total_precip_mm` 1.6% | `era5l_str` 1.6% | `aglw_total_lsu_hold2021` 0.0% |
| Nonzero variables | 94 | 96 | 94 | 94 | 3 |

**e. Feature level: each model's top 10 (share).**

| Rank | treeroute v1 | Ridge | Random forest | LightGBM | BARDL‡ |
|---|---|---|---|---|---|
| 1 | `x__hist_last_1` 3.0% | `x__sst_anom_nino34_lag12` 4.4% | `x__spi_03m` 9.8% | `x__hist_last_1` 4.1% | `x__hist_last_1` 18.3% |
| 2 | `x__hist_mean_12` 2.9% | `x__sst_anom_nino34_lag6` 3.8% | `x__spi_06m` 7.0% | `x__hist_mean_12` 3.7% | `x__V30_soil_moisture_pct` 18.1% |
| 3 | `x__era5l_slhf_lag1` 2.3% | `x__nino34_lag12` 3.8% | `x__spi_12m` 4.1% | `x__spi_03m` 2.3% | `x__V30_soil_moisture_pct_lag1` 17.1% |
| 4 | `x__hist_mean_60` 1.9% | `x__era5l_ssr` 3.3% | `x__spi_01m_lag1` 3.1% | `x__hist_mean_all` 1.9% | `x__V02_total_precip_mm_lag1` 10.9% |
| 5 | `x__aet_total_mm_roll3` 1.6% | `x__nino34_lag6` 3.0% | `x__spi_03m_lag1` 2.5% | `x__spi_06m` 1.9% | `x__V02_total_precip_mm` 8.8% |
| 6 | `x__era5l_slhf` 1.4% | `x__sph_kgkg` 1.5% | `x__spi_06m_lag1` 1.3% | `x__spi_01m_lag1` 1.5% | `x__V30_soil_moisture_pct_lag2` 8.3% |
| 7 | `x__hist_last_2` 1.2% | `x__hist_mean_12` 1.5% | `x__hist_last_1` 1.2% | `x__spi_03m_lag1` 1.5% | `x__V02_total_precip_mm_lag2` 6.9% |
| 8 | `x__hist_mean_all` 1.2% | `x__spi_24m` 1.5% | `x__spi_12m_lag1` 1.1% | `x__spi_12m` 1.3% | `x__hist_last_3` 6.0% |
| 9 | `x__era5l_str_lag1` 1.1% | `x__hist_mean_all` 1.4% | `x__swe_mean_mm` 1.1% | `x__era5l_slhf` 0.9% | `x__hist_last_2` 5.6% |
| 10 | `x__V02_total_precip_mm_roll3` 1.0% | `x__hist_mean_60` 1.4% | `x__climate_water_deficit_mm_lag1` 1.1% | `x__hist_last_2` 0.7% | `x__V01_mean_temp_C` 0.0% |
| Nonzero players | 477 | 479 | 477 | 477 | 9 |

**f. Family shares (sums of the variable-level attributions per row).**

| Family | treeroute v1 | Ridge | Random forest | LightGBM | BARDL |
|---|---|---|---|---|---|
| Own history | 24.5% | 25.7% | 4.2% | 25.5% | 35.2% |
| Global indices | 8.0% | 11.4% | 11.3% | 15.6% | 0.0% |
| Local drivers | 67.5% | 62.9% | 84.4% | 59.0% | 64.8% |
| Context and calendar | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| Seasonal normal | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |

Sign agreement: of the players in the union of the two top-10 sets whose sign is determined in both models (the bootstrap 95% interval of the signed mean excludes 0), the share whose signs agree; in brackets, the number of such players ("signs") and, where fewer than 2,000, the number of draws on which the statistic is defined. Undefined: no player qualifies on the full sample.
† The sign agreement's interval is from the independent re-computation of the comparison (two implementations, A and B, that agree; ruling BB1): the comparison script evaluates the sign agreement on the full sample only, so its files hold no interval. The value and its number of signs are the comparison's.
‡ BARDL reads three variables (nine columns) by design and gives exactly 0 to the other 93 of the 96 variables of J (470 of the 479 players at the feature level). Its top-5, top-10 and top-20 sets are therefore filled by name order, the tie rule applied in code-point ascending order, at both levels, and the cells of its pairs that use those sets depend on that order. Under the other two orders tried (case-insensitive ascending, and descending), the largest move of each statistic over BARDL's eight pair-levels is: Jaccard top 5, 0.14 (variable level, treeroute v1 vs BARDL); Jaccard top 10, 0.06 (variable level, LightGBM vs BARDL); Jaccard top 20, 0.03 (feature level, treeroute v1 vs BARDL); top-20-union Spearman, 0.13 (feature level, treeroute v1 vs BARDL); RBO p = 0.9, 0.05 (variable level, LightGBM vs BARDL); RBO p = 0.95, 0.08 (variable level, Ridge vs BARDL). For example, BARDL's Jaccard top 5 with treeroute v1 at the variable level is 0.25 with the tie-only `aet_total_mm` in its top 5, and 0.11 without it (ruling BB3).
§ Families are sums of variable-level attributions, so at the feature level the family-share distance is the variable-level value repeated (ruling BB2).
Stability (panel c): the mean Spearman of a model's full-sample importances with its own bootstrap replicates; descriptive, not a ceiling on between-model agreement. Nonzero (panels d and e): the players of J to which the model gives a nonzero share.

**Table S3.25 (post hoc).** Burned fraction, nowcast: agreement of the models' SHAP attributions, every pair at the variable level (a) and at the feature level (b); the main set's agreement and each model's stability (c); each model's top 10 at both levels (d, e) and its family shares (f); and the arcsine-link models' top 10 on their rows with a forecast above 0 (g). Link space. Percentile 95% intervals over 2,000 paired region draws, with the number of finite draws where a statistic is defined on fewer of them. Same-link pairs are comparable; cross-link pairs are shown for completeness and are not comparable in scale or rank. Shares are of a model's total mean absolute SHAP value over J, without intervals, as in the comparison's files. <!-- src: D:/treeroute/analysis/shap_v1/out/fire/lead_0/compare/pairs.parquet, per_lead.json, importance.parquet and families.parquet; D:/treeroute/analysis/shap_v1/verify_v1/A/results.json problems.fire.levels.<level>.pairs (the sign agreement's intervals, ruling BB1); rulings BB1, BB2, BB5 -->

**a. Variable level: every pair.**

| Pair | Link | Spearman over J | Spearman, top-20 union | Kendall's tau-b | Jaccard top 5 | Jaccard top 10 | RBO, p = 0.9 | RBO, p = 0.95 | Share distance (TV) | Family-share distance (TV) | Sign agreement, top-10 union (signs)† |
|---|---|---|---|---|---|---|---|---|---|---|---|
| treeroute v1 vs Ridge | cross-link (not comparable in scale or rank); raw model, declined by its guard: Ridge | 0.47 [0.41, 0.52] | −0.15 [−0.31, −0.15] | 0.32 [0.28, 0.37] | 0.43 [0.25, 0.43] | 0.18 [0.18, 0.25] | 0.42 [0.29, 0.46] | 0.45 [0.37, 0.48] | 0.50 [0.48, 0.52] | 0.08 [0.02, 0.14] | undefined [0.00, 1.00] (0 signs; 64 finite draws) |
| treeroute v1 vs random forest | cross-link (not comparable in scale or rank) | 0.69 [0.61, 0.72] | 0.03 [−0.12, 0.17] | 0.52 [0.46, 0.55] | 0.67 [0.43, 0.67] | 0.25 [0.25, 0.43] | 0.53 [0.44, 0.57] | 0.57 [0.50, 0.60] | 0.33 [0.31, 0.36] | 0.10 [0.07, 0.17] | 1.00 [0.00, 1.00] (1 sign; 1,380 finite draws) |
| treeroute v1 vs LightGBM | cross-link (not comparable in scale or rank) | 0.68 [0.62, 0.71] | 0.05 [−0.09, 0.17] | 0.52 [0.46, 0.54] | 0.67 [0.43, 0.67] | 0.33 [0.25, 0.43] | 0.54 [0.44, 0.57] | 0.58 [0.51, 0.60] | 0.34 [0.32, 0.38] | 0.06 [0.01, 0.12] | 1.00 [0.00, 1.00] (1 sign; 1,140 finite draws) |
| treeroute v1 vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.61 [0.52, 0.67] | −0.14 [−0.26, −0.01] | 0.44 [0.37, 0.49] | 0.25 [0.11, 0.25] | 0.25 [0.11, 0.33] | 0.37 [0.26, 0.43] | 0.45 [0.39, 0.49] | 0.27 [0.26, 0.30] | 0.09 [0.06, 0.12] | 0.00 [0.00, 0.00] (1 sign) |
| Ridge vs random forest | same-link; raw model, declined by its guard: Ridge | 0.70 [0.66, 0.72] | 0.22 [−0.04, 0.26] | 0.53 [0.49, 0.55] | 0.43 [0.43, 0.43] | 0.54 [0.18, 0.54] | 0.71 [0.55, 0.72] | 0.69 [0.58, 0.70] | 0.31 [0.29, 0.34] | 0.11 [0.07, 0.16] | 1.00 [0.75, 1.00] (3 signs) |
| Ridge vs LightGBM | same-link; raw model, declined by its guard: Ridge | 0.59 [0.53, 0.64] | 0.18 [0.04, 0.24] | 0.44 [0.39, 0.47] | 0.43 [0.43, 0.67] | 0.33 [0.25, 0.43] | 0.67 [0.57, 0.68] | 0.64 [0.58, 0.66] | 0.34 [0.32, 0.36] | 0.02 [0.01, 0.09] | 0.60 [0.60, 0.75] (5 signs) |
| Ridge vs Tweedie booster | cross-link (not comparable in scale or rank); raw model, declined by its guard: Ridge | 0.68 [0.65, 0.71] | 0.16 [0.06, 0.25] | 0.50 [0.48, 0.53] | 0.25 [0.25, 0.43] | 0.43 [0.33, 0.43] | 0.59 [0.55, 0.67] | 0.62 [0.59, 0.66] | 0.37 [0.36, 0.40] | 0.12 [0.07, 0.16] | 0.83 [0.67, 0.83] (6 signs) |
| random forest vs LightGBM | same-link | 0.87 [0.82, 0.89] | 0.73 [0.50, 0.79] | 0.71 [0.66, 0.74] | 0.67 [0.67, 1.00] | 0.67 [0.43, 0.82] | 0.85 [0.77, 0.87] | 0.82 [0.77, 0.84] | 0.14 [0.12, 0.18] | 0.09 [0.06, 0.14] | 1.00 [1.00, 1.00] (4 signs) |
| random forest vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.71 [0.65, 0.77] | −0.01 [−0.16, 0.15] | 0.53 [0.47, 0.58] | 0.25 [0.25, 0.25] | 0.33 [0.18, 0.43] | 0.52 [0.48, 0.57] | 0.56 [0.52, 0.60] | 0.31 [0.28, 0.35] | 0.18 [0.15, 0.23] | 1.00 [0.80, 1.00] (4 signs) |
| LightGBM vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.75 [0.68, 0.79] | 0.11 [−0.02, 0.25] | 0.57 [0.51, 0.61] | 0.43 [0.25, 0.43] | 0.25 [0.18, 0.43] | 0.56 [0.52, 0.60] | 0.60 [0.56, 0.63] | 0.29 [0.27, 0.34] | 0.11 [0.09, 0.15] | 0.75 [0.67, 1.00] (4 signs) |

**b. Feature level: every pair.**

| Pair | Link | Spearman over J | Spearman, top-20 union | Kendall's tau-b | Jaccard top 5 | Jaccard top 10 | RBO, p = 0.9 | RBO, p = 0.95 | Share distance (TV) | Family-share distance (TV)§ | Sign agreement, top-10 union (signs)† |
|---|---|---|---|---|---|---|---|---|---|---|---|
| treeroute v1 vs Ridge | cross-link (not comparable in scale or rank); raw model, declined by its guard: Ridge | 0.27 [0.20, 0.37] | −0.73 [−0.76, −0.60] | 0.18 [0.13, 0.26] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.04 [0.02, 0.06] | 0.14 [0.11, 0.18] | 0.55 [0.54, 0.57] | 0.08 [0.02, 0.14] | undefined (0 signs) |
| treeroute v1 vs random forest | cross-link (not comparable in scale or rank) | 0.59 [0.52, 0.65] | −0.50 [−0.56, −0.34] | 0.44 [0.38, 0.49] | 0.11 [0.00, 0.11] | 0.11 [0.05, 0.18] | 0.19 [0.13, 0.33] | 0.30 [0.25, 0.36] | 0.36 [0.34, 0.39] | 0.10 [0.07, 0.17] | undefined (0 signs) |
| treeroute v1 vs LightGBM | cross-link (not comparable in scale or rank) | 0.58 [0.51, 0.63] | −0.37 [−0.48, −0.29] | 0.42 [0.37, 0.47] | 0.11 [0.00, 0.11] | 0.11 [0.05, 0.18] | 0.25 [0.13, 0.36] | 0.34 [0.25, 0.39] | 0.36 [0.35, 0.41] | 0.06 [0.01, 0.12] | undefined (0 signs) |
| treeroute v1 vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.52 [0.42, 0.59] | −0.69 [−0.78, −0.56] | 0.35 [0.28, 0.41] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.05] | 0.06 [0.03, 0.09] | 0.19 [0.14, 0.22] | 0.28 [0.27, 0.31] | 0.09 [0.06, 0.12] | undefined (0 signs) |
| Ridge vs random forest | same-link; raw model, declined by its guard: Ridge | 0.67 [0.63, 0.69] | 0.34 [0.12, 0.38] | 0.50 [0.47, 0.52] | 0.43 [0.25, 0.67] | 0.43 [0.33, 0.54] | 0.63 [0.55, 0.70] | 0.65 [0.60, 0.69] | 0.32 [0.31, 0.35] | 0.11 [0.07, 0.16] | 1.00 [0.67, 1.00] (2 signs) |
| Ridge vs LightGBM | same-link; raw model, declined by its guard: Ridge | 0.55 [0.50, 0.61] | 0.16 [0.04, 0.25] | 0.40 [0.36, 0.45] | 0.43 [0.25, 0.67] | 0.43 [0.33, 0.54] | 0.57 [0.51, 0.65] | 0.58 [0.54, 0.62] | 0.36 [0.35, 0.39] | 0.02 [0.01, 0.09] | 0.75 [0.50, 1.00] (4 signs) |
| Ridge vs Tweedie booster | cross-link (not comparable in scale or rank); raw model, declined by its guard: Ridge | 0.64 [0.62, 0.67] | 0.31 [0.18, 0.41] | 0.48 [0.47, 0.51] | 0.25 [0.25, 0.43] | 0.43 [0.33, 0.54] | 0.58 [0.43, 0.63] | 0.62 [0.53, 0.65] | 0.42 [0.40, 0.43] | 0.12 [0.07, 0.16] | 1.00 [1.00, 1.00] (3 signs) |
| random forest vs LightGBM | same-link | 0.86 [0.82, 0.88] | 0.68 [0.54, 0.77] | 0.70 [0.66, 0.73] | 0.67 [0.67, 1.00] | 0.54 [0.43, 0.82] | 0.78 [0.71, 0.87] | 0.78 [0.73, 0.83] | 0.15 [0.14, 0.19] | 0.09 [0.06, 0.14] | 1.00 [1.00, 1.00] (4 signs) |
| random forest vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.67 [0.62, 0.72] | −0.06 [−0.21, 0.05] | 0.50 [0.46, 0.54] | 0.11 [0.11, 0.25] | 0.25 [0.18, 0.43] | 0.49 [0.32, 0.51] | 0.53 [0.44, 0.55] | 0.34 [0.31, 0.37] | 0.18 [0.15, 0.23] | 0.75 [0.67, 0.80] (4 signs) |
| LightGBM vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.67 [0.62, 0.72] | −0.13 [−0.21, −0.03] | 0.51 [0.46, 0.55] | 0.25 [0.11, 0.25] | 0.33 [0.18, 0.33] | 0.49 [0.33, 0.52] | 0.52 [0.44, 0.55] | 0.32 [0.30, 0.37] | 0.11 [0.09, 0.15] | 1.00 [0.50, 1.00] (2 signs) |

**c. Agreement within the main set, and each model's stability.**

| Statistic | Variable level | Feature level |
|---|---|---|
| Kendall's W of the main set [95% CI] | undefinedᵃ | undefinedᵃ |
| Mean pairwise Spearman of the main set [95% CI] | undefinedᵃ | undefinedᵃ |
| Stability under region resampling: treeroute v1 | 0.97 | 0.95 |
| Stability under region resampling: Ridge | 0.99 | 0.99 |
| Stability under region resampling: random forest | 0.98 | 0.99 |
| Stability under region resampling: LightGBM | 0.98 | 0.97 |
| Stability under region resampling: Tweedie booster | 0.99 | 0.99 |

**d. Variable level: each model's top 10 (share).**

| Rank | treeroute v1 | Ridge | Random forest | LightGBM | Tweedie booster |
|---|---|---|---|---|---|
| 1 | `hist_mean` 4.0% | `spi` 24.2% | `spi` 16.7% | `spi` 14.8% | `spi` 8.9% |
| 2 | `spei` 3.3% | `hist_mean` 7.1% | `hist_mean` 10.2% | `hist_mean` 7.9% | `spei` 7.2% |
| 3 | `tslf_months` 3.2% | `spei` 7.1% | `tslf_months` 7.3% | `tslf_months` 7.4% | `sst_anom_atl3` 3.6% |
| 4 | `spi` 3.0% | `sst_anom_coral_sea` 6.4% | `spei` 4.6% | `spei` 4.4% | `nbr75km` 2.8% |
| 5 | `era5l_str` 2.8% | `n_burns` 3.8% | `wbal_mm` 3.2% | `sst_anom_atl3` 3.6% | `precip_seasonality` 2.5% |
| 6 | `deeprec_twsa` 2.7% | `sst_anom_atl3` 3.8% | `hist_last` 2.0% | `epo` 3.2% | `nbr25km` 2.3% |
| 7 | `ao` 2.3% | `hist_last` 3.7% | `sst_anom_coral_sea` 1.8% | `tni` 2.5% | `nao` 2.2% |
| 8 | `wbal` 2.3% | `nao` 2.9% | `sst_anom_atl3` 1.7% | `wbal_mm` 2.4% | `wbal` 2.2% |
| 9 | `grace_lwe` 1.9% | `sst_anom_iod_east` 2.5% | `sst_anom_mediterranean` 1.6% | `wbal` 2.0% | `sst_anom_coral_sea` 2.1% |
| 10 | `nbr25km` 1.8% | `sst_anom_mediterranean` 2.3% | `tni` 1.5% | `hist_last` 1.8% | `sst_anom_mediterranean` 2.0% |
| Nonzero variables | 94 | 94 | 94 | 87 | 94 |

**e. Feature level: each model's top 10 (share).**

| Rank | treeroute v1 | Ridge | Random forest | LightGBM | Tweedie booster |
|---|---|---|---|---|---|
| 1 | `x__tslf_months` 2.9% | `x__spi_03m` 11.4% | `x__spi_03m` 9.7% | `x__spi_03m` 8.8% | `x__spi_03m` 3.4% |
| 2 | `x__era5l_str` 2.6% | `x__spi_01m` 9.2% | `x__hist_mean_12` 7.0% | `x__tslf_months` 6.5% | `x__spi_24m` 3.3% |
| 3 | `x__deeprec_twsa` 2.5% | `x__spi_06m` 6.3% | `x__tslf_months` 6.3% | `x__hist_mean_12` 5.7% | `x__sst_anom_atl3` 3.1% |
| 4 | `x__hist_mean_60` 2.4% | `x__spi_24m` 6.1% | `x__spi_01m` 5.7% | `x__spi_01m` 4.6% | `x__spei_01m_lag12` 3.0% |
| 5 | `x__ao` 2.1% | `x__hist_mean_12` 5.5% | `x__hist_mean_all` 3.7% | `x__sst_anom_atl3` 3.2% | `x__spei_24m_lag12` 2.6% |
| 6 | `x__grace_lwe` 1.7% | `x__sst_anom_coral_sea` 5.1% | `x__spi_06m` 3.5% | `x__epo` 2.8% | `x__spi_06m` 2.4% |
| 7 | `x__era5l_sshf` 1.6% | `x__spi_12m` 4.2% | `x__wbal_mm` 2.7% | `x__spi_24m` 2.7% | `x__V04_precip_seasonality` 2.2% |
| 8 | `x__rmin_pct` 1.6% | `x__n_burns_12mo` 3.0% | `x__spi_24m` 2.0% | `x__hist_mean_all` 2.6% | `x__spei_06m_lag12` 2.2% |
| 9 | `x__V05_mean_vpd_kPa` 1.5% | `x__sst_anom_atl3` 3.0% | `x__hist_last_1` 1.7% | `x__spi_06m` 2.6% | `x__spi_01m` 2.0% |
| 10 | `x__hist_mean_all` 1.5% | `x__nao` 2.3% | `x__sst_anom_coral_sea` 1.5% | `x__V06_spei_12m_lag12` 2.3% | `x__spi_12m` 2.0% |
| Nonzero players | 111 | 111 | 111 | 103 | 111 |

**f. Family shares (sums of the variable-level attributions per row).**

| Family | treeroute v1 | Ridge | Random forest | LightGBM | Tweedie booster |
|---|---|---|---|---|---|
| Own history | 13.6% | 18.0% | 23.8% | 17.3% | 6.1% |
| Global indices | 26.0% | 29.6% | 18.7% | 28.1% | 34.6% |
| Local drivers | 60.4% | 52.4% | 57.5% | 54.6% | 59.3% |
| Context and calendar | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| Seasonal normal | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |

**g. Arcsine-link models, rows with a forecast above 0: top 10 (share).**

| Rank | treeroute v1 |
|---|---|
| 1 | `hist_mean` 4.1% |
| 2 | `spei` 3.4% |
| 3 | `spi` 3.3% |
| 4 | `deeprec_twsa` 3.2% |
| 5 | `era5l_str` 3.1% |
| 6 | `tslf_months` 2.9% |
| 7 | `wbal` 2.5% |
| 8 | `rmin_pct` 2.2% |
| 9 | `ao` 2.2% |
| 10 | `grace_lwe` 1.7% |
| Rows with a forecast above 0 | 226 |

ᵃ The main set is treeroute v1 alone: every rival explains in another link, and Ridge also failed its skill guard. Kendall's W and the mean pairwise Spearman need two models and are undefined; agreement between treeroute v1 and a rival cannot separate the link from the model.
Sign agreement: of the players in the union of the two top-10 sets whose sign is determined in both models (the bootstrap 95% interval of the signed mean excludes 0), the share whose signs agree; in brackets, the number of such players ("signs") and, where fewer than 2,000, the number of draws on which the statistic is defined. Undefined: no player qualifies on the full sample.
† The sign agreement's interval is from the independent re-computation of the comparison (two implementations, A and B, that agree; ruling BB1): the comparison script evaluates the sign agreement on the full sample only, so its files hold no interval. The value and its number of signs are the comparison's.
§ Families are sums of variable-level attributions, so at the feature level the family-share distance is the variable-level value repeated (ruling BB2).
Stability (panel c): the mean Spearman of a model's full-sample importances with its own bootstrap replicates; descriptive, not a ceiling on between-model agreement. Nonzero (panels d and e): the players of J to which the model gives a nonzero share.
Panel g: each arcsine-link model's variable-level shares on its rows with a forecast above 0, over every variable of the problem, in the comparison file's order.

**Table S3.26 (post hoc).** Forest loss, nowcast: agreement of the models' SHAP attributions, every pair at the variable level (a) and at the feature level (b); the main set's agreement and each model's stability (c); each model's top 10 at both levels (d, e) and its family shares (f). Link space. Percentile 95% intervals over 2,000 paired region draws, with the number of finite draws where a statistic is defined on fewer of them. Same-link pairs are comparable; cross-link pairs are shown for completeness and are not comparable in scale or rank. Shares are of a model's total mean absolute SHAP value over J, without intervals, as in the comparison's files. <!-- src: D:/treeroute/analysis/shap_v1/out/defo/lead_0/compare/pairs.parquet, per_lead.json, importance.parquet and families.parquet; D:/treeroute/analysis/shap_v1/verify_v1/A/results.json problems.defo.levels.<level>.pairs (the sign agreement's intervals, ruling BB1); rulings BB1, BB2, BB4, BB5 -->

**a. Variable level: every pair.**

| Pair | Link | Spearman over J | Spearman, top-20 union | Kendall's tau-b | Jaccard top 5 | Jaccard top 10 | RBO, p = 0.9 | RBO, p = 0.95 | Share distance (TV) | Family-share distance (TV) | Sign agreement, top-10 union (signs)† |
|---|---|---|---|---|---|---|---|---|---|---|---|
| treeroute v1 vs Ridge | same-link | 0.65 [0.62, 0.68] | 0.01 [−0.12, 0.08] | 0.48 [0.45, 0.51] | 0.25 [0.11, 0.25] | 0.33 [0.25, 0.33] | 0.33 [0.27, 0.52] | 0.45 [0.41, 0.55] | 0.36 [0.35, 0.39] | 0.31 [0.26, 0.37] | 1.00 [0.83, 1.00] (6 signs) |
| treeroute v1 vs random forest | same-link | 0.76 [0.72, 0.80] | 0.20 [0.14, 0.29] | 0.60 [0.56, 0.63] | 0.43 [0.43, 0.67] | 0.43 [0.43, 0.54] | 0.60 [0.59, 0.71] | 0.62 [0.61, 0.69] | 0.28 [0.26, 0.30] | 0.19 [0.16, 0.23] | 0.83 [0.60, 0.86] (6 signs) |
| treeroute v1 vs LightGBM | same-link | 0.74 [0.70, 0.77] | 0.47 [0.38, 0.53] | 0.56 [0.52, 0.59] | 0.43 [0.43, 0.67] | 0.43 [0.43, 0.67] | 0.64 [0.60, 0.74] | 0.67 [0.64, 0.72] | 0.28 [0.27, 0.31] | 0.17 [0.13, 0.21] | 1.00 [0.75, 1.00] (4 signs) |
| treeroute v1 vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.78 [0.74, 0.80] | 0.51 [0.43, 0.58] | 0.61 [0.58, 0.63] | 0.43 [0.43, 0.67] | 0.43 [0.43, 0.67] | 0.52 [0.50, 0.63] | 0.63 [0.61, 0.69] | 0.29 [0.27, 0.31] | 0.17 [0.11, 0.23] | 0.20 [0.00, 0.40] (5 signs) |
| Ridge vs random forest | same-link | 0.63 [0.59, 0.66] | −0.03 [−0.10, 0.05] | 0.46 [0.43, 0.49] | 0.11 [0.11, 0.25] | 0.43 [0.25, 0.43] | 0.34 [0.30, 0.51] | 0.47 [0.44, 0.56] | 0.42 [0.41, 0.43] | 0.25 [0.21, 0.28] | 0.83 [0.62, 0.86] (6 signs) |
| Ridge vs LightGBM | same-link | 0.75 [0.72, 0.77] | −0.04 [−0.13, 0.06] | 0.56 [0.53, 0.58] | 0.25 [0.11, 0.25] | 0.33 [0.25, 0.33] | 0.35 [0.31, 0.53] | 0.50 [0.46, 0.59] | 0.39 [0.38, 0.42] | 0.23 [0.20, 0.27] | 1.00 [0.83, 1.00] (5 signs) |
| Ridge vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.62 [0.58, 0.64] | −0.22 [−0.29, −0.11] | 0.45 [0.42, 0.47] | 0.11 [0.00, 0.11] | 0.25 [0.11, 0.33] | 0.28 [0.23, 0.33] | 0.42 [0.38, 0.45] | 0.47 [0.46, 0.49] | 0.34 [0.28, 0.40] | 0.75 [0.71, 0.80] (8 signs) |
| random forest vs LightGBM | same-link | 0.83 [0.80, 0.84] | 0.52 [0.46, 0.63] | 0.65 [0.62, 0.67] | 0.67 [0.67, 1.00] | 0.67 [0.67, 0.67] | 0.84 [0.74, 0.88] | 0.82 [0.76, 0.84] | 0.17 [0.16, 0.18] | 0.02 [0.00, 0.04] | 1.00 [1.00, 1.00] (6 signs) |
| random forest vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.83 [0.80, 0.85] | 0.36 [0.28, 0.41] | 0.69 [0.65, 0.70] | 0.43 [0.25, 0.67] | 0.67 [0.43, 0.67] | 0.58 [0.54, 0.62] | 0.65 [0.62, 0.67] | 0.31 [0.29, 0.32] | 0.12 [0.08, 0.17] | 0.60 [0.40, 0.67] (5 signs) |
| LightGBM vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.79 [0.75, 0.81] | 0.60 [0.54, 0.64] | 0.61 [0.57, 0.62] | 0.25 [0.25, 0.43] | 0.82 [0.67, 0.82] | 0.61 [0.57, 0.70] | 0.69 [0.65, 0.72] | 0.30 [0.28, 0.32] | 0.12 [0.09, 0.17] | 0.33 [0.25, 0.33] (3 signs) |

**b. Feature level: every pair.**

| Pair | Link | Spearman over J | Spearman, top-20 union | Kendall's tau-b | Jaccard top 5 | Jaccard top 10 | Jaccard top 20 | RBO, p = 0.9 | RBO, p = 0.95 | Share distance (TV) | Family-share distance (TV)§ | Sign agreement, top-10 union (signs)† |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| treeroute v1 vs Ridge | same-link | 0.45 [0.41, 0.50] | −0.14 [−0.27, 0.06] | 0.32 [0.29, 0.35] | 0.43 [0.25, 0.43] | 0.25 [0.18, 0.43] | 0.21 [0.14, 0.29] | 0.41 [0.25, 0.48] | 0.40 [0.30, 0.46] | 0.40 [0.39, 0.43] | 0.31 [0.26, 0.37] | 1.00 [0.83, 1.00] (6 signs) |
| treeroute v1 vs random forest | same-link | 0.67 [0.63, 0.70] | 0.11 [−0.03, 0.15] | 0.51 [0.47, 0.52] | 0.67 [0.43, 0.67] | 0.33 [0.25, 0.43] | 0.25 [0.21, 0.33] | 0.59 [0.55, 0.63] | 0.52 [0.49, 0.55] | 0.29 [0.28, 0.31] | 0.19 [0.16, 0.23] | 0.60 [0.50, 0.83] (5 signs) |
| treeroute v1 vs LightGBM | same-link | 0.62 [0.58, 0.66] | 0.37 [0.23, 0.40] | 0.45 [0.41, 0.47] | 0.67 [0.67, 0.67] | 0.67 [0.43, 0.67] | 0.33 [0.33, 0.43] | 0.65 [0.53, 0.67] | 0.61 [0.53, 0.62] | 0.33 [0.32, 0.36] | 0.17 [0.13, 0.21] | 1.00 [1.00, 1.00] (1 sign) |
| treeroute v1 vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.67 [0.63, 0.69] | 0.42 [0.28, 0.47] | 0.51 [0.47, 0.53] | 0.43 [0.43, 0.67] | 0.67 [0.43, 0.67] | 0.43 [0.29, 0.43] | 0.51 [0.48, 0.59] | 0.55 [0.53, 0.59] | 0.27 [0.26, 0.30] | 0.17 [0.11, 0.23] | 0.33 [0.33, 0.67] (3 signs) |
| Ridge vs random forest | same-link | 0.55 [0.52, 0.58] | −0.29 [−0.44, −0.16] | 0.38 [0.36, 0.40] | 0.25 [0.25, 0.25] | 0.11 [0.11, 0.25] | 0.18 [0.11, 0.25] | 0.28 [0.19, 0.37] | 0.32 [0.25, 0.39] | 0.44 [0.44, 0.46] | 0.25 [0.21, 0.28] | 0.69 [0.55, 0.75] (13 signs) |
| Ridge vs LightGBM | same-link | 0.64 [0.61, 0.65] | −0.19 [−0.35, −0.02] | 0.45 [0.43, 0.47] | 0.25 [0.25, 0.25] | 0.18 [0.11, 0.33] | 0.29 [0.21, 0.38] | 0.30 [0.23, 0.39] | 0.36 [0.30, 0.44] | 0.43 [0.41, 0.45] | 0.23 [0.20, 0.27] | 0.86 [0.83, 0.88] (7 signs) |
| Ridge vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.50 [0.47, 0.53] | −0.34 [−0.43, −0.19] | 0.35 [0.33, 0.38] | 0.11 [0.11, 0.11] | 0.25 [0.18, 0.33] | 0.18 [0.11, 0.25] | 0.22 [0.18, 0.29] | 0.30 [0.26, 0.35] | 0.46 [0.44, 0.47] | 0.34 [0.28, 0.40] | 0.71 [0.60, 0.71] (7 signs) |
| random forest vs LightGBM | same-link | 0.75 [0.73, 0.77] | 0.23 [0.15, 0.37] | 0.57 [0.55, 0.58] | 1.00 [0.67, 1.00] | 0.43 [0.43, 0.67] | 0.33 [0.29, 0.48] | 0.78 [0.66, 0.80] | 0.72 [0.65, 0.74] | 0.23 [0.22, 0.24] | 0.02 [0.00, 0.04] | 1.00 [1.00, 1.00] (6 signs) |
| random forest vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.77 [0.74, 0.78] | 0.18 [0.07, 0.24] | 0.62 [0.59, 0.63] | 0.43 [0.25, 0.43] | 0.43 [0.43, 0.43] | 0.33 [0.25, 0.43] | 0.49 [0.46, 0.53] | 0.52 [0.50, 0.56] | 0.27 [0.26, 0.29] | 0.12 [0.08, 0.17] | 0.50 [0.50, 0.67] (6 signs) |
| LightGBM vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.72 [0.69, 0.75] | 0.36 [0.29, 0.48] | 0.53 [0.51, 0.56] | 0.43 [0.43, 0.43] | 0.54 [0.43, 0.54] | 0.43 [0.38, 0.54] | 0.55 [0.53, 0.69] | 0.60 [0.58, 0.68] | 0.29 [0.29, 0.31] | 0.12 [0.09, 0.17] | 0.40 [0.40, 0.60] (5 signs) |

**c. Agreement within the main set, and each model's stability.**

| Statistic | Variable level | Feature level |
|---|---|---|
| Kendall's W of the main set [95% CI] | 0.80 [0.78, 0.81] | 0.71 [0.69, 0.73] |
| Mean pairwise Spearman of the main set [95% CI] | 0.73 [0.71, 0.74] | 0.61 [0.59, 0.63] |
| Stability under region resampling: treeroute v1 | 0.99 | 0.98 |
| Stability under region resampling: Ridge | 1.00 | 1.00 |
| Stability under region resampling: random forest | 0.99 | 0.99 |
| Stability under region resampling: LightGBM | 0.99 | 0.99 |
| Stability under region resampling: Tweedie booster | 0.99 | 0.99 |

**d. Variable level: each model's top 10 (share).**

| Rank | treeroute v1 | Ridge | Random forest | LightGBM | Tweedie booster |
|---|---|---|---|---|---|
| 1 | `hist_last` 9.2% | `tsa` 6.7% | `hist_last` 15.9% | `hist_last` 12.8% | `hist_mean` 21.9% |
| 2 | `h_nbr1` 4.8% | `h_nbr_cum` 6.0% | `hist_mean` 9.6% | `hist_mean` 10.6% | `h_yrs_since` 5.6% |
| 3 | `spei` 4.5% | `ao` 5.6% | `spi` 5.1% | `soi` 6.2% | `hist_last` 4.5% |
| 4 | `h_yrs_since` 4.4% | `hist_last` 5.1% | `soi` 4.6% | `spi` 5.0% | `sst_anom_mediterranean` 3.6% |
| 5 | `spi` 4.4% | `h_nbr1` 4.7% | `spei` 4.2% | `h_nbr1` 4.3% | `spei` 3.6% |
| 6 | `hist_mean` 4.2% | `epo` 4.0% | `h_nbr1` 4.0% | `spei` 3.7% | `spi` 3.2% |
| 7 | `h_nbr_cum` 2.5% | `spi` 3.9% | `sst_anom_mediterranean` 2.6% | `h_yrs_since` 3.7% | `sst_anom_atl3` 2.8% |
| 8 | `wbal` 2.4% | `soi` 3.1% | `h_yrs_since` 2.4% | `sst_anom_mediterranean` 3.3% | `sst_anom_iod_west` 2.1% |
| 9 | `deeprec_twsa_k3` 2.3% | `spei` 2.9% | `pdo` 2.0% | `sst_anom_atl3` 3.1% | `h_nbr1` 2.1% |
| 10 | `h_nbr2` 1.9% | `wp` 2.9% | `wp` 1.8% | `sst_anom_iod_west` 2.9% | `pdo` 1.9% |
| Nonzero variables | 99 | 99 | 99 | 99 | 99 |

**e. Feature level: each model's top 10 (share).**

| Rank | treeroute v1 | Ridge | Random forest | LightGBM | Tweedie booster |
|---|---|---|---|---|---|
| 1 | `x__hist_last_1` 6.0% | `x__h_nbr_cum` 4.3% | `x__hist_last_1` 12.5% | `x__hist_last_1` 9.6% | `x__hist_mean_all` 14.8% |
| 2 | `x__h_nbr1` 3.4% | `x__h_nbr1` 3.4% | `x__hist_mean_all` 7.8% | `x__hist_mean_all` 9.2% | `x__h_yrs_since` 4.1% |
| 3 | `x__h_yrs_since` 3.1% | `x__hist_last_1` 3.3% | `x__h_nbr1` 3.2% | `x__soi_max` 4.5% | `x__hist_mean_5` 2.8% |
| 4 | `x__hist_mean_all` 2.7% | `x__ao_max` 3.3% | `x__soi_max` 2.6% | `x__h_nbr1` 3.2% | `x__hist_last_1` 2.8% |
| 5 | `x__h_nbr_cum` 1.8% | `x__tsa_max` 3.3% | `x__h_yrs_since` 1.9% | `x__h_yrs_since` 2.8% | `x__sst_anom_mediterranean_mean` 2.1% |
| 6 | `x__hist_mean_5` 1.6% | `x__epo_mean` 1.7% | `x__sst_anom_mediterranean_mean` 1.7% | `x__sst_anom_mediterranean_mean` 2.2% | `x__sst_anom_atl3_max` 1.8% |
| 7 | `x__h_nbr2` 1.3% | `x__spi_01m_mean` 1.6% | `x__hdi` 1.3% | `x__hist_mean_5` 2.2% | `x__h_nbr1` 1.6% |
| 8 | `x__deeprec_twsa_k3_mean` 1.2% | `x__tsa_mean` 1.6% | `x__pdo_min` 1.3% | `x__sst_anom_atl3_max` 1.6% | `x__h_nbr_cum` 1.4% |
| 9 | `x__sst_anom_atl3_max` 1.0% | `x__sst_anom_atl3_max` 1.5% | `x__sst_anom_global_tropical_mean_min` 1.2% | `x__h_nbr2` 1.4% | `x__pdo_min` 1.3% |
| 10 | `x__sst_anom_mediterranean_mean` 0.9% | `x__wp_max` 1.5% | `x__oni_max` 1.2% | `x__spi_06m_min` 1.4% | `x__iod_mean` 1.1% |
| Nonzero players | 279 | 280 | 279 | 277 | 280 |

**f. Family shares (sums of the variable-level attributions per row).**

| Family | treeroute v1 | Ridge | Random forest | LightGBM | Tweedie booster |
|---|---|---|---|---|---|
| Own history | 29.3% | 12.2% | 36.9% | 35.5% | 46.1% |
| Global indices | 22.5% | 53.8% | 34.1% | 33.6% | 21.8% |
| Local drivers | 48.2% | 34.0% | 29.0% | 30.9% | 32.2% |
| Context and calendar | 0.0% (no context or calendar input) | 0.0% (no context or calendar input) | 0.0% (no context or calendar input) | 0.0% (no context or calendar input) | 0.0% (no context or calendar input) |
| Seasonal normal | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |

Sign agreement: of the players in the union of the two top-10 sets whose sign is determined in both models (the bootstrap 95% interval of the signed mean excludes 0), the share whose signs agree; in brackets, the number of such players ("signs") and, where fewer than 2,000, the number of draws on which the statistic is defined. Undefined: no player qualifies on the full sample.
† The sign agreement's interval is from the independent re-computation of the comparison (two implementations, A and B, that agree; ruling BB1): the comparison script evaluates the sign agreement on the full sample only, so its files hold no interval. The value and its number of signs are the comparison's.
§ Families are sums of variable-level attributions, so at the feature level the family-share distance is the variable-level value repeated (ruling BB2).
Stability (panel c): the mean Spearman of a model's full-sample importances with its own bootstrap replicates; descriptive, not a ceiling on between-model agreement. Nonzero (panels d and e): the players of J to which the model gives a nonzero share.

**Table S3.27 (post hoc).** Coral bleaching, nowcast: agreement of the models' SHAP attributions, every pair at the variable level (a) and at the feature level (b); the main set's agreement and each model's stability (c); each model's top 10 at both levels (d, e) and its family shares (f); and the arcsine-link models' top 10 on their rows with a forecast above 0 (g). Link space. Percentile 95% intervals over 2,000 paired region draws, with the number of finite draws where a statistic is defined on fewer of them. Same-link pairs are comparable; cross-link pairs are shown for completeness and are not comparable in scale or rank. Shares are of a model's total mean absolute SHAP value over J, without intervals, as in the comparison's files. <!-- src: D:/treeroute/analysis/shap_v1/out/coral/lead_0/compare/pairs.parquet, per_lead.json, importance.parquet and families.parquet; D:/treeroute/analysis/shap_v1/verify_v1/A/results.json problems.coral.levels.<level>.pairs (the sign agreement's intervals, ruling BB1); rulings BB1, BB2, BB4, BB5 -->

**a. Variable level: every pair.**

| Pair | Link | Spearman over J | Spearman, top-20 union | Kendall's tau-b | Jaccard top 5 | Jaccard top 10 | RBO, p = 0.9 | RBO, p = 0.95 | Share distance (TV) | Family-share distance (TV) | Sign agreement, top-10 union (signs)† |
|---|---|---|---|---|---|---|---|---|---|---|---|
| treeroute v1 vs Ridge | cross-link (not comparable in scale or rank) | 0.57 [0.40, 0.65] | 0.51 [0.32, 0.62] | 0.39 [0.25, 0.46] | 0.43 [0.43, 0.67] | 0.67 [0.43, 0.82] | 0.57 [0.49, 0.61] | 0.72 [0.67, 0.75] | 0.35 [0.32, 0.39] | 0.16 [0.10, 0.24] | 0.86 [0.71, 0.86] (7 signs) |
| treeroute v1 vs random forest | same-link | 0.52 [0.46, 0.62] | 0.49 [0.43, 0.61] | 0.37 [0.29, 0.47] | 1.00 [0.67, 1.00] | 0.54 [0.54, 0.67] | 0.63 [0.60, 0.72] | 0.75 [0.73, 0.81] | 0.29 [0.22, 0.37] | 0.10 [0.06, 0.17] | 0.88 [0.88, 1.00] (8 signs) |
| treeroute v1 vs LightGBM | same-link | 0.45 [0.29, 0.52] | 0.41 [0.24, 0.49] | 0.31 [0.18, 0.39] | 0.67 [0.43, 0.67] | 0.54 [0.43, 0.67] | 0.62 [0.53, 0.67] | 0.74 [0.68, 0.77] | 0.33 [0.28, 0.39] | 0.13 [0.10, 0.18] | 0.89 [0.78, 0.89] (9 signs) |
| treeroute v1 vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.49 [0.36, 0.57] | 0.46 [0.32, 0.55] | 0.37 [0.25, 0.45] | 0.67 [0.25, 0.67] | 0.67 [0.43, 0.82] | 0.72 [0.56, 0.75] | 0.80 [0.71, 0.82] | 0.27 [0.25, 0.31] | 0.19 [0.16, 0.26] | 0.88 [0.78, 0.88] (8 signs) |
| treeroute v1 vs absolute-error booster | same-link | 0.50 [0.40, 0.57] | 0.48 [0.38, 0.56] | 0.39 [0.28, 0.43] | 0.43 [0.43, 0.67] | 0.43 [0.43, 0.67] | 0.71 [0.64, 0.82] | 0.79 [0.76, 0.85] | 0.23 [0.21, 0.28] | 0.12 [0.10, 0.17] | 0.88 [0.78, 0.88] (8 signs) |
| Ridge vs random forest | cross-link (not comparable in scale or rank) | 0.57 [0.50, 0.65] | 0.39 [0.32, 0.54] | 0.42 [0.36, 0.50] | 0.43 [0.43, 0.43] | 0.43 [0.33, 0.67] | 0.62 [0.53, 0.75] | 0.74 [0.70, 0.82] | 0.35 [0.32, 0.38] | 0.11 [0.05, 0.18] | 0.67 [0.57, 0.78] (9 signs) |
| Ridge vs LightGBM | cross-link (not comparable in scale or rank) | 0.49 [0.40, 0.58] | 0.27 [0.16, 0.43] | 0.35 [0.28, 0.43] | 0.25 [0.25, 0.25] | 0.43 [0.25, 0.54] | 0.57 [0.49, 0.70] | 0.72 [0.67, 0.78] | 0.32 [0.30, 0.37] | 0.04 [0.01, 0.11] | 0.78 [0.71, 0.80] (9 signs) |
| Ridge vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.41 [0.36, 0.54] | 0.25 [0.17, 0.41] | 0.29 [0.25, 0.39] | 0.25 [0.11, 0.25] | 0.43 [0.33, 0.54] | 0.49 [0.42, 0.55] | 0.67 [0.63, 0.70] | 0.36 [0.35, 0.38] | 0.11 [0.07, 0.17] | 0.67 [0.57, 0.75] (9 signs) |
| Ridge vs absolute-error booster | cross-link (not comparable in scale or rank) | 0.34 [0.24, 0.42] | 0.19 [0.05, 0.32] | 0.23 [0.16, 0.30] | 0.25 [0.25, 0.43] | 0.33 [0.25, 0.54] | 0.47 [0.42, 0.50] | 0.65 [0.62, 0.67] | 0.41 [0.39, 0.44] | 0.06 [0.04, 0.12] | 0.78 [0.70, 0.83] (9 signs) |
| random forest vs LightGBM | same-link | 0.96 [0.91, 0.96] | 0.91 [0.82, 0.94] | 0.85 [0.77, 0.87] | 0.67 [0.67, 0.67] | 0.54 [0.54, 0.82] | 0.90 [0.82, 0.93] | 0.93 [0.88, 0.95] | 0.15 [0.13, 0.17] | 0.07 [0.04, 0.10] | 1.00 [1.00, 1.00] (9 signs) |
| random forest vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.81 [0.73, 0.85] | 0.73 [0.61, 0.80] | 0.63 [0.55, 0.68] | 0.67 [0.43, 0.67] | 0.67 [0.54, 0.82] | 0.63 [0.58, 0.71] | 0.77 [0.74, 0.81] | 0.32 [0.28, 0.36] | 0.22 [0.18, 0.26] | 1.00 [1.00, 1.00] (8 signs) |
| random forest vs absolute-error booster | same-link | 0.75 [0.72, 0.82] | 0.68 [0.61, 0.78] | 0.58 [0.53, 0.65] | 0.43 [0.43, 0.67] | 0.54 [0.43, 0.82] | 0.59 [0.57, 0.67] | 0.75 [0.73, 0.79] | 0.32 [0.26, 0.38] | 0.13 [0.10, 0.16] | 1.00 [0.90, 1.00] (10 signs) |
| LightGBM vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.83 [0.75, 0.86] | 0.76 [0.64, 0.81] | 0.66 [0.58, 0.69] | 0.67 [0.67, 1.00] | 0.67 [0.54, 0.82] | 0.65 [0.60, 0.71] | 0.79 [0.75, 0.82] | 0.24 [0.20, 0.28] | 0.15 [0.11, 0.18] | 1.00 [1.00, 1.00] (9 signs) |
| LightGBM vs absolute-error booster | same-link | 0.70 [0.63, 0.76] | 0.62 [0.49, 0.70] | 0.56 [0.47, 0.59] | 0.25 [0.25, 0.43] | 0.43 [0.43, 0.67] | 0.58 [0.52, 0.65] | 0.74 [0.70, 0.78] | 0.31 [0.26, 0.37] | 0.07 [0.04, 0.10] | 1.00 [0.90, 1.00] (10 signs) |
| Tweedie booster vs absolute-error booster | cross-link (not comparable in scale or rank) | 0.70 [0.64, 0.75] | 0.49 [0.42, 0.63] | 0.53 [0.47, 0.59] | 0.25 [0.11, 0.43] | 0.43 [0.43, 0.67] | 0.57 [0.54, 0.71] | 0.73 [0.71, 0.81] | 0.24 [0.21, 0.28] | 0.09 [0.04, 0.13] | 1.00 [1.00, 1.00] (10 signs) |

**b. Feature level: every pair.**

| Pair | Link | Spearman over J | Spearman, top-20 union | Kendall's tau-b | Jaccard top 5 | Jaccard top 10 | RBO, p = 0.9 | RBO, p = 0.95 | Share distance (TV) | Family-share distance (TV)§ | Sign agreement, top-10 union (signs)† |
|---|---|---|---|---|---|---|---|---|---|---|---|
| treeroute v1 vs Ridge | cross-link (not comparable in scale or rank) | 0.41 [0.28, 0.50] | −0.48 [−0.60, −0.19] | 0.27 [0.19, 0.34] | 0.00 [0.00, 0.11] | 0.05 [0.00, 0.25] | 0.15 [0.10, 0.24] | 0.33 [0.27, 0.40] | 0.45 [0.41, 0.50] | 0.16 [0.10, 0.24] | 0.62 [0.50, 0.75] (8 signs) |
| treeroute v1 vs random forest | same-link | 0.56 [0.45, 0.66] | 0.04 [−0.18, 0.41] | 0.41 [0.33, 0.50] | 0.25 [0.11, 0.43] | 0.33 [0.18, 0.54] | 0.34 [0.28, 0.46] | 0.49 [0.43, 0.58] | 0.36 [0.33, 0.40] | 0.10 [0.06, 0.17] | 1.00 [0.92, 1.00] (12 signs) |
| treeroute v1 vs LightGBM | same-link | 0.41 [0.31, 0.51] | −0.25 [−0.42, 0.09] | 0.31 [0.23, 0.39] | 0.11 [0.11, 0.25] | 0.18 [0.05, 0.33] | 0.27 [0.21, 0.39] | 0.41 [0.36, 0.50] | 0.35 [0.32, 0.39] | 0.13 [0.10, 0.18] | 0.90 [0.78, 0.92] (10 signs) |
| treeroute v1 vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.31 [0.28, 0.40] | −0.28 [−0.39, −0.09] | 0.25 [0.22, 0.31] | 0.25 [0.25, 0.43] | 0.18 [0.11, 0.25] | 0.49 [0.30, 0.56] | 0.52 [0.41, 0.57] | 0.30 [0.29, 0.33] | 0.19 [0.16, 0.26] | 0.89 [0.67, 0.91] (9 signs) |
| treeroute v1 vs absolute-error booster | same-link | 0.33 [0.28, 0.39] | 0.10 [−0.11, 0.18] | 0.24 [0.20, 0.29] | 0.25 [0.11, 0.43] | 0.43 [0.18, 0.54] | 0.44 [0.35, 0.54] | 0.52 [0.45, 0.58] | 0.35 [0.32, 0.39] | 0.12 [0.10, 0.17] | 1.00 [0.86, 1.00] (6 signs) |
| Ridge vs random forest | cross-link (not comparable in scale or rank) | 0.40 [0.34, 0.45] | −0.33 [−0.43, −0.28] | 0.26 [0.23, 0.31] | 0.11 [0.00, 0.25] | 0.18 [0.11, 0.25] | 0.22 [0.18, 0.28] | 0.37 [0.34, 0.41] | 0.50 [0.48, 0.54] | 0.11 [0.05, 0.18] | 0.80 [0.64, 0.88] (10 signs) |
| Ridge vs LightGBM | cross-link (not comparable in scale or rank) | 0.32 [0.28, 0.40] | −0.50 [−0.57, −0.37] | 0.21 [0.18, 0.27] | 0.11 [0.00, 0.25] | 0.11 [0.11, 0.18] | 0.19 [0.16, 0.27] | 0.34 [0.32, 0.40] | 0.49 [0.46, 0.54] | 0.04 [0.01, 0.11] | 0.70 [0.50, 0.82] (10 signs) |
| Ridge vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.21 [0.14, 0.30] | −0.48 [−0.59, −0.37] | 0.14 [0.08, 0.19] | 0.00 [0.00, 0.11] | 0.11 [0.00, 0.18] | 0.12 [0.10, 0.18] | 0.28 [0.26, 0.33] | 0.51 [0.48, 0.54] | 0.11 [0.07, 0.17] | 0.60 [0.50, 0.67] (10 signs) |
| Ridge vs absolute-error booster | cross-link (not comparable in scale or rank) | 0.21 [0.15, 0.28] | −0.60 [−0.66, −0.53] | 0.13 [0.09, 0.18] | 0.11 [0.00, 0.11] | 0.05 [0.05, 0.11] | 0.13 [0.10, 0.18] | 0.28 [0.26, 0.31] | 0.55 [0.53, 0.58] | 0.06 [0.04, 0.12] | 0.67 [0.50, 0.75] (6 signs) |
| random forest vs LightGBM | same-link | 0.88 [0.85, 0.89] | 0.36 [0.18, 0.51] | 0.73 [0.69, 0.74] | 0.43 [0.11, 0.43] | 0.43 [0.25, 0.54] | 0.62 [0.53, 0.68] | 0.71 [0.64, 0.74] | 0.21 [0.19, 0.23] | 0.07 [0.04, 0.10] | 1.00 [1.00, 1.00] (11 signs) |
| random forest vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.57 [0.54, 0.63] | −0.01 [−0.19, 0.11] | 0.42 [0.40, 0.47] | 0.11 [0.00, 0.25] | 0.25 [0.11, 0.33] | 0.31 [0.24, 0.37] | 0.45 [0.40, 0.50] | 0.39 [0.36, 0.41] | 0.22 [0.18, 0.26] | 1.00 [1.00, 1.00] (11 signs) |
| random forest vs absolute-error booster | same-link | 0.57 [0.53, 0.62] | −0.13 [−0.29, −0.01] | 0.47 [0.43, 0.50] | 0.00 [0.00, 0.11] | 0.18 [0.05, 0.25] | 0.25 [0.21, 0.28] | 0.43 [0.40, 0.46] | 0.41 [0.37, 0.46] | 0.13 [0.10, 0.16] | 1.00 [1.00, 1.00] (11 signs) |
| LightGBM vs Tweedie booster | cross-link (not comparable in scale or rank) | 0.70 [0.66, 0.73] | 0.24 [0.03, 0.34] | 0.54 [0.50, 0.56] | 0.25 [0.11, 0.43] | 0.43 [0.25, 0.54] | 0.51 [0.38, 0.53] | 0.60 [0.52, 0.63] | 0.27 [0.25, 0.31] | 0.15 [0.11, 0.18] | 1.00 [1.00, 1.00] (10 signs) |
| LightGBM vs absolute-error booster | same-link | 0.50 [0.44, 0.55] | −0.28 [−0.44, −0.14] | 0.39 [0.34, 0.43] | 0.11 [0.11, 0.25] | 0.33 [0.11, 0.33] | 0.33 [0.26, 0.41] | 0.48 [0.42, 0.53] | 0.37 [0.32, 0.43] | 0.07 [0.04, 0.10] | 1.00 [0.88, 1.00] (7 signs) |
| Tweedie booster vs absolute-error booster | cross-link (not comparable in scale or rank) | 0.66 [0.58, 0.71] | −0.06 [−0.19, 0.05] | 0.51 [0.44, 0.56] | 0.11 [0.11, 0.25] | 0.33 [0.18, 0.43] | 0.40 [0.32, 0.49] | 0.54 [0.48, 0.58] | 0.31 [0.28, 0.35] | 0.09 [0.04, 0.13] | 1.00 [1.00, 1.00] (9 signs) |

**c. Agreement within the main set, and each model's stability.**

| Statistic | Variable level | Feature level |
|---|---|---|
| Kendall's W of the main set [95% CI] | 0.73 [0.69, 0.76] | 0.65 [0.63, 0.69] |
| Mean pairwise Spearman of the main set [95% CI] | 0.65 [0.59, 0.68] | 0.54 [0.50, 0.58] |
| Stability under region resampling: treeroute v1 | 0.98 | 0.97 |
| Stability under region resampling: Ridge | 0.97 | 0.99 |
| Stability under region resampling: random forest | 0.98 | 0.99 |
| Stability under region resampling: LightGBM | 0.97 | 0.99 |
| Stability under region resampling: Tweedie booster | 0.98 | 0.99 |
| Stability under region resampling: absolute-error booster | 0.98 | 0.98 |

**d. Variable level: each model's top 10 (share).**

| Rank | treeroute v1 | Ridge | Random forest | LightGBM | Tweedie booster | Absolute-error booster |
|---|---|---|---|---|---|---|
| 1 | `nino34a` 15.3% | `slope` 15.1% | `n_above_mmm1` 21.7% | `n_above_mmm1` 21.0% | `nino34a` 13.1% | `hs` 14.2% |
| 2 | `hs` 12.9% | `n_above_mmm1` 14.6% | `dhw` 14.9% | `dhw` 11.2% | `calendar` 10.0% | `nino34a` 13.4% |
| 3 | `dhw` 11.6% | `dhw` 10.3% | `mhw_days` 11.2% | `nino34a` 9.0% | `n_above_mmm1` 8.1% | `dhw` 9.2% |
| 4 | `n_above_mmm1` 10.1% | `cool` 10.0% | `nino34a` 10.1% | `mhw_days` 9.0% | `mhw_days` 8.1% | `mhw_icum` 6.4% |
| 5 | `mhw_days` 6.7% | `hs` 5.8% | `hs` 9.0% | `calendar` 8.4% | `hs` 5.5% | `days_since_max_hs` 6.4% |
| 6 | `n_above_mmm` 6.0% | `mhw_days` 4.2% | `n_above_mmm` 4.4% | `n_above_mmm` 4.6% | `cyc_mindist` 5.2% | `mhw_days` 6.4% |
| 7 | `cool` 5.9% | `mhw_durmax` 3.8% | `cool` 3.6% | `hs` 3.9% | `cool` 5.2% | `cool` 4.9% |
| 8 | `mhw_icum` 4.4% | `mhw_icum` 3.4% | `calendar` 3.1% | `days_since_max_hs` 3.5% | `dhw` 4.8% | `calendar` 4.7% |
| 9 | `mhw_durmax` 3.0% | `n_above_mmm` 3.3% | `cyc_maxw` 2.7% | `cyc_mindist` 3.1% | `n_above_mmm` 4.3% | `ctx:mmm` 4.0% |
| 10 | `cyc_mindist` 2.8% | `mhw_nev` 3.1% | `ctx:mmm` 2.2% | `mhw_nev` 3.1% | `mhw_thr_gap` 3.9% | `ctx:abslat` 3.7% |
| Nonzero variables | 25 | 25 | 25 | 25 | 25 | 25 |

**e. Feature level: each model's top 10 (share).**

| Rank | treeroute v1 | Ridge | Random forest | LightGBM | Tweedie booster | Absolute-error booster |
|---|---|---|---|---|---|---|
| 1 | `x__nino34a_lag6` 6.3% | `x__cool_90` 12.0% | `x__n_above_mmm1_90` 11.4% | `x__n_above_mmm1_90` 10.6% | `x__nino34a_lag6` 5.3% | `x__hs_max_56` 9.1% |
| 2 | `x__nino34a_lag3` 4.2% | `x__dhw_84` 7.0% | `x__hs_max_30` 6.2% | `c__ctx_doy_sin` 5.1% | `c__ctx_doy_sin` 5.1% | `x__nino34a_lag6` 7.7% |
| 3 | `x__nino34a_lag9` 3.9% | `x__slope_90` 6.6% | `x__dhw_90` 6.1% | `x__nino34a_lag6` 5.0% | `x__nino34a_lag3` 4.9% | `x__mhw_icum_90` 5.4% |
| 4 | `x__mhw_icum_90` 3.7% | `x__cool_84` 6.5% | `x__nino34a_lag3` 5.2% | `x__n_above_mmm1_84` 4.6% | `c__ctx_doy_cos` 4.3% | `x__days_since_max_hs` 5.4% |
| 5 | `x__hs_max_30` 3.4% | `x__n_above_mmm1_90` 5.2% | `x__n_above_mmm1_84` 4.5% | `x__dhw_90` 3.7% | `x__mhw_days_90` 3.2% | `x__dhw_84` 4.8% |
| 6 | `x__mhw_days_90` 2.7% | `x__cool_56` 4.4% | `x__mhw_days_90` 4.5% | `c__ctx_doy_cos` 3.1% | `x__mhw_thr_gap` 3.2% | `x__mhw_days_90` 4.1% |
| 7 | `x__mhw_durmax_365` 2.5% | `x__n_above_mmm1_84` 4.1% | `x__mhw_days_365` 3.8% | `x__mhw_days_90` 3.1% | `x__mhw_days_365` 3.0% | `c__ctx_mmm` 3.4% |
| 8 | `x__hs_max_56` 2.5% | `x__hs_max_84` 3.4% | `x__mhw_days_30` 3.3% | `x__days_since_max_hs` 3.0% | `c__ctx_mmm` 3.0% | `c__ctx_abslat` 3.2% |
| 9 | `x__dhw_56` 2.4% | `x__n_above_mmm_84` 2.6% | `x__dhw_84` 3.2% | `x__nino34a_lag3` 2.9% | `x__slope_90` 2.9% | `x__nino34a_lag3` 2.9% |
| 10 | `x__dhw_84` 2.4% | `x__hs_max_90` 2.5% | `x__nino34a_lag9` 3.1% | `x__mhw_days_30` 2.9% | `x__n_above_mmm1_90` 2.8% | `c__ctx_doy_cos` 2.9% |
| Nonzero players | 68 | 68 | 68 | 67 | 68 | 68 |

**f. Family shares (sums of the variable-level attributions per row).**

| Family | treeroute v1 | Ridge | Random forest | LightGBM | Tweedie booster | Absolute-error booster |
|---|---|---|---|---|---|---|
| Own history | 0.0% (no own-history input) | 0.0% (no own-history input) | 0.0% (no own-history input) | 0.0% (no own-history input) | 0.0% (no own-history input) | 0.0% (no own-history input) |
| Global indices | 22.2% | 13.2% | 12.2% | 12.6% | 21.5% | 19.4% |
| Local drivers | 77.6% | 70.6% | 81.5% | 74.6% | 59.6% | 68.2% |
| Context and calendar | 0.2% | 16.2% | 6.4% | 12.8% | 18.9% | 12.4% |
| Seasonal normal | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |

**g. Arcsine-link models, rows with a forecast above 0: top 10 (share).**

| Rank | treeroute v1 | Random forest | LightGBM | Absolute-error booster |
|---|---|---|---|---|
| 1 | `nino34a` 15.3% | `n_above_mmm1` 21.7% | `n_above_mmm1` 21.0% | `hs` 14.2% |
| 2 | `hs` 12.9% | `dhw` 14.9% | `dhw` 11.2% | `nino34a` 13.4% |
| 3 | `dhw` 11.5% | `mhw_days` 11.2% | `nino34a` 9.0% | `dhw` 9.2% |
| 4 | `n_above_mmm1` 10.1% | `nino34a` 10.1% | `mhw_days` 9.0% | `days_since_max_hs` 6.4% |
| 5 | `mhw_days` 6.7% | `hs` 9.0% | `calendar` 8.4% | `mhw_icum` 6.4% |
| 6 | `n_above_mmm` 6.0% | `n_above_mmm` 4.4% | `n_above_mmm` 4.6% | `mhw_days` 6.4% |
| 7 | `cool` 5.9% | `cool` 3.6% | `hs` 3.9% | `cool` 4.9% |
| 8 | `mhw_icum` 4.4% | `calendar` 3.1% | `days_since_max_hs` 3.5% | `calendar` 4.7% |
| 9 | `mhw_durmax` 3.0% | `cyc_maxw` 2.7% | `cyc_mindist` 3.1% | `ctx:mmm` 4.0% |
| 10 | `cyc_mindist` 2.8% | `ctx:mmm` 2.2% | `mhw_nev` 3.1% | `ctx:abslat` 3.7% |
| Rows with a forecast above 0 | 973 | 1,000 | 995 | 983 |

Sign agreement: of the players in the union of the two top-10 sets whose sign is determined in both models (the bootstrap 95% interval of the signed mean excludes 0), the share whose signs agree; in brackets, the number of such players ("signs") and, where fewer than 2,000, the number of draws on which the statistic is defined. Undefined: no player qualifies on the full sample.
† The sign agreement's interval is from the independent re-computation of the comparison (two implementations, A and B, that agree; ruling BB1): the comparison script evaluates the sign agreement on the full sample only, so its files hold no interval. The value and its number of signs are the comparison's.
§ Families are sums of variable-level attributions, so at the feature level the family-share distance is the variable-level value repeated (ruling BB2).
Stability (panel c): the mean Spearman of a model's full-sample importances with its own bootstrap replicates; descriptive, not a ceiling on between-model agreement. Nonzero (panels d and e): the players of J to which the model gives a nonzero share.
Panel g: each arcsine-link model's variable-level shares on its rows with a forecast above 0, over every variable of the problem, in the comparison file's order.

## Supplement S3.13: treeroute v1's B1 sensitivity (kept apart from the main set)

**Table S3.28 (post hoc; sensitivity).** treeroute v1's B1 sensitivity, nowcast: the pair (main run, B1 run) at the variable level (a) and the feature level (b). B1 explains the same 1,000 sample rows against all of each location's router fit rows at or before the cut, not only those of the same calendar month (B2), so the month and the seasonal normal can take credit. treeroute v1 only; B1 is never pooled with the main set: it enters no Kendall's W, consensus or main-text row and is compared with no rival. J is the pair's own (the players to which either run gives more than 10⁻¹² of its total), so Spearman over J, Kendall's tau-b and RBO are not read against the main pairs' values number for number. Every number is from the independent re-computation (two implementations that agree); percentile 95% intervals over the problem's 2,000 saved region draws; counts without intervals. Coral bleaching: B1 is not defined; forest loss: the identity check of Table S3.30. <!-- src: D:/treeroute/analysis/shap_v1/verify_v1/A/results.json b1.<problem>.<level>.pair_main_b1 and b1.<problem>.<level>.importance.n_nonzero; rulings BA3, BB2 -->

**a. Variable level: the pair (main run, B1 run).**

| Statistic | PM2.5 | NDVI | Burned fraction |
|---|---|---|---|
| Variables in the pair's J | 91 | 96 | 96 |
| Nonzero in the B1 run | 91 | 96 | 96 |
| Spearman over J | 0.84 [0.83, 0.86] | 0.84 [0.83, 0.85] | 0.84 [0.78, 0.87] |
| Spearman, top-20 union | 0.45 [0.35, 0.51] | 0.17 [0.06, 0.24] | 0.39 [0.25, 0.50] |
| Kendall's tau-b | 0.73 [0.72, 0.75] | 0.77 [0.76, 0.79] | 0.73 [0.66, 0.76] |
| Jaccard top 5 | 0.43 [0.11, 0.43] | 0.43 [0.43, 0.43] | 0.25 [0.11, 0.67] |
| Jaccard top 10 | 0.54 [0.33, 0.54] | 0.25 [0.25, 0.33] | 0.54 [0.33, 0.82] |
| RBO, p = 0.9 | 0.57 [0.47, 0.58] | 0.46 [0.43, 0.55] | 0.46 [0.42, 0.61] |
| RBO, p = 0.95 | 0.65 [0.59, 0.66] | 0.60 [0.58, 0.65] | 0.59 [0.56, 0.68] |
| Share distance (TV) | 0.45 [0.42, 0.47] | 0.40 [0.38, 0.43] | 0.54 [0.41, 0.64] |
| Family-share distance (TV) | 0.70 [0.67, 0.73] | 0.49 [0.45, 0.53] | 0.81 [0.72, 0.87] |
| Sign agreement, top-10 union | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| Signs determined in both runs / of those, agreeing | 3 / 3 | 3 / 3 | 2 / 2 |

**b. Feature level: the pair (main run, B1 run).**

| Statistic | PM2.5 | NDVI | Burned fraction |
|---|---|---|---|
| Players in the pair's J | 105 | 482 | 113 |
| Nonzero in the B1 run | 105 | 482 | 113 |
| Spearman over J | 0.84 [0.82, 0.86] | 0.87 [0.86, 0.88] | 0.82 [0.75, 0.86] |
| Spearman, top-20 union | 0.35 [0.25, 0.43] | 0.06 [−0.02, 0.15] | 0.26 [0.06, 0.37] |
| Kendall's tau-b | 0.72 [0.71, 0.75] | 0.76 [0.74, 0.77] | 0.72 [0.64, 0.75] |
| Jaccard top 5 | 0.25 [0.11, 0.43] | 0.43 [0.25, 0.43] | 0.43 [0.25, 0.67] |
| Jaccard top 10 | 0.54 [0.43, 0.67] | 0.33 [0.25, 0.43] | 0.54 [0.25, 0.54] |
| Jaccard top 20 | – | 0.33 [0.29, 0.43] | – |
| RBO, p = 0.9 | 0.50 [0.48, 0.56] | 0.48 [0.43, 0.51] | 0.57 [0.43, 0.59] |
| RBO, p = 0.95 | 0.59 [0.57, 0.64] | 0.54 [0.51, 0.57] | 0.63 [0.52, 0.65] |
| Share distance (TV) | 0.43 [0.41, 0.46] | 0.34 [0.32, 0.36] | 0.53 [0.40, 0.63] |
| Family-share distance (TV)§ | 0.70 [0.67, 0.73] | 0.49 [0.45, 0.53] | 0.81 [0.72, 0.87] |
| Sign agreement, top-10 union | 1.00 [0.67, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| Signs determined in both runs / of those, agreeing | 2 / 2 | 4 / 4 | 1 / 1 |

–: not defined, because the pair's J has fewer than 200 players (the top-20 Jaccard is given only from 200 players).
§ Families are sums of variable-level attributions, so at the feature level the family-share distance is the variable-level value repeated (ruling BB2; an exception to the rule that B1's numbers follow the main comparison's choices).

**Table S3.29 (post hoc; sensitivity).** treeroute v1's B1 run, nowcast: family shares [95% CI] (a), top 3 and own-history share (b), and top 10 at both levels (c, d; no interval for a top-k list). Shares are of the B1 run's total mean absolute SHAP value over the pair's J. From the independent re-computation (two implementations that agree). <!-- src: D:/treeroute/analysis/shap_v1/verify_v1/A/results.json b1.<problem>.variable.families, b1.<problem>.variable.top3, b1.<problem>.variable.own_history_share, b1.<problem>.<level>.top10; rulings BA3, BB5 -->

**a. Variable level: the B1 run's family shares [95% CI].**

| Family | PM2.5 | NDVI | Burned fraction |
|---|---|---|---|
| Own history | 5.9% [5.0%, 6.7%] | 7.2% [6.2%, 8.3%] | 2.2% [1.4%, 3.4%] |
| Global indices | 8.1% [7.2%, 9.1%] | 1.7% [1.6%, 2.0%] | 4.1% [2.8%, 6.6%] |
| Local drivers | 15.7% [14.0%, 17.5%] | 42.0% [38.8%, 45.6%] | 12.6% [8.2%, 19.0%] |
| Context and calendar | 0.1% [0.1%, 0.1%] | 4.8% [4.2%, 5.4%] | <0.1% [<0.1%, <0.1%] |
| Seasonal normal | 70.3% [67.4%, 73.1%] | 44.3% [40.5%, 48.0%] | 81.1% [71.6%, 87.3%] |

**b. Variable level: the B1 run's top 3 and own-history share.**

| Quantity | PM2.5 | NDVI | Burned fraction |
|---|---|---|---|
| Top 3 (share) | `normal` 44.5%, `hist_last` 3.0%, `wbal` 2.4% | `normal` 32.1%, `aet_total_mm` 4.0%, `hist_last` 3.8% | `normal` 54.2%, `era5l_str` 1.5%, `wbal` 1.5% |
| Own-history share [95% CI] | 0.06 [0.05, 0.07] | 0.07 [0.06, 0.08] | 0.02 [0.01, 0.03] |

**c. Variable level: the B1 run's top 10 (share).**

| Rank | PM2.5 | NDVI | Burned fraction |
|---|---|---|---|
| 1 | `normal` 44.5% | `normal` 32.1% | `normal` 54.2% |
| 2 | `hist_last` 3.0% | `aet_total_mm` 4.0% | `era5l_str` 1.5% |
| 3 | `wbal` 2.4% | `hist_last` 3.8% | `wbal` 1.5% |
| 4 | `era5l_str` 1.8% | `era5l_slhf` 3.8% | `hist_mean` 1.4% |
| 5 | `era5l_sshf` 1.7% | `calendar` 3.5% | `deeprec_twsa` 1.4% |
| 6 | `climate_water_deficit_mm` 1.6% | `era5l_d2m` 3.0% | `tslf_months` 1.3% |
| 7 | `total_ref_ET_mm` 1.5% | `total_ref_ET_mm` 2.8% | `spei` 1.1% |
| 8 | `sst_anom_mediterranean` 1.4% | `hist_mean` 2.7% | `rmin_pct` 1.1% |
| 9 | `spei` 1.4% | `sph_kgkg` 2.5% | `era5l_sshf` 1.0% |
| 10 | `spi` 1.3% | `mean_temp_C` 2.4% | `spi` 1.0% |

**d. Feature level: the B1 run's top 10 (share).**

| Rank | PM2.5 | NDVI | Burned fraction |
|---|---|---|---|
| 1 | `normal` 43.0% | `normal` 23.6% | `normal` 52.6% |
| 2 | `x__hist_last_1` 2.6% | `x__hist_last_1` 2.2% | `x__era5l_str` 1.4% |
| 3 | `x__wbal_roll3` 1.8% | `x__era5l_slhf_lag1` 1.9% | `x__deeprec_twsa` 1.4% |
| 4 | `x__era5l_str` 1.7% | `x__aet_total_mm_roll3` 1.7% | `x__tslf_months` 1.3% |
| 5 | `x__era5l_sshf` 1.6% | `x__era5l_d2m` 1.6% | `x__wbal_roll3` 1.0% |
| 6 | `x__climate_water_deficit_mm` 1.6% | `c__ctx:sin1` 1.3% | `x__rmin_pct` 1.0% |
| 7 | `x__V07_total_ref_ET_mm` 1.4% | `x__hist_mean_12` 1.3% | `x__era5l_sshf` 1.0% |
| 8 | `x__sst_anom_mediterranean` 1.4% | `c__ctx:sin2` 1.2% | `x__hist_mean_60` 0.9% |
| 9 | `x__aet_total_mm` 1.3% | `x__sph_kgkg` 1.1% | `x__V05_mean_vpd_kPa` 0.9% |
| 10 | `x__pdo` 1.3% | `x__era5l_slhf` 1.1% | `x__V03_max_daily_precip_mm` 0.9% |

Under B1 the month and the seasonal normal can take credit; under B2 they are exactly 0 on these three problems. The own-history share is the own-history family's share. Each B1 player's importance, share and signed mean, with its interval, is in the re-computation's results file (verify_v1/A/results.json, key b1).

**Table S3.30 (post hoc; sensitivity).** treeroute v1's B1 runs: background pairs and seconds, from each run's log (a), and forest loss's identity check (b). Forest loss is annual, so its B1 background equals its main run's, and its B1 run must repeat the main run exactly. <!-- src: D:/treeroute/analysis/shap_v1/logs/tr_shap_<problem>_lead0.log (the B1 run's set-up and "done in" lines); D:/treeroute/analysis/shap_v1/verify_v1/A/results.json b1.defo.identity; rulings BA3 -->

**a. Background pairs and seconds of each B1 run, from its log.**

| Problem | Background pairs | Total seconds | Tree-SHAP seconds |
|---|---|---|---|
| PM2.5 | 203,963 | 17,890.4 | 17,883.2 |
| NDVI | 201,768 | 11,883.1 | 11,871.8 |
| Burned fraction | 187,186 | 2,636.6 | 2,631.6 |
| Forest loss | 16,000 | 465.9 | 464.3 |

**b. Forest loss: the B1 run against the main run.**

| Check | Result |
|---|---|
| Largest absolute difference of the SHAP values, feature level (every row and player) | 0 |
| Largest absolute difference of the SHAP values, variable level (every row and variable) | 0 |
| Rows, main run / B1 run | 1,000 / 1,000 |
| Players, main run / B1 run | 309 / 309 |
| Variables, main run / B1 run | 121 / 121 |
| Same rows / players / variables | yes / yes / yes |

Coral bleaching: B1 is not defined (its router reads a pool of other sites' survey visits), so it has no B1 run.
The identity check matches rows by their sample row and players and variables by name; it is from the independent re-computation (two implementations that agree), and it held exactly, so the B1 numbers of PM2.5, NDVI and burned fraction are reported (Tables S3.28 and S3.29).
