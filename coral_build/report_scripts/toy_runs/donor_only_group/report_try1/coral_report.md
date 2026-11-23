# Coral report-only tables (coral_report.py 1.0.0)

**NOT HEADLINE: smoke run: plumbing only (R21), smoke deltas carry no sign information**

- Run folder: `D:\treeroute\coral_build\report_scripts\toy_runs\donor_only_group\runs\toy_table\smoke\20261020_9db32590` (kind smoke, package toy_table)
- Script SHA-256: `c3cd534cbc4895147a6a8220928a790158f789c303b4e456c2bbaeee4ed4a793`; every input file's SHA-256 is in inputs_manifest.json.
- Report only: nothing here changes a fit, a pick or the verdict (draft section 6.2).
- Every forecast is read as "given a survey on this date". The 365-day row is risk stratification.
- Predict-zero and the donor-row median MAE are printed beside every MAE, on the same rows.

## 1. Per programme (stratum `source`)

Values with fewer than 10 rows are shown with n only. Full metrics for every column are in per_programme.csv.

### Lead 0 (all rows; adopted `arm__identity_plain_gls`)

| stratum_value | column | n | zero_share | mae | mae_predict_zero | mae_donor_median | hit | corr2 | n_only |
|---|---|---|---|---|---|---|---|---|---|
| ALL | arm__arcsine_trees_off_unweighted | 42 | 0.310 | 25.170 | 29.602 | 21.477 | 0.167 | 0.006 | no |
| ALL | arm__identity_plain_gls | 42 | 0.310 | 22.723 | 29.602 | 21.477 | 0.214 | 0.000 | no |
| ALL | arm__identity_trees_off_unweighted | 42 | 0.310 | 22.245 | 29.602 | 21.477 | 0.190 | 0.000 | no |
| ALL | arm__log_c_trees_off_unweighted | 42 | 0.310 | 24.547 | 29.602 | 21.477 | 0.167 | 0.009 | no |
| ALL | base__donor_median | 42 | 0.310 | 21.477 | 29.602 | 21.477 | 0.190 |  | no |
| ALL | base__predict_zero | 42 | 0.310 | 29.602 | 29.602 | 21.477 | 0.357 |  | no |
| field | arm__arcsine_trees_off_unweighted | 13 | 0.308 | 22.427 | 28.376 | 18.920 | 0.308 | 0.006 | no |
| field | arm__identity_plain_gls | 13 | 0.308 | 19.964 | 28.376 | 18.920 | 0.308 | 0.001 | no |
| field | arm__identity_trees_off_unweighted | 13 | 0.308 | 19.069 | 28.376 | 18.920 | 0.231 | 0.009 | no |
| field | arm__log_c_trees_off_unweighted | 13 | 0.308 | 21.849 | 28.376 | 18.920 | 0.231 | 0.007 | no |
| field | base__donor_median | 13 | 0.308 | 18.920 | 28.376 | 18.920 | 0.308 |  | no |
| field | base__predict_zero | 13 | 0.308 | 28.376 | 28.376 | 18.920 | 0.308 |  | no |
| lab | arm__arcsine_trees_off_unweighted | 14 | 0.357 | 24.266 | 26.764 | 21.166 | 0.071 | 0.045 | no |
| lab | arm__identity_plain_gls | 14 | 0.357 | 22.345 | 26.764 | 21.166 | 0.143 | 0.009 | no |
| lab | arm__identity_trees_off_unweighted | 14 | 0.357 | 22.305 | 26.764 | 21.166 | 0.143 | 0.009 | no |
| lab | arm__log_c_trees_off_unweighted | 14 | 0.357 | 23.722 | 26.764 | 21.166 | 0.071 | 0.054 | no |
| lab | base__donor_median | 14 | 0.357 | 21.166 | 26.764 | 21.166 | 0.143 |  | no |
| lab | base__predict_zero | 14 | 0.357 | 26.764 | 26.764 | 21.166 | 0.429 |  | no |
| remote | arm__arcsine_trees_off_unweighted | 15 | 0.267 | 28.391 | 33.313 | 23.982 | 0.133 | 0.023 | no |
| remote | arm__identity_plain_gls | 15 | 0.267 | 25.466 | 33.313 | 23.982 | 0.200 | 0.001 | no |
| remote | arm__identity_trees_off_unweighted | 15 | 0.267 | 24.940 | 33.313 | 23.982 | 0.200 | 0.001 | no |
| remote | arm__log_c_trees_off_unweighted | 15 | 0.267 | 27.654 | 33.313 | 23.982 | 0.200 | 0.031 | no |
| remote | base__donor_median | 15 | 0.267 | 23.982 | 33.313 | 23.982 | 0.133 |  | no |
| remote | base__predict_zero | 15 | 0.267 | 33.313 | 33.313 | 23.982 | 0.333 |  | no |


### Lead 183 (all rows; adopted `arm__identity_plain_gls`)

| stratum_value | column | n | zero_share | mae | mae_predict_zero | mae_donor_median | hit | corr2 | n_only |
|---|---|---|---|---|---|---|---|---|---|
| ALL | arm__identity_plain_gls | 42 | 0.310 | 22.320 | 29.602 | 21.477 | 0.214 | 0.003 | no |
| ALL | arm__identity_trees_off_unweighted | 42 | 0.310 | 22.137 | 29.602 | 21.477 | 0.214 | 0.001 | no |
| ALL | base__damped_persistence | 5 | 0.800 | 45.273 | 15.348 | 32.267 | 0.000 | 0.349 | no |
| ALL | base__donor_median | 42 | 0.310 | 21.477 | 29.602 | 21.477 | 0.190 |  | no |
| ALL | base__persistence | 5 | 0.800 | 58.398 | 15.348 | 32.267 | 0.000 | 0.937 | no |
| ALL | base__predict_zero | 42 | 0.310 | 29.602 | 29.602 | 21.477 | 0.357 |  | no |
| field | arm__identity_plain_gls | 13 | 0.308 | 19.559 | 28.376 | 18.920 | 0.308 | 0.006 | no |
| field | arm__identity_trees_off_unweighted | 13 | 0.308 | 18.902 | 28.376 | 18.920 | 0.308 | 0.006 | no |
| field | base__damped_persistence | 1 | 1.000 | 32.106 | 0.000 | 28.198 | 0.000 |  | no |
| field | base__donor_median | 13 | 0.308 | 18.920 | 28.376 | 18.920 | 0.308 |  | no |
| field | base__persistence | 1 | 1.000 | 64.213 | 0.000 | 28.198 | 0.000 |  | no |
| field | base__predict_zero | 13 | 0.308 | 28.376 | 28.376 | 18.920 | 0.308 |  | no |
| lab | arm__identity_plain_gls | 14 | 0.357 | 22.353 | 26.764 | 21.166 | 0.143 | 0.004 | no |
| lab | arm__identity_trees_off_unweighted | 14 | 0.357 | 22.588 | 26.764 | 21.166 | 0.143 | 0.018 | no |
| lab | base__damped_persistence | 2 | 1.000 | 51.177 | 0.000 | 28.198 | 0.000 |  | no |
| lab | base__donor_median | 14 | 0.357 | 21.166 | 26.764 | 21.166 | 0.143 |  | no |
| lab | base__persistence | 2 | 1.000 | 51.668 | 0.000 | 28.198 | 0.000 |  | no |
| lab | base__predict_zero | 14 | 0.357 | 26.764 | 26.764 | 21.166 | 0.429 |  | no |
| remote | arm__identity_plain_gls | 15 | 0.267 | 24.683 | 33.313 | 23.982 | 0.200 | 0.009 | no |
| remote | arm__identity_trees_off_unweighted | 15 | 0.267 | 24.521 | 33.313 | 23.982 | 0.200 | 0.007 | no |
| remote | base__damped_persistence | 2 | 0.500 | 45.952 | 38.369 | 38.369 | 0.000 | 1.000 | no |
| remote | base__donor_median | 15 | 0.267 | 23.982 | 33.313 | 23.982 | 0.133 |  | no |
| remote | base__persistence | 2 | 0.500 | 62.220 | 38.369 | 38.369 | 0.000 | 1.000 | no |
| remote | base__predict_zero | 15 | 0.267 | 33.313 | 33.313 | 23.982 | 0.333 |  | no |


