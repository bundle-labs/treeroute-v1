# apply_fix.py - the fixer's edits of the staged write-up (S3.13 write-up, 2026-11-17), on the staged files only.
# Each edit is an exact replacement whose old text must occur exactly once and whose new text then occurs exactly
# once. A file is edited only from its pre-fix state (SHA-256 in work/base_hashes.json); on a re-run the script first
# undoes the edits it recorded in work/applied_edits.json (new -> old, in reverse order), checks that the pre-fix hash
# is reached, and applies the current list. Encoding (UTF-8, no BOM) and line endings are kept: no edit adds or removes
# a line ending, except the PROTOCOL.md and ARCHIVE_MANIFEST_DRAFT.md blocks, which are LF-only files.
import json
import sys
import textwrap
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fix_lib import STAGE, WORK, sha, form

E = {}  # rel -> list of (id, old, new)


def add(rel, eid, old, new):
    E.setdefault(rel, []).append((eid, old, new))


def wrap_bullet(text, first='  - ', rest='    '):
    return '\n'.join(textwrap.wrap(text, width=120, initial_indent=first, subsequent_indent=rest,
                                   break_on_hyphens=False, break_long_words=False))


# ---------------------------------------------------------------- S3_posthoc.md
S3 = 'paper/draft/S3_posthoc.md'
add(S3, 'S3-1 header comment',
    "One caption was changed, for a point of the last table check: Table S3.21's now says that each problem's tree bank "
    "with its correctors and placebos, and the sampled locations' routers, were rebuilt; no table cell changed.",
    "One caption was changed, for a point of the last table check: Table S3.21's now says that each problem's tree bank "
    "with its correctors and placebos, and the sampled locations' routers, were rebuilt; no table cell changed. In the "
    "write-up's fix pass (2026-11-17, after its checks), one agreed note was reworded: Table S3.30's last note cites "
    "\"(Table S3.28 and Table S3.29)\" for \"(Tables S3.28 and S3.29)\", because the build reads a bare \"S3.29\" as a "
    "supplement heading; and S3.13's prose was corrected: ruling AZ1's sentence (the comparison of four models, which "
    "we had not opened; its layout was opened, Supplement S1.7), the protocol's revision of its sample and statistics "
    "sections before the freeze, coral bleaching's 50,000 background pairs, the time zone of the BB6 times, the archive "
    "path of the B1 values' results file, three do-not-use names (headline runs, boards, rows for survey visits) and "
    "S3.0's facts comment on Part 628's status words; facts A9 and A11 were corrected with it; no number changed.")
add(S3, 'S3-2 S3.0 facts comment (Part 628 status words)',
    "628: 2026-11-12, DRAFT, with its dated addendum of 2026-11-17)",
    "628: 2026-11-12, \"DRAFT 2026-11-12; RUN 2026-11-12 TO 2026-11-16 AT SCOPE (i), B1 INCLUDED, EVERY PIECE FINISHED, "
    "E5 INFORMATIONAL; RE-COMPUTED INDEPENDENTLY 2026-11-16; WRITTEN UP 2026-11-17, SUPPLEMENT S3.13 AND TABLE 9\", "
    "with its dated addendum of 2026-11-17)")
add(S3, 'S3-3 When and why: run (do-not-use "headline run")',
    "we decided that a SHAP analysis be run on treeroute v1's headline runs of all five problems",
    "we decided that a SHAP analysis be run on treeroute v1's runs of all five problems")
add(S3, 'S3-4 When and why: protocol versions; survey visits',
    "The analysis protocol was first written before any SHAP value had been computed on a real data row, and its "
    "sections on the sample and the statistics were frozen when the first sample was registered, on 2026-11-12; smoke "
    "tests computed SHAP values on real rows only as plumbing (at most 250 coral bleaching rows before those sections "
    "were frozen",
    "The analysis protocol was first written before any SHAP value had been computed on a real data row; its sections "
    "on the sample and the statistics, revised after the first smoke tests because of two design reviews' method "
    "findings (not of any value), were frozen when the first sample was registered, on 2026-11-12; smoke tests computed "
    "SHAP values on real rows only as plumbing (at most 250 coral bleaching survey visits before those sections were "
    "frozen")
add(S3, 'S3-5 When and why: ruling AZ1',
    "On 2026-11-14 we recorded that the burned-fraction comparison written on 2026-11-13, before Ridge was added, had "
    "not been read (ruling AZ1). <!-- A9; ruling AZ1 -->",
    "On 2026-11-14 we recorded that we had not opened the burned-fraction comparison of four models written on "
    "2026-11-13, before Ridge was added (ruling AZ1; its layout was opened, as Supplement S1.7 records). "
    "<!-- A9; ruling AZ1 (\"the owner had not opened that comparison before ridge was added\", the comparison of "
    "2026-11-13 21:18, four models); Supplement S1.7, row PH28; fact A26 (a) -->")
