"""The rivals export (SPEC_RIVALS.md section 2): one finished run in, per lead the rows and columns our model
used, written as per-group parquet files with fail-loud identity and parity checks.

    py -3.9 -m rivals.cli export --run <run folder> [--package <package folder>] --lead <L|all>
                                 [--roles <list>] [--config <rivals.yaml>] [--resume] [--full-engine-checks]
    py -3.9 -m rivals.cli export --write-lineage [--proof <no-op proof summary> ...] [--config <rivals.yaml>]

Plug and predict: nothing here names a problem. Everything is read from the run folder, its package and the
LIVE engine (imported read-only from rivals.yaml's engine_root; no engine file is opened for writing).

Order (section 2): the identity checks I1-I4 and I8 read files only; I9 takes the engine's heavy-job lock
(Pipeline._lock); the engine's own load, groups, target pre-flight, read and derive run; I5-I7 compare the
rebuilt run config, the run fingerprint and derived.json; then, per lead, the engine's own pools, FitContext
hand-outs and normals give the rows; the per-group files are written atomically with a progress record;
the parity checks P1-P14 run (and P15, the bank-fingerprint check, with --p15 or when the run has an accepted
engine difference: rivals.yaml 'accepted_engine_differences', which then needs EVERY check P1-P15 to pass);
export_manifest.json is written LAST.

Lean export (owner ruling AA4, the default): two engine guard steps that change no exported value are taken from
the run's own record instead of being measured again (LEAN_STEPS: R30's test-year count over every census row, and
the per-group separability check on a sample); I5-I7 and P1-P14 always run in full and decide, and P15 runs with
--p15 or when the run has an accepted engine difference. --full-engine-checks runs every engine step; the exported
files are the same bytes either way (tests/test_aa_speedups.py).

Test labels are never read: no test file holds a y column, the run's test_preds are read with key, normal and
legal columns only, open_test_labels is never called.
"""

import argparse
import gc
import io
import json
import os
import platform
import re
import shutil
import sys
import time
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from rivals import layout as LY

GIB = float(1 << 30)
DISK_SLACK_BYTES = 3 * (1 << 30)          # I8: one lead's export + 3 GiB (SPEC_RIVALS.md 2.2)
LINEAGE_FORMAT = "rivals-engine-lineage/1"
CODE_FILES = (Path(__file__).resolve(), Path(LY.__file__).resolve())
RUN_FILES = ("DONE.json", "manifest.json", "derived.json", "plan.json", "fitctx_log.parquet",
             "inner_preds.parquet", "test_preds.parquet")
LEAD_FILES = ("test_preds.parquet", "guard_preds.parquet")
LADDER_DIR = "ladder"
TEST_KEY_COLUMNS = ["unit", "group", "time", "lead", "issue", "normal", "legal_min", "legal_max"]
DONOR_MEDIAN_COLUMN = "base__donor_median"
# purposes of the run's fitctx_log hand-outs the parity reads (pipeline/passes.py, pipeline/ladder.py)
LOG_PURPOSE = {LY.ROLE_REFIT: ("bank", "fit"), LY.ROLE_TUNE: ("bank_inner", "guard"),
               LY.ROLE_GUARDFIT: ("bank_guard", "guard")}
# the export's own FitContext hand-out purposes (logged in the export's contexts only)
PURPOSE = {LY.ROLE_REFIT: "rival_refit", LY.ROLE_TUNE: "rival_tune", LY.ROLE_GUARDFIT: "rival_guardfit"}
MUST_MATCH = re.compile(r"^MUST-MATCH FILES THAT DIFFER OR ARE MISSING \((\d+)\):")
COMPARE = re.compile(r"^=== COMPARE (\S+) :")
FROM_SHA = re.compile(r"^LIVE engine_code_sha256:\s*([0-9a-f]{64})")
TO_SHA = re.compile(r"^BUILD engine_code_sha256:\s*([0-9a-f]{64})")
RESULT_PASS = "RESULT: PASS"


class ExportRefusal(Exception):
    """The export refused (fail loudly); check names the SPEC_RIVALS.md check (I1 ... P15, ACCEPT)."""

    def __init__(self, check: str, message: str, fix: Optional[str] = None) -> None:
        self.check = check
        self.fix = fix
        text = "export refused [%s]: %s" % (check, message)
        if fix:
            text += " (fix: %s)" % fix
        super().__init__(text)


# ---------------------------------------------------------------------------------------------------
# small helpers
def _read_json(path: Any) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _clean(obj: Any) -> Any:
    """JSON-safe: numpy scalars to Python, non-finite floats to None, tuples to lists."""
    import math

    if isinstance(obj, Mapping):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if hasattr(obj, "item") and not isinstance(obj, (str, bytes)):
        try:
            obj = obj.item()
        except (ValueError, AttributeError):
            pass
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, Path):
        return str(obj).replace("\\", "/")
    if hasattr(obj, "value") and not isinstance(obj, (int, float, str, bool)):
        return _clean(obj.value)
    return obj


def _peak_rss() -> Optional[int]:
    try:
        import psutil

        info = psutil.Process().memory_info()
        return int(getattr(info, "peak_wset", 0) or getattr(info, "rss", 0))
    except Exception:                         # report only: never decides anything
        return None


def code_sha() -> str:
    """The export code sha: rivals/export.py and rivals/layout.py bytes (SPEC_RIVALS.md 2.7)."""
    return LY.code_sha(CODE_FILES)


class Logger(object):
    """Plain lines to the console and, UTC stamped, to every attached export.log (2.8)."""

    def __init__(self, registry: Any, echo: Optional[Callable[[str], None]] = None) -> None:
        self.registry = registry
        self.echo = echo if echo is not None else (lambda s: print(s, flush=True))
        self.files: List[Path] = []
        self.buffer: List[str] = []

    def attach(self, path: Path) -> None:
        if path not in self.files:
            self.files.append(path)
            for line in self.buffer:
                LY.append_line(path, line, self.registry)

    def __call__(self, line: str, only: Optional[Path] = None) -> None:
        text = "%s %s" % (LY.utc_now(), str(line).rstrip())
        self.echo(str(line).rstrip())
        self.buffer.append(text)
        for f in ([only] if only is not None else self.files):
            LY.append_line(f, text, self.registry)


# ---------------------------------------------------------------------------------------------------
# I4: the engine lineage (no-op proof hops from the run's engine to LIVE)
def parse_proof(path: Any) -> Dict[str, Any]:
    """One no-op proof summary: the engine it calls LIVE (from) and BUILD (to), file shas; each COMPARE
    section's package and its must-match count; whether it ends with the PASS line. Refuses a file without
    both shas."""
    text = Path(path).read_text(encoding="utf-8-sig")
    src = dst = None
    packages: Dict[str, int] = {}
    current = None
    passed = False
    for line in text.splitlines():
        s = line.strip()
        m = FROM_SHA.match(s)
        if m:
            src = m.group(1)
        m = TO_SHA.match(s)
        if m:
            dst = m.group(1)
        m = COMPARE.match(s)
        if m:
            current = m.group(1)
        m = MUST_MATCH.match(s)
        if m and current is not None:
            packages[current] = int(m.group(1))
            current = None
        if s.startswith(RESULT_PASS):
            passed = True
    if src is None or dst is None:
        raise ExportRefusal("I4", "the proof file %s names no 'LIVE engine_code_sha256' and 'BUILD "
                            "engine_code_sha256' lines, so it proves no hop" % path)
    return {"from": src, "to": dst, "proof": str(Path(path)).replace("\\", "/"), "proof_sha256": LY.sha256_file(path),
            "packages_must_match": packages, "result_pass": passed}


def freeze_lock_engines(registry_dir: Any) -> List[Dict[str, Any]]:
    """Every freeze lock's engine pair (file sha, comment-stripped hash) under <registry>/freeze."""
    out = []
    for p in sorted(Path(registry_dir).joinpath("freeze").glob("FREEZE_*.lock.json")):
        eng = (_read_json(p).get("engine") or {})
        if eng.get("engine_code_sha256") and eng.get("engine_code_hash_comment_stripped"):
            out.append({"lock": str(p).replace("\\", "/"), "file_sha": eng["engine_code_sha256"],
                        "stripped": eng["engine_code_hash_comment_stripped"]})
    return out


def write_lineage(roots: LY.Roots, proofs: Sequence[Any], echo: Callable[[str], None] = print) -> Path:
    """engine_lineage.json from the registry's freeze locks and the given no-op proof summaries (data,
    never edited by hand). Printed for the owner."""
    LY.import_engine(roots.engine_root)
    from treeroute.runs.fingerprint import engine_code_hash, engine_code_sha256
    from treeroute.runs.machine import load_machine
    from treeroute.runs.registry import Registry

    machine = load_machine(roots.machine_file)
    registry = Registry(machine.registry_dir)
    if not proofs:
        proofs = list(roots.extra.get("lineage_proofs") or [])
    if not proofs:
        raise ExportRefusal("I4", "no proof file was given (--proof, or rivals.yaml 'lineage_proofs')")
    hops = [parse_proof(p) for p in proofs]
    doc = {"format": LINEAGE_FORMAT, "written_utc": LY.utc_now(), "code_sha256": code_sha(),
           "live": {"file_sha": engine_code_sha256(), "stripped": engine_code_hash()},
           "freeze_locks": freeze_lock_engines(machine.registry_dir), "hops": hops,
           "rule": "a hop proves the no-op of its from-engine to its to-engine for a package when its proof file "
                   "still has the recorded sha256, ends with the PASS line, and its COMPARE section of that "
                   "package has must-match count 0"}
    path = LY.lineage_file(roots)
    if path.exists():
        LY.move_aside(path, roots.moved_root, registry)
    LY.write_json_atomic(path, doc, registry)
    echo("engine lineage written: %s" % path)
    echo("LIVE engine: file sha %s, stripped %s" % (doc["live"]["file_sha"][:8], doc["live"]["stripped"][:8]))
    for h in hops:
        echo("hop %s -> %s: %s; must-match counts %s; %s" % (h["from"][:8], h["to"][:8], h["proof"],
                                                          h["packages_must_match"],
                                                          "PASS" if h["result_pass"] else "NO PASS LINE"))
    return path


# ---------------------------------------------------------------------------------------------------
# Accepted engine differences (owner rulings, kept as DATA in rivals.yaml, one entry per RUN ID; nothing here
# names a problem). An entry lets I4 use the listed engine hops that have no parsable no-op proof (each pinned by
# the sha256 of its evidence files) and lets I5 pass the listed run-config keys at exactly the listed run and LIVE
# values. Any other difference still refuses. A run with an entry must then pass EVERY parity check P1-P15
# (P15: the engine's own bank fit on the exported fit rows reproduces the run's recorded bank fingerprints).
ACCEPT_KEY = "accepted_engine_differences"
ACCEPT_ENTRY_KEYS = ("run_id", "run_fingerprint", "ruling", "ruling_source", "live_engine_file_sha",
                     "requires_parity", "I4_hops", "I5_config_keys", "note")
ACCEPT_HOP_KEYS = ("from", "to", "must_match_differences", "evidence", "note")
ACCEPT_CFG_KEYS = ("key", "run", "live", "note")
P_IDS = tuple("P%d" % i for i in range(1, 16))
REQUIRED_PARITY_TEXT = "P1-P15"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _accept_refusal(where: str, message: str) -> ExportRefusal:
    return ExportRefusal("ACCEPT", "rivals.yaml '%s' %s: %s" % (ACCEPT_KEY, where, message),
                         fix="the owner's ruling sets this block; correct the data, never the code")


def accepted_differences(roots: LY.Roots) -> List[Dict[str, Any]]:
    """The config's accepted-difference entries, checked field by field (refuses ACCEPT on any malformed
    entry, an unknown field or two entries for one run id)."""
    raw = roots.extra.get(ACCEPT_KEY)
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise _accept_refusal("", "must be a list of entries")
    out, seen = [], set()
    for i, e in enumerate(raw):
        where = "entry %d" % i
        if not isinstance(e, Mapping):
            raise _accept_refusal(where, "is not a mapping")
        extra = sorted(set(e) - set(ACCEPT_ENTRY_KEYS))
        if extra:
            raise _accept_refusal(where, "has unknown fields %s (allowed: %s)" % (extra, list(ACCEPT_ENTRY_KEYS)))
        for k in ("run_id", "ruling", "ruling_source"):
            if not isinstance(e.get(k), str) or not e[k].strip():
                raise _accept_refusal(where, "needs a non-empty '%s'" % k)
        for k in ("run_fingerprint", "live_engine_file_sha"):
            if not isinstance(e.get(k), str) or not _HEX64.match(e[k]):
                raise _accept_refusal(where, "'%s' must be a full 64-hex sha256" % k)
        if e.get("requires_parity") != REQUIRED_PARITY_TEXT:
            raise _accept_refusal(where, "'requires_parity' must be %r (every parity check must pass)"
                                  % REQUIRED_PARITY_TEXT)
        hops = e.get("I4_hops") or []
        keys = e.get("I5_config_keys") or []
        if not isinstance(hops, list) or not isinstance(keys, list) or not (hops or keys):
            raise _accept_refusal(where, "needs a non-empty list 'I4_hops' or 'I5_config_keys'")
        for j, h in enumerate(hops):
            hw = "%s I4_hops %d" % (where, j)
            if not isinstance(h, Mapping) or sorted(set(h) - set(ACCEPT_HOP_KEYS)):
                raise _accept_refusal(hw, "is not a mapping of %s" % list(ACCEPT_HOP_KEYS))
            for k in ("from", "to"):
                if not isinstance(h.get(k), str) or not _HEX64.match(h[k]):
                    raise _accept_refusal(hw, "'%s' must be a full 64-hex engine_code_sha256" % k)
            if not isinstance(h.get("must_match_differences"), list):
                raise _accept_refusal(hw, "needs 'must_match_differences' (a list; [] when the proof shows none)")
            ev = h.get("evidence")
            if not isinstance(ev, list) or not ev:
                raise _accept_refusal(hw, "needs a non-empty 'evidence' list of {path, sha256}")
            for x in ev:
                if (not isinstance(x, Mapping) or sorted(x) != ["path", "sha256"] or not isinstance(x["path"], str)
                        or not isinstance(x["sha256"], str) or not _HEX64.match(x["sha256"])):
                    raise _accept_refusal(hw, "evidence items must be {path, sha256} with a 64-hex sha256")
        for j, c in enumerate(keys):
            cw = "%s I5_config_keys %d" % (where, j)
            if not isinstance(c, Mapping) or sorted(set(c) - set(ACCEPT_CFG_KEYS)):
                raise _accept_refusal(cw, "is not a mapping of %s" % list(ACCEPT_CFG_KEYS))
            if not isinstance(c.get("key"), str) or "run" not in c or "live" not in c:
                raise _accept_refusal(cw, "needs 'key', 'run' and 'live'")
            if c["run"] == c["live"]:
                raise _accept_refusal(cw, "'run' equals 'live': nothing to accept")
        if e["run_id"] in seen:
            raise _accept_refusal(where, "a second entry for run id %r" % e["run_id"])
        seen.add(e["run_id"])
        out.append(dict(e))
    return out


