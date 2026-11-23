"""Content time: what a stored value describes, how far it reaches, and the reference instant (R8).

Every rule here follows CONTENT time only. Release and snapshot dates are recorded and printed
elsewhere, never read here (Q2).

How a window fact becomes content (whole-day closed intervals, D19; exact arithmetic in
timing.calendar):
    The stamp places the value's instant in its stored period: period_start = the start of the
    period's first day, period_end = the end of its last day, period_centre = the midpoint of the
    two, measured in the window's unit. event_date stamps a one-day period: a backward window ends
    at the end of that day, a forward window starts at its start, a centred window is centred on it.
    A window {length, unit, align} spans content around the instant: backward ends at it, forward
    starts at it, centred straddles it. align=unknown with a signed max_length w is the worst case,
    a FORWARD window of length w starting at the stamp (D20). The optional reach facts widen the
    window's content: reach_after_max past its end, reach_before_max before its start (owner
    rulings, part B item 8 (a)).
"""

from fractions import Fraction
from typing import Any, Iterable, Optional, Tuple

from .calendar import (STATIC, UNITS, describe_days, exact, first_day_holding, from_unit,
                       last_day_before, reference_periods, shift, target_grid, to_unit)
from .shapes import TimingRefusal, as_period, as_positive_number, fact_value, name_of

BACKWARD = "backward"
CENTRED = "centred"
FORWARD = "forward"
UNKNOWN = "unknown"
ALIGNS = (BACKWARD, CENTRED, FORWARD, UNKNOWN)

PERIOD_START = "period_start"
PERIOD_CENTRE = "period_centre"
PERIOD_END = "period_end"
EVENT_DATE = "event_date"

ASSUMED = "assumed"
NOWCAST = "nowcast"
ISSUE_STEP = "issue_step"
REFERENCE_KINDS = (NOWCAST, ISSUE_STEP)

# Every step walk (a lag, the R17 offset) stops with a refusal past this many steps rather than
# loop; a finite window fact never gets there.
MAX_WALK_STEPS = 10000


def _window_status(window: Any, owner: Any) -> Optional[str]:
    """fact_status of a window: its own when it carries one, else its column's."""
    status = getattr(window, "fact_status", None)
    if status is None:
        status = getattr(owner, "fact_status", None)
    return fact_value(status, "fact_status")


def _reach(window: Any, field: str, what: str) -> Optional[Tuple[Fraction, str]]:
    reach = getattr(window, field, None)
    if reach is None:
        return None
    value = as_positive_number(getattr(reach, "value", None), "%s %s value" % (what, field))
    unit = fact_value(getattr(reach, "unit", None), "%s %s unit" % (what, field))
    if unit not in UNITS:
        raise TimingRefusal("R8", "%s: %s has no unit (day, month, year)" % (what, field),
                            fix="declare %s as {value, unit}" % field)
    return exact(value), unit


