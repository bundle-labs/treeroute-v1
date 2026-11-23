# POST HOC re-computation of the engine-v2 alarm replay (owner ruling AN2, part 1 of 3: the specification)

Written 2026-10-28. Folder: `D:/treeroute/analysis/paper_posthoc/v2_replay/`.
Part 1 (this file): the specification. Part 2: two independent implementations, A and B, in `./A/` and `./B/`.
Part 3: reconciliation of A and B, then ONE post-hoc Part in `engine/PENDING_PARTS.md` (the next free number; the
last logged is Part 624). Only after that Part is logged may PAPER_FACTS V3 become "final, post hoc" (ruling AN2) and
Supplement S5.3's [PENDING] block be filled.

Everything this work computes is POST HOC: the alarm was specified after the five v1 runs had been locked, run and
scored and their test labels opened (ruling AE3; facts V2, A8). On coral bleaching the replay is CIRCULAR: the rule
was designed from the same coral test window (A8; Parts 603-604). No locked number, verdict or adoption changes. The
results go to Supplement S5 only; no alarm number goes into the main text.

Sources read for this spec: `paper/draft/S5_v2_alarm.md` (S5.2 rule, S5.3 [PENDING] list items 1-9),
`paper/PAPER_FACTS.md` (V1, V2, V3, A7, A8, C6, R15, S5), `engine/OWNER_RULINGS_2026-10-06.md` (AE1-AE4, the AE1
amendment, AF1-AF3, AK3, AN2), `engine/PENDING_PARTS.md` (Parts 601-605 and the Part 605 addendum, 622, 624),
`D:/treeroute/engine_v2/ALARM_REPORT.txt` (sections 3 and 6), `D:/treeroute/engine_v2/SPEC_ALARM.txt` (1.5, 2.1-2.7,
9, 11), the engine-v2 code `treeroute/layer/alarm.py`, `treeroute/pipeline/alarm_pass.py`,
`tools/alarm_replay.py`, `tools/alarm_with_without.py`, and the replay outputs under
`D:/treeroute/engine_v2/replay_af2_20261021/`. (There is no RESULT.txt under `D:/treeroute/engine_v2/`; the
RESULT.txt of this history is Part 604's, `D:/treeroute/analysis/guidance/RESULT.txt`, used here only for a
cross-check.)

---------------------------------------------------------------------------------------------------------------------

## 1. What the replay is, in plain words

Each v1 run picked one "adopted" arm on its decision surface. Most adopted arms have a close sibling, the "twin",
that differs only in one choice: its weighting (error-weighted vs uniform) or its answer type (corrected vs plain).
On the decision surface the two siblings usually give nearly the same answers; that typical disagreement is the
"reference gap". The alarm is a smoke detector for new conditions: it looks at the test rows month by month (a
"batch"), and if the two siblings disagree on a batch much more than they usually did (more than twice the reference
gap), it takes that as a sign that the evidence behind the adopted arm may not hold there, and it uses the simpler
sibling for that batch instead. It never looks at a test label to decide.

The "replay" runs this fixed rule on the predictions the five v1 runs already saved (nothing is refitted or
re-routed) and scores the final answers WITH and WITHOUT the alarm. Where v1 did not save the twin's predictions
(forecast leads where the twin was never routed), the rule cannot be replayed and we say so.

## 2. The rule, exactly (treeroute v2, engine code hash 88f4db2c; rulings AE1, AE1 amendment, AF1, AF2; V1)

