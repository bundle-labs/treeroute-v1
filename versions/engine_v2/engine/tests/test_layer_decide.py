"""layer/decide.py: R26 penalty search, the N2 guard, R27 adoption with the decline rule, R29's pin,
G-PLUMB and decide() (plan 2.4 R24-R29; owner rulings A: D64, D65, D86; D67; 5 G-LOCK, G-FITCUT).

  - penalty_search keeps the best grid point by MAE, the FIRST on a tie, and flags edge picks; the
    MAE is the source's float(mean(|y - p|)) bit for bit;
  - n2_eligible is strict; select_adoption ranks eligible tree arms by MAE (first in candidate order on
    a tie), declines to the arithmetic normal when none beats its own link's trees-off, records the
    best tree arm either way, and holds EVERY candidate in surface_mae;
  - a harness link key enters only through a declared LegacyCandidates order (probe: a mixed,
    out-of-order list is refused);
  - planted faults: a placebo selected (refused at select_adoption and decide); a test label reaching
    decide() (the vault refuses a test-window row, a relabelled or forged surface is refused, a
    TestLabels object is refused); a partial candidate list (probe: 1 of 8 arms); GLS arms missing
    without a declared reason; surface rows before the inner guard's cut (G-FITCUT probe); a surface
    from another vault; labels read after the fit cut;
  - forecast_adoption pins the nowcast's arm (its best tree arm when it declined), declines a lead
    whose pinned arm fails the guard, and flags the placebo at the longest lead;
  - decide() on synthetic surfaces equals a transcription of the shipped rank / N2 / pick rules; its
    record keys every row-level prediction by unit and step and registers the adoption document with
    the vault.
"""

import dataclasses
import enum
import json
import weakref

import numpy as np
import pytest

from test_vault_world import (FIT_CUT_0, GROUPS, GUARD_CUT_0, LEGAL, MONTHS, TEST_FIRST,
                              decide_world, make_context, make_surface, make_world, surface_arms,
                              surface_keys)
from treeroute.derive.derived import make_derived
from treeroute.derive.shapes import CutKind
from treeroute.derive.shapes import GridPoint as DeriveGridPoint
from treeroute.derive.shapes import Link
from treeroute.fit.context import FitContext, FitContextRefusal
from treeroute.labels.vault import TestLabels, VaultRefusal
from treeroute.layer.arms import (ArmSpec, LayerRefusal, LegacyCandidates, Tool, Weighting, arm_name,
                                  placebo_of, trees_off_of)
from treeroute.layer.decide import (Adoption, DecisionSurface, GuardStatus, LeadAdoption, PenaltyPick,
                                    SurfaceArm, adoption_document, candidate_key, candidate_table_sha256,
                                    check_adoption, check_plumbing, decide, edge_axes, forecast_adoption,
                                    lead_adoption_document, n2_eligible, penalty_search, pin_of,
                                    select_adoption, surface_mae, surface_sha256)
from treeroute.route.kinds import GridPoint, per_unit_grid
from treeroute.timing.shapes import CutPair

U, G = Weighting.UNWEIGHTED, Weighting.GLS
GRID = per_unit_grid(True)


def arm(link, tool, weighting=U):
    return ArmSpec(link, tool, weighting, tool in (Tool.PLAIN, Tool.CORRECTOR))


def pick(a, point, mae):
    return PenaltyPick(arm=a, point=point, mae=mae, mae_by_point={point: mae}, edge=False)


class Legacy(enum.Enum):                                           # a harness link key, as the replay uses
    LOG1P = "log1p"


def legacy_list(links=(Link.IDENTITY, Legacy.LOG1P, Link.LOG_C)):
    arms = [arm(link, tool) for link in links for tool in (Tool.PLAIN, Tool.CORRECTOR)]
    return LegacyCandidates(arms=tuple(arms + [trees_off_of(link) for link in links]),
                            reason="replay of a shipped link R22 does not have")


# ------------------------------------------------------------------------------------ penalty search
def test_penalty_search_keeps_the_first_best_point_and_the_source_mae():
    rng = np.random.RandomState(11)
    y = rng.gamma(2.0, 5.0, size=300)
    P = y[:, None] + rng.normal(0.0, 1.0, size=(300, len(GRID))) * np.linspace(3.0, 0.5, len(GRID))
    P[:, 20] = P[:, 17]                           # a tie with an earlier point
    p = penalty_search(arm(Link.IDENTITY, Tool.PLAIN), P, y, GRID)
    maes = [float(np.mean(np.abs(y - P[:, k]))) for k in range(len(GRID))]
    k = int(np.argmin(maes))                      # argmin returns the first minimum
    assert p.point == GRID[k] and p.mae == maes[k]
    assert list(p.mae_by_point) == list(GRID) and list(p.mae_by_point.values()) == maes
    # tie: the same values at two points; the earlier wins
    Q = np.repeat(y[:, None] + 1.0, len(GRID), axis=1)
    assert penalty_search(arm(Link.IDENTITY, Tool.PLAIN), Q, y, GRID).point == GRID[0]


