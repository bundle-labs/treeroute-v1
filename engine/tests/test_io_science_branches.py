"""io science: the branches the other io science test files do not reach on their own.

Three kinds:
  - refusals a caller can reach with odd but legal inputs (a key space too large for one int64 key,
    a fact that is not a string, a cadence without a kind, facts without a sentinel field);
  - behaviour the contract asks for that no other file checks: the history block PRINTS its filled
    shares, and its newest readable step is timing.latest_label_step's, not a local copy;
  - INTERNAL asserts, which the code's own construction makes unreachable. They are reached here by
    breaking one helper on purpose (monkeypatch, restored after each test), so each assert is shown
    to fire and to name its rule, rather than being dead code nobody has seen run.

The one internal assert left unreached is inside io.steps.predecessor_index itself: its hits come
from an exact key equality, so breaking it would need a patched numpy. Its callers' own re-checks
(apply_lags, features_at_issue_step, join_coarser_column) are reached below.
"""

from types import SimpleNamespace as NS

import numpy as np
import pandas as pd
import pytest

import treeroute.io.apply as apply_mod
import treeroute.io.joins as joins_mod
from test_io_science_apply import DONOR, FakeVault, block_of, spec, unit_history
from treeroute.errors import RefusedError
from treeroute.io.apply import apply_lags, features_at_issue_step
from treeroute.io.joins import join_coarser_column, join_one_to_one
from treeroute.io.sentinel import mask_sentinels
from treeroute.io.steps import DenseGrid, cadence_view, fact_value, predecessor_index
from treeroute.timing import latest_label_step

MONTHLY = NS(kind="regular", length=1, unit="month")
ANNUAL = NS(kind="regular", length=1, unit="year")
HUGE = 2 ** 61  # a step span that no int64 (group, step) key can hold once there are 2+ groups


def _lag(column, steps, cadence=MONTHLY):
    return NS(column=column, steps=steps, column_cadence=cadence, floor_reason=None)


def _crossing_predecessor(unit_codes, steps, k):
    """A broken lookup: every row's 'predecessor' is row 0, whatever its unit or step."""
    return np.zeros(len(np.asarray(unit_codes)), dtype=np.int64)


# ---------------------------------------------------------------------------------------------------
# internal asserts of the callers of predecessor_index (G-CALENDAR)
def test_apply_lags_refuses_a_read_that_leaves_its_unit(monkeypatch):
    frame = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
    units, steps = np.array([0, 1, 1]), np.array([1, 1, 2])
    ok = apply_lags(frame, units, steps, {"x": _lag("x", 1)}, MONTHLY)
    assert np.isnan(ok["x"].iloc[:2]).all() and ok["x"].iloc[2] == 2.0
    monkeypatch.setattr(apply_mod, "predecessor_index", _crossing_predecessor)
    with pytest.raises(RefusedError, match="lag-1 read left its unit or step") as info:
        apply_lags(frame, units, steps, {"x": _lag("x", 1)}, MONTHLY)
    assert info.value.rule == "G-CALENDAR"


def test_features_at_issue_step_refuses_a_read_that_leaves_its_unit(monkeypatch):
    X = np.array([[1.0], [2.0], [3.0]])
    units, steps = np.array([0, 1, 1]), np.array([1, 1, 2])
    assert features_at_issue_step(X, units, steps, 1)[2].tolist() == [2.0]
    monkeypatch.setattr(apply_mod, "predecessor_index", _crossing_predecessor)
    with pytest.raises(RefusedError, match="lead-1 read left its unit or step") as info:
        features_at_issue_step(X, units, steps, 1)
    assert info.value.rule == "G-CALENDAR"


