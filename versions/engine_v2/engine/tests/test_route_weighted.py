"""The GLS-weighted per-unit solve (R24 GLS arms, R25 row weights): a NEW formula for the owner's review,
gated here before any pipeline uses it.

route.solve: solve_grid_weighted / solve_point_weighted / grid_dual_weighted (the derivation is in
solve_grid_weighted's docstring: the weighted problem is the unweighted one on rows scaled by sqrt(w)).
route.kinds: _route_per_unit_grid / _route_per_unit_at with fit_weights.

Gates:
  1. every weight 1 gives the UNWEIGHTED kernel's bytes (solver and router, primal and dual regime, grid
     and point, with and without context, at 1 and 8 router workers);
  2. weighted results equal a BRUTE-FORCE weighted least-squares solve (the penalised objective written
     out and solved by an augmented least-squares system) within 1e-10, on random cases, primal and dual,
     grid and point, and per unit through the router;
  3. a common factor on every weight changes nothing but rounding (the trace-normalised penalty);
  4. the weighted shortcut is checked against solve_local (a planted fault is refused);
  5. trees-off stays unweighted; bad weights are refused.
"""

from types import SimpleNamespace

import numpy as np
import pytest

from treeroute.route import kinds as RK
from treeroute.route import solve as S

TOL_BRUTE = 1e-10
TOL_IDENTITY = 1e-6


# ------------------------------------------------------------------------------ brute force
def brute_force(Xc, yc, w, Xt, ntree, nctx, a_tree, a_ctx):
    """The weighted penalised least squares written out, solved without the engine's algebra:
        minimise sum_i w_i (y_i - x_i b)^2 + sum_j d_j b_j^2,
    d_j = a_B x tr(X_B' W X_B) / n_B on the penalised blocks (context, trees) and 0 on the intercept and
    normal, plus solve_local's 1e-8 jitter on EVERY diagonal element in the primal regime (rows >=
    columns; the dual regime solves the exact problem), with the weights divided by their mean over the
    unit's rows (the documented objective: a common factor leaves the exact minimiser unchanged and keeps
    the jitter at its unweighted scale). Solved as the augmented system
    [sqrt(W) X; diag(sqrt(d))] b = [sqrt(W) y; 0] by numpy's SVD least squares."""
    w = np.asarray(w, dtype=np.float64) / np.mean(w)
    n, p = Xc.shape
    o = S.UNPENALISED_COLUMNS
    d = np.zeros(p)
    G = Xc.T @ (Xc * w[:, None])
    if nctx:
        d[o:o + nctx] = a_ctx * np.trace(G[o:o + nctx, o:o + nctx]) / nctx
    d[o + nctx:] = a_tree * np.trace(G[o + nctx:, o + nctx:]) / ntree
    if n >= p:
        d = d + S.PRIMAL_DIAGONAL_JITTER
    A = np.vstack([Xc * np.sqrt(w)[:, None], np.diag(np.sqrt(d))])
    rhs = np.concatenate([yc * np.sqrt(w), np.zeros(p)])
    b = np.linalg.lstsq(A, rhs, rcond=None)[0]
    return Xt @ b


def make_case(rng, n, nctx, ntree, m=6):
    U = np.column_stack([np.ones(n), rng.standard_normal(n)])
    C = rng.standard_normal((n, nctx))
    T = rng.standard_normal((n, ntree)) + 0.5
    X = np.column_stack([U, C, T])
    beta = rng.standard_normal(X.shape[1]) * 0.3
    y = X @ beta + rng.standard_normal(n)
    Xt = np.column_stack([np.ones(m), rng.standard_normal(m), rng.standard_normal((m, nctx)),
                          rng.standard_normal((m, ntree)) + 0.5])
    w = np.exp(rng.uniform(np.log(0.05), np.log(5.0), n))          # R25 weights: max/min at most 100
    return X, y, Xt, w


def penalties(nctx):
    pts = [(0.5 * lv, 0.5 * lv * r) for lv in (0.1, 1.0, 100.0) for r in (0.0625, 1.0)]
    return pts if nctx else [(a, 0.0) for a, _ in pts[::2]]


SHAPES = [(12, 0, 40), (15, 2, 60), (30, 2, 8), (60, 0, 12), (25, 2, 23), (80, 1, 30)]


