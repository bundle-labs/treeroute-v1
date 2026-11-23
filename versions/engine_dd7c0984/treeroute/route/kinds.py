"""treeroute.route.kinds: the router kinds (plan 4.2 route/kinds.py row; R12-R16, R20, R26; leave one
region out, owner rulings D and E).

SCIENCE bodies for the owner-approved signatures of _proposed/route_kinds.py and the LORO additions
(_proposed/loro_additions.py, SIGNATURES_LORO_ADDENDUM.md), approved by the owner rulings file
(engine/OWNER_RULINGS_*.md, sections A-E). Where the rulings file differs from a docstring there, the
rulings file wins.

BUILT: the PER-UNIT kind.
  - The column blocks (R14): intercept, the unit's link-matched normal (unpenalised, centred on its
    fit-row mean), the standardised context (penalty level x ratio), the tree answers (penalty
    level). build_column_block serves fit and score rows alike.
  - The grid (R14, R26): 7 levels x 5 ratios around the engine-constant centres, level-major, 35
    points; 7 levels when no context is declared. a_tree = trees centre x level, a_ctx = a_tree x
    ratio, so the centre point (level 1, ratio = context centre / trees centre) is the pair of
    centres itself.
  - The normal (R15, season_normal): per season key, the mean of link(y) over the unit's own fit rows
    at or before the cut; a season with no fit row takes the unit's all-season mean, a unit with no
    fit row the donor mean (counted).
  - Trees-off (R16): intercept + normal only, unweighted, context dropped; it equals the normal, and
    that identity is asserted on every fitted unit within the tolerance the caller passes (R36:
    k x s; k is not set yet, r36_tolerance refuses until it is). The APPROVED trees_off_with_normal
    has no input that carries the R36 tolerance (s is the donor-row sd, not a unit input), so it
    raises NotImplementedError until the owner rules how the tolerance reaches it; the kernels use
    the private _trees_off_checked, which takes the tolerance.
  - The own-overlap-block column mask (R14, LORO): router_tree_columns drops every tree whose group
    is in the router's block; RouterTreeColumns carries the overlap blocks and refuses a mask that
    splits a block, keeps an own-block tree or drops any other tree; assert_no_own_group_column runs
    on every unit fit (G-DISJOINT). On every router call the mask's tree groups are checked against
    the store's own record of its trees (physical keys: n_trees and own_columns), so a mislabelled
    mask is refused. The tree-answer store already leaves each row's own group's trees out
    (fit/tables.py); the mask here also drops the other groups of the block.
  - The router loop (PRIVATE kernels until the owner approves public entry points; the approved
    route_per_unit_loro will call them): _route_per_unit_grid solves every grid point with the
    shared-Gram solve and its reference check on the first NVERIFY fitted units (the decision
    surface); _route_per_unit_at solves one grid point with solve_local (the test pass at the
    adopted penalty). Both read each unit's tree answers by row key, so a caller that keys a unit's
    rows to their predecessor rows (a lag arm) gets the explicit-row route of the forecast script.
    Units are solved ROUTER_WORKERS at once with BLAS limited to ROUTER_WORKER_BLAS_THREADS
    thread(s) (threadpoolctl) for the whole loop at ANY worker count: scipy's BLAS is loaded before
    the limit is entered, and every loaded BLAS library is checked at the limit on entering and on
    leaving the loop. Tree answers are read in unit order in the calling thread; results are
    written back in unit order. So the output is the same bytes for any worker count.
  - Short history (R12): a unit with fewer than PER_UNIT_MIN_VALID_ROWS fit rows is NOT fitted. Its
    rows get NaN (never the donor-wide mean) and it is counted; fallback_units() names the units
    and their share for the region fallback router (route/region.py's fallback service, which the
    pipeline calls). A pass in which NO unit can be fitted is refused by the kernels (nothing would
    be routed); pipeline/router.py does not send such a pass to them: it fills every row from the
    fallback region routers.
  - GLS-weighted arms (R24, R25): both kernels take fit_weights (one R25 weight per fit row); the
    weighted solves are route.solve's solve_grid_weighted / solve_point_weighted, a NEW formula for
    the owner's review (derivation in route/solve.py). All weights 1 gives the unweighted bytes;
    trees-off stays unweighted. _trees_off_per_unit gives the trees-off column alone (a forecast
    lead's decline target on the identity link).

NOT BUILT HERE (raise NotImplementedError naming the milestone): the region kind's approved names
(region_cap_units, route_region, route_region_loro, search_fallback_level: their bodies are built in
route/region.py, which the pipeline calls; aliasing these names to it is an owner item, because
tests/test_route_kinds.py pins the stubs); the neighbour kind's approved names other than trees_off_neighbour
(their bodies are built in route/neighbour.py, see below); and the FitContext-level wrappers (route_per_unit_loro,
unit_season_normal, donor_link_mean): the approved route_per_unit_loro passes score rows as grid
positions only, and FitContext has no public reader of a position's unit and step, so the pipeline
feeds the kernels itself (pipeline/router.py). The kernels here take link-space arrays.

The NEIGHBOUR kind (milestone M8, owner ruling U) is built in route/neighbour.py. trees_off_neighbour here
delegates to it (same approved signature). The other approved neighbour names cannot carry what the rulings
need and raise, naming the built body: neighbour_pool_loro has no issue day (ruling U4 filters each pool by
it; route.neighbour.neighbour_pool_loro takes it as the keyword row_issue_day, owner item O19); route_neighbour
and route_neighbour_loro pass the score rows as positions only (the table pipeline feeds the private kernels
route.neighbour._route_neighbour_grid / _route_neighbour_at); neighbour_pool is the pre-LORO name, superseded
by neighbour_pool_loro (SIGNATURES_LORO_ADDENDUM.md).

Rows: fit rows are the router's own rows at or before the cut, with finite link(y) (R30: rows with
a missing label are not fit rows; the caller leaves them out). Score rows lie after the cut.

The shared shapes (RouterKind, GridPoint, RouterDesign, DesignMatrix, NormalTable, RouteOutput) are
FIELD-IDENTICAL copies of the approved shapes; engine code may not import _proposed (G-IMPORT).
"""
# Provenance for the module: pm25_adaptation.py:310-444 (route_percell, route_sweep, trees-off),
# :335 and :395 (context mean and sd over all fit rows of the pass, sd + 1e-9), :409-414 (design
# built once per cell: intercept, normal centred on its fit-row mean, context, tree answers), :176-177
# (LEVELS, RATIOS; GRID level-major), :342-344 (the donor-wide mean fallback this module REPLACES
# with a flag), :584-604 (add_clim: the per cell-month mean over the given rows only);
# pm25_forecast.py:265-305 (route_idx: tree rows given explicitly per row, one read per cell);
# engine/speedproof/pm25_adaptation_fast.py:388-573 (the parallel cell loop proven byte-identical at
# BLAS 1: cell list, fallback rule and NVERIFY cells fixed serially, results written back in cell
# order); fire_architecture.py:102-103 (ALPHA 0.5, A_CTX 0.25: the C12 centres). Owner rulings D
# (leave one region out) and E (L2 rule 4: overlap blocks dropped together).

import math
from collections import abc, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from numbers import Integral, Real
from types import MappingProxyType
from typing import Any, Mapping, Optional, Tuple

import numpy as np

from treeroute import engine_constants as K
from treeroute.errors import RefusedError, TreerouteError
from treeroute.route import solve as S

# Block names of the router design (R14).
INTERCEPT = "intercept"
NORMAL = "normal"
CONTEXT = "context"
TREES = "trees"
BLOCK_NAMES = (INTERCEPT, NORMAL, CONTEXT, TREES)

# origin: pm25_adaptation.py:335, 395 (sd + 1e-9: a constant context column standardises to 0 instead
# of failing; the proposed default of the R20 signature, accepted in the owner rulings part A)
CONTEXT_SD_OFFSET = 1e-9

# TEST ONLY. The engine always solves with ROUTER_WORKERS workers (plan 4.5: the 'off' path exists
# only inside tests and the harness gate, never as a flag). A test sets an integer here to prove
# the bytes do not depend on the worker count. Read at every call of a router.
_TEST_ONLY_ROUTER_WORKERS = None


# ---------------------------------------------------------------------------------------------------
# Errors
class RouteRefusal(RefusedError):
    """A router rule refused the request (R12, R14-R16, R20, R30, G-FITCUT, G-DISJOINT)."""


class RouteGuardError(TreerouteError):
    """A router runtime guard failed: the trees-off identity (R16) or an own-block column (G-DISJOINT)
    found during a fit. The run stops; nothing from that call is kept."""


# ---------------------------------------------------------------------------------------------------
# Shapes (field-identical to the approved shapes)
class RouterKind(Enum):
    """R12 outcome."""
    PER_UNIT = "per_unit"
    REGION = "region"
    NEIGHBOUR = "neighbour"


