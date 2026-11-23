# Sign-off review: are the S1-S29 recommendations right, and can they go in the paper?

2026-10-06. This merges five independent reviews: three lenses (leak, paper, feasibility) and two deep dives (static
maps; reach and co-measured columns). Where the reviewers disagreed, the evidence decided, not a vote. Read-only: this
is the only file written. Scratch: D:/treeroute/recreview_20261006/.

## Short answer

- **Mostly yes.** 22 of 29 items stay as recommended; 5 of those need only a number or a note fixed.
- **Five need a change** (S1, S3, S6, S8, S29). **One needs its follow-up fixed** (S21). **Two are your choice** (S15,
  plus defo population_density inside S6).
- **Two new owner items** that are not on the sheet: pdo's window (N1) and a dating rule for static maps (N2).
- **No change needs new tool code.** S1 and S3 go through `options` blocks in the answers file; the tool already applies
  those to any item.
- **Time:** about 2 working days, not 1.5. The machine hours stay the same, except defo runs about 5-8% longer (S17).

## ATTENTION: items that change

**S1: CHANGE -> yes for 50 columns, but ban defo's scpdsi_mean/_min/_max (reason lookahead_unfixable).**
Why: CRU computes scPDSI with the method of Wells et al. (2004), and that method backtracks: later months
rewrite earlier values. So a month's value can hold data from later months. defo reads the same-year value at lag 0,
so it can see past the year it predicts. PM2.5, fire and NDVI already ban scpdsi.

**S3: CHANGE -> yes for 15 columns. You re-rule K4: ban defo's 4 MODIS land-cover columns (reason lookahead_unfixable).**
Why: the provider smooths MCD12Q1 labels across years with a hidden Markov model. Last year's label can then carry this
year's clearing, and no lag removes that. The provider also says not to use the product to measure change. defo's own
catalog has an unanswered "OWNER CHECK" on exactly this point.
The other choices: lag 2 (partial fix, 2-3 h), or keep lag 1 with a disclosure (signs a window known to be false).

**S6: CHANGE -> recommended answers, with the 4 vegetation reason texts corrected.**
Why: the texts say "January composite, up to 15 days". In fact the overlap comes from the late-December composite: at
most 3 days for NDVI/EVI and 8 days for albedo/GPP.
**Your choice inside S6: defo population_density.** yes (lag 1) matches J3's reasoning for AGLW and costs almost
nothing; no rests on your Part 437 measurement. I lean yes.

**S8: CHANGE -> sign the 28 entries that are already true now. Sign the 17 refreshed ones only after you read them
in the dry-run printout.**
Why: "yes after refresh" signs text you have not seen yet. The refresh must also add the new S1/S3/S6 disclosures.

**S29: CHANGE (text only) -> a (ban on all four), with corrected evidence.**
Why: GRIP4 is about 60 road sources of mixed date, not "one 2018 map". 2018 is the release year, so record it as an
upper bound. The ban still holds. Also, the sheet swaps fire's lead-6 and lead-12 fit cuts.

**S21: KEEP accept, but fix the follow-up.**
Why: as worded, every headline run would still be marked "not headline", because the pre-Y0 label departure is added on
all four packages. Your "unsure" can go: brute-force tests of the weighted GLS solve already exist.

**S15: OWNER CHOICE -> watch (my lean) or ban.**
Either way there is no leak. watch keeps a real snow driver in 128 groups, but feeds "no snow" in 5 Arctic groups. ban
removes those wrong values and loses the driver everywhere; other snow columns stay. The sheet's line "read J2 d
literally and the answer is ban" is wrong: J2 d keeps this column by name.

**N1 (new): pdo -> re-sign it with the ERSSTv5 reach, giving lag 2 on PM2.5, fire and NDVI.**
Why: PSL's pdo.data now points to an ERSSTv5-based PDO, so ruling R-A (a) applies, as it does to nino34. L1 b's window
gives lag 1, while the four ban texts already claim lag 2 or "the ERSSTv5 reach". Fallback: keep lag 1 and rewrite
those texts. defo stays at 1 year either way.

