# DEFORESTATION — Scoping Document for Prediction Problem #4

*Synthesised from a ten-angle web sweep (global alert systems, national systems, radar and break-date
algorithms, annual benchmarks, leak audit, drivers, prior art, ingest engineering) with adversarial
verification of every coverage claim, plus a completeness critic — 46 agents, 1,222 tool calls. Access
claims carry a class: **OPEN** (no account, endpoint exercised), **FREE_ACCOUNT** (registration, no
payment), **RESTRICTED** (gated), **UNVERIFIED** (documented, not exercised), **DEAD** (probed,
non-functional). Confidence carries a tag: **FETCHED** (a page was actually retrieved), **INFERRED**,
**UNCONFIRMED**. Probe date 2026-09-06. Where sources disagree the disagreement is stated, not
resolved silently.*

---

## 0. TL;DR — the seven decisions this document forces

1. **There is no monthly deforestation target.** Not "we could not find one" — the gap is structural
   and its cause is identified (§1). The question the user asked is answered NO.
2. **The break in data availability sits exactly on our 2019/2020 train-test boundary.** Sub-annual
   products reaching back before 2016 *stop* at or just after 2019; products covering 2020–2023
   *start* at or just after 2019. That is the Sentinel-2 / Landsat-8 near-real-time era beginning.
   This is the single most important finding in this document.
3. **The one product that spans the boundary — Terra-i — is disqualified by circularity, not by
   dates.** It is a MODIS **NDVI** anomaly detector. Our panel's NDVI and precipitation columns are
   its literal generating inputs (§2).
4. **The viable target is annual: Hansen GFC v1.13 or JRC TMF.** And the Part 425 annual-scope ruling
   **does not apply here** — see §3, this is a different situation, not a repeat.
5. **Deforestation is NOT a rare-event problem.** Measured, not assumed: 4 km cell-years of Hansen
   loss are **45.9% zero**, against wildfire's 98–99%. The wildfire architecture is the wrong import.
6. **The leak audit overrides a written project ruling and bans two columns we currently use.**
   `tree_cover_pct` and `luh2_forest` are hard bans (§4). This is the most portable finding here.
7. **The region set supports it.** 42 of our 133 regions are substantially forested — 25 donor / 17
   test — and the test set contains real active frontiers (§7).

---

## 1. THE MONTHLY QUESTION, ANSWERED

Every product with genuine sub-annual deforestation dating, with its **verified** coverage:

| product | cadence | verified span | domain | why it fails |
|---|---|---|---|---|
| **Terra-i** | 16-day | **2004-01-01 → 2022-12-19** | Latin America | spans the boundary — but NDVI-derived (§2) |
| FORMA 250m | daily `alert_date` | 2012-01-01 → **2019-05-18** | pan-tropical | dies 6.5 months before the test split |
| FORMA 500m | twice-monthly | 2006-01-01 → 2015-06-10 | humid tropics | no test-window coverage |
| **GLanCE30** | annual grid, **day-of-year** `ChgDate` | 2001 → 2019 (Africa → 2021) | global **minus Asia** | 100% of train, **0% of test** |
| Google Global CCDC | break date | 1999-01-01 → 2020-01-01 | global | ends at the split |
| LCMAP SCTIME | break date | 1985 → 2021 | CONUS only | one country |
| **DETER**-Amazonia | daily polygons | **2016-08-02** → present | Brazilian Amazon | 3.4 of 18 train years |
| DETER legacy MODIS | 15-day | 2004-05 → 2017-12 (INFERRED) | Brazilian Amazon | **HTTP 403 gated**; no test window |
| DETER-Cerrado | daily | 2018-05-01 → present | Brazilian Cerrado | 1.7 of 18 train years |
| GLAD-L | daily | pantropical from **2018-10-04** | pan-tropical | ≤3 of 18 train years |
| GLAD-S2 | NRT | 2019 → present | Amazon | zero train coverage |
| RADD | 6–12 day | 2019 (Africa) / 2020 (else) | humid tropics | zero train coverage |
| OPERA DIST-ALERT | daily | **2023-01-01** → present | global | starts in the test window |
| Imazon SAD | monthly | ~2008 → present (UNCONFIRMED) | Brazilian Amazon | unverified; one region |

