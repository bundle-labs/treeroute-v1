"""R8: the one fixed lag of a column, computed from its facts. Nothing types a lag.

How the lag is found (approved contract, decisions D19, D22-D25):
    For every target period P of the reference calendar (every position in the year, D23) and for
    both references (D24):
        NOWCAST     the reference is the last day of the target's own content for P (its window and
                    reach facts);
        ISSUE_STEP  P is the issue step whose feature row is read at a lead, and the reference is
                    P's last day.
    The column's value for P is the one stored for the column period that holds P (the same period
    on the target's own step; the calendar year on a monthly target for an annual column). The lag
    at that position is the smallest k >= 0 such that the value stored k column steps earlier has
    content ending at or before the reference (inclusive, D19). Steps are the COLUMN's own (D22).
    The fixed lag is the largest over positions and references, so one number is safe at every
    position and every lead (D23, D24). A co-measured column, or one listed in the target's
    computed_from, gets at least 1 step. There is no annual clause: on a sub-annual target an annual
    column comes out at year -1, and on an annual target a same-year annual value stays at lag 0
    unless its facts reach past the target year (D25 option a), both by this one rule.
"""

from typing import Any, Dict, Tuple

from .calendar import (EPOCH, IRREGULAR, STATIC, CadenceGrid, describe_reference_period,
                       reference_periods, target_grid)
from .content import ISSUE_STEP, MAX_WALK_STEPS, NOWCAST, content_interval, reference_day, \
    reference_kind
from .shapes import Lag, LagTrace, TimingRefusal, name_of

CO_MEASURED = "co_measured"
COMPUTED_FROM = "computed_from"
CO_MEASURED_FACT = "co_measured_with_target"


def _column_grid(column: Any, what: str) -> CadenceGrid:
    grid = CadenceGrid(getattr(column, "cadence", None), what)
    if grid.kind == STATIC:
        raise TimingRefusal("R8", "%s is static: static columns have no lag" % what,
                            fix="R8 lags time-varying columns only")
    if grid.kind == EPOCH:
        raise TimingRefusal("G-EPOCH", "%s has an epoch cadence: it is handled by G-EPOCH and the "
                            "freeze epoch (R9), not by a lag" % what,
                            fix="give it a 'freeze' verdict, or ban it")
    if grid.kind == IRREGULAR:
        raise TimingRefusal("R8", "%s is irregular: it has no steps to lag by; event-dated drivers "
                            "are joined as of each row's issue date" % what,
                            fix="join it as of the issue date (R8 events)")
    return grid


def _floor_reasons(column: Any, target: Any, what: str) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """(the floor reasons that apply, the facts the floor needed that are unanswered)."""
    reasons, unanswered = [], []
    co_measured = getattr(column, CO_MEASURED_FACT, None)
    if co_measured is None:
        unanswered.append(CO_MEASURED_FACT)       # G-FACTS blocks it at the headline
    elif not isinstance(co_measured, bool):
        raise TimingRefusal("R8", "%s: %s must be true or false, got %r"
                            % (what, CO_MEASURED_FACT, co_measured),
                            fix="declare %s as true or false in the package catalog"
                                % CO_MEASURED_FACT)
    elif co_measured:
        reasons.append(CO_MEASURED)
    computed_from = getattr(target, "computed_from", None) or ()
    if isinstance(computed_from, str):
        computed_from = (computed_from,)
    if getattr(column, "name", None) in tuple(computed_from):
        reasons.append(COMPUTED_FROM)
    return tuple(reasons), tuple(unanswered)


