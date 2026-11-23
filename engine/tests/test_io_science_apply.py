"""io science: apply_lags (R8), apply_verdicts (plan 1.4), apply_freezes (R9, D32, D33), the
R17 history block (D83, D84, R-D, the F1 fallback) and features_at_issue_step (R8, R11). Synthetic
frames and a fake label vault, every branch. The F1 leak proofs are in test_io_science_history.py."""

from enum import Enum
from types import SimpleNamespace as NS

import numpy as np
import pandas as pd
import pytest

from treeroute.errors import RefusedError
from treeroute.io.apply import (ColumnSets, apply_freezes, apply_lags, apply_verdicts, event_history_block,
                                features_at_issue_step, history_block, history_column_names)
from treeroute.io.steps import DenseGrid

MONTHLY = NS(kind="regular", length=1, unit="month")
ANNUAL = NS(kind="regular", length=1, unit="year")


def lag(column, steps, cadence=MONTHLY):
    return NS(column=column, steps=steps, column_cadence=cadence, floor_reason=None)


# ---------------------------------------------------------------------------------------------------
# apply_lags
def _panel():
    # unit 0: steps 1..5 with a gap at 4; unit 1: steps 1..3; rows shuffled
    u = np.array([0, 0, 0, 0, 1, 1, 1])
    s = np.array([1, 2, 3, 5, 1, 2, 3])
    perm = np.array([6, 3, 0, 4, 2, 5, 1])
    u, s = u[perm], s[perm]
    frame = pd.DataFrame({"x": (u * 100 + s).astype(np.int64), "f": (u * 10 + s).astype(np.float32),
                          "o": ["u%d_s%d" % (a, b) for a, b in zip(u, s)], "keep": np.arange(7.0)},
                         index=np.arange(7) * 3)
    return frame, u, s


def _expect(frame, u, s, column, k):
    lookup = {(a, b): v for a, b, v in zip(u, s, frame[column])}
    return [lookup.get((a, b - k)) for a, b in zip(u, s)]


def lags_for(frame, cadence=MONTHLY, **steps):
    """A Lag for every frame column: the given steps, 0 for the rest (same-step columns)."""
    return {c: lag(c, steps.get(c, 0), cadence) for c in frame.columns}


def test_lags_move_values_back_within_the_unit_and_leave_gaps_missing():
    frame, u, s = _panel()
    before = frame.copy()
    out = apply_lags(frame, u, s, lags_for(frame, x=1, f=2, o=1), MONTHLY)
    for column, k in (("x", 1), ("f", 2), ("o", 1)):
        want = _expect(frame, u, s, column, k)
        got = out[column].tolist()
        for w, g in zip(want, got):
            assert (w is None and (g is None or (isinstance(g, float) and np.isnan(g)))) or w == g
    assert out["x"].dtype == np.float64 and out["f"].dtype == np.float32
    assert out["keep"].equals(frame["keep"]) and out.index.equals(frame.index)
    pd.testing.assert_frame_equal(frame, before)
    row = np.flatnonzero((u == 0) & (s == 5))[0]
    assert np.isnan(out["x"].iloc[row])  # step 4 is a gap: never the step-3 value


def test_lag_zero_leaves_the_column_unchanged():
    frame, u, s = _panel()
    out = apply_lags(frame, u, s, lags_for(frame), MONTHLY)
    assert out["x"].dtype == np.int64 and out["x"].equals(frame["x"])
    pd.testing.assert_frame_equal(out, frame)


def test_a_frame_column_without_a_lag_is_refused_never_served_unlagged():
    # an index with a lag of 3 (R-A) left out of the mapping must not serve its same-step value
    frame = pd.DataFrame({"idx": [1.0, 2.0, 3.0, 4.0], "x": [5.0, 6.0, 7.0, 8.0]})
    u, s = np.zeros(4, dtype=int), np.arange(1, 5)
    with pytest.raises(RefusedError, match="have no lag") as info:
        apply_lags(frame, u, s, {"x": lag("x", 1)}, MONTHLY)
    assert "'idx'" in str(info.value) and "Lag of 0 steps" in str(info.value)
    out = apply_lags(frame, u, s, {"x": lag("x", 1), "idx": lag("idx", 3)}, MONTHLY)
    assert np.isnan(out["idx"].iloc[:3]).all() and out["idx"].iloc[3] == 1.0
    # key columns stay out of the frame: they arrive as unit_codes and steps
    with pytest.raises(RefusedError, match="have no lag"):
        apply_lags(frame.assign(unit=0), u, s, {"x": lag("x", 1), "idx": lag("idx", 3)}, MONTHLY)


