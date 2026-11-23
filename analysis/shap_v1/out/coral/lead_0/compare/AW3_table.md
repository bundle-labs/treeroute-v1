# AW3: disagreement of SHAP importances, coral lead 0 (post hoc, ruling AK)

1000 rows in 37 regions; link space; percentile 95% intervals from 2000 paired region draws. Same-link pairs are comparable; cross-link pairs are shown for completeness and are not comparable in scale or rank. A rival declined by its own guard is labelled and kept out of W, the consensus and the main row (D6).

Models and links: rival_hgb_l1 (arcsine|c=0.1084375|ub=100); rival_lgbm (arcsine|c=0.1084375|ub=100); rival_lgbm_tweedie (log_mu|c=0.1084375|ub=100); rival_rf (arcsine|c=0.1084375|ub=100); rival_ridge (log_c|c=0.1084375|ub=100); treeroute (arcsine|c=0.1084375|ub=100)

Main set: rival_hgb_l1, rival_lgbm, rival_rf, treeroute

## variable level (26 players, 25 active; structural zeros: normal)

| Pair | label | spearman | spearman_top20_union | kendall_tau_b | jaccard_top5 | jaccard_top10 | rbo_p0.9 | rbo_p0.95 | tvd | tvd_family | sign_agreement_top10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rival_hgb_l1 vs rival_lgbm | same-link | 0.70 [0.63, 0.76] | 0.62 [0.49, 0.70] | 0.56 [0.47, 0.59] | 0.25 [0.25, 0.43] | 0.43 [0.43, 0.67] | 0.58 [0.52, 0.65] | 0.74 [0.70, 0.78] | 0.31 [0.26, 0.37] | 0.07 [0.04, 0.10] | 1.00 (10 signs) |
| rival_hgb_l1 vs rival_lgbm_tweedie | cross-link (not comparable in scale or rank) | 0.70 [0.64, 0.75] | 0.49 [0.42, 0.63] | 0.53 [0.47, 0.59] | 0.25 [0.11, 0.43] | 0.43 [0.43, 0.67] | 0.57 [0.54, 0.71] | 0.73 [0.71, 0.81] | 0.24 [0.21, 0.28] | 0.09 [0.04, 0.13] | 1.00 (10 signs) |
| rival_hgb_l1 vs rival_rf | same-link | 0.75 [0.72, 0.82] | 0.68 [0.61, 0.78] | 0.58 [0.53, 0.65] | 0.43 [0.43, 0.67] | 0.54 [0.43, 0.82] | 0.59 [0.57, 0.67] | 0.75 [0.73, 0.79] | 0.32 [0.26, 0.38] | 0.13 [0.10, 0.16] | 1.00 (10 signs) |
| rival_hgb_l1 vs rival_ridge | cross-link (not comparable in scale or rank) | 0.34 [0.24, 0.42] | 0.19 [0.05, 0.32] | 0.23 [0.16, 0.30] | 0.25 [0.25, 0.43] | 0.33 [0.25, 0.54] | 0.47 [0.42, 0.50] | 0.65 [0.62, 0.67] | 0.41 [0.39, 0.44] | 0.06 [0.04, 0.12] | 0.78 (9 signs) |
| rival_hgb_l1 vs treeroute | same-link | 0.50 [0.40, 0.57] | 0.48 [0.38, 0.56] | 0.39 [0.28, 0.43] | 0.43 [0.43, 0.67] | 0.43 [0.43, 0.67] | 0.71 [0.64, 0.82] | 0.79 [0.76, 0.85] | 0.23 [0.21, 0.28] | 0.12 [0.10, 0.17] | 0.88 (8 signs) |
| rival_lgbm vs rival_lgbm_tweedie | cross-link (not comparable in scale or rank) | 0.83 [0.75, 0.86] | 0.76 [0.64, 0.81] | 0.66 [0.58, 0.69] | 0.67 [0.67, 1.00] | 0.67 [0.54, 0.82] | 0.65 [0.60, 0.71] | 0.79 [0.75, 0.82] | 0.24 [0.20, 0.28] | 0.15 [0.11, 0.18] | 1.00 (9 signs) |
| rival_lgbm vs rival_rf | same-link | 0.96 [0.91, 0.96] | 0.91 [0.82, 0.94] | 0.85 [0.77, 0.87] | 0.67 [0.67, 0.67] | 0.54 [0.54, 0.82] | 0.90 [0.82, 0.93] | 0.93 [0.88, 0.95] | 0.15 [0.13, 0.17] | 0.07 [0.04, 0.10] | 1.00 (9 signs) |
| rival_lgbm vs rival_ridge | cross-link (not comparable in scale or rank) | 0.49 [0.40, 0.58] | 0.27 [0.16, 0.43] | 0.35 [0.28, 0.43] | 0.25 [0.25, 0.25] | 0.43 [0.25, 0.54] | 0.57 [0.49, 0.70] | 0.72 [0.67, 0.78] | 0.32 [0.30, 0.37] | 0.04 [0.01, 0.11] | 0.78 (9 signs) |
| rival_lgbm vs treeroute | same-link | 0.45 [0.29, 0.52] | 0.41 [0.24, 0.49] | 0.31 [0.18, 0.39] | 0.67 [0.43, 0.67] | 0.54 [0.43, 0.67] | 0.62 [0.53, 0.67] | 0.74 [0.68, 0.77] | 0.33 [0.28, 0.39] | 0.13 [0.10, 0.18] | 0.89 (9 signs) |
| rival_lgbm_tweedie vs rival_rf | cross-link (not comparable in scale or rank) | 0.81 [0.73, 0.85] | 0.73 [0.61, 0.80] | 0.63 [0.55, 0.68] | 0.67 [0.43, 0.67] | 0.67 [0.54, 0.82] | 0.63 [0.58, 0.71] | 0.77 [0.74, 0.81] | 0.32 [0.28, 0.36] | 0.22 [0.18, 0.26] | 1.00 (8 signs) |
| rival_lgbm_tweedie vs rival_ridge | cross-link (not comparable in scale or rank) | 0.41 [0.36, 0.54] | 0.25 [0.17, 0.41] | 0.29 [0.25, 0.39] | 0.25 [0.11, 0.25] | 0.43 [0.33, 0.54] | 0.49 [0.42, 0.55] | 0.67 [0.63, 0.70] | 0.36 [0.35, 0.38] | 0.11 [0.07, 0.17] | 0.67 (9 signs) |
| rival_lgbm_tweedie vs treeroute | cross-link (not comparable in scale or rank) | 0.49 [0.36, 0.57] | 0.46 [0.32, 0.55] | 0.37 [0.25, 0.45] | 0.67 [0.25, 0.67] | 0.67 [0.43, 0.82] | 0.72 [0.56, 0.75] | 0.80 [0.71, 0.82] | 0.27 [0.25, 0.31] | 0.19 [0.16, 0.26] | 0.88 (8 signs) |
| rival_rf vs rival_ridge | cross-link (not comparable in scale or rank) | 0.57 [0.50, 0.65] | 0.39 [0.32, 0.54] | 0.42 [0.36, 0.50] | 0.43 [0.43, 0.43] | 0.43 [0.33, 0.67] | 0.62 [0.53, 0.75] | 0.74 [0.70, 0.82] | 0.35 [0.32, 0.38] | 0.11 [0.05, 0.18] | 0.67 (9 signs) |
| rival_rf vs treeroute | same-link | 0.52 [0.46, 0.62] | 0.49 [0.43, 0.61] | 0.37 [0.29, 0.47] | 1.00 [0.67, 1.00] | 0.54 [0.54, 0.67] | 0.63 [0.60, 0.72] | 0.75 [0.73, 0.81] | 0.29 [0.22, 0.37] | 0.10 [0.06, 0.17] | 0.88 (8 signs) |
| rival_ridge vs treeroute | cross-link (not comparable in scale or rank) | 0.57 [0.40, 0.65] | 0.51 [0.32, 0.62] | 0.39 [0.25, 0.46] | 0.43 [0.43, 0.67] | 0.67 [0.43, 0.82] | 0.57 [0.49, 0.61] | 0.72 [0.67, 0.75] | 0.35 [0.32, 0.39] | 0.16 [0.10, 0.24] | 0.86 (7 signs) |

