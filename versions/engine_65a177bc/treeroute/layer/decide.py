"""R26 penalty search, the N2 guard, R27 MAE adoption with the decline rule, R29's pinned lead adoption,
G-PLUMB's identities, and decide(), which runs them on one decision surface.

SCIENCE bodies for the owner-approved signatures penalty_search, n2_eligible, select_adoption,
forecast_adoption and check_plumbing (treeroute/_proposed/layer.py; owner rulings A-F: every proposed
default accepted):
  - R26: every grid point of an arm is scored on the decision surface by MAE in y units, on
    back-transformed, CLIPPED predictions (R28 before any score). The whole grid is searched; a pick
    on the grid's edge (first or last level, first or last ratio) is flagged, never extended (Q13 a).
    Trees-off has one candidate and no grid. A tie goes to the first grid point (the source's strict
    '<').
  - N2 (D64): an arm is eligible only if its MAE is STRICTLY lower than its own link's trees-off MAE
    on the same rows (the geometric normal for a log arm, the arithmetic normal for identity).
  - R27 (D65): eligible tree arms are ranked by MAE; a tie goes to the first arm in candidate_arms
    order (the source's min()). If no arm is eligible the layer DECLINES to the decline target, the
    identity-link trees-off (the arithmetic normal; owner ruling). The best tree arm and its penalty
    are recorded either way (R29 pins it when the nowcast declined): the adopted arm when one is
    adopted, else the tree arm with the lowest MAE. predict-zero and corr2 are printed beside and
    never used. A placebo or trees-off arm is never selectable: select_adoption refuses one.
  - R29 (D86): a lead is pinned to the nowcast's adopted link, tool, weighting and penalty (its best
    tree arm and penalty when the nowcast declined); the N2 guard runs on the lead's inner guard
    surface; a pinned arm that fails it DECLINES to the decline target at that lead. The placebo is
    built only at the longest lead.
  - Scores follow D67: a non-finite (y, prediction) pair is refused; the caller picks the rows and
    prints the counts. MAE is float(mean(|y - p|)), the source's expression, so a replay reproduces the
    shipped values bit for bit.

decide() never receives a test row (G-LOCK). Its DecisionSurface is issued ONLY by the label vault
(LabelView.decision_surface): the vault looks up each requested (unit, step) in its as-of view at the
cut and fills y itself, so no caller can hand decide() labels of its own; the arrays are read-only and
the surface carries the SHA-256 of its content, which decide() re-checks against the vault that issued
it. A direct construction (or dataclasses.replace) is refused, as are a row at or after the test
window, a label read after its view's cut, and a vault TestLabels object anywhere. decide() also takes
the nowcast's GUARD FitContext and runs G-FITCUT on the surface (every inner score row issued at or
after the inner guard's cut; labels read at or before the lead's fit cut). It reads R22's link set
from derived.json and refuses a surface that does not carry every selectable arm and trees-off of
candidate_arms(links); GLS arms may be missing only under an explicit gls_absent_reason, which is
recorded. A harness link key enters only through a declared LegacyCandidates list (layer/arms.py).
decide() registers the adoption document (the adoption, every candidate, and the decision section:
surface hash, cuts, candidate order, missing arms, legacy declaration, candidate-table hash) with the
vault that issued the surface; labels/vault.lock_adoption locks exactly that document before any test
label opens, and refuses an adoption no decide() made on a surface of that vault.

The shapes (GuardStatus, GuardResult, PenaltyPick, Adoption, LeadAdoption) are FIELD-IDENTICAL copies of
the approved shapes in the proposed common module (G-IMPORT keeps engine code from importing it).
Grid points are route/kinds.py's GridPoint (the router kind's grid); any point with level and ratio
is read into one.
"""
# Provenance for the module: pm25_adaptation.py:795-808 (rank: best MAE over the grid, strict '<', so
# the FIRST grid point wins a tie), :809-818 (rank_single: trees-off, one penalty-free candidate),
# :894-915 (N2 guard: eligible iff inner MAE < own link-matched normal's MAE, strict), :915-930 (pick =
# min(eligible, key=MAE) else the arithmetic normal; tree_pick = the best tree arm when declined; edge
# flags TOP / BOTTOM per axis), :263-307 (score: mae = float(np.mean(np.abs(y - p))));
# pm25_forecast.py:566-606 (the lead's guard, the adoption on disk before any test row is routed);
# plan 2.4 R24-R29, 5 G-PLUMB, G-CLIP, G-LOCK.

import math
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from numbers import Integral, Real
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from treeroute.derive.derived import sha256_of_array, sha256_of_json
from treeroute.derive.shapes import CutKind, Link
from treeroute.route.kinds import GridPoint

from .arms import (SELECTABLE_TOOLS, ArmSpec, LayerRefusal, LegacyCandidates, Tool, Weighting, arm_name,
                   check_arm, decision_candidates, is_r22_link, link_value, selectable_order,
                   trees_off_of)
from .links import ClipCounts, clip_with_counts, legal_range_of


# ---------------------------------------------------------------------------------------------------
# Shapes (field-identical to the approved shared shapes)
class GuardStatus(Enum):
    PASS = "pass"
    FLAG = "flag"                    # report only, never a choice
    BLOCK = "block"                  # stops the run


@dataclass(frozen=True)
class GuardResult:
    """What every validator returns. Messages print a rule id, the columns, the fix and a Part."""
    rule_id: str
    status: GuardStatus
    columns: Tuple[str, ...]
    reason: str
    fix: str
    part: Optional[int]
    details: Mapping[str, Any]


@dataclass(frozen=True)
class PenaltyPick:
    """R26 outcome for one arm."""
    arm: ArmSpec
    point: Optional[GridPoint]         # None for trees-off
    mae: float
    mae_by_point: Mapping[GridPoint, float]
    edge: bool


@dataclass(frozen=True)
class Adoption:
    """R27 outcome, the content of adoption.json (the nowcast pass)."""
    adopted: Optional[ArmSpec]         # None = declined to the decline target
    penalty: Optional[GridPoint]
    declined: bool
    best_tree_arm: ArmSpec
    best_tree_penalty: GridPoint
    eligible: Tuple[ArmSpec, ...]
    surface_mae: Mapping[str, float]   # every candidate, trees-off included
    beside: Mapping[str, float]        # predict-zero MAE, corr2 per arm (printed, never used)


@dataclass(frozen=True)
class LeadAdoption:
    """R29 outcome at one lead: the content of that lead's adoption file."""
    lead: int
    pinned: ArmSpec
    penalty: GridPoint
    guard_passed: bool
    adopted: Optional[ArmSpec]         # None = declined at this lead
    placebo_built: bool                # True only at the longest lead


# ---------------------------------------------------------------------------------------------------
# Scores (D67: non-finite pairs refused; the caller picks the rows and prints the counts)
def _vector(values: Any, what: str, rule: str) -> np.ndarray:
    arr = np.asarray(values)
    if arr.ndim != 1 or arr.dtype.kind not in "iuf" or arr.dtype == np.bool_:
        raise LayerRefusal(rule, "%s must be a 1-D numeric array, got %s %s"
                           % (what, arr.dtype, arr.shape))
    return np.asarray(arr, dtype=np.float64)


def _require_finite(arr: np.ndarray, what: str, rule: str) -> None:
    if arr.size and not np.isfinite(arr).all():
        raise LayerRefusal(rule, "%s holds %d missing or infinite value(s) (D67: a non-finite pair is "
                           "refused; the caller picks the rows and prints the count)"
                           % (what, int(arr.size - np.count_nonzero(np.isfinite(arr)))),
                           fix="score only rows where every column exists")


