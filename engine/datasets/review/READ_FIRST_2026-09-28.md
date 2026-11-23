# READ FIRST (2026-09-28, 13:20): use the v2 sheets

**ATTENTION:** the review sheets in this folder (`pm25_columns.csv`, `fire_columns.csv`, `defo_columns.csv`, `ndvi_columns.csv` and `README.md`, written at 12:30) are **superseded**. Fill in the sheets in `v2/` instead, and read `v2/README.md`. The old files stay only because nothing may be overwritten.

## Deadlines (corrects the old README)

| When | What |
|---|---|
| **Fri 9 Oct** (target) | ban lists (`owner_verdict`): APP_PLAN.md 8.0, line 677 |
| **Sat 10 Oct** (target) | signed timing facts (`owner_timing_signed`), at the freeze: APP_PLAN.md 8.0, line 678 |
| Tue 27 Oct | fallback only, if the fast track slips: APP_PLAN.md 8.1 (M5), 9.1 item 5 |

The old README named only Tue 27 Oct. Following it would slip the fast track by about 2.5 weeks.

## What else the old README got wrong

- **The NDVI Q34 sentence was wrong.** It said co2, the food prices, scpdsi, eddi and eddi_observed are banned by PM2.5, fire and defo. In fact:
  - defo keeps scpdsi, eddi and eddi_observed; only PM2.5 and fire ban them;
  - cropland_fraction is banned only by defo (PM2.5 conditional, fire lagged).
  v2 computes this note from the sheets.
- **Its index-audit table went stale.** `index_facts.yaml` was revised at 12:43 and now has five open rulings (R-A to R-E). R-A also touches the 8 `sst_anom_*` boxes and oni; R-D touches fire's target. v2 marks every such row "INDEX AUDIT" and points at the audit instead of copying its numbers.
- **The "vanishes in a test year" flag uses a 90% line that the plan does not set.** Sign it with the 25% line (9.1 item 2 f).
- **The old store catalogs do not load under the engine schema.** Use `../_stores/*_schema_catalog.yaml`, which do.
