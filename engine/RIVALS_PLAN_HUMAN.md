# Human rivals (type 2): the plan, the time, and the total for all rival results

Written 2026-10-21. Revised 2026-10-21 after three reviews (legitimacy, feasibility, completeness; REVIEW LOG at the end).
Status: PLAN ONLY. Nothing was downloaded, installed, built or scored.
Scratch notes behind this plan (read them for detail): D:\treeroute\rivals_plan_human\ protocol.md,
research_pm25.md, research_ndvi.md, research_fire.md, research_defo.md, research_coral.md.
All hours are estimates (x), not measured, unless marked "measured".

## 1. SUMMARY

- A human rival is the method people really use for the problem: an operational product, a physical index,
  or a published standard method. It runs on the SAME test rows, leads, cuts, metrics and paired contrasts as
  the common board. It may only use data that existed at the issue date.
- One primary rival per problem and lead. Where no human method reaches a lead, we say so plainly. The normal,
  last-5-years normal and persistence rows then stand in.
- The primary rivals:
  - PM2.5 nowcast: **no human PM2.5 nowcast that respects information parity is stronger than persistence.**
    Lagged CAMS EAC4 (month t-1) is reported because ruling D4 a names it. Real practice (same-month EAC4) is
    printed as the tier-A row right beside it. None at 6 and 12 months.
  - NDVI nowcast: per-unit Bayesian ARDL (BARDL / AstroCast), the closest published method piloted in operations.
    No operational global NDVI forecast exists. **No published NDVI forecast reaches 6 or 12 months**; H1 there is
    a labelled statistical extension.
  - Fire: two separate rivals. CEMS ERA5 Fire Weather Index (nowcast) and CEMS SEAS5 seasonal FWI (6 months).
    None at 12 months.
  - Defo: Verra VT0007 risk-map allocation (the REDD+ benchmark), both leads, as shipped AND calibrated.
  - Coral: NOAA Coral Reef Watch DHW / alert level (nowcast); the same rule fed old heat ("lagged") at 183 and
    365 days, plus the CRW 4-Month Outlook as an advantaged row (C11 c; Q12 asks to amend).
- Downloads: about **3-10 GB** in total, mostly fire (upper bound if the merged boxes are kept). Coral and NDVI need
  none. Defo needs GADM 3.6 level 2 (~0.5-1.5 GB) unless divisions = one per region.
- Human rivals cost about **18-38 h of machine time** plus about **10-50 h of network waiting** (fire; worst ~100 h
  if the queue runs one job at a time). The waiting overlaps other work.
- **All rival results:** common board 26-50 h (+ up to ~29 h if boosting hits the 800 edge; both figures priced
  before rulings Z2 and AA2-AA4) plus human 18-38 h = **about 44-88 h of machine time, worst ~117 h**.
  That is about **5-9 overnight sessions, worst ~12**. Night 1 no earlier than ~23-24 Oct. **Typical finish
  ~3-12 Nov**, about 2 weeks before the ~25 Nov submission.
- **Phase 2 dropped (AA1).** The donor-only board is not run; disclosed as a departure from ruling D.

**ATTENTION**
1. **Nowcasts read the target month's weather.** In the fire and PM2.5 runs many weather columns have
   `nowcast_steps 0` in derived.json R8 (fire: 74 entries; pm25: 50). So "nowcast issue = previous month" is true
   for LABELS only. Labels end at t-1 (pm25, defo) or t-2 (ndvi, fire; R17 offset 1). A rival may use target-month
   weather, but never a target-month observation of the target. The T1 boundary is read per rival from R8 (§3.3).
   Owner confirms (Q3).
2. **No nowcast has a persistence row today.** Lead-0 test_preds of pm25, ndvi, fire and defo hold only
   guess_normal, last5_normal and predict_zero (checked). Add persistence and damped persistence (Q4), and a
   coral last-visit row (Q23). Minutes of work.
3. **Copy before delete.** The human tool needs keys, roles, train y and normals from each common export.
   A `slim` copy must run BEFORE the owner deletes that export. A re-export costs hours (pm25 derive ~4.4 h).
4. **Gates before any common night.** Z2 build, then the AA build, then the common rival Part re-signed (AA5, Z4).
   harness.py was still changing at 04:52 today. The human tool pins the harness hash only after that signature.
5. **Two human Parts (Q22).** Part A (coral, defo, PM2.5, NDVI) signed when their manifests are hashed; Part B
   (fire) signed when D2/D3 are hashed. No human test score before its Part (H16).
6. **Calibration strength (Q19).** Pooled maps only would be a straw man for FWI and CTM output. The plan adds
   per-unit MOS (F5) and, for fire, the per-unit FWI percentile read against the normal (F6, research C-A).

## 2. THE HUMAN RIVAL PER PROBLEM AND LEAD

Kinds: I = index (needs a calibration map), N = product already in target units, M = published method.
Tiers: P = parity (decides), L = lagged on purpose (decides, labelled; only where an owner ruling asks: C11),
A = input-advantaged (printed, never decides, unless the owner rules otherwise in Q12).

