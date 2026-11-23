"""io science: the leak-free fallback of the R17 history block (owner ruling F1).

A missing history value takes the row's trailing means, then the unit's AS-OF season mean (its labels
within the cut, dated at or before the row's newest readable step, same season key), then its as-of
all-season mean, then the donor-row mean at the cut. Never 0, never a label at or after the row.

The proofs here are invariance tests: every label at or after a row (and, at a lead, every label
after its issue step) is replaced by a huge value, in the vault AND in the unit history, and the
row's block must not move. If any such label could enter, the block would jump.
"""

import numpy as np
import pytest

from test_io_science_apply import (DONOR, FakeVault, block_of, history_at_cut, season_of, spec,
                                   unit_history)
from treeroute.errors import RefusedError
from treeroute.io.apply import history_block
from treeroute.io.steps import DenseGrid

POISON = 1.0e9


def _grid(n_units, n_steps, first=2003 * 12 + 1):
    return DenseGrid(unit_ids=tuple("unit_%d" % i for i in range(n_units)), group_of_unit=("g",) * n_units,
                     first_step=first, n_steps=n_steps)


# ---------------------------------------------------------------------------------------------------
# the order of the fallback
def test_fallback_is_season_mean_then_all_season_mean_then_donor_mean():
    grid = _grid(1, 30)
    f = grid.first_step
    nan = np.nan
    labels = np.full((1, 30), nan)
    labels[0, 0] = 10.0          # step f      (season 1)
    labels[0, 1] = 20.0          # step f + 1  (season 2)
    labels[0, 12] = 30.0         # step f + 12 (season 1)
    fill = history_at_cut(grid, labels, cut=f + 29)
    sp = spec(last=1, windows=(2,), all_mean=False)
    t = np.array([f + 24, f + 14, f + 3, f])
    keys = season_of(t)                     # seasons 1, 3, 4, 1
    block, filled = history_block(grid, sp, t, np.zeros(4, dtype=int), 0, FakeVault(grid, labels), fill,
                                  keys, DONOR)
    # t = f+24 (season 1): trailing window {f+22, f+23} empty -> the season-1 labels at or before
    #   f+23: 10 and 30 -> 20
    # t = f+14 (season 3): window {f+12, f+13}: hist_last_1 (f+13) is missing, filled by the window
    #   mean {30} = 30; hist_mean_2 = 30
    # t = f+3 (season 4): window {f+1, f+2} holds 20 -> both columns 20 (hist_last_1 at f+2 missing)
    # t = f (season 1): nothing at or before f-1 -> the donor mean
    assert block[:, 0].tolist() == [20.0, 30.0, 20.0, DONOR]
    assert block[:, 1].tolist() == [20.0, 30.0, 20.0, DONOR]
    # a season with no label of its own falls to the all-season mean
    t2 = np.array([f + 27])                 # season 4; window {f+25, f+26} empty
    b2, _ = history_block(grid, sp, t2, np.zeros(1, dtype=int), 0, FakeVault(grid, labels), fill,
                          season_of(t2), DONOR)
    assert b2.tolist() == [[20.0, 20.0]]    # mean of 10, 20, 30
    assert filled["hist_last_1"] == 1.0


def test_the_fallback_is_read_as_of_each_row_not_once_per_unit():
    grid = _grid(1, 40)
    f = grid.first_step
    labels = np.full((1, 40), np.nan)
    labels[0, 0], labels[0, 12], labels[0, 24] = 1.0, 2.0, 6.0       # all season 1
    fill = history_at_cut(grid, labels, cut=f + 39)
    sp = spec(last=1, windows=(1,), all_mean=False)
    t = np.array([f + 12, f + 24, f + 36])                            # season 1 rows
    block, _ = block_of(grid, sp, t, np.zeros(3, dtype=int), 0, FakeVault(grid, labels), fill,
                        keys=season_of(t))
    # each row sees only the season-1 labels before it: {1}, {1, 2}, {1, 2, 6}
    np.testing.assert_allclose(block[:, 0], [1.0, 1.5, 3.0], rtol=1e-6)


