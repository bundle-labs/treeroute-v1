# Coral report-only tables (coral_report.py 1.0.0)

**NOT HEADLINE: smoke run: plumbing only (R21), smoke deltas carry no sign information**

- Run folder: `D:\treeroute\coral_build\report_scripts\toy_runs\ok\runs\toy_table\smoke\20261020_603d4728` (kind smoke, package toy_table)
- Script SHA-256: `c3cd534cbc4895147a6a8220928a790158f789c303b4e456c2bbaeee4ed4a793`; every input file's SHA-256 is in inputs_manifest.json.
- Report only: nothing here changes a fit, a pick or the verdict (draft section 6.2).
- Every forecast is read as "given a survey on this date". The 365-day row is risk stratification.
- Predict-zero and the donor-row median MAE are printed beside every MAE, on the same rows.

## 1. Per programme (stratum `source`)

Values with fewer than 10 rows are shown with n only. Full metrics for every column are in per_programme.csv.

### Lead 0 (all rows; adopted `base__donor_median`, declined)

| stratum_value | column | n | zero_share | mae | mae_predict_zero | mae_donor_median | hit | corr2 | n_only |
|---|---|---|---|---|---|---|---|---|---|
| ALL | arm__arcsine_trees_off_unweighted | 56 | 0.196 | 32.385 | 41.247 | 35.668 | 0.089 | 0.013 | no |
| ALL | arm__identity_trees_off_unweighted | 56 | 0.196 | 27.063 | 41.247 | 35.668 | 0.125 | 0.051 | no |
| ALL | arm__log_c_trees_off_unweighted | 56 | 0.196 | 31.205 | 41.247 | 35.668 | 0.107 | 0.010 | no |
| ALL | base__donor_median | 56 | 0.196 | 35.668 | 41.247 | 35.668 | 0.250 |  | no |
| ALL | base__predict_zero | 56 | 0.196 | 41.247 | 41.247 | 35.668 | 0.214 |  | no |
| field | arm__arcsine_trees_off_unweighted | 22 | 0.227 | 33.047 | 40.498 | 35.480 | 0.091 | 0.002 | no |
| field | arm__identity_trees_off_unweighted | 22 | 0.227 | 27.603 | 40.498 | 35.480 | 0.182 | 0.015 | no |
| field | arm__log_c_trees_off_unweighted | 22 | 0.227 | 31.696 | 40.498 | 35.480 | 0.136 | 0.004 | no |
| field | base__donor_median | 22 | 0.227 | 35.480 | 40.498 | 35.480 | 0.273 |  | no |
| field | base__predict_zero | 22 | 0.227 | 40.498 | 40.498 | 35.480 | 0.227 |  | no |
| lab | arm__arcsine_trees_off_unweighted | 16 | 0.188 | 31.797 | 41.876 | 36.147 | 0.125 | 0.060 | no |
| lab | arm__identity_trees_off_unweighted | 16 | 0.188 | 26.981 | 41.876 | 36.147 | 0.062 | 0.085 | no |
| lab | arm__log_c_trees_off_unweighted | 16 | 0.188 | 30.911 | 41.876 | 36.147 | 0.062 | 0.065 | no |
| lab | base__donor_median | 16 | 0.188 | 36.147 | 41.876 | 36.147 | 0.250 |  | no |
| lab | base__predict_zero | 16 | 0.188 | 41.876 | 41.876 | 36.147 | 0.250 |  | no |
| remote | arm__arcsine_trees_off_unweighted | 18 | 0.167 | 32.098 | 41.604 | 35.471 | 0.056 | 0.032 | no |
| remote | arm__identity_trees_off_unweighted | 18 | 0.167 | 26.475 | 41.604 | 35.471 | 0.111 | 0.083 | no |
| remote | arm__log_c_trees_off_unweighted | 18 | 0.167 | 30.864 | 41.604 | 35.471 | 0.111 | 0.021 | no |
| remote | base__donor_median | 18 | 0.167 | 35.471 | 41.604 | 35.471 | 0.222 |  | no |
| remote | base__predict_zero | 18 | 0.167 | 41.604 | 41.604 | 35.471 | 0.167 |  | no |


### Lead 183 (all rows; adopted `base__donor_median`, declined)

| stratum_value | column | n | zero_share | mae | mae_predict_zero | mae_donor_median | hit | corr2 | n_only |
|---|---|---|---|---|---|---|---|---|---|
| ALL | arm__identity_trees_off_unweighted | 56 | 0.196 | 27.126 | 41.247 | 41.247 | 0.107 | 0.045 | no |
| ALL | arm__log_c_trees_off_unweighted | 56 | 0.196 | 31.435 | 41.247 | 41.247 | 0.107 | 0.009 | no |
| ALL | base__damped_persistence | 6 | 0.500 | 21.709 | 19.940 | 19.940 | 0.333 | 0.031 | no |
| ALL | base__donor_median | 56 | 0.196 | 41.247 | 41.247 | 41.247 | 0.214 |  | no |
| ALL | base__persistence | 6 | 0.500 | 28.340 | 19.940 | 19.940 | 0.333 | 0.248 | no |
| ALL | base__predict_zero | 56 | 0.196 | 41.247 | 41.247 | 41.247 | 0.214 |  | no |
| field | arm__identity_trees_off_unweighted | 22 | 0.227 | 27.809 | 40.498 | 40.498 | 0.182 | 0.000 | no |
| field | arm__log_c_trees_off_unweighted | 22 | 0.227 | 32.124 | 40.498 | 40.498 | 0.136 | 0.042 | no |
| field | base__damped_persistence | 3 | 0.667 | 34.711 | 20.165 | 20.165 | 0.000 | 0.292 | no |
| field | base__donor_median | 22 | 0.227 | 40.498 | 40.498 | 40.498 | 0.227 |  | no |
| field | base__persistence | 3 | 0.667 | 43.808 | 20.165 | 20.165 | 0.000 | 0.747 | no |
| field | base__predict_zero | 22 | 0.227 | 40.498 | 40.498 | 40.498 | 0.227 |  | no |
| lab | arm__identity_trees_off_unweighted | 16 | 0.188 | 26.808 | 41.876 | 41.876 | 0.000 | 0.138 | no |
| lab | arm__log_c_trees_off_unweighted | 16 | 0.188 | 30.902 | 41.876 | 41.876 | 0.062 | 0.135 | no |
| lab | base__damped_persistence | 1 | 0.000 | 12.029 | 35.682 | 35.682 | 1.000 |  | no |
| lab | base__donor_median | 16 | 0.188 | 41.876 | 41.876 | 41.876 | 0.250 |  | no |
| lab | base__persistence | 1 | 0.000 | 11.625 | 35.682 | 35.682 | 1.000 |  | no |
| lab | base__predict_zero | 16 | 0.188 | 41.876 | 41.876 | 41.876 | 0.250 |  | no |
| remote | arm__identity_trees_off_unweighted | 18 | 0.167 | 26.573 | 41.604 | 41.604 | 0.111 | 0.067 | no |
| remote | arm__log_c_trees_off_unweighted | 18 | 0.167 | 31.067 | 41.604 | 41.604 | 0.111 | 0.019 | no |
| remote | base__damped_persistence | 2 | 0.500 | 7.047 | 11.731 | 11.731 | 0.500 | 1.000 | no |
| remote | base__donor_median | 18 | 0.167 | 41.604 | 41.604 | 41.604 | 0.167 |  | no |
| remote | base__persistence | 2 | 0.500 | 13.496 | 11.731 | 11.731 | 0.500 | 1.000 | no |
| remote | base__predict_zero | 18 | 0.167 | 41.604 | 41.604 | 41.604 | 0.167 |  | no |


