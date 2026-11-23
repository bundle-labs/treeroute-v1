"""treeroute.route.region: the region router kind (plan 4.2, R12, R14-R16, U-1; owner rulings A D80-D82,
C region-router threads, D, E L2 rules 2-4 and L4).

1. The trace-normalised ridge MOVED AS-IS: the shipped ridge and apply (defo_softgate.py) are read as TEXT
   and executed in an isolated namespace; region_gram + region_ridge + region_predict without a normal
   (LEGACY mode) give the same bytes, at 4 BLAS threads and at 1.
2. U-1 (D81): the unpenalised normal by projection equals the explicit block-penalised least squares
   (intercept and normal free, trees at lam x the tree block's own trace); a constant normal leaves
   the legacy bytes unchanged; a huge lam leaves intercept + normal = trees-off.
3. The kernel on arrays: own overlap block dropped (mask checked against the store), the whole-unit
   evenly spaced cap (split.region_cap_units at the budget read at call time), scored units decoupled
   from the cap, trees-off = normal asserted (R16), BLAS held at BLAS_THREADS.
4. L4: a Gram shared across links gives the same bytes as a Gram formed per pass; a Gram built on other
   rows, columns or table is refused.
5. The fallback service (R12): plan, level search (ties, the 10-unit centre rule), pooled surface MAE,
   routing on bank units, and the fill of a real per-unit pass's NaN rows.
6. Fail loudly: every refusal and guard.
"""

import ast
from types import SimpleNamespace

import numpy as np
import pytest

from conftest import REPO_PARENT

from treeroute import engine_constants as K
from treeroute import split as SP
from treeroute.route import kinds as RK
from treeroute.route import region as R
from treeroute.route.kinds import GridPoint, RouteGuardError, RouteOutput, RouteRefusal

SOFTGATE = REPO_PARENT / "defo_softgate.py"
needs_shipped = pytest.mark.skipif(not SOFTGATE.is_file(), reason="the shipped scripts are not beside the engine")
TOL = 1e-9          # the trees-off identity tolerance these tests pass (R36 stand-in)


# ------------------------------------------------------------------------------ shipped source
def _function_source(path, name):
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    hits = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    assert len(hits) == 1, (path, name)
    lines = text.split("\n")
    return "\n".join(ln.rstrip("\r") for ln in lines[hits[0].lineno - 1:hits[0].end_lineno]) + "\n"


@pytest.fixture(scope="module")
def shipped():
    import gc
    ns = {"np": np, "gc": gc}
    for name in ("ridge", "apply"):
        exec(compile(_function_source(SOFTGATE, name), "softgate:" + name, "exec"), ns)
    return ns


def _blas(n):
    from threadpoolctl import threadpool_limits
    return threadpool_limits(limits=n, user_api="blas")


def _legacy_engine(A, y, rows, lam):
    gram = R.region_gram(A[rows])
    fit = R.region_ridge(gram, y[rows], lam)
    return fit, R.region_predict(fit, A)


# ------------------------------------------------------------------------------ 1. moved as-is
@needs_shipped
@pytest.mark.parametrize("threads", [4, 1])
def test_legacy_ridge_is_the_shipped_ridge_byte_for_byte(shipped, threads):
    rs = np.random.RandomState(3)
    n, p = 2600, 180
    A = (rs.gamma(2.0, 0.02, size=(n, p)) + rs.normal(0, 0.01, size=(n, p))).astype(np.float16).astype(np.float32)
    y = np.arcsin(np.sqrt(np.clip(rs.beta(0.3, 8.0, size=n), 0, 1)))
    rows = np.flatnonzero(rs.rand(n) < 0.7)
    rows = rows[np.linspace(0, len(rows) - 1, 1500).astype(np.int64)]    # the shipped linspace row pick
    for lam in (100.0, 10.0, 3000.0):
        with _blas(threads):
            w_s, b_s = shipped["ridge"](A, y, rows, lam)
            p_s = shipped["apply"](A, (w_s, b_s))
            fit, p_e = _legacy_engine(A, y, rows, lam)
        assert fit.w.tobytes() == w_s.tobytes()
        assert np.float64(fit.intercept).tobytes() == np.float64(b_s).tobytes()
        assert type(fit.intercept) is type(b_s)
        assert p_e.dtype == p_s.dtype and p_e.tobytes() == p_s.tobytes()


def test_consumed_block_gives_the_same_bytes_as_a_copied_one():
    rs = np.random.RandomState(12)
    T = rs.rand(700, 33).astype(np.float32)
    y = rs.rand(700)
    copied = R.region_gram(T)
    assert np.array_equal(T, T.copy()) and T.flags.writeable            # the caller's block is untouched
    mine = T.copy()
    consumed = R.region_gram(mine, consume=True)
    assert consumed.centred is mine                                       # centred in place, no copy
    for a, b in ((copied.centred, consumed.centred), (copied.means, consumed.means),
                 (copied.gram, consumed.gram)):
        assert a.tobytes() == b.tobytes()
    assert copied.trace_scale == consumed.trace_scale
    view = T[:, :10]                                                      # not C-ordered: copied anyway
    assert R.region_gram(view, consume=True).centred is not view


