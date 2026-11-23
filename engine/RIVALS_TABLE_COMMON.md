# Common rivals: all five problems (deciding contrast: rival's guarded answer vs our headline answer)

Cell = rival MAE + verdict for OURS: WIN = we beat it, loss = it beats us, ? = cannot tell, = equivalent, same = identical answers (both fell back to the normal). TIMID = the rival's win comes from cautious near-zero predictions. Lower MAE is better. Built 2026-10-25 from the five boards (Parts 600, 606, 610, 614, 616).

| Problem | Lead | Ours (MAE) | Ridge | Random Forest | LightGBM | LightGBM-Tweedie | L1-boosting | Ours top corr2 (ties count) |
|---|---|---|---|---|---|---|---|---|
| Coral (% bleached) | 0 | 6.698 | 7.198 ? | 7.376 ? | 7.146 ? | 7.255 ? | 6.356 loss | no |
| Coral (% bleached) | 183 | 7.710 | 8.122 ? | 8.004 ? | 7.824 ? | 8.065 ? | 7.956 ? | yes |
| Coral (% bleached) | 365 | 8.294 | 8.017 ? TIMID | 8.165 ? TIMID | 8.245 ? TIMID | 8.078 ? TIMID | 7.935 ? TIMID | no |
| Fire (burned fraction) | 0 | 0.00439 | 0.00626 WIN | 0.00427 ? TIMID | 0.00429 ? TIMID | 0.00404 loss TIMID | - | yes |
| Fire (burned fraction) | 6 | 0.00631 | 0.00631 same | 0.00631 same | 0.00631 same | 0.00416 loss TIMID | - | yes |
| Fire (burned fraction) | 12 | 0.00631 | 0.00631 same | 0.00631 same | 0.00631 same | 0.00412 loss TIMID | - | yes |
| PM2.5 (ug/m3) | 0 | 3.588 | 3.426 ? | 3.692 WIN | 3.552 ? | - | - | no |
| PM2.5 (ug/m3) | 6 | 3.846 | 3.600 loss | 3.822 ? | 4.054 WIN | - | - | no |
| PM2.5 (ug/m3) | 12 | 4.084 | 3.656 loss | 3.890 loss | 3.844 loss | - | - | no |
| Defo (loss fraction) | 0 | 0.00542 | 0.00581 WIN | 0.00549 ? | 0.00547 = | 0.00631 WIN | - | no |
| Defo (loss fraction) | 1 | 0.00541 | 0.00567 WIN | 0.00538 = TIMID | 0.00536 = TIMID | 0.00620 WIN | - | no |
| NDVI | 0 | 0.0315 | 0.0429 WIN | 0.0352 WIN | 0.0320 ? | - | - | yes |
| NDVI | 6 | 0.0396 | 0.0384 loss | 0.0396 same | 0.0396 same | - | - | no |
| NDVI | 12 | 0.0396 | 0.0396 same | 0.0396 same | 0.0396 same | - | - | yes |

Verdict count over all cells: = 3, ? 21, WIN 9, loss 9, same 11
