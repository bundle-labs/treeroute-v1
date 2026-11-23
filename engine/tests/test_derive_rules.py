"""derive/ rules on synthetic inputs: every branch and every refusal of R1-R8, R10, R11, R22, R23, R28
and the borderline flags (R9, R12-R21 and R30: tests/test_derive_loro_rules.py).

Synthetic tables only (no store is read). The approved shapes are mirrored where a rule reads facts
(tests/test_timing_facts.py builders; DonorView from test_derive_shapes.py).
"""

import datetime as dt
from types import SimpleNamespace

import numpy as np
import pytest

from test_derive_shapes import DonorView
from test_timing_facts import (ANNUAL_TARGET, CENTRED_MONTH, EPOCH, EVENTS, MONTH, MONTHLY_TARGET,
                               PLAIN_YEAR, STATIC, YEAR, A, C, S as STAMP, U, column, composite, target,
                               win)
from treeroute import derive as D
from treeroute import engine_constants as K
from treeroute import timing
from treeroute.errors import RefusedError
from treeroute.timing import TimingRefusal

S = D  # the derive package exports its shapes


def refused(rule, call, *args, **kwargs):
    with pytest.raises(RefusedError) as info:
        call(*args, **kwargs)
    assert info.value.rule == rule, str(info.value)
    return str(info.value)


# ===================================================================================================
# borderline flags (Section 2, D1)
def test_margins_are_signed_and_the_flag_is_within_twenty_percent_inclusive():
    margins, flags = D.borderline_flags(0.6, {"a": 0.5, "b": 1.0, "c": 0.75})
    assert margins == {"a": pytest.approx(0.1), "b": pytest.approx(-0.4), "c": pytest.approx(-0.15)}
    # |0.6 - 0.5| = 0.1 = 20% of 0.5 (inclusive); 0.4 > 0.2; 0.15 = 20% of 0.75 exactly
    assert flags == ("borderline:a", "borderline:c")


def test_zero_threshold_uses_the_absolute_margin_only():
    margins, flags = D.borderline_flags(0.001, {"zero": 0.0})
    assert margins == {"zero": pytest.approx(0.001)} and flags == ()
    assert D.borderline_flags(0, {"zero": 0})[1] == ("borderline:zero",)


def test_negative_threshold_is_relative_to_its_size():
    assert D.borderline_flags(-9, {"t": -10})[1] == ("borderline:t",)
    assert D.borderline_flags(-7, {"t": -10})[1] == ()


@pytest.mark.parametrize("value,thresholds", [(float("nan"), {"t": 1}), (float("inf"), {"t": 1}),
                                              (1.0, {"t": float("nan")}), (1.0, {"": 1.0}),
                                              ("1", {"t": 1}), (True, {"t": 1})])
def test_borderline_refuses_non_finite_or_malformed_input(value, thresholds):
    refused("Section 2", D.borderline_flags, value, thresholds)


# ===================================================================================================
# R1 cadence
def monthly_table(units=("u1", "u2", "u3"), years=(2001, 2002), step=1):
    uid, yy, mm = [], [], []
    for u in units:
        for y in years:
            for m in range(1, 13, step):
                uid.append(u), yy.append(y), mm.append(m)
    return np.array(uid), {"yr": np.array(yy), "mo": np.array(mm)}, {"yr": "year", "mo": "month"}


def day_table(dates_by_unit):
    uid, days = [], []
    for u, dates in dates_by_unit.items():
        for d in dates:
            uid.append(u), days.append(np.datetime64(d, "D"))
    return np.array(uid), {"when": np.array(days, dtype="datetime64[D]")}, {"when": "date"}


def composite_rows(n_days, years=(2003, 2004, 2005), units=("a", "b")):
    uid, yy, doy = [], [], []
    for u in units:
        for y in years:
            length = (dt.date(y + 1, 1, 1) - dt.date(y, 1, 1)).days
            for d in range(1, length + 1, n_days):
                uid.append(u), yy.append(y), doy.append(d)
    return np.array(uid), np.array(yy), np.array(doy)


def test_r1_monthly_grid_records_the_spacing_of_every_unit():
    out = D.derive_r01_cadence(*monthly_table())
    assert out.value == S.Cadence(S.CadenceKind.REGULAR, length=1, unit=S.StepUnit.MONTH)
    assert out.inputs["units_by_spacing"] == {1: 3} and out.inputs["regular_units_by_step"] == {1: 3}
    assert out.inputs["rows"] == 72 and out.inputs["single_row_units"] == 0
    assert out.inputs["time_line"] == "month"
    assert {"unit_ids", "time:yr", "time:mo"} <= set(out.input_hashes)


def test_r1_annual_and_multi_month_grids():
    annual = D.derive_r01_cadence(np.array(["a"] * 5 + ["b"] * 5), {"y": np.tile(np.arange(2001, 2006), 2)},
                                  {"y": "year"})
    assert annual.value == S.Cadence(S.CadenceKind.REGULAR, length=1, unit=S.StepUnit.YEAR)
    two = D.derive_r01_cadence(*monthly_table(step=2))
    assert two.value == S.Cadence(S.CadenceKind.REGULAR, length=2, unit=S.StepUnit.MONTH)


def test_r1_accepts_integer_unit_codes_and_any_row_order():
    uid, times, facts = monthly_table()
    order = np.random.RandomState(0).permutation(len(uid))    # fixed permutation of a synthetic table
    codes = np.unique(uid, return_inverse=True)[1]
    out = D.derive_r01_cadence(codes[order], {k: v[order] for k, v in times.items()}, facts)
    assert out.value.length == 1 and out.value.unit == S.StepUnit.MONTH


def test_r1_refuses_an_empty_table_and_mismatched_facts():
    refused("R1", D.derive_r01_cadence, np.array([], dtype=object), {"y": np.array([], dtype=int)},
            {"y": "year"})
    uid, times, facts = monthly_table()
    refused("R1", D.derive_r01_cadence, uid, times, {"yr": "year"})                 # column without fact
    refused("R1", D.derive_r01_cadence, uid, {"yr": times["yr"]}, facts)            # fact without column
    refused("R1", D.derive_r01_cadence, uid, times, {"yr": "year", "mo": "week"})   # unknown part
    refused("R1", D.derive_r01_cadence, uid[:-1], times, facts)                     # lengths differ


def test_r1_refuses_missing_unit_ids_and_repeated_keys():
    uid, times, facts = monthly_table()
    bad = uid.astype(object)
    bad[3] = None
    assert "no unit id" in refused("R1", D.derive_r01_cadence, bad, times, facts)
    dup_t = {k: np.r_[v, v[:1]] for k, v in times.items()}
    assert "repeat" in refused("R1", D.derive_r01_cadence, np.r_[uid, uid[:1]], dup_t, facts)


