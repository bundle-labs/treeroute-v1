"""treeroute.route.neighbour: the NEIGHBOUR router kind (plan 2.2 R12-R14, R16; owner ruling U, sections
U3 and U4; owner rulings D and E (leave one region out, L2 rule 4); SIGNATURES_LORO_ADDENDUM.md (the pool
drop default); the build specs SPEC_NEIGHBOUR.md and SPEC_TABLE_MODE.md section 4; file names and dates in
the provenance comment below).

SCIENCE bodies for the approved neighbour signatures of _proposed/route_kinds.py (trees_off_neighbour) and
_proposed/loro_additions.py (neighbour_pool_loro, route_neighbour_loro), ported from the legacy neighbour
router (adaptation.py:1610-1666 and the legacy architecture module; provenance below) with the STRICT pool of
ruling U4.
Where the rulings differ from a docstring there, the rulings win. route/kinds.py and route/solve.py are
not edited here: this module imports their shapes, guards and solvers. route/kinds.py's approved
trees_off_neighbour delegates to this module; its other approved neighbour names cannot carry what the
rulings need (an issue day per row; the score rows' identity) and raise, naming this module.

BUILT
  - The strict pool (R14, U4; neighbour_pool_loro, neighbour_pools). Candidates are the pass's own
    router rows: train rows with a valid label, dated at or before the pass's bank cut (the context
    hands out nothing else; the vault never hands out a test row). Per scored row, a candidate is
    ELIGIBLE when its target day is strictly before the row's ISSUE day (the target day minus the lead;
    a nowcast's own day) and it is not the row itself. Under C11.neighbour_pool_min_rows eligible rows
    the row has no pool (the caller's fallback, U3). Else: the haversine central angle to every
    candidate (the legacy formula without the Earth radius: the same ranking), a stable sort, the first
    C11.neighbour_pool_distance; then the Euclidean distance in the standardised tree features Z, a
    stable sort of those, the first C11.neighbour_pool_feature. Ties at the map step go to the earlier
    row position (candidates come in row-position order, which is asserted); ties at the feature step
    keep the map order. Every pool is asserted (RouteGuardError, kept under python -O): no row after
    the cut, none on or after the issue day, never the row itself. Pools handed to a kernel are
    asserted again there, with their drop sets (_pools_for).
  - The drop set (R14, LORO; SIGNATURES_LORO_ADDENDUM.md): the row's own overlap block and the block of
    every group present in its pool, sorted (whole blocks). Every pool row of group h was trained on by
    h's trees, so h's trees are dropped for that row.
  - Z (SPEC_TABLE_MODE.md 4.0): pool_feature_z fills a missing tree feature with 0 (as the trees see
    it, R30), and standardises with the mean and population sd (+ CONTEXT_SD_OFFSET) over the pass's
    candidates only (rows at or before the cut). A column constant over the candidates is set to 0 on
    both sides: it adds the same term to every candidate's distance, so leaving it out keeps the true
    ranking (with the offset alone a score value off the constant would weigh about 1e18 and turn the
    feature step into map order; FIX_REPORT.md, correctness item 1).
  - Trees-off (R16; trees_off_neighbour): intercept + standardised context fitted on the row's pool,
    intercept unpenalised, context penalised at the R14 base point (owner item O9), unweighted:
    route.solve.solve_point with one unpenalised column. Without context it is the jittered pool mean.
  - The local fit (R14): [intercept, standardised context, kept tree answers], intercept alone
    unpenalised (n_unpenalised=1 on every solver), a_tree = C12.neighbour_trees_centre x level,
    a_ctx = a_tree x ratio, each penalised block trace-normalised on its own raw block. Pools hold at
    most 50 rows, so with more columns than rows the solvers take the exact k-space dual (route/solve.py
    solve_local_dual; the derivation is in SPEC_NEIGHBOUR.md 3.3); the decision surface solves every
    grid point with the shared-Gram dual (solve_grid, reference check on the first NVERIFY fitted rows);
    a test or guard pass solves one point (solve_point). GLS arms (R24, R25) use the weighted twins
    with the pool rows' weights; trees-off stays unweighted.
  - Rows whose drop set holds every tree of the bank (owner item O8): every tree arm takes that row's
    trees-off on its pool, counted as n_rows_no_tree.
  - Rows with no pool (U3, owner item O7): every arm and the trees-off take the row's fallback_link,
    the link of the donor-row median in y, which the caller computes from the pass's bank donor rows.
  - The kernels on arrays (NeighbourRows; private until the owner approves public entry points, as the
    per-unit and region kernels): _route_neighbour_grid, _route_neighbour_at, _trees_off_neighbour_pass.
    Pools are computed once per pass (neighbour_pools) and may be handed to every arm: they depend on
    the candidates, Z and the issue days only, never on the link, the table kind or the weights (a
    fingerprint refuses pools built on other rows). Rows are solved ROUTER_WORKERS at once with BLAS at
    ROUTER_WORKER_BLAS_THREADS (route/kinds.py _solve_units), results written back in row order, so the
    bytes do not depend on the worker count. No random draw anywhere.
  - The dense answer matrix of one table kind (dense_answers): every candidate and scored row's tree
    answers in bank order, each row read from its own group's table; the group's own trees stay NaN and
    are never read (they are always in the row's drop set; a NaN in a kept column is refused).

NOT BUILT (raise in route/kinds.py): the FitContext-level wrappers route_neighbour and
route_neighbour_loro (the approved signatures pass the score rows as positions only; the table pipeline
feeds the kernels itself), the approved neighbour_pool_loro without an issue day (U4 needs one; this
module's neighbour_pool_loro takes it as a keyword) and the pre-LORO neighbour_pool (superseded).
"""
# Provenance for the module: adaptation.py:1434 (K = 50, MINOK = 12, ALPHA 0.5, A_CTX 0.25), :1620-1640 (the
# eligible mask, the 3K nearest by haversine, the K most similar in Z), :1643 (the future-row assert),
# :1651-1666 (the local design [1, MMM, context, trees] and solve_local with W[sel]), :1601-1603 and
# :1662-1665 (a_tree = ALPHA x mlt, a_ctx = ALPHA x mlt x rho); coral_architecture.py:143-147 (haversine),
# :176-254 (solve_local and the exact dual, USE_DUAL); CORAL_EXPERIMENTS.md Part 458 (the legacy pool took
# test rows; not ported). Owner ruling U (OWNER_RULINGS_2026-10-06.md:84-95): U3 donor-row median fallback,
# U4 strict pool. SIGNATURES_LORO_ADDENDUM.md:34 (pool groups' trees dropped by default). Build specs:
# D:/treeroute/coral_build/SPEC_NEIGHBOUR.md and SPEC_TABLE_MODE.md section 4 (2026-10-19).

import hashlib
import math
from dataclasses import dataclass
from numbers import Integral
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from treeroute import engine_constants as K
from treeroute import split as SP
from treeroute.route import kinds as RK
from treeroute.route import solve as S
from treeroute.route.kinds import (CONTEXT, INTERCEPT, NORMAL, TREES, DesignMatrix, GridPoint,
                                   RouteGuardError, RouteOutput, RouteRefusal, RouterDesign, RouterKind)

