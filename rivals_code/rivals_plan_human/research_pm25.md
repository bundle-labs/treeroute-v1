# Human rivals (type 2) for PM2.5: research notes

Written 2026-10-21 by the PM2.5 researcher of the human-rival workflow. PLAN ONLY. Nothing was downloaded,
installed, built, run or scored. Disk checks were metadata only.
Engine paths are relative to `C:\Users\<user>\Desktop\data set for reserch paper\engine\`; "root" means
`C:\Users\<user>\Desktop\data set for reserch paper\`.

## 0. Short answer

| Lead | Primary human rival | Optional (at most one) | Plain verdict |
|---|---|---|---|
| 0 (nowcast) | CAMS EAC4 monthly PM2.5 of month t-1 (lagged one month), calibrated on train rows | MERRA-2 surface PM2.5 of month t-1 (already on disk) | A legitimate rival exists, but it is weak: it sees less than our history block, which already holds y(t-1). |
| 6 months | NONE | none recommended | No operational 6-month PM2.5 forecast exists. The reference rows stand in: normal, last-5 normal, persistence and damped persistence. |
| 12 months | NONE | none recommended | Same as 6 months. Damped persistence (3.835) already edges our pinned model (3.840) and the declined answer (4.084). |

- Same-month EAC4 (month t) is NOT a parity rival. It assimilates the target month's MODIS AOD, the same signal ACAG is
  built from. It can be printed as a labelled tier-A "input-advantaged" row, and it never decides (protocol.md HQ4).
- **ATTENTION P1:** the nowcast has no persistence reference row today. The PM2.5 lead-0 ladder table prints only the
  normal, the last-5 normal and predict-zero (ladder_table.csv, lead 0 rows). The prereg prints persistence only at
  leads (PREREGISTRATION_DRAFT_pm25.md:131-133). Persistence of y(t-1) is what a human with the label record does. Add it
  as a reference row (minutes of work, from the slim copy's labels). Old evidence: lead-1 damped persistence had a higher
  anomaly R2 than the old nowcast (+0.087 vs +0.060; PM25_RIVALS_PLAN.md:81, :232).
- **ATTENTION P2:** EAC4 is NOT on disk, and its licence status is unknown. The owner must accept the dataset licence on
  the Atmosphere Data Store (ADS) and give an ADS key (G6, QUESTIONS_ROUND3_HANDOFF.md:517-521). If that does not
  happen, MERRA-2 (on disk) becomes the primary.
- Total PM2.5 human-rival time: about 1.5-3 h end to end. That is about 1-2 h machine time plus 0.5-1.5 h of ADS queue
  and download. Not measured; see section 6.

## 1. Our design, as the rival must meet it

- Run: D:/treeroute/runs/pm25/headline/20261007_74e67609. Test 2020-2023. 127 groups (leave one region out), 1,905
  scored units, 91,440 test rows per lead (test_preds.parquet, checked 2026-10-21).
- Lead 0: issue = the target step (`time - issue = 0` on all rows). Driver features may reach the end of month t. A
  column that is co-measured with the target is floored at a 1-month lag (catalog.yaml:217, burn_frac).
- Labels a row may read: t-1 at lead 0, and t-L at lead L (treeroute/timing/cuts.py:50-58). R17 start offset is 0 on
  PM2.5 (protocol.md, sources).
- Headline (HEADLINE_MODEL_TABLE.md:11-13): MAE 3.588 at lead 0; 3.846 at lead 6; 3.841 at lead 12 (the declined
  answer there is the normal, 4.084). Band 0.0462 (ladder.json).
- Reference rows already saved (ladder_table.csv, common rows, pooled):

| Lead | Normal | Last-5 normal | Persistence | Damped persistence | Ours (pinned arm) |
|---|---|---|---|---|---|
| 0 | 4.032 | 3.972 | not printed (P1) | not printed (P1) | 3.588 |
| 6 | 4.054 | 4.051 | 10.090 | 3.975 | 3.846 |
| 12 | 4.084 | 4.122 | 4.224 | 3.835 | 3.840 |

## 2. Candidates

### C1. CAMS EAC4 global reanalysis, monthly PM2.5 (RECOMMENDED primary at lead 0, lagged to t-1)

- **What:** ECMWF's 4D-Var atmospheric-composition reanalysis. It gives monthly mean surface PM2.5.
- **Standing:** it is the Copernicus reference reanalysis for aerosols. The owner already ruled it the nowcast's domain
  baseline (D4 a; D1 wording "assimilates the same satellite AOD but zero ground monitors";
  QUESTIONS_ROUND3_HANDOFF.md:375-378, :475, :478).
- **Period:** 2003 to 2025, so it covers the train years (2003-2019) and the test years (2020-2023)
  ([ADS EAC4 monthly](https://ads.atmosphere.copernicus.eu/datasets/cams-global-reanalysis-eac4-monthly)).
- **Leads:** it is a reanalysis, not a forecast. It enters at lead 0 only. At leads 6 and 12 it would only be a lagged
  persistence (see section 4).
- **Source:** ADS, dataset `cams-global-reanalysis-eac4-monthly`. Variable "Particulate matter d < 2.5 um (PM2.5)", in
  kg m-3. Grid 0.75 x 0.75 degrees. GRIB, with optional netCDF. Updated twice a year, with a 4-6 month delay. Licence:
  CC-BY, shown on the dataset page. Needs an ECMWF/ADS account, licence acceptance on the dataset page, and an ADS API
  key.
- **Size:** 252 months x 480 x 241 values. About 0.06 GB as GRIB or about 0.12 GB as netCDF (my arithmetic, not
  measured).
- **On disk:** NO. No EAC4 or CAMS file was found on D:. `~/.cdsapirc` exists (its contents were not read). It serves the
  Climate Data Store; ADS needs its own URL and key.
- **Assimilates:** MODIS (Terra and Aqua) AOD and AATSR AOD (to 2012)
  ([EGU26-12278](https://meetingorganizer.copernicus.org/EGU26/EGU26-12278.html)). It uses no ground PM2.5 monitors.
  The page lists AOD components for BC, dust, organic matter, sea salt and sulphate only, so nitrate is probably missing
  (verify before the Part).

### C2. MERRA-2 aerosol reanalysis, surface PM2.5 (OPTIONAL second arm at lead 0, lagged to t-1)

- **What:** NASA GMAO's aerosol reanalysis. PM2.5 is rebuilt as DUST25 + SS25 + BC + 1.4 OC + 1.375 SO4 (Buchard et al.
  2016; pm25_products_map.py:1-6). It has no nitrate, so it runs low where nitrate matters.
- **Standing:** it is widely used as a no-monitor PM2.5 estimate (Buchard et al. 2017 evaluate its surface PM2.5).
- **Assimilates:** bias-corrected MODIS Terra and Aqua AOD, AVHRR over ocean, MISR over bright surfaces, and AERONET
  (Randles et al. 2017, J. Climate). So it is co-measured with the target, like EAC4.
- **Period:** 1980 onward. Covers train and test.
- **On disk: YES.** `D:/pm25_products/merra2/aer_200301.nc` .. `aer_202312.nc`: 252 monthly files, 0.80 GB. Fields
  DUSMASS25, SSSMASS25, BCSMASS, OCSMASS, SO4SMASS, kg m-3, on 361 x 576 cells (0.5 x 0.625 degrees). Fetch log:
  `D:/pm25_products/merra2_fetch.log` (2026-09-26). 2005-08 failed first and was re-fetched (file dated 02:45).
  Streams: MERRA2_401 (a reprocessing) for 2020-09 and 2021-06..09, and MERRA2_400 for the other test months. Disclose
  this. Old mapped copies exist in D:/pm25_rivals/full/cache/merra2_*.npy. They are keyed to the OLD rows and are not
  reusable. D:/pm25_rivals is protected (registry/protected_roots.txt).
- **Licence:** NASA open data. Earthdata login (it already exists, per the fetch).
- **Why only optional:** D4 a names EAC4. MERRA-2 is the cheaper twin (no download), with the same co-measurement
  issue and no nitrate. Promote it to primary only if the EAC4 licence click does not happen.

### C3. Same-month EAC4 / MERRA-2 (tier A reference, never decides)

- This is the real operational practice: use the current month's aerosol analysis. But it observes the target month's
  AOD, so it fails parity rule T2 (protocol.md H2).
- It is printed only as a labelled "input-advantaged" row (HQ4 a). A loss to it measures what that observation is
  worth. It is not an architecture failure (PM25_RIVALS_PLAN.md:18).
- In real time the stand-in would be the CAMS near-real-time analysis. That system changed several times inside
  2020-2023 (PM25_RIVALS_PLAN.md:229; the ADS forecasts page says it is "upgraded roughly once a year"). So use EAC4
  for this row too, and disclose it.

### Rejected or not available (checked)

| Candidate | Why not |
|---|---|
| CAMS global forecasts | They reach only 5 days ([ADS forecasts page](https://ads.atmosphere.copernicus.eu/datasets/cams-global-atmospheric-composition-forecasts)). They cannot reach 6 or 12 months. A monthly mean of day-1 forecasts is a same-month analysis (tier A at best) and has no consistent model (D4 c was not chosen). |
| C3S seasonal forecasts (SEAS5 and others) | They have no aerosol, AOD, dust or PM2.5 variable ([CDS seasonal single levels](https://cds.climate.copernicus.eu/datasets/seasonal-monthly-single-levels)). |
| NASA GEOS-S2S-2 (interactive GOCART aerosols, about 9-month runs) | This is the only seasonal system found with prognostic aerosols. A GMAO poster says its sub-seasonal and seasonal PM2.5 "can be skillful" ([Molod poster](https://gmao.Gsfc.Nasa.Gov/pubs/posters/2019/Molod90.pdf)). But: (1) a 9-month horizon cannot reach lead 12; (2) I could not verify that aerosol or PM2.5 output and a 2003-2019 hindcast archive are public, because the GMAO pages returned HTTP 503 on 2026-10-21; (3) a search summary says version 2 was discontinued in spring 2026 (unverified). It is a research system, not an operational PM2.5 product. Not planned. If the owner wants it, one short verification task comes first (HQ-P3). |
| Statistical seasonal haze/PM2.5 models (for example, winter PM2.5 in China from climate precursors: [ACP 22, 11173, 2022](https://acp.copernicus.org/articles/22/11173/2022/); [arXiv 2605.25436](https://arxiv.org/pdf/2605.25436)) | They are regional (China), research only, and built for different targets. On our global grid they reduce to a regression on lagged climate indices, which the common Ridge rival already covers (ruling Y1). |
| Satellite+monitor PM2.5 maps (ACAG V5/V6, van Donkelaar; ChinaHighPM2.5; Di et al./SEDAC) | ACAG is our target. The others use the same month's AOD and ground monitors. They are maps, not forecasts. Their learning engines belong to the common board (type 1; PM25_RIVALS_PLAN.md:7). |
| Land-use regression, RF, boosting engines | Type 1, on the common board (RIVALS_PLAN_COMMON.md; ruling Y). |

## 3. Alignment and calibration (for C1, C2, C3)

- **Space:** take unit centres (lat, lon) from datasets/pm25/data/static/part-0.parquet (cell_id, region, lat, lon).
  Bilinearly interpolate the product to each centre, then multiply by 1e9 to get ug m-3.
  - EAC4: lon 0-359.25 needs a wrap, and lat runs north to south.
  - MERRA-2: lon -180..179.375, lat ascending (the old code's checks: pm25_products_map.py:31-38).
  - `product_cell` = the product grid box (protocol H15). Many 4 km cells share one 0.75-degree box. Say so.
- **Time (parity, protocol H2 rule T2):** product month m, info_end = end of month m, target_obs_end = m.
  - Lead 0: m = t-1.
  - Lead L: m = t-L, if run at all (section 4).
  - Tier-A row (C3): m = t.
- **Coverage:** lead 0 loses the 2003-01 train rows (EAC4 and the MERRA-2 copy both start in 2003-01; no 2002-12). Test
  rows are fully covered. The rule is fixed from the product alone, before any label (protocol H11).
- **Calibration (protocol H6, train rows only; picked on inner MAE, then locked; HQ5 a gauged global):** one statistic,
  `x__pm25` (the monthly mean). Families F0-F4 x links {identity, log_c} = 9 candidate fits per product.
  - Expect the anomaly forms (F3 lin_anom, F4 iso_anom) to win. The product's own unit x month mean (xbar) removes its
    place-dependent level bias.
  - Old evidence: a pooled 2-parameter log map was very poor (old M1 MAE 9.81; raw product M0 15.14). An anomaly
    MOS with a climatology term was strong (old M2 3.926) (D:/pm25_rivals/full/board.csv).
- **Fit rows:** the export's train rows for lead 0: all bank units up to the cut, c = the run's fit-cut c, and the
  normal as a fixed offset (protocol H4).
  - Tuning fits use rows to the inner/guard cut (2016) and are scored on 2017-2019.
  - The refit uses rows to the fit cut (2019).
- **Possible owner item (HQ-P2):** the old strong arm (M2) used PER-CELL slopes (a per-cell MOS), not a pooled map.
  The protocol's families are pooled. A per-unit MOS would be a method (M kind), not a map. I recommend the protocol
  families only, so one rule holds everywhere. The old per-cell MOS can be a labelled extra if the owner wants
  the closest copy of the old arm.
- **Placebo/control:** the time-shifted product (the same unit and calendar month, product from another year), as the
  old MP arm (pm25_products_map.py:9-13). The guard should decline it.

## 4. Leads 6 and 12: no legitimate human rival

- No operational system issues monthly PM2.5 at 6-12 months. CAMS stops at 5 days, and C3S has no aerosol fields. The
  owner already ruled D4 b for the ladder: "no domain baseline" (QUESTIONS_ROUND3_HANDOFF.md:379, :478).
- What a human would do instead is already printed: the normal, the last-5 normal, persistence and damped persistence
  (ladder_table.csv). They are the reference rows at 6 and 12.
- Lagged product persistence (EAC4 of month t-L, as tier L) is legal but adds nothing. At lead L the target itself is
  readable at t-L, and damped persistence of y(t-L) is the stronger form of the same idea. Not recommended.

## 5. Leak risks

| Risk | Handling |
|---|---|
| EAC4 and MERRA-2 assimilate MODIS AOD of the same month as ACAG. ACAG combines MODIS/MISR/SeaWiFS/VIIRS AOD with GEOS-Chem and calibrates to monitors by GWR ([ACAG datasets](https://sites.wustl.edu/acag/datasets/surface-pm2-5)). | Lag to the T2 step (t-1 at lead 0). The same-month row is tier A only. |
| Fire emissions in both reanalyses come from MODIS fire products, like ACAG's GEOS-Chem burn input (catalog.yaml:217). | Covered by the same lag. |
| EAC4 is published 4-6 months late, so EAC4(t-1) did not exist at a real issue date. Its real-time analogue is the CAMS NRT analysis. | Disclose: it is generous to the rival (a better, homogeneous system). |
| Observing-system changes: AATSR ends in 2012 (EAC4). MERRA-2 MISR/AERONET use may change, and the old plan reported a stop after 2014 (unverified, PM25_RIVALS_PLAN.md:229). MERRA2_401 months fall in the test window. | Disclose. The anomaly xbar uses train years only. |
| Product climatology (xbar) and maps fitted on rows past the cut | xbar and maps use only the fit set's train rows (guard cut for tuning, fit cut for the refit). Assert per row. |
| Reading test y early | Keys only until the lock. One reader of y (protocol H16). |
| Reusing the old caches (old rows, unlagged) | Forbidden. Rebuild from the product files. D:/pm25_rivals is protected. |
| rivals.py / pm25_rivals.py `_clip` caps at 1 ug m-3 | Never import them (protocol H9; rivals.py:145-148). |

## 6. Old project result, and why it must be redone

- The old Board C (D:/pm25_rivals/full/board.csv; rivals.log 2026-09-26 02:48-02:50), MERRA-2 only. It is history only
  (protocol H19):
  - M2, the same-month product + per-cell log MOS: MAE 3.926 vs the old nowref 4.156. Contrast -0.231 [-0.510, +0.049],
    CANNOT TELL, W/T/L 7/3/10.
  - MP, the time-shifted placebo: declined to the normal (4.533).
  - M1, a pooled donor log map: 9.810.
  - M0, the raw product: 15.142.
  - EAC4 was never downloaded.
- Why redo:
  1. The split changed. It was a hard split (20 test regions, 1,997 cells, 95,856 rows); now it is leave one region out
     (127 groups, 1,905 units, 91,440 rows).
  2. The opponent changed. The old nowref (4.156) is replaced by the headline 3.588.
  3. The product was UNLAGGED (month t). That now fails parity and is tier A only.
  4. The MOS, normal and c differed from the engine's.
  5. There were no leads.
  6. The band was 0.0395; now it is 0.0462.

## 7. Work needed on this PC (15.8 GB RAM, HDD; D: 39 GB free on 2026-10-21)

| Step | Who | Time (not measured) |
|---|---|---|
| EAC4: ADS account, accept the licence, ADS key | owner | minutes |
| EAC4 download: one request, pm2p5, monthly means, 2003-01..2023-12, global | owner command | ADS queue minutes to about 1 h; transfer under 5 min; about 0.06-0.12 GB |
| MERRA-2 download | none | 0 (on disk) |
| Adapters: EAC4 reader (GRIB/netCDF) and MERRA-2 reader, bilinear map, index tables for lead 0 (parity, t-1) and tier A (t), one row per export key (about 2.6M train rows plus test rows) | agent code about 1 session; machine about 10-20 min per product | old MERRA-2 map of 2.18M rows took about 2-3 min (cache file times) |
| Slim copy of the pm25 lead-0 export (shared with all human rivals) | machine | about 5-15 min (protocol.md section 5). It must run BEFORE the owner deletes the common export (protocol H-A2). |
| Tune (9 fits) + lock + refit + guard, per product and tier | machine | about 10-30 min each; 4 tables (EAC4 P/A, MERRA-2 P/A) = about 0.7-2 h at the top end; likely under 1 h |
| Nowcast persistence + damped persistence reference rows (P1) | machine | minutes |
| Score, jackknife over 127 groups, join to the one rival table | machine | minutes |
| **Total** | | **about 1-2 h machine + 0.5-1.5 h download wait, so about 1.5-3 h end to end.** Leads 6 and 12 add nothing (no rival). |

- Dependencies:
  - The common PM2.5 export at lead 0 must exist (ruling Z1: P1-P15 parity checks pass).
  - The human tool needs the signed common-harness hash (protocol H-A1).
- Fitting uses well under 4 GB of RAM (pooled 2-parameter or isotonic maps).

## 8. Owner questions for PM2.5

| # | Question | Options | Recommendation |
|---|---|---|---|
| HQ-P1 | Primary lead-0 product | (a) EAC4 primary, MERRA-2 optional; (b) MERRA-2 only (no download); (c) both decide | **(a)**, as ruled in D4 a; fall back to (b) if the ADS click does not happen |
| HQ-P2 | Calibration | (a) protocol families F0-F4, pooled; (b) add the old per-unit MOS as a labelled extra | **(a)** |
| HQ-P3 | GEOS-S2S-2 seasonal aerosols | (a) not planned; (b) one verification task on output and hindcast availability first | **(a)** |
| HQ-P4 | Nowcast persistence reference rows (P1) | (a) add y(t-1) persistence and damped persistence at lead 0, reference only; (b) leave as is | **(a)** |

## Sources

- Local: HEADLINE_MODEL_TABLE.md:11-13; PREREGISTRATION_DRAFT_pm25.md:93-104, :126-133; OWNER_RULINGS_2026-10-06.md:136-156;
  OWNER_RULINGS_2026-09-28.md:84-104; root QUESTIONS_ROUND3_HANDOFF.md:354-379, :475-478, :517-535; root
  PM25_RIVALS_PLAN.md:7-19, :32, :58, :229; root REVIEW_PM25_RIVALS.md; root pm25_products_map.py:1-38;
  pm25_merra2_fetch.py:1-22; treeroute/timing/cuts.py:50-58; datasets/pm25/catalog.yaml:207-220;
  datasets/pm25/dataset.yaml; D:/treeroute/runs/pm25/headline/20261007_74e67609/{derived.json R10/R11, test_preds.parquet,
  ladder/ladder_table.csv, ladder/ladder.json}; D:/pm25_products/merra2 and merra2_fetch.log; D:/pm25_rivals/full/board.csv
  and rivals.log; D:/treeroute/rivals_plan_human/protocol.md.
- Web (read 2026-10-21):
  - [ADS EAC4 monthly](https://ads.atmosphere.copernicus.eu/datasets/cams-global-reanalysis-eac4-monthly)
  - [ADS CAMS forecasts](https://ads.atmosphere.copernicus.eu/datasets/cams-global-atmospheric-composition-forecasts)
  - [CDS seasonal single levels](https://cds.climate.copernicus.eu/datasets/seasonal-monthly-single-levels)
  - [EGU26-12278 (EAC4 AOD, assimilated sensors)](https://meetingorganizer.copernicus.org/EGU26/EGU26-12278.html)
  - MERRA-2 aerosol reanalysis: Randles et al. 2017 and Buchard et al. 2017, J. Climate ([PNNL record](https://www.pnnl.gov/publications/merra-2-aerosol-reanalysis-1980-onward-part-i-system-description-and-data-assimilation))
  - [GMAO GEOS-S2S-2 poster](https://gmao.Gsfc.Nasa.Gov/pubs/posters/2019/Molod90.pdf)
  - Molod et al. 2020, [JGR 10.1029/2019JD031767](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2019JD031767)
  - [ACAG surface PM2.5](https://sites.wustl.edu/acag/datasets/surface-pm2-5)
  - [ACP 22, 11173, 2022](https://acp.copernicus.org/articles/22/11173/2022/)
  - [arXiv 2605.25436](https://arxiv.org/pdf/2605.25436)
