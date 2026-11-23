"""Command line (Typer). Every command takes ONLY a package path and --run-root (plan 1.7), and 'check'
also takes --deep (plan 6.1 names 'check --deep'; it selects the data checks, never a modelling setting).

There are no modelling flags: every setting is derived from the data (derived.json). Resume and
status are their own commands. tests/test_cli_allowlist.py checks every command's parameters
against the allow-list, so a new flag fails the tests.

Exit codes:
  0  done
  2  usage error (unknown flag or missing argument; raised by click)
  3  not built yet (skeleton stub), or built only in part
  4  refused by a guard or a closed door (for example a protected run root, a router guard's breach,
     a launch whose thread pins or backend could not be verified)
  5  the package failed to load (closed folder, schema, include hash)

Heavy modules are imported inside the commands, after the launcher has pinned the thread pools.

Help and messages are plain ASCII: rich formatting is off (rich_markup_mode=None), so click's plain
formatter writes the help. rich's box-drawing characters could not be decoded by a reader that uses
the Windows code page (a PowerShell console, or subprocess text mode) when the child writes UTF-8
(PYTHONIOENCODING=utf-8), so the help tests failed there. tests/test_cli_allowlist.py checks that
every command's help is ASCII under that setting.
"""

from pathlib import Path
from typing import Annotated, Optional

import typer

from treeroute.errors import PackageError, RefusedError, RegistryError

EXIT_NOT_BUILT = 3
EXIT_REFUSED = 4
EXIT_PACKAGE = 5

# The only parameters any command may take (checked by tests/test_cli_allowlist.py). 'deep' is check's alone.
ALLOWED_PARAMETERS = ("package", "run_root", "deep")
CHECK_ONLY_PARAMETERS = ("deep",)

app = typer.Typer(
    name="treeroute",
    help="Generic tree-routing forecasting engine (placeholder name). See README.md.",
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
)

PackageArg = Annotated[Path, typer.Argument(help="Path to a dataset package folder.")]
RunRootOpt = Annotated[Optional[Path], typer.Option(
    "--run-root", help="Run root folder. Default: run_root in config/machine.yaml.")]


def _fail(code, message):
    typer.echo(message, err=True)
    raise typer.Exit(code=code)


def _not_built(command, detail=""):
    text = "treeroute %s: not built yet (engine skeleton)." % command
    if detail:
        text += " " + detail
    _fail(EXIT_NOT_BUILT, text)


def _machine():
    from treeroute.runs.machine import load_machine

    try:
        return load_machine()
    except PackageError as exc:
        _fail(EXIT_PACKAGE, "machine file: %s" % exc)


def _writable_run_root(run_root):
    """Resolve the run root (default from the machine file) and refuse a protected location."""
    from treeroute.runs.registry import Registry

    machine = _machine()
    root = Path(run_root) if run_root is not None else Path(machine.run_root)
    try:
        return Registry(machine.registry_dir).assert_writable(root)
    except (RefusedError, RegistryError) as exc:
        _fail(EXIT_REFUSED, str(exc))


def _load(package):
    from treeroute.package.load import load_package

    try:
        return load_package(package)
    except PackageError as exc:
        _fail(EXIT_PACKAGE, str(exc))


DeepOpt = Annotated[bool, typer.Option(
    "--deep", help="Also run the data checks (sentinels, ranges, observed steps, missing shares, joins, the "
                   "engineered recompute), streamed file by file, on the package's R21 smoke groups (owner ruling "
                   "M2: the first groups in sorted order; the quick checks cover the whole package); the groups and "
                   "the expected time are printed first.")]


@app.command()
def check(package: PackageArg, run_root: RunRootOpt = None, deep: DeepOpt = False):
    """The quick checks (package facts and verdicts, seconds) or, with --deep, the quick checks and the data checks
    (plan 5, 6.1) on the package's R21 smoke groups (owner ruling M2; no size knob).
    Writes check_<quick|deep>_<fingerprint>.json under <run root>/<package>/check/ (a deep report names its groups
    in checked_groups). Exit 0 only when no guard refuses; a refusal exits 4 naming the rule, the columns and the
    fix."""
    from treeroute.check.report import is_green, message_of, now_text, selection_text, write_report

    loaded = _load(package)
    root = _writable_run_root(run_root)
    typer.echo("package %s version %s" % (loaded.dataset.name, loaded.dataset.version))
    typer.echo("fingerprint %s" % loaded.fingerprint)
    typer.echo("files hashed: %d; store catalogs included: %d"
               % (len(loaded.file_hashes), len(loaded.include_hashes)))
    typer.echo("catalog columns: %d; ban verdicts: %d"
               % (len(loaded.catalog.columns), len(loaded.ban.verdicts)))
    typer.echo("split (leave one region out): excluded groups: %d; seen_during_design: %d. Every "
               "other group in the data is trained and tested; the groups, their bank and scored "
               "units and the overlap blocks are derived from the data by plan."
               % (len(loaded.split.excluded), len(loaded.split.seen_during_design)))
    mode = "deep" if deep else "quick"
    started = now_text()
    if deep:
        from treeroute.check.deep import run_deep

        typer.echo("check --deep: the ruling-M2 subset (owner ruling M2): the quick checks on the whole package, then "
                   "the data checks on the package's R21 smoke groups (named below and in the report)")
        ctx = _check_call(lambda: run_deep(package, echo=typer.echo))
    else:
        from treeroute.check.quick import run_quick

        ctx = _check_call(lambda: run_quick(package, echo=typer.echo))
    finished = now_text()
    for label, res in ctx.results:
        typer.echo("%-22s %-6s %s" % (label, {"pass": "pass", "flag": "flag", "block": "REFUSE"}[res.status.value],
                                      message_of(res)))
    selection = ctx.deep_selection if deep else None
    path = write_report(root, loaded, mode, ctx.results, started, finished, checked_groups=selection)
    typer.echo("check report: %s" % path)
    if deep:
        typer.echo("checked groups: %s" % selection_text(selection))
    if not is_green(ctx.results):
        refused = [label for label, res in ctx.results if res.status.value == "block"]
        _fail(EXIT_REFUSED, "treeroute check refused (%s): %d guards refused: %s. Each line above names the rule, "
                            "the columns and the fix." % (mode, len(refused), ", ".join(refused)))
    typer.echo("check %s: green" % mode)


