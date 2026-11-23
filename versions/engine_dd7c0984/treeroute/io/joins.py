"""1:1 joins with row-count asserts (plan 4.1 step 3; plan 5 G-JOIN, runtime; G-CADENCE).

SCIENCE bodies for the owner-approved signatures of treeroute/_proposed/io_science.py:
  - join_one_to_one      G-JOIN: 1:1 join on keys with a row-count assert.
  - join_coarser_column  G-CADENCE, R8: a column declared at a coarser cadence than its stored table
                         (an annual column in monthly rows): constancy assert, one value per unit x
                         period, the lag on that collapsed table, then the 1:1 join. Keys come as
                         explicit arrays of unit codes and coarse periods (owner ruling F6).
  - coarse_periods       the grid periods of join_coarser_column, computed from the rows' TARGET
                         steps (an addition awaiting the owner's sign-off).
  - asof_driver_join     R8 for events: milestone M8 (raises NotImplementedError).

Owner ruling D31 (proposed default accepted): unmatched left rows are allowed, get NaN in the
right-hand columns and are counted in the report (they then fall under R30), as the source's left
join did.

Pandas behaviours this module guards against, because they would fail silently:
  - merge() matches a NaN key with a NaN key; a NaN key is refused on either side.
  - merge() quietly compares a numeric key with a text key as unequal; a key that is numeric on one
    side and not on the other is refused. Numeric is read from the VALUES for an object column (ints
    held as Python objects are numeric) and from the categories for a categorical column, so an
    object key of numbers against an object key of text is refused too.
  - merge() may change a key's dtype (a categorical key comes back as object, Int64 as int64); the
    left key columns are put back from the left frame itself, dtype included.
"""

from dataclasses import dataclass
from typing import Any, Tuple

import numpy as np
import pandas as pd

from treeroute.engine_constants import CADENCE_CONSTANCY_TOLERANCE
from treeroute.errors import RefusedError
from treeroute.io.steps import (as_int_array, cadence_identity, cadence_view, predecessor_index,
                                step_bounds, step_containing)

_SHOW = 5


@dataclass(frozen=True)
class JoinReport:
    """Row counts of one 1:1 join."""
    what: str
    left_rows: int
    right_rows: int
    out_rows: int
    unmatched_left: int


def _check_frame(frame: pd.DataFrame, side: str, what: str) -> None:
    if not isinstance(frame, pd.DataFrame):
        raise RefusedError("G-JOIN", "%s: the %s side must be a pandas DataFrame, got %s"
                           % (what, side, type(frame).__name__))
    names = list(frame.columns)
    twice = sorted({str(c) for c in names if names.count(c) > 1})
    if twice:
        raise RefusedError("G-JOIN", "%s: the %s side holds these columns more than once: %s"
                           % (what, side, twice))


def _check_keys(frame: pd.DataFrame, keys: Tuple[str, ...], side: str, what: str) -> None:
    absent = [k for k in keys if k not in frame.columns]
    if absent:
        raise RefusedError("G-JOIN", "%s: the %s side has no key column %s" % (what, side, absent))
    for k in keys:
        nulls = frame[k].isna()
        if nulls.any():
            raise RefusedError("G-JOIN", "%s: the %s side has %d missing values in key %r (a NaN key "
                               "would match a NaN key)" % (what, side, int(nulls.sum()), k))
    dup = frame.duplicated(subset=list(keys), keep=False)
    if dup.any():
        shown = frame.loc[dup, list(keys)].head(_SHOW).to_dict("records")
        raise RefusedError("G-JOIN", "%s: %d rows on the %s side share a key, e.g. %s"
                           % (what, int(dup.sum()), side, shown))


_NUMERIC_VALUES = ("integer", "floating", "mixed-integer-float", "decimal", "boolean")


def _is_numeric_key(values: pd.Series) -> bool:
    """True when a key column holds numbers: by dtype, or, for an object column, by its values
    (pandas infer_dtype), or, for a categorical column, by its categories."""
    dtype = values.dtype
    if isinstance(dtype, pd.CategoricalDtype):
        return _is_numeric_key(pd.Series(dtype.categories))
    if pd.api.types.is_numeric_dtype(dtype):
        return True
    if dtype == object:
        return len(values) > 0 and pd.api.types.infer_dtype(values, skipna=False) in _NUMERIC_VALUES
    return False


