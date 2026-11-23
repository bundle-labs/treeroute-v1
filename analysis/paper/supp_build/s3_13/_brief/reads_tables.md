# What the S3.13 table rounds read (for PROTOCOL.md section 14)

Names as in `brief_tables.md`: SHAP, V, ROOT, OUT. Compiled by the lead on 2026-11-17 from each table agent's own
record: its returned notes (kept with the workflow records) and, for the spec writer, section 8 and the closing
items of sections 9 and 10 of `OUT\spec\TABLE_SPEC.md`. "Printouts" are the comparison's ten tables
`SHAP\out\<problem>\lead_0\compare\AW3_table.md` and `AW4_table.md`. No agent of these rounds ran a script of
`SHAP\scripts`, `V` or `V\_lead\scripts`, changed a file under SHAP, or opened `SHAP\smoke\bardl_fix\`. Every agent
wrote only in its own folder under OUT.

## Version 1 (table spec, two builders, reconciler, checker)

- **Spec writer**: read the printouts (formats only) and `V\reconcile\report.md` (fourth version: the lead's note,
  sections 1-6, the addendum A1-A6 and the first rows of A7), with `SHAP\PROTOCOL.md` in full, the rulings AW to BB and
  the other files listed in section 8 of the spec. One slip, recorded there: a Grep with a `*.md` pattern over
  `SHAP\out` (for "-0.00"), which matched nothing and showed no line.
- **Builders A and B** (independent of each other): opened neither the printouts nor `V\reconcile\report.md`; only the
  spec's section-1 sources. Builder A's exploration script also printed the set-up and "done in" lines of coral's
  `SHAP\logs\tr_shap_coral_lead0.log`, which section 1 does not list; nothing from it is printed or used.
- **Reconciler**: through its scripts, by name, the ten printouts (to compare the tables with them) and
  `V\reconcile\report.md` section A6 (after a heading search of that one file), besides the section-1 sources.
- **Checker**: read `V\reconcile\report.md` sections A4 and A5 (to check notes and captions); coral's `AW4_table.md`
  only by its file time (2026-11-13 00:06:12).

## Version 2 (spec fixer, the two builders, reconciler, checker)

- **Spec fixer**: no printout and not `V\reconcile\report.md`; the files listed at the end of section 9 of the spec.
- **Builders A and B**: no printout and not `V\reconcile\report.md`.
- **Reconciler**: as in version 1 (the printouts and report A6 through its scripts, by name).
- **Checker**: no printout and not `V\reconcile\report.md`.

## Version 3 (spec fixer, the two builders, reconciler, checker)

- **Spec fixer**: no printout and not `V\reconcile\report.md`; the files listed at the end of section 10 of the spec,
  among them `SHAP\scripts\tr_rebuild.py` and `ROOT\engine\treeroute\pipeline\stages.py` (read, not run).
- **Builders A and B**: their task forbade the printouts and `V\reconcile\report.md`, and their records name none; they
  read the order, the spec's change list, the spec, their own scripts and outputs, and (through their scripts) the
  section-1 data files.
- **Reconciler**: as before (the printouts and report A6 through its scripts, by name).
- **Checker**: no printout and not `V\reconcile\report.md`; it read `SHAP\scripts\tr_rebuild.py` lines 690-755 and
  `ROOT\engine\treeroute\pipeline\stages.py` lines 165-201 (read only, not run), with PROTOCOL, GLOSSARY and the paper
  files that the order names.

## Version 4

- **Spec fixer**: no printout and not `V\reconcile\report.md`; the files listed at the end of section 11 of the spec.
- **Builders A and B**: as in version 3 (their task forbade the printouts and the report; their records name none).
- **Reconciler**: as before (the printouts and report A6 through its scripts, by name).
- **Checker**: no printout and not `V\reconcile\report.md`. Besides PROTOCOL, GLOSSARY, `03_protocol.md` and the
  five `gates.json`, it read (read only, nothing run) `SHAP\scripts\tr_rebuild.py`, the engine's `run.py`, the
  re-computation's scripts `V\A\scripts\a20_b1.py`, `a_core.py` and `a_lib.py`, `ROOT\engine\datasets\ndvi\features\build.py`
  and `ROOT\engine\datasets\coral\catalog.yaml`, and, through its scripts, each NDVI model's `meta.json`,
  `per_lead.json`, `importance.parquet` and `families.parquet`, and coral's treeroute `background_keys.parquet` and
  `rows.parquet` (keys and dates, to count the background visits at the explained visit's own reef site).

## The lead (all rounds)

No printout and not `V\reconcile\report.md`. Read: the agreed tables of each version, the change orders and the
agents' returns; `SHAP\PROTOCOL.md` (sections 4.1, 5 and 8 and the lines the orders cite); the rulings file
(sections AW to BB); GLOSSARY, `05_rivals.md`, `S3_posthoc.md` (headings), `TABLE_NUMBERS.md` and BUILD_README;
`V\_lead\outputs\bardl_maxima.txt` and `bardl_ties.txt`; the E3a, E3m, E3 and E6 values of the rebuild `gates.json`;
lines of `SHAP\scripts\tr_rebuild.py` and of the engine's `stages.py` (gate E6; read, not run); and, by a print-only
script, each model's `meta.json` field `duplicates_merged` and the keys and dates of coral's treeroute
`background_keys.parquet` and `rows.parquet` (to check the version-5 order).

## Version 5 (the tables' final version)

- **Spec fixer**: no printout and not `V\reconcile\report.md`; the files listed at the end of section 12 of the spec,
  among them, through its source-check script, coral's treeroute `background_keys.parquet` and `rows.parquet` (first
  their schemas and five rows of their columns other than the SHAP values, then keys and dates) and each model's
  `meta.json`.
- **Builders A and B**: as before (their task forbade the printouts and the report; their records name none).
- **Reconciler**: as before (the printouts and report A6 through its scripts, by name).
- **Checker**: no printout and not `V\reconcile\report.md`. It read (read only, nothing run) the engine's
  `route/neighbour.py`, its constants, `fit/bank.py` and `fit/tables.py`, `SHAP\scripts\tr_rebuild.py`, PROTOCOL,
  GLOSSARY and `02_method.md` line 53, and, through its scripts, each model's `meta.json` and variable map, the five
  `gates.json`, and coral's treeroute `background_keys.parquet` and `rows.parquet` (keys, dates and the saved pools).