add(S3, 'S3-6 Method: coral background pairs',
    "(of the 50,000, 980 are at the explained survey visit's own reef site, in 415 of the 1,000 sample rows, and none "
    "is dated on or after the explained survey visit)",
    "(of the 50,000 background pairs, 980 pair an explained survey visit with an earlier survey visit at its own reef "
    "site, for 415 of the 1,000 explained survey visits, and in none is the background survey visit dated on or after "
    "the explained one)")
add(S3, 'S3-7 Models explained: rival boards (do-not-use "board")',
    "Every common rival of the nowcast boards was explained",
    "Every common rival of the nowcast rival boards was explained")
add(S3, 'S3-8 B1 paragraph: archived results file',
    "is in the re-computation's results file (verify_v1/A/results.json, key b1); of B1's per-player numbers this "
    "section prints only its top 3 and top 10. <!-- A22; SHAP protocol sections 9 and 10 -->",
    "is in the re-computation's results file, archived as analysis/shap_v1/verify_v1/A/results.json (key b1); of B1's "
    "per-player numbers this section prints only its top 3 and top 10. <!-- A22; SHAP protocol sections 9 and 10; the "
    "archive path: _archive_plan/ARCHIVE_MANIFEST_DRAFT.md section 2.5 and section 8 (a) -->")
add(S3, 'S3-9 Table S3.30 last note (bare S3.29)',
    "so the B1 numbers of PM2.5, NDVI and burned fraction are reported (Tables S3.28 and S3.29).",
    "so the B1 numbers of PM2.5, NDVI and burned fraction are reported (Table S3.28 and Table S3.29).")
add(S3, 'S3-10 Presentation: BB6 (the comparison reported here; local time, UTC+1)',
    "Coral bleaching's table of the main-text statistics (`AW4_table.md`, written on 2026-11-13 at 00:06) was read on "
    "2026-11-13 at about 15:31, before the independent re-computation; the re-computation's implementers A and B never "
    "opened it (BB6; Supplement S1.7 records who read it). <!-- A25 -->",
    "Coral bleaching's table of the main-text statistics, from the comparison reported here (`AW4_table.md`, written "
    "on 2026-11-13 at 00:06), was read on 2026-11-13 at about 15:31 (local time, UTC+1), before the independent "
    "re-computation; the re-computation's implementers A and B never opened it (BB6; Supplement S1.7 records who read "
    "it). <!-- A25 (the current coral comparison's table, ruling BB6); A28 (local time, UTC+1) -->")

# ---------------------------------------------------------------- S1_disclosures.md
S1 = 'paper/draft/S1_disclosures.md'
add(S1, 'S1-1 header comment',
    "No existing row was removed or moved, and no existing number changed. GPCC download outcome, fixes after the checks",
    "No existing row was removed or moved, and no existing number changed. Fix pass of the same write-up (2026-11-17, "
    "after its checks): PH22 now says that the protocol was first written (version 1) before any SHAP value on a real "
    "data row and that its sample and statistics sections were revised after the first smoke tests (version 3), "
    "because of two design reviews' method findings, before the freeze; PH23's sentence on gates E3a and E10 is split "
    "in two; PH25 gives the results file's archive path; PH26's BB1 clause names only the first two departures; PH22 "
    "and PH29 say survey visits, and PH29 counts the 50,000 as background pairs. No number changed. GPCC download "
    "outcome, fixes after the checks")
add(S1, 'S1-2 PH22 protocol versions; survey visits',
    "The analysis protocol was written before any SHAP value had been computed on a real data row, and its sections on "
    "the sample and the statistics were frozen when the first sample was registered (2026-11-12); smoke tests computed "
    "SHAP values on real rows only as plumbing (at most 250 coral bleaching rows before those sections were frozen",
    "The analysis protocol was first written (version 1) before any SHAP value had been computed on a real data row; "
    "its sections on the sample and the statistics were revised after the first smoke tests (version 3), because of "
    "two design reviews' method findings, not of any value, and were frozen when the first sample was registered "
    "(2026-11-12); smoke tests computed SHAP values on real rows only as plumbing (at most 250 coral bleaching survey "
    "visits before those sections were frozen")
add(S1, 'S1-3 PH22 comment (fact A9: version 3)',
    "facts A9 (protocol version 1 before any SHAP value on a real data row; sections 3 and 8 frozen at the first "
    "registration,",
    "facts A9 (protocol version 1 before any SHAP value on a real data row; version 3 changed sections 3 and 8 after "
    "the v2 and v3 smokes, because two design reviewers had found that the code and the text disagreed and that "
    "several statistics were biased, every change answering a method finding, not a value; sections 3 and 8 frozen at "
    "the first registration,")
