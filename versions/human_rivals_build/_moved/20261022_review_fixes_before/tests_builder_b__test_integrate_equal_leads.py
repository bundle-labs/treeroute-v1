"""Integration tests (INTEGRATE_REPORT.txt): SPEC_HUMAN 3 "`check` asserts equality per (unit, time)" for the defo
rivals, as the generic registry field `equal_value_leads` (index.check_equal_value_leads, called by index.check;
validated by board.check_registry_against_run). Toy data only.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:      # the human build root only; never this folder (its conftest.py would
    sys.path.insert(0, str(HERE.parent))  # shadow the engine's top-level `conftest`, toy_runs.py:184-191)

from rivals_human import board as B           # noqa: E402
from rivals_human import index as IX          # noqa: E402


def _frame(lead, units, times, vals):
    return pd.DataFrame({"unit": units, "group": "g", "time": times, "issue": [t - lead for t in times],
                         "lead": lead, "x__v": np.asarray(vals, dtype=np.float64)})


def test_equal_leads_pass_count_and_nan_equals_nan():
    a = _frame(0, ["c1", "c1", "c2", "c3"], [2011, 2012, 2011, 2011], [0.1, 0.2, np.nan, 0.5])
    b = _frame(1, ["c1", "c1", "c2"], [2011, 2012, 2011], [0.1, 0.2, np.nan])
    rec = IX.check_equal_value_leads({0: a, 1: b}, ["x__v"], "toy")
    p = rec["pairs"]["0-1"]
    assert p["keys_compared"] == 3 and p["only_lead_0"] == 1 and p["only_lead_1"] == 0 and p["result"] == "equal"


@pytest.mark.parametrize("val", [0.1 + 1e-15, np.nan])
def test_equal_leads_refuse_on_any_difference(val):
    a = _frame(0, ["c1", "c2"], [2011, 2011], [0.1, 0.3])
    b = _frame(1, ["c1", "c2"], [2011, 2011], [val, 0.3])
    with pytest.raises(Exception, match="differ between lead 0 and lead 1"):
        IX.check_equal_value_leads({0: a, 1: b}, ["x__v"], "toy")


def test_equal_leads_refuse_without_shared_keys_or_with_duplicates():
    a = _frame(0, ["c1"], [2011], [0.1])
    with pytest.raises(Exception, match="share no"):
        IX.check_equal_value_leads({0: a, 1: _frame(1, ["c9"], [2011], [0.1])}, ["x__v"], "toy")
    with pytest.raises(Exception, match="twice"):
        IX.check_equal_value_leads({0: pd.concat([a, a]), 1: a}, ["x__v"], "toy")


def test_defo_registry_names_equal_value_leads_on_every_rival():
    reg = yaml.safe_load((HERE.parent / "registry" / "defo.yaml").read_text(encoding="utf-8"))
    for r in reg["rivals"]:
        assert r.get("equal_value_leads") == [0, 1], r["id"]


class _Run(object):
    leads = [0, 1]
    links = ["identity"]
    derived = {"R8": {"value": {}}}
    plan = {}


def test_registry_check_refuses_a_bad_equal_value_leads():
    base = {"id": "r", "kind": "N", "adapter": "a:b", "stats": ["x__v"], "coverage": "x_finite",
            "leads": {0: {"tier": "P"}, 1: {"tier": "none", "reason": "no product"}}}
    B.check_registry_against_run({"rivals": [dict(base)]}, _Run())
    with pytest.raises(Exception, match="equal_value_leads"):
        B.check_registry_against_run({"rivals": [dict(base, equal_value_leads=[0, 1])]}, _Run())
    with pytest.raises(Exception, match="equal_value_leads"):
        B.check_registry_against_run({"rivals": [dict(base, runner="adapters.x", equal_value_leads=[0, 1],
                                                      coverage="all_rows")]}, _Run())


def test_vt0007_toy_build_passes_the_tool_check_across_leads(tmp_path, fake_ctx_class, fake_run_class):
    """Builder B's real adapter on the toy granules, lead 0 and lead 1, through the tool's equality check."""
    from tests_builder_b import test_defo_adapters as TD

    ctx, products, cells, layers, asg = TD.prep_and_ctx(tmp_path, fake_ctx_class, fake_run_class)
    rv = TD.defo_rivals()
    TD.DP.run_stage(ctx, rv["vt0007_shipped"], "train", workers=1)
    out0 = TD.VT.build(ctx, rv["vt0007_shipped"], 0, "train")
    ctx1 = fake_ctx_class(tmp_path, ctx.run, "vt0007_shipped", products,
                          keys={"train": TD.keys_of(cells, range(2004, 2020), 1)}, stage="train")
    out1 = TD.VT.build(ctx1, rv["vt0007_shipped"], 1, "train")
    rec = IX.check_equal_value_leads({0: out0, 1: out1}, ["x__vt0007"], "vt0007 toy")
    assert rec["pairs"]["0-1"]["keys_compared"] == len(out0) and np.isfinite(out0["x__vt0007"]).any()
