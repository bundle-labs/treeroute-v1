# Human rivals for coral bleaching (percent bleached per survey visit)

Written 2026-10-21 by the coral researcher of the human-rivals workflow. PLAN ONLY. Nothing was downloaded,
installed, built, run or scored. Read-only checks of files on disk (metadata, counts, dates) only.
Fits the uniform protocol D:/treeroute/rivals_plan_human/protocol.md (rules H0-H19; tiers P / A / L; maps F2-F4).
Project root = `C:\Users\<user>\Desktop\data set for reserch paper\`.

---

## 0. Short answer

| Lead | Primary human rival | Tier | Optional (at most one) | Data on disk? | Download |
|---|---|---|---|---|---|
| 0 (nowcast) | **NOAA CRW 5 km v3.1 heat stress (DHW; BAA 7-day max) at the day before the survey** | P | none needed | YES: CoralTemp SST at every site + the official CRW MMM climatology | none |
| 183 d | **No legitimate human forecast exists.** The reference rows stand in (donor median 8.294, predict-zero 8.100). Ruled labelled row (C11 c): the same CRW heat stress read at the issue day ("NOAA's nowcast rule fed old heat") | L | **CRW 4-Month Outlook v5 at its 140-day maximum** ("advantaged horizon": issued ~42-49 days AFTER our issue date) | YES: all 1,984 Outlook files, 2011-2020, 4 percentile products | none |
| 365 d | **No legitimate human forecast exists.** Reference rows stand in. Ruled labelled row: CRW heat stress at the issue day | L | same Outlook row (issued ~225 days after our issue date) | YES | none |

- Owner ruling C11 = (c) "both": lagged DHW, labelled, AND the real Outlook head to head
  (QUESTIONS_ROUND3_HANDOFF.md:332-337, :472). This plan delivers exactly that.
- **No download is needed.** Total work: about 1 agent day to build and test, about 1-1.5 h of machine time, seconds
  of fitting. Optional: a ~15-minute official-value check from NOAA ERDDAP (owner command; section 5).
- Old numbers (Parts 456-457) are history only. They used a spatial donor split, a leaky pool and other rows.

**ATTENTION C-A1 - the nowcast rival is a subset of our own inputs.** Our features already hold DHW windows
(dhw_84 etc.) computed from the same CoralTemp SST (SPEC_CORAL_TABLES.md:190). The rival differs only in the MMM
(NOAA's fixed official climatology vs the package's own `mmm_from`) and in the rule (one index, one monotone map).
That is the point: it measures what the model adds over NOAA's rule. State it in the Part.

**ATTENTION C-A2 - the Outlook cannot reach 183 or 365 days.** Every file has Week_01..Week_20 only; Week_20 ends
icwk+141 days (checked on 4 files, e.g. icwk 2015-11-22: Week_20 2016-04-04 to 2016-04-11). Under parity it has no
row at 183 or 365 (protocol H5). Its only use there is the tier-A row, which never decides.

**ATTENTION C-A3 - the Outlook archive on disk is a 2019 reissue.** Every checked file (icwk 2011, 2015, 2017, 2018)
has `date_issued` 2019-07 to 2019-08. The content is CFSv2 initialised at icwk; the v5 algorithm was applied later.
Disclose it.

---

## 1. Our design (what the rivals must match)

- Run: D:/treeroute/runs/coral/headline/20261020_f3b8e3da (lock FREEZE_20261020T100907Z, engine 930d961c).
  Store read-only: D:/treeroute/coral_build/coral_store/20261020_014201/lead_{0,183,365}.parquet (protected root).
- Test: 2016-2019, 2,312 scored visits in 37 groups (store has 2,347 test rows before the 11 V5 exclusions).
  By year 883 / 575 / 454 / 435 (store, all 2,347). By programme (scored): Reef_Check 1,932, FRRP 190,
  McClanahan 189, AGRRA 1 (HEADLINE_MODEL_TABLE.md coral note).
- Leads 0 / 183 / 365 days. Issue date = T - L. Every feature value is dated before C - g, g = 1 day
  (SPEC_CORAL_TABLES.md:163-173). So at the nowcast the last SST day used is T - 2.
- Cuts (derived.json R11, ordinals checked): lead 0 fit 2015-12-31, inner 2012-12-31; lead 183 fit 2015-07-02,
  guard 2012-07-02; lead 365 fit 2015-01-01, guard 2012-01-02 (also SPEC_CORAL_TABLES.md:120-121).
- Ours: MAE 6.698 / 7.710 / 8.281 vs donor median 8.294; predict-zero 8.100 (HEADLINE_MODEL_TABLE.md:22-24).
  Per programme at the nowcast predict-zero wins on Reef_Check (3.83 vs 3.17).
- Contrast band (coral) 0.918; groups 37 (RIVALS_PLAN_COMMON.md:115). Fallback: donor-row median (ruling V1).

---

## 2. Candidates

### 2.1 R1: CRW 5 km v3.1 heat stress at the issue date (PRIMARY at lead 0; labelled L at 183 / 365)

- **What.** NOAA Coral Reef Watch daily HotSpot, Degree Heating Weeks and Bleaching Alert Area from CoralTemp SST.
- **Who uses it.** The default worldwide: GBRMPA, FKNMS/BleachWatch, Allen Coral Atlas triggering, 219 Virtual
  Stations; India, the WIO and Mexico run clones of the same algorithm (CORAL_BASELINE_LANDSCAPE.md:13-15, :29).
  As a bleaching predictor it is the standard of the literature: DeCarlo 2020 (ETS 0.150), Whitaker & DeCarlo 2024,
  Liu Foo & Guan 2024, Fukui 2026 (CORAL_BASELINE_LANDSCAPE.md:30-33, :68-80). Operational status OPERATIONAL.
- **Definition (verified, https://coralreefwatch.noaa.gov/product/5km/methodology.php).** HotSpot = SST - MMM.
  DHW = sum of daily HotSpots >= 1 deg C over the last 84 days, / 7. BAA: No Stress HS <= 0; Watch 0 < HS < 1;
  Warning HS >= 1 and 0 < DHW < 4; Alert 1 DHW 4-8; Alert 2 8-12; Alert 3-5 at 12/16/20 (added Dec 2023). BAA 7-day
  max = highest daily level of the last 7 days. MMM: CoralTemp 1985-2012, re-centred to 1988.2857.
- **Period.** CoralTemp v3.1 daily from 1985-04-01 to now (ERDDAP NOAA_DHW, https://coastwatch.pfeg.noaa.gov/erddap/info/NOAA_DHW/index.html,
  coverage 1985-04-01 to 2026-10-18). Covers every train year (1994-2015) and the test window. All leads.
- **Data on disk (no download).**
  - D:/coral/drivers/sst_compact_all.npz, 932 MB: CoralTemp v3.1 daily SST per site pixel (10,254 site keys,
    116.5 M values), days 5479..18627 = 1985-01-01..2020-12-31. Fetched from
    https://oceanwatch.pifsc.noaa.gov/erddap/griddap/CRW_sst_v3_1 (coral_fetch_sst.py:42). Key = `site_key(lat, lon)`
    (coral_safe.py:97-107), the same key the store uses (SPEC_CORAL_TABLES.md:57).
  - D:/coral/drivers/static/ct5km_climatology_v3.1.nc, 81.5 MB: the OFFICIAL CRW v3.1 climatology
    (`sst_clim_mmm`, 12 monthly means, masks; 0.05 deg; content 1985-01-01 to 2013-01-01; date_issued 2019-02-02).
  - Licence: "available for use without restriction", credit requested (file `license` attribute). No account.
- **Not on disk:** the official daily DHW/BAA grids themselves. Not needed: they are a fixed function of the two
  files above. Optional check in section 5.
- **Alignment.** Space: the site's own 5 km pixel (the SST series already is that pixel). MMM: the climatology pixel
  holding the site; if masked (land/coast), the nearest valid pixel within 3 cells (pre-registered); none -> NaN
  -> row not covered (H11). Time: the index is read at day d* = C - g - 1 (= T - 2 at the nowcast; = T - L - 2 at
  a lead), the same last day our SST windows read. DHW needs the 84 days before d*; BAA 7-day max the 7 days ending d*.
  Month-precision train rows (2,128, 1994-2011, SPEC_CORAL_TABLES.md:81) use their own C, as the package does.
- **Stats (H6, max 3, pre-registered):** `x__dhw` (continuous, the core quantity), `x__baa7d` (0-4 scale as published
  during 2016-2019; levels 3-5 merged into 4, because they did not exist at the test issue dates), and none other.
  The pick between them is by inner MAE (H8) at the nowcast, pinned at 183 / 365.
- **Calibration (train rows only, per lead).** Protocol maps F2 iso_raw and F4 iso_anom on links identity, log_c,
  arcsine; isotonic direction from train Spearman (H6). Fit rows at each lead = that lead's refit rows (labels before
  the lead's fit cut: 2015-12-31 / 2015-07-02 / 2015-01-01); tune/inner and guard rows as the protocol says.
  Covered rows: essentially all (every store row has a CoralTemp series by construction, SPEC_CORAL_TABLES.md:94).
- **Leak risks.**
  - Must read DHW/BAA at d* or earlier, never the survey day or later. A "season maximum DHW" or "annual max DHW"
    (common in the literature) reads after the survey: FORBIDDEN.
  - The MMM content runs to 2012-12-31. It is before every test issue date (earliest 2015-01-06 at lead 365) but
    after early train rows. It touches the calibration only (SST, not labels). Disclose (static-map dating rule N2).
  - CoralTemp 2002-2016 is a reanalysis (Geo-Polar Blended reanalysis), NRT after Oct 2016
    (CORAL_BASELINE_LANDSCAPE.md:29). Our model reads the same SST, so this is parity, not an advantage. Disclose.
  - The v3.1 suite was released Apr/Aug 2018 (CORAL_BASELINE_LANDSCAPE.md:149). For 2016-2017 issue dates the live
    product was an earlier version. Content is info-legal; the algorithm version is later. Disclose.
- **Old result (history only).** "NOAA DHW bands" arm: NOAA's 1/4/8 bands on our dhw_84, isotonic on donor
  ecoregions: MAE 10.70 vs predict-zero 13.05 (n = 999, 2011-2019) (CRW_BENCHMARK_REPORT.md:118-126). Lagged:
  T-180 15.834, T-365 14.964 vs zero 13.518 (n = 953) (CRW_BENCHMARK_REPORT.md:141-150; CORAL_EXPERIMENTS.md:3661 Part 457).
- **Why redo.** Old split was spatial (donor vs test ecoregions, 1994-2019) not 2016-2019 temporal; the isotonic map
  was fitted on donor rows of ANY year, including 2016-2019 (coral_crw.py:259-299, :492-494); our arm had the Part 458
  pool leak; it used our package-style MMM, not NOAA's; leads were 180 not 183; rows were the CRW-coverable 953-999.
  Ruling X2: no legacy coral number is comparable (OWNER_RULINGS_2026-10-06.md:130).

### 2.2 R2: CRW Four-Month Coral Bleaching Outlook v5 (CFSv2) (OPTIONAL tier-A row at 183 / 365)

- **What.** Weekly, 0.5 deg probabilistic forecast of the Bleaching Alert Area, weeks 1-20 plus a 4-month composite.
- **Who uses it.** The de-facto forward-looking product worldwide, but filed by NOAA as EXPERIMENTAL; v5.0 public
  27 Mar 2018 (verified, https://coralreefwatch.noaa.gov/satellite/bleachingoutlook_cfs/outlook_cfs.php;
  CORAL_BASELINE_LANDSCAPE.md:17, :46). NOAA advises caution beyond 20 weeks. Only published verification: hit/miss
  counts vs CRW's own heat product, 2011-2015 (Liu et al. 2018; CORAL_BASELINE_LANDSCAPE.md:88-90).
- **Period.** Archive from icwk 2011-07-03 (2010 is HTTP 404) (D:/coral/crw/fetch_multi.log). Week_20 rows cover
  targets from about 2011-11-14. Covers the test window. Does NOT reach 183 or 365 days (max 141 days).
- **Data on disk (no download).** D:/coral/crw/nc/: 1,984 NetCDF4 files, 732 MB = 4 products (010, 030, 060, 090 perc)
  x 496 issues, icwk 2011-07-03 .. 2020-12-27 (2011: 26, 2012: 53, 2013-2016: 52, 2017: 53, 2018-2020: 52 each).
  The old report's "090 in progress" is out of date: all four are complete. Variables CRW_BAA_FourMonth,
  CRW_BAA_Week_01..20 (360 x 720), surface_flag; fill -5 on land. Old extraction (060 only):
  D:/coral/crw/crw_baa_060perc.parquet. Source https://www.star.nesdis.noaa.gov/pub/socd/mecb/crw/data/outlook/v5/nc/v1/outlook/.
  Licence: CRW free use with credit; no account.
- **Alignment.** Space: the 0.5 deg cell of the site; if land, the nearest ocean cell within 3 rings, max within the
  ring (old rule, coral_crw.py:112-121; 92.2% exact cell, 0 rows unmatched in the old extract,
  CRW_BENCHMARK_REPORT.md:88-93). This favours CRW; disclose. Time: for target date T, the issue whose Week_20 window
  [start_time, stop_time) contains T (window read from each variable's `start_time`, asserted, as coral_crw.py:186-193
  did). That issue's icwk is T-141..T-134, i.e. 42-49 days later than our 183 issue date and 224-231 days later than
  our 365 issue date. That breaks rule T1 in CRW's favour: tier A, never decides (protocol H5, HQ7).
- **Stats (pre-registered, max 3):** `x__baa060_w20` (the 60% composite managers read) and `x__baa4p_w20`
  (mean BAA over the 4 percentile files: a continuous score with up to 17 values, answering the old caveat that a
  5-level map caps the rival, CRW_BENCHMARK_REPORT.md:222-227).
- **Calibration.** Same maps F2/F4 x 3 links. Fit rows only where the Outlook covers: train visits from
  2011-11-14. Counts (store, train rows): before the lead-183 guard cut (2012-07-02) 239 rows in 22 groups; before
  the lead-365 guard cut (2012-01-02) **38 rows in 11 groups: below the protocol minimum of 100 (HQ9)**, so no
  guard-fit at 365; before the fit cuts: 2,270 rows / 38 groups (lead 183), 2,003 / 37 (lead 365). Picked on the
  lead-183 guard rows (protocol H8 rule for forecast-only products). Disclose the short calibration years.
- **Leak risks.** Advantaged issue time (above). The 2019 reissue (C-A3). Coarse 0.5 deg vs our 5 km. It never
  sees a bleaching label, so no target leak.
- **Old result (history only).** CRW @ week 20: MAE 13.389 vs predict-zero 13.518 (n = 953); McClanahan 47.49 vs
  zero 59.58; Reef_Check 4.62 vs zero 1.67 (CRW_BENCHMARK_REPORT.md:147, :163-167). Redo for the same reasons as R1.
- **Not used at lead 0.** At the nowcast the observed product (R1) is strictly better and info-legal.

### 2.3 Considered and rejected

| Candidate | Why not |
|---|---|
| BoM ACCESS-S seasonal thermal-stress outlook (operational, 6-month lead) | Australian waters only: 5 test groups, 181 of 2,347 test rows. No public archive found for 2016-2019 issues (not verified this session). Its skill is published for DHM at leads 0-2 months only (CORAL_BASELINE_LANDSCAPE.md:48). |
| NMME / CFSv2 monthly SST -> Degree Heating Months at 183 d (Jacox et al. 2022 style) | A research benchmark, not a coral product anyone issues (CORAL_BASELINE_LANDSCAPE.md:50). New download and new code. NMME tops out near 12 months, so it cannot cover the 84 days before T at 365 d. Not in ruling C11. Could be added later as a labelled research row if the owner asks. |
| CRW Multi-Factor Disease Risk | Disease, not bleaching (CORAL_BASELINE_LANDSCAPE.md:49). |
| Allen Coral Atlas bleaching monitor | It OBSERVES bleaching (target leak), starts 2019-02-18 (CORAL_BASELINE_LANDSCAPE.md:38). |
| ReefTemp Next Generation | Decommissioned; Australia only (CORAL_BASELINE_LANDSCAPE.md:35). |
| van Hooidonk et al. 2016 bleaching-onset projections | A decadal climate projection (year of annual severe bleaching), not a forecast of a season. |
| Re-tuned DHW thresholds (DeCarlo 2020, Whitaker & DeCarlo 2024) | Research variants of R1; R1's isotonic map already learns its own thresholds on train rows. |

---

## 3. Information parity per lead (protocol H2)

| Lead | R1 index day | Our last SST day | Tier | R2 issue | Tier |
|---|---|---|---|---|---|
| 0 | T - 2 | T - 2 | P | (not used) | - |
| 183 | T - 185 | T - 185 | L (nowcast rule fed old heat) | icwk in T-141..T-134 | A |
| 365 | T - 367 | T - 367 | L | icwk in T-141..T-134 | A |

R1 never reads a label, so rule T2 is empty for it. The calibration reads train labels only, before each fit cut.

---

## 4. Work on this PC (15.8 GB RAM, HDD)

| Step | Hours | Notes |
|---|---|---|
| Download | 0 | Everything is on disk. |
| Build the R1 adapter (official MMM lookup, DHW / BAA at d*, 3 leads) + tests | ~0.5 agent day | Test: with the package MMM in place of NOAA's, the adapter must reproduce the store's dhw_84 / hs_max_84 to 1e-9 (the store's replay rule, SPEC_CORAL_TABLES.md:239-242). |
| Build the R2 adapter (week-20 issue per row, ring rule, 4 products) + tests | ~0.3 agent day | Reuse the logic of coral_crw.py:105-211, not its file (it is old code). |
| R1 index tables, 3 leads x 13,694 rows | ~0.3 h machine | One read of the 932 MB npz (memory-mapped; few minutes on HDD) + the 81 MB climatology. RAM < 3 GB. |
| R2 index tables | ~0.5-1 h machine | 1,984 files x 21 layers of 360 x 720 int8, read once each. |
| Calibration fits | seconds | 2 stats x 2 maps x 3 links = 12 candidates per rival per lead. |
| Scoring with the engine metrics | minutes | 2,312 rows x 3 leads. |
| **Total** | **~1 agent day + ~1-1.5 h machine** | Coral goes first in the protocol order (ruling Y4). |

---

## 5. Optional check (needs an owner command: it is a download)

Pull official CRW_DHW and CRW_BAA_7D_MAX for about 200 test and train site-days from
https://coastwatch.pfeg.noaa.gov/erddap/griddap/NOAA_DHW (v3.1, 0.05 deg, 1985-04-01 to now; point queries, a few KB
each, ~10-20 minutes). Compare to the R1 adapter. Expected: exact match where the site pixel and the climatology pixel
agree. A mismatch above rounding means our recomputation is not NOAA's product: stop and report.

---

## 6. Owner questions (short)

- HQ-C1. Accept "no legitimate human rival" at 183 and 365, with R1-lagged (tier L) as the ruled C11 row and R2 as the
  one optional tier-A row? (Recommended: yes.)
- HQ-C2. R1 MMM: NOAA's official climatology (recommended; it is the product) or the package MMM (identical to our
  features; then R1 is just "our dhw_84 through a monotone map")?
- HQ-C3. BAA scale: the 5 levels published during 2016-2019 (recommended) or today's 8 levels?
- HQ-C4. R2 at lead 365 has no guard-fit (38 rows < 100). Score it without the safety net, labelled (recommended),
  or drop it at 365?
- HQ-C5. The protocol's isotonic maps use squared error while the headline is MAE. Keep (recommended: one rule for
  all problems), or add an L1 isotonic map for coral only?
