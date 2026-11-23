# Brief: the number tables of Supplement S3.13 and main-text Table 9 (SHAP, post hoc)

Names: SHAP = `D:\treeroute\analysis\shap_v1`; V = `SHAP\verify_v1`; ROOT = the research-paper folder (the parent of
`engine\` and `paper\`); OUT = `ROOT\paper\supp_build\s3_13`. Problems: coral, fire, pm25, defo, ndvi (scope (i): lead 0
of each).

## Goal

Build every number table that the paper's SHAP write-up needs, from the stored values, with ONE rounding step: each
printed number is formatted once from a stored double (never re-round a printed number; never copy a printed table).
The tables are: the new section S3.13 of Supplement S3 (`ROOT\paper\draft\S3_posthoc.md`; its tables continue the
numbering at Table S3.18) and one compact main-text table, Table 9 (Section 5.4, "Post hoc analyses", in
`ROOT\paper\draft\05_rivals.md`; Tables 1-8 exist, see `ROOT\paper\draft\TABLE_NUMBERS.md`). The text around the
tables is written later, by another workflow; this one makes the tables and proves them (one spec, two independent
builders, a reconciler, a skeptic).

## Sources

- The analysis protocol `SHAP\PROTOCOL.md`: section 7 (rivals covered and left out), 8 (players, J, statistics,
  bootstrap, the main-text row; frozen), 9 (outputs), 10 (what goes into the paper, the presentation rules BB1-BB6, the
  B1 list, "Not claimed"), 4 and 11 (gates and stop rules), 14 (change log; its last entry records the independent
  re-computation of 2026-11-16 and what `compare_shap.py` does not do). The rulings: `ROOT\engine\OWNER_RULINGS_2026-10-06.md`
  sections AW, AY, AZ, BA and BB. The run record: `SHAP\RUN_COMMANDS.md`.
- Official comparison outputs, per problem, in `SHAP\out\<p>\lead_0\compare\`: `importance.parquet`,
  `families.parquet`, `pairs.parquet`, `per_lead.json`, `bootstrap_draws.npy`, `bootstrap_stats.parquet`,
  `AW4_main_row.json` (and the printouts `AW3_table.md`, `AW4_table.md`). Per model, `SHAP\out\<p>\lead_0\<model>\`:
  `meta.json`, `exactness.json` (rivals; for `rival_ridge` outside coral also `ridge_shap_exactness.json`, the check
  that passed), `gates.json` (treeroute), `rows.parquet.done.json`; treeroute's B1 runs in `treeroute_B1\`.
- The independent re-computation (round 14): `V\A\results.json` (implementer A; equal to B's, and every number that
  the official files also hold equals theirs within 1e-9), its keys in `V\spec\SPEC.md` and `V\spec\results_schema.json`,
  `V\reconcile\report.md` (fourth version: read the lead's note first; its A1 corrects the reconciler's text, A4 gives
  the BARDL tie maxima, A5 the six points the owner accepted as rulings BB1-BB6, A6 the B1 tables built from
  `results.json`), `V\_lead\outputs\bardl_maxima.txt` (the tie maxima at full precision).
- B1 run facts: `SHAP\logs\tr_shap_<p>_lead0.log` (the B1 set-up line with its background pairs; the "done in" lines
  with total and tree-SHAP seconds; the B1 block of each log starts at its last set-up line, see RUN_COMMANDS.md
  section 2, "Status."). Samples: `SHAP\SAMPLE_REGISTER.txt`.
- Paper conventions: `ROOT\paper\draft\S3_posthoc.md` (its header comment; Tables S3.1-S3.17; read one or two table
  sections, for example S3.6 and S3.7, for caption, note and comment style: fact IDs and sources go in HTML comments),
  `ROOT\paper\draft\GLOSSARY.md` (names of models and terms), `ROOT\paper\draft\tables\table_7.md` (a main-text table
  file), `ROOT\paper\draft\03_protocol.md` (Table 3, the common-rival learners), `ROOT\paper\build\BUILD_README.md`
  (how the Word build reads tables and table files).

## What the tables must hold (protocol section 10; the spec maps each item to a table)

1. **Table 9 (main text)**: one row per problem at lead 0, variable level, holding section 8's main-text row: the main
   set; Kendall's W [CI]; treeroute against its same-link rivals: the median of the top-20-union Spearman [CI] and the
   range; RBO (p 0.9) of treeroute against the rivals' consensus [CI]; treeroute's top 3; the consensus top 3; the
   own-history share of treeroute [CI] and of the median rival [CI]. Rulings: BB1 (fire's treeroute top 3 and
   own-history share [CI] come from `V\A\results.json`; a note under the table says so); BB4 (a family with no variable
   keeps its defined 0 with a label: coral's own-history shares "0.00 [0.00, 0.00]" with "(no own-history input)"; the
   median column is labelled "median of the rivals" in every row: defo and PM2.5 LightGBM's share, NDVI the mean of
   the two middle of four shares; check coral's and fire's cells in `AW4_main_row.json` and `V\A\results.json`; a
   one-line note that PM2.5's RBO against the consensus has an asymmetric interval because the consensus's top variable
   changes across draws). Fire's
   main set is treeroute alone (every rival is log_c or log mu), so its W and the treeroute-against-rival cells are
   undefined or empty by design: section 8 says the fire row states that treeroute-against-rival agreement cannot
   separate the link from the model.
2. **AW3 tables per problem, both levels**: every pair x section 8's pair statistics with percentile 95% intervals;
   same-link and cross-link pairs labelled (cross-link: "not comparable in scale or rank"); declined rivals labelled;
   the sign agreement with its count and, by BB1, its interval and number of finite replicates from `V\A\results.json`
   (fire's three thin intervals, all at the variable level against treeroute, printed with their finite counts:
   ridge 64 (its full-sample value undefined), LightGBM 1,140, RF 1,380; all [0, 1]); by BB2 the feature-level
   family-share distance is the variable-level value repeated, with a note; Kendall's W and the mean pairwise Spearman
   of the main set with intervals; each model's stability under region resampling. NDVI's pairs with BARDL are kept,
   with the BB3 footnote: BARDL gives exactly 0 to 93 of the 96 variables of J (it reads three variables, nine
   columns), so its top-k sets are filled by name order (code-point ascending), at both levels; the footnote gives
   each statistic's largest move under other collations (from `bardl_maxima.txt`, rounded once) and an example
   (Jaccard top 5 with treeroute: 0.25, or 0.11 without the tie-only `aet_total_mm`).
3. **Each model's top 10 with shares**, per problem and level; no intervals (BB5).
4. **Family shares per model** (variable level; no intervals for the main models, BB5), with the BB4 labels: coral's
   own history "(no own-history input)", defo's context and calendar "0.0%" with "(no context or calendar input)".
5. **Arcsine models' nonzero-forecast view** (fire; section 8), as the compare files hold it.
6. **The AW4 statistics** per problem (everything behind Table 9, with the range of the top-20-union Spearman).
7. **The exactness gates** per problem and model: the S-EXACT outcome (rows bit-equal, largest difference), the
   additivity error, S-ZERO, the guard (passed or declined), treeroute's E-gates with E5 marked informational (the
   rebuilt bank's fingerprint differs at coral; every checked prediction matches), from the run records. What each
   gate is: PROTOCOL sections 4 and 11, RUN_COMMANDS.md.
8. **Rivals covered and left out**, with reasons (PROTOCOL section 7; `ROOT\engine\PENDING_PARTS.md` Part 628, "Rivals
   covered" and "Left out"): per problem, each explained model with its link, its guard outcome and whether it is in
   the main set; each left-out rival with its reason.
9. **treeroute's B1 sensitivity** (protocol section 10, the B1 list; report A6 shows one layout): for fire, PM2.5 and
   NDVI, the pair (main run, B1 run) at both levels under section 8's pair statistics with intervals and finite
   replicates; B1's family shares with intervals; its top 3 and own-history share [CI]; its top 10 with shares (no
   interval); counts without intervals (nonzero players; signs determined in both runs, and of those that agree); B1's
   feature-level family-share distance, which equals its variable-level value (the BB2 exception). Defo: the identity
   check only (largest difference exactly 0 at both levels, same rows, players and variables). Every B1 run's (defo's
   included) background pairs and total and tree-SHAP seconds, from the logs. B1 is never pooled with the main set: it
   enters no W, consensus, main-set statistic or main-text row and is compared with no rival.
10. **The samples and active sets**: per problem the rows, regions and units of the registered sample, and per level
    the number of players, the size of J and the structural zeros.

## Decisions the spec must make and state

Table numbering (S3.18 onward, in the order the tables will appear in S3.13; propose the order) and short caption
titles (the text writers polish them later); columns; row order (state the rule, for example the pairs sorted as
`pairs.parquet` or by display name); display names (models as GLOSSARY.md names them, with the data name where a reader
needs it; variables keep their data names); number formats (start from compare_shap's printouts: statistics with two
decimals, "0.70 [0.63, 0.76]"; shares in percent with one decimal; sign agreement "1.00 (10 signs)"; give a reason for
any change); how undefined values print, with the reason in a note; how the BB1 cells are marked (for example a symbol
and a note "from the independent re-computation; A = B"); when the number of finite replicates is printed (for
example only when it is below 2,000); the exact draft note texts that carry rulings BB1-BB6 (the writers may polish
the wording, never the numbers). Every cell type gets its source (file and key or column) and its format string. The
spec must be complete enough that two independent builders produce byte-identical Markdown.

## Rules

- Read-only on every existing file; write only in your own folder (named in your task). Python only as
  `py -3.9 -I -B <script>`; no pip.
- Never open `SHAP\smoke\bardl_fix\`. Never Grep or Glob over SHAP with a `*.md` pattern (open named files only). Run
  no script of `SHAP\scripts`, `V` or `V\_lead\scripts`.
- Builders compute every printed number from the stored values (`compare\` parquet and json files, `V\A\results.json`,
  `bardl_maxima.txt`, the logs and run records) and do NOT open `AW3_table.md`, `AW4_table.md`, `report.md` or the
  other builder's folder; only the spec writer and the reconciler read the printouts.
- Never write user names, e-mail addresses, user-folder names, host names, session ids or workflow ids into any file
  or output. Do not write a file named like a report; return what you are asked for as the structured output.
- Plain, exact words; no claim beyond the sources.