| Problem | Lead | Rival rows (kind, tier) | Optional rival | Data on disk / download | Calibration (train rows only) | Leak notes |
|---|---|---|---|---|---|---|
| PM2.5 | 0 | **The human baseline to beat is (damped) persistence (Q4).** P row: CAMS EAC4 monthly PM2.5 at t-1, "the operational product at parity" (N, P). **Printed directly beside it:** same-month EAC4 (N, A), "real practice", the reviewer-facing comparison | MERRA-2 PM2.5 at t-1 (N, P); same-month MERRA-2 (A) beside it | MERRA-2 on disk (D:/pm25_products/merra2, 252 files 2003-01..2023-12, 0.84 GB). EAC4 NOT on disk: ~0.12 GB as netCDF, CC-BY, ADS key file + CAMS licence click | F0-F5 picked on inner MAE; F1-F4 pooled, F5 per-unit MOS (Q19) | EAC4 assimilates target-month MODIS AOD, so the P row is lagged. EAC4 at t-1 knows less than y(t-1), so it is weak by construction (research_pm25.md §0). EAC4 is published 4-6 months late: t-1 is generous (disclose). 5 MERRA-2 test months are the reprocessed stream (disclose) |
| PM2.5 | 6, 12 | **No human rival.** No operational 6-12 month PM2.5 forecast exists | none | - | - | CAMS forecasts reach 5 days; C3S seasonal has no aerosols. GEOS-S2S-2 (prognostic aerosols) could reach lead 6; public PM2.5 output and a hindcast archive are unverified; research system (Q21) |
| NDVI | 0 | H1: per-unit Bayesian ARDL on the NDVI anomaly (BARDL / AstroCast; M, P). Past NDVI to t-2, precipitation and soil moisture at issue and 2 months before | Kraft 2019 global LSTM, re-run on the headline rows (M, P) | All inputs on disk (D:/monthly_panel, 2,926 files, 40.9 GiB). torch 2.8.0 installed | None: fitted in NDVI units (F0) | Engine reads NDVI to issue minus 1, so a rival may too. MOD13C2 15-day reach: use exactly the engine's offset. H1 reads NDVI labels only through the slim copy (§3.6) |
| NDVI | 6 | **No published NDVI forecast reaches 6 months.** H1-direct is reported as a labelled statistical extension (Q8) | H1 + SEAS5 month-6 climate (CDS download; recommend skip, Q10) | On disk. SEAS5: ~3.3 GB GRIB, CC-BY, CDS licence click, NetCDF (cfgrib not installed) | F0 | BARDL is published for 6-10 weeks only, piloted in 7 Kenyan counties (Salakpi 2022). SEAS5 run of 1st of t-5 holds data to the issue month |
| NDVI | 12 | **No published NDVI forecast reaches 12 months.** H1-direct is reported as a labelled statistical extension (Q8) | none | - | F0 | - |
| Fire | 0 | Rival F-ERA5: CEMS GEFF-ERA5 FWI of the target month (I, P). Picked on its own at lead 0 | none | NOT on disk (one yakutia file only). ~0.4-2.2 GB, CC-BY, EWDS licence already accepted (confirm) | F0-F6 on bank units to the lead's cut: F1-F4 pooled (one map), F5 per-unit MOS, F6 per-unit FWI percentile `x__fwi_pct` x per-group isotonic ratio on the normal (research C-A). Inner MAE picks (Q19) | Parity because our nowcast reads target-month ERA5 weather (ATTENTION 1; T1 boundary from R8). ERA5 does not assimilate burned area |
| Fire | 6 | Rival F-SEAS5: CEMS GEFF-SEAS5 FWI, start 1st of month M-5, daily leads 150-184, mean of members 0-24 (I, P). **A separate rival:** picked on lead-6 guard rows; no pick carries over from F-ERA5 | ENSO-lag regression (Chen et al. 2011, 2016), ONI in the panel (M, P); Turco 2018 SPI-lag model (M, P) if Q20 says yes | NOT on disk. 240 starts x 35 days x 25 members, ~1.5-6.3 GB, CC-BY, EWDS | Same F0-F6 family | Re-forecasts for starts to 2016-12; real-time from 2017-01 (part of train, all of test) (HQ11). Members 0-24 in every year keep ensemble size equal. Re-forecasts start from a different analysis (disclose) |
| Fire | 12 | **No human rival.** GEFF-SEAS5 stops at 216 days | ENSO-lag regression, labelled; Turco SPI-lag if Q20 says yes | - | - | - |
| Defo | 0, 1 yr | Verra VT0007 "UDef-A" benchmark: 30 distance-to-forest-edge risk classes x admin divisions, past loss frequency, region's 10-year mean rate spread over them (M, P). **Two P rows:** as shipped (F0) and isotonic-calibrated. Both leads get identical numbers (labels end at t-1 at both) | The same method frozen at 2019 (what Verra certified for Peru and Colombia, 2020-2025) | Hansen GFC-2025-v1.13 on disk (D:/hansen, 231 files, 32.05 GB, same version as our target; missing tile 20S_040W is all ocean). GADM 3.6 level 2 NOT on disk, ~0.5-1.5 GB, free for academic use | Both forms pre-registered (Q14). "Ours beats VT0007" only if ours beats both; otherwise each form's verdict is printed | Lossyear read only for 2001..t-1; the runner asserts pixel lossyear <= the T2 year. Gain layer banned. Admin boundaries dated before 2019. Distances need pixels outside each region |
| Coral | 0 | NOAA CRW 5 km v3.1 DHW and 7-day-max alert level, **read at d* = T - 2, the same last SST day as our features** (SPEC_CORAL_TABLES.md:165-171) (I, P) | none | All on disk: D:/coral/drivers/sst_compact_all.npz (932 MB, 1985-01-01..2020-12-31), official climatology ct5km_climatology_v3.1.nc (81.5 MB). D6 check REQUIRED before Part A | F0-F5 family, NOAA's own MMM, 5-level alert scale of 2016-19 | Never use a "season max DHW": it reads past the survey date. Recomputed from our SST file, so D6 must show it equals NOAA's grid. The rival is a subset of our inputs: it measures what the model adds over NOAA's rule |
| Coral | 183 d, 365 d | **No forecast with a public 2016-19 archive covering our sites reaches 183 d or 365 d.** BoM ACCESS-S (Australia only, about 6 months) has no archive we found (verify before Part A). Row C11: CRW heat stress **read at T - L - 2**, "NOAA's nowcast rule fed old heat" (I, L) | CRW 4-Month Outlook v5 at its 140-day maximum (I, A by default; C11 c asks "head to head": Q12) | Outlook archive on disk: D:/coral/crw/nc, 1,984 files, issue weeks 2011-07-03..2020-12-27 | F0-F5 family | The Outlook is issued 42-49 days (183 d) or ~225 days (365 d) after our issue date, so it cannot be head to head under parity. Experimental product; files are a 2019 v5 reissue (disclose). At 365 d only 38 guard rows in 11 groups (no safety net possible) |