@pytest.mark.parametrize("with_normal", [False, True])
def test_prediction_bytes_do_not_depend_on_the_score_block_layout(with_normal):
    """A masked store view (values[:, columns]) is not C-ordered, a single-block view is: the float32
    matrix-vector product on a column-ordered block rounds differently (about one ulp). region_predict
    normalises to C order, so every layout (C, Fortran, strided, float64) gives the C-ordered bytes."""
    rs = np.random.RandomState(31)
    full = rs.rand(3000, 57).astype(np.float32)
    cols = np.sort(rs.choice(57, 41, replace=False))
    y, n_fit, n_score = rs.rand(2000), rs.rand(2000), rs.rand(1000)
    gram = R.region_gram(full[:2000][:, cols])
    fit = R.region_ridge(gram, y, 100.0, n_fit if with_normal else None)
    sn = n_score if with_normal else None
    fancy = full[2000:][:, cols]
    layouts = [np.asfortranarray(fancy), full[2000:, :][:, cols], np.asfortranarray(full)[2000:][:, cols],
               full[2000:].astype(np.float64)[:, cols]]
    assert any(not a.flags.c_contiguous for a in layouts)
    with _blas(4):
        ref = R.region_predict(fit, np.ascontiguousarray(fancy), sn)
        for a in layouts:
            assert R.region_predict(fit, a, sn).tobytes() == ref.tobytes()


@needs_shipped
def test_legacy_prediction_block_spans_more_than_one_apply_block(shipped):
    rs = np.random.RandomState(4)
    n, p = R.REGION_APPLY_BLOCK_ROWS + 1234, 24
    A = rs.rand(n, p).astype(np.float32)
    y = rs.rand(n)
    rows = np.arange(0, n, 7)
    with _blas(4):
        w_s, b_s = shipped["ridge"](A, y, rows, 100.0)
        p_s = shipped["apply"](A, (w_s, b_s))
        _, p_e = _legacy_engine(A, y, rows, 100.0)
    assert p_e.tobytes() == p_s.tobytes()


# ------------------------------------------------------------------------------ 2. U-1
def _explicit_u1(T, y, normal, lam, score_T, score_normal):
    """Block-penalised least squares in float64: intercept and normal free, trees at lam x the centred
    tree block's trace / columns (+ 1e-12), by the full normal equations."""
    T = T.astype(np.float64)
    n, p = T.shape
    Tc = T - T.mean(0)
    s = np.trace(Tc.T @ Tc) / p + 1e-12
    X = np.column_stack([np.ones(n), normal - normal.mean(), T])
    G = X.T @ X
    G[2:, 2:] += lam * s * np.eye(p)
    beta = np.linalg.solve(G, X.T @ y)
    Xs = np.column_stack([np.ones(len(score_normal)), score_normal - normal.mean(), score_T.astype(np.float64)])
    return Xs @ beta, beta


def test_u1_normal_by_projection_is_the_block_penalised_least_squares():
    rs = np.random.RandomState(5)
    n, p, m = 900, 40, 120
    T = rs.rand(n, p).astype(np.float32)
    normal = rs.rand(n) * 2.0
    y = 0.4 + 0.9 * normal + T[:, :5].astype(np.float64) @ rs.rand(5) + rs.normal(0, 0.05, n)
    ST = rs.rand(m, p).astype(np.float32)
    SN = rs.rand(m) * 2.0
    for lam in (0.1, 1.0, 100.0):
        gram = R.region_gram(T)
        fit = R.region_ridge(gram, y, lam, normal)
        got = R.region_predict(fit, ST, SN)
        want, beta = _explicit_u1(T, y, normal, lam, ST, SN)
        assert np.max(np.abs(got - want)) < 2e-5
        assert abs(fit.normal_coef - beta[1]) < 2e-5
        assert fit.lam == lam


def test_u1_constant_normal_leaves_the_legacy_bytes():
    rs = np.random.RandomState(6)
    T = rs.rand(500, 30).astype(np.float32)
    y = rs.rand(500)
    gram = R.region_gram(T)
    legacy = R.region_ridge(gram, y, 100.0)
    const = R.region_ridge(gram, y, 100.0, np.full(500, 0.25))
    assert const.w.tobytes() == legacy.w.tobytes()
    assert const.normal_coef == 0.0
    ST = rs.rand(40, 30).astype(np.float32)
    assert (R.region_predict(const, ST, np.full(40, 0.25)).tobytes()
            == R.region_predict(legacy, ST).tobytes())


def test_u1_huge_penalty_leaves_intercept_plus_normal():
    rs = np.random.RandomState(7)
    n = 600
    T = rs.rand(n, 20).astype(np.float32)
    normal = np.repeat(rs.rand(60), 10)
    y = normal + rs.normal(0, 0.1, n)
    fit = R.region_ridge(R.region_gram(T), y, 1e12, normal)
    assert np.max(np.abs(fit.w)) < 1e-8
    ols = np.polyfit(normal - normal.mean(), y, 1)
    assert abs(fit.normal_coef - ols[0]) < 1e-6