def test_the_same_composite_cadence_in_store_and_proposed_form_is_one_cadence():
    store_form = NS(kind="composite_of_year", length=16, unit="day", composites_per_year=23)
    proposed = NS(kind="composite_of_year", length=None, unit=None, composites_per_year=23,
                  composite_days=16)
    frame = pd.DataFrame({"x": [1.0, 2.0]})
    u, s = np.array([0, 0]), np.array([2010 * 23 + 1, 2010 * 23 + 2])
    for column_cadence, target in ((store_form, proposed), (proposed, store_form)):
        out = apply_lags(frame, u, s, {"x": lag("x", 1, column_cadence)}, target)
        assert np.isnan(out["x"].iloc[0]) and out["x"].iloc[1] == 1.0
    other = NS(kind="composite_of_year", composites_per_year=46, composite_days=8)
    with pytest.raises(RefusedError, match="join_coarser_column"):
        apply_lags(frame, u, s, {"x": lag("x", 1, other)}, proposed)


def test_lag_refusals():
    frame, u, s = _panel()

    def with_(**over):
        out = lags_for(frame)
        out.update(over)
        return out

    with pytest.raises(RefusedError, match="does not hold"):
        apply_lags(frame, u, s, with_(zz=lag("zz", 1)), MONTHLY)
    with pytest.raises(RefusedError, match="is the lag of"):
        apply_lags(frame, u, s, with_(x=lag("f", 1)), MONTHLY)
    with pytest.raises(RefusedError, match="negative"):
        apply_lags(frame, u, s, with_(x=lag("x", -1)), MONTHLY)
    with pytest.raises(RefusedError, match="integer"):
        apply_lags(frame, u, s, with_(x=lag("x", 1.0)), MONTHLY)
    with pytest.raises(RefusedError, match="join_coarser_column"):
        apply_lags(frame, u, s, with_(x=lag("x", 1, ANNUAL)), MONTHLY)
    with pytest.raises(RefusedError, match="not a Lag"):
        apply_lags(frame, u, s, with_(x=1), MONTHLY)
    with pytest.raises(RefusedError, match="repeat"):
        apply_lags(frame, np.zeros(7, dtype=int), np.ones(7, dtype=int), with_(x=lag("x", 1)), MONTHLY)
    with pytest.raises(RefusedError, match="frame rows"):
        apply_lags(frame, u[:-1], s, with_(x=lag("x", 1)), MONTHLY)


# ---------------------------------------------------------------------------------------------------
# apply_verdicts
class V(Enum):  # stands in for the proposed common.Verdict
    KEEP = "keep"


def verdict(v):
    return NS(verdict=v)


def test_verdicts_route_columns_by_role_and_mark_freeze_and_listed():
    cols = ("d1", "ctx", "sup", "e1", "fz", "ku", "w", "b", "cnd", "tgt", "twin", "ext", "strat")
    verdicts = {"d1": verdict(V.KEEP), "ctx": verdict("keep"), "sup": verdict("keep"),
                "e1": verdict("keep_unreviewed"), "fz": verdict("freeze"), "ku": verdict("keep"),
                "w": verdict("watch"), "b": verdict("ban"), "cnd": verdict("conditional"),
                "tgt": verdict("ban"), "twin": verdict("ban"), "ext": verdict("keep"),
                "strat": verdict("watch")}
    roles = {"d1": "driver", "ctx": "router_context", "sup": "support", "e1": "engineered",
             "fz": "driver", "ku": "driver", "w": "router_context", "b": "driver", "cnd": "driver",
             "tgt": "target", "twin": "target_twin", "ext": "external_product",
             "strat": "report_stratum", "unit_key": "key_unit"}
    sets = apply_verdicts(cols, verdicts, roles)
    assert sets == ColumnSets(tree_features=("d1", "e1", "fz", "ku"), router_context=("ctx", "w"),
                              report_only=("sup", "ext", "strat"), frozen=("fz",),
                              listed_in_reports=("e1", "w", "strat"))


