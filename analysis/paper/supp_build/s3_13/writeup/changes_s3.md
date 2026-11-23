# Changes: writer s3 (Supplement S3.13 write-up, 2026-11-17)

Names as in the brief: SHAP = the SHAP analysis folder (D:/treeroute/analysis/shap_v1); V = SHAP/verify_v1; ROOT = the
research-paper folder; D = ROOT/paper/draft; OUT = ROOT/paper/supp_build/s3_13; STAGE = OUT/stage. Only staged copies
were written; no live file was edited. Every staged file was written by a script in STAGE/_scripts/s3/ (listed at the
end), so each can be rebuilt from its start point.

## Files

| Staged file | Start | Start SHA-256 (bytes) | Staged SHA-256 (bytes) | Encoding, line endings |
|---|---|---|---|---|
| STAGE/paper/draft/S3_posthoc.md | first writer: byte-for-byte copy of D/S3_posthoc.md (SHA-256 checked equal before any edit); the build script re-reads the live file, checks its SHA-256 and writes the staged file | 373537b8e454094559c1bb9ed7b0ba8423468f063f19f2ae39a21bb67c232191 (109,952) | ea1d808ef8056bfa33901ac396d69a72241b821bff09e3bba7fef5fb70cfe262 (242,797) | UTF-8 without BOM, LF (kept; no CR; final LF) |
| STAGE/paper/PAPER_FACTS.md | the glossary writer's staged copy (SHA-256 as that writer returned it) | 8206f9ef45fa9111d412a311679d2c726488999faa2c90b97d53d4a730342403 (356,088) | 735e10c81ceee24e89d522c02f0dd86b344902f77147238d2972723702425a8b (381,200) | UTF-8 without BOM, LF (kept) |
| STAGE/paper/draft/REFERENCES.md | first writer: byte-for-byte copy of D/REFERENCES.md (SHA-256 checked equal); the script re-reads the live file and checks its SHA-256 | 79598da01eb582eedb4a8170e2f520246cde0ba7343dabcaa70128aa636d7c50 (157,938) | b699e55f1e84875e6b80101665ffeefbe855d4495341098b75eb8ff4977864b3 (167,145) | UTF-8 without BOM, LF (kept) |
| STAGE/paper/draft/GLOSSARY.md | the glossary writer's staged copy (SHA-256 as returned) | b40954b2a89c77b15fc4b24d8b8f54081be58425101a1b33130f4bd97b3b50c9 (40,923) | edb836a8a8cb11b5c02c0e57fa92742886805c78e86bb26b51a8cf6a28fde3f8 (42,634) | UTF-8 without BOM, CRLF (kept; 140 CRLF, no bare LF) |

Base copies of the two earlier-writer files, for re-runs: STAGE/_scripts/s3/work/paper__PAPER_FACTS.md.base and
paper__draft__GLOSSARY.md.base (SHA-256 checked against the returned values). A line diff of each staged file against
its start (check_s3.py, check_others.py) shows only the changes below.

## S3_posthoc.md

