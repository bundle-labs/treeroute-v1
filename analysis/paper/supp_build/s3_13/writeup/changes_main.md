# Changes: writer main (Section 5.4, Table 9 and the table index; S3.13 write-up, 2026-11-17)

Names as in the brief: SHAP = the SHAP analysis folder (D:/treeroute/analysis/shap_v1); V = SHAP/verify_v1; ROOT = the
research-paper folder; D = ROOT/paper/draft; OUT = ROOT/paper/supp_build/s3_13; STAGE = OUT/stage. Only staged copies
were written; no live file was edited. Every staged file was written by a script in STAGE/_scripts/main/ (listed
below), so each can be rebuilt from its start point.

## Files

| Staged file | Start | Start SHA-256 (bytes) | Staged SHA-256 (bytes) | Encoding, line endings |
|---|---|---|---|---|
| STAGE/paper/draft/05_rivals.md | first writer: byte-for-byte copy of D/05_rivals.md (stage_copy_main.py; SHA-256 checked equal before any edit); build_main.py edits a SHA-checked base copy (_scripts/main/work/) | c439966f79efcf9dc9c23362dfa389f1dca6b3d65dd6871e53b8540b39b2fb59 (17,434) | 74fe38496b9f536811eab0fe879f6c2415992f10177c3f95e85ba3c604fd5592 (19,202) | UTF-8 without BOM, LF (kept; no CR; one final LF) |
| STAGE/paper/draft/TABLE_NUMBERS.md | first writer: byte-for-byte copy of D/TABLE_NUMBERS.md (same procedure) | 4bd98584a116a68e2b50c8d9aab51ba2f02a963c548fb9d0f5a3fef617c0be36 (1,950) | 9e159faebff12c27a0f1e85f4d418fdea758777e7db20e77736b4f5d61520598 (2,468) | UTF-8 without BOM, LF (kept) |
| STAGE/paper/draft/tables/table_9.md | new file (live SHA-256 "absent": D/tables/table_9.md does not exist) | absent | 0a5471ff6c1567072b0f730cd596d6977c9b8d96a146f2f531ce200c72c65a1e (6,885) | UTF-8 without BOM, LF, as tables_agreed.md and table_6.md (table_7.md is CRLF; a byte-for-byte copy of the LF block needs LF) |

Not changed: STAGE/paper/PAPER_FACTS.md (every number of the new paragraph is already in A10, A16 or A17, so no fact
was added and A26 stays the next free ID) and STAGE/paper/draft/REFERENCES.md (the one citation, Lundberg and Lee 2017,
is already there as LundbergLee2017_SHAP, added by the S3.13 writer).

## 05_rivals.md

| # | Place (staged line) | What | Why | Source |
|---|---|---|---|---|
| M1 | Section 5.4, new last paragraph (line 47), after the coral bleaching paragraph (line 45) and before the edit-history comments | Four sentences: (1) "Table 9 compares, post hoc, the SHAP values (Lundberg and Lee 2017) of treeroute v1 and its rivals at the nowcast (Supplement S3.13)."; (2) where defined, Kendall's W of the main set's full rankings, 0.62 [0.61, 0.62] (NDVI) to 0.85 [0.85, 0.86] (PM2.5); (3) over the variables in either model's top 20, treeroute v1's median Spearman correlation with its same-link rivals, −0.02 [−0.08, 0.07] on PM2.5 and 0.07 [−0.01, 0.12] on NDVI, both intervals including 0, 0.20 [0.14, 0.29] on forest loss and 0.48 [0.39, 0.55] on coral bleaching; (4) "SHAP values show what a model uses, not what causes the outcome, and agreement between rankings is not correctness." Each sentence ends with an HTML comment: rulings AW, AY, AZ1, BA, BB and AK (post hoc, report-only) and Part 628; A16; A17 and A10 (the top-20 union); SHAP protocol section 10 ("Not claimed") and S3.13's "Not claimed" | Task (brief item 2): introduce the comparison, cite Table 9 (Table 8 is cited first in 5.4, so the numbering stays in order of first citation), the main reading with its intervals, the label "post hoc", what is not claimed, a pointer to S3.13; brief | tables_agreed.md v5 (Table 9, lines 9-13); cells.json (table 9 entries: source, selector, stored value); facts A10, A16, A17; staged S3_posthoc.md S3.13 (Results, Not claimed); SHAP protocol sections 8 and 10 |
| M2 | End of file, new comment after the AT pass comment (line 53) | Edit-history comment "S3.13 write-up, 2026-11-17 (pre-edit copy in draft/_snapshots/@@SNAP@@/): ..." in the style of the file's trailing pass comments: the new paragraph, its citations (Table 9, Lundberg and Lee 2017, Supplement S3.13), its facts, the one-rounding-step rule; no existing sentence or number changed | Brief: edit-history rule; task: an edit-history comment | - |

No other line changed (check_main.py: two insertions only, live lines 46 and 50 kept).

