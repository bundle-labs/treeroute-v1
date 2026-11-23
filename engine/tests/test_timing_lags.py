"""R8 compute_lag: the ruled values of 2026-09-28 and a synthetic case for every branch.

Ruled (OWNER_RULINGS_2026-09-28.md, INDEX_WINDOW_AUDIT.md): oni -> 3 months and nino*/sst_anom_* -> 2
(R-A a), tni -> 3 (R-B), co2 -> 1 (R-C a), all 13 ERSSTv5 columns -> 1 year on annual aggregates;
annual columns on a monthly target -> year -1; same-year annual on an annual target -> 0 (D25 a);
co-measured columns -> 1 (Q3 a, Q38 b); the reaching NDVI target leaves whole-month drivers alone;
the burned-area target's reach (R-D b) leaves the lags alone.
Decisions: D19 inclusive, D22 column steps, D23 largest over positions, D24 max of both references.
"""

from types import SimpleNamespace as NS

import pytest

from test_timing_facts import (A, ANNUAL_TARGET, C, DAILY, EPOCH, EVENTS, MONTH, MONTHLY_TARGET,
                               PLAIN_YEAR, QUARTER, REACH_TARGET, STATIC, S, U, YEAR, column,
                               composite, detection_target, target, win)
from treeroute.timing import Lag, Reach, TimingRefusal, compute_lag, lag_trace

NOWCAST = C.ReferenceKind.NOWCAST
ISSUE = C.ReferenceKind.ISSUE_STEP
SST_BOXES = ("sst_anom_atl3", "sst_anom_iod_west", "sst_anom_iod_east",
             "sst_anom_subpolar_north_atlantic", "sst_anom_coral_sea", "sst_anom_mediterranean",
             "sst_anom_global_tropical_mean", "sst_anom_nino34")
NINO = ("nino12", "nino3", "nino4", "nino34")


def lag(col, tgt=MONTHLY_TARGET, cadence=None, reference=NOWCAST):
    return compute_lag(col, tgt, cadence or tgt.cadence, reference)


def idx(name, window):
    """A global index in the audit's spelling: stamp at the month centre, window around it."""
    return column(name, stamp=S.PERIOD_CENTRE, window=window)


# ---- ruled values: the climate indices ----
def test_oni_lags_three_months_under_R_A_a_in_either_spelling():
    assert lag(idx("oni", win(7))).steps == 3                                # window_if_filter
    assert lag(idx("oni", win(3, after=Reach(2, "month")))).steps == 3       # 3-month mean + reach
    assert lag(idx("oni", win(3))).steps == 1                                # without the filter


@pytest.mark.parametrize("name", NINO + SST_BOXES)
def test_nino_and_sst_boxes_lag_two_months_under_R_A_a(name):
    assert lag(idx(name, win(5))).steps == 2
    assert lag(idx(name, win(1, after=Reach(2, "month")))).steps == 2


def test_tni_lags_three_months_under_R_B():
    assert lag(idx("tni", win(7))).steps == 3


def test_co2_lags_one_month_under_R_C_a():
    assert lag(idx("co2", win(3, status=C.FactStatus.ASSUMED))).steps == 1
    # the ruled window is in the audit's spelling (stamp at the month centre); kept at the seeded
    # store stamp period_end, the same window would reach mid-(m+2) and lag 2
    assert lag(column("co2", stamp=S.PERIOD_END, window=win(3))).steps == 2


@pytest.mark.parametrize("reach_months", [2, 3])
def test_ersst_columns_lag_one_year_on_annual_aggregates(reach_months):
    # an annual aggregate of a monthly column whose content reaches +2 (+3 for oni) months
    agg = column("agg", cadence=YEAR, stamp=S.PERIOD_CENTRE,
                 window=win(1, U.YEAR, A.CENTRED, after=Reach(reach_months, "month"),
                            before=Reach(reach_months, "month")))
    got = lag(agg, ANNUAL_TARGET)
    assert got.steps == 1 and got.column_cadence == YEAR


@pytest.mark.parametrize("window_months", [3, 7])
def test_centred_tni_and_co2_windows_lag_one_year_as_annual_aggregates(window_months):
    # a calendar-year mean of a centred w-month window spans 12 + w - 1 months around the year centre
    agg = column("agg", cadence=YEAR, stamp=S.PERIOD_CENTRE, window=win(12 + window_months - 1))
    assert lag(agg, ANNUAL_TARGET).steps == 1


# ---- ruled values: annual columns (Q3 a, D25 a) ----
def test_annual_columns_on_a_monthly_target_come_out_at_year_minus_one():
    annual = column("pop", cadence=YEAR, window=PLAIN_YEAR)
    got = lag(annual)
    assert got == Lag(column="pop", steps=1, column_cadence=YEAR, floor_reason=None)
    trace = lag_trace(annual, MONTHLY_TARGET, MONTH)
    # only December can read its own year (inclusive bound); every other month needs year -1
    assert trace.positions == 96 and trace.issue_steps == 1


