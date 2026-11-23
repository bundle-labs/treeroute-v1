"""The router rules of plan 2.2 and the history block's spec (2.3): R12 router kind (with its valid-row
counter and the constant-history share), R13 decision surface under leave one region out, R14 router
design, R17 own-history spec.

SCIENCE bodies for the owner-approved signatures of the proposed derive_rules module and, for R13, the
LORO additions (derive_r13_surface_loro supersedes derive_r13_decision_surface), with the decisions of
SIGNATURES_FOR_REVIEW.md (proposed defaults accepted: D9, D10, D11, D12) and the owner rulings file,
which wins where it differs (sections D and E: leave one region out). Each rule is a pure function: it
reads its arguments only, writes nothing, draws nothing, and returns a Derived.

Under leave one region out every group is tested, so R12's h is the median over the candidate units of
EVERY group (D9 restated), and R13's neighbour surface is one fold per group from one inner-cut bank.

Readings flagged for the owner (no code path hides them):
  - R14 per-unit and region designs list the intercept among the unpenalised blocks, as the router
    (route/kinds.py per_unit_router_design) builds them; the plan cell names only the normal.
  - R17 needs the target's STAMP as well as its window to measure the reach past the step, and the
    approved signature passes the window only: the argument target_window takes the target's facts
    (window and stamp), and a bare window is refused.
  - R17 for events (trailing means in days) and the whole neighbour track are milestone M8; R17 raises
    NotImplementedError for events.
"""
# Provenance for the module: plan 2.2 R12-R14, 2.3 R17; C5, C8, C10, C12; pm25_adaptation.py:143
# (MIN_HIST = 24), :176-177 (LEVELS, RATIOS); fire_architecture.py:102-103 (ALPHA 0.5, A_CTX 0.25);
# adaptation.py:1213-1214 (REGROWS 60000, LAM 100), :1434 (the neighbour grid); pm25_forecast.py:122-159
# (the own-history columns); owner rulings D, E (leave one region out), R-D b (the history block starts
# one more step back when the target window reaches past its step), F8.

from typing import Any, List, Mapping, Tuple

import numpy as np

from treeroute import engine_constants as K
from treeroute import timing
from treeroute.io.apply import history_column_names
from treeroute.io import steps as _steps

from .derived import (DeriveRefusal, borderline_flags, constants_used, make_derived, sha256_of_array,
                      sha256_of_json)
from .rules import _int, _value
from .shapes import Derived, GridPoint, HistorySpec, LoroSurfaceKind, RouterDesign, RouterKind

INTERCEPT, NORMAL, CONTEXT, TREES = "intercept", "normal", "context", "trees"
PER_UNIT, REGION, NEIGHBOUR = (RouterKind.PER_UNIT.value, RouterKind.REGION.value,
                               RouterKind.NEIGHBOUR.value)
EVENT_MONTH = "event_month"
_SHOW = 5


def _kind(kind: Any, rule: str) -> RouterKind:
    try:
        return RouterKind(_value(kind))
    except ValueError:
        raise DeriveRefusal(rule, "unknown router kind %r" % (kind,), fix="pass R12's outcome")


def _names(values: Any, what: str, rule: str, allow_empty: bool = True) -> Tuple[str, ...]:
    if isinstance(values, str) or not isinstance(values, (tuple, list)):
        raise DeriveRefusal(rule, "%s must be a tuple of names, got %r" % (what, values),
                            fix="pass a tuple of names")
    out = tuple(values)
    if any(not isinstance(v, str) or not v for v in out):
        raise DeriveRefusal(rule, "%s must hold non-empty names" % what, fix="pass names")
    if len(set(out)) != len(out):
        raise DeriveRefusal(rule, "%s names an entry twice" % what, fix="pass each name once")
    if not out and not allow_empty:
        raise DeriveRefusal(rule, "%s is empty" % what, fix="pass at least one name")
    return out


