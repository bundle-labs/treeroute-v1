"""io science: aggregate_time (plan 1.5; owner rulings F5, D34, D35).

The values: mean, min, max and sum over each unit x target period, strict on a missing sub-period
(D34), with a growing season. The facts: computed with the timing helpers (F5), so a column whose
content reaches past its stored month keeps the ruled 1-year lag on an annual target, checked here
through compute_lag, the same rule R8 runs.
"""

import dataclasses
import datetime as dt
from enum import Enum
from types import SimpleNamespace as NS

import numpy as np
import pandas as pd
import pytest

from test_timing_aggregate import annual_lag
from test_timing_facts import (A, ANNUAL_TARGET, C, MONTH, YEAR, S, U, composite, win)
from test_timing_facts import column as timing_column
from treeroute.errors import RefusedError
from treeroute.io.aggregate import STEP, UNIT_CODE, AggregateWindow, aggregate_time
from treeroute.timing import Reach, compute_lag
from treeroute.timing.shapes import TimingRefusal

YEARS = range(2001, 2006)


class Role(Enum):
    """Stands in for the approved common.Role: the two values these tests use (the timing tests'
    stand-in has DRIVER only, and aggregate_time writes the engineered role)."""
    DRIVER = "driver"
    ENGINEERED = "engineered"


def column(name, **kw):
    """The timing tests' column facts, with a role enum that holds the engineered role."""
    return dataclasses.replace(timing_column(name, **kw), role=Role.DRIVER)


def monthly_panel(n_units=3, years=YEARS, seed=2):
    rng = np.random.RandomState(seed)  # synthetic values only
    steps = np.array([y * 12 + m for y in years for m in range(1, 13)])
    units = np.repeat(np.arange(n_units), len(steps))
    s = np.tile(steps, n_units)
    values = rng.gamma(2.0, 3.0, size=len(s))
    perm = rng.permutation(len(s))                      # rows in any order
    return pd.DataFrame({"x": values[perm]}, index=np.arange(len(s))[perm] * 2), units[perm], s[perm]


def expected(frame, units, steps, stat, months=None):
    """Plain reference: per unit x year, the stat over the (season) months, NaN if any is missing."""
    year = (steps - 1) // 12
    month = (steps - 1) % 12 + 1
    want = months if months is not None else range(1, 13)
    out = {}
    for u in np.unique(units):
        for y in np.unique(year[units == u]):
            vals = []
            for m in want:
                hit = (units == u) & (year == y) & (month == m)
                vals.append(frame["x"].to_numpy()[hit][0] if hit.any() else np.nan)
            vals = np.array(vals)
            out[(u, y)] = np.nan if np.isnan(vals).any() else getattr(np, stat)(vals)
    return out


def x_facts(**kw):
    return dataclasses.replace(column("x"), **kw)


# ---------------------------------------------------------------------------------------------------
# values
@pytest.mark.parametrize("stat", ["mean", "min", "max", "sum"])
def test_monthly_to_annual_statistics_match_the_plain_reference(stat):
    frame, units, steps = monthly_panel()
    before = frame.copy()
    rows, facts = aggregate_time(frame, units, steps, "x", x_facts(), YEAR, stat, None)
    assert list(rows.columns) == [UNIT_CODE, STEP, "x"]
    assert rows[UNIT_CODE].dtype == np.int64 and rows[STEP].dtype == np.int64 and rows["x"].dtype == np.float64
    assert rows.index.tolist() == list(range(len(rows)))
    keys = list(zip(rows[UNIT_CODE], rows[STEP]))
    assert keys == sorted(keys) and len(keys) == 3 * len(YEARS)
    ref = expected(frame, units, steps, stat)
    np.testing.assert_allclose(rows["x"], [ref[k] for k in keys], rtol=1e-12)
    pd.testing.assert_frame_equal(frame, before)


def test_a_missing_month_or_a_nan_value_makes_the_year_nan_strictly():
    frame, units, steps = monthly_panel()
    drop = (units == 0) & (steps == 2003 * 12 + 7)      # unit 0, July 2003: no row
    nan_at = (units == 1) & (steps == 2002 * 12 + 1)    # unit 1, January 2002: NaN value
    frame = frame.copy()
    frame.loc[frame.index[nan_at], "x"] = np.nan
    keep = ~drop
    rows, _ = aggregate_time(frame[keep], units[keep], steps[keep], "x", x_facts(), YEAR, "mean", None)
    got = {(u, t): v for u, t, v in zip(rows[UNIT_CODE], rows[STEP], rows["x"])}
    assert np.isnan(got[(0, 2003)]) and np.isnan(got[(1, 2002)])
    assert np.isfinite([v for k, v in got.items() if k not in ((0, 2003), (1, 2002))]).all()
    # a year with only part of its months in the data is NaN too (D34), and still a row
    part = steps < 2001 * 12 + 7
    rows2, _ = aggregate_time(frame[part], units[part], steps[part], "x", x_facts(), YEAR, "sum", None)
    assert rows2[STEP].tolist() == [2001] * 3 and rows2["x"].isna().all()