def test_r1_refuses_calendar_parts_it_cannot_place():
    refused("R1", D.derive_r01_cadence, np.array(["a", "a"]), {"m": np.array([1, 2])}, {"m": "month"})
    refused("R1", D.derive_r01_cadence, np.array(["a", "a"]), {"d": np.array([1, 9])},
            {"d": "day_of_year"})
    # a month column that disagrees with year + day_of_year (day 40 is in February)
    refused("R1", D.derive_r01_cadence, np.array(["a", "a"]),
            {"y": np.array([2001, 2001]), "d": np.array([1, 40]), "m": np.array([1, 3])},
            {"y": "year", "d": "day_of_year", "m": "month"})


def test_r1_month_line_checks_every_unit_and_refuses_gaps_or_single_rows():
    uid, times, facts = monthly_table(units=tuple("u%d" % i for i in range(50)))
    keep = ~((uid == "u49") & (times["mo"] == 7))         # one gap in the LAST unit only
    msg = refused("R1", D.derive_r01_cadence, uid[keep], {k: v[keep] for k, v in times.items()}, facts)
    assert "irregular" in msg and "u49" in msg
    extra_u = np.r_[uid, ["lonely"]]
    extra_t = {"yr": np.r_[times["yr"], [2001]], "mo": np.r_[times["mo"], [1]]}
    assert "one row" in refused("R1", D.derive_r01_cadence, extra_u, extra_t, facts)
    refused("R1", D.derive_r01_cadence, np.array(["a", "b"]), {"y": np.array([2001, 2001])},
            {"y": "year"})                                  # every unit has one row


def test_r1_refuses_units_regular_with_different_steps_d2():
    u1, t1, facts = monthly_table(units=("a",), step=1)
    u2, t2, _ = monthly_table(units=("b",), step=3)
    msg = refused("R1", D.derive_r01_cadence, np.r_[u1, u2], {k: np.r_[t1[k], t2[k]] for k in t1}, facts)
    assert "D2" in msg


def day_run(first, n, step=1):
    return [str(np.datetime64(first) + i * step) for i in range(n)]


def test_r1_day_line_regular_grids():
    days = day_run("2001-01-01", 40)
    daily = D.derive_r01_cadence(*day_table({"a": days, "b": days}))
    assert daily.value == S.Cadence(S.CadenceKind.REGULAR, length=1, unit=S.StepUnit.DAY)
    later = day_run("2001-01-03", 6, 7)                      # not on a 7-day grid from 1 January
    weekly = D.derive_r01_cadence(*day_table({"a": later, "b": later}))
    assert weekly.value == S.Cadence(S.CadenceKind.REGULAR, length=7, unit=S.StepUnit.DAY)
    # a year end that keeps the spacing (a leap year: 2004-12-31 is day 366) shows there is no reset
    five = day_run("2003-01-01", 3 * 73 + 1, 5)
    out = D.derive_r01_cadence(*day_table({"a": five}))
    assert out.value == S.Cadence(S.CadenceKind.REGULAR, length=5, unit=S.StepUnit.DAY)


# (f) one regular N-day spacing on the N-day grid from 1 January with no year end that tells a restart
# apart: both a regular N-day step and an N-day composite calendar fit, so R1 refuses
@pytest.mark.parametrize("dates", [
    day_run("2001-01-01", 6, 7),                              # weekly, one year, from 1 January
    day_run("2003-01-01", 46, 8),                             # one year of 8-day composites
    day_run("2003-02-18", 40, 8),                             # the same from day 49
    day_run("2001-01-01", 2 * 73 + 5, 5),                     # 5-day across common years only
])
def test_r1_refuses_a_grid_that_fits_a_regular_step_and_a_composite_calendar(dates):
    msg = refused("R1", D.derive_r01_cadence, *day_table({"a": dates, "b": dates}))
    assert "fit both" in msg


# (a) annual grids keyed by a date column are read on the year line
@pytest.mark.parametrize("month_day", ["01-01", "07-01", "12-31"])
def test_r1_date_keyed_annual_grids(month_day):
    dates = {u: ["%d-%s" % (y, month_day) for y in range(2001, 2009)] for u in ("a", "b")}
    out = D.derive_r01_cadence(*day_table(dates))
    assert out.value == S.Cadence(S.CadenceKind.REGULAR, length=1, unit=S.StepUnit.YEAR)
    assert out.inputs["time_line"] == "year" and "of its year" in out.inputs["date_anchor"]


def test_r1_date_keyed_annual_grid_without_a_leap_year_is_not_a_365_day_grid():
    out = D.derive_r01_cadence(*day_table({"a": ["2001-01-01", "2002-01-01", "2003-01-01"]}))
    assert out.value == S.Cadence(S.CadenceKind.REGULAR, length=1, unit=S.StepUnit.YEAR)


def month_dates(day_of_month, years=(2001, 2002), units=("a", "b"), every=1):
    out = {}
    for u in units:
        rows = []
        for y in years:
            for m in range(1, 13, every):
                last = (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)).day
                rows.append(str(dt.date(y, m, last if day_of_month == "last" else day_of_month)))
        out[u] = rows
    return out


# (b) monthly grids keyed by a date column are read on the month line
@pytest.mark.parametrize("day_of_month,anchor", [(15, "day 15 of its month"), (1, "day 1 of its month"),
                                                 ("last", "the last day of its month")])
def test_r1_date_keyed_monthly_grids(day_of_month, anchor):
    out = D.derive_r01_cadence(*day_table(month_dates(day_of_month)))
    assert out.value == S.Cadence(S.CadenceKind.REGULAR, length=1, unit=S.StepUnit.MONTH)
    assert out.inputs["time_line"] == "month" and anchor in out.inputs["date_anchor"]
    quarterly = D.derive_r01_cadence(*day_table(month_dates(day_of_month, every=3)))
    assert quarterly.value == S.Cadence(S.CadenceKind.REGULAR, length=3, unit=S.StepUnit.MONTH)


def test_r1_date_keyed_monthly_grid_with_a_hole_is_refused_on_the_month_line():
    dates = month_dates(1)
    dates["b"].remove("2002-05-01")
    msg = refused("R1", D.derive_r01_cadence, *day_table(dates))
    assert "month time line" in msg and "irregular" in msg and "composite" not in msg
    single = {"a": ["2001-03-01"], "b": ["2002-07-01"]}          # single visits dated by month only
    assert "one row" in refused("R1", D.derive_r01_cadence, *day_table(single))


def test_r1_year_and_day_of_year_on_a_year_or_month_anchor_is_refused():
    years = np.repeat(np.arange(2001, 2006), 1)
    msg = refused("R1", D.derive_r01_cadence, np.array(["a"] * 5), {"y": years, "d": np.ones(5, int)},
                  {"y": "year", "d": "day_of_year"})
    assert "declare the calendar parts" in msg and "(year)" in msg
    firsts = np.array([dt.date(2001, m, 1).timetuple().tm_yday for m in range(1, 13)])
    msg = refused("R1", D.derive_r01_cadence, np.array(["a"] * 12),
                  {"y": np.full(12, 2001), "d": firsts}, {"y": "year", "d": "day_of_year"})
    assert "(year + month)" in msg