# ===================================================================================================
# R12 router kind
# Provenance: plan 2.1 R12 and R18 (valid rows only; test-window rows never read; for events, the
# unit's valid visits in the window).
def count_valid_rows_per_unit(unit_ids: np.ndarray, steps: np.ndarray, label_is_valid: np.ndarray,
                              first_step: int, last_step: int) -> Mapping[str, int]:
    """Number of VALID target rows per unit inside [first_step, last_step].

    Rule: R12, R18. NaN labels do not count (the caller passes validity only, never a value). Rows
    outside the window are not counted (the caller passes Y0 to the inner-fit end, so test-window rows
    are never read). Every unit present in unit_ids gets an entry, 0 when none of its rows is a valid
    row inside the window. Steps are integer steps (grids) or Day ordinals (events: the unit's valid
    visits in the window).
    Returns {unit id: valid row count}, sorted by unit id.
    Refuses: mismatched array lengths; validity that is not boolean; steps that are not whole numbers;
    first_step > last_step; a unit id that is not a non-empty string.
    """
    rule = "R12"
    units = np.asarray(unit_ids, dtype=object)
    t = _steps.as_int_array(steps, "steps", rule)
    ok = np.asarray(label_is_valid)
    if not (units.ndim == ok.ndim == 1) or not (len(units) == len(t) == len(ok)):
        raise DeriveRefusal(rule, "unit ids, steps and validity have lengths %d, %d, %d"
                            % (len(units), len(t), len(ok)), fix="pass one entry per target row")
    if ok.dtype.kind != "b":
        raise DeriveRefusal(rule, "validity must be boolean, got dtype %s" % ok.dtype,
                            fix="pass validity flags, never label values")
    first, last = _int(first_step, "first_step", rule), _int(last_step, "last_step", rule)
    if first > last:
        raise DeriveRefusal(rule, "the window [%d, %d] is empty" % (first, last),
                            fix="pass first_step <= last_step")
    names, codes = np.unique(units, return_inverse=True)
    bad = [u for u in names[:len(names)] if not isinstance(u, str) or not u]
    if bad:
        raise DeriveRefusal(rule, "unit ids must be non-empty strings, got %r" % (bad[:_SHOW],),
                            fix="pass the unit ids")
    inside = ok & (t >= first) & (t <= last)
    counts = np.bincount(codes[inside], minlength=len(names))
    return {str(u): int(n) for u, n in zip(names.tolist(), counts.tolist())}


# Provenance: plan 2.1 R12 ("The share of units whose whole fit history is one value is printed").
def constant_history_share(unit_ids: np.ndarray, y_fit_rows: np.ndarray) -> float:
    """Share of units whose whole fit history is one value (report only).

    Rule: R12. Printed in plan and in reports; it never changes a setting. The rows are the fit rows of
    the units the caller names (under leave one region out, every group's scored units: valid labels
    at or before the inner-fit end, from the plan-time label view); a unit whose rows all hold the same
    value counts as constant.
    Returns the share in [0, 1].
    Refuses: no rows; mismatched lengths; a non-finite label (fit rows hold valid labels only).
    """
    rule = "R12"
    units = np.asarray(unit_ids, dtype=object)
    y = np.asarray(y_fit_rows)
    if units.ndim != 1 or y.ndim != 1 or len(units) != len(y):
        raise DeriveRefusal(rule, "unit ids and labels have shapes %s and %s" % (units.shape, y.shape),
                            fix="pass one unit id per fit row")
    if len(y) == 0:
        raise DeriveRefusal(rule, "no fit row: the constant-history share is undefined",
                            fix="pass the fit rows of the units")
    if y.dtype.kind not in "iuf" or (y.dtype.kind == "f" and not np.isfinite(y).all()):
        raise DeriveRefusal(rule, "fit-row labels must be finite numbers",
                            fix="pass valid labels only")
    _, codes = np.unique(units, return_inverse=True)
    order = np.lexsort((y, codes))
    c, v = codes[order], y[order]
    first = np.r_[True, c[1:] != c[:-1]]
    new_value = np.r_[True, (c[1:] != c[:-1]) | (v[1:] != v[:-1])]
    distinct = np.add.reduceat(new_value.astype(np.int64), np.flatnonzero(first))
    return float(np.mean(distinct == 1))