def test_solver_refusals():
    rs = np.random.RandomState(8)
    T = rs.rand(50, 5).astype(np.float32)
    with pytest.raises(RouteRefusal):
        R.region_gram(T[:1])
    with pytest.raises(RouteRefusal):
        R.region_gram(np.arange(10).reshape(5, 2))                   # integers
    bad = T.copy()
    bad[3, 1] = np.nan
    with pytest.raises(RouteRefusal):
        R.region_gram(bad)
    gram = R.region_gram(T)
    for lam in (0.0, -1.0, float("nan"), True):
        with pytest.raises(RouteRefusal):
            R.region_ridge(gram, rs.rand(50), lam)
    with pytest.raises(RouteRefusal):
        R.region_ridge(gram, rs.rand(49), 1.0)
    y = rs.rand(50)
    y[0] = np.inf
    with pytest.raises(RouteRefusal):
        R.region_ridge(gram, y, 1.0)
    legacy = R.region_ridge(gram, rs.rand(50), 1.0)
    u1 = R.region_ridge(gram, rs.rand(50), 1.0, rs.rand(50))
    with pytest.raises(RouteRefusal):
        R.region_predict(legacy, T, rs.rand(50))
    with pytest.raises(RouteRefusal):
        R.region_predict(u1, T)
    with pytest.raises(RouteRefusal):
        R.region_predict(legacy, T[:, :4])


def test_cholesky_failure_stops_the_run(monkeypatch):
    rs = np.random.RandomState(9)
    gram = R.region_gram(rs.rand(40, 6).astype(np.float32))

    def boom(_):
        raise np.linalg.LinAlgError("not positive definite")

    monkeypatch.setattr(R.np.linalg, "cholesky", boom)
    with pytest.raises(RouteGuardError):
        R.region_ridge(gram, rs.rand(40), 100.0)


# ------------------------------------------------------------------------------ grid and design
def test_grid_design_and_lambda_match_the_engine_constants_and_derive():
    from treeroute.derive.router_rules import derive_r14_router_design
    d = derive_r14_router_design("region", ()).value
    e = R.region_router_design()
    assert (e.kind.value, e.columns, e.unpenalised, e.centre, e.fit_row_cap) == \
        (d.kind.value, d.columns, d.unpenalised, d.centre, d.fit_row_cap)
    assert [(p.level, p.ratio) for p in e.grid] == [(p.level, p.ratio) for p in d.grid]
    assert len(R.region_grid()) == 7 and R.region_centre() == GridPoint(1.0, None)
    assert R.region_lambda(GridPoint(1.0, None)) == 100.0 == K.REGION_LAMBDA_CENTRE
    assert R.region_lambda(SimpleNamespace(level=30.0, ratio=None)) == 3000.0
    with pytest.raises(RouteRefusal):
        R.region_lambda(GridPoint(2.0, None))
    with pytest.raises(RouteRefusal):
        R.region_lambda(GridPoint(1.0, 0.5))


def test_region_cap_units_is_the_split_rule():
    units = tuple("u%03d" % i for i in range(30))
    rows = {u: 10 + (i % 4) for i, u in enumerate(units)}
    for budget in (10 ** 6, 200, 60, 13):
        assert R.region_cap_units(units, rows, budget) == SP.region_cap_units(units, rows, budget)
    with pytest.raises(SP.SplitRefusal):
        R.region_cap_units(units, rows, 5)                            # one unit exceeds the budget


# ------------------------------------------------------------------------------ synthetic group
class FakeStore(object):
    """In-memory stand-in for fit/tables.TreeAnswerStore: every tree's float32 answer per row key, the
    rows' own group's trees left out (as the store does). ``lie_group`` reports another group."""

    def __init__(self, tables, row_group, tree_group, lie_group=None):
        self.tables = {k: np.asarray(v, np.float32) for k, v in tables.items()}
        self.row_group = np.asarray(row_group, dtype=object)
        self.tree_group = np.asarray(tree_group, dtype=object)
        self.lie_group = lie_group
        self.bank_fingerprint = "fake-bank"
        self.calls = []

    @property
    def n_trees(self):
        return int(self.tree_group.size)

    def own_columns(self, group):
        return np.flatnonzero(self.tree_group == group).astype(np.int64)

    def unit_view(self, row_keys, table_kind):
        keys = np.asarray(row_keys, dtype=np.int64)
        self.calls.append((table_kind, keys.size))
        groups = sorted(set(self.row_group[keys].tolist()))
        assert len(groups) == 1, groups
        g = groups[0]
        idx = np.flatnonzero(self.tree_group != g)
        vals = self.tables[table_kind][keys][:, idx].copy()
        return SimpleNamespace(values=vals, tree_index=idx.astype(np.int64), group=self.lie_group or g,
                               kind=table_kind)