# ------------------------------------------------------------------------------ 1. unit weights = unweighted
@pytest.mark.parametrize("seed", range(40))
def test_unit_weights_give_the_unweighted_bytes(seed):
    rng = np.random.default_rng(seed)
    n, nctx, ntree = SHAPES[seed % len(SHAPES)]
    X, y, Xt, _ = make_case(rng, n, nctx, ntree)
    pen = penalties(nctx)
    ones = np.ones(n)
    assert np.array_equal(S.solve_grid(X, y, Xt, ntree, nctx, pen, True),
                          S.solve_grid_weighted(X, y, ones, Xt, ntree, nctx, pen, True))
    for a_tree, a_ctx in pen:
        assert np.array_equal(S.solve_point(X, y, Xt, ntree, nctx, a_tree, a_ctx),
                              S.solve_point_weighted(X, y, ones, Xt, ntree, nctx, a_tree, a_ctx))
    if n < X.shape[1]:
        assert np.array_equal(S.grid_dual(X, y, Xt, ntree, nctx, pen),
                              S.grid_dual_weighted(X, y, ones, Xt, ntree, nctx, pen))


# ------------------------------------------------------------------------------ 2. brute force
@pytest.mark.parametrize("seed", range(60))
def test_weighted_solves_match_brute_force_weighted_least_squares(seed):
    rng = np.random.default_rng(1000 + seed)
    n, nctx, ntree = SHAPES[seed % len(SHAPES)]
    X, y, Xt, w = make_case(rng, n, nctx, ntree)
    pen = penalties(nctx)
    ref = np.column_stack([brute_force(X, y, w, Xt, ntree, nctx, a, c) for a, c in pen])
    grid = S.solve_grid_weighted(X, y, w, Xt, ntree, nctx, pen, True)
    assert np.max(np.abs(grid - ref)) <= TOL_BRUTE, (n, nctx, ntree, np.max(np.abs(grid - ref)))
    for j, (a, c) in enumerate(pen):
        point = S.solve_point_weighted(X, y, w, Xt, ntree, nctx, a, c)
        assert np.max(np.abs(point - ref[:, j])) <= TOL_BRUTE
    # and the weights matter: the unweighted solve is a different answer
    assert np.max(np.abs(S.solve_grid(X, y, Xt, ntree, nctx, pen, False) - ref)) > 1e-6


def test_both_regimes_are_exercised():
    """The shapes above cover the dual regime (rows < columns: the weighted shared-Gram solve) and the
    primal regime (solve_local with the weights)."""
    dual = [s for s in SHAPES if s[0] < 2 + s[1] + s[2]]
    primal = [s for s in SHAPES if s[0] >= 2 + s[1] + s[2]]
    assert dual and primal


# ------------------------------------------------------------------------------ 3. a common factor
@pytest.mark.parametrize("seed", range(12))
def test_a_common_factor_on_the_weights_changes_nothing_but_rounding(seed):
    rng = np.random.default_rng(2000 + seed)
    n, nctx, ntree = SHAPES[seed % len(SHAPES)]
    X, y, Xt, _ = make_case(rng, n, nctx, ntree)
    pen = penalties(nctx)
    base = S.solve_grid(X, y, Xt, ntree, nctx, pen, False)
    for factor in (0.01, 7.3, 250.0):
        scaled = S.solve_grid_weighted(X, y, np.full(n, factor), Xt, ntree, nctx, pen, False)
        assert np.max(np.abs(scaled - base)) <= 1e-11 * max(1.0, float(np.max(np.abs(base))))


# ------------------------------------------------------------------------------ 4. the reference check
def test_the_weighted_shortcut_is_checked_against_solve_local(monkeypatch):
    rng = np.random.default_rng(7)
    X, y, Xt, w = make_case(rng, 15, 2, 60)
    pen = penalties(2)
    S.solve_grid_weighted(X, y, w, Xt, 60, 2, pen, True)               # passes as is
    real = S.grid_dual

    def planted(*args):
        return real(*args) + 1e-6
    monkeypatch.setattr(S, "grid_dual", planted)
    with pytest.raises(S.GridReferenceError, match="weighted shared-Gram"):
        S.solve_grid_weighted(X, y, w, Xt, 60, 2, pen, True, unit_id="u7")


@pytest.mark.parametrize("bad", [np.zeros(15), -np.ones(15), np.r_[np.ones(14), np.nan], np.ones(14),
                                 np.ones((15, 1)), np.r_[np.ones(14), np.inf]])
def test_bad_weights_are_refused(bad):
    rng = np.random.default_rng(3)
    X, y, Xt, _ = make_case(rng, 15, 2, 60)
    with pytest.raises(S.WeightRefusal):
        S.solve_grid_weighted(X, y, bad, Xt, 60, 2, penalties(2), False)
    with pytest.raises(S.WeightRefusal):
        S.solve_point_weighted(X, y, bad, Xt, 60, 2, 0.5, 0.125)


