"""Content time, forward reach, the reference instant and the R17 start offset (treeroute.timing).

Every branch of content_interval (stamp x align, the unknown-window bound, the reach facts, the
refusals), forward reach (D21), reference_day (NOWCAST / ISSUE_STEP, events) and the D12 offset.
Whole-day closed intervals, 'at or before' inclusive (D19).
"""

from types import SimpleNamespace as NS

import pytest

from test_timing_facts import (A, C, DAILY, EVENTS, MONTH, MONTHLY_TARGET, PLAIN_MONTH,
                               REACH_TARGET, STATIC, S, U, YEAR, column, composite, day,
                               detection_target, month_period, target, win, year_period)
from treeroute.errors import RefusedError
from treeroute.timing import (Reach, TimingRefusal, content_interval, forward_reach_days,
                              latest_label_step, max_forward_reach_days, reference_day,
                              target_reach_offset_steps)

NOWCAST = C.ReferenceKind.NOWCAST
ISSUE = C.ReferenceKind.ISSUE_STEP


# ---- content_interval: stamp x align ----
@pytest.mark.parametrize("y,m", [(2019, 1), (2019, 2), (2020, 2), (2019, 12), (2019, 4)])
def test_plain_month_in_both_spellings_is_exactly_the_month(y, m):
    period = month_period(y, m)
    assert content_interval(column("x", stamp=S.PERIOD_END, window=PLAIN_MONTH), period) == period
    centred = column("x", stamp=S.PERIOD_CENTRE, window=win(1, U.MONTH, A.CENTRED))
    assert content_interval(centred, period) == period
    forward = column("x", stamp=S.PERIOD_START, window=win(1, U.MONTH, A.FORWARD))
    assert content_interval(forward, period) == period


def test_centred_three_months_straddles_the_year_end():
    col = column("idx", stamp=S.PERIOD_CENTRE, window=win(3))
    assert content_interval(col, month_period(2019, 12)) == (day(2019, 11, 1), day(2020, 1, 31))
    assert content_interval(col, month_period(2020, 1)) == (day(2019, 12, 1), day(2020, 2, 29))


def test_backward_window_from_period_start_ends_before_the_period():
    # trailing history 'strictly before this month' (a stamp at the period start)
    col = column("h", stamp=S.PERIOD_START, window=win(12, U.MONTH, A.BACKWARD))
    assert content_interval(col, month_period(2019, 3)) == (day(2018, 3, 1), day(2019, 2, 28))


def test_one_day_snapshot_at_the_month_end():
    col = column("snap", stamp=S.PERIOD_END, window=win(1, U.DAY, A.BACKWARD))
    assert content_interval(col, month_period(2019, 6)) == (day(2019, 6, 30), day(2019, 6, 30))


def test_day_window_centred_on_a_month_centre():
    # January's centre is 16 Jan noon; +-23.5 days reaches 24 Dec .. 8 Feb
    col = column("d", stamp=S.PERIOD_CENTRE, window=win(47, U.DAY, A.CENTRED))
    assert content_interval(col, month_period(2019, 1)) == (day(2018, 12, 24), day(2019, 2, 8))


def test_centre_is_taken_in_the_window_unit():
    months = column("a", cadence=YEAR, stamp=S.PERIOD_CENTRE, window=win(12, U.MONTH, A.CENTRED))
    assert content_interval(months, year_period(2019)) == year_period(2019)
    days = column("a", cadence=YEAR, stamp=S.PERIOD_CENTRE, window=win(366, U.DAY, A.CENTRED))
    assert content_interval(days, year_period(2020)) == year_period(2020)


def test_forward_day_window_from_the_year_start_reaches_into_the_next_year():
    col = column("p", cadence=YEAR, stamp=S.PERIOD_START, window=win(430, U.DAY, A.FORWARD))
    first, last = content_interval(col, year_period(2019))
    assert first == day(2019, 1, 1) and last == day(2019, 1, 1) + 429


def test_partly_covered_days_count_as_content():
    # a one-day window centred on the middle of a two-day period covers half of each day (D19)
    col = column("h", cadence=DAILY, stamp=S.PERIOD_CENTRE, window=win(1, U.DAY, A.CENTRED))
    assert content_interval(col, (day(2019, 5, 1), day(2019, 5, 2))) == (day(2019, 5, 1),
                                                                         day(2019, 5, 2))


