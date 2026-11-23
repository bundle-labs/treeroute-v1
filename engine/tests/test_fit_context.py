"""fit/context.py: FitContext, the only gateway to rows for fitted objects (plan 2.1 R11, R13; 5
G-FITCUT, G-DONOR; owner rulings D, E (L6 b)).

  - donor_rows: every picked group's BANK units only, valid labels at or before the context's cut
    (the vault's as-of rule), ascending grid order, X 0-filled float32; its row-key hash equals the
    vault's plan-time DonorLabels at the same cut and units; the bank recipe fits from it;
  - both cuts per lead, from derived.json; the GUARD context hands out the inner-cut bank's rows (L6);
  - unit_history (R2 season keys), router_rows (context NaN kept), check_inner_score_rows, for_lead;
  - the containers cannot be built or replaced outside FitContext (G-DONOR by structure);
  - refusals: a lead not in derived.json, picks that differ from derived.json's or name a unit
    outside its group, fold contexts (not built), Type-3 services (M4);
  - bank_plan: the nowcast's two banks under A7.inner_cut_bank_refit, one otherwise; fitctx_log rows.
"""

import dataclasses

import numpy as np
import pytest

from test_vault_world import (EXCLUDED, FIT_CUT_0, GROUPS, GUARD_CUT_0, MONTHS, PAST_STEP, TEST_FIRST,
                              make_context, make_world)
from treeroute import engine_constants as K
from treeroute.derive.shapes import CutKind
from treeroute.fit import context as C
from treeroute.fit.context import (BankPlanEntry, DonorRows, FitContext, FitContextRefusal, FitCtxLogRow,
                                   FoldPurpose, RouterRows, UnitHistory, bank_plan, log_records,
                                   season_keys_of)
from treeroute.split import UnitLists


def _lookup(world):
    return {(u, t): v for u, t, v in zip(world.units.tolist(), world.steps.tolist(), world.y.tolist())}


# ------------------------------------------------------------------------------------ donor_rows
def test_donor_rows_are_the_bank_units_rows_at_or_before_the_cut():
    w = make_world()
    ctx = make_context(w, 0, CutKind.FIT)
    d = ctx.donor_rows("bank")
    assert isinstance(d, DonorRows)
    assert d.cut == FIT_CUT_0 and d.cut_kind is CutKind.FIT and d.lead == 0 and d.fold is None
    assert d.groups == GROUPS
    bank = {u for g in GROUPS for u in w.picks.bank[g]}
    assert set(d.unit_ids.tolist()) == bank                     # the excluded group never appears
    assert d.times.max() <= FIT_CUT_0 and np.isfinite(d.y).all()
    assert np.all(np.diff(d.grid_rows) > 0)                     # ascending grid order
    lookup = _lookup(w)
    assert all(lookup[(u, t)] == v for u, t, v in zip(d.unit_ids.tolist(), d.times.tolist(), d.y.tolist()))
    n_valid = sum(1 for (u, t), v in lookup.items() if u in bank and t <= FIT_CUT_0 and np.isfinite(v))
    assert d.y.size == n_valid
    assert d.X.dtype == np.float32 and np.isfinite(d.X).all()
    raw = w.features.tree_features(d.grid_rows)
    assert np.array_equal(np.where(np.isnan(raw), 0.0, raw), d.X)   # R30 0-fill
    assert np.isnan(raw).any()
    assert list(d.group_of_row) == [u.rsplit("_", 1)[0] for u in d.unit_ids.tolist()]


@pytest.mark.parametrize("facts", ["in_month", "past_step"])
def test_donor_rows_hash_equals_the_vaults_plan_time_view(facts):
    from test_vault_world import IN_MONTH
    w = make_world(target_facts=IN_MONTH if facts == "in_month" else PAST_STEP)
    ctx = make_context(w, 0, CutKind.FIT)
    d = ctx.donor_rows("c")
    bank = tuple(u for g in GROUPS for u in w.picks.bank[g])
    view = w.labels.donor_labels(w.split, FIT_CUT_0, CutKind.FIT, 0, bank, "links")
    assert d.row_key_hash == view.row_key_hash
    assert d.y.tobytes() == view.y.tobytes()


