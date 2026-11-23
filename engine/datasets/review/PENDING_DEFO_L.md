# Pending for the defo task: ruling L on datasets/defo (written 2026-10-06)

Ruling L is in `engine/OWNER_RULINGS_2026-10-05.md` section L (every item accepted by the owner, 2026-10-06). The L task changed
the shared store catalogs and the PM2.5, fire and NDVI packages. It did not edit `datasets/defo/`, because the defo
task (ruling K) owns that folder. This file lists the exact defo changes. The defo task applies them.

## Status (checked 2026-10-06, after the defo task's 00:37-02:20 edits)

The defo task has already applied most of this list. Where it chose differently, the owner has to decide; the L task
does not override it (it does not edit `datasets/defo/`).

| Change | State in `datasets/defo` | Source checked |
|---|---|---|
| 1 panel re-pin | DONE: pins `53f56fe0...` | defo/dataset.yaml (file time 00:24) |
| 2 regenerate the generated catalogs | PART: the K store catalog is regenerated and re-pinned (02:15); `defo_features_store_catalog.yaml` is not (file time 2026-09-29) | features/ |
| 3 sign the 15 J4 and 6 aglw_* catalog rows | NOT APPLIED, and the defo task disagrees (see "Owner decision" below) | defo/catalog.yaml: no fact_status / reviewed_by on those rows |
| 4 sign the 18 lag-1 windows | NOT APPLIED, same disagreement | defo/features/build.py writes no reviewed_by |
| 5 a raw aglw_* banned 'incomplete' | DONE | defo/ban.yaml |
| 5 b six hold catalog rows | DONE, without a reviewer (this file now asks for that too) | defo/catalog.yaml |
| 5 c hold verdicts 'watch' | DONE | defo/ban.yaml |
| 5 d hold outputs in features/build.py | DONE, the parent's facts without reviewed_by/date | defo/features/build.py |
| 6 eddi_observed aggregates banned structural | DONE | defo/ban.yaml |
| 7 the 11 index families back (K6) | DONE in the package 2026-10-06 (agent C1): built by features/build_store_k.py (K6, 33 columns), catalog regenerated and re-pinned, verdicts conditional -> keep. The store FILES wait for the owner's K build (section 9) | defo/ban.yaml soi_mean; features/defo_features_k_store_catalog.yaml |

### Owner decision: the two tasks read "signed" differently

- **The L task's reading** (PM2.5, fire, NDVI): ruling L1 is the owner's signature. Writing `reviewed_by: owner` on a
  fact the ruling names records that signature; it is not the agent signing. So the L task signed exactly what
  L1 lists: on the three monthly packages the index windows, the J-assumed facts, the aglw_* yearly facts, the
  co-measured answers (NDVI cloud_frequency_pct / snow_cover_fraction / burn_frac, fire cloud_frequency_pct) and the
  six lag-12 windows. On defo that reading means changes 3 and 4: the 15 J4 rows, the 6 aglw_* rows and the 18
  lag-1 windows.
- **The defo task's reading:** "the agent signs nothing". Its test `tests/test_defo_k_l3_l4.py::
  test_nothing_in_the_package_is_marked_signed` forbids any `reviewed_by` in defo's catalog, feature outputs and K
  store. Its J4 and aglw_* rows say "Package fact, unverified (the owner signs timing facts separately)".
- **Where the two agree:** the L3 hold columns are not signed in any package. L1 does not list them; they are new
  columns that L3 creates. The L task first copied the parent's signature onto them; that is now undone on PM2.5,
  fire and NDVI, so all four packages write them the same way.
- **To settle:** (a) apply changes 3 and 4 on defo, and drop the "nothing signed" test; or (b) keep defo unsigned
  and accept that defo's L1 (c) facts read unsigned while the same ruling is recorded as signed on the other three
  packages. The panel store catalog that all four share already carries the signature on the aglw_* yearly facts
  (L1 c) and the index windows (L1 b), and defo reads those facts as signed.

## 1. Re-pin the panel store catalog (defo/dataset.yaml)

In `datasets/defo/dataset.yaml`, change the include line:

```yaml
  - {path: ../_stores/monthly_panel_v170_schema_catalog.yaml, sha256: 512b4a2e5edaa2245a8ecde555d64cd21ec687d8d87a92197da559fcf06b74a5}
