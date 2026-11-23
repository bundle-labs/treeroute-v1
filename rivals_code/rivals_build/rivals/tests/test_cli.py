"""The command line in a fresh process (SPEC_RIVALS.md 2.1, 3.1, 3.10): the export pins the engine's threads itself, so
nothing may load numpy before it (treeroute/launch.py refuses then); the harness commands refuse with exit code 2.

The child gets this process's environment WITHOUT the variables the engine launcher refuses (launch.py
FOREIGN_ENV_PREFIXES: pytest's sklearnex import sets KMP_* here).
"""

import os
import subprocess
import sys

from rivals.tests import toy_runs as T


def _clean_env():
    from treeroute.launch import foreign_environment
    env = dict(os.environ)
    for name in foreign_environment(env):
        env.pop(name, None)
    return env


def _cli(*args, timeout=600):
    return subprocess.run([sys.executable, "-m", "rivals.cli"] + [str(a) for a in args], cwd=str(T.BUILD_ROOT),
                          env=_clean_env(), capture_output=True, text=True, timeout=timeout)


def test_cli_export_runs_in_a_fresh_process(grid_toy):
    root = grid_toy.base / "cli"
    cfg = T.write_rivals_yaml(root / "rivals.yaml", grid_toy.machine_file, root / "_export",
                              grid_toy.export_ckpt_root, root / "_out", root / "_moved")
    r = _cli("export", "--run", grid_toy.run, "--package", grid_toy.package, "--lead", "0", "--config", cfg)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    lead0 = root / "_export" / grid_toy.package_name / grid_toy.run_name / "lead_0"
    man = T.read_json(lead0 / "export_manifest.json")
    assert man["launch"] != "not pinned by treeroute.launch (test call)", "the CLI export did not pin threads"


def test_cli_harness_refuses_with_exit_code_2(table_toy, table_export):
    out_root = table_toy.base / "_out_cli"
    r = _cli("init", "--run", table_toy.run, "--export", table_export.dirs[0], "--out", out_root,
             "--config", table_toy.config)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    out = out_root / table_toy.package_name / table_toy.run_name
    assert (out / "board.json").is_file()
    r = _cli("lock", "--out", out, "--config", table_toy.config)          # nothing tuned yet
    assert r.returncode == 2, (r.returncode, r.stdout[-2000:], r.stderr[-2000:])
    assert "REFUSED" in r.stdout
    assert not (out / "picks.json").exists()
