# Pre-registration Part: the wildfire headline run (the fire freeze alone)

> **This copy is for the fire freeze alone** (owner ruling O3, OWNER_RULINGS_2026-10-06.md section O: "The signature
> stands for each package's freeze, taken before that package's headline run"). Made 2026-10-07 from
> PREREGISTRATION_DRAFT_pm25.md (itself made from PREREGISTRATION_DRAFT.md, which stays the shared draft). Only the
> title, this note and items 7 and 11 of section 12 differ from the PM2.5 copy; the signature line in section 13 is the
> same. pm25 (frozen and run alone, Parts 583-584), defo and ndvi are **not in this freeze**: every line below about
> them is context only; each gets its own freeze, and its own filled copy, before its headline run. The freeze
> command for this copy: `py -3.9 -m treeroute_report.freeze datasets/fire --prereg PREREGISTRATION_DRAFT_fire.md`.

> **Status: DRAFT for the owner to sign.** Written 2026-10-06 by the report task (agent C2). Nothing here is
> signed. Plan sources: APP_PLAN.md (Q24 a: "pre-registration Part + hash"; 7.1 "Pre-registration Part"; 7.2;
> 8.0 Sun 11 Oct; 8.1 M5) and the owner rulings files (engine/OWNER_RULINGS_2026-09-28.md,
> engine/OWNER_RULINGS_2026-10-05.md and engine/OWNER_RULINGS_2026-10-06.md). Where this text and a ruling
> differ, the ruling wins.
>
> **How it is filled.** Fields in double braces are filled by the freeze tool
> (`py -3.9 -m treeroute_report.freeze <the four packages>`). The freeze writes the lock file, then writes a copy of
> this draft with every field filled, next to the lock: `<registry>/freeze/PREREGISTRATION_<UTC time>.md`. The owner
> signs THAT copy. Its SHA-256 goes into the Part log with the lock's SHA-256. A field the freeze cannot fill is
> printed as "NOT FILLED" in bold.
>
> **Open items.** Every item still open starts with a bold marker: "owner decision pending" (a choice only the owner
> can make) or "open before freeze" (work or a check still to do), written in bold capitals. The freeze refuses while
> either bold marker is anywhere in this file (F-PREREG), so the filled copy the owner signs carries none. Whoever settles
> an item removes its marker. The freeze sees only the marker, not whether the item is really settled; section 12
> says which items the freeze also checks by itself and which the owner checks by hand.
>
> **Scope.** This Part covers the four nowcast-and-ladder headline runs. It leaves out, on purpose:
> - the rivals, their region-fold assignment and the Board B tuning choice (plan 4.6): deferred to M8 by owner
>   ruling E, L3. They get their own pre-registration Part before any rival number;
> - the full overlap-block list: this Part prints only the count of blocks with more than one group (from
>   plan.json); the list itself is in each run's derived.json (R14), whose hash is filled in section 4;
> - the nearest-donor distances and distance bands: not built yet (a build departure, section 12, item 6). They
>   are added when they are built.

## 1. The frozen state

- Lock file: D:\treeroute\registry\freeze\FREEZE_20261016T091126Z.lock.json
- Lock SHA-256: f8c297e5ff761c901c54efccfb25530d67dd37d623737b0954e2492d49470aa7
- Lock written (UTC): 2026-10-16T09:11:26+00:00
- Engine code (file hashes, the check contract): 65a177bc7cdd47bacca806582bd13be52706ba3da385bb468fe1f0f24b81a0ff
- Engine code (comments stripped, as in the run manifests): 13838e41843cf1ec2598a1c3f7383c8ae2371dc094a1f3ec7f63fd7fc073f74a
- Engine constants: 3ef147e5959c04166e3dbcd603723259d9c8ed0adab2d34dd4755662fc1e3a5b
- Python: 3.9.13
- Report tooling (treeroute_report: the table builder, the freeze, continuity_groups.yaml, history_bands.yaml,
  report_rows.yaml; outside the engine hash, so hashed on its own): af64f5f013ad194fc5aad3bdc7aa99c22ae90941e24e4353105df9f38299d178
- The lock also holds every engine constant with its value and origin, every package file hash and draft status,
  the input-store hashes, the library versions and the launch pins (thread pins, workers, version pins).
- After the freeze, `py -3.9 -m treeroute_report.freeze verify` re-hashes all of it and lists any drift.

## 2. The problems and their packages

Four grid problems run now. Each is one dataset package. The engine is the same for all four.

| Problem | Package | Target | Groups | Package fingerprint | Deep check report |
|---|---|---|---|---|---|
| PM2.5 | datasets/pm25 | monthly surface PM2.5 (ACAG), ug/m3 | 127 regions | **NOT FILLED: pm25 is not in this freeze** | **NOT FILLED: pm25 is not in this freeze** |
| Wildfire | datasets/fire | monthly MODIS burned fraction | 40 regions | 18c7bbb8634cf591fded8306fe5b3c34c372c63f1129cc56c03f747e6b9563f0 | 4f1e1bc1ea2e24634573c1d548494427a031d859f6806bb9f941eb2be904b48f |
| Deforestation | datasets/defo | annual Hansen forest-loss fraction | 42 forested regions | **NOT FILLED: defo is not in this freeze** | **NOT FILLED: defo is not in this freeze** |
| NDVI | datasets/ndvi | monthly MODIS NDVI | 133 regions | **NOT FILLED: ndvi is not in this freeze** | **NOT FILLED: ndvi is not in this freeze** |

- Coral bleaching is NOT in this Part. It is built after the four grid runs and gets its own pre-registration Part
  before its run (owner ruling H1 b).
- The only hand-set input of each run is its package: data, column facts, feature script, ban list, exclusions.
  Every modelling setting is derived by a written rule and printed by `treeroute plan` before any compute.

## 3. The design

- **Leave one region out (owner ruling D).** There is no hand-made donor/test split. Every group is trained and
  every group is tested.
- **Per-group banks.** Each group trains its own specialist trees (100 per group), only on its own bank units' rows
  up to the donor train end. Bank units: 100 per group; 4,285 per group on defo (the region-router budget, R18;
  four smaller defo groups use all their cells).
- **Own-block masking.** Groups that share or touch a unit location form one overlap block (R14). A unit's router
  never sees the trees of its own block. A guard asserts this at every router fit (G-DISJOINT).
- **Router kind by one rule (R12).** Per-unit on PM2.5, fire and NDVI; region on defo. The neighbour kind is not used
  by these four.
- **The router.** It learns on each unit's own history (or its group's, for the region kind). Every kind carries the
  unit's normal as an unpenalised column, so "trees off" equals the normal (R15, R16).