def test_verdict_refusals():
    base_roles = {"a": "driver", "b": "driver"}
    with pytest.raises(RefusedError, match="closed world"):
        apply_verdicts(("a", "b"), {"a": verdict("keep")}, base_roles)
    with pytest.raises(RefusedError, match="closed world"):
        apply_verdicts(("a",), {"a": verdict("keep"), "gone": verdict("keep")}, base_roles)
    with pytest.raises(RefusedError, match="without a role"):
        apply_verdicts(("a", "c"), {"a": verdict("keep"), "c": verdict("keep")}, base_roles)
    with pytest.raises(RefusedError, match="must be ban"):
        apply_verdicts(("y",), {"y": verdict("keep")}, {"y": "target"})
    with pytest.raises(RefusedError, match="must be ban"):
        apply_verdicts(("y2",), {"y2": verdict("freeze")}, {"y2": "target_twin"})
    with pytest.raises(RefusedError, match="G-KEYS"):
        apply_verdicts(("k",), {"k": verdict("keep")}, {"k": "key_time"})
    with pytest.raises(RefusedError, match="unknown verdict"):
        apply_verdicts(("a",), {"a": verdict("lag")}, base_roles)
    with pytest.raises(RefusedError, match="unknown role"):
        apply_verdicts(("a",), {"a": verdict("keep")}, {"a": "mask"})
    with pytest.raises(RefusedError, match="more than once"):
        apply_verdicts(("a", "a"), {"a": verdict("keep")}, base_roles)
    with pytest.raises(RefusedError, match="no 'verdict'"):
        apply_verdicts(("a",), {"a": "keep"}, base_roles)
    with pytest.raises(RefusedError, match="not one string"):
        apply_verdicts("a", {"a": verdict("keep")}, base_roles)


# ---------------------------------------------------------------------------------------------------
# apply_freezes
def test_every_row_takes_the_units_epoch_value_and_a_unit_without_one_gets_nan():
    units = np.array([0, 0, 0, 1, 1, 2, 2])
    epoch_of_row = np.array([100, 200, 300, 100, 200, 300, 300])
    frame = pd.DataFrame({"z": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 6.0], "other": list("abcdefg")},
                         index=list("ABCDEFG"))
    before = frame.copy()
    out = apply_freezes(frame, units, {"z": epoch_of_row}, {"z": 200})
    assert out["z"].tolist()[:5] == [2.0, 2.0, 2.0, 5.0, 5.0]  # earlier rows too (D32)
    assert np.isnan(out["z"].iloc[5:]).all()  # unit 2 has no value at the epoch (D33)
    assert out["other"].equals(frame["other"]) and out.index.equals(frame.index)
    pd.testing.assert_frame_equal(frame, before)


def test_freeze_with_integer_values_missing_epochs_and_nan_values():
    units = np.array([0, 0, 1, 1])
    epochs_f = np.array([5.0, np.nan, 5.0, 5.0])
    frame = pd.DataFrame({"z": np.array([7, 8, 9, 9], dtype=np.int64)})
    out = apply_freezes(frame, units, {"z": epochs_f}, {"z": 5})
    assert out["z"].dtype == np.float64 and out["z"].tolist() == [7.0, 7.0, 9.0, 9.0]
    frame2 = pd.DataFrame({"z": [np.nan, 1.0]})
    out2 = apply_freezes(frame2, np.array([0, 0]), {"z": np.array([5, 6])}, {"z": 5})
    assert np.isnan(out2["z"]).all()  # the value at the epoch is missing


def test_freeze_refusals():
    frame = pd.DataFrame({"z": [1.0, 2.0]})
    units = np.array([0, 0])
    with pytest.raises(RefusedError, match="more than one value"):
        apply_freezes(frame, units, {"z": np.array([5, 5])}, {"z": 5})
    with pytest.raises(RefusedError, match="name"):
        apply_freezes(frame, units, {"z": np.array([5, 6])}, {"z": 5, "w": 5})
    with pytest.raises(RefusedError, match="does not hold"):
        apply_freezes(frame, units, {"q": np.array([5, 6])}, {"q": 5})
    with pytest.raises(RefusedError, match="whole days"):
        apply_freezes(frame, units, {"z": np.array([5.5, 6.0])}, {"z": 5})
    with pytest.raises(RefusedError, match="one value per frame row"):
        apply_freezes(frame, units, {"z": np.array([5])}, {"z": 5})
    with pytest.raises(RefusedError, match="integer"):
        apply_freezes(frame, units, {"z": np.array([5, 6])}, {"z": 5.0})


