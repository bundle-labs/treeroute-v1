# Paper notes: rival comparison (running list of claims to include)

Started 2026-10-21. Every claim below has its numbers and its source. The rival Part (signed 2026-10-21, Part 598) rules the protocol. Results are logged in engine/PENDING_PARTS.md Parts 600 (coral), 606 (fire) and later.

## Fire (Part 606; board D:/treeroute/rivals/fire/20261017_869d1f38)

1. **MUST INCLUDE (owner, 2026-10-21): on the cells that actually burn, our model beats the MAE-winning rival (LightGBM-Tweedie).**
   - Nowcast, cells with fire (y > 0), 1,759 cell-months in 33 regions: MAE ours **0.191** vs Tweedie **0.201**.
   - Per-region paired contrast (Tweedie minus ours) is +0.0047, 95% jackknife CI **[+0.0024, +0.0071]**. Ours is better in **25 of 33** regions.
   - Big fires (top 1% of burned fraction, 949 cell-months): ours 0.308 vs Tweedie 0.335. On these, ours predicts 0.098 and Tweedie 0.062, where the truth averaged 0.391.
   - Computed 2026-10-21 from the run's test_preds and the board's preds_lgbm_tweedie.parquet. Group-level jackknife as in the board.
   - **Wording rule:** this subset is defined by the outcome (fire happened), so it is reported as a conditional, stratified result ("on cell-months where fire occurred"), beside the pooled result. It is never presented as the headline.
2. **Pooled MAE, the honest overall result:** Tweedie wins (0.00404 vs ours 0.00439; LOSES verdict, flagged TIMID). Predict-zero (0.00428) also beats us on MAE.
   - The reason is that 98.1% of cell-months have no fire. On those, ours predicts a mean of 0.00085 and Tweedie 0.00032; the many tiny errors add up.
   - RF and LightGBM: CANNOT TELL (TIMID). Ridge: we BEAT it.
3. **Ranking (corr2): ours is highest** at every lead (0.222 at the nowcast vs rivals 0.198-0.213).
4. **Leads 6 and 12:** the pre-registered safety check declines our model to the normal, and Ridge, RF and LightGBM also decline (IDENTICAL). Tweedie stays and wins on MAE (TIMID).
   - Our pinned model's own MAE: 0.00452 / 0.00450, corr2 0.214 (the highest).

## Coral (Part 600; board D:/treeroute/rivals/coral/20261020_f3b8e3da)

- **Pre-registered nowcast:** ours 6.70. The coral-only L1-boosting rival 6.36 beats us (LOSES, significant). Against the four common rivals: CANNOT TELL; ours has the lowest pooled MAE vs Ridge, RF, LightGBM and Tweedie.
- **The loss comes from under-predicting big events, not from missing zeros.** Ours wins on 0% surveys (1.39 vs 2.12); L1 wins on every bleached stratum (severe: 38.7 vs 53.1). **CORRECTED 2026-10-26 (Part 622, two independent scripts):** NOT every bleached stratum. Ours is lower in the three bleached quartile bins below q75 (e.g. 8.40 vs 9.47); the L1 booster is lower only above q75 (41.05 vs 31.15, HURTS) and at y >= 50 (53.13 vs 38.66, HURTS). Ours under-predicts the largest events (above q75: mean prediction 17.8 vs truth 58.4; L1 29.3).
- **Post-hoc, engine v2 alarm** (designed AFTER the v1 runs; ruling AE3; must be stated so): ours with the alarm 6.12, the lowest of all models. Against L1-boosting this is within noise (CANNOT TELL); against Tweedie it is a significant win. The gain comes from 2016 (McClanahan); 2017 and 2019 are slightly worse.

- **Active (bleached, y > 0) surveys, nowcast** (1,024 surveys, 36 regions; computed 2026-10-21): the fire result does NOT carry over.
  - Pre-registered ours: 13.37, mid-pack: L1 11.69, LightGBM 12.70, RF 12.87 are better; Tweedie 13.62 and Ridge 14.48 are worse.
  - Per-region contrasts: ALL CANNOT TELL (every CI includes zero; e.g. vs L1 -1.90 [-4.76, +0.97]).
  - With the v2 alarm (post-hoc): ours 11.84, level with L1 (11.69). Ahead of every rival per region (19-22 of 36), none significant.
  - Paper wording: "the active-cell advantage holds on fire (significant) but not on coral, where the pre-registered model is mid-pack on bleached surveys."

## Reporting rules for every problem

