"""treeroute.route.region: the REGION router kind (plan 4.2 route/kinds.py row, region part; plan 2.2
R12, R14-R16; U-1; owner rulings A (D80-D82 as proposed), C (region-router threads), D, E (L2 rules 2-4,
L4)).

SCIENCE bodies for the owner-approved region signatures of _proposed/route_kinds.py (region_cap_units,
route_region, search_fallback_level) and the LORO addition route_region_loro (_proposed/
loro_additions.py), approved by the owner rulings file (engine/OWNER_RULINGS_*.md, sections A-F). Where
that file differs from a docstring, the rulings file wins. route/kinds.py (the per-unit kind) and
route/solve.py are not edited: this module imports their shapes, guards and the trees-off identity.

BUILT
  - The trace-normalised ridge, MOVED AS-IS (plan 4.2 route/solve.py row: "the trace-normalised
    ridge, moved"): the fit block is copied to float32 and centred on its fit-row column means (in
    float32), y is centred on its fit-row mean, the Gram of the centred block is formed in float32
    and cast to float64, lam x (trace(G) / columns + 1e-12) is added to the diagonal, numpy's
    Cholesky and two solves give w, and the intercept is ym - means @ w. Predictions are
    block @ w in float32 blocks of REGION_APPLY_BLOCK_ROWS rows plus the intercept. region_ridge
    WITHOUT a normal is the shipped ridge line for line (LEGACY mode): only the legacy-harness gate
    and the tests call it that way; the engine kernels always pass the normal.
  - U-1, the unpenalised normal column (D81, accepted as proposed): the per-unit link-matched normal
    enters UNPENALISED by projecting the intercept (the centring) and the normal out first; the
    trace normalisation is taken over the tree block only. READING (owner confirms): "the tree block
    only" is the centred tree block's trace, exactly the shipped scale, so adding the normal column
    never moves the penalty, and the fit without a normal is the shipped ridge. Closed form, with
    everything centred on the fit rows (b = T'n, the border of the tree block with the normal):
        G_p = G - b b' / n'n,   r_p = T'y - b (n'y) / n'n,   w = (G_p + lam s I)^-1 r_p,
        g = (n'y - b'w) / n'n,  prediction = T w + (ym - means @ w) + g (normal - fit-row mean).
    This is the exact minimiser of |y - a - g n - T w|^2 + lam s |w|^2 with a and g free. A normal
    that is constant on the fit rows lies in the intercept's span; its coefficient is then 0 (the
    minimum-norm solution) and the intercept carries it.
  - Shared Gram across links (L4, owner rulings E): RegionGram holds the centred fit block, its
    column means, its Gram and trace scale, and a fingerprint of (group, table kind, fit row keys,
    tree columns, bank). The Gram does not depend on the link (the fit rows of the three links are
    the same rows); only y and the normal's border change, and both are recomputed per link. A
    Gram is formed once, in one piece (never in row blocks), so a pass that reuses it gives the
    same bytes as a pass that forms its own (tests/test_route_region.py proves it); a Gram built on
    other rows, columns, table or bank is refused, and so is a store without a bank fingerprint
    (a Gram must be tied to its bank; the real TreeAnswerStore always carries one).
  - The grid (R14, R26): REGION_PENALTY_LEVELS around REGION_LAMBDA_CENTRE (lam = centre x level),
    ratio None; the centre is level 1.
  - The cap (R14, C7; L2 rule 2): the fit keeps the largest evenly spaced set of WHOLE bank units
    whose pooled fit rows stay within REGION_ROUTER_ROW_BUDGET (split.region_cap_units, read at
    call time); every kept unit keeps all its fit rows. The kernel applies the cap itself, from the
    fit rows it is given for every bank unit, so the cap cannot be skipped. Scored units are a
    subset of the bank units, decoupled from the cap: a scored unit outside the cap is still scored,
    with its own normal (R15: each unit's normal uses all its fit-year rows).
  - The kernel on plain arrays (RegionRows; private until the owner approves public entry points,
    as the per-unit kernels): the own-overlap-block tree columns dropped (RouterTreeColumns, checked
    against the store's own trees on every call; assert_no_own_group_column on every fit,
    G-DISJOINT), every level solved, trees-off = intercept + normal fitted on the capped rows and
    asserted equal to the normal within the R36 tolerance the caller passes (R16), BLAS held at
    BLAS_THREADS (4) threads for the pooled solve and checked on entering and leaving (owner ruling
    C: the 4-thread mode; plan 4.5: the region solve is one pooled solve, not sped up).
  - The fallback service (R12, C10, C15; L2 rule 3): short-history units of a PER-UNIT package are
    counted (fallback_plan; flagged above FALLBACK_FLAG_SHARE, report only) and routed by their
    group's region router fitted on the group's BANK units (the region design, cap included); its
    level is searched ONCE on the region grid over the fallback units' inner score rows pooled
    across groups (fallback_surface_mae, search_fallback_level), and the lambda centre is used
    when fewer than FALLBACK_MIN_UNITS_FOR_SEARCH such units exist (the count is printed);
    fill_fallback writes those rows into the per-unit output and refuses any row left NaN.

NOT BUILT (raise NotImplementedError): the FitContext-level wrappers route_region and
route_region_loro. They need the score rows' unit and step from FitContext (the approved signature
passes positions only, and FitContext has no public reader of a score row's identity) and the
pipeline's region wiring (pipeline/, outside this module); route_per_unit_loro in kinds.py is unbuilt
for the same reason. The kernels do the work on arrays. A weighted (GLS) region solve is a new
formula for the owner's review: the kernels take no weights.

Rows: fit rows are the bank units' own rows at or before the cut with a finite link(y) (R30: rows
with a missing label are not fit rows; the caller leaves them out). Score rows lie after the cut.
"""
# Provenance for the module: defo_softgate.py:105-124 (ridge: float32 centring, float32 Gram cast to
# float64, sc = trace / p + 1e-12, lam x sc on the diagonal, numpy Cholesky, np.linalg.solve twice,
# intercept ym - am @ w; apply: float32 blocks of 20000 rows @ w + b); add_linkcorr.py:37, 176-185
# (REGROWS 60000, LAM 100.0, the linspace row cap this module REPLACES with whole units; the link fitted
# through the ridge); adaptation.py:1149-1150, 1213-1214 (the same cap and lambda in the shipped nowcast);
# plan 2.2 R12, R14-R16; owner rulings A (D80 m = 1 -> position 0, D81 the projection, D82 the 10-unit
# threshold), C ('Region-router threads': a 4-thread mode, 1e-9 against its golden), E (L2 rules 2-4, L4).