# ---------------------------------------------------------------------------------------------------
# history block
class FakeVault:
    """asof_rows exactly as the vault contract states, over a dense label matrix; records the
    REQUESTS (unit rows, newest readable step, k_back) as history_block made them."""

    def __init__(self, grid, labels):
        self.grid = grid
        self.labels = np.asarray(labels, dtype=np.float64)
        self.requests = []

    def asof_rows(self, unit_rows, newest_readable, k_back):
        self.requests.append((np.asarray(unit_rows).copy(), np.asarray(newest_readable).copy(), k_back))
        step = np.asarray(newest_readable) - k_back
        j = step - self.grid.first_step
        out = np.full(len(step), np.nan)
        ok = (j >= 0) & (j < self.grid.n_steps)
        out[ok] = self.labels[np.asarray(unit_rows)[ok], j[ok]]
        return out


DONOR = 7.25  # a donor-row mean at the cut (synthetic)


def spec(columns=None, last=3, windows=(12, 60), all_mean=True, offset=0, dropped=()):
    s = NS(columns=(), last_values=last, trailing_steps=windows, trailing_days=(365, 1826),
           all_history_mean=all_mean, start_offset_steps=offset, dropped_duplicates=tuple(dropped))
    s.columns = tuple(columns) if columns is not None else tuple(
        c for c in history_column_names(s) if c not in s.dropped_duplicates)
    return s


def season_of(steps, per_year=12):
    """The monthly season key of the test grids (month 1..12 from the year x 12 + month index)."""
    return (np.asarray(steps) - 1) % per_year + 1


def unit_history(unit_id, y, times=None, keys=None, cut=None):
    """A UnitHistory view: labels y at the given steps (default 1, 2, ...), season keys (default 1)
    and its cut (default the last label step)."""
    y = np.asarray(y, dtype=float)
    times = np.arange(1, len(y) + 1) if times is None else np.asarray(times)
    keys = np.ones(len(y), dtype=int) if keys is None else np.asarray(keys)
    if cut is None:
        cut = int(times.max()) if len(times) else 0
    return NS(unit_id=unit_id, group="g", cut=cut, cut_kind="fit", lead=0, times=times,
              season_keys=keys, y=y)


def history_at_cut(grid, labels, cut, per_year=12):
    """{unit id: UnitHistory at the cut} as FitContext builds it: each unit's VALID labels dated at or
    before the cut, with their season keys."""
    steps = grid.first_step + np.arange(grid.n_steps)
    out = {}
    for r, unit_id in enumerate(grid.unit_ids):
        ok = np.isfinite(labels[r]) & (steps <= cut)
        out[unit_id] = unit_history(unit_id, labels[r][ok], times=steps[ok],
                                    keys=season_of(steps[ok], per_year), cut=cut)
    return out


def block_of(grid, sp, t, rows, lead, vault, fill, keys=None, donor=DONOR):
    keys = np.ones(len(t), dtype=int) if keys is None else keys
    return history_block(grid, sp, t, rows, lead, vault, fill, keys, donor)


def _reference(labels, first, rows, t, lead, sp, fill, unit_ids, keys, donor):
    """Plain-loop reference of the R17 block with the F1 fallback (the contract read directly)."""
    out = []
    for r, tt, key in zip(rows, t, keys):
        newest = tt - max(lead, 1) - sp.start_offset_steps

        def lab(step):
            j = step - first
            return labels[r, j] if 0 <= j < labels.shape[1] else np.nan

        def mean_over(steps):
            vals = [lab(x) for x in steps if np.isfinite(lab(x))]
            return float(np.mean(vals)) if vals else np.nan

        raw = {}
        for j in range(1, sp.last_values + 1):
            raw["hist_last_%d" % j] = lab(newest - j + 1)
        for w in sp.trailing_steps:
            raw["hist_mean_%d" % w] = mean_over(range(newest - w + 1, newest + 1))
        if sp.all_history_mean:
            raw["hist_mean_all"] = mean_over(range(first, newest + 1))
        h = fill[unit_ids[r]]
        asof = np.asarray(h.times) <= newest
        same = asof & (np.asarray(h.season_keys) == key)
        season_mean = float(np.mean(h.y[same])) if same.any() else np.nan
        all_mean = float(np.mean(h.y[asof])) if asof.any() else np.nan
        # the fill chain: shortest trailing window first, then the F1 fallback
        chain = [mean_over(range(newest - w + 1, newest + 1)) for w in sorted(sp.trailing_steps)]
        chain += [season_mean, all_mean, donor]
        row = []
        for c in sp.columns:
            v = raw[c]
            for src in chain:
                if np.isfinite(v):
                    break
                v = src
            row.append(v)
        out.append(row)
    return np.array(out, dtype=np.float32)


