"""Exact calendar arithmetic for the timing rules (module-wide convention D19).

Days are proleptic Gregorian ordinals (datetime.date.toordinal). Periods and content are CLOSED
intervals of whole days (first_day, last_day). Inside a computation an INSTANT is an exact fraction on
the day line: day d covers [d, d + 1). Month and year coordinates are linear inside each month or
year, so month index M covers [M, M + 1) and a centred month window is exact whatever the month's
length. A content interval is read back to whole days conservatively: its first day is the day that
holds its first instant, its last day is the day that holds its last instant, so a partly covered day
counts as content. Nothing here rounds through floating point.

Periods of a cadence (CadenceGrid): a regular step of n months is anchored so that n-month steps
start at month index 0 (January when n divides the months of a year); a regular step of n years at
year 0; a regular step of n days at day ordinal 1 (the calendar's first day, used only to walk the
calendar: a column and a target on the same n-day step share it); composite-of-year steps restart on
1 January and the last one of a year ends on 31 December (plan R1; a longer spill is a reach fact).
Irregular data (events) use one-day periods.

That anchor is NOT the data's: step_index counts a regular step longer than one unit from the
target table's first observed position (D29), which no timing rule is given. So a TARGET on such a
step (n months, n years or n days with n > 1) is refused by every rule that walks target positions
(target_grid), as year_last_step refuses it for the cuts. A COLUMN on such a step is still walked
from this anchor: on a one-unit target every phase of the column's step meets some target position,
so the largest lag over positions (D23) sees the same phases whatever the anchor; only which month
lengths fall at which phase can differ, which moves a day-unit window by at most a day.
"""

import datetime as _dt
from fractions import Fraction
from math import ceil, floor
from numbers import Integral
from typing import Any, Iterator, Tuple

from treeroute.engine_constants import MONTHS_PER_YEAR

from .shapes import TimingRefusal, as_int, fact_value

DAY = "day"
MONTH = "month"
YEAR = "year"
UNITS = (DAY, MONTH, YEAR)

REGULAR = "regular"
COMPOSITE_OF_YEAR = "composite_of_year"
STATIC = "static"
EPOCH = "epoch"
IRREGULAR = "irregular"
KINDS = (REGULAR, COMPOSITE_OF_YEAR, STATIC, EPOCH, IRREGULAR)

# The reference calendar every "position in the year" rule walks (compute_lag, D23; the R17 offset,
# D12): REFERENCE_YEARS consecutive years from REFERENCE_FIRST_YEAR. Eight years hold two leap years
# and every pairing of a leap and a common year, so every month length and year length meets every
# neighbour; a century's common year only lengthens a run of common years, which adds no new length.
# The first year starts a 400-year Gregorian cycle, like year 1. A window reaching further than these
# eight years around a position is still walked exactly; only the set of positions is fixed here.
REFERENCE_FIRST_YEAR = 401
REFERENCE_YEARS = 8

# A regular n-day step is walked from this day ordinal (the calendar's first day). See the module
# docstring: it fixes only how the calendar is walked, never a lag between two tables on one step.
DAY_STEP_ORIGIN = 1


def to_date(day: int) -> _dt.date:
    try:
        return _dt.date.fromordinal(day)
    except (ValueError, OverflowError):
        raise TimingRefusal("R8", "day ordinal %r is outside the calendar" % (day,),
                            fix="check the period passed to the timing rule")


def day_of(year: int, month: int, day: int) -> int:
    try:
        return _dt.date(year, month, day).toordinal()
    except (ValueError, OverflowError):
        raise TimingRefusal("R8", "no calendar day %r-%r-%r" % (year, month, day),
                            fix="check the years passed to the timing rule")


def year_first_day(year: int) -> int:
    return day_of(year, 1, 1)


def year_last_day(year: int) -> int:
    return year_first_day(year + 1) - 1


def month_index(day: int) -> int:
    """0-based month count of the month holding ``day`` (year x months-per-year + month - 1)."""
    d = to_date(day)
    return d.year * MONTHS_PER_YEAR + d.month - 1


def month_first_day(index: int) -> int:
    year, month0 = divmod(index, MONTHS_PER_YEAR)
    return day_of(year, month0 + 1, 1)


def month_length(index: int) -> int:
    return month_first_day(index + 1) - month_first_day(index)


