"""Guard for the once-per-block finiteness scan (owner ruling C, speed: option (a) of
engine/speedproof/SPEEDPROOF_REPORT.md open item 1, "add version pins and a guard test").

The scan-once path in treeroute/fit/tables.py relies on private sklearn and sklearnex internals:
  - sklearn 1.6.1: a tree's predict() -> _validate_X_predict -> validate_data -> check_array, which
    calls the MODULE-LEVEL sklearn.utils.validation._assert_all_finite exactly once, with
    allow_nan = BaseDecisionTree._support_missing_values(X), input_name 'X' and the estimator's
    class name; sklearn's config (assume_finite) is thread-local;
  - scikit-learn-intelex 2025.10.0: patch_sklearn() replaces that module attribute with daal4py's
    _assert_all_finite (which returns at once under assume_finite, and scans small blocks with
    sklearn's code and large ones with oneDAL's), and replaces sklearn.config_context with its own,
    which sets sklearn's thread-local config; it does not replace DecisionTreeRegressor.
Every one of those facts is asserted here, plus the probe's guards G-a (byte identity), G-b (an inf
must raise in the scan, and predict under assume_finite alone does not raise, so the scan can never
be skipped) and G-c (a NaN behaves the same in both paths). If a library changes, this file fails
before any tree answer is written with the new version.

The pins live here and not in the engine, because the G-NONAMES scan refuses the sklearnex version
string in engine code (its first four digits read as a year).
"""

import inspect
import threading
from importlib import metadata

import numpy as np
import pytest

# THE PINS (SPEEDPROOF_REPORT.md, finding 1 and open item 1). sklearnex's module reports a
# placeholder __version__, so it is pinned by its distribution metadata.
PINNED = {"scikit-learn": "1.6.1", "scikit-learn-intelex": "2025.10.0"}
PATCHED_SCAN_MODULE = "daal4py.sklearn.utils.validation"
PATCHED_CONTEXT_MODULE = "sklearnex._config"
SCAN_PARAMETERS = ["X", "allow_nan", "msg_dtype", "estimator_name", "input_name"]
SMALL = (40, 8)          # 320 values: sklearnex hands it to sklearn's own scan
LARGE = (4500, 8)        # 36,000 values: oneDAL's scan (the split is at 32,768 values)


@pytest.fixture(scope="module", autouse=True)
def sklearnex_patched():
    import sklearnex

    was = sklearnex.sklearn_is_patched()
    if not was:
        sklearnex.patch_sklearn()
    yield
    if not was:
        sklearnex.unpatch_sklearn()


def _block(shape, offset=0.0):
    i = np.arange(shape[0], dtype=np.float64)[:, None]
    k = np.arange(shape[1], dtype=np.float64)[None, :]
    return (np.sin(0.011 * (i + 1.0) * (k + 1.0)) + offset).astype(np.float32)


@pytest.fixture(scope="module")
def trees():
    from sklearn.tree import DecisionTreeRegressor

    X = _block((3000, 8))
    y = (2.0 * X[:, 0] - X[:, 1] * X[:, 2] + X[:, 3] ** 2).astype(np.float64)
    out = [DecisionTreeRegressor(max_depth=8, min_samples_leaf=5, max_features=0.5,
                                 random_state=j).fit(X[j::2], y[j::2]) for j in range(6)]
    strict = DecisionTreeRegressor(max_depth=4, criterion="absolute_error",
                                   random_state=0).fit(X[:400], y[:400])
    return {"allow": out, "strict": strict}


# ------------------------------------------------------------------------------------------ pins
def test_library_versions_match_the_pins():
    import sklearn

    got = {"scikit-learn": sklearn.__version__,
           "scikit-learn-intelex": metadata.version("scikit-learn-intelex")}
    assert got == PINNED, (
        "the scan-once path was proven on %s; installed %s. Re-run the speed proof's probe "
        "(engine/speedproof/probe_finite_scan.py) and this guard on the new versions, then move "
        "the pins." % (PINNED, got))


def test_the_engine_records_the_pinned_versions():
    from treeroute.fit.tables import backend_versions

    rec = backend_versions()
    assert {k: rec[k] for k in PINNED} == PINNED
    assert rec["sklearn_patched"] is True
    assert rec["finite_scan"] == PATCHED_SCAN_MODULE + "._assert_all_finite"
    assert rec["config_context"] == PATCHED_CONTEXT_MODULE + ".config_context"


