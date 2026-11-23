"""labels/vault.py: LabelView's reads (plan 4.2; R3, R11, R12, R17, R18; G-LOCK, G-FITCUT, G-DONOR).

  - the constructor takes the labels in and refuses a target that is not the grid's census;
  - validity hands out flags only; donor_labels equals derive's plan-time reader on the same data
    (rows, order, labels, row-key hash) for both scopes;
  - asof applies R11's label rule: at or before the cut, own window ended by the cut's last day, so a
    cut step's own label is dropped when the target window reaches past its step;
  - asof_rows reads exactly k steps before each row's newest readable step, NaN before the grid; each
    read logs its purpose, the test-window positions it served and the passes locked at that moment
    (probe: 40 test-window labels were served before any lock with only max_label_time logged);
  - decision_surface: the only source of decide()'s surface, the as-of labels at a cut for given rows,
    read-only and content-hashed; refusals counted by reason;
  - donor_labels with the R18 lists refuses a unit that is not a bank unit;
  - no read at a cut inside the test window; every read is logged.
The locks are in test_vault_lock.py.
"""

from types import SimpleNamespace

import numpy as np
import pytest

from test_vault_world import (CADENCE, EXCLUDED, FIRST_STEP, FIT_CUT_0, GROUPS, GUARD_CUT_0, IN_MONTH,
                              LAST_STEP, PAST_STEP, TEST_FIRST, census, make_world, step_of,
                              window_last_days)
from treeroute.derive.orchestrate import _PlanLabels
from treeroute.derive.shapes import CutKind, DonorLabels
from treeroute.io.steps import build_dense_grid
from treeroute.labels.vault import LabelSlice, LabelView, VaultRefusal, row_key_hash


def _target(units, groups, y):
    return SimpleNamespace(unit_ids=units, group_ids=groups, time_columns={}, y=y)


# ------------------------------------------------------------------------------------ constructor
def test_constructor_refuses_events_and_a_missing_cadence():
    units, groups, steps, y = census()
    grid = build_dense_grid(units, groups, steps, (FIRST_STEP, LAST_STEP))
    wend = window_last_days(steps, IN_MONTH)
    with pytest.raises(NotImplementedError, match="M8"):
        LabelView(None, _target(units, groups, y), steps, TEST_FIRST, wend, None, cadence=CADENCE)
    with pytest.raises(VaultRefusal, match="cadence"):
        LabelView(grid, _target(units, groups, y), steps, TEST_FIRST, wend, None)


def test_constructor_refuses_a_target_that_is_not_the_grids_census():
    units, groups, steps, y = census()
    grid = build_dense_grid(units, groups, steps, (FIRST_STEP, LAST_STEP))
    wend = window_last_days(steps, IN_MONTH)
    # a unit off the grid
    bad_units = units.copy()
    bad_units[0] = "nowhere_u0"
    with pytest.raises(VaultRefusal, match="not on the grid"):
        LabelView(grid, _target(bad_units, groups, y), steps, TEST_FIRST, wend, None, cadence=CADENCE)
    # a group that differs from the grid's
    bad_groups = groups.copy()
    bad_groups[0] = "g_b"
    with pytest.raises(VaultRefusal, match="group"):
        LabelView(grid, _target(units, bad_groups, y), steps, TEST_FIRST, wend, None, cadence=CADENCE)
    # a repeated (unit, step)
    rep = steps.copy()
    rep[1] = rep[0]
    with pytest.raises(VaultRefusal, match="repeat"):
        LabelView(grid, _target(units, groups, y), rep, TEST_FIRST, wend, None, cadence=CADENCE)
    # a missing row (the census has a hole)
    keep = np.arange(1, len(units))
    with pytest.raises(VaultRefusal, match="census"):
        LabelView(grid, _target(units[keep], groups[keep], y[keep]), steps[keep], TEST_FIRST, wend[keep],
                  None, cadence=CADENCE)
    # an infinite label
    inf = y.copy()
    inf[3] = np.inf
    with pytest.raises(VaultRefusal, match="infinite"):
        LabelView(grid, _target(units, groups, inf), steps, TEST_FIRST, wend, None, cadence=CADENCE)