| # | Place (staged line) | What | Why | Source |
|---|---|---|---|---|
| C1 | Header comment, line 1, at its head | Edit-history entry "S3.13 write-up, 2026-11-17: ..." (new section, tables inserted by script byte for byte from tables_agreed.md version 5 without its draft headings and line-1 comment, Table 9 cited not repeated, the one caption change, the S3.0 and header edits, facts A9-A25, no existing number changed, pre-edit copy draft/_snapshots/@@SNAP@@/), in the file's style (newest entry first) | Task: header comment, edit-history line; brief, edit-history rule | - |
| C2 | Line 1, its list of rulings and Parts | "Ruling AN2 (...)." gains "Rulings AW, AY, AZ1, BA and BB (the SHAP comparison of S3.13)."; "Parts 601-606, ..., 625" gains 628 | The header lists every ruling and Part the supplement rests on | rulings file sections AW-BB; engine/PENDING_PARTS.md Part 628 |
| C3 | NUMBER SOURCES paragraph, line 9, before "No number was typed from memory or from a draft." | Sentence for Tables S3.18 to S3.30: copied byte for byte from paper/supp_build/s3_13/reconcile/tables_agreed.md, version 5, built twice by the two builders' scripts paper/supp_build/s3_13/A/scripts/build_tables.py and paper/supp_build/s3_13/B/scripts/build_tables.py under paper/supp_build/s3_13/spec/TABLE_SPEC.md, reconciled and checked (versions 2-5 reworded texts, no number changed); cells.json gives each printed data number's source, selector and stored value; S3.13's prose numbers come from facts A9-A25 | Task: the NUMBER SOURCES sentence | brief_text.md (Goal; item 1); tables_agreed.md line-1 comment |
| C4 | STATUS paragraph, line 11, before " -->" | Sentence: S3.13 (Part 628) is post hoc and report-only; its facts are "final, post hoc (Part 628)"; no PENDING or OWNER marker; the B1 sensitivity is labelled and kept apart | Task: the STATUS line | PAPER_FACTS status key (Part 628 line); protocol section 10 |
| C5 | S3.0 index table, new row after S3.12 (line 35) | S3.13 row: analysis, "2026-11-12 to 2026-11-16 (628)", why (ruling AW) | Task: S3.13's row in S3.0's index table | A9; rulings file AW |
| C6 | S3.0 facts comment (line 37) | "S3.13 A9 (dates), A10"; Part 628's date (2026-11-12, DRAFT, with its dated addendum of 2026-11-17); rulings AW-BB with dates; S3.13's run dates from the protocol's change log and sample register | The comment gives the facts and dates behind every index row | A9; rulings file; PENDING_PARTS Part 628 heading; brief item 3 (the addendum of 2026-11-17, written by the records writer) |
| C7 | New section S3.13 after S3.12's last paragraph and before the file's closing "Cross-check pass" comment (lines 666-1466) | Heading "## S3.13 SHAP comparison of treeroute v1 and its rivals at the nowcast (Part 628)"; prose under run-in heads: When and why; Method (value function, B2 and its meaning, coral bleaching's background, rebuild and S-EXACT, TreeSHAP and linear terms, the two levels and NDVI's merged context columns, families, importances and the two share bases, J and structural zeros, pair statistics, same-link/cross-link, main set, W, stability, the main-text row, the paired region bootstrap); Models explained and rivals left out; Samples and active sets; Exactness checks (E5 informational, E3a on coral, E8 on coral's 2,312 survey visits, E10 as Table S3.21 says); Results (W, the top-20-union Spearman median, RBO, top variables, own-history shares, with their intervals; the per-problem tables); treeroute v1's B1 sensitivity, kept apart (with the pointer verify_v1/A/results.json, key b1); Independent re-computation; What the comparison script does not do (BB1, BB2); Presentation (BB3-BB6, BB6 without any AI term, pointing to Supplement S1.7); Not claimed (protocol section 10 in plain words, coral wording corrected); closing line. Thirteen table blocks inserted by script after the paragraphs that first cite them | Task; brief item 1 | SHAP/PROTOCOL.md sections 1-14; rulings file AK, AW, AY, AZ, BA, BB; PENDING_PARTS Part 628; brief_text.md item 1 (the facts the table checks established); tables_agreed.md v5; cells.json; facts A9-A25 |
| C8 | Table S3.21 caption (line 792) | "so each problem's tree bank and the sampled locations' routers were rebuilt" became "so each problem's tree bank with its correctors and placebos, and the sampled locations' routers, were rebuilt" | A point of the last table check listed in the task (S3.13 writer only); the engine fits one corrector and one placebo per tree, and E5's fingerprint covers all three | task's list; fix_order_v5.md V5-3; protocol section 4.1 (E5) |

Every other byte of the 13 table blocks equals tables_agreed.md (check_s3.py: each block found exactly once, byte for
byte, with C8 applied); no cell, note or source comment changed. Table 9 is cited (Results paragraph), not repeated.

**Table order** (first citations in S3.13, each block placed after the paragraph that first cites it): S3.18
(Models paragraph), S3.19 (Samples), S3.20 and S3.21 (Exactness), S3.22 (Results), S3.23-S3.27 (per-problem paragraph;
each cited as "Table S3.2x" so the build's bare-reference rule does not fire), S3.28-S3.30 (B1 paragraph).

**Numbers.** Every prose number of S3.13 is filled by s3lib.tokens() from its stored value (cells.json, per_lead.json,
the lead check output, the protocol text for two constants) and, where the tables print it, checked equal to the
printed string (one rounding step; the same format as the tables). Each sentence group with a number ends with an
HTML comment citing its fact (A9-A25). check_numbers.py found every number token of the prose in a cited fact, except
section and citation numbers and product names (13 in the heading S3.13; 2017, 2020, 2010, 1939 and 2019 in
citations; MERRA-2, VT0007, EAC4).

**Wording choices, from the sources.** Coral bleaching's background: "a pool of earlier nearby survey visits", with
the counts of the lead check (980 of the 50,000 at the explained survey visit's own reef site, in 415 of the 1,000
sample rows; none dated on or after it), not the protocol's "other sites' visits". No count of coral's reef sites is
given. E3a's keys are not listed. The B2 meaning says "test-window forecast", not the protocol's "2020-2023" (burned
fraction's window is 2019-2022, coral's 2016-2019). Terms checked against the staged glossary (check_s3.py): the
remaining hits are parts of paper terms (skill guard, router fit rows, survey visit, coral bleaching, tree bank,
D8 tolerance, season key), the family names (context and calendar, local drivers), the required phrase "a pool of
earlier nearby survey visits" and decision IDs; "kind", "ours", "freeze", "catalog", "form" and a software "package"
were reworded. No AI term and no "agent" in S3.13's visible text; no absolute path in visible text.

## PAPER_FACTS.md

| # | Place | What | Why | Source |
|---|---|---|---|---|
| F1 | Head, the "Revised 2026-11-17 (S3.13 write-up)" paragraph (line 19), before its last sentence | "Section 9 gains A9-A25 (final, post hoc (Part 628)): the facts behind every number of Supplement S3.13's prose, each with its source path and selector and, for a computed number, the value as the paper prints it beside the stored value." | Edit history of this pass (the glossary writer left the paragraph for the writers who add section 9 facts) | - |
| F2 | Section 9, after A8 (lines 1046-1062) | Facts A9-A25, status "final, post hoc (Part 628)", each with source paths and selectors: A9 timeline (rulings AW-BB with dates and answer times, protocol versions, freeze, smoke tests, registrations, run windows); A10 fixed settings (N, B, J rule, statistics, levels, families, stop rules, D8); A11 coral bleaching's B2 background (980 / 50,000 / 415 / 1,000 / none later); A12 exactness checks and rebuild gates; A13 NDVI's five merged context columns; A14 the samples; A15 BARDL (3 variables, 9 columns, 93 of 96, 470 of 479); A16 W; A17 top-20-union Spearman median and RBO; A18 own-history shares and the median rule; A19 rows with a forecast above 0; A20 coral's context-and-calendar family shares; A21 forest loss's B1 identity check; A22 B1's seasonal-normal shares; A23 the independent re-computation and compare_shap.py's departures; A24 BB1's thin intervals; A25 BB6's read | Task: a new fact for every number of the prose, next free IDs after A8 (A9-A25 are free in the sheet and the live drafts) | cells.json (source, selector, stored value of each table number cited); per_lead.json; SAMPLE_REGISTER.txt; gates.json; verify_v5_claims_out.txt; PROTOCOL.md; rulings file |

## REFERENCES.md

| # | Place | What | Why | Source |
|---|---|---|---|---|
| R1 | Line 3, at the head of the history comment | Entry "S3.13 write-up (2026-11-17; pre-edit copy draft/_snapshots/@@SNAP@@/): five entries added to section A ... No other entry changed, and no printed number changed." | Edit-history rule | - |
| R2 | Section A, at the places of refs_candidates.md's table (build sort key) | Janzing2020_interventional (after Jacox2022_MHWforecasts), KendallBabingtonSmith1939_W (after Ke2017_LightGBM), LundbergLee2017_SHAP and Lundberg2020_TreeSHAP (after LuTian2017_fert), Webber2010_RBO (after Watkins2015); each line copied unchanged from STAGE/refs_candidates.md (SHA-256 526ba5bc...) | S3.13's method paragraph cites all five, in the in-text forms the references writer checked (Lundberg and Lee 2017; Janzing et al. 2020; Lundberg et al. 2020; Webber et al. 2010; Kendall and Babington Smith 1939) | refs_candidates.md; check_cites.py (all S3.13 citations resolve to exactly one entry, Kraft et al. (2019) included; the five sort where they stand) |

The text follows the entries' notes: Lundberg et al. 2020 is cited for TreeSHAP and Janzing et al. 2020 for the
interventional value function; the background is said to be this analysis's choice; the project's own TreeSHAP code
is named ("no SHAP library is used"); Kendall and Babington Smith 1939 is cited for W, not for the tie correction;
no equation number of Webber et al. 2010 is given.

## GLOSSARY.md

| # | Place | What | Why | Source |
|---|---|---|---|---|
| G1 | End of the table, after "sign agreement" (lines 131-132) | Rows "share distance (TV); family-share distance" (other names tvd, tvd_family (code); feature-level value repeated, ruling BB2) and "D8 tolerance" (other names arcsine tolerance, relative tolerance; relative 10⁻¹² on arcsine arms, licensed by E5a; not the identity tolerance), each with its sources in an HTML comment, First defined S3.13 | Terms S3.13's prose uses that the glossary lacked; D8 tolerance is distinct from the row "identity tolerance", whose do-not-use names include "tolerance" | protocol sections 4.1, 8 and 12; ruling AY3, BB2; Tables S3.20-S3.28; cells.json selectors |
| G2 | Last line, the glossary writer's S3.13 history comment | Sentence "The writer of S3.13's prose then added two rows after sign agreement: share distance and family-share distance, and D8 tolerance." before "No existing row changed." | Edit-history rule | - |

The new do-not-use names (tvd, tvd_family, arcsine tolerance, relative tolerance) occur 0 times in tables_agreed.md and
in the Markdown files of D, D/tables and D/submission.

## Checks run (all read only; outputs on screen)

- check_s3.py: line diff live -> staged (only C1-C8); 13 blocks each once, byte for byte; first citations in number
  order, each table after its citing paragraph; no AI term, "agent" or absolute path in S3.13's visible text; glossary
  scan of the prose.
- check_numbers.py: number tokens of the prose against the cited facts (above); every date in A9 or A25.
- check_cites.py: with the references writer's copy of the build's parser (STAGE/_scripts/refs/check_entries.py,
  functions only): every citation of S3.13 resolves; none unresolved or ambiguous in the whole staged file.
- check_xrefs.py: the build's cross-reference expressions over the staged file: S3.13's prose 0 problems; the agreed
  tables 1 (see the open point on Table S3.30's note); the rest of the file 0.
- check_others.py: diffs of PAPER_FACTS.md, GLOSSARY.md and REFERENCES.md (only F1-F2, G1-G2, R1-R2).
- A privacy scan of every staged file and script of this writer for the account and host names (taken from the
  environment, never written to a file), user-folder paths, e-mail domains, workflow and session ids: no hit in any
  text this writer added (the hits "wf_" and "session" are in older text of S3_posthoc.md, PAPER_FACTS.md and
  REFERENCES.md, unchanged).

## Scripts (STAGE/_scripts/s3/, each run as `py -3.9 -I -B <script>`)

s3lib.py (paths, formats, the prose tokens with their checks), build_s3.py (S3_posthoc.md; template s313_template.md),
make_facts.py (PAPER_FACTS.md), build_refs.py (REFERENCES.md), build_glossary.py (GLOSSARY.md), stage_copy.py (the
byte-for-byte first copies), save_bases.py (base copies of the earlier writers' files), check_s3.py, check_numbers.py,
check_cites.py, check_xrefs.py, check_others.py, cells_peek.py and cells_find.py (cells.json lookups), per_lead_keys.py
(per_lead.json top-level keys and scalars), gates_peek.py (gates.json pass flags and the E5 and E3a values). work/
holds the two base copies and s313_prose_only.md (S3.13's prose without tables, for the scans). No script of
SHAP/scripts, V, V/_lead/scripts or ROOT/engine was run; the paper build was not run; nothing was written outside
STAGE.

Process note: one call ran `py -3.9 -I -B -c` with inline code instead of a script, to compute the SHA-256 of the
two-byte text "[]" (for A12's reading of coral's E3a value); it opened no file.

## Opened outside OUT/_brief, OUT/reconcile and STAGE

D/S3_posthoc.md and D/REFERENCES.md (live; read and copied); SHAP/PROTOCOL.md (read in full; two constants also read by
s3lib.py); ROOT/engine/OWNER_RULINGS_2026-10-06.md (headings searched; sections AK and AW-BB read);
ROOT/engine/PENDING_PARTS.md (searched for Part 628; its entry read); D/02_method.md (lines 45-59) and D/05_rivals.md
(lines 37-48); headings of D/02_method.md, 03_protocol.md, 05_rivals.md and S1_disclosures.md; the Markdown files of D
(two searches: fact IDs A9-A49, and lists of supplement tables; snapshots and review logs included) and of D, D/tables
and D/submission (a search for the new glossary names); every D/S*.md and D/0*.md file, read by check_xrefs.py for
their headings and table captions; ROOT/paper/PAPER_OUTLINE.md (searched for A9-A39); ROOT/paper/build/BUILD_README.md
(read); ROOT/paper/build/build_docx.py (searched; lines 534-593 and 1455-1534 read; not run);
ROOT/paper/build/build_report_REVIEW.md (searched; lines 270-299 read) and a listing of ROOT/paper/build;
SHAP/SAMPLE_REGISTER.txt (read); SHAP/out/<problem>/lead_0/compare/per_lead.json, all five (by per_lead_keys.py and
s3lib.py: top-level keys and scalar fields); SHAP/rebuild/<problem>/lead_0/gates.json, all five (by gates_peek.py:
result, pass flags, the E5 and E3a values); existence checks only of OUT/A/scripts/build_tables.py,
OUT/B/scripts/build_tables.py and OUT/spec/TABLE_SPEC.md; ROOT/paper/PAPER_FACTS.md and D/GLOSSARY.md hashed only (to
confirm the live files are unchanged: b6a1f6bc... and 07ef124c..., as the glossary writer recorded). Not opened: SHAP/smoke/bardl_fix/, the comparison printouts
(AW3_table.md, AW4_table.md), V/reconcile/report.md, V/A/results.json (its numbers came through cells.json), and no
Grep or Glob ran over SHAP or V.

## Open points (for the lead)

1. Table S3.30's note (as agreed) ends "(Tables S3.28 and S3.29)". The build's bare-reference rule (build_docx.py
   BARE_SUP_RE) reads the second number, "S3.29", as a supplement heading, which does not exist, so a final build would
   refuse (cross-reference blocker; a REVIEW build lists it). check_xrefs.py finds no other such case in the staged
   file. A fix would be "(Table S3.28 and Table S3.29)"; it is a note change outside this writer's listed points, so it
   was not made. S3.13's own prose cites each table as "Table S3.2x" for this reason.
2. The supplement's reference list will now carry two titles with "explainable AI" (Lundberg et al. 2020; Janzing et
   al. 2020). The build's AI-term check skips the reference lists; the owner's wish for no AI mention is the lead's call
   (as the references writer noted).
3. Clock times: S3.13 and Table S3.22 note d give the BB6 times as the rulings and protocol record them, in local time
   (UTC+1): AW4_table.md written 2026-11-13 at 00:06, read at about 15:31. S4.2's timeline is in UTC (2026-11-12 23:06
   and about 14:31 UTC); the two places should not be read against each other without the offset.
4. S3.0's facts comment names Part 628's heading as "DRAFT, with its dated addendum of 2026-11-17"; that addendum is
   the records writer's (brief item 3). If its date or the heading's status words differ, the comment should follow.
5. The brief says the B1 per-player values are "in the archived results file"; S3.13 follows Table S3.29's note ("the
   re-computation's results file (verify_v1/A/results.json, key b1)") and does not say "archived", as the archive is
   still a plan. Add "archived" once the manifest lists verify_v1/A/results.json.
6. BB6's pointer "Supplement S1.7 records who read it" needs the S1.7 row that the S1 writer adds (brief item 3).
7. Facts A9-A25 are taken; a later writer adding section 9 facts should start at A26.
8. The references writer's unconfirmed points stand: the text cites Lundberg et al. 2020 for TreeSHAP only and Janzing
   et al. 2020 for the interventional value function; no equation number of Webber et al. 2010; Kendall and Babington
   Smith 1939 for W only (its byline not seen).