**Three separate teams built a global break-date product (GLanCE, Google CCDC, LCMAP) and all three
stop in 2019–2021.** None has a successor. The community moved its effort to alerting systems, and
the alerting systems begin in 2019. That convergence is why the gap is structural rather than a
search failure.

**Nothing anywhere has sub-annual deforestation dating for 2002 and 2003.** Four independent
searchers agree. Stop looking.

**Two products were checked specifically for a hidden sub-annual layer, and both are traps:**

- **JRC TMF** — its only day-unit layer, `Duration`, is an *elapsed-days count between the first and
  last disruption observation*, not a calendar date. There is no month or DOY band anywhere in TMF.
  Read from the official TMF Data Users Guide.
- **PRODES** — carries a per-polygon `image_date` (xsd:date) plus `julian_day`, which looks like a
  clearing date. **It is not.** 4,000 real 2015 polygons were fetched: **100% of `image_date` values
  fall in July–October**, because it is the acquisition date of the *annual anniversary image*. A
  fake sub-annual signal, and it must not be used to build a monthly target.

---

## 2. TERRA-I — the one product that spans the boundary, and why it still fails

Terra-i is the near-miss and deserves its own section, because on dates alone it works: **2004-01-01
to 2022-12-19**, 16-day, 250 m, and — decisively — each pixel stores *"1–353: the Julian day when the
pixel was detected as converted"*. That is a genuine within-year detection date, so it aggregates
natively to a monthly converted-area rate per 4 km cell. Coverage is 16 of 18 train years (89%) and 3
of 4 test years (75%).

**It is disqualified on circularity.** From Terra-i's own methodology page, its inputs are **MODIS
MOD13Q1 NDVI (250 m, 16-day)** plus **TRMM/GPM precipitation**, fed to a Bayesian neural-network
anomaly detector. Our panel's NDVI columns and precipitation columns are not correlates of that
target — they are the inputs that generate it. That is strictly worse than anything the NDVI chapter
banned, and a referee would find it immediately.

Four further costs, recorded so the decision is not revisited: Latin America only; 2023 entirely
missing; the licence is non-commercial with redistribution requiring written CIAT permission; and
conversion is terminal (a pixel is flagged once and never re-flagged), so a cell monotonically
consumes its own convertible area and cannot lose forest twice.

*Correction recorded: an earlier agent in this sweep reported Terra-i as DEAD. That was wrong — the
site serves a certificate for `*.terra-iplus.org` and 403s default user-agents, which was misread as
a dead endpoint. It is reachable over plain HTTP with a browser user-agent. Separately,
`terra-iplus.org` is **not** the Terra-i archive; it is a commercial 10 m Sentinel product operating
only in Vietnam, and must not be cited for the 2004–2022 MODIS record.*

---

## 3. THE VIABLE TARGET IS ANNUAL — and Part 425 does not forbid it

| product | span | res | domain | access | notes |
|---|---|---|---|---|---|
| **Hansen GFC v1.13** | **2001–2025** | 1 arc-sec (~30 m) | global | OPEN | `lossyear` 1–25; `treecover2000` baseline |
| **JRC TMF** | **1982–2025** | 30 m | pan-tropical moist | OPEN | separates *deforestation* from *degradation*; ~20 yr of pre-2002 history for antecedent features |
| MapBiomas | 1985–2023 | 30 m | Brazil (+ sister networks) | OPEN | best-in-class but one country |
| PRODES | 2000–present | 30 m | Brazil biomes | OPEN | annual, anniversary-image based |
| ESA CCI LC | 1992–present | 300 m | global | FREE_ACCOUNT | weak as a loss target |
| CGLS-LC100 | 2015–2019 | 100 m | global | UNVERIFIED | ends the year the test window starts |

