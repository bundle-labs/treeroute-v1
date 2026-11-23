"""derive/ rules R9, R12-R14, R17-R21 and R30 on synthetic inputs, under leave one region out: every
branch and every refusal.

Synthetic inputs only (no store is read). The approved shapes are mirrored where a rule reads facts
(tests/test_timing_facts.py builders; DonorView from test_derive_shapes.py).
"""

import datetime as dt

import numpy as np
import pytest

from test_derive_shapes import DonorView
from test_timing_facts import (ANNUAL_TARGET, MONTH, MONTHLY_TARGET, PLAIN_MONTH, REACH_TARGET, YEAR,
                               composite, detection_target, win, A, U)
from treeroute import derive as D
from treeroute import engine_constants as K
from treeroute import split as SP
from treeroute import timing
from treeroute.errors import RefusedError
from treeroute.timing import Reach, TimingRefusal


def refused(rule, call, *args, **kwargs):
    with pytest.raises(RefusedError) as info:
        call(*args, **kwargs)
    assert info.value.rule == rule, str(info.value)
    return str(info.value)


def day(y, m, d):
    return dt.date(y, m, d).toordinal()


MONTHLY = D.Cadence(D.CadenceKind.REGULAR, length=1, unit=D.StepUnit.MONTH)
ANNUAL = D.Cadence(D.CadenceKind.REGULAR, length=1, unit=D.StepUnit.YEAR)
MONTHLY_SEASON = D.SeasonKeySpec(D.SeasonKeyKind.MONTH_OF_YEAR, 12)
ANNUAL_SEASON = D.SeasonKeySpec(D.SeasonKeyKind.CONSTANT, 1)
WINDOWS = D.Windows(y0=2003, y_end=2012, test_years=(2009, 2010, 2011, 2012), train_end=2008,
                    inner_fit=(2003, 2005), inner_score=(2006, 2007, 2008))


def monthly_cuts():
    plan = D.derive_r10_leads(MONTHLY_SEASON, False).value
    return D.derive_r11_cuts(WINDOWS, plan, MONTHLY).value


# ===================================================================================================
# R9 freeze epochs
def test_cut_days_turn_each_step_cut_into_its_last_day():
    cuts = monthly_cuts()
    out = D.cut_days(cuts, MONTHLY)
    assert sorted(out) == sorted(cuts)
    assert out[0].fit_cut_day == day(2008, 12, 31) and out[0].guard_cut_day == day(2005, 12, 31)
    assert out[6].fit_cut_day == day(2008, 7, 31)                   # lead 6: five steps back (owner ruling I1)
    assert out[0].lead_unit == D.LeadUnit.STEPS
    annual = D.derive_r11_cuts(WINDOWS, D.derive_r10_leads(ANNUAL_SEASON, False).value, ANNUAL).value
    assert D.cut_days(annual, ANNUAL)[1].fit_cut_day == day(2008, 12, 31)


def test_cut_days_refusals():
    cuts = monthly_cuts()
    refused("R9", D.cut_days, {}, MONTHLY)
    refused("R9", D.cut_days, {1: cuts[0]}, MONTHLY)                # key and lead differ
    events = D.Cadence(D.CadenceKind.IRREGULAR)
    refused("R9", D.cut_days, cuts, events)                         # step cuts on an event target


def test_r9_takes_the_latest_epoch_at_or_before_each_cut_d27():
    cuts = D.cut_days(monthly_cuts(), MONTHLY)
    epochs = {"lc": [day(2000, 6, 30), day(2005, 12, 31), day(2008, 12, 31), day(2011, 6, 30)]}
    out = D.derive_r09_freeze_epochs(epochs, cuts)
    assert out.rule_id == "R9" and out.flags == ()
    assert out.value["lc"][0] == {"fit": day(2008, 12, 31), "guard": day(2005, 12, 31)}   # inclusive
    assert out.value["lc"][6]["fit"] == day(2005, 12, 31)          # the lead-6 cut is 31 July
    assert set(out.value["lc"]) == set(cuts)
    assert D.derived_entry(out)["value"]["lc"]["0"]["guard"] == day(2005, 12, 31)