def surface_mae(y: np.ndarray, p: np.ndarray) -> float:
    """MAE in y units: float(mean(|y - p|)) (the source's expression). Refuses a shape mismatch, no
    rows and a non-finite pair (D67)."""
    yv = _vector(y, "y", "R27")
    pv = _vector(p, "predictions", "R27")
    if yv.shape != pv.shape:
        raise LayerRefusal("R27", "y has %d rows, the predictions %d" % (yv.size, pv.size))
    if yv.size == 0:
        raise LayerRefusal("R27", "no rows to score")
    _require_finite(yv, "y", "R27")
    _require_finite(pv, "the predictions", "R27")
    return float(np.mean(np.abs(yv - pv)))


def surface_corr2(y: np.ndarray, p: np.ndarray) -> float:
    """Squared Pearson correlation (printed beside MAE, never used to select); NaN when either side is
    constant. Refuses what surface_mae refuses."""
    surface_mae(y, p)            # the same row checks
    yv = np.asarray(y, dtype=np.float64)
    pv = np.asarray(p, dtype=np.float64)
    yd, pd_ = yv - yv.mean(), pv - pv.mean()
    den = float(np.sqrt(np.sum(yd * yd) * np.sum(pd_ * pd_)))
    if not den > 0:
        return float("nan")
    r = float(np.sum(yd * pd_)) / den
    return r * r


def _finite_number(x: Any, what: str, rule: str) -> float:
    if isinstance(x, bool) or not isinstance(x, (Real, np.floating, np.integer)) or not math.isfinite(float(x)):
        raise LayerRefusal(rule, "%s must be a finite number, got %r" % (what, x))
    return float(x)


# ---------------------------------------------------------------------------------------------------
# Grid points
def as_point(point: Any) -> GridPoint:
    """A grid point read into route/kinds.py's GridPoint (level float, ratio float or None)."""
    try:
        level, ratio = point.level, point.ratio
    except AttributeError:
        raise LayerRefusal("R26", "a grid point needs a level and a ratio, got %r" % (point,)) from None
    lv = _finite_number(level, "a grid level", "R26")
    rv = None if ratio is None else _finite_number(ratio, "a grid ratio", "R26")
    return GridPoint(lv, rv)


def _grid(grid: Any) -> Tuple[GridPoint, ...]:
    points = tuple(as_point(p) for p in grid)
    if not points:
        raise LayerRefusal("R26", "the grid is empty; a tree arm is searched over the router kind's "
                                  "whole grid (R14, R26)")
    if len(set(points)) != len(points):
        raise LayerRefusal("R26", "the grid repeats a point")
    if len({p.ratio is None for p in points}) != 1:
        raise LayerRefusal("R26", "the grid mixes points with and without a ratio")
    return points


def edge_axes(point: GridPoint, grid: Sequence[GridPoint]) -> Dict[str, Optional[str]]:
    """Which grid edge a pick sits on, per axis: 'top', 'bottom' or None. An axis with fewer than two
    distinct values has no edge (a frozen axis). Flag only, never extended (Q13 a)."""
    pts = _grid(grid)
    p = as_point(point)
    if p not in pts:
        raise LayerRefusal("R26", "%r is not a point of the grid" % (p,))
    out: Dict[str, Optional[str]] = {"level": None, "ratio": None}
    levels = sorted({q.level for q in pts})
    if len(levels) > 1:
        out["level"] = "top" if p.level == levels[-1] else ("bottom" if p.level == levels[0] else None)
    ratios = sorted({q.ratio for q in pts if q.ratio is not None})
    if len(ratios) > 1 and p.ratio is not None:
        out["ratio"] = "top" if p.ratio == ratios[-1] else ("bottom" if p.ratio == ratios[0] else None)
    return out


# ---------------------------------------------------------------------------------------------------
# Provenance: plan 2.4 R26 (whole grid on the decision surface for every package; edge picks flagged,
# never extended, Q13 a; trees-off one candidate with no grid); pm25_adaptation.py:795-808 (rank: best
# MAE, strict '<' so the FIRST grid point wins a tie).
def penalty_search(arm: ArmSpec, surface_predictions: np.ndarray, y_surface: np.ndarray,
                   grid: Tuple[GridPoint, ...]) -> PenaltyPick:
    """R26: score every grid point of one arm on the decision surface by MAE and keep the best.

    Rule: R26, R27, R28. MAE in y units on back-transformed, CLIPPED predictions (the caller clips
    with clip_to_legal; decide() does). The whole grid is searched; a pick on the grid's edge is
    flagged (edge_axes), never extended. A tie goes to the first grid point in grid order. Trees-off
    has one candidate and no grid: pass grid () and a (rows,) or (rows, 1) array.
    Returns PenaltyPick (mae_by_point in grid order; empty for trees-off).
    Refuses: a placebo arm (never on the decision surface: the placebo table is built once at the test
    pass, plan 4.1 step 9); a surface row count mismatch; non-finite predictions or labels (D67); a
    grid for trees-off, or no grid for a tree arm; a grid that repeats a point.
    """
    check_arm(arm)
    if arm.tool is Tool.PLACEBO_CORRECTOR:
        raise LayerRefusal("R24", "the placebo %s never enters the decision surface; it is built once at "
                           "the test pass and never selectable" % arm_name(arm))
    y = _vector(y_surface, "the surface labels", "R26")
    if y.size == 0:
        raise LayerRefusal("R26", "the decision surface has no row")
    _require_finite(y, "the surface labels", "R26")
    P = np.asarray(surface_predictions)
    if P.dtype.kind not in "iuf" or P.dtype == np.bool_:
        raise LayerRefusal("R26", "surface predictions must be numeric, got %s" % P.dtype)
    P = np.asarray(P, dtype=np.float64)
    if arm.tool is Tool.TREES_OFF:
        if tuple(grid):
            raise LayerRefusal("R26", "trees-off has one candidate and no grid (R26); pass grid ()")
        if P.ndim == 2 and P.shape[1] == 1:
            P = P[:, 0]
        if P.ndim != 1 or P.shape[0] != y.size:
            raise LayerRefusal("R26", "trees-off predictions have shape %s for %d surface rows"
                               % (P.shape, y.size))
        _require_finite(P, "the %s predictions" % arm_name(arm), "R26")
        return PenaltyPick(arm=arm, point=None, mae=surface_mae(y, P), mae_by_point={}, edge=False)
    points = _grid(grid)
    if P.ndim != 2 or P.shape != (y.size, len(points)):
        raise LayerRefusal("R26", "%s: surface predictions have shape %s; the surface has %d rows and "
                           "the grid %d points" % (arm_name(arm), P.shape, y.size, len(points)))
    _require_finite(P, "the %s predictions" % arm_name(arm), "R26")
    maes = []
    best = None
    for k in range(len(points)):
        m = float(np.mean(np.abs(y - P[:, k])))
        maes.append(m)
        if best is None or m < maes[best]:
            best = k
    axes = edge_axes(points[best], points)
    return PenaltyPick(arm=arm, point=points[best], mae=maes[best],
                       mae_by_point=dict(zip(points, maes)),
                       edge=bool(axes["level"] is not None or axes["ratio"] is not None))


# Provenance: pm25_adaptation.py:894-915 (N2 guard: eligible iff inner MAE < own link-matched normal's
# MAE, strict); plan 2.4 R27, Q17 a; D64 (strictly lower, the source).
def n2_eligible(arm_mae: float, own_trees_off_mae: float) -> bool:
    """N2 guard: an arm is eligible only if it beats its own-link trees-off on the decision surface.

    Rule: R27 (N2), R16 (D64). The comparison is against the arm's OWN link-matched trees-off, both
    MAE in y units on the same rows: eligible iff arm_mae < own_trees_off_mae, strictly (the source).
    Returns True if eligible. Refuses: non-finite inputs.
    """
    a = _finite_number(arm_mae, "the arm's MAE", "R27")
    b = _finite_number(own_trees_off_mae, "its trees-off MAE", "R27")
    return a < b


