# Round 3: questions after reading PROJECT_HANDOFF.md

**Date:** 2026-09-24
**What I did:** I read the whole handoff (1,748 lines), then checked it against the code, the logs
and the data. Nineteen read-only checkers went through it section by section. Each finding was then
handed to a separate skeptic whose only job was to answer it from the source or knock it down.
Anything the files could answer was dropped. What's left below is either **your decision** or **a
place where the handoff and the code disagree**. Every item points at a file and line I (or a
checker) actually opened.

**How to answer:** reply with the question number and a letter, e.g. `A1 a, A2 b, C1 a`. One line
each is enough. My pick is marked **← my pick**, with the reason. If you skip something, I hold it;
I won't guess.

---

## ATTENTION: read these four first

1. **The PM2.5 full run is stopped, and the restart waits on section A.** You chose "kill, fix,
   restart". I stopped it at 04:38, while it was still building the tree bank, so nothing was lost.
   The disk bug is fixed and tested (details in section 0). But section A found things that change
   *what* the run computes: your annual-column lag isn't in the code, nine "test before trusting"
   satellite columns and fourteen "frozen" snapshot columns are in the model, and AMO is a made-up 0
   for 11 of the 48 test months. **Restarting before those are decided would repeat a multi-hour
   run.**
2. **Coral's forecasts use survey labels from after the forecast is issued** (C1). I checked the
   code myself: `adaptation.py:2020`. The "keeps ~80% of its skill at 12 months" and NOAA DHW
   ladder results (handoff 10.2, "the strongest single result") are not true forecasts as built.
3. **Coral's pre-registered test came out against the headline pool** (C2). Your own rule, written
   before running, says `full` must not be the headline. Every coral number in the 12-cell table
   uses `full`.
4. **The PM2.5 split picked 8 test regions using 2020–2023 results** (B1). The fire-balance rule
   chose them by how much burned area helped in the scoring years. Nothing is running now, so this
   is the cheapest moment to decide.

---

## 0. What changed today (no answer needed)

| | |
|---|---|
| **Run** | `pm25_adaptation.py --npd 100` (started 02:56) stopped at 04:38 on your instruction. It was still in the bank build, and no output had been written. |
| **Disk bug, now FIXED in `pm25_adaptation.py`** | `drop_cache()` tried to delete each tree-matrix file while the program still had it open. On Windows that fails, and a bare `except: pass` hid the error, so no file was ever deleted. I reproduced this on tiny files. The run would have died right after `LAYER ADOPTS`, needing ~104 GB with 40.7 GB free. **Fix:** close the file, then delete it, and log a warning if the delete still fails. Each matrix is also dropped as soon as the last arm that uses it is done, so only **one** is on disk at a time (18.4 GB inner, 22.5 GB test). The contract check now runs right after `base`: same computation, moved up so base's matrix can be freed. Nothing scientific changed. A replay on small files showed at most one file at a time and none left at the end, and the file compiles. The original is kept at `%TEMP%\...\scratchpad\pm25_adaptation_ORIG.py`. |
| **Disk cleanup (for you to run)** | 7 temp files, 18.8 GB, each named after a process that is no longer running (the killed run's 18.4 GB leftover plus the smoke leftovers). I can't permanently delete files myself. The command is in my chat message. D: goes from 40.7 → ~59.5 GB. |

---

## A. BEFORE THE RESTART: each of these changes what the run computes

**A1. Your one-year lag for the annual columns isn't in the code.** Your ruling (Part 539, handoff
6.6) is to feed the ~25 annual human and land-use columns (GDP, night lights, population, LUH2,
fertiliser, livestock, conflict…) one year late, counted from the forecast origin. That's one year
at nowcast. The code only lags EDGAR (`pm25_architecture.py:146`). Everything else joins the
*same* year (`:103-116`), so a January row already sees that whole year's value. The driver screen
did the same. Adding the lag leaves 2002 with nothing to lag from. The code fills gaps with 0
(`:192`), so 2002 would get 25 fake zeros.
- (a) Add the lag and **drop 2002** from training and calibration (−12 of 216 months per cell).
  **← my pick.** One move fixes three 2002 problems: this lag hole, EDGAR's fake zero emissions in
  2002, and the two water-balance columns that are 42% and 92% empty in 2002 (they're zero-filled
  while their 24-month sibling was banned for the same thing).
