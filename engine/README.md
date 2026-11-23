# treeroute engine: boilerplate skeleton

`treeroute` is a placeholder name. The plan is `../APP_PLAN.md`. This folder holds only the
**boilerplate skeleton** from plan 4.2. No science module exists yet. The science modules are
derive/, timing/, io/ transforms, check/ validators, split.py, labels/, fit/, route/, layer/ and
report/metrics.py. Each waits for an owner-approved signature.

## Run the tests

From this folder (`engine/`):

```
py -3.9 -m pytest
```

About 1,030 tests run in roughly 15 seconds. pytest's temporary files go to `tests/_pytest_tmp/`,
and pytest clears that folder at the start of each run. Nothing is written outside `engine/`.
Nothing is written to D:, either. A few tests read the real shipped registry (read-only) and are
skipped on a machine that does not have it.

## Run the command line

```
py -3.9 -m treeroute --help
py -3.9 -m treeroute check  <package folder>
py -3.9 -m treeroute status <package folder> [--run-root <folder>]
```

Every command takes only a package path and `--run-root`. The allow-list is tested; any other flag
is a usage error.

| Exit code | Meaning |
|---|---|
| 0 | done |
| 2 | usage error (unknown flag, missing argument) |
| 3 | not built yet (stub), or built only in part (`check`) |
| 4 | refused by a guard or closed door (for example, a run root under a shipped folder) |
| 5 | the package failed to load (closed folder, schema, include hash) |

## What exists

