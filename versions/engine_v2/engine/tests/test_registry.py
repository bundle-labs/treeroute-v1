"""G-NOOVERWRITE: any output path under a protected (shipped) root is refused."""

import json
import os

import pytest

from conftest import make_registry
from treeroute.errors import RegistryError, RegistryRefusal
from treeroute.runs.registry import Registry
from treeroute.runs.resume import open_run

FP = "ab" * 32


@pytest.fixture
def reg(tmp_path):
    a = tmp_path / "shipped_a"
    b = tmp_path / "deep" / "shipped_b"
    a.mkdir()
    b.mkdir(parents=True)
    folder = make_registry(tmp_path, [a, b])
    extra = tmp_path / "listed_only_in_json"
    shipped = {"roots": [str(extra)],
               "files": [{"path": str(tmp_path / "loose" / "result.csv"), "sha256": "0" * 64}]}
    (folder / "shipped.json").write_text(json.dumps(shipped), encoding="utf-8")
    return Registry(folder), tmp_path


def test_paths_under_protected_roots_are_refused(reg):
    registry, tmp = reg
    for path in (tmp / "shipped_a", tmp / "shipped_a" / "new" / "x.json",
                 tmp / "deep" / "shipped_b" / "run", tmp / "listed_only_in_json" / "y",
                 tmp / "free" / ".." / "shipped_a" / "z"):
        with pytest.raises(RegistryRefusal) as info:
            registry.assert_writable(path)
        assert "G-NOOVERWRITE" in str(info.value)


def test_case_variants_are_refused_on_windows(reg):
    registry, tmp = reg
    if os.name != "nt":
        pytest.skip("case-insensitive paths are a Windows property")
    with pytest.raises(RegistryRefusal):
        registry.assert_writable(str(tmp / "SHIPPED_A" / "x").upper())


def test_listed_shipped_file_and_registry_files_are_refused(reg):
    registry, tmp = reg
    with pytest.raises(RegistryRefusal):
        registry.assert_writable(tmp / "loose" / "result.csv")
    with pytest.raises(RegistryRefusal):
        registry.assert_writable(tmp / "registry" / "protected_roots.txt")
    with pytest.raises(RegistryRefusal):
        registry.assert_writable(tmp / "registry" / "shipped.json")


def test_paths_outside_are_allowed(reg):
    registry, tmp = reg
    assert registry.assert_writable(tmp / "runs" / "pkg")
    assert registry.assert_writable(tmp / "shipped_a_sibling" / "x")  # a prefix is not a parent
    assert registry.assert_writable(tmp / "loose" / "other.csv")


def test_missing_or_empty_registry_refuses_everything(tmp_path):
    with pytest.raises(RegistryError):
        Registry(tmp_path / "nowhere")
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "protected_roots.txt").write_text("# nothing\n\n", encoding="utf-8")
    with pytest.raises(RegistryError):
        Registry(empty)


def test_open_run_refuses_a_protected_run_root(reg):
    registry, tmp = reg
    with pytest.raises(RegistryRefusal):
        open_run(tmp / "shipped_a", "pkg", "smoke", FP, registry)
    assert not (tmp / "shipped_a" / "pkg").exists()


BS = "\\"
LONG = BS * 2 + "?" + BS  # the Windows extended-length prefix
windows_only = pytest.mark.skipif(os.name != "nt", reason="Windows path spellings")


@windows_only
def test_extended_length_and_device_spellings_are_refused(reg):
    registry, tmp = reg
    target = str(tmp / "shipped_a" / "x")
    for spelling in (LONG + target, LONG + target.lower(), "//?/" + target.replace(BS, "/"),
                     BS * 2 + "." + BS + target,
                     LONG + str(tmp / "free" / ".." / "shipped_a" / "y")):
        with pytest.raises(RegistryRefusal) as info:
            registry.assert_writable(spelling)
        assert "G-NOOVERWRITE" in str(info.value), spelling


@windows_only
def test_unc_and_admin_share_spellings_are_refused(reg):
    registry, tmp = reg
    drive, rest = os.path.splitdrive(str(tmp / "shipped_a" / "x"))
    share = BS * 2 + "localhost" + BS + drive[0] + "$" + rest
    for spelling in (share, LONG + "UNC" + BS + share[2:], share.replace(BS, "/"),
                     # a UNC path to a folder that is NOT protected is refused too: it cannot be
                     # compared with the registry reliably
                     BS * 2 + "localhost" + BS + drive[0] + "$" + os.path.splitdrive(
                         str(tmp / "runs"))[1]):
        with pytest.raises(RegistryRefusal) as info:
            registry.assert_writable(spelling)
        assert "G-NOOVERWRITE" in str(info.value), spelling


@windows_only
def test_trailing_dots_and_spaces_are_refused(reg):
    registry, tmp = reg
    for spelling in (str(tmp / "shipped_a") + "." + BS + "x", str(tmp / "shipped_a") + ". " + BS + "x",
                     str(tmp / "shipped_a") + " " + BS + "x", str(tmp / "free") + BS + "..." + BS + "x"):
        with pytest.raises(RegistryRefusal):
            registry.assert_writable(spelling)


