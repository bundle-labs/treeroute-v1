# Human rivals for fire (monthly burned fraction): research notes

Researcher: fire. Written 2026-10-21. Read-only research. Nothing was downloaded or installed.

## 0. The rows we must match

- Run: D:/treeroute/runs/fire/headline/20261017_869d1f38 (test years 2019-2022, train end 2018: engine/PREREGISTRATION_DRAFT_fire.md:100-103).
- Rows per lead: 96,000 = 40 groups x 50 scored units x 48 months. Same units and months at leads 0, 6, 12 (test_preds.parquet; ladder/lead_6, ladder/lead_12). 1.8% of rows burned.
- Issue: lead 0 issue = target month; lead 6 issue = time - 6; lead 12 issue = time - 12 (checked in the three test_preds files).
- Fit cuts: lead 0 = 24228 (Dec 2018), lead 6 = 24223 (Jul 2018) (ladder/contract_lead_0.json "cuts"; ladder/lead_6/lead.json "cuts"). Lead 12 has its own cut in ladder/lead_12/lead.json.
- Reference rows already on file: predict-zero, guess-normal, last-5-years normal; at leads 6 and 12 also persistence and damped persistence (ladder/lead_6/test_preds.parquet columns).

**ATTENTION (issue date at lead 0).** The workflow context says "nowcast issue = previous month". For fire that is not what the run did. derived.json R8 gives the ERA5 weather columns nowcast_steps 0 (V01_mean_temp_C, V05_mean_vpd_kPa, era5l_* all 0). So the fire nowcast READS THE TARGET MONTH'S WEATHER. Labels are known only to t-2 (datasets/fire/dataset.yaml header, ruling R-D b). So at lead 0 a rival may read month-M fire WEATHER, but never month-M fire OBSERVATIONS. If the designer defines the nowcast issue as month M-1 instead, every lead-0 statement below shifts by one month (use FWI of M-1).

## 1. Candidates

### 1.1 CEMS GEFF-ERA5 fire danger reanalysis (Canadian FWI from ERA5) -- for lead 0

