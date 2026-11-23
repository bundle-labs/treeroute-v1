"""R4 under owner ruling J5: the first data year is the first year of the DRIVER stores the lag sources
read, not the target's first year, so a lagged column never reads a year its store does not have.

derive_all measures each lag-source store's first year with the column reader's drivers_present, once
per store catalog and set of declared-absent groups (orchestrate._r04_first_data_year), and passes the
latest of them to the approved derive_r04_first_year. Shown here: the unchanged case, a store that
starts a year late (Y0 moves, flagged and recorded), declared-absent groups that do not count, a lag-0
column whose store starts late (Y0 does not move), the refusals, and the annual case the ruling names
(target from 2001, store from 2002, a 1-year lag: Y0 2003, not 2002); and a declared lag operation
(orchestrate._r04_lags: a lag-k output's k counts on top of its R8 lag, units turned into the column's
steps, other operations listed, a 'lag' without k flagged, an unconvertible unit refused). The toy package
and reader are test_derive_all's.
"""

from types import SimpleNamespace as NS

import numpy as np
import pytest

from test_derive_all import FIRST_YEAR, LAST_DRIVER_YEAR, Reader, package, target_table
from treeroute import derive as D
from treeroute import timing
from treeroute.derive import orchestrate as O
from treeroute.errors import RefusedError

YEAR = NS(kind="regular", length=1, unit="year")
MONTH = NS(kind="regular", length=1, unit="month")


class StoreReader(Reader):
    """drivers_present answers per asked column set: ``rule(columns, years, groups) -> bool array``."""

    def __init__(self, rule):
        super().__init__()
        self.rule = rule

    def drivers_present(self, unit_ids, group_ids, time_columns, columns):
        self.calls.append(("drivers_present", tuple(columns)))
        years = np.asarray(time_columns["step_year"])
        base = years <= self.last
        return base & self.rule(tuple(columns), years, np.asarray(group_ids, dtype=object))


def run(tmp_path, reader):
    return D.derive_all(package(tmp_path), target_table(), reader)


def test_the_toy_package_has_one_lag_source(tmp_path):
    """a1 (annual, 1-year lag) is the only lag source; x1 and c1 lag 0 months; s1 static, e1 epoch."""
    out = run(tmp_path, Reader())
    assert {c: lag.steps for c, lag in out["R8"].value.items()} == {"a1": 1, "c1": 0, "x1": 0}


def test_stores_that_start_with_the_target_keep_the_old_y0(tmp_path):
    reader = Reader()
    out = run(tmp_path, reader)
    assert out["R4"].value == FIRST_YEAR + 1 and "store_first_year_moved_y0" not in out["R4"].flags
    stores = out["R4"].inputs["driver_stores"]
    assert stores["target_first_year"] == stores["first_data_year"] == FIRST_YEAR
    assert [(s["lag_sources"], s["absent_groups"], s["first_year"]) for s in stores["stores"]] == [
        (["a1"], ["g_e"], FIRST_YEAR)]
    assert out["R4"].inputs["first_data_year"] == FIRST_YEAR
    # R3's joined-row call comes first, then one call per lag-source store (only a1 has a lag)
    assert reader.calls[0] == ("drivers_present", ("x1", "a1", "s1", "e1", "c1"))
    assert reader.calls[1] == ("drivers_present", ("a1",))
    assert sum(1 for c in reader.calls if c[0] == "drivers_present") == 2


def test_a_store_that_starts_a_year_late_moves_y0(tmp_path):
    reader = StoreReader(lambda cols, years, groups: years >= FIRST_YEAR + 1)
    out = run(tmp_path, reader)
    assert out["R4"].value == FIRST_YEAR + 2                     # store first year + the 1-year lag
    assert out["R4"].inputs["first_data_year"] == FIRST_YEAR + 1
    assert out["R4"].inputs["driver_stores"]["target_first_year"] == FIRST_YEAR
    assert out["R4"].inputs["driver_stores"]["stores"][0]["first_year"] == FIRST_YEAR + 1
    assert "store_first_year_moved_y0" in out["R4"].flags
    assert out["R7"].value.y0 == FIRST_YEAR + 2 and out["R3"].value == LAST_DRIVER_YEAR
    entry = D.derived_entry(out["R4"])
    assert entry["input_hashes"]["driver_stores"] and entry["inputs"]["set_by"] == ["a1"]


