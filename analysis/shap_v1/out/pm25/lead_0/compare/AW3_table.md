# AW3: disagreement of SHAP importances, pm25 lead 0 (post hoc, ruling AK)

1000 rows in 127 regions; link space; percentile 95% intervals from 2000 paired region draws. Same-link pairs are comparable; cross-link pairs are shown for completeness and are not comparable in scale or rank. A rival declined by its own guard is labelled and kept out of W, the consensus and the main row (D6).

Models and links: rival_lgbm (log_c|c=1.5|ub=-); rival_rf (log_c|c=1.5|ub=-); rival_ridge (log_c|c=1.5|ub=-); treeroute (log_c|c=1.5|ub=-)

Main set: rival_lgbm, rival_rf, rival_ridge, treeroute

## variable level (111 players, 89 active; structural zeros: CTI, awc_cm3cm3, bulk_density_gcm3, calendar, cec_cmolkg, clay_pct, coarse_fragments_pct, ctx:lat, dist_to_coast_km, elevation_m, hand_m, irrigation_pct_gmia, nitrogen_gkg, normal, sand_pct, silt_pct, slope_deg, soil_organic_carbon_gkg, soil_ph, southness, travel_time, upstream_area_km2)

| Pair | label | spearman | spearman_top20_union | kendall_tau_b | jaccard_top5 | jaccard_top10 | rbo_p0.9 | rbo_p0.95 | tvd | tvd_family | sign_agreement_top10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rival_lgbm vs rival_rf | same-link | 0.98 [0.97, 0.98] | 0.69 [0.59, 0.74] | 0.87 [0.85, 0.87] | 0.25 [0.25, 0.43] | 0.67 [0.54, 0.67] | 0.66 [0.60, 0.75] | 0.76 [0.73, 0.81] | 0.22 [0.21, 0.23] | 0.05 [0.03, 0.07] | 1.00 (8 signs) |
| rival_lgbm vs rival_ridge | same-link | 0.73 [0.72, 0.75] | 0.14 [0.11, 0.23] | 0.54 [0.52, 0.55] | 0.11 [0.11, 0.25] | 0.33 [0.25, 0.33] | 0.37 [0.36, 0.44] | 0.51 [0.50, 0.55] | 0.41 [0.41, 0.42] | 0.11 [0.08, 0.15] | 0.67 (9 signs) |
| rival_lgbm vs treeroute | same-link | 0.85 [0.83, 0.87] | 0.08 [0.01, 0.19] | 0.68 [0.65, 0.70] | 0.11 [0.11, 0.43] | 0.33 [0.25, 0.43] | 0.53 [0.50, 0.64] | 0.60 [0.58, 0.66] | 0.24 [0.23, 0.25] | 0.18 [0.15, 0.20] | 0.80 (5 signs) |
| rival_rf vs rival_ridge | same-link | 0.73 [0.71, 0.75] | 0.21 [0.15, 0.28] | 0.55 [0.53, 0.56] | 0.25 [0.25, 0.25] | 0.33 [0.33, 0.33] | 0.40 [0.37, 0.41] | 0.52 [0.51, 0.53] | 0.43 [0.42, 0.45] | 0.14 [0.11, 0.18] | 0.78 (9 signs) |
| rival_rf vs treeroute | same-link | 0.85 [0.83, 0.86] | -0.02 [-0.08, 0.07] | 0.68 [0.65, 0.69] | 0.25 [0.11, 0.43] | 0.25 [0.25, 0.25] | 0.42 [0.39, 0.54] | 0.53 [0.50, 0.60] | 0.36 [0.34, 0.37] | 0.15 [0.12, 0.18] | 1.00 (5 signs) |
| rival_ridge vs treeroute | same-link | 0.69 [0.67, 0.72] | -0.12 [-0.17, -0.02] | 0.50 [0.48, 0.52] | 0.00 [0.00, 0.25] | 0.25 [0.25, 0.25] | 0.26 [0.24, 0.34] | 0.41 [0.40, 0.46] | 0.49 [0.48, 0.50] | 0.29 [0.26, 0.32] | 1.00 (4 signs) |