- What: the Canadian Fire Weather Index system (Van Wagner 1987) run daily on ERA5 weather by ECMWF's GEFF model.
- Standing: the Copernicus EMS fire-danger reanalysis behind EFFIS/GWIS fire-danger climatologies. Vitolo et al. 2020, Sci. Data 7:216; GEFF: Di Giuseppe et al. 2016, J. Appl. Meteor. Climatol. 55:2469. FWI-to-burned-area mapping per region is the literature standard (Bedia et al. 2015, Agric. For. Meteorol.; Abatzoglou et al. 2018, Biogeosciences).
- Exists for our period: yes. 1940 to present, daily, updated daily (https://ewds.climate.copernicus.eu/datasets/cems-fire-historical-v1).
- Format: NetCDF/GRIB, 0.25 deg reanalysis grid, global land. Licence CC-BY. Account: the owner's ECMWF key already works on EWDS (fire_cems.py:58, :106-113; an old file was fetched).
- Request used before: dataset cems-fire-historical-v1, product_type reanalysis, dataset_type consolidated_dataset, system_version 4_1, grid 0.25/0.25 (fire_cems.py:198-204).
- On disk: almost nothing. D:\fire\cems\raw\hist_yakutia_larch_2020-2020.nc (one region, one year, 2.8 MB). It was never scored. Zenodo GEFF-ERA5 stops 2019-06-30 and NASA GFWED was unreachable from this PC (FIRE_EXPERIMENTS.md:125-127).
- Our own hand-rolled indices are NOT the human rival: D:\fire\drivers\danger\*.parquet (40 files, 2002-2022, monthly DC/KBDI/Nesterov/Angstrom/FFWI from monthly means, only the shipped 1,000 cells per region) and D:\fire\fwi_c7, fwi_dl, fwi_smoke (AgERA5 FWI, greece_mainland smoke only). fire_cems.py:12-14 already says GEFF supersedes them.
- Space: each unit's lat/lon from engine/datasets/fire/data/static/part-0.parquet, nearest 0.25 deg land point. Cast lat/lon to float64 BEFORE rounding (the zero-match bug, FIRE_CEMS_REPORT.md:223-227). Coastal NaN -> nearest land point; count them; fail loud above 1%.
- Time: target month M -> monthly mean of daily FWI over the days of M. Parity: same information class as our lag-0 ERA5 columns (derived.json R8). ERA5 does not assimilate burned area.
- Leak risks: none from the target. Do NOT add any fire observation of month M (FIRMS active fire, GFAS, GFED, EFFIS rapid burnt-area): those observe the target; our model is barred from them (labels only to t-2). Use only the consolidated ERA5 stream.
- Work: download about 0.4 GB for FWI only (22,400 grid points over the 40 padded boxes x 7,305 days, at the measured ~2.6 bytes per value: D:\fire\cems\batch_test.log line A, 1.37 MB for 5 years of a 15x19 box). Measured 1,590 s per 5-year request (batch_test.log). Per region and 5-year block = 160 requests = about 70 h serial. Merged continental boxes (9 boxes, FIRE_EXPERIMENTS.md:184-186) x 4 blocks = 36 requests = about 16 h serial, about 5-8 h wall with 2-3 jobs queued. Processing (daily -> unit-month) about 1 h. Fitting minutes. RAM small.

### 1.2 CEMS GEFF-SEAS5 seasonal fire danger forecast -- for lead 6

- What: the same GEFF indices run on the 51-member SEAS5 seasonal forecast, monthly start, 216 days ahead.
- Standing: the operational Copernicus seasonal fire-danger forecast. Di Giuseppe et al. 2024, Sci. Data 11, doi 10.1038/s41597-024-02948-3. That paper finds skill above climatology mostly at 1-2 months, sometimes 6-7 months under ENSO/IOD. So at lead 6 expect it near climatology.
- Exists: yes. 1981 to present. Re-forecasts 1981-2016 with 25 members; real-time 2017 on with 51 members. 1 deg x 1 deg grid (the 2024 paper says ~0.25 deg; the EWDS page and our own fetch both say 1 deg: FIRE_CEMS_REPORT.md:91). Horizon 216 days. Released monthly on the 5th. GRIB/NetCDF. CC-BY (https://ewds.climate.copernicus.eu/datasets/cems-fire-seasonal).
- Covers lead 6: yes. Covers lead 12: NO (216 days).
- On disk: D:\fire\cems\raw\seas_*.nc, 22 files, 11 regions, starts in 2019, 2021, 2022 only, 62 daily leads (lead months 0-2), 51 members, FWI only. D:\fire\cems\cems_seas_monthly.parquet: 1,416,000 rows, 11 regions, target years 2019-2023, lead_m 0-2. NOT usable: no train years (2003-2018) for calibration, no lead-6 days, 29 of 40 regions missing.
- Time (pre-register): target month M, issue = end of month M-6. Use the start of the 1st of month M-5. Its initial state is the issue instant, so data-time parity matches our ERA5 inputs at the issue (both appear about 5 days later). Month M lies at daily leads 150-184 of that start. Stricter variant (start of the 1st of M-6, leads 181-214, still inside 216): pre-register one, not both. I recommend M-5.
- Ensemble: mean of members 0-24 in every year. This keeps train (25-member re-forecasts) and test (51-member forecasts) on the same ensemble size. Disclose: re-forecasts and real-time forecasts start from different analyses.
- Space: nearest 1 deg land box. Every unit in a box gets the same value. Score on the frozen rows (the protocol). Print the box-matched table beside it as a disclosed extra, because the old work showed a 1 deg product cannot rank inside its box (FIRE_CEMS_REPORT.md:86-101, :131-134).
- Leak risks: none from the target. Make sure no start date after the issue is used. Only 216 days, so never offer it at lead 12 (FIRE_CEMS_REPORT.md:247).
- Work: starts needed 2002-08 to 2022-07 = 240 starts; leads 150-184 only (35 days); FWI only; 25 members. About 1.5 GB (measured ~3.9 bytes per value: seas_canadian_taiga_2019.nc 14.7 MB for 12 starts x 62 leads x 51 members). Requests: the old code sent one region-year per request (fire_cems.py:209-214; YEARBATCH 1). Raw-file timestamps show 12-34 min per request. 40 regions x 20 years = 800 requests = 160-450 h serial: too slow. With 9 merged boxes x 20 years = 180 requests = 36-100 h serial, about 15-35 h wall with 3 jobs. If EWDS accepts several years per request, much less. Test this with ONE request first (about 30 min). Processing (members x leads -> unit-month mean) about 2-3 h. Fitting minutes. RAM small; reads per box.

### 1.3 ENSO-lag statistical fire-season model -- optional, leads 6 and 12

- What: a regression of fire-season burned area on SST indices known months ahead.
- Standing: Chen et al. 2011, Science 334:787 (South American fire season from SST, 3-5 months ahead); Chen et al. 2016, Nature Climate Change 6:906 (pan-tropical ENSO fire cascade). It is a published method class, not an operational global product. It must be labelled "our implementation".
- Data: ONI from the panel, already on disk (D:/monthly_panel), lagged by the catalog rule (oni lag per monthly_panel_v170_schema_catalog.yaml:17; owner ruling: oni/tni lagged, not dropped). No download.
- Form (pre-register): y_hat = N x (1 + b_g x ONI at the issue), clipped to [0, 1]. N = the row's guess-normal. One slope b_g per group, fitted on train rows up to the lead's fit cut.
- Leak risks: low; ONI is lagged by the catalog. It uses a subset of our own inputs.
- Work: no download; about 1 h coding, minutes to fit.

### 1.4 Rejected

- Active-fire or burnt-area observations of the target month (FIRMS, GFAS, GFED, EFFIS rapid damage assessment): they observe the target. Our model is barred from them. Not a forecast. Excluded.
- SEAS5 13-month "annual range" runs: GEFF is not run on them and they start only 4 times a year. Not an operational fire product. Excluded at lead 12.
- Qualitative outlooks (US NIFC Predictive Services 1-4 months; AFAC Australian seasonal bushfire outlook): no gridded number; regional only; not 6-12 months. Excluded.
- Our own indices (D:\fire\drivers\danger, AgERA5 FWI): our formulas, not a human product.

## 2. Calibration to burned fraction (train rows only, fixed before any test score)

FWI is a danger score, not a burned fraction. The old run fitted an isotonic link on donor regions (FIRE_CEMS_REPORT.md:73-77). Options for the designer (owner decides):

- C-A (my recommendation, primary): normal-anchored. y_hat = N x R_g(p). p = the row's FWI percentile among the same unit's same-calendar-month values from train years. R_g = an increasing isotonic ratio curve per group, fitted on train rows. Clip to [0, 1]. This is how agencies read FWI (anomaly or ranking against local climate, as EFFIS/GWIS publish). It gives the rival the cell-level fuel information the guess-normal holds, so it is the strongest fair version. For train rows, N is the same normal formula computed leaving that year out.
- C-B (continuity with Part 496): per-group isotonic map from monthly mean FWI to burned fraction, fitted on train rows. Report beside C-A, disclosed as secondary.
- Shared rules: input statistic fixed as the monthly MEAN of daily FWI (fwi_mean won before; FIRE_CEMS_REPORT.md:76; the p90 view did not help, :233-237). Fit rows: the group's 100 bank units, label time at or below the lead's fit cut. Lead-specific fits (lead 0 on ERA5 FWI; lead 6 on SEAS5 FWI at the same lead). No test row touches any fit.

## 3. Old result and why it must be redone

- Old: Parts 496-498 (FIRE_EXPERIMENTS.md:2229-2357; FIRE_CEMS_REPORT.md). GEFF-SEAS5 FWI at lead 0 and 1 month, one region (northern_australia_monsoon), 2021-2022, 125 shipped cells. Fine grid: CEMS MAE 0.0254, anomaly R2 +0.0195, vs predict-zero MAE 0.0192 (FIRE_CEMS_REPORT.md:109-116). Box-matched: CEMS anomaly R2 -0.0890 (:123-129). Flat in lead (:238-241). GEFF-ERA5 was never scored.
- Why redo: (1) old 30/10 hard split, now leave-one-region-out over 40 groups; (2) old test years 2021-22, now 2019-22; (3) old leads 0-1 month, now 0/6/12 months; lead 6 was never fetched; (4) old cells came from a hash-seeded pick that cannot be rebuilt (dataset.yaml header); now stride-picked scored units; (5) the old link was fitted on donor rows of 2019+ (the fetch started in 2019: cems_seas_monthly.parquet years 2019-2023), which are test-window years; the protocol now needs train rows only; (6) the old "ours" was the old architecture (final_rows.parquet), not the frozen headline arm.

## 4. Recommendation per lead

| Lead | Primary human rival | Optional (at most one) |
|---|---|---|
| 0 (nowcast) | CEMS GEFF-ERA5 FWI of the target month, calibration C-A | none needed (C-B printed beside as a disclosed secondary) |
| 6 months | CEMS GEFF-SEAS5 FWI, start 1st of M-5, members 0-24, calibration C-A | ENSO-lag model (1.3) |
| 12 months | **NO legitimate operational human rival exists.** GEFF-SEAS5 stops at 216 days. The reference rows stand in: guess-normal, last-5-years normal, persistence, damped persistence, predict-zero. | ENSO-lag model (1.3), labelled "our implementation of a published method" |

Output rows should match the rival harness row shape (unit, time, lead, issue, pred) so the same scorer and region-level paired contrasts apply. Keep MAE beside predict-zero and corr2, as the headline table does (HEADLINE_MODEL_TABLE.md:26).

## 5. Time estimate (fire only, this PC)

| Step | Download | Wall time | CPU / RAM |
|---|---|---|---|
| Adapt fire_cems.py into a rival exporter (fetch, extract to unit-month, calibrate, write rows) + toy tests | - | 4-6 h agent work | - |
| Smoke: 1 ERA5 + 1 SEAS5 request, to test multi-year requests | ~20 MB | ~0.5-1 h | none |
| Lead 0 GEFF-ERA5 FWI, 2003-2022, 40 regions | ~0.4 GB | 5-16 h (queue) | idle |
| Lead 0 extract + fit + score | - | ~1.5 h | small |
| Lead 6 GEFF-SEAS5 FWI, 240 starts, leads 150-184, 25 members | ~1.5 GB | 15-35 h with 3 jobs (36-100 h serial) | idle |
| Lead 6 extract + fit + score | - | 2-3 h | small |
| ENSO-lag model, leads 6 and 12 | none | ~1 h | small |
| **Total** | **~2 GB** | **about 25-60 h wall, of which only ~5-6 h uses the CPU** | under 4 GB RAM |

The downloads wait on the EWDS queue, not on this PC. They can run while the common rivals use the CPU. Write into a new folder (not D:/treeroute/rivals_build, not a protected root). The licence is already accepted for both datasets (old files exist).

## 6. Open points for the owner

1. Lead-0 issue: confirm that the fire nowcast reads month-M weather (derived.json R8 says yes). If not, use FWI of month M-1.
2. Calibration: C-A (normal-anchored, recommended) or C-B (plain isotonic) as the headline rival.
3. SEAS5 start: 1st of M-5 (recommended, data-time parity) or 1st of M-6 (strict).
4. Whether the optional ENSO-lag model is worth the paper space.