def test_edge_picks_are_flagged_never_extended():
    assert edge_axes(GridPoint(3.0, 1.0), GRID) == {"level": None, "ratio": "top"}
    assert edge_axes(GridPoint(0.1, 0.25), GRID) == {"level": "bottom", "ratio": None}
    assert edge_axes(GridPoint(1.0, 0.5), GRID) == {"level": None, "ratio": None}
    y = np.linspace(1.0, 2.0, 50)
    P = np.full((50, len(GRID)), 9.0)
    P[:, GRID.index(GridPoint(100.0, 0.5))] = y
    p = penalty_search(arm(Link.IDENTITY, Tool.PLAIN), P, y, GRID)
    assert p.point == GridPoint(100.0, 0.5) and p.edge is True
    region = tuple(GridPoint(v, None) for v in (0.1, 0.3, 1.0))
    assert edge_axes(GridPoint(0.3, None), region) == {"level": None, "ratio": None}
    # a grid of derive's GridPoint records is read into the router's
    q = penalty_search(arm(Link.IDENTITY, Tool.PLAIN), P[:, :3], y,
                       tuple(DeriveGridPoint(g.level, g.ratio) for g in GRID[:3]))
    assert isinstance(q.point, GridPoint)


def test_penalty_search_refusals():
    y = np.ones(10)
    P = np.ones((10, len(GRID)))
    a = arm(Link.IDENTITY, Tool.PLAIN)
    with pytest.raises(LayerRefusal, match="placebo"):
        penalty_search(placebo_of(a), P, y, GRID)
    with pytest.raises(LayerRefusal, match="no grid"):
        penalty_search(trees_off_of(Link.IDENTITY), y, y, GRID)
    with pytest.raises(LayerRefusal, match="grid is empty"):
        penalty_search(a, P, y, ())
    with pytest.raises(LayerRefusal, match="shape"):
        penalty_search(a, P[:9], y, GRID)
    bad = P.copy()
    bad[3, 4] = np.nan
    with pytest.raises(LayerRefusal, match="D67"):
        penalty_search(a, bad, y, GRID)
    with pytest.raises(LayerRefusal, match="repeats"):
        penalty_search(a, P[:, :2], y, (GRID[0], GRID[0]))
    off = penalty_search(trees_off_of(Link.IDENTITY), y[:, None] * 2, y, ())
    assert off.point is None and off.mae == 1.0 and off.mae_by_point == {}


# ------------------------------------------------------------------------------------ N2 and R27
def test_n2_is_strict():
    assert n2_eligible(1.0, 1.5) and not n2_eligible(1.5, 1.5) and not n2_eligible(2.0, 1.5)
    with pytest.raises(LayerRefusal, match="finite"):
        n2_eligible(float("nan"), 1.0)


def test_select_adoption_ranks_eligible_arms_and_records_every_candidate():
    a1, a2 = arm(Link.IDENTITY, Tool.PLAIN), arm(Link.IDENTITY, Tool.CORRECTOR)
    b1, b2 = arm(Link.LOG_C, Tool.PLAIN), arm(Link.LOG_C, Tool.CORRECTOR)
    picks = (pick(a1, GRID[3], 3.0), pick(a2, GRID[4], 2.2), pick(b1, GRID[5], 2.1), pick(b2, GRID[6], 2.5))
    # log_c's own trees-off is 2.0: log_c arms are not eligible; identity's is 3.5
    ad = select_adoption(picks, {Link.IDENTITY: 3.5, Link.LOG_C: 2.0}, {"predict_zero_mae": 9.0})
    assert ad.adopted == a2 and ad.penalty == GRID[4] and not ad.declined
    assert ad.eligible == (a1, a2)
    assert ad.best_tree_arm == a2 and ad.best_tree_penalty == GRID[4]
    assert ad.surface_mae[candidate_key(b1, GRID[5])] == 2.1
    assert ad.surface_mae[candidate_key(trees_off_of(Link.LOG_C), None)] == 2.0
    assert ad.beside == {"predict_zero_mae": 9.0}
    check_adoption(ad)
    # every grid point of every pick is a candidate (the approved shape: "every candidate")
    full = penalty_search(a1, np.tile(np.arange(len(GRID), dtype=float), (5, 1)), np.zeros(5), GRID)
    ad2 = select_adoption((full,), {Link.IDENTITY: 99.0}, {})
    assert len(ad2.surface_mae) == len(GRID) + 1
    assert ad2.surface_mae[candidate_key(a1, GRID[7])] == 7.0