add(S1, 'S1-4 PH23 E3a and E10 (split in two)',
    "On coral bleaching, gate E3a compares no data file before the labels are read (its static file list is empty, and "
    "its label-file list cannot be read before the labels), and gate E10 checks the exported trees on one sampled "
    "location's router fit rows and test rows only (on coral bleaching one survey visit's router fit rows and test row; "
    "on forest loss every sampled location).",
    "On coral bleaching, gate E3a compares no data file before the labels are read (its static file list is empty, and "
    "its label-file list cannot be read before the labels). Gate E10 checks the exported trees on one sampled "
    "location's router fit rows and test rows on PM2.5, NDVI and burned fraction, on one survey visit's router fit "
    "rows and test row on coral bleaching, and on every sampled location on forest loss.")
add(S1, 'S1-5 PH25 archived results file',
    "and gives the per-player values through the re-computation's results file. <!--",
    "and gives the per-player values through the re-computation's results file, archived as "
    "analysis/shap_v1/verify_v1/A/results.json (key b1). <!--")
add(S1, 'S1-6 PH25 comment',
    "\"The re-computation's results file\", as S3.13 and Table S3.29 call it, not \"the archived results file\", "
    "because the archive is still a plan -->",
    "\"The re-computation's results file\", as S3.13 and Table S3.29 call it; its archive path, which S3.13 also gives, "
    "is the archive plan's (_archive_plan/ARCHIVE_MANIFEST_DRAFT.md section 2.5 and section 8 (a); fix pass of the "
    "write-up, 2026-11-17; the row had said \"the re-computation's results file\" only, because the archive is still "
    "a plan) -->")
add(S1, 'S1-7 PH26 BB1 clause (first two departures)',
    "By ruling BB1 these entries come from the re-computation, so in them S3.13 and Table 9 differ",
    "By ruling BB1 the entries of the first two come from the re-computation, so in them S3.13 and Table 9 differ")
add(S1, 'S1-8 PH29 background pairs; survey visits',
    "but of its 50,000 background survey visits (50 per explained survey visit), 980 are earlier visits at the "
    "explained survey visit's own reef site (for 415 of the 1,000 explained survey visits), and none is dated on or "
    "after its explained survey visit.",
    "but of its 50,000 background pairs (50 background survey visits for each explained survey visit), 980 pair an "
    "explained survey visit with an earlier survey visit at its own reef site (for 415 of the 1,000 explained survey "
    "visits), and in none is the background survey visit dated on or after the explained one.")
add(S1, 'S1-9 PH29 comment',
    "980 of 50,000 at the same reef site, in 415 of the 1,000 sample rows;",
    "980 of the 50,000 background pairs at the same reef site, in 415 of the 1,000 sample rows;")
add(S1, 'S1-10 S1.7 comment after the table (PH25)',
    "PH25 gives B1's per-player values through the re-computation's results file, as S3.13 does. -->",
    "PH25 gives B1's per-player values through the re-computation's results file, with its archive path, as S3.13 "
    "does. -->")

# ---------------------------------------------------------------- S4_provenance.md (CRLF; edits inside lines)
S4 = 'paper/draft/S4_provenance.md'
add(S4, 'S4-1 header comment',
    "No existing hash, time or locked verdict changed; CRLF line endings kept.",
    "No existing hash, time or locked verdict changed; CRLF line endings kept. Fix pass of the same write-up "
    "(2026-11-17, after its checks): the S4.2 sentence and the comment on the new rows now except ruling AX, which is "
    "not part of the SHAP comparison; the re-computation row adds its three explained cases; Table S4.11's row 628 and "
    "Table S4.14's group heading give the table builders' folder as the archive plan archives it, "
    "analysis/paper/supp_build/s3_13/; the comments' script paths name the folder that the write-up's scripts are "
    "copied to (paper/supp_build/s3_13/writeup/). No number, hash or time changed.")
add(S4, 'S4-2 S4.2 opening sentence (ruling AX)',
    "The rows from 2026-11-12 on are the post hoc SHAP comparison of Supplement S3.13 (Part 628), which ran after every "
    "lock and test-label opening above. <!-- S3.13 write-up, 2026-11-17: ruling AK; facts A9 and A28 -->",
    "The rows from 2026-11-12 on, except ruling AX (the GPCC download, in the row of 2026-11-13), are the post hoc SHAP "
    "comparison of Supplement S3.13 (Part 628), which ran after every lock and test-label opening above. <!-- S3.13 "
    "write-up, 2026-11-17: ruling AK; facts A9 and A28; ruling AX (engine/OWNER_RULINGS_2026-10-06.md section AX, the "
    "GPCC download) is not part of Part 628 (fix pass of the write-up) -->")
