"""treeroute.route.neighbour: the local fit of the neighbour kind (SPEC_NEIGHBOUR.md 2-4, 7; SPEC_TABLE_MODE.md
4.2-4.3; owner ruling U3).

1. The one-unpenalised solve (n_unpenalised=1): the dual equals a brute-force primal (np.linalg.solve on
   the full normal equations, intercept unpenalised, no jitter) within 1e-9, k = 50, p = 60 to 400,
   weighted and not; the kernel's prediction for a row equals the brute force on its pool and columns.
2. The shared-Gram grid equals the per-point reference at all 35 points, weighted and not.
3. Trees-off equals a closed-form ridge of [1, context] at the base point; without context the pool mean.
4. A row whose drop set holds every tree takes its trees-off in every column (n_rows_no_tree).
5. G-DISJOINT fires on a planted own-block column; G-PLUMB on a missing kept answer.
6. Rows with no pool equal the donor-row median in y after the inverse link (1e-12): identity, log_c,
   arcsine.
7. Same bytes with 1 and 8 workers; pools shared across arms give the same bytes; the one-point pass
   equals the grid at that point; the trees-off pass equals the kernels' trees-off.
Plus the dense answer matrix from a store and the refusals.
"""

import numpy as np
import pytest

from treeroute.derive.router_rules import derive_r14_router_design
from treeroute.layer.links import Link, link_forward, link_inverse
from treeroute.route import kinds as RK
from treeroute.route import neighbour as N
from treeroute.route import solve as S
from treeroute.route.kinds import DesignMatrix, GridPoint, RouteGuardError, RouteRefusal, RouterKind

from test_route_neighbour_pool import GROUPS, _with, blocks_for, brute_pool, make_pass

TOL = 1e-9


def design_for(has_context):
    return derive_r14_router_design(RouterKind.NEIGHBOUR, ("c1", "c2") if has_context else ()).value


def tree_bank(groups=GROUPS, per_group=20):
    return tuple(g for g in groups for _ in range(per_group))


def answers_for(rows, tree_group):
    keys = np.sort(np.r_[rows.cand_keys, rows.score_keys]).astype(np.int64)
    group_of = dict(zip(rows.cand_keys.tolist(), rows.cand_group.tolist()))
    group_of.update(zip(rows.score_keys.tolist(), rows.score_group.tolist()))
    t = np.arange(len(tree_group))
    vals = np.sin(0.37 * t[None, :] + 0.013 * keys[:, None]) + 0.3 * np.cos(0.11 * t[None, :] * (keys[:, None] % 7))
    vals = vals.astype(np.float32)
    owners = np.asarray(tree_group, dtype=object)
    for r, k in enumerate(keys.tolist()):
        vals[r, owners == group_of[k]] = np.nan          # the store never answers a row's own group
    return N.NeighbourAnswers(keys=keys, values=vals, tree_group=tuple(tree_group), kind="plain")


def brute_ridge(X, y, w, nctx, ntree, a_tree, a_ctx, Xt):
    """The block-penalised weighted ridge by the full normal equations: intercept free, the context and
    tree blocks each a x (trace of its weighted Gram block / columns), no jitter."""
    G = X.T @ (X * w[:, None])
    r = X.T @ (y * w)
    reg = np.zeros(X.shape[1])
    if nctx:
        b = np.arange(1, 1 + nctx)
        reg[b] = a_ctx * np.trace(G[np.ix_(b, b)]) / nctx
    if ntree:
        b = np.arange(1 + nctx, 1 + nctx + ntree)
        reg[b] = a_tree * np.trace(G[np.ix_(b, b)]) / ntree
    return Xt @ np.linalg.solve(G + np.diag(reg), r)


