# Freeze sign-off sheet (2026-10-06, second version)

Everything that still blocks the freeze on PM2.5, fire, defo and NDVI, plus two leaks found in review. One reply
answers it. Nothing here is signed and no package file was edited. Counts come from the quick check on a frozen copy
taken at 15:47 (D:/treeroute/signoff_20261006/frozen3). Details for each item are in Appendix B.

## Short answer

- **Time:** about 1.5 working days after you answer, then about 51-65 machine hours for the four runs.
- **One reply works:** "yes to all" takes every RECOMMENDED answer. Or answer by ID: "S9 b, S28 b, rest yes".
- **Every refusal the checks print today is an owner item.** No engine fault refuses.
- **Tested on a scratch copy** with the recommended answers written in (S9 left open), never on the real packages:
  the quick check is green on PM2.5, defo and NDVI. Fire waits only for S9. The deep check (the `check --deep`
  command, on the smoke groups) is green on the same three; on fire it refuses only S9's rows. The freeze, run on all
  four with those reports, refused only the 12 pre-registration markers (S22) and fire's S9.
- **ATTENTION:**
  1. **Two new leaks no check catches (S28, S29).** defo's phenology at lag 1 can hold data from the year it
     predicts. road_density is a road map from about 2018, later than every package's guard cuts.
  2. **S8 needs a refresh first.** 17 of the 45 disclosures still describe the state before rulings L1 and L3, or
     say "OWNER DECISION". The tool refuses to sign them as written. An agent rewrites them to the rulings first.
  3. **S9 a needs fire's history store built first** (two commands, about 10 minutes, at D:/fire_history_lag2).
  4. **Writing the answers breaks 60 tests** that check the unsigned state (measured). The tool lists them; each
     package task updates its own (about half a day, in parallel). 31 more fail until the drafts are refreshed, then
     pass.

## Blocking the freeze (each one refuses until answered)

| ID | What it is | RECOMMENDED | If the answer is wrong |
|---|---|---|---|
| S1 | Timing facts of the climate and water columns | yes | a few days of look-ahead |
| S2 | Timing facts of the climate indices and sea temperatures | yes | 1-2 months of look-ahead |
| S3 | Timing facts of the satellite land and fire products | yes (**least sure of S1-S4**) | a few days of look-ahead |
| S4 | Timing facts of the human, land-use and static columns | yes | little: yearly columns lag a year; maps: S27, S29 |
| S5 | Derived columns: lags, rolls, holds, defo's yearly columns | yes | a child is wrong where its parent is |
| S6 | "Measured with the target?" on every kept column that changes in time | yes: PM2.5 burn_frac, defo's 12 vegetation columns; no: the rest | see the flag in B |
| S7 | A source for PM2.5's target range | "never negative; no upper bound" | a reviewer may ask for the ACAG citation |
| S8 | The 45 disclosures in exceptions.yaml | yes, after the refresh | NDVI stays refused (G-FACTS) |
| S9 | Fire's 19 history rows have no store | a: you build it | b drops the burn-history features |
| S10 | defo: 10 rows with no data, 2 data columns with no row | yes | nothing: all banned or unread |
| S11 | NDVI: an empty ctx:climatology row | yes: remove it | nothing |
| S12 | The guard tolerance k is unset | a: 5.230771281733543e-08 | it also changes every smoke's tolerance |
| S13 | Ban reason on the raw livestock columns | incomplete | post_window_snapshot: every run refuses the hold columns |
| S14 | PM2.5 ban-list notes: 3 'watch' choices, 2 stale notes | confirm watch | none |
| S15 | NDVI snow: winter gaps in 5 Arctic groups | watch (**unsure**) | there the fill says "no snow" in deep snow |
| S16 | defo ban-list notes | lookahead_unfixable | none |
| S17 | defo's first year | a: 2004 | b drops tree cover from two years back |
| S18 | defo and the word "signed" | a: signed like the others | b keeps defo refused |
| S19 | What the last-value count covers | a: the rows the run reads | b needs one more engine pass |
| S20 | 17 engine constants awaiting you | b: mark them confirmed now | none for the run |
| S21 | Build departures | accept (**unsure: weighted GLS solve**) | a reviewer can challenge one |
| S22 | Pre-registration Appendix A and its 12 markers | yes | the freeze refuses while a marker is left |
| S27 | Fire's travel_time is a 2015 map, later than fire's guard cuts | ban on fire | - |

