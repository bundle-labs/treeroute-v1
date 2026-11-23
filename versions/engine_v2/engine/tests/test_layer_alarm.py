"""layer/alarm.py: the twin-disagreement alarm's pure rule (owner ruling AE with the AE1 amendment; no I/O).

  U1 twin_of: every link x tool x weighting for the two weighting sets; the weighting twin is preferred; the tool twin
     only without the other weighting; trees-off and placebo refused;
  U2 twin_is_simpler: GLS -> unweighted and corrector -> plain are simpler; the reverse never;
  U3 batch_keys: monthly steps, annual steps (the year), composite steps (the calendar month of the first day: two
     composites in one month share a batch), day ordinals (YYYY-MM), month edges;
  U4 decide_alarm: a ratio of exactly 2.0 does not switch, above it does; 29 rows untested, 30 tested; R = 0 or NaN not
     tested; an inert or declined pass never switches (even at ratio 100); with_alarm is the twin exactly in switched
     batches; batches in a fixed order;
  U5 eligibility: twin_eligible_nowcast reads Adoption.eligible (since owner ruling AF2 recorded beside only; the
     nowcast's rule, the twin at the ADOPTED point, is tests/test_alarm_af2.py); a lead compares the twin's guard MAE
     with its guard's baseline (strict).
"""

import datetime as dt

import numpy as np
import pytest

from treeroute import engine_constants as K
from treeroute.derive.shapes import Cadence, CadenceKind, Link, StepUnit
from treeroute.layer import alarm as LAL
from treeroute.layer.arms import ArmSpec, Tool, Weighting, placebo_of, trees_off_of

LINKS = (Link.IDENTITY, Link.LOG_C, Link.ARCSINE)
BOTH = (Weighting.UNWEIGHTED, Weighting.GLS)
UNW = (Weighting.UNWEIGHTED,)


def arm(link, tool, w):
    return ArmSpec(link, tool, w, True)


# ------------------------------------------------------------------------------------------------ U1, U2
@pytest.mark.parametrize("link", LINKS)
@pytest.mark.parametrize("tool", (Tool.PLAIN, Tool.CORRECTOR))
@pytest.mark.parametrize("w", BOTH)
def test_u1_the_weighting_twin_is_preferred_when_both_weightings_are_routed(link, tool, w):
    twin, kind = LAL.twin_of(arm(link, tool, w), BOTH)
    other = Weighting.GLS if w is Weighting.UNWEIGHTED else Weighting.UNWEIGHTED
    assert kind == LAL.TWIN_WEIGHTING and twin == arm(link, tool, other)
    assert LAL.twin_is_simpler(arm(link, tool, w), twin) is (w is Weighting.GLS)


@pytest.mark.parametrize("link", LINKS)
@pytest.mark.parametrize("tool", (Tool.PLAIN, Tool.CORRECTOR))
def test_u1_the_tool_twin_is_used_only_without_the_other_weighting(link, tool):
    twin, kind = LAL.twin_of(arm(link, tool, Weighting.UNWEIGHTED), UNW)
    other = Tool.PLAIN if tool is Tool.CORRECTOR else Tool.CORRECTOR
    assert kind == LAL.TWIN_TOOL and twin == arm(link, other, Weighting.UNWEIGHTED)
    assert LAL.twin_is_simpler(arm(link, tool, Weighting.UNWEIGHTED), twin) is (tool is Tool.CORRECTOR)


def test_u1_trees_off_placebo_and_a_foreign_weighting_are_refused():
    with pytest.raises(LAL.AlarmRefusal, match="selectable tree arm"):
        LAL.twin_of(trees_off_of(Link.IDENTITY), BOTH)
    with pytest.raises(LAL.AlarmRefusal, match="selectable tree arm"):
        LAL.twin_of(placebo_of(arm(Link.LOG_C, Tool.CORRECTOR, Weighting.GLS)), BOTH)
    with pytest.raises(LAL.AlarmRefusal, match="not among the routed weightings"):
        LAL.twin_of(arm(Link.LOG_C, Tool.CORRECTOR, Weighting.GLS), UNW)


def test_u2_simpler_is_one_way_only():
    g = arm(Link.ARCSINE, Tool.CORRECTOR, Weighting.GLS)
    u = arm(Link.ARCSINE, Tool.CORRECTOR, Weighting.UNWEIGHTED)
    p = arm(Link.ARCSINE, Tool.PLAIN, Weighting.UNWEIGHTED)
    assert LAL.twin_is_simpler(g, u) and LAL.twin_is_simpler(u, p)
    assert not LAL.twin_is_simpler(u, g) and not LAL.twin_is_simpler(p, u)
    assert not LAL.twin_is_simpler(g, p)                              # two changes: never a twin
    assert not LAL.twin_is_simpler(g, arm(Link.LOG_C, Tool.CORRECTOR, Weighting.UNWEIGHTED))