@windows_only
def test_alias_missed_by_path_resolution_is_caught_by_file_identity(reg, monkeypatch):
    """A junction into a protected root is refused even if realpath did not resolve it (as with a
    subst drive): the volume serial and file index of an existing ancestor match the root."""
    import _winapi

    registry, tmp = reg
    alias = tmp / "alias_of_shipped_a"
    _winapi.CreateJunction(str(tmp / "shipped_a"), str(alias))
    try:
        from treeroute.runs import registry as R

        monkeypatch.setattr(R.os.path, "realpath", lambda p, *a, **k: p)
        with pytest.raises(RegistryRefusal) as info:
            registry.assert_writable(alias / "new_run")
        assert "file index" in str(info.value)
        monkeypatch.undo()
        with pytest.raises(RegistryRefusal):  # and the normal resolution catches it by name
            registry.assert_writable(alias / "new_run")
    finally:
        os.rmdir(str(alias))  # removes the junction only (test scratch)


def test_registry_folder_is_protected_except_engine_written_files(reg):
    registry, tmp = reg
    folder = tmp / "registry"
    backup = folder / "backup_x"
    backup.mkdir()
    (backup / "FINAL_TABLE.csv").write_text("a\n", encoding="utf-8")
    for path in (folder, folder / "zz_probe", backup, backup / "zz_probe",
                 backup / "FINAL_TABLE.csv", folder / "other.csv"):
        with pytest.raises(RegistryRefusal) as info:
            registry.assert_writable(path)
        assert "G-NOOVERWRITE" in str(info.value)
    for name in ("index.csv", "bands.csv"):
        assert registry.assert_writable(folder / name) == folder / name


def test_existing_file_with_several_hard_links_is_refused(reg):
    registry, tmp = reg
    (tmp / "free").mkdir()
    original = tmp / "free" / "a.csv"
    original.write_text("x\n", encoding="utf-8")
    assert registry.assert_writable(original)
    os.link(str(original), str(tmp / "free" / "b.csv"))
    with pytest.raises(RegistryRefusal) as info:
        registry.assert_writable(original)
    assert "hard links" in str(info.value)


def test_assert_writable_returns_the_resolved_path_and_open_run_creates_exactly_it(reg):
    registry, tmp = reg
    from treeroute.runs.registry import canonical

    raw = str(tmp / "free" / ".." / "runs2")
    assert registry.assert_writable(raw) == tmp / "runs2"
    handle = open_run(raw, "pkg", "smoke", FP, registry)
    assert handle.path.parent == tmp / "runs2" / "pkg" / "smoke"
    assert handle.path.is_dir() and str(handle.path) == canonical(handle.path)
    assert not (tmp / "free").exists()


@windows_only
def test_open_run_with_a_long_prefix_or_case_variant_creates_the_checked_path(reg):
    registry, tmp = reg
    a = open_run(LONG + str(tmp / "runs3"), "pkg", "smoke", FP, registry)
    assert a.path.parent == tmp / "runs3" / "pkg" / "smoke" and a.path.is_dir()
    # the existing part of an upper-cased spelling comes back in its real case
    b = open_run(str(tmp).upper() + BS + "runs4", "pkg", "headline", FP, registry)
    assert str(b.path).startswith(str(tmp) + BS) and b.path.is_dir()


def _real_registry():
    from treeroute.runs.machine import load_machine

    machine = load_machine()
    roots_file = os.path.join(machine.registry_dir, "protected_roots.txt")
    if not os.path.isfile(roots_file):
        pytest.skip("no shipped registry on this machine (%s)" % roots_file)
    return machine, Registry(machine.registry_dir)


def test_real_registry_protects_every_listed_root():
    """Read-only check against the machine file's registry (skipped where it does not exist)."""
    machine, registry = _real_registry()
    assert registry.roots, "the real registry lists no roots"
    for root in registry.roots:
        probe = os.path.join(root, "treeroute_probe_never_written")
        with pytest.raises(RegistryRefusal):
            registry.assert_writable(probe)
        if os.name == "nt":
            with pytest.raises(RegistryRefusal):
                registry.assert_writable(LONG + os.path.abspath(probe))
    # the machine file's own run root must be writable
    assert registry.assert_writable(machine.run_root)


def test_real_registry_folder_and_its_backups_are_protected():
    machine, registry = _real_registry()
    folder = os.path.abspath(machine.registry_dir)
    with pytest.raises(RegistryRefusal):
        registry.assert_writable(folder)
    with pytest.raises(RegistryRefusal):
        registry.assert_writable(os.path.join(folder, "zz_probe"))
    backups = sorted(d for d in os.listdir(folder)
                     if d.startswith("backup") and os.path.isdir(os.path.join(folder, d)))
    for name in backups:
        backup = os.path.join(folder, name)
        with pytest.raises(RegistryRefusal):
            registry.assert_writable(os.path.join(backup, "zz_probe"))
        for entry in sorted(os.listdir(backup))[:5]:
            with pytest.raises(RegistryRefusal):
                registry.assert_writable(os.path.join(backup, entry))
    assert registry.assert_writable(os.path.join(folder, "index.csv"))