TREE_GROUP = ["g_a"] * 20 + ["g_b"] * 16 + ["g_c"] * 8 + ["g_t"] * 12
BLOCKS = {"g_a": ("g_a",), "g_b": ("g_b",), "g_c": ("g_c", "g_t"), "g_t": ("g_c", "g_t")}


def make_group(n_units=40, cut=10, score_steps=(11, 12), scored_every=4, seed=0, short=None,
               link_shift=0.0):
    """One group 'g_t' of bank units u000.. with fit rows at steps 0..cut (unit i starts at step i % 3,
    so the units hold 9-11 fit rows) and score rows after the cut for every scored_every-th unit.
    Normals are each unit's mean link(y) over ALL its fit rows (R15, one season key). Returns
    (RegionRows, store, tree_columns, arrays)."""
    rs = np.random.RandomState(seed)
    units = ["u%03d" % i for i in range(n_units)]
    scored = tuple(units[::scored_every])
    level = rs.rand(n_units)
    fit_u, fit_t, fit_y, keys = [], [], [], []
    sc_u, sc_t, sc_k = [], [], []
    key = 0
    row_group = []
    tree_ans = []
    ntree = len(TREE_GROUP)
    w_true = rs.normal(0, 0.3, ntree)
    for i, u in enumerate(units):
        start = i % 3
        steps = list(range(start, cut + 1))
        if short is not None and u in short:
            steps = steps[-2:]
        for t in steps:
            a = rs.rand(ntree)
            tree_ans.append(a)
            fit_u.append(u)
            fit_t.append(t)
            fit_y.append(level[i] + 0.2 * (a @ w_true) / ntree + rs.normal(0, 0.05) + link_shift)
            keys.append(key)
            row_group.append("g_t")
            key += 1
        if u in scored:
            for t in score_steps:
                tree_ans.append(rs.rand(ntree))
                sc_u.append(u)
                sc_t.append(t)
                sc_k.append(key)
                row_group.append("g_t")
                key += 1
    fit_u = np.array(fit_u, dtype=object)
    fit_y = np.array(fit_y)
    norm = {u: float(fit_y[fit_u == u].mean()) for u in units}
    sc_u = np.array(sc_u, dtype=object)
    A = np.array(tree_ans, dtype=np.float32)
    store = FakeStore({"plain": A, "corrector": A * np.float32(1.5) + np.float32(0.01)}, row_group, TREE_GROUP)
    cols = RK.own_block_tree_columns(TREE_GROUP, BLOCKS)
    rows = R.RegionRows(cut=cut, group="g_t", fit_units=tuple(units), scored_units=scored,
                        fit_unit=fit_u, fit_time=np.array(fit_t, dtype=np.int64), fit_y=fit_y,
                        fit_normal=np.array([norm[u] for u in fit_u]), fit_keys=np.array(keys, dtype=np.int64),
                        score_unit=sc_u, score_time=np.array(sc_t, dtype=np.int64),
                        score_normal=np.array([norm[u] for u in sc_u]),
                        score_keys=np.array(sc_k, dtype=np.int64), score_rows=np.arange(len(sc_u)) + 100)
    return rows, store, cols, {"A": A, "norm": norm}


def _replace(rows, **kw):
    d = dict(rows.__dict__)
    d.update(kw)
    return R.RegionRows(**d)


def _direct(rows, store, table_kind, kept_units, lam):
    """The same solve done by hand: kept rows, the mask (drop g_c and g_t), the solver functions."""
    A = store.tables[table_kind]
    allowed = np.flatnonzero(~np.isin(np.array(TREE_GROUP, dtype=object), ["g_c", "g_t"]))
    keep = np.isin(rows.fit_unit, np.array(kept_units, dtype=object))
    T = A[rows.fit_keys[keep]][:, allowed]
    gram = R.region_gram(T)
    fit = R.region_ridge(gram, rows.fit_y[keep], lam, rows.fit_normal[keep])
    return R.region_predict(fit, A[rows.score_keys][:, allowed], rows.score_normal)


# ------------------------------------------------------------------------------ 3. the kernel
def test_kernel_every_level_matches_the_direct_solve_and_trees_off_is_the_normal():
    rows, store, cols, _ = make_group()
    out = R._route_region_grid(rows, store, "plain", cols, TOL)
    assert isinstance(out, RouteOutput)
    assert out.predictions.shape == (rows.score_unit.size, 7)
    assert out.grid == R.region_grid()
    assert np.array_equal(out.row_positions, rows.score_rows)
    assert out.n_units_fitted == 40 and out.n_units_fallback == 0
    for j, p in enumerate(R.region_grid()):
        want = _direct(rows, store, "plain", rows.fit_units, R.region_lambda(p))
        assert out.predictions[:, j].tobytes() == want.tobytes()
    assert np.max(np.abs(out.trees_off - rows.score_normal)) < TOL
    assert not np.allclose(out.predictions[:, 0], out.predictions[:, -1])