# Provenance: plan 2.1 R12; C5 (MIN_HIST = 24 at pm25_adaptation.py:143); C10 (the 5% fallback flag);
# D9 (h over ALL candidate units before the pick; under LORO every group's, SIGNATURES_LORO_ADDENDUM.md
# "same signature, changed contract"); D10 (numpy median, so h may be a half-integer). Replaces the
# donor-wide mean fallback at pm25_adaptation.py:342-344.
def derive_r12_router_kind(valid_rows_per_test_unit: Mapping[str, int]) -> Derived:
    """Router kind by one rule: per-unit if h >= 24, region if 2 <= h < 24, neighbour if h < 2.

    Rule: R12 (C5, C10, D9, D10). h = the median number of VALID target rows per unit from Y0 to the
    inner-fit end, over the units given: under leave one region out, every candidate unit of EVERY
    group (R18 candidates, before the pick, because the pick size depends on the kind; the argument
    keeps its approved name). The median is numpy's (the midpoint of an even count, D10). PER-UNIT if
    h >= C5.per_unit_min_valid_rows; REGION if C5.region_min_valid_rows <= h < that; NEIGHBOUR below.
    In a per-unit outcome a unit with fewer than C5.per_unit_min_valid_rows valid rows uses its group's
    region router (route.kinds.fallback_units at run time): here those units are counted over the
    given units and flagged 'fallback_share_above:C10.fallback_flag_share' when their share is above
    C10's (report only).
    Returns Derived[RouterKind]; inputs record h, the unit count, the fallback count and share and the
    count distribution; margins: h against both C5 thresholds (borderline within 20%).
    Refuses: an empty unit map; a unit id that is not a non-empty string; a count that is not a whole
    number >= 0.
    """
    rule = "R12"
    if not isinstance(valid_rows_per_test_unit, Mapping) or not valid_rows_per_test_unit:
        raise DeriveRefusal(rule, "the unit map is empty: h is undefined",
                            fix="pass the valid rows of every candidate unit (count_valid_rows_per_unit)")
    units = sorted(valid_rows_per_test_unit)
    if any(not isinstance(u, str) or not u for u in units):
        raise DeriveRefusal(rule, "unit ids must be non-empty strings", fix="pass the unit ids")
    counts = np.array([_int(valid_rows_per_test_unit[u], "the valid rows of %s" % u, rule)
                       for u in units], dtype=np.int64)
    if (counts < 0).any():
        raise DeriveRefusal(rule, "a valid-row count is negative", fix="pass row counts")
    h = float(np.median(counts))
    per_unit_min, region_min = K.PER_UNIT_MIN_VALID_ROWS, K.REGION_MIN_VALID_ROWS
    if h >= per_unit_min:
        kind = RouterKind.PER_UNIT
    elif h >= region_min:
        kind = RouterKind.REGION
    else:
        kind = RouterKind.NEIGHBOUR
    short = int((counts < per_unit_min).sum())
    share = short / float(len(counts))
    flags: List[str] = []
    if kind == RouterKind.PER_UNIT and share > K.FALLBACK_FLAG_SHARE:
        flags.append("fallback_share_above:C10.fallback_flag_share")
    margins, more = borderline_flags(h, {"C5.per_unit_min_valid_rows": per_unit_min,
                                         "C5.region_min_valid_rows": region_min})
    quantiles = np.percentile(counts, [0, 25, 50, 75, 100])
    inputs = {"h": h, "median_method": "numpy median (midpoint of an even count, D10)",
              "units": len(units), "units_scope": "every candidate unit of every group (D9, LORO)",
              "fallback_units": short if kind == RouterKind.PER_UNIT else None,
              "fallback_share": share if kind == RouterKind.PER_UNIT else None,
              "count_quantiles": {"min": float(quantiles[0]), "q25": float(quantiles[1]),
                                  "median": float(quantiles[2]), "q75": float(quantiles[3]),
                                  "max": float(quantiles[4])},
              "constants": constants_used("C5.per_unit_min_valid_rows", "C5.region_min_valid_rows",
                                          "C10.fallback_flag_share")}
    hashes = {"valid_rows_per_unit": sha256_of_json([sha256_of_array(np.asarray(units, dtype=object)),
                                                     sha256_of_array(counts)])}
    return make_derived(rule, kind, inputs, hashes, margins, tuple(flags) + more)


