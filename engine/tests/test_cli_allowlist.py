"""G-NOKNOB, command line: every command takes only a package path and --run-root (plan 1.7); 'check' alone also
takes --deep (plan 6.1 names 'check --deep'; the freeze gate is 'check --deep green on all four', APP_PLAN.md 8.0 and
8.1 M5): it selects the data checks, never a modelling setting."""

import inspect

import click
import pytest
import typer
from typer.testing import CliRunner

from conftest import ENGINE_DIR, run_python
from treeroute import cli

EXPECTED_COMMANDS = {"check", "plan", "smoke", "run", "report", "status", "resume"}
ALLOWED_OPTION_FLAGS = {"--run-root", "--help"}
CHECK_ONLY_OPTION_FLAGS = {"--deep"}           # cli.CHECK_ONLY_PARAMETERS: 'check --deep' only

runner = CliRunner()


def _group():
    group = typer.main.get_command(cli.app)
    assert isinstance(group, click.Group)
    return group


def test_command_set_is_exactly_the_skeleton_set():
    assert set(_group().commands) == EXPECTED_COMMANDS


def test_group_level_takes_no_options_but_help():
    group = _group()
    names = {p.name for p in group.params}
    assert names <= {"help"}, names


@pytest.mark.parametrize("name", sorted(EXPECTED_COMMANDS))
def test_each_command_signature_is_allow_listed(name):
    group = _group()
    command = group.commands[name]
    allowed_flags = ALLOWED_OPTION_FLAGS | (CHECK_ONLY_OPTION_FLAGS if name == "check" else set())
    for param in command.params:
        assert param.name in cli.ALLOWED_PARAMETERS, "%s takes %r" % (name, param.name)
        if name != "check":
            assert param.name not in cli.CHECK_ONLY_PARAMETERS, "%s takes check's own %r" % (name, param.name)
        assert not getattr(param, "envvar", None), "%s reads an environment variable" % name
        if isinstance(param, click.Option):
            assert set(param.opts) | set(param.secondary_opts) <= allowed_flags, param.opts
        else:
            assert param.name == "package"
    # the Python signature too, so a parameter cannot hide behind a custom click type
    fn = getattr(cli, name)
    params = set(inspect.signature(fn).parameters)
    assert params <= set(cli.ALLOWED_PARAMETERS)
    if name != "check":
        assert not params & set(cli.CHECK_ONLY_PARAMETERS), name


def test_every_command_takes_the_package_argument():
    for name, command in _group().commands.items():
        args = [p for p in command.params if isinstance(p, click.Argument)]
        assert [a.name for a in args] == ["package"], name


def test_old_knobs_are_usage_errors(toy_package, fake_machine):
    # plan 1.7's old knobs, plus other flags a legacy script took
    for knob in ("--cells", "--dcells", "--npd", "--mf", "--links", "--levels", "--ratios",
                 "--alpha", "--actx", "--calib", "--donors", "--tests", "--from", "--seed",
                 "--threads", "--force", "--smoke", "--deep"):
        result = runner.invoke(cli.app, ["run", str(toy_package), knob, "5"])
        assert result.exit_code == 2, (knob, result.output)


@pytest.mark.parametrize("name", ["resume"])
def test_stubs_say_not_built_and_exit_nonzero(name, toy_package, fake_machine):
    result = runner.invoke(cli.app, [name, str(toy_package), "--run-root",
                                     str(fake_machine["runs"])])
    assert result.exit_code == cli.EXIT_NOT_BUILT, result.output
    assert "not built yet" in result.output


@pytest.mark.parametrize("name", ["plan", "smoke", "run"])
def test_built_pipeline_commands_refuse_the_toy_package_loudly(name, toy_package, fake_machine):
    """plan, smoke and run are built (the pipeline): on the toy package, whose target has no verdict, they
    refuse with the closed-world rule (exit 4), never 'not built'."""
    result = runner.invoke(cli.app, [name, str(toy_package), "--run-root",
                                     str(fake_machine["runs"])])
    assert result.exit_code == cli.EXIT_REFUSED, result.output
    assert "[G-CLOSED]" in result.output and "not built yet" not in result.output