def test_constructor_refuses_a_run_folder_that_does_not_exist(tmp_path):
    with pytest.raises(VaultRefusal, match="does not exist"):
        make_world(run_folder=tmp_path / "missing")


# ------------------------------------------------------------------------------------ validity
def test_validity_hands_out_flags_never_values():
    w = make_world()
    first, last = step_of(2003, 1), step_of(2010, 12)
    units, times, valid = w.labels.validity(first, last)
    assert valid.dtype == np.bool_ and len(units) == len(times) == len(valid)
    assert times.min() == first and times.max() == last          # the test window may be read (R3)
    lookup = {(u, s): v for u, s, v in zip(w.units.tolist(), w.steps.tolist(), w.y.tolist())}
    want = np.array([np.isfinite(lookup[(u, s)]) for u, s in zip(units.tolist(), times.tolist())])
    assert np.array_equal(valid, want)
    assert not (valid.all())                                     # some labels are invalid
    with pytest.raises(VaultRefusal, match="empty"):
        w.labels.validity(last, first)
    assert w.labels.read_log()[-1]["method"] == "validity"


# ------------------------------------------------------------------------------------ donor_labels
@pytest.mark.parametrize("facts", [IN_MONTH, PAST_STEP], ids=["in_month", "past_step"])
@pytest.mark.parametrize("picked", [True, False], ids=["picked", "all_units"])
def test_donor_labels_equal_the_plan_time_reader(facts, picked):
    w = make_world(target_facts=facts)
    plan = _PlanLabels(w.units, w.groups, w.steps, w.y, CADENCE, facts)
    plan.set_test_first_step(TEST_FIRST)
    bank = tuple(u for g in GROUPS for u in w.picks.bank[g][:3]) if picked else None
    mine = w.labels.donor_labels(w.split, FIT_CUT_0, CutKind.FIT, 0, bank, "links")
    ref = plan.donor_labels(GROUPS, FIT_CUT_0, CutKind.FIT, 0, bank, "links")
    assert isinstance(mine, DonorLabels)
    assert mine.groups == GROUPS and mine.unit_scope == ref.unit_scope
    assert mine.unit_ids.tolist() == ref.unit_ids.tolist()
    assert np.array_equal(mine.times, ref.times)
    assert mine.y.tobytes() == ref.y.tobytes()
    assert list(mine.group_of_row) == list(ref.group_of_row)
    assert mine.row_key_hash == ref.row_key_hash
    assert EXCLUDED not in set(mine.group_of_row.tolist())
    assert np.isfinite(mine.y).all() and mine.times.max() <= FIT_CUT_0


def test_donor_labels_refuses_a_test_window_cut_and_foreign_units():
    w = make_world()
    with pytest.raises(VaultRefusal, match="test window"):
        w.labels.donor_labels(w.split, TEST_FIRST, CutKind.FIT, 0, None, "links")
    with pytest.raises(VaultRefusal, match="not units of the donor groups"):
        w.labels.donor_labels(w.split, FIT_CUT_0, CutKind.FIT, 0, ("%s_u0" % EXCLUDED,), "links")
    with pytest.raises(VaultRefusal, match="not units of the donor groups"):
        w.labels.donor_labels(w.split, FIT_CUT_0, CutKind.FIT, 0, ("nowhere",), "links")
    with pytest.raises(VaultRefusal, match="purpose"):
        w.labels.donor_labels(w.split, FIT_CUT_0, CutKind.FIT, 0, None, "")
    with pytest.raises(VaultRefusal, match="negative"):
        w.labels.donor_labels(w.split, FIT_CUT_0, CutKind.FIT, -1, None, "links")


def test_donor_labels_feed_the_derive_rules():
    from treeroute.derive import rules as R

    w = make_world()
    bank = tuple(u for g in GROUPS for u in w.picks.bank[g])
    view = w.labels.donor_labels(w.split, FIT_CUT_0, CutKind.FIT, 0, bank, "links")
    links = R.derive_r22_links((0.0, float("inf")), view)
    entry = R.derive_r23_c_for_cut(view)
    assert links.input_hashes["donor_row_key_hash"] == view.row_key_hash
    assert entry.value == R.c_from_donor_y(view.y)[0]


