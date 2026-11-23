"""io science: integer step index, step bounds, dense grid, predecessor lookup (R1, R30, G-CALENDAR).

Synthetic frames only; every branch of treeroute/io/steps.py. The real-file smoke is in
test_io_science_smoke.py.
"""

import datetime
from enum import Enum
from types import SimpleNamespace as NS

import numpy as np
import pytest

from treeroute.errors import RefusedError
from treeroute.io.steps import (DenseGrid, build_dense_grid, cadence_identity, cadence_view,
                                predecessor_index, step_bounds, step_containing, step_index)

MONTHLY = NS(kind="regular", length=1, unit="month")
ANNUAL = NS(kind="regular", length=1, unit="year")
COMP8 = NS(kind="composite_of_year", length=None, unit=None, composites_per_year=46, composite_days=8)
YM = {"yr": "year", "mo": "month"}


def d(y, m, day):
    return datetime.date(y, m, day)


def ords(*dates):
    return [x.toordinal() for x in dates]


class Part(Enum):  # stands in for the proposed common.CalendarPart
    YEAR = "year"
    MONTH = "month"


class Kind(Enum):
    REGULAR = "regular"


class Unit(Enum):
    MONTH = "month"


# ---------------------------------------------------------------------------------------------------
# step_index
def test_monthly_index_is_year_times_months_plus_month_without_subtracting_one():
    s = step_index({"yr": np.array([2010, 2010, 2011]), "mo": np.array([1, 12, 1])}, YM, MONTHLY)
    assert s.dtype == np.int64
    assert s.tolist() == [2010 * 12 + 1, 2010 * 12 + 12, 2011 * 12 + 1]
    assert s[2] - s[1] == 1  # December to January is one step


def test_monthly_index_accepts_enum_facts_and_enum_cadence():
    cad = NS(kind=Kind.REGULAR, length=1, unit=Unit.MONTH)
    s = step_index({"a": np.array([2003]), "b": np.array([4])}, {"a": Part.YEAR, "b": Part.MONTH}, cad)
    assert s.tolist() == [2003 * 12 + 4]


def test_monthly_index_from_a_date_column_and_from_date_objects():
    dates = np.array(["2010-01-15", "2010-02-28", "2012-12-01"], dtype="datetime64[D]")
    s = step_index({"dt": dates}, {"dt": "date"}, MONTHLY)
    assert s.tolist() == [2010 * 12 + 1, 2010 * 12 + 2, 2012 * 12 + 12]
    objs = np.array([d(2010, 1, 15), datetime.datetime(2010, 2, 28)], dtype=object)
    assert step_index({"dt": objs}, {"dt": "date"}, MONTHLY).tolist() == [2010 * 12 + 1, 2010 * 12 + 2]
    ns = np.array(["2010-03-01T00:00:00"], dtype="datetime64[ns]")
    assert step_index({"dt": ns}, {"dt": "date"}, MONTHLY).tolist() == [2010 * 12 + 3]


def test_date_and_explicit_parts_must_agree():
    dates = np.array(["2010-01-15", "2010-02-28"], dtype="datetime64[D]")
    cols = {"dt": dates, "yr": np.array([2010, 2010]), "mo": np.array([1, 2])}
    facts = {"dt": "date", "yr": "year", "mo": "month"}
    assert step_index(cols, facts, MONTHLY).tolist() == [2010 * 12 + 1, 2010 * 12 + 2]
    cols["mo"] = np.array([1, 3])
    with pytest.raises(RefusedError, match="disagrees with the date"):
        step_index(cols, facts, MONTHLY)


def test_date_column_refuses_nat_time_of_day_and_text():
    with pytest.raises(RefusedError, match="NaT"):
        step_index({"dt": np.array(["NaT"], dtype="datetime64[D]")}, {"dt": "date"}, MONTHLY)
    with pytest.raises(RefusedError, match="time of day"):
        step_index({"dt": np.array(["2010-01-01T06"], dtype="datetime64[h]")}, {"dt": "date"}, MONTHLY)
    with pytest.raises(RefusedError, match="time of day"):
        step_index({"dt": np.array([datetime.datetime(2010, 1, 1, 6)], dtype=object)}, {"dt": "date"}, MONTHLY)
    with pytest.raises(RefusedError, match="not a date"):
        step_index({"dt": np.array(["2010-01-01"], dtype=object)}, {"dt": "date"}, MONTHLY)
    with pytest.raises(RefusedError, match="dtype"):
        step_index({"dt": np.array(["2010-01-01"])}, {"dt": "date"}, MONTHLY)


