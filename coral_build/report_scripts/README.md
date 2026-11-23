# Coral report-only scripts

Written 2026-10-20 for the coral pre-registration (PREREGISTRATION_DRAFT_coral.md section 6.1, 6.2 and section 12
item 8). They run AFTER the headline run, on its SAVED rows. They never fit, never pick and never edit the run.
Nothing they print can change a choice or the verdict. Not signed; the owner reviews them before the freeze.

## Files

| File | What it is |
|---|---|
| coral_report.py | the report script (the only file the headline report uses) |
| build_toy_runs.py | builds SYNTHETIC toy runs with the engine's own toy table package (engine/tests/table_toy.py) |
| test_coral_report.py | pytest: hand-computed numbers plus checks on the toy runs |
| toy_runs/ | the toy runs (synthetic only; no real data) |

## Command (after the headline run is DONE)

```
py -3.9 coral_report.py <run folder> --package <LIVE engine>\datasets\coral --out <new folder>
```

The month-precision list needs no flag: a non-toy run always reads
D:/treeroute/coral_build/coral_data/month_precision_rows.csv and refuses unless its SHA-256 is
cfa18268198ca9be48feb26f384287e7fe694c6f1ca7b221773af1994d838bf5 (coral_report.py MONTH_PRECISION_LIST,
MONTH_PRECISION_SHA256).

- `--out` must be a new or empty folder, outside the run folder and outside every root in
  D:/treeroute/registry/protected_roots.txt. Every file is created once (never overwritten).
- `--stratum` is needed only if the run has more than one report stratum (coral has one: `programme`).
- `--month-precision-rows <csv>` names the month-precision list (see "Saved-record tables", item 3). For a non-toy
  run it may be left out (the pinned list above is read); a given file must have the same SHA-256. For a toy run it
  is optional; without it the month-precision pool counts print "not saved by the engine".
- **Read gate.** It refuses any run that is not a headline-eligible headline run (run_record `kind` "headline" and
  `headline_eligible` true), before any score file is opened. So a real-data smoke's test scores are never read
  before the freeze (read rule, PREREGISTRATION_DRAFT_coral.md section 12 item 4). `--toy` is for the tests only: it
  admits a run whose package is the synthetic `toy_table`, and nothing else.
- Exit code 2 and a `REFUSED:` line when a saved file is missing or does not agree with the engine's records. This
  includes: the recomputed registered verdict (the ALL line) differs from verdict.json or ladder.json; fitctx_log has
  no "bank" donor-rows record at a fit cut, or test_preds has no `base__donor_median` (the two donor-row
  cross-checks cannot be made); the protected-roots file is missing. Since version 1.2.0 also (fail loud: the
  engine always writes these records): derived.json has no R30, or a lead table lacks an R30 or `mhw_*` column, or
  the lead-0 donor-row NaN share of a tree column differs from R30 filled_share; under a V1 decline target, a lead
  guard record lacks a field, `guard.passed` differs from `not declined_at_lead`, the nowcast decline baseline is
  missing, or the best tree arm has no surface MAE; run.log is absent, holds other than one decision block or no
  parsed line, its arms differ from adoption.json decision.candidate_order's tree arms, a printed MAE differs from
  surface_mae by more than the %.6f rounding (5e-7), or the best arm's printed point differs from
  best_tree_penalty; the month-precision list's SHA-256 differs from the pinned one (non-toy run), or a listed row id
  is not a row of the lead-0 table.

## What it reads (saved files only; each file's SHA-256 goes into inputs_manifest.json)