def window_content(stamp: Any, window: Any, period: Tuple[int, int], status: Optional[str],
                   what: str) -> Tuple[int, int]:
    """(first_day, last_day) of the content a value stored for ``period`` describes."""
    if window is None:
        raise TimingRefusal("R8", "%s has no window fact" % what,
                            fix="declare its window {length, unit, align} (plan 1.3)")
    align = fact_value(getattr(window, "align", None), what + " window align")
    unit = fact_value(getattr(window, "unit", None), what + " window unit")
    if align == UNKNOWN:
        bound = getattr(window, "max_length", None)
        if bound is None:
            raise TimingRefusal("G-LAG", "%s: unknown window with no signed bound; the column is "
                                "refused at lag 0 (R8)" % what,
                                fix="find the window, or sign a bound (align: unknown, max_length, "
                                    "fact_status: assumed)")
        if status != ASSUMED:
            raise TimingRefusal("G-LAG", "%s: the bound max_length of an unknown window is not "
                                "signed (fact_status %r, not 'assumed')" % (what, status),
                                fix="the owner signs the bound as 'assumed' (plan 1.3)")
        length, align = bound, FORWARD          # D20: the worst case, forward from the stamp
    elif align in (BACKWARD, CENTRED, FORWARD):
        length = getattr(window, "length", None)
        if length is None:
            raise TimingRefusal("R8", "%s: a %s window with no length" % (what, align),
                                fix="declare the window length")
    else:
        raise TimingRefusal("R8", "%s: unknown window align %r" % (what, align),
                            fix="declare one of %s" % ", ".join(ALIGNS))
    if unit not in UNITS:
        raise TimingRefusal("R8", "%s: the window has no unit (day, month, year)" % what,
                            fix="declare the window unit")
    size = exact(as_positive_number(length, what + " window length"))

    first, last = period
    start = to_unit(Fraction(first), unit)
    end = to_unit(Fraction(last + 1), unit)
    centre = (start + end) / 2
    stamp = fact_value(stamp, what + " stamp")
    if stamp == PERIOD_START:
        anchor = start
    elif stamp == PERIOD_END:
        anchor = end
    elif stamp == PERIOD_CENTRE:
        anchor = centre
    elif stamp == EVENT_DATE:
        anchor = end if align == BACKWARD else (start if align == FORWARD else centre)
    else:
        raise TimingRefusal("R8", "%s: unknown stamp %r" % (what, stamp),
                            fix="declare period_start, period_centre, period_end or event_date")

    if align == BACKWARD:
        low, high = anchor - size, anchor
    elif align == FORWARD:
        low, high = anchor, anchor + size
    else:
        low, high = anchor - size / 2, anchor + size / 2
    low_day, high_day = from_unit(low, unit), from_unit(high, unit)

    after = _reach(window, "reach_after_max", what)
    if after is not None:
        high_day = shift(high_day, after[0], after[1])
    before = _reach(window, "reach_before_max", what)
    if before is not None:
        low_day = shift(low_day, -before[0], before[1])
    return first_day_holding(low_day), last_day_before(high_day)


# ---------------------------------------------------------------------------------------------------
# Provenance: plan 1.3 (window fact, align unknown + max_length signed 'assumed').
def content_interval(column: Any, period: Any) -> Tuple[int, int]:
    """First and last day of content that a value stored for one period actually describes.

    Rule: R8 (input). Contract: see the module docstring and the approved signature (D20: an
    unknown window with a signed max_length w is a FORWARD window of length w from the stamp).

    Refuses: align=UNKNOWN without max_length; align=UNKNOWN with a max_length whose fact_status is
    not 'assumed' (the window's own fact_status, else the column's); a window with no length on a
    time-varying column; a static column (no content time).
    """
    what = "column %s" % name_of(column)
    first_last = as_period(period, "period of " + what)
    cadence = getattr(column, "cadence", None)
    if cadence is not None and fact_value(getattr(cadence, "kind", None),
                                          what + " cadence kind") == STATIC:
        raise TimingRefusal("R8", "%s is static: it has no content time and no lag" % what,
                            fix="timing rules take time-varying columns only")
    window = getattr(column, "window", None)
    return window_content(getattr(column, "stamp", None), window, first_last,
                          _window_status(window, column), what)


# Provenance: plan 1.4 (keep_unreviewed needs no forward reach), plan 5 G-LAG.
def forward_reach_days(column: Any, period: Any) -> int:
    """How many days a column's content reaches past the end of its own stored period.

    Rule: R8, G-LAG, A5. content last_day minus period last_day; 0 or negative means none.
    Refuses: whatever content_interval refuses.
    """
    first_last = as_period(period, "period of column %s" % name_of(column))
    return content_interval(column, first_last)[1] - first_last[1]


def max_forward_reach_days(column: Any, periods: Iterable[Any]) -> int:
    """D21: forward reach measured on every period the column has in the data; the MAXIMUM.

    Refuses: an empty period list, and whatever content_interval refuses.
    """
    values = [forward_reach_days(column, p) for p in periods]
    if not values:
        raise TimingRefusal("R8", "column %s: no period to measure forward reach on"
                            % name_of(column), fix="pass every period the column has in the data")
    return max(values)


# ---------------------------------------------------------------------------------------------------
def check_target_window(target: Any) -> None:
    """Refuse an unknown target window (align unknown, or no length): R8 and R17 need it."""
    what = "target %s" % name_of(target)
    window = getattr(target, "window", None)
    if window is None:
        raise TimingRefusal("R8", "%s has no window fact" % what,
                            fix="declare the target's own window and stamp (plan 1.3)")
    align = fact_value(getattr(window, "align", None), what + " window align")
    if align == UNKNOWN or getattr(window, "length", None) is None:
        raise TimingRefusal("R8", "%s: unknown target window (align %r); the reference instant "
                            "and the history block need it (R8, R17)" % (what, align),
                            fix="sign the target's window fact, with reach_after_max / "
                                "reach_before_max where its content crosses the step edge")