| Path | What it does | State |
|---|---|---|
| `treeroute/__init__.py` | Package marker. Importing it has no side effects. | done |
| `treeroute/__main__.py`, `treeroute/launch.py` | Entry point. It pins BLAS/OpenMP to 4 threads BEFORE numpy loads, overwriting shell values. It refuses to start if numpy was already imported, or if any other variable the numeric libraries read is set (`OPENBLAS_*`, `OMP_*`, `KMP_*`, `MKL_*`, `SKLEARN*`, `TBB_*`, `PYTHONHASHSEED`, ...). It imports sklearnex (required) and pins oneDAL to 4 threads. It applies and verifies threadpoolctl limits on every loaded pool. It keeps a launch record for the manifest, then runs the CLI. | done |
| `treeroute/engine_constants.py` | 92 constants: every plan 3.1 constant (C1-C15) plus the A7 design flag. Each has an id, a value, a test-exposed flag and a status. Origins are in comments only. Numbers that the Section 1/2/5 rules name but 3.1 omits are marked `extra`. The one unset constant (`C9.guard_tolerance_k`) raises on any use, comparisons and hashing included. | done; owner reviews once |
| `treeroute/cli.py` | Typer commands `check`, `plan`, `smoke`, `run`, `report`, `status`, `resume`. | `check` loads and fingerprints the package, then says the guards are not built (exit 3). `status` works. The rest are stubs, but each one checks the run root against the registry first. |
| `treeroute/errors.py` | Exception types. Every refusal names its rule and the fix. | done |
| `treeroute/runs/atomic.py` | Atomic JSON writes: temp file, fsync, rename. `write_json_once` never overwrites. `replace_json` is only for the heartbeat. NaN is refused. Canonical JSON for hashing. Temp names carry pid + process start time + a counter, so a stale temp file of a dead process never blocks a write. A rename that Windows refuses because another process holds the file (a reader of status.json, an indexer, antivirus) is retried 20 x 50 ms, then fails loudly naming the file. | done |
| `treeroute/runs/fingerprint.py` | Hashes every engine `.py` file with comments stripped, in sorted order (excluding `_proposed/`). The run fingerprint = SHA-256 of the resolved config + engine code + library versions (tbb included) + Python. The manifest refuses while any `treeroute._proposed` module is loaded. | done |
| `treeroute/runs/manifest.py` | Builds and writes `manifest.json` once. Fields whose producer is not built yet are null and listed under `not_built_yet`. | done |
| `treeroute/runs/registry.py` | Refuses any path under a root in `protected_roots.txt` or `shipped.json` (by spelling, and by volume + file index of every existing ancestor), any listed shipped file, anything inside the registry folder except `index.csv` / `bands.csv` (so the `backup_*` folders are protected), UNC / admin-share / device paths, and existing files with more than one hard link. Spellings are resolved first: the `\\?\` prefix, `..`, trailing dots and spaces, symlinks and letter case. It returns the resolved path, and `open_run` creates exactly that path. A missing registry refuses everything. | done |
| `treeroute/runs/resume.py` | Run folders `<root>/<package>/<headline or smoke>/<yyyymmdd>_<fp8>/`, found again by fingerprint. Same fingerprint and unfinished: resume. Finished: refuse. Phase `DONE` markers carry the fingerprint; a different one stops the run. | done |
| `treeroute/runs/preflight.py` | Disk and RAM decide go or refuse only, and the refusal says "free X GB". Orphan temp files from dead processes are refused, never deleted. One heavy job per machine (lock file; a stale lock is refused, not removed). | done |
| `treeroute/runs/status.py` | `status.json` heartbeat. The reader tells a live writer from a dead one (pid + start time). A beat waits (bounded) for a reader holding the file instead of crashing the run. | done |
| `treeroute/runs/tempmem.py` | Windows-safe temp memmap. It creates a NEW file, writes and reads row blocks, then drops its reference, runs gc, checks that no alias survives, and deletes. Any failure raises and names the file. | done |
| `treeroute/runs/proc.py`, `runs/machine.py` | Process identity (pid + start time); machine-file loader. | done |
| `treeroute/package/schema.py` | Pydantic 2 models (`extra='forbid'`, frozen) for dataset.yaml, store catalogs, catalog.yaml, ban.yaml, split.yaml, exceptions.yaml and machine.yaml. Also holds the reserved table columns and the JSON Schema export. Numbers are strict: a string, a boolean, or a float in an integer field is refused; ranges must be ordered. G-NOKNOB: an undeclared key that names a derived setting is refused with "derived: see derived.json, rule Rn" (every plan 1.7 knob included); `donors` / `tests` / `from` point to the split.yaml sets. | done; owner reviews which fields are required |
| `treeroute/package/load.py` | YAML loader. It refuses duplicate keys, keeps dates as strings, treats only `true`/`false` as booleans, and reads only plain decimal numbers (`010`, `0x1F`, `12:30`, `1_000` stay strings). Closed package folder; `AUDIT_CHECKLIST.md` is required (plan 1.1). Include hashes are verified. Package fingerprint. | done |
| `config/machine.yaml` | Paths only: run root, temp dir, registry dir. It sits outside the engine hash and the G-NONAMES scan. | done; owner confirms the temp dir |

## Tests

| File | Checks |
|---|---|
| `test_cli_allowlist.py` | Every command's parameters are only `package` and `--run-root`, with no environment variables. Old knobs are usage errors. Stubs exit 3. A protected run root exits 4. `python -m treeroute` runs through the launcher. |
| `test_nonames.py` (+ `nonames_scan.py`) | G-NONAMES over `treeroute/`: no dataset name, 4-digit year, drive letter (also a lone `'D:'`), unit name or month arithmetic with 12 (`% 12`, `* 12.0`, `12 / x`, `divmod(x, 12)`, `np.mod(x, 12)`) in identifiers, strings or numbers (comments are exempt). The scanner is proven on planted faults. |
| `test_import.py` | G-IMPORT, in a fresh interpreter with the legacy scripts importable. Importing the engine loads no legacy or dataset module and no `treeroute._proposed` module, touches no argv (spied) and changes no environment variable. The entry modules do not load numpy. A static scan refuses any engine import of `_proposed` (absolute, relative or through `import_module`). |
| `test_noknob.py` | Only `launch.py` touches the environment. The machine file holds absolute paths only and refuses a thread count. |
| `test_registry.py` | Refusal under protected roots (sub-paths, `..`, case, `\\?\` and `\\.\` prefixes, UNC and admin shares, trailing dots and spaces, a junction that path resolution misses, json-only roots, shipped files, the registry folder and its backups, hard-linked files). `open_run` creates exactly the checked path. A missing registry refuses everything. Read-only checks of the real registry, backups included. |
| `test_atomic_resume.py` | Write-once, replace, NaN refusal, interrupted writes, temp names, a stale same-pid temp file, a reader holding the file (waited for, or a loud failure). New / resume / finished-refused run folders. Collision refusal. Phase markers keyed by fingerprint. |
| `test_schema.py`, `test_load.py` | Unknown keys, every derived-setting key in every file, every plan 1.7 knob spelling, misplaced facts, shapes, strict numbers, ordered ranges. Closed folder, required audit checklist, include hashes, fingerprint scope, duplicate YAML keys, YAML number forms. |
| `test_tempmem.py` | Normal delete, a leaked alias fails loudly, a body exception still deletes, a delete failure is not swallowed, no overwrite. |
| `test_launch.py` | Pins applied and recorded; importing numpy first is refused; foreign numeric environment variables are refused; missing sklearnex fails loudly; tbb is versioned. |
| `test_constants.py`, `test_preflight_status.py`, `test_fingerprint_manifest.py` | Constants registry; go/refuse; orphans; lock; heartbeat; comment-stripped hashes; manifest fields. |

## Choices the owner should check

1. **How sklearnex is made active (changes numbers; decide before fit/).** G-THREADS says
   "sklearnex verified active". Today the launcher imports sklearnex and pins oneDAL to 4 threads,
   but does NOT patch sklearn (`sklearn_patched: false` in the launch record). The shipped runs
   patched globally (fire_architecture.py:66-68, imported by pm25_adaptation.py:191;
   coral_architecture.py:60-61), so coral's GLS forest (R25's source) ran on oneDAL, and oneDAL does
   not equal stock sklearn at the same seed. Options: (a) the launcher calls `patch_sklearn()` after
   the pins and asserts `sklearn_is_patched()` (G-IMPORT still holds: it happens at launch, not at
   import); (b) fit/ uses explicit `sklearnex` estimators, checked by a signature test. The choice
   goes into the launch record and the manifest.
2. **Region penalty levels** (`C12.region_penalty_levels`). The plan says "7 levels 0.1-100x around
   λ 100", but no shipped 7-value region list exists (adaptation.py:153 swept 15 levels,
   defo_softgate.py:75 six). The per-unit list (0.1, 0.3, 1, 3, 10, 30, 100) is reused.
3. **`C9.guard_tolerance_k` is UNSET.** It needs the measurement that keeps the identity gate at
   1e-6 (U-4). Any use raises.
4. **`extra` constants (15).** Numbers named in plan Sections 1, 2 and 5 but missing from the 3.1
   table: history block (3 values; 1- and 5-year windows), c quantile 0.01, R22's "more than 2"
   distinct values, R31's last-5-years normal, hit tolerance 0.5 x mean deviation, detection
   (10% / 10 events / 50%), jackknife 1.96, sentinels (1e30, 2^30), G-CADENCE's 0.1% constancy
   tolerance, G-SUPPORT's "at least 2" distinct values, and plan 1.2's 4-decimal lat/lon unit id.
   Keep them or move them. The neighbour centres 0.5 / 0.25 now have their own ids
   (`C12.neighbour_*_centre`), flagged test-exposed because plan 7.2 lists them.
5. **`check --deep`** (plan 6.1) conflicts with the 1.7 allow-list (package + `--run-root` only).
   It is not built. Either allow `--deep` as a run-control flag or make a separate command.
6. **Schema required fields and files.** Required now: dataset `stores.target` and `stores.static`,
   and a verdict's `evidence` (except `keep_unreviewed`). Every `key_time` column needs a
   `calendar_part`. `includes` lives in dataset.yaml only, although plan 1.2 mentions includes for
   catalog.yaml too. `co_measured_with_target` is a bool, with its Part number in
   `co_measured_evidence`. `AUDIT_CHECKLIST.md` is now REQUIRED (plan 1.1 marks only features/,
   type3/ and tables/ optional); only its presence is checked, and its signatures wait for a
   validator. `expected_derived.json` stays optional. Window lengths and the measurement error
   floor must be finite; fill values may be any number.
7. **Package fingerprint scope.** It excludes `data/` (a data manifest is a later item) and
   `expected_derived.json` (tests only, "never read by a run"). It includes everything else,
   `tables/*.parquet` and `AUDIT_CHECKLIST.md` included.
8. **Machine file.** `temp_dir: D:/treeroute/tmp` is a proposal; the plan names no temp dir.
   `registry_dir` was added (paths only) so that engine code never names a drive.
9. **Environment door.** The launcher refuses to start while any `OPENBLAS_*`, `GOTO*`, `OMP_*`,
   `KMP_*`, `MKL_*`, `BLIS_*`, `NUMEXPR_*`, `VECLIB_*`, `SKLEARN*`, `SCIPY_*`, `NPY_*`, `DAAL*`,
   `ONEDAL*`, `TBB_*` or `PYTHONHASHSEED` variable is set (other than its own six pins). None is set
   on this machine. If one must be allowed, it has to be recorded and fingerprinted instead.
10. **Registry folder.** Everything under `registry_dir` is protected except `index.csv` and
    `bands.csv` (plan 7.1). UNC and admin-share paths are refused as output locations outright.
11. **G-NONAMES name list** lives in `tests/nonames_scan.py`, plus any package under `datasets/`
    with a `dataset.yaml`. `_proposed/` is not scanned until its code moves into the engine.

## Known limits

- Router workers "8 at once with BLAS at 1 thread each" are recorded constants only. OpenBLAS's
  thread count is process-wide, so route/solve.py will need to set BLAS to 1 around the parallel
  router phase and back to 4 afterwards.
- pyarrow's own thread pool is not pinned. It cannot change a number.
- Manifest fields for the feature list, unit lists, table schedule and lock file are null until
  their producers exist.
- A free-text field (for example an exception's `decision`) could still carry a number in prose.
  The schema blocks keys, not prose.
- Registry identity checks compare the volume serial and file index of existing folders only; a
  protected root that does not exist yet is protected by spelling alone.
- The heartbeat waits about 1 s for a reader that holds status.json. A reader that holds it longer
  (an editor keeping it open) makes the beat fail loudly; the run is then resumed.
- The engine does not write `index.csv` / `bands.csv` yet; when it does, their temp files will need
  the same registry carve-out.