- **Type-2 layer (R22-R28).** Links: identity and log(y + c); arcsine only with a finite upper bound. Arms: plain,
  corrector, trees-off, and a placebo that is never selectable. GLS row weights as one more tool. A relative penalty
  grid; picks at the grid edge are flagged, never extended.
- **Selection by MAE** on the inner score window (Q37), with predict-zero and corr2 printed beside. The adoption is
  locked and hashed before any test label is opened (G-LOCK).
- **Decline to the normal.** If the N2 guard fails, the layer declines and the prediction is the arithmetic normal
  (R16, R27). The verdict then reads "declined".
- **Seeds.** No seed is varied. Each group's bag, tree and corrector seeds come from the group's name (R19).
- **Every row-level prediction is saved** (test_preds.parquet: every arm, the normal, every baseline, the pre-clip
  value). Every table is built from these saved rows (`py -3.9 -m treeroute_report.table`).

## 4. Leads, windows and test years

- **Leads (owner ruling I1):** the nowcast (lead 0), 6 months and 12 months. On defo (annual) the two leads merge into
  one: nowcast + 1 year.
- At every lead, every fitted object is cut at the issue date. Each lead refits its guard bank at its guard cut
  (rulings H2-H5). The lead-0 contract must reproduce the nowcast.
- The placebo of the pinned arm is built at the longest lead (12 months).

| Package | Test years | Donor train end | Inner score years |
|---|---|---|---|
| PM2.5 | 2020-2023 | 2019 | 2017-2019 |
| Wildfire | 2019-2022 | 2018 | 2016-2018 |
| Deforestation | 2020-2023 | 2019 | 2017-2019 |
| NDVI | 2020-2023 (and a 2021-2023 row, Q40 a) | 2019 | 2017-2019 |