# ===================================================================================================
# R13 decision surface
# Provenance: plan 2.1 R13 (LORO: neighbour folds become leave-one-group-out from one bank cut at the
# inner-fit end; fold g drops g's block's trees); C8 (restated for LORO in engine_constants.py);
# derive_r13_surface_loro supersedes derive_r13_decision_surface (SIGNATURES_LORO_ADDENDUM.md).
def derive_r13_surface_loro(kind: Any, groups: Tuple[str, ...]) -> Derived:
    """Decision surface under LORO: the inner window (per-unit, region) or leave-one-group-out folds
    (neighbour).

    Rule: R13, C8. Per-unit and region: the inner window, unchanged; their routers drop their own
    block's trees there too (R14). Neighbour: one fold per group, in sorted order; one extra bank cut
    at the inner-fit end serves every fold, and fold g drops the trees of group g's overlap block and,
    by the pool default, of every group present in each row's pool (the drop itself is the neighbour
    router's, milestone M8). Fold g's scored rows are group g's rows in the inner score years.
    Returns Derived[(surface kind, one single-group tuple per fold)] (an empty fold tuple for the
    inner window).
    Refuses: an unknown kind; groups that are not distinct non-empty names; a neighbour kind with
    fewer than C15.min_groups groups (G-SUPPORT refuses earlier).
    """
    rule = "R13"
    k = _kind(kind, rule)
    names = tuple(sorted(_names(groups, "groups", rule, allow_empty=False)))
    if k == RouterKind.NEIGHBOUR:
        if len(names) < K.MIN_GROUPS:
            raise DeriveRefusal(rule, "leave-one-group-out folds need at least %d groups, got %d"
                                % (K.MIN_GROUPS, len(names)),
                                fix="G-SUPPORT refuses a package with fewer groups")
        value = (LoroSurfaceKind.LEAVE_ONE_GROUP_OUT, tuple((g,) for g in names))
    else:
        value = (LoroSurfaceKind.INNER_WINDOW, ())
    inputs = {"kind": k.value, "groups": list(names),
              "constants": constants_used("C8.neighbour_folds_leave_one_group_out", "C15.min_groups")}
    return make_derived(rule, value, inputs)


# ===================================================================================================
# R14 router design
def _grid(levels: Tuple[float, ...], ratios: Any) -> Tuple[GridPoint, ...]:
    """Level-major grid (every level, then every ratio within it), or the levels alone."""
    lv = tuple(float(v) for v in levels)
    if ratios is None:
        return tuple(GridPoint(level, None) for level in lv)
    return tuple(GridPoint(level, float(r)) for level in lv for r in ratios)


