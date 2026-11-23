"""R11: the fit cut and the inner guard's cut for every lead, in integer steps (grids) or days
(events), and the label rule. Every bound is inclusive ('at or before', D19).
"""

from typing import Any, Dict, Mapping, Tuple

from treeroute.engine_constants import MONTHS_PER_YEAR

from .calendar import (COMPOSITE_OF_YEAR, IRREGULAR, MONTH, REGULAR, YEAR, CadenceGrid,
                       year_first_day, year_last_day)
from .shapes import CutPair, TimingRefusal, as_int, fact_value

STEPS = "steps"
DAYS = "days"


def _lead(value: Any, what: str) -> int:
    lead = as_int(value, what)
    if lead < 0:
        raise TimingRefusal("R11", "%s is negative (%d)" % (what, lead),
                            fix="leads are 0 (the nowcast) or positive (R10)")
    return lead


# Provenance: pm25_forecast.py:190-192 (cut_of: min(T_DEC_train_end, T_DEC_train_end + 1 - L)).
def fit_cut_step(lead_steps: int, train_end_step: int) -> int:
    """Grid fit cut for lead L: the donor train end moved back by L-1 steps, never later than it.

    Rule: R11. cut(L) = train_end_step - (L - 1), capped at train_end_step, so the nowcast (lead 0)
    and lead 1 share the train end. Refuses: lead_steps < 0.
    """
    lead = _lead(lead_steps, "lead_steps")
    end = as_int(train_end_step, "train_end_step")
    return min(end, end - (lead - 1))


# Provenance: pm25_forecast.py:195-197 (inner_cut_of: the same rule from the inner-fit end).
def guard_cut_step(lead_steps: int, inner_fit_end_step: int) -> int:
    """Grid cut of the inner guard at lead L: the same rule as fit_cut_step, from the inner-fit end.

    Rule: R11. Every inner score row must be issued at or after this cut (G-FITCUT).
    Refuses: lead_steps < 0.
    """
    lead = _lead(lead_steps, "lead_steps")
    end = as_int(inner_fit_end_step, "inner_fit_end_step")
    return min(end, end - (lead - 1))


# Provenance: plan 2.1 R11 ("Labels reach the issue step at leads of 1 or more, and t-1 at lead 0").
def latest_label_step(target_step: int, lead_steps: int) -> int:
    """The newest label a row predicting step t may read at lead L (history, persistence).

    Rule: R11, R17. Lead L >= 1: the issue step t - L. Lead 0: t - 1. The R17 start offset
    (timing.target_reach_offset_steps) is subtracted by the history block, not here.
    Refuses: lead_steps < 0.
    """
    lead = _lead(lead_steps, "lead_steps")
    step = as_int(target_step, "target_step")
    return step - 1 if lead == 0 else step - lead


# Provenance: plan 2.1 R11 (events); plan 3.3 flag 13 (event leads in days). M8 under the fast track.
def event_fit_cut_day(lead_days: int, test_first_day: int, train_end_last_day: int) -> int:
    """Event fit cut for a lead in days: the first day of the test window minus L days.

    Rule: R11 (events). Lead L >= 1: test_first_day - L. Lead 0: the last day of the donor train
    end year. Refuses: lead_days < 0.
    """
    lead = _lead(lead_days, "lead_days")
    first = as_int(test_first_day, "test_first_day")
    end = as_int(train_end_last_day, "train_end_last_day")
    return end if lead == 0 else first - lead


# Provenance: plan 2.1 R11 (events: the inner guard's cut follows the same rule from the first day of
# the inner score window); D99 (lead 0: the last day of the inner-fit end year). M8 fast track.
def event_guard_cut_day(lead_days: int, inner_score_first_day: int,
                        inner_fit_end_last_day: int) -> int:
    """Event cut of the inner guard: the same rule from the first day of the inner score window.

    Rule: R11 (events). Lead L >= 1: inner_score_first_day - L. Lead 0: the last day of the
    inner-fit end year (D99). Refuses: lead_days < 0.
    """
    lead = _lead(lead_days, "lead_days")
    first = as_int(inner_score_first_day, "inner_score_first_day")
    end = as_int(inner_fit_end_last_day, "inner_fit_end_last_day")
    return end if lead == 0 else first - lead