def reference_kind(kind: Any) -> str:
    value = fact_value(kind, "reference kind")
    if value not in REFERENCE_KINDS:
        raise TimingRefusal("R8", "unknown reference kind %r" % (value,),
                            fix="use nowcast or issue_step")
    return value


# Provenance: plan 2.1 R8.
def reference_day(target: Any, row_period: Any, kind: Any, issue_period: Any = None) -> int:
    """The instant a feature row must not look past: end of the target's own window (nowcast) or
    end of the issue step (lead L).

    Rule: R8. NOWCAST: the last day of the target's own content for that row, reach facts included
    (the composite window when it reaches past its step). ISSUE_STEP: the last day of the issue
    period. Events: the end of the event's own window (nowcast), or the issue date, passed as the
    one-day issue period (lead).

    Refuses: an unknown target window (R17 refuses it too); kind=ISSUE_STEP without issue_period;
    an issue period that ends after the row's own period (the issue step is the row's step at lead
    0 and earlier at a lead; a later one would move the reference into the future of the row).
    """
    what = "target %s" % name_of(target)
    kind = reference_kind(kind)
    row = as_period(row_period, "row period of " + what)
    check_target_window(target)
    if kind == NOWCAST:
        window = getattr(target, "window", None)
        return window_content(getattr(target, "stamp", None), window, row,
                              _window_status(window, target), what)[1]
    if issue_period is None:
        raise TimingRefusal("R8", "%s: the issue-step reference needs the issue period" % what,
                            fix="pass issue_period (the issue step; for events the issue date)")
    issue = as_period(issue_period, "issue period of " + what)
    if issue[1] > row[1]:
        raise TimingRefusal("R8", "%s: the issue period (%s) ends after the row's own period (%s); "
                            "the issue step is never later than the step it predicts"
                            % (what, describe_days(issue), describe_days(row)),
                            fix="pass the issue step of this row (the row itself at lead 0, L steps "
                                "earlier at lead L); check the argument order")
    return issue[1]


def target_content(target: Any, row_period: Any) -> Tuple[int, int]:
    """(first_day, last_day) of the target's own content for one row (its window and reach facts)."""
    what = "target %s" % name_of(target)
    row = as_period(row_period, "row period of " + what)
    check_target_window(target)
    window = getattr(target, "window", None)
    return window_content(getattr(target, "stamp", None), window, row,
                          _window_status(window, target), what)


# Provenance: plan 2.1 R17 ("If the target's own window reaches past its step ... the block starts
# one more step back, computed from the target's window fact"); D12 (accepted default).
def target_reach_offset_steps(target: Any, target_cadence: Any) -> int:
    """D12: the number of whole steps the target's own window reaches past its step, rounded up.

    For every target period of a reference calendar (see timing.calendar.reference_periods), count
    the steps after the period that its content still reaches into; the MAXIMUM over the positions
    in the year is returned (a spill that happens in any month counts). 0 means the content ends
    inside its own step. Irregular (event) targets count one-day steps.

    Rule: R17 (start offset of the history block), used by the history spec and by
    timing.latest_label_step's callers. Refuses: an unknown target window; a static or epoch
    target cadence; a regular target step longer than one unit (its periods are indexed from the
    target table's first position, which this rule is not given: see timing.calendar.target_grid).
    """
    what = "target %s" % name_of(target)
    check_target_window(target)
    grid = target_grid(target_cadence, what, "R17")
    worst = 0
    for period in reference_periods(grid):
        last = target_content(target, period)[1]
        steps, step = 0, period
        while last > step[1]:
            step = grid.following(step)
            steps += 1
            if steps > MAX_WALK_STEPS:
                raise TimingRefusal("R17", "%s: the window reaches more than %d steps past its "
                                    "step" % (what, MAX_WALK_STEPS), fix="check the window fact")
        worst = max(worst, steps)
    return worst


__all__ = ["content_interval", "forward_reach_days", "max_forward_reach_days", "reference_day",
           "target_content", "target_reach_offset_steps", "check_target_window", "window_content",
           "reference_kind"]
