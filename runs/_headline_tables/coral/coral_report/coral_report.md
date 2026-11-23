# Coral report-only tables (coral_report.py 1.2.0)

- Run folder: `D:\treeroute\runs\coral\headline\20261020_f3b8e3da` (kind headline, package coral)
- Script SHA-256: `063be40279a1b4ae0937a21eaec73af98fc4fb379349e34cbdb9c67cf2bacf88`; every input file's SHA-256 is in inputs_manifest.json.
- Report only: nothing here changes a fit, a pick or the verdict (draft section 6.2).
- Every forecast is read as "given a survey on this date". The 365-day row is risk stratification.
- Predict-zero and the donor-row median MAE are printed beside every MAE, on the same rows.

## 1. Per programme (stratum `programme`)

Values with fewer than 10 rows are shown with n only. Full metrics for every column are in per_programme.csv.

### Lead 0 (all rows; adopted `arm__arcsine_corrector_gls`)

| stratum_value | column | n | zero_share | mae | mae_predict_zero | mae_donor_median | hit | corr2 | n_only |
|---|---|---|---|---|---|---|---|---|---|
| ALL | arm__arcsine_corrector_gls | 2312 | 0.557 | 6.698 | 8.100 | 8.294 | 0.742 | 0.464 | no |
| ALL | arm__arcsine_trees_off_unweighted | 2312 | 0.557 | 7.536 | 8.100 | 8.294 | 0.749 | 0.162 | no |
| ALL | arm__identity_trees_off_unweighted | 2312 | 0.557 | 7.975 | 8.100 | 8.294 | 0.686 | 0.223 | no |
| ALL | arm__log_c_trees_off_unweighted | 2312 | 0.557 | 7.517 | 8.100 | 8.294 | 0.779 | 0.095 | no |
| ALL | base__donor_median | 2312 | 0.557 | 8.294 | 8.100 | 8.294 | 0.773 |  | no |
| ALL | base__predict_zero | 2312 | 0.557 | 8.100 | 8.100 | 8.294 | 0.762 |  | no |
| AGRRA | arm__arcsine_corrector_gls | 1 |  |  |  |  |  |  | yes |
| AGRRA | arm__arcsine_trees_off_unweighted | 1 |  |  |  |  |  |  | yes |
| AGRRA | arm__identity_trees_off_unweighted | 1 |  |  |  |  |  |  | yes |
| AGRRA | arm__log_c_trees_off_unweighted | 1 |  |  |  |  |  |  | yes |
| AGRRA | base__donor_median | 1 |  |  |  |  |  |  | yes |
| AGRRA | base__predict_zero | 1 |  |  |  |  |  |  | yes |
| Donner | arm__arcsine_corrector_gls | 0 |  |  |  |  |  |  | yes |
| Donner | arm__arcsine_trees_off_unweighted | 0 |  |  |  |  |  |  | yes |
| Donner | arm__identity_trees_off_unweighted | 0 |  |  |  |  |  |  | yes |
| Donner | arm__log_c_trees_off_unweighted | 0 |  |  |  |  |  |  | yes |
| Donner | base__donor_median | 0 |  |  |  |  |  |  | yes |
| Donner | base__predict_zero | 0 |  |  |  |  |  |  | yes |
| FRRP | arm__arcsine_corrector_gls | 190 | 0.084 | 7.660 | 11.735 | 10.912 | 0.416 | 0.007 | no |
| FRRP | arm__arcsine_trees_off_unweighted | 190 | 0.084 | 9.078 | 11.735 | 10.912 | 0.332 | 0.004 | no |
| FRRP | arm__identity_trees_off_unweighted | 190 | 0.084 | 10.117 | 11.735 | 10.912 | 0.316 | 0.001 | no |
| FRRP | arm__log_c_trees_off_unweighted | 190 | 0.084 | 7.858 | 11.735 | 10.912 | 0.447 | 0.016 | no |
| FRRP | base__donor_median | 190 | 0.084 | 10.912 | 11.735 | 10.912 | 0.347 |  | no |
| FRRP | base__predict_zero | 190 | 0.084 | 11.735 | 11.735 | 10.912 | 0.295 |  | no |
| McClanahan | arm__arcsine_corrector_gls | 189 | 0.011 | 35.060 | 54.819 | 53.840 | 0.138 | 0.228 | no |
| McClanahan | arm__arcsine_trees_off_unweighted | 189 | 0.011 | 45.585 | 54.819 | 53.840 | 0.085 | 0.020 | no |
| McClanahan | arm__identity_trees_off_unweighted | 189 | 0.011 | 41.149 | 54.819 | 53.840 | 0.085 | 0.032 | no |
| McClanahan | arm__log_c_trees_off_unweighted | 189 | 0.011 | 50.632 | 54.819 | 53.840 | 0.069 | 0.024 | no |
| McClanahan | base__donor_median | 189 | 0.011 | 53.840 | 54.819 | 53.840 | 0.069 |  | no |
| McClanahan | base__predict_zero | 189 | 0.011 | 54.819 | 54.819 | 53.840 | 0.058 |  | no |
| Reef_Check | arm__arcsine_corrector_gls | 1932 | 0.657 | 3.829 | 3.170 | 3.581 | 0.834 | 0.060 | no |
| Reef_Check | arm__arcsine_trees_off_unweighted | 1932 | 0.657 | 3.660 | 3.170 | 3.581 | 0.855 | 0.024 | no |
| Reef_Check | arm__identity_trees_off_unweighted | 1932 | 0.657 | 4.517 | 3.170 | 3.581 | 0.781 | 0.031 | no |
| Reef_Check | arm__log_c_trees_off_unweighted | 1932 | 0.657 | 3.264 | 3.170 | 3.581 | 0.881 | 0.019 | no |
| Reef_Check | base__donor_median | 1932 | 0.657 | 3.581 | 3.170 | 3.581 | 0.884 |  | no |
| Reef_Check | base__predict_zero | 1932 | 0.657 | 3.170 | 3.170 | 3.581 | 0.877 |  | no |
| mixed | arm__arcsine_corrector_gls | 0 |  |  |  |  |  |  | yes |
| mixed | arm__arcsine_trees_off_unweighted | 0 |  |  |  |  |  |  | yes |
| mixed | arm__identity_trees_off_unweighted | 0 |  |  |  |  |  |  | yes |
| mixed | arm__log_c_trees_off_unweighted | 0 |  |  |  |  |  |  | yes |
| mixed | base__donor_median | 0 |  |  |  |  |  |  | yes |
| mixed | base__predict_zero | 0 |  |  |  |  |  |  | yes |

- Predict-zero beats the adopted answer on Reef_Check at lead 0 (MAE 3.170 vs 3.829).

### Lead 183 (all rows; adopted `arm__arcsine_corrector_gls`)

| stratum_value | column | n | zero_share | mae | mae_predict_zero | mae_donor_median | hit | corr2 | n_only |
|---|---|---|---|---|---|---|---|---|---|
| ALL | arm__arcsine_corrector_gls | 2312 | 0.557 | 7.710 | 8.100 | 8.294 | 0.763 | 0.139 | no |
| ALL | arm__arcsine_trees_off_unweighted | 2312 | 0.557 | 7.730 | 8.100 | 8.294 | 0.751 | 0.101 | no |
| ALL | arm__identity_trees_off_unweighted | 2312 | 0.557 | 8.193 | 8.100 | 8.294 | 0.691 | 0.156 | no |
| ALL | base__damped_persistence | 1419 | 0.693 | 5.478 | 3.527 | 3.991 | 0.679 | 0.006 | no |
| ALL | base__donor_median | 2312 | 0.557 | 8.294 | 8.100 | 8.294 | 0.773 |  | no |
| ALL | base__persistence | 1419 | 0.693 | 4.529 | 3.527 | 3.991 | 0.818 | 0.052 | no |
| ALL | base__predict_zero | 2312 | 0.557 | 8.100 | 8.100 | 8.294 | 0.762 |  | no |
| AGRRA | arm__arcsine_corrector_gls | 1 |  |  |  |  |  |  | yes |
| AGRRA | arm__arcsine_trees_off_unweighted | 1 |  |  |  |  |  |  | yes |
| AGRRA | arm__identity_trees_off_unweighted | 1 |  |  |  |  |  |  | yes |
| AGRRA | base__damped_persistence | 0 |  |  |  |  |  |  | yes |
| AGRRA | base__donor_median | 1 |  |  |  |  |  |  | yes |
| AGRRA | base__persistence | 0 |  |  |  |  |  |  | yes |
| AGRRA | base__predict_zero | 1 |  |  |  |  |  |  | yes |
| Donner | arm__arcsine_corrector_gls | 0 |  |  |  |  |  |  | yes |
| Donner | arm__arcsine_trees_off_unweighted | 0 |  |  |  |  |  |  | yes |
| Donner | arm__identity_trees_off_unweighted | 0 |  |  |  |  |  |  | yes |
| Donner | base__damped_persistence | 0 |  |  |  |  |  |  | yes |
| Donner | base__donor_median | 0 |  |  |  |  |  |  | yes |
| Donner | base__persistence | 0 |  |  |  |  |  |  | yes |
| Donner | base__predict_zero | 0 |  |  |  |  |  |  | yes |
| FRRP | arm__arcsine_corrector_gls | 190 | 0.084 | 7.320 | 11.735 | 10.912 | 0.500 | 0.036 | no |
| FRRP | arm__arcsine_trees_off_unweighted | 190 | 0.084 | 7.453 | 11.735 | 10.912 | 0.463 | 0.010 | no |
| FRRP | arm__identity_trees_off_unweighted | 190 | 0.084 | 7.924 | 11.735 | 10.912 | 0.442 | 0.005 | no |
| FRRP | base__damped_persistence | 23 | 0.174 | 4.918 | 5.839 | 5.189 | 0.609 | 0.141 | no |
| FRRP | base__donor_median | 190 | 0.084 | 10.912 | 11.735 | 10.912 | 0.347 |  | no |
| FRRP | base__persistence | 23 | 0.174 | 4.523 | 5.839 | 5.189 | 0.652 | 0.212 | no |
| FRRP | base__predict_zero | 190 | 0.084 | 11.735 | 11.735 | 10.912 | 0.295 |  | no |
| McClanahan | arm__arcsine_corrector_gls | 189 | 0.011 | 48.292 | 54.819 | 53.840 | 0.095 | 0.006 | no |
| McClanahan | arm__arcsine_trees_off_unweighted | 189 | 0.011 | 47.792 | 54.819 | 53.840 | 0.116 | 0.009 | no |
| McClanahan | arm__identity_trees_off_unweighted | 189 | 0.011 | 43.186 | 54.819 | 53.840 | 0.111 | 0.032 | no |
| McClanahan | base__damped_persistence | 6 | 0.000 | 44.856 | 53.132 | 52.132 | 0.000 | 0.602 | no |
| McClanahan | base__donor_median | 189 | 0.011 | 53.840 | 54.819 | 53.840 | 0.069 |  | no |
| McClanahan | base__persistence | 6 | 0.000 | 38.312 | 53.132 | 52.132 | 0.000 | 0.567 | no |
| McClanahan | base__predict_zero | 189 | 0.011 | 54.819 | 54.819 | 53.840 | 0.058 |  | no |
| Reef_Check | arm__arcsine_corrector_gls | 1932 | 0.657 | 3.778 | 3.170 | 3.581 | 0.855 | 0.002 | no |
| Reef_Check | arm__arcsine_trees_off_unweighted | 1932 | 0.657 | 3.837 | 3.170 | 3.581 | 0.842 | 0.004 | no |
| Reef_Check | arm__identity_trees_off_unweighted | 1932 | 0.657 | 4.798 | 3.170 | 3.581 | 0.773 | 0.007 | no |
| Reef_Check | base__damped_persistence | 1390 | 0.704 | 5.318 | 3.275 | 3.764 | 0.683 | 0.004 | no |
| Reef_Check | base__donor_median | 1932 | 0.657 | 3.581 | 3.170 | 3.581 | 0.884 |  | no |
| Reef_Check | base__persistence | 1390 | 0.704 | 4.384 | 3.275 | 3.764 | 0.824 | 0.043 | no |
| Reef_Check | base__predict_zero | 1932 | 0.657 | 3.170 | 3.170 | 3.581 | 0.877 |  | no |
| mixed | arm__arcsine_corrector_gls | 0 |  |  |  |  |  |  | yes |
| mixed | arm__arcsine_trees_off_unweighted | 0 |  |  |  |  |  |  | yes |
| mixed | arm__identity_trees_off_unweighted | 0 |  |  |  |  |  |  | yes |
| mixed | base__damped_persistence | 0 |  |  |  |  |  |  | yes |
| mixed | base__donor_median | 0 |  |  |  |  |  |  | yes |
| mixed | base__persistence | 0 |  |  |  |  |  |  | yes |
| mixed | base__predict_zero | 0 |  |  |  |  |  |  | yes |

