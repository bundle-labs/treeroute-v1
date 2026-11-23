# Changes: fixer (S3.13 write-up, 2026-11-17)

Names as in the brief: SHAP = the SHAP analysis folder (D:/treeroute/analysis/shap_v1); V = SHAP/verify_v1; ROOT = the
research-paper folder; D = ROOT/paper/draft; OUT = ROOT/paper/supp_build/s3_13; STAGE = OUT/stage. Only staged files
were edited, each from its staged state (the last writer's output; its SHA-256 equals that writer's record, and every
live counterpart still has the writers' start hash). No live file was written, and OUT/reconcile/tables_agreed.md and
cells.json were not changed. Every edit was made by STAGE/_scripts/fix/apply_fix.py as an exact replacement whose old
text occurs once in the file and whose new text then occurs once; a re-run undoes the recorded edits
(work/applied_edits.json, new -> old, in reverse order), checks that the pre-fix SHA-256 is reached, and applies the
list again, so each file can be rebuilt from its pre-fix state. No edit adds or removes a line ending inside the
CRLF files, and no number of a table or a fact changed.

## Files

| Staged file | Pre-fix SHA-256 (bytes) | Post-fix SHA-256 (bytes) | Encoding, line endings | Edits |
|---|---|---|---|---|
| paper/draft/S3_posthoc.md | ea1d808ef8056bfa33901ac396d69a72241b821bff09e3bba7fef5fb70cfe262 (242,797) | 62d66a4fb57fd9ecdfb8b902adc94209a14a87019cdd55826c4c78154ee23779 (244,453) | UTF-8 without BOM, LF only (1,467 lines, unchanged), one final LF | S3-1 to S3-10 |
| paper/draft/S1_disclosures.md | b469b1dc9f883519e946e2a6cc3f9fc031e51254c1d61cb611e41d4b73d2dc25 (165,620) | c0ffa78cb0e826ae2379fe57c82b4d4fcaef741d13d2e2d1bc725088115b10a5 (167,003) | UTF-8 without BOM, LF only (317 lines) | S1-1 to S1-10 |
| paper/draft/S4_provenance.md | 081654fa31b449c28aa4cf1123f7e481bb6f2970a22ddc2bc4c798f6dda8dec0 (207,278) | 3a8cd47136c82bc7562291b1f36a7c7e2b68bdecbda42e6a99741d11f1f776a5 (208,245) | UTF-8 without BOM, CRLF only (735, no bare LF or CR) | S4-1 to S4-8 |
| paper/draft/GLOSSARY.md | edb836a8a8cb11b5c02c0e57fa92742886805c78e86bb26b51a8cf6a28fde3f8 (42,634) | 0ae2edd7f88b344bb81e1991c23dab2a15aa667238938686b1d9f260ed9ef4ad (43,080) | UTF-8 without BOM, CRLF only (140) | G-1 to G-6 |
| paper/draft/REFERENCES.md | b699e55f1e84875e6b80101665ffeefbe855d4495341098b75eb8ff4977864b3 (167,145) | 28bbe54ee1a0dd3b637cf812298961a9bd453d55fb83e41b556a3858c1afe369 (167,526) | UTF-8 without BOM, LF only (321) | R-1 to R-3 |
| paper/PAPER_FACTS.md | ce7a86e64c2b66268c40e78db0a7074bb42dafc71e410729062cc8550395115a (388,038) | f20d4e517d2c94be6ce30d245375572af9ebe0296da3de275b8d1b9a71281967 (389,225) | UTF-8 without BOM, LF only (1,484) | F-1 to F-6 |
| shap/PROTOCOL.md | f59c52b6fe3d396608314f8f4c557bd3347c735ecfa9b778068d06f28b9a56b8 (128,823) | c0779fbc0c58ac4b4c4dec4e3ced8a9b6adbe9cec6727dca4ecff6d33171e303 (129,350) | UTF-8 without BOM, LF only (1,289 lines, 6 more), one final LF; new lines ASCII, at most 120 characters; the live file (32daa77b...) is still a byte prefix; sections 3 (28d54cbd9df9..., 3,767 B) and 8 (4c03d6ed5974..., 5,558 B) byte-identical | P-1, P-2 |
| _archive_plan/ARCHIVE_MANIFEST_DRAFT.md | 98835dfcc69ef8346553000f46d1bae994a79aedcb92cc2a51d46950bd84a49f (193,259) | 9819451c3094397260f955198a957610059ba6733a035d4318b6f02b41b08f22 (195,471) | UTF-8 without BOM, LF only (921 lines, 1 more), one final LF | M-1 to M-8 |

Not changed (no finding needs it): paper/draft/05_rivals.md (74fe3849...), paper/draft/tables/table_9.md (0a5471ff...),
paper/draft/TABLE_NUMBERS.md (9e159fae...), paper/PAPER_OUTLINE.md (7a5a8a2a...) and engine/PENDING_PARTS.md
(1d9e5750...). The placeholders @@SNAP@@ and @@LATER_READS@@ are untouched (same count in every file).

## The lead's list

| Item | Done | Edits |
|---|---|---|
| 1. Table S3.30's last note: "(Tables S3.28 and S3.29)" -> "(Table S3.28 and Table S3.29)" | Yes, in S3_posthoc.md only, recorded as a paper-side wording change of an agreed table note (no number changes); tables_agreed.md v5 is unchanged (its SHA-256 d05a6856... is pinned in facts A27, S1 PH30 and table_9.md's comment) | S3-9; S3-1 (header comment) |
| 2. S3.13 'When and why', ruling AZ1 sentence | Yes, in the lead's words, plus "of four models" (claims finding 1: fire had three comparisons on 2026-11-13, at 18:19 and 18:46 with three models each, and at 21:18 with four; AZ1 is about the 21:18 one; PROTOCOL.md section 14, entry of 2026-11-14) | S3-5 |
| 3. Presentation: "(local time, UTC+1)" after "about 15:31"; note d stays | Yes; the sentence also says "from the comparison reported here" (claims finding 3, ruling BB6's "the current coral comparison's table"); Table S3.22's note d unchanged | S3-10 |
| 4. S3.0 facts comment on Part 628 | Yes: it quotes the staged heading's status words and names the addendum of 2026-11-17 | S3-2 |
| 5. LundbergLee2017_SHAP's Supports note adds Section 5.4 (SHAP values) | Yes (after the Key marker, so not printed) | R-2 |
| 6. GLOSSARY "(named 5.4)" | Checked each new row against the staged 05_rivals.md (5.4's new paragraph names SHAP values, Kendall's W, the main set and same-link rivals before Table 9; it does not name share, variable level, background, importance, family, RBO or consensus). SHAP value and same-link / cross-link: "S3.13 (named Table 9)" -> "S3.13 (named 5.4)". Main set and Kendall's W, whose rows read "Table 9 (Section 5.4)" (the lead's example lists main set): "Table 9 (named 5.4)". Share and the variable level keep "(named Table 9)" | G-1, G-3, G-4, G-5, G-6 |
| 7. S4's archive paths for Part 628's files | Table S4.11 row 628 and Table S4.14's second Part 628 group heading: `paper/supp_build/s3_13/` -> `analysis/paper/supp_build/s3_13/` (manifest 2.5 and section 1). The other visible paths (`analysis/shap_v1/`, `analysis/shap_v1/PROTOCOL.md`, `.../RUN_COMMANDS.md`, `.../SAMPLE_REGISTER.txt`, `.../verify_v1/`) already match the manifest. Comment paths that say where a file was read are project paths and stay | S4-5, S4-7 |
| 8. Pointers to paper/supp_build/s3_13/stage/... -> .../writeup/...; manifest section 8 item | Five pointers in four places: S4 (Table S4.11's comment; Table S4.14's comment, two), REFERENCES.md's history comment (refs_candidates.md) and PAPER_FACTS A27; none is left in the 13 files. The manifest's `stage\` rows (2.5, appendix A, section 7, appendix B) classify the stage folder as left out and stay. Section 8 gains item (e) | S4-6, S4-8, R-1, F-6, M-7 |

## The checkers' findings: decisions

Numbers checker:
- N1 (minor; the table build's listing and scan are stale): verified. My os.stat re-listing (relist_out.py, 10:49:45 UTC)
  gives 226 files, 32,661,794 B for spec, A, B, reconcile, skeptic and _brief: only `_brief/lead_checks/verify_v5_claims.py`
  (3,346 -> 3,271 B, written 10:12:11 UTC) and `verify_v5_claims_out.txt` (2,055 -> 1,971 B, 10:12:15 UTC) differ from
  the records writer's listing of 09:34:21 UTC; the current output prints no survey-visit key. Fixed without changing a
  total: the plan's numbers are correct for the 09:34 listing, whose time it states, and every total, section 0, 1, 2.5,
  7, 7.2 and appendix B, derives from that one listing, so changing some would break their agreement. 2.5 now records the
  two rewritten files, the current byte count (159 B fewer; .py 75 B fewer; no GB, GiB or MB figure changes, recomputed)
  and that packaging re-takes the totals; the "prints two coral survey-visit keys" sentence is replaced by what the
  current output prints; a count-only scan of the two rewritten files (privacy_two.py, 10:50:02 UTC, the records
  writer's patterns) found none of the patterns; notes in the header, 6.5, section 7, 7.2 and appendix B (M-1 to M-5,
  M-8).
- N2 (minor; A16 "stored null"): verified (peek_fire_w.py prints fire's AW4_main_row.json kendall_w entry only:
  `"ci": [NaN, NaN, 0], "value": NaN`; cells.json line 11 stores [null]). Fixed (F-5).
- N3 (minor; the references writer's read ranges in the PROTOCOL entry): not changed. The ranges came from that
  writer's returned list, which the records writer had and I do not; no staged record holds them (changes_refs.md and
  refs_candidates.md say "sections 5 and 8"). Writing the vaguer record could understate what was read. Left for the lead
  to check against the returned list at apply (open point 1).
- N4 (minor; time zone of the BB6 times): fixed in the prose (lead item 3, S3-10); note d unchanged by the lead's ruling.
- N5 (minor; S4.2 includes ruling AX): fixed (S4-2, S4-4).

Claims checker:
- C1 (major; AZ1 overstated in S3.13 and A9; which comparison): fixed (S3-5, F-2); verified against rulings file AZ and
  PROTOCOL.md section 14 (entry of 2026-11-14: the 18:19 and 18:46 comparisons of three models, the 21:18 one of four).
- C2 (major; PROTOCOL entry says results.json gives BB2's numbers; bardl_maxima.txt missing): verified in cells.json
  (Tables S3.23-S3.27 panel b tvd_family: source compare/pairs.parquet, selector level=variable; Table S3.28's
  tv_family_shares from V/A/results.json b1; 8 cells from V/_lead/outputs/bardl_maxima.txt; the samples', checks' and
  gates' cells from SAMPLE_REGISTER.txt, sample_manifest.json, meta.json, exactness records and gates.json). Fixed
  (P-1), with the sources of the sample, check and gate numbers added so that the bullet names every source cells.json
  lists.
- C3 (minor; BB6 identification and zone): prose fixed (S3-10); note d not changed (lead's list).
- C4 (minor; PH22 "was written before any SHAP value"): verified against the protocol's preamble and section 14 (v1,
  v2 and v3 entries). Fixed in PH22 (S1-2, S1-3), and, as the checker suggested, in S3.13 (S3-4); fact A9 gains the v3
  statement (F-3) so the new words have a fact.
- C5 (minor; PH23 garbled): fixed (S1-4), from Table S3.21's E10 row and S3.13's exactness paragraph.
- C6 (minor; PH26 "these entries"): fixed (S1-7).
- C7 (minor; S4.2 re-computation row omits the exceptions): fixed (S4-3; A23 named in S4-4's comment).
- C8 (minor; S4.2 and ruling AX): fixed (S4-2, S4-4).
- C9 (minor; S4 archive path of the builders): fixed (S4-5, S4-7).
- C10 (minor; "archived" results file): fixed in S3.13's B1 paragraph (S3-8) and PH25 with its comment and the S1.7
  comment (S1-5, S1-6, S1-10), with the manifest's archive path (2.5; section 8 (a), updated by M-6). Table S3.29's note
  (agreed text) is not changed: it is not wrong, and the prose carries the archive path.
- C11 (minor; "the owner" in Table S3.18 b and Table S3.20 note c): not changed. Agreed table text and not a clear error
  by the paper's rules: ruling AT20 sets "the author" for S1 and S4, and the visible text of S6, S7, S9 and S10 also says
  "owner ruling" or "the owner" (tmp_owner_words.py). A style choice for the lead (open point 3).
- C12 (minor; 50,000 background pairs, not visits): verified (verify_v5_claims_out.txt line 33; Table S3.19's
  "Background pairs" 50,000; 11,338 training survey visits in gate E4). Fixed in S3.13 (S3-6), PH29 and its comment
  (S1-8, S1-9), the PROTOCOL entry (P-2) and, for consistency, fact A11 (F-4).
- C13 (minor; S3.0 facts comment): fixed (S3-2, lead item 4).

Conventions and build checker:
- B1 (major; bare "S3.29"): fixed (S3-9, lead item 1); the build's expressions (BARE_SUP_RE, SUP_REF_RE, SEC_REF_RE,
  Table S-number check) now find 0 problems in the staged S3, S1, S4, 05_rivals and table_9 (check_fix.py). The lead's
  list keeps the change paper-side, so tables_agreed.md line 785 is not edited.
- B2 (minor; AI terms in two reference titles): not changed; titles are bibliographic data, the build's AI check skips
  reference lists, and the choice is the lead's (open point 4).
- B3 (minor; do-not-use names in S3.13): fixed: "headline runs" -> "runs" (S3-3), "the nowcast boards" -> "the nowcast
  rival boards" (S3-7), "250 coral bleaching rows" -> "survey visits" (S3-4), "in 415 of the 1,000 sample rows" -> "for
  415 of the 1,000 explained survey visits" (S3-6). The optional "the owner" change: not made (C11).
- B4 (minor; S1 PH22 rows, PH29 bare visits): fixed (S1-2, S1-8).
- B5 (minor; GLOSSARY "catalog code"): fixed with S3.13's words (G-2).
- B6 (minor; Webber2010_RBO "(see the table above)"): fixed: the note now says that the build does not resolve
  "Webber, Moffat and Zobel 2010" (changes_refs.md, check_entries.py result) (R-3).
- B7 (minor; S4 archive paths): fixed (S4-5, S4-7).
- B8 (minor; zone of the BB6 times): prose fixed (S3-10); note d unchanged (lead).
- B9 (minor; AZ1 sentence): fixed (S3-5).
- B10 (minor; the build checker's copies under OUT/checks/build hold four figure files with an old user name): outside
  the staged files; nothing deleted (open point 5).
- B11 (minor; pre-existing paths and ids in PENDING_PARTS.md and in the records writer's base copy): nothing for the
  write-up; the manifest's new section 8 item (e) classes the write-up's copied scripts and checks at packaging (open
  point 6).

## Edits

| # | File | Place | What | Why | Source |
|---|---|---|---|---|---|
| S3-1 | S3_posthoc.md | Header comment (line 1), after "One caption was changed ... no table cell changed." | Fix-pass sentence: the Table S3.30 note change and the prose corrections below; facts A9 and A11 corrected with them; no number changed | Edit-history rule; the header had said one caption was changed | this record |
| S3-2 | S3_posthoc.md | S3.0 facts comment (line 37) | "628: 2026-11-12, DRAFT, with its dated addendum of 2026-11-17" -> 628: 2026-11-12, "DRAFT 2026-11-12; RUN 2026-11-12 TO 2026-11-16 AT SCOPE (i), B1 INCLUDED, EVERY PIECE FINISHED, E5 INFORMATIONAL; RE-COMPUTED INDEPENDENTLY 2026-11-16; WRITTEN UP 2026-11-17, SUPPLEMENT S3.13 AND TABLE 9", with its dated addendum of 2026-11-17 | Lead item 4; claims C13 | staged engine/PENDING_PARTS.md line 1500 and line 1553 (the addendum's date) |
| S3-3 | S3_posthoc.md | When and why (line 668) | "treeroute v1's headline runs" -> "treeroute v1's runs" | Conventions B3: "headline run" is a do-not-use name of run | staged GLOSSARY.md, row run |
| S3-4 | S3_posthoc.md | When and why | The protocol's sections on the sample and the statistics were "revised after the first smoke tests because of two design reviews' method findings (not of any value)" before the freeze; "at most 250 coral bleaching rows" -> "survey visits" | Claims C4 (suggested for S3.13 too); conventions B3 | PROTOCOL.md preamble and section 14 (v1, v2, v3 entries); fact A9 (F-3); GLOSSARY row survey visit |
| S3-5 | S3_posthoc.md | When and why | "...we recorded that the burned-fraction comparison written on 2026-11-13, before Ridge was added, had not been read (ruling AZ1)." -> "...we recorded that we had not opened the burned-fraction comparison of four models written on 2026-11-13, before Ridge was added (ruling AZ1; its layout was opened, as Supplement S1.7 records)."; comment cites AZ1's words, PH28 and A26 (a) | Lead item 2; claims C1 ("four models": three fire comparisons that day); conventions B9 | rulings file AZ (heading, AZ1); PROTOCOL.md section 14, entry of 2026-11-14; S1 PH28; facts A9, A26 (a) |
| S3-6 | S3_posthoc.md | Method (line 670) | "(of the 50,000, 980 are at the explained survey visit's own reef site, in 415 of the 1,000 sample rows, and none is dated on or after the explained survey visit)" -> "(of the 50,000 background pairs, 980 pair an explained survey visit with an earlier survey visit at its own reef site, for 415 of the 1,000 explained survey visits, and in none is the background survey visit dated on or after the explained one)" | Claims C12; conventions B3 | OUT/_brief/lead_checks/verify_v5_claims_out.txt line 33; Table S3.19; fact A11 |
| S3-7 | S3_posthoc.md | Models explained (line 682) | "the nowcast boards" -> "the nowcast rival boards" | Conventions B3: "board" is a do-not-use name of rival board | GLOSSARY row rival board |
| S3-8 | S3_posthoc.md | B1 paragraph (line 1337) and its comment | "(verify_v1/A/results.json, key b1)" -> ", archived as analysis/shap_v1/verify_v1/A/results.json (key b1)"; comment names the manifest | Claims C10; brief item 1 ("the archived results file") | staged manifest 2.5 and section 8 (a) |
| S3-9 | S3_posthoc.md | Table S3.30, last note (line 1455) | "(Tables S3.28 and S3.29)" -> "(Table S3.28 and Table S3.29)": a paper-side wording change of an agreed table note; no number changes | Lead item 1; conventions B1 (major): the build's BARE_SUP_RE reads the bare "S3.29" as a supplement heading, which blocks a final build | ROOT/paper/build/build_docx.py lines 1457-1458 |
| S3-10 | S3_posthoc.md | Presentation (line 1461) and its comment | "Coral bleaching's table of the main-text statistics, from the comparison reported here (`AW4_table.md`, written on 2026-11-13 at 00:06), was read on 2026-11-13 at about 15:31 (local time, UTC+1), ..."; comment adds A28 | Lead item 3; numbers N4; claims C3; conventions B8 | ruling BB6 ("the current coral comparison's table"); facts A25, A28 |
| S1-1 | S1_disclosures.md | Header comment (line 1), after the write-up's entry | Fix-pass sentence naming S1-2 to S1-10 | Edit-history rule | this record |
| S1-2 | S1_disclosures.md | PH22 (line 245) | "was written" -> "was first written (version 1)"; the sample and statistics sections "were revised after the first smoke tests (version 3), because of two design reviews' method findings, not of any value, and were frozen ..."; "250 coral bleaching rows" -> "survey visits" | Claims C4; conventions B4 | PROTOCOL.md preamble and section 14 (v1, v3 entries); fact A9 (F-3) |
| S1-3 | S1_disclosures.md | PH22's comment | A9's v3 change of sections 3 and 8 added to the list of what A9 gives | Source comment for S1-2 | as S1-2 |
| S1-4 | S1_disclosures.md | PH23 (line 246) | The E3a and E10 sentence split in two: E10 on one sampled location's router fit rows and test rows on PM2.5, NDVI and burned fraction, one survey visit's on coral bleaching, every sampled location on forest loss | Claims C5 | Table S3.21 row E10; S3.13's exactness paragraph; fact A12 |
| S1-5 | S1_disclosures.md | PH25 (line 248) | "...through the re-computation's results file" + ", archived as analysis/shap_v1/verify_v1/A/results.json (key b1)" | Claims C10 | staged manifest 2.5 and section 8 (a) |
| S1-6 | S1_disclosures.md | PH25's comment | The note that the row avoids "archived" replaced by the archive path's source and the old wording | Comment follows S1-5 | as S1-5 |
| S1-7 | S1_disclosures.md | PH26 (line 249) | "By ruling BB1 these entries come from" -> "By ruling BB1 the entries of the first two come from" | Claims C6: the third departure is filled by BB2 from the variable-level value, not from the re-computation | PROTOCOL.md section 9 (BB2); cells.json (Tables S3.23-S3.27 panel b tvd_family from pairs.parquet, level=variable); fact A23 |
| S1-8 | S1_disclosures.md | PH29 (line 252) | "of its 50,000 background survey visits (50 per explained survey visit), 980 are earlier visits ..." -> "of its 50,000 background pairs (50 background survey visits for each explained survey visit), 980 pair an explained survey visit with an earlier survey visit at its own reef site (for 415 of the 1,000 explained survey visits), and in none is the background survey visit dated on or after the explained one" | Claims C12; conventions B4 | verify_v5_claims_out.txt line 33; fact A11 |
| S1-9 | S1_disclosures.md | PH29's comment | "980 of 50,000" -> "980 of the 50,000 background pairs" | Comment follows S1-8 | as S1-8 |
| S1-10 | S1_disclosures.md | S1.7 comment after the table | PH25 gives the results file "with its archive path" | Comment follows S1-5 | - |
| S4-1 | S4_provenance.md | Header comment (line 1), after the write-up's entry | Fix-pass sentence naming S4-2 to S4-8 | Edit-history rule | this record |
| S4-2 | S4_provenance.md | S4.2 opening paragraph (line 31) and its comment | "The rows from 2026-11-12 on, except ruling AX (the GPCC download, in the row of 2026-11-13), are the post hoc SHAP comparison ..."; comment names section AX | Numbers N5; claims C8 | rulings file section AX (AX1, the GPCC download) |
| S4-3 | S4_provenance.md | S4.2 row "2026-11-16 16:09 to about 18:20" | "agrees within 10⁻⁹" + ", except in three explained cases" | Claims C7 | fact A23; PROTOCOL.md section 14, entry of 2026-11-16; S3.13 |
| S4-4 | S4_provenance.md | The comment after the S4.2 table | The ten rows are the SHAP comparison "except ruling AX (the GPCC download, AX1), which shares the row of 2026-11-13 with ruling AY"; A23 named for the three cases | Numbers N5; claims C7, C8 | as S4-2, S4-3 |
| S4-5 | S4_provenance.md | Table S4.11, row 628 | `paper/supp_build/s3_13/` -> `analysis/paper/supp_build/s3_13/` | Lead item 7; claims C9; conventions B7 | staged manifest 2.5 (line 173) and section 1 |
| S4-6 | S4_provenance.md | Table S4.11's comment | hash_files.py's path: .../stage/_scripts/... -> .../writeup/_scripts/... | Lead item 8 | lead's list (the lead copies STAGE/_scripts/ to OUT/writeup/) |
| S4-7 | S4_provenance.md | Table S4.14, the builders' group heading | `paper/supp_build/s3_13/` -> `analysis/paper/supp_build/s3_13/` | Lead item 7; claims C9; conventions B7 | as S4-5 |
| S4-8 | S4_provenance.md | Table S4.14's comment | hash_files.py's and count_s414.py's paths -> .../writeup/_scripts/s1s4/ | Lead item 8 | as S4-6 |
| G-1 | GLOSSARY.md | Row SHAP value, First defined | "S3.13 (named Table 9)" -> "S3.13 (named 5.4)" | Lead item 6: 5.4's paragraph names "the SHAP values" before Table 9 | staged 05_rivals.md line 47 |
| G-2 | GLOSSARY.md | Row player, definition | "and catalog code are stripped" -> "and their numbered code prefix (such as V02_) are stripped" | Conventions B5: "catalog" is a do-not-use name of dataset package | S3.13 line 674; GLOSSARY row dataset package |
| G-3 | GLOSSARY.md | Row main set, First defined | "Table 9 (Section 5.4)" -> "Table 9 (named 5.4)" | Lead item 6 (its example): 5.4 names "the main set's full rankings" before Table 9 defines the main set | staged 05_rivals.md line 47; Table 9 caption |
| G-4 | GLOSSARY.md | Row same-link / cross-link, First defined | "S3.13 (named Table 9)" -> "S3.13 (named 5.4)" | Lead item 6: 5.4 names "its same-link rivals" | staged 05_rivals.md line 47 |
| G-5 | GLOSSARY.md | Row Kendall's W, First defined | "Table 9 (Section 5.4)" -> "Table 9 (named 5.4)" | Lead item 6: 5.4 names "Kendall's W of the main set's full rankings" before Table 9 | staged 05_rivals.md line 47 |
| G-6 | GLOSSARY.md | The write-up's history comment (line 140) | Fix-pass sentence for G-1 to G-5 | Edit-history rule | this record |
| R-1 | REFERENCES.md | History comment (line 3) | refs_candidates.md's path -> paper/supp_build/s3_13/writeup/refs_candidates.md; fix-pass sentence for R-2 and R-3 (after the Key marker; no printed text changed) | Lead item 8; edit-history rule | lead's list |
| R-2 | REFERENCES.md | LundbergLee2017_SHAP, Supports | "(Supplement S3.13, method paragraph; Table S3.18 a)" -> "(Section 5.4, SHAP values; Supplement S3.13, method paragraph; Table S3.18 a)" | Lead item 5 | staged 05_rivals.md line 47 |
| R-3 | REFERENCES.md | Webber2010_RBO, note | "Cite it as "Webber et al. 2010" (see the table above)." -> "Cite it as "Webber et al. 2010": the build does not resolve "Webber, Moffat and Zobel 2010"." | Conventions B6: no table stands above the entry | changes_refs.md (check_entries.py: that in-text form would stop the build) |
| F-1 | PAPER_FACTS.md | "Revised 2026-11-17 (S3.13 write-up)" paragraph (line 19) | Fix-pass sentence for F-2 to F-6, before the snapshot sentence | Edit-history rule | this record |
| F-2 | PAPER_FACTS.md | A9, ruling AZ1 | "the burned-fraction comparison of 2026-11-13 21:18 (four models, without Ridge) had not been read before Ridge was added" -> "the author had not opened [it] before Ridge was added (the author's answer); it had been opened once, by an agent, for its layout only (A26 (a))" | Claims C1 | rulings file AZ1; fact A26 (a) |
| F-3 | PAPER_FACTS.md | A9, protocol | Adds: version 3 (2026-11-12, before any registration) changed sections 3 and 8 after the smokes, because two design reviewers had found that the code and the text disagreed and that several statistics were biased; every change answers a method finding, not a value | Claims C4: the fact for S3-4, S1-2 | PROTOCOL.md preamble (lines 3-7) and section 14 (v3 entry, lines 780-782) |
| F-4 | PAPER_FACTS.md | A11 | "Of the 50,000, 980 are earlier visits at ..." -> "Of the 50,000 pairs, 980 pair the explained visit with an earlier visit at its own reef site, ... and in none is the background visit dated on or after the explained visit", with line 33 quoted | Claims C12, for the fact behind S3-6, S1-8 and P-2 | verify_v5_claims_out.txt line 33 (current file) |
| F-5 | PAPER_FACTS.md | A16, burned fraction | "stored null" -> "stored NaN, with 0 finite draws, which cells.json writes as null" | Numbers N2 | SHAP/out/fire/lead_0/compare/AW4_main_row.json kendall_w (read by peek_fire_w.py); cells.json line 11 entry |
| F-6 | PAPER_FACTS.md | A27 | hash_files.py's path -> .../writeup/_scripts/s1s4/hash_files.py | Lead item 8 | lead's list |
| P-1 | shap/PROTOCOL.md | Entry of 2026-11-17, bullet "What was written, and from what" (reflowed, lines 1232-1246) | results.json gives "the numbers of ruling BB1, and every B1 number but the B1 runs' background pairs and seconds"; adds bardl_maxima.txt (the spreads of ruling BB3's footnote); "by ruling BB2 the feature-level family-share distance repeats the variable-level value (from the compare/ files, and for B1 from results.json)"; adds the sources of the samples', checks' and gates' numbers (SAMPLE_REGISTER.txt, the sample manifests, the pieces' meta.json and exactness records, the rebuild gates.json); the rest unchanged | Claims C2 (major) | cells.json sources and selectors (counted by source); Table S3.24's source comment; PROTOCOL.md section 9 |
| P-2 | shap/PROTOCOL.md | Entry of 2026-11-17, the wording-correction bullet (reflowed) | "of the 50,000 background visits ..., 980 are earlier visits at ..." -> "of the 50,000 background pairs of the 1,000 coral sample rows (50 per row), 980 pair the explained visit with an earlier visit at its own reef site, in 415 of the sample rows, and in none is the background visit dated on or after the explained visit" | Claims C12 | verify_v5_claims_out.txt line 33 |
| M-1 | ARCHIVE_MANIFEST_DRAFT.md | Header, "Measured" bullet (line 5) | The fix pass's re-listing (10:49:45 UTC) and count-only scan (10:50:02 UTC) | Numbers N1: every measurement with its time | relist_out.py; privacy_two.py |
| M-2 | ARCHIVE_MANIFEST_DRAFT.md | 2.5, the table build's bullet (line 189) | The sentence "...prints two coral survey-visit keys (...)" replaced: the two files rewritten after the listing and scan (10:12:11, 10:12:15 UTC; 3,346 -> 3,271 B and 2,055 -> 1,971 B); what the current output prints (no survey-visit key); the re-listing (32,661,794 B, 159 B fewer; .py 75 B fewer; no GB, GiB or MB figure changes); the totals stay those of the 09:34 listing and are re-taken at packaging; the re-scan found none of the patterns | Numbers N1 | relist_out.py (work/relist_out.json); verify_v5_claims_out.txt (read); privacy_two.py output; roundings recomputed |
| M-3 | ARCHIVE_MANIFEST_DRAFT.md | 6.5, the write-up's note (line 703) | Adds the re-scan of the two rewritten files | Numbers N1 | privacy_two.py |
| M-4 | ARCHIVE_MANIFEST_DRAFT.md | Section 7, "Changes since the fourth revision's listing" (line 720) | Adds that with the two files' current sizes each total that holds the table build is 159 B smaller, no GB or GiB figure changing | Numbers N1 | as M-2 |
| M-5 | ARCHIVE_MANIFEST_DRAFT.md | 7.2, the write-up's bullet (line 782) | ".py files they add (4,131,267 B)" -> "(4,131,267 B when listed; 4,131,192 B since the lead's check script was rewritten, 2.5)" | Numbers N1 | relist_out.py (.py bytes of OUT 2,074,548 -> 2,074,473) |
| M-6 | ARCHIVE_MANIFEST_DRAFT.md | Section 8, write-up item (a) (line 828) | "does not yet call it archived" -> S3.13 now calls it archived, with the plan's archive path, as S1 PH25 does; the file must stay in the archive | Follows S3-8, S1-5 | this record |
| M-7 | ARCHIVE_MANIFEST_DRAFT.md | Section 8, write-up item, new (e) | `ROOT\paper\supp_build\s3_13\writeup\` (the write-up's scripts and change records, which the lead copies from `stage\` at apply) and the write-up's `checks\` folders were written after the listing of 2.5, are not among its 226 files, and are listed and classed at packaging | Lead item 8 | lead's list |
| M-8 | ARCHIVE_MANIFEST_DRAFT.md | Appendix B, the write-up's entry (last line) | New bullet for the fix pass (M-1 to M-7) | The plan's change record | this record |

## Checks run (read only; results on screen)

- check_fix.py (final run, all passed): for each edited file the recorded edits undo to the pre-fix SHA-256; no BOM,
  valid UTF-8, one final newline; the CRLF files gained no bare LF or CR, the LF files no CR; @@SNAP@@ and @@LATER_READS@@
  counts unchanged; every HTML comment closed, none nested, none holding "--" (whole files); PROTOCOL.md: the live file
  is a byte prefix of the staged one, every line after it ASCII and at most 120 characters (longest 120), sections 3 and
  8 byte-identical; the build's cross-reference expressions (build_docx.py lines 1455-1458 and 1494) over the visible
  text of the staged S3, S1, S4, 05_rivals and table_9, against the supplement headings and table captions of D/S*.md and
  D/tables/table_S*.md and the manuscript headings (staged copies in place of live ones): 0 problems; the build's
  AI_STRONG and AI_WEAK (lines 1506-1507) over the visible text of the staged S3, 05_rivals, table_9 and GLOSSARY: 0; no
  drive-letter path in the visible text of S3, S1, S4, GLOSSARY, 05_rivals or table_9; no privacy pattern in any new
  text; no pointer to the stage folder left in the 13 files; S4's visible Part 628 paths are `analysis/shap_v1/...` and
  `analysis/paper/supp_build/s3_13/`. A scan of each edit's new visible text against the staged glossary's do-not-use
  names (the lead's gloss_scan.py rule, plus plurals) finds only parts of paper terms (survey visit), the generic
  "model" and a table "row"; an "in answer to" was reworded ("because of") to keep "answer" out.
- The build's year-token expression (build_docx.py line 534) matches no new token in the edited visible text (dates are
  ISO dates, which it skips), so no new citation is parsed.
- relist_out.py, privacy_two.py and peek_fire_w.py as described under N1 and N2; privacy_two.py also scanned this
  fixer's own outputs: no pattern in any of them.
- tmp_owner_words.py: visible "owner" uses across D/*.md and D/tables/*.md (staged copies where present), for C11;
  tmp_archive_words.py: visible "archive" wording in the staged S3 and S1, for S3-8.
- The paper build was not run: a build needs a copy of the paper's inputs, and this pass may write only in
  STAGE/_scripts/fix/ (open point 2).

## Scripts (STAGE/_scripts/fix/, each run as `py -3.9 -I -B <script>`)

fix_lib.py (paths derived at run time; forms; comment stripping), save_base_and_diff.py (run once before the first edit:
pre-fix hashes in work/base_hashes.json; its byte copies and diffs were removed after the fix, because three of the
staged files hold pre-existing ids in old text and apply_fix.py needs no copy), apply_fix.py (every edit; record in
work/applied_edits.json), check_fix.py (the checks; work/fixdiff_<file>.txt, the changed lines pre-fix -> post-fix),
relist_out.py (work/relist_out.json), privacy_two.py, scan_base.py, peek_fire_w.py, and in work/ the small views
show_edits.py, show_lines.py, tmp_owner_words.py and tmp_archive_words.py. No script of SHAP/scripts, V,
V/_lead/scripts or ROOT/engine was run, and no other writer's script was run.

## Opened outside OUT/_brief, OUT/reconcile and STAGE

- Live files, read only (hashed and diffed by save_base_and_diff.py; S3_posthoc.md, S1, S4, GLOSSARY.md, REFERENCES.md,
  05_rivals.md and TABLE_NUMBERS.md of D; ROOT/paper/PAPER_FACTS.md; ROOT/paper/PAPER_OUTLINE.md;
  ROOT/engine/PENDING_PARTS.md; ROOT/_archive_plan/ARCHIVE_MANIFEST_DRAFT.md; SHAP/PROTOCOL.md, also read by
  check_fix.py for the prefix check).
- ROOT/engine/OWNER_RULINGS_2026-10-06.md: headings searched; sections AW-BB (lines 395-455) read.
- ROOT/paper/build/build_docx.py: searched; lines 1440-1535 read (the expressions copied into check_fix.py); not run.
- SHAP/out/fire/lead_0/compare/AW4_main_row.json: by peek_fire_w.py, which printed only its kendall_w entry.
- Every D/*.md and D/tables/*.md (staged copies where present), read by tmp_owner_words.py and check_fix.py for
  "owner", headings and table captions.
- OUT/spec, OUT/A, OUT/B and OUT/skeptic: names, sizes and times only (os.stat, relist_out.py).
- Not opened: SHAP/smoke/bardl_fix/, AW3_table.md, AW4_table.md, V/reconcile/report.md, V/A/results.json, OUT/checks/;
  no Grep or Glob ran over SHAP or V.

## Open points for the lead

1. PROTOCOL.md entry, "The write-up's writers before this entry": the references writer's ranges (lines 355-679 and
   712-723) are in no staged record; check them against that writer's returned list at apply, or write "searched this
   file and read its sections 5 and 8" (numbers N3).
2. The REVIEW build was not re-run after the fix; check_fix.py replays its cross-reference, AI-term and year-token
   expressions only. A rebuild of a copy should give "Cross-references: none dangling".
3. "the owner" in Table S3.18 b and Table S3.20 note c (agreed text) is unchanged (claims C11); S6, S7, S9 and S10 use
   "owner ruling" too.
4. Janzing2020_interventional and Lundberg2020_TreeSHAP carry "explainable AI" and "Artificial Intelligence" in their
   titles and venues (conventions B2): keep (bibliographic data) or drop both and cite Lundberg and Lee 2017 alone.
5. OUT/checks/build/copy and copy_live hold byte copies of four live figure files with an old user name (conventions
   B10); delete or keep them out at packaging.
6. When STAGE/_scripts/ is copied to OUT/writeup/, the records writer's work/base/ copy of PENDING_PARTS.md (and the
   s1s4 and s3 writers' base copies) come with it; PENDING_PARTS.md holds pre-existing user-folder paths and workflow
   ids (conventions B11). Manifest section 8 (e) classes the folder at packaging.
7. REFERENCES.md's comment now points to paper/supp_build/s3_13/writeup/refs_candidates.md: copy STAGE/refs_candidates.md
   to OUT/writeup/ too (the lead's list names only STAGE/_scripts/ and STAGE/changes_*.md).
8. The manifest keeps the totals of the 09:34 listing, with the two rewritten files recorded in 2.5 (32,661,794 B now,
   159 B fewer); if the lead prefers current totals, subtract 159 B from 32,661,953, 112,610,764, 98,639,502,
   594,527,726, 108,916,833, 4,675,415,873, 217,205,351 and 5,331,402,235, and 75 B from 4,131,267 (no rounding
   changes).
9. The lead fills @@LATER_READS@@ from the later readers' lists; this pass's reads are listed above.