## Leaks no check catches (settle them before the freeze)

| ID | What it is | RECOMMENDED | If the answer is wrong |
|---|---|---|---|
| S28 | defo's phenology at lag 1 can hold data from the year it predicts | a: a lag-2 column (with S17 a) | kept: a possible leak on every defo row |
| S29 | road_density is a ~2018 map, later than every guard cut; no date recorded | a: record 2018, ban on all four | kept: the guard sees roads built after its cut |

## Not blocking (no answer needed)

| ID | What it is | RECOMMENDED |
|---|---|---|
| S23 | A lag-12 or hold column whose record ends after a cut: G-EPOCH flags it | treat it as the record end |
| S24 | PM2.5 burn_lag1 repeats the lagged burn_frac | out |
| S25 | Fire's joined store holds only banned columns (a flag) | leave it |
| S26 | For the record: three false or harmless flags (B) | noted |

## After you answer, in this order

1. You: for S9 a, run fire's two history commands (about 10 minutes).
2. Agent: refresh the 17 stale disclosures to the rulings and your answers (S8; about 1 hour).
3. Agent: copy `datasets/_tools/signoff_answers_TEMPLATE.yaml`, fill in your words, run
   `py -3.9 datasets/_tools/apply_signoff.py <answers>` (dry run), then with `--apply`. Old files are moved aside,
   never deleted. Run it again after fire's store is declared and after the S28 a column exists.
4. Agents, in parallel (about half a day): the follow-ups the tool prints (defo's lag-2 phenology column, defo's
   expected values, generators that keep the signatures, DEPARTURES, the G-EPOCH flag, Appendix A and the markers),
   the drafts (refresh_drafts.py), and the 60 tests the tool lists (Appendix E).
5. After the last engine change: quick and deep checks on all four (`check`, `check --deep`), one full test suite
   (about 30 minutes), the 3-group probes (ruling M1, not yet measured), then the freeze.

## How much time until the headline runs

- **Your part:** about 15-30 minutes.
- **Before the first headline run:** about 1.5 working days of agent and machine time. If you answer by the morning
  of Wed 7 Oct, fire's headline run can start about Thu 8 Oct.
- **The four headline runs:** about 51-65 machine hours: plan 4.5 prices the engine as built at 46.2-58.7 h, and
  ruling L6 b adds 5.0-6.6 h. Up to about 72 h if a weighted forecast arm is pinned (+3.8-6.6 h).
- Cheapest first: fire 3.3-4.1 h, PM2.5 8.6-11.7 h, NDVI 14.8-18.2 h, defo 14.6-19.9 h (41.3-53.8 h together),
  plus about 5 h for the engine as built and 5-7 h for L6 b, spread over the four.
- That is about 2-3 days non-stop, or 6.5-9 days at 8 machine hours a day. The plan also keeps about 20 h for bug
  fixes. None of this is proven until the probes measure it.

## Appendix A. Counts

**G-FACTS today** (quick check, frozen copy 15:47). Kept columns with unverified timing facts, plus 'assumed' with no
reviewer: PM2.5 90 + 7, fire 91 + 6, defo 261 + 48, NDVI 387 + 91. Unanswered "measured with the target": 99 / 98 /
266 / 479. PM2.5's target range has no source.

**What the recommended answers write** (dry run, 24 files):

| Group | PM2.5 | fire | defo | NDVI |
|---|---|---|---|---|
| S1 | 42 | 44 | 51 | 45 |
| S2 | 13 | 13 | 14 | 12 |
| S3 | 1 | 2 | 18 | 3 |
| S4 | 32 | 29 | 24 | 29 |
| S5 | 8 | 8 | 295 | 388 |
| S6 no / yes | 97 / 1 | 98 / 0 | 253 / 12 | 479 / 0 |
| S8 | 11 | 8 | 9 | 17 |

PM2.5's S6 is 98, not 99, because S24 takes burn_lag1 out. S4 leaves out road_density (S29) everywhere and
travel_time (S27) on fire. Signing counts include the parents a kept derived column needs.

The panel store catalog is shared, so one signature covers every package: S1 51, S2 14, S3 19, S4 32 of its columns.

