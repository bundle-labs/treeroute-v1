"""treeroute.route.solve: the per-unit ridge solvers, moved AS-IS (plan 4.2, route/solve.py row).

Moved, not rewritten: every line of arithmetic below is the shipped code's, in the shipped order, so
a solve in the engine gives the same bytes as the shipped router on the same design (the harness
gate legacy_harness/router_replay.py and tests/test_route_solve.py prove it). What changed is
plumbing only:
  - the penalties arrive as numbers (a_tree, a_ctx) instead of being formed from module constants
    inside the solver. Each pair is formed by the caller exactly as the source formed it
    (a_tree = centre x level, a_ctx = a_tree x ratio), so the products are the same floats;
  - the always-on dual switch is gone (the dual runs whenever rows < columns, as it always did);
  - errors fail loudly: only numpy's LinAlgError takes the shipped lstsq fallback (the source
    caught every exception there), scipy is imported before the try, and the shared-Gram reference
    check raises GridReferenceError instead of an assert that python -O would strip;
  - the shared-Gram solve skips the context term when a design has no context column (the source
    never ran that case; a design WITH context takes the shipped lines unchanged).

Layout every solver assumes (the source's): columns [intercept, normal] (unpenalised), then nctx
context columns, then ntree tree columns. Each penalised block is trace-normalised on its OWN raw
columns (the dual takes the trace on the raw block, not the projected one; see solve_local_dual).

Cholesky is numpy's (np.linalg.cholesky); scipy is used only for the triangular solves, as shipped.
Importing this module loads numpy only; scipy loads at the first solve.

NEW, for owner review (not moved): the GLS-weighted grid and point solves at the end of the module
(solve_grid_weighted, solve_point_weighted, grid_dual_weighted). They reuse the moved lines unchanged:
the weighted primal is solve_local with the weights passed through, and the weighted shared-Gram solve
is grid_dual on the fit rows scaled by sqrt(w); solve_grid_weighted's docstring carries the derivation.
"""
# Provenance for the module: coral_architecture.py:179-254 (solve_local and _solve_local_dual, with
# the primal note "NOT scipy cho_factor -- 570x slower here"); pm25_adaptation.py:416-430 (the
# route_sweep cell body: shared-Gram grid solve in the dual regime, the reference cross-check on the
# first NVERIFY fitted cells, per-point solve_local otherwise), :447 (NVERIFY = 3), :451-481
# (_grid_dual, with s2c, s2t = ALPHA * mlt * rho * sc0, ALPHA * mlt * st0); pm25_adaptation.py:
# 385-387 (route_percell's single-penalty solve). Memory: reference_scipy_cholesky_slow.

import numpy as np

from treeroute.errors import RefusedError, TreerouteError

# origin: pm25_adaptation.py:447 (NVERIFY = 3: the first 3 fitted units of every sweep are
# re-solved with solve_local at every grid point). OWNER CONFIRMS whether it moves to C12.
NVERIFY = 3
# origin: pm25_adaptation.py:424 (assert err < 1e-8: shared-Gram grid vs solve_local, link space)
GRID_REFERENCE_TOLERANCE = 1e-8
# origin: coral_architecture.py:224 (G.flat[:: p + 1] += reg + 1e-8 in the primal)
PRIMAL_DIAGONAL_JITTER = 1e-8
# origin: coral_architecture.py:245-247 and pm25_adaptation.py:467-468 (trace floor 1e-12)
TRACE_FLOOR = 1e-12
UNPENALISED_COLUMNS = 2   # intercept and normal (the source's "o = 2")


class GridReferenceError(TreerouteError):
    """The shared-Gram grid solve disagreed with solve_local on a verified unit (fail loudly)."""


def _solve_triangular():
    from scipy.linalg import solve_triangular   # scipy's triangular solve, as shipped
    return solve_triangular


