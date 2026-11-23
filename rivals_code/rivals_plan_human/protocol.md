# Human rivals (type 2): the uniform protocol

Written 2026-10-21 by the protocol designer. Status: PLAN ONLY. Nothing was downloaded, built, run or scored.
Scope: the rule set every human rival follows on all five problems. The per-problem rival lists, download needs and
times are planned by the other agents of this workflow; section 3 only shows how each known candidate enters.
Builds on: RIVALS_PLAN_COMMON.md section 3 (rules 0-19), D:/treeroute/rivals_build/SPEC_RIVALS.md (read only),
OWNER_RULINGS_2026-10-06.md sections Y (:136-145) and Z (:147-156). Engine paths are relative to
`C:\Users\<user>\Desktop\data set for reserch paper\engine\`.

---

## 0. Short version and must-reads

- A human rival is one of three kinds. **I (index):** a number that is not on the target scale (FWI, DHW, BAA, a
  risk score). **N (product on target scale):** already in target units (CAMS EAC4 PM2.5 in ug/m3). **M (method):**
  a published fitting recipe (per-cell SARIMA, rainfall-lag regression, Kraft LSTM, the REDD+ allocation).
- Every rival runs on the SAME saved test rows, leads, cuts, normals, metrics, guard and "beats" rule as the common
  board. Nearly all of it is reused from the common harness (read-only import, pinned by code hash).
- An index enters through a small, fixed set of calibration maps (isotonic or linear, raw or as an anomaly added to
  the normal). Each map is fitted on TRAIN rows only, per lead. The map is picked by inner-window MAE before any test
  score, then locked.
- Information parity is two timing rules read from the run (section 2, H2). A product that sees what our model
  cannot (for example same-month EAC4, which assimilates the target's own satellite AOD) is labelled
  "input-advantaged" and does not decide.
- A product that cannot cover some test rows is scored on the rows it covers. Ours is scored on the same rows. The
  coverage is fixed from the product alone, before any label, and locked.
- Results join the common board into ONE rival table with one schema (section 4).

**ATTENTION H-A1 - do not touch the common build.** The human tool lives in its own folders (section 1). It imports
`rivals.layout` and `rivals.harness` from D:/treeroute/rivals_build READ-ONLY and refuses unless their code hash equals
the signed one (ruling Z4: the rival Part is signed after Z2 is built). Build it only after that signature.

**ATTENTION H-A2 - the export is deleted after each common lead is scored** (RIVALS_PLAN_COMMON.md:157). The human
tool needs only keys, role flags, train `y` and the normals. Its first command copies those columns (with hashes) out
of the export BEFORE the owner deletes it. Otherwise a re-export costs hours (pm25 derive ~4.4 h).

**ATTENTION H-A3 - ruling D4 says EAC4 is "fitted on donors only"** (QUESTIONS_ROUND3_HANDOFF.md:377, :478). That
ruling came before LORO. The common board is now "gauged global" (ruling Y3 Q1 b). This protocol fits every
calibration gauged global for consistency. Owner confirms (HQ5).

**ATTENTION H-A4 - these candidates are not blind.** CEMS, CRW and the Kraft LSTM were scored before on other designs
(FIRE_CEMS_REPORT.md; CRW_BENCHMARK_REPORT.md; NDVI_BASELINE_REPORT.md). The Part must say so. Old numbers are history
only and are never paired with the new runs (common rule 19).

---

## 1. Where it lives and what is reused

| what | path | writes? |
|---|---|---|
| human tool code (build + tests) | `D:/treeroute/rivals_human_build/rivals_human/` | yes (new) |
| downloaded product files (owner commands only) | `D:/treeroute/human_products/<product>/<version>/` + `product_manifest.json` (file, size, sha256, URL, licence, download UTC) | yes (owner) |
| index tables (one per rival, run and lead) | `D:/treeroute/human_index/<pkg>/<run>/<rival>/lead_<L>.parquet` | yes |
| slim copy of the export | `D:/treeroute/rivals_human/<pkg>/<run>/slim/lead_<L>/` | yes |
| human board outputs | `D:/treeroute/rivals_human/<pkg>/<run>/` | yes |
| the ONE rival table | `D:/treeroute/rivals_table/<stamp>/` | yes |
| common harness, export, run folders, engine, packages | as today | NEVER |

- None of these roots is in D:/treeroute/registry/protected_roots.txt. Every write path is still checked with the
  engine's `Registry(...).assert_writable(path)` (runs/registry.py:195), as the common harness does (SPEC_RIVALS.md:58).
- **Reused read-only, never re-implemented:**
  - row roles, keys, normals per link (`nfit__<link>`, `ngd__<link>`), train `y`: the common export files
    (SPEC_RIVALS.md:64-83), checked by their manifest sha256 (harness.py:704);
  - links and clip: `layer.links.link_forward` / `link_inverse` / `clip_to_legal` (layer/links.py:84, :118, :261);
  - the guard: `rivals.harness.apply_guard` (harness.py:1989) = `layer.decide.n2_eligible` (layer/decide.py:290);
  - scoring: `report.metrics.score_table` (report/metrics.py:846), `metric_by_key` (:999), `_paired_contrast`
    (:1123), `contrast_tag` (:1097), `blocked_jackknife` (:1058), `mae` (:569), `corr2` (:604),
    `calibration_ratio` (:623), `anomaly_r2` (:580);
  - "ours" and its tie to the run: the logic of `harness.check_ours_against_run` (harness.py:2292);
  - strata, seen_during_design and per-programme tables: the logic of `harness._strata_tables` and `score`
    (harness.py:2259, :2330-2400).
- **New code (small):** the slim copy, the index-table checker, the calibration maps, the method runners, the coverage
  mask, the lock, the test-label reader of the human board, and the joiner.
- **Plug and predict.** The tool names no problem. Everything problem-specific sits in a per-product ADAPTER
  (dataset side, like a package ingest): it reads the product files and the unit coordinates and writes the index
  table. The adapter never reads a label.

---

## 2. The rules (H0-H19)

**H0. Identity.** The human board takes a run folder. It refuses unless the run fingerprint, `derived.json`, the
saved `test_preds.parquet` sha256 per lead and the nowcast band are the ones the common board used (read from the
common `board.json`). Same LIVE engine rule as the common board (SPEC_RIVALS.md:117, ruling Z1 for pm25).

**H1. The index table (the adapter's only output).** One parquet per rival, run and lead, keyed exactly like the
export: `unit, group, time, issue, lead`, one row for EVERY export row of that lead (refit, tune, inner, guard-fit,
guard, test). Columns:
- `x__<stat>` float64, one per pre-registered statistic (at most 3, for example ensemble mean / max / p90). NaN = not
  covered.
- `info_end` int64: the newest data time the value used (a forecast's initialisation; a reanalysis value's valid
  end; a method's newest label). In the run's step units (days for a table package).
- `target_obs_end` int64 or NaN: the newest time of any observation of the TARGET quantity (or its direct source,
  e.g. satellite AOD for an AOD-built target) the value used. NaN when it uses none.
- `product_cell` (str): the product grid box (for the resolution-matched table, H15).
- `src` (str): product file name; its sha256 is in product_manifest.json.
- N-kind rivals add `on_target_scale = true` and use the target's units.
- The tool checks: one row per export key, no duplicate, no infinite value, every `src` in the manifest with the
  right sha256, and the timing rules of H2. Any failure refuses.

**H2. Information parity (two timing rules, read from the run; nothing hand-set).**
- **Rule T1, inputs of the driver kind** (weather, SST, fire weather): `info_end` <= the row's feature boundary at
  that lead. The whole feature row is taken at the issue step t - L (H3, OWNER_RULINGS_2026-09-28.md:97). So:
  monthly/annual grids: the end of the issue step's window; table packages: the day before the issue day (ruling V9
  keeps the 1-day SST gap).
- **Rule T2, inputs that observe the target** (its own labels, or a product that assimilates the target's own
  observation): `target_obs_end` <= the newest readable label step = `timing.latest_label_step(t, L)` (t - 1 at the
  nowcast, t - L at lead L; timing/cuts.py:50-58) minus the run's R17 `start_offset_steps` (pipeline/ladder.py:221-230;
  today pm25 0, ndvi 1, fire 1, defo 0, coral 0, read from derived.json). Table packages: the last label before the
  issue day (pipeline/table_ladder.py:396). This is the same rule as our history block and persistence (rule D54 a,
  labels/vault.py:304).
- **Tiers.** Every human row carries one:
  - **P (parity):** passes T1 and T2. Only P rows decide "ours beats".
  - **A (input-advantaged):** fails T1 or T2 by design (e.g. same-month EAC4 at the nowcast: it assimilates the
    target month's MODIS AOD; ruling D1 wording "assimilates the same satellite AOD but zero ground monitors",
    QUESTIONS_ROUND3_HANDOFF.md:475). Scored and tagged, labelled; a loss to it measures what that observation is
    worth, not an architecture failure (PM25_RIVALS_PLAN.md ATTENTION 4).
  - **L (lagged by design):** a nowcast rule fed old inputs to reach a lead it was not made for (ruling C11 a:
    "lagged DHW", QUESTIONS_ROUND3_HANDOFF.md:332-337). It is P for information and decides, but carries the label.
- The tool refuses a P row whose index table breaks T1 or T2 on any row.
- **Fits** (calibration maps, method parameters) use train rows only: labels at or before the cut of that fit (H4).
  T2 governs only what a prediction may READ at its issue date (for example a SARIMA state update).

**H3. Same test rows.** The human rival predicts the saved test rows of each lead (`test_preds.parquet`; lead L:
`ladder/lead_L/test_preds.parquet`), joined on (unit, time, lead), in the saved order. Rows our run dropped (H4, S1)
stay dropped. Test `y` is read only after the lock (H16).

**H4. Same train rows, roles and cuts.** The roles of the export: tune rows and inner rows at lead 0; guard-fit and
guard rows at each lead >= 1; refit rows at each lead's fit cut (SPEC_RIVALS.md:68-83). Cuts are the run's
(`fit_cut`, `guard_cut`, `inner_fit_end_step` per lead from derived.json); a cut applies to the label step (common
rule 6). Normals: the guard-cut normal (`ngd__`) on tune, inner, guard-fit and guard rows; the fit-cut normal
(`nfit__`) on refit and test rows (common rule 5). c is the run's fit-cut c at every row of a lead (A3,
SPEC_RIVALS.md:34-37). Train rows include every bank unit (gauged global, ruling Y3 Q1 b), no unit ID.

**H5. Leads.** Leads are the run's: pm25/ndvi/fire 0, 6, 12 months; defo 0, 1 year; coral 0, 183, 365 days.
- A forecast product enters at lead L with the LATEST initialisation whose `info_end` passes T1/T2 for the row's
  issue date, and whose horizon covers the whole target window. Daily forecasts are aggregated to the target window
  only when at least 20 of the window's days are covered (the old CEMS rule, FIRE_CEMS_REPORT.md:64-68); else NaN.
- A diagnostic product (reanalysis, DHW, ERA5 FWI) at lead L is read at the issue date (the persistence of the index).
- **Horizon gap.** When no initialisation reaches a lead (for example the CRW Outlook stops at 20 weeks = 140 days,
  CRW_BENCHMARK_REPORT.md:50; no 6-12 month PM2.5 forecast exists, QUESTIONS_ROUND3_HANDOFF.md:375-376), the
  product has NO row at that lead. The human answer there is the normal / persistence, already printed. Optional
  (HQ7): one labelled tier-A "advantaged horizon" row that uses the product at its longest lead (issued after our
  issue date). It never decides.

**H6. How an index or product enters: the calibration maps.** A fixed family list, the same on every problem:

| id | form (z = link-space prediction, z0 = the row's link-space normal, H4) | allowed for |
|---|---|---|
| F0 native | prediction = x (no fit) | N only |
| F1 lin_link | link(y) = a + b link(x), OLS (the PM25 plan's R1 "2-parameter log mapping", PM25_RIVALS_PLAN.md:57) | N only |
| F2 iso_raw | link(y) = iso(x), one global isotonic map (the old CEMS map, FIRE_CEMS_REPORT.md:72-76) | I, N |
| F3 lin_anom | link(y) - z0 = a + b (x - xbar), OLS; the normal is a fixed offset, as for the common rivals (Q16 a) | I, N |
| F4 iso_anom | link(y) - z0 = iso(x - xbar), one global isotonic map | I, N |

- **Rows.** Each map is fitted per lead on that fit set's train rows (tune rows for tuning, guard-fit rows for the
  guard, refit rows for the test prediction), using only rows with a finite label and a finite `x`. No weights.
- **Links.** Every R22 link of the run (`plan.json["links"]`; today pm25 identity+log_c, ndvi identity,
  fire/defo/coral identity+log_c+arcsine). F0 has no link.
- **Isotonic direction** = the sign of Spearman(x, y) on the same fit rows (data-driven, train only; recorded). sklearn
  `IsotonicRegression(increasing=<sign>, out_of_bounds="clip")`, squared error. Deterministic.
- **xbar** = the index's own mean per unit x season key (the run's season key) over the same fit rows. A unit with
  fewer than 3 covered fit rows in that key uses the pooled mean of that key; no season key (annual, table) uses the
  pooled mean. So coral's anomaly form is "donor median + f(x - pooled mean)".
- **Statistics.** At most 3 pre-registered `x__<stat>` per rival.
- **Candidates per rival** = stats x families x links: at most 3 x 5 x 3 = 45 fits, each seconds to minutes.
- **Minimum to fit:** at least 100 covered labelled fit rows in at least 3 groups (HQ9). Below that the rival is "not
  calibratable at this lead": no row, disclosed.
- **Archive shorter than the train period:** fit on the covered train rows only and disclose the years. If a
  product's real-time archive misses the train years but a reforecast/hindcast archive covers them, the hindcast is
  used for the fit rows and the real-time archive for the test rows, disclosed (HQ11).

**H7. Method-type rivals (M).** The method is the fit. It follows H2-H5 like a learner:
- parameters fitted on labels at or before the cut of each fit set (guard cut for tuning and guard, fit cut for refit);
- at prediction it may READ labels up to the T2 step (a SARIMA or Holt-Winters state update, the REDD+ "recent loss"
  layer). It never refits on them;
- its own published settings, plus at most one small pre-registered grid (for example SARIMA orders by per-unit AIC,
  which uses train rows only; or the REDD+ reference-period length) picked by inner MAE;
- a per-unit method predicts only the units it was fitted on (the scored units). A global method (Kraft LSTM) fits on
  all bank units' rows, like a common rival;
- output on the target scale: F0 only. No extra calibration (a recalibrated method is a different method).

**H8. Pick, pin, lock.**
- The pick per rival = the lowest inner MAE (clipped prediction) over its candidates, on the inner rows it covers.
  Ties: the fixed order (stat order, family order F0..F4, link order of R22). corr2, calibration ratio and
  predict-zero MAE are logged beside each candidate (as harness.py:1234).
- One pick per rival, made at the nowcast and PINNED at every lead (ruling Y3 Q12 a). The map is REFIT per lead on
  that lead's rows. A forecast-only product (no nowcast form) is picked on the guard rows of its lowest covered lead,
  pre-registered.
- The pick, the coverage mask of every lead (H11) and every hash go into a write-once lock before any test label is
  read (H16).

**H9. Clip and save.** Back-transform with no smearing. Clip with `clip_to_legal` to each row's legal range; save the
pre-clip value. Never import rivals.py or pm25_rivals.py (their `_clip` caps at 1, rivals.py:145-148).

**H10. The safety net: APPLIED, as for the common rivals (Y3 Q11 c; HQ2).**
- Why: our headline answer includes the decline (rule D86, HEADLINE_MODEL_TABLE.md:7-10). The fair pair is guarded vs
  guarded. Raw ("the product as shipped") vs our pinned model is printed beside.
- Lead 0: the guard is the picked fit on the inner rows. Lead L: the pick fitted on that lead's guard-fit rows,
  scored on its covered guard rows.
- Comparator: the trees-off of the pick's link (`<link>_trees_off_unweighted`; F0 and M rivals: identity), clipped,
  on the same covered rows. Neighbour kind (coral): the donor-row median (ruling V1). Fallback: the run's decline
  target (SPEC_RIVALS.md:28-32, A2). Passed iff MAE(rival) < MAE(comparator) strictly (`n2_eligible`).
- Rows the product does not cover get neither raw nor fallback on the deciding board (H11).

**H11. Missing coverage: score on the common rows and disclose.**
- The coverage mask of a lead = test rows where the picked candidate has a finite prediction. It comes from the
  index table alone (no label), is hashed and locked (H8).
- **Deciding contrast:** on the covered rows only, for the rival AND for ours. A group enters only with at least 10
  covered test rows (the engine's own 10-row floor for anomaly R2, report/metrics.py:115; HQ9); fewer groups means
  wider intervals, and fewer than 3 groups gives CANNOT TELL by the engine rule (report/metrics.py:1043-1046).
- **Printed beside, never deciding:**
  - coverage: rows k of n, groups g of G, years covered;
  - a selection check: our MAE and the normal's MAE on the covered rows vs on all rows;
  - a "filled" full-row line: uncovered rows take the run's decline target (what a practitioner would do).
- Why not "filled" as the decider: it scores the normal, not the product, on the uncovered rows.
- The engine's score_table already does this split for a column missing on some rows (`rows_basis`,
  report/metrics.py:859-863); the human board passes a frame cut to the covered rows instead, so every column (ours,
  the rival, the baselines) is scored on exactly the same rows.

**H12. Metrics.** The engine's own functions only (section 1). MAE is the headline. Printed with it: anomaly R2 (not
coral: its normal is one constant), corr2, the hit rate at the run's own tolerance (verdict.json `hit_tolerance`) and
at the declared floor, the calibration ratio, the pre-clip rate. Pooled, macro, per year, per group; defo per stratum
(forest2000_px); NDVI also without its seen_during_design groups; coral per programme first
(HEADLINE_MODEL_TABLE.md:31-34). Beside every line: predict-zero, guess-normal, last-5-years normal, persistence and
damped persistence (leads), as saved in test_preds (`base__*`).

**H13. "Ours beats human rival X" (same rule as the common board).**
- d_g = MAE_rival(g) - MAE_ours(g) per scored group on the covered rows, all groups weighted the same:
  `metric_by_key` then `_paired_contrast(rival_map, ours_map)` (it subtracts the second from the first,
  report/metrics.py:1133), as harness.py:2366-2368 does.
- Tag: `contrast_tag(d, band)` with the run's NOWCAST verdict.json band at every lead (F57): pm25 0.0462, ndvi
  0.000597, fire 1.36e-5, defo 1.10e-4, coral 0.918 (RIVALS_PLAN_COMMON.md:115). BEATS = HELPS, LOSES = HURTS,
  otherwise EQUIVALENT / CANNOT TELL. `blocked_jackknife` with derived R14 blocks printed beside.
- Guarded vs our headline answer decides; raw vs our pinned model is printed beside.
- No multiplicity correction (the engine has none, report/metrics.py:1037). Every rival is reported; no "best rival"
  headline (common rule 16).

**H14. Timid flag.** A rival MAE win with calibration ratio < 0.5, or corr2 below half of ours, is flagged "timid
win" (common rule 14; harness.py:2378-2380). The verdict is not changed.

**H15. Resolution-matched context table (printed only).** For a product coarser than our unit, both sides are also
averaged to (group, product_cell, time) and scored the same way. The old CEMS work showed why: a 1-degree product
scored at 4 km cannot rank inside its box (FIRE_CEMS_REPORT.md:83-101). This table never decides; it says whether a
loss is resolution or skill.

**H16. Pre-registration and the test-label lock.**
- A new Part (next free number after the common rival Part) records, BEFORE any human-rival test score: the rival
  list per problem and lead with kind and tier; each product's manifest (files, sha256, licence, versions, archive
  dates); adapter and tool code hashes; the pinned common-harness code hash; statistics, families, links, grids; the
  constants of HQ9; the coverage rule; the H-A4 disclosure (not blind); the D4/D1 wording for EAC4.
- Order: index tables built and checked, then `tune`, then `lock` (write-once picks + coverage masks + hashes, sha
  in a lock file; same design as harness.py:1786-1830), then `refit`, then `score`.
- One reader of test `y`: it refuses without a valid lock, writes a `test_labels_opened` record with the picks sha,
  and joins one to one on the saved keys (F65: the same saved y for every column). Separate ledger in the human out
  root.
- Nothing is re-picked or added after a test number is seen. A later addition gets its own Part and the label
  "added after test scores were seen".

**H17. Save everything.** Per rival x lead: one parquet keyed like test_preds with x, pre-clip, raw, guarded, guard
flag, coverage flag; every inner candidate's predictions; the candidate CSV; the guard rows; fitted maps (isotonic
knots, OLS coefficients) as JSON; for M rivals, per-unit parameters. Memory rule: save predictions, not just scores.

**H18. Determinism.** No seeds varied (Kraft LSTM: `random_state=0` / one fixed torch seed, CPU, recorded); one
thread count for the whole board (8, ruling Y3 Q15 a); library versions in the manifest.

**H19. Old results.** CEMS Parts 496-497, CRW Parts 456-457, the NDVI Parts 417-426 and the old PM2.5 plan are
history only. They are cited as context, never paired with the new runs.

---

## 3. How the known candidates enter (for the per-problem planners; facts to verify there)

| problem | candidate | kind | leads it can reach | tier | note |
|---|---|---|---|---|---|
| pm25 | CAMS EAC4 monthly pm2p5, lagged to the T2 step | N | 0 (lagged) | P | the parity version of ruling D4 a |
| pm25 | CAMS EAC4, same month | N | 0 | A | assimilates the target month's MODIS AOD (D1) |
| pm25 | MERRA-2 aerosol (second arm) | N | 0 | P lagged / A same month | as EAC4; no nitrate (PM25_RIVALS_PLAN.md:58) |
| pm25 | none at 6 and 12 months | - | - | - | no operational 1-12 month PM2.5 forecast (D4 b); the normals and persistence stand |
| ndvi | Kraft et al. LSTM (land cover dropped) | M (global) | 0, 6, 12 if its inputs pass T1 | P | NDVI_BASELINE_REPORT.md:67 |
| ndvi | rainfall-lag regression | M (per unit) | 0, 6, 12 | P | inputs as McPhillips 2026 (precipitation, max VPD; built before as a per-cell Gaussian process, NDVI_BASELINE_REPORT.md:66, :80) |
| ndvi | SARIMA / Holt-Winters per cell | M (per unit) | 0, 6, 12 | P | reads labels up to the T2 step (ndvi offset 1) |
| fire | ERA5-based FWI of the target month | I | 0 | P if our nowcast row holds that month's weather (T1) | |
| fire | CEMS GEFF-SEAS5 FWI, ensemble mean (+ max / p90 as stats) | I | the leads its horizon covers | P | old fetch used 62 daily leads (FIRE_CEMS_REPORT.md:242-244); horizon and archive start to verify |
| defo | REDD+ jurisdictional allocation (historical rate by group, allocated by distance-to-recent-loss) | M | 0, 1 year | P | reads loss up to the T2 year; VT0007 / VM0048 / JNR details by the defo planner |
| coral | CRW DHW / BAA at the day before the survey | I | 0 | P | C11 a at lead 0 |
| coral | CRW DHW / BAA at the issue day | I | 183, 365 | L | "NOAA's nowcast rule fed old heat" (C11 a) |
| coral | CRW 4-Month Outlook v5 (CFSv2), BAA week composites | I | leads <= 140 days only, so none of 183 / 365; optional tier-A "advantaged horizon" row (HQ7) | P / A | archive from 2011 (CRW_BENCHMARK_REPORT.md:57-58); EXPERIMENTAL product (CORAL_BASELINE_LANDSCAPE.md:13) |

- Coral: the train calibration rows that the CRW Outlook can cover are only the 2011-2015 train visits (test 2016-2019,
  ruling V3). The H6 minimum applies.

---

## 4. ONE rival table (the joiner)

- **Inputs:** each problem's common `board_lead_<L>.csv` and `scores/` (D:/treeroute/rivals/<pkg>/<run>/,
  harness.py:2384-2386) and the human board's files in the same schema (D:/treeroute/rivals_human/<pkg>/<run>/).
  Read only.
- **Refuses unless** both boards name the same run fingerprint, the same test_preds sha256 per lead, the same band,
  and the same "ours" pooled MAE on all rows (equal to the run's score_pooled.csv at lead 0, harness.py:2292-2327).
- **One schema per row** (problem x lead x rival x contrast):
  `problem, lead, rival, rival_type (common | human | own_history | reference), kind (learner | I | N | M | -),
  tier (P | A | L | -), rows_basis (all | covered), rows, rows_total, groups, groups_total, contrast
  (guarded_vs_headline | raw_vs_raw), verdict (BEATS | LOSES | EQUIVALENT | CANNOT TELL), d_mean, d_low, d_high,
  rival_mae, ours_mae_same_rows, ours_mae_all_rows, normal_mae_same_rows, anomaly_r2, corr2, hit, calibration_ratio,
  timid_win, guard_passed, flags (edge picks, not calibratable, horizon gap), part_number`.
- Common rivals fill `rows_basis = all`, `tier = -`. Own-history rows (guess-normal, last-5-years normal, damped
  persistence) and reference rows (predict-zero, persistence, coral donor median) come from the same score tables.
- **Output:** `D:/treeroute/rivals_table/<stamp>/RIVALS_TABLE.md` and `.csv`, plus a sha256 list of every input.
- **Order inside a problem x lead block:** our headline, common rivals, human P and L rows, human A rows, own-history,
  reference. Every row is printed; no "best rival" line.
- **Reading rules printed under the table:**
  - "ours beats rival X" is claimed only from a guarded_vs_headline row with tier P or L;
  - on a covered-rows row the claim is "on the k% of rows the product covers";
  - an A row is read as "what that extra observation is worth";
  - a timid win is printed with its flag; verdicts are not changed.

---

## 5. Owner commands and order (each resumable, each takes the heavy-job lock, never backgrounded by the agent)

```
py -3.9 -m rivals_human.cli slim    --run <run folder> --export <export lead folder>      (before the export is deleted)
py -3.9 -m rivals_human.cli adapt   --run <run folder> --rival <id> --lead <L|all>         (adapter -> index table)
py -3.9 -m rivals_human.cli check   --run <run folder> --rival <id>                        (H1, H2 refusals)
py -3.9 -m rivals_human.cli tune    --out <folder> --resume
py -3.9 -m rivals_human.cli lock    --out <folder>
py -3.9 -m rivals_human.cli refit   --out <folder> --lead <L> --resume
py -3.9 -m rivals_human.cli score   --out <folder> --lead <L>
py -3.9 -m rivals_human.cli join    --runs <5 run folders>
```

- Order follows ruling Y4: coral first (end to end), then fire, pm25, defo, NDVI. For each problem: `slim` right after
  the common export of that lead exists; human fits and scores can then run any time.
- Downloads are owner commands only, logged into product_manifest.json before the Part is signed.

### Cost of the protocol itself (x = extrapolated, not measured)

- `slim`: reads ~6 columns of the export per lead; pm25/ndvi/defo ~2.5-3.0M rows per fit set: ~5-15 min per lead (x).
- `tune` for an I/N rival: at most 45 candidate fits of 1-2 parameter maps or isotonic maps on up to ~2.6M rows:
  ~5-20 min per rival (x). Refit + guard per lead: about the same per lead.
- `score` and `join`: minutes.
- So the protocol adds roughly 1-3 h per problem (x). The real costs are the downloads, the adapters' extraction and
  the M rivals (per-cell SARIMA on ~2,000 units x leads; the Kraft LSTM), estimated by the per-problem planners.

---

## 6. Owner decision sheet

| Q | question | options | RECOMMENDED | why (one line) |
|---|---|---|---|---|
| HQ1 | where the human rivals live | (a) separate tool, imports the common harness read-only at its signed hash, plus a joiner; (b) add them as learners inside rivals_build after its sign-off | **(a)** | (b) changes a signed board and a folder another workflow is editing |
| HQ2 | safety net | (a) raw and guarded, guarded decides; (b) raw only ("as shipped") decides | **(a)** | same as the common board (Y3 Q11 c); our headline includes the decline |
| HQ3 | partial coverage | (a) covered rows decide, "filled" printed; (b) filled full rows decide | **(a)** | (b) scores the normal, not the product, on missing rows |
| HQ4 | products that see the target month (same-month EAC4) | (a) the T2-lagged version decides, same-month printed as tier A; (b) same-month only, labelled | **(a)** | it keeps D1's wording and still gives a parity answer |
| HQ5 | calibration rows | (a) gauged global (all bank units up to the cut), like the common board; (b) donor-only, D4 a wording (pre-LORO; needs fold maps) | **(a)** | one information rule for every rival; D4 predates LORO |
| HQ6 | calibration choices | (a) F0-F4 x links x <=3 stats, picked on inner MAE; (b) one fixed family per rival (iso_raw) | **(a)** | it gives each product its best train-only mapping, as the common rivals get links and the normal offset |
| HQ7 | product cannot reach a lead | (a) no row; normals/persistence stand; plus an optional labelled tier-A "advantaged horizon" row; (b) no row, nothing else | **(a)** | it shows the CRW Outlook at its 140-day limit without letting it decide |
| HQ8 | M rivals reading labels up to the T2 step | (a) yes, same rule as our history block (D54 a); (b) frozen at the fit cut | **(a)** | it is what a forecaster has at the issue date and what our model reads |
| HQ9 | constants | min 10 covered test rows per group; min 100 covered fit rows in >= 3 groups; unit index mean needs >= 3 rows | **as listed** | 10 is the engine's own row floor; the others keep tiny fits out |
| HQ10 | tuning at leads | (a) pick at the nowcast, pin, refit per lead; forecast-only products picked at their lowest covered lead; (b) re-pick per lead | **(a)** | mirrors Y3 Q12 a |
| HQ11 | short real-time archive | (a) hindcast archive for train rows, real-time for test, disclosed; (b) real-time train years only | **(a)** | more fit rows; the ensemble-size change is disclosed |

---

## 7. Risks

| # | risk | what we do |
|---|---|---|
| H-R1 | a product breaks parity silently (wrong init chosen, valid date off by one) | `info_end` / `target_obs_end` per row; T1/T2 refusals (H1, H2); a test with a shifted product must refuse |
| H-R2 | the export is gone before the human run | `slim` first (H-A2); otherwise a deterministic re-export |
| H-R3 | the common harness code changes under us | pinned code hash; refuse on mismatch (H-A1) |
| H-R4 | coverage chosen after seeing labels | the mask comes from the index table and is locked before labels (H8, H11) |
| H-R5 | coarse products scored at fine resolution | H15 context table |
| H-R6 | candidates known from old results (not blind) | disclosed in the Part (H-A4); no additions after test |
| H-R7 | short archives (CRW Outlook 2011+) leave few fit rows | H6 minimum; "not calibratable" is a reported outcome |
| H-R8 | hindcast vs real-time ensemble sizes differ | disclosed (HQ11) |
| H-R9 | per-unit methods (SARIMA) fail to converge on some units | the method's documented fallback (e.g. a lower order), counted and disclosed; never the normal silently |
| H-R10 | disk (D: ~39 GB free today, df 2026-10-21) | index tables are small; product files are owner downloads; sizes from the planners |

---

## 8. Sources

- Common plan and spec: RIVALS_PLAN_COMMON.md:75-127 (rules 0-19), :115 (bands), :157 (export deletion);
  D:/treeroute/rivals_build/SPEC_RIVALS.md:28-37 (A2, A3), :64-83 (export files), :117 (I4), :382-420 (guard, scoring).
- Rulings: OWNER_RULINGS_2026-10-06.md:136-145 (Y), :147-156 (Z); OWNER_RULINGS_2026-09-28.md:52-55 (D), :97 (H3);
  QUESTIONS_ROUND3_HANDOFF.md:332-337 (C11 options), :354-378 (D1, D4), :472-478 (answers).
- Engine: report/metrics.py:115 (10-row floor), :569-630, :846-863, :999, :1032-1056, :1058, :1097-1137;
  layer/decide.py:290; layer/links.py:84, :118, :261; timing/cuts.py:50-58; pipeline/ladder.py:221-230, :878-897;
  pipeline/table_ladder.py:396; labels/vault.py:304.
- Common harness (read only): D:/treeroute/rivals_build/rivals/harness.py:704, :1234, :1786-1830, :1989-2003,
  :2195-2400.
- Runs: D:/treeroute/runs/{pm25/headline/20261007_74e67609, ndvi/headline/20261016_d1de3158,
  fire/headline/20261017_869d1f38, defo/headline/20261017_d71c61f4, coral/headline/20261020_f3b8e3da}: derived.json
  R17 start_offset_steps (0, 1, 1, 0, 0) and R22 links; test_preds.parquet `base__*` columns (checked 2026-10-21).
- Old human-rival work (history only): PM25_RIVALS_PLAN.md:20, :57-58; FIRE_CEMS_REPORT.md:60-101, :238-244;
  CRW_BENCHMARK_REPORT.md:28-58; CORAL_BASELINE_LANDSCAPE.md:13; NDVI_BASELINE_REPORT.md:40-80;
  HEADLINE_MODEL_TABLE.md:7-34.