import hashlib
import math
from dataclasses import dataclass
from numbers import Integral, Real
from types import MappingProxyType
from typing import Any, Callable, Mapping, Optional, Sequence, Tuple

import numpy as np

from treeroute import engine_constants as K
from treeroute import split as SP
from treeroute.route import kinds as RK
from treeroute.route import solve as S
from treeroute.route.kinds import (INTERCEPT, NORMAL, TREES, GridPoint, RouteGuardError, RouteOutput,
                                   RouteRefusal, RouterDesign, RouterKind, RouterTreeColumns)

# origin: defo_softgate.py:119-121 (apply: A[s:s + 20000].astype(np.float32) @ w + b). A prediction is
# one float32 dot product per row; the block only bounds the float32 copy. Kept as shipped.
REGION_APPLY_BLOCK_ROWS = 20000
# origin: defo_softgate.py:111 (sc = trace(G) / p + 1e-12)
TRACE_JITTER = 1e-12


# ---------------------------------------------------------------------------------------------------
# small helpers
def _name(value, what):
    if not isinstance(value, str) or not value:
        raise RouteRefusal("R14", "%s must be a non-empty string, got %r" % (what, value))
    return value


def _vector(values, what, n=None, rule="R14"):
    arr = np.asarray(values)
    if arr.ndim != 1 or arr.dtype.kind not in "fiu":
        raise RouteRefusal(rule, "%s must be a one-dimensional numeric array, got shape %s dtype %s"
                           % (what, arr.shape, arr.dtype))
    if n is not None and arr.shape[0] != n:
        raise RouteRefusal(rule, "%s has %d rows, expected %d" % (what, arr.shape[0], n))
    arr = np.asarray(arr, dtype=np.float64)
    if arr.size and not np.all(np.isfinite(arr)):
        raise RouteRefusal(rule, "%s holds %d missing or infinite value(s)"
                           % (what, int(arr.size - np.count_nonzero(np.isfinite(arr)))),
                           fix="leave rows with a missing label out of the fit rows (R30); normals and "
                               "tree answers must be finite")
    return arr


def _units_tuple(units, what):
    if isinstance(units, (str, bytes)):
        raise RouteRefusal("R14", "%s must be a sequence of unit ids, not one string" % what)
    out = tuple(units)
    for u in out:
        _name(u, "a unit id in %s" % what)
    if not out:
        raise RouteRefusal("R14", "%s is empty" % what)
    if list(out) != sorted(set(out)):
        raise RouteRefusal("R14", "%s must be sorted and hold each unit once" % what)
    return out


def _point(point, what="point"):
    """A grid point read into route.kinds.GridPoint (any object with level and ratio)."""
    if isinstance(point, GridPoint):
        return point
    level = getattr(point, "level", None)
    if not isinstance(level, Real) or isinstance(level, bool):
        raise RouteRefusal("R26", "%s must be a grid point (level, ratio), got %r" % (what, point))
    ratio = getattr(point, "ratio", None)
    return GridPoint(float(level), None if ratio is None else float(ratio))


# ---------------------------------------------------------------------------------------------------
# The grid and design (R14, R26)
def region_grid():
    """The region grid: every C12 region level with ratio None (level order)."""
    return tuple(GridPoint(float(v), None) for v in K.REGION_PENALTY_LEVELS)


def region_centre():
    """The region centre: level 1 (lam = REGION_LAMBDA_CENTRE). Refuses engine constants whose centre
    is not a grid point."""
    point = GridPoint(1.0, None)
    if point not in region_grid():
        raise RouteRefusal("C12", "the region centre %s is not a point of the region grid" % (point,),
                           fix="the engine constants C12 must put the centre on the grid")
    return point


def region_lambda(point):
    """lam of one region grid point: REGION_LAMBDA_CENTRE x level. Refuses a point off the grid (no
    penalty is hand-set, R26)."""
    p = _point(point)
    if p not in region_grid():
        raise RouteRefusal("R26", "%r is not a point of the region grid" % (p,),
                           fix="penalties come from the engine grid only; no point is hand-set")
    return float(K.REGION_LAMBDA_CENTRE) * p.level


def region_router_design():
    """R14 region layout: intercept, normal (unpenalised, U-1), trees; the region grid around the
    lambda centre; the fit-row cap of C7 (the same design derive_r14_router_design writes)."""
    return RouterDesign(kind=RouterKind.REGION, columns=(INTERCEPT, NORMAL, TREES),
                        unpenalised=(INTERCEPT, NORMAL), centre=(float(K.REGION_LAMBDA_CENTRE),),
                        grid=region_grid(), fit_row_cap=int(K.REGION_ROUTER_ROW_BUDGET))


# Provenance: plan 2.2 R14 (positions floor(i x (N-1)/(m-1)) of whole units within the budget), C7, Q11 a;
# owner rulings A (D80: m = 1 keeps position 0) and E (L2 rule 2: bank units, decoupled from the scored
# units); the body is split.region_cap_units (built with the LORO split).
def region_cap_units(sorted_units, fit_rows_per_unit, budget):
    """The region router's fit cap (approved signature): the largest set of evenly spaced WHOLE units
    whose pooled fit rows stay within the budget, in sorted order. The rule lives in
    split.region_cap_units, which this calls; its refusals (an empty, unsorted or repeated unit
    list, a missing or negative row count, a unit whose own rows exceed the budget) stand."""
    return SP.region_cap_units(tuple(sorted_units), fit_rows_per_unit, budget)