def test_kernel_at_one_level_is_the_grid_column():
    rows, store, cols, _ = make_group(seed=1)
    grid = R._route_region_grid(rows, store, "corrector", cols, TOL)
    for j in (0, 2, 6):
        at = R._route_region_at(rows, store, "corrector", cols, R.region_grid()[j], TOL)
        assert at.predictions.shape == (rows.score_unit.size, 1)
        assert at.predictions[:, 0].tobytes() == grid.predictions[:, j].tobytes()
        assert at.trees_off.tobytes() == grid.trees_off.tobytes()
    with pytest.raises(RouteRefusal):
        R._route_region_at(rows, store, "plain", cols, GridPoint(2.0, None), TOL)


def test_the_cap_keeps_evenly_spaced_whole_units_and_scores_units_outside_it(monkeypatch):
    rows, store, cols, _ = make_group(seed=2)
    counts = {u: int((rows.fit_unit == u).sum()) for u in rows.fit_units}
    monkeypatch.setattr(K, "REGION_ROUTER_ROW_BUDGET", 150)
    kept = SP.region_cap_units(rows.fit_units, counts, 150)
    assert 1 < len(kept) < len(rows.fit_units)
    assert sum(counts[u] for u in kept) <= 150
    out = R._route_region_grid(rows, store, "plain", cols, TOL)
    assert out.n_units_fitted == len(kept)
    want = _direct(rows, store, "plain", kept, R.region_lambda(R.region_centre()))
    assert out.predictions[:, 2].tobytes() == want.tobytes()
    outside = sorted(set(rows.scored_units) - set(kept))
    assert outside, "the test needs a scored unit outside the cap"
    # trees-off = each scored unit's OWN normal (all its fit rows), inside the cap or not
    assert np.max(np.abs(out.trees_off - rows.score_normal)) < TOL
    assert R.region_router_design().fit_row_cap == 150


def test_the_own_overlap_block_is_dropped_and_checked_against_the_store():
    rows, store, cols, _ = make_group(seed=3)
    assert set(np.array(TREE_GROUP, dtype=object)[cols.columns_by_group["g_t"]]) == {"g_a", "g_b"}
    lying = FakeStore(store.tables, store.row_group, store.tree_group, lie_group="g_a")
    with pytest.raises(RouteGuardError):
        R._route_region_grid(rows, lying, "plain", cols, TOL)
    # a mask whose tree labels are not the store's physical groups is refused
    swapped = ["g_b" if g == "g_a" else "g_a" if g == "g_b" else g for g in TREE_GROUP]
    bad = RK.own_block_tree_columns(swapped, BLOCKS)
    with pytest.raises(RouteGuardError):
        R._route_region_grid(rows, store, "plain", bad, TOL)
    with pytest.raises(RouteRefusal):
        R._route_region_grid(rows, store, "plain", {"g_t": cols.columns_by_group["g_t"]}, TOL)
    other = RK.RouterTreeColumns(tree_group=tuple(TREE_GROUP), blocks=cols.blocks,
                                 columns_by_group={g: cols.columns_by_group[g] for g in ("g_a", "g_b")},
                                 router_groups={g: cols.router_groups[g] for g in ("g_a", "g_b")})
    with pytest.raises(RouteRefusal):
        R._route_region_grid(rows, store, "plain", other, TOL)       # g_t has no router columns


def test_trees_off_guard_fires_when_a_normal_is_not_the_units_own_mean():
    rows, store, cols, _ = make_group(seed=4)
    fn = rows.fit_normal.copy()
    fn[rows.fit_unit == "u005"] += 0.5
    with pytest.raises(RouteGuardError):
        R._route_region_grid(_replace(rows, fit_normal=fn), store, "plain", cols, TOL)
    with pytest.raises(RouteRefusal):
        R._route_region_grid(rows, store, "plain", cols, 0.0)


def test_blas_is_held_at_the_engine_thread_count_for_the_pooled_solve(monkeypatch):
    from threadpoolctl import threadpool_info
    rows, store, cols, _ = make_group(seed=5)
    seen, calls = [], []
    real_gram = R.region_gram
    real_assert = RK._assert_blas_threads

    def spy_gram(T, fp="", **kw):
        seen.append(sorted({d["num_threads"] for d in threadpool_info() if d.get("user_api") == "blas"}))
        return real_gram(T, fp, **kw)

    def spy_assert(limit, when):
        calls.append((limit, when))
        return real_assert(limit, when)

    monkeypatch.setattr(R, "region_gram", spy_gram)
    monkeypatch.setattr(RK, "_assert_blas_threads", spy_assert)
    R._route_region_grid(rows, store, "plain", cols, TOL)
    assert seen == [[int(K.BLAS_THREADS)]]
    assert calls == [(int(K.BLAS_THREADS), "entering"), (int(K.BLAS_THREADS), "leaving")]


