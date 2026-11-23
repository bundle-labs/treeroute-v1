"""Byte identity of two finished run folders (INSTALL_AFTER_NDVI.md step b; owner ruling R1).

    py -3.9 D:/treeroute/engine_next/tools/compare_runs.py <old run folder> <new run folder> [--show-removed]

MUST MATCH (exit 1 otherwise), and none may be missing on one side:
  - every prediction and score file (every *.parquet and *.csv, at any depth: the nowcast and every forecast lead)
    and derived.json: SHA-256 of the bytes;
  - every other *.json at any depth (gls_weight_model.json, adoption*.json, test_pass_router.json, ladder.json,
    tables.json, decision_checks.json, contract_lead_0.json, manifest.json, status.json, ...): byte-identical after
    removing ONLY the fields that are times, pids, paths, engine/code hashes or fingerprints (strip() below). The
    rest of each record is serialised in its own key order and compared byte for byte.
    The engine's constants table (manifest.json "engine_constants") is the engine's identity: it is removed like the
    engine's code hashes, and its differences are printed constant by constant (added, removed, changed) for review.
Review only (listed, never a failure): every other file (run.log, the phases' DONE markers, ...).
Reads only.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

# the fields removed before a JSON record is compared, by kind (key names; each is listed with --show-removed)
TIME_KEYS = {"created_utc", "started_utc", "finished_utc", "updated_utc", "locked_at", "locked_at_epoch", "opened_at",
             "eta_seconds_estimate", "seconds", "timings"}
TIME_SUFFIXES = ("_utc", "_at", "_at_epoch", "_seconds")
PID_KEYS = {"pid", "pid_created_ms", "ppid"}
PATH_KEYS = {"argv", "temp_dir", "run_root", "registry_dir", "temp_root", "folder", "run_dir"}
ENGINE_KEYS = {"engine_code_hash", "engine_code_sha256", "engine_constants_hash", "engine_constants_sha256",
               "engine_modules", "loaded_engine_modules", "engine_hash", "code_hash"}
CONSTANTS_KEY = "engine_constants"          # the constants table: removed, and diffed id by id
FINGERPRINT_KEYS = {"fingerprint", "run_fingerprint"}
ISO_TIME = re.compile(r"^\d{4}-\d\d-\d\d[T ]\d\d:\d\d:\d\d")
ABS_PATH = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\|/)")


def kind_of(key, value):
    """Why a field is removed (times, pid, path, engine, fingerprint), or None when it is kept."""
    if key in TIME_KEYS or key.endswith(TIME_SUFFIXES):
        return "time"
    if key in PID_KEYS:
        return "pid"
    if key in PATH_KEYS:
        return "path"
    if key in ENGINE_KEYS or key == CONSTANTS_KEY:
        return "engine"
    if key in FINGERPRINT_KEYS:
        return "fingerprint"
    if isinstance(value, str) and ISO_TIME.match(value):
        return "time"
    if isinstance(value, str) and ABS_PATH.match(value):
        return "path"
    return None


def strip(obj, where="", removed=None):
    """obj without the removed fields; removed collects (json path, kind)."""
    removed = [] if removed is None else removed
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            kind = kind_of(str(k), v)
            if kind is not None:
                removed.append(("%s/%s" % (where, k), kind))
                continue
            out[k] = strip(v, "%s/%s" % (where, k), removed)
        return out
    if isinstance(obj, list):
        out = []
        for i, v in enumerate(obj):
            if isinstance(v, str) and (ISO_TIME.match(v) or ABS_PATH.match(v)):
                removed.append(("%s[%d]" % (where, i), "time" if ISO_TIME.match(v) else "path"))
                continue
            out.append(strip(v, "%s[%d]" % (where, i), removed))
        return out
    return obj


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=True)


def diff_fields(a, b, where="", out=None, limit=12):
    """Up to `limit` json paths where two stripped records differ (with both values, short)."""
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        if list(a) != list(b):
            only_a, only_b = [k for k in a if k not in b], [k for k in b if k not in a]
            if only_a or only_b:
                out.append("%s: keys only in old %s, only in new %s" % (where or "/", only_a[:6], only_b[:6]))
            else:
                out.append("%s: same keys in another order" % (where or "/"))
        for k in a:
            if k in b:
                diff_fields(a[k], b[k], "%s/%s" % (where, k), out, limit)
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append("%s: %d items in old, %d in new" % (where, len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            diff_fields(x, y, "%s[%d]" % (where, i), out, limit)
        return out
    if canonical(a) != canonical(b):
        out.append("%s: old %s | new %s" % (where, canonical(a)[:100], canonical(b)[:100]))
    return out


def constants_diff(a, b):
    """The engine constants tables (lists of {id, value, ...}) compared id by id."""
    def table(rows):
        return {str(r.get("id")): r for r in rows or [] if isinstance(r, dict)}
    ta, tb = table(a), table(b)
    lines = ["added %s = %s" % (k, canonical(tb[k].get("value"))) for k in tb if k not in ta]
    lines += ["removed %s (was %s)" % (k, canonical(ta[k].get("value"))) for k in ta if k not in tb]
    lines += ["changed %s: %s -> %s" % (k, canonical(ta[k]), canonical(tb[k])) for k in ta
              if k in tb and canonical(ta[k]) != canonical(tb[k])]
    return lines


def files(root):
    root = Path(root)
    return {p.relative_to(root).as_posix(): p for p in sorted(root.rglob("*")) if p.is_file()}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def byte_kind(rel):
    return rel.endswith((".parquet", ".csv")) or rel == "derived.json"


def load_json(p):
    try:
        return json.loads(p.read_text(encoding="utf-8")), None
    except (ValueError, UnicodeDecodeError) as exc:
        return None, str(exc)


def main(argv):
    show_removed = "--show-removed" in argv
    args = [a for a in argv if not a.startswith("--")]
    old, new = files(args[0]), files(args[1])
    bad, review, notes = [], [], []
    same_bytes = same_json = 0
    removed_kinds = {}
    for rel in sorted(set(old) | set(new)):
        a, b = old.get(rel), new.get(rel)
        must = byte_kind(rel) or rel.endswith(".json")
        if a is None or b is None:
            (bad if must else review).append("%s: %s" % (rel, "missing in new" if b is None else "missing in old"))
            continue
        if byte_kind(rel):
            if sha(a) == sha(b):
                same_bytes += 1
            else:
                bad.append("%s: bytes differ" % rel)
            continue
        if rel.endswith(".json"):
            ja, ea = load_json(a)
            jb, eb = load_json(b)
            if ea or eb:                                   # not JSON: compared as bytes
                if sha(a) != sha(b):
                    bad.append("%s: not readable as JSON (%s) and its bytes differ" % (rel, ea or eb))
                else:
                    same_json += 1
                continue
            ra, rb = [], []
            sa, sb = strip(ja, "", ra), strip(jb, "", rb)
            for path, kind in ra + rb:
                removed_kinds.setdefault(rel, set()).add("%s (%s)" % (path, kind))
            if isinstance(ja, dict) and isinstance(jb, dict) and CONSTANTS_KEY in ja and CONSTANTS_KEY in jb:
                for line in constants_diff(ja[CONSTANTS_KEY], jb[CONSTANTS_KEY]):
                    notes.append("%s engine constants: %s" % (rel, line))
            if canonical(sa) == canonical(sb):
                same_json += 1
            else:
                bad.append("%s: differs after removing times, pids, paths, engine hashes and fingerprints:\n      %s"
                           % (rel, "\n      ".join(diff_fields(sa, sb))))
            continue
        if sha(a) != sha(b):
            review.append("%s: differs" % rel)
    print("prediction and score files and derived.json byte-identical: %d" % same_bytes)
    print("other JSON records identical after removing times, pids, paths, engine hashes, fingerprints: %d" % same_json)
    print("MUST-MATCH FILES THAT DIFFER OR ARE MISSING (%d):" % len(bad))
    for line in bad:
        print("  " + line)
    print("engine identity (the constants table, removed above; for review) (%d):" % len(notes))
    for line in notes:
        print("  " + line)
    print("other files that differ (review; engine hash, fingerprint or times expected) (%d):" % len(review))
    for line in review:
        print("  " + line)
    if show_removed:
        print("fields removed before the JSON comparison:")
        for rel in sorted(removed_kinds):
            print("  %s: %s" % (rel, ", ".join(sorted(removed_kinds[rel]))))
    if not same_bytes:
        print("no prediction or score file was found: wrong folders?")
        return 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
