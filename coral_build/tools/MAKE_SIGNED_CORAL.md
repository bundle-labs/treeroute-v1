# make_signed_coral.py: the signing step for coral (prepared, NOT run)

Written 2026-10-20 by an agent; fixed the same day after a skeptic review. Nothing here is signed. `datasets/coral`
does not exist yet.

## What it does

It makes the signed package `engine/datasets/coral` from `engine/datasets/coral_draft`. The grid packages went the
other way: the real package came first, and `datasets/_tools/refresh_drafts.py` made each draft from it (name
`_draft`, version `-draft`, owner `UNSIGNED -- DRAFT ...`, a `DRAFT --` stamp). Then `apply_signoff.py` wrote the
owner's answers into the real packages. This tool does both steps for coral, in reverse, from one answers file.
The rewording and the signatures happen in one step: you read the reworded texts in the dry run, and the package is
written only with exactly that text (see `--expect-fingerprint`). You never sign a file that still says DRAFT: the
stale-text scan refuses it.

What changes:
- **dataset.yaml**: name `coral`, plus your version, owner text and description. The `DRAFT --` stamp is removed.
  The engine reads a draft from that stamp (`treeroute/pipeline/draft.py:51-57`).
- **catalog.yaml**: the target's facts are signed here, directly (`fact_status`, `reviewed_by: owner`, `date`), with
  the ruling added to the provenance. columns.py and make_draft.py are NOT used: make_draft.py rewrites catalog.yaml
  and ban.yaml, so running it after signing would lose the signatures. Text edits C1 and R8 say so in the package.
- **ban.yaml**: all 76 verdicts are signed, or changed where you say so. The `(owner item)` note on ctx_mmm is
  settled (accepted, or replaced by your changed verdict), because the freeze's F-BAN-OPEN scan matches it
  (`treeroute_report/freeze.py:127-134`). Each `unsigned (Q22)` phrase is closed, also on a verdict you change. The
  Counts line is recomputed.
- **exceptions.yaml**: `UNSIGNED -- basis: X` becomes `owner -- signed by the owner <date> (ruling ...); basis: X`.
  This is the grid spelling (`datasets/defo/exceptions.yaml:33`).
- **AUDIT_CHECKLIST.md**: the 10 boxes are ticked, the full-build line is added to section B, and the U2 signature
  line is written.
- **The stale prose in all 7 files** (DRAFT / UNSIGNED / "V6 (b) option", the old make_split.py path, the old
  TABLE_DEPARTURES citation, the "listed in verdict.json" list, the "LIVE refuses it" line) is replaced by 28 text
  edits. The agent wrote them. You approve them as one block.

It refuses, and writes nothing, while any answer is blank. It lists every missing item.

## Commands

```
py -3.9 -B D:/treeroute/coral_build/tools/make_signed_coral.py sign <your filled copy>          # dry run (default)
py -3.9 -B D:/treeroute/coral_build/tools/make_signed_coral.py sign <your filled copy> --apply --expect-fingerprint <fp>
```

`<fp>` is the "predicted fingerprint" line of the dry run you read (the dry run's last line prints the whole
command). `--apply` refuses without it, and refuses when the plan it rebuilds has another fingerprint: then the
answers file or coral_draft changed since you read the dry run.

The dry run validates each new file with the engine's own rules: the schema, the draft stamp, F-BAN-OPEN,
`exception_signed`, and a scan for stale text. It also predicts the new package fingerprint.

Before `--apply` writes anything, it checks these and refuses if any fails:
- `--expect-fingerprint` is given and equals the plan's fingerprint;
- the answers file is not in `tools/_dryrun`; ruling.id, signer and dataset.owner do not say DUMMY; ruling.date is
  not after today (the dummy file uses 2099-01-01);
- the cited ruling section (`## <id>.`) is in the rulings file;
- `datasets/coral` does not exist yet;
- coral_draft still has fingerprint 04b9aab0..., which is the GREEN deep check;
- no target lies under a protected root (the protected-roots file must exist).

It then writes into a new `datasets/_staging_coral_<stamp>/` folder and loads that folder with the engine. If the
load passes, it renames the folder to `datasets/coral`. If anything fails, the folder is renamed to
`_moved_signed_coral_<stamp>`. Nothing is deleted. A record goes to `tools/signoff_records/`.

## What the owner must fill (TEMPLATE: coral_signoff_answers_TEMPLATE.yaml)