def test_join_coarser_column_refuses_a_lagged_read_that_leaves_its_unit(monkeypatch):
    grid = pd.DataFrame({"x": np.zeros(4)})
    gu, gyear = np.array([0, 0, 1, 1]), np.array([2001, 2002, 2001, 2002])
    store = pd.DataFrame({"a": [10.0, 11.0, 20.0, 21.0]})
    su, syear = np.array([0, 0, 1, 1]), np.array([2001, 2002, 2001, 2002])
    args = (grid, gu, gyear, store, su, syear, "a", ANNUAL, MONTHLY, _lag("a", 1, ANNUAL))
    ok = join_coarser_column(*args)
    np.testing.assert_array_equal(ok["a"].to_numpy(), [np.nan, 10.0, np.nan, 20.0])
    monkeypatch.setattr(joins_mod, "predecessor_index", _crossing_predecessor)
    with pytest.raises(RefusedError, match="left its unit or period") as info:
        join_coarser_column(*args)
    assert info.value.rule == "G-CALENDAR"


# ---------------------------------------------------------------------------------------------------
# join_one_to_one: the row-count and row-order asserts (merge(validate="one_to_one") keeps both true)
def _pair():
    left = pd.DataFrame({"u": [1, 2, 3], "x": [0.1, 0.2, 0.3]}, index=[9, 8, 7])
    right = pd.DataFrame({"u": [3, 1, 2], "z": [30.0, 10.0, 20.0]})
    return left, right


def test_join_one_to_one_refuses_a_merge_that_adds_a_row(monkeypatch):
    left, right = _pair()
    assert join_one_to_one(left, right, ("u",), "t")[0]["z"].tolist() == [10.0, 20.0, 30.0]
    real = pd.DataFrame.merge

    def extra_row(self, *args, **kwargs):
        out = real(self, *args, **kwargs)
        return pd.concat([out, out.iloc[:1]], ignore_index=True)

    monkeypatch.setattr(pd.DataFrame, "merge", extra_row)
    with pytest.raises(RefusedError, match=r"changed the row count \(3 -> 4\)") as info:
        join_one_to_one(left, right, ("u",), "t")
    assert info.value.rule == "G-JOIN"


def test_join_one_to_one_refuses_a_merge_that_reorders_rows(monkeypatch):
    left, right = _pair()
    real = pd.DataFrame.merge

    def reversed_rows(self, *args, **kwargs):
        return real(self, *args, **kwargs).iloc[::-1].reset_index(drop=True)

    monkeypatch.setattr(pd.DataFrame, "merge", reversed_rows)
    with pytest.raises(RefusedError, match="changed the row order or key 'u'") as info:
        join_one_to_one(left, right, ("u",), "t")
    assert info.value.rule == "G-JOIN"


# ---------------------------------------------------------------------------------------------------
# history_block: the G-HIST and fill-chain internal asserts, and the (group, step) key space
def _one_unit():
    grid = DenseGrid(unit_ids=("u",), group_of_unit=("g",), first_step=1, n_steps=6)
    return grid, np.full((1, 6), np.nan)


def test_history_block_refuses_a_newest_readable_step_at_the_target_step(monkeypatch):
    grid, labels = _one_unit()
    fill = {"u": unit_history("u", [1.0])}
    block_of(grid, spec(windows=(2,)), np.array([4]), np.array([0]), 0, FakeVault(grid, labels), fill)
    # a broken bound that lets the row read its own step: the block must stop, not read it
    monkeypatch.setattr(apply_mod, "_latest_label_step", lambda t, lead: np.asarray(t).copy())
    with pytest.raises(RefusedError, match="newest readable step is not before its target step") as info:
        block_of(grid, spec(windows=(2,)), np.array([4]), np.array([0]), 0, FakeVault(grid, labels), fill)
    assert info.value.rule == "G-HIST"


def test_history_block_refuses_a_gap_left_after_the_fill_chain(monkeypatch):
    grid, labels = _one_unit()
    fill = {"u": unit_history("u", [], times=[])}           # no history: the donor mean is the last step
    got, _ = block_of(grid, spec(windows=(2,)), np.array([4]), np.array([0]), 0, FakeVault(grid, labels), fill)
    assert (got == np.float32(DONOR)).all()
    # a broken last step (a NaN donor mean slipping past its check): the block refuses, never 0
    monkeypatch.setattr(apply_mod, "_donor_mean", lambda value: float("nan"))
    with pytest.raises(RefusedError, match="still missing after the fill chain, e.g. units \\['u'\\]") as info:
        block_of(grid, spec(windows=(2,)), np.array([4]), np.array([0]), 0, FakeVault(grid, labels), fill)
    assert info.value.rule == "R17"


