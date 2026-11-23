"""layer/arms.py: R24's candidate list and the arms of a forecast lead (R29).

  - candidate_arms: per link in R22 order plain / corrector x unweighted / GLS (selectable), then every
    link's trees-off (unweighted, not selectable), then every link x weighting's placebo (never
    selectable); refuses a set without identity, a repeat, anything but R22's links;
  - lead_arms: the pinned arm and its link's trees-off, its placebo only at the longest lead;
  - check_arm refuses malformed arms (a selectable placebo, a weighted trees-off, ...).
"""

import enum

import pytest

from treeroute.derive.shapes import Link
from treeroute.layer.arms import (ArmSpec, LayerRefusal, Tool, Weighting, arm_name, candidate_arms,
                                  check_arm, lead_arms, placebo_of, selectable_order, table_kind,
                                  trees_off_of)

U, G = Weighting.UNWEIGHTED, Weighting.GLS


def test_candidate_arms_fixed_order():
    arms = candidate_arms((Link.ARCSINE, Link.IDENTITY, Link.LOG_C))       # any input order
    names = [arm_name(a) for a in arms]
    want = []
    for link in ("identity", "log_c", "arcsine"):
        want += ["%s_plain_unweighted" % link, "%s_plain_gls" % link,
                 "%s_corrector_unweighted" % link, "%s_corrector_gls" % link]
    want += ["%s_trees_off_unweighted" % link for link in ("identity", "log_c", "arcsine")]
    for link in ("identity", "log_c", "arcsine"):
        want += ["%s_placebo_corrector_unweighted" % link, "%s_placebo_corrector_gls" % link]
    assert names == want
    assert [a.selectable for a in arms] == [True] * 12 + [False] * 9
    assert selectable_order((Link.IDENTITY,)) == arms[:4]


def test_candidate_arms_refusals():
    with pytest.raises(LayerRefusal, match="no identity"):
        candidate_arms((Link.LOG_C,))
    with pytest.raises(LayerRefusal, match="empty"):
        candidate_arms(())
    with pytest.raises(LayerRefusal, match="repeats"):
        candidate_arms((Link.IDENTITY, Link.IDENTITY))
    with pytest.raises(LayerRefusal, match="not R22 links"):
        candidate_arms(("identity",))


def test_lead_arms():
    pinned = ArmSpec(Link.LOG_C, Tool.CORRECTOR, G, True)
    assert lead_arms(pinned, 1, 12) == (pinned, trees_off_of(Link.LOG_C))
    last = lead_arms(pinned, 12, 12)
    assert last == (pinned, trees_off_of(Link.LOG_C), ArmSpec(Link.LOG_C, Tool.PLACEBO_CORRECTOR, G, False))
    with pytest.raises(LayerRefusal, match="at least 1"):
        lead_arms(pinned, 0, 12)
    with pytest.raises(LayerRefusal, match="beyond the longest lead"):
        lead_arms(pinned, 13, 12)
    with pytest.raises(LayerRefusal, match="not a tree arm"):
        lead_arms(trees_off_of(Link.IDENTITY), 1, 12)
    with pytest.raises(LayerRefusal, match="whole number"):
        lead_arms(pinned, 1.0, 12)


def test_check_arm_refuses_malformed_arms():
    with pytest.raises(LayerRefusal, match="never selectable"):
        check_arm(ArmSpec(Link.IDENTITY, Tool.PLACEBO_CORRECTOR, U, True))
    with pytest.raises(LayerRefusal, match="selectable"):
        check_arm(ArmSpec(Link.IDENTITY, Tool.PLAIN, U, False))
    with pytest.raises(LayerRefusal, match="unweighted"):
        check_arm(ArmSpec(Link.IDENTITY, Tool.TREES_OFF, G, False))
    with pytest.raises(LayerRefusal, match="Tool and Weighting"):
        check_arm(ArmSpec(Link.IDENTITY, "plain", U, True))
    with pytest.raises(LayerRefusal, match="must be an ArmSpec"):
        check_arm(("identity", "plain"))
    with pytest.raises(LayerRefusal, match="Enum member"):
        check_arm(ArmSpec("identity", Tool.PLAIN, U, True))

    class Harness(enum.Enum):
        LOG1P = "log1p"

    legacy = ArmSpec(Harness.LOG1P, Tool.PLAIN, U, True)
    assert check_arm(legacy) is legacy                                   # a harness link key
    with pytest.raises(LayerRefusal, match="R22's links only"):
        check_arm(legacy, engine_link_only=True)
    assert arm_name(legacy) == "log1p_plain_unweighted"


def test_table_kinds_and_derived_arms():
    assert table_kind(ArmSpec(Link.IDENTITY, Tool.PLAIN, U, True)) == "plain"
    assert table_kind(ArmSpec(Link.IDENTITY, Tool.CORRECTOR, G, True)) == "corrector"
    assert table_kind(placebo_of(ArmSpec(Link.IDENTITY, Tool.PLAIN, G, True))) == "placebo_corrector"
    assert table_kind(trees_off_of(Link.LOG_C)) is None
    with pytest.raises(LayerRefusal, match="only a tree arm"):
        placebo_of(trees_off_of(Link.IDENTITY))


def test_decision_candidates_are_the_link_sets_arms_or_a_declared_legacy_list():
    from treeroute.layer.arms import LegacyCandidates, decision_candidates

    arms = decision_candidates((Link.LOG_C, Link.IDENTITY), None)
    assert [arm_name(a) for a in arms] == [
        "identity_plain_unweighted", "identity_plain_gls", "identity_corrector_unweighted",
        "identity_corrector_gls", "log_c_plain_unweighted", "log_c_plain_gls",
        "log_c_corrector_unweighted", "log_c_corrector_gls", "identity_trees_off_unweighted",
        "log_c_trees_off_unweighted"]                                   # no placebo on the surface
    legacy = LegacyCandidates(arms=(ArmSpec(Link.IDENTITY, Tool.PLAIN, U, True),
                                    trees_off_of(Link.IDENTITY)), reason="a replay")
    assert decision_candidates(None, legacy) == legacy.arms
    with pytest.raises(LayerRefusal, match="either"):
        decision_candidates((Link.IDENTITY,), legacy)
    with pytest.raises(LayerRefusal, match="either"):
        decision_candidates(None, None)
    with pytest.raises(LayerRefusal, match="LegacyCandidates"):
        decision_candidates(None, legacy.arms)
