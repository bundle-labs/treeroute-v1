"""R11 cuts per lead (grids in integer steps, events in days), the label rule and R9 freeze epochs.

The grid cuts reproduce the shipped rule (pm25_forecast.py:190-197): cut(L) = min(T_end, T_end + 1 - L).
The four packages' windows and leads are read from their expected_derived.json (tests only).
"""

import json

import pytest

from conftest import ENGINE_DIR
from test_timing_facts import C, DAILY, EPOCH, EVENTS, MONTH, QUARTER, STATIC, YEAR, composite, day
from treeroute.timing import (CutPair, TimingRefusal, cuts_for_leads, event_fit_cut_day,
                              event_guard_cut_day, fit_cut_step, freeze_epoch, guard_cut_step,
                              label_usable, latest_label_step, year_last_step)

STEPS = C.LeadUnit.STEPS
DAYS = C.LeadUnit.DAYS


def windows(train_end, inner_fit, test_years, inner_score, y0=None, y_end=None):
    return C.Windows(y0=y0 or inner_fit[0], y_end=y_end or max(test_years),
                     test_years=tuple(test_years), train_end=train_end, inner_fit=tuple(inner_fit),
                     inner_score=tuple(inner_score))


def lead_plan(leads, unit=STEPS):
    return C.LeadPlan(requested_months=(6, 12), leads=tuple(leads), lead_unit=unit,
                      merged={}, not_supplied=(), contract_lead_zero=True)


def package(name):
    exp = json.loads((ENGINE_DIR / "datasets" / name / "expected_derived.json").read_text("utf-8"))
    w = exp["R3_R7_windows"]
    return (windows(w["train_end"], w["inner_fit"], w["test_years"], w["inner_score"], w["y0"],
                    w["y_end"]),
            lead_plan(exp["R10_leads"]["leads"]), exp["R1_cadence"]["unit"])


# ---- grid cuts ----
def test_fit_cut_moves_back_l_minus_one_steps_never_later_than_the_train_end():
    assert fit_cut_step(0, 1000) == 1000
    assert fit_cut_step(1, 1000) == 1000
    assert fit_cut_step(3, 1000) == 998
    assert fit_cut_step(12, 1000) == 989
    assert guard_cut_step(0, 900) == 900 and guard_cut_step(6, 900) == 895


@pytest.mark.parametrize("call", [lambda: fit_cut_step(-1, 100), lambda: guard_cut_step(-1, 100),
                                  lambda: latest_label_step(100, -1)])
def test_negative_leads_are_refused(call):
    with pytest.raises(TimingRefusal) as info:
        call()
    assert info.value.rule == "R11"


def test_shipped_forecast_rule_is_reproduced():
    # cut_of(L) = min(T_DEC_train_end, T_DEC_train_end + 1 - L), for every lead of the ladder
    t_dec = 2019 * 12 + 12
    for lead in (0, 1, 3, 6, 12):
        assert fit_cut_step(lead, t_dec) == min(t_dec, t_dec + 1 - lead)


def test_latest_label_step():
    assert latest_label_step(500, 0) == 499          # nowcast: t - 1
    assert latest_label_step(500, 1) == 499          # lead 1: the issue step
    assert latest_label_step(500, 12) == 488


# ---- event cuts (days) ----
def test_event_cuts():
    test_first, train_end_last = day(2016, 1, 1), day(2015, 12, 31)
    assert event_fit_cut_day(0, test_first, train_end_last) == train_end_last
    assert event_fit_cut_day(30, test_first, train_end_last) == test_first - 30
    score_first, fit_end_last = day(2013, 1, 1), day(2012, 12, 31)
    assert event_guard_cut_day(0, score_first, fit_end_last) == fit_end_last        # D99
    assert event_guard_cut_day(91, score_first, fit_end_last) == score_first - 91
    with pytest.raises(TimingRefusal):
        event_fit_cut_day(-30, test_first, train_end_last)
    with pytest.raises(TimingRefusal):
        event_guard_cut_day(-1, score_first, fit_end_last)


# ---- the label rule (D19 inclusive; D26 the window-ended clause on grids too) ----
def test_label_usable_is_inclusive_on_both_clauses():
    cut = day(2019, 12, 31)
    assert label_usable(cut, cut, cut)
    assert not label_usable(cut + 1, cut + 1, cut)
    assert not label_usable(cut, cut + 1, cut)


def test_a_reaching_composite_label_at_the_cut_step_is_not_usable():
    cut = day(2019, 12, 31)                         # last day of the cut step
    dec_label, dec_window_end = cut, day(2020, 1, 15)
    assert not label_usable(dec_label, dec_window_end, cut)
    nov_label, nov_window_end = day(2019, 11, 30), day(2019, 12, 15)
    assert label_usable(nov_label, nov_window_end, cut)


# ---- year_last_step: the step_index form (monthly year x 12 + month; annual year; composites) ----
def test_year_last_step_follows_the_step_index_form():
    assert year_last_step(2019, MONTH) == 2019 * 12 + 12
    assert year_last_step(2019, YEAR) == 2019
    assert year_last_step(2019, composite(16, per_year=23)) == 2019 * 23 + 23
    assert year_last_step(2019, C.Cadence(C.CadenceKind.COMPOSITE_OF_YEAR,
                                          composites_per_year=46, composite_days=8)) == 2019 * 46 + 46


