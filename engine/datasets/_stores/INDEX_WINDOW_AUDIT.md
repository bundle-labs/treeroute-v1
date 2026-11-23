# Index and target window audit (F10, plus the target windows R17 needs)

Written 2026-09-28 by the index-audit task, revised the same day after review. Status: **proposed facts, nothing signed.** The machine-readable proposal is `index_facts.yaml` in this folder. Every fact in it has `fact_status: unverified`; my view is in a separate `proposed_status` field, and `reviewed_by` / `date` are left empty for you. Every claim below carries a source: a file:line in this repo, a provider page (list at the end, [S1]...[S42]), or a read-only test on the panel values ([T1]...[T10]). "unknown" means I could not verify it.

## In short

- **34 columns of the shared monthly panel are global** (one value per month, the same in every cell of all 133 regions) [T1]. They are 19 NOAA/CPC climate indices, 8 SST boxes the repo computed itself from ERSSTv5, co2, and 6 FAO food prices. Three columns only *look* global in some regions and are not: `conflict_events`, `conflict_deaths` and `eddi_observed`. In 2019 they vary inside a region-month in 36, 32 and 36 of 133 regions, so they are per cell (the 36 regions are not the same set for the two).
- **New, needs a ruling: 13 columns may carry up to 2 months of later data.** The panel's ENSO columns (nino12, nino3, nino4, nino34, oni) and the repo's 8 `sst_anom_*` boxes are ERSSTv5. CPC says that, because of a high-frequency filter applied to the ERSSTv5 data, ONI values "may change up to two months after the initial 'real time' value is posted" [S39; same sentence on the v6 page, S6]. A value that changes later because of a filter contains later data. If you count that as content, their lags become 2 months (3 for oni). Until you rule, these 13 are marked "pending".
- **tni is a 5-month running mean** (provider page [S4]). **Its alignment is not stated anywhere I could read.** The data rule out the alignments that would give lag 0 or 1, but they cannot tell "centred" (lag 2) from "one month later" (lag 3) [T4, T4b]. So the YAML files it as the plan's bound form (`align: unknown, max_length: 5`, lag 4) until you sign one of three options.
- **oni is a 3-month running mean, centred** (confirmed on the data [S6, T3, T5]): lag 1 month, or 3 if the ERSSTv5 filter counts as content.
- **The other columns are plain monthly values** (no running mean): lag 0. This rests on the provider pages and, for the 8 repo SST boxes, on the repo code. The data signature test [T8] is decisive only for the 8 atmospheric indices; for the SST and food indices it is only consistent.
- **co2 has one caveat.** NOAA builds its global monthly mean from smoothed station curves (a filter about 40 days wide), so one month's value can carry a few weeks of the next month [S19]. My proposal is a bound reaching 1 month ahead (lag 1), for your signature. The alternative is a plain month (lag 0).
- **Targets:**
  - PM2.5 (ACAG monthly files) covers one calendar month.
  - **Fire (MCD64A1) needs a ruling.** The burn dates lie in the calendar month, but the burned/unburned decision normally uses observations from after the month end [S34 §3.1.2]. Whether that counts as content decides whether fire's history block starts at t-1 or t-2.
  - Defo (Hansen `lossyear`) covers one calendar year ("loss detected primarily in" that year).
  - **NDVI's V11 (MOD13C2) is a weighted average of the 16-day composites that overlap the month.** One month's value can include **up to 15 days of the next month**, and up to 15 of the previous one [S38, T9]. **This includes December:** the last composite of each year runs to 2 or 3 January (NASA CMR granule time ranges [S42]). Under R17, NDVI's history block starts one month further back (t-2 at the nowcast). V11 and V12 used as *drivers* get lag 1 on monthly targets and lag 1 year on annual ones.

**ATTENTION: decisions for the owner** (details under "Open items"):
1. **ERSSTv5 filter (13 columns).** (a) Count it as content: lags 2 for nino12/3/4/34 and the 8 `sst_anom_*` boxes, 3 for oni, and 1 year on defo's annual aggregates. The plan's 3.2 value "oni 1 month" becomes 3. (b) Treat it as a disclosed property of the input analysis, like a base period: lags stay 0 (oni 1). Option (b) needs a new ruling, because Q43 a covers base periods only.
2. **tni:** sign "centred" from the data (lag 2), "centred or one month later" (lag 3), or leave the bound (lag 4).
3. **co2:** sign the 1-month bound (lag 1) or a plain month (lag 0).
4. **Fire's detection window:** (a) sign one calendar month and disclose the margin (history ends at t-1), or (b) add a reach-after fact (history starts at t-2; a new acceptance flag).
5. **PSL footers.** F10's endorsed fix says "Record each index's smoothing from PSL/CPC footers". Reading the 13 PSL `.data` footers (read-only, nothing saved) would settle several unknown base periods. I had already read one footer (`tni.data`, [S22]) before stopping to ask; it is **no longer used as evidence** until you rule.
6. **Vintage.** Do not re-download the indices without re-running this audit (hashes in the YAML).

## How a lag follows from a window (plain words)

Each index value carries a date (its month). "Window" means which months of real-world data went into that value. R8 asks one question: how late is the newest data, measured from the month the value is dated? That lateness is the lag, because the engine must step back that many months before the value is safe to use at the reference month. The reference month is the target month for a nowcast, or the issue month at lead L; the lag number is the same at every lead.