Kendall's W (main set) = 0.73 [0.69, 0.76]; mean pairwise Spearman (main set) = 0.65 [0.59, 0.68].
Stability under region resampling (mean Spearman of a model's full-sample importances with its own bootstrap replicates; descriptive, not a ceiling on between-model agreement): rival_hgb_l1 0.98, rival_lgbm 0.97, rival_lgbm_tweedie 0.98, rival_rf 0.98, rival_ridge 0.97, treeroute 0.98

- rival_hgb_l1 top-10 (25 nonzero): hs 14.2%; nino34a 13.4%; dhw 9.2%; mhw_icum 6.4%; days_since_max_hs 6.4%; mhw_days 6.4%; cool 4.9%; calendar 4.7%; ctx:mmm 4.0%; ctx:abslat 3.7%
- rival_lgbm top-10 (25 nonzero): n_above_mmm1 21.0%; dhw 11.2%; nino34a 9.0%; mhw_days 9.0%; calendar 8.4%; n_above_mmm 4.6%; hs 3.9%; days_since_max_hs 3.5%; cyc_mindist 3.1%; mhw_nev 3.1%
- rival_lgbm_tweedie top-10 (25 nonzero): nino34a 13.1%; calendar 10.0%; n_above_mmm1 8.1%; mhw_days 8.1%; hs 5.5%; cyc_mindist 5.2%; cool 5.2%; dhw 4.8%; n_above_mmm 4.3%; mhw_thr_gap 3.9%
- rival_rf top-10 (25 nonzero): n_above_mmm1 21.7%; dhw 14.9%; mhw_days 11.2%; nino34a 10.1%; hs 9.0%; n_above_mmm 4.4%; cool 3.6%; calendar 3.1%; cyc_maxw 2.7%; ctx:mmm 2.2%
- rival_ridge top-10 (25 nonzero): slope 15.1%; n_above_mmm1 14.6%; dhw 10.3%; cool 10.0%; hs 5.8%; mhw_days 4.2%; mhw_durmax 3.8%; mhw_icum 3.4%; n_above_mmm 3.3%; mhw_nev 3.1%
- treeroute top-10 (25 nonzero): nino34a 15.3%; hs 12.9%; dhw 11.6%; n_above_mmm1 10.1%; mhw_days 6.7%; n_above_mmm 6.0%; cool 5.9%; mhw_icum 4.4%; mhw_durmax 3.0%; cyc_mindist 2.8%

## feature level (69 players, 68 active; structural zeros: normal)

| Pair | label | spearman | spearman_top20_union | kendall_tau_b | jaccard_top5 | jaccard_top10 | rbo_p0.9 | rbo_p0.95 | tvd | sign_agreement_top10 |
|---|---|---|---|---|---|---|---|---|---|---|
| rival_hgb_l1 vs rival_lgbm | same-link | 0.50 [0.44, 0.55] | -0.28 [-0.44, -0.14] | 0.39 [0.34, 0.43] | 0.11 [0.11, 0.25] | 0.33 [0.11, 0.33] | 0.33 [0.26, 0.41] | 0.48 [0.42, 0.53] | 0.37 [0.32, 0.43] | 1.00 (7 signs) |
| rival_hgb_l1 vs rival_lgbm_tweedie | cross-link (not comparable in scale or rank) | 0.66 [0.58, 0.71] | -0.06 [-0.19, 0.05] | 0.51 [0.44, 0.56] | 0.11 [0.11, 0.25] | 0.33 [0.18, 0.43] | 0.40 [0.32, 0.49] | 0.54 [0.48, 0.58] | 0.31 [0.28, 0.35] | 1.00 (9 signs) |
| rival_hgb_l1 vs rival_rf | same-link | 0.57 [0.53, 0.62] | -0.13 [-0.29, -0.01] | 0.47 [0.43, 0.50] | 0.00 [0.00, 0.11] | 0.18 [0.05, 0.25] | 0.25 [0.21, 0.28] | 0.43 [0.40, 0.46] | 0.41 [0.37, 0.46] | 1.00 (11 signs) |
| rival_hgb_l1 vs rival_ridge | cross-link (not comparable in scale or rank) | 0.21 [0.15, 0.28] | -0.60 [-0.66, -0.53] | 0.13 [0.09, 0.18] | 0.11 [0.00, 0.11] | 0.05 [0.05, 0.11] | 0.13 [0.10, 0.18] | 0.28 [0.26, 0.31] | 0.55 [0.53, 0.58] | 0.67 (6 signs) |
| rival_hgb_l1 vs treeroute | same-link | 0.33 [0.28, 0.39] | 0.10 [-0.11, 0.18] | 0.24 [0.20, 0.29] | 0.25 [0.11, 0.43] | 0.43 [0.18, 0.54] | 0.44 [0.35, 0.54] | 0.52 [0.45, 0.58] | 0.35 [0.32, 0.39] | 1.00 (6 signs) |
| rival_lgbm vs rival_lgbm_tweedie | cross-link (not comparable in scale or rank) | 0.70 [0.66, 0.73] | 0.24 [0.03, 0.34] | 0.54 [0.50, 0.56] | 0.25 [0.11, 0.43] | 0.43 [0.25, 0.54] | 0.51 [0.38, 0.53] | 0.60 [0.52, 0.63] | 0.27 [0.25, 0.31] | 1.00 (10 signs) |
| rival_lgbm vs rival_rf | same-link | 0.88 [0.85, 0.89] | 0.36 [0.18, 0.51] | 0.73 [0.69, 0.74] | 0.43 [0.11, 0.43] | 0.43 [0.25, 0.54] | 0.62 [0.53, 0.68] | 0.71 [0.64, 0.74] | 0.21 [0.19, 0.23] | 1.00 (11 signs) |
| rival_lgbm vs rival_ridge | cross-link (not comparable in scale or rank) | 0.32 [0.28, 0.40] | -0.50 [-0.57, -0.37] | 0.21 [0.18, 0.27] | 0.11 [0.00, 0.25] | 0.11 [0.11, 0.18] | 0.19 [0.16, 0.27] | 0.34 [0.32, 0.40] | 0.49 [0.46, 0.54] | 0.70 (10 signs) |
| rival_lgbm vs treeroute | same-link | 0.41 [0.31, 0.51] | -0.25 [-0.42, 0.09] | 0.31 [0.23, 0.39] | 0.11 [0.11, 0.25] | 0.18 [0.05, 0.33] | 0.27 [0.21, 0.39] | 0.41 [0.36, 0.50] | 0.35 [0.32, 0.39] | 0.90 (10 signs) |
| rival_lgbm_tweedie vs rival_rf | cross-link (not comparable in scale or rank) | 0.57 [0.54, 0.63] | -0.01 [-0.19, 0.11] | 0.42 [0.40, 0.47] | 0.11 [0.00, 0.25] | 0.25 [0.11, 0.33] | 0.31 [0.24, 0.37] | 0.45 [0.40, 0.50] | 0.39 [0.36, 0.41] | 1.00 (11 signs) |
| rival_lgbm_tweedie vs rival_ridge | cross-link (not comparable in scale or rank) | 0.21 [0.14, 0.30] | -0.48 [-0.59, -0.37] | 0.14 [0.08, 0.19] | 0.00 [0.00, 0.11] | 0.11 [0.00, 0.18] | 0.12 [0.10, 0.18] | 0.28 [0.26, 0.33] | 0.51 [0.48, 0.54] | 0.60 (10 signs) |
| rival_lgbm_tweedie vs treeroute | cross-link (not comparable in scale or rank) | 0.31 [0.28, 0.40] | -0.28 [-0.39, -0.09] | 0.25 [0.22, 0.31] | 0.25 [0.25, 0.43] | 0.18 [0.11, 0.25] | 0.49 [0.30, 0.56] | 0.52 [0.41, 0.57] | 0.30 [0.29, 0.33] | 0.89 (9 signs) |
| rival_rf vs rival_ridge | cross-link (not comparable in scale or rank) | 0.40 [0.34, 0.45] | -0.33 [-0.43, -0.28] | 0.26 [0.23, 0.31] | 0.11 [0.00, 0.25] | 0.18 [0.11, 0.25] | 0.22 [0.18, 0.28] | 0.37 [0.34, 0.41] | 0.50 [0.48, 0.54] | 0.80 (10 signs) |
| rival_rf vs treeroute | same-link | 0.56 [0.45, 0.66] | 0.04 [-0.18, 0.41] | 0.41 [0.33, 0.50] | 0.25 [0.11, 0.43] | 0.33 [0.18, 0.54] | 0.34 [0.28, 0.46] | 0.49 [0.43, 0.58] | 0.36 [0.33, 0.40] | 1.00 (12 signs) |
| rival_ridge vs treeroute | cross-link (not comparable in scale or rank) | 0.41 [0.28, 0.50] | -0.48 [-0.60, -0.19] | 0.27 [0.19, 0.34] | 0.00 [0.00, 0.11] | 0.05 [0.00, 0.25] | 0.15 [0.10, 0.24] | 0.33 [0.27, 0.40] | 0.45 [0.41, 0.50] | 0.62 (8 signs) |

Kendall's W (main set) = 0.65 [0.63, 0.69]; mean pairwise Spearman (main set) = 0.54 [0.50, 0.58].
Stability under region resampling (mean Spearman of a model's full-sample importances with its own bootstrap replicates; descriptive, not a ceiling on between-model agreement): rival_hgb_l1 0.98, rival_lgbm 0.99, rival_lgbm_tweedie 0.99, rival_rf 0.99, rival_ridge 0.99, treeroute 0.97

- rival_hgb_l1 top-10 (68 nonzero): x__hs_max_56 9.1%; x__nino34a_lag6 7.7%; x__mhw_icum_90 5.4%; x__days_since_max_hs 5.4%; x__dhw_84 4.8%; x__mhw_days_90 4.1%; c__ctx_mmm 3.4%; c__ctx_abslat 3.2%; x__nino34a_lag3 2.9%; c__ctx_doy_cos 2.9%
- rival_lgbm top-10 (67 nonzero): x__n_above_mmm1_90 10.6%; c__ctx_doy_sin 5.1%; x__nino34a_lag6 5.0%; x__n_above_mmm1_84 4.6%; x__dhw_90 3.7%; c__ctx_doy_cos 3.1%; x__mhw_days_90 3.1%; x__days_since_max_hs 3.0%; x__nino34a_lag3 2.9%; x__mhw_days_30 2.9%
- rival_lgbm_tweedie top-10 (68 nonzero): x__nino34a_lag6 5.3%; c__ctx_doy_sin 5.1%; x__nino34a_lag3 4.9%; c__ctx_doy_cos 4.3%; x__mhw_days_90 3.2%; x__mhw_thr_gap 3.2%; x__mhw_days_365 3.0%; c__ctx_mmm 3.0%; x__slope_90 2.9%; x__n_above_mmm1_90 2.8%
- rival_rf top-10 (68 nonzero): x__n_above_mmm1_90 11.4%; x__hs_max_30 6.2%; x__dhw_90 6.1%; x__nino34a_lag3 5.2%; x__n_above_mmm1_84 4.5%; x__mhw_days_90 4.5%; x__mhw_days_365 3.8%; x__mhw_days_30 3.3%; x__dhw_84 3.2%; x__nino34a_lag9 3.1%
- rival_ridge top-10 (68 nonzero): x__cool_90 12.0%; x__dhw_84 7.0%; x__slope_90 6.6%; x__cool_84 6.5%; x__n_above_mmm1_90 5.2%; x__cool_56 4.4%; x__n_above_mmm1_84 4.1%; x__hs_max_84 3.4%; x__n_above_mmm_84 2.6%; x__hs_max_90 2.5%
- treeroute top-10 (68 nonzero): x__nino34a_lag6 6.3%; x__nino34a_lag3 4.2%; x__nino34a_lag9 3.9%; x__mhw_icum_90 3.7%; x__hs_max_30 3.4%; x__mhw_days_90 2.7%; x__mhw_durmax_365 2.5%; x__hs_max_56 2.5%; x__dhw_56 2.4%; x__dhw_84 2.4%

## Families (sums of the variable-level attributions per row)

| Family | rival_hgb_l1 | rival_lgbm | rival_lgbm_tweedie | rival_rf | rival_ridge | treeroute |
|---|---|---|---|---|---|---|
| own history | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| global indices | 19.4% | 12.6% | 21.5% | 12.2% | 13.2% | 22.2% |
| local drivers | 68.2% | 74.6% | 59.6% | 81.5% | 70.6% | 77.6% |
| context and calendar | 12.4% | 12.8% | 18.9% | 6.4% | 16.2% | 0.2% |
| seasonal normal | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |

## Nonzero forecasts of arcsine-link models (rows with pre > 0)

- rival_hgb_l1, 983 rows: hs 14.2%; nino34a 13.4%; dhw 9.2%; days_since_max_hs 6.4%; mhw_icum 6.4%; mhw_days 6.4%; cool 4.9%; calendar 4.7%; ctx:mmm 4.0%; ctx:abslat 3.7%
- rival_lgbm, 995 rows: n_above_mmm1 21.0%; dhw 11.2%; nino34a 9.0%; mhw_days 9.0%; calendar 8.4%; n_above_mmm 4.6%; hs 3.9%; days_since_max_hs 3.5%; cyc_mindist 3.1%; mhw_nev 3.1%
- rival_rf, 1000 rows: n_above_mmm1 21.7%; dhw 14.9%; mhw_days 11.2%; nino34a 10.1%; hs 9.0%; n_above_mmm 4.4%; cool 3.6%; calendar 3.1%; cyc_maxw 2.7%; ctx:mmm 2.2%
- treeroute, 973 rows: nino34a 15.3%; hs 12.9%; dhw 11.5%; n_above_mmm1 10.1%; mhw_days 6.7%; n_above_mmm 6.0%; cool 5.9%; mhw_icum 4.4%; mhw_durmax 3.0%; cyc_mindist 2.8%