# origin: derive/router_rules.py derive_r14_router_design, neighbour branch (unpenalised = (intercept,));
# signed R14 lists the intercept alone (APP_PLAN.md R14); SPEC_NEIGHBOUR.md 3.3. The legacy design had two
# free columns (intercept and MMM, adaptation.py:1651); MMM is not ported (owner item N8).
NEIGHBOUR_UNPENALISED_COLUMNS = 1
# origin: coral_architecture.py:144 (p = pi / 180 in haversine)
_DEGREE = np.pi / 180.0


# ---------------------------------------------------------------------------------------------------
# small helpers
def _name(value, what):
    if not isinstance(value, str) or not value:
        raise RouteRefusal("R14", "%s must be a non-empty string, got %r" % (what, value))
    return value


def _int_scalar(value, what, rule="U4"):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (Integral, np.integer)):
        raise RouteRefusal(rule, "%s must be an integer day, got %s %r" % (what, type(value).__name__, value))
    return int(value)


def _int_vector(values, what, n=None, rule="U4"):
    arr = np.asarray(values)
    if arr.ndim != 1 or (arr.size and arr.dtype.kind not in "iu") or arr.dtype == np.bool_:
        raise RouteRefusal(rule, "%s must be a 1-D integer array, got shape %s dtype %s"
                           % (what, arr.shape, arr.dtype))
    if n is not None and arr.shape[0] != n:
        raise RouteRefusal(rule, "%s has %d rows, expected %d" % (what, arr.shape[0], n))
    return arr.astype(np.int64, copy=False)


def _float_vector(values, what, n=None, rule="R14"):
    arr = np.asarray(values)
    if arr.ndim != 1 or (arr.size and arr.dtype.kind not in "fiu") or arr.dtype == np.bool_:
        raise RouteRefusal(rule, "%s must be a 1-D numeric array, got shape %s dtype %s"
                           % (what, arr.shape, arr.dtype))
    if n is not None and arr.shape[0] != n:
        raise RouteRefusal(rule, "%s has %d rows, expected %d" % (what, arr.shape[0], n))
    return np.asarray(arr, dtype=np.float64)


def _finite(arr, what, rule):
    if arr.size and not np.all(np.isfinite(arr)):
        bad = int(arr.size - np.count_nonzero(np.isfinite(arr)))
        raise RouteRefusal(rule, "%s holds %d missing or infinite value(s)" % (what, bad))
    return arr


def _matrix(values, what, n, rule="R14"):
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[0] != n or arr.shape[1] == 0:
        raise RouteRefusal(rule, "%s must be (%d, >=1), got %s" % (what, n, arr.shape))
    return arr


def _coordinates(lat, lon, what, n=None):
    la = _float_vector(lat, "%s latitude" % what, n)
    lo = _float_vector(lon, "%s longitude" % what, la.shape[0])
    _finite(la, "%s latitude" % what, "R14")
    _finite(lo, "%s longitude" % what, "R14")
    if la.size and (float(la.min()) < -90.0 or float(la.max()) > 90.0):
        raise RouteRefusal("R14", "%s latitudes must lie in [-90, 90]" % what)
    return la, lo


def _names(values, what, n):
    arr = np.asarray(values, dtype=object)
    if arr.ndim != 1 or arr.shape[0] != n:
        raise RouteRefusal("R14", "%s must be 1-D with %d entries, got shape %s" % (what, n, arr.shape))
    for v in set(arr.tolist()):
        _name(v, "an entry of %s" % what)
    return arr


def _block_map(blocks):
    """{group: its whole overlap block} from OverlapBlocks, checked once (split.block_of_group's rules)."""
    if not isinstance(blocks, SP.OverlapBlocks):
        raise RouteRefusal("G-DISJOINT", "blocks must be OverlapBlocks (derive_overlap_blocks(...).value), "
                                         "got %s" % type(blocks).__name__)
    first = next(iter(blocks.block_of_group), None)
    if first is None:
        raise RouteRefusal("G-DISJOINT", "no overlap blocks given")
    SP.block_of_group(blocks, first)          # validates the whole partition (split._check_blocks)
    return {g: tuple(blocks.members[i]) for g, i in blocks.block_of_group.items()}


def _drop_groups(row_group, pool_groups, block_of):
    """The sorted union of the row's own block and the block of every pool group (whole blocks)."""
    out = set()
    for g in {row_group} | set(pool_groups):
        if g not in block_of:
            raise RouteRefusal("G-DISJOINT", "group %r is in no overlap block" % (g,),
                               fix="derive the blocks over every group's units")
        out.update(block_of[g])
    return tuple(sorted(out))


# ---------------------------------------------------------------------------------------------------
# Distance, grid and penalties
# Provenance: coral_architecture.py:143-147 (haversine; the Earth radius left out: the same ranking).
def haversine_angle(lat1, lon1, lat2, lon2):
    """The great-circle central angle (radians) between (lat1, lon1) and (lat2, lon2), degrees in: the
    legacy haversine line for line, without the Earth radius."""
    p = _DEGREE
    a = (np.sin((lat2 - lat1) * p / 2) ** 2
         + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2)
    return 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def neighbour_grid(has_context):
    """The neighbour grid (R14, R26): C12.penalty_levels x C12.penalty_ratios, level-major (35 points), or
    the 7 levels with ratio None without context. The same points as derive_r14_router_design's."""
    return RK.per_unit_grid(has_context)


def neighbour_base_point(has_context):
    """The R14 base point: level 1 and ratio = context centre / trees centre (C12), the legacy shipped
    pair; refuses constants whose base point is off the grid."""
    ratio = None
    if has_context:
        ratio = float(K.NEIGHBOUR_CONTEXT_CENTRE) / float(K.NEIGHBOUR_TREES_CENTRE)
    point = GridPoint(1.0, ratio)
    if point not in neighbour_grid(has_context):
        raise RouteRefusal("C12", "the neighbour base point %s is not a point of the grid" % (point,),
                           fix="the engine constants C12 must put the centres on the grid")
    return point


def _as_point(point):
    """Any grid point (route/kinds.py's or derive/shapes.py's: level and ratio) as route/kinds.py's
    GridPoint (layer/decide.py as_point's reading); None when it has no level."""
    level = getattr(point, "level", None)
    if isinstance(level, (bool, np.bool_)) or not isinstance(level, (int, float, np.integer, np.floating)):
        return None
    ratio = getattr(point, "ratio", None)
    if ratio is not None and (isinstance(ratio, (bool, np.bool_))
                              or not isinstance(ratio, (int, float, np.integer, np.floating))):
        return None
    return GridPoint(float(level), None if ratio is None else float(ratio))


def neighbour_point_penalties(point, has_context):
    """(a_tree, a_ctx) of one neighbour grid point: a_tree = C12.neighbour_trees_centre x level,
    a_ctx = a_tree x ratio (0.0 without context). Refuses a point that is not on the grid."""
    point = _as_point(point)
    if point is None or point not in neighbour_grid(has_context):
        raise RouteRefusal("R26", "%r is not a point of the neighbour grid (%s context)"
                           % (point, "with" if has_context else "without"),
                           fix="penalties come from the engine grid only; no point is hand-set")
    a_tree = K.NEIGHBOUR_TREES_CENTRE * point.level
    if point.ratio is None:
        return a_tree, 0.0
    return a_tree, a_tree * point.ratio