def test_a_growing_season_reads_its_months_only():
    frame, units, steps = monthly_panel()
    frame = frame.copy()
    winter = ((steps - 1) % 12 + 1) == 1
    frame.loc[frame.index[winter], "x"] = np.nan         # outside the season: never read
    season = (6, 7, 8, 9)
    for stat in ("mean", "max", "sum"):
        rows, _ = aggregate_time(frame, units, steps, "x", x_facts(), YEAR, stat, season)
        ref = expected(frame, units, steps, stat, months=season)
        keys = list(zip(rows[UNIT_CODE], rows[STEP]))
        np.testing.assert_allclose(rows["x"], [ref[k] for k in keys], rtol=1e-12)
        assert np.isfinite(rows["x"]).all()
    # the season order does not matter; a missing season month makes the year NaN
    gap = ~((units == 2) & (steps == 2004 * 12 + 8))
    rows, _ = aggregate_time(frame[gap], units[gap], steps[gap], "x", x_facts(), YEAR, "mean", (9, 6, 8, 7))
    got = {(u, t): v for u, t, v in zip(rows[UNIT_CODE], rows[STEP], rows["x"])}
    assert np.isnan(got[(2, 2004)]) and np.isfinite(got[(2, 2003)])


def test_composites_to_annual_include_the_short_last_composite():
    comp = composite(16, 23)
    steps = np.array([y * 23 + n for y in (2010, 2011) for n in range(1, 24)])
    units = np.zeros(len(steps), dtype=int)
    values = np.arange(len(steps), dtype=float)
    col = column("x", cadence=comp, window=win(16, U.DAY, A.BACKWARD))
    rows, facts = aggregate_time(pd.DataFrame({"x": values}), units, steps, "x", col, YEAR, "mean", None)
    assert rows[STEP].tolist() == [2010, 2011]
    np.testing.assert_allclose(rows["x"], [values[:23].mean(), values[23:].mean()])
    # 22 missing composites of a year: NaN; the facts count 23 sub-periods per year for a sum range
    rows2, facts2 = aggregate_time(pd.DataFrame({"x": values[:22]}), units[:22], steps[:22], "x", col, YEAR,
                                   "sum", None)
    assert np.isnan(rows2["x"]).all() and facts2.legal_range == (0.0, 23.0)


def test_an_enum_statistic_is_read_by_its_value():
    class AggStat(Enum):
        MEAN = "mean"

    frame, units, steps = monthly_panel(n_units=1)
    a, _ = aggregate_time(frame, units, steps, "x", x_facts(), YEAR, AggStat.MEAN, None)
    b, _ = aggregate_time(frame, units, steps, "x", x_facts(), YEAR, "mean", None)
    pd.testing.assert_frame_equal(a, b)


# ---------------------------------------------------------------------------------------------------
# facts (F5, D35)
def test_output_facts_are_computed_and_the_rest_inherited():
    frame, units, steps = monthly_panel(n_units=1)
    src = x_facts(units="mm", product_family="fam", lineage_assimilates=("a",), dtype="float32",
                  fill_values=(-32768.0,), legal_range=(-1.0, 5.0))
    _, f = aggregate_time(frame, units, steps, "x", src, YEAR, "mean", None)
    assert f.cadence is YEAR and f.stamp is S.PERIOD_END
    assert f.window == AggregateWindow(length=1, unit=U.YEAR, align=A.BACKWARD, max_length=None,
                                       fact_status=C.FactStatus.UNVERIFIED)
    assert f.fill_values == () and f.dtype == "float64" and f.derived_from == ("x",)
    assert (f.units, f.product_family, f.lineage_assimilates, f.legal_range) == ("mm", "fam", ("a",), (-1.0, 5.0))
    assert (f.name, f.scope) == (src.name, src.scope)
    assert f.role is Role.ENGINEERED and f.operation is None and f.reviewed_by is None
    # D35: a sum's range is n x the range, widest over the periods (12 months each here)
    _, fs = aggregate_time(frame, units, steps, "x", src, YEAR, "sum", None)
    assert fs.legal_range == (-12.0, 60.0)
    _, fseason = aggregate_time(frame, units, steps, "x", src, YEAR, "sum", (4, 5, 6))
    assert fseason.legal_range == (-3.0, 15.0)
    _, finf = aggregate_time(frame, units, steps, "x", x_facts(legal_range=(0.0, float("inf"))), YEAR,
                             "sum", None)
    assert finf.legal_range == (0.0, float("inf"))
    _, fnone = aggregate_time(frame, units, steps, "x", dataclasses.replace(src, legal_range=None), YEAR,
                              "sum", None)
    assert fnone.legal_range is None