@pytest.mark.parametrize("month", [0, 13])
def test_month_out_of_range_is_refused(month):
    with pytest.raises(RefusedError, match="months outside"):
        step_index({"yr": np.array([2010]), "mo": np.array([month])}, YM, MONTHLY)


def test_monthly_refuses_an_unused_day_of_year_column_and_a_missing_month():
    cols = {"yr": np.array([2010]), "mo": np.array([1]), "doy": np.array([1])}
    with pytest.raises(RefusedError, match="does not use"):
        step_index(cols, {"yr": "year", "mo": "month", "doy": "day_of_year"}, MONTHLY)
    with pytest.raises(RefusedError, match="needs the calendar part"):
        step_index({"yr": np.array([2010])}, {"yr": "year"}, MONTHLY)


def test_annual_index_is_the_year_and_refuses_a_month_column():
    assert step_index({"yr": np.array([2003, 2023])}, {"yr": "year"}, ANNUAL).tolist() == [2003, 2023]
    with pytest.raises(RefusedError, match="does not use"):
        step_index({"yr": np.array([2003]), "mo": np.array([1])}, YM, ANNUAL)
    dates = np.array(["2003-07-01"], dtype="datetime64[D]")
    assert step_index({"dt": dates}, {"dt": "date"}, ANNUAL).tolist() == [2003]


def test_composite_index_is_year_times_composites_plus_number():
    cols = {"yr": np.array([2010, 2010, 2010, 2011]), "doy": np.array([1, 9, 361, 1])}
    s = step_index(cols, {"yr": "year", "doy": "day_of_year"}, COMP8)
    assert s.tolist() == [2010 * 46 + 1, 2010 * 46 + 2, 2010 * 46 + 46, 2011 * 46 + 1]
    assert s[3] - s[2] == 1  # the last composite of a year is followed by the first of the next


def test_composite_index_from_dates_and_from_the_store_form_of_the_cadence():
    dates = np.array(["2010-01-09", "2012-12-26"], dtype="datetime64[D]")
    assert step_index({"dt": dates}, {"dt": "date"}, COMP8).tolist() == [2010 * 46 + 2, 2012 * 46 + 46]
    store_form = NS(kind="composite_of_year", length=16, unit="day", composites_per_year=23)
    s = step_index({"yr": np.array([2010]), "doy": np.array([17])}, {"yr": "year", "doy": "day_of_year"},
                   store_form)
    assert s.tolist() == [2010 * 23 + 2]


def test_composite_spacing_break_and_number_above_the_year_count_are_refused():
    facts = {"yr": "year", "doy": "day_of_year"}
    with pytest.raises(RefusedError, match="spacing"):
        step_index({"yr": np.array([2010]), "doy": np.array([2])}, facts, COMP8)
    short = NS(kind="composite_of_year", composites_per_year=45, composite_days=8)
    with pytest.raises(RefusedError, match="above composites_per_year"):
        step_index({"yr": np.array([2010]), "doy": np.array([361])}, facts, short)


def test_day_of_year_out_of_range_is_refused():
    facts = {"yr": "year", "doy": "day_of_year"}
    with pytest.raises(RefusedError, match="days of year outside"):
        step_index({"yr": np.array([2010]), "doy": np.array([367])}, facts, COMP8)
    with pytest.raises(RefusedError, match="days of year outside"):
        step_index({"yr": np.array([2010]), "doy": np.array([366])}, facts, COMP8)  # not a leap year
    with pytest.raises(RefusedError, match="days of year outside"):
        step_index({"yr": np.array([2010]), "doy": np.array([0])}, facts, COMP8)
    # 366 is a real day in a leap year; composite 46 starts on day 361 and 366 is off its spacing
    with pytest.raises(RefusedError, match="spacing"):
        step_index({"yr": np.array([2012]), "doy": np.array([366])}, facts, COMP8)


