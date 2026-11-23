"""The freeze lock and its 'verify' subcommand (plan 8.0 'Sat 10 Oct freeze: checks green, lock file';
plan 8.1 M5: 'From here on only bug fixes').

Usage, from the engine folder:

    py -3.9 -m treeroute_report.freeze <package> [<package> ...]
    py -3.9 -m treeroute_report.freeze verify [<lock file>] [--rehash-inputs]

Both take --run-root and --registry-dir (default: config/machine.yaml). They never write under a protected
root; the lock goes to <registry>/freeze/ only.

FREEZE refuses unless EVERY precondition holds, and nothing is written then. The failures come in two rounds:
round 1 checks every precondition below and lists all its failures together; only when round 1 is clean does
round 2 hash the store files inputs.json does not list (slow: about 6 GiB on the four packages) and check
again that the engine code and those files did not change while the freeze ran.
  F-NAMES         at least one package; no package named twice
  F-PACKAGE       each package loads (closed folder, schema, include hashes)
  F-DRAFT         no package is a DRAFT (treeroute.pipeline.draft.draft_status: a 'DRAFT --' stamp in ban.yaml or
                  dataset.yaml). A draft package's run can never be a headline run (G-DRAFT), so it is not frozen
  F-ENGINE-HASH   the CHECK REPORT CONTRACT's engine_code_sha256 function exists (treeroute/runs/fingerprint.py),
                  and the engine code does not change while the freeze runs (round 2)
  F-TOOLING       this tool's own .py and .yaml files (treeroute_report/: the table builder, the freeze and the
                  pre-registered lists, e.g. continuity_groups.yaml) are found; they are outside the engine hash,
                  so the lock records them in their own 'report_tooling' block, and they do not change while the
                  freeze runs (round 2)
  F-CHECK-EXISTS  the deep check report <run_root>/<package>/check/check_deep_<fingerprint 12 hex>.json exists
                  for the package's CURRENT fingerprint (a report for an older fingerprint is named)
  F-CHECK-CONTRACT the report carries the deep contract keys (checked_groups included) with the contract types
  F-CHECK-MATCH   its package, full package_fingerprint, mode 'deep' and engine_code_sha256 equal today's
  F-CHECK-GROUPS  owner ruling M2 (OWNER_RULINGS_2026-10-06.md): the deep check runs on each package's R21 smoke
                  groups, so the report's checked_groups.groups must equal the package's R21 smoke groups that the
                  freeze recomputes now (common.package_smoke_groups -> treeroute.check.report.package_smoke_groups:
                  the target store's groups minus split.yaml's exclusions, then the engine's smoke rule), and the
                  package's group count must be the one the report recorded. A report on any other subset (every
                  group included: a full-size deep check is a side record, never the gate), a report whose group
                  choice refused, or a package whose groups cannot be listed refuses. The deep report's quick checks
                  cover the whole package (the rest of M2)
  F-CHECK-GREEN   green is true and no guard says 'refuse'
  G-FACTS         the report's G-FACTS guard is present and says 'pass' (a 'flag' means unsigned timing facts
                  remain on kept columns; the check may run G-FACTS in its flag-only mode, the freeze may not)
  F-BAN-OPEN      ban.yaml has no open verdict: no 'keep_unreviewed' verdict and no open-decision text anywhere
                  in the file, comments included (OPEN_DECISION: 'DECISION pending', 'decision open', 'await(s)
                  confirmation', 'await the owner's signature', 'owner to decide', 'pending the owner', the item
                  labels 'OWNER item' and '(owner check)', ...; a label followed by 'is moot' / 'closed' is
                  settled). A stale note refuses too: the fix is to update the note, never to skip the scan
  F-PLAN          if the package has a plan (a headline folder whose plan phase is done), the latest one was
                  made from the current package fingerprint and the current engine code
  F-CONSTANTS     no engine constant is unset (CONSTANT_STATUSES_REFUSED), and every constant has an origin
                  comment. Constants whose status says the owner has not confirmed them yet
                  (CONSTANT_STATUSES_TO_CONFIRM: 'proposed', 'extra') do NOT refuse: they are printed, listed in
                  the lock ('awaiting_owner') and written into the filled pre-registration
                  ({{CONSTANTS_AWAITING_OWNER}}), so the owner signs them with it (owner decision; adding a status
                  to CONSTANT_STATUSES_REFUSED makes the freeze refuse on it instead)
  F-PINS          the installed library versions equal the version pins (owner ruling C)
  F-INPUTS        <registry>/inputs.json exists and is readable
  F-PREREG        the pre-registration draft is readable, every {{PLACEHOLDER}} in it is a known field, and no
                  item in it still starts with a bold pending marker (PENDING_MARKERS: 'OWNER DECISION PENDING',
                  'OPEN BEFORE FREEZE'); the freeze sees only the marker, so the owner checks that each removed
                  marker's item is really settled
  F-STORES        every store template of every package matches files, and each file inputs.json lists is
                  unchanged (size and modification time) (round 1); files inputs.json does not list are hashed
                  and must not change while they are read (round 2)

When everything holds it writes <registry>/freeze/FREEZE_<UTC timestamp>.lock.json ONCE (atomic, never
overwritten) with: engine_code_sha256 (and the file listing behind it and the comment-stripped engine hash
the manifests use); the report tooling's own file hashes (treeroute_report/*.py and *.yaml); every engine
constant with its value, status, test-exposed flag and origin comment, and the ids still awaiting the owner;
each package's fingerprint, draft status, file hashes, include hashes, check report hash and its checked groups
(ruling M2) and derived.json / plan.json hashes when a plan exists; the store files each package reads
(inputs.json's hashes, or the freeze's own); inputs.json's own hash; Python and library versions; the launch pins
(thread pins, workers, version pins).
It then fills the pre-registration draft's placeholders into PREREGISTRATION_<UTC timestamp>.md next to the
lock (written once) and prints both SHA-256s.

VERIFY re-hashes everything the lock recorded, lists the package's R21 smoke groups again (a drift when they
differ from the checked groups the lock recorded), and lists every drift (the M5 no-op rule: after the freeze
only bug fixes; a bug fix re-runs every package already run unless the no-op rule holds for it). A change to
the engine or to the report tooling affects all packages. It writes
VERIFY_<lock stamp>_<UTC timestamp>.json next to the lock. Exit codes: 0 no drift; 6 drift found; 4 refused.
"""

import argparse
import glob
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from treeroute.errors import TreerouteError
from treeroute_report import common as C
from treeroute_report.common import ReportRefusal

LOCK_FORMAT = "treeroute_report.freeze/3"     # /2: adds report_tooling, the draft status and awaiting_owner;
#                                               /3: adds the deep report's checked groups (ruling M2)
FREEZE_SUBDIR = "freeze"
LOCK_PREFIX = "FREEZE_"
LOCK_SUFFIX = ".lock.json"
PREREG_PREFIX = "PREREGISTRATION_"
VERIFY_PREFIX = "VERIFY_"
INPUTS_FILE = "inputs.json"
CHECK_DIR = "check"
CHECK_MODE_DEEP = "deep"
CHECK_DETAILS_SUFFIX = "_details.json"  # treeroute/check/report.py writes check_<mode>_<fp>_details.json beside it
FINGERPRINT_PREFIX_CHARS = 12          # the check report's file name carries the first 12 hex characters
GUARD_STATUSES = ("pass", "flag", "refuse")
CONTRACT_KEYS = ("package", "package_fingerprint", "engine_code_sha256", "mode", "green", "guards", "started",
                 "finished")
