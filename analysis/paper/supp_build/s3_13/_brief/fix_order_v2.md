# Change order for version 2 of the S3.13 tables (2026-11-17)

Names as in `brief_tables.md`: SHAP, V, ROOT, OUT. The first check of version 1 (`OUT\reconcile\tables_agreed.md`,
SHA-256 5f414a11...beae03) found no wrong number, and ten wording problems. This order fixes them, and the gaps that
the builders and the reconciler reported in the spec. **No number changes.** Every printed number of version 2 must
equal the version-1 number of the same cell. The only changes are the texts below, one row dropped from Table S3.18 b
and one note line added there.

Each change gives the printed text of version 1 (OLD) and of version 2 (NEW). Where the spec makes the text from a
template (for example one caption template for Tables S3.23-S3.27), change the template so that it prints NEW in
every table named.

## C1. What a share is measured against (the major finding)

The family shares (`families.parquet`, and A's B1 family shares) are each family's mean absolute attribution divided
by the sum over the five families, where a family's attribution on a row is the sum of its variables' phi on that row
(PROTOCOL section 8). The top-k shares are a player's mean absolute SHAP value divided by the sum over J. Version 1's
captions gave the second basis for both.

- Table 9 caption. OLD: `Own-history share: the share of a model's total mean absolute SHAP value that goes to the
  location's own lagged labels.` NEW: `Own-history share: the share of the own-history family (the location's own
  lagged labels) in the sum of the model's five families' mean absolute attributions, a family's attribution on a row
  being the sum of its variables' SHAP values; it is not the sum of the own-history variables' shares.`
- Captions of Tables S3.23, S3.24 and S3.26. OLD: `Shares are of a model's total mean absolute SHAP value over J,
  without intervals, as in the comparison's files.` NEW: `Top-10 shares (d, e) are of a model's total mean absolute
  SHAP value over J; family shares (f) are of the sum of its five families' mean absolute attributions, a family's
  attribution on a row being the sum of its variables' SHAP values; neither has an interval, as in the comparison's
  files.`
- Captions of Tables S3.25 and S3.27 (they have panel g). OLD: the same sentence. NEW: `Top-10 shares (d, e, g) are of
  a model's total mean absolute SHAP value over J (g: on its rows with a forecast above 0); family shares (f) are of
  the sum of its five families' mean absolute attributions, a family's attribution on a row being the sum of its
  variables' SHAP values; none has an interval, as in the comparison's files.`
- Caption of Table S3.29. OLD: `Shares are of the B1 run's total mean absolute SHAP value over the pair's J.` NEW:
  `Top-3 and top-10 shares are of the B1 run's total mean absolute SHAP value over the pair's J; family shares and the
  own-history share are of the sum of its five families' mean absolute attributions, a family's attribution on a row
  being the sum of its variables' SHAP values.`
- Spec sections 4.1, 4.7 and 4.9 (and any other place in the spec that defines a share in prose): state the two bases
  as above.

## C2. Which script checks the rivals (Table S3.20, notes a and b)

- Note ᵃ. OLD: `The comparison script checks a rival's pre-clip column only (–: not read).` NEW: `The rivals' SHAP
  script (rival_shap.py) checks a rival's pre-clip column only (–: not read).`
- Note ᵇ. OLD: `The comparison script's own check of its row-by-row copy of the design,` NEW: `The rivals' SHAP
  script's own check of its row-by-row copy of the design,` (the rest of the note is unchanged).

## C3. NDVI's BARDL footnote (Table S3.24, note ‡)

- OLD: `Its top-5, top-10 and top-20 sets are therefore filled by name order, the tie rule applied in code-point
  ascending order, at both levels, and the cells of its pairs that use those sets depend on that order.` NEW: `Beyond
  its three variables (variable level) and nine columns (feature level), its top-5, top-10 and top-20 sets are
  therefore filled by name order, the tie rule applied in code-point ascending order, and the cells of its pairs that
  use those sets depend on that order.`
- OLD: `Under the other two orders tried (case-insensitive ascending, and descending), the largest move of each
  statistic over BARDL's eight pair-levels is:` NEW: `Across the three orders tried (code-point ascending, as printed;
  case-insensitive ascending; and descending), the largest spread (highest minus lowest value) of each statistic over
  BARDL's eight pair-levels is:` (the six values, the pair-levels named and the example are unchanged:
  `V\_lead\outputs\bardl_maxima.txt` gives spreads over the three values).

## C4. Rivals left out (Table S3.18 b) and coral's B1 (Table S3.30)

- Drop the row `| Coral bleaching | CRW Outlook | ... |` from panel b: the CRW Outlook is a rival at forecast leads
  only (Table 7, `ROOT\paper\draft\tables\table_6.md`; check which), so it is outside this nowcast comparison.
- The baselines row. OLD: `| All five | The baselines: the seasonal normal, the last-5-years normal, predict-zero,
  persistence and damped persistence; on coral bleaching the training median and the last visit | No input feature:
  there is no SHAP value to compute. |` NEW: `| All five | The naive baselines at the nowcast: the arithmetic and
  last-5-years normals and predict-zero; on coral bleaching, which has no per-location normal, the training median and
  predict-zero | No input feature: there is no SHAP value to compute. |` (Sources: Section 3.3 of the paper,
  `ROOT\paper\draft\03_protocol.md`: persistence and damped persistence are baselines at the forecast leads only;
  Table 4a note ᵈ, `ROOT\paper\draft\tables\table_3.md`: coral bleaching has no normal baselines.)
- Add one note line directly after the panel b table, before the line that starts `ᵃ Failed`: `Panel b lists the
  rivals of the nowcast; rivals that run only at forecast leads (Table 7), among them the CRW Outlook, are outside this
  comparison, which explains the nowcast only.`
- Table S3.30 note. OLD: `Coral bleaching: B1 is not defined (its router reads a pool of other sites' survey visits),
  so it has no B1 run.` NEW: `Coral bleaching: B1 is not defined, so it has no B1 run.` (PROTOCOL section 5 says only
  "Not defined for coral".)

## C5. Table S3.22, row label

- OLD row label: `Rivals in another link`. NEW: `Guard-passing rivals in another link`. The cells are unchanged (AW4
  `cross_link_models`); Ridge stays in the next row, `Rivals declined by their skill guard`.

## C6. Table S3.21, gate E10 and note a

- E10, column "What it checks". OLD: `exported trees and evaluator reproduce the engine's tree answers bit for bit`
  NEW: `exported trees and evaluator reproduce the engine's tree answers bit for bit, on one sampled location's fit and
  test rows (forest loss: every sampled location; coral bleaching: one visit's pool and test row)`. The five cells are
  unchanged. (Sources: each `gates.json` E10 `values.unit`; PROTOCOL section 4.1, E10.)
- Note ᵃ. OLD: `while every checked prediction matches (E5a, E8, E10); the cause is not established.` NEW: `while every
  checked tree answer and prediction matches: bit for bit (E5a, E10, and E8 on the identity and log(y + c) arms), and
  within the D8 tolerance on the arcsine arms (E8); the cause is not established.`

## C7. The sign-agreement note (Tables S3.23-S3.27)

- OLD: `and, where fewer than 2,000, the number of draws on which the statistic is defined. Undefined: no player
  qualifies on the full sample.` NEW: `and, where the statistic is defined on 1 to 1,999 of the 2,000 draws, that
  number of draws. Undefined: no player qualifies on the full sample; printed without an interval, it is undefined on
  every draw.`

## C8. Table S3.22, note d (ruling BB6; the paper's rule on AI terms)

- OLD: `was read by an agent on 2026-11-13 at about 15:31, before the independent re-computation; the re-computation's
  implementers A and B never opened it (ruling BB6).` NEW: `was read on 2026-11-13 at about 15:31, before the
  independent re-computation; the re-computation's implementers A and B never opened it (ruling BB6; Supplement S1.7
  records who read it).` The supplements outside S1 and S4 use no AI term and no "agent"; S1 says who read it.

## C9. The header comment (line 1)

- Add, after its first sentence: `Version 2 (2026-11-17, after the first check): ten captions and notes reworded, one
  row of Table S3.18 b dropped and one note line added; no number changed.` The phrase "every printed number is
  listed in cells.json beside this file" stays; the reconciler places the agreed cells.json beside the agreed file.

## G. Gaps in the spec that the builders and the reconciler reported (close them in the spec)

- G1, cells.json `part` names. A cell that prints one number and has no named part uses `value`; the family shares of
  panel f in Tables S3.23-S3.27 use `share`, as the other shares printed without an interval (panels d, e and g;
  Table S3.29 c and d); interval cells with no named parts use `value`, `ci_low`, `ci_high`, and `n_finite` when it
  is printed. With this, the two builders' cells.json files must be byte-identical.
- G2, source text formats. `SHAP\SAMPLE_REGISTER.txt` and the `tr_shap_<p>_lead0.log` files have CRLF line ends;
  `V\_lead\outputs\bardl_maxima.txt` has a UTF-8 byte-order mark and CRLF. Read them as text with universal newlines
  and encoding `utf-8-sig`; line numbers in selectors count from 1 after that; the 'done in' regex is applied to the
  line without its line end.
- G3, Table S3.21 E3m: the selector is `len(gates.E3m_recorded_path_map.values.files)`.
- G4, Table S3.22, coral bleaching, "Own-history share of each same-link rival": the BB4 label is appended once, at the
  end of the joined cell, as both builders printed it. State this in the cell rule.

## What does not change

Every number, interval, count, mark, panel, column and row other than those named above; the table numbering; the
order of tables, panels, rows and columns; the source comments (apart from what a changed text needs).
