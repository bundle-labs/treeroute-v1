# Headline tables

Built by treeroute_report.table from SAVED row-level predictions (test_preds.parquet) with the engine's treeroute.report.metrics functions. Every recorded verdict, band pair and blocked jackknife was recomputed from the saved rows and is equal. The band was recomputed from each run's own contrasts and is equal. MAE, anomaly R2 against the per-unit normal, corr2 and the hit rate are printed together, each beside guess-normal and the last-5-years normal; never R2 alone. Uncertainty is over groups (jackknife at 1.96); no multiplicity correction.

Files: `continuity_5df3be88bf06.csv`, `disclosures_68d51372e8c7.csv`, `headline_1571da960aa6.csv`, `per_group_f3b9e681f897.csv`, `per_stratum_685bb0839a17.csv`, `per_year_994462902c87.csv`, `scores_long_726623e350c2.csv`, `subsets_9d46554c7b2a.csv`, `verdicts_bf99c6741bce.csv`

## Runs

| package | run folder | kind | run fingerprint | package fingerprint | leads | groups | scored units |
|---|---|---|---|---|---|---|---|
| defo | D:\treeroute\runs\defo\headline\20261017_d71c61f4 | headline | d71c61f4543fa5b2 | d607314e8d571703 | 0, 1 | 42 | 92274 |

## Headline: pooled and macro (unweighted mean over groups)

