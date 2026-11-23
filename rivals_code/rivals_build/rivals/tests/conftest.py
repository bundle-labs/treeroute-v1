"""Shared fixtures of the rival tests (SPEC_RIVALS.md section 4).

Every toy run, export and harness output lives under the test's basetemp, which must sit under
D:/treeroute/rivals_build (the build's only write root). The engine is imported read-only, and its own toy
builders (engine tests/test_pipeline.py, tests/table_toy.py) are imported from the engine's tests folder.

Toy runs are session-scoped and built only when a test asks for them (grid toy ~40 s, table toy ~25 s).
"""

import datetime as _dt
import os
import sys
from pathlib import Path

import pytest

sys.dont_write_bytecode = True            # never write a .pyc into the LIVE engine (or its tests folder)

TESTS_DIR = Path(__file__).resolve().parent
BUILD_ROOT = TESTS_DIR.parents[1]                     # D:/treeroute/rivals_build
ENGINE_ROOT = Path(os.environ.get("RIVALS_ENGINE_ROOT",
                                  r"C:\Users\<user>\Desktop\data set for reserch paper\engine"))
ENGINE_TESTS = ENGINE_ROOT / "tests"

# rivals_build first (so `import rivals` is OUR package, never the legacy rivals.py of the research folder),
# then the engine, then the engine's test helpers (appended: they never shadow a name of ours).
for _p in (str(BUILD_ROOT), str(ENGINE_ROOT)):
    if _p in sys.path:
        sys.path.remove(_p)
sys.path.insert(0, str(ENGINE_ROOT))
sys.path.insert(0, str(BUILD_ROOT))
if str(ENGINE_TESTS) not in sys.path:
    sys.path.append(str(ENGINE_TESTS))


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    if not config.option.basetemp:
        stamp = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        parent = BUILD_ROOT / "pt" / "tests"
        parent.mkdir(parents=True, exist_ok=True)
        config.option.basetemp = str(parent / ("auto_" + stamp))   # a fresh folder: pytest empties nothing
    base = Path(config.option.basetemp).resolve()
    try:
        base.relative_to(BUILD_ROOT.resolve())
    except ValueError:
        raise pytest.UsageError("--basetemp %s is outside %s, the build's only write root" % (base, BUILD_ROOT))
    if not base.parent.is_dir():
        raise pytest.UsageError("the parent of --basetemp (%s) must exist (pytest refuses otherwise)" % base.parent)


def pytest_collection_modifyitems(config, items):
    if os.environ.get("RIVALS_HEAVY", "").strip() != "1":
        heavy = pytest.mark.skip(reason="heavy synthetic test: set RIVALS_HEAVY=1 (~1 GB file, ~2.5 GiB RAM)")
        for item in items:
            if "heavy" in item.keywords:
                item.add_marker(heavy)
    if os.environ.get("RIVALS_REAL") == "1":
        return
    skip = pytest.mark.skip(reason="real-data test: set RIVALS_REAL=1 (owner-approved, one heavy job at a time)")
    for item in items:
        if "realdata" in item.keywords:
            item.add_marker(skip)


# ------------------------------------------------------------------------------------------ process setup
@pytest.fixture(scope="session", autouse=True)
def sklearnex_patched():
    """The engine's toy runs need sklearn patched (owner ruling C), as the engine tests do. sklearnex sets
    KMP_* variables; they are put back at the end so no later child process inherits them."""
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
    """numpy is loaded in a pytest process, so the engine's pin_threads() would refuse (launch.py:80-87). The
    launcher caches its record; a test record is put in that cache, as the engine tests pass FAKE_LAUNCH."""
    from rivals.tests import toy_runs as T
    from treeroute import launch

    old = launch._STATE["record"]
    launch._STATE["record"] = dict(T.FAKE_LAUNCH)
    yield
    launch._STATE["record"] = old


# ------------------------------------------------------------------------------------------ toy runs
@pytest.fixture(scope="session")
def grid_toy(tmp_path_factory):
    from rivals.tests import toy_runs as T
    return T.build_grid_toy(tmp_path_factory.mktemp("grid_ok"), "ok")


@pytest.fixture(scope="session")
def grid_toy_sparse(tmp_path_factory):
    from rivals.tests import toy_runs as T
    return T.build_grid_toy(tmp_path_factory.mktemp("grid_sparse"), "sparse")


@pytest.fixture(scope="session")
def grid_toy_decline(tmp_path_factory):
    from rivals.tests import toy_runs as T
    return T.build_grid_toy(tmp_path_factory.mktemp("grid_decline"), "decline")


@pytest.fixture(scope="session")
def table_toy(tmp_path_factory):
    from rivals.tests import toy_runs as T
    return T.build_table_toy(tmp_path_factory.mktemp("table_ok"), "ok")


@pytest.fixture(scope="session")
def table_toy_donor_only(tmp_path_factory):
    from rivals.tests import toy_runs as T
    return T.build_table_toy(tmp_path_factory.mktemp("table_donor_only"), "donor_only_group")


# ------------------------------------------------------------------------------------------ exports
@pytest.fixture(scope="session")
def grid_export(grid_toy):
    """The grid toy exported at every lead through export.main (--lead all), the CLI path."""
    from rivals.tests import toy_runs as T
    return T.export_all_via_main(grid_toy)


@pytest.fixture(scope="session")
def table_export(table_toy):
    """The table toy exported at every lead, every role, with the T1 read spy on (flow A's export)."""
    from rivals.tests import toy_runs as T
    return T.export_with_spy(table_toy)


# ------------------------------------------------------------------------------------------ harness flows
@pytest.fixture(scope="session")
def table_flow(table_toy, table_export):
    """Flow A: init (with hgb_l1) / tune / lock under the read spy; refusals tried before the lock; then refit,
    score and board at every lead (refit under a second spy that refuses any test y read)."""
    from rivals.tests import toy_runs as T
    return T.run_full_flow(table_toy, table_export, out_name="_out_a")


@pytest.fixture(scope="session")
def table_flow_b(table_toy, table_export):
    """Flow B: a second, independent init / tune / lock on the same export (determinism, T11; forced guard, T16)."""
    from rivals.tests import toy_runs as T
    return T.run_tune_lock_flow(table_toy, table_export, out_name="_out_b")