def _check_design(design, has_context):
    """The R14 neighbour design (derived['R14'].value, a derive/shapes.py RouterDesign, or route/kinds.py's
    field-identical shape), checked field by field and returned as route/kinds.py's RouterDesign (the
    shape build_column_block takes)."""
    kind = getattr(design, "kind", None)
    if getattr(kind, "value", kind) != RouterKind.NEIGHBOUR.value or not hasattr(design, "columns"):
        raise RouteRefusal("R14", "the neighbour kernels need the R14 neighbour design, got %r" % (kind,))
    want = (INTERCEPT, CONTEXT, TREES) if has_context else (INTERCEPT, TREES)
    if tuple(design.columns) != want or tuple(design.unpenalised) != (INTERCEPT,):
        raise RouteRefusal("R14", "neighbour design columns %s / unpenalised %s; expected %s / (intercept,)"
                           % (design.columns, design.unpenalised, want),
                           fix="pass derived['R14'].value for a package %s router context"
                               % ("with" if has_context else "without"))
    grid = tuple(_as_point(p) for p in design.grid)
    if grid != neighbour_grid(has_context):
        raise RouteRefusal("R26", "the design's grid is not the engine's neighbour grid",
                           fix="penalties come from the engine grid only (derived['R14'])")
    return RouterDesign(kind=RouterKind.NEIGHBOUR, columns=want, unpenalised=(INTERCEPT,),
                        centre=tuple(float(v) for v in design.centre), grid=grid,
                        fit_row_cap=design.fit_row_cap)


# ---------------------------------------------------------------------------------------------------
# Z: the standardised tree features of the feature-space step
# Provenance: adaptation.py:1547-1548 (mean, sd + 1e-9 over the training rows); SPEC_TABLE_MODE.md 4.0
# (constants over the pass's candidates, at or before its cut; missing values 0-filled as the trees see
# them, R30; the legacy donor-median fill read later rows and is not ported). Constant columns zeroed:
# FIX_REPORT.md (correctness review, item 1); the legacy's constants came from every training row, so
# a column constant on a pass's candidates did not arise there.
def pool_feature_z(candidate_features, score_features, candidate_times, cut):
    """(candidate Z, score Z, mean, sd): the tree features with a missing value set to 0, standardised
    with the mean and population sd (+ CONTEXT_SD_OFFSET) of each column over the candidates only.
    A column whose candidates all hold one value is 0 in both Z matrices (exact: it adds the same
    term to every candidate's distance); a Z column that is 0 on every candidate marks it.

    Refuses a candidate after the cut (G-FITCUT), no candidate, an infinite value, and score rows whose
    columns differ from the candidates'."""
    t = _int_vector(candidate_times, "candidate times", rule="G-FITCUT")
    c = _int_scalar(cut, "the cut", "G-FITCUT")
    if t.size == 0:
        raise RouteRefusal("R14", "no candidates: the feature constants cannot be fitted")
    if int(t.max()) > c:
        raise RouteRefusal("G-FITCUT", "%d candidate(s) lie after the cut %d; Z constants see only rows at "
                           "or before it" % (int(np.count_nonzero(t > c)), c))
    F = np.array(candidate_features, dtype=np.float64, copy=True)
    G = np.array(score_features, dtype=np.float64, copy=True)
    if F.ndim != 2 or F.shape[0] != t.size or F.shape[1] == 0:
        raise RouteRefusal("R14", "candidate features must be (%d, >=1), got %s" % (t.size, F.shape))
    if G.ndim != 2 or G.shape[1] != F.shape[1]:
        raise RouteRefusal("R14", "score features %s do not have the candidates' %d columns"
                           % (G.shape, F.shape[1]))
    for arr, what in ((F, "candidate"), (G, "score")):
        if np.isinf(arr).any():
            raise RouteRefusal("R30", "%d infinite %s feature value(s); only a missing value is filled"
                               % (int(np.isinf(arr).sum()), what))
        arr[np.isnan(arr)] = 0.0
    F = np.ascontiguousarray(F)
    mean, sd = F.mean(0), F.std(0) + RK.CONTEXT_SD_OFFSET
    zc, zs = (F - mean) / sd, (G - mean) / sd
    const = F.max(0) == F.min(0)              # exact: every candidate holds the same value
    if const.any():
        zc[:, const] = 0.0
        zs[:, const] = 0.0
    return zc, zs, mean, sd


def constant_z_columns(candidate_z):
    """How many columns of a candidate Z (pool_feature_z) are constant over the candidates (all 0)."""
    cz = np.asarray(candidate_z, dtype=np.float64)
    return int(np.count_nonzero(np.all(cz == 0.0, axis=0))) if cz.ndim == 2 and cz.shape[0] else 0


# ---------------------------------------------------------------------------------------------------
# The strict pool (R14, U4, C11)
def _check_candidate_rows(candidates):
    """cut, times, unit ids and row positions of a RouterRows or a ContextKeptRows (the same fields)."""
    cut = getattr(candidates, "cut", None)
    if isinstance(cut, (bool, np.bool_)) or not isinstance(cut, (Integral, np.integer)):
        raise RouteRefusal("G-FITCUT", "candidates must carry an integer cut (a RouterRows from the pass's "
                                       "own FitContext, or the ContextKeptRows G1 leaves)")
    times = _int_vector(getattr(candidates, "times", None), "candidate times", rule="G-FITCUT")
    n = times.shape[0]
    units = getattr(candidates, "unit_ids", None)
    units = np.asarray(units, dtype=object) if units is not None else None
    if units is None or units.shape != (n,):
        raise RouteRefusal("R14", "candidates must carry one unit id per row")
    pos = _int_vector(getattr(candidates, "row_positions", None), "candidate row positions", n, rule="R14")
    if n and int(times.max()) > int(cut):
        raise RouteRefusal("G-FITCUT", "%d candidate(s) lie after the cut %d"
                           % (int(np.count_nonzero(times > int(cut))), int(cut)))
    if n > 1 and not np.all(np.diff(pos) > 0):
        raise RouteRefusal("R14", "candidate row positions must be strictly ascending (row-position order "
                                  "makes the tie rule; FitContext.router_rows hands them out so)")
    return int(cut), times, units, pos


def _assert_pool(sel, cand_day, cand_unit, cut, issue, unit, what):
    """G-FITCUT on one pool, raised even under python -O."""
    if sel.size == 0:
        return
    d = cand_day[sel]
    if int(d.max()) > cut:
        raise RouteGuardError("G-FITCUT: %s: a pool row is dated %d, after the pass's cut %d"
                              % (what, int(d.max()), cut))
    if int(d.max()) >= issue:
        raise RouteGuardError("G-FITCUT: %s: a pool row is dated %d, on or after the issue day %d (U4)"
                              % (what, int(d.max()), issue))
    if np.any(cand_unit[sel] == unit):
        raise RouteGuardError("G-FITCUT: %s: the row itself entered its own pool" % (what,))


def _pool_of_row(issue, unit, lat, lon, z, cand_day, cand_unit, cand_lat, cand_cos, cand_lon, cand_z):
    """Candidate indices of one row's pool in pool order, or None under the minimum (C11).

    The map angle is computed on the FULL candidate vector (elementwise, so it does not depend on which
    rows are eligible); the legacy expression with cos(lat2 p) taken once per pass (the same floats)."""
    ok = np.flatnonzero((cand_day < issue) & (cand_unit != unit))
    if ok.size < int(K.NEIGHBOUR_POOL_MIN_ROWS):
        return None
    p = _DEGREE
    a = (np.sin((cand_lat - lat) * p / 2) ** 2
         + np.cos(lat * p) * cand_cos * np.sin((cand_lon - lon) * p / 2) ** 2)
    ang = 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
    gg = ok[np.argsort(ang[ok], kind="stable")][:min(ok.size, int(K.NEIGHBOUR_POOL_DISTANCE))]
    dz = np.sqrt(((cand_z[gg] - z) ** 2).sum(1))
    return gg[np.argsort(dz, kind="stable")][:int(K.NEIGHBOUR_POOL_FEATURE)]


