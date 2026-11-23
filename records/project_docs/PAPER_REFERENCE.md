# PAPER REFERENCE — Desertflow

**A complete working reference for writing the manuscript.** Every number, every caveat, every
provenance pointer in one place. Organised so a section of the paper can be written by reading one
section of this.

| | |
|---|---|
| Compiled | 2026-08-21 |
| Experiment log | `EXPERIMENT_SUMMARY.md`, **402 numbered Parts** |
| Claim summary | `FINDINGS.md` |
| Architecture spec | `ARCHITECTURE.md` |
| Sandbox spec | `presplit_cc/SANDBOX.md` |
| Entry point | `presplit_cc/desertflow.py` |

**Conventions used throughout.**

- Every quantitative claim cites the Part that established it.
- **Noise floor:** ±0.01 anomaly-R² at full scale. Deltas below this carry no sign information.
- **Reconstruction floor:** 5×10⁻⁴ NDVI for anything rebuilt by the sandbox.
- **Metric bundle:** MAE, hit-rate (±0.02), anomaly-R² reported *together*, never anomaly-R² alone.
- `riseR²` is **diagnostic only** and never carries a claim.
- Retractions are kept in place, not deleted. Where a Part was later narrowed or voided, both are cited.

---

# PART I — WHAT THE PAPER IS

## 1.1  One-sentence statement

A tree-routing architecture that estimates and forecasts monthly NDVI at 4 km in drylands **without
observing NDVI as an input** and **without training on the region being predicted**, evaluated
retrospectively across 44 regions and prospectively on a year that did not exist when the model was
built.

## 1.2  What is claimable, in order of strength

| # | claim | evidence | strength |
|---|---|---|---|
| 1 | Driver-conditioned NDVI estimation transfers zero-shot across regions | 38/44 beat both baselines, p = 9.4×10⁻⁷ | **strong** |
| 2 | The architecture retains skill at a 12-month lead against persistence | 39/44, p = 1.4×10⁻⁷ | **strong** |
| 3 | Forecast skill survives prospectively in managed-water systems | 4/4 over climatology; 3/4 *higher* out-of-sample than held-out | **moderate** (n=4) |
| 4 | Uncertainty intervals are conditionally calibrated | difficulty corr +0.332 in 44/44; spread 0.287→0.124 | **moderate** |
| 5 | The model reads coherent climate *states*, not individual drivers | 0.0052 alone vs 0.2111 with correlates | **moderate** (2 regions) |
| 6 | The architecture has forecasting but ≈ zero prescriptive value | achievable change 5% of MAE with real levers | **moderate** (2 regions) |

## 1.3  What is NOT claimable

- **Anything about desertification itself.** No trend analysis, no attribution, no degradation
  extent. The experiments measured model behaviour. [§11.11]
- **Negative-NDVI prediction as a capability.** Climatology calls the sign better. [Part 388]
- **Uniform forecast superiority.** 15/44 regions are worse than doing nothing. [Part 393]
- **Prospective persistence advantage.** 1/4 only. [Part 394]
- **Cell-specific intervention as a general property.** Thar yes, gobi no. [Part 402]
- **Causal interpretation of anything.** The model was never causally identified. [Part 399]

## 1.4  The paper's distinctive contribution

The literature sweep (43-agent workflow, 36 studies) found **zero** fair yardsticks: the
memory-free × zero-shot × multi-year-forward cell is empty. Closest peers are Kraft 2019
(0.25–0.40 per-pixel arid) and McPhillips 2026 (MSSS ≈ +0.36).

Two things nobody in that set had:

1. **A genuinely prospective test** — forecast issued from a panel ending 2023, scored against
   observations ingested afterwards, with a product-consistency check that refuses to run on a
   mismatch.
2. **Interventional model interrogation** — a gate-verified sandbox that asks the deployed model what
   it does when an input actually changes, rather than attributing importance post hoc.

---

# PART II — DATA

## 2.1  Inventory

| | |
|---|---|
| Source panel | `D:\monthly_panel` — **2,926 parquet files, 44 GB**, read-only |
| Spatial unit | 4 km cell |
| Temporal unit | calendar month, **2002–2023 = 264 months** per cell |
| Regions | **133** total: **89 donors** / **44 targets** |
| Target variable | `V11_mean_ndvi` |
| Feature count | **612** after the leak ban |
| Non-constant features (thar) | 569 of 612 |
| Historical features | **297 of 569** (`_lag*`, `_roll*`, `_wytd`) |

## 2.2  Target provenance  [Part 390]

`presplit_cc/ingest_modis_cmg_local.py`, product entry `ndvi`:

| | |
|---|---|
| Product | **MOD13C2 v061** — CMG 0.05° (~5.6 km) **monthly** |
| SDS | `"CMG 0.05 Deg Monthly NDVI"` |
| Column | `V11_mean_ndvi` |
| Scale | ×1e-4 |
| Valid gate | **raw [−2000, 10000]**, applied *before* scaling |
| Fill | −3000, excluded by the gate |
| Observed range in the panel | **exactly [−0.2000, 0.9988]** |

**Three consequences.**

1. The gate explains the empirically clean range: zero rows below the floor, zero mass at −0.30.
2. **No QA is ever read.** Pixel Reliability and VI Quality are never opened, so rank-4
   "Estimated — from MODIS historic time series" (climatology backfill) enters unfiltered. [§8.5]
3. It explains the **Part 385 retraction**: the panel is MOD13C2 (0.05°), while the first prospective
   verification fetched MOD13A3 (1 km) via AppEEARS. Different product, grid and compositing —
   the 2022–2023 overlap correlated 0.913 with mean |diff| 0.0285, the same size as the "error" being
   reported. [Parts 385, 390, 392]

## 2.3  Driver families

| family | representative columns |
|---|---|
| ERA5-Land energy | `era5l_sshf`, `era5l_slhf`, `era5l_ssr`, `era5l_str`, `era5l_pev` |
| ERA5-Land water | `era5l_sro`, `era5l_ssro`, `era5l_stl1`, `era5l_d2m` |
| Precipitation | `V02_total_precip_mm`, `V03_max_daily_precip_mm`, `precip_intensity_mm`, `wet_day_count`, `V04_precip_seasonality` |
| Temperature | `V01_mean_temp_C`, `diurnal_temp_range_C`, `gdd5_degC_days`, `heatwave_days_gt35C` |
| Humidity / demand | `sph_kgkg`, `tc_vapor_pressure`, `V05_mean_vpd_kPa`, `vpd_max_daily`, `rmin_pct`, `V07_total_ref_ET_mm` |
| Drought indices | `spi_01m…24m`, `spei_01m…24m`, `scpdsi`, `eddi`, `aridity_index_p_pet` |
| Soil water | `V30_soil_moisture_pct`, `soil_water_tc_mm`, `esacci_sm`, `api_soilmoist` |
| Storage | `grace_lwe`, `deeprec_twsa` |
| Balance | `wbal_mm`, `climate_water_deficit_mm`, `aet_total_mm` |
| Radiation / cloud | `solar_radiation_Wm2`, `cloud_frequency_pct` |
| Static | `soil_organic_carbon_gkg`, `soil_ph`, terrain |
| Teleconnections | `nino12`, `nino34`, `iod`, `amo`, `pdo`, `tna`, `soi`, `oni`, `tni` |
| Socioeconomic | `population_density`, `hdi`, `food_*`, `fert_n`, `luh2_*`, `aglw_cattle` |

Most carry `_lag1/2/3/6/12`, `_roll3/6/12`, `_wytd` derivations.

## 2.4  The leak ban  [§1.1 of ARCHITECTURE.md]

**Eleven banned columns:** `V12_mean_evi`, `V13_mean_lst_C`, `nighttime_lst_C`, `V14_mean_albedo`,
`V15_bare_ground_pct`, `V17_herb_cover_pct`, `gpp_kgC_m2`, `modis_landcover_annual`,
`phenology_sos_doy`, `shrub_cover_pct_global`, `tree_cover_pct`. Plus 3 default drops and 5 livestock
columns inside `LA.build`.

**Enforcement.** Installed on `keep_cols` in four modules; re-probed on 3–4 regions per run;
feature-list SHA compared across probes; derivation check ensures no lag/roll of a banned parent
survives. Printed before any fitting.

**Why.** These are optical measurements of vegetation state, not drivers. EVI is a sibling band of
NDVI in the same MOD13 file. In unrestricted versions of this model, LST/albedo/GPP dominate SHAP —
and the project established they are **vegetation-state proxies**, with the real driver being water.

**Known wart.** Two ban versions exist historically (9-column and 11-column). Mainline resolves to
**11** and asserts it at runtime; ~25 older exploratory scripts carry the stale 9-list and would
silently admit EVI. No reported result comes from those.

## 2.5  Negative NDVI  [Parts 387, 388]

| | |
|---|---|
| Count | **686,854 of 10,279,423 test rows = 6.68%** |
| Regions affected | 29 of 44 |
| Most affected | `pamir_plateau` 48.8%, `alaska_north_slope` 46.5% (100% of its cells) |
| Distribution | p1 −0.1701, p50 −0.0331, p99 −0.0011 |
| Rows below −0.2 | **0** |
| Mass at −0.30 (mis-scaled fill) | **0** |
| Mass at exactly −0.20 | 147 (0.021%) |

**Physics.** MOD13 does not compute VIs over ocean/inland water, so land negatives are **snow/ice**,
retained as valid data (Pixel Reliability rank 2). The monthly value is a weighted average of 16-day
CV-MVC maxima, so a negative month means the **greenest** observation that month was still negative.

**Model behaviour on them.** Negatives are *easier*: MAE 0.0290 vs 0.0347 overall. But against
climatology the advantage collapses — 1.8% vs 20.8% elsewhere, hit-rate goes the wrong way
(60.3% vs 66.3%), and on the deepest band (−0.20 to −0.10) the model is **worse** than climatology
(+5.7% MAE, MSSS −0.042). Observed spread on negative rows is 0.0377 against 0.2746 overall — deep
snow is a near-constant regime climatology stores exactly.

**Sign prediction — do not claim it.**

| | precision | recall | accuracy | F1 |
|---|---|---|---|---|
| model | 0.909 | 0.815 | 0.9822 | 0.860 |
| **climatology** | **0.937** | 0.802 | **0.9832** | **0.864** |

With a 6.68% base rate, "never predict negative" scores **93.32%** accuracy — above the 90.9%
precision. Report MCC 0.852 / F1 0.860 if reporting at all. And Umirbekov et al. 2024 (GMD, GEMS)
already publish zero-shot snow-from-climate at 92% / 87% class-balanced **in the western Pamir**.

## 2.6  Robustness to excluding negatives

Excluding all negative rows without recalibration: macro MSSS **+0.329 → +0.333**. The headline does
not depend on them. [Part 387]

---

# PART III — ARCHITECTURE (K_AD_climcol)

## 3.1  Overview in one paragraph

Eighty-nine donor regions are each fitted with 500 **tree pairs** — a base predictor plus a corrector
fitted to the base's out-of-bag residual — giving a 44,500-column basis learned entirely off-target.
For each target **cell**, a ridge regression over those 44,500 columns plus a 10-column context block
is solved on that cell's calibration rows (≤2019) and applied to 2020–2023. A learned **gate** derived
from donor surge-probability columns amplifies the corrector by 1–3×; **GLS row weights** from donor
spread downweight rows the donors disagree on; an **unpenalised climatology basis** is projected out
first so the model can fall back on the seasonal mean at no ridge cost; and 89 **routed EVT columns**
are appended for tail behaviour.

## 3.2  The donor bank

| parameter | value | note |
|---|---|---|
| donor regions | 89 | never include the target |
| tree pairs per donor | **500** | `--ntrees 500` |
| total columns | **44,500** | 89 × 500 |
| `--maxfeatures` | 15 | drawn **per node**; constants consume budget |
| `--maxsamples` | 50,000 | |
| `--corrdepth` | 12 | corrector depth |
| backend | Intel oneDAL (sklearn-intelex) | ~11× faster; **not** bit-identical to stock sklearn |
| store size | 2.47 GB RAM | 58.3 KB per pair |
| flatten time | 45–175 s | 89 blocks over 89 parts at `--tblk 500` |

**Why pairs, not trees.** The corrector is fitted to the base's **out-of-bag** residual. In-bag
residual fitting learns nothing — an early structural finding. The corrector only carries signal
because it sees rows the base did not.

**Shared divisor vector (`colscale`).** A tree trained on Siberia must score a Thar row, so one
divisor vector is calibrated over **133 regions × 1,200 cells** and applied everywhere
(`31 columns rescaled, max 1024×`).

> **Cache-key hazard.** `get_colscale` keys on `md5(sorted(region_list))`. A 132-region list silently
> builds a divisor the forests were never fitted under. This occurred once and was caught. The
> 133-region list is now pinned in every entry point via `all133_regions.txt` with a count assertion.

## 3.3  Helper columns

Three per-donor blocks are projected onto the target panel, each `(n_rows × 89)`:

| block | content | used for |
|---|---|---|
| `G` | donor **gate** columns — surge probability for this row | the learned blend → `η` |
| `S` | donor **spread** columns — predictive dispersion | GLS row weights `W` |
| `EV` | donor **EVT** columns — extreme-value tail estimates | `evz`, appended to context |

Cost: 89 forests scored over every panel row. Gobi (2,113,848 rows) took **10m46s**, batched into two
passes over the panel rather than 89 (`--helpbuf 2.0 GB`).

## 3.4  The ladder — exact derivations

```python
wsz    = NR / NR.sum()                        # donor size weights
gsize  = G @ wsz                              # size-weighted gate
gavg   = rowmean(G)                           # averaged gate

# LEARNED GATE BLEND: regress the SURGE INDICATOR on the 89 donor gate columns
A      = [1 | G]  on calibration rows ci
wgb    = solve(AᵀA + 1e-6·I, Aᵀ·tj[ci])
gblend = clip(wgb[0] + G @ wgb[1:], 0, 1)

η      = 1 + 2·gblend                         # corrector amplification, range [1, 3]
```

