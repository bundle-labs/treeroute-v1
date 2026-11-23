"""Shared test fixtures.

pytest's temporary folders are anchored inside tests/_pytest_tmp (not the system temp folder), so a
test run writes nothing outside the engine repo. pytest clears that folder at the start of each run;
it holds only files the tests themselves created.
"""

import hashlib
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
ENGINE_DIR = TESTS_DIR.parent
TREEROUTE_DIR = ENGINE_DIR / "treeroute"
REPO_PARENT = ENGINE_DIR.parent  # the research folder holding the legacy scripts
BASETEMP = TESTS_DIR / "_pytest_tmp"

if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    if not config.option.basetemp:
        config.option.basetemp = str(BASETEMP)


def run_python(code, timeout=180):
    """Run ``code`` in a fresh interpreter (same Python as pytest) with cwd = engine repo."""
    return subprocess.run([sys.executable, "-c", textwrap.dedent(code)], cwd=str(ENGINE_DIR),
                          capture_output=True, text=True, timeout=timeout)


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


STORE_CATALOG = """\
store: toy_store
description: a generic synthetic store
columns:
  x1:
    dtype: float32
    units: "1"
    cadence: {kind: regular, length: 1, unit: month}
    scope: unit
    stamp: period_end
    window: {length: 1, unit: month, align: backward}
    legal_range: [0, .inf]
    fill_values: [-32768]
    content_epoch: 2000-01
  g1:
    dtype: float32
    units: "1"
    cadence: {kind: regular, length: 1, unit: month}
    scope: global
    stamp: period_centre
    window: {align: unknown, max_length: 3, unit: month}
    fact_status: assumed
    reviewed_by: owner
"""

CATALOG = """\
columns:
  unit_id: {role: key_unit}
  group_id: {role: key_group}
  step_year: {role: key_time, calendar_part: year}
  step_month: {role: key_time, calendar_part: month}
  y:
    role: target
    legal_range: [0, 1]
    legal_range_source: product user guide, valid range table
    window: {length: 16, unit: day, align: backward}
    stamp: period_start
  x1: {role: driver, co_measured_with_target: false, co_measured_evidence: Part 1}
  g1: {role: driver}
"""

BAN = """\
verdicts:
  x1: {verdict: keep, reason: reviewed, evidence: Part 1}
  g1: {verdict: keep_unreviewed, reason: "timing facts signed, not yet reviewed"}
"""

# Leave one region out (owner rulings D, E L7 b): split.yaml holds only exclusions and seen_during_design.
SPLIT = """\
excluded: {grp_z: no coverage}
seen_during_design: [grp_b]
"""


def make_package(root, dataset_extra="", store_text=STORE_CATALOG, include_sha=None):
    """Write a minimal valid package under ``root``/pkg with a shared store catalog under
    ``root``/_stores. Returns the package folder."""
    root = Path(root)
    stores = root / "_stores"
    stores.mkdir(parents=True, exist_ok=True)
    store_path = stores / "toy_store.yaml"
    store_path.write_text(store_text, encoding="utf-8")
    sha = include_sha or sha256_of(store_path)
    pkg = root / "pkg"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "dataset.yaml").write_text(
        "name: toy_pkg\n"
        "version: '0.1'\n"
        "owner: tester\n"
        "description: a synthetic package for the skeleton tests\n"
        "stores:\n"
        "  target: 'data/target/group={group}/year={year}/part-0.parquet'\n"
        "  static: 'data/static/part-0.parquet'\n"
        "  drivers: ['data/drivers/group={group}/year={year}/part-0.parquet']\n"
        "includes:\n"
        "  - {path: ../_stores/toy_store.yaml, sha256: %s}\n" % sha + dataset_extra,
        encoding="utf-8")
    (pkg / "catalog.yaml").write_text(CATALOG, encoding="utf-8")
    (pkg / "ban.yaml").write_text(BAN, encoding="utf-8")
    (pkg / "split.yaml").write_text(SPLIT, encoding="utf-8")
    (pkg / "exceptions.yaml").write_text("", encoding="utf-8")
    (pkg / "AUDIT_CHECKLIST.md").write_text("# Audit checklist\n\n- [ ] signed by: tester\n",
                                            encoding="utf-8")
    return pkg


@pytest.fixture
def toy_package(tmp_path):
    return make_package(tmp_path)


def make_registry(root, protected):
    """A fake registry folder listing ``protected`` roots (absolute paths)."""
    reg = Path(root) / "registry"
    reg.mkdir(parents=True, exist_ok=True)
    (reg / "protected_roots.txt").write_text(
        "# test registry\n" + "\n".join(str(p) for p in protected) + "\n", encoding="utf-8")
    return reg


@pytest.fixture
def fake_machine(tmp_path, monkeypatch):
    """A machine file under tmp_path with its own registry; the CLI is pointed at it."""
    protected = tmp_path / "shipped_root"
    protected.mkdir()
    reg = make_registry(tmp_path, [protected])
    runs = tmp_path / "runs"
    temp = tmp_path / "temp"
    temp.mkdir()
    machine = tmp_path / "machine.yaml"
    machine.write_text("run_root: %s\ntemp_dir: %s\nregistry_dir: %s\n"
                       % (runs.as_posix(), temp.as_posix(), reg.as_posix()), encoding="utf-8")
    from treeroute.runs import machine as M

    monkeypatch.setattr(M, "MACHINE_FILE", machine)
    return {"machine": machine, "protected": protected, "registry": reg, "runs": runs,
            "temp": temp}