### Lead 365 (all rows; adopted `base__donor_median`, declined)

| stratum_value | column | n | zero_share | mae | mae_predict_zero | mae_donor_median | hit | corr2 | n_only |
|---|---|---|---|---|---|---|---|---|---|
| ALL | arm__identity_trees_off_unweighted | 52 | 0.212 | 28.408 | 40.957 | 40.957 | 0.096 | 0.017 | no |
| ALL | arm__log_c_trees_off_unweighted | 52 | 0.212 | 32.397 | 40.957 | 40.957 | 0.077 | 0.002 | no |
| ALL | base__damped_persistence | 5 | 0.600 | 23.232 | 19.235 | 19.235 | 0.400 | 0.001 | no |
| ALL | base__donor_median | 52 | 0.212 | 40.957 | 40.957 | 40.957 | 0.231 |  | no |
| ALL | base__persistence | 5 | 0.600 | 33.769 | 19.235 | 19.235 | 0.200 | 0.245 | no |
| ALL | base__predict_zero | 52 | 0.212 | 40.957 | 40.957 | 40.957 | 0.231 |  | no |
| field | arm__identity_trees_off_unweighted | 20 | 0.250 | 28.866 | 39.297 | 39.297 | 0.150 | 0.015 | no |
| field | arm__log_c_trees_off_unweighted | 20 | 0.250 | 32.593 | 39.297 | 39.297 | 0.050 | 0.070 | no |
| field | base__damped_persistence | 3 | 0.667 | 34.711 | 20.165 | 20.165 | 0.000 | 0.292 | no |
| field | base__donor_median | 20 | 0.250 | 39.297 | 39.297 | 39.297 | 0.250 |  | no |
| field | base__persistence | 3 | 0.667 | 43.808 | 20.165 | 20.165 | 0.000 | 0.747 | no |
| field | base__predict_zero | 20 | 0.250 | 39.297 | 39.297 | 39.297 | 0.250 |  | no |
| lab | arm__identity_trees_off_unweighted | 16 | 0.188 | 27.581 | 41.876 | 41.876 | 0.000 | 0.136 | no |
| lab | arm__log_c_trees_off_unweighted | 16 | 0.188 | 31.771 | 41.876 | 41.876 | 0.125 | 0.129 | no |
| lab | base__damped_persistence | 1 | 0.000 | 12.029 | 35.682 | 35.682 | 1.000 |  | no |
| lab | base__donor_median | 16 | 0.188 | 41.876 | 41.876 | 41.876 | 0.250 |  | no |
| lab | base__persistence | 1 | 0.000 | 11.625 | 35.682 | 35.682 | 1.000 |  | no |
| lab | base__predict_zero | 16 | 0.188 | 41.876 | 41.876 | 41.876 | 0.250 |  | no |
| remote | arm__identity_trees_off_unweighted | 16 | 0.188 | 28.661 | 42.114 | 42.114 | 0.125 | 0.033 | no |
| remote | arm__log_c_trees_off_unweighted | 16 | 0.188 | 32.777 | 42.114 | 42.114 | 0.062 | 0.008 | no |
| remote | base__damped_persistence | 1 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 |  | no |
| remote | base__donor_median | 16 | 0.188 | 42.114 | 42.114 | 42.114 | 0.188 |  | no |
| remote | base__persistence | 1 | 1.000 | 25.796 | 0.000 | 0.000 | 0.000 |  | no |
| remote | base__predict_zero | 16 | 0.188 | 42.114 | 42.114 | 42.114 | 0.188 |  | no |


### Programme verdict lines (D74 rule, report only; the ALL line is the registered verdict's rows)

| lead | rows_basis | stratum_value | n_rows | n_groups | mean | se | low | high | tag | matches_engine |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | all | ALL | 56 | 4 | 0.000 | 0.000 | 0.000 | 0.000 | declined | yes |
| 0 | all | field | 22 | 4 | 0.000 | 0.000 | 0.000 | 0.000 | declined |  |
| 0 | all | lab | 16 | 4 | 0.000 | 0.000 | 0.000 | 0.000 | declined |  |
| 0 | all | remote | 18 | 4 | 0.000 | 0.000 | 0.000 | 0.000 | declined |  |
| 0 | common | ALL | 52 | 4 | 0.000 | 0.000 | 0.000 | 0.000 | declined | yes |
| 0 | common | field | 20 | 4 | 0.000 | 0.000 | 0.000 | 0.000 | declined |  |
| 0 | common | lab | 16 | 4 | 0.000 | 0.000 | 0.000 | 0.000 | declined |  |
| 0 | common | remote | 16 | 4 | 0.000 | 0.000 | 0.000 | 0.000 | declined |  |
| 183 | common | ALL | 52 | 4 | 0.000 | 0.000 | 0.000 | 0.000 | declined | yes |
| 183 | common | field | 20 | 4 | 0.000 | 0.000 | 0.000 | 0.000 | declined |  |
| 183 | common | lab | 16 | 4 | 0.000 | 0.000 | 0.000 | 0.000 | declined |  |
| 183 | common | remote | 16 | 4 | 0.000 | 0.000 | 0.000 | 0.000 | declined |  |
| 365 | common | ALL | 52 | 4 | 0.000 | 0.000 | 0.000 | 0.000 | declined | yes |
| 365 | common | field | 20 | 4 | 0.000 | 0.000 | 0.000 | 0.000 | declined |  |
| 365 | common | lab | 16 | 4 | 0.000 | 0.000 | 0.000 | 0.000 | declined |  |
| 365 | common | remote | 16 | 4 | 0.000 | 0.000 | 0.000 | 0.000 | declined |  |

