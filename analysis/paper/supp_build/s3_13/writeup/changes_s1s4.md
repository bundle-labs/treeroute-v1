# Changes of the s1s4 writer (S3.13 write-up, 2026-11-17)

Writer label: s1s4. Task: brief item 3, the S1 and S4 bullets (S1.7 rows from PH22, the RP18 clause, S1.10's counts;
Table S4.13 rows AW-BB, the S4.2 timeline, Table S4.11's Part 628 row and the hashes), with the facts the new rows
cite. Names as in the brief: ROOT, D, OUT, STAGE, SHAP = `D:\treeroute\analysis\shap_v1`, V = `SHAP\verify_v1`.

## Files

| File (staged path) | Started from | SHA-256 before | SHA-256 staged | Encoding |
|---|---|---|---|---|
| `STAGE\paper\draft\S1_disclosures.md` | live `D\S1_disclosures.md`, copied byte for byte (hash checked) | 23d7c5d8167293ad1ea08561e1f0f471fe818da722e6e805e97094cc6c450862 | b469b1dc9f883519e946e2a6cc3f9fc031e51254c1d61cb611e41d4b73d2dc25 | UTF-8, no BOM, LF (317 LF, 0 CR) |
| `STAGE\paper\draft\S4_provenance.md` | live `D\S4_provenance.md`, copied byte for byte (hash checked) | 19112cd642e6a8d74773278a5c2a32a958ae584bd064a3485ffc3fe19fdc7d5f | 081654fa31b449c28aa4cf1123f7e481bb6f2970a22ddc2bc4c798f6dda8dec0 | UTF-8, no BOM, CRLF (735 CRLF, no bare LF or CR) |
| `STAGE\paper\PAPER_FACTS.md` | the S3.13 writer's staged copy (735e10c8..., hash checked; live b6a1f6bc...) | 735e10c81ceee24e89d522c02f0dd86b344902f77147238d2972723702425a8b | ce7a86e64c2b66268c40e78db0a7074bb42dafc71e410729062cc8550395115a | UTF-8, no BOM, LF (1484 LF) |

All three are rebuilt by `STAGE\_scripts\s1s4\build_s1s4.py` from hash-checked base copies in
`STAGE\_scripts\s1s4\work\` (made by `stage_copy.py`). Every edit is an exact replacement whose old text must occur
once; nothing outside the places below changed (the unified diffs are in `work\diff_*.txt`).

## Times: local time is UTC+1 in the SHAP records

The times in `SHAP\PROTOCOL.md` section 14, `SHAP\RUN_COMMANDS.md`, `SHAP\SAMPLE_REGISTER.txt` and the rulings file
(sections AW-BB) are local time, UTC+1. Evidence (file times read with Get-Item, contents not opened): PROTOCOL.md and
RUN_COMMANDS.md were last written 2026-11-16 23:31:06 local = 22:31:06 UTC (the protocol's entry says "recorded on
2026-11-16 at 23:31"); SAMPLE_REGISTER.txt 14:37:52 local = 13:37:52 UTC (its last line is stamped 2026-11-14T14:37:52);
the coral sample manifest 2026-11-12 23:49:45 local (the coral registration's stamp); the coral run log and coral
per_lead.json 2026-11-13 00:06:12 local = 2026-11-12 23:06:12 UTC (the pilot's end, "00:06"); the NDVI per_lead.json
19:11:39 local = 18:11:39 UTC; the four tr_shap logs 23:14:02, 23:58:00, 04:56:11 and 08:14:14 local, the B1 "done in"
times of RUN_COMMANDS.md, each one hour after its UTC file time. The machine's zone has base offset +01:00. In S4 every
time from these records was converted to UTC (one hour earlier) and printed with the local time in parentheses, as
S4.1 asks; S4.1's Times bullet now says that the SHAP records use UTC+1 (the run records stay UTC+3). The ruling rows
of S4.2 keep the rulings file's dates, as the existing rows do; AZ1 (about 04:35 local), BA (about 19:45 and 22:50)
and BB (20:59) fall on the same date in UTC, and the records give no time for AW, AX and AY. Fact A28 records all of
this. S1 keeps local times (PH27, as Table S3.22's note d and S3.13 give them) and says so in the row.

## Changes to S1 (`STAGE\paper\draft\S1_disclosures.md`)

- **S1-1, line 1 (header comment).** Prepended an edit-history entry "S3.13 write-up, 2026-11-17 (pre-edit copy
  draft/_snapshots/@@SNAP@@/): ..." naming every change below. Why: brief rule on edit-history comments. Source: this
  record.
- **S1-2, line 37 (key of "Where the paper states it").** "Tables 1-8 and Table S3.1 are the paper's tables" now reads
  "Tables 1-9 ...", with a dated comment. Why: the main text now has Table 9 (staged `D\tables\table_9.md`,
  `D\TABLE_NUMBERS.md`); the main-text writer's open point named this line. Source: staged TABLE_NUMBERS.md and
  05_rivals.md.
- **S1-3, S1.7, after PH21: nine new rows PH22-PH30.** Why: brief item 3 (S1 bullet) and the task. Each row has a
  source comment; every number in it is from a fact (A9-A27) printed as the fact prints it.
  - PH22: the comparison itself (rulings AK, AW, AY1): nowcast only, 1,000 test rows per problem, 2,000 paired region
    draws; protocol version 1 before any SHAP value on a real row; sections 3 and 8 frozen at the first registration
    (2026-11-12); smokes on at most 250 coral rows and the loaders' checks as plumbing; report-only; what it does not
    claim (protocol section 10). Where: 5.4; Table 9; S3.13. Sources: facts A9, A10, A14; Part 628.
  - PH23: rebuild and exactness: the tree bank with correctors and placebos and the sampled routers rebuilt; S-EXACT
    before any SHAP value; E5 informational on all five problems; the D8 tolerance (10⁻¹²) used by the coral pilot
    before it was ruled (AY3); coral's E3a compares no data file before the labels; E10's coverage as Table S3.21
    gives it; the moved package file and gate E3m (AY2). Where: S3.13 (Table S3.20 and Table S3.21). Sources: facts
    A9, A10, A12.
  - PH24: rivals left out with the reasons of Table S3.18 b, the Kraft LSTM under the default of the open protocol
    decision D7 (its skill guard failed at the nowcast, fact RH4), and, as the table's note says, the rivals that run
    only at forecast leads, among them the Coral Reef Watch Outlook; the Ridge and BARDL loaders added after the freeze;
    BARDL kept in the NDVI main set (BA1) and its name-order fill (BB3). Sources: facts A15, RH4; rulings AG1, AS, AY,
    BA1, BB3.
  - PH25: treeroute v1's B1 sensitivity (BA3): scope, forest loss's exact identity check, ruled before any statistic
    of the four gridded comparisons was read, the B1 list written by an agent before the first B1 run and recorded
    after the runs began, the forest-loss run added by an agent, kept apart; and the protocol-section-10 disclosure that
    the per-player values are given through "the re-computation's results file" (as S3.13 and Table S3.29 call it; not
    "the archived results file", because the archive is still a plan). Sources: facts A9, A21, A22.
  - PH26: the independent re-computation (BA2), agreement within 10⁻⁹ but for three explained cases, the comparison
    script's three departures, BB1 (so S3.13 and Table 9 differ from the compare files in those cells; the three
    intervals on 64, 1,140 and 1,380 of 2,000 draws) and BB2; the presentation rulings came after an agent's messages
    had quoted some statistics, rounded (rulings file BB lead paragraph). Sources: facts A10, A23, A24, A26.
  - PH27 (required; the row Table S3.22's note d points to): coral's AW4_table.md (written 2026-11-13 at 00:06) read
    by an agent on 2026-11-13 at about 15:31, before the re-computation; implementers A and B never opened it; local
    times stated as such; first recorded in the protocol on 2026-11-16; question C10 to the author ("owner question
    C10" in the records, quoted, as AT20 asks "the author") settled by BB6. Sources: facts A25, A26; ruling BB6.
  - PH28: the burned-fraction comparison of 2026-11-13 (four models, without Ridge) opened once by an agent for its
    layout only; what was read held no agreement statistic; the author had not opened it (AZ1); the Ridge loader has no
    free choice. Where: S3.13 (in part), because S3.13 states AZ1 only. Sources: facts A9, A26; ruling AZ1.
  - PH29: record conflict: the protocol's "other sites' visits" for coral's B2 background against the count (980 of
    50,000 at the explained survey visit's own reef site, for 415 of 1,000; none dated on or after it). Source: fact
    A11. Its comment names the records writer's staged change-log correction; the visible text does not depend on it.
  - PH30: how the tables were built (twice, two independent builders, one specification, reconciled with each other and
    the printed tables, checked; versions 2-5 after four checks, no number changed; the builders' final tables
    byte-identical). Where: S1 only (elsewhere only in comments). Source: fact A27.
- **S1-4, S1.7 comment after the table.** Appended a sentence on PH22-PH30 (no recomputed values; facts A9-A27; PH27
  is the BB6 row; PH25's wording). Why: the comment records each section's number sources.
- **S1-5, RP18.** Inserted, after the Part 611 comment and before "They chose the PM2.5 trend cut points", one clause
  on the agents' part in the SHAP analysis: the design workflow with adversarial reviews; the protocol, scripts, smoke
  tests and the commands with which the author ran the long computations; the Ridge and BARDL loaders, reviewed; the
  smoke tests and checks; the independent re-computation's workflow (specification writer, implementers A and B,
  reconciler, checkers) and the report an agent wrote from the reconciler's text; the specification, the two builders,
  the reconciliation and checks of the S3.13 tables and Table 9 (PH30); the writers and checkers of this write-up. One
  sentence says that the model list ends with fact M14b's scan of 2026-11-10, before this analysis. Its comment gives
  the sources: Part 628 (the design workflow), SHAP protocol sections 1 and 14, `OUT\_brief\reads_tables.md`, facts
  A9, A23, A27, M14b. The Source cell gains facts A9, A23, A27, ruling BA2 and Part 628. The OWNER marker of ruling
  AT11 and every other word of the row are unchanged. Why: brief item 3 ("RP18 gains a clause on the agents' part").
- **S1-6, S1.10.** post hoc 21 -> 30; Total 170 -> 179; the counts comment gains one sentence. Counted by script from
  the table rows by section (S1.1 8, S1.2 14, S1.3 15, S1.4 16, S1.5 37, S1.6 32, S1.7 30, S1.8 18, S1.9 9).

## Changes to S4 (`STAGE\paper\draft\S4_provenance.md`)

- **S4-1, line 1 (header comment).** Prepended the dated entry "S3.13 write-up, 2026-11-17 (pre-edit copy
  draft/_snapshots/@@SNAP@@/): ..." naming every change below.
- **S4-2, line 15 (opening paragraph).** "the lettered rulings of the author (S4.10)" -> "every lettered ruling of the
  author (S4.10)", with a comment. Why: "every" had been dropped only because section AW was not in Table S4.13
  (comment of the AV close-out fixes); Table S4.13 now has every lettered section, through BB, the file's last
  (checked by script: the last "## XX." heading of the rulings file is BB).
- **S4-3, S4.1 Times bullet.** Now: local time follows in parentheses, UTC+3 in the records of the runs and rival
  boards, and UTC+1 in those of the SHAP analysis of 2026-11-12 to 2026-11-16 (S4.2); the comment cites fact A28 and
  keeps the old wording. Why: the new rows convert UTC+1 records.
- **S4-4, S4.1 Identifiers.** "(A to AV, Table S4.13)" -> "(A to BB, Table S4.13)", with a comment.
- **S4-5, S4.2 opening paragraph.** One sentence: the rows from 2026-11-12 on are the post hoc SHAP comparison (Part
  628), which ran after every lock and test-label opening above (comment: ruling AK; facts A9, A28).
- **S4-6, S4.2 table, after the 2026-11-11/12 row.** Ten rows (UTC, local in parentheses): ruling AW and the protocol
  (2026-11-12); the coral pilot 22:49:45-23:06:12 (23:49:45-00:06:12 local); rulings AX and AY (2026-11-13); the read
  of coral's AW4_table.md at about 14:31 (15:31 local); the four gridded nowcast runs 2026-11-13 16:23:16 to 2026-11-15
  18:11:39 with the four registrations and the layout read of the 20:18 burned-fraction comparison; ruling AZ1 (about
  03:35); ruling BA (about 18:45 and 21:50); the B1 runs 2026-11-15 22:06:16 to 2026-11-16 07:14:14 (list written
  22:03); the re-computation 16:09 to about 18:20; ruling BB 19:59. A comment after the table's comments gives the
  sources and the UTC+1 rule. Sources: rulings AW-BB, PROTOCOL.md sections 1, 10 and 14, RUN_COMMANDS.md section 2,
  SAMPLE_REGISTER.txt, file times; facts A9, A25, A26, A28.
- **S4-7, Table S4.11.** Caption: Part 628's files are in the folders its row names. New row 628: the 17 SHAP analysis
  scripts (`scripts/` 12, `scripts/tests/` 5) and the two builders' `build_tables.py`, with 8-digit prefixes, in the
  style of the 622-625 rows. The table's comment gains the 19 full SHA-256 (read by `hash_files.py`), the match with
  the four prefixes the protocol's change log records (bardl_shap.py 6bfc9aaf, smoke_bardl.py 0f7de758, ridge_shap.py
  866fd329, smoke_ridge.py c48f3f66), and why PROTOCOL.md and the re-computation's files are not listed (the
  protocol's hash changes with this write-up's change-log entry; V's files are named in S3.13). Why: brief item 3.
- **S4-8, S4.10.** "Table S4.13 lists the lettered rulings ..., A to AV. [PENDING: ... AW ... AX ... in a later pass]"
  -> "Table S4.13 lists every lettered ruling in the three rulings files, A to BB." The marker is closed; the comment
  keeps the old sentence. Why: the task ("A to BB"; the PENDING marker about AW and AX closes).
- **S4-9, Table S4.13, after row AV.** Rows AW, AX, AY, AZ, BA and BB (date, one-line summary, the author's recorded
  words), each with a source comment; every quoted string (14) was checked by script against the rulings file;
  numbers: AW5's 1,000 and AY3's 10⁻¹² (fact A10), BB's 2,000 (facts A10, A24), AX's 13 items and items 2-13 (rulings
  file, AX), AZ's time in UTC with local (fact A28). The summaries say "the author" (AT20); the S3.13 disclosure in BB6
  names the agent here, as S4 may. The table's closing comment gains a sentence for rows AW-BB.
- **S4-10, S4.12 paragraph before Table S4.14.** "(... the Part 627 sensitivity row on 2026-11-10)" -> "(...; the Part
  628 files on 2026-11-17)".
- **S4-11, Table S4.14.** Two groups after the Part 627 group: "Post hoc SHAP comparison, Part 628: analysis scripts
  (`analysis/shap_v1/`; ...)" with the 17 scripts, and "... the S3.13 table builders' scripts
  (`paper/supp_build/s3_13/`; ...)" with the two builders. Kind "file", full SHA-256. The table's comment gains the
  pass, the recount and the new totals: a recount by `count_s414.py` finds 235 values, 234 distinct, before this pass
  (the comment had said 234 and 233; the one shared value is coral's driver and static file lists), so the table now
  holds 254 values, 253 distinct; no two distinct values share an 8-digit prefix, and every 64-hex string in the file
  is in the table; the visible text gains no 8-hex string without an entry.

## Changes to PAPER_FACTS (`STAGE\paper\PAPER_FACTS.md`)

- **F-1, line 19 ("Revised 2026-11-17 (S3.13 write-up)").** One sentence before the snapshot sentence: section 9 also
  gains A26-A28 for Supplements S1 and S4.
- **F-2, section 9, after A25.** Three facts, status "final, post hoc (Part 628)":
  - A26: what was read of the comparison's results before the re-computation (the layout read of the 21:18
    burned-fraction comparison and AZ1; when the coral read was first recorded and question C10; the agent's chat
    messages before the author accepted all six recommendations). Sources: PROTOCOL.md section 14 (three entries), rulings AZ and BB.
  - A27: how the S3.13 tables and Table 9 were built, with the two builders' script hashes and the byte-identity of
    both builders' tables.md and cells.json with the agreed copies (d05a6856..., 3c2ac02d...). Sources: tables_agreed.md
    line 1, the two briefs, reads_tables.md, the hashes.
  - A28: the comparison's times in UTC and the evidence that the records use UTC+1 (above).
  Why: every number the new S1 and S4 text prints needs a fact; A9-A25 did not hold the reads, the table build or the
  UTC times. Next free ID: A29.

## Checks run (all read-only; scripts in `STAGE\_scripts\s1s4\`)

- `check_s1s4.py`: encoding and line endings as the live files (no BOM; S1 and PAPER_FACTS LF only, S4 CRLF only);
  the build's cross-reference rules (BARE_SUP_RE, SUP_REF_RE, SEC_REF_RE and supplement table captions, copied from
  `ROOT\paper\build\build_docx.py`) over the staged S1 and S4 against the supplement and main headings (staged copies
  where they exist): 0 problems, none new; the privacy scan (account, host and user-folder names from the environment,
  user-folder paths, session and workflow ids): no new occurrence; no absolute path in the new visible text of S1 or S4
  (D:/ paths only in comments; PAPER_FACTS uses D:/ paths by its own rule); S1.10 equals the row counts; PH1-PH30 in
  order; Table S4.14 counts and prefixes as above; the S4.13 quotes are in the rulings file; every fact cited exists;
  the glossary's do-not-use names over the new visible text (hits only inside paper terms such as "tree bank",
  "survey visit", "skill guard", "D8 tolerance", "rival board", or generic words; "a pool of earlier nearby survey
  visits" and "calendar month" follow the agreed tables and S3.13).
- `check_comments.py`: every `<!--` has its `-->` (S1 83, S4 143), none nested; the only new year token in visible text
  is "October 2026" (S4 row AX), which the build's citation scanner skips ("October" is a stop word).
- The paper build was not run.

## Process notes

- Python only as `py -3.9 -I -B <script>`; no pip, no environment change. One PowerShell call read
  `[System.TimeZoneInfo]::Local` (base offset and DST support only) and file times with Get-Item.
- `hash_files.py` opened each named file only to hash its bytes; no SHAP, V or engine script was run.
  `SHAP\smoke\bardl_fix\` was never entered; no Grep or Glob ran over SHAP or V; AW3_table.md, AW4_table.md and
  `V\reconcile\report.md` were not opened (their folders were listed, names and sizes only).
- Nothing was written outside STAGE.

## Open points

1. Archive paths: S4's visible text names `analysis/shap_v1/` (by analogy with `analysis/paper_posthoc/`) and
   `paper/supp_build/s3_13/` for Part 628's files (Table S4.11's caption and row, Table S4.14's group headings). The
   staged archive manifest held no SHAP or supp_build entry when I looked; the lead should align these with the
   records writer's manifest paths.
2. PROTOCOL.md (and RUN_COMMANDS.md, SAMPLE_REGISTER.txt, V's results files) are not in Table S4.11; PROTOCOL.md's hash
   changes when the lead applies this write-up's change-log entry. Add them with their final hashes after the apply if
   wanted (also to Table S4.14).
3. S3.13's "When and why" (S3 writer's file) says "we recorded that the burned-fraction comparison written on
   2026-11-13, before Ridge was added, had not been read (ruling AZ1)"; an agent had opened it for its layout (PH28).
   Consider "had not been read by the author", or a pointer to S1.7.
4. RP18's model list is fact M14b's scan of 2026-11-10; the SHAP analysis and this write-up came later. I added one
   sentence saying so; a re-scan would be needed to name the later sessions' models. Drop the sentence if the lead
   prefers.
5. Table S4.14's earlier count was one short (234 against 235 rows found by script); the comment now says so. Which row
   the earlier count missed is not traced.
6. PH29's comment points to the records writer's staged PROTOCOL.md entry of 2026-11-17 (the correction of "other
   sites' visits"); edit the comment if that entry is not applied.
7. S4.11 (open items) is unchanged: SHAP decision D7 (the Kraft LSTM) and items 2-13 of the 2026-11-13 decision list
   stay open but S4.11 lists only the runs' open items; S1 PH24 and S4.13 rows AY and AX state them.
8. S3.13 and Table S3.22's note d give the BB6 times in local time without naming the zone; S1 PH27 names it and S4.2
   gives UTC (about 14:31; written 2026-11-12 23:06 UTC).
9. S1's "Agent" definition and Section 2.9 (main text, not touched) describe the agents' work generally; whether 2.9
   should name the SHAP analysis is the lead's call (ruling AT11 open).
10. Comments cite helper scripts under `paper/supp_build/s3_13/stage/_scripts/s1s4/`; if the stage folder is not
    archived, move them or drop the pointers.
11. Apply together with the staged S3_posthoc.md, 05_rivals.md, tables/table_9.md, TABLE_NUMBERS.md and GLOSSARY.md:
    S1's Where cells cite 5.4, Table 9, S3.13 and Tables S3.18-S3.30, and S4 cites Supplement S3.13.
