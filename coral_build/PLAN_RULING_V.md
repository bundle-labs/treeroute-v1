# PLAN: the edits for owner ruling V (V1, V3, V5, V6, V7, V11)

Written 2026-10-19 by the plan agent. READ-ONLY step: nothing was edited. This file is the only file written.
Ruling: `C:\Users\<user>\Desktop\data set for reserch paper\engine\OWNER_RULINGS_2026-10-06.md:97-115`.
Build copy: `D:\treeroute\coral_build\engine` (hash `a4900984...0e5e`). Engine paths below are relative to it.

## ATTENTION (read first)

1. **V6 removes 46 of the 83 kept groups, not a handful.** Only 37 groups have a test visit. The 46 others hold
   **1,874 train visits** (16.5% of kept train rows; 1,066 sites) and **111 of the 2,046 decision-surface rows**.
   Brazil (146), Cuba and Cayman Islands (288), Hong Kong (313), New Caledonia (201), Gulf of Thailand (152) and
   Vanuatu (115) are among them. Their rows also leave every neighbour pool, because split.yaml's `excluded` drops the
   rows outside the contract checks (`package/table.py:505-507`). Verified on `coral_data/visits.parquet` (section 3.3).
   The ruling says "left out" (BUILD_REPORT.md:102-103, choice (a)). The plan does what the ruling says. **But the
   recommendation text never gave this count.** I suggest one line to the owner before the coral freeze: "V6 drops 46
   train-only groups (1,874 visits) from banks and pools; confirm (a), or take (b): they stay as train and pool rows
   and only leave the scored lists (an engine reading of R18)."
2. **V1 cannot stay inside the table-only modules.** The nowcast decline is chosen inside `layer/decide.py`, and the
   vault locks only an adoption that `decide()` registered (`labels/vault.py:374-399`, `:790`). So `decide.py`
   (a shared module that grid runs import) gets one keyword-only argument. With the argument left out, every
   existing line runs unchanged and in the same order (section 1.5). The no-op proof must be re-run after the edit.
3. The engine hash moves again (V1). The code hash of the build is expected to change; the four grid headline runs
   keep their old hash (U5).

---

## 1. V1: the decline object of the neighbour kind

### 1.1 Every place the decline target or the guard/decline baseline is chosen today

| # | Place | What it does today |
|---|---|---|
| a | `layer/decide.py:431` (`select_adoption`) | N2: an arm is eligible iff its MAE < its OWN link's trees-off MAE (`n2_eligible`, :284-294). |
| b | `layer/decide.py:423-425`, `:442-444`, `:1016-1019` | No eligible arm: declined, and the decline target is the identity trees-off (text and refusal). |
| c | `pipeline/table_passes.py:317-320` (`decision`) | Hands the trees-off arms to `LD.decide`; no other baseline. |
| d | `pipeline/table_passes.py:531-533` (`report`) | A declined nowcast scores `arm__identity_trees_off_unweighted`. |
| e | `pipeline/table_passes.py:563-565` | `beside`: "adopted link" trees-off uses identity when declined. |
| f | `pipeline/table_ladder.py:139-140` (`_decline_links`), `:262`, `:270-274` | Routes the identity trees-off as "the decline target". |
| g | `pipeline/table_ladder.py:323-326` (`_guard`) | Lead guard: pinned MAE vs its own-link trees-off MAE, then `LD.forecast_adoption` (D86). |
| h | `pipeline/table_ladder.py:482`, `:486-487`, `:504` (`run_lead`) | A declined lead adopts `trees_off_of(Link.IDENTITY)`. |
| i | `pipeline/table_ladder.py:542` (`table`) | Lead 0's adopted column = `arm__` + verdict["adopted"]. |
| j | `treeroute_report/table.py:177-179` | Lead 0's adopted column = `arm__` + verdict["adopted"]. |
| k | Docstrings: `table_ladder.py:17-18`, `:25-26`; `route/neighbour.py:961`; SPEC_NEIGHBOUR.md:278 | Name the identity trees-off as the decline target. |

