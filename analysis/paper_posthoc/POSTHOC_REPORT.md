# Paper post-hoc facts: A/B reconciliation (POST HOC, report-only)

2026-10-26. Rulings AK3 / AK4(a) (engine/OWNER_RULINGS_2026-10-06.md). **Every number here is POST HOC**: it was computed after the test labels were opened. **None of it changes a pre-registered verdict.** Light compute only (pandas/pyarrow on saved predictions and frozen engine CSVs; no refit, no re-routing). No seeds; every interval is a jackknife over regions (groups), z = 1.96 unless stated.

## Scripts and outputs

| file | sha256 | role |
|---|---|---|
| D:/treeroute/analysis/paper_posthoc/posthoc_A.py | 0cee249c0834dc2bbf0fe9ec458b200e20e096a4c5fc24e8d585a09584bab7c0 | implementer A (unchanged; no fix needed) |
| D:/treeroute/analysis/paper_posthoc/posthoc_B.py | 6b781c848bd84391da3bb71975135ebdcd806150ec45911d18e2c3f3f0db58ff | implementer B (unchanged; no fix needed) |
| D:/treeroute/analysis/paper_posthoc/result_A.json | 7550f667311cc728b8b500cfbc47f7cccd2e3f800cb0a53cabc9841f883055f3 | A output (1,327 checks, 0 failed) |
| D:/treeroute/analysis/paper_posthoc/result_B.json | 1e616b11700b4d066a9466ee5fbff38e9ec7615157b2c02a580714297fbf0eb0 | B output (1,738 checks, 0 failed) |
| D:/treeroute/analysis/paper_posthoc/reconcile_AB.py | 5dcbe687b730c77f6207236bfa674d9a7a473b402e89a6c74b3487c7273b4c58 | leaf-by-leaf A vs B comparison, fact-sheet comparison, input re-hash, spot checks C |
| D:/treeroute/analysis/paper_posthoc/reconcile_AB.json | e86c98c0d48f67e1aa29b9c1996e599111ecb6e29034b6d00bd7e84ec5824372 | reconciliation output |
| D:/treeroute/analysis/paper_posthoc/make_report.py | 5ba4491726fed6178acd33ed73719ca6beccbfe3dbfc4730477f91197c69cdb6 | writes this report from the JSON files |
| D:/treeroute/analysis/paper_posthoc/SPEC.json | 13fc0aaad163db0d3d3d659f381fb6ca84ef668a08b946be43d692972b7de032 | the spec both implementers worked from |

Run: `py -3.9 -I <script>` for each (A about 10 s, B similar, reconcile about 2 s, report <1 s).

## How A and B were compared