def candidate_key(arm: ArmSpec, point: Optional[Any]) -> str:
    """The key of one candidate in Adoption.surface_mae and the candidate table: the arm's name for
    trees-off (no grid), '<arm name>@level=<level>,ratio=<ratio>' for a tree arm at a grid point
    (repr of the floats, so the key round-trips)."""
    name = arm_name(arm)
    if point is None:
        return name
    p = as_point(point)
    return "%s@level=%r,ratio=%r" % (name, p.level, p.ratio)


def _check_pick(pick: Any, where: str) -> PenaltyPick:
    """A PenaltyPick penalty_search could have made: a well-formed arm, a finite MAE, and for a tree arm
    its point among its scored points with that MAE, no point scored lower, every MAE finite."""
    if not isinstance(pick, PenaltyPick):
        raise LayerRefusal("R27", "%s must be a PenaltyPick, got %s" % (where, type(pick).__name__))
    check_arm(pick.arm)
    mae = _finite_number(pick.mae, "%s MAE" % where, "R27")
    if not isinstance(pick.mae_by_point, Mapping):
        raise LayerRefusal("R27", "%s: mae_by_point must map grid points to MAEs" % where)
    scored = {as_point(p): _finite_number(m, "%s MAE at %r" % (where, p), "R27")
              for p, m in pick.mae_by_point.items()}
    if pick.point is not None:
        point = as_point(pick.point)
        if point not in scored or scored[point] != mae:
            raise LayerRefusal("R26", "%s (%s): its point %r is not among its scored grid points with its "
                               "MAE" % (where, arm_name(pick.arm), point))
        if min(scored.values()) < mae:
            raise LayerRefusal("R26", "%s (%s) is not the best point of its grid (R26 keeps the lowest MAE)"
                               % (where, arm_name(pick.arm)))
    return pick


def _selection_order(arms: Sequence[ArmSpec], order: Any) -> Tuple[Tuple[ArmSpec, ...], Optional[LegacyCandidates]]:
    """The tie order (D65) the picks must follow: selectable_order over the picks' R22 links (identity
    always included) when order is None; a declared LegacyCandidates list's selectable arms otherwise.
    A non-R22 link key without a declared list is refused."""
    if order is None:
        bad = sorted({link_value(a.link) for a in arms if not is_r22_link(a.link)})
        if bad:
            raise LayerRefusal("R22", "link key(s) %s are not R22's links; a harness link enters a decision "
                               "only through a declared LegacyCandidates order" % bad,
                               fix="take the links from derived.json's R22 entry (a legacy replay passes "
                                   "order=LegacyCandidates(...))")
        links = tuple({a.link for a in arms} | {Link.IDENTITY})      # candidate_arms sorts to R22 order
        return selectable_order(links), None
    if not isinstance(order, LegacyCandidates):
        raise LayerRefusal("R22", "order must be None (R22 links, candidate_arms order) or a declared "
                                  "LegacyCandidates list, got %s" % type(order).__name__)
    return order.selectable(), order


def _beside(beside: Any) -> Dict[str, float]:
    if not isinstance(beside, Mapping):
        raise LayerRefusal("R27", "beside must be a mapping of printed-only numbers")
    out: Dict[str, float] = {}
    for key, value in beside.items():
        if not isinstance(key, str) or not key:
            raise LayerRefusal("R27", "beside keys are non-empty names, got %r" % (key,))
        if isinstance(value, bool) or not isinstance(value, (Real, np.floating, np.integer)):
            raise LayerRefusal("R27", "beside[%r] must be a number, got %r" % (key, value))
        out[key] = float(value)
    return out


# Provenance: pm25_adaptation.py:915-930 (pick = min(eligible, key=MAE) else the arithmetic normal;
# tree_pick = best tree arm for the pin when declined); plan 2.4 R27; owner ruling (a decline adopts the
# ARITHMETIC normal, pm25_adaptation.py:133-138); D65 (a tie goes to the first arm in candidate order).
def select_adoption(picks: Tuple[PenaltyPick, ...], trees_off_mae: Mapping[Any, float],
                    beside: Mapping[str, float], *, order: Optional[LegacyCandidates] = None) -> Adoption:
    """R27: rank eligible tree arms by decision-surface MAE; decline to the arithmetic normal when none
    is eligible.

    Rule: R27, G-LOCK (D64, D65). Only selectable tree arms are ranked, by MAE (Q37). N2: an arm is
    eligible only if it beats its own link's trees-off (n2_eligible). If none is eligible the layer
    declines to the identity-link trees-off (adopted None, penalty None, declined True). The best tree
    arm and its penalty are recorded either way: the adopted arm when one is adopted, else the tree arm
    with the lowest MAE. A tie in MAE goes to the first arm in candidate order: candidate_arms order
    over R22 links, or the declared order of a LegacyCandidates list (keyword order, harness replays
    only; the only way a non-R22 link key is accepted). surface_mae holds EVERY candidate (the approved
    shape): each pick at each of its scored grid points (candidate_key) and every link's trees-off, by
    arm name. predict-zero and corr2 go in beside, printed and never used. The result is hashed by
    vault.lock_adoption before test labels open. Completeness (every selectable arm of the link set) is
    decide()'s check, which holds the link set.
    Returns Adoption.
    Refuses: a placebo or trees-off arm among the picks (never selectable); no pick; a repeated arm; a
    pick without a grid point, or one that is not its grid's best; picks out of candidate order; a
    non-R22 link key without a declared LegacyCandidates order, or one the declared list does not
    name; a trees-off MAE missing for a pick's link or for the identity link (the decline target);
    non-finite MAEs.
    """
    picks = tuple(picks)
    if not picks:
        raise LayerRefusal("R27", "no tree arm to rank", fix="pass the penalty_search result of every "
                                  "selectable arm")
    for i, pick in enumerate(picks):
        _check_pick(pick, "pick %d" % i)
        if not pick.arm.selectable or pick.arm.tool not in SELECTABLE_TOOLS:
            raise LayerRefusal("R27", "pick %d is the %s arm %s: a placebo or trees-off arm is never "
                               "selectable (R24)" % (i, pick.arm.tool.value, arm_name(pick.arm)),
                               fix="rank tree arms only (plain and corrector)")
        if pick.point is None:
            raise LayerRefusal("R27", "pick %d (%s) has no grid point; a tree arm is searched over the "
                               "grid (R26)" % (i, arm_name(pick.arm)))
    arms = [p.arm for p in picks]
    if len(set(arms)) != len(arms):
        raise LayerRefusal("R27", "an arm is ranked twice")
    tie_order, legacy = _selection_order(arms, order)
    position = {a: i for i, a in enumerate(tie_order)}
    unknown = [arm_name(a) for a in arms if a not in position]
    if unknown:
        raise LayerRefusal("R27", "arm(s) %s are not in the candidate order %s"
                           % (unknown, "of the declared legacy list" if legacy else "of candidate_arms"))
    idx = [position[a] for a in arms]
    if idx != sorted(idx):
        raise LayerRefusal("R27", "the picks are not in candidate order; that order is the tie rule (D65)",
                           fix="pass the picks in candidate_arms order (or the declared legacy order)")
    if not isinstance(trees_off_mae, Mapping):
        raise LayerRefusal("R27", "trees_off_mae must map each link to its trees-off MAE")
    allowed_keys = None if legacy is None else {a.link for a in legacy.arms}
    off: Dict[Any, float] = {}
    for link, value in trees_off_mae.items():
        link_value(link)
        if not is_r22_link(link) and (allowed_keys is None or link not in allowed_keys):
            raise LayerRefusal("R22", "the trees-off MAE of link key %r: not an R22 link and not declared "
                               "in a LegacyCandidates order" % link_value(link))
        off[link] = _finite_number(value, "the trees-off MAE of %s" % link_value(link), "R27")
    if Link.IDENTITY not in off:
        raise LayerRefusal("R27", "no identity-link trees-off MAE: the decline target (the arithmetic "
                                  "normal, R16) is not on the surface")
    missing = sorted({link_value(a.link) for a in arms if a.link not in off})
    if missing:
        raise LayerRefusal("R27", "no trees-off MAE for link(s) %s: N2 compares each arm with its own "
                           "link's trees-off" % missing)
    extra = _beside(beside)
    eligible = [p for p in picks if n2_eligible(p.mae, off[p.arm.link])]
    best_all = picks[0]
    for p in picks[1:]:
        if p.mae < best_all.mae:
            best_all = p
    if eligible:
        adopted = eligible[0]
        for p in eligible[1:]:
            if p.mae < adopted.mae:
                adopted = p
        best_tree = adopted
    else:
        adopted = None
        best_tree = best_all
    surface: Dict[str, float] = {}
    for p in picks:
        for point, value in p.mae_by_point.items():
            surface[candidate_key(p.arm, point)] = float(value)
    for link, value in off.items():
        surface[candidate_key(trees_off_of(link), None)] = value
    return Adoption(adopted=None if adopted is None else adopted.arm,
                    penalty=None if adopted is None else adopted.point,
                    declined=adopted is None,
                    best_tree_arm=best_tree.arm, best_tree_penalty=best_tree.point,
                    eligible=tuple(p.arm for p in eligible), surface_mae=surface, beside=extra)