# Provenance: plan 2.2 R14; C7, C12; D11 (the source level values 0.1-100 on every grid, the region's
# included); per-unit grid pm25_adaptation.py:176-177 (origin fire_architecture.py:102-103); region
# lambda 100 and cap 60,000 at adaptation.py:1213-1214; neighbour centre adaptation.py:1434; the router's
# own layout route/kinds.py per_unit_router_design (intercept and normal unpenalised).
def derive_r14_router_design(kind: Any, context_columns: Tuple[str, ...]) -> Derived:
    """The router's column layout, unpenalised columns, penalty grid and fit-row cap.

    Rule: R14 (C7, C12, D11). Per-unit: intercept, normal, context (level x ratio), trees (level);
    intercept and normal unpenalised; C12.penalty_levels x C12.penalty_ratios around trees 0.5 /
    context 0.25, level-major (35 points); without declared context the context block goes and the
    grid collapses to the 7 levels. Region: intercept, normal (unpenalised, U-1), trees (trace-
    normalised ridge); C12.region_penalty_levels around lambda C12.region_lambda_centre; fit rows
    capped at C7.region_router_row_budget by keeping whole units (split.region_cap_units); declared
    context is unused and flagged 'context_unused'. Neighbour: intercept, context, trees (intercept
    unpenalised) on the per-unit grid around the neighbour centres. Under leave one region out every
    kind's tree block drops the router's own overlap block (a column mask at run time, R14; not a
    design field). The base point (level 1, ratio = context centre / trees centre) reproduces the
    un-swept route (G-PLUMB) and is recorded; it must be a grid point.
    Returns Derived[RouterDesign]; inputs record the context columns, the base point and the
    constants.
    Refuses: an unknown kind; context columns that are not distinct names; engine constants whose
    base point is not on the grid.
    """
    rule = "R14"
    k = _kind(kind, rule)
    context = _names(context_columns, "context_columns", rule)
    has_context = bool(context)
    flags: List[str] = []
    ratios = K.PENALTY_RATIOS if has_context else None
    if k == RouterKind.REGION:
        design = RouterDesign(kind=k, columns=(INTERCEPT, NORMAL, TREES), unpenalised=(INTERCEPT, NORMAL),
                              centre=(float(K.REGION_LAMBDA_CENTRE),),
                              grid=_grid(K.REGION_PENALTY_LEVELS, None),
                              fit_row_cap=int(K.REGION_ROUTER_ROW_BUDGET))
        base = GridPoint(1.0, None)
        if has_context:
            flags.append("context_unused")
        used = ("C12.region_lambda_centre", "C12.region_penalty_levels", "C7.region_router_row_budget")
    else:
        if k == RouterKind.PER_UNIT:
            trees_c, ctx_c = float(K.PER_UNIT_TREES_CENTRE), float(K.PER_UNIT_CONTEXT_CENTRE)
            columns = (INTERCEPT, NORMAL, CONTEXT, TREES) if has_context else (INTERCEPT, NORMAL, TREES)
            unpenalised = (INTERCEPT, NORMAL)
            used = ("C12.per_unit_trees_centre", "C12.per_unit_context_centre")
        else:
            trees_c, ctx_c = float(K.NEIGHBOUR_TREES_CENTRE), float(K.NEIGHBOUR_CONTEXT_CENTRE)
            columns = (INTERCEPT, CONTEXT, TREES) if has_context else (INTERCEPT, TREES)
            unpenalised = (INTERCEPT,)
            used = ("C12.neighbour_trees_centre", "C12.neighbour_context_centre")
        design = RouterDesign(kind=k, columns=columns, unpenalised=unpenalised, centre=(trees_c, ctx_c),
                              grid=_grid(K.PENALTY_LEVELS, ratios), fit_row_cap=None)
        base = GridPoint(1.0, ctx_c / trees_c if has_context else None)
        used = used + ("C12.penalty_levels", "C12.penalty_ratios")
    if base not in design.grid:
        raise DeriveRefusal(rule, "the base point %r is not on the %s grid" % (base, k.value),
                            fix="the C12 constants must put the centres on the grid")
    inputs = {"kind": k.value, "context_columns": list(context), "base_point": base,
              "grid_points": len(design.grid), "constants": constants_used(*used)}
    return make_derived(rule, design, inputs, flags=tuple(flags))