add(S4, 'S4-3 S4.2 re-computation row (three explained cases)',
    "every number of the comparison's files that both implementations hold agrees within 10⁻⁹ (Supplement S3.13)",
    "every number of the comparison's files that both implementations hold agrees within 10⁻⁹, except in three "
    "explained cases (Supplement S3.13)")
add(S4, 'S4-4 S4.2 comment after the table',
    "the ten rows of 2026-11-12 to 2026-11-16 are the post hoc SHAP comparison (Part 628).",
    "the ten rows of 2026-11-12 to 2026-11-16 are the post hoc SHAP comparison (Part 628), except ruling AX (the GPCC "
    "download, AX1), which shares the row of 2026-11-13 with ruling AY; the re-computation row's three explained cases: "
    "fact A23 (fix pass of the write-up).")
add(S4, 'S4-5 Table S4.11 row 628 archive path',
    "the scripts of the two independent builders of the S3.13 tables and Table 9, in `paper/supp_build/s3_13/`. "
    "Results: Supplement S3.13",
    "the scripts of the two independent builders of the S3.13 tables and Table 9, in "
    "`analysis/paper/supp_build/s3_13/`. Results: Supplement S3.13")
add(S4, 'S4-6 Table S4.11 comment script path',
    "by a script (paper/supp_build/s3_13/stage/_scripts/s1s4/hash_files.py) on 2026-11-17",
    "by a script (paper/supp_build/s3_13/writeup/_scripts/s1s4/hash_files.py) on 2026-11-17")
add(S4, 'S4-7 Table S4.14 group heading archive path',
    "| **Post hoc SHAP comparison, Part 628: the S3.13 table builders' scripts (`paper/supp_build/s3_13/`; Table S4.11; "
    "read 2026-11-17)** | | |",
    "| **Post hoc SHAP comparison, Part 628: the S3.13 table builders' scripts (`analysis/paper/supp_build/s3_13/`; "
    "Table S4.11; read 2026-11-17)** | | |")
add(S4, 'S4-8 Table S4.14 comment script paths',
    "read-only, by paper/supp_build/s3_13/stage/_scripts/s1s4/hash_files.py). A recount by script on 2026-11-17 "
    "(paper/supp_build/s3_13/stage/_scripts/s1s4/count_s414.py)",
    "read-only, by paper/supp_build/s3_13/writeup/_scripts/s1s4/hash_files.py). A recount by script on 2026-11-17 "
    "(paper/supp_build/s3_13/writeup/_scripts/s1s4/count_s414.py)")

# ---------------------------------------------------------------- GLOSSARY.md (CRLF; edits inside lines)
GL = 'paper/draft/GLOSSARY.md'
add(GL, 'G-1 SHAP value first defined (named 5.4)',
    "the bare phi is the link (row link; Section 2.7). --> | S3.13 (named Table 9) |",
    "the bare phi is the link (row link; Section 2.7). --> | S3.13 (named 5.4) |")
add(GL, 'G-2 player row (catalog code)',
    "aggregate and window suffixes and catalog code are stripped",
    "aggregate and window suffixes and their numbered code prefix (such as V02_) are stripped")
add(GL, 'G-3 main set first defined (named 5.4)',
    "(model sets; main-text row); Table 9 caption and note a; Table S3.18 --> | Table 9 (Section 5.4) |",
    "(model sets; main-text row); Table 9 caption and note a; Table S3.18 --> | Table 9 (named 5.4) |")
add(GL, 'G-4 same-link first defined (named 5.4)',
    "Table S3.18 note on links; Tables S3.23-S3.27 captions --> | S3.13 (named Table 9) |",
    "Table S3.18 note on links; Tables S3.23-S3.27 captions --> | S3.13 (named 5.4) |")
add(GL, "G-5 Kendall's W first defined (named 5.4)",
    "Table 9 caption and note a; Tables S3.23-S3.27, panel c --> | Table 9 (Section 5.4) |",
    "Table 9 caption and note a; Tables S3.23-S3.27, panel c --> | Table 9 (named 5.4) |")
add(GL, 'G-6 history comment',
    "and D8 tolerance. No existing row changed. -->",
    "and D8 tolerance. No existing row changed. Fix pass of the same write-up (2026-11-17, after its checks): "
    "\"First defined\" of SHAP value and same-link / cross-link now reads \"S3.13 (named 5.4)\", and of main set and "
    "Kendall's W \"Table 9 (named 5.4)\", because Section 5.4's new paragraph names these terms before Table 9; the "
    "player row says \"their numbered code prefix (such as V02_)\", as S3.13 does, for \"catalog code\" (catalog is a "
    "do-not-use name of the dataset package). -->")

