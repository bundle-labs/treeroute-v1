"""Write the owner's freeze sign-off answers into the dataset packages (dataset tool).

    cd "C:\\Users\\<user>\\Desktop\\data set for reserch paper\\engine"
    py -3.9 datasets/_tools/apply_signoff.py <answers.yaml>             # DRY RUN (default): every planned edit, counted
    py -3.9 datasets/_tools/apply_signoff.py <answers.yaml> --apply     # write; every edited file's old copy moved aside

Options: --engine <engine folder> (default: the engine folder this script sits in), --packages <names> (default: the
answers file's 'packages'), --aside-root <folder> (default: <engine>/datasets/_moved_signoff_<UTC stamp>),
--summary-json <file> (the plan as JSON: counts per group and package), --brief (counts only; by default the
dry run also lists every planned edit, file by file and group by group).

WHAT IT IS FOR. engine/FREEZE_SIGNOFF_SHEET.md lists every item that blocks the freeze, in groups S1, S2, ... The owner
answers them. The owner, or an agent AFTER the owner has answered, copies the answers into a copy of
datasets/_tools/signoff_answers_TEMPLATE.yaml. This script then writes exactly the edits those answers imply:
  S1-S4  the store-catalog timing facts of every kept column (and of the parents of kept derived columns), chosen by
         product family through the answers file's 'families' map: fact_status 'assumed' (or 'verified' when the
         answer is 'verified') + reviewed_by 'owner' + date, and the ruling appended to the column's provenance;
  S5     derived columns: feature-script outputs (a marked SIGNOFF block appended to features/build.py that updates
         OUTPUTS) and the columns of GENERATED store catalogs; a derived column is signed only when every parent
         (other than keys and the target) is signed after this run; never 'verified' (a derived column is 'assumed');
  S6     co_measured_with_target + co_measured_evidence on every kept time-varying column that has no answer, with
         the R8 lag before and after printed for every 'true' answer;
  S7     the target's legal_range_source;
  S8     the owner field of every unsigned exceptions.yaml entry. Refused (nothing is written) while an unsigned entry
         still reads as an open decision (OWNER DECISION, 'owner chooses', 'options for the owner', the freeze's
         open-decision phrases) or still calls a column kept or watch that ban.yaml bans after this run: an agent
         refreshes those entries to the rulings first (the sheet's S8 'yes after refresh'). With S8.sign_only
         ({package: {entry index: label}}, the label being the entry's column or the start of its check) only the
         listed entries are checked and signed (an owner who signs part of the list, ruling N); the other unsigned
         entries are left as they are and named in the report;
  S12   C9.guard_tolerance_k (option a: the measured candidate of tests/test_c9_guard_tolerance.py);
  S20    option b: the engine constants whose status is 'proposed' or 'extra' become 'cited';
  S18    option b: the named package's own files are left out of S1-S5;
  every ID: the option actions the answers file spells out under options.<answer>: verdicts (change a verdict),
         reasons (change a ban's reason word), remove_rows (catalog row + verdict), drop_driver / add_driver (a
         dataset.yaml driver template), add_rows (a catalog row + a ban or conditional verdict for a column the data
         hold without a row), add_include (a dataset.yaml include, sha256 computed here), notes (settle an
         open-decision note in ban.yaml so the freeze's F-BAN-OPEN scan no longer matches it), store_facts (record
         a content_epoch on a store-catalog column, for example GRIP4's road map, S29).
Every dataset.yaml of a listed package that includes an edited store catalog is re-pinned to its new sha256. A real
package (datasets/<name>/, not a *_draft copy) that includes an edited catalog but is not listed is REFUSED: its pin
would break. The DRAFT copies that include it are only listed: refresh them with refresh_drafts.py.

SAFETY. The default is a dry run: nothing is written. Unknown IDs, answers and option keys are refused before any
package is read. Every edit is made on the text in memory; the file is then parsed again, validated with the engine's
schema (treeroute.package.schema), and the parsed difference must lie inside the planned fields, or the run is
refused. With --apply, every new text is first STAGED in the aside folder (<aside>/_staged/...) and every target is
checked to be byte-for-byte the file the plan read (another task may have edited it since: then nothing is moved).
Only then is each edited file's old version MOVED (renamed, never deleted) into the aside folder under its path
relative to the engine folder, and the staged text put in its place. If a step fails half way (a file locked by
another program, for example), every file already replaced is put back: the new text is moved to
<aside>/_rolled_back/... and the old version copied back from the aside folder, so the packages are as before and
nothing is deleted (a leftover <file>.signoff_tmp is named in the message). Nothing is written under a root listed
in the registry's protected_roots.txt. After writing, every listed package is loaded again (closed folder, schema,
include hashes, the feature script's outputs). Running again with the same answers plans no edit (idempotent),
except for items whose inputs changed in between (a store built since, for example). The report ends with the test
files that read an edited file and the ones measured to pin the unsigned state: they need updating after --apply.

WHAT IT NEVER DOES. It never edits without an answer, never answers for the owner, never deletes a file, never edits
PREREGISTRATION_DRAFT.md (its markers are removed by hand once each item is really settled) and never touches files
outside the engine folder except the aside folder. Items that need engine code or a hand edit are printed as
follow-ups at the end.
"""
# Provenance: engine/FREEZE_SIGNOFF_SHEET.md (the groups); treeroute/check/guards.py (timing_facts_signed,
# exception_signed, the G-FACTS rules); treeroute_report/freeze.py (OPEN_DECISION, the F-BAN-OPEN scan);
# treeroute/package/schema.py (the file models); OWNER_RULINGS_2026-10-05.md L1 (the spelling of a signed fact:
# fact_status 'assumed' + reviewed_by owner + date); datasets/_tools/refresh_drafts.py (move aside, never delete).

import argparse
import ast
import datetime
import fnmatch
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import yaml

ENGINE_DEFAULT = Path(__file__).resolve().parents[2]
OWNER = "owner"
SHEET = "FREEZE_SIGNOFF_SHEET.md"
SIGN_GROUPS = ("S1", "S2", "S3", "S4")
KNOWN = {
    "S1": ("yes", "verified", "no"),
    "S2": ("yes", "verified", "no"),
    "S3": ("yes", "verified", "no"),
    "S4": ("yes", "verified", "no"),
    "S5": ("yes", "no"),
    "S6": ("recommended", "all_false", "no"),
    "S7": ("yes", "no"),
    "S8": ("yes", "no"),
    "S9": ("a", "b", "no"),
    "S10": ("yes", "no"),
    "S11": ("yes", "no"),
    "S12": ("a", "b", "c"),
    "S13": ("incomplete", "post_window_snapshot"),
    "S14": ("confirm_watch", "keep"),
    "S15": ("watch", "ban", "conditional"),
    "S16": ("lookahead_unfixable", "target_derived"),
    "S17": ("a", "b"),
    "S18": ("a", "b"),
    "S19": ("a", "b"),
    "S20": ("a", "b", "c"),
    "S21": ("accept", "build"),
    "S22": ("yes", "no"),
    "S23": ("record_end", "d42"),
    "S24": ("out", "keep", "t2"),
    "S25": ("leave", "remove"),
    "S26": ("noted",),
    "S27": ("ban", "freeze"),
    "S28": ("a", "b", "c"),
    "S29": ("a", "b"),
}
ITEM_KEYS = ("answer", "options", "note")
EXTRA_KEYS = {"S6": ("true_for", "reason_true", "reason_false", "reason_false_for", "reason_derived",
                     "reason_coproduct"),
              "S7": ("source",), "S8": ("sign_only",), "S18": ("package",)}
OPTION_KEYS = ("verdicts", "reasons", "remove_rows", "add_rows", "drop_driver", "add_driver", "add_include", "notes",
               "store_facts")
NOTE_KEYS = ("package", "contains", "text", "column", "all_matches")
STORE_FACT_KEYS = ("content_epoch",)       # the only store facts an option may record (S29)
# A parent banned for one of these reasons measures the target or its event: a column built from it is answered
# with reason_coproduct (its 'no' holds only because its content ends before the predicted step).
COPRODUCT_REASONS = ("label", "coproduct", "target_derived", "post_event_state")
# S8: an unsigned exceptions.yaml entry whose text still reads as an open owner decision is not signed as written.
STALE_ENTRY = re.compile(r"\bOWNER\s+DECISION\b|\bowner\s+chooses\b|\boptions?\s+for\s+the\s+owner\b"
                         r"|\buntil\s+the\s+owner\s+signs\b|\bchoice\b[^.;]{0,40}\bis\s+the\s+owner'?s\b", re.I)
