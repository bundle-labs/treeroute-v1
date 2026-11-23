"""treeroute.route: the routers (plan 4.2, route/solve.py and route/kinds.py rows).

What exists:
  - solve.py   the per-unit ridge solvers, moved as-is: the block-penalised primal and dual
               (each penalised block trace-normalised on its own raw columns), the shared-Gram grid
               solve with its reference cross-check on the first NVERIFY units, the single-point
               solve. numpy's Cholesky. Boilerplate move, gated by byte identity.
  - kinds.py   the PER-UNIT kind: column blocks (intercept, unpenalised normal, context, trees),
               the 7 x 5 grid around the engine-constant centres, the normal from fit rows (R15),
               trees-off = intercept + normal with the identity asserted (R16), the own-overlap-block
               tree-column mask, checked against the store's own trees, and its assert (R14,
               G-DISJOINT), units solved ROUTER_WORKERS at once at ROUTER_WORKER_BLAS_THREADS BLAS
               thread(s), short-history units flagged (R12). The router kernels are private
               (_route_per_unit_grid, _route_per_unit_at) until the owner approves public entry
               points; the approved route_per_unit_loro will call them.
               SCIENCE: owner-approved signatures, agent bodies. The region kind's approved names raise,
               naming route/region.py, where its bodies are built (Tue 6 Oct); of the neighbour kind's
               names, trees_off_neighbour delegates to route/neighbour.py and the others raise, naming it.
  - region.py  the REGION kind's bodies (the pipeline calls them).
  - neighbour.py  the NEIGHBOUR kind's bodies (the table option, owner ruling U: the strict pool, the drop
               set, Z, trees-off and the private kernels; pipeline/table_router.py calls them).
  - solve.py's solvers take the keyword n_unpenalised (default 2, the moved bytes; the neighbour design
               passes 1).

Importing this package loads nothing; solve.py and kinds.py load numpy (import them after the
launcher has pinned the thread pools). threadpoolctl and scipy load at the first router call,
scipy before the BLAS limit is entered.
"""