def test_composite_cadence_without_its_year_count_is_refused():
    with pytest.raises(RefusedError, match="composites_per_year"):
        cadence_view(NS(kind="composite_of_year", length=8, unit="day"))
    with pytest.raises(RefusedError, match="composite length"):
        cadence_view(NS(kind="composite_of_year", composites_per_year=46))


@pytest.mark.parametrize("cad", [NS(kind="regular", length=10, unit="day"),
                                 NS(kind="regular", length=1, unit="day"),
                                 NS(kind="regular", length=2, unit="month"),
                                 NS(kind="regular", length=5, unit="year")])
def test_regular_steps_without_a_fixed_origin_are_refused(cad):
    # D29's origin (the first day of the WHOLE target table) is carried by neither the rows nor the
    # cadence: counting from the rows given would number a chunk on its own (the same 10-day dates
    # gave 0..5 whole and 0..2 for the last three alone), so these steps are refused for now.
    dates = np.array(["2010-01-01", "2010-01-11", "2010-01-21"], dtype="datetime64[D]")
    with pytest.raises(RefusedError, match="fixed origin") as info:
        step_index({"dt": dates}, {"dt": "date"}, cad)
    assert "owner decision" in str(info.value)
    with pytest.raises(RefusedError, match="fixed origin"):
        step_index({"yr": np.array([2010]), "doy": np.array([1])}, {"yr": "year", "doy": "day_of_year"}, cad)


def test_empty_table_gives_an_empty_index():
    out = step_index({"dt": np.array([], dtype="datetime64[D]")}, {"dt": "date"}, MONTHLY)
    assert out.dtype == np.int64 and out.size == 0
    out = step_index({"yr": np.array([], dtype=int)}, {"yr": "year"}, ANNUAL)
    assert out.dtype == np.int64 and out.size == 0


def test_cadence_identity_ignores_the_form_a_cadence_is_written_in():
    store_form = NS(kind="composite_of_year", length=16, unit="day", composites_per_year=23)
    proposed = NS(kind="composite_of_year", length=None, unit=None, composites_per_year=23,
                  composite_days=16)
    assert cadence_identity(cadence_view(store_form)) == cadence_identity(cadence_view(proposed))
    assert cadence_identity(cadence_view(COMP8)) != cadence_identity(cadence_view(proposed))
    assert cadence_identity(cadence_view(MONTHLY)) == ("regular", 1, "month")
    assert cadence_identity(cadence_view(MONTHLY)) != cadence_identity(cadence_view(ANNUAL))
    assert cadence_identity(cadence_view(NS(kind="static", length=1, unit="year"))) == ("static",)


def test_a_composite_cadence_whose_two_lengths_disagree_is_refused():
    both = NS(kind="composite_of_year", length=16, unit="day", composites_per_year=23, composite_days=16)
    assert cadence_view(both).composite_days == 16
    with pytest.raises(RefusedError, match="disagree"):
        cadence_view(NS(kind="composite_of_year", length=16, unit="day", composites_per_year=23,
                        composite_days=8))


@pytest.mark.parametrize("kind", ["irregular", "static", "epoch"])
def test_cadences_without_steps_are_refused(kind):
    with pytest.raises(RefusedError):
        step_index({"yr": np.array([2010])}, {"yr": "year"}, NS(kind=kind))


