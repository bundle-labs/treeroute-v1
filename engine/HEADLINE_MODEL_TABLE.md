# Headline runs: the model's own scores per problem and lead (2026-10-17)

Computed from the saved row-level test predictions of the finished headline runs (test years: PM2.5, NDVI and defo 2020-2023; fire 2019-2022; coral 2016-2019; from each run's derived.json R5; header corrected 2026-10-26, it said 2020-2023 for all). Defo (annual target; leads: nowcast and 1 year) added 2026-10-19.
- **Model:** the arm the adaptation layer chose on the nowcast, pinned at every lead.
- **Normal:** each unit's guess-normal.
- **Anomaly R2:** 1 - SSE(model) / SSE(normal); it matches the table builder.
- **Safety check:** at each lead, the pinned arm against its own-link trees-off on that lead's guard rows. If it fails, the headline answer is the plain normal (rule D86), but the model's forecast is still saved and scored here.

| Problem | Lead | Chosen tool (scale / tool / weighting / penalty level) | Safety check | Model MAE | Normal MAE | Model vs normal | Anomaly R2 | corr2 |
|---|---|---|---|---|---|---|---|---|
| PM2.5 | 0 | log / corrector / none / 30 | adopted | 3.588 | 4.032 | -11.0% | 0.185 | 0.852 |
| PM2.5 | 6 | (pinned) | passed: model kept | 3.846 | 4.054 | -5.1% | 0.069 | 0.830 |
| PM2.5 | 12 | (pinned) | failed: normal output | 3.840 | 4.084 | -6.0% | 0.078 | 0.831 |
| NDVI | 0 | raw / plain / none / 1 | adopted | 0.0315 | 0.0394 | -20.2% | 0.317 | 0.963 |
| NDVI | 6 | (pinned) | failed: normal output | 0.0392 | 0.0396 | -0.9% | 0.002 | 0.945 |
| NDVI | 12 | (pinned) | failed: normal output | 0.0400 | 0.0396 | +1.0% | -0.030 | 0.944 |
| Fire | 0 | arcsine / corrector / GLS-weighted / 100 | adopted | 0.00439 | 0.00626 | -29.9% | 0.026 | 0.222 |
| Fire | 6 | (pinned) | failed: normal output | 0.00452 | 0.00631 | -28.4% | 0.023 | 0.214 |
| Fire | 12 | (pinned) | failed: normal output | 0.00450 | 0.00631 | -28.6% | 0.024 | 0.214 |
| Defo | 0 | log / corrector / none / region router level 0.1 | adopted | 0.00542 | 0.00841 | -35.6% | 0.052 | 0.017 |
| Defo | 1 yr | (pinned) | passed: model kept | 0.00541 | 0.00841 | -35.7% | 0.050 | 0.016 |
| Coral | 0 | arcsine / corrector / GLS-weighted / neighbour router level 100, ratio 1 | adopted | 6.698 | 8.294 (donor median) | -19.2% | n/a | 0.464 |
| Coral | 183 d | (pinned) | passed: model kept | 7.710 | 8.294 | -7.0% | n/a | 0.139 |
| Coral | 365 d | (pinned) | failed: donor median output (model's own 8.281) | 8.281 | 8.294 | -0.2% | n/a | 0.038 |

Fire's predict-zero MAE is 0.00428: on this mostly-zero target MAE rewards timidity, so report corr2 and detection beside it.
Defo's predict-zero MAE is 0.00612 and its own-link trees-off 0.00572: the model beats both, by -11.5% and -5.2%.

Coral (added 2026-10-20; run D:/treeroute/runs/coral/headline/20261020_f3b8e3da, lock FREEZE_20261020T100907Z, engine 930d961c):
percent bleached per survey visit, test years 2016-2019, 2,312 test surveys in 37 ecoregions (46 donor-only groups train only).
Its 'normal' is the donor-row median (rulings V1, R34): a single constant. No anomaly R2 (most sites have one visit).
Predict-zero MAE 8.100. By programme at the nowcast (report per programme first; pooled mixes programmes):
McClanahan 35.06 vs predict-zero 54.82 (189 rows); FRRP 7.66 vs 11.74 (190); Reef_Check 3.83 vs 3.17 (1,932): predict-zero WINS on Reef_Check.
Flattening guard (edge b, severe rows observed mean ~56-58%): mean prediction 17.8 (nowcast), 5.6 (183 d), 4.4 (365 d).