def test_candidate_keys():
    a = arm(Link.LOG_C, Tool.CORRECTOR, G)
    assert candidate_key(a, GridPoint(3.0, 1.0)) == "log_c_corrector_gls@level=3.0,ratio=1.0"
    assert candidate_key(trees_off_of(Link.IDENTITY), None) == "identity_trees_off_unweighted"
    assert candidate_key(a, GridPoint(0.3, None)) == "log_c_corrector_gls@level=0.3,ratio=None"


def test_select_adoption_declines_to_the_arithmetic_normal():
    a1, b1 = arm(Link.IDENTITY, Tool.PLAIN), arm(Link.LOG_C, Tool.PLAIN)
    picks = (pick(a1, GRID[3], 3.0), pick(b1, GRID[5], 2.1))
    ad = select_adoption(picks, {Link.IDENTITY: 3.0, Link.LOG_C: 2.0}, {})
    assert ad.declined and ad.adopted is None and ad.penalty is None and ad.eligible == ()
    assert ad.best_tree_arm == b1 and ad.best_tree_penalty == GRID[5]   # the lowest MAE, for R29's pin
    assert pin_of(ad) == (b1, GRID[5])


def test_a_tie_goes_to_the_first_arm_in_candidate_order():
    a1, a2 = arm(Link.IDENTITY, Tool.PLAIN), arm(Link.IDENTITY, Tool.PLAIN, G)
    b1 = arm(Link.LOG_C, Tool.PLAIN)
    picks = (pick(a1, GRID[1], 2.0), pick(a2, GRID[2], 2.0), pick(b1, GRID[3], 2.0))
    ad = select_adoption(picks, {Link.IDENTITY: 3.0, Link.LOG_C: 3.0}, {})
    assert ad.adopted == a1
    with pytest.raises(LayerRefusal, match="candidate order"):
        select_adoption((picks[2], picks[0]), {Link.IDENTITY: 3.0, Link.LOG_C: 3.0}, {})


def test_probe_a_harness_link_key_needs_a_declared_legacy_order():
    """Probe (review): a mixed, out-of-order list with a non-R22 key was accepted and the log_c
    corrector won the tie. Now the key is refused without a declared order, and the declared order's
    tie rule is enforced."""
    ident, logc_corr = arm(Link.IDENTITY, Tool.PLAIN), arm(Link.LOG_C, Tool.CORRECTOR)
    harness = arm(Legacy.LOG1P, Tool.PLAIN)
    off = {Link.IDENTITY: 5.0, Link.LOG_C: 5.0, Legacy.LOG1P: 5.0}
    mixed = (pick(logc_corr, GRID[0], 1.0), pick(harness, GRID[0], 1.0), pick(ident, GRID[0], 1.0))
    with pytest.raises(LayerRefusal, match="not R22's links"):
        select_adoption(mixed, off, {})
    order = legacy_list()
    with pytest.raises(LayerRefusal, match="candidate order"):
        select_adoption(mixed, off, {}, order=order)
    in_order = (pick(ident, GRID[0], 1.0), pick(harness, GRID[0], 1.0), pick(logc_corr, GRID[0], 1.0))
    ad = select_adoption(in_order, off, {}, order=order)
    assert ad.adopted == ident                                      # the declared first arm wins the tie
    with pytest.raises(LayerRefusal, match="LegacyCandidates"):
        select_adoption(in_order, off, {}, order=tuple(order.arms))
    with pytest.raises(LayerRefusal, match="not an R22 link and not declared"):
        select_adoption((pick(ident, GRID[0], 1.0),), {Link.IDENTITY: 2.0, Legacy.LOG1P: 2.0}, {})


def test_legacy_candidates_refusals():
    base = legacy_list()
    with pytest.raises(LayerRefusal, match="reason"):
        LegacyCandidates(arms=base.arms, reason=" ")
    with pytest.raises(LayerRefusal, match="placebo"):
        LegacyCandidates(arms=base.arms + (placebo_of(base.arms[0]),), reason="r")
    with pytest.raises(LayerRefusal, match="after a trees-off"):
        LegacyCandidates(arms=(trees_off_of(Link.IDENTITY), arm(Link.IDENTITY, Tool.PLAIN)), reason="r")
    with pytest.raises(LayerRefusal, match="no trees-off"):
        LegacyCandidates(arms=(arm(Legacy.LOG1P, Tool.PLAIN), trees_off_of(Link.IDENTITY)), reason="r")
    with pytest.raises(LayerRefusal, match="decline target"):
        LegacyCandidates(arms=(arm(Legacy.LOG1P, Tool.PLAIN), trees_off_of(Legacy.LOG1P)), reason="r")
    with pytest.raises(LayerRefusal, match="repeats"):
        LegacyCandidates(arms=base.arms + base.arms[:1], reason="r")
    assert base.link_keys() == ("identity", "log1p", "log_c")