## 2. By magnitude (a target-defined diagnostic, not a headline)

Edges from the donor rows at each lead's fit cut (train rows only):

| lead | fit_cut | donor_rows | donor_rows_engine | donor_median | positive_donor_rows | pos_q25 | pos_q50 | pos_q75 | q75_all_donor_labels |
|---|---|---|---|---|---|---|---|---|---|
| 0.000 | 733041.000 | 116.000 | 116.000 | 9.200 | 58.000 | 37.177 | 47.159 | 56.180 | 47.086 |
| 183.000 | 732859.000 | 109.000 | 109.000 | 0.000 | 52.000 | 40.487 | 47.414 | 57.707 | 47.327 |
| 365.000 | 732677.000 | 97.000 | 97.000 | 0.000 | 44.000 | 41.949 | 47.414 | 59.628 | 47.307 |

### Lead 0, adopted `base__donor_median`

| stratum_value | bin | n | mean_y | mean_pred | mae | mae_predict_zero | mae_donor_median | n_only |
|---|---|---|---|---|---|---|---|---|
| ALL | B0 zero | 11 | 0.000 | 9.200 | 9.200 | 0.000 | 9.200 | no |
| ALL | B1 (0, q25] | 11 | 26.962 | 9.200 | 17.791 | 26.962 | 17.791 | no |
| ALL | B2 (q25, q50] | 5 | 41.686 | 9.200 | 32.486 | 41.686 | 32.486 | no |
| ALL | B3 (q50, q75] | 12 | 52.417 | 9.200 | 43.218 | 52.417 | 43.218 | no |
| ALL | B4 (q75, max] | 17 | 69.166 | 9.200 | 59.967 | 69.166 | 59.967 | no |
| field | B0 zero | 5 | 0.000 | 9.200 | 9.200 | 0.000 | 9.200 | no |
| field | B1 (0, q25] | 3 | 24.184 | 9.200 | 14.985 | 24.184 | 14.985 | no |
| field | B2 (q25, q50] | 4 | 41.728 | 9.200 | 32.528 | 41.728 | 32.528 | no |
| field | B3 (q50, q75] | 3 | 54.282 | 9.200 | 45.082 | 54.282 | 45.082 | no |
| field | B4 (q75, max] | 7 | 69.806 | 9.200 | 60.606 | 69.806 | 60.606 | no |
| lab | B0 zero | 3 | 0.000 | 9.200 | 9.200 | 0.000 | 9.200 | no |
| lab | B1 (0, q25] | 3 | 27.207 | 9.200 | 18.115 | 27.207 | 18.115 | no |
| lab | B2 (q25, q50] | 1 | 41.520 | 9.200 | 32.320 | 41.520 | 32.320 | no |
| lab | B3 (q50, q75] | 4 | 52.927 | 9.200 | 43.728 | 52.927 | 43.728 | no |
| lab | B4 (q75, max] | 5 | 67.034 | 9.200 | 57.834 | 67.034 | 57.834 | no |
| remote | B0 zero | 3 | 0.000 | 9.200 | 9.200 | 0.000 | 9.200 | no |
| remote | B1 (0, q25] | 5 | 28.481 | 9.200 | 19.281 | 28.481 | 19.281 | no |
| remote | B2 (q25, q50] | 0 |  |  |  |  |  | no |
| remote | B3 (q50, q75] | 5 | 50.890 | 9.200 | 41.691 | 50.890 | 41.691 | no |
| remote | B4 (q75, max] | 5 | 70.404 | 9.200 | 61.204 | 70.404 | 61.204 | no |

### Lead 183, adopted `base__donor_median`

| stratum_value | bin | n | mean_y | mean_pred | mae | mae_predict_zero | mae_donor_median | n_only |
|---|---|---|---|---|---|---|---|---|
| ALL | B0 zero | 11 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | no |
| ALL | B1 (0, q25] | 13 | 28.902 | 0.000 | 28.902 | 28.902 | 28.902 | no |
| ALL | B2 (q25, q50] | 3 | 43.096 | 0.000 | 43.096 | 43.096 | 43.096 | no |
| ALL | B3 (q50, q75] | 13 | 52.788 | 0.000 | 52.788 | 52.788 | 52.788 | no |
| ALL | B4 (q75, max] | 16 | 69.912 | 0.000 | 69.912 | 69.912 | 69.912 | no |
| field | B0 zero | 5 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | no |
| field | B1 (0, q25] | 5 | 30.339 | 0.000 | 30.339 | 30.339 | 30.339 | no |
| field | B2 (q25, q50] | 2 | 43.884 | 0.000 | 43.884 | 43.884 | 43.884 | no |
| field | B3 (q50, q75] | 3 | 54.282 | 0.000 | 54.282 | 54.282 | 54.282 | no |
| field | B4 (q75, max] | 7 | 69.806 | 0.000 | 69.806 | 69.806 | 69.806 | no |
| lab | B0 zero | 3 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | no |
| lab | B1 (0, q25] | 3 | 27.207 | 0.000 | 27.207 | 27.207 | 27.207 | no |
| lab | B2 (q25, q50] | 1 | 41.520 | 0.000 | 41.520 | 41.520 | 41.520 | no |
| lab | B3 (q50, q75] | 5 | 53.789 | 0.000 | 53.789 | 53.789 | 53.789 | no |
| lab | B4 (q75, max] | 4 | 69.484 | 0.000 | 69.484 | 69.484 | 69.484 | no |
| remote | B0 zero | 3 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | no |
| remote | B1 (0, q25] | 5 | 28.481 | 0.000 | 28.481 | 28.481 | 28.481 | no |
| remote | B2 (q25, q50] | 0 |  |  |  |  |  | no |
| remote | B3 (q50, q75] | 5 | 50.890 | 0.000 | 50.890 | 50.890 | 50.890 | no |
| remote | B4 (q75, max] | 5 | 70.404 | 0.000 | 70.404 | 70.404 | 70.404 | no |

### Lead 365, adopted `base__donor_median`