def test_r9_reads_event_cuts_in_days_and_flags_an_empty_map():
    pair = timing.CutPair(lead=0, lead_unit=D.LeadUnit.DAYS, fit_cut=day(2010, 12, 31),
                          guard_cut=day(2007, 12, 31))
    out = D.derive_r09_freeze_epochs({"e": [day(2007, 1, 1), day(2009, 1, 1)]}, {0: pair})
    assert out.value["e"][0] == {"fit": day(2009, 1, 1), "guard": day(2007, 1, 1)}
    empty = D.derive_r09_freeze_epochs({}, D.cut_days(monthly_cuts(), MONTHLY))
    assert empty.value == {} and empty.flags == ("no_freeze_columns",)


def test_r9_refusals():
    cuts = monthly_cuts()
    days = D.cut_days(cuts, MONTHLY)
    assert "not days" in refused("R9", D.derive_r09_freeze_epochs, {"lc": [day(2000, 1, 1)]}, cuts)
    refused("R9", D.derive_r09_freeze_epochs, {"lc": [day(2000, 1, 1)]}, {})
    refused("R9", D.derive_r09_freeze_epochs, {"lc": []}, days)
    refused("R9", D.derive_r09_freeze_epochs, {"lc": [1.5]}, days)
    with pytest.raises(TimingRefusal) as info:                    # no epoch at or before a cut
        D.derive_r09_freeze_epochs({"lc": [day(2006, 1, 1)]}, days)
    assert info.value.rule == "R9"


# ===================================================================================================
# R12 router kind
def test_valid_rows_per_unit_counts_valid_rows_inside_the_window_only():
    units = np.array(["a", "a", "a", "b", "b", "c"], dtype=object)
    steps = np.array([1, 2, 9, 1, 2, 9])
    valid = np.array([True, True, True, False, True, True])
    assert D.count_valid_rows_per_unit(units, steps, valid, 1, 5) == {"a": 2, "b": 1, "c": 0}
    refused("R12", D.count_valid_rows_per_unit, units, steps, valid.astype(int), 1, 5)
    refused("R12", D.count_valid_rows_per_unit, units[:-1], steps, valid, 1, 5)
    refused("R12", D.count_valid_rows_per_unit, units, steps, valid, 5, 1)
    refused("R12", D.count_valid_rows_per_unit, units, steps.astype(float) + 0.5, valid, 1, 5)
    refused("R12", D.count_valid_rows_per_unit, np.array(["a", "", "b", "b", "c", "c"], dtype=object),
            steps, valid, 1, 5)


def test_constant_history_share_counts_units_with_one_value():
    units = np.array(["a", "a", "b", "b", "c"], dtype=object)
    y = np.array([0.0, 0.0, 0.1, 0.2, 0.3])
    assert D.constant_history_share(units, y) == pytest.approx(2 / 3)
    refused("R12", D.constant_history_share, units[:0], y[:0])
    refused("R12", D.constant_history_share, units, y[:-1])
    refused("R12", D.constant_history_share, units, np.array([0.0, np.nan, 0.1, 0.2, 0.3]))


@pytest.mark.parametrize("counts,kind", [
    ([24, 24, 24], D.RouterKind.PER_UNIT),
    ([23, 24], D.RouterKind.REGION),               # D10: the midpoint 23.5
    ([2, 2, 40], D.RouterKind.REGION),
    ([1, 2], D.RouterKind.NEIGHBOUR),              # 1.5
    ([0, 0, 1], D.RouterKind.NEIGHBOUR),
])
def test_r12_kind_by_the_median_valid_rows(counts, kind):
    out = D.derive_r12_router_kind({"u%d" % i: n for i, n in enumerate(counts)})
    assert out.value == kind
    assert out.inputs["h"] == float(np.median(counts))
    assert set(out.margins) == {"C5.per_unit_min_valid_rows", "C5.region_min_valid_rows"}


