"""PROPOSED science signatures for owner approval. Nothing in this folder runs.

Every function body here is exactly one line that raises NotImplementedError. The owner approves or
edits each signature and docstring; only then does the agent write a body, which the owner reviews
before it is used (owner rule: agent writes boilerplate, the owner signs the science contract).

Layout (one file per science module named in the plan, Section 4.2):
    common.py         shared proposed types (enums, frozen dataclasses, protocols), incl. the
                      keys-only dense grid, the target table, the label-free feature source,
                      the bank and the layer's adoption records
    derive_rules.py   R1-R36 home (derive/)
    timing.py         forward reach, reference instant, lags (R8), cuts (R11), freeze (R9)
    io_science.py     integer step index, sentinels, 1:1 joins, lags/bans/freezes, set and file
                      checks, dense grid + predecessor lookup, history block (R17), aggregations
    split.py          sorted sets, stride unit picks (R18), folds, disjointness, output set checks
    fit_context.py    FitContext with DonorRows and UnitHistory, cuts per lead, fitctx_log
    bank_recipe.py    R19: three name seeds, fit-one-tree primitive, correctors, placebo
    weights_gls.py    R25 GLS row weights
    route_kinds.py    R12-R16: per-unit, region (normal column, whole-unit cap), neighbour
    layer.py          R22-R29: links, c, arms, penalty search, selection + N2, clip, ladder pin
    metrics.py        R31-R36: baselines, scores, detection, jackknife, single verdict, band
    vault.py          label vault (the only label source: validity, plan-time donor labels,
                      as-of views) + adoption locks (nowcast and per lead)
    validators.py     every G-* validator the plan marks as science

Provenance (source file:line) is written in comments directly above each function, never inside a
string, because G-NONAMES refuses dataset names and 4-digit numbers in engine strings.
"""
