# The NDVI chapter against every baseline we could legally build

**Status: SUPERSEDED IN PART - CLOSED WITH OPEN ITEMS. Do not circulate this version.**

> **CORRECTION NOTICE (Part 426).** A close-out audit found that the 44 regions scored here are
> **25 genuine test regions plus 19 DONOR regions**, and that 19 real test regions were never scored
> at all. Both counts being 44 is why it went unnoticed. Every occurrence of *“44 held-out regions”*
> below is therefore wrong; the honest N is **25**, i.e. 57% of the test set.
>
> **The conclusion is unchanged and the margins get larger.** On the clean 25 the nowcast scores
> **+0.3207** anomaly R² (published: +0.2930) and every comparison against an external rival is
> significant under a region bootstrap. The Kraft LSTM was additionally trained on 13 of the 19
> donor regions it was scored on — a contamination in *its* favour — and still lost, so the
> published margin is a lower bound.
>
> **One claim does change:** the 12-month forecast **ties** climatology rather than beating it
> (MAE −0.00059, 95% CI [−0.00232, +0.00124]; hit rate +0.66pp, CI [−1.21, +2.48]). §1/§5/§6 state a
> win. Fixes are deferred by decision until the remaining environmental problems are done — the four
> open items are listed in **Part 426**.
Written for adversarial review. Every number traces to a file named in §11. Three errors I made and
caught during this work are recorded in §7 rather than removed.

Source Parts: `EXPERIMENT_SUMMARY.md` **417–426**.

**Scope.** This report evaluates the **monthly** target — the architecture's native resolution, and
what it is built, trained and calibrated to predict. An annual-aggregate comparison was also run on
all 44 regions and is recorded in Parts 419–424; it is excluded here because the annual figure is a
derived average of twelve monthly predictions rather than a target the model was ever asked to
optimise. Excluded on **scope, not on doubt** — §9 states what it found.

---

## 1. The claim

Two information tiers, because *"does the arm see the target month's climate?"* changes the question
entirely:

| tier | ours | best rival | |
|---|---|---|---|
| **nowcast** — sees the target month's climate | **0.03172** MAE, **+0.2930** anomaly R² | 0.04658, **−0.3347** | **we win** |
| **12-month forecast** | **0.03899** MAE, **+0.0073** anomaly R² | 0.04784, **−0.3764** | **we win** |

**We win both monthly tiers — on MAE, on raw R², and on anomaly R².** Against a calibrated global
LSTM and a per-cell Gaussian process, on 4,411,696 cell-months across 44 held-out regions.

**And the honest half of the same sentence:** the nowcast is a strong result (+0.2930 anomaly R²);
the 12-month forecast sits essentially **at the climatology floor** (+0.0073). §6 examines that
rather than burying it.

---

## 2. The leak audit — the chapter's most portable finding

Coral has CRW and wildfire has CEMS. NDVI appeared to have no external baseline at all. The reason
is structural, not an oversight:

| candidate | inputs | verdict |
|---|---|---|
| **NOAA STAR Global VHI** | VCI, TCI, VHI, smoothed NDVI | ✗ **derived from NDVI.** VCI *is* normalised NDVI; SMN *is* smoothed NDVI |
| **FAO ASIS / GIEWS** | NDVI anomaly, VCI, VHI | ✗ same |
| **Copernicus Global Land** | NDVI, FAPAR, VCI, VPI | ✗ same |
| **FEWS NET** | NDVI + rainfall | ✗ qualitative outlooks, not a gridded forecast |
| **Grass-Cast** | **NDVI** + weather + CPC outlooks | ✗ **three ways**: takes NDVI as input; its domain (Great Plains + NM/AZ) excludes every US region in our TEST split; and `great_plains` is a TRAIN region |
| **BARDL** (NHESS 2022) | 3-month lags of **VCI**, precip, soil moisture | ✗ its own AR baseline already reaches R² 0.88/0.77/0.65 — persistence with extras |
| **Global DNN** (2024) | "**NDVI**, temperature, precipitation, soil moisture" | ✗ NDVI is an input; its 0.85 is with the target in hand |
| **McPhillips 2026** | precipitation, max VPD | ✓ **clean — built and run** |
| **Kraft 2019** | climate series + soil + *land cover* | ✓ **clean once land cover is dropped — built and run** |
| Martinuzzi 2024 | meteorology → spectral indices | — clean but European forest **sites**, an architecture comparison, not a gridded forecaster |
| Janetzky 2024 | FourCastNet state | — workshop paper, not a deployable forecaster |