# ---------------------------------------------------------------------------------------------------
# Instants on the day line <-> the coordinate of a window unit
def to_unit(x: Fraction, unit: str) -> Fraction:
    """The instant ``x`` (day coordinate) in the coordinate of ``unit``."""
    if unit == DAY:
        return x
    day = floor(x)
    if unit == MONTH:
        index = month_index(day)
        return index + (x - month_first_day(index)) / month_length(index)
    if unit == YEAR:
        year = to_date(day).year
        first = year_first_day(year)
        return year + (x - first) / (year_first_day(year + 1) - first)
    raise TimingRefusal("R8", "unknown time unit %r" % (unit,), fix="use day, month or year")


def from_unit(u: Fraction, unit: str) -> Fraction:
    """The instant ``u`` (coordinate of ``unit``) on the day line."""
    if unit == DAY:
        return u
    whole = floor(u)
    if unit == MONTH:
        return month_first_day(whole) + (u - whole) * month_length(whole)
    if unit == YEAR:
        first = year_first_day(whole)
        return first + (u - whole) * (year_first_day(whole + 1) - first)
    raise TimingRefusal("R8", "unknown time unit %r" % (unit,), fix="use day, month or year")


def shift(x: Fraction, amount: Fraction, unit: str) -> Fraction:
    """The instant ``amount`` units after ``x`` (before, if negative), on the day line."""
    return from_unit(to_unit(x, unit) + amount, unit)


def first_day_holding(x: Fraction) -> int:
    """The whole day that holds the instant ``x`` (the first day of an interval starting at x)."""
    return floor(x)


def last_day_before(x: Fraction) -> int:
    """The whole day that holds the last instant before ``x`` (the last day of an interval ending at
    x, exclusive): a partly covered day counts."""
    return ceil(x) - 1


def exact(number: Any) -> Fraction:
    """An exact fraction of a fact's number (an integer, or a float read as its decimal text)."""
    if isinstance(number, Integral):
        return Fraction(int(number))
    return Fraction(repr(float(number)))