| stratum_value | bin | n | mean_y | mean_pred | mae | mae_predict_zero | mae_donor_median | n_only |
|---|---|---|---|---|---|---|---|---|
| ALL | B0 zero | 11 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | no |
| ALL | B1 (0, q25] | 13 | 30.291 | 0.000 | 30.291 | 30.291 | 30.291 | no |
| ALL | B2 (q25, q50] | 1 | 45.727 | 0.000 | 45.727 | 45.727 | 45.727 | no |
| ALL | B3 (q50, q75] | 12 | 52.888 | 0.000 | 52.888 | 52.888 | 52.888 | no |
| ALL | B4 (q75, max] | 15 | 70.375 | 0.000 | 70.375 | 70.375 | 70.375 | no |
| field | B0 zero | 5 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | no |
| field | B1 (0, q25] | 5 | 30.339 | 0.000 | 30.339 | 30.339 | 30.339 | no |
| field | B2 (q25, q50] | 1 | 45.727 | 0.000 | 45.727 | 45.727 | 45.727 | no |
| field | B3 (q50, q75] | 3 | 54.282 | 0.000 | 54.282 | 54.282 | 54.282 | no |
| field | B4 (q75, max] | 6 | 70.946 | 0.000 | 70.946 | 70.946 | 70.946 | no |
| lab | B0 zero | 3 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | no |
| lab | B1 (0, q25] | 4 | 30.786 | 0.000 | 30.786 | 30.786 | 30.786 | no |
| lab | B2 (q25, q50] | 0 |  |  |  |  |  | no |
| lab | B3 (q50, q75] | 5 | 53.789 | 0.000 | 53.789 | 53.789 | 53.789 | no |
| lab | B4 (q75, max] | 4 | 69.484 | 0.000 | 69.484 | 69.484 | 69.484 | no |
| remote | B0 zero | 3 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | no |
| remote | B1 (0, q25] | 4 | 29.735 | 0.000 | 29.735 | 29.735 | 29.735 | no |
| remote | B2 (q25, q50] | 0 |  |  |  |  |  | no |
| remote | B3 (q50, q75] | 4 | 50.716 | 0.000 | 50.716 | 50.716 | 50.716 | no |
| remote | B4 (q75, max] | 5 | 70.404 | 0.000 | 70.404 | 70.404 | 70.404 | no |

## 3. Flattening guard (report only, never a choice)

Rows with label at or above the edge; every arm and baseline in flattening_guard.csv. Primary edge = q75 of all donor labels; beside = q75 of positive donor labels.

### Lead 0

| edge_rule | edge | column | n | observed_mean | mean_pred | mean_pred_minus_observed |
|---|---|---|---|---|---|---|
| q75_all_donor_labels | 47.086 | arm__arcsine_corrector_gls | 29 | 62.236 | 15.592 | -46.644 |
| q75_all_donor_labels | 47.086 | arm__arcsine_corrector_unweighted | 29 | 62.236 | 15.085 | -47.151 |
| q75_all_donor_labels | 47.086 | placebo__arcsine_placebo_corrector_gls | 29 | 62.236 | 15.592 | -46.644 |
| q75_all_donor_labels | 47.086 | placebo__arcsine_placebo_corrector_unweighted | 29 | 62.236 | 15.085 | -47.151 |
| q75_all_donor_labels | 47.086 | arm__arcsine_plain_gls | 29 | 62.236 | 15.592 | -46.644 |
| q75_all_donor_labels | 47.086 | arm__arcsine_plain_unweighted | 29 | 62.236 | 15.085 | -47.151 |
| q75_all_donor_labels | 47.086 | arm__arcsine_trees_off_unweighted | 29 | 62.236 | 16.329 | -45.907 |
| q75_all_donor_labels | 47.086 | arm__identity_corrector_gls | 29 | 62.236 | 25.310 | -36.926 |
| q75_all_donor_labels | 47.086 | arm__identity_corrector_unweighted | 29 | 62.236 | 25.037 | -37.199 |
| q75_all_donor_labels | 47.086 | placebo__identity_placebo_corrector_gls | 29 | 62.236 | 25.310 | -36.926 |
| q75_all_donor_labels | 47.086 | placebo__identity_placebo_corrector_unweighted | 29 | 62.236 | 25.037 | -37.199 |
| q75_all_donor_labels | 47.086 | arm__identity_plain_gls | 29 | 62.236 | 25.310 | -36.926 |
| q75_all_donor_labels | 47.086 | arm__identity_plain_unweighted | 29 | 62.236 | 25.037 | -37.199 |
| q75_all_donor_labels | 47.086 | arm__identity_trees_off_unweighted | 29 | 62.236 | 26.536 | -35.700 |
| q75_all_donor_labels | 47.086 | arm__log_c_corrector_gls | 29 | 62.236 | 17.360 | -44.876 |
| q75_all_donor_labels | 47.086 | arm__log_c_corrector_unweighted | 29 | 62.236 | 16.867 | -45.369 |
| q75_all_donor_labels | 47.086 | placebo__log_c_placebo_corrector_gls | 29 | 62.236 | 17.360 | -44.876 |
| q75_all_donor_labels | 47.086 | placebo__log_c_placebo_corrector_unweighted | 29 | 62.236 | 16.867 | -45.369 |
| q75_all_donor_labels | 47.086 | arm__log_c_plain_gls | 29 | 62.236 | 17.360 | -44.876 |
| q75_all_donor_labels | 47.086 | arm__log_c_plain_unweighted | 29 | 62.236 | 16.867 | -45.369 |
| q75_all_donor_labels | 47.086 | arm__log_c_trees_off_unweighted | 29 | 62.236 | 18.178 | -44.058 |
| q75_all_donor_labels | 47.086 | base__donor_median | 29 | 62.236 | 9.200 | -53.036 |
| q75_all_donor_labels | 47.086 | base__predict_zero | 29 | 62.236 | 0.000 | -62.236 |
| q75_positive_donor_labels | 56.180 | arm__arcsine_corrector_gls | 17 | 69.166 | 15.364 | -53.802 |
| q75_positive_donor_labels | 56.180 | arm__arcsine_corrector_unweighted | 17 | 69.166 | 14.984 | -54.182 |
| q75_positive_donor_labels | 56.180 | placebo__arcsine_placebo_corrector_gls | 17 | 69.166 | 15.364 | -53.802 |
| q75_positive_donor_labels | 56.180 | placebo__arcsine_placebo_corrector_unweighted | 17 | 69.166 | 14.984 | -54.182 |
| q75_positive_donor_labels | 56.180 | arm__arcsine_plain_gls | 17 | 69.166 | 15.364 | -53.802 |
| q75_positive_donor_labels | 56.180 | arm__arcsine_plain_unweighted | 17 | 69.166 | 14.984 | -54.182 |
| q75_positive_donor_labels | 56.180 | arm__arcsine_trees_off_unweighted | 17 | 69.166 | 17.739 | -51.428 |
| q75_positive_donor_labels | 56.180 | arm__identity_corrector_gls | 17 | 69.166 | 25.840 | -43.327 |
| q75_positive_donor_labels | 56.180 | arm__identity_corrector_unweighted | 17 | 69.166 | 25.647 | -43.520 |
| q75_positive_donor_labels | 56.180 | placebo__identity_placebo_corrector_gls | 17 | 69.166 | 25.840 | -43.327 |
| q75_positive_donor_labels | 56.180 | placebo__identity_placebo_corrector_unweighted | 17 | 69.166 | 25.647 | -43.520 |
| q75_positive_donor_labels | 56.180 | arm__identity_plain_gls | 17 | 69.166 | 25.840 | -43.327 |
| q75_positive_donor_labels | 56.180 | arm__identity_plain_unweighted | 17 | 69.166 | 25.647 | -43.520 |
| q75_positive_donor_labels | 56.180 | arm__identity_trees_off_unweighted | 17 | 69.166 | 28.250 | -40.916 |
| q75_positive_donor_labels | 56.180 | arm__log_c_corrector_gls | 17 | 69.166 | 17.075 | -52.091 |
| q75_positive_donor_labels | 56.180 | arm__log_c_corrector_unweighted | 17 | 69.166 | 16.637 | -52.530 |
| q75_positive_donor_labels | 56.180 | placebo__log_c_placebo_corrector_gls | 17 | 69.166 | 17.075 | -52.091 |
| q75_positive_donor_labels | 56.180 | placebo__log_c_placebo_corrector_unweighted | 17 | 69.166 | 16.637 | -52.530 |
| q75_positive_donor_labels | 56.180 | arm__log_c_plain_gls | 17 | 69.166 | 17.075 | -52.091 |
| q75_positive_donor_labels | 56.180 | arm__log_c_plain_unweighted | 17 | 69.166 | 16.637 | -52.530 |
| q75_positive_donor_labels | 56.180 | arm__log_c_trees_off_unweighted | 17 | 69.166 | 19.229 | -49.938 |
| q75_positive_donor_labels | 56.180 | base__donor_median | 17 | 69.166 | 9.200 | -59.967 |
| q75_positive_donor_labels | 56.180 | base__predict_zero | 17 | 69.166 | 0.000 | -69.166 |