- **First year (Y0):** 2003 on PM2.5, fire and NDVI; 2004 on defo (owner ruling N, S17 a: the K5 lag-2-year MOD44B
  columns are kept, so defo's inner fit is 2004-2016, 13 years).
- The settings each package's plan derived (filled from plan.json):
  - PM2.5 (derived.json **NOT FILLED: pm25 is not in this freeze**, plan.json **NOT FILLED: pm25 is not in this freeze**):
**NOT FILLED: pm25 is not in this freeze**
  - Wildfire (derived.json **NOT FILLED: fire has no plan (run 'py -3.9 -m treeroute plan' before the freeze)**, plan.json **NOT FILLED: fire has no plan (run 'py -3.9 -m treeroute plan' before the freeze)**):
**NOT FILLED: fire has no plan (run 'py -3.9 -m treeroute plan' before the freeze)**
  - Deforestation (derived.json **NOT FILLED: defo is not in this freeze**, plan.json **NOT FILLED: defo is not in this freeze**):
**NOT FILLED: defo is not in this freeze**
  - NDVI (derived.json **NOT FILLED: ndvi is not in this freeze**, plan.json **NOT FILLED: ndvi is not in this freeze**):
**NOT FILLED: ndvi is not in this freeze**

## 5. Scored units

- Scored units per group = max(10, floor(K x 100 / G)), with K = 20, capped at the units available (owner ruling E,
  L1). On defo, 4,285 replaces 100.
- That gives 15 per group on PM2.5 (1,905 units), 50 on fire (2,000), 2,040 on defo (85,680) and 15 on NDVI (1,995).
- The scored units are an evenly spaced subset of the bank units. The saved rows must score exactly the derived units
  (G-SPLIT on the outputs).

## 6. Headline metrics

- **MAE** is the headline score. It is also the selection score.
- Printed with it, always together: **anomaly R2** against the per-unit normal, **corr2**, and the **hit rate**.
  R2 is never reported alone.
- Each is printed **beside the guess-normal reference** (the per-unit normal) and beside the **last-5-years normal**.
  Predict-zero is printed beside MAE. At leads, persistence and damped persistence are printed too.
- Hit rate: the share of rows within the R32 tolerance (half the donor rows' mean absolute deviation from their own
  normal). A declared measurement floor is printed beside it (PM2.5 2 ug/m3; NDVI 0.02).
- Also printed: the calibration ratio, the pre-clip rate and the strict top-10% detection score (R33) with its event
  count. All three are in the headline and per-year tables (treeroute_report.table: headline, per_year and the
  markdown).
- **Per report stratum (R34, Q50).** Defo declares one report stratum, forest2000_px. Its strata are the donor rows'
  quartiles, right-closed (D73). The engine's report pass scores them from the same saved rows (per_stratum.csv). The
  table builder copies that table into its per_stratum table and the markdown. It checks the stratum columns against
  run_record.json and the edges against verdict.json, but it does NOT recompute these scores: the units' stratum
  values and the donor rows are not in the saved rows. The other three packages declare no stratum.
- Pooled over all scored rows is the headline. The macro value (unweighted mean over groups) is printed beside it
  (Q20 a). Scores are also given per test year and per group.
- The ladder is scored on the rows common to all leads, with all rows beside.

## 7. The single verdict (rule D74)

- One contrast decides: the adopted arm against its own link-matched trees-off (the guard reference; Q17 a). Per
  group: MAE(reference) minus MAE(adopted). Positive means the adopted arm is better.
- The tag follows the ruled rule D74. The tests run in this order, and the first one that holds gives the tag
  (treeroute/report/metrics.py contrast_tag):
  1. If the layer declined, the tag is "declined".
  2. **IDENTICAL:** every contrast is 0.
  3. **CANNOT TELL:** the CI cannot be computed (fewer than 3 groups).
  4. **EQUIVALENT:** the whole CI lies inside +-band. This is tested before HELPS and HURTS (F42).
  5. **HELPS:** the CI low end is above 0 AND the point estimate is at or above +band.
  6. **HURTS:** the CI high end is below 0 AND the point estimate is at or below -band.
  7. **CANNOT TELL:** everything else.
- **The band (Q22 b, R35):** derived from each package's FIRST headline run. It is the median jackknife SE of the
  arm contrasts (each tree arm against its own trees-off, each corrector against its placebo; identical contrasts
  left out). It is stored in registry/bands.csv. The nowcast band decides at every lead (F57).
- PM2.5's old band, **0.0395** (Part 556: hard split, 20 test groups x 100 cells), is printed beside PM2.5's band as
  history. It is never used for a verdict.
- The arithmetic normal and predict-zero are printed beside the verdict. Sign flips between groups are flagged.

## 8. Uncertainty: the jackknife over groups

- Leave-one-group-out jackknife at 1.96 (Q19 a), over ALL groups: 127 (PM2.5), 40 (fire), 42 (defo), 133 (NDVI).
- No multiplicity correction (Q21 a).
- Report only: the same jackknife with overlap blocks as the unit (the blocked jackknife). If its SE is more than
  20% above the group SE, the report flags "group jackknife may be too narrow". The group jackknife still decides.

## 9. The continuity row

- The old hard-split test groups are also scored alone, from the same run: 20 groups (PM2.5), 10 (fire), 17 (defo),
  44 (NDVI). The lists are in treeroute_report/continuity_groups.yaml.
- The row is labelled **"continuity, not a replication"**. It has its own jackknife over those groups. The package's
  band judges it; the band is not re-derived on the subset.
- The old test-unit totals are printed beside: 2,000 / 1,000 / 70,487 / 4,400.
- NDVI also gets a row without its two seen_during_design groups (thar_desert, greece_mainland; Q49).

## 10. Disclosures

- **Fire's shipped cell pick cannot be regenerated.** Its seed used Python's string hash. The engine uses the R18
  stride over all cells instead (owner ruling C).
- **The LORO budget departs from "the same total test cells"** (owner rulings D and E, L1). With K = 20 the scored
  totals are x2 on fire (2,000 against 1,000), x0.45 on NDVI (1,995 against 4,400) and x1.31 on defo (92,274 against
  70,487; Y0 2004, ruling N S17 a). PM2.5 is about the same (1,905 against 2,000). K = 20 comes from the size of the old hand splits, not from
  results.
- **Provider base periods** of anomaly and index columns are allowed, even when they reach past the cut, and are
  printed (Q43 a).
- **Livestock hold-2021 (owner ruling L3).** The 2022-2023 livestock layers are the 2021 layer times India's FAOSTAT
  ratios, applied to every region, so they are not used. Each package uses engineered columns that hold the real
  2021 layer for 2022 and 2023. They are lagged one year and listed ("watch").
- **No multiplicity correction** across packages, leads or rows (Q21 a).
- **The A7 bias.** The decision surface uses one bank. Neighbouring groups' trees know the inner-score years, so the
  surface flatters trees. The bank is refit at the inner cut (owner ruling E, L6 b) at every lead (H2).
- **The GLS weight model, c and s (ruling E, L5).** The sigma served on a row the forest was fitted on is its
  out-of-bag prediction (L5 c). The forest's training rows include the scored units' own fit rows. The log link's
  c (R23) and the guard scale s (R36) include the scored units' fit and inner-score labels (history up to the cut,
  which L5 allows). This is not a test-window leak (L5).