def _check_call(call):
    """Run the check; a package that fails to load exits 5; a refusal outside a guard (a reader that refused
    before any guard could judge) exits 4 with its rule and fix."""
    try:
        return call()
    except PackageError as exc:
        _fail(EXIT_PACKAGE, str(exc))
    except RefusedError as exc:
        _fail(EXIT_REFUSED, "treeroute check refused: %s: %s" % (type(exc).__name__, exc))


def _pipeline(command, call):
    """Run one pipeline entry point; a refusal exits 4 (a guard's refusal, a router guard's breach
    (G-DISJOINT, R16), a launch the backend or thread pins refused, an unset constant), a package that
    fails to load exits 5, a part that is not built exits 3 (every refusal names its rule and fix).
    Anything else is a bug: it keeps its traceback and exits 1."""
    from treeroute.errors import LaunchError, NotBuiltError, UnsetConstantError
    from treeroute.route.kinds import RouteGuardError

    try:
        return call()
    except PackageError as exc:
        _fail(EXIT_PACKAGE, str(exc))
    except (RefusedError, RegistryError, UnsetConstantError, RouteGuardError, LaunchError) as exc:
        _fail(EXIT_REFUSED, "treeroute %s refused: %s: %s" % (command, type(exc).__name__, exc))
    except (NotImplementedError, NotBuiltError) as exc:
        _not_built(command, str(exc))


@app.command()
def plan(package: PackageArg, run_root: RunRootOpt = None):
    """Write derived.json and plan.json into the headline run folder (derive_all, the overlap blocks,
    the unit lists; no fit). 'run' then resumes that folder."""
    root = _writable_run_root(run_root)
    from treeroute.pipeline.run import plan_pipeline

    folder = _pipeline("plan", lambda: plan_pipeline(package, root, machine=_machine(), echo=typer.echo))
    typer.echo("plan: %s" % folder)


@app.command()
def smoke(package: PackageArg, run_root: RunRootOpt = None):
    """The fixed-size plumbing pass (R21): the first groups in sorted order, a fixed number of units
    and trees per group, the whole pipeline end to end: the nowcast, then the forecast ladder (the
    lead-0 contract and every derived lead). Smoke deltas carry no sign information."""
    root = _writable_run_root(run_root)
    from treeroute.pipeline.record import KIND_SMOKE
    from treeroute.pipeline.run import run_pipeline

    folder = _pipeline("smoke", lambda: run_pipeline(package, root, KIND_SMOKE, machine=_machine(),
                                                     echo=typer.echo))
    typer.echo("smoke finished: %s" % folder)


@app.command()
def run(package: PackageArg, run_root: RunRootOpt = None):
    """The headline run of the package: the nowcast, then the forecast ladder (hours on a real
    package: paste this command into your own terminal). It refuses when derived.json differs from
    the one the latest 'plan' showed. An unfinished run of the same fingerprint resumes; a finished
    one is refused."""
    root = _writable_run_root(run_root)
    from treeroute.pipeline.record import KIND_HEADLINE
    from treeroute.pipeline.run import run_pipeline

    folder = _pipeline("run", lambda: run_pipeline(package, root, KIND_HEADLINE, machine=_machine(),
                                                   echo=typer.echo))
    typer.echo("run finished: %s" % folder)


@app.command()
def report(package: PackageArg, run_root: RunRootOpt = None):
    """Print every finished run's verdict and build the headline table from finished headline runs
    (DRAFT, smoke and legacy runs, and runs with a not-headline reason, are refused by the table
    builder)."""
    root = _writable_run_root(run_root)
    from treeroute.pipeline.run import report_runs

    _pipeline("report", lambda: report_runs(package, root, machine=_machine(), echo=typer.echo))


@app.command()
def resume(package: PackageArg, run_root: RunRootOpt = None):
    """Resume an unfinished run by its fingerprint (not built yet)."""
    _writable_run_root(run_root)
    _not_built("resume", "'run' and 'smoke' resume an unfinished run of the same fingerprint "
                         "themselves (phases already done are not redone).")


@app.command()
def status(package: PackageArg, run_root: RunRootOpt = None):
    """Show phase, heartbeat and liveness of this package's runs under the run root."""
    from treeroute.package.load import load_dataset_file
    from treeroute.runs.resume import RUN_KINDS
    from treeroute.runs.status import describe, read_status

    try:
        name = load_dataset_file(package).name
    except PackageError as exc:
        _fail(EXIT_PACKAGE, str(exc))
    root = Path(run_root) if run_root is not None else Path(_machine().run_root)
    found = 0
    for kind in RUN_KINDS:
        kind_dir = root / name / kind
        if not kind_dir.is_dir():
            continue
        for folder in sorted(p for p in kind_dir.iterdir() if p.is_dir()):
            found += 1
            typer.echo("%s/%s: %s" % (kind, folder.name, describe(read_status(folder))))
    if not found:
        typer.echo("no runs of package %s under %s" % (name, root))