def test_r1_composite_of_year_from_year_and_day_of_year():
    uid, yy, doy = composite_rows(8)
    out = D.derive_r01_cadence(uid, {"y": yy, "d": doy}, {"y": "year", "d": "day_of_year"})
    assert out.value == S.Cadence(S.CadenceKind.COMPOSITE_OF_YEAR, composites_per_year=46,
                                  composite_days=8)
    assert out.inputs["within_year_spacings"] == {8: 2 * 3 * 45}   # 45 gaps per unit-year
    assert out.inputs["composites_per_year_observed"] == 46


def test_r1_composite_of_year_from_a_date_column():
    uid, yy, doy = composite_rows(16)
    dates = np.array([np.datetime64(dt.date(int(y), 1, 1) + dt.timedelta(days=int(d) - 1), "D")
                      for y, d in zip(yy, doy)])
    out = D.derive_r01_cadence(uid, {"when": dates}, {"when": "date"})
    assert out.value.kind == S.CadenceKind.COMPOSITE_OF_YEAR
    assert (out.value.composite_days, out.value.composites_per_year) == (16, 23)


def test_r1_refuses_a_composite_calendar_whose_spacing_breaks_inside_a_year():
    uid, yy, doy = composite_rows(8)
    keep = ~((uid == "b") & (yy == 2004) & (doy == 81))       # one composite missing mid-year
    msg = refused("R1", D.derive_r01_cadence, uid[keep], {"y": yy[keep], "d": doy[keep]},
                  {"y": "year", "d": "day_of_year"})
    assert "breaks inside a year" in msg


def test_r1_events_irregular_dates_single_visits_and_two_visit_sites():
    irregular = D.derive_r01_cadence(*day_table({"a": ["2001-01-05", "2001-03-07", "2002-06-01"],
                                                 "b": ["2001-02-02"]}))
    assert irregular.value == S.Cadence(S.CadenceKind.IRREGULAR)
    assert irregular.inputs["single_row_units"] == 1 and irregular.inputs["irregular_units"] == 1
    single = D.derive_r01_cadence(*day_table({"a": ["2001-01-05"], "b": ["2003-02-02"]}))
    assert single.value.kind == S.CadenceKind.IRREGULAR
    # every site visited twice, at different gaps: one gap each shows no regularity -> events, not D2
    two = D.derive_r01_cadence(*day_table({"a": ["2001-01-01", "2001-01-11"],
                                           "b": ["2001-05-01", "2001-05-31"]}))
    assert two.value.kind == S.CadenceKind.IRREGULAR


def test_r1_a_calendar_that_resets_each_january_is_never_read_as_events():
    uid, yy, doy = composite_rows(8)
    stray_u, stray_y, stray_d = np.r_[uid, ["a"]], np.r_[yy, [2004]], np.r_[doy, [6]]   # off-grid row
    msg = refused("R1", D.derive_r01_cadence, stray_u, {"y": stray_y, "d": stray_d},
                  {"y": "year", "d": "day_of_year"})
    assert "1 rows off the 8-day grid" in msg
    # irregular visits that happen to start every unit-year on 1 January: refused, not events
    refused("R1", D.derive_r01_cadence,
            *day_table({"a": ["2001-01-01", "2001-01-11", "2001-02-20", "2002-01-01", "2002-01-11"]}))


def test_r1_day_line_d2_when_each_unit_shows_its_step_twice():
    msg = refused("R1", D.derive_r01_cadence,
                  *day_table({"a": ["2001-01-01", "2001-01-11", "2001-01-21"],
                              "b": ["2001-05-01", "2001-05-31", "2001-06-30"]}))
    assert "D2" in msg


# (d) a daily or composite grid with one single-row unit is refused, as on the month line
def test_r1_refuses_a_single_row_unit_in_a_daily_grid():
    days = day_run("2001-01-03", 40)
    msg = refused("R1", D.derive_r01_cadence, *day_table({"a": days, "b": days, "c": ["2001-01-05"]}))
    assert "1 units have one row" in msg and "'c'" in msg


def test_r1_refuses_a_single_row_unit_in_a_composite_grid():
    uid, yy, doy = composite_rows(8)
    msg = refused("R1", D.derive_r01_cadence, np.r_[uid, ["c"]], {"y": np.r_[yy, [2004]],
                                                                 "d": np.r_[doy, [9]]},
                  {"y": "year", "d": "day_of_year"})
    assert "composite-of-year" in msg and "1 units have one row" in msg


# (e) a unit regular at one step next to a two-row unit at another spacing is refused (D2)
def test_r1_refuses_a_two_row_unit_at_another_spacing_next_to_a_regular_unit():
    days = day_run("2001-01-03", 40)
    msg = refused("R1", D.derive_r01_cadence,
                  *day_table({"a": days, "b": ["2001-03-01", "2001-03-11"]}))
    assert "two rows at another spacing" in msg and "'b'" in msg
    # a two-row unit AT the grid's spacing is part of the grid
    out = D.derive_r01_cadence(*day_table({"a": days, "b": ["2001-03-01", "2001-03-02"]}))
    assert out.value == S.Cadence(S.CadenceKind.REGULAR, length=1, unit=S.StepUnit.DAY)


def test_r1_events_count_and_flag_units_that_are_regular_anyway():
    out = D.derive_r01_cadence(*day_table({"a": ["2001-01-05", "2001-03-07", "2002-06-01"],
                                           "b": ["2001-02-02", "2001-02-12", "2001-02-22"],
                                           "c": ["2001-04-04"]}))
    assert out.value.kind == S.CadenceKind.IRREGULAR
    assert out.flags == ("regular_units_in_events:1",)


# (c) composite grids at the edge of a unit's record, and holes in them
def test_r1_composite_grid_whose_first_year_starts_mid_year():
    uid, yy, doy = composite_rows(8)
    keep = ~((yy == 2003) & (doy < 49))                    # the record starts on day 49 of 2003
    out = D.derive_r01_cadence(uid[keep], {"y": yy[keep], "d": doy[keep]},
                               {"y": "year", "d": "day_of_year"})
    assert out.value == S.Cadence(S.CadenceKind.COMPOSITE_OF_YEAR, composites_per_year=46,
                                  composite_days=8)
    # a unit whose own record starts later, mid-year, is at its own edge too
    late = ~((uid == "b") & ((yy == 2003) | ((yy == 2004) & (doy < 100))))
    out = D.derive_r01_cadence(uid[late], {"y": yy[late], "d": doy[late]},
                               {"y": "year", "d": "day_of_year"})
    assert out.value.kind == S.CadenceKind.COMPOSITE_OF_YEAR