For each pass (a run's nowcast, lead 0, or a forecast lead L) of the five v1 runs:

R1. Adopted arm A. Nowcast: `adoption.json` "adopted" (link, tool, weighting), at the penalty point P =
    `adoption.json` "penalty" (level, ratio; ratio may be null). If `adoption.json` "declined" is true: status
    `not_applicable_declined`. Lead L: `adoption_lead_<L>.json` "pinned"; if "guard_passed" is false the lead adopts
    its decline target: status `not_applicable_declined`.
R2. Routed weightings: `verdict.json` "router_kind" == "region" -> unweighted only; otherwise (per-unit grid,
    neighbour router) unweighted and GLS (error-weighted).
R3. Twin T (`alarm.twin_of`): same link and tool, the OTHER weighting, when that weighting is routed; otherwise
    same link and weighting, the other tool (plain <-> corrector).
R4. T is simpler (`alarm.twin_is_simpler`) iff (T unweighted and A GLS, same link and tool) or (T plain and A
    corrector, same link and weighting). Not simpler: status `inert_twin_not_simpler` (nothing can switch).
R5. Skill guard of the twin (AF2). Nowcast: T's decision-surface MAE at the ADOPTED point,
    `adoption.json` "surface_mae"["<T>@level=<level>,ratio=<ratio>"], strictly below its baseline:
    `surface_mae`["<link>_trees_off_unweighted"] for grid kinds, or, when `adoption.json`
    "decision"."decline_baseline"."key" exists (the neighbour router, ruling V1), `surface_mae`[that key]
    (coral: "base__donor_median"). Not below: status `inert_twin_not_eligible`. (A lead would use the lead's guard
    rows (SPEC_ALARM D2); no v1 lead reaches this step with a saved twin, see R10.)
R6. Reference gap R (`alarm.reference_gap`): mean |A - T| over ALL rows of the decision surface,
    `inner_preds.parquet` columns "<A>@level=<level>,ratio=<ratio>" and "<T>@level=<level>,ratio=<ratio>" (both
    already clipped, as decide scored them). Arm names are "<link>_<tool>_<weighting>"; the point text is Python
    `repr` of floats and `None` (e.g. `log_c_corrector_unweighted@level=0.1,ratio=None`). R not finite or R == 0:
    status `not_tested_zero_reference_gap` (AF1). Otherwise status `active`. Status order: declined, not simpler,
    not eligible, zero gap, active (`alarm.pass_status`).
R7. Batches (AE1 amendment; `alarm.batch_keys`), from the saved column "issue" of the pass's test_preds and the
    cadence `derived.json` "R1"."value": irregular (coral: issue is a day ordinal) -> calendar month of
    `date.fromordinal(issue)`, key "YYYY-MM"; regular with unit month or year and length 1 (pm25, ndvi, fire monthly;
    defo yearly) -> the issue step itself, key "step:<issue>". Every SAVED test row counts, labelled or not
    (SPEC_ALARM D4). Batches are ordered: steps by number, months by text.
R8. Per batch b with rows I_b (in saved row order): g_b = mean over I_b of |A - T| using the saved, clipped test
    columns `arm__<A>` and `arm__<T>`; ratio_b = g_b / R. The batch is TESTED iff status is active, |I_b| >= 30
    (A8.alarm_min_batch_rows) and R is finite and > 0. It SWITCHES iff tested and ratio_b > 2.0
    (A8.alarm_ratio_threshold, strict). NOTE: for an inert pass with a saved twin the code still computes g_b and
    ratio_b, but the batch is NOT tested (tested = false); those ratios are information only.
R9. With-alarm column: `arm__<T>` on the rows of switched batches, `arm__<A>` on every other row. The adopted column
    is never changed. Without = the v1 final answer (the adopted column of the pass; for a declined pass, its
    decline target column).
R10. Forecast leads: v1 routed only the pinned arm at a lead (SPEC_ALARM 1.5). A lead that is declined, or whose
    pinned arm's twin is not simpler, can never switch and IS replayed (with == without, asserted). A lead with
    guard passed and a simpler twin ("may be active": defo lead 1, coral lead 183) needs the twin's predictions and
    guard MAE, which were not saved: status `not_replayable_twin_not_saved`; only the without MAE and the batch
    counts are reported.
R11. Scoring: MAE = mean |y - p| over the labelled rows (finite y) of the pass or subset, label scale, using the
    saved clipped values (`metrics.score_table`, rows basis "all"; `metrics.mae`).

What the rule gives on the five v1 runs (design, already in S5 Table S5.1a; to be confirmed by the gate):

| package | run | lead | status (code) | plain status (S5 Table S5.1a wording) |
|---|---|---|---|---|
| pm25 | 20261007_74e67609 | 0 | inert_twin_not_simpler | cannot switch: twin not simpler |
| pm25 | | 6 | inert_twin_not_simpler | cannot switch: twin not simpler |
| pm25 | | 12 | not_applicable_declined | nothing to switch: declined |
| ndvi | 20261016_d1de3158 | 0 | inert_twin_not_simpler | cannot switch: twin not simpler |
| ndvi | | 6, 12 | not_applicable_declined | nothing to switch: declined |
| fire | 20261017_869d1f38 | 0 | inert_twin_not_eligible | cannot switch: twin fails its skill guard |
| fire | | 6, 12 | not_applicable_declined | nothing to switch: declined |
| defo | 20261017_d71c61f4 | 0 | active | can switch |
| defo | | 1 | not_replayable_twin_not_saved | not replayable: twin not saved |
| coral | 20261020_f3b8e3da | 0 | active | can switch |
| coral | | 183 | not_replayable_twin_not_saved | not replayable: twin not saved |
| coral | | 365 | not_applicable_declined | nothing to switch: declined |

Run folders: `D:/treeroute/runs/<package>/headline/<run>/` (read-only). Test windows: pm25, ndvi, defo 2020-2023;
fire 2019-2022; coral 2016-2019 (coral's window was set by hand, PAPER_FACTS R3/V3 note; say so wherever years are
listed).

## 3. Inputs (read-only; sha256 checked before use)

Machine-readable list: `D:/treeroute/analysis/paper_posthoc/v2_replay/INPUTS_SHA256.txt` (sha256sum format, 108
files; every hash computed 2026-10-28 by the spec writer). Each implementer re-hashes every file it reads and STOPS on
any mismatch. Read parquet columns selectively (`pyarrow.parquet.read_table(columns=...)`).

Per run folder (all five): `adoption.json`, `decision_checks.json` (surface hash only), `verdict.json` (router_kind,
adopted_column, pooled_mae_adopted, band, hit_tolerance, measurement_error_floor, reference, reference_rule, verdict),
`run_record.json` (kind), `derived.json` (R1 cadence; "R14:overlap_blocks" for the blocked jackknife),
`score_pooled.csv` (cross-check), `inner_preds.parquet` (two columns only), `test_preds.parquet` (unit, group, time,
year, lead, issue, y, normal, legal_min, legal_max, the adopted, twin and reference columns and their `pre__`
columns; coral also `programme`), `ladder/ladder.json`, `ladder/ladder_table.csv`, `adoption_lead_<L>.json` and
`ladder/lead_<L>/test_preds.parquet` for each lead (pm25 6, 12; ndvi 6, 12; fire 6, 12; defo 1; coral 183, 365).

Key hashes (full list in INPUTS_SHA256.txt):

| file | sha256 |
|---|---|
| runs/pm25/headline/20261007_74e67609/test_preds.parquet | 9e62fe4256c08c50108f09bb0eef65bd46bed78c1deb045a2746eb500f454225 |
| runs/pm25/.../adoption.json | b6408c90560b458543f0b1d7d46fc7f4c70de110ff2e6e2ad0e8cdef27ec4335 |
| runs/pm25/.../inner_preds.parquet | 88241690f24479323c4b54f13ea5c964db79a05d361ec8a0cda881364b1193d6 |
| runs/ndvi/headline/20261016_d1de3158/test_preds.parquet | 87c0b1414af7e37027905ff55b2caa39adadd7cee01591ea8b17de1172dfb00c |
| runs/ndvi/.../adoption.json | d5ae6f1dd672868166425c6b7590ca911596b29a0c9ccf198feb594623963e59 |
| runs/ndvi/.../inner_preds.parquet | a36b44645c779c2cd403c561cb56c42ab758cad1601ee288e9849b40edf8963a |
| runs/fire/headline/20261017_869d1f38/test_preds.parquet | 86e9c97a58a9b7142a865fd1e3f3ad1da2ea75550c14cdfe200e8a748ac51c8b |
| runs/fire/.../adoption.json | 75f70e5cd22039b62c65f0e4546f669de484edd21d5a9cec581fc0ed774260ad |
| runs/fire/.../inner_preds.parquet | 9f21182b5164af8ab1ae022dd4148a667a673b6f8bd772dbdd0f8cbe5e09be9a |
| runs/defo/headline/20261017_d71c61f4/test_preds.parquet | 3a002e9a9deb006a6698f4b021236782deae1480c3df821bf07888ee6012df4a |
| runs/defo/.../adoption.json | d8ebdd4cc458b276938bee2bf165088ac9c622f133518031f7c6c806592ee54a |
| runs/defo/.../inner_preds.parquet | 7af8963e927ea8f0a42324792fec38cf3ef6b8d0b61d0e482c1b18ad47697cbf |
| runs/coral/headline/20261020_f3b8e3da/test_preds.parquet | dd07762558023d5fed6007a99c5b92f935c518a2c408622ccb8230397db6e3fa |
| runs/coral/.../adoption.json | 2106a36efee4f9fc0650ed7c821a6f8f73c3fdd10c21674f7c8a24b27d80da2f |
| runs/coral/.../inner_preds.parquet | 74b457be8690bebea44f1bb6bc7c4656748b9e8a0c1fa52ddb183ea20a4955b2 |
| runs/coral/.../verdict.json | 6bf9b04970173323c9112d90910c47c16da9e65bf214be3e6e9e9bb46fcde200 |
| runs/_headline_tables/coral/coral_report/magnitude_edges.csv | d6571f1f6d8f314d42391e6a351be2cf2c8632e6b59f5b53e65900cf5e781450 |
| engine_v2/replay_af2_20261021/WITH_WITHOUT.csv (gate target) | e25a210e139d96db0236572ba03307a587cbb0670769c3d8ff59bf3dab00056f |
| engine_v2/replay_af2_20261021/coral/20261020_f3b8e3da/alarm_replay.json (gate target) | 0f1f54a359ecf8e8896d29de8903eb7193f526679c9df99848def2110ff1a769 |
| engine_v2/replay_af2_20261021/coral/20261020_f3b8e3da/alarm_replay_scores.csv (gate target) | 4845a5c73f7938623c3891b04a38f775bec355ab491d162b16a28160cabb1ad7 |
| engine_v2/replay_af2_20261021/rows/coral_20261020_f3b8e3da_lead_0.parquet (gate target) | c5de1d24b57e6d5b72f455f21cb2a865e84f2f048b7ea24d773974d78ab3eb43 |
| engine_v2/engine/tools/alarm_with_without.py | 0eb714ea083bd13a0e323e6f403bd9b9312061a94ee63eaeb549f043ed8193d7 |
| engine_v2/engine/tools/alarm_replay.py | e64b6b7a15be23cc8ff78abf28caf3a87398fd165faa333d4063295773346271 |
| engine_v2/engine/treeroute/layer/alarm.py | b5800507289c9111e06b5e21f1f5af96da791ec626ba3121381642b42e7e8b46 |
| engine_v2/engine/treeroute/pipeline/alarm_pass.py | cdc381a5349440a85a407db48dc4fdbfb3e526fe1d4556345f5b77db97c2c634 |
| engine_v2/engine/treeroute/report/metrics.py (equal to LIVE's) | 5b90337ba404c89faa9e4a074d373cd16b40f3a7ecac79b9caddde9407aff6f1 |
| analysis/guidance/coral/results_coral.json (Part 604, cross-check) | bc698a5bc3d015a23650fa06bcf9634caa33bac838a9ad8a9ea3baf3185d2604 |

Engine identities (checked 2026-10-28 with `treeroute.runs.fingerprint.engine_code_sha256`, read-only import):
treeroute v2 `D:/treeroute/engine_v2/engine/treeroute` = 88f4db2ce7c0a48834243b8e9403a29d8a3dbcc88c00ed44620d9ced79b44b7d;
LIVE v1 `engine/treeroute` = 930d961cdfdd219c36b113174e6c865096f973068e30696850f13d5ec4a60814 (both unchanged).
The two tools are outside `treeroute/` and are pinned by their own file hashes above.

Gate targets (outputs of the 2026-10-21 replay under 88f4db2c): `D:/treeroute/engine_v2/replay_af2_20261021/`:
`WITH_WITHOUT.csv` (23 rows), `<package>/<run>/alarm_replay.json` and `alarm_replay_scores.csv` (5 each),
`rows/<package>_<run>_lead_<L>.parquet` (14 files). History only (not gate targets): `replay/` (first replay, build
663ab8ef, before AF2), `replay_recheck_20261021/` (coral re-run after the skeptic fixes),
`_moved/replay_trial_coral_20261021/`.
Not hashed in the list (living documents; read as of 2026-10-28): PAPER_FACTS.md, PENDING_PARTS.md,
OWNER_RULINGS_2026-10-06.md (sha256 983f3326f0c7fa97... at writing; rulings may be appended).

## 4. Who does what

Implementer A (engine path; `./A/`): uses the engine-v2 code exactly where the original replay did.
- `py -3.9 -I -B`, `sys.dont_write_bytecode = True` BEFORE any import from `D:/treeroute/engine_v2/engine` (insert
  that folder and its `tools/` folder into `sys.path`). Never edit, move or write any file there.
- Step A1: verify engine_code_sha256 == 88f4db2c... and the tool hashes.
- Step A2: re-run the ORIGINAL tools into A's own folder, never elsewhere:
  `tools/alarm_replay.py <5 run folders> --out D:/treeroute/analysis/paper_posthoc/v2_replay/A/tool_rerun` and then
  `tools/alarm_with_without.py <5 run folders> --out D:/treeroute/analysis/paper_posthoc/v2_replay/A/tool_rerun
  --magnitude-edges coral=D:/treeroute/runs/_headline_tables/coral/coral_report/magnitude_edges.csv --abs-edge 50`
  (the subset labels in the gate target prove these arguments: "y > 23.9575" = lead-0 q75_positive_donor_labels,
  "y >= 50"). Run order: alarm_replay first (alarm_with_without cross-checks its record). Compare the re-run outputs
  with the gate targets (Gate G1-G7).
- Step A3: the new quantities (section 6) with the engine's own functions: `alarm.batch_keys`, `alarm.decide_alarm`
  (also with `threshold=` for the information-only threshold check), `metrics.score_table` (pooled lines on row
  subsets as `alarm_with_without._score_rows` does; key lines with `by=("year",)`, `("group",)`, `("programme",)`,
  `("programme", "year")`; a key column added to the frame is fine: score_table accepts any key column),
  `alarm_pass.verdict_with` for the with-alarm verdict. Extra prediction columns (the blend forms of Q6) are added
  as `arm__<name>` columns of the label-scale values (no `pre__` column), exactly as `arm__with_alarm` is.
  Contributions (Q5) use the formula in Q5, not an engine function (none exists).

Implementer B (independent; `./B/`): NO import of any engine or tool code (neither v2 nor LIVE) and no copying of it.
- `py -3.9 -I -B` (same numpy 2.0.2 / pandas 2.3.3 / pyarrow 21.0.0 as A, for bit equality), numpy/pandas/pyarrow
  only. Write the rule from section 2 of this spec (SPEC_ALARM.txt 2.1-2.7 may be read). Do not open alarm.py,
  alarm_pass.py or the two tools; if a gate fails and you must read them to find why, log that in result_B.json
  ("read_engine_code": [files, reason]).
- Compute every mean as `np.mean(np.abs(y[m] - p[m]))` over the rows in SAVED ROW ORDER (that is how the engine
  computes it; Part 622 got bit-equal results this way). The verdict (G7) is re-implemented from its definition:
  per-group MAE of the reference column and of the with-alarm column over labelled rows; d_g = MAE_ref(g) -
  MAE_with(g); group jackknife of the mean of d_g (G groups, leave-one-group-out, interval mean +/- 1.96 x se);
  tag against the run's band (verdict.json "band"); the blocked jackknife over derived.json R14 blocks; check it
  against the gate target (if the definitions here are not enough to match, record what was missing).

Both: never read the other implementer's folder. Each run takes minutes and well under 4 GB RAM (largest table: defo
test_preds 369,096 rows, a few columns). One job at a time (a network download is running). No seeds are involved
(nothing here is random). Nothing is refitted or re-routed; no engine run, no tool CLI other than A's step A2.

## 5. Reproduction gate (must pass in full BEFORE any section-6 quantity is computed)

If any gate item fails: STOP, write `result_<A|B>.json` with the failing item, the expected and obtained values and
the first differing rows, and compute nothing new. Equality rules: integers, strings, booleans, batch keys and
switched flags: exact. Row-level prediction columns: bitwise equal (NaN-aware). MAEs, gaps, ratios: A must be
bit-equal (same code); B bit-equal preferred, else |relative difference| <= 1e-12, and every non-bit-equal value is
listed in the result file.

G0 Inputs: every file in INPUTS_SHA256.txt that the script reads matches. A also: engine v2 hash 88f4db2c..., tool
   hashes as in section 3, LIVE 930d961c... unchanged (read-only check).
G1 Pass facts, all 14 passes (the 23 lines of WITH_WITHOUT.csv): status, replayable, adopted_column, twin_arm,
   twin_kind, twin_simpler, twin_eligible, reference_gap, batches (count), batches_tested, batches_fired,
   rows_switched, n, mae_without, mae_with, max_ratio_tested, fired_batches equal the gate file (read it with
   `float_precision="round_trip"`). Headline values:
   - coral nowcast: status active; twin arcsine_corrector_unweighted (weighting), simpler, eligible; R =
     0.34056479282671 on 2,046 decision-surface rows; 48 batches, 33 tested, **11 switched**: 2016-01 2016-02 2016-03
     2016-04 2016-05 2016-06 2016-08 2017-03 2017-12 2019-05 2019-06; **737 rows switched** of 2,312; largest tested
     ratio 29.105817502602708; MAE without **6.69798924506233** (= verdict.json pooled_mae_adopted), with
     **6.119956002798195** (V3: 6.698 -> 6.120; C6: NOT 6.147, which is the twin on every row).
   - coral nowcast subsets (outcome-defined): y > 0, n 1,024: 13.370101628934457 -> 11.835788785619453; y > 23.9575,
     n 239: 41.05202467908258 -> 33.27844301061296; y >= 50, n 140: 53.12512328455528 -> 40.9865068947793
     (Part 605: 13.37 -> 11.84 and 53.13 -> 40.99).
   - pm25 nowcast 91,428 labelled rows, 3.588091134093021 both; pm25 lead 6 inert_twin_not_simpler,
     3.846310424132128 both; pm25 lead 12 declined, 4.083558322865165 both.
   - ndvi nowcast inert_twin_not_simpler 0.03146059686292064 both; leads 6 and 12 declined (0.03956835866470208,
     0.039583272201769236).
   - fire nowcast inert_twin_not_eligible 0.004385064558301006 both; leads 6 and 12 declined (0.006312458723027394,
     0.006310978468756987).
   - defo nowcast active, twin log_c_plain_unweighted (tool), R = 0.00013719429872479928 on 276,822 rows, 4 batches,
     4 tested, 0 switched, largest ratio 1.1659792695776747, 0.005415798421978487 both; defo lead 1 not replayable,
     without 0.005407746164567043, 4 of 4 batches have >= 30 rows.
   - coral lead 183 not replayable: without 7.709698984777605 (y > 0: 15.883504733505497; y > 22.22, n 255:
     50.58073261784866; y >= 50: 68.44966552627503), 49 batches, 32 of 49 with >= 30 rows. Coral lead 365 declined
     (base__donor_median): 8.294498353993655 both (y > 0 17.4696095648763; y > 22.5, n 251, 55.70945219123506;
     y >= 50 73.64017261904762).
G2 Every batch record (key, rows, gap, ratio, tested, fired) in the five gate `alarm_replay.json` files, and the
   records' twin-eligibility basis (coral twin 7.287182963109116 vs base__donor_median 9.74151323420556; fire twin
   0.004386949584483835 vs arcsine trees-off 0.00436777286420139, not eligible; defo 0.005808902179729096 vs
   0.006102746693604387; pm25 3.3585540357961188 vs 3.5256518387286944; ndvi 0.029235256613920256 vs
   0.03681265458390077) and the reference (columns, rows, gap). Inert nowcasts' largest computed (NOT tested) ratios:
   pm25 1.753861864808271, ndvi 1.749949522314697, fire 1.847279910383901 (ALARM_REPORT section 3 prints them as
   "48/0 (max 1.75)"; in the code's sense 0 batches were tested there; see pitfall P1).
G3 Coral by test year (alarm_replay_scores.csv "year" lines): 2016 n 873 12.406328256098309 -> 10.681069664805374;
   2017 n 565 3.5692507744181308 -> 3.6880301411805525 (worse); 2018 n 443 1.280418254929322 -> 1.280418254929322
   (unchanged); 2019 n 431 4.805509495430039 -> 5.043624464950422 (worse). V3 prints 12.41 -> 10.68, 3.57 -> 3.69,
   unchanged, 4.81 -> 5.04. Also every "pooled" and "group" line of all five alarm_replay_scores.csv files (A: the
   re-run files byte-identical; B: values equal).
G4 Small batches: coral nowcast 15 batches with fewer than 30 rows, 275 rows in all; among them 2016-07 has ratio
   25.529655201638473 on 16 rows (ALARM_REPORT: "2016-07, had ratio 25.5 on 16 rows"). pm25, ndvi, fire, defo
   nowcasts: none.
G5 Row-level: for each of the 14 gate `rows/*.parquet` files, the recomputed frame (unit, group, time, year, issue, y,
   batch, adopted, twin where saved, with_alarm and fired where present) equals the file (pandas `equals` after
   reset_index, and bitwise floats). A: also the re-run files (step A2) equal the gate files.
G6 Threshold check (information only; ALARM_REPORT section 3 is the only record, at 3 decimals): coral nowcast with
   threshold 1.5 -> pooled MAE with 6.109 (rounded to 3 decimals); 2.5 -> 6.100; 3.0 -> 6.100. Everything else as
   at 2.0.
G7 With-alarm verdict (coral `alarm_replay.json` "scores"): verdict_with tag "helps", contrast mean
   7.873171654763077, interval [2.405477799042173, 13.34086551048398], 37 groups, 23 better, pooled contrast
   2.17454235119546; blocked jackknife (35 blocks) mean 8.016229062074508, [2.3522839485988065, 13.68017417555021],
   flag false; band 0.9175581931137083; the locked verdict_without (from verdict.json) "helps", 5.206781299700313
   [1.9722236985140444, 8.441338900886581]. The same block for pm25, ndvi, fire and defo (with == without there).
G8 Part 604 cross-check (results_coral.json, methods C, T, M1, M2): the adopted arm per survey programme (n and MAE)
   equals method C: AGRRA n 1 5.540752183604888; FRRP n 190 7.659652365514182; McClanahan n 189 35.05979452499404;
   Reef_Check n 1,932 3.829490304207522. The twin on every row = method T = M1 = 6.14748576299595 (R15 6.147;
   per programme FRRP 7.736388261777524, Reef_Check 4.022595138987255 as in A8); the even blend on every row = M2 =
   M3 = 6.393951387338696; the whole-window ratio mean|A - T| over all 2,312 test rows / R = 4.2913410523963345
   (Part 603: 4.29).
G9 History (information): `replay/WITH_WITHOUT.csv` (build 663ab8ef, before AF2) equals the gate file in every column
   except "note" (V2: "bit for bit").

## 6. Quantities to compute (only after G0-G8 pass; every one labelled POST HOC)

Item numbers refer to S5.3's [PENDING] list (1)-(9). "Labelled rows" = finite y; "saved rows" = every saved test row.
For coral, a row is a survey visit; a batch is an issue calendar month. Every number is written at full precision.

Q1 (item 1) Table S5.1b, one line per pass in the order of section 2's table (14 lines): package, run, lead, code
   status, plain status (section 2 wording), twin arm and kind, twin simpler, twin passes its skill guard (or "not
   needed"/"not saved"/"none"), replayable, saved rows, labelled rows, batches, batches with >= 30 saved rows,
   saved rows in batches with < 30 rows, batches tested (code sense, R8), batches switched, saved rows switched,
   labelled rows switched, rows whose value changed (switched rows where twin != adopted), MAE without, MAE with,
   change (with - without), change in % of without, change in units of the run's band (verdict.json band;
   information), reference gap, largest ratio among TESTED batches, largest ratio among batches with >= 30 rows
   whether or not the rule could act ("information only: the rule could not act" for inert passes). Not-replayable
   passes: MAE with, tested and switched are null (never 0).
Q2 (item 2, 3) Coral nowcast: MAE without and with (the fixed per-batch rule), the 33 tested month batches with
   their rows and ratios, the 11 switched batches and the 737 switched survey visits; also the per-batch table
   (Q1 columns per batch: key, saved rows, labelled rows, year, gap, ratio, tested, switched, MAE without, MAE with
   on that batch). Same per-batch table for the defo nowcast (4 yearly batches, ratios, none switched) and, as
   information, for the pm25, ndvi and fire nowcasts (ratios computed, none tested).
Q3 (item 4) By test year (the `year` column; at lead 0 it equals the issue year; assert every batch lies in one
   year) for EVERY replayable pass: n, MAE without, MAE with, change, and a flag better / same (bitwise equal) /
   worse; batches, batches tested, batches switched, rows switched in that year. List every test year in which the
   alarm made a nowcast worse (V3: coral 2017 and 2019). For passes where nothing switched, assert with == without
   bitwise in every year.
Q4 (item 5; NEW, never computed for the per-batch rule) Coral nowcast by survey programme (`programme` column of
   the coral run's test_preds.parquet, row-aligned with the replay rows: assert unit, time and y equal row by row;
   values AGRRA, FRRP, McClanahan, Reef_Check): n, MAE without, MAE with, change, better/same/worse flag, rows
   switched, number of switched batches holding that programme's visits. Also programme x year: the same columns
   for every (programme, year) cell that has rows. Mark AGRRA "n = 1, not interpretable".
Q5 (item 5) Contributions to the coral nowcast's net change, by programme and by (programme, year):
   contrib = (n_cell / N) x (MAE_with(cell) - MAE_without(cell)), N = 2,312 labelled rows; share = contrib / (pooled
   MAE_with - pooled MAE_without). Report the residual (sum of contribs minus the pooled change; rounding only).
   Shares above 100% (as in A8's "130%") are expected when other cells lose.
Q6 (the switching form vs the other form) Coral nowcast, four columns scored the same way (pooled; by year; by
   programme; Q7's subsets and complements; rows whose value differs from the adopted arm):
   F1 per-batch switch: the fixed v2 rule (= the with-alarm column);
   F2 per-batch even blend (INFORMATION ONLY, not the rule): on the rows of the SAME 11 switched batches, 0.5 x
      adopted + 0.5 x twin of the saved clipped label-scale values (Part 604 M2's blend, PROTOCOL.txt line 92, applied
      per batch); adopted elsewhere;
   F3 whole-window switch (Part 603's disagreement guard = Part 604 M1; on coral it is the twin on every row, 6.147,
      R15): a cross-check only, labelled "not the alarm's value (C6)";
   F4 whole-window even blend (Part 603 blend = Part 604 M2 = M3 on coral, 6.394): cross-check only.
   On the defo nowcast nothing switched, so F1 = F2 = without (assert); F3/F4 are not computed for defo.
Q7 (item 6) Outcome-defined subsets, coral nowcast (and the coral lead lines as in G1), ALWAYS beside their
   complements, each labelled "outcome-defined (selected on the test label)": y > 0 (bleached, 1,024) vs y == 0
   (1,288); y >= 50 (140) vs y < 50 (2,172); y > 23.9575 (the lead's q75 of positive donor labels, from
   magnitude_edges.csv; 239) vs y <= 23.9575. Per subset: n, MAE without, MAE with (F1; also F2-F4 under Q6), change,
   rows switched IN THAT SUBSET (not the pass total; see pitfall P2). Use y >= 50, not Part 604's y > 50 (135 rows).
Q8 (item 7) Batches too small to test, every replayable pass with a saved twin: each batch with < 30 saved rows:
   key, saved rows, labelled rows, ratio (computed, not tested), whether the ratio exceeds 2.0; totals (count, rows,
   largest ratio, count and rows of those above 2.0). INFORMATION ONLY, coral only: the pooled MAE if the small
   batches with ratio > 2.0 had also switched (the 30-row floor stays fixed). For the not-replayable leads (defo 1,
   coral 183): batch count, batches with < 30 rows and their rows (no ratio exists).
Q9 (item 8) Threshold check, INFORMATION ONLY (the threshold 2.0 stays fixed): coral and defo nowcasts at thresholds
   1.5, 2.0, 2.5, 3.0 (exactly these; no others): batches switched, rows switched, pooled MAE with, and coral by
   year. Inert passes are not re-thresholded (the rule cannot act there).
Q10 (item 9) Silence and firing: for each nowcast, one line: switched any batch (yes/no), and why not where no
   (cannot switch: twin not simpler / twin fails its skill guard; or can switch but no tested batch's ratio
   exceeded 2.0, with the largest ratio). Keep "inert" (cannot act) apart from "active, nothing switched" (defo):
   V3's "silent at the other four nowcasts" covers both.
Q11 (information; S5 use is an owner item) Coral nowcast by region (`group`): the 37 region lines with and without
   (from Q3-style scoring; equal to alarm_replay_scores.csv "group" lines), and counts of regions better, same,
   worse; the with-alarm verdict block of G7 (post hoc).
Q12 Row-level output (always save predictions): per replayable pass a parquet with unit, group, time, year, issue,
   y, batch, adopted, twin (NaN where not saved), with_alarm (F1), fired, and for the coral nowcast also programme,
   blend_batch (F2), twin_all (F3), blend_all (F4).

## 7. Output contract (each implementer, only inside its own folder)

`D:/treeroute/analysis/paper_posthoc/v2_replay/<A|B>/`:
- `replay_<A|B>.py` (and any helper); A's `tool_rerun/` (step A2 outputs only).
- `result_<A|B>.json`, with these top-level keys and the SAME schema in A and B (so part 3 can compare leaf by leaf):
  `implementer`, `script_sha256`, `python_and_libraries`, `inputs` {path: sha256}, `engine_v2_hash` (A; null in B),
  `read_engine_code` (B; [] if none), `gates` {G0..G9: {pass, details}}, `passes` (Q1, 14 entries keyed
  "<package>/<lead>"), `batches` (Q2/Q8, keyed "<package>/<lead>/<batch>"), `by_year` (Q3, "<package>/<lead>/<year>"),
  `coral_programme` (Q4, "<programme>"), `coral_programme_year` (Q4, "<programme>/<year>"), `contributions` (Q5),
  `forms` (Q6, "F1".."F4" -> {pooled, by_year, by_programme, subsets, rows_differing}), `subsets` (Q7,
  "<package>/<lead>/<subset id>" with ids all, y_gt_0, y_eq_0, y_ge_50, y_lt_50, y_gt_q75, y_le_q75),
  `small_batches` (Q8), `threshold_check` (Q9, "<package>/0/<threshold>"), `silence` (Q10), `regions` (Q11),
  `verdicts` (G7/Q11), `summary_text` (plain words, numbers only, every line tagged POST HOC; coral lines also
  CIRCULAR). Floats as JSON numbers at full precision (`repr`), NaN as null.
- `rows_<package>_lead_<L>.parquet` (Q12) for every replayable pass.
- Print a short plain summary at the end. Nothing is written outside the implementer's folder.

## 8. Part 3 (reconciliation), for the record

`D:/treeroute/analysis/paper_posthoc/v2_replay/reconcile/reconcile_AB.py` compares result_A.json and result_B.json
leaf by leaf (exact for non-floats; floats bit-equal or |rel| <= 1e-12, every non-bit-equal leaf listed) and the
row-level parquets column by column (bitwise). Only when A and B both pass every gate and agree is the Part logged,
with both script hashes, the result hashes and the reconcile output; then PAPER_FACTS V3 is re-statused "final, post
hoc (Part N)" and S5.3 is filled, each number labelled post hoc and the coral numbers labelled circular (A8).

## 9. Rules (restated from the workflow; binding)

- Never edit, move, rename or delete any file under `engine/treeroute`, `D:/treeroute/engine*` (engine_v2
  included), `D:/treeroute/runs`, `D:/treeroute/rivals_*`, `D:/treeroute/human_*`, `D:/adaptation`, `D:/pm25_*`,
  `D:/run89full`, `D:/defo_*`, `D:/treeroute/coral_build`. Write only in your own `A/` or `B/` folder. Never delete
  any file.
- `sys.dont_write_bytecode = True` before importing any engine or tool code; run with `py -3.9 -I -B`.
- Numbers only from the named files or your own code; no invented values; no rounding before the JSON.
- Wording in any text you write: "post hoc" on every result; coral "circular"; never "leave-one-region-out" or
  "pre-registered" (the tools' printed ALARM_ORIGIN sentence uses words the paper does not use: do not copy it);
  "fixed" rule, not "frozen"; "decline", not "fall back"; no hype words; losses as visible as gains; coral's
  2016-2019 window was set by hand.
- No new thresholds, subsets, floors or forms beyond those listed (no tuning). Information-only items stay
  information only; the threshold 2.0 and the 30-row floor are fixed.

## 10. Pitfalls (read before coding)

P1 "Tested" has one meaning: the code's (R8). pm25, ndvi and fire nowcasts have 48 batches with ratios computed but
   0 tested; ALARM_REPORT section 3's "48/0 (max 1.75)" means "48 ratios computed, 0 switched". Report both counts.
P2 WITH_WITHOUT.csv repeats the pass totals (batches_tested 33, batches_fired 11, rows_switched 737) on every coral
   subset line; Q7's "rows switched in the subset" is a different, subset-specific count. Do not "fix" the gate file.
P3 6.120 (the per-batch rule, the alarm's value) vs 6.147 (the twin on every row: Part 603's whole-window switch,
   R15) vs 6.15 (an old rounded text). C6: S5 quotes 6.120 for the alarm.
P4 Saved vs labelled rows: batch sizes count saved rows (pm25 91,440 saved, 91,428 labelled; ndvi 95,184 / 94,527;
   fire 96,000 / 94,702; defo 369,096 both; coral 2,312 both). MAEs use labelled rows.
P5 Grid batch keys are "step:<issue step>" (pm25/ndvi/fire monthly steps, defo the year); coral's are "YYYY-MM".
   Map a step to its year with the rows' `year` column at lead 0, not by arithmetic on the step number.
P6 The subset edges: y > 0; y >= 50 (not > 50); the q75 edge 23.9575 at the nowcast (22.22 at 183 d, 22.5 at 365 d).
P7 Coral 2018: with == without bitwise (no batch switched in 2018); say "unchanged", not "0.000 better".
P8 Defo's twin is the plain twin (answer type), because the region router has no error-weighted arms.
P9 A's tool re-run must not reuse `--out` folders that already exist with other content (the tools refuse); use a
   fresh `A/tool_rerun/`.

## 11. Owner items (NOT decided here; listed for the owner)

O1 Whether S5 reports F2 (the per-batch even blend; new, information only) beside the fixed switching rule, or only
   the switching rule with the whole-window M1/M2 history of S5.1.
O2 Whether S5 reports the with-alarm verdict against the training median ("helps" with and without, post hoc) and
   the region better/worse counts (Q11), or only MAEs.
O3 Whether the information-only small-batch counterfactual (Q8) and the threshold check (Q9) go into S5 text or stay
   in the Part only. S5's [PENDING] item 8 asks for the threshold check "information only"; Q8's counterfactual is
   not in the S5 list.
O4 Whether the q75-edge subset (y > 23.9575, 239 visits; present in WITH_WITHOUT.csv, not in V3) is reported beside
   the bleached and y >= 50 subsets.
O5 Record wording to fix after the Part (not a ruling, a correction for the drafting step): PAPER_FACTS V3 "silent at
   the other four nowcasts" and ALARM_REPORT section 3 "48/0 tested" blur "cannot act" (pm25, ndvi, fire) with "active,
   nothing switched" (defo); S5 Table S5.1b should keep them apart (Q10).
