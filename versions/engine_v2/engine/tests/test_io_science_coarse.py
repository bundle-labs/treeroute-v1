"""io science: join_coarser_column (G-CADENCE, R8, G-CALENDAR; owner ruling F6: explicit arrays of
unit codes and coarse periods). Synthetic frames, every branch.

The source rule (pm25_architecture.py:139-160): the share of unit x years holding more than one
distinct non-NaN value must be at most 0.1%; one value per unit x year (the first non-NaN); the lag
on that collapsed table (year + 1 serves year Y); then the row-count-safe join.
"""

from types import SimpleNamespace as NS

import numpy as np
import pandas as pd
import pytest

from treeroute.errors import RefusedError
from treeroute.io.apply import features_at_issue_step
from treeroute.io.joins import asof_driver_join, coarse_periods, join_coarser_column

MONTHLY = NS(kind="regular", length=1, unit="month")
ANNUAL = NS(kind="regular", length=1, unit="year")
COMP = NS(kind="composite_of_year", length=16, unit="day", composites_per_year=23)
STATIC = NS(kind="static")


def lag(column, steps, cadence=ANNUAL):
    return NS(column=column, steps=steps, column_cadence=cadence, floor_reason=None)


def monthly_rows(units, years, seed=0):
    """Monthly (unit, step, year) keys over the years, in a shuffled order."""
    u = np.repeat(units, 12 * len(years))
    step = np.tile(np.array([y * 12 + m for y in years for m in range(1, 13)]), len(units))
    rng = np.random.RandomState(seed)  # synthetic row order only
    perm = rng.permutation(len(u))
    u, step = u[perm], step[perm]
    return u, step, (step - 1) // 12


def annual_store(units, years, value, seed=1):
    """A store with an annual column repeated on every monthly row: value(unit, year)."""
    u, _, year = monthly_rows(units, years, seed=seed)
    return pd.DataFrame({"a": [value(a, b) for a, b in zip(u, year)]}), u, year


# ---------------------------------------------------------------------------------------------------
def test_an_annual_lag_of_one_serves_every_month_of_the_next_year():
    gu, gstep, gyear = monthly_rows(np.array([0, 1]), range(2001, 2004))
    grid = pd.DataFrame({"x": np.arange(len(gu), dtype=float)}, index=np.arange(len(gu)) * 3 + 7)
    store, su, syear = annual_store(np.array([0, 1]), range(2001, 2004), lambda a, b: a * 10000 + b)
    before_g, before_s = grid.copy(), store.copy()
    out = join_coarser_column(grid, gu, gyear, store, su, syear, "a", ANNUAL, MONTHLY, lag("a", 1))
    assert out.index.equals(grid.index) and out["x"].equals(grid["x"]) and list(out.columns) == ["x", "a"]
    want = np.where(gyear > 2001, gu * 10000 + gyear - 1, np.nan)
    np.testing.assert_array_equal(out["a"].to_numpy(), want)
    assert out["a"].dtype == np.float64                   # int values come back as float (NaN possible)
    pd.testing.assert_frame_equal(grid, before_g)
    pd.testing.assert_frame_equal(store, before_s)


def test_lag_zero_on_the_targets_own_cadence_collapses_and_joins_one_to_one():
    grid = pd.DataFrame({"x": [0.0, 0.0, 0.0]})
    gu, gyear = np.array([1, 0, 1]), np.array([2002, 2002, 2001])
    store, su, syear = annual_store(np.array([0, 1]), range(2001, 2003), lambda a, b: float(a + b))
    out = join_coarser_column(grid, gu, gyear, store, su, syear, "a", ANNUAL, ANNUAL, lag("a", 0))
    assert out["a"].tolist() == [2003.0, 2002.0, 2002.0]