# ------------------------------------------------------------------------------------------------ U3
def _ord(y, m, d):
    return dt.date(y, m, d).toordinal()


def test_u3_monthly_and_annual_steps_are_their_own_batch():
    monthly = Cadence(CadenceKind.REGULAR, 1, StepUnit.MONTH)
    annual = Cadence(CadenceKind.REGULAR, 1, StepUnit.YEAR)
    keys = LAL.batch_keys(np.array([24097, 24097, 24098], dtype=np.int64), monthly)
    assert keys.tolist() == ["step:24097", "step:24097", "step:24098"]
    assert LAL.batch_keys(np.array([2001, 2002, 2002], dtype=np.int64), annual).tolist() == \
        ["step:2001", "step:2002", "step:2002"]


def test_u3_composite_steps_batch_by_the_calendar_month_of_their_first_day():
    comp = Cadence(CadenceKind.COMPOSITE_OF_YEAR, None, None, 23, 16)
    # composite n of year Y is step Y * 23 + n (io/steps.py step_index: year, n0 = divmod(s - 1, 23))
    y = 2010
    steps = np.array([y * 23 + 1, y * 23 + 2, y * 23 + 3, y * 23 + 4], dtype=np.int64)   # Jan 1, Jan 17, Feb 2, Feb 18
    keys = LAL.batch_keys(steps, comp).tolist()
    assert keys[0] == keys[1] == "2010-01" and keys[2] == keys[3] == "2010-02"


def test_u3_day_ordinals_batch_by_calendar_month_with_exact_edges():
    days = np.array([_ord(2009, 1, 31), _ord(2009, 2, 1), _ord(2009, 2, 28), _ord(2009, 3, 1), _ord(2008, 12, 31)],
                    dtype=np.int64)
    assert LAL.batch_keys(days, None).tolist() == ["2009-01", "2009-02", "2009-02", "2009-03", "2008-12"]


def test_u3_a_cadence_without_calendar_steps_and_non_integer_issues_are_refused():
    with pytest.raises(LAL.AlarmRefusal, match="whole number"):
        LAL.batch_keys(np.array([1.5]), None)
    with pytest.raises(Exception):
        LAL.batch_keys(np.array([1], dtype=np.int64), Cadence(CadenceKind.STATIC))


# ------------------------------------------------------------------------------------------------ U4
def _rows(gaps, sizes):
    """A pass whose batch b has sizes[b] rows and a constant |A - T| of gaps[b]."""
    a, t, keys = [], [], []
    for b, (g, n) in enumerate(zip(gaps, sizes)):
        a += [1.0] * n
        t += [1.0 + g] * n
        keys += ["2010-%02d" % (b + 1)] * n
    return np.array(a), np.array(t), np.array(keys, dtype=object)


def test_u4_the_threshold_is_strict_and_the_batch_floor_is_thirty():
    assert K.ALARM_RATIO_THRESHOLD == 2.0 and K.ALARM_MIN_BATCH_ROWS == 30
    R = 0.5
    a, t, keys = _rows([1.0, 1.0 + 1e-9, 5.0, 5.0], [30, 30, 29, 30])
    rec = LAL.decide_alarm(LAL.STATUS_ACTIVE, a, a - 0.1, t, t - 0.1, keys, R)
    got = {b.batch: (b.rows, b.tested, b.fired) for b in rec.batches}
    assert got["2010-01"] == (30, True, False)                      # ratio exactly 2.0: no switch
    assert got["2010-02"] == (30, True, True)                       # just above 2.0: switch
    assert got["2010-03"] == (29, False, False)                     # 29 rows: not tested
    assert got["2010-04"] == (30, True, True)
    assert rec.batches_fired == 2 and rec.rows_switched == 60
    sw = np.asarray(rec.fired)
    assert np.array_equal(rec.with_alarm[sw], t[sw]) and np.array_equal(rec.with_alarm[~sw], a[~sw])
    assert np.array_equal(rec.pre_with_alarm[sw], (t - 0.1)[sw]) and np.array_equal(rec.pre_with_alarm[~sw], (a - 0.1)[~sw])


@pytest.mark.parametrize("gap", (0.0, float("nan"), None))
def test_u4_a_zero_or_missing_reference_gap_is_not_tested(gap):
    status = LAL.pass_status(False, True, True, gap)
    assert status == LAL.STATUS_ZERO_GAP
    a, t, keys = _rows([5.0], [40])
    rec = LAL.decide_alarm(status, a, a, t, t, keys, gap)
    assert rec.rows_switched == 0 and not any(b.tested for b in rec.batches)
    assert np.array_equal(rec.with_alarm, a)