def test_r12_counts_and_flags_the_fallback_units():
    counts = {"u%02d" % i: 200 for i in range(18)}
    counts.update({"s1": 10, "s2": 3})                 # 2 of 20 = 10% under 24 valid rows
    out = D.derive_r12_router_kind(counts)
    assert out.value == D.RouterKind.PER_UNIT
    assert out.inputs["fallback_units"] == 2 and out.inputs["fallback_share"] == pytest.approx(0.1)
    assert "fallback_share_above:C10.fallback_flag_share" in out.flags
    one = D.derive_r12_router_kind({**{"u%02d" % i: 200 for i in range(19)}, "s1": 10})
    assert "fallback_share_above:C10.fallback_flag_share" not in one.flags      # exactly 5%
    near = D.derive_r12_router_kind({"a": 25, "b": 25})
    assert "borderline:C5.per_unit_min_valid_rows" in near.flags


def test_r12_refusals():
    refused("R12", D.derive_r12_router_kind, {})
    refused("R12", D.derive_r12_router_kind, {"a": -1})
    refused("R12", D.derive_r12_router_kind, {"a": 2.5})
    refused("R12", D.derive_r12_router_kind, {"": 3})


# ===================================================================================================
# R13 decision surface
GROUPS = ("g_c", "g_a", "g_b", "g_d")


def test_r13_inner_window_for_per_unit_and_region():
    for kind in (D.RouterKind.PER_UNIT, "region"):
        out = D.derive_r13_surface_loro(kind, GROUPS)
        assert out.value == (D.LoroSurfaceKind.INNER_WINDOW, ())


def test_r13_neighbour_is_one_fold_per_group_in_sorted_order():
    out = D.derive_r13_surface_loro(D.RouterKind.NEIGHBOUR, GROUPS)
    assert out.value == (D.LoroSurfaceKind.LEAVE_ONE_GROUP_OUT, (("g_a",), ("g_b",), ("g_c",), ("g_d",)))
    assert D.derived_entry(out)["value"] == ["leave_one_group_out", [["g_a"], ["g_b"], ["g_c"], ["g_d"]]]


def test_r13_refusals():
    refused("R13", D.derive_r13_surface_loro, "neighbour", ("g_a", "g_b"))
    refused("R13", D.derive_r13_surface_loro, "ridge", GROUPS)
    refused("R13", D.derive_r13_surface_loro, "per_unit", ())
    refused("R13", D.derive_r13_surface_loro, "per_unit", ("g_a", "g_a"))
    refused("R13", D.derive_r13_surface_loro, "per_unit", "g_a")


# ===================================================================================================
# R14 router design
def test_r14_per_unit_design_and_grid():
    out = D.derive_r14_router_design(D.RouterKind.PER_UNIT, ("c1", "c2"))
    d = out.value
    assert d.columns == ("intercept", "normal", "context", "trees")
    assert d.unpenalised == ("intercept", "normal") and d.fit_row_cap is None
    assert d.centre == (0.5, 0.25) and len(d.grid) == 35
    assert d.grid[0] == D.GridPoint(0.1, 0.0625) and d.grid[1] == D.GridPoint(0.1, 0.125)   # level-major
    assert out.inputs["base_point"] == D.GridPoint(1.0, 0.5)
    bare = D.derive_r14_router_design("per_unit", ()).value
    assert bare.columns == ("intercept", "normal", "trees") and len(bare.grid) == 7
    assert all(p.ratio is None for p in bare.grid)


def test_r14_matches_the_routers_own_per_unit_design():
    try:
        from treeroute.route import kinds as RK
    except Exception as exc:                  # the router is built in parallel: report, never hide
        pytest.skip("route.kinds does not import (%s)" % exc)
    for has_context in (True, False):
        ours = D.derive_r14_router_design("per_unit", ("c1",) if has_context else ()).value
        theirs = RK.per_unit_router_design(has_context)
        assert ours.columns == theirs.columns and ours.unpenalised == theirs.unpenalised
        assert ours.centre == theirs.centre and ours.fit_row_cap == theirs.fit_row_cap
        assert [(p.level, p.ratio) for p in ours.grid] == [(p.level, p.ratio) for p in theirs.grid]


def test_r14_region_and_neighbour_designs():
    region = D.derive_r14_router_design("region", ("c1",))
    assert region.value.columns == ("intercept", "normal", "trees")
    assert region.value.centre == (100.0,) and region.value.fit_row_cap == 60000
    assert [p.level for p in region.value.grid] == [0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0]
    assert region.flags == ("context_unused",)
    neighbour = D.derive_r14_router_design("neighbour", ("c1",)).value
    assert neighbour.columns == ("intercept", "context", "trees") and neighbour.unpenalised == ("intercept",)
    assert len(neighbour.grid) == 35 and neighbour.fit_row_cap is None