GUARD_KEYS = ("id", "status", "message", "columns")
# Ruling M2: a deep report also names the groups it checked (treeroute/check/report.py; a test keeps these equal).
GROUPS_KEY = "checked_groups"
DEEP_CONTRACT_KEYS = CONTRACT_KEYS + (GROUPS_KEY,)
GROUPS_RECORD_KEYS = ("groups", "selection", "rule", "constants", "package_groups", "data_groups", "refused")
M2_SELECTION = "R21 smoke groups, ruling M2"
G_FACTS = "G-FACTS"
OPEN_VERDICT = "keep_unreviewed"
# An owner decision still open, written into ban.yaml (in a verdict's text or in a comment). Matched case-blind,
# line by line. Wide on purpose: a stale note that matches refuses loudly and is fixed by updating the note; an open
# decision the scan missed would pass silently. The two label forms the ban lists use for an open item, 'OWNER item'
# and '(owner check)', count too, unless the same words say it is settled ('... is moot', '... closed'); the bare
# words 'OWNER CHECK' do not, because the ban lists also use them to cite the review sheet's OWNER CHECK column
# (e.g. 'the 2023-vintage OWNER CHECK is moot', 'closes J2 d's OWNER CHECK').
_SETTLED_AFTER = r"(?!\s*(?:is|are|was|were|now)?\s*(?:moot|closed|settled|resolved|withdrawn)\b)"
OPEN_DECISION = re.compile(
    r"\bdecisions?\s+(?:is\s+|are\s+|still\s+)?(?:pending|open)\b"
    r"|\bawait(?:s|ing)?\s+(?:the\s+)?(?:owner'?s?\s+)?(?:confirmation|signature|sign-?off|decision|ruling|review)\b"
    r"|\bowner\s+(?:to|must|should)\s+(?:decide|confirm|sign|rule)\b"
    r"|\b(?:pending|awaiting|unconfirmed\s+by)\s+(?:the\s+)?owner\b"
    r"|\bowner\s+items?\b" + _SETTLED_AFTER +
    r"|\(\s*owner\s+check\s*\)" + _SETTLED_AFTER,
    re.IGNORECASE)
# engine_constants statuses (engine_constants.STATUSES): refused by the freeze, or printed and listed for the owner
CONSTANT_STATUSES_REFUSED = ("unset",)
CONSTANT_STATUSES_TO_CONFIRM = ("proposed", "extra")
STORE_ROLES = ("target", "static", "drivers", "globals", "features")
PLACEHOLDER = re.compile(r"\{\{([A-Z0-9_]+)(?::([A-Za-z0-9_.\-]+))?\}\}")
# An item of the pre-registration draft still open: it starts with one of these markers in bold. The freeze refuses
# while one remains (F-PREREG): the draft says every such item is settled before the freeze, and the filled copy
# the owner signs must not carry one. The freeze cannot tell whether an item is really settled, only that whoever
# settled it removed its marker.
PENDING_MARKERS = ("OWNER DECISION PENDING", "OPEN BEFORE FREEZE")
PENDING_MARKER = re.compile(r"\*\*(%s)\b" % "|".join(re.escape(m) for m in PENDING_MARKERS))
DEFAULT_PREREG = C.ENGINE_DIR / "PREREGISTRATION_DRAFT.md"
NO_OP_RULE = ("plan 8.1 M5: after the freeze only bug fixes. A bug fix re-runs every package already run, unless "
              "the no-op rule applies for that package: its derived.json and smoke outputs stay byte-identical, AND "
              "either a one-group full-width probe stays byte-identical or the changed functions are shown never to "
              "run on that package at full size.")
EXIT_REFUSED = 4
EXIT_DRIFT = 6
PRECONDITIONS = ("F-NAMES", "F-PACKAGE", "F-DRAFT", "F-ENGINE-HASH", "F-TOOLING", "F-CHECK-EXISTS",
                 "F-CHECK-CONTRACT", "F-CHECK-MATCH", "F-CHECK-GROUPS", "F-CHECK-GREEN", G_FACTS, "F-BAN-OPEN",
                 "F-PLAN", "F-CONSTANTS", "F-PINS", "F-INPUTS", "F-PREREG", "F-STORES")


class FreezeRefusal(ReportRefusal):
    """The freeze refused: one or more preconditions failed (each listed with its id)."""

    def __init__(self, failures: Sequence[Tuple[str, Optional[str], str]]):
        self.failures = list(failures)
        lines = ["%s%s: %s" % (fid, " [%s]" % pkg if pkg else "", msg) for fid, pkg, msg in self.failures]
        super().__init__("FREEZE", "%d precondition(s) failed; nothing was written:\n  %s"
                         % (len(lines), "\n  ".join(lines)),
                         fix="fix each failed precondition, then run the freeze again")

    def ids(self) -> List[str]:
        return [f[0] for f in self.failures]


# ============================================================================== package preconditions
def _check_report_path(run_root: Path, name: str, fingerprint: str) -> Path:
    return run_root / name / CHECK_DIR / ("check_%s_%s.json" % (CHECK_MODE_DEEP, fingerprint[:FINGERPRINT_PREFIX_CHARS]))