- (b) Add the lag, and let 2002 use its own year's value. That's a small look-ahead in training
  rows only, disclosed.
- (c) Restart without the lag and disclose it.

**A2. Nine "test before trusting" satellite columns are in the model.** `pm25_ban.py:53-72` says
NDVI, EVI, day and night LST, albedo, GPP, cloud frequency, solar radiation and `era5l_ssr` "MUST
BE ABLATED" before they're trusted. `pm25_ban.py:57-59` also warns that cloud frequency can
literally *be* smoke. The code keeps them (`DROP_CONDITIONAL=False`, `pm25_architecture.py:64`),
and no arm tests them. The handoff's feature table (8.8) counts them as removed. The real count is
164 − 29 banned + 7 = **142**, and the handoff's own table sums to 141. Also, **eight MODIS annual
land-cover columns** that are on no list have the same retrieval problem: tree cover, bare, herb,
land-cover class ×2, cropland, shrub, snow. The MOD44B year also runs to March of the next year
(`defo_ban.py:28-29`).
- (a) Keep the 9 in the headline, and add a "neutralize these" arm.
- (b) Drop the 9 from the headline (133 features), and run "with them" later as the ablation.
  **← my pick:** the headline should be the version whose leak status is settled.
- (c) Run both and report both (~2× time).
- *Also:* should the 8 MODIS land-cover columns join the ablate list? yes / only the MOD44B three /
  no.

**A3. The 14 columns you "froze" for defo are in the PM2.5 model.** `defo_ban.py:76-97` bans them as
post-window snapshots:
- 7 `dist_*` columns (power plants, thermal plants, coal mines, oil/gas wells, dams, reservoirs,
  protected areas), with sources dated as late as **2026**;
- `built_surface_fraction`, held at its 2018 value through 2023 (identical cell by cell in thar);
- 6 livestock columns, which are rescaled rather than observed after 2021.

`pm25_ban.py` never mentions them. **Power plants, coal mines and wells are direct PM2.5 sources**,
so a 2019 training row "knows" about a plant built in 2022.
- (a) Drop all 14 from the PM2.5 headline, same as defo. **← my pick.**
- (b) Drop only the 7 `dist_*`, and keep built-up and livestock with a disclosure.
- (c) Rebuild the `dist_*` columns at a pre-2020 date from the date fields the sources already
  carry (a re-ingest).
- (d) Keep all 14 and disclose.

**A4. EDGAR: in or out?** The screen said EDGAR "does not earn its place", and you wanted one retest
under the real model. The run has EDGAR on (`USE_EDGAR=1`) with no with/without arm, so it can't
be that retest. The screen's verdict is also weaker than it reads, for two reasons. It measured
EDGAR on top of GDP, night lights and population at lag 0, which are its closest stand-ins. And
its penalty was stuck at the grid edge (see F).
- (a) Keep EDGAR in, and add an "EDGAR neutralized" arm as the retest.
- (b) Take EDGAR out of the headline (137 features), and test it as an add-on arm. **← my pick.**
- (c) Keep it in with no retest.

**A5. AMO is blank for Feb–Dec 2023 and gets filled with 0.** That's 11 of 48 test months (23%) with
an invented value, in every region (91.7% null in every 2023 file checked). SPEI was dropped for
exactly this gap; AMO wasn't.
- (a) Drop AMO, the same rule as SPEI.
- (b) Re-fetch AMO 2023 from its source (a tiny public index).
  **← my pick if the source has 2023; otherwise (a).**
- (c) Carry January forward.
- (d) Keep the 0 and report 2023 separately.

**A6. The inner decision window is easier than the real test, in two ways.** This is the window
that picks the arm and penalty: fit up to 2016, score 2017–19.
1. The "normal" climatology fed to the router, which is an unpenalised input, is averaged over
   2002–2019. So 3 of its 18 years are the very years being scored (`pm25_adaptation.py:306-310`).
2. The donor trees learned 2017–19, and the global climate-index columns (ENSO, PDO, AMO…), which
   are one value per month everywhere, let a tree recognise those months.

