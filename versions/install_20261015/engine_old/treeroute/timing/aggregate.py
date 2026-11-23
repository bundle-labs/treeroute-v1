"""Content of a time aggregate, for R8 (plan 1.5 aggregate_time: the aggregate's "window and stamp
[are] computed from the aggregation span, never typed").

An aggregate of a column's values over the sub-periods inside one aggregate period describes every
content day that any of those values describes: from the earliest first day to the latest last day
of their content intervals (each value's own window and reach facts, timing.content_interval). A
value stored INSIDE the period can still describe content past its edge (a centred or filtered
monthly index; a composite that runs into the next year), so a calendar-year aggregate can reach
past the year end. That reach is what gives such an aggregate lag 1 on an annual target, by the one
R8 rule (D25 option a); computing the window from the calendar year alone would give lag 0, a leak.

The aggregate's own facts are written in the form of the reach ruling (owner rulings, part B item 8
(a)): a window equal to its stored step, stamped at the period end, plus reach_after_max /
reach_before_max in days. Each reach is the MAXIMUM over every aggregate period measured (D21's rule
for forward reach, applied to the aggregate), so one fact is safe in every period. A reach of 0 or
less is not written (a reach fact is positive): the window then claims the whole period, which
never places the content's end too early.
"""

from typing import Any, Dict, Iterable, Tuple

from .calendar import COMPOSITE_OF_YEAR, DAY, REGULAR, CadenceGrid, describe_days
from .content import content_interval
from .shapes import AggregateReach, TimingRefusal, as_period, name_of

AGGREGATE_STAMP = "period_end"
AGGREGATE_ALIGN = "backward"


def periods_inside(column_cadence: Any, period: Any) -> Tuple[Tuple[int, int], ...]:
    """Every period of the column's cadence that lies inside ``period`` (first_day, last_day): the
    stored values an aggregate over that period may read ("trailing only", plan 1.5).

    Refuses: a column step that straddles an edge of the period (it does not nest: aggregate only to
    a step it nests in); a static or epoch cadence (no periods).
    """
    what = "the column cadence"
    return CadenceGrid(column_cadence, what).inside(as_period(period, "aggregate period"))


def aggregate_content_interval(column: Any, sub_periods: Iterable[Any]) -> Tuple[int, int]:
    """(first_day, last_day) of the content an aggregate of the column over ``sub_periods``
    describes: the earliest first day and the latest last day of content_interval over them.

    Refuses: an empty sub-period list; whatever content_interval refuses.
    """
    spans = [content_interval(column, p) for p in sub_periods]
    if not spans:
        raise TimingRefusal("R8", "column %s: an aggregate over no sub-period has no content"
                            % name_of(column), fix="pass the sub-periods the aggregate reads")
    return min(first for first, _ in spans), max(last for _, last in spans)


def aggregate_reach(column: Any, spans: Iterable[Any]) -> AggregateReach:
    """How far the column's aggregate reaches before and after its own stored periods: for every
    (aggregate_period, sub_periods) pair, aggregate_content_interval against the aggregate period's
    first and last day; the MAXIMUM over the pairs (D21 applied to the aggregate), floored at 0.

    Pass every aggregate period the data has, each with the sub-periods actually aggregated (a
    growing season passes its months only).

    Refuses: no pair; a pair with no sub-period; a sub-period outside its aggregate period (an
    aggregate reads only values stored inside its period, plan 1.5); whatever content_interval
    refuses.
    """
    what = "column %s" % name_of(column)
    before = after = None                   # (largest reach so far, the aggregate period it is at)
    count = 0
    for pair in spans:
        try:
            aggregate_period, sub_periods = pair
        except (TypeError, ValueError):
            raise TypeError("%s: each span must be (aggregate_period, sub_periods), got %r"
                            % (what, pair))
        period = as_period(aggregate_period, "aggregate period of " + what)
        subs = [as_period(p, "sub-period of " + what) for p in sub_periods]
        for sub in subs:
            if sub[0] < period[0] or sub[1] > period[1]:
                raise TimingRefusal("R8", "%s: the sub-period %s lies outside the aggregate period "
                                    "%s" % (what, describe_days(sub), describe_days(period)),
                                    fix="an aggregate reads only values stored inside its period "
                                        "(plan 1.5, trailing only)")
        first, last = aggregate_content_interval(column, subs)
        count += 1
        if before is None or period[0] - first > before[0]:
            before = (period[0] - first, period)
        if after is None or last - period[1] > after[0]:
            after = (last - period[1], period)
    if count == 0:
        raise TimingRefusal("R8", "%s: no aggregate period to measure the reach on" % what,
                            fix="pass every aggregate period the data has, with its sub-periods")
    return AggregateReach(before_days=max(before[0], 0), after_days=max(after[0], 0),
                          worst_before_period=before[1], worst_after_period=after[1], spans=count)


def aggregate_window(reach: AggregateReach, aggregate_cadence: Any) -> Dict[str, Any]:
    """The aggregate's computed stamp and window, in the store catalog's form (package schema
    Window): {"stamp": "period_end", "window": {length, unit, align: "backward",
    reach_after_max / reach_before_max as {value, unit: "day"} when positive}}.

    The window equals the stored step: a regular step {n, unit}, or a composite-of-year step of d
    days (d days back from the period end: for a year's shorter last composite this claims days
    before the period's start, which only widens the content's start, never its end).

    Refuses: an aggregate cadence that is not a regular or composite-of-year step.
    """
    grid = CadenceGrid(aggregate_cadence, "the aggregate cadence")
    if grid.kind == REGULAR:
        length, unit = grid.length, grid.unit
    elif grid.kind == COMPOSITE_OF_YEAR:
        length, unit = grid.length, DAY
    else:
        raise TimingRefusal("R8", "an aggregate to a %s cadence has no step to hold its value"
                            % grid.kind, fix="aggregate to the target's grid step (plan 1.5)")
    window: Dict[str, Any] = {"length": length, "unit": unit, "align": AGGREGATE_ALIGN}
    if reach.after_days > 0:
        window["reach_after_max"] = {"value": reach.after_days, "unit": DAY}
    if reach.before_days > 0:
        window["reach_before_max"] = {"value": reach.before_days, "unit": DAY}
    return {"stamp": AGGREGATE_STAMP, "window": window}


__all__ = ["periods_inside", "aggregate_content_interval", "aggregate_reach", "aggregate_window"]