# ---------------------------------------------------------------------------------------------------
# The trace-normalised ridge, moved as-is, with the U-1 normal (D81)
@dataclass(frozen=True)
class RegionGram:
    """The tree block's link-free pieces for one group, table kind and set of fit rows (L4).

    centred      float32 (fit rows, columns): the fit block minus its column means, read-only
    means        float32 (columns,): the fit-row column means
    gram         float64 (columns, columns): centred' centred, formed in float32 and cast, read-only
    trace_scale  trace(gram) / columns + TRACE_JITTER: the scale of the tree penalty
    fingerprint  what the Gram was built on (group, table kind, row keys, columns, bank); '' when the
                 caller gave none (the solver-level use)
    """
    centred: np.ndarray
    means: np.ndarray
    gram: np.ndarray
    trace_scale: float
    fingerprint: str

    @property
    def n_rows(self):
        return int(self.centred.shape[0])

    @property
    def n_columns(self):
        return int(self.centred.shape[1])


@dataclass(frozen=True)
class RegionFit:
    """One solved region ridge: tree weights, intercept (a float64 scalar, as the shipped b), and the
    unpenalised normal's coefficient and fit-row centre (None in LEGACY mode, without a normal)."""
    w: np.ndarray
    intercept: Any
    normal_coef: Optional[float]
    normal_centre: Optional[float]
    lam: float


def region_gram(fit_trees, fingerprint="", consume=False):
    """The shared tree-block pieces of the shipped ridge (L4): a float32 C-ordered copy of the fit
    block, its column means (float32), the block centred on them in place, and its Gram, formed in
    float32 and cast to float64, with the trace scale trace / columns + 1e-12. Formed once, in one
    piece. consume=True lets the caller hand over a block it will not read again (a writeable,
    C-ordered float32 array owning its data): it is centred in place instead of copied, which gives
    the same bytes and saves one copy of the block (the kernels' fit block, the harness gate's rows).
    Refuses a block that is not 2-D floats with at least 2 rows and 1 column, and a non-finite
    value."""
    T = np.asarray(fit_trees)
    if T.ndim != 2 or T.shape[0] < 2 or T.shape[1] < 1 or T.dtype.kind != "f":
        raise RouteRefusal("R14", "the fit block must be (rows >= 2, columns >= 1) floats, got shape %s "
                                  "dtype %s" % (T.shape, T.dtype))
    if not isinstance(fingerprint, str):
        raise RouteRefusal("R14", "the Gram fingerprint must be a string")
    # the shipped Ar = A[rows].astype(np.float32): a C-ordered float32 copy of the fit rows
    if (consume and isinstance(fit_trees, np.ndarray) and T.dtype == np.float32 and T.flags.c_contiguous
            and T.flags.owndata and T.flags.writeable):
        Ar = T
    else:
        Ar = np.array(T, dtype=np.float32, order="C", copy=True)
    if not np.all(np.isfinite(Ar)):
        raise RouteRefusal("R14", "the fit block holds %d missing or infinite tree answer(s)"
                           % int(Ar.size - np.count_nonzero(np.isfinite(Ar))))
    am = Ar.mean(axis=0)
    Ar -= am                                      # the shipped Ar = Ar - am, elementwise, in place
    G = (Ar.T @ Ar).astype(np.float64)
    p = Ar.shape[1]
    sc = float(np.trace(G)) / max(p, 1) + TRACE_JITTER
    Ar.setflags(write=False)
    am.setflags(write=False)
    G.setflags(write=False)
    return RegionGram(centred=Ar, means=am, gram=G, trace_scale=sc, fingerprint=fingerprint)


def region_ridge(gram, fit_y, lam, fit_normal=None):
    """The trace-normalised ridge on the fit rows of ``gram`` at one lam.

    Without fit_normal: the shipped ridge (LEGACY mode; harness and tests only). With fit_normal
    (U-1): the normal enters unpenalised, the intercept and the normal projected out first, the tree
    penalty lam x trace_scale (the tree block's own trace). Returns RegionFit. Refuses a non-finite
    y or normal, rows that do not match the Gram, lam that is not finite and positive, and a
    penalised Gram that Cholesky cannot factor (RouteGuardError: the shipped code returned None and
    its caller then failed; the engine stops)."""
    if not isinstance(gram, RegionGram):
        raise RouteRefusal("R14", "gram must be a RegionGram, got %s" % type(gram).__name__)
    y = _vector(fit_y, "fit link(y)", gram.n_rows, rule="R30")
    if not isinstance(lam, Real) or isinstance(lam, bool) or not math.isfinite(lam) or lam <= 0:
        raise RouteRefusal("R26", "lam must be finite and positive, got %r" % (lam,))
    lam = float(lam)
    ym = float(y.mean())
    # the shipped rhs = (Ar.T @ (y[rows] - ym).astype(np.float32)).astype(np.float64)
    rhs = (gram.centred.T @ (y - ym).astype(np.float32)).astype(np.float64)
    G = np.array(gram.gram, dtype=np.float64, copy=True)
    g_coef, n_centre = None, None
    border, nn, ny = None, 0.0, 0.0
    if fit_normal is not None:
        n = _vector(fit_normal, "fit normal", gram.n_rows, rule="R15")
        n_centre = float(n.mean())
        nc = n - n_centre
        nn = float(nc @ nc)
        if nn > 0.0:
            border = (gram.centred.T @ nc.astype(np.float32)).astype(np.float64)
            ny = float(nc @ (y - ym))
            G -= np.outer(border, border) / nn
            rhs = rhs - border * (ny / nn)
    p = G.shape[0]
    G[np.diag_indices(p)] += lam * gram.trace_scale
    try:
        L = np.linalg.cholesky(G)
        w = np.linalg.solve(L.T, np.linalg.solve(L, rhs))
    except np.linalg.LinAlgError as exc:
        raise RouteGuardError("R14: the penalised region Gram (%d columns, lam %g) is not positive "
                              "definite: %s" % (p, lam, exc)) from None
    b = ym - gram.means @ w                       # a float64 scalar, as the shipped intercept
    if fit_normal is not None:
        g_coef = (ny - float(border @ w)) / nn if border is not None else 0.0
    return RegionFit(w=w, intercept=b, normal_coef=g_coef, normal_centre=n_centre, lam=lam)