def _read_check_report(run_root: Path, name: str, fingerprint: str, engine_sha: Optional[str],
                       fail: Callable[[str, str], None],
                       smoke: Optional[Mapping[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """The deep check report for the current fingerprint, checked against the contract; None on failure. smoke:
    the package's R21 smoke groups recomputed by the freeze (common.package_smoke_groups), None when they could not
    be listed (F-CHECK-GROUPS already failed then)."""
    path = _check_report_path(run_root, name, fingerprint)
    if not path.is_file():
        others = sorted(p.name for p in (run_root / name / CHECK_DIR).glob("check_%s_*.json" % CHECK_MODE_DEEP)
                        if not p.name.endswith(CHECK_DETAILS_SUFFIX)) \
            if (run_root / name / CHECK_DIR).is_dir() else []
        fail("F-CHECK-EXISTS", "no deep check report for the current package fingerprint %s (%s)%s"
             % (fingerprint[:FINGERPRINT_PREFIX_CHARS], path,
                "; deep reports exist for other fingerprints (the package changed since): %s" % ", ".join(others)
                if others else "; run 'py -3.9 -m treeroute check <package> --deep'"))
        return None
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        fail("F-CHECK-CONTRACT", "%s is not readable JSON: %s" % (path, exc))
        return None
    problems = []
    if not isinstance(report, dict):
        fail("F-CHECK-CONTRACT", "%s is not a JSON object" % path)
        return None
    missing = [k for k in DEEP_CONTRACT_KEYS if k not in report]
    if missing:
        problems.append("missing keys %s%s" % (missing, " (a deep report names the groups it checked since ruling "
                                                      "M2: run 'check --deep' again)" if GROUPS_KEY in missing else ""))
    else:
        problems += _groups_record_problems(report[GROUPS_KEY])
    if not isinstance(report.get("green"), bool):
        problems.append("green is %r, not true or false" % (report.get("green"),))
    guards = report.get("guards")
    if not isinstance(guards, list):
        problems.append("guards is not a list")
        guards = []
    for i, g in enumerate(guards):
        if not isinstance(g, dict) or [k for k in GUARD_KEYS if k not in g]:
            problems.append("guard %d lacks the keys %s" % (i, list(GUARD_KEYS)))
        elif g["status"] not in GUARD_STATUSES:
            problems.append("guard %s has status %r (allowed: %s)" % (g.get("id"), g["status"], "|".join(GUARD_STATUSES)))
        elif not isinstance(g["columns"], list):
            problems.append("guard %s: columns is not a list" % g.get("id"))
    for key in ("started", "finished"):
        if key in report and not (isinstance(report[key], str) and report[key]):
            problems.append("%s is not a timestamp string" % key)
    if problems:
        fail("F-CHECK-CONTRACT", "%s does not follow the CHECK REPORT CONTRACT: %s" % (path, "; ".join(problems)))
        return None
    mismatch = []
    if report["package"] != name:
        mismatch.append("package %r, not %r" % (report["package"], name))
    if report["package_fingerprint"] != fingerprint:
        mismatch.append("package_fingerprint %s..., not the current %s..." % (str(report["package_fingerprint"])[:16],
                                                                             fingerprint[:16]))
    if report["mode"] != CHECK_MODE_DEEP:
        mismatch.append("mode %r, not 'deep'" % report["mode"])
    if engine_sha is not None and report["engine_code_sha256"] != engine_sha:
        mismatch.append("engine_code_sha256 %s..., not today's %s... (the engine changed since the check)"
                        % (str(report["engine_code_sha256"])[:16], engine_sha[:16]))
    if mismatch:
        fail("F-CHECK-MATCH", "%s: %s" % (path, "; ".join(mismatch)))
    _check_groups(path, report[GROUPS_KEY], smoke, fail)
    refused = [g["id"] for g in guards if g["status"] == "refuse"]
    if report["green"] is not True or refused:
        fail("F-CHECK-GREEN", "%s: green=%s; guards that refuse: %s" % (path, report["green"], refused or "none"))
    facts = [g for g in guards if g["id"] == G_FACTS]          # a label may repeat (quick + deep parts)
    if not facts:
        fail(G_FACTS, "%s has no %s guard: the freeze needs its 'pass'" % (path, G_FACTS))
    for g in facts:
        if g["status"] != "pass":
            cols = g["columns"]
            fail(G_FACTS, "%s says %r: kept columns with unsigned timing facts remain (%d columns%s): %s"
                 % (G_FACTS, g["status"], len(cols), ", e.g. " + ", ".join(map(str, cols[:8])) if cols else "",
                    g["message"][:400]))
    return {"path": str(path), "sha256": C.sha256_file(path), "mode": report["mode"], "green": report["green"],
            "engine_code_sha256": report["engine_code_sha256"], "started": report["started"],
            "finished": report["finished"], "checked_groups": report[GROUPS_KEY],
            "guards": [{"id": g["id"], "status": g["status"]} for g in guards]}


def _groups_record_problems(record: Any) -> List[str]:
    """F-CHECK-CONTRACT on a deep report's checked_groups: exactly GROUPS_RECORD_KEYS, a sorted list of distinct
    group names, integer group counts."""
    if not isinstance(record, dict):
        return ["%s is %r, not an object" % (GROUPS_KEY, record)]
    if set(record) != set(GROUPS_RECORD_KEYS):
        return ["%s has the keys %s, not %s" % (GROUPS_KEY, sorted(record), list(GROUPS_RECORD_KEYS))]
    problems = []
    names = record["groups"]
    if not isinstance(names, list) or any(not isinstance(g, str) or not g for g in names) \
            or names != sorted(set(names)):
        problems.append("%s.groups is not a sorted list of distinct group names: %r" % (GROUPS_KEY, names))
    for key in ("package_groups", "data_groups"):
        if isinstance(record[key], bool) or not isinstance(record[key], int):
            problems.append("%s.%s is %r, not a count" % (GROUPS_KEY, key, record[key]))
    return problems


def _check_groups(path: Path, record: Mapping[str, Any], smoke: Optional[Mapping[str, Any]],
                  fail: Callable[[str, str], None]) -> None:
    """F-CHECK-GROUPS (ruling M2): the report checked exactly the package's R21 smoke groups recomputed now, and
    the package's group count is the one the report recorded. How the report chose them (its 'selection') is
    recorded in the lock; the groups decide."""
    if record["refused"]:
        fail("F-CHECK-GROUPS", "%s: the deep check chose no group (%s): %s" % (path, record["selection"],
                                                                              record["refused"]))
        return
    if smoke is None:
        return
    problems = []
    checked = list(record["groups"])
    if checked != list(smoke["groups"]):
        shown = ", ".join(checked[:12]) + (", ... (%d in all)" % len(checked) if len(checked) > 12 else "")
        problems.append("it checked %d group(s) [%s] (%s), not the package's R21 smoke groups [%s] that the freeze "
                        "recomputes now (ruling M2: the deep check runs on exactly those)"
                        % (len(checked), shown, record["selection"], ", ".join(smoke["groups"])))
    if record["package_groups"] != smoke["package_groups"]:
        problems.append("the package had %d groups after split.yaml's exclusions when it was checked, %d now"
                        % (record["package_groups"], smoke["package_groups"]))
    if problems:
        fail("F-CHECK-GROUPS", "%s: %s; run 'py -3.9 -m treeroute check <package> --deep' (it checks the ruling-M2 "
             "subset)" % (path, "; ".join(problems)))


def open_verdicts(package: Any) -> Dict[str, Any]:
    """F-BAN-OPEN: the open verdicts of a loaded package's ban.yaml (structural and written markers)."""
    unreviewed = sorted(c for c, v in package.ban.verdicts.items() if v.verdict == OPEN_VERDICT)
    markers = []
    text = (Path(package.root) / "ban.yaml").read_text(encoding="utf-8")
    for no, line in enumerate(text.splitlines(), 1):
        if OPEN_DECISION.search(line):
            markers.append({"line": no, "text": line.strip()[:200]})
    return {"keep_unreviewed": unreviewed, "open_decision_markers": markers}


def latest_plan(run_root: Path, name: str) -> Optional[Path]:
    """The headline folder whose plan phase finished last (the engine's own rule, pipeline/run.py
    _plan_check: by the plan marker's finished_utc, then its mtime, then the folder name)."""
    from treeroute.runs.resume import PHASE_DONE, PHASES_DIR

    kind_dir = run_root / name / "headline"
    plans = []
    if kind_dir.is_dir():
        for folder in kind_dir.iterdir():
            marker = folder / PHASES_DIR / "plan" / PHASE_DONE
            if folder.is_dir() and marker.is_file():
                info = json.loads(marker.read_text(encoding="utf-8"))
                plans.append((str(info.get("finished_utc")), marker.stat().st_mtime_ns, folder.name, folder))
    if not plans:
        return None
    return max(plans, key=lambda p: p[:3])[3]


def _plan_record(run_root: Path, name: str, fingerprint: str, engine_hash_stripped: str,
                 fail: Callable[[str, str], None]) -> Optional[Dict[str, Any]]:
    folder = latest_plan(run_root, name)
    if folder is None:
        return None
    rec = {"folder": str(folder)}
    needed = ("run_record.json", "manifest.json", "derived.json", "plan.json")
    absent = [n for n in needed if not (folder / n).is_file()]
    if absent:
        fail("F-PLAN", "the latest plan folder %s lacks %s" % (folder, absent))
        return None
    run_record = json.loads((folder / "run_record.json").read_text(encoding="utf-8"))
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    rec.update({"run_fingerprint": run_record.get("run_fingerprint"),
                "package_fingerprint": run_record.get("package_fingerprint"),
                "engine_code_hash": manifest.get("engine_code_hash"),
                "derived_json_sha256": C.sha256_file(folder / "derived.json"),
                "plan_json_sha256": C.sha256_file(folder / "plan.json"),
                "derived_sha256": run_record.get("derived_sha256")})
    if run_record.get("package_fingerprint") != fingerprint:
        fail("F-PLAN", "the latest plan %s was made from package fingerprint %s..., not the current %s...: plan again"
             % (folder.name, str(run_record.get("package_fingerprint"))[:16], fingerprint[:16]))
    if manifest.get("engine_code_hash") != engine_hash_stripped:
        fail("F-PLAN", "the latest plan %s was made by other engine code (manifest engine_code_hash %s..., today "
             "%s...): plan again" % (folder.name, str(manifest.get("engine_code_hash"))[:16], engine_hash_stripped[:16]))
    return rec


# ===================================================================================== store files
def _norm_key(path: Any) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def load_inputs(registry_dir: Path) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """inputs.json (the registry's input-store hashes) and an index {normalised path: entry}."""
    path = registry_dir / INPUTS_FILE
    if not path.is_file():
        raise ReportRefusal("F-INPUTS", "%s is missing: the lock records the input-store hashes from it" % path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("files"), list):
        raise ReportRefusal("F-INPUTS", "%s has no 'files' list" % path)
    index = {}
    for entry in data["files"]:
        if not isinstance(entry, dict) or not all(k in entry for k in ("path", "size", "mtime", "sha256")):
            raise ReportRefusal("F-INPUTS", "%s has a file entry without path, size, mtime and sha256: %r"
                                % (path, entry))
        index[_norm_key(entry["path"])] = entry
    meta = {"path": str(path), "sha256": C.sha256_file(path), "created": data.get("created"),
            "roots": data.get("roots"), "extra": data.get("extra"), "n_files": len(data["files"])}
    return meta, index


def store_templates(package: Any) -> List[Tuple[str, str]]:
    """(role, template) of every store path in dataset.yaml."""
    stores = package.dataset.stores
    out = []
    for role in STORE_ROLES:
        value = getattr(stores, role, None)
        if value is None:
            continue
        for template in (value if isinstance(value, list) else [value]):
            out.append((role, template))
    return out


def template_files(package_root: Path, template: str) -> List[str]:
    """The files a store template names: placeholders ({group}, {year}, ...) match anything; a template
    that names an existing folder means every file under it."""
    path = Path(template)
    if not path.is_absolute():
        path = Path(package_root) / path
    if path.is_dir():
        return sorted(str(p) for p in path.rglob("*") if p.is_file())
    pattern = re.sub(r"\{[^{}]+\}", "*", str(path))
    return sorted(p for p in glob.glob(pattern) if os.path.isfile(p))


def _stat(path: str) -> Tuple[int, int]:
    st = os.stat(path)
    return int(st.st_size), int(st.st_mtime)


SOURCE_FREEZE = "freeze"


def scan_stores(packages: Sequence[Any], index: Mapping[str, Dict[str, Any]], fail: Callable[..., None],
                echo: Callable[[str], None]) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Dict[str, Any]]]:
    """Round 1 (cheap, no hashing): per package, the store files each template names; one record per file.
    A file inputs.json lists takes its hash after a size and time check; any other file is marked
    source 'freeze' with sha256 None, to be hashed in round 2 (hash_store_files)."""
    per_package: Dict[str, List[Dict[str, Any]]] = {}
    files: Dict[str, Dict[str, Any]] = {}
    for pkg in packages:
        name = pkg.dataset.name
        rows = []
        for role, template in store_templates(pkg):
            paths = template_files(pkg.root, template)
            if not paths:
                fail("F-STORES", "store template %s %r matches no file" % (role, template), name)
                continue
            fresh = 0
            for p in paths:
                key = _norm_key(p)
                if key in files:
                    continue
                size, mtime = _stat(p)
                entry = index.get(key)
                if entry is not None:
                    if (int(entry["size"]), int(entry["mtime"])) != (size, mtime):
                        fail("F-STORES", "%s changed since inputs.json (size %s -> %s, mtime %s -> %s): re-hash the "
                             "input stores before the freeze" % (p, entry["size"], size, entry["mtime"], mtime), name)
                        continue
                    files[key] = {"path": p, "size": size, "mtime": mtime, "sha256": entry["sha256"],
                                  "source": INPUTS_FILE}
                else:
                    files[key] = {"path": p, "size": size, "mtime": mtime, "sha256": None, "source": SOURCE_FREEZE}
                    fresh += size
            echo("  %s %s %s: %d files%s" % (name, role, template, len(paths),
                                             ", %s to hash (not in inputs.json)" % C.gib(fresh) if fresh else ""))
            rows.append({"role": role, "template": template,
                         "files": [files[_norm_key(p)]["path"] for p in paths if _norm_key(p) in files]})
        per_package[name] = rows
    return per_package, files


def hash_store_files(files: Mapping[str, Dict[str, Any]], fail: Callable[..., None],
                     echo: Callable[[str], None]) -> int:
    """Round 2: hash every store file inputs.json does not list, and refuse one that changed (size or time)
    while it was read. Returns the bytes hashed."""
    hashed = 0
    for key in sorted(files):
        rec = files[key]
        if rec["source"] != SOURCE_FREEZE:
            continue
        rec["sha256"] = C.sha256_file(rec["path"])
        hashed += rec["size"]
        if _stat(rec["path"]) != (rec["size"], rec["mtime"]):
            fail("F-STORES", "%s changed while the freeze read it (size %s, mtime %s before): run the freeze again "
                 "when nothing writes the stores" % (rec["path"], rec["size"], rec["mtime"]))
    echo("hashed %s of store files that inputs.json does not list" % C.gib(hashed))
    return hashed


def collect_stores(packages: Sequence[Any], index: Mapping[str, Dict[str, Any]], fail: Callable[..., None],
                   echo: Callable[[str], None]) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Dict[str, Any]]]:
    """Both rounds at once (scan_stores, then hash_store_files): every record carries its SHA-256."""
    per_package, files = scan_stores(packages, index, fail, echo)
    hash_store_files(files, fail, echo)
    return per_package, files


