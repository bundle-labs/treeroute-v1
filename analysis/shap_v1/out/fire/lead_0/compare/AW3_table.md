# AW3: disagreement of SHAP importances, fire lead 0 (post hoc, ruling AK)

1000 rows in 40 regions; link space; percentile 95% intervals from 2000 paired region draws. Same-link pairs are comparable; cross-link pairs are shown for completeness and are not comparable in scale or rank. A rival declined by its own guard is labelled and kept out of W, the consensus and the main row (D6).

Models and links: rival_lgbm (log_c|c=0.012987012987|ub=1); rival_lgbm_tweedie (log_mu|c=0.012987012987|ub=1); rival_rf (log_c|c=0.012987012987|ub=1); rival_ridge (log_c|c=0.012987012987|ub=1, declined by its guard); treeroute (arcsine|c=0.012987012987|ub=1)

Main set: treeroute

## variable level (117 players, 94 active; structural zeros: CTI, awc_cm3cm3, bulk_density_gcm3, calendar, cec_cmolkg, clay_pct, coarse_fragments_pct, conflict_deaths, conflict_events, ctx:lat, dist_to_coast_km, elevation_m, hand_m, irrigation_pct_gmia, nitrogen_gkg, normal, sand_pct, silt_pct, slope_deg, soil_organic_carbon_gkg, soil_ph, southness, upstream_area_km2)

| Pair | label | spearman | spearman_top20_union | kendall_tau_b | jaccard_top5 | jaccard_top10 | rbo_p0.9 | rbo_p0.95 | tvd | tvd_family | sign_agreement_top10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rival_lgbm vs rival_lgbm_tweedie | cross-link (not comparable in scale or rank) | 0.75 [0.68, 0.79] | 0.11 [-0.02, 0.25] | 0.57 [0.51, 0.61] | 0.43 [0.25, 0.43] | 0.25 [0.18, 0.43] | 0.56 [0.52, 0.60] | 0.60 [0.56, 0.63] | 0.29 [0.27, 0.34] | 0.11 [0.09, 0.15] | 0.75 (4 signs) |
| rival_lgbm vs rival_rf | same-link | 0.87 [0.82, 0.89] | 0.73 [0.50, 0.79] | 0.71 [0.66, 0.74] | 0.67 [0.67, 1.00] | 0.67 [0.43, 0.82] | 0.85 [0.77, 0.87] | 0.82 [0.77, 0.84] | 0.14 [0.12, 0.18] | 0.09 [0.06, 0.14] | 1.00 (4 signs) |
| rival_lgbm vs rival_ridge | same-link; raw model, declined by its guard: rival_ridge | 0.59 [0.53, 0.64] | 0.18 [0.04, 0.24] | 0.44 [0.39, 0.47] | 0.43 [0.43, 0.67] | 0.33 [0.25, 0.43] | 0.67 [0.57, 0.68] | 0.64 [0.58, 0.66] | 0.34 [0.32, 0.36] | 0.02 [0.01, 0.09] | 0.60 (5 signs) |
| rival_lgbm vs treeroute | cross-link (not comparable in scale or rank) | 0.68 [0.62, 0.71] | 0.05 [-0.09, 0.17] | 0.52 [0.46, 0.54] | 0.67 [0.43, 0.67] | 0.33 [0.25, 0.43] | 0.54 [0.44, 0.57] | 0.58 [0.51, 0.60] | 0.34 [0.32, 0.38] | 0.06 [0.01, 0.12] | 1.00 (1 signs) |
| rival_lgbm_tweedie vs rival_rf | cross-link (not comparable in scale or rank) | 0.71 [0.65, 0.77] | -0.01 [-0.16, 0.15] | 0.53 [0.47, 0.58] | 0.25 [0.25, 0.25] | 0.33 [0.18, 0.43] | 0.52 [0.48, 0.57] | 0.56 [0.52, 0.60] | 0.31 [0.28, 0.35] | 0.18 [0.15, 0.23] | 1.00 (4 signs) |
| rival_lgbm_tweedie vs rival_ridge | cross-link (not comparable in scale or rank); raw model, declined by its guard: rival_ridge | 0.68 [0.65, 0.71] | 0.16 [0.06, 0.25] | 0.50 [0.48, 0.53] | 0.25 [0.25, 0.43] | 0.43 [0.33, 0.43] | 0.59 [0.55, 0.67] | 0.62 [0.59, 0.66] | 0.37 [0.36, 0.40] | 0.12 [0.07, 0.16] | 0.83 (6 signs) |
| rival_lgbm_tweedie vs treeroute | cross-link (not comparable in scale or rank) | 0.61 [0.52, 0.67] | -0.14 [-0.26, -0.01] | 0.44 [0.37, 0.49] | 0.25 [0.11, 0.25] | 0.25 [0.11, 0.33] | 0.37 [0.26, 0.43] | 0.45 [0.39, 0.49] | 0.27 [0.26, 0.30] | 0.09 [0.06, 0.12] | 0.00 (1 signs) |
| rival_rf vs rival_ridge | same-link; raw model, declined by its guard: rival_ridge | 0.70 [0.66, 0.72] | 0.22 [-0.04, 0.26] | 0.53 [0.49, 0.55] | 0.43 [0.43, 0.43] | 0.54 [0.18, 0.54] | 0.71 [0.55, 0.72] | 0.69 [0.58, 0.70] | 0.31 [0.29, 0.34] | 0.11 [0.07, 0.16] | 1.00 (3 signs) |
| rival_rf vs treeroute | cross-link (not comparable in scale or rank) | 0.69 [0.61, 0.72] | 0.03 [-0.12, 0.17] | 0.52 [0.46, 0.55] | 0.67 [0.43, 0.67] | 0.25 [0.25, 0.43] | 0.53 [0.44, 0.57] | 0.57 [0.50, 0.60] | 0.33 [0.31, 0.36] | 0.10 [0.07, 0.17] | 1.00 (1 signs) |
| rival_ridge vs treeroute | cross-link (not comparable in scale or rank); raw model, declined by its guard: rival_ridge | 0.47 [0.41, 0.52] | -0.15 [-0.31, -0.15] | 0.32 [0.28, 0.37] | 0.43 [0.25, 0.43] | 0.18 [0.18, 0.25] | 0.42 [0.29, 0.46] | 0.45 [0.37, 0.48] | 0.50 [0.48, 0.52] | 0.08 [0.02, 0.14] | nan (0 signs) |