def region_predict(fit, score_trees, score_normal=None):
    """Predictions (link space) of a RegionFit on score rows: the shipped apply (float32 blocks of
    REGION_APPLY_BLOCK_ROWS rows @ float32 w, plus the intercept), plus g x (normal - its fit-row
    centre) when the fit has a normal. Refuses a normal for a LEGACY fit, a missing normal for a U-1
    fit, and blocks that do not match."""
    if not isinstance(fit, RegionFit):
        raise RouteRefusal("R14", "fit must be a RegionFit, got %s" % type(fit).__name__)
    A = np.asarray(score_trees)
    if A.ndim != 2 or A.shape[1] != fit.w.shape[0] or A.dtype.kind != "f":
        raise RouteRefusal("R14", "score block of shape %s dtype %s does not match %d tree weights"
                           % (A.shape, A.dtype, fit.w.shape[0]))
    if fit.normal_coef is None and score_normal is not None:
        raise RouteRefusal("R14", "a fit without a normal column was given a score normal")
    if fit.normal_coef is not None and score_normal is None:
        raise RouteRefusal("R14", "a fit with the normal column (U-1) needs the score rows' normal")
    p = np.empty(A.shape[0])
    for s in range(0, A.shape[0], REGION_APPLY_BLOCK_ROWS):
        # C order always: the shipped apply ran on a C-ordered block, and a float32 matrix-vector product
        # on a column-ordered block takes another BLAS path that rounds differently (about one float32
        # ulp). A masked store view (values[:, columns]) is not C-ordered; a single-block one is. The
        # layout must not decide the bytes.
        blk = np.ascontiguousarray(A[s:s + REGION_APPLY_BLOCK_ROWS], dtype=np.float32)
        p[s:s + REGION_APPLY_BLOCK_ROWS] = blk @ fit.w.astype(np.float32) + fit.intercept
    if fit.normal_coef is not None:
        sn = _vector(score_normal, "score normal", A.shape[0], rule="R15")
        p = p + fit.normal_coef * (sn - fit.normal_centre)
    return p


# ---------------------------------------------------------------------------------------------------
# The region kernel on arrays
@dataclass(frozen=True)
class RegionRows:
    """One pass of one group's region router over plain arrays, in link space.

    group         the group
    fit_units     the group's BANK units, sorted: the candidates of the cap (R18 (1), L2 rules 2-3)
    scored_units  the units whose rows are scored here, sorted, a subset of fit_units (the group's
                  scored units; for the fallback router, the group's short-history units)
    fit_*         every bank unit's own rows at or before ``cut`` with a finite label (R30), in the
                  order they should be read (unit by unit, step order): fit_unit, fit_time (integer
                  step), fit_y (link(y)), fit_normal (the unit's link-matched normal, R15), fit_keys
                  (int64 row keys of the tree answers). The kernel keeps the capped units' rows.
    score_*       the rows to predict, after ``cut``: score_unit, score_time, score_normal,
                  score_keys; score_rows (m,) the caller's positions, returned as row_positions
    """
    cut: int
    group: str
    fit_units: Tuple[str, ...]
    scored_units: Tuple[str, ...]
    fit_unit: np.ndarray
    fit_time: np.ndarray
    fit_y: np.ndarray
    fit_normal: np.ndarray
    fit_keys: np.ndarray
    score_unit: np.ndarray
    score_time: np.ndarray
    score_normal: np.ndarray
    score_keys: np.ndarray
    score_rows: np.ndarray


def _int_times(values, what, n):
    arr = np.asarray(values)
    if arr.shape != (n,) or (n and arr.dtype.kind not in "iu"):
        raise RouteRefusal("G-FITCUT", "%s must be a 1-D integer array of %d steps" % (what, n))
    return arr.astype(np.int64, copy=False)


def _keys(values, what, n):
    arr = np.asarray(values)
    if arr.shape != (n,) or (n and arr.dtype.kind not in "iu"):
        raise RouteRefusal("R20", "%s must be a 1-D integer array of %d row keys" % (what, n))
    if n and int(arr.min()) < 0:
        raise RouteRefusal("R20", "%s holds a negative row key" % what)
    return arr.astype(np.int64, copy=False)


