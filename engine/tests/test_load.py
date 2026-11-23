"""Package loader: closed folder, YAML strictness, sha256 includes, package fingerprint."""

import pytest

from conftest import make_package
from treeroute.errors import PackageError
from treeroute.package.load import load_package, load_yaml


def test_toy_package_loads(toy_package):
    pkg = load_package(toy_package)
    assert pkg.dataset.name == "toy_pkg"
    assert len(pkg.fingerprint) == 64
    assert list(pkg.stores) == ["../_stores/toy_store.yaml"]
    assert pkg.exceptions.entries == []  # an empty exceptions.yaml is allowed
    assert pkg.split.excluded == {"grp_z": "no coverage"}
    assert pkg.split.seen_during_design == ["grp_b"]
    assert pkg.catalog.columns["step_month"].calendar_part == "month"


def test_fingerprint_is_stable_and_tracks_package_files(toy_package):
    fp1 = load_package(toy_package).fingerprint
    assert load_package(toy_package).fingerprint == fp1
    ban = toy_package / "ban.yaml"
    ban.write_text(ban.read_text(encoding="utf-8") + "# edited\n", encoding="utf-8")
    assert load_package(toy_package).fingerprint != fp1


def test_fingerprint_covers_code_slots_but_not_data_or_acceptance_values(toy_package):
    fp1 = load_package(toy_package).fingerprint
    (toy_package / "data").mkdir()
    (toy_package / "data" / "part-0.parquet").write_bytes(b"not hashed here")
    (toy_package / "expected_derived.json").write_text("{}", encoding="utf-8")
    assert load_package(toy_package).fingerprint == fp1
    (toy_package / "features").mkdir()
    (toy_package / "features" / "build.py").write_text("x = 1\n", encoding="utf-8")
    assert load_package(toy_package).fingerprint != fp1


def test_include_hash_mismatch_is_refused(tmp_path):
    pkg = make_package(tmp_path, include_sha="0" * 64)
    with pytest.raises(PackageError) as info:
        load_package(pkg)
    assert "sha256" in str(info.value)


def test_changed_shared_catalog_is_refused(toy_package):
    store = toy_package.parent / "_stores" / "toy_store.yaml"
    store.write_text(store.read_text(encoding="utf-8") + "# drift\n", encoding="utf-8")
    with pytest.raises(PackageError):
        load_package(toy_package)


def test_unknown_top_level_entries_are_refused(toy_package):
    (toy_package / "recipe.yaml").write_text("trees: 500\n", encoding="utf-8")
    with pytest.raises(PackageError) as info:
        load_package(toy_package)
    assert "recipe.yaml" in str(info.value) and "G-NOKNOB" in str(info.value)


def test_unknown_folder_and_table_are_refused(toy_package):
    (toy_package / "presets").mkdir()
    with pytest.raises(PackageError):
        load_package(toy_package)
    (toy_package / "presets").rmdir()
    (toy_package / "tables").mkdir()
    (toy_package / "tables" / "weights.parquet").write_bytes(b"x")
    with pytest.raises(PackageError) as info:
        load_package(toy_package)
    assert "weights.parquet" in str(info.value)


def test_missing_required_file_is_refused(toy_package):
    (toy_package / "split.yaml").unlink()
    with pytest.raises(PackageError) as info:
        load_package(toy_package)
    assert "split.yaml" in str(info.value)


def test_empty_required_file_is_refused(toy_package):
    (toy_package / "ban.yaml").write_text("", encoding="utf-8")
    with pytest.raises(PackageError):
        load_package(toy_package)


def test_duplicate_yaml_keys_are_refused(tmp_path):
    path = tmp_path / "x.yaml"
    path.write_text("a: 1\nb: 2\na: 3\n", encoding="utf-8")
    with pytest.raises(PackageError) as info:
        load_yaml(path)
    assert "duplicate key" in str(info.value)


def test_yaml_dates_stay_strings_and_only_true_false_are_booleans(tmp_path):
    path = tmp_path / "x.yaml"
    path.write_text("d: 2001-02-03\nn: no\ny: yes\nt: true\n", encoding="utf-8")
    assert load_yaml(path) == {"d": "2001-02-03", "n": "no", "y": "yes", "t": True}


def test_yaml_numbers_are_plain_decimals_only(tmp_path):
    path = tmp_path / "x.yaml"
    path.write_text("a: 12:30\nb: 010\nc: 0x1F\nd: 0b101\ne: 1_000\nf: 190:20:30.15\n"
                    "g: 42\nh: -7\ni: 1e5\nj: 1.5e-3\nk: .inf\nl: -.inf\nm: 0.25\nn: 3.\n"
                    "o: +2\np: 0\n", encoding="utf-8")
    data = load_yaml(path)
    assert data["a"] == "12:30" and data["b"] == "010" and data["c"] == "0x1F"
    assert data["d"] == "0b101" and data["e"] == "1_000" and data["f"] == "190:20:30.15"
    assert data["g"] == 42 and data["h"] == -7 and data["o"] == 2 and data["p"] == 0
    assert isinstance(data["g"], int)
    assert data["i"] == 1e5 and isinstance(data["i"], float) and data["j"] == 1.5e-3
    assert data["k"] == float("inf") and data["l"] == float("-inf")
    assert data["m"] == 0.25 and data["n"] == 3.0


def test_yaml_nan_and_explicit_tags(tmp_path):
    import math

    path = tmp_path / "x.yaml"
    path.write_text("a: .nan\nb: !!int '12'\n", encoding="utf-8")
    data = load_yaml(path)
    assert math.isnan(data["a"]) and data["b"] == 12
    path.write_text("c: !!int 0x1F\n", encoding="utf-8")
    with pytest.raises(PackageError) as info:
        load_yaml(path)
    assert "plain decimal" in str(info.value)


def test_text_numbers_in_a_package_are_refused_through_the_loader(tmp_path):
    from conftest import STORE_CATALOG

    for old, new in (("length: 1, unit: month}\n    scope: unit", "length: '1', unit: month}\n"
                      "    scope: unit"),
                     ("fill_values: [-32768]", "fill_values: ['-32768']"),
                     ("legal_range: [0, .inf]", "legal_range: [.inf, 0]")):
        assert old in STORE_CATALOG
        pkg = make_package(tmp_path / old[:6].strip(":{ "), store_text=STORE_CATALOG.replace(old, new))
        with pytest.raises(PackageError):
            load_package(pkg)


def test_audit_checklist_is_required(toy_package):
    (toy_package / "AUDIT_CHECKLIST.md").unlink()
    with pytest.raises(PackageError) as info:
        load_package(toy_package)
    assert "missing required file AUDIT_CHECKLIST.md" in str(info.value)


def test_knob_in_a_package_file_is_refused_through_the_loader(tmp_path):
    pkg = make_package(tmp_path, dataset_extra="leads: [1, 3]\n")
    with pytest.raises(PackageError) as info:
        load_package(pkg)
    assert "derived: see derived.json, rule R10" in str(info.value)