**ATTENTION — the annual-scope ruling does not transfer, and this distinction matters.** Part 425
excluded annual NDVI because an annual NDVI figure is a *derived average of twelve monthly
predictions* — a quantity the model was never trained to optimise. For forest loss, **annual is the
observation's native resolution.** Nothing is being aggregated; there is no derived quantity. The
model would be trained directly on the target as measured. That is a materially different situation,
and treating Part 425 as a blanket ban on annual targets would be a misreading of our own ruling.

The real cost of annual is **sample size, not legitimacy**: ~22 timesteps per cell instead of 264,
which thins the per-cell local refit that is the architecture's distinguishing component. That is the
honest objection to state, and it should be measured rather than argued.

---

## 4. THE LEAK AUDIT — the most portable finding in this document

### Hard bans (columns currently in our 170-column panel)

**`tree_cover_pct` — the worst column in the panel for this target.** Confirmed from our own repo
(`fire_ban.py:46` annotates it "VCF-family cover fractions", sitting beside `V15_bare_ground_pct` and
`V17_herb_cover_pct` — the MOD44B band triple), so it is **MODIS MOD44B Vegetation Continuous
Fields**. Two independent disqualifications, either sufficient:
1. It is not a proxy for the target, **it is the target** — annual percent tree cover falling in a
   cell *is* forest loss, measured from the same optical signal.
2. **An independent timing leak.** From the LP DAAC MOD44B v061 catalogue: *"The product year begins
   at day-of-year 65"* (≈6 March) and each annual composite draws on the following 12 months. So the
   value labelled 2019 is composited from ~March 2019 to March 2020 — it contains two-plus months of
   the test window. A hard look-ahead at a 2019/2020 split regardless of the leak argument.

**`luh2_forest`, `luh2_secondary` — hard ban, and this overrides a written project ruling.**
`DEPLOYABLE_SPEC.md:300` currently states that `luh2_*` "is a census/historical land-use
reconstruction and not a leak at all". **That ruling was made against an NDVI target and does not
survive a forest-loss target.** Verified from the version we actually use
(`presplit_cc/assemble_human_drivers.py:121` opens `LUH2-GCB2025_states.nc`; line 124 defines
`luh2_forest = primf + secdf`):
- Hurtt et al. 2020 (GMD 13, 5425–5464): *"The spatial patterns of forest transitions … were
  constrained by the Landsat-based gridded forest loss observations from Hansen et al."* — the same
  product proposed as our target.
- Zenodo 15557904 (LUH2-GCB2025): the dataset *"continues to provide improved representation of
  deforestation in Brazil and Indonesia by using the latest versions of MapBiomas remote sensing
  data"* — optical deforestation observations in the two largest tropical deforestation countries.
- Same record: recent years are *"extended … using new input data from FAO and other sources, and
  extends historical trends for years without underlying input data"* — i.e. the 2020–2023 test
  window is partly trend extrapolation, the failure mode already documented in
  `reference_regime_ood_failure`.

**`luh2_cropland` / `luh2_pasture` / `luh2_range` / `luh2_urban` — ban.** Same LUH2 file, plus their
spatial allocation descends from HYDE, which allocates using ESA CCI Land Cover (300 m optical).
*Honest nuance:* HYDE's optical input is a single ~2010 reference map and the year-to-year movement is
FAO national statistics — so the contamination is in the **spatial** pattern (which matters for the
region-blocked axis) rather than the temporal one.

**`modis_landcover_class` / `modis_landcover_annual`** — stays banned (already dropped in Part 312).

### Provenance not resolved — must be settled before any run