# ------------------------------------------------------------------------------------ asof
def test_asof_serves_valid_labels_at_or_before_the_cut():
    w = make_world()
    s = w.labels.asof(GUARD_CUT_0)
    assert isinstance(s, LabelSlice) and s.cut == GUARD_CUT_0
    assert s.times.max() == GUARD_CUT_0 and np.isfinite(s.y).all()
    lookup = {(u, t): v for u, t, v in zip(w.units.tolist(), w.steps.tolist(), w.y.tolist())}
    assert all(lookup[(u, t)] == v for u, t, v in zip(s.unit_ids.tolist(), s.times.tolist(), s.y.tolist()))
    n_valid = sum(1 for (u, t), v in lookup.items() if t <= GUARD_CUT_0 and np.isfinite(v))
    assert len(s.y) == n_valid                    # every group, the excluded one too: the vault is raw
    rec = w.labels.read_log()[-1]
    assert rec["method"] == "asof" and rec["cut"] == GUARD_CUT_0 and rec["max_label_time"] == GUARD_CUT_0


def test_asof_drops_labels_whose_own_window_reaches_past_the_cut():
    w = make_world(target_facts=PAST_STEP)
    s = w.labels.asof(GUARD_CUT_0)
    assert s.times.max() == GUARD_CUT_0 - 1       # the cut step's own window ends after the cut


def test_asof_refuses_a_cut_inside_the_test_window():
    w = make_world()
    with pytest.raises(VaultRefusal, match="test window"):
        w.labels.asof(TEST_FIRST)
    with pytest.raises(VaultRefusal, match="test window"):
        w.labels.asof(LAST_STEP)


# ------------------------------------------------------------------------------------ asof_rows
def test_asof_rows_reads_exactly_k_steps_back_in_the_same_unit():
    w = make_world()
    grid = w.grid
    rows = np.array([0, 1, 5, 5, 7])
    newest = np.array([FIRST_STEP + 3, LAST_STEP - 1, TEST_FIRST + 2, FIRST_STEP, FIRST_STEP + 40])
    lookup = {(u, t): v for u, t, v in zip(w.units.tolist(), w.steps.tolist(), w.y.tolist())}
    for k in (0, 1, 3):
        got = w.labels.asof_rows(rows, newest, k)
        for r, n, g in zip(rows.tolist(), newest.tolist(), got.tolist()):
            step = n - k
            if step < FIRST_STEP:
                assert np.isnan(g)                 # before the grid: absent
            else:
                want = lookup[(grid.unit_ids[r], step)]
                assert (np.isnan(want) and np.isnan(g)) or want == g
    # D54 (a): a test row's read inside the test window, before its issue step, is served; the log
    # records the newest step served (never after a row's newest readable step)
    assert w.labels.read_log()[-1]["max_label_time"] <= int((newest - 3).max())
    got = w.labels.asof_rows(np.array([5]), np.array([TEST_FIRST + 2]), 0)
    assert got[0] == lookup[(grid.unit_ids[5], TEST_FIRST + 2)]


def test_asof_rows_refusals():
    w = make_world()
    with pytest.raises(VaultRefusal, match="negative"):
        w.labels.asof_rows(np.array([0]), np.array([FIRST_STEP + 5]), -1)
    with pytest.raises(VaultRefusal, match="off the grid"):
        w.labels.asof_rows(np.array([10 ** 6]), np.array([FIRST_STEP + 5]), 0)
    with pytest.raises(VaultRefusal, match="after the grid"):
        w.labels.asof_rows(np.array([0]), np.array([LAST_STEP + 1]), 0)
    with pytest.raises(VaultRefusal, match="differ in length"):
        w.labels.asof_rows(np.array([0, 1]), np.array([FIRST_STEP + 5]), 0)


