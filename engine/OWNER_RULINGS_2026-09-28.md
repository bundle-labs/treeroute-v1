# Owner rulings, 2026-09-28 (evening): the owner accepted the recommendations

These rulings approve the proposed science signatures, so bodies may now be written for them. Where a row below differs from a docstring in `treeroute/_proposed/`, this file wins.

## A. Science signatures (engine/SIGNATURES_FOR_REVIEW.md)

- **All 101 decisions (D1-D101):** the PROPOSED default is accepted wherever the checklist proposes one. The rows below cover the decisions that had no default, or where the recommendation differed from the proposal.

| Decision | Ruling |
|---|---|
| D74 single_verdict | The ruled R5 rule (pm25_forecast.py:321-344). **HELPS:** the CI low end is above 0 AND the point estimate is at or above +band. **HURTS:** the CI high end is below 0 AND the point estimate is at or below -band. **EQUIVALENT:** the whole CI lies inside +-band. **IDENTICAL:** every contrast is 0. **CANNOT TELL:** everything else. |
| D54 LabelView.asof_rows | Option (a): each test row's history and persistence read the labels known at THAT row's issue step, served before the pass's adoption lock. decide() never sees test rows. |
| D93 check_g_derived rows | Follows D54 (a): the sample spans every row. |
| D25 compute_lag (9.1 item 3) | Option (a): on an annual target, same-year annual values stay at lag 0 unless their facts reach past the target year. |
| D15 thin flag | Count the NON-tree router columns only. |
| D51 check_oob_share | A statistical bound, not a hand number: \|observed - expected\| <= 5 x sqrt(p(1-p)/n). Here p is the expected held-out share for the bag size and n is the home group's row count. |
| D79, D92 sample checks | A stride sample of 1,000 rows (all rows if fewer), with a relative tolerance of 1e-9. |
| D95 check_g_range | Refuse if more than 0.1% of a column's non-missing values fall outside its legal range; otherwise flag and print the count. |

## B. Index and target timing (engine/datasets/_stores/INDEX_WINDOW_AUDIT.md)

| Item | Ruling |
|---|---|
| R-A (ERSSTv5 filter) | (a) Lag by the content reach of +2 months: nino* and the 8 sst_anom_* get lag 2, oni gets lag 3, and all 13 get 1 year on annual aggregates. Plan 3.2's "oni 1 month" becomes 3. |
| R-B (tni) | Sign the bound `{7, month, centred}`: lag 3. |
| R-C (co2) | (a) `window {3, month, centred}`, assumed: lag 1 month, and 1 year on annual aggregates. |
| R-D (fire detection window) | (b) Add a reach-after fact; R17 starts fire's history block at t-2, as for NDVI. This is a new acceptance flag. |
| R-E (PSL footers) | Authorised: read the 13 footers (read-only web pages, nothing saved) to record the base periods. |
| Item 6 (vintage pin) | Keep the current snapshots, as hashed. |
| Item 7 (filters inside input analyses) | Disclose, do not lag. |
| Item 8 (schema) | (a) Add `reach_after_max` / `reach_before_max` to the store window fact. |

## C. Build choices (groundwork reports)

