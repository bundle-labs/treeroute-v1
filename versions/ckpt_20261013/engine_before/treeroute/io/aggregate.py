"""Time aggregation of a finer column to the target's step (plan 1.5 aggregate_time; owner rulings
F5, D34, D35).

SCIENCE body for the owner-approved signature aggregate_time (treeroute/_proposed/io_science.py).

What it does, generically (no problem, unit or year is named here):
  - each stored value of the source column belongs to the target step that holds its whole
    calendar span (io.steps.step_bounds, step_containing); a source step that does not nest in one
    target step is refused, so a period's aggregate reads only content stored INSIDE that period
    (plan 1.5, "trailing only");
  - the statistic (mean, min, max or sum) runs over each unit x target period, or over the
    declared season months inside a target year (a growing season);
  - D34 (strict): a unit x period with any season sub-period missing (no row, or a NaN value) is
    NaN; the aggregate never averages over the sub-periods that happen to be there;
  - D35: the legal range of a SUM is [n x min, n x max] for n sub-periods (the widest over the
    periods in the data); mean, min and max inherit the source's range;
  - F5: the output's stamp and window are COMPUTED with the timing helpers
    (timing.aggregate_reach over every aggregate period the data holds, each with the
    sub-periods actually aggregated, then timing.aggregate_window). A value stored inside a
    period whose content reaches past it (a centred or filtered index, a composite that runs into
    the next year) therefore gives the aggregate a reach past its period, and R8 then gives it the
    ruled 1-year lag on an annual target. A window typed as the calendar period alone would give
    lag 0: the leak this prevents (timing/aggregate.py).

The output facts are the input facts with three kinds of field (the lists below are exact; a field
the facts record does not have is skipped):
  - COMPUTED here: cadence (the target's), stamp and window (F5), legal_range (D35, a sum only),
    fill_values (none: the output holds NaN, never a code), dtype (float64), derived_from (the
    source column).
  - RESET, because they describe the PARENT's own declaration and would contradict the aggregate's
    record: operation -> None (the aggregate's declaration is its own catalog entry, an
    aggregate_time operation, which replaces the parent's; a parent that is itself engineered,
    e.g. a trailing operation,
    must not lend it that operation), reviewed_by -> None (nobody has reviewed the aggregate's
    record), role -> engineered (plan 1.3: derived_from and operation belong to engineered columns
    only; plan 1.1: a finer driver is aggregated by the feature script).
  - INHERITED, everything else: name, units, scope, legal_range (mean, min, max), product_family,
    lineage_assimilates, lineage_trained_on (plan 1.5), and the provenance and content facts the
    aggregation does not change: near_sentinel_optout, sum_group, content_epoch, observed_through,
    release_date, snapshot_date, baseline_period, absent_groups, reads_target, fact_status,
    co_measured_with_target, co_measured_part, data_selected.
The column keeps its name; a package that declares the aggregate under another name renames it
(and its facts) itself. The reset and inherited lists await the owner's confirmation.

SIGNATURE (owner sign-off asked): the approved signature passes the rows as one frame with no key
names, so this body takes the unit codes and source steps as explicit arrays after the frame, the
form the owner ruled for join_coarser_column (F6) and the one apply_lags already uses.
"""

from dataclasses import dataclass, is_dataclass, replace
from enum import Enum
from types import SimpleNamespace
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from treeroute.engine_constants import MONTHS_PER_YEAR, SENTINEL_MASK_ABS
from treeroute.errors import RefusedError
from treeroute.io.steps import (as_int_array, cadence_identity, cadence_view, fact_value, step_bounds,
                                step_containing)
from treeroute.timing import Reach, aggregate_reach, aggregate_window, periods_inside

AGG_STATS = ("mean", "min", "max", "sum")
UNIT_CODE = "unit_code"   # output key: the unit code of the input rows
STEP = "step"             # output key: the integer target step (io.steps.step_index form)
_SHOW = 5
_MONTHLY = SimpleNamespace(kind="regular", length=1, unit="month")
_REQUIRED_FACTS = ("cadence", "stamp", "window")
ENGINEERED_ROLE = "engineered"   # plan 1.3 role of a column the feature script builds


@dataclass(frozen=True)
class AggregateWindow:
    """The computed window of an aggregate: the approved Window's fields plus the ruled reach facts
    (owner rulings, part B item 8 (a)), as timing.aggregate_window computes them: a window equal to
    the stored step, aligned backward from the period end, widened by the measured reach."""
    length: Any
    unit: Any
    align: Any
    max_length: Any = None
    fact_status: Any = None
    reach_after_max: Optional[Reach] = None
    reach_before_max: Optional[Reach] = None