def test_a_lead_moves_the_fallback_bound_to_the_issue_step():
    grid = _grid(1, 40)
    f = grid.first_step
    labels = np.full((1, 40), np.nan)
    labels[0, 0], labels[0, 22] = 4.0, 100.0          # season 1 at f; season 11 at f + 22
    fill = history_at_cut(grid, labels, cut=f + 39)
    sp = spec(last=1, windows=(1,), all_mean=False)
    t = np.array([f + 24])                            # season 1; at lead 3 the issue step is f + 21
    b0, _ = block_of(grid, sp, t, np.zeros(1, dtype=int), 0, FakeVault(grid, labels), fill, keys=season_of(t))
    b3, _ = block_of(grid, sp, t, np.zeros(1, dtype=int), 3, FakeVault(grid, labels), fill, keys=season_of(t))
    assert b0.tolist() == [[4.0, 4.0]]                # season mean {4}
    # at lead 3 the label at f + 22 lies after the issue step: not read, so the season mean is 4
    # and the all-season mean would be 4 too (never 52 = mean of 4 and 100)
    assert b3.tolist() == [[4.0, 4.0]]
    t2 = np.array([f + 26])                           # season 3 (no season label): all-season
    b_all0, _ = block_of(grid, sp, t2, np.zeros(1, dtype=int), 0, FakeVault(grid, labels), fill,
                         keys=season_of(t2))
    # at lead 4 the issue step is f + 22 itself, so its label is readable and fills hist_last_1
    b_all4, _ = block_of(grid, sp, t2, np.zeros(1, dtype=int), 4, FakeVault(grid, labels), fill,
                         keys=season_of(t2))
    # at lead 5 the issue step is f + 21: the label at f + 22 is after it and never enters
    b_all5, _ = block_of(grid, sp, t2, np.zeros(1, dtype=int), 5, FakeVault(grid, labels), fill,
                         keys=season_of(t2))
    assert b_all0.tolist() == [[52.0, 52.0]]
    assert b_all4.tolist() == [[100.0, 100.0]] and b_all5.tolist() == [[4.0, 4.0]]


def test_never_zero_when_nothing_is_known_the_donor_mean_fills_even_if_it_is_small():
    grid = _grid(2, 6, first=1)
    labels = np.full((2, 6), np.nan)
    fill = {u: unit_history(u, []) for u in grid.unit_ids}
    block, filled = block_of(grid, spec(windows=(2, 4)), np.array([3, 6]), np.array([0, 1]), 0,
                             FakeVault(grid, labels), fill, donor=0.125)
    assert (block == np.float32(0.125)).all() and all(v == 1.0 for v in filled.values())


# ---------------------------------------------------------------------------------------------------
# the proofs: no label at or after the row can enter
def _poisoned(labels, fill, grid, r, after_step):
    """Labels and histories with every label of unit r dated after ``after_step`` replaced by POISON."""
    steps = grid.first_step + np.arange(grid.n_steps)
    lab = labels.copy()
    late = steps > after_step
    lab[r, late & np.isfinite(lab[r])] = POISON
    out = dict(fill)
    h = fill[grid.unit_ids[r]]
    y = h.y.copy()
    y[np.asarray(h.times) > after_step] = POISON
    out[grid.unit_ids[r]] = unit_history(h.unit_id, y, times=h.times, keys=h.season_keys, cut=h.cut)
    return lab, out


@pytest.mark.parametrize("lead,offset,windows", [(0, 0, (2,)), (0, 1, (3, 6)), (3, 0, (2,)),
                                                 (6, 1, (2, 12))])
def test_no_label_at_or_after_the_row_or_its_issue_step_can_enter_the_block(lead, offset, windows):
    rng = np.random.RandomState(5)  # synthetic labels only
    grid = _grid(4, 72)
    labels = rng.gamma(2.0, 3.0, size=(4, 72))
    labels[rng.rand(4, 72) < 0.65] = np.nan          # sparse, so the fallback is reached often
    cut = grid.first_step + 47
    fill = history_at_cut(grid, labels, cut)
    sp = spec(last=3, windows=windows, all_mean=True, offset=offset)
    rows = np.repeat(np.arange(4), 72)
    t = np.tile(grid.first_step + np.arange(72), 4)
    keys = season_of(t)
    base, filled = history_block(grid, sp, t, rows, lead, FakeVault(grid, labels), fill, keys, DONOR)
    assert np.isfinite(base).all() and (base < POISON / 10).all()
    reached = 0
    for i in range(0, len(t), 7):
        r, tt = int(rows[i]), int(t[i])
        newest = tt - max(lead, 1) - offset
        lab, fill_p = _poisoned(labels, fill, grid, r, newest)
        got, _ = history_block(grid, sp, t[i:i + 1], rows[i:i + 1], lead, FakeVault(grid, lab), fill_p,
                               keys[i:i + 1], DONOR)
        np.testing.assert_array_equal(got[0], base[i])
        reached += int(np.isnan(labels[r, max(newest - grid.first_step, 0)]) or newest < grid.first_step)
    assert reached > 0
    assert max(filled.values()) > 0.3                 # the fallback really was exercised


def test_a_test_rows_fallback_reads_labels_within_the_cut_only():
    # D54 (a): a test row's own columns read test-window labels known at its issue step, but F1's
    # fallback reads the unit history at the cut, so a test-window label never fills a gap.
    grid = _grid(1, 30)
    f = grid.first_step
    labels = np.full((1, 30), np.nan)
    labels[0, 0] = 8.0            # step f (season 1), before the cut
    labels[0, 21] = 500.0         # step f + 21 (season 10), after the cut: test window
    cut = f + 19
    fill = history_at_cut(grid, labels, cut)
    assert fill["unit_0"].times.tolist() == [f]
    sp = spec(last=1, windows=(2,), all_mean=True)
    t = np.array([f + 25])        # a test row, nowcast: newest readable f + 24
    block, _ = block_of(grid, sp, t, np.zeros(1, dtype=int), 0, FakeVault(grid, labels), fill,
                        keys=season_of(t))
    # hist_last_1 and hist_mean_2 have no label in {f+23, f+24}: the fallback is the as-of
    # all-season mean within the cut (8), not 500; hist_mean_all reads every readable label (D54 a)
    np.testing.assert_allclose(block[0], [8.0, 8.0, 254.0], rtol=1e-6)


