"""Owner ruling AF2 (the owner rulings file, section AF, 2026-10-21): at the nowcast the twin's eligibility is judged at
the ADOPTED penalty point, the point the alarm uses, not at the twin's own best point; and AF1 recorded by id.

Toys built with the layer's own select_adoption (so every Adoption here is one the engine could lock):
  F1 SPLIT: the twin beats its own-link trees-off at its own best point (it IS in Adoption.eligible) but NOT at the
     adopted point: AF2 says not eligible, the pass is inert, and a batch whose ratio is far above the threshold does
     NOT switch (the pre-AF2 reading, the eligible list, would have switched it: shown on the same rows);
  F2 THE REVERSE: the twin beats its trees-off at the adopted point: eligible, active, the same batch switches. The
     strict reverse of F1 (eligible at the adopted point, NOT at its own best point) cannot come from select_adoption
     (the best point has the lowest MAE against the same baseline): a doctored adoption of that shape is refused;
  F3 NEIGHBOUR KIND (ruling V1): the baseline is the locked decline baseline (the donor-row median), not the trees-off,
     read from adoption.json's decision section; a missing decision section or key is refused;
  F4 the basis record (ruling id, point, both keys and MAEs, the eligible-list reading beside) and the record's
     rulings (AE1, AF1, AF2, AF3 by id); a declined nowcast records "not computed"; AF1: a zero reference gap is not
     tested and the adopted arm stands even at a huge batch gap.
"""

import dataclasses
import datetime as dt
import json

import numpy as np
import pytest

from treeroute.derive.shapes import Link
from treeroute.layer import alarm as LAL
from treeroute.layer import decide as LD
from treeroute.layer.arms import ArmSpec, Tool, Weighting
from treeroute.pipeline import alarm_pass as AP
from treeroute.route.kinds import GridPoint

BOTH = (Weighting.UNWEIGHTED, Weighting.GLS)
P_LOW = GridPoint(1.0, 0.5)
P_HIGH = GridPoint(10.0, 0.5)
PLAIN_U = ArmSpec(Link.IDENTITY, Tool.PLAIN, Weighting.UNWEIGHTED, True)
PLAIN_G = ArmSpec(Link.IDENTITY, Tool.PLAIN, Weighting.GLS, True)
CORR_U = ArmSpec(Link.IDENTITY, Tool.CORRECTOR, Weighting.UNWEIGHTED, True)     # the twin
CORR_G = ArmSpec(Link.IDENTITY, Tool.CORRECTOR, Weighting.GLS, True)            # adopted
OFF = 1.00                                                                      # identity trees-off MAE


def _pick(arm, by_point):
    best = min(by_point, key=lambda p: by_point[p])
    return LD.PenaltyPick(arm=arm, point=best, mae=by_point[best], mae_by_point=dict(by_point), edge=False)


def _adoption(twin_at_adopted, twin_best=0.90, baseline=None):
    """The adopted arm is the GLS corrector at P_HIGH (MAE 0.80, the lowest); its twin (the unweighted corrector) has
    twin_best at P_LOW and twin_at_adopted at P_HIGH (twin_at_adopted >= twin_best: P_LOW stays its best point)."""
    picks = (_pick(PLAIN_U, {P_LOW: 0.97, P_HIGH: 0.98}), _pick(PLAIN_G, {P_LOW: 0.96, P_HIGH: 0.99}),
             _pick(CORR_U, {P_LOW: twin_best, P_HIGH: twin_at_adopted}), _pick(CORR_G, {P_LOW: 0.85, P_HIGH: 0.80}))
    kw = {} if baseline is None else {"baseline": baseline}
    a = LD.select_adoption(picks, {Link.IDENTITY: OFF}, {}, **kw)
    assert a.adopted == CORR_G and a.penalty == P_HIGH and not a.declined
    return a


def _test_rows(n_per_month=40, gap=1.0):
    """Two issue months of day-dated rows; the twin sits `gap` away from the adopted arm on every row."""
    days = np.asarray([dt.date(2000, m, 1 + k % 28).toordinal() for m in (1, 2) for k in range(n_per_month)],
                      dtype=np.int64)
    a = np.linspace(1.0, 2.0, days.size)
    return days, a, a + gap