# ------------------------------------------------------------------------------ 4. L4 shared Gram
def test_a_gram_shared_across_links_gives_the_same_bytes_and_is_bound_to_its_rows(monkeypatch):
    rows_a, store, cols, _ = make_group(seed=6)
    # a second link: other link(y) and other normals on the SAME rows (keys, units, steps)
    y_b = np.arcsinh(rows_a.fit_y * 3.0)
    norm_b = {u: float(y_b[rows_a.fit_unit == u].mean()) for u in rows_a.fit_units}
    rows_b = _replace(rows_a, fit_y=y_b, fit_normal=np.array([norm_b[u] for u in rows_a.fit_unit]),
                      score_normal=np.array([norm_b[u] for u in rows_a.score_unit]))
    gram = R.region_shared_gram(rows_a, store, "corrector", cols)
    assert gram.fingerprint
    fresh = R._route_region_grid(rows_b, store, "corrector", cols, TOL)
    n_calls = len(store.calls)
    shared = R._route_region_grid(rows_b, store, "corrector", cols, TOL, gram=gram)
    assert store.calls[n_calls:] == [("corrector", rows_b.score_keys.size)]   # score rows only
    assert shared.predictions.tobytes() == fresh.predictions.tobytes()
    assert shared.trees_off.tobytes() == fresh.trees_off.tobytes()
    at = R._route_region_at(rows_b, store, "corrector", cols, R.region_centre(), TOL, gram=gram)
    assert at.predictions[:, 0].tobytes() == fresh.predictions[:, 2].tobytes()
    with pytest.raises(RouteRefusal):
        R._route_region_grid(rows_b, store, "plain", cols, TOL, gram=gram)          # other table
    monkeypatch.setattr(K, "REGION_ROUTER_ROW_BUDGET", 150)
    with pytest.raises(RouteRefusal):
        R._route_region_grid(rows_b, store, "corrector", cols, TOL, gram=gram)      # other fit rows
    with pytest.raises(RouteRefusal):
        R._route_region_grid(rows_b, store, "corrector", cols, TOL, gram="gram")


def test_a_store_without_a_bank_fingerprint_is_refused_not_defaulted():
    """The Gram fingerprint must be tied to the bank: a store with no (or an empty, or a non-string)
    bank_fingerprint is refused by the shared Gram and by both kernels, never given a silent ''."""
    rows, store, cols, _ = make_group(seed=6)
    for bad in (None, "", 7):
        if bad is None:
            del store.bank_fingerprint
        else:
            store.bank_fingerprint = bad
        with pytest.raises(RouteRefusal, match="bank fingerprint"):
            R.region_shared_gram(rows, store, "corrector", cols)
        with pytest.raises(RouteRefusal, match="bank fingerprint"):
            R._route_region_grid(rows, store, "corrector", cols, TOL)
        with pytest.raises(RouteRefusal, match="bank fingerprint"):
            R._route_region_at(rows, store, "corrector", cols, R.region_centre(), TOL)
    # two banks give two fingerprints: a Gram built on bank A is refused on bank B's store
    store.bank_fingerprint = "bank-A"
    gram = R.region_shared_gram(rows, store, "corrector", cols)
    store.bank_fingerprint = "bank-B"
    with pytest.raises(RouteRefusal, match="shared Gram"):
        R._route_region_grid(rows, store, "corrector", cols, TOL, gram=gram)


# ------------------------------------------------------------------------------ 6. refusals
def test_kernel_refusals():
    rows, store, cols, _ = make_group(seed=7)
    ft = rows.fit_time.copy()
    ft[0] = rows.cut + 1
    with pytest.raises(RouteRefusal):
        R._route_region_grid(_replace(rows, fit_time=ft), store, "plain", cols, TOL)
    st = rows.score_time.copy()
    st[0] = rows.cut
    with pytest.raises(RouteRefusal):
        R._route_region_grid(_replace(rows, score_time=st), store, "plain", cols, TOL)
    with pytest.raises(RouteRefusal):      # a scored unit that is not a bank unit
        R._route_region_grid(_replace(rows, scored_units=rows.scored_units + ("zzz",)), store, "plain", cols, TOL)
    with pytest.raises(RouteRefusal):      # a score row of a unit outside the scored units
        R._route_region_grid(_replace(rows, scored_units=rows.scored_units[1:]), store, "plain", cols, TOL)
    with pytest.raises(RouteRefusal):      # fit rows of a unit outside the bank list
        R._route_region_grid(_replace(rows, fit_units=rows.fit_units[1:]), store, "plain", cols, TOL)
    with pytest.raises(RouteRefusal):      # unsorted bank list
        R._route_region_grid(_replace(rows, fit_units=tuple(reversed(rows.fit_units))), store, "plain", cols, TOL)
    fy = rows.fit_y.copy()
    fy[3] = np.nan
    with pytest.raises(RouteRefusal):
        R._route_region_grid(_replace(rows, fit_y=fy), store, "plain", cols, TOL)
    with pytest.raises(RouteRefusal):      # a (unit, step) fit row twice
        R._route_region_grid(_replace(rows, fit_time=np.zeros_like(rows.fit_time)), store, "plain", cols, TOL)
    with pytest.raises(RouteRefusal):
        R._route_region_grid(_replace(rows, score_rows=rows.score_rows[:-1]), store, "plain", cols, TOL)
    with pytest.raises(RouteRefusal):
        R._route_region_grid(_replace(rows, cut=10.0), store, "plain", cols, TOL)
    with pytest.raises(RouteRefusal):
        R._route_region_grid(rows, object(), "plain", cols, TOL)
    one = _replace(rows, fit_units=("u000",), scored_units=("u000",),
                   fit_unit=np.array(["u000"], dtype=object), fit_time=np.array([3]), fit_y=np.array([0.1]),
                   fit_normal=np.array([0.1]), fit_keys=np.array([0]),
                   score_unit=np.array(["u000"], dtype=object), score_time=np.array([11]),
                   score_normal=np.array([0.1]), score_keys=np.array([11]), score_rows=np.array([0]))
    with pytest.raises(RouteRefusal):
        R._route_region_grid(one, store, "plain", cols, TOL)