# Provenance: plan 2.1 R8; ruled cases Q2, Q3 a, Q38 b; 9.1 item 3 (D25 option a, owner ruling).
def lag_trace(column: Any, target: Any, target_cadence: Any) -> LagTrace:
    """compute_lag's value with what it read: per-reference maxima, the positions where they are
    reached, the content lag before the floor and the floor reason (derived.json inputs, margins).

    Refuses: whatever compute_lag refuses.
    """
    name = name_of(column)
    what = "column %s" % name
    column_grid = _column_grid(column, what)
    reasons, unanswered = _floor_reasons(column, target, what)
    walked = target_grid(target_cadence, "target %s" % name_of(target), "R8")

    ends: Dict[Tuple[int, int], int] = {}

    def content_end(period: Tuple[int, int]) -> int:
        if period not in ends:
            ends[period] = content_interval(column, period)[1]
        return ends[period]

    best = {NOWCAST: (-1, None), ISSUE_STEP: (-1, None)}
    positions = 0
    for period in reference_periods(walked):
        positions += 1
        aligned = column_grid.containing(period[0])
        if aligned[1] < period[1]:
            raise TimingRefusal(
                "R8", "%s: its step does not hold the target's step (the target step %s lies in no "
                "single column period); a finer or overlapping column has no value per target row"
                % (what, describe_reference_period(period)),
                fix="aggregate it to the target's step first (aggregate_time, plan 1.5)")
        references = {NOWCAST: reference_day(target, period, NOWCAST),
                      ISSUE_STEP: reference_day(target, period, ISSUE_STEP, issue_period=period)}
        for kind, reference in references.items():
            steps, source = 0, aligned
            while content_end(source) > reference:
                source = column_grid.previous(source)
                steps += 1
                if steps > MAX_WALK_STEPS:
                    raise TimingRefusal("R8", "%s: no value within %d steps has content at or "
                                        "before the reference" % (what, MAX_WALK_STEPS),
                                        fix="check the column's window fact")
            if steps > best[kind][0]:
                best[kind] = (steps, period)

    content_steps = max(best[NOWCAST][0], best[ISSUE_STEP][0])
    steps, floor_reason = content_steps, None
    if reasons and content_steps < 1:
        steps, floor_reason = 1, "+".join(reasons)
    return LagTrace(column=name, steps=steps, content_steps=content_steps,
                    nowcast_steps=best[NOWCAST][0], issue_steps=best[ISSUE_STEP][0],
                    worst_nowcast_period=best[NOWCAST][1], worst_issue_period=best[ISSUE_STEP][1],
                    worst_nowcast_position=describe_reference_period(best[NOWCAST][1]),
                    worst_issue_position=describe_reference_period(best[ISSUE_STEP][1]),
                    positions=positions, floor_reason=floor_reason, unanswered=unanswered)


# Provenance: plan 2.1 R8; ruled cases Q2 (centred indices lagged), Q3 a (annual columns at year -1
# on monthly targets), Q38 b (co_measured burn column at lag 1); 9.1 item 3 (annual target reading).
def compute_lag(column: Any, target: Any, target_cadence: Any, reference: Any) -> Lag:
    """The one fixed lag of a column: the smallest whole number of the column's steps that puts its
    newest content at or before the reference instant.

    Rule: R8 (module docstring). D24: the returned lag is the larger of the NOWCAST and ISSUE_STEP
    results, so it is the same number whichever ``reference`` is passed; ``reference`` must still
    name one of the two. lag_trace gives each reference's own value.

    Refuses: align UNKNOWN with no signed bound ("refused at lag 0", G-LAG); an EPOCH column
    (G-EPOCH, freeze); a static column (no lag); an irregular column (joined as of the issue date);
    a column whose step does not hold the target's step (aggregate it first); an unknown target
    window; a static or epoch target cadence, or a regular target step longer than one unit (its
    periods are indexed from the target table's first position, which the rule is not given); a
    co_measured_with_target that is neither true, false nor unanswered (None; recorded by lag_trace).
    """
    reference_kind(reference)
    trace = lag_trace(column, target, target_cadence)
    return Lag(column=trace.column, steps=trace.steps,
               column_cadence=getattr(column, "cadence", None), floor_reason=trace.floor_reason)