def _check_region_rows(rows, budget):
    """Validate a RegionRows pass and apply the cap. Returns a dict of checked arrays, the kept units
    and the kept fit positions."""
    if not isinstance(rows, RegionRows):
        raise RouteRefusal("R14", "rows must be RegionRows, got %s" % type(rows).__name__)
    group = _name(rows.group, "the group")
    if not isinstance(rows.cut, Integral) or isinstance(rows.cut, bool):
        raise RouteRefusal("G-FITCUT", "the cut must be an integer step, got %r" % (rows.cut,))
    cut = int(rows.cut)
    fit_units = _units_tuple(rows.fit_units, "fit_units (the group's bank units)")
    scored = _units_tuple(rows.scored_units, "scored_units")
    stray = sorted(set(scored) - set(fit_units))
    if stray:
        raise RouteRefusal("R14", "group %s: scored unit(s) %s are not among its bank units (fit_units); "
                           "scored units are a subset of the bank units (R18)" % (group, stray[:5]))
    fu = np.asarray(rows.fit_unit, dtype=object)
    su = np.asarray(rows.score_unit, dtype=object)
    if fu.ndim != 1 or su.ndim != 1:
        raise RouteRefusal("R14", "fit_unit and score_unit must be one-dimensional")
    nf, ns = fu.shape[0], su.shape[0]
    if ns == 0:
        raise RouteRefusal("R14", "group %s: no score rows, nothing to route" % group)
    ft = _int_times(rows.fit_time, "fit_time", nf)
    st = _int_times(rows.score_time, "score_time", ns)
    if nf and int(ft.max()) > cut:
        raise RouteRefusal("G-FITCUT", "group %s: %d fit row(s) lie after the cut %d"
                           % (group, int(np.count_nonzero(ft > cut)), cut),
                           fix="the router fits only on rows at or before the cut")
    if int(st.min()) <= cut:
        raise RouteRefusal("G-FITCUT", "group %s: %d score row(s) lie at or before the cut %d; a fit row "
                           "would be scored" % (group, int(np.count_nonzero(st <= cut)), cut))
    fy = _vector(rows.fit_y, "fit link(y)", nf, rule="R30")
    fn = _vector(rows.fit_normal, "fit normal", nf, rule="R15")
    sn = _vector(rows.score_normal, "score normal", ns, rule="R15")
    fk = _keys(rows.fit_keys, "fit_keys", nf)
    sk = _keys(rows.score_keys, "score_keys", ns)
    sr = np.asarray(rows.score_rows)
    if sr.shape != (ns,):
        raise RouteRefusal("R14", "score_rows must hold one position per score row")
    fu_s = np.array([str(u) for u in fu.tolist()], dtype=object)
    su_s = np.array([str(u) for u in su.tolist()], dtype=object)
    outside = sorted(set(fu_s.tolist()) - set(fit_units))
    if outside:
        raise RouteRefusal("R14", "group %s: fit rows of unit(s) %s, which are not its bank units"
                           % (group, outside[:5]))
    off = sorted(set(su_s.tolist()) - set(scored))
    if off:
        raise RouteRefusal("R14", "group %s: score rows of unit(s) %s, which are not its scored units"
                           % (group, off[:5]))
    if nf:
        pairs = np.rec.fromarrays([fu_s.astype(str), ft], names="u,t")
        if np.unique(pairs).size != nf:
            raise RouteRefusal("R14", "group %s: a (unit, step) fit row is given twice" % group)
    counts = {u: 0 for u in fit_units}
    if nf:
        uniq, cnt = np.unique(fu_s.astype(str), return_counts=True)
        for u, c in zip(uniq.tolist(), cnt.tolist()):
            counts[u] = int(c)
    kept_units = region_cap_units(fit_units, counts, budget)
    keep = np.isin(fu_s, np.asarray(kept_units, dtype=object))
    kept_pos = np.flatnonzero(keep)
    if kept_pos.size < 2:
        raise RouteRefusal("R12", "group %s: the capped region fit holds %d fit row(s); the region "
                           "router needs at least 2" % (group, kept_pos.size))
    return {"group": group, "cut": cut, "fit_units": fit_units, "scored": scored, "fy": fy, "fn": fn,
            "sn": sn, "fk": fk, "sk": sk, "sr": sr, "kept_units": kept_units, "kept_pos": kept_pos,
            "ns": ns}


def _gram_fingerprint(group, table_kind, fit_keys, columns, answers):
    """What a RegionGram was built on: group, table kind, the store's bank fingerprint and tree count,
    the fit row keys and the tree columns. A store without a non-empty string bank_fingerprint is
    refused (fit/tables.TreeAnswerStore always has one): a Gram not tied to its bank could be shared
    with a pass on another bank."""
    bank = getattr(answers, "bank_fingerprint", None)
    if not isinstance(bank, str) or not bank:
        raise RouteRefusal("R20", "the tree-answer store carries no bank fingerprint (got %r); the region Gram "
                                  "must be tied to its bank (L4)" % (bank,),
                           fix="pass the fit/tables.TreeAnswerStore built from the bank")
    h = hashlib.sha256()
    h.update(("region-gram|%s|%s|%s|%s|" % (group, table_kind, bank, int(answers.n_trees))).encode("utf-8"))
    h.update(np.ascontiguousarray(fit_keys, dtype=np.int64).tobytes())
    h.update(b"|")
    h.update(np.ascontiguousarray(columns, dtype=np.int64).tobytes())
    return h.hexdigest()


def _masked_view(answers, keys, table_kind, tree_columns, group, what):
    """The store's answers on ``keys`` at the group's allowed columns (own block dropped), float32."""
    view = answers.unit_view(keys, table_kind)
    view_group = getattr(view, "group", None)
    if view_group != group:
        raise RouteGuardError("G-DISJOINT: the %s rows of group %s were answered from the table of group "
                              "%s" % (what, group, view_group))
    index = np.asarray(view.tree_index, dtype=np.int64)
    values = np.asarray(view.values)
    if values.ndim != 2 or values.shape != (keys.size, index.size):
        raise RouteRefusal("R20", "the store answered shape %s for %d rows and %d columns"
                           % (values.shape, keys.size, index.size))
    want = np.asarray(tree_columns.columns_by_group[group], dtype=np.int64)
    pos = np.searchsorted(index, want)
    pos_c = np.minimum(pos, max(index.size - 1, 0))
    if index.size == 0 or not np.array_equal(index[pos_c], want):
        raise RouteGuardError("G-DISJOINT: group %s needs tree column(s) the store does not answer (an "
                              "own-group tree, or a column outside the bank)" % group)
    if not (pos_c.size == index.size and np.array_equal(pos_c, np.arange(index.size))):
        values = values[:, pos_c]
    owners = np.asarray(tree_columns.tree_group, dtype=object)
    RK.assert_no_own_group_column(owners[want], tree_columns.router_groups[group],
                                  "group %s region router" % group)
    # one layout whichever mask path ran (region_predict also normalises; the Gram copies to C order)
    return np.ascontiguousarray(values)


def _blas_limit():
    """BLAS at BLAS_THREADS for one pooled region solve (owner ruling C: the 4-thread mode). scipy's
    BLAS (the trees-off solve's triangular solves) is loaded BEFORE the limit is entered, so the limit
    covers it; the caller checks every loaded BLAS library on entering and on leaving."""
    from threadpoolctl import threadpool_limits

    S._solve_triangular()
    return threadpool_limits(limits=int(K.BLAS_THREADS), user_api="blas")


