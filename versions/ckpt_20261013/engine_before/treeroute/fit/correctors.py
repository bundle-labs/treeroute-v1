"""Out-of-bag correctors and their placebo (plan 2.3 R19, 2.4 R24).

SCIENCE bodies for the owner-approved signatures in treeroute/_proposed/bank_recipe.py
(fit_one_corrector, fit_corrector, fit_placebo_corrector; D52 accepted: a tree with fewer than 50
out-of-bag rows gets no corrector).

The construction is the same for every package:
  residual  = y - tree(X) on the tree's out-of-bag rows (its own group's rows outside its bag);
  corrector = a depth CORRECTOR_MAX_DEPTH, min leaf CORRECTOR_MIN_LEAF tree with the bank's
              max_features (TREE_MAX_FEATURES), fitted on that residual with the corrector seed;
  placebo   = the same fit on the residual rolled by half its length (distribution kept, link to
              the rows broken), with the SAME seed. Never selectable; it guards against false
              'helps' claims (R24).
"""
# Provenance for the module: adaptation.py:454-477 (fit_correctors: ob = setdiff1d(home, inbag);
# skip under minrows = 50; r = y[ob] - t.predict(X[ob]).astype(np.float64); placebo np.roll(r,
# len(r) // 2) at :467; DecisionTreeRegressor(max_depth=6, min_samples_leaf=10, max_features=mf,
# random_state=j) at :470); pm25_adaptation.py:648-649 (mf = the bank's MF).

from typing import Any, Optional, Tuple

import numpy as np

from treeroute.engine_constants import (CORRECTOR_MAX_DEPTH, CORRECTOR_MIN_LEAF, TREE_CRITERION,
                                        TREE_MAX_FEATURES)
from treeroute.fit.bank import (SEED_MAX, BankRefusal, _tree_class, as_int_value, check_features,
                                check_rows, check_target)

# D52 (owner rulings, part A: the proposed default accepted): a tree with fewer out-of-bag rows gets
# no corrector (and no placebo corrector).
# origin: adaptation.py:454 (minrows=50). OWNER CONFIRMS: not yet in engine_constants.py (outside
# this module's write scope); it belongs beside the C13 corrector constants.
CORRECTOR_MIN_OOB_ROWS = 50

# The corrector uses the bank's max_features (contract: "max_features 10% (the source used the
# bank's max_features)").
CORRECTOR_MAX_FEATURES = TREE_MAX_FEATURES


def _fit_corrector_rows(X_rows: np.ndarray, residual_rows: np.ndarray, random_state: int) -> Any:
    """Fit one corrector tree on rows already gathered (engine constants only)."""
    tree = _tree_class()(criterion=TREE_CRITERION, max_depth=CORRECTOR_MAX_DEPTH,
                         min_samples_leaf=CORRECTOR_MIN_LEAF, max_features=CORRECTOR_MAX_FEATURES,
                         random_state=random_state)
    return tree.fit(X_rows, residual_rows)


def _check_finite_residual(r: np.ndarray, what: str) -> None:
    if not np.all(np.isfinite(r)):
        raise BankRefusal("R19", "%d of the %d %s residuals are not finite"
                          % (int(np.sum(~np.isfinite(r))), len(r), what),
                          fix="bank rows come from DonorRows, which holds valid labels only")


# Provenance: adaptation.py:470 (DecisionTreeRegressor(max_depth=6, min_samples_leaf=10,
# max_features=mf, random_state=j).fit(X[ob], r)).
def fit_one_corrector(X: np.ndarray, residual: np.ndarray, row_indices: np.ndarray,
                      random_state: int) -> Any:
    """PRIMITIVE: fit one corrector tree (depth 6, leaf 10) on given rows and residuals.

    Rule: R19. Corrector constants from the engine constants: depth CORRECTOR_MAX_DEPTH, min leaf
    CORRECTOR_MIN_LEAF, max_features the bank's TREE_MAX_FEATURES, criterion TREE_CRITERION.
    random_state is a value (name_seed(..., CORRECTOR), or a legacy value from the harness).

    Inputs: X float32; residual float64 at every row of X (only row_indices are read); row_indices
    the out-of-bag rows. Returns the fitted corrector. Refuses empty row_indices, rows outside X, a
    non-finite residual at those rows, or a random_state outside [0, 2^32 - 1].
    """
    X = check_features(X)
    residual = check_target(residual, X.shape[0], "residual")
    rows = check_rows(row_indices, X.shape[0], "row_indices")
    rs = as_int_value(random_state, "random_state", 0, SEED_MAX)
    r = residual[rows]
    _check_finite_residual(r, "corrector")
    return _fit_corrector_rows(X[rows], r, rs)


