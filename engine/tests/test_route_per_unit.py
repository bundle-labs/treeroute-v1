"""treeroute.route.kinds: the per-unit router kernels (plan 4.2, R12, R14-R16, R20, R26, 4.5 speedup 3;
owner rulings D and E).

1. Equivalence with the shipped router, byte for byte. The shipped route_sweep, route_percell and
   _grid_dual (pm25_adaptation.py), route_idx (pm25_forecast.py) and solve_local (coral_architecture.py)
   are read as TEXT and executed in an isolated namespace on synthetic frames; the engine kernels get
   the same rows through a small in-memory answer source and must give the same bytes (grid surface,
   single point, explicit predecessor rows). The shipped trees-off (intercept + normal + context at the
   centre penalties) is rebuilt from the engine's own design builder and solver, as the harness does.
2. Worker-count invariance (1, 3, 8 workers) and BLAS at 1 thread inside the loop.
3. Leave one region out: the whole overlap block's trees are dropped and every fit asserts it.
4. Short history: flagged, NaN, counted, never a donor-wide mean.
5. Fail loudly: every refusal and guard, including the reference check raised from a worker.
"""

import ast
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from conftest import REPO_PARENT

ADAPT = REPO_PARENT / "pm25_adaptation.py"
FORE = REPO_PARENT / "pm25_forecast.py"
CORAL = REPO_PARENT / "coral_architecture.py"
FIREA = REPO_PARENT / "fire_architecture.py"
HAVE_SHIPPED = all(p.is_file() for p in (ADAPT, FORE, CORAL, FIREA))
needs_shipped = pytest.mark.skipif(not HAVE_SHIPPED, reason="the shipped scripts are not beside the engine")

TOL = 1e-6          # the trees-off identity tolerance used by these tests (R36 stand-in)


# ------------------------------------------------------------------------------ shipped source
def _function_source(path, name):
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    hits = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    assert len(hits) == 1, (path, name)
    lines = text.split("\n")
    return "\n".join(ln.rstrip("\r") for ln in lines[hits[0].lineno - 1:hits[0].end_lineno]) + "\n"


def _assigned(path, name):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name
                                                for t in node.targets):
            v = node.value
            calls = [c for c in ast.walk(v)
                     if isinstance(c, ast.Call) and getattr(c.func, "id", None) == "_num"]
            if calls:                     # NAME = ..._num("--flag", default, cast)...: the default
                return ast.literal_eval(calls[0].args[1])
            return ast.literal_eval(v)
    raise AssertionError("%s not in %s" % (name, path))


@pytest.fixture(scope="module")
def shipped():
    ns = {"np": np, "pd": pd, "USE_DUAL": _assigned(CORAL, "USE_DUAL")}
    for name in ("solve_local", "_solve_local_dual"):
        exec(compile(_function_source(CORAL, name), "coral:" + name, "exec"), ns)
    ns.update(ALPHA=_assigned(FIREA, "ALPHA"), A_CTX=_assigned(FIREA, "A_CTX"),
              CTX=_assigned(ADAPT, "CTX"), MIN_HIST=_assigned(ADAPT, "MIN_HIST"),
              NVERIFY=_assigned(ADAPT, "NVERIFY"))
    for name in ("route_percell", "route_sweep", "_grid_dual"):
        exec(compile(_function_source(ADAPT, name), "adapt:" + name, "exec"), ns)
    pen = tuple(float(x) for x in _assigned(FORE, "PEN").split(","))
    ns.update(PAD=SimpleNamespace(solve_local=ns["solve_local"]), PEN=pen)
    exec(compile(_function_source(FORE, "route_idx"), "fore:route_idx", "exec"), ns)
    return ns


# ------------------------------------------------------------------------------ synthetic data
class FakeStore(object):
    """In-memory stand-in for fit/tables.TreeAnswerStore (unit_view, n_trees, own_columns): every
    tree's float32 answer per row key, the rows' own group's trees left out (as the store does).
    ``drop_extra`` drops more groups for a planted fault; ``lie_group`` reports another group."""

    def __init__(self, tables, row_group, tree_group, drop_extra=(), lie_group=None):
        self.tables = {k: np.asarray(v, np.float32) for k, v in tables.items()}
        self.row_group = np.asarray(row_group, dtype=object)
        self.tree_group = np.asarray(tree_group, dtype=object)
        self.drop_extra = tuple(drop_extra)
        self.lie_group = lie_group
        self.calls = 0

    @property
    def n_trees(self):
        return int(self.tree_group.size)

    def own_columns(self, group):
        return np.flatnonzero(self.tree_group == group).astype(np.int64)

    def unit_view(self, row_keys, table_kind):
        self.calls += 1
        keys = np.asarray(row_keys, dtype=np.int64)
        groups = sorted(set(self.row_group[keys].tolist()))
        assert len(groups) == 1, groups
        g = groups[0]
        drop = {g} | set(self.drop_extra)
        idx = np.flatnonzero(~np.isin(self.tree_group, np.array(sorted(drop), dtype=object)))
        vals = self.tables[table_kind][keys][:, idx].copy()
        return SimpleNamespace(values=vals, tree_index=idx.astype(np.int64),
                               group=self.lie_group or g, kind=table_kind)


