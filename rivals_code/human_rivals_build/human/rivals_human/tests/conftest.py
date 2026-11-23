"""Shared fixtures of the human-rival tests (SPEC_HUMAN.txt section 7).

Layout (BUILD_NOTES_shared.txt): the human build root is D:/treeroute/human_rivals_build/human (the cwd of every
command); every toy, product, slim copy, index table and board of a test lives under the test's basetemp, which must
sit under D:/treeroute/human_rivals_build (the build's only write root) and must be a FRESH folder (pytest empties an
existing basetemp; that would be a delete, so an existing one is refused here).

Imports, all read-only: the human tool from the human build root; the signed common package and its toy builders
(rivals/tests/toy_runs.py) from D:/treeroute/rivals_build; the LIVE engine and its tests folder (the engine's toy
builders). sys.dont_write_bytecode is set first, so no import writes a __pycache__ into any of them.

Toy runs and flows are session-scoped and built only when a test asks for them.
"""

import datetime as _dt
import os
import sys
from pathlib import Path

import pytest

sys.dont_write_bytecode = True            # never write a .pyc into the LIVE engine, the common build or the tool

TESTS_DIR = Path(__file__).resolve().parent
HUMAN_ROOT = TESTS_DIR.parents[1]                                   # D:/treeroute/human_rivals_build/human
WRITE_ROOT = HUMAN_ROOT.parent                                      # D:/treeroute/human_rivals_build
COMMON_ROOT = Path(os.environ.get("HUMAN_COMMON_ROOT", r"D:\treeroute\rivals_build"))
ENGINE_ROOT = Path(os.environ.get("RIVALS_ENGINE_ROOT",
                                  r"C:\Users\<user>\Desktop\data set for reserch paper\engine"))
ENGINE_TESTS = ENGINE_ROOT / "tests"

# the human build first (rivals_human), then the common build (rivals), then the engine; the engine's test helpers
# are appended (they never shadow a name of ours)
for _p in (str(HUMAN_ROOT), str(COMMON_ROOT), str(ENGINE_ROOT)):
    if _p in sys.path:
        sys.path.remove(_p)
sys.path.insert(0, str(ENGINE_ROOT))
sys.path.insert(0, str(COMMON_ROOT))
sys.path.insert(0, str(HUMAN_ROOT))
if str(ENGINE_TESTS) not in sys.path:
    sys.path.append(str(ENGINE_TESTS))


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    if not config.option.basetemp:
        stamp = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        parent = WRITE_ROOT / "pt" / "tests"
        parent.mkdir(parents=True, exist_ok=True)
        config.option.basetemp = str(parent / ("auto_" + stamp))
    base = Path(config.option.basetemp).resolve()
    try:
        base.relative_to(WRITE_ROOT.resolve())
    except ValueError:
        raise pytest.UsageError("--basetemp %s is outside %s, the build's only write root" % (base, WRITE_ROOT))
    if not base.parent.is_dir():
        raise pytest.UsageError("the parent of --basetemp (%s) must exist (pytest refuses otherwise)" % base.parent)
    if base.exists():
        raise pytest.UsageError("--basetemp %s exists; pytest would empty it (a delete). Use a fresh name." % base)


def pytest_collection_modifyitems(config, items):
    if os.environ.get("HUMAN_REAL") == "1":
        return
    skip = pytest.mark.skip(reason="real-data test: set HUMAN_REAL=1 (owner command, one heavy job at a time)")
    for item in items:
        if "realdata" in item.keywords:
            item.add_marker(skip)


# ------------------------------------------------------------------------------------------ process setup
@pytest.fixture(scope="session", autouse=True)
def sklearnex_patched():
    """The engine's toy runs need sklearn patched (owner ruling C), as the engine and common tests do. sklearnex sets
    KMP_* variables; they are put back at the end."""
    before = dict(os.environ)
    import sklearnex

    was = sklearnex.sklearn_is_patched()
    if not was:
        sklearnex.patch_sklearn(verbose=False)
    yield
    if not was:
        sklearnex.unpatch_sklearn()
    for name in set(os.environ) - set(before):
        del os.environ[name]
    for name, value in before.items():
        if os.environ.get(name) != value:
            os.environ[name] = value


@pytest.fixture(scope="session", autouse=True)
def fake_launch_record():
    """numpy is loaded in a pytest process, so the engine's pin_threads() would refuse; a test launch record is put
    in the launcher's cache, as the common tests do (rivals/tests/conftest.py)."""
    from rivals.tests import toy_runs as T
    from treeroute import launch

    old = launch._STATE["record"]
    launch._STATE["record"] = dict(T.FAKE_LAUNCH)
    yield
    launch._STATE["record"] = old


# ------------------------------------------------------------------------------------------ toy runs and exports
@pytest.fixture(scope="session")
def grid_toy(tmp_path_factory):
    from rivals.tests import toy_runs as T
    return T.build_grid_toy(tmp_path_factory.mktemp("grid_ok"), "ok")


@pytest.fixture(scope="session")
def table_toy(tmp_path_factory):
    from rivals.tests import toy_runs as T
    return T.build_table_toy(tmp_path_factory.mktemp("table_ok"), "ok")


@pytest.fixture(scope="session")
def grid_export(grid_toy):
    """{lead: export lead folder} of the grid toy (the common export, through export.main --lead all)."""
    from rivals.tests import toy_runs as T
    return T.export_all_via_main(grid_toy)


@pytest.fixture(scope="session")
def table_export(table_toy):
    from rivals.tests import toy_runs as T
    return T.export_all_via_main(table_toy)


# ------------------------------------------------------------------------------------------ human toy setups
@pytest.fixture(scope="session")
def grid_human(grid_toy, grid_export):
    """The grid toy wired for the human tool: config, toy registry, toy products and the common board (init only)."""
    from rivals_human.tests import hooks as HK
    return HK.setup_grid(grid_toy, grid_export)


@pytest.fixture(scope="session")
def table_human(table_toy, table_export):
    """The table toy wired for the human tool, with a SCORED common board (the joiner needs one)."""
    from rivals_human.tests import hooks as HK
    return HK.setup_table(table_toy, table_export)


@pytest.fixture(scope="session")
def grid_slim(grid_human):
    from rivals_human.tests import hooks as HK
    return HK.slim_all(grid_human)


@pytest.fixture(scope="session")
def table_slim(table_human):
    from rivals_human.tests import hooks as HK
    return HK.slim_all(table_human)


@pytest.fixture(scope="session")
def grid_flow(grid_human, grid_slim):
    """slim, adapt (train side), check, init, tune, lock under the read spy (with pre-lock refusals tried), then the
    test side: adapt stage test, refit, refs, score at every lead, board."""
    from rivals_human.tests import hooks as HK
    return HK.run_flow(grid_human, grid_slim, out_name="_hout_a")


@pytest.fixture(scope="session")
def table_flow(table_human, table_slim):
    from rivals_human.tests import hooks as HK
    return HK.run_flow(table_human, table_slim, out_name="_hout_a")