def test_declared_absent_groups_do_not_count_toward_a_store_first_year(tmp_path):
    """a1's store declares g_e absent (F8 counts its rows as present): its rows in the first years
    must not make the store look older than it is."""
    def rule(cols, years, groups):
        if cols == ("a1",):
            return (groups == "g_e") | (years >= FIRST_YEAR + 2)
        return np.ones(len(years), dtype=bool)
    out = run(tmp_path, StoreReader(rule))
    assert out["R4"].inputs["first_data_year"] == FIRST_YEAR + 2 and out["R4"].value == FIRST_YEAR + 3


def test_a_lag_0_column_whose_store_starts_late_does_not_move_y0(tmp_path):
    """x1 (lag 0) is never asked for by R4 (C4: only lag sources count); its late start shows in R3's
    joined rows only."""
    def rule(cols, years, groups):
        if "x1" in cols:
            return years >= FIRST_YEAR + 3
        return np.ones(len(years), dtype=bool)
    reader = StoreReader(rule)
    out = run(tmp_path, reader)
    assert out["R4"].value == FIRST_YEAR + 1 and out["R4"].inputs["first_data_year"] == FIRST_YEAR
    asked = [c[1] for c in reader.calls if c[0] == "drivers_present"]
    assert asked[1:] == [("a1",)]


def test_refusals(tmp_path):
    def nothing_outside_absent(cols, years, groups):
        if cols == ("a1",):
            return groups == "g_e"
        return np.ones(len(years), dtype=bool)
    with pytest.raises(RefusedError) as info:
        run(tmp_path / "a", StoreReader(nothing_outside_absent))
    assert info.value.rule == "R4" and "holds no target row" in str(info.value)

    class Short(Reader):
        def drivers_present(self, unit_ids, group_ids, time_columns, columns):
            out = Reader.drivers_present(self, unit_ids, group_ids, time_columns, columns)
            return out[:-1] if tuple(columns) == ("a1",) else out
    with pytest.raises(RefusedError) as info:
        run(tmp_path / "b", Short())
    assert info.value.rule == "R4" and "one boolean per target row" in str(info.value)


# ---------------------------------------------------------------------------------------------------
# the annual case the ruling names: target from 2001, its driver store from 2002, a 1-year lag
def test_an_annual_target_whose_store_starts_a_year_later_gets_y0_two_years_on():
    years = np.repeat(np.arange(2001, 2024), 3)                         # 3 units x 23 years
    units = np.tile(np.array(["g_u0", "g_u1", "h_u0"], dtype=object), 23)
    groups = np.array([u.split("_")[0] for u in units], dtype=object)
    time_columns = {"year": years}

    class AnnualReader(object):
        def __init__(self):
            self.asked = []

        def drivers_present(self, unit_ids, group_ids, tc, columns):
            self.asked.append(tuple(columns))
            return np.asarray(tc["year"]) >= 2002                      # the store starts in 2002

    pkg = NS(stores={"features.yaml": NS(columns={"v": None, "w": None}),
                     "other.yaml": NS(columns={"z": None})})
    facts = NS(absent_groups={"v": {}, "w": {}, "z": {"h": "no file"}})
    lags = {"v": timing.Lag(column="v", steps=1, column_cadence=YEAR, floor_reason=None),
            "w": timing.Lag(column="w", steps=0, column_cadence=YEAR, floor_reason=None),
            "z": timing.Lag(column="z", steps=1, column_cadence=YEAR, floor_reason=None)}
    reader = AnnualReader()
    first, record = O._r04_first_data_year(pkg, facts, lags, reader, units, groups, time_columns, years)
    assert first == 2002 and record["target_first_year"] == 2001 and record["first_data_year"] == 2002
    assert sorted(reader.asked) == [("v",), ("z",)]                      # lag sources only, per store
    assert {s["catalog"]: s["first_year"] for s in record["stores"]} == {"features.yaml": 2002,
                                                                          "other.yaml": 2002}
    r4 = D.derive_r04_first_year(first, lags)
    assert r4.value == 2003                                               # not 2002 (the old rule)
    assert D.derive_r04_first_year(2001, lags).value == 2002              # the old reading, for contrast


