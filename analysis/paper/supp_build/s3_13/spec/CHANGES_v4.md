# Changes to the table spec, version 3 to version 4 (2026-11-17)

Names as in the spec: SHAP = `D:\treeroute\analysis\shap_v1`; V = `SHAP\verify_v1`; ROOT = the research-paper folder;
OUT = `ROOT\paper\supp_build\s3_13`. Change order: `OUT\_brief\fix_order_v4.md` (V4-1 to V4-13), the last table
round, written after the third check of version 3 (`OUT\reconcile\tables_agreed.md`, SHA-256
86f7eb2a5ae2bcb1ad798a81332698b7448daee9e5dfe8c13ed193900e5919d7, 785 lines, a byte copy of both builders' tables.md).

- Version 3: `OUT\spec\TABLE_SPEC_v3.md`, a byte copy of `TABLE_SPEC.md` made before any edit (SHA-256 of both equal:
  573cc04e149d8d921e41aff285938ecb8a3b819f2d1c020b1f8ad816ead8da31; 1,368 lines). Versions 1 and 2 stay
  `OUT\spec\TABLE_SPEC_v1.md` (979be5ed...7cf9fb) and `OUT\spec\TABLE_SPEC_v2.md` (2046c58a...ad30f02), unchanged.
- Version 4: `OUT\spec\TABLE_SPEC.md` (SHA-256 8697d7a7f3d01743d1061c1c006c3a9107284cd50695d4f8f695a331a3984885; 1,423
  lines). UTF-8 without BOM, LF only, as version 3.
- "L" is a line of the spec. Every change of version 4 is inside a line, so sections 0 to 10 keep their line numbers
  (a v3 line number is the v4 line number); section 11 is new (v4 L1369-1423). S11 is this maintenance's own id: the
  new section 11 and its entry in the contents line.
- Checks (all in `OUT\spec\`, read-only, print only; `py -3.9 -I -B <script>` from that folder):
  `s18_diff_v3_v4.py` replays the 17 listed edits on version 3 and finds version 4 equal to the result plus section
  11, byte for byte; every changed line belongs to a listed change (line 417 holds two, V4-3 and V4-4); no line of
  sections 0 to 10 is added or dropped; 63 fenced blocks in both versions; the copies of versions 1 to 3 are intact.
  `s19_check_new_texts_v4.py` builds the expected version 4 of tables.md from `OUT\reconcile\tables_agreed.md` and
  the order's OLD and NEW texts (15 OLD, 15 NEW and the sentence that V4-13 adds; wrapped lines joined by one space),
  instantiates the spec's changed texts (7 fenced blocks; the constant cells of the S3.21 rows E3a, E3m, E3, E5 and
  E8 and the S3.22 row label; the rule of S3.21's `Adopted arm` row applied to the `result` of the five rebuild
  records) and finds each equal to its expected line: 15 lines of tables.md change, all 15 produced by a checked spec
  text; sections 0 to 8 of the spec hold every NEW text and no OLD text.
  `s20_source_checks_v4.py` prints the source lines behind the order's claims (see the last section);
  `s21_check_changes_v4.py` checks every fenced text of this file against the file it is quoted from, the hashes and
  line counts above, and the correction of CHANGES_v3.md.

## What a builder does differently (summary)

1. Copy the changed fixed texts of the fenced blocks: the header comment (V4-13); the caption of Table 9 (V4-3 and
   V4-4); the caption of S3.18 with its source comment (V4-12); the panel b table of S3.18, whose header line is new
   (V4-7); notes ᵇ and ᶜ of S3.19 (V4-3); note ᵃ of S3.21 (V4-6); the caption of S3.28 (V4-9). Block 15 starts
   differently (see "Fenced blocks").
2. Constant cells outside fenced blocks: the "What it checks" cells of S3.21's rows E3a (V4-2), E3m (V4-1), E3
   (V4-10), `E5ᵃ` (V4-6) and E8 (V4-11); the S3.22 row label (V4-8).
3. S3.21's `Adopted arm` row: the rule prints "plain tree answers" for a plain arm, which is NDVI's cell (V4-5); the
   four "corrected answers" cells are unchanged.
4. cells.json: nothing changes. The entries on changed lines are in problem cells that do not change. The `spec` key
   stays `OUT\spec\TABLE_SPEC.md`.

## Expected effect on the outputs (against version 3)

- tables.md keeps its 785 lines; no line is added or dropped, so every cells.json `line` is unchanged. The lines that
  change (1-based, 15): 1, 5, 22, 56, 82, 83, 130, 134, 135, 136, 138, 143, 146, 155, 669.
- cells.json keeps its 4,859 entries, in the same order, with every key unchanged. The 15 entries on changed lines (3
  on line 135, S3.21's E3m row; 12 on line 143, its E8 row) keep their `cell`, a problem cell that does not change; no
  note line that holds an entry changes. The `spec` key stays `OUT\spec\TABLE_SPEC.md`.
- No printed number changes. The number tokens that the changes add are constants of the texts only (none is
  removed): on line 1, "Version 4", the date and the path `paper/supp_build/s3_13/spec/CHANGES_v4.md` (V4-13); on
  line 22, the "3.4" of `Sections 3.3 and 3.4` (V4-12). `s19_check_new_texts_v4.py` lists them line by line.

## Fenced blocks

None added or removed: 63 in both versions, in the same order and at the same lines. Blocks whose content changed
(number = position in the file; L = line of the opening fence, the same in both versions):

| Block | L | Table | Change | First line |
|---|---|---|---|---|
| 4 | 308 | header comment | V4-13: one sentence added | same start |
| 8 | 416 | Table 9 caption | V4-3 and V4-4 | same start |
| 11 | 479 | S3.18 caption | V4-12: the source comment | same start |
| 15 | 523 | S3.18 panel b table | V4-7: the header line (its first line) | NEW start (below) |
| 19 | 577 | S3.19 notes | V4-3: notes ᵇ and ᶜ (its second and third lines) | unchanged |
| 26 | 692 | S3.21 notes | V4-6: note ᵃ (its first line) | same start |
| 45 | 930 | S3.28 caption | V4-9 | same start |

Block 15's first line is now the header `Problem`, `Rival or naive baseline`, `Why it has no SHAP value` (it was
`Problem`, `Rival`, `Why it has no SHAP value`). A builder that finds a block by its position and the start of its
first line must use the new start for block 15. Every other changed block keeps the first 24 characters of its first
line.

---

## V4-1. Table S3.21, E3m: what the locks are

Spec line: L679 (the gate table of 4.5, not a fenced block).

OLD printed text:

```
a moved dataset package file has the content, size and time that the run's locks record (path map)
```

NEW printed text:

```
a moved dataset package file has the content, size and modification time that every lock recording it at its old path holds (path map)
```

Builder: the "What it checks" cell of the E3m row (tables.md line 135). Its problem cells (`passed (1 file)` on
PM2.5, NDVI and burned fraction; `not used (no moved file)` on forest loss and coral bleaching) and their 3 entries are
unchanged.

## V4-2. Table S3.21, E3a: coral bleaching's label files; the tree inputs

Spec line: L678 (not fenced).

OLD printed text:

```
inputs, before the labels are read, equal the manifest's (dataset package, regions, constants, file lists, features)
```

NEW printed text:

```
inputs, before the labels are read, equal the manifest's (dataset package, regions, constants, file lists (coral bleaching: the static file list only), tree inputs)
```

Builder: the "What it checks" cell of the E3a row (tables.md line 134); its five `passed` cells are unchanged; no
entries.

## V4-3. Coral bleaching's locations; "site"

Spec lines: L417 (Table 9 caption, block 8); L579 and L580 (S3.19 notes ᵇ and ᶜ, the second and third lines of block
19).

S3.19 note ᵇ, OLD printed text:

```
ᵇ Coral bleaching: a location is a survey visit.
```

NEW printed text:

```
ᵇ Coral bleaching: the column counts survey visits, the engine's unit there; a location is a reef site.
```

S3.19 note ᶜ, the end of the note's first sentence, OLD printed text:

```
a pool of other sites' survey visits.
```

NEW printed text:

```
a pool of survey visits at other locations.
```

Table 9 caption, OLD printed text:

```
(forest loss, annual: all of them; coral bleaching: other sites' survey visits).
```

NEW printed text:

```
(forest loss, annual: all of them; coral bleaching: survey visits at other locations).
```

Builder: copy the caption block of Table 9 and the notes block of S3.19 (tables.md lines 5, 82 and 83). The note group
keeps its four fixed lines and the five structural-zero lines, so no line moves; notes ᵇ and ᶜ hold no entry, and the
caption holds none.

## V4-4. Table 9, the context-and-calendar family

Spec line: L417 (Table 9 caption, block 8; the same line as V4-3).

OLD printed text:

```
local drivers, context and calendar, and the seasonal normal.
```

NEW printed text:

```
local drivers, context and calendar (the router context), and the seasonal normal.
```

Builder: the caption block of Table 9 (tables.md line 5, with V4-3). The family labels `Context and calendar` of
panel f of S3.23-S3.27 and panel a of S3.29, and the label `(no context or calendar input)` of 2.7, stay, as the
order says.

## V4-5. Table S3.21, the adopted arm of NDVI

Spec line: L674 (the rule of the `Adopted arm` row, not fenced).

OLD printed cell, made by the rule (NDVI):

```
identity, plain answers, uniformly weighted; per-location router
```

NEW printed cell, made by the rule (NDVI):

```
identity, plain tree answers, uniformly weighted; per-location router
```

The rule's answer-type part, v3 spec text:

```
("plain answers" if R `table_kind` == plain, "corrected answers" if corrector)
```

v4 spec text:

```
("plain tree answers" if R `table_kind` == plain, "corrected answers" if corrector)
```

Builder: NDVI's cell of the `Adopted arm` row (tables.md line 130; NDVI's rebuild record is the only one with
`table_kind` plain); the four "corrected answers" cells are unchanged; no entries.

## V4-6. Table S3.21, E5 and note ᵃ

Spec lines: L682 (E5's "What it checks", not fenced); L693 (note ᵃ, the first line of block 26).

E5's "What it checks", OLD printed text:

```
bank fingerprint over every tree array (informational)
```

NEW printed text:

```
tree-bank fingerprint over every tree array (informational)
```

Note ᵃ, OLD printed text:

```
the rebuilt bank's fingerprint differs
```

NEW printed text:

```
the rebuilt tree bank's fingerprint differs
```

Builder: the "What it checks" cell of the `E5ᵃ` row (tables.md line 138) and the notes block of S3.21 (line 146); no
entries.

## V4-7. Table S3.18 b, column header

Spec line: L524 (the first line of block 15).

OLD printed text:

```
| Problem | Rival | Why it has no SHAP value |
```

NEW printed text:

```
| Problem | Rival or naive baseline | Why it has no SHAP value |
```

Builder: copy the panel b block (block 15: new start of its first line; tables.md line 56); its separator and its 8
rows are unchanged; Table S3.18 has no entries.

## V4-8. Table S3.22, row label

Spec line: L724 (the row table of 4.6, not fenced).

OLD printed text:

```
Rivals in another link that passed their skill guard
```

NEW printed text:

```
Rivals that explain in another link and passed their skill guard
```

Builder: the first cell of that row (tables.md line 155); its cells (AW4 `cross_link_models`) are unchanged; no
entries.

## V4-9. Table S3.28, the pair's J

Spec line: L931 (the S3.28 caption, block 45).

OLD printed text:

```
(the players to which either run gives more than 10⁻¹² of its total)
```

NEW printed text:

```
(the players to which either run gives more than 10⁻¹² of its total mean absolute SHAP value, with each region weighted equally)
```

Builder: copy the caption block (tables.md line 669); captions hold no entry.

## V4-10. Table S3.21, E3

Spec line: L680 (not fenced).

OLD printed text:

```
dataset package fingerprint, the settings that the written rules set, and run fingerprint, after the written rules are applied
```

NEW printed text:

```
the dataset package fingerprint, the settings that the written rules set and the run fingerprint equal the manifest's, after the written rules are applied
```

Builder: the "What it checks" cell of the E3 row (tables.md line 136); its five `passed` cells are unchanged; no
entries.

## V4-11. Table S3.21, E8

Spec line: L687 (not fenced).

OLD printed text:

```
kept predictions, pre-clip and clipped, on every test row of every sampled location
```

NEW printed text:

```
the adopted arm's saved predictions, pre-clip and clipped, on every test row of every sampled location (coral bleaching: every test survey visit)
```

Builder: the "What it checks" cell of the E8 row (tables.md line 143); its problem cells and their 12 entries are
unchanged.

## V4-12. Table S3.18, source comment

Spec line: L480 (the S3.18 caption, block 11).

OLD printed text:

```
paper/draft/03_protocol.md Section 3.3, paper/draft/tables/table_3.md note d
```

NEW printed text:

```
paper/draft/03_protocol.md Sections 3.3 and 3.4, paper/draft/tables/table_3.md note d
```

Builder: copy the caption block (tables.md line 22); no entries.

## V4-13. Bookkeeping

Spec line: L309 (the header comment, block 4). Outside the spec: `OUT\spec\CHANGES_v3.md` lines 53-54.

Header comment, the sentence added directly after the Version 3 sentence (which ends `CHANGES_v3.md lists; no number
changed.`) and before `Built from the stored values`, NEW printed text:

```
Version 4 (2026-11-17, after the third check): captions, notes, a column header, a row label, cells and a source comment reworded, as paper/supp_build/s3_13/spec/CHANGES_v4.md lists; no number changed.
```

`OUT\spec\CHANGES_v3.md`, "Expected effect", the correction (marked "(corrected in version 4)"). The S3.25 lines whose
entries keep their `cell` are the 8 Ridge-pair lines, 354 and 358-360 of panel a and 369 and 373-375 of panel b, as
the list of changed lines just above it already says; lines 355-357 and 370-372 did not change in version 3.
CHANGES_v3.md text before the correction:

```
  354-360 and 369-375 of S3.25) keep their `cell`, a cell that does not change. The `spec` key stays
  `OUT\spec\TABLE_SPEC.md`.
```

CHANGES_v3.md text after the correction:

```
  354, 358-360, 369 and 373-375 (corrected in version 4) of S3.25) keep their `cell`, a cell that does not change.
  The `spec` key stays `OUT\spec\TABLE_SPEC.md`.
```

Builder: copy the header comment block (tables.md line 1). The CHANGES_v3.md correction changes no output. No entries.

## S11. Section 11 and the contents line

Spec lines: L15 (contents line); new L1369-1423 (section 11, from its blank line before `---`: each change and where
it is, what was left as in version 3 and why, the helper scripts, what was opened).

v3 spec text:

```
8 What the spec writer opened - 9 Version 2 (2026-11-17) - 10 Version 3 (2026-11-17).
```

v4 spec text:

```
8 What the spec writer opened - 9 Version 2 (2026-11-17) - 10 Version 3 (2026-11-17) - 11 Version 4 (2026-11-17).
```

Builder: nothing to print.

## Left as in version 3 (not named by the order)

- The order's "Accepted as they are" items are untouched, among them the family labels `Context and calendar` and
  BB4's `(no context or calendar input)` (V4-4).
- The "What it checks" of S3.21's `Adopted arm` row (`link, answer type and weighting; router type`) and its
  "corrected answers": GLOSSARY "answer type" reads "Whether the router uses plain tree answers or corrected answers."
- S3.20 note ᵃ (L644) already has the coral clause `(coral bleaching: every test survey visit)` that V4-11's NEW E8
  text now repeats.
- Section 10 (the version-3 record) keeps its texts and its line numbers; two of its "left as in version 2" items
  (the S3.28 caption's J and E8's "kept predictions", L1350-1352) are now changed by V4-9 and V4-11, and its V3-5 item
  (L1340) quotes the version-3 label of S3.22.
- The version-3 helper scripts `s13_diff_v2_v3.py`, `s14_check_new_texts.py` and `s17_check_changes_v3.py` read
  `TABLE_SPEC.md` as version 3 (and s14 and s17 read `tables_agreed.md` as version 2 of tables.md); they were not
  changed.
- CHANGES_v3.md is corrected only where the order says; its other statements are those of version 3 (for example,
  its "Version 3: `OUT\spec\TABLE_SPEC.md`" now names the file kept as `TABLE_SPEC_v3.md`).

## The order's sources (s20_source_checks_v4.py)

- V4-1: E3m `values.rule` is "content SHA-256, size and mtime equal every freeze-lock record of the recorded path" on
  PM2.5, NDVI and burned fraction; `lock_records` is 1 on PM2.5, 4 on NDVI and 4 on burned fraction; forest loss and
  coral bleaching have no E3m (E3a `path_map` false). PROTOCOL L178-179: "every file the recorded path map renamed has
  today's content SHA-256, size and mtime equal to every freeze-lock record of its recorded path".
- V4-2: E3a `checked` has 12 keys with `target_files_sha256` and `not_before_read` is empty on PM2.5, NDVI, burned
  fraction and forest loss; on coral bleaching `checked` has 11 keys without it and `not_before_read` is
  `["target_files_sha256"]`; the feature key is `feature_list (tree-feature prefix)` on all five. PROTOCOL L175-177
  lists the keys; GLOSSARY "tree inputs" has the other name "tree features".
- V4-3: GLOSSARY "location": "a reef site on coral; on coral each survey visit at a site is scored separately (the
  engine's unit there is the visit)"; PROTOCOL L375: "coral, B2 is the visit's saved 50-visit router pool
  (`pools_test_pass.parquet` of the lead): other sites' visits."; tables.md line 79 prints coral's Locations as 1,000.
- V4-4: GLOSSARY "router context" lists the other names "context, ctx, standardised context, context columns";
  PROTOCOL L487-488: "context columns are `calendar` (month and harmonics) or `ctx:<name>`; a duplicate context column
  is its tree column's variable."; L491-492 name the family "context and calendar".
- V4-5: GLOSSARY "tree answer" lists "plain answer" among its other names; "answer type": "plain tree answers or
  corrected answers". V4-6: GLOSSARY "tree bank" lists "bank" among its other names and defines it as "The union of
  all regions' specialist trees"; PROTOCOL L182: "E5, informational only: the bank fingerprint (SHA-256 over every
  node array of every tree, corrector and placebo)."
- V4-10: PROTOCOL L180: "E3, after the derive: the package fingerprint, `derived_sha256` and the run fingerprint equal
  the manifest's." V4-11: PROTOCOL L198: "E8: `pre__<arm>` and `arm__<arm>` are bit-identical on every test row of
  every sampled unit."; tables.md line 121 (S3.20 note ᵃ): "for treeroute v1, every test row of every sampled location
  (coral bleaching: every test survey visit)".
- V4-12: `ROOT\paper\draft\03_protocol.md` L23 is the heading "## 3.4 References, verdicts and uncertainty" and L25
  defines the reference; L21, in Section 3.3, lists the baselines.
- V4-13: tables.md lines 354, 358-360, 369 and 373-375 hold the Ridge pairs of S3.25 (Link cell "... declined by its
  skill guard: Ridge"); lines 355-357 and 370-372 do not.