# Provenance: plan 2.1 R11 ("labels dated at or before the cut whose own window has ended by then").
def label_usable(label_day: int, label_window_last_day: int, cut_day: int) -> bool:
    """True if a label may enter a fitted object at this cut: dated at or before the cut AND its own
    window ended by the cut, both inclusive. Applies to grid cuts too (D26), which drops the cut
    step's own label when the target window reaches past its step.

    Rule: R11, G-FITCUT. A pure predicate.
    """
    cut = as_int(cut_day, "cut_day")
    return (as_int(label_day, "label_day") <= cut
            and as_int(label_window_last_day, "label_window_last_day") <= cut)


# ---------------------------------------------------------------------------------------------------
def year_last_step(year: int, target_cadence: Any) -> int:
    """The integer step of the last step of a calendar year, in the form of io_science.step_index
    (plan R1; D28, source form): monthly = year x months-per-year + month, so the last step is
    year x months-per-year + months-per-year; annual = year; composite-of-year = year x composites
    per year + composite number (counted from 1, as months are), so the last step is year x
    composites per year + composites per year.

    Refuses: any other regular step (n months with n > 1, n years with n > 1, n days): its step
    index counts from the target table's first day (step_index 'fixed origin', D29), which the cut
    signature does not carry; a composite-of-year cadence without composites_per_year, or with a
    composites_per_year that is not the number of d-day composites in BOTH a common and a leap
    year (ceil(365 / d) = ceil(366 / d)): otherwise the step numbers have gaps and end - (L - 1) is
    not L - 1 real steps back; a static, epoch or irregular cadence.
    """
    year = as_int(year, "year")
    grid = CadenceGrid(target_cadence, "target")
    if grid.kind == REGULAR and grid.length == 1 and grid.unit == MONTH:
        return year * MONTHS_PER_YEAR + MONTHS_PER_YEAR
    if grid.kind == REGULAR and grid.length == 1 and grid.unit == YEAR:
        return year
    if grid.kind == COMPOSITE_OF_YEAR:
        per_year = getattr(target_cadence, "composites_per_year", None)
        if per_year is None:
            raise TimingRefusal("R11", "the composite-of-year cadence has no composites_per_year",
                                fix="R1 records the composites per year in the data")
        per_year = as_int(per_year, "composites_per_year")
        d = grid.length
        common_days = year_last_day(1) - year_first_day(1) + 1      # proleptic year 1: common
        leap_days = year_last_day(4) - year_first_day(4) + 1        # proleptic year 4: leap
        in_common, in_leap = -(-common_days // d), -(-leap_days // d)     # ceiling division
        if not per_year == in_common == in_leap:
            raise TimingRefusal("R11", "composites_per_year is %d, but %d-day composites number %d "
                                "in a common year and %d in a leap year; the step numbers would "
                                "have gaps" % (per_year, d, in_common, in_leap),
                                fix="R1: a composite length whose count per year is the same in "
                                    "every year, and composites_per_year equal to it")
        return year * per_year + per_year
    if grid.kind == REGULAR:
        raise TimingRefusal("R11", "a regular step of %d %s(s) is indexed from the target table's "
                            "first day, which the cut rule is not given" % (grid.length, grid.unit),
                            fix="pass the step index origin (open item: signature gap)")
    raise TimingRefusal("R11", "a %s cadence has no integer steps" % grid.kind,
                        fix="events take the day cuts")


def _year_list(values: Any, what: str) -> Tuple[int, ...]:
    years = tuple(as_int(y, what) for y in (values or ()))
    if not years:
        raise TimingRefusal("R11", "%s is empty" % what, fix="pass the R5/R7 windows")
    return years


def _window_years(windows: Any) -> Tuple[int, int, int, int]:
    """(train end, inner-fit end, first test year, first inner score year), checked against the R6
    and R7 definitions the cut formulas depend on: train end = the year before the test window
    (R6); inner fit ends the year before the score window (R7); the score window lies at or before
    the train end (R6: every router row is at or before it). A malformed Windows would otherwise
    let test-window labels into every fitted object without a refusal."""
    train_end = as_int(getattr(windows, "train_end", None), "windows.train_end")
    inner_fit = getattr(windows, "inner_fit", None)
    if inner_fit is None or len(inner_fit) != 2:
        raise TimingRefusal("R11", "windows.inner_fit must be (first year, last year)",
                            fix="pass the R7 windows")
    inner_fit_end = as_int(inner_fit[1], "windows.inner_fit last year")
    test_years = _year_list(getattr(windows, "test_years", None), "windows.test_years")
    inner_score = _year_list(getattr(windows, "inner_score", None), "windows.inner_score")
    test_first, score_first = min(test_years), min(inner_score)
    if test_first != train_end + 1 or score_first != inner_fit_end + 1:
        raise TimingRefusal("R11", "the windows are not adjacent: train end %d / first test year "
                            "%d, inner-fit end %d / first inner score year %d"
                            % (train_end, test_first, inner_fit_end, score_first),
                            fix="R6: train end = the year before the test window; R7: inner fit "
                                "ends the year before the score window")
    if max(inner_score) > train_end:
        raise TimingRefusal("R11", "the inner score window runs to %d, after the train end %d"
                            % (max(inner_score), train_end),
                            fix="R6/R7: the inner score window lies at or before the train end")
    return train_end, inner_fit_end, test_first, score_first


# Provenance: plan 2.1 R11 ("Both: FitContext applies the cuts to every fitted object").
def cuts_for_leads(windows: Any, leads: Any, target_cadence: Any) -> Mapping[int, CutPair]:
    """Both cuts (fit and inner guard) for lead 0 and every derived lead.

    Rule: R11. Grids: fit_cut_step and guard_cut_step per lead, from the last step of the donor
    train end year (R6) and of the inner-fit end year (R7) (see year_last_step). Events: the day
    rules, from 1 January of the first test year and of the first inner score year, and 31 December
    of the train end year and of the inner-fit end year. For both, the windows must satisfy R6 and
    R7 as the formulas assume (see _window_years). Lead 0 is always present. Returns
    {lead: CutPair}, sorted by lead; each CutPair carries the lead plan's own lead_unit.

    Refuses: a lead plan whose unit does not match the cadence (steps for grids, days for events);
    a listed lead that is not positive (lead 0 is the contract, never listed) or listed twice;
    windows that break R6 / R7 (train end not the year before the test window, inner fit not ending
    the year before the score window, a score window past the train end) or are malformed; a
    static or epoch target; whatever year_last_step refuses.
    """
    grid = CadenceGrid(target_cadence, "target")
    lead_unit = getattr(leads, "lead_unit", None)
    unit = fact_value(lead_unit, "lead plan unit")
    listed = [as_int(lead, "lead") for lead in (getattr(leads, "leads", None) or ())]
    if any(lead <= 0 for lead in listed) or len(set(listed)) != len(listed):
        raise TimingRefusal("R11", "the lead plan lists %r: leads must be positive and distinct "
                            "(lead 0 is the contract and is never listed)" % (listed,),
                            fix="pass the R10 lead plan")
    train_end, inner_fit_end, test_first, score_first = _window_years(windows)
    out: Dict[int, CutPair] = {}
    if grid.kind == IRREGULAR:
        if unit != DAYS:
            raise TimingRefusal("R11", "events take leads in days, the lead plan says %r" % unit,
                                fix="R10 gives event leads in days")
        test_first_day, score_first_day = year_first_day(test_first), year_first_day(score_first)
        train_end_day, inner_fit_end_day = year_last_day(train_end), year_last_day(inner_fit_end)
        for lead in [0] + sorted(listed):
            out[lead] = CutPair(lead=lead, lead_unit=lead_unit,
                                fit_cut=event_fit_cut_day(lead, test_first_day, train_end_day),
                                guard_cut=event_guard_cut_day(lead, score_first_day,
                                                              inner_fit_end_day))
        return out
    if grid.kind not in (REGULAR, COMPOSITE_OF_YEAR):
        raise TimingRefusal("R11", "a %s target has no cuts" % grid.kind,
                            fix="R1 gives the target a grid or events")
    if unit != STEPS:
        raise TimingRefusal("R11", "a grid takes leads in steps, the lead plan says %r" % unit,
                            fix="R10 gives grid leads in steps")
    train_end_step = year_last_step(train_end, target_cadence)
    inner_fit_end_step = year_last_step(inner_fit_end, target_cadence)
    for lead in [0] + sorted(listed):
        out[lead] = CutPair(lead=lead, lead_unit=lead_unit,
                            fit_cut=fit_cut_step(lead, train_end_step),
                            guard_cut=guard_cut_step(lead, inner_fit_end_step))
    return out