### Lead 365 (all rows; adopted `arm__identity_plain_gls`)

| stratum_value | column | n | zero_share | mae | mae_predict_zero | mae_donor_median | hit | corr2 | n_only |
|---|---|---|---|---|---|---|---|---|---|
| ALL | arm__identity_plain_gls | 39 | 0.333 | 23.452 | 28.520 | 22.691 | 0.205 | 0.000 | no |
| ALL | arm__identity_trees_off_unweighted | 39 | 0.333 | 22.957 | 28.520 | 22.691 | 0.205 | 0.001 | no |
| ALL | base__damped_persistence | 5 | 0.800 | 45.077 | 15.348 | 28.018 | 0.000 | 0.347 | no |
| ALL | base__donor_median | 39 | 0.333 | 22.691 | 28.520 | 22.691 | 0.179 |  | no |
| ALL | base__persistence | 5 | 0.800 | 58.398 | 15.348 | 28.018 | 0.000 | 0.937 | no |
| ALL | base__predict_zero | 39 | 0.333 | 28.520 | 28.520 | 22.691 | 0.385 |  | no |
| field | arm__identity_plain_gls | 12 | 0.333 | 18.834 | 25.766 | 18.788 | 0.333 | 0.002 | no |
| field | arm__identity_trees_off_unweighted | 12 | 0.333 | 18.550 | 25.766 | 18.788 | 0.333 | 0.000 | no |
| field | base__damped_persistence | 1 | 1.000 | 32.106 | 0.000 | 21.117 | 0.000 |  | no |
| field | base__donor_median | 12 | 0.333 | 18.788 | 25.766 | 18.788 | 0.250 |  | no |
| field | base__persistence | 1 | 1.000 | 64.213 | 0.000 | 21.117 | 0.000 |  | no |
| field | base__predict_zero | 12 | 0.333 | 25.766 | 25.766 | 18.788 | 0.333 |  | no |
| lab | arm__identity_plain_gls | 14 | 0.357 | 23.802 | 26.764 | 22.178 | 0.143 | 0.070 | no |
| lab | arm__identity_trees_off_unweighted | 14 | 0.357 | 23.158 | 26.764 | 22.178 | 0.143 | 0.037 | no |
| lab | base__damped_persistence | 2 | 1.000 | 50.686 | 0.000 | 21.117 | 0.000 |  | no |
| lab | base__donor_median | 14 | 0.357 | 22.178 | 26.764 | 22.178 | 0.143 |  | no |
| lab | base__persistence | 2 | 1.000 | 51.668 | 0.000 | 21.117 | 0.000 |  | no |
| lab | base__predict_zero | 14 | 0.357 | 26.764 | 26.764 | 22.178 | 0.429 |  | no |
| remote | arm__identity_plain_gls | 13 | 0.308 | 27.339 | 32.952 | 26.845 | 0.154 | 0.007 | no |
| remote | arm__identity_trees_off_unweighted | 13 | 0.308 | 26.809 | 32.952 | 26.845 | 0.154 | 0.000 | no |
| remote | base__damped_persistence | 2 | 0.500 | 45.952 | 38.369 | 38.369 | 0.000 | 1.000 | no |
| remote | base__donor_median | 13 | 0.308 | 26.845 | 32.952 | 26.845 | 0.154 |  | no |
| remote | base__persistence | 2 | 0.500 | 62.220 | 38.369 | 38.369 | 0.000 | 1.000 | no |
| remote | base__predict_zero | 13 | 0.308 | 32.952 | 32.952 | 26.845 | 0.385 |  | no |


### Programme verdict lines (D74 rule, report only; the ALL line is the registered verdict's rows)

| lead | rows_basis | stratum_value | n_rows | n_groups | mean | se | low | high | tag | matches_engine |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | all | ALL | 42 | 3 | -1.144 | 1.249 | -3.592 | 1.304 | cannot_tell | yes |
| 0 | all | field | 13 | 3 | -2.727 | 2.859 | -8.332 | 2.877 | cannot_tell |  |
| 0 | all | lab | 14 | 3 | -0.292 | 1.265 | -2.772 | 2.188 | cannot_tell |  |
| 0 | all | remote | 15 | 3 | -1.980 | 0.853 | -3.652 | -0.307 | hurts |  |
| 0 | common | ALL | 39 | 3 | -1.113 | 1.136 | -3.339 | 1.114 | cannot_tell | yes |
| 0 | common | field | 12 | 3 | -2.903 | 2.692 | -8.179 | 2.374 | cannot_tell |  |
| 0 | common | lab | 14 | 3 | -0.292 | 1.265 | -2.772 | 2.188 | cannot_tell |  |
| 0 | common | remote | 13 | 3 | -1.655 | 1.282 | -4.167 | 0.857 | cannot_tell |  |
| 183 | common | ALL | 39 | 3 | -0.809 | 0.954 | -2.678 | 1.060 | cannot_tell | yes |
| 183 | common | field | 12 | 3 | -2.392 | 2.512 | -7.316 | 2.531 | cannot_tell |  |
| 183 | common | lab | 14 | 3 | -0.667 | 0.779 | -2.194 | 0.859 | cannot_tell |  |
| 183 | common | remote | 13 | 3 | -1.052 | 1.217 | -3.437 | 1.334 | cannot_tell |  |
| 365 | common | ALL | 39 | 3 | -0.699 | 0.700 | -2.072 | 0.673 | cannot_tell | yes |
| 365 | common | field | 12 | 3 | -0.984 | 2.065 | -5.032 | 3.063 | cannot_tell |  |
| 365 | common | lab | 14 | 3 | -1.509 | 1.464 | -4.379 | 1.360 | cannot_tell |  |
| 365 | common | remote | 13 | 3 | -1.093 | 1.739 | -4.502 | 2.317 | cannot_tell |  |

