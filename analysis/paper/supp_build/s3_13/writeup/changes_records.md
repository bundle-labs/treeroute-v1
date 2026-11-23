# Changes: writer records (Part 628's log entry, the archive plan, the SHAP protocol's change log and the outline; S3.13 write-up, 2026-11-17)

Names as in the brief: SHAP = the SHAP analysis folder (D:/treeroute/analysis/shap_v1); V = SHAP/verify_v1; ROOT = the
research-paper folder; D = ROOT/paper/draft; OUT = ROOT/paper/supp_build/s3_13; STAGE = OUT/stage; TR = D:/treeroute.
Only staged copies were written; no live file was edited. No staged copy of these files existed, so each was first copied
byte for byte from the live file (STAGE/_scripts/records/stage_copy.py, SHA-256 checked equal for the live file, the
staged copy and a base copy in STAGE/_scripts/records/work/base/). build_records.py rebuilds every staged file from its
SHA-checked base copy, so each can be rebuilt from its start point. Every edit is an insertion at an exact anchor that
occurs once, except the replacements listed below; check_records.py confirms that no line was deleted.

## Files

| Staged file | Start | Start SHA-256 (bytes) | Staged SHA-256 (bytes) | Encoding, line endings |
|---|---|---|---|---|
| STAGE/engine/PENDING_PARTS.md | copy of ROOT/engine/PENDING_PARTS.md | 0380e743511a0b02bef1f7f12743eb70f129ade2159adc7ae6ecc38bb9a112fd (192,198) | 1d9e57502c405d342eaf2fd0c226ae33f26a16cfd32c345f3b0c7b311c87f695 (199,166) | UTF-8 without BOM, LF, one final LF (kept); inserted text ASCII only, as the log is |
| STAGE/_archive_plan/ARCHIVE_MANIFEST_DRAFT.md | copy of ROOT/_archive_plan/ARCHIVE_MANIFEST_DRAFT.md | 5a6894015ed37a0ceec96a596c4bd7cb69052b0551bbba570fb551a9fcbdace2 (174,020) | 98835dfcc69ef8346553000f46d1bae994a79aedcb92cc2a51d46950bd84a49f (193,259) | UTF-8 without BOM, LF, one final LF (kept) |
| STAGE/shap/PROTOCOL.md | copy of SHAP/PROTOCOL.md (hash-pinned; the lead applies it) | 32daa77b893cf7af378b3145a285fa71c0cec61b0b3a51420195415658618abc (122,349) | f59c52b6fe3d396608314f8f4c557bd3347c735ecfa9b778068d06f28b9a56b8 (128,823) | UTF-8 without BOM, LF only, one final LF; inserted lines ASCII, at most 119 characters; sections 3 and 8 byte-identical |
| STAGE/paper/PAPER_OUTLINE.md | copy of ROOT/paper/PAPER_OUTLINE.md | d6d80bd1ee245b54b7dbd2d94ef33ce9545b70b4c45046b9d3c646db33d0ac66 (54,474) | 7a5a8a2a4ad8b97f1ee8eb4969532db5d051a6be21baf823d545f2b38d88c449 (55,139) | UTF-8 without BOM, LF, one final LF (kept) |

Not staged and not changed (read, SHA-256 of the live file, and why):

