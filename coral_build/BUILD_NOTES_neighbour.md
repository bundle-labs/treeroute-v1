# BUILD NOTES: neighbour router (builder key: neighbour)

Written 2026-10-19. Scope: route/neighbour.py (new), the neighbour stubs in route/kinds.py, tests.
Paths are under `D:\treeroute\coral_build\engine\`.

## Files

| File | Change |
|---|---|
| treeroute/route/neighbour.py | NEW. Strict pool, drop set, Z, trees-off, the private kernels, dense answers. |
| treeroute/route/kinds.py | Neighbour stubs only (lines 1209-1286) and two docstring paragraphs (59-72). `trees_off_neighbour` delegates to route/neighbour.py. The other four approved names still raise `NotImplementedError`, now naming the built body. |
| tests/test_route_kinds.py | The neighbour pin list drops `trees_off_neighbour` (now wired); one new test checks the delegation. |
| tests/test_route_neighbour_pool.py | NEW. 26 tests (spec 8, test_neighbour_pool items 1-9, plus Z). |
| tests/test_route_neighbour_fit.py | NEW. 32 tests (spec 8, test_neighbour_route items 1-7, plus extras). |
| treeroute/engine_constants.py | Not changed. No new constant: a new constant moves `constants_hash`, which grid manifests record. |

## What the pipeline builder calls (route/neighbour.py)

- `pool_feature_z(cand_raw, score_raw, cand_times, cut)` -> (cand Z, score Z, mean, sd). NaN -> 0, constants on candidates only.
- `NeighbourRows(...)`: the fields of SPEC_TABLE_MODE.md 4.3, unchanged.
- `neighbour_pools(rows, blocks, echo=None)` -> `NeighbourPools` (once per pass; serves every arm).
- `pool_records(rows, pools)` -> columns for `pools_<pass>.parquet`.
- `dense_answers(store, table_kind, row_keys, row_group, tree_group)` -> `NeighbourAnswers` (one kind).
- `_route_neighbour_grid(rows, answers, tree_group, blocks, design, tol, *, pools=None, echo=None)`.
- `_route_neighbour_at(rows, answers, tree_group, blocks, design, point, tol, *, pools=None, echo=None)`.
- `_trees_off_neighbour_pass(rows, blocks, *, pools=None)` -> (trees-off, rows with pool, rows without).
- `neighbour_pool_loro(..., blocks, *, row_issue_day)`: the per-row public form (SPEC_TABLE_MODE.md 4.1).
- `design` may be `derived["R14"].value` as is (a derive/shapes.py RouterDesign). Points may be either GridPoint class.

## Deviations (each the smallest the code forced)

1. **kinds.py wiring.** The task said "wire the stubs". SPEC_TABLE_MODE.md 4 said "the stubs stay raising" (O19).
   tests/test_route_kinds.py:360-372 pins every approved name to its exact parameter list, so the kinds.py
   `neighbour_pool_loro` cannot take `row_issue_day`. Without the issue day it cannot apply U4. So:
   `trees_off_neighbour` delegates (same signature); `neighbour_pool_loro`, `route_neighbour_loro` raise naming
   the gap and the built body; `neighbour_pool` and `route_neighbour` raise as superseded pre-LORO names.
2. **Ties at the feature step.** Spec 1.2 step 7 says ties go to the earlier row position "at both steps".
   The spec's own code is a stable sort on the 150 map-ordered rows (adaptation.py:1640 with `kind="stable"`).
   That keeps the MAP order on a feature tie: nearer first, then earlier row position. Built as the code says.
   The two readings differ only when two rows at different sites have exactly equal Z distance. The legacy
   harness (spec 8, step 1) needs this reading to get "same pools".
3. **Kernel keywords.** `pools=None` and `echo=None` are added, keyword only. Pools are deterministic, so a
   passed pool gives the same bytes (tested); a pool built on other rows is refused by a fingerprint.
4. **`answers` shape.** Spec 4.3 says "the dense answer matrix with a row lookup". Built as the frozen
   `NeighbourAnswers(keys, values, tree_group, kind)`. The kernel checks `tree_group` against the bank's.
5. **`tol`.** Kept in the signature, checked (finite, > 0) and recorded. The kind has no normal, so there is
   no trees-off identity to assert (SPEC_NEIGHBOUR.md 4). G-PLUMB pair 1 stays in the decision step (O10).
6. **Record.** No "c used" field: c is not a kernel input (y arrives in link space). The pass adds it.
7. **Extra guard.** `NeighbourRows` with a score row issued before the pass's cut is refused (G-FITCUT). Valid
   passes never have one (SPEC_TABLE_MODE.md 2.4; `check_inner_score_rows`).
8. **"Not train-marked" assert (spec 1.2 step 8).** The kernel has no mark field. Train-only candidates come
   from `ctx.router_rows`; the pool audit of SPEC_TABLE_MODE.md 6.3 checks marks from the files.
9. **Drop groups with no tree.** `router_tree_columns` refuses a group that owns no tree. Such groups are
   left out of its call (they drop nothing); if none remains, every column is kept. Under LORO every group
   trains trees (O13 refuses an empty group), so this does not fire on a valid run.
10. **Trees-off design.** `build_column_block` refuses an intercept-only design, so the kernel builds the
    `[1, context]` (or `[1]`) DesignMatrix directly and calls `trees_off_neighbour`.
11. **Progress blocks.** Reuse `C14.table_row_block_rows` (12,288 rows) for progress lines only.

## Requests for files I do not own

- treeroute/route/__init__.py docstring still says the neighbour kind raises `NotImplementedError`.
  Suggested text: "the neighbour kind (M8) is built in route/neighbour.py; kinds.py's trees_off_neighbour
  delegates to it".
- SPEC_TABLE_MODE.md 5.9 lists route/kinds.py as "NOT edited". It is now edited (neighbour stubs and docstring
  only; no grid line). The engine hash moves anyway (U5).
- tests/test_nonames.py fails on other builders' files: derive/table.py, labels/rows.py, package/table.py hold
  the year '2026' in their module docstrings (move dates to comments).
- tests/test_route_kinds.py::test_the_r36_tolerance_refuses_until_k_is_set fails before and after my edit:
  `C9.guard_tolerance_k` is set by ruling N (engine_constants.py:159, same in LIVE). Not a neighbour test.

## Grid byte-identity

- route/neighbour.py is new. No grid module imports it. kinds.py imports it lazily, only inside
  `trees_off_neighbour`, which no grid path calls.
- kinds.py: only the five neighbour stubs, the `_NEIGHBOUR` message and docstring text changed. Diff against
  LIVE shows nothing else.
- route/solve.py is not edited by me; the kernel only passes `n_unpenalised=1`.

## Owner items (added or sharpened by this build)

- O19: `trees_off_neighbour` is now wired through kinds.py; the other names are not (deviation 1).
- O5 detail: the feature-step tie rule (deviation 2).
- N3, N5, N7, N8, N12, N14 unchanged (SPEC_NEIGHBOUR.md 9).

## Measured speed (synthetic, this machine)

13,600 candidates, 480 score rows, 2,000 trees, 35 points, 8 workers: pools 1.1 ms per row; grid 8 ms per row.
