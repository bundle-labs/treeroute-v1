"""R03: the test set's EXTRA columns are read WITHOUT the lock (slim.py:468-474 extras_of("test"); index.py:214-217
ctx.extras("test") at stage all). That is safe only while no registry names a label-bearing column as a
slim_extra_column: a history column (x__hist_*: labels of other rows, SPEC_HUMAN A2) or y. Nothing checks it
(slim.py:108-115 extra_columns, board.py:58-95 check_registry_against_run).
"""
import json
from types import SimpleNamespace

import pytest

from rivals_human import board as B
from review_tests.conftest import RUNS, real_registry


def _run(history):
    return SimpleNamespace(leads=[0], links=["identity"], derived={"R8": {"value": {"x1": {"steps": 0}}}},
                           plan={"history_columns": list(history)})


def _rival(extra):
    return {"id": "r", "kind": "I", "adapter": "a:b", "stats": ["x__v"], "coverage": "x_finite",
            "leads": {0: {"tier": "P"}}, "slim_extra_columns": list(extra)}


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="ISSUE 3: a registry may name a history column or y as a slim_extra_column; its TEST values "
                          "(labels of other test rows) are then readable before the lock through extras_of('test')")
@pytest.mark.parametrize("col", ["x__hist_last_1", "x__hist_mean_12", "y"])
def test_r03_registry_refuses_label_bearing_extra_columns(col):
    refused = False
    try:
        B.check_registry_against_run({"rivals": [_rival([col])]}, _run(["hist_last_1", "hist_mean_12"]))
    except Exception:                                                # noqa: BLE001
        refused = True
    assert refused, "slim_extra_columns %r was accepted" % col


@pytest.mark.parametrize("pkg", ["coral", "defo", "pm25", "ndvi"])
def test_r03_shipped_registries_name_no_label_bearing_extra(pkg):
    """Today's four registries are clean: no extra column is a run history column, y, or names the target."""
    from pathlib import Path
    plan = json.loads((Path(RUNS[pkg]) / "plan.json").read_text(encoding="utf-8"))
    hist = {"x__" + h for h in plan.get("history_columns") or []}
    for r in real_registry(pkg)["rivals"]:
        for c in r.get("slim_extra_columns") or []:
            assert c not in hist and c != "y" and "hist_" not in c, (pkg, r["id"], c)
            assert c.startswith(("x__", "c__")), (pkg, r["id"], c)