def test_planted_a_placebo_or_trees_off_selected_is_refused():
    a1 = arm(Link.IDENTITY, Tool.PLAIN)
    placebo = placebo_of(a1)
    with pytest.raises(LayerRefusal, match="never selectable"):
        select_adoption((pick(a1, GRID[0], 3.0), pick(placebo, GRID[0], 1.0)), {Link.IDENTITY: 4.0}, {})
    with pytest.raises(LayerRefusal, match="never selectable"):
        select_adoption((pick(trees_off_of(Link.IDENTITY), GRID[0], 1.0),), {Link.IDENTITY: 4.0}, {})


def test_select_adoption_refusals():
    a1, b1 = arm(Link.IDENTITY, Tool.PLAIN), arm(Link.LOG_C, Tool.PLAIN)
    with pytest.raises(LayerRefusal, match="no tree arm"):
        select_adoption((), {Link.IDENTITY: 1.0}, {})
    with pytest.raises(LayerRefusal, match="identity-link trees-off"):
        select_adoption((pick(b1, GRID[0], 1.0),), {Link.LOG_C: 2.0}, {})
    with pytest.raises(LayerRefusal, match="no trees-off MAE for link"):
        select_adoption((pick(a1, GRID[0], 1.0), pick(b1, GRID[0], 1.0)), {Link.IDENTITY: 2.0}, {})
    with pytest.raises(LayerRefusal, match="twice"):
        select_adoption((pick(a1, GRID[0], 1.0), pick(a1, GRID[1], 1.0)), {Link.IDENTITY: 2.0}, {})
    with pytest.raises(LayerRefusal, match="no grid point"):
        select_adoption((PenaltyPick(a1, None, 1.0, {}, False),), {Link.IDENTITY: 2.0}, {})
    with pytest.raises(LayerRefusal, match="number"):
        select_adoption((pick(a1, GRID[0], 1.0),), {Link.IDENTITY: 2.0}, {"x": "y"})
    # a pick penalty_search could not have made: not its grid's best, or its point unscored
    worse = PenaltyPick(a1, GRID[0], 2.0, {GRID[0]: 2.0, GRID[1]: 1.0}, False)
    with pytest.raises(LayerRefusal, match="not the best point"):
        select_adoption((worse,), {Link.IDENTITY: 3.0}, {})
    stray = PenaltyPick(a1, GRID[0], 2.0, {GRID[1]: 2.0}, False)
    with pytest.raises(LayerRefusal, match="not among its scored"):
        select_adoption((stray,), {Link.IDENTITY: 3.0}, {})


def test_check_adoption_refuses_inconsistent_records():
    a1 = arm(Link.IDENTITY, Tool.PLAIN)
    good = select_adoption((pick(a1, GRID[0], 1.0),), {Link.IDENTITY: 2.0}, {})
    fields = dict(adopted=good.adopted, penalty=good.penalty, declined=False, best_tree_arm=a1,
                  best_tree_penalty=GRID[0], eligible=(a1,), surface_mae=good.surface_mae, beside={})
    with pytest.raises(LayerRefusal):
        check_adoption(Adoption(**dict(fields, declined=True)))
    with pytest.raises(LayerRefusal, match="not eligible"):
        check_adoption(Adoption(**dict(fields, eligible=())))
    with pytest.raises(LayerRefusal, match="best tree arm"):
        check_adoption(Adoption(**dict(fields, best_tree_penalty=GRID[1])))
    with pytest.raises(LayerRefusal, match="every candidate"):
        check_adoption(Adoption(**dict(fields, surface_mae={"identity_trees_off_unweighted": 2.0})))


# ------------------------------------------------------------------------------------ R29
def test_forecast_adoption_pins_and_guards():
    a1, b1 = arm(Link.IDENTITY, Tool.PLAIN), arm(Link.LOG_C, Tool.CORRECTOR, G)
    now = select_adoption((pick(a1, GRID[2], 3.0), pick(b1, GRID[9], 2.0)),
                          {Link.IDENTITY: 3.5, Link.LOG_C: 2.5}, {})
    la = forecast_adoption(now, 3, 1.9, 2.0, 12)
    assert la == LeadAdoption(lead=3, pinned=b1, penalty=GRID[9], guard_passed=True, adopted=b1,
                              placebo_built=False)
    fail = forecast_adoption(now, 12, 2.0, 2.0, 12)                # equal is not better (N2 strict)
    assert fail.guard_passed is False and fail.adopted is None and fail.placebo_built is True
    with pytest.raises(LayerRefusal, match="at least 1"):
        forecast_adoption(now, 0, 1.0, 2.0, 12)
    with pytest.raises(LayerRefusal, match="beyond the longest"):
        forecast_adoption(now, 13, 1.0, 2.0, 12)
    doc = lead_adoption_document(la, "a" * 64)
    assert doc["pinned"]["weighting"] == "gls" and doc["penalty"] == {"level": GRID[9].level,
                                                                      "ratio": GRID[9].ratio}