| Item | Ruling |
|---|---|
| Fire golden | Run it with >= 8.5 GB free RAM (close the browser first); command in legacy_harness/README.md. Hashes go in goldens_v3.json. |
| Defo store | Rebuild defo's yearly columns from the monthly panel with the package's feature script (aggregate_time). Do not read D:/defo_matrix's target copy, train/test flag or pre-lagged columns. |
| ban.yaml | Keep the forced-bans-only placeholder until the Q34 review. |
| Fire cells | The R18 stride over all cells. Disclose that the shipped 1,000-cell pick cannot be regenerated (its seed used Python's string hash). |
| Speed | Speedup 2 with the finiteness scan once per block, option (a) of SPEEDPROOF_REPORT.md open item 1. Add version pins and a guard test. |
| sklearnex | Patch globally at start-up, as the shipped runs did. |
| Region-router threads | A 4-thread mode for the pooled region solve, with a 1e-9 match tolerance against its golden. |
| Reach across a step edge | Same as B item 8: add `reach_after_max` / `reach_before_max`. |

## D. Split design (owner, 2026-09-28 night): LEAVE-ONE-REGION-OUT, same total test cells

- **No hand-made donor/test split.** Every group gets its own specialist trees, trained on its rows up to the donor train end. Every group is tested. A unit's router never sees its own group's trees, which are dropped as columns. Everything else is unchanged: the time split, the router on the unit's own history, and the issue-date cuts.
- **Test units:** the same TOTAL as the old hard split, spread over all groups. The generic rule and its engine constant are written into APP_PLAN.md and are for the owner to sign. The region router keeps enough rows.
- **This replaces:** the hand-set split.yaml test set (split.yaml keeps only exclusions and seen_during_design), and "100 cells per region" (Q39 a).
- **Free continuity row:** the old hard-split test groups are also reported alone, from the same run.
- **Rivals:** see APP_PLAN.md (Q44).
  - Own-history rivals (normals, persistence, per-cell MOS) need no retraining.
  - Gauged global models (trained on every group up to the cut, own history included, which is the same information the router gets) are trained ONCE.
  - Donor-only rivals are trained on region folds (10), and each group is scored by the fold model that never saw it. This is disclosed.

## E. Leave-one-region-out details (owner, 2026-09-28 night: accepted the recommendations; APP_PLAN.md 9.1 L1-L7)

| Item | Ruling |
|---|---|
| L1 scored-unit budget | One engine constant, K = 20: scored units per group = max(10, floor(20 x R18 count / G)), capped at the units available. That gives PM2.5 15 per group, fire 50, defo 2,040 and NDVI 15. The old totals are shown beside it, and the departure from "same total" (fire x2, NDVI x0.45, defo x1.22) is disclosed. |
| L2 companion rules | Yes, all five: (1) banks keep the R18 count (100 units per group; 4,285 on the region kind); (2) the region router keeps its 60,000-row budget of whole units, decoupled from the scored units, which are an evenly spaced subset; (3) the fallback region router pools the group's bank units; (4) OVERLAP BLOCKS -- groups that share cells are dropped together, so a router drops the trees of its whole overlap block; (5) Type-3 services answer only through the own-block-masked gateway. |
| L5 GLS weights, c, s | Weights: out-of-bag sigma (each tree's held-out rows), about free. c and s: accept them as specified (history up to the cut is allowed). |
| L6 A7 under LORO | Option b: for the inner decision, refit the bank (and correctors) at the INNER cut, so it has no rows after the inner-fit end (about +5-6.6 h over the four nowcasts). |
| L7 old test lists | Move them out of split.yaml into legacy_harness/ and treeroute_report/, so split.yaml holds only exclusions and seen_during_design. |
| L4 defo region Gram | Yes: share each group's region Gram across its 3 links, gated by byte identity (saves about 3 h). |
| L3 rivals (M8) | Deferred to M8; the plan's defaults stand for now. |
| Fit-build small approvals (recommended the same evening) | Approved: check_oob_share takes n_group_rows (D51 needs it); no fold banks under LORO; the store's group check reads the grid's own unit-to-group keys; the two docstring fixes ("every tree not owned by the rows' group"; DonorRows in ascending grid order); corrector weight 1.0 (R24); the constants D51 5 sigma, D52 50 rows and the block size 12,288 move into engine_constants.py. |

## F. Tuesday-build follow-ups (owner, 2026-09-28 night: accepted the recommendation)

| Item | Ruling |
|---|---|
| F1 history-block fallback leak | Leak-free fallback. A missing history value takes the unit's AS-OF season mean (labels strictly before the row, within the cut), then its as-of all-season mean, then the donor-row mean at the cut. Never 0, never a label at or after the row. |
| F2 coverage end (R3) | Count only rows that have BOTH a valid label AND the kept drivers present (the joined rows). This is generic, and it gives defo 2023. |
| F3 first year (Y0) and the tree-cover trio | Follow the shipped verdicts through the Q34 review (PM2.5 and fire did not use V15/V17/tree_cover_pct), so Y0 stays 2003. No engine change. |
| F4 index facts | Merge the stamp with the ruled window for co2 and the 8 sst_anom_* columns, so the rulings come out right: sst_anom_* lag 2, co2 lag 1. |
| F5 aggregate_time | Must build its output facts with the new timing helpers (the ruled 1-year annual lags must survive aggregation). |
| F6 join_coarser_column | Pass explicit arrays of unit codes and coarse periods. |
| F7 unknown-alignment bound | The safe reading: a signed bound runs forward from the stamp (a 5-month bound gives lag 5). |
| F8 smaller sign-offs | Accepted. They cover: the six new refusals; R8 skips epoch and irregular columns; the empty-lag-map guard reading; R23/R28 stay in layer; R1 reading grids keyed by a date column; the history column names; declared-absent groups allowed silently; steps other than 1 month / 1 year / composite are refused until ruled; reach is measured from the window edge. |
| CLI help encoding | Fix, so the help tests pass under PowerShell's default encoding. |

## G. Ladder: missing router context at long leads (owner, 2026-10-05: accepted the recommended option)

| Item | Ruling |
|---|---|
| G1 empty context on fit rows at a lead | Option (a), generic for every package: at each lead, a FIT row whose router context (read at the lead's issue step) is missing or non-finite leaves that lead's router fit, exactly as a row with a missing label does (R30). The count per unit and per lead is printed, and flagged above 5% of a unit's fit rows. Nothing is filled or invented. Scored rows with missing context still REFUSE loudly. The kernel's R20 refusal stays as the last guard. (Trigger: NDVI lead 12, where three lagged-driver context columns need 2001 data on early-2003 fit rows.) |

## H. Coral track and forecast-ladder rules (owner, 2026-10-05: accepted the recommended rules for the coral track and the forecast ladder)

| Item | Ruling |
|---|---|
| H1 coral | Option (b): finish and run the four grid problems first. Coral (neighbour router, events, leave-one-ecoregion-out) is built RIGHT AFTER, with its OWN pre-registration Part before its run, during the writing period. |
| H2 lead guard (departure ladder_guard_bank) | L6 b applies at every lead. Each lead refits its bank and correctors, and builds its guard history block, at the lead's GUARD cut, so no guard row sits inside a bank trained on its labels. One more bank per lead; plan 4.5 hours are re-priced. |
| H3 router context at a lead (departure ladder_readings b) | Approved as implemented: the router context moves to the issue step with the whole feature row. |
| H4 missing issue row (departure ladder_readings c) | CHANGED: a test row whose issue-step features are missing is LEFT OUT of scoring, saved with a flag, and counted per unit and lead. It is never scored on NaN features. |
| H5 fallback level at a lead (departure ladder_readings d) | Follows H2: each lead searches its own fallback level on its own guard surface, instead of reusing the nowcast's. The lambda centre is used below 10 fallback units, as before. |

## I. Lead set (owner, 2026-10-05: asked for the nowcast and the 6- and 12-month leads, and no other lead)

| Item | Ruling |
|---|---|
| I1 leads | The engine's lead constant (R10) becomes 6 and 12 months, generic for every package, plus the nowcast (lead 0), which always runs as the contract. This replaces 1/3/6/12 (Q41 a and the plan's lead list). On annual data both leads round to 1 year and merge (defo: nowcast + 1 year); events (coral track) use 183 and 365 days. The pinned placebo stays at the longest lead (12 months). Re-price plan 4.5 (fewer forecast passes) and update expected_derived.json and the ladder tests. |