def solve_local(Xc, yc, w, ntree, nctx, a_tree, a_ctx):
    """Block-penalised weighted ridge: intercept and normal unpenalised, the context block and the
    tree block each trace-normalised on its own columns (a_ctx and a_tree times the block's mean
    diagonal). Dispatches to the dual whenever rows < columns; the primal adds a 1e-8 jitter to
    every diagonal element. Returns the coefficients."""
    if Xc.shape[0] < Xc.shape[1]:
        return solve_local_dual(Xc, yc, w, ntree, nctx, a_tree, a_ctx)
    solve_triangular = _solve_triangular()
    W = w[:, None]
    G = Xc.T @ (Xc * W)
    rhs = Xc.T @ (yc * w)
    reg = np.zeros(Xc.shape[1])
    o = UNPENALISED_COLUMNS
    if nctx:
        blk = np.arange(o, o + nctx)
        tr_ = float(np.trace(G[np.ix_(blk, blk)])) / max(nctx, 1)
        reg[blk] = a_ctx * tr_
    if ntree:
        blk = np.arange(o + nctx, o + nctx + ntree)
        tr_ = float(np.trace(G[np.ix_(blk, blk)])) / max(ntree, 1)
        reg[blk] = a_tree * tr_
    G.flat[:: G.shape[0] + 1] += reg + PRIMAL_DIAGONAL_JITTER
    try:
        L = np.linalg.cholesky(G)
        z = solve_triangular(L, rhs, lower=True)
        return solve_triangular(L.T, z, lower=False)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(G, rhs, rcond=None)[0]


def solve_local_dual(Xc, yc, w, ntree, nctx, a_tree, a_ctx):
    """The k-space form of solve_local (k = rows): the same answer, cost independent of the tree
    count. The unpenalised block is projected out; each penalised block is scaled by
    sqrt(a x trace / columns) taken on its RAW (weighted) columns, which is the primal's
    parameterisation of the penalty (the projected block would give a much smaller trace)."""
    solve_triangular = _solve_triangular()
    k = Xc.shape[0]
    o = UNPENALISED_COLUMNS
    U, P = Xc[:, :o], Xc[:, o:]
    r = np.sqrt(w)[:, None]
    Us, Ps_, ys = U * r, P * r, yc * np.sqrt(w)
    Q, _ = np.linalg.qr(Us)
    Py = ys - Q @ (Q.T @ ys)
    PP = Ps_ - Q @ (Q.T @ Ps_)
    s = np.empty(P.shape[1])
    if nctx:
        s[:nctx] = np.sqrt(a_ctx * max(float((Ps_[:, :nctx] ** 2).sum()) / max(nctx, 1), TRACE_FLOOR))
    if ntree:
        s[nctx:] = np.sqrt(a_tree * max(float((Ps_[:, nctx:] ** 2).sum()) / max(ntree, 1), TRACE_FLOOR))
    Zs = PP / s
    G = Zs @ Zs.T
    G.flat[:: k + 1] += 1.0
    try:
        L = np.linalg.cholesky(G)
        z = solve_triangular(L, Py, lower=True)
        u = solve_triangular(L.T, z, lower=False)
    except np.linalg.LinAlgError:
        u = np.linalg.lstsq(G, Py, rcond=None)[0]
    bP = (Zs.T @ u) / s
    bU = np.linalg.lstsq(Us, ys - Ps_ @ bP, rcond=None)[0]
    return np.r_[bU, bP]