def brute_row(rows, answers, i, point, weighted):
    """One score row's prediction by brute force: its pool, its drop set's columns, the full ridge."""
    idx = brute_pool(rows, i)
    groups = set(rows.cand_group[idx].tolist()) | {rows.score_group[i]}
    blocks = blocks_for()
    drop = set()
    for g in groups:
        drop.update(blocks.members[blocks.block_of_group[g]])
    owners = np.asarray(answers.tree_group, dtype=object)
    cols = np.flatnonzero(~np.isin(owners, np.asarray(sorted(drop), dtype=object)))
    arow = np.searchsorted(answers.keys, np.r_[rows.cand_keys[idx], rows.score_keys[i]])
    T = answers.values[np.ix_(arow, cols)].astype(np.float64)
    ctx = rows.cand_ctx[idx] if rows.cand_ctx is not None else np.zeros((idx.size, 0))
    sctx = rows.score_ctx[i:i + 1] if rows.score_ctx is not None else np.zeros((1, 0))
    X = np.column_stack([np.ones(idx.size), ctx, T[:-1]])
    Xt = np.column_stack([np.ones(1), sctx, T[-1:]])
    a_tree, a_ctx = N.neighbour_point_penalties(point, rows.cand_ctx is not None)
    w = rows.cand_w[idx] if weighted else np.ones(idx.size)
    return float(brute_ridge(X, rows.cand_y_link[idx], w, ctx.shape[1], cols.size, a_tree, a_ctx, Xt)[0]), cols.size


def random_case(k, p, nctx, seed):
    rng = np.random.default_rng(seed)
    X = np.column_stack([np.ones(k), rng.normal(size=(k, p - 1))])
    Xt = np.column_stack([np.ones(4), rng.normal(size=(4, p - 1))])
    y = rng.normal(size=k)
    w = rng.uniform(0.5, 2.0, size=k)
    return X, y, w, Xt, nctx, p - 1 - nctx


# ------------------------------------------------------------------------------ 1. dual = primal
@pytest.mark.parametrize("p", [60, 120, 400])
@pytest.mark.parametrize("weighted", [False, True])
def test_the_one_unpenalised_dual_equals_a_brute_force_primal(p, weighted):
    X, y, w, Xt, nctx, ntree = random_case(50, p, 2, p)
    w = w if weighted else np.ones(50)
    for a_tree, a_ctx in [(0.5, 0.25), (0.05, 0.003125), (50.0, 50.0)]:
        want = brute_ridge(X, y, w, nctx, ntree, a_tree, a_ctx, Xt)
        if weighted:
            got = S.solve_point_weighted(X, y, w, Xt, ntree, nctx, a_tree, a_ctx, n_unpenalised=1)
        else:
            got = S.solve_point(X, y, Xt, ntree, nctx, a_tree, a_ctx, n_unpenalised=1)
        assert float(np.abs(got - want).max()) < TOL


@pytest.mark.parametrize("weighted", [False, True])
def test_the_kernel_prediction_of_a_row_equals_the_brute_force_ridge(weighted):
    rows = make_pass(n_per_group=60, weights=weighted)
    tg = tree_bank()
    ans = answers_for(rows, tg)
    out, rec = N._route_neighbour_grid(rows, ans, tg, blocks_for(), design_for(True), TOL)
    grid = design_for(True).grid
    n_dual = n_primal = 0
    for i in range(0, rows.score_keys.size, 5):
        for j in (0, 17, 34):
            want, ncols = brute_row(rows, ans, i, grid[j], weighted)
            assert abs(out.predictions[i, j] - want) < TOL, (i, j)
        if 50 < 1 + 2 + ncols:
            n_dual += 1
        else:
            n_primal += 1
    assert n_dual > 0
    assert rec["n_rows_pool"] == rows.score_keys.size and rec["verified_rows"] == S.NVERIFY


def test_small_banks_take_the_primal_path_and_still_match():
    rows = make_pass(n_per_group=60)
    tg = tree_bank(per_group=3)                 # few kept trees: k >= p, the jittered primal
    ans = answers_for(rows, tg)
    out, _ = N._route_neighbour_grid(rows, ans, tg, blocks_for(), design_for(True), TOL)
    point = design_for(True).grid[16]
    for i in range(0, rows.score_keys.size, 9):
        want, ncols = brute_row(rows, ans, i, point, False)
        assert 1 + 2 + ncols <= 50
        assert abs(out.predictions[i, 16] - want) < 1e-7      # the primal adds a 1e-8 diagonal jitter