COMPUTED = ("cadence", "stamp", "window", "fill_values", "dtype", "derived_from")   # + a sum's legal_range
RESET = ("operation", "reviewed_by", "role")
INHERITED = ("name", "units", "scope", "product_family", "lineage_assimilates", "lineage_trained_on",
             "near_sentinel_optout", "sum_group", "content_epoch", "observed_through", "release_date",
             "snapshot_date", "baseline_period", "absent_groups", "reads_target", "fact_status",
             "co_measured_with_target", "co_measured_part", "data_selected")


def test_the_three_field_lists_cover_every_column_fact_exactly_once():
    names = [f.name for f in dataclasses.fields(column("x"))]
    listed = list(COMPUTED) + list(RESET) + list(INHERITED) + ["legal_range"]
    assert sorted(listed) == sorted(names) and len(set(listed)) == len(listed)


def test_the_parents_declaration_review_and_role_are_reset_and_every_other_fact_inherited():
    # a derived parent (a trailing operation of another column, reviewed, in a sum group, reading the
    # target): its aggregate must not claim the parent's operation, review or role (the record would
    # contradict itself, derived_from being the parent), and keeps every other fact
    frame, units, steps = monthly_panel(n_units=1)
    src = x_facts(derived_from=("w",), operation=NS(kind="trailing", sources=("w",), window=3),
                  reviewed_by="a reviewer", units="mm", product_family="fam", lineage_assimilates=("a",),
                  lineage_trained_on=("b",), near_sentinel_optout=True, sum_group="balance",
                  content_epoch=dt.date(2000, 1, 1), observed_through=dt.date(2020, 12, 31),
                  release_date=dt.date(2021, 2, 1), snapshot_date=dt.date(2021, 3, 1),
                  baseline_period=(1991, 2020), absent_groups={"g9": "no file"}, reads_target=True,
                  fact_status=C.FactStatus.VERIFIED, co_measured_with_target=False, co_measured_part=2,
                  data_selected=NS(method="top-k", rows="donor", latest_date="2019-12-31", groups=("g1",)))
    for stat in ("mean", "min", "max", "sum"):
        _, f = aggregate_time(frame, units, steps, "x", src, YEAR, stat, None)
        assert f.derived_from == ("x",) and f.operation is None and f.reviewed_by is None, stat
        assert f.role is Role.ENGINEERED, stat
        for name in INHERITED:
            assert getattr(f, name) == getattr(src, name), (stat, name)
        assert (f.legal_range == src.legal_range) == (stat != "sum"), stat
    # plain strings (the package schema's form): the role becomes the string 'engineered'
    view = NS(name="x", cadence=MONTH, stamp="period_end", units="1", sum_group="balance",
              window=NS(length=1, unit="month", align="backward", max_length=None, fact_status="unverified"),
              role="driver", operation="trailing mean of w", reviewed_by="a reviewer", derived_from=("w",))
    _, fv = aggregate_time(frame, units, steps, "x", view, YEAR, "mean", None)
    assert (fv.role, fv.operation, fv.reviewed_by, fv.derived_from, fv.sum_group) == (
        "engineered", None, None, ("x",), "balance")
    # a record without those fields gains none of them
    bare = NS(name="x", cadence=MONTH, stamp="period_end",
              window=NS(length=1, unit="month", align="backward", max_length=None, fact_status="unverified"))
    _, fb = aggregate_time(frame, units, steps, "x", bare, YEAR, "mean", None)
    assert not any(hasattr(fb, name) for name in RESET)