@dataclass(frozen=True)
class GridPoint:
    """One penalty grid point (R14). ratio is None on the region grid and on a context-free grid."""
    level: float
    ratio: Optional[float]


@dataclass(frozen=True)
class RouterDesign:
    """R14 outcome: column layout, which blocks are penalised, the grid and any fit-row cap."""
    kind: RouterKind
    columns: Tuple[str, ...]           # block names in order, e.g. intercept, normal, context, trees
    unpenalised: Tuple[str, ...]
    centre: Tuple[float, ...]          # penalty centre(s) from engine constants (C12)
    grid: Tuple[GridPoint, ...]
    fit_row_cap: Optional[int]         # region only (C7)


@dataclass(frozen=True)
class DesignMatrix:
    """One router design: rows x columns, with the block of each column."""
    X: np.ndarray
    blocks: Tuple[str, ...]


@dataclass(frozen=True)
class NormalTable:
    """R15: one unit's normal per season key in one link at one cut, with the fallback counts."""
    unit_id: str
    link: Any
    cut: int
    c: Optional[float]
    by_season: Mapping[int, float]
    unit_all_season_mean: float
    n_season_from_unit_mean: int
    used_donor_mean: bool


@dataclass(frozen=True)
class RouteOutput:
    """A router's predictions in link space for the rows it scores: one column per grid point, plus
    the trees-off column, with fallback counts. Rows of a unit that was not fitted (short history,
    R12) hold NaN in both, so they cannot be read as a prediction."""
    row_positions: np.ndarray
    predictions: np.ndarray            # (rows, grid points)
    trees_off: np.ndarray              # (rows,)
    grid: Tuple[GridPoint, ...]
    n_units_fitted: int
    n_units_fallback: int
    n_rows_pool_fallback: int          # neighbour only


@dataclass(frozen=True)
class PerUnitRows:
    """One pass of the per-unit router over plain arrays, in link space.

    fit_*    the router's fit rows: every scored unit's own rows at or before ``cut`` with a finite
             label (R30), in the order the unit's rows should be read (step order)
               fit_unit (n,) unit id; fit_time (n,) integer step; fit_y (n,) link(y);
               fit_normal (n,) the unit's link-matched normal on the row (R15, from fit rows only);
               fit_context (n, c) standardised context (router_standardisation) or None;
               fit_keys (n,) int64 row keys of the tree answers to use for the row
    score_*  the rows to predict, after ``cut``: score_unit, score_time, score_normal,
             score_context, score_keys as above; score_rows (m,) the caller's positions of these
             rows, returned as RouteOutput.row_positions
    unit_group  {unit id: its group}, for every scored unit
    Units are routed in the order of their first score row."""
    cut: int
    fit_unit: np.ndarray
    fit_time: np.ndarray
    fit_y: np.ndarray
    fit_normal: np.ndarray
    fit_context: Optional[np.ndarray]
    fit_keys: np.ndarray
    score_unit: np.ndarray
    score_time: np.ndarray
    score_normal: np.ndarray
    score_context: Optional[np.ndarray]
    score_keys: np.ndarray
    score_rows: np.ndarray
    unit_group: Mapping[str, str]


@dataclass(frozen=True)
class RouterTreeColumns:
    """The tree columns each group's routers may use.

    tree_group        the group that owns each bank tree, in bank (column) order
    blocks            the overlap blocks: a partition of the groups into sorted tuples (derive_overlap_
                      blocks' members); every tree's group and every router group is in one block
    columns_by_group  {group: bank positions its routers use, ascending}: exactly the trees whose
                      group is not one of its router groups (router_tree_columns)
    router_groups     {group: its own groups}: whole overlap blocks, its own block included (L2 rule
                      4); every fit asserts that no used column belongs to one of them (G-DISJOINT)
    own_block_tree_columns builds it from the blocks. A direct construction is checked the same way:
    router groups that split a block, a column of an own-block tree and a mask that drops any other
    tree are refused. The router also checks tree_group against the store's own record of its trees
    (physical keys) on every call."""
    tree_group: Tuple[str, ...]
    blocks: Tuple[Tuple[str, ...], ...]
    columns_by_group: Mapping[str, np.ndarray]
    router_groups: Mapping[str, Tuple[str, ...]]

    def __post_init__(self):
        owners = _owners(self.tree_group)
        n = owners.size
        block_of = _block_index(self.blocks)
        loose = sorted(set(owners.tolist()) - set(block_of))
        if loose:
            raise RouteRefusal("G-DISJOINT", "tree group(s) %s are in no overlap block" % loose[:10],
                               fix="pass the blocks of every group (derive_overlap_blocks)")
        if not isinstance(self.columns_by_group, abc.Mapping) or \
                not isinstance(self.router_groups, abc.Mapping):
            raise RouteRefusal("R14", "columns_by_group and router_groups must be mappings")
        for group, cols in self.columns_by_group.items():
            _require_name(group, "a group")
            if group not in self.router_groups:
                raise RouteRefusal("G-DISJOINT", "group %r has tree columns but no router groups" % group,
                                   fix="give every group its whole overlap block")
            rg = tuple(self.router_groups[group])
            if group not in rg:
                raise RouteRefusal("G-DISJOINT", "group %r is not among its own router groups %s"
                                   % (group, rg))
            for g in rg:
                _require_name(g, "a router group of group %r" % group)
                if g not in block_of:
                    raise RouteRefusal("G-DISJOINT", "router group %r of group %r is in no overlap "
                                                     "block" % (g, group))
            split = sorted(set(m for g in rg for m in block_of[g]) - set(rg))
            if split:
                raise RouteRefusal("G-DISJOINT", "the router groups %s of group %r split an overlap "
                                   "block: its block-mate(s) %s are missing, so their trees would be "
                                   "used" % (rg, group, split),
                                   fix="router groups are whole overlap blocks (own_block_tree_columns)")
            arr = np.asarray(cols)
            if arr.ndim != 1 or arr.dtype.kind not in "iu" or arr.size == 0:
                raise RouteRefusal("R14", "group %r: tree columns must be a non-empty 1-D integer "
                                          "array" % group)
            if int(arr.min()) < 0 or int(arr.max()) >= n or np.any(np.diff(arr) <= 0):
                raise RouteRefusal("R14", "group %r: tree columns must be ascending, unique bank "
                                          "positions in [0, %d)" % (group, n))
            assert_no_own_group_column(owners[arr], rg, "group %s" % group)
            want = np.flatnonzero(~np.isin(owners, np.asarray(rg, dtype=object)))
            if not np.array_equal(arr, want):
                raise RouteRefusal("R14", "group %r: the mask keeps %d tree column(s), but every tree "
                                   "outside its router groups %s is %d; a router drops its own block's "
                                   "trees and nothing else" % (group, arr.size, rg, want.size),
                                   fix="build the mask with own_block_tree_columns")
        # frozen after the checks: read-only copies, so a checked mask cannot change afterwards
        cols_ro = {}
        for group, cols in self.columns_by_group.items():
            arr = np.array(cols, dtype=np.int64)
            arr.setflags(write=False)
            cols_ro[group] = arr
        object.__setattr__(self, "tree_group", tuple(owners.tolist()))
        object.__setattr__(self, "blocks", tuple(tuple(b) for b in self.blocks))
        object.__setattr__(self, "columns_by_group", MappingProxyType(cols_ro))
        object.__setattr__(self, "router_groups", MappingProxyType(
            {g: tuple(v) for g, v in self.router_groups.items()}))


# ---------------------------------------------------------------------------------------------------
# small helpers
def _require_name(value, what):
    if not isinstance(value, str) or not value:
        raise RouteRefusal("R14", "%s must be a non-empty string, got %r" % (what, value))
    return value


def _as_float_vector(values, what, n=None):
    arr = np.asarray(values)
    if arr.ndim != 1:
        raise RouteRefusal("R14", "%s must be one-dimensional, got shape %s" % (what, arr.shape))
    if arr.dtype.kind not in "fiu":
        raise RouteRefusal("R14", "%s must be numeric, got dtype %s" % (what, arr.dtype))
    if n is not None and arr.shape[0] != n:
        raise RouteRefusal("R14", "%s has %d rows, expected %d" % (what, arr.shape[0], n))
    return np.asarray(arr, dtype=np.float64)


def _require_finite(arr, what, rule):
    if arr.size and not np.all(np.isfinite(arr)):
        bad = int(np.size(arr) - np.count_nonzero(np.isfinite(arr)))
        raise RouteRefusal(rule, "%s holds %d missing or infinite value(s)" % (what, bad),
                           fix="leave rows with a missing label out of the fit rows (R30); "
                               "normals, context and tree answers must be finite")


def _router_workers():
    if _TEST_ONLY_ROUTER_WORKERS is not None:
        workers = _TEST_ONLY_ROUTER_WORKERS
        if not isinstance(workers, Integral) or int(workers) < 1:
            raise RouteRefusal("C14", "test-only router workers must be a positive integer, got %r"
                               % (workers,))
        return int(workers)
    return int(K.ROUTER_WORKERS)