**There is no operational leak-free vegetation forecaster anywhere.** Every operational product
monitors; the forecasting literature almost universally feeds NDVI back in. That is the context for
our 11-proxy ban — and why "no external baseline" was a fact about the field, not about our
diligence.

---

## 3. What we built, and what kind of models they are

**McPhillips 2026** — *Remote Sensing* 18(6):850. A **local, per-cell Gaussian process** mapping
accumulated climate to NDVI, with the climate attributes themselves forecast from data ≥1 year old.
Predictors: precipitation and max VPD, accumulated over trailing 3- and 12-month windows (4
features). Each cell's GP sees only that cell's own history. **Not a trained network** — a small
local fit.

**Kraft 2019** — *Frontiers in Big Data* 2:31. A **single global LSTM**: 12-month windows of six
climate drivers (temperature, precipitation, VPD, soil moisture, radiation, wind) plus six statics
(soil organic carbon, pH, sand, clay, AWC, elevation). 405,112 sequences from donor regions, hidden
64, 8 epochs. **This is a genuinely learned model** — ~30k weights fitted by gradient descent.

**Ours** — cross-region transfer: donor forests never see the target region; only a per-cell ridge is
fitted locally, on ≤2019.

**Two opposite model classes, deliberately.** Beating only a local model invites *"you only beat
local models"*; beating only a deep model invites the reverse.

**Worth stating plainly:** Kraft is the **first trained, pooled machine-learning rival this project
has faced**. NOAA CRW is fixed alert thresholds; CEMS GEFF is Van Wagner's 1987 equations with
coefficients frozen since the 1980s; McPhillips is a four-feature local fit. Beating a real deep
model is a different claim from beating an index.

### Two handicaps imposed on Kraft, both declared

1. **Land cover was dropped.** Kraft's published form uses it. Every optical land-cover product is a
   banned proxy here — NDVI is an input to the classifiers that produce them. Dropping it removes
   the main signal telling a global model what NDVI *level* to expect in a cell.
2. **It initially had no local calibration**, while both other models are locally calibrated by
   construction. That was unfair and was fixed — §7.3.

---

## 4. Phase two: three versions of "what will the climate be?"

Both rivals must guess next year's climate. Rather than pick one guess, all three are run:

| arm | fed | honest? |
|---|---|---|
| `driver-clim` | the cell's ≤2019 average for that calendar month | ✓ |
| `lag12` | the driver's observed value 12 months earlier | ✓ |
| **`ORACLE`** | **the driver's true value in the month being predicted** | ✗ **reads the future** |

The oracle is **not a forecast and never competes**. It is a labelled ceiling — the same instrument
as the DHW oracle in the coral report and the `[+hist]` arms in wildfire. The gap between it and the
honest arms measures **how forecastable the drivers are**; the gap between it and our nowcast
measures **how good the climate→NDVI map is**.

**Its information-matched partner is our NOWCAST, never our forecast.** Comparing an oracle to a
forecast produced a retracted claim in Part 417 (§7.2).

---

## 5. Results — 4,411,696 rows, 124,585 cells, 44 held-out regions

### 5.1 MAE and R²

| tier | arm | MAE | vs clim | beats clim | raw R² | **anomaly R²** |
|---|---|---|---|---|---|---|
| sees target climate | **OURS nowcast** | **0.03172** | **+19.7%** | **38/44** | **0.8342** | **+0.2930** |
| *(not forecasts)* | Kraft LSTM ORACLE (cal) | 0.04658 | −17.9% | 15/44 | 0.7158 | −0.3347 |
| | McPhillips ORACLE | 0.05554 | −40.6% | 6/44 | 0.5953 | −1.0266 |
| | Kraft LSTM ORACLE (raw) | 0.09109 | −130.5% | 2/44 | — | — |
| 12-month forecast | **OURS forecast** | **0.03899** | **+1.3%** | **24/44** | **0.7493** | **+0.0073** |
| | Kraft driver-clim (cal) | 0.04784 | −21.1% | 9/44 | 0.6832 | −0.3764 |
| | Kraft lag-12 (cal) | 0.05125 | −29.7% | 6/44 | 0.6471 | −0.5619 |
| | McPhillips driver-clim | 0.05569 | −41.0% | 3/44 | 0.5865 | −1.0260 |
| | McPhillips lag-12 | 0.05862 | −48.4% | 1/44 | — | — |
| | cell climatology | 0.03951 | — | — | 0.7492 | 0.0000 |

**ATTENTION — never quote raw R² for this problem.** Climatology alone scores **0.7492**. NDVI is
dominated by its seasonal cycle, so any arm reproducing seasonality looks strong regardless of
skill. Anomaly R², deseasonalised against the per-cell-month climatology, is the only informative
form. Both are shown so the point is visible rather than asserted.