Reference rows on every problem and lead: guess-normal, last-5-years normal, predict-zero, persistence and damped
persistence (Q4), and at coral a last-visit-at-the-site row read at the T2 step (Q23).

Rejected, with reasons in the scratch notes: GEOS-S2S-2 and regional haze models (PM2.5); NMME, McPhillips GP,
SARIMA, VHI/ASIS/FEWS NET (NDVI); FIRMS, GFAS, GFED, EFFIS, NIFC/AFAC outlooks (fire); GLAD/RADD, PRODES/DETER,
Terra-i, Verra's published maps, ForestCast, forestatrisk (defo); NMME degree heating months, Allen Coral Atlas,
ReefTemp (coral). BoM ACCESS-S is not rejected: no archive found yet. Products that observe the target month are
always rejected.

**Old results are history only.** EAC4/MERRA-2 (old PM2.5 plan), Kraft and BARDL (NDVI Parts 417-426),
CEMS (Parts 496-498), udef_a (defo_papers.py) and CRW (Parts 456-457) used old splits, old leads, test-year
calibration rows or the old model. None is paired with the new runs. These rivals are not blind; §8 R10 lists each
choice an old score influenced.

## 3. THE UNIFORM PROTOCOL

Full text: D:\treeroute\rivals_plan_human\protocol.md (rules H0-H19). Changes this revision makes to it are listed
in §3.15; they are applied to protocol.md at build time (this revision edits only this file).

1. **Same run.** The human board refuses unless the run fingerprint, test_preds sha256 per lead and band match
   the common board's.
2. **Same rows.** It predicts the saved test rows of each lead, joined on (unit, time, lead). Same train roles,
   cuts, normals and fit-cut c as the common export (read from a `slim` copy).
3. **Information parity, two timing rules read from the run.** T1: driver inputs (weather, SST, FWI) end no
   later than the boundary of that driver kind, read per rival from derived.json R8 as the max `nowcast_steps`
   of the run's driver columns of the same kind, and recorded in the lock. T2: anything that observes the target
   ends no later than `timing.latest_label_step(t, L)` minus the run's R17 offset (treeroute/timing/cuts.py:50-60).
   Offsets: pm25 0, ndvi 1, fire 1, defo 0, coral 0. Each row stores `info_end` and `target_obs_end`; a P row
   that breaks a rule refuses. Toy test: a target-month FWI passes on a fire run and refuses on a run whose R8
   says 1.
4. **Tiers.** P and L rows decide. A rows are printed as "what that extra input is worth" and never decide
   (unless Q12 c). L rows exist only where an owner ruling asks for them (today: C11 at coral). A BEATS verdict
   against the coral L row is worded "beats NOAA's nowcast rule fed old heat", never "beats NOAA".
5. **Calibration of an index (I and N kinds).** A fixed family: F0 native; F1 linear on the link; F2 isotonic raw;
   F3 linear on the index anomaly; F4 isotonic on the anomaly (F1-F4 pooled: one map per lead over all bank units);
   F5 per-unit MOS: per-unit linear map on the anomaly, slopes shrunk toward the pooled slope (Q19); fire only:
   F6 = normal x per-group isotonic ratio of the per-unit FWI percentile `x__fwi_pct` (train years, same calendar
   month). Crossed with the run's links and at most 3 statistics. Fitted per lead on train rows only. Isotonic
   direction from the train Spearman sign. Maps use squared error, as the engine fits the mean; on the zero-heavy
   targets (fire, coral, defo) an L1 (median) isotonic map is printed beside and never decides (Q13), so a
   "timid" MAE loss is visible.
6. **Methods (M kind)** fit only up to each cut. At the issue date they may read labels up to the T2 step,
   never refit on them. They read labels only through the slim copy, and every row records `target_obs_end`.
   A shifted-label test must refuse (R8). M-kind runners are the one place problem knowledge lives; they stay
   outside the generic tool. Output as shipped (F0), except defo, where both forms are P rows (Q14).
7. **Pick, pin, lock.** Lowest inner MAE picks one candidate at the nowcast, pinned at every lead, refit per lead.
   A forecast-only product is a separate rival picked on its lowest covered lead (fire: F-SEAS5 on lead-6 guard
   rows; no pick carries over from F-ERA5). Picks and coverage masks are locked before any test label is read.
   Nothing is added after a test score.
8. **Safety net applied**, as on the common board: raw and guarded are both scored; guarded vs our headline
   answer decides. Exception: coral Outlook at 365 d has 38 guard rows, scored without the net, labelled (Q12).
9. **Coverage.** A product that misses rows is scored on the rows it covers, and ours on the same rows. A group
   needs 10 covered rows. Coverage, our all-row MAE and a "filled" line are printed beside.
10. **Metrics and "beats".** The engine's own functions (score_table, metric_by_key, _paired_contrast,
    contrast_tag, blocked_jackknife) with the nowcast band at every lead. MAE headline; anomaly R2, corr2, hit
    rate, calibration ratio and the reference rows beside. Timid wins flagged.
11. **Coarse products** (EAC4 0.75 deg, SEAS5 FWI 1 deg) also get a resolution-matched table. It never decides.
12. **Pre-registration: two Parts (Q22).** Part A (coral, defo, PM2.5, NDVI) and Part B (fire), each signed
    before any of its test scores, listing: rival list, every product manifest (file, size, sha256, licence,
    dates), code hashes, the pinned common-harness hash, families, constants, the T1 boundaries, and the R10 list.