def test_history_block_refuses_a_group_step_key_space_too_large_for_int64():
    # three season keys in the history and a lead of 2^61 steps: the as-of mean's (season, step)
    # key would need 3 x 2^61 values, more than one int64 key can index; refused, not wrapped
    grid, labels = _one_unit()
    fill = {"u": unit_history("u", [1.0, 2.0, 3.0], times=[1, 2, 3], keys=[1, 2, 3])}
    t, rows = np.array([5]), np.array([0])
    got, _ = block_of(grid, spec(windows=(2,)), t, rows, 3, FakeVault(grid, labels), fill, keys=np.array([2]))
    assert (got == np.float32(2.0)).all()                     # the as-of season-2 mean at lead 3
    with pytest.raises(RefusedError, match=r"\(group, step\) key space is too large") as info:
        block_of(grid, spec(windows=(2,)), t, rows, HUGE, FakeVault(grid, labels), fill, keys=np.array([2]))
    assert info.value.rule == "R17"


def test_history_block_refuses_a_unit_season_key_space_too_large_for_int64():
    # season keys spanning 2^61 values: one unit fits one int64 (unit, season key) key, two do not;
    # refused, never wrapped around into another unit's season
    nan_labels = np.full((1, 6), np.nan)
    one = DenseGrid(unit_ids=("u",), group_of_unit=("g",), first_step=1, n_steps=6)
    wide = unit_history("u", [1.0, 2.0], times=[1, 2], keys=[1, HUGE])
    got, _ = block_of(one, spec(windows=(2,)), np.array([5]), np.array([0]), 0, FakeVault(one, nan_labels),
                      {"u": wide}, keys=np.array([1]))
    assert (got == np.float32(1.0)).all()                     # the as-of season-1 mean
    two = DenseGrid(unit_ids=("u", "v"), group_of_unit=("g", "g"), first_step=1, n_steps=6)
    fill = {"u": wide, "v": unit_history("v", [3.0], times=[1], keys=[1])}
    with pytest.raises(RefusedError, match=r"\(unit, season key\) key space is too large") as info:
        block_of(two, spec(windows=(2,)), np.array([5, 5]), np.array([0, 1]), 0,
                 FakeVault(two, np.full((2, 6), np.nan)), fill, keys=np.array([1, 1]))
    assert info.value.rule == "R17"


# ---------------------------------------------------------------------------------------------------
# history_block: the printed filled shares and the timing helper's label rule
def test_history_block_prints_the_filled_share_of_every_column(capsys):
    grid = DenseGrid(unit_ids=("u",), group_of_unit=("g",), first_step=1, n_steps=10)
    nan = np.nan
    labels = np.array([[1.0, 2.0, nan, nan, 5.0, nan, nan, nan, nan, nan]])
    capsys.readouterr()
    _, filled = block_of(grid, spec(last=2, windows=(3, 6)), np.array([2, 9, 10]), np.array([0, 0, 0]), 0,
                         FakeVault(grid, labels), {"u": unit_history("u", [4.0, 8.0])})
    assert filled["hist_last_2"] == 1.0
    assert capsys.readouterr().out.splitlines() == [
        "history block, lead 0, 3 rows: filled share per column: hist_last_1 0.6667, hist_last_2 1.0000, "
        "hist_mean_3 0.6667, hist_mean_6 0.0000, hist_mean_all 0.0000"]
    block_of(grid, spec(columns=(), last=0, windows=(), all_mean=False), np.array([3]), np.array([0]), 2,
             FakeVault(grid, labels), {"u": unit_history("u", [4.0])})
    block_of(grid, spec(last=1, windows=(), all_mean=False), np.array([], dtype=int), np.array([], dtype=int),
             0, FakeVault(grid, labels), {})
    assert capsys.readouterr().out.splitlines() == [
        "history block, lead 2, 1 rows: filled share per column: no history columns",
        "history block, lead 0, 0 rows: filled share per column: hist_last_1 nan"]


