# Why the layer picked arcsine + corrector + GLS on coral, and why it lost on test (POST-HOC)

2026-10-21. Post-hoc diagnosis (workflow <id>-d62: noise, drift and gap analyses, an explanation agent and a skeptic; the skeptic's corrections are applied). Nothing here changes the pre-registered headline. Scripts and outputs: gap\, noise\, drift\, explain\ in this folder.

## Answer

1. **On the 2013-15 decision surface, GLS beat its unweighted twin by only 0.077 MAE (7.210 vs 7.287).**
   - The edge was small but STABLE: GLS won in 98% of group and block resamples, in all three surface years, and mostly on reefs with no bleaching.
   - The rule takes the strictly lowest MAE with no tie zone, so it adopted GLS correctly by its own rule.
2. **On test, unweighted was 9% better (6.147 vs 6.698).** The whole reversal sits in the 2016 Indo-Pacific mass bleaching (McClanahan, 189 rows, all 2016): 130% of the gap. Without McClanahan, GLS wins (4.173 vs 4.353).
3. **The mechanism (shown by association and dose-response, not by a re-solve).**
   - In those reefs, the neighbour pools held past mass-bleaching reefs: Donner 2010 (359 pool slots), 1998 (155) and 2005 (41).
   - GLS gives low weight to neighbours that other regions' trees predicted badly, and these were mostly those past events. Their pool weight fell to about 0.24 of the pool mean, so they weighed roughly 4 times less.
   - Severe test reefs (truth about 75%) were then predicted at about 22% by GLS against 35% by unweighted (all 140 severe rows; McClanahan severe rows: 25.8 vs 41.5, truth 77.2).
   - The unweighted-minus-GLS gap on severe rows rises with the pool's share of severe neighbours: 1.2, 9.2, 13.1, then 21.4.
4. **Why the surface could not warn.** It had as many severe reefs (6.0% vs 6.1%), but they were mostly Florida 2014-15, with almost no past mass-bleaching neighbours in their pools.
   - Rows with severe neighbours and a severe outcome: 16 on the surface against 105 on test.
   - On the surface both arms predicted severe reefs the same (14.4 vs 14.3).
5. **NOT a weight-model drift.** The fold models and the test-pass model share the same donor cutoff (2012-12-31). Their sigmas correlate 0.996, and re-weighting the test pools with the fold models gives nearly the same result.
   - The earlier chat guess, that "the final model's GLS weights were relearned with 2014-15 data", is WRONG and is withdrawn.
6. **NOT a bug and NOT sampling noise.** It is a shift between the decision surface and the test window that the surface did not contain.

## Options for a next engine version (owner decides; post-hoc, fitted to one failure; must be pre-registered before any new run)

- **A.** GLS must beat its unweighted twin beyond a decision-time band; otherwise use the unweighted twin. On the saved runs this would change only coral. Testing it on coral is circular.
- **C.** Stability flag: re-run the rule on group-resampled surfaces and flag when the pick wins in under 50% of draws. It flags only coral (29%; pm25 93%, ndvi 97%, fire 84%, defo 88%). That instability is mostly arcsine vs log_c, not GLS vs unweighted.
- **E2.** A label-free test-pass flag: alarm when the pick and its twin disagree on test far more than they did on the surface. Coral 4.3x; the others 0.9-1.2x. It needs no test labels, so it can run before the labels open.
- **E3.** Always save pools_*.parquet, so pool-composition shifts can be checked (today only coral saves them).
- **Not recommended:** a broad "simplest arm" rule (it changes 4 of 5 picks for the worse); a severe-row check (it would not have saved coral and would hurt fire); a weight-drift check (it checks the wrong thing).
- **Note:** every problem's picks sit on a penalty-grid edge, so an edge warning tells the problems apart not at all.