| Group | Families (columns in the shared catalog) |
|---|---|
| S1 (51) | TerraClimate 12, AgERA5 11, ERA5-Land 11, GPCC SPI 5, SPEIbase 5, derived water balance and seasonality 6, CRU scPDSI 1 |
| S2 (14) | ERSSTv5 sst_anom_* 8, NOAA nino12/3/34/4, oni, amo 6 |
| S3 (19) | FireCCI 3, MOD44B 3, MCD12Q1 3, MOD11C3 LST 2, MOD13C2 NDVI/EVI 2, MCD12C1 1, MCD43 albedo 1, MOD08 cloud 1, MOD10 snow 1, FluxSat GPP 1, night lights 1 |
| S4 (32) | soil 9, LUH2 6, terrain 4, fertiliser 2, MERIT 2, UCDP 2, GDP, HDI, WorldPop, GMIA, travel time, coast, lat (parent of ctx:lat) 1 each |
| S5 | PM2.5 and fire: 6 holds + 2 router context each. NDVI: 345 lags, 18 rolls, 6 water-year-to-date, 4 water-state, 6 holds, 9 router context. defo: 18 lag-1 + 6 holds (build.py), 229 features-store and 42 K-store columns |

Every edit, with its file and group: D:/treeroute/signoff_20261006/SIGNOFF_COLUMN_EDITS_2.csv. The dry run behind
these counts: D:/treeroute/signoff_20261006/dryrun_recommended_FINAL3.log.

## Appendix B. Each item in detail

- **S1-S4.** Seeded from the panel builder code on 2026-09-28; not checked against the provider pages. S3: MODIS
  composites can reach a few days past the month end; their windows are already widened by hand. S4: a static
  column counts as timeless only when it records no date; two maps carry one (S27, S29).
- **S5.** Feature-script outputs are signed through a marked SIGNOFF block added to the end of features/build.py.
  defo's two generated catalogs are edited directly; their generators will call them stale until they learn to keep
  the signatures (a defo task, and most of the defo tests in Appendix E).
- **S6, the flag.** A 'yes' only floors a column at 1 step. It does not stop a lag-1 value from reaching into the
  step it predicts. Three cases reach in. PM2.5 burn_frac: up to 1 month (its signed reach; you ruled this in J1 and
  L1). defo's 12 NDVI, EVI, albedo and GPP yearly columns: 8-15 days, from their January composite (recommended:
  accept; the written reason says so). defo's phenology: up to a whole year (S28). One 'no' a reviewer could
  question: defo's population_density. WorldPop spreads people with same-year land cover, the way J3 called AGLW
  co-measured on defo. You ruled it not a leak by measurement (Part 437, within-cell rho 0.0076), so 'no' stands with
  that reason written. Lag and hold columns get 'no' (a 'yes' would push them one step further back). defo's three
  lag-2 tree-cover columns get 'no' because their content ends before the year, not because MODIS is unrelated.
  Tested: no lag moves.
- **S7.** The ACAG V5.GL.06 documentation is not in the repository. Add its citation if you want one.
- **S8.** 45 entries: PM2.5 11, fire 8, defo 9, NDVI 17. The tool refuses these 17 as written: PM2.5 3 and NDVI 6
  (epo: "until the owner signs" its window; L1 b signed it); PM2.5 5-10 and NDVI 10-15 (livestock before L3: raw
  columns "kept as watch", "the 2022 layer IS read", "the data fix is an OWNER DECISION"); fire 1 (calls the banned
  raw columns 'watch'); NDVI 5 (snow: "OWNER DECISION OPEN" until S15); defo 8 ("OWNER chooses": record the S16
  choice). The refresh only writes down rulings already made; the dry run shows every entry before it is signed.
  Unsigned: NDVI's top-5 list stays refused (G-FACTS), defo's K5 columns stay a flag (G-LINEAGE), pre-registration
  item 7 stays open.
- **S9.** a: from the engine folder, `py -3.9 datasets/fire/ingest/build_history.py datasets/fire
  D:/fire_history_lag2` (about 10 minutes, about 2 GB on D:, 2.5 GB of RAM), then `py -3.9
  datasets/fire/ingest/build_history.py catalog datasets/fire "D:/fire_history_lag2/{group}.parquet" --every-unit`.
  The tool then declares the store, switches the 9 kept columns and drops the 4 lag-1 rings the store never holds.
  It runs again to sign the 9 new columns. Built elsewhere, the path in the answers file changes with it.