def test_bad_facts_and_columns_are_refused():
    with pytest.raises(RefusedError, match="name different"):
        step_index({"yr": np.array([2010])}, {"year": "year"}, ANNUAL)
    with pytest.raises(RefusedError, match="both hold"):
        step_index({"a": np.array([2010]), "b": np.array([2010])}, {"a": "year", "b": "year"}, ANNUAL)
    with pytest.raises(RefusedError, match="unknown calendar part"):
        step_index({"a": np.array([2010])}, {"a": "week"}, ANNUAL)
    with pytest.raises(RefusedError, match="different lengths"):
        step_index({"yr": np.array([2010, 2011]), "mo": np.array([1])}, YM, MONTHLY)
    with pytest.raises(RefusedError, match="no time column"):
        step_index({}, {}, ANNUAL)
    with pytest.raises(RefusedError, match="unknown cadence kind"):
        step_index({"yr": np.array([2010])}, {"yr": "year"}, NS(kind="weekly"))
    with pytest.raises(RefusedError, match="positive length"):
        cadence_view(NS(kind="regular", length=0, unit="month"))
    with pytest.raises(RefusedError, match="unknown cadence unit"):
        cadence_view(NS(kind="regular", length=1, unit="week"))


def test_integer_parsing_of_time_columns():
    assert step_index({"yr": np.array([2010.0])}, {"yr": "year"}, ANNUAL).tolist() == [2010]
    assert step_index({"yr": np.array([2010], dtype=object)}, {"yr": "year"}, ANNUAL).tolist() == [2010]
    for bad, needle in ((np.array([2010.5]), "whole"), (np.array([np.nan]), "non-finite"),
                        (np.array(["2010"]), "dtype"), (np.array([True]), "booleans"),
                        (np.array(["2010"], dtype=object), "not integers"),
                        (np.array([[2010]]), "one-dimensional")):
        with pytest.raises(RefusedError, match=needle):
            step_index({"yr": bad}, {"yr": "year"}, ANNUAL)


# ---------------------------------------------------------------------------------------------------
# step_bounds
def test_monthly_bounds_cover_the_calendar_month():
    first, last = step_bounds(np.array([2012 * 12 + 2, 2010 * 12 + 12, 2011 * 12 + 1]), MONTHLY)
    assert first.tolist() == ords(d(2012, 2, 1), d(2010, 12, 1), d(2011, 1, 1))
    assert last.tolist() == ords(d(2012, 2, 29), d(2010, 12, 31), d(2011, 1, 31))


def test_annual_bounds_cover_the_calendar_year():
    first, last = step_bounds(np.array([2011, 2012]), ANNUAL)
    assert first.tolist() == ords(d(2011, 1, 1), d(2012, 1, 1))
    assert last.tolist() == ords(d(2011, 12, 31), d(2012, 12, 31))


def test_composite_bounds_last_composite_of_a_year_is_short():
    s = np.array([2010 * 46 + 1, 2010 * 46 + 46, 2012 * 46 + 46])
    first, last = step_bounds(s, COMP8)
    assert first.tolist() == ords(d(2010, 1, 1), d(2010, 12, 27), d(2012, 12, 26))
    assert last.tolist() == ords(d(2010, 1, 8), d(2010, 12, 31), d(2012, 12, 31))
    assert (last - first + 1).tolist() == [8, 5, 6]


def test_composite_bounds_refuse_a_composite_that_starts_after_the_year():
    five = NS(kind="composite_of_year", composites_per_year=74, composite_days=5)
    first, last = step_bounds(np.array([2012 * 74 + 74]), five)  # leap year: day 366
    assert first.tolist() == last.tolist() == ords(d(2012, 12, 31))
    with pytest.raises(RefusedError, match="after 31 December"):
        step_bounds(np.array([2010 * 74 + 74]), five)


def test_bounds_invert_the_index():
    rng_days = np.arange(d(2009, 1, 1).toordinal(), d(2013, 1, 1).toordinal(), 7)
    dates = np.array([np.datetime64(datetime.date.fromordinal(int(o)), "D") for o in rng_days])
    s = step_index({"dt": dates}, {"dt": "date"}, MONTHLY)
    first, last = step_bounds(s, MONTHLY)
    assert ((first <= rng_days) & (rng_days <= last)).all()
    comp_dates = np.array([np.datetime64(d(2011, 1, 1) + datetime.timedelta(days=8 * i), "D")
                           for i in range(46)])
    sc = step_index({"dt": comp_dates}, {"dt": "date"}, COMP8)
    f2, _ = step_bounds(sc, COMP8)
    assert f2.tolist() == [x.astype(object).toordinal() for x in comp_dates]


