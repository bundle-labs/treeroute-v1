# AW3: disagreement of SHAP importances, defo lead 0 (post hoc, ruling AK)

1000 rows in 42 regions; link space; percentile 95% intervals from 2000 paired region draws. Same-link pairs are comparable; cross-link pairs are shown for completeness and are not comparable in scale or rank. A rival declined by its own guard is labelled and kept out of W, the consensus and the main row (D6).

Models and links: rival_lgbm (log_c|c=4.95638378197e-05|ub=1); rival_lgbm_tweedie (log_mu|c=4.95638378197e-05|ub=1); rival_rf (log_c|c=4.95638378197e-05|ub=1); rival_ridge (log_c|c=4.95638378197e-05|ub=1); treeroute (log_c|c=4.95638378197e-05|ub=1)

Main set: rival_lgbm, rival_rf, rival_ridge, treeroute

## variable level (121 players, 99 active; structural zeros: CTI, awc_cm3cm3, bulk_density_gcm3, cec_cmolkg, clay_pct, coarse_fragments_pct, conflict_deaths, conflict_events, dist_to_coast_km, elevation_m, hand_m, irrigation_pct_gmia, nitrogen_gkg, normal, sand_pct, silt_pct, slope_deg, soil_organic_carbon_gkg, soil_ph, southness, travel_time, upstream_area_km2)

| Pair | label | spearman | spearman_top20_union | kendall_tau_b | jaccard_top5 | jaccard_top10 | rbo_p0.9 | rbo_p0.95 | tvd | tvd_family | sign_agreement_top10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rival_lgbm vs rival_lgbm_tweedie | cross-link (not comparable in scale or rank) | 0.79 [0.75, 0.81] | 0.60 [0.54, 0.64] | 0.61 [0.57, 0.62] | 0.25 [0.25, 0.43] | 0.82 [0.67, 0.82] | 0.61 [0.57, 0.70] | 0.69 [0.65, 0.72] | 0.30 [0.28, 0.32] | 0.12 [0.09, 0.17] | 0.33 (3 signs) |
| rival_lgbm vs rival_rf | same-link | 0.83 [0.80, 0.84] | 0.52 [0.46, 0.63] | 0.65 [0.62, 0.67] | 0.67 [0.67, 1.00] | 0.67 [0.67, 0.67] | 0.84 [0.74, 0.88] | 0.82 [0.76, 0.84] | 0.17 [0.16, 0.18] | 0.02 [0.00, 0.04] | 1.00 (6 signs) |
| rival_lgbm vs rival_ridge | same-link | 0.75 [0.72, 0.77] | -0.04 [-0.13, 0.06] | 0.56 [0.53, 0.58] | 0.25 [0.11, 0.25] | 0.33 [0.25, 0.33] | 0.35 [0.31, 0.53] | 0.50 [0.46, 0.59] | 0.39 [0.38, 0.42] | 0.23 [0.20, 0.27] | 1.00 (5 signs) |
| rival_lgbm vs treeroute | same-link | 0.74 [0.70, 0.77] | 0.47 [0.38, 0.53] | 0.56 [0.52, 0.59] | 0.43 [0.43, 0.67] | 0.43 [0.43, 0.67] | 0.64 [0.60, 0.74] | 0.67 [0.64, 0.72] | 0.28 [0.27, 0.31] | 0.17 [0.13, 0.21] | 1.00 (4 signs) |
| rival_lgbm_tweedie vs rival_rf | cross-link (not comparable in scale or rank) | 0.83 [0.80, 0.85] | 0.36 [0.28, 0.41] | 0.69 [0.65, 0.70] | 0.43 [0.25, 0.67] | 0.67 [0.43, 0.67] | 0.58 [0.54, 0.62] | 0.65 [0.62, 0.67] | 0.31 [0.29, 0.32] | 0.12 [0.08, 0.17] | 0.60 (5 signs) |
| rival_lgbm_tweedie vs rival_ridge | cross-link (not comparable in scale or rank) | 0.62 [0.58, 0.64] | -0.22 [-0.29, -0.11] | 0.45 [0.42, 0.47] | 0.11 [0.00, 0.11] | 0.25 [0.11, 0.33] | 0.28 [0.23, 0.33] | 0.42 [0.38, 0.45] | 0.47 [0.46, 0.49] | 0.34 [0.28, 0.40] | 0.75 (8 signs) |
| rival_lgbm_tweedie vs treeroute | cross-link (not comparable in scale or rank) | 0.78 [0.74, 0.80] | 0.51 [0.43, 0.58] | 0.61 [0.58, 0.63] | 0.43 [0.43, 0.67] | 0.43 [0.43, 0.67] | 0.52 [0.50, 0.63] | 0.63 [0.61, 0.69] | 0.29 [0.27, 0.31] | 0.17 [0.11, 0.23] | 0.20 (5 signs) |
| rival_rf vs rival_ridge | same-link | 0.63 [0.59, 0.66] | -0.03 [-0.10, 0.05] | 0.46 [0.43, 0.49] | 0.11 [0.11, 0.25] | 0.43 [0.25, 0.43] | 0.34 [0.30, 0.51] | 0.47 [0.44, 0.56] | 0.42 [0.41, 0.43] | 0.25 [0.21, 0.28] | 0.83 (6 signs) |
| rival_rf vs treeroute | same-link | 0.76 [0.72, 0.80] | 0.20 [0.14, 0.29] | 0.60 [0.56, 0.63] | 0.43 [0.43, 0.67] | 0.43 [0.43, 0.54] | 0.60 [0.59, 0.71] | 0.62 [0.61, 0.69] | 0.28 [0.26, 0.30] | 0.19 [0.16, 0.23] | 0.83 (6 signs) |
| rival_ridge vs treeroute | same-link | 0.65 [0.62, 0.68] | 0.01 [-0.12, 0.08] | 0.48 [0.45, 0.51] | 0.25 [0.11, 0.25] | 0.33 [0.25, 0.33] | 0.33 [0.27, 0.52] | 0.45 [0.41, 0.55] | 0.36 [0.35, 0.39] | 0.31 [0.26, 0.37] | 1.00 (6 signs) |