def _like(example: Any, value: str) -> Any:
    """``value`` as a member of ``example``'s enum when the input used enums, else the plain string."""
    if isinstance(example, Enum):
        return type(example)(value)
    return value


def _engineered_role(example: Any) -> Any:
    """The engineered role, as a member of the input's role enum when the input used one."""
    if isinstance(example, Enum):
        try:
            return type(example)(ENGINEERED_ROLE)
        except ValueError:
            raise RefusedError("plan 1.3", "the role enum %s of the facts has no %r member, so the aggregate's "
                               "role cannot be written" % (type(example).__name__, ENGINEERED_ROLE)) from None
    return ENGINEERED_ROLE


def _months(days: np.ndarray) -> np.ndarray:
    """Calendar month (1..months-per-year) of each day ordinal."""
    return (step_containing(days, _MONTHLY) - 1) % MONTHS_PER_YEAR + 1


def _season(season_months: Any, target_view: Any) -> Optional[Tuple[int, ...]]:
    if season_months is None:
        return None
    if isinstance(season_months, (str, bytes)):
        raise RefusedError("plan 1.5", "season_months is a list of month numbers, got %r" % (season_months,))
    months = tuple(season_months)
    bad = [m for m in months if isinstance(m, (bool, np.bool_)) or not isinstance(m, (int, np.integer))
           or not 1 <= int(m) <= MONTHS_PER_YEAR]
    if not months or bad:
        raise RefusedError("plan 1.5", "season_months must be month numbers 1..%d, got %r"
                           % (MONTHS_PER_YEAR, season_months))
    months = tuple(int(m) for m in months)
    if len(set(months)) != len(months):
        raise RefusedError("plan 1.5", "season_months names a month twice: %r" % (season_months,))
    if not (target_view.kind == "regular" and target_view.length == 1 and target_view.unit == "year"):
        raise RefusedError("plan 1.5", "a season is a set of months inside the year; the target step "
                           "is %s, not one year" % (cadence_identity(target_view),))
    return tuple(sorted(months))


def _check_masked(values: np.ndarray, facts: Any, column: str) -> None:
    """The frame must hold masked values (sentinels are masked at read, before any aggregation)."""
    finite = values[np.isfinite(values)]
    huge = np.abs(finite) >= SENTINEL_MASK_ABS
    fills = [float(f) for f in (getattr(facts, "fill_values", None) or ())]
    coded = np.isin(finite, np.asarray(fills, dtype=np.float64)) if fills else np.zeros(len(finite), bool)
    if huge.any() or coded.any():
        raise RefusedError("G-SENTINEL", "column %r holds %d unmasked sentinel values (abs >= %g or a "
                           "declared fill value)" % (column, int((huge | coded).sum()), SENTINEL_MASK_ABS),
                           fix="mask sentinels at read (io.sentinel.mask_sentinels) before aggregating")


def _with(facts: Any, updates: Dict[str, Any]) -> Any:
    """A copy of the facts with ``updates`` for the fields they have (dataclass or namespace view)."""
    present = {k: v for k, v in updates.items() if hasattr(facts, k)}
    if is_dataclass(facts) and not isinstance(facts, type):
        return replace(facts, **present)
    if isinstance(facts, SimpleNamespace):
        fields = dict(vars(facts))
        fields.update(present)
        return SimpleNamespace(**fields)
    raise RefusedError("plan 1.5", "facts must be a column-facts record (a dataclass such as the approved "
                       "ColumnFacts, or a namespace view), got %s" % type(facts).__name__)


def _sum_range(legal_range: Any, counts: np.ndarray) -> Tuple[float, float]:
    """D35: [n x min, n x max], widest over the sub-period counts n of the periods in the data."""
    lo, hi = float(legal_range[0]), float(legal_range[1])
    n_lo, n_hi = float(counts.min()), float(counts.max())
    return min(n_lo * lo, n_hi * lo), max(n_lo * hi, n_hi * hi)