- Report MAE AND corr2 (and hit rate) together. On mostly-zero targets MAE rewards timidity; the board's TIMID flag marks such wins.
- Pre-registered verdicts first. Post-hoc analyses are labelled as such.
- Conditional (outcome-defined) subsets are reported as stratified results beside the pooled one, never as the headline.

## PM2.5 (Part 610; board D:/treeroute/rivals/pm25/20261007_74e67609)

- **Honest headline: a linear model (Ridge, log link, normal as offset) is the strongest rival.**
  - Nowcast: ours 3.588 vs Ridge 3.426, CANNOT TELL.
  - Leads 6 and 12: Ridge is significantly better (lead 6: 3.600 vs 3.846; lead 12: 3.656 vs our pinned model 3.840 and our headline normal 4.084).
- **Against the tree rivals** ours is level or better.
  - RF: we beat it at the nowcast and at raw lead 12.
  - LightGBM: CANNOT TELL / EQUIVALENT. At lead 6 we beat its guarded answer, because its own guard failed.
- **Lead 12:** our guard declined to the normal (4.084), so every guarded rival beats our headline answer there. Our pinned model (3.840) is level with LightGBM and beats RF.
- **corr2** is high for everyone (0.83-0.85), and the differences are small. PM2.5 is largely seasonal and regional.
- **To check before writing (post-hoc, label it so):** whether Ridge's edge comes from extrapolating multi-year trends that trees cannot follow (residual by test year).
- **Leak audit (Part 611): Ridge's win is leak-free and fair.**
  - History and drivers were byte-checked against the raw stores on every row and group. Picks were locked before the test labels were opened.
  - Removing every extra advantage Ridge had (its own test group, lat, missing flags) moves MAE by <= 0.026, and no verdict changes.
- **Why it wins:** a linear "recent level minus long-run level" correction from the history columns that both models receive. It tracks the post-2019 decline (China) that our trees, anchored to a 2019 normal, cannot extrapolate. Without the history columns Ridge loses its edge (we win at the nowcast).
- **Report:** at lead 0 the gap rests on 3 Chinese groups (without them d -0.04, CANNOT TELL). At leads 6/12 it is broad (85/127 groups) and survives dropping China. Ridge's edge was already visible before the test window, so the result is not a test-period fluke.
- **Honest framing:** a limitation of tree models under trends. It is a candidate future-work item (unit-relative history), NOT something to fix post-hoc on this test set.

### PM2.5 vetted wording (2026-10-22)

The fact-checker and the hostile reviewer were run in workflow <id>-b08 against the board, the headline table and the audit.

- **Do NOT write that the architecture "fails" on PM2.5.** Our answer beats the normal by 11% (nowcast) and 5% (6 months).
- **Do NOT write "we beat the other rivals".** On the deciding contrast against the tree rivals: 2 BEATS, 2 CANNOT TELL and 2 LOSES; both losses are at 12 months, where our answer is the normal.
- **"Level" is only for EQUIVALENT.** CANNOT TELL means inconclusive.
- **Rounding:** HEADLINE_MODEL_TABLE.md shows the 12-month pm25 model MAE as 3.841 (-5.9%). Recomputed it is 3.84046, i.e. 3.840 (-6.0%). DONE 2026-10-26 (Part 621 addendum): the table now shows 3.840 (-6.0%).

| Lead | Our answer | Ridge | Random Forest | LightGBM |
|---|---|---|---|---|
| 0 | 3.588 | 3.426: cannot tell (raw same) | 3.692: **we beat** (raw same) | 3.552: cannot tell (raw same) |
| 6 | 3.846 | 3.600: **we lose** (raw same) | 3.822: cannot tell (raw same) | 4.054 (its own guard failed): **we beat**; raw 3.842 equivalent |
| 12 | 4.084 (our guard failed: normal; model 3.840) | 3.656: **we lose**; raw also loses | 3.890: **we lose**; raw **we beat** (+0.050 [+0.001, +0.098]) | 3.844: **we lose**; raw equivalent |

Paragraph:

> On PM2.5, our pre-registered answer lowers pooled MAE relative to each location's normal by 11% at the nowcast (3.588 vs 4.032; corr² 0.852, anomaly R² 0.185) and by 5% at 6 months (3.846 vs 4.054; anomaly R² 0.069). At 12 months the pre-registered safety check rejected the model on the 2017–2019 check window, so our answer is the normal (4.084). The rejected model would have scored 3.840 (−6%); we report that only as a secondary number.
>
> Against the two tree-based rivals, on the pre-registered deciding contrast:
> - our answer beats Random Forest at the nowcast (d = +0.104 [+0.040, +0.168]);
> - it beats LightGBM at 6 months (+0.208 [+0.103, +0.312]), because LightGBM's own safety check failed;
> - it cannot be told apart from LightGBM at the nowcast or from Random Forest at 6 months, and both point estimates favour the rival;
> - it loses to both at 12 months, where our answer is the normal.
>
> Compared before safety checks, our model is never significantly worse than either tree rival.
>
> A linear model was the strongest rival: Ridge on log(y + 1.5) with the normal as offset, given the same driver and history columns as our trees plus latitude and calendar month, and fitted across all regions.
> - At 6 months it beats our answer: 3.600 vs 3.846, d = −0.247 [−0.422, −0.071].
> - At 12 months it beats our answer too: 3.656 vs 4.084, d = −0.427 [−0.637, −0.218]. Against our rejected model, d = −0.184 [−0.326, −0.043].
> - At the nowcast the two cannot be told apart: 3.426 vs 3.588, d = −0.162 [−0.342, +0.019]. This gap rests on three Chinese regions; without them, d = −0.042 [−0.128, +0.043].
> - At 6 and 12 months the gap is broad: Ridge is better in 85 of 127 regions, and still wins without those three.
>
> Ridge's corr² and hit rate are equal or higher, and no rival win is flagged as timid. A post-hoc audit found no leakage. Refitting Ridge so that it sees exactly what our router sees changes its MAE by at most 0.026 and changes no verdict.
>
> Post-hoc analyses, designed after the test results were seen, are consistent with a drift explanation but do not prove it:
> - Ridge's largest coefficients form a "recent level minus long-run level" contrast from the history columns.
> - Its advantage grows with test year, and with how steeply a region was falling before 2020 (Spearman ≈ −0.3).
> - A refit without the six history columns removes its advantage. That refit also removes last month's value, so it shows that the history block carries the edge, not the contrast alone.
>
> On the North China Plain, PM2.5 fell about 5.5% a year over 2013–2019. Our nowcast there averaged 58.0 µg/m³, against an observed 42.0 and a normal of 62.4. The two tree-based rivals also trail Ridge at every lead, so tree models here share the limitation. Our design makes it worse, because the router does not see the unit's own recent level. We did not change the model on this test set; a unit-relative history input is future work.
- **No-trend locations (Part 612; post-hoc; grouped by PRE-test slope).**
  - At the nowcast we are level with Ridge on flat locations (d +0.008 [-0.09, +0.11]). We are significantly better on locations that had been rising >3%/yr (+0.22 [+0.09, +0.35], 74/88 units).
  - At 6 and 12 months Ridge keeps a small edge even on flat locations (6 months: -0.10 [-0.165, -0.040]). The trend explains most of its lead, not all of it.
  - Report it as a post-hoc stratified result, beside the pooled verdicts.
- **MUST INCLUDE (owner, 2026-10-22): on spike months we beat Ridge at every lead.** Source: Part 612 addendum; D:/treeroute/analysis/pm25_ridge_audit/spike_months.py, .csv and _out.txt.
  - **Definition.** A spike month is a test cell-month whose observed PM2.5 is above the location's own 2003-2019 90th percentile: 7,966 cell-months in 124 regions. The subset is defined by the outcome, so it is reported as a stratified result beside the pooled verdicts, never as the headline.
  - **Spike months** (d = Ridge - ours, region-jackknife 95% CI):
    - nowcast: MAE ours 9.15 vs Ridge 10.39, d +1.35 [+0.99, +1.71];
    - 6 months: 9.92 vs 10.60, +0.82 [+0.57, +1.07];
    - 12 months: our answer (the normal) 9.40 vs 10.30, +1.04 [+0.81, +1.28]; our model 9.80, +0.52 [+0.33, +0.70].
    - Same sign and significance at the 75th and 95th percentile thresholds.
  - **Ordinary months:** Ridge is better at every lead (nowcast d -0.28 [-0.47, -0.09]). That is where its pooled win comes from.
  - **Required qualifier (do not drop it).** The win comes mostly from Ridge's downward shift, not from extra skill of ours on extremes:
    - the plain normal also beats Ridge on spike months (nowcast 9.42 vs 10.39);
    - our model only ties the normal on spikes at the nowcast (d +0.03 [-0.18, +0.25]);
    - at 6 and 12 months the normal beats our model on spikes (-0.53 [-0.75, -0.32]).
  - **Against the tree rivals on spikes at the nowcast:** better than LightGBM (+0.30 [+0.11, +0.48]); vs RF +0.20 [-0.01, +0.41] (cannot tell at p90; significant at p75 and p95).
  - **Wording:** "On spike months (observed PM2.5 above the location's 2003-2019 90th percentile; an outcome-defined subset), our model's MAE is lower than Ridge's at every lead, the mirror image of Ridge's advantage on ordinary months. The difference reflects Ridge's systematic downward shift: the location's normal also beats Ridge on these months, and our model does not beat the normal on them."