# ---------------------------------------------------------------------------------------------------
# The grid (R14, R26)
def per_unit_grid(has_context):
    """The per-unit grid: every (level, ratio) of the engine constants, level-major (35 points), or
    the 7 levels with ratio None when no context is declared."""
    levels = tuple(float(v) for v in K.PENALTY_LEVELS)
    if not has_context:
        return tuple(GridPoint(level, None) for level in levels)
    ratios = tuple(float(v) for v in K.PENALTY_RATIOS)
    return tuple(GridPoint(level, ratio) for level in levels for ratio in ratios)


def per_unit_centre(has_context):
    """The centre point: level 1 and, with context, the ratio that makes a_ctx the context centre
    (context centre / trees centre). Refuses engine constants whose centre is not a grid point."""
    ratio = None
    if has_context:
        ratio = float(K.PER_UNIT_CONTEXT_CENTRE) / float(K.PER_UNIT_TREES_CENTRE)
    point = GridPoint(1.0, ratio)
    if point not in per_unit_grid(has_context):
        raise RouteRefusal("C12", "the per-unit centre %s is not a point of the grid" % (point,),
                           fix="the engine constants C12 must put the centres on the grid")
    return point


def point_penalties(point, has_context):
    """(a_tree, a_ctx) of one grid point: a_tree = trees centre x level, a_ctx = a_tree x ratio (0.0
    without context, where no context block exists). Refuses a point that is not on the grid."""
    if not isinstance(point, GridPoint) or point not in per_unit_grid(has_context):
        raise RouteRefusal("R26", "%r is not a point of the per-unit grid (%s context)"
                           % (point, "with" if has_context else "without"),
                           fix="penalties come from the engine grid only; no point is hand-set")
    a_tree = K.PER_UNIT_TREES_CENTRE * point.level
    if point.ratio is None:
        return a_tree, 0.0
    return a_tree, a_tree * point.ratio


def per_unit_router_design(has_context):
    """R14 per-unit layout: intercept, normal (unpenalised), context (if declared), trees."""
    columns = (INTERCEPT, NORMAL, CONTEXT, TREES) if has_context else (INTERCEPT, NORMAL, TREES)
    return RouterDesign(kind=RouterKind.PER_UNIT, columns=columns, unpenalised=(INTERCEPT, NORMAL),
                        centre=(float(K.PER_UNIT_TREES_CENTRE), float(K.PER_UNIT_CONTEXT_CENTRE)),
                        grid=per_unit_grid(has_context), fit_row_cap=None)


def trees_off_router_design():
    """R16 layout: intercept + normal only (context dropped, no tree block, no penalty)."""
    return RouterDesign(kind=RouterKind.PER_UNIT, columns=(INTERCEPT, NORMAL),
                        unpenalised=(INTERCEPT, NORMAL), centre=(), grid=(), fit_row_cap=None)


# ---------------------------------------------------------------------------------------------------
# Columns (R14) and standardisation (R20)
# Provenance: plan 2.2 R14; pm25_adaptation.py:409-414 (np.column_stack of intercept, normal minus its
# fit-row mean, standardised context, tree answers as float64).
def build_column_block(design, normal, context, trees, normal_centre):
    """Build one router design matrix in the layout the design names (fit and score rows alike).

    The normal column is normal - normal_centre (the fit-row mean, applied to fit and score rows);
    context is already standardised; trees are the tree answers, upcast to float64. Refuses a block
    the design does not list, a missing block it does list, mismatched rows or a non-finite value.
    """
    if not isinstance(design, RouterDesign):
        raise RouteRefusal("R14", "design must be a RouterDesign, got %s" % type(design).__name__)
    unknown = [c for c in design.columns if c not in BLOCK_NAMES]
    if unknown or len(set(design.columns)) != len(design.columns) or not design.columns:
        raise RouteRefusal("R14", "design columns %s are not an ordered set of %s"
                           % (design.columns, BLOCK_NAMES))
    given = {NORMAL: normal is not None, CONTEXT: context is not None, TREES: trees is not None}
    for name, present in given.items():
        if present and name not in design.columns:
            raise RouteRefusal("R14", "a %s block was given, but the design lists %s"
                               % (name, design.columns))
        if not present and name in design.columns:
            raise RouteRefusal("R14", "the design lists a %s block, but none was given" % name)
    n = None
    blocks_in = {}
    if normal is not None:
        nv = _as_float_vector(normal, "normal")
        _require_finite(nv, "the normal column", "R15")
        if normal_centre is None or not isinstance(normal_centre, Real) or not math.isfinite(normal_centre):
            raise RouteRefusal("R14", "the normal column needs a finite fit-row centre, got %r"
                               % (normal_centre,))
        n = nv.shape[0]
        blocks_in[NORMAL] = nv - normal_centre
    if context is not None:
        cv = np.asarray(context, dtype=np.float64)
        if cv.ndim != 2 or cv.shape[1] == 0:
            raise RouteRefusal("R14", "context must be (rows, columns) with at least one column, "
                                      "got shape %s" % (cv.shape,))
        _require_finite(cv, "the context block", "R20")
        if n is not None and cv.shape[0] != n:
            raise RouteRefusal("R14", "context has %d rows, the normal %d" % (cv.shape[0], n))
        n = cv.shape[0] if n is None else n
        blocks_in[CONTEXT] = cv
    if trees is not None:
        tv = np.asarray(trees)
        if tv.ndim != 2 or tv.shape[1] == 0 or tv.dtype.kind != "f":
            raise RouteRefusal("R14", "trees must be (rows, columns) of floats with at least one "
                                      "column, got shape %s dtype %s" % (tv.shape, tv.dtype))
        if n is not None and tv.shape[0] != n:
            raise RouteRefusal("R14", "trees have %d rows, the other blocks %d" % (tv.shape[0], n))
        tv = np.asarray(tv, np.float64)
        _require_finite(tv, "the tree block", "R14")
        n = tv.shape[0] if n is None else n
        blocks_in[TREES] = tv
    if n is None:
        raise RouteRefusal("R14", "a design needs at least one data block to know its rows")
    pieces, blocks = [], []
    for name in design.columns:
        if name == INTERCEPT:
            pieces.append(np.ones(n))
            blocks.append(INTERCEPT)
        elif name == NORMAL:
            pieces.append(blocks_in[NORMAL])
            blocks.append(NORMAL)
        else:
            pieces.append(blocks_in[name])
            blocks.extend([name] * blocks_in[name].shape[1])
    return DesignMatrix(X=np.column_stack(pieces), blocks=tuple(blocks))


# Provenance: plan 2.3 R20; pm25_adaptation.py:335, 395 (Ch.mean(0), Ch.std(0) + 1e-9 over all fit rows
# of the pass, on a C-ordered float64 array).
def router_standardisation(fit_rows, context):
    """Mean and standard deviation (+ CONTEXT_SD_OFFSET) of each context column over the router's
    fit rows at the cut: ALL fit rows of the pass, never one batch.

    fit_rows needs ``cut`` and ``times`` (FitContext.router_rows gives both). Refuses a row after the
    cut, a shape mismatch and a non-finite context value."""
    cut = getattr(fit_rows, "cut", None)
    times = getattr(fit_rows, "times", None)
    if not isinstance(cut, Integral) or times is None:
        raise RouteRefusal("R20", "fit_rows must carry an integer cut and the rows' times")
    t = np.asarray(times)
    if t.ndim != 1 or t.dtype.kind not in "iu":
        raise RouteRefusal("R20", "fit row times must be a 1-D integer array")
    if t.size == 0:
        raise RouteRefusal("R20", "no fit rows: the scalers cannot be fitted")
    if int(t.max()) > int(cut):
        raise RouteRefusal("G-FITCUT", "%d fit row(s) lie after the cut %d; scalers see only rows at "
                           "or before it" % (int(np.count_nonzero(t > cut)), int(cut)))
    C = np.ascontiguousarray(np.asarray(context, dtype=np.float64))
    if C.ndim != 2 or C.shape[0] != t.size or C.shape[1] == 0:
        raise RouteRefusal("R20", "context must be (fit rows, columns) = (%d, >=1), got %s"
                           % (t.size, C.shape))
    _require_finite(C, "the context on fit rows", "R20")
    return C.mean(0), C.std(0) + CONTEXT_SD_OFFSET


def standardise_context(context, mean, sd):
    """(context - mean) / sd with the constants of router_standardisation (fit and score rows)."""
    C = np.ascontiguousarray(np.asarray(context, dtype=np.float64))
    mean = np.asarray(mean, dtype=np.float64)
    sd = np.asarray(sd, dtype=np.float64)
    if C.ndim != 2 or mean.shape != (C.shape[1],) or sd.shape != (C.shape[1],):
        raise RouteRefusal("R20", "context %s does not match constants %s / %s"
                           % (C.shape, mean.shape, sd.shape))
    return (C - mean) / sd


