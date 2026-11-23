# Change order for version 3 of the S3.13 tables (2026-11-17)

Names as in `brief_tables.md`: SHAP, V, ROOT, OUT. The second check of version 2 (`OUT\reconcile\tables_agreed.md`,
SHA-256 a7710171...6570c9) found no wrong number and closed every change of version 2; it left seven minor wording
points, and a scan of the tables' prose against `ROOT\paper\draft\GLOSSARY.md` found terms the paper does not use.
This order fixes them. **No number changes, and no line is added or dropped**: every printed number of version 3 must
equal the version-2 number of the same cell, and tables.md keeps its 785 lines. The lead checked every source named
below before writing this order.

Each change gives the printed text of version 2 (OLD) and of version 3 (NEW), each in one code span (wrapped lines
join with one space). Where the spec makes a text from a template or states it in more than one place, change every
place, so that a builder prints NEW everywhere the order names.

## V3-1. Importances and shares: the region weighting; Table 9's families

PROTOCOL section 8 (L496): `I_m(j): the region-weighted mean |phi_ij| (each region weighs 1)`; the family shares
(families.parquet), panel g and A's B1 values are region-weighted too (second check, k08_share_bases.py; a plain mean
would change 84 of the 250 printed top-10 shares). Families: PROTOCOL L491-493. Own-history features: GLOSSARY
("Engine-built lags and trailing means of the location's own labels"; "lagged target" is a do-not-use name).

- Table 9 caption, a new sentence directly after `(forest loss, annual: all of them; coral bleaching: other sites'
  survey visits).` NEW: `A variable's importance to a model is its mean absolute SHAP value over the sample, with
  each region weighted equally; rankings order the variables by importance.`
- Table 9 caption. OLD: `RBO: rank-biased overlap of treeroute v1's full ranking with the rivals' consensus (the mean
  of their shares).` NEW: `RBO: rank-biased overlap of treeroute v1's full ranking with the rivals' consensus (the
  mean of their importance shares).`
- Table 9 caption. OLD: `Own-history share: the share of the own-history family (the location's own lagged labels)
  in the sum of the model's five families' mean absolute attributions, a family's attribution on a row being the sum
  of its variables' SHAP values; it is not the sum of the own-history variables' shares.` NEW: `Own-history share: the
  share of the own-history family in the sum of the mean absolute attributions of the model's five families (with
  each region weighted equally), a family's attribution on a row being the sum of its variables' SHAP values; it is
  not the sum of the own-history variables' shares. The five families are own history (the lags and trailing means of
  the location's own labels), global indices, local drivers, context and calendar, and the seasonal normal.`
- Table S3.19 caption. OLD: `J: the players to which some model gives more than 10⁻¹² of its total mean absolute
  SHAP value; the others are structural zeros.` NEW: `J: the players to which some model gives more than 10⁻¹² of its
  total mean absolute SHAP value (with each region weighted equally); the others are structural zeros.`
- Captions of Tables S3.23, S3.24 and S3.26 (the `{shares_sentence}` value with `(d, e)`). OLD: `...the sum of its
  variables' SHAP values; neither has an interval, as in the comparison's files.` NEW: `...the sum of its variables'
  SHAP values; both means weight each region equally, and neither share has an interval, as in the comparison's
  files.` (The text before `the sum of its variables' SHAP values` is unchanged.)
- Captions of Tables S3.25 and S3.27 (the value with `(d, e, g)`). OLD: `...the sum of its variables' SHAP values;
  none has an interval, as in the comparison's files.` NEW: `...the sum of its variables' SHAP values; both means
  weight each region equally, and no share has an interval, as in the comparison's files.`
- Caption of Table S3.29. OLD: `...a family's attribution on a row being the sum of its variables' SHAP values. From
  the independent re-computation (two implementations that agree).` NEW: `...a family's attribution on a row being
  the sum of its variables' SHAP values; both means weight each region equally. From the independent re-computation
  (two implementations that agree).`
- Spec sections 4.1, 4.7 and 4.9, and any other place where the spec defines an importance or a share in prose:
  state the region weighting, citing PROTOCOL section 8.

## V3-2. Table S3.18: the naive baselines and the references

GLOSSARY: "naive baseline" (`... the arithmetic and last-5-years normals, predict-zero, persistence and damped
persistence (and, among the candidates for the best naive baseline, each link's trees-off fit)`), "best naive
baseline", "trees-off fit" (`it equals that link's normal exactly`), "reference" (`An arm's own-link trees-off fit
(the training median on coral)`), "training median" (`coral's reference and decline target`). Version 2's row listed
the arithmetic normal only, so PM2.5's and forest loss's reference (the geometric normal) and burned fraction's (the
arcsine-scale normal) were missing.

