"""Install the coral build (owner rulings U, V) into LIVE by explicit file list.

Usage (from anywhere):  py -3.9 D:/treeroute/coral_build/tools/install_into_live.py --expect-build <sha> [--apply]
Without --apply it only prints the plan. With --apply it:
  1. checks: no engine or pytest process; LIVE hash is the old one; the build hash is --expect-build; the last no-op
     proof summary says RESULT: PASS and names the same build hash;
  2. moves every LIVE file that the build changes to LIVE/_moved_coral_<stamp>/<same relative path> (move, never delete);
  3. copies every changed and new build file into LIVE, file by file (no recursive copy);
  4. checks that LIVE's engine_code_sha256 equals the build's and that LIVE's treeroute .py file set equals the build's;
  5. writes LIVE/_moved_coral_<stamp>/INSTALL_MANIFEST.json (files, sha256 before/after, hashes).
Scope: treeroute/**/*.py, treeroute_report/**/*.py, tests/*.py (no __pycache__, no _pytest_tmp, no _proposed changes
expected). A LIVE file that the build lacks is reported, never removed.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

LIVE = Path(r"C:\Users\<user>\Desktop\data set for reserch paper\engine")
BUILD = Path(r"D:\treeroute\coral_build\engine")
OLD_LIVE_HASH = "65a177bc7cdd47bacca806582bd13be52706ba3da385bb468fe1f0f24b81a0ff"
PROOF_SUMMARY = Path(r"D:\treeroute\coral_build\noop\noop_summary.txt")
SKIP_PARTS = {"__pycache__", "_pytest_tmp", "_pytest_fix"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def files(root: Path):
    out = {}
    for sub, pattern in (("treeroute", "**/*.py"), ("treeroute_report", "**/*.py"), ("tests", "*.py")):
        base = root / sub
        for p in base.glob(pattern):
            rel = p.relative_to(root)
            if SKIP_PARTS & set(rel.parts):
                continue
            out[rel.as_posix()] = p
    return out


def engine_hash(root: Path) -> str:
    code = "from treeroute.runs.fingerprint import engine_code_sha256; print(engine_code_sha256())"
    r = subprocess.run([sys.executable, "-c", code], cwd=str(root), capture_output=True, text=True, check=True)
    return r.stdout.strip()


def busy() -> str:
    # the query's own powershell holds both patterns in its command line, so lines holding 'Get-CimInstance' are skipped
    ps = ("Get-CimInstance Win32_Process | Where-Object { ($_.CommandLine -match 'treeroute (smoke|run|plan)' "
          "-or $_.CommandLine -match '-m pytest') -and $_.CommandLine -notmatch 'Get-CimInstance' } | "
          "ForEach-Object { $_.ProcessId }")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    return r.stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect-build", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--build", default=str(BUILD), help="the build engine folder to install from")
    ap.add_argument("--old-live", default=OLD_LIVE_HASH, help="the LIVE hash expected before the install")
    ap.add_argument("--proof", default=str(PROOF_SUMMARY), help="the no-op proof summary that must say PASS")
    a = ap.parse_args()
    build_root, proof_summary = Path(a.build), Path(a.proof)

    live_files, build_files = files(LIVE), files(build_root)
    changed = sorted(k for k in build_files if k in live_files and sha(build_files[k]) != sha(live_files[k]))
    new = sorted(k for k in build_files if k not in live_files)
    live_only = sorted(k for k in live_files if k not in build_files)
    print("changed: %d" % len(changed)); [print("  ~ " + k) for k in changed]
    print("new: %d" % len(new)); [print("  + " + k) for k in new]
    print("LIVE-only (kept, never removed): %d" % len(live_only)); [print("  = " + k) for k in live_only]

    live_hash, build_hash = engine_hash(LIVE), engine_hash(build_root)
    print("LIVE hash  %s" % live_hash)
    print("BUILD hash %s" % build_hash)
    problems = []
    if live_hash != a.old_live:
        problems.append("LIVE hash is not the old one: LIVE changed since the build copy was made")
    if build_hash != a.expect_build:
        problems.append("BUILD hash differs from --expect-build")
    summary = proof_summary.read_bytes().decode("utf-8", "replace") if proof_summary.is_file() else ""
    if "RESULT: PASS" not in summary or build_hash not in summary:
        problems.append("the no-op proof summary does not say RESULT: PASS for this build hash")
    if any(k.startswith("treeroute/_proposed/") for k in changed + new):
        problems.append("a _proposed file differs: not expected")
    b = busy()
    if b:
        problems.append("an engine or pytest process is running: %s" % b.replace("\n", ", "))
    for p in problems:
        print("PROBLEM: " + p)
    if problems:
        return 2
    if not a.apply:
        print("plan only (no --apply): nothing changed")
        return 0

    stamp = time.strftime("%Y%m%d_%H%M%S")
    moved_root = LIVE / ("_moved_coral_%s" % stamp)
    manifest = {"stamp": stamp, "live_hash_before": live_hash, "build_hash": build_hash, "changed": [], "new": []}
    for k in changed:
        src, dst = build_files[k], LIVE / k
        aside = moved_root / k
        aside.parent.mkdir(parents=True, exist_ok=True)
        before = sha(dst)
        shutil.move(str(dst), str(aside))
        shutil.copy2(str(src), str(dst))
        manifest["changed"].append({"file": k, "sha256_before": before, "sha256_after": sha(dst), "moved_to": str(aside)})
    for k in new:
        src, dst = build_files[k], LIVE / k
        if dst.exists():
            raise SystemExit("refusing: %s appeared during the install" % dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
        manifest["new"].append({"file": k, "sha256_after": sha(dst)})

    after = engine_hash(LIVE)
    manifest["live_hash_after"] = after
    live_tr = sorted(k for k in files(LIVE) if k.startswith("treeroute/"))
    build_tr = sorted(k for k in files(build_root) if k.startswith("treeroute/"))
    manifest["treeroute_file_sets_equal"] = live_tr == build_tr
    moved_root.mkdir(parents=True, exist_ok=True)
    (moved_root / "INSTALL_MANIFEST.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print("LIVE hash after install %s" % after)
    print("treeroute file sets equal: %s" % manifest["treeroute_file_sets_equal"])
    print("manifest: %s" % (moved_root / "INSTALL_MANIFEST.json"))
    if after != build_hash or not manifest["treeroute_file_sets_equal"]:
        print("INSTALL CHECK FAILED: restore from %s" % moved_root)
        return 1
    print("INSTALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