def test_r1_refuses_a_composite_grid_missing_a_day_one_row_after_the_first_year():
    uid, yy, doy = composite_rows(8)
    keep = ~((uid == "b") & (yy == 2004) & (doy == 1))
    msg = refused("R1", D.derive_r01_cadence, uid[keep], {"y": yy[keep], "d": doy[keep]},
                  {"y": "year", "d": "day_of_year"})
    assert "start after 1 January" in msg and "('b', 2004, 9)" in msg


# problem: composite grids missing the last composite of a year, or a whole year
def test_r1_refuses_a_composite_grid_missing_a_year_end_composite_or_a_year():
    uid, yy, doy = composite_rows(8)
    keep = ~((uid == "b") & (yy == 2004) & (doy == 361))
    msg = refused("R1", D.derive_r01_cadence, uid[keep], {"y": yy[keep], "d": doy[keep]},
                  {"y": "year", "d": "day_of_year"})
    assert "stop before their last composite" in msg and "('b', 2004, 353)" in msg
    uid, yy, doy = composite_rows(16, years=(2003, 2004, 2005, 2006))
    keep = ~((uid == "a") & (yy == 2004))
    msg = refused("R1", D.derive_r01_cadence, uid[keep], {"y": yy[keep], "d": doy[keep]},
                  {"y": "year", "d": "day_of_year"})
    assert "skip a whole year" in msg and "('a', 2003, 2005)" in msg


def test_r1_composite_records_its_checks():
    uid, yy, doy = composite_rows(16)
    out = D.derive_r01_cadence(uid, {"y": yy, "d": doy}, {"y": "year", "d": "day_of_year"})
    check = out.inputs["composite_check"]
    assert check["usual_within_year_spacing"] == 16 and check["year_end_crossings"] == 2 * 2
    assert check["rows_off_grid"] == check["crossings_skipping_a_year"] == 0


# ===================================================================================================
# R2 season key
@pytest.mark.parametrize("cadence,kind,per_year", [
    (S.Cadence(S.CadenceKind.REGULAR, 1, S.StepUnit.MONTH), S.SeasonKeyKind.MONTH_OF_YEAR, 12),
    (S.Cadence(S.CadenceKind.REGULAR, 3, S.StepUnit.MONTH), S.SeasonKeyKind.STEP_POSITION_IN_YEAR, 4),
    (S.Cadence(S.CadenceKind.REGULAR, 2, S.StepUnit.MONTH), S.SeasonKeyKind.STEP_POSITION_IN_YEAR, 6),
    (S.Cadence(S.CadenceKind.REGULAR, 1, S.StepUnit.YEAR), S.SeasonKeyKind.CONSTANT, 1),
    (S.Cadence(S.CadenceKind.IRREGULAR), S.SeasonKeyKind.EVENT_MONTH, None),
    (SimpleNamespace(kind="regular", length=1, unit="month"), S.SeasonKeyKind.MONTH_OF_YEAR, 12),
])
def test_r2_season_keys(cadence, kind, per_year):
    out = D.derive_r02_season_key(cadence, None)
    assert out.value == S.SeasonKeySpec(kind, per_year)


def test_r2_composites_take_the_observed_count():
    cad = S.Cadence(S.CadenceKind.COMPOSITE_OF_YEAR, composites_per_year=46, composite_days=8)
    assert D.derive_r02_season_key(cad, 46).value == S.SeasonKeySpec(S.SeasonKeyKind.COMPOSITE_NUMBER, 46)
    store_form = SimpleNamespace(kind="composite_of_year", length=16, unit="day")
    assert D.derive_r02_season_key(store_form, 23).value.steps_per_year == 23
    refused("R2", D.derive_r02_season_key, cad, None)
    refused("R2", D.derive_r02_season_key, cad, 45)            # disagrees with the cadence
    refused("R2", D.derive_r02_season_key, S.Cadence(S.CadenceKind.REGULAR, 1, S.StepUnit.MONTH), 46)


def test_r2_refuses_cadences_without_a_defined_season_key():
    msg = refused("R2", D.derive_r02_season_key, S.Cadence(S.CadenceKind.REGULAR, 8, S.StepUnit.DAY), None)
    assert "D5" in msg and "= 46" in msg                        # 365.25 / 8 = 45.66, half up 46
    refused("R2", D.derive_r02_season_key, S.Cadence(S.CadenceKind.REGULAR, 5, S.StepUnit.MONTH), None)
    refused("R2", D.derive_r02_season_key, S.Cadence(S.CadenceKind.REGULAR, 2, S.StepUnit.YEAR), None)
    refused("R2", D.derive_r02_season_key, S.Cadence(S.CadenceKind.STATIC), None)
    refused("R2", D.derive_r02_season_key, S.Cadence(S.CadenceKind.EPOCH), None)


# ===================================================================================================
# R3 coverage end
GROUPS = ("g1", "g2", "g3", "g4")


def full_counts(years=range(2001, 2011), groups=GROUPS, n=100):
    return {(g, y): n for g in groups for y in years}


def test_valid_row_counter_reads_validity_only_and_listed_groups_only():
    g = np.array(["g1", "g1", "g2", "g9", "g2"])
    y = np.array([2001, 2001, 2002, 2001, 2002])
    v = np.array([True, False, True, True, True])
    joined = np.ones(5, dtype=bool)
    assert D.count_valid_rows_per_group_year(g, y, v, joined, ("g1", "g2")) == {("g1", 2001): 1,
                                                                                 ("g2", 2002): 2}
    refused("R3", D.count_valid_rows_per_group_year, g, y, v.astype(float), joined, ("g1",))
    refused("R3", D.count_valid_rows_per_group_year, g[:-1], y, v, joined, ("g1",))
    refused("R3", D.count_valid_rows_per_group_year, g, y, v, joined, ("g1", "g1"))


def test_valid_row_counter_counts_only_the_joined_rows_f2():
    # owner ruling F2: a row counts only with a valid label AND the kept drivers present
    g = np.array(["g1"] * 6)
    y = np.array([2001, 2001, 2002, 2002, 2003, 2003])
    v = np.array([True, True, True, False, True, True])
    joined = np.array([True, True, True, True, False, False])     # the drivers end after 2002
    assert D.count_valid_rows_per_group_year(g, y, v, joined, ("g1",)) == {("g1", 2001): 2,
                                                                            ("g1", 2002): 1}
    refused("R3", D.count_valid_rows_per_group_year, g, y, v, joined.astype(int), ("g1",))
    refused("R3", D.count_valid_rows_per_group_year, g, y, v, joined[:-1], ("g1",))