## 2. By magnitude (a target-defined diagnostic, not a headline)

Edges from the donor rows at each lead's fit cut (train rows only):

| lead | fit_cut | donor_rows | donor_rows_engine | donor_median | positive_donor_rows | pos_q25 | pos_q50 | pos_q75 | q75_all_donor_labels |
|---|---|---|---|---|---|---|---|---|---|
| 0.000 | 733041.000 | 123.000 | 123.000 | 28.198 | 70.000 | 36.989 | 48.241 | 60.273 | 51.139 |
| 183.000 | 732859.000 | 115.000 | 115.000 | 28.198 | 63.000 | 39.392 | 50.745 | 62.349 | 51.952 |
| 365.000 | 732677.000 | 106.000 | 106.000 | 21.117 | 56.000 | 40.262 | 50.274 | 59.566 | 51.226 |

### Lead 0, adopted `arm__identity_plain_gls`

| stratum_value | bin | n | mean_y | mean_pred | mae | mae_predict_zero | mae_donor_median | n_only |
|---|---|---|---|---|---|---|---|---|
| ALL | B0 zero | 13 | 0.000 | 29.318 | 29.318 | 0.000 | 28.198 | no |
| ALL | B1 (0, q25] | 9 | 23.291 | 19.764 | 6.582 | 23.291 | 7.306 | no |
| ALL | B2 (q25, q50] | 10 | 43.993 | 23.829 | 20.163 | 43.993 | 15.794 | no |
| ALL | B3 (q50, q75] | 6 | 53.725 | 26.242 | 27.483 | 53.725 | 25.527 | no |
| ALL | B4 (q75, max] | 4 | 67.842 | 30.983 | 36.860 | 67.842 | 39.644 | no |
| field | B0 zero | 4 | 0.000 | 28.624 | 28.624 | 0.000 | 28.198 | no |
| field | B1 (0, q25] | 3 | 25.385 | 20.160 | 5.225 | 25.385 | 3.209 | no |
| field | B2 (q25, q50] | 3 | 42.845 | 26.375 | 16.469 | 42.845 | 14.646 | no |
| field | B3 (q50, q75] | 3 | 54.732 | 28.083 | 26.649 | 54.732 | 26.534 | no |
| field | B4 (q75, max] | 0 |  |  |  |  |  | no |
| lab | B0 zero | 5 | 0.000 | 28.345 | 28.345 | 0.000 | 28.198 | no |
| lab | B1 (0, q25] | 3 | 25.861 | 18.268 | 9.707 | 25.861 | 9.138 | no |
| lab | B2 (q25, q50] | 4 | 45.316 | 25.141 | 20.175 | 45.316 | 17.118 | no |
| lab | B3 (q50, q75] | 1 | 55.421 | 23.066 | 32.355 | 55.421 | 27.223 | no |
| lab | B4 (q75, max] | 1 | 60.426 | 31.497 | 28.929 | 60.426 | 32.228 | no |
| remote | B0 zero | 4 | 0.000 | 31.228 | 31.228 | 0.000 | 28.198 | no |
| remote | B1 (0, q25] | 3 | 18.627 | 20.863 | 4.814 | 18.627 | 9.571 | no |
| remote | B2 (q25, q50] | 3 | 43.376 | 19.534 | 23.842 | 43.376 | 15.178 | no |
| remote | B3 (q50, q75] | 2 | 51.366 | 25.068 | 26.299 | 51.366 | 23.168 | no |
| remote | B4 (q75, max] | 3 | 70.315 | 30.811 | 39.503 | 70.315 | 42.116 | no |

### Lead 183, adopted `arm__identity_plain_gls`

| stratum_value | bin | n | mean_y | mean_pred | mae | mae_predict_zero | mae_donor_median | n_only |
|---|---|---|---|---|---|---|---|---|
| ALL | B0 zero | 13 | 0.000 | 27.608 | 27.608 | 0.000 | 28.198 | no |
| ALL | B1 (0, q25] | 10 | 24.800 | 20.534 | 7.541 | 24.800 | 7.594 | no |
| ALL | B2 (q25, q50] | 11 | 45.473 | 23.816 | 21.657 | 45.473 | 17.275 | no |
| ALL | B3 (q50, q75] | 6 | 57.511 | 27.815 | 29.696 | 57.511 | 29.313 | no |
| ALL | B4 (q75, max] | 2 | 74.999 | 31.635 | 43.364 | 74.999 | 46.800 | no |
| field | B0 zero | 4 | 0.000 | 27.413 | 27.413 | 0.000 | 28.198 | no |
| field | B1 (0, q25] | 4 | 28.634 | 21.967 | 6.680 | 28.634 | 4.953 | no |
| field | B2 (q25, q50] | 3 | 46.388 | 24.745 | 21.643 | 46.388 | 18.190 | no |
| field | B3 (q50, q75] | 2 | 57.592 | 31.111 | 26.481 | 57.592 | 29.394 | no |
| field | B4 (q75, max] | 0 |  |  |  |  |  | no |
| lab | B0 zero | 5 | 0.000 | 26.386 | 26.386 | 0.000 | 28.198 | no |
| lab | B1 (0, q25] | 3 | 25.861 | 19.192 | 10.159 | 25.861 | 9.138 | no |
| lab | B2 (q25, q50] | 4 | 45.316 | 23.312 | 22.005 | 45.316 | 17.118 | no |
| lab | B3 (q50, q75] | 2 | 57.924 | 26.667 | 31.257 | 57.924 | 29.726 | no |
| lab | B4 (q75, max] | 0 |  |  |  |  |  | no |
| remote | B0 zero | 4 | 0.000 | 29.332 | 29.332 | 0.000 | 28.198 | no |
| remote | B1 (0, q25] | 3 | 18.627 | 19.966 | 6.069 | 18.627 | 9.571 | no |
| remote | B2 (q25, q50] | 4 | 44.944 | 23.623 | 21.321 | 44.944 | 16.745 | no |
| remote | B3 (q50, q75] | 2 | 57.017 | 25.666 | 31.351 | 57.017 | 28.818 | no |
| remote | B4 (q75, max] | 2 | 74.999 | 31.635 | 43.364 | 74.999 | 46.800 | no |