### Lead 183

| edge_rule | edge | column | n | observed_mean | mean_pred | mean_pred_minus_observed |
|---|---|---|---|---|---|---|
| q75_all_donor_labels | 47.327 | arm__identity_trees_off_unweighted | 29 | 62.236 | 26.438 | -35.797 |
| q75_all_donor_labels | 47.327 | arm__log_c_plain_gls | 29 | 62.236 | 16.978 | -45.258 |
| q75_all_donor_labels | 47.327 | arm__log_c_trees_off_unweighted | 29 | 62.236 | 17.798 | -44.438 |
| q75_all_donor_labels | 47.327 | base__damped_persistence | 1 | 60.494 | 22.465 | -38.029 |
| q75_all_donor_labels | 47.327 | base__donor_median | 29 | 62.236 | 0.000 | -62.236 |
| q75_all_donor_labels | 47.327 | base__persistence | 1 | 60.494 | 0.000 | -60.494 |
| q75_all_donor_labels | 47.327 | base__predict_zero | 29 | 62.236 | 0.000 | -62.236 |
| q75_positive_donor_labels | 57.707 | arm__identity_trees_off_unweighted | 16 | 69.912 | 27.623 | -42.290 |
| q75_positive_donor_labels | 57.707 | arm__log_c_plain_gls | 16 | 69.912 | 18.799 | -51.113 |
| q75_positive_donor_labels | 57.707 | arm__log_c_trees_off_unweighted | 16 | 69.912 | 18.384 | -51.528 |
| q75_positive_donor_labels | 57.707 | base__damped_persistence | 1 | 60.494 | 22.465 | -38.029 |
| q75_positive_donor_labels | 57.707 | base__donor_median | 16 | 69.912 | 0.000 | -69.912 |
| q75_positive_donor_labels | 57.707 | base__persistence | 1 | 60.494 | 0.000 | -60.494 |
| q75_positive_donor_labels | 57.707 | base__predict_zero | 16 | 69.912 | 0.000 | -69.912 |

### Lead 365

| edge_rule | edge | column | n | observed_mean | mean_pred | mean_pred_minus_observed |
|---|---|---|---|---|---|---|
| q75_all_donor_labels | 47.307 | arm__identity_trees_off_unweighted | 27 | 62.603 | 24.925 | -37.678 |
| q75_all_donor_labels | 47.307 | placebo__log_c_placebo_corrector_gls | 27 | 62.603 | 17.250 | -45.353 |
| q75_all_donor_labels | 47.307 | arm__log_c_plain_gls | 27 | 62.603 | 17.250 | -45.353 |
| q75_all_donor_labels | 47.307 | arm__log_c_trees_off_unweighted | 27 | 62.603 | 16.406 | -46.197 |
| q75_all_donor_labels | 47.307 | base__damped_persistence | 1 | 60.494 | 22.465 | -38.029 |
| q75_all_donor_labels | 47.307 | base__donor_median | 27 | 62.603 | 0.000 | -62.603 |
| q75_all_donor_labels | 47.307 | base__persistence | 1 | 60.494 | 0.000 | -60.494 |
| q75_all_donor_labels | 47.307 | base__predict_zero | 27 | 62.603 | 0.000 | -62.603 |
| q75_positive_donor_labels | 59.628 | arm__identity_trees_off_unweighted | 15 | 70.375 | 25.391 | -44.985 |
| q75_positive_donor_labels | 59.628 | placebo__log_c_placebo_corrector_gls | 15 | 70.375 | 18.445 | -51.931 |
| q75_positive_donor_labels | 59.628 | arm__log_c_plain_gls | 15 | 70.375 | 18.445 | -51.931 |
| q75_positive_donor_labels | 59.628 | arm__log_c_trees_off_unweighted | 15 | 70.375 | 16.443 | -53.932 |
| q75_positive_donor_labels | 59.628 | base__damped_persistence | 1 | 60.494 | 22.465 | -38.029 |
| q75_positive_donor_labels | 59.628 | base__donor_median | 15 | 70.375 | 0.000 | -70.375 |
| q75_positive_donor_labels | 59.628 | base__persistence | 1 | 60.494 | 0.000 | -60.494 |
| q75_positive_donor_labels | 59.628 | base__predict_zero | 15 | 70.375 | 0.000 | -70.375 |