KEPT_WORDS = re.compile(r"\b(?:kept|keep|watch)\b", re.I)
# Follow-ups the script cannot write (engine code, a hand edit, a command): printed when the answer is given.
FOLLOW_UPS = {
    ("S5", "yes"): "defo: confirm the K store build has finished (D:/defo_features_k: one file and one _build manifest "
                   "per group-year, every manifest's catalog_sha256 = the committed K catalog's) BEFORE --apply: the K "
                   "builder refuses a committed catalog that differs from what it generates, and defo's two generators "
                   "call their signed catalogs stale until they learn to carry the signatures (defo task)",
    ("S8", "yes"): "S8 is signed only after an agent refreshes the entries this tool names as still open or stale "
                   "(the L1 and L3 state, the S13, S15, S16, S28 and S29 answers); new entries the answers ask for "
                   "(S28 c, S29 b) are signed by the next run",
    ("S9", "a"): "fire: the owner builds the history store first, at D:/fire_history_lag2 (fire/dataset.yaml header: "
                 "build_history.py datasets/fire D:/fire_history_lag2, then its 'catalog' command); the 9 history "
                 "columns are new kept columns, so run this tool again after the store is declared to sign them (S1-S6)",
    ("S12", "b"): "C9 per cut: an engine change (R36 reads one k); not written by this tool",
    ("S12", "c"): "C9 unset: the freeze keeps refusing (F-CONSTANTS)",
    ("S13", "post_window_snapshot"): "every run refuses the 6 hold columns until the engine learns backward-only holds: "
                                     "the lineage stand-in (pipeline/data.py check_feature_lineage) refuses a "
                                     "feature-script output built from a post_window_snapshot ban, and no "
                                     "exceptions.yaml entry can lift that (engine change)",
    ("S17", "a"): "defo: edit expected_derived.json (Y0 2004, inner fit 2004-2016, R12 13/16, R18 4615/2197, R14 "
                  "4615/3750) and drop the six PENDING_OWNER_DERIVED pins in tests/test_derive_acceptance.py (defo task)",
    ("S18", "a"): "defo: drop tests/test_defo_k_l3_l4.py::test_nothing_in_the_package_is_marked_signed (defo task)",
    ("S19", "a"): "PREREGISTRATION_DRAFT.md item 3: remove its marker by hand (the record stays over the read rows)",
    ("S19", "b"): "last-value count over every target row: an engine change (one more counting pass)",
    ("S20", "a"): "PREREGISTRATION_DRAFT.md item 9: remove its marker by hand (the constants are signed with the Part)",
    ("S20", "c"): "make the freeze refuse on 'proposed'/'extra': edit CONSTANT_STATUSES_REFUSED in treeroute_report/freeze.py",
    ("S21", "accept"): "pipeline/run.py DEPARTURES: the engine task removes the ruled-acceptable departures (engine code)",
    ("S21", "build"): "the engine task builds each departure (quick checks in the pipeline, report rows, band source)",
    ("S22", "yes"): "PREREGISTRATION_DRAFT.md: write Appendix A from plan 3.3 and remove the settled markers by hand",
    ("S23", "record_end"): "treeroute/check/guards.py check_g_epoch: drop the observed_through flag for regular columns "
                           "(engine task)",
    ("S23", "d42"): "regular columns with observed_through after a cut need 'freeze' or a ban (lag-12 and hold columns)",
    ("S24", "t2"): "pm25 features/build.py: BURN_K 1 -> 2 (pm25 task), then run this tool again to sign the new facts",
    ("S25", "remove"): "fire: remove the joined store from dataset.yaml together with its catalog rows and verdicts "
                       "(not written by this tool: list the rows under options.remove.remove_rows instead)",
    ("S28", "a"): "defo task: add phenology_sos_doy_lag2 to datasets/defo/features/build.py (like the J2 a lag-1 "
                  "columns: derived_from phenology_sos_doy, operation 'lag k=2 unit=year', backward window), its "
                  "catalog.yaml row and a keep verdict, and its tests; then run this tool again (S5, S6 sign it). "
                  "The raw column is conditional, so the lineage stand-in allows the lag-2 output",
    ("S28", "c"): "defo: an agent writes an exceptions.yaml entry disclosing that phenology_sos_doy at lag 1 can hold "
                  "data from the predicted year (its signed reach runs 1 year past its year); the next run signs it (S8)",
    ("S29", "b"): "an agent writes one exceptions.yaml entry per package disclosing that road_density is a single "
                  "~2018 road map that G-EPOCH cannot check (no epoch recorded); the next run signs them (S8)",
}
# Measured 2026-10-06 18:00 (scratch copy D:/treeroute/signoff_20261006/applytest5 with the recommended answers
# applied, S9 open; targeted run against the same files unapplied): the test files that pin the state before the
# sign-off (unsigned facts, k unset, generated catalogs equal to their builders, verdict counts). 60 fail and need an
# edit; 31 more (draft copies equal to the package) fail until refresh_drafts.py runs, then pass. Printed after the
# planned edits; refresh this list whenever the sign-off is measured again.
MEASURED_TEST_IMPACT = (
    ("tests/test_constants.py", 4, "engine task: C9 set and statuses cited"),
    ("tests/test_packages_declarative.py", 8, "engine task: drafted owner fields marked unsigned, review-sheet cover"),
    ("tests/test_catalog_timing_facts.py", 3, "engine task: defo aggregate facts equal the generator's"),
    ("tests/test_packages_pm25_bans.py", 6, "pm25 task: unsigned facts and disclosures, verdict counts"),
    ("tests/test_fire_package_bans.py", 5, "fire task: unsigned facts and disclosures, verdict counts"),
    ("tests/test_ndvi_package_ban.py", 9, "ndvi task: only L1 signatures, closed world, verdict counts"),
    ("tests/test_ndvi_package.py", 2, "ndvi task: facts inherited from the unsigned source (1 more until the drafts "
                                      "are refreshed)"),
    ("tests/test_defo_k_ruling.py", 8, "defo task: the K catalog equals what build_store_k.py writes"),
    ("tests/test_defo_k_l3_l4.py", 3, "defo task: nothing marked signed (S18 a), hold facts unsigned"),
    ("tests/test_route_region_defo_package.py", 12, "defo task: the features catalog equals what build_store.py "
                                                    "writes (2 more until the drafts are refreshed)"),
    ("tests/test_pipeline_draft.py", 16, "no edit: they pass once refresh_drafts.py rewrites the drafts"),
    ("tests/test_fire_package.py", 8, "no edit: they pass once refresh_drafts.py rewrites the drafts"),
    ("tests/test_ndvi_package_draft.py", 4, "no edit: they pass once refresh_drafts.py rewrites the drafts"),
)
GENERIC_FILES = ("catalog.yaml", "ban.yaml", "exceptions.yaml", "dataset.yaml", "build.py")
BLOCK_BEGIN = "# >>> SIGNOFF BLOCK (written by datasets/_tools/apply_signoff.py; do not edit by hand) >>>"
BLOCK_END = "# <<< SIGNOFF BLOCK <<<"
GENERATED_MARK = "GENERATED by"
C9_ID = "C9.guard_tolerance_k"
C9_CANDIDATE = float.fromhex("0x1.c151e07e7cf79p-25")   # tests/test_c9_guard_tolerance.py K_CANDIDATE
CONFIRM_STATUSES = ("proposed", "extra")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SAFE_TEXT = re.compile(r"[^A-Za-z0-9 ,.;()/_+=<>\-]")


class SignoffRefusal(Exception):
    """The answers or the packages do not allow the planned edit (fail loudly; nothing is written)."""


# ==================================================================================== answers
def word(value):
    """An answer word: YAML 1.1 reads yes/no as booleans, so they are read back as the words."""
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return str(value or "").strip()


def load_answers(path):
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(doc, dict):
        raise SignoffRefusal("%s is not a mapping" % path)
    extra = sorted(set(doc) - {"ruling", "packages", "families", "answers"})
    if extra:
        raise SignoffRefusal("unknown top-level keys in %s: %s" % (path, extra))
    answers = doc.get("answers") or {}
    if not isinstance(answers, dict):
        raise SignoffRefusal("'answers' must be a mapping of IDs")
    unknown = sorted(str(k) for k in answers if k not in KNOWN)
    if unknown:
        raise SignoffRefusal("unknown IDs %s (known: %s); nothing was read or written" % (unknown, ", ".join(KNOWN)))
    clean = {}
    for sid, item in answers.items():
        item = {} if item is None else item
        if not isinstance(item, dict):
            raise SignoffRefusal("%s: must be a mapping with 'answer'" % sid)
        bad = sorted(set(item) - set(ITEM_KEYS) - set(EXTRA_KEYS.get(sid, ())))
        if bad:
            raise SignoffRefusal("%s: unknown keys %s" % (sid, bad))
        answer = word(item.get("answer"))
        if answer and answer not in KNOWN[sid]:
            raise SignoffRefusal("%s: answer %r is not one of %s" % (sid, answer, list(KNOWN[sid])))
        options = item.get("options") or {}
        if not isinstance(options, dict):
            raise SignoffRefusal("%s: options must be a mapping" % sid)
        options = {word(k): v for k, v in options.items()}
        for opt, spec in options.items():
            if opt not in KNOWN[sid]:
                raise SignoffRefusal("%s: options for unknown answer %r" % (sid, opt))
            spec = spec or {}
            badk = sorted(set(spec) - set(OPTION_KEYS))
            if badk:
                raise SignoffRefusal("%s.options.%s: unknown keys %s (known: %s)" % (sid, opt, badk, list(OPTION_KEYS)))
            for note in spec.get("notes") or ():
                badn = sorted(set(note) - set(NOTE_KEYS))
                if badn or not note.get("package") or not note.get("contains") or not note.get("text"):
                    raise SignoffRefusal("%s.options.%s: a note needs package, contains and text (unknown keys %s)"
                                         % (sid, opt, badn))
            for p, cols in (spec.get("store_facts") or {}).items():
                for c, facts in (cols or {}).items():
                    badf = sorted(set(facts or {}) - set(STORE_FACT_KEYS) - {"evidence"})
                    if badf or not set(facts or {}) & set(STORE_FACT_KEYS):
                        raise SignoffRefusal("%s.options.%s.store_facts.%s.%s: only %s may be recorded (got %s)"
                                             % (sid, opt, p, c, list(STORE_FACT_KEYS), sorted(facts or {})))
        clean[sid] = dict(item, answer=answer, options=options)
    only = (clean.get("S8") or {}).get("sign_only")
    if only is not None:
        good = isinstance(only, dict) and only and all(
            isinstance(entries, dict) and entries and all(
                isinstance(n, int) and not isinstance(n, bool) and n >= 0 and str(label or "").strip()
                for n, label in entries.items())
            for entries in only.values())
        if not good:
            raise SignoffRefusal("S8.sign_only must map each package to {entry index: label} (the label: the entry's "
                                 "column, or the start of its check), got %r" % (only,))
    if (clean.get("S17") or {}).get("answer") == "b" and (clean.get("S28") or {}).get("answer") == "a":
        raise SignoffRefusal("S17 b keeps defo's Y0 at 2003 by dropping the lag-2 MOD44B columns, but S28 a adds a lag-2 "
                             "phenology column, which moves Y0 back to 2004: answer S28 b (or S17 a)")
    families = doc.get("families") or {}
    for fam, group in families.items():
        if group not in SIGN_GROUPS:
            raise SignoffRefusal("families: %r maps to %r, not one of %s" % (fam, group, SIGN_GROUPS))
    ruling = doc.get("ruling") or {}
    answered = [s for s, it in clean.items() if it["answer"]]
    if answered:
        for key in ("id", "file", "date"):
            if not str(ruling.get(key) or "").strip():
                raise SignoffRefusal("answers are given (%s) but ruling.%s is empty: the edits must cite the owner's "
                                     "ruling" % (", ".join(answered), key))
        if not DATE_RE.match(str(ruling["date"])):
            raise SignoffRefusal("ruling.date %r is not YYYY-MM-DD" % ruling["date"])
    return SimpleNamespace(answers=clean, families=dict(families), ruling=SimpleNamespace(
        id=str(ruling.get("id") or ""), file=str(ruling.get("file") or ""), date=str(ruling.get("date") or "")),
        packages=list(doc.get("packages") or []))


def answer_of(ans, sid):
    item = ans.answers.get(sid)
    return item["answer"] if item else ""


def safe_text(text):
    return re.sub(r"\s+", " ", SAFE_TEXT.sub("", str(text))).strip()


# ==================================================================================== text editing
def sq(text):
    """A YAML single-quoted scalar on one line."""
    return "'" + str(text).replace("'", "''") + "'"