def grid_dual(Xc, yc, Xt, ntree, nctx, penalties):
    """solve_local's dual path (unit weights) for every (a_tree, a_ctx) pair at once, predicting the
    rows of Xt. The projection and the two block Grams do not depend on the penalty, so they are
    built once; each pair is then a k x k Cholesky and a back-substitution. Traces are taken on the
    RAW blocks, as solve_local_dual does. Returns (rows of Xt, pairs)."""
    solve_triangular = _solve_triangular()
    o = UNPENALISED_COLUMNS
    k = Xc.shape[0]
    U, P = Xc[:, :o], Xc[:, o:]
    Q, _ = np.linalg.qr(U)
    Py = yc - Q @ (Q.T @ yc)
    PP = P - Q @ (Q.T @ P)
    Pc, Pt = PP[:, :nctx], PP[:, nctx:]
    Gc, Gt = Pc @ Pc.T, Pt @ Pt.T
    sc0 = max(float((P[:, :nctx] ** 2).sum()) / max(nctx, 1), TRACE_FLOOR)
    st0 = max(float((P[:, nctx:] ** 2).sum()) / max(ntree, 1), TRACE_FLOOR)
    out = np.empty((Xt.shape[0], len(penalties)))
    for j, (a_tree, a_ctx) in enumerate(penalties):
        s2t = a_tree * st0
        if nctx:
            s2c = a_ctx * sc0
            G = Gc / s2c + Gt / s2t
        else:
            G = Gt / s2t
        G.flat[:: k + 1] += 1.0
        try:
            L = np.linalg.cholesky(G)
            u = solve_triangular(L.T, solve_triangular(L, Py, lower=True), lower=False)
        except np.linalg.LinAlgError:
            u = np.linalg.lstsq(G, Py, rcond=None)[0]
        if nctx:
            bP = np.r_[Pc.T @ u / s2c, Pt.T @ u / s2t]
        else:
            bP = Pt.T @ u / s2t
        bU = np.linalg.lstsq(U, yc - P @ bP, rcond=None)[0]
        out[:, j] = Xt @ np.r_[bU, bP]
    return out


def reference_grid(Xc, yc, Xt, ntree, nctx, penalties):
    """solve_local at every pair, predicting the rows of Xt (the reference the shortcut is checked
    against). Unit weights, as the source."""
    w = np.ones(Xc.shape[0])
    return np.column_stack([Xt @ solve_local(Xc, yc, w, ntree, nctx, a_tree, a_ctx)
                            for a_tree, a_ctx in penalties])


def solve_grid(Xc, yc, Xt, ntree, nctx, penalties, verify, unit_id=None):
    """One unit's predictions at every grid pair (the source's sweep cell body).

    Dual regime (rows < columns): the shared-Gram solve; when ``verify`` is true (the caller sets it
    for the first NVERIFY fitted units of a sweep) every pair is re-solved with solve_local and any
    gap of GRID_REFERENCE_TOLERANCE or more raises GridReferenceError. Otherwise solve_local per
    pair. Unit weights. Returns (rows of Xt, pairs)."""
    if not ntree:
        raise ValueError("solve_grid serves tree arms; a design without tree columns has no grid")
    if Xc.shape[0] < Xc.shape[1]:
        Pk = grid_dual(Xc, yc, Xt, ntree, nctx, penalties)
        if verify:
            ref = reference_grid(Xc, yc, Xt, ntree, nctx, penalties)
            err = float(np.abs(Pk - ref).max())
            if not err < GRID_REFERENCE_TOLERANCE:
                raise GridReferenceError(
                    "shared-Gram grid solve disagrees with solve_local by %.3g on unit %s (limit "
                    "%.0e); the shortcut is not the reference solver here" %
                    (err, unit_id, GRID_REFERENCE_TOLERANCE))
        return Pk
    w = np.ones(Xc.shape[0])
    Pk = np.full((Xt.shape[0], len(penalties)), np.nan)
    for j, (a_tree, a_ctx) in enumerate(penalties):
        b = solve_local(Xc, yc, w, ntree, nctx, a_tree, a_ctx)
        Pk[:, j] = Xt @ b
    return Pk


def solve_point(Xc, yc, Xt, ntree, nctx, a_tree, a_ctx):
    """One unit's predictions at one penalty pair with solve_local (the source's single-penalty
    route: primal or dual by shape), unit weights. Returns (rows of Xt,)."""
    b = solve_local(Xc, yc, np.ones(len(yc)), ntree, nctx, a_tree, a_ctx)
    return Xt @ b


# ---------------------------------------------------------------------------------------------------
# The GLS-weighted per-unit solve (R24 GLS arms, R25 row weights). NEW FORMULA, FOR OWNER REVIEW.
#
# Everything above is moved as-is. The functions below are new: the shipped router never solved a
# weighted grid (its GLS weights went through solve_local one penalty at a time). They add no new
# arithmetic to the moved lines: the weighted primal IS solve_local with the weights passed through,
# and the weighted shared-Gram grid solve IS grid_dual on rows scaled by the square roots of the
# weights. The derivation is in solve_grid_weighted's docstring; tests/test_route_weighted.py gates it
# (all weights 1 gives the unweighted kernel's bytes; weighted results equal a brute-force weighted
# least-squares solve within 1e-10 on random cases, primal and dual, grid and point).
class WeightRefusal(RefusedError):
    """GLS row weights the weighted solve cannot take (R25): not one finite, positive number per fit
    row."""