def test_r14_refusals(monkeypatch):
    refused("R14", D.derive_r14_router_design, "ridge", ())
    refused("R14", D.derive_r14_router_design, "per_unit", ("c1", "c1"))
    refused("R14", D.derive_r14_router_design, "per_unit", "c1")
    monkeypatch.setattr(K, "PER_UNIT_CONTEXT_CENTRE", 0.3)          # centre ratio 0.6 is off the grid
    refused("R14", D.derive_r14_router_design, "per_unit", ("c1",))


# ===================================================================================================
# R17 own-history spec
def test_r17_monthly_block_six_columns_ending_at_the_issue_step():
    out = D.derive_r17_history_spec(MONTHLY_SEASON, MONTHLY_TARGET, MONTH, "per_unit", False)
    spec = out.value
    assert spec.columns == ("hist_last_1", "hist_last_2", "hist_last_3", "hist_mean_12", "hist_mean_60",
                            "hist_mean_all")
    assert spec.trailing_steps == (12, 60) and spec.start_offset_steps == 0
    assert spec.all_history_mean and spec.dropped_duplicates == () and spec.trailing_days == ()


def test_r17_starts_one_step_back_when_the_target_reaches_past_its_step():
    for target in (REACH_TARGET, detection_target(Reach(1, "month"))):
        out = D.derive_r17_history_spec(MONTHLY_SEASON, target, MONTH, "per_unit", False)
        assert out.value.start_offset_steps == 1 and "start_offset:1" in out.flags


def test_r17_annual_drops_the_one_year_mean():
    out = D.derive_r17_history_spec(ANNUAL_SEASON, ANNUAL_TARGET, YEAR, "region", False)
    spec = out.value
    assert spec.trailing_steps == (1, 5) and spec.dropped_duplicates == ("hist_mean_1",)
    assert len(spec.columns) == 5 and "hist_mean_1" not in spec.columns


def test_r17_neighbour_is_empty_and_events_wait_for_m8():
    spec = D.derive_r17_history_spec(MONTHLY_SEASON, MONTHLY_TARGET, MONTH, "neighbour", False).value
    assert spec.columns == () and spec.last_values == 0
    with pytest.raises(NotImplementedError):
        D.derive_r17_history_spec(D.SeasonKeySpec(D.SeasonKeyKind.EVENT_MONTH, None), MONTHLY_TARGET,
                                  MONTH, "per_unit", True)


def test_r17_refusals():
    refused("R17", D.derive_r17_history_spec, MONTHLY_SEASON, PLAIN_MONTH, MONTH, "per_unit", False)
    refused("R17", D.derive_r17_history_spec, D.SeasonKeySpec(D.SeasonKeyKind.MONTH_OF_YEAR, None),
            MONTHLY_TARGET, MONTH, "per_unit", False)
    refused("R17", D.derive_r17_history_spec, MONTHLY_SEASON, MONTHLY_TARGET, MONTH, "ridge", False)
    unknown = detection_target(None)
    unknown = type(unknown)(**{**unknown.__dict__, "window": win(None, U.MONTH, A.UNKNOWN)})
    with pytest.raises(TimingRefusal):
        D.derive_r17_history_spec(MONTHLY_SEASON, unknown, MONTH, "per_unit", False)


# ===================================================================================================
# R18 bank and scored counts
def test_r18_bank_per_unit_caps_and_flags_thin_groups():
    avail = {"g_a": 250, "g_b": 60, "g_c": 3}
    pooled = {"g_a": 99999, "g_b": 60 * 168, "g_c": 3 * 10}
    out = D.derive_r18_bank_count("per_unit", MONTHLY_SEASON, 168.0, avail, pooled, 4)
    n, bank = out.value
    assert n == 100 and bank == {"g_a": 100, "g_b": 60, "g_c": 3}
    assert out.flags == ("capped:g_b", "capped:g_c", "thin:g_c")       # 30 < 20 x 4 non-tree columns


