"""T-H01 import guard (SPEC_HUMAN.txt 1.2): the tool imports the signed common package read-only, pinned by its code
hash; a wrong pin refuses; the import writes nothing under D:/treeroute/rivals_build; `-B` is respected."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from rivals_human.tests import hooks as HK


def test_the_pinned_sha_is_the_signed_harness_today():
    """The common harness code on disk has the hash the tool is pinned to: b6ea97b7 since the Part 608 fix (the signed
    Part 598 harness was 71457aa9; boards made under it are accepted only through ruling AG)."""
    assert HK.harness_sha_now() == HK.COMMON_SHA


def test_a_wrong_pin_refuses(tmp_path):
    cfg = HK.minimal_config(tmp_path, common_sha="0" * 64)
    C = HK.tool("common")
    HK.refuses(("pinned", "sha"), HK.need(C, "load", "A2"), str(cfg))


def test_the_right_pin_loads_the_common_package_from_the_common_build(tmp_path):
    cfg = HK.minimal_config(tmp_path)
    LY, H = HK.common_modules(cfg)
    assert Path(H.__file__).resolve().parent == (HK.COMMON_ROOT / "rivals").resolve()
    assert H.harness_code_sha() == HK.COMMON_SHA


def test_a_common_board_under_another_harness_refuses(tmp_path):
    """The common board's harness_code_sha256 must equal the pin (spec 1.2; H:1464) unless the config accepts that
    older harness in writing (ruling AG5: test_h01b)."""
    board_root = tmp_path / "_out_common"
    cfg = HK.minimal_config(tmp_path, common_board_root=board_root)
    LY, H = HK.common_modules(cfg)
    C = HK.tool("common")
    conf = HK.load_config(cfg)
    bp = board_root / "pkg" / "run1" / "board.json"
    HK.write_json(bp, {"harness_code_sha256": "f" * 64, "run": {"name": "run1"}})
    HK.refuses(("harness", "pinned"), HK.need(C, "check_common_board", "A2"), H, conf, "pkg", "run1", True)
    HK.write_json(bp, {"harness_code_sha256": HK.COMMON_SHA, "run": {"name": "run1"}})
    rec = C.check_common_board(H, conf, "pkg", "run1", True)
    assert rec["sha256"] == HK.sha256_file(bp)
    HK.refuses(("does not exist", "common board"), C.check_common_board, H, conf, "pkg", "other_run", True)


def _fresh_import(tmp_path: Path, cfg: Path, with_b: bool, pyc_prefix: Path) -> subprocess.CompletedProcess:
    """A fresh interpreter imports rivals_human.common and loads the common package (nothing imported before)."""
    code = ("import sys; sys.path.insert(0, %r)\n%s"
            "from rivals_human import common\n"
            "LY, H = common.load(%r)\n"
            "print('DWB', sys.dont_write_bytecode)\n"
            % (str(HK.HUMAN_ROOT), "" if with_b else "sys.dont_write_bytecode = False\n", str(cfg)))
    env = dict(os.environ)
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    env["PYTHONPYCACHEPREFIX"] = str(pyc_prefix)          # any byte-code write lands here, never in a source tree
    args = [sys.executable] + (["-B"] if with_b else []) + ["-c", code]
    return subprocess.run(args, cwd=str(tmp_path), env=env, capture_output=True, text=True, timeout=300)


def test_the_common_import_writes_nothing_under_the_common_build(tmp_path):
    """Snapshot of D:/treeroute/rivals_build/rivals before and after a fresh import (spec 1.2: dont_write_bytecode is
    set BEFORE the import). The interpreter starts WITHOUT -B and with dont_write_bytecode forced off; byte code is
    redirected to a prefix folder, which must then hold nothing from the common build."""
    cfg = HK.minimal_config(tmp_path)
    before = HK.snapshot(HK.COMMON_ROOT / "rivals")
    prefix = tmp_path / "pyc_prefix"
    res = _fresh_import(tmp_path, cfg, with_b=False, pyc_prefix=prefix)
    assert res.returncode == 0, res.stderr[-3000:]
    assert "DWB True" in res.stdout, "rivals_human.common did not set sys.dont_write_bytecode (spec 1.2)"
    after = HK.snapshot(HK.COMMON_ROOT / "rivals")
    assert before == after, "files under the common build changed: %s" % sorted(set(after) ^ set(before))[:5]
    written = [p for p in prefix.rglob("*.pyc")] if prefix.is_dir() else []
    common_tail = "/" + "/".join(HK.COMMON_ROOT.resolve().parts[1:]) + "/"      # e.g. /treeroute/rivals_build/
    from_common = [p for p in written if common_tail.lower() in p.as_posix().lower()]
    assert not from_common, "byte code of the common package was written: %s" % from_common[:3]


def test_minus_b_run_writes_no_byte_code_at_all(tmp_path):
    cfg = HK.minimal_config(tmp_path)
    prefix = tmp_path / "pyc_prefix_b"
    res = _fresh_import(tmp_path, cfg, with_b=True, pyc_prefix=prefix)
    assert res.returncode == 0, res.stderr[-3000:]
    assert not (prefix.is_dir() and any(prefix.rglob("*.pyc")))