def test_the_guard_context_hands_out_the_inner_cut_banks_rows():
    """L6 b: the inner decision's bank is refit at the INNER cut (lead 0's guard cut)."""
    w = make_world()
    guard = make_context(w, 0, CutKind.GUARD)
    d = guard.donor_rows("bank")
    assert guard.cut == GUARD_CUT_0 and d.cut == GUARD_CUT_0 and d.times.max() <= GUARD_CUT_0
    assert d.cut_kind is CutKind.GUARD
    fit = make_context(w, 0, CutKind.FIT).donor_rows("bank")
    assert d.y.size < fit.y.size


def test_donor_rows_restrict_to_bank_units_only():
    w = make_world()
    ctx = make_context(w, 0, CutKind.FIT)
    d = ctx.donor_rows("gls", ("g_a_u1", "g_b_u3"))
    assert set(d.unit_ids.tolist()) == {"g_a_u1", "g_b_u3"} and d.groups == ("g_a", "g_b")
    with pytest.raises(FitContextRefusal, match="not bank units"):
        ctx.donor_rows("gls", ("%s_u0" % EXCLUDED,))
    with pytest.raises(FitContextRefusal, match="purpose"):
        ctx.donor_rows("")


def test_the_bank_recipe_fits_from_donor_rows():
    from treeroute.fit.bank import fit_donor_bank

    w = make_world()
    d = make_context(w, 0, CutKind.GUARD).donor_rows("bank")
    bank = fit_donor_bank(d, K.SMOKE_TREES_PER_GROUP)
    assert bank.manifest.cut == GUARD_CUT_0 and bank.manifest.groups == GROUPS
    assert bank.manifest.max_label_time <= GUARD_CUT_0
    assert len(bank.trees) == len(GROUPS) * K.SMOKE_TREES_PER_GROUP


def test_the_containers_cannot_be_built_or_replaced_outside_fitcontext():
    w = make_world()
    d = make_context(w, 0, CutKind.FIT).donor_rows("bank")
    with pytest.raises(FitContextRefusal, match="handed out by FitContext only"):
        dataclasses.replace(d, y=d.y * 0.0)
    fields = {f.name: getattr(d, f.name) for f in dataclasses.fields(d)}
    with pytest.raises(FitContextRefusal, match="handed out by FitContext only"):
        DonorRows(**fields)
    with pytest.raises(FitContextRefusal, match="handed out by FitContext only"):
        UnitHistory(unit_id="u", group="g", cut=1, cut_kind=CutKind.FIT, lead=0, times=np.array([1]),
                    season_keys=np.array([1]), y=np.array([1.0]))
    with pytest.raises(FitContextRefusal, match="handed out by FitContext only"):
        RouterRows(cut=1, cut_kind=CutKind.FIT, lead=0, unit_ids=np.array(["u"]), times=np.array([1]),
                   row_positions=np.array([0]), y=np.array([1.0]), context=np.zeros((1, 1)))


# ------------------------------------------------------------------------------------ other hand-outs
def test_unit_history_carries_r2_season_keys():
    w = make_world()
    ctx = make_context(w, 1, CutKind.GUARD)
    h = ctx.unit_history("g_b_u2", "normal")
    assert isinstance(h, UnitHistory) and h.unit_id == "g_b_u2" and h.group == "g_b"
    assert h.cut == ctx.cut and h.times.max() <= ctx.cut and np.isfinite(h.y).all()
    assert np.array_equal(h.season_keys, (h.times - 1) % MONTHS + 1)
    with pytest.raises(FitContextRefusal, match="not a picked unit"):
        ctx.unit_history("%s_u0" % EXCLUDED, "normal")


def test_router_rows_keep_context_nan_and_grid_order():
    w = make_world()
    ctx = make_context(w, 0, CutKind.FIT)
    r = ctx.router_rows(("g_c_u1", "g_a_u0"), "router")
    assert isinstance(r, RouterRows)
    assert r.times.max() <= FIT_CUT_0 and np.all(np.diff(r.row_positions) > 0)
    assert r.unit_ids[0] == "g_a_u0" and r.unit_ids[-1] == "g_c_u1"
    assert r.context.shape == (r.y.size, 1) and np.isnan(r.context).any()
    with pytest.raises(FitContextRefusal, match="not picked"):
        ctx.router_rows(("%s_u1" % EXCLUDED,), "router")
    with pytest.raises(FitContextRefusal, match="at least one unit"):
        ctx.router_rows((), "router")