### Lead 365, adopted `arm__identity_plain_gls`

| stratum_value | bin | n | mean_y | mean_pred | mae | mae_predict_zero | mae_donor_median | n_only |
|---|---|---|---|---|---|---|---|---|
| ALL | B0 zero | 13 | 0.000 | 26.045 | 26.045 | 0.000 | 21.117 | no |
| ALL | B1 (0, q25] | 9 | 24.584 | 18.715 | 8.775 | 24.584 | 8.711 | no |
| ALL | B2 (q25, q50] | 10 | 45.564 | 19.982 | 25.582 | 45.564 | 24.447 | no |
| ALL | B3 (q50, q75] | 3 | 54.665 | 25.829 | 28.835 | 54.665 | 33.548 | no |
| ALL | B4 (q75, max] | 4 | 67.842 | 29.154 | 38.689 | 67.842 | 46.725 | no |
| field | B0 zero | 4 | 0.000 | 23.919 | 23.919 | 0.000 | 21.117 | no |
| field | B1 (0, q25] | 4 | 28.634 | 20.870 | 7.764 | 28.634 | 7.702 | no |
| field | B2 (q25, q50] | 3 | 46.388 | 22.249 | 24.139 | 46.388 | 25.271 | no |
| field | B3 (q50, q75] | 1 | 55.486 | 28.635 | 26.851 | 55.486 | 34.369 | no |
| field | B4 (q75, max] | 0 |  |  |  |  |  | no |
| lab | B0 zero | 5 | 0.000 | 25.868 | 25.868 | 0.000 | 21.117 | no |
| lab | B1 (0, q25] | 3 | 25.861 | 16.700 | 11.237 | 25.861 | 11.499 | no |
| lab | B2 (q25, q50] | 4 | 45.316 | 18.962 | 26.354 | 45.316 | 24.199 | no |
| lab | B3 (q50, q75] | 1 | 55.421 | 21.944 | 33.478 | 55.421 | 34.304 | no |
| lab | B4 (q75, max] | 1 | 60.426 | 29.143 | 31.283 | 60.426 | 39.309 | no |
| remote | B0 zero | 4 | 0.000 | 28.390 | 28.390 | 0.000 | 21.117 | no |
| remote | B1 (0, q25] | 2 | 14.569 | 17.427 | 7.103 | 14.569 | 6.548 | no |
| remote | B2 (q25, q50] | 3 | 45.071 | 19.075 | 25.996 | 45.071 | 23.954 | no |
| remote | B3 (q50, q75] | 1 | 53.087 | 26.910 | 26.177 | 53.087 | 31.970 | no |
| remote | B4 (q75, max] | 3 | 70.315 | 29.157 | 41.157 | 70.315 | 49.198 | no |

## 3. Flattening guard (report only, never a choice)

Rows with label at or above the edge; every arm and baseline in flattening_guard.csv. Primary edge = q75 of all donor labels; beside = q75 of positive donor labels.

### Lead 0

| edge_rule | edge | column | n | observed_mean | mean_pred | mean_pred_minus_observed |
|---|---|---|---|---|---|---|
| q75_all_donor_labels | 51.139 | arm__arcsine_corrector_gls | 8 | 61.883 | 19.337 | -42.546 |
| q75_all_donor_labels | 51.139 | arm__arcsine_corrector_unweighted | 8 | 61.883 | 20.204 | -41.679 |
| q75_all_donor_labels | 51.139 | placebo__arcsine_placebo_corrector_gls | 8 | 61.883 | 19.337 | -42.546 |
| q75_all_donor_labels | 51.139 | placebo__arcsine_placebo_corrector_unweighted | 8 | 61.883 | 20.204 | -41.679 |
| q75_all_donor_labels | 51.139 | arm__arcsine_plain_gls | 8 | 61.883 | 19.337 | -42.546 |
| q75_all_donor_labels | 51.139 | arm__arcsine_plain_unweighted | 8 | 61.883 | 20.204 | -41.679 |
| q75_all_donor_labels | 51.139 | arm__arcsine_trees_off_unweighted | 8 | 61.883 | 19.646 | -42.237 |
| q75_all_donor_labels | 51.139 | arm__identity_corrector_gls | 8 | 61.883 | 29.104 | -32.779 |
| q75_all_donor_labels | 51.139 | arm__identity_corrector_unweighted | 8 | 61.883 | 30.110 | -31.773 |
| q75_all_donor_labels | 51.139 | placebo__identity_placebo_corrector_gls | 8 | 61.883 | 29.104 | -32.779 |
| q75_all_donor_labels | 51.139 | placebo__identity_placebo_corrector_unweighted | 8 | 61.883 | 30.110 | -31.773 |
| q75_all_donor_labels | 51.139 | arm__identity_plain_gls | 8 | 61.883 | 29.104 | -32.779 |
| q75_all_donor_labels | 51.139 | arm__identity_plain_unweighted | 8 | 61.883 | 30.110 | -31.773 |
| q75_all_donor_labels | 51.139 | arm__identity_trees_off_unweighted | 8 | 61.883 | 29.465 | -32.417 |
| q75_all_donor_labels | 51.139 | arm__log_c_corrector_gls | 8 | 61.883 | 19.702 | -42.181 |
| q75_all_donor_labels | 51.139 | arm__log_c_corrector_unweighted | 8 | 61.883 | 20.244 | -41.639 |
| q75_all_donor_labels | 51.139 | placebo__log_c_placebo_corrector_gls | 8 | 61.883 | 19.702 | -42.181 |
| q75_all_donor_labels | 51.139 | placebo__log_c_placebo_corrector_unweighted | 8 | 61.883 | 20.244 | -41.639 |
| q75_all_donor_labels | 51.139 | arm__log_c_plain_gls | 8 | 61.883 | 19.702 | -42.181 |
| q75_all_donor_labels | 51.139 | arm__log_c_plain_unweighted | 8 | 61.883 | 20.244 | -41.639 |
| q75_all_donor_labels | 51.139 | arm__log_c_trees_off_unweighted | 8 | 61.883 | 19.890 | -41.992 |
| q75_all_donor_labels | 51.139 | base__donor_median | 8 | 61.883 | 28.198 | -33.684 |
| q75_all_donor_labels | 51.139 | base__predict_zero | 8 | 61.883 | 0.000 | -61.883 |
| q75_positive_donor_labels | 60.273 | arm__arcsine_corrector_gls | 4 | 67.842 | 21.025 | -46.817 |
| q75_positive_donor_labels | 60.273 | arm__arcsine_corrector_unweighted | 4 | 67.842 | 21.365 | -46.477 |
| q75_positive_donor_labels | 60.273 | placebo__arcsine_placebo_corrector_gls | 4 | 67.842 | 21.025 | -46.817 |
| q75_positive_donor_labels | 60.273 | placebo__arcsine_placebo_corrector_unweighted | 4 | 67.842 | 21.365 | -46.477 |
| q75_positive_donor_labels | 60.273 | arm__arcsine_plain_gls | 4 | 67.842 | 21.025 | -46.817 |
| q75_positive_donor_labels | 60.273 | arm__arcsine_plain_unweighted | 4 | 67.842 | 21.365 | -46.477 |
| q75_positive_donor_labels | 60.273 | arm__arcsine_trees_off_unweighted | 4 | 67.842 | 20.478 | -47.364 |
| q75_positive_donor_labels | 60.273 | arm__identity_corrector_gls | 4 | 67.842 | 30.983 | -36.860 |
| q75_positive_donor_labels | 60.273 | arm__identity_corrector_unweighted | 4 | 67.842 | 31.642 | -36.200 |
| q75_positive_donor_labels | 60.273 | placebo__identity_placebo_corrector_gls | 4 | 67.842 | 30.983 | -36.860 |
| q75_positive_donor_labels | 60.273 | placebo__identity_placebo_corrector_unweighted | 4 | 67.842 | 31.642 | -36.200 |
| q75_positive_donor_labels | 60.273 | arm__identity_plain_gls | 4 | 67.842 | 30.983 | -36.860 |
| q75_positive_donor_labels | 60.273 | arm__identity_plain_unweighted | 4 | 67.842 | 31.642 | -36.200 |
| q75_positive_donor_labels | 60.273 | arm__identity_trees_off_unweighted | 4 | 67.842 | 30.642 | -37.201 |
| q75_positive_donor_labels | 60.273 | arm__log_c_corrector_gls | 4 | 67.842 | 21.036 | -46.807 |
| q75_positive_donor_labels | 60.273 | arm__log_c_corrector_unweighted | 4 | 67.842 | 21.079 | -46.763 |
| q75_positive_donor_labels | 60.273 | placebo__log_c_placebo_corrector_gls | 4 | 67.842 | 21.036 | -46.807 |
| q75_positive_donor_labels | 60.273 | placebo__log_c_placebo_corrector_unweighted | 4 | 67.842 | 21.079 | -46.763 |
| q75_positive_donor_labels | 60.273 | arm__log_c_plain_gls | 4 | 67.842 | 21.036 | -46.807 |
| q75_positive_donor_labels | 60.273 | arm__log_c_plain_unweighted | 4 | 67.842 | 21.079 | -46.763 |
| q75_positive_donor_labels | 60.273 | arm__log_c_trees_off_unweighted | 4 | 67.842 | 20.529 | -47.313 |
| q75_positive_donor_labels | 60.273 | base__donor_median | 4 | 67.842 | 28.198 | -39.644 |
| q75_positive_donor_labels | 60.273 | base__predict_zero | 4 | 67.842 | 0.000 | -67.842 |

