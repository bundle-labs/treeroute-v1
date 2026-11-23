"""treeroute.check: the validators (plan Section 5) and the 'check' command's two passes.

  guards.py     SCIENCE bodies for the owner-approved signatures of treeroute/_proposed/validators.py
                (owner ruling A accepted every proposed default, D1-D101; the rulings files win where a
                docstring differs). Every validator returns a GuardResult (layer/decide.py's shape).
  recompute.py  the body of the approved io_science signature recompute_declared_operation (the
                reference G-DERIVED compares the feature script against). It lives here because io/ is
                outside this build's write scope; the owner may move it into io/.
  facts.py      boilerplate: the merged facts of a loaded package (package catalog + store catalogs +
                the feature script's declared outputs), read by attribute.
  quick.py      'check': the quick checks on package facts and verdicts (seconds; it reads file
                listings, parquet footers and ONE target file for R1, never the data pass).
  deep.py       'check --deep': the data checks, streamed file by file (bounded RAM, one pass over each
                store), the windows (R3-R11: the engine's own rules on the joined rows, never an
                estimate), then the sample pass (G-DERIVED recompute, G-HIST sample match, G-CALENDAR on
                the predecessor lookup, the G-LINEAGE reconstruction test).
  report.py     the CHECK REPORT CONTRACT json (check_<quick|deep>_<package fingerprint 12 hex>.json).

Importing this package loads nothing heavy; the modules import numpy and pandas when they are imported.
"""