Fire's closed result has both (`adaptation.py:2322-2326`), and defo has #2. Fire's inner pass
also picked the top edge of its penalty grid.
- (a) Accept both, and disclose them as a caveat all problems share.
- (b) Fix #1 in PM2.5 now (build the climatology from ≤2016 inside the inner pass; cheap), and
  disclose #2. **← my pick.**
- (c) Fix both (a separate ≤2016 bank, roughly double the bank cost).
- (d) (b), plus the same fix in fire and defo and a re-run of their decisions.

**A7. What counts as "Type 1 (untooled)" for PM2.5?** The test pass scores every arm at the
*adopted* arm's penalty. If `base` wins at a new penalty, Type 1 and Type 2 are the same model,
and the gain from the penalty sweep itself (3.4075 → 3.3217 at smoke) never shows.
- (a) Base at fire's inherited penalty, i.e. no adaptation at all.
- (b) Base at its own best inner penalty.
- (c) As now.
- (d) Report (a) and (c) together. **← my pick:** it reuses a matrix already on disk, so it's
  nearly free.

**A8. The `log` arm isn't a fair test of a log link.** It fits log(PM2.5), but its inputs are on
the raw scale: the climatology in µg/m³ and tree predictions made on the raw target. At smoke it
wrecks bolivia (MAE 9.71 vs base 6.32) but wins in brittany (2.14 vs 2.29). So "the layer looked at
log and rejected it" doesn't show the Tier-1 blind spot is harmless. Separately, the "Taylor p ≈ 2
means log link" argument doesn't hold. That estimator reads the *shape* of the target's
distribution: any log-normal gives ~2.15, and the gamma law it cites gives 1.24. Defo, fire and
coral all read about 2 too.
- (a) Rebuild the log arm with log-scale climatology as its input (no new bank), and delete the
  Taylor argument. **← my pick.**
- (b) Keep it as built, and write only "the log arm as built lost".
- (c) Drop the log arm.

**A9. The penalty grid: what to add when it's extended.** The last smoke also sat at the **bottom**
of the ratio axis (rho 0.25), which 12.1 doesn't mention. The handoff's reason for the edge is also
backwards. The smoke banks (96–320 trees) were *narrower* than fire's (~9,000), and the
column-count law predicts a *smaller* penalty for a narrower bank, not a larger one. A top-edge pick
more likely means "the trees add nothing and the router falls back to intercept + climatology".
That fits base losing to guess-normal in every smoke run.
- (a) Extend the ratio axis down (to ~0.06).
- (b) Add an explicit "trees off" candidate, so an edge pick is reported as "the layer declined the
  trees".
- (c) Both. **← my pick.**
- (d) Levels only, as 12.1 says.

**A10. Seeds.**
- The bank uses fire's shipped seed formula (`pm25_adaptation.py:339,342`), which is inherited,
  but nothing labels it that way as your rule requires.
- The region bootstrap uses 2,000 seeded draws (`:546`). The shipped layer uses a seedless
  leave-one-region-out jackknife instead (`adaptation.py:530-537`).

Options:
- (a) Allow both, each labelled.
- (b) Allow the bank with a label, and switch the confidence interval to the jackknife.
  **← my pick:** it adds no new seeds.
- (c) Neither: deterministic bagging too. That changes every tree and every number.