def test_check_inner_score_rows():
    w = make_world()
    guard = make_context(w, 3, CutKind.GUARD)
    guard.check_inner_score_rows(np.array([guard.cut, guard.cut + 5]))
    with pytest.raises(FitContextRefusal, match="before the guard cut"):
        guard.check_inner_score_rows(np.array([guard.cut - 1, guard.cut + 5]))
    with pytest.raises(FitContextRefusal, match="GUARD context"):
        make_context(w, 3, CutKind.FIT).check_inner_score_rows(np.array([TEST_FIRST]))


def test_both_cuts_per_lead_come_from_derived():
    w = make_world()
    ctx = make_context(w, 0, CutKind.FIT)
    three = ctx.for_lead(3, CutKind.FIT)
    assert three.lead == 3 and three.cut == FIT_CUT_0 - 2
    assert ctx.for_lead(3, "guard").cut == GUARD_CUT_0 - 2
    assert ctx.for_lead(1, CutKind.FIT).cut == FIT_CUT_0              # lead 1 shares the nowcast cut
    assert ctx.cut_pair().fit_cut == FIT_CUT_0 and ctx.cut_pair().guard_cut == GUARD_CUT_0
    with pytest.raises(FitContextRefusal, match="not in derived.json"):
        ctx.for_lead(6, CutKind.FIT)


# ------------------------------------------------------------------------------------ refusals
def test_picks_must_match_derived_and_the_grid():
    w = make_world()
    other = UnitLists(bank=dict(w.picks.bank), scored={g: w.picks.bank[g][1:3] for g in GROUPS})
    with pytest.raises(FitContextRefusal, match="differ from derived.json"):
        FitContext(w.derived, w.split, w.grid, w.labels, w.features, other, 0, CutKind.FIT)
    w2 = make_world(with_units_entry=False)
    wrong = UnitLists(bank={"g_a": ("g_b_u0",)}, scored={})
    with pytest.raises(FitContextRefusal, match="grid group"):
        FitContext(w2.derived, w2.split, w2.grid, w2.labels, w2.features, wrong, 0, CutKind.FIT)
    outside = UnitLists(bank={EXCLUDED: ("%s_u0" % EXCLUDED,)}, scored={})
    with pytest.raises(FitContextRefusal, match="outside the split"):
        FitContext(w2.derived, w2.split, w2.grid, w2.labels, w2.features, outside, 0, CutKind.FIT)
    scored_out = UnitLists(bank={"g_a": ("g_a_u0",)}, scored={"g_a": ("g_a_u1",)})
    with pytest.raises(FitContextRefusal, match="outside its bank list"):
        FitContext(w2.derived, w2.split, w2.grid, w2.labels, w2.features, scored_out, 0, CutKind.FIT)


def test_a_lead_not_in_derived_and_fold_contexts_are_refused():
    w = make_world()
    with pytest.raises(FitContextRefusal, match="not in derived.json"):
        make_context(w, 2, CutKind.FIT)
    with pytest.raises(FitContextRefusal, match="both fold and fold_purpose"):
        FitContext(w.derived, w.split, w.grid, w.labels, w.features, w.picks, 0, CutKind.FIT, fold=0)
    with pytest.raises(NotImplementedError, match="M8"):
        FitContext(w.derived, w.split, w.grid, w.labels, w.features, w.picks, 0, CutKind.GUARD, fold=0,
                   fold_purpose=FoldPurpose.DECISION_SURFACE)
    ctx = make_context(w)
    with pytest.raises(NotImplementedError, match="M8"):
        ctx.for_fold(0, FoldPurpose.DECISION_SURFACE)
    with pytest.raises(NotImplementedError, match="M4"):
        ctx.fit_bank()
    with pytest.raises(NotImplementedError, match="M4"):
        ctx.donor_fold_predict(np.array([0]))


def test_a_vault_on_another_grid_is_refused():
    w = make_world()
    from types import SimpleNamespace
    other_grid = SimpleNamespace(unit_ids=w.grid.unit_ids[:-1], group_of_unit=w.grid.group_of_unit[:-1],
                                 first_step=w.grid.first_step, n_steps=w.grid.n_steps)
    with pytest.raises(FitContextRefusal, match="another grid"):
        FitContext(w.derived, w.split, other_grid, w.labels, w.features, w.picks, 0, CutKind.FIT)