# ===================================================================================== launch pins
def launch_pins(version_pin_record: Mapping[str, Any]) -> Dict[str, Any]:
    """The thread pins the launcher sets (read from the launcher itself, in a fresh interpreter whose
    environment holds none of the variables the launcher refuses), the worker constants and the version pins."""
    from treeroute import engine_constants as K
    from treeroute import launch

    env = {k: v for k, v in os.environ.items()
           if k.upper() not in launch.PIN_ENV_VARS and k not in launch.foreign_environment({k: v})}
    code = ("import json, os\nfrom treeroute import launch\nlaunch.pin_environment()\n"
            "print('PINS ' + json.dumps({v: os.environ[v] for v in launch.PIN_ENV_VARS}, sort_keys=True))\n")
    proc = subprocess.run([sys.executable, "-c", code], cwd=str(C.ENGINE_DIR), env=env, capture_output=True,
                          text=True, timeout=120)
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("PINS ")]
    if proc.returncode != 0 or not lines:
        raise ReportRefusal("F-PINS", "the launcher's pins could not be read: %s" % (proc.stderr.strip()[-400:]))
    return {"env_pins": json.loads(lines[-1][len("PINS "):]),
            "workers": {"forest_threads": K.FOREST_THREADS, "blas_threads": K.BLAS_THREADS,
                        "tree_predict_workers": K.TREE_PREDICT_WORKERS, "router_workers": K.ROUTER_WORKERS,
                        "router_worker_blas_threads": K.ROUTER_WORKER_BLAS_THREADS,
                        "sklearnex_required": K.SKLEARNEX_REQUIRED},
            "refused_environment": {"prefixes": list(launch.FOREIGN_ENV_PREFIXES),
                                    "names": list(launch.FOREIGN_ENV_NAMES)},
            "version_pins": dict(version_pin_record)}