```
data months:         Oct   Nov   Dec   Jan   Feb
plain value, "Dec"               [Dec]                 newest data = Dec  -> on time   -> lag 0
oni, "Dec"                 [ Nov   Dec   Jan ]         newest data = Jan  -> 1 late    -> lag 1
tni (centred), "Dec" [ Oct   Nov   Dec   Jan   Feb ]   newest data = Feb  -> 2 late    -> lag 2
```

Two traps:
- **A later revision is not always "release time".** If a value is revised because newer data *arrived* (a late report), the content did not change month, and R8 ignores it (Q2). If it is revised because a *filter* now sees the following months, the settled value contains those months: that is content time. CPC gives the second reason for the ERSSTv5 indices (ATTENTION 1).
- **Annual targets.** On an annual target (defo), the engine averages a monthly column over the calendar year (aggregate_time, APP_PLAN 1.5). A December value that reaches into January pushes the whole year's value past the year end, and R8 gives lag 1 year. That affects oni, tni, V11 and V12 in any case; co2 if its bound is signed; and the other 12 ERSSTv5 columns under ruling (a). Every other column stays at lag 0 years.

## Table 1: the 34 global columns

"Running mean" describes the provider's own smoothing of the monthly value. "Status" is my **proposed** status (every YAML entry stays `unverified` until you sign): **V** = verified (a provider page or repo code states it, and the panel data agree wherever a test was possible); **A** = assumed (a bound you must sign); **P** = pending one of your rulings. The "R8 lag" column gives the lag on a monthly target / on an annual target made from calendar-year aggregates. All 19 index files were written into `noaa_indices_monthly.parquet` by `presplit_cc/ingest_noaa_indices.py` and broadcast on (year, month) by `presplit_cc/assemble_monthly_panel.py:63-68`. The panel values equal that table in all 264 months [T2].