### Lead 183

| edge_rule | edge | column | n | observed_mean | mean_pred | mean_pred_minus_observed |
|---|---|---|---|---|---|---|
| q75_all_donor_labels | 51.952 | arm__identity_plain_gls | 8 | 61.883 | 28.770 | -33.113 |
| q75_all_donor_labels | 51.952 | arm__identity_trees_off_unweighted | 8 | 61.883 | 29.171 | -32.712 |
| q75_all_donor_labels | 51.952 | base__damped_persistence | 1 | 76.738 | 32.535 | -44.204 |
| q75_all_donor_labels | 51.952 | base__donor_median | 8 | 61.883 | 28.198 | -33.684 |
| q75_all_donor_labels | 51.952 | base__persistence | 1 | 76.738 | 0.000 | -76.738 |
| q75_all_donor_labels | 51.952 | base__predict_zero | 8 | 61.883 | 0.000 | -61.883 |
| q75_positive_donor_labels | 62.349 | arm__identity_plain_gls | 2 | 74.999 | 31.635 | -43.364 |
| q75_positive_donor_labels | 62.349 | arm__identity_trees_off_unweighted | 2 | 74.999 | 32.418 | -42.581 |
| q75_positive_donor_labels | 62.349 | base__damped_persistence | 1 | 76.738 | 32.535 | -44.204 |
| q75_positive_donor_labels | 62.349 | base__donor_median | 2 | 74.999 | 28.198 | -46.800 |
| q75_positive_donor_labels | 62.349 | base__persistence | 1 | 76.738 | 0.000 | -76.738 |
| q75_positive_donor_labels | 62.349 | base__predict_zero | 2 | 74.999 | 0.000 | -74.999 |

### Lead 365

| edge_rule | edge | column | n | observed_mean | mean_pred | mean_pred_minus_observed |
|---|---|---|---|---|---|---|
| q75_all_donor_labels | 51.226 | placebo__identity_placebo_corrector_gls | 7 | 62.195 | 27.729 | -34.466 |
| q75_all_donor_labels | 51.226 | arm__identity_plain_gls | 7 | 62.195 | 27.729 | -34.466 |
| q75_all_donor_labels | 51.226 | arm__identity_trees_off_unweighted | 7 | 62.195 | 26.540 | -35.655 |
| q75_all_donor_labels | 51.226 | base__damped_persistence | 1 | 76.738 | 32.535 | -44.204 |
| q75_all_donor_labels | 51.226 | base__donor_median | 7 | 62.195 | 21.117 | -41.078 |
| q75_all_donor_labels | 51.226 | base__persistence | 1 | 76.738 | 0.000 | -76.738 |
| q75_all_donor_labels | 51.226 | base__predict_zero | 7 | 62.195 | 0.000 | -62.195 |
| q75_positive_donor_labels | 59.566 | placebo__identity_placebo_corrector_gls | 4 | 67.842 | 29.154 | -38.689 |
| q75_positive_donor_labels | 59.566 | arm__identity_plain_gls | 4 | 67.842 | 29.154 | -38.689 |
| q75_positive_donor_labels | 59.566 | arm__identity_trees_off_unweighted | 4 | 67.842 | 27.621 | -40.221 |
| q75_positive_donor_labels | 59.566 | base__damped_persistence | 1 | 76.738 | 32.535 | -44.204 |
| q75_positive_donor_labels | 59.566 | base__donor_median | 4 | 67.842 | 21.117 | -46.725 |
| q75_positive_donor_labels | 59.566 | base__persistence | 1 | 76.738 | 0.000 | -76.738 |
| q75_positive_donor_labels | 59.566 | base__predict_zero | 4 | 67.842 | 0.000 | -67.842 |