The pool fallback (fewer than 12 rows) is already the donor-row median (U3; `table_router.py:201`, `:229`). It is
not changed.

### 1.2 The new behaviour (neighbour kind only)

- **One object.** In every pass the baseline is the donor-row median of the SAME DonorRows that the pass already
  uses as its U3 pool fallback (`PassPart.fallback_donor`, median set at `table_router.py:201`). Target units (y),
  clipped to the legal range (R28). Every such DonorRows is train rows at or before the pass's cut (asserted at
  `table_router.py:193-200`).
  - Decision surface (nowcast N2): per fold g, `pt.median` of fold g's guard-cut donor rows outside g's block (N5).
    Each surface row gets its fold's median.
  - Nowcast decline target on the test pass: `self.median_fit` (fit-cut donor rows; `table_passes.py:173`), which is
    already the saved column `base__donor_median` (`table_passes.py:447-450`).
  - Lead L guard (D86): the median of the lead's guard-bank donor rows (`donor_g`, `table_ladder.py:285`), which is
    the guard pass's part median.
  - Lead L decline target on the test pass: `o["median"]` (lead L fit-cut donor rows, `table_ladder.py:162`), already
    the saved column `base__donor_median` of the lead's test_preds.
- **N2 at the nowcast:** an arm is eligible iff its surface MAE < the baseline's surface MAE (strict, as D64).
  The same baseline for every link. No eligible arm: declined, decline target = `base__donor_median`.
- **D86 at a lead:** guard passes iff pinned MAE < the baseline's MAE on the guard rows. Else the lead adopts
  `base__donor_median`.
- Not changed: the D75 band pairs (each tree arm vs its own trees-off, corrector vs placebo; `table_passes.py:543-550`).
  They are not a guard or decline comparison. The verdict reference was already the donor-row median (R34).
- The identity trees-off is still routed and saved (printed beside). This keeps the lead-0 contract and the saved
  columns as they are.
- **Gate:** on the router kind read from derived.json R12 (`table_passes.py:87-90` sets `self.kind`), never a name.

### 1.3 Edits, file by file

**(1) `layer/decide.py` (shared; additive, keyword-only).**
- New frozen dataclass after `SurfaceArm` (about :690):
  ```python
  @dataclass(frozen=True)
  class DeclineBaseline:
      """Owner ruling V1: the one baseline of a kind with no normal ... key (a saved column name, never an arm
      name), rule (text), pre_clip (rows,) in y units."""
      key: str
      rule: str
      pre_clip: np.ndarray
  ```
- `select_adoption(..., *, order=None, baseline=None)` (:364). `baseline` is `(key, mae)` or None.
  None: the current body, unchanged. Given: refuse with `order` (R27: "a legacy replay has no decline baseline");
  refuse a key equal to any candidate key; `eligible = [p for p in picks if n2_eligible(p.mae, base_mae)]` instead
  of :431; `surface[key] = base_mae`. The trees-off checks (:413-429) stay in both modes (trees-off are still
  candidates and printed).
- `decide(..., *, legacy=None, gls_absent_reason=None, decline_baseline=None)` (:897). Given: refuse with
  `legacy`; check 1-D, finite, length n; `clip_with_counts` it (`clip[key]`, `clipped[key]`); `base_mae =
  surface_mae(y, clipped[key])`; pass `baseline=(key, base_mae)`; append `CandidateRow(arm=key, level=None,
  ratio=None, n, mae=base_mae)`; set `decline_baseline={"key", "rule", "mae"}` on the record. `clipped[key]` goes into
  `record.predictions`, so `_save_inner` (`passes.py:843-846`) saves it as the column `base__donor_median`.
- `DecisionRecord` (:699): new LAST field `decline_baseline: Optional[Mapping[str, Any]] = None`.
- `decision_section` (:1057): add `"decline_baseline"` only when it is not None.
- `decision_lines` (:991): when given, one line "decline baseline <key> MAE ... (V1)", and the declined line names
  `<key>` instead of the identity trees-off. Grid strings unchanged.