# ---------------------------------------------------------------------------------------------------
def check_adoption(adoption: Any) -> Adoption:
    """Refuse an Adoption that select_adoption could not have made: declined exactly when nothing is
    adopted; an adopted arm (and the best tree arm, and every eligible arm) that is a selectable tree
    arm, never a placebo or trees-off; the adopted arm eligible and equal to the best tree arm with the
    same penalty; finite surface MAEs over every candidate, the best tree arm at its penalty and the
    decline target among them. Used by vault.lock_adoption before hashing. Returns it."""
    if not isinstance(adoption, Adoption):
        raise LayerRefusal("G-LOCK", "an adoption must be the layer's Adoption, got %s"
                           % type(adoption).__name__)
    if not isinstance(adoption.declined, bool):
        raise LayerRefusal("G-LOCK", "Adoption.declined must be a bool")
    for arm in (adoption.best_tree_arm,) + tuple(adoption.eligible) + (
            () if adoption.adopted is None else (adoption.adopted,)):
        check_arm(arm)
        if not arm.selectable:
            raise LayerRefusal("R27", "the adoption names the %s arm %s as a tree arm; a placebo or "
                               "trees-off arm is never selectable (R24)" % (arm.tool.value, arm_name(arm)))
    as_point(adoption.best_tree_penalty)
    if adoption.declined:
        if adoption.adopted is not None or adoption.penalty is not None:
            raise LayerRefusal("R27", "a declined adoption adopts nothing and has no penalty")
        if adoption.eligible:
            raise LayerRefusal("R27", "an adoption with eligible arms cannot decline")
    else:
        if adoption.adopted is None or adoption.penalty is None:
            raise LayerRefusal("R27", "an adoption that does not decline names its arm and penalty")
        if adoption.adopted not in adoption.eligible:
            raise LayerRefusal("R27", "the adopted arm %s is not eligible (N2)" % arm_name(adoption.adopted))
        if adoption.best_tree_arm != adoption.adopted or \
                as_point(adoption.best_tree_penalty) != as_point(adoption.penalty):
            raise LayerRefusal("R27", "when an arm is adopted it is the best tree arm, at its penalty")
    if not isinstance(adoption.surface_mae, Mapping):
        raise LayerRefusal("R27", "Adoption.surface_mae must map every candidate to its MAE")
    for name, value in dict(adoption.surface_mae).items():
        if not isinstance(name, str) or not name:
            raise LayerRefusal("R27", "surface_mae keys are candidate keys, got %r" % (name,))
        _finite_number(value, "surface_mae[%r]" % name, "R27")
    for key, what in ((candidate_key(adoption.best_tree_arm, adoption.best_tree_penalty),
                       "the best tree arm at its penalty"),
                      (candidate_key(trees_off_of(Link.IDENTITY), None), "the decline target")):
        if key not in adoption.surface_mae:
            raise LayerRefusal("R27", "surface_mae holds every candidate, but not %s (%s)" % (what, key))
    _beside(adoption.beside)
    return adoption


def pin_of(nowcast: Adoption) -> Tuple[ArmSpec, GridPoint]:
    """R29's pin: the nowcast's adopted arm and penalty, or its best tree arm and that arm's penalty
    when the nowcast declined."""
    check_adoption(nowcast)
    if nowcast.declined:
        return nowcast.best_tree_arm, as_point(nowcast.best_tree_penalty)
    return nowcast.adopted, as_point(nowcast.penalty)