def _oob_residual(tree: Any, X: np.ndarray, y: np.ndarray, oob: Any) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """(X[oob], y[oob] - tree(X[oob])) in float64, or None when there are too few out-of-bag rows.

    The out-of-bag rows must be sorted and unique, as oob_rows returns them: the corrector is
    fitted on the rows in that order."""
    X = check_features(X)
    y = check_target(y, X.shape[0], "y")
    ob = np.asarray(oob)
    if ob.ndim != 1:
        raise BankRefusal("R19", "out-of-bag rows must be 1-D")
    if len(ob) < CORRECTOR_MIN_OOB_ROWS:
        return None
    ob = check_rows(ob, X.shape[0], "out-of-bag rows")
    if np.any(np.diff(ob) <= 0):
        raise BankRefusal("R19", "out-of-bag rows must be sorted and unique",
                          fix="take them from oob_rows(home_rows, bag_rows)")
    X_rows = X[ob]
    r = y[ob] - tree.predict(X_rows).astype(np.float64)
    _check_finite_residual(r, "out-of-bag")
    return X_rows, r


# Provenance: adaptation.py:454-470 (r = y[ob] - t.predict(X[ob]); skip trees with < 50 out-of-bag
# rows, minrows=50); D52.
def fit_corrector(tree: Any, X: np.ndarray, y: np.ndarray, oob: np.ndarray,
                  random_state: int) -> Optional[Any]:
    """Fit a tree's corrector on its out-of-bag residuals.

    Rule: R19, R24, D52. residual = y - tree(X) on the tree's out-of-bag rows, then the corrector
    fit with the corrector seed. Same construction for every package.

    Inputs: tree, the bank tree; X, y, the donor rows (DonorRows.X, DonorRows.y); oob, the tree's
    out-of-bag rows (oob_rows: sorted, unique); random_state, name_seed(group, j, CORRECTOR).
    Returns the corrector, or None when the tree has fewer than CORRECTOR_MIN_OOB_ROWS out-of-bag
    rows. Refuses non-finite residuals.
    """
    rs = as_int_value(random_state, "random_state", 0, SEED_MAX)
    got = _oob_residual(tree, X, y, oob)
    if got is None:
        return None
    X_rows, r = got
    return _fit_corrector_rows(X_rows, r, rs)


# Provenance: adaptation.py:466-467 (placebo: r = np.roll(r, len(r) // 2)); plan 2.4 R24 (placebo =
# scrambled residual, never selectable).
def fit_placebo_corrector(tree: Any, X: np.ndarray, y: np.ndarray, oob: np.ndarray,
                          random_state: int) -> Optional[Any]:
    """Fit the placebo corrector: the same construction on a scrambled residual.

    Rule: R19, R24. The residual (as in fit_corrector) is rolled by half its length, which keeps
    its distribution and breaks its link to the rows. random_state is the SAME value the real
    corrector used. Never selectable.

    Returns the placebo corrector, or None when the real one was skipped. Refuses as fit_corrector.
    """
    rs = as_int_value(random_state, "random_state", 0, SEED_MAX)
    got = _oob_residual(tree, X, y, oob)
    if got is None:
        return None
    X_rows, r = got
    return _fit_corrector_rows(X_rows, np.roll(r, len(r) // 2), rs)


def fit_corrector_and_placebo(tree: Any, X: np.ndarray, y: np.ndarray, oob: np.ndarray,
                              random_state: int) -> Tuple[Optional[Any], Optional[Any]]:
    """fit_corrector and fit_placebo_corrector with one residual computation (the bank's path).

    The two fits are exactly those of the two functions above: same rows, same residual (rolled
    for the placebo), same seed. Returns (None, None) when the tree has too few out-of-bag rows."""
    rs = as_int_value(random_state, "random_state", 0, SEED_MAX)
    got = _oob_residual(tree, X, y, oob)
    if got is None:
        return None, None
    X_rows, r = got
    return (_fit_corrector_rows(X_rows, r, rs),
            _fit_corrector_rows(X_rows, np.roll(r, len(r) // 2), rs))