def test_asof_rows_serves_the_history_block():
    """The engine's history block reads its labels only through asof_rows (G-HIST)."""
    from treeroute.io.apply import history_block
    from treeroute.derive.shapes import HistorySpec
    from treeroute.derive.shapes import CutKind as CK
    from test_vault_world import make_context

    w = make_world()
    ctx = make_context(w, 0, CK.FIT)
    units = w.picks.scored["g_a"]
    hist = {u: ctx.unit_history(u, "history_fill") for u in units}
    rows = np.array([w.grid.unit_ids.index(u) for u in units for _ in range(3)])
    t = np.array([TEST_FIRST, TEST_FIRST + 1, TEST_FIRST + 5] * len(units))
    spec = HistorySpec(columns=("hist_last_1",), last_values=1, trailing_steps=(12,), trailing_days=(),
                       all_history_mean=False, start_offset_steps=0, dropped_duplicates=())
    from treeroute.fit.context import season_keys_of
    keys = season_keys_of(t, w.derived["R2"].value)
    block, filled = history_block(w.grid, spec, t, rows, 0, w.labels, hist, keys, 1.0)
    lookup = {(u, s): v for u, s, v in zip(w.units.tolist(), w.steps.tolist(), w.y.tolist())}
    for i, (r, s) in enumerate(zip(rows.tolist(), t.tolist())):
        want = lookup[(w.grid.unit_ids[r], s - 1)]
        if np.isfinite(want):
            assert block[i, 0] == np.float32(want)


def test_probe_pre_lock_test_window_reads_are_logged_and_totalled():
    """Probe (review): 40 test-window labels were served with no pass locked, and the log showed only
    max_label_time. Each read now logs its test-window rows and the locks at that moment."""
    w = make_world()
    rows = np.arange(40) % len(w.grid.unit_ids)
    newest = np.full(40, TEST_FIRST + 5)
    w.labels.asof_rows(rows, newest, 0, purpose="persistence")
    rec = w.labels.read_log()[-1]
    assert rec["method"] == "asof_rows" and rec["purpose"] == "persistence"
    assert rec["test_window_rows"] == 40 and rec["locked_passes"] == [] and rec["opened_passes"] == []
    w.labels.asof_rows(rows[:3], np.full(3, TEST_FIRST - 4), 1)          # before the test window
    assert w.labels.read_log()[-1]["test_window_rows"] == 0 and w.labels.read_log()[-1]["purpose"] == "rows"
    total = w.labels.test_window_reads()
    assert total["reads"] == 1 and total["rows"] == 40 and total["rows_before_any_lock"] == 40
    with pytest.raises(VaultRefusal, match="purpose"):
        w.labels.asof_rows(rows, newest, 0, purpose="")


def test_decision_surface_is_the_as_of_view_of_the_given_rows():
    w = make_world()
    lookup = {(u, t): v for u, t, v in zip(w.units.tolist(), w.steps.tolist(), w.y.tolist())}
    s = w.labels.asof(FIT_CUT_0)
    pick = np.flatnonzero(s.times > GUARD_CUT_0)[::-7]                 # any order: kept as given
    units, times = s.unit_ids[pick], s.times[pick]
    surf = w.labels.decision_surface(units, times, FIT_CUT_0)
    assert surf.unit_ids.tolist() == units.tolist() and surf.times.tolist() == times.tolist()
    assert surf.y.tolist() == [lookup[(u, t)] for u, t in zip(units.tolist(), times.tolist())]
    assert surf.label_cut == FIT_CUT_0 and surf.test_first_time == TEST_FIRST
    from treeroute.layer.decide import surface_sha256
    assert surf.sha256 == surface_sha256(units, times, surf.y, FIT_CUT_0, TEST_FIRST)
    assert w.labels._issued_surface(surf.sha256)
    for arr in (surf.unit_ids, surf.times, surf.y):
        assert not arr.flags.writeable
        with pytest.raises(ValueError):
            arr.setflags(write=True)
    rec = w.labels.read_log()[-1]
    assert rec["method"] == "decision_surface" and rec["surface_sha256"] == surf.sha256
    assert rec["rows"] == units.size and rec["max_label_time"] == int(times.max())