# ---------------------------------------------------------------------------------------------------
# The normal (R15) and trees-off (R16)
# Provenance: plan 2.2 R15; pm25_adaptation.py:584-604 (per cell-month mean over the given rows ONLY;
# fallbacks the cell's own mean, then the donor mean).
def season_normal(unit_id, link, cut, c, fit_times, fit_season_keys, fit_y_link, needed_season_keys,
                  donor_link_mean):
    """R15 on link-space values: the unit's normal per season key, the mean of link(y) over its own
    fit rows at or before the cut, however few. A season key with no fit row takes the unit's
    all-season mean (counted); a unit with no fit row takes the donor mean (used_donor_mean).

    The table covers the needed keys and every key of the fit rows. Refuses a fit row after the cut,
    a missing label on a fit row (R30), non-integer season keys and a non-finite donor mean."""
    _require_name(unit_id, "unit_id")
    if not isinstance(cut, Integral):
        raise RouteRefusal("R15", "cut must be an integer step, got %r" % (cut,))
    t = np.asarray(fit_times)
    keys = np.asarray(fit_season_keys)
    y = _as_float_vector(fit_y_link, "fit link(y)")
    if t.ndim != 1 or keys.ndim != 1 or t.shape != y.shape or keys.shape != y.shape:
        raise RouteRefusal("R15", "fit times, season keys and link(y) must be 1-D and equally long")
    if y.size and (t.dtype.kind not in "iu" or keys.dtype.kind not in "iu"):
        raise RouteRefusal("R15", "fit times and season keys must be integers")
    if y.size and int(t.max()) > int(cut):
        raise RouteRefusal("G-FITCUT", "unit %s: %d fit row(s) after the cut %d"
                           % (unit_id, int(np.count_nonzero(t > cut)), int(cut)))
    _require_finite(y, "unit %s fit link(y)" % unit_id, "R30")
    needed = np.asarray(needed_season_keys)
    if needed.ndim != 1 or (needed.size and needed.dtype.kind not in "iu"):
        raise RouteRefusal("R15", "needed season keys must be a 1-D integer array")
    if not isinstance(donor_link_mean, Real) or not math.isfinite(donor_link_mean):
        raise RouteRefusal("R15", "the donor link mean must be finite, got %r" % (donor_link_mean,))
    all_keys = sorted(set(int(k) for k in needed.tolist()) | set(int(k) for k in keys.tolist()))
    if y.size == 0:
        by = {k: float(donor_link_mean) for k in all_keys}
        return NormalTable(unit_id=unit_id, link=link, cut=int(cut), c=c, by_season=by,
                           unit_all_season_mean=float(donor_link_mean),
                           n_season_from_unit_mean=0, used_donor_mean=True)
    unit_mean = float(y.mean())
    by, from_unit = {}, 0
    for k in all_keys:
        mask = keys == k
        if mask.any():
            by[k] = float(y[mask].mean())
        else:
            by[k] = unit_mean
            from_unit += 1
    return NormalTable(unit_id=unit_id, link=link, cut=int(cut), c=c, by_season=by,
                       unit_all_season_mean=unit_mean, n_season_from_unit_mean=from_unit,
                       used_donor_mean=False)


def normal_values(table, season_keys):
    """The normal of each row from its season key (a key missing from the table is refused)."""
    keys = np.asarray(season_keys)
    if keys.ndim != 1:
        raise RouteRefusal("R15", "season keys must be one-dimensional")
    missing = sorted(set(int(k) for k in keys.tolist()) - set(table.by_season))
    if missing:
        raise RouteRefusal("R15", "unit %s has no normal for season key(s) %s" % (table.unit_id,
                                                                                  missing[:10]),
                           fix="list every key the rows need in needed_season_keys")
    return np.array([table.by_season[int(k)] for k in keys.tolist()], dtype=np.float64)


R36_FLOOR_RULE = ("owner ruling O4 (owner rulings, section O): the R36 tolerance is max(k x s, "
                  "C9.k_min_multiple_of_arith_error x C9.measured_arith_error); the floor (10 x 9e-8 = 9e-7) keeps "
                  "a small s from pushing k x s below the measured rounding error")


def r36_floor():
    """Owner ruling O4: the floor under every R36 tolerance, C9.k_min_multiple_of_arith_error x
    C9.measured_arith_error, read from the constants registry at each call."""
    return float(K.get("C9.k_min_multiple_of_arith_error")) * float(K.get("C9.measured_arith_error"))


def r36_tolerance(donor_link_sd):
    """R36: max(k x s, floor), s the donor-row standard deviation of link(y), k = C9.guard_tolerance_k
    (UnsetConstantError while unset) and the floor of owner ruling O4 (r36_floor)."""
    k = K.get("C9.guard_tolerance_k")
    s = float(donor_link_sd)
    if not math.isfinite(s) or s <= 0:
        raise RouteRefusal("R36", "the donor link standard deviation must be finite and positive, "
                                  "got %r" % (donor_link_sd,))
    return max(k * s, r36_floor())          # owner ruling O4: the floor


def _check_tolerance(tolerance):
    if not isinstance(tolerance, Real) or not math.isfinite(tolerance) or tolerance <= 0:
        raise RouteRefusal("R36", "the trees-off identity needs a finite positive tolerance "
                                  "(R36: k x s), got %r" % (tolerance,))
    return float(tolerance)


def _trees_off(fit_normal, fit_y_link, score_normal):
    """Intercept + normal, unweighted, on the fit rows; predictions on the score rows."""
    centre = fit_normal.mean()
    design = trees_off_router_design()
    Xc = build_column_block(design, fit_normal, None, None, centre).X
    Xt = build_column_block(design, score_normal, None, None, centre).X
    return S.solve_point(Xc, fit_y_link, Xt, 0, 0, 0.0, 0.0)


# Provenance: plan 2.2 R16; 9.1 item 2a; pm25_adaptation.py:436-442.
def _trees_off_checked(fit_normal, fit_y_link, score_normal, tolerance, router_id="the unit"):
    """R16 trees-off: intercept + normal only, unweighted, context dropped, fitted on the unit's fit
    rows; predictions (link space) on the score rows. It equals the normal: any score row further
    than ``tolerance`` (R36, k x s) from score_normal is refused (RouteGuardError).

    PRIVATE: the body of the approved trees_off_with_normal, with the R36 tolerance as an input (the
    approved signature has none; owner decision pending)."""
    tol = _check_tolerance(tolerance)
    fn = _as_float_vector(fit_normal, "fit normal")
    fy = _as_float_vector(fit_y_link, "fit link(y)", fn.shape[0])
    sn = _as_float_vector(score_normal, "score normal")
    _require_finite(fy, "fit link(y)", "R30")
    if fn.shape[0] < 2:
        raise RouteRefusal("R16", "trees-off needs at least 2 fit rows, got %d" % fn.shape[0])
    p = _trees_off(fn, fy, sn)
    dev = float(np.max(np.abs(p - sn))) if p.size else 0.0
    if not dev <= tol:
        raise RouteGuardError("R16: %s: trees-off differs from its normal by %.3g, beyond the tolerance "
                              "%.3g; intercept + normal must reproduce the normal" % (router_id, dev, tol))
    return p


def trees_off_with_normal(fit_normal, fit_y_link, score_normal):
    """R16 trees-off for kinds with a normal (APPROVED signature). Not callable yet: the contract
    asserts the identity within the R36 tolerance, k x s, but s (the donor-row sd of link(y)) is not
    one of the inputs and k (C9) is unset. Raises NotImplementedError until the owner rules how the
    tolerance reaches this function (proposed: a keyword ``tolerance``); the router kernels use
    _trees_off_checked, which takes it."""
    raise NotImplementedError(
        "trees_off_with_normal asserts trees-off = normal within the R36 tolerance k x s, but its "
        "approved signature carries neither s (the donor-row sd of link(y)) nor a tolerance, and k "
        "(C9.guard_tolerance_k) is unset: owner decision pending (proposed: a keyword 'tolerance'). "
        "The router kernels use _trees_off_checked(fit_normal, fit_y_link, score_normal, tolerance)")


# Provenance: plan 2.2 R16 (guard reference = each arm's own-link trees-off; decline target = the
# identity-link trees-off).
def reference_predictions(trees_off_by_link):
    """R16 references in y units: ({link: guard reference}, decline target). The guard reference of a
    link is that link's trees-off (already back-transformed and clipped); the decline target is the
    identity entry. Refuses a map without an identity entry."""
    refs, target = {}, None
    for link, values in trees_off_by_link.items():
        arr = _as_float_vector(values, "trees-off of %s" % (link,))
        refs[link] = arr
        if getattr(link, "value", link) == "identity":
            target = arr
    if target is None:
        raise RouteRefusal("R16", "no identity-link trees-off: the decline target is undefined")
    return refs, target