# ---------------------------------------------------------------- REFERENCES.md
RF = 'paper/draft/REFERENCES.md'
add(RF, 'R-1 history comment: pointer and fix-pass note',
    "(paper/supp_build/s3_13/stage/refs_candidates.md; each was checked on 2026-11-17 as its Check note says) and "
    "placed where the build's sort key (authors, then year) puts it: Janzing2020_interventional, "
    "KendallBabingtonSmith1939_W, LundbergLee2017_SHAP, Lundberg2020_TreeSHAP and Webber2010_RBO. No other entry "
    "changed, and no printed number changed.",
    "(paper/supp_build/s3_13/writeup/refs_candidates.md; each was checked on 2026-11-17 as its Check note says) and "
    "placed where the build's sort key (authors, then year) puts it: Janzing2020_interventional, "
    "KendallBabingtonSmith1939_W, LundbergLee2017_SHAP, Lundberg2020_TreeSHAP and Webber2010_RBO. No other entry "
    "changed, and no printed number changed. Fix pass of the same write-up (2026-11-17, after its checks): "
    "LundbergLee2017_SHAP's Supports note adds Section 5.4, which now cites it for SHAP values, and Webber2010_RBO's "
    "note no longer points to a table above it, which this file does not hold; both changes are after the Key marker, "
    "so no printed text changed.")
add(RF, 'R-2 LundbergLee2017_SHAP Supports adds Section 5.4',
    "(each coefficient times the row's difference from its background) (Supplement S3.13, method paragraph; Table "
    "S3.18 a).",
    "(each coefficient times the row's difference from its background) (Section 5.4, SHAP values; Supplement S3.13, "
    "method paragraph; Table S3.18 a).")
add(RF, 'R-3 Webber2010_RBO stale pointer',
    "Cite it as \"Webber et al. 2010\" (see the table above).",
    "Cite it as \"Webber et al. 2010\": the build does not resolve \"Webber, Moffat and Zobel 2010\".")

# ---------------------------------------------------------------- PAPER_FACTS.md
PF = 'paper/PAPER_FACTS.md'
add(PF, 'F-1 revision paragraph',
    " Copy of this sheet before the S3.13 write-up, 2026-11-17: paper/draft/_snapshots/@@SNAP@@/.",
    " In the write-up's fix pass (2026-11-17, after its checks), A9 also records that version 3 of the SHAP protocol "
    "revised its sections 3 and 8 after the smoke tests, in answer to two design reviewers' method findings, and gives "
    "ruling AZ1 as the author's not having opened the comparison (it had been opened once for its layout, A26 (a)); "
    "A11 counts the 50,000 as background pairs; A16 gives burned fraction's stored W as NaN, as its source file stores "
    "it (cells.json writes null); and A27's script path names the folder that the write-up's scripts are copied to. "
    "No number changed. Copy of this sheet before the S3.13 write-up, 2026-11-17: paper/draft/_snapshots/@@SNAP@@/.")
add(PF, 'F-2 A9 AZ1',
    "the burned-fraction comparison of 2026-11-13 21:18 (four models, without Ridge) had not been read before Ridge was "
    "added.",
    "the author had not opened the burned-fraction comparison of 2026-11-13 21:18 (four models, without Ridge) before "
    "Ridge was added (the author's answer); it had been opened once, by an agent, for its layout only (A26 (a)).")
add(PF, 'F-3 A9 protocol version 3',
    "as plumbing, with no statistic read as a result; sections 3 (sample) and 8 (statistics) were frozen when the first "
    "sample was registered;",
    "as plumbing, with no statistic read as a result; version 3 (2026-11-12, before any registration) changed sections "
    "3 and 8 after those smokes, because two design reviewers had found that the code and the text disagreed and that "
    "several statistics were biased, and every change answers a method finding, not a value (preamble; section 14, v3 "
    "entry); sections 3 (sample) and 8 (statistics) were frozen when the first sample was registered;")
add(PF, 'F-4 A11 background pairs',
    "Of the 50,000, 980 are earlier visits at the explained visit's own reef site, in 415 of the 1,000 sample rows, and "
    "none is dated on or after the explained visit.",
    "Of the 50,000 pairs, 980 pair the explained visit with an earlier visit at its own reef site, in 415 of the 1,000 "
    "sample rows, and in none is the background visit dated on or after the explained visit (line 33: \"background "
    "pairs: 50000; same reef site: 980 in 415 sample rows; dated on/after the explained visit: 0\").")
add(PF, 'F-5 A16 stored NaN',
    "burned fraction undefined (main set treeroute v1 alone; stored null).",
    "burned fraction undefined (main set treeroute v1 alone; stored NaN, with 0 finite draws, which cells.json writes "
    "as null).")