- Predict-zero beats the adopted answer on Reef_Check at lead 183 (MAE 3.170 vs 3.778).

### Lead 365 (all rows; adopted `base__donor_median`, declined)

| stratum_value | column | n | zero_share | mae | mae_predict_zero | mae_donor_median | hit | corr2 | n_only |
|---|---|---|---|---|---|---|---|---|---|
| ALL | arm__arcsine_corrector_gls | 2312 | 0.557 | 8.281 | 8.100 | 8.294 | 0.728 | 0.038 | no |
| ALL | arm__arcsine_trees_off_unweighted | 2312 | 0.557 | 8.141 | 8.100 | 8.294 | 0.724 | 0.062 | no |
| ALL | arm__identity_trees_off_unweighted | 2312 | 0.557 | 8.676 | 8.100 | 8.294 | 0.677 | 0.105 | no |
| ALL | base__damped_persistence | 1334 | 0.693 | 5.948 | 3.619 | 4.082 | 0.645 | 0.001 | no |
| ALL | base__donor_median | 2312 | 0.557 | 8.294 | 8.100 | 8.294 | 0.773 |  | no |
| ALL | base__persistence | 1334 | 0.693 | 4.893 | 3.619 | 4.082 | 0.806 | 0.014 | no |
| ALL | base__predict_zero | 2312 | 0.557 | 8.100 | 8.100 | 8.294 | 0.762 |  | no |
| AGRRA | arm__arcsine_corrector_gls | 1 |  |  |  |  |  |  | yes |
| AGRRA | arm__arcsine_trees_off_unweighted | 1 |  |  |  |  |  |  | yes |
| AGRRA | arm__identity_trees_off_unweighted | 1 |  |  |  |  |  |  | yes |
| AGRRA | base__damped_persistence | 0 |  |  |  |  |  |  | yes |
| AGRRA | base__donor_median | 1 |  |  |  |  |  |  | yes |
| AGRRA | base__persistence | 0 |  |  |  |  |  |  | yes |
| AGRRA | base__predict_zero | 1 |  |  |  |  |  |  | yes |
| Donner | arm__arcsine_corrector_gls | 0 |  |  |  |  |  |  | yes |
| Donner | arm__arcsine_trees_off_unweighted | 0 |  |  |  |  |  |  | yes |
| Donner | arm__identity_trees_off_unweighted | 0 |  |  |  |  |  |  | yes |
| Donner | base__damped_persistence | 0 |  |  |  |  |  |  | yes |
| Donner | base__donor_median | 0 |  |  |  |  |  |  | yes |
| Donner | base__persistence | 0 |  |  |  |  |  |  | yes |
| Donner | base__predict_zero | 0 |  |  |  |  |  |  | yes |
| FRRP | arm__arcsine_corrector_gls | 190 | 0.084 | 7.863 | 11.735 | 10.912 | 0.442 | 0.009 | no |
| FRRP | arm__arcsine_trees_off_unweighted | 190 | 0.084 | 7.635 | 11.735 | 10.912 | 0.447 | 0.005 | no |
| FRRP | arm__identity_trees_off_unweighted | 190 | 0.084 | 7.499 | 11.735 | 10.912 | 0.442 | 0.007 | no |
| FRRP | base__damped_persistence | 16 | 0.062 | 6.326 | 5.857 | 4.984 | 0.375 | 0.003 | no |
| FRRP | base__donor_median | 190 | 0.084 | 10.912 | 11.735 | 10.912 | 0.347 |  | no |
| FRRP | base__persistence | 16 | 0.062 | 2.998 | 5.857 | 4.984 | 0.688 | 0.652 | no |
| FRRP | base__predict_zero | 190 | 0.084 | 11.735 | 11.735 | 10.912 | 0.295 |  | no |
| McClanahan | arm__arcsine_corrector_gls | 189 | 0.011 | 50.346 | 54.819 | 53.840 | 0.085 | 0.079 | no |
| McClanahan | arm__arcsine_trees_off_unweighted | 189 | 0.011 | 48.493 | 54.819 | 53.840 | 0.069 | 0.007 | no |
| McClanahan | arm__identity_trees_off_unweighted | 189 | 0.011 | 44.226 | 54.819 | 53.840 | 0.053 | 0.023 | no |
| McClanahan | base__damped_persistence | 6 | 0.000 | 44.856 | 53.132 | 52.132 | 0.000 | 0.602 | no |
| McClanahan | base__donor_median | 189 | 0.011 | 53.840 | 54.819 | 53.840 | 0.069 |  | no |
| McClanahan | base__persistence | 6 | 0.000 | 38.312 | 53.132 | 52.132 | 0.000 | 0.567 | no |
| McClanahan | base__predict_zero | 189 | 0.011 | 54.819 | 54.819 | 53.840 | 0.058 |  | no |
| Reef_Check | arm__arcsine_corrector_gls | 1932 | 0.657 | 4.207 | 3.170 | 3.581 | 0.819 | 0.002 | no |
| Reef_Check | arm__arcsine_trees_off_unweighted | 1932 | 0.657 | 4.242 | 3.170 | 3.581 | 0.816 | 0.001 | no |
| Reef_Check | arm__identity_trees_off_unweighted | 1932 | 0.657 | 5.313 | 3.170 | 3.581 | 0.761 | 0.003 | no |
| Reef_Check | base__damped_persistence | 1312 | 0.704 | 5.765 | 3.365 | 3.851 | 0.652 | 0.000 | no |
| Reef_Check | base__donor_median | 1932 | 0.657 | 3.581 | 3.170 | 3.581 | 0.884 |  | no |
| Reef_Check | base__persistence | 1312 | 0.704 | 4.763 | 3.365 | 3.851 | 0.811 | 0.008 | no |
| Reef_Check | base__predict_zero | 1932 | 0.657 | 3.170 | 3.170 | 3.581 | 0.877 |  | no |
| mixed | arm__arcsine_corrector_gls | 0 |  |  |  |  |  |  | yes |
| mixed | arm__arcsine_trees_off_unweighted | 0 |  |  |  |  |  |  | yes |
| mixed | arm__identity_trees_off_unweighted | 0 |  |  |  |  |  |  | yes |
| mixed | base__damped_persistence | 0 |  |  |  |  |  |  | yes |
| mixed | base__donor_median | 0 |  |  |  |  |  |  | yes |
| mixed | base__persistence | 0 |  |  |  |  |  |  | yes |
| mixed | base__predict_zero | 0 |  |  |  |  |  |  | yes |

- Predict-zero beats the adopted answer on Reef_Check at lead 365 (MAE 3.170 vs 3.581).

### Programme verdict lines (D74 rule, report only; the ALL line is the registered verdict's rows)

| lead | rows_basis | stratum_value | n_rows | n_groups | mean | se | low | high | tag | matches_engine |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | all | ALL | 2312 | 37 | 5.207 | 1.650 | 1.972 | 8.441 | helps | yes |
| 0 | all | AGRRA | 1 | 1 | 4.570 |  |  |  | cannot_tell |  |
| 0 | all | Donner | 0 | 0 |  |  |  |  | no rows |  |
| 0 | all | FRRP | 190 | 1 | 3.252 |  |  |  | cannot_tell |  |
| 0 | all | McClanahan | 189 | 15 | 17.162 | 3.037 | 11.210 | 23.114 | helps |  |
| 0 | all | Reef_Check | 1932 | 28 | -0.625 | 0.338 | -1.287 | 0.038 | cannot_tell |  |
| 0 | all | mixed | 0 | 0 |  |  |  |  | no rows |  |
| 0 | common | ALL | 2312 | 37 | 5.207 | 1.650 | 1.972 | 8.441 | helps | yes |
| 0 | common | AGRRA | 1 | 1 | 4.570 |  |  |  | cannot_tell |  |
| 0 | common | Donner | 0 | 0 |  |  |  |  | no rows |  |
| 0 | common | FRRP | 190 | 1 | 3.252 |  |  |  | cannot_tell |  |
| 0 | common | McClanahan | 189 | 15 | 17.162 | 3.037 | 11.210 | 23.114 | helps |  |
| 0 | common | Reef_Check | 1932 | 28 | -0.625 | 0.338 | -1.287 | 0.038 | cannot_tell |  |
| 0 | common | mixed | 0 | 0 |  |  |  |  | no rows |  |
| 183 | common | ALL | 2312 | 37 | 1.747 | 0.829 | 0.122 | 3.372 | helps | yes |
| 183 | common | AGRRA | 1 | 1 | 1.475 |  |  |  | cannot_tell |  |
| 183 | common | Donner | 0 | 0 |  |  |  |  | no rows |  |
| 183 | common | FRRP | 190 | 1 | 3.591 |  |  |  | cannot_tell |  |
| 183 | common | McClanahan | 189 | 15 | 4.611 | 1.831 | 1.021 | 8.201 | helps |  |
| 183 | common | Reef_Check | 1932 | 28 | -0.205 | 0.225 | -0.646 | 0.236 | equivalent |  |
| 183 | common | mixed | 0 | 0 |  |  |  |  | no rows |  |
| 365 | common | ALL | 2312 | 37 | 0.000 | 0.000 | 0.000 | 0.000 | declined | yes |
| 365 | common | AGRRA | 1 | 1 | 0.000 |  |  |  | declined |  |
| 365 | common | Donner | 0 | 0 |  |  |  |  | no rows |  |
| 365 | common | FRRP | 190 | 1 | 0.000 |  |  |  | declined |  |
| 365 | common | McClanahan | 189 | 15 | 0.000 | 0.000 | 0.000 | 0.000 | declined |  |
| 365 | common | Reef_Check | 1932 | 28 | 0.000 | 0.000 | 0.000 | 0.000 | declined |  |
| 365 | common | mixed | 0 | 0 |  |  |  |  | no rows |  |

### Blocked jackknife per programme (report only; the group jackknife decides)

Overlap blocks from derived.json R14:overlap_blocks. The engine saves only the ALL line at the nowcast (verdict.json); every other line is computed here from the saved rows, by the engine's rule.