def test_fitcontext_wrappers_are_not_built():
    with pytest.raises(NotImplementedError):
        R.route_region(None, "g", (), None, None, None, {}, None, None, None, None)
    with pytest.raises(NotImplementedError):
        R.route_region_loro(None, "g", (), (), None, None, None, {}, None, None, None, None, None)


# ------------------------------------------------------------------------------ 5. fallback service
def test_fallback_plan_counts_flags_and_groups():
    valid = {"a1": 30, "a2": 5, "b1": 23, "b2": 24, "c1": 0}
    plan = R.fallback_plan(valid, {"a1": "A", "a2": "A", "b1": "B", "b2": "B", "c1": "C"})
    assert plan.short_units == ("a2", "b1", "c1")
    assert plan.share == pytest.approx(0.6) and plan.flagged
    assert dict(plan.by_group) == {"A": ("a2",), "B": ("b1",), "C": ("c1",)}
    assert R.fallback_units(valid) == RK.fallback_units(valid)
    ok = R.fallback_plan({"a%d" % i: 24 for i in range(40)}, {})
    assert ok.short_units == () and not ok.flagged
    with pytest.raises(RouteRefusal):
        R.fallback_plan({"a1": 3}, {})
    with pytest.raises(RouteRefusal):
        R.fallback_plan({}, {})


def test_search_fallback_level(capsys):
    grid = R.region_grid()
    mae = {p: 1.0 + abs(p.level - 3.0) for p in grid}
    assert R.search_fallback_level(mae, 10, R.region_centre()) == (GridPoint(3.0, None), False)
    ties = {p: 0.5 for p in grid}
    assert R.search_fallback_level(ties, 12, R.region_centre()) == (grid[0], False)
    got = R.search_fallback_level(mae, 9, R.region_centre())
    assert got == (R.region_centre(), True)
    assert "9 fallback unit(s)" in capsys.readouterr().out
    from treeroute.derive.shapes import GridPoint as DeriveGridPoint     # field-equal, another class
    derive_like = {DeriveGridPoint(p.level, None): v for p, v in mae.items()}
    assert R.search_fallback_level(derive_like, 10, DeriveGridPoint(1.0, None))[0] == GridPoint(3.0, None)
    with pytest.raises(RouteRefusal):
        R.search_fallback_level({p: v for p, v in list(mae.items())[:6]}, 10, R.region_centre())
    with pytest.raises(RouteRefusal):
        R.search_fallback_level(mae, 10, GridPoint(3.0, None))
    with pytest.raises(RouteRefusal):
        R.search_fallback_level(mae, -1, R.region_centre())
    with pytest.raises(RouteRefusal):
        R.search_fallback_level({**mae, grid[3]: float("nan")}, 10, R.region_centre())


def test_fallback_surface_mae_pools_rows_across_groups():
    grid = R.region_grid()
    o1 = RouteOutput(row_positions=np.arange(2), predictions=np.tile(np.arange(7.0), (2, 1)),
                     trees_off=np.zeros(2), grid=grid, n_units_fitted=1, n_units_fallback=0, n_rows_pool_fallback=0)
    o2 = RouteOutput(row_positions=np.arange(1), predictions=np.full((1, 7), 2.0), trees_off=np.zeros(1),
                     grid=grid, n_units_fitted=1, n_units_fallback=0, n_rows_pool_fallback=0)
    mae, n = R.fallback_surface_mae({"A": o1, "B": o2}, {"A": np.array([1.0, 3.0]), "B": np.array([2.0])},
                                    {"A": np.array(["a1", "a2"], dtype=object), "B": np.array(["b1"], dtype=object)},
                                    lambda z: np.clip(z, 0.0, 5.0))
    assert n == 3
    # level j predicts j on A's rows (clipped at 5) and 2 on B's row
    for j, p in enumerate(grid):
        pj = min(j, 5)
        assert mae[p] == pytest.approx((abs(1 - pj) + abs(3 - pj) + 0.0) / 3)
    with pytest.raises(RouteRefusal):
        R.fallback_surface_mae({}, {}, {}, lambda z: z)