def test_decision_surface_refusals():
    w = make_world()
    s = w.labels.asof(FIT_CUT_0)
    units, times = s.unit_ids[:20], s.times[:20]
    with pytest.raises(VaultRefusal, match="not on the grid"):
        w.labels.decision_surface(np.append(units, "nowhere"), np.append(times, times[0]), FIT_CUT_0)
    with pytest.raises(VaultRefusal, match="outside the grid"):
        w.labels.decision_surface(units[:1], np.array([LAST_STEP + 1]), FIT_CUT_0)
    with pytest.raises(VaultRefusal, match="repeat"):
        w.labels.decision_surface(np.append(units, units[0]), np.append(times, times[0]), FIT_CUT_0)
    with pytest.raises(VaultRefusal, match="no row"):
        w.labels.decision_surface(units[:0], times[:0], FIT_CUT_0)
    with pytest.raises(VaultRefusal, match="one unit id per step"):
        w.labels.decision_surface(units[:3], times[:2], FIT_CUT_0)
    nan_at = [(u, t) for u, t, v in zip(w.units.tolist(), w.steps.tolist(), w.y.tolist())
              if np.isnan(v) and GUARD_CUT_0 < t <= FIT_CUT_0][0]
    with pytest.raises(VaultRefusal, match="1 invalid"):
        w.labels.decision_surface(np.array([nan_at[0]], dtype=object), np.array([nan_at[1]]), FIT_CUT_0)
    with pytest.raises(VaultRefusal, match="1 dated after the cut .1 of them in the test window"):
        w.labels.decision_surface(np.array([units[0]], dtype=object), np.array([TEST_FIRST]), FIT_CUT_0)
    with pytest.raises(VaultRefusal, match="test window"):
        w.labels.decision_surface(units, times, TEST_FIRST)
    past = make_world(target_facts=PAST_STEP)
    with pytest.raises(VaultRefusal, match="1 whose own label window ends after"):
        past.labels.decision_surface(np.array([units[0]], dtype=object), np.array([GUARD_CUT_0]), GUARD_CUT_0)


def test_donor_labels_with_the_r18_lists_refuses_a_non_bank_unit():
    """LORO addendum: the refusal is 'a unit that is not a bank unit' (the vault checks it when the R18
    lists are given; flagged signature gap otherwise)."""
    from treeroute.split import UnitLists

    w = make_world()
    small = UnitLists(bank={g: w.picks.bank[g][:2] for g in GROUPS}, scored={g: w.picks.bank[g][:1] for g in GROUPS})
    ok = w.labels.donor_labels(w.split, FIT_CUT_0, CutKind.FIT, 0, ("g_a_u0", "g_b_u1"), "links", picks=small)
    assert set(ok.unit_ids.tolist()) == {"g_a_u0", "g_b_u1"}
    assert w.labels.read_log()[-1]["bank_unit_check"] is True
    with pytest.raises(VaultRefusal, match="not bank units"):
        w.labels.donor_labels(w.split, FIT_CUT_0, CutKind.FIT, 0, ("g_a_u3",), "links", picks=small)
    with pytest.raises(VaultRefusal, match="all-units view"):
        w.labels.donor_labels(w.split, FIT_CUT_0, CutKind.FIT, 0, None, "links", picks=small)
    with pytest.raises(VaultRefusal, match="UnitLists"):
        w.labels.donor_labels(w.split, FIT_CUT_0, CutKind.FIT, 0, ("g_a_u0",), "links", picks=object())
    w.labels.donor_labels(w.split, FIT_CUT_0, CutKind.FIT, 0, ("g_a_u3",), "links")
    assert w.labels.read_log()[-1]["bank_unit_check"] is False


def test_row_key_hash_depends_on_units_and_times():
    a = row_key_hash(np.array(["u1", "u2"], dtype=object), np.array([1, 2]))
    b = row_key_hash(np.array(["u1", "u2"], dtype=object), np.array([1, 3]))
    c = row_key_hash(np.array(["u1", "u3"], dtype=object), np.array([1, 2]))
    assert len({a, b, c}) == 3