| # | Column | Provider and exact file read | Running mean (window, alignment) | Date stamp in the file | Anomaly base period | Status | R8 lag monthly / annual | Sources |
|---|---|---|---|---|---|---|---|---|
| 1 | nino12 | NOAA PSL `data/correlation/nina1.anom.data`, "From CPC", CPC Niño 1+2 area-mean anomaly (0-10S, 90-80W) from ERSST | none (monthly area mean, per the provider pages). **ERSSTv5 filter: ruling 1** | PSL format: one row per year, 12 month columns | unknown: 1981-2010 [S7] or 1991-2020 (the list page links CPC's `ersst5.nino.mth.91-20` file [S3]) | P | 0 / 0 under (b); 2 / 1 under (a) | ingest_noaa_indices.py:32; S3; S7; S39 |
| 2 | nino3 | PSL `nina3.anom.data` (CPC, 5N-5S, 150-90W) | none; the data look like the unsmoothed sibling nino34 [T8]. Filter: ruling 1 | PSL | unknown (as nino12) | P | 0 / 0 (b); 2 / 1 (a) | ingest_noaa_indices.py:33; S3; S39; T8 |
| 3 | nino4 | PSL `nina4.anom.data` (CPC, 5N-5S, 160E-150W) | none; as nino3 [T8]. Filter: ruling 1 | PSL | unknown (as nino12) | P | 0 / 0 (b); 2 / 1 (a) | ingest_noaa_indices.py:34; S3; S39; T8 |
| 4 | nino34 | PSL `nina34.anom.data` (CPC, 5N-5S, 170-120W). Tested to be ERSSTv5 up to its base period [T6] | none: it equals an unrolled ERSSTv5 box mean [T6]. Filter: ruling 1 | PSL | unknown (as nino12) | P | 0 / 0 (b); 2 / 1 (a) | ingest_noaa_indices.py:35; S3; S7; S39; T6 |
| 5 | **oni** | PSL `oni.data` (CPC ONI): Niño 3.4 from ERSSTv5 [T5, T6] | **3 months, centred.** The column for month m holds the season centred on m (January = DJF) [T3]. Filter: ruling 1 | PSL | rolling: "centered 30-year base periods updated every 5 years" [S6, S39], confirmed by the 5-year block structure in the data [T5]. PSL's timeseries page says 1971-2000 [S5]; the data contradict that | P (the 3-month centred mean itself: V) | **1 / 1** (b); **3 / 1** (a) | ingest_noaa_indices.py:36; S3; S6; S39; T3; T5 |
| 6 | **tni** | PSL `tni.data`: "standardized Nino 12 minus the Niño 4", from HadISST1.1 (and NOAA OI) [S4] | **5 months** ("with a 5 month running mean applied" [S4]); **alignment not stated.** Data: centred fits best, but one month later cannot be ruled out [T4, T4b] | PSL | standardised "using the 1950-1979 period" [S4] | **A** (filed as `align: unknown, max_length: 5`) | **4 / 1** as filed; 2 / 1 or 3 / 1 if you sign an option | ingest_noaa_indices.py:38; S4; S23; T4; T4b |
| 7 | soi | PSL `soi.data`. Provider unknown: the list page says CPC [S3], the timeseries page says CRU (Ropelewski-Jones) [S8] | none (both provider pages describe monthly values; data signature [T8]) | PSL | unknown | V (window); provider unknown | 0 / 0 | ingest_noaa_indices.py:37; S3; S8; T8 |
| 8 | pdo | PSL `pdo.data`. Variant unknown: the list page says "leading PC of monthly SST anomalies in the North Pacific", 1948-2002 [S3]; the timeseries page says an ensemble of COBE, ERSSTv5 and HadISST1.1 [S9] | none (a monthly EOF value). If the variant uses ERSSTv5, ruling 1 applies here too | PSL | unknown: 1920-2014 [S9] or 1948-2002 [S3] | V (window) | 0 / 0 (unless ruling 1 (a) and the variant uses ERSSTv5) | ingest_noaa_indices.py:39; S3; S9 |
| 9 | amo | PSL `amon.us.data` = "AMO unsmoothed, short (1948 to Jan 2023)", from Kaplan SST [S10] | none. The 121-month smoothed version is `amon.sm.data`, which is not used [S10] | PSL | the index is **detrended over its whole record** [S10], a whole-record dependency to disclose like a base period (Q43 a). No update after Jan 2023: panel NaN Feb-Dec 2023 [T2] | V | 0 / 0 | ingest_noaa_indices.py:40; S10 |
| 10 | tna | PSL `tna.data`: box 55-15W, 5-25N, HadISST1.1 [S11] (the list page says HadISST + NOAA OI [S3]) | none (monthly box-mean anomaly) | PSL | unknown: 1951-2000 [S11] or 1971-2000 [S3] | V | 0 / 0 | ingest_noaa_indices.py:41; S3; S11 |
| 11 | tsa | PSL `tsa.data`: "Anomaly of the average of the monthly SST from Eq-20S and 10E-30W", HadISST1.1 [S12] | none | PSL | unknown: 1951-2000 [S12] or 1971-2000 [S3] | V | 0 / 0 | ingest_noaa_indices.py:42; S3; S12 |
| 12 | iod | PSL `gcos_wgsp/Timeseries/Data/dmi.had.long.data`: DMI = SST anomaly gradient 50-70E/10S-10N minus 90-110E/10S-0, HadISST1.1 [S14] | none (provider page; T7 is too close to decide) | PSL | unknown | V | 0 / 0 | ingest_noaa_indices.py:43; S14 |
| 13 | noi | PSL `noi.data`: Northern Oscillation Index (Schwing et al. 2002), SLP-anomaly difference from NCEP/NCAR reanalysis [S13] | none. The page is silent on smoothing; the data signature shows no running mean [T8] | PSL | unknown | V (data test only) | 0 / 0 | ingest_noaa_indices.py:44; S13; T8 |
| 14 | ao | CPC `daily_ao_index/monthly.ao.index.b50.current.ascii` | none: "monthly mean 1000-hPa height anomalies" projected on the AO pattern [S15] | CPC format: year, month, value | loading pattern and normalisation 1979-2000 [S15] | V | 0 / 0 | ingest_noaa_indices.py:45; S15; T8 |
| 15 | nao | CPC `pna/norm.nao.monthly.b5001.current.ascii` | none: RPCA fit of that month's standardised 500-hPa anomaly map [S16] | CPC | 1950-2000 standardisation [S16] | V | 0 / 0 | ingest_noaa_indices.py:46; S16; T8 |
| 16 | pna | CPC `pna/norm.pna.monthly.b5001.current.ascii` | none (as nao) [S16] | CPC | 1950-2000 [S16] | V | 0 / 0 | ingest_noaa_indices.py:47; S16; T8 |
| 17 | wp | CPC `ftp.cpc.ncep.noaa.gov/wd52dg/data/indices/tele_index.nh`, WP column | none (as nao) [S16]. The 3-month window on that page is used to *estimate the fixed patterns* over 1950-2000; each month's value uses that month only | CPC table | 1950-2000 [S16] | V | 0 / 0 | ingest_noaa_indices.py:48, 57-78; S16; T8 |
| 18 | epo | Same file, EP/NP column | none (as nao) [S16] | CPC table | 1950-2000 [S16] | V | 0 / 0 | ingest_noaa_indices.py:49, 57-78; S16; T8 |
| 19 | sam | CPC `daily_ao_index/aao/monthly.aao.index.b79.current.ascii` (AAO) | none: monthly mean 700-hPa anomalies projected on the AAO pattern [S15] | CPC | 1979-2000 [S15] | V | 0 / 0 | ingest_noaa_indices.py:50; S15; T8 |
| 20-27 | sst_anom_atl3, _iod_west, _iod_east, _subpolar_north_atlantic, _coral_sea, _mediterranean, _global_tropical_mean, _nino34 | Built in the repo: cos-latitude-weighted box mean of each monthly field of PSL `noaa.ersst.v5/sst.mnmean.nc` | none in the repo step (one monthly field per value; the code has no rolling step). The input fields are ERSSTv5: ruling 1 | ERSST monthly time -> (year, month) | **1971-2000**, computed by the ingest | P (the repo step itself: V from code) | 0 / 0 (b); 2 / 1 (a) | ingest_ersst_boxes.py:25-40, 70-91 [S17]; S39; T2; T6 |
| 28 | **co2** | NOAA GML `co2_mm_gl.txt`, column "average" (global marine-surface monthly mean) [T2] | no running mean over months. But each value is built from station curves smoothed with a "~40 days" filter, plus a whole-record polynomial and harmonic fit [S19], so it can carry weeks of the next month | "centered on the middle of each month" [S18]; decimal year in the file | none (absolute ppm) | **A** (proposed: newest content = next month) | **1 / 1** if the bound is signed; 0 / 0 if signed as a plain month | download_drivers.py:29; assemble_human_drivers.py:279-283; S18; S19; local file header |
| 29-34 | food_price_index, food_meat, food_dairy, food_cereals, food_oils, food_sugar | FAO Food Price Index csv (nominal), columns Food Price Index, Meat, Dairy, Cereals, Oils, Sugar | none: "monthly change in international prices" [S20] | "YYYY-MM" | **2014-2016 = 100** (file line 2; [S20]) | V | 0 / 0 | download_drivers.py:30; assemble_human_drivers.py:286-295; S20; T2 |

Notes that apply across the table:
- **Release time vs content time.** FAO's meat index "for the most recent months is derived from a mixture of projected and observed prices" [S20], and co2's last year is "preliminary" (file header). These are revisions as data arrive, so R8 ignores them (Q2); the snapshot is pinned (hashes in the YAML). **The ERSSTv5 revision is different:** CPC attributes it to a filter, so it is a content question (ATTENTION 1). It is also not a v6-only matter: the v5 ONI page gives the same sentence and cites Huang et al. (2017) [S39].
- **What the ERSSTv5 filter is.** CPC names it only as a "high frequency filter". A web-search summary says ERSSTv5 and its predecessors use a 3-month filter to widen coverage. I could not open the ERSSTv5 or v6 papers (the journal returned 403), so that detail is unconfirmed. The 2-month figure in the proposal comes from CPC's own statement.
- **Other filters inside the input analyses are not audited.** HadISST1.1 (tni, tna, tsa, iod): neither the Met Office HadISST page nor the Climate Data Guide page describes a filter across months [S40, S41]. I did not read Rayner et al. (2003), so a filter is not ruled out. The PSL pages also name NOAA OI as an input for tni and tna. Kaplan SST (amo) and the NCEP/NCAR reanalysis (noi and the CPC teleconnection indices) were not traced. The proposal is to disclose these, not lag for them; that is open item 7.
- **epo is missing every December** (22 of 264 months, 8.3%) [T2]. That fits CPC's statement that "eight to nine" of the ten patterns appear in each calendar month [S16]. It is below R30's 25% threshold.
- **Not in the monthly panel.** The desertflow bundle's `tier1_climate_indices.py` read other PSL files (for example `nina1.data`, `amon.us.long.data`, `ao.data`, `aao.data`, `wp.data`, `epo.data`) into `tier1_*_annual` columns. The panel assembler drops every `tier1_` column (assemble_monthly_panel.py:104), so none of them reach a package. If a package ever reads them, they need their own audit.

### Columns that look global but are not

| Column | Why it is not global | Source |
|---|---|---|
| conflict_events, conflict_deaths | UCDP GED events counted **per cell** (`groupby cell_id, year, month`). They are 0 in many regions, which makes them look constant; in 2019 they vary within a region-month in 36 (events) and 32 (deaths) of 133 regions | assemble_human_drivers.py:254-276; T1 |
| eddi_observed | varies within a region-month in 36 of 133 regions in 2019, and differs across regions: per cell | T1 (2019, all regions) |

## Table 2: the tests on the panel values (read-only; scripts in the task's scratchpad)

| Test | What it checks | Result |
|---|---|---|
| T1 | Global scope: 34 columns, all 133 regions, 2019 | no column varies within a region-month; no column differs across regions. `conflict_events`, `conflict_deaths` and `eddi_observed` vary within a region-month in 36, 32 and 36 regions |
| T2 | Provenance: panel values vs the source tables | equal for all 264 months: `noaa_indices_monthly.parquet` (19 columns), `ersst_sst_boxes_monthly.parquet` (8), the GML "average" column (not "trend"), and the FAO csv (6) |
| T3 | oni against rolled nino34 (1, 3, 5 months; backward, centred, forward) | best: 3 centred, correlation 0.9978, rms difference 0.078. 3 backward 0.9686, 3 forward 0.9701. A shift test peaks at 0 months |
| T4 | tni against rolled [standardised nino12 minus standardised nino4], windows 1-9 | best: **5 centred (months t-2..t+2, lag 2): 0.9431.** Runner-up: **the same 5-month window one month later (t-1..t+3, lag 3): 0.9303.** Then 7 centred 0.9358 and 3 centred 0.9297 (bounds of the same family). Rejected: one month earlier (t-3..t+1, lag 1) 0.9041; backward (t-4..t, lag 0) 0.8237; forward (t..t+4, lag 4) 0.8755. The correlation is below 1 because tni is made from HadISST, while nino12 and nino4 come from ERSST |
| T4b | Year-block bootstrap of T4 (22 years, 2,000 resamples, seed fixed from the test's name) | centred minus one-month-later: gap 0.0129, 95% interval [-0.0028, +0.0408]; reversed in 6.2% of resamples; centred wins in 15 of 22 single years. **Not separated.** Centred minus one-month-earlier: 0.0390 [+0.0220, +0.0565], never reversed, 17/22 years. Centred minus backward: 0.1195 [+0.0827, +0.1629], 21/22 years. So the data rule out lag 0 and 1, but not lag 3 |
| T5 | oni minus the centred 3-month mean of nino34 | residual 0.0059 once each 5-year block has its own offset per calendar month, against 0.0453 with one base for all years. So oni is built from the same ERSSTv5 series, on 5-yearly rolling bases |
| T6 | nino34 minus the repo's ERSSTv5 Niño 3.4 box (1971-2000 base) | residual 0.0074 (max 0.023) once each calendar month has its own offset. So the panel's nino34 is ERSSTv5, differing only by its base period, and carries no running mean of its own |
| T7 | iod against rolled (sst_anom_iod_west minus sst_anom_iod_east) | 1 month 0.8513, 3 centred 0.8424, 5 centred 0.8089. **The gap between 1 and 3 months is too small to decide anything**; iod's "none" rests on the provider page |
| T8 | Smoothing signature: how strongly one month-to-month change predicts the next (lag-1 autocorrelation of the first differences), as stored and after a 3-month centred mean | **Decisive only for the 8 atmospheric indices:** stored soi -0.50, noi -0.44, pna -0.41, sam -0.41, epo -0.39, wp -0.39, nao -0.36, ao -0.30. A 3-month mean moves them to +0.19...+0.31, and even pure noise gives about 0 after such a mean, so a stored value of -0.30 or below means no mean was applied. **Sibling comparison for nino3 / nino4:** 0.50 / 0.57, like the unsmoothed nino34 (0.56, see T6) and unlike oni (0.86). **Not decisive for the rest:** a 3-month mean raises every series (oni 0.86 -> 0.91, tni 0.76 -> 0.88), and the stored levels of the SST and food indices (nino12 0.16, tna 0.13, tsa -0.13, pdo -0.03, iod -0.02, amo 0.17, the SST boxes -0.06...0.32, food 0.31...0.60) have no reference to compare with. co2 (0.73) is raised by its seasonal cycle. The test cannot see reach shorter than a month |
| T9 | V11's reach, from the MOD13 16-day calendar. The calendar is taken from NASA CMR granule time ranges [S42]: composites start on day 1, 17, ..., 353, and each covers a full 16 days, so the day-353 composite ends on 3 January (2 January in leap years) | days reached after the month end, non-leap / leap: Jan 1/1, Feb 5/4, Mar 6/5, Apr 8/7, May 9/8, Jun 11/10, Jul 12/11, Aug 13/12, Sep 15/14, Oct 0/15, Nov 2/1, **Dec 3/2**. Days reached before the month start: up to 15 |
| T10 | Fire target pixel totals (n_valid + n_unmapped) per cell and month, all 840 files | **August 2007 in cerrado (15,714 of 39,025 cells) and gran_chaco (8,337 of 20,998 cells) is exactly doubled**: ratio 2.0 in 98% / 91% of those cells, n_burned even in 99.95% of them, region total 1.40 times the neighbouring months. That is the signature of the same STAC item counted twice. burned_frac is unchanged by an exact duplicate; n_valid is not. Smaller excesses elsewhere (for example 459 siberian_taiga cells in every month of 2012) have a different pattern and were not characterised |

## Table 3: the target windows (APP_PLAN 1.3 target facts; R17)

| Target | Product and how the monthly/annual value is made | Content window | Stamp | Reaches into the next step? | R17 consequence | Status | Sources |
|---|---|---|---|---|---|---|---|
| PM2.5 | ACAG V5.GL.06 "HybridPM25" global **monthly** GWR file, one per month: `V5GL06.HybridPM25.Global.YYYYMM-YYYYMM.nc`, mean of the pixels in each cell | one calendar month | the month | no: one file per calendar month | history block ends at t-1 | V for file coverage. Whether the GWR calibration pools monitor data across months: **unknown** (the ACAG page is silent; open item 10) | acag_pm25_ingest.py:1-9, 56-66, 248-252 [S30]; S31 |
| Fire | MCD64A1.061 **monthly** granule, Burn_Date layer. burned_frac = pixels with Burn_Date > 0 / valid land pixels. The granule is named by the "start day-of-year of calendar month in which burns have been mapped" [S34 §3.1.1] | the burn **dates** lie in one calendar month | the month | **the label does, normally.** The First Day / Last Day layers give the period of reliable detection; they lie inside the mapped month only "during periods of persistent cloud cover or frequent data loss" [S34 §3.1.2, p. 10]. QA code 3 is "Apparent burn date at limits of time series". So month m's burned/unburned label uses observations from m+1. The margin is not stated | **ruling 4:** t-1 if you sign one calendar month; t-2 if the detection margin counts as content | P | fire_fetch_target.py:1-13, 114-125, 159-161, 226-228, 339 [S32]; S33; S34; T10 |
| Defo | Hansen GFC-2025-v1.13 `lossyear`: "loss detected primarily in the year"; loss_frac = pixels with lossyear = year - 2000, over year-2000 forest pixels | one calendar year | the year | no. Late-year losses can be labelled the *following* year (a backward slip, harmless for R8/R17). Each GFC release re-derives loss years using later imagery, so the version is pinned | history block ends at t-1 (year) | V (definition). The size of the backward slip is unknown | defo_fetch.py:5-22, 41; defo_ingest.py:1-16 [S35]; S36 |
| NDVI | **MOD13C2.061** "CMG 0.05 Deg Monthly NDVI" (V11), from the granule whose acquisition month matches (y, m). MOD13C2 averages every 16-day composite that overlaps the calendar month, "weighted from the overlap with the month" | the month **plus up to 15 days on each side** (December: 2-3 days into January; January: 1 day after) | the month | **yes: up to 15 days into the next month** [T9] | **history block starts one step back: t-2 at the nowcast, and one extra step at every lead** (R17; 3.3 flag 6 holds) | V: the overlap weighting is documented [S38]; the calendar comes from CMR granule time ranges [S42] | ingest_modis_cmg_local.py:56-60, 143-166 [S37]; assemble_monthly_panel.py:49; S38 (User Guide V6.1 §7.1, §9.1, pp. 19-25); S42; T9 |

More on NDVI's V11 (it matters beyond R17):
- **R8 on the NDVI target is unchanged.** The reference instant (the end of V11's own window) sits at most 15 days into month t+1. Every monthly driver of month t+1 ends after that, so whole-month columns keep the lags in Table 1.
- **V11 and V12 as drivers on other monthly targets get lag 1.** V12 (EVI) is the sibling band in the same MOD13C2 file. On PM2.5 and fire, V11(t) reaches into t+1. PM2.5 already holds these columns out as conditional (pm25_ban.py:80-83), and fire already lags them by 1 (fire_ban.py:63-67), so the computed rule reproduces what both lists do by hand.
- **V11 as an annual aggregate (defo) reaches past its year.** December reaches 2-3 days into January (the day-353 composite, [S42]), so an annual aggregate lags 1 year. Defo already lags V11 by hand (defo_ban.py:130).
- **The CMR record of the monthly granule does not show this reach.** MOD13C2.A2019335 is listed as 2019-12-01 to 2019-12-31 [S42], the nominal month. The reach comes from the 16-day composites it averages.
- **R1's composite-of-year rule needs the same care.** The plan says 8- and 16-day composites "restart every 1 January, so the last one of a year is 5-6 days long". That holds for MOD11A2 (the day-361 granule ends 31 December [S42]) but not for MOD13's 16-day composites, whose last one runs a full 16 days into January. R1 should take each product's year-end behaviour from its facts (open item 9).
- **Pixel reliability rank 4 means "Estimated: From MODIS historic time series"**, that is a climatology fill [S38 Table 18]. MOD13C1 fills from "the average of good data from all previous years CMGs of that composite period", and "this database is regularly updated" [S38 §8.1]. Whether a reprocessed year's fill used later years is unknown. This is lineage, not window (see ingest_modis_cmg_local.py:62-73; Part 390).

## Proposed facts: how to read `index_facts.yaml`

- **It is a proposal, not a store catalog.** It shares this folder with the seeded store catalogs (for example `monthly_panel_v170.yaml`), so **the M1 catalog loader must not glob it.** At M1 its entries are merged by hand: store facts into the one catalog per store, target facts into each package's `catalog.yaml`. Its extra keys (running_mean, evidence, owner_options, notes, window_if_*, and so on) are review aids to drop or map at the merge.
- **Statuses.** Every `fact_status` is `unverified` (APP_PLAN 1.2). `proposed_status` holds my proposal (verified / assumed / pending_owner_ruling), and `reviewed_by` / `date` are empty for you. Copying an entry never carries a "verified" past G-FACTS without your signature.
- **Pending rulings** are listed once under `meta.pending_rulings` (R-A to R-E, matching ATTENTION 1-5). Where a ruling changes a window, the entry gives the window that holds under the "disclose" option and a `window_if_*` key with the other.
- Convention: a (year, month) key is stamped at the **centre of that calendar month**, and `window` is the span of content time around that centre. So a plain monthly mean is `{length: 1, unit: month, align: centred}`, which is exactly its calendar month. oni is `{3, month, centred}`. tni is filed as `{max_length: 5, unit: month, align: unknown}`, the plan's form for a smoothing whose alignment cannot be found.
- V11 needs something the 1.3 window fact cannot say: "the month, plus at most 15 days on each side". The YAML proposes two extra keys, `reach_after_max` and `reach_before_max`, as a **schema proposal**. It also lists two fallbacks that fit the current schema, with their trade-offs (open item 8).
- No lag is written as a fact (G-LAG, G-NOKNOB). The lag each fact implies appears only in comments, for review.

## Open items for the owner

1. **ERSSTv5 filter (R-A; nino12, nino3, nino4, nino34, oni, 8 `sst_anom_*`).** CPC: "ONI values may change up to two months after the initial 'real time' value is posted", because of the high-frequency filter applied to the ERSSTv5 data [S39, S6].
   - (a) Content: reach +2 months. Lags become 2 (nino*, `sst_anom_*`) and 3 (oni) on every monthly package, and 1 year on defo's annual aggregates for all 13. The plan's 3.2 "oni 1 month" becomes 3.
   - (b) A disclosed property of the input analysis, like a base period: lags stay 0 (oni 1). This needs an explicit ruling, because Q43 a covers base periods only.
   - pdo may be affected too if its variant uses ERSSTv5 (unknown).
2. **tni alignment (R-B).** The provider gives only the 5-month length [S4]. The data rule out lag 0 and 1 but cannot separate centred from one month later (T4b: gap 0.0129, 95% interval down to -0.0028, reversed in 6.2% of year-block resamples, centred wins 15 of 22 years). Sign one:
   - "centred" from the data: `{5, month, centred}`, lag 2;
   - "centred or one month later": `{7, month, centred}` as a bound, lag 3;
   - the provider length only (as filed): `{max_length: 5, align: unknown}`, lag 4.
   On defo's annual aggregates every option gives lag 1 year.
3. **co2 bound (R-C).** (a) Sign `window {3, month, centred}` as assumed: lag 1 month, and lag 1 year on defo's annual aggregates. (b) Sign a plain month: lag 0, accepting the reach of about 20 days from GML's smoothing filter. co2 is also a trend-proxy candidate in the Q34 review.
4. **Fire's detection window (R-D).** (a) Sign fire's target window as one calendar month and disclose the detection margin; the history block ends at t-1. (b) Add a reach-after fact (the margin is not stated in the guide); R17 then starts fire's history block at t-2, as for NDVI. That would be a new acceptance flag.
5. **PSL footers (R-E) and the unknown base periods.** F10's endorsed fix (HEADLINE_QUESTIONS_AND_FIXES.md:374) says "Record each index's smoothing from PSL/CPC footers". Authorising the 13 footers (read-only, nothing saved) would settle the unknown base periods: nino12/3/4/34 (1981-2010 or 1991-2020), soi, pdo, tna and tsa (1951-2000 or 1971-2000), noi, iod. Per Q43 a these are only printed, never refused. **Disclosure:** I read one footer (`tni.data`, [S22]) through a web fetch before stopping to ask. Nothing was saved, and it is no longer cited as evidence.
6. **Vintage pin.** Keep the current snapshots (sha256 in the YAML). The file dates suggest downloads on 2026-06-16 and 2026-06-18, but no download date was logged. A re-download would bring ERSSTv6 [S5, S6, S7], so the audit must be redone first.
7. **Other filters inside the input analyses** (HadISST1.1, NOAA OI, Kaplan, NCEP/NCAR reanalysis): disclose, do not lag (proposed), or ask for a separate audit. HadISST's pages describe no filter across months [S40, S41], but Rayner et al. (2003) was not read.
8. **Schema for reach across a step edge** (V11 now; also ERSSTv5 under R-A (a) and fire under R-D (b)).
   - (a) Add `reach_after_max` / `reach_before_max` to the store window fact (proposed). This is exact for R17, and it leaves R8 untouched.
   - (b) Fallback `window {3, month, centred}` for V11: safe for R17 and for V11 as a driver. But as a *target* window it would move R8's reference to the end of t+1, which would let month t+1 drivers through. R8 would then need to use the step end for targets.
   - (c) Fallback `window {61, day, centred}`: close to exact, but it overstates February (17 days of reach where the real figure is at most 5).
9. **R1's composite-of-year rule.** It assumes the last composite of a year is truncated at 31 December. That is true for MOD11A2 but false for MOD13's 16-day composites [S42]. The composite-of-year handling should take each product's year-end reach from its facts.
10. **PM2.5 GWR pooling.** Check van Donkelaar et al. (2021) on whether the monthly calibration pools monitors across months. If it does, the target's window is wider than one month, and R17 would need the same one-step shift as NDVI.
11. **Two borderline statuses to sign or downgrade:** noi ("no running mean" rests on the data signature T8 alone; the provider page is silent), and nino12/nino3/nino4 ("no running mean" rests on the provider pages plus the sibling evidence of nino34, which T6 ties to an unrolled box mean).
12. **Fire target duplicate (T10).** For fire's AUDIT_CHECKLIST and exceptions, which are outside this task's scope: at ingest, keep only STAC items whose id or start date matches (year, month) and de-duplicate by tile (fire_fetch_target.py:114-125 does neither); then re-check August 2007 in cerrado and gran_chaco. It matters wherever n_valid is used, for example as a weight or cap.
13. **M1 import of this file.** Do not glob it. Split it into one catalog per store, move the target facts into each package's `catalog.yaml`, and keep every status `unverified` unless you sign it.
14. **Snapshot of the panel's global columns.** The shared panel (D:/monthly_panel) broadcasts values that were downloaded once. A later panel rebuild (see the panel-rebuild hazard note in memory) must reuse these source tables, or this audit becomes stale.

## Known limits

- The documentation for ERSST-, HadISST- and reanalysis-based products describes the *index* construction. Apart from CPC's ERSSTv5 statement, the temporal filters inside those input analyses were not traced.
- The PSL list page [S3] and the PSL timeseries pages [S4, S5, S7-S14] disagree on several base periods and datasets. Where the data could decide (ONI's rolling bases, ERSSTv5), they decided; elsewhere the fact is "unknown".
- T3, T4 and T7 compare series built from different SST datasets (for T4 and T7, HadISST against ERSST), so their correlations are below 1. For oni the ranking is clear. For tni it separates the lag 0-1 alignments but not lag 2 from lag 3 (T4b). For iod it decides nothing.
- T1 checked all regions for one year (2019), plus seven regions for 2015. T2 covers all 264 months, but for one region (alaska_interior_taiga), which T1 shows equals every region.
- The two provider user guides (MOD13 V6.1 and MCD64 V6.1) were read from the PDFs the web-fetch tool cached, with text extraction. Page numbers are the PDF pages.
- The CMR granule time ranges [S42] are metadata search results, read for 2019-2020 year ends only (MOD13C1 2019 and 2020, MOD13C2 December 2019, MOD11A2 2019). The 16-day calendar is standard for MOD13, so other years are assumed to follow it.
- T10 flags cell-months whose pixel total exceeds 1.3 times the cell's median. Only the August 2007 doubling was characterised.

## Sources

Repo files (read-only):
- [S1] `presplit_cc/ingest_noaa_indices.py:27-51` (URLs), `:57-78` (CPC table columns), `:94-127` (parsers; sentinel filter at `:95`)
- [S2] `presplit_cc/assemble_monthly_panel.py:63-68` (globals broadcast), `:104` (tier1_ dropped), `:49` (V11 source dir)
- [S17] `presplit_cc/ingest_ersst_boxes.py:25-40, 70-91`
- `presplit_cc/download_drivers.py:29-30`; `presplit_cc/assemble_human_drivers.py:254-295`
- [S30] `acag_pm25_ingest.py`
- [S32] `fire_fetch_target.py`
- [S35] `defo_fetch.py`, `defo_ingest.py`
- [S37] `presplit_cc/ingest_modis_cmg_local.py`
- Local file headers: `D:/ndvi_drivers/co2/co2_mm_gl.txt` (File Creation Jun 5 2026) and `D:/ndvi_drivers/prices/fao_food_price_indices.csv` (line 2: "2014-2016=100")

Provider pages (read 2026-09-28):
- [S3] https://psl.noaa.gov/data/climateindices/list/
- [S4] https://psl.noaa.gov/data/timeseries/month/DS/TNI/
- [S5] https://psl.noaa.gov/data/timeseries/month/DS/ONI/
- [S6] https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/ (the high-frequency-filter sentence; it names ERSSTv5 and cites Huang et al. 2025)
- [S7] https://psl.noaa.gov/data/timeseries/month/DS/Nino12_CPC/ and https://psl.noaa.gov/data/timeseries/month/DS/Nino34_CPC/
- [S8] https://psl.noaa.gov/data/timeseries/month/DS/SOI/
- [S9] https://psl.noaa.gov/data/timeseries/month/DS/PDO/
- [S10] https://psl.noaa.gov/data/timeseries/AMO/ (the link list maps `amon.us.data` to "AMO unsmoothed, short")
- [S11] https://psl.noaa.gov/data/timeseries/month/DS/TNA/
- [S12] https://psl.noaa.gov/data/timeseries/month/DS/TSA/
- [S13] https://psl.noaa.gov/data/timeseries/month/DS/NOI/
- [S14] https://psl.noaa.gov/data/timeseries/month/DS/DMI/
- [S15] https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/history/method.shtml
- [S16] https://www.cpc.ncep.noaa.gov/data/teledoc/teleindcalc.shtml
- [S18] https://gml.noaa.gov/ccgg/trends/global.html
- [S19] https://gml.noaa.gov/ccgg/about/global_means.html
- [S20] https://www.fao.org/worldfoodsituation/foodpricesindex/en/
- [S22] https://psl.noaa.gov/data/correlation/tni.data (footer text only; read before stopping to ask; **not used as evidence** pending ruling 5)
- [S23] https://climatedataguide.ucar.edu/climate-data/nino-sst-indices-nino-12-3-34-4-oni-and-tni (Trenberth-Stepaniak recipe: the raw TNI is smoothed with a 5-month running mean; no alignment stated)
- [S31] https://sites.wustl.edu/acag/datasets/surface-pm2-5/
- [S33] https://lpdaac.usgs.gov/products/mcd64a1v061/
- [S34] MCD64 User Guide V6.1, https://lpdaac.usgs.gov/documents/1006/MCD64_User_Guide_V61.pdf (§3.1.1 p. 9, §3.1.2 p. 10)
- [S36] https://storage.googleapis.com/earthenginepartners-hansen/GFC-2025-v1.13/download.html
- [S38] MOD13 User Guide V6.1, https://lpdaac.usgs.gov/documents/621/MOD13_User_Guide_V61.pdf (§7.1 p. 19, §8.1 pp. 22-23, Table 18 and §9.1 p. 25); also https://lpdaac.usgs.gov/products/mod13c2v061/
- [S39] https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v5/ (the ERSSTv5 ONI page: the same filter sentence, citing Huang et al. 2017; base periods "centered 30-year base periods updated every 5 years")
- [S40] https://www.metoffice.gov.uk/hadobs/hadisst/ (fields for the month before last are added early each month; no filter across months described)
- [S41] https://climatedataguide.ucar.edu/climate-data/sst-data-hadisst-v11 (no filter across months described)
- [S42] NASA CMR granule search (metadata only), `https://cmr.earthdata.nasa.gov/search/granules.json?short_name=<product>&version=061&temporal=...`: MOD13C1.A2019353 2019-12-19 to 2020-01-03; MOD13C1.A2020353 2020-12-18 to 2021-01-02; MOD13C1.A2019337 2019-12-03 to 2019-12-18; MOD13C1.A2020001 2020-01-01 to 2020-01-16; MOD13C2.A2019335 2019-12-01 to 2019-12-31; MOD11A2.A2019361 2019-12-27 to 2019-12-31