`tj = (y − y_prev) > JUMP` — the **surge indicator**. So the gate is a linear probe learning how to
combine 89 donors' surge opinions into one number, and that number **amplifies the corrector up to
3×**. When the gate believes a surge is underway, the corrector counts triple.

> **This mechanism explains a later result.** The gate is trained to detect *surges from
> contemporaneous drivers*. At a 12-month lead the drivers are a year stale, so the gate fires on
> noise — which is why the blend is the **worst** arm on thar in forecast mode (§7.3).

```python
sw  = S @ wsz
sig = clip(sw, p5, p95)                       # winsorised
W   = (1/sig²) / mean(1/sig²)                 # GLS ROW WEIGHTS  ← "D"
```

Inverse-variance weighting: rows the donors agree on count more. Winsorising at the 5th/95th
percentile stops one low-spread row dominating.

```python
θ   = 2π(month − 0.5)/12
ctx = [clim, sin θ, cos θ, sin 2θ, cos 2θ, X[:, top5]]      # exactly 10 columns
ctx = (ctx − ctx[ci].mean) / (ctx[ci].std + 1e-9)           # standardised on CALIBRATION rows
evz = standardise(EV over calibration rows)                 # 89 routed EVT columns
```

`top5` = the five highest mean-importance features across donors. `ctx` standardised on calibration
rows only — rebuilding it on a different row set is a known gate-failure cause.

## 3.5  Combination and standardisation

```
T  = P + η·C
T̃  = (T − μ) / σ          # μ,σ from ONE streamed pass over all calibration rows × 44,500 cols
```

| property | consequence |
|---|---|
| **Region-level statistics** | `μ`,`σ` computed over *every* calibration row. Cannot be rebuilt from a subset — a per-cell analysis still needs a whole-region pass. |
| **float16 round-trip** | Store holds float32→float16, reads back float64. Deliberate: reproduces a materialised bank. Skipping it would be a *different, slightly better* model. Sets the **5×10⁻⁴ reconstruction floor**. |

Standardisation cost: 20–52 minutes. Gobi's pass was **51m47s** over 1,729,512 rows × 44,500 columns.

## 3.6  The solve

```
λ_T = α · trace(TᵀT)/p          α = 2.0        (--alpha)
λ_A = A_CTX · trace(VᵀV)/q      A_CTX = 0.25
M   = [ V/√λ_A | T̃/√λ_T ]
```

Ridge scales set by each block's own trace, so blocks of wildly different width are penalised
comparably.

**Dual form.** `U` = unpenalised 2-column basis (constant, centred climatology) is projected out
first — **this is the "K"**. Then:

```
Q     = solve(UᵀU + 1e-10·I, Uᵀ)
M_p   = M − U(QM),   y_p = y − U(Qy)
α     = solve(M_p M_pᵀ + I, y_p)      # n_cal × n_cal — a few hundred, never 44,500²
coef  = M_pᵀ α
p     = U·b + M_all·coef
```

**Name unpacked:**

| letter | meaning |
|---|---|
| **K** | unpenalised climatology basis, projected out before the ridge |
| **A** | context block — climatology + 4 harmonics + 5 top features |
| **D** | GLS row weights `W = 1/σ²` from donor spread |
| **climcol** | climatology carried explicitly, not absorbed into trees |
| **+ EVT** | 89 routed EVT columns appended to context |

## 3.7  The ladder as an ablation

| arm | `η` | extra | meaning |
|---|---|---|---|
| `omit` | `None` (T = P + C) | — | plain routed ensemble |
| `size` | `1 + 2·gsize` | — | size-weighted gate |
| `avg` | `1 + 2·gavg` | — | averaged gate |
| `blend` | `1 + 2·gblend` | — | learned gate blend |
| **`evt`** | `1 + 2·gblend` | `evz` | **the full architecture** |

`--armset evt` computes only the last; `--armset ladder` all five at ~1.8× cost, because
`omit`/`size`/`avg` each need their own standardisation while `blend` and `evt` share one.

## 3.8  Bankless routing

Materialising the design matrix needs **84–350 GB** per region (the log prints what was avoided).
Instead the Gram is accumulated per cell-block and the bank is never allocated. Accumulation order is
preserved so the Gram is **bitwise equal** to a materialised bank's — verified by `--selfcheck`, not
assumed. Routing runs ~1 s/cell at `--cellbatch 32`.

## 3.9  Forecast mode

`--shift N` — **panel-level**: each row keeps its target `(cell, year, month)` but takes **features
from N months earlier**. Rows without a source that far back are dropped (~95.5% survive at N=12).
`--future K` appends rows beyond the panel with a climatology placeholder target, discarded at
scoring.

**Trees frozen; only the router refits.** The 12-month forecast is the same ensemble asked a harder
question.

> **Cache-name hazard, encountered and fixed.** The shifted panel's cache name originally omitted the
> shift, so `--future 1` silently reused the `--future 0` panel and produced byte-identical metrics.
> The suffix `.sh<N>f<K>` was added. [Part ~383]

---

# PART IV — EVALUATION PROTOCOL

## 4.1  Splits

| | |
|---|---|
| Calibration | ≤ **2019** |
| Test | **2020–2023** |
| Prospective | **2024** (ingested after the forecast was issued) |
| Donor exposure to target | **none** |
| Router exposure to target | calibration rows only |

## 4.2  Cell sampling — a real limitation

| run | `--cellfrac` | `--cellmin` | `--cellpick` |
|---|---|---|---|
| nowcast | 0.5 | 2000 | **first** |
| forecast (44 regions) | 0.25 | 2000 | **first** |
| prospective 2024 | 0.5 | 2000 | **first** |

`--cellpick first` selects a **contiguous corner block**, not a random sample. The script default is
`random`; `first` was used. The panel stem encodes it: `cf0.5m2000f` → `CELLPICK[0] = 'f'`.

**Evidence that it matters:** `mesopotamia`'s retrospective MAE is **worse** than climatology at
cellfrac 0.5 (0.0264 vs 0.0257) and **−9.5%** at 0.25. The subset changes the sign of the conclusion.
This needs a caption, not a footnote. [Part 394]

## 4.3  The two baselines

**Climatology** — per-(cell, month) mean over ≤2019. MSSS is defined against it, so it scores exactly 0.

**Persistence** — same cell and month one year earlier, **observed**.

**They are near-orthogonal:** `corr(MSSS, skill-vs-persistence) = −0.147` across 44 forecast regions.
Extremes make the mechanism plain:

| region | MSSS | skill vs persistence |
|---|---|---|
| `nile_valley_delta` | **+0.5227** (best) | **−1.0186** (worst) |
| `drakensberg_lesotho` | −0.2691 | −0.7582 |
| `alaska_interior_taiga` | +0.0248 (≈0) | **+0.5570** (best) |