- **S10.** Remove the 10 banned rows no store holds (grace_lwe_*, h_cum, h_lag1-3, is_train, land_px, y). Add banned
  rows for month and grace_lwe. The panel stays declared: defo's store builders need it.
- **S12.** The candidate keeps PM2.5's nowcast gate at exactly 1e-6; the leads become 0.9999e-6 and 1.0012e-6, both
  above the 10x error floor. Agent C1 left k unset on purpose: one k moves the lead gates off 1e-6 and changes every
  smoke's tolerance (smokes use a per-cut stand-in today). b needs an engine change; c keeps the freeze refusing.
- **S13.** 'incomplete' (the record ends in 2021) departs from L3's literal word. With post_window_snapshot, every
  run refuses the 6 hold columns: the lineage stand-in refuses a feature built from such a ban, and no disclosure
  lifts that. Only an engine change (backward-only holds) would. The lag-12 parents' 'incomplete' is J2 a's own word.
- **S14.** Confirm 'watch' for deeprec_twsa and spei_24m_lag12 (phenology is out by L2); mark lines 9 and 21 settled.
- **S15.** J2 d bans long seasonal masks (eddi, aridity: winter months everywhere). Here the long gaps sit in 5 of
  133 groups, 4-13% of their labelled rows after the fill. In those rows R30's zero-fill says "no snow" when the
  truth is near-full snow. Read J2 d literally and the answer is 'ban'.
- **S16.** deeprec_twsa_mean/_min/_max keep 'lookahead_unfixable' (stale stored facts); the K3 and K5 notes close
  with S8.
- **S17.** K5's lag-2 MOD44B columns give Y0 2004 (13 inner-fit years, not 14).
- **S19.** The record counts the fills over the rows the run reads (the bank units), disclosed.
- **S21.** The departures in pipeline/run.py: checks not run inside the pipeline, the weighted GLS solve, private
  router kernels, the band source, report rows, the ladder's H2/H4 readings, the pre-Y0 label reading, and
  split_view (it fires only when split.yaml excludes groups; none do today). Accept: the freeze runs the checks and
  locks the hashes; the band is the first headline's own; report rows come from saved predictions. The weighted GLS
  solve is new code: read its note first.
- **S22.** An agent writes Appendix A from plan 3.3 and removes each marker once its item is settled.
- **S27.** Fire's lead-6 and lead-12 guard cuts are 2015-07-31 and 2015-01-31, before the 2015 map. PM2.5, NDVI and
  defo cut in 2016, so it passes there. 'freeze' (R9) needs a dated version at or before each cut; with one date I am
  not sure R9 can pick one. Tested: with the ban, fire's deep check refuses only G-CLOSED (S9).
- **S28.** The signed window (J2 b, L1 a) lets each year's value use data up to a year after that year. R8 gives lag 1
  year: it allows a driver whose content ends with the predicted year. So last year's value can see the predicted
  year. K5 moved MOD44B to lag 2 for a 2-month overlap; this one can be a whole year. BAN_INSTALL_REPORT.md 9.5
  listed "lag 1 vs 2" as open. a: the raw column goes out (conditional) and a defo task adds phenology_sos_doy_lag2
  in features/build.py, like the J2 a lag-1 columns (about 1-2 hours with tests). With S17 a, Y0 stays 2004. b: out.
  c: keep lag 1 with a disclosure (nothing shows the overlap is harmless). With S17 b take S28 b: the tool refuses
  S17 b with S28 a, because Y0 would move back to 2004.
- **S29.** GRIP4 (Meijer et al. 2018) is one road map compiled about 2018 (repo note DRIVERS_TO_ADD.md item 24); its
  source dates are not in the repository. No content date is recorded, so G-EPOCH cannot see it. Guard cuts: fire
  2015, the others 2016; fire's lead-6 and lead-12 fit cuts (2018-01, 2018-07) are earlier too. defo's ban list
  calls it "a pre-window content epoch", which no fact records; fire's says "G-EPOCH checks their content epoch".
  a: record 2018 on the shared catalog and ban it on all four (post_window_snapshot), as travel_time on fire. The
  cost: road density is a known deforestation driver, and the shipped defo and fire runs used it. b: keep it, with
  one disclosure per package. Not checked: soil (SoilGrids) and irrigation (GMIA) maps also record no date; terrain
  and coast are timeless.
