"""treeroute.fit: the bank (R19), its correctors and placebo correctors, and the out-of-core pool
(plan 4.2, fit/ row).

What exists:
  - bank.py        the three NAME seeds (D47), bag size and bag draw, the fit-one-tree PRIMITIVE,
                   the out-of-bag rows, the expected held-out share and its check (D50, D51), the
                   whole-bank recipe (fit_donor_bank) and per-tree group ownership, so a unit's
                   router can drop its own group's trees (owner rulings, part D: leave one group
                   out; columns_without_own_group refuses a group that owns no tree). SCIENCE:
                   owner-approved signatures, agent bodies.
  - correctors.py  the fit-one-corrector PRIMITIVE, the out-of-bag corrector and the placebo
                   corrector (scrambled residual, same seed). SCIENCE: approved signatures.
  - pool.py        the out-of-core feature pool on dense-grid rows: row-block writes, a sorted
                   gather, and the Windows-safe memmap lifecycle of runs/tempmem.py. Boilerplate.

Built separately: tables.py, the row-keyed tree-answer store and its parallel row-block writer
(plan 4.5). Not here yet: FitContext and its containers (fit/context.py) and the GLS weight model
(R25).

Importing this package loads nothing. bank.py, correctors.py and pool.py load numpy, and the tree
primitives load scikit-learn when they first fit, so import them after the launcher has pinned the
thread pools.
"""