def check_row_weights(w, n_rows):
    """R25 weights of one unit's fit rows: a 1-D array of n_rows finite, strictly positive numbers
    (weight = 1/sigma^2 after the floor, the clip and the ratio cap, so never 0). Returns float64.
    Refuses anything else (a zero weight would drop a fit row silently; a negative one has no
    least-squares meaning)."""
    arr = np.asarray(w)
    if arr.ndim != 1 or arr.dtype.kind not in "fiu" or arr.dtype == np.bool_:
        raise WeightRefusal("R25", "the row weights must be a 1-D numeric array, got shape %s dtype %s"
                            % (arr.shape, arr.dtype))
    if arr.shape[0] != int(n_rows):
        raise WeightRefusal("R25", "%d row weights for %d fit rows" % (arr.shape[0], int(n_rows)))
    arr = np.asarray(arr, dtype=np.float64)
    if arr.size and not (np.all(np.isfinite(arr)) and float(arr.min()) > 0.0):
        raise WeightRefusal("R25", "the row weights must be finite and strictly positive (%d are not)"
                            % int(np.count_nonzero(~(np.isfinite(arr) & (arr > 0)))),
                            fix="weights come from fit.weights.weights_for_rows (1/sigma^2, floored and "
                                "clipped)")
    return arr


def unit_mean_weights(w, n_rows):
    """check_row_weights, then divided by their mean over the unit's fit rows. A common factor leaves the
    exact weighted minimiser unchanged (the penalties are trace-normalised on the weighted Gram); dividing
    it out keeps solve_local's 1e-8 primal jitter at the scale it has in the unweighted solve, so equal
    weights of ANY size give the unweighted answer up to rounding. Every weight 1 has mean 1.0 exactly, so
    the weights (and the bytes) are unchanged."""
    arr = check_row_weights(w, n_rows)
    return arr / arr.mean()


def grid_dual_weighted(Xc, yc, w, Xt, ntree, nctx, penalties):
    """The shared-Gram grid solve with row weights: grid_dual on the fit rows scaled by sqrt(w) (w divided
    by its mean, unit_mean_weights; score rows unscaled). See solve_grid_weighted for the derivation. With
    every weight 1 the scaled rows are the rows themselves (x * 1.0 == x in floating point), so the bytes
    are grid_dual's."""
    r = np.sqrt(unit_mean_weights(w, Xc.shape[0]))
    return grid_dual(Xc * r[:, None], yc * r, Xt, ntree, nctx, penalties)


def reference_grid_weighted(Xc, yc, w, Xt, ntree, nctx, penalties):
    """solve_local with the row weights (divided by their mean) at every pair, predicting the rows of Xt:
    the reference the weighted shortcut is checked against."""
    w = unit_mean_weights(w, Xc.shape[0])
    return np.column_stack([Xt @ solve_local(Xc, yc, w, ntree, nctx, a_tree, a_ctx)
                            for a_tree, a_ctx in penalties])


