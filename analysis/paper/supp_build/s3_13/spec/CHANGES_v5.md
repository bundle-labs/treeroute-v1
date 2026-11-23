# Changes to the table spec, version 4 to version 5 (2026-11-17)

Names as in the spec: SHAP = `D:\treeroute\analysis\shap_v1`; V = `SHAP\verify_v1`; ROOT = the research-paper folder;
OUT = `ROOT\paper\supp_build\s3_13`. Change order: `OUT\_brief\fix_order_v5.md` (V5-1 to V5-5), written after the
fourth check of version 4 (`OUT\reconcile\tables_agreed.md`, SHA-256
f3d55546f3e83cdcbf80fbfe00a5b2d0cf5b103eeef9fb544e3e037c36a688d9, 785 lines, a byte copy of both builders' tables.md):
three untrue texts corrected and one wording made exact; no number changes.

- Version 4: `OUT\spec\TABLE_SPEC_v4.md`, a byte copy of `TABLE_SPEC.md` made before any edit (SHA-256 of both equal:
  8697d7a7f3d01743d1061c1c006c3a9107284cd50695d4f8f695a331a3984885; 1,423 lines). Versions 1 to 3 stay
  `OUT\spec\TABLE_SPEC_v1.md` (979be5ed...7cf9fb), `OUT\spec\TABLE_SPEC_v2.md` (2046c58a...ad30f02) and
  `OUT\spec\TABLE_SPEC_v3.md` (573cc04e...ead8da31), unchanged.
- Version 5: `OUT\spec\TABLE_SPEC.md` (SHA-256 96a973d2bbaf949cafc1b203ed3e05605c0511196de5580f2ba0734c17e23fc2; 1,476
  lines). UTF-8 without BOM, LF only, as version 4.
- "L" is a line of the spec. Every change of version 5 is inside a line, so sections 0 to 11 keep their line numbers
  (a v4 line number is the v5 line number); section 12 is new (v5 L1424-1476). S12 is this maintenance's own id: the
  new section 12 and its entry in the contents line.
- Checks (all in `OUT\spec\`, read-only, print only; `py -3.9 -I -B <script>` from that folder):
  `s22_diff_v4_v5.py` ties the 7 edits of V5-1 to V5-5 to the order (each of its 6 OLD/NEW pairs used by one edit,
  and V5-5's sentence inserted after the Version 4 sentence), replays the 8 listed edits (with S12's contents entry)
  on version 4 and finds version 5 equal to the result plus section 12, byte for byte; every changed line belongs to
  a listed change (line 417 holds two, V5-1 and V5-2); no line of sections 0 to 11 is added or dropped; 63 fenced
  blocks in both versions, and the four changed blocks keep the first 24 characters of their first line; the copies
  of versions 1 to 4 are intact.
  `s23_check_new_texts_v5.py` builds the expected version 5 of tables.md from `OUT\reconcile\tables_agreed.md` and
  the order's OLD and NEW texts (6 OLD, 6 NEW and the sentence that V5-5 adds; wrapped lines joined by one space),
  instantiates the spec's changed texts (4 fenced blocks; the constant "What it checks" cells of the S3.21 rows E3m
  and E5 with E5's constant problem cell, and the rule of E3m's problem cells applied to the five rebuild records)
  and finds each equal to its expected line: 6 lines of tables.md change, all 6 produced by a checked spec text;
  sections 0 to 8 of the spec hold every NEW text and no OLD text.
  `s24_source_checks_v5.py` prints the source lines and counts behind the order's claims (see the last section);
  `s25_check_changes_v5.py` checks every fenced text of this file against the file it is quoted from, the quotes of
  the last two sections against their sources, the block table below, and the hashes and line counts above.

## What a builder does differently (summary)

1. Copy the changed fixed texts of the fenced blocks: the header comment (V5-5); the caption of Table 9 (V5-1 and
   V5-2); note ᶜ of S3.19 (V5-2); note ᵃ of S3.21 (V5-3). Every changed block keeps the first 24 characters of its
   first line, so a builder finds the blocks as before.
2. Constant cells outside fenced blocks: the "What it checks" cells of S3.21's rows E3m (V5-4) and `E5ᵃ` (V5-3).
3. cells.json: nothing changes. The `spec` key stays `OUT\spec\TABLE_SPEC.md`.

## Expected effect on the outputs (against version 4)

- tables.md keeps its 785 lines; no line is added or dropped, so every cells.json `line` is unchanged. The lines that
  change (1-based, 6): 1, 5, 83, 135, 138, 146.
- cells.json keeps its 4,859 entries, in the same order, with every key unchanged. The 3 entries on changed lines (on
  line 135, S3.21's E3m row: PM2.5, NDVI and burned fraction) keep their `cell` `passed (1 file)`, a problem cell that
  does not change; no note line that holds an entry changes. The `spec` key stays `OUT\spec\TABLE_SPEC.md`.
- No printed number changes. The number tokens that the changes add are constants of the texts only (none is
  removed): on line 1, "Version 5", the date and the path `paper/supp_build/s3_13/spec/CHANGES_v5.md` (V5-5); on line
  135, the "256" of `SHA-256` (V5-4). `s23_check_new_texts_v5.py` lists them line by line.

## Fenced blocks

None added or removed: 63 in both versions, in the same order and at the same lines. Blocks whose content changed
(number = position in the file; L = line of the opening fence, the same in both versions):

| Block | L | Table | Change | First line |
|---|---|---|---|---|
| 4 | 308 | header comment | V5-5: one sentence added | same start |
| 8 | 416 | Table 9 caption | V5-1 and V5-2 | same start |
| 19 | 577 | S3.19 notes | V5-2: note ᶜ (its third line) | unchanged |
| 26 | 692 | S3.21 notes | V5-3: note ᵃ (its first line) | same start |

Every changed block keeps the first 24 characters of its first line, so a builder that finds a block by its position
and the start of its first line finds the same blocks as in version 4.

---

## V5-1. Table 9, the context-and-calendar family on NDVI

Spec line: L417 (Table 9 caption, block 8; the same line as V5-2).

OLD printed text:

```
local drivers, context and calendar (the router context), and the seasonal normal.
```

NEW printed text:

```
local drivers, context and calendar (the router-context columns that copy no tree input), and the seasonal normal.
```

Builder: the caption block of Table 9 (tables.md line 5, with V5-2); captions hold no entry. The family labels
`Context and calendar` of panel f of S3.23-S3.27 and panel a of S3.29, and the label `(no context or calendar input)`
of 2.7, stay.

## V5-2. Coral bleaching's background: earlier nearby survey visits

Spec lines: L417 (Table 9 caption, block 8); L580 (S3.19 note ᶜ, the third line of block 19).

Table 9 caption, OLD printed text:

```
(forest loss, annual: all of them; coral bleaching: survey visits at other locations).
```

NEW printed text:

```
(forest loss, annual: all of them; coral bleaching: a pool of earlier nearby survey visits).
```

S3.19 note ᶜ, the end of the note's first sentence, OLD printed text:

```
a pool of survey visits at other locations.
```

NEW printed text:

```
a pool of earlier nearby survey visits.
```

Builder: copy the caption block of Table 9 and the notes block of S3.19 (tables.md lines 5 and 83). The note group
keeps its four fixed lines and the five structural-zero lines, so no line moves; note ᶜ holds no entry, and the
caption holds none.

## V5-3. Table S3.21, E5 and note ᵃ: what the fingerprint covers

Spec lines: L682 (E5's "What it checks", not fenced); L693 (note ᵃ, the first line of block 26).

E5's "What it checks", OLD printed text:

```
tree-bank fingerprint over every tree array (informational)
```

NEW printed text:

```
fingerprint of the tree bank, the correctors and the placebos, over every node array (informational)
```

Note ᵃ, OLD printed text:

```
the rebuilt tree bank's fingerprint differs
```

NEW printed text:

```
the rebuilt fingerprint of the tree bank, correctors and placebos differs
```

Builder: the "What it checks" cell of the `E5ᵃ` row (tables.md line 138; its five `differs (informational)` cells
are unchanged) and the notes block of S3.21 (line 146); no entries.

## V5-4. Table S3.21, E3m: a lock holds a content hash

Spec line: L679 (the gate table of 4.5, not a fenced block).

OLD printed text:

```
a moved dataset package file has the content, size and modification time that every lock recording it at its old path holds (path map)
```

NEW printed text:

```
a moved dataset package file has the content SHA-256, size and modification time that every lock recording it at its old path holds (path map)
```

Builder: the "What it checks" cell of the E3m row (tables.md line 135). Its problem cells (`passed (1 file)` on
PM2.5, NDVI and burned fraction; `not used (no moved file)` on forest loss and coral bleaching) and their 3 entries are
unchanged.

## V5-5. Bookkeeping

Spec line: L309 (the header comment, block 4). Outside the spec: this file.

Header comment, the sentence added directly after the Version 4 sentence (which ends `CHANGES_v4.md lists; no number
changed.`) and before `Built from the stored values`, NEW printed text:

```
Version 5 (2026-11-17, after the fourth check): three untrue texts corrected and one wording made exact, as paper/supp_build/s3_13/spec/CHANGES_v5.md lists; no number changed.
```

Builder: copy the header comment block (tables.md line 1). No entries.

## S12. Section 12 and the contents line

Spec lines: L15 (contents line); new L1424-1476 (section 12, from its blank line before `---`: each change and where
it is, what was left as in version 4, the helper scripts, what was opened).

v4 spec text:

```
8 What the spec writer opened - 9 Version 2 (2026-11-17) - 10 Version 3 (2026-11-17) - 11 Version 4 (2026-11-17).
```

v5 spec text:

```
8 What the spec writer opened - 9 Version 2 (2026-11-17) - 10 Version 3 (2026-11-17) - 11 Version 4 (2026-11-17) - 12 Version 5 (2026-11-17).
```

Builder: nothing to print.

## Left as in version 4 (not named by the order)

- The order's "Accepted as they are" items are untouched, among them the family labels `Context and calendar` and
  BB4's `(no context or calendar input)` (V5-1).
- The S3.21 caption (L659) still says that "each problem's tree bank and the sampled locations' routers were
  rebuilt"; the order names only E5's "What it checks" and note ᵃ for what the fingerprint covers (V5-3).
- Check 3.10 (L375) names the gate key `E5_bank_fingerprint`, a key of the records, not a printed text.
- Sections 9 to 11 (the records of versions 2 to 4) keep their texts and their line numbers; some of their items
  name texts that version 5 changes again (section 11's V4-1, V4-3, V4-4, V4-6 and V4-13 items, L1386, L1388-1390,
  L1392 and L1399-1401).
- The version-4 helper scripts `s18_diff_v3_v4.py`, `s19_check_new_texts_v4.py` and `s21_check_changes_v4.py` read
  `TABLE_SPEC.md` as version 4 (and s19, s20 and s21 read `tables_agreed.md` as version 3 of tables.md); they were
  not changed.
- CHANGES_v4.md is not changed: its "Version 4: `OUT\spec\TABLE_SPEC.md`" now names the file kept as
  `TABLE_SPEC_v4.md`, and its last section quotes PROTOCOL L375 ("other sites' visits.") for V4-3, a text that the
  order calls inexact on coral's background.

## The order's sources (s24_source_checks_v5.py)

- V5-1: PROTOCOL L393-394: "A context column that is an exact copy of a tree column (the name rule
  `c__ctx:top5:<v>` -> `x__<v>`, then bitwise equality on every explained and background row) is the SAME player";
  L487-488: "a duplicate context column is its tree column's variable". NDVI's `meta.json` `duplicates_merged` has 5
  entries (`c__ctx:top5:V01_mean_temp_C`, `c__ctx:top5:V07_total_ref_ET_mm_lag1`, `c__ctx:top5:era5l_d2m`,
  `c__ctx:top5:era5l_slhf_lag1` and `c__ctx:top5:sph_kgkg_lag6`, each `c__ctx:top5:<v>` mapped to `x__<v>`) on
  treeroute, Ridge, the random forest and LightGBM (and treeroute_B1); BARDL's is empty (it has no `c__` player).
  The merged columns' variables (`mean_temp_C`, `total_ref_ET_mm`, `era5l_d2m`, `era5l_slhf`, `sph_kgkg`, from
  treeroute's `variable_map`) are "local drivers" in per_lead.json `families`, and NDVI's "context and calendar"
  holds only `calendar`; NDVI treeroute's other context players are the four harmonics `c__ctx:sin1`, `c__ctx:cos1`,
  `c__ctx:sin2` and `c__ctx:cos2` (4 + 5 = 9 columns). `duplicates_merged` is empty on every model of PM2.5, burned
  fraction, forest loss and coral bleaching.
- V5-2: coral's treeroute `background_keys.parquet` has 50,000 rows, 50 for each of the 1,000 sample rows of
  `rows.parquet`; 980 are at the explained visit's own reef site (the unit key's part before "|"), in 415 sample
  rows; none is dated on or after the explained visit (by `time`, a day number that equals the date after "|" on
  every key, and by that date), the closest 21 days before it. GLOSSARY L36, "neighbour router": "A ridge on a pool
  of earlier nearby survey visits (coral); it has no normal." The inexact texts that the order names: PROTOCOL L375,
  "other sites' visits.", and L381-382, "its background is a pool of other sites".
- V5-3: PROTOCOL L182: "E5, informational only: the bank fingerprint (SHA-256 over every node array of every tree,
  corrector and placebo)."; `SHAP\scripts\tr_rebuild.py` L737 (read, not run): "the fingerprint hashes every node
  array of every tree, corrector and placebo". GLOSSARY L24, "tree bank": "The union of all regions' specialist trees
  (4,000 to 13,300 trees per problem)."; "corrector" (L27) and "placebo" (L28) are rows of their own.
- V5-4: E3m `values.rule` is "content SHA-256, size and mtime equal every freeze-lock record of the recorded path" on
  PM2.5, NDVI and burned fraction (1 file each); forest loss and coral bleaching have no E3m (E3a `path_map` false).