## 4. Pooled second (pooled (mixes programmes)): pooled, macro over ecoregions, per test year

No claim is made from a pooled margin.

### Lead 0

| column | line | year | n | n_groups | mae | mae_predict_zero | mae_donor_median |
|---|---|---|---|---|---|---|---|
| arm__arcsine_trees_off_unweighted | year | 2008.000 | 10 | 3 | 26.208 | 39.200 | 18.779 |
| arm__arcsine_trees_off_unweighted | year | 2009.000 | 11 | 3 | 27.547 | 33.552 | 21.287 |
| arm__arcsine_trees_off_unweighted | year | 2010.000 | 11 | 3 | 23.781 | 22.333 | 22.140 |
| arm__arcsine_trees_off_unweighted | year | 2011.000 | 10 | 3 | 23.046 | 23.653 | 23.653 |
| arm__arcsine_trees_off_unweighted | pooled |  | 42 | 3 | 25.170 | 29.602 | 21.477 |
| arm__arcsine_trees_off_unweighted | macro_over_groups |  | 42 | 3 | 25.150 | 29.619 | 21.595 |
| arm__identity_plain_gls | year | 2008.000 | 10 | 3 | 19.184 | 39.200 | 18.779 |
| arm__identity_plain_gls | year | 2009.000 | 11 | 3 | 23.974 | 33.552 | 21.287 |
| arm__identity_plain_gls | year | 2010.000 | 11 | 3 | 23.827 | 22.333 | 22.140 |
| arm__identity_plain_gls | year | 2011.000 | 10 | 3 | 23.670 | 23.653 | 23.653 |
| arm__identity_plain_gls | pooled |  | 42 | 3 | 22.723 | 29.602 | 21.477 |
| arm__identity_plain_gls | macro_over_groups |  | 42 | 3 | 22.739 | 29.619 | 21.595 |
| arm__identity_trees_off_unweighted | year | 2008.000 | 10 | 3 | 19.259 | 39.200 | 18.779 |
| arm__identity_trees_off_unweighted | year | 2009.000 | 11 | 3 | 22.561 | 33.552 | 21.287 |
| arm__identity_trees_off_unweighted | year | 2010.000 | 11 | 3 | 23.870 | 22.333 | 22.140 |
| arm__identity_trees_off_unweighted | year | 2011.000 | 10 | 3 | 23.095 | 23.653 | 23.653 |
| arm__identity_trees_off_unweighted | pooled |  | 42 | 3 | 22.245 | 29.602 | 21.477 |
| arm__identity_trees_off_unweighted | macro_over_groups |  | 42 | 3 | 22.270 | 29.619 | 21.595 |
| arm__log_c_trees_off_unweighted | year | 2008.000 | 10 | 3 | 25.226 | 39.200 | 18.779 |
| arm__log_c_trees_off_unweighted | year | 2009.000 | 11 | 3 | 26.840 | 33.552 | 21.287 |
| arm__log_c_trees_off_unweighted | year | 2010.000 | 11 | 3 | 22.848 | 22.333 | 22.140 |
| arm__log_c_trees_off_unweighted | year | 2011.000 | 10 | 3 | 23.212 | 23.653 | 23.653 |
| arm__log_c_trees_off_unweighted | pooled |  | 42 | 3 | 24.547 | 29.602 | 21.477 |
| arm__log_c_trees_off_unweighted | macro_over_groups |  | 42 | 3 | 24.557 | 29.619 | 21.595 |
| base__donor_median | year | 2008.000 | 10 | 3 | 18.779 | 39.200 | 18.779 |
| base__donor_median | year | 2009.000 | 11 | 3 | 21.287 | 33.552 | 21.287 |
| base__donor_median | year | 2010.000 | 11 | 3 | 22.140 | 22.333 | 22.140 |
| base__donor_median | year | 2011.000 | 10 | 3 | 23.653 | 23.653 | 23.653 |
| base__donor_median | pooled |  | 42 | 3 | 21.477 | 29.602 | 21.477 |
| base__donor_median | macro_over_groups |  | 42 | 3 | 21.595 | 29.619 | 21.595 |
| base__predict_zero | year | 2008.000 | 10 | 3 | 39.200 | 39.200 | 18.779 |
| base__predict_zero | year | 2009.000 | 11 | 3 | 33.552 | 33.552 | 21.287 |
| base__predict_zero | year | 2010.000 | 11 | 3 | 22.333 | 22.333 | 22.140 |
| base__predict_zero | year | 2011.000 | 10 | 3 | 23.653 | 23.653 | 23.653 |
| base__predict_zero | pooled |  | 42 | 3 | 29.602 | 29.602 | 21.477 |
| base__predict_zero | macro_over_groups |  | 42 | 3 | 29.619 | 29.619 | 21.595 |

### Lead 183