- `forecast_adoption` (:527): docstring only ("the neighbour kind passes the donor-row median's MAE, V1").
- `__all__`: add `DeclineBaseline`. Module docstring and provenance: add V1.
- `Adoption`, `check_adoption`, `adoption_document`, `pin_of` are NOT edited. The decline target lives in the
  locked decision section; `read_adoption` (`passes.py:875-887`) therefore needs no change on resume.

**(2) `pipeline/table_router.py` (table-only).** New method `NeighbourPass.fallback_median_rows()` -> (rows,) y:
each scored row's part median (`pt.median`, :201). Docstring cites V1 ("the check and the fallback are one object").

**(3) `pipeline/table_passes.py` (table-only).**
- Module constant `V1_RULE` (text of V1 with the file:line of the ruling) and method
  `decline_to_donor_median(self) -> bool: return self.kind == PR.KIND_NEIGHBOUR` (docstring: R12, V1).
- `decision` (:317-320): `dl = LD.DeclineBaseline(REFERENCE_COLUMN, V1_RULE, npass.fallback_median_rows()) if
  self.decline_to_donor_median() else None`; pass `decline_baseline=dl`. Add to DECISION_CHECKS (:324-337):
  `"decline_baseline": {"key", "rule", "per_fold_median": {pt.name: pt.median}}`.
- `report` (:531-533): `adopted_col = REFERENCE_COLUMN if declined and V1 else arm__<adopted>`; :563 own trees-off
  of `a.best_tree_arm.link` when declined (printed beside); verdict.json gains `"adopted_column"`,
  `"decline_target": REFERENCE_COLUMN`, `"decline_rule": V1_RULE`; `"adopted"` = `"donor_median"` when declined.
- Module docstring (:16-18): add the V1 sentence.

**(4) `pipeline/table_ladder.py` (table-only).**
- Docstring :17-18, :25-26: the decline target and guard baseline are the donor-row median (V1).
- `_decline_links` (:139) -> `_beside_links`, same body; docstring "printed beside, no longer the decline target".
- `_guard` (:320-347): `base = self.last_pass.parts[0].median`; assert it equals
  `M.baseline_donor_median(donor_g)` (G-PLUMB refusal if not); `base_v = clip_to_legal(np.full(n, base), legal)`;
  `mae_base = LD.surface_mae(y, base_v)`; comparator `mae_base if s.decline_to_donor_median() else mae_off`. Save
  `base__donor_median` in guard_preds.parquet. lead.json guard: `baseline_column`, `baseline_value`, `baseline_mae`,
  `baseline_donor_rows`, `baseline_rule`; keep `own_trees_off_mae` (beside). Log line names the baseline.
- `run_lead` (:482-491): declined -> `adopted_column = REFERENCE_COLUMN`, `"decline_target": REFERENCE_COLUMN`;
  `own_trees_off_column` = the pinned link's trees-off (beside). :504 log text.
- `table` (:542): `info[0]["adopted_column"] = verdict["adopted_column"]` (a table run always writes it).

**(5) `treeroute_report/table.py` (report tooling, shared).** :178:
`self.verdict.get("adopted_column") or M.ARM_PREFIX + self.verdict["adopted"]`, with a comment citing V1. Grid
verdicts never carry the key.

**(6) `route/neighbour.py`:** docstring :961 only ("the identity trees-off, printed beside"). Optional.

`report/metrics.py`: no change. `single_verdict` with adopted == reference gives IDENTICAL, then DECLINED
(:1163-1166); grids already take this path (a declined grid adopts its own reference).

### 1.4 Where V1 is written

| Output | New content (table runs only) |
|---|---|
| adoption.json (locked) | `decision.decline_baseline` {key, rule, mae}; `surface_mae["base__donor_median"]` |
| inner_preds.parquet / inner_candidates.csv | column / row `base__donor_median` (per-fold medians) |
| decision_checks.json | `decline_baseline` with the per-fold medians |
| ladder/lead_L/guard_preds.parquet, lead.json | column `base__donor_median`; guard `baseline_*`; test `adopted_column`, `decline_target` |
| test_preds.parquet (all leads) | unchanged (`base__donor_median` is already saved) |
| verdict.json, ladder.json | `adopted_column`, `decline_target`, `decline_rule`; a declined lead's adopted = `base__donor_median` |

