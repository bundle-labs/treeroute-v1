"""Content of a time aggregate (plan 1.5 aggregate_time: the aggregate's window and stamp are computed
from the aggregation span, never typed), and the lags it gives on an annual target (R8, D25 a).

A calendar-year aggregate of a value whose content reaches past its month (a centred index, a
filtered one, a composite running into January) reaches past the year: lag 1 year. Computed from
the calendar year alone it would be lag 0, a leak.
"""

import datetime as dt

import pytest

from test_timing_facts import (A, ANNUAL_TARGET, DAILY, EVENTS, MONTH, STATIC, S, U, YEAR, column,
                               composite, day, month_period, win, year_period)
from treeroute.package import schema as SC
from treeroute.timing import (AggregateReach, Reach, TimingRefusal, aggregate_content_interval,
                              aggregate_reach, aggregate_window, compute_lag, periods_inside)

YEARS = range(2001, 2024)


def spans(col, years=YEARS, months=None):
    out = []
    for y in years:
        period = year_period(y)
        subs = periods_inside(col.cadence, period)
        if months is not None:
            subs = tuple(s for s in subs if dt.date.fromordinal(s[0]).month in months)
        out.append((period, subs))
    return out


def aggregate_column(col, years=YEARS, months=None):
    fact = aggregate_window(aggregate_reach(col, spans(col, years, months)), YEAR)
    return column(col.name + "_annual", cadence=YEAR, stamp=fact["stamp"],
                  window=SC.Window.model_validate(fact["window"]))


def annual_lag(col, months=None):
    return compute_lag(aggregate_column(col, months=months), ANNUAL_TARGET, YEAR, "nowcast").steps


def idx(name, window):
    return column(name, stamp=S.PERIOD_CENTRE, window=window)


# ---- periods_inside ----
def test_months_inside_a_year():
    months = periods_inside(MONTH, year_period(2020))
    assert len(months) == 12 and months[0] == month_period(2020, 1) \
        and months[-1] == month_period(2020, 12)
    assert len(periods_inside(DAILY, month_period(2020, 2))) == 29


def test_composites_inside_a_year_end_with_the_short_one():
    comps = periods_inside(composite(16, 23), year_period(2019))
    assert len(comps) == 23 and comps[-1][1] == day(2019, 12, 31)
    assert comps[-1][1] - comps[-1][0] + 1 == 365 - 22 * 16


def test_a_step_that_does_not_nest_is_refused():
    with pytest.raises(TimingRefusal):
        periods_inside(composite(16, 23), month_period(2019, 2))   # composites straddle months
    with pytest.raises(TimingRefusal):
        periods_inside(STATIC, year_period(2019))


# ---- aggregate_content_interval ----
def test_aggregate_content_is_the_union_of_the_values_content():
    oni_seeded = idx("oni", win(3))
    assert aggregate_content_interval(oni_seeded, periods_inside(MONTH, year_period(2019))) == \
        (day(2018, 12, 1), day(2020, 1, 31))
    assert aggregate_content_interval(column("m"), periods_inside(MONTH, year_period(2019))) == \
        year_period(2019)
    with pytest.raises(TimingRefusal):
        aggregate_content_interval(column("m"), [])


# ---- aggregate_reach ----
def test_reach_is_the_largest_over_the_aggregate_periods():
    r = aggregate_reach(idx("co2", win(3)), spans(idx("co2", win(3))))
    assert r == AggregateReach(before_days=31, after_days=31, worst_before_period=year_period(2001),
                               worst_after_period=year_period(2001), spans=len(YEARS))
    # the filtered oni's December reaches the end of March: 91 days after a year before a leap year
    r = aggregate_reach(idx("oni", win(7)), spans(idx("oni", win(7))))
    assert r.after_days == 91 and r.worst_after_period == year_period(2003)


