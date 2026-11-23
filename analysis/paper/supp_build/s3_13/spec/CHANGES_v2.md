# Changes to the table spec, version 1 to version 2 (2026-11-17)

Names as in the spec: SHAP = `D:\treeroute\analysis\shap_v1`; V = `SHAP\verify_v1`; ROOT = the research-paper folder;
OUT = `ROOT\paper\supp_build\s3_13`. Change order: `OUT\_brief\fix_order_v2.md` (C1-C9, G1-G4).

- Version 1: `OUT\spec\TABLE_SPEC_v1.md`, a byte copy of `TABLE_SPEC.md` made before any edit (SHA-256 of both equal:
  979be5ed64b908402b8c69ad60eb0b07e48f1b10b8cacaadb7049fefff7cf9fb; 1,218 lines).
- Version 2: `OUT\spec\TABLE_SPEC.md` (SHA-256 2046c58a7aa787c15d6cd90b1353a513f6ef28dbff517a4531fa58b09ad30f02; 1,301
  lines). UTF-8 without BOM, LF only, as version 1.
- "v1 L" is a line of version 1, "v2 L" a line of version 2. S9 is this maintenance's own id: the new section 9 and its
  entry in the contents line.
- Checks (all in `OUT\spec\`, read-only, print only; `py -3.9 -I -B <script>` from that folder):
  `s07_diff_v1_v2.py` replays the 30 listed edits on version 1 and finds version 2 equal to the result plus section 9,
  byte for byte; every changed line belongs to a listed change; 63 fenced blocks in both versions.
  `s10_check_new_texts.py` builds the expected version 2 of tables.md from `OUT\reconcile\tables_agreed.md` and the
  order's OLD/NEW texts, instantiates the spec's changed texts (39 texts: fenced blocks, the caption template with
  `{shares_sentence}`, the two notes with data placeholders, the two constant cells) and finds each in it.
  `s12_check_changes_file.py` checks every fenced text of this file against the file it is quoted from.

## What a builder does differently (summary)

1. Copy the changed fixed texts: the header comment (C9), the captions of Table 9 and Table S3.29 (C1), notes ᵃ and ᵇ
   of S3.20 (C2), note ᵃ of S3.21 (C6), note ᵈ of S3.22 (C8), the sign-agreement note of S3.23-S3.27 (C7), the ‡ note
   of S3.24 (C3), the note of S3.30 (C4), and three constant cells outside fenced blocks: E10's "What it checks"
   (C6), the S3.22 row label `Guard-passing rivals in another link` (C5), and the reworded baselines row of S3.18 b
   (C4, inside the panel b block).
2. S3.23-S3.27 captions: the template has one new placeholder, `{shares_sentence}`, with two values: the one with
   "(d, e, g)" for S3.25 (fire) and S3.27 (coral), the one with "(d, e)" for S3.23 (pm25), S3.24 (ndvi) and S3.26
   (defo) (C1).
3. Table S3.18: panel b has one row fewer (8 rows; the CRW Outlook row is gone), and its note group has one line more
   (3 lines), the new line first, before `ᵃ Failed` (C4).
4. cells.json: panel f's family shares use part `share` (G1); the `cell` text of the 8 entries of S3.20 note ᵇ and of
   the 12 entries of the S3.24 ‡ note is the new note line (C2, C3).
5. Read `SHAP\SAMPLE_REGISTER.txt`, the logs and `bardl_maxima.txt` with universal newlines and `utf-8-sig`, and match
   the regexes on lines without their line ends (G2). G3 and G4 write down what both builders already did.

## Expected effect on the outputs (against version 1)

- tables.md keeps its 785 lines (corrected in version 3) (one row out and one note line in, both inside Table
  S3.18), so every cells.json `line` is unchanged. The lines that change (1-based): 1, 5, 65, 66, 67, 121, 122, 144,
  146, 155, 171, 174, 251, 256, 342, 344, 348, 451, 457, 543, 548, 661, 711, 784 (line 66 is now the blank line, line
  67 the new note).
- cells.json keeps its 4,859 entries, in the same order, with the same `line`, `table`, `panel`, `row`, `column`,
  `printed`, `source`, `selector` and `stored`. Changes: `cell` of the 8 entries on line 122 (S3.20 note ᵇ) and of the
  12 entries on line 344 (S3.24 note ‡); `part` `share` on the 125 panel-f entries (S3.23 20, S3.24 25, S3.25 25,
  S3.26 25, S3.27 30), which builder A already wrote in version 1 and builder B wrote as `value`. That part name was
  the only difference between the two version-1 cells.json files (`s09_builder_cells_diff.py`; their tables.md were
  equal, SHA-256 5f414a11...beae03). The 9 E10 entries on line 144 keep their `cell` (each is a problem cell, which
  does not change). The `spec` key stays `OUT\spec\TABLE_SPEC.md`.
- No printed number changes. The digits that the changes add or remove are constants of the texts only: D15 (the
  dropped row), Table 7 (the new note), "1 to 1,999 of the 2,000 draws" (C7), S1.7 (C8), the date and S3.18 (C9), and
  section and gate numbers in the spec's rules; and also (corrected in version 3) `Top-10` six times and `Top-3` once
  (C1: the five captions of S3.23-S3.27, and the S3.29 caption's `Top-3 and top-10 shares`), `above 0` twice (C1: the
  captions of S3.25 and S3.27), a second E8 and a D8 in Table S3.21 note ᵃ (C6), and `Version 2` (C9).

## Fenced blocks

None added or removed: 63 in both versions, in the same order. Blocks whose content changed (number = position in
the file, v1 L / v2 L of the opening fence):

| Block | v1 L / v2 L | Table | Change | First line |
|---|---|---|---|---|
| 4 | 301 / 308 | header comment | C9: one sentence inserted | same start |
| 8 | 408 / 415 | Table 9 caption | C1 | same start |
| 15 | 501 / 516 | S3.18 panel b table | C4: 11 lines to 10 (CRW Outlook row dropped; baselines row reworded) | unchanged |
| 16 | 517 / 531 | S3.18 notes | C4: 2 lines to 3; new first line | NEW: `Panel b lists the rivals of the nowcast; ...` (was `ᵃ Failed: ...`) |
| 23 | 621 / 636 | S3.20 notes | C2: notes ᵃ and ᵇ | same start |
| 26 | 670 / 685 | S3.21 notes | C6: note ᵃ | same start |
| 29 | 716 / 732 | S3.22 notes | C8: note ᵈ (4th line) | unchanged |
| 30 | 735 / 751 | S3.23-S3.27 caption template | C1: `{shares_sentence}` | same start |
| 41 | 849 / 875 | sign-agreement and † notes (all five AW3 tables) | C7 | same start |
| 42 | 856 / 882 | S3.24 ‡ note | C3 | same start |
| 50 | 952 / 979 | S3.29 caption | C1 | same start |
| 63 | 1056 / 1089 | S3.30 notes | C4 | same start |

A builder that finds a block by its position and the start of its first line must use the new first line for block 16
only.

---

## C1. What a share is measured against

Spec lines: v1 409 -> v2 416 (Table 9 caption, block 8); new v2 446-452 (4.1, paragraph on the two bases); v1 736 ->
v2 752 (caption template, block 30); new v2 760-763 (the `{shares_sentence}` bullet) and 765-769 (4.7, paragraph);
v1 953 -> v2 980 (S3.29 caption, block 50); new v2 1013-1016 (4.9, paragraph); v1 1157-1158 -> v2 1191-1193
(decision 12).

Table 9 caption, OLD printed text:

```
Own-history share: the share of a model's total mean absolute SHAP value that goes to the location's own lagged labels.
```

NEW printed text:

```
Own-history share: the share of the own-history family (the location's own lagged labels) in the sum of the model's five families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values; it is not the sum of the own-history variables' shares.
```

Captions of S3.23-S3.27, OLD printed text (all five):

```
Shares are of a model's total mean absolute SHAP value over J, without intervals, as in the comparison's files.
```

NEW printed text (S3.23, S3.24, S3.26):

```
Top-10 shares (d, e) are of a model's total mean absolute SHAP value over J; family shares (f) are of the sum of its five families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values; neither has an interval, as in the comparison's files.
```

NEW printed text (S3.25, S3.27):

```
Top-10 shares (d, e, g) are of a model's total mean absolute SHAP value over J (g: on its rows with a forecast above 0); family shares (f) are of the sum of its five families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values; none has an interval, as in the comparison's files.
```

Caption of S3.29, OLD printed text:

```
Shares are of the B1 run's total mean absolute SHAP value over the pair's J.
```

NEW printed text:

```
Top-3 and top-10 shares are of the B1 run's total mean absolute SHAP value over the pair's J; family shares and the own-history share are of the sum of its five families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values.
```

The template (block 30), v1 spec text:

```
not comparable in scale or rank. Shares are of a model's total mean absolute SHAP value over J, without intervals, as in the comparison's files. <!--
```

v2 spec text:

```
not comparable in scale or rank. {shares_sentence} <!--
```

The new placeholder's bullet, after `{extra_rulings}` (v2 760-763), v2 spec text:

```
- `{shares_sentence}` (version 2, C1): fire and coral (the tables with panel g)
  `Top-10 shares (d, e, g) are of a model's total mean absolute SHAP value over J (g: on its rows with a forecast above 0); family shares (f) are of the sum of its five families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values; none has an interval, as in the comparison's files.`;
  else (pm25, ndvi, defo)
  `Top-10 shares (d, e) are of a model's total mean absolute SHAP value over J; family shares (f) are of the sum of its five families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values; neither has an interval, as in the comparison's files.`
```

The prose that states the two bases (the order: sections 4.1, 4.7 and 4.9). 4.1 (v2 446-452), v2 spec text:

```
The two share bases (PROTOCOL section 8; version 2, C1). A player's share (importance.parquet `share`, the top-k
shares) is its mean absolute SHAP value divided by the model's total mean absolute SHAP value over J. A family share
(families.parquet `share`) is the family's mean absolute attribution divided by the sum of the model's five families'
mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values on that row.
The own-history shares of Table 9 (AW4 `own_history_share_treeroute` and `own_history_share_median_rival`; A's
`problems.fire.main_row.own_history_share_treeroute`) are family shares, not the sum of the own-history variables'
shares, as the caption says.
```

4.7 (v2 765-769), v2 spec text:

```
The two share bases (version 2, C1; as in 4.1): the top-10 shares of panels d and e (importance.parquet `share`) and
of panel g (PL `nonzero_forecast_rows`, on the model's rows with a forecast above 0) are of the model's total mean
absolute SHAP value over J; the family shares of panel f (families.parquet `share`) are of the sum of the model's five
families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values.
`{shares_sentence}` states both in the caption.
```

4.9 (v2 1013-1016), v2 spec text:

```
The two share bases (version 2, C1; as in 4.1): B1's top-3 and top-10 shares (A `b1.{p}.variable.top3`,
`b1.{p}.{L}.top10`) are of the B1 run's total mean absolute SHAP value over the pair's J; its family shares and its
own-history share (A `b1.{p}.variable.families`, `b1.{p}.variable.own_history_share`) are of the sum of its five
families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values.
```

Decision 12 quoted the old caption words. v1 spec text:

```
12. **BB5.** No interval for the main models' top-10 shares and family shares; the captions say "without intervals, as
    in the comparison's files". B1's family shares and own-history share keep their intervals; no top-k list has one.
```

v2 spec text:

```
12. **BB5.** No interval for the main models' top-10 shares and family shares; the captions say so ("neither has an
    interval, as in the comparison's files", or "none has an interval" in the two tables with panel g). B1's family
    shares and own-history share keep their intervals; no top-k list has one.
```

Builder: copy the new caption blocks of Table 9 and S3.29. For S3.23-S3.27, fill `{shares_sentence}` (one more
placeholder, defined in one more bullet whose two values each sit on their own line as one code span). The paragraphs
and decision 12 change no output. Captions hold no cells.json entry, so cells.json is unchanged by C1.

## C2. Which script checks the rivals (S3.20, notes ᵃ and ᵇ)

Spec lines: v1 622-623 -> v2 637-638 (block 23); v1 330 -> v2 337 (check 3.2, the same record named the same way).

Note ᵃ, OLD printed text:

```
The comparison script checks a rival's pre-clip column only (–: not read).
```

NEW printed text:

```
The rivals' SHAP script (rival_shap.py) checks a rival's pre-clip column only (–: not read).
```

Note ᵇ, OLD printed text:

```
The comparison script's own check of its row-by-row copy of the design,
```

NEW printed text:

```
The rivals' SHAP script's own check of its row-by-row copy of the design,
```

Check 3.2, v1 spec text:

```
`exactness.json` (the comparison
   script's own row-by-row check
```

v2 spec text:

```
`exactness.json` (the rivals' SHAP
   script's own row-by-row check
```

Builder: copy the new notes block. Note ᵇ's 8 cells.json entries (row `note`, columns `ridge_copy:pm25`,
`ridge_copy:ndvi`, `ridge_copy:fire`, `ridge_copy:defo`, parts `bit_equal_rows` and `rows`) get the new note line as
`cell`; their printed values and everything else are unchanged. Check 3.2 tests the same fields as before.

## C3. NDVI's BARDL footnote (S3.24, note ‡)

Spec lines: v1 857 -> v2 883 (block 42); v1 277 -> v2 284 (2.8, the meaning of `‡`); v1 1151-1152 -> v2 1185-1186
(decision 10).

OLD printed text (first sentence):

```
Its top-5, top-10 and top-20 sets are therefore filled by name order, the tie rule applied in code-point ascending order, at both levels, and the cells of its pairs that use those sets depend on that order.
```

NEW printed text:

```
Beyond its three variables (variable level) and nine columns (feature level), its top-5, top-10 and top-20 sets are therefore filled by name order, the tie rule applied in code-point ascending order, and the cells of its pairs that use those sets depend on that order.
```

OLD printed text (second sentence, up to the list):

```
Under the other two orders tried (case-insensitive ascending, and descending), the largest move of each statistic over BARDL's eight pair-levels is:
```

NEW printed text:

```
Across the three orders tried (code-point ascending, as printed; case-insensitive ascending; and descending), the largest spread (highest minus lowest value) of each statistic over BARDL's eight pair-levels is:
```

2.8, v1 spec text:

```
(footnote with the collation moves)
```

v2 spec text:

```
(footnote with the spreads over the three collations)
```

Decision 10, v1 spec text:

```
and the six largest moves and the example from
    bardl_maxima.txt, each
```

v2 spec text:

```
and the six largest spreads over the three collations and
    the example from bardl_maxima.txt, each
```

Builder: copy the new block; its placeholders, their values and their order are unchanged (the six spreads, the
pair-levels and the example are the same numbers). The 12 note entries (row `note`, columns `z_var`, `j_var`,
`z_feat`, `j_feat`, `m_jaccard_top5`, `m_jaccard_top10`, `m_jaccard_top20`, `m_rho20`, `m_rbo090`, `m_rbo095`,
`ex_base`, `ex_desc`) get the new note line as `cell`.

## C4. Rivals left out (S3.18 b) and coral's B1 (S3.30)

Spec lines: v1 511-512 -> v2 526 (panel b block 15: v1 511 dropped, v1 512 reworded); new v2 532 (first line of the
notes block 16); v1 1057 -> v2 1090 (S3.30 notes, block 63).

Dropped row, OLD printed text:

```
| Coral bleaching | CRW Outlook | One-input linear map on anomalies; it could instead be shown as a labelled reference row (decision D15, left at its default). |
```

Baselines row, OLD printed text:

```
| All five | The baselines: the seasonal normal, the last-5-years normal, predict-zero, persistence and damped persistence; on coral bleaching the training median and the last visit | No input feature: there is no SHAP value to compute. |
```

NEW printed text:

```
| All five | The naive baselines at the nowcast: the arithmetic and last-5-years normals and predict-zero; on coral bleaching, which has no per-location normal, the training median and predict-zero | No input feature: there is no SHAP value to compute. |
```

New note line, first in the note group, before `ᵃ Failed` (NEW printed text):

```
Panel b lists the rivals of the nowcast; rivals that run only at forecast leads (Table 7), among them the CRW Outlook, are outside this comparison, which explains the nowcast only.
```

S3.30 note, OLD printed text:

```
Coral bleaching: B1 is not defined (its router reads a pool of other sites' survey visits), so it has no B1 run.
```

NEW printed text:

```
Coral bleaching: B1 is not defined, so it has no B1 run.
```

Builder: panel b prints 8 rows (10 table lines with the header and separator), not 9; the note group of S3.18 prints 3
lines, the new line first (block 16's first line is new; see "Fenced blocks"). The two changes sit inside Table
S3.18, so every later line number of tables.md, and every cells.json `line`, stays; Table S3.18 has no entries. The
S3.30 note has no entries.

## C5. Table S3.22, row label

Spec line: v1 701 -> v2 717 (the row table of 4.6, not a fenced block).

OLD printed text:

```
Rivals in another link
```

NEW printed text:

```
Guard-passing rivals in another link
```

Builder: the first cell of that row; its cells (AW4 `cross_link_models`) are unchanged; no entries.

## C6. Table S3.21, gate E10 and note ᵃ

Spec lines: v1 666 -> v2 681 (the E10 row of 4.5, column "What it checks", not a fenced block); v1 671 -> v2 686
(note ᵃ, block 26).

E10, OLD printed text:

```
exported trees and evaluator reproduce the engine's tree answers bit for bit
```

NEW printed text:

```
exported trees and evaluator reproduce the engine's tree answers bit for bit, on one sampled location's fit and test rows (forest loss: every sampled location; coral bleaching: one visit's pool and test row)
```

Note ᵃ, OLD printed text:

```
while every checked prediction matches (E5a, E8, E10); the cause is not established.
```

NEW printed text:

```
while every checked tree answer and prediction matches: bit for bit (E5a, E10, and E8 on the identity and log(y + c) arms), and within the D8 tolerance on the arcsine arms (E8); the cause is not established.
```

Builder: E10's constant "What it checks" text is longer; its five problem cells, and their 9 cells.json entries
(whose `cell` is the problem cell), are unchanged. Note ᵃ: copy; no entries.

## C7. The sign-agreement note (S3.23-S3.27)

Spec line: v1 850 -> v2 876 (block 41, first line); printed on tables.md lines 251, 342, 451, 543 and 661.

OLD printed text:

```
and, where fewer than 2,000, the number of draws on which the statistic is defined. Undefined: no player qualifies on the full sample.
```

NEW printed text:

```
and, where the statistic is defined on 1 to 1,999 of the 2,000 draws, that number of draws. Undefined: no player qualifies on the full sample; printed without an interval, it is undefined on every draw.
```

Builder: copy, in all five tables. SIGN (2.6) is unchanged and already prints what the note says (an interval when
`n_finite` > 0; the count when 0 < `n_finite` < 2,000). No entries.

## C8. Table S3.22, note ᵈ

Spec line: v1 720 -> v2 736 (block 29, its fourth line).

OLD printed text:

```
was read by an agent on 2026-11-13 at about 15:31, before the independent re-computation; the re-computation's implementers A and B never opened it (ruling BB6).
```

NEW printed text:

```
was read on 2026-11-13 at about 15:31, before the independent re-computation; the re-computation's implementers A and B never opened it (ruling BB6; Supplement S1.7 records who read it).
```

Builder: copy; no entries.

## C9. The header comment (tables.md line 1)

Spec line: v1 302 -> v2 309 (block 4). Inserted after the first sentence, which ends "the nowcast of each problem."
(NEW printed text):

```
Version 2 (2026-11-17, after the first check): ten captions and notes reworded, one row of Table S3.18 b dropped and one note line added; no number changed.
```

Builder: copy; the rest of the line, with "every printed number is listed in cells.json beside this file", is
unchanged. No entries.

## G1. cells.json part names

Spec lines: v1 1087 -> v2 1120 (section 5, the `part` row of the entry table); v1 886 -> v2 912-913 (4.7, panel f).

v1 spec text:

```
| `part` | the part name of section 4 (`value`, `ci_low`, `ci_high`, `n_finite`, `signs`, `count`, `share`, ...) |
```

v2 spec text:

```
| `part` | the part name of section 4 (`value`, `ci_low`, `ci_high`, `n_finite`, `signs`, `count`, `share`, ...). Where section 4 names no part (version 2, G1): a cell that prints one number uses `value`; the family shares of panel f in Tables S3.23-S3.27 use `share`, as the other shares printed without an interval (panels d, e and g; Table S3.29 c and d); an interval cell uses `value`, `ci_low`, `ci_high`, and `n_finite` when it is printed |
```

4.7, v1 spec text:

```
Panel f: row = family name (as in families.parquet), column = model. Note numbers (ndvi):
```

v2 spec text:

```
Panel f: row = family name (as in families.parquet), column = model, part `share` (version
2, G1: as the other shares printed without an interval). Note numbers (ndvi):
```

Builder: the 125 panel-f entries use part `share`. Every other unnamed part follows the rule as both builders already
wrote it in version 1 (for example `value` for S3.19's counts, S3.20's single numbers, S3.23-S3.27 panel c's
stabilities and S3.30; `value`, `ci_low`, `ci_high` for panel c's W and mean Spearman and S3.29 a and b).

## G2. Source text formats

Spec lines: new v2 100-105 (section 1, after the maxima block's paragraph); v1 1014 -> v2 1046-1047 and v1 1023 -> v2
1056 (4.10, the log's B1 block); v1 1107 -> v2 1140-1141 (section 5, selector grammar).

Section 1, v2 spec text:

```
Text formats (version 2, G2): `SHAP\SAMPLE_REGISTER.txt` and the logs `SHAP\logs\tr_shap_<p>_lead0.log` have CRLF
line ends; `V\_lead\outputs\bardl_maxima.txt` has a UTF-8 byte-order mark and CRLF line ends. Read each of them as text
with universal newlines and encoding `utf-8-sig` (`open(path, encoding="utf-8-sig")`, whose default `newline=None`
turns every `\r\n` into `\n`), and split the text on `\n`. Line numbers (the selectors of section 5) count from 1 on
the lines so read; the register's fields, the maxima regex above and the two log regexes of section 4.10 (the "done
in" regex ends in `$`) are applied to a line without its line end.
```

4.10, v1 spec text:

```
The B1 block of a log: split the file on `\n`; the set-up lines match
```

v2 spec text:

```
The B1 block of a log: read the file as section 1's text formats say
(universal newlines, encoding `utf-8-sig`; version 2, G2) and split the text on `\n`; the set-up lines match
```

4.10, v1 spec text:

```
first line after it that matches
```

v2 spec text:

```
first line after it that matches, as a line without its line end (G2),
```

Section 5, v1 spec text:

```
with the 1-based line number in that file and the field name
```

v2 spec text:

```
with the 1-based line number in that file (counted on the lines read
  as section 1's text formats say: universal newlines, `utf-8-sig`; version 2, G2) and the field name
```

Builder: open these files with `encoding="utf-8-sig"` and the default newline handling, split on `\n`, and match on
lines without line ends. Line numbers are those both builders wrote in version 1 (for example PM2.5's log: line 25,
background pairs; line 39, total and tree-SHAP seconds). Measured (`s08_source_checks.py`): the register has 5 CRLF
line ends and no BOM; the five logs have CRLF line ends and no BOM; `bardl_maxima.txt` has a BOM and 14 CRLF line
ends.

## G3. Table S3.21, E3m

Spec lines: v1 676 -> v2 691-692 (4.5, cells.json keys).

v1 spec text:

```
problem; parts: E3m `files`; E4 `rows`;
```

v2 spec text:

```
problem; parts: E3m `files` (version 2, G3: its selector is `len(gates.E3m_recorded_path_map.values.files)` and its
stored value the list's length); E4 `rows`;
```

Builder: the three E3m entries (pm25, ndvi, fire) keep the selector and the stored value `[1]` that both builders
wrote in version 1. The stored value is stated as for S3.19's structural-zero counts.

## G4. Table S3.22, coral's "Own-history share of each same-link rival"

Spec line: v1 711 -> v2 727 (4.6, the cell rule).

v1 spec text:

```
joined by "; ", on coral + " (no own-history input)" (fire: `–`) |
```

v2 spec text:

```
joined by "; "; on coral the label " (no own-history input)" is appended once, at the end of the joined cell, not after each rival's share (version 2, G4) (fire: `–`) |
```

Builder: no change; coral's cell stays `random forest 0.00; LightGBM 0.00; absolute-error booster 0.00 (no own-history
input)`, as both builders printed it.

## S9. Section 9 and the contents line

Spec lines: v1 15 -> v2 15 (contents line); new v2 1254-1301 (section 9, from its blank line before `---`: each change and where it is, what was left as
in version 1 and why, the helper scripts, what was opened).

v1 spec text:

```
8 What the spec writer opened.
```

v2 spec text:

```
8 What the spec writer opened - 9 Version 2 (2026-11-17).
```

Builder: nothing to print.

## Left as in version 1 (not named by the order)

- The S3.24 caption's source comment (`{extra_src}`, v2 757): "the collation moves of the footnote", while the
  footnote now speaks of spreads. The order keeps the source comments unless a changed text needs them.
- The S3.23-S3.27 caption: "with the number of finite draws where a statistic is defined on fewer of them", the
  wording that C7 made exact in the note (a statistic defined on no draw prints no count).
- The S3.18 caption's source comment names PROTOCOL sections 5 and 7 and Part 628 for "rivals left out and why"; the
  reworded panel b rests on the paper's Section 3.3, Table 4a note ᵈ and Table 7, which it does not name.
- Section 8 (what the version-1 spec writer opened) is the version-1 record; section 9 records version 2.