### 1.5 Why grids are untouched

- Grid runs never import `table_passes`, `table_ladder`, `table_router` (BUILD_REPORT.md:44-45: `is_table_package`
  moved to `package/load.py:297`; the no-op proof compares the module list).
- Grid runs import `layer/decide.py`. Its grid callers pass no new keyword: `pipeline/passes.py:772`,
  `pipeline/ladder.py:825`, `legacy_harness/layer_replay.py:565-755`. With `decline_baseline=None` the statements run
  as today; `DecisionRecord.decline_baseline` is None, `decision_section` adds no key, the candidate table is the same,
  so adoption.json and its hash are byte-identical. No new module is imported.
- `treeroute_report/table.py`: the `.get` returns None on every grid verdict, so the old expression runs.

### 1.6 Tests

Tests that pin the OLD behaviour: none in the table tests (`grep` of tests/: no table test names the identity decline).
`tests/test_layer_decide.py:161-177` pins the grid decline to the identity trees-off: it must pass UNCHANGED (grid
evidence). `tests/test_pipeline_ladder.py`, `tests/test_pipeline.py`, `tests/test_report_table.py` likewise.

New file `tests/test_table_v1_decline.py`:
1. `decide` with a `DeclineBaseline`: an arm that beats its own trees-off but not the baseline declines; an arm that
   beats the baseline but not its trees-off is adopted; a tie with the baseline is not eligible (strict).
2. The record and document: `surface_mae` has the key; `decision_section["decline_baseline"]`; the candidate row; the
   clipped column in `record.predictions`.
3. Refusals: with `legacy`; wrong length; NaN; a key equal to an arm name.
4. `decline_baseline=None`: `adoption_document(record.adoption, record)` equals the one from a call without the
   keyword (byte for byte), and has no `decline_baseline` key.
5. Toy end to end (`table_toy`, one module-scope run): adoption.json names `base__donor_median`; each lead.json has
   `guard.passed == (pinned_mae < baseline_mae)`; `baseline_value` equals the guard pass's part median.
6. Forced decline (monkeypatch `LD.n2_eligible` to return False; one more toy run): verdict.json `adopted_column ==
   "base__donor_median"`; each lead adopts it; ladder.json tags DECLINED; the report table builds and reads
   `adopted_column`.
7. Gate: `TableRunState.decline_to_donor_median()` follows `self.kind`; `tests/test_nonames.py` passes.

Lean run while working: the new file, `test_layer_decide.py`, `test_table_mode_pipeline.py`, `test_report_table.py`,
`test_pipeline_ladder.py`, `test_nonames.py`, `test_noknob.py`. Then the tiny smoke (23 s): leads 183/365, if still
declined, must now score the donor median (3.896 on the tiny data; BUILD_REPORT.md:73-77). Owner afterwards:
`run_noop_proof.ps1` (must end RESULT: PASS) and the one full suite.

---

## 2. V3: test window 2016-2019, sensitivity 2017-2020

### 2.1 Verified

- `coral_data/visits.parquet`: 38 visits marked `unused`, all dated 2020, in 5 groups. Census `test_years [2016,
  2019]`, `visits_unused_after_window 38`.
- The default already gives 2016-2019: `coral_tables/build_visits.py:271` (`--test-years 2016-2019`); the rule is
  SPEC_CORAL_TABLES.md:89-114. **No code change is needed for the headline window.**

### 2.2 Package edits (text only)

- `engine/datasets/coral_draft/exceptions.yaml`: new entry:
  ```yaml
  - kind: disclosed_defect
    check: R3
    decision: 'test window 2016-2019, set by leaving out the 38 visits of 2020 (owner ruling V3); 2017-2020 is the declared sensitivity row'
    reason: 'Signed R3 on all the data gives 2017-2020. The owner signed this departure on 2026-10-19 (OWNER_RULINGS_2026-10-06.md:105). The rule came after the yearly counts were seen (SPEC_CORAL_TABLES.md:19-21, 89-114).'
    owner: 'owner ruling V3 (2026-10-19)'
    date: '2026-10-19'
  ```