add(PF, 'F-6 A27 script path',
    "(hashed read-only on 2026-11-17 by paper/supp_build/s3_13/stage/_scripts/s1s4/hash_files.py)",
    "(hashed read-only on 2026-11-17 by paper/supp_build/s3_13/writeup/_scripts/s1s4/hash_files.py)")

# ---------------------------------------------------------------- shap/PROTOCOL.md (LF; ASCII; lines <= 120)
PR = 'shap/PROTOCOL.md'
P_OLD1 = (
    "  - What was written, and from what. Supplement S3.13 (Tables S3.18 to S3.30) and the main-text Table 9 (Section 5.4)\n"
    "    take every number of the comparison from the `compare/` files, from `verify_v1/A/results.json` (the numbers of\n"
    "    rulings BB1 and BB2, and every B1 number but the B1 runs' background pairs and seconds) and from the B1 runs' log\n"
    "    lines (those pairs and seconds), through the checked tables `paper/supp_build/s3_13/reconcile/tables_agreed.md`\n"
    "    (version 5), with `cells.json` beside them giving each printed number's source, selector and stored value. Two\n"
    "    builders built the tables independently from the stored values, with one rounding step, by one specification\n"
    "    (`paper/supp_build/s3_13/spec/TABLE_SPEC.md`); a reconciler compared their tables with each other and with the\n"
    "    printouts, and a checker checked each version. Versions 2 to 5 reworded captions, notes, labels and cells after\n"
    "    four checks and changed no number. Each prose number of S3.13 and Section 5.4 is formatted once from its stored\n"
    "    value and carries a fact ID (the paper's facts A9 to A25). Every number stays post hoc and is labelled so.")
P_NEW1 = wrap_bullet(
    "What was written, and from what. Supplement S3.13 (Tables S3.18 to S3.30) and the main-text Table 9 (Section 5.4) "
    "take every number of the comparison from the `compare/` files, from `verify_v1/A/results.json` (the numbers of "
    "ruling BB1, and every B1 number but the B1 runs' background pairs and seconds), from the B1 runs' log lines (those "
    "pairs and seconds) and from `verify_v1/_lead/outputs/bardl_maxima.txt` (the spreads of ruling BB3's footnote); by "
    "ruling BB2 the feature-level family-share distance repeats the variable-level value (from the `compare/` files, "
    "and for B1 from `results.json`). The numbers of the samples, the exactness checks and the rebuild gates come from "
    "`SAMPLE_REGISTER.txt`, the sample manifests, the pieces' `meta.json` and exactness records and the rebuild "
    "`gates.json`. All of them reach the paper through the checked tables "
    "`paper/supp_build/s3_13/reconcile/tables_agreed.md` (version 5), with `cells.json` beside them giving each printed "
    "number's source, selector and stored value. Two builders built the tables independently from the stored values, "
    "with one rounding step, by one specification (`paper/supp_build/s3_13/spec/TABLE_SPEC.md`); a reconciler compared "
    "their tables with each other and with the printouts, and a checker checked each version. Versions 2 to 5 reworded "
    "captions, notes, labels and cells after four checks and changed no number. Each prose number of S3.13 and Section "
    "5.4 is formatted once from its stored value and carries a fact ID (the paper's facts A9 to A25). Every number "
    "stays post hoc and is labelled so.")
add(PR, 'P-1 what was written, and from what (BB2; bardl_maxima.txt; samples and checks)', P_OLD1, P_NEW1)
P_OLD2 = (
    "  - A correction of this protocol's wording; the old lines stay as written. Section 5 (lines 375 and 381-382) calls\n"
    "    coral's B2 background, the visit's saved 50-visit router pool, \"other sites' visits\" and \"a pool of other sites\",\n"
    "    and section 10 (\"Not claimed\", lines 673-674) repeats \"other sites' visits\". Some of the pool is at the explained\n"
    "    visit's own reef site: of the 50,000 background visits of the 1,000 coral sample rows, 980 are earlier visits at\n"
    "    the explained visit's own reef site, in 415 of the sample rows, and none is dated on or after the explained visit\n"
    "    (a read-only count of `out/coral/lead_0/treeroute/background_keys.parquet` against its `rows.parquet`, the reef\n"
    "    site being a key's text before \"|\": `paper/supp_build/s3_13/_brief/lead_checks/verify_v5_claims_out.txt`, line\n"
    "    33). The conclusion of sections 5 and 10 stands: there, static and calendar columns are not zero by construction\n"
    "    and can carry attribution. The paper says \"a pool of earlier nearby survey visits\".")
