"""G-NOKNOB static doors: no environment reads outside the launcher; the machine file holds paths
only. (The package-file door is in test_schema.py / test_load.py; the CLI door in
test_cli_allowlist.py.)"""

import io
import os
import tokenize

import yaml

from conftest import ENGINE_DIR, TREEROUTE_DIR
from treeroute.package.schema import MachineFile
from treeroute.runs.machine import MACHINE_FILE, load_machine

ENV_NAMES = {"environ", "getenv", "putenv", "unsetenv", "environb"}
ALLOWED_ENV_FILES = {"launch.py"}  # the launcher sets the thread pins, and nothing else reads env


def test_only_the_launcher_touches_the_environment():
    offenders = []
    for path in sorted(TREEROUTE_DIR.rglob("*.py")):
        rel = path.relative_to(TREEROUTE_DIR)
        if "_proposed" in rel.parts or "__pycache__" in rel.parts:
            continue
        if rel.as_posix() in ALLOWED_ENV_FILES:
            continue
        source = path.read_text(encoding="utf-8")
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.NAME and tok.string in ENV_NAMES:
                offenders.append("%s:%d %s" % (rel.as_posix(), tok.start[0], tok.string))
    assert offenders == [], offenders


def test_machine_file_is_outside_the_engine_and_holds_paths_only():
    assert MACHINE_FILE == ENGINE_DIR / "config" / "machine.yaml"
    assert TREEROUTE_DIR not in MACHINE_FILE.parents
    raw = yaml.safe_load(MACHINE_FILE.read_text(encoding="utf-8"))
    assert set(raw) == set(MachineFile.model_fields)
    machine = load_machine()
    for key in raw:
        value = getattr(machine, key)
        assert isinstance(value, str) and os.path.isabs(value), (key, value)


def test_machine_file_refuses_a_thread_count(tmp_path):
    import pytest

    from treeroute.errors import PackageError

    bad = tmp_path / "machine.yaml"
    bad.write_text("run_root: /r\ntemp_dir: /t\nregistry_dir: /g\nthreads: 16\n", encoding="utf-8")
    with pytest.raises(PackageError) as info:
        load_machine(bad)
    assert "rule C14" in str(info.value)
    rel = tmp_path / "rel.yaml"
    rel.write_text("run_root: runs\ntemp_dir: /t\nregistry_dir: /g\n", encoding="utf-8")
    with pytest.raises(PackageError):
        load_machine(rel)