# Provenance: loro_additions.py neighbour_pool_loro (approved contract); adaptation.py:1620-1643; owner
# ruling U4 (strict pool by the issue day); SPEC_TABLE_MODE.md 4.1 (the keyword row_issue_day, owner item
# O19).
def neighbour_pool_loro(row_unit, row_group, row_lat, row_lon, row_features, candidates, candidate_lat,
                        candidate_lon, candidate_features, candidate_group, blocks, *, row_issue_day):
    """The strict pool of one neighbour-kind row under leave one region out, and the groups whose trees
    its router must drop.

    Rule: R14 (neighbour), C11, U4, G-FITCUT.
    row_unit       the row's engine unit (its row id); never in its own pool
    row_group      its group; row_lat, row_lon its place (degrees); row_features its Z row
    candidates     the pass's RouterRows (FitContext.router_rows), or the ContextKeptRows G1 leaves:
                   cut, times (target days), unit_ids, row_positions (row-position order, asserted)
    candidate_*    their places, Z rows and groups, in the candidates' order
    blocks         OverlapBlocks (derive_overlap_blocks)
    row_issue_day  the row's issue day: its target day minus the lead (a nowcast's own day)
    Eligible: candidates dated strictly before row_issue_day, other than the row. Under
    C11.neighbour_pool_min_rows eligible: (None, the row's own block). Else the C11.neighbour_pool_distance
    nearest by haversine angle (stable sort, ties to the earlier row position), then the
    C11.neighbour_pool_feature nearest of those in Z (stable sort, ties keep the map order).
    Returns (pool row positions in pool order, as candidates.row_positions values; the drop groups:
    the row's block and every pool group's block, sorted).
    Refuses: malformed inputs, a candidate after the cut. Asserts (RouteGuardError) a pool row after the
    cut, on or after the issue day, or the row itself."""
    unit = _name(row_unit, "row_unit")
    group = _name(row_group, "row_group")
    issue = _int_scalar(row_issue_day, "row_issue_day")
    cut, times, units, pos = _check_candidate_rows(candidates)
    n = times.shape[0]
    clat, clon = _coordinates(candidate_lat, candidate_lon, "candidate", n)
    rlat, rlon = _coordinates([row_lat], [row_lon], "row")
    cz = _finite(_matrix(candidate_features, "candidate features", n), "candidate features", "R14") \
        if n else np.zeros((0, np.asarray(row_features).size))
    rz = _finite(_float_vector(row_features, "row features"), "row features", "R14")
    if n and rz.shape[0] != cz.shape[1]:
        raise RouteRefusal("R14", "the row has %d features, the candidates %d" % (rz.shape[0], cz.shape[1]))
    cgroup = _names(candidate_group, "candidate groups", n)
    block_of = _block_map(blocks)
    if group not in block_of:
        raise RouteRefusal("G-DISJOINT", "row group %r is in no overlap block" % group)
    sel = _pool_of_row(issue, unit, float(rlat[0]), float(rlon[0]), rz, times, units, clat,
                       np.cos(clat * _DEGREE), clon, cz)
    if sel is None:
        return None, tuple(block_of[group])
    _assert_pool(sel, times, units, cut, issue, unit, "row %s" % unit)
    return pos[sel].copy(), _drop_groups(group, cgroup[sel].tolist(), block_of)


# ---------------------------------------------------------------------------------------------------
# Trees-off (R16)
# Provenance: _proposed/route_kinds.py trees_off_neighbour (approved contract); plan 2.2 R16 ("Neighbour:
# trees-off = intercept + context fit"); SPEC_TABLE_MODE.md 4.2 (solve_point with one unpenalised column,
# the R14 base point: owner item O9).
def trees_off_neighbour(fit, fit_y_link, score, level):
    """R16 trees-off for the neighbour kind: intercept + standardised context fitted on the row's pool,
    predicted on the score rows (link space).

    fit, score   DesignMatrix of [intercept, context] (no tree block, no normal), the same columns
    fit_y_link   link(y) on the pool rows
    level        the context penalty point (a neighbour grid point; the kernels pass the R14 base point)
    The intercept is unpenalised; the context block is penalised at a_ctx = C12.neighbour_trees_centre x
    level x ratio, trace-normalised on its own columns; unweighted. Without context the design is the
    intercept alone and the result is the pool mean (with the solver's 1e-8 primal jitter).
    Refuses: a design with a tree block or a normal; a first column that is not the intercept; fit and
    score designs with other columns; a point off the grid or not matching the context; a non-finite
    value; fewer than 2 pool rows."""
    for d, what in ((fit, "fit"), (score, "score")):
        if not isinstance(d, DesignMatrix):
            raise RouteRefusal("R16", "%s must be a DesignMatrix, got %s" % (what, type(d).__name__))
        if TREES in d.blocks or NORMAL in d.blocks:
            raise RouteRefusal("R16", "the neighbour trees-off design holds a %s block; it is intercept + "
                                      "context only" % (TREES if TREES in d.blocks else NORMAL))
        if not d.blocks or d.blocks[0] != INTERCEPT or any(b != CONTEXT for b in d.blocks[1:]):
            raise RouteRefusal("R16", "the %s design must be [intercept, context...], got blocks %s"
                               % (what, d.blocks))
    if tuple(fit.blocks) != tuple(score.blocks):
        raise RouteRefusal("R16", "fit and score designs have other columns: %s vs %s"
                           % (fit.blocks, score.blocks))
    Xc = _finite(np.asarray(fit.X, dtype=np.float64), "the trees-off fit design", "R16")
    Xt = _finite(np.asarray(score.X, dtype=np.float64), "the trees-off score design", "R16")
    ncol = len(fit.blocks)
    if Xc.ndim != 2 or Xc.shape[1] != ncol or Xt.ndim != 2 or Xt.shape[1] != ncol:
        raise RouteRefusal("R16", "design matrices do not match their %d blocks" % ncol)
    y = _finite(_float_vector(fit_y_link, "fit link(y)", Xc.shape[0]), "fit link(y)", "R30")
    if Xc.shape[0] < 2:
        raise RouteRefusal("R16", "trees-off needs at least 2 pool rows, got %d" % Xc.shape[0])
    nctx = ncol - 1
    _, a_ctx = neighbour_point_penalties(level, nctx > 0)
    return S.solve_point(Xc, y, Xt, 0, nctx, 0.0, a_ctx, n_unpenalised=NEIGHBOUR_UNPENALISED_COLUMNS)


def _trees_off_design(ctx, n):
    """DesignMatrix [intercept, context] (or the intercept alone) on n rows."""
    if ctx is None:
        return DesignMatrix(X=np.ones((n, 1)), blocks=(INTERCEPT,))
    return DesignMatrix(X=np.column_stack([np.ones(n), ctx]), blocks=(INTERCEPT,) + (CONTEXT,) * ctx.shape[1])