def test_same_year_annual_value_stays_at_lag_zero_on_an_annual_target():
    assert lag(column("pop", cadence=YEAR, window=PLAIN_YEAR), ANNUAL_TARGET).steps == 0
    centred = column("pop", cadence=YEAR, stamp=S.PERIOD_CENTRE, window=win(1, U.YEAR))
    assert lag(centred, ANNUAL_TARGET).steps == 0


def test_annual_value_whose_facts_reach_past_the_year_lags_one_year():
    # a December composite running 3 days into January makes the calendar-year aggregate reach
    v11_annual = column("v", cadence=YEAR, stamp=S.PERIOD_CENTRE,
                        window=win(1, U.YEAR, after=Reach(3, "day")))
    assert lag(v11_annual, ANNUAL_TARGET).steps == 1
    phenology = column("p", cadence=YEAR, stamp=S.PERIOD_START, window=win(430, U.DAY, A.FORWARD))
    assert lag(phenology, ANNUAL_TARGET).steps == 1
    assert lag(phenology).steps == 2     # on a monthly target: January needs two years back


# ---- ruled values: the reaching composite target and composite drivers ----
def test_reaching_composite_as_a_driver_lags_one_month():
    v11 = idx("V11", win(1, after=Reach(15, "day"), before=Reach(15, "day")))
    assert lag(v11).steps == 1


def test_whole_month_drivers_keep_their_lags_on_the_reaching_target():
    assert lag(column("m"), REACH_TARGET).steps == 0
    assert lag(idx("oni", win(3)), REACH_TARGET).steps == 1
    assert lag(column("pop", cadence=YEAR, window=PLAIN_YEAR), REACH_TARGET).steps == 1
    trace = lag_trace(column("m"), REACH_TARGET, MONTH)
    assert trace.nowcast_steps == 0 and trace.issue_steps == 0


def test_co_measured_columns_take_the_one_step_floor():
    cloud = column("cloud_frequency_pct", co_measured=True)
    got = lag(cloud)
    assert got.steps == 1 and got.floor_reason == "co_measured"
    burn = column("burn_frac", co_measured=True)
    assert lag(burn, REACH_TARGET).steps == 1


@pytest.mark.parametrize("after", [Reach(1, "month"), Reach(16, "day")])
def test_detection_reach_on_the_burned_area_target_leaves_lags_alone(after):
    t = detection_target(after)
    assert lag(column("cloud_frequency_pct", co_measured=True), t).steps == 1
    assert lag(column("m"), t).steps == 0
    assert lag(column("pop", cadence=YEAR, window=PLAIN_YEAR), t).steps == 1


# ---- the floor ----
def test_computed_from_takes_the_floor_and_both_reasons_are_named():
    t = target(computed_from=("precip", "pet"))
    assert lag(column("precip"), t).floor_reason == "computed_from"
    assert lag(column("precip", co_measured=True), t).floor_reason == "co_measured+computed_from"
    assert lag(column("other"), t).steps == 0


def test_computed_from_given_as_one_string():
    one = NS(name="y", cadence=MONTH, stamp="period_end", window=win(1, U.MONTH, A.BACKWARD),
             computed_from="precip")
    got = lag(column("precip", co_measured=False), one)
    assert got.steps == 1 and got.floor_reason == "computed_from"
    assert lag(column("pre", co_measured=False), one).steps == 0      # not a substring match


@pytest.mark.parametrize("value", [1, 0, "yes", "true", 1.0])
def test_co_measured_must_be_a_bool(value):
    with pytest.raises(TimingRefusal) as info:
        lag(column("cloud", co_measured=value))
    assert info.value.rule == "R8" and "co_measured_with_target" in str(info.value)


def test_unanswered_co_measured_is_recorded_in_the_trace():
    trace = lag_trace(column("cloud", co_measured=None), MONTHLY_TARGET, MONTH)
    assert trace.unanswered == ("co_measured_with_target",) and trace.steps == 0
    assert lag_trace(column("cloud", co_measured=False), MONTHLY_TARGET, MONTH).unanswered == ()
    assert lag_trace(column("cloud", co_measured=True), MONTHLY_TARGET, MONTH).unanswered == ()


def test_floor_does_not_bite_when_the_content_already_lags():
    got = lag(idx("co2", win(3)), target(computed_from=("co2",)))
    assert got.steps == 1 and got.floor_reason is None
    annual = column("pop", cadence=YEAR, window=PLAIN_YEAR, co_measured=True)
    got = lag(annual, ANNUAL_TARGET)
    assert got.steps == 1 and got.floor_reason == "co_measured"     # 1 step = 1 YEAR (D22)


