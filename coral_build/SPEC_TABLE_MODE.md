# SPEC: the engine's generic TABLE option and the neighbour router

Written 2026-10-19 under owner ruling U (engine/OWNER_RULINGS_2026-10-06.md:84-95). Revised the same day after three
skeptic reviews (grid safety, leakage, feasibility); the REVIEW LOG is at the end. Design only. Nothing is built yet.
Every path below is under `D:\treeroute\coral_build\engine\` unless it starts with a drive letter.
"file:line" points at the build copy, which today equals LIVE (engine hash 65a177bc...).
Signed rules win over this text. Where no rule covers a choice, the default is listed in section 7.
SPEC_NEIGHBOUR.md details section 4. Section 4.0 below is the ONE reconciled text both specs follow.

**ATTENTION (read first)**
- **One idea carries the whole design: in a table run, each table ROW is the engine's "unit".** The rows become a
  keys-only DenseGrid with ONE step (`io.steps.build_dense_grid(row_ids, groups, zeros, (0, 0))`,
  treeroute/io/steps.py:476-536). FitContext, the bank, the tree-answer store, decide(), the locks and the
  metrics then run UNCHANGED. Only a thin vault subclass swaps "step" for "day" (section 3.4).
- **Grid code is not edited where it runs.** The grid LIMITS and DEPARTURES in pipeline/run.py:131-201 stay
  byte for byte. Table runs carry their own lists. Eleven shared files get small gated or purely additive edits
  (section 5). An agent-run grid tripwire compares LIVE and the build copy byte for byte in the Fix phase (5.10).
- **The pool horizon of every pass is that pass's own bank cut** (signed R14: "a pool of labelled rows at or
  before the lead's cut", APP_PLAN.md:239). U4's per-row filter "target day before the issue day" applies on top.
  Every per-pass constant (scalers, Z, fallback median, c, GLS model) comes from rows at or before that cut.
- **GLS arms are built for the neighbour kind** (signed R24, R25, R13: "per held-out group for neighbour",
  APP_PLAN.md:238, :259, :260). This needs two additive functions in fit/ (5.11, 5.12).
- **The verdict reference is the donor-row median** (signed R34 and G-DECIDE, APP_PLAN.md:274, :319, :619;
  `M.REFERENCE_DONOR_ROW_MEDIAN`, report/metrics.py:131). Neighbour trees-off is printed beside it.
- **Owner items that can block coral:** a group with 0 rows at any of the 6 bank cuts is refused at plan time
  (O13); a one-site group is refused by the overlap-block rule (O14); the marks must equal the derived test
  window (O1). Each has a listed alternative.
- **Signatures that need an owner signature** (each is a not-headline reason until signed, 3.6):
  `neighbour_pool_loro` gains a keyword `row_issue_day`; route/solve.py's solvers gain a keyword `n_unpenalised`
  (default 2, bytes unchanged); the approved `route_neighbour_loro` stays unbuilt and a private kernel runs instead
  (like per-unit and region, departure `private_router`, run.py:177-178); two new fold entries for the GLS model:
  `FitContext.donor_rows_outside` and `fit.weights.weight_models_for_folds` (5.11, 5.12).

---

## 0. Words used here

- **sample row**: one row of a table: one survey (or any sample) with its group, unit, date, label, features.
- **package unit**: the package's own unit (for example a site). Kept as a column. Used for R12, overlap
  blocks, persistence and reports only.
- **engine unit**: the sample row (its row id). Used by FitContext, the vault, R18 lists, saved rows.
- **day**: a proleptic Gregorian ordinal (`datetime.date.toordinal()`), the engine's Day (io/steps.py:234-236,
  timing/calendar.py:79-84).
- **lead L**: days. Nowcast L = 0. Event leads come from R10: 183 and 365 (derive/rules.py:1009-1069; ruling I1).
- **issue day**: target day minus L.
- **horizon of a pass**: the pass's own bank cut (R14). Decision surface: lead 0's guard cut. Nowcast test pass:
  lead 0's fit cut. Lead-L guard surface: lead L's guard cut. Lead-L test pass: lead L's fit cut
  (timing/cuts.py:62-87, 211-222).

---

## 1. THE TABLE CONTRACT

### 1.1 How a package says "table"

`dataset.yaml` gains one declared field. Everything else keeps its meaning.

```yaml
name: <package>
version: '0.1.0'
owner: '<owner>'
description: '<one line>'
input: table                                   # new; default 'grid' (every existing package)
stores:
  target: 'D:/<store root>/lead_{lead}.parquet'  # one file per lead, {lead} = days
