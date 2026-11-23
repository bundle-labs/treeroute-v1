# BUILD_NOTES_harness (builder B: rivals/harness.py, rivals/models.py, rivals/cli.py, rivals/__init__.py, rivals.yaml)

Plain notes for builders A (export) and C (tests), and items for the owner.

## Interfaces as built

- `harness.init(run, export_lead0, out_root, extra_learners=(), config=None) -> board folder` (<out_root>/<package>/<run name>).
- `harness.tune(out, resume=False, config=None, hook=None)`, `lock(out, config=None)`, `refit(out, lead, resume=False, config=None)`,
  `score(out, lead, config=None)`, `board(out, config=None)`, `probe(out, lead=0, config=None)`.
- `harness.open_test_labels_rivals(out, lead, config=None)`: the ONE reader of test y. Refuses first (lock, picks sha,
  every learner's preds_<learner>.parquet + done_<learner>.json), then reads, then writes
  `test_labels_opened_rivals_lead_<L>.json` (top-level fields of the latest opening incl. `picks_sha256`, plus `history`).
- Pure hooks: `pick_learner(rows)`, `trials_to_extend(rows, pick)`, `own_best(rows, trial_id, max_checkpoint)`,
  `check_extension_prefix(base, ext, trial_id="")`, `pick_flags(learner, pick)`,
  `board_learners(legal_min, zero_share, links, extra_learners=())`, `apply_guard(guard_pred, comparator, y, raw, fallback)`.
  A row = {trial_id, link_order, grid_order, checkpoint, inner_mae}.
- `models.fit_predict(learner, params, fit_set, score_sets, checkpoints, cache=None) -> FitResult`:
  a dict {score name: {checkpoint: {"pre", "pred" (only when a legal range is given)}}} with `.model` and `.info`.
  fit_set: `models.FitData` or the mapping {X, columns, y, z0, link, c, ub, legal}; score_sets: list of `ScoreData`
  or {name: {X, z0, link}}. Also `models.rf_stride`, `RF_RAM_BUDGET`, `rf_max_samples`, `grid`, `checkpoints`.
- The harness calls `M.fit_predict` through the module (wrappable).

## For builder A (export)

- A1. The harness reads only: the folder layout and names of rivals/layout.py; the column prefixes x__/c__/h__/nfit__/ngd__;
  the five flag columns; `units.parquet` (unit, group, report stratum columns, seen_during_design); the export manifest
  bytes (sha256), and from the manifest only: the run fingerprint anywhere in it (identity), and `zero_share_refit_y`
  (used ONLY when the export holds no refit row, i.e. the dry pass). Everything else comes from the run folder.
- A2. Group names come from the `group` column, never from file stems (stems are %XX-encoded).
- A3. Test files: the harness puts its predictions in the run's SAVED test row order by key join on (unit, time, lead) and
  refuses a missing or extra key; `saved_row` is not used.

## For builder C (tests)

- C1. T8 Tweedie (`test_t8_tweedie_with_a_zero_raw_score_returns_max_of_normal_and_c`) cannot pass at rtol 1e-9:
  LightGBM stores labels as float32 (label_t), so y = max(normal, c) enters as float32 and the boosted raw score
  converges to log(y32 / y64), about 1e-8 relative. Seen on the toy: about 7e-9 relative. Suggest rtol 1e-6.
  For plain lgbm the harness feeds the residual label link(y) - z0 with a zero init_score (same squared-error fit as label
  link(y) with init_score z0, see models._fit_lgbm), so T8 is exact there.
- C2. T12 failed once in the combined run with "lead_0 has no export_manifest.json": another test in the same session
  re-exported (or moved aside) the shared toy export folder. Run alone, T11, T12, T15, T16 pass. The toy export should not
  be rewritten by T13 or the export-refusal tests while flows read it (or flows should use their own export copy).
- C3. RF stride: I followed the spec's formula with RF_RAM_BUDGET = 4.5 GiB (your test). See owner item O-1.

## Items for the owner

- O-1 RF stride budget. Spec 3.4 says 4.5 GiB and states strides pm25 1, fire 1, coral 1, ndvi 4, defo 3. With 4.5 GiB the
  formula gives ndvi 3 (2.93); ndvi 4 needs 4.5e9 decimal bytes. Built: 4.5 GiB (formula). Owner picks.
- O-2 RF stride per fit set. The stride is computed from each RF fit set's own size (tune, guard-fit, refit). On ndvi this
  can give a different s for tuning than for the refit. Alternative: one s per board from the lead-0 refit size.
- O-3 lgbm offset. Built as residual label (link(y) - normal) with a zero init_score instead of label link(y) with
  init_score = normal: the same fit, but exact where the spec's form loses float32 precision. Tweedie keeps label y and
  init_score log(max(identity normal, c)).
- O-4 One binned LightGBM Dataset per (fit set, link), not per fit set: the normal column differs per link (spec 3.3 puts
  the trial's link normal in X), so one Dataset cannot serve every link. Settings reuse it (set_label / set_init_score).
  Tweedie reuses the identity Dataset (its column is the identity normal).
- O-5 Materialized memmap: one float32 memmap per fit set holds the RAW x__/c__ block (history columns already at the
  right cut); the 0-fill (trees), the mean + flags (ridge) and the normal column are applied per block when read.
- O-6 Watchdog reads process-tree RSS (spec). On Windows the memmap's resident file pages count toward RSS, so a
  large fit set can look bigger than its private memory.
- O-7 Declined nowcast: "ours" = the decline target; "our pinned arm raw" = arm__<verdict.best_tree_arm>.
- O-8 The board refuses any later command if the harness code, library versions, thread pools or config roots differ
  from board.json (init a new board after any code change).