def solve_grid_weighted(Xc, yc, w, Xt, ntree, nctx, penalties, verify, unit_id=None):
    """One unit's predictions at every grid pair with GLS row weights w (one per fit row).

    THE PROBLEM (the weighted form of the one solve_local solves; NEW, owner review):
        minimise over b   sum_i w_i (y_i - x_i b)^2  +  sum_B a_B (tr(X_B' W X_B) / n_B) |b_B|^2
    with W = diag(w), the intercept and normal columns unpenalised, each penalised block B (context,
    trees) trace-normalised on its own WEIGHTED Gram block (solve_local's G = X' W X; the primal adds
    its 1e-8 jitter to every diagonal element, as shipped). The weights are first divided by their mean
    over the unit's fit rows (unit_mean_weights): a common factor does not move the exact minimiser, and
    dividing it out keeps the jitter at its unweighted scale.
    THE DERIVATION. Put R = diag(sqrt(w)), X~ = R X, y~ = R y. Then
        sum_i w_i (y_i - x_i b)^2 = |y~ - X~ b|^2   and   tr(X_B' W X_B) = tr(X~_B' X~_B),
    so the weighted problem IS the unweighted problem on the scaled rows (X~, y~): same objective,
    same penalties, same minimiser b. Every step of the unweighted shared-Gram solve (grid_dual) then
    applies unchanged to (X~, y~): project out the unpenalised columns U~ = R U (QR), form the block
    Grams of the projected blocks, solve (I + sum_B P~_B P~_B' / s2_B) u = P~ y~ per pair, recover
    b_B = P~_B' u / s2_B and b_U by least squares on U~, where s2_B = a_B x tr(X~_B' X~_B) / n_B is
    taken on the RAW scaled block, exactly as solve_local_dual takes it on sqrt(w)-scaled columns. The
    predictions are the UNSCALED score rows times b (weights enter the fit, never the prediction).
    Hence: (1) the dual regime (rows < columns) is grid_dual on (X~, y~), and its reference check is
    solve_local with the weights (which, in that regime, is solve_local_dual on the same scaled rows);
    (2) the primal regime is solve_local with the weights passed through, the shipped weighted
    primal; (3) every weight 1 gives R = I, so the bytes are the unweighted solve's; (4) a common
    factor c on every weight scales X' W X, the traces and X' W y by c, so b does not change (the
    weighted arm with equal weights equals the unweighted arm up to rounding; G-PLUMB checks it at
    run time within the R36 tolerance).
    Dual regime: the weighted shared-Gram solve; when ``verify`` is true every pair is re-solved with
    solve_local and a gap of GRID_REFERENCE_TOLERANCE or more raises GridReferenceError. Primal
    regime: solve_local with the weights per pair. Returns (rows of Xt, pairs)."""
    if not ntree:
        raise ValueError("solve_grid_weighted serves tree arms; a design without tree columns has no grid")
    w = check_row_weights(w, Xc.shape[0])          # each path below divides by the mean once
    if Xc.shape[0] < Xc.shape[1]:
        Pk = grid_dual_weighted(Xc, yc, w, Xt, ntree, nctx, penalties)
        if verify:
            ref = reference_grid_weighted(Xc, yc, w, Xt, ntree, nctx, penalties)
            err = float(np.abs(Pk - ref).max())
            if not err < GRID_REFERENCE_TOLERANCE:
                raise GridReferenceError(
                    "weighted shared-Gram grid solve disagrees with solve_local by %.3g on unit %s "
                    "(limit %.0e); the shortcut is not the reference solver here" %
                    (err, unit_id, GRID_REFERENCE_TOLERANCE))
        return Pk
    w = unit_mean_weights(w, Xc.shape[0])
    Pk = np.full((Xt.shape[0], len(penalties)), np.nan)
    for j, (a_tree, a_ctx) in enumerate(penalties):
        b = solve_local(Xc, yc, w, ntree, nctx, a_tree, a_ctx)
        Pk[:, j] = Xt @ b
    return Pk


def solve_point_weighted(Xc, yc, w, Xt, ntree, nctx, a_tree, a_ctx):
    """One unit's predictions at one penalty pair with GLS row weights: solve_local with the weights
    (primal or dual by shape, as shipped), the weights divided by their mean (unit_mean_weights). Every
    weight 1 gives solve_point's bytes."""
    b = solve_local(Xc, yc, unit_mean_weights(w, Xc.shape[0]), ntree, nctx, a_tree, a_ctx)
    return Xt @ b


__all__ = [
    "NVERIFY", "GRID_REFERENCE_TOLERANCE", "PRIMAL_DIAGONAL_JITTER", "TRACE_FLOOR",
    "UNPENALISED_COLUMNS", "GridReferenceError", "solve_local", "solve_local_dual", "grid_dual",
    "reference_grid", "solve_grid", "solve_point", "WeightRefusal", "check_row_weights", "unit_mean_weights",
    "grid_dual_weighted", "reference_grid_weighted", "solve_grid_weighted", "solve_point_weighted",
]
