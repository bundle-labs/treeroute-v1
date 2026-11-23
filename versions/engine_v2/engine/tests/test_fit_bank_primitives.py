"""R19 primitives: fit-one-tree and fit-one-corrector (G-NOKNOB signatures), out-of-bag rows, the
expected held-out share (D50) and its check (D51), and the corrector / placebo construction (D52)."""

import ast
import inspect
import io
import math
import operator
import os
import tokenize

import numpy as np
import pytest

from conftest import TREEROUTE_DIR
from treeroute import engine_constants as K
from treeroute.fit import bank as B
from treeroute.fit import correctors as C
from treeroute.fit.bank import BankRefusal


@pytest.fixture(scope="module", autouse=True)
def _keep_environment():
    """scikit-learn sets KMP_* variables when it is first imported (sklearn/__init__.py). Later tests
    start the launcher in a fresh interpreter, which refuses them, so this module puts the
    environment back as it found it. sklearn is imported inside the tests, never at collection."""
    before = dict(os.environ)
    yield
    for key in set(os.environ) - set(before):
        del os.environ[key]
    for key, value in before.items():
        if os.environ.get(key) != value:
            os.environ[key] = value


def DecisionTreeRegressor(**params):
    """The source's estimator, imported at call time (see _keep_environment)."""
    from sklearn.tree import DecisionTreeRegressor as tree_class
    return tree_class(**params)


def _data(n=300, p=20, seed=0):
    rng = np.random.RandomState(seed)  # synthetic test data only
    X = rng.normal(size=(n, p)).astype(np.float32)
    y = (X[:, 0] * 2.0 + np.sin(X[:, 1]) + 0.1 * rng.normal(size=n)).astype(np.float64)
    return X, y


def _same_tree(a, b):
    return B.tree_fingerprint(a) == B.tree_fingerprint(b)


# ---------------------------------------------------------------------------------------------------
# G-NOKNOB: the primitives take rows and a random_state VALUE, nothing else
FORBIDDEN_PARAMS = ("storage", "path", "dir", "folder", "file", "sampler", "sample", "layout",
                    "order", "formula", "seed_fn", "artefact", "artifact", "depth", "leaf",
                    "max_features", "criterion", "dtype", "n_jobs", "threads", "settings",
                    "params", "kwargs", "args")


def test_primitive_signatures_are_exactly_rows_and_a_random_state_value():
    assert list(inspect.signature(B.fit_one_tree).parameters) == ["X", "y", "row_indices",
                                                                  "random_state"]
    assert list(inspect.signature(C.fit_one_corrector).parameters) == ["X", "residual",
                                                                       "row_indices", "random_state"]
    for fn in (B.fit_one_tree, C.fit_one_corrector, B.draw_bag, B.name_seed, C.fit_corrector,
               C.fit_placebo_corrector, B.fit_donor_bank):
        for name, prm in inspect.signature(fn).parameters.items():
            assert prm.kind not in (prm.VAR_POSITIONAL, prm.VAR_KEYWORD), (fn.__name__, name)
            assert prm.default is prm.empty, (fn.__name__, name)
            assert not any(bad in name.lower() for bad in FORBIDDEN_PARAMS), (fn.__name__, name)


# The files this scan owns: the bank's own modules. tables.py (the tree-answer store) belongs to
# another build and is not scanned here.
BANK_FILES = ("__init__.py", "bank.py", "correctors.py", "pool.py")
LEGACY_SEED_NUMBERS = {7000, 700, 17}
_FOLD_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
             ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow,
             ast.LShift: operator.lshift, ast.RShift: operator.rshift, ast.BitOr: operator.or_,
             ast.BitAnd: operator.and_, ast.BitXor: operator.xor, ast.Div: operator.truediv}


def _folded(node):
    """The value of a sub-expression made only of numeric literals and arithmetic, else None."""
    if isinstance(node, ast.Constant):
        v = node.value
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = _folded(node.operand)
        return None if v is None else (-v if isinstance(node.op, ast.USub) else v)
    if isinstance(node, ast.BinOp) and type(node.op) in _FOLD_OPS:
        a, b = _folded(node.left), _folded(node.right)
        if a is None or b is None or (isinstance(node.op, (ast.Pow, ast.LShift)) and abs(b) > 256):
            return None
        try:
            return _FOLD_OPS[type(node.op)](a, b)
        except (ArithmeticError, ValueError):
            return None
    return None