def region_shared_gram(rows, answers, table_kind, tree_columns):
    """The RegionGram of one group's pass (L4): read the capped fit rows' tree answers at the group's
    allowed columns and form the Gram once, at BLAS_THREADS threads. Pass it to the region kernels of
    every link of the same group, table kind and cut; they refuse a Gram built on other rows,
    columns, table or bank."""
    chk = _check_region_rows(rows, K.REGION_ROUTER_ROW_BUDGET)
    group = chk["group"]
    _check_mask(answers, tree_columns, group)
    keys = chk["fk"][chk["kept_pos"]]
    want = np.asarray(tree_columns.columns_by_group[group], dtype=np.int64)
    fp = _gram_fingerprint(group, table_kind, keys, want, answers)
    T = _masked_view(answers, keys, table_kind, tree_columns, group, "fit")
    limit = int(K.BLAS_THREADS)
    with _blas_limit():
        RK._assert_blas_threads(limit, "entering")
        gram = region_gram(T, fp, consume=True)
        RK._assert_blas_threads(limit, "leaving")
    return gram


def _check_mask(answers, tree_columns, group):
    if not isinstance(tree_columns, RouterTreeColumns):
        raise RouteRefusal("G-DISJOINT", "tree_columns must be RouterTreeColumns (the own-block mask)")
    if not callable(getattr(answers, "unit_view", None)):
        raise RouteRefusal("R20", "answers must be the tree-answer store (unit_view(row_keys, kind))")
    if group not in tree_columns.columns_by_group:
        raise RouteRefusal("G-DISJOINT", "group %s has no router tree columns" % group)
    RK._check_mask_against_store(answers, tree_columns)


def _route(rows, answers, table_kind, tree_columns, points, identity_tolerance, gram):
    chk = _check_region_rows(rows, K.REGION_ROUTER_ROW_BUDGET)
    tol = RK._check_tolerance(identity_tolerance)
    group = chk["group"]
    _check_mask(answers, tree_columns, group)
    kept = chk["kept_pos"]
    fk = chk["fk"][kept]
    fy = chk["fy"][kept]
    fn = chk["fn"][kept]
    want = np.asarray(tree_columns.columns_by_group[group], dtype=np.int64)
    fp = _gram_fingerprint(group, table_kind, fk, want, answers)
    lams = [region_lambda(p) for p in points]
    if gram is not None:
        if not isinstance(gram, RegionGram):
            raise RouteRefusal("R14", "gram must be a RegionGram (region_shared_gram), got %s"
                               % type(gram).__name__)
        if gram.fingerprint != fp:
            raise RouteRefusal("R14", "group %s: the shared Gram was built on other fit rows, tree columns, "
                               "table kind or bank than this pass (L4 shares a Gram only across the links "
                               "of one group, table and cut)" % group,
                               fix="build it with region_shared_gram on this pass's rows")
        score_T = _masked_view(answers, chk["sk"], table_kind, tree_columns, group, "score")
        fit_T = None
    else:
        allv = _masked_view(answers, np.concatenate([fk, chk["sk"]]), table_kind, tree_columns, group,
                            "fit and score")
        fit_T, score_T = allv[:fk.size], allv[fk.size:]
    limit = int(K.BLAS_THREADS)
    out = np.empty((chk["ns"], len(points)))
    with _blas_limit():
        RK._assert_blas_threads(limit, "entering")
        if gram is None:
            gram = region_gram(fit_T, fp, consume=True)
            del fit_T
        for j, lam in enumerate(lams):
            fit = region_ridge(gram, fy, lam, fn)
            out[:, j] = region_predict(fit, score_T, chk["sn"])
        p0 = RK._trees_off_checked(fn, fy, chk["sn"], tol, "group %s region router" % group)
        RK._assert_blas_threads(limit, "leaving")
    return RouteOutput(row_positions=np.asarray(chk["sr"]).copy(), predictions=out, trees_off=p0,
                       grid=tuple(points), n_units_fitted=len(chk["kept_units"]), n_units_fallback=0,
                       n_rows_pool_fallback=0)


# The two region kernels are PRIVATE, as the per-unit kernels are: the owner approved route_region /
# route_region_loro as the entry points (FitContext-level, not built here). The legacy-harness gate, the
# tests and the fallback service below call them.
def _route_region_grid(rows, answers, table_kind, tree_columns, identity_tolerance, gram=None):
    """The region router on the decision surface: one pooled ridge on the group's capped bank units,
    solved at EVERY level of the region grid, plus trees-off (R16, asserted equal to the normal within
    identity_tolerance).

    rows          RegionRows (link space)
    answers       the tree-answer store: unit_view(row_keys, table_kind) -> values, tree_index, group;
                  n_trees and own_columns(group), against which the mask is checked (physical keys)
    table_kind    the table the arm reads ('plain', 'corrector' or 'placebo_corrector')
    tree_columns  RouterTreeColumns: the group's allowed tree columns and its own overlap block
    gram          an optional RegionGram from region_shared_gram on the same rows (L4)
    Returns RouteOutput with one column per region level."""
    return _route(rows, answers, table_kind, tree_columns, region_grid(), identity_tolerance, gram)


def _route_region_at(rows, answers, table_kind, tree_columns, point, identity_tolerance, gram=None):
    """The region router at ONE level (the test pass at the adopted level). Arguments as
    _route_region_grid; ``point`` must be a region grid point. The same solve as the grid's column."""
    p = _point(point)
    region_lambda(p)
    return _route(rows, answers, table_kind, tree_columns, (p,), identity_tolerance, gram)


# ---------------------------------------------------------------------------------------------------
# The fallback service for short-history units of a per-unit package (R12, C10, C15; L2 rule 3)
@dataclass(frozen=True)
class FallbackPlan:
    """R12 for one pass: the short-history units (fewer than PER_UNIT_MIN_VALID_ROWS valid fit rows),
    their share of the scored units, whether the share is flagged (C10, report only), and the short
    units of each group (each such group fits one fallback region router on its bank units)."""
    short_units: Tuple[str, ...]
    share: float
    flagged: bool
    by_group: Mapping[str, Tuple[str, ...]]


def fallback_units(valid_fit_rows):
    """Units with fewer than PER_UNIT_MIN_VALID_ROWS valid fit rows, sorted, and their share (the
    approved signature; route.kinds.fallback_units is its body)."""
    return RK.fallback_units(valid_fit_rows)