def test_r3_ends_where_the_drivers_end_f2():
    # labels run to 2012 but the drivers end in 2010: Y_end is the last year of joined rows
    rows = 12 * 10
    g = np.repeat(np.array(["g1", "g2"]), rows * 12)
    years = np.tile(np.repeat(np.arange(2001, 2013), rows), 2)
    valid = np.ones(len(g), dtype=bool)
    joined = years <= 2010
    counts = D.count_valid_rows_per_group_year(g, years, valid, joined, ("g1", "g2"))
    out = D.derive_r03_coverage_end(counts, ("g1", "g2"), False)
    assert out.value == 2010
    assert "kept drivers present" in out.inputs["counted"]


def test_r3_full_coverage_ends_at_the_last_year():
    out = D.derive_r03_coverage_end(full_counts(), GROUPS, False)
    assert out.value == 2010
    assert out.margins == {"C3.coverage_group_share": pytest.approx(0.5)}
    assert out.inputs["median_rows_per_group"] == {g: 100.0 for g in GROUPS}


def test_r3_half_the_groups_at_ninety_percent_is_enough():
    counts = full_counts()
    for g in ("g3", "g4"):                     # two late groups stop after the second-last year
        counts[(g, 2010)] = 0
    out = D.derive_r03_coverage_end(counts, GROUPS, False)
    assert out.value == 2010                    # exactly half qualify (>=)
    assert out.inputs["qualifying_share_by_year"]["2010"] == 0.5
    assert "borderline:C3.coverage_group_share" in out.flags
    counts[("g2", 2010)] = 89                   # 89 < 90% of 100
    assert D.derive_r03_coverage_end(counts, GROUPS, False).value == 2009
    counts[("g2", 2010)] = 90                   # 90 = 90% of 100 (inclusive)
    assert D.derive_r03_coverage_end(counts, GROUPS, False).value == 2010


def test_r3_median_counts_zero_row_years_between_first_and_last_d7():
    counts = {("g1", y): 100 for y in (2001, 2005, 2006)}        # 2002-2004 have no row
    counts.update({("g1", y): 100 for y in (2007,)})
    out = D.derive_r03_coverage_end(counts, ("g1",), False)
    # years 2001..2007 -> counts 100,0,0,0,100,100,100 -> median 100
    assert out.inputs["median_rows_per_group"] == {"g1": 100.0}
    sparse = {("g1", 2001): 100, ("g1", 2007): 100}               # median over 7 years is 0
    zero = D.derive_r03_coverage_end(sparse, ("g1",), False)
    assert "zero_median:g1" in zero.flags and zero.value == 2007


def test_r3_events_take_the_last_year_with_any_row():
    counts = {("g1", 2001): 5, ("g2", 2004): 1, ("g1", 2003): 0}
    out = D.derive_r03_coverage_end(counts, ("g1", "g2"), True)
    assert out.value == 2004 and out.margins == {}


def test_r3_refusals():
    counts = full_counts()
    refused("R3", D.derive_r03_coverage_end, counts, GROUPS + ("empty",), False)   # a group without rows
    refused("R3", D.derive_r03_coverage_end, counts, ("g1", "g2"), False)          # unknown group in counts
    refused("R3", D.derive_r03_coverage_end, {("g1", 2001): -1}, ("g1",), False)
    refused("R3", D.derive_r03_coverage_end, {("g1", 2001.5): 3}, ("g1",), False)
    refused("R3", D.derive_r03_coverage_end, counts, (), False)
    refused("R3", D.derive_r03_coverage_end, counts, "g1", False)
    # no year qualifies: disjoint two-year spans, so every year has 1 of 4 groups at its usual rows
    staggered = {("g%d" % i, 1998 + 2 * i + k): 100 for i in range(1, 5) for k in (0, 1)}
    msg = refused("R3", D.derive_r03_coverage_end, staggered, GROUPS, False)
    assert "best share 0.250" in msg


# ===================================================================================================
# R4 first year
def lag(name, steps, cadence):
    return timing.Lag(column=name, steps=steps, column_cadence=cadence, floor_reason=None)


def test_r4_rounds_each_lag_up_to_whole_years():
    lags = {"m2": lag("m2", 2, MONTH), "m0": lag("m0", 0, MONTH), "y1": lag("y1", 1, YEAR)}
    out = D.derive_r04_first_year(2002, lags)
    assert out.value == 2003
    assert out.inputs["lags"]["m2"]["years"] == 1 and out.inputs["set_by"] == ["m2", "y1"]
    assert D.derive_r04_first_year(2002, {"m13": lag("m13", 13, MONTH)}).value == 2004
    assert D.derive_r04_first_year(2002, {"y2": lag("y2", 2, YEAR)}).value == 2004
    assert D.derive_r04_first_year(2002, {"m0": lag("m0", 0, MONTH)}).value == 2002


def test_r4_composite_day_and_store_form_cadences():
    comp = composite(8, per_year=46)
    assert D.derive_r04_first_year(2000, {"c": lag("c", 1, comp)}).value == 2001
    assert D.derive_r04_first_year(2000, {"c": lag("c", 47, composite(8))}).value == 2002
    ten_day = C.Cadence(C.CadenceKind.REGULAR, length=10, unit=C.StepUnit.DAY)
    assert D.derive_r04_first_year(2000, {"d": lag("d", 40, ten_day)}).value == 2002   # 400 days
    store = SimpleNamespace(kind="regular", length=1, unit="month")
    assert D.derive_r04_first_year(2000, {"s": lag("s", 3, store)}).value == 2001


def test_r4_guard_needs_r8_over_exactly_the_kept_columns():
    cols = {"x": column("x"), "elev": column("elev", cadence=STATIC)}
    r8 = D.derive_r08_feature_lags(cols, MONTHLY_TARGET, MONTH)
    assert D.check_r08_covers_kept_columns(("x", "elev"), r8) is None
    static_only = D.derive_r08_feature_lags({"elev": cols["elev"]}, MONTHLY_TARGET, MONTH)
    assert static_only.value == {}
    D.check_r08_covers_kept_columns(("elev",), static_only)        # every kept column has no steps
    assert D.derive_r04_first_year(2002, static_only.value).flags == ("no_lag_sources",)
    empty = D.derive_r08_feature_lags({}, MONTHLY_TARGET, MONTH)
    assert "is empty" in refused("R4", D.check_r08_covers_kept_columns, ("x",), empty)
    assert "not kept" in refused("R4", D.check_r08_covers_kept_columns, ("x",), r8)
    assert "did not handle" in refused("R4", D.check_r08_covers_kept_columns, ("x", "elev", "z"), r8)
    refused("R4", D.check_r08_covers_kept_columns, ("x",), D.derive_r04_first_year(2002, {}))
    refused("R4", D.check_r08_covers_kept_columns, "x", r8)
    refused("R4", D.check_r08_covers_kept_columns, ("x", "x"), r8)


