"""Make the signed coral package datasets/coral from the development copy datasets/coral_draft (dataset tool).

    py -3.9 -B D:/treeroute/coral_build/tools/make_signed_coral.py template --out <new file>   # write a blank answers file
    py -3.9 -B D:/treeroute/coral_build/tools/make_signed_coral.py sign <answers.yaml>           # DRY RUN (the default)
    py -3.9 -B D:/treeroute/coral_build/tools/make_signed_coral.py sign <answers.yaml> --dry-run # the same, said aloud
    py -3.9 -B D:/treeroute/coral_build/tools/make_signed_coral.py sign <answers.yaml> --apply --expect-fingerprint <fp>
                                                     # write datasets/coral; <fp> = the dry run's predicted fingerprint

WHAT IT IS FOR. The four grid packages were made BEFORE their drafts: datasets/_tools/refresh_drafts.py derives each
<name>_draft from <name> (name '<name>_draft', version '-draft', owner 'UNSIGNED -- DRAFT ...', the DRAFT stamp on the
description and on every ban evidence), and datasets/_tools/apply_signoff.py then wrote the owner's answers into the
real packages (signed facts: fact_status + reviewed_by 'owner' + date; signed exceptions: an 'owner' field whose first
word is not a placeholder). Coral went the other way: only coral_draft exists. This tool makes datasets/coral from it:
  - dataset.yaml: name 'coral', the owner's version and owner text, a description without the DRAFT stamp (the engine
    reads a draft from 'DRAFT --' in the description or version: treeroute/pipeline/draft.py:51-57);
  - catalog.yaml: the target's facts signed (fact_status from the answer, reviewed_by 'owner', date; the ruling
    appended to its provenance). A table package's G-FACTS passes only on 'verified' (treeroute/check/table.py:131-136);
  - ban.yaml: every verdict signed as drafted or changed by the owner; the '(owner item)' note settled (it matches the
    freeze's F-BAN-OPEN scan, treeroute_report/freeze.py:127-134); 'unsigned (Qn)' evidence phrases closed; the
    header's Counts line recomputed;
  - exceptions.yaml: every 'UNSIGNED -- basis: X' owner field becomes 'owner -- signed by the owner <date> (ruling
    ...); basis: X' (the grid spelling, datasets/defo/exceptions.yaml:33), or is kept when it already names a ruling;
  - AUDIT_CHECKLIST.md: the ten section-A boxes ticked, the full-build evidence line added to section B, the U2
    statement signed (signature line);
  - every stale DRAFT / UNSIGNED text: replaced by the 'text_edits' of the answers file (agent-PROPOSED texts the owner
    approves as a block); split.yaml and ingest/README.md change in comments and prose only.
It refuses (and writes nothing) while ANY item of the answers file is unanswered, and lists every missing item. It
also refuses an answer to Q9, Q10 or Q22 other than 'confirm' when no verdict is changed (ban.changes empty), unless
acknowledge_q_answers is 'yes': those questions decide ban.yaml verdicts.

SAFETY. The default is a dry run: it reads coral_draft and the engine modules (bytecode writing off), builds every new
file in memory, validates it with the engine's own schema, loader rules, draft stamp, F-BAN-OPEN scan and exception
rule, computes the new package fingerprint, prints every change, and writes NOTHING. 'template' writes only the new
file named by --out (never over an existing file, never inside the engine folder). --apply also:
  refuses without --expect-fingerprint, or when the plan's fingerprint differs from it (the owner approves the dry
  run he read, nothing else); refuses when datasets/coral exists, when the answers file sits in tools/_dryrun/, when
  ruling.id, signer or dataset.owner says DUMMY, when ruling.date is after today, when the
  cited ruling section is not in the rulings file, when coral_draft changed since its GREEN deep check (fingerprint
  04b9aab0..., D:/treeroute/runs/coral_draft/check/check_deep_04b9aab0fb5a.json; pass --draft-fingerprint to accept a
  newer one), or when a target lies under a protected root (D:/treeroute/registry/protected_roots.txt);
  writes the files into a NEW folder datasets/_staging_coral_<stamp>/ (open mode 'xb'), loads it with the engine's
  load_package, checks the fingerprint equals the dry run's, then RENAMES it to datasets/coral (same drive). On any
  failure the staging folder is renamed to datasets/_moved_signed_coral_<stamp>/ (never deleted);
  writes a record (answers sha256, every file's sha256 before and after, the fingerprints, the follow-ups) and a copy
  of the answers file under D:/treeroute/coral_build/tools/signoff_records/.
It never edits coral_draft, engine code, treeroute_report/continuity_groups.yaml, tests, the pre-registration or the
rulings file: those are printed as follow-ups.
"""
# Provenance: datasets/_tools/refresh_drafts.py:80-138 (how a draft differs from its package), apply_signoff.py:12-62
# (answers -> edits; dry run by default; move aside, never delete), treeroute/pipeline/draft.py (the DRAFT stamp),
# treeroute/check/guards.py:133-159 (signed facts, signed exceptions), treeroute/check/table.py:131-136 (table
# G-FACTS), treeroute_report/freeze.py:127-134 (OPEN_DECISION), D:/treeroute/coral_build/PREREGISTRATION_DRAFT_coral.md
# section 12 items 3, 5, 7 and section 13 (the edit list), D:/treeroute/coral_build/CORAL_MORNING_SHEET.md B-D,
# OWNER_RULINGS_2026-10-06.md U, V, W.

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True          # importing the LIVE engine must not write __pycache__ into it

import yaml  # noqa: E402

ENGINE = Path(r"C:\Users\moh the ghost\Desktop\data set for reserch paper\engine")
DATASETS = ENGINE / "datasets"
DRAFT = "coral_draft"
SIGNED = "coral"
TOOLS = Path(__file__).resolve().parent
DRYRUN_DIR = TOOLS / "_dryrun"
RECORDS = TOOLS / "signoff_records"
PROTECTED_LIST = Path("D:/treeroute/registry/protected_roots.txt")
CHECKED_DRAFT_FINGERPRINT = "04b9aab0fb5aa616d8544c8babff0d373800aea9c1c8d088d3911444082d7045"
CHECK_REPORT = "D:/treeroute/runs/coral_draft/check/check_deep_04b9aab0fb5a.json"
TARGET = "pct_bleached"
OWNER_ITEM_COLUMN = "ctx_mmm"
OWNER_ITEM_TEXT = "(owner item)"
EXPECTED_EXCLUDED = 11                  # V5; split.yaml under V6 (b) excludes only these (ruling W1)
AUDIT_ROWS = 10
AUDIT_TINY_LINE = "Tiny build 2026-10-19: all passed (coral_data/tiny/build_manifest.json, check_report.json)."
AUDIT_SIGNATURE = "Signed: ____________________   Date: ____________"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PLACEHOLDERS = ("{date}", "{ruling_id}", "{ruling_file}", "{signer}", "{target_fact_status}", "{Q9}", "{Q10}", "{Q22}")
# Text that must not survive into the signed package (case-insensitive unless the flag says so).
STALE = [(re.compile(p, f), p) for p, f in (
    (r"\bunsigned\b", re.I), (r"\bnot signed\b", re.I), (r"\bDRAFT\b", 0), (r"\bdraft option\b", re.I),
    (r"\bawaiting the owner\b", re.I), (r"\bowner chooses\b", re.I), (r"\(to sign\)", re.I),
    (r"\bnothing (?:here is )?signed\b", re.I), (r"\buntil the owner ticks\b", re.I), (r"\bcoral_draft\b", 0),
    (r"\bowner items?\b", re.I), (r"\bOWNER DECISION\b", 0), (r"\bpending\b", re.I))]
STALE_FILES = ("dataset.yaml", "catalog.yaml", "ban.yaml", "split.yaml", "exceptions.yaml", "AUDIT_CHECKLIST.md",
               "ingest/README.md")
# Text edits that may change parsed YAML content (everything else must change comments only).
CONTENT_EDIT_FIELDS = {"exceptions.yaml": ("decision", "reason", "owner")}

# The agent's reading of the coral question sheet (PREREGISTRATION_DRAFT_coral.md section 12 item 7,
# CORAL_ENGINE_PLAN.md:244-267). 'confirm' accepts the reading; any other text is the owner's own answer.
CORAL_QUESTIONS = (
    ("Q1", "item-13 flags", "not ruled as a bundle; pool part overtaken by U3; built engine values, one row each"),
    ("Q2", "pool mode", "engine pool overtaken by U4; strict pool only; side rows out of scope"),
    ("Q3", "close Q28-Q32 pool items", "not ruled; strict pool (U4)"),
    ("Q4", "guard and decline objects", "overtaken by V1 (donor-row median)"),
    ("Q5", "scored rows", "overtaken by U1 (test marks)"),
    ("Q6", "test window end", "overtaken by V3 (2016-2019)"),
    ("Q7", "repeat surveys", "not ruled; averaged, disclosed (exceptions entry 2)"),
    ("Q8", "one-site groups", "overtaken by V5"),
    ("Q9", "column set 77 / 80", "not ruled; the drafted ban.yaml column set, signed here"),
    ("Q10", "heat totals", "not ruled; drafted ban.yaml as Q10 b, signed here"),
    ("Q11", "season at a lead", "overtaken by H3 and V8"),
    ("Q12", "GLS and c for folds", "not ruled; signed R13, R25; departure fold_gls_entry (V4)"),
    ("Q13", "corrector arms", "not ruled; the engine's arms as for grids"),
    ("Q14", "headline form", "not ruled; signed D74 decides; per-programme verdict lines are report only"),
    ("Q15", "legacy harness replay", "not ruled; V7 toy-only replay; legacy replay out of scope"),
    ("Q16", "G-DERIVED route", "overtaken by U2 (vouched, no recompute)"),
    ("Q17", "verdict reference", "not ruled; donor-row median by signed R34 + V1; trees-off printed beside"),
    ("Q18", "groups with no rows at a cut", "overtaken by V5"),
    ("Q19", "rivals", "not ruled; deferred by signed rulings E, L3"),
    ("Q20", "imputed day 15", "not ruled; month precision (exceptions entry 0)"),
    ("Q21", "group id form", "not ruled; ecoregion names; R21 smoke groups as listed"),
    ("Q22", "C3's remaining verdicts", "not ruled; partly overtaken by V9; drafted ban.yaml, signed here"),
)
# The questions whose answers decide ban.yaml verdicts (written into its header by text edit B1).
BAN_QUESTIONS = ("Q9", "Q10", "Q22")