- Caption. OLD: `The models explained at the nowcast (a), and the rivals left out, with the reason (b).` NEW: `The
  models explained at the nowcast (a), and the rivals and naive baselines left out, with the reason (b).`
- Panel b label. OLD: `**b. Rivals left out.**` NEW: `**b. Rivals and naive baselines left out.**`
- The baselines row. OLD: `| All five | The naive baselines at the nowcast: the arithmetic and last-5-years normals
  and predict-zero; on coral bleaching, which has no per-location normal, the training median and predict-zero | No
  input feature: there is no SHAP value to compute. |` NEW: `| All five | The naive baselines at the nowcast: the
  arithmetic and last-5-years normals, predict-zero and each link's trees-off fit, which equals that link's normal
  exactly and is the reference of the arms in that link; on coral bleaching, which has no per-location normal, the
  training median (its reference) and predict-zero | No input feature: there is no SHAP value to compute. |`
- The note line after panel b. OLD: `Panel b lists the rivals of the nowcast; rivals that run only at forecast leads
  (Table 7), among them the CRW Outlook, are outside this comparison, which explains the nowcast only.` NEW: `Panel b
  lists the nowcast's rivals and naive baselines that have no SHAP value; rivals that run only at forecast leads
  (Table 7), among them the CRW Outlook, are outside this comparison, which explains the nowcast only.`
- The caption's source comment. OLD: `engine/PENDING_PARTS.md Part 628 (methods; rivals left out and why); rulings
  AW2, AY1, BA1` NEW: `engine/PENDING_PARTS.md Part 628 (methods; rivals left out and why);
  paper/draft/03_protocol.md Section 3.3, paper/draft/tables/table_3.md note d and paper/draft/GLOSSARY.md (naive
  baseline, trees-off fit, reference) for the naive baselines; paper/draft/tables/table_6.md (Table 7) for the rivals
  at forecast leads only; rulings AW2, AY1, BA1`

## V3-3. The AW3 captions' count clause; one source comment

- Captions of Tables S3.23-S3.27 (the template). OLD: `with the number of finite draws where a statistic is defined
  on fewer of them` NEW: `with the number of finite draws where a statistic is defined on 1 to 1,999 of them` (as the
  sign-agreement note of version 2 says: a statistic defined on no draw prints no count).
- Table S3.24's source comment (`{extra_src}`). OLD: `(the collation moves of the footnote, ruling BB3)` NEW: `(the
  spreads of the footnote, ruling BB3)`

## V3-4. NDVI's BARDL footnote (Table S3.24, note ‡): RBO reads the whole ranking

PROTOCOL section 8 (L506-510): Spearman on average ranks over J and over the union of the two top-20 sets; Jaccard of
the top-k sets, ties broken by name; RBO on the full rankings over J, ties broken by name.
`V\_lead\outputs\bardl_ties.txt` gives every BARDL pair-level's values under the three orders (for example RBO
p = 0.9, variable level, LightGBM vs BARDL: 0.2027 / 0.2027 / 0.2524).

- OLD: `Beyond its three variables (variable level) and nine columns (feature level), its top-5, top-10 and top-20
  sets are therefore filled by name order, the tie rule applied in code-point ascending order, and the cells of its
  pairs that use those sets depend on that order.` NEW: `Beyond its three variables (variable level) and nine columns
  (feature level), its ranking is therefore filled by name order, the tie rule applied in code-point ascending order,
  and so are its top-5, top-10 and top-20 sets where they reach that far; the cells of its pairs that read that part
  of its ranking (the Jaccard similarities, the top-20-union Spearman and the RBO) depend on that order.`

## V3-5. Table S3.22, row label (GLOSSARY: "guard" is a do-not-use name of the skill guard)

- OLD row label: `Guard-passing rivals in another link`. NEW: `Rivals in another link that passed their skill guard`.
  The cells are unchanged.

## V3-6. Terms the paper does not use (GLOSSARY, column 2)

- Tables S3.18 a and S3.20, the five treeroute v1 rows of each. OLD: `passed (the kept arm)` NEW: `passed (the adopted
  arm)` (the paper's term; S3.18 a already says `the adopted arm: tree bank and router`).
- Table S3.21, first row label. OLD: `Kept arm` NEW: `Adopted arm`. Its "What it checks" text and cells are unchanged.
- Table S3.18 a, the five random-forest rows. OLD: `random forest, rebuilt from the board's records` NEW: `random
  forest, rebuilt from the rival board's records`.
