# SPEC_RIVALS: the export, the harness and the tests of the lean common-rival board

Written 2026-10-20 (design); built since; updated 2026-10-21 for ruling AA (section 7).
Sources: RIVALS_PLAN_COMMON.md (the plan), OWNER_RULINGS_2026-10-06.md section Y (Y1-Y4, :136-145), the LIVE engine
(engine_code_sha256 930d961c, comment-stripped hash 85c64b55). Engine paths below are relative to
`C:\Users\<user>\Desktop\data set for reserch paper\engine\`. Run folders are `D:/treeroute/runs/<pkg>/headline/<run>`.

## 0. Short version and the must-reads

- One export script reads a finished run and its package, calls the engine's own builders (read-only), and writes
  per lead the same rows and columns our model used. It refuses on any identity or parity mismatch.
- One harness tunes each rival on the inner window, locks the picks (hashed), refits per lead, runs our safety
  net on the rival, and scores with the engine's own metric functions.
- Test labels are never in an export file. They are read from the run's `test_preds.parquet` only after the lock.
- Code lives in `D:/treeroute/rivals_build/rivals/`. It names no problem (plug and predict).

**ATTENTION A1 - engine hash.** The grid runs were made under older engines: pm25 under 7b508557 (file sha;
stripped 6d19c3e2), ndvi/fire/defo under 65a177bc (stripped 13838e41). LIVE is 930d961c (stripped 85c64b55)
(freeze locks `D:/treeroute/registry/freeze/FREEZE_*.lock.json`, key `engine`). A plain "engine hash must equal"
check refuses all four grids (24 to 38 engine modules differ). This spec accepts LIVE only through a recorded
chain of no-op proofs from the run's engine to LIVE (section 2.2 check I4), plus full data parity. The hops
65a177bc -> dd7c0984 -> 930d961c are recorded (`D:/treeroute/coral_build/noop/noop_summary.txt`,
`D:/treeroute/coral_build_v6b/noop/noop_summary.txt`: 0 must-match files differ on all four smokes). The pm25 hops
7b508557 -> 1f257395 -> 7a0341ef -> 65a177bc must be found in `D:/treeroute/install_20261015/`,
`D:/treeroute/s_20261016/` (and the ruling-S3/T install records). If one hop has no proof file, the pm25 export
refuses. Owner confirms this reading before the first grid export.

**ATTENTION A2 - the safety net's fallback.** Plan rule 12 says the test fallback is `arm__<link>_trees_off_unweighted`.
The engine's decline target is the IDENTITY trees-off (the plain normal) at every lead (pipeline/ladder.py:1036,
layer/decide.py:452), and the donor-row median for the neighbour kind (ruling V1, pipeline/table_passes.py:357-360).
This spec follows the engine: comparator = the rival's own-link trees-off (N2, layer/decide.py:290-299);
fallback = the run's decline target. Owner confirms.

**ATTENTION A3 - c on inner and guard rows.** Plan rule 5 says "c follows the same rule" (guard-cut c). The engine
uses the lead's FIT-cut c on its decision and guard surfaces (ruling D63 a; pipeline/ladder.py:132-138;
layer/links.py:145-205 refuses guard-cut donor rows for c). This spec gives rivals the same c our model used
(derived.json `R23:lead=L`). Normals and the history block DO follow the guard cut, as in the engine.

**Ruling AA (owner, 2026-10-21, options A, B, C and D chosen; built 2026-10-21, see section 7).**
- AA1: there is no phase 2. The donor-only 10-fold board (Q1 b, Q17, Q18; ruling D's default named both boards) is
  DROPPED; the one board is the global board of this spec. Nothing in the code built a phase-2 board, so AA1 changes
  no code; it is a disclosed departure from ruling D's default.
- AA2: LightGBM and LightGBM-Tweedie tuning trials stop early on the inner window (3.4a, 3.5).
- AA3: 63 histogram bins in tuning; every final fit uses 255 bins at the picked round count. **WITHDRAWN by AC1**
  (below).
- AA4: the lean export takes two engine guard steps from the run's record (2.10); the byte parity checks decide.

**Ruling AC (owner, 2026-10-21, all accepted and the out-of-core random forest kept; built 2026-10-21, see section 7b).**
- AC1 (replaces AA3): LightGBM and LightGBM-Tweedie tune AND refit at the default 255 bins (3.4a, 3.7). The 63-bin
  tuning path is removed (old code in `_moved/20261021_preAC_code`).
- AC2 (amends Y2/Z3 b and AA2): the extension to 1600 rounds applies only to a trial that ran to the 800 cap without
  a patience stop; a trial stopped by patience is never extended (3.5).
- AC3: the out-of-core Random Forest (Z2) stays as built. AC4: rebuild, tests, coral dry pass, new hash in the draft.

**Readings for the owner (R-items, section 6):** R-Y2 (what "that model alone is extended" means), R-C6 (how
hgb_l1 is switched on without a problem name), R-TW (the N2 comparator of the Tweedie rival), R-CN (coral's
offset is one donor-row median per cut, not per fold).

---

## 1. The shared contract (`rivals/layout.py`, fixed here; both builders code to it)

### 1.1 Roots (paths only; one YAML file `D:/treeroute/rivals_build/rivals.yaml`, every path absolute)

| key | production value | build and test value |
|---|---|---|
| engine_root | `C:/Users/<user>/Desktop/data set for reserch paper/engine` | same (read-only) |
| machine_file | engine `config/machine.yaml` (run_root, temp_dir D:/treeroute/tmp, registry_dir) | a test machine under `D:/treeroute/rivals_build/_machine/` (temp_dir and run_root under rivals_build; registry_dir = `D:/treeroute/registry`, read-only) |
| export_root | `D:/treeroute/rival_export` | `D:/treeroute/rivals_build/_export` |
| export_ckpt_root | `D:/treeroute/rival_export/_engine_run_root` (the export's own engine run_root: census and R30 checkpoints) | `D:/treeroute/rivals_build/_export/_engine_run_root` |
| out_root | `D:/treeroute/rivals` | `D:/treeroute/rivals_build/_out` |
| moved_root | `<root>/_moved` | `D:/treeroute/rivals_build/_moved` |

Every write path is checked with the engine's `runs.registry.Registry(registry_dir).assert_writable(path)`
(runs/registry.py:195) before the first byte. Nothing is ever deleted: a replaced or partial file is moved under
`moved_root/<utc stamp>/`.

### 1.2 Export folder of one run and lead

`<export_root>/<package>/<run_name>/lead_<L>/` with:

| file | rows | columns |
|---|---|---|
| `train/<group>.parquet` | every non-test row any fit or inner/guard score uses at this lead (section 2.4) | keys, role flags, `y`, `nfit__<link>`, `x__<tree col>`, `c__<context col>` |
| `guardside/<group>.parquet` | the subset of train rows flagged `r_tune`, `r_inner` (lead 0) or `r_guardfit`, `r_guard` (lead >= 1), same order as in `train/` | keys, `h__<history col>` (history block at the guard cut), `ngd__<link>` (guard-cut normal) |
| `test/<group>.parquet` | the run's scored test rows of this lead | keys, `nfit__<link>`, `x__...`, `c__...`. **No `y` column.** |
| `units.parquet` | every bank unit | `unit`, `group`, `is_scored`, `seen_during_design` (group in split.yaml list), each report stratum column |
| `_progress/<part>/<group>.json` | one per finished group file | `{file, sha256, rows, export_key}` |
| `export_manifest.json` | written LAST, after every parity check passed | section 2.7 |

- Keys: `unit` (str), `group` (str), `time` (int64: the LABEL step, or the target day for a table), `issue`
  (int64 = time - L), `lead` (int64).
- Role flags (bool, train files only): `r_refit`, `r_tune`, `r_inner`, `r_guardfit`, `r_guard`.
- `x__*` are the tree columns in `manifest.json["feature_list"]` order (kept tree features, then the R17 history
  columns: the FIT-cut history block of this lead). `c__*` are plan.json `context` in order. Values are float32,
  RAW (NaN kept; no 0-fill). `y`, `nfit__*`, `ngd__*` are float64.
- `<link>` is the R22 link value (`identity`, `log_c`, `arcsine`); `nfit__<link>` and `ngd__<link>` are the normal
  IN LINK SPACE.
- Atomic write: write `<name>.tmp_<pid>` with `open(..., "xb")`, flush, fsync, `os.replace`; then the progress json.

### 1.3 Harness output folder

`<out_root>/<package>/<run_name>/` with `board.json` (section 3.1), `trials/<learner>/<trial_id>/`,
`trials.csv`, `picks.json`, `picks.json.lock.json`, `lead_<L>/` (fits, preds, guard), `test_labels_opened_rivals_lead_<L>.json`,
`scores/`, `board_lead_<L>.csv`, `board.md`, `rivals.log`, `status.json`, `materialized/` (memmaps; section 3.10).

---

## 2. THE EXPORT (`rivals/export.py`)

### 2.1 Command

```
py -3.9 -m rivals.cli export --run <run folder> [--package <package folder>] --lead <L|all> [--roles <list>] [--config <rivals.yaml>] --resume [--p15] [--full-engine-checks]
```

- `--full-engine-checks` (AA4): run every engine guard step again instead of the lean export (2.10). The default is
  the lean export. The exported files are the same bytes either way.

- `--package` default: the last argv item of `manifest.json["argv"]` resolved under engine_root (e.g. `datasets/fire`).
- `--lead all` exports every lead in one process (one derive). NDVI is exported with `--lead 0`, then `--lead 6`,
  then `--lead 12`, each after the previous lead's fits and scores are done (plan Q13 a).
- `--roles` (default all) limits what is written; the coral dry pass uses `--roles tune,inner` (no test file).
- The first statement of `export` is `treeroute.launch.pin_threads()` (launch.py:162): the export runs under the
  engine's own thread pins, as the run did (manifest `launch.env_pins`). The shell must be clean (the launcher
  refuses foreign OMP_*/MKL_* variables, launch.py:1-21).
- Engine import: `sys.path.insert(0, engine_root)`; no engine file is ever opened for writing.

### 2.2 Identity checks (before any work; each failure is a loud refusal naming the check)

| id | check | source |
|---|---|---|
| I1 | the run folder holds `DONE.json`, `manifest.json`, `derived.json`, `plan.json`, `fitctx_log.parquet`, `inner_preds.parquet`, `test_preds.parquet`, and each lead's `ladder/lead_<L>/{test_preds,guard_preds}.parquet` | run folder |
| I2 | the package loads and `package.fingerprint == manifest["package_fingerprint"]` | package/load.py |
| I3 | LIVE `library_versions()` == `manifest["versions"]` and `platform.python_version()` == `manifest["python"]` | runs/fingerprint.py:114-124 (checked 2026-10-20: equal for pm25, fire, coral) |
| I4 | engine: LIVE `engine_code_hashes()` == `manifest["engine_modules"]`, OR a chain of no-op proof hops from the run's engine to LIVE exists in `D:/treeroute/rivals_build/engine_lineage.json` (A1). The run's file-sha is found by matching `manifest["engine_code_hash"]` to a freeze lock's `engine.engine_code_hash_comment_stripped`; each hop names its proof file, the proof file's sha256, and the line `MUST-MATCH FILES THAT DIFFER OR ARE MISSING (0)` for this package. The lineage file is written by builder A from those records and printed for the owner; it is data, never edited by hand | registry freeze locks; noop summaries |
| I5 | after the engine's own derive (2.3 step 2): the export rebuilds the run config exactly as the engine does (grid: pipeline/run.py:1124-1133; table: pipeline/table_run.py:309-317) and checks it KEY BY KEY against `manifest["config"]` (package, derived_sha256, data manifest, target/static/driver file sha by size and mtime, constants hash, feature_list, context_list, groups, trees_per_group, strata, draft) | |
| I6 | `sha256(dumps_canonical({"config": rebuilt config, "engine_code": manifest["engine_modules"], "versions": manifest["versions"], "python": manifest["python"]}))` == `manifest["fingerprint"]` (the run_fingerprint formula, runs/fingerprint.py:127-135; verified on pm25, fire, coral). This proves the input manifest and derived document are the run's | |
| I7 | the derived document derived now equals the run's `derived.json` as JSON (the engine's own resume check, pipeline/run.py:1163-1172) | |
| I8 | free disk on the export drive >= one lead's export (2.8 table) + 3 GiB; the engine's own temp-disk and RAM checks run inside its builders (pipeline/run.py:672-726, 494-512) | |
| I9 | heavy-job lock: taken by the engine's own `Pipeline._lock()` (pipeline/run.py:271-298, `HeavyJobLock` in the machine temp_dir, runs/preflight.py:168-218); refuses when another job holds it | |

### 2.3 Engine calls, grid packages (per-unit and region kinds)

The export drives the engine's `Pipeline` (pipeline/run.py:233) with `run_root = export_ckpt_root` and the run's
kind (`manifest["config"]["kind"]`: headline or smoke), WITHOUT `_open` (it writes into a run folder,
pipeline/run.py:1113-1203) and without any fit, bank, store, router or label opening.

1. `pipe._lock(); pipe._load(); pipe._groups(); pipe._preflight_target(); pipe._read()` (run.py:1369-1373).
   The census checkpoints go under `export_ckpt_root` (run.py:796-801). They are KEPT after the export so the
   next lead's export of the same package resumes the census and R30 (owner moves them aside after the package's
   last lead).
2. `pipe._derive()`; checks I5-I7; then `pipe._release_census()` (run.py:968-985).
3. Host fields the passes read: `pipe.folder = <lead dir>/_engine_folder` (empty, ours; the vault reads lock
   records from it and finds none), `pipe.fingerprint = manifest["fingerprint"]`, `pipe.status =
   runs.status.StatusWriter(pipe.folder, fingerprint)`, `pipe.derived_sha` from step 2. Then `pipe._temp()`
   (run.py:1331-1343: the engine's temp folder and its disk pre-flight).
4. `state = passes.RunState(pipe)` used as a context manager (passes.py:189-226, it releases every pool).

**Lead 0** (`state.build_pool(need_inner=True)`, passes.py:371-434): the nowcast pool (kept tree features +
FIT-cut history block + context) and `pool_inner_history` (the history block at the guard cut).
- `ctx_fit = state.ctx_fit` (lead 0, FIT). `inner_features = state.inner_features` (passes.HistoryOverride).
  `ctx_inner = FitContext(derived, split_sets, vg.grid, labels, inner_features, lists, 0, CutKind.GUARD)`
  (as passes.py:586-587).
- refit rows: `ctx_fit.donor_rows_lazy("rival_refit")` (fit/context.py:597-602): keys, `y`, grid rows.
- tune rows: `ctx_inner.donor_rows_lazy("rival_tune")`.
- inner rows: the decision surface, selected exactly as passes.py:735-755: `labels.validity(guard_cut+1, fit_cut)`,
  scored units, valid, own window ended by the fit cut's last day, then owner ruling S1 through
  `state.leave_out_score_context("decision surface", ctx_inner, 0, keys, units, steps, save=False)`
  (passes.py:264-328; `save=False` writes nothing), then `labels.decision_surface(units, steps, fit_cut)`
  (labels/vault.py:547-612) for `y`.
- test rows: `stages.unit_positions(vg, scored_units, vg.test_first, None)` then S1 with `save=False`
  (passes.py:898-908 without the label read).

**Lead L >= 1** (as pipeline/ladder.py:618-754, features only, no bank):
- `pool_L = open_pool(temp_dir, "pool_lead_L", rows, tree_cols, ctx_cols)` (fit/pool.py:231);
  `ctx_fit_L = FitContext(..., pool_L, lists, L, CutKind.FIT)`; history block `hist` from
  `stages.history_inputs(ctx_fit_L, ...)` + `io.apply.history_block(..., L, ...)` (ladder.py:471-481);
  `absent = state.fill_pool_by_group(pool_L, hist, L, move=io.apply.features_at_issue_step)` (passes.py:436-509).
- `ctx_guard_hist = ctx_fit_L.for_lead(L, GUARD)`; guard history block at the lead's guard cut into
  `pool_guard_history_lead_L`; `guard_features = HistoryOverride(pool_L, that pool)`;
  `ctx_guard_L = FitContext(..., guard_features, lists, L, CutKind.GUARD)` (ladder.py:719-736).
- refit rows: `ctx_fit_L.donor_rows_lazy("rival_refit")`. guard-fit rows: `ctx_guard_L.donor_rows_lazy("rival_guardfit")`.
- guard rows: selected exactly as ladder.py:769-798 (score steps nowcast guard_cut+1 .. lead fit cut; scored, valid,
  window ended; `check_inner_score_rows`; a guard row whose issue row is absent REFUSES, as the engine does;
  S1 `save=False`; `labels.decision_surface(..., purpose="rival_lead_L_guard")` for `y`).
- test rows: as ladder.py:987-1006 without the label read: H4 drops rows with `absent[t_keys]`, then S1 `save=False`.

**Feature values.** Every `x__`/`c__` value is read RAW from the pool the engine's own object read:
refit and test rows from `pool` / `pool_L` (`tree_features(rows)`, `context(rows)`, fit/pool.py:206-212);
tune, inner, guard-fit and guard rows' history columns from the guard history pool (written to `guardside/`).
The export asserts, group by group, that the 0-filled export of a fit set equals `donor.X[group rows]` of the
engine's lazy hand-out byte for byte (fit/context.py:544-551, R30 0-fill), and that no value is infinite.

### 2.4 The normals (link space; one per link per cut)

- c: `layer.links.c_for_cut_against_plan(refit_donor_rows, derived)` (layer/links.py:172) at each lead when
  `log_c` is a link; asserted equal to `derived["R23:lead=L"]`. The same c serves fit, inner and guard rows (A3).
  ub = legal max when finite (passes.py:388-389).
- Fallback mean per cut: `stages.donor_link_means(donor_rows, links, c, ub)` (stages.py:201-205) of that cut's
  donor rows (refit rows for FIT, tune / guard-fit rows for GUARD).
- Per-unit and region kinds: `stages.unit_normals(ctx, bank_units, link, c, ub, donor_mean[link], season)`
  (stages.py:208-220) at the cut's context (FIT: `ctx_fit` / `ctx_fit_L`; GUARD: `ctx_inner` / `ctx_guard_L`).
  For the per-unit kind with context columns, the SCORED units' normals are rebuilt as the router builds them:
  `stages.pass_rows(ctx, scored_units, score units, steps, keys, purpose)` then
  `stages.context_kept_histories(ctx, scored_units, rows)` then `unit_normals(..., histories=...)`
  (pipeline/router.py:264-276; owner ruling G1 trims a unit's normal to its kept fit rows). Bank-only units and
  the region kind use plain `unit_normals` (router.py:307, :537).
- Row values: `stages._normals_on(tables, units, season_keys_of(steps, season), link, cut, c)` (stages.py:223-233).
- Neighbour kind (tables): the normal is the donor-row median `report.metrics.baseline_donor_median(donor_rows)`
  (metrics.py:558-564) of the cut's donor rows, one constant, written as `link_forward(median)` per link (R-CN).

### 2.5 Table packages (today coral)

"Coral reads its table store directly": the export reads the store files named in `manifest["config"]["data"]
["files"]` (path + sha256; each sha256 re-checked before the read) through the engine's own reader, and builds the
same per-lead files, so the harness has one code path.
- `TablePipeline` (pipeline/table_run.py:97): `_lock, _load, _groups, _preflight_target, _read` (read_tables,
  package/table.py:481, with the run's excluded groups), `_derive` (derive_all_table). Checks I5-I7 with the
  table config (table_run.py:309-317).
- `state = table_passes.TableRunState(pipe)`; `state.build_pool()` (table_passes.py:109-142: lead-0 pool from the
  lead table; no history block, R17 empty). The engine's TableData holds every label in RAM (the vault reads it);
  the export never reads `pipe.table.y` itself and never writes a test `y` (section 2.6).
- refit / tune rows: `ctx_fit.donor_rows("rival_refit")`, `FitContext(..., pool, lists, 0, GUARD).donor_rows("rival_tune")`.
- inner rows: as table_passes.py:317-330 (train-marked rows dated guard_cut+1..fit_cut with a valid label, S1
  `save=False`, `labels.decision_surface`). Donor-only groups' rows are included (ruling W1).
- test rows: `state.test_rows()` (table_passes.py:406-411) then S1 `save=False`.
- lead L: `pool_L = state.open_lead_pool("pool_lead_L", L)` (table_passes.py:149-169);
  `vault_L = labels.for_lead(lt.present, L)` (labels/rows.py:201); `FitContext(..., vault_L, pool_L, lists, L, FIT)`
  for refit rows, `(..., L, GUARD)` for guard-fit rows; guard rows as table_ladder.py:296-317 (refuses an absent
  guard row, as the engine); test rows = test rows present at L (table_ladder.py:481-497), then S1 `save=False`.
- No history block, so `guardside/` holds only `ngd__<link>` (the guard-cut donor median).

### 2.6 Test labels stay unreadable until the lock

- No export file holds a test label: `test/*.parquet` has no `y` column; train files hold only rows dated at or
  before the lead's fit cut (asserted: max `time` of every `r_refit` row <= fit cut; of `r_tune`/`r_guardfit`
  rows <= guard cut, equal to fitctx_log `max_label_time`).
- The export never opens the run's `test_preds.parquet` with the `y` column: it reads
  `pyarrow.parquet.read_table(path, columns=["unit","group","time","lead","issue","normal","legal_min","legal_max"])`
  only. Same for `ladder/lead_L/test_preds.parquet`.
- The export never calls `open_test_labels` (labels/vault.py:665), `lock_adoption` or any pass that does.
- The harness has ONE function that reads test `y` (section 3.8). It refuses unless the picks lock is valid.
- A table store holds test labels on disk; the export reads them only inside the engine's vault (G-LOCK holder)
  and never copies them out.

### 2.7 Parity proof (all must pass before `export_manifest.json` is written; each a refusal)

| id | what | compared with |
|---|---|---|
| P1 | refit rows: `labels.vault.row_key_hash(units, times)` (labels/vault.py:144) and row count | fitctx_log.parquet: `object_kind=="donor_rows" & purpose=="bank" & lead==L` `row_key_hash`, `n_rows`, `max_label_time` |
| P2 | tune rows (lead 0) | fitctx_log `purpose=="bank_inner"` (lead 0, guard) |
| P3 | guard-fit rows (lead >= 1) | fitctx_log `purpose=="bank_guard"` (lead L, guard) |
| P4 | inner rows: (unit, time) in order and `y` byte equal | `inner_preds.parquet` columns unit, time, y |
| P5 | guard rows: (unit, time, issue) in order and `y` byte equal | `ladder/lead_L/guard_preds.parquet` |
| P6 | test rows: the same (unit, group, time, lead, issue) set, no duplicate; the export records the saved row order so the harness can restore it | lead 0 `test_preds.parquet`; lead L `ladder/lead_L/test_preds.parquet` (keys only) |
| P7 | tree column list == `manifest["feature_list"]`; its sha (`runs.manifest._hash_or_none`) == `manifest["feature_list_hash"]`; history columns == plan.json `history_columns`; context == plan.json `context` == `manifest["config"]["context_list"]` | manifest.json, plan.json |
| P8 | groups == `manifest["config"]["groups"]`, == tables.json fit-cut store build groups; bank and scored unit lists hash == `manifest["unit_list_hashes"]` | manifest.json, tables.json |
| P9 | identity FIT-cut normal on test rows == saved `normal` column, byte equal (NaN on both sides for the neighbour kind) | test_preds (key-joined) |
| P10 | GUARD-cut normal on inner rows, per link: `|normal_link - link_forward(pre__<link>_trees_off_unweighted)| <= tolerance[link]` (the run's R36 tolerance, decision_checks.json `tolerances.tolerance`); for the neighbour kind the guard-cut median vs `base__donor_median` is NOT compared (per-fold medians, R-CN) and is printed | inner_preds |
| P11 | guard-cut normal on guard rows, for each link saved in guard_preds (pinned link and identity), same tolerance rule; neighbour kind: guard-cut median clipped == `base__donor_median` byte equal | guard_preds |
| P12 | c == `derived["R23:lead=L"]` value; legal range == test_preds legal_min/legal_max | derived.json |
| P13 | the 0-filled export of each fit set == the engine's `DonorRows.X` per group (2.3) | engine hand-out |
| P14 | determinism: a second export of one group (the smallest) gives byte-equal parquet bytes | |

`export_manifest.json`: format `rivals-export/1`, run folder/name/fingerprint, package path/name/fingerprint,
engine (LIVE sha, stripped hash, run's hashes, lineage hops used), derived_sha256, router kind, links, c, ub,
legal range, cuts (`fit_cut`, `guard_cut`, `inner_fit_end_step` from derived R11), column lists, counts and
row-key hashes per role, every P-check with its numbers, zero share of refit `y` and legal_min (for the Tweedie
data rule), seen_during_design groups, strata columns, file list {path, sha256, rows}, export code sha256
(sha of rivals/export.py and rivals/layout.py bytes), timings, peak RSS.

### 2.8 Resume, determinism, logging

- Export key = sha of {run fingerprint, package fingerprint, lead, roles, export code sha, LIVE engine sha}.
  A rerun with `--resume` skips each group file whose `_progress` record has the same key and whose file sha
  matches; any other file in the lead folder is moved aside. The engine's census/R30 checkpoints resume by the
  engine's own keys.
- Order: groups in sorted order; rows within a group in grid order (unit, then step), as the engine hands them out.
- Log: `<lead dir>/export.log` (append; UTC per line; every engine echo line too) and `status.json` heartbeat.

### 2.10 The lean export (owner ruling AA4; `export.py` `LeanEngine`, `LEAN_STEPS`)

While the engine derives (`export_run`, around `pipe._derive()`), two engine steps that only GUARD and change no
exported value are taken from the run's own record instead of being measured again. Only attributes of
`treeroute.pipeline.stream` are replaced, in this process, and always put back on exit; no engine file is written.

| step | engine code | taken from the run | applied when | what still checks it |
|---|---|---|---|---|
| R30's per-test-year missing count over every census row of the test years (with its window check) | `pipeline/stream.py` `StreamedShareReader.measure` -> `_count_setup` / `_count_group` / `_check_block` | `derived.json` `R30.inputs.test_year_missing_share`, put into the reader's own count cache in the engine's order, so the engine's count never starts | only when the count would run (not every census row is a picked row); when every row is picked the engine takes the shares from the picked readers at no extra cost and nothing is skipped (recorded as `not_needed`) | R30 only feeds a refusal gate (engine `derive/unit_rules.py:526-540`), never an exported value, so a wrong share could only make the export refuse. The shares are COPIED from `derived.json`, so I7's comparison with that same file cannot catch a wrong share by itself; what protects the copy is I5's data-file check (size and mtime: the census is the run's) and the `first_pass_sha256` cross-check of `derived.json` (engine `pipeline/run.py:849-859`). On a run with an accepted engine difference (pm25) the lean export cannot show an R30 difference that LIVE's own count would give; exported values are not affected (P15 is forced there); `--full-engine-checks` (about +2.7 h on pm25) runs that audit |
| the per-group path's separability check on a sample | `pipeline/stream.py` `check_group_separable` (one sample reader of the sampled groups together, one per group) | `per_group_plan.json` `separability`, used only when it shows the check passed (or was not needed); otherwise the check runs | per-group path | the per-group path is the run's own path; P1-P14 (and P15 with `--p15` or an accepted engine difference) check rows, labels, normals, c and banks byte for byte |

- The export manifest records `lean_export` (`on`, and per step `skipped` / `not_needed` / `ran` counts); it is not
  part of the export key or of the content hash, because the files are the same bytes.
- Timing check (the "when a check confirms the time saving" of AA4), defo smoke run, fresh roots, P15 on
  (test `test_aa4_defo_smoke_lean_equals_full_and_its_time`): in the AA check run (`pt/aa/check_full.log`, both
  disk caches warm) full 50.1 s and 51.0 s, lean 45.1 s and 45.8 s. The builder's first run gave full 80.1 s (cold
  cache) and 49.7 s, lean 44.1 s and 43.9 s (derive 34.4 / 16.2 s full vs 10.7 / 10.9 s lean); that file was
  overwritten by the check run. The test now also writes a time-stamped copy
  (`evidence/aa4/defo_smoke_timing_<utc>.json`), so a later run never overwrites the cited numbers. On the smoke every census row is picked, so this saving is the separability check alone (about 5.5 s of
  ~49 s). At full size the R30 test-year count is the large part: the headline runs' own logs give 590 s (defo
  run.log:207), 4,153 s (fire run.log:191) and 9,830 s (pm25 run.log:543) for that count, which the lean export no
  longer repeats. NDVI's headline log loaded it from a checkpoint
  (`runs/ndvi/headline/20261016_d1de3158/run.log:159-160`), so it gives no measured figure; NDVI's count reads
  about 604M rows and 256k files (pm25's 9,830 s count read 195M rows), and a fit of time to rows and files on
  fire, pm25 and defo puts it at roughly 7-23 h. **Never run an NDVI export with `--full-engine-checks` without
  asking the owner.** The 4.0 h saving of the three measured runs is not yet seen on a real export (the defo smoke
  had nothing to skip); fire's export is the first check: its manifest's `derive` time should be about 1,700 s,
  against 5,841 s in the headline. The separability check runs once per export call, so NDVI (one lead per call)
  skips it three times: up to about 1.58 h saved in all (129 + 620 + 1,016 + 3 x 1,312 s), not 0.85 h.
- Byte identity: the grid toy (`test_aa4_lean_export_is_byte_identical_on_the_grid_toy`) and the defo smoke export:
  every listed file has the same path, sha256 and rows, the content hash is equal, and P1-P14 (toy) / P1-P15
  (smoke) pass in both exports. The count skip itself is tested on the engine class with a stand-in measure
  (`test_aa4_the_r30_count_is_taken_from_the_run_only_when_it_would_run`): no cheap real run has unpicked census rows.

### 2.9 Sizes, RAM, disk and time per problem (x = extrapolated)

Rows per lead from each run's fitctx_log and saved parquets (2026-10-20). Columns = tree+history + context + one
normal per link. Size = float32 features, uncompressed upper value.

| problem | cols (x/c/links) | lead 0: refit / tune / inner / test | lead L: refit / guardfit / guard / test | export size (all leads) | export RAM = engine derive peak (per_group_plan.json `ram.derive_peak_gib`) | engine temp disk during export (pool + guard history pool; no tree tables) | export time (x) |
|---|---|---|---|---|---|---|---|
| pm25 | 122 / 2 / 2 | 2,590,280 / 2,133,214 / 68,559 / 91,440 | L6: 2,526,780 / 2,069,714 / 59,034 / 91,440; L12: 2,450,597 / 1,993,576 / 47,606 / 91,440 | ~4.1 GB | 5.4 GiB | ~1.6 GiB | census+derive ~4.4 h (pm25 run.log:33, :928) + 3 pool fills |
| ndvi | 498 / 9 / 1 | 2,680,841 / 2,205,498 / 68,999 / 95,184 | L6: 2,614,487 / 2,139,143 / 59,104 / 95,184; L12: 2,535,117 / 2,059,787 / 47,267 / 95,184 | ~5.7 GB per lead | 6.1 GiB | ~6.4 GiB per lead | derive 2,270 s after census (ndvi run.log:299); lead 6 and 12 reuse census/R30 checkpoints |
| fire | 131 / 2 / 3 | 751,508 / 609,838 / 68,901 / 96,000 | L6: 731,546 / 589,965 / 58,922 / 96,000; L12: 708,099 / 566,516 / 47,188 / 96,000 | ~1.4 GB | **8.3 GiB** | ~0.5 GiB | census 826 s + derive 5,841 s (fire run.log:27, :317) + 3 pool fills (~9 min each) |
| defo | 308 / 0 / 3 | 3,011,184 / 2,446,587 / 276,822 / 369,096 | L1: 3,011,184 / 2,446,587 / 276,822 / 369,096 | ~8.5 GB | 4.7 GiB | ~4.4 GiB | census 90 s + derive 1,052 s (defo run.log:35, :339) + 2 pool fills (~1.6 h each, defo run.log:344-471) |
| coral | 63 / 5 / 3 | 11,338 / 9,292 / 2,046 / 2,312 | L183: 10,838 / 8,804 / 1,554 / 2,312; L365: 10,567 / 8,603 / 1,283 / 2,312 | ~10 MB | < 0.5 GiB | ~0 | seconds |

- Fire's 8.3 GiB and NDVI's 6.1 GiB exceed the build limit of ~6 GB: full-size exports are OWNER commands only,
  other apps closed. Builders run only the toy, smoke (defo 0.65 GiB, fire 2.6 GiB derive peak) and coral sizes.
- NDVI one lead at a time: lead export ~5.7 GB + engine temp ~6.4 GiB at the export, then the temp is freed;
  the harness's materialized memmap of one fit set (~2.2-2.7M x 508 x 4 B = 4.5-5.5 GB) replaces it while fitting.

---

## 3. THE HARNESS (`rivals/harness.py`, `rivals/models.py`, `rivals/cli.py`)

### 3.1 Commands (each takes the heavy-job lock, refuses when held, is resumable, prints one plain line per step)

```
py -3.9 -m rivals.cli init   --run <run folder> --export <export lead_0 folder> [--extra-learners hgb_l1] --out <out_root>
py -3.9 -m rivals.cli probe  --out <folder> --lead 0          (20-round LightGBM + 10-tree RF at the real shape: time and peak RAM; no inner score)
py -3.9 -m rivals.cli tune   --out <folder> --resume
py -3.9 -m rivals.cli lock   --out <folder>
py -3.9 -m rivals.cli refit  --out <folder> --lead <L> --resume   (guard fit, N2, refit, predict test: raw and guarded)
py -3.9 -m rivals.cli score  --out <folder> --lead <L>
py -3.9 -m rivals.cli board  --out <folder>
```

`init` writes `board.json` once: the run folder and fingerprint, export manifest sha per lead, the learner list
from the data rules (3.2), every grid (3.4), threads, harness code sha (sha of rivals/*.py bytes), library
versions (lightgbm, sklearn, scikit-learn-intelex pip version via importlib.metadata, numpy, pandas, pyarrow,
threadpoolctl), our layer's candidate count (rows of the run's inner_candidates.csv) printed beside the trial count.

### 3.2 The board (lean, ruling Y1) and its data rules (no problem name anywhere)

| learner id | rival | switched on when (read from the run and export) |
|---|---|---|
| `ridge` | C1 Ridge | always |
| `rf` | C2 Random Forest (sklearnex) | always |
| `lgbm` | C4 LightGBM | always |
| `lgbm_tweedie` | C5 LightGBM-Tweedie | legal_min == 0 AND zero share of lead-0 refit `y` >= 0.20 (export manifest) AND `log_c` is an R22 link (it needs the run's c; otherwise REFUSE with an owner item) |
| `hgb_l1` | C6 HistGradientBoosting, absolute error, labelled timid-prone | only with `init --extra-learners hgb_l1` (R-C6) |

XGBoost (C3) is absent (Y1). Links offered = derived R22 (`plan.json["links"]`).

### 3.3 Data preparation (same for every trial)

- X for tree learners (rf, lgbm, lgbm_tweedie, hgb_l1): `x__*` then `c__*` then the normal of the trial's link
  (`n__` column, a plain feature: Q16 a "offset AND column"), NaN -> 0.0 (the engine's R30 0-fill,
  pipeline/stages.py:161-171). For tune, inner, guard-fit and guard rows the history columns come from
  `guardside/` (`h__*` replaces the matching `x__` history columns) and the normal from `ngd__<link>`; for refit and
  test rows from `train/`/`test/` (`nfit__<link>`).
- X for Ridge: same columns, NaN -> the column mean over the fit's own train rows, plus one 0/1 missing flag per
  column that has any NaN in those train rows (Q7 a); then standardised with the train rows' mean and sd
  (sd 0 -> column dropped, recorded). Flags and scaling are rebuilt for every fit set (rule 9).
- Offset (Q16 a): z0 = the row's link-space normal.
  - lgbm: label = link(y); `init_score = z0` on the Dataset; prediction z = z0 + raw score.
  - lgbm_tweedie: label = y (raw, >= 0); `init_score = log(max(normal_identity, c))`, normal_identity = the
    row's `nfit__identity` / `ngd__identity` (the identity normal is in y units); prediction y = exp(init + raw).
  - rf, ridge, hgb_l1: target = link(y) - z0; prediction z = z0 + f(X). Ridge's intercept is unpenalised.
- Link forward/back: `layer.links.link_forward` / `link_inverse` (layer/links.py:84, :118) with the lead's c (A3)
  and ub; no smearing. Pre-clip value kept; clip with `layer.links.clip_to_legal(pred, legal, False)[0]`
  (layer/links.py:261). Never import rivals.py or pm25_rivals.py (`_clip` caps at 1, rivals.py:145-148).
- Loss: squared error, except lgbm_tweedie (Tweedie) and hgb_l1 (absolute error).

### 3.4 The exact grids (fixed; recorded in board.json)

| learner | fixed | grid | staged | trials per link |
|---|---|---|---|---|
| ridge | float64 X'X, chunked; solve with `np.linalg.cholesky` (never scipy's, memory note) | alpha {0.1, 1, 10, 100, 1e3, 1e4, 1e5, 1e6} | all 8 alphas from one X'X per fit set | 1 fit, 8 candidates |
| rf | `sklearnex.ensemble.RandomForestRegressor(n_estimators=300, bootstrap=True, max_samples=min(1.0, 200000 / n_train) as a FLOAT, random_state=0, n_jobs=8)`; criterion squared_error | max_features {0.2, 0.5} x min_samples_leaf {5, 50} | none | 4 |
| lgbm | `objective=regression, learning_rate=0.1, feature_fraction=0.5, bagging_fraction=1.0, bagging_freq=0, deterministic=True, force_row_wise=True, feature_pre_filter=False, num_threads=8, seed=0, verbose=-1`; `max_bin` 255 in tuning and in every final fit (AC1, 3.4a) | num_leaves {31, 127} x min_child_samples {20, 200} | tuning: early stopping on the inner MAE after every round, patience 50, cap 800 (stages {100, 200, 400, 800} kept for the record); extension cap 1600, only for a trial that ran to the 800 cap without a patience stop (AC2; 3.4a, 3.5) | 4 |
| lgbm_tweedie | as lgbm with `objective=tweedie` | the lgbm 4 settings x tweedie_variance_power {1.2, 1.5} | as lgbm | 8 in all (no link loop) |
| hgb_l1 | `HistGradientBoostingRegressor(loss="absolute_error", learning_rate=0.1, max_iter=800, early_stopping=False, random_state=0)` | max_leaf_nodes {31, 127} x min_samples_leaf {20, 200} | `staged_predict` at {100, 200, 400, 800}; extension cap 1600 when its own best is 800 (3.5) | 4 |

### 3.4a LightGBM speed-ups (owner rulings AA2, AC1, AC2; `models.py` `EarlyStop`, `_RoundScorer`, `_tree_output`, `ran_to_cap`; pre-registered)

- **Early stopping (AA2), tuning only, lgbm and lgbm_tweedie.** After every round the trial's inner prediction is
  scored with the pick criterion (the engine's `mae` of the clipped prediction, the inner labels of the export):
  the round's tree output on the inner rows is added to a float64 sum in tree order (the same additions
  `booster.predict(num_iteration=r)` makes), read from the tree's `dump_model` record (calling the library's
  predict between two training rounds slowed every later round about a hundredfold here, measured). The trial stops
  once **50** training rounds in a row (`PATIENCE_ROUNDS`) bring no strictly lower inner MAE, or at the cap (800;
  1600 when extended). Its pick is its best round (ties: the earlier round). A round is a tree of the model (an
  iteration where LightGBM finds no split adds no tree and counts as a round without improvement).
- The trial keeps the predictions of the stages reached ({100, 200, 400, 800}, {1200, 1600} when extended), of the
  best round, and (extended) of every round its base trial kept. At each kept round the inner MAE from the finished
  model's own prediction must equal the per-round MAE bit for bit (else the fit refuses). trial.json records
  `early_stopping` {patience_rounds, cap_rounds, best_round, best_metric, stopped_at, iterations_run,
  stopped_by_patience, saved_rounds, trace (the inner MAE after every round)} and `tuning` (the options).
- **Test rows are never read:** the only score set of a tuning fit is the inner set (`harness._run_trial` refuses
  any other), and the early-stop metric closes over the inner labels only.
- **Bins (AC1, replaces AA3).** Every LightGBM fit, each tuning trial and each final fit (the refit at the fit cut,
  every guard fit), bins the features into LightGBM's default 255 histogram bins (`models.LGBM_MAX_BIN`; the
  Dataset and the training parameters both carry `max_bin`; trial.json `fit_info.max_bin` and `tuning.max_bin`,
  done_<learner>.json `final_fit.max_bin` record it). A final fit differs from its tuning trial only in running the
  picked round count with no early stopping, so the tuning trial at its pick IS the final model fitted on the tune
  rows: its trees and its inner predictions at that round equal a fresh 255-bin fit's byte for byte (tested,
  `test_aa_speedups.py::test_ac1_the_tuning_trial_at_its_best_round_is_the_final_fit_at_that_round`). The lead-0
  guard therefore reuses the tuning trial's predictions (3.7), as before AA.
  - Why (ruling AC1): the 63-bin tuning of AA3 picked a round count that did not carry to the 255-bin refit (AA
    review toy: best round 12 at 63 bins against 743 at 255, inner MAE 1.862 against 1.564; coral inner rows: 6.47
    at the pinned 63-bin round against 6.385 at the best 255-bin round, `pt/aa/coral_bins_probe.json`). The 63 bins
    saved only 14-23% per round (AA_CHECK_REPORT.md section 4). The 63-bin code is in
    `_moved/20261021_preAC_code/rivals/`.
- **The pick is any round (AA2).** The round is chosen from up to 800 per trial (not from 4 stages) on the same
  inner rows the lead-0 guard uses later, so the rival's inner MAE is a little optimistic and its guard a little
  easier to pass. This favours the rival; disclosed.
- **Extension only for a trial that ran to the cap (AC2).** `models.ran_to_cap(early_stopping)` is true only when
  the trial was NOT stopped by patience (`stopped_by_patience` false) and ran all `cap_rounds` iterations (a record
  that says "not stopped" yet ran fewer refuses). With patience 50 such a trial's best round lies in (750, 800], in
  the last stage before the cap. A trial stopped by patience (even exactly at round 800) is not extended: its
  extension would repeat it unchanged (same rounds, same stop), so it could change no pick (3.5).
- The trial config hash includes the tuning options (with the extension rule and the bins); the refit hash includes
  the final-fit options.

- **RF stride (Q9 b, generic rule; SUPERSEDED by ruling Z2, the out-of-core RF of `models.py`).** data_bytes = rows x columns x 4 of the RF fit set; s = the smallest
  integer >= 1 with 2.6 x data_bytes / s <= RF_RAM_BUDGET = 4.5 GiB (2.6 = the measured peak factor, plan 5a).
  With today's sizes this gives pm25 1, fire 1, coral 1, ndvi 4, defo 3: the plan's numbers. The stride keeps
  every s-th unit of each group's sorted bank-unit list (units[::s]), for RF only, at every RF fit (tune, refit,
  guard-fit); the kept-unit list hash and s are recorded and disclosed. max_samples is then 200000 / kept rows.
- One fit set (tune rows; refit rows of lead L; guard-fit rows of lead L) is binned once: LightGBM `Dataset`
  built once from an `lgb.Sequence` over the materialized memmap (3.10), `free_raw_data=False`; settings and
  links reuse it with `set_label` / `set_init_score`; a new Dataset per fit set (bins from its own rows, rule 9).
- Determinism: random_state / seed 0, never varied (memory: no seeds); 8 threads everywhere.

### 3.5 Tuning (lead 0 only; plan rules 8, 9; Y2, Y3/Q12 a)

- Fit rows = tune rows (guard-cut donor rows at lead 0). Score rows = inner rows. Each trial = one learner x
  setting x link (Tweedie: x power). One staged fit per trial; checkpoints scored on inner rows only.
- Per trial and checkpoint: inner MAE of the CLIPPED prediction (the pick criterion, MAE decides), corr2,
  calibration ratio, and predict-zero MAE beside; all with `report.metrics.mae / corr2 / calibration_ratio`
  (metrics.py:569, 604, 623).
- Pick per learner = lowest inner MAE over setting x link x checkpoint; ties broken by the fixed order
  (link order of R22, then grid order, then the smaller checkpoint).
- **Extension (Y2, reading R-Y2 b of Z3, with AA2 and AC2):** after a learner's base grid is complete, these
  trials are refit FROM SCRATCH with cap 1600 (same Dataset, same params, the same patience for lgbm /
  lgbm_tweedie):
  - hgb_l1 (scored at 100, 200, 400, 800 only): every trial whose own best is 800;
  - lgbm and lgbm_tweedie (AC2): only a trial that ran to the 800 cap without a patience stop
    (`models.ran_to_cap` on its trial.json `early_stopping` record; its best round then lies in the last stage,
    (400, 800]). A trial stopped by patience is never extended, whatever its best round
    (`harness.trials_to_extend(rows, pick, ran_to_cap)`, `harness._extension_ids`; a base trial without an
    early-stopping record refuses). The extended trial must reproduce every round its base trial kept byte for byte,
  and (lgbm, lgbm_tweedie) the base trial's per-round inner MAE (determinism checks, refusal otherwise). The
  learner is re-picked over all its trials, an extended trial replacing its base trial. A pick in (1200, 1600] is
  FLAGGED (`edge_rounds_1600`), never extended. Lower edge: hgb_l1 (staged) at 100 iterations is flagged
  `edge_rounds_100`; lgbm / lgbm_tweedie (any round can be picked) only at round 1, flagged `edge_round_1` (a pick
  at round 63 is an interior best, not an edge; AA review item 4).
  Before AC2, an early-stopped trial with its best round in (400, 750] (already stopped by patience) was extended
  literally and only reproduced itself; AC2 removed that repeat (no pick can change, time is saved).
- Ridge: a pick at alpha 1e6 is flagged (`edge_alpha_1e6`), not extended.
- One tuning per learner, on the nowcast; the pick (setting, link, rounds/alpha) is PINNED at every lead.

### 3.6 The lock (rule 17)

- `lock` refuses unless every learner of board.json has a complete grid (and its extension when triggered).
- It writes `picks.json` (write-once): per learner the pick, its inner MAE, flags, the N2 result at lead 0
  (comparator name, comparator MAE, eligible), trials.csv sha256, board.json sha256, export manifest shas.
  `inner_mae_and_n2_are_of` says whose numbers these are: for every learner the tuning model's, which is the
  reported model's lead-0 guard model (AC1: lgbm / lgbm_tweedie tune at the same 255 bins they refit at), so they
  equal `lead_0/done_<learner>.json` `guard.rival_mae` / `guard.passed` (tested on the table toy).
- Then `picks.json.lock.json` = {file, sha256 of picks.json bytes, utc, harness code sha, rule}. A changed
  picks.json later is refused (sha check on every later command).
- No test file and no test label is opened before the lock (section 3.8 and tests T1-T3).

### 3.7 Per-lead fits (`refit --lead L`; requires the lock)

1. **Guard (our N2, applied to the rival; O2 c / Q11 c).**
   - Lead 0, every learner (AC1 for lgbm and lgbm_tweedie): the guard is the tuning fit at the pick, on the inner
     rows (no new fit; `guard.source` "the tuning trial's inner predictions at the pick"). For lgbm /
     lgbm_tweedie the refit first checks that the tuning trial's `fit_info.max_bin` equals the final fit's (255),
     else it refuses. (Under AA3 the lead-0 guard was a second 255-bin fit on the tune rows; that branch is gone,
     its code is in `_moved/20261021_preAC_code`.) Comparator = the inner_preds
     column `<link>_trees_off_unweighted` of the pick's link (clipped, as saved). For a run with a decline baseline
     (decision_checks.json has `decline_baseline`, ruling V1) the comparator is that column (`base__donor_median`).
   - Lead L >= 1: fit the pick on the guard-fit rows of lead L (guard cut, guard-cut history and normal);
     predict the guard rows. Comparator = clip(link_inverse(ngd__<link>)) on the guard rows (= the trees-off of
     that link; parity P11 proved it on the saved links); V1 runs: guard_preds `base__donor_median`.
   - Tweedie comparator: the identity trees-off (R-TW).
   - Passed iff MAE(rival, clipped) < MAE(comparator), strictly (`layer.decide.n2_eligible`, decide.py:290-299).
2. **Refit:** the pick on the refit rows of lead L (fit cut), the pinned rounds / alpha; RF out of core (Z2);
   lgbm and lgbm_tweedie with 255 bins (AC1, the same as their tuning). The lead-L guard fit uses the same options.
3. **Predict test rows** (`test/` files; first read of any test file, allowed only after the lock): pre-clip and
   clipped. **Guarded** = raw if the lead's guard passed, else the run's decline target column read from the
   lead's saved test_preds (`arm__identity_trees_off_unweighted`; V1 runs `base__donor_median`) by key join,
   reading prediction columns only (never `y`).
4. Save `lead_L/preds_<learner>.parquet`: keys, `pre__rival_<learner>`, `arm__rival_<learner>_raw`,
   `arm__rival_<learner>` (guarded), guard flag; and `lead_L/guard_<learner>.parquet` (guard rows, prediction,
   comparator). GBM model files are saved; RF models are not (plan 5c), their predictions are.

### 3.8 Scoring (`score --lead L`; the only reader of test `y`)

- `open_test_labels_rivals(run, lead, out)`: refuses unless picks.json.lock.json exists and its sha matches
  picks.json, and every learner's `preds_<learner>.parquet` for that lead exists. Then it reads the saved
  test_preds of the lead WITH `y`, writes `test_labels_opened_rivals_lead_<L>.json` (utc, picks sha, rows), and
  joins the rival rows to the saved rows one to one by (unit, time, lead), in the saved order, and refuses a
  missing or extra key (F65: every column is scored on the same saved y, max|y difference| = 0 by construction).
- Frame: keys, `y`, `normal`, legal columns and baselines from the saved test_preds; the rival columns; OUR
  columns: the headline answer `ours` = `lead.json["test"]["adopted_column"]` at a lead and, at the nowcast,
  `arm__<verdict.adopted>` (or the decline target when `verdict.declined`); our pinned arm raw beside.
- Tables with the LIVE engine's own `report.metrics.score_table(frame, ("group",), tol, floor, kind)` and
  `("year",)`, `()` (metrics.py:846), tol = verdict.json `hit_tolerance`, floor = `measurement_error_floor`.
  Per-stratum tables with the run's own edges (per_stratum.csv `edge_q*`) and `units.parquet` values;
  NDVI-type runs also without their seen_during_design groups (export `units.parquet`).
- Contrast: per group MAE maps; `d_g = MAE_rival(g) - MAE_ours(g)` through `metrics._paired_contrast(rival,
  ours)` (metrics.py:1123-1137) and `metrics.contrast_tag(d, band)` (metrics.py:1097-1121), band = the NOWCAST
  verdict.json `band` at every lead; BEATS = HELPS, LOSES = HURTS. `metrics.blocked_jackknife` with derived
  `R14:overlap_blocks` beside. Guarded-vs-headline decides; raw-vs-raw printed beside.
- Timid flag (rule 14): a rival MAE win with calibration ratio < 0.5 or corr2 < half of ours. Printed, verdict
  unchanged. Predict-zero, guess-normal, persistence and damped persistence rows are printed from test_preds.
- Every number written to `scores/` (CSV per table) and `board_lead_<L>.csv`; `board` builds `board.md`.

### 3.9 Outputs (every row-level prediction saved)

`trials/<learner>/<trial_id>/{trial.json, inner_preds.parquet}` (inner rows keys + pre-clip and clipped
prediction per checkpoint), `trials.csv` (rebuilt from trial.json files in a fixed order), `picks.json` + lock,
`lead_L/{preds_*, guard_*, model_*}`, `scores/`, `board_lead_L.csv`, `board.md`, `rivals.log`, `status.json`.

### 3.10 Mechanics

- **Materialize:** per fit set, a float32 C-ordered memmap `materialized/lead_L_<set>.f32` (rows x columns of
  the learner family) + `index.parquet` (keys), written once with its sha; `lgb.Sequence` and RF/Ridge read it in
  blocks. Moved aside after the lead's scores are written (owner deletes).
- **Threads:** `rivals.cli` sets OMP/MKL/OPENBLAS/NUMEXPR to 8 before importing numpy, then
  `threadpoolctl.threadpool_limits(8)`; `threadpool_info()` saved in board.json; never changed mid-board
  (memory: --jobs changes results).
- **Heavy-job lock:** `treeroute.runs.preflight.HeavyJobLock(machine.temp_dir)` (runs/preflight.py:168) held
  for the whole command.
- **RAM:** a go/refuse estimate before each fit (LightGBM: rows x cols x 1 B bins + 2 GiB; RF: 2.6 x data;
  Ridge: 1 GiB); a watchdog thread polls the process tree RSS (psutil) every 2 s and stops the command at 12 GiB
  with a failure line; the trial in flight is redone on resume.
- **Resume:** each trial has a config hash (learner, params, link, fit-set export sha, harness code sha). A
  finished trial (trial.json with that hash) is skipped; a partial one is moved aside and redone. Lead steps the
  same, per learner.
- **Logging:** `rivals.log` (append, UTC, stage, learner, trial, seconds, peak RSS) and `status.json` heartbeat.
- **Time (x, lean board, upper, from plan 5c without XGBoost and at 800 rounds):** pm25 ~2.5 h, ndvi ~7.5 h,
  fire ~2.2 h, defo ~11.5 h, coral < 0.2 h; an extension can double that learner's tuning.

---

## 4. TEST PLAN (`rivals/tests/`, pytest, py -3.9, `--basetemp D:/treeroute/rivals_build/_pt/<run>`; the parent folder must exist)

### 4.1 Toy data

- Grid per-unit toy: `tests/test_pipeline.py` `make_pipeline_package` (:157) + its `_machine`/`_run` pattern
  (:275-291) with `FAKE_LAUNCH`, kind smoke, everything under the test's basetemp. Variants: `sparse=True` (R12
  fallback units), `decline=True` (a declined nowcast).
- Table toy: `tests/table_toy.py` `build_toy_table_package` (:174) variants `ok` and `donor_only_group`, run with
  `run_toy` (:287), `toy_machine` (:274).
- Region kind: no engine toy runs it end to end through the pipeline (tests/test_route_region_pipeline.py drives
  the kernels only), so the defo smoke (4.3) covers it.
- Engine test helpers are imported read-only by adding the engine's `tests/` to sys.path.

### 4.2 Unit tests (toy runs; each < 1 min; RAM < 1 GB)

| id | test |
|---|---|
| T1 | no test-row read before the lock: a spy on `pyarrow.parquet.read_table` / `pandas.read_parquet` / `open` records every path and column list; `export`, `init`, `tune`, `lock` never open a `test/` file and never request `y` from any test_preds; `refit` before `lock` refuses |
| T2 | `test/*.parquet` has no `y` column; train rows' max time <= fit cut; tune/guard-fit rows <= guard cut |
| T3 | `score` refuses without the lock, with an edited picks.json, and with a missing learner's preds |
| T4 | parity refusals, one per check: package fingerprint changed (copy the toy package, edit a catalog line), derived.json differs (edited copy of the run folder), data file mtime changed, engine_modules differ with no lineage hop, versions differ (patched), feature list differs, row-key hash differs (edited fitctx_log copy), test keys differ (one row dropped), normal differs (edited `normal`) |
| T5 | parity passes on the toy grid run (lead 0 and both leads) and the toy table run (all three leads), every P-check |
| T6 | engine-lineage logic: a fake chain with one missing hop refuses; a complete chain passes; the proof line must name the package |
| T7 | extension rule (Y2, R-Y2 a) on synthetic trial results: best at 400 -> no extension; learner pick at 800 -> only that learner's trials whose own best is 800 extend to {1200,1600}; pick at 1600 -> flagged, no further extension; checkpoint 100-800 mismatch after the refit -> refusal |
| T8 | offsets: a model whose f == 0 (lgbm 0 rounds; ridge with alpha -> huge; RF on a constant-zero residual target) returns exactly the normal for every link (the R16 analogue); Tweedie with raw score 0 returns max(normal, c) |
| T9 | links: forward/inverse round trip <= 1e-12 for identity, log_c, arcsine with the run's c and ub; clipping uses clip_to_legal and keeps pre-clip; the code never imports rivals.py / pm25_rivals.py (scan) |
| T10 | RF: `max_samples` is a float; a fitted sklearnex forest predicts on fewer rows than it was fitted on (R5); stride rule gives s for the five table sizes (1,1,1,4,3) |
| T11 | determinism: tune twice on the toy table run -> byte-equal trials.csv, inner preds and picks.json |
| T12 | resume: stop after trial k (raise in a hook), rerun -> trials 1..k skipped, final outputs byte-equal to an uninterrupted run |
| T13 | heavy-job lock held by a live process -> every command refuses; stale lock -> refuses with the engine's message |
| T14 | plug and predict: the engine's `tests/nonames_scan.py` over `rivals/` finds no problem name; data rules switch Tweedie on/off from (legal_min, zero share, links) only |
| T15 | scoring path: on the toy run, score_table / contrast_tag outputs equal a hand computation from the same frame; the verdict tag uses the run's band |
| T16 | guard: a rival worse than its comparator on the guard rows gets the decline target column as its guarded test prediction; better -> raw |
| T-AA | ruling AA (`tests/test_aa_speedups.py`): early stopping picks the best round (the first lowest per-round inner MAE, equal to the library's own prediction at every round), stops 50 rounds after it, and its trees equal a plain fit's; Tweedie too; only the named inner set is scored, misuse refuses; the extension still triggers for a trial that ran to the cap and reproduces its base trial; the rules on early-stopped rows, with AC2 (a patience-stopped trial is never extended; `ran_to_cap` fails loud on a bad record); AC1: 255 bins in tuning and in final fits, no 63-bin constant left, and the tuning trial at its best round equals a fresh final fit at that round byte for byte (lgbm and Tweedie); on the table toy: tuning fits score the inner rows only, no test file is read, trial.json records patience / best round / trace, the harness extension path runs (rule forced), unforced AC2 (exactly the ran-to-cap trials are extended), refit and guard fits use 255 bins and the lead-0 guard is the tuning trial with picks.json's inner MAE; the lean export is byte-identical to the full export on the grid toy (P1-P14 pass); the R30 count is taken from the run only when it would run; the CLI switch; real data (RIVALS_REAL=1): the defo smoke lean vs full export, byte-identical, P1-P15, timing evidence |

### 4.3 Smoke-size grid export parity (real package, R21 smoke groups)

- Target: the LIVE-engine defo smoke run `D:/treeroute/coral_build_v6b/noop/new/defo/smoke/20261020_192b4285`
  (engine stripped hash 85c64b55 = LIVE, so no lineage hop; package `datasets/defo`, fingerprint d607314e = the
  headline's). Region kind, 4 groups x 40 units, leads 0 and 1, 3 links. Derive peak 0.65 GiB.
- Command: `export --run <that folder> --package <engine>/datasets/defo --lead all --config <test rivals.yaml>`
  (machine temp_dir, run_root and export root under rivals_build). Expected: I1-I9 and P1-P14 pass; inner 480
  rows, test 640 rows per lead.
- Second (per-unit kind with context, monthly leads 6/12): fire smoke `.../noop/new/fire/smoke/20261020_ee5cd20a`,
  derive peak 2.6 GiB; run only if `available RAM > 5 GiB` at start.
- Lock rule for builders: before starting, the test checks read-only that `D:/treeroute/tmp/treeroute_heavy_job.lock`
  is absent (no real heavy job running); the engine lock it takes is in the test machine's temp_dir.
- These are export-parity tests only: no rival is fitted on the smoke rows.

### 4.4 Coral tune-only dry pass (real data; stops at the lock)

1. `export --run D:/treeroute/runs/coral/headline/20261020_f3b8e3da --lead 0 --roles tune,inner` into
   `D:/treeroute/rivals_build/_export` (writes no `test/` folder; P6/P9 marked "skipped: dry pass").
2. `init --extra-learners hgb_l1` (pending R-C6), `tune`, `lock` into `D:/treeroute/rivals_build/_dryrun`.
3. Checks: no `test/` folder exists; the T1 spy saw no test file and no `y` request of any test_preds; no
   `scores/` and no `test_labels_opened_rivals*` file; picks.json + lock exist; every trial saved.
4. Expected cost: minutes, < 1 GiB RAM. Trials: ridge 3 fits (24 candidates), rf 12, lgbm 12, lgbm_tweedie 8,
   hgb_l1 12.
5. These picks are LABELLED DRY. They are not the board's picks: the board's coral tune runs after the owner
   signs the rival Part and must reproduce the dry picks byte for byte (determinism check).

### 4.5 Gates and order

Relevant unit tests while building; ONE full rivals suite at the end (memory: lean testing); the engine's own
suite is not touched (no engine edit).

---

## 5. FILE OWNERSHIP (three parallel builders; nobody edits another's file)

| builder | owns (under `D:/treeroute/rivals_build/`) | reads but never edits |
|---|---|---|
| A: export | `rivals/export.py`, `rivals/layout.py` (section 1 exactly), `engine_lineage.json` (generated by `export.py --write-lineage`, from registry freeze locks and no-op proof files) | the engine, packages, runs, registry |
| B: harness | `rivals/__init__.py`, `rivals/cli.py`, `rivals/harness.py`, `rivals/models.py`, `rivals.yaml` (build values of 1.1) | `rivals/layout.py`, `rivals/export.py` (cli dispatches `export.main(args)`) |
| C: tests | `rivals/tests/__init__.py`, `rivals/tests/conftest.py`, `rivals/tests/toy_runs.py`, `rivals/tests/test_*.py`, `pytest.ini`, `_machine/` test machine files | everything else |

Interfaces fixed by this spec: `export.main(argv) -> int`; `export.export_run(run, package, leads, roles, config) -> list[Path]`
(lead folders); `harness.init / tune / lock / refit / score / board(out, ...)`; `models.fit_predict(learner,
params, fit_set, score_sets, checkpoints) -> dict` ; `harness.open_test_labels_rivals(out, lead)`. Shared names and
paths only from `rivals/layout.py`.

## 6. Owner readings and items (answer before the rival Part is signed)

| id | question | recommended |
|---|---|---|
| A1 | accept LIVE (930d961c) for the grid exports through the recorded no-op chain + full parity (I4, I6, P1-P14) | yes; refuse a package whose chain has a gap |
| A2 | rival fallback = the run's decline target (identity trees-off; coral donor median), comparator = own-link trees-off | yes (it is our safety net exactly) |
| A3 | rival c = the run's fit-cut c on every row of a lead (D63 a) | yes |
| R-Y2 | "that model alone is extended": (a) every trial of the learner whose own best is 800; (b) only the picked trial | (a) |
| R-C6 | hgb_l1 only through `--extra-learners hgb_l1`, written into the rival Part (ruling C12 names a problem; the code must not) | yes |
| R-TW | Tweedie's N2 comparator: the identity trees-off | yes |
| R-CN | coral offset: one donor-row median per cut (our decision surface uses per-fold medians) | yes, disclosed |
| O1 | full-size exports above 6 GB RAM (fire 8.3 GiB) are owner commands with other apps closed | yes |

## 7. Change note: ruling AA (built 2026-10-21)

- Code (old versions copied to `_moved/20261021_preAA_code/` first): `rivals/models.py` (EarlyStop, _RoundScorer,
  _tree_output, max_bin, tuning_options, final_fit_options, in_last_stage), `rivals/harness.py` (_run_trial early
  stopping and the extension checks, trials_to_extend, check_extension_prefix, pick_flags, trial_hash, refit final-fit
  options and the lead-0 guard model, board.json rules, probe bins), `rivals/export.py` (LeanEngine, LEAN_STEPS,
  export_run(lean=...), --full-engine-checks, manifest `lean_export`). `rivals/cli.py` unchanged (it passes the
  export arguments through).
- Tests: `rivals/tests/test_aa_speedups.py` (section 4.2 T-AA).
- Departures and readings, for the rival Part: AA1 drops the donor-only board (ruling D's default named both); AA3 is
  read as "63 bins for tuning, 255 for every final fit" (shown to the owner in the ruling); the lead-0 guard of
  lgbm / lgbm_tweedie is a new fit on the tune rows with the final-fit options (it was the tuning trial's
  prediction); an extended early-stopped trial is refit literally even when its base stopped by patience (it then
  reproduces its base).
- Harness code hash after AA: e5032ad59af881d7cf89359b428943263cdb9618e89cfd8d4d1c930402eaffff (was fb8656a9); export
  code sha 189fee1e. Full suite on it: 162 passed, 5 opt-in skipped (`pt/aa/full1.log`, 15.6 min); the defo smoke
  lean-vs-full test passed (`pt/aa/real1.log`); the coral dry pass passed (`pt/aa/coral1.log`).
- Coral tune-only dry pass under AA (inner window only): lgbm tuning 23.0 s -> 7.9 s, lgbm_tweedie 20.5 s -> 6.1 s.
  Picks content hash 3b5a33f1 -> 2a3e224e. lgbm: arcsine, 127 leaves, min child 200, round 63, inner MAE 6.5463
  (was 31 leaves, 200 rounds, 6.4388); lgbm_tweedie: power 1.5, 31 leaves, min child 20, round 181, 6.4522 (was
  6.5649). A diagnostic to 800 rounds without early stopping (`pt/aa/coral_bins_probe.json`) shows the 63 bins cost
  coral about 0.14-0.21 of inner MAE at each trial's best round (e.g. arcsine 31/200: 6.5264 at 63 bins vs 6.3872 at
  255 bins), and patience 50 stopped that trial at round 84 although its 63-bin best was round 289. OWNER ITEM.

### 7a. AA fixes after the two AA reviews (2026-10-21)

Old code copied to `_moved/20261021_preAAfix_code/` first. No pick changes (picks content 2a3e224e).
- `harness.py` `pick_flags`: the lower-edge flag of lgbm / lgbm_tweedie is `edge_round_1` (a pick at round 1);
  hgb_l1 keeps `edge_rounds_100`. board.json rules: the bins rule says the round count is chosen at 63 bins and the
  reported model can be weaker; the early-stopping rule names the any-round tilt; the edge-flag rule is updated.
- `harness.py` lock: picks.json gains `inner_mae_and_n2_are_of` (whose numbers they are); the log says "tuning
  model". Not part of the picks content hash.
- `export.py`: the module text says "I5-I7 and P1-P14 always; P15 with --p15 or an accepted difference"; the lean
  comment and the R30 log line no longer say "checked by I5-I7" (that check is circular for a copied share).
- Tests: `test_aa_speedups.py` and `test_tuning_rules.py` follow the new flag; the AA4 timing test also writes a
  time-stamped evidence file. Docs: 2.10, 3.4a, 3.5, 3.6 above.
- Harness code hash: e5032ad5 -> c52babae829df106ed9abc593e52ee153a5cb05fce4588233af9471650176198. Full suite 166
  passed, 1 opt-in skipped (`pt/aafix/full1.log`); review folder 26 passed, 1 xfailed (`pt/aafix/review_aa1.log`);
  coral dry pass: picks content 2a3e224e, trials.csv and all 53 inner prediction files byte-equal to e5032ad5's.
- (Superseded by ruling AC, section 7b.) Not changed (owner items, AA_REPORT.md): the 255-bin refit stays at the 63-bin round count (ruling AA3 as
  written); a patience-stopped trial with its best in (400, 800) is still extended literally (ruling AA2), and
  repeats itself.

### 7b. Ruling AC built (2026-10-21; the owner accepted all and kept the out-of-core random forest)

- Old code, tests, the AA review tests and this spec copied first to `_moved/20261021_preAC_code/` (nothing
  deleted).
- **AC1 (bins):** `models.py` has one bin constant, `LGBM_MAX_BIN = 255`; `TUNE_MAX_BIN` (63) and `REFIT_MAX_BIN`
  are gone. `harness._run_trial` tunes with `max_bin=LGBM_MAX_BIN`; the probe uses it too. `harness.refit` at lead 0
  reuses the tuning trial's inner predictions for every learner (the AA3 second 255-bin lead-0 guard fit is
  removed) after checking the trial's `fit_info.max_bin`; leads >= 1 fit with `final_fit_options` (255 bins, the
  pinned round). picks.json `inner_mae_and_n2_are_of` is again "the tuning model, which is the reported model's
  lead-0 guard model" for every learner. board.json `rules.bins` and `tuning.max_bin` say 255.
- **AC2 (extension):** new `models.ran_to_cap(early_stopping)`; `harness.trials_to_extend` takes
  `ran_to_cap={trial_id: bool}` (a trial without a record refuses); `harness._extension_ids` builds it from each
  base trial.json of lgbm / lgbm_tweedie; hgb_l1 is unchanged ("own best at 800"). board.json `rules.extension` and
  `tuning.extension` state the AC2 rule; the tune log line names the rule per learner.
- **AC3:** the out-of-core RF is untouched.
- **Tests:** `test_aa_speedups.py` (AC1 bins and tuning = final fit at the pick; AC2 `ran_to_cap`, the rule on
  early-stopped rows, the unforced AC2 path on flow A; the lead-0 guard is the tuning trial),
  `test_tuning_rules.py::test_t7_ac2_only_a_trial_that_ran_to_the_cap_is_extended`. The AA review folder
  (`review_tests_aa`) carries a dated AC note: its 63/255 weakness test (was xfail strict) now checks the built
  rule and passes; the AA3 weakness stays as a plain record test.
- **Expected effect on coral (not yet re-run here; AC4 does it):** the lgbm and Tweedie picks will change (tuning
  at 255 bins); no coral trial reached the cap under AA, so no extension is expected.
- Harness code hash: changes from c52babae (the new hash is written into the rival Part draft by AC4).
