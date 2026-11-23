"""The 'check' command (plan 6.1) and the CHECK REPORT CONTRACT: exit codes, the --deep option (check only), the
report file and its keys, engine_code_sha256."""

import json
from pathlib import Path

import click
import pytest
import typer
from typer.testing import CliRunner

from planted import build as B
from planted import faults as F
from test_check_deep import six_group_package
from treeroute import cli
from treeroute.check import report as R
from treeroute.check.report import CONTRACT_KEYS, DEEP_CONTRACT_KEYS, GUARD_KEYS
from treeroute.package.load import load_package
from treeroute.runs.fingerprint import engine_code_sha256

runner = CliRunner()


def _report(runs, pkg, mode):
    loaded = load_package(pkg)
    path = Path(runs) / loaded.dataset.name / "check" / ("check_%s_%s.json" % (mode, loaded.fingerprint[:12]))
    assert path.is_file(), path
    return loaded, json.loads(path.read_text(encoding="utf-8")), path


@pytest.mark.parametrize("deep", [False, True], ids=["quick", "deep"])
def test_check_on_the_clean_package_is_green_and_writes_the_contract(tmp_path, fake_machine, deep):
    pkg = B.make_clean_package(tmp_path / "p")
    args = ["check", str(pkg), "--run-root", str(fake_machine["runs"])] + (["--deep"] if deep else [])
    result = runner.invoke(cli.app, args)
    assert result.exit_code == 0, result.output
    assert "check %s: green" % ("deep" if deep else "quick") in result.output
    loaded, doc, path = _report(fake_machine["runs"], pkg, "deep" if deep else "quick")
    assert set(doc) == set(DEEP_CONTRACT_KEYS if deep else CONTRACT_KEYS)    # exactly the agreed keys
    assert doc["package"] == loaded.dataset.name and doc["package_fingerprint"] == loaded.fingerprint
    assert doc["engine_code_sha256"] == engine_code_sha256()
    assert doc["mode"] == ("deep" if deep else "quick") and doc["green"] is True
    assert doc["guards"] and all(set(g) == set(GUARD_KEYS) for g in doc["guards"])
    assert {g["status"] for g in doc["guards"]} <= {"pass", "flag", "refuse"}
    assert len({g["id"] for g in doc["guards"]}) == len(doc["guards"])
    assert doc["started"] <= doc["finished"]
    details = json.loads(path.with_name(path.stem + "_details.json").read_text(encoding="utf-8"))
    assert [g["id"] for g in details["guards"]] == [g["id"] for g in doc["guards"]]
    if deep:
        ids = {g["id"] for g in doc["guards"]}
        assert {"G-CADENCE", "G-JOIN", "G-RANGE", "G-DERIVED (recompute)", "G-HIST (sample)"} <= ids
        # ruling M2: the report names the groups it checked, how they were chosen and the package's group count
        want = R.package_smoke_groups(loaded)
        assert doc["checked_groups"] == want == details["checked_groups"]
        assert want["groups"] == list(B.GROUPS) and want["selection"] == R.M2_SELECTION == "R21 smoke groups, ruling M2"
        assert (want["package_groups"], want["data_groups"], want["refused"]) == (3, 3, None)
        assert "ruling-M2 subset" in result.output and "checked groups: ruling-M2 subset" in result.output
        assert "deep groups (ruling M2)" in ids
    else:
        assert "checked_groups" not in details and "ruling-M2" not in result.output


def test_check_deep_checks_only_the_r21_smoke_groups_and_says_so(tmp_path, fake_machine):
    from treeroute import engine_constants as K

    pkg = six_group_package(tmp_path / "p")
    result = runner.invoke(cli.app, ["check", str(pkg), "--run-root", str(fake_machine["runs"]), "--deep"])
    assert result.exit_code == 0, result.output
    loaded, doc, path = _report(fake_machine["runs"], pkg, "deep")
    smoke = ["grp_b", "grp_c", "grp_d", "grp_e"][:int(K.SMOKE_GROUPS)]          # sorted, after the exclusion
    rec = doc["checked_groups"]
    assert rec["groups"] == smoke and rec["selection"] == R.M2_SELECTION and rec["rule"] == "R21"
    assert (rec["package_groups"], rec["data_groups"]) == (5, 6) and rec["refused"] is None
    assert rec["constants"] == {"C13.smoke_groups": K.SMOKE_GROUPS, "C15.min_groups": K.MIN_GROUPS}
    assert rec == R.package_smoke_groups(loaded)
    details = json.loads(path.with_name(path.stem + "_details.json").read_text(encoding="utf-8"))
    assert details["checked_groups"] == rec
    lines = result.output.splitlines()
    assert any(ln.startswith("check --deep: the ruling-M2 subset (owner ruling M2)") for ln in lines)   # the header
    head = [ln for ln in lines if ln.startswith("check --deep: ruling-M2 subset (R21 smoke groups, ruling M2;")]
    assert len(head) == 1 and head[0].endswith(": " + ", ".join(smoke)) and "of the package's 5 groups" in head[0]
    assert "check --deep: %d groups," % len(smoke) in result.output          # pass 1 reads only those
    line = [g for g in doc["guards"] if g["id"] == "deep groups (ruling M2)"][0]
    assert line["status"] == "pass" and "grp_f" not in line["message"]