| lead | rows_basis | stratum_value | n_rows | n_groups | n_blocks | mean | se | group_se | flag | engine_record | matches_engine |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | all | ALL | 2312 | 37 | 35 | 5.311 | 1.702 | 1.650 |  | verdict.json blocked_jackknife | yes |
| 0 | all | AGRRA | 1 | 1 | 1 | 4.570 |  |  |  | not saved by the engine |  |
| 0 | all | Donner | 0 | 0 | 0 |  |  |  |  | not saved by the engine |  |
| 0 | all | FRRP | 190 | 1 | 1 | 3.252 |  |  |  | not saved by the engine |  |
| 0 | all | McClanahan | 189 | 15 | 15 | 17.162 | 3.037 | 3.037 |  | not saved by the engine |  |
| 0 | all | Reef_Check | 1932 | 28 | 26 | -0.557 | 0.347 | 0.338 |  | not saved by the engine |  |
| 0 | all | mixed | 0 | 0 | 0 |  |  |  |  | not saved by the engine |  |
| 0 | common | ALL | 2312 | 37 | 35 | 5.311 | 1.702 | 1.650 |  | not saved by the engine |  |
| 0 | common | AGRRA | 1 | 1 | 1 | 4.570 |  |  |  | not saved by the engine |  |
| 0 | common | Donner | 0 | 0 | 0 |  |  |  |  | not saved by the engine |  |
| 0 | common | FRRP | 190 | 1 | 1 | 3.252 |  |  |  | not saved by the engine |  |
| 0 | common | McClanahan | 189 | 15 | 15 | 17.162 | 3.037 | 3.037 |  | not saved by the engine |  |
| 0 | common | Reef_Check | 1932 | 28 | 26 | -0.557 | 0.347 | 0.338 |  | not saved by the engine |  |
| 0 | common | mixed | 0 | 0 | 0 |  |  |  |  | not saved by the engine |  |
| 183 | common | ALL | 2312 | 37 | 35 | 1.836 | 0.874 | 0.829 |  | not saved by the engine |  |
| 183 | common | AGRRA | 1 | 1 | 1 | 1.475 |  |  |  | not saved by the engine |  |
| 183 | common | Donner | 0 | 0 | 0 |  |  |  |  | not saved by the engine |  |
| 183 | common | FRRP | 190 | 1 | 1 | 3.591 |  |  |  | not saved by the engine |  |
| 183 | common | McClanahan | 189 | 15 | 15 | 4.611 | 1.831 | 1.831 |  | not saved by the engine |  |
| 183 | common | Reef_Check | 1932 | 28 | 26 | -0.219 | 0.241 | 0.225 |  | not saved by the engine |  |
| 183 | common | mixed | 0 | 0 | 0 |  |  |  |  | not saved by the engine |  |
| 365 | common | ALL | 2312 | 37 | 35 | 0.000 | 0.000 | 0.000 |  | not saved by the engine |  |
| 365 | common | AGRRA | 1 | 1 | 1 | 0.000 |  |  |  | not saved by the engine |  |
| 365 | common | Donner | 0 | 0 | 0 |  |  |  |  | not saved by the engine |  |
| 365 | common | FRRP | 190 | 1 | 1 | 0.000 |  |  |  | not saved by the engine |  |
| 365 | common | McClanahan | 189 | 15 | 15 | 0.000 | 0.000 | 0.000 |  | not saved by the engine |  |
| 365 | common | Reef_Check | 1932 | 28 | 26 | 0.000 | 0.000 | 0.000 |  | not saved by the engine |  |
| 365 | common | mixed | 0 | 0 | 0 |  |  |  |  | not saved by the engine |  |

## 2. By magnitude (a target-defined diagnostic, not a headline)

Edges from the donor rows at each lead's fit cut (train rows only):

| lead | fit_cut | donor_rows | donor_rows_engine | donor_median | positive_donor_rows | pos_q25 | pos_q50 | pos_q75 | q75_all_donor_labels | q75_positive_donor_labels |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 735963 | 11338 | 11338 | 1.000 | 6776 | 1.916 | 7.255 | 23.957 | 10.000 | 23.957 |
| 183 | 735781 | 10838 | 10838 | 1.000 | 6424 | 1.750 | 6.670 | 22.220 | 9.735 | 22.220 |
| 365 | 735599 | 10567 | 10567 | 1.000 | 6330 | 1.760 | 6.685 | 22.500 | 10.000 | 22.500 |

### Lead 0, adopted `arm__arcsine_corrector_gls`, pinned `arm__arcsine_corrector_gls`

| stratum_value | bin | column | n | mean_y | mean_pred | mae | mae_predict_zero | mae_donor_median | n_only |
|---|---|---|---|---|---|---|---|---|---|
| ALL | B0 zero | arm__arcsine_corrector_gls | 1288 | 0.000 | 1.393 | 1.393 | 0.000 | 1.000 | no |
| ALL | B1 (0, q25] | arm__arcsine_corrector_gls | 278 | 0.785 | 2.552 | 2.248 | 0.785 | 0.454 | no |
| ALL | B2 (q25, q50] | arm__arcsine_corrector_gls | 262 | 4.174 | 5.018 | 4.571 | 4.174 | 3.174 | no |
| ALL | B3 (q50, q75] | arm__arcsine_corrector_gls | 245 | 14.123 | 7.678 | 8.396 | 14.123 | 13.123 | no |
| ALL | B4 (q75, max] | arm__arcsine_corrector_gls | 239 | 58.389 | 17.772 | 41.052 | 58.389 | 57.389 | no |
| AGRRA | B0 zero | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| AGRRA | B1 (0, q25] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| AGRRA | B2 (q25, q50] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| AGRRA | B3 (q50, q75] | arm__arcsine_corrector_gls | 1 |  |  |  |  |  | yes |
| AGRRA | B4 (q75, max] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| Donner | B0 zero | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| Donner | B1 (0, q25] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| Donner | B2 (q25, q50] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| Donner | B3 (q50, q75] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| Donner | B4 (q75, max] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| FRRP | B0 zero | arm__arcsine_corrector_gls | 16 | 0.000 | 10.556 | 10.556 | 0.000 | 1.000 | no |
| FRRP | B1 (0, q25] | arm__arcsine_corrector_gls | 11 | 1.231 | 8.151 | 6.956 | 1.231 | 0.365 | no |
| FRRP | B2 (q25, q50] | arm__arcsine_corrector_gls | 46 | 4.596 | 9.876 | 5.749 | 4.596 | 3.596 | no |
| FRRP | B3 (q50, q75] | arm__arcsine_corrector_gls | 102 | 14.733 | 10.503 | 5.859 | 14.733 | 13.733 | no |
| FRRP | B4 (q75, max] | arm__arcsine_corrector_gls | 15 | 33.467 | 10.278 | 23.189 | 33.467 | 32.467 | no |
| McClanahan | B0 zero | arm__arcsine_corrector_gls | 2 | 0.000 | 1.194 | 1.194 | 0.000 | 1.000 | no |
| McClanahan | B1 (0, q25] | arm__arcsine_corrector_gls | 1 | 1.720 | 1.939 | 0.219 | 1.720 | 0.720 | no |
| McClanahan | B2 (q25, q50] | arm__arcsine_corrector_gls | 14 | 4.735 | 5.389 | 4.214 | 4.735 | 3.735 | no |
| McClanahan | B3 (q50, q75] | arm__arcsine_corrector_gls | 22 | 16.204 | 15.881 | 8.652 | 16.204 | 15.204 | no |
| McClanahan | B4 (q75, max] | arm__arcsine_corrector_gls | 150 | 66.242 | 24.440 | 42.496 | 66.242 | 65.242 | no |
| Reef_Check | B0 zero | arm__arcsine_corrector_gls | 1270 | 0.000 | 1.278 | 1.278 | 0.000 | 1.000 | no |
| Reef_Check | B1 (0, q25] | arm__arcsine_corrector_gls | 266 | 0.763 | 2.322 | 2.061 | 0.763 | 0.457 | no |
| Reef_Check | B2 (q25, q50] | arm__arcsine_corrector_gls | 202 | 4.039 | 3.886 | 4.328 | 4.039 | 3.039 | no |
| Reef_Check | B3 (q50, q75] | arm__arcsine_corrector_gls | 120 | 13.248 | 3.790 | 10.528 | 13.248 | 12.248 | no |
| Reef_Check | B4 (q75, max] | arm__arcsine_corrector_gls | 74 | 47.521 | 5.775 | 41.747 | 47.521 | 46.521 | no |
| mixed | B0 zero | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| mixed | B1 (0, q25] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| mixed | B2 (q25, q50] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| mixed | B3 (q50, q75] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| mixed | B4 (q75, max] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |

### Lead 183, adopted `arm__arcsine_corrector_gls`, pinned `arm__arcsine_corrector_gls`

| stratum_value | bin | column | n | mean_y | mean_pred | mae | mae_predict_zero | mae_donor_median | n_only |
|---|---|---|---|---|---|---|---|---|---|
| ALL | B0 zero | arm__arcsine_corrector_gls | 1288 | 0.000 | 1.211 | 1.211 | 0.000 | 1.000 | no |
| ALL | B1 (0, q25] | arm__arcsine_corrector_gls | 277 | 0.781 | 1.997 | 1.719 | 0.781 | 0.453 | no |
| ALL | B2 (q25, q50] | arm__arcsine_corrector_gls | 249 | 4.009 | 2.871 | 3.158 | 4.009 | 3.009 | no |
| ALL | B3 (q50, q75] | arm__arcsine_corrector_gls | 243 | 13.121 | 4.857 | 8.659 | 13.121 | 12.121 | no |
| ALL | B4 (q75, max] | arm__arcsine_corrector_gls | 255 | 56.172 | 5.592 | 50.581 | 56.172 | 55.172 | no |
| AGRRA | B0 zero | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| AGRRA | B1 (0, q25] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| AGRRA | B2 (q25, q50] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| AGRRA | B3 (q50, q75] | arm__arcsine_corrector_gls | 1 |  |  |  |  |  | yes |
| AGRRA | B4 (q75, max] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| Donner | B0 zero | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| Donner | B1 (0, q25] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| Donner | B2 (q25, q50] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| Donner | B3 (q50, q75] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| Donner | B4 (q75, max] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| FRRP | B0 zero | arm__arcsine_corrector_gls | 16 | 0.000 | 7.854 | 7.854 | 0.000 | 1.000 | no |
| FRRP | B1 (0, q25] | arm__arcsine_corrector_gls | 11 | 1.231 | 5.525 | 4.634 | 1.231 | 0.365 | no |
| FRRP | B2 (q25, q50] | arm__arcsine_corrector_gls | 43 | 4.437 | 6.521 | 3.055 | 4.437 | 3.437 | no |
| FRRP | B3 (q50, q75] | arm__arcsine_corrector_gls | 98 | 13.900 | 8.303 | 6.170 | 13.900 | 12.900 | no |
| FRRP | B4 (q75, max] | arm__arcsine_corrector_gls | 22 | 30.146 | 8.411 | 21.735 | 30.146 | 29.146 | no |
| McClanahan | B0 zero | arm__arcsine_corrector_gls | 2 | 0.000 | 0.439 | 0.439 | 0.000 | 1.000 | no |
| McClanahan | B1 (0, q25] | arm__arcsine_corrector_gls | 1 | 1.720 | 0.656 | 1.064 | 1.720 | 0.720 | no |
| McClanahan | B2 (q25, q50] | arm__arcsine_corrector_gls | 11 | 4.108 | 6.213 | 5.467 | 4.108 | 3.108 | no |
| McClanahan | B3 (q50, q75] | arm__arcsine_corrector_gls | 21 | 13.513 | 7.828 | 7.203 | 13.513 | 12.513 | no |
| McClanahan | B4 (q75, max] | arm__arcsine_corrector_gls | 154 | 65.131 | 7.249 | 57.882 | 65.131 | 64.131 | no |
| Reef_Check | B0 zero | arm__arcsine_corrector_gls | 1270 | 0.000 | 1.129 | 1.129 | 0.000 | 1.000 | no |
| Reef_Check | B1 (0, q25] | arm__arcsine_corrector_gls | 265 | 0.759 | 1.855 | 1.601 | 0.759 | 0.455 | no |
| Reef_Check | B2 (q25, q50] | arm__arcsine_corrector_gls | 195 | 3.909 | 1.878 | 3.050 | 3.909 | 2.909 | no |
| Reef_Check | B3 (q50, q75] | arm__arcsine_corrector_gls | 123 | 12.450 | 1.623 | 10.890 | 12.450 | 11.450 | no |
| Reef_Check | B4 (q75, max] | arm__arcsine_corrector_gls | 79 | 45.957 | 1.575 | 44.381 | 45.957 | 44.957 | no |
| mixed | B0 zero | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| mixed | B1 (0, q25] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| mixed | B2 (q25, q50] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| mixed | B3 (q50, q75] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| mixed | B4 (q75, max] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |

### Lead 365, adopted `base__donor_median`, pinned `arm__arcsine_corrector_gls`

| stratum_value | bin | column | n | mean_y | mean_pred | mae | mae_predict_zero | mae_donor_median | n_only |
|---|---|---|---|---|---|---|---|---|---|
| ALL | B0 zero | arm__arcsine_corrector_gls | 1288 | 0.000 | 1.518 | 1.518 | 0.000 | 1.000 | no |
| ALL | B0 zero | base__donor_median | 1288 | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 | no |
| ALL | B1 (0, q25] | arm__arcsine_corrector_gls | 277 | 0.781 | 3.063 | 2.859 | 0.781 | 0.453 | no |
| ALL | B1 (0, q25] | base__donor_median | 277 | 0.781 | 1.000 | 0.453 | 0.781 | 0.453 | no |
| ALL | B2 (q25, q50] | arm__arcsine_corrector_gls | 249 | 4.009 | 3.931 | 4.091 | 4.009 | 3.009 | no |
| ALL | B2 (q25, q50] | base__donor_median | 249 | 4.009 | 1.000 | 3.009 | 4.009 | 3.009 | no |
| ALL | B3 (q50, q75] | arm__arcsine_corrector_gls | 247 | 13.272 | 4.666 | 9.121 | 13.272 | 12.272 | no |
| ALL | B3 (q50, q75] | base__donor_median | 247 | 13.272 | 1.000 | 12.272 | 13.272 | 12.272 | no |
| ALL | B4 (q75, max] | arm__arcsine_corrector_gls | 251 | 56.709 | 4.407 | 52.302 | 56.709 | 55.709 | no |
| ALL | B4 (q75, max] | base__donor_median | 251 | 56.709 | 1.000 | 55.709 | 56.709 | 55.709 | no |
| AGRRA | B0 zero | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| AGRRA | B0 zero | base__donor_median | 0 |  |  |  |  |  | yes |
| AGRRA | B1 (0, q25] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| AGRRA | B1 (0, q25] | base__donor_median | 0 |  |  |  |  |  | yes |
| AGRRA | B2 (q25, q50] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| AGRRA | B2 (q25, q50] | base__donor_median | 0 |  |  |  |  |  | yes |
| AGRRA | B3 (q50, q75] | arm__arcsine_corrector_gls | 1 |  |  |  |  |  | yes |
| AGRRA | B3 (q50, q75] | base__donor_median | 1 |  |  |  |  |  | yes |
| AGRRA | B4 (q75, max] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| AGRRA | B4 (q75, max] | base__donor_median | 0 |  |  |  |  |  | yes |
| Donner | B0 zero | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| Donner | B0 zero | base__donor_median | 0 |  |  |  |  |  | yes |
| Donner | B1 (0, q25] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| Donner | B1 (0, q25] | base__donor_median | 0 |  |  |  |  |  | yes |
| Donner | B2 (q25, q50] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| Donner | B2 (q25, q50] | base__donor_median | 0 |  |  |  |  |  | yes |
| Donner | B3 (q50, q75] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| Donner | B3 (q50, q75] | base__donor_median | 0 |  |  |  |  |  | yes |
| Donner | B4 (q75, max] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| Donner | B4 (q75, max] | base__donor_median | 0 |  |  |  |  |  | yes |
| FRRP | B0 zero | arm__arcsine_corrector_gls | 16 | 0.000 | 6.737 | 6.737 | 0.000 | 1.000 | no |
| FRRP | B0 zero | base__donor_median | 16 | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 | no |
| FRRP | B1 (0, q25] | arm__arcsine_corrector_gls | 11 | 1.231 | 4.746 | 3.515 | 1.231 | 0.365 | no |
| FRRP | B1 (0, q25] | base__donor_median | 11 | 1.231 | 1.000 | 0.365 | 1.231 | 0.365 | no |
| FRRP | B2 (q25, q50] | arm__arcsine_corrector_gls | 43 | 4.437 | 7.699 | 4.034 | 4.437 | 3.437 | no |
| FRRP | B2 (q25, q50] | base__donor_median | 43 | 4.437 | 1.000 | 3.437 | 4.437 | 3.437 | no |
| FRRP | B3 (q50, q75] | arm__arcsine_corrector_gls | 99 | 13.986 | 7.425 | 7.020 | 13.986 | 12.986 | no |
| FRRP | B3 (q50, q75] | base__donor_median | 99 | 13.986 | 1.000 | 12.986 | 13.986 | 12.986 | no |
| FRRP | B4 (q75, max] | arm__arcsine_corrector_gls | 21 | 30.517 | 7.709 | 22.808 | 30.517 | 29.517 | no |
| FRRP | B4 (q75, max] | base__donor_median | 21 | 30.517 | 1.000 | 29.517 | 30.517 | 29.517 | no |
| McClanahan | B0 zero | arm__arcsine_corrector_gls | 2 | 0.000 | 0.522 | 0.522 | 0.000 | 1.000 | no |
| McClanahan | B0 zero | base__donor_median | 2 | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 | no |
| McClanahan | B1 (0, q25] | arm__arcsine_corrector_gls | 1 | 1.720 | 0.889 | 0.831 | 1.720 | 0.720 | no |
| McClanahan | B1 (0, q25] | base__donor_median | 1 | 1.720 | 1.000 | 0.720 | 1.720 | 0.720 | no |
| McClanahan | B2 (q25, q50] | arm__arcsine_corrector_gls | 11 | 4.108 | 3.027 | 2.821 | 4.108 | 3.108 | no |
| McClanahan | B2 (q25, q50] | base__donor_median | 11 | 4.108 | 1.000 | 3.108 | 4.108 | 3.108 | no |
| McClanahan | B3 (q50, q75] | arm__arcsine_corrector_gls | 21 | 13.513 | 2.706 | 11.229 | 13.513 | 12.513 | no |
| McClanahan | B3 (q50, q75] | base__donor_median | 21 | 13.513 | 1.000 | 12.513 | 13.513 | 12.513 | no |
| McClanahan | B4 (q75, max] | arm__arcsine_corrector_gls | 154 | 65.131 | 5.088 | 60.043 | 65.131 | 64.131 | no |
| McClanahan | B4 (q75, max] | base__donor_median | 154 | 65.131 | 1.000 | 64.131 | 65.131 | 64.131 | no |
| Reef_Check | B0 zero | arm__arcsine_corrector_gls | 1270 | 0.000 | 1.453 | 1.453 | 0.000 | 1.000 | no |
| Reef_Check | B0 zero | base__donor_median | 1270 | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 | no |
| Reef_Check | B1 (0, q25] | arm__arcsine_corrector_gls | 265 | 0.759 | 3.002 | 2.840 | 0.759 | 0.455 | no |
| Reef_Check | B1 (0, q25] | base__donor_median | 265 | 0.759 | 1.000 | 0.455 | 0.759 | 0.455 | no |
| Reef_Check | B2 (q25, q50] | arm__arcsine_corrector_gls | 195 | 3.909 | 3.151 | 4.175 | 3.909 | 2.909 | no |
| Reef_Check | B2 (q25, q50] | base__donor_median | 195 | 3.909 | 1.000 | 2.909 | 3.909 | 2.909 | no |
| Reef_Check | B3 (q50, q75] | arm__arcsine_corrector_gls | 126 | 12.689 | 2.850 | 10.416 | 12.689 | 11.689 | no |
| Reef_Check | B3 (q50, q75] | base__donor_median | 126 | 12.689 | 1.000 | 11.689 | 12.689 | 11.689 | no |
| Reef_Check | B4 (q75, max] | arm__arcsine_corrector_gls | 76 | 46.883 | 2.116 | 44.767 | 46.883 | 45.883 | no |
| Reef_Check | B4 (q75, max] | base__donor_median | 76 | 46.883 | 1.000 | 45.883 | 46.883 | 45.883 | no |
| mixed | B0 zero | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| mixed | B0 zero | base__donor_median | 0 |  |  |  |  |  | yes |
| mixed | B1 (0, q25] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| mixed | B1 (0, q25] | base__donor_median | 0 |  |  |  |  |  | yes |
| mixed | B2 (q25, q50] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| mixed | B2 (q25, q50] | base__donor_median | 0 |  |  |  |  |  | yes |
| mixed | B3 (q50, q75] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| mixed | B3 (q50, q75] | base__donor_median | 0 |  |  |  |  |  | yes |
| mixed | B4 (q75, max] | arm__arcsine_corrector_gls | 0 |  |  |  |  |  | yes |
| mixed | B4 (q75, max] | base__donor_median | 0 |  |  |  |  |  | yes |

## 3. Flattening guard (report only, never a choice)

Rows with label at or above the edge; every arm and baseline in flattening_guard.csv. Two edges are printed; the owner chose (b) as the default (owner ruling X4, 2026-10-20):

- (a) q75 of all donor-row labels -- printed beside, not the default (owner ruling X4).
- (b) q75 of positive donor-row labels -- DEFAULT (owner ruling X4).

### Lead 0