# ---------------------------------------------------------------------------------------------------
# Short history (R12)
# Provenance: plan 2.2 R12 (fewer than 24 valid rows -> the group's region router; counted; flagged
# above 5%); replaces the donor-wide mean at pm25_adaptation.py:342-344.
def fallback_units(valid_fit_rows):
    """(Units with fewer than PER_UNIT_MIN_VALID_ROWS valid fit rows, sorted; their share). The share
    is flagged above FALLBACK_FLAG_SHARE (report only; fallback_share_flagged)."""
    if not valid_fit_rows:
        raise RouteRefusal("R12", "no units: the fallback share is undefined")
    short = []
    for unit, n in valid_fit_rows.items():
        _require_name(unit, "a unit id")
        if not isinstance(n, Integral) or int(n) < 0:
            raise RouteRefusal("R12", "unit %s: valid fit rows must be a count, got %r" % (unit, n))
        if int(n) < K.PER_UNIT_MIN_VALID_ROWS:
            short.append(unit)
    return tuple(sorted(short)), len(short) / float(len(valid_fit_rows))


def fallback_share_flagged(share):
    """Whether a fallback share is above the C10 flag share (report only, never a choice)."""
    return float(share) > K.FALLBACK_FLAG_SHARE


def valid_fit_rows(rows):
    """{scored unit: its number of fit rows} for a PerUnitRows (every fit row has a finite label)."""
    plan, short = per_unit_plan(rows)
    counts = {item[0]: int(item[2].size) for item in plan}
    for unit, n in short:
        counts[unit] = int(n)
    return counts


# ---------------------------------------------------------------------------------------------------
# The own-overlap-block column mask (R14, LORO; G-DISJOINT)
def _owners(tree_group):
    owners = np.asarray(list(tree_group), dtype=object)
    if owners.ndim != 1 or owners.size == 0:
        raise RouteRefusal("R14", "the bank's tree groups must be a non-empty sequence")
    for g in owners.tolist():
        _require_name(g, "a tree's group")
    return owners


def _block_index(blocks):
    """{group: its block} for a partition of the groups into sorted, non-empty tuples of names;
    refuses anything else (a group in two blocks, an unsorted or empty block)."""
    if isinstance(blocks, (str, bytes)) or blocks is None:
        raise RouteRefusal("G-DISJOINT", "blocks must be a sequence of group tuples, got %r" % (blocks,))
    index = {}
    for block in blocks:
        if isinstance(block, (str, bytes)):
            raise RouteRefusal("G-DISJOINT", "a block must be a tuple of groups, got the string %r"
                               % (block,))
        members = tuple(block)
        if not members or members != tuple(sorted(members)):
            raise RouteRefusal("G-DISJOINT", "block %r is empty or not sorted by name" % (members,))
        for g in members:
            _require_name(g, "a block member")
            if g in index:
                raise RouteRefusal("G-DISJOINT", "group %r is in two blocks, %s and %s"
                                   % (g, index[g], members),
                                   fix="the blocks are the connected components of "
                                       "derive_overlap_blocks: every group is in exactly one")
            index[g] = members
    if not index:
        raise RouteRefusal("G-DISJOINT", "no overlap blocks given")
    return index


# Provenance: owner rulings D and E (L2 rule 4); plan 2.2 R14, 2.3 R20.
def router_tree_columns(tree_group, router_groups):
    """The tree columns a router may use: every tree whose group is not one of the router's own
    groups (its whole overlap block), in bank order. int64, ascending.

    Refuses empty router_groups, a router group that owns no tree in the bank (under leave one region
    out every group trains trees, so the name is wrong; near-miss spellings are named) and an empty
    result. CONTRACT GAP (owner): the approved contract also refuses router groups that split a
    block, but its signature has no blocks input, so it cannot; that check is made where the blocks
    are known, by own_block_tree_columns and RouterTreeColumns, which is the only mask the router
    accepts."""
    owners = _owners(tree_group)
    groups = tuple(router_groups)
    if not groups:
        raise RouteRefusal("G-DISJOINT", "a router needs its own groups (its overlap block)")
    present = set(owners.tolist())
    for g in groups:
        _require_name(g, "a router group")
        if g not in present:
            near = sorted(o for o in present if o != g and o.strip().casefold() == g.strip().casefold())
            raise RouteRefusal("G-DISJOINT", "router group %r owns no tree in the bank%s; under leave one "
                               "region out every group trains its own trees, so the mask would drop "
                               "nothing" % (g, (" (did you mean %s?)" % " or ".join(repr(x) for x in near))
                                             if near else ""),
                               fix="pass the group names exactly as the bank's tree groups hold them")
    keep = np.flatnonzero(~np.isin(owners, np.asarray(groups, dtype=object))).astype(np.int64)
    if keep.size == 0:
        raise RouteRefusal("G-DISJOINT", "the router's block %s owns every tree of the bank" % (groups,))
    assert_no_own_group_column(owners[keep], groups, "block %s" % (groups,))
    return keep


# Provenance: plan 5 G-DISJOINT (LORO row: asserted on every router fit).
def assert_no_own_group_column(column_tree_group, router_groups, router_id):
    """Refuse a router fit whose tree columns include one of its own groups' trees (raised even under
    python -O), naming the router and the columns."""
    groups = set(router_groups)
    if not groups:
        raise RouteGuardError("G-DISJOINT: router %s has no own groups to check against" % (router_id,))
    col_groups = np.asarray(column_tree_group, dtype=object)
    if col_groups.ndim != 1:
        raise RouteGuardError("G-DISJOINT: router %s: column groups must be one-dimensional" % (router_id,))
    bad = np.flatnonzero(np.isin(col_groups, np.asarray(sorted(groups), dtype=object)))
    if bad.size:
        raise RouteGuardError(
            "G-DISJOINT: router %s holds %d tree column(s) of its own block %s (first design "
            "columns: %s); a group's trees answer its own units in-bag"
            % (router_id, bad.size, sorted(groups), ", ".join(str(int(v)) for v in bad[:10])))


def own_block_tree_columns(tree_group, block_of_group):
    """RouterTreeColumns for leave one region out: each group's routers use every tree outside its
    overlap block. block_of_group maps EVERY group to its whole block ({g: split.block_of_group(
    blocks, g)} over derive_overlap_blocks' groups); a mapping that does not give every member of a
    block the same block is refused (it would split a block), and so is a tree group with no block."""
    owners = _owners(tree_group)
    if not isinstance(block_of_group, abc.Mapping) or not block_of_group:
        raise RouteRefusal("G-DISJOINT", "block_of_group must map every group to its overlap block")
    cols, rgroups, blocks = {}, {}, set()
    for group, block in block_of_group.items():
        _require_name(group, "a group")
        members = tuple(sorted(block))
        if group not in members:
            raise RouteRefusal("G-DISJOINT", "group %r is not in its own block %s" % (group, members))
        for m in members:
            other = block_of_group.get(m)
            if other is None or tuple(sorted(other)) != members:
                raise RouteRefusal("G-DISJOINT", "block %s of group %r is not the block of its member "
                                   "%r (%s): the blocks would be split" % (members, group, m, other),
                                   fix="pass the connected components of derive_overlap_blocks")
        blocks.add(members)
        cols[group] = router_tree_columns(owners.tolist(), members)
        rgroups[group] = members
    return RouterTreeColumns(tree_group=tuple(owners.tolist()), blocks=tuple(sorted(blocks)),
                             columns_by_group=cols, router_groups=rgroups)


# ---------------------------------------------------------------------------------------------------
# The per-unit router (R12, R14-R16, R20, R26; plan 4.5 speedup 3)
def _check_keys(keys, what, n):
    arr = np.asarray(keys)
    if arr.ndim != 1 or arr.shape[0] != n or (n and arr.dtype.kind not in "iu"):
        raise RouteRefusal("R20", "%s must be a 1-D integer array of %d row keys" % (what, n))
    if n and int(arr.min()) < 0:
        raise RouteRefusal("R20", "%s holds a negative row key (a missing predecessor)" % what)
    return arr.astype(np.int64, copy=False)