def test_report_is_built_and_finds_no_headline_run(toy_package, fake_machine):
    result = runner.invoke(cli.app, ["report", str(toy_package), "--run-root", str(fake_machine["runs"])])
    assert result.exit_code == 0, result.output
    assert "no finished headline run" in result.output and "not built yet" not in result.output


def test_stub_refuses_a_protected_run_root(toy_package, fake_machine):
    target = fake_machine["protected"] / "runs"
    result = runner.invoke(cli.app, ["smoke", str(toy_package), "--run-root", str(target)])
    assert result.exit_code == cli.EXIT_REFUSED, result.output
    assert "G-NOOVERWRITE" in result.output


def test_stub_refuses_alias_spellings_of_a_protected_run_root(toy_package, fake_machine):
    import os

    if os.name != "nt":
        pytest.skip("Windows path spellings")
    bs = "\\"
    target = str(fake_machine["protected"] / "zz_probe")
    drive, rest = os.path.splitdrive(target)
    for spelling in (bs * 2 + "?" + bs + target, bs * 2 + "localhost" + bs + drive[0] + "$" + rest,
                     str(fake_machine["registry"] / "backup_x" / "zz_probe")):
        result = runner.invoke(cli.app, ["smoke", str(toy_package), "--run-root", spelling])
        assert result.exit_code == cli.EXIT_REFUSED, (spelling, result.output)
        assert "G-NOOVERWRITE" in result.output
    assert not (fake_machine["protected"] / "zz_probe").exists()


def test_stub_refuses_the_real_registry_backups_and_long_prefix(toy_package):
    """Against the real machine file and registry (read-only; nothing is created)."""
    import os

    from treeroute.runs.machine import load_machine

    machine = load_machine()
    folder = os.path.abspath(machine.registry_dir)
    if not os.path.isfile(os.path.join(folder, "protected_roots.txt")):
        pytest.skip("no shipped registry on this machine")
    probes = [os.path.join(folder, "zz_probe")]
    probes += [os.path.join(folder, d, "zz_probe") for d in sorted(os.listdir(folder))
               if d.startswith("backup") and os.path.isdir(os.path.join(folder, d))]
    with open(os.path.join(folder, "protected_roots.txt"), encoding="utf-8") as fh:
        first_root = [ln.split("#", 1)[0].strip() for ln in fh if ln.split("#", 1)[0].strip()][0]
    if os.name == "nt":
        probes.append("\\\\?\\" + os.path.abspath(os.path.join(first_root, "zz_probe")))
    for probe in probes:
        result = runner.invoke(cli.app, ["smoke", str(toy_package), "--run-root", probe])
        assert result.exit_code == cli.EXIT_REFUSED, (probe, result.output)
        assert not os.path.exists(probe)


def test_check_loads_the_package_then_reports_the_guards(toy_package, fake_machine):
    """check is built (treeroute/check/): it loads the package, prints its lines, runs the quick guards and, on the
    toy package (whose target has no verdict), refuses with exit 4 naming the guards, never 'not built'."""
    result = runner.invoke(cli.app, ["check", str(toy_package)])
    assert result.exit_code == cli.EXIT_REFUSED, result.output
    assert "fingerprint" in result.output and "not built yet" not in result.output
    assert "treeroute check refused (quick)" in result.output and "check report:" in result.output
    # leave one region out: the split line prints the exclusions and seen_during_design, no donor or
    # test count (the toy split excludes grp_z and marks grp_b seen during design)
    assert "excluded groups: 1; seen_during_design: 1" in result.output
    assert "trained and tested" in result.output
    assert "donor groups" not in result.output and "test groups" not in result.output


def test_check_refuses_a_broken_package(toy_package, fake_machine):
    (toy_package / "split.yaml").write_text("excluded: {}\nseed: 7\n", encoding="utf-8")
    result = runner.invoke(cli.app, ["check", str(toy_package)])
    assert result.exit_code == cli.EXIT_PACKAGE, result.output
    assert "derived: see derived.json" in result.output


@pytest.mark.parametrize("text", ["donor_groups: [a]\ntest_groups: [b]\n", "test_groups: [b]\n",
                                  "excluded: {}\ntests: 10\n"])