| column | line | year | n | n_groups | mae | mae_predict_zero | mae_donor_median |
|---|---|---|---|---|---|---|---|
| arm__identity_plain_gls | year | 2008.000 | 10 | 3 | 19.618 | 39.200 | 18.779 |
| arm__identity_plain_gls | year | 2009.000 | 11 | 3 | 23.607 | 33.552 | 21.287 |
| arm__identity_plain_gls | year | 2010.000 | 11 | 3 | 23.683 | 22.333 | 22.140 |
| arm__identity_plain_gls | year | 2011.000 | 10 | 3 | 22.108 | 23.653 | 23.653 |
| arm__identity_plain_gls | pooled |  | 42 | 3 | 22.320 | 29.602 | 21.477 |
| arm__identity_plain_gls | macro_over_groups |  | 42 | 3 | 22.350 | 29.619 | 21.595 |
| arm__identity_trees_off_unweighted | year | 2008.000 | 10 | 3 | 19.335 | 39.200 | 18.779 |
| arm__identity_trees_off_unweighted | year | 2009.000 | 11 | 3 | 22.479 | 33.552 | 21.287 |
| arm__identity_trees_off_unweighted | year | 2010.000 | 11 | 3 | 23.734 | 22.333 | 22.140 |
| arm__identity_trees_off_unweighted | year | 2011.000 | 10 | 3 | 22.807 | 23.653 | 23.653 |
| arm__identity_trees_off_unweighted | pooled |  | 42 | 3 | 22.137 | 29.602 | 21.477 |
| arm__identity_trees_off_unweighted | macro_over_groups |  | 42 | 3 | 22.169 | 29.619 | 21.595 |
| base__damped_persistence | year | 2008.000 | 1 | 1 | 32.106 | 0.000 | 28.198 |
| base__damped_persistence | year | 2009.000 | 1 | 1 | 47.701 | 0.000 | 28.198 |
| base__damped_persistence | year | 2010.000 | 2 | 2 | 48.398 | 38.369 | 38.369 |
| base__damped_persistence | year | 2011.000 | 1 | 1 | 49.763 | 0.000 | 28.198 |
| base__damped_persistence | pooled |  | 5 | 3 | 45.273 | 15.348 | 32.267 |
| base__damped_persistence | macro_over_groups |  | 5 | 3 | 43.079 | 12.790 | 31.589 |
| base__donor_median | year | 2008.000 | 10 | 3 | 18.779 | 39.200 | 18.779 |
| base__donor_median | year | 2009.000 | 11 | 3 | 21.287 | 33.552 | 21.287 |
| base__donor_median | year | 2010.000 | 11 | 3 | 22.140 | 22.333 | 22.140 |
| base__donor_median | year | 2011.000 | 10 | 3 | 23.653 | 23.653 | 23.653 |
| base__donor_median | pooled |  | 42 | 3 | 21.477 | 29.602 | 21.477 |
| base__donor_median | macro_over_groups |  | 42 | 3 | 21.595 | 29.619 | 21.595 |
| base__persistence | year | 2008.000 | 1 | 1 | 64.213 | 0.000 | 28.198 |
| base__persistence | year | 2009.000 | 1 | 1 | 47.701 | 0.000 | 28.198 |
| base__persistence | year | 2010.000 | 2 | 2 | 64.665 | 38.369 | 38.369 |
| base__persistence | year | 2011.000 | 1 | 1 | 50.745 | 0.000 | 28.198 |
| base__persistence | pooled |  | 5 | 3 | 58.398 | 15.348 | 32.267 |
| base__persistence | macro_over_groups |  | 5 | 3 | 59.367 | 12.790 | 31.589 |
| base__predict_zero | year | 2008.000 | 10 | 3 | 39.200 | 39.200 | 18.779 |
| base__predict_zero | year | 2009.000 | 11 | 3 | 33.552 | 33.552 | 21.287 |
| base__predict_zero | year | 2010.000 | 11 | 3 | 22.333 | 22.333 | 22.140 |
| base__predict_zero | year | 2011.000 | 10 | 3 | 23.653 | 23.653 | 23.653 |
| base__predict_zero | pooled |  | 42 | 3 | 29.602 | 29.602 | 21.477 |
| base__predict_zero | macro_over_groups |  | 42 | 3 | 29.619 | 29.619 | 21.595 |

### Lead 365

| column | line | year | n | n_groups | mae | mae_predict_zero | mae_donor_median |
|---|---|---|---|---|---|---|---|
| arm__identity_plain_gls | year | 2008.000 | 10 | 3 | 20.379 | 39.200 | 23.028 |
| arm__identity_plain_gls | year | 2009.000 | 10 | 3 | 26.135 | 34.232 | 25.786 |
| arm__identity_plain_gls | year | 2010.000 | 11 | 3 | 23.878 | 22.333 | 20.209 |
| arm__identity_plain_gls | year | 2011.000 | 8 | 3 | 23.355 | 16.533 | 21.813 |
| arm__identity_plain_gls | pooled |  | 39 | 3 | 23.452 | 28.520 | 22.691 |
| arm__identity_plain_gls | macro_over_groups |  | 39 | 3 | 23.444 | 28.469 | 22.744 |
| arm__identity_trees_off_unweighted | year | 2008.000 | 10 | 3 | 20.570 | 39.200 | 23.028 |
| arm__identity_trees_off_unweighted | year | 2009.000 | 10 | 3 | 25.338 | 34.232 | 25.786 |
| arm__identity_trees_off_unweighted | year | 2010.000 | 11 | 3 | 23.058 | 22.333 | 20.209 |
| arm__identity_trees_off_unweighted | year | 2011.000 | 8 | 3 | 22.826 | 16.533 | 21.813 |
| arm__identity_trees_off_unweighted | pooled |  | 39 | 3 | 22.957 | 28.520 | 22.691 |
| arm__identity_trees_off_unweighted | macro_over_groups |  | 39 | 3 | 22.958 | 28.469 | 22.744 |
| base__damped_persistence | year | 2008.000 | 1 | 1 | 32.106 | 0.000 | 21.117 |
| base__damped_persistence | year | 2009.000 | 1 | 1 | 47.701 | 0.000 | 21.117 |
| base__damped_persistence | year | 2010.000 | 2 | 2 | 48.398 | 38.369 | 38.369 |
| base__damped_persistence | year | 2011.000 | 1 | 1 | 48.781 | 0.000 | 21.117 |
| base__damped_persistence | pooled |  | 5 | 3 | 45.077 | 15.348 | 28.018 |
| base__damped_persistence | macro_over_groups |  | 5 | 3 | 42.915 | 12.790 | 26.868 |
| base__donor_median | year | 2008.000 | 10 | 3 | 23.028 | 39.200 | 23.028 |
| base__donor_median | year | 2009.000 | 10 | 3 | 25.786 | 34.232 | 25.786 |
| base__donor_median | year | 2010.000 | 11 | 3 | 20.209 | 22.333 | 20.209 |
| base__donor_median | year | 2011.000 | 8 | 3 | 21.813 | 16.533 | 21.813 |
| base__donor_median | pooled |  | 39 | 3 | 22.691 | 28.520 | 22.691 |
| base__donor_median | macro_over_groups |  | 39 | 3 | 22.744 | 28.469 | 22.744 |
| base__persistence | year | 2008.000 | 1 | 1 | 64.213 | 0.000 | 21.117 |
| base__persistence | year | 2009.000 | 1 | 1 | 47.701 | 0.000 | 21.117 |
| base__persistence | year | 2010.000 | 2 | 2 | 64.665 | 38.369 | 38.369 |
| base__persistence | year | 2011.000 | 1 | 1 | 50.745 | 0.000 | 21.117 |
| base__persistence | pooled |  | 5 | 3 | 58.398 | 15.348 | 28.018 |
| base__persistence | macro_over_groups |  | 5 | 3 | 59.367 | 12.790 | 26.868 |
| base__predict_zero | year | 2008.000 | 10 | 3 | 39.200 | 39.200 | 23.028 |
| base__predict_zero | year | 2009.000 | 10 | 3 | 34.232 | 34.232 | 25.786 |
| base__predict_zero | year | 2010.000 | 11 | 3 | 22.333 | 22.333 | 20.209 |
| base__predict_zero | year | 2011.000 | 8 | 3 | 16.533 | 16.533 | 21.813 |
| base__predict_zero | pooled |  | 39 | 3 | 28.520 | 28.520 | 22.691 |
| base__predict_zero | macro_over_groups |  | 39 | 3 | 28.469 | 28.469 | 22.744 |