def _monthly_setup(n_units=3, n_steps=90, missing_share=0.2, seed=3):
    rng = np.random.RandomState(seed)  # synthetic labels only
    labels = rng.gamma(2.0, 5.0, size=(n_units, n_steps))
    labels[rng.rand(n_units, n_steps) < missing_share] = np.nan
    first = 2003 * 12 + 1
    grid = DenseGrid(unit_ids=tuple("unit_%d" % i for i in range(n_units)),
                     group_of_unit=("g",) * n_units, first_step=first, n_steps=n_steps)
    rows = np.repeat(np.arange(n_units), n_steps)
    t = np.tile(np.arange(first, first + n_steps), n_units)
    return grid, labels, rows, t


@pytest.mark.parametrize("lead,offset,windows,missing", [
    (0, 0, (12, 60), 0.2), (0, 1, (12, 60), 0.2), (3, 0, (12, 60), 0.2), (12, 1, (12, 60), 0.2),
    (0, 0, (2,), 0.6), (3, 1, (2, 4), 0.7)])
def test_history_block_matches_the_plain_reference(lead, offset, windows, missing):
    grid, labels, rows, t = _monthly_setup(missing_share=missing)
    cut = grid.first_step + 59                      # rows after the cut are test rows (D54 a)
    fill = history_at_cut(grid, labels, cut)
    keys = season_of(t)
    sp = spec(offset=offset, windows=windows)
    vault = FakeVault(grid, labels)
    block, filled = history_block(grid, sp, t, rows, lead, vault, fill, keys, DONOR)
    ref = _reference(labels, grid.first_step, rows, t, lead, sp, fill, grid.unit_ids, keys, DONOR)
    assert block.dtype == np.float32 and block.shape == (len(t), len(sp.columns))
    np.testing.assert_allclose(block, ref, rtol=1e-6)
    assert np.isfinite(block).all()
    assert set(filled) == set(sp.columns) and all(0.0 <= v <= 1.0 for v in filled.values())
    # G-HIST, request side: each request names a target row's own unit with exactly that row's
    # newest readable step (t - max(L, 1) - offset, always before t) and a k_back >= 0, so the block
    # never asks for a later label. That the vault serves nothing later is the vault's own contract.
    newest_of = {(r, tt - max(lead, 1) - offset) for r, tt in zip(rows.tolist(), t.tolist())}
    ks = []
    for unit_rows, newest, k_back in vault.requests:
        assert isinstance(k_back, int) and k_back >= 0
        assert all((r, n) in newest_of for r, n in zip(unit_rows.tolist(), newest.tolist()))
        ks.append(k_back)
    assert ks == list(range(len(ks)))  # one request per look-back step, newest first


def test_nowcast_block_ends_at_t_minus_1_and_offset_moves_it_to_t_minus_2():
    grid = DenseGrid(unit_ids=("u",), group_of_unit=("g",), first_step=1, n_steps=6)
    labels = np.array([[10.0, 20.0, 30.0, 40.0, 50.0, 60.0]])
    fill = {"u": unit_history("u", [1.0])}
    sp = spec(windows=(2,), all_mean=False)
    b0, _ = block_of(grid, sp, np.array([6]), np.array([0]), 0, FakeVault(grid, labels), fill)
    assert b0.tolist() == [[50.0, 40.0, 30.0, 45.0]]
    sp1 = spec(windows=(2,), all_mean=False, offset=1)
    b1, _ = block_of(grid, sp1, np.array([6]), np.array([0]), 0, FakeVault(grid, labels), fill)
    assert b1.tolist() == [[40.0, 30.0, 20.0, 35.0]]
    b3, _ = block_of(grid, sp, np.array([6]), np.array([0]), 3, FakeVault(grid, labels), fill)
    assert b3.tolist() == [[30.0, 20.0, 10.0, 25.0]]


