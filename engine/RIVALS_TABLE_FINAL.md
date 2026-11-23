# Final rival table (common + human), 2026-10-25 (notes corrected 2026-10-26)

Source: D:\treeroute\rivals_table\20261025T162302876402Z\RIVALS_TABLE.csv (join of the five common boards, Parts 600/606/610/614/616, and the human boards, Parts 617/618; fire human rivals = Part B, pending).
Deciding contrast everywhere: the rival's guarded answer vs our headline answer. WIN = ours beats the rival; loss = the rival beats ours; ? = cannot tell; = equivalent; same = identical answers (both fell back to the normal). Lower MAE is better. Human rows listed are the deciding ones (tier P or L); advantaged (A), extension (X) and placebo rows are in the full table. Human cells compare on the rival's deciding rows ('ours' there is our MAE on those rows; coral: NOAA covers all 2,312 test rows and the deciding contrast uses 2,290 rows in 32 of 37 ecoregions with >= 10 rows). When a rival's guard failed, its deciding answer is the normal, so that WIN is ours beating the normal; the raw rival is in the full table. * on a common verdict = that rival's guard failed, so its deciding answer is the normal (a WIN* is ours beating the normal).

| Problem | Lead | Ours (MAE) | Common rivals (Ridge / RF / LightGBM / Tweedie / L1) | Human rivals (deciding rows) |
|---|---|---|---|---|
| Coral | 0 | 6.698 | ? / ? / ? / ? / loss | NOAA heat-stress rule 8.089 vs ours 6.471: ? |
| Coral | 183 | 7.710 | ? / ? / ? / ? / ? | NOAA heat-stress rule 7.977 vs ours 7.397: WIN (vs rule fed old heat) [rival's guard failed: its answer = the normal] |
| Coral | 365 | 8.294 | ? (timid) / ? (timid) / ? (timid) / ? (timid) / ? (timid) | NOAA heat-stress rule 7.977 vs ours 7.977: same [rival's guard failed: its answer = the normal] |
| Fire | 0 | 0.00439 | WIN* / ? (timid) / ? (timid) / loss (timid) / - | pending (Part B) |
| Fire | 6 | 0.00631 | same / same / same / loss (timid) / - | pending (Part B) |
| Fire | 12 | 0.00631 | same / same / same / loss (timid) / - | pending (Part B) |
| PM2.5 | 0 | 3.588 | ? / WIN / ? / - / - | MERRA-2 (lag 1) 8.444 vs ours 3.588: ? |
| PM2.5 | 6 | 3.846 | loss / ? / WIN* / - / - | no published forecast at this lead |
| PM2.5 | 12 | 4.084 | loss / loss / loss / - / - | no published forecast at this lead |
| Defo | 0 | 0.00542 | WIN / ? / = / WIN / - | VT0007 shipped 0.00840 vs ours 0.00542: WIN [rival's guard failed: its answer = the normal]; VT0007 calibrated 0.00840 vs ours 0.00542: WIN [rival's guard failed: its answer = the normal]; VT0007 frozen-2019 0.00840 vs ours 0.00542: WIN [rival's guard failed: its answer = the normal] |
| Defo | 1 | 0.00541 | WIN / = (timid) / = (timid) / WIN / - | VT0007 shipped 0.00840 vs ours 0.00541: WIN [rival's guard failed: its answer = the normal]; VT0007 calibrated 0.00840 vs ours 0.00541: WIN [rival's guard failed: its answer = the normal]; VT0007 frozen-2019 0.00840 vs ours 0.00541: WIN [rival's guard failed: its answer = the normal] |
| NDVI | 0 | 0.0315 | WIN / WIN / ? / - / - | rain-lag regression (H1) 0.0342 vs ours 0.0315: WIN; Kraft LSTM 0.0394 vs ours 0.0315: WIN [rival's guard failed: its answer = the normal] |
| NDVI | 6 | 0.0396 | loss / same / same / - / - | no published forecast at this lead |
| NDVI | 12 | 0.0396 | same / same / same / - / - | no published forecast at this lead |

Common verdicts: = 3, ? 21, WIN 9, loss 9, same 11
Human deciding verdicts: ? 2, WIN 9, same 1
Joint claim (pre-registered): defo lead 0 and lead 1 - ours beats VT0007 (every form): YES.