**N2 (new): add one line to Appendix A (S22): physical maps (terrain, coast, hydrography, soil) are timeless; maps of
human-built features are dated and checked at every cut.**
Why: dated the way S29 dates GRIP4, SoilGrids and MERIT Hydro would also fall after the guard cuts. Without a written
rule, the travel_time and road bans look selective.

**Keep, but fix a number or a note:**
- S17: defo's bank becomes 4,615 and scored 2,197 per group, 92,274 in all. That is x1.31 against the old split, not
  the disclosed x1.22. Update APP_PLAN, the L1 disclosure and the pre-registration.
- S27: freeze is not possible here, rather than "unsure". R9 refuses when the only date is after the cut, and the
  pipeline refuses every freeze verdict.
- S28: budget 2-3 h, not 1-2. It needs a new facts helper, because the J2 a helper refuses this parent.
- S9: build the store after the RAM probe ends and before the first apply. The tool refuses the whole apply until the
  files exist.
- S12: test_pipeline.py and test_c9_guard_tolerance.py also break; they are not among the 60.

## All items, one line each

| ID | Verdict | Plain reason |
|---|---|---|
| S1 | CHANGE | yes for 50; ban defo scpdsi_* (backtracking can carry later months) |
| S2 | KEEP | ERSSTv5 lags 2/3 follow CPC; see N1 for pdo |
| S3 | CHANGE | yes for 15; ban defo's 4 MODIS land-cover columns (labels smoothed across years); you re-rule K4 |
| S4 | KEEP | yearly human columns lag a year; static maps predate the cuts; add N2 |
| S5 | KEEP | children copy their parents; safe only together with the S1 and S3 bans |
| S6 | CHANGE | right answers, wrong texts (December, 3 and 8 days); population_density is your choice |
| S7 | KEEP | physical bound; before the paper, confirm which ACAG release "V5GL06" is |
| S8 | CHANGE | read the 17 refreshed texts before signing them |
| S9 | KEEP a | labels t-2 and older only; build after the probe, before the first apply |
| S10 | KEEP | removes unread rows; adds 2 banned rows |
| S11 | KEEP | empty row |
| S12 | KEEP a | set by measurement on training rows; 2 more test files break |
| S13 | KEEP incomplete | true, and the only word that runs |
| S14 | KEEP | notes record rulings already made |
| S15 | OWNER CHOICE | watch (lean) or ban; no leak either way |
| S16 | KEEP | lookahead_unfixable is true; target_derived would be false |
| S17 | KEEP a | forced by K5; fix the unit numbers (x1.31) |
| S18 | KEEP a | L1 covers every package |
| S19 | KEEP a | counts the rows the run reads |
| S20 | KEEP b | describe them in the paper as owner-fixed constants, not literature values |
| S21 | KEEP accept | fix the follow-up (pre-Y0 departure); GLS solve already brute-force tested |
| S22 | KEEP | Appendix A also gets N2 and the S1/S3/S6 flags |
| S23 | KEEP | the record end is not a content date; do it with the S21 engine edit |
| S24 | KEEP out | exact duplicate |
| S25 | KEEP | the store holds only banned columns |
| S26 | KEEP | false or harmless flags |
| S27 | KEEP ban | rule-based; freeze is impossible, not "unsure" |
| S28 | KEEP a | real leak; b is just as leak-free if time is short |
| S29 | CHANGE (text) | a, with the GRIP4 evidence corrected; swap the fit cuts back |
| N1 | NEW | pdo: give it the ERSSTv5 reach (lag 2) |
| N2 | NEW | one dating rule for static maps |

## Paper disclosures the answers require