def legacy_seed_numbers_in(source):
    """Every legacy seed number in the code: as a literal, or as a literal-only expression that
    evaluates to one (7 * 1000 counts as 7000). Comments and docstrings are text, not numbers."""
    tokens = {t.string for t in tokenize.generate_tokens(io.StringIO(source).readline)
              if t.type == tokenize.NUMBER}
    hits = sorted(tokens & {str(v) for v in LEGACY_SEED_NUMBERS})
    for node in ast.walk(ast.parse(source)):
        v = _folded(node)
        if v is not None and v in LEGACY_SEED_NUMBERS:
            hits.append("%s at line %d" % (v, node.lineno))
    return hits


def test_the_legacy_seed_scan_finds_literals_and_folded_expressions():
    assert legacy_seed_numbers_in("s = 7000 + e * 17 + j\n")
    assert legacy_seed_numbers_in("s = 700 + j\n")
    assert legacy_seed_numbers_in("s = 7 * 1000 + e * (10 + 7) + j\n")
    assert legacy_seed_numbers_in("s = (3500 << 1) + j\n")
    assert legacy_seed_numbers_in("s = -(-700)\n")
    assert not legacy_seed_numbers_in("# 7000 + e*17 + j in a comment\nx = 1 << 32\n")
    assert not legacy_seed_numbers_in('"""700 + j in a docstring"""\ny = 70 * 11 + e\n')


def test_engine_bank_code_holds_no_legacy_seed_formula():
    """The legacy seeds (bags 7000 + e*17 + j, trees 700 + j, correctors j) live in the harness only."""
    for name in BANK_FILES:
        path = TREEROUTE_DIR / "fit" / name
        assert path.is_file(), path
        assert legacy_seed_numbers_in(path.read_text(encoding="utf-8")) == [], name


@pytest.mark.parametrize("rs", [1.0, "7", None, True, -1, 2 ** 32, np.random.RandomState(0),
                                lambda: 700])
def test_random_state_must_be_an_integer_value(rs):
    X, y = _data()
    with pytest.raises(BankRefusal):
        B.fit_one_tree(X, y, np.arange(40), rs)
    with pytest.raises(BankRefusal):
        C.fit_one_corrector(X, y, np.arange(40), rs)


# ---------------------------------------------------------------------------------------------------
def test_fit_one_tree_uses_the_engine_constants_and_the_rows_in_order():
    X, y = _data()
    rows = B.draw_bag(len(X), 11)
    tree = B.fit_one_tree(X, y, rows, 123)
    params = tree.get_params()
    assert (params["max_depth"], params["min_samples_leaf"], params["max_features"],
            params["criterion"], params["random_state"]) == (
        K.TREE_MAX_DEPTH, K.TREE_MIN_LEAF, K.TREE_MAX_FEATURES, K.TREE_CRITERION, 123)
    assert (K.TREE_MAX_DEPTH, K.TREE_MIN_LEAF, K.TREE_MAX_FEATURES) == (8, 5, 0.1)
    # the same fit the source wrote inline (defaults otherwise)
    ref = DecisionTreeRegressor(max_depth=8, min_samples_leaf=5, max_features=0.1,
                                random_state=123).fit(X[rows], y[rows])
    assert _same_tree(tree, ref)
    assert tree.predict(X).tobytes() == ref.predict(X).tobytes()


def test_fit_one_tree_is_deterministic_and_the_random_state_matters():
    X, y = _data()
    rows = B.draw_bag(len(X), 3)
    a, b = B.fit_one_tree(X, y, rows, 9), B.fit_one_tree(X, y, rows, 9)
    assert _same_tree(a, b) and a.predict(X).tobytes() == b.predict(X).tobytes()
    assert not _same_tree(a, B.fit_one_tree(X, y, rows, 10))


def test_fit_one_tree_accepts_numpy_integer_values_and_repeated_rows():
    X, y = _data()
    rows = np.array([5, 5, 5, 7, 9] * 10, dtype=np.int32)
    tree = B.fit_one_tree(X, y, rows, np.uint32(4))
    assert tree.get_params()["random_state"] == 4 and isinstance(tree.get_params()["random_state"],
                                                                  int)