# ===================================================================================================
# R17 own-history spec
# Provenance: plan 2.3 R17; Q4 a, Q12 (the engine block replaces own-past columns; the all-history mean
# keeps the cumulative column's memory); D12 (offset = whole steps the target window reaches past its
# step, rounded up: timing.target_reach_offset_steps); ruling R-D b; F8 ("reach is measured from the
# window edge"; the history column names); extends pm25_forecast.py:122-159.
def derive_r17_history_spec(season: Any, target_window: Any, target_cadence: Any, kind: Any,
                            is_events: bool) -> Derived:
    """Which own-history columns the engine builds, and where the block starts.

    Rule: R17 (D12, R-D b). The last S2.history_last_values target values, trailing means over each of
    S2.history_trailing_years years counted in steps (years x R2's steps per year), and the mean of all
    history so far. The block ends at the issue step (t-1 for a nowcast); it starts
    start_offset_steps further back, the whole steps the target's own window reaches past its step,
    rounded up (timing.target_reach_offset_steps on the target's window and stamp, D12). A trailing
    mean over ONE step equals the last value and is dropped as a duplicate (on annual data the 1-year
    mean). Column names are io.apply.history_column_names' (hist_last_j, hist_mean_w, hist_mean_all).
    Neighbour: the empty spec. target_window is the target's FACTS (window and stamp): the reach is
    measured from the stamped window, which a bare window cannot place (signature gap, flagged).
    Returns Derived[HistorySpec]; inputs record the steps per year, the offset and the target window.
    Refuses: an unknown kind; a season without steps per year; a target without a window or stamp; an
    unknown target window (timing refuses it). Raises NotImplementedError for events (trailing means in
    days: milestone M8).
    """
    rule = "R17"
    k = _kind(kind, rule)
    if bool(is_events):
        if k == RouterKind.NEIGHBOUR:
            # the table option (owner ruling U1; SPEC_TABLE_MODE.md 5.4): the neighbour kind builds no own-history
            # block, on events as on grids, so its empty spec needs no event history rule (grids never reach here)
            empty = HistorySpec(columns=(), last_values=0, trailing_steps=(), trailing_days=(),
                                all_history_mean=False, start_offset_steps=0, dropped_duplicates=())
            return make_derived(rule, empty, {"kind": k.value, "rule": "empty for the neighbour kind"})
        raise NotImplementedError("R17 for events (the last visits and the trailing 365 / 1,826-day "
                                  "means of the as-of label view): milestone M8")
    if _value(getattr(season, "kind", None)) == EVENT_MONTH:
        raise DeriveRefusal(rule, "an event season key on a grid", fix="pass R2's outcome")
    empty = HistorySpec(columns=(), last_values=0, trailing_steps=(), trailing_days=(),
                        all_history_mean=False, start_offset_steps=0, dropped_duplicates=())
    if k == RouterKind.NEIGHBOUR:
        return make_derived(rule, empty, {"kind": k.value, "rule": "empty for the neighbour kind"})
    spy = getattr(season, "steps_per_year", None)
    if spy is None:
        raise DeriveRefusal(rule, "the season key has no steps per year", fix="pass R2's outcome")
    spy = _int(spy, "steps_per_year", rule)
    if spy < 1:
        raise DeriveRefusal(rule, "steps_per_year is %d" % spy, fix="pass R2's outcome")
    if getattr(target_window, "window", None) is None or getattr(target_window, "stamp", None) is None:
        raise DeriveRefusal(rule, "the reach past the step needs the target's window AND stamp; got %s"
                            % type(target_window).__name__,
                            fix="pass the target's facts (window and stamp) as target_window")
    offset = int(timing.target_reach_offset_steps(target_window, target_cadence))
    last = _int(K.HISTORY_LAST_VALUES, "S2.history_last_values", rule)
    trailing = tuple(_int(y, "a trailing length in years", rule) * spy for y in K.HISTORY_TRAILING_YEARS)
    full = HistorySpec(columns=(), last_values=last, trailing_steps=trailing, trailing_days=(),
                       all_history_mean=True, start_offset_steps=offset, dropped_duplicates=())
    names = history_column_names(full)
    one_step = [n for w, n in zip(trailing, names[last:last + len(trailing)]) if w == 1]
    columns = tuple(n for n in names if n not in one_step)
    spec = HistorySpec(columns=columns, last_values=last, trailing_steps=trailing, trailing_days=(),
                       all_history_mean=True, start_offset_steps=offset,
                       dropped_duplicates=tuple(one_step))
    window = target_window.window
    inputs = {"kind": k.value, "steps_per_year": spy, "start_offset_steps": offset,
              "target_stamp": _value(target_window.stamp),
              "target_window": {f: _reach_text(getattr(window, f, None)) for f in
                                ("length", "unit", "align", "max_length", "reach_after_max",
                                 "reach_before_max")},
              "dropped_rule": "a trailing mean over one step equals the last value",
              "constants": constants_used("S2.history_last_values", "S2.history_trailing_years")}
    flags = ("start_offset:%d" % offset,) if offset else ()
    return make_derived(rule, spec, inputs, flags=flags)


def _reach_text(value: Any) -> Any:
    """A window field as derived.json holds it (a reach fact becomes {value, unit})."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if hasattr(value, "value") and hasattr(value, "unit"):
        return {"value": float(value.value), "unit": _value(value.unit)}
    return _value(value)