includes: []
```

Schema rules (package/schema.py, DatasetFile at :246-260, StorePaths at :229-236):
- `input: Literal["grid", "table"] = "grid"`.
- `StorePaths.static` becomes `Optional[NonEmptyStr] = None`. A DatasetFile validator keeps it required when
  `input` is `grid` (same outcome for every grid package).
- `input: table` requires: `stores.target` holds exactly one placeholder, `{lead}`, and no other `{...}`;
  `static`, `drivers`, `globals`, `features` are absent or empty; `includes` is empty (a table has no store
  facts). `input: grid` refuses `{lead}` in any template.
- `{lead}` is NOT added to io/listing.py's placeholders (io/listing.py:47-53). The table reader fills the
  template itself (section 3.3). The freeze's `template_files` already globs any `{...}` (treeroute_report/
  freeze.py:397-407), so F-STORES works unchanged.

### 1.2 Files

- One parquet file per lead. The leads are 0 plus R10's leads: `lead_0.parquet`, `lead_183.parquet`,
  `lead_365.parquet` (the number written as a plain decimal).
- A missing file is refused. Any other file that matches the template's glob is refused (an unknown lead).
- The files may live inside the package's `data/` folder (not part of the package fingerprint, package/load.py:13-16)
  or in an outside store. The run's data manifest hashes each file's CONTENT (they are small), so the run
  fingerprint covers them. The owner adds the store root to protected_roots.txt. That root must be a folder no
  builder writes to any more (a published copy; for coral see SPEC_CORAL_TABLES.md 4.1).
- The lead-0 file defines the sample set. A lead-L file holds a subset of its row ids (section 1.6).
- ingest/ and features/ may hold the scripts that BUILD the tables. In table mode the engine never executes
  them: no target reader, no feature hook (pipeline/data.py:149-160 is not called).

### 1.3 Columns, roles and dtypes

Every column of every file is declared in `catalog.yaml`, and every declared column is in every file.
An extra or missing column is refused (closed world on columns).

Six roles are added to `ROLES` / `Role` (package/schema.py:383-386). With the three old key roles they form
`TABLE_KEY_ROLES` (9 roles), defined in package/table.py. They are KEY roles: never a tree feature, never a
verdict. The loader refuses the six new roles in a grid package, and refuses a table package without them.
No shared KEY_ROLES tuple is edited (io/apply.py:51, pipeline/data.py:60, check/facts.py:16, check/guards.py:48,
derive/orchestrate.py:96, io/sentinel.py:36). Table code removes the 9 key columns before it calls
`apply_verdicts` (which refuses an unknown role, io/apply.py:229-230) or any grid guard.

| Role | Count | dtype in parquet | Rule |
|---|---|---|---|
| `key_row` (new) | 1 | string | Non-empty, unique in a file. The same id means the same sample in every lead file. |
| `key_unit` | 1 | string | Non-empty. A package unit belongs to one group. |
| `key_group` | 1 | string | Non-empty group name. |
| `key_lat` (new) | 1 | float64 | Finite, in [-90, 90]. One value per package unit, in every file. |
| `key_lon` (new) | 1 | float64 | Finite, in [-180, 180]. One value per package unit, in every file. |
| `key_time`, `calendar_part: date` | exactly 1 | date32, or timestamp with no time of day, no time zone | The TARGET date: the last day the label's content covers. The label is known from the next day on. No other key_time column. |
| `key_issue` (new) | 1 | same as the target date | Issue date = target date minus L days, exactly. |
| `key_feature_end` (new) | 1 | same as the target date | The last content day that any feature or context value of this row, at this lead, may read (the package's declared window end, ruling U1). Must be before the issue date (T-FEATEND). |
| `key_mark` (new) | 1 | string | Exactly `train` or `test`. |
| `target` | 1 | float (an int is cast) | NaN = an invalid label (D30). A finite label lies in the legal range, bounds included; else refused. |
| `driver`, `engineered` | any | float or int (bool refused) | Tree features when the verdict keeps them (`io.apply.apply_verdicts`, as `pipeline.data.package_spec` does at pipeline/data.py:112-144). NaN allowed: 0-filled for the trees (R30). Infinite values, or values at or above `S5.sentinel_mask_abs` in size, are refused (missing is written as NaN). |
| `router_context` | any | float or int | Router context when kept. NaN allowed: a fit row leaves the fit (G1), a scored row is left out (S1). |
| `report_stratum` | any | string or numeric | Per-row values for report tables only. Never a feature, any verdict (as pipeline/data.py:27-31). |
| `support`, `target_twin`, `external_product` | any | as for grids | Handled by `apply_verdicts` exactly as for grids. |

Canonical row order: the row grid sorts rows by row id in plain code-point order (io/steps.py:510-515, D37).
Every bag, row-key hash and saved row follows that order.

### 1.4 catalog.yaml, ban.yaml, split.yaml, exceptions.yaml

- **Tree features vs router context**: declared exactly as for grids. Role `driver` / `engineered` with a
  keeping verdict goes to the trees; role `router_context` goes to the router. `apply_verdicts` decides.
- **ban.yaml**: one verdict per non-key column (G-CLOSED), as for grids. A `freeze` verdict is refused (R9: no
  per-cut pools, as pipeline/run.py:332-335). keep_unreviewed is refused at the freeze (F-BAN-OPEN).
- **split.yaml**: unchanged: `excluded` and `seen_during_design` only (package/schema.py:477-490). Rows of an
  excluded group are dropped after the contract checks; they never reach derive or a fit.
- **exceptions.yaml**: unchanged.
- **AUDIT_CHECKLIST.md**: required as now. It carries the owner's signed U2 statement (a human check).

### 1.5 Target facts

- `legal_range` is required, with `legal_range_source`. When the range is [0, UB] with UB finite, R22 offers
  arcsine (derive/rules.py:1301-1302). log(y + c) when the minimum is 0 or above. Identity always.
- `window` and `stamp` must be absent, or exactly `stamp: event_date` with window `{length: 1, unit: day,
  align: backward}` and no reach. Anything else is refused: "in a table the target date is the label's last
  content day; move the date instead".
- `measurement_error_floor` is optional (printed beside the hit rate, as for grids).
- No store catalog: the engine computes no lag for any column (U1).

### 1.6 Rows missing at a lead

- A row id in the lead-0 file but not in the lead-L file has **no issue row at lead L**.
- The package decides this by leaving the row out (for example: too little history before the issue date).
- What the engine does with such a row is in section 3.7 (test rows: H4; guard rows: refused, as grids; other
  rows: O15).

### 1.7 What the package vouches for (ruling U2), and what the engine checks (U1)

The engine cannot recompute hand-built features. The package owner vouches that:
1. Every feature and context value of a lead-L row uses only content dated strictly before its issue date, in
   the source's own day convention (the content-date rule of ruling N2 and the grid packages). Publication delay
   is disclosed per source in exceptions.yaml, not promised here.
2. No feature reads the row's own label, a label of any test row, or any label dated on or after the issue date.
3. The issue date column equals target date minus L (the engine checks this one: T-ISSUE).
4. The same row id means the same sample, with the same label, in every file (the engine checks this one:
   T-LEADSET).
5. The target date is the label's last content day (section 1.3).
6. `key_feature_end` is the last content day any of the row's feature windows may read. The engine checks that it
   is before the issue day on every row (T-FEATEND, U1's "no feature dated after the issue date, as the package
   declares"). The engine cannot check that the declaration is true; that part is vouched.

The engine writes this list into plan.json and run_record.json of every table run ("U2: features vouched by the
package owner"), with the largest `feature_end - issue day` per lead (always below 0). The coral pre-registration
and the paper disclose it (U2). The G-DERIVED recompute and the look-ahead canary are NOT run on tables (U2 says
the engine cannot recompute them). This closes CORAL_ENGINE_PLAN.md BLOCKER 1 by ruling, not by code.

---

## 2. DATE CHECKS THE ENGINE STILL ENFORCES

### 2.1 Contract checks (package/table.py; every file; refusal = `RefusedError` with the rule id)

Run by `treeroute check` (quick) and again by every `plan`, `smoke` and `run` before anything is fitted.

| Id | Check | Rule id |
|---|---|---|
| T-FILES | the lead files are exactly {0} plus R10's leads | U1 |
| T-COLUMNS | file columns = catalog columns; dtypes as 1.3 | G-CLOSED |
| T-NAMES | the package-unit column and every stratum column (saved under their catalog names, 3.7) are not a reserved saved column (`RESERVED_COLUMNS`, report/metrics.py:157: unit, group, time, year, lead, issue, y, normal, legal_min, legal_max) and do not start with `arm__`, `pre__` or `base__` (report/metrics.py:149-152, :1368-1370) | R34 |
| T-ROWID | row ids unique and non-empty in each file | G-SUPPORT |
| T-UNITTIME | (package unit, target date) unique in each file (the grid's repeated (unit, step) refusal) | R1 |
| T-UNIT | a package unit has one group and one (lat, lon) in every file | G-DISJOINT |
| T-ISSUE | issue day = target day minus L on every row of the lead-L file | R11 |
| T-FEATEND | feature-end day < issue day on every row of every lead file | U1 |
| T-LEADSET | every lead-L row id is in the lead-0 file, with the same unit, group, lat, lon, target date, label (bytes), mark and strata | U1 |
| T-RANGE | finite labels inside the legal range | G-RANGE |
| T-FINITE | no infinite feature or context; nothing at the sentinel size | G-SENTINEL |
| T-MARK | after derive (2.2): a train row's target date is at or before 31 December of the train end year; a test row's target date lies inside the test years; the marks equal the derived window exactly | R5, R6 |

### 2.2 Windows and cuts come from the dates (unchanged rules)

- R3 events: Y_end = the last year with any valid row (derive/rules.py:620-622, is_events True).
- R4: Y0 = the first year of any valid row; no lag sources (derive/rules.py:692-738; flag `no_lag_sources`).
- R5, R6, R7 as written (derive/rules.py:785-890).
- R11 events (timing/cuts.py:62-87, 211-222): lead 0: fit cut = 31 Dec of the train end year; guard cut = 31 Dec
  of the inner-fit end year. Lead L >= 1: fit cut = 1 Jan of the first test year minus L; guard cut = 1 Jan of
  the first inner-score year minus L. `label_usable` applies at every cut (cuts.py:91-100); with a 1-day label
  it reduces to "target day at or before the cut".
- Known one-day gap (O27): at L >= 1 the earliest test rows are issued ON the fit cut day, and `label_usable`
  keeps labels dated on the cut. So a lead-L bank, c, tolerance and median may hold a label dated on a scored
  row's issue day, which section 1.3 says is known only from the next day. The pool is strict (`<`). This is
  signed R11 code; the default keeps it and discloses it.

### 2.3 Structural guarantees (no test label reaches a fit, a selection, a guard or a pool)

- The row vault (3.4) is the only holder of labels. `_before_test` refuses any cut on or after 1 January of the
  first test year (labels/vault.py:324-331). FitContext hand-outs come only through it.
- Test labels open only through `open_test_labels` after the pass's adoption lock (labels/vault.py:665-724).
- decide() refuses a surface row in the test window or after its label cut (layer/decide.py:772-806) and runs
  `check_inner_score_rows` (fit/context.py:715-732).
- Pool assert, per scored row (route/neighbour.py): every pool row is train-marked, its target day is at or
  before the pass's horizon (its own bank cut), and strictly before the row's issue day. A breach is
  `RouteGuardError("G-FITCUT")`.
- Constant assert, per pass (pipeline/table_router.py): the newest label day of every row set a per-pass constant
  is fitted on (context scalers, Z constants, fallback median, c, GLS model) is at or before the pass's bank cut.
  The newest candidate day is at or before the earliest scored issue day (equality is the O27 day). A breach is
  `RouteGuardError("G-FITCUT")`. Logged per pass.
- Every hand-out writes its fitctx_log row (fit/context.py:495-501). The neighbour pass adds one log row per
  pass with the largest "pool day minus issue day" (always below 0).
- Every pass saves its pools (`pools_<pass>.parquet`, 3.8 step 9), so a test re-reads the lead files on their own
  and audits every pool row (6.3).

### 2.4 Which rows each pass scores

| Pass | Bank cut | Scored rows | Pool horizon |
|---|---|---|---|
| Decision surface (nowcast, R13) | lead 0 guard cut (inner-cut bank, L6 b) | train rows with a valid label, target day in (lead-0 guard cut, lead-0 fit cut] | lead-0 guard cut |
| Test pass (nowcast) | lead 0 fit cut | every test row | lead-0 fit cut |
| Guard surface, lead L (H2) | lead L guard cut | rows present at L, valid label, target day in (lead-0 guard cut, lead-L fit cut]; issue day at or after the lead-L guard cut | lead-L guard cut |
| Test pass, lead L | lead L fit cut | test rows present at L (absent ones: H4) | lead-L fit cut |

---

## 3. INTEGRATION

### 3.1 Where the pipeline branches

| Where | Today | Change |
|---|---|---|
| treeroute/cli.py:192-218 (`smoke`, `run`), :181-189 (`plan`) | call `run_pipeline` / `plan_pipeline` | none |
| treeroute/pipeline/run.py:1476-1487 `run_pipeline`, `plan_pipeline` | build `Pipeline` | try `load_dataset_file` (package/load.py:268-271); only when it succeeds AND says `input: table`, build `TablePipeline` (pipeline/table_run.py). On any exception, or `grid`, fall through to the unchanged `Pipeline(...)` call, so a grid package's refusals, messages and exit codes stay as today |
| treeroute/cli.py:103-149 (`check`) | `run_quick` / `run_deep` | none in cli.py |
| treeroute/check/quick.py:246 `run_quick`, check/deep.py:1092 `run_deep` | grid checks | first line: the same guarded read; a table package goes to `check/table.py` (`run_table_quick` / `run_table_deep`), which returns the same `CheckContext` shape (results, deep_selection); any read error falls through to the grid path |
| treeroute/check/report.py:87-103 `package_smoke_groups` | groups from the target store's `{group}` listing | a table package lists groups from the lead-0 file's group column (the freeze's F-CHECK-GROUPS calls this) |

Nothing else in cli.py, run.py, passes.py, ladder.py, stream.py, census.py or data.py changes.

### 3.2 Grid-only steps a table run skips, and what replaces them

| Grid step (where) | Table run |
|---|---|
| Target reader and feature hook (pipeline/run.py:312-335) | not loaded |
| Streamed census, its checkpoints, R30 blocks (pipeline/run.py:413-492, 786-807; derive/census.py; pipeline/stream.py) | not run. The census also refuses day lines (derive/census.py:254-261). Replaced by the contract read (3.3). |
| R1 cadence detection (derive/rules.py:326-436) | not run; R1 = irregular by declaration (O2) |
| R8 lags and R4 store first years (orchestrate.py:263-276, 586-818) | not run: no lags (U1). R8 entry = empty map with the U1 text. |
| Computed lags, last-value fill (J2 d), column readers, separability check | not run |
| Dense unit x step grid and its vault (pipeline/stages.py:86-103) | row grid + row vault (3.4) |
| R17 own-history block and the inner history pool (passes.py:365-434) | not built: R17 is empty for the neighbour kind |
| Grid pools by group (passes.py:436-509) | one pool per lead from the lead file (3.7) |
| Overlap blocks with grid indices (pipeline/run.py:946-953) | overlap blocks from the package units' (lat, lon) by the spacing rule (split.py:774-878; "point-site blocks") |
| Per-group table batching, GroupTables (passes.py:522-550) | off (`per_group=False`): a table is small; one table kind's answers held at a time (O20) |
| Moving features to the issue step (ladder.py:439-470; io.apply.features_at_issue_step) | not run: each lead's file already holds issue-date features |
| Normals, guess-normal, last-5 normal (stages.py:201-233; metrics.py:348-434) | none: the neighbour kind has no normal (R15) |
| GLS weight model (passes.py:571-580) | built: the cut's model as grids (`weight_model_for_cut`) for the test passes; one model per fold on the decision surface (5.11, 5.12; R13, R25) |

### 3.3 Reading the tables (package/table.py, new)

`read_tables(package, leads) -> TableData`:
- Fill the template with each lead, check T-FILES, read each file whole (pyarrow), check T-COLUMNS to T-FINITE.
- Convert dates to days: date32 -> `days_to_ordinals` (io/steps.py:234-236); timestamps checked for zero time.
- Drop excluded groups after the checks (split.yaml).
- Build the **row grid** from the lead-0 rows: `build_dense_grid(row_ids, groups, zeros, (0, 0))`. Row position =
  index in the sorted row ids.
- Per lead: `present` (bool per row position), issue day and feature-end day per row, tree-feature matrix,
  context matrix (float32, NaN kept), in row-position order.
- Per row position: package unit, group, lat, lon, target day, label, mark, strata values.
- `data_manifest`: per file the path, size, mtime_ns, rows, columns and content SHA-256.
- The 9 key columns are split off before `apply_verdicts` (1.3).

RAM: a plan-time pre-flight refuses when rows x columns x 8 bytes x leads does not fit (`Pipeline._refuse_ram(...,
wait=False)`, pipeline/run.py:494-512). Inside a run every RAM check waits (ruling Q1: `wait=True`), and refuses
after the maximum wait, as today.

### 3.4 The row vault (labels/rows.py, new): `RowLabelView(LabelView)`

Built with the parent constructor unchanged (labels/vault.py:180-260):
`LabelView(row_grid, target(unit_ids=row_ids, group_ids, y), times=zeros, test_first_time=<1 Jan of the first
test year as a day>, label_window_last_day=<target days>, run_folder, cadence=<Cadence(irregular)>)`.
The one-step grid passes every check there. Then the subclass:
- sets `self._steps_of_pos` to the target days (read-only). Every inherited method that reads it now works in
  days: `_usable` (:333-338), `_asof_positions` (:344-362), `_label_values` (:363-368), `validity` (:407-424),
  `donor_labels` (:426-487), `asof`, `open_test_labels` (:665-724);
- overrides `_cut_last_day(cut)` to return `cut` (a cut is a day; :322-323 reads step bounds);
- overrides `decision_surface` (:547-617): positions are the rows themselves; each given time must equal its
  row's target day (else refused); the rest is the parent's code (usable check, hash, issuer registration);
- overrides `asof_rows` (:501-545) to refuse (R17: no history block in a table run);
- adds `for_lead(present) -> RowLabelView`: the same rows and run folder, labels of rows absent at that lead set
  to NaN (recorded in the read log as "absent at lead L"). A lead's contexts, guard surface, lock and test labels
  use it. Built after the nowcast lock, it re-reads the locks from disk (`_load_folder_state`, :623-658), so
  `lock_lead_adoption` (:809-855) and `open_test_labels` work on it;
- adds `last_label_before(unit_codes, issue_days, purpose)`: per scored row, the newest valid label of the SAME
  package unit with target day strictly before the issue day, or NaN. It asserts both conditions on every served
  label. It may read test-window labels before the lead's lock (D54 a). Each call logs a read with method
  `last_label_before`, purpose, and how many test-window rows it served. Used for R31 persistence and damped
  persistence only (3.9 step 5); never an arm, a guard or a decide() input;
- overrides `test_window_reads` (:299-308) to count reads of method `asof_rows` OR `last_label_before`, so the
  lock records print the true D54 a totals. labels/vault.py is not edited.

Locks (`lock_adoption`, `lock_lead_adoption`, labels/vault.py:767-855) take the row vault unchanged
(`_check_vault` asks for a LabelView, :757-764).

### 3.5 Derive for tables (derive/table.py, new): `derive_all_table(package, data, smoke_plan) -> {entry: Derived}`

Plan-time label reads go through a `RowLabelView` built with `run_folder=None` (validity and donor views only).
Order and source of every entry:

| Entry | How |
|---|---|
| `U1:table` | files, rows per lead, rows absent per lead and mark, the file hashes, the row-grid hash, the largest `feature_end - issue day` per lead |
| `U2:vouched` | the section 1.7 list (text) |
| `R1` | `Cadence(kind=irregular)`; inputs: "declared by the table option (ruling U1)", rows, package units, repeat-visit units (O2) |
| `R2` | `R.derive_r02_season_key(cadence, None)` -> event month (rules.py:439-510) |
| `R8` | empty lag map; inputs: the U1 text |
| `R4` | `R.derive_r04_first_year(first_year, {})` |
| `R18:groups` | `split.groups_under_loro` over the lead-0 groups; G-SPLIT check as orchestrate.py:278-289 |
| `R3` | `R.count_valid_rows_per_group_year(..., present=all True, ...)` then `R.derive_r03_coverage_end(counts, groups, True)` |
| `R5`, `R6`, `R7` | the rules as written |
| T-MARK | marks against R5/R6 (2.1); refusal names the first rows |
| `R10` | `R.derive_r10_leads(season, True)` -> 183, 365 days |
| `R11` | `R.derive_r11_cuts(windows, leads, cadence)` -> day cuts |
| `R9` | `R.derive_r09_freeze_epochs({}, R.cut_days(cuts, cadence))` |
| candidates | `split.candidate_units` over PACKAGE units (a valid label at or before the train end), per group |
| `R12` | `RR.derive_r12_router_kind({package unit: valid rows from Y0 to the inner-fit end})` (one mapping, router_rules.py:148) |
| kind check | a kind other than neighbour is refused: "the table option builds the neighbour kind only (U3)" (O16) |
| `R13` | `RR.derive_r13_surface_loro(kind, groups)` (needs 3 groups or more) |
| `R14` | `RR.derive_r14_router_design(kind, context_columns)` (intercept, context, trees; neighbour centres) |
| `R14:overlap_blocks` | `split.derive_overlap_blocks(unit groups, lat, lon, None, None)` over package units |
| `R17` | `RR.derive_r17_history_spec(..., kind, True)` -> empty (after the 5.4 reorder) |
| `R18:units` | `make_derived("R18", UnitLists(bank={g: every row id of g, row-grid order}, scored={g: every test row id of g}), {"bank_units_hash": ..., "scored_units_hash": ..., "rule": "U1: the package marks train and test"})`, the same input keys as orchestrate.py:525-526 (read by run.py:1069-1076). Scored = the marked test rows replaces R18(2)'s stride pick (U1; listed in TABLE_LIMITS) |
| `R19`, `R19:inner_cut` | `UR.derive_r19_bank_plan` / `derive_r19_inner_cut_bank_plan` on the row vault's donor views at lead 0's fit / guard cut; they carry `donor_row_key_hash` (read by run.py:1061-1065) |
| `R19:lead=L:fit`, `R19:lead=L:guard` | rows per group at each lead's two cuts from `for_lead` views; a group with 0 rows refuses with R19's own message (unit_rules.py:404-407) (O13) |
| `R20` | `UR.derive_r20_batching(True, groups)` (row key unit + event date + issue date) |
| `R21`, `R21:smoke_selection` | as for grids |
| `R22` | `R.derive_r22_links(legal_range, donor at lead 0 fit cut)` |
| `R23:lead=L` | when log_c is a link: `R.derive_r23_c_for_cut` on each lead's fit-cut donor view (`for_lead`), with guard 2's rebuild |
| `R23:fold=<g>` | when log_c is a link: c from the lead-0 guard-cut donor rows OUTSIDE g's overlap block (signed R13, APP_PLAN.md:238; loro_additions.py:742-743) |
| `R28` | `R.derive_r28_clip_bounds` |
| `R30` | `MissingShares` over the R19 donor rows (train rows at the lead-0 fit cut) and the test rows per year, then `UR.derive_r30_missing_flags(shares, {})` |

Smoke (R21): the first `C13.smoke_groups` groups; in each, `C13.smoke_units_per_group` PACKAGE units by
`split.stride_pick` over the sorted package units with a valid label (validity only); every row of those units
in every lead file; `C13.smoke_trees_per_group` trees (O22). derive runs on the smoke rows, as the grid smoke
does (pipeline/run.py:87-92).

### 3.6 TablePipeline (pipeline/table_run.py, new): `class TablePipeline(Pipeline)`

After `super().__init__`, the subclass sets `self.streamed = False` and `self.per_group = False` itself, with a
comment: the base marks `streamed=False` as GATE ONLY (run.py:259-266), and the gate flag keeps that meaning on
grids. It also sets `self.census_step` to a small record whose `key` is the SHA-256 of the table data manifest
(each lead file's content SHA-256). The inherited `fit_bank` then puts it in every bank checkpoint key
(passes.py:623-625), so ruling P1's "every input file" holds with no passes.py edit.

Inherited unchanged: `__init__`, `_lock` (one heavy job, :271-298), `_release`, `_refuse_ram`, `_split_view`,
`_plan_check`, `_temp` (with its own disk plan), `_unit_list_hashes` (reads `R18:units` inputs, 3.5),
`_smoke_bank_plans` (reads the `R19` hashes, 3.5), `plan()` and `run()`.
Overridden:

| Method | Table version |
|---|---|
| `_load` (:312-350) | load_package, draft status, `table_spec` (PackageSpec-shaped: roles, tree features, context, strata, legal range, `listed_in_reports`, `frozen`; `package_spec` is not called), `self.feature_lineage = {}` with the log line "feature lineage: vouched by the package owner (U2)"; DRAFT / smoke / C9 not-headline reasons as the grid code; the `spec.frozen` refusal (run.py:329) runs unchanged |
| `_groups` (:352-378) | groups from the lead-0 file's group column; G-SPLIT check |
| `_preflight_target` (:380-411) | the table RAM pre-flight (3.3) |
| `_read` (:728-741) | `read_tables` (3.3) |
| `_derive` (:809-889) | `derive_all_table` (3.5); strata per row; `self.blocks` from `R14:overlap_blocks` |
| `_vault` (:1023-1043) | a `VaultRows` record: row grid, `RowLabelView` on the run folder, row ids, `steps` = target days per position, `window_end` = target days (1-day labels), `test_first` = the first test day. No step bounds are carried. |
| `_build_tables`, `_pass_tables` (passes.py:722-724; stages.py:112-117) | raise `PipelineRefusal("U1", "grid step helper reached in a table run")`; a test proves no grid helper that takes steps is reachable (6.2) |
| `_plan_document` (:1302-1320) | the grid keys with `limits = TABLE_LIMITS`, the U2 list, `leads` in days, `input: "table"`, `router_kind`, links, windows, groups, rows per group (bank) and test rows per group (scored), overlap blocks, `tree_features`, `context`, `listed_in_reports`, `strata`, `feature_lineage = {}` with the U2 note, the largest `feature_end - issue day` per lead, phases. `plan()` and `_open` call it unchanged (run.py:1170). |
| `_open` (:1113-1203) | the grid body with a table `config`: kind, package, package fingerprint, derived SHA-256, draft, groups, trees per group, `input: "table"`, the table data manifest, `target_files_sha256` over the lead files, empty static / driver lists, engine constants hash, feature list, context list, strata. `self.not_headline` adds `TABLE_DEPARTURES` in place of `build_departures(self)` (run.py:1123); `REC.run_record` gets `TABLE_LIMITS` in place of `LIMITS` and `TABLE_DEPARTURES` as `departures` (run.py:1144-1146), plus the U2 list. `per_group_plan.json` is not written. |
| `_preflight_disk` (:672-726) | temp disk: one pool per lead (rows x (tree + context) x 4 bytes) and, per live bank, rows x trees x 4 bytes x 3 kinds; waits (Q1) |
| `_compute` (:1391-1467) | same phase logic (decision, test_pass, report, then the ladder phases); `TableRunState` and `TableLadder` in place of `RunState` and `Ladder` |
| `_ladder_phases` | `TableLadder.phase_names`: `ladder_contract`, `ladder_lead_183`, `ladder_lead_365`, `ladder` (names as ladder.py:139-141) |

`TABLE_LIMITS` (new, in table_run.py; grid `LIMITS` untouched): Type 3 not built; table features vouched by the
owner (U2), the engine recomputes none and checks only the declared feature-end day; the neighbour kind only;
scored rows are the package's test marks (U1), not R18(2)'s stride pick; continuity row, nearest-donor distances
and report.html not built (as grids); a time-varying stratum is reported per row.

`TABLE_DEPARTURES` (not-headline reasons until the owner accepts them, as S21 did for grids, run.py:163-191):
- `neighbour_private_kernel`: the private kernel in place of `route_neighbour_loro`;
- `neighbour_pool_signature`: `neighbour_pool_loro(..., *, row_issue_day)` and solve.py's `n_unpenalised`;
- `fold_gls_entry`: `FitContext.donor_rows_outside` and `weight_models_for_folds` (5.11, 5.12);
- `table_absent_rows`: a non-test row absent from a lead file leaves that lead's banks, c, tolerances, median,
  GLS rows and pools. This departs from the accepted grid reading in `ladder_h_readings` (run.py:183-189), where
  such a row stays in the bank with 0-filled features. Reason: a table has no feature row at that lead to fill.
  A guard-surface row absent at its lead refuses, as on grids (ladder.py:44-45);
- `table_readings`: the owner items of section 7 not yet signed.

### 3.7 TableRunState (pipeline/table_passes.py, new): `class TableRunState(RunState)`

Inherited UNCHANGED from `RunState` (pipeline/passes.py:189-...): `fit_bank` (the per-group bank checkpoints,
:602-669; its key holds the table manifest key through `census_step`, 3.6), `_bank_stack`, `release_bank`,
`banks_held`, `_check_bank`, `write_log_part`, `write_fitctx_log`, `log_g1_kept`, `save_context_missing_rows`,
`_manifest_adoption`, `read_adoption`, `_save_inner`, `_preclip`, `decision_arms`, `weightings`, `gls_record`.

Overridden:
- `build_pool`: the nowcast pool `open_pool(temp, "pool", rows=row positions, tree_cols, ctx_cols)` (fit/pool.py,
  unchanged) filled from the lead-0 matrices. `ctx_fit = FitContext(derived, split_sets, row_grid, row_vault,
  pool, R18 lists, 0, FIT)` (fit/context.py:343-407, unchanged). `inner_features = pool` (no history block).
- `fit`: as passes.py:552-600: the fit-cut bank (`fit_bank`), its `TreeAnswerStore.from_bank` with
  `ST.row_group_of(vg)` (stages.py:121-128: with one step it maps a row id to its group), c
  (`c_for_cut_against_plan`), R36 tolerances (`ST.guard_tolerances`), the fit-cut donor-row median
  (`M.baseline_donor_median`, metrics.py:558-566); the inner-cut bank on `FitContext(0, GUARD)` (L6 b); the GLS
  model of the cut, `weight_model_for_cut(ctx_fit, ctx_guard, ...)` exactly as passes.py:575-583 (serves the test
  pass); and the decision surface's per-fold models, `weight_models_for_folds(ctx_fit, ctx_guard, ..., folds=R13)`
  (5.12): one forest per fold g, fitted on the guard-cut donor rows outside g's overlap block (R13, R25, L5 out-of-bag
  sigma). Each model's record goes to derived as `R25:lead=0` and `R25:fold=<g>`.
- `leave_out_score_context`: the body of passes.py:264-328 with the gate `kind == neighbour` (the neighbour router
  reads context) and years from days. Owner ruling S1 applies on every scored pass.
- `decision`: the surface rows of 2.4; S1; `row_vault.decision_surface(row_ids, days, lead-0 fit cut)`;
  `NeighbourPass(..., fold=True)` (3.8) on the inner-cut bank, with each row's fold c, fold GLS model and fold
  fallback median; each fold's c is checked against `R23:fold=<g>` (the fold twin of `c_for_cut_against_plan`,
  which checks only `R23:lead=L`, passes.py:576); SurfaceArms through `ST.inverse`; `LD.decide(surface, arms, grid,
  legal, ctx_inner)` (layer/decide.py:897-988, unchanged); `decision_checks.json` (with a `neighbour` record: pool
  counts, fallback counts, drop-set sizes, rows with no tree, and the G-PLUMB note of 3.8 step 8); `lock_adoption`.
- `test_pass`: open the lead-0 test labels after the lock; every test row; S1; `NeighbourPass` on the fit-cut bank
  at the adopted point (or the best tree penalty when declined) for every arm of `candidate_arms` (plain and
  corrector, unweighted and GLS-weighted, R24), the placebos and each link's trees-off; baselines `predict_zero` and
  `donor_median` (R31 neighbour); `M.assemble_rows` with keys `unit` = row id, `group`, `time` = target day, `year`,
  plus the package-unit column (under its catalog name) and every stratum column (T-NAMES keeps them clear of
  reserved names); `normal` = NaN on every row (allowed: metrics.py:1384-1387, 906-913).
- `hit_tolerance`: `M.hit_tolerance(fit-cut donor rows, donor-row median on every donor row)` (R32 neighbour,
  metrics.py:665-686).
- `_strata`: a string stratum is scored per value (`score_table(..., ("stratum",))`); a numeric stratum uses the
  grid rule (quartile edges from the fit-cut donor rows with a value, metrics.py:722-760). (O18)
- `report`: the grid body (passes.py:1049-1172) with the table `hit_tolerance` and `_strata`, and its own verdict
  lines (signed R34, G-DECIDE; APP_PLAN.md:274, :319, :619): `ref_col = M.BASELINE_PREFIX + "donor_median"` and
  `M.single_verdict(..., M.REFERENCE_DONOR_ROW_MEDIAN)` in place of the hard-coded `REFERENCE_OWN_LINK_TREES_OFF`
  (passes.py:1102-1103). The band and the blocked jackknife use the same contrast. `beside` holds
  `identity_trees_off_mae` (the identity trees-off, the decline target) and the adopted link's neighbour trees-off,
  not `arithmetic_normal_mae` (passes.py:1110), which would be a false label. `check_scored_units` works unchanged
  because `unit` is the row id and R18's scored lists are row ids (pipeline/record.py:178-197).

Rows absent at a lead (from 1.6): the lead-L vault view gives them NaN labels, so they are in no lead-L bank,
c, tolerance, donor median, GLS model or pool (`table_absent_rows`, 3.6). A guard-surface row absent at its lead
refuses (as grids). A test row absent at lead L is left out of scoring (H4), saved in
`ladder/lead_<L>/issue_missing_rows.parquet` with the flag `issue_features_missing`, and counted per unit (O15).

### 3.8 The neighbour pass (pipeline/table_router.py, new): `NeighbourPass`

Inputs: the run state, the pass's FitContext (its bank cut; this context is also the horizon), the pass's store,
the lead's table (features, context, `key_issue` days), score rows (row positions), c (one per pass, or one per
fold on the decision surface), the GLS model (one per pass, or one per fold), the donor rows for the fallback
median, the R14 design, the overlap blocks.

Steps of one pass:
1. Candidates: `ctx.router_rows(every train row id present at the lead, "neighbour_pool:<pass>")`
   (fit/context.py:680-713). They are train rows, valid, at or before the pass's bank cut, and the hand-out is
   logged with the pass's lead. Then owner ruling G1 (OWNER_RULINGS_2026-09-28.md:88): `ST.drop_missing_context`
   (stages.py:357-...), `log_g1_kept` and `save_context_missing_rows` (passes.py:247-262), as the grid passes do.
   The kept candidates are a `ContextKeptRows` (stages.py:286-298), which has the RouterRows fields.
2. Issue days of the scored rows come from the lead table's `key_issue` column, never from the target day. The
   pass asserts `issue = target - L` on every scored row (a second T-ISSUE at run time).
3. Context scalers: `RK.router_standardisation(candidates, candidates.context)` (route/kinds.py:456-480), applied to
   candidates and score rows with `RK.standardise_context`.
4. Z: the candidates' tree features (0-filled, R30); mean and population sd plus `RK.CONTEXT_SD_OFFSET` per column
   over the candidates; applied to candidates and score rows (4.0).
5. Fallback median and the constant assert: `M.baseline_donor_median` of the pass's bank DonorRows (decision
   surface: fold g's guard-cut DonorRows outside g's block; lead-L guard surface: lead L's GUARD-bank DonorRows;
   test passes: the lead's FIT-bank DonorRows). The pass asserts that the newest label day of the candidates, the
   fallback donor rows, c's rows and the GLS model's rows is at or before its bank cut (2.3), and logs it.
6. Per score row: `route.neighbour.neighbour_pool_loro(..., row_issue_day=<key_issue>)` (section 4) -> pool
   positions or None, drop groups.
7. Tables: `store.build(group, kind, ids, ST.zero_filled(pool))` for every candidate and score row of each group,
   per kind. Then one kind at a time: a dense answer matrix (rows x bank trees, float32), each row filled from
   its group's `unit_view` (fit/tables.py:936-959) by `tree_index`; own-group columns stay NaN and are never read
   (they are always in the drop set). A RAM check waits before the matrix (Q1) and refuses after the maximum wait.
8. Per link, kind and weighting: `route.neighbour._route_neighbour_grid` (decision surface, every grid point) or
   `_route_neighbour_at` (test and guard passes, one point). Weighted arms read `weights_for_rows(model, ...)` on
   the pool rows (fit/weights.py:648-654). The trees-off of each link comes from `trees_off_neighbour` (4.2).
9. Output: a `pipeline.router.RoutedPass` (router.py:159-168, unchanged): predictions per arm (link space),
   trees-off per link, `score_normal` empty, records `neighbour`, plumbing. The pools are saved write-once as
   `pools_<pass>.parquet`: scored row id, pool row ids in pool order, drop set, fallback flag (about 3 MB).
10. G-PLUMB (decision surface only): `LD.check_plumbing` with (trees-off, an independent closed-form ridge of the
   same pool, O10) and (the base grid point, a one-point solve at the base point) (layer/decide.py:577-632). Pair 1
   keeps its grid name `trees_off_equals_normal` (decide.py:592); `decision_checks.json` records a `neighbour` note
   beside the G-PLUMB details: "pair 1 compares neighbour trees-off with a closed-form ridge; there is no normal".

Blocks of scored rows are for progress lines only. No partial pass is checkpointed (3.10).

### 3.9 TableLadder (pipeline/table_ladder.py, new)

Per lead L in 183, 365 (R10), after the nowcast report, one phase each, then the ladder table. The order follows
the grid ladder (ladder.py:1060-1069: guard, persistence inputs, lock, test):
1. Lead pool from the lead-L file; `vault_L = row_vault.for_lead(present_L)`.
2. `FitContext(L, FIT)` on them: the lagtrain bank at the lead's fit cut (`fit_bank`), c (`R23:lead=L`), R36
   tolerances, donor median. When the pinned arm is weighted (R29), the lead's GLS model
   `weight_model_for_cut(FitContext(L, FIT), FitContext(L, GUARD), ...)`.
3. H2: `FitContext(L, GUARD)`: the guard bank at the lead's guard cut; assert no guard row inside its label window.
4. Guard surface (2.4): `vault_L.decision_surface(..., lead-L fit cut)`; `ctx_guard.check_inner_score_rows(issue days)`;
   S1; a guard-surface row absent at L refuses (as ladder.py:44-45); `NeighbourPass` with ctx = `FitContext(L, GUARD)`
   (horizon = the lead's guard cut), the guard bank's store, the fallback median and Z from the guard-bank rows,
   c = the lead's fit-cut c (D63 a), at the pinned point (`LD.pin_of`), for the pinned arm and its link's trees-off;
   `LD.forecast_adoption` (D86). The guard rows are saved.
5. Persistence inputs (R31 events, D54 a), BEFORE the lead's lock, as the grid ladder (ladder.py:47-48):
   - persistence = `row_vault.last_label_before(package units, issue days, "persistence_lead_<L>")` for the test rows;
   - damped persistence (R31: "fitted on (visit, previous visit) pairs with the same season-key rule applied to each
     pair", APP_PLAN.md:271): per package unit, pairs (visit, previous visit of the same unit dated before the
     visit's issue day), both labels at or before the lead's fit cut; R2's event-month key. The U-2 / D88 rule is
     applied pair by pair: when the two visits share the event month, both leave their shared mean (at least
     `PHI_SHARED_MIN_LABELS` labels in it); otherwise each leaves itself out of its own mean
     (`PHI_SEPARATE_MIN_LABELS`) (the arithmetic of metrics.py:461-530). phi = through-origin slope, clipped to
     [0, 1], 0 when undefined. The baseline normal it needs (the kind has no normal, R15) is a baseline-only mean
     (O17). Built in pipeline/table_ladder.py (metrics.damped_persistence_phi takes one season-key flag for every pair
     and is grids only, metrics.py:472-474); `M.baseline_damped_persistence` (metrics.py:534-556) is reused.
   Both feed only their baseline columns.
6. `lock_lead_adoption(..., vault_L, folder)`. Its record prints `test_window_reads` (3.4), which now counts the
   persistence reads.
7. Test pass: test rows present at L (H4 for the rest); S1; `NeighbourPass` with ctx = `FitContext(L, FIT)` (horizon
   = the lead's fit cut); arms `LA.lead_arms(pinned, L, longest)` plus the identity trees-off (decline target);
   baselines predict_zero, donor_median, persistence, damped persistence; `assemble_rows`;
   `ladder/lead_<L>/test_preds.parquet`, `guard_preds.parquet`, `lead.json` (keys as ladder.py writes them).
8. The lead-0 contract (G-PLUMB "lead 0 = nowcast"): the lead path at L = 0 on `lead_0.parquet`: the pool equals the
   nowcast pool byte for byte; the donor rows equal the nowcast bank's inputs (so the bank is not refitted); c,
   tolerances, donor median and GLS model equal; every assembled column equals the nowcast's saved column.
9. The ladder table on the rows common to all leads (`M.common_rows`, keys unit + time), under the nowcast band.
   `TableLadder` may subclass `Ladder` (pipeline/ladder.py:407) and inherit `table()` and `run()` only if their
   bodies read nothing grid-specific; the builder checks each inherited line and copies otherwise.

### 3.10 Checkpoints (P1, S3), RAM waits (Q), records and fingerprints

- P1/S3: every bank (nowcast fit and inner, each lead's fit and guard) is checkpointed per group by the inherited
  `RunState.fit_bank` (passes.py:602-669), keyed with the table manifest (3.6). No census, no R30 blocks. Phase
  markers, the adoption lock and resume work as for grids (pipeline/run.py:1397-1432). The GLS models and the
  neighbour passes are recomputed on resume; their outputs are write-once and must equal (`_write_parquet_once`,
  passes.py:118-136).
- Q1: every in-run RAM or disk check uses `wait_for_room` (runs/room.py:135) or `_refuse_ram(..., wait=True)`. After
  the maximum wait it refuses, as today. There is no second, slower path.
- Records: run.json, run_record.json, manifest.json, manifest_adoption.json, derived.json, plan.json,
  plan_check.json, status.json, run.log, phases/*, adoption.json + lock, decision_checks.json, inner_preds.parquet,
  test_preds.parquet, pools_<pass>.parquet, gls_weight_model.json, tables.json, test_pass_router.json,
  score_by_group.csv, per_year.csv, per_stratum.csv, score_pooled.csv, per_group.csv, jackknife.csv, preclip.csv,
  guard_report.json, verdict.json, ladder/*, DONE.json. Same names and writers as grids where they exist.
- Fingerprint: `run_fingerprint(config)` (runs/fingerprint.py) over the table config of 3.6. Any engine edit moves
  `engine_code_sha256` (disclosed, U5).

### 3.11 The report

- `report/metrics.py` is unchanged. "No normal" scoring already exists: `normal` NaN everywhere gives anomaly R2
  NaN with n 0 (metrics.py:906-913); `baseline_donor_median` (:558-566), the neighbour hit tolerance (:665-686) and
  `REFERENCE_DONOR_ROW_MEDIAN` (:131).
- Saved keys: `unit` = row id, `time` = target day (so `(unit, time)` is unique and common rows match across leads).
- `treeroute_report/table.py`: works on neighbour runs (guess-normal and last-5 columns are absent, shown NaN,
  :247-251). One gated change: `_read_strata` (:214-245) accepts a string stratum whose verdict.json record has
  no edges (5.8).
- `treeroute_report/continuity_groups.yaml` needs the package's entry (report tooling, may name packages).

---

## 4. THE NEIGHBOUR INTERFACE (route/neighbour.py, new)

The approved stubs in route/kinds.py:1233-1258 stay as they are and keep raising (tests/test_route_kinds.py:305
pins them). This follows the region precedent: bodies in route/region.py, the kinds.py names unwired (kinds.py:
1195-1205). Wiring both kinds' names is one owner item (O19). route/neighbour.py defines the approved names with
the approved signatures, plus one keyword.

### 4.0 Reconciled choices (SPEC_NEIGHBOUR.md follows this text)

| Point | The one text |
|---|---|
| Pool horizon | the pass's own bank cut (R14), then U4's per-row `target day < issue day` |
| Map distance | the haversine central angle, the legacy formula without the Earth radius (coral_architecture.py:143-147); the approved text accepts great-circle distance (_proposed/route_kinds.py:399; loro_additions.py:672-673) |
| Z and context scalers | the pass's candidates (RouterRows after G1, fit/context.py:169-171). With the horizon at the pass's own cut they are the pass's bank DonorRows less G1 drops, which is also the approved proposal "donor rows at or before the cut" (_proposed/route_kinds.py:400). Decision surface: all candidates at the guard cut (N12) |
| Trees-off | `solve_point(Xc, y_link, Xt, 0, nctx, 0.0, a_ctx, n_unpenalised=1)` on [intercept, context]; with no context, the same call with nctx = 0 (the jittered pool mean) |
| Every tree dropped | that row's trees-off on its pool, counted as `n_rows_no_tree` (O8, one owner item) |
| Pool None | `link_forward(donor-row median)` for every arm and the trees-off (U3) |
| Weighted solvers | `n_unpenalised` on the unweighted AND weighted solvers (5.5) |
| GLS | built: the cut's model on test passes; per fold on the decision surface (R13, R25) |
| Verdict reference | the donor-row median (R34) |
| Checkpoints, memmap fallback | none inside a pass; a failed RAM wait refuses (Q1) |

### 4.1 `neighbour_pool_loro`

```python
def neighbour_pool_loro(row_unit, row_group, row_lat, row_lon, row_features, candidates, candidate_lat,
                        candidate_lon, candidate_features, candidate_group, blocks, *, row_issue_day)
    -> Tuple[Optional[np.ndarray], Tuple[str, ...]]
