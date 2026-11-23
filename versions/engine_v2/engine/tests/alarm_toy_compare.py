"""Shared helpers of the alarm pipeline tests (tests/test_pipeline_alarm.py, tests/test_table_mode_alarm.py); not a
test file. A toy runs through an engine copy in a child process (tests/alarm_toy_runner.py) and two run folders are
compared file by file (owner ruling AE: when the alarm switches nothing, every engine v1 output stays the same)."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import ENGINE_DIR, TESTS_DIR

V1_REF = ENGINE_DIR.parent / "engine_v1_ref"          # the frozen copy of the v1 engine (LIVE 930d961c)
V1_HASH = "930d961cdfdd219c36b113174e6c865096f973068e30696850f13d5ec4a60814"
RUNNER = TESTS_DIR / "alarm_toy_runner.py"
# files every engine change moves (times, the engine's identity) or that the alarm adds a key to (compared apart)
IDENTITY_OR_TIME = {"DONE.json", "guard_report.json", "manifest.json", "manifest_adoption.json", "run.json", "run.log",
                    "run_record.json", "status.json", "tables.json", "verdict.json"}
ALARM_PREFIXES = ("alarm_",)


def run_child(engine, pkg, base, registry, mode="normal", switch_all=False, spy=None, timeout=900, af2=None):
    """One toy run in a fresh interpreter with python -B (no __pycache__ is written into the engine copy); returns
    the RESULT record (run folder, imported engine, engine_code_sha256)."""
    cmd = [sys.executable, "-B", str(RUNNER), "--engine", str(engine), "--pkg", str(pkg), "--base", str(base),
           "--registry", str(registry), "--mode", mode]
    if switch_all:
        cmd.append("--alarm-switch-all")
    if spy is not None:
        cmd += ["--spy", str(spy)]
    if af2 is not None:
        cmd += ["--af2", str(af2)]
    Path(base).mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("KMP_", "PYTHONDONTWRITE"))}
    proc = subprocess.run(cmd, cwd=str(base), capture_output=True, text=True, timeout=timeout, env=env)
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT ")]
    assert proc.returncode == 0 and lines, proc.stdout[-3000:] + proc.stderr[-6000:]
    rec = json.loads(lines[-1][len("RESULT "):])
    rec["folder"] = Path(rec["folder"])
    return rec


def file_hashes(root):
    out = {}
    root = Path(root)
    for dp, _, fn in os.walk(str(root)):
        for f in fn:
            p = Path(dp) / f
            out[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _is_alarm(rel):
    """An alarm file: alarm_* files, and owner ruling G1's saved fit rows of the twin's own router pass (named after
    the pass, '<pass> alarm twin', only when the twin is routed)."""
    name = Path(rel).name
    return name.startswith(ALARM_PREFIXES) or (Path(rel).parent.name == "context_missing" and "_alarm_twin" in name)


def _expected_to_move(rel):
    name = Path(rel).name
    return (rel in IDENTITY_OR_TIME or name == "DONE" or name.endswith(".lock.json")
            or name.startswith("test_labels_opened_lead_"))


def compare_runs(v1_folder, v2_folder, allowed_extra=()):
    """(the v1 files that differ in v2, beyond the ones every engine change moves and the allowed extras; the v2-only
    files that are not alarm files; the v1 files missing in v2)."""
    a, b = file_hashes(v1_folder), file_hashes(v2_folder)
    differ = sorted(k for k in a if k in b and a[k] != b[k] and not _expected_to_move(k) and k not in allowed_extra)
    extra = sorted(k for k in set(b) - set(a) if not _is_alarm(k))
    missing = sorted(set(a) - set(b))
    return differ, extra, missing


def _drop(obj, keys):
    if isinstance(obj, dict):
        return {k: _drop(v, keys) for k, v in obj.items() if k not in keys}
    if isinstance(obj, list):
        return [_drop(v, keys) for v in obj]
    return obj


def json_without(path, keys):
    return _drop(json.loads(Path(path).read_text(encoding="utf-8")), set(keys))