def test_the_newest_readable_step_is_the_timing_helpers(monkeypatch):
    steps = np.array([24005, 24000, 24005, 24100, 23999], dtype=np.int64)
    for lead in range(0, 13):
        want = [latest_label_step(int(s), lead) for s in steps]
        assert apply_mod._latest_label_step(steps, lead).tolist() == want, lead
    assert apply_mod._latest_label_step(np.array([], dtype=np.int64), 3).tolist() == []
    # delegated, not copied: a changed timing rule reaches the block, once per distinct step
    calls = []

    def changed_rule(step, lead):
        calls.append((step, lead))
        return step - 100

    monkeypatch.setattr(apply_mod, "latest_label_step", changed_rule)
    assert apply_mod._latest_label_step(steps, 2).tolist() == (steps - 100).tolist()
    assert sorted(calls) == [(23999, 2), (24000, 2), (24005, 2), (24100, 2)]
    grid = DenseGrid(unit_ids=("u",), group_of_unit=("g",), first_step=1, n_steps=200)
    labels = np.arange(1.0, 201.0)[None, :]                   # label of step s is s
    got, _ = block_of(grid, spec(last=1, windows=(), all_mean=False), np.array([150]), np.array([0]), 0,
                      FakeVault(grid, labels), {"u": unit_history("u", [1.0])})
    assert got.tolist() == [[50.0]]                           # read at 150 - 100, not at 149


# ---------------------------------------------------------------------------------------------------
# steps: predecessor key space, fact values and cadences without a kind
def test_predecessor_index_refuses_a_unit_step_key_space_too_large_for_int64():
    assert predecessor_index(np.array([0, 1]), np.array([0, 5]), 1).tolist() == [-1, -1]
    with pytest.raises(RefusedError, match=r"\(unit, step\) key space is too large") as info:
        predecessor_index(np.array([0, 1]), np.array([0, HUGE]), 1)
    assert info.value.rule == "G-CALENDAR"


def test_fact_values_must_be_enum_members_or_strings():
    assert fact_value("month", "unit") == "month"
    for bad in (3, None, 1.0, b"month"):
        with pytest.raises(RefusedError, match="must be an enum member or a string") as info:
            fact_value(bad, "cadence.unit")
        assert info.value.rule == "G-FACTS"
    with pytest.raises(RefusedError, match="enum member or a string"):
        cadence_view(NS(kind=1, length=1, unit="month"))
    with pytest.raises(RefusedError, match="enum member or a string"):
        cadence_view(NS(kind="regular", length=1, unit=12))


def test_a_cadence_without_a_kind_is_refused():
    for bad in (NS(length=1, unit="month"), None, "month", {"kind": "regular"}):
        with pytest.raises(RefusedError, match="a cadence needs a 'kind'") as info:
            cadence_view(bad)
        assert info.value.rule == "R1"


# ---------------------------------------------------------------------------------------------------
# sentinel: facts without one of the fields the mask reads
@pytest.mark.parametrize("missing", ["role", "fill_values", "near_sentinel_optout"])
def test_mask_sentinels_refuses_facts_without_a_field_it_reads(missing):
    fields = dict(role="driver", fill_values=(-9999,), near_sentinel_optout=False)
    frame = pd.DataFrame({"x": [1.0, -9999.0]})
    out, _ = mask_sentinels(frame, {"x": NS(**fields)})
    assert np.isnan(out["x"].iloc[1])
    del fields[missing]
    with pytest.raises(RefusedError, match="the facts of column 'x' have no '%s'" % missing) as info:
        mask_sentinels(frame, {"x": NS(**fields)})
    assert info.value.rule == "G-SENTINEL"