@pytest.mark.parametrize("align,expected", [
    (A.BACKWARD, (-29, 0)), (A.FORWARD, (0, 29)), (A.CENTRED, (-15, 15))])
def test_event_date_windows_include_the_event_day(align, expected):
    d = day(2016, 3, 10)
    length = 31 if align is A.CENTRED else 30
    col = column("e", cadence=EVENTS, stamp=S.EVENT_DATE, window=win(length, U.DAY, align))
    assert content_interval(col, (d, d)) == (d + expected[0], d + expected[1])


# ---- the unknown window: refused without a signed bound; the bound is forward from the stamp ----
def test_unknown_window_without_a_bound_is_refused_at_lag_zero():
    col = column("i", stamp=S.PERIOD_CENTRE, window=win(None, U.MONTH, A.UNKNOWN))
    with pytest.raises(TimingRefusal) as info:
        content_interval(col, month_period(2019, 5))
    assert info.value.rule == "G-LAG" and "refused at lag 0" in str(info.value)


def test_unknown_window_with_an_unsigned_bound_is_refused():
    col = column("i", stamp=S.PERIOD_CENTRE,
                 window=win(None, U.MONTH, A.UNKNOWN, max_length=5,
                            status=C.FactStatus.VERIFIED))
    with pytest.raises(TimingRefusal) as info:
        content_interval(col, month_period(2019, 5))
    assert info.value.rule == "G-LAG" and "not signed" in str(info.value)


def test_signed_bound_is_a_forward_window_from_the_stamp():
    # D20 read literally: a 3-month forward window from the CENTRE of May ends mid-August
    col = column("i", stamp=S.PERIOD_CENTRE,
                 window=win(None, U.MONTH, A.UNKNOWN, max_length=3, status=C.FactStatus.ASSUMED))
    first, last = content_interval(col, month_period(2019, 5))
    assert first == day(2019, 5, 16) and last == day(2019, 8, 16)
    # from a period_start stamp the same bound covers exactly three whole months
    col2 = column("i", stamp=S.PERIOD_START,
                  window=win(None, U.MONTH, A.UNKNOWN, max_length=3, status=C.FactStatus.ASSUMED))
    assert content_interval(col2, month_period(2019, 5)) == (day(2019, 5, 1), day(2019, 7, 31))


def test_bound_status_falls_back_to_the_column_when_the_window_carries_none():
    window = NS(length=None, unit="month", align="unknown", max_length=3)   # no fact_status
    signed = NS(name="g", cadence=MONTH, stamp="period_start", window=window,
                fact_status="assumed")
    assert content_interval(signed, month_period(2019, 5))[1] == day(2019, 7, 31)
    with pytest.raises(TimingRefusal):
        content_interval(NS(name="g", cadence=MONTH, stamp="period_start", window=window,
                            fact_status="unverified"), month_period(2019, 5))


@pytest.mark.parametrize("col", [
    column("n", window=win(None, U.MONTH, A.BACKWARD)),                  # known align, no length
    column("n", window=win(1, None, A.BACKWARD)),                        # no unit
    column("n", window=win(1, "week", A.BACKWARD)),                      # a unit timing has not
    column("n", window=win(1, U.MONTH, "sideways")),                     # unknown align value
    column("n", window=None),                                            # no window at all
    column("n", cadence=STATIC, window=None),                            # static: no content time
    column("n", stamp="mid_month"),                                      # unknown stamp
])
def test_malformed_window_facts_are_refused(col):
    with pytest.raises(TimingRefusal):
        content_interval(col, month_period(2019, 5))


def test_a_fact_that_is_not_an_enum_or_its_string_is_a_type_error():
    with pytest.raises(TypeError):
        content_interval(column("n", window=win(1, U.MONTH, 5)), month_period(2019, 5))


def test_days_outside_the_calendar_are_refused():
    with pytest.raises(TimingRefusal) as info:
        content_interval(column("x"), (0, 0))                   # ordinal 0 is before 1 January 1
    assert "outside the calendar" in str(info.value)