# ------------------------------------------------------------------------------------ G-PLUMB
def test_check_plumbing():
    x = np.linspace(0, 1, 20)
    ok = check_plumbing(x, x + 1e-9, x, x, None, None, x, x.copy(), 1e-6)
    assert ok.status is GuardStatus.PASS and ok.details["weighted_equal_weights_equals_unweighted"] == {"checked": False}
    bad = check_plumbing(x, x + 1e-3, x, x, x, x + 1.0, None, None, 1e-6)
    assert bad.status is GuardStatus.BLOCK
    assert bad.columns == ("trees_off_equals_normal", "weighted_equal_weights_equals_unweighted")
    with pytest.raises(LayerRefusal, match="one side is missing"):
        check_plumbing(x, x, x, x, x, None, None, None, 1e-6)
    with pytest.raises(LayerRefusal, match="shapes"):
        check_plumbing(x, x[:5], x, x, None, None, None, None, 1e-6)
    with pytest.raises(LayerRefusal, match="positive"):
        check_plumbing(x, x, x, x, None, None, None, None, 0.0)


# ------------------------------------------------------------------------------------ decide()
def _setup(**kw):
    w = make_world(**kw)
    return w, make_surface(w), make_context(w, 0, CutKind.GUARD)


def test_decide_clips_every_arm_adopts_and_keys_every_row():
    w, s, guard = _setup()
    arms = surface_arms(s.y, shift=-30.0)                          # many predictions below 0
    rec = decide(s, arms, GRID, LEGAL, guard)
    name = arm_name(arms[0].arm)
    assert rec.clip[name].n_below > 0 and rec.clip[name].n_rows == s.y.size * len(GRID)
    clipped = np.maximum(arms[0].pre_clip, 0.0)
    want = [float(np.mean(np.abs(s.y - clipped[:, k]))) for k in range(len(GRID))]
    assert [r.mae for r in rec.candidates if r.arm == name] == want   # R28 before any score
    assert rec.predictions[name].tobytes() == clipped.tobytes()        # row-level, for the run folder
    assert not rec.predictions[name].flags.writeable
    assert set(rec.predictions) == {arm_name(a.arm) for a in arms}
    assert len(rec.candidates) == 8 * len(GRID) + 2
    assert rec.unit_ids.tolist() == s.unit_ids.tolist() and np.array_equal(rec.times, s.times)
    assert rec.surface_sha256 == s.sha256 and rec.label_cut == FIT_CUT_0 and rec.guard_cut == GUARD_CUT_0
    assert rec.adoption.beside["predict_zero_mae"] == float(np.mean(np.abs(s.y)))
    assert all(("corr2:" + arm_name(a.arm)) in rec.adoption.beside for a in arms)
    # every candidate row is in the adoption, keyed; the table's hash is recorded
    assert len(rec.adoption.surface_mae) == len(rec.candidates)
    for r in rec.candidates:
        key = r.arm if r.level is None else "%s@level=%r,ratio=%r" % (r.arm, r.level, r.ratio)
        assert rec.adoption.surface_mae[key] == r.mae
    assert rec.candidate_table_sha256 == candidate_table_sha256(rec.candidates)
    assert rec.candidate_order[:4] == ("identity_plain_unweighted", "identity_plain_gls",
                                       "identity_corrector_unweighted", "identity_corrector_gls")
    assert rec.missing_arms == () and rec.legacy_reason is None
    table = rec.table()
    assert table[0]["arm"] == name and table[-1]["level"] is None
    doc = adoption_document(rec.adoption, rec)
    assert doc["pass"] == "nowcast" and doc["decision"]["surface_sha256"] == s.sha256
    assert doc["decision"]["legal_range"] == [0.0, "inf"] and doc["decision"]["n_candidates"] == len(rec.candidates)
    registered = w.labels.decision_documents()
    assert registered and json.dumps(registered[-1], sort_keys=True) == json.dumps(
        json.loads(json.dumps(doc)), sort_keys=True)


def test_decide_ranks_arms_given_in_any_order():
    w, s, guard = _setup()
    arms = surface_arms(s.y, seed=9)
    rec = decide(s, list(reversed(arms)), GRID, LEGAL, guard)
    ref = decide(s, arms, GRID, LEGAL, guard)
    assert [arm_name(p.arm) for p in rec.picks] == [arm_name(p.arm) for p in ref.picks]
    assert rec.adoption == ref.adoption