# Provenance: pm25_architecture.py:155-160 (left merge + row-count assert); plan 5 G-JOIN.
def join_one_to_one(left: pd.DataFrame, right: pd.DataFrame, keys: Tuple[str, ...],
                    what: str) -> Tuple[pd.DataFrame, JoinReport]:
    """Join 1:1 on keys with a row-count assert.

    Rule: G-JOIN (runtime), D31. The output has exactly the left rows, in left order, with the left
    index and the left key columns (values and dtypes) unchanged; the right's non-key columns follow
    the left's columns. Unmatched left rows get NaN and are counted (D31), even when every row is
    unmatched (whether that should refuse is an open owner question). Neither input is changed.
    Refuses: duplicate keys on either side; a missing (NaN) key; a key absent from either side or
    numeric on one side only (numeric read from the values of an object column); any change in row
    count or row order; a right column name that collides with a left column; repeated column
    names; an empty key list.
    """
    if not isinstance(what, str) or not what:
        raise RefusedError("G-JOIN", "what must be a non-empty label, got %r" % (what,))
    if isinstance(keys, str):
        raise RefusedError("G-JOIN", "%s: keys is a tuple of column names, not one string" % what)
    keys = tuple(keys)
    if not keys or len(set(keys)) != len(keys):
        raise RefusedError("G-JOIN", "%s: keys must be a non-empty list of distinct columns, got %r"
                           % (what, keys))
    _check_frame(left, "left", what)
    _check_frame(right, "right", what)
    _check_keys(left, keys, "left", what)
    _check_keys(right, keys, "right", what)
    for k in keys:
        if _is_numeric_key(left[k]) != _is_numeric_key(right[k]):
            kinds = ["numeric" if _is_numeric_key(f[k]) else "not numeric" for f in (left, right)]
            raise RefusedError("G-JOIN", "%s: key %r is %s on the left (%s) and %s on the right (%s)"
                               % (what, k, kinds[0], left[k].dtype, kinds[1], right[k].dtype))
    collide = sorted(str(c) for c in right.columns if c not in keys and c in left.columns)
    if collide:
        raise RefusedError("G-JOIN", "%s: right columns collide with left columns: %s" % (what, collide))

    flag = "_join_indicator"
    while flag in left.columns or flag in right.columns:
        flag = "_" + flag
    merged = left.reset_index(drop=True).merge(
        right.reset_index(drop=True), on=list(keys), how="left", sort=False,
        validate="one_to_one", indicator=flag)
    if len(merged) != len(left):
        raise RefusedError("G-JOIN", "%s: the join changed the row count (%d -> %d)"
                           % (what, len(left), len(merged)))
    for k in keys:
        if not np.array_equal(merged[k].to_numpy(dtype=object), left[k].to_numpy(dtype=object)):
            raise RefusedError("G-JOIN", "%s: internal: the join changed the row order or key %r" % (what, k))
        merged[k] = left[k].reset_index(drop=True)  # the left key back, dtype included
    unmatched = int((merged[flag] == "left_only").sum())
    merged = merged.drop(columns=[flag])
    merged.index = left.index
    report = JoinReport(what=what, left_rows=len(left), right_rows=len(right), out_rows=len(merged),
                        unmatched_left=unmatched)
    return merged, report


# ---------------------------------------------------------------------------------------------------
# A column declared at a coarser cadence than the table that stores it (G-CADENCE, R8; F6)
def _nested(periods: np.ndarray, column_cadence: Any, target_cadence: Any, column: str) -> None:
    """Refuse unless every column step holds whole target steps: the target step holding a column
    step's first day starts on that day, and the one holding its last day ends on it."""
    if len(periods) == 0:
        return
    first, last = step_bounds(periods, column_cadence)
    t_first, _ = step_bounds(step_containing(first, target_cadence), target_cadence)
    _, t_last = step_bounds(step_containing(last, target_cadence), target_cadence)
    bad = (t_first != first) | (t_last != last)
    if bad.any():
        raise RefusedError("G-CADENCE", "column %r: its declared cadence %s is finer than the target's %s "
                           "(or its steps do not hold whole target steps), e.g. column periods %s"
                           % (column, cadence_identity(cadence_view(column_cadence)),
                              cadence_identity(cadence_view(target_cadence)), periods[bad][:_SHOW].tolist()),
                           fix="a column at the target's own step is lagged by apply_lags; a finer column "
                               "is aggregated to the target's step first (aggregate_time)")