def test_content_inside_the_period_gives_no_reach():
    r = aggregate_reach(column("m"), spans(column("m")))
    assert (r.before_days, r.after_days) == (0, 0)
    # a growing season inside the year: the content ends before the year does (floored at 0)
    r = aggregate_reach(column("m"), spans(column("m"), months=range(6, 10)))
    assert (r.before_days, r.after_days) == (0, 0)


def test_reach_refusals():
    with pytest.raises(TimingRefusal):
        aggregate_reach(column("m"), [])                                        # no period
    with pytest.raises(TimingRefusal):
        aggregate_reach(column("m"), [(year_period(2019), ())])                 # no sub-period
    with pytest.raises(TimingRefusal):                                          # outside its period
        aggregate_reach(column("m"), [(year_period(2019), (month_period(2020, 1),))])
    with pytest.raises(TypeError) as info:
        aggregate_reach(column("m"), [5])                                       # not a pair
    assert "each span" in str(info.value)
    with pytest.raises(TypeError):
        aggregate_reach(column("m"), [year_period(2019)])        # a bare period: not a sub-period list
    with pytest.raises(TimingRefusal):                                          # unknown window
        aggregate_reach(idx("t", win(None, U.MONTH, A.UNKNOWN)), spans(column("m"), years=[2019]))


# ---- aggregate_window: the store catalog's form ----
def test_window_fact_forms_validate_in_the_schema():
    plain = aggregate_window(AggregateReach(0, 0, year_period(2019), year_period(2019), 1), YEAR)
    assert plain == {"stamp": "period_end",
                     "window": {"length": 1, "unit": "year", "align": "backward"}}
    reaching = aggregate_window(AggregateReach(3, 91, year_period(2019), year_period(2019), 1), YEAR)
    assert reaching["window"]["reach_after_max"] == {"value": 91, "unit": "day"}
    assert reaching["window"]["reach_before_max"] == {"value": 3, "unit": "day"}
    for fact in (plain, reaching):
        SC.Window.model_validate(fact["window"])
    comp = aggregate_window(AggregateReach(0, 2, year_period(2019), year_period(2019), 1),
                            SC.Cadence.model_validate({"kind": "composite_of_year", "length": 16,
                                                       "unit": "day"}))
    assert comp["window"] == {"length": 16, "unit": "day", "align": "backward",
                              "reach_after_max": {"value": 2, "unit": "day"}}


@pytest.mark.parametrize("cadence", [EVENTS, STATIC])
def test_window_fact_refuses_a_cadence_without_steps(cadence):
    with pytest.raises(TimingRefusal):
        aggregate_window(AggregateReach(0, 0, year_period(2019), year_period(2019), 1), cadence)


# ---- lags through the path (R8 on the annual target) ----
def test_same_year_aggregate_of_a_plain_month_stays_at_lag_zero():
    assert annual_lag(column("m")) == 0                                          # D25 (a)


def test_seeded_oni_annual_mean_lags_one_year():
    # December's 3-month centred season reaches January: lag 1 under every ruling
    assert annual_lag(idx("oni", win(3))) == 1


@pytest.mark.parametrize("name,window", [
    ("nino34", win(5)), ("sst_anom_atl3", win(5)), ("oni", win(7)), ("tni", win(7)),
    ("co2", win(3)), ("V11", win(1, after=Reach(15, "day"), before=Reach(15, "day")))])
def test_ruled_windows_give_one_year_as_annual_aggregates(name, window):
    assert annual_lag(idx(name, window)) == 1


def test_calendar_year_window_alone_would_leak():
    # the aggregate written as the calendar year without its reach: lag 0, the leak the path prevents
    typed = column("oni_annual", cadence=YEAR, stamp=S.PERIOD_END, window=win(1, U.YEAR, A.BACKWARD))
    assert compute_lag(typed, ANNUAL_TARGET, YEAR, "nowcast").steps == 0


def test_growing_season_aggregates():
    centred = idx("c", win(3))
    assert annual_lag(centred, months=range(6, 10)) == 0       # Jun-Sep content ends in October
    assert annual_lag(centred, months=range(10, 13)) == 1      # Oct-Dec content reaches January