def test_fill_chain_one_year_then_five_years_then_the_as_of_normal_never_zero():
    grid = DenseGrid(unit_ids=("u",), group_of_unit=("g",), first_step=1, n_steps=10)
    nan = np.nan
    labels = np.array([[1.0, 2.0, nan, nan, 5.0, nan, nan, nan, nan, nan]])
    sp = spec(last=2, windows=(3, 6), all_mean=True)
    t = np.array([2, 9, 10])
    # t=2: newest 1 -> last1 = 1; last2 (step 0, before the grid) takes the 3-step mean {1} = 1
    # t=9: newest 8 -> the 3-step window {6,7,8} is empty, so gaps take the 6-step mean {5} = 5
    # t=10: newest 9 -> the same
    block, filled = block_of(grid, sp, t, np.array([0, 0, 0]), 0, FakeVault(grid, labels),
                             {"u": unit_history("u", [4.0, 8.0])})
    assert sp.columns == ("hist_last_1", "hist_last_2", "hist_mean_3", "hist_mean_6", "hist_mean_all")
    for j in range(4):
        assert block[:, j].tolist() == [1.0, 5.0, 5.0]
    np.testing.assert_allclose(block[:, 4], [1.0, 8.0 / 3.0, 8.0 / 3.0], rtol=1e-6)
    assert filled == pytest.approx({"hist_last_1": 2 / 3, "hist_last_2": 1.0, "hist_mean_3": 2 / 3,
                                    "hist_mean_6": 0.0, "hist_mean_all": 0.0})
    # no label in the trailing windows: the unit's as-of season mean, from its history at the cut
    # dated at or before the newest readable step 9 (steps 1 and 5 here: 3 and 5 -> 4), never 0
    labels2 = np.full((1, 10), nan)
    labels2[0, 0], labels2[0, 4] = 3.0, 5.0
    b2, _ = block_of(grid, spec(last=1, windows=(2,), all_mean=False), np.array([10]), np.array([0]), 0,
                     FakeVault(grid, labels2), {"u": unit_history("u", [3.0, 5.0], times=[1, 5])})
    assert b2.tolist() == [[4.0, 4.0]]


def test_the_old_normal_leak_is_gone_the_rows_own_and_later_labels_never_fill():
    # Before owner ruling F1 this row took the unit's whole history at the cut (2, 4, 6, 8 -> 5),
    # its own label y(2) = 2 and the later labels included. Now nothing at or after the row can
    # enter: the history holds no label at or before the newest readable step 1, so the fallback
    # goes past the season and all-season means to the donor-row mean at the cut.
    grid = DenseGrid(unit_ids=("u",), group_of_unit=("g",), first_step=1, n_steps=5)
    labels = np.array([[np.nan, 2.0, 4.0, 6.0, 8.0]])
    block, filled = block_of(grid, spec(last=1, windows=(2,), all_mean=False), np.array([2]),
                             np.array([0]), 0, FakeVault(grid, labels),
                             {"u": unit_history("u", [2.0, 4.0, 6.0, 8.0], times=[2, 3, 4, 5])})
    assert block.tolist() == [[DONOR, DONOR]] and filled == {"hist_last_1": 1.0, "hist_mean_2": 1.0}


def test_fill_chain_takes_the_shortest_window_first_whatever_the_spec_order():
    grid = DenseGrid(unit_ids=("u",), group_of_unit=("g",), first_step=1, n_steps=10)
    nan = np.nan
    # by step: 1, 2, -, -, 5, -, 7, -, -, 10; nowcast of step 10 -> newest readable step 9
    labels = np.array([[1.0, 2.0, nan, nan, 5.0, nan, 7.0, nan, nan, 10.0]])
    fill = {"u": unit_history("u", [99.0])}
    blocks = {}
    for windows in ((3, 6), (6, 3)):
        sp = spec(last=2, windows=windows, all_mean=False)
        block, _ = block_of(grid, sp, np.array([10]), np.array([0]), 0, FakeVault(grid, labels), fill)
        blocks[windows] = dict(zip(sp.columns, block[0].tolist()))
    # steps 9 and 8 are missing: the 3-step mean {7} fills them, never the 6-step mean {5, 7} = 6
    for got in blocks.values():
        assert got == {"hist_last_1": 7.0, "hist_last_2": 7.0, "hist_mean_3": 7.0, "hist_mean_6": 6.0}


def test_annual_spec_with_a_dropped_duplicate_still_fills_from_the_one_year_mean():
    grid = DenseGrid(unit_ids=("u",), group_of_unit=("g",), first_step=2003, n_steps=6)
    labels = np.array([[0.1, np.nan, 0.3, np.nan, 0.5, 0.6]])
    sp = spec(windows=(1, 5), dropped=("hist_mean_1",))
    assert sp.columns == ("hist_last_1", "hist_last_2", "hist_last_3", "hist_mean_5", "hist_mean_all")
    block, _ = block_of(grid, sp, np.array([2008]), np.array([0]), 0, FakeVault(grid, labels),
                        {"u": unit_history("u", [0.2], times=[2003])})
    # newest 2007 = 0.5; last2 = 2006 missing -> 1-yr mean (0.5); last3 = 2005 = 0.3
    # the 5-step window 2003..2007 holds 0.1, 0.3 and 0.5, as does all history
    np.testing.assert_allclose(block[0], [0.5, 0.5, 0.3, 0.3, 0.3], rtol=1e-6)