def _alarm(facts, ref_gap=0.01, gap=1.0):
    days, a, t = _test_rows(gap=gap)
    status = LAL.pass_status(facts["declined"], facts["simpler"], facts["eligible"], ref_gap)
    return LAL.decide_alarm(status, a, a, t, t, LAL.batch_keys(days, None), ref_gap, threshold=2.0, min_batch_rows=30)


# ------------------------------------------------------------------------------------------------ F1
def test_f1_eligible_at_its_own_best_point_but_not_at_the_adopted_point_never_switches():
    a = _adoption(twin_at_adopted=1.05)                  # best 0.90 < 1.00 (in the list); 1.05 at the adopted point
    assert CORR_U in a.eligible                          # the pre-AF2 reading: eligible
    facts = AP.nowcast_twin(a, BOTH, baseline_key=None)
    assert facts["twin"] == CORR_U and facts["simpler"] is True
    assert facts["eligible"] is False                    # AF2: judged at the adopted point
    basis = facts["eligibility_basis"]
    assert basis["in_adoption_eligible_list"] is True and basis["twin_mae"] == 1.05 and basis["baseline_mae"] == OFF
    rec = _alarm(facts)
    assert rec.status == LAL.STATUS_NOT_ELIGIBLE
    assert all(b.ratio == pytest.approx(100.0) for b in rec.batches)        # far above the threshold 2.0 ...
    assert rec.batches_tested == 0 and rec.batches_fired == 0 and rec.rows_switched == 0   # ... and nothing switches
    days, adopted, _ = _test_rows()
    assert np.array_equal(rec.with_alarm, adopted)
    # the same rows under the pre-AF2 reading (the eligible list) WOULD have switched: AF2 is what stops it
    old = _alarm(dict(facts, eligible=LAL.twin_eligible_nowcast(CORR_U, a.eligible)))
    assert old.status == LAL.STATUS_ACTIVE and old.batches_fired == 2


def test_f1_equal_to_the_baseline_at_the_adopted_point_is_not_eligible():
    a = _adoption(twin_at_adopted=OFF)                   # strict, as n2_eligible
    assert AP.nowcast_twin(a, BOTH, baseline_key=None)["eligible"] is False


# ------------------------------------------------------------------------------------------------ F2
def test_f2_eligible_at_the_adopted_point_switches():
    a = _adoption(twin_at_adopted=0.95)                  # 0.95 < 1.00 at the adopted point
    facts = AP.nowcast_twin(a, BOTH, baseline_key=None)
    assert facts["eligible"] is True and facts["eligibility_basis"]["in_adoption_eligible_list"] is True
    rec = _alarm(facts)
    assert rec.status == LAL.STATUS_ACTIVE and rec.batches_tested == 2 and rec.batches_fired == 2
    _, _, twin = _test_rows()
    assert np.array_equal(rec.with_alarm, twin)
    # below the threshold on the same eligible twin: tested, not switched
    calm = _alarm(facts, ref_gap=1.0)
    assert calm.batches_tested == 2 and calm.batches_fired == 0


def test_f2_the_strict_reverse_cannot_come_from_select_adoption_and_is_refused():
    a = _adoption(twin_at_adopted=0.95)
    doctored = dataclasses.replace(a, eligible=tuple(x for x in a.eligible if x != CORR_U))
    with pytest.raises(LAL.AlarmRefusal, match="not in the adoption's eligible list"):
        AP.nowcast_twin(doctored, BOTH, baseline_key=None)
    # and select_adoption itself never makes it: a twin out of the list loses at every point, the adopted one too
    lose = _adoption(twin_at_adopted=1.20, twin_best=1.10)
    assert CORR_U not in lose.eligible
    assert AP.nowcast_twin(lose, BOTH, baseline_key=None)["eligible"] is False


