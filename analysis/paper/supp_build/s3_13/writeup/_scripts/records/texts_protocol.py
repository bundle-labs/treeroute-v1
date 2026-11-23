# The text of PROTOCOL.md section 14's entry of 2026-11-17 (records writer, S3.13 write-up). ASCII only; every line
# at most 120 characters; the line @@LATER_READS@@ is the lead's placeholder for the reads of the S1/S4 writer and of
# the checks that follow. Imported by build_records.py.

ENTRY = r'''- 2026-11-17, no method change; sections 3 and 8 are untouched, and nothing that is reported changes: the write-up of
  this analysis in the paper (Supplement S3.13 and the main-text Table 9). This entry, recorded on 2026-11-17, gives
  what the write-up was written from, that no SHAP script ran and no file of this folder changed for it but this file,
  one correction of this protocol's wording, and who read what. Before it is applied, the earlier `PROTOCOL.md`
  (SHA-256 32daa77b893cf7af378b3145a285fa71c0cec61b0b3a51420195415658618abc, the version that the paper's fact sheet
  cites) is saved in `_snapshots/@@SNAP@@/`, beside the write-up's other pre-edit copies in
  `paper/draft/_snapshots/@@SNAP@@/`.
  - What was written, and from what. Supplement S3.13 (Tables S3.18 to S3.30) and the main-text Table 9 (Section 5.4)
    take every number of the comparison from the `compare/` files, from `verify_v1/A/results.json` (the numbers of
    rulings BB1 and BB2, and every B1 number but the B1 runs' background pairs and seconds) and from the B1 runs' log
    lines (those pairs and seconds), through the checked tables `paper/supp_build/s3_13/reconcile/tables_agreed.md`
    (version 5), with `cells.json` beside them giving each printed number's source, selector and stored value. Two
    builders built the tables independently from the stored values, with one rounding step, by one specification
    (`paper/supp_build/s3_13/spec/TABLE_SPEC.md`); a reconciler compared their tables with each other and with the
    printouts, and a checker checked each version. Versions 2 to 5 reworded captions, notes, labels and cells after
    four checks and changed no number. Each prose number of S3.13 and Section 5.4 is formatted once from its stored
    value and carries a fact ID (the paper's facts A9 to A25). Every number stays post hoc and is labelled so.
  - Nothing of this folder ran or changed for the write-up. No script of `scripts/`, `verify_v1/` or
    `verify_v1/_lead/scripts/` was run, and no file of this folder was written but this one, by this entry. For the
    archive plan (`_archive_plan/ARCHIVE_MANIFEST_DRAFT.md`, section 2.5) the folder was listed on 2026-11-17 at 10:34
    by file metadata only (names, sizes and times; `smoke/bardl_fix/` not entered); no file of it was opened for that.
  - A correction of this protocol's wording; the old lines stay as written. Section 5 (lines 375 and 381-382) calls
    coral's B2 background, the visit's saved 50-visit router pool, "other sites' visits" and "a pool of other sites",
    and section 10 ("Not claimed", lines 673-674) repeats "other sites' visits". Some of the pool is at the explained
    visit's own reef site: of the 50,000 background visits of the 1,000 coral sample rows, 980 are earlier visits at
    the explained visit's own reef site, in 415 of the sample rows, and none is dated on or after the explained visit
    (a read-only count of `out/coral/lead_0/treeroute/background_keys.parquet` against its `rows.parquet`, the reef
    site being a key's text before "|": `paper/supp_build/s3_13/_brief/lead_checks/verify_v5_claims_out.txt`, line
    33). The conclusion of sections 5 and 10 stands: there, static and calendar columns are not zero by construction
    and can carry attribution. The paper says "a pool of earlier nearby survey visits".
  - What was read, by each reader's own record. No reader below ran a script of `scripts/`, `verify_v1/` or
    `verify_v1/_lead/scripts/`, changed a file of this folder or opened `smoke/bardl_fix/`.
    - The table rounds, versions 1 to 5 (`paper/supp_build/s3_13/_brief/reads_tables.md`, compiled by the agent from
      each round's records). Version 1's specification writer read the comparison printouts (the ten `AW3_table.md`
      and `AW4_table.md`, for their formats) and `verify_v1/reconcile/report.md` (fourth version: the lead's note,
      sections 1-6, A1-A6 and the first rows of A7), with this file in full and the rulings; one text search with a
      `*.md` pattern over `out/` (for "-0.00") matched nothing and showed no line. The two builders opened neither the
      printouts nor the report, only the specification's sources (the stored values the tables print); builder A's
      exploration script also printed the set-up and "done in" lines of coral's treeroute SHAP log, which were not
      used. The reconciler of each version read the ten printouts and the report's section A6 through its scripts, by
      name. Version 1's checker read the report's sections A4 and A5, and coral's `AW4_table.md` only by its file time.
      The later specification fixers and checkers, and the agent that led the rounds, opened no printout and not the
      report; they read (read only, nothing run) `scripts/tr_rebuild.py`, engine modules and dataset files, the
      re-computation's scripts `verify_v1/A/scripts/a20_b1.py`, `a_core.py` and `a_lib.py`, and
      `verify_v1/_lead/outputs/bardl_maxima.txt` and `bardl_ties.txt`, and, through their scripts, the models'
      `meta.json` and variable maps, the five rebuild `gates.json`, NDVI's `per_lead.json`, `importance.parquet` and
      `families.parquet`, and coral's treeroute `background_keys.parquet` and `rows.parquet` (their schemas, five rows
      of the columns other than the SHAP values, then keys, dates and the saved pools).
    - The write-up's writers before this entry, by the lists of files each returned: the glossary writer read lines
      1-648 of this file; the references writer searched this file and read lines 355-679 and 712-723; the S3.13
      writer read this file in full and, through its scripts, `SAMPLE_REGISTER.txt`, the five `per_lead.json`
      (top-level keys and scalar fields) and the five rebuild `gates.json` (results, pass flags and the E5 and E3a
      values); the main-text writer searched this file's headings and read lines 479-693. This entry's writer read
      most of this file (sections 1 to 4.1, parts of 4.2, 5 and 8, and sections 9 to 14) and `RUN_COMMANDS.md`, and
      made the listing above. None of them opened a comparison printout, `verify_v1/reconcile/report.md`,
      `verify_v1/A/results.json`, a row file or a compare file other than `per_lead.json`; the numbers they wrote come
      from the checked tables, `cells.json` and the record fields named here.
@@LATER_READS@@
  - Every result of this analysis stays post hoc (ruling AK, section 1); nothing in this entry changes that label.
'''