## 4. Pooled second (pooled (mixes programmes)): pooled, macro over ecoregions, per test year

No claim is made from a pooled margin.

### Lead 0

| column | line | year | n | n_groups | mae | mae_predict_zero | mae_donor_median |
|---|---|---|---|---|---|---|---|
| arm__arcsine_trees_off_unweighted | year | 2008.000 | 13 | 4 | 32.214 | 38.583 | 33.629 |
| arm__arcsine_trees_off_unweighted | year | 2009.000 | 15 | 4 | 31.867 | 39.922 | 34.424 |
| arm__arcsine_trees_off_unweighted | year | 2010.000 | 15 | 4 | 30.109 | 41.120 | 34.374 |
| arm__arcsine_trees_off_unweighted | year | 2011.000 | 13 | 4 | 35.779 | 45.587 | 40.633 |
| arm__arcsine_trees_off_unweighted | pooled |  | 56 | 4 | 32.385 | 41.247 | 35.668 |
| arm__arcsine_trees_off_unweighted | macro_over_groups |  | 56 | 4 | 32.468 | 41.373 | 35.778 |
| arm__identity_trees_off_unweighted | year | 2008.000 | 13 | 4 | 26.864 | 38.583 | 33.629 |
| arm__identity_trees_off_unweighted | year | 2009.000 | 15 | 4 | 28.348 | 39.922 | 34.424 |
| arm__identity_trees_off_unweighted | year | 2010.000 | 15 | 4 | 23.273 | 41.120 | 34.374 |
| arm__identity_trees_off_unweighted | year | 2011.000 | 13 | 4 | 30.151 | 45.587 | 40.633 |
| arm__identity_trees_off_unweighted | pooled |  | 56 | 4 | 27.063 | 41.247 | 35.668 |
| arm__identity_trees_off_unweighted | macro_over_groups |  | 56 | 4 | 27.152 | 41.373 | 35.778 |
| arm__log_c_trees_off_unweighted | year | 2008.000 | 13 | 4 | 30.640 | 38.583 | 33.629 |
| arm__log_c_trees_off_unweighted | year | 2009.000 | 15 | 4 | 31.210 | 39.922 | 34.424 |
| arm__log_c_trees_off_unweighted | year | 2010.000 | 15 | 4 | 28.416 | 41.120 | 34.374 |
| arm__log_c_trees_off_unweighted | year | 2011.000 | 13 | 4 | 34.982 | 45.587 | 40.633 |
| arm__log_c_trees_off_unweighted | pooled |  | 56 | 4 | 31.205 | 41.247 | 35.668 |
| arm__log_c_trees_off_unweighted | macro_over_groups |  | 56 | 4 | 31.294 | 41.373 | 35.778 |
| base__donor_median | year | 2008.000 | 13 | 4 | 33.629 | 38.583 | 33.629 |
| base__donor_median | year | 2009.000 | 15 | 4 | 34.424 | 39.922 | 34.424 |
| base__donor_median | year | 2010.000 | 15 | 4 | 34.374 | 41.120 | 34.374 |
| base__donor_median | year | 2011.000 | 13 | 4 | 40.633 | 45.587 | 40.633 |
| base__donor_median | pooled |  | 56 | 4 | 35.668 | 41.247 | 35.668 |
| base__donor_median | macro_over_groups |  | 56 | 4 | 35.778 | 41.373 | 35.778 |
| base__predict_zero | year | 2008.000 | 13 | 4 | 38.583 | 38.583 | 33.629 |
| base__predict_zero | year | 2009.000 | 15 | 4 | 39.922 | 39.922 | 34.424 |
| base__predict_zero | year | 2010.000 | 15 | 4 | 41.120 | 41.120 | 34.374 |
| base__predict_zero | year | 2011.000 | 13 | 4 | 45.587 | 45.587 | 40.633 |
| base__predict_zero | pooled |  | 56 | 4 | 41.247 | 41.247 | 35.668 |
| base__predict_zero | macro_over_groups |  | 56 | 4 | 41.373 | 41.373 | 35.778 |

### Lead 183