# ------------------------------------------------------------------------------ the router kernels
class Store(object):
    """In-memory tree-answer store: unit_view(keys, kind) answers every tree except the rows' own group's."""

    def __init__(self, values, row_group, tree_group):
        self.values = np.asarray(values, dtype=np.float32)
        self.row_group = np.asarray(row_group, dtype=object)
        self.tree_group = np.asarray(tree_group, dtype=object)

    @property
    def n_trees(self):
        return int(self.tree_group.size)

    def own_columns(self, group):
        return np.flatnonzero(self.tree_group == group).astype(np.int64)

    def unit_view(self, keys, kind):
        keys = np.asarray(keys, dtype=np.int64)
        g = sorted(set(self.row_group[keys].tolist()))
        assert len(g) == 1
        idx = np.flatnonzero(self.tree_group != g[0]).astype(np.int64)
        return SimpleNamespace(values=self.values[keys][:, idx].copy(), tree_index=idx, group=g[0], kind=kind)


def make_router_case(seed, n_units=4, n_fit=30, n_score=6, ntree_per_group=30, context=True):
    """PerUnitRows (link space) for n_units units of group g_t, a store of 3 groups' trees (g_t's own are
    never answered), the own-block mask, and one R25-like weight per fit row."""
    rng = np.random.default_rng(seed)
    tree_group = tuple(["g_a"] * ntree_per_group + ["g_b"] * ntree_per_group + ["g_t"] * 5)
    fu, ft, fy, fk, su, st, sk = [], [], [], [], [], [], []
    key = 0
    for u in range(n_units):
        for t in range(1, n_fit + 1):
            fu.append("u%d" % u)
            ft.append(t)
            fk.append(key)
            key += 1
        for t in range(n_fit + 1, n_fit + n_score + 1):
            su.append("u%d" % u)
            st.append(t)
            sk.append(key)
            key += 1
    base = rng.gamma(2.0, 2.0, size=(key, 1))
    values = base + rng.normal(0.0, 0.7, size=(key, len(tree_group)))
    fu, su = np.asarray(fu, dtype=object), np.asarray(su, dtype=object)
    ft, st = np.asarray(ft, dtype=np.int64), np.asarray(st, dtype=np.int64)
    fk, sk = np.asarray(fk, dtype=np.int64), np.asarray(sk, dtype=np.int64)
    fy = base[fk, 0] + rng.normal(0.0, 0.5, size=fk.size)
    season_f, season_s = ft % 4, st % 4
    fn, sn = np.empty(fk.size), np.empty(sk.size)
    for u in np.unique(fu):
        for k in range(4):                         # R15: the unit's season mean over its own fit rows
            m = fy[(fu == u) & (season_f == k)].mean()
            fn[(fu == u) & (season_f == k)] = m
            sn[(su == u) & (season_s == k)] = m
    fc = rng.standard_normal((fk.size, 2)) if context else None
    sc = rng.standard_normal((sk.size, 2)) if context else None
    rows = RK.PerUnitRows(cut=n_fit, fit_unit=fu, fit_time=ft, fit_y=fy, fit_normal=fn, fit_context=fc, fit_keys=fk,
                          score_unit=su, score_time=st, score_normal=sn, score_context=sc, score_keys=sk,
                          score_rows=np.arange(sk.size), unit_group={"u%d" % u: "g_t" for u in range(n_units)})
    row_group = np.full(key, "g_t", dtype=object)
    store = Store(values, row_group, tree_group)
    masks = RK.own_block_tree_columns(tree_group, {"g_a": ("g_a",), "g_b": ("g_b",), "g_t": ("g_t",)})
    w = np.exp(rng.uniform(np.log(0.05), np.log(5.0), fk.size))
    return rows, store, masks, w


@pytest.fixture
def workers(monkeypatch):
    def set_(n):
        monkeypatch.setattr(RK, "_TEST_ONLY_ROUTER_WORKERS", n)
    return set_


@pytest.mark.parametrize("n_fit,ntree,context", [(30, 30, True), (60, 6, True), (40, 12, False), (26, 40, False)])
@pytest.mark.parametrize("n_workers", [1, 8])
def test_the_router_with_unit_weights_gives_the_unweighted_bytes(n_fit, ntree, context, n_workers, workers):
    workers(n_workers)
    rows, store, masks, w = make_router_case(11, n_fit=n_fit, ntree_per_group=ntree, context=context)
    ones = np.ones(w.size)
    a = RK._route_per_unit_grid(rows, store, "plain", masks, TOL_IDENTITY)
    b = RK._route_per_unit_grid(rows, store, "plain", masks, TOL_IDENTITY, fit_weights=ones)
    assert np.array_equal(a.predictions, b.predictions) and np.array_equal(a.trees_off, b.trees_off)
    point = RK.per_unit_centre(context)
    a1 = RK._route_per_unit_at(rows, store, "plain", masks, point, TOL_IDENTITY)
    b1 = RK._route_per_unit_at(rows, store, "plain", masks, point, TOL_IDENTITY, fit_weights=ones)
    assert np.array_equal(a1.predictions, b1.predictions)