## 5. Per ecoregion (n, zero share, programme mix; never ranked by MAE)

| group | n | zero_share | n_field | n_lab | n_remote |
|---|---|---|---|---|---|
| g_b | 13 | 0.385 | 7 | 3 | 3 |
| g_c | 15 | 0.333 | 3 | 8 | 4 |
| g_d | 14 | 0.214 | 3 | 3 | 8 |

## 6. Counts

### Rows left with no tree (V2 pool tree drop), per arm and pass

| pass | lead | arm | n_rows | n_rows_no_tree | share_no_tree |
|---|---|---|---|---|---|
| decision_surface | 0 | arcsine_corrector_gls | 46 | 39 | 0.848 |
| decision_surface | 0 | arcsine_corrector_unweighted | 46 | 39 | 0.848 |
| decision_surface | 0 | arcsine_plain_gls | 46 | 39 | 0.848 |
| decision_surface | 0 | arcsine_plain_unweighted | 46 | 39 | 0.848 |
| decision_surface | 0 | identity_corrector_gls | 46 | 39 | 0.848 |
| decision_surface | 0 | identity_corrector_unweighted | 46 | 39 | 0.848 |
| decision_surface | 0 | identity_plain_gls | 46 | 39 | 0.848 |
| decision_surface | 0 | identity_plain_unweighted | 46 | 39 | 0.848 |
| decision_surface | 0 | log_c_corrector_gls | 46 | 39 | 0.848 |
| decision_surface | 0 | log_c_corrector_unweighted | 46 | 39 | 0.848 |
| decision_surface | 0 | log_c_plain_gls | 46 | 39 | 0.848 |
| decision_surface | 0 | log_c_plain_unweighted | 46 | 39 | 0.848 |
| test_pass | 0 | arcsine_corrector_gls | 42 | 25 | 0.595 |
| test_pass | 0 | arcsine_corrector_unweighted | 42 | 25 | 0.595 |
| test_pass | 0 | arcsine_placebo_corrector_gls | 42 | 25 | 0.595 |
| test_pass | 0 | arcsine_placebo_corrector_unweighted | 42 | 25 | 0.595 |
| test_pass | 0 | arcsine_plain_gls | 42 | 25 | 0.595 |
| test_pass | 0 | arcsine_plain_unweighted | 42 | 25 | 0.595 |
| test_pass | 0 | identity_corrector_gls | 42 | 25 | 0.595 |
| test_pass | 0 | identity_corrector_unweighted | 42 | 25 | 0.595 |
| test_pass | 0 | identity_placebo_corrector_gls | 42 | 25 | 0.595 |
| test_pass | 0 | identity_placebo_corrector_unweighted | 42 | 25 | 0.595 |
| test_pass | 0 | identity_plain_gls | 42 | 25 | 0.595 |
| test_pass | 0 | identity_plain_unweighted | 42 | 25 | 0.595 |
| test_pass | 0 | log_c_corrector_gls | 42 | 25 | 0.595 |
| test_pass | 0 | log_c_corrector_unweighted | 42 | 25 | 0.595 |
| test_pass | 0 | log_c_placebo_corrector_gls | 42 | 25 | 0.595 |
| test_pass | 0 | log_c_placebo_corrector_unweighted | 42 | 25 | 0.595 |
| test_pass | 0 | log_c_plain_gls | 42 | 25 | 0.595 |
| test_pass | 0 | log_c_plain_unweighted | 42 | 25 | 0.595 |
| guard | 183 | identity_plain_gls | 38 | 38 | 1.000 |
| test_pass | 183 | identity_plain_gls | 42 | 27 | 0.643 |
| guard | 365 | identity_plain_gls | 30 | 30 | 1.000 |
| test_pass | 365 | identity_placebo_corrector_gls | 39 | 27 | 0.692 |
| test_pass | 365 | identity_plain_gls | 39 | 27 | 0.692 |

### Pool fallbacks (under 12 valid pool rows)

| pass | lead | pools_file | rows | rows_pool_fallback | matches_record |
|---|---|---|---|---|---|
| decision_surface | 0 | pools_decision_surface.parquet | 46 | 0 | yes |
| test_pass | 0 | pools_test_pass.parquet | 42 | 0 | yes |
| guard | 183 | ladder\lead_183\pools_guard.parquet | 38 | 0 | yes |
| test_pass | 183 | ladder\lead_183\pools_test_pass.parquet | 42 | 0 | yes |
| guard | 365 | ladder\lead_365\pools_guard.parquet | 30 | 0 | yes |
| test_pass | 365 | ladder\lead_365\pools_test_pass.parquet | 39 | 0 | yes |

### Rows left out

| what | lead | source | rows_record | rows_file |
|---|---|---|---|---|
| H4 test rows absent at the lead (left out of scoring) | 183 | lead.json issue_features_missing / issue_missing_rows.parquet | 0 | 0 |
| H4 test rows absent at the lead (left out of scoring) | 365 | lead.json issue_features_missing / issue_missing_rows.parquet | 3 | 3 |
| S1/G1 rows with missing router context, left out | 0 | context_missing/decision_surface.parquet (neighbour_pool:decision_surface) | 3 | 3 |
| S1/G1 rows with missing router context, left out | 0 | context_missing/lead_0_contract.parquet (neighbour_pool:lead_0_contract) | 3 | 3 |
| S1/G1 rows with missing router context, left out | 183 | context_missing/lead_183_guard.parquet (neighbour_pool:lead_183_guard) | 3 | 3 |
| S1/G1 rows with missing router context, left out | 183 | context_missing/lead_183_test_pass.parquet (neighbour_pool:lead_183_test_pass) | 3 | 3 |
| S1/G1 rows with missing router context, left out | 365 | context_missing/lead_365_guard.parquet (neighbour_pool:lead_365_guard) | 3 | 3 |
| S1/G1 rows with missing router context, left out | 365 | context_missing/lead_365_test_pass.parquet (neighbour_pool:lead_365_test_pass) | 3 | 3 |
| S1/G1 rows with missing router context, left out | 0 | context_missing/test_pass.parquet (neighbour_pool:test_pass) | 3 | 3 |

## 7. Leads

Leads [0, 183, 365]; the ladder rows are scored on the rows common to all leads (rows_basis 'common' in every CSV), with all rows beside.