def test_the_report_writer_refuses_a_deep_report_without_its_groups(tmp_path):
    from treeroute.check.deep import run_deep

    pkg = B.make_clean_package(tmp_path / "p")
    loaded = load_package(pkg)
    ctx = run_deep(pkg, echo=lambda _t: None, workers=1)
    with pytest.raises(ValueError, match="checked_groups"):
        R.write_report(tmp_path / "runs", loaded, "deep", ctx.results, "a", "b")
    with pytest.raises(ValueError, match="takes no checked_groups"):
        R.write_report(tmp_path / "runs", loaded, "quick", ctx.results, "a", "b", checked_groups=ctx.deep_selection)
    bad = dict(ctx.deep_selection, groups=list(reversed(ctx.deep_selection["groups"])))
    with pytest.raises(ValueError, match="sorted list"):
        R.write_report(tmp_path / "runs", loaded, "deep", ctx.results, "a", "b", checked_groups=bad)
    short = {k: v for k, v in ctx.deep_selection.items() if k != "refused"}
    with pytest.raises(ValueError, match="exactly the keys"):
        R.write_report(tmp_path / "runs", loaded, "deep", ctx.results, "a", "b", checked_groups=short)
    assert not (tmp_path / "runs").exists()


def test_a_refusal_exits_4_naming_rule_columns_and_fix(tmp_path, fake_machine):
    pkg = B.make_clean_package(tmp_path / "p")
    F.pf_keys_month_tree(pkg)
    result = runner.invoke(cli.app, ["check", str(pkg), "--run-root", str(fake_machine["runs"])])
    assert result.exit_code == cli.EXIT_REFUSED, result.output
    assert "[G-KEYS]" in result.output and "Columns: ctx:m" in result.output and "Fix:" in result.output
    assert "refused (quick)" in result.output
    _, doc, _ = _report(fake_machine["runs"], pkg, "quick")
    assert doc["green"] is False
    keys = [g for g in doc["guards"] if g["id"] == "G-KEYS"][0]
    assert keys["status"] == "refuse" and keys["columns"] == ["ctx:m"]


def test_a_package_that_does_not_load_exits_5(tmp_path, fake_machine):
    pkg = B.make_clean_package(tmp_path / "p")
    (pkg / "split.yaml").write_text("excluded: {}\nseed: 7\n", encoding="utf-8")
    result = runner.invoke(cli.app, ["check", str(pkg), "--deep"])
    assert result.exit_code == cli.EXIT_PACKAGE, result.output


def test_check_refuses_a_protected_run_root(tmp_path, fake_machine):
    pkg = B.make_clean_package(tmp_path / "p")
    result = runner.invoke(cli.app, ["check", str(pkg), "--run-root", str(fake_machine["protected"] / "r")])
    assert result.exit_code == cli.EXIT_REFUSED, result.output
    assert "G-NOOVERWRITE" in result.output
    assert not (fake_machine["protected"] / "r").exists()


def test_deep_is_checks_own_option_and_on_the_allow_list():
    group = typer.main.get_command(cli.app)
    assert isinstance(group, click.Group)
    for name, command in group.commands.items():
        names = {p.name for p in command.params}
        assert names <= set(cli.ALLOWED_PARAMETERS), (name, names)
        if name != "check":
            assert not names & set(cli.CHECK_ONLY_PARAMETERS), name
    deep = [p for p in group.commands["check"].params if p.name == "deep"][0]
    assert isinstance(deep, click.Option) and deep.opts == ["--deep"] and deep.is_flag
    result = runner.invoke(cli.app, ["run", "x", "--deep"])
    assert result.exit_code == 2


def test_check_help_is_ascii():
    result = runner.invoke(cli.app, ["check", "--help"])
    assert result.exit_code == 0 and result.output.isascii()
    assert "--deep" in result.output and "--run-root" in result.output
    assert "R21 smoke groups" in " ".join(result.output.split())          # ruling M2, named in the help


def test_engine_code_sha256_covers_every_engine_file_but_proposed_and_caches(tmp_path):
    root = tmp_path / "treeroute"
    (root / "sub").mkdir(parents=True)
    (root / "_proposed").mkdir()
    (root / "__pycache__").mkdir()
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    (root / "sub" / "b.py").write_text("y = 2\n", encoding="utf-8")
    base = engine_code_sha256(root)
    (root / "_proposed" / "p.py").write_text("z = 3\n", encoding="utf-8")
    (root / "__pycache__" / "c.py").write_text("z = 3\n", encoding="utf-8")
    assert engine_code_sha256(root) == base
    (root / "sub" / "b.py").write_text("y = 2  # a comment counts here\n", encoding="utf-8")
    assert engine_code_sha256(root) != base
    assert len(engine_code_sha256()) == 64