- `dataset.yaml` header comment: one line "Test window 2016-2019 (ruling V3); 2017-2020 is the sensitivity row."
- `ingest/README.md`: the V block of section 5 below.
- Builder: `build_visits.py:3` docstring and README.md:94: "2016-2019 is signed (V3)". `check_tables.py`: no change.

### 2.3 How the 2017-2020 row would be produced (later; not run now)

Needed builder edits (small, package side; defaults unchanged):
- `build_tables.py:75-78`, `:797-803`: a `--visits-dir DIR` option (default `coral_data`). VISITS =
  `DIR/visits.parquet`; output `DIR/<build>/`. `publish()` (:773) takes the same option.
- `check_tables.py:52`, `:324-332`: the same `--visits-dir`.

Commands (owner, after the headline run; each one heavy job alone):
```powershell
Set-Location D:\treeroute\coral_build\coral_tables
py -3.9 -u build_visits.py --test-years 2017-2020 --out D:\treeroute\coral_build\coral_data\sens_2017_2020
py -3.9 -u build_tables.py --build full --visits-dir D:\treeroute\coral_build\coral_data\sens_2017_2020
py -3.9 -u check_tables.py --build full --visits-dir D:\treeroute\coral_build\coral_data\sens_2017_2020
py -3.9 -u make_split.py --build-dir D:\treeroute\coral_build\coral_data\sens_2017_2020\full --package <sens package>
```
- A package copy `coral_sens_2017_2020` (name, store line and its own split.yaml differ; generated like
  `write_tiny_package`, `build_tables.py:740-768`). Its header: "declared sensitivity row (V3); never the headline".
- R3 then gives 2020, R5 2017-2020, the cuts move one year. Its own V5/V6 lists are recomputed (rough count from
  the stage-1 flags: about 1,493 test visits in 29 groups before exclusions; the stage-1 rerun gives exact counts).
- Run from LIVE: check, smoke, run. Reported as the sensitivity row with a not-headline reason. It is declared in the
  coral pre-registration Part with these commands.

---

## 3. V5 and V6: groups left out in split.yaml

### 3.1 V5 list (verified: census and a recount from visits.parquet with the six cuts of the census)

| Group | Reason | Test | Train |
|---|---|---:|---:|
| Gulf of Guinea to Sierra Leone | 0 train rows at all 6 cuts (O13) | 18 | 0 |
| Kimberley Coast, north-west Australia | 0 train rows at all 6 cuts (O13) | 10 | 0 |
| North-west Arabian Sea | 0 rows at all 6 cuts (O13); one site (O14) | 1 | 0 |
| Birds Head Peninsula, Papua | 0 rows at the 3 inner/guard cuts (O13) | 6 | 1 |
| Ashmore Reef; Gulf of California; Houtman Abrolhos Islands; Line Islands; Pompey and Swain Reefs; South China Sea; Southern Seychelles | one site (O14) | 0 | 8 |

Total 11 groups, **35 test, 9 train** visits: matches SPEC_CORAL_TABLES.md:27-29, :141-155, P6 (:374), P23 (:391).
The draft split.yaml already holds exactly these 11 (`engine/datasets/coral_draft/split.yaml:13-24`).

### 3.2 V6 list (46 groups with no test visit after V5)