# ------------------------------------------------------------------------------------------ patch
def test_the_patch_installs_the_daal4py_scan_with_the_expected_signature():
    import sklearn.utils.validation as skval

    scan = skval._assert_all_finite
    assert scan.__module__ == PATCHED_SCAN_MODULE
    assert list(inspect.signature(scan).parameters) == SCAN_PARAMETERS
    src = inspect.getsource(scan)
    # the flag is read first, from sklearn's own thread-local config, before any scanning
    assert src.index('if _get_config()["assume_finite"]:') < src.index("X.size < 32768")
    import sys

    import sklearn._config

    assert sys.modules[scan.__module__]._get_config is sklearn._config.get_config


def test_the_patch_leaves_the_decision_tree_to_sklearn():
    import sklearn.tree
    from sklearn.tree._classes import BaseDecisionTree

    assert sklearn.tree.DecisionTreeRegressor.__module__ == "sklearn.tree._classes"
    assert sklearn.tree.DecisionTreeRegressor.predict is BaseDecisionTree.predict
    import sklearnex.dispatcher

    names = set(sklearnex.dispatcher.get_patch_map())
    assert not {n for n in names if "decision" in n.lower()}, names


def test_the_patched_config_context_sets_sklearns_thread_local_flag():
    import sklearn
    import sklearn._config

    assert sklearn.config_context.__module__ == PATCHED_CONTEXT_MODULE
    assert sklearn._config.get_config()["assume_finite"] is False
    with sklearn.config_context(assume_finite=True):
        assert sklearn._config.get_config()["assume_finite"] is True
        assert sklearn.get_config()["assume_finite"] is True
    assert sklearn._config.get_config()["assume_finite"] is False
    assert isinstance(sklearn._config._threadlocal, threading.local)


# ------------------------------------------------------------------------------------------ predict path
def test_predict_source_still_takes_the_path_the_scan_once_copies():
    from sklearn.tree._classes import BaseDecisionTree
    import sklearn.utils.validation as skval

    validate = inspect.getsource(BaseDecisionTree._validate_X_predict)
    assert "if self._support_missing_values(X):" in validate
    assert 'ensure_all_finite = "allow-nan"' in validate
    assert "ensure_all_finite=ensure_all_finite" in validate
    support = inspect.getsource(BaseDecisionTree._support_missing_values)
    for needle in ("not issparse(X)", "self.__sklearn_tags__().input_tags.allow_nan",
                   "self.monotonic_cst is None"):
        assert needle in support
    check = inspect.getsource(skval.check_array)
    assert 'allow_nan=ensure_all_finite == "allow-nan"' in check


@pytest.mark.parametrize("shape", [SMALL, LARGE])
def test_predict_calls_the_module_scan_once_with_the_arguments_the_store_passes(shape, trees,
                                                                              monkeypatch):
    import sklearn.utils.validation as skval

    from treeroute.fit import tables

    real = skval._assert_all_finite
    calls = []

    def spy(*args, **kwargs):
        calls.append((args, kwargs))
        return real(*args, **kwargs)

    monkeypatch.setattr(skval, "_assert_all_finite", spy)
    V = _block(shape)
    for tree in trees["allow"] + [trees["strict"]]:
        del calls[:]
        tree.predict(V)
        assert len(calls) == 1, calls
        args, kwargs = calls[0]
        assert np.shares_memory(args[0], V)
        expect = {"input_name": "X", "estimator_name": type(tree).__name__,
                  "allow_nan": tree._support_missing_values(V)}
        assert kwargs == expect
        del calls[:]
        tables._scan_block(V, tree._support_missing_values(V), type(tree).__name__)
        assert len(calls) == 1 and calls[0][0][0] is V and calls[0][1] == expect


def test_support_missing_values_depends_on_the_tree_not_the_rows(trees):
    from sklearn.tree import DecisionTreeRegressor

    tree = trees["allow"][0]
    assert tree._support_missing_values(_block(SMALL)) is True
    assert tree._support_missing_values(np.zeros((1, 8), np.float32)) is True
    assert tree._support_missing_values(np.asfortranarray(_block(LARGE))) is True
    assert trees["strict"]._support_missing_values(_block(SMALL)) is False
    mono = DecisionTreeRegressor(max_depth=2, monotonic_cst=[1] + [0] * 7).fit(
        _block((200, 8)), np.arange(200.0))
    assert mono._support_missing_values(_block(SMALL)) is False