**A11. Hit-rate for PM2.5 needs a margin in µg/m³**, the way NDVI has ±0.02. The code counts "right
side of normal", which guess-normal can't be scored on. At smoke, within ±2 µg/m³ the model gets
0.496 and guess-normal 0.518. Pick one:
- (a) ±2 µg/m³ (ACAG's own error floor), with the sign-hit as a bonus. **← my pick.**
- (b) ±3.
- (c) Within 10% of the true value.
- (d) Sign only.

**A12. Scoring covers 100 cells per test region (2,000 cells, every region weighted equally).** Is
that the final evaluation? The handoff's "yakutia is 19% of test rows" describes whole regions, not
what gets scored.
- (a) Yes, final, and say so in the paper. **← my pick for this run.**
- (b) Raise it to 300 per region. That needs chunked matrices: 300 per region makes a 67 GB test
  matrix, which won't fit.
- (c) Later, score every cell of the 20 regions with the fitted model, in chunks.

---

## B. The PM2.5 split and its claims

**B1. The fire-balance rule used test-window results.** The 15 "fire-signal" regions are exactly
the ones where burned area raised the **2020–2023** pattern-R² in the full screen
(`pm25_split_design.py:40-46`, `D:/pm25_screen.csv`). The rebuild then forced 8 of them into test
(`pm25_split_rebuild.py:82-104`). Measured: the 20 test regions hold **55%** of the whole panel's
burn gain (mean +0.0160 in test vs +0.0024 in donors, 6.7×). Also, one test region
(`bolivia_beni_savanna`) is a place where burned area clearly *hurts*, and the rule counted gains
only.
- (a) Keep the split, disclose it, and make no "the smoke driver transfers" claim on those 8.
- (b) Re-score the screen on ≤2019 only (~55 min, ridge), rebuild the fire list, and keep the split
  if the same 8 come out; disclose if not. **← my pick:** nothing is running, so it's cheap now.
- (c) Rebuild the split now.

**B2. "A donor at median 716 km" is region centre to region centre.** Measured edge to edge (from
the region boxes), the median is about **180 km**, and 3 test regions touch a donor region. Your
causal result (Part 533) is about distance to the nearest *training cell*.
- (a) Keep 716 km, labelled "centre to centre".
- (b) Per-cell distance to the nearest donor training cell, computed from coordinates (no re-run).
- (c) Both. **← my pick.**

**B3. "Bad regions are SHIFTED, not failed" comes from 6 smoke regions.** On all 127 regions, taking
the offset out turns only 9 regions from negative to non-negative, while 20 go the other way. In at
least 42 regions the ridge already predicts part of the test-window level.
- (a) Restate it narrowly: "true in 6 smoke regions, not panel-wide", with the 127-region numbers.
- (b) Withdraw it.
- (c) Hold the wording until the real architecture's numbers exist, then decide. **← my pick.**

**B4. The "MEASURED" uncertainty table (thar 16.8%, Tibet 98.7%, mean 32.4%) is ONE month (Jan
2002).** It came from a scratch script in an old session's Temp folder (`how_model_is_it.py`), which
calls itself "an indication, not the final number". The split's rationale leans on it.
- (a) Relabel it "one-month indication", and firm it up with more months (~50 MB each, anonymous S3,
  no big download). **← my pick.**
- (b) Download the full 14.8 GB layer first.
- (c) Drop the claim.

---

## C. The closed problems: what the paper can claim

**C1. ATTENTION: coral forecasts see labels from after the issue date.** At every lead only the
*features* are lagged. The calibration pool still admits any same-ecoregion survey dated before the
**target** (`adaptation.py:2020`: `dat < dat[gi]`, with no lead subtracted; I read this myself). A
read-only check on the 2,168 test rows at a 365-day lead found:
- 39% of each row's nearest candidates are labelled surveys taken *after* the forecast was issued;
- 77% of rows have at least one.

So the 1/3/6/12-month coral cells, and the DHW ladder, set a model that sees future labels against
DHW, which gets only old heat.
- (a) Limit the pool to surveys dated ≤ the issue date, and re-run coral's 4 leads plus their folds.
  **← my pick.**
- (b) Relabel them "feature-lagged nowcasts with live surveys", and drop the 10.2 framing.
- (c) Something else.

**C2. ATTENTION: the pre-registered coral test failed for `full`.** Your rule (`adaptation.py:74-88`):
"If rollout ≈ strict … full must not be the headline." Result on identical rows (Part 525
amendment):

| pool | MAE |
|---|---|
| full | 5.93 |
| rollout | 11.73 |
| strict | 12.37 |

So rollout ≈ strict. Part 525 argues `full` is *causal*, which is true, but that answers a
different question than the one registered. Without test-era labels, coral **loses to NOAA DHW** at
nowcast (corr² 0.097 vs 0.421). The rivals were also barred from test-window rows
(`rivals.py:12`), while `full` takes 47% of its neighbours from them. Which coral pool goes in the
paper?
- (a) `full`, with the registered outcome reported and argued, plus giving the rivals the same
  earlier-label access so the comparison is fair.
- (b) `rollout` as the headline, dropping the "strongest result" framing.
- (c) Both side by side, no single headline.

**C3. Which coral number is the headline?** The handoff (7.2) names MAE **4.493**, but that is the
Part 417 pilot: 730 rows, averaged over 3 seeds, leaky mask. Its split line is also inverted (it's
20 **donor** / 74 held-out, not 20 test / 93 donor). The other candidates:
- 5.906: dbl split, cut 2005, `full` pool (the 12-cell table).
- 5.56: main spatial split, leak-free mask. **CORRECTED, see G1.** This label was wrong: 5.56 is
  the old `own_earlier` mask, which admits donor rows of any date. The date-safe number on the same
  split is **5.725**.

(C2 applies to both.) Pick: (a) 5.906 (b) 5.56 (c) both (d) other.

**C4. Two or three problems auto-configured?** The handoff says both "coral declines, it's two"
(1.2, 5.5, 12.5) and "all 12 arms layer-decided" (10.1). The code and log say coral *is* decided,
on held-out **donor** ecoregions (`adaptation.py:570-577, 771-773`; the log says `ADOPTED:
link_corrector`). But the votes are weak (3/5 at nowcast, 2/5 at 3 and 12 months), and the nowcast
was decided on *strict*-pool folds and then scored on `full`.
- (a) Three, with the votes disclosed on every coral row.
- (b) Two, with coral shown as "donor-fold decision, weak".
- (c) "Two on the unit's own history + one donor-only".

**C5. Which selection rule does the paper declare?** The 12-cell table mixes two rules:
- **MAE** picked all 5 coral cells, fire now and defo now;
- **corr²** picked fire 1/3/6/12 and defo 1-year.

The rule changes the arm only at fire 3 months and 6 months. Your standing rule says don't select
on MAE for mostly-zero targets, and defo now was picked on MAE.
- (a) Disclose it as-is.
- (b) corr² for fire and defo, MAE for coral and PM2.5, re-read from logs already saved (no
  retraining). **← my pick.**
- (c) MAE everywhere.

**C6. Defo nowcast: which arm shipped?** The table has `link` (0.005540). With its full candidate
set the layer actually adopted `link_corrector` (0.005434): `D:/adaptation/defo/_addarm.log`,
Part 516. `rivals_final.py` read an older log that lacked that arm.
- (a) `link_corrector`: regenerate the row and its W/T/L.
- (b) `link`, because link_corrector was dropped on purpose (please give the reason).

**C7. Defo framing: please confirm your ruling still holds** (not reopening it, just checking the
facts under it). The handoff says the "loss" verdict came from corr² alone. Part 530 actually
weighed six measures (R², pooled and per-region corr², hit, lift, wcorr2) and said "write it as a
loss". Also, predict-zero's MAE (0.005396) beats both models, and lgbm_tweedie wins R² (+0.0291 vs
+0.0168). The +0.000524 MAE test exists only in a session transcript, not in the log.
- (a) Ruling stands: "not a loss". I'll log the test.
- (b) Say "mixed: wins MAE, loses R² and rank skill".