def test_fit_one_tree_refusals():
    X, y = _data()
    with pytest.raises(BankRefusal):
        B.fit_one_tree(X, y, np.array([], dtype=np.int64), 1)          # empty rows
    with pytest.raises(BankRefusal):
        B.fit_one_tree(X, y, np.array([0, len(X)]), 1)                 # outside X
    with pytest.raises(BankRefusal):
        B.fit_one_tree(X, y, np.array([0.0, 1.0]), 1)                  # not integer positions
    with pytest.raises(BankRefusal):
        B.fit_one_tree(X, y, np.array([True, False]), 1)
    y_bad = y.copy()
    y_bad[3] = np.nan
    with pytest.raises(BankRefusal) as info:
        B.fit_one_tree(X, y_bad, np.arange(10), 1)                     # non-finite label in bag
    assert "non-finite label" in str(info.value)
    B.fit_one_tree(X, y_bad, np.arange(4, 60), 1)                      # the NaN row not in the bag
    with pytest.raises(BankRefusal):
        B.fit_one_tree(X.astype(np.float64), y, np.arange(40), 1)      # X must be float32
    with pytest.raises(BankRefusal):
        B.fit_one_tree(X, y.astype(np.float32), np.arange(40), 1)      # y must be float64
    with pytest.raises(BankRefusal):
        B.fit_one_tree(X, y[:-1], np.arange(40), 1)                    # length mismatch


# ---------------------------------------------------------------------------------------------------
def test_oob_rows_within_the_group_sorted_unique():
    home = np.arange(100, 160)
    bag = home[np.array([0, 0, 5, 7, 59, 59])]
    ob = B.oob_rows(home, bag)
    assert ob.dtype == np.int64
    assert np.array_equal(ob, np.setdiff1d(home, bag))
    assert np.all(np.diff(ob) > 0) and not set(ob) & set(bag)
    assert len(ob) == 60 - 4


def test_oob_rows_refuses_a_bag_row_outside_the_group():
    with pytest.raises(BankRefusal):
        B.oob_rows(np.arange(10), np.array([1, 2, 10]))


def test_expected_oob_share_is_one_minus_one_over_n_to_the_b():
    assert B.expected_oob_share(1, 30) == 0.0
    for n, b in [(2, 30), (100, 50), (8640, 4320), (61, 30)]:
        assert B.expected_oob_share(n, b) == pytest.approx((1 - 1 / n) ** b, rel=0, abs=0)
    # near exp(-b/n) for large n, but not the same form (D50 picks (1 - 1/n)^b)
    assert abs(B.expected_oob_share(8640, 4320) - math.exp(-0.5)) < 1e-4
    with pytest.raises(BankRefusal):
        B.expected_oob_share(0, 3)
    with pytest.raises(BankRefusal):
        B.expected_oob_share(3, 0)


def test_d51_tolerance_is_five_binomial_sigmas_of_the_home_group():
    assert B.OOB_SHARE_TOLERANCE_SIGMAS == 5.0
    p, n = B.expected_oob_share(1000, 500), 1000
    assert B.oob_share_tolerance(p, n) == pytest.approx(5 * math.sqrt(p * (1 - p) / n))
    assert B.oob_share_tolerance(0.0, 1) == 0.0


def test_check_oob_share_passes_inside_and_refuses_outside_naming_every_group():
    n = {"a": 1000, "b": 60, "c": 500}
    exp = {g: B.expected_oob_share(k, B.bag_size(k)) for g, k in n.items()}
    B.check_oob_share(dict(exp), exp, n)
    tol_a = B.oob_share_tolerance(exp["a"], 1000)
    B.check_oob_share({"a": exp["a"] + 0.99 * tol_a, "b": exp["b"], "c": exp["c"]}, exp, n)
    obs = {"a": exp["a"] + 1.01 * tol_a, "b": exp["b"], "c": 0.97}  # c: the all-groups signature
    with pytest.raises(BankRefusal) as info:
        B.check_oob_share(obs, exp, n)
    msg = str(info.value)
    assert "2 group(s)" in msg and "a:" in msg and "c:" in msg and "b:" not in msg


def test_check_oob_share_refuses_mismatched_groups_or_bad_numbers():
    exp = {"a": 0.6}
    with pytest.raises(BankRefusal):
        B.check_oob_share({"a": 0.6, "b": 0.6}, exp, {"a": 10})
    with pytest.raises(BankRefusal):
        B.check_oob_share({"a": 0.6}, exp, {"b": 10})
    with pytest.raises(BankRefusal):
        B.check_oob_share({"a": float("nan")}, exp, {"a": 10})
    with pytest.raises(BankRefusal):
        B.check_oob_share({"a": 0.6}, exp, {"a": 0})