def fallback_plan(valid_fit_rows, unit_group):
    """FallbackPlan of a per-unit pass: fallback_units, the C10 flag, and each short unit's group.
    Refuses an empty map and a short unit without a group."""
    short, share = RK.fallback_units(valid_fit_rows)
    by = {}
    for u in short:
        g = unit_group.get(u) if isinstance(unit_group, Mapping) else None
        if g is None:
            raise RouteRefusal("R12", "short-history unit %s has no group" % u)
        by.setdefault(_name(g, "the group of unit %s" % u), []).append(u)
    return FallbackPlan(short_units=short, share=float(share), flagged=RK.fallback_share_flagged(share),
                        by_group=MappingProxyType({g: tuple(sorted(v)) for g, v in sorted(by.items())}))


def _check_fallback_rows(rows_by_group, bank_units_by_group, plan):
    if not isinstance(plan, FallbackPlan):
        raise RouteRefusal("R12", "plan must be a FallbackPlan (fallback_plan)")
    if set(rows_by_group) != set(plan.by_group):
        raise RouteRefusal("R12", "fallback rows are given for groups %s, the plan's groups with a short "
                           "unit are %s" % (sorted(rows_by_group), sorted(plan.by_group)))
    for g, rows in sorted(rows_by_group.items()):
        if not isinstance(rows, RegionRows) or rows.group != g:
            raise RouteRefusal("R12", "the fallback rows of group %s must be RegionRows of that group" % g)
        bank = bank_units_by_group.get(g) if isinstance(bank_units_by_group, Mapping) else None
        if bank is None or tuple(rows.fit_units) != tuple(sorted(bank)):
            raise RouteRefusal("R12", "group %s: the fallback router pools the group's BANK units (L2 rule "
                               "3); its fit_units differ from the bank list" % g)
        if tuple(rows.scored_units) != tuple(plan.by_group[g]):
            raise RouteRefusal("R12", "group %s: the fallback router scores exactly the group's short units "
                               "%s, got %s" % (g, plan.by_group[g], tuple(rows.scored_units)))


def route_fallback_grid(rows_by_group, bank_units_by_group, plan, answers, table_kind, tree_columns,
                        identity_tolerance):
    """Each group's fallback region router on the decision surface (every region level): RegionRows
    whose fit units are the group's bank units and whose scored units are its short units. Groups are
    solved one after another (each is one pooled solve at BLAS_THREADS). Returns {group: RouteOutput}."""
    _check_fallback_rows(rows_by_group, bank_units_by_group, plan)
    return {g: _route_region_grid(rows_by_group[g], answers, table_kind, tree_columns, identity_tolerance)
            for g in sorted(rows_by_group)}


def route_fallback_at(rows_by_group, bank_units_by_group, plan, answers, table_kind, tree_columns, point,
                      identity_tolerance):
    """Each group's fallback region router at the one fallback level (search_fallback_level)."""
    _check_fallback_rows(rows_by_group, bank_units_by_group, plan)
    return {g: _route_region_at(rows_by_group[g], answers, table_kind, tree_columns, point,
                                identity_tolerance) for g in sorted(rows_by_group)}


# Provenance: plan 2.2 R12 ("its level is searched once on the 7-level region grid, scored on the fallback
# units' inner score rows pooled across groups"), R28 (scores in y units after the inverse and the clip).
def fallback_surface_mae(outputs, y_true, score_units, inverse):
    """Pooled MAE per region level over the fallback units' inner score rows of every group, and the
    number of fallback units with at least one such row.

    outputs      {group: RouteOutput of route_fallback_grid on the inner surface}
    y_true       {group: the labels (y units) of those rows, in the output's row order}
    score_units  {group: the unit of each of those rows}
    inverse      link space -> y units with the legal clip (R28), elementwise
    Returns ({GridPoint: MAE}, n_units_scored). Refuses outputs that are not on the region grid,
    mismatched rows, and a non-finite label or prediction."""
    if not outputs:
        raise RouteRefusal("R12", "no fallback outputs: nothing to score")
    grid = region_grid()
    abs_sum = np.zeros(len(grid))
    n_rows = 0
    units = set()
    for g in sorted(outputs):
        out = outputs[g]
        if tuple(_point(p) for p in out.grid) != grid:
            raise RouteRefusal("R12", "group %s: the fallback output is not on the region grid" % g)
        y = _vector(y_true[g], "labels of group %s" % g, out.predictions.shape[0], rule="R28")
        u = np.asarray(score_units[g], dtype=object)
        if u.shape != (out.predictions.shape[0],):
            raise RouteRefusal("R12", "group %s: one unit per scored row is needed" % g)
        for j in range(len(grid)):
            pred = np.asarray(inverse(np.asarray(out.predictions[:, j], dtype=np.float64)), dtype=np.float64)
            if pred.shape != y.shape or not np.all(np.isfinite(pred)):
                raise RouteRefusal("R28", "group %s: the back-transformed fallback predictions are not finite "
                                   "and one per row" % g)
            abs_sum[j] += float(np.abs(y - pred).sum())
        n_rows += y.size
        units.update(str(x) for x in u.tolist())
    if n_rows == 0:
        raise RouteRefusal("R12", "no fallback score rows: nothing to score")
    return {p: abs_sum[j] / n_rows for j, p in enumerate(grid)}, len(units)