def test_r4_empty_map_is_flagged_and_bad_lags_refused():
    out = D.derive_r04_first_year(2002, {})
    assert out.value == 2002 and out.flags == ("no_lag_sources",)
    refused("R4", D.derive_r04_first_year, 2002, {"a": lag("b", 1, MONTH)})
    refused("R4", D.derive_r04_first_year, 2002, {"a": lag("a", -1, MONTH)})
    refused("R4", D.derive_r04_first_year, 2002, {"a": lag("a", 1, STATIC)})
    refused("R4", D.derive_r04_first_year, "2002", {})


# ===================================================================================================
# R5 - R7 windows
def test_r5_full_record_and_margins():
    out = D.derive_r05_test_window(2003, 2023)
    assert out.value == S.TestWindowPlan((2020, 2021, 2022, 2023), 3, ())
    assert out.margins["years_needed_full"] == 13 and out.flags == ()
    edge = D.derive_r05_test_window(2003, 2010)                  # exactly 8 years: no ladder
    assert edge.value.inner_score_years == 3 and edge.value.ladder_steps == ()
    assert "borderline:years_needed_full" in edge.flags


def test_r5_short_record_ladder():
    seven = D.derive_r05_test_window(2003, 2009)
    assert seven.value == S.TestWindowPlan((2006, 2007, 2008, 2009), 2, ("short record: inner score 2",))
    assert "short record: inner score 2" in seven.flags
    six = D.derive_r05_test_window(2003, 2008)
    assert six.value == S.TestWindowPlan((2006, 2007, 2008), 2,
                                         ("short record: inner score 2", "short record: test 3"))
    msg = refused("R5", D.derive_r05_test_window, 2003, 2007)
    assert "5 years" in msg


def test_r6_train_end_and_refusals():
    assert D.derive_r06_train_end((2019, 2020, 2021, 2022)).value == 2018
    for bad in [(2019, 2021), (), (2021, 2020), "2019", (2019.0, 2020.0)]:
        refused("R6", D.derive_r06_train_end, bad)


def test_r7_inner_windows_normal_and_short():
    plan = D.derive_r05_test_window(2003, 2023).value
    out = D.derive_r07_inner_windows(2003, 2023, plan, 2019)
    assert out.value == S.Windows(2003, 2023, (2020, 2021, 2022, 2023), 2019, (2003, 2016),
                                  (2017, 2018, 2019))
    short = D.derive_r05_test_window(2003, 2009).value
    w = D.derive_r07_inner_windows(2003, 2009, short, 2005).value
    assert w.inner_score == (2004, 2005) and w.inner_fit == (2003, 2003)


def test_r7_refusals():
    plan = D.derive_r05_test_window(2003, 2023).value
    refused("R7", D.derive_r07_inner_windows, 2003, 2023, plan, 2018)          # train end off
    refused("R7", D.derive_r07_inner_windows, 2003, 2024, plan, 2019)          # test window not at Y_end
    tight = S.TestWindowPlan((2017, 2018, 2019, 2020), 3, ())
    msg = refused("R7", D.derive_r07_inner_windows, 2015, 2020, tight, 2016)   # fit 2015..2013
    assert "inner fit" in msg
    refused("R7", D.derive_r07_inner_windows, 2003, 2023, S.TestWindowPlan((2020, 2021, 2022, 2023), 0, ()),
            2019)


# ===================================================================================================
# R8 feature lags (through timing.compute_lag)
def test_r8_lags_every_time_varying_column_and_skips_static():
    cols = {"x": column("x"),
            "ann": column("ann", cadence=YEAR, window=PLAIN_YEAR),
            "burn": column("burn", co_measured=True),
            "elev": column("elev", cadence=STATIC)}
    out = D.derive_r08_feature_lags(cols, MONTHLY_TARGET, MONTH)
    assert {k: v.steps for k, v in out.value.items()} == {"x": 0, "ann": 1, "burn": 1}
    assert out.value["burn"].floor_reason == "co_measured"
    assert out.inputs["static"] == ["elev"]
    assert out.inputs["columns"]["ann"]["cadence"] == {"kind": "regular", "length": 1, "unit": "year"}
    assert "unanswered:x:co_measured_with_target" in out.flags
    direct = timing.compute_lag(cols["x"], MONTHLY_TARGET, MONTH, "nowcast")
    assert (out.value["x"].steps, out.value["x"].floor_reason) == (direct.steps, direct.floor_reason)
    assert out.value["x"].column_cadence == S.Cadence(S.CadenceKind.REGULAR, 1, S.StepUnit.MONTH)


def test_r8_builds_each_lag_from_one_trace_equal_to_compute_lag():
    tgt = target(computed_from=("src",))
    cols = {"x": column("x"), "c": column("c", stamp=STAMP.PERIOD_CENTRE, window=CENTRED_MONTH),
            "ann": column("ann", cadence=YEAR, window=PLAIN_YEAR, co_measured=False),
            "burn": column("burn", co_measured=True), "src": column("src", co_measured=False)}
    out = D.derive_r08_feature_lags(cols, tgt, MONTH)
    for name, col in cols.items():
        direct = timing.compute_lag(col, tgt, MONTH, "nowcast")
        got = out.value[name]
        assert (got.column, got.steps, got.floor_reason) == (direct.column, direct.steps,
                                                             direct.floor_reason), name
        assert got.column_cadence == S.Cadence(S.CadenceKind.REGULAR, 1,
                                               S.StepUnit(direct.column_cadence.unit.value))
    assert out.value["src"].floor_reason == "computed_from"


def test_r8_lists_epoch_and_irregular_columns_without_a_lag():
    cols = {"x": column("x"), "frozen": column("frozen", cadence=EPOCH),
            "visits": column("visits", cadence=EVENTS), "elev": column("elev", cadence=STATIC)}
    out = D.derive_r08_feature_lags(cols, MONTHLY_TARGET, MONTH)
    assert set(out.value) == {"x"} and set(out.inputs["columns"]) == {"x"}
    assert (out.inputs["static"], out.inputs["epoch"], out.inputs["irregular"]) == (
        ["elev"], ["frozen"], ["visits"])
    for name in ("frozen", "visits"):                 # compute_lag itself refuses them
        with pytest.raises(TimingRefusal):
            timing.compute_lag(cols[name], MONTHLY_TARGET, MONTH, "nowcast")
    D.check_r08_covers_kept_columns(tuple(cols), out)


def test_r8_refuses_what_compute_lag_refuses_and_bad_keys():
    unknown = column("idx", window=win(None, U.MONTH, A.UNKNOWN))
    with pytest.raises(TimingRefusal) as info:
        D.derive_r08_feature_lags({"idx": unknown}, MONTHLY_TARGET, MONTH)
    assert info.value.rule == "G-LAG"
    refused("R8", D.derive_r08_feature_lags, {"other": column("x")}, MONTHLY_TARGET, MONTH)
    open_target = target(window=win(None, U.MONTH, A.UNKNOWN))
    with pytest.raises(TimingRefusal):
        D.derive_r08_feature_lags({"x": column("x")}, open_target, MONTH)