# ---- decisions ----
def test_inclusive_bound_lets_same_step_content_through():
    # D19: content ending exactly on the reference day is 'at or before'
    assert lag(column("m")).steps == 0


def test_largest_lag_over_positions_in_the_year():
    # D23: a quarterly total needs 0 steps in quarter-end months and 1 elsewhere -> 1
    quarterly = column("q", cadence=QUARTER, window=win(3, U.MONTH, A.BACKWARD))
    trace = lag_trace(quarterly, MONTHLY_TARGET, MONTH)
    assert trace.steps == 1
    first, last = trace.worst_issue_period
    assert last < first + 31                  # a month, not a quarter end
    assert lag(quarterly).column_cadence == QUARTER


def test_lag_is_the_larger_of_the_two_references():
    # D24: a target whose own content is the PREVIOUS month (stamped at the period start) moves the
    # nowcast reference earlier than the issue-step end
    early = target(stamp=S.PERIOD_START, window=win(1, U.MONTH, A.BACKWARD))
    trace = lag_trace(column("m"), early, MONTH)
    assert (trace.nowcast_steps, trace.issue_steps) == (1, 0)
    assert lag(column("m"), early, reference=NOWCAST).steps == 1
    assert lag(column("m"), early, reference=ISSUE).steps == 1


def test_steps_are_counted_in_the_column_steps():
    # D22: an annual column on a monthly target is 1 step back (1 year), not 12 target steps
    got = lag(column("pop", cadence=YEAR, window=PLAIN_YEAR))
    assert got.steps == 1 and got.column_cadence == YEAR


def test_signed_bound_lags_by_the_forward_worst_case():
    bound = idx("t", win(None, U.MONTH, A.UNKNOWN, max_length=5, status=C.FactStatus.ASSUMED))
    assert lag(bound).steps == 5      # D20 literal: forward 5 months from the month CENTRE


# ---- refusals ----
def test_unknown_window_without_a_signed_bound_is_refused():
    with pytest.raises(TimingRefusal) as info:
        lag(idx("t", win(None, U.MONTH, A.UNKNOWN)))
    assert info.value.rule == "G-LAG"
    with pytest.raises(TimingRefusal):
        lag(idx("t", win(None, U.MONTH, A.UNKNOWN, max_length=5)))      # bound not signed


def test_epoch_static_and_irregular_columns_are_refused():
    with pytest.raises(TimingRefusal) as info:
        lag(column("wdpa", cadence=EPOCH))
    assert info.value.rule == "G-EPOCH"
    with pytest.raises(TimingRefusal):
        lag(column("elev", cadence=STATIC, window=None))
    with pytest.raises(TimingRefusal):
        lag(column("ev", cadence=EVENTS, stamp=S.EVENT_DATE, window=win(1, U.DAY, A.BACKWARD)))


def test_a_column_finer_than_the_target_step_is_refused():
    with pytest.raises(TimingRefusal) as info:
        lag(column("m"), ANNUAL_TARGET)
    assert "aggregate" in str(info.value)
    # the position is printed as a place in the year on the synthetic calendar, not as ordinals
    assert "Jan 1 - Dec 31" in str(info.value) and "reference year 1 of 8" in str(info.value)
    assert "146" not in str(info.value)
    comp_target = target(cadence=composite(16, 23), stamp=S.PERIOD_START,
                         window=win(16, U.DAY, A.FORWARD))
    with pytest.raises(TimingRefusal):
        lag(column("m"), comp_target)             # months do not hold 16-day composites


def test_unknown_target_window_and_bad_reference_are_refused():
    with pytest.raises(TimingRefusal):
        lag(column("m"), target(window=win(None, U.MONTH, A.UNKNOWN)))
    with pytest.raises(TimingRefusal):
        compute_lag(column("m"), MONTHLY_TARGET, MONTH, "lead_1")


def test_static_target_cadence_is_refused():
    with pytest.raises(TimingRefusal):
        compute_lag(column("m"), MONTHLY_TARGET, STATIC, NOWCAST)
    with pytest.raises(TimingRefusal):
        compute_lag(column("m"), MONTHLY_TARGET, EPOCH, NOWCAST)


@pytest.mark.parametrize("cadence", [QUARTER,
                                     C.Cadence(C.CadenceKind.REGULAR, length=2, unit=U.YEAR),
                                     C.Cadence(C.CadenceKind.REGULAR, length=8, unit=U.DAY)])
def test_a_target_step_longer_than_one_unit_is_refused(cadence):
    # step_index counts such steps from the target table's first position (D29); walking them from
    # January would place a DJF-type season as JFM
    t = target(cadence=cadence, window=win(3, U.MONTH, A.BACKWARD))
    with pytest.raises(TimingRefusal) as info:
        compute_lag(column("m"), t, cadence, NOWCAST)
    assert info.value.rule == "R8" and "first position" in str(info.value)