**Numbers.** The twelve numbers of sentences 2 and 3 are formatted once by build_main.py from their stored doubles
(cells.json, table "9", lines 9, 10, 12 and 13, columns kendall_w and spearman_top20_union_median, parts value, ci_low
and ci_high; sources AW4_main_row.json kendall_w and treeroute_vs_same_link_rivals_median_spearman_top20_union), with
two decimals and U+2212 minus, and each is checked equal to its printed string, to the start of its Table 9 cell, to the
printed line of tables_agreed.md, and to the same stored value in Table S3.22's entries. The script also checks the
claims around them: burned fraction's W is the undefined cell ("Where defined"), NDVI has the lowest and PM2.5 the
highest of the four defined W values, and the PM2.5 and NDVI Spearman intervals include 0. check_main.py finds every
interval verbatim in A16 or A17 and every number token in a cited fact ("20" in A10 and A17).

**Wording choices.** The main reading is Table 9's first two statistics, W and the median top-20-union Spearman
correlation, as in S3.13's Results paragraph, each with the base it is taken over ("full rankings"; "over the
variables in either model's top 20"), so that the two are not read against each other as one statistic; no contrast
word joins them. RBO, the top 3 lists and the own-history shares are left to Table 9 for the word budget; the paragraph
does not describe the own-history share, so it cannot misstate it. "Where defined" covers burned fraction, whose main
set is treeroute v1 alone (Table 9, note a). The sample (1,000 test rows per problem) is left to the caption. The
"Not claimed" sentence uses the brief's and the protocol's words. Terms follow the staged glossary (main set, same-link,
Kendall's W, SHAP value, nowcast, coral bleaching in full); "model" is the generic word of Table 9's caption and S3.13,
not a name for treeroute v1. No AI term, no "agent" and no absolute path in the visible text.

## tables/table_9.md (new)

| # | Place | What | Why | Source |
|---|---|---|---|---|
| T1 | Lines 3-16 | The Table 9 block of tables_agreed.md (version 5; SHA-256 d05a6856019d90cfe6d2c5aa798a57bc9f9f1f38bad76e5367d28753df3b467c), its lines 5-18: the caption with its source comment, the table (five rows), notes a, b, c and †, copied by script byte for byte (4,562 bytes), without the draft heading "## Main text: Table 9 (Section 5.4, Post hoc analyses)" and without the file's line-1 comment. No caption, note, label or cell changed | Task; brief item 2 (the notes the rulings require are all in the block: BB1's †, BB4's labels "(no own-history input)" and "median of the rivals" with note c, BB4's PM2.5 note b, fire's link note a) | tables_agreed.md v5 |
| T2 | Line 1 | Header comment in the style of table_6.md and table_7.md: the pass, new file (no pre-edit copy), what the table is (post hoc, report-only, ruling AK; Part 628; rulings AW-BB; protocol sections 8 and 10), where the block comes from (path, lines, SHA-256), how tables_agreed.md was built (two builders' scripts, spec, reconciled, versions 2-5 with no number changed), cells.json and the cells' two sources (AW4_main_row.json; V/A/results.json problems.fire.main_row for the two † cells, BB1), the rulings behind each note and label, facts A16, A17, A18, A10, A14 and that Section 5.4 cites A10, A16 and A17, and Table S3.22 | Task: a header comment in the style of the other table files | as T1; facts sheet section 9 |

The Word build places the file after 5.4's last paragraph, the first to cite Table 9 (BUILD_README "Tables"); its
caption starts "**Table 9.**", so it is found as table 9; its comment line is removed at build.

## TABLE_NUMBERS.md

| # | Place (staged line) | What | Why | Source |
|---|---|---|---|---|
| N1 | Table, new last row (line 15), after the Table 8 row | "\| – \| 9 \| `tables/table_9.md` \| SHAP agreement between treeroute v1 and its rivals at the nowcast \| 5.4 Post hoc analyses \|": no old number (en dash, as Table 9 marks an empty cell), the caption title taken by script from Table 9's caption (its text before the first comma, as the other rows shorten theirs), placed after 5.4 | Task | Table 9 caption (tables_agreed.md line 5) |
| N2 | Closing paragraph (line 17), at its end | "S3.13 write-up, 2026-11-17: Table 9 ... is new, so it has no old number, and its file, `tables/table_9.md`, carries its own number (no file is named `table_8.md`). The Word build places it after the last paragraph of 5.4, which first cites it, after Table 8; no table was renumbered. Pre-edit copy under draft/_snapshots/@@SNAP@@/." | Edit-history note in the file's style (its notes are sentences in this paragraph); the file-name clause because every other file keeps its old number | - |

## Checks run (all read only; outputs on screen)

check_main.py: (1) bytes of the three staged files (no BOM, no CR, one final LF); (2) line diffs live -> staged (05:
two insertions; TABLE_NUMBERS: one inserted row and the closing line extended, its old text kept as prefix); (3)
table_9.md equals its header + a blank line + the block, the block found once in tables_agreed.md and once in the file;
(4) numbers against the cited facts (above); (5) AI terms, "agent", absolute paths, e-mail addresses, account and host
names (read from the environment, never written) in the added visible text: 0; in this writer's staged files, scripts
and this record: no account or host name, user-folder path, e-mail address, uuid-like id or "wf_" id; (6) citations,
with the references writer's copy of the build's parser (STAGE/_scripts/refs/check_entries.py, functions only) against
the staged REFERENCES.md: "Lundberg and Lee 2017" resolves to LundbergLee2017_SHAP; no unresolved or ambiguous citation
in the staged 05_rivals.md or table_9.md; (7) cross-references, with the build's expressions (supplement headings and
table captions from D/S*.md with the staged S3_posthoc.md in place of the live one): "Supplement S3.13" and "Table
S3.25" exist; no problem; (8) first citations of Tables 1-9 in the running text in manuscript order (the availability
section, then Sections 1-8 with the staged 05_rivals.md): 1, 2, ..., 9, Table 9 first in 05_rivals.md and cited by no
other main-text file; (9) the lead's glossary scan rule on the added prose: "bleaching" (inside "coral bleaching") and
"model" twice (generic, as in Table 9's caption) only; (10) word counts with the build's count_words rule: Section 5
running text 1,777 (equal to the last REVIEW build report) -> 1,886 words (+109; budget 1,100, ceiling 1,400); 5.4 235
-> 344; Table 9's caption, table and notes 620 words (counted under tables).

## Scripts (STAGE/_scripts/main/, each run as `py -3.9 -I -B <script>`)

inspect_files.py (encodings, line endings and SHA-256 of the inputs and outputs), cells_table9.py (cells.json's table 9
entries), stage_copy_main.py (the byte-for-byte first copies and the base copies in work/; on a re-run it keeps an
edited staged copy and re-checks the base), build_main.py (the three staged files), check_main.py (the checks above).
work/ holds the two base copies. No script of SHAP/scripts, V, V/_lead/scripts or ROOT/engine was run; the paper build
was not run; nothing was written outside STAGE.

## Opened outside OUT/_brief, OUT/reconcile and STAGE

D/05_rivals.md and D/TABLE_NUMBERS.md (live; read; copied byte for byte; re-read by the scripts, hash-checked);
D/tables/table_6.md and D/tables/table_7.md (read in full); a listing of D/tables (table_9.md absent) and of OUT's top
level; SHAP/PROTOCOL.md (headings searched in that one file; sections 8-10, lines 479-693, read); ROOT/paper/build/
BUILD_README.md (read in full); ROOT/paper/build/build_report_REVIEW.md (searched for the word counts);
ROOT/paper/build/build_docx.py (searched; lines 905-964, 1039-1054 and 1195-1269 read; not run); the Markdown files of D,
snapshots and review logs included (one search for "Table 9", "table_9" and "S3.13", file names only); D/0*.md,
snapshots included (one search for SHAP, Shapley and attribution; matching lines of 07_discussion.md and
09_availability.md shown) and D/submission (one search for SHAP); the files of ROOT/paper outside _snapshots (one search
for table-count phrases; matching lines shown from OUT/spec's TABLE_SPEC versions and CHANGES_v2.md, the build's _work
read-backs of the supplement, and D/S1_disclosures.md, whose line 37 was read in part); by check_main.py: D/S*.md and
D/0*.md (headings, table captions and table citations; an earlier run read every top-level D/*.md, using only those)
and D/submission/software_data_availability.md (table citations). Not opened: SHAP/smoke/bardl_fix/, AW3_table.md,
AW4_table.md, V/reconcile/report.md, V/A/results.json, and no Grep or Glob ran over SHAP or V.

## Open points (for the lead)

1. Apply together: the new 5.4 paragraph cites Lundberg and Lee 2017, which only the staged REFERENCES.md holds, and
   "Supplement S3.13" and Table 9's "Table S3.25", which only the staged S3_posthoc.md holds. Applied alone, 05_rivals.md
   and table_9.md would fail the build's citation and cross-reference checks.
2. Word budget: Section 5's running text goes from 1,777 to 1,886 words (budget 1,100, ceiling 1,400), and Table 9 adds
   620 words under tables. The paragraph keeps only W and the median Spearman correlation; RBO, the top 3 lists and the
   own-history shares stay in Table 9.
3. D/S1_disclosures.md line 37 says "Tables 1-8 and Table S3.1 are the paper's tables"; with Table 9 it should say
   Tables 1-9 (the S1 writer's file; not edited here).
4. LundbergLee2017_SHAP's Supports note names Supplement S3.13 and Table S3.18 a; Section 5.4 now cites it too, for
   "SHAP values" only, as the note allows. REFERENCES.md was not edited (the task allows it only for a missing work).
5. The glossary rows SHAP value and same-link give "First defined: S3.13 (named Table 9)"; Section 5.4's paragraph now
   names SHAP values, the main set and same-link rivals just before Table 9. No change seems needed, but the lead may
   prefer "(named 5.4)".
6. No fact was added; A26 is still the next free ID for the S1 writer.
7. Table 9's intervals are percentile bootstrap intervals over regions, while the rest of 5.4 uses jackknife intervals;
   the caption says so, the paragraph does not (for the word budget).