## Defo (Part 614; board D:/treeroute/rivals/defo/20261017_d71c61f4)

- **No rival beats our model on defo at either lead.**
  - Nowcast: ours 0.00542 is the lowest MAE. We beat Ridge and LightGBM-Tweedie; equivalent to LightGBM; cannot tell vs RF (point estimate favours ours).
  - 1 year: we beat Ridge and Tweedie; equivalent to RF and LightGBM. Their nominal edge is inside the equivalence band and flagged TIMID.
- **Report corr2 beside MAE:** the two tree rivals have slightly higher corr2 (0.017-0.019 vs ours 0.016-0.017). Hit rate is highest or tied for ours.
- **Versus the normal:** -35.6% MAE.

## NDVI (Part 616; board D:/treeroute/rivals/ndvi/20261016_d1de3158)

- **Nowcast:** ours 0.0315 (-20% vs the normal) beats Ridge (0.0429) and RF (0.0352). Against LightGBM (0.0320) we cannot tell, with the point estimate in our favour. Ours has the highest corr2 (0.963) and hit rate (0.461).
- **6 and 12 months:** the pre-registered guards decline most models to the normal, ours included.
  - At 6 months only Ridge passes its guard, and it beats our normal answer by 3% (0.0384 vs 0.0396).
  - At 12 months every guard fails, so all are identical.
  - Raw models: Ridge (and RF at 12 months) are slightly better than our pinned model. Report this beside, labelled as raw.
- **Across problems** (post-hoc observation, not a tested claim): Ridge is the rival that holds up at long leads on the two trending targets (PM2.5, NDVI). The PM2.5 mechanism (Part 611) has not been tested on NDVI.

## Human (published / domain) rivals - Parts 617-619 (final table engine/RIVALS_TABLE_FINAL.md)

- **Wording rule:** when the rival's guard failed, its deciding answer IS the normal. Write "the published method did not beat the seasonal normal on these rows; ours did". Never write "ours beat method X by Y" using the guarded number. Print the raw rival beside it.
- **Defo vs REDD+ VT0007** (pre-registered joint claim: YES at both leads). No VT0007 form beat the normal. Even the calibrated raw map (MAE 0.00568) is worse than ours (0.00542), and the difference is small but clear.
- **NDVI nowcast.**
  - We beat the rain-lag BARDL model (0.0342 vs 0.0315). This is a real win over a method that itself beats the normal.
  - The Kraft et al. LSTM re-run did not beat the normal (raw 0.0607); ours did.
  - No published NDVI forecast reaches 6 or 12 months, so say so; the H1 extension is printed, labelled, and never decides.
- **Coral vs NOAA CRW.**
  - Nowcast: cannot tell.
  - 4-6 months ahead: NOAA's nowcast rule fed old heat does not beat the normal; ours does, barely (CI low edge 0.002).
  - 1 year ahead: both are the normal.
  - CORRECTED 2026-10-26: NOAA covers all 2,312 coral test rows (not a subset). The deciding contrast uses 2,290 rows in 32 of 37 ecoregions (groups with >= 10 rows); 'ours 6.47' is our MAE on those rows.
- **PM2.5 vs MERRA-2 (lagged 1 month):** cannot tell. The mean gap is large (8.44 vs 3.59), but the region spread is huge. MERRA-2 same-month (advantaged, never decides) is slightly better than ours: disclose.
- **Fire:** pending (Part B).

## Correction 2026-10-26 (paper fact-sheet review, C4/C5 and the common board)
- Human deciding WINs over a rival whose guard failed: **8 of 9**, not 7 (coral 183 d, defo x6, NDVI Kraft). Only NDVI BARDL H1 passed its guard. Count by METHOD in the paper: one real win (BARDL H1); three published methods (VT0007, Kraft LSTM, NOAA's rule fed old heat) did not beat the seasonal normal while ours did; two inconclusive (NOAA nowcast, MERRA-2). Keep the 9/2/1 row counts for the full table only.
- The same rule applies to the COMMON board: 2 of the 9 common WINs are over rivals whose guard failed (fire lead 0 Ridge, guarded = the normal 0.006259; raw Ridge 0.004299 is CANNOT TELL, timid; and PM2.5 lead 6 LightGBM). Write them as "the rival did not beat the normal; ours did".