@pytest.mark.parametrize("cadence", [QUARTER, DAILY, composite(16), EVENTS, STATIC, EPOCH,
                                     C.Cadence(C.CadenceKind.REGULAR, length=2,
                                               unit=C.StepUnit.YEAR)])
def test_year_last_step_refuses_what_the_step_index_origin_decides(cadence):
    with pytest.raises(TimingRefusal):
        year_last_step(2019, cadence)


@pytest.mark.parametrize("days,per_year", [
    (16, 24),          # one composite too many: step numbers with a gap
    (16, 22),
    (5, 73),           # 73 composites in a common year, 74 in a leap year: no fixed count
    (5, 74),
    (1, 365),
])
def test_composites_per_year_must_be_the_count_in_every_year(days, per_year):
    with pytest.raises(TimingRefusal) as info:
        year_last_step(2019, composite(days, per_year=per_year))
    assert info.value.rule == "R11"


def test_schema_composite_form_reads_its_length_but_needs_the_count():
    from types import SimpleNamespace as NS
    from treeroute.package import schema as SC
    schema_form = SC.Cadence.model_validate({"kind": "composite_of_year", "length": 16,
                                             "unit": "day"})
    with pytest.raises(TimingRefusal):
        year_last_step(2019, schema_form)            # the schema's Cadence carries no count
    counted = NS(kind="composite_of_year", length=16, unit="day", composites_per_year=23)
    assert year_last_step(2019, counted) == 2019 * 23 + 23
    with pytest.raises(TimingRefusal):
        year_last_step(2019, NS(kind="composite_of_year", length=16, unit="month",
                                composites_per_year=23))


def test_io_label_rule_matches_timing():
    # the R11 label rule exists twice until io calls timing.latest_label_step: they must not drift
    import numpy as np
    from treeroute.io.apply import _latest_label_step
    steps = np.arange(24000, 24300, dtype=np.int64)
    for lead in range(0, 25):
        expected = np.array([latest_label_step(int(t), lead) for t in steps])
        assert np.array_equal(_latest_label_step(steps, lead), expected), lead


# ---- cuts_for_leads ----
@pytest.mark.parametrize("name", ["pm25", "fire", "ndvi"])
def test_monthly_package_cuts(name):
    w, leads, unit = package(name)
    assert unit == "month"
    cuts = cuts_for_leads(w, leads, MONTH)
    assert list(cuts) == [0, 6, 12]                    # owner ruling I1: the nowcast, 6 and 12 months
    t_end, i_end = w.train_end * 12 + 12, w.inner_fit[1] * 12 + 12
    for lead, pair in cuts.items():
        assert pair == CutPair(lead=lead, lead_unit=STEPS, fit_cut=min(t_end, t_end + 1 - lead),
                               guard_cut=min(i_end, i_end + 1 - lead))
    assert cuts[6].fit_cut == t_end - 5 and cuts[12].guard_cut == i_end - 11


def test_annual_package_cuts():
    w, leads, unit = package("defo")
    assert unit == "year" and leads.leads == (1,)
    cuts = cuts_for_leads(w, leads, YEAR)
    assert cuts == {0: CutPair(0, STEPS, 2019, 2016), 1: CutPair(1, STEPS, 2019, 2016)}


def test_composite_of_year_cuts():
    cadence = composite(16, per_year=23)
    w = windows(2019, (2003, 2016), (2020, 2021, 2022, 2023), (2017, 2018, 2019))
    cuts = cuts_for_leads(w, lead_plan((1, 6, 12, 23)), cadence)
    end = 2019 * 23 + 23
    assert cuts[0].fit_cut == end and cuts[23].fit_cut == end - 22


def test_event_cuts_in_days():
    w = windows(2015, (2003, 2012), (2016, 2017, 2018, 2019), (2013, 2014, 2015))
    cuts = cuts_for_leads(w, lead_plan((30, 91, 183, 365), DAYS), EVENTS)
    assert list(cuts) == [0, 30, 91, 183, 365]
    assert cuts[0] == CutPair(0, DAYS, day(2015, 12, 31), day(2012, 12, 31))
    assert cuts[91] == CutPair(91, DAYS, day(2016, 1, 1) - 91, day(2013, 1, 1) - 91)


def test_lead_unit_must_match_the_cadence():
    w = windows(2019, (2003, 2016), (2020, 2021, 2022, 2023), (2017, 2018, 2019))
    with pytest.raises(TimingRefusal):
        cuts_for_leads(w, lead_plan((30,), DAYS), MONTH)
    with pytest.raises(TimingRefusal):
        cuts_for_leads(w, lead_plan((1,), STEPS), EVENTS)


