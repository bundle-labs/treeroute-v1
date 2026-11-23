# AUDIT_CHECKLIST -- defo package

The human checks that no code can do (APP_PLAN.md 1.2, 'AUDIT_CHECKLIST.md'). **UNSIGNED.** Drafted by the agent on
2026-09-28 from the repo and the plan; every box is open until the owner ticks it and signs at the bottom. Evidence
pointers are where to look, not conclusions.

| # | Check (plan 1.2) | Where to look | Done |
|---|---|---|---|
| 1 | Target lineage and co-products | Hansen GFC-2025-v1.13 lossyear -> loss_frac. forest2000_px comes from treecover2000, a co-product of the same model run: never a predictor, report stratum only (Q50). The MOD44B triple (V15 + V17 + tree_cover_pct = 100) is banned on the sheet (defo_ban.py:34). D:/defo_matrix also carries y, an exact copy of loss_frac (defo_matrix.py:282-283; max difference 0.0 over 42 groups, measured 2026-09-28), and land_px (Hansen datamask count): declared as target_twin / support with forced bans in ban.yaml. | [ ] |
| 2 | Fill codes | D:/defo_matrix inherited the panel's NoData sentinels in 27 columns, inside its annual aggregates (defo_train.py:135-139): disclosed in exceptions.yaml (rebuild declined, HEADLINE_RUN_PLAN.md:144). | [ ] |
| 3 | Compositing-window dating | Loss is detected primarily in its year; late-year losses can be labelled the next year (index_facts.yaml). | [ ] |
| 4 | Product vintages | GFC-2025-v1.13 pinned (defo_fetch.py:21-22, 41): each GFC release re-derives loss years with later imagery. | [ ] |
| 5 | Split design | Forested groups (forest_census frac_tc30 >= 0.25) intersected with the NDVI split; all 42 forested groups are used (25 donors / 17 tests). D:/defo_matrix carries a split flag, is_train = (year <= 2019), from the hand-set TRAIN_END (defo_matrix.py:79, 287): banned (G-KEYS); the engine derives the train end by R6. | [ ] |
| 6 | The unit definition (as delivered) | 4 km panel cells; 30 m Hansen pixels aggregated per cell (defo_ingest.py). | [ ] |
| 7 | The unit set was not chosen from target values after the donor train end | Units per group by rule R18 (4,285, test and donor); the shipped run used 4,000 test cells and a 1.5M-row donor pool. | [ ] |
| 8 | The unit set is declared, and whether it holds an all-zero unit (G-SUPPORT: a unit set with no all-zero unit is flagged) | 42 groups; 63.8% of test rows are exactly zero (D:/adaptation/FINAL_THREE_TYPES.txt). | [ ] |
| 9 | The target legal range cites the product's documented valid range (plan 1.3) | [0, 1] by construction (defo_ingest.py:6, 9, 14); confirm. | [ ] |

## Items the agent found while writing this package (for the owner)

- Read D:/defo_matrix in place (as shipped, with the sentinel disclosure) or rebuild its aggregates in features/build.py with aggregate_time (plan 3.2), which retires the disclosure.
- Plan 3.2 says R30 flags conflict_* and eddi_observed, but they are stored as zeros, not blanks: a missing-share rule cannot see them (expected_derived.json R30 note).
- D:/defo_matrix is not only aggregates (catalog.yaml header): y, land_px, is_train and 33 lag1_* columns are now declared. y, land_px, is_train and forest2000_px carry forced bans (y by plan 1.4; the other three are the agent's reading of plan 1.3/1.4 and G-KEYS: confirm); the lag1_* columns need your verdicts (or the ingest drops them). Under option (a), 51 listed drivers are absent from the matrix (38 dropped at build by defo_ban.py's BAN/FREEZE lists; 13 LAG parents only in lag1_* form).
- loss_px (target store only) is not in catalog.yaml: give it a role (target_twin, forced ban) or let the ingest drop it.
- No shared store catalog exists for D:/defo_target or D:/defo_matrix.
- ban.yaml holds only forced bans (the target, y, forest2000_px, land_px, is_train): the schema refuses an empty ban.yaml.

---

Signed: ____________________   Date: ____________

(The loader checks only that this file exists; its content and signature are checked by a later validator.)