# ---------------------------------------------------------------------------------------------------
# The pass's rows, answers and pools
@dataclass(frozen=True)
class NeighbourRows:
    """One neighbour pass over plain arrays (SPEC_TABLE_MODE.md 4.3).

    cut, lead      the pass's bank cut (a day: the horizon) and its lead in days
    cand_*         the candidates (the pass's router rows after G1), in row-position order:
                   cand_keys (n,) int64 store row keys, strictly ascending; cand_day (n,) target days,
                   at or before the cut; cand_unit (n,) engine units (row ids); cand_group (n,);
                   cand_lat, cand_lon (n,) degrees; cand_z (n, f) Z rows; cand_ctx (n, c) standardised
                   context or None; cand_y_link (n,) link(y) with the pass's c; cand_w (n,) GLS weights
                   (R25) for a weighted arm, or None
    score_*        the rows to predict: score_keys, score_unit, score_issue (issue days, from the lead
                   table), score_group, score_lat, score_lon, score_z, score_ctx; score_rows (m,) the
                   caller's positions, returned as RouteOutput.row_positions
    fallback_link  (m,) the link of the donor-row median in y (U3), per score row"""
    cut: int
    lead: int
    cand_keys: np.ndarray
    cand_day: np.ndarray
    cand_unit: np.ndarray
    cand_group: np.ndarray
    cand_lat: np.ndarray
    cand_lon: np.ndarray
    cand_z: np.ndarray
    cand_ctx: Optional[np.ndarray]
    cand_y_link: np.ndarray
    cand_w: Optional[np.ndarray]
    score_keys: np.ndarray
    score_unit: np.ndarray
    score_issue: np.ndarray
    score_group: np.ndarray
    score_lat: np.ndarray
    score_lon: np.ndarray
    score_z: np.ndarray
    score_ctx: Optional[np.ndarray]
    score_rows: np.ndarray
    fallback_link: np.ndarray


def _check_neighbour_rows(rows):
    if not isinstance(rows, NeighbourRows):
        raise RouteRefusal("R14", "rows must be NeighbourRows, got %s" % type(rows).__name__)
    cut = _int_scalar(rows.cut, "the cut", "G-FITCUT")
    lead = _int_scalar(rows.lead, "the lead", "R10")
    if lead < 0:
        raise RouteRefusal("R10", "the lead must be >= 0 days, got %d" % lead)
    ck = _int_vector(rows.cand_keys, "cand_keys", rule="R14")
    n = ck.shape[0]
    if n > 1 and not np.all(np.diff(ck) > 0):
        raise RouteRefusal("R14", "cand_keys must be strictly ascending (row-position order makes the tie rule)")
    cd = _int_vector(rows.cand_day, "cand_day", n, rule="G-FITCUT")
    if n and int(cd.max()) > cut:
        raise RouteRefusal("G-FITCUT", "%d candidate(s) are dated after the pass's cut %d"
                           % (int(np.count_nonzero(cd > cut)), cut))
    cu = _names(rows.cand_unit, "cand_unit", n)
    cg = _names(rows.cand_group, "cand_group", n)
    clat, clon = _coordinates(rows.cand_lat, rows.cand_lon, "candidate", n)
    cy = _finite(_float_vector(rows.cand_y_link, "cand_y_link", n), "candidate link(y)", "R30")
    sk = _int_vector(rows.score_keys, "score_keys", rule="R14")
    m = sk.shape[0]
    if m == 0:
        raise RouteRefusal("R14", "no score rows: nothing to route")
    si = _int_vector(rows.score_issue, "score_issue", m)
    if int(si.min()) < cut:
        raise RouteRefusal("G-FITCUT", "%d score row(s) are issued before the pass's cut %d; objects fitted "
                           "at the cut saw their labels" % (int(np.count_nonzero(si < cut)), cut))
    su = _names(rows.score_unit, "score_unit", m)
    sg = _names(rows.score_group, "score_group", m)
    slat, slon = _coordinates(rows.score_lat, rows.score_lon, "score", m)
    cz = _finite(_matrix(rows.cand_z, "cand_z", n), "candidate Z", "R14") if n else None
    sz = _finite(_matrix(rows.score_z, "score_z", m), "score Z", "R14")
    if cz is None:
        cz = np.zeros((0, sz.shape[1]))
    if cz.shape[1] != sz.shape[1]:
        raise RouteRefusal("R14", "candidate and score Z have %d and %d columns" % (cz.shape[1], sz.shape[1]))
    if (rows.cand_ctx is None) != (rows.score_ctx is None):
        raise RouteRefusal("R14", "candidates and score rows must carry the same context columns")
    cc = sc = None
    if rows.cand_ctx is not None:
        sc = _finite(_matrix(rows.score_ctx, "score_ctx", m, "R20"), "score context", "R20")
        cc = (_finite(_matrix(rows.cand_ctx, "cand_ctx", n, "R20"), "candidate context", "R20") if n
              else np.zeros((0, sc.shape[1])))
        if cc.shape[1] != sc.shape[1]:
            raise RouteRefusal("R14", "candidate and score context have %d and %d columns"
                               % (cc.shape[1], sc.shape[1]))
    cw = None
    if rows.cand_w is not None:
        try:
            cw = S.check_row_weights(rows.cand_w, n)
        except S.WeightRefusal as exc:
            raise RouteRefusal("R25", "cand_w: %s" % exc,
                               fix="one weight per candidate (fit.weights.weights_for_rows)") from None
    sr = np.asarray(rows.score_rows)
    if sr.shape != (m,):
        raise RouteRefusal("R14", "score_rows must hold one position per score row")
    fb = _finite(_float_vector(rows.fallback_link, "fallback_link", m), "fallback_link", "U3")
    return {"cut": cut, "lead": lead, "ck": ck, "cd": cd, "cu": cu, "cg": cg, "clat": clat, "clon": clon,
            "cz": cz, "cc": cc, "cy": cy, "cw": cw, "sk": sk, "si": si, "su": su, "sg": sg, "slat": slat,
            "slon": slon, "sz": sz, "sc": sc, "sr": sr, "fb": fb, "n": n, "m": m}


def _hash_arrays(*arrays):
    h = hashlib.sha256()
    for a in arrays:
        arr = np.ascontiguousarray(np.asarray(a))
        if arr.dtype == object:
            data = "\x1f".join(str(v) for v in arr.ravel().tolist()).encode("utf-8")
        else:
            data = arr.tobytes()
        h.update(("%s|%s|" % (arr.dtype.str, arr.shape)).encode("ascii"))
        h.update(hashlib.sha256(data).digest())
    return h.hexdigest()


def _pool_fingerprint(chk, block_of):
    blocks = sorted(set(block_of.values()))
    return _hash_arrays(np.asarray([chk["cut"], chk["lead"]], np.int64), chk["ck"], chk["cd"], chk["cu"],
                        chk["cg"], chk["clat"], chk["clon"], chk["cz"], chk["sk"], chk["si"], chk["su"],
                        chk["sg"], chk["slat"], chk["slon"], chk["sz"],
                        np.asarray(["|".join(b) for b in blocks], dtype=object))


@dataclass(frozen=True)
class NeighbourPools:
    """Every score row's pool of one pass, fixed before any solve (SPEC_NEIGHBOUR.md 1.4).

    fingerprint  hash of the rows and blocks the pools were built on (refused on other rows)
    index        per score row: candidate indices (int32) in pool order, or None (no pool: fallback)
    drop         per score row: the drop groups, sorted (the own block alone for a row with no pool)"""
    fingerprint: str
    index: Tuple[Optional[np.ndarray], ...]
    drop: Tuple[Tuple[str, ...], ...]