**C8. How should the paper describe Tier 1?** The readings are printed, but no adapter acts on them.
`tier1_check` only compares unit and link. Defo's own run printed "hurdle **no**", coral ships no
hurdle, and PM2.5 ignores its reading entirely. So "hurdle 3/3" and "PM2.5's hurdle-no is the first
time the layer said no" are both wrong.
- (a) Describe it as an **audit** that checks the configuration rather than setting it, and fix
  those lines. **← my pick.**
- (b) "Derived" for unit and link only; the hurdle moves to Type 3 (manual).
- (c) Wire it so every adapter uses the reading, then re-audit.

**C9. What is Type 2's candidate set?** The handoff says {base, corrector, evt, both}.
`adaptation.py:3185-3188` prints that EVT "is NOT wired"; what actually ran is link × corrector.
- (a) Describe what ran, and drop EVT from the description. **← my pick.**
- (b) Wire EVT everywhere (days of work).
- (c) EVT for PM2.5 only, labelled as an extension.

**C10. Which results are the paper's deliverables for fire and coral?** If it's the 12-cell table,
the "2 forced / 2 chosen on test" ledger (12.5 #4) is wrong. Fire's test-chosen 5% gate isn't in
it, and coral ships the corrector its own design file excluded.
- (a) The 12-cell table.
- (b) The older variants (fire cascade @5%, coral 4.493).
- (c) Both, labelled.

**C11. Which NOAA comparison?** 10.2 uses *lagged* DHW (NOAA's nowcast rule fed old heat), not
NOAA's actual 4-month Outlook. The Outlook was benchmarked before (Parts 456-457), but on the old
leaky pipeline.
- (a) Lagged DHW, labelled as such.
- (b) The real Outlook, head to head (re-run on the leak-free path).
- (c) Both.

**C12. Rival list.**
1. On coral, `hgb_l1` is a real model (not flat; lift 2.0×). Does your "exclude hgb_l1" ruling
   apply there too? yes / no.
2. CatBoost is listed as a legitimate rival but was never run. (a) add it (b) remove it from the
   list.

**C13. Where is the log for Parts 1–399?** The NDVI closed doors cite Parts 130–131, 243, 365 and
371, but `EXPERIMENT_SUMMARY.md` (and its .bak) start at Part 400.
- (a) It's at \<path\>.
- (b) Lost: cite from notes with that caveat.

---

## D. Things only you can supply

**D1. The EAC4 circularity control.**
1. EAC4 lives on the Copernicus **Atmosphere** Data Store, which has its own licence. Only you can
   click it; your existing token should then work. Accepted / will accept / not yet?
2. EAC4 also takes in **satellite AOD**, the same signal ACAG is built from, so it isn't "pure
   meteorology". Still want it as the control? (a) yes, described as "no ground monitors" (b) look
   for a cleaner control first (c) skip it and argue the point in words.

**D2. ERA5 is NOT blocked by an account.** Your `~/.cdsapirc` exists, and ERA5 was downloaded in
July (`presplit_cc/fetch_wind_dir.py`).
- (a) Fetch the inversion proxy only (t850 − t2m). This needs the pressure-levels licence click if
  you haven't done it.
- (b) BLH + the inversion proxy, with BLH ablated.
- (c) Neither for now.

**D3. Monitor-density layer (OpenAQ).**
- (a) You register a free API key.
- (b) I use their anonymous archive (slower).
- (c) Skip it and state the limitation.

Monitor list as of 2019, or year by year?

**D4. What plays DHW's role for PM2.5?** Operational CAMS PM2.5 forecasts only reach about 5 days,
so nothing operational exists at 1–12-month leads.
- (a) EAC4 as a nowcast baseline, fitted on donors only.
- (b) No domain baseline: ML rivals + climatology, and say why.
- (c) CAMS short-range forecasts averaged to monthly.

**D5. PM2.5 forecast ladder: when and how big?** Fire's full four-arm set needs ~45 GB for one arm.
- (a) After the nowcast headline: leads 1/3/6/12 with the two single-bank arms only.
- (b) All arms at half width.
- (c) Leads 1 and 12 only.
- (d) Skip it for PM2.5.

---

## E. What I'll do myself unless you say no

1. **Make the adapter keep a record.** Right now its verdict exists only in the console. I'll add a
   log file, save the 84-candidate inner table, the adopted arm and penalty, the Tier-1 reading and
   the fallback counts, plus per-phase timings. The handoff's "under 40 min" rule can't work: its
   own 1.75 s/cell benchmark × 2,000 cells is 58 min of reads alone. I'll also add per-region and
   per-year pattern-R², and always print corrector − placebo. The printed pattern-R² is currently
   pooled, which doesn't remove the region-signed shift it exists for.
2. **Run the smoke first**, with the output logged, before any full restart.
3. **Log the missing Parts 541+** (~15 PM2.5 results since Part 540 aren't in the log), and copy
   `how_model_is_it.py` into the project before Temp is cleaned.
4. **Mechanical fixes:**
   - Recount W/T/L without persistence and `hgb_l1`.
   - Guard the EDGAR and GFED `--smoke` modes, which write into the real output folders; EDGAR's
     did once, on 09-23.
   - Stop PM2.5 writing its Tier-1 and corrector lines into **fire's** log. `pm25_adaptation.py:91`
     sets `--problem fire`, so they land in `D:/adaptation/fire_full/_adaptation.log`.
5. **Handoff 12.3 reading debts:** the mdsoar EDGAR v4.3.1 string, Hammer 2023, and the 2024
   Correction.
6. **One question for you: the corrections in section F.** Should I (a) edit `PROJECT_HANDOFF.md`
   in place, or (b) keep them as a separate errata list? **← my pick: (b)**, so your text isn't
   rewritten under you.

---

## F. Handoff corrections (facts, no answer needed)

| Handoff says | Source says |
|---|---|
| D: ~59 GB free, C: ~21 GB | D: 40.7 GB (≈59.5 after the cleanup), C: 7–12 GB |
| 142 features = 134 leak-free + 7 | 164 − 29 banned + 7. It **keeps** the 9 conditional columns and drops the 9 incomplete ones (A2). 134 + 7 = 141 |
| 179,182 cells lost (7.83%) | **254,264 (11.1%)**. 75,082 in-grid cells were dropped by the whole-region rule. tierra_del_fuego is cut at the *south* edge |
| EDGAR download 1.12 GB, resumable | **~36 GB** (TRANSPORT zips are ~4.2 GB each). Not resumable. `--smoke` overwrites real output |
| EDGAR's gap is 2023 (flagged) | The real gap is **2002** (all zeros after the lag). `edgar_carried` is never used |
| Driver screen: ridge on 78 monthly columns | ~103 columns, including the 25 annual at lag 0 and SPEI median-filled. Penalty at its grid edge in 113/127 regions. No predictions or per-year output saved |
| 15 of 127 regions clear ±0.01 | 17: 15 gains + **2 losses** (idaho, and **bolivia, a test region**) |
| W/T/L = our wins/ties/losses, per region, on MAE | It counts **rivals**: rival wins / can't tell / rival loses, on per-unit **corr²**. Coral "0/1/16" means we beat 16 |
| Poisson never measured at full scale (defo) | **Part 527 measured it** on identical rows: MAE slightly better, R²/corr² slightly worse. The same false line is in `adaptation.py:427-428` and in my memory notes. Your ship-on-squared_error ruling is untouched |
| Coral: 20 test / 93 donor; loses to predict-zero on 91% | 20 donor / 74 held-out. 91% is from the pilot; on dbl2005 it's 46.6% |
| Coral: deep learning tested, dead | Rejected from the literature, never tested |
| Fire's Type 2 = {base, corrector, evt, both} | EVT never wired in any problem (C9) |
| Coral's layer declines | It decides on held-out donor folds (C4) |
| GFED "leak-checked", no fire variable in the GWR | The ingest's own docstring (`gfed_burn_ingest.py:22-27`) says **physics-upstream, the paper must say so**: GEOS-Chem runs on GFED4 (same MCD64A1 burned area), with a second hop into the OC predictor. The time-shift placebo can't separate real smoke from the simulation's own fire input |
| ERA5 BLH needs a CDS account | Account and token exist (D2) |
| Section 13 commands reproduce the results | Fire needs `--calib=strict`, coral `--cut=2005`, forecasts `--lead=N` and `--select=corr2`. The ACAG command omits `--full-only`, and `--uncertainty` has no assemble step |
| `USE_LAG` is ready for the forecast ladder | It shifts by **rows**, not months, across target gaps, and would also delay EDGAR a second time. Needs a fix before the ladder |
| Parts 520–521 missing | They're in `FIRE_EXPERIMENTS.md:2666, 2831` |
| The (1.0, 0.5) contract assertion guards the sweep | It only checks that two code paths agree, on the base arm only |

---

## G. Your answers (2026-09-24) and my follow-ups

**Recorded decisions:**

| | Decision |
|---|---|
| A1 | a: lag the annual columns, drop 2002 |
| A2 | b: drop the 9 conditional columns, plus all 8 MODIS land-cover columns (`cropland_fraction` and the shrub column are MCD12Q1 slices, `defo_ban.py:37-38`, so all 8 count) |
| A3 | a |
| A4 | b |
| A5 | b, falling back to a |
| A6 | b |
| A7 | d |
| A8 | a |
| A9 | c |
| A10 | b |
| A11 | a (±2 µg/m³) |
| A12 | a |
| B1 | b |
| B2 | c |
| B3 | c |
| B4 | a |
| C1 | a |
| C2 | c |
| C3 | b → **see G1** |
| C4 | c |
| C5 | b |
| C6 | a → **see G2** |
| C7 | b |
| C8 | a |
| C9 | a |
| C10 | a |
| C11 | c |
| C12 | hgb_l1 stays on coral; remove CatBoost |
| C13 | b |
| D1 | keep EAC4, described as "assimilates the same satellite AOD but zero ground monitors" |
| D2 | b |
| D3 | b, year by year |
| D4 | a nowcast / b ladder |
| D5 | a |
| E1-E6 | all approved; errata as a separate file |

**Follow-up questions:**

**G1. My C3 wording was wrong.** 5.56 isn't the leak-free number. I checked the saved predictions,
same split and same 3,042 rows:
- `D:/adaptation/coral` (old `own_earlier` mask): link_corrector **5.5617**. That mask lets donor
  rows of **any date** into the pool (`adaptation.py:1591-1595` says so).
- `D:/adaptation/coral_full` (`--calib=full`, date filter on every row): link_corrector **5.7251**
  (base 5.7803).

Options:
- (a) Headline 5.725, with the C2 caveat. **← my pick.**
- (b) Show both, labelled.

**G2. C5 and C6 interact.** C5 b says defo is chosen on corr². C6 a says use the full candidate set.
Together they mean re-deciding the defo nowcast **on corr² over all four arms**, and that may not
land on link_corrector (link_corrector was the MAE pick). The corr² inner reading for link_corrector
was never logged, so this may need a re-run of defo's inner decision.
- (a) Re-decide on corr² over all four. **← my pick.**
- (b) Keep link_corrector for the nowcast only.

**G3. A6 follow-up.** Fire has the same climatology leak (#1). By your own comparability argument,
fixing it only in PM2.5 makes PM2.5's inner surface differ from fire's.
- (a) PM2.5 only, and disclose it for fire; fire is closed. **← my pick.**
- (b) Fix fire too, and re-run its inner decisions (several hours).

**G4. B1 details.**
1. The ≤2019 re-score uses the new feature rules (A1-A4), a ≤2016 climatology, and a wider penalty
   grid (the old one hit its edge in 113/127 regions). **← yes, my pick.**
2. If the rebuilt test list differs from the frozen one, we adopt the new split and run everything
   on it. Your condition that the same eight come out again implies yes; please confirm.

**G5. C1 and C2 together.** At the four coral leads, run **both** pools: `full` limited to ≤ issue
date, and `rollout`. Then every coral row can be shown side by side. Coral runs are short.
**← yes, my pick** / full only.

**G6. Two licence clicks only you can do.** I can't accept terms for you. Please accept:
1. the CAMS EAC4 licence on the **Atmosphere** Data Store;
2. the ERA5 **pressure-levels** monthly licence on CDS (needed for t850).

Tell me when both are done.

**G7. Where do BLH and the inversion proxy go?**
- (a) An add-on arm after the headline, matching A2's "headline = settled leak status".
  **← my pick.**
- (b) In the headline, with an ablation arm.

**G8. Downloads: your OK for this list.** I'll confirm the exact size before each one.

| What | Source | Size |
|---|---|---|
| AMO 2023 monthly | NOAA PSL text file | < 1 MB |
| ACAG uncertainty, 12 more months (Jan/Apr/Jul/Oct of 2005, 2012, 2019) | anonymous S3 | ~56 MB each ≈ 0.7 GB |
| ERA5 BLH by hour-of-day + t2m + t850 (grib) | CDS | ~4.2 + ~2.2 GB |
| EAC4 monthly PM2.5 | ADS, after G6 | ~0.1 GB |
| OpenAQ archive | — | I'll list it and report the size **before** downloading anything |

(a) all (b) all except ___.

**G9. The log arm's climatology (A8).** Should it be the per-cell, per-month **mean of log(PM2.5)**
**← my pick** (the normal in the space the ridge actually fits), or log of the existing raw-scale
normal?

**G10. Code review.** The A fixes touch scientific code, and your rule is that you write
signatures, I fill bodies, and you review.
- (a) I write them all and send **one diff for your review** before the smoke. **← my pick.**
- (b) You give me signatures first.

**Not a question:** the disk cleanup hasn't been run yet (D: still 38 GB free). The command is in
the earlier message.

**Plan once these are answered** (multi-hour steps as terminal commands for you):
1. A fixes + E1 bookkeeping → one diff for review.
2. Smoke, logged to a file.
3. B1 re-score → split check.
4. PM2.5 full run.
5. Coral C1/C2/C11 re-runs.
6. Parts 541+, the errata file, and the W/T/L recount.
