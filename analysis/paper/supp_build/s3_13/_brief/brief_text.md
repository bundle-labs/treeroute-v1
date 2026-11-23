# Brief: write the SHAP results into the paper (Supplement S3.13, main-text Table 9 and the records)

Names: SHAP = `D:\treeroute\analysis\shap_v1`; V = `SHAP\verify_v1`; ROOT = the research-paper folder (the parent of
`engine\` and `paper\`); D = `ROOT\paper\draft`; OUT = `ROOT\paper\supp_build\s3_13`; STAGE = `OUT\stage`. Read
`OUT\_brief\brief_tables.md` too: it names the analysis sources.

## Goal

Write the post hoc SHAP comparison (rulings AW, AY, AZ, BA, BB; protocol `SHAP\PROTOCOL.md`) into the paper, using the
checked tables in `OUT\reconcile\tables_agreed.md` (version 5: built twice from the stored values with one rounding
step, by the rules of `OUT\spec\TABLE_SPEC.md`, version 5; `OUT\reconcile\cells.json` beside it gives every printed
data number's source, selector and stored value; versions 2 to 5 reworded captions, notes, labels and cells after
four checks, `OUT\_brief\fix_order_v2.md` to `fix_order_v5.md`, and changed no number). Nothing live is edited: every writer works on staged copies under STAGE, at the same
relative path as the live file (for example `STAGE\paper\draft\S3_posthoc.md`, `STAGE\engine\PENDING_PARTS.md`,
`STAGE\shap\PROTOCOL.md`). A writer starts from the staged copy if an earlier writer made one, else from the live file,
and records each change in `STAGE\changes_<writer>.md` (file, place, what, why, source). The lead agent applies the
staged files after the checks.

## What to write (protocol section 10 is the authority on content; rulings BB1-BB6 on presentation)

1. **Supplement S3, new section S3.13** (`D\S3_posthoc.md`, after S3.12): the SHAP comparison, post hoc (ruling AK).
   In the style of S3.1-S3.12: "When and why" (what was asked and ruled, when, and that it ran after the locked results
   and the opened test labels; rulings AW, AY, AZ1, BA, BB); the method paragraph (interventional TreeSHAP with per-row
   backgrounds, the B2 background and what it means, the rebuild of treeroute's trees and the exactness gate before any
   value, the two levels, families, the importances (a player's mean absolute SHAP value, with each region weighted
   equally: protocol section 8's I_m(j)) and the two share bases (top-k shares of the total importance over J; family
   shares of the sum of the five families' mean absolute attributions), J, the statistics and the paired region
   bootstrap, all per protocol sections 3-8);
   the scope (lead 0 of the five problems; the samples); the results with their intervals, as tables (from
   `tables_agreed.md`, placed in the order the spec gives, numbered from Table S3.18) and a short reading of them that
   claims nothing beyond the numbers; the rivals covered and left out with reasons; the exactness gates (with E5
   disclosed as informational: the rebuilt bank's fingerprint differs from the run's on all five problems, while every
   checked tree answer and prediction matches, bit for bit or, on the arcsine arms, within the D8 tolerance; E10 checks
   one sampled location's router fit rows and test rows on PM2.5, NDVI and burned fraction, one survey visit's router
   fit rows and test row on coral bleaching and every sampled location on forest loss, so claim no more than Table
   S3.21 says); treeroute's B1 sensitivity,
   labelled a sensitivity and kept apart (protocol section 10's B1 list; S3.13 prints B1's family shares, top 3 and
   top 10, and says that every B1 player's importance, share and signed mean with its interval is in the archived
   results file of the re-computation, `verify_v1/A/results.json`, key `b1`); the
   independent re-computation (two implementations written from the protocol, each blind to the comparison code and
   outputs, and a reconciliation: every number the official files hold that both also hold agrees within 1e-9; what
   `compare_shap.py` does not do, and how BB1 and BB2 fill it); the BB3 footnote; the BB4 labels and the PM2.5 note;
   BB5; the BB6 disclosure (see the AI rule below); and the "Not claimed" list of protocol section 10, in plain words.
   Facts the table checks established; write them as the tables do, never in the protocol's older words:
   - coral bleaching's B2 background is the survey visit's saved router fit rows, a pool of earlier nearby survey
     visits (not "other sites' visits": some are earlier visits at the same reef site);
   - on NDVI, five router-context columns (`ctx:top5:*`) are exact copies of tree inputs and count with them, as the
     same players (protocol section 5 and section 8's duplicate rule), so NDVI's context-and-calendar family holds
     only the calendar; the family's name is the protocol's: gloss it once as the router-context columns that copy no
     tree input, and keep BB4's label "(no context or calendar input)";
   - E5's fingerprint covers the tree bank, the correctors and the placebos;
   - on coral bleaching E3a compares no data file before the labels are read (its static file list is empty and its
     label-file list cannot be read before the labels), and E8 checks all 2,312 test survey visits, not only the
     1,000 sampled; never say that coral's static files were checked;
   - the importances and every share weight each region equally (protocol section 8), and J is the same set under a
     plain mean (every player outside J is exactly 0 on every row of every model);
   - Table S3.19's coral "Locations" count survey visits, the engine's unit there; a location is a reef site.
   Also: a row for S3.13 in S3.0's index table, and the file's header comment (an edit-history line, the NUMBER
   SOURCES sentence for Tables S3.18 onward naming `OUT\reconcile\tables_agreed.md` and its two builders' scripts, and
   the STATUS line).
2. **Main text** (`D\05_rivals.md`, Section 5.4): two to four sentences that introduce the comparison, cite Table 9,
   state the main reading with its intervals and the labels "post hoc", and say what it does not claim (SHAP shows what
   a model uses, not what causes the outcome; agreement is not correctness), pointing to S3.13. Table 9 goes in a new
   table file `D\tables\table_9.md` (caption "**Table 9.** ...", the body from `tables_agreed.md`, the notes the rulings
   require: BB1's note, BB4's labels and PM2.5 note, fire's link note), and `D\TABLE_NUMBERS.md` gains its row. Keep
   the caption's definitions as `tables_agreed.md` gives them; in particular the own-history share is a family share
   (the own-history family's share of the sum of the five families' mean absolute attributions), not the sum of the
   own-history variables' shares, and the 5.4 sentences must not describe it otherwise. Keep
   the main text short: it is over its word budget, and this adds only what protocol section 10 asks for.
3. **The records**:
   - `ROOT\paper\PAPER_FACTS.md`: new facts (section 9, post hoc; next free IDs; each with its source path and the
     status "final, post hoc (Part 628)") for every number that the prose of S3.13, Section 5.4 or the S1 rows cites;
     the status key gains a line for Part 628 if needed. Also the stale bullet in the slim-data list that still reads
     "Not until confirmed" for the SPI and ONI files becomes "Kept out: cited, not shared (ruling AV10)" (decided by
     the agent on 2026-11-13, "going ahead unless objected"; no objection came).
   - `ROOT\engine\PENDING_PARTS.md`, Part 628: its heading says DRAFT and "nothing run at scale"; add a dated addendum
     (2026-11-17) in the log's style: the runs (scope (i), dates, the gates), the B1 runs, the independent
     re-computation and its result, rulings AY, AZ1, BA and BB, what the paper reports and where; update the heading's
     status words in the log's style (the log keeps old text; it adds).
   - `D\S1_disclosures.md`: new rows in S1.7 (post hoc), continuing PH21 (for example: the SHAP comparison itself, its
     sample and what it does not claim; the B1 sensitivity; what `compare_shap.py` does not do and BB1/BB2; the coral
     comparison table read before the independent re-computation, BB6, owner question C10; anything else the sources
     require, such as E5 or the open item D7, the Kraft LSTM left out; how the tables were built: twice, by two
     independent builders from the stored values, reconciled and checked, and versions 2 to 5 reworded captions,
     notes, labels and cells after four checks, with no number changed; B1's per-player values given through the archived results file, although
     protocol section 10 lists them for S3.13); RP18 gains a clause on the agents' part in the SHAP analysis (the
     design workflow, the scripts, the runs the author started, the independent re-computation's implementers and
     checkers, the S3.13 table builders, reconciler and checkers, and the writers and checkers of this write-up);
     S1.10's counts follow.
   - `D\S4_provenance.md`: Table S4.13 gains rows AW, AX, AY, AZ, BA and BB (date, one-line summary, the author's
     recorded words, in the table's style), the text above it says "A to BB" and its [PENDING] marker about AW and AX
     closes; the S4.2 timeline gains rows for 2026-11-12 to 2026-11-16 (UTC; the SHAP design, the pilot and runs, the
     rulings, B1, the re-computation); Table S4.11 (post hoc analysis code) gains a Part 628 row with its files and
     hashes, in its style (the SHAP analysis scripts, and the two S3.13 table builders' scripts
     `OUT\A\scripts\build_tables.py` and `OUT\B\scripts\build_tables.py`), and its comment gains their full hashes (read
     them yourself with SHA-256); S4.12 and Table
     S4.14 if they list such files.
   - `D\GLOSSARY.md`: the terms S3.13 and Table 9 introduce (for example SHAP value, interventional TreeSHAP,
     background, Kendall's W, rank-biased overlap, consensus, same-link and cross-link, structural zero), in its table
     style.
   - `D\REFERENCES.md` section A: every new author-year citation, checked as the file's "How each entry was checked"
     paragraph says (doi.org and the Crossref record; fetch them), with Key, Supports and Check notes. Candidates:
     Lundberg et al. 2020 (TreeSHAP), Lundberg and Lee 2017, Janzing et al. 2020 (interventional Shapley values),
     Webber, Moffat and Zobel 2010 (RBO), Kendall and Babington Smith 1939 (W). Cite only what the text uses.
   - `ROOT\_archive_plan\ARCHIVE_MANIFEST_DRAFT.md` (sections 2.5, 4.1 and 4.2, totals in 7): the SHAP folder
     (`TR\analysis\shap_v1`): what is archived (scripts, protocol, run commands, sample register, compare outputs,
     the re-computation `verify_v1/`, logs if clean), what is kept out (coral's row-level files, decision D13 and
     protocol section 9; `engine_runs/`, `engine_tmp/` and the smoke worlds' engine folders, which hold the account
     name; anything else by its rule), with file counts and bytes from your own listing (os.stat only; never enter
     `smoke\bardl_fix\`; give that folder's handling by rule, not by its contents). Also the S3.13 table build folder
     `ROOT\paper\supp_build\s3_13\` (the spec, both builders' scripts and outputs, the reconciler's and the checkers'
     scripts and outputs), in the manifest's style for the paper's build folders. `D\09_availability.md` and
     `D\submission\software_data_availability.md` and Supplement S9.6 if they list the analysis folders.
   - `SHAP\PROTOCOL.md` section 14: a short dated entry (2026-11-17): S3.13 and Table 9 written from the compare files
     and `V\A\results.json` through `OUT\reconcile\tables_agreed.md`; no SHAP script ran and no SHAP file changed; who
     read what (the table rounds: `OUT\_brief\reads_tables.md`; the writers and checkers of this write-up, by their
     own records). The entry also records one correction of the protocol's wording, without editing the old lines:
     lines 375 and 381-382 call coral's B2 pool "other sites' visits", but 980 of the 50,000 background visits are
     earlier visits at the explained visit's own reef site (in 415 of the 1,000 sample rows), and none is dated on or
     after it; the paper says "a pool of earlier nearby survey visits" (`OUT\_brief\lead_checks\verify_v5_claims_out.txt`).
     PROTOCOL.md is hash-pinned: stage
     it as `STAGE\shap\PROTOCOL.md`; the lead applies it. Its format rules: LF only, no BOM, one final LF, prose lines at
     most 120 characters, sections 3 and 8 byte-identical.
   - `ROOT\paper\PAPER_OUTLINE.md` and `ROOT\_archive_plan\OPEN_ITEMS_2026-11-11.md`: update a SHAP status line if one
     exists.

## Paper rules (the build enforces several; `ROOT\paper\build\BUILD_README.md`)

- **AI terms only in S1 and S4** (and, in the main text, Section 2.9's paragraph and the declaration). The owner asked
  for no AI mention at all; the paper keeps the required disclosures only there (rulings file, the AT11 row and the
  "On AT11" note). So S3.13, Section 5.4, Table 9 and every other supplement use no AI term and no "agent": the
  re-computation is "two independent implementations", and BB6's disclosure in S3.13 states what was read and when
  (coral's `AW4_table.md`, the current coral comparison's table written 2026-11-13 at 00:06, read on 2026-11-13 at
  about 15:31, before the independent re-computation; the re-computation's implementers A and B never opened it) and
  points to the S1 row that says who read it ("an agent", S1's term). Table S3.22's note d already says this and that
  "Supplement S1.7 records who read it", so that S1 row goes in S1.7, and it is required: the checks confirm it before
  the tables go live. Do not edit `D\submission\ai_declaration.md` (ruling AT11 is open).
- **Visible text holds no absolute local path** (a `D:/...` path only inside HTML comments); sources and fact IDs go in
  HTML comments, as in the existing sections; the build strips them.
- **Citations** in author-year form must resolve to exactly one entry of `D\REFERENCES.md` section A.
- **Tables** are numbered in order of first appearance; a table file must be cited; S3.13's tables are written in the
  section. Cross-references must name existing sections and tables. Copy the tables, their captions, notes and source
  comments as `tables_agreed.md` gives them; change a caption or note only for a point your task lists (the last
  table check's notes for the writers) or a clear error, and record each such change with its reason in your changes file; never
  change a table cell.
- **Terms**: GLOSSARY.md's paper terms (burned fraction, forest loss, coral bleaching; location, region, survey visit;
  our final answer; skill guard; the rivals' names), not its "do not use" names, except where a table needs a code name.
  S1 and S4 say "the author" (ruling AT20). Every number from this analysis is labelled post hoc.
- **Numbers**: never retype a number from memory; every prose number has a fact ID in a comment; every table number
  comes from `tables_agreed.md` unchanged. Do not re-round a printed number. A prose number that the tables do not
  print is formatted once from its stored double (find it through `OUT\reconcile\cells.json` or the source file),
  never from a printout with other digits: 131 of the tables' two-decimal numbers would print differently if
  re-rounded from the three-decimal values of `V\reconcile\report.md` section A6 (for example PM2.5's own-history
  share is stored as 0.18525... and prints 0.19, but "0.185" would give 0.18).
- **Edit-history comments**: each touched file gets a short dated HTML comment in its existing style naming this pass
  ("S3.13 write-up, 2026-11-17") and the pre-edit copy `draft/_snapshots/@@SNAP@@/` (the lead fills the folder name).
- **Privacy**: no user name, account or host name, e-mail address, user-folder path, session id or workflow id in any
  file. **Owner markers**: add an `[OWNER: ...]` marker only for a decision only the author can make; prefer none.
- Python only as `py -3.9 -I -B <script>` (the build itself: `py -3.12 -I build_docx.py`, see BUILD_README). Never open
  `SHAP\smoke\bardl_fix\`; never Grep or Glob over SHAP with a `*.md` pattern; run no SHAP or `V` script. Do not write a
  file named like a report; return what you are asked for as the structured output.