def test_planted_a_test_label_reaching_decide_is_refused():
    """Probe (review): test-window labels relabelled with inner-window times went through decide().
    Now the surface's labels come only from the vault, keyed by (unit, step)."""
    w, s, guard = _setup()
    arms = surface_arms(s.y)
    units, times = surface_keys(w)
    # the vault refuses a test-window row, a cut inside the test window, a row after the cut
    with pytest.raises(VaultRefusal, match="test window"):
        w.labels.decision_surface(np.append(units, units[0]), np.append(times, TEST_FIRST), FIT_CUT_0)
    with pytest.raises(VaultRefusal, match="test window"):
        w.labels.decision_surface(units, times, TEST_FIRST)
    with pytest.raises(VaultRefusal, match="dated after the cut"):
        w.labels.decision_surface(units, times, GUARD_CUT_0 + 12)
    # a surface built by hand, or replaced, is refused: labels never come from the caller
    tl_y = s.y[::-1].copy()
    with pytest.raises(LayerRefusal, match="issued by the label vault only"):
        DecisionSurface(unit_ids=s.unit_ids, times=s.times, y=tl_y, label_cut=FIT_CUT_0,
                        test_first_time=TEST_FIRST, sha256=s.sha256)
    with pytest.raises(LayerRefusal, match="issued by the label vault only"):
        dataclasses.replace(s, y=tl_y)
    # the issued arrays are read-only, and cannot be made writable
    with pytest.raises(ValueError):
        s.y[0] = 1.0
    with pytest.raises(ValueError):
        s.y.setflags(write=True)
    # forgeries that bypass the constructor are refused by decide()
    forged = object.__new__(DecisionSurface)
    for f in dataclasses.fields(DecisionSurface):
        object.__setattr__(forged, f.name, getattr(s, f.name))
    with pytest.raises(LayerRefusal, match="not issued by a live label vault"):
        decide(forged, arms, GRID, LEGAL, guard)
    object.__setattr__(forged, "_issuer", weakref.ref(w.labels))
    object.__setattr__(forged, "y", tl_y)                          # relabelled, old hash
    with pytest.raises(LayerRefusal, match="SHA-256 mismatch"):
        decide(forged, arms, GRID, LEGAL, guard)
    object.__setattr__(forged, "sha256", surface_sha256(s.unit_ids, s.times, tl_y, FIT_CUT_0, TEST_FIRST))
    with pytest.raises(LayerRefusal, match="not issued by a live label vault"):
        decide(forged, arms, GRID, LEGAL, guard)                   # a hash the vault never issued
    # a TestLabels object anywhere
    tl = TestLabels(lead=0, adoption_sha256="a" * 64, unit_ids=s.unit_ids, times=s.times, y=s.y)
    with pytest.raises(LayerRefusal, match="TestLabels"):
        decide(s, arms + [tl], GRID, LEGAL, guard)
    with pytest.raises(LayerRefusal, match="TestLabels"):
        decide(s, [SurfaceArm(arms[0].arm, tl)] + arms[1:], GRID, LEGAL, guard)


def test_planted_a_placebo_on_the_decision_surface_is_refused():
    w, s, guard = _setup()
    arms = surface_arms(s.y)
    placebo = SurfaceArm(placebo_of(arms[1].arm), arms[1].pre_clip)
    with pytest.raises(LayerRefusal, match="never on the decision surface"):
        decide(s, arms + [placebo], GRID, LEGAL, guard)


def test_probe_a_partial_candidate_list_is_refused():
    """Probe (review): 1 of the 8 selectable arms was adopted with no refusal."""
    w, s, guard = _setup()
    arms = surface_arms(s.y)
    one = [arms[0]] + [a for a in arms if a.arm.tool is Tool.TREES_OFF]
    with pytest.raises(LayerRefusal, match="lacks candidate arm"):
        decide(s, one, GRID, LEGAL, guard)
    no_off = [a for a in arms if a.arm != trees_off_of(Link.LOG_C)]
    with pytest.raises(LayerRefusal, match="log_c_trees_off_unweighted"):
        decide(s, no_off, GRID, LEGAL, guard)
    no_decline = [a for a in arms if a.arm != trees_off_of(Link.IDENTITY)]
    with pytest.raises(LayerRefusal, match="identity_trees_off_unweighted"):
        decide(s, no_decline, GRID, LEGAL, guard)
    extra = arms + [SurfaceArm(arm(Link.ARCSINE, Tool.PLAIN), arms[0].pre_clip)]
    with pytest.raises(LayerRefusal, match="not candidates"):
        decide(s, extra, GRID, LEGAL, guard)