Managed-water systems are hard for climatology (irrigation decouples cells from their seasonal mean)
and easy for persistence (last year's managed state repeats). Cold high-variance systems are the
reverse. **Neither baseline alone tells the story.** [Part 389]

**Persistence is the fairer test** because it sees the target's own NDVI history — which the model is
denied by the leak ban.

## 4.4  Metrics

| metric | definition | note |
|---|---|---|
| MAE | mean \|y − p\| | fairest single number |
| hit-rate | fraction with \|y − p\| ≤ **0.02** | |
| anomaly-R² | `r2_score(y − clim, p − clim)` | climatology scores `floor = −(mean/sd)²` |
| **MSSS** | `(aR² − floor)/(1 − floor)` | Nash–Sutcliffe / Murphy (1988); climatology = **0** |
| riseR² | anomaly-R² on surge rows | **DIAGNOSTIC ONLY** — never a claim |

**Why MSSS looks small next to MAE and R².** Pooled NDVI R² is ~77% climatology floor. MSSS strips
that floor out and reports only the skill *above* seasonality, so a large R² and a small MSSS are
routine and not contradictory.

## 4.5  Significance and noise

- Sign tests are two-sided binomial across the 44 regions.
- **Noise floor ±0.01 anomaly-R²** at full scale.
- **Smoke deltas lie.** Three arms reversed between 400 and 4,973 cells, all seed-stable with CIs
  excluding zero at smoke scale. Any delta under ~0.01 at reduced scale carries **no sign
  information**.

---

# PART V — RESULTS, PER REGION

## 5.1  Nowcast — per region, all 44

Test window 2020–2023. `MAE` = model, `clim` = per-(cell,month) mean over ≤2019, `pers` = same
cell and month one year earlier, observed. `skill/p` = 1 − SSE_model/SSE_persist.

| # | region | n rows | MSSS | MAE | clim | pers | vs clim | vs pers | skill/p |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `drakensberg_lesotho` | 130,608 | +0.7298 | 0.0239 | 0.0468 | 0.0387 | -48.9% | -38.2% | +0.6542 |
| 2 | `madagascar_spiny_thicket` | 122,400 | +0.7137 | 0.0285 | 0.0549 | 0.0615 | -48.2% | -53.7% | +0.7924 |
| 3 | `madagascar_western_dry` | 157,632 | +0.6400 | 0.0265 | 0.0446 | 0.0482 | -40.7% | -45.1% | +0.7124 |
| 4 | `indian_acacia_babool` | 243,696 | +0.5840 | 0.0385 | 0.0698 | 0.0579 | -44.9% | -33.6% | +0.5242 |
| 5 | `new_zealand_north_island` | 104,353 | +0.5504 | 0.0227 | 0.0316 | 0.0389 | -28.2% | -41.6% | +0.6612 |
| 6 | `thar_desert` | 119,328 | +0.5499 | 0.0277 | 0.0426 | 0.0440 | -35.1% | -37.1% | +0.6151 |
| 7 | `nile_valley_delta` | 194,880 | +0.5118 | 0.0152 | 0.0222 | 0.0122 | -31.4% | +24.5% | -0.3856 |
| 8 | `mexican_altiplano` | 331,152 | +0.5100 | 0.0239 | 0.0345 | 0.0395 | -30.8% | -39.4% | +0.6417 |
| 9 | `hulunbuir_grassland` | 420,720 | +0.5092 | 0.0416 | 0.0613 | 0.0675 | -32.2% | -38.4% | +0.6224 |
| 10 | `hungarian_puszta` | 224,544 | +0.5042 | 0.0429 | 0.0624 | 0.0815 | -31.2% | -47.4% | +0.7206 |
| 11 | `karoo` | 263,328 | +0.4849 | 0.0187 | 0.0265 | 0.0355 | -29.5% | -47.4% | +0.7276 |
| 12 | `japan_central_honshu` | 202,844 | +0.4832 | 0.0294 | 0.0408 | 0.0393 | -28.0% | -25.3% | +0.5898 |
| 13 | `east_african_savanna` | 376,320 | +0.4511 | 0.0488 | 0.0698 | 0.0988 | -30.1% | -50.6% | +0.7264 |
| 14 | `uruguay` | 315,504 | +0.4265 | 0.0399 | 0.0518 | 0.0573 | -23.0% | -30.4% | +0.5541 |
| 15 | `gobi_desert` | 384,336 | +0.4122 | 0.0076 | 0.0096 | 0.0128 | -21.4% | -40.9% | +0.7220 |
| 16 | `greece_mainland` | 143,661 | +0.4102 | 0.0280 | 0.0382 | 0.0405 | -26.6% | -30.8% | +0.6150 |
| 17 | `central_india_dry_forest` | 247,008 | +0.3931 | 0.0483 | 0.0678 | 0.0605 | -28.8% | -20.3% | +0.3055 |
| 18 | `western_europe_temperate` | 450,672 | +0.3839 | 0.0353 | 0.0470 | 0.0584 | -24.9% | -39.6% | +0.6193 |
| 19 | `mediterranean_andalusia` | 161,904 | +0.3833 | 0.0251 | 0.0324 | 0.0370 | -22.7% | -32.3% | +0.5493 |
| 20 | `iberian_wildfire` | 144,384 | +0.3830 | 0.0345 | 0.0465 | 0.0503 | -25.8% | -31.4% | +0.4828 |
| 21 | `okavango_delta` | 83,328 | +0.3696 | 0.0336 | 0.0429 | 0.0565 | -21.6% | -40.4% | +0.6681 |
| 22 | `mopane_woodland` | 231,168 | +0.3625 | 0.0298 | 0.0389 | 0.0493 | -23.2% | -39.5% | +0.6107 |
| 23 | `mesopotamia` | 204,000 | +0.3582 | 0.0251 | 0.0320 | 0.0317 | -21.6% | -20.8% | +0.3684 |
| 24 | `vietnam_central_highlands` | 162,048 | +0.3561 | 0.0268 | 0.0324 | 0.0334 | -17.4% | -19.8% | +0.4087 |
| 25 | `alaska_interior_taiga` | 640,640 | +0.3455 | 0.0478 | 0.0561 | 0.0683 | -14.8% | -30.0% | +0.6838 |
| 26 | `borneo_peat_fires` | 116,256 | +0.3368 | 0.0266 | 0.0333 | 0.0287 | -20.1% | -7.0% | +0.2155 |
| 27 | `pearl_river_delta` | 95,818 | +0.3225 | 0.0375 | 0.0493 | 0.0411 | -24.0% | -8.7% | +0.2762 |
| 28 | `brittany_france` | 103,541 | +0.3107 | 0.0301 | 0.0350 | 0.0434 | -13.9% | -30.5% | +0.6091 |
| 29 | `uk_midlands` | 178,800 | +0.2818 | 0.0332 | 0.0402 | 0.0549 | -17.2% | -39.5% | +0.6301 |
| 30 | `pamir_plateau` | 146,976 | +0.2699 | 0.0147 | 0.0167 | 0.0215 | -12.2% | -31.7% | +0.6264 |
| 31 | `scandinavian_taiga` | 804,700 | +0.2399 | 0.0519 | 0.0558 | 0.0709 | -7.0% | -26.8% | +0.6082 |
| 32 | `atacama_desert` | 124,416 | +0.2382 | 0.0049 | 0.0057 | 0.0060 | -14.3% | -18.1% | +0.4941 |
| 33 | `anatolian_plateau` | 361,248 | +0.2311 | 0.0358 | 0.0413 | 0.0440 | -13.2% | -18.5% | +0.4421 |
| 34 | `yucatan_peninsula` | 129,639 | +0.1765 | 0.0284 | 0.0311 | 0.0387 | -8.6% | -26.5% | +0.5065 |
| 35 | `sundarbans` | 95,589 | +0.1718 | 0.0490 | 0.0563 | 0.0583 | -12.9% | -15.9% | +0.3282 |
| 36 | `tuva_steppe` | 235,826 | +0.1586 | 0.0415 | 0.0478 | 0.0593 | -13.1% | -30.0% | +0.5130 |
| 37 | `namib_desert` | 46,519 | +0.0489 | 0.0035 | 0.0038 | 0.0035 | -7.1% | +1.8% | +0.2650 |
| 38 | `tierra_del_fuego` | 133,691 | +0.0331 | 0.0446 | 0.0468 | 0.0569 | -4.8% | -21.7% | +0.4220 |
| 39 | `tasmania_western` | 95,975 | +0.0145 | 0.0267 | 0.0272 | 0.0334 | -1.6% | -20.0% | +0.3359 |
| 40 | `borneo_rainforest` | 187,711 | +0.0062 | 0.0270 | 0.0282 | 0.0300 | -4.1% | -10.0% | +0.2722 |
| 41 | `alaska_north_slope` | 708,082 | +0.0016 | 0.0398 | 0.0384 | 0.0467 | +3.4% | -14.9% | +0.4898 |
| 42 | `costa_rica` | 95,857 | -0.0474 | 0.0209 | 0.0206 | 0.0248 | +1.1% | -16.0% | +0.3283 |
| 43 | `tongass_alaska` | 99,494 | -0.0565 | 0.0681 | 0.0631 | 0.0802 | +7.8% | -15.1% | +0.4550 |
| 44 | `llanos_venezuela` | 455,616 | -0.0685 | 0.0333 | 0.0316 | 0.0383 | +5.3% | -13.1% | +0.3570 |

**Aggregates.** macro MAE model 0.0315 | clim 0.0404 | pers 0.0454. Beats clim **40/44** (p = 1.71e-08), beats persistence **42/44** (p = 1.13e-10), beats **both 38/44** (p = 9.43e-07). Macro MSSS +0.3290, median +0.3603.

## 5.2  Forecast (12-month lead) — per region, all 44

| # | region | n rows | MSSS | MAE | clim | pers | vs clim | vs pers | skill/p | corr(model,pers) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `nile_valley_delta` | 97,440 | +0.5227 | 0.0129 | 0.0186 | 0.0092 | -30.7% | +40.0% | -1.0186 | 0.991 |
| 2 | `borneo_peat_fires` | 96,000 | +0.4011 | 0.0253 | 0.0339 | 0.0279 | -25.5% | -9.4% | +0.2407 | 0.721 |
| 3 | `pearl_river_delta` | 95,763 | +0.3298 | 0.0360 | 0.0483 | 0.0410 | -25.4% | -12.2% | +0.3064 | 0.962 |
| 4 | `indian_acacia_babool` | 121,824 | +0.2618 | 0.0473 | 0.0608 | 0.0555 | -22.1% | -14.7% | +0.3001 | 0.936 |
| 5 | `madagascar_western_dry` | 95,712 | +0.2396 | 0.0421 | 0.0479 | 0.0534 | -12.2% | -21.3% | +0.4390 | 0.935 |
| 6 | `mesopotamia` | 102,000 | +0.2208 | 0.0255 | 0.0282 | 0.0278 | -9.5% | -8.4% | +0.1902 | 0.920 |
| 7 | `greece_mainland` | 95,719 | +0.1878 | 0.0309 | 0.0356 | 0.0397 | -13.2% | -22.2% | +0.5067 | 0.907 |
| 8 | `vietnam_central_highlands` | 96,000 | +0.1834 | 0.0271 | 0.0296 | 0.0323 | -8.4% | -16.0% | +0.3479 | 0.938 |
| 9 | `japan_central_honshu` | 101,282 | +0.1546 | 0.0372 | 0.0428 | 0.0419 | -13.2% | -11.2% | +0.3679 | 0.953 |
| 10 | `sundarbans` | 95,490 | +0.1474 | 0.0500 | 0.0557 | 0.0582 | -10.3% | -14.1% | +0.3177 | 0.909 |
| 11 | `hungarian_puszta` | 112,272 | +0.1374 | 0.0470 | 0.0515 | 0.0618 | -8.7% | -23.9% | +0.4228 | 0.859 |
| 12 | `central_india_dry_forest` | 123,504 | +0.1319 | 0.0635 | 0.0687 | 0.0606 | -7.5% | +4.9% | -0.0003 | 0.911 |
| 13 | `madagascar_spiny_thicket` | 96,000 | +0.1312 | 0.0521 | 0.0567 | 0.0646 | -8.2% | -19.4% | +0.3914 | 0.819 |
| 14 | `hulunbuir_grassland` | 210,336 | +0.1228 | 0.0574 | 0.0620 | 0.0648 | -7.4% | -11.4% | +0.2635 | 0.929 |
| 15 | `okavango_delta` | 83,328 | +0.0772 | 0.0404 | 0.0422 | 0.0565 | -4.2% | -28.4% | +0.5289 | 0.827 |
| 16 | `new_zealand_north_island` | 95,513 | +0.0715 | 0.0309 | 0.0315 | 0.0390 | -1.9% | -20.8% | +0.3102 | 0.890 |
| 17 | `thar_desert` | 96,000 | +0.0712 | 0.0389 | 0.0404 | 0.0444 | -3.8% | -12.4% | +0.2573 | 0.809 |
| 18 | `namib_desert` | 46,501 | +0.0668 | 0.0036 | 0.0038 | 0.0035 | -4.8% | +4.5% | +0.2842 | 0.896 |
| 19 | `atacama_desert` | 96,000 | +0.0628 | 0.0055 | 0.0058 | 0.0063 | -5.4% | -12.9% | +0.4240 | 0.958 |
| 20 | `mopane_woodland` | 115,584 | +0.0589 | 0.0376 | 0.0392 | 0.0525 | -4.0% | -28.4% | +0.4758 | 0.917 |
| 21 | `anatolian_plateau` | 180,624 | +0.0347 | 0.0402 | 0.0408 | 0.0456 | -1.4% | -11.8% | +0.3721 | 0.939 |
| 22 | `uk_midlands` | 96,000 | +0.0327 | 0.0387 | 0.0393 | 0.0550 | -1.6% | -29.7% | +0.5191 | 0.817 |
| 23 | `mediterranean_andalusia` | 96,000 | +0.0290 | 0.0292 | 0.0307 | 0.0338 | -5.0% | -13.7% | +0.2762 | 0.921 |
| 24 | `alaska_interior_taiga` | 320,384 | +0.0248 | 0.0558 | 0.0553 | 0.0689 | +0.9% | -19.0% | +0.5570 | 0.950 |
| 25 | `tasmania_western` | 95,246 | +0.0087 | 0.0274 | 0.0273 | 0.0334 | +0.3% | -18.0% | +0.3227 | 0.884 |
| 26 | `western_europe_temperate` | 225,312 | +0.0072 | 0.0489 | 0.0490 | 0.0597 | -0.2% | -18.2% | +0.3793 | 0.885 |
| 27 | `tierra_del_fuego` | 95,681 | +0.0006 | 0.0468 | 0.0470 | 0.0567 | -0.4% | -17.5% | +0.4029 | 0.931 |
| 28 | `yucatan_peninsula` | 95,830 | -0.0027 | 0.0307 | 0.0307 | 0.0382 | -0.2% | -19.7% | +0.4038 | 0.922 |
| 29 | `brittany_france` | 95,948 | -0.0106 | 0.0346 | 0.0349 | 0.0431 | -0.8% | -19.7% | +0.4243 | 0.693 |
| 30 | `iberian_wildfire` | 96,000 | -0.0110 | 0.0450 | 0.0471 | 0.0525 | -4.5% | -14.3% | +0.1835 | 0.896 |
| 31 | `borneo_rainforest` | 95,646 | -0.0114 | 0.0277 | 0.0286 | 0.0310 | -3.2% | -10.6% | +0.2734 | 0.734 |
| 32 | `tuva_steppe` | 115,201 | -0.0189 | 0.0524 | 0.0520 | 0.0667 | +0.8% | -21.3% | +0.4197 | 0.931 |
| 33 | `pamir_plateau` | 96,000 | -0.0235 | 0.0162 | 0.0155 | 0.0199 | +5.1% | -18.3% | +0.4804 | 0.958 |
| 34 | `costa_rica` | 95,839 | -0.0453 | 0.0207 | 0.0206 | 0.0248 | +0.5% | -16.7% | +0.3340 | 0.910 |
| 35 | `east_african_savanna` | 188,160 | -0.0725 | 0.0753 | 0.0706 | 0.0970 | +6.7% | -22.4% | +0.4335 | 0.765 |
| 36 | `llanos_venezuela` | 227,808 | -0.0846 | 0.0327 | 0.0317 | 0.0374 | +3.2% | -12.4% | +0.2845 | 0.971 |
| 37 | `scandinavian_taiga` | 398,548 | -0.1226 | 0.0586 | 0.0551 | 0.0727 | +6.3% | -19.4% | +0.4740 | 0.940 |
| 38 | `uruguay` | 157,728 | -0.1313 | 0.0512 | 0.0511 | 0.0589 | +0.1% | -13.1% | +0.1631 | 0.603 |
| 39 | `alaska_north_slope` | 355,000 | -0.1892 | 0.0446 | 0.0389 | 0.0477 | +14.8% | -6.4% | +0.3894 | 0.976 |
| 40 | `karoo` | 131,664 | -0.2172 | 0.0239 | 0.0235 | 0.0305 | +1.5% | -21.7% | +0.3543 | 0.562 |
| 41 | `mexican_altiplano` | 165,600 | -0.2229 | 0.0450 | 0.0390 | 0.0438 | +15.3% | +2.8% | +0.0812 | 0.941 |
| 42 | `drakensberg_lesotho` | 96,000 | -0.2691 | 0.0583 | 0.0503 | 0.0398 | +15.9% | +46.5% | -0.7582 | 0.886 |
| 43 | `tongass_alaska` | 95,985 | -0.3572 | 0.0768 | 0.0628 | 0.0802 | +22.2% | -4.3% | +0.2969 | 0.943 |
| 44 | `gobi_desert` | 192,192 | -0.4003 | 0.0128 | 0.0107 | 0.0144 | +19.9% | -10.9% | +0.3524 | 0.811 |

**Aggregates.** macro MAE model 0.0387 | clim 0.0399 | pers 0.0453. Beats clim **29/44** (p = 0.0488), beats persistence **39/44** (p = 1.41e-07), beats **both 26/44** (p = 0.291). Macro MSSS +0.0347, median +0.0309. Mean corr(model, persistence) 0.8808.

**Orthogonality of the two baselines.** corr(MSSS, skill-vs-persistence) = **-0.147** across these
44 regions. They are near-independent and sometimes opposed — reporting either alone is selective.

## 5.3  Nowcast vs forecast, side by side

| # | region | NOW MAE | NOW clim | NOW Δ | FC MAE | FC clim | FC Δ | nowcast→forecast |
|---|---|---|---|---|---|---|---|---|
| 1 | `alaska_interior_taiga` | 0.0478 | 0.0561 | -14.8% | 0.0558 | 0.0553 | +0.9% | +15.7 pp |
| 2 | `alaska_north_slope` | 0.0398 | 0.0384 | +3.4% | 0.0446 | 0.0389 | +14.8% | +11.4 pp |
| 3 | `anatolian_plateau` | 0.0358 | 0.0413 | -13.2% | 0.0402 | 0.0408 | -1.4% | +11.7 pp |
| 4 | `atacama_desert` | 0.0049 | 0.0057 | -14.3% | 0.0055 | 0.0058 | -5.4% | +8.9 pp |
| 5 | `borneo_peat_fires` | 0.0266 | 0.0333 | -20.1% | 0.0253 | 0.0339 | -25.5% | -5.5 pp |
| 6 | `borneo_rainforest` | 0.0270 | 0.0282 | -4.1% | 0.0277 | 0.0286 | -3.2% | +0.9 pp |
| 7 | `brittany_france` | 0.0301 | 0.0350 | -13.9% | 0.0346 | 0.0349 | -0.8% | +13.1 pp |
| 8 | `central_india_dry_forest` | 0.0483 | 0.0678 | -28.8% | 0.0635 | 0.0687 | -7.5% | +21.3 pp |
| 9 | `costa_rica` | 0.0209 | 0.0206 | +1.1% | 0.0207 | 0.0206 | +0.5% | -0.6 pp |
| 10 | `drakensberg_lesotho` | 0.0239 | 0.0468 | -48.9% | 0.0583 | 0.0503 | +15.9% | +64.9 pp |
| 11 | `east_african_savanna` | 0.0488 | 0.0698 | -30.1% | 0.0753 | 0.0706 | +6.7% | +36.8 pp |
| 12 | `gobi_desert` | 0.0076 | 0.0096 | -21.4% | 0.0128 | 0.0107 | +19.9% | +41.3 pp |
| 13 | `greece_mainland` | 0.0280 | 0.0382 | -26.6% | 0.0309 | 0.0356 | -13.2% | +13.4 pp |
| 14 | `hulunbuir_grassland` | 0.0416 | 0.0613 | -32.2% | 0.0574 | 0.0620 | -7.4% | +24.8 pp |
| 15 | `hungarian_puszta` | 0.0429 | 0.0624 | -31.2% | 0.0470 | 0.0515 | -8.7% | +22.5 pp |
| 16 | `iberian_wildfire` | 0.0345 | 0.0465 | -25.8% | 0.0450 | 0.0471 | -4.5% | +21.3 pp |
| 17 | `indian_acacia_babool` | 0.0385 | 0.0698 | -44.9% | 0.0473 | 0.0608 | -22.1% | +22.7 pp |
| 18 | `japan_central_honshu` | 0.0294 | 0.0408 | -28.0% | 0.0372 | 0.0428 | -13.2% | +14.8 pp |
| 19 | `karoo` | 0.0187 | 0.0265 | -29.5% | 0.0239 | 0.0235 | +1.5% | +31.0 pp |
| 20 | `llanos_venezuela` | 0.0333 | 0.0316 | +5.3% | 0.0327 | 0.0317 | +3.2% | -2.2 pp |
| 21 | `madagascar_spiny_thicket` | 0.0285 | 0.0549 | -48.2% | 0.0521 | 0.0567 | -8.2% | +40.0 pp |
| 22 | `madagascar_western_dry` | 0.0265 | 0.0446 | -40.7% | 0.0421 | 0.0479 | -12.2% | +28.6 pp |
| 23 | `mediterranean_andalusia` | 0.0251 | 0.0324 | -22.7% | 0.0292 | 0.0307 | -5.0% | +17.7 pp |
| 24 | `mesopotamia` | 0.0251 | 0.0320 | -21.6% | 0.0255 | 0.0282 | -9.5% | +12.0 pp |
| 25 | `mexican_altiplano` | 0.0239 | 0.0345 | -30.8% | 0.0450 | 0.0390 | +15.3% | +46.1 pp |
| 26 | `mopane_woodland` | 0.0298 | 0.0389 | -23.2% | 0.0376 | 0.0392 | -4.0% | +19.2 pp |
| 27 | `namib_desert` | 0.0035 | 0.0038 | -7.1% | 0.0036 | 0.0038 | -4.8% | +2.2 pp |
| 28 | `new_zealand_north_island` | 0.0227 | 0.0316 | -28.2% | 0.0309 | 0.0315 | -1.9% | +26.3 pp |
| 29 | `nile_valley_delta` | 0.0152 | 0.0222 | -31.4% | 0.0129 | 0.0186 | -30.7% | +0.7 pp |
| 30 | `okavango_delta` | 0.0336 | 0.0429 | -21.6% | 0.0404 | 0.0422 | -4.2% | +17.4 pp |
| 31 | `pamir_plateau` | 0.0147 | 0.0167 | -12.2% | 0.0162 | 0.0155 | +5.1% | +17.3 pp |
| 32 | `pearl_river_delta` | 0.0375 | 0.0493 | -24.0% | 0.0360 | 0.0483 | -25.4% | -1.4 pp |
| 33 | `scandinavian_taiga` | 0.0519 | 0.0558 | -7.0% | 0.0586 | 0.0551 | +6.3% | +13.3 pp |
| 34 | `sundarbans` | 0.0490 | 0.0563 | -12.9% | 0.0500 | 0.0557 | -10.3% | +2.6 pp |
| 35 | `tasmania_western` | 0.0267 | 0.0272 | -1.6% | 0.0274 | 0.0273 | +0.3% | +1.9 pp |
| 36 | `thar_desert` | 0.0277 | 0.0426 | -35.1% | 0.0389 | 0.0404 | -3.8% | +31.2 pp |
| 37 | `tierra_del_fuego` | 0.0446 | 0.0468 | -4.8% | 0.0468 | 0.0470 | -0.4% | +4.4 pp |
| 38 | `tongass_alaska` | 0.0681 | 0.0631 | +7.8% | 0.0768 | 0.0628 | +22.2% | +14.4 pp |
| 39 | `tuva_steppe` | 0.0415 | 0.0478 | -13.1% | 0.0524 | 0.0520 | +0.8% | +13.9 pp |
| 40 | `uk_midlands` | 0.0332 | 0.0402 | -17.2% | 0.0387 | 0.0393 | -1.6% | +15.5 pp |
| 41 | `uruguay` | 0.0399 | 0.0518 | -23.0% | 0.0512 | 0.0511 | +0.1% | +23.1 pp |
| 42 | `vietnam_central_highlands` | 0.0268 | 0.0324 | -17.4% | 0.0271 | 0.0296 | -8.4% | +9.1 pp |
| 43 | `western_europe_temperate` | 0.0353 | 0.0470 | -24.9% | 0.0489 | 0.0490 | -0.2% | +24.8 pp |
| 44 | `yucatan_peninsula` | 0.0284 | 0.0311 | -8.6% | 0.0307 | 0.0307 | -0.2% | +8.5 pp |

| aggregate | model | clim | improvement |
|---|---|---|---|
| nowcast macro | 0.0315 | 0.0404 | **-21.9%** |
| nowcast sample-weighted | 0.0347 | 0.0433 | -20.0% |
| forecast macro | 0.0387 | 0.0399 | **-2.9%** |
| forecast sample-weighted | 0.0419 | 0.0423 | -0.9% |

Rows behind these: nowcast **10,276,212**, forecast **5,880,664**.

**Nowcast skill anti-predicts forecast skill.** corr(nowcast Δ%, forecast Δ%) = **+0.348**.
The largest reversals — regions that are strong nowcast and weak forecast:

| region | nowcast Δ | forecast Δ | swing |
|---|---|---|---|
| `drakensberg_lesotho` | -48.9% | +15.9% | +64.9 pp |
| `mexican_altiplano` | -30.8% | +15.3% | +46.1 pp |
| `gobi_desert` | -21.4% | +19.9% | +41.3 pp |
| `madagascar_spiny_thicket` | -48.2% | -8.2% | +40.0 pp |
| `east_african_savanna` | -30.1% | +6.7% | +36.8 pp |
| `thar_desert` | -35.1% | -3.8% | +31.2 pp |
| `karoo` | -29.5% | +1.5% | +31.0 pp |
| `madagascar_western_dry` | -40.7% | -12.2% | +28.6 pp |

## 5.4  Prospective 2024 — the four tested regions

| region | n | MSSS | MAE | clim | pers | vs clim | vs pers | MSSS Jan–May | MSSS Jun–Sep |
|---|---|---|---|---|---|---|---|---|---|
| `nile_valley_delta` | 48,720 | +0.4131 | 0.0203 | 0.0266 | 0.0119 | -23.9% | +70.2% | +0.4051 | +0.4415 |
| `pearl_river_delta` | 23,948 | +0.3749 | 0.0367 | 0.0517 | 0.0388 | -29.0% | -5.3% | +0.3705 | +0.3063 |
| `mesopotamia` | 51,000 | +0.1781 | 0.0306 | 0.0328 | 0.0246 | -6.8% | +24.3% | +0.2274 | -0.0474 |
| `thar_desert` | 29,832 | -0.0141 | 0.0644 | 0.0656 | 0.0530 | -1.8% | +21.7% | +0.2427 | -0.0727 |

**Macro** over 153,500 rows: MSSS +0.2380 | MAE 0.0380 vs clim 0.0442 (**-14.0%**) vs pers 0.0321 (+18.5%). Beats climatology **4/4**, beats persistence **1/4**.

## 5.5  Backfill audit — exact-repeat fingerprint, all 44

Rank-4 MOD13C2 backfill is deterministic per (pixel, month), so an exact repeated value within a
(cell, month) series is its fingerprint. Raw tie rate is dominated by quantisation, so it is
normalised: effective levels `L = √(2πe)·sd/1e-4`, expected tie rate `(n−1)/2L`.

| # | region | spread | tie obs % | **OBS/EXP** | neg % | neg % among ties |
|---|---|---|---|---|---|---|
| 1 | `scandinavian_taiga` ⚠ | 0.0676 | 4.03 | **5.8×** | 3.9% | 17.0% |
| 2 | `tuva_steppe` ⚠ | 0.0542 | 6.48 | **5.1×** | 13.3% | 49.6% |
| 3 | `tierra_del_fuego` ⚠ | 0.0546 | 3.45 | **4.9×** | 2.0% | 17.9% |
| 4 | `central_india_dry_forest` ⚠ | 0.0595 | 1.92 | **3.4×** | 0.0% | 0.0% |
| 5 | `sundarbans` ⚠ | 0.0551 | 1.88 | **3.3×** | 0.1% | 0.1% |
| 6 | `alaska_north_slope` ⚠ | 0.0531 | 5.53 | **3.2×** | 47.6% | 93.1% |
| 7 | `alaska_interior_taiga` | 0.0616 | 2.22 | **2.8×** | 24.4% | 63.2% |
| 8 | `pearl_river_delta` | 0.0506 | 1.42 | **2.5×** | 0.0% | 0.0% |
| 9 | `tongass_alaska` | 0.0805 | 1.40 | **1.6×** | 30.2% | 52.7% |
| 10 | `hulunbuir_grassland` | 0.0673 | 0.98 | **1.6×** | 7.4% | 10.0% |
| 11 | `indian_acacia_babool` | 0.0631 | 0.82 | **1.5×** | 0.0% | 0.0% |
| 12 | `borneo_rainforest` | 0.0317 | 1.41 | **1.4×** | 0.0% | 0.0% |
| 13 | `japan_central_honshu` | 0.0425 | 1.30 | **1.3×** | 0.2% | 0.7% |
| 14 | `tasmania_western` | 0.0339 | 1.17 | **1.3×** | 0.0% | 0.0% |
| 15 | `costa_rica` | 0.0252 | 1.56 | **1.3×** | 0.0% | 0.0% |
| 16 | `borneo_peat_fires` | 0.0362 | 1.10 | **1.3×** | 0.0% | 0.0% |
| 17 | `anatolian_plateau` | 0.0530 | 0.92 | **1.3×** | 3.3% | 8.1% |
| 18 | `pamir_plateau` | 0.0202 | 3.15 | **1.3×** | 50.6% | 66.0% |
| 19 | `western_europe_temperate` | 0.0493 | 0.79 | **1.3×** | 0.0% | 0.0% |
| 20 | `east_african_savanna` | 0.0774 | 0.55 | **1.3×** | 0.1% | 0.1% |
| 21 | `mesopotamia` | 0.0330 | 1.85 | **1.3×** | 0.0% | 0.0% |
| 22 | `gobi_desert` | 0.0133 | 4.57 | **1.2×** | 0.6% | 0.1% |
| 23 | `karoo` | 0.0248 | 1.55 | **1.2×** | 0.0% | 0.0% |
| 24 | `uruguay` | 0.0585 | 0.61 | **1.2×** | 0.0% | 0.0% |
| 25 | `hungarian_puszta` | 0.0671 | 0.56 | **1.2×** | 0.1% | 0.0% |
| 26 | `mexican_altiplano` | 0.0422 | 0.87 | **1.2×** | 0.0% | 0.0% |
| 27 | `atacama_desert` | 0.0067 | 6.75 | **1.2×** | 0.7% | 0.3% |
| 28 | `vietnam_central_highlands` | 0.0364 | 1.14 | **1.2×** | 0.0% | 0.0% |
| 29 | `uk_midlands` | 0.0462 | 0.73 | **1.2×** | 0.0% | 0.0% |
| 30 | `brittany_france` | 0.0381 | 0.90 | **1.2×** | 0.0% | 0.0% |
| 31 | `yucatan_peninsula` | 0.0380 | 1.07 | **1.2×** | 0.0% | 0.0% |
| 32 | `greece_mainland` | 0.0424 | 0.85 | **1.2×** | 0.1% | 0.2% |
| 33 | `okavango_delta` | 0.0530 | 0.75 | **1.2×** | 0.0% | 0.0% |
| 34 | `new_zealand_north_island` | 0.0325 | 1.24 | **1.2×** | 0.0% | 0.0% |
| 35 | `llanos_venezuela` | 0.0370 | 1.10 | **1.2×** | 0.0% | 0.0% |
| 36 | `mopane_woodland` | 0.0475 | 0.84 | **1.2×** | 0.3% | 0.4% |
| 37 | `namib_desert` | 0.0046 | 9.27 | **1.2×** | 0.1% | 0.0% |
| 38 | `madagascar_spiny_thicket` | 0.0500 | 0.80 | **1.2×** | 0.0% | 0.0% |
| 39 | `iberian_wildfire` | 0.0507 | 0.74 | **1.2×** | 0.0% | 0.0% |
| 40 | `madagascar_western_dry` | 0.0409 | 0.96 | **1.2×** | 0.0% | 0.0% |
| 41 | `nile_valley_delta` | 0.0180 | 5.77 | **1.1×** | 0.0% | 0.0% |
| 42 | `thar_desert` | 0.0459 | 0.93 | **1.1×** | 0.0% | 0.0% |
| 43 | `drakensberg_lesotho` | 0.0445 | 0.89 | **1.1×** | 0.0% | 0.0% |
| 44 | `mediterranean_andalusia` | 0.0348 | 1.00 | **1.1×** | 0.0% | 0.0% |

Median **1.2×**; **6/44** above 3× (flagged ⚠). corr(OBS/EXP, negative-row %) = +0.240.
---

# PART VI — UNCERTAINTY

## 6.1  ESS-BM-CP and what was actually shipped

The project explored **ESS-BM-CP** (Effective-Sample-Size Block-Mondrian Conformal Prediction) — a
distribution-free interval method with block structure for spatial correlation and a Mondrian
(conditional) split so coverage holds *within* strata rather than only on average.

**What shipped is the frozen-calibration variant.** Two design questions forced it:

1. *What if the user supplies a single cell with no neighbours?* Block structure degenerates.
2. *The architecture never observes NDVI in the test years*, so an adaptive scheme that updates on
   observed residuals would violate the same discipline the leak ban enforces.

Frozen calibration answers both: intervals are fixed from ≤2019 and never updated in the test window.

## 6.2  The difficulty model

A **random forest predicting the main model's own `|error|`**, used as the conformal normaliser.

| | |
|---|---|
| Target | `|y − p|` of the deployed model |
| Fitting | **leave-one-region-out** — a region's own rows never train its normaliser |
| Features | `FEATS_V2`, including `abslat` (recovered from `cell_id`), `yr`, `reg_absres19` |
| Role | scales the conformal radius per row |

**Why a difficulty model at all.** A constant-width interval is wrong everywhere: it over-covers easy
cells and under-covers hard ones. Normalising by predicted error makes width track difficulty.

## 6.3  Results

| | |
|---|---|
| Difficulty correlation, sign positive | **44 / 44 regions** |
| Mean difficulty correlation | **+0.332** |
| Conditional-coverage spread | **0.287 → 0.124** (**57% flatter**) |
| Mean coverage | **0.884** |

The spread number is the one that matters: it measures how much coverage varies *across* strata.
Halving it means the interval means roughly the same thing in an easy cell and a hard one.

## 6.4  Fixed-width comparison

A fixed ±0.03 band was tested as an alternative to letting the method choose width. It is simpler to
communicate but discards the conditional calibration that is the method's whole point. Reported for
comparison, not adopted.

---

# PART VII — MODEL INTERROGATION (the sandbox)

Full spec: `presplit_cc/SANDBOX.md`. Logged as Parts 395–402.

## 7.1  What it is

Takes one calibrated cell, edits its drivers, reports what the model says. **Nothing is refitted** —
the cell's calibrated weights are reused exactly.

**The expensive part was already done.** `weights_subset.npy` holds the full 44,500-dimensional ridge
solution for **64 cells per region**. Across 44 regions that is **2,816 already-calibrated cells**.

## 7.2  The gate — two independent checks

| check | question | measured |
|---|---|---|
| **solve check** | do our re-solved tree weights match production's saved 44,500-dim vector? | < 1×10⁻⁶ |
| **reconstruction check** | do our predictions match the stored `evt` column? | **1.77×10⁻⁴** (thar) / **9.12×10⁻⁶** (gobi) |

Either failing halts the tool. Both are needed: a right fit with a wrong context block passes the
first and fails the second.

**Tolerance is 5×10⁻⁴, and that is the model's own precision, not a loosened gate.** Evidence it is
float16 quantisation rather than a wiring fault: (a) the error distribution is a smooth continuum
(p50 8.5×10⁻⁶ → p100 1.77×10⁻⁴), where a wiring fault gives a few broken months against a clean
baseline; (b) the **weights already matched**, ruling out every fault that would move the fit;
(c) test rows reconstruct *better* than calibration rows, which a systematic error would not respect.

**Why counterfactuals are correct by construction.** `_solve_exact` fits on calibration rows only, so
editing a **test** row cannot move the fit. Editing a calibration row would — and the tool refuses.

## 7.3  Correlated response

Editing one driver moves its correlates by the Gaussian **conditional mean on deseasonalised
anomalies of that cell's own record**:

```
E[X_free | X_edit = x_e] − μ_free  =  Σ_fe · Σ_ee⁻¹ · (x_e − μ_e)
```

**Three design decisions, each with its reason:**

| decision | why |
|---|---|
| **deseasonalise first** | raw precip/soil-moisture correlate **0.981** through the shared annual cycle; **0.880** on anomalies. Propagating raw would encode "it is July", not "rain wets soil". |
| **conditional mean, not pairwise `r·(σ_j/σ_i)`** | pairwise double-counts shared variance for multiple simultaneous edits, while reducing **exactly** to it for one (verified: 117.7285 vs 117.7287) |
| **frozen drivers in the CONDITIONING set at zero** | zeroing afterwards breaks the constraint *and* leaves every other driver at a value computed assuming the frozen one moved. Verified: freezing precip changed the free temp response from −3.248 to +0.310. |

Zero-variance columns receive exactly zero delta.

## 7.4  What the model reads

| finding | number | Part |
|---|---|---|
| Strongest single driver, moved alone across its whole range | **0.0052** NDVI (15% of MAE) | 396 |
| Same class of edit with correlates responding | **0.2111** (**40×**) | 396 |
| Features clearing the floor, direct | 272 / 569 | 396 |
| Features clearing the floor, propagated | 558 / 569 | 396 |
| Lag-2 soil moisture rank | **#7 of 569** | 397 |
| Current-month soil moisture rank | **#224 of 569** | 397 |
| Precipitation, direct, full 0–425 mm range | **0.0001** (flat) | 395 |
| Precipitation, propagated | 0.0070 | 395 |

**The structural claim:** the model has no important *features*, it has an important *state*. Each
donor tree splits on a handful of columns; a single perturbation flips a few splits in a few trees;
the ridge averages 44,500 columns and isolated changes wash out. A coherent multi-column shift moves
many trees the same way at once.

**Consequence for attribution methods.** SHAP and permutation importance report importance for levers
that do not exist. This is the *mechanism* behind the project's earlier SHAP-proxy finding, not
another instance of it.

## 7.5  Additivity holds raw and dies under co-variation  [Part 398]

| k drivers stacked | propagation OFF | propagation ON |
|---|---|---|
| 1 | +0.0034 | +0.0374 |
| 5 | +0.0142 | +0.0302 |
| 12 | +0.0273 | +0.0246 |
| **20** | +0.0377 | **−0.0507** |
| 60 | +0.0633 | −0.0222 |
| 200 | **+0.0827** | — |

Twenty simultaneous *propagated* edits leave the prediction **below baseline** — worse than doing
nothing. Only `greedy`, which re-measures after each commit, keeps improving under propagation.

**Search strategy winner flips:**

| | propagation OFF | propagation ON |
|---|---|---|
| `count` (top-k at once) | **+0.0827** | +0.0187 |
| `smart` (gain-weighted) | +0.0472 | +0.0009 |
| `greedy` (sequential) | +0.0168 | **+0.0492** |
| `exhaustive` (best single) | +0.0034 | +0.0374 |

## 7.6  Forecasting value, ≈ zero prescriptive value  [Part 399]

| search space | achievable ΔNDVI | vs MAE 0.0347 |
|---|---|---|
| free arm, **with** historical columns | +0.0492 | 142% |
| free arm, **present-tense only** (62 drivers) | **+0.0058** | 17% |
| 13 manipulable drivers | +0.0019 | 5.6% |
| current soil moisture only (2 drivers) | **+0.00003** | 0.09% |
| reconstruction floor | 0.0005 | — |

**297 of 569 columns are historical.** The model's responsiveness concentrates there, and the past
cannot be intervened on. Hence: **forecasting value, ≈ zero prescriptive value.** This is a genuine
limitation, measured rather than asserted, and the recommender is what measured it.

## 7.7  Degradation vs restoration asymmetry  [Part 400]

| direction | best achievable | vs MAE |
|---|---|---|
| push NDVI **up** | +0.00193 | 5.6% |
| push NDVI **down** | **−0.00634** | 18.3% |

**3.3× easier to degrade than restore** with the same 13 levers. **Caveat:** `soil_water_tc_mm` is at
its observed **maximum** in August 2022 — peak monsoon, saturated soil, no headroom up. Part of the
asymmetry is a **ceiling effect specific to this month**. A dry-season run would separate it;
**not done**.

## 7.8  Cell-specificity does NOT generalise  [Parts 401, 402]

| | thar 2022-08 | gobi 2022-03 |
|---|---|---|
| median achievable ΔNDVI | +0.00174 | +0.00053 |
| cells clearing the floor | **62 / 64** | **37 / 64** |
| **distinct first moves** | **11** | **7** |
| most frequent lever | 20% | **64%** (`climate_water_deficit_mm`) |

Part 401 concluded from thar that recommendations are cell-specific — 11 different first moves across
64 *adjacent* cells. **Gobi says the opposite**: one lever wins 64% and barely half the cells clear
the floor. **Confounded** by season (Aug monsoon vs Mar dry) and by aridity (baseline NDVI 0.12–0.45
vs 0.04–0.11). Unresolved; the clean test is thar in March and has **not** been run.

## 7.9  Cost of the sandbox

| operation | cost |
|---|---|
| cache build (`prep`) | 1h06m at 8,007 cells; scales with cells |
| tree-store load | 45–175 s |
| one counterfactual | milliseconds — **48 per solve** |
| full 569-feature scan | ~24 solves, ~1 min |
| 64-cell survey | 25–35 min |

**The batching trick.** `_solve_exact` fits on calibration rows only, so the cell's ~48 test rows are
free real estate: each gets a clone of the target month (same `ctx`, `η`, `U`) differing only in the
probed feature. One solve returns 48 independent counterfactuals. A 1,138-probe scan becomes ~24
solves.

---

# PART VIII — LIMITATIONS, DEFECTS, OPEN QUESTIONS

Numbered so the paper can cite them individually. Several were found by attacking our own results.

## 8.1  Cell sampling is a contiguous corner

`--cellpick first` at cellfrac 0.25–0.50. Not a random sample; the script default is `random`.
**`mesopotamia` flips sign between the two subsets** — MAE worse than climatology at 0.5, −9.5% at
0.25. Needs a caption. *Severity: high (affects interpretation of every per-region number).*

## 8.2  The SARIMA baseline diverged

−2.3×10²⁵⁰. Must be fixed or dropped; a number like that beside real ones costs credibility on both.
*Severity: high (cosmetic but fatal to trust).*

## 8.3  The forecast ablation is 2/12 regions

On thar the **plain route beat the full architecture** (+0.1242 vs +0.1112 at smoke; +0.0928 `avg` vs
+0.0712 `evt` at the pinned-colscale rerun). Greece was a tie (all arms within 0.006, inside the
noise floor). If the thar pattern holds, the paper **cannot** describe the 12-month forecast as
coming from the full architecture. n = 1 clear region + 1 tie. *Severity: high (claim-level).*

Remaining cost: 10 regions × ~74 min ≈ **12.3 h**. Note it cannot *change* what is reported — switching
the reported forecast to the plain ladder would need all 44 re-run (~54 h).

## 8.4  The EVT head's nowcast gain is NULL

The base route's **+0.4590** lies inside `evt_resid_oof`'s CI **[0.4557, 0.4692]**. By the project's
own CI rule the EVT head's anomaly-R² gain over the real strongest model is **null**. Measured on
**thar only**. Its value was on riseR² — diagnostic only.

**Combined with §8.3 this is awkward and should be stated:** the EVT head is neutral at lag 0 and
possibly harmful at lag 12. A reviewer will ask why it is in the architecture. *Severity: high.*

## 8.5  MOD13C2 QA is never read

Rank-4 "Estimated — from MODIS historic time series" (climatology backfill) enters unfiltered.
Exact-repeat fingerprinting, normalised for quantisation, flags **6 of 44 regions above 3× chance**,
concentrated in negative rows (`alaska_north_slope`: 93.1% of tied rows are negative).

**It dilutes rather than inflates:** excluding all six *improves* every headline —
nowcast MSSS +0.329 → **+0.355**, forecast +0.035 → **+0.042**. *Severity: medium (disclosable).*

Fix available: an `ndvi_qa` product entry was added to the ingester (MOD13C2 Pixel Reliability →
`V11_ndvi_reliability`, separate output dir). SDS name needs `--probe` confirmation; not yet run.

## 8.6  Prospective evidence is thin

4 regions, 1 year (2024). **Persistence beats the model in 3 of the 4.** thar fails outright
(MSSS −0.0141) because 2024's monsoon ran **+0.1014 above climatology (58% excess)**.
*Severity: medium (scope, honestly stated).*

## 8.7  Cell-specificity does not generalise

Thar 11 distinct best-interventions / top lever 20%; gobi 7 / **64%**. Confounded by season and
aridity. Unresolved. *Severity: medium (narrows Part 401).*

## 8.8  Negative NDVI

6.68% of test rows. Real and correctly ingested, but the model does **not** call the sign better than
climatology (F1 0.860 vs 0.864), and "never predict negative" scores 93.32% against a 6.68% base
rate. Must not be claimed as a capability. *Severity: low (already handled).*

## 8.9  Reconstruction floor

**5×10⁻⁴ NDVI** bounds every sandbox result. Any counterfactual shift below it is zero.

## 8.10  Two leak-ban versions in the codebase

9-column and 11-column. Mainline is **11**, asserted at runtime and printed every run. ~25 older
exploratory scripts carry the stale 9 and would silently admit EVI. No reported result comes from
those. *Severity: low, but a reviewer grepping the repo will find it.*

## 8.11  No desertification assessment

No trend analysis, no attribution, no degradation extent or rate. **This is a forecasting-methods
paper.** Part VII describes the *architecture*, not vegetation. Writing "the model responds to
antecedent soil moisture" as though it were "vegetation responds to antecedent soil moisture" is the
single easiest way to lose a reviewer.

*If a desertification component is wanted, it is new work starting from `D:\monthly_panel` (44 GB,
intact) — **not** from the cached panels, 47 of 53 of which are `sh12f0` and deliberately lagged 12
months.*

## 8.12  Selection on the test window

2020–2023 was used to choose the architecture across a **701-idea campaign**. That is selection on the
evaluation window (Cawley 2010 criterion-variance). **This is precisely why the prospective test
matters** — and on 3 of 4 regions the model scored *higher* on the unseen year, which is the direct
answer to the objection. But it is 4 regions.

## 8.13  Ledger hygiene

Of the 701 ideas, the per-idea ledger's negatives are **not** all valid: 23 corrector ideas were
judged with no corrector present, 30+ were confounded by a missing alpha sweep, 86 by no-op arms. No
surviving winner emerged from the campaign. Cite the campaign as *search effort*, not as a table of
validated negatives.

---

# PART IX — EXPERIMENT LOG DIGEST (Parts 380–402)

The parts most likely to be cited. Full text in `EXPERIMENT_SUMMARY.md`.

| Part | subject | outcome |
|---|---|---|
| 385 | prospective 2024 verification | **RETRACTED** — MOD13C2 predictions scored against MOD13A3 |
| 387 | negative-NDVI audit | 686,854 rows, 6.68%, 29/44 regions; excluding them moves MSSS +0.329→+0.333 |
| 388 | is negative NDVI real / predictable? | real & documented; **capability claim dead** on 3 grounds |
| 389 | persistence baselines, both horizons | nowcast 42/44, forecast 39/44; baselines near-orthogonal (−0.147) |
| 390 | target provenance + backfill | MOD13C2 confirmed; QA unread; 6/44 flagged; **dilutes, not inflates** |
| 391 | forecast ablation, smoke 2/12 | full architecture **4th of 5** on thar; gate blend is the culprit |
| 392 | Part 385 **UN-RETRACTED** | product check corr 1.0000; thar 2024 MSSS −0.0141; skill is seasonal |
| 393 | 44-region MAE table | nowcast −21.9%, forecast −2.9%; forecast claim bounded 4 ways |
| 394 | prospective on managed-water regions | **4/4 over climatology**; 3/4 higher out-of-sample; persistence 1/4 |
| 395 | sandbox built | gate 1.77×10⁻⁴; 4 bugs incl. a 14.75 GB allocation in the oracle path |
| 396 | full sensitivity map | **no lever, only state**: 0.0052 alone vs 0.2111 propagated |
| 397 | soil-moisture family | **lag-2 peak** (#7) vs current-month (#224), two products agree |
| 398 | recommender, 4 strategies | additivity holds raw, dies propagated; winner flips |
| 399 | the past is not a lever | **forecasting value, ≈ zero prescriptive value** |
| 400 | management levers + cost | degradation 3.3× easier; cost model **corrected** (470× → 347×) |
| 401 | all 64 cells, thar | 11 distinct first moves — recommendation is cell-specific |
| 402 | gobi, second region | **narrows 401**: gobi is 64% one lever; gate 9.12×10⁻⁶ |

**Corrections and reversals to disclose, because they strengthen rather than weaken the record:**

| what | corrected by |
|---|---|
| Part 385 retracted (product mismatch) | Part 392 un-retracted with a hard product check |
| "persistence is the strong half" (Part 393) | reversed by Part 394 — 1/4 prospectively |
| Part 398's numbers as *advice* | voided by Part 399 — they edited the past |
| "470× cost-effectiveness" | retracted in Part 400 — an artifact of per-unit costing |
| Part 401's cell-specificity headline | narrowed by Part 402 to thar |

---

# PART X — REPRODUCIBILITY

## 10.1  Single entry point

```
py -3.9 -u presplit_cc\desertflow.py --list
```

| stage | module | needs |
|---|---|---|
| `nowcast` | `cross_region_run89.py --shift 0 --future 0` | trained donors |
| `forecast` | `cross_region_run89.py --shift 12 --future 1` | trained donors |
| `table` | `run89_table.py` | a finished run |
| `prep` | `cross_region_run89.py --sandboxdump --sandboxonly` | a finished run |
| `verify` | `sandbox_app.py --verify` | prep |
| `scan` / `sweep` / `family` | `sandbox_scan/sweep/family.py` | prep + verify |
| `advise` / `survey` | `sandbox_recommend.py` / `sandbox_allcells.py` | prep + verify |

Prerequisites are enforced — a stage refuses and names what to run first. **`--dry`** prints the
delegated command without executing; it caught three real defects in one sitting.

## 10.2  Cost table

| stage | cost | scales with |
|---|---|---|
| donor training, 89 regions | **~5 days**, done once | regions × trees |
| panel build | 1–2 min | cells |
| helper projection | 6–13 min | rows |
| tree flatten | 45–175 s | fixed (2.47 GB) |
| **standardisation** | **20–52 min** | rows × 44,500 |
| routing | 32–71 min | cells (~1 s/cell) |
| sandbox `prep` | **1h06m at 8,007 cells** | cells |
| 64-cell survey | 25–35 min | cells |

Retro-fitting sandbox caches for all 44 regions: **50–80 h**. `--sandboxdump` now dumps *and
continues to routing*, so future runs save the cache for free.

## 10.3  Environment traps

| trap | consequence |
|---|---|
| `OPENBLAS_NUM_THREADS > 13` | asserted at import; past 13 the small-gemm path is **4.96× slower** |
| `--jobs` changed mid-bank | joblib sets worker BLAS threads to `cpu_count // n_jobs`; ill-conditioned leaf ridges are thread-sensitive — **results change** |
| bare `python` | resolves to 3.12 without pyarrow — cannot read a panel. Use **`py -3.9`** |
| MODIS ingestion | needs conda env `modis` (pyhdf/HDF4) at `D:\Miniconda3` |
| PowerShell `2>&1` | wraps native stderr in `NativeCommandError`; the sklearn banner aborts a script under `$ErrorActionPreference='Stop'` |

Machine of record: **i7-11800H, 15.8 GB RAM**, D: is a 7200 rpm HDD, C: is SSD.

## 10.4  Oracles — never edited

`cross_region_fast.py`, `cross_region_nocap.py`, `bench_local.py`, `arch_per_cell.py`.

Where the sandbox needed different behaviour — `_solve_exact` computes `trace(TᵀT)` by materialising a
**44,500² Gram = 14.75 GB**, an instant OOM on a 15.8 GB machine — the arithmetic was reimplemented
alongside as `(T**2).sum()` and **verified equal to the oracle** (0.0 without GLS, 6.7×10⁻¹⁶ with),
rather than modifying the reference.

## 10.5  Key artifacts

| path | content |
|---|---|
| `D:\monthly_panel` | 2,926 parquet, 44 GB — read-only source |
| `D:\run89full\out\<region>\samples\` | **per-row predictions, all 44 regions, 0.32 GB** |
| `D:\run89full\out\<region>\weights_subset.npy` | 64 cells × 44,500 router weights |
| `D:\run89full\sandbox\sandbox_<region>.npz` | sandbox cache |
| `D:\run89\models` | 44,500 donor tree pairs |
| `D:\run89\colscale_20c959cc_1200.npy` | the shared divisor vector |

**Note.** Panels are mostly gone and mostly the wrong kind: of 53 surviving `X` files (94.6 GB), **47
are `sh12f0`** (forecast, features lagged 12 months) and only 2 are nowcast-aligned. Per-row
predictions survive for all 44 regions; the 612-feature matrices do not.

---

# PART XI — PAPER SKELETON

## 11.1  Framing decision (make this first)

**This is a forecasting-methods paper.** The title and abstract must promise a method, not a
desertification assessment. §8.11 is otherwise fatal.

Suggested framing: *zero-shot, memory-free NDVI estimation and 12-month forecasting across drylands,
with prospective verification and interventional model interrogation.*

## 11.2  Section plan

| § | content | source | key numbers |
|---|---|---|---|
| 1 | Introduction — the memory-free × zero-shot × forward gap | lit sweep | 0 of 36 studies fair; Kraft 2019, McPhillips 2026 |
| 2 | Data | Part II | 133 regions, 612 features, MOD13C2, 11-column ban |
| 3 | Architecture | Part III | 44,500 columns, K_AD_climcol, bankless |
| 4 | Evaluation | Part IV | splits, **both** baselines, MSSS definition |
| 5.1 | Nowcast results | §5.1, 5.3 | −21.9%, 38/44, p = 9.4×10⁻⁷ |
| 5.2 | Forecast retrospective | §5.2, 5.3 | 39/44 persistence, p = 1.4×10⁻⁷ |
| 5.3 | **Prospective** | §5.4 | 4/4 clim; 3/4 higher out-of-sample |
| 6 | Uncertainty | Part VI | 44/44 positive; spread 0.287→0.124 |
| 7 | What the model reads | Part VII | no lever/only state; lag-2; prescriptive ≈ 0 |
| 8 | Limitations | Part VIII | all 13, numbered |
| 9 | Conclusion | | |

## 11.3  Wording that must be got right

| do NOT write | write instead |
|---|---|
| "our forecast beats climatology" | "beats climatology in 29/44 regions (p ≈ 0.017); 15 regions are worse than doing nothing" |
| "nowcast" (unqualified) | "driver-conditioned estimation under joint spatial and temporal transfer" |
| "persistence is the harder baseline" (prospective) | retrospectively yes (39/44); **prospectively 1/4** |
| "the model predicts negative NDVI" | climatology calls the sign better — do not claim |
| "the model shows vegetation responds to X" | "the model responds to X" |
| "recommended intervention" | "the input change that moves the model" |
| "470× more cost-effective" | **retracted**; corrected figure 347×, on placeholder costs |

## 11.4  Figures

| # | figure | source |
|---|---|---|
| 1 | Study regions: 89 donors vs 44 targets | region list |
| 2 | Architecture schematic — donors → 44,500 columns → per-cell router | Part III |
| 3 | Nowcast MAE vs both baselines, 44 regions sorted | §5.1 |
| 4 | **Baseline orthogonality** — MSSS vs skill-vs-persistence scatter, r = −0.147 | §5.2 |
| 5 | Forecast Δ% by region, coloured by system type (managed-water / rainfall) | §5.3 |
| 6 | **Prospective**: retrospective vs prospective MSSS, 4 regions | §5.4 |
| 7 | Conformal conditional coverage before/after difficulty normalisation | Part VI |
| 8 | **Direct vs propagated feature response** — the 40× gap | §7.4 |
| 9 | Soil-moisture lag profile — the lag-2 hump, two products | §7.4 |
| 10 | Additivity breakdown — k-sweep, propagation on vs off | §7.5 |

## 11.5  Tables

| # | table | source |
|---|---|---|
| 1 | Data and feature summary | Part II |
| 2 | Per-region nowcast, 44 rows | §5.1 |
| 3 | Per-region forecast, 44 rows | §5.2 |
| 4 | Prospective 2024, 4 rows + retro/prosp comparison | §5.4 |
| 5 | Ablation: five ladder arms | §8.3 (**incomplete — 2/12**) |
| 6 | Backfill audit, 44 rows | §5.5 |
| S1–S3 | supplementary: full per-region, all metrics | Part V |

## 11.6  Before submission — checklist

- [ ] Fix or drop the SARIMA baseline (§8.2)
- [ ] Caption the contiguous-corner cell sampling, with the mesopotamia example (§8.1)
- [ ] Rename the nowcast throughout (§11.3)
- [ ] Forecast headline: persistence retrospectively, **climatology** prospectively (§11.3)
- [ ] State the EVT head's NULL nowcast gain and possible lag-12 liability (§8.4)
- [ ] Decide: run the remaining 10 ablation regions (12.3 h) or report 2/12 honestly
- [ ] Confirm no figure or sentence implies a causal or vegetation claim (§8.11)
- [ ] Supplementary: `EXPERIMENT_SUMMARY.md`, `ARCHITECTURE.md`, `SANDBOX.md`

---

# PART XII — FEATURE RESPONSE TABLES

Direct intervention on the frozen model: each feature set to its observed minimum, then its
observed maximum; `span` is how far the prediction moved. thar_desert_1948_718, 2022-08,
baseline NDVI 0.3744, 569 non-constant features. [Part 396]

## 12.1  DIRECT — each feature moved ALONE, world frozen

Answers *does the model read this column at all*. No confound.

| # | feature | min | max | NDVI@min | NDVI@max | span | signed | × floor |
|---|---|---|---|---|---|---|---|---|
| 1 | `era5l_d2m` | 270 | 298.4 | 0.3691 | 0.3743 | **0.00525** | +0.00525 | 10.5× |
| 2 | `era5l_sshf_lag3` | -1.877e+04 | -758.3 | 0.3762 | 0.3718 | **0.00440** | -0.00440 | 8.8× |
| 3 | `diurnal_temp_range_C_lag1` | 6.3 | 23 | 0.3736 | 0.3694 | **0.00416** | -0.00416 | 8.3× |
| 4 | `era5l_d2m_lag1` | 270 | 298.4 | 0.3705 | 0.3743 | **0.00383** | +0.00383 | 7.7× |
| 5 | `diurnal_temp_range_C` | 6.3 | 23 | 0.3737 | 0.3699 | **0.00381** | -0.00381 | 7.6× |
| 6 | `V09_mean_wind_ms_lag1` | 0.5 | 5.4 | 0.3743 | 0.3706 | **0.00373** | -0.00373 | 7.5× |
| 7 | `soil_water_tc_mm_lag2` | 2.6 | 100.1 | 0.3743 | 0.3778 | **0.00342** | +0.00342 | 6.8× |
| 8 | `era5l_sshf_lag1` | -1.877e+04 | -758.3 | 0.3753 | 0.3718 | **0.00341** | -0.00341 | 6.8× |
| 9 | `sph_kgkg_lag1` | 0.003055 | 0.01989 | 0.3710 | 0.3744 | **0.00337** | +0.00337 | 6.7× |
| 10 | `V05_mean_vpd_kPa` | 0.56 | 4.07 | 0.3724 | 0.3691 | **0.00332** | -0.00332 | 6.6× |
| 11 | `era5l_str` | -2.406e+04 | -4407 | 0.3711 | 0.3744 | **0.00332** | +0.00332 | 6.6× |
| 12 | `sph_kgkg_lag12` | 0.003055 | 0.01989 | 0.3712 | 0.3743 | **0.00316** | +0.00316 | 6.3× |
| 13 | `tc_vapor_pressure_lag12` | 0.636 | 3.533 | 0.3715 | 0.3746 | **0.00314** | +0.00314 | 6.3× |
| 14 | `deeprec_twsa_lag12` | -20.93 | 23.28 | 0.3740 | 0.3771 | **0.00309** | +0.00309 | 6.2× |
| 15 | `V07_total_ref_ET_mm_lag1` | 79.1 | 284.1 | 0.3708 | 0.3738 | **0.00299** | +0.00299 | 6.0× |
| 16 | `era5l_str_lag2` | -2.406e+04 | -4407 | 0.3746 | 0.3775 | **0.00290** | +0.00290 | 5.8× |
| 17 | `sph_kgkg` | 0.003055 | 0.01989 | 0.3716 | 0.3745 | **0.00288** | +0.00288 | 5.8× |
| 18 | `cloud_frequency_pct_lag2` | 0.92 | 96.66 | 0.3742 | 0.3770 | **0.00276** | +0.00276 | 5.5× |
| 19 | `months_since_sig_rain` | 0 | 22 | 0.3744 | 0.3716 | **0.00273** | -0.00273 | 5.5× |
| 20 | `wbal_roll3_lag1` | -717 | 397.6 | 0.3732 | 0.3760 | **0.00272** | +0.00272 | 5.4× |
| 21 | `diurnal_temp_range_C_lag2` | 6.3 | 23 | 0.3757 | 0.3730 | **0.00267** | -0.00267 | 5.3× |
| 22 | `era5l_sro_lag6` | 0 | 0.002516 | 0.3744 | 0.3718 | **0.00256** | -0.00256 | 5.1× |
| 23 | `rmin_pct` | 6.575 | 70.68 | 0.3722 | 0.3748 | **0.00255** | +0.00255 | 5.1× |
| 24 | `climate_water_deficit_mm_roll3` | 6.3 | 238.5 | 0.3765 | 0.3740 | **0.00255** | -0.00255 | 5.1× |
| 25 | `era5l_pev_lag3` | -0.01229 | -0.003317 | 0.3751 | 0.3726 | **0.00252** | -0.00252 | 5.0× |
| 26 | `era5l_sshf` | -1.877e+04 | -758.3 | 0.3757 | 0.3733 | **0.00242** | -0.00242 | 4.8× |
| 27 | `diurnal_temp_range_C_lag3` | 6.3 | 23 | 0.3763 | 0.3739 | **0.00241** | -0.00241 | 4.8× |
| 28 | `era5l_ssro_lag2` | 2.362e-06 | 0.01062 | 0.3721 | 0.3745 | **0.00240** | +0.00240 | 4.8× |
| 29 | `aet_total_mm_roll12` | 1.225 | 42.07 | 0.3724 | 0.3748 | **0.00237** | +0.00237 | 4.7× |
| 30 | `aridity_index_p_pet_lag2` | 0 | 3.911 | 0.3743 | 0.3767 | **0.00235** | +0.00235 | 4.7× |
| 31 | `V09_mean_wind_ms_lag2` | 0.5 | 5.4 | 0.3745 | 0.3722 | **0.00232** | -0.00232 | 4.6× |
| 32 | `clf_dry` | 9.81e-06 | 1 | 0.3744 | 0.3722 | **0.00220** | -0.00220 | 4.4× |
| 33 | `era5l_sshf_lag6` | -1.877e+04 | -758.3 | 0.3757 | 0.3735 | **0.00217** | -0.00217 | 4.3× |
| 34 | `climate_water_deficit_mm` | 0 | 282.8 | 0.3744 | 0.3722 | **0.00212** | -0.00212 | 4.2× |
| 35 | `era5l_pev_lag6` | -0.01229 | -0.003317 | 0.3760 | 0.3739 | **0.00211** | -0.00211 | 4.2× |
| 36 | `diurnal_temp_range_C_lag12` | 6.3 | 23 | 0.3743 | 0.3722 | **0.00202** | -0.00202 | 4.0× |
| 37 | `V07_total_ref_ET_mm_roll12` | 95.7 | 188.4 | 0.3757 | 0.3737 | **0.00196** | -0.00196 | 3.9× |
| 38 | `era5l_pev_lag1` | -0.01229 | -0.003317 | 0.3748 | 0.3728 | **0.00195** | -0.00195 | 3.9× |
| 39 | `era5l_pev_lag12` | -0.01229 | -0.003317 | 0.3750 | 0.3731 | **0.00195** | -0.00195 | 3.9× |
| 40 | `V07_total_ref_ET_mm_wytd` | 5.981 | 123.9 | 0.3745 | 0.3726 | **0.00194** | -0.00194 | 3.9× |
| 41 | `V30_soil_moisture_pct_lag2` | -9.412e-19 | 27.24 | 0.3743 | 0.3763 | **0.00193** | +0.00193 | 3.9× |
| 42 | `iod_lag12` | -0.758 | 0.964 | 0.3742 | 0.3761 | **0.00187** | +0.00187 | 3.7× |
| 43 | `vpd_max_daily_lag1` | 1.229 | 5.35 | 0.3727 | 0.3746 | **0.00187** | +0.00187 | 3.7× |
| 44 | `ao` | -4.266 | 3.417 | 0.3739 | 0.3758 | **0.00186** | +0.00186 | 3.7× |
| 45 | `vpd_days_gt_2kpa` | 0 | 31 | 0.3744 | 0.3725 | **0.00184** | -0.00184 | 3.7× |
| 46 | `scpdsi_lag1` | -4.64 | 4.76 | 0.3757 | 0.3739 | **0.00183** | -0.00183 | 3.7× |
| 47 | `grace_lwe_lag12` | -19.81 | 28.35 | 0.3736 | 0.3754 | **0.00174** | +0.00174 | 3.5× |
| 48 | `spi_06m_lag3` | -1.935 | 2.808 | 0.3733 | 0.3750 | **0.00170** | +0.00170 | 3.4× |
| 49 | `rmin_pct_lag1` | 6.575 | 70.68 | 0.3751 | 0.3735 | **0.00166** | -0.00166 | 3.3× |
| 50 | `wbal_roll12_lag6` | -1994 | -918.2 | 0.3742 | 0.3759 | **0.00166** | +0.00166 | 3.3× |

**272 of 569** features clear the 5×10⁻⁴ floor; **297** are indistinguishable from inert. Strongest span **0.0052** NDVI against a model MAE of 0.0347 (**15%**).

## 12.2  PROPAGATED — correlates responding

Answers *how far does the model move in the kind of month where this value occurs*. NOT pure importance: editing a central driver drags its whole bundle and the effect is credited to the nominated column, so features central to the correlation structure rank high partly for being central.

| # | feature | min | max | NDVI@min | NDVI@max | span | signed | × floor |
|---|---|---|---|---|---|---|---|---|
| 1 | `sph_kgkg` | 0.003055 | 0.01989 | 0.1685 | 0.3797 | **0.21114** | +0.21114 | 422.3× |
| 2 | `tc_vapor_pressure` | 0.636 | 3.533 | 0.1731 | 0.3819 | **0.20882** | +0.20882 | 417.6× |
| 3 | `sph_kgkg_lag1` | 0.003055 | 0.01989 | 0.1976 | 0.3885 | **0.19081** | +0.19081 | 381.6× |
| 4 | `tc_vapor_pressure_lag1` | 0.636 | 3.533 | 0.2092 | 0.3869 | **0.17768** | +0.17768 | 355.4× |
| 5 | `diurnal_temp_range_C` | 6.3 | 23 | 0.3730 | 0.2193 | **0.15371** | -0.15371 | 307.4× |
| 6 | `climate_water_deficit_mm_wytd` | 5.875 | 121.1 | 0.3745 | 0.2214 | **0.15304** | -0.15304 | 306.1× |
| 7 | `V07_total_ref_ET_mm_roll6` | 95.7 | 219.4 | 0.3961 | 0.2446 | **0.15153** | -0.15153 | 303.1× |
| 8 | `era5l_d2m` | 270 | 298.4 | 0.2261 | 0.3763 | **0.15024** | +0.15024 | 300.5× |
| 9 | `era5l_d2m_lag1` | 270 | 298.4 | 0.2565 | 0.3819 | **0.12540** | +0.12540 | 250.8× |
| 10 | `diurnal_temp_range_C_lag1` | 6.3 | 23 | 0.3806 | 0.2848 | **0.09577** | -0.09577 | 191.5× |
| 11 | `V07_total_ref_ET_mm_lag2` | 79.1 | 284.1 | 0.4036 | 0.3191 | **0.08456** | -0.08456 | 169.1× |
| 12 | `vpd_warm_season_mean` | 0.7039 | 3.49 | 0.3705 | 0.2931 | **0.07736** | -0.07736 | 154.7× |
| 13 | `V09_mean_wind_ms_lag2` | 0.5 | 5.4 | 0.3821 | 0.3150 | **0.06712** | -0.06712 | 134.2× |
| 14 | `V05_mean_vpd_kPa` | 0.56 | 4.07 | 0.3680 | 0.3013 | **0.06670** | -0.06670 | 133.4× |
| 15 | `rmin_pct` | 6.575 | 70.68 | 0.3071 | 0.3720 | **0.06494** | +0.06494 | 129.9× |
| 16 | `V07_total_ref_ET_mm` | 79.1 | 284.1 | 0.3745 | 0.3107 | **0.06383** | -0.06383 | 127.7× |
| 17 | `V07_total_ref_ET_mm_lag3` | 79.1 | 284.1 | 0.3849 | 0.3217 | **0.06315** | -0.06315 | 126.3× |
| 18 | `sph_kgkg_lag2` | 0.003055 | 0.01989 | 0.3432 | 0.4046 | **0.06143** | +0.06143 | 122.9× |
| 19 | `tc_vapor_pressure_lag2` | 0.636 | 3.533 | 0.3405 | 0.4011 | **0.06056** | +0.06056 | 121.1× |
| 20 | `era5l_d2m_lag2` | 270 | 298.4 | 0.3418 | 0.4017 | **0.05989** | +0.05989 | 119.8× |
| 21 | `climate_water_deficit_mm_lag2` | 0 | 282.8 | 0.4031 | 0.3447 | **0.05839** | -0.05839 | 116.8× |
| 22 | `era5l_sshf_lag2` | -1.877e+04 | -758.3 | 0.3402 | 0.3985 | **0.05830** | +0.05830 | 116.6× |
| 23 | `solar_radiation_Wm2_lag6` | 161.8 | 308.8 | 0.3744 | 0.3164 | **0.05791** | -0.05791 | 115.8× |
| 24 | `climate_water_deficit_mm_roll6` | 50.65 | 214.5 | 0.3883 | 0.3316 | **0.05670** | -0.05670 | 113.4× |
| 25 | `sph_kgkg_lag12` | 0.003055 | 0.01989 | 0.3183 | 0.3746 | **0.05635** | +0.05635 | 112.7× |
| 26 | `V07_total_ref_ET_mm_roll3` | 91.9 | 242.9 | 0.3923 | 0.3363 | **0.05601** | -0.05601 | 112.0× |
| 27 | `climate_water_deficit_mm_roll12` | 94 | 185.8 | 0.3838 | 0.3287 | **0.05516** | -0.05516 | 110.3× |
| 28 | `V07_total_ref_ET_mm_wytd` | 5.981 | 123.9 | 0.3752 | 0.3209 | **0.05435** | -0.05435 | 108.7× |
| 29 | `wbal_roll6_lag2` | -1289 | 108.6 | 0.3336 | 0.3869 | **0.05322** | +0.05322 | 106.4× |
| 30 | `wbal_roll6_lag1` | -1289 | 108.6 | 0.3351 | 0.3879 | **0.05280** | +0.05280 | 105.6× |
| 31 | `tc_vapor_pressure_lag12` | 0.636 | 3.533 | 0.3227 | 0.3748 | **0.05213** | +0.05213 | 104.3× |
| 32 | `era5l_pev_lag3` | -0.01229 | -0.003317 | 0.3338 | 0.3859 | **0.05201** | +0.05201 | 104.0× |
| 33 | `era5l_str` | -2.406e+04 | -4407 | 0.3285 | 0.3791 | **0.05065** | +0.05065 | 101.3× |
| 34 | `wbal_roll3_lag2` | -717 | 397.6 | 0.3485 | 0.3987 | **0.05021** | +0.05021 | 100.4× |
| 35 | `diurnal_temp_range_C_lag2` | 6.3 | 23 | 0.3988 | 0.3491 | **0.04969** | -0.04969 | 99.4× |
| 36 | `solar_radiation_Wm2_lag3` | 161.8 | 308.8 | 0.3923 | 0.3429 | **0.04934** | -0.04934 | 98.7× |
| 37 | `V09_mean_wind_ms_lag1` | 0.5 | 5.4 | 0.3827 | 0.3347 | **0.04803** | -0.04803 | 96.1× |
| 38 | `tc_vapor_pressure_lag3` | 0.636 | 3.533 | 0.3390 | 0.3870 | **0.04800** | +0.04800 | 96.0× |
| 39 | `sph_kgkg_lag3` | 0.003055 | 0.01989 | 0.3404 | 0.3880 | **0.04765** | +0.04765 | 95.3× |
| 40 | `V07_total_ref_ET_mm_roll12` | 95.7 | 188.4 | 0.3864 | 0.3399 | **0.04647** | -0.04647 | 92.9× |
| 41 | `era5l_d2m_lag12` | 270 | 298.4 | 0.3240 | 0.3703 | **0.04622** | +0.04622 | 92.4× |
| 42 | `era5l_sshf_lag3` | -1.877e+04 | -758.3 | 0.3406 | 0.3868 | **0.04617** | +0.04617 | 92.3× |
| 43 | `esacci_sm_lag2` | 0.05027 | 0.3296 | 0.3591 | 0.4050 | **0.04591** | +0.04591 | 91.8× |
| 44 | `V09_mean_wind_ms_lag3` | 0.5 | 5.4 | 0.3808 | 0.3356 | **0.04522** | -0.04522 | 90.4× |
| 45 | `era5l_pev_lag6` | -0.01229 | -0.003317 | 0.3272 | 0.3724 | **0.04519** | +0.04519 | 90.4× |
| 46 | `wbal_roll6_lag3` | -1289 | 108.6 | 0.3330 | 0.3781 | **0.04512** | +0.04512 | 90.2× |
| 47 | `vpd_warm_season_mean_lag6` | 0.7039 | 3.49 | 0.3726 | 0.3283 | **0.04424** | -0.04424 | 88.5× |
| 48 | `era5l_d2m_lag3` | 270 | 298.4 | 0.3449 | 0.3889 | **0.04400** | +0.04400 | 88.0× |
| 49 | `V09_mean_wind_ms` | 0.5 | 5.4 | 0.3795 | 0.3356 | **0.04395** | -0.04395 | 87.9× |
| 50 | `api_soilmoist` | 1.496 | 7.152 | 0.3436 | 0.3872 | **0.04362** | +0.04362 | 87.2× |

**558 of 569** features clear the 5×10⁻⁴ floor; **11** are indistinguishable from inert. Strongest span **0.2111** NDVI against a model MAE of 0.0347 (**608%**).

## 12.3  Soil-moisture family — the lag-2 hump  [Part 397]

Two independently measured soil-water products, swept across their observed ranges.

| feature | lag | direct span | × floor | propagated span | × floor |
|---|---|---|---|---|---|
| `soil_water_tc_mm` | 0 | 0.00061 | 1.2× | 0.00897 | 17.9× |
| `soil_water_tc_mm_lag1` | 1 | 0.00047 | 0.9× | 0.01552 | 31.0× |
| `soil_water_tc_mm_lag2` | 2 | 0.00342 | 6.8× | 0.02298 | 46.0× | **←**
| `soil_water_tc_mm_lag3` | 3 | 0.00206 | 4.1× | 0.01270 | 25.4× |
| `soil_water_tc_mm_lag6` | 6 | 0.00102 | 2.0× | 0.00411 | 8.2× |
| `soil_water_tc_mm_lag12` | 12 | 0.00197 | 3.9× | 0.00184 | 3.7× |
| `V30_soil_moisture_pct` | 0 | 0.00062 | 1.2× | 0.00795 | 15.9× |
| `V30_soil_moisture_pct_lag1` | 1 | 0.00125 | 2.5× | 0.01218 | 24.4× |
| `V30_soil_moisture_pct_lag2` | 2 | 0.00327 | 6.5× | 0.04188 | 83.8× | **←**
| `V30_soil_moisture_pct_lag3` | 3 | 0.00119 | 2.4× | 0.01991 | 39.8× |
| `V30_soil_moisture_pct_lag6` | 6 | 0.00118 | 2.4× | 0.01056 | 21.1× |
| `V30_soil_moisture_pct_lag12` | 12 | 0.00122 | 2.4× | 0.01490 | 29.8× |

**Both families peak at lag 2 and decay either side.** Current-month soil moisture is near-inert.
Two products measured differently putting the peak in the same place is not an artifact of one dataset.

## 12.4  Intervention survey — 64 cells per region  [Parts 401, 402]

### thar 2022-08 (monsoon)

| statistic | value |
|---|---|
| cells | 64 |
| median achievable ΔNDVI | **+0.00174** |
| mean / min / max | +0.00193 / +0.00033 / +0.00581 |
| clearing the 5e-4 floor | **62 / 64** |
| reaching 50% of MAE | 0 / 64 |
| nothing helps | 0 / 64 |
| **distinct first moves** | **11** |
| baseline NDVI range | 0.1236 – 0.4509 |
| median moves committed | 6 |

| first move chosen | cells | share | median gain | median baseline NDVI |
|---|---|---|---|---|
| `deeprec_twsa` | 13 | 20% | +0.00203 | 0.3179 |
| `aet_total_mm` | 10 | 16% | +0.00262 | 0.2463 |
| `api_soilmoist` | 8 | 12% | +0.00123 | 0.3186 |
| `era5l_stl1` | 6 | 9% | +0.00172 | 0.2612 |
| `esacci_sm` | 5 | 8% | +0.00097 | 0.4110 |
| `V30_soil_moisture_pct` | 4 | 6% | +0.00115 | 0.1300 |
| `era5l_ssro` | 4 | 6% | +0.00288 | 0.3384 |
| `wbal_mm` | 4 | 6% | +0.00138 | 0.1447 |
| `soil_water_tc_mm` | 4 | 6% | +0.00107 | 0.2759 |
| `climate_water_deficit_mm` | 3 | 5% | +0.00248 | 0.3030 |
| `grace_lwe` | 3 | 5% | +0.00087 | 0.1951 |

### gobi 2022-03 (dry)

| statistic | value |
|---|---|
| cells | 64 |
| median achievable ΔNDVI | **+0.00053** |
| mean / min / max | +0.00077 / +0.00020 / +0.00194 |
| clearing the 5e-4 floor | **37 / 64** |
| reaching 50% of MAE | 0 / 64 |
| nothing helps | 0 / 64 |
| **distinct first moves** | **7** |
| baseline NDVI range | 0.0390 – 0.1066 |
| median moves committed | 6 |

| first move chosen | cells | share | median gain | median baseline NDVI |
|---|---|---|---|---|
| `climate_water_deficit_mm` | 41 | 64% | +0.00096 | 0.0777 |
| `V09_mean_wind_ms` | 11 | 17% | +0.00050 | 0.0502 |
| `esacci_sm` | 4 | 6% | +0.00030 | 0.0508 |
| `era5l_stl1` | 3 | 5% | +0.00031 | 0.0778 |
| `wbal_mm` | 3 | 5% | +0.00041 | 0.0787 |
| `aet_total_mm` | 1 | 2% | +0.00044 | 0.0861 |
| `V30_soil_moisture_pct` | 1 | 2% | +0.00032 | 0.0501 |

---

# PART XIII — RELATED WORK AND POSITIONING

## 13.1  The benchmark sweep

A 43-agent literature workflow screened **36 studies** against the cell this work occupies:
memory-free (no NDVI as input) × zero-shot (no training on the target region) × multi-year-forward.

**Result: 0 of 36 were fair yardsticks.** Every study failed at least one axis — most used
autoregressive NDVI, trained per-region, or evaluated at a lead of one month or less.

| study | closest metric | why not a fair comparison |
|---|---|---|
| Kraft 2019 | 0.25–0.40 per-pixel R², arid | uses NDVI memory |
| McPhillips 2026 | MSSS ≈ +0.36 | not zero-shot across regions |
| (34 others) | — | autoregressive, per-region, or ≤1-month lead |

**How to write this.** Do *not* claim to beat them — the comparison is not like-for-like, and saying
so is the stronger move. Claim instead that the intersection is empty and this work occupies it.

## 13.2  Adjacent results worth citing

| topic | source | relevance |
|---|---|---|
| Snow-from-climate, zero-shot | Umirbekov, Essery & Müller 2024 (GMD, **GEMS**) | 92% pixel / 87% class-balanced **in the western Pamir** — one of our own regions. Kills any negative-NDVI capability claim. |
| Precipitation phase | Jennings et al. 2025 (Nat. Commun.) | a single wet-bulb threshold reaches ~93.1%; ML adds ≤0.6% |
| Temperature-index melt | Hock 2003, J. Hydrol. 282:104–115 | index models often match energy-balance models |
| Melt energy partition | Ohmura 2001 | longwave + sensible supply ~¾ of melt energy |
| MODIS VI validation | MODIS LP DAAC | snow is an unstable regime: errors 0.04–0.1 VI units; documented +0.020 compositing bias |
| Model-selection variance | Cawley & Talbot 2010 | criterion variance from selecting on the evaluation window — §8.12 |
| Skill score definition | Murphy 1988 | MSSS / Nash–Sutcliffe against climatology |

---

# PART XIV — QUESTIONS A REVIEWER WILL ASK

Prepared answers. Each cites where the evidence lives.

**Q1. Isn't NDVI leaking in through EVI, LST or albedo?**
No. Eleven vegetation-proxy columns are banned, enforced on `keep_cols` in four modules, re-probed on
3–4 regions each run, with the feature-list SHA compared across probes and a derivation check on
lag/roll children. The log line `banned survivors 0 | V11_mean_ndvi as a feature: NO` prints before
any fitting. [§2.4] *Disclose:* ~25 older exploratory scripts carry a stale 9-column list; no reported
result comes from those.

**Q2. You selected the architecture on 2020–2023 and then evaluated on it.**
Correct, and it is why the prospective test exists. On 2024 — a year that did not exist when the model
was built — **three of four regions scored higher than on the held-out years** (nile +0.0436, pearl
+0.1258, mesopotamia +0.0343). n = 4. [§5.4, §8.12]

**Q3. Your forecast only beats climatology by 3%.**
Yes, and we say so. The defensible forecast claim is against **persistence** (39/44, p = 1.4×10⁻⁷)
while never observing NDVI. Against climatology it is 29/44, MSSS is not significant (p ≈ 0.085), and
**15 regions are worse than doing nothing**. [§5.2, §8.6]

**Q4. Why report two baselines?**
Because they are near-orthogonal — corr(MSSS, skill-vs-persistence) = **−0.147**. nile is best on one
and worst on the other. Reporting either alone would be selective. [§4.3]

**Q5. Is the EVT head doing anything?**
On the nowcast, no: the base route's +0.4590 sits inside its CI, so the gain is **null** (thar only).
At 12-month lead it may be a **liability** — on thar the plain route scored +0.0928 against the full
architecture's +0.0712. The ablation is **2 of 12 regions**. [§8.3, §8.4]

**Q6. 25% of cells, chosen how?**
`--cellpick first` — a deterministic **contiguous corner block**, not a random sample. This matters:
mesopotamia's MAE is *worse* than climatology at cellfrac 0.5 and −9.5% at 0.25. [§4.2, §8.1]

**Q7. What about MODIS quality flags?**
Not read. Rank-4 climatology backfill enters unfiltered. We measured it by exact-repeat fingerprinting
(normalised for quantisation): 6/44 regions above 3× chance. **Excluding all six improves every
headline**, so it dilutes rather than inflates. [§8.5]

**Q8. 6.68% of your NDVI is negative.**
Real, in-range, snow over land — MOD13 excludes water and retains snow/ice. Range is exactly
[−0.2000, 0.9988] with zero fill contamination. Excluding every negative row moves macro MSSS
+0.329 → +0.333. We do **not** claim to predict their sign; climatology does it better. [§2.5]

**Q9. Can this guide land management?**
No, and we measured why. 297 of 569 columns are historical and cannot be intervened on. Restricting to
genuinely manipulable present-tense drivers caps achievable change at ~5% of the model's own MAE.
The architecture has forecasting value and **≈ zero prescriptive value**. [§7.6]

**Q10. Why not SHAP?**
Because it is structurally misleading here. No single driver is a lever: the strongest column moved
alone across its full range shifts the prediction 0.0052, while the same class of edit with correlates
responding shifts it 0.2111 — **forty times more**. Attribution reports importance for levers that do
not exist. We intervene instead. [§7.4]

**Q11. Is the sandbox looking at test data?**
Yes, and it is not a leak. The sandbox issues no predictions to be scored — it asks what the model
does with inputs it already had. The architecture's discipline is separate: donor forests never train
on the target region, and the router is fitted only on ≤2019 rows. [§7.1]

**Q12. How do you know the sandbox reproduces the deployed model?**
A two-part gate: our re-solved tree weights against production's saved 44,500-dim vector, and our
predictions against the stored `evt` column. Measured 1.77×10⁻⁴ (thar) and 9.12×10⁻⁶ (gobi). Either
failing halts the tool. [§7.2]

**Q13. Your 12-month forecast — does the model know it is forecasting?**
No, and it does not need to. `--shift 12` is a panel-level transform: the row keeps its target and
takes features from 12 months earlier. The trees are frozen; only the router refits. It is the same
ensemble asked a harder question. [§3.9]

**Q14. Why is MSSS so low when R² is high?**
Pooled NDVI R² is ~77% climatology floor. MSSS strips the floor out and reports only skill *above*
seasonality. A high R² with a low MSSS is routine, not contradictory. [§4.4]

**Q15. What did you try that failed?**
A 701-idea campaign. No surviving winner emerged. We cite it as **search effort**, not as a table of
validated negatives — 23 corrector ideas were judged with no corrector present, 30+ were confounded by
a missing alpha sweep, 86 by no-op arms. [§8.13]

---

# PART XV — GLOSSARY

| term | meaning |
|---|---|
| **anomaly-R²** | `r2_score(y − clim, p − clim)`. Climatology scores `floor = −(mean/sd)²`, not 0. |
| **bankless routing** | accumulating the Gram per cell-block so the 84–350 GB design matrix is never allocated |
| **cellfrac / cellpick** | fraction of a region's cells used, and how chosen. `first` = contiguous corner. |
| **colscale** | the single shared divisor vector making tree columns comparable across regions |
| **corrector** | the second tree of each pair, fitted to the base's **out-of-bag** residual |
| **donor region** | one of 89 regions whose forests form the basis; never a target |
| **ESS-BM-CP** | Effective-Sample-Size Block-Mondrian Conformal Prediction |
| **difficulty model** | RF predicting the main model's own `\|error\|`, used as the conformal normaliser |
| **gate blend** | linear probe regressing the surge indicator on 89 donor gate columns → `η ∈ [1,3]` |
| **GLS row weights** | `W = 1/σ²` from winsorised donor spread — the "D" |
| **hit-rate** | fraction of rows with `\|y − p\| ≤ 0.02` NDVI |
| **K** | the unpenalised climatology basis, projected out before the ridge |
| **ladder** | the five nested arms omit → size → avg → blend → evt |
| **MSSS** | `(aR² − floor)/(1 − floor)`; climatology scores exactly 0 |
| **noise floor** | ±0.01 anomaly-R² at full scale |
| **propagation** | moving an edited driver's correlates by the conditional mean on deseasonalised anomalies |
| **reconstruction floor** | 5×10⁻⁴ NDVI — the float16 limit on rebuilding a prediction |
| **riseR²** | anomaly-R² on surge rows. **Diagnostic only.** |
| **router** | the per-cell ridge over 44,500 tree columns + context; the only thing fitted on the target |
| **shift / future** | `--shift N` takes features from N months earlier; `--future K` appends K forecast rows |
| **surge indicator** | `tj = (y − y_prev) > JUMP`; what the gate is trained to detect |
| **tree pair** | base predictor + OOB-residual corrector; 500 per donor |
| **zero-shot transfer** | the forests never train on the region being predicted |

---

# PART XVI — DOCUMENT MAP

| file | purpose | audience |
|---|---|---|
| `PAPER_REFERENCE.md` | **this document** — every number, table and caveat | the author, while writing |
| `FINDINGS.md` | claims with their caveats, by paper section | the author, deciding what to claim |
| `ARCHITECTURE.md` | architecture and protocol narrative | a reviewer |
| `presplit_cc/SANDBOX.md` | the interrogation subsystem | a reviewer, or a user of the tool |
| `EXPERIMENT_SUMMARY.md` | 402 numbered Parts, chronological, retractions in place | provenance / supplementary |
| `presplit_cc/sandbox_interventions.py` | the manipulable-driver taxonomy — a **reviewable scientific claim** | a domain reviewer |

**Result CSVs** referenced throughout:

| file | content |
|---|---|
| `nowcast_persistence_44.csv` | per-region nowcast vs both baselines |
| `forecast12_persistence_44.csv` | per-region forecast vs both baselines |
| `mae_table_nowcast_forecast_44.csv` | side-by-side MAE, both horizons |
| `prospective_2024_all.csv` | the four prospective regions |
| `backfill_tie_audit_44.csv` | exact-repeat fingerprint, all 44 |
| `scan_thar_desert_{direct,prop}_202208.csv` | 569-feature response |
| `family_thar_desert_202208.csv` | soil-moisture lag profile |
| `allcells_{thar,gobi}_*_*.csv` | 64-cell intervention surveys |
| `costpath_thar_desert_{increase,decrease}.csv` | ordered intervention paths |
