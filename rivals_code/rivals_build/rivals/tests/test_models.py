"""T8 (the normal as a fixed offset), T9 (links and the legal clip), T10 (RF R5) on synthetic data and on flow A's
saved trial and lead files (SPEC_RIVALS.md 3.3, 3.4, 3.9).

models.fit_predict is called through toy_runs.fit_predict (the fit-set shape of BUILD_NOTES_tests.md item B3).
"""

import ast
from pathlib import Path

import numpy as np
import pytest

from rivals.tests import toy_runs as T

LINKS = ("identity", "log_c", "arcsine")
C, UB, LEGAL = 2.0, 100.0, (0.0, 100.0)
PARAMS = {"ridge": {}, "rf": {"max_features": 0.5, "min_samples_leaf": 5},
          "lgbm": {"num_leaves": 31, "min_child_samples": 20},
          "hgb_l1": {"max_leaf_nodes": 31, "min_samples_leaf": 20}}
CHECKPOINTS = {"ridge": [0.1, 1e6], "rf": [0], "lgbm": [100], "hgb_l1": [100]}


def _data(n=300, n_score=37, k=5):
    rng = np.random.default_rng(1)                      # test data only; never a model seed
    X = rng.standard_normal((n, k)).astype(np.float32)
    X[rng.random((n, k)) < 0.1] = np.nan
    Xs = rng.standard_normal((n_score, k)).astype(np.float32)
    normal = rng.uniform(0.5, 60.0, n)
    normal_s = rng.uniform(0.5, 60.0, n_score)
    normal[:7] = 0.0                                     # zero normals: log_c and arcsine at their edge
    return X, Xs, normal, normal_s


def _L(link):
    from treeroute.derive.shapes import Link
    return Link(link)


def _fwd(v, link):
    from treeroute.layer.links import link_forward
    return link_forward(np.asarray(v, dtype=np.float64), _L(link), C, UB)


def _inv(z, link):
    from treeroute.layer.links import link_inverse
    return link_inverse(np.asarray(z, dtype=np.float64), _L(link), C, UB)


# ------------------------------------------------------------------------------------------ T8
@pytest.mark.parametrize("learner", ["ridge", "rf", "lgbm", "hgb_l1"])
@pytest.mark.parametrize("link", LINKS)
def test_t8_a_zero_residual_model_returns_exactly_the_normal(learner, link):
    """y equals the normal, so link(y) - z0 is exactly 0 on every fit row: every learner's f is 0 and the
    prediction is link_inverse(z0) bit for bit (the R16 analogue: trees-off equals the normal)."""
    X, Xs, normal, normal_s = _data()
    z0, z0s = _fwd(normal, link), _fwd(normal_s, link)
    res = T.fit_predict(learner, PARAMS[learner], X, normal, z0, link, C, UB, LEGAL,
                        {"score": (Xs, z0s), "fit": (X, z0)}, CHECKPOINTS[learner])
    for name, zz, nn in (("score", z0s, normal_s), ("fit", z0, normal)):
        for ck in CHECKPOINTS[learner]:
            pre = np.asarray(res[name][ck]["pre"], dtype=np.float64)
            assert np.array_equal(pre, _inv(zz, link)), (learner, link, name, ck)
            assert np.allclose(pre, nn, rtol=1e-12, atol=1e-12)


def test_t8_tweedie_with_a_zero_raw_score_returns_max_of_normal_and_c():
    """label = max(normal, c) makes the Tweedie gradient zero at init_score = log(max(normal, c)), so the raw score
    stays at 0 and the prediction is exp(init) = max(normal, c)."""
    X, Xs, normal, normal_s = _data()
    # LightGBM keeps labels in float32: values on a 1/8 grid are exact there, so the gradient is zero up to the
    # rounding of exp(log(v)) and the raw score stays at ~1e-16
    normal, normal_s = np.round(normal * 8.0) / 8.0, np.round(normal_s * 8.0) / 8.0
    y = np.maximum(normal, C)
    res = T.fit_predict("lgbm_tweedie", dict(PARAMS["lgbm"], tweedie_variance_power=1.5), X, y, normal, "identity",
                        C, UB, LEGAL, {"score": (Xs, normal_s)}, [100])
    pre = np.asarray(res["score"][100]["pre"], dtype=np.float64)
    assert np.allclose(pre, np.maximum(normal_s, C), rtol=1e-12, atol=0.0)


