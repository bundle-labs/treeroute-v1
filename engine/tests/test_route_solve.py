"""treeroute.route.solve: the per-unit solvers moved AS-IS (plan 4.2, route/solve.py row).

The shipped functions are read from the shipped files as TEXT (ast), executed in an isolated
namespace (nothing of the legacy modules is imported, so no argv parsing, thread change or sklearn
patch), and compared BYTE FOR BYTE with the engine's versions on the same designs:
    coral_architecture.py   solve_local, _solve_local_dual
    pm25_adaptation.py      _grid_dual (ALPHA from fire_architecture.py's default)
Both regimes (primal rows >= columns, dual rows < columns), with and without context. Plus the
engine-only pieces: the reference cross-check raises, the context-free grid, the primal branch of the
grid, and a clean import (no scipy until the first solve).
"""

import ast
import json

import numpy as np
import pytest

from conftest import REPO_PARENT, run_python

CORAL = REPO_PARENT / "coral_architecture.py"
ADAPT = REPO_PARENT / "pm25_adaptation.py"
FIREA = REPO_PARENT / "fire_architecture.py"

pytestmark = pytest.mark.skipif(not (CORAL.is_file() and ADAPT.is_file() and FIREA.is_file()),
                                reason="the shipped scripts are not beside the engine")


def _function_source(path, name):
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    hits = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    assert len(hits) == 1, (path, name)
    lines = text.split("\n")
    return "\n".join(ln.rstrip("\r") for ln in lines[hits[0].lineno - 1:hits[0].end_lineno]) + "\n"


