"""Fingerprints (comment-stripped engine code hash) and the write-once manifest."""

import json

import pytest

from conftest import TREEROUTE_DIR
from treeroute.runs.atomic import AtomicWriteError
from treeroute.runs.fingerprint import (code_hash, engine_code_hash, engine_code_hashes,
                                        engine_module_files, run_fingerprint)
from treeroute.runs.manifest import build_manifest, write_manifest


def test_code_hash_ignores_comments_and_blank_lines_only():
    a = b"x = 1\n\ny = x + 2\n"
    b = b"# origin: somewhere\nx = 1  # a note\n\n\n\ny = x + 2\n"
    c = b"x = 1\ny = x + 3\n"
    assert code_hash(a) == code_hash(b)
    assert code_hash(a) != code_hash(c)


def test_engine_files_are_sorted_and_exclude_proposed():
    files = engine_module_files()
    rels = [p.relative_to(TREEROUTE_DIR).as_posix() for p in files]
    assert rels == sorted(rels)
    assert "engine_constants.py" in rels and "launch.py" in rels
    assert not any(r.startswith("_proposed/") for r in rels)


def test_engine_hash_is_stable():
    assert engine_code_hash() == engine_code_hash()
    assert list(engine_code_hashes()) == sorted(engine_code_hashes())


def test_run_fingerprint_follows_the_config():
    a = run_fingerprint({"package": "p", "derived": "h1"})
    assert a == run_fingerprint({"derived": "h1", "package": "p"})
    assert a != run_fingerprint({"package": "p", "derived": "h2"})
    assert len(a) == 64


def test_engine_fingerprint_changes_with_engine_code(tmp_path):
    root = tmp_path / "fake_engine"
    root.mkdir()
    (root / "mod.py").write_text("A = 1\n", encoding="utf-8")
    h1 = run_fingerprint({"k": 1}, root=root)
    (root / "mod.py").write_text("A = 1  # comment only\n", encoding="utf-8")
    assert run_fingerprint({"k": 1}, root=root) == h1
    (root / "mod.py").write_text("A = 2\n", encoding="utf-8")
    assert run_fingerprint({"k": 1}, root=root) != h1


FAKE_LAUNCH = {"python": "x", "env_pins": {}, "threadpools": [], "backend": {}, "workers": {}}


def test_manifest_has_the_plan_7_1_fields_and_is_written_once(tmp_path):
    m = build_manifest("f" * 64, "e" * 64, {"run_root": "/r"}, config={"a": 1},
                       launch_record=FAKE_LAUNCH, argv=["treeroute", "smoke", "pkg"])
    for key in ("engine_modules", "engine_code_hash", "engine_constants", "engine_constants_hash",
                "versions", "python", "launch", "gls_random_state", "package_fingerprint",
                "machine", "argv", "not_built_yet"):
        assert key in m, key
    assert m["gls_random_state"] == 0
    assert "feature_list" in m["not_built_yet"] and "config" not in m["not_built_yet"]
    json.dumps(m, allow_nan=False)
    path = write_manifest(tmp_path, m)
    with pytest.raises(AtomicWriteError):
        write_manifest(tmp_path, m)
    assert json.loads(path.read_text(encoding="utf-8"))["fingerprint"] == "f" * 64


def test_manifest_refuses_while_proposed_code_is_loaded(monkeypatch):
    import sys
    import types

    from treeroute.errors import RefusedError
    from treeroute.runs.fingerprint import loaded_proposed_modules

    assert loaded_proposed_modules() == []
    monkeypatch.setitem(sys.modules, "treeroute._proposed.fake_probe",
                        types.ModuleType("treeroute._proposed.fake_probe"))
    with pytest.raises(RefusedError) as info:
        build_manifest("f" * 64, "e" * 64, {}, launch_record=FAKE_LAUNCH)
    assert "G-FINGERPRINT" in str(info.value) and "fake_probe" in str(info.value)


def test_manifest_refuses_without_a_launch_record():
    from treeroute import launch
    from treeroute.errors import LaunchError

    if launch._STATE["record"] is not None:
        pytest.skip("this process was launched")
    with pytest.raises(LaunchError):
        build_manifest("f" * 64, "e" * 64, {})