# ------------------------------------------------------------------------------ 2. grid = reference
@pytest.mark.parametrize("weighted", [False, True])
def test_the_shared_gram_grid_equals_the_reference_at_every_point(weighted):
    X, y, w, Xt, nctx, ntree = random_case(50, 200, 2, 7)
    pts = [N.neighbour_point_penalties(p, True) for p in N.neighbour_grid(True)]
    assert len(pts) == 35
    if weighted:
        a = S.grid_dual_weighted(X, y, w, Xt, ntree, nctx, pts, n_unpenalised=1)
        b = S.reference_grid_weighted(X, y, w, Xt, ntree, nctx, pts, n_unpenalised=1)
    else:
        a = S.grid_dual(X, y, Xt, ntree, nctx, pts, n_unpenalised=1)
        b = S.reference_grid(X, y, Xt, ntree, nctx, pts, n_unpenalised=1)
    assert float(np.abs(a - b).max()) < TOL


def test_the_grid_has_35_points_and_the_base_point_is_the_legacy_pair():
    assert len(N.neighbour_grid(True)) == 35 and len(N.neighbour_grid(False)) == 7
    base = N.neighbour_base_point(True)
    assert base == GridPoint(1.0, 0.5)
    assert N.neighbour_point_penalties(base, True) == (0.5, 0.25)
    assert N.neighbour_point_penalties(GridPoint(1.0, None), False) == (0.5, 0.0)
    with pytest.raises(RouteRefusal, match="R26"):
        N.neighbour_point_penalties(GridPoint(2.0, 0.5), True)


# ------------------------------------------------------------------------------ 3. trees-off
def test_trees_off_equals_a_closed_form_ridge_of_intercept_and_context():
    rng = np.random.default_rng(3)
    ctx = rng.normal(size=(30, 2))
    y = rng.normal(size=30)
    sctx = rng.normal(size=(3, 2))
    fit = DesignMatrix(X=np.column_stack([np.ones(30), ctx]), blocks=("intercept", "context", "context"))
    score = DesignMatrix(X=np.column_stack([np.ones(3), sctx]), blocks=fit.blocks)
    got = N.trees_off_neighbour(fit, y, score, N.neighbour_base_point(True))
    want = brute_ridge(fit.X, y, np.ones(30), 2, 0, 0.0, 0.25, score.X)
    assert float(np.abs(got - want).max()) < TOL


def test_trees_off_without_context_is_the_pool_mean():
    y = np.array([0.1, 0.7, 0.4, 1.9, 0.0, 0.3, 0.9, 0.2, 0.5, 0.6, 0.8, 1.1])
    fit = DesignMatrix(X=np.ones((12, 1)), blocks=("intercept",))
    score = DesignMatrix(X=np.ones((2, 1)), blocks=("intercept",))
    got = N.trees_off_neighbour(fit, y, score, GridPoint(1.0, None))
    assert float(np.abs(got - y.mean()).max()) < TOL


def test_trees_off_refuses_a_tree_block_or_a_normal():
    X = np.ones((5, 2))
    y = np.arange(5.0)
    for blocks in (("intercept", "trees"), ("intercept", "normal"), ("context", "intercept")):
        d = DesignMatrix(X=X, blocks=blocks)
        with pytest.raises(RouteRefusal, match="R16"):
            N.trees_off_neighbour(d, y, d, GridPoint(1.0, 0.5))
    ok = DesignMatrix(X=X, blocks=("intercept", "context"))
    with pytest.raises(RouteRefusal, match="R26"):
        N.trees_off_neighbour(ok, y, ok, GridPoint(1.0, None))         # context present, point without


def test_the_kernel_trees_off_is_the_pool_ridge_at_the_base_point():
    rows = make_pass()
    tg = tree_bank()
    out, _ = N._route_neighbour_grid(rows, answers_for(rows, tg), tg, blocks_for(), design_for(True), TOL)
    for i in range(0, rows.score_keys.size, 6):
        idx = brute_pool(rows, i)
        X = np.column_stack([np.ones(idx.size), rows.cand_ctx[idx]])
        Xt = np.r_[1.0, rows.score_ctx[i]][None, :]
        want = brute_ridge(X, rows.cand_y_link[idx], np.ones(idx.size), 2, 0, 0.0, 0.25, Xt)[0]
        assert abs(out.trees_off[i] - want) < TOL