# ------------------------------------------------------------------------------------------------ F3
def test_f3_the_neighbour_kind_judges_against_the_locked_decline_baseline(tmp_path):
    base = ("base__donor_median", 1.10)                  # V1: one baseline for every link
    a = _adoption(twin_at_adopted=1.05, baseline=base)
    assert a.surface_mae["base__donor_median"] == 1.10
    doc = {"adopted": None, "decision": {"decline_baseline": {"key": base[0], "mae": base[1], "rule": "V1 (test)"}}}
    (tmp_path / "adoption.json").write_text(json.dumps(doc), encoding="utf-8")
    key = AP.decline_baseline_key(tmp_path)
    assert key == "base__donor_median"
    facts = AP.nowcast_twin(a, BOTH, baseline_key=key)
    assert facts["eligible"] is True                     # 1.05 < 1.10 (the trees-off 1.00 would have said no)
    assert facts["eligibility_basis"]["baseline"] == "base__donor_median"
    assert AP.nowcast_twin(a, BOTH, baseline_key=None)["eligible"] is False      # the grid reading differs
    with pytest.raises(LAL.AlarmRefusal, match="hold no"):
        AP.nowcast_twin(a, BOTH, baseline_key="base__not_there")


def test_f3_the_baseline_key_is_read_from_the_locked_decision_or_refused(tmp_path):
    (tmp_path / "adoption.json").write_text(json.dumps({"decision": {"grid": []}}), encoding="utf-8")
    assert AP.decline_baseline_key(tmp_path) is None     # every grid kind
    (tmp_path / "adoption.json").write_text(json.dumps({"adopted": None}), encoding="utf-8")
    with pytest.raises(AP.AlarmPassRefusal, match="no decision section"):
        AP.decline_baseline_key(tmp_path)
    (tmp_path / "adoption.json").write_text(json.dumps({"decision": {"decline_baseline": {"mae": 1.0}}}),
                                            encoding="utf-8")
    with pytest.raises(AP.AlarmPassRefusal, match="names no key"):
        AP.decline_baseline_key(tmp_path)


def test_f3_the_twin_point_must_be_on_the_surface():
    a = _adoption(twin_at_adopted=0.95)
    with pytest.raises(LAL.AlarmRefusal, match="hold no"):
        LAL.twin_eligible_at_point(a.surface_mae, CORR_U, GridPoint(3.0, 0.5))
    with pytest.raises(LAL.AlarmRefusal, match="adopted point"):
        LAL.twin_eligible_at_point(a.surface_mae, CORR_U, None)


# ------------------------------------------------------------------------------------------------ F4
def test_f4_the_record_names_the_rulings_and_the_basis():
    a = _adoption(twin_at_adopted=1.05)
    facts = AP.nowcast_twin(a, BOTH, baseline_key=None)
    basis = facts["eligibility_basis"]
    assert basis["ruling"] == "AF2" and basis["point"] == {"level": 10.0, "ratio": 0.5}
    assert basis["twin_key"] == LD.candidate_key(CORR_U, P_HIGH) and basis["baseline"] == "identity_trees_off_unweighted"
    doc = LAL.alarm_document(_alarm(facts), {"lead": 0, "eligibility_basis": basis})
    assert set(doc["rulings"]) == {"AE1", "AF1", "AF2", "AF3"}
    assert doc["rulings"]["AF2"] == LAL.AF2_RULE and doc["rulings"]["AF1"] == LAL.AF1_RULE
    assert "AF2" in doc["rule"] and "AF1" in doc["rule"]
    na = LAL.not_applicable_document(0, "adoption.json", "0" * 64, "a harness replay scores no arm")
    assert set(na["rulings"]) == {"AE1", "AF1", "AF2", "AF3"}


def test_f4_a_declined_nowcast_records_not_computed():
    a = LD.select_adoption((_pick(PLAIN_U, {P_LOW: 2.0}), _pick(PLAIN_G, {P_LOW: 2.0}),
                            _pick(CORR_U, {P_LOW: 2.0}), _pick(CORR_G, {P_LOW: 2.0})), {Link.IDENTITY: OFF}, {})
    assert a.declined
    facts = AP.nowcast_twin(a, BOTH, baseline_key=None)
    assert facts["eligible"] is None and facts["eligibility_basis"]["basis"].startswith("not computed")


def test_f4_af1_a_zero_reference_gap_is_not_tested_and_the_adopted_arm_stands():
    a = _adoption(twin_at_adopted=0.95)
    facts = AP.nowcast_twin(a, BOTH, baseline_key=None)
    rec = _alarm(facts, ref_gap=0.0, gap=5.0)
    assert rec.status == LAL.STATUS_ZERO_GAP and rec.batches_tested == 0 and rec.rows_switched == 0
    days, adopted, _ = _test_rows(gap=5.0)
    assert np.array_equal(rec.with_alarm, adopted)