1. Leads count in content time, on final data versions. Real-time release delays are not simulated.
2. Whole-record dependencies are disclosed, not lagged: SPI/SPEI fits, index base periods (ONI's rolling 30-year bases), AMO detrended over its whole record, ERSSTv5's own filters.
3. ERSSTv5 filter reach: nino and sst_anom enter at lag 2, oni and tni at lag 3 (pdo at lag 2 if N1 is taken).
4. DeepRec: input window undocumented, so lag 3 is your bound; it was trained on GRACE months that include 2020-23.
5. DeepRec on defo carries a LUH2-based input, while LUH2 itself is banned on defo; accepted at a 1-year lag.
6. defo: MOD44B and phenology enter at lag 2 because their product windows run into the next year; Y0 is 2004.
7. defo's scored units: 92,274 (x1.31 of the old split).
8. Materiality: defo's lag-1 vegetation aggregates overlap the predicted year by up to 3 days (NDVI/EVI) or 8 days (albedo/GPP), under 1% of the year; MOD44B's 2-month overlap was not accepted.
9. PM2.5's lag-1 burn_frac can use imagery from the predicted month (MCD64A1 detection; J1, L1).
10. Fire history reads labels at least 2 months old (rings 3), past labels only, possibly from neighbouring regions.
11. Hansen labels some late-year clearing in the next year; lag-1 optical columns see it (past data, not look-ahead).
12. FireCCI switches sensor (MODIS to OLCI) at 2019/2020, exactly defo's train/test boundary. Night lights switch at 2013/2014.
13. Holds and extrapolations: HDI held at 2015, fertiliser at 2013, livestock at 2021; WorldPop 2021-23 extrapolated.
14. A static-map table: product, version, content year or "physical, timeless", input years, and verdict per problem.
15. In that table: the DEM source, the SoilGrids version (2001-2015 covariates include MODIS NDVI/EVI, so add it to NDVI's disclosures), MERIT's Hansen-2000 link, GMIA v5 (about 2005).
16. travel_time is excluded on fire only (a 2015 map after fire's 2015 guard cuts): a rule, not a found leak.
17. road_density (GRIP4) is excluded everywhere (sources up to about 2017). The shipped defo and fire runs used it.
18. NDVI snow: under watch, polar-night gaps are filled as "no snow" in 5 Arctic groups (4-13% of their rows); under ban, one line saying it is excluded.
19. Last-value fill counts cover the rows each run reads.
20. The 17 engine constants were fixed by the owner before the run.
21. Build departures: weighted GLS, private router kernels, the pre-Y0 label reading. The verdict band comes from the same run it judges.
22. The pre-registration was written after earlier shipped runs on the same test years.
23. PM2.5 target: cite the exact ACAG release behind the "V5GL06" file names. Whether ACAG's GWR pools monitors across months is unknown.
24. Index values are a 2026 snapshot (hashed), not the real-time values.
25. luh2_forest has under 0.1% of values above 1 (measured on the smoke groups only).

## Open checks (none blocks the freeze; settle them before writing the paper)

- AGLW's land-cover mask (FROM-GLC Plus): if its yearly maps use later years, defo's aglw hold at lag 1 has the S3 weakness.
- travel_time: whether Weiss et al. took its road inputs in 2016. The provider's stated year 2015 is the defence.
- Who extrapolated WorldPop 2021-23, and from what.
- The SoilGrids version: the repo says 2.0 in one place and 250m in another.
- FireCCI may confirm a month's burns with next-month images (a few weeks at most on defo's lag-1-year columns).

---

## Evidence

### S1: scPDSI backtracking (only the leak lens raised it; the other reviews did not check it)
- Panel catalog `scpdsi`: window {1, month, backward}, no reach, `product_family: CRU scPDSI`, from
  `presplit_cc/ingest_drought_indices.py` ("CRU TS 4.09").
- CRU readme for the 2024 release (crudata.uea.ac.uk/cru/data/drought/scpdsi.global2024.readme.txt, read
  2026-10-06): it names Wells, Goddard and Hayes (2004) as the source of "detailed information about its calculation"
  and says nothing about removing backtracking.
- Wells et al. (2004), read by the leak lens: section 2 defines backtracking, where values already calculated are
  replaced; section 4 leaves out "the last two years" because of it.
- The file names show whole-record calibration (`cal_1901_..`), a base-period-like dependency.
- defo/ban.yaml:1532-1543: scpdsi_mean/_min/_max are `keep` only as a "family expansion" of the shipped keep. No owner
  ruling keeps them. pm25:694, fire:1008 and ndvi:1063 ban scpdsi (trend_proxy).
- Feasibility: the answers file can carry `S1: options: yes: verdicts: defo: {scpdsi_mean: {verdict: ban, reason:
  lookahead_unfixable}, ...}`. apply_signoff.py `plan_options` applies verdicts for any item, and `entering_after`
  then leaves the three columns out of signing. A 12-month reach cannot be written by the tool: STORE_FACT_KEYS holds
  only content_epoch. Put the provider citation in your ruling entry, because the tool writes its own evidence string.

### S3: MCD12Q1 HMM (leak, paper and feasibility lenses all agree; they differed on how to apply it)
- MCD12 User Guide V6.1 (D:/treeroute/recreview_20261006/mcd12_ug_v61.txt, lines 75-95): smoothing splines on the NBAR
  time series; "an approach based on Hidden Markov Models that post-process map results for each year" (Abercrombie and
  Friedl 2016); "we urge users not to use the product to determine post-classification land cover change".
- OWNER_RULINGS_2026-10-05.md K4 rests on "last year's land cover is past information".
- defo/catalog.yaml K4 rows: "OWNER CHECK before the headline, not verified here: if the MCD12Q1 time-series
  post-processing (the C6 HMM label stabilisation) uses LATER years ..."
- No other defo column is derived from the four, so a ban leaves no orphans. PM2.5 holds them conditional; fire and
  NDVI ban them.
- The disagreement on mechanics, settled by the code: dropping MCD12Q1/MCD12C1 from `families` leaves kept columns
  unsigned (`plan_signing` -> skipped, so G-FACTS keeps refusing defo). A `verdicts` block under `S3: options: yes`
  bans them, and then nothing needs signing. Test pins in test_defo_k_ruling.py change.

### S6
- signoff_answers_TEMPLATE.yaml:114-117 says "(its January composite)".
- monthly_panel_v170_schema_catalog.yaml:981 and :3463, and INDEX_WINDOW_AUDIT.md:113: "December reaches 2-3 days into
  January (the day-353 composite)". V14 and gpp use a 47-day centred window, about 8 days of reach.
- population_density: J3 calls AGLW co-measured on defo for the same mechanism (same-year land cover in the
  downscaling). defo/ban.yaml:179 keeps it by your Part 437 measurement. The paper lens and the reach deep dive favour
  yes; the feasibility lens calls no defensible. Either answer is leak-safe; yes is consistent and costs about nothing
  (no Y0 move, a few defo pins).

### S8
- apply_signoff.py `plan_exceptions` signs every unsigned entry at apply time, with the text the refresh wrote. The
  stale check only catches open-decision words, or "kept/watch" next to a `ban`. Example: PM2.5's burn_lag1
  test-exposure entry becomes moot under S24 (conditional) and is not flagged.
- The count: the template comment says 16, the sheet 17 (PM2.5 7, NDVI 8, fire 1, defo 1).

### S29
- Meijer et al. 2018, ERL 13:064006 (read by two reviewers): over 50% of road length from sources published in 2010 or
  later, 23% 2006-2010, 14% 2000-2005, 8% VMAP0. Received June 2017, published May 2018.
- The sheet's Appendix B gives the fire fit cuts as "(2018-01, 2018-07)" for lead 6 and lead 12. timing/cuts.py (cut =
  end - (L-1)) gives lead 6 = 2018-07 and lead 12 = 2018-01.
- Corrected evidence text for `S29: options: a: store_facts`: "GRIP4 (Meijer et al. 2018, ERL 13 064006) merges about
  60 national and OSM sources; over half the road length comes from sources published 2010 or later; latest source
  dates not recorded; 2018 (release) is recorded as an upper bound; after every guard cut, before every test year."

### S21
- tests/test_route_weighted.py:98 `test_weighted_solves_match_brute_force_weighted_least_squares` and :268
  `test_the_weighted_router_matches_brute_force_per_unit`. Both check against sqrt-weight rows plus numpy lstsq, the
  test the paper lens asked for.
- pipeline/run.py:211-220 `build_departures` appends MODEL_LABELS_DEPARTURE whenever `model_labels_withheld`, which is
  set at :776/:846 when target rows exist before Y0: true on all four packages. split_view fires only when groups are
  excluded (the probes), so headline runs are unaffected by it.
- FOLLOW_UPS ("S21", "accept") names only the DEPARTURES tuple.

### S15 (the paper lens says ban; the leak and feasibility lenses and the reach deep dive say watch)
- OWNER_RULINGS_2026-10-05.md J2 d fixes "NDVI snow_cover_fraction's empty October 2022 (also lag 1 as same-sensor
  co-measured)". It names the long seasonal masks that stay banned: "eddi, eddi_observed, aridity_index".