| edge_rule | is_default | edge | column | n | observed_mean | mean_pred | mean_pred_minus_observed |
|---|---|---|---|---|---|---|---|
| q75_all_donor_labels | no | 10.000 | arm__arcsine_corrector_gls | 434 | 39.147 | 13.298 | -25.850 |
| q75_all_donor_labels | no | 10.000 | arm__arcsine_corrector_unweighted | 434 | 39.147 | 18.955 | -20.192 |
| q75_all_donor_labels | no | 10.000 | placebo__arcsine_placebo_corrector_gls | 434 | 39.147 | 13.140 | -26.008 |
| q75_all_donor_labels | no | 10.000 | placebo__arcsine_placebo_corrector_unweighted | 434 | 39.147 | 18.883 | -20.265 |
| q75_all_donor_labels | no | 10.000 | arm__arcsine_plain_gls | 434 | 39.147 | 13.093 | -26.054 |
| q75_all_donor_labels | no | 10.000 | arm__arcsine_plain_unweighted | 434 | 39.147 | 18.893 | -20.254 |
| q75_all_donor_labels | no | 10.000 | arm__arcsine_trees_off_unweighted | 434 | 39.147 | 8.386 | -30.762 |
| q75_all_donor_labels | no | 10.000 | arm__identity_corrector_gls | 434 | 39.147 | 16.884 | -22.263 |
| q75_all_donor_labels | no | 10.000 | arm__identity_corrector_unweighted | 434 | 39.147 | 21.712 | -17.436 |
| q75_all_donor_labels | no | 10.000 | placebo__identity_placebo_corrector_gls | 434 | 39.147 | 16.732 | -22.416 |
| q75_all_donor_labels | no | 10.000 | placebo__identity_placebo_corrector_unweighted | 434 | 39.147 | 21.639 | -17.508 |
| q75_all_donor_labels | no | 10.000 | arm__identity_plain_gls | 434 | 39.147 | 16.688 | -22.459 |
| q75_all_donor_labels | no | 10.000 | arm__identity_plain_unweighted | 434 | 39.147 | 21.651 | -17.497 |
| q75_all_donor_labels | no | 10.000 | arm__identity_trees_off_unweighted | 434 | 39.147 | 12.191 | -26.957 |
| q75_all_donor_labels | no | 10.000 | arm__log_c_corrector_gls | 434 | 39.147 | 7.326 | -31.821 |
| q75_all_donor_labels | no | 10.000 | arm__log_c_corrector_unweighted | 434 | 39.147 | 11.811 | -27.336 |
| q75_all_donor_labels | no | 10.000 | placebo__log_c_placebo_corrector_gls | 434 | 39.147 | 7.178 | -31.969 |
| q75_all_donor_labels | no | 10.000 | placebo__log_c_placebo_corrector_unweighted | 434 | 39.147 | 11.743 | -27.405 |
| q75_all_donor_labels | no | 10.000 | arm__log_c_plain_gls | 434 | 39.147 | 7.196 | -31.952 |
| q75_all_donor_labels | no | 10.000 | arm__log_c_plain_unweighted | 434 | 39.147 | 11.755 | -27.392 |
| q75_all_donor_labels | no | 10.000 | arm__log_c_trees_off_unweighted | 434 | 39.147 | 4.398 | -34.749 |
| q75_all_donor_labels | no | 10.000 | base__donor_median | 434 | 39.147 | 1.000 | -38.147 |
| q75_all_donor_labels | no | 10.000 | base__predict_zero | 434 | 39.147 | 0.000 | -39.147 |
| q75_positive_donor_labels | yes | 23.957 | arm__arcsine_corrector_gls | 239 | 58.389 | 17.772 | -40.616 |
| q75_positive_donor_labels | yes | 23.957 | arm__arcsine_corrector_unweighted | 239 | 58.389 | 27.146 | -31.243 |
| q75_positive_donor_labels | yes | 23.957 | placebo__arcsine_placebo_corrector_gls | 239 | 58.389 | 17.498 | -40.890 |
| q75_positive_donor_labels | yes | 23.957 | placebo__arcsine_placebo_corrector_unweighted | 239 | 58.389 | 27.026 | -31.362 |
| q75_positive_donor_labels | yes | 23.957 | arm__arcsine_plain_gls | 239 | 58.389 | 17.411 | -40.977 |
| q75_positive_donor_labels | yes | 23.957 | arm__arcsine_plain_unweighted | 239 | 58.389 | 27.036 | -31.353 |
| q75_positive_donor_labels | yes | 23.957 | arm__arcsine_trees_off_unweighted | 239 | 58.389 | 8.706 | -49.682 |
| q75_positive_donor_labels | yes | 23.957 | arm__identity_corrector_gls | 239 | 58.389 | 21.913 | -36.476 |
| q75_positive_donor_labels | yes | 23.957 | arm__identity_corrector_unweighted | 239 | 58.389 | 29.762 | -28.626 |
| q75_positive_donor_labels | yes | 23.957 | placebo__identity_placebo_corrector_gls | 239 | 58.389 | 21.654 | -36.735 |
| q75_positive_donor_labels | yes | 23.957 | placebo__identity_placebo_corrector_unweighted | 239 | 58.389 | 29.643 | -28.746 |
| q75_positive_donor_labels | yes | 23.957 | arm__identity_plain_gls | 239 | 58.389 | 21.571 | -36.818 |
| q75_positive_donor_labels | yes | 23.957 | arm__identity_plain_unweighted | 239 | 58.389 | 29.650 | -28.739 |
| q75_positive_donor_labels | yes | 23.957 | arm__identity_trees_off_unweighted | 239 | 58.389 | 13.350 | -45.039 |
| q75_positive_donor_labels | yes | 23.957 | arm__log_c_corrector_gls | 239 | 58.389 | 9.774 | -48.615 |
| q75_positive_donor_labels | yes | 23.957 | arm__log_c_corrector_unweighted | 239 | 58.389 | 17.470 | -40.919 |
| q75_positive_donor_labels | yes | 23.957 | placebo__log_c_placebo_corrector_gls | 239 | 58.389 | 9.511 | -48.878 |
| q75_positive_donor_labels | yes | 23.957 | placebo__log_c_placebo_corrector_unweighted | 239 | 58.389 | 17.340 | -41.049 |
| q75_positive_donor_labels | yes | 23.957 | arm__log_c_plain_gls | 239 | 58.389 | 9.536 | -48.853 |
| q75_positive_donor_labels | yes | 23.957 | arm__log_c_plain_unweighted | 239 | 58.389 | 17.359 | -41.030 |
| q75_positive_donor_labels | yes | 23.957 | arm__log_c_trees_off_unweighted | 239 | 58.389 | 4.053 | -54.336 |
| q75_positive_donor_labels | yes | 23.957 | base__donor_median | 239 | 58.389 | 1.000 | -57.389 |
| q75_positive_donor_labels | yes | 23.957 | base__predict_zero | 239 | 58.389 | 0.000 | -58.389 |

### Lead 183

| edge_rule | is_default | edge | column | n | observed_mean | mean_pred | mean_pred_minus_observed |
|---|---|---|---|---|---|---|---|
| q75_all_donor_labels | no | 9.735 | arm__arcsine_corrector_gls | 434 | 39.147 | 5.351 | -33.796 |
| q75_all_donor_labels | no | 9.735 | arm__arcsine_trees_off_unweighted | 434 | 39.147 | 6.083 | -33.065 |
| q75_all_donor_labels | no | 9.735 | arm__identity_trees_off_unweighted | 434 | 39.147 | 9.670 | -29.477 |
| q75_all_donor_labels | no | 9.735 | base__damped_persistence | 126 | 33.042 | 4.951 | -28.091 |
| q75_all_donor_labels | no | 9.735 | base__donor_median | 434 | 39.147 | 1.000 | -38.147 |
| q75_all_donor_labels | no | 9.735 | base__persistence | 126 | 33.042 | 8.212 | -24.830 |
| q75_all_donor_labels | no | 9.735 | base__predict_zero | 434 | 39.147 | 0.000 | -39.147 |
| q75_positive_donor_labels | yes | 22.220 | arm__arcsine_corrector_gls | 257 | 55.908 | 5.606 | -50.302 |
| q75_positive_donor_labels | yes | 22.220 | arm__arcsine_trees_off_unweighted | 257 | 55.908 | 6.280 | -49.628 |
| q75_positive_donor_labels | yes | 22.220 | arm__identity_trees_off_unweighted | 257 | 55.908 | 10.626 | -45.282 |
| q75_positive_donor_labels | yes | 22.220 | base__damped_persistence | 66 | 49.844 | 4.249 | -45.595 |
| q75_positive_donor_labels | yes | 22.220 | base__donor_median | 257 | 55.908 | 1.000 | -54.908 |
| q75_positive_donor_labels | yes | 22.220 | base__persistence | 66 | 49.844 | 8.714 | -41.130 |
| q75_positive_donor_labels | yes | 22.220 | base__predict_zero | 257 | 55.908 | 0.000 | -55.908 |

### Lead 365

| edge_rule | is_default | edge | column | n | observed_mean | mean_pred | mean_pred_minus_observed |
|---|---|---|---|---|---|---|---|
| q75_all_donor_labels | no | 10.000 | arm__arcsine_corrector_gls | 434 | 39.147 | 4.601 | -34.547 |
| q75_all_donor_labels | no | 10.000 | placebo__arcsine_placebo_corrector_gls | 434 | 39.147 | 4.583 | -34.564 |
| q75_all_donor_labels | no | 10.000 | arm__arcsine_trees_off_unweighted | 434 | 39.147 | 5.738 | -33.410 |
| q75_all_donor_labels | no | 10.000 | arm__identity_trees_off_unweighted | 434 | 39.147 | 9.268 | -29.880 |
| q75_all_donor_labels | no | 10.000 | base__damped_persistence | 122 | 33.175 | 4.566 | -28.609 |
| q75_all_donor_labels | no | 10.000 | base__donor_median | 434 | 39.147 | 1.000 | -38.147 |
| q75_all_donor_labels | no | 10.000 | base__persistence | 122 | 33.175 | 5.220 | -27.955 |
| q75_all_donor_labels | no | 10.000 | base__predict_zero | 434 | 39.147 | 0.000 | -39.147 |
| q75_positive_donor_labels | yes | 22.500 | arm__arcsine_corrector_gls | 254 | 56.305 | 4.357 | -51.948 |
| q75_positive_donor_labels | yes | 22.500 | placebo__arcsine_placebo_corrector_gls | 254 | 56.305 | 4.373 | -51.932 |
| q75_positive_donor_labels | yes | 22.500 | arm__arcsine_trees_off_unweighted | 254 | 56.305 | 6.037 | -50.269 |
| q75_positive_donor_labels | yes | 22.500 | arm__identity_trees_off_unweighted | 254 | 56.305 | 10.403 | -45.902 |
| q75_positive_donor_labels | yes | 22.500 | base__damped_persistence | 64 | 50.171 | 3.644 | -46.527 |
| q75_positive_donor_labels | yes | 22.500 | base__donor_median | 254 | 56.305 | 1.000 | -55.305 |
| q75_positive_donor_labels | yes | 22.500 | base__persistence | 64 | 50.171 | 5.402 | -44.769 |
| q75_positive_donor_labels | yes | 22.500 | base__predict_zero | 254 | 56.305 | 0.000 | -56.305 |

## 4. Pooled second (pooled (mixes programmes)): pooled, macro over ecoregions, per test year

No claim is made from a pooled margin.

### Lead 0

| column | line | year | n | n_groups | mae | mae_predict_zero | mae_donor_median |
|---|---|---|---|---|---|---|---|
| arm__arcsine_corrector_gls | year | 2016.000 | 873 | 36 | 12.406 | 17.081 | 16.826 |
| arm__arcsine_corrector_gls | year | 2017.000 | 565 | 24 | 3.569 | 2.808 | 3.231 |
| arm__arcsine_corrector_gls | year | 2018.000 | 443 | 15 | 1.280 | 0.844 | 1.507 |
| arm__arcsine_corrector_gls | year | 2019.000 | 431 | 18 | 4.806 | 4.304 | 4.627 |
| arm__arcsine_corrector_gls | pooled |  | 2312 | 37 | 6.698 | 8.100 | 8.294 |
| arm__arcsine_corrector_gls | macro_over_groups |  | 2312 | 37 | 14.635 | 19.991 | 19.842 |
| arm__arcsine_trees_off_unweighted | year | 2016.000 | 873 | 36 | 14.736 | 17.081 | 16.826 |
| arm__arcsine_trees_off_unweighted | year | 2017.000 | 565 | 24 | 3.501 | 2.808 | 3.231 |
| arm__arcsine_trees_off_unweighted | year | 2018.000 | 443 | 15 | 1.293 | 0.844 | 1.507 |
| arm__arcsine_trees_off_unweighted | year | 2019.000 | 431 | 18 | 4.657 | 4.304 | 4.627 |
| arm__arcsine_trees_off_unweighted | pooled |  | 2312 | 37 | 7.536 | 8.100 | 8.294 |
| arm__arcsine_trees_off_unweighted | macro_over_groups |  | 2312 | 37 | 17.901 | 19.991 | 19.842 |
| arm__identity_trees_off_unweighted | year | 2016.000 | 873 | 36 | 14.538 | 17.081 | 16.826 |
| arm__identity_trees_off_unweighted | year | 2017.000 | 565 | 24 | 4.540 | 2.808 | 3.231 |
| arm__identity_trees_off_unweighted | year | 2018.000 | 443 | 15 | 1.998 | 0.844 | 1.507 |
| arm__identity_trees_off_unweighted | year | 2019.000 | 431 | 18 | 5.325 | 4.304 | 4.627 |
| arm__identity_trees_off_unweighted | pooled |  | 2312 | 37 | 7.975 | 8.100 | 8.294 |
| arm__identity_trees_off_unweighted | macro_over_groups |  | 2312 | 37 | 17.094 | 19.991 | 19.842 |
| arm__log_c_trees_off_unweighted | year | 2016.000 | 873 | 36 | 15.343 | 17.081 | 16.826 |
| arm__log_c_trees_off_unweighted | year | 2017.000 | 565 | 24 | 2.920 | 2.808 | 3.231 |
| arm__log_c_trees_off_unweighted | year | 2018.000 | 443 | 15 | 1.014 | 0.844 | 1.507 |
| arm__log_c_trees_off_unweighted | year | 2019.000 | 431 | 18 | 4.377 | 4.304 | 4.627 |
| arm__log_c_trees_off_unweighted | pooled |  | 2312 | 37 | 7.517 | 8.100 | 8.294 |
| arm__log_c_trees_off_unweighted | macro_over_groups |  | 2312 | 37 | 18.949 | 19.991 | 19.842 |
| base__donor_median | year | 2016.000 | 873 | 36 | 16.826 | 17.081 | 16.826 |
| base__donor_median | year | 2017.000 | 565 | 24 | 3.231 | 2.808 | 3.231 |
| base__donor_median | year | 2018.000 | 443 | 15 | 1.507 | 0.844 | 1.507 |
| base__donor_median | year | 2019.000 | 431 | 18 | 4.627 | 4.304 | 4.627 |
| base__donor_median | pooled |  | 2312 | 37 | 8.294 | 8.100 | 8.294 |
| base__donor_median | macro_over_groups |  | 2312 | 37 | 19.842 | 19.991 | 19.842 |
| base__predict_zero | year | 2016.000 | 873 | 36 | 17.081 | 17.081 | 16.826 |
| base__predict_zero | year | 2017.000 | 565 | 24 | 2.808 | 2.808 | 3.231 |
| base__predict_zero | year | 2018.000 | 443 | 15 | 0.844 | 0.844 | 1.507 |
| base__predict_zero | year | 2019.000 | 431 | 18 | 4.304 | 4.304 | 4.627 |
| base__predict_zero | pooled |  | 2312 | 37 | 8.100 | 8.100 | 8.294 |
| base__predict_zero | macro_over_groups |  | 2312 | 37 | 19.991 | 19.991 | 19.842 |