Austral Islands, French Polynesia; Bay of Campeche, Yucatan, Gulf of Mexico; Bermuda; Bismarck Sea, New Guinea;
Brazil; Caroline Islands, Micronesia; Cenderawasih Bay, Papua; Chagos Archipelago; Christmas Island, Indian Ocean;
Cocos Keeling Atolls, Indian Ocean; Cook Islands, south-west Pacific; Coral Sea; Costa Rica and Panama, Pacific coast;
Cuba and Cayman Islands; Eastern coast South Africa; Flower Garden Banks, Gulf of Mexico; Gilbert Islands, west
Kiribati; Gulf of Aden; Gulf of Thailand; Gulf of Tomini, Indonesia; Hong Kong; Honshu, Japan; Johnston Atoll, north
central Pacific; Marianas; Marshall Islands; Milne Bay, Papua New Guinea; New Caledonia; North Mozambique coast; North
Myanmar and Bangladesh; North Sri Lanka and east India; North Vietnam; Northern Seychelles; Ogasawara Islands, Japan;
Palau; Phoenix Islands, central Kiribati; Pohnpei and Kosrae, Micronesia; Samoa, Tuvalu and Tonga; Shikoku, Japan;
Socotra Archipelago; South Mozambique coast; South Red Sea; South Ryukyu Islands, Japan; South Vietnam; Vanuatu; West
Sumatra; Western Tuamotu Archipelago, central Pacific.

### 3.3 Counts after V5 + V6 (lead 0, from visits.parquet)

| | Before split.yaml | After V5 | After V5 + V6 |
|---|---|---|---|
| Groups | 94 | 83 | **37** |
| Train visits | 11,347 | 11,338 | **9,464** (Reef_Check 4,965, FRRP 2,185, Donner 1,805, AGRRA 504, mixed 5) |
| Test visits | 2,347 | 2,312 | **2,312** (Reef_Check 1,932, FRRP 190, McClanahan 189, AGRRA 1) |
| Decision-surface rows (2013-2015) | | 2,046 | **1,935** in 25 groups |
| Sites | | | 7,065 |

R12 on the 37 groups: h = 1.0, still the neighbour kind. No kept group loses rows, so O13/O14 still hold for them.
The overlap blocks change (two of the five 2-group blocks leave whole; West Sumatra leaves its block); the engine
derives them again.

### 3.4 Package edits

- New script `coral_tables/make_split.py` (package side). Input: a built `lead_0.parquet` (keys and mark only) plus
  the census cuts; or `--census` before stage 2. It computes O13 (0 present train rows at any of the six cuts), O14
  (one site), then V6 (no test row after V5). It writes `split.yaml` with: `excluded` = V5 + V6 with reasons;
  `seen_during_design` = the other 37 (the schema refuses a group in both lists, `split.py:227-235`). It prints the
  counts. `--check` recomputes and exits 1 if split.yaml differs. Writes only under D:\treeroute\coral_build.
- Run it now from the census (the stage-2 build is not done). After the full build: `make_split.py --check` on
  `lead_0.parquet` (stage 2 may drop rows by the MMM rule, SPEC_CORAL_TABLES.md:99-100). If a group changes, rewrite
  and say so. The engine still refuses loudly at plan (R19) or report (G-SPLIT) if the list is wrong.
- `split.yaml` reason texts: V5 rows: `'excluded by owner ruling V5 (2026-10-19): <the old fact>'`; V6 rows:
  `'excluded by owner ruling V6 (2026-10-19): no test-window visit after V5 (train visits: N); under leave one
  region out a group with no test row cannot be scored (G-SPLIT, BUILD_NOTES_table.md:68-79)'`. Header comment:
  replace "OWNER ITEM ... this list empties" (:5-9) with the signed V5/V6 text and the counts of 3.3.
- `exceptions.yaml`: one `test_exposure` entry, check G-SPLIT: "57 groups excluded (V5: 11, 35 test and 9 train
  visits; V6: 46 train-only groups, 1,874 train visits); scores cover 37 ecoregions; their rows also leave the
  neighbour pools". Edit the existing test_exposure reason (:76-81) only if its "every group" wording is now wrong.
- `ingest/README.md:39` row: "split.yaml | 57 groups excluded (V5: 11 refused by the engine defaults; V6: 46 with no
  test visit); 37 groups seen during design".
- The tiny package: its 4 groups each have test rows (63, 81, 75, 49), so `excluded: {}` stays. Regenerate it
  (`build_tables.py --build tiny`, 3 min) so the copied exceptions.yaml and README match the draft.