# ------------------------------------------------------------------------------ 4. every tree dropped
def test_a_row_whose_drop_set_holds_every_tree_takes_its_trees_off():
    rows = make_pass()
    tg = tree_bank(groups=("g_a", "g_b"), per_group=5)      # the bank is one block: (g_a, g_b)
    out, rec = N._route_neighbour_grid(rows, answers_for(rows, tg), tg, blocks_for(), design_for(True), TOL)
    own = np.isin(rows.score_group, ["g_a", "g_b"])
    no_tree = rec["per_row"]["no_tree"]
    assert np.all(no_tree[own]) and rec["n_rows_no_tree"] == int(no_tree.sum()) >= int(own.sum())
    for i in np.flatnonzero(no_tree):
        assert np.all(out.predictions[i] == out.trees_off[i])
    assert np.any(~no_tree)
    assert np.all(rec["per_row"]["kept_trees"][no_tree] == 0)


# ------------------------------------------------------------------------------ 5. guards
def test_g_disjoint_fires_on_a_planted_own_block_column(monkeypatch):
    rows = make_pass()
    tg = tree_bank()
    monkeypatch.setattr(RK, "router_tree_columns", lambda tree_group, groups: np.arange(len(tree_group)))
    with pytest.raises(RouteGuardError, match="G-DISJOINT"):
        N._route_neighbour_grid(rows, answers_for(rows, tg), tg, blocks_for(), design_for(True), TOL)


def test_g_plumb_fires_on_a_missing_answer_in_a_kept_column():
    rows = make_pass()
    tg = tree_bank()
    ans = answers_for(rows, tg)
    vals = ans.values.copy()
    vals[:, :] = np.where(np.isnan(vals), np.nan, vals)
    vals[np.searchsorted(ans.keys, rows.score_keys[0]), tg.index("g_h")] = np.nan
    bad = N.NeighbourAnswers(keys=ans.keys, values=vals, tree_group=ans.tree_group, kind=ans.kind)
    drop0 = N.neighbour_pools(rows, blocks_for()).drop[0]
    assert "g_h" not in drop0
    with pytest.raises(RouteGuardError, match="G-PLUMB"):
        N._route_neighbour_grid(rows, bad, tg, blocks_for(), design_for(True), TOL)


def test_answers_must_carry_the_bank_tree_groups():
    rows = make_pass()
    tg = tree_bank()
    ans = answers_for(rows, tg)
    with pytest.raises(RouteGuardError, match="G-DISJOINT"):
        N._route_neighbour_grid(rows, ans, tuple(reversed(tg)), blocks_for(), design_for(True), TOL)
    missing = N.NeighbourAnswers(keys=ans.keys[1:], values=ans.values[1:], tree_group=ans.tree_group, kind="plain")
    with pytest.raises(RouteRefusal, match="no tree answers"):
        N._route_neighbour_grid(rows, missing, tg, blocks_for(), design_for(True), TOL)


def test_the_design_must_be_the_neighbour_design():
    rows = make_pass()
    tg = tree_bank()
    ans = answers_for(rows, tg)
    with pytest.raises(RouteRefusal, match="R14"):
        N._route_neighbour_grid(rows, ans, tg, blocks_for(), design_for(False), TOL)      # context mismatch
    per_unit = derive_r14_router_design(RouterKind.PER_UNIT, ("c1", "c2")).value
    with pytest.raises(RouteRefusal, match="R14"):
        N._route_neighbour_grid(rows, ans, tg, blocks_for(), per_unit, TOL)
    with pytest.raises(RouteRefusal, match="R36"):
        N._route_neighbour_grid(rows, ans, tg, blocks_for(), design_for(True), 0.0)


# ------------------------------------------------------------------------------ 6. fallback
@pytest.mark.parametrize("link,c,ub", [(Link.IDENTITY, None, None), (Link.LOG_C, 0.5, None),
                                       (Link.ARCSINE, None, 100.0)])