def python_record() -> Dict[str, Any]:
    from treeroute.runs.fingerprint import library_versions

    return {"python_version": platform.python_version(), "implementation": platform.python_implementation(),
            "sys_version": sys.version, "libraries": library_versions()}


# ========================================================================================== freeze
def freeze(package_paths: Sequence[Any], run_root: Any, registry_dir: Any,
           engine_code_sha256: Optional[Callable[[], str]] = None, prereg_draft: Any = DEFAULT_PREREG,
           echo: Callable[[str], None] = print, now: Any = None) -> Dict[str, Any]:
    """Check every precondition, then write the lock (and the filled pre-registration) once.

    ``engine_code_sha256`` defaults to the contract function (common.contract_engine_code_sha256); tests
    pass their own. Returns {lock, lock_sha256, prereg, prereg_sha256, unfilled}. Raises FreezeRefusal listing
    every failed precondition; nothing is written then."""
    from treeroute import engine_constants as K
    from treeroute.errors import PackageError
    from treeroute.package.load import load_package
    from treeroute.pipeline.draft import DRAFT_RULE, draft_status
    from treeroute.runs.atomic import dumps, write_text_once
    from treeroute.runs.fingerprint import engine_code_hash

    run_root, registry_dir = Path(run_root), Path(registry_dir)
    moment = now if now is not None else C.utc_now()
    failures: List[Tuple[str, Optional[str], str]] = []

    def fail(fid: str, msg: str, pkg: Optional[str] = None) -> None:
        failures.append((fid, pkg, msg))

    guard = C.WriteGuard(registry_dir, own_registry_subdirs=(FREEZE_SUBDIR,))
    lock_path = guard.check(registry_dir / FREEZE_SUBDIR / ("%s%s%s" % (LOCK_PREFIX, C.utc_stamp(moment), LOCK_SUFFIX)))
    prereg_path = guard.check(registry_dir / FREEZE_SUBDIR / ("%s%s.md" % (PREREG_PREFIX, C.utc_stamp(moment))))

    if not package_paths:
        fail("F-NAMES", "no package was named")
    engine_sha = None
    try:
        engine_sha = (engine_code_sha256 or C.contract_engine_code_sha256)()
    except ReportRefusal as exc:
        fail("F-ENGINE-HASH", str(exc))
    stripped = engine_code_hash()
    tooling = None
    try:
        tooling = C.report_file_hashes()
    except ReportRefusal as exc:
        fail("F-TOOLING", str(exc))
    awaiting: List[Dict[str, Any]] = []
    try:
        constants = C.constants_with_origins()
        refused = [r["id"] for r in constants if r["status"] in CONSTANT_STATUSES_REFUSED]
        if refused:
            fail("F-CONSTANTS", "engine constants not fixed yet (status %s): %s"
                 % ("/".join(CONSTANT_STATUSES_REFUSED), ", ".join(refused)))
        no_origin = [r["id"] for r in constants if not r["origin"]]
        if no_origin:
            fail("F-CONSTANTS", "engine constants without an origin comment: %s" % ", ".join(no_origin))
        awaiting = [{"id": r["id"], "status": r["status"]} for r in constants
                    if r["status"] in CONSTANT_STATUSES_TO_CONFIRM]
    except ReportRefusal as exc:
        constants = []
        fail("F-CONSTANTS", str(exc))
    try:
        pins = C.version_pins()
        drift = {k: (v, pins["installed"].get(k)) for k, v in pins["pins"].items() if pins["installed"].get(k) != v}
        if drift:
            fail("F-PINS", "installed versions differ from the pins: %s"
                 % "; ".join("%s pinned %s, installed %s" % (k, a, b) for k, (a, b) in sorted(drift.items())))
    except ReportRefusal as exc:
        pins = None
        fail("F-PINS", str(exc))
    pins_record = None
    if pins is not None:
        try:
            pins_record = launch_pins(pins)
        except ReportRefusal as exc:
            fail("F-PINS", str(exc))
    inputs_meta, index = None, {}
    try:
        inputs_meta, index = load_inputs(registry_dir)
    except ReportRefusal as exc:
        fail("F-INPUTS", str(exc))
    draft_text = None
    try:
        draft_text = Path(prereg_draft).read_text(encoding="utf-8")
        PLACEHOLDER_CHECK.sub(lambda m: _known_placeholder(m), draft_text)
    except OSError as exc:
        fail("F-PREREG", "the pre-registration draft %s cannot be read: %s" % (prereg_draft, exc))
    except ReportRefusal as exc:
        fail("F-PREREG", str(exc))
    if draft_text is not None:
        pending = pending_items(draft_text)
        if pending:
            fail("F-PREREG", "the pre-registration draft %s still has %d open item(s) marked %s (lines %s): %s; "
                 "settle each and remove its marker"
                 % (prereg_draft, len(pending), " / ".join(PENDING_MARKERS), ", ".join(str(m["line"]) for m in pending),
                    "; ".join("line %d: %s" % (m["line"], m["text"][:100]) for m in pending[:5])))

    loaded, records = [], {}
    names = []
    for raw in package_paths:
        try:
            pkg = load_package(raw)
        except PackageError as exc:
            fail("F-PACKAGE", "%s: %s" % (raw, exc))
            continue
        name = pkg.dataset.name
        if name in names:
            fail("F-NAMES", "package %s is named twice" % name)
            continue
        names.append(name)
        loaded.append(pkg)

        def pfail(fid, msg, _n=name):
            fail(fid, msg, _n)
        draft = draft_status(pkg)
        if draft.is_draft:
            pfail("F-DRAFT", "the package is a DRAFT (%s: stamp %r in %s): its runs can never be headline runs, so it "
                  "is not frozen; freeze the real package" % (DRAFT_RULE, draft.stamp, ", ".join(draft.where)))
        try:
            smoke = C.package_smoke_groups(pkg)
        except ReportRefusal as exc:
            smoke = None
            pfail("F-CHECK-GROUPS", str(exc))
        check = _read_check_report(run_root, name, pkg.fingerprint, engine_sha, pfail, smoke)
        ban = open_verdicts(pkg)
        if ban["keep_unreviewed"]:
            pfail("F-BAN-OPEN", "%d keep_unreviewed verdict(s): %s" % (len(ban["keep_unreviewed"]),
                                                                       ", ".join(ban["keep_unreviewed"][:10])))
        if ban["open_decision_markers"]:
            marks = ban["open_decision_markers"]
            pfail("F-BAN-OPEN", "ban.yaml records %d open owner decision(s): %s%s"
                  % (len(marks), "; ".join("line %d: %s" % (m["line"], m["text"][:120]) for m in marks[:5]),
                     "; ... and %d more (lines %s)" % (len(marks) - 5, ", ".join(str(m["line"]) for m in marks[5:]))
                     if len(marks) > 5 else ""))
        plan = _plan_record(run_root, name, pkg.fingerprint, stripped, pfail)
        records[name] = {"name": name, "version": pkg.dataset.version, "path": str(pkg.root),
                         "fingerprint": pkg.fingerprint, "draft": draft.record(), "file_hashes": dict(pkg.file_hashes),
                         "include_hashes": dict(pkg.include_hashes), "check_report": check, "plan": plan,
                         "ban": {"verdict_counts": _verdict_counts(pkg), "open": ban}}
    stores, files = scan_stores(loaded, index, fail, echo) if loaded else ({}, {})
    if failures:
        raise FreezeRefusal(failures)

    # round 2: hash the store files inputs.json does not list; nothing may change while the freeze runs
    echo("all checks hold; hashing the store files inputs.json does not list")
    hash_store_files(files, fail, echo)
    engine_files = C.engine_file_hashes()
    try:
        again = (engine_code_sha256 or C.contract_engine_code_sha256)()
    except ReportRefusal as exc:
        again = str(exc)
    if again != engine_sha or engine_code_hash() != stripped:
        fail("F-ENGINE-HASH", "the engine code changed while the freeze ran (%s... then %s...): run it again when "
             "no one edits the engine" % (str(engine_sha)[:16], str(again)[:16]))
    try:
        tooling_again = C.report_file_hashes()
    except ReportRefusal as exc:
        tooling_again = {"(unreadable)": str(exc)}
    if tooling_again != tooling:
        changed = sorted(k for k in set(tooling) | set(tooling_again) if tooling.get(k) != tooling_again.get(k))
        fail("F-TOOLING", "the report tooling changed while the freeze ran (%s): run it again when no one edits "
             "treeroute_report" % ", ".join(changed))
    if failures:
        raise FreezeRefusal(failures)
    for name in records:
        records[name]["stores"] = stores[name]
    if awaiting:
        echo("NOTE: %d engine constant(s) await the owner's confirmation (status %s; listed in the lock and the "
             "pre-registration): %s" % (len(awaiting), "/".join(CONSTANT_STATUSES_TO_CONFIRM),
                                        ", ".join(r["id"] for r in awaiting)))
    lock = {
        "lock_format": LOCK_FORMAT, "created_utc": C.utc_iso(moment), "run_root": str(run_root),
        "registry_dir": str(registry_dir),
        "engine": {"engine_code_sha256": engine_sha, "contract_function": "%s.%s" % (C.CONTRACT_MODULE,
                                                                                     C.CONTRACT_FUNCTION),
                   "engine_code_hash_comment_stripped": stripped, "files": engine_files},
        "report_tooling": {"root": str(C.REPORT_DIR), "suffixes": list(C.REPORT_TOOLING_SUFFIXES),
                           "sha256": report_tooling_sha256(tooling), "files": tooling},
        "engine_constants": {"constants_hash": K.constants_hash(),
                             "file_sha256": C.sha256_file(C.CONSTANTS_FILE), "constants": constants,
                             "awaiting_owner": awaiting,
                             "statuses_refused": list(CONSTANT_STATUSES_REFUSED),
                             "statuses_awaiting_owner": list(CONSTANT_STATUSES_TO_CONFIRM)},
        "packages": [records[n] for n in sorted(records)],
        "store_files": {files[k]["path"]: {kk: vv for kk, vv in files[k].items() if kk != "path"}
                        for k in sorted(files)},
        "inputs": inputs_meta,
        "python": python_record(),
        "launch_pins": pins_record,
        "no_op_rule": NO_OP_RULE,
        "preconditions": list(PRECONDITIONS),
    }
    text = dumps(lock) + "\n"
    lock_sha = C.sha256_text(text)
    filled, unfilled = fill_preregistration(draft_text, lock, lock_path, lock_sha)   # before any write
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    write_text_once(lock_path, text)
    echo("lock written: %s" % lock_path)
    echo("lock sha256 %s" % lock_sha)
    write_text_once(prereg_path, filled)
    prereg_sha = C.sha256_text(filled)
    echo("pre-registration filled: %s (sha256 %s)" % (prereg_path, prereg_sha))
    if unfilled:
        echo("NOT FILLED (marked in the file): %s" % ", ".join(unfilled))
    return {"lock": lock_path, "lock_sha256": lock_sha, "prereg": prereg_path, "prereg_sha256": prereg_sha,
            "unfilled": unfilled}