def test_r8_writes_store_form_facts_in_the_approved_cadence_shape():
    # facts as the package schema gives them: plain strings, a store-form composite cadence
    plain = SimpleNamespace(name="p", cadence=SimpleNamespace(kind="regular", length=1, unit="year"),
                            stamp="period_end", window=SimpleNamespace(length=1, unit="year",
                                                                       align="backward", max_length=None),
                            fact_status="unverified", co_measured_with_target=False)
    out = D.derive_r08_feature_lags({"p": plain}, MONTHLY_TARGET, MONTH)
    assert out.value["p"].column_cadence == S.Cadence(S.CadenceKind.REGULAR, 1, S.StepUnit.YEAR)
    assert D.derived_entry(out)["value"]["p"]["column_cadence"] == {
        "kind": "regular", "length": 1, "unit": "year", "composites_per_year": None,
        "composite_days": None}
    assert out.flags == ()                                         # co_measured answered: no flag


def test_r8_and_r4_chain_on_an_annual_target():
    cols = {"same_year": column("same_year", cadence=YEAR, window=PLAIN_YEAR)}
    lags = D.derive_r08_feature_lags(cols, ANNUAL_TARGET, YEAR).value
    assert lags["same_year"].steps == 0                             # D25 (a)
    assert D.derive_r04_first_year(2001, lags).value == 2001


# ===================================================================================================
# R10 leads (owner ruling I1: 6 and 12 months, generic for every package, plus lead 0 as the contract)
@pytest.mark.parametrize("per_year,leads,merged,not_supplied", [
    (12, (6, 12), {}, ()),                        # monthly: leads 6 and 12 (no lead 1 or 3)
    (1, (1,), {1: (6, 12)}, ()),                  # annual: 6 and 12 months round to 1 year and merge
    (6, (3, 6), {}, ()),                          # 2-month step
    (4, (2, 4), {}, ()),                          # quarterly
    (46, (23, 46), {}, ()),                       # 8-day composites: 23, 46
    (23, (12, 23), {}, ()),                       # 16-day composites: 11.5 -> 12 (half up), 23
])
def test_r10_grid_leads(per_year, leads, merged, not_supplied):
    out = D.derive_r10_leads(S.SeasonKeySpec(S.SeasonKeyKind.MONTH_OF_YEAR, per_year), False)
    assert out.value.leads == leads and out.value.merged == merged
    assert out.value.not_supplied == not_supplied and out.value.lead_unit == S.LeadUnit.STEPS
    assert out.value.requested_months == (6, 12) and out.value.contract_lead_zero is True
    assert not {1, 3} & set(out.value.leads) or per_year < 12          # leads 1 and 3 run nowhere monthly


def test_r10_merge_is_flagged():
    out = D.derive_r10_leads(S.SeasonKeySpec(S.SeasonKeyKind.CONSTANT, 1), False)
    assert out.flags == ("merged:1<-6+12",)
    assert out.inputs["before_rounding"] == {"6": "1/2", "12": "1/1"}


def test_r10_rounds_half_up_and_lists_a_lead_under_one_step_as_not_supplied(monkeypatch):
    """The rounding and the not-supplied rule stay generic (R10, D4), shown with a stood-in lead list."""
    monkeypatch.setattr(K, "LEAD_MONTHS", (1, 3, 6, 12))
    out = D.derive_r10_leads(S.SeasonKeySpec(S.SeasonKeyKind.CONSTANT, 1), False)
    assert out.value.leads == (1,) and out.value.not_supplied == (1, 3)
    assert out.flags == ("merged:1<-6+12", "not_supplied:1", "not_supplied:3")


def test_r10_event_leads_in_days():
    out = D.derive_r10_leads(S.SeasonKeySpec(S.SeasonKeyKind.EVENT_MONTH, None), True)
    assert out.value.leads == (183, 365) and out.value.lead_unit == S.LeadUnit.DAYS


def test_r10_refusals(monkeypatch):
    refused("R10", D.derive_r10_leads, S.SeasonKeySpec(S.SeasonKeyKind.MONTH_OF_YEAR, None), False)
    refused("R10", D.derive_r10_leads, S.SeasonKeySpec(S.SeasonKeyKind.MONTH_OF_YEAR, 0), False)
    refused("R10", D.derive_r10_leads, S.SeasonKeySpec(S.SeasonKeyKind.EVENT_MONTH, None), False)
    refused("R10", D.derive_r10_leads, S.SeasonKeySpec(S.SeasonKeyKind.MONTH_OF_YEAR, 12), True)
    monkeypatch.setattr(K, "LEAD_ROUNDING", "half_even")
    refused("R10", D.derive_r10_leads, S.SeasonKeySpec(S.SeasonKeyKind.MONTH_OF_YEAR, 12), False)


# ===================================================================================================
# R11 cuts (through timing.cuts_for_leads)
def monthly_windows():
    return S.Windows(2003, 2023, (2020, 2021, 2022, 2023), 2019, (2003, 2016), (2017, 2018, 2019))


def test_r11_grid_cuts_are_timings_and_record_the_year_end_steps():
    leads = D.derive_r10_leads(S.SeasonKeySpec(S.SeasonKeyKind.MONTH_OF_YEAR, 12), False).value
    out = D.derive_r11_cuts(monthly_windows(), leads, MONTH)
    assert out.value == dict(timing.cuts_for_leads(monthly_windows(), leads, MONTH))
    assert sorted(out.value) == [0, 6, 12]
    end = 2019 * K.MONTHS_PER_YEAR + K.MONTHS_PER_YEAR
    assert out.inputs["train_end_step"] == end and out.value[6].fit_cut == end - 5
    assert D.derived_entry(out)["value"]["12"]["guard_cut"] == out.value[12].guard_cut


def test_r11_event_cuts_in_days_and_refusals():
    leads = D.derive_r10_leads(S.SeasonKeySpec(S.SeasonKeyKind.EVENT_MONTH, None), True).value
    out = D.derive_r11_cuts(monthly_windows(), leads, S.Cadence(S.CadenceKind.IRREGULAR))
    assert out.value[183].fit_cut == dt.date(2020, 1, 1).toordinal() - 183
    assert "train_end_step" not in out.inputs
    bad = S.Windows(2003, 2023, (2020, 2021, 2022, 2023), 2018, (2003, 2016), (2017, 2018, 2019))
    grid_leads = D.derive_r10_leads(S.SeasonKeySpec(S.SeasonKeyKind.MONTH_OF_YEAR, 12), False).value
    with pytest.raises(TimingRefusal):
        D.derive_r11_cuts(bad, grid_leads, MONTH)