P_NEW2 = wrap_bullet(
    "A correction of this protocol's wording; the old lines stay as written. Section 5 (lines 375 and 381-382) calls "
    "coral's B2 background, the visit's saved 50-visit router pool, \"other sites' visits\" and \"a pool of other "
    "sites\", and section 10 (\"Not claimed\", lines 673-674) repeats \"other sites' visits\". Some of the pool is at "
    "the explained visit's own reef site: of the 50,000 background pairs of the 1,000 coral sample rows (50 per row), "
    "980 pair the explained visit with an earlier visit at its own reef site, in 415 of the sample rows, and in none "
    "is the background visit dated on or after the explained visit (a read-only count of "
    "`out/coral/lead_0/treeroute/background_keys.parquet` against its `rows.parquet`, the reef site being a key's text "
    "before \"|\": `paper/supp_build/s3_13/_brief/lead_checks/verify_v5_claims_out.txt`, line 33). The conclusion of "
    "sections 5 and 10 stands: there, static and calendar columns are not zero by construction and can carry "
    "attribution. The paper says \"a pool of earlier nearby survey visits\".")
add(PR, 'P-2 the wording correction (background pairs)', P_OLD2, P_NEW2)

# ---------------------------------------------------------------- ARCHIVE_MANIFEST_DRAFT.md (LF)
AM = '_archive_plan/ARCHIVE_MANIFEST_DRAFT.md'
add(AM, 'M-1 Measured bullet (fix pass times)',
    "a count-only privacy scan of the table build's 226 archived files 10:04:44-10:04:48; no file of the SHAP folder "
    "was opened.",
    "a count-only privacy scan of the table build's 226 archived files 10:04:44-10:04:48; no file of the SHAP folder "
    "was opened. In the write-up's fix pass: the table build's 226 archived files listed again by file metadata at "
    "10:49:45, after two of them had been rewritten (10:12:11 and 10:12:15; 2.5), and those two scanned count-only at "
    "10:50:02.")
add(AM, 'M-2 2.5 bullet: the two rewritten files; no survey-visit key',
    "(the old user name was not in the patterns; the scan of 6.5 covers it at packaging). The one check output "
    "`_brief\\lead_checks\\verify_v5_claims_out.txt` prints two coral survey-visit keys (region code, coordinates and "
    "date, from the CC0 coral database; no CoralTemp value and no label).",
    "(the old user name was not in the patterns; the scan of 6.5 covers it at packaging). After this listing and this "
    "scan, two files of `_brief\\lead_checks\\` were rewritten (2026-11-17, 10:12:11 and 10:12:15 UTC): the lead's "
    "check script `verify_v5_claims.py` (3,346 B when listed, now 3,271 B) and its output `verify_v5_claims_out.txt` "
    "(2,055 B, now 1,971 B), which now prints the merged-duplicate counts and names, the key columns' names and the "
    "coral counts of its line 33, and no coral survey-visit key. Listed again by file metadata (10:49:45 UTC), the 226 "
    "archived files hold 32,661,794 B, 159 B fewer, so each total that adds them is 159 B smaller (the .py bytes of "
    "7.2, 75 B smaller) and no GB, GiB or MB figure changes; this plan keeps the totals of the 09:34 listing, and "
    "packaging re-takes them. A count-only scan of the two rewritten files with the patterns above (10:50:02 UTC) found "
    "none of them.")
add(AM, 'M-3 6.5 note (re-scan)',
    "workflow ids and e-mail addresses: none holds any (2.5).",
    "workflow ids and e-mail addresses: none holds any (2.5); the two of them rewritten after that scan were scanned "
    "again with the same patterns in the write-up's fix pass: none (2.5).")
add(AM, 'M-4 section 7 changes paragraph',
    "Before this round: main archive 4,920 files, 4,562,805,109 B (4.56 GB, 4.25 GiB); main + 5A 7,719 files, "
    "5,218,791,471 B; GitHub part 2,231 files, 118,565,849 B.",
    "Before this round: main archive 4,920 files, 4,562,805,109 B (4.56 GB, 4.25 GiB); main + 5A 7,719 files, "
    "5,218,791,471 B; GitHub part 2,231 files, 118,565,849 B. Two files of the table build were rewritten after its "
    "listing (2.5): with their current sizes each total above that holds the table build is 159 B smaller, and no GB "
    "or GiB figure changes.")
add(AM, 'M-5 7.2 .py bytes',
    "The 367 .py files they add (4,131,267 B) are not in the program-size counts above",
    "The 367 .py files they add (4,131,267 B when listed; 4,131,192 B since the lead's check script was rewritten, 2.5) "
    "are not in the program-size counts above")
add(AM, 'M-6 section 8 item (a)',
    "(a) S3.13 points to `verify_v1/A/results.json` (key b1) for every B1 player's numbers and does not yet call it "
    "archived: this plan archives it, as `analysis/shap_v1/verify_v1/A/results.json` (2.5).",
    "(a) S3.13 points to `verify_v1/A/results.json` (key b1) for every B1 player's numbers and, since the write-up's "
    "fix pass, calls it archived, with this plan's archive path `analysis/shap_v1/verify_v1/A/results.json` (2.5), as "
    "Supplement S1's row PH25 does; the file must stay in the archive.")
