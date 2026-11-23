# BUILD NOTES: ruling V7, the toy-only legacy replay harness

Written 2026-10-19 by the V7 build task. Owned folder: `D:\treeroute\coral_build\replay\`. No engine file was edited.
Result: `replay\REPLAY_REPORT.md` (PASS). Plan: `PLAN_RULING_V.md` section 4.

## Gate

- The harness imports the build copy, so it waited for the gate.
- First check at 22:13:04: `noop\noop_summary.txt` held "RESULT: PASS. All four grid smokes are identical under LIVE
  and the build copy." No process had "treeroute smoke" in its command line. The gate passed on the first check.

## Files written

- `replay\run_replay.py` (entry point), `replay\legacy_lines.py` (verbatim spans, edits, self-check),
  `replay\toy.py` (toy and bank), `replay\README.md`, `replay\REPLAY_REPORT.md`.
- Run folders `replay\out\20261019_222446` (P2 FAIL, raw weights), `20261019_222612` (PASS),
  `20261019_222733` (PASS, the one the report cites). Nothing was deleted.

## Deviations from the plan

1. **The legacy loop runs from the verbatim copy.** Plan 4.3 said "as a function with switches". The harness instead
   executes `adaptation.py:1600-1667` as copied, with eight marked text edits that add the switches
   (`legacy_lines.py:243-273`). Each switch at its legacy value gives the legacy line. So the code under test is the
   legacy text, not a re-typing of it.
2. **Strict mask without an edit.** The aligned run gives each frame row its own eco label, so the `same` clause
   (`adaptation.py:1611`, `:1620`) holds only the row itself. The eligible set is then the engine's candidates dated
   before the issue day (`run_replay.py:222`).
3. **Edit E-L8 (pool-mean weights) added.** The engine divides each pool's weights by their mean
   (`engine/treeroute/route/solve.py:244`). With raw weights the primal's fixed 1e-8 jitter gives gaps up to 1.3e-4 on
   the toy. P2 compares with pool-mean weights on both sides; the raw-weight gap is reported as information.
4. **A third aligned case: 40 trees per group at lead 0.** With 12 trees per group no toy pool has fewer rows than
   columns, so the k-space dual never ran. With 40, 27 rows take the dual on both sides.
5. **Extra step-2 rows.** (j) Z and context scalers over every train row at the lead (LK1 of `SPEC_NEIGHBOUR.md:442`),
   and `legacy_all` (every legacy behaviour at once). Both report only.
6. **P4 on planted passes.** The toy's main passes have no fallback row, and the engine refuses a scored row issued
   before the cut. So P4 builds two small passes from the first 11 and 12 candidates (cut = the last one's day).
7. **One new run folder per run** (`out\<timestamp>\`), so nothing is overwritten. One more row file:
   `rows_lead0_wide.parquet`.
8. **Toy check without a marker file.** `SPEC_NEIGHBOUR.md:383-384` asks for a marker the toy builder writes. The builder
   writes none, and `engine/tests/table_toy.py` is not mine to edit. The harness takes no data path, builds the toy
   itself in a new folder, and checks the builder's dataset.yaml name and description (`toy.py:56`).
9. **(g) MMM.** The raw toy column c_aux is added as the unpenalised MMM column; the context block is unchanged.
10. **G1 in every legacy frame.** Rows with a missing context value are left out of every frame (the legacy frame had
    none).
11. **The legacy spread forest runs with n_jobs 1** (legacy 4; a forest's values do not depend on n_jobs).
12. **Location.** `SPEC_NEIGHBOUR.md:382` names `engine/legacy_harness/neighbour_replay.py`. V7 and the plan put it
    outside the engine, under `replay\`. Followed the plan.

## Tests run

- Only the harness itself (three runs, about 26 s each). Final run: exit 0, P1-P5 pass, P6 yes. The second and third
  runs are byte-identical. No engine test was run (no engine file changed).

## Open items

1. **Re-run the harness after all V edits land.** The engine hash moved during this work (`b0ddaf81...6096` at the run,
   `a4900984...0e5e` at the no-op proof): the V1 task edited the build copy. The kernels used here did not change
   (`route/neighbour.py` docstring only, `:960-962`).
2. `SPEC_NEIGHBOUR.md:425` and `BUILD_REPORT.md:104` still say N18 is not built. I do not own them; the integrator
   should point them to `replay\REPLAY_REPORT.md`.
3. Owner, information: the engine's pool-mean weight scaling is a (tiny) departure from the legacy weighted primal.
   It is already in the weighted solvers' "NEW, for owner review" text (`route/solve.py:27-30`, `:244`).
4. The toy has 16-20% rows with every tree dropped. V2 asks for this share on the full data; the toy says nothing
   about coral.