# Provenance: plan 2.2 R12, C15 (the lambda centre under 10 fallback units; D82 accepted as proposed);
# layer.penalty_search's tie rule (the first level in grid order).
def search_fallback_level(surface_mae_by_level, n_fallback_units_scored, centre):
    """The fallback region router's level: the minimum pooled MAE over the region levels (ties to the
    first level in grid order), or the centre when fewer than FALLBACK_MIN_UNITS_FOR_SEARCH fallback
    units have inner score rows (the count is printed). Returns (level, used_centre). Refuses a level
    set that is not the region grid, a centre that is not the region centre, a count that is not a
    non-negative integer and a non-finite MAE."""
    grid = region_grid()
    if not isinstance(surface_mae_by_level, Mapping):
        raise RouteRefusal("R12", "surface_mae_by_level must map region levels to their pooled MAE")
    by = {}
    for k, v in surface_mae_by_level.items():
        by[_point(k, "a level")] = v
    if set(by) != set(grid) or len(by) != len(surface_mae_by_level):
        raise RouteRefusal("R12", "the levels %s are not the region grid %s"
                           % (sorted(p.level for p in by), [p.level for p in grid]))
    c = _point(centre, "centre")
    if c != region_centre():
        raise RouteRefusal("R12", "the fallback centre must be the region centre %s, got %s"
                           % (region_centre(), c))
    n = n_fallback_units_scored
    if not isinstance(n, Integral) or isinstance(n, bool) or int(n) < 0:
        raise RouteRefusal("R12", "the fallback unit count must be a non-negative integer, got %r" % (n,))
    if int(n) < int(K.FALLBACK_MIN_UNITS_FOR_SEARCH):
        print("region fallback: %d fallback unit(s) with inner score rows, under %d: the lambda centre is "
              "used (R12, C15)" % (int(n), int(K.FALLBACK_MIN_UNITS_FOR_SEARCH)))
        return c, True
    best, best_v = None, None
    for p in grid:
        v = by[p]
        if not isinstance(v, Real) or isinstance(v, bool) or not math.isfinite(float(v)):
            raise RouteRefusal("R12", "level %s has a non-finite MAE %r" % (p.level, v))
        if best_v is None or float(v) < best_v:
            best, best_v = p, float(v)
    return best, False


def fill_fallback(per_unit, fallback_by_group, point):
    """The per-unit output with its short-history rows filled by the fallback region routers (R12).

    per_unit           RouteOutput of the per-unit pass (its short units' rows are NaN)
    fallback_by_group  {group: RouteOutput of that group's fallback router}; its row_positions are
                       the per-unit pass's row positions of the group's short units' rows
    point              the fallback level (search_fallback_level); every fallback output holds it
    Each filled row takes the fallback prediction at ``point`` in every per-unit grid column and the
    fallback trees-off (the normal). Refuses a fallback row that the per-unit router fitted (not NaN),
    a position the per-unit pass does not hold, a row filled twice, and any row still NaN after the
    fill (a NaN router row is never scored)."""
    if not isinstance(per_unit, RouteOutput):
        raise RouteRefusal("R12", "per_unit must be a RouteOutput")
    p = _point(point)
    region_lambda(p)
    pos = np.asarray(per_unit.row_positions)
    index = {v: i for i, v in enumerate(pos.tolist())}
    if len(index) != pos.size:
        raise RouteRefusal("R12", "the per-unit output repeats a row position")
    pred = np.array(per_unit.predictions, dtype=np.float64, copy=True)
    off = np.array(per_unit.trees_off, dtype=np.float64, copy=True)
    filled = np.zeros(pos.size, dtype=bool)
    for g in sorted(fallback_by_group):
        fb = fallback_by_group[g]
        grid = tuple(_point(q) for q in fb.grid)
        if p not in grid:
            raise RouteRefusal("R12", "group %s: the fallback output does not hold the level %s" % (g, p.level))
        j = grid.index(p)
        for r, position in enumerate(np.asarray(fb.row_positions).tolist()):
            i = index.get(position)
            if i is None:
                raise RouteRefusal("R12", "group %s: fallback row position %r is not a row of the per-unit "
                                   "pass" % (g, position))
            if filled[i]:
                raise RouteRefusal("R12", "row position %r is filled twice" % (position,))
            if not (np.isnan(pred[i]).all() and np.isnan(off[i])):
                raise RouteRefusal("R12", "group %s: row position %r was fitted by the per-unit router; only "
                                   "short-history rows take the fallback" % (g, position))
            pred[i, :] = fb.predictions[r, j]
            off[i] = fb.trees_off[r]
            filled[i] = True
    left = int(np.count_nonzero(np.isnan(pred).any(axis=1) | np.isnan(off)))
    if left:
        raise RouteRefusal("R12", "%d router row(s) are still NaN after the fallback fill; a NaN router "
                           "row is never scored" % left,
                           fix="give every group with a short unit its fallback router")
    return RouteOutput(row_positions=pos.copy(), predictions=pred, trees_off=off, grid=tuple(per_unit.grid),
                       n_units_fitted=per_unit.n_units_fitted, n_units_fallback=per_unit.n_units_fallback,
                       n_rows_pool_fallback=per_unit.n_rows_pool_fallback)


# ---------------------------------------------------------------------------------------------------
# Approved FitContext-level signatures (not built: see the module docstring)
_WRAPPER = ("needs the score rows' unit and step from FitContext (the approved signature passes grid "
            "positions only, and FitContext has no public reader of a score row's identity) and the "
            "pipeline's region wiring (pipeline/, outside route/region.py); a weighted (GLS) region solve "
            "is a new formula awaiting the owner. The kernels _route_region_grid / _route_region_at do the "
            "work on arrays (RegionRows)")


def route_region(ctx, group, unit_ids, link, c, ub, normals, design, answers, score_row_positions,
                 weights):
    """Region router (approved signature; superseded by route_region_loro under LORO). Not built."""
    raise NotImplementedError("route_region " + _WRAPPER)


def route_region_loro(ctx, group, fit_units, scored_units, link, c, ub, normals, design, answers,
                      tree_columns, score_row_positions, weights):
    """Region router under leave one region out (approved signature). Not built."""
    raise NotImplementedError("route_region_loro " + _WRAPPER)


__all__ = [
    "REGION_APPLY_BLOCK_ROWS", "TRACE_JITTER", "region_grid", "region_centre", "region_lambda",
    "region_router_design", "region_cap_units", "RegionGram", "RegionFit", "region_gram", "region_ridge",
    "region_predict", "RegionRows", "region_shared_gram", "FallbackPlan", "fallback_units", "fallback_plan",
    "route_fallback_grid", "route_fallback_at", "fallback_surface_mae", "search_fallback_level",
    "fill_fallback", "route_region", "route_region_loro",
]