| Live file | SHA-256 | Why unchanged |
|---|---|---|
| D/09_availability.md | 666297a2f33a31de119a3e89c1ed57e20af95ee587f20c36c7e646f2bea75aa2 | It lists no analysis folder: Code names the engine and rival-tool versions, Predictions the predictions and the files kept out, Inputs the rebuild tables and one archive path (the region map's script, analysis/paper/figures/fig_map/fig_map.py). Its promises still hold under the plan: no NumPy or compressed file and none of the engine's fitted trees enters the archive (plan 4.2 I) |
| D/submission/software_data_availability.md | e9dcae0c0ff021a5574b9fa566a025212ed9557425436d4fe7df277c0a756fd9 | It lists no analysis folder ("What the software archive holds" names the rival tools and the engine versions and points to Supplement S4.12); its Access form line ("No pickle, NumPy or compiled Python file is included") stays true, because the plan keeps the SHAP folder's NumPy and compressed files out |
| D/S9_inputs_licences.md (S9.6) | fdd9b485d16cfeee85824444273b04e962083de331c1dc20e5e495847d4862d9 | S9.6 lists licence points and kept-out files, not analysis folders. It does not name the SHAP files the plan keeps out; that is left to the lead (plan section 8, item (b); open points) |
| ROOT/_archive_plan/OPEN_ITEMS_2026-11-11.md | 391cb3c78602be3f94d2539e5a98a88052a709b12736a80cc8697a4dfab0f696 | It holds no SHAP status line (no SHAP, Part 628, S3.13 or ruling AW-BB in it) |

## engine/PENDING_PARTS.md (Part 628)

| # | Place (staged line) | What | Why | Source |
|---|---|---|---|---|
| P1 | Line 1500, Part 628's heading (replaced) | The status words are updated in the style of Part 627's heading ("(SIGNED BY THE OWNER ...; RUN ..., ALL 12 CHECKS PASSED)"): "(DRAFT 2026-11-12; RUN 2026-11-12 TO 2026-11-16 AT SCOPE (i), B1 INCLUDED, EVERY PIECE FINISHED, E5 INFORMATIONAL; RE-COMPUTED INDEPENDENTLY 2026-11-16; WRITTEN UP 2026-11-17, SUPPLEMENT S3.13 AND TABLE 9)", and the rulings list becomes "AW1-AW5, AY1-AY3, AZ1, BA1-BA3, BB1-BB6". Every old word is kept, with its date: "NOTHING RUN AT SCALE (2026-11-12)", "RULINGS D8 AND D14 NEEDED FIRST (RULED 2026-11-13: AY3 AND AY2)", "THE NOWCAST COSTS 43-50 MACHINE HOURS (ESTIMATE OF 2026-11-12)" | Brief item 3 (the heading says DRAFT and "nothing run at scale"; update its status words in the log's style; the log keeps old text) | Part 627's heading history (snapshots of 2026-10-28: "(PREPARED)", then "(PREPARED; SIGNED ...; NOT RUN YET)", then the live form); rulings AY-BB; facts A9, A12 |
| P2 | Lines 1553-1561, the end of Part 628 (and of the file) | A dated addendum, in the style of Part 627's RUN and RESULT bullets and the "addendum" bullets of Parts 626 and 627: its lead bullet (2026-11-17; the S3.13 write-up; pre-edit copy paper/draft/_snapshots/@@SNAP@@/; post hoc, no headline number changes; the record is the protocol and RUN_COMMANDS.md; the paper's numbers are the facts of section 9 from A9 on) and eight sub-bullets: Rulings (AY1-AY3, AZ1, BA1-BA3, BB1-BB6 with their dates and answers; the other defaults, D7 and D10); Runs (scope (i), the coral pilot, the last comparison, the samples, fire's E0 stops, the ridge and BARDL loaders after the freeze); Gates (E5 informational; treeroute's and the rivals' exactness counts; S-ADD, S-EVAL, S-RESID, S-ZERO; coral's E3a and E8); B1 (the command's times; defo's identity check); the independent re-computation (agreement within 1e-9 on all 2,000 draws but three explained groups; compare_shap.py's three departures and how BB1 and BB2 fill them; no SHAP script run or edited); what the paper reports and where (S3.13's parts and Tables S3.18-S3.30, Table 9 and Section 5.4, tables_agreed.md v5, the main reading with its intervals, what is not claimed, BB6, S1.7 and S4); Archive (plan only); Still open (D7, E5's cause) | Brief item 3 (the runs with scope, dates and gates; the B1 runs; the re-computation and its result; rulings AY, AZ1, BA and BB; what the paper reports and where) | Facts A9, A10, A12, A14, A15, A16, A17, A21, A23, A25 (staged PAPER_FACTS.md); SHAP/PROTOCOL.md sections 1, 2, 10, 12, 14; SHAP/RUN_COMMANDS.md; ROOT/engine/OWNER_RULINGS_2026-10-06.md sections AY, AZ, BA, BB; tables_agreed.md captions S3.18-S3.30 |

Fact IDs are given inline, as the log cites facts (for example "fact K90"); the log has no HTML comments. Negative numbers
use the log's ASCII hyphen ("-0.02 [-0.08, 0.07]") where facts A16 and A17 print U+2212; no digit differs.

## _archive_plan/ARCHIVE_MANIFEST_DRAFT.md

Measured for this pass (UTC): the two folders listed by os.scandir and os.stat only, 2026-11-17 09:34:20-09:34:21
(list_folders.py; SHAP/smoke/bardl_fix/ pruned before any listing call, so never entered and not counted; no reparse
point, no error); a count-only privacy scan of OUT's 226 archived files, 10:04:44-10:04:48 (privacy_count_out.py; the
names are taken from the environment at run time and never printed). No file of SHAP was opened by these scripts. The
groups and totals come from classify.py (rules in its header) and are filled into the texts by build_records.py from
work/classify.json and work/listing_shap.json (work/tokens.json keeps every filled value).

| # | Place (staged line) | What | Why | Source |
|---|---|---|---|---|
| A1 | Line 3, header paragraph (appended) | A sentence naming this pass (S3.13 write-up, 2026-11-17; pre-edit copy under paper/draft/_snapshots/@@SNAP@@/), what it adds and where, and that only the two folders were listed | Brief: edit-history rule, in the file's own style (it records its revisions in this paragraph; it has no HTML comments) | - |
| A2 | Line 5, "Measured" bullet (appended) | The listing and scan times (UTC) and that no SHAP file was opened | The plan's style: every measurement with its time | list_folders.py and privacy_count_out.py outputs |
| A3 | Line 21, attention item 1, new last sub-bullet | One more default beyond the rulings' words: the gridded row-level SHAP values (23 files, 59,524,068 B) kept out beside coral's (D13), why, and "You may let them in" | The plan lists every default beyond the rulings' words here for the owner | classify.py group K2; SHAP protocol sections 5 and 9 (D13) |
| A4 | Lines 38-39, section 0, after the table | Dated note: the totals with the two folders (main archive 5,721 files, 4,675,415,873 B; GitHub part 2,966 files, 217,205,351 B; kept out 20,277 files, 48,392,823,794 B), pointing to section 7; the rows above are the fourth revision's | Totals follow (brief: "the totals of section 7 follow"); section 0 repeats them, so it points there | tokens.json |
| A5 | Lines 69-70, section 1, after the paragraph under the table | Dated note: analysis/ gains the two folders (1,183 files, 594,527,726 B; GitHub 1,040 files, 108,916,833 B) and the new total; the rows above are the fourth revision's | As A4 | tokens.json |
| A6 | Lines 172-174, 2.5 table: two new rows, and the Total row replaced | Row TR\analysis\shap_v1 (575 files, 79,948,811 B: what is archived, who cites it, the GitHub split, what is kept out and left out); row ROOT\paper\supp_build\s3_13 as analysis/paper/supp_build/s3_13/ (226 files, 32,661,953 B: spec, A, B, reconcile, skeptic, _brief; who cites it; stage left out); Total 1,183 files, 594,527,726 B, with the old total (382 files, 481,916,962 B) kept in its notes cell | Brief item 3: the SHAP folder and the S3.13 build folder, with counts and bytes from my own listing, in the manifest's style for the paper's build folders (paper/figures is archived as analysis/paper/figures/, keeping its project-relative path) | listing and classify.py; protocol sections 9 and 10; facts A9-A25 (who cites) |
| A7 | Lines 184-189, 2.5, two bullets after "Not included" | The SHAP folder by rule: archived (each group with its count, and why: scripts, protocol, run commands, sample register, machine file, logs if clean, _snapshots, run summaries, compare/ without the NumPy draws, every piece's records, the gridded background keys, samples and rebuild check files, coral's sample manifest, the rebuild records, verify_v1 without NumPy and compressed files); kept out (pointing to 4.2 I); left out (smoke/, with smoke/bardl_fix/ by rule, not by its contents); not opened (what the packaging scans must check). The S3.13 table build: what is archived and left out, the count-only privacy scan's result, and the two coral survey-visit keys printed in one lead check output | Brief item 3 (what is archived and what is kept out and why; logs if clean; bardl_fix's handling by rule) | as A6; RUN_COMMANDS.md section 4 (privacy_scan); protocol sections 4.2, 9, 14 |
| A8 | Line 423, 4.1, new bullet before the Licence bullet | The SHAP analysis's archived row-level files (46 Parquet files, 7,369,055 B: keys and predictions, columns not read), its aggregates, and what is kept out | Brief: section 4.1 | as A6 |
| A9 | Lines 499-510, 4.2, new block I after H | "I. The SHAP analysis (Part 628) ..." 3,574 files, 4,755,149,138 B, in a table: coral's row-level files (19; D13); the gridded row-level SHAP values (23; a default under the keep-out rule D1, since a linear model's SHAP value is proportional to its input's difference from the background mean, and the ridge dumps are archived); engine_runs/ (1,994; account name, D13); the rebuilt banks, routers and random forests (1,515; none of the engine's fitted trees is archived, coral's are derived CoralTemp products, NumPy type); the NumPy and compressed record files (23; the file-type rule of 7.1 and the Access form) | Brief: section 4.2 (coral's row-level files, D13 and section 9; engine_runs/, engine_tmp/ (absent: no such folder exists) and the smoke worlds' engine folders; anything else by its rule) | as A6; protocol sections 5, 8, 9, 12 (D12, D13); 09 "Inputs"; software_data_availability.md Access form |
| A10 | Lines 512-513, 4.2, after the Total paragraph | Dated note: with I, 20,277 files, 48,392,823,794 B; A-H not re-measured | Totals follow | tokens.json |
| A11 | Line 521, the KEPT_OUT.md line (appended) | "and the items of I" | KEPT_OUT.md lists every kept-out item | - |
| A12 | Lines 703-704, 6.5, after the "After the planned cleaning" paragraph | Dated note on privacy: the two folders fall under the packaging scans; the table build's count-only scan found nothing; the SHAP files were not opened; the engine-written folders are kept out | The plan's privacy section; brief privacy rule | privacy_count_out.py; RUN_COMMANDS.md section 4 |
| A13 | Lines 711, 713, 716, section 7 table (three rows replaced) | Main archive 5,721 / 4,675,415,873 / 4.68 / 4.35; main + 5A 8,520 / 5,331,402,235 / 5.33 / 4.97; GitHub part 2,966 / 217,205,351 / 0.22 / 0.20 (GB = 10^9 B, GiB = 2^30 B, two decimals, computed by script) | Brief: "the totals of section 7 follow" | tokens.json (old totals + the two folders' archived files) |
| A14 | Lines 719-720, section 7, after "Changes since the third revision's listing" | "Changes since the fourth revision's listing": what was listed, what was added (801 files, 112,610,764 B; 735 files, 98,639,502 B to GitHub), what 4.2 I and appendix A take, and the totals before this round (the replaced numbers, kept) | The plan records each revision's changes here | tokens.json |
| A15 | Line 751, 7.1, new bullet | The added files by type (.py 367, .json 204, .parquet 66, .md 62, .log 50, .txt 41, .jsonl 7, .yaml 1, three .before_fix copies); no type that the Access form excludes | 7.1 feeds the Access form line | classify.py archived_ext |
| A16 | Line 766, 7.2 GitHub | The GitHub part's largest files are now the two mismatches.json copies (16,321,120 B each); still under 25 MiB | 7.2 named the largest GitHub file | classify.py (largest archived files) |
| A17 | Line 775, 7.2 zips | analysis.zip about 594.5 MB | 7.2 sizes the zips | tokens.json |
| A18 | Line 782, 7.2 | Staging about 4.7 GB (5.3 GB with 5A); the 367 added .py files (4,131,267 B) are not in the program-size counts | 7.2 gives staging and program size | tokens.json |
| A19 | Line 828, section 8 "For the lead", new item before "Done since the third revision" | (a) S3.13 may call verify_v1/A/results.json archived (archive path analysis/shap_v1/verify_v1/A/results.json); (b) S9.6 does not name the SHAP keep-outs; (c) 09, the software and data availability section and S9.6 list no analysis folder, unchanged, promises hold; (d) PROTOCOL.md's hash changes when its entry is applied; keep the 32daa77b copy in SHAP/_snapshots | The plan's list of paper-text items for the lead | S3.13 writer's open point; this pass |
| A20 | Lines 857-858, appendix A, two new rows | TR\analysis\shap_v1\smoke (6,952 files, 1,033,307,203 B; the smokes' engine folders 787 files, 109,465,128 B; bardl_fix by rule, not entered, not counted) and ROOT\paper\supp_build\s3_13\stage (55 files, 2,817,928 B when listed) | Appendix A lists what is left out because nothing needs it | listing; classify.py |
| A21 | Lines 916-921, appendix B, new entry at the end | "S3.13 write-up (2026-11-17; pre-edit copy ...)": what changed and the new totals | The plan's change record | - |

## shap/PROTOCOL.md (section 14)

| # | Place (staged line) | What | Why | Source |
|---|---|---|---|---|
| R1 | Lines 1225-1283, a new last entry of section 14 (after the entry of 2026-11-16) | "- 2026-11-17, no method change; sections 3 and 8 are untouched, and nothing that is reported changes: the write-up ...": its lead paragraph (what the entry gives; the pre-edit copy 32daa77b... saved in _snapshots/@@SNAP@@/ beside paper/draft/_snapshots/@@SNAP@@/); "What was written, and from what" (the compare files, V/A/results.json and the B1 log lines, through tables_agreed.md v5 and cells.json; two builders, one spec, a reconciler and a checker per version; versions 2-5 changed no number; facts A9-A25); "Nothing of this folder ran or changed" (no script run; no file written but this one; the metadata listing at 10:34, bardl_fix not entered); the correction of lines 375 and 381-382 (and section 10's lines 673-674), without editing them: 980 of the 50,000 background visits are earlier visits at the explained visit's own reef site, in 415 of the 1,000 sample rows, none dated on or after it; the paper says "a pool of earlier nearby survey visits"; "What was read" (the table rounds from reads_tables.md; the four earlier writers from their returned lists; this writer's own reads), then the single line @@LATER_READS@@ for the S1/S4 writer and the checks that follow, and the closing post hoc bullet of the earlier entries | Brief item 3 (PROTOCOL.md section 14: the dated entry, its correction note, who read what; LF, no BOM, one final LF, prose lines at most 120 characters, sections 3 and 8 byte-identical) | OUT/_brief/reads_tables.md; OUT/_brief/lead_checks/verify_v5_claims_out.txt line 33; the four writers' returned "opened" lists; facts A9, A11; the protocol's earlier entries (style) |

Times in the entry are local (UTC+1), as the protocol records them; the listing ran at 09:34 UTC, 10:34 local.

## paper/PAPER_OUTLINE.md

| # | Place (staged line) | What | Why | Source |
|---|---|---|---|---|
| O1 | Line 344, a bullet under decision O3 (whose line 343 says "No SHAP analysis exists for v1 (X3)") | "- **RULED AW (owner, 2026-11-12): SHAP is run on all five problems and its results go into the paper, labelled post hoc (ruling AK); scope (i), the nowcast (AY1, 2026-11-13).**" AW amends O3 as confirmed by AT17 (e); the line above is the outline's of 2026-10-26; run 2026-11-12 to 2026-11-16 (Part 628) and written up 2026-11-17 (S3.13, Tables S3.18-S3.30, Table 9, Section 5.4; facts from A9 on); the pass and the pre-edit copy paper/draft/_snapshots/@@SNAP@@/ | Brief item 3 (update a SHAP status line if one exists); in the style of O7's "RULED AS" bullet, which keeps the decision text as the record of the recommendation | Ruling AW1 (it amends O3 as confirmed by AT17 (e)); AY1; A9 |

The outline has no HTML comments, so the pass and its pre-edit copy are named inside the bullet, as its other dated
notes do. No other outline line names SHAP; its tables list (section 5) and status table (section 0) were not changed.

## Numbers

- PENDING_PARTS.md, PROTOCOL.md and PAPER_OUTLINE.md: every number token of the inserted lines was looked up by
  check_records.py in the sources (the staged fact sheet, SHAP/PROTOCOL.md, SHAP/RUN_COMMANDS.md, the rulings file,
  verify_v5_claims_out.txt, reads_tables.md, the brief): none is missing. The prose numbers of the addendum are those of
  facts A9-A25 as printed there (A16 and A17's intervals with the log's ASCII minus).
- ARCHIVE_MANIFEST_DRAFT.md: every count, byte total, GB/GiB/MB figure and time is filled by build_records.py from the
  listing (work/classify.json, work/listing_shap.json, work/privacy_count_out.txt); none was typed. The old totals the
  new ones build on (4,920 / 4,562,805,109; 2,231 / 118,565,849; 16,703 / 43,637,674,656; 382 / 481,916,962;
  305 / 10,277,331; 2,799 / 655,986,362) are constants checked against the base manifest's text. check_records.py
  finds no other number token in the inserted lines except the plain words 1,000 (the sample), 179 and 204 (the type
  counts, matched with a trailing comma) and 5.4 (a section).

## Checks run (check_records.py, on the final build)

- Insertions only, except P1 (heading), A1, A2 and A11 (lines appended: each old line is the prefix of its new line),
  A6's Total row and A13's three rows; no line deleted.
- All four files: UTF-8 without BOM, LF only, one final LF.
- PROTOCOL.md: inserted lines ASCII and at most 119 characters; the two @@SNAP@@ lines are at most 91 characters, so a
  folder name of up to about 37 characters keeps them under 121; one @@LATER_READS@@ line. Section 3 (from its heading
  to the heading of section 4): SHA-256 28d54cbd9df90ae613454587401ab1c6f87e7d74e61bc3895076a333f47d84c3, 3,767 bytes,
  equal in the live and the staged file; section 8 (to the heading of section 9):
  4c03d6ed5974f20a919b856a42070f0435b2e1f52736183af1b69e3d20163299, 5,558 bytes, equal.
- Privacy: no account or host name, drive-letter Users path, session-folder form, UUID-shaped id or workflow id in any
  inserted line of the four files.

## Scripts (STAGE/_scripts/records/, all run as py -3.9 -I -B)

list_folders.py (the os.stat listing), summarise.py, names.py and find_dirs.py (views of the listing files only),
classify.py (the archive groups), privacy_count_out.py and privacy_selftest.py (count-only scan of OUT outside stage/,
and its pattern test on synthetic strings and on stage/), stage_copy.py, texts_pending.py, texts_manifest.py,
texts_protocol.py, texts_outline.py, build_records.py, check_records.py, show_inserts.py, finalize_changes.py (fills
the staged hashes into this file) and privacy_self.py (the same count-only patterns over this writer's own outputs,
outside work/base/: no hit; the scan script's labels and the self-test's synthetic strings are built so that they hold
none of the patterns' text). Work files in work/:
listing_shap.json, listing_out.json, classify.json, tokens.json, privacy_count_out.txt (UTF-16, written by PowerShell's
Tee-Object) and the four base copies. No script of SHAP/scripts, V, V/_lead/scripts or ROOT/engine was run, and the
paper build was not run.

## Files opened outside OUT/_brief, OUT/reconcile and STAGE

- SHAP/PROTOCOL.md (read lines 1-140, 145-295, 360-399 and 536-1225; headings and a few terms searched in this named
  file; hashed; copied to STAGE by script).
- SHAP/RUN_COMMANDS.md (read in full; searched; read by check_records.py for the number check).
- The SHAP folder's listing: names, sizes and times of every file outside smoke/bardl_fix/ (os.scandir/os.stat only;
  no file content read), and Test-Path existence checks of engine_tmp, engine_runs, work and smoke/bardl_fix (the
  folder itself, not entered).
- OUT/A, OUT/B, OUT/spec and OUT/skeptic: every file read whole by privacy_count_out.py for counts only (no content
  printed); names, sizes and times listed.
- ROOT/engine/PENDING_PARTS.md (headings searched; lines 1380-1553 read; a non-ASCII count; copied).
- ROOT/_archive_plan/ARCHIVE_MANIFEST_DRAFT.md (read in full in parts; copied).
- ROOT/_archive_plan/OPEN_ITEMS_2026-11-11.md (read in full; not changed).
- ROOT/paper/PAPER_OUTLINE.md (searched; lines 1-40 and 336-454 read; copied).
- D/09_availability.md (read in full; not changed); D/submission/software_data_availability.md (searched; its visible
  text printed without comments; not changed); D/S9_inputs_licences.md (headings searched; lines 155-172, S9.6, read;
  not changed).
- ROOT/engine/OWNER_RULINGS_2026-10-06.md (headings searched; sections AW-BB, lines 395-455, read; read by
  check_records.py).
- The staged STAGE/paper/PAPER_FACTS.md (section 9, lines 1021-1065) and STAGE/paper/draft/S3_posthoc.md (searched for
  smoke, archive and verify_v1; matching lines shown), and STAGE/changes_main.md (lines 1-60, for the style).
- Glob of ROOT for PENDING_PARTS* and a search of ROOT/paper/draft/_snapshots for Part 627's heading history.

Not opened: SHAP/smoke/bardl_fix/, any comparison printout (AW3_table.md, AW4_table.md), V/reconcile/report.md,
V/A/results.json, any row file, any compare file and any file of SHAP other than the two named above. No Grep or Glob
ran over SHAP or V with a *.md pattern; the Grep calls on SHAP named PROTOCOL.md or RUN_COMMANDS.md.

## Open points (also in the writer's return)

- PROTOCOL.md placeholders: the single line `@@LATER_READS@@` (staged line 1282, column 0) and two `@@SNAP@@` in the
  entry's first paragraph (this folder's `_snapshots/@@SNAP@@/` and `paper/draft/_snapshots/@@SNAP@@/`). The entry says
  the 32daa77b version is saved in SHAP's `_snapshots/` before it is applied; if it is saved elsewhere, that sentence
  changes. Applying the entry changes PROTOCOL.md's SHA-256; records that pin 32daa77b (fact A9's source, the SHAP
  baseline hash list, any S4 row for PROTOCOL.md) then name the pre-edit version.
- New default in the archive plan: the gridded row-level SHAP values (23 files) are kept out (4.2 I; attention item 1);
  D13's own default would archive them. The NumPy draws and the per-draw .npz files are kept out by the file-type rule;
  archiving them would change the Access form line and S4.12's file types. `smoke\` is left out whole (appendix A).
- Not verified by this pass (os.stat only): the SHAP logs' privacy, the columns of the gridded rebuild check and sample
  files, and the contents of verify_v1's work outputs, skeptic/blindness and _lead/returns; the plan marks them for the
  packaging scans.
- S3.13 may now say "archived" for `verify_v1/A/results.json` (archive path `analysis/shap_v1/verify_v1/A/results.json`).
- Part 628's heading now begins "(DRAFT 2026-11-12; RUN 2026-11-12 TO 2026-11-16 AT SCOPE (i), ..."; the S3.0 facts
  comment of S3_posthoc.md should follow it.