def _verdict_counts(pkg: Any) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for v in pkg.ban.verdicts.values():
        counts[v.verdict] = counts.get(v.verdict, 0) + 1
    return dict(sorted(counts.items()))


# =============================================================================== pre-registration
def _derived_settings(plan_folder: Optional[str]) -> Optional[str]:
    """A short markdown list of the settings plan.json shows (no number typed here)."""
    if plan_folder is None:
        return None
    plan = json.loads((Path(plan_folder) / "plan.json").read_text(encoding="utf-8"))
    w = plan.get("windows") or {}
    scored = plan.get("scored_units") or {}
    bank = plan.get("bank_units") or {}
    lines = [
        "router kind %s; links %s" % (plan.get("router_kind"), ", ".join(map(str, plan.get("links") or []))),
        "coverage %s-%s; test years %s; donor train end %s; inner fit %s; inner score %s"
        % (w.get("y0"), w.get("y_end"), ", ".join(map(str, w.get("test_years") or [])), w.get("train_end"),
           "-".join(map(str, w.get("inner_fit") or [])), "-".join(map(str, w.get("inner_score") or []))),
        "groups %s; bank units %d; scored units %d; trees per group %s"
        % (plan.get("groups"), sum(bank.values()), sum(scored.values()), plan.get("trees_per_group")),
        "leads %s (plus the lead-0 contract); history columns %s"
        % (", ".join(map(str, plan.get("leads") or [])), ", ".join(plan.get("history_columns") or [])),
        "overlap blocks with more than one group: %s" % (len(plan.get("overlap_blocks") or [])),
        "tree features %s; router context %s" % (plan.get("tree_features"), ", ".join(plan.get("context") or []) or "none"),
    ]
    return "\n".join("  - " + ln for ln in lines)


GLOBAL_FIELDS = ("LOCK_FILE", "LOCK_SHA256", "LOCK_CREATED_UTC", "ENGINE_CODE_SHA256", "ENGINE_CODE_HASH_STRIPPED",
                 "ENGINE_CONSTANTS_SHA256", "PYTHON_VERSION", "REPORT_TOOLING_SHA256", "CONSTANTS_AWAITING_OWNER")


def report_tooling_sha256(files: Mapping[str, str]) -> str:
    """One SHA-256 over the report tooling's sorted (relative path, file SHA-256) list (printed in the
    pre-registration; the lock keeps the per-file listing)."""
    return C.sha256_text(json.dumps(sorted(files.items()), separators=(",", ":")))


def _awaiting_text(rows: Sequence[Mapping[str, Any]]) -> str:
    if not rows:
        return "none"
    return "%d: %s" % (len(rows), ", ".join("%s (%s)" % (r["id"], r["status"]) for r in rows))
PACKAGE_FIELDS = ("PACKAGE_FINGERPRINT", "CHECK_REPORT_SHA256", "DERIVED_SHA256", "PLAN_SHA256", "DERIVED_SETTINGS")
PLACEHOLDER_CHECK = PLACEHOLDER


def pending_items(draft: str) -> List[Dict[str, Any]]:
    """F-PREREG: the draft's lines that still carry a bold pending marker (PENDING_MARKERS)."""
    return [{"line": no, "marker": m.group(1), "text": line.strip()}
            for no, line in enumerate(draft.splitlines(), 1) for m in [PENDING_MARKER.search(line)] if m]


def _known_placeholder(match: Any) -> str:
    """Refuse an unknown placeholder (checked before the freeze writes anything)."""
    field, pkg = match.group(1), match.group(2)
    known = GLOBAL_FIELDS if pkg is None else PACKAGE_FIELDS
    if field not in known:
        raise ReportRefusal("F-PREREG", "unknown placeholder {{%s%s}} in the pre-registration draft (known: %s; "
                            "per package: %s)" % (field, "" if pkg is None else ":" + pkg, ", ".join(GLOBAL_FIELDS),
                                                  ", ".join(PACKAGE_FIELDS)))
    return match.group(0)