### 5.2 Head-to-head region counts, out of 44

| comparison | ours wins |
|---|---|
| OURS forecast vs **Kraft driver-clim (cal)** | **38** |
| OURS forecast vs **Kraft lag-12 (cal)** | **40** |
| OURS forecast vs Kraft ORACLE (cal) | **30** |
| **OURS nowcast** vs Kraft ORACLE (cal) | **39** |
| **OURS nowcast** vs Kraft driver-clim (cal) | **40** |
| OURS forecast vs McPhillips driver-clim | **39** |
| OURS forecast vs McPhillips lag-12 | **41** |
| **OURS nowcast** vs McPhillips ORACLE | **44** |
| OURS forecast vs climatology | 24 |
| OURS nowcast vs climatology | **38** |
| OURS forecast vs **best of all rival honest arms** | **33** |

**Our nowcast beats McPhillips's oracle — an arm that reads the future — in 44 of 44 regions.**

---

## 6. The weakest number in this report, examined

**Our 12-month forecast sits at the climatology floor: +0.0073 anomaly R², against the nowcast's
+0.2930.** A factor of forty. In MAE it is +1.3% over a free baseline, beating it in only **24 of
44** regions.

| wins most vs climatology | ours | clim | | loses most | ours | clim |
|---|---|---|---|---|---|---|
| pearl_river_delta | 0.03659 | 0.04877 | | tongass_alaska | 0.07316 | 0.06168 |
| indian_acacia_babool | 0.04981 | 0.06019 | | drakensberg_lesotho | 0.06317 | 0.05527 |
| borneo_peat_fires | 0.02616 | 0.03359 | | east_african_savanna | 0.06505 | 0.05745 |
| nile_valley_delta | 0.01375 | 0.01922 | | mexican_altiplano | 0.04769 | 0.04127 |
| madagascar_western_dry | 0.04134 | 0.04631 | | scandinavian_taiga | 0.05402 | 0.04886 |

Skill lives in **managed-water and fire-driven systems** and is absent or reversed in
**rainfall-driven, cold-wet and montane** ones — the same regional structure Part 393 reported.

**This is the chapter's real limitation, and no rival changes it.** We beat every leak-free published
model at 12-month lead; we barely beat climatology. Both are true, and a write-up stating only the
first will not survive a reviewer recomputing the second.

### Why the forecast is weak — measured, not assumed

Three independent measurements here say **the drivers are not usefully forecastable at a one-year
lead**:

1. McPhillips's oracle gap: perfect knowledge of precipitation and VPD is worth **0.00206 MAE**,
   about 8.3% of climatology's error.
2. The Kraft LSTM's **climatology-driver arm beats its own lag-12 arm** — the long-run average is
   more useful than last year's actual weather.
3. Both rivals' honest arms sit far below climatology, despite clean climate inputs.

That is the project's founding premise — *forecast NDVI when the drivers are unforecastable* —
measured rather than asserted.

---

## 7. Three errors made and caught during this work

**7.1 The McPhillips strawman.** My first implementation fed the GP *instantaneous* monthly precip
and VPD; the paper *accumulates*. On `drakensberg_lesotho` this produced a near-flat predictor — SD
**0.0137** against a truth SD of **0.1257**, month-of-year variance share **0.000** against 0.889.
**The tell was that its ORACLE arm scored worse than its climatology arm, which is impossible.**
Trailing 3- and 12-month accumulations fixed it: SD → 0.1083, seasonality → 0.892, MAE 0.109 →
0.0418. The first run is retracted in full.

**7.2 An information mismatch.** Part 417 reported "their oracle beats us" as a defeat. It compared
their *cheating* arm to our *honest* one. Matched properly — their oracle against our nowcast — we
win. Retracted in Part 418.

**7.3 An uncalibrated rival.** The Kraft LSTM was first scored with no local calibration while both
other models are locally calibrated by construction. Diagnostics showed it was tracking fine
(correlation 0.587, up to 0.94; SD ratio 0.94; mean |bias| 0.0201) and simply unanchored. A per-cell
linear map fitted on 2017–2019 improved it enormously — monthly oracle **0.09109 → 0.04658** (−49%).
The calibrated numbers are the ones reported.

*All three were caught by a sanity check that should have been impossible to fail, not by reading
the code.*

---

## 8. Caveats