---

## 4. V7: the toy-only legacy replay harness (N18)

### 4.1 Layout (outside the engine)

```
D:\treeroute\coral_build\replay\
  README.md          what it checks, how to run, pass/fail
  run_replay.py      entry point; takes only --out (default replay\out); refuses any data path
  legacy_lines.py    verbatim copies of the legacy lines, with provenance and a self-check
  toy.py             the toy rows (engine/tests/table_toy.py, imported read-only)
  out\               replay_report.json, differences.csv, rows_lead0.parquet, rows_lead365.parquet, replay.log
```
Command: `py -3.9 -u D:\treeroute\coral_build\replay\run_replay.py` (from `D:\treeroute\coral_build\engine`, so
`treeroute` is the build copy). Target: under 2 minutes, under 1 GB.

### 4.2 Inputs (toy only)

- `table_toy.build_toy_table_package(replay\work)` writes the synthetic package (5 groups, about 300 rows, 6 tree
  features, 2 context columns, leads 0/183/365; `tests/table_toy.py:1-30`). The harness reads its lead 0 and lead 365
  parquet files with pandas. These are synthetic labels; no real package and no vault is involved. Any other path is
  refused (the harness takes none).
- Bank: 12 trees per group, the legacy recipe (`adaptation.py:1531-1540`: depth 8, leaf 5, max_features 0.15, bag
  max(30, 0.8n)) on train rows at or before the cut. Both sides get the SAME answer matrix. The bank is not under test.
- Cut: 31 Dec of the year before the first toy test year; at lead 365 the cut minus 365 days. Issue day = target day
  minus the lead.

### 4.3 Legacy lines (copied, never imported: adaptation.py parses arguments on import)

- `haversine` (`coral_architecture.py:143-147`), `solve_local` and `_solve_local_dual` (`coral_architecture.py:179-254`)
  with one marked edit: `o` becomes a parameter (default 2).
- The pool and fit loop (`adaptation.py:1610-1666`) as a function with switches: mask (`strict-at-issue` / `full`),
  date basis (issue / target), fallback (median / train mean), sort (stable / default), design o (1 / 2 with MMM).
- Self-check: the harness re-reads the two legacy files as text (read-only) and checks each copied span equals the
  source lines, apart from the marked edits. It records each file's SHA-256 and line span.

### 4.4 What it runs and the pass/fail criteria

Step 1, aligned (lead 0 and lead 365). The legacy loop gets: train rows at or before the cut as candidates, eligible
= dated strictly before the issue day and not the row, W = 1, o = 1 (no MMM), the engine's Z (`pool_feature_z`) and
standardised context, stable sorts, the median fallback, and the tree columns of the engine's drop set.

| Id | Check | Pass |
|---|---|---|
| P1 | Pools: engine `neighbour_pools` vs legacy `sel`, every scored row | identical index arrays |
| P2 | Local fit given the SAME pool and columns: engine `_route_neighbour_at` / `_route_neighbour_grid` vs legacy `solve_local` | max abs diff <= 1e-9 in link space, all 35 grid points, links identity, log_c, arcsine |
| P3 | Trees-off and no-tree rows: engine trees-off vs legacy `solve_local` with ntree = 0 at the base point | <= 1e-9 |
| P4 | Fallback rows (planted: a row with under 12 eligible rows) | both equal the donor median within 1e-12 |
| P5 | Legacy copy self-check | every span equal |
| P6 | The strict pool matters on the toy: difference (a) changes at least one pool | at least 1 row (else WARN: the toy does not exercise the leak) |

Exit 0 when P1-P5 pass; exit 1 otherwise. P6 is a warning only.