def test_rows_without_a_pool_equal_the_donor_median_after_the_inverse_link(link, c, ub):
    donor_y = np.array([0.0, 3.5, 12.0, 40.0, 7.25, 0.0, 99.0])
    median = float(np.median(donor_y))
    fb = float(link_forward(np.array([median]), link, c, ub)[0])
    rows = make_pass(n_per_group=1, fallback=fb)            # 8 candidates: every row under 12
    tg = tree_bank()
    out, rec = N._route_neighbour_grid(rows, answers_for(rows, tg), tg, blocks_for(), design_for(True), TOL)
    assert out.n_rows_pool_fallback == rows.score_keys.size == rec["n_rows_pool_fallback"]
    assert out.n_units_fitted == 0
    back = link_inverse(out.predictions.ravel(), link, c, ub)
    assert float(np.abs(back - median).max()) <= 1e-12
    assert float(np.abs(link_inverse(out.trees_off, link, c, ub) - median).max()) <= 1e-12


def test_fallback_and_pooled_rows_mix_in_one_pass(monkeypatch):
    rows = make_pass()
    tg = tree_bank()
    # rows issued on the cut see no candidate dated on the cut... make the first rows' issue the cut and
    # put every candidate on the cut day, so those rows have no eligible candidate
    m = rows.score_keys.size
    issue = rows.score_issue.copy()
    issue[:5] = int(rows.cut)
    day = rows.cand_day.copy()
    day[:] = np.minimum(day, int(rows.cut) - 1)
    day[: rows.cand_day.size - 11] = int(rows.cut)          # only 11 candidates before the cut day
    sub = _with(rows, score_issue=issue, cand_day=day)
    out, rec = N._route_neighbour_grid(sub, answers_for(sub, tg), tg, blocks_for(), design_for(True), TOL)
    fb = rec["per_row"]["pool_fallback"]
    assert np.all(fb[:5]) and not np.any(fb[5:])
    assert np.all(out.predictions[:5] == sub.fallback_link[0])
    assert out.n_rows_pool_fallback == 5 and out.n_units_fitted == m - 5
    assert rec["max_pool_day_minus_issue_day"] < 0


# ------------------------------------------------------------------------------ 7. determinism
@pytest.mark.parametrize("weighted", [False, True])
def test_the_same_bytes_with_one_and_eight_workers(monkeypatch, weighted):
    rows = make_pass(n_per_group=60, weights=weighted)
    tg = tree_bank()
    ans = answers_for(rows, tg)
    res = {}
    for workers in (1, 8):
        monkeypatch.setattr(RK, "_TEST_ONLY_ROUTER_WORKERS", workers)
        out, _ = N._route_neighbour_grid(rows, ans, tg, blocks_for(), design_for(True), TOL)
        at, _ = N._route_neighbour_at(rows, ans, tg, blocks_for(), design_for(True), GridPoint(3.0, 0.25), TOL)
        res[workers] = (out.predictions.tobytes(), out.trees_off.tobytes(), at.predictions.tobytes())
    assert res[1] == res[8]


def test_shared_pools_give_the_same_bytes_and_other_rows_are_refused():
    rows = make_pass()
    tg = tree_bank()
    ans = answers_for(rows, tg)
    pools = N.neighbour_pools(rows, blocks_for())
    a, _ = N._route_neighbour_grid(rows, ans, tg, blocks_for(), design_for(True), TOL)
    b, _ = N._route_neighbour_grid(rows, ans, tg, blocks_for(), design_for(True), TOL, pools=pools)
    assert a.predictions.tobytes() == b.predictions.tobytes()
    # another link's y (a different arm) may reuse the pools
    other = _with(rows, cand_y_link=rows.cand_y_link * 2.0 + 1.0)
    N._route_neighbour_grid(other, ans, tg, blocks_for(), design_for(True), TOL, pools=pools)
    moved = _with(rows, score_issue=rows.score_issue - 1)
    with pytest.raises(RouteRefusal, match="other rows"):
        N._route_neighbour_grid(moved, ans, tg, blocks_for(), design_for(True), TOL, pools=pools)