# ---------------------------------------------------------------------------------------------------
# Periods of a cadence
class CadenceGrid:
    """The periods (first_day, last_day) of one cadence, for walking a calendar."""

    def __init__(self, cadence: Any, what: str):
        if cadence is None:
            raise TimingRefusal("R8", "%s has no cadence" % what, fix="declare the cadence fact")
        self.what = what
        self.kind = fact_value(getattr(cadence, "kind", None), what + " cadence kind")
        if self.kind not in KINDS:
            raise TimingRefusal("R8", "%s has an unknown cadence kind %r" % (what, self.kind),
                                fix="declare one of %s" % ", ".join(KINDS))
        self.length = None
        self.unit = None
        if self.kind == REGULAR:
            self.length = as_int(getattr(cadence, "length", None), what + " cadence length")
            self.unit = fact_value(getattr(cadence, "unit", None), what + " cadence unit")
            if self.length < 1 or self.unit not in UNITS:
                raise TimingRefusal("R8", "%s has a regular cadence without a positive length and "
                                    "a unit (day, month, year)" % what,
                                    fix="declare the cadence {length, unit}")
        elif self.kind == COMPOSITE_OF_YEAR:
            days = getattr(cadence, "composite_days", None)
            if days is None:
                days = getattr(cadence, "length", None)
                unit = fact_value(getattr(cadence, "unit", None), what + " cadence unit")
                if unit not in (None, DAY):
                    raise TimingRefusal("R8", "%s: a composite-of-year cadence counts days" % what,
                                        fix="declare the composite length in days")
            self.length = as_int(days, what + " composite length")
            self.unit = DAY
            if self.length < 1:
                raise TimingRefusal("R8", "%s: composite length must be positive" % what,
                                    fix="declare the composite length in days")

    def containing(self, day: int) -> Tuple[int, int]:
        """The period that holds ``day``."""
        if self.kind == IRREGULAR:
            return day, day
        if self.kind == COMPOSITE_OF_YEAR:
            year = to_date(day).year
            first_of_year = year_first_day(year)
            start = first_of_year + ((day - first_of_year) // self.length) * self.length
            return start, min(start + self.length - 1, year_last_day(year))
        if self.kind == REGULAR:
            n = self.length
            if self.unit == DAY:
                start = DAY_STEP_ORIGIN + ((day - DAY_STEP_ORIGIN) // n) * n
                return start, start + n - 1
            if self.unit == MONTH:
                j = month_index(day) // n
                return month_first_day(j * n), month_first_day((j + 1) * n) - 1
            j = to_date(day).year // n
            return year_first_day(j * n), year_first_day((j + 1) * n) - 1
        raise TimingRefusal("R8", "%s has a %s cadence: it has no periods to walk"
                            % (self.what, self.kind), fix="only time-varying cadences have steps")

    def previous(self, period: Tuple[int, int]) -> Tuple[int, int]:
        return self.containing(period[0] - 1)

    def following(self, period: Tuple[int, int]) -> Tuple[int, int]:
        return self.containing(period[1] + 1)

    def inside(self, period: Tuple[int, int]) -> Tuple[Tuple[int, int], ...]:
        """Every period of this cadence that lies inside ``period`` (first_day, last_day), in order.

        Refuses a period of this cadence that straddles either edge of ``period``: its value is not
        inside that period (a finer step that does not nest, e.g. 16-day composites in a month).
        """
        first, last = period
        out = []
        current = self.containing(first)
        while current[0] <= last:
            if current[0] < first or current[1] > last:
                raise TimingRefusal("R8", "%s: its step %s straddles the edge of the period %s; its "
                                    "values do not nest in that period"
                                    % (self.what, describe_days(current), describe_days(period)),
                                    fix="aggregate only to a step its own steps nest in (plan 1.5)")
            out.append(current)
            current = self.following(current)
        return tuple(out)


def target_grid(cadence: Any, what: str, rule: str) -> CadenceGrid:
    """The grid of a TARGET whose positions a rule walks (compute_lag, the R17 offset).

    Refuses: a static or epoch cadence (no steps); a regular step longer than one unit (n months,
    n years or n days with n > 1), whose periods step_index counts from the target table's first
    position (D29): the rule is not given that origin, so walking its own anchor would place the
    periods differently from the data (see the module docstring).
    """
    grid = CadenceGrid(cadence, what)
    if grid.kind in (STATIC, EPOCH):
        raise TimingRefusal(rule, "%s has a %s cadence: it has no steps" % (what, grid.kind),
                            fix="R1 gives the target a grid or events")
    if grid.kind == REGULAR and grid.length > 1:
        raise TimingRefusal(rule, "%s: a regular step of %d %ss is indexed from the target table's "
                            "first position, which this rule is not given" % (what, grid.length,
                                                                             grid.unit),
                            fix="pass the step index origin (open item: signature gap, as for the "
                                "cuts)")
    return grid


_MONTH_ABBREVIATIONS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
                        "Dec")


def _month_day(day: int) -> str:
    d = to_date(day)
    return "%s %d" % (_MONTH_ABBREVIATIONS[d.month - 1], d.day)


def describe_days(period: Tuple[int, int]) -> str:
    """A (first_day, last_day) period as calendar text for a message: 'May 1 - May 31 of year Y'."""
    first, last = period
    a, b = to_date(first), to_date(last)
    if a.year == b.year:
        return "%s - %s of year %d" % (_month_day(first), _month_day(last), a.year)
    return "%s of year %d - %s of year %d" % (_month_day(first), a.year, _month_day(last), b.year)


def describe_reference_period(period: Tuple[int, int]) -> str:
    """A period of the reference calendar as a POSITION IN THE YEAR, for messages and traces: the
    reference years are synthetic, so they are printed as 'reference year k of REFERENCE_YEARS'."""
    first, last = period
    a, b = to_date(first), to_date(last)
    k_first = a.year - REFERENCE_FIRST_YEAR + 1
    k_last = b.year - REFERENCE_FIRST_YEAR + 1
    where = ("reference year %d of %d" % (k_first, REFERENCE_YEARS) if k_first == k_last else
             "reference years %d-%d of %d" % (k_first, k_last, REFERENCE_YEARS))
    return "%s - %s (%s; a position in the year, not a data date)" % (_month_day(first),
                                                                     _month_day(last), where)


def reference_periods(grid: CadenceGrid) -> Iterator[Tuple[int, int]]:
    """Every period of ``grid`` in the reference calendar, in order: the period holding the first
    reference day, then each following period that starts on or before the last reference day."""
    start = year_first_day(REFERENCE_FIRST_YEAR)
    stop = year_last_day(REFERENCE_FIRST_YEAR + REFERENCE_YEARS - 1)
    period = grid.containing(start)
    while period[0] <= stop:
        yield period
        period = grid.following(period)
