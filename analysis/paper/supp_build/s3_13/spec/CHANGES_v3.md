# Changes to the table spec, version 2 to version 3 (2026-11-17)

Names as in the spec: SHAP = `D:\treeroute\analysis\shap_v1`; V = `SHAP\verify_v1`; ROOT = the research-paper folder;
OUT = `ROOT\paper\supp_build\s3_13`. Change order: `OUT\_brief\fix_order_v3.md` (V3-1 to V3-7), written after the
second check of version 2 (`OUT\reconcile\tables_agreed.md`, SHA-256
a771017173f7c891b56467bd8dab220d586089e66d8955627a900fb0456570c9, 785 lines, a byte copy of both builders' tables.md).

- Version 2: `OUT\spec\TABLE_SPEC_v2.md`, a byte copy of `TABLE_SPEC.md` made before any edit (SHA-256 of both equal:
  2046c58a7aa787c15d6cd90b1353a513f6ef28dbff517a4531fa58b09ad30f02; 1,301 lines). Version 1 stays
  `OUT\spec\TABLE_SPEC_v1.md` (979be5ed...7cf9fb), unchanged.
- Version 3: `OUT\spec\TABLE_SPEC.md` (SHA-256 573cc04e149d8d921e41aff285938ecb8a3b819f2d1c020b1f8ad816ead8da31; 1,368
  lines). UTF-8 without BOM, LF only, as version 2.
- "v2 L" is a line of version 2, "v3 L" a line of version 3. S10 is this maintenance's own id: the new section 10 and
  its entry in the contents line.
- Checks (all in `OUT\spec\`, read-only, print only; `py -3.9 -I -B <script>` from that folder):
  `s13_diff_v2_v3.py` replays the 37 listed edits on version 2 and finds version 3 equal to the result plus section
  10, byte for byte; every changed line belongs to a listed change; 63 fenced blocks in both versions.
  `s14_check_new_texts.py` builds the expected version 3 of tables.md from `OUT\reconcile\tables_agreed.md` and the
  order's OLD and NEW texts (27 OLD, 28 NEW, wrapped lines joined by one space; for the items whose texts start with
  "...", the changed tail), instantiates the spec's changed texts (9 fenced blocks; the S3.23-S3.27 caption template
  with its placeholder values; the NDVI footnote with its data placeholders; the constant cells outside fenced
  blocks; the Link cell rule of 4.7 applied to the source labels) and finds each equal to its expected line: 45 lines
  of tables.md change, all 45 produced by a checked spec text.
  `s15_source_checks_v3.py` prints the source lines behind the order's claims; `s16_v2_number_tokens.py` counts the
  lines of tables.md in versions 1 and 2 and the number tokens that version 2 added (the two corrections of
  CHANGES_v2.md); `s17_check_changes_v3.py` checks every fenced text of this file against the file it is quoted from.

## What a builder does differently (summary)

1. Copy the changed fixed texts of the fenced blocks: the header comment (V3-7); the captions of Table 9, S3.19 and
   S3.29 (V3-1) and of S3.18 with its source comment (V3-2); the panel b label of S3.18 (V3-2), the baselines row
   inside the panel b block (V3-2) and the first line of S3.18's notes (V3-2); note ᶜ of S3.19 (V3-6); the NDVI ‡ note
   (V3-4). Blocks 14 and 16 have a new first line (see "Fenced blocks").
2. S3.23-S3.27 captions: the template's count clause (V3-3), the value of `{extra_src}` (V3-3) and the two values of
   `{shares_sentence}` (V3-1) changed; no placeholder is added or removed.
3. Constant cells outside fenced blocks: treeroute's skill-guard cell in S3.18 a and in S3.20, `passed (the adopted
   arm)`; the random forest's "Model and SHAP method" in S3.18 a; the first cell of S3.21's first row, `Adopted arm`,
   and the "What it checks" cells of E3a, E3m, E3, E6 and E10 (all V3-6); the S3.22 row label (V3-5).
4. S3.25's Link cells: the rule of 4.7 now prints `; raw model, declined by its skill guard: ` where the source label
   holds `; raw model, declined by its guard: ` (V3-6). Check 3.3 still compares the source label (pairs.parquet) with
   the source's own words, as before.
5. cells.json: the 12 entries of the NDVI ‡ note (tables.md line 344) get the new note line as `cell`; nothing else
   in cells.json changes. Section 5 now says what `tables_file` names (V3-7); its value stays `tables.md`.

## Expected effect on the outputs (against version 2)

- tables.md keeps its 785 lines; no line is added or dropped, so every cells.json `line` is unchanged. The lines that
  change (1-based, 45): 1, 5, 22, 28, 30, 32, 34, 37, 39, 42, 44, 47, 49, 54, 65, 67, 71, 83, 95, 99, 104, 109, 114,
  130, 134, 135, 136, 140, 144, 155, 174, 256, 344, 348, 354, 358, 359, 360, 369, 373, 374, 375, 457, 548, 711.
- cells.json keeps its 4,859 entries, in the same order, with the same `line`, `table`, `panel`, `row`, `column`,
  `part`, `printed`, `source`, `selector` and `stored`. The only change: the `cell` of the 12 entries on line 344
  (S3.24 note ‡). The other entries on changed lines (lines 95, 99, 104, 109, 114 of S3.20; 135 and 144 of S3.21;
  354, 358-360, 369 and 373-375 (corrected in version 4) of S3.25) keep their `cell`, a cell that does not change.
  The `spec` key stays `OUT\spec\TABLE_SPEC.md`.
- No printed number changes. The number tokens that the changes add are constants of the texts only (none is
  removed): on line 1, "Version 3", the date and the path `paper/supp_build/s3_13/spec/CHANGES_v3.md`, and "1,000 and
  2,000" (V3-7); on line 22, `paper/draft/03_protocol.md Section 3.3`, `table_3.md` and `table_6.md (Table 7)` (V3-2);
  "1 to 1,999" in each of the five AW3 captions (V3-3); `top-20` of "the top-20-union Spearman" in the NDVI footnote
  (V3-4). `s14_check_new_texts.py` lists them line by line.

## Fenced blocks

None added or removed: 63 in both versions, in the same order. Blocks whose content changed (number = position in
the file; v2 L / v3 L of the opening fence):

| Block | v2 L / v3 L | Table | Change | First line |
|---|---|---|---|---|
| 4 | 308 / 308 | header comment | V3-7: one sentence reworded, one added; one clause reworded | same start |
| 8 | 415 / 416 | Table 9 caption | V3-1 | same start |
| 11 | 472 / 479 | S3.18 caption | V3-2: caption and source comment | same start |
| 14 | 512 / 519 | S3.18 panel b label | V3-2 | NEW: `**b. Rivals and naive baselines left out.**` (was `**b. Rivals left out.**`) |
| 15 | 516 / 523 | S3.18 panel b table | V3-2: the baselines row (its last line) | unchanged |
| 16 | 531 / 538 | S3.18 notes | V3-2: the first line | NEW: `Panel b lists the nowcast's rivals and naive baselines ...` (was `Panel b lists the rivals of the nowcast; ...`) |
| 17 | 543 / 550 | S3.19 caption | V3-1 | same start |
| 19 | 570 / 577 | S3.19 notes | V3-6: note ᶜ (its third line) | unchanged |
| 30 | 751 / 758 | S3.23-S3.27 caption template | V3-3 | same start |
| 42 | 882 / 890 | S3.24 ‡ note | V3-4 | same start |
| 50 | 979 / 987 | S3.29 caption | V3-1 | same start |

A builder that finds a block by its position and the start of its first line must use the new first line for blocks
14 and 16. Every other changed block keeps its first 24 characters.

---

## V3-1. Importances and shares: the region weighting; Table 9's families

Spec lines: v2 416 -> v3 417 (Table 9 caption, block 8); v2 452 -> v3 453-459 (4.1, the paragraph on the two
bases); v2 544 -> v3 551 (S3.19 caption, block 17); v2 760-761 and 763 -> v3 767-768 and 770 (4.7, the
`{shares_sentence}` bullet and its two values); v2 769 -> v3 776-777 (4.7, the paragraph on the two bases); v2 980 ->
v3 988 (S3.29 caption, block 50); new v3 1025-1026 (4.9, the paragraph on the two bases); v2 1191-1193 -> v3
1203-1205 (decision 12).

Table 9 caption, the new sentence, directly after `(forest loss, annual: all of them; coral bleaching: other sites'
survey visits).` (NEW printed text):

```
A variable's importance to a model is its mean absolute SHAP value over the sample, with each region weighted equally; rankings order the variables by importance.
```

Table 9 caption, OLD printed text:

```
RBO: rank-biased overlap of treeroute v1's full ranking with the rivals' consensus (the mean of their shares).
```

NEW printed text:

```
RBO: rank-biased overlap of treeroute v1's full ranking with the rivals' consensus (the mean of their importance shares).
```

Table 9 caption, OLD printed text:

```
Own-history share: the share of the own-history family (the location's own lagged labels) in the sum of the model's five families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values; it is not the sum of the own-history variables' shares.
```

NEW printed text:

```
Own-history share: the share of the own-history family in the sum of the mean absolute attributions of the model's five families (with each region weighted equally), a family's attribution on a row being the sum of its variables' SHAP values; it is not the sum of the own-history variables' shares. The five families are own history (the lags and trailing means of the location's own labels), global indices, local drivers, context and calendar, and the seasonal normal.
```

S3.19 caption, OLD printed text:

```
J: the players to which some model gives more than 10⁻¹² of its total mean absolute SHAP value; the others are structural zeros.
```

NEW printed text:

```
J: the players to which some model gives more than 10⁻¹² of its total mean absolute SHAP value (with each region weighted equally); the others are structural zeros.
```

Captions of S3.23, S3.24 and S3.26, the end of the `{shares_sentence}` value with "(d, e)" (the text before it is
unchanged), OLD printed text:

```
the sum of its variables' SHAP values; neither has an interval, as in the comparison's files.
```

NEW printed text:

```
the sum of its variables' SHAP values; both means weight each region equally, and neither share has an interval, as in the comparison's files.
```

Captions of S3.25 and S3.27, the end of the value with "(d, e, g)", OLD printed text:

```
the sum of its variables' SHAP values; none has an interval, as in the comparison's files.
```

NEW printed text:

```
the sum of its variables' SHAP values; both means weight each region equally, and no share has an interval, as in the comparison's files.
```

Caption of S3.29, OLD printed text:

```
a family's attribution on a row being the sum of its variables' SHAP values. From the independent re-computation (two implementations that agree).
```

NEW printed text:

```
a family's attribution on a row being the sum of its variables' SHAP values; both means weight each region equally. From the independent re-computation (two implementations that agree).
```

The `{shares_sentence}` bullet's first line, v2 spec text:

```
- `{shares_sentence}` (version 2, C1): fire and coral (the tables with panel g)
```

v3 spec text:

```
- `{shares_sentence}` (version 2, C1; version 3, V3-1): fire and coral (the tables with panel g)
```

The prose that defines the importances and the shares (the order: sections 4.1, 4.7 and 4.9, citing PROTOCOL
section 8). 4.1, v2 spec text:

```
`problems.fire.main_row.own_history_share_treeroute`) are family shares, not the sum of the own-history variables'
shares, as the caption says.
```

v3 spec text:

```
`problems.fire.main_row.own_history_share_treeroute`) are family shares, not the sum of the own-history variables'
shares, as the caption says. The region weighting (version 3, V3-1): every mean absolute value in the two bases
weights each region equally. A player's importance (importance.parquet `mean_abs`, by which check 3.5 ranks the
players) is the region-weighted mean of its absolute SHAP values over the sample rows, as PROTOCOL section 8 defines
it ("I_m(j): the region-weighted mean |phi_ij| (each region weighs 1)"), and the model's total is the sum of these
over J; a family's mean absolute attribution is weighted the same way (the second check,
`OUT\skeptic\k08_share_bases.py`, found this for families.parquet, panel g and A's B1 values). The captions of
Table 9 and of Tables S3.19, S3.23 to S3.27 and S3.29 state it.
```

4.7, v2 spec text:

```
families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values.
`{shares_sentence}` states both in the caption.
```

v3 spec text:

```
families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values.
Both means weight each region equally, panel g's included (version 3, V3-1; PROTOCOL section 8, as in 4.1).
`{shares_sentence}` states both bases and the weighting in the caption.
```

4.9, two lines added after the paragraph's last line, v3 spec text:

```
families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values.
Both means weight each region equally, as in the main runs (version 3, V3-1; PROTOCOL section 8, as in 4.1); the
caption says so.
```

Decision 12 quoted the old caption words. v2 spec text:

```
12. **BB5.** No interval for the main models' top-10 shares and family shares; the captions say so ("neither has an
    interval, as in the comparison's files", or "none has an interval" in the two tables with panel g). B1's family
    shares and own-history share keep their intervals; no top-k list has one.
```

v3 spec text:

```
12. **BB5.** No interval for the main models' top-10 shares and family shares; the captions say so ("neither share
    has an interval, as in the comparison's files", or "no share has an interval" in the two tables with panel g;
    version 3, V3-1). B1's family shares and own-history share keep their intervals; no top-k list has one.
```

Builder: copy the new caption blocks of Table 9, S3.19 and S3.29; fill `{shares_sentence}` with its two new values
(same placeholder, same tables: "(d, e, g)" for S3.25 and S3.27, "(d, e)" for S3.23, S3.24 and S3.26). The prose of
4.1, 4.7 and 4.9 and decision 12 change no output. Captions hold no cells.json entry, so cells.json is unchanged by
V3-1.

## V3-2. Table S3.18: the naive baselines and the references

Spec lines: v2 473 -> v3 480 (caption and its source comment, block 11); v2 513 -> v3 520 (the panel b label, block
14, whose only line is new); v2 526 -> v3 533 (the baselines row, the last line of block 15); v2 532 -> v3 539 (the
first line of the notes, block 16).

Caption, OLD printed text:

```
The models explained at the nowcast (a), and the rivals left out, with the reason (b).
```

NEW printed text:

```
The models explained at the nowcast (a), and the rivals and naive baselines left out, with the reason (b).
```

The caption's source comment, OLD printed text:

```
engine/PENDING_PARTS.md Part 628 (methods; rivals left out and why); rulings AW2, AY1, BA1
```

NEW printed text:

```
engine/PENDING_PARTS.md Part 628 (methods; rivals left out and why); paper/draft/03_protocol.md Section 3.3, paper/draft/tables/table_3.md note d and paper/draft/GLOSSARY.md (naive baseline, trees-off fit, reference) for the naive baselines; paper/draft/tables/table_6.md (Table 7) for the rivals at forecast leads only; rulings AW2, AY1, BA1
```

Panel b label, OLD printed text:

```
**b. Rivals left out.**
```

NEW printed text:

```
**b. Rivals and naive baselines left out.**
```

The baselines row, OLD printed text:

```
| All five | The naive baselines at the nowcast: the arithmetic and last-5-years normals and predict-zero; on coral bleaching, which has no per-location normal, the training median and predict-zero | No input feature: there is no SHAP value to compute. |
```

NEW printed text:

```
| All five | The naive baselines at the nowcast: the arithmetic and last-5-years normals, predict-zero and each link's trees-off fit, which equals that link's normal exactly and is the reference of the arms in that link; on coral bleaching, which has no per-location normal, the training median (its reference) and predict-zero | No input feature: there is no SHAP value to compute. |
```

The note line after panel b (the first line of the note group), OLD printed text:

```
Panel b lists the rivals of the nowcast; rivals that run only at forecast leads (Table 7), among them the CRW Outlook, are outside this comparison, which explains the nowcast only.
```

NEW printed text:

```
Panel b lists the nowcast's rivals and naive baselines that have no SHAP value; rivals that run only at forecast leads (Table 7), among them the CRW Outlook, are outside this comparison, which explains the nowcast only.
```

Builder: copy the caption block, the new panel b label (block 14: new first line), the panel b block and the notes
block (block 16: new first line). Panel b keeps its 8 rows and the note group its 3 lines, so no line of tables.md
moves; Table S3.18 has no cells.json entries.

## V3-3. The AW3 captions' count clause; one source comment

Spec lines: v2 752 -> v3 759 (the S3.23-S3.27 caption template, block 30); v2 757 -> v3 764 (`{extra_src}`).

Template, all five captions, OLD printed text:

```
with the number of finite draws where a statistic is defined on fewer of them
```

NEW printed text:

```
with the number of finite draws where a statistic is defined on 1 to 1,999 of them
```

`{extra_src}` (S3.24's source comment), OLD printed text:

```
(the collation moves of the footnote, ruling BB3)
```

NEW printed text:

```
(the spreads of the footnote, ruling BB3)
```

Builder: copy the template and the new `{extra_src}` value. CI2 and SIGN (2.6) are unchanged and already print a
count of finite draws only when 0 < `n_finite` < 2,000, as the clause now says. No entries.

## V3-4. NDVI's BARDL footnote (S3.24, note ‡)

Spec lines: v2 883 -> v3 891 (block 42); v2 284 -> v3 284 (2.8, the meaning of `‡`, a prose definition of the same
fact).

OLD printed text (the footnote's second sentence):

```
Beyond its three variables (variable level) and nine columns (feature level), its top-5, top-10 and top-20 sets are therefore filled by name order, the tie rule applied in code-point ascending order, and the cells of its pairs that use those sets depend on that order.
```

NEW printed text:

```
Beyond its three variables (variable level) and nine columns (feature level), its ranking is therefore filled by name order, the tie rule applied in code-point ascending order, and so are its top-5, top-10 and top-20 sets where they reach that far; the cells of its pairs that read that part of its ranking (the Jaccard similarities, the top-20-union Spearman and the RBO) depend on that order.
```

2.8, v2 spec text:

```
| `‡` | BARDL's top-k sets are filled by name order (footnote with the spreads over the three collations) | BB3 |
```

v3 spec text:

```
| `‡` | BARDL's ranking beyond its three variables (nine columns) is filled by name order, and so are its top-k sets where they reach that far (footnote with the spreads over the three collations) | BB3 |
```

Builder: copy the new block; its placeholders, their values and their order are unchanged (the counts, the six
spreads with their pair-levels and the example are the same numbers). The 12 note entries (row `note`, columns
`z_var`, `j_var`, `z_feat`, `j_feat`, `m_jaccard_top5`, `m_jaccard_top10`, `m_jaccard_top20`, `m_rho20`,
`m_rbo090`, `m_rbo095`, `ex_base`, `ex_desc`) get the new note line (tables.md line 344) as `cell`.

## V3-5. Table S3.22, row label

Spec line: v2 717 -> v3 724 (the row table of 4.6, not a fenced block).

OLD printed text:

```
Guard-passing rivals in another link
```

NEW printed text:

```
Rivals in another link that passed their skill guard
```

Builder: the first cell of that row (tables.md line 155); its cells (AW4 `cross_link_models`) are unchanged; no
entries.

## V3-6. Terms the paper does not use

Spec lines: v2 495 -> v3 502 (4.2, treeroute's skill-guard cell of S3.18 a); v2 630 -> v3 637 (4.4, the same cell of
S3.20); v2 504 -> v3 511 (4.2, the random forest's constant); v2 573 -> v3 580 (S3.19 note ᶜ, the third line of
block 19); v2 667, 671-673, 677 and 681 -> v3 674, 678-680, 684 and 688 (4.5, the S3.21 rows `Adopted arm`, E3a, E3m,
E3, E6 and E10, not fenced); v2 798 -> v3 806 (4.7, the Link cell rule); v2 345 -> v3 345-346 (check 3.3, which keeps
the source's words); v2 1206-1207 -> v3 1218-1219 (decision 18, which names the first row of S3.21).

S3.18 a and S3.20, the five treeroute v1 rows of each, OLD printed text:

```
passed (the kept arm)
```

NEW printed text:

```
passed (the adopted arm)
```

S3.21, first row label, OLD printed text:

```
Kept arm
```

NEW printed text:

```
Adopted arm
```

S3.18 a, the five random-forest rows, OLD printed text:

```
random forest, rebuilt from the board's records
```

NEW printed text:

```
random forest, rebuilt from the rival board's records
```

S3.19 note ᶜ, OLD printed text:

```
coral bleaching: the visit's saved pool of other sites' visits.
```

NEW printed text:

```
coral bleaching: the survey visit's saved router fit rows, a pool of other sites' survey visits.
```

S3.21, E10's "What it checks", OLD printed text:

```
on one sampled location's fit and test rows (forest loss: every sampled location; coral bleaching: one visit's pool and test row)
```

NEW printed text:

```
on one sampled location's router fit rows and test rows (forest loss: every sampled location; coral bleaching: one survey visit's router fit rows and test row)
```

S3.21, E3a's "What it checks", OLD printed text:

```
inputs before the read equal the manifest's (package, groups, constants, file lists, features)
```

NEW printed text:

```
inputs, before the labels are read, equal the manifest's (dataset package, regions, constants, file lists, features)
```

S3.21, E3m's "What it checks", OLD printed text:

```
a moved package file has the content, size and time that the freeze locks record (path map)
```

NEW printed text:

```
a moved dataset package file has the content, size and time that the run's locks record (path map)
```

S3.21, E3's "What it checks", OLD printed text:

```
package fingerprint, derived settings and run fingerprint after the derive
```

NEW printed text:

```
dataset package fingerprint, the settings that the written rules set, and run fingerprint, after the written rules are applied
```

S3.21, E6's "What it checks", OLD printed text:

```
c and the guard tolerances equal the run's records
```

NEW printed text:

```
c and the identity tolerances (one per link) equal the run's records
```

S3.25, the Link cell of every Ridge pair (panels a and b; 4 pairs each), for example, OLD printed text:

```
cross-link (not comparable in scale or rank); raw model, declined by its guard: Ridge
```

NEW printed text:

```
cross-link (not comparable in scale or rank); raw model, declined by its skill guard: Ridge
```

(and likewise `same-link; raw model, declined by its skill guard: Ridge` for Ridge's pairs with the random forest and
LightGBM). The rule of 4.7, v2 spec text:

```
with M = "; raw model, declined by its guard: ", if the label holds M, the text before M + M + the inline names (2.2) of the data names after M (split on ", ") joined by ", "; else the label as it stands.
```

v3 spec text:

```
with M = "; raw model, declined by its guard: " (the source label's words, check 3.3) and P = "; raw model, declined by its skill guard: " (the printed words; version 3, V3-6), if the label holds M, the text before M + P + the inline names (2.2) of the data names after M (split on ", ") joined by ", "; else the label as it stands.
```

Check 3.3, v2 spec text:

```
   `declined_by_guard`, `<names>` being those models' data names joined by `, `.
```

v3 spec text:

```
   `declined_by_guard`, `<names>` being those models' data names joined by `, ` (the source label's own words; the
   Link cell of 4.7 prints "declined by its skill guard" in their place, version 3, V3-6).
```

Decision 18, v2 spec text:

```
S3.21 per gate, in the protocol's running order, with the kept arm
    as the first row.
```

v3 spec text:

```
S3.21 per gate, in the protocol's running order, with the adopted
    arm as the first row.
```

Builder: copy the new constant cells: the skill-guard cell of the 5 treeroute rows of S3.18 a and of S3.20; the
"Model and SHAP method" cell of the 5 random-forest rows of S3.18 a; the first cell of S3.21's first row and the
"What it checks" cells of E3a, E3m, E3, E6 and E10; and note ᶜ of S3.19 (in its notes block). In S3.25 compose the
Link cell with P in place of M (8 cells). Check 3.3 tests the source labels with the source's words, as before. No
cells.json entry changes: the entries on these lines (S3.20's treeroute rows, S3.21's E3m and E10 rows, S3.25's
Ridge pairs) are in cells that do not change.

## V3-7. Bookkeeping texts

Spec lines: v2 309 -> v3 309 (header comment, block 4); v2 1104 -> v3 1114-1116 (section 5).

Header comment, OLD printed text:

```
Version 2 (2026-11-17, after the first check): ten captions and notes reworded, one row of Table S3.18 b dropped and one note line added; no number changed.
```

NEW printed text:

```
Version 2 (2026-11-17, after the first check): ten captions and notes and three table cells reworded, one row of Table S3.18 b dropped and one note line added; no number changed. Version 3 (2026-11-17, after the second check): captions, notes, labels, cells and source comments reworded, as paper/supp_build/s3_13/spec/CHANGES_v3.md lists; no number changed.
```

Header comment, OLD printed text:

```
every printed number is listed in cells.json beside this file.
```

NEW printed text:

```
every printed data number is listed in cells.json beside this file (the constants of the fixed texts, such as 1,000 and 2,000, are not).
```

Section 5, v2 spec text:

```
below. It is written by `json.dumps(doc, ensure_ascii=False, indent=1, allow_nan=False) + "\n"` (UTF-8, no BOM; no
other formatting step).
```

v3 spec text:

```
below. It is written by `json.dumps(doc, ensure_ascii=False, indent=1, allow_nan=False) + "\n"` (UTF-8, no BOM; no
other formatting step). `tables_file` names the builders' `tables.md` (`OUT\<X>\tables.md`, beside cells.json), of
which `OUT\reconcile\tables_agreed.md` is a byte copy with the same lines, so an entry's `line` is the same line in
both files (version 3, V3-7).
```

`OUT\spec\CHANGES_v2.md`, the two corrections (each marked "(corrected in version 3)"; `s16_v2_number_tokens.py`
measured both: tables.md has 785 lines in versions 1 and 2; version 2 added the tokens `-10` six times, `-3` once and
`0` twice in C1, `8` twice in C6 and `2` once in C9, besides those already listed). CHANGES_v2.md text before the
correction:

```
- tables.md keeps its 786 lines (one row out and one note line in, both inside Table S3.18), so every cells.json
```

CHANGES_v2.md text after the correction:

```
- tables.md keeps its 785 lines (corrected in version 3) (one row out and one note line in, both inside Table
```

CHANGES_v2.md text before the correction:

```
  section and gate numbers in the spec's rules.
```

CHANGES_v2.md text after the correction:

```
  section and gate numbers in the spec's rules; and also (corrected in version 3) `Top-10` six times and `Top-3` once
  (C1: the five captions of S3.23-S3.27, and the S3.29 caption's `Top-3 and top-10 shares`), `above 0` twice (C1: the
  captions of S3.25 and S3.27), a second E8 and a D8 in Table S3.21 note ᵃ (C6), and `Version 2` (C9).
```

Builder: copy the header comment block. Section 5 changes no output: `tables_file` stays `tables.md`. No entries.

## S10. Section 10 and the contents line

Spec lines: v2 15 -> v3 15 (contents line); new v3 1314-1368 (section 10, from its blank line before `---`: each
change and where it is, what was left as in version 2 and why, the helper scripts, what was opened).

v2 spec text:

```
8 What the spec writer opened - 9 Version 2 (2026-11-17).
```

v3 spec text:

```
8 What the spec writer opened - 9 Version 2 (2026-11-17) - 10 Version 3 (2026-11-17).
```

Builder: nothing to print.

## Left as in version 2 (not named by the order)

- The short title of Table S3.18 in the table of section 4 (v3 391) and the heading of 4.2 (v3 475) still say "the
  rivals left out"; neither is printed, and the order changes only the caption and the panel label.
- The S3.28 caption (v3 931) defines the pair's J as "the players to which either run gives more than
  10⁻¹² of its total", without the region weighting that the S3.19 caption now states.
- E8's "What it checks" (v3 687) still says "kept predictions".
- Decision 6 (v3 1182, "Printed only when fewer than the 2,000 draws, for every interval") already agrees with the new
  count clause: no count is printed without an interval.
- Section 9 (the version-2 record) keeps its texts and its version-2 line numbers; two of its "left as in version 1"
  items (the S3.24 source comment and the count clause of the S3.23-S3.27 caption) and the S3.18 source comment are
  now changed by V3-3 and V3-2.
- The version-2 helper scripts `s07_diff_v1_v2.py`, `s10_check_new_texts.py` and `s12_check_changes_file.py` read
  `TABLE_SPEC.md` as version 2; they now hold for `TABLE_SPEC_v2.md` and were not changed.
- CHANGES_v2.md is corrected only where the order says; its other statements are those of version 2 (for example,
  its "Version 2: `OUT\spec\TABLE_SPEC.md`" now names the file kept as `TABLE_SPEC_v2.md`).