def _unit_design(rows, store, masks, unit):
    """The design the kernel builds for one unit (R14 layout), written out from the approved builders."""
    fsel = np.flatnonzero(rows.fit_unit == unit)
    ssel = np.flatnonzero(rows.score_unit == unit)
    keys = np.concatenate([rows.fit_keys[fsel], rows.score_keys[ssel]])
    view = store.unit_view(keys, "plain")
    want = np.asarray(masks.columns_by_group["g_t"], dtype=np.int64)
    vals = view.values[:, np.searchsorted(view.tree_index, want)].astype(np.float64)
    has_ctx = rows.fit_context is not None
    design = RK.per_unit_router_design(has_ctx)
    centre = rows.fit_normal[fsel].mean()
    Xc = RK.build_column_block(design, rows.fit_normal[fsel], rows.fit_context[fsel] if has_ctx else None,
                               vals[:fsel.size], centre).X
    Xt = RK.build_column_block(design, rows.score_normal[ssel], rows.score_context[ssel] if has_ctx else None,
                               vals[fsel.size:], centre).X
    return fsel, ssel, Xc, Xt, vals.shape[1], (rows.fit_context.shape[1] if has_ctx else 0)


@pytest.mark.parametrize("n_fit,ntree,context", [(30, 30, True), (60, 6, True), (40, 12, False)])
def test_the_weighted_router_matches_brute_force_per_unit(n_fit, ntree, context, workers):
    workers(8)
    rows, store, masks, w = make_router_case(23, n_fit=n_fit, ntree_per_group=ntree, context=context)
    grid = RK.per_unit_grid(context)
    out = RK._route_per_unit_grid(rows, store, "plain", masks, TOL_IDENTITY, fit_weights=w)
    point = grid[len(grid) // 2]
    at = RK._route_per_unit_at(rows, store, "plain", masks, point, TOL_IDENTITY, fit_weights=w)
    for unit in np.unique(rows.fit_unit):
        fsel, ssel, Xc, Xt, ntr, nctx = _unit_design(rows, store, masks, unit)
        for j, pt in enumerate(grid):
            a_tree, a_ctx = RK.point_penalties(pt, context)
            ref = brute_force(Xc, rows.fit_y[fsel], w[fsel], Xt, ntr, nctx, a_tree, a_ctx)
            assert np.max(np.abs(out.predictions[ssel, j] - ref)) <= TOL_BRUTE
        a_tree, a_ctx = RK.point_penalties(point, context)
        ref = brute_force(Xc, rows.fit_y[fsel], w[fsel], Xt, ntr, nctx, a_tree, a_ctx)
        assert np.max(np.abs(at.predictions[ssel, 0] - ref)) <= TOL_BRUTE


def test_trees_off_stays_unweighted_and_the_weights_move_the_tree_arm(workers):
    workers(1)
    rows, store, masks, w = make_router_case(5)
    a = RK._route_per_unit_grid(rows, store, "plain", masks, TOL_IDENTITY)
    b = RK._route_per_unit_grid(rows, store, "plain", masks, TOL_IDENTITY, fit_weights=w)
    assert np.array_equal(a.trees_off, b.trees_off)                   # R24: trees-off keeps the identity
    assert np.max(np.abs(a.predictions - b.predictions)) > 1e-6
    p0, fitted, short = RK._trees_off_per_unit(rows, TOL_IDENTITY)
    assert np.array_equal(p0, a.trees_off) and fitted == 4 and short == 0


@pytest.mark.parametrize("bad", ["short", "zero", "nan"])
def test_the_router_refuses_bad_weights(bad, workers):
    workers(1)
    rows, store, masks, w = make_router_case(9)
    w = {"short": w[:-1], "zero": np.r_[w[:-1], 0.0], "nan": np.r_[w[:-1], np.nan]}[bad]
    with pytest.raises(RK.RouteRefusal, match="R25"):
        RK._route_per_unit_grid(rows, store, "plain", masks, TOL_IDENTITY, fit_weights=w)