- ndvi/ban.yaml snow_cover_fraction: 4.4-13.4% of the labelled rows in 5 groups. It is not in LAG_BASES, so a ban
  leaves no orphans. R30 zero-fills with no missing-value indicator (APP_PLAN.md R30).

### N1: pdo
- Panel catalog pdo: {3, month, centred}, signed under L1 b; expected_derived.json has pdo lag 1 on pm25, fire and ndvi.
- psl.noaa.gov/data/correlation/pdo.data footer (read 2026-10-06) links oceanview.pfeg.noaa.gov ERDDAP
  `cciea_OC_PDO`, whose summary reads "the projections of the ERSST V5 monthly SSTA onto the 1st EOF pattern of North
  Pacific 20N-60N". This settles the disagreement between the leak lens ("names no SST dataset") and the deep dive. The
  footer does not name the dataset itself; the page it points to does.
- pm25/ban.yaml:412 says "R8 lag 2", fire:605 "carries R-A (a)'s 2-month reach", ndvi:636 "with the ERSSTv5 reach", and
  defo pdo_* "the ruled ERSSTv5 reach". None of these matches the signed fact.
- Cost of lag 2: a hand edit of the store catalog (the tool cannot write a reach), pdo 1 -> 2 in three
  expected_derived.json files, and test pins. No Y0 change.