def neighbour_pools(rows, blocks, echo=None):
    """NeighbourPools of a pass: the strict pool and drop set of every score row, in score order (the
    rule of neighbour_pool_loro, on the pass's arrays). Pools depend on the candidates, Z, places and
    issue days only, so one result serves every arm of the pass."""
    chk = _check_neighbour_rows(rows)
    block_of = _block_map(blocks)
    for g in set(chk["sg"].tolist()) | set(chk["cg"].tolist()):
        if g not in block_of:
            raise RouteRefusal("G-DISJOINT", "group %r is in no overlap block" % (g,))
    cos_c = np.cos(chk["clat"] * _DEGREE)
    # unit ids as integer codes (the same equalities as the names, compared fast)
    _, codes = np.unique(np.r_[chk["cu"], chk["su"]].astype(str), return_inverse=True)
    ccode, scode = codes[:chk["n"]].astype(np.int64), codes[chk["n"]:].astype(np.int64)
    index, drop = [], []
    m = chk["m"]
    for i in range(m):
        unit, issue = chk["su"][i], int(chk["si"][i])
        sel = _pool_of_row(issue, int(scode[i]), float(chk["slat"][i]), float(chk["slon"][i]), chk["sz"][i],
                           chk["cd"], ccode, chk["clat"], cos_c, chk["clon"], chk["cz"])
        group = chk["sg"][i]
        if sel is None:
            index.append(None)
            drop.append(tuple(block_of[group]))
            continue
        _assert_pool(sel, chk["cd"], chk["cu"], chk["cut"], issue, unit, "score row key %d" % int(chk["sk"][i]))
        arr = sel.astype(np.int32)
        arr.setflags(write=False)
        index.append(arr)
        drop.append(_drop_groups(group, chk["cg"][sel].tolist(), block_of))
        if echo is not None and (i + 1) % int(K.TABLE_ROW_BLOCK_ROWS) == 0:
            echo("neighbour pools: %d of %d rows" % (i + 1, m))
    return NeighbourPools(fingerprint=_pool_fingerprint(chk, block_of), index=tuple(index), drop=tuple(drop))


def pool_records(rows, pools):
    """The rows of pools_<pass>.parquet (SPEC_TABLE_MODE.md 3.8 step 9) as plain columns: the scored row's
    key, its pool's row keys in pool order (empty when it has none), its drop groups and the fallback
    flag."""
    chk = _check_neighbour_rows(rows)
    if not isinstance(pools, NeighbourPools) or len(pools.index) != chk["m"]:
        raise RouteRefusal("R14", "pools must be the NeighbourPools of these rows")
    keys = chk["ck"]
    return {"score_key": chk["sk"].copy(),
            "pool_keys": [np.zeros(0, np.int64) if p is None else keys[p] for p in pools.index],
            "drop_groups": [list(d) for d in pools.drop],
            "pool_fallback": np.asarray([p is None for p in pools.index], dtype=bool)}


@dataclass(frozen=True)
class NeighbourAnswers:
    """The dense tree-answer matrix of one table kind (SPEC_TABLE_MODE.md 3.8 step 7).

    keys        int64 (rows,) store row keys, strictly ascending
    values      float32 (rows, bank trees): bank tree j's answer in column j; a row's own group's trees
                are NaN (never read: they are always in the row's drop set)
    tree_group  the group of every bank tree, in bank order (the store's own record)
    kind        the table kind ('plain', 'corrector' or 'placebo_corrector')"""
    keys: np.ndarray
    values: np.ndarray
    tree_group: Tuple[str, ...]
    kind: str


def dense_answers(store, table_kind, row_keys, row_group, tree_group):
    """NeighbourAnswers for the listed rows from the tree-answer store: each group's rows read with one
    unit_view of that group's table, placed by the view's tree_index. tree_group is checked against the
    store's own trees (n_trees, own_columns: physical keys, G-DISJOINT). Refuses duplicate keys, a row
    answered from another group's table and a view whose columns are not every tree outside the group."""
    keys = _int_vector(row_keys, "row_keys", rule="R20")
    groups = _names(row_group, "row_group", keys.shape[0])
    owners = RK._owners(tree_group)
    n_trees = getattr(store, "n_trees", None)
    own_columns = getattr(store, "own_columns", None)
    if isinstance(n_trees, bool) or not isinstance(n_trees, Integral) or not callable(own_columns) \
            or not callable(getattr(store, "unit_view", None)):
        raise RouteRefusal("G-DISJOINT", "store must be the tree-answer store (n_trees, own_columns, unit_view)")
    if int(n_trees) != owners.size:
        raise RouteGuardError("G-DISJOINT: tree_group lists %d trees, the store's bank holds %d"
                              % (owners.size, int(n_trees)))
    for g in sorted(set(owners.tolist()) | set(groups.tolist())):
        have = np.asarray(own_columns(g), dtype=np.int64)
        if have.ndim != 1 or not np.array_equal(have, np.flatnonzero(owners == g)):
            raise RouteGuardError("G-DISJOINT: tree_group disagrees with the store's own trees for group %s" % g)
    order = np.argsort(keys, kind="stable")
    ks, gs = keys[order], groups[order]
    if ks.size > 1 and not np.all(np.diff(ks) > 0):
        raise RouteRefusal("R20", "row_keys hold duplicates")
    kind = getattr(table_kind, "value", table_kind)
    values = np.full((ks.size, owners.size), np.nan, dtype=np.float32)
    for g in sorted(set(gs.tolist())):
        sel = np.flatnonzero(gs == g)
        view = store.unit_view(ks[sel], table_kind)
        if getattr(view, "group", None) != g:
            raise RouteGuardError("G-DISJOINT: rows of group %s were answered from the table of group %s"
                                  % (g, getattr(view, "group", None)))
        idx = np.asarray(view.tree_index, dtype=np.int64)
        if not np.array_equal(idx, np.flatnonzero(owners != g)):
            raise RouteGuardError("G-DISJOINT: the table of group %s does not answer exactly the trees "
                                  "outside the group" % g)
        vals = np.asarray(view.values)
        if vals.shape != (sel.size, idx.size):
            raise RouteRefusal("R20", "the store answered shape %s for %d rows and %d columns"
                               % (vals.shape, sel.size, idx.size))
        values[np.ix_(sel, idx)] = vals
    ks = ks.copy()
    ks.setflags(write=False)
    return NeighbourAnswers(keys=ks, values=values, tree_group=tuple(owners.tolist()), kind=str(kind))


def _answer_rows(answers, keys, what):
    pos = np.searchsorted(answers.keys, keys)
    pos_c = np.minimum(pos, max(answers.keys.size - 1, 0))
    if answers.keys.size == 0 or not np.array_equal(answers.keys[pos_c], keys):
        raise RouteRefusal("R20", "%d %s row key(s) have no tree answers"
                           % (int(np.count_nonzero(answers.keys[pos_c] != keys)) if answers.keys.size
                              else keys.size, what),
                           fix="build the dense answers over every candidate and score row")
    return pos_c