### Lead 183

| column | line | year | n | n_groups | mae | mae_predict_zero | mae_donor_median |
|---|---|---|---|---|---|---|---|
| arm__arcsine_corrector_gls | year | 2016.000 | 873 | 36 | 14.953 | 17.081 | 16.826 |
| arm__arcsine_corrector_gls | year | 2017.000 | 565 | 24 | 3.465 | 2.808 | 3.231 |
| arm__arcsine_corrector_gls | year | 2018.000 | 443 | 15 | 1.488 | 0.844 | 1.507 |
| arm__arcsine_corrector_gls | year | 2019.000 | 431 | 18 | 4.996 | 4.304 | 4.627 |
| arm__arcsine_corrector_gls | pooled |  | 2312 | 37 | 7.710 | 8.100 | 8.294 |
| arm__arcsine_corrector_gls | macro_over_groups |  | 2312 | 37 | 18.095 | 19.991 | 19.842 |
| arm__arcsine_trees_off_unweighted | year | 2016.000 | 873 | 36 | 14.778 | 17.081 | 16.826 |
| arm__arcsine_trees_off_unweighted | year | 2017.000 | 565 | 24 | 3.663 | 2.808 | 3.231 |
| arm__arcsine_trees_off_unweighted | year | 2018.000 | 443 | 15 | 1.756 | 0.844 | 1.507 |
| arm__arcsine_trees_off_unweighted | year | 2019.000 | 431 | 18 | 4.927 | 4.304 | 4.627 |
| arm__arcsine_trees_off_unweighted | pooled |  | 2312 | 37 | 7.730 | 8.100 | 8.294 |
| arm__arcsine_trees_off_unweighted | macro_over_groups |  | 2312 | 37 | 19.011 | 19.991 | 19.842 |
| arm__identity_trees_off_unweighted | year | 2016.000 | 873 | 36 | 14.227 | 17.081 | 16.826 |
| arm__identity_trees_off_unweighted | year | 2017.000 | 565 | 24 | 4.769 | 2.808 | 3.231 |
| arm__identity_trees_off_unweighted | year | 2018.000 | 443 | 15 | 2.850 | 0.844 | 1.507 |
| arm__identity_trees_off_unweighted | year | 2019.000 | 431 | 18 | 5.951 | 4.304 | 4.627 |
| arm__identity_trees_off_unweighted | pooled |  | 2312 | 37 | 8.193 | 8.100 | 8.294 |
| arm__identity_trees_off_unweighted | macro_over_groups |  | 2312 | 37 | 18.226 | 19.991 | 19.842 |
| base__damped_persistence | year | 2016.000 | 397 | 24 | 6.827 | 6.128 | 6.312 |
| base__damped_persistence | year | 2017.000 | 412 | 20 | 4.489 | 2.881 | 3.350 |
| base__damped_persistence | year | 2018.000 | 320 | 14 | 3.566 | 0.284 | 1.088 |
| base__damped_persistence | year | 2019.000 | 290 | 15 | 7.148 | 4.461 | 4.930 |
| base__damped_persistence | pooled |  | 1419 | 26 | 5.478 | 3.527 | 3.991 |
| base__damped_persistence | macro_over_groups |  | 1419 | 26 | 7.186 | 5.928 | 6.097 |
| base__donor_median | year | 2016.000 | 873 | 36 | 16.826 | 17.081 | 16.826 |
| base__donor_median | year | 2017.000 | 565 | 24 | 3.231 | 2.808 | 3.231 |
| base__donor_median | year | 2018.000 | 443 | 15 | 1.507 | 0.844 | 1.507 |
| base__donor_median | year | 2019.000 | 431 | 18 | 4.627 | 4.304 | 4.627 |
| base__donor_median | pooled |  | 2312 | 37 | 8.294 | 8.100 | 8.294 |
| base__donor_median | macro_over_groups |  | 2312 | 37 | 19.842 | 19.991 | 19.842 |
| base__persistence | year | 2016.000 | 397 | 24 | 6.240 | 6.128 | 6.312 |
| base__persistence | year | 2017.000 | 412 | 20 | 5.374 | 2.881 | 3.350 |
| base__persistence | year | 2018.000 | 320 | 14 | 1.141 | 0.284 | 1.088 |
| base__persistence | year | 2019.000 | 290 | 15 | 4.727 | 4.461 | 4.930 |
| base__persistence | pooled |  | 1419 | 26 | 4.529 | 3.527 | 3.991 |
| base__persistence | macro_over_groups |  | 1419 | 26 | 6.090 | 5.928 | 6.097 |
| base__predict_zero | year | 2016.000 | 873 | 36 | 17.081 | 17.081 | 16.826 |
| base__predict_zero | year | 2017.000 | 565 | 24 | 2.808 | 2.808 | 3.231 |
| base__predict_zero | year | 2018.000 | 443 | 15 | 0.844 | 0.844 | 1.507 |
| base__predict_zero | year | 2019.000 | 431 | 18 | 4.304 | 4.304 | 4.627 |
| base__predict_zero | pooled |  | 2312 | 37 | 8.100 | 8.100 | 8.294 |
| base__predict_zero | macro_over_groups |  | 2312 | 37 | 19.991 | 19.991 | 19.842 |

### Lead 365

| column | line | year | n | n_groups | mae | mae_predict_zero | mae_donor_median |
|---|---|---|---|---|---|---|---|
| arm__arcsine_corrector_gls | year | 2016.000 | 873 | 36 | 15.362 | 17.081 | 16.826 |
| arm__arcsine_corrector_gls | year | 2017.000 | 565 | 24 | 4.213 | 2.808 | 3.231 |
| arm__arcsine_corrector_gls | year | 2018.000 | 443 | 15 | 2.462 | 0.844 | 1.507 |
| arm__arcsine_corrector_gls | year | 2019.000 | 431 | 18 | 5.253 | 4.304 | 4.627 |
| arm__arcsine_corrector_gls | pooled |  | 2312 | 37 | 8.281 | 8.100 | 8.294 |
| arm__arcsine_corrector_gls | macro_over_groups |  | 2312 | 37 | 19.110 | 19.991 | 19.842 |
| arm__arcsine_trees_off_unweighted | year | 2016.000 | 873 | 36 | 15.038 | 17.081 | 16.826 |
| arm__arcsine_trees_off_unweighted | year | 2017.000 | 565 | 24 | 4.153 | 2.808 | 3.231 |
| arm__arcsine_trees_off_unweighted | year | 2018.000 | 443 | 15 | 2.650 | 0.844 | 1.507 |
| arm__arcsine_trees_off_unweighted | year | 2019.000 | 431 | 18 | 5.043 | 4.304 | 4.627 |
| arm__arcsine_trees_off_unweighted | pooled |  | 2312 | 37 | 8.141 | 8.100 | 8.294 |
| arm__arcsine_trees_off_unweighted | macro_over_groups |  | 2312 | 37 | 18.707 | 19.991 | 19.842 |
| arm__identity_trees_off_unweighted | year | 2016.000 | 873 | 36 | 14.337 | 17.081 | 16.826 |
| arm__identity_trees_off_unweighted | year | 2017.000 | 565 | 24 | 5.408 | 2.808 | 3.231 |
| arm__identity_trees_off_unweighted | year | 2018.000 | 443 | 15 | 4.130 | 0.844 | 1.507 |
| arm__identity_trees_off_unweighted | year | 2019.000 | 431 | 18 | 6.166 | 4.304 | 4.627 |
| arm__identity_trees_off_unweighted | pooled |  | 2312 | 37 | 8.676 | 8.100 | 8.294 |
| arm__identity_trees_off_unweighted | macro_over_groups |  | 2312 | 37 | 17.875 | 19.991 | 19.842 |
| base__damped_persistence | year | 2016.000 | 359 | 24 | 7.308 | 6.388 | 6.542 |
| base__damped_persistence | year | 2017.000 | 394 | 20 | 4.896 | 2.953 | 3.436 |
| base__damped_persistence | year | 2018.000 | 298 | 14 | 3.828 | 0.279 | 1.083 |
| base__damped_persistence | year | 2019.000 | 283 | 15 | 7.920 | 4.550 | 5.017 |
| base__damped_persistence | pooled |  | 1334 | 26 | 5.948 | 3.619 | 4.082 |
| base__damped_persistence | macro_over_groups |  | 1334 | 26 | 7.460 | 5.968 | 6.135 |
| base__donor_median | year | 2016.000 | 873 | 36 | 16.826 | 17.081 | 16.826 |
| base__donor_median | year | 2017.000 | 565 | 24 | 3.231 | 2.808 | 3.231 |
| base__donor_median | year | 2018.000 | 443 | 15 | 1.507 | 0.844 | 1.507 |
| base__donor_median | year | 2019.000 | 431 | 18 | 4.627 | 4.304 | 4.627 |
| base__donor_median | pooled |  | 2312 | 37 | 8.294 | 8.100 | 8.294 |
| base__donor_median | macro_over_groups |  | 2312 | 37 | 19.842 | 19.991 | 19.842 |
| base__persistence | year | 2016.000 | 359 | 24 | 6.644 | 6.388 | 6.542 |
| base__persistence | year | 2017.000 | 394 | 20 | 5.087 | 2.953 | 3.436 |
| base__persistence | year | 2018.000 | 298 | 14 | 2.035 | 0.279 | 1.083 |
| base__persistence | year | 2019.000 | 283 | 15 | 5.412 | 4.550 | 5.017 |
| base__persistence | pooled |  | 1334 | 26 | 4.893 | 3.619 | 4.082 |
| base__persistence | macro_over_groups |  | 1334 | 26 | 6.364 | 5.968 | 6.135 |
| base__predict_zero | year | 2016.000 | 873 | 36 | 17.081 | 17.081 | 16.826 |
| base__predict_zero | year | 2017.000 | 565 | 24 | 2.808 | 2.808 | 3.231 |
| base__predict_zero | year | 2018.000 | 443 | 15 | 0.844 | 0.844 | 1.507 |
| base__predict_zero | year | 2019.000 | 431 | 18 | 4.304 | 4.304 | 4.627 |
| base__predict_zero | pooled |  | 2312 | 37 | 8.100 | 8.100 | 8.294 |
| base__predict_zero | macro_over_groups |  | 2312 | 37 | 19.991 | 19.991 | 19.842 |

