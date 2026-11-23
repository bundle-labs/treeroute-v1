"""treeroute.pipeline: the one pipeline of plan 4.1, wired end to end: the nowcast and the forecast ladder.

Modules (orchestration and boilerplate; every rule is its approved module's):
  - draft.py   the DRAFT stamp of a development package (never a headline number)
  - data.py    the package's code hooks (target reader, feature script), the target table, the static
               table, the driver stores and the column reader derive_all calls
  - stages.py  the vault on the dense grid, the feature pool and the history block, R36 tolerances,
               normals and the router rows
  - router.py  the router-kind dispatch of one pass (R12): per-unit (route.kinds, with the GLS-weighted
               solve and route/region.py's fallback for short-history units) or region (route/region.py)
  - passes.py  the fits, the tree-answer tables, the decision surface and its lock, the test pass, the
               metrics and the report files
  - ladder.py  the forecast ladder (plan 4.1 step 11; leads 6 and 12 months, owner ruling I1): the lead-0
               contract, per lead the moved features, lagtrain, the guard-cut bank and the guard with its
               own fallback level (H2, H5) and its lock, persistence, the test pass (H4's left-out rows
               saved flagged); the ladder table
  - record.py  run records, the run log and the headline-table builder (refuses DRAFT, smoke, legacy)
  - run.py     Pipeline: phases, the run folder, the fingerprint, resume and the heartbeat;
               run_pipeline / plan_pipeline / report_runs, which the CLI calls

Importing this package imports nothing heavy (G-IMPORT): the modules are imported inside the CLI
commands, after the launcher has pinned the thread pools.
"""