Lead 0 is the nowcast. Rows 'all' = every saved row of the lead; 'common' = rows scored at every lead (the ladder's basis, R34).

| package | lead | rows | line | metric | adopted | own-link trees-off | guess-normal | last-5-years normal | predict-zero | persistence | damped persistence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| defo | 0 | all | pooled | MAE | 0.005416 | 0.005715 | 0.008405 | 0.008665 | 0.00612 | n/a | n/a |
| defo | 0 | all | pooled | anomaly R2 | 0.05176 | 0.04119 | 0 | -0.1284 | n/a | n/a | n/a |
| defo | 0 | all | pooled | corr2 | 0.01691 | 0.008624 | 0.003557 | 0.005718 | n/a | n/a | n/a |
| defo | 0 | all | pooled | hit rate | 0.834 | 0.8192 | 0.667 | 0.7198 | n/a | n/a | n/a |
| defo | 0 | all | pooled | hit rate at the declared floor | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| defo | 0 | all | pooled | calibration ratio | 0.2732 | 0.2132 | 0.9439 | 1.088 | n/a | n/a | n/a |
| defo | 0 | all | pooled | pre-clip rate | 0.07003 | 0 | n/a | n/a | n/a | n/a | n/a |
| defo | 0 | all | pooled | strict top-10% detection (R33) | 0.4879 | 0.4192 | 0.2619 | 0.3869 | n/a | n/a | n/a |
| defo | 0 | all | pooled | detection events | 3.691e+04 | 3.691e+04 | 3.691e+04 | 3.691e+04 | n/a | n/a | n/a |
| defo | 0 | all | macro | MAE | 0.005416 | 0.005715 | 0.008405 | 0.008665 | 0.00612 | n/a | n/a |
| defo | 0 | all | macro | anomaly R2 | 0.1107 | 0.05073 | 0 | -0.3454 | n/a | n/a | n/a |
| defo | 0 | all | macro | corr2 | 0.07795 | 0.05898 | 0.05729 | 0.06728 | n/a | n/a | n/a |
| defo | 0 | all | macro | hit rate | 0.834 | 0.8192 | 0.667 | 0.7198 | n/a | n/a | n/a |
| defo | 0 | all | macro | hit rate at the declared floor | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| defo | 0 | all | macro | calibration ratio | 0.2658 | 0.2328 | 1.296 | 1.348 | n/a | n/a | n/a |
| defo | 0 | all | macro | pre-clip rate | 0.07003 | 0 | n/a | n/a | n/a | n/a | n/a |
| defo | 0 | all | macro | strict top-10% detection (R33) | 0.3663 | 0.3024 | 0.235 | 0.3057 | n/a | n/a | n/a |
| defo | 0 | all | macro | detection events | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| defo | 0 | common | pooled | MAE | 0.005416 | 0.005715 | 0.008405 | 0.008665 | 0.00612 | n/a | n/a |
| defo | 0 | common | pooled | anomaly R2 | 0.05176 | 0.04119 | 0 | -0.1284 | n/a | n/a | n/a |
| defo | 0 | common | pooled | corr2 | 0.01691 | 0.008624 | 0.003557 | 0.005718 | n/a | n/a | n/a |
| defo | 0 | common | pooled | hit rate | 0.834 | 0.8192 | 0.667 | 0.7198 | n/a | n/a | n/a |
| defo | 0 | common | pooled | hit rate at the declared floor | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| defo | 0 | common | pooled | calibration ratio | 0.2732 | 0.2132 | 0.9439 | 1.088 | n/a | n/a | n/a |
| defo | 0 | common | pooled | pre-clip rate | 0.07003 | 0 | n/a | n/a | n/a | n/a | n/a |
| defo | 0 | common | pooled | strict top-10% detection (R33) | 0.4879 | 0.4192 | 0.2619 | 0.3869 | n/a | n/a | n/a |
| defo | 0 | common | pooled | detection events | 3.691e+04 | 3.691e+04 | 3.691e+04 | 3.691e+04 | n/a | n/a | n/a |
| defo | 0 | common | macro | MAE | 0.005416 | 0.005715 | 0.008405 | 0.008665 | 0.00612 | n/a | n/a |
| defo | 0 | common | macro | anomaly R2 | 0.1107 | 0.05073 | 0 | -0.3454 | n/a | n/a | n/a |
| defo | 0 | common | macro | corr2 | 0.07795 | 0.05898 | 0.05729 | 0.06728 | n/a | n/a | n/a |
| defo | 0 | common | macro | hit rate | 0.834 | 0.8192 | 0.667 | 0.7198 | n/a | n/a | n/a |
| defo | 0 | common | macro | hit rate at the declared floor | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| defo | 0 | common | macro | calibration ratio | 0.2658 | 0.2328 | 1.296 | 1.348 | n/a | n/a | n/a |
| defo | 0 | common | macro | pre-clip rate | 0.07003 | 0 | n/a | n/a | n/a | n/a | n/a |
| defo | 0 | common | macro | strict top-10% detection (R33) | 0.3663 | 0.3024 | 0.235 | 0.3057 | n/a | n/a | n/a |
| defo | 0 | common | macro | detection events | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| defo | 1 | all | pooled | MAE | 0.005408 | 0.005715 | 0.008405 | 0.008665 | 0.00612 | 0.008064 | 0.008317 |
| defo | 1 | all | pooled | anomaly R2 | 0.05031 | 0.04119 | 0 | -0.1284 | n/a | n/a | n/a |
| defo | 1 | all | pooled | corr2 | 0.01582 | 0.008624 | 0.003557 | 0.005718 | n/a | n/a | n/a |
| defo | 1 | all | pooled | hit rate | 0.8354 | 0.8192 | 0.667 | 0.7198 | n/a | n/a | n/a |
| defo | 1 | all | pooled | hit rate at the declared floor | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| defo | 1 | all | pooled | calibration ratio | 0.2688 | 0.2132 | 0.9439 | 1.088 | n/a | n/a | n/a |
| defo | 1 | all | pooled | pre-clip rate | 0.09725 | 0 | n/a | n/a | n/a | n/a | n/a |
| defo | 1 | all | pooled | strict top-10% detection (R33) | 0.488 | 0.4192 | 0.2619 | 0.3869 | n/a | n/a | n/a |
| defo | 1 | all | pooled | detection events | 3.691e+04 | 3.691e+04 | 3.691e+04 | 3.691e+04 | n/a | n/a | n/a |
| defo | 1 | all | macro | MAE | 0.005408 | 0.005715 | 0.008405 | 0.008665 | 0.00612 | 0.008064 | 0.008317 |
| defo | 1 | all | macro | anomaly R2 | 0.102 | 0.05073 | 0 | -0.3454 | n/a | n/a | n/a |
| defo | 1 | all | macro | corr2 | 0.07704 | 0.05898 | 0.05729 | 0.06728 | n/a | n/a | n/a |
| defo | 1 | all | macro | hit rate | 0.8354 | 0.8192 | 0.667 | 0.7198 | n/a | n/a | n/a |
| defo | 1 | all | macro | hit rate at the declared floor | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| defo | 1 | all | macro | calibration ratio | 0.2559 | 0.2328 | 1.296 | 1.348 | n/a | n/a | n/a |
| defo | 1 | all | macro | pre-clip rate | 0.09725 | 0 | n/a | n/a | n/a | n/a | n/a |
| defo | 1 | all | macro | strict top-10% detection (R33) | 0.3607 | 0.3024 | 0.235 | 0.3057 | n/a | n/a | n/a |
| defo | 1 | all | macro | detection events | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| defo | 1 | common | pooled | MAE | 0.005408 | 0.005715 | 0.008405 | 0.008665 | 0.00612 | 0.008064 | 0.008317 |
| defo | 1 | common | pooled | anomaly R2 | 0.05031 | 0.04119 | 0 | -0.1284 | n/a | n/a | n/a |
| defo | 1 | common | pooled | corr2 | 0.01582 | 0.008624 | 0.003557 | 0.005718 | n/a | n/a | n/a |
| defo | 1 | common | pooled | hit rate | 0.8354 | 0.8192 | 0.667 | 0.7198 | n/a | n/a | n/a |
| defo | 1 | common | pooled | hit rate at the declared floor | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| defo | 1 | common | pooled | calibration ratio | 0.2688 | 0.2132 | 0.9439 | 1.088 | n/a | n/a | n/a |
| defo | 1 | common | pooled | pre-clip rate | 0.09725 | 0 | n/a | n/a | n/a | n/a | n/a |
| defo | 1 | common | pooled | strict top-10% detection (R33) | 0.488 | 0.4192 | 0.2619 | 0.3869 | n/a | n/a | n/a |
| defo | 1 | common | pooled | detection events | 3.691e+04 | 3.691e+04 | 3.691e+04 | 3.691e+04 | n/a | n/a | n/a |
| defo | 1 | common | macro | MAE | 0.005408 | 0.005715 | 0.008405 | 0.008665 | 0.00612 | 0.008064 | 0.008317 |
| defo | 1 | common | macro | anomaly R2 | 0.102 | 0.05073 | 0 | -0.3454 | n/a | n/a | n/a |
| defo | 1 | common | macro | corr2 | 0.07704 | 0.05898 | 0.05729 | 0.06728 | n/a | n/a | n/a |
| defo | 1 | common | macro | hit rate | 0.8354 | 0.8192 | 0.667 | 0.7198 | n/a | n/a | n/a |
| defo | 1 | common | macro | hit rate at the declared floor | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| defo | 1 | common | macro | calibration ratio | 0.2559 | 0.2328 | 1.296 | 1.348 | n/a | n/a | n/a |
| defo | 1 | common | macro | pre-clip rate | 0.09725 | 0 | n/a | n/a | n/a | n/a | n/a |
| defo | 1 | common | macro | strict top-10% detection (R33) | 0.3607 | 0.3024 | 0.235 | 0.3057 | n/a | n/a | n/a |
| defo | 1 | common | macro | detection events | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Verdicts (D74 rule; recomputed = recorded)

| package | lead | rows | verdict | contrast | CI low | CI high | SE | groups | band | band check | history band (beside, never used) | pooled contrast | groups better | sign flips | blocked-jackknife flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| defo | 0 | all | helps | 0.0002988 | 8.75e-05 | 0.0005101 | 0.0001078 | 42 | 0.0001104 | recomputed from this run's D75 contrasts, equal | n/a | 0.0002988 | 42 |  | no |
| defo | 0 | common | helps | 0.0002988 | 8.75e-05 | 0.0005101 | 0.0001078 | 42 | 0.0001104 | recomputed from this run's D75 contrasts, equal | n/a | 0.0002988 | 42 |  | n/a |
| defo | 1 | common | helps | 0.0003069 | 0.0001022 | 0.0005115 | 0.0001044 | 42 | 0.0001104 | recomputed from this run's D75 contrasts, equal | n/a | 0.0003069 | 41 | tongass_alaska | n/a |

## Per test year

| package | lead | rows | year | MAE adopted | MAE trees-off | MAE guess-normal | MAE last-5 | anomaly R2 | corr2 | hit rate | hit guess-normal | detection | detection guess-normal | rows |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| defo | 0 | all | 2020 | 0.007722 | 0.008035 | 0.01048 | 0.01038 | 0.0183 | 0.009522 | 0.82 | 0.6641 | 0.4699 | 0.2721 | 92274 |
| defo | 0 | all | 2021 | 0.004949 | 0.005304 | 0.007967 | 0.00827 | 0.07225 | 0.02476 | 0.8345 | 0.6638 | 0.4835 | 0.2612 | 92274 |
| defo | 0 | all | 2022 | 0.003681 | 0.00394 | 0.006807 | 0.007269 | 0.1393 | 0.03616 | 0.8503 | 0.6758 | 0.5216 | 0.2677 | 92274 |
| defo | 0 | all | 2023 | 0.005311 | 0.005579 | 0.008364 | 0.008744 | 0.06276 | 0.01794 | 0.8313 | 0.6643 | 0.4821 | 0.2488 | 92274 |
| defo | 0 | common | 2020 | 0.007722 | 0.008035 | 0.01048 | 0.01038 | 0.0183 | 0.009522 | 0.82 | 0.6641 | 0.4699 | 0.2721 | 92274 |
| defo | 0 | common | 2021 | 0.004949 | 0.005304 | 0.007967 | 0.00827 | 0.07225 | 0.02476 | 0.8345 | 0.6638 | 0.4835 | 0.2612 | 92274 |
| defo | 0 | common | 2022 | 0.003681 | 0.00394 | 0.006807 | 0.007269 | 0.1393 | 0.03616 | 0.8503 | 0.6758 | 0.5216 | 0.2677 | 92274 |
| defo | 0 | common | 2023 | 0.005311 | 0.005579 | 0.008364 | 0.008744 | 0.06276 | 0.01794 | 0.8313 | 0.6643 | 0.4821 | 0.2488 | 92274 |
| defo | 1 | all | 2020 | 0.007665 | 0.008035 | 0.01048 | 0.01038 | 0.01792 | 0.009554 | 0.8249 | 0.6641 | 0.4705 | 0.2721 | 92274 |
| defo | 1 | all | 2021 | 0.004981 | 0.005304 | 0.007967 | 0.00827 | 0.0713 | 0.02297 | 0.8312 | 0.6638 | 0.4802 | 0.2612 | 92274 |
| defo | 1 | all | 2022 | 0.003694 | 0.00394 | 0.006807 | 0.007269 | 0.135 | 0.03339 | 0.8494 | 0.6758 | 0.5195 | 0.2677 | 92274 |
| defo | 1 | all | 2023 | 0.00529 | 0.005579 | 0.008364 | 0.008744 | 0.06005 | 0.01709 | 0.8359 | 0.6643 | 0.4846 | 0.2488 | 92274 |
| defo | 1 | common | 2020 | 0.007665 | 0.008035 | 0.01048 | 0.01038 | 0.01792 | 0.009554 | 0.8249 | 0.6641 | 0.4705 | 0.2721 | 92274 |
| defo | 1 | common | 2021 | 0.004981 | 0.005304 | 0.007967 | 0.00827 | 0.0713 | 0.02297 | 0.8312 | 0.6638 | 0.4802 | 0.2612 | 92274 |
| defo | 1 | common | 2022 | 0.003694 | 0.00394 | 0.006807 | 0.007269 | 0.135 | 0.03339 | 0.8494 | 0.6758 | 0.5195 | 0.2677 | 92274 |
| defo | 1 | common | 2023 | 0.00529 | 0.005579 | 0.008364 | 0.008744 | 0.06005 | 0.01709 | 0.8359 | 0.6643 | 0.4846 | 0.2488 | 92274 |

## Continuity row (the old hard-split test groups alone, same run): continuity, not a replication

| package | lead | rows | groups listed | groups scored | scored units | old test units | MAE adopted | MAE trees-off | MAE guess-normal | MAE last-5 | anomaly R2 | verdict | contrast | CI low | CI high | band | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| defo | 0 | all | 17 | 17 | 37349 | 70487 | 0.004933 | 0.005126 | 0.008703 | 0.009251 | 0.09757 | helps | 0.0001936 | 1.552e-05 | 0.0003718 | 0.0001104 | the package's band judges this row (R35); its jackknife is over these groups only |
| defo | 0 | common | 17 | 17 | 37349 | 70487 | 0.004933 | 0.005126 | 0.008703 | 0.009251 | 0.09757 | helps | 0.0001936 | 1.552e-05 | 0.0003718 | 0.0001104 | the package's band judges this row (R35); its jackknife is over these groups only |
| defo | 1 | all | 17 | 17 | 37349 | 70487 | 0.004917 | 0.005126 | 0.008703 | 0.009251 | 0.09605 | helps | 0.0002095 | 1.214e-05 | 0.000407 | 0.0001104 | the package's band judges this row (R35); its jackknife is over these groups only |
| defo | 1 | common | 17 | 17 | 37349 | 70487 | 0.004917 | 0.005126 | 0.008703 | 0.009251 | 0.09605 | helps | 0.0002095 | 1.214e-05 | 0.000407 | 0.0001104 | the package's band judges this row (R35); its jackknife is over these groups only |

## Per report stratum (R34; lead 0, rows 'all')

The stratum tables are copied from the engine's per_stratum.csv (report pass, the same saved rows); NOT recomputed here: the units' stratum values and the donor-row edges are not in the saved rows. Strata are the donor rows' quartiles, right-closed (D73).

| package | stratum column | stratum | edges q25 / q50 / q75 | rows | MAE adopted | MAE trees-off | MAE guess-normal | MAE last-5 | anomaly R2 | corr2 | hit rate | detection |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| defo | forest2000_px | 1 | 3499.0 / 10484.0 / 17398.0 | 91788 | 0.002925 | 0.002967 | 0.005363 | 0.004781 | 0.072 | 0.01204 | 0.9128 | 0.4477 |
| defo | forest2000_px | 2 | 3499.0 / 10484.0 / 17398.0 | 91848 | 0.004977 | 0.005119 | 0.008524 | 0.008319 | 0.07324 | 0.01148 | 0.841 | 0.4175 |
| defo | forest2000_px | 3 | 3499.0 / 10484.0 / 17398.0 | 93488 | 0.007704 | 0.007951 | 0.01101 | 0.01202 | 0.02607 | 0.004566 | 0.8141 | 0.4033 |
| defo | forest2000_px | 4 | 3499.0 / 10484.0 / 17398.0 | 91972 | 0.006013 | 0.006778 | 0.008672 | 0.009474 | 0.08734 | 0.05283 | 0.7688 | 0.5453 |

## Per group (rows 'all')

Each group's score is noisy; the pooled headline and the all-group jackknife decide, never one group.

| package | lead | group | scored units | overlap block | MAE adopted | MAE trees-off | MAE guess-normal | MAE last-5 | contrast | anomaly R2 | hit rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| defo | 0 | amazon_basin_brazil | 2197 | amazon_basin_brazil | 0.001359 | 0.001383 | 0.001739 | 0.00247 | 2.443e-05 | 0.009571 | 0.9465 |
| defo | 0 | andes_puna | 2197 | andes_puna+bolivia_beni_savanna | 0.00506 | 0.005061 | 0.005424 | 0.00542 | 1.306e-06 | -0.00509 | 0.8617 |
| defo | 0 | angola_zambia_fire_belt | 2197 | angola_zambia_fire_belt+miombo_woodland_zambia | 0.002539 | 0.002731 | 0.002636 | 0.002331 | 0.0001917 | -0.04409 | 0.822 |
| defo | 0 | atlantic_forest_brazil | 2197 | atlantic_forest_brazil | 0.002912 | 0.00301 | 0.004656 | 0.007196 | 9.774e-05 | 0.2852 | 0.7774 |
| defo | 0 | australian_bushfire_belt | 2197 | australian_bushfire_belt | 0.02934 | 0.02936 | 0.03228 | 0.03431 | 2.826e-05 | -0.004167 | 0.8752 |
| defo | 0 | bc_inland_rainforest | 2197 | bc_inland_rainforest | 0.003677 | 0.003691 | 0.006709 | 0.006822 | 1.414e-05 | 0.04857 | 0.9514 |
| defo | 0 | bolivia_beni_savanna | 2197 | andes_puna+bolivia_beni_savanna | 0.009972 | 0.01004 | 0.01121 | 0.0108 | 6.757e-05 | -0.001213 | 0.7959 |
| defo | 0 | borneo_peat_fires | 2197 | borneo_peat_fires | 0.006607 | 0.007894 | 0.01795 | 0.01788 | 0.001287 | 0.3343 | 0.7218 |
| defo | 0 | borneo_rainforest | 2197 | borneo_rainforest | 0.006375 | 0.007048 | 0.0154 | 0.01329 | 0.0006728 | 0.4215 | 0.7146 |
| defo | 0 | canadian_taiga | 2197 | canadian_taiga | 0.01244 | 0.01258 | 0.02622 | 0.02397 | 0.0001372 | 0.06944 | 0.9515 |
| defo | 0 | caucasus_highlands | 2197 | caucasus_highlands | 0.0001667 | 0.0001705 | 0.000469 | 0.0002443 | 3.884e-06 | 0.3878 | 0.9931 |
| defo | 0 | congo_basin_drc | 2197 | congo_basin_drc | 0.002731 | 0.003728 | 0.00267 | 0.003249 | 0.0009973 | -0.06925 | 0.7943 |
| defo | 0 | costa_rica | 2197 | costa_rica | 0.002062 | 0.002122 | 0.004355 | 0.007247 | 6.059e-05 | 0.5961 | 0.8773 |
| defo | 0 | eastern_us_deciduous | 2197 | eastern_us_deciduous | 0.002672 | 0.002742 | 0.003997 | 0.004356 | 7.024e-05 | 0.02412 | 0.8579 |
| defo | 0 | gran_chaco | 2197 | gran_chaco | 0.008383 | 0.008399 | 0.01711 | 0.01805 | 1.574e-05 | 0.09356 | 0.8627 |
| defo | 0 | greece_mainland | 2197 | greece_mainland | 0.002955 | 0.002964 | 0.005214 | 0.00371 | 8.996e-06 | 0.03999 | 0.9511 |
| defo | 0 | idaho_montana_wildfire | 2197 | idaho_montana_wildfire | 0.005734 | 0.005883 | 0.01326 | 0.01209 | 0.0001489 | 0.09452 | 0.9254 |
| defo | 0 | ireland | 2197 | ireland | 0.005044 | 0.00509 | 0.007538 | 0.007437 | 4.642e-05 | -0.02179 | 0.8852 |
| defo | 0 | japan_central_honshu | 2197 | japan_central_honshu | 0.0008205 | 0.0008389 | 0.001067 | 0.001037 | 1.835e-05 | -0.01078 | 0.9439 |
| defo | 0 | llanos_venezuela | 2197 | llanos_venezuela | 0.002031 | 0.002098 | 0.003142 | 0.0027 | 6.7e-05 | 0.05644 | 0.8876 |
| defo | 0 | miombo_woodland_zambia | 2197 | angola_zambia_fire_belt+miombo_woodland_zambia | 0.008276 | 0.009284 | 0.009456 | 0.008807 | 0.001008 | 0.03457 | 0.5814 |
| defo | 0 | new_guinea_papua | 2197 | new_guinea_papua | 0.00115 | 0.001252 | 0.001473 | 0.002109 | 0.000102 | 0.08582 | 0.9284 |
| defo | 0 | new_zealand_fiordland | 2197 | new_zealand_fiordland | 0.001712 | 0.001736 | 0.003522 | 0.00336 | 2.393e-05 | 0.1103 | 0.954 |
| defo | 0 | new_zealand_north_island | 2197 | new_zealand_north_island | 0.008739 | 0.009071 | 0.01425 | 0.01454 | 0.0003321 | 0.08361 | 0.7761 |
| defo | 0 | northeast_china_broadleaf | 2197 | northeast_china_broadleaf | 0.002515 | 0.00256 | 0.003947 | 0.00375 | 4.466e-05 | 0.04584 | 0.9074 |
| defo | 0 | northern_thailand | 2197 | northern_thailand | 0.004817 | 0.005748 | 0.00595 | 0.005775 | 0.0009311 | 0.1006 | 0.6978 |
| defo | 0 | pacific_nw_coast | 2197 | pacific_nw_coast | 0.01041 | 0.01048 | 0.01282 | 0.01319 | 7.669e-05 | -0.02754 | 0.6647 |
| defo | 0 | pantanal | 2197 | pantanal | 0.02305 | 0.02308 | 0.02469 | 0.02522 | 2.503e-05 | -0.008615 | 0.6493 |
| defo | 0 | pearl_river_delta | 2197 | pearl_river_delta | 0.005876 | 0.006069 | 0.00917 | 0.009135 | 0.000193 | 0.1422 | 0.6458 |
| defo | 0 | poland_central | 2197 | poland_central | 0.004289 | 0.004378 | 0.005368 | 0.006518 | 8.849e-05 | 0.03107 | 0.74 |
| defo | 0 | russian_far_east_primorye | 2197 | russian_far_east_primorye | 0.0006346 | 0.0006446 | 0.00148 | 0.0009988 | 1.003e-05 | 0.1282 | 0.9818 |
| defo | 0 | siberian_taiga | 2197 | siberian_taiga | 0.001186 | 0.001245 | 0.006896 | 0.006725 | 5.905e-05 | 0.6455 | 0.9713 |
| defo | 0 | southern_chile_rainforest | 2197 | southern_chile_rainforest | 0.001993 | 0.001999 | 0.003173 | 0.003745 | 5.607e-06 | 0.03254 | 0.9554 |
| defo | 0 | tasmania_western | 2197 | tasmania_western | 0.005762 | 0.00586 | 0.01285 | 0.02182 | 9.714e-05 | 0.1141 | 0.8699 |
| defo | 0 | tierra_del_fuego | 2197 | tierra_del_fuego | 0.0006528 | 0.0006545 | 0.001683 | 0.000648 | 1.672e-06 | 0.1556 | 0.9903 |
| defo | 0 | tongass_alaska | 2197 | tongass_alaska | 0.0002824 | 0.0002826 | 0.0004381 | 0.0003889 | 1.894e-07 | 0.08841 | 0.9859 |
| defo | 0 | trans_baikal_steppe | 2197 | trans_baikal_steppe | 0.001989 | 0.002097 | 0.01044 | 0.01047 | 0.0001083 | 0.3668 | 0.9505 |
| defo | 0 | vietnam_central_highlands | 2197 | vietnam_central_highlands | 0.006812 | 0.00787 | 0.01133 | 0.01022 | 0.001058 | 0.2721 | 0.6222 |
| defo | 0 | west_africa_monsoon_guinea | 2197 | west_africa_monsoon_guinea | 0.008968 | 0.01313 | 0.008734 | 0.01 | 0.00416 | -0.06058 | 0.4002 |
| defo | 0 | western_europe_temperate | 2197 | western_europe_temperate | 0.004203 | 0.004264 | 0.004698 | 0.004707 | 6.029e-05 | -0.05325 | 0.7622 |
| defo | 0 | western_scotland | 2197 | western_scotland | 0.005493 | 0.005504 | 0.009259 | 0.008809 | 1.108e-05 | 0.01894 | 0.8825 |
| defo | 0 | yucatan_peninsula | 2197 | yucatan_peninsula | 0.005776 | 0.00597 | 0.00832 | 0.008363 | 0.0001937 | 0.0386 | 0.7155 |
| defo | 1 | amazon_basin_brazil | 2197 | amazon_basin_brazil | 0.00136 | 0.001383 | 0.001739 | 0.00247 | 2.313e-05 | -0.001384 | 0.9462 |
| defo | 1 | andes_puna | 2197 | andes_puna+bolivia_beni_savanna | 0.005023 | 0.005061 | 0.005424 | 0.00542 | 3.818e-05 | -0.006749 | 0.8675 |
| defo | 1 | angola_zambia_fire_belt | 2197 | angola_zambia_fire_belt+miombo_woodland_zambia | 0.002536 | 0.002731 | 0.002636 | 0.002331 | 0.0001945 | -0.03735 | 0.8223 |
| defo | 1 | atlantic_forest_brazil | 2197 | atlantic_forest_brazil | 0.002941 | 0.00301 | 0.004656 | 0.007196 | 6.867e-05 | 0.2903 | 0.7728 |
| defo | 1 | australian_bushfire_belt | 2197 | australian_bushfire_belt | 0.02933 | 0.02936 | 0.03228 | 0.03431 | 3.274e-05 | -0.004438 | 0.8752 |
| defo | 1 | bc_inland_rainforest | 2197 | bc_inland_rainforest | 0.00366 | 0.003691 | 0.006709 | 0.006822 | 3.152e-05 | 0.04778 | 0.9524 |
| defo | 1 | bolivia_beni_savanna | 2197 | andes_puna+bolivia_beni_savanna | 0.00993 | 0.01004 | 0.01121 | 0.0108 | 0.0001097 | -0.004107 | 0.8023 |
| defo | 1 | borneo_peat_fires | 2197 | borneo_peat_fires | 0.006811 | 0.007894 | 0.01795 | 0.01788 | 0.001083 | 0.3328 | 0.698 |
| defo | 1 | borneo_rainforest | 2197 | borneo_rainforest | 0.006316 | 0.007048 | 0.0154 | 0.01329 | 0.0007313 | 0.4106 | 0.7261 |
| defo | 1 | canadian_taiga | 2197 | canadian_taiga | 0.01245 | 0.01258 | 0.02622 | 0.02397 | 0.0001282 | 0.0676 | 0.9549 |
| defo | 1 | caucasus_highlands | 2197 | caucasus_highlands | 0.0001666 | 0.0001705 | 0.000469 | 0.0002443 | 3.897e-06 | 0.3878 | 0.9931 |
| defo | 1 | congo_basin_drc | 2197 | congo_basin_drc | 0.003085 | 0.003728 | 0.00267 | 0.003249 | 0.0006429 | -0.3301 | 0.7868 |
| defo | 1 | costa_rica | 2197 | costa_rica | 0.002032 | 0.002122 | 0.004355 | 0.007247 | 9.058e-05 | 0.5922 | 0.8732 |
| defo | 1 | eastern_us_deciduous | 2197 | eastern_us_deciduous | 0.002663 | 0.002742 | 0.003997 | 0.004356 | 7.906e-05 | 0.01838 | 0.858 |
| defo | 1 | gran_chaco | 2197 | gran_chaco | 0.008304 | 0.008399 | 0.01711 | 0.01805 | 9.552e-05 | 0.09265 | 0.868 |
| defo | 1 | greece_mainland | 2197 | greece_mainland | 0.002944 | 0.002964 | 0.005214 | 0.00371 | 2.039e-05 | 0.03969 | 0.9505 |
| defo | 1 | idaho_montana_wildfire | 2197 | idaho_montana_wildfire | 0.005718 | 0.005883 | 0.01326 | 0.01209 | 0.0001656 | 0.09111 | 0.9255 |
| defo | 1 | ireland | 2197 | ireland | 0.005026 | 0.00509 | 0.007538 | 0.007437 | 6.434e-05 | -0.0216 | 0.8864 |
| defo | 1 | japan_central_honshu | 2197 | japan_central_honshu | 0.0008293 | 0.0008389 | 0.001067 | 0.001037 | 9.556e-06 | -0.01422 | 0.9428 |
| defo | 1 | llanos_venezuela | 2197 | llanos_venezuela | 0.002023 | 0.002098 | 0.003142 | 0.0027 | 7.436e-05 | 0.05094 | 0.8887 |
| defo | 1 | miombo_woodland_zambia | 2197 | angola_zambia_fire_belt+miombo_woodland_zambia | 0.007938 | 0.009284 | 0.009456 | 0.008807 | 0.001346 | 0.07587 | 0.5955 |
| defo | 1 | new_guinea_papua | 2197 | new_guinea_papua | 0.001171 | 0.001252 | 0.001473 | 0.002109 | 8.13e-05 | 0.06068 | 0.9247 |
| defo | 1 | new_zealand_fiordland | 2197 | new_zealand_fiordland | 0.001712 | 0.001736 | 0.003522 | 0.00336 | 2.383e-05 | 0.1099 | 0.9539 |
| defo | 1 | new_zealand_north_island | 2197 | new_zealand_north_island | 0.008731 | 0.009071 | 0.01425 | 0.01454 | 0.0003398 | 0.07868 | 0.7811 |
| defo | 1 | northeast_china_broadleaf | 2197 | northeast_china_broadleaf | 0.002518 | 0.00256 | 0.003947 | 0.00375 | 4.158e-05 | 0.04581 | 0.9068 |
| defo | 1 | northern_thailand | 2197 | northern_thailand | 0.004865 | 0.005748 | 0.00595 | 0.005775 | 0.0008827 | 0.06492 | 0.6953 |
| defo | 1 | pacific_nw_coast | 2197 | pacific_nw_coast | 0.01037 | 0.01048 | 0.01282 | 0.01319 | 0.0001117 | -0.03236 | 0.676 |
| defo | 1 | pantanal | 2197 | pantanal | 0.02306 | 0.02308 | 0.02469 | 0.02522 | 1.585e-05 | -0.0108 | 0.6537 |
| defo | 1 | pearl_river_delta | 2197 | pearl_river_delta | 0.005707 | 0.006069 | 0.00917 | 0.009135 | 0.000362 | 0.1476 | 0.6645 |
| defo | 1 | poland_central | 2197 | poland_central | 0.004301 | 0.004378 | 0.005368 | 0.006518 | 7.681e-05 | 0.02073 | 0.7445 |
| defo | 1 | russian_far_east_primorye | 2197 | russian_far_east_primorye | 0.0006296 | 0.0006446 | 0.00148 | 0.0009988 | 1.504e-05 | 0.128 | 0.9819 |
| defo | 1 | siberian_taiga | 2197 | siberian_taiga | 0.001186 | 0.001245 | 0.006896 | 0.006725 | 5.848e-05 | 0.6456 | 0.9713 |
| defo | 1 | southern_chile_rainforest | 2197 | southern_chile_rainforest | 0.001986 | 0.001999 | 0.003173 | 0.003745 | 1.298e-05 | 0.03198 | 0.9536 |
| defo | 1 | tasmania_western | 2197 | tasmania_western | 0.005771 | 0.00586 | 0.01285 | 0.02182 | 8.82e-05 | 0.1141 | 0.8685 |
| defo | 1 | tierra_del_fuego | 2197 | tierra_del_fuego | 0.0006472 | 0.0006545 | 0.001683 | 0.000648 | 7.254e-06 | 0.1549 | 0.9902 |
| defo | 1 | tongass_alaska | 2197 | tongass_alaska | 0.0002827 | 0.0002826 | 0.0004381 | 0.0003889 | -8.493e-08 | 0.08831 | 0.9859 |
| defo | 1 | trans_baikal_steppe | 2197 | trans_baikal_steppe | 0.002013 | 0.002097 | 0.01044 | 0.01047 | 8.407e-05 | 0.3669 | 0.9497 |
| defo | 1 | vietnam_central_highlands | 2197 | vietnam_central_highlands | 0.006375 | 0.00787 | 0.01133 | 0.01022 | 0.001495 | 0.2854 | 0.6466 |
| defo | 1 | west_africa_monsoon_guinea | 2197 | west_africa_monsoon_guinea | 0.009214 | 0.01313 | 0.008734 | 0.01 | 0.003914 | -0.09149 | 0.3968 |
| defo | 1 | western_europe_temperate | 2197 | western_europe_temperate | 0.004195 | 0.004264 | 0.004698 | 0.004707 | 6.849e-05 | -0.04735 | 0.7616 |
| defo | 1 | western_scotland | 2197 | western_scotland | 0.005466 | 0.005504 | 0.009259 | 0.008809 | 3.772e-05 | 0.01492 | 0.8852 |
| defo | 1 | yucatan_peninsula | 2197 | yucatan_peninsula | 0.005833 | 0.00597 | 0.00832 | 0.008363 | 0.0001375 | 0.03184 | 0.7073 |

## Disclosures (from each run's records)

### defo

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
- **listed_in_reports:** listed in every report (watch / keep_unreviewed): clay_pct, sand_pct, silt_pct, soil_organic_carbon_gkg, nitrogen_gkg, soil_ph, awc_cm3cm3, bulk_density_gcm3, cec_cmolkg, coarse_fragments_pct, hand_m, upstream_area_km2, aglw_cattle_hold2021, aglw_buffalo_hold2021, aglw_horse_hold2021, aglw_sheep_hold2021, aglw_goats_hold2021, aglw_total_lsu_hold2021
- **ladder_reading:g1_normal:** owner ruling G1 with R15: at a pass where G1 left fit rows out, the normal of each unit that lost rows is the mean over its KEPT fit rows (pipeline.stages G1_NORMAL), so that pass's saved normal column, guess-normal, the decline target and, at the test pass, damped persistence's normal follow the G1 fit rows, while damped persistence's phi is fitted on every label of the unit's history at the lead's fit cut (two row sets in one baseline); kept as built; context_missing in lead.json names the units and steps it touches
- **ladder_reading:guard_gls_answers:** a weighted pin's guard GLS weight model reads its error target's tree answers from the lead's FIT-cut bank (whose trees saw the guard window's labels), as the nowcast's inner decision does under L6 b (fit.weights.L6_ANSWERS_DISCLOSURE: L6 b as ruled names the bank and correctors; L6's add-on, the inner GLS target on the refit bank, +0.9-2.4 h over the nowcasts, was priced separately and is not ruled). Only a weighted pin reads it. One owner answer covers the nowcast and every lead (owner confirms, or both move to the refit bank)
- **ladder_reading:guard_issue_rows:** H4 names test rows; a GUARD-surface row whose issue row is absent refuses loudly (never scored on NaN features, never left out without a ruling); owner: rule whether H4 also leaves such guard rows out
- **ladder_reading:issue_missing_scope:** H4 is read as: a test row whose issue row t - L is absent from the base rows (every moved feature NaN: the case departure ladder_readings c put to the owner, 'a row whose issue row is absent ... (owner confirms, or they are dropped from scoring and saved flagged)'). A test row whose issue row exists keeps R30's 0-fill for a missing tree feature and G1's refusal for missing context, as the nowcast's own rows do at lead 0 (a broader H4 applied at the leads only would score the nowcast and the leads on different row rules). Such rows are counted per lead, lead 0 included (lead.json fits.issue_features_partly_missing, ladder.json issue_features_partly_missing), not left out. Under the dense census (G-SUPPORT) a test row's issue row lies inside the coverage at leads of up to 12 months, so the left-out count is 0 on the four packages (owner confirms)
- **ladder_reading:lead0_bank:** the lead-0 contract runs the lead path at lead 0 (the lead pool, FitContext(lead 0) and its donor rows, c, tolerances, donor-row means, the GLS refit when the pin is weighted, the route and the row assembly) and proves the bank's inputs (donor row keys, grid rows, features, labels) equal the nowcast bank's byte for byte; the bank itself is not refitted (deterministic name seeds on the same inputs give the same fit). The guard (and its guard-cut bank) and persistence have no lead-0 counterpart and are not covered