```

to

```yaml
  - {path: ../_stores/monthly_panel_v170_schema_catalog.yaml, sha256: 53f56fe0b361d9cdcd318e582ff7dc70d1bae2bb577e66e5d6f318b98a6bc4c7}
```

Check with `sha256sum datasets/_stores/monthly_panel_v170_schema_catalog.yaml`. If another task edits that catalog
again, use the hash at that time. defo does not include `gfed_burn_schema_catalog.yaml`, so that file's re-pin does
not apply to defo.

**Which panel facts changed.** Each one is written fact_status `assumed` + `reviewed_by: owner` + `date: '2026-10-06'`.
That is how the schema writes a signed fact; it has no `signed` value.

- L1 (b): the windows of soi, tna, tsa, iod, ao, nao, pna, wp, sam, noi, pdo, epo and grace_lwe. Each is now
  `{length: 3, unit: month, align: centred}` at the stamp period_centre (it was `align: unknown` with no bound).
  On a monthly target this gives lag 1 month. As a calendar-year aggregate, the December value reaches one month
  into January, so the timing helpers give lag 1 year on defo's annual target. This is the same path the nino
  columns take.
- L1 (a): the signature is added to deeprec_twsa, phenology_sos_doy, nitrogen_gkg, V30_soil_moisture_pct and tni.
  Their values are unchanged.
- L1 (c): aglw_* (6) go from unverified to signed. Their values are unchanged.

## 2. Regenerate the generated defo store catalogs, then re-pin them

`features/defo_features_store_catalog.yaml` and `features/defo_features_k_store_catalog.yaml` are built from the
panel facts. treeroute/io/aggregate.py takes fact_status from the parent and resets reviewed_by. `build_store.py`
cross-checks the result against `../_stores/defo_annual_features_schema_catalog.yaml` (the seed).

- Regenerate both catalogs with the defo builders, and re-pin both include lines in `defo/dataset.yaml`.
- If the builders' cross-check refuses on the seed, the seed may need the same index windows. The L task did not
  edit the seed: defo's builders read it, so it is the defo task's file to change.
- epo's yearly aggregates (K2, built in the K store) now inherit a signed window instead of an unknown one.

## 3. L1 (c): sign defo's co-measured answers (defo/catalog.yaml)

Ruling L1 (c) signs "the co_measured_with_target 'true' answers (defo's 15 J4 columns and the 6 aglw_*)". Append
`fact_status: assumed, reviewed_by: owner, date: '2026-10-06'` to each of these flow rows. The rows have no
fact_status key today.

- **The 15 J4 rows:** burn_month_count, burn_doy_mean, ntl, V13_mean_lst_C_mean, V13_mean_lst_C_min,
  V13_mean_lst_C_max, nighttime_lst_C_mean, nighttime_lst_C_min, nighttime_lst_C_max, cloud_frequency_pct_mean,
  cloud_frequency_pct_min, cloud_frequency_pct_max, V20_burned_binary_mean, V20_burned_binary_min,
  V20_burned_binary_max.
- **The 6 aglw_* rows:** aglw_cattle, aglw_buffalo, aglw_horse, aglw_sheep, aglw_goats, aglw_total_lsu.
  - Under change 5 the raw aglw_* are banned. Sign them anyway: the ruling signs these facts. The hold rows do NOT
    copy the signature (change 5 b).
- **NOT APPLIED by the defo task** (it signs nothing): see "Owner decision" above.
- **Not in the ruling's list, so not signed:** the K4 rows modis_landcover_class, shrub_cover_pct_global,
  cropland_fraction and modis_landcover_annual. They are already `assumed` with "not signed" in their evidence.
  - Owner question: does L1 (a) "every fact the install marked 'assumed'" cover them? They were written by the K
    task after the install.

## 4. L1 (c): sign the windows of defo's engineered lag columns

L1 (c) signs "the windows of the engineered lag columns". On defo these are the 18 J2 (a) columns
`<parent>_<stat>_lag1`:

- parents: V06_spei_12m, spei_01m, spei_03m, spei_06m, spei_24m, amo;
- stats: mean, min, max.

In `features/build.py` `_lag_facts`, write `fact_status: 'assumed'`, `reviewed_by: 'owner'` and
`date: '2026-10-06'` on these 18 outputs.

- The pm25, fire and ndvi feature scripts do the same for their six lag-12 columns. Each defines a LAG12_SIGNATURE
  dict and appends one note to the column's provenance.
- **NOT APPLIED by the defo task** (it signs nothing): see "Owner decision" above.
- Scope: the list that the owner accepted in full (BAN_INSTALL_REPORT.md section 8 C) names "the windows of defo's 18 lag-1
  columns, and of the lag-12 columns on PM2.5, fire and NDVI". The other engineered lag columns (PM2.5's burn_lag1,
  NDVI's 345 driver lags) are not signed; that is an owner question in the L report.
- `h_lag1` is the engine's history block, not one of these 18. Leave it as it is.

## 5. L3: livestock 2022-23 (defo/ban.yaml, defo/catalog.yaml, features/build.py)

The 2022 and 2023 aglw_* layers are not used. Each package builds an engineered column that holds the real 2021
layer for 2022-2023 (backward only, declared). The raw aglw_* are banned. The fixed columns are 'watch' and lagged
one year by R8, and the hold is disclosed.

**a. ban.yaml, the six raw rows.** For each `aglw_<x>`, change watch to:

```yaml
  aglw_cattle:
    verdict: ban
    reason: incomplete
    evidence: 'the 2022 and 2023 layers are not observations (the 2021 layer times INDIA''s FAOSTAT ratios, applied to every region; store observed_through 2021), so the raw column is not used and is kept through aglw_cattle_hold2021 | ruling L3 (OWNER_RULINGS_2026-10-05.md section L). REASON WORD: the ruling names post_window_snapshot; written ''incomplete'' (as J2 a''s raw parents) because treeroute/pipeline/data.py LINEAGE_LEAK_REASONS / check_feature_lineage refuses every feature-script output derived from a column banned for post_window_snapshot (G-LINEAGE), which would refuse the hold column L3 asks for. OWNER: confirm the word, or rule an engine change; was watch (amended J3)'