def test_the_one_point_pass_equals_the_grid_at_that_point():
    rows = make_pass(n_per_group=60, weights=True)
    tg = tree_bank()
    ans = answers_for(rows, tg)
    grid, _ = N._route_neighbour_grid(rows, ans, tg, blocks_for(), design_for(True), TOL)
    for j in (0, 12, 34):
        point = design_for(True).grid[j]
        at, rec = N._route_neighbour_at(rows, ans, tg, blocks_for(), design_for(True), point, TOL)
        assert at.predictions.shape == (rows.score_keys.size, 1) and at.grid == (GridPoint(point.level, point.ratio),)
        assert float(np.abs(at.predictions[:, 0] - grid.predictions[:, j]).max()) < TOL
        assert at.trees_off.tobytes() == grid.trees_off.tobytes()
        assert rec["verified_rows"] == 0
    with pytest.raises(RouteRefusal, match="R26"):
        N._route_neighbour_at(rows, ans, tg, blocks_for(), design_for(True), GridPoint(2.0, 0.5), TOL)


def test_the_trees_off_pass_equals_the_kernel_trees_off():
    rows = make_pass(weights=True)
    tg = tree_bank()
    out, _ = N._route_neighbour_grid(rows, answers_for(rows, tg), tg, blocks_for(), design_for(True), TOL)
    t0, n_pool, n_fb = N._trees_off_neighbour_pass(rows, blocks_for())
    assert t0.tobytes() == out.trees_off.tobytes() and n_pool == rows.score_keys.size and n_fb == 0


def test_a_pass_without_context():
    rows = make_pass(n_ctx=0)
    tg = tree_bank()
    ans = answers_for(rows, tg)
    out, _ = N._route_neighbour_grid(rows, ans, tg, blocks_for(), design_for(False), TOL)
    assert out.predictions.shape == (rows.score_keys.size, 7)
    for i in range(0, rows.score_keys.size, 8):
        idx = brute_pool(rows, i)
        assert abs(out.trees_off[i] - rows.cand_y_link[idx].mean()) < TOL
        want, _ = brute_row(rows, ans, i, GridPoint(1.0, None), False)
        assert abs(out.predictions[i, 2] - want) < TOL


# ------------------------------------------------------------------------------ dense answers
class _FakeStore(object):
    def __init__(self, tree_group, key_group):
        self.tree_group = np.asarray(tree_group, dtype=object)
        self.key_group = key_group
        self.n_trees = len(tree_group)

    def own_columns(self, group):
        return np.flatnonzero(self.tree_group == group)

    def unit_view(self, keys, kind):
        groups = {self.key_group[int(k)] for k in keys}
        assert len(groups) == 1
        g = groups.pop()
        idx = np.flatnonzero(self.tree_group != g)
        vals = (np.asarray(keys, np.float32)[:, None] * 1000 + idx[None, :]).astype(np.float32)
        from types import SimpleNamespace
        return SimpleNamespace(values=vals, tree_index=idx, group=g, kind=kind)


def test_dense_answers_place_each_group_s_view_by_tree_index():
    tg = ("g_a", "g_a", "g_b", "g_c")
    key_group = {5: "g_b", 2: "g_a", 9: "g_c", 7: "g_a"}
    store = _FakeStore(tg, key_group)
    ans = N.dense_answers(store, "plain", [5, 2, 9, 7], ["g_b", "g_a", "g_c", "g_a"], tg)
    assert ans.keys.tolist() == [2, 5, 7, 9] and ans.values.dtype == np.float32
    assert np.isnan(ans.values[0, :2]).all() and ans.values[0, 2] == 2002 and ans.values[0, 3] == 2003
    assert np.isnan(ans.values[1, 2]) and ans.values[1, 0] == 5000
    with pytest.raises(RouteGuardError, match="G-DISJOINT"):
        N.dense_answers(store, "plain", [5], ["g_b"], ("g_a", "g_b", "g_b", "g_c"))
    with pytest.raises(RouteGuardError, match="answered from the table"):
        N.dense_answers(store, "plain", [5], ["g_a"], tg)
    with pytest.raises(RouteRefusal, match="duplicates"):
        N.dense_answers(store, "plain", [5, 5], ["g_b", "g_b"], tg)
