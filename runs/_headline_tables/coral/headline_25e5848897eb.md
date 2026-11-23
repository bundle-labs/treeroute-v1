# Headline tables

Built by treeroute_report.table from SAVED row-level predictions (test_preds.parquet) with the engine's treeroute.report.metrics functions. Every recorded verdict, band pair and blocked jackknife was recomputed from the saved rows and is equal. The band was recomputed from each run's own contrasts and is equal. MAE, anomaly R2 against the per-unit normal, corr2 and the hit rate are printed together, each beside guess-normal and the last-5-years normal; never R2 alone. Uncertainty is over groups (jackknife at 1.96); no multiplicity correction.

Files: `continuity_bbff151092ad.csv`, `disclosures_a6d0f1d46939.csv`, `headline_344838cf7de1.csv`, `per_group_1e2505d594fc.csv`, `per_stratum_efe3264836e0.csv`, `per_year_7dde14b4e308.csv`, `scores_long_57920b9d8983.csv`, `subsets_e7e0be563aaf.csv`, `verdicts_a9d948cbf26b.csv`

## Runs

| package | run folder | kind | run fingerprint | package fingerprint | leads | groups | scored units |
|---|---|---|---|---|---|---|---|
| coral | D:\treeroute\runs\coral\headline\20261020_f3b8e3da | headline | f3b8e3daee7474db | 5b9383f0446df0f1 | 0, 183, 365 | 37 | 2312 |

## Headline: pooled and macro (unweighted mean over groups)