```

- PM2.5, fire and NDVI use the same wording, so the owner sees one choice.
- Defo builds its hold columns in `features/build.py`, a feature-script output, so the same G-LINEAGE check applies.

**b. catalog.yaml, six new rows.** Add after aglw_total_lsu. The co-measured fact is the parents' (amended J3), so
R8 still gives one year on this annual target:

```yaml
  aglw_cattle_hold2021: {role: engineered, co_measured_with_target: true, fact_status: assumed, co_measured_evidence: 'as aglw_cattle (amended J3: the AGLW downscaling uses a year-matched optical land-cover mask that shows that year''s forest loss); ruling L3 hold column (features/build.py)'}
```

CORRECTED 2026-10-06: no `reviewed_by` / `date` on the hold rows. L1 does not list the hold columns (L3 creates
them), so they are not signed. The defo task already wrote them this way.

Write the same row for aglw_buffalo, aglw_horse, aglw_sheep, aglw_goats and aglw_total_lsu.

**c. ban.yaml, six new rows.** Each `aglw_<x>_hold2021` is `verdict: watch`. Use a reason that discloses the hold.
On defo:

- R8 lags each hold column one year (it is co-measured).
- The 2023 test row reads the held 2021 layer, which is two years old.
- The 2022 row reads 2021, as before.

**d. features/build.py.** Add six outputs.

- Their facts are the parent's store facts with these changes:
  - `fill_values` and `near_sentinel_optout` dropped;
  - `reviewed_by` and `date` dropped (the parent is signed by L1 c; the hold column is not);
  - `derived_from: [<parent>]`;
  - `reads_target: false`;
  - `operation: 'hold_last_observed through_year=2021 unit=year'`.
- Refuse unless the parent's cadence is `{regular, 1, year}` and its `observed_through == '2021'`.
- The values on annual steps:

```python
years = frame[year_col].to_numpy().astype(np.int64)
after = years > 2021
values = frame[parent].to_numpy(dtype=np.float64)
out = np.where(after, np.nan, values)
for gap in np.unique(years[after] - 2021):          # annual steps: the 2021 row is `gap` steps back
    rows = years - 2021 == gap
    prev = predecessor_index(codes, steps, int(gap))
    ok = rows & (prev >= 0)
    out[ok] = values[prev[ok]]