# ===================================================================================================
# R22 links and R23 c (label-only donor view, D16)
def donor(y, scope="picked", cut_kind="fit", lead=0, cut=100, times=None, units=None):
    y = np.asarray(y, dtype=float)
    n = len(y)
    return DonorView(groups=("d1",), cut=cut, cut_kind=cut_kind, lead=lead, unit_scope=scope,
                     unit_ids=np.array(["u%d" % i for i in range(n)]) if units is None else units,
                     times=cut - np.arange(n) if times is None else np.asarray(times),
                     group_of_row=np.array(["d1"] * n), y=y, row_key_hash="ab" * 32)


RICH = [0.0, 0.0, 0.1, 0.4, 0.9, 1.0]


@pytest.mark.parametrize("legal,expected", [
    ((0.0, float("inf")), (S.Link.IDENTITY, S.Link.LOG_C)),
    ((0.0, 1.0), (S.Link.IDENTITY, S.Link.LOG_C, S.Link.ARCSINE)),
    ((-0.2, 1.0), (S.Link.IDENTITY,)),
    ((0.5, 10.0), (S.Link.IDENTITY, S.Link.LOG_C)),             # no [0, UB]: no arcsine
])
def test_r22_links_follow_the_legal_range(legal, expected):
    out = D.derive_r22_links(legal, donor(RICH))
    assert out.value == expected
    assert out.input_hashes["donor_row_key_hash"] == "ab" * 32
    assert out.inputs["donor"]["unit_scope"] == "picked"


def test_r22_donor_rows_gate_the_log_and_arcsine_links():
    two = D.derive_r22_links((0.0, 1.0), donor([0.0, 1.0, 1.0, 0.0]))
    assert two.value == (S.Link.IDENTITY,)                      # only 2 distinct values
    assert two.margins == {"S2.link_distinct_values_above": 0.0}
    assert "borderline:S2.link_distinct_values_above" in two.flags
    no_positive = D.derive_r22_links((0.0, 1.0), donor([-3.0, -2.0, -1.0]))
    assert no_positive.value == (S.Link.IDENTITY, S.Link.ARCSINE)


@pytest.mark.parametrize("legal", [(1.0, 1.0), (2.0, 1.0), (float("nan"), 1.0), ("0", 1.0), (0.0,)])
def test_r22_refuses_a_bad_legal_range(legal):
    refused("R22", D.derive_r22_links, legal, donor(RICH))


def test_r22_refuses_a_donor_view_it_may_not_read():
    refused("R22", D.derive_r22_links, (0.0, 1.0), donor(RICH, scope="all_donor_units"))
    refused("R22", D.derive_r22_links, (0.0, 1.0), donor(RICH, lead=3))
    refused("R22", D.derive_r22_links, (0.0, 1.0), donor(RICH, cut_kind="guard"))
    refused("R22", D.derive_r22_links, (0.0, 1.0), donor([]))
    refused("R22", D.derive_r22_links, (0.0, 1.0), donor([0.1, float("nan"), 0.3]))
    refused("R22", D.derive_r22_links, (0.0, 1.0), SimpleNamespace(y=np.array([1.0])))


@pytest.mark.parametrize("rule,call", [("R22", lambda v: D.derive_r22_links((0.0, 1.0), v)),
                                       ("R23", D.derive_r23_c_for_cut)])
def test_donor_rows_must_sit_at_or_before_the_cut_in_its_unit(rule, call):
    assert "after the view's cut 100" in refused(rule, call, donor(RICH, times=[100, 101, 99, 98, 97, 96]))
    refused(rule, call, donor(RICH, times=np.arange(6, dtype=float)))       # not whole steps or days
    refused(rule, call, donor(RICH, times=[100, 99]))                         # one time per row
    refused(rule, call, donor(RICH, units=np.array(["u1"])))                  # one unit id per row
    assert call(donor(RICH, times=[100] * 6)).rule_id == rule                 # at the cut is allowed


def test_r23_c_is_the_first_percentile_of_positive_donor_y():
    y = np.r_[np.zeros(50), np.linspace(0.01, 5.0, 500)]
    out = D.derive_r23_c_for_cut(donor(y))
    assert out.value == pytest.approx(float(np.percentile(y[y > 0], 1)))
    assert out.inputs["positive_rows"] == 500 and out.inputs["donor"]["cut"] == 100
    assert D.derive_r23_c_for_cut(donor(y, lead=6)).inputs["donor"]["lead"] == 6   # one c per lead cut


def test_r23_uses_the_one_formula_and_the_run_check_compares_it():
    y = np.r_[np.zeros(50), np.linspace(0.01, 5.0, 500)]
    out = D.derive_r23_c_for_cut(donor(y, lead=3))
    c, positive = D.c_from_donor_y(y)
    assert out.value == c and positive == 500
    assert D.c_from_donor_y(np.r_[y, np.nan, np.inf, -np.inf]) == (c, 500)   # positive FINITE values
    assert D.check_r23_matches_run(out, 3, 100, c, "ab" * 32) is None
    assert "differ from plan's" in refused("R23", D.check_r23_matches_run, out, 3, 100, c, "cd" * 32)
    refused("R23", D.check_r23_matches_run, out, 3, 100, c * (1 + 1e-12), "ab" * 32)
    refused("R23", D.check_r23_matches_run, out, 0, 100, c, "ab" * 32)       # another lead
    refused("R23", D.check_r23_matches_run, out, 3, 99, c, "ab" * 32)        # another cut
    refused("R23", D.check_r23_matches_run, D.derive_r28_clip_bounds((0.0, 1.0)), 3, 100, c, "ab" * 32)
    refused("R23", D.c_from_donor_y, np.array([0.0, -1.0, np.nan]))
    refused("R23", D.c_from_donor_y, np.array([["a"]]))


def test_r23_refusals():
    refused("R23", D.derive_r23_c_for_cut, donor([0.0, 0.0, -1.0]))
    refused("R23", D.derive_r23_c_for_cut, donor(RICH, cut_kind="guard"))          # D63 (a)
    refused("R23", D.derive_r23_c_for_cut, donor(RICH, scope="all_donor_units"))
    refused("R23", D.derive_r23_c_for_cut, donor([]))


# ===================================================================================================
# R28 clip bounds
def test_r28_clip_bounds_keep_an_open_upper_end():
    out = D.derive_r28_clip_bounds((0, float("inf")))
    assert out.value == (0.0, float("inf")) and out.inputs["upper_unbounded"] is True
    assert D.derived_entry(out)["value"] == [0.0, "inf"]
    assert D.derive_r28_clip_bounds((-0.2, 1.0)).value == (-0.2, 1.0)
    for bad in [(1.0, 1.0), (1.0, 0.0), (float("nan"), 1.0), (None, 1.0), (0.0, 1.0, 2.0)]:
        refused("R28", D.derive_r28_clip_bounds, bad)
