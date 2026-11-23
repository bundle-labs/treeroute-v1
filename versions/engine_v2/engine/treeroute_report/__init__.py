"""treeroute_report: paper tooling OUTSIDE the engine hash (plan 7.1, 7.2, 8.0, 8.1 M5 and M7).

It may name problems (the engine may not, G-NONAMES). It never changes a fit, a pick or a decision:
it reads finished runs, packages and check reports, and writes its own files only.

  freeze.py  the freeze lock (plan 8.0 'Sat 10 Oct freeze: checks green, lock file'; 8.1 M5) and its
             'verify' subcommand (the M5 no-op rule: after the freeze only bug fixes)
  table.py   the headline tables, built from SAVED row-level predictions of finished headline runs
  common.py  shared helpers (hashes, the protected-root check, the engine code listing)

continuity_groups.yaml holds the old hard-split test groups (owner rulings E, L7 b); history_bands.yaml
holds the old bands printed beside a package's derived band as history (R35, Q22 b).
"""

__version__ = "0.1.0"
