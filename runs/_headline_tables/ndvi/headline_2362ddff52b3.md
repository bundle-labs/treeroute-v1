# Headline tables

Built by treeroute_report.table from SAVED row-level predictions (test_preds.parquet) with the engine's treeroute.report.metrics functions. Every recorded verdict, band pair and blocked jackknife was recomputed from the saved rows and is equal. The band was recomputed from each run's own contrasts and is equal. MAE, anomaly R2 against the per-unit normal, corr2 and the hit rate are printed together, each beside guess-normal and the last-5-years normal; never R2 alone. Uncertainty is over groups (jackknife at 1.96); no multiplicity correction.

Files: `continuity_a96f8e83dc35.csv`, `disclosures_d8d01fbcba11.csv`, `headline_9e5590eab94b.csv`, `per_group_6385d3cbe10e.csv`, `per_stratum_582739ed9698.csv`, `per_year_b537985b2ac7.csv`, `scores_long_be44fcb279ae.csv`, `subsets_a88a8d9c284b.csv`, `verdicts_c4cd7e7c2610.csv`

## Runs

| package | run folder | kind | run fingerprint | package fingerprint | leads | groups | scored units |
|---|---|---|---|---|---|---|---|
| ndvi | D:\treeroute\runs\ndvi\headline\20261016_d1de3158 | headline | d1de3158cad5ab44 | edbc45b52643dcdd | 0, 6, 12 | 133 | 1983 |

## Headline: pooled and macro (unweighted mean over groups)