- **S23.** Read literally, D42 refuses the lag-12 and hold columns that J2 a and L3 asked for.
- **S24.** Both columns hold month t-1 since J1. Keeping it is a harmless duplicate; t-2 needs a code change.
- **S25.** Removing the joined store means removing its rows too.
- **S26.** The -999 flag on wbal_roll* is a false alarm: the values are real (at Thar 2009, -999 occurs as often as
  -998 and -1000). luh2_forest has values above 1: 13,104 rows in the PM2.5, fire and NDVI smoke groups and 14,196
  in defo's (under 0.1%; banned on defo). co2 is unsigned but banned everywhere.

## Appendix C. The 20 open notes the freeze reads in ban.yaml (F-BAN-OPEN)

| Package, line | Note | Settled by |
|---|---|---|
| PM2.5 9, 21, 23 | phenology decision; index windows awaiting signature; three 'watch' choices | S14 |
| PM2.5 44, fire 69, NDVI 58, defo 54 | the reason word on the raw aglw_* | S13 |
| NDVI 357, 368 | snow_cover_fraction in polar night | S15 |
| defo 49, 1351-1359, 1653-1673 | the K3/K5 store columns; deeprec_twsa's reason word | S16 (with S8) |
| defo 57 | the L1 signatures are not written on defo | S18 |

## Appendix D. What changed since the reports and the first version of this sheet

- Ruling M2 is wired: `check --deep` runs on the R21 smoke groups, its report names them (checked_groups), and the
  freeze checks them (F-CHECK-CONTRACT, F-CHECK-GROUPS). Deep reports made earlier by a scratch script name no groups
  and no longer count. Re-run the deep checks with the command after the last engine change.
- defo's K store build is finished: 924 files and 924 build records, every record carrying the committed K catalog's
  hash (1f711e57...), last write 13:58. Its 33 index aggregates no longer refuse.
- New: S28 and S29. S8 is now "yes after refresh". The S6 texts no longer claim that a 'yes' protects a column.
- G-JOIN is a flag now, not a refusal, on fire and defo. defo's "102 columns without facts" are 2 (month,
  grace_lwe); J4's "declared through" covers the other 100. PM2.5's expected Y0 is already 2003.
- The deep G-EPOCH checks every lead's fit and guard cut, not only the train end. That is why travel_time (S27)
  refuses now and passed at 11:04.

## Appendix E. Tests the written answers break (measured on the scratch copy)

Targeted run, 17 test files, on the scratch copy before and after the recommended answers (S9 open). Before: 1
failure and 5 errors, all already there. After: 91 more failures. 31 of them compare the drafts with the package and
pass again once refresh_drafts.py rewrites the drafts (checked). The other 60 need an edit:

| Test file | Fail | Who | What they check today |
|---|---|---|---|
| test_constants.py | 4 | engine | k unset; constants still 'proposed' or 'extra' |
| test_packages_declarative.py | 8 | engine | owner fields marked unsigned; the review-sheet cover |
| test_catalog_timing_facts.py | 3 | engine | defo's yearly facts equal the generator's |
| test_packages_pm25_bans.py | 6 | pm25 | unsigned facts and disclosures; verdict counts |
| test_fire_package_bans.py | 5 | fire | unsigned facts and disclosures; verdict counts |
| test_ndvi_package_ban.py | 9 | ndvi | only L1 signatures; verdict counts |
| test_ndvi_package.py | 2 | ndvi | facts inherited from the unsigned source |
| test_defo_k_ruling.py | 8 | defo | the K catalog equals what its builder writes |
| test_defo_k_l3_l4.py | 3 | defo | nothing marked signed (S18 a); hold facts unsigned |
| test_route_region_defo_package.py | 12 | defo | the features catalog equals what its builder writes |

The defo tests mostly need the two generators to keep the signatures (code, about 2-3 hours). The rest are pins to
rewrite (about 1 hour per package). The 1 failure before (test_packages_pm25_bans.py, India ratios) is not ours.
Logs: D:/treeroute/signoff_20261006/tests_before10.log, tests_after10.log, tests_after10_drafts.log.