def _check_answers(answers, tree_group):
    if not isinstance(answers, NeighbourAnswers):
        raise RouteRefusal("R20", "answers must be NeighbourAnswers (dense_answers), got %s"
                           % type(answers).__name__)
    owners = RK._owners(tree_group)
    if tuple(answers.tree_group) != tuple(owners.tolist()):
        raise RouteGuardError("G-DISJOINT: the answers' tree groups are not the bank's tree_group")
    vals = answers.values
    if not isinstance(vals, np.ndarray) or vals.ndim != 2 or vals.shape != (answers.keys.size, owners.size) \
            or vals.dtype.kind != "f":
        raise RouteRefusal("R20", "answers.values must be float (rows, %d trees)" % owners.size)
    keys = np.asarray(answers.keys)
    if keys.ndim != 1 or (keys.size and keys.dtype.kind not in "iu") or \
            (keys.size > 1 and not np.all(np.diff(keys) > 0)):
        raise RouteRefusal("R20", "answers.keys must be strictly ascending integer row keys")
    return owners


def _pools_for(chk, blocks, pools):
    """Pools handed to a kernel: the fingerprint (the rows they were built on), then every pool asserted
    again as neighbour_pools asserts it (U4, G-FITCUT: no row after the cut, none on or after the issue
    day, never the row itself), its size (C11) and its drop set (R14, LORO: the own block plus every
    pool group's block). The fingerprint covers the input rows, not the index or the drop sets
    (FIX_REPORT.md, leakage review item 1)."""
    block_of = _block_map(blocks)
    if pools is None:
        return block_of, None
    if not isinstance(pools, NeighbourPools) or len(pools.index) != chk["m"] or len(pools.drop) != chk["m"]:
        raise RouteRefusal("R14", "pools must be the NeighbourPools of these rows (neighbour_pools)")
    if pools.fingerprint != _pool_fingerprint(chk, block_of):
        raise RouteRefusal("R14", "the pools were built on other rows, Z, issue days or blocks",
                           fix="build them with neighbour_pools(rows, blocks) on this pass")
    n = chk["n"]
    lo = int(K.NEIGHBOUR_POOL_MIN_ROWS)
    hi = int(K.NEIGHBOUR_POOL_FEATURE)
    for i in range(chk["m"]):
        idx, drop = pools.index[i], pools.drop[i]
        what = "handed-in pool, score row key %d" % int(chk["sk"][i])
        group = chk["sg"][i]
        if idx is None:
            if tuple(drop) != tuple(block_of[group]):
                raise RouteRefusal("R14", "%s: a row with no pool must drop its own block alone, got %s"
                                   % (what, drop))
            continue
        arr = np.asarray(idx)
        if arr.ndim != 1 or (arr.size and arr.dtype.kind not in "iu") or arr.dtype == np.bool_:
            raise RouteRefusal("R14", "%s: the index must be a 1-D integer array" % what)
        if arr.size and (int(arr.min()) < 0 or int(arr.max()) >= n):
            raise RouteRefusal("R14", "%s: an index lies outside the %d candidates" % (what, n))
        if np.unique(arr).size != arr.size:
            raise RouteRefusal("R14", "%s: the pool repeats a candidate" % what)
        if arr.size < lo or arr.size > hi:
            raise RouteRefusal("C11", "%s: the pool holds %d rows; a pool holds %d to %d"
                               % (what, arr.size, lo, hi))
        sel = arr.astype(np.int64)
        _assert_pool(sel, chk["cd"], chk["cu"], chk["cut"], int(chk["si"][i]), chk["su"][i], what)
        want = _drop_groups(group, chk["cg"][sel].tolist(), block_of)
        if tuple(drop) != want:
            raise RouteRefusal("R14", "%s: the drop set %s is not the own block plus every pool group's block %s"
                               % (what, tuple(drop), want))
    return block_of, pools


# ---------------------------------------------------------------------------------------------------
# The kernels (private, as the per-unit and region kernels)
def _route(rows, answers, tree_group, blocks, design, points, tol, sweep, pools, echo):
    chk = _check_neighbour_rows(rows)
    tol = RK._check_tolerance(tol)
    has_context = chk["cc"] is not None
    nctx = chk["cc"].shape[1] if has_context else 0
    design = _check_design(design, has_context)
    points = tuple(_as_point(p) for p in points)
    penalties = [neighbour_point_penalties(p, has_context) for p in points]
    base = neighbour_base_point(has_context)
    owners = _check_answers(answers, tree_group)
    block_of, pools = _pools_for(chk, blocks, pools)
    if pools is None:
        pools = neighbour_pools(rows, blocks, echo)
    bank_groups = set(owners.tolist())
    cand_arow = _answer_rows(answers, chk["ck"], "candidate") if chk["n"] else np.zeros(0, np.int64)
    score_arow = _answer_rows(answers, chk["sk"], "score")
    cy, cw, cc, sc, fb = chk["cy"], chk["cw"], chk["cc"], chk["sc"], chk["fb"]
    m, npts = chk["m"], len(points)
    columns_cache: Dict[Tuple[str, ...], np.ndarray] = {}
    items: List[Tuple[int, np.ndarray, Optional[np.ndarray], Tuple[str, ...], bool]] = []
    n_fit = 0
    kept = np.zeros(m, np.int64)
    for i in range(m):
        idx, drop = pools.index[i], pools.drop[i]
        if idx is None:
            continue
        if bank_groups <= set(drop):
            items.append((i, idx, None, drop, False))          # every tree dropped: trees-off (O8)
            continue
        cols = columns_cache.get(drop)
        if cols is None:
            own = [g for g in drop if g in bank_groups]      # a group with no tree drops nothing
            cols = (RK.router_tree_columns(owners.tolist(), own) if own
                    else np.arange(owners.size, dtype=np.int64))
            columns_cache[drop] = cols
        kept[i] = cols.size
        items.append((i, idx, cols, drop, bool(sweep) and n_fit < S.NVERIFY))
        n_fit += 1

    def load(item):
        i, idx, cols, drop, verify = item
        if cols is None:
            return item, None
        arows = np.concatenate([cand_arow[idx], score_arow[i:i + 1]])
        values = answers.values[np.ix_(arows, cols)]
        RK.assert_no_own_group_column(owners[cols], drop, "score row key %d" % int(chk["sk"][i]))
        if not np.all(np.isfinite(values)):
            raise RouteGuardError("G-PLUMB: score row key %d: %d missing tree answer(s) in its kept columns"
                                  % (int(chk["sk"][i]), int(values.size - np.count_nonzero(np.isfinite(values)))))
        return item, values

    def solve(loaded):
        (i, idx, cols, drop, verify), values = loaded
        k = idx.size
        y = cy[idx]
        ctx_f = cc[idx] if has_context else None
        ctx_t = sc[i:i + 1] if has_context else None
        p0 = trees_off_neighbour(_trees_off_design(ctx_f, k), y, _trees_off_design(ctx_t, 1), base)
        if values is None:
            return np.repeat(p0, npts), p0[0]
        Xc = RK.build_column_block(design, None, ctx_f, values[:k], None).X
        Xt = RK.build_column_block(design, None, ctx_t, values[k:], None).X
        ntree = values.shape[1]
        uid = "score row key %d" % int(chk["sk"][i])
        o = NEIGHBOUR_UNPENALISED_COLUMNS
        if cw is None:
            if sweep:
                P = S.solve_grid(Xc, y, Xt, ntree, nctx, penalties, verify, unit_id=uid, n_unpenalised=o)
            else:
                a_tree, a_ctx = penalties[0]
                P = S.solve_point(Xc, y, Xt, ntree, nctx, a_tree, a_ctx, n_unpenalised=o)[:, None]
        else:
            w = cw[idx]
            if sweep:
                P = S.solve_grid_weighted(Xc, y, w, Xt, ntree, nctx, penalties, verify, unit_id=uid,
                                          n_unpenalised=o)
            else:
                a_tree, a_ctx = penalties[0]
                P = S.solve_point_weighted(Xc, y, w, Xt, ntree, nctx, a_tree, a_ctx, n_unpenalised=o)[:, None]
        return P[0], p0[0]

    out = np.empty((m, npts))
    out0 = np.empty(m)
    for i in range(m):
        if pools.index[i] is None:
            out[i, :] = fb[i]
            out0[i] = fb[i]
    workers = RK._router_workers()
    block = int(K.TABLE_ROW_BLOCK_ROWS)     # progress lines only; a row's bytes do not depend on it
    for lo in range(0, len(items), block):
        part = items[lo:lo + block]
        for (i, _idx, _cols, _drop, _v), (P, p0) in zip(part, RK._solve_units(part, load, solve, workers)):
            out[i, :] = P
            out0[i] = p0
        if echo is not None:
            echo("neighbour router: %d of %d pooled rows solved" % (min(lo + block, len(items)), len(items)))
    record = _record(chk, pools, kept, owners.size, items, tol, sweep, npts)
    return RouteOutput(row_positions=chk["sr"].copy(), predictions=out, trees_off=out0, grid=tuple(points),
                       n_units_fitted=record["n_rows_pool"], n_units_fallback=0,
                       n_rows_pool_fallback=record["n_rows_pool_fallback"]), record


