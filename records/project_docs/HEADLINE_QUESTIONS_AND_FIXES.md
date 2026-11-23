# Headline run: every question and fix (2026-09-27)

Checked by 16 agents: 7 scouts, 7 skeptics, 1 completeness critic, 1 compressor. Read-only; nothing was edited or run.
Answer format: `Q1 a, Q2 a, ...`, or "all recs except Q7 b".

## Residual uniformity audit (2026-09-28; 136 agents: finders by layer, 2 skeptics per finding)

Result: after all rulings, ONE real architecture gap and three small porting fixes remain. Everything else is already ruled, dataset-owned, or the outcome of one shared rule.

| # | Item | Recommended rule | Status |
|---|---|---|---|
| U-1 | The region router (defo) has no per-cell normal column. So its trees-off is a region constant, while its guard reference is a per-cell normal: three different objects, where PM2.5 has one (defo_softgate.py:105-124 vs pm25_adaptation.py:436-442). | Every router with a normal carries the per-unit link-matched normal (fit rows only) as an UNPENALISED column. Then trees-off = guard reference = decline target on every problem. It adds no penalty, so the region router still tunes trees only. Coral is exempt (it has no normal). | **APPROVED by the owner 2026-09-28** |
| U-2 | Damped persistence leaves both years out only when lead % 12 == 0 (pm25_forecast.py:512, 533), which biases phi low on annual defo. | Leave both out whenever target and predecessor share the normal's season key (for annual data: every lead). | porting fix |
| U-3 | Top-10% detection has two definitions: strict pooled (forecast_report.py:55-77) and inclusive per region (final_table.py:77-79, 142). The inclusive one breaks on zero-heavy targets. | One function: event = y > the test-row q90 (strict); NaN if there are fewer than 10 events or more than 50% of rows are events; print the event share. Pooled for the headline, per region for the jackknife. | default unless the owner objects |
| U-4 | Guard tolerances are absolute PM2.5 numbers (1e-4, 1e-6), about 1000x looser relative to fire's and defo's scale. | Relative tolerances scaled to each problem, with PM2.5's gates unchanged. | porting fix |

Stale APP_PLAN lines to clean up (no decision needed): :91 per-problem recipe keys, :116/:138 'PM2.5 stays frozen', :139 fire_cap800, :122 decline wording, :126 defo normal window, :129 add the last-5-years normal.

## Uniformity rulings (owner, 2026-09-28): the recommendations accepted