def test_r18_bank_sub_monthly_region_and_neighbour():
    avail = {"g_a": 5000, "g_b": 2543}
    pooled = {"g_a": 1, "g_b": 2543 * 14}
    sub = D.derive_r18_bank_count("per_unit", D.SeasonKeySpec(D.SeasonKeyKind.COMPOSITE_NUMBER, 46),
                                  0.0, avail, pooled, 2)
    assert sub.value[0] == 27                                            # ceil(1200 / 46)
    region = D.derive_r18_bank_count("region", ANNUAL_SEASON, 14.0, avail, pooled, 2)
    assert region.value == (4285, {"g_a": 4285, "g_b": 2543}) and region.flags == ("capped:g_b",)
    half = D.derive_r18_bank_count("region", ANNUAL_SEASON, 14.5, avail, pooled, 2)
    assert half.value[0] == 4137                                         # floor(60000 / 14.5)
    neighbour = D.derive_r18_bank_count("neighbour", ANNUAL_SEASON, 1.0, {"a": 7, "b": 4, "c": 10},
                                        {"a": 0, "b": 0, "c": 0}, 1)
    assert neighbour.value == (7, {"a": 7, "b": 4, "c": 10}) and neighbour.flags == ()


def test_r18_bank_refusals():
    ok = {"g_a": 10}
    refused("R18", D.derive_r18_bank_count, "ridge", MONTHLY_SEASON, 1.0, ok, ok, 1)
    refused("R18", D.derive_r18_bank_count, "per_unit", MONTHLY_SEASON, 1.0, {}, ok, 1)
    refused("R18", D.derive_r18_bank_count, "per_unit", MONTHLY_SEASON, 1.0, ok, {}, 1)
    refused("R18", D.derive_r18_bank_count, "per_unit", MONTHLY_SEASON, 1.0, ok, ok, 0)
    refused("R18", D.derive_r18_bank_count, "per_unit", MONTHLY_SEASON, 1.0, {"g_a": 0}, ok, 1)
    refused("R18", D.derive_r18_bank_count, "region", ANNUAL_SEASON, 0.0, ok, ok, 1)
    refused("R18", D.derive_r18_bank_count, "region", ANNUAL_SEASON, 60001.0, ok, ok, 1)


def donor_all(y, scope="all_donor_units", lead=0, cut_kind="fit", groups=("g_a",)):
    y = np.asarray(y, dtype=float)
    n = len(y)
    return DonorView(groups=tuple(groups), cut=100, cut_kind=cut_kind, lead=lead, unit_scope=scope,
                     unit_ids=np.array(["u%d" % (i % 7) for i in range(n)], dtype=object),
                     times=100 - np.arange(n) % 50, group_of_row=np.array([groups[i % len(groups)]
                                                                            for i in range(n)], dtype=object),
                     y=y, row_key_hash="cd" * 32)


def test_r18_scored_budget_is_floor_k_n_over_g_capped_at_the_bank():
    groups = ["g%02d" % i for i in range(42)]
    bank = {g: 4285 for g in groups}
    bank["g00"] = 2000
    avail = {g: 5000 for g in groups}
    y = np.arange(1000.0)                               # q90 = 899.1: 100 rows strictly above it
    out = D.derive_r18_scored_count("region", 4285, bank, avail, 20, donor_all(y), 4)
    counts = out.value
    assert isinstance(counts, SP.UnitCounts)
    assert counts.scored_by_group["g01"] == 2040 and counts.scored_by_group["g00"] == 2000
    assert counts.rule_value == 4285 and counts.k_group_equivalents == 20 and counts.n_groups == 42
    assert "scored_capped:g00" in out.flags
    assert out.inputs["event_rate"]["events"] == 100
    assert out.inputs["event_floor_units"] == 25                   # ceil(10 x 1000 / (4 x 100))
    assert out.input_hashes["donor_all_row_key_hash"] == "cd" * 32