add(AM, 'M-7 section 8 new item (e)',
    "stay checkable from the archive only if its pre-edit copy is kept in `TR\\analysis\\shap_v1\\_snapshots\\` "
    "(archived, 2.5).",
    "stay checkable from the archive only if its pre-edit copy is kept in `TR\\analysis\\shap_v1\\_snapshots\\` "
    "(archived, 2.5). (e) Added in the write-up's fix pass: `ROOT\\paper\\supp_build\\s3_13\\writeup\\`, to which the "
    "lead copies this write-up's scripts and change records from `stage\\` when the write-up is applied, and the "
    "`checks\\` folders of the write-up's checks (`ROOT\\paper\\supp_build\\s3_13\\checks\\`) were written after the "
    "listing of 2.5 and are not among its 226 files; both are listed and classed at packaging.")
add(AM, 'M-8 appendix B (fix pass bullet)',
    "- 4.1, 6.5 and the KEPT_OUT.md line of 4.2 name the new items, and section 8 gains the lead's items of the "
    "write-up.\n",
    "- 4.1, 6.5 and the KEPT_OUT.md line of 4.2 name the new items, and section 8 gains the lead's items of the "
    "write-up.\n"
    "- Fix pass of the write-up (2026-11-17, after its checks): the two files of the table build rewritten after the "
    "listing are recorded in 2.5 (159 B fewer in all; the check output now prints no survey-visit key; a count-only "
    "re-scan found none of the patterns), with notes in the header, 6.5, section 7 and 7.2; the totals stay those of "
    "the 09:34 listing. Section 8's item (a) now says that S3.13 calls the results file archived, and its new item (e) "
    "classes `writeup\\` and `checks\\` at packaging.\n")


# ---------------------------------------------------------------- engine
def apply_file(rel, edits, pre_sha, prev):
    p = STAGE / rel
    b = p.read_bytes()
    t = b.decode('utf-8')
    if sha(b) != pre_sha:
        if rel not in prev:
            raise SystemExit('%s: not in its pre-fix state and no recorded edits to undo' % rel)
        for eid, old, new in reversed(prev[rel]):
            if t.count(new) != 1:
                raise SystemExit('%s: cannot undo %s (new text found %d times)' % (rel, eid, t.count(new)))
            t = t.replace(new, old)
        if sha(t.encode('utf-8')) != pre_sha:
            raise SystemExit('%s: undo did not reach the pre-fix hash' % rel)
    for eid, old, new in edits:
        n = t.count(old)
        if n != 1:
            raise SystemExit('%s: %s: old text found %d times' % (rel, eid, n))
        t = t.replace(old, new)
        if t.count(new) != 1:
            raise SystemExit('%s: %s: new text found %d times after the edit' % (rel, eid, t.count(new)))
    nb = t.encode('utf-8')
    f0, f1 = form(b), form(nb)
    added_nl = (f1['crlf'] + f1['bare_lf']) - (f0['crlf'] + f0['bare_lf'])
    if f1['bom'] or f1['bare_cr'] != f0['bare_cr'] or (f0['crlf'] and f1['bare_lf'] != f0['bare_lf']) or \
            (not f0['crlf'] and f1['crlf']):
        raise SystemExit('%s: encoding or line endings would change' % rel)
    p.write_bytes(nb)
    return {'pre_sha': pre_sha, 'post_sha': sha(nb), 'pre_bytes': len(b) if sha(b) == pre_sha else None,
            'post_bytes': len(nb), 'lines_added': added_nl, 'edits': [e[0] for e in edits]}


def main():
    pre = json.loads((WORK / 'base_hashes.json').read_text(encoding='utf-8'))
    apath = WORK / 'applied_edits.json'
    prev = {}
    if apath.exists():
        prev = {k: [tuple(x) for x in v] for k, v in json.loads(apath.read_text(encoding='utf-8'))['edits'].items()}
    report = {}
    for rel, edits in E.items():
        report[rel] = apply_file(rel, edits, pre[rel]['base_sha'], prev)
    apath.write_text(json.dumps({'edits': {k: [list(x) for x in v] for k, v in E.items()}, 'result': report},
                                indent=1, ensure_ascii=False), encoding='utf-8')
    for rel, r in report.items():
        print(rel, '| pre', r['pre_sha'][:16], '-> post', r['post_sha'][:16], '| bytes', r['post_bytes'],
              '| lines added', r['lines_added'], '|', len(r['edits']), 'edits')


if __name__ == '__main__':
    main()