def test_a_role_enum_without_the_engineered_role_is_refused():
    class DriverOnly(Enum):
        DRIVER = "driver"

    frame, units, steps = monthly_panel(n_units=1)
    with pytest.raises(RefusedError, match="no 'engineered' member") as info:
        aggregate_time(frame, units, steps, "x", x_facts(role=DriverOnly.DRIVER), YEAR, "mean", None)
    assert info.value.rule == "plan 1.3"


def test_the_window_carries_the_measured_reach_and_the_source_status():
    frame, units, steps = monthly_panel(n_units=1)
    src = column("co2", stamp=S.PERIOD_CENTRE, window=win(3, status=C.FactStatus.ASSUMED))
    _, f = aggregate_time(frame.rename(columns={"x": "co2"}), units, steps, "co2", src, YEAR, "mean", None)
    assert f.window.reach_after_max == Reach(31, U.DAY) and f.window.reach_before_max == Reach(31, U.DAY)
    assert f.window.fact_status is C.FactStatus.ASSUMED
    # facts without a window status take the column's
    plain = dataclasses.replace(column("m", fact_status=C.FactStatus.VERIFIED),
                                window=NS(length=1, unit=U.MONTH, align=A.BACKWARD, max_length=None))
    _, fp = aggregate_time(frame.rename(columns={"x": "m"}), units, steps, "m", plain, YEAR, "mean", None)
    assert fp.window.fact_status is C.FactStatus.VERIFIED and fp.window.reach_after_max is None


RULED = [("nino34", win(5)), ("sst_anom_atl3", win(5)), ("oni", win(7)), ("tni", win(7)),
         ("co2", win(3)), ("V11", win(1, after=Reach(15, "day"), before=Reach(15, "day")))]


@pytest.mark.parametrize("name,window", RULED)
def test_ruled_one_year_annual_lags_survive_aggregation(name, window):
    frame, units, steps = monthly_panel(n_units=2)
    src = column(name, stamp=S.PERIOD_CENTRE, window=window)
    for stat in ("mean", "min", "max", "sum"):
        _, f = aggregate_time(frame.rename(columns={"x": name}), units, steps, name, src, YEAR, stat, None)
        assert compute_lag(f, ANNUAL_TARGET, YEAR, "nowcast").steps == 1
        assert compute_lag(f, ANNUAL_TARGET, YEAR, "nowcast").steps == annual_lag(src)


def test_plain_months_stay_at_lag_zero_and_seasons_follow_their_content():
    frame, units, steps = monthly_panel(n_units=1)
    _, plain = aggregate_time(frame, units, steps, "x", x_facts(), YEAR, "mean", None)
    assert compute_lag(plain, ANNUAL_TARGET, YEAR, "nowcast").steps == 0          # D25 (a)
    centred = column("x", stamp=S.PERIOD_CENTRE, window=win(3))
    _, summer = aggregate_time(frame, units, steps, "x", centred, YEAR, "mean", (6, 7, 8, 9))
    _, autumn = aggregate_time(frame, units, steps, "x", centred, YEAR, "mean", (10, 11, 12))
    assert compute_lag(summer, ANNUAL_TARGET, YEAR, "nowcast").steps == 0         # content ends in October
    assert compute_lag(autumn, ANNUAL_TARGET, YEAR, "nowcast").steps == 1         # content reaches January
    assert annual_lag(centred, months=range(10, 13)) == 1


def test_facts_as_a_namespace_view_and_refusal_of_other_records():
    frame, units, steps = monthly_panel(n_units=1)
    view = NS(name="x", cadence=MONTH, stamp="period_centre",
              window=NS(length=3, unit="month", align="centred", max_length=None, fact_status="unverified"),
              legal_range=(0.0, 2.0), fill_values=(), dtype="float32", derived_from=(), units="1")
    _, f = aggregate_time(frame, units, steps, "x", view, YEAR, "sum", None)
    assert isinstance(f, NS) and f.stamp == "period_end" and f.window.align == "backward"
    assert f.window.unit is U.YEAR and f.legal_range == (0.0, 24.0)
    assert compute_lag(f, ANNUAL_TARGET, YEAR, "nowcast").steps == 1

    class Record:
        name, cadence, stamp, window = "x", MONTH, "period_end", NS(length=1, unit="month", align="backward")

    with pytest.raises(RefusedError, match="column-facts record"):
        aggregate_time(frame, units, steps, "x", Record(), YEAR, "mean", None)