## 5. Per ecoregion (n, zero share, programme mix; never ranked by MAE)

| group | n | zero_share | n_AGRRA | n_Donner | n_FRRP | n_McClanahan | n_Reef_Check | n_mixed |
|---|---|---|---|---|---|---|---|---|
| Andaman Islands | 8 | 0.000 | 0 | 0 | 0 | 8 | 0 | 0 |
| Andaman Sea | 63 | 0.841 | 0 | 0 | 0 | 0 | 63 | 0 |
| Bahamas and Florida Keys | 206 | 0.097 | 0 | 0 | 190 | 0 | 16 | 0 |
| Banda Sea and Molucca Islands | 71 | 0.761 | 0 | 0 | 0 | 0 | 71 | 0 |
| Belize and west Caribbean | 22 | 0.318 | 0 | 0 | 0 | 0 | 22 | 0 |
| Celebes Sea | 25 | 0.560 | 0 | 0 | 0 | 0 | 25 | 0 |
| Central and northern Great Barrier Reef | 48 | 0.104 | 0 | 0 | 0 | 0 | 48 | 0 |
| Eastern Hawaii | 1 | 1.000 | 0 | 0 | 0 | 0 | 1 | 0 |
| Fiji | 73 | 0.507 | 0 | 0 | 0 | 11 | 62 | 0 |
| Gulf of Oman | 13 | 0.769 | 0 | 0 | 0 | 0 | 13 | 0 |
| Hispaniola, Puerto Rico and Lesser Antilles | 171 | 0.684 | 0 | 0 | 0 | 0 | 171 | 0 |
| Jamaica | 49 | 0.878 | 1 | 0 | 0 | 0 | 48 | 0 |
| Java Sea | 18 | 0.000 | 0 | 0 | 0 | 18 | 0 | 0 |
| Kenya and Tanzania coast | 35 | 0.000 | 0 | 0 | 0 | 35 | 0 | 0 |
| Lakshadweep Islands | 14 | 0.000 | 0 | 0 | 0 | 14 | 0 | 0 |
| Lesser Sunda Islands and Savu Sea | 164 | 0.476 | 0 | 0 | 0 | 9 | 155 | 0 |
| Makassar Strait, Indonesia | 2 | 0.000 | 0 | 0 | 0 | 2 | 0 | 0 |
| Maldive Islands | 81 | 0.370 | 0 | 0 | 0 | 3 | 78 | 0 |
| Mascarene Islands | 14 | 0.071 | 0 | 0 | 0 | 12 | 2 | 0 |
| Mayotte and Comoros | 7 | 0.714 | 0 | 0 | 0 | 0 | 7 | 0 |
| Moreton Bay, eastern Australia | 75 | 0.133 | 0 | 0 | 0 | 0 | 75 | 0 |
| Netherlands Antilles and south Caribbean | 10 | 0.200 | 0 | 0 | 0 | 0 | 10 | 0 |
| Ningaloo Reef and coastal north-west Australia | 16 | 0.000 | 0 | 0 | 0 | 10 | 6 | 0 |
| North Madagascar | 28 | 0.179 | 0 | 0 | 0 | 21 | 7 | 0 |
| North Philippines | 19 | 0.316 | 0 | 0 | 0 | 0 | 19 | 0 |
| North Ryukyu Islands, Japan | 4 | 0.000 | 0 | 0 | 0 | 4 | 0 | 0 |
| North and central Red Sea | 49 | 0.918 | 0 | 0 | 0 | 0 | 49 | 0 |
| Persian Gulf | 11 | 0.727 | 0 | 0 | 0 | 0 | 11 | 0 |
| Society Islands, French Polynesia | 113 | 0.743 | 0 | 0 | 0 | 0 | 113 | 0 |
| Solomon Islands and Bougainville | 16 | 0.000 | 0 | 0 | 0 | 16 | 0 | 0 |
| South Madagascar | 12 | 0.000 | 0 | 0 | 0 | 12 | 0 | 0 |
| South-east Philippines | 16 | 0.875 | 0 | 0 | 0 | 0 | 16 | 0 |
| Southern Great Barrier Reef | 32 | 0.000 | 0 | 0 | 0 | 0 | 32 | 0 |
| Strait of Malacca | 14 | 0.000 | 0 | 0 | 0 | 14 | 0 | 0 |
| Sulu Sea | 263 | 0.814 | 0 | 0 | 0 | 0 | 263 | 0 |
| Sunda Shelf, south-east Asia | 445 | 0.762 | 0 | 0 | 0 | 0 | 445 | 0 |
| Taiwan and coastal China | 104 | 0.827 | 0 | 0 | 0 | 0 | 104 | 0 |

## 6. Counts

### Rows left with no tree (V2 pool tree drop), per arm and pass

| pass | lead | arm | n_rows | n_rows_no_tree | share_no_tree |
|---|---|---|---|---|---|
| decision_surface | 0 | arcsine_corrector_gls | 2046 | 0 | 0.000 |
| decision_surface | 0 | arcsine_corrector_unweighted | 2046 | 0 | 0.000 |
| decision_surface | 0 | arcsine_plain_gls | 2046 | 0 | 0.000 |
| decision_surface | 0 | arcsine_plain_unweighted | 2046 | 0 | 0.000 |
| decision_surface | 0 | identity_corrector_gls | 2046 | 0 | 0.000 |
| decision_surface | 0 | identity_corrector_unweighted | 2046 | 0 | 0.000 |
| decision_surface | 0 | identity_plain_gls | 2046 | 0 | 0.000 |
| decision_surface | 0 | identity_plain_unweighted | 2046 | 0 | 0.000 |
| decision_surface | 0 | log_c_corrector_gls | 2046 | 0 | 0.000 |
| decision_surface | 0 | log_c_corrector_unweighted | 2046 | 0 | 0.000 |
| decision_surface | 0 | log_c_plain_gls | 2046 | 0 | 0.000 |
| decision_surface | 0 | log_c_plain_unweighted | 2046 | 0 | 0.000 |
| test_pass | 0 | arcsine_corrector_gls | 2312 | 0 | 0.000 |
| test_pass | 0 | arcsine_corrector_unweighted | 2312 | 0 | 0.000 |
| test_pass | 0 | arcsine_placebo_corrector_gls | 2312 | 0 | 0.000 |
| test_pass | 0 | arcsine_placebo_corrector_unweighted | 2312 | 0 | 0.000 |
| test_pass | 0 | arcsine_plain_gls | 2312 | 0 | 0.000 |
| test_pass | 0 | arcsine_plain_unweighted | 2312 | 0 | 0.000 |
| test_pass | 0 | identity_corrector_gls | 2312 | 0 | 0.000 |
| test_pass | 0 | identity_corrector_unweighted | 2312 | 0 | 0.000 |
| test_pass | 0 | identity_placebo_corrector_gls | 2312 | 0 | 0.000 |
| test_pass | 0 | identity_placebo_corrector_unweighted | 2312 | 0 | 0.000 |
| test_pass | 0 | identity_plain_gls | 2312 | 0 | 0.000 |
| test_pass | 0 | identity_plain_unweighted | 2312 | 0 | 0.000 |
| test_pass | 0 | log_c_corrector_gls | 2312 | 0 | 0.000 |
| test_pass | 0 | log_c_corrector_unweighted | 2312 | 0 | 0.000 |
| test_pass | 0 | log_c_placebo_corrector_gls | 2312 | 0 | 0.000 |
| test_pass | 0 | log_c_placebo_corrector_unweighted | 2312 | 0 | 0.000 |
| test_pass | 0 | log_c_plain_gls | 2312 | 0 | 0.000 |
| test_pass | 0 | log_c_plain_unweighted | 2312 | 0 | 0.000 |
| guard | 183 | arcsine_corrector_gls | 1554 | 0 | 0.000 |
| test_pass | 183 | arcsine_corrector_gls | 2312 | 0 | 0.000 |
| guard | 365 | arcsine_corrector_gls | 1283 | 0 | 0.000 |
| test_pass | 365 | arcsine_corrector_gls | 2312 | 0 | 0.000 |
| test_pass | 365 | arcsine_placebo_corrector_gls | 2312 | 0 | 0.000 |

### Pool fallbacks (under 12 valid pool rows)

| pass | lead | pools_file | rows | rows_pool_fallback | matches_record |
|---|---|---|---|---|---|
| decision_surface | 0 | pools_decision_surface.parquet | 2046 | 0 | yes |
| test_pass | 0 | pools_test_pass.parquet | 2312 | 0 | yes |
| guard | 183 | ladder/lead_183/pools_guard.parquet | 1554 | 0 | yes |
| test_pass | 183 | ladder/lead_183/pools_test_pass.parquet | 2312 | 0 | yes |
| guard | 365 | ladder/lead_365/pools_guard.parquet | 1283 | 0 | yes |
| test_pass | 365 | ladder/lead_365/pools_test_pass.parquet | 2312 | 0 | yes |

### Rows left out

| what | lead | source | rows_record | rows_file |
|---|---|---|---|---|
| H4 test rows absent at the lead (left out of scoring) | 183 | lead.json issue_features_missing / issue_missing_rows.parquet | 0 | 0 |
| H4 test rows absent at the lead (left out of scoring) | 365 | lead.json issue_features_missing / issue_missing_rows.parquet | 0 | 0 |

### R30 missing tree features (0-filled share) and marine-heatwave NaN rows

Saved once by the engine (derived.json R30): donor rows at the lead-0 fit cut. Per-year shares are in r30_missing.csv.

| lead | what | column | filled_share | flag_threshold | over_threshold | engine_flags | status |
|---|---|---|---|---|---|---|---|
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cool_180 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cool_30 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cool_365 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cool_56 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cool_84 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cool_90 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cyc_days_since_close | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cyc_maxw_200_30 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cyc_maxw_200_365 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cyc_maxw_200_90 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cyc_maxw_500_30 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cyc_maxw_500_365 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cyc_maxw_500_90 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cyc_mindist_30 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cyc_mindist_365 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cyc_mindist_90 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cyc_n_200_30 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cyc_n_200_365 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cyc_n_200_90 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cyc_n_500_30 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cyc_n_500_365 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | cyc_n_500_90 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | days_since_dhw4 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | days_since_max_hs | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | dhw_180 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | dhw_30 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | dhw_365 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | dhw_56 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | dhw_84 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | dhw_90 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | hs_max_180 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | hs_max_30 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | hs_max_365 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | hs_max_56 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | hs_max_84 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | hs_max_90 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | mhw_cat_max_90 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | mhw_days_30 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | mhw_days_365 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | mhw_days_90 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | mhw_durmax_365 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | mhw_icum_90 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | mhw_imax_90 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | mhw_nev_365 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | mhw_since_end | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | mhw_thr_gap | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | n_above_mmm1_180 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | n_above_mmm1_30 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | n_above_mmm1_365 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | n_above_mmm1_56 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | n_above_mmm1_84 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | n_above_mmm1_90 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | n_above_mmm_180 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | n_above_mmm_30 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | n_above_mmm_365 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | n_above_mmm_56 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | n_above_mmm_84 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | n_above_mmm_90 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | n_dhw_ge8_before | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | nino34a_lag3 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | nino34a_lag6 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | nino34a_lag9 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | 0-filled share (R30), donor rows at the lead-0 fit cut | slope_90 | 0.000 | 0.250 | no |  | saved: derived.json R30 |
| 0 | largest 0-filled share over the marine-heatwave tree columns (mhw_*), donor rows | (10 marine-heatwave columns) | 0.000 |  |  |  | saved: the largest of the per-column shares above |