def test_check_refuses_a_donor_or_test_list(toy_package, fake_machine, text):
    (toy_package / "split.yaml").write_text(text, encoding="utf-8")
    result = runner.invoke(cli.app, ["check", str(toy_package)])
    assert result.exit_code == cli.EXIT_PACKAGE, result.output
    assert "derived: every group is tested" in result.output
    assert "G-NOKNOB" in result.output


def test_check_refuses_a_continuity_list_in_the_package(toy_package, fake_machine):
    (toy_package / "split.yaml").write_text("excluded: {}\ncontinuity_groups: [a]\n", encoding="utf-8")
    result = runner.invoke(cli.app, ["check", str(toy_package)])
    assert result.exit_code == cli.EXIT_PACKAGE, result.output
    assert "legacy_harness/ and treeroute_report/" in result.output


def test_status_with_no_runs(toy_package, fake_machine):
    result = runner.invoke(cli.app, ["status", str(toy_package)])
    assert result.exit_code == 0, result.output
    assert "no runs" in result.output


def test_entry_point_help_runs_through_the_launcher():
    proc = run_python("""
        import sys
        from treeroute import launch
        sys.argv = ['treeroute', '--help']
        try:
            launch.main()
        except SystemExit as e:
            print('EXIT', e.code)
        rec = launch.record()
        print('PINS', sorted(set(rec['env_pins'].values())), rec['backend']['onedal_threads'])
    """)
    assert proc.returncode == 0, proc.stderr
    assert "EXIT 0" in proc.stdout
    assert "PINS ['4'] 4" in proc.stdout
    assert "Usage" in proc.stdout


def test_module_entry_point(tmp_path):
    import subprocess
    import sys

    proc = subprocess.run([sys.executable, "-m", "treeroute", "--help"], cwd=str(ENGINE_DIR),
                          capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, proc.stderr
    for name in EXPECTED_COMMANDS:
        assert name in proc.stdout


# ---- help encoding (owner rulings F: the help tests must pass under PowerShell's default encoding) ----
# A PowerShell session here sets PYTHONIOENCODING=utf-8, so a child writes UTF-8 while the parent's
# subprocess text mode decodes with the Windows code page. rich's box-drawing characters then broke the
# decode (UnicodeDecodeError in the reader thread, stdout None). The help is now plain click text, ASCII.
POWERSHELL_LIKE = {"PYTHONIOENCODING": "utf-8:surrogateescape"}


def _help_bytes(args, env_extra):
    import os
    import subprocess
    import sys

    env = dict(os.environ)
    env.update(env_extra)
    proc = subprocess.run([sys.executable, "-m", "treeroute"] + args + ["--help"], cwd=str(ENGINE_DIR),
                          capture_output=True, timeout=180, env=env)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


@pytest.mark.parametrize("env_extra", [POWERSHELL_LIKE, {"PYTHONIOENCODING": "cp1252"}],
                         ids=["utf8_child", "cp1252_child"])
def test_module_help_is_ascii_whatever_the_child_encoding(env_extra):
    out = _help_bytes([], env_extra)
    assert all(b < 128 for b in out), sorted({b for b in out if b >= 128})
    text = out.decode("ascii")
    assert "Usage" in text
    for name in EXPECTED_COMMANDS:
        assert name in text


@pytest.mark.parametrize("name", sorted(EXPECTED_COMMANDS))
def test_every_command_help_is_ascii(name):
    result = runner.invoke(cli.app, [name, "--help"])
    assert result.exit_code == 0, result.output
    assert result.output.isascii(), [c for c in result.output if ord(c) > 127]
    assert "--run-root" in result.output and "PACKAGE" in result.output


def test_help_decodes_with_the_windows_code_page_under_a_utf8_child():
    """The PowerShell failure itself: text-mode decoding with the locale code page."""
    import locale

    out = _help_bytes(["check"], POWERSHELL_LIKE)
    out.decode(locale.getpreferredencoding(False))     # raised UnicodeDecodeError before the fix
    assert b"PACKAGE" in out


def test_rich_help_is_off():
    assert cli.app.rich_markup_mode is None