def test_empty_spec_for_the_neighbour_kind_gives_no_columns():
    grid = DenseGrid(unit_ids=("u",), group_of_unit=("g",), first_step=1, n_steps=3)
    sp = spec(columns=(), last=0, windows=(), all_mean=False)
    block, filled = block_of(grid, sp, np.array([2, 3]), np.array([0, 0]), 0,
                             FakeVault(grid, np.ones((1, 3))), {"u": unit_history("u", [1.0])})
    assert block.shape == (2, 0) and filled == {}


def test_no_rows_gives_an_empty_block_with_nan_shares():
    grid = DenseGrid(unit_ids=("u",), group_of_unit=("g",), first_step=1, n_steps=3)
    block, filled = block_of(grid, spec(windows=(2,)), np.array([], dtype=int), np.array([], dtype=int),
                             0, FakeVault(grid, np.ones((1, 3))), {})
    assert block.shape == (0, 5) and all(np.isnan(v) for v in filled.values())


def test_history_refusals():
    grid = DenseGrid(unit_ids=("u", "v"), group_of_unit=("g", "g"), first_step=1, n_steps=5)
    labels = np.ones((2, 5))
    fill = {"u": unit_history("u", [1.0]), "v": unit_history("v", [1.0])}
    t, rows = np.array([3, 4]), np.array([0, 1])

    def run(sp=None, t=t, rows=rows, lead=0, vault=None, fill=fill, keys=None, donor=DONOR):
        return block_of(grid, sp or spec(windows=(2,)), t, rows, lead,
                        vault or FakeVault(grid, labels), fill, keys=keys, donor=donor)

    with pytest.raises(RefusedError, match="lead_steps is negative"):
        run(lead=-1)
    with pytest.raises(RefusedError, match="start_offset_steps is negative"):
        run(sp=spec(windows=(2,), offset=-1))
    with pytest.raises(RefusedError, match="do not describe"):
        run(sp=spec(columns=("h_y0",), windows=(2,)))
    with pytest.raises(RefusedError, match="also dropped"):
        run(sp=spec(columns=("hist_last_1",), windows=(2,), dropped=("hist_last_1",)))
    with pytest.raises(RefusedError, match="twice"):
        run(sp=spec(columns=("hist_last_1", "hist_last_1"), windows=(2,)))
    with pytest.raises(RefusedError, match="twice"):
        history_column_names(spec(columns=(), windows=(2, 2)))
    with pytest.raises(RefusedError, match="at least 1 step"):
        history_column_names(spec(columns=(), windows=(0,)))
    with pytest.raises(RefusedError, match="outside the grid"):
        run(t=np.array([3, 6]))
    with pytest.raises(RefusedError, match="not on the grid"):
        run(rows=np.array([0, 2]))
    with pytest.raises(RefusedError, match="differ in length"):
        run(rows=np.array([0]))
    with pytest.raises(RefusedError, match="no unit history"):
        run(fill={"u": fill["u"]})
    with pytest.raises(RefusedError, match="belongs to unit"):
        run(fill={"u": fill["u"], "v": fill["u"]})
    with pytest.raises(RefusedError, match="non-finite labels"):
        run(fill={"u": fill["u"], "v": unit_history("v", [np.nan])})

    class Bad(FakeVault):
        def asof_rows(self, unit_rows, newest_readable, k_back):
            return np.ones(len(unit_rows) + 1)

    with pytest.raises(RefusedError, match="shape"):
        run(vault=Bad(grid, labels))

    class Inf(FakeVault):
        def asof_rows(self, unit_rows, newest_readable, k_back):
            return np.full(len(unit_rows), np.inf)

    with pytest.raises(RefusedError, match="infinite"):
        run(vault=Inf(grid, labels))


def test_reads_before_the_grid_start_are_absent_not_requested():
    grid = DenseGrid(unit_ids=("u",), group_of_unit=("g",), first_step=10, n_steps=5)
    vault = FakeVault(grid, np.arange(5.0).reshape(1, 5) + 1)
    block_of(grid, spec(windows=(3,)), np.array([10, 11, 14]), np.array([0, 0, 0]), 0, vault,
             {"u": unit_history("u", [9.0], times=[10])})
    assert all((newest - k >= 10).all() for _, newest, k in vault.requests)


