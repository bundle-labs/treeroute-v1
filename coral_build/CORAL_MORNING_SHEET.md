# Coral: owner sheet (2026-10-20, after ruling W)

DRAFT by an agent. Nothing here is signed. Full detail and paths: PREREGISTRATION_DRAFT_coral.md (updated today,
see its last change note). Log: engine\PENDING_PARTS.md Part 595.

## A. Done since the last sheet

- **You chose V6 (b)** (ruling W, OWNER_RULINGS_2026-10-06.md:116-121). The 46 groups with no test rows now train as
  donor-only groups. Nothing is scored for them. Scored: the same 2,312 test surveys in 37 groups. As W1 says
  (:120): a donor-only group is read from the train/test marks, never from a list or a name; split.yaml excludes only
  the 11 V5 groups; and this departs from ruling D ("every group is trained and tested") for table packages only,
  disclosed.
- **The (b) engine is installed in LIVE** (06:44). Engine hash 930d961c. Old files kept in
  engine\_moved_coral_20261020_064437. Before the install it passed the full suite (3,500 passed; only the 33 old
  failures) and the grid no-op proof: the old and new smokes of the four grid problems, run once at 02:17, before
  your instruction, were identical. Since your words (W2), nothing on the grid has been re-run, and no grid headline
  run was ever repeated.
- **Package switched to (b).** Split check PASS: 83 groups (37 scored + 46 donor-only), 11,338 training and 2,312
  test surveys.
- **Deep check GREEN** (D:\treeroute\runs\coral_draft\check\check_deep_cda2b2b66401.json (re-run 2026-10-20 after one disclosure-text fix; the earlier check_deep_04b9aab0fb5a.json was also green)). Router: neighbour. Test
  years: 2016-2019. One flag: target facts not signed.
- **Small run on full data: plumbing OK** (0.3 min). Every borrowing pool held 50 surveys, with no fallbacks. Only
  the pool records and row counts were read, never a score.
- **Report-only scripts written and tested** on synthetic toy runs only (D:\treeroute\coral_build\report_scripts).
  They refuse any run that is not a headline run, so no smoke score can be read through them. Hash recorded in
  PREREGISTRATION_DRAFT_coral.md section 6.2.
- **Signing tool ready, not run** (D:\treeroute\coral_build\tools\make_signed_coral.py, MAKE_SIGNED_CORAL.md). It
  makes the signed package `coral` from one answers file. Its dry run shows every change; nothing is written until
  you run it with `--apply` and the fingerprint of the dry run you read.
- **Disclosed:** the small run opened the test labels of 42 surveys (3 groups). No score was read. Earlier
  exposures: the tiny smoke's test MAE was in view when V1 was chosen. The (a) smoke opened 79 test labels, and its
  log's test line was seen. See PREREGISTRATION_DRAFT_coral.md section 4.4 and Appendix B.

## B. Decisions still needed

1. **matrix_dir:** add it to the approved inputs of weight_model_for_cut? **Recommend: approve.** It came with your
   RAM-saving ruling R. It is the cause of one old failing test. Approving means adding matrix_dir to
   ADDED["weight_model_for_cut"] at engine\tests\test_layer_shapes.py:57 (or to the matching file in
   treeroute\_proposed). Neither is inside the engine code hash (fingerprint.py:138-145 hashes treeroute\*.py and
   leaves out _proposed), so the engine hash and the checks do not change.
2. **continuity_groups for coral:** **Recommend `[]` (empty).** No old coral number can be compared, because of the
   old pool leak (Part 458). The report refuses a package with no entry. Editing this file shows as expected drift on
   the four grid locks.
3. **Protected root:** confirm `D:/treeroute/coral_build/coral_store` (D:/treeroute/registry/protected_roots.txt
   line 8). The session added it, not you. **Recommend: confirm.**