def _lead(value: Any, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise LayerRefusal("R29", "%s must be a whole number, got %r" % (what, value))
    value = int(value)
    if value < 1:
        raise LayerRefusal("R29", "%s must be at least 1 (lead 0 is the nowcast: select_adoption and "
                           "lock_adoption), got %d" % (what, value))
    return value


# Provenance: plan 2.4 R29; pm25_adaptation.py:922-923 (pin to the best tree arm when declined);
# Q7 a (lagtrain + guard at every lead); Part 559, F45 (one placebo at the longest lead); D86 (a pinned
# arm that fails the guard adopts the decline target at that lead).
def forecast_adoption(nowcast: Adoption, lead: int, pinned_mae_guard: float, own_trees_off_mae_guard: float,
                      longest_lead: int) -> LeadAdoption:
    """R29: the adoption at one lead, pinned to the nowcast's link, tool, weighting and penalty, with
    the N2 guard run on the inner guard's cut.

    Rule: R29, R27 (N2), G-LOCK (D86). Pin = the nowcast's adopted arm and penalty; if the nowcast
    declined, its best tree arm and that arm's penalty. guard_passed = n2_eligible(pinned MAE, its
    link's trees-off MAE) on this lead's inner guard surface. A pinned arm that fails the guard
    declines to the decline target at this lead (adopted None). placebo_built is True only at the
    longest lead. The result is hashed by vault.lock_lead_adoption before any of this lead's test rows
    is scored; the nowcast band decides HELPS / HURTS at every lead (metrics.single_verdict).
    Returns LeadAdoption.
    Refuses: lead 0 or below; a lead beyond the longest lead; an invalid nowcast adoption; non-finite
    guard MAEs.
    """
    lead_v = _lead(lead, "lead")
    longest = _lead(longest_lead, "longest_lead")
    if lead_v > longest:
        raise LayerRefusal("R29", "lead %d is beyond the longest lead %d" % (lead_v, longest))
    pinned, penalty = pin_of(nowcast)
    passed = n2_eligible(pinned_mae_guard, own_trees_off_mae_guard)
    return LeadAdoption(lead=lead_v, pinned=pinned, penalty=penalty, guard_passed=bool(passed),
                        adopted=pinned if passed else None, placebo_built=lead_v == longest)


def check_lead_adoption(lead_adoption: Any) -> LeadAdoption:
    """Refuse a LeadAdoption forecast_adoption could not have made (lead >= 1; a selectable pinned
    arm; adopted is the pinned arm exactly when the guard passed). Returns it."""
    if not isinstance(lead_adoption, LeadAdoption):
        raise LayerRefusal("G-LOCK", "a lead adoption must be the layer's LeadAdoption, got %s"
                           % type(lead_adoption).__name__)
    _lead(lead_adoption.lead, "LeadAdoption.lead")
    check_arm(lead_adoption.pinned)
    if not lead_adoption.pinned.selectable:
        raise LayerRefusal("R29", "the pinned arm %s is not a tree arm" % arm_name(lead_adoption.pinned))
    as_point(lead_adoption.penalty)
    for what in ("guard_passed", "placebo_built"):
        if not isinstance(getattr(lead_adoption, what), bool):
            raise LayerRefusal("R29", "LeadAdoption.%s must be a bool" % what)
    want = lead_adoption.pinned if lead_adoption.guard_passed else None
    if lead_adoption.adopted != want:
        raise LayerRefusal("R29", "a lead adopts its pinned arm exactly when the guard passes (D86)")
    return lead_adoption


# ---------------------------------------------------------------------------------------------------
# Provenance: plan 5 G-PLUMB (trees-off = normal within the R36 tolerance; the base grid point reproduces
# the un-swept route; shared-Gram solve = reference solver on sample units (route/solve.py); column
# layout per kind; lead 0 = nowcast; weighted arms with equal weights = unweighted arms);
# pm25_forecast.py:484-486; pm25_adaptation.py:838-845 (the contract check).
def check_plumbing(trees_off: np.ndarray, normal: np.ndarray, base_point: np.ndarray, unswept: np.ndarray,
                   weighted_equal: Optional[np.ndarray], unweighted: Optional[np.ndarray],
                   lead0: Optional[np.ndarray], nowcast: Optional[np.ndarray],
                   tolerance: float) -> GuardResult:
    """G-PLUMB: the plumbing identities asserted at runtime.

    Rule: G-PLUMB, R36. Each identity must hold within the tolerance (R36's k x s of the link): trees-off
    equals the normal; the base grid point reproduces the un-swept route; weighted arms with equal
    weights equal unweighted arms; lead 0 equals the nowcast. A pair with both sides None is skipped
    (the first two pairs are always checked). The shared-Gram versus reference-solver check lives in
    route/solve.py.
    Returns GuardResult (BLOCK on any failed identity; details give each pair's largest gap).
    Refuses: shape mismatches; a pair with one side None; non-finite values; a tolerance that is not
    finite and positive.
    """
    tol = _finite_number(tolerance, "the tolerance", "G-PLUMB")
    if not tol > 0:
        raise LayerRefusal("G-PLUMB", "the tolerance must be positive (R36: k x s), got %r" % tol)
    pairs = (("trees_off_equals_normal", trees_off, normal, False),
             ("base_point_reproduces_unswept", base_point, unswept, False),
             ("weighted_equal_weights_equals_unweighted", weighted_equal, unweighted, True),
             ("lead0_equals_nowcast", lead0, nowcast, True))
    details: Dict[str, Any] = {}
    failed = []
    for name, a, b, optional in pairs:
        if a is None and b is None:
            if not optional:
                raise LayerRefusal("G-PLUMB", "%s is always checked; both sides are required" % name)
            details[name] = {"checked": False}
            continue
        if a is None or b is None:
            raise LayerRefusal("G-PLUMB", "%s: one side is missing" % name,
                               fix="pass both arrays, or neither to skip the identity")
        av, bv = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
        if av.shape != bv.shape:
            raise LayerRefusal("G-PLUMB", "%s: shapes %s and %s differ" % (name, av.shape, bv.shape))
        _require_finite(av, "%s (first side)" % name, "G-PLUMB")
        _require_finite(bv, "%s (second side)" % name, "G-PLUMB")
        gap = float(np.max(np.abs(av - bv))) if av.size else 0.0
        ok = gap <= tol
        details[name] = {"checked": True, "rows": int(av.size), "max_abs": gap, "tolerance": tol,
                         "pass": bool(ok)}
        if not ok:
            failed.append(name)
    if failed:
        return GuardResult(rule_id="G-PLUMB", status=GuardStatus.BLOCK, columns=tuple(failed),
                           reason="plumbing identit%s broken beyond the tolerance %.3g: %s"
                                  % ("y" if len(failed) == 1 else "ies", tol, ", ".join(failed)),
                           fix="find the step that changed the numbers; the run stops",
                           part=None, details=details)
    return GuardResult(rule_id="G-PLUMB", status=GuardStatus.PASS, columns=(),
                       reason="every checked plumbing identity holds within %.3g" % tol, fix="",
                       part=None, details=details)


# ---------------------------------------------------------------------------------------------------
# decide(): one decision surface, end to end
@dataclass(frozen=True)
class SurfaceArm:
    """One arm's predictions on the decision surface in y units BEFORE the legal clip (the router's
    link-space output through link_inverse), rows in the surface's row order: (rows, grid points) for a
    tree arm, (rows,) for trees-off."""
    arm: ArmSpec
    pre_clip: np.ndarray


# The construction guard of DecisionSurface: only the label vault issues one (LabelView.decision_surface)
_SURFACE_ISSUING = threading.local()


@contextmanager
def _issuing_surface():
    depth = getattr(_SURFACE_ISSUING, "depth", 0)
    _SURFACE_ISSUING.depth = depth + 1
    try:
        yield
    finally:
        _SURFACE_ISSUING.depth = depth


def surface_sha256(unit_ids: np.ndarray, times: np.ndarray, y: np.ndarray, label_cut: int,
                   test_first_time: int) -> str:
    """The content hash of a decision surface: SHA-256 of the canonical JSON of the hashes of its unit
    ids (as text), times (int64) and labels (float64), and its two cuts. One formula: the vault stamps
    it at issue, decide() re-checks it."""
    return sha256_of_json({"unit_ids": sha256_of_array(np.asarray(unit_ids, dtype=object)),
                           "times": sha256_of_array(np.asarray(times, dtype=np.int64)),
                           "y": sha256_of_array(np.asarray(y, dtype=np.float64)),
                           "label_cut": int(label_cut), "test_first_time": int(test_first_time)})


@dataclass(frozen=True)
class DecisionSurface:
    """The rows decide() scores, issued ONLY by the label vault (LabelView.decision_surface): each row's
    unit and integer step (or day), its label read through the vault's as-of view at label_cut, the
    first step of the test window, and the SHA-256 of that content (surface_sha256). The arrays are
    read-only. A direct construction, or dataclasses.replace, is refused (G-LOCK)."""
    unit_ids: np.ndarray
    times: np.ndarray
    y: np.ndarray
    label_cut: int
    test_first_time: int
    sha256: str

    def __post_init__(self):
        if not getattr(_SURFACE_ISSUING, "depth", 0):
            raise LayerRefusal("G-LOCK", "a DecisionSurface is issued by the label vault only "
                                         "(LabelView.decision_surface); a direct construction, or "
                                         "dataclasses.replace, is refused",
                               fix="ask the run's LabelView for the surface rows' as-of labels")


@dataclass(frozen=True)
class CandidateRow:
    """One scored candidate: an arm at one grid point (level and ratio None for trees-off)."""
    arm: str
    level: Optional[float]
    ratio: Optional[float]
    n: int
    mae: float


@dataclass(frozen=True)
class DecisionRecord:
    """What decide() returns: the adoption, every pick, every candidate row, the clip counts per arm,
    the edge axes of every tree pick, and every arm's CLIPPED row-level predictions on the surface (by
    arm name, rows keyed by unit_ids and times: the caller saves them, predictions and not scores
    alone); with the surface's hash and cuts, the candidate order it was checked against, the arms
    missing from it (GLS only, with the declared reason), the legacy declaration, and the SHA-256 of
    the candidate table. adoption_document(adoption, record) is what the vault locks."""
    adoption: Adoption
    picks: Tuple[PenaltyPick, ...]
    trees_off: Tuple[PenaltyPick, ...]
    trees_off_mae: Mapping[Any, float]
    candidates: Tuple[CandidateRow, ...]
    clip: Mapping[str, ClipCounts]
    edge_axes: Mapping[str, Mapping[str, Optional[str]]]
    legal_range: Tuple[float, float]
    n_rows: int
    grid: Tuple[GridPoint, ...]
    predictions: Mapping[str, np.ndarray]
    unit_ids: np.ndarray
    times: np.ndarray
    surface_sha256: str
    label_cut: int
    guard_cut: int
    test_first_time: int
    candidate_order: Tuple[str, ...]
    missing_arms: Tuple[str, ...]
    gls_absent_reason: Optional[str]
    legacy_reason: Optional[str]
    legacy_link_keys: Tuple[str, ...]
    candidate_table_sha256: str

    def table(self) -> Tuple[Dict[str, Any], ...]:
        """The candidate rows as plain dicts (arm, level, ratio, n, mae)."""
        return tuple({"arm": r.arm, "level": r.level, "ratio": r.ratio, "n": r.n, "mae": r.mae}
                     for r in self.candidates)


def candidate_table_sha256(rows: Sequence[CandidateRow]) -> str:
    """SHA-256 of the candidate table (every row's arm, level, ratio, n and MAE, in order)."""
    return sha256_of_json([{"arm": r.arm, "level": r.level, "ratio": r.ratio, "n": int(r.n),
                            "mae": float(r.mae)} for r in rows])


def _refuse_test_labels(*objects: Any) -> None:
    """G-LOCK: a vault TestLabels object never reaches decide()."""
    from treeroute.labels.vault import TestLabels   # at call time: the vault imports this module

    for obj in objects:
        if isinstance(obj, TestLabels):
            raise LayerRefusal("G-LOCK", "decide() received test-window labels (a TestLabels object); the "
                               "decision surface never sees a test row",
                               fix="build the surface with LabelView.decision_surface over the inner "
                                   "score rows")


def _int_value(x: Any, what: str) -> int:
    if isinstance(x, bool) or not isinstance(x, Integral):
        raise LayerRefusal("G-LOCK", "%s must be a whole step (or day), got %r" % (what, x))
    return int(x)


def _issuer_of(surface: "DecisionSurface") -> Any:
    ref = getattr(surface, "_issuer", None)
    vault = ref() if callable(ref) else None
    if vault is None or not callable(getattr(vault, "_issued_surface", None)) \
            or not vault._issued_surface(surface.sha256):
        raise LayerRefusal("G-LOCK", "this decision surface was not issued by a live label vault "
                                     "(LabelView.decision_surface)",
                           fix="issue the surface from the run's LabelView")
    return vault


def _check_surface(surface: Any) -> Tuple[np.ndarray, np.ndarray, Any]:
    if not isinstance(surface, DecisionSurface):
        raise LayerRefusal("G-LOCK", "decide() takes a DecisionSurface, got %s" % type(surface).__name__)
    _refuse_test_labels(surface.y, surface.times, surface.unit_ids)
    vault = _issuer_of(surface)
    t = np.asarray(surface.times)
    if t.ndim != 1 or (t.size and t.dtype.kind not in "iu"):
        raise LayerRefusal("G-LOCK", "surface times must be a 1-D integer array")
    y = _vector(surface.y, "the surface labels", "R26")
    units = np.asarray(surface.unit_ids)
    if y.shape != t.shape or units.shape != t.shape:
        raise LayerRefusal("R26", "the surface has %d unit ids, %d times and %d labels"
                           % (units.size, t.size, y.size))
    if y.size == 0:
        raise LayerRefusal("R26", "the decision surface has no row")
    cut = _int_value(surface.label_cut, "the surface's label cut")
    first = _int_value(surface.test_first_time, "the first step of the test window")
    if surface_sha256(units, t, y, cut, first) != surface.sha256:
        raise LayerRefusal("G-LOCK", "the surface's rows or labels differ from what the vault issued "
                                     "(SHA-256 mismatch)", fix="use the surface exactly as issued")
    _require_finite(y, "the surface labels", "R26")
    if cut >= first:
        raise LayerRefusal("G-LOCK", "the surface labels come from an as-of view at %d, inside the test "
                           "window (first step %d)" % (cut, first))
    late = int(np.count_nonzero(t >= first))
    if late:
        raise LayerRefusal("G-LOCK", "%d surface row(s) lie in the test window (first step %d, latest "
                           "row %d); decide() never receives a test row" % (late, first, int(t.max())),
                           fix="the decision surface is the inner score window (or held-out donor "
                               "folds), never the test window")
    after = int(np.count_nonzero(t > cut))
    if after:
        raise LayerRefusal("G-LOCK", "%d surface row(s) are dated after the label view's cut %d; their "
                           "labels were not read through that view" % (after, cut))
    return t, y, vault


def _check_guard(guard_ctx: Any, surface: DecisionSurface, times: np.ndarray, vault: Any,
                 legacy: Optional[LegacyCandidates]) -> Tuple[int, int]:
    """G-FITCUT on the decision surface: guard_ctx is the nowcast's GUARD FitContext; every surface row
    is issued at or after its cut (the inner guard's cut, check_inner_score_rows); the labels were read
    at or before the lead's fit cut; the surface and the context read the same vault (a declared legacy
    replay may keep two). Returns (guard cut, fit cut)."""
    from treeroute.fit.context import FitContext   # at call time: fit.context imports the vault

    if not isinstance(guard_ctx, FitContext):
        raise LayerRefusal("G-FITCUT", "decide() takes the nowcast's GUARD FitContext, got %s"
                           % type(guard_ctx).__name__)
    if guard_ctx.lead != 0 or guard_ctx.cut_kind is not CutKind.GUARD:
        raise LayerRefusal("G-FITCUT", "decide() is the nowcast's decision: its context is lead 0's GUARD "
                           "context, got lead %d, %s" % (guard_ctx.lead, guard_ctx.cut_kind.value),
                           fix="FitContext(..., lead=0, cut_kind=CutKind.GUARD)")
    guard_ctx.check_inner_score_rows(times)
    fit_cut = int(guard_ctx.cut_pair().fit_cut)
    if int(surface.label_cut) > fit_cut:
        raise LayerRefusal("G-FITCUT", "the surface labels were read at %d, after lead 0's fit cut %d"
                           % (int(surface.label_cut), fit_cut))
    if guard_ctx._labels is not vault and legacy is None:
        raise LayerRefusal("G-LOCK", "the decision surface and the guard context read different label "
                                     "vaults; a run has one vault")
    return int(guard_ctx.cut), fit_cut


def _r22_of(guard_ctx: Any, legal: Tuple[float, float]) -> Tuple[Link, ...]:
    """R22's link set from the guard context's derived.json; the legal range must be R22's."""
    derived = guard_ctx.derived
    entry = derived.get("R22") if isinstance(derived, Mapping) else None
    if entry is None:
        raise LayerRefusal("R22", "derived.json has no R22 entry: the decision needs the run's link set",
                           fix="run plan (derive_all) first; a legacy replay declares LegacyCandidates")
    links = tuple(getattr(entry, "value", ()))
    if not links or not all(is_r22_link(x) for x in links):
        raise LayerRefusal("R22", "derived.json's R22 value is not a set of R22 links: %r" % (links,))
    recorded = dict(getattr(entry, "inputs", {}) or {}).get("legal_range")
    if recorded is not None:
        low, high = (float(recorded[0]), float(recorded[1]))
        if (low, high) != (float(legal[0]), float(legal[1])):
            raise LayerRefusal("R28", "the legal range [%r, %r] differs from the one R22 recorded [%r, %r]"
                               % (legal[0], legal[1], low, high), fix="pass the target's legal range")
    return links


def _check_arms(arms: Sequence[Any], expected: Tuple[ArmSpec, ...], gls_absent_reason: Optional[str],
                legacy: Optional[LegacyCandidates]) -> Tuple[Dict[str, "SurfaceArm"], Tuple[ArmSpec, ...]]:
    """Every surface arm is a candidate of the decision; every candidate is on the surface, except GLS
    arms under an explicit reason. Returns ({name: SurfaceArm}, missing arms)."""
    if not arms:
        raise LayerRefusal("R27", "no arm on the decision surface")
    given: Dict[str, SurfaceArm] = {}
    for i, sa in enumerate(arms):
        if not isinstance(sa, SurfaceArm):
            raise LayerRefusal("R27", "arm %d must be a SurfaceArm, got %s" % (i, type(sa).__name__))
        _refuse_test_labels(sa.pre_clip)
        check_arm(sa.arm)
        if sa.arm.tool is Tool.PLACEBO_CORRECTOR:
            raise LayerRefusal("R24", "the placebo %s is never on the decision surface (built once at the "
                               "test pass, never selectable)" % arm_name(sa.arm))
        name = arm_name(sa.arm)
        if name in given:
            raise LayerRefusal("R27", "an arm is on the surface twice")
        given[name] = sa
    names = [arm_name(a) for a in expected]
    extra = sorted(n for n in given if n not in names)
    if extra:
        raise LayerRefusal("R24", "arm(s) %s are not candidates of this decision (%s)"
                           % (extra, "the declared legacy list" if legacy else "candidate_arms of R22's "
                              "link set"))
    missing = tuple(a for a in expected if arm_name(a) not in given)
    gls_missing = tuple(a for a in missing if a.selectable and a.weighting is Weighting.GLS)
    other = [arm_name(a) for a in missing if a not in gls_missing]
    if gls_absent_reason is not None:
        if not isinstance(gls_absent_reason, str) or not gls_absent_reason.strip():
            raise LayerRefusal("R25", "gls_absent_reason must be a non-empty reason")
        if not gls_missing:
            raise LayerRefusal("R25", "gls_absent_reason is given but every GLS arm is on the surface")
    if other or (gls_missing and gls_absent_reason is None):
        raise LayerRefusal("R24", "the decision surface lacks candidate arm(s) %s; R27 ranks the "
                           "penalty_search result of EVERY selectable arm, with each link's trees-off"
                           % ([arm_name(a) for a in missing],),
                           fix=("route every arm of candidate_arms(links)" + (
                               "; while no weighted solve exists, declare gls_absent_reason (written "
                               "into the locked adoption)" if gls_missing and not other else "")))
    return given, missing


def decide(surface: DecisionSurface, arms: Sequence[SurfaceArm], grid: Sequence[GridPoint],
           legal_range: Tuple[float, float], guard_ctx: Any, *,
           legacy: Optional[LegacyCandidates] = None,
           gls_absent_reason: Optional[str] = None) -> DecisionRecord:
    """R26-R28 on one decision surface: clip every arm (R28), search every tree arm's grid (R26),
    score each link's trees-off, run the N2 guard and the MAE adoption with the decline rule (R27),
    and print predict-zero and corr2 beside.

    Rule: R24, R26, R27, R28, G-CLIP, G-LOCK, G-FITCUT. surface: issued by the label vault
    (LabelView.decision_surface). guard_ctx: the nowcast's GUARD FitContext (G-FITCUT: every surface row
    issued at or after its cut; the labels at or before the fit cut). The candidates are
    candidate_arms(derived.json's R22 link set) without placebos, or a declared legacy list (keyword
    legacy, harness replays only); the surface must carry every one of them, in any order (decide()
    ranks them in candidate order: the tie order), except the GLS arms under an explicit
    gls_absent_reason (recorded). The clip uses the target's legal range (R22's recorded range when
    not legacy); the counts behind the pre-clip rate are kept per arm. predict-zero (zero clipped to
    the legal range) and corr2 per arm at its pick go in Adoption.beside, printed and never used. The
    adoption document (adoption_document(adoption, record)) is registered with the surface's vault,
    which lock_adoption then locks.
    Returns DecisionRecord (its predictions hold every arm's clipped surface, rows keyed by unit_ids
    and times, for the run folder).
    Refuses: a surface the vault did not issue, or whose content changed; a test row, a label read
    after its view's cut, or a TestLabels object (G-LOCK); a context that is not lead 0's GUARD
    context, a surface row issued before its cut, labels read after the fit cut (G-FITCUT); a
    derived.json without R22, or a legal range other than R22's; a placebo arm; an arm that is not a
    candidate; a missing candidate (other than GLS arms under a reason); a stale gls_absent_reason; a
    repeated arm; anything clip_with_counts, penalty_search or select_adoption refuses.
    """
    t, y, vault = _check_surface(surface)
    guard_cut, _ = _check_guard(guard_ctx, surface, t, vault, legacy)
    low, high = legal_range_of(legal_range)
    links = None if legacy is not None else _r22_of(guard_ctx, (low, high))
    expected = decision_candidates(links, legacy)
    arms = tuple(arms)
    _refuse_test_labels(*arms)
    given, missing = _check_arms(arms, expected, gls_absent_reason, legacy)
    ordered = [given[arm_name(a)] for a in expected if arm_name(a) in given]
    tree = [sa for sa in ordered if sa.arm.tool in SELECTABLE_TOOLS]
    offs = [sa for sa in ordered if sa.arm.tool is Tool.TREES_OFF]
    if not tree:
        raise LayerRefusal("R27", "no tree arm on the decision surface")
    points = _grid(grid)
    clip: Dict[str, ClipCounts] = {}
    clipped: Dict[str, np.ndarray] = {}
    for sa in ordered:
        name = arm_name(sa.arm)
        values, counts = clip_with_counts(sa.pre_clip, (low, high), allow_nan=False)
        clip[name] = counts
        clipped[name] = values
    picks = tuple(penalty_search(sa.arm, clipped[arm_name(sa.arm)], y, points) for sa in tree)
    off_picks = tuple(penalty_search(sa.arm, clipped[arm_name(sa.arm)], y, ()) for sa in offs)
    trees_off_mae = {p.arm.link: p.mae for p in off_picks}
    zero, _ = clip_with_counts(np.zeros(y.size), (low, high), allow_nan=False)
    beside: Dict[str, float] = {"predict_zero_mae": surface_mae(y, zero)}
    for p in picks:
        k = list(p.mae_by_point).index(p.point)
        beside["corr2:" + arm_name(p.arm)] = surface_corr2(y, clipped[arm_name(p.arm)][:, k])
    for p in off_picks:
        values = clipped[arm_name(p.arm)]
        beside["corr2:" + arm_name(p.arm)] = surface_corr2(y, values.reshape(-1))
    adoption = select_adoption(picks, trees_off_mae, beside, order=legacy)
    rows: List[CandidateRow] = []
    for p in picks:
        for point, mae in p.mae_by_point.items():
            rows.append(CandidateRow(arm=arm_name(p.arm), level=point.level, ratio=point.ratio,
                                     n=int(y.size), mae=float(mae)))
    for p in off_picks:
        rows.append(CandidateRow(arm=arm_name(p.arm), level=None, ratio=None, n=int(y.size),
                                 mae=float(p.mae)))
    axes = {arm_name(p.arm): edge_axes(p.point, points) for p in picks}
    for values in clipped.values():
        values.setflags(write=False)
    unit_ids = np.array(surface.unit_ids, dtype=object, copy=True)
    times = np.array(t, dtype=np.int64, copy=True)
    for arr in (unit_ids, times):
        arr.setflags(write=False)
    record = DecisionRecord(
        adoption=adoption, picks=picks, trees_off=off_picks, trees_off_mae=trees_off_mae,
        candidates=tuple(rows), clip=clip, edge_axes=axes, legal_range=(low, high), n_rows=int(y.size),
        grid=points, predictions=clipped, unit_ids=unit_ids, times=times,
        surface_sha256=str(surface.sha256), label_cut=int(surface.label_cut), guard_cut=guard_cut,
        test_first_time=int(surface.test_first_time),
        candidate_order=tuple(arm_name(a) for a in expected),
        missing_arms=tuple(arm_name(a) for a in missing),
        gls_absent_reason=None if gls_absent_reason is None else str(gls_absent_reason),
        legacy_reason=None if legacy is None else legacy.reason,
        legacy_link_keys=() if legacy is None else legacy.link_keys(),
        candidate_table_sha256=candidate_table_sha256(rows))
    vault._register_decision(adoption_document(adoption, record))
    for line in decision_lines(record):
        print(line)
    return record


def decision_lines(record: DecisionRecord) -> Tuple[str, ...]:
    """The lines decide() prints: per arm its best MAE, pick, edge axes, pre-clip rate and corr2
    (beside); predict-zero; missing arms and the legacy declaration; the adoption."""
    out = ["decision surface: %d rows, %d candidates, legal range [%r, %r], surface SHA-256 %s"
           % (record.n_rows, len(record.candidates), record.legal_range[0], record.legal_range[1],
              record.surface_sha256[:16])]
    beside = record.adoption.beside
    for p in record.picks + record.trees_off:
        name = arm_name(p.arm)
        cc = record.clip[name]
        where = "no grid" if p.point is None else "level %r ratio %r" % (p.point.level, p.point.ratio)
        axes = record.edge_axes.get(name, {})
        edge = [a for a in ("level", "ratio") if axes.get(a)]
        out.append("  %-34s MAE %.6f at %s%s | pre-clip %d below, %d above of %d | corr2 %.4f (beside)"
                   % (name, p.mae, where,
                      (" | EDGE PICK: %s" % ", ".join("%s %s" % (a, axes[a]) for a in edge)) if edge else "",
                      cc.n_below, cc.n_above, cc.n_finite, beside.get("corr2:" + name, float("nan"))))
    out.append("  predict-zero MAE %.6f (beside, never used)" % beside["predict_zero_mae"])
    if record.missing_arms:
        out.append("  MISSING ARMS (not ranked): %s -- declared: %s"
                   % (", ".join(record.missing_arms), record.gls_absent_reason))
    if record.legacy_reason is not None:
        out.append("  LEGACY candidate list (link keys %s): %s"
                   % (", ".join(record.legacy_link_keys), record.legacy_reason))
    a = record.adoption
    if a.declined:
        out.append("  => DECLINED: no tree arm beat its own link's trees-off; the decline target is the "
                   "identity-link trees-off; best tree arm %s at level %r ratio %r"
                   % (arm_name(a.best_tree_arm), a.best_tree_penalty.level, a.best_tree_penalty.ratio))
    else:
        out.append("  => ADOPTED %s at level %r ratio %r (%d of %d tree arms eligible)"
                   % (arm_name(a.adopted), a.penalty.level, a.penalty.ratio, len(a.eligible),
                      len(record.picks)))
    return tuple(out)


# ---------------------------------------------------------------------------------------------------
# JSON documents of the adoption records (hashed and locked by labels/vault.py)
def _arm_doc(arm: Optional[ArmSpec]) -> Optional[Dict[str, Any]]:
    if arm is None:
        return None
    check_arm(arm)
    return {"link": link_value(arm.link), "tool": arm.tool.value, "weighting": arm.weighting.value,
            "selectable": bool(arm.selectable)}


def _point_doc(point: Any) -> Optional[Dict[str, Any]]:
    if point is None:
        return None
    p = as_point(point)
    return {"level": p.level, "ratio": p.ratio}


def _number_doc(x: float) -> Optional[float]:
    x = float(x)
    return x if math.isfinite(x) else None


def _bound_doc(x: float) -> Any:
    """A legal-range bound in strict JSON: the number, or 'inf' / '-inf'."""
    x = float(x)
    if math.isfinite(x):
        return x
    return "inf" if x > 0 else "-inf"


def decision_section(record: DecisionRecord) -> Dict[str, Any]:
    """The 'decision' section of adoption.json: the surface's hash, rows, units and cuts, the legal
    range and grid, the candidate order checked, the arms missing (with the declared reason), the
    legacy declaration, and the candidate table's hash and size."""
    if not isinstance(record, DecisionRecord):
        raise LayerRefusal("G-LOCK", "the decision section comes from decide()'s DecisionRecord, got %s"
                           % type(record).__name__)
    return {"surface_sha256": record.surface_sha256, "n_rows": int(record.n_rows),
            "n_units": int(len(set(np.asarray(record.unit_ids).tolist()))),
            "label_cut": int(record.label_cut), "guard_cut": int(record.guard_cut),
            "test_first_time": int(record.test_first_time),
            "legal_range": [_bound_doc(record.legal_range[0]), _bound_doc(record.legal_range[1])],
            "grid": [_point_doc(p) for p in record.grid],
            "candidate_order": list(record.candidate_order), "missing_arms": list(record.missing_arms),
            "gls_absent_reason": record.gls_absent_reason,
            "legacy": None if record.legacy_reason is None else {
                "reason": record.legacy_reason, "link_keys": list(record.legacy_link_keys)},
            "candidate_table_sha256": record.candidate_table_sha256,
            "n_candidates": int(len(record.candidates))}


def adoption_document(adoption: Adoption, decision: Optional[DecisionRecord] = None) -> Dict[str, Any]:
    """The JSON content of adoption.json: every field of Adoption (surface_mae holds every candidate; a
    non-finite beside value is written null) and, with decide()'s record, its decision section (the
    record's adoption must be this adoption). Checked with check_adoption first."""
    check_adoption(adoption)
    doc = {"pass": "nowcast", "lead": 0,
           "adopted": _arm_doc(adoption.adopted), "penalty": _point_doc(adoption.penalty),
           "declined": bool(adoption.declined),
           "best_tree_arm": _arm_doc(adoption.best_tree_arm),
           "best_tree_penalty": _point_doc(adoption.best_tree_penalty),
           "eligible": [_arm_doc(a) for a in adoption.eligible],
           "surface_mae": {k: float(v) for k, v in adoption.surface_mae.items()},
           "beside": {k: _number_doc(v) for k, v in adoption.beside.items()}}
    if decision is not None:
        section = decision_section(decision)
        if decision.adoption is not adoption and adoption_document(decision.adoption) != doc:
            raise LayerRefusal("G-LOCK", "the decision record belongs to another adoption")
        doc["decision"] = section
    return doc


def lead_adoption_document(lead_adoption: LeadAdoption, nowcast_sha256: str) -> Dict[str, Any]:
    """The JSON content of one lead's adoption file, naming the nowcast adoption's hash."""
    check_lead_adoption(lead_adoption)
    return {"pass": "lead", "lead": int(lead_adoption.lead), "nowcast_sha256": str(nowcast_sha256),
            "pinned": _arm_doc(lead_adoption.pinned), "penalty": _point_doc(lead_adoption.penalty),
            "guard_passed": bool(lead_adoption.guard_passed),
            "adopted": _arm_doc(lead_adoption.adopted),
            "placebo_built": bool(lead_adoption.placebo_built)}


__all__ = ["GuardStatus", "GuardResult", "PenaltyPick", "Adoption", "LeadAdoption", "surface_mae",
           "surface_corr2", "as_point", "edge_axes", "candidate_key", "penalty_search", "n2_eligible",
           "select_adoption", "check_adoption", "pin_of", "forecast_adoption", "check_lead_adoption",
           "check_plumbing", "SurfaceArm", "DecisionSurface", "surface_sha256", "CandidateRow",
           "DecisionRecord", "candidate_table_sha256", "decide", "decision_lines", "decision_section",
           "adoption_document", "lead_adoption_document"]
