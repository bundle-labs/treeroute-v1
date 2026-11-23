# Review sheets v2: ban list and column facts (the Q34 review)

These four sheets replace the ones one folder up (`../*.csv`, written at 12:30 on 2026-09-28). Those files are kept only because nothing may be overwritten. **Fill in these v2 sheets, not the old ones.**

Each row is one column a model could read. It comes pre-filled with what the shipped run did, plus the rulings you have already made. You fill in two columns, `owner_verdict` and `owner_timing_signed`.

## Deadlines

| When | What | Source |
|---|---|---|
| **Fri 9 Oct** (target) | ban lists done (`owner_verdict` filled) | APP_PLAN.md 8.0, line 677 (fast track) |
| **Sat 10 Oct** (target) | timing facts signed (`owner_timing_signed` filled), at the freeze | APP_PLAN.md 8.0, line 678 |
| Tue 27 Oct (fallback only) | both, if the fast track slips | APP_PLAN.md 8.1 (M5) and 9.1 item 5 |

The old README gave only Tue 27 Oct. That is the fallback date. This review is on the critical path: if it waits for 27 Oct, the fast track slips by about 2.5 weeks.

## Files

| File | Rows | What is in it |
|---|---|---|
| `pm25_columns.csv` | 178 | 166 panel columns, GFED burn (2 + a pixel count), EDGAR (5 + a flag), router context (month, lat), the target |
| `fire_columns.csv` | 214 | 166 panel columns, fire history (19), fire drivers (8), **new:** fire NDVI lags (8) and fire danger indices (6), router context, the target and its 4 count columns |
| `defo_columns.csv` | 178 | 166 panel columns (the annual mean/min/max columns are listed under their parent), the 8 `h_*` history columns, the target and its 3 pixel counts |
| `ndvi_columns.csv` | 206 | 166 panel columns (V11 is the target row), GFED burn (lag 1), 28 water-memory features, router context: the normal copy (banned), 4 harmonics, and **the 5 top-5 columns by name** |
| `evidence/*.yaml` | 7 files | review aids for the store catalogs: footer statistics, the cadence sample, sources, notes |

The keys `cell_id`, `region`, `year` and `month` have no row, because a key is never a feature.

## ATTENTION: read these first