@pytest.mark.parametrize("declined,simpler,eligible,want", [
    (True, True, True, LAL.STATUS_DECLINED), (False, False, True, LAL.STATUS_NOT_SIMPLER),
    (False, True, False, LAL.STATUS_NOT_ELIGIBLE), (False, None, None, LAL.STATUS_NOT_SIMPLER)])
def test_u4_an_inert_or_declined_pass_never_switches_even_at_ratio_100(declined, simpler, eligible, want):
    status = LAL.pass_status(declined, simpler, eligible, 0.01)
    assert status == want
    a, t, keys = _rows([1.0, 1.0], [50, 50])                        # ratio 100
    rec = LAL.decide_alarm(status, a, a, t, t, keys, 0.01)
    assert rec.rows_switched == 0 and np.array_equal(rec.with_alarm, a)
    assert all(b.ratio == pytest.approx(100.0) and not b.tested for b in rec.batches)


def test_u4_an_active_pass_needs_its_twin_and_finite_values():
    a, t, keys = _rows([1.0], [40])
    with pytest.raises(LAL.AlarmRefusal, match="needs its twin"):
        LAL.decide_alarm(LAL.STATUS_ACTIVE, a, a, None, None, keys, 0.5)
    bad = t.copy()
    bad[3] = np.nan
    with pytest.raises(LAL.AlarmRefusal, match="missing"):
        LAL.decide_alarm(LAL.STATUS_ACTIVE, a, a, bad, bad, keys, 0.5)
    with pytest.raises(LAL.AlarmRefusal, match="unknown"):
        LAL.decide_alarm("on", a, a, t, t, keys, 0.5)


def test_u4_batches_are_ordered_steps_by_number_and_the_record_is_read_only():
    keys = np.array(["step:10", "step:9", "step:100", "step:9"], dtype=object)
    a = np.zeros(4)
    rec = LAL.decide_alarm(LAL.STATUS_ACTIVE, a, a, a + 1, a + 1, keys, 0.1, min_batch_rows=1)
    assert [b.batch for b in rec.batches] == ["step:9", "step:10", "step:100"]
    with pytest.raises(ValueError):
        rec.with_alarm[0] = 5.0
    assert LAL.with_alarm_column(a, a + 1, rec.fired).tolist() == rec.with_alarm.tolist()


def test_u4_the_document_carries_the_ae3_origin_and_the_constants():
    a, t, keys = _rows([1.0], [40])
    rec = LAL.decide_alarm(LAL.STATUS_ACTIVE, a, a, t, t, keys, 0.1)
    doc = LAL.alarm_document(rec, {"lead": 0, "adoption_sha256": "a" * 64})
    assert doc["alarm_origin"] == LAL.ALARM_ORIGIN and "AFTER the engine v1 headline runs" in doc["alarm_origin"]
    assert doc["constants"] == {"A8.alarm_ratio_threshold": 2.0, "A8.alarm_min_batch_rows": 30}
    assert doc["batches_fired"] == 1 and doc["rows_switched"] == 40 and doc["status"] == LAL.STATUS_ACTIVE
    na = LAL.not_applicable_document(0, "adoption.json", "b" * 64, "a reason")
    assert na["status"] == LAL.STATUS_HARNESS and na["batches"] == [] and na["alarm_origin"] == LAL.ALARM_ORIGIN


# ------------------------------------------------------------------------------------------------ U5
def test_u5_nowcast_eligibility_reads_the_locked_eligible_list():
    g = arm(Link.LOG_C, Tool.CORRECTOR, Weighting.GLS)
    u = arm(Link.LOG_C, Tool.CORRECTOR, Weighting.UNWEIGHTED)
    assert LAL.twin_eligible_nowcast(u, (g, u)) and not LAL.twin_eligible_nowcast(u, (g,))


def test_u5_lead_eligibility_is_strict_against_the_guard_baseline():
    assert LAL.twin_eligible_lead(1.0, 1.5)                        # trees-off or donor-row median MAE
    assert not LAL.twin_eligible_lead(1.5, 1.5)                    # strict, as n2_eligible
    with pytest.raises(LAL.AlarmRefusal, match="finite"):
        LAL.twin_eligible_lead(float("nan"), 1.0)
    assert LAL.reference_gap([1.0, 2.0], [1.5, 1.0]) == pytest.approx(0.75)
    assert np.isnan(LAL.reference_gap([], []))