`cropland_fraction` and `built_surface_fraction`. The ingester was not found in the repo; they predate
`assemble_human_drivers.py` and `assemble_monthly_panel.py:75-76` merely carries them. Decision rule:
if `cropland_fraction` is HYDE/LUH2-derived, ban as above; if it is a satellite cropland map
(GLAD/Potapov, GFSAD, ESA CCI), **hard-ban** — cropland expansion into forest *is* the target in most
tropical regions, and the GLAD cropland product shares the Landsat metric stack with Hansen GFC.

### Keep

`population_density`, `road_density`, `gdp_pc`, and all climate / drought / soil / topography columns.
Not optical, not target co-products. (WorldPop's dasymetric covariates include land cover and night
lights — a mild second-order dependence, not disqualifying.)

### Timing leaks — five, and the second is the exact twin of the wildfire trap

1. **MOD44B DOY-65 window** — above.
2. **Anything derived from the Hansen `lossyear` raster's own value.** `lossyear` is a *single static
   raster* where the pixel value 1–25 is the year of **first** loss and 0 = never lost; loss is
   one-time and non-reversible. So "years since last loss", "forest age", "has this cell ever been
   cleared", or a naive cumulative sum read off that raster is computed from an object encoding the
   entire 2001–2025 history **including the test window**. A cell reading 0 means "never cleared
   through 2025" — that is the answer. **This is precisely the time-since-last-fire trap.** The only
   safe construction is to binarise per year and truncate the cumulative sum at the last training
   year.
3. **GFC version reprocessing — a look-ahead on the target itself.** From the GFC download page:
   *"The years preceding 2011 have not yet been reprocessed"*, and v1.12 *"involves substantial
   methodological modifications affecting loss detection"*. Each release re-derives a pixel's loss
   year using the full archive including later imagery, so a label for year *t* was assigned with
   knowledge of observations after *t* — biting hardest near the series end, i.e. the test window.
   Mitigation: pin exactly one version, and treat the 2011 algorithm boundary as a documented regime
   break inside the train window.
4. **`built_surface_fraction` (GHS-BUILT-S R2023A) — two-way contamination.** Only five epochs are
   *observed* (1975, 1990, 2000, 2014 Landsat; 2018 Sentinel-2); everything else is interpolated by
   *"rank-optimal spatial allocation using explanatory variables … distance to water, and distance to
   vegetation"*. So training-window trends were fitted using the 2018 observation, the 2020+ layers
   are projections rather than observations, and "distance to vegetation" is an optical covariate.
   Ban, or freeze to a single pre-2014 epoch.
5. **Fire columns are a concurrent measurement, not a predictor.** GLAD's own product (Tyukavina et
   al. 2022) disaggregates Hansen loss into fire-driven vs other, and finds **26–29% of global
   2001–2019 forest loss was fire-driven**. Same-month burned area therefore *measures* a large share
   of the target. Fire columns must be strictly lagged to *t*−1 or earlier, and the evaluation should
   report fire-driven and non-fire loss separately — otherwise the headline reduces to "burned area
   detects burning".

### `treecover2000`: use it as a denominator, never as a feature

It is a co-product of the *same* processing chain and the same supervised model run that emits
`lossyear`, and GFC loss is only defined where there was cover — so the loss layer's entire support is
conditioned on it. Handing it over as a column hands over the target's support set. **But** it is a
single year-2000 epoch fixed before the window opens, so it carries **zero** temporal look-ahead.
Use it as the mask and the denominator (loss area ÷ year-2000 forest area); do not expose it as a
predictor.

**Note the inversion:** the panel today does the opposite of the safe thing — it carries MOD44B
(annual, optical, target-identical, look-ahead across the split) and does *not* carry `treecover2000`
(static, pre-window, safe as an offset). If exactly one forest-baseline layer is wanted, swap them.

**And the old rule must be restated.** "Ban all optical" cannot survive here, because for a
forest-loss target there is no non-optical forest baseline in existence. The rule should become:
*ban any layer that is (a) a co-product of the target's own model run, or (b) ingests reflectance
from inside the prediction window.* `treecover2000`-as-offset trips (a) only weakly and (b) not at
all; MOD44B trips both.