# ---------------------------------------------------------------------------------------------------
# features_at_issue_step (R8, R11)
def test_issue_step_rows_move_the_whole_feature_row_back_within_the_unit():
    units = np.array([1, 0, 0, 1, 0, 1, 0])
    steps = np.array([3, 2, 5, 1, 1, 2, 3])              # unit 0: steps 1, 2, 3, 5 (gap at 4)
    X = np.column_stack([units * 100.0 + steps, -(units * 100.0 + steps)]).astype(np.float32)
    before = X.copy()
    out = features_at_issue_step(X, units, steps, 2)
    lookup = {(u, s): row for u, s, row in zip(units, steps, X)}
    for i, (u, s) in enumerate(zip(units, steps)):
        want = lookup.get((u, s - 2))
        if want is None:
            assert np.isnan(out[i]).all()                # no issue row: NaN, never a neighbour
        else:
            assert out[i].tolist() == want.tolist()
    assert out.dtype == np.float32 and out.shape == X.shape
    np.testing.assert_array_equal(X, before)
    # unit 0, step 5: its issue step 3 exists two steps back; step 4 is absent, never used
    i5 = np.flatnonzero((units == 0) & (steps == 5))[0]
    assert out[i5].tolist() == [3.0, -3.0]


def test_lead_zero_returns_the_input_values_and_dtype_and_ints_become_float_at_a_lead():
    X = np.arange(6, dtype=np.int32).reshape(3, 2)
    same = features_at_issue_step(X, np.array([0, 0, 0]), np.array([1, 2, 3]), 0)
    assert same.dtype == np.int32 and same.tolist() == X.tolist() and same is not X
    moved = features_at_issue_step(X, np.array([0, 0, 0]), np.array([1, 2, 3]), 1)
    assert moved.dtype == np.float64 and np.isnan(moved[0]).all() and moved[1:].tolist() == [[0, 1], [2, 3]]
    b = features_at_issue_step(np.array([[True], [False]]), np.array([0, 0]), np.array([1, 2]), 1)
    assert b.dtype == np.float64 and np.isnan(b[0, 0]) and b[1, 0] == 1.0


def test_issue_step_on_random_panels_never_crosses_a_unit():
    rng = np.random.RandomState(11)  # synthetic keys only
    units = np.repeat(np.arange(6), 40)
    steps = np.tile(np.arange(40), 6)
    keep = rng.rand(len(units)) > 0.3
    units, steps = units[keep], steps[keep]
    perm = rng.permutation(len(units))
    units, steps = units[perm], steps[perm]
    X = np.column_stack([units, steps]).astype(np.float64)
    for lead in (1, 3, 12):
        out = features_at_issue_step(X, units, steps, lead)
        have = ~np.isnan(out[:, 0])
        assert (out[have, 0] == units[have]).all() and (out[have, 1] == steps[have] - lead).all()
        present = set(zip(units.tolist(), steps.tolist()))
        assert all(((u, s - lead) in present) == h for u, s, h in zip(units.tolist(), steps.tolist(), have))


def test_issue_step_refusals():
    X = np.zeros((2, 1))
    units, steps = np.array([0, 0]), np.array([1, 2])
    with pytest.raises(RefusedError, match="negative"):
        features_at_issue_step(X, units, steps, -1)
    with pytest.raises(RefusedError, match="integer"):
        features_at_issue_step(X, units, steps, 1.0)
    with pytest.raises(RefusedError, match="2-D"):
        features_at_issue_step(np.zeros(2), units, steps, 1)
    with pytest.raises(RefusedError, match="numeric"):
        features_at_issue_step(np.array([["a"], ["b"]], dtype=object), units, steps, 1)
    with pytest.raises(RefusedError, match="differ in length"):
        features_at_issue_step(X, np.array([0]), steps, 1)
    for lead in (0, 1):
        with pytest.raises(RefusedError, match="repeat"):
            features_at_issue_step(X, units, np.array([1, 1]), lead)
    with pytest.raises(RefusedError):
        features_at_issue_step(X, units, np.array([1.5, 2.0]), 1)


def test_event_history_block_waits_for_m8():
    with pytest.raises(NotImplementedError, match="M8"):
        event_history_block(np.array(["u"]), np.array([1]), np.array([1]), 0, None, {})