4. **Flattening-guard edge** (report only, never a choice): which "severe" edge is the primary one? (a) q75 of all
   donor-row labels, as the draft words it (the script's default); (b) q75 of the positive donor-row labels (the top
   magnitude bin's edge). With many zero labels, (a) is low, so its "severe" rows are not very severe. Both are
   printed either way. No recommendation. If (b), the script is changed and re-hashed before the freeze.

## C. Signatures needed

All of C1-C4 go into ONE answers file (copy tools\coral_signoff_answers_TEMPLATE.yaml). The signing tool writes them
into the new package `coral`; `coral_draft` is never edited. Line numbers below are those of
`engine\datasets\coral_draft` today.

1. **Target facts:** catalog.yaml lines 41-52 (pct_bleached; today "unverified", line 11). The freeze's G-FACTS
   check needs "verified". The tool signs them in catalog.yaml itself. Do not use coral_tables\columns.py and
   make_draft.py for this: make_draft.py rewrites both catalog.yaml and ban.yaml, so running it after signing loses
   the signatures. The signed package's texts say so.
2. **Ban verdicts:** the 76 verdicts and the header at ban.yaml lines 1-4. Also settle the "(owner item)" note at
   ban.yaml line 40 (MMM as router context) and answer coral Q9, Q10, Q22 (CORAL_ENGINE_PLAN.md lines 254-255, 267).
   If you answer Q9, Q10 or Q22 other than "confirm", write the verdict changes too, or say in the file that the
   drafted verdicts stand (the tool refuses otherwise).
3. **Exception owner fields:** exceptions.yaml lines 14, 20, 26, 32, 38, 45, 51, 69, 75, 82, 89, 95, 107, 113.
4. **Audit checklist:** AUDIT_CHECKLIST.md section A (rows at lines 11-20) and section B, then the signature at line
   54. The tool adds the full-build evidence next to the tiny-build line (line 43); you approve that line.
5. **Feature-timing statement (U2):** PREREGISTRATION_DRAFT_coral.md line 957 (text in section 3.2, line 162).
6. **Coral question sheet:** confirm the status table, PREREGISTRATION_DRAFT_coral.md line 881 (section 12 item 7).
7. **The pre-registration itself:** sign the filled copy the freeze writes (registry\freeze\PREREGISTRATION_<time>.md).
   Its blank is at PREREGISTRATION_DRAFT_coral.md line 968. Signing it also accepts: the unsigned drafted defaults
   N3-N16 and P2-P26 (section 10); the two accepted-departure texts that still say "await an owner signature" and
   "await the owner" (table_run.py:63, :72; section 10); and the C11 pool sizes that the engine does not flag as
   test-exposed (Appendix B).

## D. What happens after

1. **Make the signed package `coral`,** in this order:
   - (a) I run the tool's dry run on your filled answers file. You read it: every reworded text, the full-build line,
     the verdicts. The reworded texts are all the package lines that still say DRAFT, "not signed", "awaiting the
     owner" or "V6 (b) option", and the stale ones: split.yaml lines 1-2 and 5; exceptions.yaml lines 3-6, 125, 126;
     AUDIT_CHECKLIST.md lines 3 and 15; ingest\README.md lines 1, 5, 8-9, 28, 29, 35-44, 62, 82, 86, 126; the
     dataset.yaml name, version, owner, description and header (lines 1-4, 11-12, 17-20); the catalog.yaml and
     ban.yaml headers. You never sign a text that still says DRAFT: the tool refuses one.
   - (b) You sign C1-C4 in the answers file.
   - (c) `--apply` with the dry run's fingerprint writes `coral`: texts reworded, DRAFT stamps and name replaced, your
     signatures written, all at once. Nothing else.
   - The signed split check is the (b) file D:\treeroute\coral_build_v6b\coral_tables\make_split.py (SHA-256
     a69e1c8c...). The file of the same name in coral_build\coral_tables is the pre-(b) version (c38d76b1...) and
     checks V6 (a); the signed package's README points at the right one.
2. **Outside the package, before the freeze:** the continuity_groups.yaml entry (B2; this moves the report-tooling
   hash, so it must come before the freeze) and matrix_dir (B1).
3. **Checks:** quick (not yet run under (b)) and deep, on `coral`. Every package edit changes the fingerprint, so
   checks come after the last edit.
4. **Plan:** `py -3.9 -m treeroute plan datasets/coral`, run alone.
5. **Freeze.** You sign the filled copy. `freeze verify` on the four grid locks will list engine and report drift.
   That is expected and disclosed.
6. **Headline run.** **Estimate only, not measured: about 2 to 6 hours** (83 groups of 100 trees each, about 11,300
   training surveys). Engine memory for the full run is not measured yet; the 1.4 GB peak was the table builder, not
   the engine.