1. **Fixed, deterministic split — by design.** Training and test sets are constant: the same cells,
   the same rows, every run. Two runs of one configuration are the same experiment, so any
   difference between configurations is attributable to the configuration rather than to a draw.
   Uncertainty is quantified by bootstrapping over **regions** and by reporting every region
   individually, never by seed-to-seed spread. The 1,625 LSTM training cells are recorded in
   `train_cells.csv`.
2. **Kraft is doubly handicapped** — land cover removed by our ban, and it is a global model
   competing against two locally-calibrated ones (§3).
3. **McPhillips deviations:** monthly rather than annual-peak target; 44 global regions rather than
   Four Corners; RBF + white-noise kernel of our choosing, because MDPI blocks automated access to
   the published kernel specification.
4. **The chapter's real weakness is not the baselines** — it is §6.
5. **Test cells are a ~50% subsample** per region, fixed in advance for compute.

---

## 9. Out of scope: the annual aggregate

An annual-mean comparison was run on all 44 regions at both information tiers (Parts 419–424) and is
**excluded from this report on scope grounds**: the architecture is monthly-native, and the annual
figure is a derived average of twelve monthly predictions rather than a target it was built to
optimise.

Recorded so the answer to *"did you try annual?"* is documented rather than absent: **we win the
annual nowcast tier** (anomaly R² +0.3217 vs the calibrated LSTM's +0.1260) and **lose the annual
12-month forecast tier** (+0.0256 vs +0.1134). The mechanism was measured, not guessed — our monthly
errors are systematic (56.6% survives twelve-month averaging) while the LSTM's are noisy (46.9%), in
38 of 44 regions, so averaging cancels its error and preserves ours.

---

## 10. What a reviewer should attack

1. **"Your forecast barely beats climatology."** True — +0.0073 anomaly R², 24 of 44 regions. This
   is the honest weakness and §6 leads with it rather than hiding it.
2. **"You crippled Kraft by removing land cover."** True, and conceded in §3. The defence is that
   the ban is the chapter's premise, and the rival was given a local calibration to compensate.
3. **"You only reimplemented two of the published models."** Fair; §2 says which others exist and
   why each was excluded. The exclusions are principled (leaks) or structural (not gridded
   forecasters), not arbitrary.
4. **"Why is the proxy-free constraint interesting?"** The strongest conceptual challenge. §2 is the
   answer: every operational product and nearly every published forecaster reads NDVI, so a
   proxy-free model is the only kind deployable where NDVI is unavailable or untrustworthy.
5. **"You excluded the annual comparison after running it."** Answered in §9, with its result.

---

## 11. Reproduction

```bash
py -3.9 -u ndvi_mcphillips.py --step=fit
py -3.9 -u ndvi_mcphillips.py --step=score
py -3.9 -u ndvi_kraft.py --step=train --doncells=25 --maxseq=400000
py -3.9 -u ndvi_kraft.py --step=predict
py -3.9 -u ndvi_kraft.py --step=calib
py -3.9 -u ndvi_kraft.py --step=score
```

| artefact | path |
|---|---|
| McPhillips code / output | `ndvi_mcphillips.py` · `D:\run89full\mcphillips\` |
| Kraft code / output | `ndvi_kraft.py` · `D:\run89full\kraft\` |
| our forecast predictions | `D:\run89full\conformal_fc12\` |
| our nowcast predictions | `D:\run89full\conformal\` |
| three-way table | `D:\run89full\kraft\scores_3way_monthly.csv` |
| LSTM training cells (fixed) | `D:\run89full\kraft\train_cells.csv` |
| donor/test split | `D:\run89full\ndvi_split.txt` (89 TRAIN / 44 TEST) |
| experiment log | `EXPERIMENT_SUMMARY.md`, Parts 417–425 |

---

## Summary for a reader in a hurry

Every operational vegetation product and almost every published vegetation forecaster reads NDVI or
a direct derivative as an input. Two published models do not, and both were reimplemented: a **local
per-cell Gaussian process** (McPhillips 2026) and a **global LSTM** (Kraft 2019) — the first
genuinely trained machine-learning rival this project has faced.

On the monthly target, across 44 held-out regions and 4.4M cell-months, our architecture **wins both
information tiers on MAE and on both forms of R²**. Our nowcast reaches **+0.2930 anomaly R²**
against a best rival of **−0.3347** — below climatology — and beats McPhillips's *oracle*, an arm
that reads the future, in **44 of 44** regions.

The honest limit: our 12-month forecast sits at the climatology floor (**+0.0073** anomaly R², 24 of
44 regions). Three independent measurements here explain why — climate drivers are not usefully
forecastable a year ahead — which is the premise the chapter was built on, now measured. **The
nowcast, not the forecast, is what this chapter should lead with.**
