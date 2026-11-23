"""Shared fixtures of the fire (Part B) tests (SPEC_HUMAN_PARTB.txt section 5, builder B3).

The rules of rivals_human/tests/conftest.py:43-56, copied: every write of a test lives under its basetemp, which must
sit under D:/treeroute/human_rivals_build (the build's only write root), whose parent must exist and which must be a
FRESH folder (pytest empties an existing basetemp: that would be a delete). sys.dont_write_bytecode is set first.
Imports, all read-only: the human tool from the human build root, the signed common package from
D:/treeroute/rivals_build, the LIVE engine and its tests folder (the G-NONAMES scanner of T-F16).
Real-data tests (@pytest.mark.realdata) run only with HUMAN_REAL=1, and then only as the separate light command of
spec section 5 (tests_fire -m realdata), never over the whole suite.

Run from D:\\treeroute\\human_rivals_build\\human:
    set PYTHONDONTWRITEBYTECODE=1
    py -3.9 -B -m pytest tests_fire -q -p no:cacheprovider --basetemp D:\\treeroute\\human_rivals_build\\pt\\tests\\<FRESH>
"""

import datetime as _dt
import os
import sys
from pathlib import Path

import pytest

sys.dont_write_bytecode = True             # never write a .pyc into the LIVE engine, the common build or the tool

TESTS_DIR = Path(__file__).resolve().parent
HUMAN_ROOT = TESTS_DIR.parent                                       # D:/treeroute/human_rivals_build/human
WRITE_ROOT = HUMAN_ROOT.parent                                      # D:/treeroute/human_rivals_build
COMMON_ROOT = Path(os.environ.get("HUMAN_COMMON_ROOT", r"D:\treeroute\rivals_build"))
ENGINE_ROOT = Path(os.environ.get("RIVALS_ENGINE_ROOT",
                                  r"C:\Users\<user>\Desktop\data set for reserch paper\engine"))
ENGINE_TESTS = ENGINE_ROOT / "tests"

# the human build first (rivals_human, adapters), then the common build (rivals), then the engine; the engine's test
# helpers are appended (they never shadow a name of ours). Never a test folder on sys.path (INTEGRATE_REPORT.txt I4).
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
        config.option.basetemp = str(parent / ("auto_fire_" + stamp))
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
    skip = pytest.mark.skip(reason="real-data test: set HUMAN_REAL=1 (the separate light command of spec section 5)")
    for item in items:
        if "realdata" in item.keywords:
            item.add_marker(skip)


# ------------------------------------------------------------------------------------------ modules under test
# Imported inside fixtures, so a module another builder has not written yet fails its own tests only (never the
# collection of the whole suite). Runners only as `from adapters import fire_enso, fire_turco` (spec 4).
@pytest.fixture(scope="session")
def geff():
    from adapters import fire_geff
    return fire_geff


@pytest.fixture(scope="session")
def refs_prep():
    from adapters import fire_refs_prep
    return fire_refs_prep


@pytest.fixture(scope="session")
def runners():
    from adapters import fire_enso, fire_turco
    return fire_enso, fire_turco


# ------------------------------------------------------------------------------------------ toy products
@pytest.fixture(scope="session")
def raw_subsets(tmp_path_factory):
    """Small subsets of D:/fire/cems/raw written once into the basetemp (read-only source; fixtures_fire)."""
    from tests_fire import fixtures_fire as FF
    if not FF.RAW.is_dir():
        pytest.fail("D:/fire/cems/raw is missing: the reader fixtures copy small subsets of it (read-only)")
    return FF.build_raw_subsets(tmp_path_factory.mktemp("raw_subsets"))


@pytest.fixture(scope="session")
def synth_products(tmp_path_factory):
    """The synthetic long ERA5 (2003-2019) and SEAS5 (starts 2002-08..2019-02) files, written once."""
    from tests_fire import fixtures_fire as FF
    return FF.build_synth_products(tmp_path_factory.mktemp("synth_products"))
