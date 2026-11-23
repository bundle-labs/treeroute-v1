# Human rivals: deforestation (annual Hansen loss fraction)

Researcher note, 2026-10-21. Read-only research. Nothing was downloaded or installed.

## 0. Short answer

- **Primary human rival, both leads: the Verra VT0007 "UDef-A" benchmark risk map, with the VMD0055 quantity.**
  This is the method carbon finance uses to set REDD+ baselines. It is rebuilt on our own Hansen 30 m tiles,
  which are already on disk (D:/hansen, same version as the target). No Hansen download is needed.
- **Optional (one): the same method in its certified "frozen" form.** Fit on 2010-2019 once and hold it fixed
  for 2020-2023. This is exactly what Verra certified for Peru and Colombia (reference period 2010-2019, valid
  2020-2025). It needs no extra compute.
- **The two leads get the same rival numbers.** On defo, the nowcast and lead 1 both see labels up to t-1
  (APP_PLAN.md:231, R11). The nowcast adds only year-t drivers. VT0007 uses no drivers. So one rival series
  serves both leads. The optional frozen form is the only "longer lead" human view.
- **No legitimate human rival uses year-t information at the nowcast.** The products that do (GLAD/RADD
  alerts, DETER, PRODES) observe the target itself. They are leaks, not rivals (section 3).
- **ATTENTION: two owner decisions before any build** (section 7): (D1) the rival may see the 30 m forest map
  (forest edge), which our model never sees; (D2) admin divisions need a small download (GADM 3.6), or the
  benchmark runs with one division per region.

## 1. Our design, as the rival must match it

- Target: loss_frac = loss_px / forest2000_px per 4 km cell and year; forest = treecover2000 >= 30 and land
  (defo_ingest.py:1-16). Hansen GFC-2025-v1.13 (defo_ingest.py:53).
- Rows: 42 groups x 2,197 scored units x 4 test years = 369,096 rows per lead
  (D:/treeroute/runs/defo/headline/20261017_d71c61f4/test_preds.parquet; ladder/lead_1/test_preds.parquet).
- Lead 0: issue = year t; drivers of year t; labels up to t-1. Lead 1: issue = t-1; labels up to t-1
  (issue column checked in both files; R11 at APP_PLAN.md:231; R17 at APP_PLAN.md:247).
- Fit cut 2019; inner score years 2017-2019; Y0 2004 (derived.json R11; PREREGISTRATION_DRAFT_defo.md:12-14).
- Headline to beat: nowcast MAE 0.00542, guess-normal 0.00841, predict-zero 0.00612, own-link trees-off
  0.00572 (HEADLINE_MODEL_TABLE.md:20-21, 27).

## 2. The primary rival: VT0007 UDef-A benchmark + VMD0055 quantity