def test_calendar_internals_refuse_an_unknown_unit_and_a_missing_day():
    from fractions import Fraction
    from treeroute.timing.calendar import day_of, from_unit, to_unit
    with pytest.raises(TimingRefusal):
        to_unit(Fraction(day(2019, 5, 1)), "week")
    with pytest.raises(TimingRefusal):
        from_unit(Fraction(5), "week")
    with pytest.raises(TimingRefusal):
        day_of(2019, 2, 29)


def test_period_descriptions_for_messages():
    from treeroute.timing import describe_reference_period
    from treeroute.timing.calendar import describe_days
    assert describe_days(month_period(2019, 5)) == "May 1 - May 31 of year 2019"
    assert describe_days((day(2019, 12, 19), day(2020, 1, 3))) == \
        "Dec 19 of year 2019 - Jan 3 of year 2020"
    assert describe_reference_period((day(402, 5, 1), day(402, 5, 31))) == \
        "May 1 - May 31 (reference year 2 of 8; a position in the year, not a data date)"
    assert describe_reference_period((day(402, 12, 1), day(403, 1, 31))).startswith(
        "Dec 1 - Jan 31 (reference years 2-3 of 8")


def test_walks_stop_with_a_refusal_rather_than_loop():
    from treeroute.timing import compute_lag
    far = target(window=win(1, U.MONTH, A.BACKWARD, after=Reach(10002, "month")))
    with pytest.raises(TimingRefusal) as info:
        target_reach_offset_steps(far, MONTH)
    assert info.value.rule == "R17" and "10000" in str(info.value)
    # daily steps, so 10000 steps back stay inside the calendar
    ahead = column("a", cadence=DAILY, stamp=S.PERIOD_START, window=win(10002, U.DAY, A.FORWARD))
    daily = target(cadence=DAILY, window=win(1, U.DAY, A.BACKWARD))
    with pytest.raises(TimingRefusal) as info:
        compute_lag(ahead, daily, DAILY, NOWCAST)
    assert info.value.rule == "R8" and "10000" in str(info.value)


def test_a_backwards_period_is_refused():
    with pytest.raises(TimingRefusal):
        content_interval(column("x"), (day(2019, 5, 31), day(2019, 5, 1)))
    with pytest.raises(TypeError):
        content_interval(column("x"), (1.5, 3))


def test_refusal_is_a_refused_error_naming_the_column():
    with pytest.raises(RefusedError) as info:
        content_interval(column("the_col", window=None), month_period(2019, 5))
    assert "the_col" in str(info.value) and "Fix:" in str(info.value)


# ---- reach facts (owner ruling item 8 (a)) ----
def test_reach_widens_the_content_on_both_sides():
    col = column("v", stamp=S.PERIOD_CENTRE,
                 window=win(1, after=Reach(15, "day"), before=Reach(15, "day")))
    assert content_interval(col, month_period(2019, 12)) == (day(2019, 11, 16), day(2020, 1, 15))


def test_reach_after_alone_and_in_months():
    col = column("v", stamp=S.PERIOD_CENTRE, window=win(1, after=Reach(2, U.MONTH)))
    assert content_interval(col, month_period(2019, 11)) == (day(2019, 11, 1), day(2020, 1, 31))
    # reach is measured from the WINDOW's edge: a centred 3-month mean + 2 months reaches m+3
    oni_like = column("o", stamp=S.PERIOD_CENTRE, window=win(3, after=Reach(2, "month")))
    assert content_interval(oni_like, month_period(2019, 5))[1] == day(2019, 8, 31)


@pytest.mark.parametrize("reach", [Reach(0, "day"), Reach(-3, "day"), Reach(float("inf"), "day"),
                                   Reach(3, None), Reach(3, "week"), NS(value="15", unit="day")])
def test_malformed_reach_is_refused(reach):
    col = column("v", stamp=S.PERIOD_CENTRE, window=win(1, after=reach))
    with pytest.raises((TimingRefusal, TypeError)):
        content_interval(col, month_period(2019, 5))


# ---- forward reach (G-LAG, A5, D21) ----
def test_forward_reach_of_plain_centred_and_reaching_columns():
    jan = month_period(2019, 1)
    assert forward_reach_days(column("x"), jan) == 0
    assert forward_reach_days(column("v", stamp=S.PERIOD_CENTRE,
                                     window=win(1, after=Reach(15, "day"))), jan) == 15
    co2_like = column("c", stamp=S.PERIOD_CENTRE, window=win(3))
    assert forward_reach_days(co2_like, jan) == 28
    assert forward_reach_days(co2_like, month_period(2020, 1)) == 29
    trailing = column("h", stamp=S.PERIOD_START, window=win(1, U.MONTH, A.BACKWARD))
    assert forward_reach_days(trailing, jan) == -31