- **Test-exposed constants and lists** (plan 7.2): the region penalty centre (lambda 100), the per-unit and
  neighbour centres (0.5 / 0.25), the 60,000-row region budget, the inner-cut bank refit (A7.inner_cut_bank_refit),
  fire's 2018 cut, PM2.5's GFED burn block, NDVI's top-5 router context list, and the continuity lists themselves.
  Appendix B copies plan 7.2's table with the reason each item is exposed.
- Every run's own limits, build departures and listed columns are printed in its report (treeroute_report.table,
  "Disclosures").

## 11. What counts as a bug fix after the freeze

- From the freeze on, only bug fixes are allowed (plan 8.1 M5).
- A bug fix is a code change that makes the engine do what an approved signature, an owner ruling or a written rule
  already says. Examples: a crash, a wrong index, a guard that refuses a valid input, a record written wrongly.
- These are NOT bug fixes: a new or changed constant, rule, threshold, ban verdict, column fact, link, arm, lead,
  test year, scored-unit count, metric or verdict rule; a new package file; anything chosen after seeing a result.
  Such a change needs a new pre-registration Part before any affected run.
- Every bug fix is logged as its own Part, with the output of `py -3.9 -m treeroute_report.freeze verify`.
- A bug fix re-runs every package already run, unless the no-op rule holds for that package: its derived.json and
  smoke outputs stay byte-identical, AND either a one-group full-width probe stays byte-identical or the changed
  functions are shown never to run on that package at full size.

## 12. Items still open (each must be settled before the freeze)

Each item starts with its marker; the freeze refuses while any marker remains (F-PREREG). "Freeze also checks" names
the precondition that refuses by itself while the item is open. "By hand" means the freeze sees only the marker: the
owner checks the item before its marker is removed. Counts are from 2026-10-06; refresh them on the day of signing.

1. Settled (ruling N, S17 a): defo's first year is 2004; the K5 lag-2-year MOD44B columns are kept. F-PLAN checks
   only that the plan is current, not which Y0 it derived.
2. Owner decisions settled (ruling N: S1-S6, S9, S15, S27-S29, N1, N2): the timing facts are signed as recommended.
   What remains is checked by the freeze itself, not by a marker: G-FACTS on the new deep reports (item 11).
   As it stood before the ruling, freeze also checks: G-FACTS (it must say "pass") and
   F-CHECK-GREEN. On 2026-10-06 the deep check (run 07:44-08:02 local time by the check reviewer, engine code
   6bc240564ffa) refused G-FACTS on all four packages. Kept columns with unverified timing facts: PM2.5 90, fire 91,
   NDVI 387, defo 261. Kept columns with 'assumed' facts and no reviewer: PM2.5 7 (the six aglw_*_hold2021 columns and
   burn_lag1), fire 6, NDVI 91, defo 48. The quick check on PM2.5 also found 99 kept columns with no
   co_measured_with_target answer, and a target legal range with no cited source. Still open from the ruling-L
   report: the defo reading of "signed" (L_REPORT.md 5.1), the hold columns (5.4), the other engineered lag columns
   (5.5) and defo's K4 land-cover rows (5.6).