def fill_preregistration(draft: str, lock: Mapping[str, Any], lock_path: Path, lock_sha: str) -> Tuple[str, List[str]]:
    """Replace the draft's {{PLACEHOLDER}} / {{PLACEHOLDER:package}} fields with the lock's values.

    Known fields: GLOBAL_FIELDS (LOCK_FILE, LOCK_SHA256, LOCK_CREATED_UTC, ENGINE_CODE_SHA256,
    ENGINE_CODE_HASH_STRIPPED, ENGINE_CONSTANTS_SHA256, PYTHON_VERSION, REPORT_TOOLING_SHA256,
    CONSTANTS_AWAITING_OWNER), and per package PACKAGE_FIELDS (PACKAGE_FINGERPRINT, CHECK_REPORT_SHA256,
    DERIVED_SHA256, PLAN_SHA256, DERIVED_SETTINGS). A package that is not in this freeze, or has no plan, is
    written as a visible 'NOT FILLED' marker and listed. An unknown field refuses (a typo must not pass)."""
    packages = {p["name"]: p for p in lock["packages"]}
    unfilled: List[str] = []
    glob_values = {"LOCK_FILE": str(lock_path), "LOCK_SHA256": lock_sha, "LOCK_CREATED_UTC": lock["created_utc"],
                   "ENGINE_CODE_SHA256": lock["engine"]["engine_code_sha256"],
                   "ENGINE_CODE_HASH_STRIPPED": lock["engine"]["engine_code_hash_comment_stripped"],
                   "ENGINE_CONSTANTS_SHA256": lock["engine_constants"]["constants_hash"],
                   "PYTHON_VERSION": lock["python"]["python_version"],
                   "REPORT_TOOLING_SHA256": report_tooling_sha256(lock["report_tooling"]["files"]),
                   "CONSTANTS_AWAITING_OWNER": _awaiting_text(lock["engine_constants"]["awaiting_owner"])}
    def value(match):
        _known_placeholder(match)
        field, pkg = match.group(1), match.group(2)
        if pkg is None:
            return str(glob_values[field])
        rec = packages.get(pkg)
        if rec is None:
            unfilled.append("%s:%s" % (field, pkg))
            return "**NOT FILLED: %s is not in this freeze**" % pkg
        plan = rec.get("plan")
        if field == "PACKAGE_FINGERPRINT":
            return rec["fingerprint"]
        if field == "CHECK_REPORT_SHA256":
            return rec["check_report"]["sha256"]
        if plan is None:
            unfilled.append("%s:%s" % (field, pkg))
            return "**NOT FILLED: %s has no plan (run 'py -3.9 -m treeroute plan' before the freeze)**" % pkg
        if field == "DERIVED_SHA256":
            return plan["derived_json_sha256"]
        if field == "PLAN_SHA256":
            return plan["plan_json_sha256"]
        return _derived_settings(plan["folder"])

    filled = PLACEHOLDER.sub(value, draft)
    return filled, unfilled


# ========================================================================================== verify
def latest_lock(registry_dir: Path) -> Path:
    folder = Path(registry_dir) / FREEZE_SUBDIR
    locks = sorted(folder.glob("%s*%s" % (LOCK_PREFIX, LOCK_SUFFIX))) if folder.is_dir() else []
    if not locks:
        raise ReportRefusal("VERIFY", "no freeze lock in %s" % folder, fix="run the freeze first")
    return locks[-1]


def _diff_maps(what: str, locked: Mapping[str, str], now: Mapping[str, str], affects: str) -> List[Dict[str, Any]]:
    out = []
    for key in sorted(set(locked) | set(now)):
        a, b = locked.get(key), now.get(key)
        if a != b:
            change = "added" if a is None else "removed" if b is None else "changed"
            out.append({"what": what, "item": key, "change": change, "locked": a, "now": b, "affects": affects})
    return out


