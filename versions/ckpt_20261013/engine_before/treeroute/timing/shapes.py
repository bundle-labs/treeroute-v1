"""Shapes the timing rules return, the refusal they raise, and how they read their inputs.

The approved shared shapes (the Lag and CutPair records, the fact views) are drafted in the proposed
signatures' common module, which engine code may not import (G-IMPORT). Until those shapes get their
engine home, this module holds FIELD-IDENTICAL copies of the two records timing returns (Lag,
CutPair), plus the owner-approved Reach fact (owner rulings, part B item 8 (a): reach_after_max /
reach_before_max on the window fact).

Inputs are read by attribute name only (duck typing), so a timing rule accepts the approved fact
views, the package schema's pydantic models or any object with the same field names. Enum-valued
facts are compared by their value string ('month', 'centred', ...), so an Enum member and its plain
string are the same fact.

Attributes read:
    column  : name, cadence, stamp, window, fact_status (only when the window has none),
              co_measured_with_target (optional)
    target  : name, cadence, stamp, window, computed_from (optional)
    window  : length, unit, align, max_length, fact_status (optional),
              reach_after_max (optional), reach_before_max (optional)
    reach   : value, unit
    cadence : kind, length, unit, composites_per_year (optional), composite_days (optional)
"""

from dataclasses import dataclass
from enum import Enum
from numbers import Integral, Real
from typing import Any, Optional, Tuple

from treeroute.errors import RefusedError


class TimingRefusal(RefusedError):
    """A timing rule refused (R8, R9, R11, R17, G-LAG). Nothing catches it to carry on."""


# ---------------------------------------------------------------------------------------------------
# Records (field-identical to the approved shared shapes)
@dataclass(frozen=True)
class Reach:
    """How far content reaches past an edge of its window (window fact, owner ruling item 8 (a))."""
    value: float
    unit: Any                          # 'day' / 'month' / 'year' (or the StepUnit enum)


@dataclass(frozen=True)
class Lag:
    """R8: one fixed lag per column, counted in the column's OWN steps (D22)."""
    column: str
    steps: int
    column_cadence: Any
    floor_reason: Optional[str]        # 'co_measured' / 'computed_from' when the 1-step floor bit


@dataclass(frozen=True)
class CutPair:
    """R11: both cuts of one lead, in steps (grids) or days (events)."""
    lead: int
    lead_unit: Any
    fit_cut: int
    guard_cut: int


@dataclass(frozen=True)
class LagTrace:
    """What compute_lag read and found, for derived.json's inputs and margins (R8).

    steps          the fixed lag: max over every target position in the year (D23) and over both
                   references (D24), after the 1-step floor
    content_steps  the same before the floor (the lag the content facts alone give)
    nowcast_steps  max over positions with the NOWCAST reference
    issue_steps    max over positions with the ISSUE_STEP reference
    worst_nowcast_period / worst_issue_period
                   a target period (first day, last day) at which that maximum is reached, on the
                   synthetic reference calendar (timing.calendar.reference_periods)
    worst_nowcast_position / worst_issue_position
                   the same period as a position in the year ('May 1 - May 31 (reference year 2 of
                   8; ...)'), for derived.json and messages
    positions      how many target periods were walked
    floor_reason   'co_measured', 'computed_from' or both joined by '+', when the floor raised the lag
    unanswered     facts the floor reads that have no answer ('co_measured_with_target' when it is
                   None): the lag was computed as if the answer were 'no'; G-FACTS blocks the
                   headline until it is answered
    """
    column: str
    steps: int
    content_steps: int
    nowcast_steps: int
    issue_steps: int
    worst_nowcast_period: Tuple[int, int]
    worst_issue_period: Tuple[int, int]
    worst_nowcast_position: str
    worst_issue_position: str
    positions: int
    floor_reason: Optional[str]
    unanswered: Tuple[str, ...]


@dataclass(frozen=True)
class AggregateReach:
    """How far the content of an aggregate reaches past its own stored periods (the aggregate's
    reach facts, computed by timing.aggregate_reach; D21 applied to the aggregate: the MAXIMUM over
    every aggregate period measured).

    before_days / after_days   the most the content starts before an aggregate period's first day
                               / ends after its last day, in whole days; 0 when it never does
    worst_before_period / worst_after_period
                               an aggregate period (first day, last day) where that maximum is met
    spans                      how many aggregate periods were measured
    """
    before_days: int
    after_days: int
    worst_before_period: Tuple[int, int]
    worst_after_period: Tuple[int, int]
    spans: int


# ---------------------------------------------------------------------------------------------------
# Input readers
def fact_value(value: Any, what: str) -> Optional[str]:
    """The value string of an enum-valued fact (an Enum member or its plain string); None stays None."""
    if value is None:
        return None
    if isinstance(value, Enum):
        value = value.value
    if not isinstance(value, str):
        raise TypeError("%s must be an enum member or its value string, got %r" % (what, value))
    return value


def as_int(value: Any, what: str) -> int:
    """A whole number (a Day ordinal, a step, a lead). Booleans and floats are refused."""
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError("%s must be a whole number, got %r" % (what, value))
    return int(value)


def as_period(period: Any, what: str) -> Tuple[int, int]:
    """A closed interval of whole days (first_day, last_day) with first_day <= last_day (D19)."""
    try:
        first, last = period
    except (TypeError, ValueError):
        raise TypeError("%s must be a (first_day, last_day) pair, got %r" % (what, period))
    first = as_int(first, what + " first day")
    last = as_int(last, what + " last day")
    if first > last:
        raise TimingRefusal("R8", "%s runs backwards: first day %d after last day %d"
                            % (what, first, last), fix="pass (first_day, last_day)")
    return first, last


def as_positive_number(value: Any, what: str) -> Real:
    if isinstance(value, bool) or not isinstance(value, Real) or not value > 0 \
            or value == float("inf"):
        raise TimingRefusal("R8", "%s must be a positive finite number, got %r" % (what, value),
                            fix="declare a positive length in the window fact")
    return value


def name_of(obj: Any) -> str:
    """The column or target name used in messages ('<unnamed>' when the object has none)."""
    name = getattr(obj, "name", None)
    return name if isinstance(name, str) and name else "<unnamed>"
