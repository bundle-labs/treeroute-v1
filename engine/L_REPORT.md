# Ruling L report (2026-10-06)

Ruling L is in `OWNER_RULINGS_2026-10-05.md`, section L (every item accepted). This report says what changed, what the
three smokes did, and what is still open.

## 1. Short answer

- **All three smokes finished.** PM2.5, fire and NDVI each ran end to end: the nowcast, the lead-0 check, and leads 6
  and 12. Before ruling L, PM2.5 and NDVI were refused (the `ao` window was unknown) and fire crashed (no static table).
- **Y0 is 2003 on all three.** On PM2.5 this is what L2 wanted: phenology_sos_doy is out, so Y0 went back from 2004
  to 2003.
- **Peak memory was small:** 1.1 to 1.9 GB. Each smoke took 2.3 to 3.5 minutes.
- **Tests:** the final full suite shows 14 failures, the same 14 as before the last edits. None comes from ruling L
  (section 4).
- **The defo part is written down, not applied by me.** The defo task owns `datasets/defo/`. It has already applied
  most of the list in `datasets/review/PENDING_DEFO_L.md`. One point needs you (section 5, item 1).
- **ATTENTION:** PM2.5's `expected_derived.json` still says Y0 2004. The smoke derives 2003, which is what L2
  intends. I did not edit the file in this step, because this step could only write run folders and this report
  (section 5, item 2).

## 2. What ruling L changed

| Item | What was done | Where |
|---|---|---|
| L1 sign the timing facts | Written as `fact_status: assumed` + `reviewed_by: owner` + `date: '2026-10-06'`. That is how the schema writes a signed fact; it has no `signed` value. Signed: the 13 index windows, now `{3, month, centred}` (soi, tna, tsa, iod, ao, nao, pna, wp, sam, noi, pdo, epo, grace_lwe); the facts that were 'assumed' (deeprec_twsa, phenology_sos_doy, nitrogen_gkg, V30_soil_moisture_pct, tni, burn_frac); the six aglw_* yearly facts; the co-measured 'true' answers (fire cloud_frequency_pct; NDVI cloud_frequency_pct, snow_cover_fraction, burn_frac); the windows of the six lag-12 columns on each package. | `_stores/monthly_panel_v170_schema_catalog.yaml` (24 facts), `_stores/gfed_burn_schema_catalog.yaml` (burn_frac), fire and NDVI `catalog.yaml`, each package's `features/build.py` |
| Re-pins | Each package's `dataset.yaml` points at the new catalog hashes: panel `53f56fe0...`, GFED `baf76c72...`. | pm25, fire, ndvi `dataset.yaml` (defo was re-pinned by the defo task) |
| L2 phenology_sos_doy | `conditional` (out) on PM2.5 and fire. On NDVI it stays banned as a co-product. | pm25, fire `ban.yaml` |
| L3 livestock 2022-23 | The six raw aglw_* are banned. Six new columns `aglw_<x>_hold2021` copy the real layer for 2002-2021 and repeat the 2021 layer in 2022 and 2023. They only look backward, and they are declared and on 'watch'. R8 lags them one year. | each package's `catalog.yaml`, `ban.yaml`, `features/build.py` |
| L4 consistency | epo is kept on fire (the last-value rule fills December). Fire's wbal_roll24 is banned. Defo's eddi_observed aggregates are banned (applied by the defo task). | fire `ban.yaml`; defo via `PENDING_DEFO_L.md` |
| L5 static tables | Built with each package's `ingest/build_static.py <package>`. Each holds one row per cell: cell id, region, lat, lon and grid index. They are byte-identical to the draft copies. | PM2.5: 2,034,972 cells, 127 groups. Fire: 925,737 cells, 40 groups. NDVI: 2,289,236 cells, 133 groups. All in `data/static/part-0.parquet` |

What the hold changes in practice:

- **PM2.5 and NDVI:** the 2023 test rows now read the real 2021 layer, which is two years old. Before, they read
  the fake 2022 layer (the 2021 layer times India's ratios).
- **Fire:** nothing changes. Fire's test years end in 2022, and a one-year lag already reads 2021.

## 3. The three smokes

Each smoke ran on its own, with `py -3.9 -m treeroute smoke datasets/<package>`. Before each one I checked that no
other python job was running. A full test suite started at 02:24 was still running (4.5 GB), so I waited until it
finished at 02:57.

| | PM2.5 | Fire | NDVI |
|---|---|---|---|
| Outcome | finished (exit 0) | finished (exit 0) | finished (exit 0) |
| Run folder | `D:\treeroute\runs\pm25\smoke\20261006_8d9d587f` | `D:\treeroute\runs\fire\smoke\20261006_d8751869` | `D:\treeroute\runs\ndvi\smoke\20261006_25807945` |
| Wall time | 159 s | 141 s | 209 s |
| Peak RAM (whole process tree) | 1.26 GB | 1.10 GB | 1.89 GB |
| Size | 4 groups, 160 units | 4 groups, 160 units | 4 groups, 160 units |
| Cadence | 1 month | 1 month | 1 month |
| **Y0** | **2003** | **2003** | **2003** |
| Last year | 2023 | 2022 | 2023 |
| Inner fit / inner score | 2003-2016 / 2017-2019 | 2003-2015 / 2016-2018 | 2003-2016 / 2017-2019 |
| Train end / test years | 2019 / 2020-2023 | 2018 / 2019-2022 | 2019 / 2020-2023 |
| Leads | 6 and 12 months | 6 and 12 months | 6 and 12 months |
| Links | identity, log_c | identity, log_c, arcsine | identity |
| Router | per unit | per unit | per unit |
| Nowcast (lead 0) adopted | log_c_plain_unweighted | arcsine_plain_gls | identity_plain_unweighted |
| Lead 6 | guard fails: falls back to no trees | guard passes: arcsine_plain_gls adopted | guard fails: falls back to no trees |
| Lead 12 | guard fails: falls back to no trees | guard fails: falls back to no trees | guard fails: falls back to no trees |
| Lead-0 check | identical to the nowcast, byte for byte | identical | identical |

These are smokes: 4 groups and 12 trees per group. Smoke deltas carry no sign information, so the adoptions above
only show that the plumbing works. They say nothing about skill.

How Y0 2003 comes about (rule R4, ruling J5):

- The driver stores start in 2002.
- The largest lag any kept column needs is 1 year: the hold columns, the lag-12 columns and the yearly drivers.
- So Y0 = 2002 + 1 = 2003.
- Kept, phenology_sos_doy would need 2 years (its signed window plus its reach), which would push PM2.5's Y0 to 2004.
  L2 removed it.

Lags R8 gave on all three packages:

- 1 month: the 13 index windows (soi, ao, noi, pdo, epo, grace_lwe and the rest) and burn_frac.
- 3 months: deeprec_twsa and tni.
- 1 year: the hold columns.
- 0: the lag-12 columns, which already carry their lag.

The last-value rule (J2 d) filled:

| Package | Rows filled | Left to R30 (gaps longer than 2 months) |
|---|---|---|
| PM2.5 | 3,374 (epo 3,360) | 0 |
| Fire | 7,066 (grace_lwe 3,840, epo 3,200) | 1,760 |
| NDVI | 45,654 in 26 columns (grace_lwe and its lags 3,840 each) | 11,916 |

NDVI's R30 raised one flag: burn_frac is borderline.

## 4. Tests

Relevant tests, run after the last package edit:

- catalog, timing schema, package and ban tests for the three packages, nonames and noknob: 378 passed, 7 failed.
  - All 7 failures are defo: `test_catalog_timing_facts.py` (4) and `test_packages_declarative.py` (3).
  - They test the defo K-store work the defo task is doing (the K store's columns, its catalog include, the J4/V30
    facts in defo's generated catalog). None of them involves PM2.5, fire or NDVI.
- The per-package derive tests for PM2.5, fire and NDVI: 4 passed, 4 skipped. The skipped ones are the heavy
  real-data checks, which only run when an environment variable is set.

Full suite, run once at the end, after the smokes: **3071 passed, 14 failed, 4 skipped, 62 xfailed** (26 minutes).

- The same 14 tests failed in a full suite that finished at 02:09, before the last ruling L edits.
- None of the 14 comes from ruling L. Each one tests an older state, or another task's folder:

| Tests | Failures | Why |
|---|---|---|
| `test_catalog_timing_facts.py`, defo aggregates | 4 | Defo's generated catalogs and K store (the defo task's work). The test still expects the old `lag1_*` rows and 101 lag parents. Also failing at 21:22, before ruling L. |
| `test_packages_declarative.py`, defo | 3 | The defo task's new K store and its catalog include. |
| `test_derive_acceptance.py::test_derive_all_stops_at_the_closed_world` | 4 (all four packages) | derive_all now gets past the closed world. Called without the feature script's outputs, it stops at R8 (columns with no store facts). Failing since the J install (21:22). |
| `test_pipeline_draft.py` | 3 | Still compares byte for byte with PM2.5's older files (`spei_01m_lag12` KeyError, catalog.yaml differs). Failing since 21:22. |

An earlier suite started at 02:24, in the middle of the last edits. It also showed 3 failures on PM2.5 and NDVI.
They do not appear in the relevant run or in the final suite.

## 5. What is still open

1. **ATTENTION: defo and the word "signed".** The two tasks read L1 differently. I read L1 as your signature, so on
   PM2.5, fire and NDVI I wrote `reviewed_by: owner` on exactly the facts L1 lists. The defo task reads it as "the
   agent signs nothing", and a defo test forbids any `reviewed_by` in defo. So defo's 15 J4 rows, its 6 aglw_* rows
   and its 18 lag-1 windows read unsigned. Choose one:
   - (a) apply changes 3 and 4 of `datasets/review/PENDING_DEFO_L.md` on defo, and drop the "nothing signed" test;
   - (b) keep defo unsigned, and accept that the same ruling reads signed on three packages and unsigned on defo.

   Either way, the shared panel catalog that defo reads is already signed.
2. **ATTENTION: PM2.5's expected values are stale.** `datasets/pm25/expected_derived.json` still has the values for
   phenology kept: Y0 2004, inner fit 2004-2016, h 156, test cut 192. Under L2 they should be ruling F3's values:
   Y0 2003, inner fit 2003-2016, h 168, test cut 204. The smoke derives Y0 2003, inner fit 2003-2016 and h 168 (no
   rule outputs the test cut). The heavy check
   `tests/test_packages_pm25_derive.py` (skipped unless `PM25_DERIVE_CHECK=1`) also has old pins:
   - it expects the package to be refused at G-LAG, but the windows are now signed;
   - it expects Y0 2004, set by phenology_sos_doy;
   - it expects h 156.

   Neither file was changed in this step, because this step could only write run folders and this report.
3. **The reason word on the raw aglw_*.** L3 says `post_window_snapshot`. I wrote `incomplete` instead. The engine's
   lineage check (G-LINEAGE, `treeroute/pipeline/data.py`) refuses any feature built from a column banned as
   `post_window_snapshot`, and that would refuse the hold columns L3 asks for. All four packages use the same word.
   Confirm `incomplete`, or rule an engine change.
4. **The hold columns are not signed.** L1 does not list them, because L3 creates them. They keep the parent's
   'assumed' status with no reviewer. R8 reads the window and cadence, not the reviewer, so the lag is the same
   either way. All four packages do this the same way.
5. **Other engineered lag columns are not signed:** PM2.5's burn_lag1 and NDVI's 345 driver lags. The list you
   answered names only defo's 18 lag-1 columns and the lag-12 columns. Should L1 (c) cover these too?
6. **Defo's K4 land-cover rows** (modis_landcover_class, shrub_cover_pct_global, cropland_fraction,
   modis_landcover_annual) were written by the K task after the install. Does L1 (a), "every fact the install
   marked 'assumed'", cover them?
7. **co2** has an 'assumed' window that L1 does not list, so it stays unsigned. co2 is banned on all four packages,
   so no run reads it.
8. **Defo's 11 index families** (33 yearly aggregates) can come back now that L1 (b) signs their windows (K6). They
   need a store build first (D:/defo_features does not hold them). That is the defo task's work.
9. **Full-size derives are still yours to run.** These smokes read 4 groups. PM2.5 (127 groups), fire (40) and NDVI
   (133) at full size are long jobs for your own terminal.

## 6. What I wrote

- This report.
- Three smoke run folders under `D:\treeroute\runs\<package>\smoke\`. The engine wrote them.
- Before this step (ruling L itself): the shared catalogs, the PM2.5, fire and NDVI package files listed in section 2,
  the three static tables, and `datasets/review/PENDING_DEFO_L.md`. Nothing under `datasets/defo/` and nothing under
  a protected root.