def test_the_latest_stored_period_serves_the_period_after_it_and_a_gap_is_never_bridged():
    gu, _, gyear = monthly_rows(np.array([0]), range(2001, 2007))
    grid = pd.DataFrame({"x": np.zeros(len(gu))})
    store, su, syear = annual_store(np.array([0]), [2001, 2002, 2004, 2005], lambda a, b: float(b))
    out = join_coarser_column(grid, gu, gyear, store, su, syear, "a", ANNUAL, MONTHLY, lag("a", 1))
    by_year = {}
    for y, v in zip(gyear.tolist(), out["a"].tolist()):
        by_year.setdefault(y, set()).add("nan" if np.isnan(v) else v)
    assert all(len(v) == 1 for v in by_year.values())    # every month of a year takes one value
    got = {y: v.pop() for y, v in by_year.items()}
    # 2006 is after the store's last year: 2005 serves it through the extended table
    assert got == {2001: "nan", 2002: 2001.0, 2003: 2002.0, 2004: "nan", 2005: 2004.0, 2006: 2005.0}
    # 2003 is missing from the store: 2004 takes no value, never the 2002 value


def test_a_lag_of_two_reads_exactly_two_periods_back():
    gu, _, gyear = monthly_rows(np.array([0, 1]), range(2001, 2005))
    grid = pd.DataFrame({"x": np.zeros(len(gu))})
    store, su, syear = annual_store(np.array([0, 1]), range(2001, 2005), lambda a, b: float(a * 100 + b))
    out = join_coarser_column(grid, gu, gyear, store, su, syear, "a", ANNUAL, MONTHLY, lag("a", 2))
    want = np.where(gyear >= 2003, gu * 100 + gyear - 2, np.nan)
    np.testing.assert_array_equal(out["a"].to_numpy(), want)


def test_constancy_tolerance_is_inclusive_and_the_first_non_nan_value_is_kept():
    units = np.arange(100)
    years = range(2001, 2011)                             # 1,000 unit x years
    store, su, syear = annual_store(units, years, lambda a, b: float(b))
    vals = store["a"].to_numpy().copy()
    one = np.flatnonzero((su == 7) & (syear == 2005))
    vals[one[0]] = np.nan                                 # a NaN is not a second value
    vals[one[1]] = -1.0                                   # 1 varying unit x year of 1,000: 0.1%
    store["a"] = vals
    grid = pd.DataFrame({"x": [0.0, 0.0]})
    out = join_coarser_column(grid, np.array([7, 8]), np.array([2006, 2006]), store, su, syear, "a",
                              ANNUAL, MONTHLY, lag("a", 1))
    assert out["a"].tolist() == [-1.0, 2005.0]            # unit 7 keeps its first non-NaN value
    vals[one[2]] = -2.0                                   # still one varying unit x year
    vals[np.flatnonzero((su == 9) & (syear == 2003))[0]] = -3.0   # a second one: 0.2%
    store["a"] = vals
    with pytest.raises(RefusedError, match="more than one distinct value") as info:
        join_coarser_column(grid, np.array([7, 8]), np.array([2006, 2006]), store, su, syear, "a",
                            ANNUAL, MONTHLY, lag("a", 1))
    assert "G-CADENCE" in str(info.value)


def test_all_nan_periods_empty_stores_text_values_and_key_like_names():
    grid = pd.DataFrame({"x": [0.0, 0.0]})
    gu, gyear = np.array([0, 0]), np.array([2002, 2003])
    store = pd.DataFrame({"a": [np.nan, np.nan, 4.0]})
    out = join_coarser_column(grid, gu, gyear, store, np.array([0, 0, 0]), np.array([2001, 2001, 2002]), "a",
                              ANNUAL, MONTHLY, lag("a", 1))
    assert np.isnan(out["a"].iloc[0]) and out["a"].iloc[1] == 4.0
    empty = join_coarser_column(grid, gu, gyear, store.iloc[:0], np.array([], dtype=int),
                                np.array([], dtype=int), "a", ANNUAL, MONTHLY, lag("a", 1))
    assert empty["a"].isna().all()                       # a declared-absent group: NaN, counted by R30
    text = pd.DataFrame({"period": ["p1", "p1", "p2"]})
    out_t = join_coarser_column(grid, gu, gyear, text, np.array([0, 0, 0]), np.array([2001, 2001, 2002]),
                                "period", ANNUAL, MONTHLY, lag("period", 1))
    assert out_t["period"].tolist() == ["p1", "p2"]
    named = pd.DataFrame({"unit_code": [5.0, 6.0]})
    out_n = join_coarser_column(grid, gu, gyear, named, np.array([0, 0]), np.array([2001, 2002]),
                                "unit_code", ANNUAL, MONTHLY, lag("unit_code", 1))
    assert out_n["unit_code"].tolist() == [5.0, 6.0]