Step 2, one difference at a time (report only, never a selector). For each: rows whose pool changes, rows whose
prediction changes, max |delta|, MAE delta in y (clipped to [0, 100]) against the aligned run:
(a) legacy `full` mask: test rows and later rows enter (Part 458); this is "how the strict pool changes it";
(b) target date instead of issue date at lead 365; (c) pool groups' trees kept (own block only);
(d) training-mean fallback; (e) numpy default sort; (f) donor-median NaN fill in Z over all donor rows;
(g) MMM unpenalised (o = 2, with a toy context column as MMM); (h) legacy GLS weights (in-sample spread forest,
percentiles over train and test rows, `adaptation.py:1564-1568`); (i) constant Z columns not zeroed.
Row-level predictions of every case are saved (rows_lead*.parquet), not only the counts.

---

## 5. Disclosure text (package ingest/README.md, new section "Signed answers, ruling V")

- V1: For the neighbour kind, every decline falls back to the donor-row median, and every guard compares with that
  same median. Grid kinds keep their old rule until the next engine version.
- V2: The signed pool-drop default stays. The full run reports the share of rows with no tree left (n_rows_no_tree).
- V3: Test window 2016-2019, by leaving out the 38 visits of 2020. Signed after the yearly counts were seen.
  2017-2020 is the declared sensitivity row.
- V4: The table departures (TABLE_DEPARTURES) are accepted at the coral freeze, as S21 did for grids.
- V5 / V6: 57 groups are left out in split.yaml: 11 that the engine defaults refuse (35 test visits) and 46 with no
  test visit (1,874 train visits). Scores cover 37 ecoregions.
- V7: A toy-only replay compares the ported router with the legacy lines before the full run (replay\).
- V8: The feature-space step uses tree features only; season reaches the router as context (H3).
- V9: The 1-day SST/cyclone gap, the assumed ERSST V6 timing and DMI as conditional are kept.
- V10: The table checker recomputes 53 of 74 columns; the other 21 rest on the builder's canary.
- V11: The stale r36 test was fixed. Known package-data failures: test_catalog_timing_facts.py (3), the defo package
  tests (6); the launcher tests fail only in subset order (7).
- V12: Only trees_off_neighbour is wired in route/kinds.py; the other approved neighbour names raise.

---

## 6. V11: the stale r36 test

- File: `engine/tests/test_route_kinds.py:176-178`.
- Today: `test_the_r36_tolerance_refuses_until_k_is_set` expects `UnsetConstantError`; C9 is set
  (`engine_constants.py:159`).
- New:
  ```python
  def test_the_r36_tolerance_is_k_times_s_with_the_floor():
      # owner ruling V11 (OWNER_RULINGS_2026-10-06.md:113); C9 set by ruling N
      assert R.r36_tolerance(1.0) == max(K.GUARD_TOLERANCE_K, R.r36_floor())
  ```
  `K` and `R` are imported at :10 and :12. `UnsetConstantError` (:11) is then unused; drop that import. Tests are not
  in the engine hash.

---

## 7. Order of work and files touched

1. V11 (test only). 2. V1 engine edits + new test file; lean tests; tiny smoke. 3. V3/V5/V6 package text,
`make_split.py`, `--visits-dir`; regenerate the tiny package; tiny smoke again. 4. V7 harness; run it (minutes).
5. Owner: `run_noop_proof.ps1`, then the one full suite.

Engine files: `layer/decide.py` (shared, additive), `pipeline/table_passes.py`, `pipeline/table_ladder.py`,
`pipeline/table_router.py`, `treeroute_report/table.py` (shared, `.get`), optional docstring in `route/neighbour.py`.
Tests: `tests/test_route_kinds.py`, new `tests/test_table_v1_decline.py`. Package: `datasets/coral_draft/{split.yaml,
exceptions.yaml, dataset.yaml, ingest/README.md}`. Builder: `coral_tables/{make_split.py (new), build_tables.py,
check_tables.py, build_visits.py docstring, README.md}`. New: `replay\`. Old copies of edited files move to
`D:\treeroute\coral_build\_moved\v_<name>\` first (nothing deleted).

### Open choices (defaults taken; say if you want the other)

- Surface baseline: per-fold medians (the U3 fold fallback, N5). Other: one median of all guard-cut donor rows.
- A declined nowcast writes `"adopted": "donor_median"` plus `"adopted_column"`. Other: keep the arm-name field empty.