3. Settled (ruling N, S19 a): run_record.json counts the last-value fills (ruling J2 d) over the rows the run reads
   (the picked bank units' rows), and that count is the disclosed record.
4. Settled (ruling N: S10, S11, S13, S14, S16, S18): the sign-off tool marked each note below closed in the ban
   lists. Freeze also checks: F-BAN-OPEN. It reads every line,
   comments included, and a stale note refuses until it is updated. On 2026-10-06 it finds 20 lines:
   - PM2.5 line 23: three agent choices that await your confirmation: phenology_sos_doy, deeprec_twsa and
     spei_24m_lag12 are 'watch' rather than 'keep'. Confirm them or change them.
   - PM2.5 line 9: "DECISION pending" on phenology_sos_doy. Stale: ruling L2 has since made it conditional, so the
     note needs updating (C1).
   - PM2.5 line 21: index windows that "await the owner's signature". Stale: ruling L1 signed them, so the note
     needs updating (C1).
   - PM2.5 line 44, fire line 69, NDVI line 58: "REASON WORD (owner check)" on the raw aglw_* columns (item 8).
   - NDVI lines 357 and 368: snow_cover_fraction's polar-night gaps (keep as watch, ban, or hold conditional).
   - Defo header, three "OWNER item" notes: line 49 (the K3/K5 store columns, which the G-LINEAGE stand-in never
     checks), line 54 (L3's 'incomplete' reason word, item 8) and line 57 (L1: the file and the package's facts carry
     no reviewed_by).
   - Defo evidence, three more "OWNER item" notes, each on three columns: lines 1391, 1395, 1399 (the features
     store's deeprec_twsa_mean/_min/_max: reason lookahead_unfixable or target_derived); lines 1693, 1697, 1701
     (deeprec_twsa_k3_*: built by features/build.py they would be refused G-CLOSED); lines 1705, 1709, 1713 (the K5
     lag-2 columns: built by features/build.py they would be refused G-LINEAGE).
   - Not read as open: the bare words "OWNER CHECK", which the lists also use to cite the review sheet's column
     ("the 2023-vintage OWNER CHECK is moot"). Defo line 18 is one: its eddi_observed check is closed by line 56 (L4).
5. Settled (ruling N, S12 a): the guard tolerance constant k (C9.guard_tolerance_k) is 5.230771281733543e-08. Freeze also checks: F-CONSTANTS (it refuses while any engine constant is unset).
   engine_constants.py fixes k by a measurement, not by a choice: the identity gate of the first shipped nowcast
   stays at 1e-6, and k is at least 10x the measured arithmetic error (R36).
6. Settled (ruling N, S21 accept): the build departures are ruled acceptable and moved to pipeline/run.py
   ACCEPTED_DEPARTURES; DEPARTURES is empty, and only split_view (a probe's excluded groups) still marks a run not
   headline. The departures were: the quick and deep checks not run by the pipeline (quick_checks), the GLS kernel, the private router
   kernels, the band source (registry/bands.csv), the nearest-donor distances and distance bands (report_rows), the
   ladder's H2/H4 readings, the pre-Y0 label reading (model_labels) and the split-view reading (pipeline/run.py
   DEPARTURES). By hand: the freeze does not read them. The table builder refuses any run that carries a
   not-headline reason (pipeline.record.check_headline_run), so no headline table is built while one remains.
7. Settled for fire (ruling N S8, rulings O1 and O2): every fire exceptions.yaml entry is signed (8 entries). Ruling N
   (S8) signed the 7 entries that were already true (0 'R6 (donor train end)', 2 ntl, 3 hdi, 4 fert_n, 5 fert_p,
   6 luh2_urban, 7 grace_lwe); the owner read the refreshed entry 1 ('L3 hold:') in short form
   (engine/S8_REFRESHED_17.md) and approved it (ruling O1); it was installed and signed by
   datasets/_tools/apply_signoff.py on 2026-10-06. Ruling O2 (2026-10-07): the operation texts of fire's 7 history
   look-backs (tslf_months, tslf_censored, last_burn_month, last_burn_size, n_burns_12mo, n_burns_60mo,
   burn_rate_120mo) now say what they are in plan 1.5's words, event counts or months since the last event, at label
   lag 2. Text only: no stored or computed value changed (the store D:/fire_history_lag2 was not rebuilt). The store
   catalog (ingest/fire_history_store_catalog.yaml) was regenerated by build_history.py's 'catalog' command and its 9
   kept columns re-signed with the same ruling N answers (S5, S9); it now pins sha256 c93a2bd7... in dataset.yaml
   (ruling N S9 named the first, unsigned catalog b1defb80...). The new disclosures for the S1, S3, S6 and S28
   changes concern defo only. pm25, defo and ndvi: not in this freeze. By hand.
8. Settled (ruling N, S13): the reason word on the raw aglw_* columns is 'incomplete'. Freeze also checks: F-BAN-OPEN, through the notes listed in item 4
   (PM2.5 line 44, fire line 69, NDVI line 58, defo line 54).
9. Settled (ruling N, S20 b): the 17 engine constants are marked confirmed (status 'cited') in engine_constants.py;
   the paper states that the owner fixed them before the run. As it stood before the ruling: Two have status 'proposed'
   (C15.missing_flag_share 0.25, R30; C15.fallback_min_units_for_search 10, R12; plan 9.1 item 2f). Fifteen have
   status 'extra': numbers the plan's rules name that are missing from the 3.1 table, marked "OWNER CONFIRMS each"
   in engine_constants.py (S2.history_last_values, S2.history_trailing_years, S2.log_c_quantile,
   S2.link_distinct_values_above, S2.recent_normal_years, S2.hit_tolerance_deviation_share, S2.detection_top_share,
   S2.detection_min_events, S2.detection_max_event_share, S2.jackknife_z, S5.sentinel_mask_abs,
   S5.sentinel_flag_abs, S5.cadence_constancy_tolerance, S5.support_min_distinct_values,
   S1.unit_id_latlon_decimals). The freeze does not refuse on these statuses. It prints them, lists them in the lock
   and fills this line from the lock: none. Choose one:
   - (a) confirm them by signing this Part (today's behaviour);
   - (b) confirm them in engine_constants.py before the freeze (status 'cited');
   - (c) make the freeze refuse while any of them remains (add the status words to CONSTANT_STATUSES_REFUSED in
     treeroute_report/freeze.py).
   By hand: under (a) or (b), remove this item's marker once chosen.
10. Settled (ruling N, S22): the plan 3.3 flags are Appendix A, with the N1 and N2 rules and the S1, S3 and S6
    flags.
11. Settled for fire (ruling M2): the fire deep check runs on its R21 smoke groups (the first 4 in sorted order:
    alaska_interior_taiga, amazon_basin_brazil, angola_zambia_fire_belt, australian_bushfire_belt), with the quick
    checks on the whole package, at the package fingerprint and engine code this freeze locks. Both were run on
    2026-10-07 after the ruling O2 rewording (package fingerprint 18c7bbb8634c, the engine code of PM2.5's freeze,
    7b508557): quick green with G-HIST 'pass'; deep green (306 s) with G-FACTS 'pass' and the G-HIST sample 'pass'.
    A real-package smoke the same day exited 0 with every prediction file written. Freeze also checks:
    F-CHECK-EXISTS, F-CHECK-CONTRACT, F-CHECK-MATCH (the report's engine_code_sha256 must equal today's),
    F-CHECK-GROUPS (owner ruling M2, OWNER_RULINGS_2026-10-06.md), F-CHECK-GREEN and G-FACTS, and records the report's
    hash in the lock. pm25, defo and ndvi: not in this freeze; their deep checks are gated by their own freezes.

## Appendix A. The plan 3.3 flags as rows of their own

Copied from APP_PLAN.md 3.3 ("Flags in plain words") on 2026-10-06, one row per flag, with the rulings that changed
a flag since the plan was written (last column). After them come the rows that SIGNOFF_REVIEW.md S22 adds under owner
ruling N (OWNER_RULINGS_2026-10-06.md section N, "yes to all"): the N2 static-map dating rule and the S1, S3 and S6
flags. Where a row and a ruling differ, the ruling wins.

| # | Flag (plan 3.3, copied) | Since the plan |
|---|---|---|
| 1 | Fire's inner window becomes 3 years (2016-18) instead of 2. It follows PM2.5's rule. The router's inner fit shrinks from 180 to 156 rows per cell. | unchanged |
| 2 | Fire's first year becomes 2003. Once annual columns are lagged (Q3 a), 2002 has no source year, exactly as for PM2.5. Fire keeps 192 rows per cell at the test cut instead of 204. | unchanged |
| 3 | Fire's bank units become 100 per group by stride, in every group, and 50 of them are scored (LORO). That replaces 125 random test cells and a positive/negative donor sample. The shipped picks survive only in the harness. | unchanged |
| 4 | Defo's bank units become 4,285 per group (every group; all cells in the 4 smaller groups), and 2,040 of them are scored (LORO). This replaces 4,000 test cells and a 1.5M-row donor pool. On the inner surface the rule fills the region router's 60,000-row budget without a cap. At the test pass the router keeps about 3,529 evenly spaced whole cells. New: the test-pass router now strides whole cells (the shipped test pass took 60,000 evenly spaced ROWS, adaptation.py:1149-1150, so a kept cell could lose some of its years). Both passes see about the same row budget. The banks are rebuilt anyway. | ruling N S17 a (defo Y0 2004, 13 inner-fit years): 4,615 bank units and 2,197 scored units per group, about 3,750 whole cells at the test pass; 92,274 scored units in all (x1.31 of the old 70,487) |
| 5 | Every package's history block gains one column: the mean of all history so far. Defo needs it to keep h_cum's information (Q12: nothing is lost). The others get it because the block is uniform. | unchanged |
| 6 | NDVI's history block may start one month earlier, if the M0 audit finds that V11's 16-day composites reach into the following month. | ruling B item 8 a: V11/V12 carry a 15-day reach in the store catalog |
| 7 | Defo's conflict_* and eddi_observed are flagged by the missing-value rule (conflict_* is stored as zeros, not blanks, in 35 of 42 regions; eddi_observed in 31). The shipped run used those values as they are. The Q34 review rules on each: keep with evidence or ban. | settled in defo/ban.yaml (eddi_observed: ruling L4) |
| 8 | NDVI's router context: the column that copies the normal is replaced by the engine's normal column (same information, from fit rows only). The top-5 driver list stays as shipped. It is disclosed as picked from a bank that had 19 test regions as donors (F15; cross_region_run89.py:887). | ruling N S11: the empty ctx:climatology row is removed |
| 9 | Short-history units in a per-unit dataset use their group's region router, not the donor-wide mean. It is pooled over the group's 100 bank units, and its level is searched on the region grid over the fallback units (R12). None are expected on PM2.5 or NDVI. They are counted on fire, whose unmapped labels are now NaN. | unchanged |
| 10 | Every bank's seeds change: the bag, tree and corrector seeds all come from the group's name and the tree number (R19). The banks are rebuilt anyway. | unchanged |
| 11 | PM2.5's band is re-derived from its headline run (Q22 b), with 0.0395 beside. | ruling N S21: the band is the first headline run's own |
| 12 | PM2.5's log1p check leaves the product and becomes a report-only check in the harness (c = 1.5, Part 558). | unchanged |
| 13 | Coral (optional track only): a 2016-19 test window; leads of 183 and 365 days; LORO folds from one bank cut at the inner-fit end; a strict pool with no labels after the cut; a pool under 12 rows falls back to the donor-row median; MMM as penalised context; max_features 0.15 to 0.10, and 500 to 100 trees per group. Whether coral runs under these is decided at M6b. | out of this Part: coral gets its own Part (ruling H1 b) |
| N2 | Static-map dating rule (owner ruling N2): physical maps (terrain, soil, rivers, coast, and the grid's own coordinates) are timeless; maps of human-built things carry a content date and are checked against every cut. The store catalog writes content_epoch 'timeless' on the physical maps and a content date on the human-built ones (GMIA irrigation about 2005, travel_time 2015, GRIP4 roads 2018 as an upper bound, power plants 2020, dams and reservoirs 2024 and oil and gas wells 2023 as release-year upper bounds, coal mines 2026-05, protected areas 2026-06). G-EPOCH refuses an entering static column that is neither. Release dates are not recorded on SoilGrids or MERIT. | new (ruling N) |
| S1 | defo's scPDSI aggregates (scpdsi_mean/_min/_max) are banned lookahead_unfixable: scPDSI's backtracking (Wells 2004) lets a month's value change with later months, so no lag removes the look-ahead. The other climate and water timing facts are signed as written. | new (ruling N S1) |
| S3 | defo's 4 MODIS land-cover columns (MCD12Q1/MCD12C1) are banned lookahead_unfixable: the labels are smoothed across years, so no lag removes the overlap (this re-rules K4). The 15 other satellite columns are signed as written. | new (ruling N S3) |
| S6 | defo's lag-1 vegetation aggregates overlap the predicted year by at most 3 days (NDVI/EVI) or 8 days (albedo/GPP), from December: under 1% of the year, accepted and disclosed. MOD44B's 2-month overlap was not accepted (lag 2, K5). defo's population_density is lagged 1 year (as J3). | new (ruling N S6) |
| N1 | pdo enters at lag 2 on the monthly packages: PSL's pdo.data is ERSSTv5-based, so it carries the ERSSTv5 filter reach of +2 months, like nino34. defo stays at 1 year. | new (ruling N N1) |

## Appendix B. Test-exposed constants and disclosures (plan 7.2)

Copied from APP_PLAN.md 7.2. The engine manifest prints each engine constant's id, value and test-exposed flag
(no problem names); package exposures are disclosures in each package's exceptions.yaml. The last column says how
an owner ruling has changed the item since the plan was written.

| Item | Kind | Origin | Exposure | Since the plan |
|---|---|---|---|---|
| Region penalty centre lambda 100 (C12.region_lambda_centre) | engine constant | adaptation.py:1214 | coincides with defo's pooled test-window argmax (CLAIMS_LEDGER.md:610); defo's inner picks sit below the grid (Q13, Part 527) | unchanged |
| Per-unit and neighbour centres 0.5 / 0.25 (C12.per_unit_*_centre, C12.neighbour_*_centre) | engine constant | fire_architecture.py:102-103; adaptation.py:1434 | fire's shipped router; exposure not documented | the neighbour kind is not used by these four packages (R12) |
| 60,000-row region budget (C7.region_router_row_budget) | engine constant | adaptation.py:1213 | defo's shipped budget; exposure unknown | unchanged |
| LORO scored-unit budget (K = 20) | engine constant | owner ruling D ("the same total as the old hard split") | K = 20 comes from the size of the old hand splits (PM2.5's 20 test groups; the geometric mean of the four old counts is 19.5), not from results. About the old total on PM2.5 only (x0.95); fire x2, NDVI x0.45, defo x1.31 (ruling N S17 a). The old totals are printed beside the new ones | K = 20 chosen by owner ruling E, L1 (section 5) |
| Continuity groups | package list (reporting only; treeroute_report/continuity_groups.yaml) | the old hand splits | PM2.5's split v3 rule was written after the 2020-23 screen for all 127 regions (CLAIMS_LEDGER.md PM-10); fire's list used 2020-23 screen gains before v3 (HANDOFF_ERRATA.md 8.9). Reporting only, never a fit or a decision | unchanged (section 9) |
| One bank at the donor train end (A7) | engine design flag | pm25_adaptation.py | the inner surface flatters trees, and the penalty and weighting picks share this bias; the GLS error target (R25) is built from the same bank's trees. Under LORO, adjacent and overlapping groups lend trees trained on the inner-score years (2017-19), while the 2020-23 test window gets no such help | owner ruling E, L6 b: the bank and correctors are refit at the inner cut for the inner decision (engine constant A7.inner_cut_bank_refit, test-exposed), at every lead (H2) |
| Weight model, c and s fitted on rows that include the scored units' own fit rows (LORO) | engine design flag | R25, R23, R36 | the sigma weights on a scored unit's own fit rows would be in-bag forest predictions; c and s include its inner-score labels. Not a test-window leak | owner ruling E, L5 c: the sigma on a row the forest was fitted on is its out-of-bag prediction (section 10) |
| Group jackknife over neighbouring groups (LORO) | report design flag | Q19 a, R34 | the ruled jackknife treats neighbouring and overlapping groups as independent, so its band may be too narrow | the blocked jackknife is printed beside, report only (section 8) |
| Rival tuning (LORO) | rival design flag | 4.6 | hyperparameters tuned once on pre-cut rows of groups that a fold model later never saw | out of this Part: deferred to M8 by owner ruling E, L3 |
| Coral's route penalty | package disclosure (coral) | coral_architecture.py:383-397 | sweep scored on test rows | out of this Part: coral gets its own Part (ruling H1 b) |
| Fire's <= 2018 cut | package disclosure (fire; the value itself is derived by R6) | Q10 a | chosen knowing earlier results | unchanged |
| PM2.5's GFED burn block | package disclosure (PM2.5) | Q25 b | entered through a 2020-23 screen | unchanged |
| NDVI's top-5 context list | package disclosure (NDVI; data_selected) | cross_region_run89.py:887 | picked from a bank with 19 test regions as donors (F15) | unchanged |

## 13. Signature

- Signed by the owner (ruling O3, 2026-10-06)
- Signed by: ____________________ (owner)
- Date: ____________________
- SHA-256 of this filled file: written into the Part log by the owner after signing.
- Part number: assigned when the Part is logged.