def test_with_several_stores_the_latest_first_year_counts():
    years = np.repeat(np.arange(2001, 2011), 2)
    units = np.tile(np.array(["g_u0", "g_u1"], dtype=object), 10)
    groups = np.array(["g"] * len(units), dtype=object)

    class TwoStores(object):
        def drivers_present(self, unit_ids, group_ids, tc, columns):
            start = {("m",): 2001, ("a",): 2004}[tuple(columns)]
            return np.asarray(tc["year"]) >= start

    pkg = NS(stores={"early.yaml": NS(columns={"m": None}), "late.yaml": NS(columns={"a": None})})
    facts = NS(absent_groups={})
    lags = {"m": timing.Lag(column="m", steps=2, column_cadence=MONTH, floor_reason=None),
            "a": timing.Lag(column="a", steps=1, column_cadence=YEAR, floor_reason=None)}
    first, record = O._r04_first_data_year(pkg, facts, lags, TwoStores(), units, groups, {"year": years}, years)
    assert first == 2004 and [s["first_year"] for s in record["stores"]] == [2001, 2004]
    assert D.derive_r04_first_year(first, lags).value == 2005


def test_no_lag_source_keeps_the_target_first_year():
    years = np.arange(2001, 2006)

    class Never(object):
        def drivers_present(self, *a):
            raise AssertionError("R4 asks for lag sources only")

    lags = {"w": timing.Lag(column="w", steps=0, column_cadence=YEAR, floor_reason=None)}
    first, record = O._r04_first_data_year(NS(stores={"s": NS(columns={"w": None})}), NS(absent_groups={}),
                                           lags, Never(), np.array(["u"] * 5, dtype=object),
                                           np.array(["g"] * 5, dtype=object), {"year": years}, years)
    assert first == 2001 and record["stores"] == []
    first, _ = O._r04_first_data_year(NS(stores={}), NS(absent_groups={}), {}, Never(),
                                      np.array(["u"] * 5, dtype=object), np.array(["g"] * 5, dtype=object),
                                      {"year": years}, years)
    assert first == 2001


# ---------------------------------------------------------------------------------------------------
# J5 and a declared lag operation: a lag-k output gets R8 lag 0 (its content already ends k steps back),
# so R4 counts R8's lag PLUS k (orchestrate._r04_lags), and the output's parent store is measured
def _lag(name, steps, cadence):
    return timing.Lag(column=name, steps=steps, column_cadence=cadence, floor_reason=None)


def _out(operation, parent="p"):
    return NS(operation=operation, derived_from=[parent])