13. **Reuse.** The human tool (D:/treeroute/rivals_human_build) imports `rivals.layout` and `rivals.harness`
    read-only. Problem-specific code lives only in per-product adapters (write an index table, never read a label)
    and in M-kind runners (read labels only through the slim copy, rule 6).
14. **One combined rival table.** A joiner reads both boards, refuses on any identity mismatch, and writes
    D:/treeroute/rivals_table/<stamp>/RIVALS_TABLE.md and .csv. Per problem and lead: our headline, common rivals,
    human P/L rows with the A rows directly beside, own-history rows, reference rows. No "best rival" line.
15. **protocol.md changes to apply at build:** :121 cite "C11 c" (not "C11 a"); H2 T1 boundary from R8 (rule 3);
    H5 L rows only where a ruling asks; §4 reading rule for the coral L row (rule 4); families F5/F6 and the L1
    print (rule 5); M-kind label reads (rule 6); separate pick per forecast-only product (rule 7); H16 two Parts;
    §5 the downloader does not take the heavy-job lock (§6 below); HQ4 and HQ5 now go to the owner (Q6b, Q7).

## 4. DOWNLOADS AND DATA PREP

Every download is an owner command, approved one by one, logged in product_manifest.json under
D:/treeroute/human_products/<product>/<version>/. Disk now: D: 38 GB free (93% full), C: 14 GB free.
Downloads run in a separate downloader script that does NOT take the heavy-job lock (network only, small RAM).
The PC must stay on and awake while the queue runs.

| # | Download | Needed for | Size | Network time | Licence / account (owner) | Processing after |
|---|---|---|---|---|---|---|
| D0' | Timing probe: ONE full-size merged-box SEAS5 request (12 starts, leads 150-184, 25 members) | Re-derives D3 queue time and size | ~0.03-0.6 GB | 0.5-1 h | EWDS (accepted) | none |
| D1 | CAMS EAC4 monthly pm2p5, 2003-2023, netCDF | PM2.5 nowcast rows | ~0.12 GB | 0.5-1.5 h, mostly ADS queue | ADS: create key file (no ~/.adsapirc; ~/.cdsapirc points to CDS) + one CAMS licence click. cdsapi 0.7.7 installed | Reader + map to 4 km units: 10-20 min |
| D2 | CEMS GEFF-ERA5 FWI (`cems-fire-historical-v1`), 2003-2022 | Fire lead 0 | ~0.4 GB (per-region boxes) to ~2.2 GB (merged boxes) | 5-16 h EWDS queue (measured 1,590 s per 5-year request) | EWDS: accepted (confirm still valid) | Daily to unit-month mean: ~1 h |
| D3 | CEMS GEFF-SEAS5 FWI (`cems-fire-seasonal`), 240 starts 2002-08..2022-07, leads 150-184, members 0-24 | Fire lead 6 | ~1.5 GB (per-region boxes) to ~6.3 GB (merged boxes) | ~3-17 h with 3 queued, ~7-50 h serial (re-derived); old worst 36-100 h serial kept until D0' | EWDS: accepted | Members x leads to unit-month: 2-3 h |
| D4 | GADM 3.6 level 2 for the defo regions | Defo admin divisions | ~0.5-1.5 GB | 0.5-1 h | Free academic use, no redistribution | Clip, rasterise to Hansen tiles: in the defo build |
| D5 (optional) | SEAS5 monthly single levels, system 51 (or 5) | NDVI lead 6 optional | ~3.3 GB GRIB, more as NetCDF | 3-12 h CDS queue | CDS licence click | 1-2 h |
| D6 (REQUIRED) | ~200 site-days from ERDDAP NOAA_DHW | Coral: proves our recomputed DHW / alert equals NOAA's grid | tiny | 10-20 min | public | compare script, minutes. Refuse if the mismatch exceeds rounding |