# ------------------------------------------------------------------------------------------ G-a, G-b, G-c
@pytest.mark.parametrize("shape", [SMALL, LARGE])
def test_assume_finite_does_not_change_a_prediction(shape, trees):
    import sklearn

    V = _block(shape, offset=0.3)
    for tree in trees["allow"]:
        plain = tree.predict(V).astype(np.float32)
        with sklearn.config_context(assume_finite=True):
            fast = tree.predict(V).astype(np.float32)
        assert np.array_equal(plain.view(np.uint32), fast.view(np.uint32))


def _raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


@pytest.mark.parametrize("shape", [SMALL, LARGE])
def test_an_inf_raises_in_the_scan_and_in_predict_but_not_under_assume_finite_alone(shape, trees):
    import sklearn

    from treeroute.fit import tables

    V = _block(shape)
    V[shape[0] // 2, 3] = np.inf
    for tree in trees["allow"] + [trees["strict"]]:
        allow = tree._support_missing_values(V)
        assert _raises(lambda: tree.predict(V))
        assert _raises(lambda: tables._scan_block(V, allow, type(tree).__name__))

        def alone():
            with sklearn.config_context(assume_finite=True):
                tree.predict(V)

        assert not _raises(alone), "predict under assume_finite alone now raises; re-run the probe"


@pytest.mark.parametrize("shape", [SMALL, LARGE])
def test_a_nan_behaves_the_same_in_the_scan_and_in_predict(shape, trees):
    from treeroute.fit import tables

    V = _block(shape)
    V[1, 2] = np.nan
    for tree in trees["allow"] + [trees["strict"]]:
        allow = tree._support_missing_values(V)
        shipped = _raises(lambda: tree.predict(V))
        once = _raises(lambda: tables._scan_block(V, allow, type(tree).__name__))
        assert shipped == once == (not allow)


@pytest.mark.parametrize("shape", [SMALL, LARGE])
def test_assume_finite_in_one_thread_leaves_the_scan_on_in_another(shape):
    import sklearn
    import sklearn.utils.validation as skval

    V = _block(shape)
    V[-1, -1] = np.inf
    entered, release = threading.Event(), threading.Event()
    seen = {}

    def other():
        with sklearn.config_context(assume_finite=True):
            seen["flag"] = sklearn.get_config()["assume_finite"]
            seen["skipped"] = not _raises(lambda: skval._assert_all_finite(V, allow_nan=True))
            entered.set()
            release.wait(30)

    t = threading.Thread(target=other)
    t.start()
    try:
        assert entered.wait(30)
        assert sklearn.get_config()["assume_finite"] is False
        assert _raises(lambda: skval._assert_all_finite(V, allow_nan=True, input_name="X"))
    finally:
        release.set()
        t.join(30)
    assert seen == {"flag": True, "skipped": True}


# ------------------------------------------------------------------------------------------ the engine's own self-check
def test_the_engine_self_check_passes(monkeypatch):
    from treeroute.fit import tables

    monkeypatch.setitem(tables._SELF_CHECK, "passed", False)
    tables._self_check_scan_once()
    assert tables._SELF_CHECK["passed"] is True


def test_the_engine_self_check_fails_loudly_when_the_flag_leaks(monkeypatch):
    import sklearn

    from treeroute.fit import tables

    real = sklearn.get_config
    monkeypatch.setattr(sklearn, "get_config", lambda: dict(real(), assume_finite=True))
    monkeypatch.setitem(tables._SELF_CHECK, "passed", False)
    with pytest.raises(tables.ScanOnceGuardError, match="thread-local"):
        tables._self_check_scan_once()
    assert tables._SELF_CHECK["passed"] is False


def test_the_engine_self_check_fails_loudly_when_the_scan_lets_an_inf_through(monkeypatch):
    import sklearn.utils.validation as skval

    from treeroute.fit import tables

    monkeypatch.setattr(skval, "_assert_all_finite", lambda *a, **k: None)
    monkeypatch.setitem(tables._SELF_CHECK, "passed", False)
    with pytest.raises(tables.ScanOnceGuardError, match="let an inf through"):
        tables._self_check_scan_once()
