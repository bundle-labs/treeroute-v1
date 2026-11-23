# BUILD_NOTES_tests (builder C: tests)

Written 2026-10-20. The tests call the rival code only through `rivals/tests/toy_runs.py` (one place to fix a
signature). Most hooks below already exist in the current code (checked against it); they are listed so nobody
renames them by accident.

## Hooks the tests use

### Builder A (export.py, layout.py)
- A2 `export.export_run(run, package, leads, roles, config, resume=False)`: leads as a comma text; roles None = all;
  config a path. `export.main(argv) -> int`. Toy runs need `--package` (their manifest argv is the test's argv).
- A3 every refusal names its check id in the message (`export refused [I4]: ...`). Tests match the id.
- A5 `export_manifest.json["parity"]`: `{P1..P14: {..., "result": "pass" | "printed" | "skipped: ..."}}`.
- A6 `export.check_engine(manifest, roots, registry_dir, package_name)`, `export.parse_proof(path)`,
  `export.LINEAGE_FORMAT` (T6 drives these with a fake registry, lineage and proofs).
- `export_manifest.json["launch"]` holds the launcher record when `main` pinned threads (test_cli checks it).

### Builder B (harness.py, models.py, cli.py)
- B1 `init(run, export, out_root, extra_learners=(), config=None) -> Path` (the board folder);
  `tune(out, resume, config)`, `lock(out, config)`, `refit(out, lead, resume, config)`, `score(out, lead, config)`,
  `board(out, config)`, `open_test_labels_rivals(out, lead, config=...)`.
- B2 the harness calls `models.fit_predict` through the module attribute (T12 and T16 wrap it).
- B3 `models.fit_predict` accepts the plain mapping fit set `{X, columns, y, z0, link, c, ub, legal}` and
  score sets `{name: {X, z0, link, ...}}`; returns `{name: {checkpoint: {"pre", "pred"}}}`; `models.FitResult`.
- B4 pure rules: `harness.pick_learner`, `trials_to_extend`, `check_extension_prefix`, `pick_flags`,
  `board_learners(legal_min, zero_share, links, extra_learners)`, `apply_guard(rival_guard, comparator_guard,
  y_guard, raw_test, fallback_test) -> (guarded, passed)`; `models.rf_stride(rows, cols)`, `RF_RAM_BUDGET`,
  `rf_max_samples(n)`.
- B5 file layout read by the tests: `board.json["learners"]` (list of `{"id"}`); `picks.json["picks"]`;
  `trials/<learner>/<trial_id>/{trial.json, inner_preds.parquet}` with `pre__<ck>` / `pred__<ck>`;
  `lead_<L>/preds_<l>.parquet` (`pre__rival_<l>`, `arm__rival_<l>_raw`, `arm__rival_<l>`, `guard_passed`);
  `lead_<L>/guard_<l>.parquet` (`y`, `arm__rival_<l>`, `comparator`); `board_lead_<L>.csv` (`learner`,
  `contrast` in {guarded_vs_headline, raw_vs_raw}, `decides`, `tag`, `band`, `d_mean`, `rival_mae`, `ours_mae`);
  `test_labels_opened_rivals_lead_<L>.json["picks_sha256"]`.
- B6 `trials.csv`, every trial `inner_preds.parquet`, `board.json` and `picks.json` hold no wall-clock and no out
  path (T11 compares two boards in different out folders byte for byte).

## Defects found by the tests (to fix in the owner's file)
- **B-D1 (harness, blocks T1/T3/T9/T11/T12/T15/T16 on the table toy):** `score` refused on a V1 (neighbour, declined)
  run: `verdict adopted_column 'base__donor_median' differs from arm__<adopted> 'arm__donor_median'`. A declined
  V1 verdict has `adopted: donor_median`, `adopted_column: base__donor_median` (toy table verdict.json). The
  headline column there is `adopted_column` (or `decline_target`), not `arm__<adopted>`. Seen in run r05; FIXED in
  the code by run r10 (T15 passes).
- Note: a board refuses every later command when any `rivals/*.py` changes after its init ("the harness code
  changed since init"). A suite run while a builder edits `export.py` or `harness.py` fails T3, T16 and the export
  resume test for that reason only (run r10; the three pass on a rerun, r12).

## Spec readings and inconsistencies (owner or orchestrator decides)
- **S1 RF stride for NDVI.** SPEC 3.4 says "ndvi 4"; its own rule gives 3 (2.6 x 2,680,841 x 508 x 4 B / 4.5 GiB =
  2.93). The test pins the rule (pm25 1, fire 1, coral 1, defo 3, ndvi 3) and marks the gap. Defo is at the edge
  (2.003). Also: the stride is computed per fit set (board.json rule text), so defo tune rows (2,446,587) give s = 2
  while refit rows give 3: tuning and refit would see different unit sets. Owner: one s per problem (from the
  largest set) or per fit set?
- **S2** SPEC 3.8 writes `open_test_labels_rivals(run, lead, out)`, section 5 writes `(out, lead)`. Tests use
  section 5 (the code agrees).
- **S3** SPEC 4 says basetemp `_pt/<run>`; the task said `pt/<key>`. Tests use `pt/tests/<fresh name>` (a fresh
  name each run: pytest empties an existing basetemp, which would be a delete).
- **S4** P9 for the neighbour kind: "NaN on both sides" vs 2.4 (the neighbour normal is the donor median, so
  `nfit__identity` is not NaN). The test re-checks P9 only for the grid kinds.
- **S5** A table run's plan.json has no `history_columns` key (toy table, checked); the tests read it as [].

## Deviations in the tests
- **R1 (T1, export only):** the export may open its own `test/` files as raw bytes (hashing what it wrote, P14,
  resume); it must never decode one or read a saved test_preds with `y`. init / tune / lock may not open a
  `test/` file at all. Spec T1 says the export "never opens a test/ file"; strict reading would forbid hashing.
- **R2 (T14):** the G-NONAMES scan covers `rivals/` without `rivals/tests` (tests name paths and problems, as in
  the engine).
- **R3 (T8):** a zero residual (y = normal) stands in for "f == 0" for every learner and link; Tweedie uses
  float32-exact values (LightGBM stores labels in float32).