Kendall's W (main set) = 0.80 [0.78, 0.81]; mean pairwise Spearman (main set) = 0.73 [0.71, 0.74].
Stability under region resampling (mean Spearman of a model's full-sample importances with its own bootstrap replicates; descriptive, not a ceiling on between-model agreement): rival_lgbm 0.99, rival_lgbm_tweedie 0.99, rival_rf 0.99, rival_ridge 1.00, treeroute 0.99

- rival_lgbm top-10 (99 nonzero): hist_last 12.8%; hist_mean 10.6%; soi 6.2%; spi 5.0%; h_nbr1 4.3%; spei 3.7%; h_yrs_since 3.7%; sst_anom_mediterranean 3.3%; sst_anom_atl3 3.1%; sst_anom_iod_west 2.9%
- rival_lgbm_tweedie top-10 (99 nonzero): hist_mean 21.9%; h_yrs_since 5.6%; hist_last 4.5%; sst_anom_mediterranean 3.6%; spei 3.6%; spi 3.2%; sst_anom_atl3 2.8%; sst_anom_iod_west 2.1%; h_nbr1 2.1%; pdo 1.9%
- rival_rf top-10 (99 nonzero): hist_last 15.9%; hist_mean 9.6%; spi 5.1%; soi 4.6%; spei 4.2%; h_nbr1 4.0%; sst_anom_mediterranean 2.6%; h_yrs_since 2.4%; pdo 2.0%; wp 1.8%
- rival_ridge top-10 (99 nonzero): tsa 6.7%; h_nbr_cum 6.0%; ao 5.6%; hist_last 5.1%; h_nbr1 4.7%; epo 4.0%; spi 3.9%; soi 3.1%; spei 2.9%; wp 2.9%
- treeroute top-10 (99 nonzero): hist_last 9.2%; h_nbr1 4.8%; spei 4.5%; h_yrs_since 4.4%; spi 4.4%; hist_mean 4.2%; h_nbr_cum 2.5%; wbal 2.4%; deeprec_twsa_k3 2.3%; h_nbr2 1.9%

## feature level (309 players, 280 active; structural zeros: normal, x__V20_burned_binary_min, x__V25_elevation_m, x__V26_slope_deg, x__V27_southness, x__V28_CTI, x__awc_cm3cm3, x__bulk_density_gcm3, x__cec_cmolkg, x__clay_pct, x__coarse_fragments_pct, x__conflict_deaths_max, x__conflict_deaths_mean, x__conflict_deaths_min, x__conflict_events_max, x__conflict_events_mean, x__conflict_events_min, x__dist_to_coast_km, x__hand_m, x__heatwave_days_gt35C_min, x__irrigation_pct_gmia, x__nitrogen_gkg, x__sand_pct, x__silt_pct, x__soil_organic_carbon_gkg, x__soil_ph, x__swe_mean_mm_min, x__travel_time, x__upstream_area_km2)

| Pair | label | spearman | spearman_top20_union | kendall_tau_b | jaccard_top5 | jaccard_top10 | jaccard_top20 | rbo_p0.9 | rbo_p0.95 | tvd | sign_agreement_top10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rival_lgbm vs rival_lgbm_tweedie | cross-link (not comparable in scale or rank) | 0.72 [0.69, 0.75] | 0.36 [0.29, 0.48] | 0.53 [0.51, 0.56] | 0.43 [0.43, 0.43] | 0.54 [0.43, 0.54] | 0.43 [0.38, 0.54] | 0.55 [0.53, 0.69] | 0.60 [0.58, 0.68] | 0.29 [0.29, 0.31] | 0.40 (5 signs) |
| rival_lgbm vs rival_rf | same-link | 0.75 [0.73, 0.77] | 0.23 [0.15, 0.37] | 0.57 [0.55, 0.58] | 1.00 [0.67, 1.00] | 0.43 [0.43, 0.67] | 0.33 [0.29, 0.48] | 0.78 [0.66, 0.80] | 0.72 [0.65, 0.74] | 0.23 [0.22, 0.24] | 1.00 (6 signs) |
| rival_lgbm vs rival_ridge | same-link | 0.64 [0.61, 0.65] | -0.19 [-0.35, -0.02] | 0.45 [0.43, 0.47] | 0.25 [0.25, 0.25] | 0.18 [0.11, 0.33] | 0.29 [0.21, 0.38] | 0.30 [0.23, 0.39] | 0.36 [0.30, 0.44] | 0.43 [0.41, 0.45] | 0.86 (7 signs) |
| rival_lgbm vs treeroute | same-link | 0.62 [0.58, 0.66] | 0.37 [0.23, 0.40] | 0.45 [0.41, 0.47] | 0.67 [0.67, 0.67] | 0.67 [0.43, 0.67] | 0.33 [0.33, 0.43] | 0.65 [0.53, 0.67] | 0.61 [0.53, 0.62] | 0.33 [0.32, 0.36] | 1.00 (1 signs) |
| rival_lgbm_tweedie vs rival_rf | cross-link (not comparable in scale or rank) | 0.77 [0.74, 0.78] | 0.18 [0.07, 0.24] | 0.62 [0.59, 0.63] | 0.43 [0.25, 0.43] | 0.43 [0.43, 0.43] | 0.33 [0.25, 0.43] | 0.49 [0.46, 0.53] | 0.52 [0.50, 0.56] | 0.27 [0.26, 0.29] | 0.50 (6 signs) |
| rival_lgbm_tweedie vs rival_ridge | cross-link (not comparable in scale or rank) | 0.50 [0.47, 0.53] | -0.34 [-0.43, -0.19] | 0.35 [0.33, 0.38] | 0.11 [0.11, 0.11] | 0.25 [0.18, 0.33] | 0.18 [0.11, 0.25] | 0.22 [0.18, 0.29] | 0.30 [0.26, 0.35] | 0.46 [0.44, 0.47] | 0.71 (7 signs) |
| rival_lgbm_tweedie vs treeroute | cross-link (not comparable in scale or rank) | 0.67 [0.63, 0.69] | 0.42 [0.28, 0.47] | 0.51 [0.47, 0.53] | 0.43 [0.43, 0.67] | 0.67 [0.43, 0.67] | 0.43 [0.29, 0.43] | 0.51 [0.48, 0.59] | 0.55 [0.53, 0.59] | 0.27 [0.26, 0.30] | 0.33 (3 signs) |
| rival_rf vs rival_ridge | same-link | 0.55 [0.52, 0.58] | -0.29 [-0.44, -0.16] | 0.38 [0.36, 0.40] | 0.25 [0.25, 0.25] | 0.11 [0.11, 0.25] | 0.18 [0.11, 0.25] | 0.28 [0.19, 0.37] | 0.32 [0.25, 0.39] | 0.44 [0.44, 0.46] | 0.69 (13 signs) |
| rival_rf vs treeroute | same-link | 0.67 [0.63, 0.70] | 0.11 [-0.03, 0.15] | 0.51 [0.47, 0.52] | 0.67 [0.43, 0.67] | 0.33 [0.25, 0.43] | 0.25 [0.21, 0.33] | 0.59 [0.55, 0.63] | 0.52 [0.49, 0.55] | 0.29 [0.28, 0.31] | 0.60 (5 signs) |
| rival_ridge vs treeroute | same-link | 0.45 [0.41, 0.50] | -0.14 [-0.27, 0.06] | 0.32 [0.29, 0.35] | 0.43 [0.25, 0.43] | 0.25 [0.18, 0.43] | 0.21 [0.14, 0.29] | 0.41 [0.25, 0.48] | 0.40 [0.30, 0.46] | 0.40 [0.39, 0.43] | 1.00 (6 signs) |

Kendall's W (main set) = 0.71 [0.69, 0.73]; mean pairwise Spearman (main set) = 0.61 [0.59, 0.63].
Stability under region resampling (mean Spearman of a model's full-sample importances with its own bootstrap replicates; descriptive, not a ceiling on between-model agreement): rival_lgbm 0.99, rival_lgbm_tweedie 0.99, rival_rf 0.99, rival_ridge 1.00, treeroute 0.98

- rival_lgbm top-10 (277 nonzero): x__hist_last_1 9.6%; x__hist_mean_all 9.2%; x__soi_max 4.5%; x__h_nbr1 3.2%; x__h_yrs_since 2.8%; x__sst_anom_mediterranean_mean 2.2%; x__hist_mean_5 2.2%; x__sst_anom_atl3_max 1.6%; x__h_nbr2 1.4%; x__spi_06m_min 1.4%
- rival_lgbm_tweedie top-10 (280 nonzero): x__hist_mean_all 14.8%; x__h_yrs_since 4.1%; x__hist_mean_5 2.8%; x__hist_last_1 2.8%; x__sst_anom_mediterranean_mean 2.1%; x__sst_anom_atl3_max 1.8%; x__h_nbr1 1.6%; x__h_nbr_cum 1.4%; x__pdo_min 1.3%; x__iod_mean 1.1%
- rival_rf top-10 (279 nonzero): x__hist_last_1 12.5%; x__hist_mean_all 7.8%; x__h_nbr1 3.2%; x__soi_max 2.6%; x__h_yrs_since 1.9%; x__sst_anom_mediterranean_mean 1.7%; x__hdi 1.3%; x__pdo_min 1.3%; x__sst_anom_global_tropical_mean_min 1.2%; x__oni_max 1.2%
- rival_ridge top-10 (280 nonzero): x__h_nbr_cum 4.3%; x__h_nbr1 3.4%; x__hist_last_1 3.3%; x__ao_max 3.3%; x__tsa_max 3.3%; x__epo_mean 1.7%; x__spi_01m_mean 1.6%; x__tsa_mean 1.6%; x__sst_anom_atl3_max 1.5%; x__wp_max 1.5%
- treeroute top-10 (279 nonzero): x__hist_last_1 6.0%; x__h_nbr1 3.4%; x__h_yrs_since 3.1%; x__hist_mean_all 2.7%; x__h_nbr_cum 1.8%; x__hist_mean_5 1.6%; x__h_nbr2 1.3%; x__deeprec_twsa_k3_mean 1.2%; x__sst_anom_atl3_max 1.0%; x__sst_anom_mediterranean_mean 0.9%

## Families (sums of the variable-level attributions per row)

| Family | rival_lgbm | rival_lgbm_tweedie | rival_rf | rival_ridge | treeroute |
|---|---|---|---|---|---|
| own history | 35.5% | 46.1% | 36.9% | 12.2% | 29.3% |
| global indices | 33.6% | 21.8% | 34.1% | 53.8% | 22.5% |
| local drivers | 30.9% | 32.2% | 29.0% | 34.0% | 48.2% |
| context and calendar | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| seasonal normal | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