A and B were written independently from SPEC.json (neither read the other). reconcile_AB.py maps both result files to the same canonical keys (for example run / column / metric, or problem / lead / rival for P29) and compares every leaf both report. A float agrees when it is equal to within 1e-12 relative at full precision, or, where one side printed fewer digits (B's P29 rows are rounded to 10 significant digits), within half a unit in the last printed digit. Strings, tags, booleans and integers must be equal. A self-test confirms the comparator flags a 1e-10 relative change, a one-digit print error, a flipped tag, an integer change and a missing value. All 82 input files were re-hashed now; every sha256 prefix matches SPEC.json, A and B (0 mismatches); every spec input was read by A or B.

**Result: A and B agree on all 10 items.** 3,917 leaves were compared: 550 integers equal, 1,657 floats bit-identical, 646 P29 floats equal at B's printed precision, 0 disagreements. A ran 1,327 internal checks and B 1,738, all passed. So no script was changed.

## Summary

| item | A vs B | leaves compared | fact sheet | note |
|---|---|---|---|---|
| M34 | AGREE | 80 | 29 checked: DIFFERS (1) | Fire added. 'Within 1e-8 relative' is FALSE for fire (2.09e-8); everything else matches. |
| R12 | AGREE | 90 | 28 checked: MATCHES | Ordering and final part confirmed. Two new report-only contrasts (not in the fact sheet yet). |
| R13 | AGREE | 288 | 31 checked: MATCHES | Confirmed. 21 placebo pairs re-derived exactly. |
| R14 | AGREE | 29 | 14 checked: MATCHES | Confirmed. M47 later-lead pinning not re-checked (adoption_lead_*.json not in the inputs). |
| R15 | AGREE | 1267 | 53 checked: MATCHES; wording (1) | Confirmed. Wording: defo 'adopted = log plain' is not literal equality (6.1e-7 apart). |
| P29 | AGREE | 1248 | 34 checked: MATCHES | Confirmed: exactly 2 of 79 tags change under t. 'About 80' should read 79. |
| R3b | AGREE | 59 | 28 checked: MATCHES | Confirmed: fire +2.42% vs log trees-off, +2.36% vs predict-zero (worse). |
| RC12 | AGREE | 481 | 24 checked: DIFFERS (1) | 'L1 wins on every bleached stratum' is FALSE: ours is lower in B1-B3; L1 lower only in B4 and y >= 50. |
| A1 | AGREE | 305 | 33 checked: MATCHES; wording (1) | Confirmed. Spec wording: Ridge's guarded column is the identity trees-off, not guess-normal exactly. |
| A2 | AGREE | 70 | 39 checked: MATCHES | Confirmed: ours mid-pack; all five contrasts CANNOT TELL. |

**ATTENTION (fact-sheet edits needed):**

1. **M34:** 'equal within 1e-8 relative' is false for fire (relative difference 2.09e-08). True alternatives: 'equal within 2.1e-8 relative' (largest of the four, fire), or 'equal to 6 significant digits' (true in all four). Add fire: 0.00625876 vs 0.00625876.
2. **RC12:** 'L1 wins on every bleached stratum' is not reproduced. Ours has the lower MAE in B1 (2.248 vs 2.489), B2 (4.571 vs 5.769) and B3 (8.396 vs 9.469). hgb_l1 is lower only in B4 > q75 (41.052 vs 31.151) and in y >= 50 (53.125 vs 38.660); only those two per-region contrasts are HURTS.
3. **P29:** 'about 80 verdicts' should read 79 (14 own + 53 common + 12 human).
4. **R15 wording:** defo 'adopted 0.0054158 = log plain 0.0054164' should use '<' or 'vs'; the numbers match.
5. **A1 spec wording:** Ridge's guarded column is arm__identity_trees_off_unweighted (the R16 decline target), not base__guess_normal exactly (they differ by up to 8.09e-07).

**Could not be computed (out of the spec's inputs):** M47 (the same point pinned at later leads; needs adoption_lead_*.json); the engine-v2 alarm numbers of A2 (engine v2 replay). The RC12 probe cut (0,10] (ours 3.71 vs L1 4.41) is outside the spec formula; a single implementation (C, in reconcile_AB.py) reproduces it but it is not A/B-reconciled.

**Independent spot checks C** (reconcile_AB.py, third implementation, light): M34 MAE_TO, MAE_GN, relative difference, maxdev, GN == clip and row counts for all four runs; the two P29 rows that change (t quantile, t CI, z lower bound, p_z, p_t); fire R3b change %. 42 of 42 values equal A (and so B) exactly.

## M34

**What.** Climatology identity on the saved test rows: for every run with an identity link, the pooled test MAE of the identity-link trees-off arm against the guess-normal baseline, their exact difference, the largest per-row difference, and the trees-off anomaly R2.

**Population.** Lead 0 (nowcast), labelled rows: pm25 91,428 rows / 1,905 units / 127 groups / 2020-2023; ndvi 94,527 / 1,983 / 133 / 2020-2023; fire 94,702 / 2,000 / 40 / 2019-2022; defo 369,096 / 92,274 / 42 / 2020-2023. The per-row maximum is over every saved row (pm25 91,440, ndvi 95,184, fire 96,000, defo 369,096). Coral is excluded (neighbour kind: no normal, no guess-normal).

**Formula in words.** For each run with an identity link: mean absolute error of the identity trees-off column and of the guess-normal baseline over the labelled rows, their exact difference and relative difference, the largest absolute row difference between the two columns over every saved row, and the anomaly R2 of trees-off (1 minus squared error of the anomaly over squared anomaly, anomalies taken from the saved normal).

<details><summary>Spec formula (verbatim)</summary>

TO = arm__identity_trees_off_unweighted, GN = base__guess_normal. MAE_TO = mean|y - TO| and MAE_GN = mean|y - GN| over labelled rows; diff = MAE_TO - MAE_GN; rel = diff / MAE_GN; maxdev = max over all saved rows of |TO - GN|; assert GN == clip(normal, legal_min, legal_max) exactly; anomaly R2 of TO = 1 - sum((y-normal)-(TO-normal))^2 / sum((y-normal)^2). Compare maxdev with the run's identity tolerance verdict.json tolerances.tolerance.identity (pm25 1e-06, ndvi/fire/defo 9e-07; ruling O4: max(k*s, 9e-07), k = 5.230771281733543e-08). Check MAE_TO, MAE_GN and anomaly R2 against score_pooled.csv (rtol 1e-12). Print MAEs to 6 significant digits AND the exact diff.

</details>

**Engine definitions cited.** C:/Users/moh the ghost/Desktop/data set for reserch paper/engine/treeroute/report/metrics.py: mae() line 569, anomaly_r2() 580, baseline_guess_normal() 348, score_table() 846; route/kinds.py _trees_off_checked() 605-625 (R16: trees-off must stay within the R36 tolerance of the normal on every score row, link space); pipeline/passes.py report() 1049-1065 writes score_pooled.csv; verdict.json 'tolerances' (ruling O4); APP_PLAN.md R16, R36.

**A/B agreement: AGREE.** 80 leaves compared (20 integers, 36 floats bit-identical, 0 at printed precision), 0 disagreements. A checks 49 (failed 0); B checks 36 (failed 0). Leaves only one side reports: A 28, B 16 (extra detail, not disagreements).

### Agreed values

| run | labelled rows / units / groups / years | saved rows (maxdev) | MAE_TO (6 sig) | MAE_GN (6 sig) | exact diff TO-GN | rel diff | maxdev /TO-GN/ | identity tol | maxdev / tol | TO anomaly R2 | GN == clip(normal) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pm25 | 91,428 / 1,905 / 127 / 2020-2023 | 91,440 | 4.03161 | 4.03161 | -2.1786838999560132e-10 | -5.4e-11 | 4.125e-09 | 1e-06 | 0.004 | 5.16e-11 | True |
| ndvi | 94,527 / 1,983 / 133 / 2020-2023 | 95,184 | 0.0394141 | 0.0394141 | -2.4472252696527974e-10 | -6.21e-09 | 1.76e-07 | 9e-07 | 0.196 | 1.45e-09 | True |
| fire | 94,702 / 2,000 / 40 / 2019-2022 | 96,000 | 0.00625876 | 0.00625876 | 1.3085031756038257e-10 | 2.09e-08 | 8.091e-07 | 9e-07 | 0.899 | 5.52e-09 | True |
| defo | 369,096 / 92,274 / 42 / 2020-2023 | 369,096 | 0.00840486 | 0.00840486 | 3.3778708996567985e-13 | 4.02e-11 | 4.759e-09 | 9e-07 | 0.005 | 2.02e-10 | True |

Full precision: pm25 TO 4.031610558456933 vs GN 4.031610558674801; ndvi TO 0.039414114188559106 vs GN 0.03941411443328163; fire TO 0.006258758011328549 vs GN 0.006258757880478231; defo TO 0.008404857347564031 vs GN 0.008404857347226244. The GN anomaly R2 is exactly 0 in all four. The clip changes 0 rows in all four.

### Fact-sheet comparison

| check | fact sheet / probe states | agreed value | status |
|---|---|---|---|
| pm25 MAE_TO (6 sig) | 4.03161 | 4.031610558456933 | MATCHES |
| pm25 MAE_GN (6 sig) | 4.03161 | 4.031610558674801 | MATCHES |
| ndvi MAE_TO (6 sig) | 0.0394141 | 0.039414114188559106 | MATCHES |
| ndvi MAE_GN (6 sig) | 0.0394141 | 0.03941411443328163 | MATCHES |
| defo MAE_TO (6 sig) | 0.00840486 | 0.008404857347564031 | MATCHES |
| defo MAE_GN (6 sig) | 0.00840486 | 0.008404857347226244 | MATCHES |
| ndvi TO anomaly R2 | 1.45e-09 | 1.4520969982001475e-09 | MATCHES |
| pm25 MAE_TO (frozen score_pooled) | 4.031610558456933 | 4.031610558456933 | MATCHES |
| pm25 MAE_GN (frozen score_pooled) | 4.031610558674801 | 4.031610558674801 | MATCHES |
| ndvi MAE_TO (frozen score_pooled) | 0.039414114188559106 | 0.039414114188559106 | MATCHES |
| ndvi MAE_GN (frozen score_pooled) | 0.03941411443328163 | 0.03941411443328163 | MATCHES |
| fire MAE_TO (frozen score_pooled) | 0.006258758011328549 | 0.006258758011328549 | MATCHES |
| fire MAE_GN (frozen score_pooled) | 0.006258757880478231 | 0.006258757880478231 | MATCHES |
| defo MAE_TO (frozen score_pooled) | 0.008404857347564031 | 0.008404857347564031 | MATCHES |
| defo MAE_GN (frozen score_pooled) | 0.008404857347226244 | 0.008404857347226244 | MATCHES |
| pm25 TO anomaly R2 | 5.16e-11 | 5.1608384232793014e-11 | MATCHES |
| ndvi TO anomaly R2 | 1.45e-09 | 1.4520969982001475e-09 | MATCHES |
| fire TO anomaly R2 | 5.52e-09 | 5.519035450873844e-09 | MATCHES |
| defo TO anomaly R2 | 2.02e-10 | 2.0187096438917251e-10 | MATCHES |
| pm25 maxdev (probe) | 4.1e-09 | 4.124643737668521e-09 | MATCHES |
| ndvi maxdev (probe) | 1.76e-07 | 1.7599613409691184e-07 | MATCHES |
| fire maxdev (probe) | 8.09e-07 | 8.090730176402725e-07 | MATCHES |
| defo maxdev (probe) | 4.76e-09 | 4.759310535951133e-09 | MATCHES |
| GN == clip(normal) exactly in all four | true | true in all four | MATCHES |
| fire MAE_TO (added, 6 sig) | 0.00625876 | 0.006258758011328549 | MATCHES |
| fire MAE_GN (added, 6 sig) | 0.00625876 | 0.006258757880478231 | MATCHES |
| 'equal to every printed digit' (6 sig) in all four | true | {"pm25": ["4.03161", "4.03161"], "ndvi": ["0.0394141", "0.0394141"], "fire": ["0.00625876", "0.00625876"], "defo": ["0.00840486", "0.00840486"]} | MATCHES |
| proposed wording 'equal within 1e-8 relative' (all four runs) | max /rel/ <= 1e-8 | max /rel/ = 2.091e-08 (fire); pm25 -5.4e-11, ndvi -6.21e-09, defo 4.02e-11 | DIFFERS |
| maxdev within the run's identity tolerance (R16/R36) | true | {"pm25": 0.004124643737668521, "ndvi": 0.19555126010767984, "fire": 0.8989700196003028, "defo": 0.005288122817723482} | MATCHES |

### Inputs

| file | sha256 prefix (re-hashed now) | in spec list | read by | matches spec/A/B prefixes |
|---|---|---|---|---|
| D:/treeroute/runs/_headline_tables/ndvi/headline_9e5590eab94b.csv | 9e5590eab94b7373 | yes | AB | yes |
| D:/treeroute/runs/defo/headline/20261017_d71c61f4/score_pooled.csv | 8f1c161ad318e32c | yes | AB | yes |
| D:/treeroute/runs/defo/headline/20261017_d71c61f4/test_preds.parquet | 3a002e9a9deb006a | yes | AB | yes |
| D:/treeroute/runs/defo/headline/20261017_d71c61f4/verdict.json | 34d090aae96fed3c | yes | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/score_pooled.csv | 9236a25380d9aede | yes | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/test_preds.parquet | 86e9c97a58a9b714 | yes | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/verdict.json | 6c744bc1a0647e37 | yes | AB | yes |
| D:/treeroute/runs/ndvi/headline/20261016_d1de3158/score_pooled.csv | 3a7e09b6156e4449 | yes | AB | yes |
| D:/treeroute/runs/ndvi/headline/20261016_d1de3158/test_preds.parquet | 87c0b1414af7e370 | yes | AB | yes |
| D:/treeroute/runs/ndvi/headline/20261016_d1de3158/verdict.json | 535ef992b5057ed7 | yes | AB | yes |
| D:/treeroute/runs/pm25/headline/20261007_74e67609/score_pooled.csv | 8a7d2f44f00a9e7c | yes | AB | yes |
| D:/treeroute/runs/pm25/headline/20261007_74e67609/test_preds.parquet | 9e62fe4256c08c50 | yes | AB | yes |
| D:/treeroute/runs/pm25/headline/20261007_74e67609/verdict.json | af031ef5a44dbe67 | yes | AB | yes |

Scripts: posthoc_A.py sha256 0cee249c0834dc2bbf0fe9ec458b200e20e096a4c5fc24e8d585a09584bab7c0; posthoc_B.py sha256 6b781c848bd84391da3bb71975135ebdcd806150ec45911d18e2c3f3f0db58ff; reconcile_AB.py sha256 5dcbe687b730c77f6207236bfa674d9a7a473b402e89a6c74b3487c7273b4c58.

## R12

**What.** The pooled-MAE part of R12: on fire at the nowcast, the ordering of the geometric normal (log trees-off), predict-zero, the four log tree arms, the adopted arcsine corrector GLS, the arcsine trees-off and the identity normal (decline target). Beside it (new, report-only): the per-region paired contrast of the adopted arm against the log trees-off and against predict-zero.

**Population.** Fire, lead 0, labelled rows: 94,702 cell-months (1,298 unlabelled saved rows excluded), 2,000 units, 40 groups, test years 2019-2022. Contrasts over the 40 groups.

**Formula in words.** Fire nowcast: pooled MAE of each listed column over the labelled rows, sorted. New: for each region, MAE of the reference column minus MAE of the adopted column (positive = adopted better), averaged over the 40 regions, with a leave-one-region-out jackknife interval (mean +- 1.96 SE) and the run's band tag.

<details><summary>Spec formula (verbatim)</summary>

Pooled MAE of each listed column over the labelled rows, sorted ascending (check vs score_pooled.csv, rtol 1e-12). Report-only contrasts: d_g = MAE_ref(g) - MAE_adopted(g) with ref = arm__log_c_trees_off_unweighted and, separately, ref = base__predict_zero (positive = adopted better); per-group MAE recomputed and checked against score_by_group.csv; group jackknife (1.96); tag with the fire band 1.356697052e-05. The final part of R12 (adoption.json surface MAEs, jackknife.csv band-pair tags of the log arms) is re-read, not recomputed, and the jackknife.csv log-arm rows are re-derived from score_by_group.csv as a check.

</details>

**Engine definitions cited.** C:/Users/moh the ghost/Desktop/data set for reserch paper/engine/treeroute/report/metrics.py score_table() 846, metric_by_key() 999, _paired_contrast() 1123, group_jackknife() 1032, contrast_tag() 1097; pipeline/passes.py report() 1080-1131 (D75 pairs, single verdict, jackknife.csv); layer/decide.py (guard and adoption; M43-M45).

**A/B agreement: AGREE.** 90 leaves compared (4 integers, 52 floats bit-identical, 0 at printed precision), 0 disagreements. A checks 26 (failed 0); B checks 57 (failed 0). Leaves only one side reports: A 0, B 0 (extra detail, not disagreements).

### Agreed values

| rank | column | pooled MAE |
|---|---|---|
| 1 | arm__log_c_trees_off_unweighted | 0.00428130231282 |
| 2 | base__predict_zero | 0.00428411461924 |
| 3 | arm__log_c_corrector_gls | 0.00429579487266 |
| 4 | arm__log_c_plain_gls | 0.00429698772216 |
| 5 | arm__log_c_corrector_unweighted | 0.0043208574035 |
| 6 | arm__log_c_plain_unweighted | 0.00432242534754 |
| 7 | arm__arcsine_corrector_gls (ADOPTED) | 0.0043850645583 |
| 8 | arm__arcsine_trees_off_unweighted | 0.00442826356639 |
| 9 | base__guess_normal | 0.00625875788048 |
| 10 | arm__identity_trees_off_unweighted | 0.00625875801133 |

NEW report-only contrasts (d_g = MAE_ref(g) - MAE_adopted(g); positive = adopted better; band 1.356697052e-05):

| reference | mean d | SE | 95% CI (z) | tag | regions adopted better | pooled difference |
|---|---|---|---|---|---|---|
| arm__log_c_trees_off_unweighted | -0.000103 | 6.533e-05 | [-0.000231, +2.51e-05] | CANNOT TELL | 25/40 | -0.0001038 |
| base__predict_zero | -0.0001035 | 0.0002637 | [-0.0006205, +0.0004134] | CANNOT TELL | 3/40 | -0.0001009 |

Final part re-read from adoption.json (inner decision surface, 68,901 rows, 2,000 units; adopted point level=100.0,ratio=1.0). 'Surface pick' = the arm's own best grid point (A and B agree); 'at adopted point' = A only, direct re-read. Surface predict-zero 0.004286724.

| arm | surface pick MAE | pick point | MAE at adopted point (A only) | eligible |
|---|---|---|---|---|
| log_c_plain_unweighted | 0.004238097 | level=100.0,ratio=0.125 | 0.0042381 | False |
| log_c_plain_gls | 0.004213206 | level=100.0,ratio=0.0625 | 0.004213236 | False |
| log_c_corrector_unweighted | 0.004234358 | level=100.0,ratio=1.0 | 0.004234358 | False |
| log_c_corrector_gls | 0.004210239 | level=100.0,ratio=0.125 | 0.004210243 | False |
| arcsine_plain_gls | 0.004330022 | level=100.0,ratio=1.0 | 0.004330022 | True |
| arcsine_corrector_gls | 0.004327788 | level=100.0,ratio=1.0 | 0.004327788 | True |
| log_c_trees_off_unweighted | 0.004186195 | (no grid) |  | False |
| arcsine_trees_off_unweighted | 0.004367773 | (no grid) |  | False |

jackknife.csv log-arm rows re-derived from score_by_group.csv (equal to the file, rtol 1e-12); d_g = MAE_reference(g) - MAE_arm(g), positive = arm better:

| reference | arm | mean | 95% CI | tag (file) | tag (re-derived) |
|---|---|---|---|---|---|
| arm__log_c_trees_off_unweighted | arm__log_c_plain_unweighted | -4.188e-05 | [-6.877e-05, -1.499e-05] | HURTS | HURTS |
| arm__log_c_trees_off_unweighted | arm__log_c_corrector_unweighted | -4.03e-05 | [-6.66e-05, -1.401e-05] | HURTS | HURTS |
| placebo__log_c_placebo_corrector_unweighted | arm__log_c_corrector_unweighted | -4.53e-07 | [-3.299e-06, +2.393e-06] | EQUIVALENT | EQUIVALENT |
| arm__log_c_trees_off_unweighted | arm__log_c_plain_gls | -1.644e-05 | [-4.065e-05, +7.772e-06] | CANNOT TELL | CANNOT TELL |
| arm__log_c_trees_off_unweighted | arm__log_c_corrector_gls | -1.523e-05 | [-3.84e-05, +7.936e-06] | CANNOT TELL | CANNOT TELL |
| placebo__log_c_placebo_corrector_gls | arm__log_c_corrector_gls | -1.731e-06 | [-3.76e-06, +2.993e-07] | EQUIVALENT | EQUIVALENT |

### Fact-sheet comparison

| check | fact sheet / probe states | agreed value | status |
|---|---|---|---|
| arm__log_c_trees_off_unweighted | 0.004281 | 0.004281302312816825 | MATCHES |
| base__predict_zero | 0.004284 | 0.004284114619241937 | MATCHES |
| arm__arcsine_corrector_gls | 0.004385 | 0.004385064558301006 | MATCHES |
| arm__arcsine_trees_off_unweighted | 0.004428 | 0.00442826356638935 | MATCHES |
| arm__identity_trees_off_unweighted | 0.006259 | 0.006258758011328549 | MATCHES |
| log tree arms min | 0.004296 | 0.0042957948726572255 | MATCHES |
| log tree arms max | 0.004322 | 0.004322425347543649 | MATCHES |
| ordering logTO < PZ < log arms < adopted < arcsine TO < identity normal | as stated | ["arm__log_c_trees_off_unweighted", "base__predict_zero", "arm__log_c_corrector_gls", "arm__log_c_plain_gls", "arm__log_c_corrector_unweighted", "arm__log_c_... | MATCHES |
| arm__log_c_trees_off_unweighted (frozen score_pooled) | 0.004281302312816825 | 0.004281302312816825 | MATCHES |
| base__predict_zero (frozen score_pooled) | 0.004284114619241937 | 0.004284114619241937 | MATCHES |
| arm__log_c_corrector_gls (frozen score_pooled) | 0.0042957948726572255 | 0.0042957948726572255 | MATCHES |
| arm__log_c_plain_gls (frozen score_pooled) | 0.004296987722157366 | 0.004296987722157366 | MATCHES |
| arm__log_c_corrector_unweighted (frozen score_pooled) | 0.004320857403502066 | 0.004320857403502066 | MATCHES |
| arm__log_c_plain_unweighted (frozen score_pooled) | 0.004322425347543649 | 0.004322425347543649 | MATCHES |
| arm__arcsine_corrector_gls (frozen score_pooled) | 0.004385064558301006 | 0.004385064558301006 | MATCHES |
| arm__arcsine_trees_off_unweighted (frozen score_pooled) | 0.00442826356638935 | 0.00442826356638935 | MATCHES |
| arm__identity_trees_off_unweighted (frozen score_pooled) | 0.006258758011328549 | 0.006258758011328549 | MATCHES |
| base__guess_normal (frozen score_pooled) | 0.006258757880478231 | 0.006258757880478231 | MATCHES |
| jk log plain unw mean | -4.19e-05 | -4.187873633792463e-05 | MATCHES |
| jk log plain unw low | -6.88e-05 | -6.876883843503599e-05 | MATCHES |
| jk log plain unw high | -1.50e-05 | -1.4988634240813266e-05 | MATCHES |
| jk log plain unw tag | hurts | hurts | MATCHES |
| jk log corrector unw mean | -4.03e-05 | -4.030492240020977e-05 | MATCHES |
| jk log corrector unw low | -6.66e-05 | -6.659734476063998e-05 | MATCHES |
| jk log corrector unw high | -1.40e-05 | -1.4012500039779556e-05 | MATCHES |
| jk log corrector unw tag | hurts | hurts | MATCHES |
| jk log GLS arms tag | cannot_tell | ["cannot_tell", "cannot_tell"] | MATCHES |
| new report-only contrasts (adopted vs log TO, vs PZ) | not in fact sheet yet | {"arm__log_c_trees_off_unweighted": [-0.00010295521202507616, -0.00023100933896972204, 2.509891491956972e-05, "cannot_tell"], "base__predict_zero": [-0.00010... | MATCHES |

### Inputs

| file | sha256 prefix (re-hashed now) | in spec list | read by | matches spec/A/B prefixes |
|---|---|---|---|---|
| D:/treeroute/runs/fire/headline/20261017_869d1f38/adoption.json | 75f70e5cd22039b6 | yes | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/jackknife.csv | b8557782d9cdd703 | yes | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/score_by_group.csv | 03585591911c6e01 | yes | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/score_pooled.csv | 9236a25380d9aede | yes | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/test_preds.parquet | 86e9c97a58a9b714 | yes | A | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/verdict.json | 6c744bc1a0647e37 | yes | AB | yes |

Scripts: posthoc_A.py sha256 0cee249c0834dc2bbf0fe9ec458b200e20e096a4c5fc24e8d585a09584bab7c0; posthoc_B.py sha256 6b781c848bd84391da3bb71975135ebdcd806150ec45911d18e2c3f3f0db58ff; reconcile_AB.py sha256 5dcbe687b730c77f6207236bfa674d9a7a473b402e89a6c74b3487c7273b4c58.

## R13

**What.** The pooled-MAE table of R13: for the adopted link and weighting of each run, the pooled test MAE of the corrector arm, its placebo and the plain arm; beside it every other link x weighting triple. Also re-derive the final placebo band-pair contrasts and tags of jackknife.csv from score_by_group.csv.

**Population.** Lead 0 labelled rows of each run (pm25 91,428 / 127 groups; ndvi 94,527 / 133; fire 94,702 / 40; defo 369,096 / 42; coral 2,312 / 37). Triples used: pm25 log_c / unweighted (adopted corrector); ndvi identity / unweighted (adopted arm is plain); fire arcsine / gls (adopted); defo log_c / unweighted (adopted); coral arcsine / gls (adopted).

**Formula in words.** For each link x weighting: pooled MAE of the corrector arm, its placebo and the plain arm, and the two differences. Each placebo pair of jackknife.csv re-derived from the per-region MAEs (placebo minus corrector, region jackknife, band tag).

<details><summary>Spec formula (verbatim)</summary>

Pooled MAE per column over labelled rows (check vs score_pooled.csv). For every placebo__ row of jackknife.csv (kind band_pair): d_g = MAE_placebo(g) - MAE_corrector(g) from score_by_group.csv, group jackknife (1.96), tag with the run's band; assert mean, se, low, high and tag equal jackknife.csv (rtol 1e-12). Report corrector - placebo and corrector - plain pooled differences.

</details>

**Engine definitions cited.** C:/Users/moh the ghost/Desktop/data set for reserch paper/engine/treeroute/pipeline/passes.py report() 1087-1101 (D75 pairs: each tree arm vs its trees-off, each corrector vs its placebo) and pipeline/table_passes.py 574-642 (coral, table option); report/metrics.py band_from_pairs() 1195, group_jackknife() 1032, contrast_tag() 1097; layer/arms.py (placebo never selectable, R24).

**A/B agreement: AGREE.** 288 leaves compared (31 integers, 194 floats bit-identical, 0 at printed precision), 0 disagreements. A checks 146 (failed 0); B checks 257 (failed 0). Leaves only one side reports: A 0, B 0 (extra detail, not disagreements).

### Agreed values

| run | link / weighting | adopted | corrector | placebo | plain | corrector - placebo | corrector - plain |
|---|---|---|---|---|---|---|---|
| pm25 | log_c / unweighted | yes | 3.588091134 | 3.591572881 | 3.596454184 | -0.003482 | -0.008363 |
| pm25 | identity / gls |  | 3.724001589 | 3.724106525 | 3.728449678 | -0.0001049 | -0.004448 |
| pm25 | identity / unweighted |  | 3.774844393 | 3.774760312 | 3.777737418 | +8.408e-05 | -0.002893 |
| pm25 | log_c / gls |  | 3.587480407 | 3.592004339 | 3.597253889 | -0.004524 | -0.009773 |
| ndvi | identity / unweighted | yes | 0.03149747357 | 0.03165363992 | 0.03146059686 | -0.0001562 | +3.688e-05 |
| ndvi | identity / gls |  | 0.03150740801 | 0.03166964675 | 0.03148296727 | -0.0001622 | +2.444e-05 |
| fire | arcsine / gls | yes | 0.004385064558 | 0.004383043171 | 0.00438567029 | +2.021e-06 | -6.057e-07 |
| fire | arcsine / unweighted |  | 0.004433140383 | 0.004433615607 | 0.004436316713 | -4.752e-07 | -3.176e-06 |
| fire | identity / gls |  | 0.006477791881 | 0.006458038247 | 0.006482438031 | +1.975e-05 | -4.646e-06 |
| fire | identity / unweighted |  | 0.006684976167 | 0.00666742366 | 0.006689094218 | +1.755e-05 | -4.118e-06 |
| fire | log_c / gls |  | 0.004295794873 | 0.004294105489 | 0.004296987722 | +1.689e-06 | -1.193e-06 |
| fire | log_c / unweighted |  | 0.004320857404 | 0.004320448579 | 0.004322425348 | +4.088e-07 | -1.568e-06 |
| defo | log_c / unweighted | yes | 0.005415798422 | 0.005419502142 | 0.005416406367 | -3.704e-06 | -6.079e-07 |
| defo | arcsine / unweighted |  | 0.00573436398 | 0.005726804843 | 0.005726304748 | +7.559e-06 | +8.059e-06 |
| defo | identity / unweighted |  | 0.007973050139 | 0.007894508542 | 0.007910046311 | +7.854e-05 | +6.3e-05 |
| coral | arcsine / gls | yes | 6.697989245 | 6.731545728 | 6.735936796 | -0.03356 | -0.03795 |
| coral | arcsine / unweighted |  | 6.147485763 | 6.16526055 | 6.159354031 | -0.01777 | -0.01187 |
| coral | identity / gls |  | 7.40994183 | 7.437607615 | 7.440503695 | -0.02767 | -0.03056 |
| coral | identity / unweighted |  | 7.11041778 | 7.121152203 | 7.117837856 | -0.01073 | -0.00742 |
| coral | log_c / gls |  | 7.007205326 | 7.037013485 | 7.033586763 | -0.02981 | -0.02638 |
| coral | log_c / unweighted |  | 6.359479297 | 6.378480894 | 6.375598571 | -0.019 | -0.01612 |

All 21 placebo band pairs of jackknife.csv (d_g = MAE_placebo(g) - MAE_corrector(g)), re-derived from score_by_group.csv; mean, SE, CI, regions and tag equal the file (rtol 1e-12):

| run | corrector arm | mean | SE | 95% CI | regions | tag (file) | tag (re-derived) |
|---|---|---|---|---|---|---|---|
| pm25 | identity_corrector_unweighted | -8.357e-05 | 0.0037 | [-0.007345, +0.007178] | 127 | EQUIVALENT | EQUIVALENT |
| pm25 | identity_corrector_gls | +0.0001054 | 0.00356 | [-0.006875, +0.007086] | 127 | EQUIVALENT | EQUIVALENT |
| pm25 | log_c_corrector_unweighted | +0.003483 | 0.00313 | [-0.002646, +0.009612] | 127 | EQUIVALENT | EQUIVALENT |
| pm25 | log_c_corrector_gls | +0.004525 | 0.00345 | [-0.002238, +0.01129] | 127 | EQUIVALENT | EQUIVALENT |
| ndvi | identity_corrector_unweighted | +0.0001551 | 2.3e-05 | [+0.00011, +0.0002002] | 133 | EQUIVALENT | EQUIVALENT |
| ndvi | identity_corrector_gls | +0.0001615 | 2.27e-05 | [+0.0001169, +0.0002061] | 133 | EQUIVALENT | EQUIVALENT |
| fire | identity_corrector_unweighted | -1.792e-05 | 7.92e-06 | [-3.345e-05, -2.395e-06] | 40 | HURTS | HURTS |
| fire | identity_corrector_gls | -2.011e-05 | 7.36e-06 | [-3.454e-05, -5.682e-06] | 40 | HURTS | HURTS |
| fire | log_c_corrector_unweighted | -4.53e-07 | 1.45e-06 | [-3.299e-06, +2.393e-06] | 40 | EQUIVALENT | EQUIVALENT |
| fire | log_c_corrector_gls | -1.731e-06 | 1.04e-06 | [-3.76e-06, +2.993e-07] | 40 | EQUIVALENT | EQUIVALENT |
| fire | arcsine_corrector_unweighted | +3.847e-07 | 1.74e-06 | [-3.03e-06, +3.799e-06] | 40 | EQUIVALENT | EQUIVALENT |
| fire | arcsine_corrector_gls | -2.097e-06 | 1.36e-06 | [-4.765e-06, +5.714e-07] | 40 | EQUIVALENT | EQUIVALENT |
| defo | identity_corrector_unweighted | -7.854e-05 | 5.53e-05 | [-0.0001869, +2.979e-05] | 42 | CANNOT TELL | CANNOT TELL |
| defo | log_c_corrector_unweighted | +3.704e-06 | 2.55e-06 | [-1.296e-06, +8.704e-06] | 42 | EQUIVALENT | EQUIVALENT |
| defo | arcsine_corrector_unweighted | -7.559e-06 | 1.02e-05 | [-2.758e-05, +1.246e-05] | 42 | EQUIVALENT | EQUIVALENT |
| coral | identity_corrector_unweighted | -0.02433 | 0.0524 | [-0.127, +0.07832] | 37 | EQUIVALENT | EQUIVALENT |
| coral | identity_corrector_gls | +0.03907 | 0.0465 | [-0.05214, +0.1303] | 37 | EQUIVALENT | EQUIVALENT |
| coral | log_c_corrector_unweighted | -0.003582 | 0.0982 | [-0.1961, +0.1889] | 37 | EQUIVALENT | EQUIVALENT |
| coral | log_c_corrector_gls | +0.08506 | 0.0543 | [-0.02136, +0.1915] | 37 | EQUIVALENT | EQUIVALENT |
| coral | arcsine_corrector_unweighted | -8.676e-06 | 0.0557 | [-0.1092, +0.1092] | 37 | EQUIVALENT | EQUIVALENT |
| coral | arcsine_corrector_gls | +0.08057 | 0.0486 | [-0.01473, +0.1759] | 37 | EQUIVALENT | EQUIVALENT |

### Fact-sheet comparison

| check | fact sheet / probe states | agreed value | status |
|---|---|---|---|
| fire arcsine/gls corrector (provisional) | 0.004385 | 0.004385064558301006 | MATCHES |
| fire arcsine/gls corrector (frozen, 10 sig) | 0.004385064558 | 0.004385064558301006 | MATCHES |
| fire arcsine/gls placebo (provisional) | 0.004383 | 0.00438304317129671 | MATCHES |
| fire arcsine/gls placebo (frozen, 10 sig) | 0.004383043171 | 0.00438304317129671 | MATCHES |
| fire arcsine/gls plain (provisional) | 0.004386 | 0.004385670290261638 | MATCHES |
| fire arcsine/gls plain (frozen, 10 sig) | 0.004385670290 | 0.004385670290261638 | MATCHES |
| defo log_c/unweighted corrector (provisional) | 0.0054158 | 0.005415798421978487 | MATCHES |
| defo log_c/unweighted corrector (frozen, 10 sig) | 0.005415798422 | 0.005415798421978487 | MATCHES |
| defo log_c/unweighted placebo (provisional) | 0.0054195 | 0.005419502142027809 | MATCHES |
| defo log_c/unweighted placebo (frozen, 10 sig) | 0.005419502142 | 0.005419502142027809 | MATCHES |
| defo log_c/unweighted plain (provisional) | 0.0054164 | 0.005416406367405097 | MATCHES |
| defo log_c/unweighted plain (frozen, 10 sig) | 0.005416406367 | 0.005416406367405097 | MATCHES |
| pm25 log_c/unweighted corrector (provisional) | 3.58809 | 3.588091134093021 | MATCHES |
| pm25 log_c/unweighted corrector (frozen, 10 sig) | 3.588091134 | 3.588091134093021 | MATCHES |
| pm25 log_c/unweighted placebo (provisional) | 3.59157 | 3.5915728813934615 | MATCHES |
| pm25 log_c/unweighted placebo (frozen, 10 sig) | 3.591572881 | 3.5915728813934615 | MATCHES |
| pm25 log_c/unweighted plain (provisional) | 3.59645 | 3.596454183542564 | MATCHES |
| pm25 log_c/unweighted plain (frozen, 10 sig) | 3.596454184 | 3.596454183542564 | MATCHES |
| ndvi identity/unweighted corrector (provisional) | 0.0314975 | 0.03149747356642757 | MATCHES |
| ndvi identity/unweighted corrector (frozen, 10 sig) | 0.03149747357 | 0.03149747356642757 | MATCHES |
| ndvi identity/unweighted placebo (provisional) | 0.0316536 | 0.03165363991533624 | MATCHES |
| ndvi identity/unweighted placebo (frozen, 10 sig) | 0.03165363992 | 0.03165363991533624 | MATCHES |
| ndvi identity/unweighted plain (provisional) | 0.0314606 | 0.03146059686292064 | MATCHES |
| ndvi identity/unweighted plain (frozen, 10 sig) | 0.03146059686 | 0.03146059686292064 | MATCHES |
| coral arcsine/gls corrector (provisional) | 6.698 | 6.69798924506233 | MATCHES |
| coral arcsine/gls corrector (frozen, 10 sig) | 6.697989245 | 6.69798924506233 | MATCHES |
| coral arcsine/gls placebo (provisional) | 6.732 | 6.7315457283792615 | MATCHES |
| coral arcsine/gls placebo (frozen, 10 sig) | 6.731545728 | 6.7315457283792615 | MATCHES |
| coral arcsine/gls plain (provisional) | 6.736 | 6.735936795790105 | MATCHES |
| coral arcsine/gls plain (frozen, 10 sig) | 6.735936796 | 6.735936795790105 | MATCHES |
| every placebo pair equivalent except defo identity unw (cannot_tell), fire identity x2 (hurts) | as stated | {"n_pairs": 21, "exceptions": {"fire:arm__identity_corrector_unweighted": "hurts", "fire:arm__identity_corrector_gls": "hurts", "defo:arm__identity_corrector... | MATCHES |

### Inputs

| file | sha256 prefix (re-hashed now) | in spec list | read by | matches spec/A/B prefixes |
|---|---|---|---|---|
| D:/treeroute/runs/coral/headline/20261020_f3b8e3da/adoption.json | 2106a36efee4f9fc | no (extra) | B | yes |
| D:/treeroute/runs/coral/headline/20261020_f3b8e3da/jackknife.csv | 04178dc5d388f9f7 | yes | AB | yes |
| D:/treeroute/runs/coral/headline/20261020_f3b8e3da/score_by_group.csv | 08dd01c06c8eedc2 | yes | AB | yes |
| D:/treeroute/runs/coral/headline/20261020_f3b8e3da/score_pooled.csv | bbaa21aa184a1054 | yes | AB | yes |
| D:/treeroute/runs/coral/headline/20261020_f3b8e3da/test_preds.parquet | dd07762558023d5f | yes | AB | yes |
| D:/treeroute/runs/coral/headline/20261020_f3b8e3da/verdict.json | 6bf9b04970173323 | no (extra) | AB | yes |
| D:/treeroute/runs/defo/headline/20261017_d71c61f4/adoption.json | d8ebdd4cc458b276 | no (extra) | B | yes |
| D:/treeroute/runs/defo/headline/20261017_d71c61f4/jackknife.csv | aa7a8cd183eb5108 | yes | AB | yes |
| D:/treeroute/runs/defo/headline/20261017_d71c61f4/score_by_group.csv | d02e8f48ddef39ce | yes | AB | yes |
| D:/treeroute/runs/defo/headline/20261017_d71c61f4/score_pooled.csv | 8f1c161ad318e32c | yes | AB | yes |
| D:/treeroute/runs/defo/headline/20261017_d71c61f4/test_preds.parquet | 3a002e9a9deb006a | yes | A | yes |
| D:/treeroute/runs/defo/headline/20261017_d71c61f4/verdict.json | 34d090aae96fed3c | no (extra) | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/adoption.json | 75f70e5cd22039b6 | no (extra) | B | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/jackknife.csv | b8557782d9cdd703 | yes | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/score_by_group.csv | 03585591911c6e01 | yes | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/score_pooled.csv | 9236a25380d9aede | yes | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/test_preds.parquet | 86e9c97a58a9b714 | yes | A | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/verdict.json | 6c744bc1a0647e37 | no (extra) | AB | yes |
| D:/treeroute/runs/ndvi/headline/20261016_d1de3158/adoption.json | d5ae6f1dd6728681 | no (extra) | B | yes |
| D:/treeroute/runs/ndvi/headline/20261016_d1de3158/jackknife.csv | 533c7dd30d5b5f5b | yes | AB | yes |
| D:/treeroute/runs/ndvi/headline/20261016_d1de3158/score_by_group.csv | be1381c5568d225e | yes | AB | yes |
| D:/treeroute/runs/ndvi/headline/20261016_d1de3158/score_pooled.csv | 3a7e09b6156e4449 | yes | AB | yes |
| D:/treeroute/runs/ndvi/headline/20261016_d1de3158/test_preds.parquet | 87c0b1414af7e370 | yes | A | yes |
| D:/treeroute/runs/ndvi/headline/20261016_d1de3158/verdict.json | 535ef992b5057ed7 | no (extra) | AB | yes |
| D:/treeroute/runs/pm25/headline/20261007_74e67609/adoption.json | b6408c90560b4585 | no (extra) | B | yes |
| D:/treeroute/runs/pm25/headline/20261007_74e67609/jackknife.csv | 25624a91d0879ae2 | yes | AB | yes |
| D:/treeroute/runs/pm25/headline/20261007_74e67609/score_by_group.csv | 6fed1e7be9456655 | yes | AB | yes |
| D:/treeroute/runs/pm25/headline/20261007_74e67609/score_pooled.csv | 8a7d2f44f00a9e7c | yes | AB | yes |
| D:/treeroute/runs/pm25/headline/20261007_74e67609/test_preds.parquet | 9e62fe4256c08c50 | yes | A | yes |
| D:/treeroute/runs/pm25/headline/20261007_74e67609/verdict.json | af031ef5a44dbe67 | no (extra) | AB | yes |

Scripts: posthoc_A.py sha256 0cee249c0834dc2bbf0fe9ec458b200e20e096a4c5fc24e8d585a09584bab7c0; posthoc_B.py sha256 6b781c848bd84391da3bb71975135ebdcd806150ec45911d18e2c3f3f0db58ff; reconcile_AB.py sha256 5dcbe687b730c77f6207236bfa674d9a7a473b402e89a6c74b3487c7273b4c58.

## R14

**What.** Implied absolute penalties of each run's adopted grid point (the same point is pinned at every kept lead, M47): (a_tree, a_ctx) for the per-unit and neighbour kinds, lambda for the region kind.

**Population.** One adopted point per run at lead 0: pm25 level 30 ratio 1.0 (per_unit); ndvi level 1 ratio 0.0625 (per_unit); fire level 100 ratio 1.0 (per_unit); defo level 0.1 ratio null (region); coral level 100 ratio 1.0 (neighbour). No rows.

**Formula in words.** Absolute penalties of the adopted grid point: per-unit and neighbour kinds a_tree = trees centre x level and a_ctx = a_tree x ratio; region kind lambda = lambda centre x level.

<details><summary>Spec formula (verbatim)</summary>

Read kind and centre from derived.json R14 and (level, ratio) from adoption.json 'penalty'; assert penalty == best_tree_penalty, declined is false, and the point is in derived R14 'grid'. per_unit: a_tree = centre[0] * level; a_ctx = a_tree * ratio (0.0 when ratio is null). neighbour: the same with the neighbour centre (derived centre[0]). region: lambda = centre[0] * level. Note: the context centre (derived centre[1] = 0.25) is NOT used by point_penalties; a_ctx scales a_tree by the ratio.

</details>

**Engine definitions cited.** C:/Users/moh the ghost/Desktop/data set for reserch paper/engine/treeroute/route/kinds.py point_penalties() 365-375 (frozen ab16d168 copy D:/treeroute/install_20261015/engine_old/treeroute/route/kinds.py has the same formula); route/region.py region_lambda() 168-175; route/neighbour.py neighbour_point_penalties() 235-246; engine_constants.py C12 lines 182-190 (PER_UNIT_TREES_CENTRE 0.5, PER_UNIT_CONTEXT_CENTRE 0.25, NEIGHBOUR_TREES_CENTRE 0.5, REGION_LAMBDA_CENTRE 100); layer/decide.py penalty_search() 235.

**A/B agreement: AGREE.** 29 leaves compared (0 integers, 18 floats bit-identical, 0 at printed precision), 0 disagreements. A checks 35 (failed 0); B checks 20 (failed 0). Leaves only one side reports: A 0, B 0 (extra detail, not disagreements).

### Agreed values

| run | kind | derived centre | level | ratio | a_tree | a_ctx | lambda | grid points |
|---|---|---|---|---|---|---|---|---|
| pm25 | per_unit | [0.5, 0.25] | 30 | 1 | 15 | 15 | n/a | 35 |
| ndvi | per_unit | [0.5, 0.25] | 1 | 0.0625 | 0.5 | 0.03125 | n/a | 35 |
| fire | per_unit | [0.5, 0.25] | 100 | 1 | 50 | 50 | n/a | 35 |
| defo | region | [100.0] | 0.1 | n/a | n/a | n/a | 10 | 7 |
| coral | neighbour | [0.5, 0.25] | 100 | 1 | 50 | 50 | n/a | 35 |

Asserted for every run (A and B): penalty == best_tree_penalty, declined false, point in the derived R14 grid, centre[0] equals the C12 constant recorded in derived.json. The context centre (0.25) is not used.

### Fact-sheet comparison

| check | fact sheet / probe states | agreed value | status |
|---|---|---|---|
| pm25 a_tree | 15 | 15.0 | MATCHES |
| pm25 a_ctx | 15 | 15.0 | MATCHES |
| ndvi a_tree | 0.5 | 0.5 | MATCHES |
| ndvi a_ctx | 0.03125 | 0.03125 | MATCHES |
| fire a_tree | 50 | 50.0 | MATCHES |
| fire a_ctx | 50 | 50.0 | MATCHES |
| coral a_tree | 50 | 50.0 | MATCHES |
| coral a_ctx | 50 | 50.0 | MATCHES |
| defo lambda | 10 | 10.0 | MATCHES |
| pm25 derived centre | [0.5, 0.25] | [0.5, 0.25] | MATCHES |
| ndvi derived centre | [0.5, 0.25] | [0.5, 0.25] | MATCHES |
| fire derived centre | [0.5, 0.25] | [0.5, 0.25] | MATCHES |
| defo derived centre | [100.0] | [100.0] | MATCHES |
| coral derived centre | [0.5, 0.25] | [0.5, 0.25] | MATCHES |

### Inputs

| file | sha256 prefix (re-hashed now) | in spec list | read by | matches spec/A/B prefixes |
|---|---|---|---|---|
| D:/treeroute/runs/coral/headline/20261020_f3b8e3da/adoption.json | 2106a36efee4f9fc | yes | AB | yes |
| D:/treeroute/runs/coral/headline/20261020_f3b8e3da/derived.json | 5fd02863f8b91573 | yes | AB | yes |
| D:/treeroute/runs/defo/headline/20261017_d71c61f4/adoption.json | d8ebdd4cc458b276 | yes | AB | yes |
| D:/treeroute/runs/defo/headline/20261017_d71c61f4/derived.json | e17b92cfe8ba31cc | yes | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/adoption.json | 75f70e5cd22039b6 | yes | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/derived.json | 9255562ca6959e9e | yes | AB | yes |
| D:/treeroute/runs/ndvi/headline/20261016_d1de3158/adoption.json | d5ae6f1dd6728681 | yes | AB | yes |
| D:/treeroute/runs/ndvi/headline/20261016_d1de3158/derived.json | 8ecc92b58cbd5f65 | yes | AB | yes |
| D:/treeroute/runs/pm25/headline/20261007_74e67609/adoption.json | b6408c90560b4585 | yes | AB | yes |
| D:/treeroute/runs/pm25/headline/20261007_74e67609/derived.json | 3e2d692b74ad6472 | yes | AB | yes |

Scripts: posthoc_A.py sha256 0cee249c0834dc2bbf0fe9ec458b200e20e096a4c5fc24e8d585a09584bab7c0; posthoc_B.py sha256 6b781c848bd84391da3bb71975135ebdcd806150ec45911d18e2c3f3f0db58ff; reconcile_AB.py sha256 5dcbe687b730c77f6207236bfa674d9a7a473b402e89a6c74b3487c7273b4c58.

## R15

**What.** AK4(a) cheap ablation table: every saved column at the nowcast (all arm__ arms including each link's trees-off, all placebo__ columns, all base__ baselines) with pooled MAE, anomaly R2, corr2 and hit rate, and the adopted arm's regret. Beside it (report-only) the per-region paired contrast of the adopted arm against every other selectable arm, and factor summaries (link, tool, weighting). NOT a test of the per-unit axis (M56); AK4(b) is the real ablation.

**Population.** Lead 0 labelled rows: pm25 91,428 rows / 127 groups (17 columns: 10 arms, 4 placebos, 3 baselines; 8 selectable tree arms); ndvi 94,527 / 133 (10: 5, 2, 3; 4 selectable); fire 94,702 / 40 (24: 15, 6, 3; 12 selectable); defo 369,096 / 42 (15: 9, 3, 3; 6 selectable); coral 2,312 / 37 (23: 15, 6, 2; 12 selectable).

**Formula in words.** Every saved column at the nowcast: pooled MAE, anomaly R2, corr2 and hit rate over labelled rows. Regret = MAE of the adopted arm minus MAE of the best selectable tree arm (arms without 'trees_off'), absolute and relative. Report-only: per-region contrast of every other selectable arm against the adopted arm (arm minus adopted, positive = adopted better), region jackknife, band tag. Factor effects as MAE differences.

<details><summary>Spec formula (verbatim)</summary>

Per column: pooled MAE, anomaly R2 (saved normal; NaN on coral), corr2, hit at verdict.json hit_tolerance (and hit_floor where the floor is declared), each checked against score_pooled.csv (rtol 1e-12). Selectable tree arms = arm__ columns whose name does not contain 'trees_off' (placebos and baselines are never selectable, R24). best = the selectable arm with the lowest pooled MAE; regret_abs = MAE(adopted) - MAE(best); regret_rel = regret_abs / MAE(best). Also print the lowest column overall (any kind) and mark eligible arms from adoption.json. Report-only: for each selectable arm a != adopted, d_g = MAE_a(g) - MAE_adopted(g) (positive = adopted better) from score_by_group.csv, group jackknife 1.96, tag with the run band, labelled post hoc. Factor summaries: weighting effect = MAE(link, tool, unweighted) - MAE(link, tool, gls); tool effect = MAE(plain) - MAE(corrector); link effect = best arm per link.

</details>

**Engine definitions cited.** C:/Users/moh the ghost/Desktop/data set for reserch paper/engine/treeroute/report/metrics.py score_table() 846 (pooled, macro and key lines), hit_rate() 688, corr2() 604, anomaly_r2() 580, group_jackknife() 1032, contrast_tag() 1097; layer/arms.py (arm set, R24); layer/decide.py (eligibility guard, adoption; M43-M44); pipeline/passes.py report() 1049-1065.

**A/B agreement: AGREE.** 1267 leaves compared (198 integers, 639 floats bit-identical, 0 at printed precision), 0 disagreements. A checks 522 (failed 0); B checks 482 (failed 0). Leaves only one side reports: A 0, B 0 (extra detail, not disagreements).

### Agreed values

| run | columns (arms/placebos/baselines) | adopted | MAE adopted | best selectable | MAE best | regret | regret rel | lowest column (any kind) | its MAE | eligible (adoption.json) |
|---|---|---|---|---|---|---|---|---|---|---|
| pm25 | 17 (10/4/3; 8 selectable) | log_c_corrector_unweighted | 3.588091134 | log_c_corrector_gls | 3.587480407 | 0.0006107 | 0.017% | log_c_corrector_gls | 3.587480407 | all 8 |
| ndvi | 10 (5/2/3; 4 selectable) | identity_plain_unweighted | 0.03146059686 | identity_plain_unweighted | 0.03146059686 | 0 | 0.000% | identity_plain_unweighted | 0.03146059686 | all 4 |
| fire | 24 (15/6/3; 12 selectable) | arcsine_corrector_gls | 0.004385064558 | log_c_corrector_gls | 0.004295794873 | 8.927e-05 | 2.078% | log_c_trees_off_unweighted | 0.004281302313 | arcsine_corrector_gls, arcsine_plain_gls |
| defo | 15 (9/3/3; 6 selectable) | log_c_corrector_unweighted | 0.005415798422 | log_c_corrector_unweighted | 0.005415798422 | 0 | 0.000% | log_c_corrector_unweighted | 0.005415798422 | all 6 |
| coral | 23 (15/6/2; 12 selectable) | arcsine_corrector_gls | 6.697989245 | arcsine_corrector_unweighted | 6.147485763 | 0.5505 | 8.955% | arcsine_corrector_unweighted | 6.147485763 | all 12 |

**pm25** (hit tolerance 1.58702, measurement-error floor 2; band 0.0462119):

| column | role | pooled MAE | anomaly R2 | corr2 | hit | hit at floor |
|---|---|---|---|---|---|---|
| arm__log_c_corrector_gls | selectable | 3.587480407 | 0.1847 | 0.8507 | 0.4541 | 0.5258 |
| arm__log_c_corrector_unweighted | ADOPTED | 3.588091134 | 0.1852 | 0.8518 | 0.4565 | 0.527 |
| placebo__log_c_placebo_corrector_unweighted | placebo | 3.591572881 | 0.1845 | 0.8516 | 0.455 | 0.5269 |
| placebo__log_c_placebo_corrector_gls | placebo | 3.592004339 | 0.1828 | 0.8503 | 0.4529 | 0.5255 |
| arm__log_c_plain_unweighted | selectable | 3.596454184 | 0.1843 | 0.8515 | 0.4539 | 0.5258 |
| arm__log_c_plain_gls | selectable | 3.597253889 | 0.1824 | 0.8501 | 0.4513 | 0.5243 |
| arm__identity_corrector_gls | selectable | 3.724001589 | 0.1716 | 0.8512 | 0.4363 | 0.5073 |
| placebo__identity_placebo_corrector_gls | placebo | 3.724106525 | 0.1714 | 0.8511 | 0.4357 | 0.5081 |
| arm__identity_plain_gls | selectable | 3.728449678 | 0.1715 | 0.851 | 0.4351 | 0.5069 |
| placebo__identity_placebo_corrector_unweighted | placebo | 3.774760312 | 0.1388 | 0.8482 | 0.4378 | 0.5087 |
| arm__identity_corrector_unweighted | selectable | 3.774844393 | 0.1394 | 0.8484 | 0.436 | 0.5075 |
| arm__identity_plain_unweighted | selectable | 3.777737418 | 0.14 | 0.8483 | 0.4368 | 0.507 |
| arm__log_c_trees_off_unweighted | arm | 3.853165559 | 0.0785 | 0.8301 | 0.4288 | 0.5021 |
| base__last5_normal | baseline | 3.971950892 | -0.1311 | 0.8094 | 0.4582 | 0.5286 |
| arm__identity_trees_off_unweighted | arm | 4.031610558 | 5.161e-11 | 0.8208 | 0.4151 | 0.4878 |
| base__guess_normal | baseline | 4.031610559 | 0 | 0.8208 | 0.4151 | 0.4878 |
| base__predict_zero | baseline | 17.51882561 | -9.247 | n/a | 0.01478 | 0.02188 |

pm25 report-only contrasts vs the adopted arm (d_g = MAE_arm(g) - MAE_adopted(g), positive = adopted better):

| arm | mean d | 95% CI | tag | regions adopted better |
|---|---|---|---|---|
| log_c_corrector_gls | -0.0006118 | [-0.02269, +0.02146] | EQUIVALENT | 77/127 |
| log_c_plain_unweighted | +0.008364 | [+0.00155, +0.01518] | EQUIVALENT | 83/127 |
| log_c_plain_gls | +0.009162 | [-0.01502, +0.03335] | EQUIVALENT | 83/127 |
| identity_corrector_gls | +0.1359 | [+0.09485, +0.177] | HELPS | 101/127 |
| identity_plain_gls | +0.1404 | [+0.1004, +0.1804] | HELPS | 103/127 |
| identity_corrector_unweighted | +0.1868 | [+0.1055, +0.268] | HELPS | 103/127 |
| identity_plain_unweighted | +0.1896 | [+0.1107, +0.2686] | HELPS | 104/127 |

**ndvi** (hit tolerance 0.0163763, measurement-error floor 0.02; band 0.000597471):

| column | role | pooled MAE | anomaly R2 | corr2 | hit | hit at floor |
|---|---|---|---|---|---|---|
| arm__identity_plain_unweighted | ADOPTED | 0.03146059686 | 0.3171 | 0.9632 | 0.4606 | 0.5228 |
| arm__identity_plain_gls | selectable | 0.03148296727 | 0.3171 | 0.9632 | 0.461 | 0.5228 |
| arm__identity_corrector_unweighted | selectable | 0.03149747357 | 0.3174 | 0.9632 | 0.4589 | 0.5216 |
| arm__identity_corrector_gls | selectable | 0.03150740801 | 0.3178 | 0.9632 | 0.4587 | 0.5213 |
| placebo__identity_placebo_corrector_unweighted | placebo | 0.03165363992 | 0.3124 | 0.9629 | 0.4569 | 0.5187 |
| placebo__identity_placebo_corrector_gls | placebo | 0.03166964675 | 0.3126 | 0.9629 | 0.4563 | 0.5186 |
| base__last5_normal | baseline | 0.03933500299 | -0.05228 | 0.9425 | 0.4047 | 0.4612 |
| arm__identity_trees_off_unweighted | arm | 0.03941411419 | 1.452e-09 | 0.9461 | 0.3894 | 0.4464 |
| base__guess_normal | baseline | 0.03941411443 | 0 | 0.9461 | 0.3894 | 0.4464 |
| base__predict_zero | baseline | 0.4364799704 | -65.53 | n/a | 0.01476 | 0.01864 |

ndvi report-only contrasts vs the adopted arm (d_g = MAE_arm(g) - MAE_adopted(g), positive = adopted better):

| arm | mean d | 95% CI | tag | regions adopted better |
|---|---|---|---|---|
| identity_plain_gls | +2.377e-05 | [-8.915e-06, +5.645e-05] | EQUIVALENT | 74/133 |
| identity_corrector_unweighted | +3.779e-05 | [-9.754e-06, +8.533e-05] | EQUIVALENT | 78/133 |
| identity_corrector_gls | +4.875e-05 | [-5.989e-06, +0.0001035] | EQUIVALENT | 77/133 |

**fire** (hit tolerance 0.00299839, measurement-error floor n/a; band 1.3567e-05):

| column | role | pooled MAE | anomaly R2 | corr2 | hit | hit at floor |
|---|---|---|---|---|---|---|
| arm__log_c_trees_off_unweighted | arm | 0.004281302313 | -0.003048 | 0.2101 | 0.9353 | n/a |
| base__predict_zero | baseline | 0.004284114619 | -0.2595 | n/a | 0.9814 | n/a |
| placebo__log_c_placebo_corrector_gls | placebo | 0.004294105489 | -0.005731 | 0.2105 | 0.9377 | n/a |
| arm__log_c_corrector_gls | selectable | 0.004295794873 | -0.004915 | 0.2113 | 0.9375 | n/a |
| arm__log_c_plain_gls | selectable | 0.004296987722 | -0.005482 | 0.2108 | 0.9374 | n/a |
| placebo__log_c_placebo_corrector_unweighted | placebo | 0.004320448579 | 0.001369 | 0.216 | 0.9353 | n/a |
| arm__log_c_corrector_unweighted | selectable | 0.004320857404 | 0.002172 | 0.2168 | 0.9354 | n/a |
| arm__log_c_plain_unweighted | selectable | 0.004322425348 | 0.001378 | 0.216 | 0.9352 | n/a |
| placebo__arcsine_placebo_corrector_gls | placebo | 0.004383043171 | 0.02453 | 0.2212 | 0.9483 | n/a |
| arm__arcsine_corrector_gls | ADOPTED | 0.004385064558 | 0.0261 | 0.2224 | 0.9482 | n/a |
| arm__arcsine_plain_gls | selectable | 0.00438567029 | 0.02531 | 0.2218 | 0.9482 | n/a |
| arm__arcsine_trees_off_unweighted | arm | 0.004428263566 | 0.02257 | 0.2198 | 0.9473 | n/a |
| arm__arcsine_corrector_unweighted | selectable | 0.004433140383 | 0.03493 | 0.2293 | 0.946 | n/a |
| placebo__arcsine_placebo_corrector_unweighted | placebo | 0.004433615607 | 0.03322 | 0.228 | 0.9461 | n/a |
| arm__arcsine_plain_unweighted | selectable | 0.004436316713 | 0.03358 | 0.2283 | 0.946 | n/a |
| base__last5_normal | baseline | 0.005873194595 | -0.08281 | 0.1876 | 0.9454 | n/a |
| base__guess_normal | baseline | 0.00625875788 | 0 | 0.2186 | 0.9134 | n/a |
| arm__identity_trees_off_unweighted | arm | 0.006258758011 | 5.519e-09 | 0.2186 | 0.9134 | n/a |
| placebo__identity_placebo_corrector_gls | placebo | 0.006458038247 | 0.01292 | 0.2243 | 0.8821 | n/a |
| arm__identity_corrector_gls | selectable | 0.006477791881 | 0.01435 | 0.2254 | 0.881 | n/a |
| arm__identity_plain_gls | selectable | 0.006482438031 | 0.01304 | 0.2245 | 0.8809 | n/a |
| placebo__identity_placebo_corrector_unweighted | placebo | 0.00666742366 | 0.01098 | 0.2265 | 0.8744 | n/a |
| arm__identity_corrector_unweighted | selectable | 0.006684976167 | 0.01283 | 0.2278 | 0.8731 | n/a |
| arm__identity_plain_unweighted | selectable | 0.006689094218 | 0.01041 | 0.2263 | 0.8735 | n/a |

fire report-only contrasts vs the adopted arm (d_g = MAE_arm(g) - MAE_adopted(g), positive = adopted better):

| arm | mean d | 95% CI | tag | regions adopted better |
|---|---|---|---|---|
| log_c_corrector_gls | -8.772e-05 | [-0.0002132, +3.773e-05] | CANNOT TELL | 26/40 |
| log_c_plain_gls | -8.652e-05 | [-0.0002118, +3.88e-05] | CANNOT TELL | 27/40 |
| log_c_corrector_unweighted | -6.265e-05 | [-0.0001774, +5.211e-05] | CANNOT TELL | 30/40 |
| log_c_plain_unweighted | -6.108e-05 | [-0.0001756, +5.34e-05] | CANNOT TELL | 30/40 |
| arcsine_plain_gls | +6.205e-07 | [-1.712e-06, +2.953e-06] | EQUIVALENT | 26/40 |
| arcsine_corrector_unweighted | +4.824e-05 | [+5.76e-06, +9.072e-05] | HELPS | 29/40 |
| arcsine_plain_unweighted | +5.143e-05 | [+8.211e-06, +9.466e-05] | HELPS | 28/40 |
| identity_corrector_gls | +0.002096 | [+0.001078, +0.003115] | HELPS | 36/40 |
| identity_plain_gls | +0.002101 | [+0.001078, +0.003124] | HELPS | 36/40 |
| identity_corrector_unweighted | +0.002304 | [+0.001224, +0.003384] | HELPS | 36/40 |
| identity_plain_unweighted | +0.002308 | [+0.001221, +0.003395] | HELPS | 36/40 |

**defo** (hit tolerance 0.00353147, measurement-error floor n/a; band 0.000110449):

| column | role | pooled MAE | anomaly R2 | corr2 | hit | hit at floor |
|---|---|---|---|---|---|---|
| arm__log_c_corrector_unweighted | ADOPTED | 0.005415798422 | 0.05176 | 0.01691 | 0.834 | n/a |
| arm__log_c_plain_unweighted | selectable | 0.005416406367 | 0.05159 | 0.01674 | 0.8339 | n/a |
| placebo__log_c_placebo_corrector_unweighted | placebo | 0.005419502142 | 0.05141 | 0.01652 | 0.8339 | n/a |
| arm__log_c_trees_off_unweighted | arm | 0.00571459748 | 0.04119 | 0.008624 | 0.8192 | n/a |
| arm__arcsine_plain_unweighted | selectable | 0.005726304748 | 0.06626 | 0.02447 | 0.7868 | n/a |
| placebo__arcsine_placebo_corrector_unweighted | placebo | 0.005726804843 | 0.06587 | 0.02411 | 0.7868 | n/a |
| arm__arcsine_corrector_unweighted | selectable | 0.00573436398 | 0.06702 | 0.02509 | 0.7858 | n/a |
| base__predict_zero | baseline | 0.006120272784 | 0.02146 | n/a | 0.8065 | n/a |
| arm__arcsine_trees_off_unweighted | arm | 0.006247059151 | 0.04706 | 0.008296 | 0.754 | n/a |
| placebo__identity_placebo_corrector_unweighted | placebo | 0.007894508542 | 0.0512 | 0.01937 | 0.6332 | n/a |
| arm__identity_plain_unweighted | selectable | 0.007910046311 | 0.05186 | 0.02001 | 0.6335 | n/a |
| arm__identity_corrector_unweighted | selectable | 0.007973050139 | 0.05373 | 0.02134 | 0.6267 | n/a |
| base__guess_normal | baseline | 0.008404857347 | 0 | 0.003557 | 0.667 | n/a |
| arm__identity_trees_off_unweighted | arm | 0.008404857348 | 2.019e-10 | 0.003557 | 0.667 | n/a |
| base__last5_normal | baseline | 0.008664554825 | -0.1284 | 0.005718 | 0.7198 | n/a |

defo report-only contrasts vs the adopted arm (d_g = MAE_arm(g) - MAE_adopted(g), positive = adopted better):

| arm | mean d | 95% CI | tag | regions adopted better |
|---|---|---|---|---|
| log_c_plain_unweighted | +6.079e-07 | [-7.882e-06, +9.098e-06] | EQUIVALENT | 22/42 |
| arcsine_plain_unweighted | +0.0003105 | [+0.0001478, +0.0004732] | HELPS | 36/42 |
| arcsine_corrector_unweighted | +0.0003186 | [+0.0001546, +0.0004825] | HELPS | 36/42 |
| identity_plain_unweighted | +0.002494 | [+0.001742, +0.003246] | HELPS | 40/42 |
| identity_corrector_unweighted | +0.002557 | [+0.001759, +0.003355] | HELPS | 40/42 |

**coral** (hit tolerance 5.13614, measurement-error floor n/a; band 0.917558):

| column | role | pooled MAE | anomaly R2 | corr2 | hit | hit at floor |
|---|---|---|---|---|---|---|
| arm__arcsine_corrector_unweighted | selectable | 6.147485763 | n/a | 0.5324 | 0.7318 | n/a |
| arm__arcsine_plain_unweighted | selectable | 6.159354031 | n/a | 0.5295 | 0.7305 | n/a |
| placebo__arcsine_placebo_corrector_unweighted | placebo | 6.16526055 | n/a | 0.5284 | 0.7314 | n/a |
| arm__log_c_corrector_unweighted | selectable | 6.359479297 | n/a | 0.4653 | 0.7764 | n/a |
| arm__log_c_plain_unweighted | selectable | 6.375598571 | n/a | 0.4673 | 0.7729 | n/a |
| placebo__log_c_placebo_corrector_unweighted | placebo | 6.378480894 | n/a | 0.4659 | 0.7725 | n/a |
| arm__arcsine_corrector_gls | ADOPTED | 6.697989245 | n/a | 0.4637 | 0.7422 | n/a |
| placebo__arcsine_placebo_corrector_gls | placebo | 6.731545728 | n/a | 0.4582 | 0.7405 | n/a |
| arm__arcsine_plain_gls | selectable | 6.735936796 | n/a | 0.4563 | 0.7413 | n/a |
| arm__log_c_corrector_gls | selectable | 7.007205326 | n/a | 0.3028 | 0.779 | n/a |
| arm__log_c_plain_gls | selectable | 7.033586763 | n/a | 0.2986 | 0.7781 | n/a |
| placebo__log_c_placebo_corrector_gls | placebo | 7.037013485 | n/a | 0.2988 | 0.7781 | n/a |
| arm__identity_corrector_unweighted | selectable | 7.11041778 | n/a | 0.5024 | 0.6622 | n/a |
| arm__identity_plain_unweighted | selectable | 7.117837856 | n/a | 0.5009 | 0.6644 | n/a |
| placebo__identity_placebo_corrector_unweighted | placebo | 7.121152203 | n/a | 0.5001 | 0.6635 | n/a |
| arm__identity_corrector_gls | selectable | 7.40994183 | n/a | 0.4519 | 0.6704 | n/a |
| placebo__identity_placebo_corrector_gls | placebo | 7.437607615 | n/a | 0.4474 | 0.6717 | n/a |
| arm__identity_plain_gls | selectable | 7.440503695 | n/a | 0.4462 | 0.6717 | n/a |
| arm__log_c_trees_off_unweighted | arm | 7.517219896 | n/a | 0.09499 | 0.7785 | n/a |
| arm__arcsine_trees_off_unweighted | arm | 7.535700369 | n/a | 0.1625 | 0.7487 | n/a |
| arm__identity_trees_off_unweighted | arm | 7.974625859 | n/a | 0.2228 | 0.6856 | n/a |
| base__predict_zero | baseline | 8.099835075 | n/a | n/a | 0.7621 | n/a |
| base__donor_median | baseline | 8.294498354 | n/a | n/a | 0.7729 | n/a |

coral report-only contrasts vs the adopted arm (d_g = MAE_arm(g) - MAE_adopted(g), positive = adopted better):

| arm | mean d | 95% CI | tag | regions adopted better |
|---|---|---|---|---|
| arcsine_corrector_unweighted | -2.923 | [-5.527, -0.3195] | HURTS | 16/37 |
| arcsine_plain_unweighted | -2.915 | [-5.564, -0.2659] | HURTS | 17/37 |
| identity_plain_unweighted | -2.47 | [-5.463, +0.523] | CANNOT TELL | 25/37 |
| identity_corrector_unweighted | -2.461 | [-5.437, +0.5144] | CANNOT TELL | 25/37 |
| identity_corrector_gls | -0.371 | [-1.406, +0.6637] | CANNOT TELL | 25/37 |
| identity_plain_gls | -0.2914 | [-1.28, +0.6967] | CANNOT TELL | 25/37 |
| arcsine_plain_gls | +0.1272 | [+0.0135, +0.2408] | EQUIVALENT | 25/37 |
| log_c_corrector_unweighted | +0.2107 | [-0.9618, +1.383] | CANNOT TELL | 15/37 |
| log_c_plain_unweighted | +0.216 | [-0.9178, +1.35] | CANNOT TELL | 15/37 |
| log_c_corrector_gls | +2.544 | [+0.5482, +4.54] | HELPS | 20/37 |
| log_c_plain_gls | +2.623 | [+0.6096, +4.636] | HELPS | 20/37 |

Factor summaries (weighting = MAE unweighted - MAE GLS; tool = MAE plain - MAE corrector; link = best arm per link):

| run | weighting effect | tool effect | best arm per link (ascending) |
|---|---|---|---|
| pm25 | identity plain +0.0493; identity corrector +0.0508; log_c plain -0.0008; log_c corrector +0.000611 | identity unweighted +0.00289; identity gls +0.00445; log_c unweighted +0.00836; log_c gls +0.00977 | log_c 3.58748; identity 3.724 |
| ndvi | identity plain -2.24e-05; identity corrector -9.93e-06 | identity unweighted -3.69e-05; identity gls -2.44e-05 | identity 0.0314606 |
| fire | arcsine plain +5.06e-05; arcsine corrector +4.81e-05; identity plain +0.000207; identity corrector +0.000207; log_c plain +2.54e-05; log_c corrector +2.51e-05 | arcsine unweighted +3.18e-06; arcsine gls +6.06e-07; identity unweighted +4.12e-06; identity gls +4.65e-06; log_c unweighted +1.57e-06; log_c gls +1.19e-06 | log_c 0.00429579; arcsine 0.00438506; identity 0.00647779 |
| defo | n/a (no GLS arms) | arcsine unweighted -8.06e-06; identity unweighted -6.3e-05; log_c unweighted +6.08e-07 | log_c 0.0054158; arcsine 0.0057263; identity 0.00791005 |
| coral | arcsine plain -0.577; arcsine corrector -0.551; identity plain -0.323; identity corrector -0.3; log_c plain -0.658; log_c corrector -0.648 | arcsine unweighted +0.0119; arcsine gls +0.0379; identity unweighted +0.00742; identity gls +0.0306; log_c unweighted +0.0161; log_c gls +0.0264 | arcsine 6.14749; log_c 6.35948; identity 7.11042 |

### Fact-sheet comparison

| check | fact sheet / probe states | agreed value | status |
|---|---|---|---|
| pm25 best log corrector GLS | 3.5875 | 3.5874804069348305 | MATCHES |
| pm25 best arm | arm__log_c_corrector_gls | arm__log_c_corrector_gls | MATCHES |
| pm25 adopted log corrector unw | 3.5881 | 3.588091134093021 | MATCHES |
| pm25 regret | 0.0006 | 0.0006107271581905493 | MATCHES |
| pm25 regret (score_pooled line) | 0.00061 | 0.0006107271581905493 | MATCHES |
| pm25 best (score_pooled line, 10 dp) | 3.5874804069 | 3.5874804069348305 | MATCHES |
| pm25 adopted (score_pooled line, 10 dp) | 3.5880911341 | 3.588091134093021 | MATCHES |
| pm25 plain unw | 3.5965 | 3.596454183542564 | MATCHES |
| pm25 corrector unw | 3.5881 | 3.588091134093021 | MATCHES |
| pm25 identity arms min | 3.724 | 3.7240015891488047 | MATCHES |
| pm25 identity arms max | 3.778 | 3.777737417581777 | MATCHES |
| pm25 log trees-off | 3.853 | 3.85316555881606 | MATCHES |
| ndvi adopted identity plain unw | 0.03146 | 0.03146059686292064 | MATCHES |
| ndvi adopted is best (regret 0) | regret 0 | 0.0 | MATCHES |
| ndvi other arms min | 0.03148 | 0.03148296727485251 | MATCHES |
| ndvi other arms max | 0.03151 | 0.03150740801496085 | MATCHES |
| fire best log corrector GLS | 0.004296 | 0.0042957948726572255 | MATCHES |
| fire adopted | 0.004385 | 0.004385064558301006 | MATCHES |
| fire regret rel % (fact sheet) | 2.1 | 2.0780714231022337 | MATCHES |
| fire regret rel % (score_pooled line) | 2.08 | 2.0780714231022337 | MATCHES |
| fire all four log arms beat adopted | true | [0.0042957948726572255, 0.004320857403502066, 0.004296987722157366, 0.004322425347543649] | MATCHES |
| fire log arms min | 0.004296 | 0.0042957948726572255 | MATCHES |
| fire log arms max | 0.004322 | 0.004322425347543649 | MATCHES |
| fire log trees-off beats them all | true | 0.004281302312816825 | MATCHES |
| fire log trees-off | 0.004281 | 0.004281302312816825 | MATCHES |
| fire identity arms min | 0.00648 | 0.006477791880656638 | MATCHES |
| fire identity arms max | 0.00669 | 0.006689094217587933 | MATCHES |
| fire identity arms > identity normal | true | 0.006258758011328549 | MATCHES |
| fire identity normal | 0.006259 | 0.006258758011328549 | MATCHES |
| defo adopted | 0.0054158 | 0.005415798421978487 | MATCHES |
| defo log plain | 0.0054164 | 0.005416406367405097 | MATCHES |
| defo regret 0 | 0 | 0.0 | MATCHES |
| defo 'adopted = log plain' (wording) | equal | adopted 0.0054157984 < log plain 0.0054164064 (diff 6.08e-07); '=' is not literal | WORDING |
| defo arcsine arms min | 0.00573 | 0.00572630474833318 | MATCHES |
| defo arcsine arms max | 0.00573 | 0.005734363979621296 | MATCHES |
| defo identity arms min | 0.00791 | 0.007910046310872217 | MATCHES |
| defo identity arms max | 0.00797 | 0.007973050139196167 | MATCHES |
| defo predict-zero | 0.00612 | 0.00612027278413151 | MATCHES |
| defo identity arms > PZ | true | 0.007910046310872217 | MATCHES |
| coral every unweighted arcsine/log arm beats adopted | true | [6.14748576299595, 6.159354031225012, 6.359479297265017, 6.375598571033158] | MATCHES |
| coral unweighted arcsine/log min | 6.147 | 6.14748576299595 | MATCHES |
| coral unweighted arcsine/log max | 6.376 | 6.375598571033158 | MATCHES |
| coral adopted | 6.698 | 6.69798924506233 | MATCHES |
| coral best arm | arm__arcsine_corrector_unweighted | arm__arcsine_corrector_unweighted | MATCHES |
| coral best | 6.147 | 6.14748576299595 | MATCHES |
| coral regret | 0.55 | 0.5505034820663806 | MATCHES |
| coral regret (score_pooled line) | 0.5505 | 0.5505034820663806 | MATCHES |
| coral regret rel % (fact sheet) | 9.0 | 8.954937079807 | MATCHES |
| coral regret rel % (score_pooled line) | 8.95 | 8.954937079807 | MATCHES |
| coral best (score_pooled line, 10 dp) | 6.1474857630 | 6.14748576299595 | MATCHES |
| coral adopted (score_pooled line, 10 dp) | 6.6979892451 | 6.69798924506233 | MATCHES |
| fire best (score_pooled line) | 0.0042957949 | 0.0042957948726572255 | MATCHES |
| fire adopted (score_pooled line) | 0.0043850646 | 0.004385064558301006 | MATCHES |

### Inputs

| file | sha256 prefix (re-hashed now) | in spec list | read by | matches spec/A/B prefixes |
|---|---|---|---|---|
| D:/treeroute/runs/coral/headline/20261020_f3b8e3da/adoption.json | 2106a36efee4f9fc | yes | AB | yes |
| D:/treeroute/runs/coral/headline/20261020_f3b8e3da/score_by_group.csv | 08dd01c06c8eedc2 | yes | AB | yes |
| D:/treeroute/runs/coral/headline/20261020_f3b8e3da/score_pooled.csv | bbaa21aa184a1054 | yes | AB | yes |
| D:/treeroute/runs/coral/headline/20261020_f3b8e3da/test_preds.parquet | dd07762558023d5f | yes | A | yes |
| D:/treeroute/runs/coral/headline/20261020_f3b8e3da/verdict.json | 6bf9b04970173323 | yes | AB | yes |
| D:/treeroute/runs/defo/headline/20261017_d71c61f4/adoption.json | d8ebdd4cc458b276 | yes | AB | yes |
| D:/treeroute/runs/defo/headline/20261017_d71c61f4/score_by_group.csv | d02e8f48ddef39ce | yes | AB | yes |
| D:/treeroute/runs/defo/headline/20261017_d71c61f4/score_pooled.csv | 8f1c161ad318e32c | yes | AB | yes |
| D:/treeroute/runs/defo/headline/20261017_d71c61f4/test_preds.parquet | 3a002e9a9deb006a | yes | A | yes |
| D:/treeroute/runs/defo/headline/20261017_d71c61f4/verdict.json | 34d090aae96fed3c | yes | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/adoption.json | 75f70e5cd22039b6 | yes | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/score_by_group.csv | 03585591911c6e01 | yes | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/score_pooled.csv | 9236a25380d9aede | yes | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/test_preds.parquet | 86e9c97a58a9b714 | yes | A | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/verdict.json | 6c744bc1a0647e37 | yes | AB | yes |
| D:/treeroute/runs/ndvi/headline/20261016_d1de3158/adoption.json | d5ae6f1dd6728681 | yes | AB | yes |
| D:/treeroute/runs/ndvi/headline/20261016_d1de3158/score_by_group.csv | be1381c5568d225e | yes | AB | yes |
| D:/treeroute/runs/ndvi/headline/20261016_d1de3158/score_pooled.csv | 3a7e09b6156e4449 | yes | AB | yes |
| D:/treeroute/runs/ndvi/headline/20261016_d1de3158/test_preds.parquet | 87c0b1414af7e370 | yes | A | yes |
| D:/treeroute/runs/ndvi/headline/20261016_d1de3158/verdict.json | 535ef992b5057ed7 | yes | AB | yes |
| D:/treeroute/runs/pm25/headline/20261007_74e67609/adoption.json | b6408c90560b4585 | yes | AB | yes |
| D:/treeroute/runs/pm25/headline/20261007_74e67609/score_by_group.csv | 6fed1e7be9456655 | yes | AB | yes |
| D:/treeroute/runs/pm25/headline/20261007_74e67609/score_pooled.csv | 8a7d2f44f00a9e7c | yes | AB | yes |
| D:/treeroute/runs/pm25/headline/20261007_74e67609/test_preds.parquet | 9e62fe4256c08c50 | yes | A | yes |
| D:/treeroute/runs/pm25/headline/20261007_74e67609/verdict.json | af031ef5a44dbe67 | yes | AB | yes |

Scripts: posthoc_A.py sha256 0cee249c0834dc2bbf0fe9ec458b200e20e096a4c5fc24e8d585a09584bab7c0; posthoc_B.py sha256 6b781c848bd84391da3bb71975135ebdcd806150ec45911d18e2c3f3f0db58ff; reconcile_AB.py sha256 5dcbe687b730c77f6207236bfa674d9a7a473b402e89a6c74b3487c7273b4c58.

## P29

**What.** Sensitivity of every deciding verdict to the interval method: t(G-1) instead of z = 1.96, two-sided p-values (z and t), the re-applied tag, Holm across the five nowcast verdicts, the band as a share of the deciding reference MAE, and the count of deciding verdicts. Report-only, post hoc.

**Population.** 79 deciding verdict rows: 14 of ours (pm25 leads 0/6/12, ndvi 0/6/12, fire 0/6/12, defo 0/1, coral 0/183/365; lead 0 = verdicts CSV rows 'all' (source verdict.json), leads > 0 = rows 'common' (source ladder.json); 6 are declined) + 65 RIVALS_TABLE rows with decides == True (53 common, 12 human; 12 of them IDENTICAL). G = the row's n_groups: pm25 127, ndvi 133, fire 40, defo 42, coral 37 (32 on the coral human CRW rows). Holm: the 5 lead-0 own verdicts.

**Formula in words.** For each of the 79 deciding verdict rows: mean and SE from the source file, interval with the t quantile for G-1 degrees of freedom instead of 1.96, two-sided p-values (normal and t), the D74 tag re-applied with the t interval, Holm over the five nowcast verdicts of ours, and band as a percentage of the deciding reference MAE.

<details><summary>Spec formula (verbatim)</summary>

For each row take mean and SE from its source (own: contrast_mean, contrast_se; common: board d_mean, d_se; human: human board d_mean, d_se) and check SE == (high - low)/(2*1.96) and the recorded CI == mean +- 1.96*SE (rtol 1e-9; RIVALS_TABLE d_low/d_high cross-checked too). t CI = mean +- t_{0.975, G-1}*SE (scipy.stats.t.ppf). p_z = 2*(1 - Phi(|mean/SE|)); p_t = 2*(1 - T_{G-1}(|mean/SE|)). tag_t = the D74 rule with the t CI and the row's own band; rows tagged declined or identical keep their tag (no interval). Holm step-down at alpha 0.05 over the 5 lead-0 own verdicts, separately with p_z and p_t (adjusted p_(i) = max_{j<=i} min(1, (m-j+1) p_(j)), m = 5). Band share = 100 * band / mae_reference of the lead-0 'all' pooled headline row (own-link trees-off; coral donor median). Fire's blocked-jackknife CI is read from jackknife.csv (report-only row). Count rows = 79.

</details>

**Engine definitions cited.** C:/Users/moh the ghost/Desktop/data set for reserch paper/engine/treeroute/report/metrics.py group_jackknife() 1032, contrast_tag() 1097, single_verdict() 1141, blocked_jackknife() 1058, equivalence_band() 1175; engine_constants.py JACKKNIFE_Z (S2.jackknife_z = 1.96, line 323); rival harness D:/treeroute/rivals_build/rivals/harness.py score() 2494-2513 (contrast_tag with the run band); human tool D:/treeroute/human_rivals_build/human/rivals_human/board.py 1152-1155; engine/PREREGISTRATION_DRAFT.md sections 7-8 (z = 1.96, no multiplicity correction).

**A/B agreement: AGREE.** 1248 leaves compared (87 integers, 111 floats bit-identical, 646 at printed precision), 0 disagreements. A checks 226 (failed 0); B checks 619 (failed 0). Leaves only one side reports: A 0, B 0 (extra detail, not disagreements).

### Agreed values

79 deciding rows: 14 own, 53 common, 12 human. Declined own rows: 6. IDENTICAL rows: 12. Tags that change under t: 2. Largest relative error of SE == (high-low)/(2*1.96): 5.8e-16; of CI == mean +- 1.96 SE: 0.

Rows whose tag changes under t(G-1):

| row | contrast | G | t quantile | mean | z CI | t CI | p_z | p_t | tag z -> t |
|---|---|---|---|---|---|---|---|---|---|
| own fire lead 0 | ours vs arm__arcsine_trees_off_unweighted | 40 | 2.022691 | +4.23e-05 | [+1.455e-07, +8.445e-05] | [-1.203e-06, +8.58e-05] | 0.049210 | 0.056355 | HELPS -> CANNOT TELL |
| human coral lead 183 | crw_dhw | 32 | 2.039513 | +1.85 | [+0.001912, +3.698] | [-0.07307, +3.773] | 0.049759 | 0.058791 | HELPS -> CANNOT TELL |

Holm step-down over the 5 nowcast verdicts of ours (alpha 0.05):

| problem | p_z | Holm-adjusted p_z | survives (z) | p_t | Holm-adjusted p_t | survives (t) |
|---|---|---|---|---|---|---|
| ndvi | 2.765e-40 | 1.383e-39 | True | 4.201e-26 | 2.1e-25 | True |
| pm25 | 3.124e-09 | 1.25e-08 | True | 2.791e-08 | 1.117e-07 | True |
| coral | 0.001605 | 0.004814 | True | 0.003235 | 0.009704 | True |
| defo | 0.005578 | 0.01116 | True | 0.008349 | 0.0167 | True |
| fire | 0.04921 | 0.04921 | True | 0.05635 | 0.05635 | False |

Band as a share of the deciding reference MAE (lead-0 'all' pooled headline row):

| problem | band | reference | reference MAE | band share |
|---|---|---|---|---|
| pm25 | 0.0462119 | arm__log_c_trees_off_unweighted | 3.853166 | 1.1993% |
| ndvi | 0.000597471 | arm__identity_trees_off_unweighted | 0.03941411 | 1.5159% |
| fire | 1.3567e-05 | arm__arcsine_trees_off_unweighted | 0.004428264 | 0.3064% |
| defo | 0.000110449 | arm__log_c_trees_off_unweighted | 0.005714597 | 1.9328% |
| coral | 0.917558 | base__donor_median | 8.294498 | 11.0623% |

Fire blocked jackknife (read from jackknife.csv, report only): mean 4.078e-05, SE 2.187e-05, CI [-2.083e-06, +8.365e-05], 39 blocks.

All 79 deciding rows (own rows: ours vs the reference; rival rows: d = MAE_rival - MAE_ours):

| kind | problem | lead | vs | G | mean | SE | z CI | t CI | p_z | p_t | tag (z) | tag (t) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| own | pm25 | 0 | ours | 127 | +0.2651 | 0.04474 | [+0.1774, +0.3527] | [+0.1765, +0.3536] | 3.124e-09 | 2.791e-08 | HELPS | HELPS |
| own | pm25 | 6 | ours | 127 | +0.03247 | 0.02806 | [-0.02252, +0.08747] | [-0.02306, +0.088] | 0.2472 | 0.2494 | CANNOT TELL | CANNOT TELL |
| own | pm25 | 12 | ours | 127 | +0 | 0 | [+0, +0] | [n/a, n/a] | n/a | n/a | declined | declined |
| common | pm25 | 0 | ridge | 127 | -0.1617 | 0.09214 | [-0.3423, +0.01888] | [-0.3441, +0.02063] | 0.07924 | 0.08167 | CANNOT TELL | CANNOT TELL |
| common | pm25 | 0 | rf | 127 | +0.1044 | 0.0327 | [+0.04029, +0.1685] | [+0.03967, +0.1691] | 0.001414 | 0.001785 | HELPS | HELPS |
| common | pm25 | 0 | lgbm | 127 | -0.03577 | 0.02508 | [-0.08493, +0.01338] | [-0.0854, +0.01386] | 0.1538 | 0.1562 | CANNOT TELL | CANNOT TELL |
| common | pm25 | 6 | ridge | 127 | -0.2466 | 0.08939 | [-0.4219, -0.07143] | [-0.4236, -0.06974] | 0.005796 | 0.00666 | HURTS | HURTS |
| common | pm25 | 6 | rf | 127 | -0.0244 | 0.01993 | [-0.06345, +0.01466] | [-0.06383, +0.01504] | 0.2208 | 0.2231 | CANNOT TELL | CANNOT TELL |
| common | pm25 | 6 | lgbm | 127 | +0.2077 | 0.05341 | [+0.103, +0.3124] | [+0.102, +0.3134] | 0.0001008 | 0.0001622 | HELPS | HELPS |
| common | pm25 | 12 | ridge | 127 | -0.4274 | 0.1067 | [-0.6366, -0.2183] | [-0.6386, -0.2162] | 6.198e-05 | 0.0001053 | HURTS | HURTS |
| common | pm25 | 12 | rf | 127 | -0.1934 | 0.04844 | [-0.2884, -0.09848] | [-0.2893, -0.09756] | 6.522e-05 | 0.0001101 | HURTS | HURTS |
| common | pm25 | 12 | lgbm | 127 | -0.2393 | 0.06008 | [-0.357, -0.1215] | [-0.3582, -0.1204] | 6.817e-05 | 0.0001145 | HURTS | HURTS |
| human | pm25 | 0 | merra2_lag1 | 127 | +4.856 | 4.593 | [-4.146, +13.86] | [-4.233, +13.94] | 0.2904 | 0.2924 | CANNOT TELL | CANNOT TELL |
| own | ndvi | 0 | ours | 133 | +0.007918 | 0.0005959 | [+0.00675, +0.009086] | [+0.006739, +0.009097] | 2.765e-40 | 4.201e-26 | HELPS | HELPS |
| own | ndvi | 6 | ours | 133 | +0 | 0 | [+0, +0] | [n/a, n/a] | n/a | n/a | declined | declined |
| own | ndvi | 12 | ours | 133 | +0 | 0 | [+0, +0] | [n/a, n/a] | n/a | n/a | declined | declined |
| common | ndvi | 0 | ridge | 133 | +0.01147 | 0.0004702 | [+0.01055, +0.01239] | [+0.01054, +0.0124] | 2.11e-131 | 9.607e-51 | HELPS | HELPS |
| common | ndvi | 0 | rf | 133 | +0.00373 | 0.0003277 | [+0.003088, +0.004373] | [+0.003082, +0.004378] | 5.082e-30 | 2.437e-21 | HELPS | HELPS |
| common | ndvi | 0 | lgbm | 133 | +0.0005165 | 0.0002163 | [+9.263e-05, +0.0009404] | [+8.872e-05, +0.0009443] | 0.01693 | 0.01834 | CANNOT TELL | CANNOT TELL |
| common | ndvi | 6 | ridge | 133 | -0.00115 | 0.0002407 | [-0.001622, -0.0006785] | [-0.001627, -0.0006742] | 1.765e-06 | 4.633e-06 | HURTS | HURTS |
| common | ndvi | 6 | rf | 133 | +0 | 0 | [+0, +0] | [n/a, n/a] | n/a | n/a | IDENTICAL | IDENTICAL |
| common | ndvi | 6 | lgbm | 133 | +0 | 0 | [+0, +0] | [n/a, n/a] | n/a | n/a | IDENTICAL | IDENTICAL |
| common | ndvi | 12 | ridge | 133 | +0 | 0 | [+0, +0] | [n/a, n/a] | n/a | n/a | IDENTICAL | IDENTICAL |
| common | ndvi | 12 | rf | 133 | +0 | 0 | [+0, +0] | [n/a, n/a] | n/a | n/a | IDENTICAL | IDENTICAL |
| common | ndvi | 12 | lgbm | 133 | +0 | 0 | [+0, +0] | [n/a, n/a] | n/a | n/a | IDENTICAL | IDENTICAL |
| human | ndvi | 0 | bardl_h1 | 133 | +0.002749 | 0.0002614 | [+0.002237, +0.003261] | [+0.002232, +0.003266] | 7.21e-26 | 3.645e-19 | HELPS | HELPS |
| human | ndvi | 0 | kraft_lstm | 133 | +0.007918 | 0.0005959 | [+0.00675, +0.009086] | [+0.006739, +0.009097] | 2.765e-40 | 4.201e-26 | HELPS | HELPS |
| own | fire | 0 | ours | 40 | +4.23e-05 | 2.151e-05 | [+1.455e-07, +8.445e-05] | [-1.203e-06, +8.58e-05] | 0.04921 | 0.05635 | HELPS | CANNOT TELL (CHANGES) |
| own | fire | 6 | ours | 40 | +0 | 0 | [+0, +0] | [n/a, n/a] | n/a | n/a | declined | declined |
| own | fire | 12 | ours | 40 | +0 | 0 | [+0, +0] | [n/a, n/a] | n/a | n/a | declined | declined |
| common | fire | 0 | ridge | 40 | +0.001872 | 0.0004824 | [+0.0009265, +0.002817] | [+0.0008963, +0.002848] | 0.0001041 | 0.0003905 | HELPS | HELPS |
| common | fire | 0 | rf | 40 | -0.0001178 | 6.724e-05 | [-0.0002496, +1.395e-05] | [-0.0002538, +1.817e-05] | 0.07969 | 0.08755 | CANNOT TELL | CANNOT TELL |
| common | fire | 0 | lgbm | 40 | -9.175e-05 | 6.507e-05 | [-0.0002193, +3.58e-05] | [-0.0002234, +3.988e-05] | 0.1586 | 0.1665 | CANNOT TELL | CANNOT TELL |
| common | fire | 0 | lgbm_tweedie | 40 | -0.0003412 | 0.0001241 | [-0.0005845, -9.791e-05] | [-0.0005923, -9.013e-05] | 0.005981 | 0.009014 | HURTS | HURTS |
| common | fire | 6 | ridge | 40 | +0 | 0 | [+0, +0] | [n/a, n/a] | n/a | n/a | IDENTICAL | IDENTICAL |
| common | fire | 6 | rf | 40 | +0 | 0 | [+0, +0] | [n/a, n/a] | n/a | n/a | IDENTICAL | IDENTICAL |
| common | fire | 6 | lgbm | 40 | +0 | 0 | [+0, +0] | [n/a, n/a] | n/a | n/a | IDENTICAL | IDENTICAL |
| common | fire | 6 | lgbm_tweedie | 40 | -0.002156 | 0.0005923 | [-0.003317, -0.0009949] | [-0.003354, -0.0009578] | 0.000273 | 0.0007908 | HURTS | HURTS |
| common | fire | 12 | ridge | 40 | +0 | 0 | [+0, +0] | [n/a, n/a] | n/a | n/a | IDENTICAL | IDENTICAL |
| common | fire | 12 | rf | 40 | +0 | 0 | [+0, +0] | [n/a, n/a] | n/a | n/a | IDENTICAL | IDENTICAL |
| common | fire | 12 | lgbm | 40 | +0 | 0 | [+0, +0] | [n/a, n/a] | n/a | n/a | IDENTICAL | IDENTICAL |
| common | fire | 12 | lgbm_tweedie | 40 | -0.002191 | 0.0005866 | [-0.003341, -0.001042] | [-0.003378, -0.001005] | 0.000187 | 0.0005977 | HURTS | HURTS |
| own | defo | 0 | ours | 42 | +0.0002988 | 0.0001078 | [+8.75e-05, +0.0005101] | [+8.108e-05, +0.0005165] | 0.005578 | 0.008349 | HELPS | HELPS |
| own | defo | 1 | ours | 42 | +0.0003069 | 0.0001044 | [+0.0001022, +0.0005115] | [+9.601e-05, +0.0005177] | 0.003291 | 0.005384 | HELPS | HELPS |
| common | defo | 0 | ridge | 42 | +0.0003897 | 0.0001531 | [+8.958e-05, +0.0006899] | [+8.046e-05, +0.000699] | 0.01093 | 0.01479 | HELPS | HELPS |
| common | defo | 0 | rf | 42 | +7.272e-05 | 2.175e-05 | [+3.009e-05, +0.0001154] | [+2.88e-05, +0.0001166] | 0.0008272 | 0.001776 | CANNOT TELL | CANNOT TELL |
| common | defo | 0 | lgbm | 42 | +4.958e-05 | 1.979e-05 | [+1.078e-05, +8.838e-05] | [+9.604e-06, +8.956e-05] | 0.01225 | 0.01632 | EQUIVALENT | EQUIVALENT |
| common | defo | 0 | lgbm_tweedie | 42 | +0.000898 | 0.0001344 | [+0.0006346, +0.001161] | [+0.0006266, +0.001169] | 2.339e-11 | 4.626e-08 | HELPS | HELPS |
| common | defo | 1 | ridge | 42 | +0.0002595 | 0.0001137 | [+3.672e-05, +0.0004823] | [+2.995e-05, +0.000489] | 0.02242 | 0.02768 | HELPS | HELPS |
| common | defo | 1 | rf | 42 | -3.109e-05 | 1.859e-05 | [-6.752e-05, +5.338e-06] | [-6.863e-05, +6.445e-06] | 0.09437 | 0.102 | EQUIVALENT | EQUIVALENT |
| common | defo | 1 | lgbm | 42 | -5.025e-05 | 2.028e-05 | [-9e-05, -1.051e-05] | [-9.12e-05, -9.301e-06] | 0.0132 | 0.01741 | EQUIVALENT | EQUIVALENT |
| common | defo | 1 | lgbm_tweedie | 42 | +0.0007879 | 0.0001201 | [+0.0005526, +0.001023] | [+0.0005454, +0.00103] | 5.298e-11 | 6.864e-08 | HELPS | HELPS |
| human | defo | 0 | vt0007_shipped | 42 | +0.002989 | 0.0005157 | [+0.001978, +0.004] | [+0.001947, +0.004031] | 6.809e-09 | 8.449e-07 | HELPS | HELPS |
| human | defo | 0 | vt0007_cal | 42 | +0.002989 | 0.0005157 | [+0.001978, +0.004] | [+0.001947, +0.004031] | 6.809e-09 | 8.449e-07 | HELPS | HELPS |
| human | defo | 0 | vt0007_frozen2019 | 42 | +0.002989 | 0.0005157 | [+0.001978, +0.004] | [+0.001947, +0.004031] | 6.809e-09 | 8.449e-07 | HELPS | HELPS |
| human | defo | 1 | vt0007_shipped | 42 | +0.002997 | 0.0005171 | [+0.001984, +0.004011] | [+0.001953, +0.004041] | 6.782e-09 | 8.431e-07 | HELPS | HELPS |
| human | defo | 1 | vt0007_cal | 42 | +0.002997 | 0.0005171 | [+0.001984, +0.004011] | [+0.001953, +0.004041] | 6.782e-09 | 8.431e-07 | HELPS | HELPS |
| human | defo | 1 | vt0007_frozen2019 | 42 | +0.002997 | 0.0005171 | [+0.001984, +0.004011] | [+0.001953, +0.004041] | 6.782e-09 | 8.431e-07 | HELPS | HELPS |
| own | coral | 0 | ours | 37 | +5.207 | 1.65 | [+1.972, +8.441] | [+1.86, +8.554] | 0.001605 | 0.003235 | HELPS | HELPS |
| own | coral | 183 | ours | 37 | +1.747 | 0.8289 | [+0.1224, +3.372] | [+0.06599, +3.428] | 0.03506 | 0.04209 | HELPS | HELPS |
| own | coral | 365 | ours | 37 | +0 | 0 | [+0, +0] | [n/a, n/a] | n/a | n/a | declined | declined |
| common | coral | 0 | ridge | 37 | +1.124 | 1.342 | [-1.507, +3.755] | [-1.598, +3.847] | 0.4023 | 0.4078 | CANNOT TELL | CANNOT TELL |
| common | coral | 0 | rf | 37 | -0.1607 | 1.144 | [-2.403, +2.082] | [-2.481, +2.16] | 0.8883 | 0.889 | CANNOT TELL | CANNOT TELL |
| common | coral | 0 | lgbm | 37 | -0.4229 | 1.198 | [-2.77, +1.924] | [-2.852, +2.006] | 0.724 | 0.7261 | CANNOT TELL | CANNOT TELL |
| common | coral | 0 | lgbm_tweedie | 37 | +0.726 | 0.7453 | [-0.7348, +2.187] | [-0.7856, +2.238] | 0.33 | 0.3365 | CANNOT TELL | CANNOT TELL |
| common | coral | 0 | hgb_l1 | 37 | -2.3 | 0.9751 | [-4.212, -0.389] | [-4.278, -0.3226] | 0.01833 | 0.02387 | HURTS | HURTS |
| common | coral | 183 | ridge | 37 | +1.281 | 0.7456 | [-0.1801, +2.743] | [-0.2309, +2.793] | 0.08573 | 0.09432 | CANNOT TELL | CANNOT TELL |
| common | coral | 183 | rf | 37 | +0.4491 | 0.8367 | [-1.191, +2.089] | [-1.248, +2.146] | 0.5915 | 0.5948 | CANNOT TELL | CANNOT TELL |
| common | coral | 183 | lgbm | 37 | +0.6333 | 0.7351 | [-0.8076, +2.074] | [-0.8576, +2.124] | 0.389 | 0.3947 | CANNOT TELL | CANNOT TELL |
| common | coral | 183 | lgbm_tweedie | 37 | +0.6674 | 0.7063 | [-0.7169, +2.052] | [-0.765, +2.1] | 0.3447 | 0.351 | CANNOT TELL | CANNOT TELL |
| common | coral | 183 | hgb_l1 | 37 | +1.075 | 0.7727 | [-0.4392, +2.59] | [-0.4918, +2.642] | 0.1641 | 0.1726 | CANNOT TELL | CANNOT TELL |
| common | coral | 365 | ridge | 37 | -0.4615 | 0.2406 | [-0.933, +0.01008] | [-0.9494, +0.02646] | 0.0551 | 0.06306 | CANNOT TELL | CANNOT TELL |
| common | coral | 365 | rf | 37 | -1.008 | 0.681 | [-2.343, +0.3262] | [-2.389, +0.3726] | 0.1386 | 0.1473 | CANNOT TELL | CANNOT TELL |
| common | coral | 365 | lgbm | 37 | -0.6889 | 0.4921 | [-1.653, +0.2757] | [-1.687, +0.3092] | 0.1616 | 0.1701 | CANNOT TELL | CANNOT TELL |
| common | coral | 365 | lgbm_tweedie | 37 | -0.5508 | 0.2793 | [-1.098, -0.003464] | [-1.117, +0.01555] | 0.04856 | 0.05628 | CANNOT TELL | CANNOT TELL |
| common | coral | 365 | hgb_l1 | 37 | -0.7445 | 0.5601 | [-1.842, +0.3534] | [-1.881, +0.3915] | 0.1838 | 0.1922 | CANNOT TELL | CANNOT TELL |
| human | coral | 0 | crw_dhw | 32 | +1.27 | 1.3 | [-1.278, +3.819] | [-1.382, +3.923] | 0.3286 | 0.3361 | CANNOT TELL | CANNOT TELL |
| human | coral | 183 | crw_dhw | 32 | +1.85 | 0.943 | [+0.001912, +3.698] | [-0.07307, +3.773] | 0.04976 | 0.05879 | HELPS | CANNOT TELL (CHANGES) |
| human | coral | 365 | crw_dhw | 32 | +0 | 0 | [+0, +0] | [n/a, n/a] | n/a | n/a | IDENTICAL | IDENTICAL |

### Fact-sheet comparison

| check | fact sheet / probe states | agreed value | status |
|---|---|---|---|
| fire t39 | 2.023 | 2.0226909200367604 | MATCHES |
| fire t lower bound | -1.2e-06 | -1.2027743388921396e-06 | MATCHES |
| fire p_t | 0.056 | 0.05635456901611458 | MATCHES |
| fire z lower bound | +1.46e-07 | 1.4553254714064234e-07 | MATCHES |
| fire p_z | 0.049 | 0.04921011488404211 | MATCHES |
| fire p_z (probe) | 0.04921 | 0.04921011488404211 | MATCHES |
| fire p_t (probe) | 0.05635 | 0.05635456901611458 | MATCHES |
| fire HELPS -> CANNOT TELL | helps -> cannot_tell | ["helps", "cannot_tell"] | MATCHES |
| coral CRW 183 d, 32 groups | crw_dhw, G 32 | ["crw_dhw", 32] | MATCHES |
| coral CRW t31 low | -0.073 | -0.07306569416067066 | MATCHES |
| coral CRW t31 high | 3.773 | 3.773275681001868 | MATCHES |
| coral CRW p_z (probe) | 0.04976 | 0.04975926843790467 | MATCHES |
| coral CRW p_t (probe) | 0.05879 | 0.05879090741773607 | MATCHES |
| coral CRW BEATS -> CANNOT TELL | helps -> cannot_tell | ["helps", "cannot_tell"] | MATCHES |
| every other deciding verdict unchanged (exactly 2 change) | 2 | 2 | MATCHES |
| Holm z: all five survive, fire last | all survive | {"pm25": 1.2496245932051381e-08, "ndvi": 1.3825434560019997e-39, "fire": 0.04921011488404211, "defo": 0.01115614943217776, "coral": 0.004813605965843142} | MATCHES |
| Holm t: fire fails, others survive | fire fails | {"pm25": 1.1165386121103335e-07, "ndvi": 2.100409578207426e-25, "fire": 0.05635456901611458, "defo": 0.0166988973828065, "coral": 0.009704291770623541} | MATCHES |
| pm25 band share % | 1.20 | 1.199324190760551 | MATCHES |
| pm25 band share % (probe) | 1.1993 | 1.199324190760551 | MATCHES |
| ndvi band share % | 1.52 | 1.515880257250493 | MATCHES |
| ndvi band share % (probe) | 1.5159 | 1.515880257250493 | MATCHES |
| fire band share % | 0.31 | 0.30637224549723635 | MATCHES |
| fire band share % (probe) | 0.3064 | 0.30637224549723635 | MATCHES |
| defo band share % | 1.93 | 1.9327591344563166 | MATCHES |
| defo band share % (probe) | 1.9328 | 1.9327591344563166 | MATCHES |
| coral band share % | 11.06 | 11.062250590138705 | MATCHES |
| coral band share % (probe) | 11.0623 | 11.062250590138705 | MATCHES |
| 'About 80 verdicts' | about 80 | exactly 79 deciding rows (14 own + 53 common + 12 human); say 79 | MATCHES |
| count of deciding rows (probe) | 79 | 79 | MATCHES |
| fire blocked jk mean | 4.078e-05 | 4.078372506086034e-05 | MATCHES |
| fire blocked jk se | 2.187e-05 | 2.1871002568701678e-05 | MATCHES |
| fire blocked jk low | -2.08e-06 | -2.083439973794946e-06 | MATCHES |
| fire blocked jk high | 8.37e-05 | 8.365089009551563e-05 | MATCHES |
| fire blocked jk blocks | 39 | 39 | MATCHES |

### Inputs

| file | sha256 prefix (re-hashed now) | in spec list | read by | matches spec/A/B prefixes |
|---|---|---|---|---|
| D:/treeroute/rivals/coral/20261020_f3b8e3da/board_lead_0.csv | 3220b5c8967f0570 | yes | AB | yes |
| D:/treeroute/rivals/coral/20261020_f3b8e3da/board_lead_183.csv | 1cba4ab97d3197a0 | yes | AB | yes |
| D:/treeroute/rivals/coral/20261020_f3b8e3da/board_lead_365.csv | 393d7ff606d7b76e | yes | AB | yes |
| D:/treeroute/rivals/defo/20261017_d71c61f4/board_lead_0.csv | 0ca58e02d963f54e | yes | AB | yes |
| D:/treeroute/rivals/defo/20261017_d71c61f4/board_lead_1.csv | 6e9086b1decc531d | yes | AB | yes |
| D:/treeroute/rivals/fire/20261017_869d1f38/board_lead_0.csv | 031a261083ce6964 | yes | AB | yes |
| D:/treeroute/rivals/fire/20261017_869d1f38/board_lead_12.csv | 02236b90973a9c87 | yes | AB | yes |
| D:/treeroute/rivals/fire/20261017_869d1f38/board_lead_6.csv | b9d7636d26f8ad71 | yes | AB | yes |
| D:/treeroute/rivals/ndvi/20261016_d1de3158/board_lead_0.csv | b8208282f1c27ccc | yes | AB | yes |
| D:/treeroute/rivals/ndvi/20261016_d1de3158/board_lead_12.csv | 972572216dcbf949 | yes | AB | yes |
| D:/treeroute/rivals/ndvi/20261016_d1de3158/board_lead_6.csv | 0d48164188f8dfe5 | yes | AB | yes |
| D:/treeroute/rivals/pm25/20261007_74e67609/board_lead_0.csv | 4b2b7550b77ebe78 | yes | AB | yes |
| D:/treeroute/rivals/pm25/20261007_74e67609/board_lead_12.csv | 37abd537cd3e0f69 | yes | AB | yes |
| D:/treeroute/rivals/pm25/20261007_74e67609/board_lead_6.csv | 1b88a644d9110a3e | yes | AB | yes |
| D:/treeroute/rivals_human/coral/20261020_f3b8e3da/human_board_lead_0.csv | 8fa769680440d5e5 | yes | AB | yes |
| D:/treeroute/rivals_human/coral/20261020_f3b8e3da/human_board_lead_183.csv | 7b57584131254f9c | yes | AB | yes |
| D:/treeroute/rivals_human/coral/20261020_f3b8e3da/human_board_lead_365.csv | 7e7e8602d6a216f3 | yes | AB | yes |
| D:/treeroute/rivals_human/defo/20261017_d71c61f4/human_board_lead_0.csv | b912d3b3c726a7cc | yes | AB | yes |
| D:/treeroute/rivals_human/defo/20261017_d71c61f4/human_board_lead_1.csv | fc9dd957167b9b3d | yes | AB | yes |
| D:/treeroute/rivals_human/ndvi/20261016_d1de3158/human_board_lead_0.csv | 50db5b3db4a694c8 | yes | AB | yes |
| D:/treeroute/rivals_human/ndvi/20261016_d1de3158/human_board_lead_12.csv | ce304d4cdf002620 | yes | AB | yes |
| D:/treeroute/rivals_human/ndvi/20261016_d1de3158/human_board_lead_6.csv | 18ba49e839e9a178 | yes | AB | yes |
| D:/treeroute/rivals_human/pm25/20261007_74e67609/human_board_lead_0.csv | e8d72653cfc47bb1 | yes | AB | yes |
| D:/treeroute/rivals_human/pm25/20261007_74e67609/human_board_lead_12.csv | a097e9b97b33810e | yes | AB | yes |
| D:/treeroute/rivals_human/pm25/20261007_74e67609/human_board_lead_6.csv | 2281408c408f5fd8 | yes | AB | yes |
| D:/treeroute/rivals_table/20261025T162302876402Z/RIVALS_TABLE.csv | 1ccac0e7eb9defc0 | yes | AB | yes |
| D:/treeroute/runs/_headline_tables/coral/headline_344838cf7de1.csv | 344838cf7de1df55 | yes | AB | yes |
| D:/treeroute/runs/_headline_tables/coral/verdicts_a9d948cbf26b.csv | a9d948cbf26be365 | yes | AB | yes |
| D:/treeroute/runs/_headline_tables/defo/headline_1571da960aa6.csv | 1571da960aa6540e | yes | AB | yes |
| D:/treeroute/runs/_headline_tables/defo/verdicts_bf99c6741bce.csv | bf99c6741bcee256 | yes | AB | yes |
| D:/treeroute/runs/_headline_tables/fire/headline_85a9134089e4.csv | 85a9134089e47a61 | yes | AB | yes |
| D:/treeroute/runs/_headline_tables/fire/verdicts_7ee7167afe8d.csv | 7ee7167afe8d7a52 | yes | AB | yes |
| D:/treeroute/runs/_headline_tables/headline_93b64854d1f9.csv | 93b64854d1f9c6bf | yes | AB | yes |
| D:/treeroute/runs/_headline_tables/ndvi/headline_9e5590eab94b.csv | 9e5590eab94b7373 | yes | AB | yes |
| D:/treeroute/runs/_headline_tables/ndvi/verdicts_c4cd7e7c2610.csv | c4cd7e7c2610e218 | yes | AB | yes |
| D:/treeroute/runs/_headline_tables/verdicts_9abcea419ce2.csv | 9abcea419ce2fe63 | yes | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/jackknife.csv | b8557782d9cdd703 | yes | AB | yes |

Scripts: posthoc_A.py sha256 0cee249c0834dc2bbf0fe9ec458b200e20e096a4c5fc24e8d585a09584bab7c0; posthoc_B.py sha256 6b781c848bd84391da3bb71975135ebdcd806150ec45911d18e2c3f3f0db58ff; reconcile_AB.py sha256 5dcbe687b730c77f6207236bfa674d9a7a473b402e89a6c74b3487c7273b4c58.

## R3b

**What.** Model against the best naive baseline at the nowcast, for all five problems (only the fire cell is provisional; the other four rows are recomputed as a check).

**Population.** Lead 0 labelled rows: pm25 91,428 / 127 groups; ndvi 94,527 / 133; fire 94,702 / 40; defo 369,096 / 42; coral 2,312 / 37.

**Formula in words.** Nowcast: pooled MAE of the adopted column against the lowest-MAE naive baseline (guess-normal, last-5 normal, predict-zero, each link's trees-off; coral: donor median and predict-zero), as a percentage change.

<details><summary>Spec formula (verbatim)</summary>

Model = the adopted arm column (verdict.json 'adopted'). Candidate baselines: base__guess_normal, base__last5_normal, base__predict_zero and arm__<link>_trees_off_unweighted for every link of the run (the geometric normal on log links); coral: base__donor_median and base__predict_zero only (its trees-off is a neighbour-pool regression, not a naive baseline, R3b note). best = the candidate with the lowest pooled MAE over labelled rows; change% = 100*(MAE_model - MAE_best)/MAE_best; for fire also change% vs base__predict_zero. MAEs checked against score_pooled.csv.

</details>

**Engine definitions cited.** C:/Users/moh the ghost/Desktop/data set for reserch paper/engine/treeroute/report/metrics.py baseline_guess_normal() 348, baseline_last5_normal() 402, baseline_predict_zero() 336, baseline_donor_median() 558, mae() 569; route/kinds.py trees-off (R16); route/neighbour.py trees_off_neighbour (why coral trees-off is excluded).

**A/B agreement: AGREE.** 59 leaves compared (10 integers, 39 floats bit-identical, 0 at printed precision), 0 disagreements. A checks 94 (failed 0); B checks 107 (failed 0). Leaves only one side reports: A 0, B 0 (extra detail, not disagreements).

### Agreed values

| run | model (adopted) | MAE | best naive | MAE | change | all candidates (ascending) |
|---|---|---|---|---|---|---|
| pm25 | log_c_corrector_unweighted | 3.588091134 | log_c_trees_off_unweighted | 3.853165559 | -6.879% | log_c_trees_off_unweighted 3.8531656; last5_normal 3.9719509; identity_trees_off_unweighted 4.0316106; guess_normal 4.0316106; predict_zero 17.518826 |
| ndvi | identity_plain_unweighted | 0.03146059686 | last5_normal | 0.03933500299 | -20.019% | last5_normal 0.039335003; identity_trees_off_unweighted 0.039414114; guess_normal 0.039414114; predict_zero 0.43647997 |
| fire | arcsine_corrector_gls | 0.004385064558 | log_c_trees_off_unweighted | 0.004281302313 | +2.424% (vs predict-zero +2.356%) | log_c_trees_off_unweighted 0.0042813023; predict_zero 0.0042841146; arcsine_trees_off_unweighted 0.0044282636; last5_normal 0.0058731946; guess_normal 0.0062587579; identity_trees_off_unweighted 0.006258758 |
| defo | log_c_corrector_unweighted | 0.005415798422 | log_c_trees_off_unweighted | 0.00571459748 | -5.229% | log_c_trees_off_unweighted 0.0057145975; predict_zero 0.0061202728; arcsine_trees_off_unweighted 0.0062470592; guess_normal 0.0084048573; identity_trees_off_unweighted 0.0084048573; last5_normal 0.0086645548 |
| coral | arcsine_corrector_gls | 6.697989245 | predict_zero | 8.099835075 | -17.307% | predict_zero 8.0998351; donor_median 8.2944984 |

### Fact-sheet comparison

| check | fact sheet / probe states | agreed value | status |
|---|---|---|---|
| fire model | 0.004385 | 0.004385064558301006 | MATCHES |
| fire log TO | 0.004281 | 0.004281302312816825 | MATCHES |
| fire best naive is log trees-off | arm__log_c_trees_off_unweighted | arm__log_c_trees_off_unweighted | MATCHES |
| fire PZ | 0.004284 | 0.004284114619241937 | MATCHES |
| fire change % vs best | +2.4 | 2.4236140758747786 | MATCHES |
| fire change % vs PZ | +2.4 | 2.3563781091583493 | MATCHES |
| fire change % vs best (expected) | +2.424 | 2.4236140758747786 | MATCHES |
| fire change % vs PZ (expected) | +2.356 | 2.3563781091583493 | MATCHES |
| pm25 model | 3.588 | 3.588091134093021 | MATCHES |
| pm25 best naive | 3.853 | 3.85316555881606 | MATCHES |
| pm25 best naive column | arm__log_c_trees_off_unweighted | arm__log_c_trees_off_unweighted | MATCHES |
| pm25 change % | -6.9 | -6.879393596689541 | MATCHES |
| pm25 change % (expected) | -6.88 | -6.879393596689541 | MATCHES |
| ndvi model | 0.03146 | 0.03146059686292064 | MATCHES |
| ndvi best naive | 0.03934 | 0.03933500299284565 | MATCHES |
| ndvi best naive column | base__last5_normal | base__last5_normal | MATCHES |
| ndvi change % | -20.0 | -20.018826822911965 | MATCHES |
| ndvi change % (expected) | -20.02 | -20.018826822911965 | MATCHES |
| defo model | 0.005416 | 0.005415798421978487 | MATCHES |
| defo best naive | 0.005715 | 0.005714597480035355 | MATCHES |
| defo best naive column | arm__log_c_trees_off_unweighted | arm__log_c_trees_off_unweighted | MATCHES |
| defo change % | -5.2 | -5.228698243415378 | MATCHES |
| defo change % (expected) | -5.23 | -5.228698243415378 | MATCHES |
| coral model | 6.698 | 6.69798924506233 | MATCHES |
| coral best naive | 8.100 | 8.099835075446945 | MATCHES |
| coral best naive column | base__predict_zero | base__predict_zero | MATCHES |
| coral change % | -17.3 | -17.307091037372288 | MATCHES |
| coral change % (expected) | -17.31 | -17.307091037372288 | MATCHES |

### Inputs

| file | sha256 prefix (re-hashed now) | in spec list | read by | matches spec/A/B prefixes |
|---|---|---|---|---|
| D:/treeroute/runs/_headline_tables/coral/headline_344838cf7de1.csv | 344838cf7de1df55 | yes | AB | yes |
| D:/treeroute/runs/_headline_tables/defo/headline_1571da960aa6.csv | 1571da960aa6540e | yes | AB | yes |
| D:/treeroute/runs/_headline_tables/fire/headline_85a9134089e4.csv | 85a9134089e47a61 | yes | AB | yes |
| D:/treeroute/runs/_headline_tables/headline_93b64854d1f9.csv | 93b64854d1f9c6bf | yes | AB | yes |
| D:/treeroute/runs/_headline_tables/ndvi/headline_9e5590eab94b.csv | 9e5590eab94b7373 | yes | AB | yes |
| D:/treeroute/runs/coral/headline/20261020_f3b8e3da/score_pooled.csv | bbaa21aa184a1054 | yes | AB | yes |
| D:/treeroute/runs/coral/headline/20261020_f3b8e3da/test_preds.parquet | dd07762558023d5f | yes | A | yes |
| D:/treeroute/runs/coral/headline/20261020_f3b8e3da/verdict.json | 6bf9b04970173323 | no (extra) | AB | yes |
| D:/treeroute/runs/defo/headline/20261017_d71c61f4/score_pooled.csv | 8f1c161ad318e32c | yes | AB | yes |
| D:/treeroute/runs/defo/headline/20261017_d71c61f4/test_preds.parquet | 3a002e9a9deb006a | yes | A | yes |
| D:/treeroute/runs/defo/headline/20261017_d71c61f4/verdict.json | 34d090aae96fed3c | no (extra) | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/score_pooled.csv | 9236a25380d9aede | yes | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/test_preds.parquet | 86e9c97a58a9b714 | yes | A | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/verdict.json | 6c744bc1a0647e37 | no (extra) | AB | yes |
| D:/treeroute/runs/ndvi/headline/20261016_d1de3158/score_pooled.csv | 3a7e09b6156e4449 | yes | AB | yes |
| D:/treeroute/runs/ndvi/headline/20261016_d1de3158/test_preds.parquet | 87c0b1414af7e370 | yes | A | yes |
| D:/treeroute/runs/ndvi/headline/20261016_d1de3158/verdict.json | 535ef992b5057ed7 | no (extra) | AB | yes |
| D:/treeroute/runs/pm25/headline/20261007_74e67609/score_pooled.csv | 8a7d2f44f00a9e7c | yes | AB | yes |
| D:/treeroute/runs/pm25/headline/20261007_74e67609/test_preds.parquet | 9e62fe4256c08c50 | yes | A | yes |
| D:/treeroute/runs/pm25/headline/20261007_74e67609/verdict.json | af031ef5a44dbe67 | no (extra) | AB | yes |

Scripts: posthoc_A.py sha256 0cee249c0834dc2bbf0fe9ec458b200e20e096a4c5fc24e8d585a09584bab7c0; posthoc_B.py sha256 6b781c848bd84391da3bb71975135ebdcd806150ec45911d18e2c3f3f0db58ff; reconcile_AB.py sha256 5dcbe687b730c77f6207236bfa674d9a7a473b402e89a6c74b3487c7273b4c58.

## RC12

**What.** Coral nowcast by target magnitude: ours (adopted arcsine corrector GLS) against every common rival, with hgb_l1 (the L1 booster that beats us pooled) in focus, plus predict-zero and the donor median. Outcome-defined strata: report-only, post hoc, shown together.

**Population.** Coral lead 0, all 2,312 test visits (37 scored groups, 2016-2019). Strata: (a) the engine report's own magnitude bins with the lead-0 edges of positive donor labels (pos_q25 1.91619047625, pos_q50 7.255, pos_q75 23.9575; 11,338 donor rows): B0 y = 0 (1,288 visits, 26 groups), B1 (0, q25] (278, 23), B2 (q25, q50] (262), B3 (q50, q75] (245), B4 > q75 (239); (b) severe y >= 50 (140 visits; the D54/Part 605 stratum). y > 0 as a whole is item A2.

**Formula in words.** Coral nowcast split by the observed value (engine magnitude bins and y >= 50): per stratum, rows, regions, mean y, mean prediction and MAE of ours, the five rivals, predict-zero and donor median; per-region contrast rival minus ours over the regions present in the stratum, region jackknife, band tag.

<details><summary>Spec formula (verbatim)</summary>

Join each rival's preds_<L>.parquet on (unit, time, lead) one-to-one (2,312 rows). Bin: B0 if y == 0, else searchsorted([q25, q50, q75], y, side='left') -> B1..B4 (right-closed), exactly coral_report.py magnitude_bin. Per stratum and column (ours, arm__rival_<L> for the 5 learners, base__predict_zero, base__donor_median): n, n_groups, mean y, mean prediction, MAE. Check ours per bin against magnitude_bins.csv (lead 0, stratum_value ALL, column arm__arcsine_corrector_gls; rtol 1e-12). Report-only per-group contrast in each stratum: d_g = MAE_rival(g) - MAE_ours(g) over the groups with at least one row in the stratum, group jackknife 1.96, tag with the coral band 0.9175581931 (G < 3 -> cannot tell).

</details>

**Engine definitions cited.** D:/treeroute/coral_build/report_scripts/coral_report.py magnitude_edges() 498-529 and magnitude_bin() 531-541 (the B0-B4 bins of the frozen coral report); C:/Users/moh the ghost/Desktop/data set for reserch paper/engine/treeroute/report/metrics.py mae() 569, group_jackknife() 1032, contrast_tag() 1097; rival harness D:/treeroute/rivals_build/rivals/harness.py _frame_for_scoring() 2363-2388 (join, guarded/raw columns) and score() 2494-2513 (d = rival - ours).

**A/B agreement: AGREE.** 481 leaves compared (113 integers, 319 floats bit-identical, 0 at printed precision), 0 disagreements. A checks 111 (failed 0); B checks 117 (failed 0). Leaves only one side reports: A 0, B 0 (extra detail, not disagreements).

### Agreed values

Edges (lead 0, positive donor labels, 11,338 donor rows): q25 1.91619047625, q50 7.255, q75 23.9575. Band 0.9175581931.

| stratum | visits | regions | mean y | MAE ours | MAE hgb_l1 | mean pred ours | mean pred hgb_l1 | d = hgb_l1 - ours [CI] | tag | regions ours better | MAE ridge / rf / lgbm / tweedie / PZ / DM |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL | 2,312 | 37 | 8.0998 | 6.69799 | 6.35556 | 4.3026 | 6.2059 | -2.3 [-4.212, -0.389] | HURTS | 19/37 | 7.1983 / 7.3762 / 7.1464 / 7.255 / 8.0998 / 8.2945 |
| B0 zero | 1,288 | 26 | 0 | 1.39345 | 2.11626 | 1.3935 | 2.1163 | +1.222 [-0.9704, +3.415] | CANNOT TELL | 16/26 | 1.411 / 3.0109 / 2.728 / 2.1967 / 0 / 1 |
| B1 (0, q25] | 278 | 23 | 0.78483 | 2.24793 | 2.48862 | 2.5517 | 2.7935 | +1.014 [-1.559, +3.587] | CANNOT TELL | 12/23 | 1.4343 / 3.3097 / 2.8248 / 2.2966 / 0.78483 / 0.45411 |
| B2 (q25, q50] | 262 | 27 | 4.1741 | 4.57146 | 5.76884 | 5.0182 | 5.9191 | +1.487 [-1.272, +4.245] | CANNOT TELL | 16/27 | 4.1954 / 5.8869 / 5.0068 / 3.9849 / 4.1741 / 3.1741 |
| B3 (q50, q75] | 245 | 24 | 14.123 | 8.39552 | 9.46924 | 7.6782 | 9.3873 | +1.505 [-1.245, +4.255] | CANNOT TELL | 15/24 | 10.561 / 8.3601 / 8.294 / 8.5675 / 14.123 / 13.123 |
| B4 (q75, max] | 239 | 26 | 58.389 | 41.052 | 31.1509 | 17.772 | 29.268 | -6.161 [-9.488, -2.835] | HURTS | 4/26 | 44.936 / 36.255 / 37.154 / 42.521 / 58.389 / 57.389 |
| severe y>=50 | 140 | 18 | 74.64 | 53.1251 | 38.6597 | 21.515 | 36.33 | -11.24 [-16.22, -6.267] | HURTS | 2/18 | 54.668 / 46.937 / 46.937 / 54.242 / 74.64 / 73.64 |

Other contrasts that are not CANNOT TELL (d = MAE_column - MAE_ours; positive = ours better):

| stratum | column | mean d | 95% CI | tag | regions ours better |
|---|---|---|---|---|---|
| ALL | predict_zero | +5.356 | [+1.972, +8.739] | HELPS | 20/37 |
| ALL | donor_median | +5.207 | [+1.972, +8.441] | HELPS | 23/37 |
| B0 zero | rf | +2.099 | [+0.6705, +3.527] | HELPS | 22/26 |
| B0 zero | lgbm | +1.229 | [+0.4751, +1.982] | HELPS | 21/26 |
| B0 zero | predict_zero | -2.113 | [-3.011, -1.215] | HURTS | 0/26 |
| B0 zero | donor_median | -1.113 | [-2.011, -0.2147] | HURTS | 9/26 |
| B1 (0, q25] | predict_zero | -2.081 | [-3.355, -0.8068] | HURTS | 6/23 |
| B1 (0, q25] | donor_median | -2.439 | [-3.733, -1.146] | HURTS | 1/23 |
| B2 (q25, q50] | donor_median | -2.131 | [-4.121, -0.1409] | HURTS | 8/27 |
| B3 (q50, q75] | lgbm_tweedie | -1.593 | [-2.945, -0.2417] | HURTS | 6/24 |
| B3 (q50, q75] | predict_zero | +4.107 | [+2.785, +5.43] | HELPS | 23/24 |
| B3 (q50, q75] | donor_median | +3.107 | [+1.785, +4.43] | HELPS | 20/24 |
| B4 (q75, max] | rf | -3.931 | [-7.854, -0.008208] | HURTS | 9/26 |
| B4 (q75, max] | predict_zero | +12.2 | [+7.859, +16.55] | HELPS | 26/26 |
| B4 (q75, max] | donor_median | +11.2 | [+6.859, +15.55] | HELPS | 23/26 |
| severe y>=50 | predict_zero | +17.69 | [+11.04, +24.35] | HELPS | 17/18 |
| severe y>=50 | donor_median | +16.69 | [+10.04, +23.35] | HELPS | 17/18 |

Probe cuts of the fact sheet, single implementation C (reconcile_AB.py; NOT A/B-reconciled): (0,10] 607 visits / 29 regions: ours 3.7088 vs hgb_l1 4.4140; (10,50] 282 visits / 26 regions: ours 14.9409 vs hgb_l1 14.3491; (50,inf) 135 visits / 17 regions: ours 53.5288 vs hgb_l1 38.8340.

### Fact-sheet comparison

| check | fact sheet / probe states | agreed value | status |
|---|---|---|---|
| B0 ours (notes) | 1.39 | 1.393452691424863 | MATCHES |
| B0 hgb_l1 (notes) | 2.12 | 2.116261113427335 | MATCHES |
| severe hgb_l1 (notes) | 38.7 | 38.65970596667031 | MATCHES |
| severe ours (notes) | 53.1 | 53.12512328455528 | MATCHES |
| 'L1 wins on every bleached stratum' | true on every bleached stratum | {"B1 (0, q25]": "ours lower", "B2 (q25, q50]": "ours lower", "B3 (q50, q75]": "ours lower", "B4 (q75, max]": "hgb_l1 lower", "severe y>=50": "hgb_l1 lower"} | DIFFERS |
| B0 zero ours (probe) | 1.393 | 1.393452691424863 | MATCHES |
| B0 zero hgb_l1 (probe) | 2.116 | 2.116261113427335 | MATCHES |
| B1 (0, q25] ours (probe) | 2.248 | 2.2479349965741373 | MATCHES |
| B1 (0, q25] hgb_l1 (probe) | 2.489 | 2.4886164280167926 | MATCHES |
| B2 (q25, q50] ours (probe) | 4.571 | 4.57145862012016 | MATCHES |
| B2 (q25, q50] hgb_l1 (probe) | 5.769 | 5.768837019101032 | MATCHES |
| B3 (q50, q75] ours (probe) | 8.396 | 8.3955187028941 | MATCHES |
| B3 (q50, q75] hgb_l1 (probe) | 9.469 | 9.469240682614936 | MATCHES |
| B4 (q75, max] ours (probe) | 41.052 | 41.05202467908258 | MATCHES |
| B4 (q75, max] hgb_l1 (probe) | 31.151 | 31.15090832749444 | MATCHES |
| severe y>=50 ours (probe) | 53.125 | 53.12512328455528 | MATCHES |
| severe y>=50 hgb_l1 (probe) | 38.660 | 38.65970596667031 | MATCHES |
| final ALL hgb_l1 | 6.356 | 6.35555624463641 | MATCHES |
| final ALL ours | 6.698 | 6.69798924506233 | MATCHES |
| final ALL d | -2.30 | -2.300318346129559 | MATCHES |
| final ALL low | -4.21 | -4.21159558455701 | MATCHES |
| final ALL high | -0.39 | -0.3890411077021081 | MATCHES |
| probe cut (0,10] ours (single implementation C, not A/B-reconciled) | 3.71 | 3.708836204588227 | MATCHES (C only) |
| probe cut (0,10] hgb_l1 (single implementation C, not A/B-reconciled) | 4.41 | 4.41396394936231 | MATCHES (C only) |

### Inputs

| file | sha256 prefix (re-hashed now) | in spec list | read by | matches spec/A/B prefixes |
|---|---|---|---|---|
| D:/treeroute/rivals/coral/20261020_f3b8e3da/board_lead_0.csv | 3220b5c8967f0570 | yes | AB | yes |
| D:/treeroute/rivals/coral/20261020_f3b8e3da/lead_0/preds_hgb_l1.parquet | 7039e548bf4ead04 | yes | AB | yes |
| D:/treeroute/rivals/coral/20261020_f3b8e3da/lead_0/preds_lgbm.parquet | 3e1d4b01737efbbf | yes | AB | yes |
| D:/treeroute/rivals/coral/20261020_f3b8e3da/lead_0/preds_lgbm_tweedie.parquet | 41f5fa63b5ebb276 | yes | AB | yes |
| D:/treeroute/rivals/coral/20261020_f3b8e3da/lead_0/preds_rf.parquet | 36830d55b5092fb7 | yes | AB | yes |
| D:/treeroute/rivals/coral/20261020_f3b8e3da/lead_0/preds_ridge.parquet | f84ad92e63f9855c | yes | AB | yes |
| D:/treeroute/runs/_headline_tables/coral/coral_report/magnitude_bins.csv | 6cafcee415a42ed0 | yes | AB | yes |
| D:/treeroute/runs/_headline_tables/coral/coral_report/magnitude_edges.csv | d6571f1f6d8f314d | yes | AB | yes |
| D:/treeroute/runs/coral/headline/20261020_f3b8e3da/test_preds.parquet | dd07762558023d5f | yes | AB | yes |
| D:/treeroute/runs/coral/headline/20261020_f3b8e3da/verdict.json | 6bf9b04970173323 | yes | AB | yes |

Scripts: posthoc_A.py sha256 0cee249c0834dc2bbf0fe9ec458b200e20e096a4c5fc24e8d585a09584bab7c0; posthoc_B.py sha256 6b781c848bd84391da3bb71975135ebdcd806150ec45911d18e2c3f3f0db58ff; reconcile_AB.py sha256 5dcbe687b730c77f6207236bfa674d9a7a473b402e89a6c74b3487c7273b4c58.

## A1

**What.** Fire active cells, stratified (owner MUST-INCLUDE; outcome-conditional, post hoc): ours vs LightGBM-Tweedie (the pooled-MAE winner), other common rivals and predict-zero beside, on the zero rows, the active rows (y > 0; final in the Part 606 addendum, recomputed as a check), the top 1% and the active rows below the top 1%. The provisional pieces are the top-1% numbers and the zero-row complement.

**Population.** Fire lead 0 labelled rows 94,702 (40 groups, 2019-2022). Strata: y == 0: 92,943 rows (98.14%); y > 0: 1,759 rows in 33 groups; top 1%: y >= q99 where q99 = numpy.quantile(y over the 94,702 labelled rows, 0.99, default linear) = 0.102941 (to 6 d.p.): 949 rows in 31 groups; 0 < y < q99: 810 rows. The q99 threshold comes from TEST labels.

**Formula in words.** Fire nowcast split by the observed value (zero, active, top 1% with q99 from the test labels, active below the top 1%): per stratum, MAE and mean prediction of ours, Tweedie and the other rivals; per-region contrast Tweedie minus ours, region jackknife, band tag.

<details><summary>Spec formula (verbatim)</summary>

Join each rival on (unit, time, lead). Per stratum: n, n_groups, mean y, mean prediction (ours, Tweedie, each rival), MAE (ours = arm__arcsine_corrector_gls; rivals = arm__rival_<L>, the deciding column; Tweedie's guard passed so guarded = raw; Ridge's guard failed so its guarded column is the normal and its raw column is shown beside), predict-zero MAE. Per-group contrast d_g = MAE_Tweedie(g) - MAE_ours(g) over the stratum's groups, group jackknife 1.96, groups where ours is better, tag with the fire band 1.356697052e-05 (report-only). Check: the all-rows pooled MAEs equal board_lead_0.csv rival_mae / ours_mae (rtol 1e-12).

</details>

**Engine definitions cited.** Rival harness D:/treeroute/rivals_build/rivals/harness.py _frame_for_scoring() 2363-2388 and score() 2494-2522 (metric_by_key per group, _paired_contrast(rival, ours), contrast_tag with the run band, timid rule); C:/Users/moh the ghost/Desktop/data set for reserch paper/engine/treeroute/report/metrics.py group_jackknife() 1032, contrast_tag() 1097, top10_detection() 700 (the engine's own outcome-defined event rule, NOT used here: the top 1% is a different, post-hoc cut).

**A/B agreement: AGREE.** 305 leaves compared (71 integers, 203 floats bit-identical, 0 at printed precision), 0 disagreements. A checks 64 (failed 0); B checks 28 (failed 0). Leaves only one side reports: A 0, B 0 (extra detail, not disagreements).

### Agreed values

q99 = numpy.quantile(test y, 0.99) = 0.10294117647058823 (from TEST labels); strict y > q99 gives 938 rows. Band 1.356697052e-05. Guard passed: ridge False, rf True, lgbm True, lgbm_tweedie True.

| stratum | rows | regions | mean y | MAE ours | MAE Tweedie | mean pred ours | mean pred Tweedie | d = Tweedie - ours [CI] | tag | regions ours better | MAE ridge (guarded) / ridge raw / rf / lgbm / PZ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL labelled | 94,702 | 40 | 0.0042841 | 0.00438506 | 0.00404267 | 0.0021831 | 0.0011401 | -0.0003412 [-0.0005845, -9.791e-05] | HURTS | 5/40 | 0.0062588 / 0.0042993 / 0.0042664 / 0.0042924 / 0.0042841 |
| y == 0 | 92,943 | 40 | 0 | 0.000851251 | 0.000320813 | 0.00085125 | 0.00032081 | -0.0005492 [-0.0008665, -0.0002319] | HURTS | 4/40 | 0.0029536 / 0.00065915 / 0.0006439 / 0.00067673 / 0 |
| y > 0 | 1,759 | 33 | 0.23065 | 0.191107 | 0.2007 | 0.072554 | 0.044429 | +0.004716 [+0.002371, +0.007062] | HELPS | 25/33 | 0.1809 / 0.19664 / 0.19568 / 0.19534 / 0.23065 |
| top 1% y >= q99 | 949 | 31 | 0.39127 | 0.308244 | 0.335002 | 0.097997 | 0.061828 | +0.01164 [+0.005674, +0.01761] | HELPS | 24/31 | 0.2811 / 0.32696 / 0.32471 / 0.32399 / 0.39127 |
| 0 < y < q99 | 810 | 29 | 0.042466 | 0.0538673 | 0.0433524 | 0.042745 | 0.024046 | -0.002375 [-0.005409, +0.0006584] | CANNOT TELL | 15/29 | 0.063505 / 0.043955 / 0.044498 / 0.04461 / 0.042466 |

Beside (report-only; d = MAE_column - MAE_ours):

| stratum | column | mean d | 95% CI | tag | regions ours better |
|---|---|---|---|---|---|
| ALL labelled | ridge | +0.001872 | [+0.0009265, +0.002817] | HELPS | 36/40 |
| ALL labelled | rf | -0.0001178 | [-0.0002496, +1.395e-05] | CANNOT TELL | 23/40 |
| ALL labelled | lgbm | -9.175e-05 | [-0.0002193, +3.58e-05] | CANNOT TELL | 24/40 |
| ALL labelled | ridge_raw | -8.491e-05 | [-0.0002151, +4.528e-05] | CANNOT TELL | 26/40 |
| ALL labelled | predict_zero | -0.0001035 | [-0.0006205, +0.0004134] | CANNOT TELL | 3/40 |
| y == 0 | ridge | +0.002171 | [+0.001059, +0.003283] | HELPS | 36/40 |
| y == 0 | rf | -0.0002167 | [-0.0003927, -4.068e-05] | HURTS | 21/40 |
| y == 0 | lgbm | -0.0001829 | [-0.0003512, -1.465e-05] | HURTS | 23/40 |
| y == 0 | ridge_raw | -0.000202 | [-0.000379, -2.496e-05] | HURTS | 25/40 |
| y == 0 | predict_zero | -0.0008933 | [-0.001415, -0.0003716] | HURTS | 0/40 |
| y > 0 | ridge | -0.008078 | [-0.01078, -0.005373] | HURTS | 0/33 |
| y > 0 | rf | +0.001988 | [+0.0007593, +0.003216] | HELPS | 17/33 |
| y > 0 | lgbm | +0.001862 | [+0.0007598, +0.002963] | HELPS | 18/33 |
| y > 0 | ridge_raw | +0.002305 | [+0.001116, +0.003494] | HELPS | 20/33 |
| y > 0 | predict_zero | +0.01233 | [+0.005625, +0.01904] | HELPS | 26/33 |
| top 1% y >= q99 | ridge | -0.01755 | [-0.02292, -0.01217] | HURTS | 1/31 |
| top 1% y >= q99 | rf | +0.007164 | [+0.003297, +0.01103] | HELPS | 19/31 |
| top 1% y >= q99 | lgbm | +0.00701 | [+0.003179, +0.01084] | HELPS | 19/31 |
| top 1% y >= q99 | ridge_raw | +0.007841 | [+0.003827, +0.01185] | HELPS | 19/31 |
| top 1% y >= q99 | predict_zero | +0.02672 | [+0.01134, +0.0421] | HELPS | 24/31 |
| 0 < y < q99 | ridge | +0.002721 | [-0.0005191, +0.00596] | CANNOT TELL | 11/29 |
| 0 < y < q99 | rf | -0.003524 | [-0.005764, -0.001284] | HURTS | 5/29 |
| 0 < y < q99 | lgbm | -0.003533 | [-0.005851, -0.001214] | HURTS | 6/29 |
| 0 < y < q99 | ridge_raw | -0.003619 | [-0.005948, -0.00129] | HURTS | 6/29 |
| 0 < y < q99 | predict_zero | -0.001737 | [-0.005275, +0.001801] | CANNOT TELL | 16/29 |

Ridge failed its guard: its guarded column equals arm__identity_trees_off_unweighted exactly (max |diff| 0) and differs from base__guess_normal by up to 8.09e-07 (the M34 gap).

### Fact-sheet comparison

| check | fact sheet / probe states | agreed value | status |
|---|---|---|---|
| y>0 rows | 1759 | 1759 | MATCHES |
| y>0 groups | 33 | 33 | MATCHES |
| y>0 ours | 0.191 | 0.1911066295793603 | MATCHES |
| y>0 Tweedie | 0.201 | 0.2007004068384659 | MATCHES |
| y>0 d | +0.0047 | 0.0047161915611460955 | MATCHES |
| y>0 low | +0.0024 | 0.0023708379552287986 | MATCHES |
| y>0 high | +0.0071 | 0.0070615451670633924 | MATCHES |
| y>0 groups ours better | 25 | 25 | MATCHES |
| y>0 ours (probe) | 0.191107 | 0.1911066295793603 | MATCHES |
| y>0 Tweedie (probe) | 0.200700 | 0.2007004068384659 | MATCHES |
| y>0 d (probe) | 0.0047162 | 0.0047161915611460955 | MATCHES |
| y>0 low (probe) | 0.0023708 | 0.0023708379552287986 | MATCHES |
| y>0 high (probe) | 0.0070615 | 0.0070615451670633924 | MATCHES |
| top1% rows | 949 | 949 | MATCHES |
| top1% groups (probe) | 31 | 31 | MATCHES |
| top1% ours | 0.308 | 0.3082444795154259 | MATCHES |
| top1% Tweedie | 0.335 | 0.3350016551784588 | MATCHES |
| top1% ours (probe) | 0.3082 | 0.3082444795154259 | MATCHES |
| top1% Tweedie (probe) | 0.3350 | 0.3350016551784588 | MATCHES |
| top1% mean pred ours | 0.098 | 0.09799716868713272 | MATCHES |
| top1% mean pred Tweedie | 0.062 | 0.06182752639505287 | MATCHES |
| top1% mean y | 0.391 | 0.39127151339823263 | MATCHES |
| top1% mean y (probe) | 0.3913 | 0.39127151339823263 | MATCHES |
| top1% strict > rows (probe) | 938 | 938 | MATCHES |
| q99 (6 dp) | 0.102941 | 0.10294117647058823 | MATCHES |
| zero rows | 92943 | 92943 | MATCHES |
| zero-row share % | 98.1 | 98.14259466537138 | MATCHES |
| zero-row share % (probe) | 98.14 | 98.14259466537138 | MATCHES |
| zero rows mean pred ours | 0.00085 | 0.0008512510072854029 | MATCHES |
| zero rows mean pred Tweedie | 0.00032 | 0.0003208125704800695 | MATCHES |
| zero rows mean pred ours (probe) | 0.000851 | 0.0008512510072854029 | MATCHES |
| zero rows mean pred Tweedie (probe) | 0.000321 | 0.0003208125704800695 | MATCHES |
| spec wording: Ridge guarded column 'is the normal' | guarded == guess-normal | guarded == arm__identity_trees_off_unweighted exactly; differs from base__guess_normal by up to 8.09e-07 | WORDING |

### Inputs

| file | sha256 prefix (re-hashed now) | in spec list | read by | matches spec/A/B prefixes |
|---|---|---|---|---|
| D:/treeroute/rivals/fire/20261017_869d1f38/board_lead_0.csv | 031a261083ce6964 | yes | AB | yes |
| D:/treeroute/rivals/fire/20261017_869d1f38/lead_0/preds_lgbm.parquet | 954ca794d932bac1 | yes | AB | yes |
| D:/treeroute/rivals/fire/20261017_869d1f38/lead_0/preds_lgbm_tweedie.parquet | 17979c68252cfd2d | yes | AB | yes |
| D:/treeroute/rivals/fire/20261017_869d1f38/lead_0/preds_rf.parquet | 7634c4a48a959eec | yes | AB | yes |
| D:/treeroute/rivals/fire/20261017_869d1f38/lead_0/preds_ridge.parquet | 83f991a07a8cd126 | yes | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/test_preds.parquet | 86e9c97a58a9b714 | yes | AB | yes |
| D:/treeroute/runs/fire/headline/20261017_869d1f38/verdict.json | 6c744bc1a0647e37 | yes | AB | yes |

Scripts: posthoc_A.py sha256 0cee249c0834dc2bbf0fe9ec458b200e20e096a4c5fc24e8d585a09584bab7c0; posthoc_B.py sha256 6b781c848bd84391da3bb71975135ebdcd806150ec45911d18e2c3f3f0db58ff; reconcile_AB.py sha256 5dcbe687b730c77f6207236bfa674d9a7a473b402e89a6c74b3487c7273b4c58.

## A2

**What.** Coral active (bleached, y > 0) surveys at the nowcast: ours against each of the five common rivals, pooled MAE and per-region paired contrasts (outcome-conditional, post hoc). The engine-v2 alarm numbers in PAPER_NOTES_RIVALS.md are out of scope (engine v2 replay, not v1 saved predictions).

**Population.** Coral lead 0 visits with y > 0: 1,024 of 2,312 (36 of the 37 scored groups), 2016-2019.

**Formula in words.** Coral nowcast visits with y > 0: pooled MAE and mean prediction of ours and each rival; per-region contrast rival minus ours over the 36 regions, region jackknife, band tag.

<details><summary>Spec formula (verbatim)</summary>

Join on (unit, time, lead); keep y > 0. Pooled MAE for ours, each arm__rival_<L> (all five passed their lead-0 guard, so guarded = raw; assert), predict-zero and donor median; mean y and mean predictions. Per rival: d_g = MAE_rival(g) - MAE_ours(g) over the 36 groups, group jackknife 1.96, groups where ours is better, tag with the coral band 0.9175581931 (report-only). Check: the all-rows pooled MAEs equal board_lead_0.csv rival_mae / ours_mae (rtol 1e-12).

</details>

**Engine definitions cited.** Rival harness D:/treeroute/rivals_build/rivals/harness.py _frame_for_scoring() 2363-2388, score() 2494-2522; C:/Users/moh the ghost/Desktop/data set for reserch paper/engine/treeroute/report/metrics.py mae() 569, group_jackknife() 1032, contrast_tag() 1097.

**A/B agreement: AGREE.** 70 leaves compared (16 integers, 46 floats bit-identical, 0 at printed precision), 0 disagreements. A checks 54 (failed 0); B checks 15 (failed 0). Leaves only one side reports: A 0, B 0 (extra detail, not disagreements).

### Agreed values

1024 visits with y > 0 in 36 regions; mean y 18.2879; band 0.9175581931. All five rivals passed their lead-0 guard (guarded == raw).

| column | MAE | mean pred | d = MAE_col - MAE_ours | 95% CI | tag | regions ours better |
|---|---|---|---|---|---|---|
| ours (arcsine corrector GLS) | 13.3701 | 7.9618 |  |  |  |  |
| hgb_l1 | 11.6878 | 11.35 | -1.896 | [-4.758, +0.9666] | CANNOT TELL | 17/36 |
| lgbm | 12.704 | 9.6064 | -0.7452 | [-3.298, +1.808] | CANNOT TELL | 18/36 |
| rf | 12.8669 | 10.365 | -0.7808 | [-3.156, +1.595] | CANNOT TELL | 19/36 |
| lgbm_tweedie | 13.6173 | 7.5175 | +0.3368 | [-1.232, +1.906] | CANNOT TELL | 17/36 |
| ridge | 14.4776 | 6.1168 | +1.808 | [-1.805, +5.42] | CANNOT TELL | 23/36 |
| donor_median | 17.4696 | 1 | +5.594 | [+2.212, +8.975] | HELPS | 22/36 |
| predict_zero | 18.2879 | 0 | +6.418 | [+3.005, +9.83] | HELPS | 30/36 |

### Fact-sheet comparison

| check | fact sheet / probe states | agreed value | status |
|---|---|---|---|
| visits | 1024 | 1024 | MATCHES |
| groups | 36 | 36 | MATCHES |
| ours | 13.37 | 13.370101628934457 | MATCHES |
| ours (probe) | 13.370 | 13.370101628934457 | MATCHES |
| hgb_l1 MAE | 11.69 | 11.687794651860322 | MATCHES |
| hgb_l1 MAE (probe) | 11.688 | 11.687794651860322 | MATCHES |
| hgb_l1 d (probe) | -1.896 | -1.8959172403553828 | MATCHES |
| hgb_l1 low (probe) | -4.758 | -4.758429376513538 | MATCHES |
| hgb_l1 high (probe) | +0.967 | 0.9665948958027728 | MATCHES |
| hgb_l1 groups ours better (probe) | 17 | 17 | MATCHES |
| lgbm MAE | 12.70 | 12.70400342344966 | MATCHES |
| lgbm MAE (probe) | 12.704 | 12.70400342344966 | MATCHES |
| lgbm d (probe) | -0.745 | -0.7451568406919876 | MATCHES |
| lgbm low (probe) | -3.298 | -3.297843725034701 | MATCHES |
| lgbm high (probe) | +1.808 | 1.8075300436507256 | MATCHES |
| lgbm groups ours better (probe) | 18 | 18 | MATCHES |
| rf MAE | 12.87 | 12.866878493343368 | MATCHES |
| rf MAE (probe) | 12.867 | 12.866878493343368 | MATCHES |
| rf d (probe) | -0.781 | -0.7807782035108838 | MATCHES |
| rf low (probe) | -3.156 | -3.156196511951882 | MATCHES |
| rf high (probe) | +1.595 | 1.5946401049301144 | MATCHES |
| rf groups ours better (probe) | 19 | 19 | MATCHES |
| lgbm_tweedie MAE | 13.62 | 13.61727468823652 | MATCHES |
| lgbm_tweedie MAE (probe) | 13.617 | 13.61727468823652 | MATCHES |
| lgbm_tweedie d (probe) | +0.337 | 0.3367537945969967 | MATCHES |
| lgbm_tweedie low (probe) | -1.232 | -1.232306596028193 | MATCHES |
| lgbm_tweedie high (probe) | +1.906 | 1.9058141852221864 | MATCHES |
| lgbm_tweedie groups ours better (probe) | 17 | 17 | MATCHES |
| ridge MAE | 14.48 | 14.4776059545183 | MATCHES |
| ridge MAE (probe) | 14.478 | 14.4776059545183 | MATCHES |
| ridge d (probe) | +1.808 | 1.8079234210099406 | MATCHES |
| ridge low (probe) | -1.805 | -1.8045414963969117 | MATCHES |
| ridge high (probe) | +5.420 | 5.420388338416793 | MATCHES |
| ridge groups ours better (probe) | 23 | 23 | MATCHES |
| vs L1 d (notes) | -1.90 | -1.8959172403553828 | MATCHES |
| vs L1 low (notes) | -4.76 | -4.758429376513538 | MATCHES |
| vs L1 high (notes) | +0.97 | 0.9665948958027728 | MATCHES |
| every per-region rival contrast CANNOT TELL | cannot_tell x5 | {"ridge": "cannot_tell", "rf": "cannot_tell", "lgbm": "cannot_tell", "lgbm_tweedie": "cannot_tell", "hgb_l1": "cannot_tell"} | MATCHES |
| mid-pack: L1, LightGBM, RF better; Tweedie, Ridge worse | as stated | as stated | MATCHES |

### Inputs

| file | sha256 prefix (re-hashed now) | in spec list | read by | matches spec/A/B prefixes |
|---|---|---|---|---|
| D:/treeroute/rivals/coral/20261020_f3b8e3da/board_lead_0.csv | 3220b5c8967f0570 | yes | AB | yes |
| D:/treeroute/rivals/coral/20261020_f3b8e3da/lead_0/preds_hgb_l1.parquet | 7039e548bf4ead04 | yes | AB | yes |
| D:/treeroute/rivals/coral/20261020_f3b8e3da/lead_0/preds_lgbm.parquet | 3e1d4b01737efbbf | yes | AB | yes |
| D:/treeroute/rivals/coral/20261020_f3b8e3da/lead_0/preds_lgbm_tweedie.parquet | 41f5fa63b5ebb276 | yes | AB | yes |
| D:/treeroute/rivals/coral/20261020_f3b8e3da/lead_0/preds_rf.parquet | 36830d55b5092fb7 | yes | AB | yes |
| D:/treeroute/rivals/coral/20261020_f3b8e3da/lead_0/preds_ridge.parquet | f84ad92e63f9855c | yes | AB | yes |
| D:/treeroute/runs/coral/headline/20261020_f3b8e3da/test_preds.parquet | dd07762558023d5f | yes | AB | yes |
| D:/treeroute/runs/coral/headline/20261020_f3b8e3da/verdict.json | 6bf9b04970173323 | yes | AB | yes |

Scripts: posthoc_A.py sha256 0cee249c0834dc2bbf0fe9ec458b200e20e096a4c5fc24e8d585a09584bab7c0; posthoc_B.py sha256 6b781c848bd84391da3bb71975135ebdcd806150ec45911d18e2c3f3f0db58ff; reconcile_AB.py sha256 5dcbe687b730c77f6207236bfa674d9a7a473b402e89a6c74b3487c7273b4c58.

## Part text (paste into engine/PENDING_PARTS.md; number to be assigned by the main session)

```
## Part NNN - PAPER FACTS RE-COMPUTED POST HOC (rulings AK3, AK4(a)); TWO INDEPENDENT SCRIPTS AGREE

2026-10-26. POST HOC: computed after the test labels were opened; report-only; no pre-registered verdict changes.
Folder D:/treeroute/analysis/paper_posthoc (POSTHOC_REPORT.md, SPEC.json, posthoc_A.py, posthoc_B.py, reconcile_AB.py, *.json).
- **Method.** Two scripts (A sha256 0cee249c0834dc2b, B 6b781c848bd84391) were written independently from one spec and re-computed the provisional facts from saved predictions and frozen engine CSVs (light; no refit). reconcile_AB.py compared 3,917 leaves: 0 disagreements (every full-precision float bit-identical). A ran 1,327 checks, B 1,738; 0 failed. All 82 input files match their sha256 prefixes. No script needed a fix.
- **M34 (identity trees-off = guess-normal).** MAE equal to 6 significant digits in all four: PM2.5 4.03161, NDVI 0.0394141, fire 0.00625876 (added), defo 0.00840486. Relative differences -5.4e-11 / -6.2e-09 / 2.1e-08 / 4e-11; largest row difference 4.1e-09 / 1.76e-07 / 8.09e-07 / 4.76e-09, all inside the identity tolerance; guess-normal == clip(normal) exactly. **Wording fix:** 'within 1e-8 relative' is false for fire; say 'within 2.1e-8 relative' or 'equal to 6 significant digits'.
- **R12 (fire nowcast ordering).** Confirmed: log trees-off 0.004281 < predict-zero 0.004284 < four log arms 0.004296-0.004322 < adopted 0.004385 < arcsine trees-off 0.004428 < identity normal 0.006259. New, report-only (40 regions): adopted vs log trees-off d -0.000103 [-0.000231, +2.51e-05] CANNOT TELL (adopted better in 25/40); vs predict-zero d -0.000104 [-0.00062, +0.000413] CANNOT TELL (3/40).
- **R13 (corrector / placebo / plain).** Confirmed for all five runs; all 21 placebo pairs of jackknife.csv re-derived exactly: EQUIVALENT except defo identity unweighted (CANNOT TELL) and fire's two identity pairs (HURTS).
- **R14 (penalties).** Confirmed: PM2.5 a_tree 15 / a_ctx 15; NDVI 0.5 / 0.03125; fire 50 / 50; defo lambda 10; coral 50 / 50. M47 (same point at later leads) not re-checked.
- **R15 = AK4(a) ablation table.** Every saved column scored (89 columns, all equal to score_pooled.csv). Regret of the adopted arm: PM2.5 0.00061 (0.017%), NDVI 0, fire 8.93e-05 (+2.08%), defo 0, coral 0.5505 (+8.95%). Not a test of the per-unit axis (M56); AK4(b) is still open. Wording: defo adopted 0.0054158 vs log plain 0.0054164 is '<', not '='.
- **P29 (interval method).** With t(G-1) instead of z = 1.96, exactly 2 of the 79 deciding verdicts change: fire nowcast HELPS -> CANNOT TELL (t39 2.023, CI [-1.2e-06, +8.58e-05], p_t 0.0564 vs p_z 0.0492); coral CRW lead 183 BEATS -> CANNOT TELL (32 regions, t31 CI [-0.07307, +3.773], p_t 0.0588 vs p_z 0.0498). Holm over the five nowcasts: all survive with z (fire last, 0.0492); with t fire fails (0.0564). Band share of the reference MAE: PM2.5 1.20%, NDVI 1.52%, fire 0.31%, defo 1.93%, coral 11.06%. Count is 79, not 'about 80'.
- **R3b (model vs best naive).** Fire +2.42% vs log trees-off and +2.36% vs predict-zero (worse); PM2.5 -6.88%, NDVI -20.02%, defo -5.23%, coral -17.31%.
- **RC12 (coral by magnitude, outcome-defined).** 'L1 wins on every bleached stratum' is NOT reproduced. Ours is lower in B1-B3 (e.g. B3 8.40 vs 9.47); hgb_l1 is lower only above q75 (41.05 vs 31.15, d -6.16 [-9.49, -2.83] HURTS) and at y >= 50 (53.13 vs 38.66, HURTS). Ours under-predicts the largest events (above q75: mean prediction 17.8 vs truth 58.4; L1 29.3).
- **A1 (fire active cells vs Tweedie, outcome-defined).** Confirmed. y > 0 (1,759 cells, 33 regions): ours 0.191 vs 0.201, d +0.00472 [+0.00237, +0.00706] HELPS. Top 1% (y >= q99 = 0.102941 from test labels; 949 cells): 0.308 vs 0.335, HELPS. Zero rows (98.14%): ours predicts 0.00085 on average vs 0.00032, d -0.000549 HURTS. Ridge's guarded column is the identity trees-off, not guess-normal exactly.
- **A2 (coral bleached visits vs rivals, outcome-defined).** Confirmed: 1,024 visits, 36 regions; ours 13.37 is mid-pack (L1 11.69, LightGBM 12.70, RF 12.87 lower; Tweedie 13.62, Ridge 14.48 higher); all five per-region contrasts CANNOT TELL.
- **Fact-sheet edits:** M34 wording (+ add fire); RC12 'every bleached stratum' -> 'the top quartile and y >= 50'; P29 'about 80' -> 79; R15 defo '=' -> '<'; A1 spec: Ridge guarded = identity trees-off. Everything else matches.
```