---

## 5. TARGET STATISTICS — measured, and they change the architecture choice

- **Zero-inflation: 45.9% of 4 km cell-years have zero Hansen loss.** Not 98–99%. A 4 km cell is
  non-zero if *any 1 of 27,778* 30 m pixels is flagged. **The wildfire chapter's rare-event
  machinery — the hurdle, the cascade, the EVT head — is the wrong import.** This is a
  well-conditioned continuous regression target, closer to NDVI than to fire.
- **~~Quantisation: 0.0036%~~ — CORRECTED, and it was wrong in a way that matters.** That figure
  divided by the 27,778 pixels in a 4 km *cell*. But the target divides by `forest2000_px`, the
  *forested* pixels only. Measured on the 681,072 held-out test rows: median `forest2000_px` is
  **9,195** (p10 = 477, p01 = 10), so the median step is **0.00011**, 3× coarser than stated — and
  the tail is far worse. **15.0% of test rows have a quantisation step > 0.001**, and **9.6% sit in
  cells where a single 30 m pixel exceeds that cell's entire 2003–2023 maximum `loss_frac`** — for
  those rows the target is effectively **binary {0, one step}**, not continuous.
  This does NOT go back on the risk list as a nuisance; it is a property of the metric that the
  evaluation has to handle. R² and MAE on `loss_frac` reward modelling the denominator's noise floor
  in exactly the cells where the target is coarsest, so results should be reported within
  `forest2000_px` strata, or on a forest-pixel floor, and the sparse-denominator tail declared.

---

## 6. RIVALS — one clean candidate, and a brand-new benchmark

- **Jaffe et al. 2021** (*ERL*, INLA-SPDE Bayesian spatial model) — **the one clean rival.** Code and
  data public under BSD-3, and the paper explicitly states past deforestation was **not** used as a
  predictor. Costs: 25 km grid, annual, Brazilian Amazon only, trained 2015–2019.
- **ForestCast** (Google/WRI, EarthArXiv 31 Oct 2025) — a public TFDS benchmark, GCS bucket listed
  successfully (3,818 shards/year, ~250 MB each). But **2017–2023, Southeast Asia only** — usable as
  an external comparison, not as a training target.
- **Forest Foresight** (WWF) — monthly predictions, operational in 6 countries, but training data
  begins **January 2021** and 9 of its predictors derive from Integrated Alerts that do not exist
  before ~2015. Cannot be backdated.
- **DeepForestcast** (Ball et al. 2022) — annual, 30 m, two ~80,000 km² regions; re-fittable.
- **forestatrisk** — pan-tropical, but forest history is only three snapshots (2000, 2010, 2020).
- **CLUE / Dinamica EGO / GLOBIOM / IMAGE / LandSHIFT** — demand-driven scenario models with 10-year
  steps; cannot be scored as forecasters on a held-out window without also forecasting the exogenous
  demand. Categorically incompatible.

**Most operational deforestation forecasters ingest past forest loss as a predictor.** For a
forecasting setup that is legitimate autoregression rather than a leak — but the project must state
which convention it adopts, and adopt it consistently for itself and its rivals.

---

## 7. REGION SET — measured on our own panel

Forest census over all 133 regions (`tree_cover_pct` ≥ 30 at 2010; artefact
`D:\run89full\forest_census.csv`):

| threshold | regions | donor / test |
|---|---|---|
| majority-forested (≥50% of cells) | 22 | 13 / 9 |
| **substantially forested (≥25%)** | **42** | **25 / 17** |
| some forest (≥10%) | 57 | 38 / 19 |
| effectively treeless (<1%) | 44 | — |