```
- Signature change: `row_issue_day` (keyword only, a day). Why: U4 filters the pool by each row's issue date and
  the approved signature carries no date (loro_additions.py:760-789).
- `row_unit`: the row's engine unit (its row id). `candidates`: a RouterRows, or the `ContextKeptRows` that G1
  leaves (same fields, stages.py:286-298), from the pass's own context (fit/context.py:168-182; `times` = target
  days, `row_positions` = tree-answer row ids). `candidate_features` / `row_features`: Z rows. `blocks`:
  OverlapBlocks.
- Eligible: `candidates.times < row_issue_day` and `candidates.unit_ids != row_unit`.
- Under `C11.neighbour_pool_min_rows` (12) eligible: return `(None, own block)`.
- Else: haversine central angle (4.0), stable argsort, the first `C11.neighbour_pool_distance` (150); then Euclidean
  distance in Z, stable argsort, the first `C11.neighbour_pool_feature` (50). Ties go to the earlier row position.
- Second value: the union of the row's own block and the block of every group in the pool, sorted (the default of
  SIGNATURES_LORO_ADDENDUM.md; APP_PLAN R14).
- Asserts (raise `RouteGuardError`): a pool row on or after the issue day, after the candidates' cut, or the row
  itself.
- Returns pool positions as `candidates.row_positions` values.

### 4.2 `trees_off_neighbour` (approved signature unchanged)

```python
def trees_off_neighbour(fit, fit_y_link, score, level) -> np.ndarray
```
- `fit`, `score`: DesignMatrix of [intercept, standardised context] (no tree block). `level`: the base point of
  R14 (level 1, ratio = context centre / trees centre) (O9).
- Solve (4.0): `route.solve.solve_point(..., ntree=0, nctx, 0.0, a_ctx, n_unpenalised=1)` with
  `a_ctx = C12.neighbour_trees_centre x level x ratio`, context trace-normalised, intercept unpenalised. Without
  context the same call with nctx = 0. Unweighted. Returns link space.

### 4.3 The private kernel (the route_neighbour_loro contract, run privately)

```python
@dataclass(frozen=True)
class NeighbourRows:
    cut: int; lead: int
    cand_keys: np.ndarray; cand_day: np.ndarray; cand_unit: np.ndarray; cand_group: np.ndarray
    cand_lat: np.ndarray; cand_lon: np.ndarray; cand_z: np.ndarray; cand_ctx: Optional[np.ndarray]
    cand_y_link: np.ndarray; cand_w: Optional[np.ndarray]   # GLS weights of the candidates, or None
    score_keys: np.ndarray; score_unit: np.ndarray; score_issue: np.ndarray; score_group: np.ndarray
    score_lat: np.ndarray; score_lon: np.ndarray; score_z: np.ndarray; score_ctx: Optional[np.ndarray]
    score_rows: np.ndarray            # the caller's positions -> RouteOutput.row_positions
    fallback_link: np.ndarray         # per score row: link(donor-row median in y)