### N2: static maps
- Panel catalog: only travel_time carries a content_epoch. Soil reads "SoilGrids-type", the DEM "not recorded".
  defo/ban.yaml soil rows: 2001-2015 covariates. MERIT Hydro was released in 2019 with water masks to about 2015.
- Dated by release (the S29 method), SoilGrids and MERIT would fall after every guard cut. Dated by their newest input
  (about 2015), they would fall after fire's lead-6 and lead-12 guard cuts. Neither is a real leak (static physical
  properties). The defo ablation was null (Part 508). Do not record release dates on them.

### S17
- tests/test_derive_acceptance.py PENDING_OWNER_DERIVED and FOLLOW_UPS ("S17","a"): bank 4,615, scored 2,197, test-pass
  3,750. 2,197 x 42 = 92,274 against 70,487 (x1.31). APP_PLAN.md:701 still says 85,680 (x1.22).

### S27, S28
- treeroute/timing/freeze.py:10-27 refuses when no epoch lies at or before the cut. pipeline/data.py:676-678 refuses
  every 'freeze' verdict.
- defo/features/build.py:136-141 `_lag_facts` refuses a parent that is not a {1 year, backward} period_end aggregate,
  or that carries a reach. Phenology is period_centre with a reach.
- MCD12Q2 User Guide V6.1 (D:/treeroute/recreview_20261006/mcd12q2_ug_v61.txt:21, :55-56): fitted on "three
  consecutive years: the product year and preceding and subsequent years". C6.1 is generated 6 months after the year
  end.

### Where the reviewers disagreed, and what decided it
- S1: one lens raised it and four did not check it. The CRU readme cites Wells 2004, and Wells' method backtracks:
  CHANGE.
- S3: the three lenses agree on the change. The feasibility lens is right that dropping families is not enough; a
  verdict block is needed.
- S5: the leak lens said CHANGE. It is not needed once the S1 ban is in the answers file: the banned children are then
  never signed.
- S6 population_density: two lenses said yes, one said no. Both are defensible, so it is your choice (I lean yes).
- S8: the leak lens said read first; the others said the refresh suffices. The tool signs text at apply time, so you
  should read it first.
- S15: one lens said ban, three said watch. J2 d keeps the column by name, and there is no leak: your choice (I lean
  watch).
- S21: the paper lens was unsure. The brute-force tests it asked for already exist: accept.
- S28: a and b are both leak-free. Keep a; b is the fallback.
- pdo: the footer links the ERSSTv5 series, so the deep dive is right.
