"""R02: an M runner / adapter must see labels of ITS fit set only (SPEC_HUMAN 6: "M adapters get y only through
ctx.fit_labels(set) for fit sets"; methods.py:4 "labels only through ctx.fit_labels(fit_set)").

The tool hands the runner the SAME AdapterCtx for fit and predict (methods.py:39-47, board.py:544-549) and that ctx
(a) answers fit_labels for ANY fit set, not only the one being fitted (index.py:219-225), and (b) exposes the slim
reader itself as the public attribute `ctx.slim` (index.py:194), whose read_set gives y of every train set.
So while TUNING (fit on tune, scored on inner = the pick / N2 rows) a runner can read the inner labels through
fit_labels("refit") or ctx.slim.read_set("inner"). Test labels stay safe (read_set("test") needs the lock token).
The two shipped runners (ndvi_bardl, ndvi_kraft) behave: the static scan below passes. The hole is the contract.
"""
import types
from pathlib import Path

import numpy as np
import pytest

from rivals_human.tests import hooks as HK
from rivals_human import methods as ME

pytestmark = pytest.mark.flow


def _evil_runner(probe):
    def fit(ctx, rival, lead, fit_set):
        keys, y, _ = ctx.fit_labels("refit")               # NOT the fit set it was asked to fit
        probe["max_label_time"] = int(keys["time"].max())
        return {"lead": int(lead), "fit_set": fit_set}

    def predict(ctx, rival, lead, params, score_set):        # pragma: no cover (never reached in this test)
        raise RuntimeError("unused")
    return types.SimpleNamespace(fit=fit, predict=predict)


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="ISSUE 2: during tune a runner reads labels of rows after the guard cut (the inner rows it "
                          "is picked and guarded on) through ctx.fit_labels('refit')")
def test_r02_runner_fitted_on_tune_cannot_read_later_labels(grid_human, grid_slim):
    run = grid_human.h_run()
    guard_cut = int(run.cuts[0]["guard_cut"])
    actx = HK.adapter_ctx(grid_human, "toy_m", 0, "train")          # the ctx _tune_runner builds (board.py:544)
    probe = {}
    refused = False
    try:
        ME.run_fit(_evil_runner(probe), actx, grid_human.rival("toy_m"), 0, "tune")
    except Exception:                                                # noqa: BLE001 (a refusal is the safe outcome)
        refused = True
    assert refused or probe.get("max_label_time", -1) <= guard_cut, \
        "a runner fitted on 'tune' read labels up to %s (guard cut %d)" % (probe.get("max_label_time"), guard_cut)


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="ISSUE 2: AdapterCtx exposes the slim reader (ctx.slim) whose read_set returns y of any "
                          "train set (inner and guard included) to an I / N adapter or a runner")
def test_r02_adapter_ctx_does_not_hand_out_the_slim_reader(grid_human, grid_slim):
    actx = HK.adapter_ctx(grid_human, "toy_idx", 0, "all")
    got_y = None
    sl = getattr(actx, "slim", None)
    if sl is not None:
        try:
            got_y = sl.read_set("inner").y
        except Exception:                                            # noqa: BLE001
            got_y = None
    assert got_y is None, "ctx.slim.read_set('inner') returned %d inner labels" % len(got_y)


def test_r02_test_labels_stay_behind_the_lock_even_through_ctx_slim(grid_human, grid_slim):
    """The part that IS safe: the test set needs the lock token, whichever door is used."""
    actx = HK.adapter_ctx(grid_human, "toy_m", 0, "all")
    HK.refuses(("lock", "token"), actx.slim.read_set, "test")
    HK.refuses(("lock", "token"), actx.features, "test")


def test_r02_shipped_adapters_use_only_their_own_fit_set():
    """Static scan of every shipped adapter: fit_labels is called only with the runner's own `fit_set` argument, and
    no adapter touches ctx.slim / ctx._hctx / read_set (so today's code does not use the hole above)."""
    import ast
    root = HK.HUMAN_ROOT / "adapters"
    calls = {}
    for p in sorted(root.glob("*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        calls[p.name] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in ("slim", "_hctx", "read_set", "_token"):
                pytest.fail("%s:%d touches .%s" % (p.name, node.lineno, node.attr))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "fit_labels":
                calls[p.name].append((node.lineno, [ast.dump(a) for a in node.args]))
    for name, found in calls.items():
        for line, args in found:
            assert args == [ast.dump(ast.Name(id="fit_set", ctx=ast.Load()))], (name, line, args)
    assert calls["ndvi_bardl.py"] and calls["ndvi_kraft.py"]