def _record(chk, pools, kept, n_trees, items, tol, sweep, npts):
    m = chk["m"]
    size = np.asarray([0 if p is None else p.size for p in pools.index], np.int64)
    has = size > 0
    ngroups = np.asarray([0 if p is None else len(set(chk["cg"][p].tolist())) for p in pools.index], np.int64)
    ndrop = np.asarray([len(d) for d in pools.drop], np.int64)
    no_tree = np.zeros(m, bool)
    for (i, _idx, cols, _drop, _v) in items:
        no_tree[i] = cols is None
    gap = [int(chk["cd"][p].max()) - int(chk["si"][i]) for i, p in enumerate(pools.index) if p is not None]

    def q(a):
        return None if a.size == 0 else {"min": int(a.min()), "median": float(np.median(a)), "max": int(a.max())}

    return {"kind": "neighbour", "cut": chk["cut"], "lead": chk["lead"], "n_rows": int(m),
            "n_rows_pool": int(has.sum()), "n_rows_pool_fallback": int((~has).sum()),
            "n_rows_no_tree": int(no_tree.sum()), "n_candidates": int(chk["n"]),
            "pool_size": q(size[has]), "groups_per_pool": q(ngroups[has]), "drop_set_size": q(ndrop),
            "kept_trees": q(kept[has & ~no_tree]), "n_bank_trees": int(n_trees),
            "max_pool_day_minus_issue_day": max(gap) if gap else None,
            "weighted": chk["cw"] is not None, "sweep": bool(sweep), "grid_points": int(npts),
            "verified_rows": int(sum(1 for it in items if it[4])), "tolerance": float(tol),
            "pools_fingerprint": pools.fingerprint,
            "per_row": {"score_key": chk["sk"].copy(), "pool_size": size, "n_pool_groups": ngroups,
                        "n_drop_groups": ndrop, "kept_trees": kept.copy(),
                        "kept_share": kept / float(n_trees), "pool_fallback": ~has, "no_tree": no_tree}}


def _route_neighbour_grid(rows, answers, tree_group, blocks, design, tol, *, pools=None, echo=None):
    """The neighbour router on the decision surface: per score row, the ridge on its strict pool
    ([intercept, context, kept tree answers], intercept alone unpenalised) solved at EVERY point of the
    R14 grid (shared-Gram dual, reference check on the first NVERIFY fitted rows), plus trees-off.

    rows        NeighbourRows (link space; cand_w set for a GLS arm, None otherwise)
    answers     NeighbourAnswers of the arm's table kind (dense_answers)
    tree_group  the group of every bank tree, in bank order (checked against answers)
    blocks      OverlapBlocks; design: derived['R14'].value (the neighbour design)
    tol         the pass's R36 tolerance: checked and recorded (the kind has no normal, so no trees-off
                identity is asserted; G-PLUMB compares trees-off with a closed form in the decision step)
    pools       optional NeighbourPools of these rows (neighbour_pools), shared by the pass's arms;
                computed here when None (the same pools)
    echo        optional progress callback
    Returns (RouteOutput with one column per grid point, record). Rows with no pool hold fallback_link
    in every column and in trees-off (n_rows_pool_fallback); rows whose drop set holds every tree hold
    their trees-off in every column (record n_rows_no_tree)."""
    has_context = getattr(rows, "cand_ctx", None) is not None
    return _route(rows, answers, tree_group, blocks, design, neighbour_grid(has_context), tol, True, pools,
                  echo)


def _route_neighbour_at(rows, answers, tree_group, blocks, design, point, tol, *, pools=None, echo=None):
    """The neighbour router at ONE grid point (test and guard passes at the pinned point): solve_point
    per row (solve_point_weighted for a GLS arm), plus trees-off. Arguments as _route_neighbour_grid;
    ``point`` must be a grid point."""
    has_context = getattr(rows, "cand_ctx", None) is not None
    neighbour_point_penalties(point, has_context)
    return _route(rows, answers, tree_group, blocks, design, (point,), tol, False, pools, echo)


def _trees_off_neighbour_pass(rows, blocks, *, pools=None):
    """Trees-off alone for a pass (no tree answers read): per row with a pool, intercept + context on
    its pool at the R14 base point (trees_off_neighbour); fallback_link for a row without a pool. The
    same values as the trees-off column of the kernels (a lead saves the identity link's trees-off,
    printed beside, when its pinned arm is on another link; owner ruling V1 made the donor-row median
    the neighbour kind's decline target). Returns (trees-off (score rows,),
    rows with a pool, rows without)."""
    chk = _check_neighbour_rows(rows)
    _, pools = _pools_for(chk, blocks, pools)
    if pools is None:
        pools = neighbour_pools(rows, blocks)
    has_context = chk["cc"] is not None
    base = neighbour_base_point(has_context)
    out0 = np.empty(chk["m"])
    items = []
    for i, idx in enumerate(pools.index):
        if idx is None:
            out0[i] = chk["fb"][i]
        else:
            items.append((i, idx))

    def solve(item):
        i, idx = item
        ctx_f = chk["cc"][idx] if has_context else None
        ctx_t = chk["sc"][i:i + 1] if has_context else None
        return trees_off_neighbour(_trees_off_design(ctx_f, idx.size), chk["cy"][idx],
                                   _trees_off_design(ctx_t, 1), base)[0]

    # the kernels' loop discipline (BLAS at ROUTER_WORKER_BLAS_THREADS), so the values are their bytes
    for (i, _idx), p0 in zip(items, RK._solve_units(items, lambda it: it, solve, RK._router_workers())):
        out0[i] = p0
    return out0, len(items), chk["m"] - len(items)


__all__ = [
    "NEIGHBOUR_UNPENALISED_COLUMNS", "haversine_angle", "neighbour_grid", "neighbour_base_point",
    "neighbour_point_penalties", "pool_feature_z", "constant_z_columns", "neighbour_pool_loro", "trees_off_neighbour",
    "NeighbourRows", "NeighbourPools", "neighbour_pools", "pool_records", "NeighbourAnswers", "dense_answers",
]