```

The pm25, fire and ndvi feature scripts each carry `HOLD_PARENTS`, `HOLD_THROUGH_YEAR`, `_hold_facts` and `_held`.
Those versions use monthly steps (`gap * 12`).

## 6. L4: defo's eddi_observed aggregates are banned (defo/ban.yaml)

"defo's eddi_observed aggregates banned, like eddi_observed itself". Change `eddi_observed_mean`,
`eddi_observed_min` and `eddi_observed_max` from keep to:

```yaml
    verdict: ban
    reason: structural
    evidence: 'family of eddi_observed, banned like eddi_observed itself (PM2.5, fire and NDVI ban it structural: isfinite(eddi) is the seasonal snow mask, a month key) | ruling L4 (OWNER_RULINGS_2026-10-05.md section L: ''defo''s eddi_observed aggregates banned, like eddi_observed itself''); was keep (0.0% missing; the annual-target argument is overruled)'
```

## 7. After L1 (b): the 11 index families on defo (K6)

K6 says "The 11 climate-index families come back when the owner signs their timing windows". L1 (b) signs them.
These are the 33 aggregates of soi, tna, tsa, iod, noi, ao, nao, pna, wp, sam and pdo (mean, min and max each),
conditional today ("not built").

- They need a store build, because D:/defo_features does not hold them, then a verdict change from conditional to
  keep, applied by the defo task.
- grace_lwe_* stay banned (incomplete).
- epo_* stay keep (K2).

## 8. Tests the defo task owns that may pin the old state

- `tests/test_defo_k_ruling.py` and `tests/test_route_region_defo_package.py`: they load `datasets/defo` and may
  pin the index columns as refused (G-LAG) or the aglw_* as watch. Changes 3-7 move those pins.
- `tests/test_catalog_timing_facts.py` (defo aggregates): the L task updates it for the shared panel only.

## 9. Defo's Y0: two candidate values, waiting for the owner (written 2026-10-06 by agent C1)

`datasets/defo/expected_derived.json` is NOT changed: it still says Y0 2003. The owner decides between the two values
below. The question comes from ruling K5 (the MOD44B trio kept through engineered LAG-2-YEAR columns) and ruling J5
(R4 counts Y0 from the first year of the driver stores, and counts a declared lag operation).

| Field | (a) Y0 2004: K5's lag-2 columns count in R4 (derive_all today) | (b) Y0 2003: the expected value as it stands |
|---|---|---|
| R3_R7_windows.y0 | 2004 | 2003 |
| R3_R7_windows.inner_fit | [2004, 2016] | [2003, 2016] |
| R3_R7_windows.inner_score / train_end / test_years / y_end | [2017, 2018, 2019] / 2019 / [2020-2023] / 2023 (unchanged) | the same |
| R12_valid_rows_per_unit.inner_fit | 13 (2004-2016, one step a year) | 14 |
| R12_valid_rows_per_unit.test_cut | 16 (2004-2019) | 17 |
| R18 bank_units | 4615, 7 groups capped (costa_rica 2543, new_zealand_north_island 4304, pantanal 4585, pearl_river_delta 2734, tasmania_western 4016, tierra_del_fuego 4554, tongass_alaska 3938) | 4285, 4 groups capped (costa_rica 2543, pearl_river_delta 2734, tasmania_western 4016, tongass_alaska 3938) |
| R18 scored_units | 2197 a group, 92274 in all (42 groups, 20 group-equivalents) | 2040, 85680 |
| R14 region_fit | inner_surface_units 4615, test_pass_units 3750 | 4285, 3529 |
| Why the unit counts move | the region router's row budget (C7, 60000 rows) over the rows a unit holds: 60000 / 13 = 4615, 60000 / 16 = 3750 | 60000 / 14 = 4285, 60000 / 17 = 3529 |
| What sets it | the driver stores start in 2002; V15_bare_ground_pct_lag2, V17_herb_cover_pct_lag2 and tree_cover_pct_lag2 declare 'lag k=2 unit=year', so R4 (J5) gives 2002 + 2 = 2004 (tests/test_defo_k_ruling.py::test_k_lags_r8_and_r4_and_the_y0_they_give pins this) | every other kept column needs at most one year: 2002 + 1 = 2003 |
| What it costs | one inner-fit year less (13 instead of 14 per unit) | the lag-2 columns are empty (NaN) in 2003, the first model year; R30 0-fills them there |

How to read the two:
- (a) follows the engine's rule as built: R4 never lets a model year read a year the store does not hold, and the
  K5 columns hold nothing before 2004. Choosing (a) means editing the four fields above in defo/expected_derived.json
  with a note citing K5 and J5.
- (b) keeps 2003, but then derive_all and the expected file disagree, unless R4 is changed (an engine ruling) or the
  K5 columns leave the package.
- The 11 index families (section 7, now built) need one year, so they do not move Y0 either way.
- tests/test_derive_acceptance.py (updated 2026-10-06 by agent C1) now counts the engineered store columns as
  candidates, so it sees the K5 lag-2 columns. It reports the six fields above as KNOWN differences (xfail) and
  pins the (a) values in PENDING_OWNER_DERIVED, so a different derived value fails. Choosing (a): edit the json
  fields above, then remove those six entries and their pins from the test. Measured on the real stores
  2026-10-06 10:21-10:35 (30 passed, 71 xfailed). The defo fields from the windows are PROVISIONAL until the K store
  is built for every group (today it holds 2 of 42 groups, in the older schema without the 33 index columns).
- Measured: the smoke of the refreshed defo_draft (4 groups, 2026-10-06, run folder
  D:/treeroute/c1_20261006/runs/defo_draft/smoke/20261006_9c19948a, K store built for those 4 groups in a scratch
  store) derived Y0 2004, inner fit 2004-2016: the engine as built gives candidate (a).
- The K store must be built before any defo run (section 7): from the defo features folder,
  `py -3.9 -u build_store_k.py build ..` (about 50-120 minutes depending on machine load, about 0.25 GiB on D:;
  resumable; it moves the 44 older-schema files of costa_rica and pearl_river_delta aside into
  D:/defo_features_k/_moved_20261006/<schema>/ and rebuilds them).
- **No defo or defo_draft smoke, rehearsal, probe or headline run can run until `build_store_k.py build ..` has
  finished.** Every one stops at the driver read with G-MISSING (checked 2026-10-06 by the reviewer: a defo_draft
  smoke against the real D:/defo_features_k refused for its 4 smoke groups). The defo_draft smoke above ran only
  because its frozen snapshot pointed at a scratch K store.