@pytest.mark.parametrize("cad", [NS(kind="irregular"), NS(kind="static"), NS(kind="epoch"),
                                 NS(kind="regular", length=8, unit="day"),
                                 NS(kind="regular", length=2, unit="month"),
                                 NS(kind="regular", length=5, unit="year")])
def test_bounds_refuse_cadences_they_cannot_invert(cad):
    with pytest.raises(RefusedError):
        step_bounds(np.array([1]), cad)


# ---------------------------------------------------------------------------------------------------
# step_containing (the inverse of step_bounds, day by day)
@pytest.mark.parametrize("cad,steps", [
    (MONTHLY, [2011 * 12 + m for m in range(1, 13)] + [2012 * 12 + 2]),
    (ANNUAL, [2011, 2012]),
    (COMP8, [2011 * 46 + n for n in range(1, 47)] + [2012 * 46 + 46]),
    (NS(kind="composite_of_year", length=16, unit="day", composites_per_year=23), [2012 * 23 + 23])])
def test_every_day_of_a_step_gives_the_step_back(cad, steps):
    first, last = step_bounds(np.array(steps), cad)
    for s, a, b in zip(steps, first.tolist(), last.tolist()):
        days = np.arange(a, b + 1)
        assert (step_containing(days, cad) == s).all()
    assert step_containing(np.array([], dtype=np.int64), cad).tolist() == []


def test_step_containing_crosses_year_edges_and_leap_days():
    days = np.array(ords(d(2011, 12, 31), d(2012, 1, 1), d(2012, 2, 29), d(2012, 12, 31)))
    assert step_containing(days, MONTHLY).tolist() == [2011 * 12 + 12, 2012 * 12 + 1, 2012 * 12 + 2,
                                                       2012 * 12 + 12]
    assert step_containing(days, ANNUAL).tolist() == [2011, 2012, 2012, 2012]
    assert step_containing(days, COMP8).tolist() == [2011 * 46 + 46, 2012 * 46 + 1, 2012 * 46 + 8,
                                                     2012 * 46 + 46]


def test_step_containing_refusals():
    with pytest.raises(RefusedError, match="above composites_per_year"):
        step_containing(np.array(ords(d(2010, 12, 31))), NS(kind="composite_of_year", length=16,
                                                               unit="day", composites_per_year=22))
    for cad in (NS(kind="irregular"), NS(kind="static"), NS(kind="epoch"),
                NS(kind="regular", length=8, unit="day"), NS(kind="regular", length=3, unit="month")):
        with pytest.raises(RefusedError):
            step_containing(np.array(ords(d(2010, 1, 1))), cad)
    with pytest.raises(RefusedError, match="whole numbers"):
        step_containing(np.array([734000.5]), MONTHLY)


# ---------------------------------------------------------------------------------------------------
# build_dense_grid
def _census(units, groups, steps_per_unit):
    u, g, s = [], [], []
    for unit, group in zip(units, groups):
        for st in steps_per_unit:
            u.append(unit)
            g.append(group)
            s.append(st)
    return np.array(u, dtype=object), np.array(g, dtype=object), np.array(s)


def test_dense_grid_sorts_units_and_keeps_groups_aligned():
    u, g, s = _census(["b_2", "a_10", "a_9", "B_1"], ["gb", "ga", "ga", "gB"], range(5, 9))
    perm = np.random.RandomState(0).permutation(len(s))  # a test permutation, not engine code
    grid = build_dense_grid(u[perm], g[perm], s[perm], (5, 8))
    assert isinstance(grid, DenseGrid)
    assert grid.unit_ids == ("B_1", "a_10", "a_9", "b_2")  # code-point order
    assert grid.group_of_unit == ("gB", "ga", "ga", "gb")
    assert (grid.first_step, grid.n_steps) == (5, 4)