def _check_context(ctx, what, n):
    if ctx is None:
        return None
    arr = np.asarray(ctx, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[0] != n or arr.shape[1] == 0:
        raise RouteRefusal("R20", "%s must be (%d, >=1), got %s" % (what, n, arr.shape))
    _require_finite(arr, what, "R20")
    return arr


def _check_rows(rows):
    if not isinstance(rows, PerUnitRows):
        raise RouteRefusal("R14", "rows must be PerUnitRows, got %s" % type(rows).__name__)
    if not isinstance(rows.cut, Integral):
        raise RouteRefusal("G-FITCUT", "the cut must be an integer step, got %r" % (rows.cut,))
    fu = np.asarray(rows.fit_unit)
    su = np.asarray(rows.score_unit)
    nf, ns = fu.shape[0] if fu.ndim == 1 else -1, su.shape[0] if su.ndim == 1 else -1
    if nf < 0 or ns < 0:
        raise RouteRefusal("R14", "fit_unit and score_unit must be one-dimensional")
    if ns == 0:
        raise RouteRefusal("R14", "no score rows: nothing to route")
    ft, st = np.asarray(rows.fit_time), np.asarray(rows.score_time)
    if ft.shape != (nf,) or st.shape != (ns,) or (nf and ft.dtype.kind not in "iu") \
            or st.dtype.kind not in "iu":
        raise RouteRefusal("G-FITCUT", "fit and score times must be 1-D integer arrays of the rows")
    cut = int(rows.cut)
    if nf and int(ft.max()) > cut:
        raise RouteRefusal("G-FITCUT", "%d fit row(s) lie after the cut %d"
                           % (int(np.count_nonzero(ft > cut)), cut),
                           fix="the router fits only on rows at or before the cut")
    if int(st.min()) <= cut:
        raise RouteRefusal("G-FITCUT", "%d score row(s) lie at or before the cut %d; a fit row would "
                           "be scored" % (int(np.count_nonzero(st <= cut)), cut))
    fy = _as_float_vector(rows.fit_y, "fit_y", nf)
    _require_finite(fy, "fit link(y)", "R30")
    fn = _as_float_vector(rows.fit_normal, "fit_normal", nf)
    sn = _as_float_vector(rows.score_normal, "score_normal", ns)
    _require_finite(fn, "the fit normal", "R15")
    _require_finite(sn, "the score normal", "R15")
    fc = _check_context(rows.fit_context, "fit context", nf)
    sc = _check_context(rows.score_context, "score context", ns)
    if (fc is None) != (sc is None) or (fc is not None and fc.shape[1] != sc.shape[1]):
        raise RouteRefusal("R14", "fit and score rows must carry the same context columns")
    fk = _check_keys(rows.fit_keys, "fit_keys", nf)
    sk = _check_keys(rows.score_keys, "score_keys", ns)
    sr = np.asarray(rows.score_rows)
    if sr.shape != (ns,):
        raise RouteRefusal("R14", "score_rows must hold one position per score row")
    return {"fu": fu, "su": su, "fy": fy, "fn": fn, "sn": sn, "fc": fc, "sc": sc, "fk": fk,
            "sk": sk, "ns": ns}


def per_unit_plan(rows, _checked=None):
    """The unit plan of a pass, fixed serially: [(unit, group, fit positions, score positions)] for
    the units that are fitted, in the order of their first score row, and [(unit, fit rows)] for the
    short-history units (fewer than PER_UNIT_MIN_VALID_ROWS fit rows; not fitted, R12). Fit positions
    keep the rows' order."""
    chk = _check_rows(rows) if _checked is None else _checked
    fu, su = chk["fu"], chk["su"]
    uniq, first = np.unique(su, return_index=True)
    order = uniq[np.argsort(first, kind="stable")]
    fcode = np.full(fu.shape[0], -1, dtype=np.int64)
    if fu.shape[0]:
        pos = np.searchsorted(uniq, fu)
        pos_c = np.minimum(pos, uniq.size - 1)
        hit = uniq[pos_c] == fu
        fcode[hit] = pos_c[hit]
    fsort = np.argsort(fcode, kind="stable")
    fcs = fcode[fsort]
    scode = np.searchsorted(uniq, su)
    ssort = np.argsort(scode, kind="stable")
    scs = scode[ssort]
    plan, short = [], []
    for unit in order.tolist():
        if not isinstance(unit, str):
            unit_s = str(unit)
        else:
            unit_s = unit
        code = int(np.searchsorted(uniq, unit))
        group = rows.unit_group.get(unit, rows.unit_group.get(unit_s))
        if group is None:
            raise RouteRefusal("R14", "scored unit %s has no group in unit_group" % unit_s)
        _require_name(group, "the group of unit %s" % unit_s)
        lo, hi = np.searchsorted(fcs, code, "left"), np.searchsorted(fcs, code, "right")
        hidx = fsort[lo:hi]
        lo, hi = np.searchsorted(scs, code, "left"), np.searchsorted(scs, code, "right")
        tsel = ssort[lo:hi]
        if hidx.size < K.PER_UNIT_MIN_VALID_ROWS:
            short.append((unit_s, int(hidx.size)))
            continue
        plan.append((unit_s, group, hidx, tsel))
    return plan, short


def _assert_blas_threads(limit, when):
    """Every BLAS library loaded in the process runs at ``limit`` thread(s) (C14), or the run stops."""
    from threadpoolctl import threadpool_info

    over = [(str(d.get("filepath")), d.get("num_threads")) for d in threadpool_info()
            if d.get("user_api") == "blas" and d.get("num_threads") != limit]
    if over:
        raise RouteGuardError("C14: %s the router loop, BLAS librar(ies) %s run at other than %d "
                              "thread(s); the loop runs at ROUTER_WORKER_BLAS_THREADS so its bytes do "
                              "not depend on the worker count" % (when, over, limit))


def _solve_units(plan, load, solve, workers):
    """solve(load(item)) for every item; results in ITEM ORDER. BLAS is limited to
    ROUTER_WORKER_BLAS_THREADS for the whole loop at any worker count: scipy's BLAS (the triangular
    solves) is loaded BEFORE the limit is entered, so the limit covers it, and every loaded BLAS
    library is checked at the limit on entering and on leaving the loop. Loads run in the calling
    thread in item order, and a worker's exception is re-raised here when its result is collected."""
    from threadpoolctl import threadpool_limits

    S._solve_triangular()          # load scipy.linalg (and its BLAS) now, before the limit
    limit = int(K.ROUTER_WORKER_BLAS_THREADS)
    results = [None] * len(plan)
    with threadpool_limits(limits=limit, user_api="blas"):
        _assert_blas_threads(limit, "entering")
        if workers <= 1 or len(plan) <= 1:
            for i, item in enumerate(plan):
                results[i] = solve(load(item))
        else:
            window = 2 * workers
            pending = deque()
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="treeroute-router") as ex:
                try:
                    for i, item in enumerate(plan):
                        loaded = load(item)
                        pending.append((i, ex.submit(solve, loaded)))
                        while len(pending) >= window:
                            j, fut = pending.popleft()
                            results[j] = fut.result()
                    while pending:
                        j, fut = pending.popleft()
                        results[j] = fut.result()
                except BaseException:
                    for _, fut in pending:
                        fut.cancel()
                    raise
        _assert_blas_threads(limit, "leaving")
    return results


# Provenance: plan 5 G-DISJOINT ("the check is on physical keys, not only on labels").
def _check_mask_against_store(answers, tree_columns):
    """The mask's tree groups are the store's own record of its trees: the same bank size, and for
    every group the mask names (a tree's group or a router group) the same bank positions as the
    store's own_columns(group). A mislabelled mask would let a router use an own-block tree."""
    n_trees = getattr(answers, "n_trees", None)
    own_columns = getattr(answers, "own_columns", None)
    if isinstance(n_trees, bool) or not isinstance(n_trees, Integral) or not callable(own_columns):
        raise RouteRefusal("G-DISJOINT", "answers must be the tree-answer store: its n_trees and "
                                         "own_columns(group) are needed to check the mask against "
                                         "the store's trees")
    owners = np.asarray(tree_columns.tree_group, dtype=object)
    if owners.size != int(n_trees):
        raise RouteGuardError("G-DISJOINT: the mask lists %d trees, the store's bank holds %d"
                              % (owners.size, int(n_trees)))
    named = set(owners.tolist())
    for groups in tree_columns.router_groups.values():
        named.update(groups)
    bad = []
    for m in sorted(named):
        have = np.asarray(own_columns(m), dtype=np.int64)
        if have.ndim != 1 or not np.array_equal(have, np.flatnonzero(owners == m)):
            bad.append(m)
    if bad:
        raise RouteGuardError("G-DISJOINT: the mask's tree groups disagree with the store's own trees "
                              "for group(s) %s: a mask label is not the tree's physical group, so a "
                              "router could use an own-block tree" % bad[:10])


def _check_fit_weights(fit_weights, n_fit):
    """None (the unweighted arms) or one R25 weight per fit row of the pass (route.solve's check)."""
    if fit_weights is None:
        return None
    try:
        return S.check_row_weights(fit_weights, n_fit)
    except S.WeightRefusal as exc:
        raise RouteRefusal("R25", "fit_weights: %s" % exc,
                           fix="one weight per fit row, in the rows' order (fit.weights.weights_for_rows)") from None