FULL_BUILD_LINE_PROPOSED = (
    "Full build 2026-10-20 (the tables this package reads, published write-once to "
    "coral_store/20261020_014201): coral_data/full/build_manifest.json 'proof' (asserts passed on 41,066 row-leads; "
    "canary 822 row-leads, 0 mismatches; largest source day minus issue day sst -2, cyclone -2, index -1, "
    "feature_end -1 at every lead; replay largest relative difference 0) and coral_data/full/check_report.json "
    "(passed, 52 checks ok).")

DESCRIPTION_PROPOSED = (
    "percent of coral bleached per survey visit (GCBD; Reef Check, AGRRA, FRRP, McClanahan, Donner), one row per site "
    "and date, grouped by ecoregion; hand-built SST, marine-heatwave, cyclone and ENSO/IOD features that end before "
    "each issue date (leads 0, 183, 365 days); neighbour router; feature timing vouched by the owner (U2); signed "
    "{date} (ruling {ruling_id})")

# Agent-PROPOSED prose edits (file, old, new). 'old' must occur exactly once in the coral_draft file. The owner
# approves them as a block (text_edits_approve: yes); an edited copy in the answers file is reported as CHANGED.
PROPOSED_TEXT_EDITS = (
    ("D1", "dataset.yaml",
     "# dataset.yaml -- coral_draft: the coral bleaching TABLE package (owner ruling U, OWNER_RULINGS_2026-10-06.md:84-95).\n"
     "# DRAFT, written 2026-10-19 by the agent in the build copy (D:/treeroute/coral_build). UNSIGNED. Development and smoke\n"
     "# only, never a headline run. Design:",
     "# dataset.yaml -- coral: the coral bleaching TABLE package (owner ruling U, OWNER_RULINGS_2026-10-06.md:84-95).\n"
     "# SIGNED by the owner {date} (ruling {ruling_id}, {ruling_file}). Made by\n"
     "# D:/treeroute/coral_build/tools/make_signed_coral.py from the development copy the agent wrote on 2026-10-19 in\n"
     "# the build copy (D:/treeroute/coral_build). The headline package. Design:"),
    ("D2", "dataset.yaml",
     "The owner adds the store root to D:/treeroute/registry/protected_roots.txt before\n"
     "# the freeze (SPEC_TABLE_MODE.md 1.2).",
     "The store root D:/treeroute/coral_build/coral_store is listed in\n"
     "# D:/treeroute/registry/protected_roots.txt (added 2026-10-20 by the session, confirmed by the owner {date};\n"
     "# SPEC_TABLE_MODE.md 1.2)."),
    ("C1", "catalog.yaml",
     "# catalog.yaml -- coral_draft package facts (SPEC_TABLE_MODE.md 1.3-1.5). GENERATED 2026-10-19 by\n"
     "# D:/treeroute/coral_build/coral_tables/make_draft.py from columns.py; edit columns.py, not this file. UNSIGNED.",
     "# catalog.yaml -- coral package facts (SPEC_TABLE_MODE.md 1.3-1.5). GENERATED 2026-10-19 by\n"
     "# D:/treeroute/coral_build/coral_tables/make_draft.py from columns.py. The target's facts were then signed by the\n"
     "# owner {date} (ruling {ruling_id}) through make_signed_coral.py, so this file is no longer the generator's output:\n"
     "# never re-run make_draft.py on this package (it rewrites this file and ban.yaml and would lose the signatures)."),
    ("C2", "catalog.yaml",
     "fact_status is 'unverified' everywhere (the schema default): nothing here is signed.",
     "fact_status is 'unverified' (the schema default) on every column except the\n"
     "# target pct_bleached, whose facts the owner signed {date} ({target_fact_status}, reviewed_by owner)."),
    ("B1", "ban.yaml",
     "# ban.yaml -- coral_draft verdicts (SPEC_TABLE_MODE.md 1.4; schema treeroute/package/schema.py:446-474). GENERATED\n"
     "# 2026-10-19 by D:/treeroute/coral_build/coral_tables/make_draft.py from columns.py. UNSIGNED: the verdicts follow\n"
     "# CORAL_ENGINE_PLAN.md:153-176 (section C3), whose open questions are Q9, Q10 and Q22 (:254-255, :267). The owner\n"
     "# signs them before the coral freeze (ruling U6).",
     "# ban.yaml -- coral verdicts (SPEC_TABLE_MODE.md 1.4; schema treeroute/package/schema.py:446-474). GENERATED\n"
     "# 2026-10-19 by D:/treeroute/coral_build/coral_tables/make_draft.py from columns.py. SIGNED by the owner {date}\n"
     "# (ruling {ruling_id}, {ruling_file}) through make_signed_coral.py: every verdict below. The verdicts follow\n"
     "# CORAL_ENGINE_PLAN.md:153-176 (section C3). Its questions (:254-255, :267): Q9 {Q9}; Q10 {Q10}; Q22 {Q22}."),
    ("S1", "split.yaml",
     "# split.yaml -- coral_draft (SPEC",
     "# split.yaml -- coral (SPEC"),
    ("S2", "split.yaml",
     "# V6 (b) OPTION, DRAFT (D:/treeroute/coral_build_v6b/PLAN_V6B.md): not signed; the owner chooses V6 (a) or V6 (b).",
     "# V6 (b): owner ruling W1 (2026-10-20; OWNER_RULINGS_2026-10-06.md:116-121), which replaces V6; built as\n"
     "# D:/treeroute/coral_build_v6b (PLAN_V6B.md)."),
    ("S3", "split.yaml",
     "GENERATED by\n# coral_tables/make_split.py --write (2026-10-19) from D:/treeroute/coral_build/coral_data/visits.parquet.",
     "GENERATED by\n# the V6 (b) copy D:/treeroute/coral_build_v6b/coral_tables/make_split.py --write (2026-10-19) from\n"
     "# D:/treeroute/coral_build/coral_data/visits.parquet (stage 1). Checked 2026-10-20 by that file (SHA-256\n"
     "# a69e1c8c...) with --check on the published lead tables: PASS (engine PENDING_PARTS.md Part 595)."),
    ("X1", "exceptions.yaml",
     "# exceptions.yaml -- coral_draft (SPEC",
     "# exceptions.yaml -- coral (SPEC"),
    ("X2", "exceptions.yaml",
     "Drafted 2026-10-19 by the agent. Every 'owner' field reads 'UNSIGNED -- basis: ...':\n"
     "# the entry is NOT signed; it names the evidence behind it. 'date' is the date of that basis, not a signature.\n"
     "# An 'owner' field that names owner ruling V (OWNER_RULINGS_2026-10-06.md:97-114, signed 2026-10-19) is signed by\n"
     "# that ruling item (V3, V5, V6, V9 below).",
     "Drafted 2026-10-19 by the agent. Signed {date}: an 'owner' field that reads\n"
     "# 'owner -- signed by the owner ...; basis: ...' was signed through make_signed_coral.py (ruling {ruling_id}); one\n"
     "# that names owner ruling V (OWNER_RULINGS_2026-10-06.md:97-114, signed 2026-10-19) or W1 (:116-121) is signed by\n"
     "# that ruling item. 'date' is the date of the entry's basis, not of the signature."),
    ("X3", "exceptions.yaml",
     "V6 (b) DRAFT OPTION (D:/treeroute/coral_build_v6b/PLAN_V6B.md; not signed): the 46 groups",
     "V6 (b), owner ruling W1 (2026-10-20; OWNER_RULINGS_2026-10-06.md:116-121; D:/treeroute/coral_build_v6b/PLAN_V6B.md): the 46 groups"),
    ("X4", "exceptions.yaml",
     "; V6 (b) is a DRAFT option awaiting the owner (the signed V6 text, :108, says left out)",
     "; V6 (b) by owner ruling W1 (2026-10-20; OWNER_RULINGS_2026-10-06.md:116-121), which replaces V6 (:108)"),
    ("X5", "exceptions.yaml",
     "(engine: derived.json R18:donor_only; listed in the plan, run record, verdict.json and the report disclosures)",
     "(counted and disclosed as ruling W1 lists: derived.json R18:donor_only, the run records, the check report and one "
     "report disclosure row)"),
    ("R1", "ingest/README.md",
     "# coral_draft: the coral bleaching table package (DRAFT)",
     "# coral: the coral bleaching table package (signed {date})"),
    ("R2", "ingest/README.md",
     "Written 2026-10-19 under owner ruling U (OWNER_RULINGS_2026-10-06.md:84-95). Unsigned. Development and smoke only.",
     "Written 2026-10-19 under owner ruling U (OWNER_RULINGS_2026-10-06.md:84-95). Signed by the owner {date} (ruling\n"
     "{ruling_id}, {ruling_file}) through D:/treeroute/coral_build/tools/make_signed_coral.py. The headline package."),
    ("R3", "ingest/README.md",
     "LIVE\n(hash 65a177bc...) refuses it. The build copy's table reader (in progress, 2026-10-19) loads the tiny copy.",
     "LIVE has\nit since 2026-10-20 (engine_code_sha256 930d961c..., the V6 (b) engine; INSTALL_MANIFEST.json in\n"
     "engine/_moved_coral_20261020_064437)."),
    ("R4", "ingest/README.md",
     "(V6 b DRAFT option: no test row; they train and lend rows, nothing is scored for them)",
     "(V6 b, owner ruling W1: no test row; they train and lend rows, nothing is scored for them)"),
    ("R5", "ingest/README.md",
     "(V3, V5 and V9 entries signed by ruling V; the V6 (b) donor-only entry is a DRAFT option, not signed)",
     "(V3, V5 and V9 entries signed by ruling V, the donor-only entry by rulings V5 and W1, the others by the owner {date})"),
    ("R6", "ingest/README.md",
     "| AUDIT_CHECKLIST.md | human checks and the owner's U2 timing statement (to sign) |",
     "| AUDIT_CHECKLIST.md | human checks and the owner's U2 timing statement (signed {date}) |"),
    ("R7", "ingest/README.md",
     "- **V6 (b) donor-only groups (DRAFT option, not signed; D:/treeroute/coral_build_v6b/PLAN_V6B.md).**",
     "- **V6 (b) donor-only groups (owner ruling W1, 2026-10-20, which replaces V6; D:/treeroute/coral_build_v6b/PLAN_V6B.md).**"),
    ("R8", "ingest/README.md",
     "py -3.9 make_draft.py                            # rewrite catalog.yaml and ban.yaml from columns.py\n"
     "py -3.9 -u make_split.py --check                 # split.yaml still follows V5 with no V6 exclusion (V6 b copy; exit 1 if not); --write rewrites it\n"
     "py -3.9 -u make_split.py --lead-dir D:\\treeroute\\coral_build\\coral_data\\full --check   # again after stage 2",
     "# make_draft.py (it rewrites catalog.yaml and ban.yaml from columns.py) is NEVER run on the signed package: it\n"
     "# would lose the signatures written by make_signed_coral.py.\n"
     "# The split check uses the V6 (b) file in coral_build_v6b (SHA-256 a69e1c8c...), NOT coral_tables\\make_split.py in\n"
     "# this folder (the pre-(b) version, SHA-256 c38d76b1..., which checks V6 (a)). Its path guard (make_split.py:188-190)\n"
     "# lets it read only a split.yaml under D:\\treeroute\\coral_build_v6b: its own copy of the development package's\n"
     "# split.yaml (the same entries as this package's; only the comments differ).\n"
     "py -3.9 -u D:\\treeroute\\coral_build_v6b\\coral_tables\\make_split.py --check   # V5 with no V6 exclusion (exit 1 if not)\n"
     "py -3.9 -u D:\\treeroute\\coral_build_v6b\\coral_tables\\make_split.py --lead-dir D:\\treeroute\\coral_build\\coral_data\\full --check   # again after stage 2"),
    ("R9", "ingest/README.md",
     "## Signed answers, ruling V (2026-10-19)",
     "## Signed answers, ruling V (2026-10-19; V6 replaced by ruling W, 2026-10-20)"),
    ("R10", "ingest/README.md",
     "The table departures (TABLE_DEPARTURES, pipeline/table_run.py:52-70) are accepted at the\n"
     "  coral freeze, as S21 did for the grid departures.",
     "The table departures are accepted at the coral freeze, as S21 did for the grid departures.\n"
     "  Built: they are listed in TABLE_ACCEPTED_DEPARTURES (pipeline/table_run.py:58-73) and written into the run record\n"
     "  as accepted_departures; TABLE_DEPARTURES is empty (:57)."),
    ("R11", "ingest/README.md",
     "6. From LIVE after the install: check, smoke, run.",
     "6. From LIVE (the table option is installed: engine 930d961c..., 2026-10-20): check, smoke, run, at the same engine\n"
     "   hash as the headline run."),
    ("A1", "AUDIT_CHECKLIST.md",
     "# AUDIT_CHECKLIST -- coral_draft (table package)",
     "# AUDIT_CHECKLIST -- coral (table package)"),
    ("A2", "AUDIT_CHECKLIST.md",
     "**UNSIGNED.** Drafted by the agent\non 2026-10-19. Every box is open until the owner ticks it and signs at the bottom.",
     "**SIGNED** by the owner {date} (ruling\n{ruling_id}). Drafted by the agent on 2026-10-19; the boxes were ticked and the signature written from the\n"
     "owner's answers by make_signed_coral.py."),
    ("A3", "AUDIT_CHECKLIST.md",
     "(V6 b DRAFT option: they train trees and lend rows; nothing is scored for them)",
     "(V6 b, owner ruling W1, 2026-10-20: they train trees and lend rows; nothing is scored for them)"),
    ("A4", "AUDIT_CHECKLIST.md",
     "Open timing facts the owner must accept or change before signing:",
     "Open timing facts the owner accepted by signing ({date}):"),
)