def coarse_periods(target_steps: np.ndarray, target_cadence: Any, column_cadence: Any) -> np.ndarray:
    """The grid_periods argument of join_coarser_column: for each grid row, the step of the column's
    coarser cadence that holds the row's TARGET step whole.

    Rule: G-CADENCE, R8 (owner ruling F6 passes the periods explicitly; this pins the one way to
    compute them, from the target steps, for the feature runner to call. join_coarser_column cannot
    tell whether it was used: a caller that hands in a shifted period, one step late, would with a
    lag of 0 or 1 read the row's own period, a same-period leak).
    target_steps are the integer target steps of the grid rows (io.steps.step_index form, the steps
    the rows PREDICT, never their issue steps; features_at_issue_step moves the whole joined row
    back afterwards). Returns int64 periods, one per row, in row order.
    SIGNATURE (owner sign-off asked): an addition next to join_coarser_column, not in the approved
    contracts.
    Refuses: target steps that are not integers; a column cadence that does not hold whole target
    steps (a target step whose first and last days fall in different column periods: the column is
    finer than the target, or the two do not nest); whatever step_bounds and step_containing refuse
    (a cadence without a fixed origin, a static, epoch or irregular cadence).
    """
    t = as_int_array(target_steps, "target steps", rule="G-CADENCE")
    first, last = step_bounds(t, target_cadence)
    periods = step_containing(first, column_cadence)
    split = step_containing(last, column_cadence) != periods
    if split.any():
        raise RefusedError("G-CADENCE", "%d target steps do not nest in one period of the column's cadence "
                           "%s (the target's is %s), e.g. target steps %s"
                           % (int(split.sum()), cadence_identity(cadence_view(column_cadence)),
                              cadence_identity(cadence_view(target_cadence)), t[split][:_SHOW].tolist()),
                           fix="a coarser column's periods must hold whole target steps; a finer column is "
                               "aggregated to the target's step first (aggregate_time)")
    return periods.astype(np.int64)


def _key_name(base: str, taken: Tuple[str, ...]) -> str:
    name = base
    while name in taken:
        name = "_" + name
    return name


