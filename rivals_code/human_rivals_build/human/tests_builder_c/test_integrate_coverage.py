"""Integration tests (INTEGRATE_REPORT.txt, C-R1): the NDVI runners' registry coverage rules are label-free rules the
tool accepts, and the mask the tool locks (board.coverage_rule_mask) equals the rows each runner predicts. If the
mask held a row the runner leaves NaN, refit would refuse (board.py `_refit_one`, "predicts no value on ... rows of its
locked coverage"); if it missed a row, a predicted row would be dropped from the board.

Toy data only (the ctx stand-ins of test_pm25_ndvi_adapters.py); the coverage rules are read from the REAL registry
files registry/ndvi.yaml and registry/pm25.yaml.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
HUMAN_ROOT = HERE.parent
if str(HUMAN_ROOT) not in sys.path:          # the human build root only (see tests_builder_b/__init__.py)
    sys.path.insert(0, str(HUMAN_ROOT))

from rivals_human import board as B          # noqa: E402
from rivals_human import config as C         # noqa: E402
from tests_builder_c import test_pm25_ndvi_adapters as TC   # noqa: E402


def _registry(pkg):
    with open(str(HUMAN_ROOT / "registry" / ("%s.yaml" % pkg)), encoding="utf-8") as f:
        return {r["id"]: r for r in yaml.safe_load(f)["rivals"]}


def _rule_ok(r):
    cov = r.get("coverage") or C.COVERAGE_X
    return cov in (C.COVERAGE_X, C.COVERAGE_ALL) or isinstance(cov, dict)


@pytest.mark.parametrize("pkg", ["coral", "defo", "pm25", "ndvi"])
def test_every_real_registry_coverage_is_a_rule(pkg):
    """board.check_registry_against_run's coverage refusals, without a run: plain words live in coverage_note."""
    for rid, r in _registry(pkg).items():
        assert _rule_ok(r), "%s %s: coverage %r is not a rule" % (pkg, rid, r.get("coverage"))
        if r.get("runner") or r.get("reads_target_in_test_window"):
            assert (r.get("coverage") or C.COVERAGE_X) != C.COVERAGE_X, "%s %s needs a label-free rule" % (pkg, rid)


def test_h1_registry_mask_equals_predicted_rows():
    rule = _registry("ndvi")["bardl_h1"]["coverage"]
    ctx, _ = TC.ndvi_ctx()
    params = TC.BD.fit(ctx, TC.H1_RIVAL, 0, "tune")
    pred = TC.BD.predict(ctx, TC.H1_RIVAL, 0, params, "inner")
    keys = ctx.sets["inner"][0][TC.KEYS].reset_index(drop=True)
    mask = B.coverage_rule_mask(rule, keys, ctx.units(), "bardl_h1 toy", ctx)
    np.testing.assert_array_equal(mask, pred["pre"].notna().to_numpy())
    assert mask.any() and not mask.all()           # u4 (not scored) is not covered


@pytest.mark.slow_ok
def test_kraft_registry_mask_equals_predicted_rows(tmp_path):
    pytest.importorskip("torch")
    from adapters import ndvi_kraft as KR

    rule = _registry("ndvi")["kraft_lstm"]["coverage"]
    assert rule.get("function") == "adapters.ndvi_kraft:coverage"
    rng = np.random.default_rng(0)
    steps = np.arange(TC.step(2010, 1), TC.step(2010, 1) + 20)
    rows = []
    for u in ("k1", "k2", "k3"):
        for s in steps:
            d1 = float(rng.normal())
            if u == "k2" and s == steps[15]:
                d1 = float("nan")                  # a hole: k2 windows that hold step 15 are incomplete
            rows.append({"unit": u, "step": int(s), "d1": d1, "d2": float(rng.normal()), "s1": 1.0})
    pd.DataFrame(rows).to_parquet(str(tmp_path / "r1.parquet"), index=False)
    fit_keys = pd.DataFrame([{"unit": u, "group": "g", "time": int(s), "issue": int(s), "lead": 0}
                             for u in ("k1",) for s in steps[11:17]])
    sc_keys = pd.DataFrame([{"unit": u, "group": "g", "time": int(s), "issue": int(s), "lead": 0}
                            for u in ("k1", "k2", "k3") for s in np.r_[steps[5], steps[12], steps[17:20]]])
    y = np.linspace(0.1, 0.6, len(fit_keys)).astype(np.float32)
    units = pd.DataFrame({"unit": ["k1", "k2", "k3"], "group": ["g"] * 3, "is_scored": [True, True, False]})
    ctx = TC.KCtx(tmp_path, {"tune": (fit_keys, y), "inner": (sc_keys, None)}, units)
    ctx.rival, ctx.lead = TC.KRAFT_RIVAL, 0          # what board.coverage_rule_mask passes to the function
    params = KR.fit(ctx, TC.KRAFT_RIVAL, 0, "tune")
    pred = KR.predict(ctx, TC.KRAFT_RIVAL, 0, params, "inner")
    mask = B.coverage_rule_mask(rule, sc_keys, units, "kraft toy", ctx)
    np.testing.assert_array_equal(mask, pred["pre"].notna().to_numpy())
    # k1: steps 12 and 17-19 covered (step 5 has no full window); k2: only step 12 is before the hole; k3 not scored
    assert int(mask.sum()) == 4 + 1


def test_pm25_index_rivals_use_x_finite():
    for rid, r in _registry("pm25").items():
        assert (r.get("coverage") or C.COVERAGE_X) == C.COVERAGE_X, rid
        assert not r.get("runner")