def _route_neighbour_grid(rows, answers, tree_group, blocks, design, tol) -> Tuple[RouteOutput, dict]
def _route_neighbour_at(rows, answers, tree_group, blocks, design, point, tol) -> Tuple[RouteOutput, dict]
```
- `answers`: the dense answer matrix of one kind (3.8 step 7) with a row lookup.
- Per row: the pool (4.1); tree columns `RK.router_tree_columns(tree_group, drop_groups)` (kinds.py:719-749),
  cached per drop set; `RK.assert_no_own_group_column` on every fit (G-DISJOINT). A drop set that leaves no tree
  is not passed to `router_tree_columns` (it refuses an empty result): every tree arm of that row takes its
  trees-off (4.0, O8), counted as `n_rows_no_tree`.
- Design: `[1, context, trees]`; penalties `a_tree = C12.neighbour_trees_centre x level`,
  `a_ctx = a_tree x ratio` (the region of R14's grid: `derived["R14"].value.grid`).
- Grid: `route.solve.grid_dual(..., n_unpenalised=1)` for every point, with `solve_grid`'s reference check on the
  first `solve.NVERIFY` routed rows; one point: `solve_point(..., n_unpenalised=1)`. Weighted arms: the `_weighted`
  twins with `w = cand_w[pool]` and `n_unpenalised=1`.
- Pool None: every grid column and trees-off = `fallback_link` of the row (the y-unit donor-row median through the
  link, the same value for every arm, O7).
- Rows are routed in score order; the bytes do not depend on worker count (the same ROUTER_WORKERS discipline as
  kinds.py:39-45 when parallel).
- Returns `RouteOutput(row_positions=score_rows, predictions (rows, points), trees_off (rows,), grid,
  n_units_fitted=<rows with a pool>, n_units_fallback=0, n_rows_pool_fallback=<rows without>)` (route/kinds.py:
  171-182) and a record: pool sizes, groups per pool, drop-set sizes, rows with no tree column, the largest
  "pool day minus issue day", the c used.

### 4.4 What the pipeline passes (summary)

| Array | Source |
|---|---|
| candidate rows | the pass's own context: `ctx.router_rows(train row ids present at L)`, less G1 drops; days, row ids, context; labels from the vault |
| candidate lat, lon, group, package unit | `TableData` by row position |
| issue days of scored rows | the lead table's `key_issue` column (asserted = target - L) |
| Z | constants from the candidates; values from the lead's pool features |
| link(y) | `link_forward(y, link, c, ub)` with the pass's c (per fold on the decision surface) |
| tree answers | the pass's TreeAnswerStore, one kind at a time |
| fallback median | `M.baseline_donor_median(DonorRows)` of the pass's bank (decision surface: the fold's rows outside its block; lead guard: the guard bank's rows) |
| weights | `weights_for_rows` of the pass's GLS model (per fold on the decision surface); None for unweighted arms and every trees-off |

---

## 5. GRID SAFETY

Every grid smoke must stay byte-identical (U5; R1/S2 wording). Shared files touched, and why each change is a no-op:

| # | File | Change | Why grids do not move | Proof |
|---|---|---|---|---|
| 5.1 | package/schema.py | `DatasetFile.input` (default grid); `StorePaths.static` optional + validator; six new key roles | Every grid package validates to the same values; no grid column has a new role; the dataset model is never dumped into a record (only `name`/`version` are read, pipeline/record.py:126) | test: load every package in datasets/ before and after: same fingerprint, same model fields |
| 5.2 | package/load.py | cross-file check: table roles only with `input: table`, and required there | Fires only on the new roles or field | same test |
| 5.3 | pipeline/run.py:1476-1487 | guarded dispatch on `input` (3.1): any read error falls through | grid -> `Pipeline(...)` with the same arguments, after the same first refusal; reading dataset.yaml twice changes no byte | tripwire 5.10; a test with a malformed grid dataset.yaml: same refusal as LIVE |
| 5.4 | derive/router_rules.py:338-346 | test `kind == NEIGHBOUR` before the `is_events` raise | Grids pass `is_events=False`; the neighbour branch returns the same entry as today | derived.json of the tripwire runs identical |
| 5.5 | route/solve.py | keyword `n_unpenalised=UNPENALISED_COLUMNS` on `solve_local`, `solve_local_dual`, `grid_dual`, `reference_grid`, `solve_grid`, `solve_point`, `grid_dual_weighted`, `reference_grid_weighted`, `solve_grid_weighted`, `solve_point_weighted`; `o = n_unpenalised`; every internal call forwards it (solve.py:67-68, 172, 186-191, 202, 251-325); the module docstring's layout note (solve.py:16-19) says the unpenalised count is a parameter | Grid callers never pass it; `o` keeps the same int; no operation is reordered | tests (6.2): keyword omitted gives old bytes on random designs, weighted and not; `n_unpenalised=1` along the primal, the dual, `verify=True` and `solve_point`, weighted and not, equals a brute-force primal; tests/test_route_solve.py unchanged |
| 5.6 | check/quick.py:246, check/deep.py:1092 | first line dispatches a table package (guarded) | Grid packages take the old path | check reports of the grid packages identical (except times) |
| 5.7 | check/report.py:87-103 | table branch in `package_smoke_groups` | Grid branch unchanged | freeze verify on the grid locks: only the engine-hash drift |
| 5.8 | treeroute_report/table.py:214-245 | a recorded stratum with no edges (string stratum) is accepted | Grid verdict.json always carries edges | re-run `treeroute report` on the four headline folders: same bytes |
| 5.9 | (none else) | run.py LIMITS / DEPARTURES, passes.py, ladder.py, router.py, kinds.py, region.py, fit/* other than 5.11-5.12, labels/vault.py, layer/*, report/metrics.py, census, stream, data.py are NOT edited | | |
| 5.10 | (agent tripwire, Fix phase) | not a file change | | from LIVE and from the build copy, run the synthetic grid package of tests/test_pipeline.py and the four `*_draft` smokes (23-131 s each, SMOKES_REPORT.md:777-780), one at a time, run roots under D:\treeroute\coral_build\_tripwire; compare every output file byte for byte, leaving out only time, path and engine-hash fields; any other difference stops the build |
| 5.11 | fit/context.py | ADD `FitContext.donor_rows_outside(purpose, left_out_groups, fold) -> DonorRows`: the rows `donor_rows` would hand out, less every row of the listed groups, same order, issued and logged with the fold index (FitCtxLogRow already has `fold`) | Additive: no existing line changes; grids never call it | diff shows additions only; tripwire 5.10; test: the result equals `donor_rows` filtered by group |
| 5.12 | fit/weights.py | ADD `weight_models_for_folds(fit_ctx, guard_ctx, answers, tree_group, *, blocks, folds, matrix_dir, echo) -> Dict[str, WeightModel]`: the donor rows and the cross-region error target once (the body of `weight_model_for_cut`, unchanged arithmetic), then per fold g one `fit_weight_model` on `guard_ctx.donor_rows_outside(..., block of g, fold)` and its own floor and clip bounds; `WeightModel.fold` = the fold index (the field exists, weights.py:76-95) | Additive: `weight_model_for_cut` is not edited; grids never call the new entry | diff shows additions only; tripwire 5.10; test: with one fold that leaves out nothing, the model equals `weight_model_for_cut`'s bytes |

The engine code hash and the report-tooling hash change (fingerprint.py:138; freeze.py lock). `freeze verify`
on the grid locks reports that drift; the disclosure says why (as rulings R1 and P2 did).
Gate (owner command, about 1-2 hours; not run by an agent): the four grid smokes from LIVE and from the build copy,
compared file by file per the R1 wording (CORAL_ENGINE_PLAN.md section 3B). The agent tripwire 5.10 runs first.

---

## 6. TEST PLAN

Lean testing: relevant tests while building; the full suite (~45 min) once in the Fix phase.

### 6.1 The toy table package (tests/table_toy.py, a builder; not a test file)

`build_toy_table_package(root, variant="ok")` writes a complete package into a pytest tmp folder:
- 5 groups (`g_a` ... `g_e`), dates in 12 calendar years, irregular days from a fixed arithmetic rule (no RNG).
- About 60 rows per group; most package units have one visit; 10 units have 2-3 visits.
- (lat, lon) clustered per group, clusters apart, so the blocks are 5 single groups; variant `touching` puts two
  groups' sites together (one block of 2).
- 6 tree features (signal from fixed formulas; one column NaN on 10% of rows), 2 context columns (a seasonal one
  and one with NaN on 3 rows), one string stratum `source` with 3 values, target in [0, 100] with 40% zeros.
- `lead_0`, `lead_183`, `lead_365` files with `key_feature_end` = issue day minus 1; `lead_365` leaves out 5% of rows
  (some train, some test; no guard-surface row).
- Marks set from the derived window.
- Refusal variants, one per check: `bad_issue`, `feature_end_late`, `reserved_stratum_name`, `train_in_test`,
  `test_before_window`, `dup_row_id`, `dup_unit_date`, `unit_two_places`, `unit_two_groups`, `extra_column`,
  `missing_role`, `label_out_of_range`, `inf_feature`, `sentinel_feature`, `missing_lead_file`, `extra_lead_file`,
  `lead_row_not_in_nowcast`, `label_differs_across_leads`, `one_site_group`, `empty_group_at_cut`, `reach_on_target`,
  `grid_role_in_table`, `guard_row_absent_at_lead`.

### 6.2 Unit tests (tests/test_table_*.py and tests/test_neighbour_*.py)

| File | What it proves |
|---|---|
| test_table_schema.py | `input` default; table validator; new roles refused in grid packages; every datasets/ package loads identically (5.1, 5.2) |
| test_table_contract.py | the ok toy loads; each refusal variant refuses with its rule id; the 9 key columns never reach `apply_verdicts` |
| test_table_vault.py | RowLabelView: as-of in days, donor views, `decision_surface` (times must equal the row day), no read at a test-window cut, `open_test_labels` only after a lock, `asof_rows` refused, `for_lead` masks absent rows and sees the nowcast lock from disk, `last_label_before` serves only the same unit before the issue day, and `test_window_reads` counts its test-window reads |
| test_table_derive.py | expected entries on the toy: R1 irregular, R2 event month, R3/R5/R7, R10 = (183, 365), R11 day cuts, R12 neighbour, R13 5 folds, R14, R17 empty, R18 row lists with `bank_units_hash` / `scored_units_hash`, R19 per cut with `donor_row_key_hash`, R22 (identity, log_c, arcsine), R23 lead and fold entries, R30; the kind and empty-group refusals |
| test_neighbour_pool.py | strict pool: no pool row on or after the issue day, never after the pass's cut, never a test row, never the row itself; 150 then 50 against a brute-force reference (haversine); ties by row position; fallback under 12; drop set = own block plus pool blocks; a ContextKeptRows is accepted |
| test_neighbour_route.py | one-unpenalised solver against a brute-force primal, weighted and not; grid vs reference; trees-off vs the closed form (with and without context); G-DISJOINT assert fires on a planted own-block column; every-tree-dropped rows take the trees-off; fallback rows equal the donor median in y after the inverse link; same bytes with 1 and 8 workers |
| test_solve_unpenalised.py | 5.5: keyword omitted gives old bytes (all ten solvers); `n_unpenalised=1` through the primal, the dual, `solve_grid(verify=True)`, `solve_point` and the weighted twins equals a brute-force primal; `n_unpenalised=2` equals no keyword |
| test_fold_gls.py | 5.11-5.12: `donor_rows_outside` equals the filtered `donor_rows`; a fold that leaves out nothing reproduces `weight_model_for_cut` bytes; each fold's forest saw no row of its block |
| test_table_branch.py | run_pipeline / plan_pipeline / check build the right class for a grid and a table package; a malformed grid dataset.yaml gives LIVE's refusal; plan() and run() on the toy reach `_open` and write plan.json with TABLE_LIMITS and the U2 list; no grid step helper (`_build_tables`, `_pass_tables`, `ST.unit_positions`) is reachable in table mode |
| test_table_persistence.py | persistence and damped persistence on the toy: pairs by package unit, the per-pair season-key rule, phi from train labels only, reads counted before the lock |
| test_route_kinds.py, test_derive_loro_rules.py | unchanged stubs still raise; R17 neighbour with events returns the empty spec |
| test_nonames.py | covers the new modules automatically (they live under treeroute/); add a scan of treeroute_report/*.py (if today's files already fail, report it and scan only the table additions) |

### 6.3 End to end (tests/test_table_pipeline.py, a few minutes)

- `smoke` on the toy: the run folder holds every file of 3.10; adoption.json and its lock are older than
  `test_labels_opened_lead_0.json`; `check_scored_units` passes; `test_preds.parquet` rows = test rows less S1;
  ladder leads 183 and 365 with `issue_missing_rows.parquet` at 365; the lead-0 contract passes; verdict.json names
  `donor_row_median` as the reference; ladder.json exists; `treeroute report` builds the smoke-watermarked table.
- Pool audit: re-read the lead files on their own; for every row of every `pools_<pass>.parquet`, each pool row is
  train-marked, its target day is at or before the pass's bank cut, and before the scored row's `key_issue` from the
  file.
- Resume: stop after the decision phase (a planted stop), run again: every output equals an uninterrupted run.
- Leak probe: overwrite every test label in the toy with the legal maximum, run the whole smoke again. Byte-identical:
  derived.json, every `pools_<pass>.parquet`, the `neighbour` records, inner_preds.parquet, adoption.json, every
  guard_preds.parquet, and every prediction column (arms, trees-off, placebos, donor median, predict-zero) of
  test_preds.parquet and of ladder/lead_*/test_preds.parquet. Left out: the label column and the persistence and
  damped persistence columns (they may read earlier test labels under D54 a).

---

## 7. OWNER ITEMS (no signed rule; the default chosen)

Items O6, O11, O12 and O23 left this list: signed rules cover them (REVIEW LOG). O3 is now signed R14 and stays only
to name the U4-alone alternative.

| # | Behaviour | Default (built) | Alternative |
|---|---|---|---|
| O1 | Test window vs the package's marks | derived (R3 events, R5); marks must match exactly, else refused | take the window from the marks; or CORAL_ENGINE_PLAN Q6 a |
| O2 | R1 on tables | not run; irregular by declaration (U1) | run R1 and refuse a table whose dates look like a grid |
| O3 | Pool horizon (signed R14) | the pass's own bank cut, then U4's `< issue day` per row | literal U4 alone: lead 0's cut, so earlier inner-score rows and rows after the lead's cut may enter |
| O4 | "Dated strictly before the issue date" | target day < issue day, the target date being the label's last content day | a separate label-window column |
| O5 | Feature-space step | Euclidean on 0-filled tree features, unweighted; constants on the pass's candidates (= bank DonorRows less G1, the approved proposal); sd + 1e-9; haversine angle (approved); stable sorts, ties to the earlier row position | legacy: all training rows for the constants, donor-median fill, unstable sort |
| O7 | Fallback under 12 rows | y-unit donor-row median of the pass's bank DonorRows (decision surface: outside the fold's block; lead guard: the guard bank), every arm and trees-off | the legacy training mean of link(y) |
| O8 | A row whose drop set removes every tree | that row's trees-off on its pool (the limit of the ridge as the tree penalty grows), counted as `n_rows_no_tree` | donor-row median; refuse the run (router_tree_columns' contract) |
| O9 | Trees-off penalty point | always the R14 base point (C12 context centre) | the adopted point |
| O10 | G-PLUMB pair 1 for the neighbour kind (no normal) | trees-off vs an independent closed-form solve of the same ridge, with a `neighbour` note | skip the pair (needs a check_plumbing change) |
| O13 | A group with 0 rows at any bank cut | refused at plan (R19's rule applied to all six cuts) | CORAL_ENGINE_PLAN Q18 a: no trees at that cut, still lends pool rows |
| O14 | A one-site group | refused (derive_overlap_blocks, split.py:731-735) | Q8 a: use the median nearest-site spacing of all units |
| O15 | Rows absent from a lead file | test rows: H4; guard rows: refused (grid reading); other rows: out of that lead's banks, c, tolerances, GLS rows and pools, counted (departure `table_absent_rows`) | grid behaviour for bank rows: kept with 0-filled features |
| O16 | R12 gives per-unit or region on a table | refused | build table versions of those kinds |
| O17 | Damped persistence's normal on a no-normal kind | a baseline-only mean of the package unit's labels at or before the lead's fit cut per event month, then the unit's all-season mean, then the donor-row mean (R15's fallback chain, used for this baseline only) | damped persistence on the donor-row median as the normal |
| O18 | String report strata | scored per value; numeric strata keep the quartile rule | numeric only (string strata refused) |
| O19 | Signatures and kernel | `neighbour_pool_loro(..., *, row_issue_day)`; solve.py `n_unpenalised`; `FitContext.donor_rows_outside`; `weight_models_for_folds`; private neighbour kernel; kinds.py names unwired (as region) | alias the approved names to route/region.py and route/neighbour.py; build `for_fold` instead of the two fold entries |
| O20 | Table batching | off; one kind's answer matrix in RAM per pass, after a RAM wait | per-group batching as grids |
| O21 | G-FACTS in the table deep check | pass when the target's facts are signed; feature timing recorded as vouched (U2) | flag until each feature row is signed |
| O22 | Smoke pick | 40 package units per group by stride, all their rows | 40 rows per group |
| O24 | Repeated (unit, target date) | refused; the package merges them (Q7 is a package choice) | allow and key by row id only |
| O25 | Labels outside the legal range | refused at load | clip |
| O26 | Accepting TABLE_DEPARTURES | not-headline reasons until accepted | accept at the coral freeze, as S21 |
| O27 | The event cut day at L >= 1 (2.2) | signed R11 as built: cut = first test day minus L; labels dated on the cut enter the banks, c, tolerances and median; disclosed | cut = first test day minus L minus 1 in `event_fit_cut_day` and `event_guard_cut_day` (events only, grid-safe) |

---

## 8. Build order (after this spec is approved)

1. schema + load + package/table.py + labels/rows.py, with their tests.
2. derive/table.py and the router_rules reorder, with tests.
3. route/neighbour.py and the solve.py keyword (unweighted and weighted), with tests.
4. fit/context.py `donor_rows_outside` and fit/weights.py `weight_models_for_folds`, with test_fold_gls.py.
5. table_run.py, table_passes.py, table_router.py, table_ladder.py; the toy end to end, the pool audit, the leak probe.
6. check/table.py, the check and freeze-group branches, the report-table branch.
7. Fix phase: the agent tripwire (5.10); the full suite once; the no-op proof command for the owner (section 5).

New files (all under treeroute/, none names a problem): package/table.py, labels/rows.py, derive/table.py,
route/neighbour.py, pipeline/table_run.py, pipeline/table_passes.py, pipeline/table_router.py,
pipeline/table_ladder.py, check/table.py. No new engine constant is needed (C11, C12, C13, S5, C15 are reused).

### 8.1 Size and time on coral (estimates; the tiny smoke replaces them with measured numbers)

- 83 groups x 100 trees = 8,300 trees. Answer matrix per kind: 13,650 rows x 8,300 x 4 B = about 453 MB.
- Banks: 6 cuts x 83 groups x 100 trees on groups of 1 to about 800 rows: minutes per cut (to measure).
- GLS: two donor-row passes at lead 0 (about 9,300 guard-cut rows x 8,300 trees) plus 1 cut forest and 83 fold forests
  (120 trees, depth 8, on about 9k rows each): roughly 10-20 minutes. Lead GLS only if the pin is weighted (R29).
- Neighbour passes: decision surface 2,046 rows x 35 points x (2 tools x 2 weightings x up to 3 links) plus trees-off;
  test passes one point. Roughly 10-30 minutes with 8 workers.
- Peak RAM: about 1.5-2.5 GB (one answer matrix, one bank, the GLS donor matrix), under the 15.8 GB machine.
- Tiny smoke (4 groups, 897 rows): a few minutes, run by an agent. Full coral run: likely 1-3 hours, so an owner
  command (over the 30-minute agent limit).

---

## REVIEW LOG (2026-10-19)

GS = grid-safety review, LK = leakage review, FS = feasibility review. "Fixed" names the section changed.

| Issue | Outcome | Where / reason |
|---|---|---|
| GS1 verdict reference | fixed | ATTENTION; 3.7 `report` uses `REFERENCE_DONOR_ROW_MEDIAN` with `base__donor_median` (the prefix is `base__`, metrics.py:152, not `baseline__`); O23 deleted |
| GS2 lead pool horizon | fixed | 0, 2.4, 3.8, 3.9, 4.0: horizon = the pass's own bank cut (R14); the logs now stamp the pass's lead; O3 keeps the U4-alone alternative |
| GS3 GLS for the neighbour kind | fixed (option b, built) | 3.2, 3.6, 3.7, 4.3, 4.4, 5.5, 5.11, 5.12; O11 deleted |
| GS4 six contradictions with SPEC_NEIGHBOUR | fixed | 4.0 is the one text: haversine; scalers on own-cut candidates; trees-off by `solve_point` in both; O8 = N6 one item (default trees-off); keyword on weighted solvers; GLS built |
| GS5 `_plan_document` writes grid LIMITS | fixed | 3.6 overrides `_plan_document`; `_open` passes TABLE_LIMITS and TABLE_DEPARTURES |
| GS6 inherited fields not produced | fixed | 3.5 `R18:units` inputs, `R19` hashes; 3.6 `_load` (`feature_lineage`, `listed_in_reports`, `frozen`); 6.2 test_table_branch reaches `_open` |
| GS7 G1 on candidates | fixed | 3.8 step 1 uses the G1 tools; 4.1 accepts ContextKeptRows; O6 deleted |
| GS8 per-fold c is signed | fixed | 3.5 `R23:fold=<g>` cites R13; 3.7 checks fold c against its plan entry; O12 deleted |
| GS9 VaultRows mixes steps and days | fixed | 3.6 `_vault`, `_build_tables` / `_pass_tables` raise; 6.2 test |
| GS10 absent rows default | fixed | guard rows absent now refuse (grid reading); bank rows: departure `table_absent_rows` with its reason (3.6, 3.7, O15). The reviewer's reason "coral would refuse at 365" is not used: coral's absent rows are 1994 train rows, not guard rows |
| GS11 damped persistence and U-2 | fixed | 3.9 step 5 builds it with the per-pair season-key rule; O17 now covers only its baseline normal |
| GS12 reserved key names | fixed | 2.1 T-NAMES |
| GS13 key roles vs KEY_ROLES copies | fixed | 1.3 TABLE_KEY_ROLES, keys removed before `apply_verdicts`; 3.3 |
| GS14 `n_unpenalised` forwarding | fixed | 5.5 and 6.2 test_solve_unpenalised |
| GS15 false G-PLUMB / beside labels | fixed | 3.8 step 10 note; 3.7 `identity_trees_off_mae` |
| GS16 memmap fallback, checkpoints | fixed | 3.8 last line; 3.10 Q1 line; SPEC_NEIGHBOUR 7 |
| GS17 persistence reads uncounted | fixed | 3.4: method `last_label_before`, `test_window_reads` overridden in RowLabelView only |
| GS18 `streamed` gate flag | fixed | 3.6 first paragraph |
| GS19 dispatch changes first refusal | fixed | 3.1 guarded dispatch; 5.3 test |
| GS20 R12 signature | fixed | 3.5 R12 row |
| LK1 lead horizon and scalers | fixed | same as GS2; 2.3 adds the per-pass constant assert |
| LK2 feature dates not checked | fixed | 1.3 `key_feature_end`; 1.7 item 6; 2.1 T-FEATEND; max per lead in plan.json |
| LK3 no probe of the test pass | fixed | 6.3 leak probe covers derived.json, pools, records and every test prediction column at every lead |
| LK4 persistence label path | fixed in part | counted (3.4) and asserted; the read stays BEFORE the lock, as signed D54 a ("served before the pass's adoption lock") and the grid ladder (ladder.py:47-48, 1066-1068) do. The lock moved from step 4 to step 6 so the text no longer contradicts itself. "Read after the lock" is rejected: it departs from D54 a and leaves the reads out of the lock record |
| LK5 guard-surface fallback donor rows | fixed | 3.8 step 5, 3.9 step 4, 4.4: guard-bank DonorRows; per-pass assert |
| LK6 one-day-late event cuts | fixed (listed) | 2.2 note and O27 (signed R11; default keep and disclose) |
| LK7-LK9, LK11, LK12 | see SPEC_CORAL_TABLES.md REVIEW LOG | package side |
| LK10 legacy harness labels | fixed | SPEC_NEIGHBOUR 8 |
| FS1 GLS left out | fixed | same as GS3 |
| FS2 fold context missing | fixed | 5.11, 5.12 (additive fold entries; `for_fold` stays unbuilt, O19 alternative) |
| FS3 three spec disagreements | fixed | 4.0 |
| FS4 damped persistence | fixed | same as GS11 |
| FS5 no feature-date declaration | fixed | same as LK2; a per-row column was chosen over a per-column fact because the engine can check it row by row |
| FS6 tests cannot catch a mis-wired pool | fixed | 3.8 steps 2 and 9; 6.3 pool audit and leak probe |
| FS7 no agent grid tripwire | fixed | 5.10; 8 step 7 |
| FS8 key roles vs role lists | fixed | same as GS13 |
| FS9 O3 and O12 signed | fixed | O12 deleted; O3 marked signed R14 |
| FS10 scored rows replace R18(2) | fixed | 3.5 `R18:units` cites U1; TABLE_LIMITS; coral disclosure in SPEC_CORAL_TABLES |
| FS11 "available" vs content date | fixed | 1.7 item 1 is a content date |
| FS12 sizes and wall time | fixed | 8.1; SPEC_NEIGHBOUR 7 |
| FS13 checkpoints / memmap | fixed | same as GS16 |
| FS14 float32 in the harness | fixed | SPEC_NEIGHBOUR 8 |
| FS15 protected store root | fixed | 1.2; SPEC_CORAL_TABLES 4.1 publishes a separate copy |
| FS16 bank checkpoint key | fixed | 3.6 `census_step.key` = table manifest hash, read by the inherited `fit_bank` (passes.py:623-625) |
| FS17 dispatch order | fixed | same as GS19 |
| FS18 U6 order | see SPEC_CORAL_TABLES.md REVIEW LOG | package side |

Counts for this file: 44 issues logged (GS1-GS20, LK1-LK6, LK10, FS1-FS17); 43 fixed in full, 1 fixed in part (LK4:
its "read after the lock" wording is rejected), 0 rejected outright. FS9's N5 part is logged in SPEC_NEIGHBOUR.md.
Package-side items (LK7-LK9, LK11, LK12, FS18) are counted in SPEC_CORAL_TABLES.md.

Totals over the three reviews (50 issues): 47 fixed in full; 3 fixed in part, each with one rejected part (LK4 "after
the lock", LK9 date-precision stratum, FS9 N5 kept as an owner item); 0 rejected outright. No BLOCKER remains for the
engine build. One gate remains for the coral run, not the build: P1 (test window, a departure from R3) must be signed
before any full coral smoke or run (SPEC_CORAL_TABLES.md).