# Provenance: plan 1.5 (aggregate_time; an aggregate inherits units, legal range for mean/min/max,
# lineage and product family; its window and stamp are computed); defo_matrix.py:21-25; owner rulings
# F5 (facts through the timing helpers), D34 (strict), D35 (sum range).
def aggregate_time(frame: pd.DataFrame, unit_codes: np.ndarray, steps: np.ndarray, column: str, facts: Any,
                   target_cadence: Any, stat: Any, season_months: Optional[Tuple[int, ...]]) -> Tuple[pd.DataFrame, Any]:
    """Aggregate a finer column to the target's step (monthly to annual, or to a growing season).

    Rule: plan 1.5 aggregate_time; F5, D34, D35 (see the module docstring for the whole rule).
    Inputs: frame holds the source column (sentinels already masked); unit_codes and steps give
    each row's integer unit code and its step in the column's OWN cadence (facts.cadence, the
    io.steps.step_index form); facts are the column's facts; target_cadence is the step to
    aggregate to; stat is mean, min, max or sum (an enum member or its string); season_months is
    an optional month set inside the target year.
    Returns (rows, facts): one row per unit x target step that any input row falls in, sorted by
    unit code then step, with columns unit_code, step and the column (float64; NaN where a season
    sub-period is missing, D34); and the computed facts of the aggregate (module docstring).
    A row whose sub-period is outside the season is not read. Neither input is changed.
    Refuses: a frame that is not a DataFrame, lacks the column or holds a column twice; the column
    named like an output key; key arrays that are not one integer per row; duplicate (unit, step);
    a non-numeric column, or one holding an unmasked sentinel; facts of another column, or without
    cadence, stamp and window; a source cadence that is not finer than the target's (the same step,
    or a source step that does not nest in one target step); an unknown stat; season months that
    are not distinct month numbers, or a season on a target step other than one year, or a season
    that selects no sub-period of a period; an empty frame (no period to compute the facts on);
    facts whose role is an enum without an 'engineered' member (the reset role cannot be written);
    whatever the timing helpers refuse (for example a source window that is unknown and unsigned:
    the aggregate's reach cannot be computed, as R8 cannot lag the source).
    """
    if not isinstance(frame, pd.DataFrame):
        raise RefusedError("plan 1.5", "frame must be a pandas DataFrame, got %s" % type(frame).__name__)
    names = list(frame.columns)
    twice = sorted({str(c) for c in names if names.count(c) > 1})
    if twice:
        raise RefusedError("plan 1.5", "the frame holds these columns more than once: %s" % twice)
    if not isinstance(column, str) or column not in frame.columns:
        raise RefusedError("plan 1.5", "the frame does not hold the column %r" % (column,))
    if column in (UNIT_CODE, STEP):
        raise RefusedError("plan 1.5", "the column %r has the name of an output key (%s, %s)"
                           % (column, UNIT_CODE, STEP))
    units = as_int_array(unit_codes, "unit codes", rule="G-CALENDAR")
    s = as_int_array(steps, "steps", rule="G-CALENDAR")
    if not (len(units) == len(s) == len(frame)):
        raise RefusedError("G-CALENDAR", "unit codes (%d), steps (%d) and frame rows (%d) differ in length"
                           % (len(units), len(s), len(frame)))
    raw = frame[column].to_numpy()
    if raw.dtype.kind not in "fiu":
        raise RefusedError("plan 1.5", "column %r must be numeric to aggregate, got dtype %s" % (column, raw.dtype))
    values = raw.astype(np.float64)

    missing = [f for f in _REQUIRED_FACTS if not hasattr(facts, f)]
    if missing:
        raise RefusedError("plan 1.5", "the facts of %r lack %s" % (column, missing))
    name = getattr(facts, "name", column)
    if name != column:
        raise RefusedError("plan 1.5", "the facts given are the facts of %r, not of %r" % (name, column))
    _check_masked(values, facts, column)
    source_view = cadence_view(facts.cadence)
    target_view = cadence_view(target_cadence)
    if cadence_identity(source_view) == cadence_identity(target_view):
        raise RefusedError("G-CADENCE", "column %r already has the target's step %s: its source cadence is "
                           "not finer" % (column, cadence_identity(target_view)),
                           fix="a column at the target's step needs no aggregation (apply_lags lags it)")
    stat_name = fact_value(stat, "stat")
    if stat_name not in AGG_STATS:
        raise RefusedError("plan 1.5", "unknown statistic %r (known: %s)" % (stat_name, ", ".join(AGG_STATS)))
    season = _season(season_months, target_view)
    if len(frame) == 0:
        raise RefusedError("plan 1.5", "column %r: an empty frame has no aggregate period to compute the "
                           "facts on" % column)
    repeated = pd.DataFrame({"u": units, "s": s}).duplicated(keep=False).to_numpy()
    if repeated.any():
        i = np.flatnonzero(repeated)[:_SHOW]
        raise RefusedError("G-CALENDAR", "%d rows repeat a (unit, step), e.g. %s"
                           % (int(repeated.sum()), list(zip(units[i].tolist(), s[i].tolist()))))

    # each stored value belongs to the target step holding its whole span (trailing only)
    first, last = step_bounds(s, facts.cadence)
    target_step = step_containing(first, target_cadence)
    straddle = step_containing(last, target_cadence) != target_step
    if straddle.any():
        i = np.flatnonzero(straddle)[:_SHOW]
        raise RefusedError("G-CADENCE", "column %r: %d source steps do not nest in one target step (the "
                           "source cadence %s is not finer than the target's %s), e.g. steps %s"
                           % (column, int(straddle.sum()), cadence_identity(source_view),
                              cadence_identity(target_view), s[i].tolist()),
                           fix="aggregate only to a step the column's own steps nest in (plan 1.5)")

    # every aggregate period of the data, with the sub-periods it aggregates (season months only)
    periods = np.unique(target_step)
    p_first, p_last = step_bounds(periods, target_cadence)
    spans = []
    expected = np.empty(len(periods), dtype=np.int64)
    for i in range(len(periods)):
        period = (int(p_first[i]), int(p_last[i]))
        subs = periods_inside(facts.cadence, period)
        if season is not None:
            sub_first = np.array([a for a, _ in subs], dtype=np.int64)
            sub_last = np.array([b for _, b in subs], dtype=np.int64)
            keep = np.isin(_months(sub_first), season) & np.isin(_months(sub_last), season)
            subs = tuple(sp for sp, k in zip(subs, keep.tolist()) if k)
        if not subs:
            raise RefusedError("plan 1.5", "column %r: the season months %s hold no whole source step of "
                               "the target period %d" % (column, season, int(periods[i])))
        spans.append((period, subs))
        expected[i] = len(subs)

    in_season = np.ones(len(s), dtype=bool)
    if season is not None:
        in_season = np.isin(_months(first), season) & np.isin(_months(last), season)
    use = in_season & np.isfinite(values)
    read = pd.DataFrame({"u": units[use], "t": target_step[use], "v": values[use]})
    agg = read.groupby(["u", "t"], sort=True)["v"].agg(["count", stat_name]).reset_index()
    keys = pd.DataFrame({"u": units, "t": target_step}).drop_duplicates().sort_values(["u", "t"])
    table = keys.merge(agg, on=["u", "t"], how="left", sort=False)
    counts = table["count"].fillna(0).to_numpy(dtype=np.int64)
    need = expected[np.searchsorted(periods, table["t"].to_numpy(dtype=np.int64))]
    result = np.where(counts == need, table[stat_name].to_numpy(dtype=np.float64), np.nan)
    rows = pd.DataFrame({UNIT_CODE: table["u"].to_numpy(dtype=np.int64),
                         STEP: table["t"].to_numpy(dtype=np.int64), column: result})

    # the computed facts (F5): reach over every period of the data, then the window in catalog form
    reach = aggregate_reach(facts, spans)
    fact = aggregate_window(reach, target_cadence)
    window_fact = fact["window"]
    source_window = facts.window
    unit_example = getattr(target_cadence, "unit", None)
    if unit_example is None:
        unit_example = getattr(source_window, "unit", None)
    status = getattr(source_window, "fact_status", None)
    if status is None:
        status = getattr(facts, "fact_status", None)

    def reach_of(key: str) -> Optional[Reach]:
        given = window_fact.get(key)
        if given is None:
            return None
        return Reach(value=given["value"], unit=_like(unit_example, given["unit"]))

    window = AggregateWindow(length=window_fact["length"], unit=_like(unit_example, window_fact["unit"]),
                             align=_like(getattr(source_window, "align", None), window_fact["align"]),
                             max_length=None, fact_status=status,
                             reach_after_max=reach_of("reach_after_max"),
                             reach_before_max=reach_of("reach_before_max"))
    updates: Dict[str, Any] = {
        # computed
        "cadence": target_cadence,
        "stamp": _like(getattr(facts, "stamp", None), fact["stamp"]),
        "window": window,
        "fill_values": (),
        "dtype": "float64",
        "derived_from": (column,),
        # reset: the parent's own declaration, review and role do not describe the aggregate
        "operation": None,
        "reviewed_by": None,
        "role": _engineered_role(getattr(facts, "role", None)),
    }
    legal_range = getattr(facts, "legal_range", None)
    if stat_name == "sum" and legal_range is not None:
        updates["legal_range"] = _sum_range(legal_range, expected)
    return rows, _with(facts, updates)
