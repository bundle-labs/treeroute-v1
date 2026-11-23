# AW3: disagreement of SHAP importances, ndvi lead 0 (post hoc, ruling AK)

1000 rows in 133 regions; link space; percentile 95% intervals from 2000 paired region draws. Same-link pairs are comparable; cross-link pairs are shown for completeness and are not comparable in scale or rank. A rival declined by its own guard is labelled and kept out of W, the consensus and the main row (D6).

Models and links: rival_bardl_h1 (identity|c=-|ub=1); rival_lgbm (identity|c=-|ub=1); rival_rf (identity|c=-|ub=1); rival_ridge (identity|c=-|ub=1); treeroute (identity|c=-|ub=1)

Main set: rival_bardl_h1, rival_lgbm, rival_rf, rival_ridge, treeroute

## variable level (117 players, 96 active; structural zeros: CTI, awc_cm3cm3, bulk_density_gcm3, calendar, cec_cmolkg, clay_pct, coarse_fragments_pct, dist_to_coast_km, elevation_m, hand_m, irrigation_pct_gmia, nitrogen_gkg, normal, sand_pct, silt_pct, slope_deg, soil_organic_carbon_gkg, soil_ph, southness, travel_time, upstream_area_km2)

| Pair | label | spearman | spearman_top20_union | kendall_tau_b | jaccard_top5 | jaccard_top10 | rbo_p0.9 | rbo_p0.95 | tvd | tvd_family | sign_agreement_top10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rival_bardl_h1 vs rival_lgbm | same-link | 0.16 [0.12, 0.19] | 0.11 [0.07, 0.11] | 0.13 [0.10, 0.15] | 0.11 [0.11, 0.11] | 0.05 [0.05, 0.11] | 0.20 [0.16, 0.22] | 0.25 [0.23, 0.27] | 0.91 [0.90, 0.92] | 0.16 [0.14, 0.17] | nan (0 signs) |
| rival_bardl_h1 vs rival_rf | same-link | 0.16 [0.15, 0.17] | 0.16 [0.12, 0.18] | 0.13 [0.12, 0.14] | 0.11 [0.00, 0.11] | 0.18 [0.11, 0.18] | 0.15 [0.12, 0.19] | 0.24 [0.21, 0.27] | 0.96 [0.95, 0.96] | 0.31 [0.28, 0.35] | nan (0 signs) |
| rival_bardl_h1 vs rival_ridge | same-link | 0.15 [0.14, 0.16] | 0.03 [0.00, 0.04] | 0.13 [0.11, 0.13] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.05] | 0.05 [0.05, 0.06] | 0.15 [0.15, 0.16] | 0.96 [0.95, 0.96] | 0.11 [0.11, 0.13] | 1.00 (1 signs) |
| rival_bardl_h1 vs treeroute | same-link | 0.28 [0.27, 0.28] | 0.38 [0.34, 0.41] | 0.23 [0.22, 0.23] | 0.25 [0.25, 0.43] | 0.25 [0.18, 0.25] | 0.37 [0.31, 0.39] | 0.40 [0.37, 0.42] | 0.88 [0.87, 0.89] | 0.11 [0.08, 0.14] | 1.00 (1 signs) |
| rival_lgbm vs rival_rf | same-link | 0.91 [0.88, 0.92] | 0.47 [0.36, 0.56] | 0.78 [0.75, 0.79] | 0.43 [0.25, 0.43] | 0.54 [0.43, 0.67] | 0.69 [0.64, 0.71] | 0.74 [0.71, 0.76] | 0.28 [0.27, 0.30] | 0.25 [0.23, 0.27] | 1.00 (6 signs) |
| rival_lgbm vs rival_ridge | same-link | 0.58 [0.56, 0.60] | -0.51 [-0.58, -0.49] | 0.42 [0.40, 0.44] | 0.00 [0.00, 0.11] | 0.11 [0.05, 0.11] | 0.13 [0.11, 0.15] | 0.28 [0.26, 0.29] | 0.51 [0.50, 0.52] | 0.04 [0.03, 0.07] | 0.86 (7 signs) |
| rival_lgbm vs treeroute | same-link | 0.70 [0.66, 0.72] | 0.16 [0.08, 0.23] | 0.52 [0.49, 0.54] | 0.43 [0.25, 0.67] | 0.43 [0.33, 0.54] | 0.51 [0.46, 0.54] | 0.56 [0.53, 0.58] | 0.30 [0.29, 0.31] | 0.09 [0.07, 0.11] | 0.75 (4 signs) |
| rival_rf vs rival_ridge | same-link | 0.53 [0.51, 0.55] | -0.66 [-0.71, -0.63] | 0.37 [0.35, 0.38] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.05] | 0.08 [0.07, 0.09] | 0.22 [0.21, 0.23] | 0.61 [0.59, 0.62] | 0.22 [0.19, 0.24] | 0.83 (6 signs) |
| rival_rf vs treeroute | same-link | 0.71 [0.68, 0.73] | -0.02 [-0.11, 0.03] | 0.53 [0.50, 0.55] | 0.25 [0.00, 0.25] | 0.33 [0.25, 0.54] | 0.31 [0.26, 0.34] | 0.44 [0.40, 0.46] | 0.47 [0.45, 0.49] | 0.20 [0.18, 0.23] | 0.75 (4 signs) |
| rival_ridge vs treeroute | same-link | 0.61 [0.58, 0.63] | -0.41 [-0.44, -0.34] | 0.43 [0.41, 0.45] | 0.00 [0.00, 0.11] | 0.11 [0.11, 0.18] | 0.17 [0.15, 0.19] | 0.33 [0.31, 0.35] | 0.48 [0.47, 0.49] | 0.05 [0.03, 0.08] | 0.75 (4 signs) |