| column | line | year | n | n_groups | mae | mae_predict_zero | mae_donor_median |
|---|---|---|---|---|---|---|---|
| arm__identity_trees_off_unweighted | year | 2008.000 | 13 | 4 | 26.806 | 38.583 | 38.583 |
| arm__identity_trees_off_unweighted | year | 2009.000 | 15 | 4 | 28.784 | 39.922 | 39.922 |
| arm__identity_trees_off_unweighted | year | 2010.000 | 15 | 4 | 23.168 | 41.120 | 41.120 |
| arm__identity_trees_off_unweighted | year | 2011.000 | 13 | 4 | 30.099 | 45.587 | 45.587 |
| arm__identity_trees_off_unweighted | pooled |  | 56 | 4 | 27.126 | 41.247 | 41.247 |
| arm__identity_trees_off_unweighted | macro_over_groups |  | 56 | 4 | 27.214 | 41.373 | 41.373 |
| arm__log_c_trees_off_unweighted | year | 2008.000 | 13 | 4 | 30.702 | 38.583 | 38.583 |
| arm__log_c_trees_off_unweighted | year | 2009.000 | 15 | 4 | 31.779 | 39.922 | 39.922 |
| arm__log_c_trees_off_unweighted | year | 2010.000 | 15 | 4 | 28.717 | 41.120 | 41.120 |
| arm__log_c_trees_off_unweighted | year | 2011.000 | 13 | 4 | 34.909 | 45.587 | 45.587 |
| arm__log_c_trees_off_unweighted | pooled |  | 56 | 4 | 31.435 | 41.247 | 41.247 |
| arm__log_c_trees_off_unweighted | macro_over_groups |  | 56 | 4 | 31.527 | 41.373 | 41.373 |
| base__damped_persistence | year | 2008.000 | 1 | 1 | 12.029 | 35.682 | 35.682 |
| base__damped_persistence | year | 2009.000 | 2 | 2 | 30.784 | 30.247 | 30.247 |
| base__damped_persistence | year | 2010.000 | 2 | 2 | 21.880 | 11.731 | 11.731 |
| base__damped_persistence | year | 2011.000 | 1 | 1 | 12.898 | 0.000 | 0.000 |
| base__damped_persistence | pooled |  | 6 | 4 | 21.709 | 19.940 | 19.940 |
| base__damped_persistence | macro_over_groups |  | 6 | 4 | 22.539 | 26.977 | 26.977 |
| base__donor_median | year | 2008.000 | 13 | 4 | 38.583 | 38.583 | 38.583 |
| base__donor_median | year | 2009.000 | 15 | 4 | 39.922 | 39.922 | 39.922 |
| base__donor_median | year | 2010.000 | 15 | 4 | 41.120 | 41.120 | 41.120 |
| base__donor_median | year | 2011.000 | 13 | 4 | 45.587 | 45.587 | 45.587 |
| base__donor_median | pooled |  | 56 | 4 | 41.247 | 41.247 | 41.247 |
| base__donor_median | macro_over_groups |  | 56 | 4 | 41.373 | 41.373 | 41.373 |
| base__persistence | year | 2008.000 | 1 | 1 | 11.625 | 35.682 | 35.682 |
| base__persistence | year | 2009.000 | 2 | 2 | 42.016 | 30.247 | 30.247 |
| base__persistence | year | 2010.000 | 2 | 2 | 24.293 | 11.731 | 11.731 |
| base__persistence | year | 2011.000 | 1 | 1 | 25.796 | 0.000 | 0.000 |
| base__persistence | pooled |  | 6 | 4 | 28.340 | 19.940 | 19.940 |
| base__persistence | macro_over_groups |  | 6 | 4 | 30.270 | 26.977 | 26.977 |
| base__predict_zero | year | 2008.000 | 13 | 4 | 38.583 | 38.583 | 38.583 |
| base__predict_zero | year | 2009.000 | 15 | 4 | 39.922 | 39.922 | 39.922 |
| base__predict_zero | year | 2010.000 | 15 | 4 | 41.120 | 41.120 | 41.120 |
| base__predict_zero | year | 2011.000 | 13 | 4 | 45.587 | 45.587 | 45.587 |
| base__predict_zero | pooled |  | 56 | 4 | 41.247 | 41.247 | 41.247 |
| base__predict_zero | macro_over_groups |  | 56 | 4 | 41.373 | 41.373 | 41.373 |

### Lead 365

| column | line | year | n | n_groups | mae | mae_predict_zero | mae_donor_median |
|---|---|---|---|---|---|---|---|
| arm__identity_trees_off_unweighted | year | 2008.000 | 12 | 4 | 27.665 | 38.294 | 38.294 |
| arm__identity_trees_off_unweighted | year | 2009.000 | 15 | 4 | 30.250 | 39.922 | 39.922 |
| arm__identity_trees_off_unweighted | year | 2010.000 | 12 | 4 | 24.428 | 39.899 | 39.899 |
| arm__identity_trees_off_unweighted | year | 2011.000 | 13 | 4 | 30.641 | 45.587 | 45.587 |
| arm__identity_trees_off_unweighted | pooled |  | 52 | 4 | 28.408 | 40.957 | 40.957 |
| arm__identity_trees_off_unweighted | macro_over_groups |  | 52 | 4 | 28.449 | 41.044 | 41.044 |
| arm__log_c_trees_off_unweighted | year | 2008.000 | 12 | 4 | 31.185 | 38.294 | 38.294 |
| arm__log_c_trees_off_unweighted | year | 2009.000 | 15 | 4 | 33.128 | 39.922 | 39.922 |
| arm__log_c_trees_off_unweighted | year | 2010.000 | 12 | 4 | 29.544 | 39.899 | 39.899 |
| arm__log_c_trees_off_unweighted | year | 2011.000 | 13 | 4 | 35.304 | 45.587 | 45.587 |
| arm__log_c_trees_off_unweighted | pooled |  | 52 | 4 | 32.397 | 40.957 | 40.957 |
| arm__log_c_trees_off_unweighted | macro_over_groups |  | 52 | 4 | 32.438 | 41.044 | 41.044 |
| base__damped_persistence | year | 2008.000 | 1 | 1 | 12.029 | 35.682 | 35.682 |
| base__damped_persistence | year | 2009.000 | 2 | 2 | 30.784 | 30.247 | 30.247 |
| base__damped_persistence | year | 2010.000 | 1 | 1 | 42.564 | 0.000 | 0.000 |
| base__damped_persistence | year | 2011.000 | 1 | 1 | 0.000 | 0.000 | 0.000 |
| base__damped_persistence | pooled |  | 5 | 4 | 23.232 | 19.235 | 19.235 |
| base__damped_persistence | macro_over_groups |  | 5 | 4 | 20.777 | 24.044 | 24.044 |
| base__donor_median | year | 2008.000 | 12 | 4 | 38.294 | 38.294 | 38.294 |
| base__donor_median | year | 2009.000 | 15 | 4 | 39.922 | 39.922 | 39.922 |
| base__donor_median | year | 2010.000 | 12 | 4 | 39.899 | 39.899 | 39.899 |
| base__donor_median | year | 2011.000 | 13 | 4 | 45.587 | 45.587 | 45.587 |
| base__donor_median | pooled |  | 52 | 4 | 40.957 | 40.957 | 40.957 |
| base__donor_median | macro_over_groups |  | 52 | 4 | 41.044 | 41.044 | 41.044 |
| base__persistence | year | 2008.000 | 1 | 1 | 11.625 | 35.682 | 35.682 |
| base__persistence | year | 2009.000 | 2 | 2 | 42.016 | 30.247 | 30.247 |
| base__persistence | year | 2010.000 | 1 | 1 | 47.391 | 0.000 | 0.000 |
| base__persistence | year | 2011.000 | 1 | 1 | 25.796 | 0.000 | 0.000 |
| base__persistence | pooled |  | 5 | 4 | 33.769 | 19.235 | 19.235 |
| base__persistence | macro_over_groups |  | 5 | 4 | 33.345 | 24.044 | 24.044 |
| base__predict_zero | year | 2008.000 | 12 | 4 | 38.294 | 38.294 | 38.294 |
| base__predict_zero | year | 2009.000 | 15 | 4 | 39.922 | 39.922 | 39.922 |
| base__predict_zero | year | 2010.000 | 12 | 4 | 39.899 | 39.899 | 39.899 |
| base__predict_zero | year | 2011.000 | 13 | 4 | 45.587 | 45.587 | 45.587 |
| base__predict_zero | pooled |  | 52 | 4 | 40.957 | 40.957 | 40.957 |
| base__predict_zero | macro_over_groups |  | 52 | 4 | 41.044 | 41.044 | 41.044 |