| Item | Ruling |
|---|---|
| Router kind | One rule, three outcomes: per-cell (>= 24 history rows per unit), region (short history), neighbour (almost no repeat visits; coral). Each router kind brings its own penalties: per-cell and neighbour search trees + context (7x5 grid); region searches trees only (7 levels). This is not a non-uniformity. |
| PM2.5 penalty | Re-searched on the same grid in the headline re-run, like every problem (Part 556 found it by grid; the new inputs need a new search). |
| Log link | ONE log for all problems: log(y+c), with c from donor rows (log1p in the target's own unit). log1p stays only as a report-only regression check on PM2.5 (c = 1.5, equivalent in Part 558). Offered only where defined (not on NDVI). Supersedes D1 'both logs'. |
| Hit tolerance | The donor-data rule (D9) for every problem. PM2.5's +-2 ug/m3 and NDVI's +-0.02 are printed beside it, plus top-10% detection (Q14 c). |
| Bank recipe | One recipe for all: PM2.5's half-region bags, 100 trees per donor (raised later for everyone), max_features 10%. |
| Cells per region | A COMPUTE setting in each dataset's recipe, not architecture (default 100). This way deforestation's region router keeps enough history rows (its shipped runs used 4,000 cells per region, about 60,000 pooled rows). |
| Still per problem by design | Features, ban list, split, time windows, lead units (the dataset); Type 3 gates (reported separately); coral's decision method, which follows from having no history (optional track). |

## Owner ruling 2026-09-27 (second message): no more questions -- the other problems follow PM2.5

The goal is ONE unified schema. NDVI, fire and deforestation follow exactly what was done for PM2.5. Coral is an OPTIONAL extra track, because it has no per-site history. This settles the open questions as follows:

| Q | Settled as (the PM2.5 rule) |
|---|---|
| Q6 | D4 yes: link-matched normal from fit years only. D6: clip to the legal range everywhere; the PM2.5 re-run adds it (its forecast already floors at 0). D7 yes: donor rows. D10: coral track. |
| Q11 | a: guard against a per-cell normal (for defo, each cell's mean over the <=2019 years), pooled corr2 printed |
| Q12 | CORRECTED by the owner: feature engineering belongs to the DATASET, not the architecture. The engine adds the own-history block for every problem, and it replaces defo's 4 own-past columns (h_lag1-3, h_cum), which carry the same information. defo's neighbour and years-since columns (h_nbr1, h_nbr2, h_nbr_cum, h_yrs_since) STAY as defo dataset features. Nothing is lost. |
| Q13 | a: PM2.5's relative penalty grid; edge picks are flagged, never extended |
| Q16 | a: all donor rows up to the cut (PM2.5 reads c from all donor rows) |
| Q19 | a: 1.96 (PM2.5's jackknife, adaptation.py:537) |
| Q21 | a: no correction; the full grid is shown |
| Q22 | b: each problem's band is derived from its own first run, as PM2.5's 0.0395 was |
| Q24 | a: a PRE-REGISTRATION Part written before any number (as PM2.5 Parts 563/569/571), plus a hash stamp |
| Q25 | b: no special arm on one problem; disclose |
| Q33 | CORRECTED by the owner: NDVI keeps its engineered features (the 435 driver lags and water rolls). They are feature engineering, i.e. part of NDVI's dataset, not of the architecture. Condition: rebuild them date-safe, so that at lead L every lag ends at or before the issue month. |
| Q39 | a: 100 cells per region |
| Q37 | MAE everywhere (PM2.5's criterion); predict-zero and corr2 printed beside |
| Calibration unit | PM2.5's own rule (per-cell needs >= MIN_HIST 24 rows, pm25_adaptation.py:143): fire and NDVI per-cell; defo (17 rows/cell) automatically region-pooled |
| Q42-Q52 | Q42 withdraw; Q43 allow + disclose; Q44 PM2.5's rival boards (N/R/G/H + products where they exist) run on every problem, later; Q45 drop F with a deviation note; Q46 side rows, EAC4 later; Q47 Kraft later; Q48 no intervals in the headline; Q49 yes (free); Q50 quartiles; Q51 flag only; Q52 disclose |
| Coral Q28-Q32, coral fixes | parked in the optional coral track |

Principle (owner, 2026-09-27): the unified schema covers the ARCHITECTURE (engine + Type-2 layer). Feature engineering is per problem, like the ban lists, and lives in each dataset.

Still to do (not questions): the per-problem ban-list review after all datasets have been looked at (Q34), and checking tni's smoothing window (F10).

## Owner answers (2026-09-27)

| Q | Answer | Note |
|---|---|---|
| Q1 | a: NDVI in the headline, ported to the PM2.5 engine | |
| Q2 | **Do not drop oni/tni: use them as LAGGED features** | New rule: lag each centred index so its newest month is at or before the reference month (the nowcast month, or the issue month for forecasts). The window of each index still needs checking (F10). This replaces options a/b/c. |
| Q3 | a | |
| Q4 | a | |
| Q5 | a | |
| Q6 | explanation asked | |
| Q7 | a | |
| Q8 | a | |
| Q9 | use the existing result **if** it complies with the rules | It does not comply: see the answer in chat (it drops oni/tni rather than lagging them, has no t-1 history, and the layer never chose it). A re-run is needed. |
| Q10 | a | |
| Q11 | not answered | |
| Q12 | asked what the 8 columns are | h_lag1-3, h_cum, h_nbr1, h_nbr2, h_nbr_cum, h_yrs_since (defo_matrix.py:47-54) |
| Q13 | explanation asked | |
| Q14 | c | |
| Q15 | a | |
| Q16 | explanation asked | |
| Q17 | a | |
| Q18 | a | |
| Q19 | explanation asked | |
| Q20 | a | |
| Q21, Q22, Q24, Q25 | explanation asked | |
| Q23 | **b: read each run as it lands** | |
| Q26, Q27 | a | |
| Q28-Q33 | explanation asked | |
| Q34 | **ban lists are PER PROBLEM, not uniform**; to be discussed after reviewing every dataset | |
| Q35, Q36 | a | |
| Q37 | **a, and ALL problems select on MAE in the adaptation layer** | ATTENTION: reverses ruling C5 (which set corr2 for fire and defo); confirmation requested |
| Q38 | b: GFED burn on NDVI at lag 1 only | |
| Q39 | explanation asked | |
| Q40, Q41 | a | |
| Q42-Q52 | not yet answered (not blocking) | |

## Questions (52)

### Blocking: must be answered before the headline run

**Q1. How does NDVI enter the headline?**  
Why: NDVI's headline comes from run89. It is not on U2, it was chosen on the test window, it uses leaky features, and its split is disputed (25 vs 44 regions).  
Options: a: port to PM2.5 engine, ndvi_split.txt, fresh bank (new model) | b: keep run89 on the clean 25, labelled 'not U2' | c: keep run89 on all 44 (bundle split), labelled | d: leave NDVI out  
Rec: **a: the only option that meets the pre-registration**

**Q2. Drop oni/tni from every nowcast too?**  
Why: oni/tni are centred means, so they look ahead. Forecasts already drop them (Part 558); nowcasts and the defo banks still use them.  
Options: a: drop everywhere; retrain the defo banks | b: drop; set to donor median in cached defo banks | c: keep in nowcasts, disclose  
Rec: **a: a real drop, like PM2.5; defo L1 banks took 32.7 min**

**Q3. Apply PM2.5's full look-ahead rules to all 5 problems, nowcast and forecast?**  
Why: Only PM2.5 lags annual columns and bans FREEZE, snow-DOY and AMO/SPEI. Fire, NDVI and defo still feed these; coral feeds ENSO lag0 and future GHS-POP epochs.  
Options: a: yes, plus lag same-month co-measured columns (fire cloud) | b: yes, date rules only | c: no, oni/tni only; disclose the rest  
Rec: **a: matches the pre-registration's 'no look-ahead' promise**

**Q4. Put the own-past-target history block in every bank, ending at the issue month (nowcast t-1)?**  
Why: The PM2.5 forecast history block is already ruled (Part 561). Still open: nowcasts, and one rule for which month the block ends at.  
Options: a: yes, every bank incl. PM2.5/NDVI nowcasts; coral declared empty | b: forecasts only; fire/defo nowcasts lose theirs  
Rec: **a: uniform; fire's L>=2 block moves one month later**

**Q5. If Q4=a, does the ladder's nowref also get the t-1 history?**  
Why: A nowcast with a t-1 history compared against a nowref without one compares unlike models, and the lead-0 contract then fails.  
Options: a: yes | b: no; label lead cost 'vs drivers-only nowcast' | c: drop the lead-cost contrast  
Rec: **a: like-for-like lead cost; lead-0 contract keeps working**

**Q6. Accept D4, D6, D7 (Tier 1 only) and D10 as recommended? D5 and D9 are asked separately.**  
Why: D4, D6, D7 and D10 are still held. D8 is moot, D7's c part is already ruled (D1), and D10(b) would need new fold code.  
Options: a: accept all; D4 full run replaces pending R3/Q4 check | b: go item by item  
Rec: **a: all small, none uses test data**

**Q7. One forecast adoption rule for all problems?**  
Why: PM2.5 pre-registers lagtrain behind the guard. Fire, defo and coral pick their lag arm per lead by vote or corr2.  
Options: a: lagtrain pre-registered + N2 guard; other arms diagnostic | b: the layer's per-lead pick, as shipped  
Rec: **a: uniform; 'both' only won through width (Part 527)**

**Q8. How do we prove the plumbing when shipped numbers can no longer reproduce?**  
Why: Dropping features breaks every shipped gate: PM2.5 4.100, fire 0.003993 and the defo cached arrays.  
Options: a: smoke-scale gate on old features/config, then switch | b: full old-feature run per problem | c: no gate; quote old numbers as earlier results  
Rec: **a: cheap; defo = 2 regions on the old banks**

**Q9. Clean PM2.5 nowcast: a full U2 re-run, or Part 561's nowref?**  
Why: Part 561's nowref (4.1563) is already clean, but it was never re-guarded and uses 203 rows per cell.  
Options: a: U2 re-run (7.3 h) | b: nowref as-is, disclosed  
Rec: **a: the only way the layer picks on clean features**

**Q10. Fire cut-off: keep 2018 or move to 2019?**  
Why: Fire trains on <=2018 and tests 2019-22 (your earlier choice). The draft says <=2019 and 2020-22.  
Options: a: keep 2018, test 2019-22, declared | b: move to 2019, test 2020-22 (3 years)  
Rec: **a: keeps 4 test years; the old gate is lost either way**

**Q11. Defo's guard reference and corr2 convention?**  
Why: Defo's trees-off is a per-region constant, which is an easy bar under pooled corr2 and scores 0 under within-region corr2.  
Options: a: per-cell normal; pooled corr2, per-region printed beside | b: per-region trees-off (D5); pooled corr2 | c: per-region trees-off; within-region corr2  
Rec: **a: a real bar with the same meaning as PM2.5's**

**Q12. Does defo keep all 8 history columns?**  
Why: Defo's history block is 8 h_* columns, including neighbour loss and years-since. PM2.5's uses only the cell's own past.  
Options: a: keep, declared as defo's bank recipe | b: own-cell lags only (retrain)  
Rec: **a: the bank recipe stays per problem under U2**

**Q13. Extend defo's penalty grid below 10 before pre-registration?**  
Why: Defo's penalty grid runs 10-10,000, but inner-window picks sat lower (median 6.25-25, Part 527).  
Options: a: keep it, flag the edge | b: shift down one decade | c: add two lower levels  
Rec: **c: the evidence is from the inner window only**

**Q14. Which hit rate on fire, defo and coral?**  
Why: The shipped hit rate is top-10% detection. D9's hit is |error|<=tol, which rewards predict-zero on zero-heavy targets.  
Options: a: D9 tolerance hit | b: top-10% detection hit | c: print both  
Rec: **c: detection can't be won by timid predictions**

**Q15. What reference does coral use for its hit tolerance and MAE skill?**  
Why: Coral has no per-unit normal; most sites have one row.  
Options: a: donor-row median | b: predict-zero; no hit rate | c: k=50 trees-off  
Rec: **a: fixed from donors before any run**

**Q16. Which donor rows feed fire's c, Tier 1 and D9 tolerance?**  
Why: Fire's bank sample is ~9x fire-enriched, which skews the zero share and the spread.  
Options: a: all donor rows up to the cut | b: the enriched bank sample  
Rec: **a: matches the real fire rate**

**Q17. Which contrast decides 'Helps' in each cell?**  
Why: The pre-registration's 'Helps' names no reference, UNIFORM names two, and no engine computes that CI.  
Options: a: adopted vs own normal; predict-zero printed beside | b: must beat both | c: predict-zero on zero-heavy targets, normal otherwise  
Rec: **a: matches the N2 guard; predict-zero has no corr2**

**Q18. Which units does the jackknife use for verdicts?**  
Why: Fire's region filter uses test-label variance. Coral's floor keeps only 8-11 of 63-74 ecoregions.  
Options: a: all test units | b: a label-free pre-test filter, count printed | c: shipped filters, count printed  
Rec: **a: the shipped filters use test labels**

**Q19. CI quantile: 1.96 or t(n-1)?**  
Why: The jackknife uses 1.96 with 7-11 units, so CIs are 13-20% narrower than t.  
Options: a: 1.96, declared | b: t(n-1) | c: print both, verdict on t  
Rec: **b: 1.96 is too optimistic at 7-11 units**

**Q20. One headline aggregation for all 5 problems?**  
Why: The PM2.5 headline is pooled and NDVI's is macro; NDVI's forecast flips sign between the two.  
Options: a: pooled headline, macro beside | b: macro headline, pooled beside  
Rec: **a: C5's corr2 and fire's rows are already pooled**

**Q21. Correct for multiple comparisons?**  
Why: About 20 problem x mode cells, each with several CIs, and no multiplicity rule anywhere.  
Options: a: no; full grid printed, declared | b: Holm on the primary contrasts | c: Bonferroni  
Rec: **a: the full grid is shown, so nothing is hidden**

**Q22. Do the shipped runs count as each problem's first run for its N3 band?**  
Why: The N3 rule derives each band from a problem's first full run. Only PM2.5's band is frozen.  
Options: a: yes; derive now from saved preds and freeze | b: no; derive from each headline run  
Rec: **a: the band is fixed before any headline number**

**Q23. Seal test metrics until every run is done?**  
Why: The engines log test verdicts as each run ends, so later bug-fix calls are made after seeing test numbers.  
Options: a: seal; open them at stage 5 | b: read each run as it lands  
Rec: **a: bug-fix decisions stay blind to test numbers**

**Q24. Where is the pre-registration frozen?**  
Why: The pre-registration would be a Part in an editable .md file, with no outside timestamp.  
Options: a: hash-stamped Part, worded 'pre-specified' | b: post to OSF before the first run | c: internal only, called 'pre-registered'  
Rec: **a: unless it is posted outside**

**Q25. Add a never-selectable burn-neutralised control arm to the PM2.5 run?**  
Why: PM2.5's GFED burn block entered through a 2020-23 test-window screen; the ledger still owes a control arm.  
Options: a: yes, labelled ablation (~1.5-2 h) | b: disclose only  
Rec: **a: measures the one test-screened input directly**

**Q26. Print the last-5-years normal beside every monthly problem?**  
Why: A no-model 'last 5 years' normal ties the PM2.5 nowcast on MAE (Part 566).  
Options: a: yes | b: on the PM2.5 rival board only  
Rec: **a: hiding the tie would overstate the claim**

**Q27. Add damped persistence beside the fire, defo and NDVI forecasts?**  
Why: PM2.5 prints raw and damped persistence; fire, defo and NDVI print raw persistence only.  
Options: a: yes | b: no; each keeps its own  
Rec: **a: known at issue, and cheap**

**Q28. Headline coral model: the 80 columns actually run, or the declared 77?**  
Why: Every coral adaptation run used 80 columns; memory and Part 454 say 77.  
Options: a: 80; fix the '77' label | b: 77; 80 as the regression arm | c: both, labelled  
Rec: **a: keeps the gate; the 77-vs-80 evidence is pilot-scale**

**Q29. Which pool do coral's donor folds use to pick the arm?**  
Why: The shipped coral folds use 'strict' (other donors only), which is the dropped no-history mode.  
Options: a: strict, as shipped | b: full-pool folds, one arm for both pools | c: pool-matched folds; full and rollout each pick  
Rec: **b: mirrors the own-history setup, one arm per problem**

**Q30. Main-split rollout: accept it as coded, labelled 'no own labels'?**  
Why: On main, every own-ecoregion row is a test row, so rollout leaves the router no own labels.  
Options: a: as coded, labelled | b: keep true labels before a declared cut  
Rec: **a: matches 'no test-era label', with no new cut to pick**

**Q31. Add those 874 own-ecoregion rows to the dbl2005 pools?**  
Why: The dbl split drops 874 labelled pre-2005 rows from 56 of the 63 test ecoregions.  
Options: a: no, as shipped; disclose | b: yes, all pools | c: both, labelled  
Rec: **c: shipped stays the regression row; variant tests real history**

**Q32. At each coral lead, which pool does nowref use?**  
Why: Once the issue-date fix lands, a nowref on the issue-date pool can no longer match the cached nowcast.  
Options: a: both: target-date (contract) and issue-date (lead cost) | b: issue-date only; drop the contract | c: target-date only  
Rec: **a: keeps the harness check and gives a clean lead cost**

**Q33. Which features does NDVI use on the engine?**  
Why: 435 of run89's 612 NDVI features are driver lags and water rolls. The PM2.5 engine builds none of them.  
Options: a: raw panel columns only, as PM2.5 | b: raw panel + run89's lag/roll builder, cut at issue | c: run89's 612-feature build  
Rec: **b: lags are features, not the layer; greenness lags water**

**Q34. Which ban list does NDVI use?**  
Why: REMOVE-11 alone keeps oni/tni, co2, snow-DOY, V20, cropland_fraction, landcover class and eddi/scpdsi.  
Options: a: PM2.5 list + MCD12Q1 slices, landcover class, eddi/scpdsi | b: shipped 612 minus oni/tni | c: REMOVE-11 only (draft)  
Rec: **a: REMOVE-11 lets look-ahead columns back in**

**Q35. clf_dry/clf_wet on NDVI: ban or keep?**  
Why: clf_dry/clf_wet were ruled KEEP for NDVI (Parts 306-312), but they are trained on NDVI itself (Part 431).  
Options: a: ban | b: keep (earlier ruling)  
Rec: **a: a classifier trained on the target is a label leak**

**Q36. Which links does NDVI get?**  
Why: 8% of NDVI rows are negative. The UB rule reads NDVI as unbounded (no arcsine), and the log links break or zero the negatives.  
Options: a: identity only; logs declared N/A | b: identity + log1p (negatives zeroed) | c: identity + shifted log (new rule)  
Rec: **a: logs would distort the 8% negative rows**

**Q37. NDVI selection criterion?**  
Why: Ruling C5 covered four problems; NDVI's criterion was never ruled.  
Options: a: MAE | b: corr2  
Rec: **a: continuous, signed, not zero-heavy (like PM2.5)**

**Q38. GFED burn block on NDVI?**  
Why: The engine adds GFED burn at lag 0, but fire browns NDVI in the same month, and 6 NDVI regions have no GFED file.  
Options: a: off | b: lag-1 only | c: on, as in PM2.5  
Rec: **a: a PM2.5 add-on that risks leaking the same month's burn into NDVI**

**Q39. How many test cells per NDVI region?**  
Why: The engine scores 100 stride cells per region, about 1% of NDVI's 428,683 cells.  
Options: a: 100, as PM2.5 | b: 300 (matrix ~3x; would not fit on D:)  
Rec: **a: the time and disk estimates assume it**

**Q40. NDVI headline window?**  
Why: The old +0.32 is 2021-23 on other cells; the draft uses 2020-23.  
Options: a: 2020-23, plus a 2021-23 subset row | b: 2021-23 only  
Rec: **a: uniform with the others, plus a comparison row**

**Q41. NDVI forecast leads?**  
Why: The other problems' leads are ruled. NDVI's forecast is the biggest job (~25-30 h).  
Options: a: 1/3/6/12, as PM2.5 | b: 1 and 12 only  
Rec: **a: uniform with the other monthly problems**


### Not blocking: can wait until after the run

**Q42. B3 level-shift claim: withdraw it, or restate it narrowly?**  
Why: The B3 level-shift wording was held until real numbers existed; Parts 556/558 now have them.  
Options: a: withdraw | b: restate narrowly with the 20-region numbers  
Rec: **a: an unpredicted offset cannot make anomaly-R2 negative**

**Q43. Allow provider baselines that include post-2019 years?**  
Why: The base periods of SPI, nino*.anom and several CPC/PSL indices are not recorded, and may include post-2019 years.  
Options: a: allow, disclose | b: rebuild our own pre-2020 anomalies (~0.5 day) | c: drop any index with an unverified baseline  
Rec: **a: no future month enters the value itself**

**Q44. Which rivals, after the headline?**  
Why: O6(a)'s per-cell MOS cannot run on coral, and the old boards used old features and no history.  
Options: a: one with-history set later, same inputs; coral neighbour-pool rivals | b: each problem keeps its old board  
Rec: **a: equal inputs, re-paired on the saved rows**

**Q45. PM2.5 rival board: run F, and add H2?**  
Why: Rival F (random forest) was pre-registered but never run. H2 was never run, and Board H does worse than the normal.  
Options: a: run F (~1 h est.) and add H2 | b: drop F with a deviation Part; add H2 | c: drop both; disclose  
Rec: **b: if Q44=a; H alone reads as a straw man**

**Q46. Operational products: side rows only? And when does EAC4 come in?**  
Why: MERRA-2 ties the PM2.5 MAE but is circular with ACAG. EAC4 was approved for 'later', and its licence click is still pending.  
Options: a: side rows only; EAC4 after the headline | b: side rows; click the EAC4 licence now | c: also feed MERRA-2 as a labelled input ablation  
Rec: **a: labelled input-advantaged, never pooled, never an input**

**Q47. Neural rivals?**  
Why: The only neural rival is NDVI's Kraft, scored on old rows. An MLP rival is listed in the ledger as your decision.  
Options: a: re-pair Kraft later; state no other deep model tested | b: also add an MLP rival later | c: drop Kraft  
Rec: **a: add an MLP later only if time allows**

**Q48. Do NDVI conformal intervals go in the headline?**  
Why: The NDVI conformal intervals were calibrated on 2020 and scored on 2021-23; no other problem has intervals.  
Options: a: drop; point predictions only, like the others | b: re-run on the new rows | c: keep the old ones as an earlier result  
Rec: **a: for the headline; c in the earlier-result text**

**Q49. Pre-register an NDVI row without those two regions?**  
Why: thar_desert and greece_mainland were used to pick the NDVI design, and both are test regions.  
Options: a: yes, from the saved rows | b: no  
Rec: **a: free, and answers the selection-on-test concern**

**Q50. How should defo report by forest pixels?**  
Why: Part 435 says defo results must be reported by forest2000_px stratum or above a floor.  
Options: a: forest2000_px quartiles | b: floor at >=1000 px | c: both  
Rec: **a: no threshold to pick**

**Q51. Calibration ratio 0.5-2.0: a flag only, or an eligibility gate?**  
Why: The defo link arms run at mean/truth 0.42-0.45, which would fail a 0.5-2.0 gate.  
Options: a: flag only | b: eligibility gate  
Rec: **a: no new rule after the rulings**

**Q52. Split defo into fire and non-fire loss?**  
Why: The defo target includes fire-driven loss; the scope doc asks for fire and non-fire loss to be split.  
Options: a: disclose only | b: fetch the GLAD fire layer and split  
Rec: **a: fire columns already lagged; gross loss is already disclosed**

## Fixes (76)

| # | Blocking | Issue | Fix | Where | Type | Effort | Waits on |
|---|---|---|---|---|---|---|---|
| F1 | yes | The draft's fix subtracts DAYS nanoseconds (the column is timestamp[ns]); C1 is still not coded. | Use dat < dat[gi] - np.timedelta64(DAYS,'D'); assert zero post-issue pool rows. | adaptation.py:2020, 2042 | leak | minutes |  |
| F2 | yes | At fire leads 3/6/12 the banks, correctors, router, clim and gmean fit on labels dated after issue. | Cut every fitted object at cut_L; filter donors after rs.choice; add month-level asserts. | adaptation.py:2827-2853, 2863, 2936-2977 | leak | hours |  |
| F3 | yes | --calib=full (the default) feeds test labels dated after issue at L>=2. | Under u2, fire accepts only --calib=strict and refuses full. | adaptation.py:197, 3043-3047 | leak | minutes |  |
| F4 | yes | Fire's adoption pick uses only the regions that pass a test-label variance filter (7 of 10). | Build fire's adoption surface from every region's inner rows. | adaptation.py:2679, 3166, 983-1015 | leak | hours |  |
| F5 | yes | The coral dbl2005 bank, spread RF, scalers and lead folds use donor labels up to Dec 2005. | Cut them at 2006-01-01 minus the lead (PM2.5 cut_L rule). | adaptation.py:1896, 1913, 1939-1943, 2022 | leak | hours |  |
| F6 | yes | Coral forecasts read population at the target year. | Build the POP columns at date minus lead, as coral_forecast77.py does. | adaptation.py:1836; rival_data.py:317 | leak | minutes |  |
| F7 | yes | Coral's NaN-fill medians use all donor rows, including those after the cut. | Fit the medians on training rows only, in rival_data too. | adaptation.py:1452-1455, 1844-1847; rival_data.py:318-322 | leak | minutes |  |
| F8 | yes | Forecasts reuse c and UB fitted up to 2019, which is after the early issue dates. | Cut c and UB at cut_L in every problem, as PM2.5 does for C_LOG. | pm25_adaptation.py:776; PM25_FORECAST_LADDER_PLAN.md:101 | leak | hours |  |
| F9 | yes | cropland_fraction is an MCD12Q1 slice; fire bans MCD12Q1 but not this slice. | Add cropland_fraction to fire_ban's MCD12Q1 group. | fire_ban.py:43-54 | leak | minutes |  |
| F10 | yes | Smoothing is undocumented for soi, pdo, tna, tsa, noi, ao, nao, pna, wp, epo, sam, iod and nino*. | Record each index's smoothing from PSL/CPC footers; an unknown index fails loudly. | ingest_noaa_indices.py:31-51; tier1_climate_indices.py:17-30 | leak | hours |  |
| F11 | yes | The nowcast engine has no oni/tni drop, and the fire_ban and defo lists lack them. | Add oni/tni to build_pool's BANNED (keep --keep-centred), fire_ban, defo opt-in flag. | pm25_architecture.py:218; fire_ban.py:32-38; defo_train.py:106-111 | leak | hours | Q2 |
| F12 | yes | The time-based bans live only in pm25_ban, so fire and NDVI miss the annual lag, snow-DOY, FREEZE and AMO/SPEI rules. | One leak_rule.py imported by every ban module; fire lags annual columns, bans rest. | pm25_ban.py:33-160; fire_ban.py:83; fire_ablate.py:52-58 | leak | hours | Q3 |
| F13 | yes | Coral's ENSO/IOD lag0 reads ~15 days ahead, and GHS-POP interpolates toward the next epoch. | Join ENSO/IOD on the last complete month; carry the last GHS-POP epoch <= cut. | coral_forecast.py:20-25, 187-194; coral_ghspop_ab.py:76-104 | leak | hours | Q3 |
| F14 | yes | Tier 1/UB read test or test-region rows (coral reads tst.y). | Read Tier 1 and UB from donor rows in coral, fire and defo. | adaptation.py:1702-1709, 2336, 1376-1380 | leak | hours | Q6, Q16 |
| F15 | yes | 19 of run89's 89 donor banks are ndvi_split test regions. | Never load D:/run89 models for NDVI; train a fresh donor bank. | D:/run89/trained/*.json | leak | minutes | Q1 |
| F16 | yes | pm25_ban lists V11 as conditional, so an arm that keeps conditional columns would feed the target in as a feature. | Copy V11 to y, always ban V11/V12, assert no NDVI/EVI column in X. | pm25_ban.py:81, 175-182; pm25_architecture.py:218 | leak | minutes | Q1 |
| F17 | yes | The engine feeds lag-0 GFED burn and silently skips the 6 NDVI regions with no GFED file. | Apply Q38's burn choice; fail loudly on missing GFED files. | pm25_architecture.py:76, 169-182 | leak | minutes | Q38 |
| F18 | yes | The coral nowcast is arcsine/raw only, with a fixed penalty, no trees-off and no N2 guard. | Port U2: link argument, trees-off, per-link placebo, 35-point grid, N2 guard. | adaptation.py:1572-1701, 670-734 | science | days |  |
| F19 | yes | The fire route lacks trees-off, the N2 guard, log(y+c) and a matched placebo, and reads its penalty from module globals. | Port U2 to fire: trees-off, guard, log(y+c), corr2, matched placebos, explicit penalty. | adaptation.py:2516-2651; fire_evt_arch.py:118 | science | days |  |
| F20 | yes | The engine reads the ACAG target and hard-codes PM2.5's split, tolerance, band and [0,UB] clip. | NDVI engine: y=V11 from panel, ndvi_split module, own tolerance/band, clip [-0.2,1]. | pm25_architecture.py:65-66, 101-108, 163-164; pm25_adaptation.py:132, 144 | science | days | Q1 |
| F21 | yes | Only pm25_forecast.py has a history block, and it is refused at lead 0. | Port history_block into the nowcast engine, shifted to end at t-1. | pm25_forecast.py:125-130; pm25_adaptation.py | science | hours | Q4 |
| F22 | yes | Fire's L>=2 history block ends at t-L-1, one month before the issue date. | Take fire's L>=2 history from row t-L+1. | adaptation.py:2911-2912 | science | minutes | Q4 |
| F23 | yes | Fire's forecast clim is raw under arcsine and includes the 2017-18 scoring years. | Apply D4 in run_fire_forecast too. | adaptation.py:2936-2940 | science | hours | Q6 |
| F24 | yes | run_defo_forecast has no corrector, placebo, trees-off or log arms, and no lead-0 path. | Write a new U2 defo forecast script with a lead-0 contract. | adaptation.py:1030, 1079-1095, 3200-3203 | science | days | Q7 |
| F25 | yes | The coral forecast route lacks the corrector, the penalty grid and trees-off. | Add corrector, penalty and trees-off to run_coral_forecast's route. | adaptation.py:1985-2056 | boilerplate | hours |  |
| F26 | yes | The fire forecast hard-codes arcsine, the corrector and the penalty, and has no normal, placebo, predict-zero, persistence or guard. | Pin fire's forecast tool to the nowcast adoption; add the baselines and N2 guard. | adaptation.py:2982-2996, 3055, 3099-3101, 3155-3173 | boilerplate | days | Q7 |
| F27 | yes | The PM2.5 ladder asserts log/log_corrector, hard-codes log1p and floors at 0. | The ladder accepts any adopted link/tool; NDVI clips at its own floor. | pm25_forecast.py:74-75, 310, 424, 476-483, 527-531, 580-629 | boilerplate | hours |  |
| F28 | yes | Under rollout, the grid cells are solved on a pool fed by the shipped-penalty predictions. | One date-ordered pass per (arm, penalty), or route only the adopted and shipped arms. | adaptation.py:1653-1671 | boilerplate | hours |  |
| F29 | yes | The glob 'coral_dbl*_fold*' mixes dbl2010, full/rollout and suffixed fold folders. | Make fold_decision's glob match calib, root and cut exactly. | adaptation.py:691-693 | boilerplate | minutes |  |
| F30 | yes | The coral lead folds carry the post-issue leak, and only rollout_L12 exists (G5). | After F1, re-run the 5 donor folds and rollout at all 4 leads. | CLAIMS_LEDGER.md:410-414; QUESTIONS_ROUND3_HANDOFF.md:513-515 | boilerplate | hours | Q29 |
| F31 | yes | Fire's --lead=0 falls through to run_fire, and the forecast rows differ, so no lead-0 contract exists. | Build a fire lead-0 contract, or replace the stage-4c gate. | adaptation.py:3189, 3203, 2848, 2862 | boilerplate | hours |  |
| F32 | yes | Fire scores 59,829-59,858 rows per lead but 59,892 in the nowcast. | Score one common row set at every lead and in the nowcast; assert it. | adaptation.py:2862; Part 527 | boilerplate | hours |  |
| F33 | yes | Fire's forecast arm caches reload whenever the row count matches, and the output root is hard-coded. | Add --root and a config+code fingerprint check to arm_load. | adaptation.py:139, 241, 3079-3092 | boilerplate | hours |  |
| F34 | yes | np.vstack(A[:nh][idx]) loads the whole history into RAM (~2x 4.6 GB). | Use the forecast path's 20k-row block copy. | adaptation.py:2625, 2634, 3123-3135 | boilerplate | minutes |  |
| F35 | yes | The tree-matrix memmap is written one column per tree, which breaks rule R2. | Write the tree matrix in row blocks in route() and fill(). | adaptation.py:2589, 2994 | boilerplate | minutes |  |
| F36 | yes | There are no lag-1 placebo banks, and defo_tier2.py has no lead option. | Add --lead to defo_tier2.py and build the L1 placebo banks. | defo_tier2.py; D:/defo_tier2/banks | boilerplate | hours |  |
| F37 | yes | Defo bank paths carry no column-set tag, and the build skips files that already exist. | Tag bank paths by feature set, write to a new folder, assert columns. | defo_corrector.py:112-124, 154 | boilerplate | minutes | Q2 |
| F38 | yes | Retrained banks lose the cached-array gate, and nothing proves the rebuild path reproduces the shipped banks. | Rebuild one donor bank on the old columns; assert it equals the shipped pickle. | defo_corrector.py:139-175 | boilerplate | minutes | Q2 |
| F39 | yes | The defo bank recipe depends on several answers; settling them one at a time means rebuilding twice. | Settle Q2, Q3, Q12 and the F10 audit, then rebuild the banks once. | D:/defo_matrix parquet | boilerplate | minutes | Q2, Q3, Q12 |
| F40 | yes | G2 is approved, but defo_g2_corr2.py does not exist; the inner arrays are already cached. | Write and run the read-only G2 script; its pick becomes defo's harm baseline. | QUESTIONS_ROUND3_HANDOFF.md:495-498; D:/adaptation/defo/_addarm.log | boilerplate | hours |  |
| F41 | yes | The --expect-from check against Parts 556/558 fails once oni/tni are dropped. | A keep-centred smoke must equal u2_smoke; then a trees-off inner match vs Part 558. | pm25_adaptation.py:872-890 | boilerplate | hours | Q2, Q8 |
| F42 | yes | The verdicts print HELPS on CI>0 alone and check HURTS before the band (4 functions). | All verdicts: check the band first; HELPS needs the point estimate at or above it. | adaptation.py:540; pm25_adaptation.py:1104-1115; pm25_rivals.py:621 | boilerplate | minutes |  |
| F43 | yes | PM2.5 arms go negative (160 and 520 test rows) and are never clipped. | Clip PM2.5 arms at 0 in run_arm and the ladder; log pre-clip counts. | pm25_adaptation.py:715-768; pm25_forecast.py:527 | boilerplate | minutes | Q6 |
| F44 | yes | The lead-0 contract was shown on Part 560 code, with oni/tni kept. | Re-run the lead-0 contract on the final code against the new clean nowcast. | pm25_forecast.py:46; Parts 560, 562 | boilerplate | minutes | Q5 |
| F45 | yes | Ruled in Part 559: one placebo run at L12. pm25_forecast.py still has placebo=False. | Run the PM2.5 placebo once at L12 (~2.4 h). | pm25_forecast.py:229 | boilerplate | hours |  |
| F46 | yes | The coral, fire and defo _preds.npz files hold only y and the arms, with no row keys or normals. | Save keys, lead/issue, normal, clim, pre-clip and inner predictions for every row. | adaptation.py:962-963, 1370, 3094-3097; anomaly_r2.py:121-136 | boilerplate | hours |  |
| F47 | yes | No engine computes the adopted-vs-normal CI, and nothing cross-checks the table against the engines. | headline_table: corr2, ratio, adopted-vs-normal CI; reproduce verdict MAE; assert same rows. | adaptation.py:920-926; pm25_rivals.py:667, 681 | boilerplate | hours |  |
| F48 | yes | R0 skips the defo_L1 caches, defo banks, run89full and all input stores, and no backup exists yet. | Back up those; hash every input store; each run asserts the hashes. | UNIFORM_SCHEMA_PLAN.md:141-145 | boilerplate | hours |  |
| F49 | yes | There is no git, and adaptation.py and pm25_adaptation.py stamp no code hash. | SHA-256 every headline script at sign-off; stamp in verdicts; edits = bug-fix Part. | pm25_forecast.py:732 (the only one with a hash) | boilerplate | hours |  |
| F50 | yes | The sklearnex import silently falls back to stock sklearn, whose trees differ. | Fail loudly if sklearnex is missing; stamp the backend and versions. | fire_architecture.py:66-70; coral_architecture.py:58-62 | boilerplate | minutes |  |
| F51 | yes | Fire's split is rebuilt from a glob plus a size ranking, and its test cells come from default_rng(7). | Write each problem's test regions, cells and row counts to files; runs assert. | fire_architecture.py:236-246; adaptation.py:2297, 2861; pm25_split.py:55 | boilerplate | hours |  |
| F52 | yes | Results change with thread counts: BLAS is unpinned and coral uses n_jobs=-1. | Pin --jobs and BLAS threads to the shipped values; record them in the stamp. | coral_architecture.py:294, 305, 409; defo_corrector.py:83 | boilerplate | minutes |  |
| F53 | yes | The shipped folders hold Parts 558/561, and the engine's default root is D:/pm25_adapt/full. | One fresh headline root for every run; never pass --force. | pm25_adaptation.py:145, 148; UNIFORM_SCHEMA_PLAN.md:23, 63 | boilerplate | minutes |  |
| F54 | yes | The NDVI test matrix is ~39.5 GB, against 53 GB free on D: and 23 GB on C:. | Run a disk pre-flight before NDVI runs; keep R0 backups off D:. | pm25_adaptation.py:225 | boilerplate | minutes | Q1 |
| F55 | yes | No NDVI result exists on this engine to reproduce. | Gate: the changed engine still reproduces PM2.5; NDVI trees-off equals its normal. | HEADLINE_RUN_PLAN.md:77 | boilerplate | hours | Q1 |
| F56 | yes | The pre-registration says '<=2019, every object obeys it', which is false for fire (2018) and for coral. | Pre-reg: per-problem windows and cut-offs; coral main space-only; list every dropped column. | HEADLINE_RUN_PLAN.md:89-98 | boilerplate | minutes | Q3, Q10 |
| F57 | yes | The pre-registration omits the forecast pin rule, the band used at leads, the full baseline list and the reading rules. | Add pin-per-lead, the nowcast band at every lead, full baselines, UNIFORM reading rules. | HEADLINE_RUN_PLAN.md:89-104; UNIFORM_SCHEMA_PLAN.md:200-222 | boilerplate | minutes |  |
| F58 | yes | Some choices already rest on test numbers: the burn block, lambda=100, the 2018 cut, H1 and the cascade. | Add a per-problem table of every choice made after test numbers were seen. | CLAIMS_LEDGER.md:243, 610, 684-688 | boilerplate | minutes |  |
| F59 | yes | The verdict uses the region-mean contrast while the headline MAE is pooled, so the signs can differ. | State the verdict contrast, print pooled beside, flag sign flips; summary = full grid. | adaptation.py:535-537; HEADLINE_RUN_PLAN.md:99-104 | boilerplate | minutes | Q20 |
| F60 |  | Disclosures that are ruled or needed are absent from the pre-registration. | Disclose for all 5: perfect-latency hindcast, A6 #2, old-bank penalty, defo lambda centre. | PM25_FORECAST_LADDER_PLAN.md:83; QUESTIONS_ROUND3_HANDOFF.md:114-126; Part 509 | boilerplate | minutes |  |
| F61 |  | Errata rows that were ruled for disclosure are missing from HANDOFF_ERRATA.md. | Add rows for the oni/tni look-ahead and the fire issue-date leak; update rows 8.12 and 12.2. | HANDOFF_ERRATA.md:25, 30; Part 557 | boilerplate | minutes |  |
| F62 |  | The old headlines carry look-ahead columns, and the fire lead loss is quoted from a test-picked arm. | Errata: name each old headline's look-ahead columns; fire lead loss ~38%. | lead_report.py:135; CLAIMS_LEDGER.md:470-472 | boilerplate | minutes |  |
| F63 |  | The level-shift rationale is wrong algebra, and it appears in the code comments and the ledger. | Fix the level-shift wording in the comments and ledger per Q42. | pm25_adaptation.py:74-76, 276-277; pm25_driver_screen.py:84-90 | boilerplate | minutes | Q42 |
| F64 |  | PM2.5 is missing from TIER1_ACTUAL, and the audit rows are stale. | Add PM2.5 to TIER1_ACTUAL; fix the stale hurdle=True and defo 'poisson' rows. | adaptation.py:393-404; tier1_audit.py:48-53 | boilerplate | minutes |  |
| F65 |  | The rivals were paired with the L1 nowref, and the old rival files are paired only by row order. | Re-pair rivals on the new nowcast: shared climatology, same columns, assert row order. | pm25_rivals.py:153; rivals.py:646-652; rival_data.py:119 | boilerplate | hours | Q44 |
| F66 |  | Pooled coral scores mix survey programmes; on Reef_Check, predict-zero wins. | headline_table prints coral per survey programme, with predict-zero beside each. | CLAIMS_LEDGER.md:387-391 | boilerplate | minutes |  |
| F67 |  | The main-split DHW score is not row-paired, and the CRW Outlook was scored only on the old leaky path. | Coral: a row-paired DHW row on the main split, and the CRW Outlook leak-free (C11c). | rival_data.py:53, 309; QUESTIONS_ROUND3_HANDOFF.md:472 | boilerplate | hours |  |
| F68 |  | The default --cut is 2010, so a command without it silently runs dbl2010. | Pass --cut=2005 on every coral fold and dbl command. | adaptation.py:170 | boilerplate | minutes |  |
| F69 |  | The coral forecast route uses undefined names on a rare path, and the rollout log miscounts predicted slots. | Coral: fix the undefined names at 2035-2037 and the 'predicted slots' log count. | adaptation.py:1650, 2035-2037, 2044 | boilerplate | minutes |  |
| F70 |  | Fire: --sweeponly can still adopt, the report prints a test-chosen cascade line, and deletes swallow errors. | Fire: refuse --sweeponly under u2; drop the cascade@5% line; gc before loud deletes. | adaptation.py:2658-2707, 295-299, 2925-2930, 3139-3152 | boilerplate | minutes |  |
| F71 |  | The vod_anom normaliser is built from VOD up to 2018, which is after the issue date at leads >1. | Disclose it as a minor normaliser look-ahead, or rebuild it at cut_L. | fire_join_drivers.py:62, 206-217 | leak | minutes |  |
| F72 |  | Several small defo code and reporting gaps. | Defo: build-only exit, refuse cache rewrites, fix Poisson docstring, print region-out values. | defo_corrector.py; adaptation.py:1322-1332, 427-428; Part 509 | boilerplate | minutes |  |
| F73 |  | pm25_adaptation.py cannot resume, so a crash restarts a 7-14 h run from zero. | Add stage-level resume keyed on a config+code fingerprint. | pm25_adaptation.py:1160-1186; pm25_forecast.py:380-402 | boilerplate | hours |  |
| F74 |  | The NDVI earlier-result text has undisclosed caveats. | NDVI text: earlier-result caveats, fc12 not issue-cut, DGVMs, monthly oracle gap. | CLAIMS_LEDGER.md:63, 347; cross_region_run89.py:1001; Part 426 | boilerplate | minutes |  |
| F75 |  | The Kraft scorer silently skips any region with a missing file. | ndvi_kraft scoring fails loudly on a missing region. | ndvi_kraft.py:402-411 | boilerplate | minutes |  |
| F76 |  | UNIFORM's D1-D10 labels collide with ROUND3's ruled D1-D5. | Rename UNIFORM's held choices to U1-U10. | QUESTIONS_ROUND3_HANDOFF.md:474-479 | boilerplate | minutes |  |

## What the first draft (HEADLINE_RUN_PLAN.md) got wrong

- F1 as written does nothing: the date column is in nanoseconds, so it needs np.timedelta64(DAYS,'D').
- Fire row: tests 2019-22 with history up to 2018 (204 rows per cell), 30 donors. The 'SPEI/AMO end 2023' reason is wrong; fire's data ends in 2022.
- PM2.5 row: the nowcast uses 204 rows per cell (203 is the L1 figure); the leads use 205-2L.
- PM2.5 baselines leave out the tying last-5-years normal and EAC4. There is no ladder placebo yet (ruled: one run at L12).
- NDVI row: 204 rows per cell under the PM2.5 engine, not 216. 2020-23 is not comparable with +0.32 (2021-23, macro, clean-25).
- Coral row: dbl2005 is doubly blocked (donors up to 2005, tests after 2005), not a time split. Main rollout has no own labels.
- Coral 'printed beside' leaves out the real CRW Outlook (ruling C11c).
- Defo row: the normal is a per-cell annual mean, not cell x month. It scores 4,000 cells per region (265,924 rows).
- Section 3: the UB rule reads NDVI as unbounded (no arcsine); log(y+c) and the [0,UB] clip fail on its 8% negative rows.
- Sections 3/6: N2 declines to trees-off (a k=50 ridge on coral, a per-region constant on defo), not guess-normal.
- O1(a): REMOVE-11 lets look-ahead back in. The port also changes the model: 435 lag/roll features lost, bank 44,500 to 8,900 columns.
- O1: '25 of 44' holds only under ndvi_split.txt; the split ruling is still open.
- O2(a) cost is wrong: the defo banks and fire pool carry oni/tni, so defo must rebuild and fire's gate breaks. The forecast half is already ruled.
- O3: option (c) 'nowhere' would reverse the Part 561 ruling. Fire's L>=2 history ends at t-L-1, not at the issue month.
- O4: D7's c is already ruled (D1), D8 is moot, D10(b) needs new fold code, and D9 never considered NDVI (+-0.02 is rule R1).
- O5 is mostly ruled: PM2.5 1/3/6/12 and coral's four leads. Only NDVI's leads are open.
- O6(a) cannot run on coral (per-cell MOS needs history), and Board H failed its guard.
- F4: 'amo smoothed?' is already answered (unsmoothed; ends Jan 2023). The index list misses tna, tsa, noi, ao, pna, wp, epo and sam.
- F4 misses fire's annual lag-0 columns, snow-DOY, FREEZE and cropland_fraction; NDVI's V20/V04/clf/co2; coral's ENSO lag0 and GHS-POP.
- F5/F8 miss the coral forecast corrector, penalty and trees-off. Defo forecast is about 1 day of work, not 'medium'.
- F7: there are four verdict functions. pm25_forecast already follows R5; pm25_adaptation also gets HELPS wrong.
- F10/R0 misses the defo_L1 caches, the defo bank folders, D:/run89full and every input store; no backup exists yet.
- Stage 0: sign the pre-registration after the 5 smokes pass, not before.
- Stage 1: pm25_rescore_u2.py does not exist and is moot if the nowcast is re-run. G2 does choose something (it re-decides defo's arm).
- Stages 2/3b/3c/3e: the gates cannot hold once features change, and no NDVI result exists on this engine to reproduce.
- Stage 3d: the nowcast gate is --expect-from, not the lead-0 contract, and pm25_adaptation has no oni/tni switch.
- Stage 4a leaves out the lead-fold re-runs and rollout at the leads, and the contract fails at every lead once F1 lands.
- Stage 4b: the cached lead-1 defo banks carry oni/tni, and there is no defo lead-0 path or L1 placebo bank.
- Stage 4c: fire has no lead-0 contract (--lead=0 goes to run_fire).
- Stage 4d: 'diff 0 shown' was on pre-Part-562 code with oni/tni kept. Time is ~15-23 h, not 12-13 h.
- Section 6: 'every fitted object obeys the cut-off' is false for coral and for the pinned forecast arms. 'No look-ahead' stays false until the leak fixes land.
- Section 2: fire anomaly-R2 cannot be built from today's saved rows (no keys; anomaly_r2.py is a stub).
- Section 8 totals leave out the PM2.5 ladder rate, coral rollout at the leads, the L12 placebo and the defo bank rebuild.

## Dropped (already ruled, duplicate, or refuted)

- pm25-Q2: already ruled (Part 561): H1 is the headline, disclosed post-hoc, with Part 561 printed beside.
- pm25-Q4 / cross-Q11: already ruled (Part 559): one placebo run at L12, now fix F45.
- ndvi-Q5 / cross-Q6: already ruled (rule R1): NDVI keeps +-0.02.
- coral-Q5 / cross-Q18: already ruled (C10a): coral forecast cells use dbl2005.
- coral-Q11: duplicate of O4/D5.
- coral-Q12: this is O4/D10, folded into Q6.
- cross-E7 (NDVI gets arcsine): refuted; the UB rule reads NDVI as unbounded.
- pm25-F5: moot if Q9=a (the PM2.5 nowcast is re-run).
- pm25-F10 / pm25-F11: run commands, already covered by stages 3d/4d.
- pm25-F15: duplicate of draft F10 (R0).
- leaks-F11/F12/F13: duplicates of draft F1/F2/F3 (now F1, F14, F2).
- fire-F2: merged into F2 (filter after the draw).
- defo-F3: duplicate of Q2(a).
- ndvi-M2: not a real choice (the run89 size does not fit on D:); moved to a draft correction.
- pm25-F17, pm25-F18, defo-F16, crit-F15, cross-F13: moved to draft corrections.
- Merged into Q2: leaks-Q2, leaks-Q3, cross-Q2, defo-Q1.
- Merged into Q3: leaks-Q1, leaks-Q4, leaks-Q5, cross-Q3, skeptic-Q1, coral-Q7, coral-Q8, defo-Q3.
- Merged into Q4 + F22: pm25-Q3, fire-Q3, cross-Q10.
- Merged into Q8: fire-Q2, defo-Q2, cross-Q12, leaks-F7.
- Merged into Q7: coral-Q6, fire-Q4, defo-Q6.
- Merged into Q14/Q15: fire-Q5, coral-Q10, cross-Q7, cross-Q19.
- Merged into Q18: coral-Q9, fire-Q6, cross-Q21.
- Merged into Q11: defo-Q4, defo-Q5.
- Merged into Q1: ndvi-Q1, ndvi-Q2, cross-F15.
- Merged into Q33: ndvi-M1, cross-Q20. Q34: ndvi-Q3, leaks-Q6. Q36: ndvi-Q4, cross-Q4 (options fixed). Q37: ndvi-Q6, cross-Q5.
- Merged into Q20: ndvi-Q10, cross-Q14. Q26: pm25-Q5, cross-Q15. Q27: pm25-Q13 (reframed). Q40: cross-Q8. Q49: ndvi-Q11, cross-Q9.
- Merged into Q42 + F63: pm25-Q11, pm25-Q14. Q43: leaks-Q7, pm25-F3 base periods.
- Merged into Q44-Q47: cross-Q16, pm25-Q7/Q8/Q9/Q10/Q12, cross-Q17, crit-Q7, ndvi-Q12.
- cross-Q13: reframed as Q22 (the N3 band rule is already ruled).
- skeptic-Q2: wording only; folded into F56.
- fire-F20: folded into Q6 (the D4 run replaces R3/Q4, with your OK).
- fire-F15 / defo-F11: not leaks; merged into F14.