def _per_unit_pass(rows, short):
    """The same group as a per-unit pass (the scored units; ``short`` units hold 2 fit rows)."""
    return RK.PerUnitRows(cut=rows.cut, fit_unit=rows.fit_unit, fit_time=rows.fit_time, fit_y=rows.fit_y,
                          fit_normal=rows.fit_normal, fit_context=None, fit_keys=rows.fit_keys,
                          score_unit=rows.score_unit, score_time=rows.score_time,
                          score_normal=rows.score_normal, score_context=None, score_keys=rows.score_keys,
                          score_rows=np.arange(rows.score_unit.size),
                          unit_group={u: "g_t" for u in rows.fit_units})


def test_fallback_end_to_end_fills_a_per_unit_pass(monkeypatch):
    short = ("u004", "u016")
    rows, store, cols, _ = make_group(n_units=40, cut=30, score_steps=(31, 32), scored_every=4, seed=8,
                                      short=short)
    per = RK._route_per_unit_grid(_per_unit_pass(rows, short), store, "plain", cols, 1e-6)
    counts = RK.valid_fit_rows(_per_unit_pass(rows, short))
    plan = R.fallback_plan(counts, {u: "g_t" for u in counts})
    assert plan.short_units == short and dict(plan.by_group) == {"g_t": short}
    assert per.n_units_fallback == 2
    nan_rows = np.flatnonzero(np.isnan(per.trees_off))
    assert set(rows.score_unit[nan_rows].tolist()) == set(short)
    # the fallback router: fit on every BANK unit of the group, score only the short units' rows
    sel = np.isin(rows.score_unit, np.array(short, dtype=object))
    fb_rows = _replace(rows, scored_units=short, score_unit=rows.score_unit[sel], score_time=rows.score_time[sel],
                       score_normal=rows.score_normal[sel], score_keys=rows.score_keys[sel],
                       score_rows=np.arange(rows.score_unit.size)[sel])
    bank = {"g_t": rows.fit_units}
    fb = R.route_fallback_grid({"g_t": fb_rows}, bank, plan, store, "plain", cols, TOL)
    level, used_centre = R.search_fallback_level({p: 1.0 for p in R.region_grid()}, 2, R.region_centre())
    assert used_centre and level == R.region_centre()
    filled = R.fill_fallback(per, fb, level)
    assert not np.isnan(filled.predictions).any() and not np.isnan(filled.trees_off).any()
    j = R.region_grid().index(level)
    for i in nan_rows:
        r = int(np.flatnonzero(fb["g_t"].row_positions == i)[0])
        assert np.all(filled.predictions[i] == fb["g_t"].predictions[r, j])
    keep = ~np.isnan(per.trees_off)
    assert filled.predictions[keep].tobytes() == per.predictions[keep].tobytes()
    assert filled.n_units_fallback == 2
    at = R.route_fallback_at({"g_t": fb_rows}, bank, plan, store, "plain", cols, level, TOL)
    assert at["g_t"].predictions[:, 0].tobytes() == fb["g_t"].predictions[:, j].tobytes()
    # refusals: the fallback pools the BANK units and scores exactly the short units
    with pytest.raises(RouteRefusal):
        R.route_fallback_grid({"g_t": fb_rows}, {"g_t": rows.fit_units[:-1]}, plan, store, "plain", cols, TOL)
    with pytest.raises(RouteRefusal):
        R.route_fallback_grid({"g_t": _replace(fb_rows, scored_units=short[:1],
                                               score_unit=fb_rows.score_unit[:2], score_time=fb_rows.score_time[:2],
                                               score_normal=fb_rows.score_normal[:2], score_keys=fb_rows.score_keys[:2],
                                               score_rows=fb_rows.score_rows[:2])},
                              bank, plan, store, "plain", cols, TOL)
    with pytest.raises(RouteRefusal):
        R.route_fallback_grid({}, bank, plan, store, "plain", cols, TOL)
    # fill refusals: a NaN row left, a fitted row overwritten, an unknown position, a missing level
    with pytest.raises(RouteRefusal):
        R.fill_fallback(per, {}, level)
    wrong = RouteOutput(row_positions=np.array([int(np.flatnonzero(keep)[0])]), predictions=np.zeros((1, 7)),
                        trees_off=np.zeros(1), grid=R.region_grid(), n_units_fitted=1, n_units_fallback=0,
                        n_rows_pool_fallback=0)
    with pytest.raises(RouteRefusal):
        R.fill_fallback(per, dict(fb, extra=wrong), level)
    ghost = RouteOutput(row_positions=np.array([10 ** 6]), predictions=np.zeros((1, 7)), trees_off=np.zeros(1),
                        grid=R.region_grid(), n_units_fitted=1, n_units_fallback=0, n_rows_pool_fallback=0)
    with pytest.raises(RouteRefusal):
        R.fill_fallback(per, dict(fb, extra=ghost), level)
    with pytest.raises(RouteRefusal):
        R.fill_fallback(per, at, GridPoint(3.0, None))