def _num_default(path, name):
    """The default of NAME = _num("--flag", default, cast) in a shipped file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name
                                                for t in node.targets):
            call = node.value
            assert isinstance(call, ast.Call) and call.func.id == "_num", name
            return ast.literal_eval(call.args[1])
    raise AssertionError("%s not found in %s" % (name, path))


def _literal(path, name):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name
                                                for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("%s not found in %s" % (name, path))


@pytest.fixture(scope="module")
def shipped():
    ns = {"np": np, "USE_DUAL": _literal(CORAL, "USE_DUAL")}
    for name in ("solve_local", "_solve_local_dual"):
        exec(compile(_function_source(CORAL, name), "coral:" + name, "exec"), ns)
    ns["ALPHA"] = _num_default(FIREA, "ALPHA")
    exec(compile(_function_source(ADAPT, "_grid_dual"), "adapt:_grid_dual", "exec"), ns)
    return ns


def _design(rows, nctx, ntree, seed, n_score=7):
    rs = np.random.RandomState(seed)
    normal = rs.normal(3.0, 1.0, rows)
    centre = normal.mean()
    ctx = rs.normal(size=(rows, nctx))
    trees = (rs.normal(size=(rows, ntree)) + 2.0).astype(np.float32).astype(np.float64)
    y = 0.8 * normal + trees[:, : max(1, ntree // 3)].mean(1) + 0.1 * rs.normal(size=rows)
    Xc = np.column_stack([np.ones(rows), normal - centre, ctx, trees])
    sn = rs.normal(3.0, 1.0, n_score)
    Xt = np.column_stack([np.ones(n_score), sn - centre, rs.normal(size=(n_score, nctx)),
                          (rs.normal(size=(n_score, ntree)) + 2.0).astype(np.float32)])
    return Xc, y, Xt


GRID = [(m, r) for m in (0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0)
        for r in (0.0625, 0.125, 0.25, 0.5, 1.0)]


def _pairs(alpha):
    # formed exactly as the source forms them: a_tree = ALPHA * m, a_ctx = ALPHA * m * r
    return [(alpha * m, alpha * m * r) for m, r in GRID]


@pytest.mark.parametrize("rows,nctx,ntree", [(60, 2, 10), (40, 2, 90), (30, 3, 300), (25, 2, 3)])
def test_solve_local_is_the_shipped_function_byte_for_byte(shipped, rows, nctx, ntree):
    from treeroute.route import solve as S

    Xc, y, Xt = _design(rows, nctx, ntree, seed=rows + ntree)
    w = np.ones(rows)
    for a_tree, a_ctx in _pairs(shipped["ALPHA"])[::4]:
        ref = shipped["solve_local"](Xc, y, w, ntree, nctx, a_tree, a_ctx)
        got = S.solve_local(Xc, y, w, ntree, nctx, a_tree, a_ctx)
        assert got.tobytes() == ref.tobytes()


def test_weighted_primal_and_dual_are_the_shipped_functions(shipped):
    from treeroute.route import solve as S

    for rows, ntree in ((80, 6), (30, 70)):
        Xc, y, _ = _design(rows, 2, ntree, seed=7 + ntree)
        w = np.linspace(0.5, 2.0, rows)
        ref = shipped["solve_local"](Xc, y, w, ntree, 2, 1.5, 0.375)
        got = S.solve_local(Xc, y, w, ntree, 2, 1.5, 0.375)
        assert got.tobytes() == ref.tobytes()


@pytest.mark.parametrize("rows,ntree", [(40, 90), (30, 300)])
def test_grid_dual_is_the_shipped_function_byte_for_byte(shipped, rows, ntree):
    from treeroute.route import solve as S

    Xc, y, Xt = _design(rows, 2, ntree, seed=11 * rows)
    ref = shipped["_grid_dual"](Xc, y, Xt, ntree, 2, GRID)
    got = S.grid_dual(Xc, y, Xt, ntree, 2, _pairs(shipped["ALPHA"]))
    assert got.tobytes() == ref.tobytes()


def test_solve_grid_dual_branch_is_the_shortcut_and_passes_its_reference_check(shipped):
    from treeroute.route import solve as S

    Xc, y, Xt = _design(40, 2, 90, seed=3)
    pairs = _pairs(shipped["ALPHA"])
    got = S.solve_grid(Xc, y, Xt, 90, 2, pairs, verify=True, unit_id="u0")
    assert got.tobytes() == S.grid_dual(Xc, y, Xt, 90, 2, pairs).tobytes()
    ref = S.reference_grid(Xc, y, Xt, 90, 2, pairs)
    assert float(np.abs(got - ref).max()) < S.GRID_REFERENCE_TOLERANCE


def test_solve_grid_primal_branch_is_solve_local_per_pair(shipped):
    from treeroute.route import solve as S

    Xc, y, Xt = _design(80, 2, 10, seed=5)
    pairs = _pairs(shipped["ALPHA"])
    got = S.solve_grid(Xc, y, Xt, 10, 2, pairs, verify=True)
    w = np.ones(80)
    for j, (a_tree, a_ctx) in enumerate(pairs):
        want = Xt @ shipped["solve_local"](Xc, y, w, 10, 2, a_tree, a_ctx)
        assert got[:, j].tobytes() == want.tobytes()


def test_the_reference_check_fails_loudly(monkeypatch):
    from treeroute.route import solve as S

    Xc, y, Xt = _design(40, 2, 90, seed=9)
    pairs = [(0.5, 0.25), (1.5, 1.5)]
    real = S.grid_dual
    monkeypatch.setattr(S, "grid_dual", lambda *a: real(*a) + 1e-6)
    with pytest.raises(S.GridReferenceError, match="unit u7"):
        S.solve_grid(Xc, y, Xt, 90, 2, pairs, verify=True, unit_id="u7")
    # unverified units take the shortcut as it comes (the source checks the first NVERIFY only)
    S.solve_grid(Xc, y, Xt, 90, 2, pairs, verify=False)


def test_context_free_grid_matches_its_reference():
    from treeroute.route import solve as S

    Xc, y, Xt = _design(30, 0, 120, seed=13)
    pairs = [(0.5 * m, 0.0) for m in (0.1, 1.0, 100.0)]
    got = S.grid_dual(Xc, y, Xt, 120, 0, pairs)
    ref = S.reference_grid(Xc, y, Xt, 120, 0, pairs)
    assert np.all(np.isfinite(got))
    assert float(np.abs(got - ref).max()) < S.GRID_REFERENCE_TOLERANCE


def test_solve_point_is_the_single_penalty_route(shipped):
    from treeroute.route import solve as S

    for rows, ntree in ((40, 90), (80, 10)):
        Xc, y, Xt = _design(rows, 2, ntree, seed=17 + rows)
        want = Xt @ shipped["solve_local"](Xc, y, np.ones(rows), ntree, 2, 1.5, 1.5)
        assert S.solve_point(Xc, y, Xt, ntree, 2, 1.5, 1.5).tobytes() == want.tobytes()


def test_solve_grid_refuses_a_design_without_trees():
    from treeroute.route import solve as S

    Xc, y, Xt = _design(40, 2, 1, seed=1)
    with pytest.raises(ValueError):
        S.solve_grid(Xc[:, :4], y, Xt[:, :4], 0, 2, [(0.5, 0.25)], verify=False)


def test_the_primal_uses_numpy_cholesky_not_scipy():
    from treeroute.route import solve as S

    src = open(S.__file__, encoding="utf-8").read()
    code = "\n".join(ln.split("#", 1)[0] for ln in src.splitlines())
    assert "np.linalg.cholesky" in code
    assert "cho_factor" not in code and "linalg.cholesky(" in code
    assert "scipy.linalg import cholesky" not in code


def test_importing_the_route_modules_loads_no_scipy_or_threadpoolctl():
    proc = run_python("""
import json, sys
import treeroute.route, treeroute.route.solve, treeroute.route.kinds
print('RESULT ' + json.dumps([m for m in ('scipy', 'threadpoolctl', 'sklearn', 'sklearnex', 'pandas')
                              if m in sys.modules]))
""")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    line = [ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT ")][-1]
    assert json.loads(line[len("RESULT "):]) == []