Kendall's W (main set) = 0.62 [0.61, 0.62]; mean pairwise Spearman (main set) = 0.48 [0.47, 0.49].
Stability under region resampling (mean Spearman of a model's full-sample importances with its own bootstrap replicates; descriptive, not a ceiling on between-model agreement): rival_bardl_h1 1.00, rival_lgbm 0.99, rival_rf 1.00, rival_ridge 1.00, treeroute 0.99

- rival_bardl_h1 top-10 (3 nonzero): soil_moisture_pct 45.7%; hist_last 29.5%; total_precip_mm 24.8%; aet_total_mm 0.0%; aglw_buffalo_hold2021 0.0%; aglw_cattle_hold2021 0.0%; aglw_goats_hold2021 0.0%; aglw_horse_hold2021 0.0%; aglw_sheep_hold2021 0.0%; aglw_total_lsu_hold2021 0.0%
- rival_lgbm top-10 (94 nonzero): spi 12.2%; hist_last 6.8%; hist_mean 5.6%; wbal 2.7%; grace_lwe 2.4%; era5l_slhf 2.3%; sst_anom_subpolar_north_atlantic 2.0%; climate_water_deficit_mm 1.9%; sst_anom_global_tropical 1.7%; era5l_str 1.6%
- rival_rf top-10 (94 nonzero): spi 35.2%; climate_water_deficit_mm 3.5%; sst_anom_subpolar_north_atlantic 2.9%; wbal 2.9%; hist_last 2.3%; sst_anom_global_tropical 2.0%; grace_lwe 2.0%; aet_total_mm 1.9%; swe_mean_mm 1.7%; total_precip_mm 1.6%
- rival_ridge top-10 (96 nonzero): sst_anom_nino34 12.5%; nino34 9.8%; oni 4.9%; era5l_ssr 4.6%; mean_vpd_kPa 3.8%; sph_kgkg 3.8%; hist_mean 3.5%; vpd_warm_season 3.4%; solar_radiation_Wm2 3.2%; era5l_str 3.0%
- treeroute top-10 (94 nonzero): hist_mean 7.3%; hist_last 6.4%; era5l_slhf 5.6%; aet_total_mm 4.7%; wbal 2.9%; total_precip_mm 2.9%; era5l_str 2.8%; soil_moisture_pct 2.5%; spi 2.5%; soil_water_tc_mm 2.4%

## feature level (503 players, 479 active; structural zeros: c__ctx:cos1, c__ctx:cos2, c__ctx:sin1, c__ctx:sin2, normal, x__V25_elevation_m, x__V26_slope_deg, x__V27_southness, x__V28_CTI, x__awc_cm3cm3, x__bulk_density_gcm3, x__cec_cmolkg, x__clay_pct, x__coarse_fragments_pct, x__dist_to_coast_km, x__hand_m, x__irrigation_pct_gmia, x__nitrogen_gkg, x__sand_pct, x__silt_pct, x__soil_organic_carbon_gkg, x__soil_ph, x__travel_time, x__upstream_area_km2)

| Pair | label | spearman | spearman_top20_union | kendall_tau_b | jaccard_top5 | jaccard_top10 | jaccard_top20 | rbo_p0.9 | rbo_p0.95 | tvd | sign_agreement_top10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rival_bardl_h1 vs rival_lgbm | same-link | 0.06 [0.05, 0.07] | -0.18 [-0.24, -0.17] | 0.05 [0.04, 0.06] | 0.11 [0.11, 0.11] | 0.11 [0.05, 0.11] | 0.05 [0.05, 0.05] | 0.28 [0.12, 0.28] | 0.20 [0.11, 0.20] | 0.94 [0.93, 0.95] | 1.00 (1 signs) |
| rival_bardl_h1 vs rival_rf | same-link | 0.05 [0.04, 0.07] | -0.31 [-0.36, -0.28] | 0.04 [0.03, 0.05] | 0.00 [0.00, 0.00] | 0.05 [0.00, 0.05] | 0.03 [0.03, 0.05] | 0.05 [0.02, 0.06] | 0.06 [0.04, 0.07] | 0.98 [0.97, 0.98] | 1.00 (1 signs) |
| rival_bardl_h1 vs rival_ridge | same-link | 0.03 [0.02, 0.03] | -0.47 [-0.48, -0.46] | 0.02 [0.02, 0.03] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.01 [0.01, 0.01] | 0.03 [0.02, 0.03] | 0.99 [0.99, 0.99] | 1.00 (1 signs) |
| rival_bardl_h1 vs treeroute | same-link | 0.18 [0.18, 0.19] | -0.06 [-0.11, -0.03] | 0.15 [0.14, 0.15] | 0.11 [0.11, 0.11] | 0.11 [0.11, 0.11] | 0.11 [0.11, 0.14] | 0.31 [0.16, 0.32] | 0.26 [0.18, 0.27] | 0.93 [0.92, 0.93] | nan (0 signs) |
| rival_lgbm vs rival_rf | same-link | 0.84 [0.82, 0.85] | 0.06 [-0.01, 0.13] | 0.67 [0.65, 0.68] | 0.25 [0.25, 0.25] | 0.43 [0.33, 0.43] | 0.43 [0.33, 0.48] | 0.43 [0.40, 0.45] | 0.52 [0.49, 0.53] | 0.27 [0.26, 0.29] | 1.00 (3 signs) |
| rival_lgbm vs rival_ridge | same-link | 0.31 [0.29, 0.33] | -0.53 [-0.63, -0.45] | 0.21 [0.20, 0.23] | 0.00 [0.00, 0.00] | 0.11 [0.00, 0.11] | 0.11 [0.08, 0.14] | 0.09 [0.05, 0.13] | 0.14 [0.10, 0.17] | 0.55 [0.54, 0.56] | 1.00 (6 signs) |
| rival_lgbm vs treeroute | same-link | 0.28 [0.25, 0.30] | -0.11 [-0.19, -0.04] | 0.19 [0.17, 0.21] | 0.25 [0.25, 0.25] | 0.33 [0.25, 0.33] | 0.25 [0.18, 0.25] | 0.53 [0.41, 0.55] | 0.46 [0.39, 0.47] | 0.34 [0.33, 0.35] | 1.00 (2 signs) |
| rival_rf vs rival_ridge | same-link | 0.27 [0.25, 0.29] | -0.72 [-0.75, -0.67] | 0.19 [0.17, 0.20] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.03 [0.03, 0.05] | 0.01 [0.01, 0.02] | 0.04 [0.03, 0.05] | 0.62 [0.61, 0.63] | 1.00 (7 signs) |
| rival_rf vs treeroute | same-link | 0.27 [0.24, 0.30] | -0.65 [-0.70, -0.61] | 0.19 [0.17, 0.21] | 0.00 [0.00, 0.00] | 0.05 [0.00, 0.05] | 0.11 [0.05, 0.18] | 0.08 [0.05, 0.10] | 0.15 [0.12, 0.17] | 0.45 [0.44, 0.47] | 1.00 (3 signs) |
| rival_ridge vs treeroute | same-link | 0.17 [0.15, 0.18] | -0.48 [-0.59, -0.40] | 0.12 [0.10, 0.13] | 0.00 [0.00, 0.00] | 0.18 [0.00, 0.18] | 0.14 [0.11, 0.14] | 0.12 [0.06, 0.16] | 0.19 [0.13, 0.21] | 0.54 [0.53, 0.55] | 0.67 (9 signs) |

Kendall's W (main set) = 0.42 [0.41, 0.43]; mean pairwise Spearman (main set) = 0.25 [0.24, 0.25].
Stability under region resampling (mean Spearman of a model's full-sample importances with its own bootstrap replicates; descriptive, not a ceiling on between-model agreement): rival_bardl_h1 1.00, rival_lgbm 0.99, rival_rf 0.99, rival_ridge 1.00, treeroute 0.99

- rival_bardl_h1 top-10 (9 nonzero): x__hist_last_1 18.3%; x__V30_soil_moisture_pct 18.1%; x__V30_soil_moisture_pct_lag1 17.1%; x__V02_total_precip_mm_lag1 10.9%; x__V02_total_precip_mm 8.8%; x__V30_soil_moisture_pct_lag2 8.3%; x__V02_total_precip_mm_lag2 6.9%; x__hist_last_3 6.0%; x__hist_last_2 5.6%; x__V01_mean_temp_C 0.0%
- rival_lgbm top-10 (477 nonzero): x__hist_last_1 4.1%; x__hist_mean_12 3.7%; x__spi_03m 2.3%; x__hist_mean_all 1.9%; x__spi_06m 1.9%; x__spi_01m_lag1 1.5%; x__spi_03m_lag1 1.5%; x__spi_12m 1.3%; x__era5l_slhf 0.9%; x__hist_last_2 0.7%
- rival_rf top-10 (477 nonzero): x__spi_03m 9.8%; x__spi_06m 7.0%; x__spi_12m 4.1%; x__spi_01m_lag1 3.1%; x__spi_03m_lag1 2.5%; x__spi_06m_lag1 1.3%; x__hist_last_1 1.2%; x__spi_12m_lag1 1.1%; x__swe_mean_mm 1.1%; x__climate_water_deficit_mm_lag1 1.1%
- rival_ridge top-10 (479 nonzero): x__sst_anom_nino34_lag12 4.4%; x__sst_anom_nino34_lag6 3.8%; x__nino34_lag12 3.8%; x__era5l_ssr 3.3%; x__nino34_lag6 3.0%; x__sph_kgkg 1.5%; x__hist_mean_12 1.5%; x__spi_24m 1.5%; x__hist_mean_all 1.4%; x__hist_mean_60 1.4%
- treeroute top-10 (477 nonzero): x__hist_last_1 3.0%; x__hist_mean_12 2.9%; x__era5l_slhf_lag1 2.3%; x__hist_mean_60 1.9%; x__aet_total_mm_roll3 1.6%; x__era5l_slhf 1.4%; x__hist_last_2 1.2%; x__hist_mean_all 1.2%; x__era5l_str_lag1 1.1%; x__V02_total_precip_mm_roll3 1.0%

## Families (sums of the variable-level attributions per row)

| Family | rival_bardl_h1 | rival_lgbm | rival_rf | rival_ridge | treeroute |
|---|---|---|---|---|---|
| own history | 35.2% | 25.5% | 4.2% | 25.7% | 24.5% |
| global indices | 0.0% | 15.6% | 11.3% | 11.4% | 8.0% |
| local drivers | 64.8% | 59.0% | 84.4% | 62.9% | 67.5% |
| context and calendar | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| seasonal normal | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