Kendall's W (main set) = nan [nan, nan]; mean pairwise Spearman (main set) = nan [nan, nan].
Stability under region resampling (mean Spearman of a model's full-sample importances with its own bootstrap replicates; descriptive, not a ceiling on between-model agreement): rival_lgbm 0.98, rival_lgbm_tweedie 0.99, rival_rf 0.98, rival_ridge 0.99, treeroute 0.97

- rival_lgbm top-10 (87 nonzero): spi 14.8%; hist_mean 7.9%; tslf_months 7.4%; spei 4.4%; sst_anom_atl3 3.6%; epo 3.2%; tni 2.5%; wbal_mm 2.4%; wbal 2.0%; hist_last 1.8%
- rival_lgbm_tweedie top-10 (94 nonzero): spi 8.9%; spei 7.2%; sst_anom_atl3 3.6%; nbr75km 2.8%; precip_seasonality 2.5%; nbr25km 2.3%; nao 2.2%; wbal 2.2%; sst_anom_coral_sea 2.1%; sst_anom_mediterranean 2.0%
- rival_rf top-10 (94 nonzero): spi 16.7%; hist_mean 10.2%; tslf_months 7.3%; spei 4.6%; wbal_mm 3.2%; hist_last 2.0%; sst_anom_coral_sea 1.8%; sst_anom_atl3 1.7%; sst_anom_mediterranean 1.6%; tni 1.5%
- rival_ridge top-10 (94 nonzero): spi 24.2%; hist_mean 7.1%; spei 7.1%; sst_anom_coral_sea 6.4%; n_burns 3.8%; sst_anom_atl3 3.8%; hist_last 3.7%; nao 2.9%; sst_anom_iod_east 2.5%; sst_anom_mediterranean 2.3%
- treeroute top-10 (94 nonzero): hist_mean 4.0%; spei 3.3%; tslf_months 3.2%; spi 3.0%; era5l_str 2.8%; deeprec_twsa 2.7%; ao 2.3%; wbal 2.3%; grace_lwe 1.9%; nbr25km 1.8%

## feature level (134 players, 111 active; structural zeros: c__ctx:lat, c__ctx:month, normal, x__V25_elevation_m, x__V26_slope_deg, x__V27_southness, x__V28_CTI, x__awc_cm3cm3, x__bulk_density_gcm3, x__cec_cmolkg, x__clay_pct, x__coarse_fragments_pct, x__conflict_deaths, x__conflict_events, x__dist_to_coast_km, x__hand_m, x__irrigation_pct_gmia, x__nitrogen_gkg, x__sand_pct, x__silt_pct, x__soil_organic_carbon_gkg, x__soil_ph, x__upstream_area_km2)

| Pair | label | spearman | spearman_top20_union | kendall_tau_b | jaccard_top5 | jaccard_top10 | rbo_p0.9 | rbo_p0.95 | tvd | sign_agreement_top10 |
|---|---|---|---|---|---|---|---|---|---|---|
| rival_lgbm vs rival_lgbm_tweedie | cross-link (not comparable in scale or rank) | 0.67 [0.62, 0.72] | -0.13 [-0.21, -0.03] | 0.51 [0.46, 0.55] | 0.25 [0.11, 0.25] | 0.33 [0.18, 0.33] | 0.49 [0.33, 0.52] | 0.52 [0.44, 0.55] | 0.32 [0.30, 0.37] | 1.00 (2 signs) |
| rival_lgbm vs rival_rf | same-link | 0.86 [0.82, 0.88] | 0.68 [0.54, 0.77] | 0.70 [0.66, 0.73] | 0.67 [0.67, 1.00] | 0.54 [0.43, 0.82] | 0.78 [0.71, 0.87] | 0.78 [0.73, 0.83] | 0.15 [0.14, 0.19] | 1.00 (4 signs) |
| rival_lgbm vs rival_ridge | same-link; raw model, declined by its guard: rival_ridge | 0.55 [0.50, 0.61] | 0.16 [0.04, 0.25] | 0.40 [0.36, 0.45] | 0.43 [0.25, 0.67] | 0.43 [0.33, 0.54] | 0.57 [0.51, 0.65] | 0.58 [0.54, 0.62] | 0.36 [0.35, 0.39] | 0.75 (4 signs) |
| rival_lgbm vs treeroute | cross-link (not comparable in scale or rank) | 0.58 [0.51, 0.63] | -0.37 [-0.48, -0.29] | 0.42 [0.37, 0.47] | 0.11 [0.00, 0.11] | 0.11 [0.05, 0.18] | 0.25 [0.13, 0.36] | 0.34 [0.25, 0.39] | 0.36 [0.35, 0.41] | nan (0 signs) |
| rival_lgbm_tweedie vs rival_rf | cross-link (not comparable in scale or rank) | 0.67 [0.62, 0.72] | -0.06 [-0.21, 0.05] | 0.50 [0.46, 0.54] | 0.11 [0.11, 0.25] | 0.25 [0.18, 0.43] | 0.49 [0.32, 0.51] | 0.53 [0.44, 0.55] | 0.34 [0.31, 0.37] | 0.75 (4 signs) |
| rival_lgbm_tweedie vs rival_ridge | cross-link (not comparable in scale or rank); raw model, declined by its guard: rival_ridge | 0.64 [0.62, 0.67] | 0.31 [0.18, 0.41] | 0.48 [0.47, 0.51] | 0.25 [0.25, 0.43] | 0.43 [0.33, 0.54] | 0.58 [0.43, 0.63] | 0.62 [0.53, 0.65] | 0.42 [0.40, 0.43] | 1.00 (3 signs) |
| rival_lgbm_tweedie vs treeroute | cross-link (not comparable in scale or rank) | 0.52 [0.42, 0.59] | -0.69 [-0.78, -0.56] | 0.35 [0.28, 0.41] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.05] | 0.06 [0.03, 0.09] | 0.19 [0.14, 0.22] | 0.28 [0.27, 0.31] | nan (0 signs) |
| rival_rf vs rival_ridge | same-link; raw model, declined by its guard: rival_ridge | 0.67 [0.63, 0.69] | 0.34 [0.12, 0.38] | 0.50 [0.47, 0.52] | 0.43 [0.25, 0.67] | 0.43 [0.33, 0.54] | 0.63 [0.55, 0.70] | 0.65 [0.60, 0.69] | 0.32 [0.31, 0.35] | 1.00 (2 signs) |
| rival_rf vs treeroute | cross-link (not comparable in scale or rank) | 0.59 [0.52, 0.65] | -0.50 [-0.56, -0.34] | 0.44 [0.38, 0.49] | 0.11 [0.00, 0.11] | 0.11 [0.05, 0.18] | 0.19 [0.13, 0.33] | 0.30 [0.25, 0.36] | 0.36 [0.34, 0.39] | nan (0 signs) |
| rival_ridge vs treeroute | cross-link (not comparable in scale or rank); raw model, declined by its guard: rival_ridge | 0.27 [0.20, 0.37] | -0.73 [-0.76, -0.60] | 0.18 [0.13, 0.26] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.04 [0.02, 0.06] | 0.14 [0.11, 0.18] | 0.55 [0.54, 0.57] | nan (0 signs) |