def _route(rows, answers, table_kind, tree_columns, points, identity_tolerance, sweep, fit_weights=None,
           only_group=None):
    """only_group (plan R20's per-group batching): route only the units of that group. The unit plan, and
    the reference check on the first NVERIFY fitted units of the WHOLE pass, are fixed over every unit of
    ``rows`` first, so each routed unit's bytes are the ones the whole pass gives; the other units' rows
    come back NaN (n_units_fitted counts the group's units only)."""
    chk = _check_rows(rows)
    tol = _check_tolerance(identity_tolerance)
    fw = _check_fit_weights(fit_weights, chk["fu"].shape[0])
    if not isinstance(tree_columns, RouterTreeColumns):
        raise RouteRefusal("G-DISJOINT", "tree_columns must be RouterTreeColumns (the own-block mask)")
    if not callable(getattr(answers, "unit_view", None)):
        raise RouteRefusal("R20", "answers must be the tree-answer store (unit_view(row_keys, kind))")
    has_context = chk["fc"] is not None
    nctx = chk["fc"].shape[1] if has_context else 0
    design = per_unit_router_design(has_context)
    penalties = [point_penalties(p, has_context) for p in points]
    owners = np.asarray(tree_columns.tree_group, dtype=object)
    plan, short = per_unit_plan(rows, chk)
    if not plan:
        raise RouteRefusal("R12", "no scored unit has %d fit rows (%d unit(s), all short): this kernel "
                           "would fit no unit and route nothing; every unit needs the region fallback "
                           "router (route/region.py, milestone Tue 6 Oct), which pipeline/router.py "
                           "applies to such a pass without calling this kernel"
                           % (K.PER_UNIT_MIN_VALID_ROWS, len(short)),
                           fix="route the pass through pipeline/router.py (its fallback routers fill "
                               "an all-short pass)")
    _check_mask_against_store(answers, tree_columns)
    ns = chk["ns"]
    fy, fn, sn, fc, sc, fk, sk = (chk[k] for k in ("fy", "fn", "sn", "fc", "sc", "fk", "sk"))
    items = []
    for i, (unit, group, hidx, tsel) in enumerate(plan):
        if group not in tree_columns.columns_by_group:
            raise RouteRefusal("G-DISJOINT", "group %s of unit %s has no router tree columns"
                               % (group, unit))
        items.append((unit, group, hidx, tsel, sweep and i < S.NVERIFY))
    if only_group is not None:
        _require_name(only_group, "only_group")
        items = [it for it in items if it[1] == only_group]

    def load(item):
        unit, group, hidx, tsel, verify = item
        keys = np.concatenate([fk[hidx], sk[tsel]])
        view = answers.unit_view(keys, table_kind)
        view_group = getattr(view, "group", None)
        if view_group != group:
            raise RouteGuardError("G-DISJOINT: unit %s of group %s was answered from the table of group "
                                  "%s" % (unit, group, view_group))
        index = np.asarray(view.tree_index, dtype=np.int64)
        values = np.asarray(view.values)
        if values.ndim != 2 or values.shape != (keys.size, index.size):
            raise RouteRefusal("R20", "the store answered shape %s for %d rows and %d columns"
                               % (values.shape, keys.size, index.size))
        want = np.asarray(tree_columns.columns_by_group[group], dtype=np.int64)
        pos = np.searchsorted(index, want)
        pos_c = np.minimum(pos, index.size - 1)
        if index.size == 0 or not np.array_equal(index[pos_c], want):
            raise RouteGuardError("G-DISJOINT: unit %s needs tree column(s) the store does not answer "
                                  "for group %s (an own-group tree, or a column outside the bank)"
                                  % (unit, group))
        if not (pos_c.size == index.size and np.array_equal(pos_c, np.arange(index.size))):
            values = values[:, pos_c]
        assert_no_own_group_column(owners[want], tree_columns.router_groups[group], "unit %s" % unit)
        return item, values

    def solve(loaded):
        (unit, group, hidx, tsel, verify), values = loaded
        nf = hidx.size
        M = fn[hidx]
        centre = M.mean()
        ctx_f = fc[hidx] if has_context else None
        ctx_t = sc[tsel] if has_context else None
        Xc = build_column_block(design, M, ctx_f, np.asarray(values[:nf], np.float64), centre).X
        Xt = build_column_block(design, sn[tsel], ctx_t, np.asarray(values[nf:], np.float64),
                                centre).X
        y = fy[hidx]
        ntree = values.shape[1]
        if fw is None:
            if sweep:
                P = S.solve_grid(Xc, y, Xt, ntree, nctx, penalties, verify, unit_id=unit)
            else:
                a_tree, a_ctx = penalties[0]
                P = S.solve_point(Xc, y, Xt, ntree, nctx, a_tree, a_ctx)[:, None]
        else:
            # GLS arm (R24, R25): the weighted solve (route.solve, NEW formula for owner review); the
            # weights enter the fit rows only
            w = fw[hidx]
            if sweep:
                P = S.solve_grid_weighted(Xc, y, w, Xt, ntree, nctx, penalties, verify, unit_id=unit)
            else:
                a_tree, a_ctx = penalties[0]
                P = S.solve_point_weighted(Xc, y, w, Xt, ntree, nctx, a_tree, a_ctx)[:, None]
        # trees-off stays unweighted in every arm (R24: it keeps the identity with the normal)
        p0 = _trees_off_checked(M, y, sn[tsel], tol, "unit %s" % unit)
        return P, p0

    results = _solve_units(items, load, solve, _router_workers())
    out = np.full((ns, len(points)), np.nan)
    out0 = np.full(ns, np.nan)
    for (unit, group, hidx, tsel, verify), (P, p0) in zip(items, results):
        out[tsel, :] = P
        out0[tsel] = p0
    return RouteOutput(row_positions=np.asarray(rows.score_rows).copy(), predictions=out,
                       trees_off=out0, grid=tuple(points), n_units_fitted=len(items),
                       n_units_fallback=len(short), n_rows_pool_fallback=0)


# The two router kernels are PRIVATE: the owner approved route_per_unit_loro as the per-unit entry
# point, not these. They are proposed as public entry points (owner decision pending); until then
# route_per_unit_loro (when built), the tests and the legacy-harness gate call them.
def _route_per_unit_grid(rows, answers, table_kind, tree_columns, identity_tolerance, fit_weights=None,
                         only_group=None):
    """The per-unit router on the decision surface: one block-penalised ridge per scored unit on its
    own fit rows, solved at EVERY point of the per-unit grid (shared-Gram solve, with the reference
    check on the first NVERIFY fitted units), plus trees-off (R16, asserted equal to the normal within
    identity_tolerance).

    rows          PerUnitRows (link space; standardised context or none)
    answers       the tree-answer store: unit_view(row_keys, table_kind) -> values, tree_index, group;
                  n_trees and own_columns(group), against which the mask is checked (physical keys)
    table_kind    the table the arm reads ('plain', 'corrector' or 'placebo_corrector')
    tree_columns  RouterTreeColumns: each group's allowed tree columns and its own block
    fit_weights   None for an unweighted arm; for a GLS arm (R24, R25) one weight per fit row of
                  ``rows`` (fit.weights.weights_for_rows), used by the weighted solve of route.solve
                  (solve_grid_weighted: NEW formula, owner review). All weights 1 gives the unweighted
                  bytes. Trees-off is unweighted either way.
    only_group    None: every unit; a group name: only that group's units (plan R20's per-group batching:
                  the pipeline routes one group while only that group's tables are on disk); the plan and
                  the reference check stay the whole pass's, the other units' rows are NaN
    Returns RouteOutput with one column per grid point. Short-history units are NaN and counted; a
    pass with no unit that can be fitted is refused. The caller must not score NaN rows (the region
    fallback router of route.region fills them)."""
    has_context = rows.fit_context is not None if isinstance(rows, PerUnitRows) else False
    return _route(rows, answers, table_kind, tree_columns, per_unit_grid(has_context),
                  identity_tolerance, sweep=True, fit_weights=fit_weights, only_group=only_group)


def _route_per_unit_at(rows, answers, table_kind, tree_columns, point, identity_tolerance, fit_weights=None,
                       only_group=None):
    """The per-unit router at ONE grid point (the test pass at the adopted penalty): solve_local per
    unit (with the weights of a GLS arm: solve_point_weighted), plus trees-off. Arguments as
    _route_per_unit_grid; ``point`` must be a grid point."""
    return _route(rows, answers, table_kind, tree_columns, (point,), identity_tolerance, sweep=False,
                  fit_weights=fit_weights, only_group=only_group)


def _trees_off_per_unit(rows, identity_tolerance):
    """R16 trees-off alone for a PerUnitRows pass (no tree answers read): each fitted unit's intercept +
    normal on its fit rows, predicted on its score rows and asserted equal to the normal within
    identity_tolerance. The same arithmetic, rows and unit plan as the trees-off column of
    _route_per_unit_grid / _route_per_unit_at (a forecast lead needs the identity link's trees-off,
    the decline target, when its pinned arm is on another link). Short-history units are NaN and
    counted. Returns (trees-off (score rows,), units fitted, units short)."""
    chk = _check_rows(rows)
    tol = _check_tolerance(identity_tolerance)
    plan, short = per_unit_plan(rows, chk)
    if not plan:
        raise RouteRefusal("R12", "no scored unit has %d fit rows (%d unit(s), all short): trees-off would "
                           "route nothing; pipeline/router.py takes such a pass's trees-off from the region "
                           "fallback routers (route/region.py) without calling this kernel"
                           % (K.PER_UNIT_MIN_VALID_ROWS, len(short)))
    fy, fn, sn = chk["fy"], chk["fn"], chk["sn"]
    out0 = np.full(chk["ns"], np.nan)
    for unit, group, hidx, tsel in plan:
        out0[tsel] = _trees_off_checked(fn[hidx], fy[hidx], sn[tsel], tol, "unit %s" % unit)
    return out0, len(plan), len(short)