@pytest.mark.parametrize("cadence", [
    None,                                                             # no cadence
    NS(kind="hourly"),                                                # unknown kind
    C.Cadence(C.CadenceKind.REGULAR, length=0, unit=U.MONTH),         # non-positive length
    C.Cadence(C.CadenceKind.REGULAR, length=1, unit=None),            # no unit
    NS(kind="regular", length=1, unit="week"),                        # a unit timing has not
    composite(0),                                                     # non-positive composite
    NS(kind="composite_of_year", length=16, unit="month"),            # composites count days
])
def test_malformed_column_cadence_is_refused(cadence):
    with pytest.raises(TimingRefusal):
        lag(column("m", cadence=cadence))


def test_malformed_target_cadence_is_refused():
    with pytest.raises(TimingRefusal):
        compute_lag(column("m"), MONTHLY_TARGET, None, NOWCAST)
    with pytest.raises(TimingRefusal):
        compute_lag(column("m"), MONTHLY_TARGET, NS(kind="hourly"), NOWCAST)


def test_schema_composite_form_as_column_and_target():
    from treeroute.package import schema as SC
    schema_form = SC.Cadence.model_validate({"kind": "composite_of_year", "length": 16,
                                             "unit": "day"})
    t = target(cadence=schema_form, stamp=S.PERIOD_END, window=win(16, U.DAY, A.BACKWARD))
    plain = column("c", cadence=schema_form, stamp=S.PERIOD_END, window=win(16, U.DAY, A.BACKWARD))
    assert compute_lag(plain, t, schema_form, NOWCAST).steps == 0
    forward = column("c", cadence=schema_form, stamp=S.PERIOD_START,
                     window=win(16, U.DAY, A.FORWARD))
    assert compute_lag(forward, t, schema_form, NOWCAST).steps == 1
    assert compute_lag(column("pop", cadence=YEAR, window=PLAIN_YEAR), t, schema_form,
                       NOWCAST).steps == 1


def test_trace_prints_the_worst_positions_in_the_year():
    trace = lag_trace(column("pop", cadence=YEAR, window=PLAIN_YEAR), MONTHLY_TARGET, MONTH)
    assert trace.worst_issue_position.startswith("Jan 1 - Jan 31 (reference year 1 of 8")
    assert "not a data date" in trace.worst_nowcast_position


# ---- other cadences ----
def test_event_target_walks_every_day():
    ev = target(cadence=EVENTS, stamp=S.EVENT_DATE, window=win(1, U.DAY, A.BACKWARD))
    assert lag(column("m"), ev).steps == 1
    assert lag(column("pop", cadence=YEAR, window=PLAIN_YEAR), ev).steps == 1
    daily = column("d", cadence=DAILY, window=win(1, U.DAY, A.BACKWARD))
    assert lag(daily, ev).steps == 0


def test_same_composite_step_and_a_year_end_spill():
    cadence = composite(16, 23)
    t = target(cadence=cadence, stamp=S.PERIOD_END, window=win(16, U.DAY, A.BACKWARD))
    # content ending at the stored period's end, including the truncated last composite (31 Dec)
    plain = column("c", cadence=cadence, stamp=S.PERIOD_END, window=win(16, U.DAY, A.BACKWARD))
    assert lag(plain, t).steps == 0
    # a full 16 days forward from the start: the truncated last composite runs into January
    forward = column("c", cadence=cadence, stamp=S.PERIOD_START, window=win(16, U.DAY, A.FORWARD))
    trace = lag_trace(forward, t, cadence)
    assert trace.steps == 1
    first, last = trace.worst_issue_period
    assert last - first + 1 < 16        # the worst position is a truncated year-end composite
    spill = column("c", cadence=cadence, stamp=S.PERIOD_END,
                   window=win(16, U.DAY, A.BACKWARD, after=Reach(3, "day")))
    assert lag(spill, t).steps == 1


def test_plain_strings_and_enums_give_the_same_lag():
    as_strings = NS(name="oni", cadence=NS(kind="regular", length=1, unit="month"),
                    stamp="period_centre",
                    window=NS(length=7, unit="month", align="centred", max_length=None),
                    fact_status="unverified")
    tgt = NS(name="y", cadence=NS(kind="regular", length=1, unit="month"), stamp="period_end",
             window=NS(length=1, unit="month", align="backward", max_length=None))
    assert compute_lag(as_strings, tgt, tgt.cadence, "nowcast").steps == 3
    assert lag(idx("oni", win(7))).steps == 3


def test_lag_is_a_pure_function_of_the_facts():
    col = idx("tni", win(7))
    assert lag(col) == lag(col)
    assert lag_trace(col, MONTHLY_TARGET, MONTH) == lag_trace(col, MONTHLY_TARGET, MONTH)