def test_dense_grid_refuses_holes_duplicates_and_rows_outside_coverage():
    u, g, s = _census(["a", "b"], ["g", "g"], range(1, 4))
    with pytest.raises(RefusedError, match="holes"):
        build_dense_grid(u[1:], g[1:], s[1:], (1, 3))
    with pytest.raises(RefusedError, match="repeat"):
        build_dense_grid(np.append(u, "a"), np.append(g, "g"), np.append(s, 2), (1, 3))
    with pytest.raises(RefusedError, match="outside the coverage"):
        build_dense_grid(u, g, s, (1, 2))
    with pytest.raises(RefusedError, match="holes"):
        build_dense_grid(u, g, s, (1, 4))  # coverage reaches a step no unit has


def test_dense_grid_refuses_a_unit_in_two_groups_and_bad_inputs():
    u, g, s = _census(["a", "b"], ["g", "h"], range(1, 3))
    g2 = g.copy()
    g2[0] = "h"
    with pytest.raises(RefusedError, match="more than one group"):
        build_dense_grid(u, g2, s, (1, 2))
    with pytest.raises(RefusedError, match="no rows"):
        build_dense_grid(np.array([], dtype=object), np.array([], dtype=object), np.array([], dtype=int), (1, 2))
    with pytest.raises(RefusedError, match="non-empty strings"):
        build_dense_grid(np.array([1, 2]), np.array(["g", "g"]), np.array([1, 1]), (1, 1))
    with pytest.raises(RefusedError, match="differ in length"):
        build_dense_grid(u, g[:-1], s, (1, 2))
    for cov in ((2, 1), (1, 2, 3), (1.0, 2), "ab", None):
        with pytest.raises(RefusedError):
            build_dense_grid(u, g, s, cov)


# ---------------------------------------------------------------------------------------------------
# predecessor_index
def _brute(units, steps, k):
    where = {(int(u), int(s)): i for i, (u, s) in enumerate(zip(units, steps))}
    return np.array([where.get((int(u), int(s) - k), -1) for u, s in zip(units, steps)])


def test_predecessor_finds_exactly_k_back_in_any_row_order_and_marks_gaps():
    units = np.array([7, 7, 7, 7, 3, 3, 3])
    steps = np.array([10, 11, 13, 14, 1, 2, 3])  # unit 7 has a gap at 12
    perm = np.array([3, 0, 6, 2, 5, 1, 4])
    u, s = units[perm], steps[perm]
    for k in (1, 2, 3):
        got = predecessor_index(u, s, k)
        assert got.tolist() == _brute(u, s, k).tolist()
        ok = got >= 0
        assert (u[got[ok]] == u[ok]).all() and (s[ok] - s[got[ok]] == k).all()
    one = predecessor_index(u, s, 1)
    assert one[np.flatnonzero((u == 7) & (s == 13))[0]] == -1  # the gap, never the step-11 row


def test_predecessor_never_crosses_units_on_random_panels():
    rng = np.random.RandomState(1)  # test data only
    units = rng.randint(0, 40, 3000)
    steps = rng.randint(-50, 50, 3000)
    keep = np.unique(units * 1000 + steps, return_index=True)[1]
    u, s = units[keep], steps[keep]
    for k in (1, 5, 12, 99):
        assert predecessor_index(u, s, k).tolist() == _brute(u, s, k).tolist()


def test_predecessor_refusals():
    with pytest.raises(RefusedError, match="k must be"):
        predecessor_index(np.array([1]), np.array([1]), 0)
    with pytest.raises(RefusedError, match="k must be"):
        predecessor_index(np.array([1]), np.array([1]), True)
    with pytest.raises(RefusedError, match="k must be"):
        predecessor_index(np.array([1]), np.array([1]), 1.0)
    with pytest.raises(RefusedError, match="repeat"):
        predecessor_index(np.array([1, 1]), np.array([4, 4]), 1)
    with pytest.raises(RefusedError, match="differ in length"):
        predecessor_index(np.array([1, 2]), np.array([4]), 1)
    with pytest.raises(RefusedError, match="non-finite"):
        predecessor_index(np.array([1.0, np.nan]), np.array([1, 2]), 1)
    assert predecessor_index(np.array([], dtype=int), np.array([], dtype=int), 3).size == 0