# ---------------------------------------------------------------------------------------------------
# Approved per-unit signatures that need parts not built yet
def unit_season_normal(history, kind, link, c, ub, needed_season_keys, donor_link_mean):
    """R15 from FitContext.unit_history. Needs the R22 link transforms (layer/links, Sat 3 Oct) and
    FitContext (fit/context.py). The arithmetic is season_normal, on link-space values."""
    raise NotImplementedError("unit_season_normal needs FitContext.unit_history (fit/context.py) and "
                              "the R22 link transforms (layer, Sat 3 Oct); use season_normal on "
                              "link-space values meanwhile")


def donor_link_mean(donor_rows, link, c, ub):
    """The donor-row mean of link(y) at a cut. Needs the R22 link transforms (layer, Sat 3 Oct)."""
    raise NotImplementedError("donor_link_mean needs the R22 link transforms (layer, Sat 3 Oct)")


def route_per_unit_loro(ctx, scored_units, bank_units_by_group, link, c, ub, normals, design, answers,
                        tree_columns_by_group, score_row_positions, weights):
    """The FitContext-level per-unit router (LORO). NOT BUILT: the approved signature passes the
    score rows as grid positions only, and FitContext has no public reader of a position's unit and
    step, so pipeline/router.py feeds the private kernels _route_per_unit_grid / _route_per_unit_at
    itself and carries this wrapper's obligations (a departure the run records):
      - build the normal columns from ``normals`` (NormalTable per unit) and refuse a table whose
        cut, link or c differs from the pass (the kernels take plain arrays and cannot see them;
        their R16 guard ties the FIT-row normal to the fit rows' labels, not the score-row normal);
      - take the masks only from own_block_tree_columns over derive_overlap_blocks (RouterTreeColumns
        refuses split blocks; the kernels check the mask against the store's own trees);
      - fill the short-history units' NaN rows with the region fallback router (route/region.py)
        before any score, and refuse to score a NaN router row;
      - GLS arms: the kernels' fit_weights (route.solve's weighted solve, a new formula for the
        owner's review)."""
    raise NotImplementedError("route_per_unit_loro: the approved signature passes score rows as grid "
                              "positions only and FitContext has no public reader of their unit and "
                              "step; the pipeline (pipeline/router.py) feeds the kernels "
                              "_route_per_unit_grid / _route_per_unit_at directly")


# ---------------------------------------------------------------------------------------------------
# The region kind's names from the approved signature list: their bodies are built in route/region.py
# (region_cap_units, search_fallback_level; route_region / route_region_loro wait there for FitContext),
# and the pipeline calls that module. These stubs still raise, naming the milestone, because
# tests/test_route_kinds.py pins them; aliasing them to route.region is an owner item. The neighbour kind
# (milestone M8): built in route/neighbour.py; trees_off_neighbour delegates to it, the other approved names
# raise naming the gap (module docstring).
_REGION = ("this approved region-kind name is not wired in route.kinds: its body is built in route/region.py "
           "(milestone Tue 6 Oct: region router + normal column); call treeroute.route.region, as "
           "pipeline/router.py does")
_NEIGHBOUR = ("the neighbour router (milestone M8) is built in route/neighbour.py; this approved name is not "
              "wired here: ")


def region_cap_units(sorted_units, fit_rows_per_unit, budget):
    """R14 region fit cap (whole units, evenly spaced). Built as route.region.region_cap_units (milestone
    Tue 6 Oct); this approved name is not wired here (owner item)."""
    raise NotImplementedError(_REGION)


def route_region(ctx, group, unit_ids, link, c, ub, normals, design, answers, score_row_positions,
                 weights):
    """Region router. Built in route/region.py (milestone Tue 6 Oct; its FitContext-level wrapper waits
    there); this approved name is not wired here (owner item)."""
    raise NotImplementedError(_REGION)


def route_region_loro(ctx, group, fit_units, scored_units, link, c, ub, normals, design, answers,
                      tree_columns, score_row_positions, weights):
    """Region router under leave one region out. Built in route/region.py (milestone Tue 6 Oct; its
    FitContext-level wrapper waits there); this approved name is not wired here (owner item)."""
    raise NotImplementedError(_REGION)


def search_fallback_level(surface_mae_by_level, n_fallback_units_scored, centre):
    """The fallback region router's level. Built as route.region.search_fallback_level (milestone Tue 6
    Oct); this approved name is not wired here (owner item)."""
    raise NotImplementedError(_REGION)


def trees_off_neighbour(fit, fit_y_link, score, level):
    """Neighbour trees-off (R16): intercept + standardised context fitted on the row's pool, intercept
    unpenalised, context at the point ``level``, unweighted. Built in route/neighbour.py (milestone M8);
    this approved name delegates to it."""
    from treeroute.route import neighbour as _N      # imported here: route.neighbour imports this module
    return _N.trees_off_neighbour(fit, fit_y_link, score, level)


def neighbour_pool(row_unit, row_group, row_lat, row_lon, row_features, candidates, candidate_lat,
                   candidate_lon, candidate_features, candidate_group, test_groups):
    """Neighbour pool with held-back test groups: the pre-LORO name, superseded by neighbour_pool_loro
    (SIGNATURES_LORO_ADDENDUM.md; no group is held back under leave one region out)."""
    raise NotImplementedError(_NEIGHBOUR + "neighbour_pool is the pre-LORO name, superseded by "
                              "neighbour_pool_loro; call treeroute.route.neighbour.neighbour_pool_loro")


def neighbour_pool_loro(row_unit, row_group, row_lat, row_lon, row_features, candidates, candidate_lat,
                        candidate_lon, candidate_features, candidate_group, blocks):
    """Neighbour pool under leave one region out. Built as route.neighbour.neighbour_pool_loro, which
    takes the row's issue day as the keyword row_issue_day: ruling U4 filters every pool by it, and this
    approved signature carries no date (owner item O19)."""
    raise NotImplementedError(_NEIGHBOUR + "ruling U4 filters each pool by the row's issue day, which this "
                              "approved signature does not carry; call treeroute.route.neighbour."
                              "neighbour_pool_loro(..., row_issue_day=<the row's issue day>)")


def route_neighbour(ctx, link, c, ub, design, answers, score_row_positions, donor_median, weights):
    """Neighbour router with held-back test groups: the pre-LORO name, superseded by route_neighbour_loro."""
    raise NotImplementedError(_NEIGHBOUR + "route_neighbour is the pre-LORO name, superseded by "
                              "route_neighbour_loro; the table pipeline feeds the private kernels "
                              "treeroute.route.neighbour._route_neighbour_grid / _route_neighbour_at")


def route_neighbour_loro(ctx, link, c, ub, design, answers, tree_group, blocks, score_row_positions,
                         donor_median, weights):
    """Neighbour router under leave one region out. NOT WIRED: the approved signature passes the score
    rows as positions only, and FitContext has no public reader of their identity, place and issue day,
    so the table pipeline feeds the private kernels route.neighbour._route_neighbour_grid /
    _route_neighbour_at (as pipeline/router.py feeds the per-unit kernels)."""
    raise NotImplementedError(_NEIGHBOUR + "the approved signature passes score rows as positions only and "
                              "FitContext has no public reader of their identity, place and issue day; the "
                              "table pipeline feeds treeroute.route.neighbour._route_neighbour_grid / "
                              "_route_neighbour_at")


__all__ = [
    "INTERCEPT", "NORMAL", "CONTEXT", "TREES", "CONTEXT_SD_OFFSET", "RouteRefusal", "RouteGuardError",
    "RouterKind", "GridPoint", "RouterDesign", "DesignMatrix", "NormalTable", "RouteOutput",
    "PerUnitRows", "RouterTreeColumns", "per_unit_grid", "per_unit_centre", "point_penalties",
    "per_unit_router_design", "trees_off_router_design", "build_column_block",
    "router_standardisation", "standardise_context", "season_normal", "normal_values",
    "r36_tolerance", "trees_off_with_normal", "reference_predictions", "fallback_units",
    "fallback_share_flagged", "valid_fit_rows", "router_tree_columns", "assert_no_own_group_column",
    "own_block_tree_columns", "per_unit_plan", "unit_season_normal", "donor_link_mean", "route_per_unit_loro", "region_cap_units",
    "route_region", "route_region_loro", "search_fallback_level", "trees_off_neighbour",
    "neighbour_pool", "neighbour_pool_loro", "route_neighbour", "route_neighbour_loro",
]