def test_gls_arms_missing_only_under_a_declared_reason_which_is_recorded():
    w, s, guard = _setup()
    unweighted = surface_arms(s.y, gls=False)
    with pytest.raises(LayerRefusal, match="gls_absent_reason"):
        decide(s, unweighted, GRID, LEGAL, guard)
    reason = "no weighted grid solve exists yet (route/solve)"
    rec = decide(s, unweighted, GRID, LEGAL, guard, gls_absent_reason=reason)
    assert rec.missing_arms == ("identity_plain_gls", "identity_corrector_gls", "log_c_plain_gls",
                                "log_c_corrector_gls")
    assert rec.gls_absent_reason == reason
    doc = w.labels.decision_documents()[-1]
    assert doc["decision"]["gls_absent_reason"] == reason and len(doc["decision"]["missing_arms"]) == 4
    with pytest.raises(LayerRefusal, match="every GLS arm is on the surface"):
        decide(s, surface_arms(s.y), GRID, LEGAL, guard, gls_absent_reason=reason)
    with pytest.raises(LayerRefusal, match="non-empty"):
        decide(s, unweighted, GRID, LEGAL, guard, gls_absent_reason="  ")
    no_plain = [a for a in unweighted if a.arm != arm(Link.IDENTITY, Tool.PLAIN)]
    with pytest.raises(LayerRefusal, match="lacks candidate arm"):
        decide(s, no_plain, GRID, LEGAL, guard, gls_absent_reason=reason)   # only GLS arms may be missing


def test_probe_rows_before_the_inner_guard_cut_are_refused():
    """Probe (review): surface rows 24 steps before the guard cut were accepted (G-FITCUT)."""
    w = make_world()
    guard = make_context(w, 0, CutKind.GUARD)
    early = make_surface(w, after=GUARD_CUT_0 - 24)
    with pytest.raises(FitContextRefusal, match="before the guard cut"):
        decide(early, surface_arms(early.y), GRID, LEGAL, guard)


def test_decide_refuses_a_wrong_context_range_or_derived():
    w, s, guard = _setup()
    arms = surface_arms(s.y)
    with pytest.raises(LayerRefusal, match="GUARD context"):
        decide(s, arms, GRID, LEGAL, make_context(w, 0, CutKind.FIT))
    with pytest.raises(LayerRefusal, match="GUARD context"):
        decide(s, arms, GRID, LEGAL, make_context(w, 3, CutKind.GUARD))
    with pytest.raises(LayerRefusal, match="GUARD FitContext"):
        decide(s, arms, GRID, LEGAL, object())
    with pytest.raises(LayerRefusal, match="differs from the one R22 recorded"):
        decide(s, arms, GRID, (0.0, 1000.0), guard)
    # a derived.json without R22
    no_r22 = {k: v for k, v in w.derived.items() if k != "R22"}
    ctx = FitContext(no_r22, w.split, w.grid, w.labels, w.features, w.picks, 0, CutKind.GUARD)
    with pytest.raises(LayerRefusal, match="no R22 entry"):
        decide(s, arms, GRID, LEGAL, ctx)
    # labels read after lead 0's fit cut (a derived.json whose fit cut is a year earlier)
    early_fit = dict(w.derived)
    early_fit["R11"] = make_derived("R11", {0: CutPair(lead=0, lead_unit="steps", fit_cut=FIT_CUT_0 - MONTHS,
                                                       guard_cut=GUARD_CUT_0)}, {"source": "test"})
    ctx = FitContext(early_fit, w.split, w.grid, w.labels, w.features, w.picks, 0, CutKind.GUARD)
    with pytest.raises(LayerRefusal, match="after lead 0's fit cut"):
        decide(s, arms, GRID, LEGAL, ctx)


def test_a_surface_from_another_vault_is_refused_unless_legacy():
    w, s, guard = _setup()
    other = make_world()
    s2 = make_surface(other)
    with pytest.raises(LayerRefusal, match="different label vaults"):
        decide(s2, surface_arms(s2.y), GRID, LEGAL, guard)
    # a declared legacy replay may keep two vaults (the shipped layout kept donors and test regions
    # in separate frames); the decision is registered with the surface's vault
    legacy = legacy_list()
    arms = [SurfaceArm(a, np.tile(s2.y[:, None] + 1.0, (1, len(GRID))) if a.selectable else s2.y + 2.0)
            for a in legacy.arms]
    rec = decide(s2, arms, GRID, LEGAL, guard, legacy=legacy)
    assert not rec.adoption.declined
    assert other.labels.decision_documents() and not w.labels.decision_documents()


def test_decide_refusals():
    w, s, guard = _setup()
    arms = surface_arms(s.y)
    with pytest.raises(LayerRefusal, match="twice"):
        decide(s, arms + [arms[0]], GRID, LEGAL, guard)
    missing = [SurfaceArm(a.arm, np.where(np.arange(a.pre_clip.size).reshape(a.pre_clip.shape) == 7,
                                          np.nan, a.pre_clip)) if i == 0 else a for i, a in enumerate(arms)]
    with pytest.raises(LayerRefusal, match="missing"):
        decide(s, missing, GRID, LEGAL, guard)
    with pytest.raises(LayerRefusal, match="DecisionSurface"):
        decide(s.y, arms, GRID, LEGAL, guard)