# ---------------------------------------------------------------------------------------------------
# refusals
def test_aggregate_refusals():
    frame, units, steps = monthly_panel(n_units=1)
    f = x_facts()

    def run(frame=frame, units=units, steps=steps, column="x", facts=f, target=YEAR, stat="mean", season=None):
        return aggregate_time(frame, units, steps, column, facts, target, stat, season)

    with pytest.raises(RefusedError, match="DataFrame"):
        run(frame=frame.to_numpy())
    with pytest.raises(RefusedError, match="more than once"):
        run(frame=pd.concat([frame, frame], axis=1))
    with pytest.raises(RefusedError, match="does not hold"):
        run(column="z")
    with pytest.raises(RefusedError, match="output key"):
        run(frame=frame.rename(columns={"x": STEP}), column=STEP, facts=dataclasses.replace(f, name=STEP))
    with pytest.raises(RefusedError, match="differ in length"):
        run(units=units[:-1])
    with pytest.raises(RefusedError, match="repeat"):
        run(steps=np.where(steps == steps[0], steps[1], steps))
    with pytest.raises(RefusedError, match="numeric"):
        run(frame=pd.DataFrame({"x": ["a"] * len(frame)}))
    with pytest.raises(RefusedError, match="numeric"):
        run(frame=pd.DataFrame({"x": np.ones(len(frame), dtype=bool)}))
    with pytest.raises(RefusedError, match="unmasked sentinel"):
        run(frame=pd.DataFrame({"x": np.where(np.arange(len(frame)) == 3, 9.96921e36, 1.0)}))
    with pytest.raises(RefusedError, match="unmasked sentinel"):
        run(frame=pd.DataFrame({"x": np.where(np.arange(len(frame)) == 3, -32768.0, 1.0)}),
            facts=x_facts(fill_values=(-32768.0,)))
    with pytest.raises(RefusedError, match="facts of 'y'"):
        run(facts=x_facts(name="y"))
    with pytest.raises(RefusedError, match="lack"):
        run(facts=NS(name="x", cadence=MONTH, stamp="period_end"))
    with pytest.raises(RefusedError, match="not finer"):
        run(target=MONTH)
    with pytest.raises(RefusedError, match="unknown statistic"):
        run(stat="median")
    for bad in ((), (0,), (13,), (6, 6), "678", (True,), (6.0,)):
        with pytest.raises(RefusedError, match="season"):
            run(season=bad)
    with pytest.raises(RefusedError, match="not one year"):
        run(target=composite(16, 23), season=(6,))
    with pytest.raises(RefusedError, match="empty frame"):
        run(frame=frame.iloc[:0], units=units[:0], steps=steps[:0])
    with pytest.raises(RefusedError):          # a timestamp-like float step
        run(steps=steps + 0.5)


def test_a_source_that_is_not_finer_or_does_not_nest_is_refused():
    # annual values to a monthly target: an annual step straddles the months
    years = np.array([2001, 2002])
    col = column("x", cadence=YEAR, window=win(1, U.YEAR, A.BACKWARD))
    with pytest.raises(RefusedError, match="do not nest"):
        aggregate_time(pd.DataFrame({"x": [1.0, 2.0]}), np.array([0, 0]), years, "x", col, MONTH, "mean", None)
    # 16-day composites to months: composites straddle month edges
    comp = composite(16, 23)
    col_c = column("x", cadence=comp, window=win(16, U.DAY, A.BACKWARD))
    with pytest.raises(RefusedError, match="do not nest"):
        aggregate_time(pd.DataFrame({"x": [1.0, 2.0]}), np.array([0, 0]), np.array([2010 * 23 + 1, 2010 * 23 + 2]),
                       "x", col_c, MONTH, "mean", None)
    # a season holding no whole source step: 32-day composites never fit inside one month
    wide = composite(32, 12)
    col_w = column("x", cadence=wide, window=win(32, U.DAY, A.BACKWARD))
    steps = np.array([2010 * 12 + n for n in range(1, 13)])
    with pytest.raises(RefusedError, match="hold no whole source step"):
        aggregate_time(pd.DataFrame({"x": np.ones(12)}), np.zeros(12, dtype=int), steps, "x", col_w, YEAR,
                       "mean", (3,))


def test_an_unknown_unsigned_source_window_cannot_be_aggregated():
    frame, units, steps = monthly_panel(n_units=1)
    unknown = column("x", stamp=S.PERIOD_CENTRE, window=win(None, U.MONTH, A.UNKNOWN))
    with pytest.raises(TimingRefusal):
        aggregate_time(frame, units, steps, "x", unknown, YEAR, "mean", None)