def test_a_lag_12_output_alone_moves_y0_past_its_parent_store_start():
    """The review's case: the only look-back is a lag-12 output (R8 lag 0). Target from 2001, the
    parent's store from 2002: the old count gave Y0 2001 (no lag source) and January 2001 would read
    January 2000; now Y0 = 2002 + 1 = 2003, so the first row reads January 2002, a stored month."""
    years = np.repeat(np.arange(2001, 2011), 2)
    units = np.tile(np.array(["g_u0", "g_u1"], dtype=object), 10)
    groups = np.array(["g"] * len(units), dtype=object)

    class ParentStore(object):
        def __init__(self):
            self.asked = []

        def drivers_present(self, unit_ids, group_ids, tc, columns):
            self.asked.append(tuple(columns))
            return np.asarray(tc["year"]) >= 2002

    pkg = NS(stores={"features": NS(columns={"p_lag12": None, "w": None})})
    facts = NS(absent_groups={}, store={"p_lag12": _out("lag k=12 unit=month"), "w": NS(operation=None,
                                                                                         derived_from=[])})
    lags = {"p_lag12": _lag("p_lag12", 0, MONTH), "w": _lag("w", 0, MONTH)}
    assert D.derive_r04_first_year(2001, lags).value == 2001                 # what R8's lags alone give
    reader = ParentStore()
    r4 = O._r04_entry(pkg, facts, lags, reader, units, groups, {"year": years}, years, 2001)
    assert r4.value == 2003 and reader.asked == [("p_lag12",)]
    assert "store_first_year_moved_y0" in r4.flags and "lag_operation_not_counted" not in r4.flags
    assert r4.inputs["first_data_year"] == 2002 and r4.inputs["set_by"] == ["p_lag12"]
    assert r4.inputs["lags"]["p_lag12"] == {"steps": 12, "years": 1, "cadence": r4.inputs["lags"]["w"]["cadence"]}
    ops = r4.inputs["lag_operations"]
    assert ops["counted"] == {"p_lag12": {"operation": "lag k=12 unit=month", "derived_from": ["p"],
                                          "r8_steps": 0, "operation_steps": 12, "r4_steps": 12}}
    assert ops["not_counted"] == {} and ops["lag_operation_not_counted"] == []
    assert lags["p_lag12"].steps == 0                                         # R8's map is not changed


def test_lag_operation_units_turn_into_the_columns_own_steps():
    facts = NS(store={"a": _out("lag k=1 unit=year"), "b": _out("lag k=2 unit=year"),
                      "c": _out("lag k=13 unit=month"), "d": _out("lag k=3 unit=month")})
    lags = {"a": _lag("a", 1, YEAR), "b": _lag("b", 0, MONTH), "c": _lag("c", 0, YEAR), "d": _lag("d", 1, MONTH)}
    out, record = O._r04_lags(facts, lags)
    assert {c: out[c].steps for c in out} == {"a": 2, "b": 24, "c": 2, "d": 4}
    assert {c: record["counted"][c]["operation_steps"] for c in out} == {"a": 1, "b": 24, "c": 2, "d": 3}
    assert D.derive_r04_first_year(2002, out).value == 2004                  # a: 2 years, b: 24 months
    assert all(out[c].column_cadence is lags[c].column_cadence for c in out)


def test_other_operations_are_listed_not_counted_and_an_unreadable_lag_is_flagged():
    facts = NS(store={"m": _out("trailing_mean w=12 unit=month min_count=1"), "bare": _out("lag"),
                      "free": NS(operation="lag k=1 unit=month", derived_from=[]),   # no derived_from: a store column
                      "x": NS(operation=None, derived_from=["p"])})
    lags = {c: _lag(c, 1, MONTH) for c in ("m", "bare", "free", "x")}
    out, record = O._r04_lags(facts, lags)
    assert {c: out[c].steps for c in out} == {"m": 1, "bare": 1, "free": 1, "x": 1}
    assert record["counted"] == {}
    assert record["not_counted"] == {"lag": ["bare"], "trailing_mean w=12 unit=month min_count=1": ["m"]}
    assert record["lag_operation_not_counted"] == ["bare"]
    years = np.arange(2001, 2006)

    class All(object):
        def drivers_present(self, unit_ids, group_ids, tc, columns):
            return np.ones(len(years), dtype=bool)

    r4 = O._r04_entry(NS(stores={}), NS(store=facts.store, absent_groups={}), lags, All(),
                      np.array(["u"] * 5, dtype=object), np.array(["g"] * 5, dtype=object), {"year": years},
                      years, 2001)
    assert "lag_operation_not_counted" in r4.flags and r4.value == 2002


def test_a_lag_in_a_unit_r4_cannot_convert_is_refused():
    facts = NS(store={"d": _out("lag k=10 unit=day")})
    with pytest.raises(RefusedError) as info:
        O._r04_lags(facts, {"d": _lag("d", 0, MONTH)})
    assert info.value.rule == "R4" and "cannot turn its look-back" in str(info.value)