Kendall's W (main set) = nan [nan, nan]; mean pairwise Spearman (main set) = nan [nan, nan].
Stability under region resampling (mean Spearman of a model's full-sample importances with its own bootstrap replicates; descriptive, not a ceiling on between-model agreement): rival_lgbm 0.97, rival_lgbm_tweedie 0.99, rival_rf 0.99, rival_ridge 0.99, treeroute 0.95

- rival_lgbm top-10 (103 nonzero): x__spi_03m 8.8%; x__tslf_months 6.5%; x__hist_mean_12 5.7%; x__spi_01m 4.6%; x__sst_anom_atl3 3.2%; x__epo 2.8%; x__spi_24m 2.7%; x__hist_mean_all 2.6%; x__spi_06m 2.6%; x__V06_spei_12m_lag12 2.3%
- rival_lgbm_tweedie top-10 (111 nonzero): x__spi_03m 3.4%; x__spi_24m 3.3%; x__sst_anom_atl3 3.1%; x__spei_01m_lag12 3.0%; x__spei_24m_lag12 2.6%; x__spi_06m 2.4%; x__V04_precip_seasonality 2.2%; x__spei_06m_lag12 2.2%; x__spi_01m 2.0%; x__spi_12m 2.0%
- rival_rf top-10 (111 nonzero): x__spi_03m 9.7%; x__hist_mean_12 7.0%; x__tslf_months 6.3%; x__spi_01m 5.7%; x__hist_mean_all 3.7%; x__spi_06m 3.5%; x__wbal_mm 2.7%; x__spi_24m 2.0%; x__hist_last_1 1.7%; x__sst_anom_coral_sea 1.5%
- rival_ridge top-10 (111 nonzero): x__spi_03m 11.4%; x__spi_01m 9.2%; x__spi_06m 6.3%; x__spi_24m 6.1%; x__hist_mean_12 5.5%; x__sst_anom_coral_sea 5.1%; x__spi_12m 4.2%; x__n_burns_12mo 3.0%; x__sst_anom_atl3 3.0%; x__nao 2.3%
- treeroute top-10 (111 nonzero): x__tslf_months 2.9%; x__era5l_str 2.6%; x__deeprec_twsa 2.5%; x__hist_mean_60 2.4%; x__ao 2.1%; x__grace_lwe 1.7%; x__era5l_sshf 1.6%; x__rmin_pct 1.6%; x__V05_mean_vpd_kPa 1.5%; x__hist_mean_all 1.5%

## Families (sums of the variable-level attributions per row)

| Family | rival_lgbm | rival_lgbm_tweedie | rival_rf | rival_ridge | treeroute |
|---|---|---|---|---|---|
| own history | 17.3% | 6.1% | 23.8% | 18.0% | 13.6% |
| global indices | 28.1% | 34.6% | 18.7% | 29.6% | 26.0% |
| local drivers | 54.6% | 59.3% | 57.5% | 52.4% | 60.4% |
| context and calendar | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| seasonal normal | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |

## Nonzero forecasts of arcsine-link models (rows with pre > 0)

- treeroute, 226 rows: hist_mean 4.1%; spei 3.4%; spi 3.3%; deeprec_twsa 3.2%; era5l_str 3.1%; tslf_months 2.9%; wbal 2.5%; rmin_pct 2.2%; ao 2.2%; grace_lwe 1.7%