# Provenance: pm25_architecture.py:139-160 (share of cell-years with >1 distinct non-NaN value must
# be <= 0.001, else stop; then the first value per cell-year; the lag is applied to that collapsed
# table, year + 1, BEFORE the left join with its row-count assert, :152-160); plan 5 G-CADENCE;
# owner ruling F6 (explicit arrays of unit codes and coarse periods).
def join_coarser_column(grid_frame: pd.DataFrame, grid_unit_codes: np.ndarray, grid_periods: np.ndarray,
                        column_frame: pd.DataFrame, column_unit_codes: np.ndarray,
                        column_periods: np.ndarray, column: str, column_cadence: Any,
                        target_cadence: Any, lag: Any) -> pd.DataFrame:
    """Join a column stored in a finer table but declared at a coarser cadence (an annual column
    inside monthly rows) onto the target-step frame, after asserting it is constant within each
    unit x coarse period, with its R8 lag applied to the collapsed table before the join.

    Rule: G-CADENCE (annual joins), R8, G-CALENDAR, G-JOIN; owner ruling F6.
    Keys come as explicit arrays (F6): for every grid row, its integer unit code and the coarse
    period (an integer step of the COLUMN's cadence, e.g. the year) that holds its target step; for
    every stored row, its unit code and coarse period. Unit codes must be one coding on both sides.
    The grid periods must be computed with coarse_periods from the rows' TARGET steps: this body
    has no target steps, so it cannot check that a caller did not pass the issue step's period or
    a shifted one. Nor can it prove the two sides share one unit coding: it refuses only codings
    with no code in common (a store may hold units the grid lacks, and a grid unit may be absent
    from the store, which gives NaN and then R30).
    Steps:
      1. constancy: the share of stored unit x coarse periods holding more than one distinct
         non-NaN value must not exceed engine constant S5.cadence_constancy_tolerance (0.1%);
         every unit x period present counts in the denominator (the source's rule);
      2. one value per unit x period: the first non-NaN value in the stored rows' order (the
         source's rule; below the tolerance a varying period keeps that first value);
      3. the lag, in the column's own steps, on that collapsed table through predecessor_index: the
         value of period P serves the grid rows of period P + lag.steps (an annual lag of 1: year
         Y-1 serves every month of year Y). The collapsed table is first extended with the grid's
         (unit, period) keys, NaN valued, so the latest stored period can serve the period after
         it. A missing predecessor period gives NaN (then R30), never a neighbour's value;
      4. the lagged table is joined 1:1 (join_one_to_one) onto the grid's distinct (unit, period)
         keys, and each grid row takes its key's value: the target-step frame keeps its rows, order
         and index, and gains the column (integer and boolean values come back as float64, so a
         missing period is NaN).
    apply_lags never sees a coarser column. Neither input frame is changed.
    Refuses: the column absent from the stored frame, or already a grid column; key arrays that
    are not one integer per row of their frame; stored and grid unit codes with no code in common
    (two codings); a lag that is not a Lag of this column, is negative, or counts steps of another
    cadence than the column's; a declared cadence finer than the target's (a column step that does
    not hold whole target steps); a constancy share above the tolerance (the premise of the declared
    cadence is wrong); (internal) a lagged read that leaves its unit or is not exactly lag.steps
    back; whatever join_one_to_one refuses.
    """
    what = "coarser column %r" % (column,)
    if not isinstance(column, str) or not column:
        raise RefusedError("G-CADENCE", "column must be a non-empty name, got %r" % (column,))
    _check_frame(grid_frame, "grid", what)
    _check_frame(column_frame, "stored", what)
    if column not in column_frame.columns:
        raise RefusedError("G-CADENCE", "%s: the stored frame does not hold the column" % what)
    if column in grid_frame.columns:
        raise RefusedError("G-JOIN", "%s: the grid frame already holds a column of that name" % what)
    g_units = as_int_array(grid_unit_codes, "grid unit codes", rule="G-CADENCE")
    g_periods = as_int_array(grid_periods, "grid periods", rule="G-CADENCE")
    c_units = as_int_array(column_unit_codes, "stored unit codes", rule="G-CADENCE")
    c_periods = as_int_array(column_periods, "stored periods", rule="G-CADENCE")
    if not (len(g_units) == len(g_periods) == len(grid_frame)):
        raise RefusedError("G-CADENCE", "%s: grid unit codes (%d), grid periods (%d) and grid rows (%d) "
                           "differ in length" % (what, len(g_units), len(g_periods), len(grid_frame)))
    if not (len(c_units) == len(c_periods) == len(column_frame)):
        raise RefusedError("G-CADENCE", "%s: stored unit codes (%d), stored periods (%d) and stored rows "
                           "(%d) differ in length" % (what, len(c_units), len(c_periods), len(column_frame)))
    if len(g_units) and len(c_units) and not np.intersect1d(g_units, c_units).size:
        raise RefusedError("G-CADENCE", "%s: the grid and the stored rows share no unit code; the two "
                           "sides must use one unit coding" % what)

    try:
        lag_column, lag_steps, lag_cadence = lag.column, lag.steps, lag.column_cadence
    except AttributeError:
        raise RefusedError("R8", "%s: the lag is not a Lag (column, steps, column_cadence)" % what) from None
    if lag_column != column:
        raise RefusedError("R8", "%s: the lag given is the lag of %r" % (what, lag_column))
    if isinstance(lag_steps, (bool, np.bool_)) or not isinstance(lag_steps, (int, np.integer)):
        raise RefusedError("R8", "%s: the lag must be a whole number of steps, got %r" % (what, lag_steps))
    k = int(lag_steps)
    if k < 0:
        raise RefusedError("R8", "%s: the lag is negative (%d)" % (what, k))
    col_identity = cadence_identity(cadence_view(column_cadence))
    lag_identity = cadence_identity(cadence_view(lag_cadence))
    if lag_identity != col_identity:
        raise RefusedError("R8", "%s: the lag counts steps of %s, not of the column's cadence %s"
                           % (what, lag_identity, col_identity))
    cadence_view(target_cadence)
    _nested(np.unique(np.concatenate([c_periods, g_periods])), column_cadence, target_cadence, column)

    values = column_frame[column].to_numpy()
    numeric = values.dtype.kind in "fiub"
    if numeric:
        values = values.astype(np.float64)
    stored = pd.DataFrame({"u": c_units, "p": c_periods, "v": values})
    groups = stored.groupby(["u", "p"], sort=False)["v"]
    distinct = groups.nunique(dropna=True)
    varying = distinct[distinct > 1]
    share = float(len(varying)) / len(distinct) if len(distinct) else 0.0
    if share > CADENCE_CONSTANCY_TOLERANCE:
        raise RefusedError("G-CADENCE", "%s: %d of %d unit x periods (share %.6f, above %.6f) hold more "
                           "than one distinct value, e.g. (unit code, period) %s"
                           % (what, len(varying), len(distinct), share, CADENCE_CONSTANCY_TOLERANCE,
                              [tuple(int(x) for x in key) for key in varying.index[:_SHOW]]),
                           fix="the column varies inside its declared period: correct the column's "
                               "cadence fact")
    collapsed = groups.first()
    cu = collapsed.index.get_level_values(0).to_numpy(dtype=np.int64)
    cp = collapsed.index.get_level_values(1).to_numpy(dtype=np.int64)

    grid_keys, grid_inverse = np.unique(np.stack([g_units, g_periods], axis=1), axis=0,
                                        return_inverse=True)
    grid_inverse = np.asarray(grid_inverse).reshape(-1)
    union, union_inverse = np.unique(np.concatenate([np.stack([cu, cp], axis=1), grid_keys], axis=0),
                                     axis=0, return_inverse=True)
    union_inverse = np.asarray(union_inverse).reshape(-1)
    uu = union[:, 0].astype(np.int64)
    up = union[:, 1].astype(np.int64)
    base = np.full(len(union), np.nan) if numeric else np.full(len(union), None, dtype=object)
    base[union_inverse[:len(cu)]] = collapsed.to_numpy()
    if k == 0:
        lagged = base
    else:
        src = predecessor_index(uu, up, k)
        ok = src >= 0
        if not ((uu[src[ok]] == uu[ok]).all() and (up[ok] - up[src[ok]] == k).all()):
            raise RefusedError("G-CALENDAR", "internal: a lag-%d read of %r left its unit or period"
                               % (k, column))
        lagged = np.full(len(union), np.nan) if numeric else np.full(len(union), None, dtype=object)
        lagged[ok] = base[src[ok]]

    ku = _key_name("unit_code", (column,))
    kp = _key_name("period", (column, ku))
    right = pd.DataFrame({ku: uu, kp: up, column: lagged})
    left = pd.DataFrame({ku: grid_keys[:, 0].astype(np.int64), kp: grid_keys[:, 1].astype(np.int64)})
    joined, _ = join_one_to_one(left, right, (ku, kp), what)
    out = grid_frame.copy(deep=True)
    out[column] = pd.Series(joined[column].to_numpy()[grid_inverse], index=grid_frame.index, name=column)
    return out


# Provenance: plan 1.2 driver tables ("For events the ENGINE does the as-of join at each row's issue
# date, using each column's computed reach (R8)"). M8 under the fast track.
def asof_driver_join(events: pd.DataFrame, driver: pd.DataFrame, reach: Any) -> pd.DataFrame:
    """For each event row, the newest driver value whose content ends at or before its issue date
    (R8 for events). Not built: milestone M8 (the event rules, fast track)."""
    raise NotImplementedError("asof_driver_join is built at milestone M8 (the event rules)")