def test_an_annual_column_on_a_composite_target():
    grid = pd.DataFrame({"x": np.zeros(3)})
    gu = np.array([0, 0, 0])
    gyear = np.array([2011, 2011, 2012])                  # composites 1 and 23 of 2011, 1 of 2012
    store = pd.DataFrame({"a": [1.0, 2.0]})
    out = join_coarser_column(grid, gu, gyear, store, np.array([0, 0]), np.array([2010, 2011]), "a",
                              ANNUAL, COMP, lag("a", 1))
    assert out["a"].tolist() == [1.0, 1.0, 2.0]


def test_coarser_join_refusals():
    grid = pd.DataFrame({"x": [0.0, 0.0]})
    gu, gyear = np.array([0, 0]), np.array([2002, 2003])
    store = pd.DataFrame({"a": [1.0, 2.0]})
    su, syear = np.array([0, 0]), np.array([2001, 2002])

    def run(grid=grid, gu=gu, gp=gyear, store=store, su=su, sp=syear, column="a", ccad=ANNUAL,
            tcad=MONTHLY, lg=None):
        return join_coarser_column(grid, gu, gp, store, su, sp, column, ccad, tcad,
                                   lg if lg is not None else lag("a", 1))

    with pytest.raises(RefusedError, match="non-empty name"):
        run(column="")
    with pytest.raises(RefusedError, match="DataFrame"):
        run(grid=grid.to_numpy())
    with pytest.raises(RefusedError, match="does not hold the column"):
        run(store=store.rename(columns={"a": "b"}))
    with pytest.raises(RefusedError, match="already holds"):
        run(grid=grid.assign(a=1.0))
    with pytest.raises(RefusedError, match="differ in length"):
        run(gu=np.array([0]))
    with pytest.raises(RefusedError, match="differ in length"):
        run(sp=np.array([2001]))
    with pytest.raises(RefusedError, match="whole numbers"):
        run(gp=np.array([2002.5, 2003.0]))
    with pytest.raises(RefusedError, match="non-finite"):
        run(su=np.array([0.0, np.nan]))
    with pytest.raises(RefusedError, match="share no unit code"):
        run(su=np.array([5, 5]))
    with pytest.raises(RefusedError, match="not a Lag"):
        run(lg=3)
    with pytest.raises(RefusedError, match="lag of 'b'"):
        run(lg=lag("b", 1))
    with pytest.raises(RefusedError, match="whole number of steps"):
        run(lg=lag("a", True))
    with pytest.raises(RefusedError, match="whole number of steps"):
        run(lg=lag("a", 1.0))
    with pytest.raises(RefusedError, match="negative"):
        run(lg=lag("a", -1))
    with pytest.raises(RefusedError, match="counts steps of"):
        run(lg=lag("a", 12, MONTHLY))
    with pytest.raises(RefusedError, match="finer than the target"):
        run(ccad=MONTHLY, tcad=ANNUAL, lg=lag("a", 1, MONTHLY), gp=np.array([24025, 24026]),
            sp=np.array([24013, 24014]))
    with pytest.raises(RefusedError, match="finer than the target"):
        run(ccad=COMP, tcad=MONTHLY, lg=lag("a", 1, COMP), gp=np.array([2010 * 23 + 2, 2010 * 23 + 3]),
            sp=np.array([2010 * 23 + 1, 2010 * 23 + 2]))
    with pytest.raises(RefusedError):
        run(ccad=STATIC, lg=lag("a", 1, STATIC))