Sizes: recomputed from D:/fire/region_bbox.csv. Per-region boxes: 19,783 points at 0.25 deg, 1,784 at 1 deg.
Greedy 45 deg merge (~10 boxes): 114,165 and 7,703. At the measured bytes per value that gives the upper bounds
above; compressed ocean masks cut them somewhat. Total downloads ~3-10 GB (D1-D4, D0'). D: headroom: 38 GB free,
common exports need 6.7-10 GB per lead, so delete each scored export copy (Z3) and prefer per-region boxes with
many starts per request if D0' shows the queue allows it.

D3 queue, re-derived: D:/fire/cems/batch_test.log (2026-09-01, the old D0 smoke, already run) line B fetched
12 starts x 51 members x 92 days over a 4x5 box in 117 s (3.22 MB). A merged-box request with 12 starts, 35 days
and 25 members holds ~7x those values; ~10 boxes x 20 requests = ~200 requests at ~2-15 min each. The old 12-34 min
per request was the pace of single-region full-year fetches (seas_angola_zambia_fire_belt_2021/2022.nc, 12 min
apart). D0' replaces the guess with one measured full-size request.

Prep that needs no download (machine time in section 5):
- NDVI: one pass over D:/monthly_panel for NDVI, precipitation and soil moisture (0.5-1.5 h).
- Defo: about 20 distance-to-edge maps over 9.3 Gpx of Hansen tiles, 6 workers, RAM under 2 GB each
  (1.5-2.5 h). The builder must reproduce `loss_px` and `forest2000_px` of D:/defo_target cell by cell, or stop.
- Coral: DHW / alert from the SST file and the official climatology at T-2 and at T-L-2 (~1 h on HDD).
- Every problem: `slim` copy of the export columns (5-15 min per lead, 14 leads: 1.2-3.5 h).

## 5. TIME FOR THE HUMAN RIVALS

"Machine" = this PC busy (one heavy job at a time). "Network" = waiting on a queue; the PC stays free but awake.
"Agent" = code and toy tests, done while the machine runs other jobs. Protocol = tune, lock, refit, score at
1-3 h per problem (protocol.md:338-344).

| Problem | Network | Machine (work + protocol) | Machine (optionals) | Agent build | Owner actions |
|---|---|---|---|---|---|
| Shared tool (slim, maps, lock, joiner) | - | slim 1.2-3.5 h; join minutes | - | ~2 days | review; sign Parts A and B |
| Coral | 10-20 min (D6) | 1-1.5 h + 1-3 h = 2-4.5 h | 0 | ~1 day | Q11-Q13, Q23 |
| Defo | 0.5-1 h (GADM) | 2-4 h + 1-3 h = 3-7 h | frozen-2019 form: ~0 | ~1 day | approve D4; Q14-Q15 |
| NDVI | 0 | 1-2 h + 1-3 h = 2-5 h | Kraft lead 0: +2-4 h CPU | ~1-1.5 days | Q8-Q10 |
| PM2.5 | 0.5-1.5 h (EAC4) | 0.5-1.5 h + 1-3 h = 1.5-4.5 h | (MERRA-2 included) | ~0.5 day | ADS key file + licence click; approve D1; Q6, Q6b, Q7, Q19, Q21 |
| Fire | ~10-50 h wall (D0', D2, D3); worst ~100 h serial | 3-4.5 h + 1-3 h = 4-7.5 h | ENSO-lag +1 h; Turco SPI-lag +1 h (Q20) | ~0.5-1 day | confirm EWDS; approve D0', D2, D3; Q3, Q16-Q17, Q19-Q20, Q24 |
| **Total** | **~10-50 h, overlaps other work** | **~14-32 h** | **+3-6 h, so ~18-38 h** | **~6-7 agent days** | 1 key file + 1 licence click, 1 EWDS check, 5 downloads + D6, 2 Part signatures |

Fire is the long pole. Its time is network queue, not CPU. Start D0' on day 1.
(The earlier 15-25 h left out `slim`, under-priced the protocol, and counted ENSO-lag twice.)

## 6. TOTAL TIME FOR ALL RIVAL RESULTS

Common board figures are the build's latest (D:/treeroute/rivals_build/INTEGRATE_REPORT.md:24-27, :158-189;
RIVALS_BUILD_REPORT.md). They were **priced before rulings Z2 and AA2-AA4; re-price after the fire probe.**
AA2 (early stopping), AA3 (63 bins while tuning) and AA4 (lean export) lower the upper bound; Z2 (out-of-core RF)
may raise the RF share (~13 h). Ruling Z1 dropped the ~15.5 h pm25 re-run. Phase 2 dropped (AA1), disclosed.

| Block | Machine time | Notes |
|---|---|---|
| Common board, lean (export ~14-26 h + fits ~12-24 h) | 26-50 h | priced before Z2/AA. coral 0.1 h, fire ~2.2+2.6 h, pm25 ~2.5+5 h, defo ~11.6+3.5 h, ndvi ~7.4+2.5-15 h |
| Common edge extensions (only if picks sit at 800 rounds) | 0 to ~29 h | priced before Z3/AA2. defo carries ~16.6 h of it |
| Human rivals (section 5) | 18-38 h | plus ~10-50 h network, overlapped |
| **Total, all rival results** | **44-88 h; worst ~117 h** | the only total |

**Calendar** (one overnight session = about 10 h of machine time; today Wed 2026-10-21; submission ~25 Nov):

| Milestone | Date |
|---|---|
| Gates: Z2 build, AA build, common rival Part re-signed | by ~23 Oct |
| Night 1 (common coral) | no earlier than ~23-24 Oct |
| Human Part A signed | after the common harness signature, ~26-30 Oct |
| All rival results, typical (5-9 overnights) | ~3-12 Nov |
| All rival results, worst (~12 overnights) | ~15 Nov |
| Fire human result if the EWDS queue runs serially | up to ~1 week later than the rest |
| Cut-off for fire lead 6 (Q24): after it, reported as "pending" | 18 Nov |
| Writing window | ~2 weeks |

**What runs in parallel:**
- Downloads (D0'-D4, D6) run on the network while the common board uses the CPU. The downloader does not take the
  heavy-job lock, so queue time overlaps machine time. Keep the PC awake.
- The agent builds the human tool and adapters on toy data while the common board runs.
- Human fits are light (1-7.5 h each). They run in the evening before a common overnight job, never at the
  same time as one (the heavy-job lock).

**Suggested order:**
1. Day 1: owner approves D0', D1, D4, D6; creates the ADS key file and clicks the CAMS licence; confirms EWDS.
   D0' runs. Agent builds `slim` first.
2. Gates: Z2 build, AA build, common rival Part re-signed (AA5, Z4). No common night before this.
3. Nights 1-2: common coral, then fire (ruling Y4). `slim` each export before it is deleted. Start D2 and D3
   (sized from D0'). D1, D4 and D6 finish. Check BoM ACCESS-S archive.
4. Nights 3-5: common pm25, then defo. Agent finishes the human tool and the coral, defo, PM2.5 and NDVI adapters.
5. After the common harness is signed: pin its hash; owner signs human **Part A** (coral, defo, PM2.5, NDVI).
6. Evenings or one night: human coral, defo, PM2.5.
7. Nights 6-8: common NDVI (one lead at a time); human NDVI H1 (+ Kraft) after it.
8. When D2/D3 are hashed: owner signs human **Part B** (fire); human fire. Then edge extensions if any. Then the
   joiner: ONE rival table.

## 7. OWNER DECISION SHEET

| # | Question | Options | RECOMMENDED | Reason |
|---|---|---|---|---|
| Q1 | Accept the rival list of section 2, including "no human rival" at PM2.5 6/12, NDVI 6/12, fire 12, coral 183/365? | yes / change | **yes** | No published or operational method reaches those leads; labelled extensions and reference rows stand in |
| Q2 | Accept the protocol answers below, item by item (HQ4 moved to Q6b, HQ5 to Q7, HQ-P2 to Q19, HQ-C4 to Q12) | each yes/no | **yes to each** | Same rules as the common board; separate tool keeps the signed board untouched |
| Q2.HQ1 | Where the human rivals live | (a) separate tool, imports the common harness read-only / (b) inside rivals_build | **(a)** | (b) changes a signed board |
| Q2.HQ2 | Safety net | (a) raw and guarded, guarded decides / (b) raw only | **(a)** | Same as the common board (Y3 Q11 c) |
| Q2.HQ3 | Partial coverage | (a) covered rows decide, "filled" printed / (b) filled rows decide | **(a)** | (b) scores the normal on missing rows |
| Q2.HQ6 | Calibration choices | (a) family x links x <=3 stats, picked on inner MAE / (b) one fixed map | **(a)** | Each product gets its best train-only mapping |
| Q2.HQ7 | Product cannot reach a lead | (a) no row + optional labelled tier-A "advantaged horizon" row / (b) nothing | **(a)** | Shows the CRW Outlook without hiding it |
| Q2.HQ8 | M rivals read labels up to the T2 step | (a) yes, as our history block (D54 a) / (b) frozen at the fit cut | **(a)** | What a forecaster has at the issue date |
| Q2.HQ9 | Constants | min 10 covered test rows per group; min 100 fit rows in >= 3 groups; unit index mean >= 3 rows | **as listed** | 10 is the engine's own row floor |
| Q2.HQ10 | Tuning at leads | (a) pick at the nowcast, pin, refit per lead; forecast-only products picked on their lowest covered lead / (b) re-pick per lead | **(a)** | Mirrors Y3 Q12 a |
| Q2.HQ11 | Short real-time archive | (a) re-forecasts for train, real-time for test, disclosed / (b) real-time years only | **(a)** | More fit rows; ensemble change disclosed |
| Q3 | Nowcast parity: a rival may use target-month weather, but no target-month observation of the target; T1 boundary read from R8 per rival? | yes / strict (t-1 for all) | **yes** | That is what our nowcast reads (R8 nowcast_steps 0) |
| Q4 | Add persistence and damped persistence at the nowcast (pm25, ndvi, fire, defo) as reference rows? | yes / no | **yes** | Leads 6 and 12 have them; nowcasts do not; minutes of work. At PM2.5 lead 0 it is the human baseline to beat |
| Q5 | Approve downloads D0' (probe), D1, D2, D3, D4 (~3-10 GB) and D6 (required, tiny)? | each yes/no | **yes to all** | Licensed for research, needed for the primary rivals; D6 proves the coral rival is NOAA's product |
| Q6 | PM2.5 P row product | EAC4 / MERRA-2 | **EAC4, MERRA-2 optional** | EAC4 is the named ruling D4 baseline; MERRA-2 only if the ADS click doesn't happen |
| Q6b | Same-month EAC4: tier A (printed beside, never decides) instead of the D1/D4 a nowcast baseline? (amends D1/D4 a) | yes / no (it decides, labelled) | **yes** | It assimilates the target month's AOD; it is shown as "real practice" beside the parity row |
| Q7 | PM2.5 calibration rows (HQ5; amends D4 "fitted on donors only") | all bank units to the cut (gauged global) / donors only | **gauged global** | D4 predates LORO; one rule for every rival |
| Q8 | NDVI H1 beyond the published ~10 weeks (leads 6 and 12) | (a) both leads "no published method"; H1-direct printed as a labelled extension, never decides / (b) both leads: H1-direct decides, labelled | **(a)** | Same rule at both leads; L rows only where a ruling asks |
| Q9 | NDVI H1 inputs | published (precipitation, soil moisture) / add VPD | **published only** | Adding VPD makes it our method, not theirs |
| Q10 | NDVI optionals | Kraft at lead 0 (CPU); SEAS5 at lead 6 | **Kraft yes (CPU, no GPU); SEAS5 no** | Kraft is the known ML baseline; SEAS5 costs 3.3 GB and a queue for little expected skill |
| Q11 | Coral MMM | NOAA official / package | **NOAA official** | It is NOAA's product as shipped (checked by D6) |
| Q12 | **Amend ruling C11 (c "Both": lagged DHW and the real Outlook head to head)?** Head to head cannot hold under parity at 183 or 365 d (Outlook issued 42-49 or ~225 days after our issue) | (a) Outlook tier A at 183 d only / (b) tier A at 183 d and 365 d, 365 d without the safety net (HQ-C4) / (c) keep C11 c literally: the Outlook decides as a labelled advantaged row | **(b)** | Closest to C11 c that stays honest; (c) is defensible since a win over a better-informed rival is stronger, owner's call |
| Q13 | Coral alert scale and map loss | 5 levels (2016-19) or 8 levels; squared-error maps with an L1 map printed beside (fire, coral, defo) / L1 map competes in the coral pick (as C12 kept hgb_l1 on coral) | **5 levels; squared error decides, L1 printed beside** | Scale in use in the test years; engine fits the mean; owner may pick the C12 parallel for coral |
| Q14 | Defo: what decides | (a) both forms (as shipped, isotonic-calibrated) are P rows; "ours beats VT0007" only if ours beats both, else each verdict printed / (b) as shipped only / (c) calibrated only | **(a)** | Removes the choice between forms as a straw-man risk |
| Q15 | Defo method details | forest-edge distance from treecover2000; GADM 3.6 level 2; land only | **all three yes** | The published method; the extra forest map only helps the rival |
| Q16 | Fire SEAS5 start | 1st of M-5 / 1st of M-6 (strict) | **M-5** | Its initial state is our issue instant; M-6 throws away a month |
| Q17 | Fire ENSO-lag optional (leads 6 and 12) | yes / no | **yes** | 1 h, no download, ONI is in the panel |
| Q19 | Calibration strength for PM2.5 and fire (old per-cell MOS 3.926 vs pooled 9.81; agencies read FWI against local climate) | (a) add F5 per-unit MOS (N and I kinds) and, for fire, F6 = per-unit FWI percentile x per-group ratio on the normal; same inner-MAE pick / (b) pooled F1-F4 only, disclosed as a limitation | **(a)** | Pooled-only is open to a straw-man charge; all candidates are train-only and pre-registered |
| Q20 | Fire: Turco et al. 2018 SPI-lag climate-fire model (observed SPI at the issue month from panel precipitation), leads 6 and 12 | (a) add as a second optional beside ENSO-lag / (b) replace ENSO-lag / (c) reject in writing | **(a)** | The standard published global seasonal burned-area forecast; ~1 h, no download |
| Q21 | PM2.5 GEOS-S2S-2 at lead 6 (HQ-P3) | (a) not planned, disclosed / (b) one short verification task first | **(a)** | Output and hindcast archive unverified (HTTP 503); possibly discontinued; research system |
| Q22 | Human pre-registration | (a) two Parts: A = coral, defo, PM2.5, NDVI; B = fire, signed when D2/D3 are hashed / (b) one Part after D2/D3 | **(a)** | (b) delays every human score by the fire queue (10-50 h, worst ~100 h) |
| Q23 | Coral history reference row | add "last visit at the site", T2-legal / no (say why) | **add** | Coral reviewers expect a site-history baseline |
| Q24 | Fire lead-6 cut-off | after 18 Nov fire lead 6 is reported as "pending" / no cut-off | **18 Nov** | Fire is the long pole for the ~25 Nov submission |

## 8. RISKS

| # | Risk | What we do |
|---|---|---|
| R1 | EWDS queue slower than measured; fire SEAS5 alone could take ~100 h serial | D0' times one full-size request; 3 jobs queued; Part B separate; cut-off 18 Nov (Q24) |
| R2 | EAC4 licence never clicked | MERRA-2 (on disk) becomes the P product; disclosed |
| R3 | An export deleted before `slim` | `slim` built first; owner checklist; else a re-export (hours) |
| R4 | Common harness hash changes after we pin it | Tool refuses on mismatch; re-pin only after a signed change |
| R5 | Disk: D: 38 GB free, C: 14 GB; common exports need 6.7-10 GB per lead; fire downloads up to ~8.5 GB | Delete scored export copies (Z3); per-region boxes if D0' allows; skip SEAS5 for NDVI |
| R6 | Common hours priced before Z2 and AA2-AA4 | Re-price after the fire probe; AA lowers the upper bound, Z2 may raise RF (~13 h) |
| R7 | pm25 export still refuses a P1-P15 parity check (Z1 condition) | Owner is asked; pm25 rivals wait |
| R8 | A product or M runner breaks parity silently (wrong init, off-by-one date, label read past T2) | `info_end` and `target_obs_end` per row; shifted-product and shifted-label tests must refuse; VT0007 lossyear assert |
| R9 | Coarse products (1 deg FWI) look bad at 4 km | Resolution-matched table printed (never decides) |
| R10 | Candidates are not blind. Choices influenced by an old score on rows inside the current test window: **fire** statistic `fwi_mean` and C-B form (Parts 496-498 scored 2021-22, inside test 2019-22; old link used 2019+ rows); **coral** stats `x__baa060_w20`, `x__baa4p_w20` (chosen after CRW Parts 456-457, same test years 2016-19); **PM2.5** Q19 per-unit MOS (old board D:/pm25_rivals/full/board.csv, M2 3.926; years to confirm); **NDVI** Kraft/BARDL (Parts 417-426; years to confirm); **defo** frozen-2019 form (udef_a, defo_papers.py, frozen at 2019; years to confirm) | Each listed by name in Parts A/B; years confirmed before signing; nothing added after a test score |
| R11 | Re-forecast vs real-time differences (fire SEAS5); Outlook v5 reissue; Hansen reprocessing; reprocessed MERRA-2 months | Each disclosed; Hansen reprocessing hits our model equally |
| R12 | Per-unit fits fail on short units (NDVI H1, F5, F6) | Fallback to the pooled map or the normal, counted and disclosed, never silent |
| R13 | All hours are extrapolated (x) | Re-price after the first problem of each kind |
| R14 | Coral recomputed DHW differs from NOAA's grid | D6 required; refuse above rounding |
| R15 | BoM ACCESS-S archive exists after all | Verify before Part A; if found, add or reject in writing before signing |

## 9. SOURCES

- Scratch notes: D:\treeroute\rivals_plan_human\protocol.md (H0-H19, HQ1-HQ11, sections 2, 4, 5, 6;
  :121, :248-250, :321, :336-344); research_pm25.md (§0, §3 :128-136, :106, HQ-P2, HQ-P3); research_ndvi.md;
  research_fire.md (§2 :62-66, time table :83-94, :96 licence); research_defo.md; research_coral.md (§2.1, §2.3
  :149, §3, HQ-C4, HQ-C5).
- Common board times: D:/treeroute/rivals_build/INTEGRATE_REPORT.md:24-27, :158-189;
  RIVALS_BUILD_REPORT.md (ATTENTION 1-5); RIVALS_PLAN_COMMON.md:16, :49.
- Rulings: OWNER_RULINGS_2026-10-06.md sections Y (Y1-Y4), Z (Z1-Z4), AA (AA1-AA5, :164); QUESTIONS_ROUND3_HANDOFF.md
  :332-337, :370-378, :468-480 (C11 c, C12, D1, D4).
- Engine: treeroute/timing/cuts.py:50-60 (latest_label_step); HEADLINE_MODEL_TABLE.md (our scores per lead).
- Coral timing: D:\treeroute\coral_build\SPEC_CORAL_TABLES.md:165-171 (last SST day C - g - 1 = T - 2 at nowcast).
- Runs (checked 2026-10-21): derived.json R8 `nowcast_steps` counts and R17 `start_offset_steps` of
  D:/treeroute/runs/fire/headline/20261017_869d1f38 (offset 1), pm25/headline/20261007_74e67609 (0),
  ndvi/headline/20261016_d1de3158 (1); lead-0 test_preds `base__*` columns of all five runs.
- Fire downloads: D:/fire/cems/batch_test.log (lines A, B); D:/fire/cems/raw/ (SMOKE_*.nc and seas_angola_* fetched
  2026-09-01); D:/fire/region_bbox.csv; fire_cems.py:58 (EWDS endpoint); FIRE_EXPERIMENTS.md:184-186.
- Products: https://ads.atmosphere.copernicus.eu (EAC4);
  https://ewds.climate.copernicus.eu/datasets/cems-fire-historical-v1 ;
  https://ewds.climate.copernicus.eu/datasets/cems-fire-seasonal ; Di Giuseppe et al. 2024, Sci. Data,
  doi 10.1038/s41597-024-02948-3; https://coralreefwatch.noaa.gov/product/5km/methodology.php ;
  https://verra.org/documents/vt0007-unplanned-deforestation-allocation-v1-0 ; https://github.com/ClarkCGA/UDef-ARP ;
  https://gadm.org/license.html ; Salakpi et al. 2022, https://nhess.copernicus.org/articles/22/2703/2022/ ;
  Barrett et al. 2020, https://dx.doi.org/10.1016/j.rse.2020.111886 ; Kraft et al. 2019, doi 10.3389/fdata.2019.00031;
  Turco et al. 2018, Nat. Commun. 9:2718, doi 10.1038/s41467-018-05250-0;
  https://forum.ecmwf.int/t/changes-to-contribution-to-c3s-seasonal-forecast-systems-from-ecmwf/1539 .

## REVIEW LOG (2026-10-21)

Three reviews: legitimacy (L1-L13), feasibility (F1-F12), completeness (C1-C16). All applied unless noted.

| Issue | Change |
|---|---|
| F1, C1 phase 2 dropped (AA1) | Phase-2 rows, "Everything" line, Q18 and the 10 Nov sentence deleted; "Phase 2 dropped (AA1), disclosed" added; one total |
| F2, C8 common hours predate Z2/AA | Both figures marked "priced before Z2 and AA2-AA4; re-price after the fire probe"; AA build + re-signed Part as a gate before night 1 (ATTENTION 4, §6) |
| F3 order vs H16 | Two human Parts (A, B), Q22, §3.12, §6 order |
| F4 fire sizes | D2 0.4-2.2 GB, D3 1.5-6.3 GB from region_bbox.csv; total ~3-10 GB; disk headroom note |
| F5 D0 already run | D0 replaced by D0' (one full-size timing request); D3 queue re-derived from batch_test.log |
| F6, C14 download line | §1 download line and Q5 rewritten with one total |
| F7 machine total | Human 18-38 h (slim added, protocol 1-3 h per problem, ENSO counted once, Turco added); core 44-88 h, worst ~117 h; 5-9 overnights, worst ~12 |
| F8 heavy-job lock | Downloader is a separate script, no heavy-job lock; PC awake (§4, §6) |
| F9, C16 calendar | Dated milestones; serial-queue case; fire cut-off 18 Nov (Q24) |
| F10, L12 licences | Checked once: research_fire.md:96 and fire_cems.py:58 (EWDS endpoint), files fetched 2026-09-01. Now "EWDS accepted (confirm); ADS key file + one click" |
| F11 D1 format | netCDF ~0.12 GB; no ~/.adsapirc (checked; ~/.cdsapirc points to CDS); key file is an owner step |
| F12 re-forecast note | "Re-forecasts for starts to 2016-12; real-time from 2017-01 (part of train, all of test)" |
| L1, C6 calibration strength | F5 per-unit MOS, F6 fire per-unit percentile x per-group ratio (C-A); pooled vs per-unit stated; fire lead-0 cell fixed; Q19 |
| L2 coral timing | Read at d* = T - 2 (nowcast) and T - L - 2 (183/365) |
| L3, C10 NDVI honesty | Lead 6 and 12 both "no published NDVI forecast"; H1-direct a labelled extension; §1 wording; Q8 |
| L4, C11 PM2.5 nowcast | Persistence named as the baseline to beat; lagged EAC4 "the operational product at parity"; same-month EAC4 printed beside |
| L5, C2 C11 c | Q12 rewritten as a request to amend C11 with options a/b/c; protocol.md:121 citation fix listed (§3.15) |
| L6 hidden ruling changes | Q6b added (HQ4 vs D1/D4 a); HQ4 out of Q2; Q2 listed item by item (C15) |
| L7 defo form | Both forms P rows; "beats" only if ours beats both (Q14) |
| L8 coral D6 | D6 required before Part A; refuse above rounding |
| L9 fire picks | F-ERA5 and F-SEAS5 are separate rivals, picked separately |
| L10 L rows | L rows only where a ruling asks (C11); coral L wording rule (§3.4; protocol §4 change listed) |
| L11 ACCESS-S | Coral 183/365 wording narrowed; verify before Part A (R15) |
| L13, C12 map loss | L1 isotonic map printed beside on fire, coral, defo; C12 parallel in Q13 |
| C3 Turco 2018 | Added as optional at fire 6/12 (Q20); not verified on the web this session beyond the DOI the review cited |
| C4 GEOS-S2S-2 | Leak note corrected; Q21 |
| C5 T1 tied to the run | T1 boundary from R8 per rival, recorded in the lock; toy test (§3.3) |
| C7 M-kind label reads | Labels only via the slim copy; `target_obs_end`; shifted-label test; VT0007 lossyear assert (§3.6) |
| C9 old-score influence | R10 lists each influenced choice per problem; years for PM2.5, NDVI and defo to confirm before signing |
| C13 coral history | Last-visit reference row (Q23) |
| Not applied | protocol.md itself is not edited (this task edits only this file); its changes are listed in §3.15 |