def test_max_forward_reach_is_the_largest_over_periods():
    col = column("d", stamp=S.PERIOD_CENTRE, window=win(47, U.DAY, A.CENTRED))
    periods = [month_period(2019, m) for m in range(1, 13)]
    values = [forward_reach_days(col, p) for p in periods]
    assert max_forward_reach_days(col, periods) == max(values)
    assert len(set(values)) > 1      # uneven month lengths: the reach varies by period
    with pytest.raises(TimingRefusal):
        max_forward_reach_days(col, [])


# ---- reference_day (R8) ----
def test_nowcast_reference_is_the_end_of_the_target_window():
    may = month_period(2019, 5)
    assert reference_day(MONTHLY_TARGET, may, NOWCAST) == may[1]
    assert reference_day(REACH_TARGET, may, NOWCAST) == may[1] + 15
    assert reference_day(REACH_TARGET, month_period(2019, 12), NOWCAST) == day(2020, 1, 15)


def test_issue_step_reference_is_the_end_of_the_issue_step():
    may, feb = month_period(2019, 5), month_period(2019, 2)
    assert reference_day(REACH_TARGET, may, ISSUE, issue_period=feb) == feb[1]
    assert reference_day(MONTHLY_TARGET, may, "issue_step", issue_period=feb) == feb[1]
    assert reference_day(MONTHLY_TARGET, may, ISSUE, issue_period=may) == may[1]     # lead 0
    with pytest.raises(TimingRefusal):
        reference_day(MONTHLY_TARGET, may, ISSUE)


@pytest.mark.parametrize("issue", [month_period(2019, 8), month_period(2019, 6),
                                   (day(2019, 5, 1), day(2019, 6, 1))])
def test_an_issue_period_ending_after_the_row_is_refused(issue):
    # a swapped or wrong argument would move the reference later: a look-ahead
    with pytest.raises(TimingRefusal) as info:
        reference_day(MONTHLY_TARGET, month_period(2019, 5), ISSUE, issue_period=issue)
    assert info.value.rule == "R8" and "after the row" in str(info.value)
    d = day(2016, 3, 10)
    ev = target(cadence=EVENTS, stamp=S.EVENT_DATE, window=win(7, U.DAY, A.BACKWARD))
    with pytest.raises(TimingRefusal):
        reference_day(ev, (d, d), ISSUE, issue_period=(d + 1, d + 1))


@pytest.mark.parametrize("kind", [NOWCAST, ISSUE])
def test_a_target_with_no_window_is_refused(kind):
    no_window = target(window=None)
    may = month_period(2019, 5)
    with pytest.raises(TimingRefusal) as info:
        reference_day(no_window, may, kind, issue_period=may)
    assert "no window" in str(info.value)


@pytest.mark.parametrize("kind", [NOWCAST, ISSUE])
def test_unknown_target_window_is_refused(kind):
    unknown = target(stamp=S.PERIOD_CENTRE,
                     window=win(None, U.MONTH, A.UNKNOWN, max_length=1,
                                status=C.FactStatus.ASSUMED))
    with pytest.raises(TimingRefusal):
        reference_day(unknown, month_period(2019, 5), kind, issue_period=month_period(2019, 4))


def test_event_references():
    d = day(2016, 3, 10)
    ev = target(cadence=EVENTS, stamp=S.EVENT_DATE, window=win(7, U.DAY, A.BACKWARD))
    assert reference_day(ev, (d, d), NOWCAST) == d
    ev_fwd = target(cadence=EVENTS, stamp=S.EVENT_DATE, window=win(7, U.DAY, A.FORWARD))
    assert reference_day(ev_fwd, (d, d), NOWCAST) == d + 6
    issue = d - 30
    assert reference_day(ev, (d, d), ISSUE, issue_period=(issue, issue)) == issue


def test_unknown_reference_kind_is_refused():
    with pytest.raises(TimingRefusal):
        reference_day(MONTHLY_TARGET, month_period(2019, 5), "lead_3")