1. **Rows marked "INDEX AUDIT" (37 per sheet, 36 on NDVI).** The index audit (`../../_stores/INDEX_WINDOW_AUDIT.md` and `index_facts.yaml`) has newer, sourced proposals for these rows. Sign them against the audit, not against the timing printed on the sheet. The audit also has five open rulings you must make first:
   - **R-A (ERSSTv5 filter):** affects nino12, nino3, nino4, nino34, oni and the 8 `sst_anom_*` boxes.
   - **R-B (tni alignment):** three ways to sign tni.
   - **R-C (co2 bound):** a 3-month bound or a plain month.
   - **R-D (fire detection window):** affects fire's target row `burned_frac` and where fire's history block starts.
   - **R-E (PSL footers):** whether the PSL file footers may be read as evidence.
   The note on each row names the rulings that touch it. The numbers themselves are in the audit, so this README does not copy them (the old README's table went stale within the hour).

2. **Two ways of writing "the calendar month".** These sheets write a plain month as stamp `period_end` with a 1-month window looking back. The audit writes it as `period_centre` with a 1-month centred window. Both mean exactly the same month. The engine build (M1) picks one spelling and converts the other.

3. **Rows whose `notes` say "OWNER CHECK" or "FOOTER FINDING":** 2 on PM2.5, 22 on fire, 10 on defo, 21 on NDVI. These are places where code, a ruling or two documents disagree, or where you must decide something new. Filter the `notes` column.

4. **Rows whose `missing_share_note` says "R30 FLAG"** (10, 12, 10 and 11 rows). They need an explicit `keep` with evidence, or a `ban`; `keep_unreviewed` is not enough. Two thresholds decide the flag, and **you sign both**:
   - more than 25% missing in donor rows (the plan's R30, 9.1 item 2 f);
   - more than 90% missing in one test year ("vanishes in a test year"). **The plan does not give this number.** This tool proposes it. AMO is 92% missing in 2023, so it flags.
   A group that has no file for a store now counts as missing, as R30 treats it.

5. **NDVI and Q34.** Q34 option a (recommended, not yet ruled) means: PM2.5's list, plus the MCD12Q1 slices, the land-cover class, and eddi/scpdsi. The sheet now works out which NDVI-kept columns option a would ban, from the four sheets' actual verdicts. There are 20:
   - cropland_fraction, solar_radiation_Wm2, aridity_index_p_pet, snow_cover_fraction, cloud_frequency_pct;
   - V20_burned_binary, co2, the six food prices;
   - grace_lwe, era5l_ssr, esacci_sm, scpdsi, eddi, wbal_roll24, eddi_observed.
   Each of these rows says why, and what the other three sheets do with the column.

6. **NDVI's frozen top-5 router-context list, by name** (it was one unnamed row before):
   - sph_kgkg_lag6, era5l_slhf_lag1, V07_total_ref_ET_mm_lag1, era5l_d2m, V01_mean_temp_C.
   None of them is banned on this sheet, so each keeps its base column's verdict. They were chosen by run89's 89 helper forests. 19 of those 89 regions are TEST regions in the current NDVI split, so the list is test-exposed. It must be disclosed (an exceptions.yaml entry; plan 3.3 flag 8). The rows name all 19.

7. **Fire: two more sidecar stores.** `D:/fire/drivers/ndvi` (8 columns) and `D:/fire/drivers/danger` (6 columns) exist on disk but were switched off in the shipped run. They are marked `conditional`. Decide one of:
   - (a) the fire package does not declare these stores, so their rows drop out;
   - (b) it declares them, and you rule each row.
   A third store named in fire_architecture.py, `D:/fire/drivers/fwi`, is empty, so it has no rows.

8. **There is no "lag" verdict in the engine.** A row marked `lagged` today becomes `keep`. The engine works out the delay itself, from the timing facts you sign.

## How to fill `owner_verdict`

| Write | Plain meaning |
|---|---|
| `keep` | Let the model read it. |
| `keep_unreviewed` | Keep it without a full review. Allowed only if its timing facts are signed, it does not reach ahead in time, and it has no lineage flag. It is listed in every report. |
| `freeze` | Let the model see one old photo of the column, taken before the test period, and nothing newer. |
| `ban:<reason>` | Lock it away. Reasons: `label`, `coproduct`, `target_derived`, `replaced_by_engine`, `post_event_state`, `lookahead_unfixable`, `trend_proxy`, `incomplete`, `structural`, `post_window_snapshot`. For example `ban:trend_proxy`. |
| `conditional` | Keep it out of every engine run and save it for a later side experiment. |
| `watch` | Keep it, and list it in every report. |

- Put the evidence (a Part number) in `notes`, for example `Part 431`.
- An empty cell means "not reviewed yet".
- The mean/min/max columns of one parent share one verdict. So do the members of a sum group (MOD44B: `V15 + V17 + tree_cover_pct = 100`).

## How to fill `owner_timing_signed`

The timing facts are `cadence`, `stamp`, `window_length`, `window_align`, `units` and the legal range.

| Write | Meaning |
|---|---|
| `yes` | The facts on this row are right. |
| `assumed:<length> <unit>` | The window is unknown, but you sign a maximum, for example `assumed:5 month`. The engine then delays the column enough to cover it. |
| `fix:<what>` | A fact is wrong; say the right value, for example `fix: window 3 month centred`. |
| add `; co_measured=true` or `; co_measured=false` | Your answer for a co-measured candidate, for example `yes; co_measured=false`. |

Banned rows may stay empty. A kept column without signed timing facts cannot enter the headline run (G-FACTS).

## What changed in how timing is written

The sheet now prints exactly the facts that sit in the store catalog, so the two always agree.
- **Reach past the month or year.** The catalog format has no field for "reaches 8 days into the next month". So such a column gets a slightly wider window that ends where its data really end. Think of a receipt that covers the month plus the first week of the next one.
  - The MODIS tree-cover year (MOD44B) runs from day 65 of the year to day 64 of the next. It is written as 430 days forward from 1 January.
  - Albedo and GPP are monthly means of 16-day windows. They are written as 47 days centred on the month.
  The row's notes say "written window: ..." with the reason. Only the far end matters for the delay, so the wider start costs nothing.
- **Unknown windows** show `unknown`, with no length, until you sign a maximum.
- **Static columns** show stamp `period_end` only because the catalog format requires a stamp; a static layer has no period.
- **Engineered and router-context rows** (burn_lag1, the water-memory features, `ctx:*`, defo's `h_*`) are not store columns. Their timing is computed from their declaration (plan 1.5), so some cells say `n/a`.

## Corrections to the old sheets and README

- **Q34 sentence (NDVI).** The old sheets said co2, the food prices, scpdsi, eddi and eddi_observed are banned by PM2.5, fire *and* defo. That was wrong:
  - defo keeps scpdsi, eddi and eddi_observed;
  - cropland_fraction is banned only by defo (PM2.5 conditional, fire lagged).
  The note is now computed from the sheets.
- **nino12/3/4/34** are anomaly files. They are now `K (anomaly)` with a -10..10 range; the old -10..35 was an absolute SST range. The 8 `sst_anom_*` boxes still say `degC`, as the audit does. Pick one spelling for anomalies when you sign.
- **population_density 2021-23 is extrapolated, not held.** The stored values rise every year: for example thar_desert's January mean is 87.70, 89.94, 92.25 and 94.61 in 2020-23. So defo_ban.py is right and the ingest docstring is stale. Disclose that it is model output in 3 of the 4 test years.
- **modis_landcover_annual has a 2023 layer.** It is 0% missing in 2023 and changed from 2022 in 0.2-8.3% of cells (5 regions read). The ingest comment says 2023 is empty. Which product release filled 2023 is not recorded, so there is an OWNER CHECK.
- **EDGAR units** are tonnes per km2 per year (edgar_emis_ingest.py:31). `edgar_carried` is a 0/1 flag.
- **Every `source_locator` now has a line number.** Fire's cropland_fraction now cites the right list: it is in PM2.5's CONDITIONAL_MODIS_LC, not ANNUAL_LAG1.
- **run89's lag notes.** They now come from run89's own saved feature list, and a re-run of run89's rule gives the same 87 columns. The old notes were correct. Only amo and the SPEI columns (banned) lacked the note.
- **NDVI GFED missing share.** Counting the 6 groups that have no GFED file, burn_frac is 10.6% missing in NDVI donor rows and 12.3% in each test year. Plan 3.2 says "about 4.5%".

## Store catalogs

The catalogs are `../../_stores/<store>_schema_catalog.yaml`, one per store: monthly_panel_v170, gfed_burn, edgar_emis, fire_history, fire_drivers, fire_ndvi_lags and fire_danger.
- Each one loads under the engine's own schema, `StoreCatalog`, and was re-loaded through its loader after writing.
- The older `monthly_panel_v170.yaml` and `*_catalog.yaml` seeds in that folder do **not** load under the schema. They are superseded, and a package must not include them.
- Each fact is an unverified seed. Your signatures on these sheets are what later turn a fact into `verified` or `assumed`.

## After you finish

Save as CSV (UTF-8) under the same file name. If Excel changes `ban:trend_proxy` or long numbers, open the file with Data > From Text/CSV and set every column to text.

The generator (`../../_tools/export_review_csv_v2.py`) **never overwrites**; run it again and it refuses. For a fresh blank set, run it with `--out-dir <new folder>`.