- Run folder: DONE.json, run_record.json, derived.json, verdict.json, decision_checks.json,
  test_pass_router.json, fitctx_log.parquet, test_preds.parquet, pools_*.parquet, context_missing/*.parquet,
  ladder/ladder.json, ladder/lead_<L>/{lead.json, test_preds.parquet, pools_guard.parquet,
  pools_test_pass.parquet, issue_missing_rows.parquet}.
- Run folder, for the saved-record tables: adoption.json, adoption_lead_<L>.json, decision_checks.json
  (decline_baseline), derived.json (R30, R14:overlap_blocks), verdict.json (blocked_jackknife, best_tree_arm,
  best_tree_penalty, decline_target), ladder/lead_<L>/lead.json (guard.*, test.decline_target), pools_*.parquet
  (pool_row_ids), run.log (the engine's printed decision lines only).
- Not an engine file: the data builder's coral_data/month_precision_rows.csv (column row_id;
  build_visits.py:295-297), pinned by SHA-256 for a non-toy run. Its SHA-256 goes into the manifest.
- Package: catalog.yaml (column roles only).
- The lead tables named in derived.json (U1:table). Their SHA-256 must equal the one the run recorded. Only the row
  id, group, target date, mark, label and stratum columns (for the donor rows' labels), and the R30 tree columns and
  the `mhw_*` columns (for the R30 counts), are read.

## What it writes

| File | Draft item | Content |
|---|---|---|
| per_programme.csv | 6.2 item 1 | every column (arms, placebos, baselines) per programme value and pooled; MAE with predict-zero and donor-row median beside; hit, corr2, calibration, R33 top-10% |
| programme_verdicts.csv | 6.2 item 1 | per-programme D74 lines, report only; the ALL line re-computes the registered verdict and says if it matches the engine |
| magnitude_edges.csv, magnitude_bins.csv | 6.2 item 2 | edges from donor rows; MAE per bin, per programme |
| flattening_guard.csv | 6.2 item 3 | mean prediction vs observed mean on severe rows, every column |
| per_year_macro.csv | 6.1, 6.2 item 4 | per test year, pooled, and macro over ecoregions |
| per_ecoregion.csv | 6.2 item 5 | n, zero share, programme mix; sorted by name, no MAE |
| counts_no_tree.csv | 6.2 item 6 | rows left with no tree, per arm and pass (surface, test pass, each guard) |
| counts_pool_fallback.csv | 6.2 item 6 | pool fallbacks per pass, from the pools files, checked against the records |
| counts_left_out.csv | 6.2 item 6 | H4 rows absent at a lead; rows with missing router context |
| guard_reference.csv | 6.1 "Per lead" | guard reference = decline object (V1), its MAE beside the pinned arm's MAE on the guard surface, per lead |
| r30_missing.csv | 3.8, 6.2 item 6 | R30 0-filled share per tree column as saved (lead 0); the NaN share per column and the marine-heatwave NaN-row counts at every lead, on donor and scored rows, counted from the lead tables |
| pools_month_precision.csv | 6.2 item 6 | pools holding a month-precision row, counted from the saved pools and the builder's pinned list (not an engine record) |
| penalty_edge_picks.csv | 3.6, 6.2 item 6 | picks at the penalty grid edge: the saved picks and each arm's printed pick |
| programme_blocked_jackknife.csv | 6.2 item 1, 8 | blocked jackknife per programme (report only) |
| coral_report.md | 6.2 order | the tables above in the draft's order, with its wording |
| inputs_manifest.json | | script SHA-256, every input's SHA-256, run kind |

Every lead is reported on its own rows ("all") and on the rows common to all leads ("common").

## Definitions

Fixed by the draft (implemented as written):
- Magnitude bins: 0, then the donor rows' quartiles of the positive labels, right-closed; edges from train rows at
  the lead's fit cut, never from test rows (draft 6.2 item 2).
- Predict-zero and the donor-row median beside every MAE (draft 6.1).
- Macro = the unweighted mean over the scored ecoregions (draft 6.1, per test year and macro).
- Programme verdict lines: the D74 rule, jackknife over the groups holding that programme, report only (draft 6.2 item 1).

**Chosen by the agent (the draft is silent or vague; the owner confirms or changes each):**
1. **Donor rows** of a lead: the run's bank rows (derived.json R18:units "bank", so donor-only groups count) in that
   lead's table, target date at or before the lead's fit cut (derived.json R11), finite label. The script checks
   this equals the engine: same count as fitctx_log's "bank" hand-out, same median as the saved base__donor_median.
2. **Flattening guard edge (owner ruling X4, 2026-10-20: (b) is the default).** The draft says
   "the donor rows' upper quartile". The script prints both edges, each labelled (flattening_guard.csv columns
   `edge_role`, `is_default`): (a) q75 of ALL donor-row labels, as worded -- printed beside;
   **(b) q75 of the POSITIVE donor-row labels, the top magnitude bin's edge -- the DEFAULT (owner ruling X4)**. With many zero
   labels edge (a) is low, so its "severe" rows are not very severe (the legacy record's severe rows had an observed
   mean of 74). coral_report.py sets EDGE_DEFAULT = EDGE_POSITIVE.
3. **Rows at the edge** count as severe ("at or above", y >= edge).
4. **Quantile method:** numpy's default (linear), the same as the engine's stratum_edges.
5. **"Shown with n only":** a programme value with fewer than 10 scored rows at that lead (the engine's 10-row
   minimum for anomaly R2 and for R33 events). This gives AGRRA (1) and Donner (0) n only, by rule, not by name.
6. **Rows for each column:** a column is scored on rows with a finite label and a finite prediction (persistence has
   gaps); predict-zero and the donor-row median are scored on the SAME rows, beside it.
7. **Hit tolerance:** the engine's own (verdict.json at lead 0, ladder.json at the leads). The lead-0 value is
   rebuilt from the donor rows and must match.
8. **Common rows:** keys (row id, target day) with a finite label and adopted prediction at every lead, as the
   engine's ladder (table_ladder.py:606-611).
9. **Per-programme verdict at a lead** uses the nowcast band, and says "declined" when the layer declined there, as
   the engine's verdict does. When R35 gave no band it says "no band (R35)".
10. **Programme values** come from the lead tables (rows of the run's groups), so a value with 0 test rows (Donner)
    still gets a line with n = 0.

11. **R33 top-10% detection on the pooled line.** Draft 6.1 says it is printed within programme only, or labelled.
    The script keeps the pooled number and labels it: per_programme.csv column `detection_label` reads "source
    statistic, not severe-tail skill" on every ALL line and "within programme" on the others.

## Saved-record tables (added 2026-10-20, version 1.1.0; version 1.2.0 the same day)

Each fact is read from the file where the engine saved it. A fact the engine does not save is counted from the saved
rows and the lead tables and labelled "counted from the lead table (not an engine record)" (or, for a toy run
without a month-precision list, printed as `not saved by the engine`); nothing is rebuilt from engine internals. A
record the engine always writes that is missing or disagrees is a refusal, not a blank.

1. **Guard reference per lead** (guard_reference.csv; draft 6.1 "Per lead"). Leads: lead.json `guard.baseline_column`,
   `baseline_value`, `baseline_donor_rows`, `baseline_mae`, `pinned_mae`, `own_trees_off_mae`, `passed`,
   `surface_rows`, `bank_cut`, and `test.decline_target`; `pinned_minus_reference` = pinned_mae - baseline_mae;
   `guard_and_decline_one_object` says if the guard reference and the decline target are the same column (V1).
   Nowcast: decision_checks.json `decline_baseline` (key, mae, per-fold medians; checked equal to adoption.json
   decision.decline_baseline) and adoption.json `surface_mae` of verdict.json's best tree arm at its saved
   best_tree_penalty. Not saved by the engine at the nowcast: one reference value (there is one median per fold) and
   its donor-row count. The pinned arm's own trees-off MAE is printed beside (`own_trees_off_mae`, as the engine logs
   it, table_ladder.py:378-381). Under a V1 decline target the script refuses a lead guard record without one of
   these fields (table_ladder.py:356-357, :368-371), a `guard.passed` that differs from `not declined_at_lead`
   (:548, :558), a missing nowcast decline baseline, and a best tree arm without a surface MAE.
2. **R30 and marine-heatwave NaN rows** (r30_missing.csv). Saved: derived.json R30 (derive/table.py:247-266): per
   tree column, the share missing before the 0-fill on the donor rows at the lead-0 fit cut, the real-zero share, the
   per-test-year missing share on the lead-0 table, the flag threshold (C15) and the engine's flags. Marine-heatwave
   columns are those named `mhw_*` (catalog.yaml:182-211); the largest of their shares is printed. **Not saved by the
   engine, so counted here** from the lead tables (labelled "counted from the lead table (not an engine record)"),
   at every lead, on the donor rows at the lead's fit cut and on the scored test rows (finite label): the NaN share
   of every R30 tree column and every `mhw_*` column; the rows with a NaN in any `mhw_*` column; and, apart, the
   rows with a NaN in `mhw_days_365` (NaN exactly when under 60 thresholded days, build_tables.py:315-330;
   `mhw_thr_gap` can be NaN for another reason). At lead 0 every tree column's donor-row share must equal R30
   filled_share, or the script refuses (so the donor rows are the engine's R19 donor rows).
3. **Pools holding a month-precision row** (pools_month_precision.csv). **Not saved by the engine.** The pools are
   saved (pools_<pass>.parquet, pool_row_ids), but the lead tables carry no date-precision column (the published
   lead_0.parquet schema has none) and no engine code or record counts month-precision rows. Note: the package's
   exceptions.yaml:93-94 says "the run counts per pass the pools that hold one"; no engine code does this (no match
   for "precision" in treeroute/*.py outside _proposed). The script counts, per pass, the saved pools holding a row
   of the builder's list, labelled "not an engine record". The list is pinned (coral_report.py MONTH_PRECISION_LIST,
   MONTH_PRECISION_SHA256) and every listed row id must be a row of the lead-0 table, so a row-id format mismatch is
   refused instead of printing 0.
4. **Picks at the penalty grid edge** (penalty_edge_picks.csv). Saved picks: adoption.json `penalty` (the adopted
   pick; none when declined) and `best_tree_penalty`, adoption_lead_<L>.json `penalty` (the pinned arm). The grid:
   adoption.json `decision.grid`. The edge is the engine's own rule (layer/decide.py:214-229), a lookup on the saved
   values. Each arm's own pick is not in any structured record; the engine prints it in run.log
   (decide.py:1084-1098, "EDGE PICK"). The script reads those lines, and refuses if the edge it reads from the saved
   grid differs from the printed one. It also refuses when run.log is absent, holds other than one decision block or
   no parsed line, its arms differ from the tree arms of adoption.json `decision.candidate_order` (trees-off and
   missing arms left out), a printed MAE differs from adoption.json `surface_mae` at the printed point by more than
   5e-7 (the engine prints %.6f), or the best arm's printed point differs from `best_tree_penalty`.
5. **Blocked jackknife per programme** (programme_blocked_jackknife.csv). The engine saves it once: over all groups,
   adopted vs reference, at the nowcast (verdict.json `blocked_jackknife`; jackknife.csv). Per programme and at the
   leads it is **not saved by the engine**; the script computes it from the saved rows and the saved overlap blocks
   (derived.json R14:overlap_blocks), with the engine's rule (metrics.py:1058-1087; flag when the blocked SE is over
   1.2 x the group SE, C10.borderline_share). The ALL line at the nowcast must equal verdict.json, or the script
   refuses. A test checks the block-mean step against the engine's own functions (blocks of several groups).
   Report only; the group jackknife decides.

The flattening-guard edge labels are built from `EDGE_DEFAULT` (coral_report.py `edge_roles`). Owner ruling X4
(2026-10-20) set `EDGE_DEFAULT = EDGE_POSITIVE`; the labels and `is_default` follow. Any later change needs a
re-hash before the freeze.

Not built here:
- printed by the engine's report tool (treeroute_report), not here: the donor-only disclosure row (kind
  donor_only_groups, treeroute_report/table.py:542-545); the pre-clip rate (the engine's per_stratum.csv and
  ladder/ladder_table.csv, column preclip_rate; table.py:738);
- not reported at all: R2 of any kind (draft 6.1).

## Tests (synthetic only)

```
py -3.9 build_toy_runs.py            # once; skips a variant whose folder exists
py -3.9 -m pytest -q test_coral_report.py -p no:cacheprovider
```

Hand-computed checks: magnitude bins (right-closed), the MAE line with predict-zero and the donor median beside,
the flattening guard, the D74 tag and jackknife. Toy-run checks: edges and bins against an independent count;
flattening guard against an independent mean; predict-zero equals the mean absolute label on every column's rows;
per-programme, per-year and pooled numbers equal the engine's per_stratum.csv, per_year.csv and score_pooled.csv at
the nowcast, and the pooled lines equal ladder/ladder_table.csv at leads 0, 183 and 365 (all and common rows);
macro equals the mean of per_group.csv; the ALL verdict lines match verdict.json and ladder.json; every
non-identical band pair of jackknife.csv, put through programme_verdicts itself (adopted = the arm, not declined),
gives the engine's mean and SE (the ok toy declined, so its own contrasts are all 0; the donor-only toy adopted
identity_plain_gls); the pooled R33 label; pool and no-tree counts match the records; a donor-only group scores
nothing. Refusals: output inside the run, under a protected root, not empty; an unfinished run; the read gate (a
smoke without --toy, a real-data package with --toy, a headline run that is not headline-eligible); a missing
protected-roots file; a verdict that disagrees with the engine; a missing donor-row cross-check. The toy runs are
smokes, so every test call passes --toy.

Saved-record checks (added 2026-10-20): guard_reference equals lead.json guard.* at leads 183 and 365, and at the
nowcast the decline baseline's MAE (decision_checks.json) and the best tree arm's row of inner_candidates.csv
(hand numbers for the ok toy: lead 183 reference 11.769119, pinned minus reference 22.737449 - 20.926808; nowcast
pinned 21.728048 as printed in run.log); R30 rows equal derived.json (ok toy f6: 13 of 116 donor rows); the toy
package has no `mhw_*` column, so its marine-heatwave counts say so; a hand R30 record with `mhw_*` columns;
month-precision pools by hand (3 pools, 2 hold the listed row) and on the toy with a SYNTHETIC list against an
independent text search; the edge rule by hand (bottom, top, interior, frozen axis, a point off the grid) and the
run.log parser by hand; on the toys every printed EDGE PICK equals the saved-grid edge (the donor-only toy's adopted
pick, level 3 ratio 1/16, is interior on level and at the bottom on ratio); the blocked jackknife by hand (blocks
{a,b}, {c}, {d}: mean 14/3, SE sqrt(2/3 x 19/6)) and its 20% flag; on the toys the ALL line equals verdict.json
(donor-only toy: mean -1.144, SE 1.249, 3 blocks), every band pair through the per-programme function gives
jackknife.csv's mean and SE (one group per block), a shifted blocked jackknife is refused; both flattening edges
printed, (a) marked default, (b) not. No toy run was rebuilt: the existing toys cover every new output
(build_toy_runs.py unchanged).

Version 1.2.0 checks (2026-10-20): R30 counts at leads 0, 183 and 365, on donor and scored rows, against an
independent isna count on the lead tables (ok toy f6 at lead 0: 13 of 116 donor rows, equal to R30); marine-heatwave
counts by hand (any `mhw_*` NaN vs `mhw_days_365` NaN); refusals for a shifted R30 share (by hand and on the toy);
the month-precision list pinned by SHA-256 (constant read without a flag; another file, a changed file, an absent
file refused) and a listed id that is no lead-0 row refused; guard refusals (a missing field, `passed` against
`declined_at_lead`, no decline baseline, no surface MAE); run.log refusals (absent, no block, two blocks, no parsed
line, an arm set mismatch, a printed MAE off by 1e-5, a best-arm point mismatch) on copies of the toy's records;
the blocked jackknife and its flag equal the engine's `treeroute.report.metrics` functions on the hand case and on
two 12-group, 5-block cases (one with the flag set); the edge labels follow a monkeypatched `EDGE_DEFAULT`.
