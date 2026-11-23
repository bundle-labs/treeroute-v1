# The engine as it is now

Written for the public archive on 2026-11-18 and revised on 2026-11-23. This note describes the `engine/` folder as it
is archived. It is a new file and changes no other: the engine's own `engine/README.md` and its version label
'0.0.1-skeleton' are kept as they are, because the paper takes facts from them and the label sits inside the
hash-checked engine code, and the tests are the project's own (`engine/tests/STALE_TESTS.md`). Where this note and `engine/README.md` differ, this note describes the archived code.

## What the engine is

- `engine/treeroute/` is treeroute v1, the forecasting engine of the paper, in its reference version 930d961c. Its
  code hash is `930d961cdfdd219c36b113174e6c865096f973068e30696850f13d5ec4a60814`: the SHA-256 of the canonical
  JSON of the sorted list of [path, file SHA-256] pairs over its 94 Python files, as `engine_code_sha256` in
  `engine/treeroute/runs/fingerprint.py` forms it. The other 15 Python files, in `engine/treeroute/_proposed/`,
  hold function signatures; the engine never runs them, and the hash leaves them out.
- The paper's five headline runs were made with this code, in three versions: 930d961c made the coral bleaching
  run, 7b508557 the PM2.5 run, and 65a177bc the NDVI, burned-fraction and forest-loss runs. `VERSIONS.md` gives
  each version's folder in the archive, its full hash and how it is rebuilt. Small check runs gave byte-identical
  outputs across the versions (fact M1 of the paper's fact sheet, `records/fact_sheet/PAPER_FACTS.md`).
- The run locks record the version as `engine_code_sha256`. The run manifests record instead a hash of the
  comment-stripped code, `engine_code_hash` (85c64b55 for 930d961c). `HASH_REGISTER.md` says where each hash is
  recorded.
- The project kept no version control, so a version is named by its code hash, not by a commit or by its label.
- Beside the code, `engine/` holds the report tooling (`treeroute_report/`, version 1658e0dd), the tests
  (`tests/`), the five dataset packages with their drafts, the shared store catalogs, the signing tools and the
  review evidence (`datasets/`), the headline runner (`runner/run_headline.py`) and the machine file
  (`config/machine.yaml`). Its top-level documents are the author's rulings (`OWNER_RULINGS_*.md`), the project
  log (`PENDING_PARTS.md`, which the paper cites as "Part N"), the protocol drafts (`PREREGISTRATION_DRAFT*.md`)
  and the plans and reports of the build. The licence file `engine/LICENSE` (MIT) was added for the archive,
  outside the code hash.

## What is out of date, and why it stays

- **The version label.** `engine/treeroute/__init__.py` sets `__version__ = "0.0.1-skeleton"`, and every run
  manifest records it as `engine_version`. That file is one of the 94 that the code hash covers: a new label would
  give a new code hash, and the archived engine would no longer be the version that the locks and the run records
  name. So the label stays; the code hash, not the label, names the version.
- **The engine's docstring and command-line help.** The docstring of `engine/treeroute/__init__.py` still calls
  treeroute a placeholder name and says that no science module exists yet, and the help text in
  `engine/treeroute/cli.py` also calls the name a placeholder. Both files are inside the code hash, so both texts
  stay. The name treeroute is kept for v1.
- **`engine/README.md`.** It is the README of the engine's first stage, the boilerplate skeleton. It says that no
  science module exists yet, that about 1,030 tests run in about 15 seconds and that most commands are stubs, and
  it lists choices that were still open at that stage. The archived engine has its science modules (`check/`,
  `derive/`, `fit/`, `io/`, `labels/`, `layer/`, `pipeline/`, `report/`, `route/`, `timing/` and `split.py`);
  its commands `check`, `plan`, `smoke`, `run`, `report` and `status` are built (`resume` is not: `run` and
  `smoke` resume an unfinished run themselves); and its test suite is far larger than the README says (next point).
  The README lies outside the code hash, but the paper takes facts from it, so it stays as
  it was.
- **33 out-of-date tests.** The recorded full run of the test suite on 930d961c gave 3,500 passed, 33 failed and
  62 expected failures. The 33 failures are stale package and draft tests; `engine/tests/STALE_TESTS.md` lists each
  one with the reason that the run gives, and what has changed since. The fact sheet records that none of this
  changes a reported number (fact M2). The archived tests are the project's own: one test file was brought up to
  date after the recorded run, and the archive's text changes to the tests (`CHANGES_FOR_ARCHIVE.md`) touch only
  docstrings and one comment.

## Where to start

- `README.md` at the archive root: what each folder holds, the code versions and their hashes, the Python and
  library versions that the runs used, and what is kept out.
- `REBUILD.md` at the archive root: what the archive can and cannot rebuild, the rebuild scripts, the order of the
  coral bleaching chain and how to re-draw the figures. The archive alone does not re-run the routing: it holds
  none of the engine's fitted trees and no per-location values of the tree inputs.
- Then `VERSIONS.md` and `HASH_REGISTER.md` for the versions and their hashes, and `engine/tests/STALE_TESTS.md` for
  the tests.