def test_r18_scored_minimum_and_event_floor_raise_counts_and_the_bank():
    groups = ["g%03d" % i for i in range(250)]
    bank = {g: 100 for g in groups}
    bank["g000"] = 12
    avail = {g: 400 for g in groups}
    avail["g000"] = 12
    # 1,000 donor rows, 10 strictly above the q90 (a 1% event rate): ceil(10 / (48 x 0.01)) = 21 units
    y = np.r_[np.zeros(990), np.arange(1.0, 11.0)]
    out = D.derive_r18_scored_count("per_unit", 100, bank, avail, 20, donor_all(y), 48)
    counts = out.value
    assert "minimum:g001" in out.flags                  # floor(20 x 100 / 250) = 8 < 10
    assert counts.scored_by_group["g001"] == 21 and "event_floor:g001" in out.flags
    assert counts.scored_by_group["g000"] == 12 and "event_floor_capped:g000" in out.flags
    assert counts.bank_by_group["g001"] == 100
    small = D.derive_r18_scored_count("per_unit", 100, {"a": 15, "b": 15, "c": 15},
                                      {"a": 30, "b": 30, "c": 30}, 20, donor_all(y), 1)
    assert small.value.scored_by_group["a"] == 30 and small.value.bank_by_group["a"] == 30
    assert "bank_raised:a" in small.flags


def test_r18_scored_skips_the_floor_at_a_zero_event_rate():
    y = np.r_[np.zeros(85), np.ones(15)]                # q90 = 1 = the maximum: no row strictly above
    out = D.derive_r18_scored_count("per_unit", 100, {"a": 100, "b": 100, "c": 100},
                                    {"a": 100, "b": 100, "c": 100}, 20, donor_all(y), 48)
    assert "event_floor_skipped:rate_zero" in out.flags and out.inputs["event_floor_units"] is None


def test_r18_scored_refusals(monkeypatch):
    bank = {"a": 10, "b": 10}
    y = np.arange(100.0)
    call = D.derive_r18_scored_count
    refused("R18", call, "per_unit", 100, bank, bank, 19, donor_all(y), 48)     # not the engine K
    refused("R18", call, "per_unit", 0, bank, bank, 20, donor_all(y), 48)
    refused("R18", call, "per_unit", 100, bank, {"a": 10}, 20, donor_all(y), 48)
    refused("R18", call, "per_unit", 100, bank, {"a": 9, "b": 10}, 20, donor_all(y), 48)
    refused("R18", call, "per_unit", 100, bank, bank, 20, donor_all(y, scope="picked"), 48)
    refused("R18", call, "per_unit", 100, bank, bank, 20, donor_all(y, lead=3), 48)
    refused("R18", call, "per_unit", 100, bank, bank, 20, donor_all([]), 48)
    refused("R18", call, "per_unit", 100, bank, bank, 20, donor_all([1.0, np.nan]), 48)
    refused("R18", call, "per_unit", 100, bank, bank, 20, donor_all(y), 0)
    monkeypatch.setattr(K, "K_GROUP_EQUIVALENTS", 19)
    assert call("per_unit", 100, bank, bank, 19, donor_all(y), 48).value.k_group_equivalents == 19


def test_r18_counts_feed_splits_two_lists():
    candidates = {"g_a": tuple("a%03d" % i for i in range(250)), "g_b": tuple("b%03d" % i for i in range(40))}
    counts = SP.UnitCounts(rule_value=100, k_group_equivalents=20, n_groups=2,
                           bank_by_group={"g_a": 100, "g_b": 40}, scored_by_group={"g_a": 15, "g_b": 15})
    lists = SP.pick_unit_lists(("g_a", "g_b"), candidates, counts)
    assert len(lists.bank["g_a"]) == 100 and set(lists.scored["g_a"]) <= set(lists.bank["g_a"])
    assert lists.scored["g_b"][0] == "b000" and lists.scored["g_b"][-1] == "b039"


# ===================================================================================================
# R19 bank plan
def picked(y, groups=("g_a", "g_b")):
    return donor_all(y, scope="picked", groups=groups)


def test_r19_every_group_trains_its_trees_with_bag_sizes_from_its_rows():
    out = D.derive_r19_bank_plan(picked(np.arange(101.0)), False)
    v = out.value
    assert v["trees_per_group"] == 100 and v["bank_trees"] == 200 and v["groups"] == ["g_a", "g_b"]
    assert v["rows_per_group"] == {"g_a": 51, "g_b": 50}
    assert v["bag_size"] == {"g_a": 30, "g_b": 30}                     # max(30, n / 2)
    assert v["expected_oob_share"]["g_a"] == pytest.approx((1 - 1 / 51) ** 30)
    assert v["tree"]["max_depth"] == 8 and v["corrector"]["min_oob_rows"] == 50
    assert "SHA-256" in v["seed_formula"]
    assert out.input_hashes["donor_row_key_hash"] == "cd" * 32
    assert D.derive_r19_bank_plan(picked(np.arange(10.0)), True).value["trees_per_group"] == 12


