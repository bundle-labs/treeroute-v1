# AUDIT_CHECKLIST -- NDVI package

The human checks that no code can do (APP_PLAN.md 1.2, 'AUDIT_CHECKLIST.md'). **UNSIGNED.** Drafted by the agent on
2026-09-28 from the repo and the plan; every box is open until the owner ticks it and signs at the bottom. Evidence
pointers are where to look, not conclusions.

| # | Check (plan 1.2) | Where to look | Done |
|---|---|---|---|
| 1 | Target lineage and co-products | MOD13C2.061 V11. Target twin: V12_mean_evi (same file and month). Co-measured by ruling: GFED burn (Q38 b, lag 1). Candidates needing explicit true/false: snow_cover_fraction and cloud_frequency_pct (MODIS, same sensor and month), V20_burned_binary (FireCCI on MODIS reflectance). | [ ] |
| 2 | Fill codes | Panel fills -32768, -32767, -2^31, -2^31+1 (store catalog); the -2^31 poison in 47/133 regions. MOD13 raw valid range -2000..10000. | [ ] |
| 3 | Compositing-window dating | The monthly value is built from the 16-day composites that overlap the month; they reach past month end (index audit: up to 15 days; plan 3.2: December about 3 days into January). Decides R17's start. | [ ] |
| 4 | Product vintages | MOD13C2 collection 061 (presplit_cc/ingest_modis_cmg_local.py). | [ ] |
| 5 | Split design | D:/run89full/ndvi_split.txt (HEADLINE_RUN_PLAN.md:107-108 option a). seen_during_design: thar_desert, greece_mainland (Q49). | [ ] |
| 6 | The unit definition (as delivered) | 4 km panel cells (CMG 0.05 deg aggregated to the panel grid). | [ ] |
| 7 | The unit set was not chosen from target values after the donor train end | Units by stride, 100 per group (Q39 a). | [ ] |
| 8 | The unit set is declared, and whether it holds an all-zero unit (G-SUPPORT: a unit set with no all-zero unit is flagged) | 133 groups; the 6 GFED-absent groups are NDVI groups (burn_frac NaN there, a store fact). | [ ] |
| 9 | The target legal range cites the product's documented valid range (plan 1.3) | MOD13 User Guide V6.1 Table 19 (valid_range -2000..10000, scale 1e-4) -> [-0.2, 1]. | [ ] |

## Items the agent found while writing this package (for the owner)

- The target window is written as the store catalog seeds it (align unknown): sign the index audit's window so R17 can run. The schema can express the reach only as a wider window, which is wrong for a target window (R8 takes its reference from the target window's end, so month t+1 drivers would get through; INDEX_WINDOW_AUDIT.md open item 8 (b)); the exact form needs the audit's proposed reach_after_max field (item 8 (a)), or you sign a bound (align unknown + max_length).
- The top-5 router-context list is test-exposed on both of plan 1.3's grounds: 19 of the 89 helper regions are NDVI test groups, and the selection rows run to 2019-12, after the earliest fit cut (the inner-fit end is 2016). Disclosed in exceptions.yaml and data_selected; the entries are unsigned (basis F15 and plan 7.2).
- Router-context and engineered column names are the review sheet's (ctx:...); the feature script (M4) decides the real names.
- ban.yaml holds only the forced bans of the target and its twin V12_mean_evi (plan 1.4): the schema refuses an empty ban.yaml.

---

Signed: ____________________   Date: ____________

(The loader checks only that this file exists; its content and signature are checked by a later validator.)