Kendall's W (main set) = 0.85 [0.85, 0.86]; mean pairwise Spearman (main set) = 0.81 [0.80, 0.82].
Stability under region resampling (mean Spearman of a model's full-sample importances with its own bootstrap replicates; descriptive, not a ceiling on between-model agreement): rival_lgbm 1.00, rival_rf 1.00, rival_ridge 1.00, treeroute 0.99

- rival_lgbm top-10 (87 nonzero): hist_last 7.1%; spi 5.9%; hist_mean 5.5%; sst_anom_atl3 3.4%; hdi 3.2%; sst_anom_mediterranean 3.1%; sst_anom_coral_sea 3.0%; spei 3.0%; nino4 2.9%; sst_anom_iod_west 2.8%
- rival_rf top-10 (87 nonzero): spi 12.8%; hist_last 11.6%; sst_anom_global_tropical 6.5%; nino4 5.6%; sst_anom_mediterranean 4.6%; sst_anom_iod_west 4.1%; spei 3.2%; sst_anom_atl3 3.2%; sst_anom_coral_sea 2.8%; sst_anom_subpolar_north_atlantic 2.7%
- rival_ridge top-10 (89 nonzero): sst_anom_global_tropical 14.8%; hist_mean 10.4%; nino12 7.2%; pdo 7.2%; nino4 6.5%; spi 5.7%; hist_last 4.6%; tni 3.9%; nino3 3.7%; sst_anom_iod_west 2.9%
- treeroute top-10 (88 nonzero): hist_last 5.0%; spei 3.3%; wbal 3.2%; era5l_str 3.2%; sst_anom_mediterranean 3.1%; spi 3.1%; pdo 3.0%; hist_mean 2.7%; tna 2.5%; era5l_sshf 2.1%

## feature level (125 players, 103 active; structural zeros: c__ctx:lat, c__ctx:month, normal, x__V25_elevation_m, x__V26_slope_deg, x__V27_southness, x__V28_CTI, x__awc_cm3cm3, x__bulk_density_gcm3, x__cec_cmolkg, x__clay_pct, x__coarse_fragments_pct, x__dist_to_coast_km, x__hand_m, x__irrigation_pct_gmia, x__nitrogen_gkg, x__sand_pct, x__silt_pct, x__soil_organic_carbon_gkg, x__soil_ph, x__travel_time, x__upstream_area_km2)

| Pair | label | spearman | spearman_top20_union | kendall_tau_b | jaccard_top5 | jaccard_top10 | rbo_p0.9 | rbo_p0.95 | tvd | sign_agreement_top10 |
|---|---|---|---|---|---|---|---|---|---|---|
| rival_lgbm vs rival_rf | same-link | 0.96 [0.96, 0.97] | 0.51 [0.45, 0.61] | 0.84 [0.83, 0.85] | 0.25 [0.11, 0.43] | 0.67 [0.54, 0.67] | 0.65 [0.55, 0.71] | 0.73 [0.68, 0.76] | 0.23 [0.22, 0.24] | 1.00 (8 signs) |
| rival_lgbm vs rival_ridge | same-link | 0.73 [0.71, 0.74] | -0.02 [-0.08, 0.05] | 0.53 [0.52, 0.54] | 0.00 [0.00, 0.11] | 0.18 [0.11, 0.25] | 0.25 [0.23, 0.31] | 0.42 [0.40, 0.45] | 0.40 [0.40, 0.41] | 0.73 (11 signs) |
| rival_lgbm vs treeroute | same-link | 0.78 [0.75, 0.80] | -0.26 [-0.34, -0.16] | 0.61 [0.58, 0.63] | 0.11 [0.11, 0.25] | 0.11 [0.11, 0.18] | 0.42 [0.33, 0.46] | 0.48 [0.44, 0.51] | 0.25 [0.24, 0.26] | 0.83 (6 signs) |
| rival_rf vs rival_ridge | same-link | 0.70 [0.69, 0.72] | -0.05 [-0.10, -0.02] | 0.51 [0.50, 0.53] | 0.11 [0.11, 0.11] | 0.18 [0.18, 0.18] | 0.30 [0.28, 0.32] | 0.44 [0.42, 0.45] | 0.45 [0.44, 0.46] | 0.82 (11 signs) |
| rival_rf vs treeroute | same-link | 0.78 [0.75, 0.80] | -0.31 [-0.37, -0.22] | 0.60 [0.58, 0.62] | 0.11 [0.11, 0.25] | 0.11 [0.11, 0.18] | 0.42 [0.40, 0.45] | 0.48 [0.46, 0.51] | 0.35 [0.34, 0.37] | 1.00 (4 signs) |
| rival_ridge vs treeroute | same-link | 0.61 [0.59, 0.63] | -0.43 [-0.48, -0.34] | 0.43 [0.41, 0.45] | 0.11 [0.00, 0.11] | 0.11 [0.11, 0.18] | 0.16 [0.15, 0.21] | 0.30 [0.29, 0.33] | 0.50 [0.49, 0.51] | 0.71 (7 signs) |

Kendall's W (main set) = 0.82 [0.81, 0.83]; mean pairwise Spearman (main set) = 0.76 [0.75, 0.77].
Stability under region resampling (mean Spearman of a model's full-sample importances with its own bootstrap replicates; descriptive, not a ceiling on between-model agreement): rival_lgbm 1.00, rival_rf 1.00, rival_ridge 1.00, treeroute 0.99

- rival_lgbm top-10 (101 nonzero): x__hist_last_1 5.9%; x__hist_mean_12 5.2%; x__sst_anom_atl3 3.0%; x__hdi 2.8%; x__spi_03m 2.7%; x__sst_anom_mediterranean 2.7%; x__spi_01m 2.7%; x__sst_anom_coral_sea 2.7%; x__nino4 2.6%; x__sst_anom_iod_west 2.5%
- rival_rf top-10 (101 nonzero): x__hist_last_1 10.0%; x__spi_03m 8.1%; x__sst_anom_global_tropical_mean 5.9%; x__nino4 5.2%; x__spi_01m 4.3%; x__sst_anom_mediterranean 4.2%; x__sst_anom_iod_west 3.8%; x__sst_anom_atl3 3.0%; x__sst_anom_subpolar_north_atlantic 2.5%; x__sst_anom_coral_sea 2.5%
- rival_ridge top-10 (103 nonzero): x__sst_anom_global_tropical_mean 12.1%; x__hist_mean_60 7.2%; x__hist_mean_all 6.3%; x__nino12 5.9%; x__pdo 5.9%; x__hist_mean_12 5.5%; x__nino4 5.3%; x__hist_last_1 4.0%; x__tni 3.2%; x__nino3 3.0%
- treeroute top-10 (102 nonzero): x__hist_last_1 4.0%; x__era5l_str 2.9%; x__sst_anom_mediterranean 2.9%; x__pdo 2.8%; x__tna 2.4%; x__wbal_roll3 2.3%; x__era5l_sshf 2.0%; x__amo_lag12 1.9%; x__deeprec_twsa 1.9%; x__climate_water_deficit_mm 1.9%

## Families (sums of the variable-level attributions per row)

| Family | rival_lgbm | rival_rf | rival_ridge | treeroute |
|---|---|---|---|---|
| own history | 29.8% | 25.2% | 38.2% | 18.5% |
| global indices | 38.9% | 40.8% | 41.3% | 32.2% |
| local drivers | 31.3% | 34.0% | 20.5% | 49.2% |
| context and calendar | 0.0% | 0.0% | 0.0% | 0.0% |
| seasonal normal | 0.0% | 0.0% | 0.0% | 0.0% |