The split falls well. **Donors** hold the major arcs — `amazon_basin_brazil` (0.994),
`congo_basin_drc` (1.000), `borneo_rainforest` (0.968), `bolivia_beni_savanna`, `northern_thailand`.
**Test** holds genuine active frontiers — `gran_chaco` (the Argentina/Paraguay soy frontier),
`new_guinea_papua`, `yucatan_peninsula`, `borneo_peat_fires`, `vietnam_central_highlands`, `pantanal`,
`llanos_venezuela`, `costa_rica`. Transferring Amazon/Congo/Borneo → Chaco/Papua is exactly the
cross-region claim the architecture makes.

*Data flag:* `yucatan_peninsula` has `tree_cover_pct` 52.8 but `luh2_forest` **0.000** — that column
is broken there, which matters independently of the LUH2 ban.

---

## 8. DEAD ENDS — do not repeat these

- `www.terra-i.org` serves a cert for `*.terra-iplus.org` and 403s default user-agents. **Not dead.**
- Global Forest Watch **no longer hosts Terra-i** — all 382 datasets in the GFW Data API were
  enumerated; no entry. Obtain from CIAT directly.
- The UMD GLAD historical archive at `glad.umd.edu/alerts` is **DEAD** — every 2016/2017 per-country
  GeoTIFF 404s over both http and https.
- `radd-alert.wur.nl` refuses connections (ECONNREFUSED).
- `terrabrasilis.dpi.inpe.br/en/download-2/` is 404; the live path is `/en/download-files/`.
- `www.globalforestwatch.org` now 301-redirects to `globalnaturewatch.org`.
- INPE's pre-2016 DETER MODIS archive is **HTTP-403 permission-gated**, contradicting the literature.
- **GLAD Landsat ARD** (16-day composites, 1997→present, 27.8 m, CC-BY, published credentials) is the
  only raw material spanning 2002–2023 sub-annually. Building a target from it means running
  CCDC/BFAST ourselves over 133 regions × 22 years — multi-terabyte, multi-month on a 15.8 GB /
  7200 rpm machine. **Not viable. Flagged so nobody rediscovers it as a "solution".**
- **Constructing a monthly target is circular in every buildable version.** Allocating Hansen's annual
  amount across months by a fire signal fails twice: 26–29% of loss is fire-driven so the majority of
  cells fall back to a flat 1/12 (which *is* the annual average again), and our panel already contains
  the fire columns, so the reported monthly skill would measure the model reconstructing our own
  allocation rule. Allocating by NDVI drop is straight leakage.
- **GFED4/GFED5** carry a monthly deforestation-fire partition (`C_DEFO`/`DM_DEFO`) spanning 2001+ —
  the only monthly, deforestation-labelled, 2002-spanning global product in existence. But it is fire
  *carbon emissions* at 0.25° (~28 km, 7× coarser than our cell), model-partitioned, not a clearing
  rate.

---

## 9. RECOMMENDATION

**Run it, on an annual Hansen GFC v1.13 target, over the 42 forested regions — or drop the problem.
Do not run Terra-i.**

The case for running it: the region geometry is genuinely good (§7), the target is well-conditioned
rather than rare-event (§5), a clean external rival exists (§6), the ingest is open-access with no
credentials, and the societal value is the reason it was chosen.

The case against, stated plainly: it is **annual**, so the per-cell local refit — the architecture's
distinguishing component — gets ~22 timesteps instead of 264; and our own prior
(`reference_greenness_skill_collapse`) says this architecture predicts climate-driven vegetation well
and human-managed land badly. Deforestation is overwhelmingly human-decision-driven. **A negative
result is a live possibility and the chapter should be framed as a boundary test from the start** —
*"this transfer architecture works on climate-driven vegetation and does not work on human-driven
land-use change, and here is where the boundary lies"* — rather than discovering that at the end.

**Before any run, three things must be settled:** the provenance of `cropland_fraction` and
`built_surface_fraction` (§4); which Hansen version to pin (§4, leak 3); and whether past forest loss
is admitted as an autoregressive predictor (§6) — a decision that must then bind us and every rival
identically.