Lead 0 is the nowcast. Rows 'all' = every saved row of the lead; 'common' = rows scored at every lead (the ladder's basis, R34).

| package | lead | rows | line | metric | adopted | own-link trees-off | guess-normal | last-5-years normal | predict-zero | persistence | damped persistence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ndvi | 0 | all | pooled | MAE | 0.03146 | 0.03941 | 0.03941 | 0.03934 | 0.4365 | n/a | n/a |
| ndvi | 0 | all | pooled | anomaly R2 | 0.3171 | 1.452e-09 | 0 | -0.05228 | n/a | n/a | n/a |
| ndvi | 0 | all | pooled | corr2 | 0.9632 | 0.9461 | 0.9461 | 0.9425 | n/a | n/a | n/a |
| ndvi | 0 | all | pooled | hit rate | 0.4606 | 0.3894 | 0.3894 | 0.4047 | n/a | n/a | n/a |
| ndvi | 0 | all | pooled | hit rate at the declared floor | 0.5228 | 0.4464 | 0.4464 | 0.4612 | n/a | n/a | n/a |
| ndvi | 0 | all | pooled | calibration ratio | 0.9845 | 0.9808 | 0.9808 | 0.9928 | n/a | n/a | n/a |
| ndvi | 0 | all | pooled | pre-clip rate | 0 | 0 | n/a | n/a | n/a | n/a | n/a |
| ndvi | 0 | all | pooled | strict top-10% detection (R33) | 0.845 | 0.8265 | 0.8265 | 0.8302 | n/a | n/a | n/a |
| ndvi | 0 | all | pooled | detection events | 9448 | 9448 | 9448 | 9448 | n/a | n/a | n/a |
| ndvi | 0 | all | macro | MAE | 0.03146 | 0.03938 | 0.03938 | 0.0393 | 0.4357 | n/a | n/a |
| ndvi | 0 | all | macro | anomaly R2 | 0.2926 | 1.02e-07 | 0 | -0.07731 | n/a | n/a | n/a |
| ndvi | 0 | all | macro | corr2 | 0.8647 | 0.807 | 0.807 | 0.7975 | n/a | n/a | n/a |
| ndvi | 0 | all | macro | hit rate | 0.461 | 0.3902 | 0.3902 | 0.4057 | n/a | n/a | n/a |
| ndvi | 0 | all | macro | hit rate at the declared floor | 0.5231 | 0.4472 | 0.4472 | 0.4621 | n/a | n/a | n/a |
| ndvi | 0 | all | macro | calibration ratio | 0.9845 | 0.9806 | 0.9806 | 0.9944 | n/a | n/a | n/a |
| ndvi | 0 | all | macro | pre-clip rate | 0 | 0 | n/a | n/a | n/a | n/a | n/a |
| ndvi | 0 | all | macro | strict top-10% detection (R33) | 0.7168 | 0.6792 | 0.6792 | 0.674 | n/a | n/a | n/a |
| ndvi | 0 | all | macro | detection events | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ndvi | 0 | common | pooled | MAE | 0.03146 | 0.03941 | 0.03941 | 0.03934 | 0.4365 | n/a | n/a |
| ndvi | 0 | common | pooled | anomaly R2 | 0.3171 | 1.452e-09 | 0 | -0.05228 | n/a | n/a | n/a |
| ndvi | 0 | common | pooled | corr2 | 0.9632 | 0.9461 | 0.9461 | 0.9425 | n/a | n/a | n/a |
| ndvi | 0 | common | pooled | hit rate | 0.4606 | 0.3894 | 0.3894 | 0.4047 | n/a | n/a | n/a |
| ndvi | 0 | common | pooled | hit rate at the declared floor | 0.5228 | 0.4464 | 0.4464 | 0.4612 | n/a | n/a | n/a |
| ndvi | 0 | common | pooled | calibration ratio | 0.9845 | 0.9808 | 0.9808 | 0.9928 | n/a | n/a | n/a |
| ndvi | 0 | common | pooled | pre-clip rate | 0 | 0 | n/a | n/a | n/a | n/a | n/a |
| ndvi | 0 | common | pooled | strict top-10% detection (R33) | 0.845 | 0.8265 | 0.8265 | 0.8302 | n/a | n/a | n/a |
| ndvi | 0 | common | pooled | detection events | 9448 | 9448 | 9448 | 9448 | n/a | n/a | n/a |
| ndvi | 0 | common | macro | MAE | 0.03146 | 0.03938 | 0.03938 | 0.0393 | 0.4357 | n/a | n/a |
| ndvi | 0 | common | macro | anomaly R2 | 0.2926 | 1.02e-07 | 0 | -0.07731 | n/a | n/a | n/a |
| ndvi | 0 | common | macro | corr2 | 0.8647 | 0.807 | 0.807 | 0.7975 | n/a | n/a | n/a |
| ndvi | 0 | common | macro | hit rate | 0.461 | 0.3902 | 0.3902 | 0.4057 | n/a | n/a | n/a |
| ndvi | 0 | common | macro | hit rate at the declared floor | 0.5231 | 0.4472 | 0.4472 | 0.4621 | n/a | n/a | n/a |
| ndvi | 0 | common | macro | calibration ratio | 0.9845 | 0.9806 | 0.9806 | 0.9944 | n/a | n/a | n/a |
| ndvi | 0 | common | macro | pre-clip rate | 0 | 0 | n/a | n/a | n/a | n/a | n/a |
| ndvi | 0 | common | macro | strict top-10% detection (R33) | 0.7168 | 0.6792 | 0.6792 | 0.674 | n/a | n/a | n/a |
| ndvi | 0 | common | macro | detection events | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ndvi | 6 | all | pooled | MAE | 0.03957 | 0.03957 | 0.03957 | 0.03983 | 0.4365 | 0.1609 | 0.03862 |
| ndvi | 6 | all | pooled | anomaly R2 | 1.426e-09 | 1.426e-09 | 0 | -0.06771 | n/a | n/a | n/a |
| ndvi | 6 | all | pooled | corr2 | 0.9458 | 0.9458 | 0.9458 | 0.9414 | n/a | n/a | n/a |
| ndvi | 6 | all | pooled | hit rate | 0.3876 | 0.3876 | 0.3876 | 0.3994 | n/a | n/a | n/a |
| ndvi | 6 | all | pooled | hit rate at the declared floor | 0.4444 | 0.4444 | 0.4444 | 0.4553 | n/a | n/a | n/a |
| ndvi | 6 | all | pooled | calibration ratio | 0.9806 | 0.9806 | 0.9806 | 0.9932 | n/a | n/a | n/a |
| ndvi | 6 | all | pooled | pre-clip rate | 0 | 0 | n/a | n/a | n/a | n/a | n/a |
| ndvi | 6 | all | pooled | strict top-10% detection (R33) | 0.8255 | 0.8255 | 0.8255 | 0.8256 | n/a | n/a | n/a |
| ndvi | 6 | all | pooled | detection events | 9448 | 9448 | 9448 | 9448 | n/a | n/a | n/a |
| ndvi | 6 | all | macro | MAE | 0.03953 | 0.03953 | 0.03953 | 0.03979 | 0.4357 | 0.1641 | 0.03861 |
| ndvi | 6 | all | macro | anomaly R2 | 1.049e-07 | 1.049e-07 | 0 | -0.09383 | n/a | n/a | n/a |
| ndvi | 6 | all | macro | corr2 | 0.8062 | 0.8062 | 0.8062 | 0.7945 | n/a | n/a | n/a |
| ndvi | 6 | all | macro | hit rate | 0.3884 | 0.3884 | 0.3884 | 0.4003 | n/a | n/a | n/a |
| ndvi | 6 | all | macro | hit rate at the declared floor | 0.4452 | 0.4452 | 0.4452 | 0.4562 | n/a | n/a | n/a |
| ndvi | 6 | all | macro | calibration ratio | 0.9803 | 0.9803 | 0.9803 | 0.9946 | n/a | n/a | n/a |
| ndvi | 6 | all | macro | pre-clip rate | 0 | 0 | n/a | n/a | n/a | n/a | n/a |
| ndvi | 6 | all | macro | strict top-10% detection (R33) | 0.6791 | 0.6791 | 0.6791 | 0.6727 | n/a | n/a | n/a |
| ndvi | 6 | all | macro | detection events | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ndvi | 6 | common | pooled | MAE | 0.03957 | 0.03957 | 0.03957 | 0.03983 | 0.4365 | 0.1609 | 0.03862 |
| ndvi | 6 | common | pooled | anomaly R2 | 1.426e-09 | 1.426e-09 | 0 | -0.06771 | n/a | n/a | n/a |
| ndvi | 6 | common | pooled | corr2 | 0.9458 | 0.9458 | 0.9458 | 0.9414 | n/a | n/a | n/a |
| ndvi | 6 | common | pooled | hit rate | 0.3876 | 0.3876 | 0.3876 | 0.3994 | n/a | n/a | n/a |
| ndvi | 6 | common | pooled | hit rate at the declared floor | 0.4444 | 0.4444 | 0.4444 | 0.4553 | n/a | n/a | n/a |
| ndvi | 6 | common | pooled | calibration ratio | 0.9806 | 0.9806 | 0.9806 | 0.9932 | n/a | n/a | n/a |
| ndvi | 6 | common | pooled | pre-clip rate | 0 | 0 | n/a | n/a | n/a | n/a | n/a |
| ndvi | 6 | common | pooled | strict top-10% detection (R33) | 0.8255 | 0.8255 | 0.8255 | 0.8256 | n/a | n/a | n/a |
| ndvi | 6 | common | pooled | detection events | 9448 | 9448 | 9448 | 9448 | n/a | n/a | n/a |
| ndvi | 6 | common | macro | MAE | 0.03953 | 0.03953 | 0.03953 | 0.03979 | 0.4357 | 0.1641 | 0.03861 |
| ndvi | 6 | common | macro | anomaly R2 | 1.049e-07 | 1.049e-07 | 0 | -0.09383 | n/a | n/a | n/a |
| ndvi | 6 | common | macro | corr2 | 0.8062 | 0.8062 | 0.8062 | 0.7945 | n/a | n/a | n/a |
| ndvi | 6 | common | macro | hit rate | 0.3884 | 0.3884 | 0.3884 | 0.4003 | n/a | n/a | n/a |
| ndvi | 6 | common | macro | hit rate at the declared floor | 0.4452 | 0.4452 | 0.4452 | 0.4562 | n/a | n/a | n/a |
| ndvi | 6 | common | macro | calibration ratio | 0.9803 | 0.9803 | 0.9803 | 0.9946 | n/a | n/a | n/a |
| ndvi | 6 | common | macro | pre-clip rate | 0 | 0 | n/a | n/a | n/a | n/a | n/a |
| ndvi | 6 | common | macro | strict top-10% detection (R33) | 0.6791 | 0.6791 | 0.6791 | 0.6727 | n/a | n/a | n/a |
| ndvi | 6 | common | macro | detection events | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ndvi | 12 | all | pooled | MAE | 0.03958 | 0.03958 | 0.03958 | 0.04016 | 0.4365 | 0.06764 | 0.03882 |
| ndvi | 12 | all | pooled | anomaly R2 | 1.723e-09 | 1.723e-09 | 0 | -0.08351 | n/a | n/a | n/a |
| ndvi | 12 | all | pooled | corr2 | 0.9459 | 0.9459 | 0.9459 | 0.9405 | n/a | n/a | n/a |
| ndvi | 12 | all | pooled | hit rate | 0.3876 | 0.3876 | 0.3876 | 0.3974 | n/a | n/a | n/a |
| ndvi | 12 | all | pooled | hit rate at the declared floor | 0.4437 | 0.4437 | 0.4437 | 0.4536 | n/a | n/a | n/a |
| ndvi | 12 | all | pooled | calibration ratio | 0.9806 | 0.9806 | 0.9806 | 0.9934 | n/a | n/a | n/a |
| ndvi | 12 | all | pooled | pre-clip rate | 0 | 0 | n/a | n/a | n/a | n/a | n/a |
| ndvi | 12 | all | pooled | strict top-10% detection (R33) | 0.824 | 0.824 | 0.824 | 0.8237 | n/a | n/a | n/a |
| ndvi | 12 | all | pooled | detection events | 9448 | 9448 | 9448 | 9448 | n/a | n/a | n/a |
| ndvi | 12 | all | macro | MAE | 0.03955 | 0.03955 | 0.03955 | 0.04012 | 0.4357 | 0.06834 | 0.03883 |
| ndvi | 12 | all | macro | anomaly R2 | 1.148e-07 | 1.148e-07 | 0 | -0.1175 | n/a | n/a | n/a |
| ndvi | 12 | all | macro | corr2 | 0.8053 | 0.8053 | 0.8053 | 0.7906 | n/a | n/a | n/a |
| ndvi | 12 | all | macro | hit rate | 0.3884 | 0.3884 | 0.3884 | 0.3982 | n/a | n/a | n/a |
| ndvi | 12 | all | macro | hit rate at the declared floor | 0.4445 | 0.4445 | 0.4445 | 0.4544 | n/a | n/a | n/a |
| ndvi | 12 | all | macro | calibration ratio | 0.9802 | 0.9802 | 0.9802 | 0.9946 | n/a | n/a | n/a |
| ndvi | 12 | all | macro | pre-clip rate | 0 | 0 | n/a | n/a | n/a | n/a | n/a |
| ndvi | 12 | all | macro | strict top-10% detection (R33) | 0.6787 | 0.6787 | 0.6787 | 0.6679 | n/a | n/a | n/a |
| ndvi | 12 | all | macro | detection events | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ndvi | 12 | common | pooled | MAE | 0.03958 | 0.03958 | 0.03958 | 0.04016 | 0.4365 | 0.06764 | 0.03882 |
| ndvi | 12 | common | pooled | anomaly R2 | 1.723e-09 | 1.723e-09 | 0 | -0.08351 | n/a | n/a | n/a |
| ndvi | 12 | common | pooled | corr2 | 0.9459 | 0.9459 | 0.9459 | 0.9405 | n/a | n/a | n/a |
| ndvi | 12 | common | pooled | hit rate | 0.3876 | 0.3876 | 0.3876 | 0.3974 | n/a | n/a | n/a |
| ndvi | 12 | common | pooled | hit rate at the declared floor | 0.4437 | 0.4437 | 0.4437 | 0.4536 | n/a | n/a | n/a |
| ndvi | 12 | common | pooled | calibration ratio | 0.9806 | 0.9806 | 0.9806 | 0.9934 | n/a | n/a | n/a |
| ndvi | 12 | common | pooled | pre-clip rate | 0 | 0 | n/a | n/a | n/a | n/a | n/a |
| ndvi | 12 | common | pooled | strict top-10% detection (R33) | 0.824 | 0.824 | 0.824 | 0.8237 | n/a | n/a | n/a |
| ndvi | 12 | common | pooled | detection events | 9448 | 9448 | 9448 | 9448 | n/a | n/a | n/a |
| ndvi | 12 | common | macro | MAE | 0.03955 | 0.03955 | 0.03955 | 0.04012 | 0.4357 | 0.06834 | 0.03883 |
| ndvi | 12 | common | macro | anomaly R2 | 1.148e-07 | 1.148e-07 | 0 | -0.1175 | n/a | n/a | n/a |
| ndvi | 12 | common | macro | corr2 | 0.8053 | 0.8053 | 0.8053 | 0.7906 | n/a | n/a | n/a |
| ndvi | 12 | common | macro | hit rate | 0.3884 | 0.3884 | 0.3884 | 0.3982 | n/a | n/a | n/a |
| ndvi | 12 | common | macro | hit rate at the declared floor | 0.4445 | 0.4445 | 0.4445 | 0.4544 | n/a | n/a | n/a |
| ndvi | 12 | common | macro | calibration ratio | 0.9802 | 0.9802 | 0.9802 | 0.9946 | n/a | n/a | n/a |
| ndvi | 12 | common | macro | pre-clip rate | 0 | 0 | n/a | n/a | n/a | n/a | n/a |
| ndvi | 12 | common | macro | strict top-10% detection (R33) | 0.6787 | 0.6787 | 0.6787 | 0.6679 | n/a | n/a | n/a |
| ndvi | 12 | common | macro | detection events | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Verdicts (D74 rule; recomputed = recorded)

| package | lead | rows | verdict | contrast | CI low | CI high | SE | groups | band | band check | history band (beside, never used) | pooled contrast | groups better | sign flips | blocked-jackknife flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ndvi | 0 | all | helps | 0.007918 | 0.00675 | 0.009086 | 0.0005959 | 133 | 0.0005975 | recomputed from this run's D75 contrasts, equal | n/a | 0.007954 | 122 | alaska_north_slope argentine_monte cerrado congo_basin_drc costa_rica llanos_venezuela namib_desert sahara_eastern tongass_alaska west_africa_cocoa_belt western_sahara_coastal | no |
| ndvi | 0 | common | helps | 0.007918 | 0.00675 | 0.009086 | 0.0005959 | 133 | 0.0005975 | recomputed from this run's D75 contrasts, equal | n/a | 0.007954 | 122 | alaska_north_slope argentine_monte cerrado congo_basin_drc costa_rica llanos_venezuela namib_desert sahara_eastern tongass_alaska west_africa_cocoa_belt western_sahara_coastal | n/a |
| ndvi | 6 | common | declined | 0 | 0 | 0 | 0 | 133 | 0.0005975 | recomputed from this run's D75 contrasts, equal | n/a | 0 | 0 |  | n/a |
| ndvi | 12 | common | declined | 0 | 0 | 0 | 0 | 133 | 0.0005975 | recomputed from this run's D75 contrasts, equal | n/a | 0 | 0 |  | n/a |

## Per test year

| package | lead | rows | year | MAE adopted | MAE trees-off | MAE guess-normal | MAE last-5 | anomaly R2 | corr2 | hit rate | hit guess-normal | detection | detection guess-normal | rows |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ndvi | 0 | all | 2020 | 0.03036 | 0.03957 | 0.03957 | 0.03882 | 0.3525 | 0.9641 | 0.4817 | 0.392 | 0.862 | 0.835 | 23630 |
| ndvi | 0 | all | 2021 | 0.03033 | 0.03762 | 0.03762 | 0.03793 | 0.2902 | 0.9656 | 0.4726 | 0.3984 | 0.8451 | 0.8358 | 23633 |
| ndvi | 0 | all | 2022 | 0.03162 | 0.04023 | 0.04023 | 0.04054 | 0.3387 | 0.9621 | 0.4591 | 0.3902 | 0.8397 | 0.8211 | 23633 |
| ndvi | 0 | all | 2023 | 0.03353 | 0.04024 | 0.04024 | 0.04005 | 0.2834 | 0.961 | 0.4291 | 0.3768 | 0.8383 | 0.8226 | 23631 |
| ndvi | 0 | common | 2020 | 0.03036 | 0.03957 | 0.03957 | 0.03882 | 0.3525 | 0.9641 | 0.4817 | 0.392 | 0.862 | 0.835 | 23630 |
| ndvi | 0 | common | 2021 | 0.03033 | 0.03762 | 0.03762 | 0.03793 | 0.2902 | 0.9656 | 0.4726 | 0.3984 | 0.8451 | 0.8358 | 23633 |
| ndvi | 0 | common | 2022 | 0.03162 | 0.04023 | 0.04023 | 0.04054 | 0.3387 | 0.9621 | 0.4591 | 0.3902 | 0.8397 | 0.8211 | 23633 |
| ndvi | 0 | common | 2023 | 0.03353 | 0.04024 | 0.04024 | 0.04005 | 0.2834 | 0.961 | 0.4291 | 0.3768 | 0.8383 | 0.8226 | 23631 |
| ndvi | 6 | all | 2020 | 0.03978 | 0.03978 | 0.03978 | 0.03948 | 9.345e-10 | 0.9445 | 0.3896 | 0.3896 | 0.8337 | 0.8337 | 23630 |
| ndvi | 6 | all | 2021 | 0.03773 | 0.03773 | 0.03773 | 0.03825 | 9.364e-10 | 0.9517 | 0.3966 | 0.3966 | 0.8345 | 0.8345 | 23633 |
| ndvi | 6 | all | 2022 | 0.04033 | 0.04033 | 0.04033 | 0.04089 | 1.906e-09 | 0.9427 | 0.3895 | 0.3895 | 0.8215 | 0.8215 | 23633 |
| ndvi | 6 | all | 2023 | 0.04044 | 0.04044 | 0.04044 | 0.04069 | 1.862e-09 | 0.9444 | 0.3746 | 0.3746 | 0.8209 | 0.8209 | 23631 |
| ndvi | 6 | common | 2020 | 0.03978 | 0.03978 | 0.03978 | 0.03948 | 9.345e-10 | 0.9445 | 0.3896 | 0.3896 | 0.8337 | 0.8337 | 23630 |
| ndvi | 6 | common | 2021 | 0.03773 | 0.03773 | 0.03773 | 0.03825 | 9.364e-10 | 0.9517 | 0.3966 | 0.3966 | 0.8345 | 0.8345 | 23633 |
| ndvi | 6 | common | 2022 | 0.04033 | 0.04033 | 0.04033 | 0.04089 | 1.906e-09 | 0.9427 | 0.3895 | 0.3895 | 0.8215 | 0.8215 | 23633 |
| ndvi | 6 | common | 2023 | 0.04044 | 0.04044 | 0.04044 | 0.04069 | 1.862e-09 | 0.9444 | 0.3746 | 0.3746 | 0.8209 | 0.8209 | 23631 |
| ndvi | 12 | all | 2020 | 0.03988 | 0.03988 | 0.03988 | 0.03995 | 1.205e-09 | 0.9444 | 0.3884 | 0.3884 | 0.8333 | 0.8333 | 23630 |
| ndvi | 12 | all | 2021 | 0.03767 | 0.03767 | 0.03767 | 0.03837 | 1.268e-09 | 0.952 | 0.3972 | 0.3972 | 0.8341 | 0.8341 | 23633 |
| ndvi | 12 | all | 2022 | 0.04031 | 0.04031 | 0.04031 | 0.04112 | 2.277e-09 | 0.9427 | 0.3906 | 0.3906 | 0.8177 | 0.8177 | 23633 |
| ndvi | 12 | all | 2023 | 0.04047 | 0.04047 | 0.04047 | 0.04117 | 2.078e-09 | 0.9444 | 0.3743 | 0.3743 | 0.818 | 0.818 | 23631 |
| ndvi | 12 | common | 2020 | 0.03988 | 0.03988 | 0.03988 | 0.03995 | 1.205e-09 | 0.9444 | 0.3884 | 0.3884 | 0.8333 | 0.8333 | 23630 |
| ndvi | 12 | common | 2021 | 0.03767 | 0.03767 | 0.03767 | 0.03837 | 1.268e-09 | 0.952 | 0.3972 | 0.3972 | 0.8341 | 0.8341 | 23633 |
| ndvi | 12 | common | 2022 | 0.04031 | 0.04031 | 0.04031 | 0.04112 | 2.277e-09 | 0.9427 | 0.3906 | 0.3906 | 0.8177 | 0.8177 | 23633 |
| ndvi | 12 | common | 2023 | 0.04047 | 0.04047 | 0.04047 | 0.04117 | 2.078e-09 | 0.9444 | 0.3743 | 0.3743 | 0.818 | 0.818 | 23631 |

## Continuity row (the old hard-split test groups alone, same run): continuity, not a replication

| package | lead | rows | groups listed | groups scored | scored units | old test units | MAE adopted | MAE trees-off | MAE guess-normal | MAE last-5 | anomaly R2 | verdict | contrast | CI low | CI high | band | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ndvi | 0 | all | 44 | 44 | 660 | 4400 | 0.03241 | 0.04093 | 0.04093 | 0.04106 | 0.3242 | helps | 0.008472 | 0.006204 | 0.01074 | 0.0005975 | the package's band judges this row (R35); its jackknife is over these groups only |
| ndvi | 0 | common | 44 | 44 | 660 | 4400 | 0.03241 | 0.04093 | 0.04093 | 0.04106 | 0.3242 | helps | 0.008472 | 0.006204 | 0.01074 | 0.0005975 | the package's band judges this row (R35); its jackknife is over these groups only |
| ndvi | 6 | all | 44 | 44 | 660 | 4400 | 0.04113 | 0.04113 | 0.04113 | 0.04177 | 1.009e-09 | declined | 0 | 0 | 0 | 0.0005975 | the package's band judges this row (R35); its jackknife is over these groups only |
| ndvi | 6 | common | 44 | 44 | 660 | 4400 | 0.04113 | 0.04113 | 0.04113 | 0.04177 | 1.009e-09 | declined | 0 | 0 | 0 | 0.0005975 | the package's band judges this row (R35); its jackknife is over these groups only |
| ndvi | 12 | all | 44 | 44 | 660 | 4400 | 0.04111 | 0.04111 | 0.04111 | 0.04208 | 1.203e-09 | declined | 0 | 0 | 0 | 0.0005975 | the package's band judges this row (R35); its jackknife is over these groups only |
| ndvi | 12 | common | 44 | 44 | 660 | 4400 | 0.04111 | 0.04111 | 0.04111 | 0.04208 | 1.203e-09 | declined | 0 | 0 | 0 | 0.0005975 | the package's band judges this row (R35); its jackknife is over these groups only |

## Subset rows (reporting only)

| package | lead | rows | row | line | groups | MAE adopted | MAE trees-off | MAE guess-normal | MAE last-5 | anomaly R2 | corr2 | hit rate | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ndvi | 0 | all | without seen_during_design (Q49): greece_mainland, thar_desert | pooled | 131 | 0.03154 | 0.03941 | 0.03941 | 0.03938 | 0.3144 | 0.9632 | 0.4606 | n/a |
| ndvi | 0 | all | without seen_during_design (Q49): greece_mainland, thar_desert | macro | 131 | 0.03154 | 0.03938 | 0.03938 | 0.03935 | 0.2894 | 0.8652 | 0.461 | n/a |
| ndvi | 0 | all | 2021-2023 comparison row (Q40 a) | pooled | 133 | 0.03183 | 0.03936 | 0.03936 | 0.03951 | 0.3049 | 0.9629 | 0.4536 | n/a |
| ndvi | 0 | all | 2021-2023 comparison row (Q40 a) | macro | 133 | 0.03182 | 0.03931 | 0.03931 | 0.03945 | 0.2701 | 0.8617 | 0.4541 | n/a |
| ndvi | 0 | common | without seen_during_design (Q49): greece_mainland, thar_desert | pooled | 131 | 0.03154 | 0.03941 | 0.03941 | 0.03938 | 0.3144 | 0.9632 | 0.4606 | n/a |
| ndvi | 0 | common | without seen_during_design (Q49): greece_mainland, thar_desert | macro | 131 | 0.03154 | 0.03938 | 0.03938 | 0.03935 | 0.2894 | 0.8652 | 0.461 | n/a |
| ndvi | 0 | common | 2021-2023 comparison row (Q40 a) | pooled | 133 | 0.03183 | 0.03936 | 0.03936 | 0.03951 | 0.3049 | 0.9629 | 0.4536 | n/a |
| ndvi | 0 | common | 2021-2023 comparison row (Q40 a) | macro | 133 | 0.03182 | 0.03931 | 0.03931 | 0.03945 | 0.2701 | 0.8617 | 0.4541 | n/a |
| ndvi | 6 | all | without seen_during_design (Q49): greece_mainland, thar_desert | pooled | 131 | 0.03956 | 0.03956 | 0.03956 | 0.03987 | 1.489e-09 | 0.946 | 0.3885 | n/a |
| ndvi | 6 | all | without seen_during_design (Q49): greece_mainland, thar_desert | macro | 131 | 0.03953 | 0.03953 | 0.03953 | 0.03984 | 1.065e-07 | 0.8075 | 0.3893 | n/a |
| ndvi | 6 | all | 2021-2023 comparison row (Q40 a) | pooled | 133 | 0.0395 | 0.0395 | 0.0395 | 0.03994 | 1.595e-09 | 0.9462 | 0.3869 | n/a |
| ndvi | 6 | all | 2021-2023 comparison row (Q40 a) | macro | 133 | 0.03945 | 0.03945 | 0.03945 | 0.0399 | 1.089e-07 | 0.8083 | 0.3878 | n/a |
| ndvi | 6 | common | without seen_during_design (Q49): greece_mainland, thar_desert | pooled | 131 | 0.03956 | 0.03956 | 0.03956 | 0.03987 | 1.489e-09 | 0.946 | 0.3885 | n/a |
| ndvi | 6 | common | without seen_during_design (Q49): greece_mainland, thar_desert | macro | 131 | 0.03953 | 0.03953 | 0.03953 | 0.03984 | 1.065e-07 | 0.8075 | 0.3893 | n/a |
| ndvi | 6 | common | 2021-2023 comparison row (Q40 a) | pooled | 133 | 0.0395 | 0.0395 | 0.0395 | 0.03994 | 1.595e-09 | 0.9462 | 0.3869 | n/a |
| ndvi | 6 | common | 2021-2023 comparison row (Q40 a) | macro | 133 | 0.03945 | 0.03945 | 0.03945 | 0.0399 | 1.089e-07 | 0.8083 | 0.3878 | n/a |
| ndvi | 12 | all | without seen_during_design (Q49): greece_mainland, thar_desert | pooled | 131 | 0.03958 | 0.03958 | 0.03958 | 0.0402 | 1.788e-09 | 0.946 | 0.3884 | n/a |
| ndvi | 12 | all | without seen_during_design (Q49): greece_mainland, thar_desert | macro | 131 | 0.03955 | 0.03955 | 0.03955 | 0.04017 | 1.166e-07 | 0.8066 | 0.3892 | n/a |
| ndvi | 12 | all | 2021-2023 comparison row (Q40 a) | pooled | 133 | 0.03949 | 0.03949 | 0.03949 | 0.04022 | 1.902e-09 | 0.9463 | 0.3873 | n/a |
| ndvi | 12 | all | 2021-2023 comparison row (Q40 a) | macro | 133 | 0.03943 | 0.03943 | 0.03943 | 0.04017 | 1.193e-07 | 0.8077 | 0.3881 | n/a |
| ndvi | 12 | common | without seen_during_design (Q49): greece_mainland, thar_desert | pooled | 131 | 0.03958 | 0.03958 | 0.03958 | 0.0402 | 1.788e-09 | 0.946 | 0.3884 | n/a |
| ndvi | 12 | common | without seen_during_design (Q49): greece_mainland, thar_desert | macro | 131 | 0.03955 | 0.03955 | 0.03955 | 0.04017 | 1.166e-07 | 0.8066 | 0.3892 | n/a |
| ndvi | 12 | common | 2021-2023 comparison row (Q40 a) | pooled | 133 | 0.03949 | 0.03949 | 0.03949 | 0.04022 | 1.902e-09 | 0.9463 | 0.3873 | n/a |
| ndvi | 12 | common | 2021-2023 comparison row (Q40 a) | macro | 133 | 0.03943 | 0.03943 | 0.03943 | 0.04017 | 1.193e-07 | 0.8077 | 0.3881 | n/a |

## Per group (rows 'all')

Each group's score is noisy; the pooled headline and the all-group jackknife decide, never one group.

| package | lead | group | scored units | overlap block | MAE adopted | MAE trees-off | MAE guess-normal | MAE last-5 | contrast | anomaly R2 | hit rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ndvi | 0 | alaska_interior_taiga | 15 | alaska_interior_taiga | 0.04938 | 0.05739 | 0.05739 | 0.0574 | 0.008013 | 0.3015 | 0.3069 |
| ndvi | 0 | alaska_north_slope | 15 | alaska_north_slope | 0.03894 | 0.03843 | 0.03843 | 0.04701 | -0.0005009 | 0.07225 | 0.4229 |
| ndvi | 0 | amazon_basin_brazil | 15 | amazon_basin_brazil | 0.01995 | 0.02014 | 0.02014 | 0.02081 | 0.0001969 | -0.004977 | 0.5389 |
| ndvi | 0 | anatolian_plateau | 15 | anatolian_plateau | 0.02782 | 0.03382 | 0.03382 | 0.03048 | 0.005995 | 0.3081 | 0.4486 |
| ndvi | 0 | andes_puna | 15 | andes_puna+bolivia_beni_savanna | 0.01741 | 0.01937 | 0.01937 | 0.02008 | 0.001959 | 0.2148 | 0.6139 |
| ndvi | 0 | angola_zambia_fire_belt | 15 | angola_zambia_fire_belt+miombo_woodland_zambia | 0.02182 | 0.02232 | 0.02232 | 0.02363 | 0.0004964 | 0.04168 | 0.4972 |
| ndvi | 0 | arabian_peninsula | 15 | arabian_peninsula | 0.003927 | 0.004386 | 0.004386 | 0.004626 | 0.0004588 | 0.2972 | 0.9806 |
| ndvi | 0 | argentine_monte | 15 | argentine_monte | 0.02377 | 0.02318 | 0.02318 | 0.0244 | -0.0005884 | -0.2 | 0.5875 |
| ndvi | 0 | atacama_desert | 15 | atacama_desert | 0.004614 | 0.006076 | 0.006076 | 0.005116 | 0.001462 | 0.4445 | 0.9625 |
| ndvi | 0 | atlantic_forest_brazil | 14 | atlantic_forest_brazil | 0.02406 | 0.03345 | 0.03345 | 0.03626 | 0.009388 | 0.4339 | 0.4554 |
| ndvi | 0 | australian_bushfire_belt | 15 | australian_bushfire_belt | 0.03981 | 0.07233 | 0.07233 | 0.07302 | 0.03251 | 0.612 | 0.3069 |
| ndvi | 0 | australian_mulga | 15 | australian_mulga+brigalow_belt | 0.03085 | 0.0502 | 0.0502 | 0.0546 | 0.01935 | 0.5989 | 0.4333 |
| ndvi | 0 | bc_inland_rainforest | 15 | bc_inland_rainforest | 0.05073 | 0.05604 | 0.05604 | 0.06091 | 0.005309 | 0.2318 | 0.3347 |
| ndvi | 0 | bolivia_beni_savanna | 15 | andes_puna+bolivia_beni_savanna | 0.02534 | 0.02685 | 0.02685 | 0.02323 | 0.001504 | 0.1119 | 0.4514 |
| ndvi | 0 | borneo_peat_fires | 15 | borneo_peat_fires | 0.02518 | 0.03503 | 0.03503 | 0.02974 | 0.009854 | 0.4132 | 0.4417 |
| ndvi | 0 | borneo_rainforest | 15 | borneo_rainforest | 0.02333 | 0.02845 | 0.02845 | 0.0236 | 0.005123 | 0.2733 | 0.4417 |
| ndvi | 0 | brigalow_belt | 15 | australian_mulga+brigalow_belt | 0.03317 | 0.05507 | 0.05507 | 0.06084 | 0.0219 | 0.5487 | 0.4319 |
| ndvi | 0 | brittany_france | 15 | brittany_france | 0.02719 | 0.03512 | 0.03512 | 0.03109 | 0.007927 | 0.4038 | 0.3736 |
| ndvi | 0 | caatinga | 15 | caatinga | 0.05188 | 0.0712 | 0.0712 | 0.08468 | 0.01932 | 0.4418 | 0.2667 |
| ndvi | 0 | california_central_valley | 15 | california_central_valley+california_chaparral | 0.03149 | 0.04777 | 0.04777 | 0.04925 | 0.01628 | 0.5162 | 0.4542 |
| ndvi | 0 | california_chaparral | 15 | california_central_valley+california_chaparral | 0.01735 | 0.03076 | 0.03076 | 0.03049 | 0.01341 | 0.6867 | 0.6653 |
| ndvi | 0 | canadian_arctic_nunavut | 15 | canadian_arctic_nunavut | 0.02881 | 0.03111 | 0.03111 | 0.0312 | 0.002308 | 0.1267 | 0.5848 |
| ndvi | 0 | canadian_prairies | 15 | canadian_prairies | 0.04718 | 0.0616 | 0.0616 | 0.06787 | 0.01443 | 0.3341 | 0.2861 |
| ndvi | 0 | canadian_taiga | 15 | canadian_taiga | 0.05479 | 0.06379 | 0.06379 | 0.0602 | 0.009 | 0.1826 | 0.325 |
| ndvi | 0 | cape_floristic_region | 14 | cape_floristic_region+karoo | 0.01799 | 0.02635 | 0.02635 | 0.02905 | 0.008366 | 0.4507 | 0.6205 |
| ndvi | 0 | caucasus_highlands | 15 | caucasus_highlands | 0.04403 | 0.05389 | 0.05389 | 0.05261 | 0.00986 | 0.2979 | 0.2847 |
| ndvi | 0 | central_asia_amu_darya | 15 | central_asia_amu_darya | 0.008607 | 0.01088 | 0.01088 | 0.0111 | 0.002271 | 0.3465 | 0.8597 |
| ndvi | 0 | central_chile | 15 | central_chile | 0.0189 | 0.0352 | 0.0352 | 0.03748 | 0.0163 | 0.7034 | 0.5917 |
| ndvi | 0 | central_india_dry_forest | 15 | central_india_dry_forest | 0.04324 | 0.05908 | 0.05908 | 0.05383 | 0.01583 | 0.3626 | 0.3278 |
| ndvi | 0 | cerrado | 15 | cerrado | 0.03408 | 0.03383 | 0.03383 | 0.03198 | -0.000248 | 0.02476 | 0.3736 |
| ndvi | 0 | chihuahuan_desert | 15 | chihuahuan_desert | 0.01828 | 0.02771 | 0.02771 | 0.03141 | 0.009435 | 0.4653 | 0.6597 |
| ndvi | 0 | coastal_norway | 15 | coastal_norway | 0.05652 | 0.05822 | 0.05822 | 0.06386 | 0.0017 | 0.1715 | 0.3389 |
| ndvi | 0 | columbia_plateau | 15 | columbia_plateau | 0.0357 | 0.04556 | 0.04556 | 0.04694 | 0.009856 | 0.3454 | 0.4083 |
| ndvi | 0 | congo_basin_drc | 15 | congo_basin_drc | 0.02349 | 0.02324 | 0.02324 | 0.02438 | -0.0002501 | -0.06115 | 0.4444 |
| ndvi | 0 | costa_rica | 15 | costa_rica | 0.02212 | 0.02192 | 0.02192 | 0.02373 | -0.0002067 | -0.02238 | 0.525 |
| ndvi | 0 | drakensberg_lesotho | 15 | drakensberg_lesotho | 0.02685 | 0.0414 | 0.0414 | 0.05034 | 0.01454 | 0.565 | 0.4347 |
| ndvi | 0 | east_african_savanna | 15 | east_african_savanna | 0.03525 | 0.05247 | 0.05247 | 0.05517 | 0.01723 | 0.5108 | 0.3667 |
| ndvi | 0 | eastern_us_deciduous | 15 | eastern_us_deciduous | 0.02159 | 0.02315 | 0.02315 | 0.0218 | 0.001559 | 0.106 | 0.5042 |
| ndvi | 0 | ethiopian_highlands | 15 | ethiopian_highlands | 0.0374 | 0.04631 | 0.04631 | 0.04913 | 0.008909 | 0.3553 | 0.3333 |
| ndvi | 0 | eurasian_steppe | 15 | eurasian_steppe | 0.0375 | 0.04872 | 0.04872 | 0.05274 | 0.01122 | 0.3586 | 0.3944 |
| ndvi | 0 | falkland_islands | 15 | falkland_islands | 0.02438 | 0.02737 | 0.02737 | 0.02893 | 0.002988 | 0.1294 | 0.4597 |
| ndvi | 0 | finnish_lapland | 15 | finnish_lapland | 0.04594 | 0.04674 | 0.04674 | 0.04666 | 0.0007988 | 0.1381 | 0.3668 |
| ndvi | 0 | florida_everglades | 13 | florida_everglades | 0.02201 | 0.02676 | 0.02676 | 0.02413 | 0.00475 | 0.2912 | 0.4872 |
| ndvi | 0 | ganges_plain | 15 | ganges_plain | 0.04943 | 0.0644 | 0.0644 | 0.05827 | 0.01497 | 0.3541 | 0.2653 |
| ndvi | 0 | gobi_desert | 15 | gobi_desert | 0.007847 | 0.009719 | 0.009719 | 0.01109 | 0.001872 | 0.3127 | 0.8792 |
| ndvi | 0 | gran_chaco | 15 | gran_chaco | 0.05445 | 0.06624 | 0.06624 | 0.06789 | 0.01179 | 0.4009 | 0.1694 |
| ndvi | 0 | great_basin_sagebrush | 15 | great_basin_sagebrush | 0.02433 | 0.03648 | 0.03648 | 0.04011 | 0.01215 | 0.5376 | 0.55 |
| ndvi | 0 | great_plains | 15 | great_plains | 0.04609 | 0.05343 | 0.05343 | 0.05269 | 0.007342 | 0.2537 | 0.2569 |
| ndvi | 0 | great_sandy_desert_au | 15 | great_sandy_desert_au | 0.01309 | 0.02026 | 0.02026 | 0.02053 | 0.00717 | 0.5547 | 0.6778 |
| ndvi | 0 | greece_mainland | 15 | greece_mainland | 0.02697 | 0.0377 | 0.0377 | 0.03316 | 0.01073 | 0.4354 | 0.3917 |
| ndvi | 0 | greenland_west_coast | 15 | greenland_west_coast | 0.03339 | 0.03542 | 0.03542 | 0.04006 | 0.002024 | 0.1778 | 0.5 |
| ndvi | 0 | hulunbuir_grassland | 15 | hulunbuir_grassland | 0.04306 | 0.06387 | 0.06387 | 0.06 | 0.02081 | 0.4883 | 0.2889 |
| ndvi | 0 | hungarian_puszta | 15 | hungarian_puszta | 0.04223 | 0.06543 | 0.06543 | 0.05934 | 0.0232 | 0.5557 | 0.2833 |
| ndvi | 0 | iberian_wildfire | 15 | iberian_wildfire | 0.02951 | 0.04652 | 0.04652 | 0.04535 | 0.01701 | 0.5022 | 0.4167 |
| ndvi | 0 | idaho_montana_wildfire | 15 | idaho_montana_wildfire | 0.04837 | 0.05382 | 0.05382 | 0.05686 | 0.005445 | 0.2459 | 0.2583 |
| ndvi | 0 | indian_acacia_babool | 15 | indian_acacia_babool+thar_desert | 0.05168 | 0.0773 | 0.0773 | 0.06223 | 0.02561 | 0.4385 | 0.2819 |
| ndvi | 0 | indus_basin | 15 | indus_basin | 0.03198 | 0.04201 | 0.04201 | 0.03398 | 0.01003 | 0.3745 | 0.4014 |
| ndvi | 0 | iranian_plateau | 15 | iranian_plateau | 0.006981 | 0.008926 | 0.008926 | 0.00849 | 0.001945 | 0.4741 | 0.9097 |
| ndvi | 0 | ireland | 15 | ireland | 0.02719 | 0.03004 | 0.03004 | 0.02797 | 0.00285 | 0.1352 | 0.4319 |
| ndvi | 0 | japan_central_honshu | 15 | japan_central_honshu | 0.03463 | 0.04257 | 0.04257 | 0.03736 | 0.007936 | 0.3968 | 0.4181 |
| ndvi | 0 | kalahari_woodland | 15 | kalahari_woodland | 0.03659 | 0.05313 | 0.05313 | 0.05437 | 0.01655 | 0.4716 | 0.4167 |
| ndvi | 0 | karoo | 15 | cape_floristic_region+karoo | 0.01884 | 0.02999 | 0.02999 | 0.0324 | 0.01116 | 0.5579 | 0.6097 |
| ndvi | 0 | kazakh_steppe | 15 | kazakh_steppe | 0.04099 | 0.0483 | 0.0483 | 0.05761 | 0.007309 | 0.2243 | 0.3639 |
| ndvi | 0 | llanos_venezuela | 15 | llanos_venezuela | 0.03775 | 0.03478 | 0.03478 | 0.03717 | -0.002967 | -0.05782 | 0.2944 |
| ndvi | 0 | madagascar_spiny_thicket | 15 | madagascar_spiny_thicket | 0.0283 | 0.06075 | 0.06075 | 0.05344 | 0.03245 | 0.7546 | 0.4472 |
| ndvi | 0 | madagascar_western_dry | 15 | madagascar_western_dry | 0.01875 | 0.02976 | 0.02976 | 0.02734 | 0.01101 | 0.5703 | 0.5889 |
| ndvi | 0 | mediterranean_andalusia | 15 | mediterranean_andalusia | 0.02202 | 0.03104 | 0.03104 | 0.02984 | 0.009023 | 0.4927 | 0.4625 |
| ndvi | 0 | mekong_delta_vietnam | 15 | mekong_delta_vietnam | 0.05971 | 0.06786 | 0.06786 | 0.05967 | 0.008154 | 0.1884 | 0.2375 |
| ndvi | 0 | mesopotamia | 15 | mesopotamia | 0.02841 | 0.04366 | 0.04366 | 0.035 | 0.01525 | 0.5257 | 0.4917 |
| ndvi | 0 | mexican_altiplano | 15 | mexican_altiplano | 0.02514 | 0.03737 | 0.03737 | 0.04692 | 0.01223 | 0.475 | 0.5194 |
| ndvi | 0 | miombo_woodland_zambia | 15 | angola_zambia_fire_belt+miombo_woodland_zambia | 0.02594 | 0.02948 | 0.02948 | 0.02962 | 0.003545 | 0.1951 | 0.4806 |
| ndvi | 0 | mojave_desert | 15 | mojave_desert | 0.02061 | 0.02794 | 0.02794 | 0.02793 | 0.007327 | 0.3888 | 0.5861 |
| ndvi | 0 | mongolian_steppe | 15 | mongolian_steppe | 0.0359 | 0.04317 | 0.04317 | 0.04389 | 0.007269 | 0.2262 | 0.4306 |
| ndvi | 0 | mopane_woodland | 15 | mopane_woodland | 0.02813 | 0.03882 | 0.03882 | 0.04241 | 0.01069 | 0.4453 | 0.4292 |
| ndvi | 0 | myanmar_dry_zone | 15 | myanmar_dry_zone | 0.03656 | 0.04042 | 0.04042 | 0.04245 | 0.00386 | 0.1602 | 0.3986 |
| ndvi | 0 | namib_desert | 13 | namib_desert | 0.003317 | 0.002984 | 0.002984 | 0.003335 | -0.0003336 | -0.228 | 1 |
| ndvi | 0 | new_guinea_papua | 15 | new_guinea_papua | 0.01947 | 0.01948 | 0.01948 | 0.01967 | 9.586e-06 | 0.007925 | 0.5333 |
| ndvi | 0 | new_zealand_fiordland | 14 | new_zealand_fiordland | 0.03562 | 0.04307 | 0.04307 | 0.04137 | 0.007452 | 0.3276 | 0.375 |
| ndvi | 0 | new_zealand_north_island | 14 | new_zealand_north_island | 0.02194 | 0.03203 | 0.03203 | 0.03212 | 0.01009 | 0.5412 | 0.4896 |
| ndvi | 0 | niger_delta | 14 | niger_delta | 0.04478 | 0.04959 | 0.04959 | 0.04733 | 0.004809 | 0.1751 | 0.2604 |
| ndvi | 0 | nile_valley_delta | 15 | nile_valley_delta | 0.01018 | 0.01287 | 0.01287 | 0.009504 | 0.002693 | 0.3877 | 0.8194 |
| ndvi | 0 | north_algeria_tell_atlas | 15 | north_algeria_tell_atlas | 0.01964 | 0.03507 | 0.03507 | 0.03138 | 0.01543 | 0.6855 | 0.5472 |
| ndvi | 0 | north_china_plain | 15 | north_china_plain+ordos_plateau | 0.04345 | 0.05347 | 0.05347 | 0.04562 | 0.01001 | 0.288 | 0.2611 |
| ndvi | 0 | northeast_china_broadleaf | 15 | northeast_china_broadleaf | 0.03768 | 0.04199 | 0.04199 | 0.03617 | 0.004306 | 0.1187 | 0.3722 |
| ndvi | 0 | northern_australia_monsoon | 14 | northern_australia_monsoon | 0.02702 | 0.03623 | 0.03623 | 0.03106 | 0.009216 | 0.4244 | 0.4226 |
| ndvi | 0 | northern_australia_woodland | 15 | northern_australia_woodland | 0.02879 | 0.04248 | 0.04248 | 0.04189 | 0.01368 | 0.4855 | 0.4153 |
| ndvi | 0 | northern_thailand | 15 | northern_thailand | 0.02886 | 0.0395 | 0.0395 | 0.03888 | 0.01065 | 0.4818 | 0.4292 |
| ndvi | 0 | okavango_delta | 15 | okavango_delta | 0.03016 | 0.04275 | 0.04275 | 0.04732 | 0.01258 | 0.452 | 0.3889 |
| ndvi | 0 | ordos_plateau | 15 | north_china_plain+ordos_plateau | 0.02345 | 0.03334 | 0.03334 | 0.02565 | 0.00989 | 0.3448 | 0.5639 |
| ndvi | 0 | pacific_nw_coast | 15 | pacific_nw_coast | 0.02957 | 0.03599 | 0.03599 | 0.02962 | 0.006418 | 0.222 | 0.4222 |
| ndvi | 0 | pamir_plateau | 15 | pamir_plateau | 0.018 | 0.02008 | 0.02008 | 0.0198 | 0.002081 | 0.2565 | 0.6375 |
| ndvi | 0 | pampas | 15 | pampas+uruguay | 0.04872 | 0.06488 | 0.06488 | 0.06903 | 0.01616 | 0.4613 | 0.2389 |
| ndvi | 0 | pantanal | 15 | pantanal | 0.03645 | 0.0411 | 0.0411 | 0.04578 | 0.004645 | 0.2934 | 0.3208 |
| ndvi | 0 | patagonian_steppe | 15 | patagonian_steppe | 0.0195 | 0.02277 | 0.02277 | 0.02495 | 0.003268 | 0.2256 | 0.6639 |
| ndvi | 0 | pearl_river_delta | 15 | pearl_river_delta | 0.03087 | 0.04477 | 0.04477 | 0.03497 | 0.01391 | 0.4393 | 0.3639 |
| ndvi | 0 | poland_central | 15 | poland_central | 0.04852 | 0.06504 | 0.06504 | 0.05652 | 0.01652 | 0.3398 | 0.3 |
| ndvi | 0 | rub_al_khali | 15 | rub_al_khali | 0.003086 | 0.003264 | 0.003264 | 0.003324 | 0.0001775 | 0.1209 | 1 |
| ndvi | 0 | russian_far_east_primorye | 15 | russian_far_east_primorye | 0.04821 | 0.05264 | 0.05264 | 0.04779 | 0.004434 | 0.1044 | 0.3292 |
| ndvi | 0 | sahara_eastern | 15 | sahara_eastern | 0.002415 | 0.002187 | 0.002187 | 0.002517 | -0.0002281 | -0.1577 | 1 |
| ndvi | 0 | sahel | 15 | sahel | 0.02533 | 0.02716 | 0.02716 | 0.02645 | 0.001836 | 0.03839 | 0.5667 |
| ndvi | 0 | scandinavian_taiga | 15 | scandinavian_taiga | 0.04912 | 0.05373 | 0.05373 | 0.05399 | 0.004612 | 0.2661 | 0.3333 |
| ndvi | 0 | siberian_taiga | 15 | siberian_taiga | 0.04684 | 0.05133 | 0.05133 | 0.04854 | 0.004486 | 0.1831 | 0.3 |
| ndvi | 0 | sierra_nevada_foothills | 15 | sierra_nevada_foothills | 0.03669 | 0.04656 | 0.04656 | 0.05183 | 0.009873 | 0.2639 | 0.5514 |
| ndvi | 0 | southern_african_savanna | 15 | southern_african_savanna | 0.03672 | 0.05358 | 0.05358 | 0.06265 | 0.01686 | 0.4851 | 0.3403 |
| ndvi | 0 | southern_chile_rainforest | 15 | southern_chile_rainforest | 0.04829 | 0.05054 | 0.05054 | 0.05287 | 0.00225 | 0.08564 | 0.4028 |
| ndvi | 0 | spanish_meseta | 15 | spanish_meseta | 0.02464 | 0.03331 | 0.03331 | 0.03273 | 0.008668 | 0.4115 | 0.4611 |
| ndvi | 0 | sudanian_acacia | 15 | sudanian_acacia | 0.03549 | 0.03744 | 0.03744 | 0.03882 | 0.001952 | 0.01707 | 0.3847 |
| ndvi | 0 | sundarbans | 15 | sundarbans | 0.05063 | 0.05354 | 0.05354 | 0.0459 | 0.00291 | 0.0649 | 0.2302 |
| ndvi | 0 | sw_australia_kwongan | 15 | sw_australia_kwongan | 0.02869 | 0.04 | 0.04 | 0.0405 | 0.01131 | 0.5047 | 0.4333 |
| ndvi | 0 | taimyr_peninsula | 15 | taimyr_peninsula | 0.03226 | 0.03258 | 0.03258 | 0.0332 | 0.0003235 | 0.2319 | 0.4722 |
| ndvi | 0 | taklamakan_desert | 15 | taklamakan_desert | 0.002541 | 0.002712 | 0.002712 | 0.00282 | 0.0001717 | 0.1736 | 0.9958 |
| ndvi | 0 | tanezrouft | 15 | tanezrouft | 0.002625 | 0.002635 | 0.002635 | 0.002938 | 9.699e-06 | -0.02771 | 0.9986 |
| ndvi | 0 | tasmania_western | 15 | tasmania_western | 0.02714 | 0.03108 | 0.03108 | 0.03464 | 0.003935 | 0.1679 | 0.4125 |
| ndvi | 0 | thar_desert | 15 | indian_acacia_babool+thar_desert | 0.02597 | 0.04126 | 0.04126 | 0.03904 | 0.0153 | 0.5612 | 0.5319 |
| ndvi | 0 | tibetan_plateau | 15 | tibetan_plateau | 0.0334 | 0.04066 | 0.04066 | 0.04189 | 0.007264 | 0.2846 | 0.3819 |
| ndvi | 0 | tierra_del_fuego | 15 | tierra_del_fuego | 0.03866 | 0.04251 | 0.04251 | 0.04337 | 0.003853 | 0.01511 | 0.3597 |
| ndvi | 0 | tongass_alaska | 15 | tongass_alaska | 0.0788 | 0.07579 | 0.07579 | 0.1024 | -0.003019 | -0.006602 | 0.2142 |
| ndvi | 0 | trans_baikal_steppe | 15 | trans_baikal_steppe | 0.05804 | 0.06621 | 0.06621 | 0.06179 | 0.008167 | 0.1854 | 0.2681 |
| ndvi | 0 | tuva_steppe | 15 | tuva_steppe | 0.04139 | 0.04898 | 0.04898 | 0.04861 | 0.007596 | 0.1664 | 0.3907 |
| ndvi | 0 | uk_midlands | 15 | uk_midlands | 0.03342 | 0.04202 | 0.04202 | 0.04054 | 0.008599 | 0.3155 | 0.3375 |
| ndvi | 0 | uruguay | 15 | pampas+uruguay | 0.04459 | 0.05702 | 0.05702 | 0.0588 | 0.01243 | 0.4238 | 0.2458 |
| ndvi | 0 | us_corn_belt | 15 | us_corn_belt | 0.0383 | 0.04052 | 0.04052 | 0.0396 | 0.002222 | 0.02548 | 0.3958 |
| ndvi | 0 | vietnam_central_highlands | 15 | vietnam_central_highlands | 0.02748 | 0.03346 | 0.03346 | 0.03035 | 0.005982 | 0.3932 | 0.4 |
| ndvi | 0 | west_africa_cocoa_belt | 15 | west_africa_cocoa_belt | 0.03738 | 0.03553 | 0.03553 | 0.03362 | -0.001845 | -0.1156 | 0.2861 |
| ndvi | 0 | west_africa_monsoon_guinea | 15 | west_africa_monsoon_guinea | 0.02831 | 0.02837 | 0.02837 | 0.02905 | 5.772e-05 | 0.02016 | 0.3653 |
| ndvi | 0 | western_europe_farmlands | 15 | western_europe_farmlands | 0.03226 | 0.04447 | 0.04447 | 0.03624 | 0.01221 | 0.4108 | 0.3347 |
| ndvi | 0 | western_europe_temperate | 15 | western_europe_temperate | 0.03397 | 0.04573 | 0.04573 | 0.04252 | 0.01176 | 0.3883 | 0.35 |
| ndvi | 0 | western_ghats | 14 | western_ghats | 0.03626 | 0.05515 | 0.05515 | 0.0561 | 0.01889 | 0.5136 | 0.3006 |
| ndvi | 0 | western_sahara_coastal | 15 | western_sahara_coastal | 0.002996 | 0.00251 | 0.00251 | 0.005707 | -0.0004854 | -0.3995 | 0.9944 |
| ndvi | 0 | western_scotland | 15 | western_scotland | 0.04625 | 0.047 | 0.047 | 0.05085 | 0.0007502 | -0.01144 | 0.3528 |
| ndvi | 0 | yakutia_larch | 15 | yakutia_larch | 0.0455 | 0.04857 | 0.04857 | 0.05041 | 0.003062 | 0.1123 | 0.3542 |
| ndvi | 0 | yamal_peninsula | 14 | yamal_peninsula | 0.03617 | 0.04986 | 0.04986 | 0.04396 | 0.01369 | 0.5576 | 0.5054 |
| ndvi | 0 | yucatan_peninsula | 15 | yucatan_peninsula | 0.0307 | 0.03449 | 0.03449 | 0.03716 | 0.003789 | 0.2216 | 0.375 |
| ndvi | 6 | alaska_interior_taiga | 15 | alaska_interior_taiga | 0.05803 | 0.05803 | 0.05803 | 0.05903 | 0 | -5.694e-10 | 0.2889 |
| ndvi | 6 | alaska_north_slope | 15 | alaska_north_slope | 0.03803 | 0.03803 | 0.03803 | 0.04728 | 0 | -7.816e-10 | 0.4561 |
| ndvi | 6 | amazon_basin_brazil | 15 | amazon_basin_brazil | 0.02016 | 0.02016 | 0.02016 | 0.02085 | 0 | 4.253e-08 | 0.5292 |
| ndvi | 6 | anatolian_plateau | 15 | anatolian_plateau | 0.03431 | 0.03431 | 0.03431 | 0.03062 | 0 | 1.372e-09 | 0.375 |
| ndvi | 6 | andes_puna | 15 | andes_puna+bolivia_beni_savanna | 0.0193 | 0.0193 | 0.0193 | 0.01986 | 0 | 1.114e-09 | 0.5861 |
| ndvi | 6 | angola_zambia_fire_belt | 15 | angola_zambia_fire_belt+miombo_woodland_zambia | 0.02246 | 0.02246 | 0.02246 | 0.02381 | 0 | 1.516e-09 | 0.4972 |
| ndvi | 6 | arabian_peninsula | 15 | arabian_peninsula | 0.004406 | 0.004406 | 0.004406 | 0.004693 | 0 | 6.675e-07 | 0.9722 |
| ndvi | 6 | argentine_monte | 15 | argentine_monte | 0.02319 | 0.02319 | 0.02319 | 0.025 | 0 | -1.077e-08 | 0.5611 |
| ndvi | 6 | atacama_desert | 15 | atacama_desert | 0.006248 | 0.006248 | 0.006248 | 0.005164 | 0 | 5.032e-08 | 0.925 |
| ndvi | 6 | atlantic_forest_brazil | 14 | atlantic_forest_brazil | 0.03357 | 0.03357 | 0.03357 | 0.03668 | 0 | 3.576e-09 | 0.2991 |
| ndvi | 6 | australian_bushfire_belt | 15 | australian_bushfire_belt | 0.07141 | 0.07141 | 0.07141 | 0.06995 | 0 | 3.394e-10 | 0.1819 |
| ndvi | 6 | australian_mulga | 15 | australian_mulga+brigalow_belt | 0.04972 | 0.04972 | 0.04972 | 0.05353 | 0 | -3.33e-09 | 0.2875 |
| ndvi | 6 | bc_inland_rainforest | 15 | bc_inland_rainforest | 0.0554 | 0.0554 | 0.0554 | 0.0582 | 0 | 7.921e-11 | 0.3514 |
| ndvi | 6 | bolivia_beni_savanna | 15 | andes_puna+bolivia_beni_savanna | 0.02697 | 0.02697 | 0.02697 | 0.02343 | 0 | 1.478e-09 | 0.4403 |
| ndvi | 6 | borneo_peat_fires | 15 | borneo_peat_fires | 0.0355 | 0.0355 | 0.0355 | 0.03038 | 0 | 3.323e-08 | 0.3333 |
| ndvi | 6 | borneo_rainforest | 15 | borneo_rainforest | 0.0288 | 0.0288 | 0.0288 | 0.02379 | 0 | 1.671e-08 | 0.3639 |
| ndvi | 6 | brigalow_belt | 15 | australian_mulga+brigalow_belt | 0.05522 | 0.05522 | 0.05522 | 0.06181 | 0 | -5.228e-10 | 0.1972 |
| ndvi | 6 | brittany_france | 15 | brittany_france | 0.0353 | 0.0353 | 0.0353 | 0.03173 | 0 | 2.533e-08 | 0.2944 |
| ndvi | 6 | caatinga | 15 | caatinga | 0.071 | 0.071 | 0.071 | 0.08498 | 0 | 1.677e-10 | 0.2069 |
| ndvi | 6 | california_central_valley | 15 | california_central_valley+california_chaparral | 0.04772 | 0.04772 | 0.04772 | 0.04903 | 0 | 1.789e-09 | 0.3056 |
| ndvi | 6 | california_chaparral | 15 | california_central_valley+california_chaparral | 0.03082 | 0.03082 | 0.03082 | 0.03118 | 0 | 1.199e-08 | 0.4569 |
| ndvi | 6 | canadian_arctic_nunavut | 15 | canadian_arctic_nunavut | 0.03129 | 0.03129 | 0.03129 | 0.03203 | 0 | -7.075e-10 | 0.5545 |
| ndvi | 6 | canadian_prairies | 15 | canadian_prairies | 0.06102 | 0.06102 | 0.06102 | 0.06577 | 0 | 1.309e-11 | 0.1972 |
| ndvi | 6 | canadian_taiga | 15 | canadian_taiga | 0.06444 | 0.06444 | 0.06444 | 0.06105 | 0 | -5.088e-10 | 0.2764 |
| ndvi | 6 | cape_floristic_region | 14 | cape_floristic_region+karoo | 0.02649 | 0.02649 | 0.02649 | 0.0291 | 0 | 1.591e-08 | 0.4182 |
| ndvi | 6 | caucasus_highlands | 15 | caucasus_highlands | 0.05444 | 0.05444 | 0.05444 | 0.05413 | 0 | 2.164e-09 | 0.2667 |
| ndvi | 6 | central_asia_amu_darya | 15 | central_asia_amu_darya | 0.01084 | 0.01084 | 0.01084 | 0.01079 | 0 | 1.236e-07 | 0.7944 |
| ndvi | 6 | central_chile | 15 | central_chile | 0.0361 | 0.0361 | 0.0361 | 0.04089 | 0 | 9.525e-09 | 0.4069 |
| ndvi | 6 | central_india_dry_forest | 15 | central_india_dry_forest | 0.05987 | 0.05987 | 0.05987 | 0.05663 | 0 | 2.811e-10 | 0.1986 |
| ndvi | 6 | cerrado | 15 | cerrado | 0.03396 | 0.03396 | 0.03396 | 0.0319 | 0 | 2.521e-10 | 0.3625 |
| ndvi | 6 | chihuahuan_desert | 15 | chihuahuan_desert | 0.02782 | 0.02782 | 0.02782 | 0.03221 | 0 | 4.553e-09 | 0.4569 |
| ndvi | 6 | coastal_norway | 15 | coastal_norway | 0.05802 | 0.05802 | 0.05802 | 0.06385 | 0 | -3.232e-10 | 0.4139 |
| ndvi | 6 | columbia_plateau | 15 | columbia_plateau | 0.04566 | 0.04566 | 0.04566 | 0.04744 | 0 | 2.025e-09 | 0.325 |
| ndvi | 6 | congo_basin_drc | 15 | congo_basin_drc | 0.02324 | 0.02324 | 0.02324 | 0.02432 | 0 | 1.368e-08 | 0.4403 |
| ndvi | 6 | costa_rica | 15 | costa_rica | 0.0219 | 0.0219 | 0.0219 | 0.02397 | 0 | 3.299e-08 | 0.5083 |
| ndvi | 6 | drakensberg_lesotho | 15 | drakensberg_lesotho | 0.04108 | 0.04108 | 0.04108 | 0.04932 | 0 | -5.251e-09 | 0.3028 |
| ndvi | 6 | east_african_savanna | 15 | east_african_savanna | 0.05244 | 0.05244 | 0.05244 | 0.05511 | 0 | -3.2e-10 | 0.2444 |
| ndvi | 6 | eastern_us_deciduous | 15 | eastern_us_deciduous | 0.02318 | 0.02318 | 0.02318 | 0.02187 | 0 | 6.657e-10 | 0.4736 |
| ndvi | 6 | ethiopian_highlands | 15 | ethiopian_highlands | 0.04669 | 0.04669 | 0.04669 | 0.05101 | 0 | -9.633e-10 | 0.3028 |
| ndvi | 6 | eurasian_steppe | 15 | eurasian_steppe | 0.04893 | 0.04893 | 0.04893 | 0.05412 | 0 | 1.307e-09 | 0.3347 |
| ndvi | 6 | falkland_islands | 15 | falkland_islands | 0.02737 | 0.02737 | 0.02737 | 0.02907 | 0 | -1.471e-09 | 0.3972 |
| ndvi | 6 | finnish_lapland | 15 | finnish_lapland | 0.04728 | 0.04728 | 0.04728 | 0.04899 | 0 | -3.067e-10 | 0.3618 |
| ndvi | 6 | florida_everglades | 13 | florida_everglades | 0.02713 | 0.02713 | 0.02713 | 0.02479 | 0 | 7.939e-09 | 0.3926 |
| ndvi | 6 | ganges_plain | 15 | ganges_plain | 0.06499 | 0.06499 | 0.06499 | 0.0603 | 0 | -2.817e-10 | 0.1819 |
| ndvi | 6 | gobi_desert | 15 | gobi_desert | 0.0097 | 0.0097 | 0.0097 | 0.01138 | 0 | 1.581e-07 | 0.8083 |
| ndvi | 6 | gran_chaco | 15 | gran_chaco | 0.06652 | 0.06652 | 0.06652 | 0.06997 | 0 | -2.003e-09 | 0.1806 |
| ndvi | 6 | great_basin_sagebrush | 15 | great_basin_sagebrush | 0.03637 | 0.03637 | 0.03637 | 0.03996 | 0 | 3.941e-09 | 0.4 |
| ndvi | 6 | great_plains | 15 | great_plains | 0.05383 | 0.05383 | 0.05383 | 0.05265 | 0 | 1.139e-09 | 0.2361 |
| ndvi | 6 | great_sandy_desert_au | 15 | great_sandy_desert_au | 0.02035 | 0.02035 | 0.02035 | 0.02068 | 0 | 1.467e-09 | 0.475 |
| ndvi | 6 | greece_mainland | 15 | greece_mainland | 0.03822 | 0.03822 | 0.03822 | 0.03381 | 0 | 3.502e-09 | 0.2736 |
| ndvi | 6 | greenland_west_coast | 15 | greenland_west_coast | 0.03536 | 0.03536 | 0.03536 | 0.04084 | 0 | 1.627e-10 | 0.5101 |
| ndvi | 6 | hulunbuir_grassland | 15 | hulunbuir_grassland | 0.06451 | 0.06451 | 0.06451 | 0.06233 | 0 | -1.733e-09 | 0.2167 |
| ndvi | 6 | hungarian_puszta | 15 | hungarian_puszta | 0.06537 | 0.06537 | 0.06537 | 0.05913 | 0 | 3.548e-09 | 0.1972 |
| ndvi | 6 | iberian_wildfire | 15 | iberian_wildfire | 0.04653 | 0.04653 | 0.04653 | 0.04526 | 0 | -1.02e-09 | 0.2417 |
| ndvi | 6 | idaho_montana_wildfire | 15 | idaho_montana_wildfire | 0.05365 | 0.05365 | 0.05365 | 0.05651 | 0 | -1.55e-09 | 0.2431 |
| ndvi | 6 | indian_acacia_babool | 15 | indian_acacia_babool+thar_desert | 0.07839 | 0.07839 | 0.07839 | 0.0647 | 0 | -1.587e-10 | 0.1556 |
| ndvi | 6 | indus_basin | 15 | indus_basin | 0.0425 | 0.0425 | 0.0425 | 0.03464 | 0 | -1.511e-09 | 0.3236 |
| ndvi | 6 | iranian_plateau | 15 | iranian_plateau | 0.009047 | 0.009047 | 0.009047 | 0.008645 | 0 | -6.917e-09 | 0.8264 |
| ndvi | 6 | ireland | 15 | ireland | 0.03004 | 0.03004 | 0.03004 | 0.02806 | 0 | 1.64e-08 | 0.375 |
| ndvi | 6 | japan_central_honshu | 15 | japan_central_honshu | 0.04275 | 0.04275 | 0.04275 | 0.03805 | 0 | 1.253e-09 | 0.3708 |
| ndvi | 6 | kalahari_woodland | 15 | kalahari_woodland | 0.05305 | 0.05305 | 0.05305 | 0.05402 | 0 | -1.086e-08 | 0.2736 |
| ndvi | 6 | karoo | 15 | cape_floristic_region+karoo | 0.03014 | 0.03014 | 0.03014 | 0.0326 | 0 | 7.528e-09 | 0.3764 |
| ndvi | 6 | kazakh_steppe | 15 | kazakh_steppe | 0.04848 | 0.04848 | 0.04848 | 0.05954 | 0 | 1.08e-09 | 0.3125 |
| ndvi | 6 | llanos_venezuela | 15 | llanos_venezuela | 0.03499 | 0.03499 | 0.03499 | 0.03828 | 0 | -2.602e-11 | 0.35 |
| ndvi | 6 | madagascar_spiny_thicket | 15 | madagascar_spiny_thicket | 0.06042 | 0.06042 | 0.06042 | 0.05191 | 0 | 2.175e-09 | 0.1889 |
| ndvi | 6 | madagascar_western_dry | 15 | madagascar_western_dry | 0.02989 | 0.02989 | 0.02989 | 0.02746 | 0 | -1.158e-09 | 0.3819 |
| ndvi | 6 | mediterranean_andalusia | 15 | mediterranean_andalusia | 0.03118 | 0.03118 | 0.03118 | 0.03011 | 0 | 1.964e-09 | 0.3625 |
| ndvi | 6 | mekong_delta_vietnam | 15 | mekong_delta_vietnam | 0.06882 | 0.06882 | 0.06882 | 0.06137 | 0 | 3.753e-09 | 0.1764 |
| ndvi | 6 | mesopotamia | 15 | mesopotamia | 0.04424 | 0.04424 | 0.04424 | 0.03615 | 0 | -1.2e-08 | 0.2708 |
| ndvi | 6 | mexican_altiplano | 15 | mexican_altiplano | 0.03755 | 0.03755 | 0.03755 | 0.04845 | 0 | 5.593e-09 | 0.3403 |
| ndvi | 6 | miombo_woodland_zambia | 15 | angola_zambia_fire_belt+miombo_woodland_zambia | 0.02963 | 0.02963 | 0.02963 | 0.03001 | 0 | 1.146e-09 | 0.4056 |
| ndvi | 6 | mojave_desert | 15 | mojave_desert | 0.02796 | 0.02796 | 0.02796 | 0.02809 | 0 | 8.743e-09 | 0.4139 |
| ndvi | 6 | mongolian_steppe | 15 | mongolian_steppe | 0.0436 | 0.0436 | 0.0436 | 0.04584 | 0 | -2.362e-09 | 0.3292 |
| ndvi | 6 | mopane_woodland | 15 | mopane_woodland | 0.0389 | 0.0389 | 0.0389 | 0.04359 | 0 | -1.92e-09 | 0.3139 |
| ndvi | 6 | myanmar_dry_zone | 15 | myanmar_dry_zone | 0.04054 | 0.04054 | 0.04054 | 0.04293 | 0 | -4.171e-10 | 0.3431 |
| ndvi | 6 | namib_desert | 13 | namib_desert | 0.002979 | 0.002979 | 0.002979 | 0.003347 | 0 | 3.083e-06 | 1 |
| ndvi | 6 | new_guinea_papua | 15 | new_guinea_papua | 0.01948 | 0.01948 | 0.01948 | 0.02005 | 0 | 5.761e-08 | 0.5361 |
| ndvi | 6 | new_zealand_fiordland | 14 | new_zealand_fiordland | 0.04311 | 0.04311 | 0.04311 | 0.04119 | 0 | 3.044e-09 | 0.3646 |
| ndvi | 6 | new_zealand_north_island | 14 | new_zealand_north_island | 0.0322 | 0.0322 | 0.0322 | 0.0325 | 0 | -1.056e-08 | 0.3467 |
| ndvi | 6 | niger_delta | 14 | niger_delta | 0.04966 | 0.04966 | 0.04966 | 0.04781 | 0 | -4.653e-10 | 0.2292 |
| ndvi | 6 | nile_valley_delta | 15 | nile_valley_delta | 0.01299 | 0.01299 | 0.01299 | 0.009602 | 0 | -1.341e-08 | 0.7639 |
| ndvi | 6 | north_algeria_tell_atlas | 15 | north_algeria_tell_atlas | 0.03508 | 0.03508 | 0.03508 | 0.03124 | 0 | 1.172e-08 | 0.3778 |
| ndvi | 6 | north_china_plain | 15 | north_china_plain+ordos_plateau | 0.05397 | 0.05397 | 0.05397 | 0.04639 | 0 | 2.306e-09 | 0.2 |
| ndvi | 6 | northeast_china_broadleaf | 15 | northeast_china_broadleaf | 0.0423 | 0.0423 | 0.0423 | 0.03722 | 0 | 5.753e-10 | 0.2778 |
| ndvi | 6 | northern_australia_monsoon | 14 | northern_australia_monsoon | 0.0363 | 0.0363 | 0.0363 | 0.03099 | 0 | 3.776e-09 | 0.2961 |
| ndvi | 6 | northern_australia_woodland | 15 | northern_australia_woodland | 0.04273 | 0.04273 | 0.04273 | 0.04224 | 0 | 2.582e-11 | 0.2431 |
| ndvi | 6 | northern_thailand | 15 | northern_thailand | 0.03981 | 0.03981 | 0.03981 | 0.03938 | 0 | 2.03e-10 | 0.3667 |
| ndvi | 6 | okavango_delta | 15 | okavango_delta | 0.04329 | 0.04329 | 0.04329 | 0.04884 | 0 | -7.038e-09 | 0.2917 |
| ndvi | 6 | ordos_plateau | 15 | north_china_plain+ordos_plateau | 0.03381 | 0.03381 | 0.03381 | 0.02594 | 0 | -6.456e-09 | 0.3347 |
| ndvi | 6 | pacific_nw_coast | 15 | pacific_nw_coast | 0.03631 | 0.03631 | 0.03631 | 0.03013 | 0 | 1.094e-08 | 0.3306 |
| ndvi | 6 | pamir_plateau | 15 | pamir_plateau | 0.02009 | 0.02009 | 0.02009 | 0.01988 | 0 | 6.695e-09 | 0.6069 |
| ndvi | 6 | pampas | 15 | pampas+uruguay | 0.06508 | 0.06508 | 0.06508 | 0.07123 | 0 | 1.913e-09 | 0.1931 |
| ndvi | 6 | pantanal | 15 | pantanal | 0.04126 | 0.04126 | 0.04126 | 0.04705 | 0 | -7.772e-09 | 0.3319 |
| ndvi | 6 | patagonian_steppe | 15 | patagonian_steppe | 0.02281 | 0.02281 | 0.02281 | 0.02551 | 0 | -4.511e-09 | 0.5528 |
| ndvi | 6 | pearl_river_delta | 15 | pearl_river_delta | 0.04538 | 0.04538 | 0.04538 | 0.03578 | 0 | 2.986e-09 | 0.2181 |
| ndvi | 6 | poland_central | 15 | poland_central | 0.06526 | 0.06526 | 0.06526 | 0.05678 | 0 | 2.464e-09 | 0.2319 |
| ndvi | 6 | rub_al_khali | 15 | rub_al_khali | 0.003281 | 0.003281 | 0.003281 | 0.003351 | 0 | -3.211e-07 | 0.9986 |
| ndvi | 6 | russian_far_east_primorye | 15 | russian_far_east_primorye | 0.05279 | 0.05279 | 0.05279 | 0.04862 | 0 | 2.66e-10 | 0.2667 |
| ndvi | 6 | sahara_eastern | 15 | sahara_eastern | 0.002195 | 0.002195 | 0.002195 | 0.002556 | 0 | 2.89e-06 | 0.9986 |
| ndvi | 6 | sahel | 15 | sahel | 0.02738 | 0.02738 | 0.02738 | 0.0271 | 0 | -1.479e-08 | 0.4958 |
| ndvi | 6 | scandinavian_taiga | 15 | scandinavian_taiga | 0.05377 | 0.05377 | 0.05377 | 0.05444 | 0 | 1.818e-10 | 0.3506 |
| ndvi | 6 | siberian_taiga | 15 | siberian_taiga | 0.05168 | 0.05168 | 0.05168 | 0.04917 | 0 | -4.534e-10 | 0.3097 |
| ndvi | 6 | sierra_nevada_foothills | 15 | sierra_nevada_foothills | 0.04656 | 0.04656 | 0.04656 | 0.05169 | 0 | 3.44e-09 | 0.4458 |
| ndvi | 6 | southern_african_savanna | 15 | southern_african_savanna | 0.05352 | 0.05352 | 0.05352 | 0.06271 | 0 | -2.815e-09 | 0.2306 |
| ndvi | 6 | southern_chile_rainforest | 15 | southern_chile_rainforest | 0.05064 | 0.05064 | 0.05064 | 0.05336 | 0 | -2.573e-11 | 0.3917 |
| ndvi | 6 | spanish_meseta | 15 | spanish_meseta | 0.03338 | 0.03338 | 0.03338 | 0.03272 | 0 | 1.996e-09 | 0.3375 |
| ndvi | 6 | sudanian_acacia | 15 | sudanian_acacia | 0.03769 | 0.03769 | 0.03769 | 0.03994 | 0 | 8.75e-10 | 0.3389 |
| ndvi | 6 | sundarbans | 15 | sundarbans | 0.05401 | 0.05401 | 0.05401 | 0.04646 | 0 | 1.181e-09 | 0.1808 |
| ndvi | 6 | sw_australia_kwongan | 15 | sw_australia_kwongan | 0.03973 | 0.03973 | 0.03973 | 0.03989 | 0 | -2.85e-09 | 0.3583 |
| ndvi | 6 | taimyr_peninsula | 15 | taimyr_peninsula | 0.03312 | 0.03312 | 0.03312 | 0.03567 | 0 | -2.604e-09 | 0.5 |
| ndvi | 6 | taklamakan_desert | 15 | taklamakan_desert | 0.002722 | 0.002722 | 0.002722 | 0.00288 | 0 | 3.001e-06 | 0.9931 |
| ndvi | 6 | tanezrouft | 15 | tanezrouft | 0.002637 | 0.002637 | 0.002637 | 0.002957 | 0 | 1.363e-06 | 0.9986 |
| ndvi | 6 | tasmania_western | 15 | tasmania_western | 0.03103 | 0.03103 | 0.03103 | 0.03478 | 0 | 1.407e-08 | 0.375 |
| ndvi | 6 | thar_desert | 15 | indian_acacia_babool+thar_desert | 0.04179 | 0.04179 | 0.04179 | 0.04035 | 0 | -7.117e-09 | 0.3875 |
| ndvi | 6 | tibetan_plateau | 15 | tibetan_plateau | 0.04085 | 0.04085 | 0.04085 | 0.0426 | 0 | -4.109e-09 | 0.3097 |
| ndvi | 6 | tierra_del_fuego | 15 | tierra_del_fuego | 0.04258 | 0.04258 | 0.04258 | 0.04441 | 0 | -8.462e-11 | 0.2597 |
| ndvi | 6 | tongass_alaska | 15 | tongass_alaska | 0.07608 | 0.07608 | 0.07608 | 0.105 | 0 | -5.954e-10 | 0.2893 |
| ndvi | 6 | trans_baikal_steppe | 15 | trans_baikal_steppe | 0.06702 | 0.06702 | 0.06702 | 0.0642 | 0 | -4.094e-11 | 0.2208 |
| ndvi | 6 | tuva_steppe | 15 | tuva_steppe | 0.0491 | 0.0491 | 0.0491 | 0.04871 | 0 | -8.393e-10 | 0.3089 |
| ndvi | 6 | uk_midlands | 15 | uk_midlands | 0.04201 | 0.04201 | 0.04201 | 0.04043 | 0 | 8.732e-09 | 0.2708 |
| ndvi | 6 | uruguay | 15 | pampas+uruguay | 0.05698 | 0.05698 | 0.05698 | 0.05858 | 0 | -1.526e-09 | 0.1889 |
| ndvi | 6 | us_corn_belt | 15 | us_corn_belt | 0.04059 | 0.04059 | 0.04059 | 0.03976 | 0 | -2.25e-09 | 0.3417 |
| ndvi | 6 | vietnam_central_highlands | 15 | vietnam_central_highlands | 0.03355 | 0.03355 | 0.03355 | 0.03044 | 0 | 6.074e-09 | 0.3639 |
| ndvi | 6 | west_africa_cocoa_belt | 15 | west_africa_cocoa_belt | 0.03573 | 0.03573 | 0.03573 | 0.03416 | 0 | 2.187e-09 | 0.3 |
| ndvi | 6 | west_africa_monsoon_guinea | 15 | west_africa_monsoon_guinea | 0.02849 | 0.02849 | 0.02849 | 0.02963 | 0 | 1.175e-08 | 0.3625 |
| ndvi | 6 | western_europe_farmlands | 15 | western_europe_farmlands | 0.04474 | 0.04474 | 0.04474 | 0.0364 | 0 | 1.142e-08 | 0.2569 |
| ndvi | 6 | western_europe_temperate | 15 | western_europe_temperate | 0.04576 | 0.04576 | 0.04576 | 0.04228 | 0 | 8.07e-09 | 0.2486 |
| ndvi | 6 | western_ghats | 14 | western_ghats | 0.05559 | 0.05559 | 0.05559 | 0.05831 | 0 | 2.783e-10 | 0.1518 |
| ndvi | 6 | western_sahara_coastal | 15 | western_sahara_coastal | 0.002533 | 0.002533 | 0.002533 | 0.005883 | 0 | 2.614e-06 | 0.9958 |
| ndvi | 6 | western_scotland | 15 | western_scotland | 0.04705 | 0.04705 | 0.04705 | 0.05099 | 0 | -7.049e-10 | 0.3125 |
| ndvi | 6 | yakutia_larch | 15 | yakutia_larch | 0.04825 | 0.04825 | 0.04825 | 0.05019 | 0 | -1.561e-10 | 0.3819 |
| ndvi | 6 | yamal_peninsula | 14 | yamal_peninsula | 0.05036 | 0.05036 | 0.05036 | 0.04495 | 0 | 5.932e-11 | 0.4875 |
| ndvi | 6 | yucatan_peninsula | 15 | yucatan_peninsula | 0.0345 | 0.0345 | 0.0345 | 0.03734 | 0 | 5.826e-09 | 0.3667 |
| ndvi | 12 | alaska_interior_taiga | 15 | alaska_interior_taiga | 0.05721 | 0.05721 | 0.05721 | 0.05636 | 0 | -6.032e-10 | 0.2917 |
| ndvi | 12 | alaska_north_slope | 15 | alaska_north_slope | 0.0382 | 0.0382 | 0.0382 | 0.0472 | 0 | -7.401e-10 | 0.4594 |
| ndvi | 12 | amazon_basin_brazil | 15 | amazon_basin_brazil | 0.02038 | 0.02038 | 0.02038 | 0.02131 | 0 | 5.007e-08 | 0.525 |
| ndvi | 12 | anatolian_plateau | 15 | anatolian_plateau | 0.0345 | 0.0345 | 0.0345 | 0.03052 | 0 | 1.541e-09 | 0.3681 |
| ndvi | 12 | andes_puna | 15 | andes_puna+bolivia_beni_savanna | 0.01934 | 0.01934 | 0.01934 | 0.01981 | 0 | -7.654e-10 | 0.5889 |
| ndvi | 12 | angola_zambia_fire_belt | 15 | angola_zambia_fire_belt+miombo_woodland_zambia | 0.02253 | 0.02253 | 0.02253 | 0.02417 | 0 | 1.318e-09 | 0.4861 |
| ndvi | 12 | arabian_peninsula | 15 | arabian_peninsula | 0.004416 | 0.004416 | 0.004416 | 0.004778 | 0 | 6.518e-07 | 0.9708 |
| ndvi | 12 | argentine_monte | 15 | argentine_monte | 0.02351 | 0.02351 | 0.02351 | 0.02536 | 0 | -1.279e-08 | 0.5542 |
| ndvi | 12 | atacama_desert | 15 | atacama_desert | 0.006463 | 0.006463 | 0.006463 | 0.005354 | 0 | 1.765e-08 | 0.9194 |
| ndvi | 12 | atlantic_forest_brazil | 14 | atlantic_forest_brazil | 0.03365 | 0.03365 | 0.03365 | 0.03719 | 0 | 3.698e-09 | 0.2961 |
| ndvi | 12 | australian_bushfire_belt | 15 | australian_bushfire_belt | 0.07122 | 0.07122 | 0.07122 | 0.06921 | 0 | 4.9e-10 | 0.1875 |
| ndvi | 12 | australian_mulga | 15 | australian_mulga+brigalow_belt | 0.04945 | 0.04945 | 0.04945 | 0.0529 | 0 | -2.032e-09 | 0.2847 |
| ndvi | 12 | bc_inland_rainforest | 15 | bc_inland_rainforest | 0.05591 | 0.05591 | 0.05591 | 0.05855 | 0 | 1.845e-10 | 0.3389 |
| ndvi | 12 | bolivia_beni_savanna | 15 | andes_puna+bolivia_beni_savanna | 0.0272 | 0.0272 | 0.0272 | 0.02376 | 0 | 3.112e-09 | 0.4389 |
| ndvi | 12 | borneo_peat_fires | 15 | borneo_peat_fires | 0.03605 | 0.03605 | 0.03605 | 0.03125 | 0 | 3.405e-08 | 0.3264 |
| ndvi | 12 | borneo_rainforest | 15 | borneo_rainforest | 0.02933 | 0.02933 | 0.02933 | 0.0244 | 0 | 2.572e-08 | 0.3528 |
| ndvi | 12 | brigalow_belt | 15 | australian_mulga+brigalow_belt | 0.05509 | 0.05509 | 0.05509 | 0.0621 | 0 | 1.035e-09 | 0.2014 |
| ndvi | 12 | brittany_france | 15 | brittany_france | 0.03516 | 0.03516 | 0.03516 | 0.03206 | 0 | 2.727e-08 | 0.2958 |
| ndvi | 12 | caatinga | 15 | caatinga | 0.07132 | 0.07132 | 0.07132 | 0.08728 | 0 | -1.341e-10 | 0.1986 |
| ndvi | 12 | california_central_valley | 15 | california_central_valley+california_chaparral | 0.04729 | 0.04729 | 0.04729 | 0.04836 | 0 | 1.759e-09 | 0.3083 |
| ndvi | 12 | california_chaparral | 15 | california_central_valley+california_chaparral | 0.03092 | 0.03092 | 0.03092 | 0.03164 | 0 | 1.235e-08 | 0.4639 |
| ndvi | 12 | canadian_arctic_nunavut | 15 | canadian_arctic_nunavut | 0.03111 | 0.03111 | 0.03111 | 0.03234 | 0 | -6.671e-10 | 0.553 |
| ndvi | 12 | canadian_prairies | 15 | canadian_prairies | 0.06115 | 0.06115 | 0.06115 | 0.06791 | 0 | 4.867e-11 | 0.1972 |
| ndvi | 12 | canadian_taiga | 15 | canadian_taiga | 0.06481 | 0.06481 | 0.06481 | 0.06209 | 0 | -5.429e-10 | 0.2653 |
| ndvi | 12 | cape_floristic_region | 14 | cape_floristic_region+karoo | 0.02651 | 0.02651 | 0.02651 | 0.02934 | 0 | 1.697e-08 | 0.4241 |
| ndvi | 12 | caucasus_highlands | 15 | caucasus_highlands | 0.05422 | 0.05422 | 0.05422 | 0.05475 | 0 | 2.552e-09 | 0.2569 |
| ndvi | 12 | central_asia_amu_darya | 15 | central_asia_amu_darya | 0.01065 | 0.01065 | 0.01065 | 0.01008 | 0 | 1.383e-07 | 0.8028 |
| ndvi | 12 | central_chile | 15 | central_chile | 0.03606 | 0.03606 | 0.03606 | 0.04308 | 0 | 9.273e-09 | 0.4083 |
| ndvi | 12 | central_india_dry_forest | 15 | central_india_dry_forest | 0.05978 | 0.05978 | 0.05978 | 0.05691 | 0 | 5.81e-10 | 0.2014 |
| ndvi | 12 | cerrado | 15 | cerrado | 0.03411 | 0.03411 | 0.03411 | 0.03222 | 0 | 1.684e-10 | 0.3736 |
| ndvi | 12 | chihuahuan_desert | 15 | chihuahuan_desert | 0.02796 | 0.02796 | 0.02796 | 0.03227 | 0 | 4.202e-09 | 0.4653 |
| ndvi | 12 | coastal_norway | 15 | coastal_norway | 0.0586 | 0.0586 | 0.0586 | 0.06513 | 0 | -3.031e-10 | 0.4167 |
| ndvi | 12 | columbia_plateau | 15 | columbia_plateau | 0.04566 | 0.04566 | 0.04566 | 0.04913 | 0 | 2.603e-09 | 0.3264 |
| ndvi | 12 | congo_basin_drc | 15 | congo_basin_drc | 0.02337 | 0.02337 | 0.02337 | 0.02467 | 0 | 1.802e-08 | 0.4375 |
| ndvi | 12 | costa_rica | 15 | costa_rica | 0.02165 | 0.02165 | 0.02165 | 0.02386 | 0 | 3.66e-08 | 0.5097 |
| ndvi | 12 | drakensberg_lesotho | 15 | drakensberg_lesotho | 0.04083 | 0.04083 | 0.04083 | 0.04838 | 0 | -6.13e-09 | 0.2917 |
| ndvi | 12 | east_african_savanna | 15 | east_african_savanna | 0.05257 | 0.05257 | 0.05257 | 0.0544 | 0 | -4.112e-10 | 0.2486 |
| ndvi | 12 | eastern_us_deciduous | 15 | eastern_us_deciduous | 0.02356 | 0.02356 | 0.02356 | 0.02214 | 0 | 7.931e-10 | 0.4722 |
| ndvi | 12 | ethiopian_highlands | 15 | ethiopian_highlands | 0.04672 | 0.04672 | 0.04672 | 0.05129 | 0 | -7.94e-10 | 0.3069 |
| ndvi | 12 | eurasian_steppe | 15 | eurasian_steppe | 0.04869 | 0.04869 | 0.04869 | 0.05472 | 0 | 1.374e-09 | 0.3389 |
| ndvi | 12 | falkland_islands | 15 | falkland_islands | 0.02738 | 0.02738 | 0.02738 | 0.02912 | 0 | -2.25e-10 | 0.3986 |
| ndvi | 12 | finnish_lapland | 15 | finnish_lapland | 0.04738 | 0.04738 | 0.04738 | 0.04912 | 0 | -3.649e-10 | 0.3602 |
| ndvi | 12 | florida_everglades | 13 | florida_everglades | 0.02769 | 0.02769 | 0.02769 | 0.02569 | 0 | 9.833e-09 | 0.3814 |
| ndvi | 12 | ganges_plain | 15 | ganges_plain | 0.06478 | 0.06478 | 0.06478 | 0.06117 | 0 | -1.466e-10 | 0.1806 |
| ndvi | 12 | gobi_desert | 15 | gobi_desert | 0.009643 | 0.009643 | 0.009643 | 0.01161 | 0 | 1.642e-07 | 0.8139 |
| ndvi | 12 | gran_chaco | 15 | gran_chaco | 0.06633 | 0.06633 | 0.06633 | 0.06909 | 0 | -1.878e-09 | 0.1792 |
| ndvi | 12 | great_basin_sagebrush | 15 | great_basin_sagebrush | 0.03635 | 0.03635 | 0.03635 | 0.04141 | 0 | 5.118e-09 | 0.3903 |
| ndvi | 12 | great_plains | 15 | great_plains | 0.05339 | 0.05339 | 0.05339 | 0.05362 | 0 | 7.992e-10 | 0.2375 |
| ndvi | 12 | great_sandy_desert_au | 15 | great_sandy_desert_au | 0.02023 | 0.02023 | 0.02023 | 0.02087 | 0 | 9.107e-09 | 0.4889 |
| ndvi | 12 | greece_mainland | 15 | greece_mainland | 0.03822 | 0.03822 | 0.03822 | 0.03421 | 0 | 3.969e-09 | 0.2736 |
| ndvi | 12 | greenland_west_coast | 15 | greenland_west_coast | 0.03467 | 0.03467 | 0.03467 | 0.03913 | 0 | 9.654e-11 | 0.5116 |
| ndvi | 12 | hulunbuir_grassland | 15 | hulunbuir_grassland | 0.06519 | 0.06519 | 0.06519 | 0.06313 | 0 | -1.44e-09 | 0.2139 |
| ndvi | 12 | hungarian_puszta | 15 | hungarian_puszta | 0.06316 | 0.06316 | 0.06316 | 0.0572 | 0 | 3.717e-09 | 0.2042 |
| ndvi | 12 | iberian_wildfire | 15 | iberian_wildfire | 0.04687 | 0.04687 | 0.04687 | 0.0452 | 0 | -1.534e-09 | 0.2375 |
| ndvi | 12 | idaho_montana_wildfire | 15 | idaho_montana_wildfire | 0.05352 | 0.05352 | 0.05352 | 0.05897 | 0 | -1.638e-09 | 0.2611 |
| ndvi | 12 | indian_acacia_babool | 15 | indian_acacia_babool+thar_desert | 0.07745 | 0.07745 | 0.07745 | 0.06602 | 0 | -3.029e-11 | 0.1653 |
| ndvi | 12 | indus_basin | 15 | indus_basin | 0.04241 | 0.04241 | 0.04241 | 0.03531 | 0 | -9.88e-10 | 0.3264 |
| ndvi | 12 | iranian_plateau | 15 | iranian_plateau | 0.009073 | 0.009073 | 0.009073 | 0.008762 | 0 | -2.724e-08 | 0.8236 |
| ndvi | 12 | ireland | 15 | ireland | 0.03085 | 0.03085 | 0.03085 | 0.02915 | 0 | 1.81e-08 | 0.3569 |
| ndvi | 12 | japan_central_honshu | 15 | japan_central_honshu | 0.04334 | 0.04334 | 0.04334 | 0.03908 | 0 | 1.457e-09 | 0.375 |
| ndvi | 12 | kalahari_woodland | 15 | kalahari_woodland | 0.05061 | 0.05061 | 0.05061 | 0.05113 | 0 | -1.128e-08 | 0.2736 |
| ndvi | 12 | karoo | 15 | cape_floristic_region+karoo | 0.03017 | 0.03017 | 0.03017 | 0.03231 | 0 | 8.499e-09 | 0.3694 |
| ndvi | 12 | kazakh_steppe | 15 | kazakh_steppe | 0.04889 | 0.04889 | 0.04889 | 0.06114 | 0 | 1.21e-09 | 0.3069 |
| ndvi | 12 | llanos_venezuela | 15 | llanos_venezuela | 0.03496 | 0.03496 | 0.03496 | 0.03862 | 0 | -7.73e-11 | 0.3542 |
| ndvi | 12 | madagascar_spiny_thicket | 15 | madagascar_spiny_thicket | 0.0599 | 0.0599 | 0.0599 | 0.05021 | 0 | 2.644e-09 | 0.1944 |
| ndvi | 12 | madagascar_western_dry | 15 | madagascar_western_dry | 0.02993 | 0.02993 | 0.02993 | 0.02779 | 0 | -9.471e-10 | 0.3847 |
| ndvi | 12 | mediterranean_andalusia | 15 | mediterranean_andalusia | 0.03132 | 0.03132 | 0.03132 | 0.03126 | 0 | 1.745e-09 | 0.3597 |
| ndvi | 12 | mekong_delta_vietnam | 15 | mekong_delta_vietnam | 0.06895 | 0.06895 | 0.06895 | 0.06258 | 0 | 4.05e-09 | 0.1861 |
| ndvi | 12 | mesopotamia | 15 | mesopotamia | 0.04636 | 0.04636 | 0.04636 | 0.03917 | 0 | -1.567e-08 | 0.2681 |
| ndvi | 12 | mexican_altiplano | 15 | mexican_altiplano | 0.03778 | 0.03778 | 0.03778 | 0.05002 | 0 | 5.295e-09 | 0.3375 |
| ndvi | 12 | miombo_woodland_zambia | 15 | angola_zambia_fire_belt+miombo_woodland_zambia | 0.0296 | 0.0296 | 0.0296 | 0.03075 | 0 | 1.022e-09 | 0.4042 |
| ndvi | 12 | mojave_desert | 15 | mojave_desert | 0.02799 | 0.02799 | 0.02799 | 0.02856 | 0 | 1.021e-08 | 0.4181 |
| ndvi | 12 | mongolian_steppe | 15 | mongolian_steppe | 0.04336 | 0.04336 | 0.04336 | 0.04539 | 0 | -2.274e-09 | 0.3306 |
| ndvi | 12 | mopane_woodland | 15 | mopane_woodland | 0.03854 | 0.03854 | 0.03854 | 0.04593 | 0 | -1.403e-09 | 0.3278 |
| ndvi | 12 | myanmar_dry_zone | 15 | myanmar_dry_zone | 0.04036 | 0.04036 | 0.04036 | 0.04249 | 0 | -1.973e-10 | 0.35 |
| ndvi | 12 | namib_desert | 13 | namib_desert | 0.003023 | 0.003023 | 0.003023 | 0.003396 | 0 | 3.232e-06 | 1 |
| ndvi | 12 | new_guinea_papua | 15 | new_guinea_papua | 0.01959 | 0.01959 | 0.01959 | 0.02013 | 0 | 6.027e-08 | 0.5361 |
| ndvi | 12 | new_zealand_fiordland | 14 | new_zealand_fiordland | 0.04347 | 0.04347 | 0.04347 | 0.04213 | 0 | 3.57e-09 | 0.3616 |
| ndvi | 12 | new_zealand_north_island | 14 | new_zealand_north_island | 0.03252 | 0.03252 | 0.03252 | 0.03432 | 0 | -1.38e-08 | 0.3438 |
| ndvi | 12 | niger_delta | 14 | niger_delta | 0.04963 | 0.04963 | 0.04963 | 0.04745 | 0 | -4.804e-10 | 0.2292 |
| ndvi | 12 | nile_valley_delta | 15 | nile_valley_delta | 0.01297 | 0.01297 | 0.01297 | 0.009669 | 0 | -1.343e-08 | 0.7653 |
| ndvi | 12 | north_algeria_tell_atlas | 15 | north_algeria_tell_atlas | 0.0355 | 0.0355 | 0.0355 | 0.03011 | 0 | 1.334e-08 | 0.3722 |
| ndvi | 12 | north_china_plain | 15 | north_china_plain+ordos_plateau | 0.05407 | 0.05407 | 0.05407 | 0.04781 | 0 | 2.427e-09 | 0.2042 |
| ndvi | 12 | northeast_china_broadleaf | 15 | northeast_china_broadleaf | 0.04298 | 0.04298 | 0.04298 | 0.03795 | 0 | 8.213e-10 | 0.2806 |
| ndvi | 12 | northern_australia_monsoon | 14 | northern_australia_monsoon | 0.03657 | 0.03657 | 0.03657 | 0.03146 | 0 | 3.376e-09 | 0.2917 |
| ndvi | 12 | northern_australia_woodland | 15 | northern_australia_woodland | 0.04299 | 0.04299 | 0.04299 | 0.04299 | 0 | 1.642e-09 | 0.2431 |
| ndvi | 12 | northern_thailand | 15 | northern_thailand | 0.03971 | 0.03971 | 0.03971 | 0.03939 | 0 | 5.683e-10 | 0.375 |
| ndvi | 12 | okavango_delta | 15 | okavango_delta | 0.04199 | 0.04199 | 0.04199 | 0.04804 | 0 | -5.661e-09 | 0.2972 |
| ndvi | 12 | ordos_plateau | 15 | north_china_plain+ordos_plateau | 0.03392 | 0.03392 | 0.03392 | 0.02617 | 0 | -6.181e-09 | 0.3208 |
| ndvi | 12 | pacific_nw_coast | 15 | pacific_nw_coast | 0.03711 | 0.03711 | 0.03711 | 0.03103 | 0 | 1.281e-08 | 0.3264 |
| ndvi | 12 | pamir_plateau | 15 | pamir_plateau | 0.02005 | 0.02005 | 0.02005 | 0.02006 | 0 | 6.587e-09 | 0.6111 |
| ndvi | 12 | pampas | 15 | pampas+uruguay | 0.06472 | 0.06472 | 0.06472 | 0.07165 | 0 | 2.045e-09 | 0.1944 |
| ndvi | 12 | pantanal | 15 | pantanal | 0.04143 | 0.04143 | 0.04143 | 0.04718 | 0 | -7.891e-09 | 0.3222 |
| ndvi | 12 | patagonian_steppe | 15 | patagonian_steppe | 0.02252 | 0.02252 | 0.02252 | 0.0256 | 0 | -3.301e-09 | 0.5569 |
| ndvi | 12 | pearl_river_delta | 15 | pearl_river_delta | 0.04575 | 0.04575 | 0.04575 | 0.03669 | 0 | 4.046e-09 | 0.2153 |
| ndvi | 12 | poland_central | 15 | poland_central | 0.06604 | 0.06604 | 0.06604 | 0.05794 | 0 | 2.899e-09 | 0.2278 |
| ndvi | 12 | rub_al_khali | 15 | rub_al_khali | 0.003295 | 0.003295 | 0.003295 | 0.00339 | 0 | -3.029e-07 | 0.9986 |
| ndvi | 12 | russian_far_east_primorye | 15 | russian_far_east_primorye | 0.05286 | 0.05286 | 0.05286 | 0.04696 | 0 | 4.209e-10 | 0.2778 |
| ndvi | 12 | sahara_eastern | 15 | sahara_eastern | 0.002217 | 0.002217 | 0.002217 | 0.002599 | 0 | 3.203e-06 | 0.9972 |
| ndvi | 12 | sahel | 15 | sahel | 0.02738 | 0.02738 | 0.02738 | 0.02751 | 0 | -1.422e-08 | 0.4931 |
| ndvi | 12 | scandinavian_taiga | 15 | scandinavian_taiga | 0.0546 | 0.0546 | 0.0546 | 0.05498 | 0 | 1.727e-10 | 0.3376 |
| ndvi | 12 | siberian_taiga | 15 | siberian_taiga | 0.05153 | 0.05153 | 0.05153 | 0.0486 | 0 | -4.966e-10 | 0.3125 |
| ndvi | 12 | sierra_nevada_foothills | 15 | sierra_nevada_foothills | 0.0466 | 0.0466 | 0.0466 | 0.05327 | 0 | 3.709e-09 | 0.4514 |
| ndvi | 12 | southern_african_savanna | 15 | southern_african_savanna | 0.05239 | 0.05239 | 0.05239 | 0.06359 | 0 | -2.517e-09 | 0.225 |
| ndvi | 12 | southern_chile_rainforest | 15 | southern_chile_rainforest | 0.05088 | 0.05088 | 0.05088 | 0.05433 | 0 | 2.48e-10 | 0.3917 |
| ndvi | 12 | spanish_meseta | 15 | spanish_meseta | 0.03326 | 0.03326 | 0.03326 | 0.03258 | 0 | 2.344e-09 | 0.3458 |
| ndvi | 12 | sudanian_acacia | 15 | sudanian_acacia | 0.03738 | 0.03738 | 0.03738 | 0.03972 | 0 | 1.044e-09 | 0.3458 |
| ndvi | 12 | sundarbans | 15 | sundarbans | 0.05429 | 0.05429 | 0.05429 | 0.04713 | 0 | 1.699e-09 | 0.1879 |
| ndvi | 12 | sw_australia_kwongan | 15 | sw_australia_kwongan | 0.03982 | 0.03982 | 0.03982 | 0.0401 | 0 | -2.827e-09 | 0.3611 |
| ndvi | 12 | taimyr_peninsula | 15 | taimyr_peninsula | 0.03336 | 0.03336 | 0.03336 | 0.03569 | 0 | -2.719e-09 | 0.4981 |
| ndvi | 12 | taklamakan_desert | 15 | taklamakan_desert | 0.002724 | 0.002724 | 0.002724 | 0.002819 | 0 | 3.294e-06 | 0.9917 |
| ndvi | 12 | tanezrouft | 15 | tanezrouft | 0.002646 | 0.002646 | 0.002646 | 0.002923 | 0 | 1.481e-06 | 0.9986 |
| ndvi | 12 | tasmania_western | 15 | tasmania_western | 0.0311 | 0.0311 | 0.0311 | 0.03535 | 0 | 1.588e-08 | 0.3764 |
| ndvi | 12 | thar_desert | 15 | indian_acacia_babool+thar_desert | 0.04116 | 0.04116 | 0.04116 | 0.04006 | 0 | -7.291e-09 | 0.4028 |
| ndvi | 12 | tibetan_plateau | 15 | tibetan_plateau | 0.04069 | 0.04069 | 0.04069 | 0.04208 | 0 | -4.254e-09 | 0.3208 |
| ndvi | 12 | tierra_del_fuego | 15 | tierra_del_fuego | 0.04266 | 0.04266 | 0.04266 | 0.04447 | 0 | 1.474e-10 | 0.2653 |
| ndvi | 12 | tongass_alaska | 15 | tongass_alaska | 0.07457 | 0.07457 | 0.07457 | 0.1044 | 0 | -5.633e-10 | 0.2796 |
| ndvi | 12 | trans_baikal_steppe | 15 | trans_baikal_steppe | 0.06807 | 0.06807 | 0.06807 | 0.06559 | 0 | 1.392e-10 | 0.2139 |
| ndvi | 12 | tuva_steppe | 15 | tuva_steppe | 0.04905 | 0.04905 | 0.04905 | 0.04832 | 0 | -7.781e-10 | 0.3032 |
| ndvi | 12 | uk_midlands | 15 | uk_midlands | 0.04211 | 0.04211 | 0.04211 | 0.04032 | 0 | 9.687e-09 | 0.2653 |
| ndvi | 12 | uruguay | 15 | pampas+uruguay | 0.0571 | 0.0571 | 0.0571 | 0.05861 | 0 | -2.152e-09 | 0.1833 |
| ndvi | 12 | us_corn_belt | 15 | us_corn_belt | 0.0405 | 0.0405 | 0.0405 | 0.04007 | 0 | -2.32e-09 | 0.3431 |
| ndvi | 12 | vietnam_central_highlands | 15 | vietnam_central_highlands | 0.03381 | 0.03381 | 0.03381 | 0.03087 | 0 | 6.99e-09 | 0.3597 |
| ndvi | 12 | west_africa_cocoa_belt | 15 | west_africa_cocoa_belt | 0.03609 | 0.03609 | 0.03609 | 0.03548 | 0 | 2.595e-09 | 0.2931 |
| ndvi | 12 | west_africa_monsoon_guinea | 15 | west_africa_monsoon_guinea | 0.02898 | 0.02898 | 0.02898 | 0.03041 | 0 | 1.398e-08 | 0.3597 |
| ndvi | 12 | western_europe_farmlands | 15 | western_europe_farmlands | 0.04491 | 0.04491 | 0.04491 | 0.03779 | 0 | 1.253e-08 | 0.2556 |
| ndvi | 12 | western_europe_temperate | 15 | western_europe_temperate | 0.04564 | 0.04564 | 0.04564 | 0.04264 | 0 | 8.974e-09 | 0.2472 |
| ndvi | 12 | western_ghats | 14 | western_ghats | 0.05463 | 0.05463 | 0.05463 | 0.057 | 0 | 7.862e-10 | 0.1592 |
| ndvi | 12 | western_sahara_coastal | 15 | western_sahara_coastal | 0.002577 | 0.002577 | 0.002577 | 0.00628 | 0 | 3.03e-06 | 0.9958 |
| ndvi | 12 | western_scotland | 15 | western_scotland | 0.04773 | 0.04773 | 0.04773 | 0.05338 | 0 | -4.618e-10 | 0.3014 |
| ndvi | 12 | yakutia_larch | 15 | yakutia_larch | 0.04876 | 0.04876 | 0.04876 | 0.05215 | 0 | -1.345e-10 | 0.3861 |
| ndvi | 12 | yamal_peninsula | 14 | yamal_peninsula | 0.04996 | 0.04996 | 0.04996 | 0.04331 | 0 | 6.551e-11 | 0.4893 |
| ndvi | 12 | yucatan_peninsula | 15 | yucatan_peninsula | 0.0342 | 0.0342 | 0.0342 | 0.03654 | 0 | 6.953e-09 | 0.3722 |

## Disclosures (from each run's records)

### ndvi

- **limit:** Type 3 (plan 4.1 step 10) is not built
- **limit:** the quick and deep checks (plan 4.1 step 1, treeroute/check) are not built and not run; the feature script's lineage is checked against the verdicts only
- **limit:** the GLS-weighted per-unit solve is a new formula awaiting the owner's review; a region package routes no GLS arm (route/region.py has no weighted solve) and fits no weight model
- **limit:** the per-unit and region routers are called through route.kinds' and route.region's private kernels (route_per_unit_loro and route_region_loro are not built)
- **limit:** the neighbour router kind (R12) is refused (milestone M8)
- **limit:** the forecast ladder runs grid leads in steps only; leads in days (events) are refused (milestone M8)
- **limit:** the continuity row (continuity.csv), nearest-donor distances and distance bands, report.html and part_draft.md are not built (treeroute_report)
- **limit:** the band is derived from this run's own contrasts; registry/bands.csv and registry/index.csv are not written
- **limit:** 'freeze' verdicts are refused: per-cut frozen pools are not built
- **limit:** per_stratum.csv covers static report strata only; a time-varying stratum is refused
- **limit:** the target is read as a streaming census (derive/census.py; full rows only for the picked units): a date or day_of_year calendar (a day time line) is refused by it, and so is a driver store whose template has no {group} placeholder; R30's per-test-year missing share is counted once over every census row of the test years, in unit blocks that read the target and driver files from the test years' window on (the window rests on the feature script's declared backward windows, checked against the picked units' whole histories)
- **limit:** the picked units' column reader is built one group at a time (plan R20) and rebuilt by every stage that reads it (each derive pass's R30, the nowcast pool, the lead-0 contract's and each lead's pool): driver files are read once per build; the per-group path rests on the feature script's group-separability, checked on the smoke-shaped sample only
- **limit:** the per-group table schedule drops every table once its group is routed: the test pass recomputes the scored units' rows the GLS weight model built, and the lead-0 contract recomputes its pinned table and, for a weighted pin, the lead-0 weight model's donor rows (the same bytes, more tree predictions)
- **listed_in_reports:** listed in every report (watch / keep_unreviewed): snow_cover_fraction, sst_anom_atl3, sst_anom_coral_sea, tsa, grace_lwe, spi_24m, sst_anom_atl3_lag1, sst_anom_coral_sea_lag1, tsa_lag1, grace_lwe_lag1, spi_24m_lag1, sst_anom_atl3_lag2, sst_anom_coral_sea_lag2, tsa_lag2, grace_lwe_lag2, spi_24m_lag2, sst_anom_atl3_lag3, sst_anom_coral_sea_lag3, tsa_lag3, grace_lwe_lag3, spi_24m_lag3, sst_anom_atl3_lag6, sst_anom_coral_sea_lag6, tsa_lag6, grace_lwe_lag6, spi_24m_lag6, sst_anom_atl3_lag12, sst_anom_coral_sea_lag12, tsa_lag12, grace_lwe_lag12, spi_24m_lag12, aglw_cattle_hold2021, aglw_buffalo_hold2021, aglw_horse_hold2021, aglw_sheep_hold2021, aglw_goats_hold2021, aglw_total_lsu_hold2021
- **score_context_left_out:** decision surface (lead 0): 365 of 69364 scored rows of 12 units left out of scoring for missing router context (owner ruling S1, never filled); units with no scored row: atlantic_forest_brazil_-1149_-633, cape_floristic_region_500_-966, florida_everglades_-2228_761, florida_everglades_-2246_723, namib_desert_396_-628, namib_desert_402_-655, new_zealand_fiordland_4647_-1411, new_zealand_north_island_4836_-1076, niger_delta_139_162, northern_australia_monsoon_3651_-315, western_ghats_2047_449, yamal_peninsula_2026_2834; rows saved in context_missing/decision_surface_scored.parquet
- **score_context_left_out:** lead 12 guard (lead 12): 246 of 47513 scored rows of 12 units left out of scoring for missing router context (owner ruling S1, never filled); units with no scored row: atlantic_forest_brazil_-1149_-633, cape_floristic_region_500_-966, florida_everglades_-2228_761, florida_everglades_-2246_723, namib_desert_396_-628, namib_desert_402_-655, new_zealand_fiordland_4647_-1411, new_zealand_north_island_4836_-1076, niger_delta_139_162, northern_australia_monsoon_3651_-315, western_ghats_2047_449, yamal_peninsula_2026_2834; rows saved in context_missing/lead_12_guard_scored.parquet
- **score_context_left_out:** lead 12 test pass (lead 12): 576 of 95760 scored rows of 12 units left out of scoring for missing router context (owner ruling S1, never filled); units with no scored row: atlantic_forest_brazil_-1149_-633, cape_floristic_region_500_-966, florida_everglades_-2228_761, florida_everglades_-2246_723, namib_desert_396_-628, namib_desert_402_-655, new_zealand_fiordland_4647_-1411, new_zealand_north_island_4836_-1076, niger_delta_139_162, northern_australia_monsoon_3651_-315, western_ghats_2047_449, yamal_peninsula_2026_2834; rows saved in context_missing/lead_12_test_pass_scored.parquet
- **score_context_left_out:** lead 6 guard (lead 6): 311 of 59415 scored rows of 12 units left out of scoring for missing router context (owner ruling S1, never filled); units with no scored row: atlantic_forest_brazil_-1149_-633, cape_floristic_region_500_-966, florida_everglades_-2228_761, florida_everglades_-2246_723, namib_desert_396_-628, namib_desert_402_-655, new_zealand_fiordland_4647_-1411, new_zealand_north_island_4836_-1076, niger_delta_139_162, northern_australia_monsoon_3651_-315, western_ghats_2047_449, yamal_peninsula_2026_2834; rows saved in context_missing/lead_6_guard_scored.parquet
- **score_context_left_out:** lead 6 test pass (lead 6): 576 of 95760 scored rows of 12 units left out of scoring for missing router context (owner ruling S1, never filled); units with no scored row: atlantic_forest_brazil_-1149_-633, cape_floristic_region_500_-966, florida_everglades_-2228_761, florida_everglades_-2246_723, namib_desert_396_-628, namib_desert_402_-655, new_zealand_fiordland_4647_-1411, new_zealand_north_island_4836_-1076, niger_delta_139_162, northern_australia_monsoon_3651_-315, western_ghats_2047_449, yamal_peninsula_2026_2834; rows saved in context_missing/lead_6_test_pass_scored.parquet
- **score_context_left_out:** test pass (lead 0): 576 of 95760 scored rows of 12 units left out of scoring for missing router context (owner ruling S1, never filled); units with no scored row: atlantic_forest_brazil_-1149_-633, cape_floristic_region_500_-966, florida_everglades_-2228_761, florida_everglades_-2246_723, namib_desert_396_-628, namib_desert_402_-655, new_zealand_fiordland_4647_-1411, new_zealand_north_island_4836_-1076, niger_delta_139_162, northern_australia_monsoon_3651_-315, western_ghats_2047_449, yamal_peninsula_2026_2834; rows saved in context_missing/test_pass_scored.parquet
- **ladder_reading:g1_normal:** owner ruling G1 with R15: at a pass where G1 left fit rows out, the normal of each unit that lost rows is the mean over its KEPT fit rows (pipeline.stages G1_NORMAL), so that pass's saved normal column, guess-normal, the decline target and, at the test pass, damped persistence's normal follow the G1 fit rows, while damped persistence's phi is fitted on every label of the unit's history at the lead's fit cut (two row sets in one baseline); kept as built; context_missing in lead.json names the units and steps it touches
- **ladder_reading:guard_gls_answers:** a weighted pin's guard GLS weight model reads its error target's tree answers from the lead's FIT-cut bank (whose trees saw the guard window's labels), as the nowcast's inner decision does under L6 b (fit.weights.L6_ANSWERS_DISCLOSURE: L6 b as ruled names the bank and correctors; L6's add-on, the inner GLS target on the refit bank, +0.9-2.4 h over the nowcasts, was priced separately and is not ruled). Only a weighted pin reads it. One owner answer covers the nowcast and every lead (owner confirms, or both move to the refit bank)
- **ladder_reading:guard_issue_rows:** H4 names test rows; a GUARD-surface row whose issue row is absent refuses loudly (never scored on NaN features, never left out without a ruling); owner: rule whether H4 also leaves such guard rows out
- **ladder_reading:issue_missing_scope:** H4 is read as: a test row whose issue row t - L is absent from the base rows (every moved feature NaN: the case departure ladder_readings c put to the owner, 'a row whose issue row is absent ... (owner confirms, or they are dropped from scoring and saved flagged)'). A test row whose issue row exists keeps R30's 0-fill for a missing tree feature and G1's refusal for missing context, as the nowcast's own rows do at lead 0 (a broader H4 applied at the leads only would score the nowcast and the leads on different row rules). Such rows are counted per lead, lead 0 included (lead.json fits.issue_features_partly_missing, ladder.json issue_features_partly_missing), not left out. Under the dense census (G-SUPPORT) a test row's issue row lies inside the coverage at leads of up to 12 months, so the left-out count is 0 on the four packages (owner confirms)
- **ladder_reading:lead0_bank:** the lead-0 contract runs the lead path at lead 0 (the lead pool, FitContext(lead 0) and its donor rows, c, tolerances, donor-row means, the GLS refit when the pin is weighted, the route and the row assembly) and proves the bank's inputs (donor row keys, grid rows, features, labels) equal the nowcast bank's byte for byte; the bank itself is not refitted (deterministic name seeds on the same inputs give the same fit). The guard (and its guard-cut bank) and persistence have no lead-0 counterpart and are not covered
