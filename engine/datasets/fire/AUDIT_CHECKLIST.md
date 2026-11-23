# AUDIT_CHECKLIST -- fire package

The human checks that no code can do (APP_PLAN.md 1.2, 'AUDIT_CHECKLIST.md'). **UNSIGNED.** Drafted by the agent on
2026-09-28 from the repo and the plan; every box is open until the owner ticks it and signs at the bottom. Evidence
pointers are where to look, not conclusions.

| # | Check (plan 1.2) | Where to look | Done |
|---|---|---|---|
| 1 | Target lineage and co-products | MCD64A1.061 Burn_Date -> burned_frac. Co-measured by ruling: same-month MODIS cloud (cloud_frequency_pct, Q3 a). fire_history is target-derived (G-HIST review, plan 3.2). The sheet's co-measured candidates (e.g. V20_burned_binary, FireCCI) still need explicit true/false. | [ ] |
| 2 | Fill codes | Validity n_valid > 0 lives in the ingest (fire_architecture.py:273-274); unmapped rows become NaN labels. Data check (index_facts.yaml): Aug 2007 in cerrado and gran_chaco, n_valid + n_unmapped exactly doubled (a duplicated STAC item; fire_fetch_target.py:114-125 has no de-duplication); burned_frac is unchanged, n_valid is not. | [ ] |
| 3 | Compositing-window dating | RULED R-D (b) (OWNER_RULINGS_2026-09-28.md B): MCD64A1 First/Last Day layers mean month m's label normally uses observations from month m+1 (User Guide V6.1 3.1.2, per INDEX_WINDOW_AUDIT.md). catalog.yaml burned_frac carries reach_after_max 1 month (a PROPOSED bound, unsigned), so R17 starts the history block at t-2. Applied to the target-derived columns too: the fire-history store is rebuilt at newest label lag 2 (features/target_history.py, ingest/build_history.py); the shipped D:/fire/history reads t-1 and must not be read. Sign the 1-month bound as 'assumed'. | [ ] |
| 4 | Product vintages | MCD64A1 collection 061; WGLC lightning, LPDR v3 VOD, ESA CCI biomass (fire_join_drivers.py). | [ ] |
| 5 | Split design | Leave one region out (rulings D and E; split.yaml): every one of the 40 groups in D:/fire/target (2002-2022 each, 840 files) trains its own trees and is tested; excluded: none; a unit's router never uses its own overlap block's trees (R14: one linked pair, angola_zambia_fire_belt / miombo_woodland_zambia). With 40 groups fire is not flagged 'few groups'. The shipped 30 donor / 10 test split (the 30 largest complete groups by panel cells, fire_evt_arch.py:157-161) is kept only as the continuity row (legacy_harness/shipped_splits.yaml). | [ ] |
| 6 | The unit definition (as delivered) | Target cells keyed on lat + lon; the unit is the monthly panel cell (cell_id = {group}_{ix}_{iy}): every target cell (union over the years) that is a panel cell, on the shipped key (lat/lon to 5 decimals, fire_architecture.py:241-243). ingest/build_static.py writes that key map as the static table; the target reader maps lat/lon to the id (plan 1.2). 14,219 target cells have no panel cell and are not units (they still count as ring neighbours). | [ ] |
| 7 | The unit set was not chosen from target values after the donor train end | Ruling C ('Fire cells'): R18's stride runs over ALL units (925,737), which build_static.py takes from the target and panel grids without reading a label. DISCLOSED: the shipped run used D:/fire/cells_1000.parquet, a seeded random 1,000-cell pick per group (fire_select_cells.py:79); it never read the target (fire_select_cells.py:12-22), but its seed uses abs(hash(region)), which Python randomises per process, so it cannot be regenerated. The two sidecars (fire history, lightning / VOD / biomass) exist only for that pick (about 39,900 units, 4%); the history is rebuilt for every unit by ingest/build_history.py, the drivers sidecar cannot be without re-joining its raw products. | [ ] |
| 8 | The unit set is declared, and whether it holds an all-zero unit (G-SUPPORT: a unit set with no all-zero unit is flagged) | 40 groups, 925,737 units (data/static/key_map_manifest.json; yakutia_larch 84,114 to borneo_peat_fires 4,845). R18 picks 100 bank and 50 scored units per group by stride (expected_derived.json). Check for an all-zero unit (many fire cells never burn). | [ ] |
| 9 | The target legal range cites the product's documented valid range (plan 1.3) | [0, 1] by construction (fire_fetch_target.py:8, 339); confirm this is acceptable as the 'documented' range. | [ ] |

## Items the agent found while writing this package (for the owner)

- RULED C: R18's stride runs over all units. Consequences: the fire-history store must be rebuilt for every unit (ingest/build_history.py; owner command in dataset.yaml, about 2 GB on D:), and the lightning / VOD / biomass sidecar covers 4% of units (keep with evidence, re-join, or ban in Q34).
- RULED R-D (b), applied: the fire-history columns read labels of months <= t-2 (15 columns; the four lag-1 rings cannot be built and need a ban). last_burn_size equals y(t-2) on every row where y(t-2) > 0 (a sparse own lag): rule it in the Q34 G-HIST review.
- The target-derived fire-history columns reach the trees through a driver store with reads_target true, so the engine's G-HIST / G-LINEAGE checks (which run on feature-script outputs) do not see them: only this package's tests do. An owner ruling like defo's (declared engineered target-derived columns) is needed, and an engine item: run lineage, G-HIST and the R17 start offset on store columns that read the target.
- D:/fire/drivers/ndvi and D:/fire/drivers/danger are not declared (off in the shipped run); review/v2/README.md item 7 asks you to choose (a) or (b).
- The target store's n_burned, n_valid, n_unmapped, unmapped_frac are not in catalog.yaml: give each a role or let the ingest drop them.
- The target store D:/fire/target has no shared store catalog.
- ban.yaml holds only the target's forced ban: the schema refuses an empty ban.yaml.

---

Signed: ____________________   Date: ____________

(The loader checks only that this file exists; its content and signature are checked by a later validator.)