def test_r19_refusals():
    refused("R19", D.derive_r19_bank_plan, donor_all(np.arange(10.0)), False)            # scope
    view = picked(np.arange(10.0))
    lonely = DonorView(**{**view.__dict__, "groups": ("g_a", "g_b", "g_c")})
    assert "no donor row" in refused("R19", D.derive_r19_bank_plan, lonely, False)
    stray = DonorView(**{**view.__dict__, "groups": ("g_a",)})
    refused("R19", D.derive_r19_bank_plan, stray, False)
    refused("R19", D.derive_r19_bank_plan, picked([]), False)
    guard = DonorView(**{**view.__dict__, "cut_kind": "guard"})
    assert "fit cut" in refused("R19", D.derive_r19_bank_plan, guard, False)


def test_r19_inner_cut_bank_plan_reads_lead_0s_guard_cut_l6b():
    """The inner-cut bank (A7.inner_cut_bank_refit, L6 b) gets the same record from the guard-cut view;
    a fit-cut view, another lead or another scope is refused."""
    guard = DonorView(**{**picked(np.arange(101.0)).__dict__, "cut_kind": "guard"})
    out = D.derive_r19_inner_cut_bank_plan(guard, False)
    base = D.derive_r19_bank_plan(picked(np.arange(101.0)), False)
    assert out.value == base.value and out.rule_id == "R19"
    assert out.inputs["donor"]["cut_kind"] == "guard" and out.inputs["constants"]["A7.inner_cut_bank_refit"]
    assert "inner-cut bank" in out.inputs["bank"] and "A7.inner_cut_bank_refit" not in base.inputs["constants"]
    assert "guard cut" in refused("R19", D.derive_r19_inner_cut_bank_plan, picked(np.arange(10.0)), False)
    other_lead = DonorView(**{**guard.__dict__, "lead": 3})
    refused("R19", D.derive_r19_inner_cut_bank_plan, other_lead, False)
    all_units = DonorView(**{**guard.__dict__, "unit_scope": "all_donor_units"})
    refused("R19", D.derive_r19_inner_cut_bank_plan, all_units, False)


# ===================================================================================================
# R20, R21
def test_r20_tables_per_group_keyed_by_row():
    grid = D.derive_r20_batching(False, ("g_b", "g_a"))
    assert grid.value["row_key"] == ["unit", "step"] and grid.value["batch_order"] == ["g_a", "g_b"]
    assert grid.value["tables"] == ["plain", "corrector", "placebo"]
    assert grid.value["row_block_rows"] == K.TABLE_ROW_BLOCK_ROWS
    assert D.derive_r20_batching(True, ("g_a",)).value["row_key"] == ["unit", "event_date", "issue_date"]
    for bad in [(), "g_a", ("g_a", "g_a"), ("g_a", "")]:
        refused("R20", D.derive_r20_batching, False, bad)


def test_r21_first_four_groups_all_trained_and_tested():
    out = D.derive_r21_smoke_plan_loro(("g_e", "g_b", "g_a", "g_d", "g_c"))
    assert out.value == {"groups": ["g_a", "g_b", "g_c", "g_d"], "units_per_group": 40,
                         "scored_per_group": 40, "trees_per_group": 12}
    three = D.derive_r21_smoke_plan_loro(("g_a", "g_b", "g_c"))
    assert three.value["groups"] == ["g_a", "g_b", "g_c"] and three.flags == ("fewer_groups_than_smoke_plan",)
    refused("R21", D.derive_r21_smoke_plan_loro, ("g_a", "g_b"))
    refused("R21", D.derive_r21_smoke_plan_loro, ("g_a", "g_a", "g_b"))
    refused("R21", D.derive_r21_smoke_plan_loro, "g_a")