# ---- R17 start offset (D12): the target's reach past its step, in whole steps rounded up ----
def test_reaching_composite_target_starts_the_history_one_step_back():
    assert target_reach_offset_steps(REACH_TARGET, MONTH) == 1
    t = 500
    assert latest_label_step(t, 0) - target_reach_offset_steps(REACH_TARGET, MONTH) == t - 2
    assert latest_label_step(t, 3) - target_reach_offset_steps(REACH_TARGET, MONTH) == t - 4


def test_plain_targets_end_the_history_at_t_minus_one():
    assert target_reach_offset_steps(MONTHLY_TARGET, MONTH) == 0
    assert target_reach_offset_steps(target(cadence=YEAR, window=win(1, U.YEAR, A.BACKWARD)),
                                     YEAR) == 0
    assert latest_label_step(500, 0) - target_reach_offset_steps(MONTHLY_TARGET, MONTH) == 499


@pytest.mark.parametrize("after", [Reach(0.5, "day"), Reach(1, "day"), Reach(16, "day"),
                                   Reach(28, "day"), Reach(1, "month")])
def test_detection_window_reach_starts_the_history_at_t_minus_two(after):
    # ruling R-D (b): a reach-after fact on the burned-area target; the guide states no margin,
    # so any signed positive bound up to 28 days (the shortest next month), or 1 month, gives the
    # same offset
    assert target_reach_offset_steps(detection_target(after), MONTH) == 1


@pytest.mark.parametrize("after", [Reach(29, "day"), Reach(31, "day"), Reach(2, "month")])
def test_a_reach_longer_than_the_next_step_counts_every_step_it_touches(after):
    # 29 days past 31 January is 1 March in a common year: two steps
    assert target_reach_offset_steps(detection_target(after), MONTH) == 2


def test_offset_refuses_an_unknown_target_window_and_a_static_cadence():
    unknown = target(window=win(None, U.MONTH, A.UNKNOWN))
    with pytest.raises(TimingRefusal):
        target_reach_offset_steps(unknown, MONTH)
    with pytest.raises(TimingRefusal):
        target_reach_offset_steps(MONTHLY_TARGET, STATIC)
    with pytest.raises(TimingRefusal):
        target_reach_offset_steps(target(window=None), MONTH)


@pytest.mark.parametrize("cadence", [
    C.Cadence(C.CadenceKind.REGULAR, length=3, unit=C.StepUnit.MONTH),
    C.Cadence(C.CadenceKind.REGULAR, length=2, unit=C.StepUnit.YEAR),
    C.Cadence(C.CadenceKind.REGULAR, length=8, unit=C.StepUnit.DAY),
])
def test_offset_refuses_a_target_step_longer_than_one_unit(cadence):
    # its periods are indexed from the target table's first position (D29), not from January
    t = target(cadence=cadence, window=win(1, U.MONTH, A.BACKWARD))
    with pytest.raises(TimingRefusal) as info:
        target_reach_offset_steps(t, cadence)
    assert info.value.rule == "R17" and "first position" in str(info.value)


def test_offset_on_one_day_steps_and_the_schema_composite_form():
    from treeroute.package import schema as SC
    daily = target(cadence=DAILY, window=win(1, U.DAY, A.BACKWARD))
    assert target_reach_offset_steps(daily, DAILY) == 0
    schema_form = SC.Cadence.model_validate({"kind": "composite_of_year", "length": 16,
                                             "unit": "day"})
    t = target(cadence=schema_form, stamp=S.PERIOD_END, window=win(16, U.DAY, A.BACKWARD))
    assert target_reach_offset_steps(t, schema_form) == 0
    spill = target(cadence=schema_form, stamp=S.PERIOD_END,
                   window=win(16, U.DAY, A.BACKWARD, after=Reach(3, "day")))
    assert target_reach_offset_steps(spill, schema_form) == 1


def test_composite_target_whose_last_composite_spills_into_january():
    # 16-day composites restart on 1 January; stored periods end on 31 December, the spill is reach
    cadence = composite(16, per_year=23)
    t = target(cadence=cadence, stamp=S.PERIOD_START,
               window=win(16, U.DAY, A.FORWARD, after=Reach(16, "day")))
    assert target_reach_offset_steps(t, cadence) >= 1