def make_panel(n_units=6, fit_years=3, score_years=1, ntree=60, n_ctx_lat=True, seed=0,
               unit_groups=None, short_unit=None, tree_groups=None):
    """Frames in the shipped layout (sorted by cell, then time) plus the tree answers.

    Returns dict: hist, test (pandas, with cell, cell_id, reg, year, month, lat, y, clim), A (rows of
    hist then test, float32), tree_group."""
    rs = np.random.RandomState(seed)
    y0 = 2001
    unit_groups = unit_groups or ["grp_t"] * n_units
    tree_groups = tree_groups or ["grp_a"] * (ntree // 2) + ["grp_b"] * (ntree - ntree // 2)
    rows_h, rows_t = [], []
    for u in range(n_units):
        lat = 10.0 + 3.0 * u
        years_fit = list(range(y0, y0 + fit_years))
        months = [(yy, m) for yy in years_fit for m in range(1, 13)]
        if short_unit is not None and u == short_unit:
            months = months[-10:]
        for yy, m in months:
            rows_h.append((u, yy, m, lat))
        for yy in range(y0 + fit_years, y0 + fit_years + score_years):
            for m in range(1, 13):
                rows_t.append((u, yy, m, lat))
    cols = ["cell", "year", "month", "lat"]
    hist = pd.DataFrame(rows_h, columns=cols)
    test = pd.DataFrame(rows_t, columns=cols)
    for f in (hist, test):
        f["cell_id"] = ["c%02d" % c for c in f.cell.values]
        f["reg"] = [unit_groups[c] for c in f.cell.values]
        f["t"] = f.year.values * 12 + f.month.values
    n = len(hist) + len(test)
    base = rs.gamma(2.0, 2.0, size=(n, 1))
    A = (base + rs.normal(0.0, 0.7, size=(n, ntree))).astype(np.float32)
    season = np.concatenate([hist.month.values, test.month.values])
    cellv = np.concatenate([hist.cell.values, test.cell.values])
    y = (3.0 + np.sin(season / 1.9) + 0.3 * cellv + 0.4 * A[:, :5].mean(1)
         + rs.normal(0.0, 0.3, n))
    hist["y"] = y[:len(hist)]
    test["y"] = y[len(hist):]
    # the normal: per cell-month mean of y over the fit rows only (R15), unit mean as fallback
    s = hist[["cell", "month", "y"]].assign(ly=np.log1p(hist.y.values))
    cc, cm = s.groupby(["cell", "month"]).y.mean(), s.groupby("cell").y.mean()
    lc, lm = s.groupby(["cell", "month"]).ly.mean(), s.groupby("cell").ly.mean()
    for f in (hist, test):
        ix = f.set_index(["cell", "month"]).index
        f["clim"] = pd.Series(ix.map(cc), index=f.index).astype(float).fillna(f.cell.map(cm)).values
        f["lclim"] = pd.Series(ix.map(lc), index=f.index).astype(float).fillna(f.cell.map(lm)).values
    return {"hist": hist, "test": test, "A": A, "tree_group": tree_groups}


def engine_rows(panel, ccol="clim", yfun=lambda v: v, keys=None, cut=None, context=True):
    from treeroute.route import kinds as R

    hist, test = panel["hist"], panel["test"]
    nh, nt = len(hist), len(test)
    cut = int(hist.year.max()) if cut is None else cut
    fc = sc = None
    if context:
        Ch = np.column_stack([hist[c].values for c in ("month", "lat")]).astype(np.float64)
        Ct = np.column_stack([test[c].values for c in ("month", "lat")]).astype(np.float64)
        mu, sd = R.router_standardisation(SimpleNamespace(cut=cut, times=hist.year.values), Ch)
        fc, sc = R.standardise_context(Ch, mu, sd), R.standardise_context(Ct, mu, sd)
    fk, sk = (np.arange(nh), nh + np.arange(nt)) if keys is None else keys
    groups = dict(zip(hist.cell_id.values.tolist(), hist.reg.values.tolist()))
    groups.update(zip(test.cell_id.values.tolist(), test.reg.values.tolist()))
    return R.PerUnitRows(
        cut=cut, fit_unit=hist.cell_id.values, fit_time=hist.year.values,
        fit_y=yfun(hist.y.values.astype(np.float64)), fit_normal=hist[ccol].values.astype(np.float64),
        fit_context=fc, fit_keys=np.asarray(fk, np.int64), score_unit=test.cell_id.values,
        score_time=test.year.values, score_normal=test[ccol].values.astype(np.float64),
        score_context=sc, score_keys=np.asarray(sk, np.int64), score_rows=np.arange(nt),
        unit_group=groups)


def legacy_columns(panel, scored_groups=("grp_t",)):
    """The legacy mask: the scored groups own no tree, every group is alone in its block, so their
    routers see every tree."""
    from treeroute.route import kinds as R

    n = len(panel["tree_group"])
    groups = sorted(set(panel["tree_group"]) | set(scored_groups))
    return R.RouterTreeColumns(tree_group=tuple(panel["tree_group"]),
                               blocks=tuple((g,) for g in groups),
                               columns_by_group={g: np.arange(n, dtype=np.int64) for g in scored_groups},
                               router_groups={g: (g,) for g in scored_groups})


def store_for(panel, **kw):
    row_group = np.concatenate([panel["hist"].reg.values, panel["test"].reg.values])
    return FakeStore({"plain": panel["A"], "corrector": panel["A"] * 1.01}, row_group,
                     panel["tree_group"], **kw)


@pytest.fixture
def workers(monkeypatch):
    from treeroute.route import kinds as R

    def set_workers(n):
        monkeypatch.setattr(R, "_TEST_ONLY_ROUTER_WORKERS", n)
    return set_workers


# ------------------------------------------------------------------------------ 1. equivalence
@needs_shipped
@pytest.mark.parametrize("ntree", [60, 10])        # dual regime (NVERIFY runs) and primal regime
def test_grid_surface_is_the_shipped_route_sweep_byte_for_byte(shipped, workers, ntree):
    from treeroute.route import kinds as R

    panel = make_panel(ntree=ntree, seed=ntree)
    hist, test, A = panel["hist"], panel["test"], panel["A"]
    cut = int(hist.year.max())
    grid = [(m, r) for m in (0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0) for r in (0.0625, 0.125, 0.25, 0.5, 1.0)]
    yh = hist.y.values.astype(np.float64)
    P, P0, nfit, nfall = shipped["route_sweep"](hist, test, A, ntree, yh, -1.0, cut, grid, ccol="clim",
                                                with_off=True)
    workers(8)
    out = R._route_per_unit_grid(engine_rows(panel), store_for(panel), "plain", legacy_columns(panel), TOL)
    assert [(p.level, p.ratio) for p in out.grid] == grid
    assert out.predictions.tobytes() == P.tobytes()
    assert (out.n_units_fitted, out.n_units_fallback) == (nfit, nfall // 12)
    # the shipped trees-off (intercept + normal + context at the centre penalties), rebuilt from the
    # engine's design builder and solver on the full design, sliced as the source slices it
    rows = engine_rows(panel)
    plan, short = R.per_unit_plan(rows)
    a_tree, a_ctx = R.point_penalties(R.per_unit_centre(True), True)
    legacy0 = np.full(len(test), np.nan)
    design = R.per_unit_router_design(True)
    for unit, group, hidx, tsel in plan:
        M = rows.fit_normal[hidx]
        c = M.mean()
        Xc = R.build_column_block(design, M, rows.fit_context[hidx], A[rows.fit_keys[hidx]], c).X
        Xt = R.build_column_block(design, rows.score_normal[tsel], rows.score_context[tsel],
                                  A[rows.score_keys[tsel]], c).X
        from treeroute.route import solve as S
        b0 = S.solve_local(Xc[:, :4], rows.fit_y[hidx], np.ones(hidx.size), 0, 2, a_tree, a_ctx)
        legacy0[tsel] = Xt[:, :4] @ b0
    assert legacy0.tobytes() == P0.tobytes()
    # the engine's R16 trees-off (context dropped) equals the normal, as the shipped one does; the
    # gap is the primal's 1e-8 diagonal jitter (the golden logs 2.4e-9 for the shipped trees-off)
    assert float(np.max(np.abs(out.trees_off - test.clim.values))) < 1e-8
    assert float(np.max(np.abs(P0 - test.clim.values))) < 1e-6


@needs_shipped
@pytest.mark.parametrize("ntree", [60, 10])
def test_single_point_is_the_shipped_route_percell_byte_for_byte(shipped, workers, ntree):
    from treeroute.route import kinds as R

    panel = make_panel(ntree=ntree, seed=100 + ntree)
    hist, test, A = panel["hist"], panel["test"], panel["A"]
    cut = int(hist.year.max())
    yh = np.log1p(hist.y.values.astype(np.float64))
    workers(8)
    for pen in ((1.0, 0.5), (3.0, 1.0), (100.0, 0.0625)):
        p, nfit, nfall = shipped["route_percell"](hist, test, A, ntree, yh, -1.0, cut, pen, ccol="lclim")
        out = R._route_per_unit_at(engine_rows(panel, ccol="lclim", yfun=np.log1p), store_for(panel),
                                  "plain", legacy_columns(panel), R.GridPoint(*pen), TOL)
        assert out.predictions[:, 0].tobytes() == p.tobytes()
    # the shipped trees-off arm of the test pass: route_percell(trees_off=True), a 4-column design
    p0, _, _ = shipped["route_percell"](hist, test, None, ntree, yh, -1.0, cut, (1.0, 0.5),
                                        ccol="lclim", trees_off=True)
    rows = engine_rows(panel, ccol="lclim", yfun=np.log1p)
    plan, _ = R.per_unit_plan(rows)
    legacy = R.RouterDesign(kind=R.RouterKind.PER_UNIT, columns=(R.INTERCEPT, R.NORMAL, R.CONTEXT),
                            unpenalised=(R.INTERCEPT, R.NORMAL), centre=(), grid=(), fit_row_cap=None)
    a_tree, a_ctx = R.point_penalties(R.GridPoint(1.0, 0.5), True)
    from treeroute.route import solve as S
    got = np.full(len(test), np.nan)
    for unit, group, hidx, tsel in plan:
        M = rows.fit_normal[hidx]
        c = M.mean()
        Xc = R.build_column_block(legacy, M, rows.fit_context[hidx], None, c).X
        Xt = R.build_column_block(legacy, rows.score_normal[tsel], rows.score_context[tsel], None, c).X
        got[tsel] = S.solve_point(Xc, rows.fit_y[hidx], Xt, 0, 2, a_tree, a_ctx)
    assert got.tobytes() == p0.tobytes()


@needs_shipped
def test_explicit_predecessor_rows_are_the_shipped_route_idx(shipped, workers):
    from treeroute.route import kinds as R

    panel = make_panel(ntree=60, seed=7)
    hist, test, A = panel["hist"], panel["test"], panel["A"]
    nh = len(hist)
    # each row reads the tree answers of the row before it in the same cell (its predecessor);
    # the first row of a cell reads its own
    hrow = np.arange(nh)
    first_h = np.r_[True, hist.cell.values[1:] != hist.cell.values[:-1]]
    hrow[~first_h] -= 1
    trow = nh + np.arange(len(test))
    first_t = np.r_[True, test.cell.values[1:] != test.cell.values[:-1]]
    trow[~first_t] -= 1
    # the first test row of a cell reads the cell's last history row
    last_h = {c: i for i, c in enumerate(hist.cell.values)}
    trow[first_t] = [last_h[c] for c in test.cell.values[first_t]]
    yh = np.log1p(hist.y.values.astype(np.float64))
    p, nfit, nfall = shipped["route_idx"](hist, test, A, hrow, trow, yh, -1.0, "lclim")
    workers(8)
    pen = shipped["PEN"]
    out = R._route_per_unit_at(engine_rows(panel, ccol="lclim", yfun=np.log1p, keys=(hrow, trow)),
                              store_for(panel), "plain", legacy_columns(panel), R.GridPoint(*pen), TOL)
    assert out.predictions[:, 0].tobytes() == p.tobytes()


# ------------------------------------------------------------------------------ 2. workers, BLAS
def test_output_is_identical_for_any_worker_count(workers):
    from treeroute.route import kinds as R

    panel = make_panel(n_units=11, ntree=60, seed=3)
    outs = []
    for n in (1, 3, 8):
        workers(n)
        g = R._route_per_unit_grid(engine_rows(panel), store_for(panel), "corrector",
                                  legacy_columns(panel), TOL)
        a = R._route_per_unit_at(engine_rows(panel), store_for(panel), "plain", legacy_columns(panel),
                                R.GridPoint(3.0, 1.0), TOL)
        outs.append((g.predictions.tobytes(), g.trees_off.tobytes(), a.predictions.tobytes(),
                     a.trees_off.tobytes()))
    assert outs[0] == outs[1] == outs[2]


def test_blas_is_limited_to_one_thread_inside_the_router(workers, monkeypatch):
    from threadpoolctl import threadpool_info

    from treeroute import engine_constants as K
    from treeroute.route import kinds as R
    from treeroute.route import solve as S

    seen = []
    real = S.solve_grid

    def spy(*a, **kw):
        seen.extend(d["num_threads"] for d in threadpool_info() if d["user_api"] == "blas")
        return real(*a, **kw)

    monkeypatch.setattr(S, "solve_grid", spy)
    workers(8)
    panel = make_panel(ntree=60, seed=4)
    R._route_per_unit_grid(engine_rows(panel), store_for(panel), "plain", legacy_columns(panel), TOL)
    assert seen and set(seen) == {K.ROUTER_WORKER_BLAS_THREADS}


BLAS_CHILD = r"""
import json, os, sys
sys.path.insert(0, ENGINE)
import numpy as np
from treeroute.route import kinds as R
from treeroute.route import solve as S
scipy_before = "scipy" in sys.modules
from threadpoolctl import threadpool_info
from types import SimpleNamespace

rs = np.random.RandomState(0)
units = ["u%02d" % i for i in range(10)]
nfit, nsc, ntree = 36, 12, 80
fit_unit, score_unit = np.repeat(units, nfit), np.repeat(units, nsc)
nf, ns = fit_unit.size, score_unit.size
A = rs.normal(size=(nf + ns, ntree)).astype(np.float32)
tree_group = np.array(["ga"] * ntree, dtype=object)

class Store(object):
    n_trees = ntree
    def own_columns(self, g):
        return np.flatnonzero(tree_group == g)
    def unit_view(self, keys, kind):
        idx = np.arange(ntree, dtype=np.int64)
        return SimpleNamespace(values=A[np.asarray(keys)].copy(), tree_index=idx, group="gt", kind=kind)

season = np.tile(np.arange(12), nf // 12)
y = rs.normal(size=nf) + 0.1 * season
normal = np.zeros(nf)
for u in units:
    for s in range(12):
        m = (fit_unit == u) & (season == s)
        normal[m] = y[m].mean()
snormal = np.concatenate([normal[i * nfit:i * nfit + 12] for i in range(len(units))])
rows = R.PerUnitRows(cut=10, fit_unit=fit_unit, fit_time=np.full(nf, 10), fit_y=y, fit_normal=normal,
                     fit_context=rs.normal(size=(nf, 2)), fit_keys=np.arange(nf), score_unit=score_unit,
                     score_time=np.full(ns, 11), score_normal=snormal,
                     score_context=rs.normal(size=(ns, 2)), score_keys=nf + np.arange(ns),
                     score_rows=np.arange(ns), unit_group={u: "gt" for u in units})
cols = R.RouterTreeColumns(tree_group=tuple(tree_group), blocks=(("ga",), ("gt",)),
                           columns_by_group={"gt": np.arange(ntree)}, router_groups={"gt": ("gt",)})
seen = []
real = S.solve_grid
def spy(*a, **k):
    seen.extend((d["filepath"], d["num_threads"]) for d in threadpool_info() if d["user_api"] == "blas")
    return real(*a, **k)
S.solve_grid = spy
R._TEST_ONLY_ROUTER_WORKERS = 8
R._route_per_unit_grid(rows, Store(), "plain", cols, 1e-6)
after = [(d["filepath"], d["num_threads"]) for d in threadpool_info() if d["user_api"] == "blas"]
print(json.dumps({"scipy_before": scipy_before, "scipy_after": "scipy" in sys.modules,
                  "seen": sorted(set(map(tuple, seen))), "after": after, "cpus": os.cpu_count()}))
"""


def test_blas_is_one_thread_in_the_workers_of_a_fresh_process_that_had_not_loaded_scipy():
    """The review's probe: in a fresh, unpinned process scipy (with its own BLAS) is not loaded when
    the first router call starts. The router loads it BEFORE it enters the BLAS limit, so every BLAS
    library loaded by the end of the call ran at 1 thread inside the workers, although it runs at
    more outside the limit."""
    import json
    import os
    import subprocess
    import sys

    from conftest import ENGINE_DIR

    env = {k: v for k, v in os.environ.items()
           if k.upper() not in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                                "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")}
    code = "ENGINE = %r\n" % str(ENGINE_DIR) + BLAS_CHILD
    res = subprocess.run([sys.executable, "-c", code], cwd=str(ENGINE_DIR), env=env,
                         capture_output=True, text=True, timeout=300)
    assert res.returncode == 0, res.stderr[-3000:]
    got = json.loads(res.stdout.strip().splitlines()[-1])
    assert got["scipy_before"] is False and got["scipy_after"] is True
    inside = {path: n for path, n in got["seen"]}
    assert inside and set(inside.values()) == {1}, got["seen"]
    assert {path for path, _ in got["after"]} <= set(inside), (got["after"], got["seen"])
    if (got["cpus"] or 1) > 1:        # outside the limit the libraries run at more threads
        assert max(n for _, n in got["after"]) > 1, got["after"]


def test_the_router_stops_if_a_blas_library_escapes_the_limit(workers, monkeypatch):
    import threadpoolctl

    from treeroute.route import kinds as R

    real = threadpoolctl.threadpool_info

    def escaped():
        out = real()
        return out + [{"user_api": "blas", "internal_api": "openblas", "num_threads": 16,
                       "filepath": "late_loaded_blas.dll"}]

    monkeypatch.setattr(threadpoolctl, "threadpool_info", escaped)
    workers(3)
    panel = make_panel(ntree=20, seed=5)
    with pytest.raises(R.RouteGuardError, match="C14: entering the router loop.*late_loaded_blas"):
        R._route_per_unit_at(engine_rows(panel), store_for(panel), "plain", legacy_columns(panel),
                             R.GridPoint(1.0, 0.5), TOL)


def test_the_engine_constant_worker_count_is_used_by_default():
    from treeroute import engine_constants as K
    from treeroute.route import kinds as R

    assert R._TEST_ONLY_ROUTER_WORKERS is None
    assert R._router_workers() == K.ROUTER_WORKERS == 8
    assert K.ROUTER_WORKER_BLAS_THREADS == 1


# ------------------------------------------------------------------------------ 3. overlap blocks
def _loro_panel():
    tree_groups = ["grp_a"] * 5 + ["grp_b"] * 5 + ["grp_c"] * 5
    return make_panel(n_units=4, ntree=15, seed=21, unit_groups=["grp_a", "grp_a", "grp_c", "grp_c"],
                      tree_groups=tree_groups)


def test_the_whole_overlap_block_is_dropped_and_each_fit_matches_a_manual_solve(workers):
    from treeroute.route import kinds as R
    from treeroute.route import solve as S

    panel = _loro_panel()
    blocks = {"grp_a": ("grp_a", "grp_b"), "grp_b": ("grp_a", "grp_b"), "grp_c": ("grp_c",)}
    cols = R.own_block_tree_columns(panel["tree_group"], blocks)
    assert cols.columns_by_group["grp_a"].tolist() == list(range(10, 15))   # c's trees only
    assert cols.columns_by_group["grp_c"].tolist() == list(range(0, 10))    # a's and b's trees
    workers(8)
    rows = engine_rows(panel)
    out = R._route_per_unit_at(rows, store_for(panel), "plain", cols, R.GridPoint(1.0, 0.5), TOL)
    plan, _ = R.per_unit_plan(rows)
    design = R.per_unit_router_design(True)
    a_tree, a_ctx = R.point_penalties(R.GridPoint(1.0, 0.5), True)
    for unit, group, hidx, tsel in plan:
        use = cols.columns_by_group[group]
        M = rows.fit_normal[hidx]
        c = M.mean()
        Xc = R.build_column_block(design, M, rows.fit_context[hidx], panel["A"][rows.fit_keys[hidx]][:, use], c).X
        Xt = R.build_column_block(design, rows.score_normal[tsel], rows.score_context[tsel],
                                  panel["A"][rows.score_keys[tsel]][:, use], c).X
        want = S.solve_point(Xc, rows.fit_y[hidx], Xt, use.size, 2, a_tree, a_ctx)
        assert out.predictions[tsel, 0].tobytes() == want.tobytes()


def test_a_router_column_of_the_own_block_is_refused():
    from treeroute.errors import RefusedError
    from treeroute.route import kinds as R

    panel = _loro_panel()
    tg = tuple(panel["tree_group"])
    blocks = (("grp_a", "grp_b"), ("grp_c",))
    with pytest.raises(R.RouteGuardError, match="G-DISJOINT"):          # keeps b's trees for a
        R.RouterTreeColumns(tree_group=tg, blocks=blocks, columns_by_group={"grp_a": np.arange(5, 15)},
                            router_groups={"grp_a": ("grp_a", "grp_b")})
    with pytest.raises(RefusedError, match="split"):                     # a block split in two
        R.own_block_tree_columns(tg, {"grp_a": ("grp_a", "grp_b"), "grp_b": ("grp_b",),
                                      "grp_c": ("grp_c",)})
    with pytest.raises(RefusedError, match="split an overlap block"):    # the same, built directly
        R.RouterTreeColumns(tree_group=tg, blocks=blocks, columns_by_group={"grp_a": np.arange(5, 15)},
                            router_groups={"grp_a": ("grp_a",)})
    with pytest.raises(RefusedError, match="did you mean 'grp_a'"):      # a misspelled group
        R.router_tree_columns(tg, ("GRP_A",))
    with pytest.raises(RefusedError, match="G-DISJOINT"):                # a group missing from its block
        R.own_block_tree_columns(tg, {"grp_a": ("grp_b",)})
    with pytest.raises(R.RouteGuardError, match="unit u1 holds 2"):
        R.assert_no_own_group_column(np.array(["grp_c", "grp_a", "grp_b"], dtype=object),
                                     ("grp_a", "grp_b"), "unit u1")


def test_a_store_that_answers_from_the_wrong_table_or_misses_columns_is_refused(workers):
    from treeroute.route import kinds as R

    panel = _loro_panel()
    blocks = {"grp_a": ("grp_a", "grp_b"), "grp_b": ("grp_a", "grp_b"), "grp_c": ("grp_c",)}
    cols = R.own_block_tree_columns(panel["tree_group"], blocks)
    workers(1)
    with pytest.raises(R.RouteGuardError, match="answered from the table of group"):
        R._route_per_unit_at(engine_rows(panel), store_for(panel, lie_group="grp_b"), "plain", cols,
                            R.GridPoint(1.0, 0.5), TOL)
    with pytest.raises(R.RouteGuardError, match="does not answer"):
        R._route_per_unit_at(engine_rows(panel), store_for(panel, drop_extra=("grp_b",)), "plain", cols,
                            R.GridPoint(1.0, 0.5), TOL)
    only_ab = R.RouterTreeColumns(tree_group=cols.tree_group, blocks=cols.blocks,
                                  columns_by_group={g: cols.columns_by_group[g] for g in ("grp_a", "grp_b")},
                                  router_groups={g: cols.router_groups[g] for g in ("grp_a", "grp_b")})
    with pytest.raises(R.RouteRefusal, match="no router tree columns"):   # grp_c has no mask
        R._route_per_unit_at(engine_rows(panel), store_for(panel), "plain", only_ab,
                             R.GridPoint(1.0, 0.5), TOL)
    with pytest.raises(R.RouteGuardError, match="G-DISJOINT"):  # all trees, grp_a's own included
        legacy_columns(panel, scored_groups=("grp_a",))


def test_a_mislabelled_mask_is_refused_against_the_stores_own_trees(workers):
    """The planted fault of the review: blocks {a, b} and {c}; the mask's labels of b's and c's trees
    are swapped, so a's routers would use b's trees (block-mates). Only a's units are scored, so no
    missing column gives it away: the physical check must."""
    from treeroute.route import kinds as R

    panel = _loro_panel()
    physical = list(panel["tree_group"])                       # a x5, b x5, c x5
    swapped = ["grp_a"] * 5 + ["grp_c"] * 5 + ["grp_b"] * 5    # b <-> c in the mask only
    blocks = {"grp_a": ("grp_a", "grp_b"), "grp_b": ("grp_a", "grp_b"), "grp_c": ("grp_c",)}
    bad = R.own_block_tree_columns(swapped, blocks)
    assert bad.columns_by_group["grp_a"].tolist() == list(range(5, 10))   # physically b's trees
    rows = engine_rows(panel)
    keep = np.isin(rows.score_unit, ["c00", "c01"])            # grp_a's units only
    fkeep = np.isin(rows.fit_unit, ["c00", "c01"])
    rows_a = _replace(rows, fit_unit=rows.fit_unit[fkeep], fit_time=rows.fit_time[fkeep],
                      fit_y=rows.fit_y[fkeep], fit_normal=rows.fit_normal[fkeep],
                      fit_context=rows.fit_context[fkeep], fit_keys=rows.fit_keys[fkeep],
                      score_unit=rows.score_unit[keep], score_time=rows.score_time[keep],
                      score_normal=rows.score_normal[keep], score_context=rows.score_context[keep],
                      score_keys=rows.score_keys[keep], score_rows=np.arange(int(keep.sum())))
    workers(8)
    store = store_for(panel)
    assert list(store.tree_group) == physical
    with pytest.raises(R.RouteGuardError, match=r"disagree with the store's own trees.*grp_b.*grp_c"):
        R._route_per_unit_at(rows_a, store, "plain", bad, R.GridPoint(1.0, 0.5), TOL)
    # the correct mask routes the same rows
    good = R.own_block_tree_columns(physical, blocks)
    out = R._route_per_unit_at(rows_a, store, "plain", good, R.GridPoint(1.0, 0.5), TOL)
    assert out.n_units_fitted == 2 and np.isfinite(out.predictions).all()
    # a mask of another bank size, and a store without its own record of the trees
    short = R.own_block_tree_columns(physical[:-1], blocks)
    with pytest.raises(R.RouteGuardError, match="the mask lists 14 trees, the store's bank holds 15"):
        R._route_per_unit_at(rows_a, store, "plain", short, R.GridPoint(1.0, 0.5), TOL)

    class NoRecord(object):
        def unit_view(self, row_keys, table_kind):
            return store.unit_view(row_keys, table_kind)

    with pytest.raises(R.RouteRefusal, match="own_columns"):
        R._route_per_unit_at(rows_a, NoRecord(), "plain", good, R.GridPoint(1.0, 0.5), TOL)


ROUTE_BUILD = "D:/treeroute/route_build"
REGISTRY_DIR = "D:/treeroute/registry"


@pytest.fixture
def real_store_dir(request):
    """sklearnex patched (the store writes only then, owner ruling C) and a fresh temp folder under
    D:/treeroute/route_build for the store's memmaps, removed after the test (loudly)."""
    import gc
    import os
    import re

    import sklearnex

    if not (os.path.isdir(REGISTRY_DIR) and os.path.isdir(ROUTE_BUILD)):
        pytest.skip("the machine registry or %s is missing" % ROUTE_BUILD)
    was = sklearnex.sklearn_is_patched()
    if not was:
        sklearnex.patch_sklearn(verbose=False)
    root = os.path.join(ROUTE_BUILD, "route_tests_%d" % os.getpid())
    folder = os.path.join(root, re.sub(r"[^A-Za-z0-9_\-]", "_", request.node.name)[:80])
    os.makedirs(folder)
    try:
        yield folder
    finally:
        gc.collect()
        left = sorted(os.listdir(folder))
        for name in left:            # only files this test's store made; a live map raises here
            os.remove(os.path.join(folder, name))
        os.rmdir(folder)
        if not os.listdir(root):
            os.rmdir(root)
        if not was:
            sklearnex.unpatch_sklearn()
        assert not left, "temp files were left behind: %s" % left


def test_the_real_store_catches_a_mislabelled_mask_and_routes_the_right_one(real_store_dir, workers):
    """The review's probe with the REAL TreeAnswerStore: blocks {ga, gb} and {gc}; only ga's units
    are scored. The right mask gives the manual solve on gc's trees, byte for byte; a mask whose b
    and c labels are swapped (so ga's routers would read block-mate gb's trees) is refused."""
    from sklearn.tree import DecisionTreeRegressor

    from treeroute.fit.tables import TreeAnswerStore
    from treeroute.route import kinds as R
    from treeroute.route import solve as S
    from treeroute.runs.registry import Registry

    rs = np.random.RandomState(1)
    nfeat, nfit, nsc = 6, 36, 12
    physical = ["ga"] * 5 + ["gb"] * 5 + ["gc"] * 5
    units = ["u0", "u1"]
    fit_unit, score_unit = np.repeat(units, nfit), np.repeat(units, nsc)
    nf, ns = fit_unit.size, score_unit.size
    row_group = np.array(["ga"] * (nf + ns), dtype=object)
    V = rs.normal(size=(nf + ns, nfeat)).astype(np.float32)
    trees = []
    for j in range(15):
        t = DecisionTreeRegressor(max_depth=3, random_state=j)
        t.fit(rs.normal(size=(80, nfeat)).astype(np.float32), rs.normal(size=80))
        trees.append(t)
    season = np.tile(np.arange(12), nf // 12)
    y = rs.normal(size=nf) + 0.2 * season
    normal = np.zeros(nf)
    for u in units:
        for s in range(12):
            m = (fit_unit == u) & (season == s)
            normal[m] = y[m].mean()
    snormal = np.concatenate([normal[i * nfit:i * nfit + 12] for i in range(len(units))])
    ctx, sctx = rs.normal(size=(nf, 2)), rs.normal(size=(ns, 2))
    rows = R.PerUnitRows(cut=5, fit_unit=fit_unit, fit_time=np.full(nf, 5), fit_y=y, fit_normal=normal,
                         fit_context=ctx, fit_keys=np.arange(nf), score_unit=score_unit,
                         score_time=np.full(ns, 6), score_normal=snormal, score_context=sctx,
                         score_keys=nf + np.arange(ns), score_rows=np.arange(ns),
                         unit_group={u: "ga" for u in units})
    blocks = {"ga": ("ga", "gb"), "gb": ("ga", "gb"), "gc": ("gc",)}
    point = R.GridPoint(1.0, 0.5)
    workers(8)
    with TreeAnswerStore(trees, physical, None, None, "route_test_bank",
                         lambda ids: row_group[np.asarray(ids)], real_store_dir,
                         Registry(REGISTRY_DIR)) as store:
        store.build("ga", "plain", np.arange(nf + ns, dtype=np.int64), lambda b: V[b])
        good = R.own_block_tree_columns(physical, blocks)
        out = R._route_per_unit_at(rows, store, "plain", good, point, TOL)
        allp = np.column_stack([t.predict(V) for t in trees]).astype(np.float32)
        a_tree, a_ctx = R.point_penalties(point, True)
        design = R.per_unit_router_design(True)
        use = good.columns_by_group["ga"]
        assert use.tolist() == list(range(10, 15))
        plan, _ = R.per_unit_plan(rows)
        for unit, group, hidx, tsel in plan:
            M = normal[hidx]
            Xc = R.build_column_block(design, M, ctx[hidx], allp[hidx][:, use], M.mean()).X
            Xt = R.build_column_block(design, snormal[tsel], sctx[tsel], allp[nf + tsel][:, use],
                                      M.mean()).X
            want = S.solve_point(Xc, y[hidx], Xt, use.size, 2, a_tree, a_ctx)
            assert out.predictions[tsel, 0].tobytes() == want.tobytes()
        swapped = ["ga"] * 5 + ["gc"] * 5 + ["gb"] * 5
        bad = R.own_block_tree_columns(swapped, blocks)
        with pytest.raises(R.RouteGuardError, match="disagree with the store's own trees"):
            R._route_per_unit_at(rows, store, "plain", bad, point, TOL)


# ------------------------------------------------------------------------------ 4. short history
def test_short_history_units_are_flagged_nan_and_never_given_a_donor_mean(workers):
    from treeroute.route import kinds as R

    panel = make_panel(n_units=5, ntree=60, seed=8, short_unit=2)
    rows = engine_rows(panel)
    workers(8)
    out = R._route_per_unit_grid(rows, store_for(panel), "plain", legacy_columns(panel), TOL)
    short_rows = panel["test"].cell_id.values == "c02"
    assert np.isnan(out.predictions[short_rows]).all() and np.isnan(out.trees_off[short_rows]).all()
    assert np.isfinite(out.predictions[~short_rows]).all()
    assert (out.n_units_fitted, out.n_units_fallback) == (4, 1)
    counts = R.valid_fit_rows(rows)
    assert counts["c02"] == 10 and counts["c00"] == 36
    ids, share = R.fallback_units(counts)
    assert ids == ("c02",) and share == pytest.approx(0.2)
    assert R.fallback_share_flagged(share)


def test_a_pass_with_no_unit_to_fit_is_refused_not_returned_as_nan(workers):
    from treeroute.route import kinds as R

    panel = make_panel(n_units=2, ntree=20, seed=13)
    rows = engine_rows(panel)
    # keep only 10 fit rows per unit: every scored unit is short (R12), nothing can be routed
    keep = np.zeros(rows.fit_unit.size, dtype=bool)
    for u in np.unique(rows.fit_unit):
        keep[np.flatnonzero(rows.fit_unit == u)[-10:]] = True
    short = _replace(rows, fit_unit=rows.fit_unit[keep], fit_time=rows.fit_time[keep],
                     fit_y=rows.fit_y[keep], fit_normal=rows.fit_normal[keep],
                     fit_context=rows.fit_context[keep], fit_keys=rows.fit_keys[keep])
    workers(8)
    for call in (lambda: R._route_per_unit_grid(short, store_for(panel), "plain", legacy_columns(panel), TOL),
                 lambda: R._route_per_unit_at(short, store_for(panel), "plain", legacy_columns(panel),
                                              R.GridPoint(1.0, 0.5), TOL)):
        with pytest.raises(R.RouteRefusal, match="R12.*all short.*Tue 6 Oct"):
            call()


# ------------------------------------------------------------------------------ 5. fail loudly
def _replace(rows, **kw):
    from treeroute.route import kinds as R

    d = dict(rows.__dict__)
    d.update(kw)
    return R.PerUnitRows(**d)


def test_refusals_on_rows(workers):
    from treeroute.route import kinds as R

    panel = make_panel(ntree=20, seed=9)
    rows = engine_rows(panel)
    store, cols = store_for(panel), legacy_columns(panel)
    at = R.GridPoint(1.0, 0.5)
    workers(1)

    def refused(match, **kw):
        with pytest.raises(R.RouteRefusal, match=match):
            R._route_per_unit_at(_replace(rows, **kw), store, "plain", cols, at, TOL)

    late = rows.fit_time.copy()
    late[3] = rows.cut + 1
    refused("after the cut", fit_time=late)
    early = rows.score_time.copy()
    early[0] = rows.cut
    refused("at or before the cut", score_time=early)
    bad_y = rows.fit_y.copy()
    bad_y[5] = np.nan
    refused("R30", fit_y=bad_y)
    bad_c = rows.fit_context.copy()
    bad_c[2, 1] = np.nan
    refused("R20", fit_context=bad_c)
    refused("same context", score_context=None)
    refused("negative row key", fit_keys=np.r_[-1, rows.fit_keys[1:]])
    refused("has no group", unit_group={})
    with pytest.raises(R.RouteRefusal, match="R26"):
        R._route_per_unit_at(rows, store, "plain", cols, R.GridPoint(2.0, 0.5), TOL)
    with pytest.raises(R.RouteRefusal, match="R36"):
        R._route_per_unit_at(rows, store, "plain", cols, at, 0.0)


def test_the_trees_off_identity_is_asserted_on_every_unit(workers):
    from treeroute.route import kinds as R

    panel = make_panel(ntree=20, seed=10)
    rows = engine_rows(panel)
    workers(3)
    # a normal that is NOT the unit's season mean over its fit rows: intercept + normal no longer
    # reproduces it, and the guard must stop the run
    wrong = rows.fit_normal + np.sin(np.arange(rows.fit_normal.size))
    with pytest.raises(R.RouteGuardError, match="R16"):
        R._route_per_unit_at(_replace(rows, fit_normal=wrong), store_for(panel), "plain",
                            legacy_columns(panel), R.GridPoint(1.0, 0.5), TOL)


def test_the_reference_check_raised_in_a_worker_stops_the_run(workers, monkeypatch):
    from treeroute.route import kinds as R
    from treeroute.route import solve as S

    panel = make_panel(ntree=60, seed=11)
    real = S.grid_dual
    monkeypatch.setattr(S, "grid_dual", lambda *a: real(*a) + 1e-6)
    workers(8)
    with pytest.raises(S.GridReferenceError, match="unit c00"):
        R._route_per_unit_grid(engine_rows(panel), store_for(panel), "plain", legacy_columns(panel), TOL)


def test_only_the_first_nverify_units_are_checked(workers, monkeypatch):
    from treeroute.route import kinds as R
    from treeroute.route import solve as S

    panel = make_panel(n_units=7, ntree=60, seed=12)
    flags = []
    real = S.solve_grid

    def spy(Xc, yc, Xt, ntree, nctx, penalties, verify, unit_id=None):
        flags.append((unit_id, verify))
        return real(Xc, yc, Xt, ntree, nctx, penalties, verify, unit_id=unit_id)

    monkeypatch.setattr(S, "solve_grid", spy)
    workers(8)
    R._route_per_unit_grid(engine_rows(panel), store_for(panel), "plain", legacy_columns(panel), TOL)
    assert sorted(flags) == [("c%02d" % i, i < S.NVERIFY) for i in range(7)]