def acceptance_for(roots: LY.Roots, run: Path, manifest: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """The accepted-difference entry of this run (matched by the run folder's name, the run id), or None. The
    entry's run fingerprint must be the run's (refuses ACCEPT otherwise)."""
    hit = [e for e in accepted_differences(roots) if e["run_id"] == Path(run).name]
    if not hit:
        return None
    e = hit[0]
    if e["run_fingerprint"] != manifest.get("fingerprint"):
        raise ExportRefusal("ACCEPT", "the accepted difference of run id %s (ruling %s) names run fingerprint %s; "
                            "this run's is %s" % (e["run_id"], e["ruling"], e["run_fingerprint"][:16],
                                                  str(manifest.get("fingerprint"))[:16]),
                            fix="the ruling covers one run only: ask the owner")
    return e


def acceptance_record(acc: Optional[Mapping[str, Any]], engine: Mapping[str, Any],
                      ident: Optional[Mapping[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """What the export manifest (and the board) record of an applied acceptance."""
    if acc is None:
        return None
    return {"ruling": acc["ruling"], "ruling_source": acc["ruling_source"], "run_id": acc["run_id"],
            "run_fingerprint": acc["run_fingerprint"], "live_engine_file_sha": acc["live_engine_file_sha"],
            "requires_parity": REQUIRED_PARITY_TEXT,
            "I4_hops_accepted_on_the_chain": [h for h in engine.get("hops") or [] if h.get("accepted")],
            "I5_config_keys_accepted": list((ident or {}).get("I5_accepted") or []),
            "note": acc.get("note")}


def check_engine(manifest: Mapping[str, Any], roots: LY.Roots, registry_dir: Any, package_name: str,
                 accepted: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """I4: LIVE engine_code_hashes() == the run's engine_modules, or a chain of no-op proof hops from the
    run's engine (its file sha found through a freeze lock) to the LIVE file sha, every hop valid for this
    package. With an accepted difference (accepted_differences above), its listed hops join the chain when
    every evidence file still has its recorded sha256 and LIVE is the entry's LIVE; proven hops are tried
    first. Returns the record for the manifest."""
    from treeroute.runs.fingerprint import engine_code_hash, engine_code_hashes, engine_code_sha256

    live_file, live_stripped = engine_code_sha256(), engine_code_hash()
    rec: Dict[str, Any] = {"live_file_sha": live_file, "live_stripped": live_stripped,
                           "run_stripped": manifest.get("engine_code_hash"), "run_file_sha": None, "hops": []}
    if dict(manifest.get("engine_modules") or {}) == engine_code_hashes():
        rec["rule"] = "the run's engine modules equal LIVE's (no hop needed)"
        return rec
    path = LY.lineage_file(roots)
    acc_hops = list((accepted or {}).get("I4_hops") or [])
    if not path.is_file() and not acc_hops:
        raise ExportRefusal("I4", "the run's engine (stripped %s) is not LIVE (stripped %s) and no lineage file "
                            "exists at %s" % (str(rec["run_stripped"])[:8], live_stripped[:8], path),
                            fix="write it with 'export --write-lineage' from the no-op proof files")
    lineage = _read_json(path) if path.is_file() else {"format": LINEAGE_FORMAT, "hops": []}
    if lineage.get("format") != LINEAGE_FORMAT:
        raise ExportRefusal("I4", "%s is not a %s file" % (path, LINEAGE_FORMAT))
    files = {e["file_sha"] for e in freeze_lock_engines(registry_dir) if e["stripped"] == rec["run_stripped"]}
    if len(files) != 1:
        raise ExportRefusal("I4", "the run's stripped engine hash %s matches %d freeze-lock file shas (%s); "
                            "one is needed" % (str(rec["run_stripped"])[:8], len(files), sorted(files)))
    start = files.pop()
    rec["run_file_sha"] = start
    good: Dict[str, List[Dict[str, Any]]] = {}
    rejected = []
    for hop in lineage.get("hops") or []:
        why = None
        proof = Path(hop.get("proof", ""))
        if not proof.is_file():
            why = "proof file missing"
        elif LY.sha256_file(proof) != hop.get("proof_sha256"):
            why = "proof file changed since the lineage was written"
        else:
            now = parse_proof(proof)
            if (now["from"], now["to"]) != (hop.get("from"), hop.get("to")):
                why = "proof file names another hop"
            elif not now["result_pass"]:
                why = "proof file has no PASS line"
            elif package_name not in now["packages_must_match"]:
                why = "proof file has no COMPARE section for package %r" % package_name
            elif now["packages_must_match"][package_name] != 0:
                why = "proof file shows %d must-match difference(s) for package %r" % (
                    now["packages_must_match"][package_name], package_name)
        if why is None:
            good.setdefault(hop["from"], []).append(hop)
        else:
            rejected.append({"from": hop.get("from"), "to": hop.get("to"), "proof": hop.get("proof"), "why": why})

    def chain(hops_by_from: Mapping[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """Breadth-first from the run's engine over the given hops: {reachable engine: the hops to it}."""
        seen = {start: []}
        queue = [start]
        while queue:
            cur = queue.pop(0)
            for hop in hops_by_from.get(cur, []):
                if hop["to"] not in seen:
                    seen[hop["to"]] = seen[cur] + [hop]
                    queue.append(hop["to"])
        return seen

    seen = chain(good)                           # proven hops first; accepted hops only when these do not reach LIVE
    if live_file not in seen and acc_hops:
        if accepted["live_engine_file_sha"] != live_file:
            raise ExportRefusal("I4", "the accepted difference of run id %s (ruling %s) was ruled for LIVE engine "
                                "%s; LIVE is now %s, so it does not apply" % (accepted["run_id"], accepted["ruling"],
                                                                              accepted["live_engine_file_sha"][:8],
                                                                              live_file[:8]),
                                fix="ask the owner (a new LIVE engine needs its own no-op proof or ruling)")
        both = {k: list(v) for k, v in good.items()}
        for hop in acc_hops:
            why = None
            for ev in hop["evidence"]:
                p = Path(ev["path"])
                if not p.is_file():
                    why = "accepted hop: evidence file %s is missing" % ev["path"]
                elif LY.sha256_file(p) != ev["sha256"]:
                    why = "accepted hop: evidence file %s changed since the ruling was recorded" % ev["path"]
                if why:
                    break
            if why is None:
                both.setdefault(hop["from"], []).append(dict(hop, accepted=accepted["ruling"]))
            else:
                rejected.append({"from": hop["from"], "to": hop["to"], "proof": None, "why": why})
        seen = chain(both)
    if live_file not in seen:
        raise ExportRefusal("I4", "no chain of valid no-op proof hops leads from the run's engine %s to LIVE %s "
                            "for package %r (reachable: %s; rejected hops: %s)"
                            % (start[:8], live_file[:8], package_name, sorted(s[:8] for s in seen), rejected),
                            fix="owner: add the missing hop's proof file and rewrite the lineage")
    out = []
    for h in seen[live_file]:
        if h.get("accepted"):
            out.append({"from": h["from"], "to": h["to"], "accepted": h["accepted"], "evidence": list(h["evidence"]),
                        "must_match_differences": list(h["must_match_differences"]), "note": h.get("note"),
                        "package": package_name})
        else:
            out.append({"from": h["from"], "to": h["to"], "proof": h["proof"], "proof_sha256": h["proof_sha256"],
                        "package": package_name, "must_match": 0})
    rec["hops"] = out
    rec["rule"] = "a chain of recorded no-op proofs (lineage %s)" % str(path).replace("\\", "/")
    n_acc = sum(1 for h in out if h.get("accepted"))
    if n_acc:
        rec["rule"] += "; %d hop(s) without a parsable proof ACCEPTED by owner ruling %s (run id %s; evidence files " \
                       "pinned by sha256)" % (n_acc, accepted["ruling"], accepted["run_id"])
    rec["lineage_sha256"] = LY.sha256_file(path) if path.is_file() else None
    return rec


# ---------------------------------------------------------------------------------------------------
# the run folder
def run_leads(run: Path) -> Tuple[int, ...]:
    """The run's leads, lead 0 first (plan.json 'leads' are the forecast leads)."""
    plan = _read_json(run / "plan.json")
    return (0,) + tuple(sorted(int(x) for x in plan.get("leads") or []))


def check_run_files(run: Path) -> Tuple[int, ...]:
    """I1: every record the export reads exists."""
    missing = [n for n in RUN_FILES if not (run / n).is_file()]
    if not missing:
        leads = run_leads(run)
        for L in leads[1:]:
            missing += ["%s/lead_%d/%s" % (LADDER_DIR, L, n) for n in LEAD_FILES
                        if not (run / LADDER_DIR / ("lead_%d" % L) / n).is_file()]
    if missing:
        raise ExportRefusal("I1", "the run folder %s lacks %s" % (run, missing),
                            fix="export only a finished run (DONE.json written)")
    return run_leads(run)


def default_package(manifest: Mapping[str, Any], engine_root: Path) -> Path:
    """The package folder named in the run's argv: the last argv item that is a folder holding dataset.yaml
    (relative items resolved under the engine root)."""
    found = None
    for item in manifest.get("argv") or []:
        p = Path(str(item))
        cand = p if p.is_absolute() else engine_root / p
        if (cand / "dataset.yaml").is_file():
            found = cand
    if found is None:
        raise ExportRefusal("I2", "no argv item of the run's manifest is a package folder (dataset.yaml)",
                            fix="pass --package")
    return found


def parse_leads(text: Any, leads: Sequence[int]) -> Tuple[int, ...]:
    if text is None or str(text) == "all":
        return tuple(leads)
    out = []
    for part in str(text).split(","):
        L = int(part)
        if L not in leads:
            raise ExportRefusal("ARGS", "lead %d is not a lead of the run (%s)" % (L, list(leads)))
        out.append(L)
    return tuple(sorted(set(out)))


def parse_roles(text: Any) -> Tuple[str, ...]:
    if text is None or text == "all" or text == ():
        return tuple(LY.ROLES)
    items = text if isinstance(text, (list, tuple)) else str(text).split(",")
    out = [str(r).strip() for r in items if str(r).strip()]
    bad = [r for r in out if r not in LY.ROLES]
    if bad:
        raise ExportRefusal("ARGS", "unknown role(s) %s (roles %s)" % (bad, list(LY.ROLES)))
    return tuple(r for r in LY.ROLES if r in out)


def estimate_lead_bytes(run: Path, manifest: Mapping[str, Any], lead: int) -> int:
    """I8: an upper value of one lead's export from the run's saved row counts (fitctx_log, inner, guard
    and test predictions) and the column counts."""
    import pandas as pd
    import pyarrow.parquet as pq

    plan = _read_json(run / "plan.json")
    n_x = len(manifest.get("feature_list") or [])
    n_c = len(plan.get("context") or [])
    n_h = len(plan.get("history_columns") or [])
    n_l = len(plan.get("links") or [])
    log = pd.read_parquet(run / "fitctx_log.parquet", columns=["object_kind", "purpose", "lead", "n_rows"])
    log = log[log["object_kind"] == "donor_rows"]

    def n_of(purpose):
        sel = log[(log["purpose"] == purpose) & (log["lead"].astype(float) == float(lead))]
        return int(sel["n_rows"].max()) if len(sel) else 0
    side = n_of("bank_inner") if lead == 0 else n_of("bank_guard")
    if lead == 0:
        side += pq.ParquetFile(run / "inner_preds.parquet").metadata.num_rows
        test = pq.ParquetFile(run / "test_preds.parquet").metadata.num_rows
    else:
        d = run / LADDER_DIR / ("lead_%d" % lead)
        side += pq.ParquetFile(d / "guard_preds.parquet").metadata.num_rows
        test = pq.ParquetFile(d / "test_preds.parquet").metadata.num_rows
    train = n_of("bank") + side
    row = 64 + 8 * (1 + n_l) + 4 * (n_x + n_c)
    return int(train * row + side * (64 + 8 * n_l + 4 * n_h) + test * row)


def estimate_engine_temp_bytes(run: Path, leads: Sequence[int]) -> Tuple[int, str]:
    """I8: the engine's temp pools this export builds, from the run's own per_group_schedule.json temp_disk_plan
    (the engine's disk_plan at the run): the nowcast pool + its guard-cut history block when lead 0 is exported,
    plus one lead pool + two history blocks when a later lead is. 0 when the run kept no plan (a table run)."""
    p = Path(run) / "per_group_schedule.json"
    plan = (_read_json(p).get("temp_disk_plan") or {}) if p.is_file() else {}
    if not plan:
        return 0, "the run kept no temp_disk_plan (no engine pool)"
    need = 0
    if 0 in [int(x) for x in leads]:
        need += int(plan.get("pool", 0)) + int(plan.get("history_block", 0))
    if any(int(x) != 0 for x in leads):
        need += int(plan.get("lead_pool", 0)) + int(plan.get("lead_guard_history_block", 0)) \
            + int(plan.get("history_block", 0))
    return need, "per_group_schedule.json temp_disk_plan"


def free_disk(path: Path) -> int:
    p = Path(path)
    while not p.exists():
        p = p.parent
    return int(shutil.disk_usage(str(p)).free)


# ---------------------------------------------------------------------------------------------------
# the rows of one lead
class RoleRows(object):
    """One role's rows: grid (or row) positions ascending, unit ids, label steps (or target days), labels
    (None for test rows)."""

    def __init__(self, keys: Any, units: Any, times: Any, y: Any = None) -> None:
        import numpy as np

        self.keys = np.asarray(keys, dtype=np.int64)
        self.units = np.asarray(units, dtype=object)
        self.times = np.asarray(times, dtype=np.int64)
        self.y = None if y is None else np.asarray(y, dtype=np.float64)
        if not (self.keys.shape == self.units.shape == self.times.shape) or (
                self.y is not None and self.y.shape != self.keys.shape):
            raise ExportRefusal("ROWS", "internal: role rows of unequal lengths")

    @property
    def n(self) -> int:
        return int(self.keys.size)


class LeadBuild(object):
    """Everything one lead's files are written from (built by the engine's own objects)."""

    def __init__(self, lead: int) -> None:
        self.lead = int(lead)
        self.roles: Dict[str, RoleRows] = {}
        self.donors: Dict[str, Any] = {}           # refit / tune / guardfit: the engine's DonorRows
        self.fit_features = None                   # the FIT-cut feature source (x__ and c__)
        self.guard_history = None                  # the guard-cut history pool (h__), or None
        self.history_columns: Tuple[str, ...] = ()
        self.normal_fit: Callable[[Any, Any], Dict[str, Any]] = None
        self.normal_guard: Callable[[Any, Any], Dict[str, Any]] = None
        self.c = None
        self.records: Dict[str, Any] = {}
        self.test_order = None                     # saved test_preds row of each test row


def _state_attrs(state: Any) -> None:
    """The attributes RunState.build_pool sets before it opens the pool (pipeline/passes.py:372-389), for a
    grid export that does not export lead 0 (so no nowcast pool is built). No number is computed here."""
    import numpy as np
    from treeroute.pipeline import router as PR

    p = state.p
    state.derived = p.derived
    state.kind = PR.router_kind(state.derived)
    state.vg = p._vault(p.folder)
    state.labels = state.vg.labels
    state.lists = state.derived["R18:units"].value
    state.groups = tuple(sorted(state.lists.bank))
    order = {u: i for i, u in enumerate(state.vg.grid.unit_ids)}
    state.bank_units = sorted((u for g in state.groups for u in state.lists.bank[g]), key=order.get)
    state.scored_units = sorted((u for g in state.groups for u in state.lists.scored[g]), key=order.get)
    state.unit_group = {u: g for g in state.groups for u in state.lists.bank[g]}
    state.season = state.derived["R2"].value
    state.cuts = state.derived["R11"].value[0]
    state.windows = state.derived["R7"].value
    state.links = tuple(state.derived["R22"].value)
    state.legal = p.spec.legal_range
    state.ub = state.legal[1] if np.isfinite(state.legal[1]) else None


def _grid_history(state: Any, ctx: Any, L: int) -> Tuple[Any, Dict[str, Any], Optional[float]]:
    """R17's block at lead L with its fallbacks at ctx's cut: the body of Ladder._history
    (pipeline/ladder.py:471-481) through stages.history_inputs and io.apply.history_block."""
    import numpy as np
    from treeroute.fit.context import season_keys_of
    from treeroute.pipeline import stages as ST

    s = state
    n = int(s.vg.grid.n_steps)
    spec17 = s.derived["R17"].value
    rows = np.arange(len(s.vg.grid.unit_ids) * n, dtype=np.int64)
    if not spec17.columns:
        return np.zeros((rows.size, 0), dtype=np.float32), {}, None
    fill, donor_mean = ST.history_inputs(ctx, s.vg, s.p.split_sets, s.bank_units)
    hist, filled = ST.history_block(s.vg.grid, spec17, s.vg.steps, rows // n, L, s.labels, fill,
                                    season_keys_of(s.vg.steps, s.season), donor_mean)
    return hist, dict(filled), donor_mean


def _surface_rows(state: Any, what: str, ctx: Any, lead: int, first: int, fit_cut: int, absent: Any,
                  purpose: str) -> RoleRows:
    """A grid score surface (the nowcast decision surface, passes.py:735-755, or a lead's guard surface,
    ladder.py:769-798): the scored units' rows with a valid label in [first, fit_cut] whose own window ended
    by the fit cut's last day; at a lead the rows must be issued at or after the guard cut and an absent
    issue row refuses; owner ruling S1 (save=False) leaves out rows with missing router context; the labels
    from the vault's decision_surface."""
    import numpy as np
    from treeroute.io.steps import step_bounds

    s = state
    n = int(s.vg.grid.n_steps)
    row_of = {u: i for i, u in enumerate(s.vg.grid.unit_ids)}
    vu, vt, vv = s.labels.validity(int(first), int(fit_cut))
    pos = np.fromiter((row_of[u] for u in vu.tolist()), dtype=np.int64, count=vu.size) * n + (vt - s.vg.first_step)
    scored = np.isin(vu, np.asarray(s.scored_units, dtype=object))
    last_day = int(step_bounds(np.array([int(fit_cut)], dtype=np.int64), s.p.cadence)[1][0])
    ended = s.vg.window_end[pos] <= last_day
    pick = scored & vv & ended
    if not pick.any():
        raise ExportRefusal("ROWS", "%s: no scored row with a valid label in steps %d..%d" % (what, first, fit_cut))
    if lead > 0:
        ctx.check_inner_score_rows(vt[pick] - lead)
        ab = np.asarray(absent, dtype=bool)[pos[pick]]
        if ab.any():
            raise ExportRefusal("ROWS", "%s: %d row(s) have no issue row at t - %d (the engine refuses them too)"
                                % (what, int(ab.sum()), lead))
    keep, s1 = s.leave_out_score_context(what, ctx, lead, pos[pick], vu[pick], vt[pick], save=False)
    if s1 is not None:
        idx = np.flatnonzero(pick)
        pick = pick.copy()
        pick[idx[~keep]] = False
    surface = s.labels.decision_surface(vu[pick], vt[pick], int(fit_cut), purpose=purpose)
    rows = RoleRows(pos[pick], np.asarray(surface.unit_ids, dtype=object), np.asarray(surface.times, dtype=np.int64),
                    np.asarray(surface.y, dtype=np.float64))
    rows.s1 = None if s1 is None else int(s1["rows_left_out"])
    return rows


def _donor_rows(donor: Any) -> RoleRows:
    return RoleRows(donor.grid_rows, donor.unit_ids, donor.times, donor.y)


def _grid_normals(state: Any, ctx: Any, donor: Any, c: Optional[float], score: RoleRows, purpose: str
                  ) -> Tuple[Callable[[Any, Any], Dict[str, Any]], Dict[str, Any]]:
    """R15 at ctx's cut in every R22 link, for every bank unit (SPEC_RIVALS.md 2.4): the donor-row link means of
    the cut's donor rows (stages.donor_link_means), each unit's history read once (FitContext.unit_history) and
    stages.unit_normals per link; for the per-unit kind with context columns the scored units' histories are
    the router's (stages.pass_rows, then stages.context_kept_histories: owner ruling G1). Returns
    f(units, times) -> {link: values} (stages._normals_on at R2's season keys) and a record."""
    from treeroute.derive.shapes import Link
    from treeroute.fit.context import season_keys_of
    from treeroute.pipeline import router as PR
    from treeroute.pipeline import stages as ST

    s = state
    links = tuple(s.links)
    means = ST.donor_link_means(donor, links, c, s.ub)
    hist = {u: ctx.unit_history(u, "rival_normal") for u in s.bank_units}
    rec: Dict[str, Any] = {"cut": int(ctx.cut), "cut_kind": ctx.cut_kind.value, "lead": int(ctx.lead),
                           "donor_link_means": {L.value: means[L] for L in links}, "units": len(hist),
                           "g1": None}
    if s.kind == PR.KIND_PER_UNIT and tuple(ctx.features.context_columns):
        rows = ST.pass_rows(ctx, s.scored_units, score.units, score.times, score.keys, purpose)
        trimmed, _ = ST.context_kept_histories(ctx, s.scored_units, rows)
        g1 = rows.context_missing or {}
        rec["g1"] = {"fit_rows": int(g1.get("fit_rows", 0)), "rows_left_out": int(g1.get("rows_left_out", 0)),
                     "units_trimmed": 0 if trimmed is None else len(g1.get("by_unit") or {})}
        if trimmed is not None:
            hist.update(trimmed)
    tables = {L: ST.unit_normals(ctx, s.bank_units, L, c, s.ub, means[L], s.season, histories=hist) for L in links}
    cut = int(ctx.cut)

    def values(units: Any, times: Any) -> Dict[str, Any]:
        import numpy as np

        u = np.asarray(units, dtype=object)
        keys = season_keys_of(np.asarray(times, dtype=np.int64), s.season)
        # the router reads every link's table with the pass's c (pipeline/stages.py per_unit_rows)
        return {L.value: ST._normals_on(tables[L], u, keys, L, cut, c) for L in links}
    return values, rec


def _median_normals(state: Any, donor: Any, c: Optional[float]) -> Tuple[Callable[[Any, Any], Dict[str, Any]],
                                                                         Dict[str, Any]]:
    """The neighbour kind's normal (SPEC_RIVALS.md 2.4, reading R-CN): one donor-row median of the cut's donor
    rows (report.metrics.baseline_donor_median), in each R22 link (layer.links.link_forward)."""
    import numpy as np
    from treeroute.layer.links import link_forward
    from treeroute.pipeline import router as PR
    from treeroute.report import metrics as M

    med = float(M.baseline_donor_median(donor))
    z = {}
    for L in state.links:
        cc, uu = PR.link_arg(L, c, state.ub)
        z[L.value] = float(link_forward(np.array([med], dtype=np.float64), L, cc, uu)[0])
    rec = {"cut": int(donor.cut), "cut_kind": donor.cut_kind.value, "lead": int(donor.lead), "donor_median": med,
           "link_values": dict(z), "rule": "one donor-row median per cut (reading R-CN)"}

    def values(units: Any, times: Any) -> Dict[str, Any]:
        n = int(np.asarray(units).size)
        return {k: np.full(n, v, dtype=np.float64) for k, v in z.items()}
    return values, rec


def _c_of(state: Any, refit: Any) -> Optional[float]:
    """R23: c from the lead's FIT-cut donor rows, checked against derived.json (layer.links)."""
    from treeroute.derive.shapes import Link
    from treeroute.layer.links import c_for_cut_against_plan

    return c_for_cut_against_plan(refit, state.derived) if Link.LOG_C in state.links else None


def build_grid_lead(state: Any, L: int, stack: ExitStack, log: Callable[[str], None]) -> LeadBuild:
    """One grid lead's rows, features and normals through the engine's own objects (SPEC_RIVALS.md 2.3)."""
    import numpy as np
    from treeroute import engine_constants as K
    from treeroute.derive.shapes import CutKind
    from treeroute.fit.context import FitContext
    from treeroute.fit.pool import open_pool
    from treeroute.io.apply import features_at_issue_step
    from treeroute.pipeline import record as REC
    from treeroute.pipeline import stages as ST
    from treeroute.pipeline.passes import HistoryOverride

    s, p = state, state.p
    if not K.INNER_CUT_BANK_REFIT:
        raise ExportRefusal("I5", "A7.inner_cut_bank_refit is off (L6 a): the export is built for L6 b only")
    b = LeadBuild(L)
    if L == 0:
        log("lead 0: the nowcast pool (RunState.build_pool) and the inner history block at the guard cut")
        s.build_pool(need_inner=True)
    spec17 = s.derived["R17"].value
    b.history_columns = tuple(spec17.columns)
    cuts = s.derived["R11"].value[L]
    fit_cut, guard_cut = int(cuts.fit_cut), int(cuts.guard_cut)
    t_keys = ST.unit_positions(s.vg, s.scored_units, s.vg.test_first, None)
    if L == 0:
        ctx_fit = s.ctx_fit
        ctx_g = FitContext(s.derived, p.split_sets, s.vg.grid, s.labels, s.inner_features, s.lists, 0, CutKind.GUARD)
        b.fit_features = s.pool
        b.guard_history = getattr(s, "pool_inner_history", None) if b.history_columns else None
        b.donors[LY.ROLE_REFIT] = ctx_fit.donor_rows_lazy(PURPOSE[LY.ROLE_REFIT])
        b.donors[LY.ROLE_TUNE] = ctx_g.donor_rows_lazy(PURPOSE[LY.ROLE_TUNE])
        b.roles[LY.ROLE_REFIT] = _donor_rows(b.donors[LY.ROLE_REFIT])
        b.roles[LY.ROLE_TUNE] = _donor_rows(b.donors[LY.ROLE_TUNE])
        b.roles[LY.ROLE_INNER] = _surface_rows(s, "decision surface", ctx_g, 0, guard_cut + 1, fit_cut, None,
                                               "rival_inner")
        keep, s1 = s.leave_out_score_context(REC.S1_TEST_PASS, ctx_fit, 0, t_keys, s.vg.unit_ids[t_keys],
                                             s.vg.steps[t_keys], save=False)
        b.records["test_s1_left_out"] = 0 if s1 is None else int(s1["rows_left_out"])
        b.records["test_h4_left_out"] = 0
        t_keys = t_keys[keep]
        side_role, side_rows = LY.ROLE_TUNE, b.roles[LY.ROLE_INNER]
    else:
        log("lead %d: the lead pool (features moved to the issue step, history block at the lead's fit cut)" % L)
        n = int(s.vg.grid.n_steps)
        rows = np.arange(len(s.vg.grid.unit_ids) * n, dtype=np.int64)
        tree_cols = tuple(p.spec.tree_features) + tuple(spec17.columns)
        pool = stack.enter_context(open_pool(p.temp_dir, "pool_lead_%d" % L, rows, tree_cols, tuple(p.spec.context)))
        ctx_fit = FitContext(s.derived, p.split_sets, s.vg.grid, s.labels, pool, s.lists, L, CutKind.FIT)
        hist, _, _ = _grid_history(s, ctx_fit, L)
        absent = s.fill_pool_by_group(pool, hist, L, move=features_at_issue_step)
        del hist
        gc.collect()
        features = pool
        if spec17.columns:
            log("lead %d: the guard history block at the lead's guard cut %d" % (L, guard_cut))
            hist_g, _, _ = _grid_history(s, ctx_fit.for_lead(L, CutKind.GUARD), L)
            hpool = stack.enter_context(open_pool(p.temp_dir, "pool_guard_history_lead_%d" % L, rows,
                                                  tuple(spec17.columns), ()))
            for a0 in range(0, rows.size, 50000):
                hpool.write(rows[a0:a0 + 50000], hist_g[a0:a0 + 50000], None)
            hpool.require_complete()
            del hist_g
            gc.collect()
            features = HistoryOverride(pool, hpool)
            b.guard_history = hpool
        ctx_g = FitContext(s.derived, p.split_sets, s.vg.grid, s.labels, features, s.lists, L, CutKind.GUARD)
        b.fit_features = pool
        b.donors[LY.ROLE_REFIT] = ctx_fit.donor_rows_lazy(PURPOSE[LY.ROLE_REFIT])
        b.donors[LY.ROLE_GUARDFIT] = ctx_g.donor_rows_lazy(PURPOSE[LY.ROLE_GUARDFIT])
        b.roles[LY.ROLE_REFIT] = _donor_rows(b.donors[LY.ROLE_REFIT])
        b.roles[LY.ROLE_GUARDFIT] = _donor_rows(b.donors[LY.ROLE_GUARDFIT])
        b.roles[LY.ROLE_GUARD] = _surface_rows(s, "lead %d guard" % L, ctx_g, L, int(s.cuts.guard_cut) + 1, fit_cut,
                                               absent, "rival_lead_%d_guard" % L)
        missing = np.asarray(absent, dtype=bool)[t_keys]
        if missing.all():
            raise ExportRefusal("ROWS", "lead %d: every test row has no issue row (the engine refuses too)" % L)
        b.records["test_h4_left_out"] = int(missing.sum())
        t_keys = t_keys[~missing]
        keep, s1 = s.leave_out_score_context("lead %d test pass" % L, ctx_fit, L, t_keys, s.vg.unit_ids[t_keys],
                                             s.vg.steps[t_keys], save=False)
        b.records["test_s1_left_out"] = 0 if s1 is None else int(s1["rows_left_out"])
        t_keys = t_keys[keep]
        side_role, side_rows = LY.ROLE_GUARDFIT, b.roles[LY.ROLE_GUARD]
    b.roles[LY.ROLE_TEST] = RoleRows(t_keys, s.vg.unit_ids[t_keys], s.vg.steps[t_keys], None)
    refit = b.donors[LY.ROLE_REFIT]
    b.c = _c_of(s, refit)
    log("lead %d: normals at the fit cut %d and the guard cut %d (%d bank units, links %s)"
        % (L, fit_cut, guard_cut, len(s.bank_units), [x.value for x in s.links]))
    b.normal_fit, b.records["normal_fit"] = _grid_normals(s, ctx_fit, refit, b.c, b.roles[LY.ROLE_TEST],
                                                          "rival_router_fit")
    b.normal_guard, b.records["normal_guard"] = _grid_normals(s, ctx_g, b.donors[side_role], b.c, side_rows,
                                                              "rival_router_guard")
    b.cuts = {"fit_cut": fit_cut, "guard_cut": guard_cut,
              "inner_fit_end_step": s.derived["R11"].inputs.get("inner_fit_end_step")}
    b.records["s1_surface_left_out"] = int(side_rows.s1 or 0)
    return b


def build_table_lead(state: Any, L: int, stack: ExitStack, log: Callable[[str], None]) -> LeadBuild:
    """One table lead's rows, features and normals (SPEC_RIVALS.md 2.5): the table pipeline's pools and
    FitContext hand-outs, the decision surface as table_passes.py:317-330, a lead's guard rows as
    table_ladder.py:296-317, the test rows as table_passes.py:406-411 and table_ladder.py:481-497."""
    import numpy as np
    from treeroute import engine_constants as K
    from treeroute.derive.shapes import CutKind
    from treeroute.fit.context import FitContext
    from treeroute.pipeline import record as REC

    s, p = state, state.p
    if not K.INNER_CUT_BANK_REFIT:
        raise ExportRefusal("I5", "A7.inner_cut_bank_refit is off (L6 a): the export is built for L6 b only")
    b = LeadBuild(L)
    if getattr(s, "pool", None) is None:
        s.build_pool(need_inner=True)
    cuts = s.derived["R11"].value[L]
    fit_cut, guard_cut = int(cuts.fit_cut), int(cuts.guard_cut)
    data = s.data
    is_test = np.asarray(data.is_test, dtype=bool)
    t_keys, t_units, t_days = s.test_rows()
    if L == 0:
        ctx_fit = s.ctx_fit
        vault = s.labels
        ctx_g = FitContext(s.derived, p.split_sets, s.vg.grid, s.labels, s.pool, s.lists, 0, CutKind.GUARD)
        b.fit_features = s.pool
        b.donors[LY.ROLE_REFIT] = ctx_fit.donor_rows(PURPOSE[LY.ROLE_REFIT])
        b.donors[LY.ROLE_TUNE] = ctx_g.donor_rows(PURPOSE[LY.ROLE_TUNE])
        first, side_role, surf_role = guard_cut + 1, LY.ROLE_TUNE, LY.ROLE_INNER
        present = np.ones(is_test.size, dtype=bool)
        what, purpose = "decision surface", "rival_inner"
    else:
        lt = data.leads[L]
        vault = s.labels.for_lead(lt.present, L)
        pool = stack.enter_context(s.open_lead_pool("pool_lead_%d" % L, L))
        ctx_fit = FitContext(s.derived, p.split_sets, s.vg.grid, vault, pool, s.lists, L, CutKind.FIT)
        ctx_g = FitContext(s.derived, p.split_sets, s.vg.grid, vault, pool, s.lists, L, CutKind.GUARD)
        b.fit_features = pool
        b.donors[LY.ROLE_REFIT] = ctx_fit.donor_rows(PURPOSE[LY.ROLE_REFIT])
        b.donors[LY.ROLE_GUARDFIT] = ctx_g.donor_rows(PURPOSE[LY.ROLE_GUARDFIT])
        first, side_role, surf_role = int(s.cuts.guard_cut) + 1, LY.ROLE_GUARDFIT, LY.ROLE_GUARD
        present = np.asarray(lt.present, dtype=bool)
        what, purpose = "lead %d guard" % L, "rival_lead_%d_guard" % L
    b.roles[LY.ROLE_REFIT] = _donor_rows(b.donors[LY.ROLE_REFIT])
    b.roles[side_role] = _donor_rows(b.donors[side_role])
    # the surface (decision surface at lead 0, the guard surface at a lead)
    vu, vt, vv = s.labels.validity(int(first), fit_cut)
    pos = np.asarray([s.row_pos[str(u)] for u in vu.tolist()], dtype=np.int64)
    pick = vv & ~is_test[pos]
    if L > 0:
        ab = pick & ~present[pos]
        if ab.any():
            raise ExportRefusal("ROWS", "%s: %d row(s) are absent from the lead's file (the engine refuses too)"
                                % (what, int(ab.sum())))
        if not pick.any():
            raise ExportRefusal("ROWS", "%s: no train row with a valid label" % what)
        ctx_g.check_inner_score_rows(np.asarray(data.leads[L].issue_day, dtype=np.int64)[pos[pick]])
    keep, s1 = s.leave_out_score_context(what, ctx_g, L, pos[pick], vu[pick], vt[pick], save=False)
    if s1 is not None:
        idx = np.flatnonzero(pick)
        pick = pick.copy()
        pick[idx[~keep]] = False
    surface = vault.decision_surface(vu[pick], vt[pick], fit_cut, purpose=purpose)
    b.roles[surf_role] = RoleRows(pos[pick], np.asarray(surface.unit_ids, dtype=object),
                                  np.asarray(surface.times, dtype=np.int64), np.asarray(surface.y, dtype=np.float64))
    b.records["s1_surface_left_out"] = 0 if s1 is None else int(s1["rows_left_out"])
    # the test rows (absent rows at a lead left out: H4), then S1
    pres = present[t_keys]
    if not pres.any():
        raise ExportRefusal("ROWS", "lead %d: every test row is absent from the lead's file" % L)
    b.records["test_h4_left_out"] = int((~pres).sum())
    t_keys, t_units, t_days = t_keys[pres], t_units[pres], t_days[pres]
    keep, s1 = s.leave_out_score_context(REC.S1_TEST_PASS if L == 0 else "lead %d test pass" % L, ctx_fit, L,
                                         t_keys, t_units, t_days, save=False)
    b.records["test_s1_left_out"] = 0 if s1 is None else int(s1["rows_left_out"])
    b.roles[LY.ROLE_TEST] = RoleRows(t_keys[keep], t_units[keep], t_days[keep], None)
    b.c = _c_of(s, b.donors[LY.ROLE_REFIT])
    b.normal_fit, b.records["normal_fit"] = _median_normals(s, b.donors[LY.ROLE_REFIT], b.c)
    b.normal_guard, b.records["normal_guard"] = _median_normals(s, b.donors[side_role], b.c)
    b.cuts = {"fit_cut": fit_cut, "guard_cut": guard_cut,
              "inner_fit_end_step": s.derived["R11"].inputs.get("inner_fit_end_step")}
    log("lead %d: %s" % (L, ", ".join("%s %d rows" % (r, b.roles[r].n) for r in b.roles)))
    return b


# ---------------------------------------------------------------------------------------------------
# the files
def _arrow_table(columns: Sequence[Tuple[str, Any, Any]]) -> Any:
    import pyarrow as pa

    names = [c[0] for c in columns]
    if len(set(names)) != len(names):
        raise ExportRefusal("LAYOUT", "internal: a file repeats a column name")
    arrays = [pa.array(values, type=kind) for _, values, kind in columns]
    return pa.Table.from_arrays(arrays, names=names)


def table_bytes(columns: Sequence[Tuple[str, Any, Any]]) -> bytes:
    """One parquet file's bytes (no pandas metadata, snappy, statistics on): the same columns give the same
    bytes (P14)."""
    import pyarrow.parquet as pq

    buf = io.BytesIO()
    pq.write_table(_arrow_table(columns), buf, compression="snappy")
    return buf.getvalue()


class Writer(object):
    """The atomic, resumable writes of one lead folder (SPEC_RIVALS.md 1.2, 2.8)."""

    def __init__(self, lead_dir: Path, key: str, resume: bool, roots: LY.Roots, registry: Any, stamp: str,
                 log: Callable[..., None]) -> None:
        self.dir = lead_dir
        self.key = key
        self.resume = resume
        self.roots = roots
        self.registry = registry
        self.stamp = stamp
        self.log = log
        self.files: List[Dict[str, Any]] = []
        self.skipped = 0
        self.written = 0

    def _aside(self, path: Path) -> None:
        dest = LY.move_aside(path, self.roots.moved_root, self.registry, self.stamp,
                             relative_to=self.roots.export_root)
        self.log("moved aside %s -> %s" % (path, dest), only=self.dir / LY.EXPORT_LOG)

    def check_fresh(self) -> None:
        """Before the lock: without --resume the lead folder must hold nothing but its log and status (refuses
        early; moves nothing)."""
        if self.resume:
            return
        keep = {self.dir / LY.EXPORT_LOG, self.dir / LY.STATUS_FILE}
        present = [f for f in self.dir.rglob("*") if f.is_file()] if self.dir.exists() else []
        other = [f for f in present if f not in keep]
        if other:
            raise ExportRefusal("RESUME", "%s already holds %d file(s) (first %s); rerun with --resume, or "
                                "move the folder aside" % (self.dir, len(other), other[0]))

    def prepare(self) -> None:
        """Before the lead's first write: without --resume the lead folder must hold nothing but its log and
        status; with --resume every file not backed by a progress record of this export key (and its sha) is
        moved aside, and so is a previous export_manifest.json."""
        keep = {self.dir / LY.EXPORT_LOG, self.dir / LY.STATUS_FILE}
        present = [f for f in self.dir.rglob("*") if f.is_file()] if self.dir.exists() else []
        if not self.resume:
            other = [f for f in present if f not in keep]
            if other:
                raise ExportRefusal("RESUME", "%s already holds %d file(s) (first %s); rerun with --resume, or "
                                    "move the folder aside" % (self.dir, len(other), other[0]))
            return
        valid = set()
        for prog in (self.dir / LY.PROGRESS_DIR).rglob("*.json") if (self.dir / LY.PROGRESS_DIR).exists() else []:
            try:
                rec = _read_json(prog)
                target = self.dir / rec["file"]
                ok = rec.get("export_key") == self.key and target.is_file() and LY.sha256_file(target) == rec["sha256"]
            except Exception:                       # an unreadable record is moved aside, never trusted
                ok = False
            if ok:
                valid.add(prog)
                valid.add(target)
        for f in present:
            if f in keep or f in valid:
                continue
            self._aside(f)

    def put(self, rel: str, data: bytes, rows: int, part: str, group: str) -> Dict[str, Any]:
        path = self.dir / rel
        prog = self.dir / LY.PROGRESS_DIR / part / (Path(rel).stem + ".json")
        sha = LY.sha256_bytes(data)
        if self.resume and prog.is_file() and path.is_file():
            rec = _read_json(prog)
            if rec.get("export_key") == self.key and rec.get("sha256") == LY.sha256_file(path):
                if rec["sha256"] != sha:
                    raise ExportRefusal("P14", "%s was finished by this export key with sha %s, but the export "
                                        "now builds sha %s: not deterministic" % (path, rec["sha256"][:16], sha[:16]))
                self.skipped += 1
                entry = {"path": rel, "sha256": sha, "rows": int(rows), "part": part, "group": group}
                self.files.append(entry)
                return entry
        for old in (path, prog):
            if old.exists():
                self._aside(old)
        LY.atomic_write_bytes(path, data, self.registry)
        LY.write_json_atomic(prog, {"file": rel, "sha256": sha, "rows": int(rows), "export_key": self.key},
                             self.registry)
        self.written += 1
        entry = {"path": rel, "sha256": sha, "rows": int(rows), "part": part, "group": group}
        self.files.append(entry)
        return entry


def _float32_raw(X: Any, what: str) -> Any:
    import numpy as np

    X = np.ascontiguousarray(np.asarray(X, dtype=np.float32))
    if np.isinf(X).any():
        raise ExportRefusal("P13", "%s holds %d infinite value(s)" % (what, int(np.isinf(X).sum())))
    return X


def _key_columns(units: Any, groups: Any, times: Any, lead: int) -> List[Tuple[str, Any, Any]]:
    import numpy as np
    import pyarrow as pa

    t = np.asarray(times, dtype=np.int64)
    return [(LY.COL_UNIT, [str(u) for u in np.asarray(units, dtype=object).tolist()], pa.string()),
            (LY.COL_GROUP, [str(g) for g in np.asarray(groups, dtype=object).tolist()], pa.string()),
            (LY.COL_TIME, t, pa.int64()), (LY.COL_ISSUE, t - int(lead), pa.int64()),
            (LY.COL_LEAD, np.full(t.size, int(lead), dtype=np.int64), pa.int64())]


def _block_columns(prefix_fn: Callable[[str], str], names: Sequence[str], X: Any, kind: Any) -> List[Tuple[str, Any, Any]]:
    return [(prefix_fn(c), X[:, j], kind) for j, c in enumerate(names)]


class LeadFiles(object):
    """Builds the bytes of one lead's group files from a LeadBuild (the same code serves P14's rebuild)."""

    def __init__(self, state: Any, b: LeadBuild, tree_cols: Sequence[str], ctx_cols: Sequence[str],
                 roles: Sequence[str]) -> None:
        import numpy as np

        self.s = state
        self.b = b
        self.tree_cols = tuple(tree_cols)
        self.ctx_cols = tuple(ctx_cols)
        self.links = tuple(L.value for L in state.links)
        self.lead_roles = LY.roles_of_lead(b.lead)
        self.train_roles = tuple(r for r in self.lead_roles if r != LY.ROLE_TEST)
        self.side_roles = LY.guardside_roles(b.lead)
        self.write_roles = tuple(r for r in self.train_roles if r in roles)
        self.n_steps = int(state.vg.grid.n_steps)
        self.gou = np.asarray(state.vg.grid.group_of_unit, dtype=object)
        k = len(b.history_columns)
        if k and tuple(self.tree_cols[-k:]) != tuple(b.history_columns):
            raise ExportRefusal("P7", "the history columns are not the last tree columns")

    def group_of(self, keys: Any) -> Any:
        import numpy as np

        return self.gou[np.asarray(keys, dtype=np.int64) // self.n_steps]

    def train_positions(self, group: str) -> Any:
        import numpy as np

        parts = [self.b.roles[r].keys[self.group_of(self.b.roles[r].keys) == group] for r in self.write_roles]
        return np.unique(np.concatenate(parts)) if parts else np.zeros(0, dtype=np.int64)

    def _labels(self, pos: Any) -> Any:
        """y of each position from every role holding it (the vault's one label; asserted equal)."""
        import numpy as np

        y = np.full(pos.size, np.nan)
        got = np.zeros(pos.size, dtype=bool)
        for r in self.train_roles:
            rr = self.b.roles[r]
            if not rr.n:
                continue
            order = np.argsort(rr.keys, kind="stable")
            sk = rr.keys[order]
            idx = np.minimum(np.searchsorted(sk, pos), sk.size - 1)
            hit = sk[idx] == pos
            if hit.any():
                v = rr.y[order][idx[hit]]
                old = got[hit]
                if (old & (y[hit] != v)).any():
                    raise ExportRefusal("ROWS", "internal: one row holds two labels across roles")
                y[hit] = v
                got[hit] = True
        if not got.all():
            raise ExportRefusal("ROWS", "internal: a train row has no label")
        return y

    def flags(self, pos: Any) -> Dict[str, Any]:
        import numpy as np

        return {r: (np.isin(pos, self.b.roles[r].keys) if r in self.b.roles else np.zeros(pos.size, dtype=bool))
                for r in LY.TRAIN_ROLES}

    def train(self, group: str) -> Tuple[Optional[bytes], Optional[bytes], int, int, Dict[str, Any]]:
        """(train bytes, guardside bytes, rows, guardside rows, arrays for P13) of one group."""
        import numpy as np
        import pyarrow as pa

        pos = self.train_positions(group)
        if not pos.size:
            return None, None, 0, 0, {}
        vg = self.s.vg
        units, times = vg.unit_ids[pos], vg.steps[pos]
        groups = self.group_of(pos)
        fl = self.flags(pos)
        y = self._labels(pos)
        X = _float32_raw(self.b.fit_features.tree_features(pos), "tree features of group %s" % group)
        C = _float32_raw(self.b.fit_features.context(pos), "context of group %s" % group) if self.ctx_cols \
            else np.zeros((pos.size, 0), dtype=np.float32)
        nf = self.b.normal_fit(units, times)
        cols = _key_columns(units, groups, times, self.b.lead)
        cols += [(LY.ROLE_FLAG[r], fl[r], pa.bool_()) for r in LY.TRAIN_ROLES]
        cols += [(LY.COL_Y, y, pa.float64())]
        cols += [(LY.nfit_col(k), np.asarray(nf[k], dtype=np.float64), pa.float64()) for k in self.links]
        cols += _block_columns(LY.x_col, self.tree_cols, X, pa.float32())
        cols += _block_columns(LY.c_col, self.ctx_cols, C, pa.float32())
        train_bytes = table_bytes(cols)
        side = np.zeros(pos.size, dtype=bool)
        for r in self.side_roles:
            if r in self.write_roles:
                side |= fl[r]
        side_bytes, H = None, None
        if side.any():
            sp = pos[side]
            kcols = self.b.history_columns
            if kcols:
                if self.b.guard_history is None:
                    raise ExportRefusal("P13", "internal: history columns without a guard history pool")
                H = _float32_raw(self.b.guard_history.tree_features(sp), "guard history of group %s" % group)
            else:
                H = np.zeros((sp.size, 0), dtype=np.float32)
            ng = self.b.normal_guard(units[side], times[side])
            gcols = _key_columns(units[side], groups[side], times[side], self.b.lead)
            gcols += _block_columns(LY.h_col, kcols, H, pa.float32())
            gcols += [(LY.ngd_col(k), np.asarray(ng[k], dtype=np.float64), pa.float64()) for k in self.links]
            side_bytes = table_bytes(gcols)
        arrays = {"pos": pos, "X": X, "side": side, "H": H, "y": y, "times": times, "flags": fl}
        return train_bytes, side_bytes, int(pos.size), int(side.sum()), arrays

    def test(self, group: str) -> Tuple[Optional[bytes], int]:
        import numpy as np
        import pyarrow as pa

        rr = self.b.roles[LY.ROLE_TEST]
        sel = np.flatnonzero(self.group_of(rr.keys) == group)
        if not sel.size:
            return None, 0
        pos, units, times = rr.keys[sel], rr.units[sel], rr.times[sel]
        X = _float32_raw(self.b.fit_features.tree_features(pos), "test tree features of group %s" % group)
        C = _float32_raw(self.b.fit_features.context(pos), "test context of group %s" % group) if self.ctx_cols \
            else np.zeros((pos.size, 0), dtype=np.float32)
        nf = self.b.normal_fit(units, times)
        cols = _key_columns(units, self.group_of(pos), times, self.b.lead)
        cols += [(LY.COL_SAVED_ROW, np.asarray(self.b.test_order, dtype=np.int64)[sel], pa.int64())]
        cols += [(LY.nfit_col(k), np.asarray(nf[k], dtype=np.float64), pa.float64()) for k in self.links]
        cols += _block_columns(LY.x_col, self.tree_cols, X, pa.float32())
        cols += _block_columns(LY.c_col, self.ctx_cols, C, pa.float32())
        return table_bytes(cols), int(pos.size)


# ---------------------------------------------------------------------------------------------------
# parity
def _log_rows(log: Any, role: str, lead: int) -> Dict[str, Any]:
    purpose, kind = LOG_PURPOSE[role]
    sel = log[(log["object_kind"] == "donor_rows") & (log["purpose"] == purpose)
              & (log["lead"].astype(float) == float(lead)) & (log["cut_kind"] == kind)]
    if not len(sel):
        raise ExportRefusal("P1", "the run's fitctx_log has no donor_rows hand-out %r at lead %d (%s cut)"
                            % (purpose, lead, kind))
    vals = sel[["row_key_hash", "n_rows", "max_label_time", "cut"]].drop_duplicates()
    if len(vals) != 1:
        raise ExportRefusal("P1", "the run's fitctx_log holds %d different %r hand-outs at lead %d" % (len(vals), purpose,
                                                                                                    lead))
    r = vals.iloc[0]
    return {"row_key_hash": str(r["row_key_hash"]), "n_rows": int(r["n_rows"]),
            "max_label_time": int(r["max_label_time"]), "cut": int(r["cut"]), "purpose": purpose}


def check_fit_sets(b: LeadBuild, log: Any, check_ids: Mapping[str, str]) -> Dict[str, Any]:
    """P1-P3: each fit set's row-key hash, count and newest label against the run's fitctx_log; and (2.6) every
    refit row at or before the fit cut, every tune / guard-fit row at or before the guard cut."""
    import numpy as np
    from treeroute.labels.vault import row_key_hash

    out = {}
    for role, cid in check_ids.items():
        rr = b.roles[role]
        want = _log_rows(log, role, b.lead)
        got = {"row_key_hash": row_key_hash(rr.units, rr.times), "n_rows": rr.n,
               "max_label_time": int(rr.times.max()) if rr.n else -1}
        cut = b.cuts["fit_cut"] if role == LY.ROLE_REFIT else b.cuts["guard_cut"]
        if got["row_key_hash"] != b.donors[role].row_key_hash:
            raise ExportRefusal(cid, "internal: the %s rows are not the engine hand-out's rows" % role)
        if (got["row_key_hash"], got["n_rows"], got["max_label_time"]) != (
                want["row_key_hash"], want["n_rows"], want["max_label_time"]) or int(want["cut"]) != int(cut):
            raise ExportRefusal(cid, "lead %d %s rows: row-key hash %s, %d rows, newest %d; the run's %r hand-out: "
                                "%s, %d rows, newest %d (cut %d vs %d)"
                                % (b.lead, role, got["row_key_hash"][:16], got["n_rows"], got["max_label_time"],
                                   want["purpose"], want["row_key_hash"][:16], want["n_rows"], want["max_label_time"],
                                   want["cut"], cut))
        if rr.n and int(np.max(rr.times)) > int(cut):
            raise ExportRefusal("2.6", "lead %d %s rows reach %d, after the cut %d" % (b.lead, role, int(rr.times.max()),
                                                                                    cut))
        out[cid] = dict(got, role=role, cut=int(cut), log_purpose=want["purpose"], result="pass")
    return out


def _same_bytes(a: Any, b: Any) -> bool:
    import numpy as np

    a = np.ascontiguousarray(np.asarray(a))
    b = np.ascontiguousarray(np.asarray(b))
    return a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes()


def check_surface(cid: str, rows: RoleRows, saved: Any, issue_lead: Optional[int]) -> Dict[str, Any]:
    """P4 / P5: the surface rows (unit, time[, issue]) in order and y byte equal to the run's saved rows."""
    import numpy as np

    su = saved["unit"].to_numpy(dtype=object).astype(str)
    st = saved["time"].to_numpy(dtype=np.int64)
    sy = saved["y"].to_numpy(dtype=np.float64)
    ok = (su.size == rows.n and np.array_equal(su, rows.units.astype(str)) and np.array_equal(st, rows.times)
          and _same_bytes(sy, rows.y))
    if ok and issue_lead is not None:
        ok = np.array_equal(saved["issue"].to_numpy(dtype=np.int64), rows.times - int(issue_lead))
    if not ok:
        raise ExportRefusal(cid, "the surface rows (%d) are not the run's saved rows (%d) in keys, order or labels"
                            % (rows.n, su.size))
    return {"rows": rows.n, "result": "pass"}


def check_test_rows(rows: RoleRows, saved: Any, groups: Any, lead: int) -> Tuple[Dict[str, Any], Any]:
    """P6: the same (unit, group, time, lead, issue) set as the saved test rows, no duplicate; returns each
    exported row's index in the saved file."""
    import numpy as np

    keys = list(zip(rows.units.astype(str).tolist(), [str(g) for g in groups.tolist()], rows.times.tolist(),
                    [int(lead)] * rows.n, (rows.times - int(lead)).tolist()))
    sk = list(zip(saved["unit"].astype(str).tolist(), saved["group"].astype(str).tolist(),
                  saved["time"].astype(np.int64).tolist(), saved["lead"].astype(np.int64).tolist(),
                  saved["issue"].astype(np.int64).tolist()))
    if len(set(keys)) != len(keys) or len(set(sk)) != len(sk):
        raise ExportRefusal("P6", "duplicate test keys (export %d of %d unique, saved %d of %d unique)"
                            % (len(set(keys)), len(keys), len(set(sk)), len(sk)))
    if set(keys) != set(sk):
        raise ExportRefusal("P6", "lead %d: the export's test rows (%d) are not the saved test rows (%d): %d only in "
                            "the export, %d only saved" % (lead, len(keys), len(sk), len(set(keys) - set(sk)),
                                                           len(set(sk) - set(keys))))
    where = {k: i for i, k in enumerate(sk)}
    order = np.asarray([where[k] for k in keys], dtype=np.int64)
    return {"rows": rows.n, "same_order": bool(np.array_equal(order, np.arange(order.size))), "result": "pass"}, order


# ---------------------------------------------------------------------------------------------------
# the run
def run_bank_records(run: Path, lead: int) -> Dict[str, Tuple[Optional[str], Optional[str]]]:
    """The run's recorded bank fingerprint (and donor row-key hash, where recorded) per fit set of a lead:
    lead 0 refit -> tables.json fit_cut_store, tune -> inner_cut_store; lead L refit -> ladder/lead_L/lead.json
    fits.bank, guardfit -> guard_fits.bank (as pt/integ/parity_p15.py reads them)."""
    if int(lead) == 0:
        t = _read_json(run / "tables.json") if (run / "tables.json").is_file() else {}
        return {LY.ROLE_REFIT: ((t.get("fit_cut_store") or {}).get("bank_fingerprint"), None),
                LY.ROLE_TUNE: ((t.get("inner_cut_store") or {}).get("bank_fingerprint"), None)}
    path = run / LADDER_DIR / ("lead_%d" % int(lead)) / "lead.json"
    lj = _read_json(path) if path.is_file() else {}
    fb = (lj.get("fits") or {}).get("bank") or {}
    gb = (lj.get("guard_fits") or {}).get("bank") or {}
    return {LY.ROLE_REFIT: (fb.get("fingerprint"), fb.get("donor_row_key_hash")),
            LY.ROLE_GUARDFIT: (gb.get("fingerprint"), gb.get("donor_row_key_hash"))}


def parity_results(x: Any):
    """Every 'result' in one parity record, nested records included (a plain string is its own result)."""
    if isinstance(x, dict):
        if "result" in x:
            yield x["result"]
        for v in x.values():
            if isinstance(v, dict):
                yield from parity_results(v)
    else:
        yield x


def check_banks(b: "LeadBuild", run: Path, L: int, trees_per_group: int, log: Callable[[str], None]) -> Dict[str, Any]:
    """P15 (parity review 3): the engine's own bank fit (fit.bank.fit_donor_bank, the run's trees per group) on
    the lead's exported fit sets (the engine DonorRows the files were checked against byte for byte in P13)
    reproduces the run's recorded bank fingerprint, every tree's node arrays included, and its donor row-key
    hash where the run recorded one. One bank at a time; each is dropped once its fingerprint is read."""
    from treeroute.fit.bank import fit_donor_bank

    out: Dict[str, Any] = {}
    for role, (fp_want, rk_want) in run_bank_records(run, L).items():
        donor = b.donors.get(role)
        if donor is None:
            raise ExportRefusal("P15", "internal: lead %d has no %s donor rows" % (L, role))
        if not fp_want:
            raise ExportRefusal("P15", "lead %d: the run records no bank fingerprint for the %s fit set, so P15 "
                                "cannot be checked" % (L, role))
        t0 = time.time()
        log("P15 lead %d: fitting the %s bank (%d trees per group) to compare with the run's %s"
            % (L, role, trees_per_group, fp_want[:16]))
        bank = fit_donor_bank(donor, int(trees_per_group))
        fp = str(bank.manifest.bank_fingerprint)
        del bank
        gc.collect()
        rk = str(donor.row_key_hash)
        rec = {"bank_fingerprint": fp, "run_bank_fingerprint": fp_want, "row_key_hash": rk,
               "run_row_key_hash": rk_want, "seconds": round(time.time() - t0, 1),
               # the process's peak RAM so far, this bank fit included (Z check 7: P15's RAM at full size)
               "peak_rss_bytes_after": _peak_rss()}
        if fp != fp_want or (rk_want and rk != rk_want):
            raise ExportRefusal("P15", "lead %d %s: the engine's bank fit on the exported rows gives fingerprint %s "
                                "(row-key hash %s); the run recorded %s (%s)"
                                % (L, role, fp[:16], rk[:16], fp_want[:16], str(rk_want)[:16]))
        rec["result"] = "pass"
        out[role] = rec
        log("P15 lead %d %s: bank %s equals the run's (%.1f s; peak RAM so far %s GiB)"
            % (L, role, fp[:16], rec["seconds"], "?" if rec["peak_rss_bytes_after"] is None
               else "%.2f" % (rec["peak_rss_bytes_after"] / GIB)))
    return {"banks": out, "trees_per_group": int(trees_per_group), "result": "pass"}


# ---------------------------------------------------------------------------------------------------
# the lean export (owner ruling AA4): two engine steps that only GUARD and change no exported value are taken from
# the run's own record instead of being measured again. What protects each skip: the test-year shares feed only
# R30's flags, and R30 is a refusal gate, not a value (engine derive/unit_rules.py); the lean shares are COPIED from
# the run's derived.json, so I7's derived.json comparison cannot see a wrong share by itself (it compares the copy
# with its source); what does is I5's check of the data files (size and mtime: the census the count would read is
# the run's), the first_pass_sha256 cross-check of derived.json, and the fact that a wrong share could only make
# the export refuse, never change an exported value. The separability guard decides no number (the per-group path
# is the run's own path). P1-P14 (P15 with --p15 or an accepted difference) check the rows, labels, normals, c and
# banks byte for byte.
LEAN_STEPS = {
    "r30_test_year_count": "R30's per-test-year missing count streamed over every census row of the test years "
                           "(pipeline/stream.py StreamedShareReader._count_setup/_count_group, with its window check "
                           "_check_block): taken from the run's derived.json R30 inputs.test_year_missing_share. "
                           "Skipped only when the count would run (not every census row is a picked row); when "
                           "every census row is picked the engine takes the shares from the picked readers at no "
                           "extra cost and nothing is skipped",
    "separability_check": "the per-group path's feature-script separability check on a sample (pipeline/stream.py "
                          "check_group_separable: one sample reader of the sampled groups together and one per "
                          "group): taken from the run's per_group_plan.json 'separability' record when it shows the "
                          "check passed (or was not needed)",
}


def _run_test_year_shares(run: Path) -> Optional[Dict[str, Dict[str, float]]]:
    """The run's own R30 test-year missing shares {column: {year: share}} (derived.json), or None."""
    d = _read_json(run / "derived.json")
    r30 = d.get("R30") if isinstance(d, dict) else None
    v = ((r30 or {}).get("inputs") or {}).get("test_year_missing_share")
    return v if isinstance(v, dict) else None


def _run_separability(run: Path) -> Optional[Dict[str, Any]]:
    """The run's own separability record (per_group_plan.json), when it shows the check passed or was not needed."""
    p = run / "per_group_plan.json"
    if not p.is_file():
        return None
    sep = (_read_json(p) or {}).get("separability")
    if not isinstance(sep, dict):
        return None
    if sep.get("checked") is True and str(sep.get("result", "")).startswith("group-separable"):
        return sep
    if sep.get("checked") is False and sep.get("reason"):
        return sep
    return None


class LeanEngine(object):
    """Context manager around the engine's derive (export_run): while active, the two LEAN_STEPS are taken from the
    run's record. Only class / module attributes of treeroute.pipeline.stream are replaced in THIS process, and
    always put back on exit (no engine file is written). rec: what was skipped, counted per step."""

    def __init__(self, run: Path, log: Callable[[str], None]) -> None:
        self.run = Path(run)
        self.log = log
        self.shares = _run_test_year_shares(self.run)
        self.sep = _run_separability(self.run)
        self.rec: Dict[str, Any] = {
            "on": True, "steps": dict(LEAN_STEPS),
            "r30_test_year_count": {"skipped": 0, "not_needed": 0, "run_record": self.shares is not None},
            "separability_check": {"skipped": 0, "run_record": self.sep is not None, "ran": 0}}
        self._saved: List[Tuple[Any, str, Any]] = []

    def _shares_for(self, spec: Any, test_years: Sequence[int]) -> Dict[Tuple[str, int], float]:
        """The run's shares in the order the engine's own count returns them (stream.py _count_finish: tree columns
        in spec order, then the test years)."""
        if self.shares is None:
            raise ExportRefusal("I7", "lean export: the run's derived.json holds no R30 test-year shares to take "
                                "instead of the count", fix="export with --full-engine-checks")
        years = [int(y) for y in test_years]
        stray = sorted(set(str(y) for v in self.shares.values() for y in v) - set(str(y) for y in years))
        if stray:
            raise ExportRefusal("I7", "lean export: the run's R30 test-year shares name years %s outside the test "
                                "years %s" % (stray, years), fix="export with --full-engine-checks")
        out: Dict[Tuple[str, int], float] = {}
        for c in spec.tree_features:
            for y in years:
                v = (self.shares.get(str(c)) or {}).get(str(y))
                if v is not None:
                    out[(str(c), y)] = float(v)
        return out

    def __enter__(self) -> "LeanEngine":
        from treeroute.pipeline import stream as STR

        lean = self
        o_measure = STR.StreamedShareReader.measure
        o_sep = STR.check_group_separable

        def measure(self_, donor, lags, test_years):
            picked = getattr(self_.census, "_picked", None)
            if picked is not None:
                all_picked = int(len(picked[1].unit_ids)) == int(self_.census.rows)
                key = (STR._lag_key(lags), tuple(int(y) for y in test_years))
                if all_picked:
                    lean.rec["r30_test_year_count"]["not_needed"] += 1
                elif key not in self_._test_year_cache:
                    self_._test_year_cache[key] = lean._shares_for(self_.spec, test_years)
                    lean.rec["r30_test_year_count"]["skipped"] += 1
                    lean.log("LEAN (AA4): R30's test-year count over every census row is not run; its shares "
                             "are copied from the run's own derived.json R30 (R30 only gates a refusal; the "
                             "census is the run's by I5's data-file check)")
            out = o_measure(self_, donor, lags, test_years)
            if lean.rec["r30_test_year_count"]["skipped"]:
                self_.test_year_source = "LEAN EXPORT: the run's own count (derived.json R30), not measured again"
            return out

        def separable(*a, **kw):
            if lean.sep is None:
                lean.rec["separability_check"]["ran"] += 1
                return o_sep(*a, **kw)
            lean.rec["separability_check"]["skipped"] += 1
            lean.log("LEAN (AA4): the separability check on a sample is not run again; the run's own check: %s"
                     % (lean.sep.get("result") or lean.sep.get("reason")))
            return dict(lean.sep, lean_export="taken from the run's per_group_plan.json, not checked again")

        self._saved = [(STR.StreamedShareReader, "measure", o_measure), (STR, "check_group_separable", o_sep)]
        STR.StreamedShareReader.measure = measure
        STR.check_group_separable = separable
        return self

    def __exit__(self, *exc: Any) -> bool:
        for obj, name, value in reversed(self._saved):
            setattr(obj, name, value)
        self._saved = []
        return False


def _pipeline(package: Path, roots: LY.Roots, kind: str, machine: Any, echo: Callable[[str], None]) -> Any:
    from treeroute.pipeline.run import Pipeline, _is_table

    if _is_table(package):
        from treeroute.pipeline.table_run import TablePipeline

        return TablePipeline(package, roots.export_ckpt_root, kind, machine=machine, echo=echo)
    return Pipeline(package, roots.export_ckpt_root, kind, machine=machine, echo=echo)


def rebuilt_config(pipe: Any) -> Dict[str, Any]:
    """The run config as the engine builds it at _open (grid: pipeline/run.py:1124-1133; table:
    pipeline/table_run.py:309-317), from the export's own load, read and derive."""
    from treeroute import engine_constants as K
    from treeroute.derive import derived_sha256
    from treeroute.pipeline import data as D
    from treeroute.pipeline.run import _file_list_sha

    if getattr(pipe, "input", None) == "table":
        from treeroute.pipeline.table_run import INPUT_TABLE

        return {"kind": pipe.kind, "package": pipe.package.dataset.name,
                "package_fingerprint": pipe.package.fingerprint, "derived_sha256": derived_sha256(pipe.derived),
                "draft": pipe.draft.record(), "groups": list(pipe.run_groups),
                "trees_per_group": pipe.trees_per_group, "input": INPUT_TABLE,
                "data": pipe.data_manifest, "target_files_sha256": _file_list_sha(pipe.data_files),
                "static_files_sha256": _file_list_sha([]), "driver_files_sha256": _file_list_sha([]),
                "engine_constants_sha256": K.constants_hash(),
                "feature_list": list(pipe.spec.tree_features), "context_list": list(pipe.spec.context),
                "strata": list(pipe.spec.strata)}
    return {"kind": pipe.kind, "package": pipe.package.dataset.name,
            "package_fingerprint": pipe.package.fingerprint, "derived_sha256": derived_sha256(pipe.derived),
            "draft": pipe.draft.record(), "groups": list(pipe.run_groups),
            "trees_per_group": pipe.trees_per_group,
            "data": pipe.data_manifest, "target_files_sha256": _file_list_sha(pipe.data_files),
            "static_files_sha256": _file_list_sha(D.static_files(pipe.pkg)),
            "driver_files_sha256": _file_list_sha(pipe.driver_files),
            "engine_constants_sha256": K.constants_hash(),
            "feature_list": list(pipe.spec.tree_features) + list(pipe.derived["R17"].value.columns),
            "context_list": list(pipe.spec.context), "strata": list(pipe.spec.strata)}


def check_identity_after_derive(pipe: Any, run: Path, manifest: Mapping[str, Any],
                                accepted: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """I5 (the config key by key), I6 (the run fingerprint formula, runs/fingerprint.py run_fingerprint), I7
    (derived.json as JSON, pipeline/run.py:1163-1172). With an accepted difference, a key it lists passes I5
    only at exactly its listed run value (the manifest's) and LIVE value (the rebuilt one); I6 then rebuilds the
    fingerprint with the run's value of each accepted key, so every other key is still checked by both."""
    import hashlib

    from treeroute.derive import derived_document
    from treeroute.runs.atomic import dumps, dumps_canonical

    config = rebuilt_config(pipe)
    mine = json.loads(dumps(config))
    theirs = manifest.get("config") or {}
    diff = sorted(k for k in set(mine) | set(theirs) if mine.get(k) != theirs.get(k))
    allowed = {str(c["key"]): c for c in ((accepted or {}).get("I5_config_keys") or [])}
    acc_keys, bad = [], []
    for k in diff:
        c = allowed.get(k)
        if c is not None and k in theirs and k in mine and theirs[k] == c["run"] and mine[k] == c["live"]:
            acc_keys.append({"key": k, "run": c["run"], "live": c["live"], "ruling": accepted["ruling"]})
        else:
            bad.append(k)
    if bad:
        note = ""
        if allowed:
            note = " (accepted by ruling %s, at their listed values only: %s)" % (accepted["ruling"], sorted(allowed))
        raise ExportRefusal("I5", "the rebuilt run config differs from the run's manifest in %s%s" % (bad, note),
                            fix="the package, its data, the engine constants or the engine changed since the run")
    for_fp = dict(config)
    for c in acc_keys:
        for_fp[c["key"]] = theirs[c["key"]]
    fp = hashlib.sha256(dumps_canonical({"config": for_fp, "engine_code": manifest["engine_modules"],
                                         "versions": manifest["versions"], "python": manifest["python"]})
                        .encode("ascii")).hexdigest()
    if fp != manifest.get("fingerprint"):
        raise ExportRefusal("I6", "the run fingerprint rebuilt from the config is %s, the run's is %s"
                            % (fp[:16], str(manifest.get("fingerprint"))[:16]))
    now = json.loads(dumps(derived_document(pipe.derived)))
    if now != _read_json(run / "derived.json"):
        raise ExportRefusal("I7", "derived.json derived now differs from the run's derived.json")
    out = {"I5": "pass", "I6": "pass", "I7": "pass", "config_keys": sorted(mine)}
    if acc_keys:
        out["I5"] = "pass with %d key(s) accepted by ruling %s: %s" % (len(acc_keys), accepted["ruling"],
                                                                       [c["key"] for c in acc_keys])
        out["I6"] = "pass (rebuilt with the run's value of each accepted key)"
        out["I5_accepted"] = acc_keys
    return out


def _units_columns(state: Any, pipe: Any) -> Tuple[List[Tuple[str, Any, Any]], List[str]]:
    """units.parquet: every bank unit, its group, scored or not, seen during design or not, each report stratum."""
    import numpy as np
    import pyarrow as pa

    units = [str(u) for u in state.bank_units]
    groups = [str(state.unit_group[u]) for u in state.bank_units]
    scored = set(str(u) for u in state.scored_units)
    seen = set(str(g) for g in (pipe.pkg.split.seen_during_design or ()))
    cols = [(LY.COL_UNIT, units, pa.string()), (LY.COL_GROUP, groups, pa.string()),
            ("is_scored", np.asarray([u in scored for u in units], dtype=bool), pa.bool_()),
            ("seen_during_design", np.asarray([g in seen for g in groups], dtype=bool), pa.bool_())]
    strata = sorted(getattr(pipe, "strata", None) or {})
    for col in strata:
        values = pipe.strata[col]
        if hasattr(values, "reindex"):                       # a grid stratum: one value per unit (pd.Series)
            v = values.reindex(np.asarray(units, dtype=object)).to_numpy()
        else:                                                # a table stratum: one value per row position
            pos = state.row_pos
            v = np.asarray(values)[np.asarray([pos[u] for u in units], dtype=np.int64)]
        if v.dtype == object:
            cols.append((col, [None if x is None else str(x) for x in v.tolist()], pa.string()))
        else:
            cols.append((col, np.asarray(v, dtype=np.float64), pa.float64()))
    return cols, strata


def _read_saved(path: Path, columns: Sequence[str]) -> Any:
    """A saved prediction file read with the named columns only (never y of a test file: 2.6)."""
    import pyarrow.parquet as pq

    names = pq.read_schema(path).names
    want = [c for c in columns if c in names]
    # ParquetFile.read with the column list (pq.read_table goes through the dataset API, which opens the file
    # with no column list first)
    return pq.ParquetFile(path).read(columns=want).to_pandas()


def export_run(run: Any, package: Any = None, leads: Any = "all", roles: Any = None, config: Any = None,
               resume: bool = False, machine: Any = None, echo: Optional[Callable[[str], None]] = None,
               launch_record: Optional[Mapping[str, Any]] = None, p15: Optional[bool] = None,
               lean: bool = True) -> List[Path]:
    """Export one finished run (SPEC_RIVALS.md section 2). Returns the lead folders written.

    run: the run folder; package: the package folder (default: from the run's argv); leads: 'all', one lead
    or a comma list; roles: None (all) or a list / comma text of roles; config: rivals.yaml (path, mapping or
    Roots); resume: skip finished group files of the same export key; machine: an engine machine object (else
    rivals.yaml's machine_file); launch_record: the launcher's record when main() pinned the threads (None in
    tests: recorded as not pinned); p15: run the bank-fingerprint check P15 (None: only when the run has an
    accepted engine difference, which REQUIRES it and every other P check to pass); lean: the lean export of
    owner ruling AA4 (LEAN_STEPS taken from the run's record; False = every engine step runs, --full-engine-checks).
    """
    t_start = time.time()
    roots = LY.as_roots(config)
    LY.import_engine(roots.engine_root)
    import numpy as np
    import pandas as pd
    from treeroute.package.load import load_package
    from treeroute.runs.fingerprint import library_versions
    from treeroute.runs.machine import load_machine
    from treeroute.runs.registry import Registry

    timings: Dict[str, float] = {}
    run = Path(run).resolve()
    machine = machine if machine is not None else load_machine(roots.machine_file)
    registry = Registry(machine.registry_dir)
    log = Logger(registry, echo)
    # ---- I1 - I4: the run folder, the package, the libraries and the engine (files only)
    all_leads = check_run_files(run)
    manifest = _read_json(run / "manifest.json")
    plan = _read_json(run / "plan.json")
    package = Path(package).resolve() if package is not None else default_package(manifest, Path(roots.engine_root))
    pkg = load_package(package)
    if pkg.fingerprint != manifest.get("package_fingerprint"):
        raise ExportRefusal("I2", "the package %s has fingerprint %s; the run's is %s"
                            % (package, pkg.fingerprint[:16], str(manifest.get("package_fingerprint"))[:16]))
    versions = library_versions()
    if versions != manifest.get("versions") or platform.python_version() != manifest.get("python"):
        diff = sorted(k for k in set(versions) | set(manifest.get("versions") or {})
                      if versions.get(k) != (manifest.get("versions") or {}).get(k))
        raise ExportRefusal("I3", "LIVE library versions or Python differ from the run's (libraries %s; Python %s vs %s)"
                            % (diff, platform.python_version(), manifest.get("python")))
    package_name = str(manifest["config"]["package"])
    accepted = acceptance_for(roots, run, manifest)
    if accepted is not None and p15 is False:
        raise ExportRefusal("ARGS", "run id %s has an accepted engine difference (ruling %s): P15 cannot be "
                            "switched off" % (accepted["run_id"], accepted["ruling"]))
    need_p15 = bool(p15) or accepted is not None
    engine = check_engine(manifest, roots, machine.registry_dir, package_name, accepted)
    want_leads = parse_leads(leads, all_leads)
    if accepted is not None and set(want_leads) != set(all_leads):
        # Z check 1 a: an accepted difference holds for the WHOLE run or not at all, so it is exported in one call
        raise ExportRefusal("ARGS", "run id %s has an accepted engine difference (ruling %s): export every lead "
                            "(%s) in one call, not %s" % (accepted["run_id"], accepted["ruling"], list(all_leads),
                                                          list(want_leads)), fix="pass --lead all")
    want_roles = parse_roles(roles)
    for L in want_leads:
        if not [r for r in LY.roles_of_lead(L) if r in want_roles]:
            raise ExportRefusal("ARGS", "the roles %s name nothing to write at lead %d" % (list(want_roles), L))
    run_name = run.name
    lead_dirs = {L: LY.export_lead_dir(roots, package_name, run_name, L) for L in want_leads}
    stamp = LY.utc_stamp()
    live_file = engine["live_file_sha"]
    ecode = code_sha()
    keys = {L: LY.sha256_json({"run_fingerprint": manifest["fingerprint"], "package_fingerprint": pkg.fingerprint,
                               "lead": int(L), "roles": list(want_roles), "export_code_sha256": ecode,
                               "engine_file_sha": live_file}) for L in want_leads}
    writers = {L: Writer(lead_dirs[L], keys[L], resume, roots, registry, stamp, log) for L in want_leads}
    for L in want_leads:
        writers[L].check_fresh()                   # a refusal before the lock moves nothing
    early = ["I1-I4 pass: run files present; package fingerprint %s; libraries and Python equal; engine: %s"
             % (pkg.fingerprint[:16], engine["rule"])]
    if accepted is not None:
        early.append("ACCEPTED ENGINE DIFFERENCE (ruling %s, run id %s): hops %s, config keys %s; every parity "
                     "check P1-P15 must pass or the export refuses"
                     % (accepted["ruling"], accepted["run_id"],
                        ["%s->%s" % (h["from"][:8], h["to"][:8]) for h in accepted.get("I4_hops") or []],
                        [c["key"] for c in accepted.get("I5_config_keys") or []]))
    # ---- I8: disk
    need = {L: estimate_lead_bytes(run, manifest, L) for L in want_leads}
    biggest = max(need.values())
    pools, pools_src = estimate_engine_temp_bytes(run, want_leads)
    exp_drive = os.path.splitdrive(str(Path(roots.export_root).resolve()))[0].upper()
    tmp_drive = os.path.splitdrive(str(Path(machine.temp_dir).resolve()))[0].upper()
    free = free_disk(Path(roots.export_root))
    if exp_drive == tmp_drive:
        want_free = biggest + pools + DISK_SLACK_BYTES
        if free < want_free:
            raise ExportRefusal("I8", "%s has %.2f GiB free; this export needs about %.2f GiB (one lead's export) + "
                                "%.2f GiB (the engine's temp pools, %s) + 3 GiB"
                                % (exp_drive, free / GIB, biggest / GIB, pools / GIB, pools_src),
                                fix="free disk (the run size is never reduced)")
    else:
        if free < biggest + DISK_SLACK_BYTES:
            raise ExportRefusal("I8", "the export drive has %.2f GiB free; one lead's export needs about %.2f GiB + "
                                "3 GiB" % (free / GIB, biggest / GIB), fix="free disk (the run size is never reduced)")
        tfree = free_disk(Path(machine.temp_dir))
        if tfree < pools + DISK_SLACK_BYTES:
            raise ExportRefusal("I8", "the engine temp drive has %.2f GiB free; its pools need about %.2f GiB (%s) + "
                                "3 GiB" % (tfree / GIB, pools / GIB, pools_src), fix="free disk")
    log("I8 pass: %.2f GiB free; the largest lead's export about %.2f GiB; the engine's temp pools about %.2f GiB (%s)"
        % (free / GIB, biggest / GIB, pools / GIB, pools_src))
    # ---- the engine: I9 lock, load, groups, target pre-flight, read, derive
    kind = str(manifest["config"]["kind"])
    pipe = _pipeline(package, roots, kind, machine, lambda line: log("engine: %s" % line))
    out_dirs: List[Path] = []
    seal = LY.accept_seal_file(roots, package_name, run_name)
    started = False
    try:
        t0 = time.time()
        pipe._lock()
        # only now, under the heavy-job lock, are unrecorded files moved aside (robustness review 9)
        started = True
        if seal.is_file():                         # an older seal never covers this call's manifests
            LY.move_aside(seal, roots.moved_root, registry, stamp, relative_to=roots.export_root)
        for L in want_leads:
            writers[L].prepare()
            lead_dirs[L].mkdir(parents=True, exist_ok=True)
            log.attach(lead_dirs[L] / LY.EXPORT_LOG)
        log("export of %s (package %s, run fingerprint %s), leads %s, roles %s%s"
            % (run, package_name, manifest["fingerprint"][:16], list(want_leads), list(want_roles),
               ", resume" if resume else ""))
        for line in early:
            log(line)
        log("I9 pass: the heavy-job lock is held (%s)" % pipe.lock.path)
        pipe._load()
        pipe._groups()
        if getattr(pipe, "input", None) == "table":
            for f in (manifest["config"].get("data") or {}).get("files") or []:
                if LY.sha256_file(f["path"]) != f["sha256"]:
                    raise ExportRefusal("I5", "the table store file %s no longer has the run's sha256" % f["path"])
        pipe._preflight_target()
        pipe._read()
        timings["read"] = round(time.time() - t0, 2)
        t0 = time.time()
        lean_rec: Dict[str, Any] = {"on": False, "reason": "--full-engine-checks: every engine step ran"}
        if lean:
            with LeanEngine(run, log) as le:
                pipe._derive()
            lean_rec = le.rec
        else:
            pipe._derive()
        if pipe.smoke:
            pipe._smoke_bank_plans(pipe._vault(None))        # as Pipeline.run (pipeline/run.py:1375-1376)
        ident = check_identity_after_derive(pipe, run, manifest, accepted)
        ident.update({"I1": "pass", "I2": {"package_fingerprint": pkg.fingerprint, "result": "pass"},
                      "I3": {"python": platform.python_version(), "result": "pass"},
                      "I4": {"rule": engine["rule"], "result": "pass" if not any(h.get("accepted") for h in
                                                                                 engine["hops"])
                             else "pass with accepted hop(s), ruling %s" % accepted["ruling"]},
                      "I8": {"free_bytes": int(free), "lead_export_bytes_estimate": {str(k): int(v) for k, v in
                                                                                     need.items()},
                             "engine_temp_pools_bytes_estimate": int(pools), "engine_temp_pools_source": pools_src,
                             "slack_bytes": DISK_SLACK_BYTES, "result": "pass"},
                      "I9": {"lock": str(pipe.lock.path).replace("\\", "/"), "result": "pass"}})
        if accepted is not None and not any(h.get("accepted") for h in engine["hops"]) \
                and not ident.get("I5_accepted"):
            # Z check 3: an entry that carries nothing is stale data, never recorded as an accepted difference
            raise ExportRefusal("ACCEPT", "run id %s has an accepted-difference entry (ruling %s) but passes I4 and "
                                "I5 without it" % (accepted["run_id"], accepted["ruling"]),
                                fix="remove the entry from the rival config, or ask the owner")
        timings["derive"] = round(time.time() - t0, 2)
        log("I5-I7 pass: the rebuilt run config, the run fingerprint and derived.json equal the run's%s"
            % ("" if not ident.get("I5_accepted") else " (accepted config keys, ruling %s: %s)"
               % (accepted["ruling"], [c["key"] for c in ident["I5_accepted"]])))
        unit_hashes = json.loads(json.dumps(_clean(pipe._unit_list_hashes())))
        pipe._release_census()
        host = LY.export_run_dir(roots, package_name, run_name) / LY.ENGINE_FOLDER
        LY.assert_writable(registry, host)
        if host.exists() and any(host.iterdir()):
            LY.move_aside(host, roots.moved_root, registry, stamp, relative_to=roots.export_root)
        host.mkdir(parents=True, exist_ok=True)
        from treeroute.derive import derived_sha256
        from treeroute.runs.status import StatusWriter

        pipe.folder = host
        pipe.fingerprint = manifest["fingerprint"]
        pipe.status = StatusWriter(host, pipe.fingerprint)
        pipe.derived_sha = derived_sha256(pipe.derived)
        pipe._temp()
        common = {"pipe": pipe, "run": run, "manifest": manifest, "plan": plan, "roots": roots,
                  "registry": registry, "engine": engine, "ident": ident, "unit_hashes": unit_hashes,
                  "roles": want_roles, "package": package, "package_name": package_name, "pkg": pkg,
                  "launch_record": launch_record, "timings": timings, "t_start": t_start,
                  "accepted": accepted, "need_p15": need_p15, "lean": lean_rec}
        if getattr(pipe, "input", None) == "table":
            from treeroute.pipeline.table_passes import TableRunState as State
        else:
            from treeroute.pipeline.passes import RunState as State
        with State(pipe) as state:
            if getattr(pipe, "input", None) != "table" and 0 not in want_leads:
                _state_attrs(state)
            for L in want_leads:
                status = StatusWriter(lead_dirs[L], pipe.fingerprint)
                status.beat("export", "lead %d" % L)
                with ExitStack() as stack:
                    t0 = time.time()
                    if getattr(pipe, "input", None) == "table":
                        b = build_table_lead(state, L, stack, log)
                    else:
                        b = build_grid_lead(state, L, stack, log)
                    timings["lead_%d_rows" % L] = round(time.time() - t0, 2)
                    out_dirs.append(_write_lead(state, b, writers[L], lead_dirs[L], keys[L], common, log))
                    del b
                gc.collect()
                status.finish("finished", "lead %d exported" % L)
        if accepted is not None:
            write_accept_seal(seal, accepted, manifest, all_leads, lead_dirs, ecode, registry)
            log("ACCEPTED ENGINE DIFFERENCE (ruling %s): every lead %s passed P1-P15 in this call; seal written "
                "last: %s" % (accepted["ruling"], list(all_leads), seal))
        return out_dirs
    except BaseException:
        if accepted is not None and started:
            # Z check 1 b: under an accepted difference one failure refuses the WHOLE run: no lead stays usable
            moved = withdraw_accepted_leads(lead_dirs, roots, registry)
            log("ACCEPTED ENGINE DIFFERENCE (ruling %s): the export stopped, so %d lead manifest(s) were moved "
                "aside and no lead of run id %s is usable: %s" % (accepted["ruling"], len(moved), accepted["run_id"],
                                                                  [str(m) for m in moved]))
        raise
    finally:
        pipe._release()


def write_accept_seal(seal: Path, accepted: Mapping[str, Any], manifest: Mapping[str, Any], all_leads: Sequence[int],
                      lead_dirs: Mapping[int, Path], ecode: str, registry: Any) -> Path:
    """Z check 1 c: written last, after every lead of the run passed P1-P15 in one call; lists each lead's
    export_manifest.json sha256 (the harness refuses an accepted run without a seal covering every lead)."""
    leads = {}
    for L in all_leads:
        m = Path(lead_dirs[L]) / LY.EXPORT_MANIFEST
        if not m.is_file():
            raise ExportRefusal("ACCEPT", "internal: lead %d has no export_manifest.json to seal" % L)
        leads[str(int(L))] = {"manifest": "lead_%d/%s" % (int(L), LY.EXPORT_MANIFEST),
                              "manifest_sha256": LY.sha256_file(m)}
    doc = {"format": LY.FORMAT_ACCEPT_SEAL, "written_utc": LY.utc_now(), "run_id": accepted["run_id"],
           "run_fingerprint": manifest["fingerprint"], "ruling": accepted["ruling"],
           "requires_parity": REQUIRED_PARITY_TEXT, "leads_of_run": [int(L) for L in all_leads], "leads": leads,
           "export_code_sha256": ecode,
           "meaning": "every lead of this run passed every parity check P1-P15 (nested results included) in one "
                      "export call under the accepted engine difference; written last"}
    LY.assert_writable(registry, seal)
    return LY.write_json_atomic(seal, doc, registry)


def withdraw_accepted_leads(lead_dirs: Mapping[int, Path], roots: LY.Roots, registry: Any) -> List[Path]:
    """Z check 1 b: move every lead's export_manifest.json of the run aside (never deleted), so a refused accepted
    export leaves no lead a board can start on. A fresh stamp: prepare() may have used this call's stamp already."""
    stamp = LY.utc_stamp()
    moved = []
    for L in sorted(lead_dirs):
        m = Path(lead_dirs[L]) / LY.EXPORT_MANIFEST
        if m.is_file():
            moved.append(LY.move_aside(m, roots.moved_root, registry, stamp, relative_to=roots.export_root))
    return moved


def _write_lead(state: Any, b: LeadBuild, writer: Writer, lead_dir: Path, key: str, common: Mapping[str, Any],
                log: Logger) -> Path:
    """Write one lead's files, run P1-P14, then export_manifest.json (written last)."""
    import numpy as np
    import pandas as pd
    from treeroute.derive.shapes import Link
    from treeroute.layer import arms as LA
    from treeroute.layer.links import clip_to_legal, link_forward
    from treeroute.pipeline import router as PR
    from treeroute.report import metrics as M
    from treeroute.runs.manifest import _hash_or_none

    t0 = time.time()
    pipe, run, manifest, plan = common["pipe"], common["run"], common["manifest"], common["plan"]
    roles = common["roles"]
    L = b.lead
    neighbour = state.kind == PR.KIND_NEIGHBOUR
    p = {}
    # ---- P7 columns
    tree_cols = list(manifest.get("feature_list") or [])
    hist_cols = list(b.history_columns)
    if getattr(pipe, "input", None) == "table":
        mine_tree = list(pipe.spec.tree_features)
    else:
        mine_tree = list(pipe.spec.tree_features) + hist_cols
    ctx_cols = list(pipe.spec.context)
    if (mine_tree != tree_cols or _hash_or_none(mine_tree) != manifest.get("feature_list_hash")
            or hist_cols != list(plan.get("history_columns") or []) or ctx_cols != list(plan.get("context") or [])
            or ctx_cols != list(manifest["config"].get("context_list") or [])
            or tuple(b.fit_features.tree_columns) != tuple(mine_tree)
            or tuple(b.fit_features.context_columns) != tuple(ctx_cols)):
        raise ExportRefusal("P7", "the tree, history or context columns differ from the run's manifest and plan")
    p["P7"] = {"tree_columns": len(mine_tree), "history_columns": len(hist_cols), "context_columns": len(ctx_cols),
               "feature_list_hash": manifest.get("feature_list_hash"), "result": "pass"}
    # ---- P8 groups and unit lists
    groups = sorted(state.groups)
    tables = _read_json(run / "tables.json") if (run / "tables.json").is_file() else {}
    built = sorted(set(x["group"] for x in ((tables.get("fit_cut_store") or {}).get("builds") or [])))
    if groups != sorted(manifest["config"]["groups"]) or groups != built:
        raise ExportRefusal("P8", "the groups (%d) differ from the run config's (%d) or the fit-cut store's builds (%d)"
                            % (len(groups), len(manifest["config"]["groups"]), len(built)))
    if common["unit_hashes"] != json.loads(json.dumps(manifest.get("unit_list_hashes"))):
        raise ExportRefusal("P8", "the bank or scored unit-list hashes differ from the run's manifest")
    p["P8"] = {"groups": len(groups), "unit_list_hashes": "equal", "result": "pass"}
    # ---- P12 c (legal range below, with the test rows)
    c_doc = None
    if Link.LOG_C in state.links:
        entry = _read_json(run / "derived.json").get("R23:lead=%d" % L) or {}
        c_doc = entry.get("value")
        if c_doc is None or float(c_doc) != float(b.c):
            raise ExportRefusal("P12", "lead %d: c %r differs from derived.json R23:lead=%d %r" % (L, b.c, L, c_doc))
    elif b.c is not None:
        raise ExportRefusal("P12", "internal: a c without the log_c link")
    p["P12"] = {"c": b.c, "derived_c": c_doc, "result": "pass"}
    # ---- P1-P3 fit sets
    fitlog = pd.read_parquet(run / "fitctx_log.parquet")
    ids = {LY.ROLE_REFIT: "P1", LY.ROLE_TUNE: "P2"} if L == 0 else {LY.ROLE_REFIT: "P1", LY.ROLE_GUARDFIT: "P3"}
    p.update(check_fit_sets(b, fitlog, ids))
    # ---- P4 / P5 surfaces
    lead_run = run if L == 0 else run / LADDER_DIR / ("lead_%d" % L)
    if L == 0:
        inner = _read_saved(run / "inner_preds.parquet",
                            ["unit", "group", "time", "y", DONOR_MEDIAN_COLUMN]
                            + [M.PRE_PREFIX + LA.arm_name(LA.trees_off_of(x)) for x in state.links])
        p["P4"] = check_surface("P4", b.roles[LY.ROLE_INNER], inner, None)
        saved_surface, surf = inner, b.roles[LY.ROLE_INNER]
    else:
        guard = pd.read_parquet(lead_run / "guard_preds.parquet")
        p["P5"] = check_surface("P5", b.roles[LY.ROLE_GUARD], guard, L)
        saved_surface, surf = guard, b.roles[LY.ROLE_GUARD]
    # ---- P10 / P11 the guard-cut normal on the surface rows
    tol_doc = (_read_json(run / "decision_checks.json").get("tolerances") or {}).get("tolerance") or {}
    ng = b.normal_guard(surf.units, surf.times)
    cid = "P10" if L == 0 else "P11"
    rec: Dict[str, Any] = {}
    if neighbour:
        med = float(b.records["normal_guard"]["donor_median"])
        clipped = clip_to_legal(np.full(surf.n, med), state.legal, False)[0]
        if DONOR_MEDIAN_COLUMN in saved_surface.columns:
            gap = float(np.max(np.abs(clipped - saved_surface[DONOR_MEDIAN_COLUMN].to_numpy(dtype=np.float64)))) \
                if surf.n else 0.0
        else:
            gap = None
        if L == 0:
            rec = {"rule": "neighbour kind: the guard-cut median is not compared with the per-fold medians "
                           "(reading R-CN); printed", "max_abs_gap_to_saved_fold_medians": gap, "result": "printed"}
            log("P10 (printed, not compared): the tune-row median %.6g vs the saved per-fold medians: largest gap %s"
                % (med, gap))
        else:
            if gap is None or not _same_bytes(clipped, saved_surface[DONOR_MEDIAN_COLUMN].to_numpy(dtype=np.float64)):
                raise ExportRefusal("P11", "lead %d: the guard-fit rows' median %r, clipped, is not the saved %s"
                                    % (L, med, DONOR_MEDIAN_COLUMN))
            rec = {"donor_median": med, "rows": surf.n, "result": "pass"}
    else:
        per = {}
        for x in state.links:
            col = M.PRE_PREFIX + LA.arm_name(LA.trees_off_of(x))
            if col not in saved_surface.columns:
                continue
            cc, uu = PR.link_arg(x, b.c, state.ub)
            z = link_forward(saved_surface[col].to_numpy(dtype=np.float64), x, cc, uu)
            gap = float(np.max(np.abs(np.asarray(ng[x.value]) - z))) if surf.n else 0.0
            tol = float(tol_doc[x.value])
            if not gap <= tol:
                raise ExportRefusal(cid, "lead %d %s: the guard-cut normal is %.3g from the saved trees-off, beyond the "
                                    "run's tolerance %.3g" % (L, x.value, gap, tol))
            per[x.value] = {"max_abs_gap": gap, "tolerance": tol}
        if not per:
            raise ExportRefusal(cid, "lead %d: the saved surface holds no trees-off column to compare" % L)
        rec = {"links": per, "rows": surf.n, "result": "pass"}
    p[cid] = rec
    # ---- the test rows: P6, P9, P12 legal
    test_rows = b.roles[LY.ROLE_TEST]
    do_test = LY.ROLE_TEST in roles
    files = LeadFiles(state, b, mine_tree, ctx_cols, roles)
    if do_test:
        trees_off_pre = {x.value: M.PRE_PREFIX + LA.arm_name(LA.trees_off_of(x)) for x in state.links}
        saved = _read_saved(lead_run / "test_preds.parquet", TEST_KEY_COLUMNS + ([DONOR_MEDIAN_COLUMN] if neighbour
                                                                                 else list(trees_off_pre.values())))
        if "y" in saved.columns:
            raise ExportRefusal("2.6", "internal: a test label column was read")
        p["P6"], b.test_order = check_test_rows(test_rows, saved, files.group_of(test_rows.keys), L)
        normal_saved = saved["normal"].to_numpy(dtype=np.float64)[b.test_order]
        if neighbour:
            med = float(b.records["normal_fit"]["donor_median"])
            want = clip_to_legal(np.full(test_rows.n, med), state.legal, False)[0]
            got = saved[DONOR_MEDIAN_COLUMN].to_numpy(dtype=np.float64)[b.test_order] \
                if DONOR_MEDIAN_COLUMN in saved.columns else None
            if not np.isnan(normal_saved).all() or got is None or not _same_bytes(want, got):
                raise ExportRefusal("P9", "lead %d: the saved normal is not NaN on every row, or the refit rows' "
                                    "median %r, clipped, is not the saved %s" % (L, med, DONOR_MEDIAN_COLUMN))
            p["P9"] = {"rule": "neighbour kind: saved normal NaN on both sides; refit-row median (clipped) equals the "
                               "saved %s byte for byte" % DONOR_MEDIAN_COLUMN, "donor_median": med, "result": "pass"}
        else:
            nfit = b.normal_fit(test_rows.units, test_rows.times)
            mine = np.asarray(nfit[Link.IDENTITY.value], dtype=np.float64)
            if not _same_bytes(mine, normal_saved):
                gap = float(np.nanmax(np.abs(mine - normal_saved))) if mine.size else 0.0
                raise ExportRefusal("P9", "lead %d: the identity fit-cut normal on the test rows is not the saved "
                                    "normal byte for byte (largest gap %.3g)" % (L, gap))
            # every link: link_forward(the saved trees-off) vs the exported fit-cut normal, within the run's own
            # tolerance (decision_checks R36), as P10 / P11 do on the surface rows; a link the run saved no
            # trees-off column for is recorded as not checkable, never skipped silently
            tol_t = (_read_json(run / "decision_checks.json").get("tolerances") or {}).get("tolerance") or {}
            per_link: Dict[str, Any] = {}
            for x in state.links:
                col = trees_off_pre[x.value]
                if col not in saved.columns:
                    per_link[x.value] = {"result": "not checkable: the run saved no %s on the test rows" % col}
                    continue
                cc, uu = PR.link_arg(x, b.c, state.ub)
                z = link_forward(saved[col].to_numpy(dtype=np.float64)[b.test_order], x, cc, uu)
                got = np.asarray(nfit[x.value], dtype=np.float64)
                gap = float(np.max(np.abs(got - z))) if test_rows.n else 0.0
                tol = float(tol_t[x.value])
                if not gap <= tol:
                    raise ExportRefusal("P9", "lead %d %s: the fit-cut normal on the test rows is %.3g from the saved "
                                        "trees-off, beyond the run's tolerance %.3g" % (L, x.value, gap, tol))
                per_link[x.value] = {"max_abs_gap": gap, "tolerance": tol, "result": "pass"}
            p["P9"] = {"rows": test_rows.n, "identity_byte_equal": True, "links": per_link, "result": "pass"}
        lo, hi = state.legal
        smin, smax = np.unique(saved["legal_min"].to_numpy(dtype=np.float64)), \
            np.unique(saved["legal_max"].to_numpy(dtype=np.float64))
        if smin.size != 1 or smax.size != 1 or float(smin[0]) != float(lo) or float(smax[0]) != float(hi):
            raise ExportRefusal("P12", "lead %d: the legal range %s differs from the saved legal_min/legal_max %s / %s"
                                % (L, (lo, hi), smin.tolist(), smax.tolist()))
        p["P12"]["legal_range"] = "equal"
    else:
        p["P6"] = "skipped: dry pass (no test role)"
        p["P9"] = "skipped: dry pass (no test role)"
        p["P12"]["legal_range"] = "skipped: dry pass (no test role)"
    # ---- the files, group by group (P13 per fit set)
    p13: Dict[str, Any] = {}
    fit_sets = [r for r in (LY.ROLE_REFIT, LY.ROLE_TUNE, LY.ROLE_GUARDFIT) if r in b.donors and r in files.write_roles]
    k = len(hist_cols)
    sizes = {}
    for gi, g in enumerate(groups):
        tb, sb, n_tr, n_sd, arrays = files.train(g)
        if tb is not None:
            writer.put("%s/%s.parquet" % (LY.TRAIN_DIR, LY.group_file_stem(g)), tb, n_tr, LY.TRAIN_DIR, g)
            sizes[g] = n_tr
            for role in fit_sets:
                donor = b.donors[role]
                idx = np.flatnonzero(np.asarray(donor.group_of_row, dtype=object) == g)
                if not idx.size:
                    continue
                at = np.searchsorted(arrays["pos"], np.asarray(donor.grid_rows)[idx])
                X0 = np.array(arrays["X"][at], dtype=np.float32, copy=True)
                if role != LY.ROLE_REFIT and k:
                    side_at = np.searchsorted(np.flatnonzero(arrays["side"]), at)
                    X0[:, -k:] = arrays["H"][side_at]
                X0[np.isnan(X0)] = 0.0
                if not _same_bytes(X0, np.asarray(donor.X[idx], dtype=np.float32)):
                    raise ExportRefusal("P13", "lead %d group %s: the 0-filled %s features are not the engine's "
                                        "DonorRows.X" % (L, g, role))
                p13.setdefault(role, 0)
                p13[role] += int(idx.size)
        if sb is not None:
            writer.put("%s/%s.parquet" % (LY.GUARDSIDE_DIR, LY.group_file_stem(g)), sb, n_sd, LY.GUARDSIDE_DIR, g)
        if do_test:
            eb, n_te = files.test(g)
            if eb is not None:
                writer.put("%s/%s.parquet" % (LY.TEST_DIR, LY.group_file_stem(g)), eb, n_te, LY.TEST_DIR, g)
        state.p.status.beat("export", "lead %d: group %d of %d" % (L, gi + 1, len(groups)), done=gi + 1,
                            total=len(groups))
    for role in fit_sets:
        if p13.get(role, 0) != b.roles[role].n:
            raise ExportRefusal("P13", "lead %d: %d of the %d %s rows were compared" % (L, p13.get(role, 0),
                                                                                       b.roles[role].n, role))
    p["P13"] = {"rows_compared": p13, "result": "pass"} if fit_sets else         "skipped: the roles %s write no fit set" % list(roles)
    ucols, strata = _units_columns(state, pipe)
    writer.put(LY.UNITS_FILE, table_bytes(ucols), len(state.bank_units), "units", "_all")
    # ---- P14 determinism: the smallest group's train file built again
    part = LY.TRAIN_DIR if sizes else LY.TEST_DIR
    pool = {f["group"]: f["rows"] for f in writer.files if f["part"] == part}
    if not pool:
        raise ExportRefusal("P14", "lead %d: no train or test file was written" % L)
    g = min(sorted(pool), key=lambda x: pool[x])
    again = files.train(g)[0] if part == LY.TRAIN_DIR else files.test(g)[0]
    entry = [f for f in writer.files if f["part"] == part and f["group"] == g][0]
    if LY.sha256_bytes(again) != entry["sha256"] or LY.sha256_file(lead_dir / entry["path"]) != entry["sha256"]:
        raise ExportRefusal("P14", "lead %d group %s: a second build of its %s file gives other bytes" % (L, g, part))
    p["P14"] = {"group": g, "part": part, "rows": pool[g], "sha256": entry["sha256"], "result": "pass"}
    # ---- P15 the engine's own bank fit on the exported fit sets reproduces the run's bank fingerprints
    if common.get("need_p15"):
        t15 = time.time()
        p["P15"] = check_banks(b, run, L, int(pipe.trees_per_group), log)
        common["timings"]["lead_%d_p15" % L] = round(time.time() - t15, 2)
    else:
        p["P15"] = {"result": "not run: no accepted engine difference and no --p15 (the external smoke-size proof "
                              "is pt/integ/parity_p15.py)"}
    # ---- every P id is recorded at every lead: a check that belongs to the other kind of lead is the same check
    # under its own id there (lead 0: P2/P4/P10; a forecast lead: P3/P5/P11)
    twins = (("P2", "P3", "the guard-cut fit set"), ("P4", "P5", "the score surface"),
             ("P10", "P11", "the guard-cut normal on the score surface"))
    for zero_id, lead_id, what in twins:
        have, other = (zero_id, lead_id) if L == 0 else (lead_id, zero_id)
        res = p[have].get("result") if isinstance(p[have], dict) else str(p[have])
        p[other] = {"result": "%s (as %s: at %s %s is checked as %s)" % (res, have, "lead 0" if L == 0 else
                                                                       "a forecast lead", what, have),
                    "same_as": have}
    missing_ids = [c for c in P_IDS if c not in p]
    if missing_ids:
        raise ExportRefusal("2.7", "internal: the parity record lacks %s" % missing_ids)
    accepted = common.get("accepted")
    if accepted is not None:
        # an accepted engine difference holds only if EVERY parity check passed (not printed, skipped or not run),
        # at every level of its record (Z check 2: e.g. a P9 link marked 'not checkable' is not a pass)
        not_pass = {c: [r for r in parity_results(p[c]) if not str(r).lower().startswith("pass")] for c in P_IDS}
        not_pass = {c: r for c, r in not_pass.items() if r}
        if not_pass:
            raise ExportRefusal("ACCEPT", "lead %d: the accepted engine difference of run id %s (ruling %s) needs every "
                                "parity check P1-P15 to pass; these did not: %s"
                                % (L, accepted["run_id"], accepted["ruling"], not_pass),
                                fix="export with every role; if a check cannot pass, ask the owner")
    # ---- the manifest (last)
    refit_y = b.roles[LY.ROLE_REFIT].y
    lo, hi = state.legal
    from treeroute.runs.fingerprint import engine_code_hash

    doc = {
        "format": LY.FORMAT_EXPORT, "written_utc": LY.utc_now(), "export_key": key,
        "run": {"folder": str(run).replace("\\", "/"), "name": run.name, "fingerprint": manifest["fingerprint"],
                "kind": manifest["config"]["kind"]},
        "package": {"folder": str(common["package"]).replace("\\", "/"), "name": common["package_name"],
                    "fingerprint": common["pkg"].fingerprint},
        "engine": dict(common["engine"], live_stripped_now=engine_code_hash(),
                       accepted_difference=acceptance_record(accepted, common["engine"], common["ident"])),
        "derived_sha256": pipe.derived_sha, "router_kind": state.kind,
        "lead": L, "leads_of_run": list(run_leads(run)), "roles": list(roles),
        "links": [x.value for x in state.links], "c": b.c, "ub": state.ub,
        "legal_range": [lo if np.isfinite(lo) else None, hi if np.isfinite(hi) else None],
        "legal_range_text": [repr(float(lo)), repr(float(hi))],
        "cuts": b.cuts, "season": _season(state.derived["R2"].value),
        "columns": {"tree": mine_tree, "history": hist_cols, "context": ctx_cols,
                    "x": [LY.x_col(x) for x in mine_tree], "c": [LY.c_col(x) for x in ctx_cols],
                    "h": [LY.h_col(x) for x in hist_cols], "nfit": [LY.nfit_col(x.value) for x in state.links],
                    "ngd": [LY.ngd_col(x.value) for x in state.links]},
        "counts": {r: b.roles[r].n for r in b.roles},
        "row_key_hashes": {r: _rkh(b.roles[r]) for r in b.roles},
        "records": _clean(b.records),
        "parity": _clean(p), "identity": common["ident"],
        "zero_share_refit_y": float(np.mean(refit_y == 0.0)) if refit_y.size else None,
        "legal_min": lo if np.isfinite(lo) else None,
        "groups": groups, "seen_during_design_groups": sorted(set(str(x) for x in (pipe.pkg.split.seen_during_design
                                                                                    or ())) & set(groups)),
        "strata_columns": strata,
        "files": sorted(writer.files, key=lambda f: f["path"]),
        "files_written": writer.written, "files_skipped_resume": writer.skipped,
        "export_code_sha256": code_sha(),
        "launch": common["launch_record"] if common["launch_record"] is not None
        else "not pinned by treeroute.launch (test call)",
        # owner ruling AA4: which engine guard steps were taken from the run's record (no exported value changes)
        "lean_export": common.get("lean"),
        "timings_seconds": dict(common["timings"], lead_files=round(time.time() - t0, 2),
                                total=round(time.time() - common["t_start"], 2)),
        "peak_rss_bytes": _peak_rss()}
    LY.write_json_atomic(lead_dir / LY.EXPORT_MANIFEST, _clean(doc), writer.registry)
    log("lead %d: P1-P14 pass; P15 %s%s; %d files written, %d kept from a resumed run; manifest %s"
        % (L, "pass" if common.get("need_p15") else "not run",
           "" if accepted is None else " (accepted engine difference, ruling %s: every check passed)" % accepted["ruling"],
           writer.written, writer.skipped, lead_dir / LY.EXPORT_MANIFEST))
    return lead_dir


def _season(spec: Any) -> Dict[str, Any]:
    """R2's season key as plain fields (its kind and steps per year)."""
    kind = getattr(spec, "kind", None)
    return {"kind": getattr(kind, "value", kind), "steps_per_year": getattr(spec, "steps_per_year", None)}


def _rkh(rows: RoleRows) -> str:
    """The row-key hash of a role's rows in grid order (labels.vault.row_key_hash)."""
    from treeroute.labels.vault import row_key_hash

    return row_key_hash(rows.units, rows.times)


# ---------------------------------------------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None) -> int:
    """The export command (SPEC_RIVALS.md 2.1). Its first act is the engine's thread pins
    (treeroute.launch.pin_threads), so it must run before numpy is imported in this process."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "export":
        args = args[1:]
    ap = argparse.ArgumentParser(prog="rivals export", description="export one finished run for the rivals")
    ap.add_argument("--run")
    ap.add_argument("--package")
    ap.add_argument("--lead")
    ap.add_argument("--roles")
    ap.add_argument("--config")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--p15", action="store_true",
                    help="also run P15 (the bank-fingerprint check); always on for a run with an accepted difference")
    ap.add_argument("--full-engine-checks", action="store_true",
                    help="run every engine guard step again (no lean export, owner ruling AA4); the exported files "
                         "are the same bytes")
    ap.add_argument("--write-lineage", action="store_true")
    ap.add_argument("--proof", action="append", default=[])
    ns = ap.parse_args(args)
    roots = LY.as_roots(ns.config)
    LY.import_engine(roots.engine_root)
    from treeroute import launch

    record = launch.pin_threads()
    try:
        if ns.write_lineage:
            write_lineage(roots, ns.proof)
            return 0
        if not ns.run or ns.lead is None:
            ap.error("--run and --lead are required")
        export_run(ns.run, ns.package, ns.lead, ns.roles, roots, resume=ns.resume, launch_record=record,
                   p15=True if ns.p15 else None, lean=not ns.full_engine_checks)
        return 0
    except (ExportRefusal, LY.LayoutRefusal) as exc:
        print(str(exc), file=sys.stderr, flush=True)
        return 2
    except Exception as exc:
        from treeroute.errors import RefusedError

        if isinstance(exc, RefusedError):              # an engine refusal: its own message, no traceback
            print("export refused by the engine: %s" % exc, file=sys.stderr, flush=True)
            return 2
        raise


__all__ = ["ExportRefusal", "export_run", "main", "write_lineage", "check_engine", "parse_proof", "code_sha",
           "table_bytes", "rebuilt_config", "accepted_differences", "acceptance_for", "check_banks",
           "run_bank_records", "LeanEngine", "LEAN_STEPS"]


if __name__ == "__main__":
    raise SystemExit(main())
