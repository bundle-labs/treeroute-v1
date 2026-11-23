"""Fixtures of the skeptic review tests: the tool's own toy fixtures (rivals_human/tests/conftest.py), imported
read-only, so the review drives the same toys as the build's suite. Nothing here edits D:/treeroute/human_rivals_build/
human; every write goes to the pytest basetemp under D:/treeroute/human_rivals_build/pt.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
HUMAN_ROOT = HERE.parent / "human"
if str(HUMAN_ROOT) not in sys.path:
    sys.path.insert(0, str(HUMAN_ROOT))

# the build suite's fixtures and hooks (basetemp guard, realdata skip, sklearnex patch, fake launch record, toys)
from rivals_human.tests.conftest import *          # noqa: E402,F401,F403
from rivals_human.tests.conftest import pytest_configure, pytest_collection_modifyitems   # noqa: E402,F401

import json                                         # noqa: E402
from types import SimpleNamespace                   # noqa: E402

import pytest                                       # noqa: E402
import yaml                                         # noqa: E402

RUNS = {"pm25": r"D:\treeroute\runs\pm25\headline\20261007_74e67609",
        "ndvi": r"D:\treeroute\runs\ndvi\headline\20261016_d1de3158",
        "defo": r"D:\treeroute\runs\defo\headline\20261017_d71c61f4",
        "coral": r"D:\treeroute\runs\coral\headline\20261020_f3b8e3da"}


def real_run_json(pkg):
    """plan.json and derived.json of a real headline run as the tool's Timing reads them (run.plan, run.derived),
    plus its leads. Read-only, a few MB."""
    folder = Path(RUNS[pkg])
    plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    derived = json.loads((folder / "derived.json").read_text(encoding="utf-8"))
    return SimpleNamespace(plan=plan, derived=derived, folder=folder)


def real_registry(pkg):
    return yaml.safe_load((HUMAN_ROOT / "registry" / ("%s.yaml" % pkg)).read_text(encoding="utf-8"))


def rival_of(pkg, rid):
    return next(r for r in real_registry(pkg)["rivals"] if r["id"] == rid)


@pytest.fixture(scope="session")
def runjson():
    cache = {}

    def get(pkg):
        if pkg not in cache:
            cache[pkg] = real_run_json(pkg)
        return cache[pkg]
    return get
