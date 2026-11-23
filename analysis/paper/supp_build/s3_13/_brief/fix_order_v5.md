# Change order for version 5 of the S3.13 tables (2026-11-17): three untrue texts

Names as in `brief_tables.md`: SHAP, V, ROOT, OUT. The fourth check of version 4 (`OUT\reconcile\tables_agreed.md`,
SHA-256 f3d55546...a688d9) closed every change of version 4 and found no number problem, but found three texts that
are not true (two of them restate older words). Under the rule of `fix_order_v4.md` (an untrue text reopens the
tables), this order fixes them, with one more exact wording. **No number changes, and no line is added or dropped**
(785 lines). The lead checked the sources named below.

Each change gives the printed text of version 4 (OLD) and of version 5 (NEW), each in one code span (wrapped lines
join with one space). Change every place in the spec that states the text.

## V5-1. Table 9, the context-and-calendar family on NDVI

A context column that is an exact copy of a tree column is the same player as that column (PROTOCOL L393-397;
L487-488: "a duplicate context column is its tree column's variable"). NDVI's router context has nine columns: four
calendar harmonics and five `ctx:top5:*` copies of tree inputs, which each model's `meta.json` `duplicates_merged`
maps to their tree columns, so per_lead.json puts them in "local drivers" and NDVI's context-and-calendar family holds
only the calendar. `duplicates_merged` is empty on the other four problems. The gloss "(the router context)" is
therefore untrue on NDVI.

- OLD: `local drivers, context and calendar (the router context), and the seasonal normal.` NEW: `local drivers,
  context and calendar (the router-context columns that copy no tree input), and the seasonal normal.`

## V5-2. Coral bleaching's background: earlier nearby survey visits

Of coral's 50,000 background visits, 980 are earlier visits at the explained visit's own reef site (in 415 of the
1,000 sample rows); none is dated on or after the explained visit (`SHAP\out\coral\lead_0\treeroute\background_keys.parquet`
against `rows.parquet`). GLOSSARY "neighbour router": `A ridge on a pool of earlier nearby survey visits (coral)`.
PROTOCOL L375 and L381-382 ("other sites' visits") are inexact on this point and are not to be quoted for it.

- Table 9 caption. OLD: `(forest loss, annual: all of them; coral bleaching: survey visits at other locations).` NEW:
  `(forest loss, annual: all of them; coral bleaching: a pool of earlier nearby survey visits).`
- Table S3.19, note ᶜ. OLD: `a pool of survey visits at other locations.` NEW: `a pool of earlier nearby survey
  visits.`

## V5-3. Table S3.21, E5 and note ᵃ: what the fingerprint covers

PROTOCOL L182: "E5, informational only: the bank fingerprint (SHA-256 over every node array of every tree, corrector
and placebo)"; `SHAP\scripts\tr_rebuild.py` L736-740 (read only). GLOSSARY: the tree bank is the specialist trees
only; the corrector and the placebo have rows of their own.

- E5's "What it checks". OLD: `tree-bank fingerprint over every tree array (informational)` NEW: `fingerprint of the
  tree bank, the correctors and the placebos, over every node array (informational)`
- Note ᵃ. OLD: `the rebuilt tree bank's fingerprint differs` NEW: `the rebuilt fingerprint of the tree bank,
  correctors and placebos differs`

## V5-4. Table S3.21, E3m: a lock holds a content hash

`gates.json` E3m `values.rule`: "content SHA-256, size and mtime equal every freeze-lock record of the recorded path".

- OLD: `a moved dataset package file has the content, size and modification time that every lock recording it at its
  old path holds (path map)` NEW: `a moved dataset package file has the content SHA-256, size and modification time
  that every lock recording it at its old path holds (path map)`

## V5-5. Bookkeeping

- Header comment (line 1): after the Version 4 sentence, add `Version 5 (2026-11-17, after the fourth check): three
  untrue texts corrected and one wording made exact, as paper/supp_build/s3_13/spec/CHANGES_v5.md lists; no number
  changed.`
- Write `OUT\spec\CHANGES_v5.md` as before, and add "## 12. Version 5 (2026-11-17)" to the spec.

## Accepted as they are

Everything that `fix_order_v4.md` accepts, and the fourth check's notes for the writers (E3a's parenthesis read as
examples; coral's empty static file list; E8 on coral's 2,312 test survey visits; coral's 1,000 sampled survey visits
at 722 reef sites). They are not to be reported again.

## What does not change

Every number, interval, count, mark, panel, column and row; the line count (785); every text not named above.