# ===================================================================================================
# R30 missing-value flags
def shares(missing, zero=None, by_year=None, scope="picked"):
    return D.MissingShares(donor_row_key_hash="ef" * 32, donor_unit_scope=scope,
                           donor_training_missing_share=missing,
                           donor_training_zero_share=zero if zero is not None else {c: 0.0 for c in missing},
                           test_year_missing_share=by_year or {})


def test_r30_flags_columns_over_the_threshold_or_vanishing_in_a_test_year():
    s = shares({"a": 0.30, "b": 0.25, "c": 0.0, "d": 0.21},
               by_year={("c", 2011): 1.0, ("c", 2010): 0.99, ("a", 2012): 1.0})
    out = D.derive_r30_missing_flags(s, {"b": {"g_x": "no file"}, "c": {}})
    assert out.value == {"a": ("over_threshold", "vanishes:2012"), "c": ("vanishes:2011",)}
    assert "flagged:a" in out.flags and "flagged:c" in out.flags and "flagged:b" not in out.flags
    assert "borderline:b" in out.flags and "borderline:d" in out.flags     # within 20% of 0.25
    assert out.inputs["absent_groups"] == {"b": ["g_x"]}
    assert out.input_hashes["donor_row_key_hash"] == "ef" * 32
    assert D.derived_entry(out)["inputs"]["test_year_missing_share"]["c"] == {"2010": 0.99, "2011": 1.0}


def test_r30_refusals():
    refused("R30", D.derive_r30_missing_flags, shares({"a": 1.2}), {})
    refused("R30", D.derive_r30_missing_flags, shares({"a": "x"}), {})
    refused("R30", D.derive_r30_missing_flags, shares({"a": 0.1}, zero={"b": 0.1}), {})
    refused("R30", D.derive_r30_missing_flags, shares({"a": 0.1}, by_year={("b", 2010): 1.0}), {})
    refused("R30", D.derive_r30_missing_flags, shares({"a": 0.1}, by_year={"a": 1.0}), {})
    refused("R30", D.derive_r30_missing_flags, shares({"a": 0.1}, scope="all_donor_units"), {})
    refused("R30", D.derive_r30_missing_flags, shares({"a": 0.1}), {"a": ["g_x"]})
    refused("R30", D.derive_r30_missing_flags, object(), {})


def rate(events=10, rows=1000, scope="all_donor_units", lead=0, cut_kind="fit"):
    return D.EventRate(events=events, rows=rows, q90=0.5, unit_scope=scope, cut=100, cut_kind=cut_kind,
                       lead=lead, groups=3, row_key_hash="ab" * 32, source="a streamed count")


def test_r18_scored_counts_from_a_streamed_rate_match_the_view():
    bank = {"a": 100, "b": 100, "c": 100}
    y = np.r_[np.zeros(990), np.arange(1.0, 11.0)]
    events, rows, q90 = D.donor_event_rate(y)
    streamed = D.EventRate(events=events, rows=rows, q90=q90, unit_scope="all_donor_units", cut=100,
                           cut_kind="fit", lead=0, groups=1, row_key_hash="cd" * 32,
                           source="donor_event_rate over the label-only donor view")
    via_view = D.derive_r18_scored_count("per_unit", 100, bank, bank, 20, donor_all(y), 48)
    direct = D.scored_counts_at_event_rate("per_unit", 100, bank, bank, 20, streamed, 48)
    assert direct.value == via_view.value and direct.flags == via_view.flags
    assert direct.inputs["event_rate"]["source"] == "donor_event_rate over the label-only donor view"


def test_r18_scored_counts_refuse_a_rate_of_another_scope_or_shape():
    bank = {"a": 10, "b": 10}
    call = D.scored_counts_at_event_rate
    refused("R18", call, "per_unit", 100, bank, bank, 20, rate(scope="picked"), 48)
    refused("R18", call, "per_unit", 100, bank, bank, 20, rate(lead=1), 48)
    refused("R18", call, "per_unit", 100, bank, bank, 20, rate(cut_kind="guard"), 48)
    refused("R18", call, "per_unit", 100, bank, bank, 20, rate(events=11, rows=10), 48)
    refused("R18", call, "per_unit", 100, bank, bank, 20, rate(rows=0, events=0), 48)
    refused("R18", call, "ridge", 100, bank, bank, 20, rate(), 48)