def verify(lock_path: Any = None, registry_dir: Any = None, rehash_inputs: bool = False,
           engine_code_sha256: Optional[Callable[[], str]] = None, echo: Callable[[str], None] = print,
           write_report: bool = True, now: Any = None) -> Dict[str, Any]:
    """Re-hash what the lock recorded and list every drift. Returns {lock, drift, affected, report}."""
    from treeroute.errors import PackageError
    from treeroute.package.load import load_package
    from treeroute.pipeline.draft import draft_status
    from treeroute.runs.atomic import dumps, write_text_once
    from treeroute.runs.fingerprint import engine_code_hash

    if lock_path is None:
        if registry_dir is None:
            raise ReportRefusal("VERIFY", "name the lock file or the registry folder")
        lock_path = latest_lock(Path(registry_dir))
    lock_path = Path(lock_path)
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("lock_format") != LOCK_FORMAT:
        raise ReportRefusal("VERIFY", "%s is not a %s lock" % (lock_path, LOCK_FORMAT))
    registry_dir = Path(registry_dir) if registry_dir is not None else Path(lock["registry_dir"])
    ALL = "all packages"
    drift: List[Dict[str, Any]] = []
    drift += _diff_maps("engine file", lock["engine"]["files"], C.engine_file_hashes(), ALL)
    try:
        tooling_now = C.report_file_hashes()
    except ReportRefusal as exc:
        tooling_now = {"(unreadable)": str(exc)}
    drift += _diff_maps("report tooling file (treeroute_report)", lock["report_tooling"]["files"], tooling_now, ALL)
    try:
        sha = (engine_code_sha256 or C.contract_engine_code_sha256)()
    except ReportRefusal as exc:
        sha = "cannot compute: %s" % exc
    if sha != lock["engine"]["engine_code_sha256"]:
        drift.append({"what": "engine_code_sha256", "item": "engine", "change": "changed",
                      "locked": lock["engine"]["engine_code_sha256"], "now": sha, "affects": ALL})
    stripped = engine_code_hash()
    if stripped != lock["engine"]["engine_code_hash_comment_stripped"]:
        drift.append({"what": "engine code hash (comments stripped)", "item": "engine", "change": "changed",
                      "locked": lock["engine"]["engine_code_hash_comment_stripped"], "now": stripped, "affects": ALL})
    locked_k = {r["id"]: json.dumps([r["value"], r["status"], r["test_exposed"], r["origin"]])
                for r in lock["engine_constants"]["constants"]}
    try:
        now_k = {r["id"]: json.dumps([r["value"], r["status"], r["test_exposed"], r["origin"]])
                 for r in C.constants_with_origins()}
    except ReportRefusal as exc:
        now_k = {"(unreadable)": str(exc)}
    drift += _diff_maps("engine constant (value, status, test-exposed, origin)", locked_k, now_k, ALL)
    for pkg in lock["packages"]:
        name = pkg["name"]
        try:
            loaded = load_package(pkg["path"])
        except PackageError as exc:
            drift.append({"what": "package", "item": name, "change": "fails to load", "locked": pkg["fingerprint"],
                          "now": str(exc)[:300], "affects": name})
            continue
        if loaded.fingerprint != pkg["fingerprint"]:
            drift.append({"what": "package fingerprint", "item": name, "change": "changed",
                          "locked": pkg["fingerprint"], "now": loaded.fingerprint, "affects": name})
        draft_now = draft_status(loaded).record()
        if draft_now != pkg["draft"]:
            drift.append({"what": "package draft status", "item": name, "change": "changed",
                          "locked": pkg["draft"], "now": draft_now, "affects": name})
        drift += _diff_maps("package file (%s)" % name, pkg["file_hashes"], loaded.file_hashes, name)
        drift += _diff_maps("included store catalog (%s)" % name, pkg["include_hashes"], loaded.include_hashes, name)
        rep = pkg.get("check_report") or {}
        locked_groups = (rep.get("checked_groups") or {}).get("groups")
        if locked_groups is not None:
            try:
                now_groups = C.package_smoke_groups(loaded, rule="VERIFY")["groups"]
            except ReportRefusal as exc:
                now_groups = "cannot be listed: %s" % exc
            if now_groups != locked_groups:
                drift.append({"what": "R21 smoke groups (ruling M2)", "item": name, "change": "changed",
                              "locked": locked_groups, "now": now_groups, "affects": name})
        if rep.get("path"):
            now_sha = C.sha256_file(rep["path"]) if os.path.isfile(rep["path"]) else None
            if now_sha != rep["sha256"]:
                drift.append({"what": "check report", "item": rep["path"], "change": "changed" if now_sha else "removed",
                              "locked": rep["sha256"], "now": now_sha, "affects": name})
        plan = pkg.get("plan")
        if plan:
            for fname, key in (("derived.json", "derived_json_sha256"), ("plan.json", "plan_json_sha256")):
                p = Path(plan["folder"]) / fname
                now_sha = C.sha256_file(p) if p.is_file() else None
                if now_sha != plan[key]:
                    drift.append({"what": "plan file", "item": str(p), "change": "changed" if now_sha else "removed",
                                  "locked": plan[key], "now": now_sha, "affects": name})
        for store in pkg.get("stores") or []:
            now_files = set(_norm_key(p) for p in template_files(Path(pkg["path"]), store["template"]))
            locked_files = set(_norm_key(p) for p in store["files"])
            for added in sorted(now_files - locked_files):
                drift.append({"what": "store file", "item": added, "change": "added (matches %s)" % store["template"],
                              "locked": None, "now": "present", "affects": name})
    hashed = 0
    for path, rec in sorted(lock["store_files"].items()):
        if not os.path.isfile(path):
            drift.append({"what": "store file", "item": path, "change": "removed", "locked": rec["sha256"], "now": None,
                          "affects": _owners(lock, path)})
            continue
        size, mtime = _stat(path)
        if (size, mtime) != (rec["size"], rec["mtime"]):
            drift.append({"what": "store file", "item": path, "change": "size or time changed",
                          "locked": [rec["size"], rec["mtime"]], "now": [size, mtime], "affects": _owners(lock, path)})
        if rehash_inputs:
            now_sha = C.sha256_file(path)
            hashed += size
            if now_sha != rec["sha256"]:
                drift.append({"what": "store file", "item": path, "change": "content changed", "locked": rec["sha256"],
                              "now": now_sha, "affects": _owners(lock, path)})
    if rehash_inputs:
        echo("re-hashed %d store files (%s)" % (len(lock["store_files"]), C.gib(hashed)))
    inputs = lock.get("inputs") or {}
    if inputs.get("path"):
        now_sha = C.sha256_file(inputs["path"]) if os.path.isfile(inputs["path"]) else None
        if now_sha != inputs["sha256"]:
            drift.append({"what": "inputs.json", "item": inputs["path"], "change": "changed", "locked": inputs["sha256"],
                          "now": now_sha, "affects": ALL})
    py_now = python_record()
    for key in ("python_version", "implementation"):
        if py_now[key] != lock["python"][key]:
            drift.append({"what": "python", "item": key, "change": "changed", "locked": lock["python"][key],
                          "now": py_now[key], "affects": ALL})
    drift += _diff_maps("library version", {k: str(v) for k, v in lock["python"]["libraries"].items()},
                        {k: str(v) for k, v in py_now["libraries"].items()}, ALL)
    try:
        pins_now = launch_pins(C.version_pins())
        for key in ("env_pins", "workers", "version_pins"):
            a, b = lock["launch_pins"][key], pins_now[key]
            if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True):
                drift.append({"what": "launch pins", "item": key, "change": "changed", "locked": a, "now": b,
                              "affects": ALL})
    except ReportRefusal as exc:
        drift.append({"what": "launch pins", "item": "all", "change": "unreadable", "locked": None, "now": str(exc),
                      "affects": ALL})
    affected = sorted(set(d["affects"] for d in drift))
    if ALL in affected:
        affected = [ALL]
    result = {"lock": str(lock_path), "lock_sha256": C.sha256_file(lock_path), "drift": drift,
              "affected": affected, "rehash_inputs": bool(rehash_inputs), "no_op_rule": NO_OP_RULE}
    if not drift:
        echo("verify: no drift against %s" % lock_path.name)
    else:
        echo("verify: %d drift item(s) against %s" % (len(drift), lock_path.name))
        for d in drift[:60]:
            echo("  %s | %s | %s | affects %s" % (d["what"], d["item"], d["change"], d["affects"]))
        if len(drift) > 60:
            echo("  ... and %d more (in the verify report)" % (len(drift) - 60))
        echo("affected: %s. %s" % (", ".join(affected), NO_OP_RULE))
    if write_report:
        moment = now if now is not None else C.utc_now()
        guard = C.WriteGuard(registry_dir, own_registry_subdirs=(FREEZE_SUBDIR,))
        stem = lock_path.name[:-len(LOCK_SUFFIX)] if lock_path.name.endswith(LOCK_SUFFIX) else lock_path.stem
        out = guard.check(lock_path.parent / ("%s%s_%s.json" % (VERIFY_PREFIX, stem, C.utc_stamp(moment))))
        write_text_once(out, dumps(dict(result, verified_utc=C.utc_iso(moment))) + "\n")
        result["report"] = str(out)
        echo("verify report: %s" % out)
    return result


def _owners(lock: Mapping[str, Any], path: str) -> str:
    key = _norm_key(path)
    owners = sorted(p["name"] for p in lock["packages"]
                    if any(_norm_key(f) == key for s in (p.get("stores") or []) for f in s["files"]))
    return "+".join(owners) or "unknown"


# ============================================================================================= CLI
def _parser_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--run-root", default=None, help="run root (default: run_root in config/machine.yaml)")
    parser.add_argument("--registry-dir", default=None,
                        help="registry folder (default: registry_dir in config/machine.yaml)")


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if args and args[0] == "verify":
            parser = argparse.ArgumentParser(prog="python -m treeroute_report.freeze verify",
                                             description="Re-hash everything the freeze lock recorded; list drift.")
            parser.add_argument("lock", nargs="?", default=None, help="lock file (default: the newest lock)")
            parser.add_argument("--rehash-inputs", action="store_true",
                                help="re-hash every store file (slow); by default size and time are compared")
            _parser_common(parser)
            ns = parser.parse_args(args[1:])
            registry = ns.registry_dir or (None if ns.lock else C.machine_defaults()["registry_dir"])
            res = verify(ns.lock, registry, rehash_inputs=ns.rehash_inputs)
            return EXIT_DRIFT if res["drift"] else 0
        parser = argparse.ArgumentParser(prog="python -m treeroute_report.freeze",
                                         description="Freeze: check every precondition, then write the lock once.")
        parser.add_argument("packages", nargs="+", help="dataset package folders")
        parser.add_argument("--prereg", default=str(DEFAULT_PREREG), help="the pre-registration draft to fill")
        _parser_common(parser)
        ns = parser.parse_args(args)
        defaults = C.machine_defaults() if not (ns.run_root and ns.registry_dir) else {}
        freeze(ns.packages, ns.run_root or defaults["run_root"], ns.registry_dir or defaults["registry_dir"],
               prereg_draft=ns.prereg)
        return 0
    except TreerouteError as exc:     # ReportRefusal, FreezeRefusal, RegistryError, RegistryRefusal, write-once
        print("refused: %s" % exc, file=sys.stderr)
        return EXIT_REFUSED


if __name__ == "__main__":
    sys.exit(main())
