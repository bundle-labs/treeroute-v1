# Change order for version 4 of the S3.13 tables (2026-11-17): the last table round

Names as in `brief_tables.md`: SHAP, V, ROOT, OUT. The third check of version 3 (`OUT\reconcile\tables_agreed.md`,
SHA-256 86f7eb2a...5919d7) closed every change of version 3, found no wrong number and left twelve minor wording
points, most from its whole-file scan against `ROOT\paper\draft\GLOSSARY.md`. This order fixes them. **No number
changes, and no line is added or dropped** (785 lines). The lead checked every source named below. This is the last
table round: after it, only an untrue text or a number problem reopens the tables; wording preferences go to the text
writers.

Each change gives the printed text of version 3 (OLD) and of version 4 (NEW), each in one code span (wrapped lines
join with one space). Change every place in the spec that states the text (fenced block, constant cell, rule,
decision), so that a builder prints NEW.

## V4-1. Table S3.21, E3m (what the locks are)

`gates.json` E3m `values.rule`: "content SHA-256, size and mtime equal every freeze-lock record of the recorded path";
PROTOCOL L178-179. On NDVI and burned fraction four separate locks record the file.

- OLD: `a moved dataset package file has the content, size and time that the run's locks record (path map)` NEW: `a
  moved dataset package file has the content, size and modification time that every lock recording it at its old path
  holds (path map)`

## V4-2. Table S3.21, E3a (coral's label files; the tree inputs)

Coral's `gates.json` E3a: `not_before_read` is `target_files_sha256`, and its `checked` list lacks it (PM2.5's has it);
the checked feature key is `feature_list (tree-feature prefix)`; GLOSSARY "tree inputs" (other name "tree features").

- OLD: `inputs, before the labels are read, equal the manifest's (dataset package, regions, constants, file lists,
  features)` NEW: `inputs, before the labels are read, equal the manifest's (dataset package, regions, constants, file
  lists (coral bleaching: the static file list only), tree inputs)`

## V4-3. Coral bleaching's locations; "site" (a do-not-use name of "location")

GLOSSARY "location": `a reef site on coral; on coral each survey visit at a site is scored separately (the engine's
unit there is the visit)`. S3.19's Locations column counts coral's 1,000 sampled survey visits (`units_in_sample`).
PROTOCOL L375: coral's B2 is "the visit's saved 50-visit router pool ...: other sites' visits".

- Table S3.19, note ᵇ. OLD: `ᵇ Coral bleaching: a location is a survey visit.` NEW: `ᵇ Coral bleaching: the column
  counts survey visits, the engine's unit there; a location is a reef site.`
- Table S3.19, note ᶜ. OLD: `a pool of other sites' survey visits.` NEW: `a pool of survey visits at other locations.`
- Table 9 caption. OLD: `(forest loss, annual: all of them; coral bleaching: other sites' survey visits).` NEW:
  `(forest loss, annual: all of them; coral bleaching: survey visits at other locations).`

## V4-4. Table 9, the context-and-calendar family

GLOSSARY "router context": other names `context, ctx, standardised context, context columns`. The family's members
are router-context columns (PROTOCOL L487). The family's name is the frozen protocol's (L491-492) and ruling BB4 fixed
defo's label `(no context or calendar input)`, so the panel labels and that label stay; Table 9, where the families
are named, glosses the name once.

- OLD: `local drivers, context and calendar, and the seasonal normal.` NEW: `local drivers, context and calendar (the
  router context), and the seasonal normal.`

## V4-5. Table S3.21, adopted arm of NDVI (GLOSSARY "tree answer": other name "plain answer")

- OLD: `identity, plain answers, uniformly weighted; per-location router` NEW: `identity, plain tree answers, uniformly
  weighted; per-location router`

## V4-6. Table S3.21, E5 and note ᵃ (GLOSSARY "tree bank": other name "bank")

- E5's "What it checks". OLD: `bank fingerprint over every tree array (informational)` NEW: `tree-bank fingerprint
  over every tree array (informational)`
- Note ᵃ. OLD: `the rebuilt bank's fingerprint differs` NEW: `the rebuilt tree bank's fingerprint differs`

## V4-7. Table S3.18 b, column header (the panel now lists naive baselines too)

- OLD: `| Problem | Rival | Why it has no SHAP value |` NEW: `| Problem | Rival or naive baseline | Why it has no SHAP
  value |`

## V4-8. Table S3.22, row label (as Table 9 words the main set)

- OLD: `Rivals in another link that passed their skill guard` NEW: `Rivals that explain in another link and passed their
  skill guard`

## V4-9. Table S3.28, the pair's J (the region weighting, as in Table S3.19)

- OLD: `(the players to which either run gives more than 10⁻¹² of its total)` NEW: `(the players to which either run
  gives more than 10⁻¹² of its total mean absolute SHAP value, with each region weighted equally)`

## V4-10. Table S3.21, E3 (what it is compared with; PROTOCOL L180: "... equal the manifest's")

- OLD: `dataset package fingerprint, the settings that the written rules set, and run fingerprint, after the written
  rules are applied` NEW: `the dataset package fingerprint, the settings that the written rules set and the run
  fingerprint equal the manifest's, after the written rules are applied`

## V4-11. Table S3.21, E8 (PROTOCOL L198: `pre__<arm>` and `arm__<arm>`; Table S3.20 note ᵃ for coral)

- OLD: `kept predictions, pre-clip and clipped, on every test row of every sampled location` NEW: `the adopted arm's
  saved predictions, pre-clip and clipped, on every test row of every sampled location (coral bleaching: every test
  survey visit)`

## V4-12. Table S3.18, source comment (the reference is defined in Section 3.4; `03_protocol.md` L25)

- OLD: `paper/draft/03_protocol.md Section 3.3, paper/draft/tables/table_3.md note d` NEW: `paper/draft/03_protocol.md
  Sections 3.3 and 3.4, paper/draft/tables/table_3.md note d`

## V4-13. Bookkeeping

- Header comment (line 1): after the Version 3 sentence, add `Version 4 (2026-11-17, after the third check): captions,
  notes, a column header, a row label, cells and a source comment reworded, as
  paper/supp_build/s3_13/spec/CHANGES_v4.md lists; no number changed.`
- `OUT\spec\CHANGES_v3.md`, "Expected effect": the S3.25 lines are 354, 358-360, 369 and 373-375 (corrected in version
  4).
- Write `OUT\spec\CHANGES_v4.md` as before, and add "## 11. Version 4 (2026-11-17)" to the spec.

## Accepted as they are (the third check judged them; not to be reported again)

The family labels `Context and calendar` and BB4's `(no context or calendar input)` (see V4-4); `pool` as an
appositive after "router fit rows"; "the engine's unit" in note ᵇ (the glossary's own words); `calendar month`,
`month`, `test year`; `rows`, `sample rows`, `model` used generically; `y units` and `log(y + c)`; `the D8 tolerance`;
`decision D6` and `decision D7`; `LightGBM with a Tweedie loss`; `VT0007, frozen at 2019` (an entry's name);
`block-wise scoring`; `local drivers`.

## What does not change

Every number, interval, count, mark, panel, column and row; the line count (785); every text not named above.