# ---------------------------------------------------------------------------------------------------
# coarse_periods: the grid periods computed from the rows' TARGET steps (the call-site rule)
def test_coarse_periods_are_the_column_periods_holding_each_target_step():
    months = np.array([2003 * 12 + 1, 2003 * 12 + 12, 2004 * 12 + 1, 2002 * 12 + 6])
    got = coarse_periods(months, MONTHLY, ANNUAL)
    assert got.dtype == np.int64 and got.tolist() == [2003, 2003, 2004, 2002]
    comps = np.array([2010 * 23 + 1, 2010 * 23 + 23, 2011 * 23 + 1])   # the short last composite too
    assert coarse_periods(comps, COMP, ANNUAL).tolist() == [2010, 2010, 2011]
    assert coarse_periods(np.array([2005, 2001]), ANNUAL, ANNUAL).tolist() == [2005, 2001]
    assert coarse_periods(np.array([], dtype=np.int64), MONTHLY, ANNUAL).tolist() == []


def test_the_call_site_rule_never_serves_a_row_its_own_target_period():
    # the feature-runner pattern: periods from the TARGET steps, the coarser join, then the whole row
    # moved back to its issue step. Every value a row ends up with is dated before its target year.
    units = np.array([0, 1])
    gu, gstep, _ = monthly_rows(units, range(2001, 2005), seed=4)
    grid = pd.DataFrame({"x": np.zeros(len(gu))})
    store, su, syear = annual_store(units, range(2001, 2005), lambda a, b: a * 10000 + b)
    periods = coarse_periods(gstep, MONTHLY, ANNUAL)
    target_year = (gstep - 1) // 12
    for k in (0, 1):
        out = join_coarser_column(grid, gu, periods, store, su, syear, "a", ANNUAL, MONTHLY, lag("a", k))
        want = np.where(target_year - k >= 2001, gu * 10000 + target_year - k, np.nan)
        np.testing.assert_array_equal(out["a"].to_numpy(), want)
    out = join_coarser_column(grid, gu, periods, store, su, syear, "a", ANNUAL, MONTHLY, lag("a", 1))
    served_year = out["a"].to_numpy() - gu * 10000
    assert (served_year[np.isfinite(served_year)] < target_year[np.isfinite(served_year)]).all()
    for lead in (1, 3, 12):
        moved = features_at_issue_step(out[["a"]].to_numpy(), gu, gstep, lead)[:, 0] - gu * 10000
        issue_year = (gstep - lead - 1) // 12
        ok = np.isfinite(moved)
        assert ok.any() and (moved[ok] == issue_year[ok] - 1).all() and (moved[ok] < target_year[ok]).all()


def test_coarse_periods_refusals():
    with pytest.raises(RefusedError, match="do not nest in one period") as info:
        coarse_periods(np.array([2001, 2002]), ANNUAL, MONTHLY)            # a year holds many months
    assert info.value.rule == "G-CADENCE"
    with pytest.raises(RefusedError, match="do not nest in one period"):
        coarse_periods(np.array([2010 * 23 + 2]), COMP, MONTHLY)          # 17 Jan - 1 Feb straddles
    with pytest.raises(RefusedError, match="whole numbers"):
        coarse_periods(np.array([24001.5]), MONTHLY, ANNUAL)
    with pytest.raises(RefusedError):
        coarse_periods(np.array([24001]), MONTHLY, STATIC)


def test_asof_driver_join_waits_for_m8():
    with pytest.raises(NotImplementedError, match="M8"):
        asof_driver_join(pd.DataFrame(), pd.DataFrame(), {})