# ------------------------------------------------------------------------------------ plan and log
def test_bank_plan_follows_the_inner_cut_refit(monkeypatch):
    w = make_world()
    plan = bank_plan(w.derived)
    assert K.INNER_CUT_BANK_REFIT is True
    # lead 1 shares lead 0's fit cut (and lead 0's guard cut): flagged on both entries, never merged (its bank
    # reads the features at its own issue step, so it is another bank)
    assert plan[0] == BankPlanEntry(0, CutKind.FIT, FIT_CUT_0, ("test_pass",), (1,), "")
    assert plan[1] == BankPlanEntry(0, CutKind.GUARD, GUARD_CUT_0, ("decision_surface",), (1,), "")
    # owner ruling H2 (L6 b at every lead): each lead's fit-cut bank serves its test pass and a bank refit at
    # the lead's GUARD cut serves its guard surface; no lead entry carries a disclosure
    assert [(e.lead, e.cut_kind) for e in plan[2:]] == [(1, CutKind.FIT), (1, CutKind.GUARD), (3, CutKind.FIT),
                                                        (3, CutKind.GUARD)]
    assert plan[2] == BankPlanEntry(1, CutKind.FIT, FIT_CUT_0, ("test_pass",), (0,), "")
    assert plan[3] == BankPlanEntry(1, CutKind.GUARD, GUARD_CUT_0, ("guard_surface",), (0,), "")
    assert plan[4] == BankPlanEntry(3, CutKind.FIT, FIT_CUT_0 - 2, ("test_pass",), (), "")
    assert plan[5] == BankPlanEntry(3, CutKind.GUARD, GUARD_CUT_0 - 2, ("guard_surface",), (), "")
    assert all(e.disclosure == "" for e in plan)
    assert "L6 a" in C.L6_LEAD_GUARD_DISCLOSURE and "owner ruling pending" not in C.L6_LEAD_GUARD_DISCLOSURE
    assert len({(e.lead, e.cut_kind, e.cut) for e in plan}) == len(plan)
    monkeypatch.setattr(C.K, "INNER_CUT_BANK_REFIT", False)
    legacy = bank_plan(w.derived)
    assert legacy[0] == BankPlanEntry(0, CutKind.FIT, FIT_CUT_0, ("decision_surface", "test_pass"), (1,), "")
    assert len(legacy) == 3


def test_the_derived_view_is_read_only():
    w = make_world()
    ctx = make_context(w, 0, CutKind.GUARD)
    assert ctx.derived["R22"].value == w.derived["R22"].value
    with pytest.raises(TypeError):
        ctx.derived["R22"] = None


def test_every_hand_out_writes_a_log_row():
    w = make_world()
    ctx = make_context(w, 0, CutKind.GUARD)
    d = ctx.donor_rows("bank")
    ctx.unit_history("g_a_u0", "normal")
    ctx.router_rows(("g_a_u0",), "scaler")
    rows = ctx.log()
    assert [r.object_kind for r in rows] == ["donor_rows", "unit_history", "router_rows"]
    assert [r.purpose for r in rows] == ["bank", "normal", "scaler"]
    assert all(isinstance(r, FitCtxLogRow) and r.cut == GUARD_CUT_0 and r.max_label_time <= GUARD_CUT_0
               for r in rows)
    assert rows[0].row_key_hash == d.row_key_hash and rows[0].n_rows == d.y.size
    recs = log_records(rows)
    assert recs[0]["cut_kind"] == "guard" and recs[0]["fold"] is None
    methods = [r["method"] for r in w.labels.read_log()]
    assert methods[-3:] == ["donor_rows", "unit_history", "router_rows"]


def test_season_keys_of_follow_r2():
    from treeroute.derive.shapes import SeasonKeyKind, SeasonKeySpec

    steps = np.array([MONTHS * 2000 + m for m in range(1, 13)] + [MONTHS * 2001 + 1])
    keys = season_keys_of(steps, SeasonKeySpec(SeasonKeyKind.MONTH_OF_YEAR, MONTHS))
    assert keys.tolist() == list(range(1, 13)) + [1]
    annual = season_keys_of(np.array([1999, 2000, 2001]), SeasonKeySpec(SeasonKeyKind.CONSTANT, 1))
    assert annual.tolist() == [1, 1, 1]
    with pytest.raises(NotImplementedError, match="M8"):
        season_keys_of(steps, SeasonKeySpec(SeasonKeyKind.EVENT_MONTH, None))