- Table S3.19, note ᶜ. OLD: `coral bleaching: the visit's saved pool of other sites' visits.` NEW: `coral bleaching:
  the survey visit's saved router fit rows, a pool of other sites' survey visits.` ("visit" and "pool" are do-not-use
  names of "survey visit" and "router fit rows"; GLOSSARY's router fit rows: `(a pool on coral)`.)
- Table S3.21, E10's "What it checks". OLD: `on one sampled location's fit and test rows (forest loss: every sampled
  location; coral bleaching: one visit's pool and test row)` NEW: `on one sampled location's router fit rows and test
  rows (forest loss: every sampled location; coral bleaching: one survey visit's router fit rows and test row)`.
- Table S3.25, every pair label that carries it (panels a and b; Ridge's pairs). OLD: `; raw model, declined by its
  guard: ` NEW: `; raw model, declined by its skill guard: `. The source's pair label (pairs.parquet) keeps its own
  words: check 3.3 compares the source label with the composed form first, and the printed form then uses NEW.
- Table S3.21, E3a's "What it checks". OLD: `inputs before the read equal the manifest's (package, groups, constants,
  file lists, features)` NEW: `inputs, before the labels are read, equal the manifest's (dataset package, regions,
  constants, file lists, features)` (PROTOCOL L175: the engine's "groups" are the regions).
- Table S3.21, E3m's "What it checks". OLD: `a moved package file has the content, size and time that the freeze locks
  record (path map)` NEW: `a moved dataset package file has the content, size and time that the run's locks record
  (path map)` ("freeze" is a do-not-use name of "lock").
- Table S3.21, E3's "What it checks". OLD: `package fingerprint, derived settings and run fingerprint after the derive`
  NEW: `dataset package fingerprint, the settings that the written rules set, and run fingerprint, after the written
  rules are applied` ("derived settings" and "derive" are do-not-use names of "written rules").
- Table S3.21, E6's "What it checks". OLD: `c and the guard tolerances equal the run's records` NEW: `c and the
  identity tolerances (one per link) equal the run's records`. (Sources: `SHAP\scripts\tr_rebuild.py` L702 and
  L745-746, E6 compares the record of the engine's `guard_tolerances`; `ROOT\engine\treeroute\pipeline\stages.py`
  L174-180, that function is rule R36's tolerance, one per link; GLOSSARY "identity tolerance", other name "guard
  tolerance (C9 name)". Read these files, never run or edit them.)

## V3-7. Bookkeeping texts

- Header comment (line 1). OLD: `Version 2 (2026-11-17, after the first check): ten captions and notes reworded, one
  row of Table S3.18 b dropped and one note line added; no number changed.` NEW: `Version 2 (2026-11-17, after the
  first check): ten captions and notes and three table cells reworded, one row of Table S3.18 b dropped and one note
  line added; no number changed. Version 3 (2026-11-17, after the second check): captions, notes, labels, cells and
  source comments reworded, as paper/supp_build/s3_13/spec/CHANGES_v3.md lists; no number changed.`
- Header comment (line 1). OLD: `every printed number is listed in cells.json beside this file.` NEW: `every printed
  data number is listed in cells.json beside this file (the constants of the fixed texts, such as 1,000 and 2,000,
  are not).`
- Spec, section 5: add that cells.json's `tables_file` names the builders' `tables.md`, of which
  `OUT\reconcile\tables_agreed.md` is a byte copy with the same lines.
- `OUT\spec\CHANGES_v2.md`: correct "786 lines" to 785 and complete its list of added number tokens (Top-10 x6, Top-3,
  `above 0` x2, the E8 and D8 of Table S3.21 note ᵃ, `Version 2`), each correction marked "(corrected in version 3)".
- Write `OUT\spec\CHANGES_v3.md` as CHANGES_v2.md was written, and add "## 10. Version 3 (2026-11-17)" to the spec.

## Outside this order

Table S3.22 note ᵈ says that Supplement S1.7 records who read coral's AW4_table.md; the write-up adds that S1.7 row
(it is checked there). Nothing in the tables changes for it.

## What does not change

Every number, interval, count, mark, panel, column and row; the line count (785); the table numbering; the order of
tables, panels, rows and columns; every text not named above.