Lead 0 is the nowcast. Rows 'all' = every saved row of the lead; 'common' = rows scored at every lead (the ladder's basis, R34).

| package | lead | rows | line | metric | adopted | own-link trees-off | guess-normal | last-5-years normal | predict-zero | persistence | damped persistence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| coral | 0 | all | pooled | MAE | 6.698 | 8.294 | n/a | n/a | 8.1 | n/a | n/a |
| coral | 0 | all | pooled | anomaly R2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | all | pooled | corr2 | 0.4637 | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | all | pooled | hit rate | 0.7422 | 0.7729 | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | all | pooled | hit rate at the declared floor | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | all | pooled | calibration ratio | 0.5312 | 0.1235 | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | all | pooled | pre-clip rate | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | all | pooled | strict top-10% detection (R33) | 0.569 | 0 | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | all | pooled | detection events | 232 | 232 | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | all | macro | MAE | 14.64 | 19.84 | n/a | n/a | 19.99 | n/a | n/a |
| coral | 0 | all | macro | anomaly R2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | all | macro | corr2 | 0.2488 | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | all | macro | hit rate | 0.5903 | 0.6079 | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | all | macro | hit rate at the declared floor | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | all | macro | calibration ratio | 1.019 | 0.715 | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | all | macro | pre-clip rate | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | all | macro | strict top-10% detection (R33) | 0.181 | 0 | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | all | macro | detection events | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | common | pooled | MAE | 6.698 | 8.294 | n/a | n/a | 8.1 | n/a | n/a |
| coral | 0 | common | pooled | anomaly R2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | common | pooled | corr2 | 0.4637 | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | common | pooled | hit rate | 0.7422 | 0.7729 | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | common | pooled | hit rate at the declared floor | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | common | pooled | calibration ratio | 0.5312 | 0.1235 | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | common | pooled | pre-clip rate | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | common | pooled | strict top-10% detection (R33) | 0.569 | 0 | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | common | pooled | detection events | 232 | 232 | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | common | macro | MAE | 14.64 | 19.84 | n/a | n/a | 19.99 | n/a | n/a |
| coral | 0 | common | macro | anomaly R2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | common | macro | corr2 | 0.2488 | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | common | macro | hit rate | 0.5903 | 0.6079 | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | common | macro | hit rate at the declared floor | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | common | macro | calibration ratio | 1.019 | 0.715 | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | common | macro | pre-clip rate | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | common | macro | strict top-10% detection (R33) | 0.181 | 0 | n/a | n/a | n/a | n/a | n/a |
| coral | 0 | common | macro | detection events | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | all | pooled | MAE | 7.71 | 8.294 | n/a | n/a | 8.1 | 4.529 | 5.478 |
| coral | 183 | all | pooled | anomaly R2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | all | pooled | corr2 | 0.1394 | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | all | pooled | hit rate | 0.763 | 0.7729 | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | all | pooled | hit rate at the declared floor | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | all | pooled | calibration ratio | 0.2902 | 0.1235 | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | all | pooled | pre-clip rate | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | all | pooled | strict top-10% detection (R33) | 0.2457 | 0 | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | all | pooled | detection events | 232 | 232 | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | all | macro | MAE | 18.1 | 19.84 | n/a | n/a | 19.99 | 6.09 | 7.186 |
| coral | 183 | all | macro | anomaly R2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | all | macro | corr2 | 0.1571 | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | all | macro | hit rate | 0.5903 | 0.6079 | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | all | macro | hit rate at the declared floor | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | all | macro | calibration ratio | 0.621 | 0.715 | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | all | macro | pre-clip rate | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | all | macro | strict top-10% detection (R33) | 0.07365 | 0 | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | all | macro | detection events | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | common | pooled | MAE | 7.71 | 8.294 | n/a | n/a | 8.1 | 4.529 | 5.478 |
| coral | 183 | common | pooled | anomaly R2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | common | pooled | corr2 | 0.1394 | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | common | pooled | hit rate | 0.763 | 0.7729 | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | common | pooled | hit rate at the declared floor | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | common | pooled | calibration ratio | 0.2902 | 0.1235 | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | common | pooled | pre-clip rate | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | common | pooled | strict top-10% detection (R33) | 0.2457 | 0 | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | common | pooled | detection events | 232 | 232 | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | common | macro | MAE | 18.1 | 19.84 | n/a | n/a | 19.99 | 6.09 | 7.186 |
| coral | 183 | common | macro | anomaly R2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | common | macro | corr2 | 0.1571 | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | common | macro | hit rate | 0.5903 | 0.6079 | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | common | macro | hit rate at the declared floor | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | common | macro | calibration ratio | 0.621 | 0.715 | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | common | macro | pre-clip rate | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | common | macro | strict top-10% detection (R33) | 0.07365 | 0 | n/a | n/a | n/a | n/a | n/a |
| coral | 183 | common | macro | detection events | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | all | pooled | MAE | 8.294 | 8.294 | n/a | n/a | 8.1 | 4.893 | 5.948 |
| coral | 365 | all | pooled | anomaly R2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | all | pooled | corr2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | all | pooled | hit rate | 0.7729 | 0.7729 | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | all | pooled | hit rate at the declared floor | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | all | pooled | calibration ratio | 0.1235 | 0.1235 | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | all | pooled | pre-clip rate | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | all | pooled | strict top-10% detection (R33) | 0 | 0 | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | all | pooled | detection events | 232 | 232 | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | all | macro | MAE | 19.84 | 19.84 | n/a | n/a | 19.99 | 6.364 | 7.46 |
| coral | 365 | all | macro | anomaly R2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | all | macro | corr2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | all | macro | hit rate | 0.6079 | 0.6079 | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | all | macro | hit rate at the declared floor | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | all | macro | calibration ratio | 0.715 | 0.715 | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | all | macro | pre-clip rate | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | all | macro | strict top-10% detection (R33) | 0 | 0 | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | all | macro | detection events | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | common | pooled | MAE | 8.294 | 8.294 | n/a | n/a | 8.1 | 4.893 | 5.948 |
| coral | 365 | common | pooled | anomaly R2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | common | pooled | corr2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | common | pooled | hit rate | 0.7729 | 0.7729 | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | common | pooled | hit rate at the declared floor | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | common | pooled | calibration ratio | 0.1235 | 0.1235 | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | common | pooled | pre-clip rate | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | common | pooled | strict top-10% detection (R33) | 0 | 0 | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | common | pooled | detection events | 232 | 232 | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | common | macro | MAE | 19.84 | 19.84 | n/a | n/a | 19.99 | 6.364 | 7.46 |
| coral | 365 | common | macro | anomaly R2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | common | macro | corr2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | common | macro | hit rate | 0.6079 | 0.6079 | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | common | macro | hit rate at the declared floor | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | common | macro | calibration ratio | 0.715 | 0.715 | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | common | macro | pre-clip rate | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | common | macro | strict top-10% detection (R33) | 0 | 0 | n/a | n/a | n/a | n/a | n/a |
| coral | 365 | common | macro | detection events | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Verdicts (D74 rule; recomputed = recorded)

| package | lead | rows | verdict | contrast | CI low | CI high | SE | groups | band | band check | history band (beside, never used) | pooled contrast | groups better | sign flips | blocked-jackknife flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| coral | 0 | all | helps | 5.207 | 1.972 | 8.441 | 1.65 | 37 | 0.9176 | recomputed from this run's D75 contrasts, equal | n/a | 1.597 | 23 | Banda Sea and Molucca Islands Belize and west Caribbean Central and northern Great Barrier Reef Eastern Hawaii Hispaniola, Puerto Rico and Lesser Antilles Jamaica Mayotte and Comoros Netherlands Antilles and south Caribbean Persian Gulf South-east Philippines Southern Great Barrier Reef Sulu Sea Sunda Shelf, south-east Asia Taiwan and coastal China | no |
| coral | 0 | common | helps | 5.207 | 1.972 | 8.441 | 1.65 | 37 | 0.9176 | recomputed from this run's D75 contrasts, equal | n/a | 1.597 | 23 | Banda Sea and Molucca Islands Belize and west Caribbean Central and northern Great Barrier Reef Eastern Hawaii Hispaniola, Puerto Rico and Lesser Antilles Jamaica Mayotte and Comoros Netherlands Antilles and south Caribbean Persian Gulf South-east Philippines Southern Great Barrier Reef Sulu Sea Sunda Shelf, south-east Asia Taiwan and coastal China | n/a |
| coral | 183 | common | helps | 1.747 | 0.1224 | 3.372 | 0.8289 | 37 | 0.9176 | recomputed from this run's D75 contrasts, equal | n/a | 0.5848 | 22 | Andaman Islands Banda Sea and Molucca Islands Belize and west Caribbean Fiji Gulf of Oman Hispaniola, Puerto Rico and Lesser Antilles Jamaica Lesser Sunda Islands and Savu Sea Makassar Strait, Indonesia Maldive Islands Netherlands Antilles and south Caribbean North Philippines Southern Great Barrier Reef Strait of Malacca Sulu Sea | n/a |
| coral | 365 | common | declined | 0 | 0 | 0 | 0 | 37 | 0.9176 | recomputed from this run's D75 contrasts, equal | n/a | 0 | 0 |  | n/a |

## Per test year

| package | lead | rows | year | MAE adopted | MAE trees-off | MAE guess-normal | MAE last-5 | anomaly R2 | corr2 | hit rate | hit guess-normal | detection | detection guess-normal | rows |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| coral | 0 | all | 2016 | 12.41 | 16.83 | n/a | n/a | n/a | 0.4969 | 0.5304 | n/a | 0.5795 | n/a | 873 |
| coral | 0 | all | 2017 | 3.569 | 3.231 | n/a | n/a | n/a | 0.01295 | 0.8566 | n/a | 0.2281 | n/a | 565 |
| coral | 0 | all | 2018 | 1.28 | 1.507 | n/a | n/a | n/a | 0.028 | 0.9571 | n/a | 0.1667 | n/a | 443 |
| coral | 0 | all | 2019 | 4.806 | 4.627 | n/a | n/a | n/a | 0.01238 | 0.8005 | n/a | 0.1628 | n/a | 431 |
| coral | 0 | common | 2016 | 12.41 | 16.83 | n/a | n/a | n/a | 0.4969 | 0.5304 | n/a | 0.5795 | n/a | 873 |
| coral | 0 | common | 2017 | 3.569 | 3.231 | n/a | n/a | n/a | 0.01295 | 0.8566 | n/a | 0.2281 | n/a | 565 |
| coral | 0 | common | 2018 | 1.28 | 1.507 | n/a | n/a | n/a | 0.028 | 0.9571 | n/a | 0.1667 | n/a | 443 |
| coral | 0 | common | 2019 | 4.806 | 4.627 | n/a | n/a | n/a | 0.01238 | 0.8005 | n/a | 0.1628 | n/a | 431 |
| coral | 183 | all | 2016 | 14.95 | 16.83 | n/a | n/a | n/a | 0.1193 | 0.5808 | n/a | 0.2614 | n/a | 873 |
| coral | 183 | all | 2017 | 3.465 | 3.231 | n/a | n/a | n/a | 0.0004377 | 0.8708 | n/a | 0.08772 | n/a | 565 |
| coral | 183 | all | 2018 | 1.488 | 1.507 | n/a | n/a | n/a | 0.01579 | 0.9458 | n/a | 0.2857 | n/a | 443 |
| coral | 183 | all | 2019 | 4.996 | 4.627 | n/a | n/a | n/a | 0.0009841 | 0.8028 | n/a | 0.04651 | n/a | 431 |
| coral | 183 | common | 2016 | 14.95 | 16.83 | n/a | n/a | n/a | 0.1193 | 0.5808 | n/a | 0.2614 | n/a | 873 |
| coral | 183 | common | 2017 | 3.465 | 3.231 | n/a | n/a | n/a | 0.0004377 | 0.8708 | n/a | 0.08772 | n/a | 565 |
| coral | 183 | common | 2018 | 1.488 | 1.507 | n/a | n/a | n/a | 0.01579 | 0.9458 | n/a | 0.2857 | n/a | 443 |
| coral | 183 | common | 2019 | 4.996 | 4.627 | n/a | n/a | n/a | 0.0009841 | 0.8028 | n/a | 0.04651 | n/a | 431 |
| coral | 365 | all | 2016 | 16.83 | 16.83 | n/a | n/a | n/a | n/a | 0.5636 | n/a | 0 | n/a | 873 |
| coral | 365 | all | 2017 | 3.231 | 3.231 | n/a | n/a | n/a | n/a | 0.885 | n/a | 0 | n/a | 565 |
| coral | 365 | all | 2018 | 1.507 | 1.507 | n/a | n/a | n/a | n/a | 0.9639 | n/a | 0 | n/a | 443 |
| coral | 365 | all | 2019 | 4.627 | 4.627 | n/a | n/a | n/a | n/a | 0.8538 | n/a | 0 | n/a | 431 |
| coral | 365 | common | 2016 | 16.83 | 16.83 | n/a | n/a | n/a | n/a | 0.5636 | n/a | 0 | n/a | 873 |
| coral | 365 | common | 2017 | 3.231 | 3.231 | n/a | n/a | n/a | n/a | 0.885 | n/a | 0 | n/a | 565 |
| coral | 365 | common | 2018 | 1.507 | 1.507 | n/a | n/a | n/a | n/a | 0.9639 | n/a | 0 | n/a | 443 |
| coral | 365 | common | 2019 | 4.627 | 4.627 | n/a | n/a | n/a | n/a | 0.8538 | n/a | 0 | n/a | 431 |

## Continuity row (the old hard-split test groups alone, same run): continuity, not a replication

| package | lead | rows | groups listed | groups scored | scored units | old test units | MAE adopted | MAE trees-off | MAE guess-normal | MAE last-5 | anomaly R2 | verdict | contrast | CI low | CI high | band | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| coral | 0 | all | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | no continuity group in this run |
| coral | 0 | common | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | no continuity group in this run |
| coral | 183 | all | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | no continuity group in this run |
| coral | 183 | common | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | no continuity group in this run |
| coral | 365 | all | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | no continuity group in this run |
| coral | 365 | common | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | no continuity group in this run |

## Subset rows (reporting only)

| package | lead | rows | row | line | groups | MAE adopted | MAE trees-off | MAE guess-normal | MAE last-5 | anomaly R2 | corr2 | hit rate | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| coral | 0 | all | without seen_during_design (Q49): Andaman Islands, Andaman Sea, Austral Islands, French Polynesia, Bahamas and Florida Keys, Banda Sea and Molucca Islands, Bay of Campeche, Yucatan, Gulf of Mexico, Belize and west Caribbean, Bermuda, Bismarck Sea, New Guinea, Brazil, Caroline Islands, Micronesia, Celebes Sea, Cenderawasih Bay, Papua, Central and northern Great Barrier Reef, Chagos Archipelago, Christmas Island, Indian Ocean, Cocos Keeling Atolls, Indian Ocean, Cook Islands, south-west Pacific, Coral Sea, Costa Rica and Panama, Pacific coast, Cuba and Cayman Islands, Eastern Hawaii, Eastern coast South Africa, Fiji, Flower Garden Banks, Gulf of Mexico, Gilbert Islands, west Kiribati, Gulf of Aden, Gulf of Oman, Gulf of Thailand, Gulf of Tomini, Indonesia, Hispaniola, Puerto Rico and Lesser Antilles, Hong Kong, Honshu, Japan, Jamaica, Java Sea, Johnston Atoll, north central Pacific, Kenya and Tanzania coast, Lakshadweep Islands, Lesser Sunda Islands and Savu Sea, Makassar Strait, Indonesia, Maldive Islands, Marianas, Marshall Islands, Mascarene Islands, Mayotte and Comoros, Milne Bay, Papua New Guinea, Moreton Bay, eastern Australia, Netherlands Antilles and south Caribbean, New Caledonia, Ningaloo Reef and coastal north-west Australia, North Madagascar, North Mozambique coast, North Myanmar and Bangladesh, North Philippines, North Ryukyu Islands, Japan, North Sri Lanka and east India, North Vietnam, North and central Red Sea, Northern Seychelles, Ogasawara Islands, Japan, Palau, Persian Gulf, Phoenix Islands, central Kiribati, Pohnpei and Kosrae, Micronesia, Samoa, Tuvalu and Tonga, Shikoku, Japan, Society Islands, French Polynesia, Socotra Archipelago, Solomon Islands and Bougainville, South Madagascar, South Mozambique coast, South Red Sea, South Ryukyu Islands, Japan, South Vietnam, South-east Philippines, Southern Great Barrier Reef, Strait of Malacca, Sulu Sea, Sunda Shelf, south-east Asia, Taiwan and coastal China, Vanuatu, West Sumatra, Western Tuamotu Archipelago, central Pacific | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | no saved row in this subset |
| coral | 0 | common | without seen_during_design (Q49): Andaman Islands, Andaman Sea, Austral Islands, French Polynesia, Bahamas and Florida Keys, Banda Sea and Molucca Islands, Bay of Campeche, Yucatan, Gulf of Mexico, Belize and west Caribbean, Bermuda, Bismarck Sea, New Guinea, Brazil, Caroline Islands, Micronesia, Celebes Sea, Cenderawasih Bay, Papua, Central and northern Great Barrier Reef, Chagos Archipelago, Christmas Island, Indian Ocean, Cocos Keeling Atolls, Indian Ocean, Cook Islands, south-west Pacific, Coral Sea, Costa Rica and Panama, Pacific coast, Cuba and Cayman Islands, Eastern Hawaii, Eastern coast South Africa, Fiji, Flower Garden Banks, Gulf of Mexico, Gilbert Islands, west Kiribati, Gulf of Aden, Gulf of Oman, Gulf of Thailand, Gulf of Tomini, Indonesia, Hispaniola, Puerto Rico and Lesser Antilles, Hong Kong, Honshu, Japan, Jamaica, Java Sea, Johnston Atoll, north central Pacific, Kenya and Tanzania coast, Lakshadweep Islands, Lesser Sunda Islands and Savu Sea, Makassar Strait, Indonesia, Maldive Islands, Marianas, Marshall Islands, Mascarene Islands, Mayotte and Comoros, Milne Bay, Papua New Guinea, Moreton Bay, eastern Australia, Netherlands Antilles and south Caribbean, New Caledonia, Ningaloo Reef and coastal north-west Australia, North Madagascar, North Mozambique coast, North Myanmar and Bangladesh, North Philippines, North Ryukyu Islands, Japan, North Sri Lanka and east India, North Vietnam, North and central Red Sea, Northern Seychelles, Ogasawara Islands, Japan, Palau, Persian Gulf, Phoenix Islands, central Kiribati, Pohnpei and Kosrae, Micronesia, Samoa, Tuvalu and Tonga, Shikoku, Japan, Society Islands, French Polynesia, Socotra Archipelago, Solomon Islands and Bougainville, South Madagascar, South Mozambique coast, South Red Sea, South Ryukyu Islands, Japan, South Vietnam, South-east Philippines, Southern Great Barrier Reef, Strait of Malacca, Sulu Sea, Sunda Shelf, south-east Asia, Taiwan and coastal China, Vanuatu, West Sumatra, Western Tuamotu Archipelago, central Pacific | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | no saved row in this subset |
| coral | 183 | all | without seen_during_design (Q49): Andaman Islands, Andaman Sea, Austral Islands, French Polynesia, Bahamas and Florida Keys, Banda Sea and Molucca Islands, Bay of Campeche, Yucatan, Gulf of Mexico, Belize and west Caribbean, Bermuda, Bismarck Sea, New Guinea, Brazil, Caroline Islands, Micronesia, Celebes Sea, Cenderawasih Bay, Papua, Central and northern Great Barrier Reef, Chagos Archipelago, Christmas Island, Indian Ocean, Cocos Keeling Atolls, Indian Ocean, Cook Islands, south-west Pacific, Coral Sea, Costa Rica and Panama, Pacific coast, Cuba and Cayman Islands, Eastern Hawaii, Eastern coast South Africa, Fiji, Flower Garden Banks, Gulf of Mexico, Gilbert Islands, west Kiribati, Gulf of Aden, Gulf of Oman, Gulf of Thailand, Gulf of Tomini, Indonesia, Hispaniola, Puerto Rico and Lesser Antilles, Hong Kong, Honshu, Japan, Jamaica, Java Sea, Johnston Atoll, north central Pacific, Kenya and Tanzania coast, Lakshadweep Islands, Lesser Sunda Islands and Savu Sea, Makassar Strait, Indonesia, Maldive Islands, Marianas, Marshall Islands, Mascarene Islands, Mayotte and Comoros, Milne Bay, Papua New Guinea, Moreton Bay, eastern Australia, Netherlands Antilles and south Caribbean, New Caledonia, Ningaloo Reef and coastal north-west Australia, North Madagascar, North Mozambique coast, North Myanmar and Bangladesh, North Philippines, North Ryukyu Islands, Japan, North Sri Lanka and east India, North Vietnam, North and central Red Sea, Northern Seychelles, Ogasawara Islands, Japan, Palau, Persian Gulf, Phoenix Islands, central Kiribati, Pohnpei and Kosrae, Micronesia, Samoa, Tuvalu and Tonga, Shikoku, Japan, Society Islands, French Polynesia, Socotra Archipelago, Solomon Islands and Bougainville, South Madagascar, South Mozambique coast, South Red Sea, South Ryukyu Islands, Japan, South Vietnam, South-east Philippines, Southern Great Barrier Reef, Strait of Malacca, Sulu Sea, Sunda Shelf, south-east Asia, Taiwan and coastal China, Vanuatu, West Sumatra, Western Tuamotu Archipelago, central Pacific | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | no saved row in this subset |
| coral | 183 | common | without seen_during_design (Q49): Andaman Islands, Andaman Sea, Austral Islands, French Polynesia, Bahamas and Florida Keys, Banda Sea and Molucca Islands, Bay of Campeche, Yucatan, Gulf of Mexico, Belize and west Caribbean, Bermuda, Bismarck Sea, New Guinea, Brazil, Caroline Islands, Micronesia, Celebes Sea, Cenderawasih Bay, Papua, Central and northern Great Barrier Reef, Chagos Archipelago, Christmas Island, Indian Ocean, Cocos Keeling Atolls, Indian Ocean, Cook Islands, south-west Pacific, Coral Sea, Costa Rica and Panama, Pacific coast, Cuba and Cayman Islands, Eastern Hawaii, Eastern coast South Africa, Fiji, Flower Garden Banks, Gulf of Mexico, Gilbert Islands, west Kiribati, Gulf of Aden, Gulf of Oman, Gulf of Thailand, Gulf of Tomini, Indonesia, Hispaniola, Puerto Rico and Lesser Antilles, Hong Kong, Honshu, Japan, Jamaica, Java Sea, Johnston Atoll, north central Pacific, Kenya and Tanzania coast, Lakshadweep Islands, Lesser Sunda Islands and Savu Sea, Makassar Strait, Indonesia, Maldive Islands, Marianas, Marshall Islands, Mascarene Islands, Mayotte and Comoros, Milne Bay, Papua New Guinea, Moreton Bay, eastern Australia, Netherlands Antilles and south Caribbean, New Caledonia, Ningaloo Reef and coastal north-west Australia, North Madagascar, North Mozambique coast, North Myanmar and Bangladesh, North Philippines, North Ryukyu Islands, Japan, North Sri Lanka and east India, North Vietnam, North and central Red Sea, Northern Seychelles, Ogasawara Islands, Japan, Palau, Persian Gulf, Phoenix Islands, central Kiribati, Pohnpei and Kosrae, Micronesia, Samoa, Tuvalu and Tonga, Shikoku, Japan, Society Islands, French Polynesia, Socotra Archipelago, Solomon Islands and Bougainville, South Madagascar, South Mozambique coast, South Red Sea, South Ryukyu Islands, Japan, South Vietnam, South-east Philippines, Southern Great Barrier Reef, Strait of Malacca, Sulu Sea, Sunda Shelf, south-east Asia, Taiwan and coastal China, Vanuatu, West Sumatra, Western Tuamotu Archipelago, central Pacific | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | no saved row in this subset |
| coral | 365 | all | without seen_during_design (Q49): Andaman Islands, Andaman Sea, Austral Islands, French Polynesia, Bahamas and Florida Keys, Banda Sea and Molucca Islands, Bay of Campeche, Yucatan, Gulf of Mexico, Belize and west Caribbean, Bermuda, Bismarck Sea, New Guinea, Brazil, Caroline Islands, Micronesia, Celebes Sea, Cenderawasih Bay, Papua, Central and northern Great Barrier Reef, Chagos Archipelago, Christmas Island, Indian Ocean, Cocos Keeling Atolls, Indian Ocean, Cook Islands, south-west Pacific, Coral Sea, Costa Rica and Panama, Pacific coast, Cuba and Cayman Islands, Eastern Hawaii, Eastern coast South Africa, Fiji, Flower Garden Banks, Gulf of Mexico, Gilbert Islands, west Kiribati, Gulf of Aden, Gulf of Oman, Gulf of Thailand, Gulf of Tomini, Indonesia, Hispaniola, Puerto Rico and Lesser Antilles, Hong Kong, Honshu, Japan, Jamaica, Java Sea, Johnston Atoll, north central Pacific, Kenya and Tanzania coast, Lakshadweep Islands, Lesser Sunda Islands and Savu Sea, Makassar Strait, Indonesia, Maldive Islands, Marianas, Marshall Islands, Mascarene Islands, Mayotte and Comoros, Milne Bay, Papua New Guinea, Moreton Bay, eastern Australia, Netherlands Antilles and south Caribbean, New Caledonia, Ningaloo Reef and coastal north-west Australia, North Madagascar, North Mozambique coast, North Myanmar and Bangladesh, North Philippines, North Ryukyu Islands, Japan, North Sri Lanka and east India, North Vietnam, North and central Red Sea, Northern Seychelles, Ogasawara Islands, Japan, Palau, Persian Gulf, Phoenix Islands, central Kiribati, Pohnpei and Kosrae, Micronesia, Samoa, Tuvalu and Tonga, Shikoku, Japan, Society Islands, French Polynesia, Socotra Archipelago, Solomon Islands and Bougainville, South Madagascar, South Mozambique coast, South Red Sea, South Ryukyu Islands, Japan, South Vietnam, South-east Philippines, Southern Great Barrier Reef, Strait of Malacca, Sulu Sea, Sunda Shelf, south-east Asia, Taiwan and coastal China, Vanuatu, West Sumatra, Western Tuamotu Archipelago, central Pacific | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | no saved row in this subset |
| coral | 365 | common | without seen_during_design (Q49): Andaman Islands, Andaman Sea, Austral Islands, French Polynesia, Bahamas and Florida Keys, Banda Sea and Molucca Islands, Bay of Campeche, Yucatan, Gulf of Mexico, Belize and west Caribbean, Bermuda, Bismarck Sea, New Guinea, Brazil, Caroline Islands, Micronesia, Celebes Sea, Cenderawasih Bay, Papua, Central and northern Great Barrier Reef, Chagos Archipelago, Christmas Island, Indian Ocean, Cocos Keeling Atolls, Indian Ocean, Cook Islands, south-west Pacific, Coral Sea, Costa Rica and Panama, Pacific coast, Cuba and Cayman Islands, Eastern Hawaii, Eastern coast South Africa, Fiji, Flower Garden Banks, Gulf of Mexico, Gilbert Islands, west Kiribati, Gulf of Aden, Gulf of Oman, Gulf of Thailand, Gulf of Tomini, Indonesia, Hispaniola, Puerto Rico and Lesser Antilles, Hong Kong, Honshu, Japan, Jamaica, Java Sea, Johnston Atoll, north central Pacific, Kenya and Tanzania coast, Lakshadweep Islands, Lesser Sunda Islands and Savu Sea, Makassar Strait, Indonesia, Maldive Islands, Marianas, Marshall Islands, Mascarene Islands, Mayotte and Comoros, Milne Bay, Papua New Guinea, Moreton Bay, eastern Australia, Netherlands Antilles and south Caribbean, New Caledonia, Ningaloo Reef and coastal north-west Australia, North Madagascar, North Mozambique coast, North Myanmar and Bangladesh, North Philippines, North Ryukyu Islands, Japan, North Sri Lanka and east India, North Vietnam, North and central Red Sea, Northern Seychelles, Ogasawara Islands, Japan, Palau, Persian Gulf, Phoenix Islands, central Kiribati, Pohnpei and Kosrae, Micronesia, Samoa, Tuvalu and Tonga, Shikoku, Japan, Society Islands, French Polynesia, Socotra Archipelago, Solomon Islands and Bougainville, South Madagascar, South Mozambique coast, South Red Sea, South Ryukyu Islands, Japan, South Vietnam, South-east Philippines, Southern Great Barrier Reef, Strait of Malacca, Sulu Sea, Sunda Shelf, south-east Asia, Taiwan and coastal China, Vanuatu, West Sumatra, Western Tuamotu Archipelago, central Pacific | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | no saved row in this subset |

## Per report stratum (R34; lead 0, rows 'all')

The stratum tables are copied from the engine's per_stratum.csv (report pass, the same saved rows); NOT recomputed here: the units' stratum values and the donor-row edges are not in the saved rows. Strata are the donor rows' quartiles, right-closed (D73).

| package | stratum column | stratum | edges q25 / q50 / q75 | rows | MAE adopted | MAE trees-off | MAE guess-normal | MAE last-5 | anomaly R2 | corr2 | hit rate | detection |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| coral | programme | AGRRA | per value | 1 | 5.541 | 10.11 | n/a | n/a | n/a | n/a | 0 | n/a |
| coral | programme | FRRP | per value | 190 | 7.66 | 10.91 | n/a | n/a | n/a | 0.007109 | 0.4158 | 0.05556 |
| coral | programme | McClanahan | per value | 189 | 35.06 | 53.84 | n/a | n/a | n/a | 0.2277 | 0.1376 | 0.1579 |
| coral | programme | Reef_Check | per value | 1932 | 3.829 | 3.581 | n/a | n/a | n/a | 0.06008 | 0.8339 | 0.1959 |

## Per group (rows 'all')

Each group's score is noisy; the pooled headline and the all-group jackknife decide, never one group.

| package | lead | group | scored units | overlap block | MAE adopted | MAE trees-off | MAE guess-normal | MAE last-5 | contrast | anomaly R2 | hit rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| coral | 0 | Andaman Islands | 8 | Andaman Islands | 47.36 | 71.91 | n/a | n/a | 24.56 | n/a | 0 |
| coral | 0 | Andaman Sea | 63 | Andaman Sea | 3.24 | 4.063 | n/a | n/a | 0.8238 | n/a | 0.9365 |
| coral | 0 | Bahamas and Florida Keys | 206 | Bahamas and Florida Keys | 7.569 | 10.53 | n/a | n/a | 2.963 | n/a | 0.4272 |
| coral | 0 | Banda Sea and Molucca Islands | 71 | Banda Sea and Molucca Islands | 1.486 | 1.436 | n/a | n/a | -0.05014 | n/a | 0.9014 |
| coral | 0 | Belize and west Caribbean | 22 | Belize and west Caribbean | 6.068 | 5.693 | n/a | n/a | -0.3757 | n/a | 0.6818 |
| coral | 0 | Celebes Sea | 25 | Celebes Sea | 1.867 | 1.95 | n/a | n/a | 0.08261 | n/a | 0.88 |
| coral | 0 | Central and northern Great Barrier Reef | 48 | Central and northern Great Barrier Reef | 23.88 | 20.85 | n/a | n/a | -3.03 | n/a | 0.2917 |
| coral | 0 | Eastern Hawaii | 1 | Eastern Hawaii | 1.856 | 1 | n/a | n/a | -0.8563 | n/a | 1 |
| coral | 0 | Fiji | 73 | Fiji | 3.645 | 4.031 | n/a | n/a | 0.3865 | n/a | 0.863 |
| coral | 0 | Gulf of Oman | 13 | Gulf of Oman | 0.6346 | 1.115 | n/a | n/a | 0.4808 | n/a | 1 |
| coral | 0 | Hispaniola, Puerto Rico and Lesser Antilles | 171 | Hispaniola, Puerto Rico and Lesser Antilles | 2.387 | 1.616 | n/a | n/a | -0.7707 | n/a | 0.8772 |
| coral | 0 | Jamaica | 49 | Jamaica | 3.303 | 1.732 | n/a | n/a | -1.571 | n/a | 0.8367 |
| coral | 0 | Java Sea | 18 | Java Sea | 33.97 | 41.46 | n/a | n/a | 7.485 | n/a | 0 |
| coral | 0 | Kenya and Tanzania coast | 35 | Kenya and Tanzania coast | 21.44 | 48.49 | n/a | n/a | 27.04 | n/a | 0.1143 |
| coral | 0 | Lakshadweep Islands | 14 | Lakshadweep Islands | 48.07 | 84.49 | n/a | n/a | 36.42 | n/a | 0 |
| coral | 0 | Lesser Sunda Islands and Savu Sea | 164 | Lesser Sunda Islands and Savu Sea | 8.024 | 9.259 | n/a | n/a | 1.234 | n/a | 0.7805 |
| coral | 0 | Makassar Strait, Indonesia | 2 | Makassar Strait, Indonesia | 3.782 | 7.8 | n/a | n/a | 4.018 | n/a | 0.5 |
| coral | 0 | Maldive Islands | 81 | Maldive Islands | 5.103 | 5.392 | n/a | n/a | 0.2886 | n/a | 0.716 |
| coral | 0 | Mascarene Islands | 14 | Mascarene Islands | 42.02 | 45.88 | n/a | n/a | 3.86 | n/a | 0 |
| coral | 0 | Mayotte and Comoros | 7 | Mayotte and Comoros+North Madagascar | 2.421 | 0.9643 | n/a | n/a | -1.457 | n/a | 0.7143 |
| coral | 0 | Moreton Bay, eastern Australia | 75 | Moreton Bay, eastern Australia+Southern Great Barrier Reef | 6.018 | 6.018 | n/a | n/a | 0.0002407 | n/a | 0.7067 |
| coral | 0 | Netherlands Antilles and south Caribbean | 10 | Netherlands Antilles and south Caribbean | 4.856 | 1 | n/a | n/a | -3.856 | n/a | 0.7 |
| coral | 0 | Ningaloo Reef and coastal north-west Australia | 16 | Ningaloo Reef and coastal north-west Australia | 5.644 | 6.721 | n/a | n/a | 1.077 | n/a | 0.6875 |
| coral | 0 | North Madagascar | 28 | Mayotte and Comoros+North Madagascar | 43.13 | 58.7 | n/a | n/a | 15.57 | n/a | 0.07143 |
| coral | 0 | North Philippines | 19 | North Philippines | 3.54 | 6.974 | n/a | n/a | 3.433 | n/a | 0.8421 |
| coral | 0 | North Ryukyu Islands, Japan | 4 | North Ryukyu Islands, Japan | 65.44 | 77.47 | n/a | n/a | 12.04 | n/a | 0 |
| coral | 0 | North and central Red Sea | 49 | North and central Red Sea | 0.1394 | 0.977 | n/a | n/a | 0.8376 | n/a | 1 |
| coral | 0 | Persian Gulf | 11 | Persian Gulf | 4.397 | 4.205 | n/a | n/a | -0.1927 | n/a | 0.9091 |
| coral | 0 | Society Islands, French Polynesia | 113 | Society Islands, French Polynesia | 2.055 | 2.252 | n/a | n/a | 0.1975 | n/a | 0.9027 |
| coral | 0 | Solomon Islands and Bougainville | 16 | Solomon Islands and Bougainville | 12.14 | 29.2 | n/a | n/a | 17.06 | n/a | 0.25 |
| coral | 0 | South Madagascar | 12 | South Madagascar | 56.87 | 73.87 | n/a | n/a | 17 | n/a | 0 |
| coral | 0 | South-east Philippines | 16 | South-east Philippines | 1.505 | 1.195 | n/a | n/a | -0.3097 | n/a | 0.9375 |
| coral | 0 | Southern Great Barrier Reef | 32 | Moreton Bay, eastern Australia+Southern Great Barrier Reef | 6.239 | 5.688 | n/a | n/a | -0.5517 | n/a | 0.6562 |
| coral | 0 | Strait of Malacca | 14 | Strait of Malacca+West Sumatra | 54.26 | 83.58 | n/a | n/a | 29.31 | n/a | 0 |
| coral | 0 | Sulu Sea | 263 | Sulu Sea | 1.45 | 1.444 | n/a | n/a | -0.006482 | n/a | 0.9354 |
| coral | 0 | Sunda Shelf, south-east Asia | 445 | Sunda Shelf, south-east Asia | 4.222 | 3.909 | n/a | n/a | -0.3127 | n/a | 0.8067 |
| coral | 0 | Taiwan and coastal China | 104 | Taiwan and coastal China | 1.481 | 1.294 | n/a | n/a | -0.1862 | n/a | 0.9135 |
| coral | 183 | Andaman Islands | 8 | Andaman Islands | 72.26 | 71.91 | n/a | n/a | -0.3472 | n/a | 0 |
| coral | 183 | Andaman Sea | 63 | Andaman Sea | 3.455 | 4.063 | n/a | n/a | 0.6088 | n/a | 0.9365 |
| coral | 183 | Bahamas and Florida Keys | 206 | Bahamas and Florida Keys | 7.11 | 10.53 | n/a | n/a | 3.422 | n/a | 0.5194 |
| coral | 183 | Banda Sea and Molucca Islands | 71 | Banda Sea and Molucca Islands | 2.097 | 1.436 | n/a | n/a | -0.6612 | n/a | 0.831 |
| coral | 183 | Belize and west Caribbean | 22 | Belize and west Caribbean | 6.195 | 5.693 | n/a | n/a | -0.5018 | n/a | 0.7273 |
| coral | 183 | Celebes Sea | 25 | Celebes Sea | 1.882 | 1.95 | n/a | n/a | 0.06764 | n/a | 0.92 |
| coral | 183 | Central and northern Great Barrier Reef | 48 | Central and northern Great Barrier Reef | 20.78 | 20.85 | n/a | n/a | 0.06772 | n/a | 0.5 |
| coral | 183 | Eastern Hawaii | 1 | Eastern Hawaii | 0.7344 | 1 | n/a | n/a | 0.2656 | n/a | 1 |
| coral | 183 | Fiji | 73 | Fiji | 4.143 | 4.031 | n/a | n/a | -0.1113 | n/a | 0.863 |
| coral | 183 | Gulf of Oman | 13 | Gulf of Oman | 1.169 | 1.115 | n/a | n/a | -0.05369 | n/a | 1 |
| coral | 183 | Hispaniola, Puerto Rico and Lesser Antilles | 171 | Hispaniola, Puerto Rico and Lesser Antilles | 3.483 | 1.616 | n/a | n/a | -1.867 | n/a | 0.807 |
| coral | 183 | Jamaica | 49 | Jamaica | 2.796 | 1.732 | n/a | n/a | -1.064 | n/a | 0.7959 |
| coral | 183 | Java Sea | 18 | Java Sea | 40.06 | 41.46 | n/a | n/a | 1.397 | n/a | 0 |
| coral | 183 | Kenya and Tanzania coast | 35 | Kenya and Tanzania coast | 41.01 | 48.49 | n/a | n/a | 7.479 | n/a | 0.02857 |
| coral | 183 | Lakshadweep Islands | 14 | Lakshadweep Islands | 59.13 | 84.49 | n/a | n/a | 25.36 | n/a | 0 |
| coral | 183 | Lesser Sunda Islands and Savu Sea | 164 | Lesser Sunda Islands and Savu Sea | 10.47 | 9.259 | n/a | n/a | -1.214 | n/a | 0.6402 |
| coral | 183 | Makassar Strait, Indonesia | 2 | Makassar Strait, Indonesia | 8.688 | 7.8 | n/a | n/a | -0.8881 | n/a | 0 |
| coral | 183 | Maldive Islands | 81 | Maldive Islands | 5.642 | 5.392 | n/a | n/a | -0.2498 | n/a | 0.8272 |
| coral | 183 | Mascarene Islands | 14 | Mascarene Islands | 44.52 | 45.88 | n/a | n/a | 1.354 | n/a | 0.07143 |
| coral | 183 | Mayotte and Comoros | 7 | Mayotte and Comoros+North Madagascar | 0.5064 | 0.9643 | n/a | n/a | 0.4579 | n/a | 1 |
| coral | 183 | Moreton Bay, eastern Australia | 75 | Moreton Bay, eastern Australia+Southern Great Barrier Reef | 6.004 | 6.018 | n/a | n/a | 0.01472 | n/a | 0.7067 |
| coral | 183 | Netherlands Antilles and south Caribbean | 10 | Netherlands Antilles and south Caribbean | 1.575 | 1 | n/a | n/a | -0.5755 | n/a | 0.9 |
| coral | 183 | Ningaloo Reef and coastal north-west Australia | 16 | Ningaloo Reef and coastal north-west Australia | 6.381 | 6.721 | n/a | n/a | 0.3408 | n/a | 0.4375 |
| coral | 183 | North Madagascar | 28 | Mayotte and Comoros+North Madagascar | 57.9 | 58.7 | n/a | n/a | 0.8026 | n/a | 0.25 |
| coral | 183 | North Philippines | 19 | North Philippines | 7.071 | 6.974 | n/a | n/a | -0.09713 | n/a | 0.4737 |
| coral | 183 | North Ryukyu Islands, Japan | 4 | North Ryukyu Islands, Japan | 71.52 | 77.47 | n/a | n/a | 5.953 | n/a | 0 |
| coral | 183 | North and central Red Sea | 49 | North and central Red Sea | 0.1589 | 0.977 | n/a | n/a | 0.8182 | n/a | 1 |
| coral | 183 | Persian Gulf | 11 | Persian Gulf | 3.927 | 4.205 | n/a | n/a | 0.2775 | n/a | 0.8182 |
| coral | 183 | Society Islands, French Polynesia | 113 | Society Islands, French Polynesia | 2.016 | 2.252 | n/a | n/a | 0.2364 | n/a | 0.9115 |
| coral | 183 | Solomon Islands and Bougainville | 16 | Solomon Islands and Bougainville | 17.34 | 29.2 | n/a | n/a | 11.86 | n/a | 0.3125 |
| coral | 183 | South Madagascar | 12 | South Madagascar | 62.64 | 73.87 | n/a | n/a | 11.23 | n/a | 0.08333 |
| coral | 183 | South-east Philippines | 16 | South-east Philippines | 1.152 | 1.195 | n/a | n/a | 0.04284 | n/a | 1 |
| coral | 183 | Southern Great Barrier Reef | 32 | Moreton Bay, eastern Australia+Southern Great Barrier Reef | 6.224 | 5.688 | n/a | n/a | -0.5368 | n/a | 0.6562 |
| coral | 183 | Strait of Malacca | 14 | Strait of Malacca+West Sumatra | 83.76 | 83.58 | n/a | n/a | -0.1849 | n/a | 0 |
| coral | 183 | Sulu Sea | 263 | Sulu Sea | 1.492 | 1.444 | n/a | n/a | -0.04797 | n/a | 0.9696 |
| coral | 183 | Sunda Shelf, south-east Asia | 445 | Sunda Shelf, south-east Asia | 3.642 | 3.909 | n/a | n/a | 0.2673 | n/a | 0.8921 |
| coral | 183 | Taiwan and coastal China | 104 | Taiwan and coastal China | 0.5769 | 1.294 | n/a | n/a | 0.7176 | n/a | 0.9615 |
| coral | 365 | Andaman Islands | 8 | Andaman Islands | 71.91 | 71.91 | n/a | n/a | 0 | n/a | 0 |
| coral | 365 | Andaman Sea | 63 | Andaman Sea | 4.063 | 4.063 | n/a | n/a | 0 | n/a | 0.9365 |
| coral | 365 | Bahamas and Florida Keys | 206 | Bahamas and Florida Keys | 10.53 | 10.53 | n/a | n/a | 0 | n/a | 0.3592 |
| coral | 365 | Banda Sea and Molucca Islands | 71 | Banda Sea and Molucca Islands | 1.436 | 1.436 | n/a | n/a | 0 | n/a | 0.9577 |
| coral | 365 | Belize and west Caribbean | 22 | Belize and west Caribbean | 5.693 | 5.693 | n/a | n/a | 0 | n/a | 0.7727 |
| coral | 365 | Celebes Sea | 25 | Celebes Sea | 1.95 | 1.95 | n/a | n/a | 0 | n/a | 0.88 |
| coral | 365 | Central and northern Great Barrier Reef | 48 | Central and northern Great Barrier Reef | 20.85 | 20.85 | n/a | n/a | 0 | n/a | 0.4583 |
| coral | 365 | Eastern Hawaii | 1 | Eastern Hawaii | 1 | 1 | n/a | n/a | 0 | n/a | 1 |
| coral | 365 | Fiji | 73 | Fiji | 4.031 | 4.031 | n/a | n/a | 0 | n/a | 0.8493 |
| coral | 365 | Gulf of Oman | 13 | Gulf of Oman | 1.115 | 1.115 | n/a | n/a | 0 | n/a | 1 |
| coral | 365 | Hispaniola, Puerto Rico and Lesser Antilles | 171 | Hispaniola, Puerto Rico and Lesser Antilles | 1.616 | 1.616 | n/a | n/a | 0 | n/a | 0.9357 |
| coral | 365 | Jamaica | 49 | Jamaica | 1.732 | 1.732 | n/a | n/a | 0 | n/a | 0.9184 |
| coral | 365 | Java Sea | 18 | Java Sea | 41.46 | 41.46 | n/a | n/a | 0 | n/a | 0 |
| coral | 365 | Kenya and Tanzania coast | 35 | Kenya and Tanzania coast | 48.49 | 48.49 | n/a | n/a | 0 | n/a | 0 |
| coral | 365 | Lakshadweep Islands | 14 | Lakshadweep Islands | 84.49 | 84.49 | n/a | n/a | 0 | n/a | 0 |
| coral | 365 | Lesser Sunda Islands and Savu Sea | 164 | Lesser Sunda Islands and Savu Sea | 9.259 | 9.259 | n/a | n/a | 0 | n/a | 0.7744 |
| coral | 365 | Makassar Strait, Indonesia | 2 | Makassar Strait, Indonesia | 7.8 | 7.8 | n/a | n/a | 0 | n/a | 0.5 |
| coral | 365 | Maldive Islands | 81 | Maldive Islands | 5.392 | 5.392 | n/a | n/a | 0 | n/a | 0.8395 |
| coral | 365 | Mascarene Islands | 14 | Mascarene Islands | 45.88 | 45.88 | n/a | n/a | 0 | n/a | 0.1429 |
| coral | 365 | Mayotte and Comoros | 7 | Mayotte and Comoros+North Madagascar | 0.9643 | 0.9643 | n/a | n/a | 0 | n/a | 1 |
| coral | 365 | Moreton Bay, eastern Australia | 75 | Moreton Bay, eastern Australia+Southern Great Barrier Reef | 6.018 | 6.018 | n/a | n/a | 0 | n/a | 0.6933 |
| coral | 365 | Netherlands Antilles and south Caribbean | 10 | Netherlands Antilles and south Caribbean | 1 | 1 | n/a | n/a | 0 | n/a | 1 |
| coral | 365 | Ningaloo Reef and coastal north-west Australia | 16 | Ningaloo Reef and coastal north-west Australia | 6.721 | 6.721 | n/a | n/a | 0 | n/a | 0.4375 |
| coral | 365 | North Madagascar | 28 | Mayotte and Comoros+North Madagascar | 58.7 | 58.7 | n/a | n/a | 0 | n/a | 0.25 |
| coral | 365 | North Philippines | 19 | North Philippines | 6.974 | 6.974 | n/a | n/a | 0 | n/a | 0.4737 |
| coral | 365 | North Ryukyu Islands, Japan | 4 | North Ryukyu Islands, Japan | 77.47 | 77.47 | n/a | n/a | 0 | n/a | 0 |
| coral | 365 | North and central Red Sea | 49 | North and central Red Sea | 0.977 | 0.977 | n/a | n/a | 0 | n/a | 1 |
| coral | 365 | Persian Gulf | 11 | Persian Gulf | 4.205 | 4.205 | n/a | n/a | 0 | n/a | 0.9091 |
| coral | 365 | Society Islands, French Polynesia | 113 | Society Islands, French Polynesia | 2.252 | 2.252 | n/a | n/a | 0 | n/a | 0.9115 |
| coral | 365 | Solomon Islands and Bougainville | 16 | Solomon Islands and Bougainville | 29.2 | 29.2 | n/a | n/a | 0 | n/a | 0 |
| coral | 365 | South Madagascar | 12 | South Madagascar | 73.87 | 73.87 | n/a | n/a | 0 | n/a | 0 |
| coral | 365 | South-east Philippines | 16 | South-east Philippines | 1.195 | 1.195 | n/a | n/a | 0 | n/a | 1 |
| coral | 365 | Southern Great Barrier Reef | 32 | Moreton Bay, eastern Australia+Southern Great Barrier Reef | 5.688 | 5.688 | n/a | n/a | 0 | n/a | 0.6562 |
| coral | 365 | Strait of Malacca | 14 | Strait of Malacca+West Sumatra | 83.58 | 83.58 | n/a | n/a | 0 | n/a | 0 |
| coral | 365 | Sulu Sea | 263 | Sulu Sea | 1.444 | 1.444 | n/a | n/a | 0 | n/a | 0.9658 |
| coral | 365 | Sunda Shelf, south-east Asia | 445 | Sunda Shelf, south-east Asia | 3.909 | 3.909 | n/a | n/a | 0 | n/a | 0.8989 |
| coral | 365 | Taiwan and coastal China | 104 | Taiwan and coastal China | 1.294 | 1.294 | n/a | n/a | 0 | n/a | 0.9712 |

## Disclosures (from each run's records)

### coral

- **limit:** Type 3 (plan 4.1 step 10) is not built
- **limit:** table features are vouched by the package owner (owner ruling U2): the engine recomputes none of them and checks only the declared feature-end day (T-FEATEND); the G-DERIVED recompute and the look-ahead canary are not run on tables
- **limit:** the table option builds the neighbour router kind only (U3); per-unit and region tables are refused (O16)
- **limit:** the scored rows are the package's test marks (U1), not R18 (2)'s stride pick
- **limit:** the continuity row (continuity.csv), nearest-donor distances and distance bands, report.html and part_draft.md are not built (treeroute_report)
- **limit:** the band is derived from this run's own contrasts; registry/bands.csv and registry/index.csv are not written
- **limit:** 'freeze' verdicts are refused: per-cut frozen pools are not built
- **limit:** a time-varying report stratum is reported per row (a string stratum per value, a numeric one by quartiles)
- **listed_in_reports:** listed in every report (watch / keep_unreviewed): n_dhw_ge8_before, days_since_dhw4, mhw_thr_gap
- **donor_only_groups:** 46 groups trained only (no test row): their trees serve every bank and their rows every pool and the decision surface; nothing is scored for them (1874 train rows with a valid label): Austral Islands, French Polynesia, Bay of Campeche, Yucatan, Gulf of Mexico, Bermuda, Bismarck Sea, New Guinea, Brazil, Caroline Islands, Micronesia, Cenderawasih Bay, Papua, Chagos Archipelago, Christmas Island, Indian Ocean, Cocos Keeling Atolls, Indian Ocean, Cook Islands, south-west Pacific, Coral Sea, Costa Rica and Panama, Pacific coast, Cuba and Cayman Islands, Eastern coast South Africa, Flower Garden Banks, Gulf of Mexico, Gilbert Islands, west Kiribati, Gulf of Aden, Gulf of Thailand, Gulf of Tomini, Indonesia, Hong Kong, Honshu, Japan, Johnston Atoll, north central Pacific, Marianas, Marshall Islands, Milne Bay, Papua New Guinea, New Caledonia, North Mozambique coast, North Myanmar and Bangladesh, North Sri Lanka and east India, North Vietnam, Northern Seychelles, Ogasawara Islands, Japan, Palau, Phoenix Islands, central Kiribati, Pohnpei and Kosrae, Micronesia, Samoa, Tuvalu and Tonga, Shikoku, Japan, Socotra Archipelago, South Mozambique coast, South Red Sea, South Ryukyu Islands, Japan, South Vietnam, Vanuatu, West Sumatra, Western Tuamotu Archipelago, central Pacific. A scored group's overlap_block (per_group.csv) can name one of them: that names a block partner, not a scored group