# ------------------------------------------------------------------------------------ the shipped rules
def _shipped(y, surfaces, offs, grid):
    """A transcription of pm25_adaptation.py's rank (strict '<' over the grid), rank_single, the N2 guard
    (inner MAE < own normal's, strict) and pick = min(eligible, key=MAE) else the arithmetic normal;
    tree_pick = pick, or min over every tree arm when declined."""
    inner = {}
    for name, P in surfaces.items():
        best_k, best = None, None
        for k in range(len(grid)):
            m = float(np.mean(np.abs(y - P[:, k])))
            if best is None or m < best:
                best_k, best = k, m
        inner[name] = (best, grid[best_k])
    for name, p in offs.items():
        inner[name] = (float(np.mean(np.abs(y - p))), None)
    normal_of = {name: name.split("|")[0] + "|off" for name in surfaces}
    eligible = [k for k in normal_of if inner[k][0] < inner[normal_of[k]][0]]
    pick_ = min(eligible, key=lambda k: inner[k][0]) if eligible else "identity|off"
    tree_pick = pick_ if pick_ in normal_of else min(normal_of, key=lambda k: inner[k][0])
    return pick_, tree_pick, inner[tree_pick][1], eligible, inner


@pytest.mark.parametrize("seed,shift,off_noise", [(1, 0.0, 3.0), (2, 0.0, 0.5), (3, 2.0, 1.0),
                                                  (4, 0.0, 9.0), (5, -1.0, 0.1)])
def test_decide_equals_the_shipped_rules(seed, shift, off_noise):
    w, s, guard = _setup()
    rng = np.random.RandomState(seed)
    y = s.y
    n = y.size
    legacy = legacy_list()
    arms, surfaces, offs = [], {}, {}
    for a in legacy.selectable():
        P = y[:, None] + shift + rng.normal(0.0, 1.0, size=(n, len(GRID))) * rng.uniform(0.5, 5.0, len(GRID))
        P = np.abs(P)
        arms.append(SurfaceArm(a, P))
        surfaces["%s|%s" % (a.link.value, a.tool.value)] = P
    for a in legacy.arms[len(legacy.selectable()):]:
        p = np.abs(y + rng.normal(0.0, off_noise, size=n))
        arms.append(SurfaceArm(a, p))
        offs["%s|off" % a.link.value] = p
    rec = decide(s, arms, GRID, (-float("inf"), float("inf")), guard, legacy=legacy)
    pick_, tree_pick, pen, eligible, inner = _shipped(y, surfaces, offs, GRID)
    a = rec.adoption
    name = lambda x: "%s|%s" % (x.link.value, x.tool.value)          # noqa: E731
    if pick_ == "identity|off":
        assert a.declined and a.adopted is None
    else:
        assert not a.declined and name(a.adopted) == pick_ and a.penalty == inner[pick_][1]
    assert name(a.best_tree_arm) == tree_pick and a.best_tree_penalty == pen
    assert [name(x) for x in a.eligible] == eligible
    for p in rec.picks:
        assert (p.mae, p.point) == inner[name(p.arm)]
    for p in rec.trees_off:
        assert p.mae == inner["%s|off" % p.arm.link.value][0]
    assert rec.legacy_reason == legacy.reason and rec.legacy_link_keys == ("identity", "log1p", "log_c")
    doc = w.labels.decision_documents()[-1]
    assert doc["decision"]["legacy"] == {"reason": legacy.reason, "link_keys": ["identity", "log1p", "log_c"]}


def test_a_harness_key_without_a_legacy_declaration_is_refused_by_decide():
    w, s, guard = _setup()
    arms = surface_arms(s.y) + [SurfaceArm(arm(Legacy.LOG1P, Tool.PLAIN), np.tile(s.y[:, None], (1, len(GRID))))]
    with pytest.raises(LayerRefusal, match="not candidates"):
        decide(s, arms, GRID, LEGAL, guard)


def test_surface_mae_is_the_source_expression():
    y = np.array([1.0, 2.0, 3.5])
    p = np.array([1.5, 1.0, 3.5])
    assert surface_mae(y, p) == float(np.mean(np.abs(y - p)))
    with pytest.raises(LayerRefusal, match="no rows"):
        surface_mae(np.array([]), np.array([]))
    with pytest.raises(LayerRefusal, match="rows"):
        surface_mae(y, p[:2])


def test_decide_world_helper_records_both_outcomes():
    w = make_world()
    assert decide_world(w).adoption.eligible
    rec = decide_world(w, declined=True)
    assert rec.adoption.declined and len(w.labels.decision_documents()) == 2
    assert set(GROUPS) == {u.rsplit("_", 1)[0] for u in rec.unit_ids.tolist()}