1. `ruling` id, file and date. Write the ruling section in OWNER_RULINGS first. Also fill `signer`.
2. `v6_choice: b`, which confirms ruling W1. `protected_root_confirm` (yes/no). `matrix_dir` (approve/reject).
   `continuity_groups` (empty, or a list).
3. `dataset`: version, owner, and description (`proposed`, or your own text).
4. `target_facts.fact_status`: verified or assumed. **ATTENTION:** a table package passes G-FACTS only on
   `verified` (`treeroute/check/table.py:131-136`).
5. `ban`: set `all` to `sign_all` or `per_column`. Answer `owner_item_ctx_mmm` (accept/change; with change, also
   answer `ban.verdicts.ctx_mmm: change` and write the new verdict, reason and note under `ban.changes.ctx_mmm`; the
   new reason must not keep "(owner item)"). Add other per-column changes if you want any.
6. `exceptions`: 19 entries, each `sign` or `keep`. `keep` is allowed only where the owner field already names a
   ruling: entries 7, 8, 15, 17 and 18.
7. `audit_checklist` A1-A10: `tick`. `full_build_line`: `approve`, or your own line. `u2_vouch: yes`.
8. `coral_questions` Q1-Q22: `confirm`, or your own answer. Q9, Q10 and Q22 go into the ban.yaml header and decide
   verdicts: if you answer one of them other than `confirm`, write the verdict changes under `ban.changes`, or set
   `acknowledge_q_answers: yes` to sign the drafted verdicts with your answer recorded (the dry run then warns). Every
   answer other than `confirm` is printed as a follow-up for prereg section 12 item 7 (U6).
9. `text_edits_approve: yes`, after reading the edits in the dry-run output (`--full` prints them untruncated).

## Not done by the tool (printed as follow-ups)

- `tests/test_layer_shapes.py:57` (matrix_dir).
- `treeroute_report/continuity_groups.yaml` (coral entry).
- The pre-registration markers of section 12 items 2, 3, 5 and 7, and item 8 once the report-script SHA-256 lines
  are filled in section 6.2; the section 13 signatures; by hand.
- Then: check, check --deep and plan on `datasets/coral`.

## Dry-run evidence (tools/_dryrun/)

Earlier sets were moved aside, never deleted: `_superseded_20261020_v1/` (before the review fixes), `_v2/` and `_v3/`
(intermediate runs of the fixes). The template made before the fixes is `tools/_moved/`.


- `dryrun_1_template.txt`: the blank template. Refused, 144 unanswered items.
- `dryrun_2_dummy.txt`: dummy answers, exit 0. 90 changes in 7 files; every check clean; predicted fingerprint
  56f31f72....
- `dryrun_3_render_load.txt`: the planned files, written only to `_dryrun/rendered/coral`, load with
  `load_package`. The fingerprint equals the plan, and `is_draft` is False.
- `dryrun_4_quick_rendered.txt`: the table quick check on that scratch copy. All pass, and G-FACTS passes.
- `dryrun_5_negative.txt`: text edits X3/X4 dropped. Refused, naming the stale lines exceptions.yaml:125-126.
- `dryrun_6_change_dhw_30.txt`: dhw_30 changed to watch. Exit 0; its "unsigned (Q22)" is closed.
- `dryrun_7_change_ctx_mmm.txt`: ctx_mmm changed. Exit 0; no "(owner item)" left; F-BAN-OPEN 0 lines.
- `dryrun_8_negative_ctx_mmm_note.txt`: a changed ctx_mmm reason that keeps "(owner item)". Refused.
- `dryrun_9_negative_Q10_a.txt`: Q10 answered "a" with no verdict change. Refused.
- `dryrun_10_Q10_a_acknowledged.txt`: the same with `acknowledge_q_answers: yes`. Exit 0, a WARNING line and the
  Q10 follow-up.
- `dryrun_11_apply_guards.txt` (`apply_guards.py`): `--apply` refused without `--expect-fingerprint`, with a wrong
  one, from `_dryrun`, with DUMMY in the ruling id or the signer, and with a future date; then one complete `--apply`
  into a scratch copy of the datasets folder (scratch rulings file): written, loaded, fingerprint equal, record
  written. The real `datasets/coral` did not exist before or after.
- `stray_tmp_dr1.txt`: a stray copy of the first dry run 1 output (the temp folder's dr1.txt, 06:56), moved here.