def emit(value):
    """One flow-style YAML value."""
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, float):
        if value == float("inf"):
            return ".inf"
        if value == float("-inf"):
            return "-.inf"
        return repr(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.\-]*", value) and value.lower() not in (
                "true", "false", "null", "yes", "no", "on", "off", "y", "n", "~"):
            return value
        return sq(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(emit(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join("%s: %s" % (emit_key(k), emit(v)) for k, v in value.items()) + "}"
    raise SignoffRefusal("cannot write the value %r" % (value,))


def emit_key(key):
    key = str(key)
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.\-]*", key):
        return key
    return sq(key)


def indent_of(line):
    return len(line) - len(line.lstrip(" "))


def key_re(key, indent):
    alts = [re.escape(key), "'" + re.escape(key.replace("'", "''")) + "'", '"' + re.escape(key) + '"']
    return re.compile(r"^ {%d}(?:%s)\s*:(?:\s|$)" % (indent, "|".join(alts)))


def section_range(lines, name):
    """(first, stop) line indexes of a top-level mapping 'name:'."""
    head = key_re(name, 0)
    start = None
    for k, line in enumerate(lines):
        if start is None:
            if head.match(line):
                start = k + 1
        elif line.strip() and not line.startswith(" ") and not line.startswith("#"):
            return start, k
    if start is None:
        raise SignoffRefusal("no top-level '%s:' section" % name)
    return start, len(lines)


def find_block(lines, key, indent, section):
    """(i, j): the key's line and the end of its block (exclusive), or None. Refuses a key found twice."""
    lo, hi = section_range(lines, section)
    pat = key_re(key, indent)
    hits = [k for k in range(lo, hi) if pat.match(lines[k])]
    if not hits:
        return None
    if len(hits) > 1:
        raise SignoffRefusal("key %r appears %d times in section %s" % (key, len(hits), section))
    i = hits[0]
    j = i + 1
    while j < hi:
        line = lines[j]
        if line.strip() and indent_of(line) <= indent:
            break
        j += 1
    while j - 1 > i and not lines[j - 1].strip():
        j -= 1
    return i, j


def split_flow(line, key, indent):
    """(prefix, mapping, comment) of a one-line flow row 'key: {...}  # comment', or None if not a flow row."""
    m = key_re(key, indent).match(line)
    rest = line[m.end():].strip() if m.end() <= len(line) else ""
    prefix = line[:m.end()].rstrip()
    if not rest.startswith("{"):
        return None
    # the comment starts at the first ' #' after which the row's text still parses as one closed mapping
    cuts = [k for k in range(1, len(rest)) if rest[k] == "#" and rest[k - 1] == " "
            and rest[:k].rstrip().endswith("}")] + [len(rest)]
    for cut in cuts:
        try:
            value = yaml.safe_load(rest[:cut])
        except yaml.YAMLError:
            continue
        if isinstance(value, dict):
            return prefix, value, rest[cut:].strip()
    raise SignoffRefusal("cannot read the flow row of %r: %s" % (key, line[:120]))


def field_span(lines, k, j, child_indent):
    """(value, end): the parsed scalar value of the field on line k and the end (exclusive) of its lines. A value may
    run over continuation lines (indented deeper than the field); the lines are parsed together. A nested mapping
    or list under the field is refused (only scalars are edited here)."""
    end = k + 1
    while end < j and (not lines[end].strip() or indent_of(lines[end]) > child_indent):
        end += 1
    while end - 1 > k and not lines[end - 1].strip():
        end -= 1
    text = "\n".join(line[child_indent:] if line.strip() else "" for line in lines[k:end])
    try:
        value = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise SignoffRefusal("cannot read the field %r: %s" % (lines[k].strip()[:80], exc))
    if not isinstance(value, dict) or len(value) != 1:
        raise SignoffRefusal("cannot read the field %r" % lines[k].strip()[:80])
    value = list(value.values())[0]
    if isinstance(value, (dict, list)):
        raise SignoffRefusal("the field %r holds a mapping or list; not edited" % lines[k].strip()[:80])
    return value, end


def set_fields(lines, key, indent, section, fields, append_to=None):
    """Set fields of the mapping 'key' (flow row or block). fields {name: value}; append_to {name: text} appends
    '; text' to a string field (creating it when absent). Each edited field is written on one line. Returns the
    new list of lines."""
    found = find_block(lines, key, indent, section)
    if found is None:
        raise SignoffRefusal("no row %r in section %s" % (key, section))
    i, j = found
    append_to = append_to or {}
    flow = split_flow(lines[i], key, indent)
    if flow is not None:
        prefix, mapping, comment = flow
        for name, value in fields.items():
            mapping[name] = value
        for name, text in append_to.items():
            old = mapping.get(name)
            mapping[name] = ("%s; %s" % (old, text)) if old else text
        new = "%s %s%s" % (prefix, emit(mapping), ("  " + comment) if comment else "")
        return lines[:i] + [new] + lines[j:]
    child = indent + 2
    body = lines[i + 1:j]
    sub = lines[:i + 1]

    def field_line(name):
        pat = key_re(name, child)
        hits = [k for k, line in enumerate(body) if pat.match(line)]
        if len(hits) > 1:
            raise SignoffRefusal("%r: field %s written twice" % (key, name))
        return hits[0] if hits else None

    for name, value in list(fields.items()) + [(n, None) for n in append_to if n not in fields]:
        k = field_line(name)
        old, end = field_span(body, k, len(body), child) if k is not None else (None, None)
        if name in append_to:
            if old is not None and not isinstance(old, str):
                raise SignoffRefusal("%r: field %s is not text" % (key, name))
            value = ("%s; %s" % (old, append_to[name])) if old else append_to[name]
        text = "%s%s: %s" % (" " * child, name, emit(value))
        if k is not None:
            body[k:end] = [text]
        else:
            at = field_line("provenance")
            at = len(body) if at is None or name == "provenance" else at
            body.insert(at, text)
    return sub + body + lines[j:]


def remove_block(lines, key, indent, section):
    found = find_block(lines, key, indent, section)
    if found is None:
        return lines, False
    i, j = found
    return lines[:i] + lines[j:], True


def replace_verdict(lines, column, verdict, reason, evidence):
    found = find_block(lines, column, 2, "verdicts")
    if found is None:
        raise SignoffRefusal("ban.yaml has no verdict for %r" % column)
    i, j = found
    flow = split_flow(lines[i], column, 2)
    head = [flow[0]] if flow is not None else [lines[i]]
    kept_comments = [line for line in lines[i + 1:j] if line.lstrip().startswith("#")]
    body = ["    verdict: %s" % verdict, "    reason: %s" % sq(reason), "    evidence: %s" % sq(evidence)]
    return lines[:i] + head + kept_comments + body + lines[j:]


def ydiff(a, b, path=()):
    """The set of parsed paths whose value differs."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = set()
        for k in set(a) | set(b):
            if k not in a or k not in b:
                out.add(path + (k,))
            else:
                out |= ydiff(a[k], b[k], path + (k,))
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = set()
        for n, (x, y) in enumerate(zip(a, b)):
            out |= ydiff(x, y, path + (n,))
        return out
    return set() if a == b else {path}


def within(path, allowed):
    return any(path[:len(p)] == p for p in allowed)


# ==================================================================================== the edit plan
class FileEdit(object):
    """One file's planned edit: its text, the ops (for the report) and the parsed paths allowed to change."""

    def __init__(self, path, kind):
        self.path = Path(path).resolve()
        self.kind = kind
        self.raw_bytes = self.path.read_bytes()          # what the plan read: checked again before any write
        raw = self.raw_bytes.decode("utf-8")
        self.crlf = "\r\n" in raw
        self.original = raw.replace("\r\n", "\n")
        self.lines = self.original.split("\n")
        self.allowed = set()
        self.ops = []            # (sid, text)
        self.checks = []         # (description, callable(parsed) -> bool)

    def text(self):
        return "\n".join(self.lines)

    def changed(self):
        return self.text() != self.original

    def data(self):
        out = self.text()
        return (out.replace("\n", "\r\n") if self.crlf else out).encode("utf-8")


class Plan(object):
    def __init__(self, engine, ans, packages):
        self.engine = engine
        self.ans = ans
        self.packages = packages
        self.files = {}
        self.counts = {}         # sid -> {package or 'all': n}
        self.samples = {}        # sid -> [names]
        self.skipped = []        # (sid, package, column, why)
        self.warnings = []
        self.lag_moves = []
        self.follow = []

    def file(self, path, kind):
        path = Path(path).resolve()
        if path not in self.files:
            self.files[path] = FileEdit(path, kind)
        return self.files[path]

    def count(self, sid, package, name):
        self.counts.setdefault(sid, {}).setdefault(package, 0)
        self.counts[sid][package] += 1
        sample = self.samples.setdefault(sid, [])
        if len(sample) < 6 and name not in sample:
            sample.append(name)


def ruling_note(ans, sid, words="signed by the owner"):
    r = ans.ruling
    return "%s %s (ruling %s, %s, %s %s)" % (words, r.date, r.id, r.file, SHEET, sid)


def cite(ans, sid):
    r = ans.ruling
    return "ruling %s, %s, %s, %s %s" % (r.id, r.date, r.file, SHEET, sid)


# ------------------------------------------------------------------------------------ packages
def load_contexts(engine, packages):
    if (engine / "treeroute").is_dir() and str(engine) not in sys.path:
        sys.path.insert(0, str(engine))
    from treeroute.check.quick import run_quick

    ctxs = {}
    for p in packages:
        root = engine / "datasets" / p
        if not (root / "dataset.yaml").is_file():
            raise SignoffRefusal("no package %s (%s)" % (p, root))
        ctxs[p] = run_quick(root, echo=lambda s: None)
    return ctxs


def is_generated(path):
    try:
        head = Path(path).read_text(encoding="utf-8")[:400]
    except OSError:
        return False
    return GENERATED_MARK in head


def entering_after(plan, ctxs):
    """{package: {column: merged facts}} of the columns that enter after this run's verdict changes and removals."""
    from treeroute.check import guards as G

    gone = {}
    for sid, item in plan.ans.answers.items():
        spec = (item["options"] or {}).get(item["answer"]) or {}
        for p, cols in (spec.get("verdicts") or {}).items():
            for c, v in (cols or {}).items():
                if v.get("verdict") not in G.ENTERING_VERDICTS:
                    gone.setdefault(p, set()).add(c)
        for p, cols in (spec.get("remove_rows") or {}).items():
            gone.setdefault(p, set()).update(cols or ())
    return {p: {c: f for c, f in ctx.entering.items() if c not in gone.get(p, set())} for p, ctx in ctxs.items()}


# ------------------------------------------------------------------------------------ S1-S5
def plan_signing(plan, ctxs, entering):
    from treeroute.check import guards as G
    from treeroute.check.facts import FEATURE_STORE

    ans = plan.ans
    excluded = set()
    if answer_of(ans, "S18") == "b":
        pkg = ans.answers["S18"].get("package")
        if not pkg:
            raise SignoffRefusal("S18 b needs 'package' (the package kept unsigned)")
        excluded.add((plan.engine / "datasets" / pkg).resolve())
    store_signs = {}      # catalog path -> {column: (sid, status)}
    output_signs = {}     # package -> {column}
    seen = {}

    def under_excluded(path):
        return any(str(path).startswith(str(x) + os.sep) for x in excluded)

    for p, ctx in ctxs.items():
        facts = ctx.facts
        root = Path(facts.loaded.root).resolve()
        target = facts.target.name if facts.target is not None else None

        def facts_of(name):
            src = facts.store_of.get(name)
            if src is None:
                return None, None, None
            if src == FEATURE_STORE:
                return src, root / "features" / "build.py", facts.outputs[name]
            return src, (root / src).resolve(), facts.loaded.stores[src].columns[name]

        def classify(name, depth=0):
            """True when the column will be signed after this run (or already is)."""
            key = (p, name)
            if key in seen:
                return seen[key]
            seen[key] = False
            src, path, f = facts_of(name)
            if f is None:
                plan.skipped.append(("S1-S5", p, name, "no store facts (package-row facts): not signed here"))
                return False
            if G.timing_facts_signed(f):
                seen[key] = True
                return True
            if depth > 8:
                raise SignoffRefusal("%s: derived_from chain deeper than 8 at %s" % (p, name))
            derived = src == FEATURE_STORE or is_generated(path)
            if derived:
                sid = "S5"
            else:
                fam = getattr(f, "product_family", None) or "(none)"
                sid = ans.families.get(fam)
                if sid is None:
                    plan.skipped.append(("S1-S4", p, name, "product family %r is in no group (answers 'families')"
                                         % fam))
                    return False
            answer = answer_of(ans, sid)
            if answer not in ("yes", "verified"):
                plan.skipped.append((sid, p, name, "%s not answered yes" % sid))
                return False
            if under_excluded(path):
                plan.skipped.append((sid, p, name, "S18 b: package kept unsigned"))
                return False
            if derived:
                for parent in getattr(f, "derived_from", ()) or ():
                    if parent in facts.keys or parent == target:
                        continue
                    if not classify(parent, depth + 1):
                        plan.skipped.append(("S5", p, name, "parent %s stays unsigned" % parent))
                        return False
            status = "verified" if (answer == "verified" and not derived) else "assumed"
            if src == FEATURE_STORE:
                output_signs.setdefault(p, set()).add(name)
            else:
                store_signs.setdefault(path, {})[name] = (sid, status)
            plan.count(sid, p, name)
            seen[key] = True
            return True

        for name in sorted(entering[p]):
            if not G.timing_facts_signed(entering[p][name]):
                classify(name)

    for path, cols in sorted(store_signs.items()):
        fe = plan.file(path, "store")
        if is_generated(path):
            plan.warnings.append("%s is GENERATED: its generator's check will call it stale until the generator "
                                 "carries signatures; build any store that checks it BEFORE --apply" % rel(plan, path))
        for name, (sid, status) in sorted(cols.items()):
            fe.lines = set_fields(fe.lines, name, 2, "columns",
                                  {"fact_status": status, "reviewed_by": OWNER, "date": plan.ans.ruling.date},
                                  append_to={"provenance": ruling_note(plan.ans, sid)})
            fe.allowed |= {("columns", name, k) for k in ("fact_status", "reviewed_by", "date", "provenance")}
            fe.checks.append(("%s signed" % name, lambda d, n=name: d["columns"][n].get("reviewed_by") == OWNER))
            fe.ops.append((sid, "sign %s (%s)" % (name, status)))
    for p, cols in sorted(output_signs.items()):
        path = (plan.engine / "datasets" / p / "features" / "build.py").resolve()
        fe = plan.file(path, "feature_script")
        fe.lines = signoff_block(fe.lines, cols, plan.ans)
        for name in sorted(cols):
            fe.ops.append(("S5", "sign %s (assumed, SIGNOFF block)" % name))


def signoff_block(lines, columns, ans):
    text = "\n".join(lines)
    entries = {}
    if BLOCK_BEGIN in text:
        head, rest = text.split(BLOCK_BEGIN, 1)
        if BLOCK_END not in rest:
            raise SignoffRefusal("features/build.py has a SIGNOFF block without its end marker")
        block, tail = rest.split(BLOCK_END, 1)
        m = re.search(r"SIGNOFF_COLUMNS = (\{.*?\n\})", block, re.S)
        if m is None:
            raise SignoffRefusal("cannot read the existing SIGNOFF block")
        entries = ast.literal_eval(m.group(1))
        if tail.strip():
            raise SignoffRefusal("features/build.py has code after its SIGNOFF block; not edited")
        text = head.rstrip("\n")
    for c in columns:
        entries.setdefault(c, (ans.ruling.id, ans.ruling.date, ans.ruling.file))
    body = ["", "", BLOCK_BEGIN,
            "# The owner signed the composed timing facts of these outputs (%s S5): fact_status 'assumed' + reviewed_by"
            % SHEET,
            "# owner + date, plan 1.3's spelling of a signed fact. Each entry: column -> (ruling id, date, rulings file).",
            "# The parents' facts were signed first (S1-S4 or earlier rulings); a renamed or removed output fails",
            "# loudly here (KeyError). Written by datasets/_tools/apply_signoff.py; edit the answers, not this block.",
            "SIGNOFF_COLUMNS = {"]
    for c in sorted(entries):
        body.append("    %r: %r," % (c, tuple(entries[c])))
    body += ["}",
             "for _signoff_column, (_signoff_ruling, _signoff_date, _signoff_file) in SIGNOFF_COLUMNS.items():",
             "    _signoff_facts = OUTPUTS[_signoff_column]",
             "    _signoff_facts.update({'fact_status': 'assumed', 'reviewed_by': 'owner', 'date': _signoff_date})",
             "    _signoff_facts['provenance'] = '; '.join(x for x in (_signoff_facts.get('provenance'), "
             "'signed by the owner %s (ruling %s, %s, " + SHEET + " S5)' % (_signoff_date, _signoff_ruling, "
             "_signoff_file)) if x)",
             "del _signoff_column, _signoff_ruling, _signoff_date, _signoff_file, _signoff_facts",
             BLOCK_END, ""]
    return (text + "\n".join(body)).split("\n")


# ------------------------------------------------------------------------------------ S6, S7
def match_any(name, patterns):
    return next((p for p in patterns if fnmatch.fnmatchcase(name, p)), None)


def plan_co_measured(plan, ctxs, entering):
    from treeroute.check import guards as G
    from treeroute.derive.rules import derive_r08_feature_lags

    item = plan.ans.answers.get("S6")
    if not item or item["answer"] not in ("recommended", "all_false"):
        return
    true_for = (item.get("true_for") or {}) if item["answer"] == "recommended" else {}
    listed = item.get("true_for") or {}            # the owner's co-measured list, also read for derived columns
    reasons = item.get("reason_true") or {}
    r_false = item.get("reason_false") or "not measured by the target's sensor or product within the target's step"
    r_false_for = item.get("reason_false_for") or {}
    r_derived = item.get("reason_derived") or ("a derived column whose content already ends at least one step "
                                               "before the row; a true answer would move it one more step back")
    r_coproduct = item.get("reason_coproduct") or (
        "built from a column measured with the target (or banned as its co-product or post-event state); 'no' holds "
        "only because this column's content ends before the predicted step (its lag or hold); a true answer would "
        "move it one more step back")
    for p, ctx in ctxs.items():
        facts = ctx.facts
        fe = plan.file(Path(facts.loaded.root) / "catalog.yaml", "catalog")
        verdicts = planned_verdicts(plan, ctx)
        target_name = getattr(facts.target, "name", None)

        def coproduct_parent(q):
            if q == target_name:
                return False                       # the target's own history: reason_derived (below)
            v = verdicts.get(q) or {}
            return (v.get("verdict") == "ban" and v.get("reason") in COPRODUCT_REASONS) \
                or match_any(q, listed.get(p) or ()) is not None

        for name in sorted(entering[p]):
            f = entering[p][name]
            if G._cadence_kind(f) in G.UNLAGGED_KINDS or f.co_measured_with_target is not None:
                continue
            pattern = match_any(name, true_for.get(p) or ())
            value = pattern is not None
            if value:
                why = reasons.get(p, {}).get(pattern) if isinstance(reasons.get(p), dict) else None
                why = why or "co-measured with the target"
                new = f.__dict__.copy()
                new["co_measured_with_target"] = True
                before = getattr(ctx.lags.get(name), "steps", None)
                try:
                    after = derive_r08_feature_lags({name: SimpleNamespace(**new)}, facts.target,
                                                    ctx.cadence).value[name].steps
                except Exception as exc:                               # noqa: BLE001 - reported, never hidden
                    after = "refused (%s)" % exc
                plan.lag_moves.append((p, name, before, after))
            elif match_any(name, (r_false_for.get(p) or {}).keys()) is not None:
                why = r_false_for[p][match_any(name, r_false_for[p].keys())]     # the owner's own reason
            elif f.derived_from and any(coproduct_parent(q) for q in f.derived_from):
                why = r_coproduct                  # e.g. defo's lag-2 MOD44B columns (parents banned coproduct)
            elif f.derived_from and any(q == target_name
                                        or getattr(facts.columns.get(q), "co_measured_with_target", None)
                                        for q in f.derived_from):
                why = r_derived                    # a lag, hold or aggregate of the target or of a co-measured column
            else:
                why = r_false
            evidence = "%s: %s" % (ruling_note(plan.ans, "S6", "answered by the owner"), safe_text(why))
            fe.lines = set_fields(fe.lines, name, 2, "columns",
                                  {"co_measured_with_target": value, "co_measured_evidence": evidence})
            fe.allowed |= {("columns", name, "co_measured_with_target"), ("columns", name, "co_measured_evidence")}
            fe.checks.append(("%s answered" % name, lambda d, n=name, v=value:
                              d["columns"][n].get("co_measured_with_target") is v))
            fe.ops.append(("S6", "%s co_measured %s" % (name, str(value).lower())))
            plan.count("S6" + ("_true" if value else "_false"), p, name)


def plan_target_source(plan, ctxs):
    item = plan.ans.answers.get("S7")
    if not item or item["answer"] != "yes":
        return
    sources = item.get("source") or {}
    for p, ctx in ctxs.items():
        t = ctx.facts.target
        if t is None or t.legal_range_source:
            continue
        text = sources.get(p)
        if not text:
            raise SignoffRefusal("S7 yes, but no source text for %s (answers S7.source.%s)" % (p, p))
        fe = plan.file(Path(ctx.facts.loaded.root) / "catalog.yaml", "catalog")
        value = "%s | %s" % (str(text).strip(), ruling_note(plan.ans, "S7", "cited by the owner"))
        fe.lines = set_fields(fe.lines, t.name, 2, "columns", {"legal_range_source": value})
        fe.allowed.add(("columns", t.name, "legal_range_source"))
        fe.ops.append(("S7", "%s legal_range_source" % t.name))
        plan.count("S7", p, t.name)


# ------------------------------------------------------------------------------------ S8
def plan_exceptions(plan, ctxs):
    from treeroute.check import guards as G

    if answer_of(plan.ans, "S8") != "yes":
        return
    only = plan.ans.answers["S8"].get("sign_only")
    if only is not None:
        unknown = sorted(set(only) - set(ctxs))
        if unknown:
            raise SignoffRefusal("S8.sign_only names packages that are not listed: %s (listed: %s)"
                                 % (unknown, list(ctxs)))
        for p, listed in sorted(only.items()):
            path = Path(ctxs[p].facts.loaded.root) / "exceptions.yaml"
            entries = ((yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("entries") or []) \
                if path.is_file() else []
            for n, label in sorted(listed.items()):
                if n >= len(entries):
                    raise SignoffRefusal("S8.sign_only: %s has %d exceptions.yaml entries, no entry %d (%s)"
                                         % (p, len(entries), n, label))
                entry, label = entries[n], str(label).strip()
                if not (str(entry.get("column") or "") == label
                        or (not entry.get("column") and str(entry.get("check") or "").startswith(label))):
                    raise SignoffRefusal("S8.sign_only: %s entry %d is %r, not %r (the file changed since the answers "
                                         "were written?)" % (p, n, entry.get("column") or entry.get("check"), label))

    def chosen(p, n):
        return only is None or n in (only.get(p) or {})

    stale, left = [], []
    for p, ctx in ctxs.items():
        path = Path(ctx.facts.loaded.root) / "exceptions.yaml"
        if not path.is_file():
            continue
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        verdicts = planned_verdicts(plan, ctx)
        for n, entry in enumerate(doc.get("entries") or []):
            if not G.exception_signed(SimpleNamespace(owner=entry.get("owner"))) and not chosen(p, n):
                left.append("%s %d (%s)" % (p, n, entry.get("column") or entry.get("check")))
            elif not G.exception_signed(SimpleNamespace(owner=entry.get("owner"))):
                why = stale_entry_reason(entry, verdicts)
                if why:
                    stale.append("%s entry %d (%s): %s" % (p, n, entry.get("column") or entry.get("check"), why))
    if stale:
        raise SignoffRefusal("S8 yes, but %d unsigned exceptions.yaml entries are not true as written; an agent refreshes "
                             "them to the rulings (and to this run's answers) first, or leave S8 blank for this run:\n  - "
                             % len(stale) + "\n  - ".join(stale))
    if left:
        plan.warnings.append("S8.sign_only: %d unsigned exceptions.yaml entries are left unsigned, as the answers ask: %s"
                             % (len(left), "; ".join(left)))
    for p, ctx in ctxs.items():
        path = Path(ctx.facts.loaded.root) / "exceptions.yaml"
        if not path.is_file():
            continue
        fe = plan.file(path, "exceptions")
        doc = yaml.safe_load(fe.text()) or {}
        entries = doc.get("entries") or []
        starts = [k for k, line in enumerate(fe.lines) if re.match(r"^ {2}- ", line)]
        if len(starts) != len(entries):
            raise SignoffRefusal("%s: %d entries parsed but %d '  - ' lines found" % (path, len(entries), len(starts)))
        for n, entry in enumerate(entries):
            if G.exception_signed(SimpleNamespace(owner=entry.get("owner"))) or not chosen(p, n):
                continue
            lo, hi = starts[n], (starts[n + 1] if n + 1 < len(starts) else len(fe.lines))
            hits = [k for k in range(lo, hi) if re.match(r"^ {4}owner\s*:", fe.lines[k])]
            if len(hits) != 1:
                raise SignoffRefusal("%s entry %d: owner line not found once" % (path, n))
            k = hits[0]
            _, end = field_span(fe.lines, k, hi, 4)
            old = str(entry.get("owner") or "")
            basis = re.sub(r"^\s*UNSIGNED\s*(--|:|-)?\s*", "", old)
            fe.lines[k:end] = ["    owner: %s" % sq("%s -- %s; %s" % (OWNER, ruling_note(plan.ans, "S8"), basis))]
            fe.allowed.add(("entries", n, "owner"))
            fe.ops.append(("S8", "sign entry %d (%s)" % (n, entry.get("column") or entry.get("check"))))
            plan.count("S8", p, str(entry.get("column") or entry.get("check")))


def stale_entry_reason(entry, verdicts):
    """Why an unsigned entry cannot be signed as written ('' when it can): its text still reads as an open owner
    decision, or its decision calls kept/watch a column that ban.yaml bans (after this run's verdict changes). For an
    entry addressed by 'check', the second test applies only when EVERY verdict column it names is banned (an entry
    may disclose a banned raw column and its kept hold column together)."""
    from treeroute_report.freeze import OPEN_DECISION

    text = " ".join(str(entry.get(k) or "") for k in ("decision", "reason", "owner", "check"))
    m = STALE_ENTRY.search(text) or OPEN_DECISION.search(text)
    if m:
        return "still reads as an open decision (%r)" % m.group(0)
    decision = str(entry.get("decision") or "")
    if not KEPT_WORDS.search(decision):
        return ""
    if entry.get("column"):
        named = [str(entry["column"])]
    else:
        named = sorted({c for c in re.findall(r"[A-Za-z_][A-Za-z0-9_:]*", str(entry.get("check") or ""))
                        if c in verdicts})
    banned = [c for c in named if (verdicts.get(c) or {}).get("verdict") == "ban"]
    if named and len(banned) == len(named):
        return "its decision says %r but ban.yaml bans %s" % (KEPT_WORDS.search(decision).group(0), ", ".join(banned))
    return ""


def planned_verdicts(plan, ctx):
    """{column: {verdict, reason}} of the package's ban.yaml as this run will leave it (the planned text when an
    option edits it, else the file)."""
    path = (Path(ctx.facts.loaded.root) / "ban.yaml").resolve()
    text = plan.files[path].text() if path in plan.files else path.read_text(encoding="utf-8")
    raw = (yaml.safe_load(text) or {}).get("verdicts") or {}
    return {c: (v if isinstance(v, dict) else {}) for c, v in raw.items()}


# ------------------------------------------------------------------------------------ engine constants
def plan_constants(plan):
    s12, s20 = answer_of(plan.ans, "S12"), answer_of(plan.ans, "S20")
    if s12 != "a" and s20 != "b":
        return
    path = plan.engine / "treeroute" / "engine_constants.py"
    fe = plan.file(path, "constants")
    r = plan.ans.ruling
    if s12 == "a":
        pat = re.compile(r'^(?P<name>\w+) = _c\("%s", UNSET, status="unset"\)\s*$' % re.escape(C9_ID))
        hits = [k for k, line in enumerate(fe.lines) if pat.match(line)]
        done = [k for k, line in enumerate(fe.lines) if ('"%s", %r' % (C9_ID, C9_CANDIDATE)) in line]
        if len(hits) == 1:
            name = pat.match(fe.lines[hits[0]]).group("name")
            fe.lines[hits[0]] = ('%s = _c("%s", %r, status="cited")  # origin: owner ruling %s (%s, %s S12 a): the '
                                 'measured candidate, PM2.5 nowcast identity gate exactly C9.identity_gate '
                                 '(tests/test_c9_guard_tolerance.py)' % (name, C9_ID, C9_CANDIDATE, r.id, r.date, SHEET))
            fe.ops.append(("S12", "%s = %r (cited)" % (C9_ID, C9_CANDIDATE)))
            plan.count("S12", "engine", C9_ID)
        elif not done:
            raise SignoffRefusal("engine_constants.py: the unset %s line was not found" % C9_ID)
        fe.checks.append(("C9 set", lambda reg: float(reg[C9_ID].value) == C9_CANDIDATE))
    if s20 == "b":
        pat = re.compile(r'^(?P<head>\w+ = _c\("(?P<cid>[^"]+)", .*status=")(?P<st>%s)(?P<tail>"\).*)$'
                         % "|".join(CONFIRM_STATUSES))
        for k, line in enumerate(fe.lines):
            m = pat.match(line)
            if not m:
                continue
            fe.lines[k] = "%scited%s  # owner confirmed: ruling %s (%s, %s S20 b), was %s" % (
                m.group("head"), m.group("tail"), r.id, r.date, SHEET, m.group("st"))
            fe.ops.append(("S20", "%s %s -> cited" % (m.group("cid"), m.group("st"))))
            plan.count("S20", "engine", m.group("cid"))
        fe.checks.append(("no constant awaits the owner",
                          lambda reg: not [c for c in reg.values() if c.status in CONFIRM_STATUSES]))


# ------------------------------------------------------------------------------------ option actions
OPEN_FIX = (
    (re.compile(r"\bdecisions?\s+(?:is\s+|are\s+|still\s+)?(?:pending|open)\b", re.I), "decision settled"),
    (re.compile(r"\bawait(?:s|ing)?\s+(?:the\s+)?(?:owner'?s?\s+)?(?:confirmation|signature|sign-?off|decision|"
                r"ruling|review)\b", re.I), "were settled by the owner"),
    (re.compile(r"\bowner\s+(?:to|must|should)\s+(?:decide|confirm|sign|rule)\b", re.I), "owner ruled"),
    (re.compile(r"\b(?:pending|awaiting|unconfirmed\s+by)\s+(?:the\s+)?owner\b", re.I), "settled by the owner"),
    (re.compile(r"\b(owner\s+items?)\b", re.I), r"\1 closed"),
    (re.compile(r"(\(\s*owner\s+check\s*\))", re.I), r"\1 closed"),
)


def settle_line(line, note_text, open_re):
    """The line with every open-decision phrase settled and the ruling cited after the first one."""
    done = [False]

    def fix(m, repl):
        out = m.expand(repl) if "\\" in repl else repl
        if not done[0]:
            done[0] = True
            out += " (%s)" % note_text
        return out

    for pat, repl in OPEN_FIX:
        line = pat.sub(lambda m, r=repl: fix(m, r), line)
    if open_re.search(line):
        raise SignoffRefusal("a note still reads open after settling: %s" % line.strip()[:160])
    return line


def verdict_block_of(lines, k):
    """(column, field) of the verdict that holds line k, or (None, None) for a header line or a comment."""
    if lines[k].lstrip().startswith("#"):
        return None, None
    lo, hi = section_range(lines, "verdicts")
    if not lo <= k < hi:
        return None, None
    col = field = None
    for n in range(k, lo - 1, -1):
        line = lines[n]
        if field is None and indent_of(line) == 4 and re.match(r"^ {4}[A-Za-z_]+\s*:", line):
            field = line.strip().split(":", 1)[0]
        if indent_of(line) == 2 and line.strip() and not line.lstrip().startswith("#"):
            key = line.strip()[:-1] if line.strip().endswith(":") else line.strip().split(": ", 1)[0]
            col = yaml.safe_load(key + ": 0")
            col = list(col)[0] if isinstance(col, dict) else key
            break
    return col, field


def plan_options(plan, ctxs):
    from treeroute_report.freeze import OPEN_DECISION

    r = plan.ans.ruling
    for sid in KNOWN:
        item = plan.ans.answers.get(sid)
        if not item or not item["answer"]:
            continue
        follow = FOLLOW_UPS.get((sid, item["answer"]))
        if follow:
            plan.follow.append("%s %s: %s" % (sid, item["answer"], follow))
        spec = (item["options"] or {}).get(item["answer"]) or {}
        for p, cols in (spec.get("remove_rows") or {}).items():
            root = package_root(plan, ctxs, p)
            cat = plan.file(root / "catalog.yaml", "catalog")
            ban = plan.file(root / "ban.yaml", "ban")
            for c in cols or ():
                cat.lines, a = remove_block(cat.lines, c, 2, "columns")
                ban.lines, b = remove_block(ban.lines, c, 2, "verdicts")
                if a or b:
                    cat.allowed.add(("columns", c))
                    ban.allowed.add(("verdicts", c))
                    cat.ops.append((sid, "remove row %s" % c))
                    ban.ops.append((sid, "remove verdict %s" % c))
                    plan.count(sid + "_remove", p, c)
        for p, cols in (spec.get("add_rows") or {}).items():
            root = package_root(plan, ctxs, p)
            cat = plan.file(root / "catalog.yaml", "catalog")
            ban = plan.file(root / "ban.yaml", "ban")
            for c, row in (cols or {}).items():
                if not row.get("role") or row.get("verdict") not in ("ban", "conditional") or not row.get("reason"):
                    raise SignoffRefusal("%s: add_rows %s needs role, verdict ban or conditional, and reason" % (sid, c))
                if row["verdict"] == "ban" and row["reason"] not in BAN_REASONS():
                    raise SignoffRefusal("%s: add_rows %s: %r is not a ban reason" % (sid, c, row["reason"]))
                note = ruling_note(plan.ans, sid, "row added by owner ruling")
                if find_block(cat.lines, c, 2, "columns") is None:
                    _, hi = section_range(cat.lines, "columns")
                    while hi > 0 and not cat.lines[hi - 1].strip():
                        hi -= 1
                    cat.lines.insert(hi, "  %s: %s" % (emit_key(c), emit({"role": row["role"], "provenance": note})))
                    cat.allowed.add(("columns", c))
                    cat.ops.append((sid, "add row %s" % c))
                if find_block(ban.lines, c, 2, "verdicts") is None:
                    _, hi = section_range(ban.lines, "verdicts")
                    while hi > 0 and not ban.lines[hi - 1].strip():
                        hi -= 1
                    evidence = "%s%s" % (note, (": " + row["evidence"]) if row.get("evidence") else "")
                    ban.lines[hi:hi] = ["  %s:" % emit_key(c), "    verdict: %s" % row["verdict"],
                                        "    reason: %s" % sq(row["reason"]), "    evidence: %s" % sq(evidence)]
                    ban.allowed.add(("verdicts", c))
                    ban.ops.append((sid, "add verdict %s" % c))
                    plan.count(sid + "_add", p, c)
        for p, cols in (spec.get("verdicts") or {}).items():
            root = package_root(plan, ctxs, p)
            ban = plan.file(root / "ban.yaml", "ban")
            current = (yaml.safe_load(ban.text()) or {}).get("verdicts") or {}
            for c, v in (cols or {}).items():
                old = current.get(c)
                if old is None:
                    raise SignoffRefusal("%s: %s has no verdict for %s" % (sid, p, c))
                new_v = v.get("verdict")
                if new_v == old.get("verdict") and (not v.get("reason") or v.get("reason") == old.get("reason")):
                    continue
                reason = v.get("reason") or old.get("reason")
                if new_v == "ban" and reason not in BAN_REASONS():
                    raise SignoffRefusal("%s: a ban of %s needs a ban reason word, got %r" % (sid, c, reason))
                if new_v != "ban" and old.get("verdict") == "ban" and not v.get("reason"):
                    raise SignoffRefusal("%s: %s leaves a ban; give its plain reason" % (sid, c))
                evidence = "%s: %s -> %s | was: %s | %s | %s" % (
                    ruling_note(plan.ans, sid, "owner ruling"), old.get("verdict"), new_v, old.get("verdict"),
                    old.get("reason"), old.get("evidence") or "")
                ban.lines = replace_verdict(ban.lines, c, new_v, reason, evidence)
                ban.allowed.add(("verdicts", c))
                ban.ops.append((sid, "%s: %s -> %s" % (c, old.get("verdict"), new_v)))
                plan.count(sid + "_verdict", p, c)
        for p, cols in (spec.get("reasons") or {}).items():
            root = package_root(plan, ctxs, p)
            ban = plan.file(root / "ban.yaml", "ban")
            current = (yaml.safe_load(ban.text()) or {}).get("verdicts") or {}
            for c, word in (cols or {}).items():
                old = current.get(c)
                if old is None or old.get("verdict") != "ban":
                    raise SignoffRefusal("%s: %s is not a ban in %s" % (sid, c, p))
                if word not in BAN_REASONS():
                    raise SignoffRefusal("%s: %r is not a ban reason" % (sid, word))
                if old.get("reason") == word:
                    continue
                evidence = "%s: reason %s -> %s | was: %s" % (ruling_note(plan.ans, sid, "owner ruling"),
                                                              old.get("reason"), word, old.get("evidence") or "")
                ban.lines = replace_verdict(ban.lines, c, "ban", word, evidence)
                ban.allowed.add(("verdicts", c))
                ban.ops.append((sid, "%s reason %s -> %s" % (c, old.get("reason"), word)))
                plan.count(sid + "_reason", p, c)
        for p, template in (spec.get("drop_driver") or {}).items():
            fe = plan.file(package_root(plan, ctxs, p) / "dataset.yaml", "dataset")
            hits = [k for k, line in enumerate(fe.lines) if re.match(r"^\s*-\s*['\"]?%s['\"]?\s*(#.*)?$"
                                                                      % re.escape(template), line)]
            if len(hits) > 1:
                raise SignoffRefusal("%s: driver %s listed twice in %s" % (sid, template, p))
            if hits:
                k = hits[0]
                fe.lines[k] = "%s# %s: driver store removed (%s): %s" % (
                    " " * indent_of(fe.lines[k]), sid, ruling_note(plan.ans, sid, "owner ruling"), template)
                fe.allowed.add(("stores", "drivers"))
                fe.ops.append((sid, "drop driver %s" % template))
                plan.count(sid + "_driver", p, template)
        for p, add in (spec.get("add_driver") or {}).items():
            fe = plan.file(package_root(plan, ctxs, p) / "dataset.yaml", "dataset")
            template = add["template"] if isinstance(add, dict) else add
            if any(template in line and not line.lstrip().startswith("#") for line in fe.lines):
                continue
            pattern = template.replace("{group}", "*").replace("{year}", "*")
            import glob
            if not glob.glob(pattern):
                raise SignoffRefusal("%s: the driver store %s holds no file yet (build it first)" % (sid, template))
            after = add.get("after") if isinstance(add, dict) else None
            lo, hi = drivers_range(fe.lines)
            at = hi
            if after:
                hits = [k for k in range(lo, hi) if after in fe.lines[k] and not fe.lines[k].lstrip().startswith("#")]
                if len(hits) != 1:
                    raise SignoffRefusal("%s: 'after' %s not found once among the drivers of %s" % (sid, after, p))
                at = hits[0] + 1
            fe.lines.insert(at, "    - %s  # %s" % (sq(template), ruling_note(plan.ans, sid, "added by owner ruling")))
            fe.allowed.add(("stores", "drivers"))
            fe.ops.append((sid, "add driver %s" % template))
            plan.count(sid + "_driver", p, template)
        for p, inc in (spec.get("add_include") or {}).items():
            root = package_root(plan, ctxs, p)
            fe = plan.file(root / "dataset.yaml", "dataset")
            src = (root / inc).resolve()
            if not src.is_file():
                raise SignoffRefusal("%s: include %s does not exist yet (run its catalog command first)" % (sid, src))
            if any(re.search(r"path:\s*%s\b" % re.escape(inc), line) for line in fe.lines):
                continue
            hi = includes_end(fe.lines)
            fe.lines.insert(hi, "  - {path: %s, sha256: %s}" % (inc, sha256_bytes(src.read_bytes())))
            fe.allowed.add(("includes",))
            fe.ops.append((sid, "add include %s" % inc))
            plan.count(sid + "_include", p, inc)
        for p, cols in (spec.get("store_facts") or {}).items():
            plan_store_facts(plan, ctxs, sid, p, cols or {})
        for note in spec.get("notes") or ():
            p = note["package"]
            ban = plan.file(package_root(plan, ctxs, p) / "ban.yaml", "ban")
            lines = ban.lines
            rng = range(len(lines))
            if note.get("column"):
                found = find_block(lines, note["column"], 2, "verdicts")
                if found is None:
                    raise SignoffRefusal("%s: note column %s has no verdict in %s" % (sid, note["column"], p))
                rng = range(found[0], found[1])
            hits = [k for k in rng if note["contains"] in lines[k]]
            if not hits:
                if any(("%s %s --" % (SHEET, sid)) in lines[k] for k in rng):
                    continue                                       # settled by an earlier run (idempotent)
                raise SignoffRefusal("%s: no line of %s/ban.yaml contains %r" % (sid, p, note["contains"]))
            if len(hits) > 1 and not note.get("all_matches"):
                raise SignoffRefusal("%s: %d lines of %s/ban.yaml contain %r (narrow it, or set all_matches)"
                                     % (sid, len(hits), p, note["contains"]))
            text = "%s -- %s" % (cite(plan.ans, sid), safe_text(note["text"]))
            for k in hits:
                if not OPEN_DECISION.search(lines[k]):
                    continue                                       # already settled (idempotent)
                col, field = verdict_block_of(lines, k)
                lines[k] = settle_line(lines[k], text, OPEN_DECISION)
                if col is not None:
                    ban.allowed.add(("verdicts", col, field) if field else ("verdicts", col))
                ban.ops.append((sid, "settle note line %d" % (k + 1)))
                plan.count(sid + "_note", p, "line %d" % (k + 1))


def plan_store_facts(plan, ctxs, sid, p, cols):
    """Record store facts (STORE_FACT_KEYS only) on the store-catalog row the package reads each column from. A
    shared catalog named through several packages is edited once (the second package finds the value set)."""
    from treeroute.check.facts import FEATURE_STORE

    facts = ctxs[p].facts if p in ctxs else None
    if facts is None:
        raise SignoffRefusal("%s: store_facts names package %s, which is not in the listed packages %s"
                             % (sid, p, list(ctxs)))
    root = Path(facts.loaded.root).resolve()
    for c, new in sorted(cols.items()):
        src = facts.store_of.get(c)
        if src is None or src == FEATURE_STORE:
            raise SignoffRefusal("%s: %s reads %s from no store catalog (store_facts edits store-catalog rows only)"
                                 % (sid, p, c))
        path = (root / src).resolve()
        fe = plan.file(path, "store")
        current = ((yaml.safe_load(fe.text()) or {}).get("columns") or {}).get(c) or {}
        todo = {k: v for k, v in new.items() if k in STORE_FACT_KEYS and str(current.get(k)) != str(v)}
        if not todo:
            continue                                               # recorded already (idempotent)
        note = "%s %s%s" % (", ".join("%s %s" % kv for kv in sorted(todo.items())),
                            ruling_note(plan.ans, sid, "recorded by owner ruling"),
                            (": " + safe_text(new["evidence"])) if new.get("evidence") else "")
        fe.lines = set_fields(fe.lines, c, 2, "columns", {k: str(v) for k, v in todo.items()},
                              append_to={"provenance": note})
        fe.allowed |= {("columns", c, k) for k in list(todo) + ["provenance"]}
        fe.checks.append(("%s %s recorded" % (c, sorted(todo)),
                          lambda d, n=c, t=dict(todo): all(str(d["columns"][n].get(k)) == str(v) for k, v in t.items())))
        fe.ops.append((sid, "%s: %s" % (c, ", ".join("%s %s" % kv for kv in sorted(todo.items())))))
        plan.count(sid + "_fact", p, c)


def BAN_REASONS():
    from treeroute.package.schema import BAN_REASONS as reasons
    return reasons


def package_root(plan, ctxs, p):
    if p not in ctxs:
        raise SignoffRefusal("the answers name package %s, which is not in the listed packages %s" % (p, list(ctxs)))
    return Path(ctxs[p].facts.loaded.root).resolve()


def drivers_range(lines):
    head = [k for k, line in enumerate(lines) if re.match(r"^\s+drivers\s*:\s*$", line)]
    if len(head) != 1:
        raise SignoffRefusal("dataset.yaml: no single 'drivers:' list")
    k0 = head[0]
    ind = indent_of(lines[k0])
    last = k0
    for k in range(k0 + 1, len(lines)):
        line = lines[k]
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if indent_of(line) <= ind and not line.lstrip().startswith("-"):
            break
        last = k
    return k0 + 1, last + 1


def includes_end(lines):
    k0 = [k for k, line in enumerate(lines) if re.match(r"^includes\s*:\s*$", line)]
    if len(k0) != 1:
        raise SignoffRefusal("dataset.yaml: no single 'includes:' list")
    last = k0[0]
    for k in range(k0[0] + 1, len(lines)):
        line = lines[k]
        if re.match(r"^\s*-\s*\{", line):
            last = k
        elif line.strip() and not line.startswith(" ") and not line.startswith("#"):
            break
    return last + 1


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def rel(plan, path):
    try:
        return Path(path).resolve().relative_to(plan.engine).as_posix()
    except ValueError:
        return str(path)


# ------------------------------------------------------------------------------------ re-pins
def plan_repins(plan, ctxs):
    changed = {path: fe for path, fe in plan.files.items() if fe.kind == "store" and fe.changed()}
    for p, ctx in ctxs.items():
        root = Path(ctx.facts.loaded.root).resolve()
        ds = plan.file(root / "dataset.yaml", "dataset")
        for path, fe in changed.items():
            for k, line in enumerate(ds.lines):
                m = re.match(r"^(\s*-\s*\{path:\s*)(?P<path>[^,]+?)(\s*,\s*sha256:\s*)(?P<sha>[0-9a-f]{64})(\s*\}.*)$", line)
                if not m or (root / m.group("path").strip()).resolve() != path:
                    continue
                new = sha256_bytes(fe.data())
                if m.group("sha") != new:
                    ds.lines[k] = line[:m.start("sha")] + new + line[m.end("sha"):]
                    ds.allowed.add(("includes",))
                    ds.ops.append(("pin", "%s -> %s" % (m.group("path").strip(), new[:12])))
    others, unlisted = [], []
    listed_roots = {Path(ctx.facts.loaded.root).resolve() for ctx in ctxs.values()}
    for ds_path in sorted((plan.engine / "datasets").glob("*/dataset.yaml")):
        root = ds_path.parent.resolve()
        if root in listed_roots or root.name.startswith("_"):
            continue
        text = ds_path.read_text(encoding="utf-8")
        for path in changed:
            for m in re.finditer(r"path:\s*([^,]+?)\s*,", text):
                if (root / m.group(1)).resolve() == path:
                    line = "%s includes %s" % (rel(plan, ds_path), rel(plan, path))
                    (others if root.name.endswith("_draft") else unlisted).append(line)
    if unlisted:
        raise SignoffRefusal("the edits change a store catalog that a real package not listed here also includes, so "
                             "its include pin would break: %s. List every such package (--packages or the answers "
                             "file's 'packages')" % "; ".join(sorted(set(unlisted))))
    if others:
        plan.warnings.append("not re-pinned (not listed packages; refresh drafts with refresh_drafts.py): "
                             + "; ".join(sorted(set(others))))


# ------------------------------------------------------------------------------------ validation
def validate(plan):
    from treeroute.package import schema as S

    models = {"store": S.StoreCatalog, "catalog": S.PackageCatalog, "ban": S.BanFile, "exceptions": S.ExceptionsFile,
              "dataset": S.DatasetFile}
    for path, fe in sorted(plan.files.items()):
        if not fe.changed():
            continue
        if fe.kind in models:
            old = yaml.safe_load(fe.original)
            try:
                new = yaml.safe_load(fe.text())
            except yaml.YAMLError as exc:
                raise SignoffRefusal("%s: the edited text does not parse: %s" % (rel(plan, path), exc))
            try:
                models[fe.kind].model_validate(new)
            except Exception as exc:
                raise SignoffRefusal("%s: the edited file fails the engine schema: %s" % (rel(plan, path), exc))
            stray = sorted(str(d) for d in ydiff(old, new) if not within(d, fe.allowed))
            if stray:
                raise SignoffRefusal("%s: unplanned parsed changes %s" % (rel(plan, path), stray[:8]))
            for what, check in fe.checks:
                if not check(new):
                    raise SignoffRefusal("%s: check failed after the edit: %s" % (rel(plan, path), what))
        elif fe.kind == "feature_script":
            try:
                compile(fe.text(), str(path), "exec")
            except SyntaxError as exc:
                raise SignoffRefusal("%s: the edited script does not compile: %s" % (rel(plan, path), exc))
        elif fe.kind == "constants":
            ns = {"__name__": "apply_signoff_constants_check"}
            exec(compile(fe.text(), str(path), "exec"), ns)       # registers into its own _REGISTRY
            for what, check in fe.checks:
                if not check(ns["_REGISTRY"]):
                    raise SignoffRefusal("engine_constants.py: check failed after the edit: %s" % what)


# ------------------------------------------------------------------------------------ writing
def protected_roots(engine):
    try:
        machine = yaml.safe_load((engine / "config" / "machine.yaml").read_text(encoding="utf-8")) or {}
        reg = Path(machine["registry_dir"]) / "protected_roots.txt"
        return [Path(line.strip()).resolve() for line in reg.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.strip().startswith("#")]
    except (OSError, KeyError, TypeError):
        raise SignoffRefusal("cannot read the registry's protected_roots.txt (config/machine.yaml registry_dir): no "
                             "write can be checked, so nothing is written")


def under(path, root):
    path, root = str(Path(path).resolve()).lower(), str(Path(root).resolve()).lower()
    return path == root or path.startswith(root.rstrip("\\/") + os.sep)


def write_all(plan, aside_root):
    roots = protected_roots(plan.engine)
    todo = [fe for fe in plan.files.values() if fe.changed()]
    for fe in todo:
        for target in (fe.path, aside_root / rel(plan, fe.path)):
            hit = [r for r in roots if under(target, r)]
            if hit:
                raise SignoffRefusal("refused: %s is under the protected root %s" % (target, hit[0]))
        if not under(fe.path, plan.engine):
            raise SignoffRefusal("refused: %s is outside the engine folder" % fe.path)
        for extra in (aside_root / rel(plan, fe.path), aside_root / "_staged" / rel(plan, fe.path),
                      fe.path.with_name(fe.path.name + ".signoff_tmp")):
            if extra.exists():
                raise SignoffRefusal("refused: %s already exists (an aside copy is never overwritten; a leftover "
                                     ".signoff_tmp means a previous run stopped half way: compare it, then move it "
                                     "away by hand)" % extra)
    todo = sorted(todo, key=lambda f: str(f.path))
    # 1. stage every new text inside the aside folder; nothing next to the packages changes yet
    for fe in todo:
        staged = aside_root / "_staged" / rel(plan, fe.path)
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(fe.data())
    # 2. every target must still be the file the plan read (other tasks edit these folders too)
    changed_since = [rel(plan, fe.path) for fe in todo if fe.path.read_bytes() != fe.raw_bytes]
    if changed_since:
        raise SignoffRefusal("refused: changed on disk since this run read them (another task?): %s. Nothing was "
                             "moved; run again to plan on the new text (staged copies are in %s)"
                             % (", ".join(changed_since), aside_root / "_staged"))
    # 3. swap: old version moved aside, staged text put in place; on any failure every swap so far is undone
    moved = []
    try:
        for fe in todo:
            aside = aside_root / rel(plan, fe.path)
            aside.parent.mkdir(parents=True, exist_ok=True)
            tmp = fe.path.with_name(fe.path.name + ".signoff_tmp")
            shutil.copyfile(str(aside_root / "_staged" / rel(plan, fe.path)), str(tmp))
            try:
                os.rename(str(fe.path), str(aside))
            except OSError:
                if aside.drive.lower() == fe.path.drive.lower():
                    raise                                       # same drive: a lock, not a drive change: fail
                shutil.copy2(str(fe.path), str(aside))          # another drive: the old version is copied, then replaced
            moved.append((fe.path, aside))
            os.replace(str(tmp), str(fe.path))
    except OSError as exc:
        restored, problems = rollback(plan, aside_root, moved, [fe.path for fe in todo])
        raise SignoffRefusal("refused half way (%s): %d file(s) were put back as they were (%s)%s; the new texts are "
                             "in %s" % (exc, len(restored), ", ".join(restored) or "none",
                                        ("; NOT restored: " + "; ".join(problems)) if problems else "",
                                        aside_root / "_rolled_back"))
    return moved


def rollback(plan, aside_root, moved, paths):
    """Undo the swaps of write_all, newest first, without deleting or moving anything: the new text is copied to
    <aside>/_rolled_back/<path>, then the old version is copied back over it from the aside folder. Returns (the
    restored paths, the problems: a file that could not be restored, a leftover .signoff_tmp)."""
    restored, problems = [], []
    for path, aside in reversed(moved):
        try:
            if path.exists():
                back = aside_root / "_rolled_back" / rel(plan, path)
                back.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(path), str(back))
            shutil.copy2(str(aside), str(path))
            restored.append(rel(plan, path))
        except OSError as exc:                                     # printed, never swallowed
            problems.append("%s (%s; its old version is %s)" % (rel(plan, path), exc, aside))
    for path in paths:
        tmp = path.with_name(path.name + ".signoff_tmp")
        if tmp.exists():
            problems.append("%s is left over (compare it with the staged copy, then move it away)" % tmp)
    return restored, problems


def reload_check(plan, ctxs):
    from treeroute.check import guards as G
    from treeroute.check.facts import package_facts
    from treeroute.package.load import load_package

    problems = []
    for p, ctx in ctxs.items():
        root = Path(ctx.facts.loaded.root)
        try:
            loaded = load_package(root)
            facts = package_facts(loaded)
            for rule, texts in facts.problems.items():
                problems.append("%s %s: %s" % (p, rule, "; ".join(texts)[:300]))
            verdicts = loaded.ban.verdicts
            unsigned = [c for c in facts.outputs if not G.timing_facts_signed(facts.outputs[c])
                        and G.verdict_of(verdicts, c) in G.ENTERING_VERDICTS]
            print("  reload %-6s ok: loads; %d kept feature-script outputs still unsigned" % (p, len(unsigned)))
        except Exception as exc:                                       # noqa: BLE001 - printed loudly
            problems.append("%s: %s" % (p, exc))
    return problems


# ==================================================================================== report
def report(plan, ans, dry, brief=False):
    r = ans.ruling
    print("apply_signoff %s -- engine %s" % ("DRY RUN" if dry else "APPLY", plan.engine))
    print("ruling %s (%s, %s); packages %s" % (r.id or "-", r.file or "-", r.date or "-", ", ".join(plan.packages)))
    given = ["%s=%s" % (s, it["answer"]) for s, it in ans.answers.items() if it["answer"]]
    open_ = [s for s in KNOWN if not answer_of(ans, s)]
    print("answered: %s" % (" ".join(given) or "none"))
    print("not answered (stay open): %s" % (" ".join(open_) or "none"))
    print()
    print("planned edits per group (columns or items, per package):")
    for sid in sorted(plan.counts, key=lambda s: (int(re.match(r"S(\d+)", s).group(1)), s)):
        per = plan.counts[sid]
        print("  %-14s %5d  %s   e.g. %s" % (sid, sum(per.values()), "  ".join("%s %d" % kv for kv in sorted(per.items())),
                                            ", ".join(plan.samples.get(sid, []))))
    if plan.lag_moves:
        print()
        print("S6 'true' answers and R8's lag (steps) before -> after:")
        for p, name, before, after in plan.lag_moves:
            flag = "" if before == after else "   <-- LAG MOVES"
            print("  %-6s %-34s %s -> %s%s" % (p, name, before, after, flag))
    print()
    print("files to write: %d" % sum(1 for fe in plan.files.values() if fe.changed()))
    for path, fe in sorted(plan.files.items()):
        if not fe.changed():
            continue
        groups = {}
        for sid, _ in fe.ops:
            groups[sid] = groups.get(sid, 0) + 1
        print("  %-62s %s" % (rel(plan, path), "  ".join("%s x%d" % kv for kv in sorted(groups.items()))))
    if not brief:
        import textwrap
        print()
        print("every planned edit, by file and group (--brief hides this list):")
        for path, fe in sorted(plan.files.items()):
            if not fe.changed():
                continue
            print("  %s" % rel(plan, path))
            by = {}
            for sid, text in fe.ops:
                by.setdefault(sid, []).append(text)
            for sid in sorted(by):
                body = "%s (%d): %s" % (sid, len(by[sid]), "; ".join(by[sid]))
                for k, line in enumerate(textwrap.wrap(body, 112)):
                    print("    %s%s" % ("" if k == 0 else "  ", line))
    skipped = {}
    for sid, p, name, why in plan.skipped:
        skipped.setdefault((sid, why), []).append("%s:%s" % (p, name))
    if skipped:
        print()
        print("not signed (reason, count, examples):")
        for (sid, why), names in sorted(skipped.items()):
            print("  %-6s %-60s %4d  %s" % (sid, why[:60], len(names), ", ".join(names[:4])))
    for w in plan.warnings:
        print()
        print("WARNING: %s" % w)
    if plan.follow:
        print()
        print("follow-ups by hand (not written by this tool):")
        for f in plan.follow:
            print("  - %s" % f)
    tests = affected_tests(plan)
    if tests:
        print()
        print("tests to update after --apply (they read an edited file or were measured to pin the unsigned state;")
        print("each package task updates its own, then one full suite):")
        for path, why in tests:
            print("  - %-44s %s" % (path, why))


def affected_tests(plan):
    """[(test file, why)] of the engine's test files that read a file this run edits (a heuristic scan: the file's
    own name, or for a generic name such as ban.yaml the file name together with its package's quoted name), plus
    the files MEASURED_TEST_IMPACT lists. They need updating after --apply (most pin the unsigned state)."""
    changed = [fe for fe in plan.files.values() if fe.changed()]
    tests_dir = plan.engine / "tests"
    if not changed or not tests_dir.is_dir():
        return []
    probes = []
    for fe in changed:
        name = fe.path.name
        if fe.kind == "constants":
            probes.append((name, [re.compile(r"engine_constants"),
                                  re.compile(r"guard_tolerance|['\"](?:proposed|extra)['\"]")]))
        elif name in GENERIC_FILES:
            try:
                parts = fe.path.relative_to((plan.engine / "datasets").resolve()).parts
            except ValueError:
                parts = (fe.path.parent.name, name)
            pkg = parts[0]
            probes.append(("/".join(parts), [re.compile(re.escape(name)),
                                                   re.compile(r"[\"']%s[\"']" % re.escape(pkg))]))
        else:
            probes.append((name, [re.compile(re.escape(name))]))
    measured = {f: (n, who) for f, n, who in MEASURED_TEST_IMPACT}
    out = {}
    for path in sorted(tests_dir.glob("test_*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        hits = [label for label, pats in probes if all(p.search(text) for p in pats)]
        key = "tests/" + path.name
        if hits:
            out[key] = "reads " + ", ".join(sorted(set(hits))[:4]) + (" ..." if len(set(hits)) > 4 else "")
    for key, (n, who) in measured.items():
        note = "measured 2026-10-06: %d failed after the recommended answers; %s" % (n, who)
        out[key] = (out[key] + "; " + note) if key in out else note
    return sorted(out.items())


def summary(plan):
    return {"counts": plan.counts, "samples": plan.samples,
            "files": {rel(plan, p): [op for op in fe.ops] for p, fe in plan.files.items() if fe.changed()},
            "skipped": [list(s) for s in plan.skipped], "lag_moves": [list(x) for x in plan.lag_moves],
            "warnings": plan.warnings, "follow_ups": plan.follow, "tests": affected_tests(plan)}


# ==================================================================================== main
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("answers")
    parser.add_argument("--apply", action="store_true", help="write the edits (default: dry run)")
    parser.add_argument("--engine", default=str(ENGINE_DEFAULT))
    parser.add_argument("--packages", nargs="+", default=None)
    parser.add_argument("--aside-root", default=None)
    parser.add_argument("--summary-json", default=None)
    parser.add_argument("--brief", action="store_true", help="counts only, without the list of every edit")
    args = parser.parse_args(argv)
    try:
        ans = load_answers(args.answers)
        engine = Path(args.engine).resolve()
        packages = args.packages or ans.packages
        if not packages:
            raise SignoffRefusal("no packages: give --packages or 'packages' in the answers file")
        ctxs = load_contexts(engine, packages)
        plan = Plan(engine, ans, packages)
        entering = entering_after(plan, ctxs)
        plan_options(plan, ctxs)
        plan_signing(plan, ctxs, entering)
        plan_co_measured(plan, ctxs, entering)
        plan_target_source(plan, ctxs)
        plan_exceptions(plan, ctxs)
        plan_constants(plan)
        plan_repins(plan, ctxs)
        validate(plan)
        report(plan, ans, dry=not args.apply, brief=args.brief)
        if args.summary_json:
            Path(args.summary_json).write_text(json.dumps(summary(plan), indent=1, default=str), encoding="utf-8")
        if not args.apply:
            print()
            print("Nothing was written (dry run). Run again with --apply to write.")
            return 0
        stamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        aside_root = Path(args.aside_root).resolve() if args.aside_root else \
            engine / "datasets" / ("_moved_signoff_" + stamp)
        moved = write_all(plan, aside_root)
        print()
        print("written: %d files; every old version moved into %s" % (len(moved), aside_root))
        problems = reload_check(plan, ctxs)
        if problems:
            print()
            print("ATTENTION: a package does not load cleanly after the edits (old files in %s):" % aside_root)
            for prob in problems:
                print("  - %s" % prob)
            return 4
        return 0
    except SignoffRefusal as exc:
        print("apply_signoff refused: %s" % exc)
        return 4


if __name__ == "__main__":
    sys.exit(main())