@pytest.mark.parametrize("leads", [(0, 1), (1, 1), (-3,)])
def test_a_malformed_lead_list_is_refused(leads):
    w = windows(2019, (2003, 2016), (2020, 2021, 2022, 2023), (2017, 2018, 2019))
    with pytest.raises(TimingRefusal):
        cuts_for_leads(w, lead_plan(leads), MONTH)


def test_lead_zero_is_always_present():
    w = windows(2019, (2003, 2016), (2020, 2021, 2022, 2023), (2017, 2018, 2019))
    assert list(cuts_for_leads(w, lead_plan(()), MONTH)) == [0]


def test_event_windows_must_be_adjacent():
    w = windows(2014, (2003, 2012), (2016, 2017, 2018, 2019), (2013, 2014, 2015))
    with pytest.raises(TimingRefusal):
        cuts_for_leads(w, lead_plan((30,), DAYS), EVENTS)


@pytest.mark.parametrize("cadence", [MONTH, YEAR, composite(16, per_year=23)])
@pytest.mark.parametrize("w", [
    # train end inside the test window: a fit cut of 2021-Dec would let test labels in
    windows(2021, (2003, 2016), (2020, 2021, 2022, 2023), (2017, 2018, 2019)),
    # train end two years before the test window
    windows(2018, (2003, 2015), (2020, 2021, 2022, 2023), (2016, 2017, 2018)),
    # inner fit overlapping the inner score window
    windows(2019, (2003, 2018), (2020, 2021, 2022, 2023), (2017, 2018, 2019)),
    # inner score window running past the train end (into the test window)
    windows(2019, (2003, 2016), (2020, 2021, 2022, 2023), (2017, 2018, 2019, 2020)),
])
def test_grid_windows_must_satisfy_r6_and_r7(w, cadence):
    with pytest.raises(TimingRefusal) as info:
        cuts_for_leads(w, lead_plan((1, 3)), cadence)
    assert info.value.rule == "R11"


@pytest.mark.parametrize("w", [
    C.Windows(y0=2003, y_end=2023, test_years=(2020,), train_end=2019, inner_fit=None,
              inner_score=(2017, 2018, 2019)),
    C.Windows(y0=2003, y_end=2023, test_years=(2020,), train_end=2019, inner_fit=(2003, 2010, 2016),
              inner_score=(2017, 2018, 2019)),
    C.Windows(y0=2003, y_end=2023, test_years=(), train_end=2019, inner_fit=(2003, 2016),
              inner_score=(2017, 2018, 2019)),
    C.Windows(y0=2003, y_end=2023, test_years=(2020,), train_end=2019, inner_fit=(2003, 2016),
              inner_score=()),
])
@pytest.mark.parametrize("cadence,unit", [(MONTH, STEPS), (EVENTS, DAYS)])
def test_malformed_windows_are_refused(w, cadence, unit):
    with pytest.raises(TimingRefusal):
        cuts_for_leads(w, lead_plan((1,), unit), cadence)


def test_windows_with_a_float_year_are_a_type_error():
    w = C.Windows(y0=2003, y_end=2023, test_years=(2020,), train_end=2019.0, inner_fit=(2003, 2016),
                  inner_score=(2017, 2018, 2019))
    with pytest.raises(TypeError):
        cuts_for_leads(w, lead_plan((1,)), MONTH)


def test_cuts_refuse_a_static_target_and_an_unindexed_step():
    w = windows(2019, (2003, 2016), (2020, 2021, 2022, 2023), (2017, 2018, 2019))
    with pytest.raises(TimingRefusal):
        cuts_for_leads(w, lead_plan((1,)), STATIC)
    with pytest.raises(TimingRefusal):
        cuts_for_leads(w, lead_plan((1,)), DAILY)


# ---- R9 freeze epochs ----
def test_freeze_takes_the_latest_epoch_at_or_before_the_cut():
    epochs = [day(2000, 1, 1), day(2010, 1, 1), day(2020, 1, 1)]
    assert freeze_epoch(epochs, day(2019, 12, 31)) == day(2010, 1, 1)
    assert freeze_epoch(epochs, day(2010, 1, 1)) == day(2010, 1, 1)          # inclusive (D19)
    assert freeze_epoch(reversed(epochs), day(2030, 1, 1)) == day(2020, 1, 1)


def test_guard_cut_can_freeze_an_earlier_epoch_than_the_fit_cut():
    # D27: each cut in use takes the epoch at or before its OWN cut
    epochs = [day(2000, 1, 1), day(2015, 6, 1)]
    assert freeze_epoch(epochs, day(2019, 12, 31)) == day(2015, 6, 1)        # fit cut
    assert freeze_epoch(epochs, day(2016, 12, 31)) == day(2015, 6, 1)
    assert freeze_epoch(epochs, day(2014, 12, 31)) == day(2000, 1, 1)        # an earlier guard cut


def test_freeze_without_an_epoch_at_or_before_the_cut_is_refused():
    with pytest.raises(TimingRefusal) as info:
        freeze_epoch([day(2021, 1, 1)], day(2019, 12, 31))
    assert info.value.rule == "R9" and "ban" in str(info.value)
    with pytest.raises(TimingRefusal):
        freeze_epoch([], day(2019, 12, 31))