Counted from the lead tables (not an engine record), at every lead, on the donor rows at the lead's fit cut and on the scored test rows. At lead 0 the donor-row shares were checked equal to R30. Below: the marine-heatwave counts, and every column with at least one NaN row (all columns are in r30_missing.csv).

| lead | rows_set | what | column | n_rows | n_nan | nan_share | over_threshold | status |
|---|---|---|---|---|---|---|---|---|
| 0 | donor rows at the lead's fit cut | rows with a NaN in any marine-heatwave column (count) | (10 mhw_* columns) | 11338 | 0 | 0.000 |  | counted from the lead table (not an engine record) |
| 0 | donor rows at the lead's fit cut | rows with a NaN in mhw_days_365 (under 60 thresholded days; count) | mhw_days_365 | 11338 | 0 | 0.000 |  | counted from the lead table (not an engine record); NaN exactly when under 60 thresholded days (build_tables.py:315) |
| 0 | scored test rows (finite label) | rows with a NaN in any marine-heatwave column (count) | (10 mhw_* columns) | 2312 | 0 | 0.000 |  | counted from the lead table (not an engine record) |
| 0 | scored test rows (finite label) | rows with a NaN in mhw_days_365 (under 60 thresholded days; count) | mhw_days_365 | 2312 | 0 | 0.000 |  | counted from the lead table (not an engine record); NaN exactly when under 60 thresholded days (build_tables.py:315) |
| 183 | donor rows at the lead's fit cut | rows with a NaN in any marine-heatwave column (count) | (10 mhw_* columns) | 10838 | 0 | 0.000 |  | counted from the lead table (not an engine record) |
| 183 | donor rows at the lead's fit cut | rows with a NaN in mhw_days_365 (under 60 thresholded days; count) | mhw_days_365 | 10838 | 0 | 0.000 |  | counted from the lead table (not an engine record); NaN exactly when under 60 thresholded days (build_tables.py:315) |
| 183 | scored test rows (finite label) | rows with a NaN in any marine-heatwave column (count) | (10 mhw_* columns) | 2312 | 0 | 0.000 |  | counted from the lead table (not an engine record) |
| 183 | scored test rows (finite label) | rows with a NaN in mhw_days_365 (under 60 thresholded days; count) | mhw_days_365 | 2312 | 0 | 0.000 |  | counted from the lead table (not an engine record); NaN exactly when under 60 thresholded days (build_tables.py:315) |
| 365 | donor rows at the lead's fit cut | rows with a NaN in any marine-heatwave column (count) | (10 mhw_* columns) | 10567 | 0 | 0.000 |  | counted from the lead table (not an engine record) |
| 365 | donor rows at the lead's fit cut | rows with a NaN in mhw_days_365 (under 60 thresholded days; count) | mhw_days_365 | 10567 | 0 | 0.000 |  | counted from the lead table (not an engine record); NaN exactly when under 60 thresholded days (build_tables.py:315) |
| 365 | scored test rows (finite label) | rows with a NaN in any marine-heatwave column (count) | (10 mhw_* columns) | 2312 | 0 | 0.000 |  | counted from the lead table (not an engine record) |
| 365 | scored test rows (finite label) | rows with a NaN in mhw_days_365 (under 60 thresholded days; count) | mhw_days_365 | 2312 | 0 | 0.000 |  | counted from the lead table (not an engine record); NaN exactly when under 60 thresholded days (build_tables.py:315) |

### Pools holding a month-precision row

| pass | lead | pools_file | pools | pools_holding_month_precision_row | status |
|---|---|---|---|---|---|
| decision_surface | 0 | pools_decision_surface.parquet | 2046 | 1094 | counted from the saved pools and the builder's list D:\treeroute\coral_build\coral_data\month_precision_rows.csv (SHA-256 cfa18268198ca9be) (not an engine record) |
| test_pass | 0 | pools_test_pass.parquet | 2312 | 1007 | counted from the saved pools and the builder's list D:\treeroute\coral_build\coral_data\month_precision_rows.csv (SHA-256 cfa18268198ca9be) (not an engine record) |
| guard | 183 | ladder/lead_183/pools_guard.parquet | 1554 | 1055 | counted from the saved pools and the builder's list D:\treeroute\coral_build\coral_data\month_precision_rows.csv (SHA-256 cfa18268198ca9be) (not an engine record) |
| test_pass | 183 | ladder/lead_183/pools_test_pass.parquet | 2312 | 1172 | counted from the saved pools and the builder's list D:\treeroute\coral_build\coral_data\month_precision_rows.csv (SHA-256 cfa18268198ca9be) (not an engine record) |
| guard | 365 | ladder/lead_365/pools_guard.parquet | 1283 | 1029 | counted from the saved pools and the builder's list D:\treeroute\coral_build\coral_data\month_precision_rows.csv (SHA-256 cfa18268198ca9be) (not an engine record) |
| test_pass | 365 | ladder/lead_365/pools_test_pass.parquet | 2312 | 1245 | counted from the saved pools and the builder's list D:\treeroute\coral_build\coral_data\month_precision_rows.csv (SHA-256 cfa18268198ca9be) (not an engine record) |

### Picks at the penalty grid edge (flagged, never extended)

| source | lead | arm | point | at_edge | edge_level | edge_ratio | engine_printed_edge | note |
|---|---|---|---|---|---|---|---|---|
| adoption.json penalty (the adopted pick) | 0 | arcsine_corrector_gls | level 100.0 ratio 1.0 | yes | top | top |  |  |
| adoption.json best_tree_penalty | 0 | arcsine_corrector_gls | level 100.0 ratio 1.0 | yes | top | top |  |  |
| adoption_lead_183.json penalty (the pinned arm at the lead) | 183 | arcsine_corrector_gls | level 100.0 ratio 1.0 | yes | top | top |  |  |
| adoption_lead_365.json penalty (the pinned arm at the lead) | 365 | arcsine_corrector_gls | level 100.0 ratio 1.0 | yes | top | top |  |  |
| run.log (the engine's printed decision line) | 0 | identity_plain_unweighted | level 100.0 ratio 1.0 | yes | top | top | level top, ratio top | decision block 1; MAE 8.068373 as printed, checked against adoption.json surface_mae |
| run.log (the engine's printed decision line) | 0 | identity_plain_gls | level 100.0 ratio 1.0 | yes | top | top | level top, ratio top | decision block 1; MAE 7.894813 as printed, checked against adoption.json surface_mae |
| run.log (the engine's printed decision line) | 0 | identity_corrector_unweighted | level 100.0 ratio 1.0 | yes | top | top | level top, ratio top | decision block 1; MAE 8.07137 as printed, checked against adoption.json surface_mae |
| run.log (the engine's printed decision line) | 0 | identity_corrector_gls | level 100.0 ratio 1.0 | yes | top | top | level top, ratio top | decision block 1; MAE 7.901014 as printed, checked against adoption.json surface_mae |
| run.log (the engine's printed decision line) | 0 | log_c_plain_unweighted | level 3.0 ratio 1.0 | yes |  | top | ratio top | decision block 1; MAE 7.314079 as printed, checked against adoption.json surface_mae |
| run.log (the engine's printed decision line) | 0 | log_c_plain_gls | level 3.0 ratio 1.0 | yes |  | top | ratio top | decision block 1; MAE 7.325022 as printed, checked against adoption.json surface_mae |
| run.log (the engine's printed decision line) | 0 | log_c_corrector_unweighted | level 3.0 ratio 1.0 | yes |  | top | ratio top | decision block 1; MAE 7.243545 as printed, checked against adoption.json surface_mae |
| run.log (the engine's printed decision line) | 0 | log_c_corrector_gls | level 3.0 ratio 1.0 | yes |  | top | ratio top | decision block 1; MAE 7.261769 as printed, checked against adoption.json surface_mae |
| run.log (the engine's printed decision line) | 0 | arcsine_plain_unweighted | level 100.0 ratio 1.0 | yes | top | top | level top, ratio top | decision block 1; MAE 7.294547 as printed, checked against adoption.json surface_mae |
| run.log (the engine's printed decision line) | 0 | arcsine_plain_gls | level 100.0 ratio 1.0 | yes | top | top | level top, ratio top | decision block 1; MAE 7.21281 as printed, checked against adoption.json surface_mae |
| run.log (the engine's printed decision line) | 0 | arcsine_corrector_unweighted | level 100.0 ratio 1.0 | yes | top | top | level top, ratio top | decision block 1; MAE 7.287183 as printed, checked against adoption.json surface_mae |
| run.log (the engine's printed decision line) | 0 | arcsine_corrector_gls | level 100.0 ratio 1.0 | yes | top | top | level top, ratio top | decision block 1; MAE 7.210064 as printed, checked against adoption.json surface_mae; same point as the saved best_tree_penalty (checked) |

## 7. Leads

Leads [0, 183, 365]; the ladder rows are scored on the rows common to all leads (rows_basis 'common' in every CSV), with all rows beside.

### Guard reference and decline object per lead (ruling V1: one object)

The pinned arm's MAE and the reference's MAE on the guard surface, side by side.

| lead | surface | surface_rows | reference_column | reference_value | reference_value_text | reference_mae | pinned_arm | pinned_mae | pinned_minus_reference | own_trees_off_mae | passed | decline_target | guard_and_decline_one_object | not_saved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | decision surface (nowcast N2 check) | 2046 | base__donor_median |  | per fold: Andaman Sea=1.25; Bahamas and Florida Keys=0.25; Banda Sea and Molucca Islands=1.25; Belize and west Caribbean=0.8416666666666667; Celebes Sea=1.190476186; Central and northern Great Barrier Reef=1.25; Fiji=1.2993162057272727; Gulf of Oman=1.25; Gulf of Thailand=1.25; Hispaniola, Puerto Rico and Lesser Antilles=1.0; Honshu, Japan=1.1952380950000001; Jamaica=1.14; Lesser Sunda Islands and Savu Sea=1.190476186; Maldive Islands=1.234567901; Marshall Islands=1.190476186; Mascarene Islands=1.25; Mayotte and Comoros=1.25; Moreton Bay, eastern Australia=1.25; Netherlands Antilles and south Caribbean=1.25; Ningaloo Reef and coastal north-west Australia=1.19; North Philippines=1.234567901; North and central Red Sea=1.25; Samoa, Tuvalu and Tonga=1.133658007; Shikoku, Japan=1.1952380950000001; Society Islands, French Polynesia=1.25; South Ryukyu Islands, Japan=1.25; South-east Philippines=1.349431817; Southern Great Barrier Reef=1.25; Sulu Sea=1.25; Sunda Shelf, south-east Asia=1.395; Taiwan and coastal China=1.2084702445; Vanuatu=1.25; Western Tuamotu Archipelago, central Pacific=1.234567901 | 9.742 | arcsine_corrector_gls | 7.210 | -2.531 | 7.417 | yes | base__donor_median | yes | reference_value (one median per fold, not one value); reference_donor_rows |
| 183 | lead guard surface (H2) | 1554 | base__donor_median | 1.250 |  | 6.932 | arcsine_corrector_gls | 6.679 | -0.253 | 6.928 | yes | base__donor_median | yes |  |
| 365 | lead guard surface (H2) | 1283 | base__donor_median | 1.333 |  | 7.835 | arcsine_corrector_gls | 8.181 | 0.346 | 7.933 | no | base__donor_median | yes |  |