## 5. Per ecoregion (n, zero share, programme mix; never ranked by MAE)

| group | n | zero_share | n_field | n_lab | n_remote |
|---|---|---|---|---|---|
| g_a | 14 | 0.143 | 7 | 3 | 4 |
| g_b | 13 | 0.154 | 3 | 7 | 3 |
| g_c | 15 | 0.200 | 4 | 3 | 8 |
| g_d | 14 | 0.286 | 8 | 3 | 3 |

## 6. Counts

### Rows left with no tree (V2 pool tree drop), per arm and pass

| pass | lead | arm | n_rows | n_rows_no_tree | share_no_tree |
|---|---|---|---|---|---|
| decision_surface | 0 | arcsine_corrector_gls | 43 | 38 | 0.884 |
| decision_surface | 0 | arcsine_corrector_unweighted | 43 | 38 | 0.884 |
| decision_surface | 0 | arcsine_plain_gls | 43 | 38 | 0.884 |
| decision_surface | 0 | arcsine_plain_unweighted | 43 | 38 | 0.884 |
| decision_surface | 0 | identity_corrector_gls | 43 | 38 | 0.884 |
| decision_surface | 0 | identity_corrector_unweighted | 43 | 38 | 0.884 |
| decision_surface | 0 | identity_plain_gls | 43 | 38 | 0.884 |
| decision_surface | 0 | identity_plain_unweighted | 43 | 38 | 0.884 |
| decision_surface | 0 | log_c_corrector_gls | 43 | 38 | 0.884 |
| decision_surface | 0 | log_c_corrector_unweighted | 43 | 38 | 0.884 |
| decision_surface | 0 | log_c_plain_gls | 43 | 38 | 0.884 |
| decision_surface | 0 | log_c_plain_unweighted | 43 | 38 | 0.884 |
| test_pass | 0 | arcsine_corrector_gls | 56 | 23 | 0.411 |
| test_pass | 0 | arcsine_corrector_unweighted | 56 | 23 | 0.411 |
| test_pass | 0 | arcsine_placebo_corrector_gls | 56 | 23 | 0.411 |
| test_pass | 0 | arcsine_placebo_corrector_unweighted | 56 | 23 | 0.411 |
| test_pass | 0 | arcsine_plain_gls | 56 | 23 | 0.411 |
| test_pass | 0 | arcsine_plain_unweighted | 56 | 23 | 0.411 |
| test_pass | 0 | identity_corrector_gls | 56 | 23 | 0.411 |
| test_pass | 0 | identity_corrector_unweighted | 56 | 23 | 0.411 |
| test_pass | 0 | identity_placebo_corrector_gls | 56 | 23 | 0.411 |
| test_pass | 0 | identity_placebo_corrector_unweighted | 56 | 23 | 0.411 |
| test_pass | 0 | identity_plain_gls | 56 | 23 | 0.411 |
| test_pass | 0 | identity_plain_unweighted | 56 | 23 | 0.411 |
| test_pass | 0 | log_c_corrector_gls | 56 | 23 | 0.411 |
| test_pass | 0 | log_c_corrector_unweighted | 56 | 23 | 0.411 |
| test_pass | 0 | log_c_placebo_corrector_gls | 56 | 23 | 0.411 |
| test_pass | 0 | log_c_placebo_corrector_unweighted | 56 | 23 | 0.411 |
| test_pass | 0 | log_c_plain_gls | 56 | 23 | 0.411 |
| test_pass | 0 | log_c_plain_unweighted | 56 | 23 | 0.411 |
| guard | 183 | log_c_plain_gls | 36 | 36 | 1.000 |
| test_pass | 183 | log_c_plain_gls | 56 | 24 | 0.429 |
| guard | 365 | log_c_plain_gls | 28 | 28 | 1.000 |
| test_pass | 365 | log_c_placebo_corrector_gls | 52 | 26 | 0.500 |
| test_pass | 365 | log_c_plain_gls | 52 | 26 | 0.500 |

### Pool fallbacks (under 12 valid pool rows)

| pass | lead | pools_file | rows | rows_pool_fallback | matches_record |
|---|---|---|---|---|---|
| decision_surface | 0 | pools_decision_surface.parquet | 43 | 0 | yes |
| test_pass | 0 | pools_test_pass.parquet | 56 | 0 | yes |
| guard | 183 | ladder\lead_183\pools_guard.parquet | 36 | 0 | yes |
| test_pass | 183 | ladder\lead_183\pools_test_pass.parquet | 56 | 0 | yes |
| guard | 365 | ladder\lead_365\pools_guard.parquet | 28 | 0 | yes |
| test_pass | 365 | ladder\lead_365\pools_test_pass.parquet | 52 | 0 | yes |

### Rows left out

| what | lead | source | rows_record | rows_file |
|---|---|---|---|---|
| H4 test rows absent at the lead (left out of scoring) | 183 | lead.json issue_features_missing / issue_missing_rows.parquet | 0 | 0 |
| H4 test rows absent at the lead (left out of scoring) | 365 | lead.json issue_features_missing / issue_missing_rows.parquet | 4 | 4 |
| S1/G1 rows with missing router context, left out | 0 | context_missing/decision_surface.parquet (neighbour_pool:decision_surface) | 3 | 3 |
| S1/G1 rows with missing router context, left out | 0 | context_missing/lead_0_contract.parquet (neighbour_pool:lead_0_contract) | 3 | 3 |
| S1/G1 rows with missing router context, left out | 183 | context_missing/lead_183_guard.parquet (neighbour_pool:lead_183_guard) | 3 | 3 |
| S1/G1 rows with missing router context, left out | 183 | context_missing/lead_183_test_pass.parquet (neighbour_pool:lead_183_test_pass) | 3 | 3 |
| S1/G1 rows with missing router context, left out | 365 | context_missing/lead_365_guard.parquet (neighbour_pool:lead_365_guard) | 3 | 3 |
| S1/G1 rows with missing router context, left out | 365 | context_missing/lead_365_test_pass.parquet (neighbour_pool:lead_365_test_pass) | 3 | 3 |
| S1/G1 rows with missing router context, left out | 0 | context_missing/test_pass.parquet (neighbour_pool:test_pass) | 3 | 3 |

## 7. Leads

Leads [0, 183, 365]; the ladder rows are scored on the rows common to all leads (rows_basis 'common' in every CSV), with all rows beside.