# ---------------------------------------------------------------------------------------------------
def _tree_and_oob(n=300, seed=0):
    X, y = _data(n=n, seed=seed)
    home = np.arange(n)
    bag = B.draw_bag(n, 21)
    tree = B.fit_one_tree(X, y, bag, 5)
    return X, y, tree, B.oob_rows(home, bag)


def test_fit_one_corrector_uses_the_corrector_constants():
    X, y, tree, ob = _tree_and_oob()
    r = y - tree.predict(X)
    corr = C.fit_one_corrector(X, r, ob, 77)
    params = corr.get_params()
    assert (params["max_depth"], params["min_samples_leaf"], params["max_features"],
            params["criterion"], params["random_state"]) == (
        K.CORRECTOR_MAX_DEPTH, K.CORRECTOR_MIN_LEAF, K.TREE_MAX_FEATURES, K.TREE_CRITERION, 77)
    assert (K.CORRECTOR_MAX_DEPTH, K.CORRECTOR_MIN_LEAF) == (6, 10)
    ref = DecisionTreeRegressor(max_depth=6, min_samples_leaf=10, max_features=0.1,
                                random_state=77).fit(X[ob], r[ob])
    assert _same_tree(corr, ref)


def test_fit_corrector_is_the_source_construction_on_oob_residuals():
    X, y, tree, ob = _tree_and_oob()
    corr = C.fit_corrector(tree, X, y, ob, 31)
    r = y[ob] - tree.predict(X[ob]).astype(np.float64)
    ref = DecisionTreeRegressor(max_depth=6, min_samples_leaf=10, max_features=0.1,
                                random_state=31).fit(X[ob], r)
    assert _same_tree(corr, ref)
    assert corr.predict(X).tobytes() == ref.predict(X).tobytes()


def test_placebo_is_the_residual_rolled_by_half_with_the_same_seed():
    X, y, tree, ob = _tree_and_oob()
    plac = C.fit_placebo_corrector(tree, X, y, ob, 31)
    r = y[ob] - tree.predict(X[ob]).astype(np.float64)
    ref = DecisionTreeRegressor(max_depth=6, min_samples_leaf=10, max_features=0.1,
                                random_state=31).fit(X[ob], np.roll(r, len(r) // 2))
    assert _same_tree(plac, ref)
    assert not _same_tree(plac, C.fit_corrector(tree, X, y, ob, 31))
    pair = C.fit_corrector_and_placebo(tree, X, y, ob, 31)
    assert _same_tree(pair[0], C.fit_corrector(tree, X, y, ob, 31))
    assert _same_tree(pair[1], plac)


def test_d52_too_few_oob_rows_gives_no_corrector_and_no_placebo():
    assert C.CORRECTOR_MIN_OOB_ROWS == 50
    X, y, tree, ob = _tree_and_oob()
    few = ob[:49]
    assert C.fit_corrector(tree, X, y, few, 1) is None
    assert C.fit_placebo_corrector(tree, X, y, few, 1) is None
    assert C.fit_corrector_and_placebo(tree, X, y, few, 1) == (None, None)
    assert C.fit_corrector(tree, X, y, ob[:50], 1) is not None
    assert C.fit_corrector(tree, X, y, np.array([], dtype=np.int64), 1) is None


def test_corrector_refusals():
    X, y, tree, ob = _tree_and_oob()
    y_bad = y.copy()
    y_bad[ob[3]] = np.inf
    with pytest.raises(BankRefusal):
        C.fit_corrector(tree, X, y_bad, ob, 1)
    with pytest.raises(BankRefusal):
        C.fit_placebo_corrector(tree, X, y_bad, ob, 1)
    with pytest.raises(BankRefusal):
        C.fit_corrector(tree, X, y, ob[::-1], 1)                       # must be sorted unique
    with pytest.raises(BankRefusal):
        C.fit_corrector(tree, X, y, np.concatenate([ob, ob[-1:]]), 1)
    with pytest.raises(BankRefusal):
        C.fit_one_corrector(X, y, np.array([], dtype=np.int64), 1)     # empty rows
    r = y - tree.predict(X)
    r[ob[0]] = np.nan
    with pytest.raises(BankRefusal):
        C.fit_one_corrector(X, r, ob, 1)