class SignRefusal(Exception):
    """The answers or the draft do not allow the signed package (fail loudly; nothing is written)."""


# ==================================================================================================== engine
def engine_modules():
    if str(ENGINE) not in sys.path:
        sys.path.insert(0, str(ENGINE))
    from treeroute.package import schema as S
    from treeroute.package import load as L
    from treeroute.pipeline.draft import draft_status, DRAFT_MARKER
    from treeroute.check.guards import exception_signed
    from treeroute.runs.fingerprint import sha256_bytes
    from treeroute_report.freeze import OPEN_DECISION
    return SimpleNamespace(S=S, L=L, draft_status=draft_status, DRAFT_MARKER=DRAFT_MARKER,
                           exception_signed=exception_signed, sha256_bytes=sha256_bytes, OPEN_DECISION=OPEN_DECISION)


def parse_yaml(E, text, name):
    try:
        return yaml.load(text, Loader=E.L._UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise SignRefusal("%s does not parse as YAML: %s" % (name, exc))


def validate(E, name, text):
    data = parse_yaml(E, text, name)
    if data is None and name in E.L.EMPTY_ALLOWED:
        data = {}
    try:
        return data, E.S.PACKAGE_FILE_MODELS[name].model_validate(data)
    except Exception as exc:            # pydantic ValidationError
        raise SignRefusal("%s fails the engine schema:\n%s" % (name, exc))


def fingerprint(E, files):
    """The engine's package fingerprint (treeroute/package/load.py:198-216) from {relative path: bytes}."""
    hashes = {}
    for rel in sorted(files):
        parts = rel.split("/")
        if parts[0] in E.L.NOT_FINGERPRINTED_DIRS or "__pycache__" in parts or rel in E.L.NOT_FINGERPRINTED_FILES:
            continue
        hashes[rel] = E.sha256_bytes(files[rel])
    return E.L.package_fingerprint(hashes, {}), hashes


# ==================================================================================================== files
def read_package(root):
    out = {}
    for dirpath, dirnames, filenames in os.walk(str(root)):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for f in sorted(filenames):
            out[Path(dirpath, f).relative_to(root).as_posix()] = Path(dirpath, f).read_bytes()
    return out


def to_text(data, rel):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise SignRefusal("%s is not UTF-8" % rel)
    crlf = "\r\n" in text
    return text.replace("\r\n", "\n"), crlf


def to_bytes(text, crlf):
    return (text.replace("\n", "\r\n") if crlf else text).encode("utf-8")


def sq(text):
    return "'" + str(text).replace("'", "''") + "'"


def one_line(text, what):
    text = str(text)
    if "\n" in text or "\r" in text:
        raise SignRefusal("%s must be one line" % what)
    return text.strip()


def word(value):
    """YAML 1.1 reads yes/no as booleans: read them back as the words."""
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "" if value is None else str(value).strip()


def short(text, n=150):
    text = str(text).replace("\n", " / ")
    return text if len(text) <= n else text[:n - 3] + "..."


def protected_roots():
    if not PROTECTED_LIST.is_file():
        raise SignRefusal("%s is missing: cannot check the protected roots" % PROTECTED_LIST)
    roots = []
    for line in PROTECTED_LIST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            roots.append(os.path.normcase(os.path.abspath(line)))
    return roots


def under_protected(path, roots):
    p = os.path.normcase(os.path.abspath(str(path)))
    return [r for r in roots if p == r or p.startswith(r.rstrip("\\/") + os.sep)]


# ==================================================================================================== answers
def load_answers(path, draft_ban, draft_exc):
    """Read the answers file. Returns (answers namespace, [missing items], [problems])."""
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(doc, dict):
        raise SignRefusal("%s is not a mapping" % path)
    known = {"ruling", "signer", "v6_choice", "protected_root_confirm", "matrix_dir", "continuity_groups", "dataset",
             "target_facts", "ban", "exceptions", "audit_checklist", "u2_vouch", "coral_questions",
             "text_edits_approve", "text_edits", "acknowledge_q_answers"}
    extra = sorted(set(doc) - known)
    if extra:
        raise SignRefusal("unknown top-level keys in %s: %s" % (path, extra))
    missing, problems = [], []

    def need(value, item, allowed=None):
        v = word(value)
        if not v:
            missing.append(item)
            return ""
        if allowed is not None and v not in allowed:
            problems.append("%s: %r is not one of %s" % (item, v, list(allowed)))
        return v

    r = doc.get("ruling") or {}
    ruling = SimpleNamespace(id=need(r.get("id"), "ruling.id"), file=need(r.get("file"), "ruling.file"),
                             date=need(r.get("date"), "ruling.date"))
    if ruling.date and not DATE_RE.match(ruling.date):
        problems.append("ruling.date %r is not YYYY-MM-DD" % ruling.date)
    signer = need(doc.get("signer"), "signer")
    v6 = need(doc.get("v6_choice"), "v6_choice", ("b", "a"))
    if v6 == "a":
        problems.append("v6_choice 'a': coral_draft carries the V6 (b) split (ruling W1, 2026-10-20); this tool does "
                        "not make an (a) split.yaml. Rule again, or answer b")
    root_ok = need(doc.get("protected_root_confirm"), "protected_root_confirm", ("yes", "no"))
    if root_ok == "no":
        problems.append("protected_root_confirm 'no': settle D:/treeroute/registry/protected_roots.txt:8 first; the "
                        "signed dataset.yaml says the root is confirmed (text edit D2)")
    matrix = need(doc.get("matrix_dir"), "matrix_dir", ("approve", "reject"))
    cont = doc.get("continuity_groups")
    if cont is None or (isinstance(cont, str) and not cont.strip()):
        missing.append("continuity_groups")
        cont = None
    elif isinstance(cont, str) and cont.strip() == "empty":
        cont = []
    elif isinstance(cont, list) and all(isinstance(g, str) and g.strip() for g in cont):
        cont = list(cont)
    else:
        problems.append("continuity_groups must be 'empty' or a list of group names, got %r" % (cont,))
        cont = None

    d = doc.get("dataset") or {}
    version = need(d.get("version"), "dataset.version")
    owner = need(d.get("owner"), "dataset.owner")
    desc = need(d.get("description"), "dataset.description")
    if desc == "proposed":
        desc = DESCRIPTION_PROPOSED

    t = doc.get("target_facts") or {}
    tfs = need(t.get("fact_status"), "target_facts.fact_status", ("verified", "assumed"))

    b = doc.get("ban") or {}
    ban_all = need(b.get("all"), "ban.all", ("sign_all", "per_column"))
    owner_item = need(b.get("owner_item_ctx_mmm"), "ban.owner_item_ctx_mmm", ("accept", "change"))
    per_col = b.get("verdicts") or {}
    changes = b.get("changes") or {}
    unknown = sorted(set(per_col) - set(draft_ban)) + sorted(set(changes) - set(draft_ban))
    if unknown:
        problems.append("ban: unknown columns %s" % unknown)
    verdict_answers = {}
    for col in draft_ban:
        item = per_col.get(col) or {}
        a = word(item.get("answer") if isinstance(item, dict) else item)
        if not a:
            if ban_all == "sign_all":
                a = "sign"
            else:
                missing.append("ban.verdicts.%s.answer" % col)
                continue
        if a not in ("sign", "change"):
            problems.append("ban.verdicts.%s.answer: %r is not sign or change" % (col, a))
            continue
        if a == "change":
            ch = changes.get(col) or {}
            if not word(ch.get("verdict")) or not word(ch.get("reason")) or not word(ch.get("note")):
                problems.append("ban.verdicts.%s is 'change' but ban.changes.%s lacks verdict, reason or note" % (col, col))
        verdict_answers[col] = a
    if owner_item == "change" and verdict_answers.get(OWNER_ITEM_COLUMN) != "change":
        problems.append("ban.owner_item_ctx_mmm 'change': write the new verdict under ban.changes.%s and answer "
                        "ban.verdicts.%s 'change'" % (OWNER_ITEM_COLUMN, OWNER_ITEM_COLUMN))
    if owner_item == "accept" and verdict_answers.get(OWNER_ITEM_COLUMN) == "change":
        problems.append("ban.owner_item_ctx_mmm 'accept' but ban.verdicts.%s is 'change': the two answers disagree; "
                        "answer owner_item_ctx_mmm 'change'" % OWNER_ITEM_COLUMN)
    if owner_item == "change":
        new_reason = word((changes.get(OWNER_ITEM_COLUMN) or {}).get("reason"))
        if OWNER_ITEM_TEXT in new_reason:
            problems.append("ban.changes.%s.reason still holds the note %r: the freeze's F-BAN-OPEN scan would match "
                            "it; write the settled reason" % (OWNER_ITEM_COLUMN, OWNER_ITEM_TEXT))

    x = doc.get("exceptions") or {}
    xe = x.get("entries") or {}
    exc_answers = {}
    for i in range(len(draft_exc)):
        item = xe.get(i, xe.get(str(i))) or {}
        a = word(item.get("answer") if isinstance(item, dict) else item)
        if not a:
            missing.append("exceptions.entries.%d.answer" % i)
            continue
        if a not in ("sign", "keep"):
            problems.append("exceptions.entries.%d.answer: %r is not sign or keep" % (i, a))
        exc_answers[i] = a
    extra_idx = sorted(str(k) for k in xe if str(k) not in {str(i) for i in range(len(draft_exc))})
    if extra_idx:
        problems.append("exceptions.entries: unknown entry numbers %s" % extra_idx)

    au = doc.get("audit_checklist") or {}
    ticks = {}
    for n in range(1, AUDIT_ROWS + 1):
        v = need(au.get("A%d" % n), "audit_checklist.A%d" % n, ("tick",))
        ticks[n] = v
    fbl = need(au.get("full_build_line"), "audit_checklist.full_build_line")
    if fbl == "approve":
        fbl = FULL_BUILD_LINE_PROPOSED
    u2 = need(doc.get("u2_vouch"), "u2_vouch", ("yes",))

    cq = doc.get("coral_questions") or {}
    q_answers = {}
    for q, _topic, _reading in CORAL_QUESTIONS:
        item = cq.get(q) or {}
        a = word(item.get("answer") if isinstance(item, dict) else item)
        if not a:
            missing.append("coral_questions.%s.answer" % q)
        q_answers[q] = a
    # Q9, Q10 and Q22 decide verdicts of ban.yaml. An answer other than 'confirm' with no verdict changed would sign
    # the drafted verdicts under a header that says otherwise: refused unless the owner says so in words.
    ack = word(doc.get("acknowledge_q_answers"))
    if ack not in ("", "yes", "no"):
        problems.append("acknowledge_q_answers: %r is not yes or no" % ack)
    differ = [q for q in BAN_QUESTIONS if q_answers.get(q) and q_answers[q] != "confirm"]
    if differ and not changes and ack != "yes":
        problems.append("coral_questions %s answered other than 'confirm', but ban.changes is empty: every verdict "
                        "would be signed as drafted. Write the verdict changes under ban.changes, or set "
                        "acknowledge_q_answers: yes to sign the drafted verdicts with that answer recorded"
                        % ", ".join(differ))

    approve = need(doc.get("text_edits_approve"), "text_edits_approve", ("yes",))
    edits = []
    for k, e in enumerate(doc.get("text_edits") or []):
        if not isinstance(e, dict) or set(e) - {"id", "file", "old", "new"} or not all(
                isinstance(e.get(f), str) and e.get(f) for f in ("id", "file", "old")) or not isinstance(e.get("new"), str):
            problems.append("text_edits[%d] needs id, file, old, new (strings)" % k)
            continue
        edits.append(SimpleNamespace(id=e["id"], file=e["file"], old=e["old"], new=e["new"]))
    if not edits:
        missing.append("text_edits (the list is empty)")
    ids = [e.id for e in edits]
    if len(set(ids)) != len(ids):
        problems.append("text_edits: repeated ids %s" % sorted({i for i in ids if ids.count(i) > 1}))

    return SimpleNamespace(ruling=ruling, signer=signer, v6=v6, root_ok=root_ok, matrix=matrix, continuity=cont,
                           version=version, owner=owner, description=desc, target_fact_status=tfs, ban_all=ban_all,
                           owner_item=owner_item, verdict_answers=verdict_answers, changes=changes,
                           exc_answers=exc_answers, ticks=ticks, full_build_line=fbl, u2=u2, q_answers=q_answers,
                           approve=approve, edits=edits, ack_q=ack), missing, problems


def fill(text, ans):
    q = {k: ("confirmed as drafted" if v == "confirm" else v) for k, v in ans.q_answers.items()}
    values = {"{date}": ans.ruling.date, "{ruling_id}": ans.ruling.id, "{ruling_file}": ans.ruling.file,
              "{signer}": ans.signer, "{target_fact_status}": ans.target_fact_status,
              "{Q9}": q.get("Q9", ""), "{Q10}": q.get("Q10", ""), "{Q22}": q.get("Q22", "")}
    for k, v in values.items():
        if "\n" in v:
            raise SignRefusal("the value for %s must be one line" % k)
        text = text.replace(k, v)
    return text


# ==================================================================================================== planning
class Plan(object):
    def __init__(self):
        self.changes = []          # (file, where, old, new)
        self.notes = []
        self.warnings = []

    def add(self, f, where, old, new):
        self.changes.append((f, where, old, new))


def block_range(lines, key, indent, start=0, end=None):
    """[first, last) of the block of '<indent spaces>key:' (its own line included)."""
    end = len(lines) if end is None else end
    head = " " * indent + key + ":"
    first = None
    for i in range(start, end):
        if lines[i] == head or lines[i].startswith(head + " "):
            if first is not None:
                raise SignRefusal("key %r appears twice at indent %d" % (key, indent))
            first = i
    if first is None:
        raise SignRefusal("key %r not found at indent %d" % (key, indent))
    j = first + 1
    while j < end and (not lines[j].strip() or lines[j].startswith(" " * (indent + 1))):
        j += 1
    return first, j


def field_line(lines, first, last, key, indent):
    hits = [i for i in range(first, last) if lines[i].startswith(" " * indent + key + ":")]
    if len(hits) != 1:
        raise SignRefusal("expected one '%s:' line at indent %d in lines %d-%d, found %d" % (key, indent, first + 1, last, len(hits)))
    i = hits[0]
    value = yaml.safe_load(lines[i].strip())[key]
    return i, value


def apply_text_edits(plan, texts, ans):
    proposed = {p[0]: p for p in PROPOSED_TEXT_EDITS}
    for e in ans.edits:
        if e.file not in texts:
            raise SignRefusal("text edit %s names %s, not a file of %s" % (e.id, e.file, DRAFT))
        p = proposed.get(e.id)
        if p is None or (p[1], p[2], p[3]) != (e.file, e.old, e.new):
            plan.warnings.append("text edit %s is NOT the tool's proposal (the owner's file changed or added it): "
                                 "read it below" % e.id)
        n = texts[e.file].count(e.old)
        if n != 1:
            raise SignRefusal("text edit %s: its 'old' text occurs %d times in %s/%s (must be exactly once): %r"
                              % (e.id, n, DRAFT, e.file, short(e.old, 120)))
        new = fill(e.new, ans)
        texts[e.file] = texts[e.file].replace(e.old, new)
        plan.add(e.file, "text edit %s" % e.id, e.old, new)
    missing = sorted(set(proposed) - {e.id for e in ans.edits})
    if missing:
        plan.warnings.append("the answers file leaves out the proposed text edits %s; the stale-text scan decides "
                             "whether the package is still clean" % missing)


def edit_dataset(plan, texts, ans, E):
    lines = texts["dataset.yaml"].split("\n")
    marker = E.DRAFT_MARKER
    for key, value in (("name", SIGNED), ("version", ans.version), ("owner", ans.owner),
                       ("description", fill(ans.description, ans))):
        value = one_line(value, "dataset.%s" % key)
        if key in ("version", "description") and marker in value:
            raise SignRefusal("dataset.%s contains the engine's draft marker %r" % (key, marker))
        if key == "version" and "draft" in value.lower():
            raise SignRefusal("dataset.version %r still says draft" % value)
        hits = [i for i, l in enumerate(lines) if l.startswith(key + ":")]
        if len(hits) != 1:
            raise SignRefusal("dataset.yaml: expected one top-level '%s:' line, found %d" % (key, len(hits)))
        i = hits[0]
        new = "%s: %s" % (key, value if key == "name" else sq(value))
        plan.add("dataset.yaml", "line %d (%s)" % (i + 1, key), lines[i], new)
        lines[i] = new
    texts["dataset.yaml"] = "\n".join(lines)


def edit_catalog(plan, texts, ans):
    lines = texts["catalog.yaml"].split("\n")
    cols = block_range(lines, "columns", 0)
    first, last = block_range(lines, TARGET, 2, cols[0] + 1, cols[1])
    for k in ("fact_status", "reviewed_by", "date"):
        if any(lines[i].startswith("    %s:" % k) for i in range(first, last)):
            raise SignRefusal("catalog.yaml %s already has %s: the draft is not the expected one" % (TARGET, k))
    i, prov = field_line(lines, first, last, "provenance", 4)
    stamp = "; facts signed by the owner %s (%s, ruling %s, %s)" % (
        ans.ruling.date, ans.target_fact_status, ans.ruling.id, ans.ruling.file)
    new_prov = "    provenance: %s" % sq(str(prov) + stamp)
    added = ["    fact_status: %s" % ans.target_fact_status, "    reviewed_by: owner", "    date: %s" % sq(ans.ruling.date)]
    plan.add("catalog.yaml", "%s (line %d)" % (TARGET, i + 1), lines[i], "\n".join(added + [new_prov]))
    lines[i:i + 1] = added + [new_prov]
    texts["catalog.yaml"] = "\n".join(lines)
    if ans.target_fact_status != "verified":
        plan.warnings.append("**ATTENTION** target fact_status 'assumed': a table package's G-FACTS passes only on "
                             "'verified' (treeroute/check/table.py:131-136), so the coral freeze will refuse (G-FACTS)")


def edit_ban(plan, texts, ans, E, draft_ban):
    lines = texts["ban.yaml"].split("\n")
    vr = block_range(lines, "verdicts", 0)
    note = "signed by the owner %s (ruling %s)" % (ans.ruling.date, ans.ruling.id)
    for col in draft_ban:
        first, last = block_range(lines, col, 2, vr[0] + 1, vr[1])
        if ans.verdict_answers.get(col) == "change":
            ch = ans.changes[col]
            new_v = {"verdict": word(ch["verdict"]), "reason": one_line(word(ch["reason"]), "ban.changes.%s.reason" % col)}
            try:
                E.S.Verdict.model_validate(dict(new_v, evidence="x"))
            except Exception as exc:
                raise SignRefusal("ban.changes.%s: %s" % (col, exc))
            if new_v["verdict"] == "freeze":
                raise SignRefusal("ban.changes.%s: a 'freeze' verdict is refused for tables (R9; SPEC 1.4)" % col)
            for key in ("verdict", "reason"):
                i, old = field_line(lines, first, last, key, 4)
                new = "    %s: %s" % (key, new_v[key] if key == "verdict" else sq(new_v[key]))
                if str(old) != new_v[key]:
                    plan.add("ban.yaml", "%s.%s (line %d)" % (col, key, i + 1), lines[i], new)
                    lines[i] = new
            i, ev = field_line(lines, first, last, "evidence", 4)
            was = draft_ban[col]
            # close the drafted 'unsigned (Qn)' phrase (the stale-text scan refuses it) and the '(owner item)' note
            # of the old reason quoted below (the freeze's F-BAN-OPEN scan matches it)
            ev = re.sub(r"\bunsigned \((Q\d+)\)", lambda m: "%s answered by the owner %s (ruling %s)" % (
                m.group(1), ans.ruling.date, ans.ruling.id), str(ev))
            was_reason = str(was["reason"]).replace(OWNER_ITEM_TEXT, "(owner-item note settled)")
            new = "    evidence: %s" % sq("%s | changed by the owner %s (ruling %s): was %s/%s; %s" % (
                ev, ans.ruling.date, ans.ruling.id, was["verdict"], was_reason,
                one_line(word(ans.changes[col]["note"]), "ban.changes.%s.note" % col)))
            plan.add("ban.yaml", "%s.evidence (line %d)" % (col, i + 1), lines[i], new)
            lines[i] = new
            continue
        i, ev = field_line(lines, first, last, "evidence", 4)
        if ev is not None and re.search(r"\bunsigned \((Q\d+)\)", str(ev)):
            new_ev = re.sub(r"\bunsigned \((Q\d+)\)", lambda m: "%s %s" % (m.group(1), note), str(ev))
            new = "    evidence: %s" % sq(new_ev)
            plan.add("ban.yaml", "%s.evidence (line %d)" % (col, i + 1), lines[i], new)
            lines[i] = new
    # the '(owner item)' note on ctx_mmm (F-BAN-OPEN)
    first, last = block_range(lines, OWNER_ITEM_COLUMN, 2, vr[0] + 1, vr[1])
    i, reason = field_line(lines, first, last, "reason", 4)
    if ans.owner_item == "accept":
        if OWNER_ITEM_TEXT not in str(reason):
            raise SignRefusal("ban.yaml %s.reason has no %r note to settle" % (OWNER_ITEM_COLUMN, OWNER_ITEM_TEXT))
        new = "    reason: %s" % sq(str(reason).replace(OWNER_ITEM_TEXT, "(accepted by the owner %s, ruling %s)"
                                                       % (ans.ruling.date, ans.ruling.id)))
        plan.add("ban.yaml", "%s.reason (line %d)" % (OWNER_ITEM_COLUMN, i + 1), lines[i], new)
        lines[i] = new
    elif OWNER_ITEM_TEXT in str(reason):
        raise SignRefusal("ban.yaml %s.reason still holds %r after the owner's change" % (OWNER_ITEM_COLUMN,
                                                                                           OWNER_ITEM_TEXT))
    text = "\n".join(lines)
    # the header's Counts line
    final = yaml.safe_load(text)["verdicts"]
    counts = {}
    for v in final.values():
        k = v["verdict"] + (":" + v["reason"] if v["verdict"] == "ban" else "")
        counts[k] = counts.get(k, 0) + 1
    want = "Counts: " + ", ".join("%s %d" % (k, counts[k]) for k in sorted(counts)) + "."
    m = re.search(r"Counts: [^\n]*?\.(?=\n)", text)
    if not m:
        raise SignRefusal("ban.yaml header has no 'Counts: ...' line")
    if m.group(0) != want:
        plan.add("ban.yaml", "header Counts", m.group(0), want)
        text = text[:m.start()] + want + text[m.end():]
        plan.warnings.append("verdict counts changed: ingest/README.md:27 ('keep 65 ...') is now stale; edit it by a "
                             "text edit")
    texts["ban.yaml"] = text


def edit_exceptions(plan, texts, ans, E):
    lines = texts["exceptions.yaml"].split("\n")
    starts = [i for i, l in enumerate(lines) if l.startswith("  - kind:")]
    parsed = parse_yaml(E, texts["exceptions.yaml"], "exceptions.yaml")["entries"]
    if len(starts) != len(parsed):
        raise SignRefusal("exceptions.yaml: %d '  - kind:' lines but %d entries" % (len(starts), len(parsed)))
    bounds = starts + [len(lines)]
    for n, entry in enumerate(parsed):
        a = ans.exc_answers.get(n)
        signed_now = E.exception_signed(SimpleNamespace(owner=entry["owner"]))
        if a == "keep":
            if not signed_now:
                raise SignRefusal("exceptions entry %d: 'keep' but its owner field is not signed (%r); answer sign"
                                  % (n, short(entry["owner"], 80)))
            continue
        i, owner = field_line(lines, bounds[n], bounds[n + 1], "owner", 4)
        basis = re.sub(r"^\s*UNSIGNED\s*--\s*basis:\s*", "", str(owner))
        if basis == str(owner) and not signed_now:
            raise SignRefusal("exceptions entry %d: owner field %r is neither 'UNSIGNED -- basis: ...' nor signed"
                              % (n, short(owner, 80)))
        new_owner = "owner -- signed by the owner %s (ruling %s, %s, coral sign-off E%d); basis: %s" % (
            ans.ruling.date, ans.ruling.id, ans.ruling.file, n, basis)
        new = "    owner: %s" % sq(new_owner)
        plan.add("exceptions.yaml", "entry %d owner (line %d)" % (n, i + 1), lines[i], new)
        lines[i] = new
    texts["exceptions.yaml"] = "\n".join(lines)


def edit_audit(plan, texts, ans):
    lines = texts["AUDIT_CHECKLIST.md"].split("\n")
    for n in range(1, AUDIT_ROWS + 1):
        hits = [i for i, l in enumerate(lines) if l.startswith("| %d | " % n)]
        if len(hits) != 1 or not lines[hits[0]].rstrip().endswith("| [ ] |"):
            raise SignRefusal("AUDIT_CHECKLIST.md: row %d is not one open '| [ ] |' row" % n)
        i = hits[0]
        new = lines[i].rstrip()[:-len("| [ ] |")] + "| [x] |"
        plan.add("AUDIT_CHECKLIST.md", "row A%d (line %d)" % (n, i + 1), "...| [ ] |", "...| [x] |")
        lines[i] = new
    text = "\n".join(lines)
    if text.count(AUDIT_TINY_LINE) != 1:
        raise SignRefusal("AUDIT_CHECKLIST.md: the tiny-build evidence sentence is not there exactly once")
    line = one_line(fill(ans.full_build_line, ans), "audit_checklist.full_build_line")
    text = text.replace(AUDIT_TINY_LINE, AUDIT_TINY_LINE + "\n" + line)
    plan.add("AUDIT_CHECKLIST.md", "section B evidence", AUDIT_TINY_LINE, AUDIT_TINY_LINE + " / " + line)
    if text.count(AUDIT_SIGNATURE) != 1:
        raise SignRefusal("AUDIT_CHECKLIST.md: the blank signature line is not there exactly once")
    sig = "Signed: %s (owner; U2 statement and sections A and B, ruling %s)   Date: %s" % (
        one_line(ans.signer, "signer"), ans.ruling.id, ans.ruling.date)
    text = text.replace(AUDIT_SIGNATURE, sig)
    plan.add("AUDIT_CHECKLIST.md", "signature", AUDIT_SIGNATURE, sig)
    texts["AUDIT_CHECKLIST.md"] = text


# ==================================================================================================== checks
def ydiff(a, b, path=()):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                out.append(path + (k,))
            else:
                out += ydiff(a[k], b[k], path + (k,))
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += ydiff(x, y, path + (i,))
        return out
    return [] if a == b else [path]


def check_result(plan, E, draft_texts, texts, after_edits, ans, draft_ban):
    # 1. every YAML file passes the engine schema; only planned fields changed
    parsed, models = {}, {}
    for name in E.S.PACKAGE_FILE_MODELS:
        parsed[name], models[name] = validate(E, name, texts[name])
    before = {n: parse_yaml(E, draft_texts[n], n) for n in E.S.PACKAGE_FILE_MODELS}
    mid = {n: parse_yaml(E, after_edits[n], n) for n in E.S.PACKAGE_FILE_MODELS}
    for n in E.S.PACKAGE_FILE_MODELS:              # text edits: comments only, except the allowed exception fields
        for p in ydiff(before[n], mid[n]):
            ok = n in CONTENT_EDIT_FIELDS and len(p) == 3 and p[0] == "entries" and p[2] in CONTENT_EDIT_FIELDS[n]
            if not ok:
                raise SignRefusal("a text edit changed parsed content of %s at %s (text edits may change comments "
                                  "only, or exceptions.yaml decision/reason/owner)" % (n, ".".join(map(str, p))))
    allowed = {
        "dataset.yaml": lambda p: p[0] in ("name", "version", "owner", "description") and len(p) == 1,
        "catalog.yaml": lambda p: p[:2] == ("columns", TARGET) and len(p) == 3
        and p[2] in ("fact_status", "reviewed_by", "date", "provenance"),
        "ban.yaml": lambda p: p[0] == "verdicts" and len(p) == 3 and p[2] in ("verdict", "reason", "evidence"),
        "exceptions.yaml": lambda p: p[0] == "entries" and len(p) == 3 and p[2] in ("owner", "decision", "reason"),
        "split.yaml": lambda p: False,
    }
    for n in E.S.PACKAGE_FILE_MODELS:
        for p in ydiff(mid[n], parsed[n]):
            if not allowed[n](p):
                raise SignRefusal("%s changed outside the planned fields at %s" % (n, ".".join(map(str, p))))
    # 2. closed world and split
    if set(parsed["ban.yaml"]["verdicts"]) != set(draft_ban):
        raise SignRefusal("the verdict columns changed")
    if len(models["split.yaml"].excluded) != EXPECTED_EXCLUDED:
        raise SignRefusal("split.yaml excludes %d groups, not the %d of V5 (V6 b, ruling W1)"
                          % (len(models["split.yaml"].excluded), EXPECTED_EXCLUDED))
    # 3. the engine's own reads
    st = E.draft_status(SimpleNamespace(ban=models["ban.yaml"], dataset=models["dataset.yaml"]))
    if st.is_draft:
        raise SignRefusal("the engine still reads a DRAFT: %r" % (st.record(),))
    plan.notes.append("engine draft_status of the signed package: is_draft=False")
    marks = [(no, l.strip()) for no, l in enumerate(texts["ban.yaml"].split("\n"), 1) if E.OPEN_DECISION.search(l)]
    if marks:
        raise SignRefusal("ban.yaml still matches the freeze's F-BAN-OPEN scan: %s" % marks[:5])
    unreviewed = [c for c, v in models["ban.yaml"].verdicts.items() if v.verdict == "keep_unreviewed"]
    if unreviewed:
        raise SignRefusal("keep_unreviewed verdicts remain (F-BAN-OPEN): %s" % unreviewed)
    plan.notes.append("F-BAN-OPEN scan (treeroute_report/freeze.py OPEN_DECISION) on the signed ban.yaml: 0 lines")
    unsigned = [i for i, e in enumerate(models["exceptions.yaml"].entries) if not E.exception_signed(e)]
    if unsigned:
        raise SignRefusal("exceptions entries still unsigned (guards.exception_signed): %s" % unsigned)
    plan.notes.append("exceptions.yaml: all %d entries signed (guards.exception_signed)"
                      % len(models["exceptions.yaml"].entries))
    tf = models["catalog.yaml"].columns[TARGET].fact_status
    plan.notes.append("target %s fact_status %s (table G-FACTS passes only on 'verified')" % (TARGET, tf))
    # 4. stale text
    stale = []
    for f in STALE_FILES:
        for no, l in enumerate(texts[f].split("\n"), 1):
            for rx, pat in STALE:
                if rx.search(l):
                    stale.append("%s:%d [%s] %s" % (f, no, pat, short(l.strip(), 140)))
    if stale:
        raise SignRefusal("stale DRAFT/UNSIGNED text remains (add or fix a text edit):\n  " + "\n  ".join(stale))
    plan.notes.append("stale-text scan over %d files: clean" % len(STALE_FILES))
    for ph in PLACEHOLDERS:
        for f in texts:
            if ph in texts[f]:
                raise SignRefusal("placeholder %s left in %s" % (ph, f))


# ==================================================================================================== main steps
def build(answers_path, draft_fp_expected):
    E = engine_modules()
    draft_root = DATASETS / DRAFT
    if not draft_root.is_dir():
        raise SignRefusal("%s does not exist" % draft_root)
    files = read_package(draft_root)
    fp, _ = fingerprint(E, files)
    if fp != draft_fp_expected:
        raise SignRefusal("coral_draft's fingerprint is %s..., not %s... (the GREEN deep check %s); it changed since "
                          "the check: re-check it, then pass --draft-fingerprint %s" % (fp[:16], draft_fp_expected[:16],
                                                                                         CHECK_REPORT, fp))
    texts, crlf = {}, {}
    for rel in STALE_FILES:
        if rel not in files:
            raise SignRefusal("%s/%s is missing" % (DRAFT, rel))
        texts[rel], crlf[rel] = to_text(files[rel], rel)
    draft_texts = dict(texts)
    draft_ban = parse_yaml(E, texts["ban.yaml"], "ban.yaml")["verdicts"]
    draft_exc = parse_yaml(E, texts["exceptions.yaml"], "exceptions.yaml")["entries"]
    ans, missing, problems = load_answers(answers_path, draft_ban, draft_exc)
    if missing or problems:
        msg = []
        if missing:
            msg.append("%d item(s) UNANSWERED:\n  %s" % (len(missing), "\n  ".join(missing)))
        if problems:
            msg.append("%d problem(s):\n  %s" % (len(problems), "\n  ".join(problems)))
        raise SignRefusal("nothing planned, nothing written. " + "\n".join(msg))
    plan = Plan()
    apply_text_edits(plan, texts, ans)
    after_edits = dict(texts)
    edit_dataset(plan, texts, ans, E)
    edit_catalog(plan, texts, ans)
    edit_ban(plan, texts, ans, E, draft_ban)
    edit_exceptions(plan, texts, ans, E)
    edit_audit(plan, texts, ans)
    check_result(plan, E, draft_texts, texts, after_edits, ans, draft_ban)
    new_files = dict(files)
    for rel in texts:
        new_files[rel] = to_bytes(texts[rel], crlf[rel])
    new_fp, new_hashes = fingerprint(E, new_files)
    _, old_hashes = fingerprint(E, files)
    return SimpleNamespace(E=E, ans=ans, plan=plan, files=files, new_files=new_files, draft_fp=fp, new_fp=new_fp,
                           old_hashes=old_hashes, new_hashes=new_hashes)


def follow_ups(ans):
    out = []
    if ans.matrix == "approve":
        out.append("matrix_dir APPROVED: engine-test task: add 'matrix_dir' to weight_model_for_cut's approved "
                   "parameters in tests/test_layer_shapes.py:57 (the old failing test; prereg section 10, section 12 "
                   "item 2). Not written by this tool.")
    else:
        out.append("matrix_dir REJECTED: an engine change removes the parameter from fit/weights.py:526 and its "
                   "callers (ruling R RAM tactics); needs its own no-op proof. Not written by this tool.")
    cg = ans.continuity or []
    out.append("continuity: add to treeroute_report/continuity_groups.yaml (outside the package; adds report-tooling "
               "drift to the four grid locks, disclosed):\n      coral:\n        label: continuity, not a replication\n"
               "        source: \"none: no legacy coral number is comparable (Part 458 pool leak); owner %s (ruling %s)\"\n"
               "        n_groups: %d\n        continuity_groups:%s"
               % (ans.ruling.date, ans.ruling.id, len(cg), " []" if not cg else "".join("\n          - " + g for g in cg)))
    out.append("pre-registration (D:/treeroute/coral_build/PREREGISTRATION_DRAFT_coral.md): remove the markers of "
               "section 12 items 2, 3, 5 and 7 by hand, and item 8 once the report-script SHA-256 lines are filled in "
               "section 6.2; record the coral question answers in item 7; the section 13 signatures are the "
               "owner's, by hand.")
    for q, a in sorted(ans.q_answers.items(), key=lambda kv: int(kv[0][1:])):
        if a and a != "confirm":
            out.append("%s answered differently: write it into prereg section 12 item 7 and check it against the "
                       "signed rules (U6)" % q)
    out.append("then, in this order, from the engine folder: py -3.9 -m treeroute check datasets/coral ; "
               "py -3.9 -m treeroute check datasets/coral --deep ; py -3.9 -m treeroute plan datasets/coral (alone, "
               "heavy). Any later package edit invalidates F-CHECK-MATCH and F-PLAN.")
    out.append("report-only scripts (prereg section 12 item 8): D:/treeroute/coral_build/report_scripts/coral_report.py; "
               "its SHA-256 must equal the one in prereg section 6.2 (re-hash after any change, e.g. the flattening-"
               "guard edge).")
    return out


def report(b, dry, full):
    ans, plan = b.ans, b.plan
    print("=" * 100)
    print("make_signed_coral: %s" % ("DRY RUN (nothing written)" if dry else "APPLY"))
    print("ruling %s (%s, %s); signer %s" % (ans.ruling.id, ans.ruling.file, ans.ruling.date, ans.signer))
    print("source %s  fingerprint %s (= the GREEN deep check)" % (DATASETS / DRAFT, b.draft_fp))
    print("target %s  predicted fingerprint %s" % (DATASETS / SIGNED, b.new_fp))
    for w in plan.warnings:
        print("WARNING: " + w)
    for q in BAN_QUESTIONS:
        a = ans.q_answers.get(q)
        if a and a != "confirm":
            print("WARNING: %s answered %r (not 'confirm'); ban.changes holds %d change(s); acknowledge_q_answers %r. "
                  "Check every verdict below against that answer." % (q, short(a, 60), len(ans.changes),
                                                                       ans.ack_q or ""))
    by_file = {}
    for f, where, old, new in plan.changes:
        by_file.setdefault(f, []).append((where, old, new))
    print("-" * 100)
    print("CHANGES: %d in %d files" % (len(plan.changes), len(by_file)))
    n = 150 if not full else 10 ** 6
    for f in sorted(by_file):
        print("[%s] %d change(s)" % (f, len(by_file[f])))
        for where, old, new in by_file[f]:
            print("  - %s" % where)
            print("      old: %s" % short(old, n))
            print("      new: %s" % short(new, n))
    same = sorted(r for r in b.files if b.files[r] == b.new_files[r])
    print("unchanged files (byte for byte): %s" % ", ".join(same))
    print("-" * 100)
    for note in plan.notes:
        print("CHECK: " + note)
    print("coral questions: %s" % "; ".join("%s %s" % (q, "confirm" if a == "confirm" else "ANSWERED: " + short(a, 60))
                                           for q, a in sorted(ans.q_answers.items(), key=lambda kv: int(kv[0][1:]))))
    print("-" * 100)
    print("FOLLOW-UPS (not done by this tool):")
    for f in follow_ups(ans):
        print("  * " + f)


def do_apply(b, answers_path):
    ans = b.ans
    ap = Path(answers_path).resolve()
    if str(ap).lower().startswith(str(DRYRUN_DIR.resolve()).lower()):
        raise SignRefusal("--apply refused: the answers file is a dry-run copy (tools/_dryrun)")
    dummy = [k for k, v in (("ruling.id", ans.ruling.id), ("signer", ans.signer), ("dataset.owner", ans.owner))
             if "DUMMY" in str(v).upper()]
    if dummy:
        raise SignRefusal("--apply refused: DUMMY in %s (a dry-run answers file)" % ", ".join(dummy))
    if ans.ruling.date > datetime.date.today().isoformat():
        raise SignRefusal("--apply refused: ruling.date %s is after today (%s); the dummy file uses 2099-01-01"
                          % (ans.ruling.date, datetime.date.today().isoformat()))
    rfile = (ENGINE / ans.ruling.file) if not Path(ans.ruling.file).is_absolute() else Path(ans.ruling.file)
    if not rfile.is_file():
        raise SignRefusal("--apply refused: the ruling file %s does not exist" % rfile)
    if not re.search(r"^## %s\. " % re.escape(ans.ruling.id), rfile.read_text(encoding="utf-8"), re.M):
        raise SignRefusal("--apply refused: %s has no section '## %s. ...': the owner's ruling must be written first"
                          % (rfile, ans.ruling.id))
    target = DATASETS / SIGNED
    if target.exists():
        raise SignRefusal("--apply refused: %s exists (never overwritten; move it aside first)" % target)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    staging = DATASETS / ("_staging_coral_%s" % stamp)
    aside = DATASETS / ("_moved_signed_coral_%s" % stamp)
    roots = protected_roots()
    for p in (target, staging, aside, RECORDS):
        if under_protected(p, roots):
            raise SignRefusal("--apply refused: %s lies under a protected root" % p)
    if staging.exists() or aside.exists():
        raise SignRefusal("--apply refused: %s or %s exists" % (staging, aside))
    # the draft must still be the one planned
    if read_package(DATASETS / DRAFT) != b.files:
        raise SignRefusal("--apply refused: coral_draft changed while planning; run again")
    staging.mkdir()
    try:
        for rel, data in sorted(b.new_files.items()):
            p = staging / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(str(p), "xb") as fh:
                fh.write(data)
        if read_package(staging) != b.new_files:
            raise SignRefusal("the staged files differ from the plan")
        loaded = b.E.L.load_package(staging)
        if loaded.fingerprint != b.new_fp:
            raise SignRefusal("the engine's fingerprint of the staged package is %s, not the planned %s"
                              % (loaded.fingerprint, b.new_fp))
        if b.E.draft_status(loaded).is_draft:
            raise SignRefusal("the engine reads the staged package as a DRAFT")
        os.rename(str(staging), str(target))
    except Exception:
        if staging.exists():
            os.rename(str(staging), str(aside))
            print("REFUSED after staging: the staged folder was moved to %s (nothing deleted)" % aside)
        raise
    loaded = b.E.L.load_package(target)
    if loaded.fingerprint != b.new_fp:
        raise SignRefusal("datasets/coral fingerprint %s differs from the plan %s: inspect it (left in place)"
                          % (loaded.fingerprint, b.new_fp))
    RECORDS.mkdir(exist_ok=True)
    raw = Path(answers_path).read_bytes()
    copy = RECORDS / ("coral_signoff_answers_%s.yaml" % stamp)
    with open(str(copy), "xb") as fh:
        fh.write(raw)
    record = {"made": stamp, "tool": str(Path(__file__).resolve()),
              "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "answers": str(ap), "answers_sha256": hashlib.sha256(raw).hexdigest(), "answers_copy": str(copy),
              "ruling": vars(ans.ruling), "source": str(DATASETS / DRAFT), "source_fingerprint": b.draft_fp,
              "target": str(target), "target_fingerprint": loaded.fingerprint,
              "files_before": b.old_hashes, "files_after": b.new_hashes,
              "changes": [{"file": f, "where": w, "old": o, "new": n} for f, w, o, n in b.plan.changes],
              "coral_questions": ans.q_answers, "matrix_dir": ans.matrix, "continuity_groups": ans.continuity,
              "v6_choice": ans.v6, "protected_root_confirm": ans.root_ok, "follow_ups": follow_ups(ans)}
    rec = RECORDS / ("coral_signoff_record_%s.json" % stamp)
    with open(str(rec), "x", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1, sort_keys=True)
    print("WRITTEN: %s (engine fingerprint %s); record %s" % (target, loaded.fingerprint, rec))


# ==================================================================================================== template
def write_template(out):
    out = Path(out).resolve()
    if out.exists():
        raise SignRefusal("%s exists (never overwritten)" % out)
    if str(out).lower().startswith(str(ENGINE).lower()):
        raise SignRefusal("the template is not written inside the engine folder")
    E = engine_modules()
    files = read_package(DATASETS / DRAFT)
    ban = parse_yaml(E, to_text(files["ban.yaml"], "ban.yaml")[0], "ban.yaml")["verdicts"]
    exc = parse_yaml(E, to_text(files["exceptions.yaml"], "exceptions.yaml")[0], "exceptions.yaml")["entries"]
    L = []
    w = L.append
    w("# coral sign-off answers -- TEMPLATE (written by D:/treeroute/coral_build/tools/make_signed_coral.py template).")
    w("# EVERY value '' is UNANSWERED: the tool refuses while any one is empty. Copy this file, fill the copy, then run")
    w("#   py -3.9 -B D:/treeroute/coral_build/tools/make_signed_coral.py sign <copy>            (dry run: prints every change)")
    w("#   py -3.9 -B D:/treeroute/coral_build/tools/make_signed_coral.py sign <copy> --apply --expect-fingerprint <fp>")
    w("#       (writes datasets/coral; <fp> = the 'predicted fingerprint' line of the dry run you read)")
    w("# Source: engine/datasets/coral_draft (fingerprint %s..., the GREEN deep check)." % CHECKED_DRAFT_FINGERPRINT[:16])
    w("# Words in comments: 'drafted' = what coral_draft says today. Nothing here is answered for the owner.")
    w("")
    w("# The owner's ruling that signs coral. Write it in OWNER_RULINGS_2026-10-06.md first ('## <id>. ...'); --apply checks it.")
    w("ruling:")
    w("  id: ''        # e.g. X")
    w("  file: ''      # e.g. OWNER_RULINGS_2026-10-06.md (relative to the engine folder)")
    w("  date: ''      # YYYY-MM-DD; also the signature date of every item")
    w("signer: ''      # the name written on the AUDIT_CHECKLIST.md signature line")
    w("")
    w("# V6: ruling W1 (2026-10-20) chose (b); coral_draft carries the (b) split. Write b to confirm. (a) is refused here.")
    w("v6_choice: ''")
    w("# Morning sheet B3: D:/treeroute/coral_build/coral_store is in protected_roots.txt:8 (added by the session). yes | no")
    w("protected_root_confirm: ''")
    w("# Morning sheet B1 (recommended: approve): matrix_dir in weight_model_for_cut's approved parameters. approve | reject")
    w("matrix_dir: ''")
    w("# Morning sheet B2 (recommended: empty): coral's treeroute_report/continuity_groups.yaml entry. empty | [group, ...]")
    w("continuity_groups: ''")
    w("")
    w("# dataset.yaml (drafted: name coral_draft, version '0.1.0-draft', owner 'UNSIGNED -- DRAFT ...', description 'DRAFT -- ...').")
    w("dataset:")
    w("  version: ''       # e.g. 0.1.0 (must not say draft)")
    w("  owner: ''         # the owner field (the grid packages still read 'UNSIGNED -- the project owner fills in the name')")
    w("  description: ''   # 'proposed' takes the text below; or write your own one line")
    w("  # proposed: %s" % DESCRIPTION_PROPOSED)
    w("")
    w("# The target's facts (catalog.yaml pct_bleached; G-FACTS). verified | assumed.")
    w("# NOTE: a table package's G-FACTS passes ONLY on 'verified' (treeroute/check/table.py:131-136); 'assumed' blocks the freeze.")
    w("target_facts:")
    w("  fact_status: ''")
    w("")
    w("# ban.yaml: 76 verdicts. all: sign_all (every verdict answered blank below is signed as drafted) | per_column.")
    w("# Per column: sign | change (then ban.changes.<col>: {verdict, reason, note}). 'freeze' is refused for tables.")
    w("ban:")
    w("  all: ''")
    w("  # ban.yaml:40 ctx_mmm '(owner item)': absolute temperature kept as penalised router context, a disclosed departure.")
    w("  owner_item_ctx_mmm: ''   # accept | change")
    w("  verdicts:")
    for col, v in ban.items():
        w("    %s: {now: %s, answer: ''}" % (col, sq("%s/%s" % (v["verdict"], short(v["reason"], 70)))))
    w("  changes: {}")
    w("")
    w("# exceptions.yaml: %d entries. sign = stamp 'owner -- signed by the owner <date> (ruling ...); basis: ...';" % len(exc))
    w("# keep = leave an owner field that already names a ruling (only allowed when the engine already reads it signed).")
    w("exceptions:")
    w("  entries:")
    for i, e in enumerate(exc):
        about = "%s %s: %s" % (e["kind"], e.get("column") or e.get("check"), e["decision"])
        w("    %d: {about: %s, owner_now: %s, answer: ''}" % (i, sq(short(about, 90)), sq(short(e["owner"], 90))))
    w("")
    w("# AUDIT_CHECKLIST.md section A: every box must be ticked (tick) before the signature.")
    w("audit_checklist:")
    for n in range(1, AUDIT_ROWS + 1):
        w("  A%d: ''" % n)
    w("  # Section B evidence for the FULL tables (morning sheet C; prereg 3.2). approve | your own one line.")
    w("  full_build_line: ''")
    w("  # proposed: %s" % FULL_BUILD_LINE_PROPOSED)
    w("# Ruling U2: 'I vouch for the feature timing of every row of every lead file' (AUDIT_CHECKLIST.md section B). yes")
    w("u2_vouch: ''")
    w("")
    w("# The coral question sheet (prereg section 12 item 7). confirm = the reading shown; any other text = your answer.")
    w("# Q9, Q10 and Q22 are written into the signed ban.yaml header and decide verdicts: an answer other than confirm")
    w("# needs the verdict changes under ban.changes, or acknowledge_q_answers: yes (signs the drafted verdicts anyway).")
    w("coral_questions:")
    for q, topic, reading in CORAL_QUESTIONS:
        w("  %s: {topic: %s, reading: %s, answer: ''}" % (q, sq(topic), sq(reading)))
    w("acknowledge_q_answers: ''   # yes | no | blank; read only when Q9, Q10 or Q22 is not confirm")
    w("")
    w("# PROSE EDITS the agent PROPOSES (every DRAFT/UNSIGNED/stale sentence of coral_draft). Read them in the dry run.")
    w("# yes approves the list below as written. Placeholders {date} {ruling_id} ... are filled by the tool.")
    w("text_edits_approve: ''")
    w("text_edits:")
    for eid, f, old, new in PROPOSED_TEXT_EDITS:
        w("  - id: %s" % eid)
        w("    file: %s" % f)
        w("    old: |-")
        for l in old.split("\n"):
            w("      " + l)
        w("    new: |-")
        for l in new.split("\n"):
            w("      " + l)
    text = "\n".join(L) + "\n"
    yaml.safe_load(text)                   # the template must parse
    with open(str(out), "x", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("template written: %s (%d verdicts, %d exception entries, %d questions, %d text edits)"
          % (out, len(ban), len(exc), len(CORAL_QUESTIONS), len(PROPOSED_TEXT_EDITS)))


def main(argv=None):
    ap = argparse.ArgumentParser(description="make datasets/coral from datasets/coral_draft (dry run by default)")
    sub = ap.add_subparsers(dest="cmd")
    t = sub.add_parser("template")
    t.add_argument("--out", required=True)
    s = sub.add_parser("sign")
    s.add_argument("answers")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", help="the default: plan, validate, print; write nothing")
    g.add_argument("--apply", action="store_true", help="write datasets/coral (and the record)")
    s.add_argument("--draft-fingerprint", default=CHECKED_DRAFT_FINGERPRINT)
    s.add_argument("--expect-fingerprint", default=None,
                   help="required with --apply: the 'predicted fingerprint' of the dry run the owner read")
    s.add_argument("--full", action="store_true", help="print every change in full (no truncation)")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "template":
            write_template(a.out)
            return 0
        if a.cmd != "sign":
            ap.print_help()
            return 2
        if a.apply and not a.expect_fingerprint:
            raise SignRefusal("--apply needs --expect-fingerprint <the predicted fingerprint printed by the dry run "
                              "you read>, so that what is written is what you approved; nothing planned, nothing "
                              "written")
        b = build(a.answers, a.draft_fingerprint)
        report(b, dry=not a.apply, full=a.full)
        if a.apply:
            if b.new_fp != a.expect_fingerprint.strip().lower():
                raise SignRefusal("--apply refused: the plan's fingerprint %s is not the --expect-fingerprint %s; "
                                  "the answers or coral_draft changed since that dry run: read the dry run again"
                                  % (b.new_fp, a.expect_fingerprint))
            do_apply(b, a.answers)
        else:
            print("DRY RUN: nothing was written. To write %s, re-run with --apply --expect-fingerprint %s"
                  % (DATASETS / SIGNED, b.new_fp))
        return 0
    except SignRefusal as exc:
        print("REFUSED: %s" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
