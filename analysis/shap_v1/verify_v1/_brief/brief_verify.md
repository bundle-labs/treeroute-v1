# Brief: independent re-computation of the SHAP comparison numbers (round 14)

Names: SHAP = `D:\treeroute\analysis\shap_v1`; ROOT = the research-paper folder; V = `SHAP\verify_v1` (new; every
output of this round goes there, nowhere else). Never write user names, e-mail addresses, user-folder names, session
ids or workflow ids into any file or output: use the short names.

## Why

The SHAP comparisons of scope (i) (lead 0 of coral, fire, pm25, defo, ndvi) are finished. Their numbers go into the
paper: one main-text row per problem and the new supplement section S3.13 (PROTOCOL.md section 10). Before any of them
is written into the paper, two implementers (A and B) recompute them with their own code, written from the protocol's
words, and a reconciler compares A, B and the official outputs of `SHAP\scripts\compare_shap.py`, the same way the
paper's other post hoc numbers were checked (Supplement S3.1: implementers A and B, then a reconciliation). The owner
gave the go-ahead to open the comparison results on 2026-11-15 (rulings file, section BA).

Treeroute's B1 sensitivity is part of this round (PROTOCOL.md sections 5 and 10; rulings file, section BA, ruling
BA3). Its pieces are `SHAP\out\<p>\lead_0\treeroute_B1\` for defo, fire, pm25 and ndvi (command and status:
`SHAP\RUN_COMMANDS.md` section 2, "Treeroute's B1 sensitivity has its own command"). This round starts only after
that command has ended (every run finished, or a stop recorded there). `compare_shap.py` does not read
`treeroute_B1\`, so the B1 numbers have no official output: A and B compute them, and the reconciler compares A with
B. "The main run" below is treeroute's B2 piece, `SHAP\out\<p>\lead_0\treeroute\`.

## Ground truth for the method

`SHAP\PROTOCOL.md` section 8 (frozen; it defines every statistic), section 5 (the players and the variable level),
section 9 (the files) and section 10 (what the paper reports). Where the protocol leaves a choice open, write down the
choice you made and why; do not look at how `compare_shap.py` or `shapv1_stats.py` made it.

For B1, section 10's bullet "Also in S3.13: treeroute's B1 sensitivity" is the whole specification, with section 5's
definition of B1 and section 8's definitions where that bullet points to them. Compute nothing for B1 that it does not
list (in particular not item 8, fire's view on its rows with a nonzero forecast), and put nothing of B1 into items 1-8.

## The numbers to recompute (both levels, feature and variable, unless said otherwise)

For each problem p and the models of `SHAP\out\<p>\lead_0\compare\per_lead.json` key `models` (main set: key
`main_set`; declined: `declined_by_guard`; link keys: `links`):

1. Active set J (players some model gives more than 1e-12 of its total mean |phi|) and the structural zeros.
2. Per model: I_m(j) = region-weighted mean |phi_ij| (each region weighs 1), shares s_m(j), signed mean S_m(j), the
   number of nonzero players; its top-10 with shares.
3. Families at the variable level (own history, global indices, local drivers, context and calendar, seasonal normal;
   a family's attribution on a row is the sum of its variables' phi on that row) and each model's family shares.
   "Global indices" needs the lead's test set (section 8's rule): find it from the run's records, read only the
   columns you need.
4. Every pair (same-link and cross-link labelled): Spearman over J and over the union of the two top-20 sets; Kendall's
   tau-b; Jaccard top-5, top-10 (top-20 when J has 200 or more players); RBO p = 0.9 and 0.95 on the full rankings
   over J; total-variation distance between shares and between family shares; sign agreement on the union of the two
   top-10 sets among players whose sign is determined in both models, with that count.
5. Per problem: Kendall's W over the main set (tie-corrected); the mean pairwise Spearman of the main set (computed
   directly); each model's stability under region resampling.
6. Uncertainty: the saved draw matrix `compare\bootstrap_draws.npy` (check its SHA-256 against `per_lead.json`); every
   statistic recomputed per draw; percentile 95% intervals with their number of finite replicates.
7. The main-text row (variable level), section 8: the main set; W [CI]; treeroute against its same-link rivals: the
   median top-20-union Spearman [CI] and the range; RBO (p 0.9) of treeroute against the rivals' consensus (the mean
   of their shares, rebuilt per draw) [CI]; treeroute's top 3 variables; the consensus top 3; the own-history share of
   treeroute [CI] and of the median rival [CI]. Fire's main set is treeroute alone: W and the pair statistics are
   undefined there, and treeroute's top 3 and own-history share still have values.
8. Arcsine-link models: the variable-level importances on their rows with a nonzero forecast (pre > 0).
9. Treeroute's B1 sensitivity (section 10's B1 bullet), lead 0. B1 is not one of the models above.
   - First, per problem, write whether `treeroute_B1\` exists and holds `rows.parquet.done.json` (a finished piece)
     or `FAILED.json` (a stop at S-ADD, S-EVAL, S-ZERO or S-RESID); a stop in the set-up (for example
     S-SAMPLE) or a run that never started leaves neither. For a finished piece, write its `meta.json` fields
     `pass`, `checks_passed`, `rows`, `background` (it must be "B1"), `pairs`, `trees_used`, `sample_sha256` (it
     must be the registered one, `SHAP\SAMPLE_REGISTER.txt`) and `duplicates_merged`. A problem without a finished
     B1 piece gets no B1 numbers: write which and why.
   - Defo: only the identity check, with its pairs and seconds (below). Match the rows by `row` and the players and
     variables by name; give the largest |difference| between `treeroute_B1\rows.parquet` and
     `treeroute\rows.parquet` over every row and every `phi__` column, the same over the `phiv__` columns, and
     whether the two runs have the same rows, players and variables. Expected: 0 and the same. If not, write these
     numbers and stop the B1 work there: report to the lead before any other B1 number is computed (section 10 holds
     back the fire, pm25 and ndvi B1 numbers until the cause is recorded and the owner rules).
   - Merged context columns, before any feature-level number of fire, pm25 or ndvi: if the B1 run's
     `duplicates_merged` lacks a column that the main run's merged, sum the B1 run's tree player and context player
     of that column (`phi__x__<v>` and `phi__c__ctx:top5:<v>`) into one player named as in the main run (`x__<v>`),
     as section 10 says. The variable level needs no step. (NDVI's main run merged five columns.)
   - Fire, pm25 and ndvi, at both levels: the B1 run's I(j), s(j) and S(j), with J the pair's J (next sub-item) for
     the shares; its number of nonzero players (at the feature level also before any summing of the previous
     sub-item, for the reconciler); its top 10 with shares. At the variable level also its family shares (the
     families and the global-index rule of items 1-3), its top 3 variables and its own-history share.
   - The pair (the main run, the B1 run), at both levels: Spearman over J and over the union of the two top-20 sets;
     Kendall's tau-b; Jaccard top-5 and top-10 (top-20 when this J has 200 or more players); RBO p = 0.9 and 0.95
     over J; the total-variation distance between the two runs' shares over this J and between their family shares;
     sign agreement on the union of the two top-10 sets among the players whose sign is determined in both runs, with
     that count. J here is the pair's own (the players to which either run gives more than 1e-12 of its total mean
     |phi|), not the J of item 1; ties by section 8's tie rule.
   - Uncertainty: the same saved draws as items 1-8 (`compare\bootstrap_draws.npy`, its SHA-256 checked against
     `per_lead.json`), the same draws for both runs; every number above recomputed on each draw; percentile 95%
     intervals, each with its number of finite replicates; none for the top-k lists.
   - Wherever the protocol leaves a choice open, make for B1 the choice you make for the main pairs, and say so; if
     the reconciliation changes a main choice, compute B1 again with it.
   - Each B1 run's (defo's included) background pairs and its total and tree-SHAP seconds, from its log's set-up line
     and "done in" line (`SHAP\logs\tr_shap_<p>_lead0.log`); the pairs and `tree_shap_seconds` are also in its
     `meta.json`, the total `seconds` in its `rows.parquet.done.json`.
   - Check that `per_lead.json`'s `models` does not list `treeroute_B1`.

## Rules

- Read-only on every existing file. Python 3.9 as `py -3.9 -I -B <script>`; your scripts and results live in V only.
  No pip, no new packages (numpy, pandas, pyarrow and scipy are installed). Small data: no special memory care needed,
  but never write memmaps column by column.
- Before your results are written, an implementer reads none of: `SHAP\scripts\compare_shap.py`,
  `SHAP\scripts\shapv1_stats.py`, the compare outputs (`AW3_table.md`, `AW4_table.md`, `AW4_main_row.json`,
  `pairs.parquet`, `importance.parquet`, `families.parquet`, `bootstrap_stats.parquet`), per_lead.json beyond its
  structural keys (models, main_set, declined_by_guard, links, rows, sample_sha256, the draws' SHA-256 and the maps of
  players to variables and families if it holds them), and the other implementer's folder. Reading the protocol, the
  row files, `meta.json`, `bootstrap_draws.npy` and the run records is allowed.
- Do not open `SHAP\smoke\bardl_fix\` (not needed).
- Results: one JSON file per implementer in the schema given by the spec, so that the reconciler can match every number
  by its key.
- The B1 pieces (`SHAP\out\<p>\lead_0\treeroute_B1\`: `rows.parquet`, `background_keys.parquet`, `meta.json`,
  `rows.parquet.done.json`, or `FAILED.json`) are row files and run records: reading them is allowed in this round.
  `SHAP\logs\tr_shap_<p>_lead0.log` holds the main and the B1 lines one after the other, with no B1 label; the B1
  lines are those written from 2026-11-15 23:06.
- Results: the B1 numbers go under their own top-level key `b1`: per problem `status`; for defo `identity`; for
  fire, pm25 and ndvi `run` and, per level (`feature`, `variable`), `importance`, `top10` and `pair_main_b1`, and at
  the variable level also `families`, `top3` and `own_history_share`. Each number that has an interval carries
  `value`, `ci_low`, `ci_high` and `n_finite`, so that the reconciler can match every B1 number by its key.
- The reconciler compares A with B on every B1 number (there is no official one), diagnoses each mismatch as for the
  main numbers, compares A's and B's B1 nonzero counts with the B1 `meta.json`'s `players_nonzero` (the count before
  any summing of merged context columns) and `variables_nonzero`, and confirms that no number of items 1-8 depends
  on B1.
