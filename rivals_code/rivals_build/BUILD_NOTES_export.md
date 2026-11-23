# BUILD_NOTES_export (builder A: rivals/export.py, rivals/layout.py, engine_lineage.json)

Written 2026-10-20. Status: built and checked on toy and smoke-size data. No full-size export was run.

## 1. Interfaces (fixed)

- `export.main(argv) -> int`. argv may start with `export`. `--run --lead` (export) or `--write-lineage [--proof F ...]`.
  Returns 0, or 2 on a refusal (ours or the engine's), message on stderr. Its first act is `treeroute.launch.pin_threads()`.
- `export.export_run(run, package=None, leads="all", roles=None, config=None, resume=False, machine=None, echo=None,
  launch_record=None) -> list[Path]` (the lead folders). leads: `all`, `L` or `L1,L2`. roles: None (all), a list or a
  comma text. config: rivals.yaml path, a mapping, or `layout.Roots`. machine: an engine machine object (tests); else
  rivals.yaml's `machine_file`.
- `export.write_lineage(roots, proofs)`, `export.check_engine(manifest, roots, registry_dir, package_name)`,
  `export.parse_proof(path)`, `export.LINEAGE_FORMAT`, `export.ExportRefusal(check, message)` (`.check` = I1..I9, P1..P14,
  2.6, 2.7, ARGS, RESUME, ROWS).
- `layout.py`: roots (`load_roots`, `as_roots`, `Roots`, `lineage_file`, `import_engine`), every folder/file/column name
  of SPEC 1.2 and 1.3, and the file helpers (`atomic_write_bytes`, `write_json_atomic`, `move_aside`, `sha256_file`,
  `code_sha`, `assert_writable`). It imports no numeric library.

## 2. The export files (what the harness reads)

- `train/<group>.parquet`: keys `unit, group, time, issue, lead`; flags `r_refit r_tune r_inner r_guardfit r_guard`;
  `y` (float64); `nfit__<link>` (float64, FIT-cut normal, link space); `x__<tree col>` (float32 raw, NaN kept);
  `c__<context col>` (float32 raw). Rows = the union of the WRITTEN roles' rows, grid order.
  With `--roles` a subset, the flags still mark membership of every role (a tune row that is also a refit row has
  `r_refit` True) but only the written roles' rows are present.
- `guardside/<group>.parquet`: the train rows flagged with a written guardside role (lead 0: tune, inner; lead L:
  guardfit, guard), same order; keys, `h__<history col>` (history block at the guard cut), `ngd__<link>`.
- `test/<group>.parquet`: keys, `saved_row` (int64: the row's index in the run's saved test_preds of that lead),
  `nfit__<link>`, `x__`, `c__`. No `y`.
- `units.parquet`: `unit, group, is_scored, seen_during_design`, then each report stratum column.
- `export_manifest.json` (written last): `format, export_key, run, package, engine, derived_sha256, router_kind, lead,
  roles, links, c, ub, legal_range ([min, max]; null = infinite), legal_range_text, cuts {fit_cut, guard_cut,
  inner_fit_end_step}, season {kind, steps_per_year}, columns {tree, history, context, x, c, h, nfit, ngd}, counts,
  row_key_hashes, records (normals, G1, S1/H4 counts), parity {P1..P14: {..., result}}, identity {I1..I9},
  zero_share_refit_y (THIS lead's refit rows; the Tweedie rule reads lead 0's), legal_min, groups,
  seen_during_design_groups, strata_columns, files [{path, sha256, rows, part, group}], export_code_sha256, launch,
  timings_seconds, peak_rss_bytes`.
- Neighbour kind (tables): `nfit__`/`ngd__` are ONE donor-row median per cut in each link (reading R-CN).

## 3. Requests to builder B (harness, cli, rivals.yaml)

- B-A1: `rivals/cli.py` and `rivals/__init__.py` must not import numpy, pandas, sklearn or pyarrow before dispatching
  `export` to `export.main(argv)`: `pin_threads()` refuses once numpy is loaded. (Setting the OMP/MKL/... env vars
  first is fine: the launcher overwrites its own six pins.)
- B-A2: optional rivals.yaml keys read by the export: `engine_lineage` (path; default `engine_lineage.json` beside the
  config file, i.e. `D:/treeroute/rivals_build/engine_lineage.json` for the build config) and `lineage_proofs` (list of
  no-op proof files for `--write-lineage`). `layout.roots_from_mapping` keeps unknown keys in `Roots.extra`.
- B-A3: the guard-cut rows (tune, inner, guardfit, guard) take `h__*` in place of the matching `x__` history columns
  and `ngd__<link>` as their normal; refit and test rows take `x__` and `nfit__<link>` (SPEC 3.3).

## 4. Requests to builder C (tests)

- C-A1: every P1..P14 is recorded at every lead. A check of the other kind of lead is recorded as its twin, e.g. at
  lead 0 `P3 = {"result": "pass (as P2: at lead 0 the guard-cut fit set is checked as P2)", "same_as": "P2"}`
  (pairs P2/P3, P4/P5, P10/P11). A dry pass records `P6`, `P9` as `skipped: dry pass (no test role)`; P13 is
  `skipped: ...` only when the roles write no fit set.
- C-A2: `test_realdata.py` exports into the shared `_export` with resume False. A second run then refuses
  `[RESUME]` (by design: a filled lead folder needs `--resume`). Use a fresh export root per run or `resume=True`.
- C-A3: the export reads saved test_preds with `pyarrow.parquet.ParquetFile(path).read(columns=[...])`
  (`pq.read_table` goes through `pyarrow.dataset` with no column list, which the read spy counts as every column).

## 5. Deviations from SPEC_RIVALS.md (each small; owner may rule)

- D1: the engine host folder is one per run export, `<export_root>/<package>/<run>/_engine_folder` (spec: per lead).
  The engine's status.json goes there; each lead folder has its own `status.json` and `export.log`.
- D2: for a smoke run the export calls `pipe._smoke_bank_plans(pipe._vault(None))` before I5-I7, as `Pipeline.run`
  does (pipeline/run.py:1375-1376); without it a smoke run's derived.json (R19:smoke entries) fails I7.
- D3: `--package` default = the LAST argv item that is a package folder (holds dataset.yaml), not the last argv item
  (the smoke runs' argv ends with `--run-root <folder>`).
- D4: test files carry `saved_row` (the spec's "the export records the saved row order").
- D5: P9 for the neighbour kind also checks the refit-row median, clipped, against the saved `base__donor_median`
  byte for byte (a prediction column of test_preds; y is never read).
- D6: a grid export without lead 0 sets the attributes `RunState.build_pool` sets (passes.py:372-389) without
  building the nowcast pool (one lead pool at a time, SPEC 2.9). Checked: `--lead 12` alone and `--lead 0` alone give
  files byte-identical to `--lead all`.
- D7: the export refuses when A7.inner_cut_bank_refit is off (L6 a); it is built for L6 b (H2) only.
- D8: the test row KEYS are built even in a dry pass (unit_positions and S1 on context; no label, no test_preds read).
- D9: table packages: each store file's sha256 is re-checked before the read (manifest config data files).
- D10: on `--resume`, a finished file whose rebuilt bytes differ refuses (P14), never silently rewritten.
- D11: I4's proof lines are matched on the `=== COMPARE <package> :` section name exactly (a package name inside
  another name does not count).

## 6. What was run (all writes under rivals_build)

- Toy grid (engine make_pipeline_package: ok, sparse, the G1 package), toy table (ok, donor_only_group): every lead,
  I1-I9 and P1-P14 pass; resume skips every file; refusals I1-I7, P1, P4, P6, P9, P12, RESUME fire on mutated copies
  (pt/export/drive_*.py).
- Builder C's tests: test_lineage.py, test_nonames.py, test_export_parity.py, the two T1 export tests: pass.
- Real, smoke-size: defo smoke 20261020_192b4285 (region kind; leads 0, 1; inner 480, test 640 per lead; peak 0.48 GiB);
  fire smoke 20261020_ee5cd20a (per-unit with context; leads 0, 6, 12; peak 1.6 GiB): all pass.
  Coral headline 20261020_f3b8e3da lead 0, roles tune,inner (no test file, no test label): all pass, P6/P9 skipped.
  Outputs under pt/export/real_export (config pt/export/real_cfg.yaml), not the shared _export.
- engine_lineage.json written from D:/treeroute/coral_build/noop/noop_summary.txt and
  D:/treeroute/coral_build_v6b/noop/noop_summary.txt. I4 on the five headline manifests: ndvi, fire, defo pass
  (65a177bc -> dd7c0984 -> 930d961c); coral is LIVE; pm25 REFUSES (section 7).

## 7. Open items for the owner

- O-A1 pm25 cannot be exported as built: (a) I4: no parsable proof hop 7b508557 -> 1f257395 -> 7a0341ef -> 65a177bc
  (install_20261015/smokes/compare_pm25.txt has no LIVE/BUILD sha lines; s_20261016/smokes/compare_pm25_*.txt show
  MUST-MATCH (1): per_group_schedule.json); (b) even with a hop, I5 refuses: the run config's
  engine_constants_sha256 differs from LIVE's 3ef147e5 (the constants table gained P7.room_* and
  P7.reader_batch_rows since). Options: a pm25 re-run under LIVE, or a ruling that accepts these differences.
- O-A2 NDVI's headline has G1 / S1 left-out rows (decision 1760, test 2136). The trimmed-normal path is checked only on
  the engine's G1 toy (lead 12: 96 rows left out, P9 byte equal, P11 within tolerance); P9/P10/P11 will check it at
  full size.
- O-A3 full-size exports (fire 8.3 GiB derive, ndvi 6.1 GiB) are owner commands (O1), one lead at a time on NDVI.