def test_a_history_label_after_its_cut_or_off_the_grid_is_refused():
    grid = _grid(1, 12, first=1)
    labels = np.ones((1, 12))
    t, rows = np.array([5]), np.array([0])
    with pytest.raises(RefusedError, match="after its cut"):
        block_of(grid, spec(windows=(2,)), t, rows, 0, FakeVault(grid, labels),
                 {"unit_0": unit_history("unit_0", [1.0, 2.0], times=[3, 9], cut=6)})
    with pytest.raises(RefusedError, match="off the grid"):
        block_of(grid, spec(windows=(2,)), t, rows, 0, FakeVault(grid, labels),
                 {"unit_0": unit_history("unit_0", [1.0], times=[0])})
    with pytest.raises(RefusedError, match="twice"):
        block_of(grid, spec(windows=(2,)), t, rows, 0, FakeVault(grid, labels),
                 {"unit_0": unit_history("unit_0", [1.0, 2.0], times=[3, 3])})


# ---------------------------------------------------------------------------------------------------
# season keys and the donor mean
def test_row_season_keys_must_match_the_history_where_they_meet():
    grid = _grid(1, 24)
    f = grid.first_step
    labels = np.ones((1, 24))
    fill = history_at_cut(grid, labels, cut=f + 23)
    t = np.array([f + 5, f + 6])
    ok, _ = block_of(grid, spec(windows=(2,)), t, np.zeros(2, dtype=int), 0, FakeVault(grid, labels), fill,
                     keys=season_of(t))
    assert np.isfinite(ok).all()
    with pytest.raises(RefusedError, match="season key") as info:
        block_of(grid, spec(windows=(2,)), t, np.zeros(2, dtype=int), 0, FakeVault(grid, labels), fill,
                 keys=season_of(t) - 1)          # a 0-based convention against the history's 1-based
    assert "R2" in str(info.value)
    # a row whose step is not in the history (a test row past the cut) is not checked
    fill_short = history_at_cut(grid, labels, cut=f + 3)
    block_of(grid, spec(windows=(2,)), t, np.zeros(2, dtype=int), 0, FakeVault(grid, labels), fill_short,
             keys=np.array([99, 98]))


def test_season_key_and_donor_mean_refusals():
    grid = _grid(1, 6, first=1)
    labels = np.ones((1, 6))
    fill = {"unit_0": unit_history("unit_0", [1.0])}
    t, rows = np.array([3, 4]), np.array([0, 0])

    def run(keys=None, donor=DONOR, fill=fill):
        return block_of(grid, spec(windows=(2,)), t, rows, 0, FakeVault(grid, labels), fill, keys=keys,
                        donor=donor)

    with pytest.raises(RefusedError, match="season keys"):
        run(keys=np.array([1]))
    with pytest.raises(RefusedError, match="whole numbers"):
        run(keys=np.array([1.5, 1.0]))
    for bad in (np.nan, np.inf):
        with pytest.raises(RefusedError, match="not finite"):
            run(donor=bad)
    for bad in (True, "7", None):
        with pytest.raises(RefusedError, match="must be a number"):
            run(donor=bad)
    assert run(donor=np.float32(2.5))[0].shape == (2, 5)
    assert run(donor=3)[0].shape == (2, 5)

    class NoCut:
        unit_id, times, season_keys, y = "unit_0", np.array([1]), np.array([1]), np.array([1.0])

    with pytest.raises(RefusedError, match="not a UnitHistory"):
        run(fill={"unit_0": NoCut()})
    with pytest.raises(RefusedError, match="one per label"):
        run(fill={"unit_0": unit_history("unit_0", [1.0, 2.0], times=[1, 2], keys=[1])})
    with pytest.raises(RefusedError, match="integer"):
        bad_cut = unit_history("unit_0", [1.0])
        bad_cut.cut = 1.0
        run(fill={"unit_0": bad_cut})


def test_many_units_run_vectorised_and_match_a_per_unit_run():
    rng = np.random.RandomState(9)  # synthetic labels only
    grid = _grid(300, 30)
    labels = rng.gamma(2.0, 3.0, size=(300, 30))
    labels[rng.rand(300, 30) < 0.8] = np.nan
    fill = history_at_cut(grid, labels, cut=grid.first_step + 20)
    rows = np.repeat(np.arange(300), 30)
    t = np.tile(grid.first_step + np.arange(30), 300)
    sp = spec(last=2, windows=(2,), all_mean=False)
    whole, _ = history_block(grid, sp, t, rows, 0, FakeVault(grid, labels), fill, season_of(t), DONOR)
    for r in (0, 57, 299):
        sel = rows == r
        part, _ = history_block(grid, sp, t[sel], rows[sel], 0, FakeVault(grid, labels), fill,
                                season_of(t[sel]), DONOR)
        np.testing.assert_array_equal(part, whole[sel])
