"""route/solve.py's keyword n_unpenalised (SPEC_TABLE_MODE.md 5.5): omitted, every solver gives LIVE's bytes (the
grid no-op proof); n_unpenalised=1 through the primal, the dual, the shared-Gram grid with its reference check and
the weighted twins equals a brute-force primal; n_unpenalised=2 equals no keyword."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

from treeroute.route import solve as S

LIVE_SOLVE = Path(r"C:\Users\moh the ghost\Desktop\data set for reserch paper\engine\treeroute\route\solve.py")
PEN = [(0.05, 0.0125), (0.5, 0.125), (5.0, 2.5)]


@pytest.fixture(scope="module")
def live():
    if not LIVE_SOLVE.is_file():
        pytest.skip("the LIVE engine is not on this machine")
    was = sys.dont_write_bytecode
    sys.dont_write_bytecode = True                 # LIVE is only read: no bytecode is written beside it
    try:
        spec = importlib.util.spec_from_file_location("_live_solve_for_test", str(LIVE_SOLVE))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = was
    return mod


def _design(k, nctx, ntree, seed, o=2):
    rng = np.random.default_rng(seed)                 # test data only; the engine never draws
    cols = [np.ones(k)] + ([rng.standard_normal(k)] if o == 2 else [])
    X = np.column_stack(cols + [rng.standard_normal((k, nctx + ntree))])
    y = rng.standard_normal(k)
    Xt = np.column_stack([np.ones(3)] + ([rng.standard_normal(3)] if o == 2 else []) +
                         [rng.standard_normal((3, nctx + ntree))])
    w = rng.uniform(0.5, 2.0, k)
    return X, y, Xt, w


@pytest.mark.parametrize("k, nctx, ntree", [(40, 2, 10), (12, 2, 30), (20, 0, 25), (60, 3, 5)])
def test_the_keyword_omitted_gives_live_bytes(live, k, nctx, ntree):
    X, y, Xt, w = _design(k, nctx, ntree, k + ntree)
    pairs = [
        (S.solve_local(X, y, w, ntree, nctx, 0.5, 0.125), live.solve_local(X, y, w, ntree, nctx, 0.5, 0.125)),
        (S.solve_local_dual(X, y, w, ntree, nctx, 0.5, 0.125), live.solve_local_dual(X, y, w, ntree, nctx, 0.5, 0.125)),
        (S.grid_dual(X, y, Xt, ntree, nctx, PEN), live.grid_dual(X, y, Xt, ntree, nctx, PEN)),
        (S.reference_grid(X, y, Xt, ntree, nctx, PEN), live.reference_grid(X, y, Xt, ntree, nctx, PEN)),
        (S.solve_grid(X, y, Xt, ntree, nctx, PEN, True), live.solve_grid(X, y, Xt, ntree, nctx, PEN, True)),
        (S.solve_point(X, y, Xt, ntree, nctx, 0.5, 0.125), live.solve_point(X, y, Xt, ntree, nctx, 0.5, 0.125)),
        (S.grid_dual_weighted(X, y, w, Xt, ntree, nctx, PEN), live.grid_dual_weighted(X, y, w, Xt, ntree, nctx, PEN)),
        (S.reference_grid_weighted(X, y, w, Xt, ntree, nctx, PEN),
         live.reference_grid_weighted(X, y, w, Xt, ntree, nctx, PEN)),
        (S.solve_grid_weighted(X, y, w, Xt, ntree, nctx, PEN, True),
         live.solve_grid_weighted(X, y, w, Xt, ntree, nctx, PEN, True)),
        (S.solve_point_weighted(X, y, w, Xt, ntree, nctx, 0.5, 0.125),
         live.solve_point_weighted(X, y, w, Xt, ntree, nctx, 0.5, 0.125)),
    ]
    for a, b in pairs:
        assert np.asarray(a).tobytes() == np.asarray(b).tobytes()
        assert np.asarray(a).dtype == np.asarray(b).dtype


def _brute(X, y, w, ntree, nctx, a_tree, a_ctx, o):
    """The weighted ridge with o unpenalised columns, by np.linalg.solve on the full normal equations, no jitter."""
    G = X.T @ (X * w[:, None])
    reg = np.zeros(X.shape[1])
    if nctx:
        blk = np.arange(o, o + nctx)
        reg[blk] = a_ctx * float(np.trace(G[np.ix_(blk, blk)])) / nctx
    if ntree:
        blk = np.arange(o + nctx, o + nctx + ntree)
        reg[blk] = a_tree * float(np.trace(G[np.ix_(blk, blk)])) / ntree
    return np.linalg.solve(G + np.diag(reg), X.T @ (y * w))


@pytest.mark.parametrize("k, nctx, ntree", [(50, 2, 60), (50, 0, 120), (80, 2, 20)])
def test_one_unpenalised_column_equals_a_brute_force_primal(k, nctx, ntree):
    X, y, Xt, w = _design(k, nctx, ntree, 7 * k + ntree, o=1)
    ones = np.ones(k)
    for a_tree, a_ctx in PEN:
        b = _brute(X, y, ones, ntree, nctx, a_tree, a_ctx, 1)
        got = S.solve_point(X, y, Xt, ntree, nctx, a_tree, a_ctx, n_unpenalised=1)
        assert np.allclose(got, Xt @ b, rtol=0, atol=1e-6)
        bw = _brute(X, y, w / w.mean(), ntree, nctx, a_tree, a_ctx, 1)
        gw = S.solve_point_weighted(X, y, w, Xt, ntree, nctx, a_tree, a_ctx, n_unpenalised=1)
        assert np.allclose(gw, Xt @ bw, rtol=0, atol=1e-6)
    grid = S.solve_grid(X, y, Xt, ntree, nctx, PEN, True, n_unpenalised=1)
    gridw = S.solve_grid_weighted(X, y, w, Xt, ntree, nctx, PEN, True, n_unpenalised=1)
    for j, (a_tree, a_ctx) in enumerate(PEN):
        assert np.allclose(grid[:, j], Xt @ _brute(X, y, ones, ntree, nctx, a_tree, a_ctx, 1), rtol=0, atol=1e-6)
        assert np.allclose(gridw[:, j], Xt @ _brute(X, y, w / w.mean(), ntree, nctx, a_tree, a_ctx, 1), rtol=0,
                           atol=1e-6)


def test_two_unpenalised_columns_equal_no_keyword():
    X, y, Xt, w = _design(30, 2, 40, 3)
    assert S.solve_grid(X, y, Xt, 40, 2, PEN, True, n_unpenalised=2).tobytes() == \
        S.solve_grid(X, y, Xt, 40, 2, PEN, True).tobytes()
    assert S.solve_point_weighted(X, y, w, Xt, 40, 2, 0.5, 0.1, n_unpenalised=2).tobytes() == \
        S.solve_point_weighted(X, y, w, Xt, 40, 2, 0.5, 0.1).tobytes()