**What it is.** Each forest pixel gets a risk class from its distance to the forest edge (30 geometric classes,
cut at the distance holding 99.5% of past loss). Classes are crossed with admin divisions. Each class x
division gets its past loss frequency. The jurisdiction's expected loss is then spread by those frequencies.
(VT0007 v1.0, 21 Feb 2024, sections 5.3.1-5.3.2; https://verra.org/documents/vt0007-unplanned-deforestation-allocation-v1-0)

**Who uses it.** It is Verra's required benchmark for unplanned-deforestation baselines under VM0048 / VMD0055.
Verra and its data providers (CTrees, Clark University) issue official allocated risk maps with it
(https://verra.org/verra-finalizes-allocated-deforestation-risk-maps-for-mato-grosso-and-para/). It descends
from the JNR allocation tools (VT0007 p2). Reference code: UDef-ARP, GPL-3.0, Windows, Python
(https://github.com/ClarkCGA/UDef-ARP). Verra states the quantity rule: the jurisdiction's mean rate over the
previous 10 years, carried forward with no trend (https://verra.org/methodologies-main/technical-background-note-new-redd-methodology/).
VT0007 cites studies where distance to forest edge alone matches richer models (VT0007 text around its Figure 2).

**Exists for our period and leads?** Yes, because we rebuild it. Hansen loss covers 2001-2025. A 10-year
reference period ending at t-1 exists for every issue year from 2011. So it covers the calibration years
(2014-2019) and the test years (2020-2023). Same output at lead 0 and lead 1 (section 0).

**Data, all on disk.**
| Input | Where | Coverage | Size | Licence |
|---|---|---|---|---|
| Hansen GFC v1.13 lossyear, treecover2000, datamask, 30 m (1 arc-sec) | D:/hansen (231 files: 76 lossyear, 77 treecover2000, 77 datamask) | loss 2001-2025; tiles cover all 42 regions | 30 GB | CC BY 4.0 (open, no account) |
| 4 km cell grid and target counts | D:/defo_target/{group}.parquet | 2001-2025 per cell | 49 MB | ours |
| Static cell table (forest2000_px) | D:/defo_features/static/part-0.parquet | static | 3.9 MB | ours |
| Admin divisions | NOT on disk (D:/ndvi_drivers/gdp/DOSE_shapefiles.gpkg holds only 73 non-GADM regions) | - | - | see D2 |

The tiles are the same version as the target (defo_fetch.py:20-24 pins v1.13). So the rival cannot mix
label definitions with the target.

**Alignment in space.** Reuse the exact pixel-to-cell mapping of defo_ingest.py:100-200 (searchsorted on the
region's own cell centres). A parity check comes for free: the rival builder must reproduce loss_px and
forest2000_px of D:/defo_target cell by cell, or it stops.

**Alignment in time (issue year t, both leads).**
- Reference period (HRP) = years t-10 .. t-1. T1 = end of year t-11. T3 = end of year t-1.
- Forest at time T = treecover2000 >= 30 and land, minus pixels with lossyear in 1..(T-2000). Pixels lost at
  or after t stay "forest". This is the "binarise per year, truncate" rule (DEFORESTATION_SCOPE.md:185-191).
- Fit (application stage): distance to non-forest at T1 -> NRT -> 30 classes -> loss frequency per class x
  division over the HRP (VT0007 5.3.1).
- Predict: distance at T3 -> classes -> assign the fitted frequencies -> scale so the group total equals the
  group's mean annual loss over the HRP (the VMD0055 quantity; VT0007 5.3.2.3). Cap each pixel at 1.
- Cell prediction = sum of expected loss pixels in the cell / forest2000_px. That is the target's scale.
- Jurisdiction = our group (region). Quantity = wall-to-wall Hansen counts, not Verra's sample-based activity
  data (disclose).
- Optional frozen form: one fit with HRP 2010-2019, distance at end 2019, held for 2020-2023.

**Calibration (train rows only).** VT0007 is already on the target scale; its quantity step is its own
calibration. Recommended pre-registration: run the rolling rival for issue years 2014-2019 too. Fit one
increasing isotonic map (squared error) from rival prediction to loss_frac on those rows, pooled over the 42
groups, labels <= 2019 only. Clip to the legal range. The calibrated form decides; the raw form is printed
beside (same pattern as common-rivals Q11 c, OWNER_RULINGS_2026-10-06.md section Y3). Chosen before any test
score.

**Leak risks and how each is closed.**
1. lossyear is one static raster holding 2001-2025. Only "lossyear in 1..t-1-2000" is ever read as past loss.
   Nothing reads "never lost" (value 0) as information.
2. GFC reprocessing look-ahead: Hansen re-derives loss years with later imagery; pre-2011 years are not
   reprocessed (DEFORESTATION_SCOPE.md:193-199). It hits the target and our own history block the same way.
   Disclose; no fix.
3. Do not use the gain layer. Its window runs past the cut.
4. Release dates: Hansen year t-1 is released around spring of year t (INFERRED). At lead 1 (issue end of
   t-1) it would not yet be public. The engine ignores release dates by ruling (R8, APP_PLAN.md:228, Q2). The
   rival follows the same rule. Parity holds; disclose.
5. treecover2000 (the forest map) is a co-product of the target run. It is banned as a feature for our model
   (DEFORESTATION_SCOPE.md:213-221). For the rival it is issue-date information and the method's core input.
   It favours the rival, never us. Owner decision D1.
6. Admin boundaries carry a content date (ruling N2, PREREGISTRATION_DRAFT_defo.md:343). GADM 3.6 (2018) is
   before the 2019 cut. geoBoundaries "current" is after it. See D2.
7. Edges: distance near a region's edge needs pixels outside it. Read a margin of at least the NRT from the
   whole 10-degree granules on disk. Where a margin falls in a granule we did not fetch, count and disclose.
8. Pixel shape: 1 arc-sec pixels are not square in metres (15 m wide at 60 N). VT0007 asks for an equal-area
   map. Use per-tile anisotropic spacing in the distance transform instead of reprojecting 9.3 Gpx. Disclose.

**Old project result, and why it must be redone.**
- defo_papers.py:52-57, 221-222 ran "udef_a" on 17 hard-split test regions (log D:/defo_papers/_papers.log,
  2026-09-07): R2c +0.0923, MAE 0.008768, against softgate +0.1645 / 0.008098 (we won 16/17).
  vm0015 (flat historical rate) gave +0.1005 / 0.008798.
- It is not VT0007. It swapped distance to forest edge for travel_time and road_density, because rule (d) bans
  forest2000-derived features (defo_papers.py:43-46, 191; log "ADAPTATIONS"). It froze all test years at 2019.
  It used up to 4,000 cells per region, a different panel row set, a threshold of 0.01 and no pre-registered
  calibration. Its reference arm (softgate) is not the shipped model.
- rivals.py:409-433 "jnr_rate" is a project NNLS blend of history columns, not a published method. CLAIMS_LEDGER.md
  :594-597 says call it "JNR-style". Old score: corr2 0.01872 vs ours 0.02943; per-region verdict CANNOT TELL
  (-0.00697, Part 528), and that paired test used a test-chosen arm (CLAIMS_LEDGER.md:597, 734).
- So: new rows (LORO, 42 groups, 92,274 units), new leads, the canonical edge distance, a pre-registered
  calibration, and paired contrasts against the shipped arm. Nothing old carries over.

**Work on this PC (15.8 GB RAM, D: HDD, 39 GB free on D:).**
- Download: Hansen 0 h (on disk). Admin divisions: GADM 3.6 level 2 for about 35 countries, roughly 0.5-1.5 GB,
  about 0.5-1 h (estimate; zero if D2 picks "one division per region").
- Build: one script, about 1 agent day plus owner review. Reuse the strip reader of defo_ingest.py. Test on a toy
  raster. Check parity with D:/defo_target.
- Processing: two read passes of 9.3 Gpx (the full ingest took 9.8 min, D:/defo_target/_ingest.log). About 20
  distance maps (T1 = end 2003..2012, T3 = end 2013..2022; the frozen form reuses 2009 and 2019). A 16 Mpx
  scipy distance transform measured 1.15 s here (about 72 ns per pixel). 20 maps x 9.3 Gpx with margins is
  about 4.5 h on one core; binning and counting about 1-2 h more. With 6 worker processes: about 1.5-2.5 h
  wall. RAM under 2 GB per worker with 4000 x 4000 tiles. Outputs are small count tables (well under 1 GB).
- Fitting: frequency tables and the isotonic map: minutes. Scoring on the saved rows: minutes.
- **Total: about 2-4 h machine time, plus up to 1 h download, plus 1 build day.**

## 3. Candidates rejected (and why)

| Candidate | Why not a rival for our rows |
|---|---|
| Verra's own published VMD0055 risk maps (https://verra.org/methodologies-main/vmd0055-jurisdictional-data-table/) | Only a few jurisdictions. Usable windows: Mato Grosso/Para (HRP 2009-2018, valid 2019-2024), Peru and Colombia (HRP 2010-2019, valid 2020-2025). That touches at most pantanal (Mato Grosso part) and llanos_venezuela (Colombian part). Amazonas uses HRP 2013-2022, which covers our test window: leak. No train-year version, so no train-row calibration. Built on CTrees data, not Hansen. Access: free request form; compliant version via Verra Project Hub with a fee. At most an external case study. |
| FCPF / UNFCCC FREL, VM0015 historical rate | A flat regional rate. Our guess-normal (per-cell mean) is already stronger and stands in as the reference row. |
| GLAD-L / GLAD-S2 / RADD alerts, DETER, PRODES, Terra-i | They observe year-t loss: the target itself (DEFORESTATION_SCOPE.md:40-55). Most also start in 2016-2020, so no train years. |
| Forest Foresight (WWF) | Training data start January 2021; cannot be backdated (DEFORESTATION_SCOPE.md:262-264). |
| ForestCast (Google/WRI 2025) | Southeast Asia only, 2017-2023; a benchmark dataset, not an operational product (DEFORESTATION_SCOPE.md:259-261). |
| forestatrisk / deforisk iCAR (Vieilledent 2021; FAO/CIRAD) | A VT0007 "alternative model", not the benchmark. Needs roads, towns and rivers from current OpenStreetMap (content date after the cut) and protected areas. The old project only ran an RF stand-in. Heavier and less standard. |
| Jaffe et al. 2021 INLA-SPDE | Brazilian Amazon only, 25 km grid (DEFORESTATION_SCOPE.md:256-258). |
| CLUE, Dinamica EGO, GLOBIOM | 10-year scenario models driven by demand; not scorable as forecasts (DEFORESTATION_SCOPE.md:267-269). |

## 4. Per lead

| Lead | Primary human rival | Optional | Note |
|---|---|---|---|
| Nowcast (issue t, labels to t-1) | VT0007 benchmark + VMD0055 10-year quantity, rolling HRP t-10..t-1, isotonic-calibrated (raw beside) | VT0007 frozen at 2019 (HRP 2010-2019), as certified | No human method uses year-t drivers legitimately. |
| 1 year (issue t-1, labels to t-1) | The same series as the nowcast | The same frozen series | Identical by construction; say so in the table. |

## 5. Scoring

Same rows (unit, year) as test_preds.parquet at each lead. Same metrics: MAE headline; anomaly R2, corr2, hit
rate beside; guess-normal and predict-zero beside; per forest2000_px stratum (PREREGISTRATION_DRAFT_defo.md:152-156).
Region-level paired contrast against the adopted arm, jackknife over the 42 groups.

## 6. Disclosures to carry

- The rival sees the 30 m forest map (edge distance); our model does not (if D1 = allow).
- Quantity from wall-to-wall Hansen, not sample-based activity data.
- Annual rolling use of a 6-year baseline method is our adaptation; the frozen form is the certified practice.
- Anisotropic pixel spacing instead of an equal-area reprojection.
- GFC pre-2011 regime break and reprocessing look-ahead (shared with the target).

## 7. Owner decisions (list, not chosen)

- **D1 forest map.** (a) Allow the canonical edge distance from treecover2000 + past loss (recommended:
  it is the published method; the asymmetry only helps the rival). (b) Parity form: distance to past-loss
  pixels only (not canonical).
- **D2 divisions.** (a) GADM 3.6 level 2 (content 2018, before the cut; free for academic use, no
  redistribution, https://gadm.org/license.html) (recommended). (b) geoBoundaries gbOpen ADM2 (CC BY 4.0,
  but current vintage after the cut). (c) One division per region (no download; weaker, not canonical).
- **D3 non-forest for distance.** Land-only non-forest (water excluded) (recommended) or all non-forest
  including water.
- **D4 decision form.** Isotonic-calibrated decides, raw beside (recommended), or raw decides.