# ------------------------------------------------------------------------------------------ T9
def test_t9_links_round_trip_with_the_runs_c_and_ub(table_toy):
    from treeroute.layer.links import link_forward, link_inverse

    c = table_toy.c(0)
    lo, hi = table_toy.legal()
    assert c is not None and np.isfinite(hi)
    y = np.r_[lo, hi, np.linspace(lo, hi, 1001), 1e-9, hi - 1e-9]
    for link in table_toy.links():
        back = link_inverse(link_forward(y, _L(link), c, hi), _L(link), c, hi)
        assert np.max(np.abs(back - y) / np.maximum(1.0, np.abs(y))) <= 1e-12, link


def test_t9_clipped_values_are_clip_to_legal_of_the_saved_pre_clip(table_toy, table_flow):
    from treeroute.layer.links import clip_to_legal

    legal = table_toy.legal()
    files = T.trial_pred_files(table_flow.out)
    assert files, "no trial inner_preds.parquet (item B5)"
    n_pairs = 0
    for f in files:
        frame = T.read_parquet(f)
        pres = [c for c in frame.columns if c.startswith("pre__")]
        assert pres, "%s: no pre__<checkpoint> column (item B5)" % f
        for p in pres:
            q = "pred__" + p[len("pre__"):]
            assert q in frame.columns, (f, q)
            want = clip_to_legal(frame[p].to_numpy(np.float64), legal, False)[0]
            assert np.array_equal(frame[q].to_numpy(np.float64), want), (f, q)
            n_pairs += 1
    for L in table_flow.scored_leads:
        for learner in T.learners_of(table_flow.out):
            pf = table_flow.out / ("lead_%d" % L) / ("preds_%s.parquet" % learner)
            frame = T.read_parquet(pf)
            want = clip_to_legal(frame["pre__rival_%s" % learner].to_numpy(np.float64), legal, False)[0]
            assert np.array_equal(frame["arm__rival_%s_raw" % learner].to_numpy(np.float64), want), pf
            n_pairs += 1
    assert n_pairs > 0


LEGACY = {"pm25_rivals", "pm25_rivals_data", "rivals_fc", "rivals_final", "rivals_full", "rivals_table"}


def _code_files():
    root = T.BUILD_ROOT / "rivals"
    return [p for p in sorted(root.rglob("*.py")) if "tests" not in p.relative_to(root).parts]


def test_t9_the_code_never_imports_the_legacy_rival_scripts():
    files = _code_files()
    assert files, "no rivals/*.py yet (builders A and B)"
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    assert a.name.split(".")[0] not in LEGACY, (path, node.lineno, a.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert mod.split(".")[0] not in LEGACY, (path, node.lineno, mod)
                if node.level == 0 and mod == "rivals":
                    assert all(a.name != "_clip" for a in node.names), (path, node.lineno)
            elif isinstance(node, ast.Attribute) and node.attr == "_clip":
                pytest.fail("%s:%d uses an attribute named _clip (rivals.py:145-148 caps at 1)" % (path, node.lineno))
            elif isinstance(node, ast.Call) and getattr(node.func, "id", None) in ("__import__",):
                pytest.fail("%s:%d imports by name at run time" % (path, node.lineno))


def test_t9_the_package_rivals_is_ours_not_the_legacy_script():
    import rivals
    import rivals.models
    here = Path(rivals.models.__file__).resolve()
    assert T.BUILD_ROOT.resolve() in here.parents, here
    assert getattr(rivals, "__path__", None), "rivals is a module, not the package (legacy rivals.py on sys.path?)"


# ------------------------------------------------------------------------------------------ T10 (R5)
def test_t10_a_fitted_forest_predicts_fewer_rows_than_it_was_fitted_on():
    """sklearnex integer max_samples fails at predict on fewer rows (plan R5); the fraction must not."""
    X, Xs, normal, normal_s = _data(n=400, n_score=3)
    rng = np.random.default_rng(2)
    y = np.clip(normal + rng.standard_normal(len(normal)), 0.0, 100.0)
    res = T.fit_predict("rf", PARAMS["rf"], X, y, normal, "identity", C, UB, LEGAL, {"few": (Xs, normal_s)}, [0])
    pre = np.asarray(res["few"][0]["pre"], dtype=np.float64)
    assert pre.shape == (3,) and np.isfinite(pre).all()


def test_t10_the_plain_sklearnex_fraction_predicts_fewer_rows():
    """The library fact behind R5, without the rival code: a float max_samples forest predicts 3 rows."""
    from sklearnex.ensemble import RandomForestRegressor

    X, Xs, normal, _ = _data(n=400, n_score=3)
    Xf = np.nan_to_num(X, nan=0.0)
    m = RandomForestRegressor(n_estimators=10, bootstrap=True, max_samples=0.5, random_state=0, n_jobs=2)
    m.fit(Xf, normal)
    assert m.predict(np.nan_to_num(Xs, nan=0.0)).shape == (3,)
