"""The last-value rule (owner ruling J2 d; engine constant C18): io.lastvalue.fill_last_value and
last_value_max_steps.

Covered: the constant (id, value, status, origin); the step maximum per cadence; every gap class (filled,
gap longer than the maximum, head, tail, a unit with no value); calendar-step gaps (a step with no row
counts); rows in any order; the input, the index, the dtypes and the non-tree columns untouched; the
record (counts add up, JSON-ready, printed); every refusal; a brute-force reference on random panels; and
the leak proofs: a value planted at 1e9 in every LATER step never enters a fill, and changing every value
after any step T (presence kept) changes no output at or before T.
"""

import json
from types import SimpleNamespace as NS

import numpy as np
import pandas as pd
import pytest

from treeroute import engine_constants as K
from treeroute.errors import RefusedError
from treeroute.io import lastvalue as LV
from treeroute.io.lastvalue import LastValueRecord, fill_last_value, last_value_max_steps

MONTHLY = NS(kind="regular", length=1, unit="month")
ANNUAL = NS(kind="regular", length=1, unit="year")
COMPOSITE = NS(kind="composite_of_year", length=None, unit=None, composites_per_year=46, composite_days=8)
PLANT = 1e9
NAN = np.nan


def refused(rule, fn, *args, **kwargs):
    with pytest.raises(RefusedError) as info:
        fn(*args, **kwargs)
    assert info.value.rule == rule, (info.value.rule, str(info.value))
    return str(info.value)


def one_unit(values, steps=None):
    """A frame of one unit and one tree feature 'x' (plus an untouched context copy 'ctx')."""
    v = np.asarray(values, dtype=np.float64)
    s = np.arange(1, len(v) + 1) if steps is None else np.asarray(steps)
    frame = pd.DataFrame({"x": v, "ctx": v.copy()})
    return frame, np.zeros(len(v), dtype=np.int64), s


def same(a, b):
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    return a.shape == b.shape and bool(((a == b) | (np.isnan(a) & np.isnan(b))).all())


# ---------------------------------------------------------------------------------------------------
# the constant and the step maximum
def test_c18_is_two_months_cited_with_its_ruling():
    from pathlib import Path

    const = {c.id: c for c in K.constants()}["C18.last_value_max_months"]
    assert const.value == K.LAST_VALUE_MAX_MONTHS == K.get("C18.last_value_max_months") == 2
    assert const.status == "cited" and not const.test_exposed
    assert "C18" in K.groups()
    lines = Path(K.__file__).read_text(encoding="utf-8").splitlines()
    at = next(i for i, line in enumerate(lines) if line.startswith("LAST_VALUE_MAX_MONTHS = _c("))
    assert "ruling J2(d)" in "\n".join(lines[max(0, at - 7):at])
    assert LV.CONSTANT_ID == "C18.last_value_max_months" and LV.RULE == "J2d"


def test_the_maximum_in_target_steps_is_floored():
    assert last_value_max_steps(MONTHLY) == 2
    assert last_value_max_steps(ANNUAL) == 0                       # one step back is 12 months
    assert last_value_max_steps(COMPOSITE) == 7                    # floor(2 x 46 / 12)
    store_form = NS(kind="composite_of_year", length=8, unit="day", composites_per_year=46)
    assert last_value_max_steps(store_form) == 7


@pytest.mark.parametrize("cadence", [NS(kind="regular", length=3, unit="month"),
                                     NS(kind="regular", length=2, unit="year"),
                                     NS(kind="regular", length=10, unit="day"),
                                     NS(kind="static"), NS(kind="epoch"), NS(kind="irregular")])
def test_other_cadences_are_refused(cadence):
    assert "F8" in refused("J2d", last_value_max_steps, cadence)


def test_a_negative_constant_is_refused(monkeypatch):
    monkeypatch.setattr(K, "LAST_VALUE_MAX_MONTHS", -1)
    refused("J2d", last_value_max_steps, MONTHLY)
    monkeypatch.setattr(K, "LAST_VALUE_MAX_MONTHS", 2.0)
    refused("J2d", last_value_max_steps, MONTHLY)


# ---------------------------------------------------------------------------------------------------
# the gap classes
def test_short_gaps_take_the_most_recent_earlier_value():
    #          1    2    3    4    5    6    7    8    9   10
    frame, u, s = one_unit([NAN, 1.0, NAN, 3.0, NAN, NAN, 6.0, NAN, NAN, NAN])
    out, rec = fill_last_value(frame, u, s, ("x",), MONTHLY)
    assert same(out["x"], [NAN, 1.0, 1.0, 3.0, 3.0, 3.0, 6.0, NAN, NAN, NAN])
    assert same(out["ctx"], frame["ctx"])                          # not a tree feature: untouched
    assert (rec.missing["x"], rec.filled["x"], rec.gap_longer["x"], rec.head["x"], rec.tail["x"]) == (7, 3, 0, 1, 3)
    assert rec.left_to_r30("x") == 4 and rec.max_steps == 2 and rec.max_months == 2


def test_a_gap_longer_than_the_maximum_is_left_whole_to_r30():
    """Reading (1) of the module docstring: the gap falls back as a whole; its first two steps are not
    filled either."""
    frame, u, s = one_unit([1.0, NAN, NAN, NAN, 5.0, NAN, NAN, 8.0])
    out, rec = fill_last_value(frame, u, s, ("x",), MONTHLY)
    assert same(out["x"], [1.0, NAN, NAN, NAN, 5.0, 5.0, 5.0, 8.0])
    assert (rec.filled["x"], rec.gap_longer["x"], rec.head["x"], rec.tail["x"]) == (2, 3, 0, 0)


def test_gap_length_counts_calendar_steps_without_rows():
    # steps 1, 2, 4: step 3 has no row; the gap between the values at 1 and 4 is 2 steps long -> filled
    frame, u, s = one_unit([1.0, NAN, 4.0], steps=[1, 2, 4])
    out, rec = fill_last_value(frame, u, s, ("x",), MONTHLY)
    assert same(out["x"], [1.0, 1.0, 4.0]) and rec.filled["x"] == 1
    # steps 1, 2, 5: steps 3 and 4 have no row; the gap is 3 steps long -> left to R30
    frame, u, s = one_unit([1.0, NAN, 5.0], steps=[1, 2, 5])
    out, rec = fill_last_value(frame, u, s, ("x",), MONTHLY)
    assert same(out["x"], [1.0, NAN, 5.0]) and rec.gap_longer["x"] == 1


def test_head_tail_and_empty_units_stay_missing():
    frame = pd.DataFrame({"x": [NAN, NAN, 2.0, NAN, NAN, NAN, NAN, NAN]})
    u = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    s = np.array([1, 2, 3, 4, 1, 2, 3, 4])
    out, rec = fill_last_value(frame, u, s, ("x",), MONTHLY)
    assert same(out["x"], frame["x"])
    assert (rec.missing["x"], rec.filled["x"], rec.head["x"], rec.tail["x"]) == (7, 0, 6, 1)
    assert rec.units == 2 and rec.rows == 8


def test_a_fill_never_crosses_a_unit():
    # unit 0 ends with a value, unit 1 starts with a gap: unit 1's head gap is not filled from unit 0
    frame = pd.DataFrame({"x": [1.0, 2.0, NAN, 7.0]})
    out, rec = fill_last_value(frame, np.array([0, 0, 1, 1]), np.array([1, 2, 1, 2]), ("x",), MONTHLY)
    assert same(out["x"], [1.0, 2.0, NAN, 7.0]) and rec.head["x"] == 1


def test_no_fill_on_an_annual_target():
    frame, u, s = one_unit([1.0, NAN, 3.0, NAN, NAN, 6.0])
    out, rec = fill_last_value(frame, u, s, ("x",), ANNUAL)
    assert same(out["x"], frame["x"])
    assert rec.max_steps == 0 and rec.filled["x"] == 0 and rec.gap_longer["x"] == 3


def test_composite_steps_bridge_up_to_seven():
    v = [1.0] + [NAN] * 7 + [9.0] + [NAN] * 8 + [18.0]
    frame, u, s = one_unit(v)
    out, rec = fill_last_value(frame, u, s, ("x",), COMPOSITE)
    assert same(out["x"][:9], [1.0] * 8 + [9.0])                    # 7 missing composites: filled
    assert np.isnan(out["x"][9:17]).all()                           # 8 missing composites: left to R30
    assert (rec.filled["x"], rec.gap_longer["x"]) == (7, 8)


def test_the_decision_reads_presence_up_to_the_maximum_ahead_never_a_value():
    """The disclosed look-ahead: whether step 3 is filled depends on whether the column holds a value
    within the next two steps (presence), never on that value."""
    base = [1.0, 2.0, NAN, 4.0, 5.0]
    for later in ([4.0, 5.0], [NAN, 5.0], [-3.0, 77.0], [PLANT, PLANT]):
        frame, u, s = one_unit(base[:3] + later)
        out, _ = fill_last_value(frame, u, s, ("x",), MONTHLY)
        assert out["x"][2] == 2.0, later                            # filled from step 2 every time
    frame, u, s = one_unit([1.0, 2.0, NAN, NAN, NAN, 6.0])          # the gap closes 3 steps later
    out, _ = fill_last_value(frame, u, s, ("x",), MONTHLY)
    assert np.isnan(out["x"][2])


# ---------------------------------------------------------------------------------------------------
# frame handling
def test_rows_in_any_order_index_dtypes_and_input_kept():
    rng = np.random.default_rng(0)
    u = np.repeat(np.arange(3), 6)
    s = np.tile(np.arange(10, 16), 3)
    x = np.array([1, NAN, 3, NAN, NAN, 6, NAN, 2, NAN, 4, NAN, NAN, 5, NAN, NAN, NAN, 9, NAN], dtype=np.float64)
    frame = pd.DataFrame({"x": x, "f": x.astype(np.float32), "i": np.arange(18), "o": ["k"] * 18},
                         index=np.arange(18) * 7)
    perm = rng.permutation(18)
    shuffled = frame.iloc[perm]
    before = shuffled.copy(deep=True)
    out, rec = fill_last_value(shuffled, u[perm], s[perm], ("x", "f", "i"), MONTHLY)
    pd.testing.assert_frame_equal(shuffled, before)                 # the input is not changed
    assert out.index.equals(shuffled.index) and list(out.columns) == list(shuffled.columns)
    assert out["f"].dtype == np.float32 and out["i"].dtype == shuffled["i"].dtype
    assert out["o"].tolist() == ["k"] * 18 and out["i"].equals(shuffled["i"])
    sorted_out = out.loc[frame.index]
    want = [1, 1, 3, 3, 3, 6, NAN, 2, 2, 4, NAN, NAN, 5, NAN, NAN, NAN, 9, NAN]
    assert same(sorted_out["x"], want) and same(sorted_out["f"], np.asarray(want, dtype=np.float32))
    assert rec.filled == {"x": 4, "f": 4, "i": 0} and rec.columns == ("x", "f", "i")


def test_the_record_adds_up_is_json_ready_and_is_printed(capsys):
    frame, u, s = one_unit([NAN, 1.0, NAN, 3.0, NAN, NAN, NAN, 7.0, NAN])
    frame["y"] = 1.0
    out, rec = fill_last_value(frame, u, s, ("x", "y"), MONTHLY)
    printed = capsys.readouterr().out
    assert printed.strip() == rec.summary_line()
    assert "C18.last_value_max_months = 2 months = 2 steps" in printed and "1 rows filled in 1 columns" in printed
    doc = rec.as_dict()
    assert json.loads(json.dumps(doc)) == doc
    assert doc["constant"] == {"C18.last_value_max_months": 2} and doc["rule"] == "J2d"
    assert doc["columns"]["x"] == {"missing": 6, "filled": 1, "gap_longer": 3, "head": 1, "tail": 1,
                                   "left_to_r30": 5}
    assert doc["columns"]["y"]["missing"] == 0 and doc["filled_rows"] == 1 and doc["columns_filled"] == 1
    for c in rec.columns:
        e = doc["columns"][c]
        assert e["missing"] == e["filled"] + e["gap_longer"] + e["head"] + e["tail"]
    assert isinstance(rec, LastValueRecord)


def test_an_empty_frame_and_no_tree_features():
    empty = pd.DataFrame({"x": np.zeros(0)})
    out, rec = fill_last_value(empty, np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64), ("x",), MONTHLY)
    assert len(out) == 0 and rec.rows == 0 and rec.filled == {"x": 0}
    frame, u, s = one_unit([1.0, NAN, 3.0])
    out, rec = fill_last_value(frame, u, s, (), MONTHLY)
    assert same(out["x"], frame["x"]) and rec.columns == ()


# ---------------------------------------------------------------------------------------------------
# refusals
def test_refusals():
    frame, u, s = one_unit([1.0, NAN, 3.0])
    refused("J2d", fill_last_value, frame["x"], u, s, ("x",), MONTHLY)
    twice = pd.concat([frame[["x"]], frame[["x"]]], axis=1)
    refused("J2d", fill_last_value, twice, u, s, ("x",), MONTHLY)
    refused("J2d", fill_last_value, frame, u[:2], s, ("x",), MONTHLY)
    refused("J2d", fill_last_value, frame, u, s[:2], ("x",), MONTHLY)
    refused("J2d", fill_last_value, frame, u, s + 0.5, ("x",), MONTHLY)
    refused("G-CALENDAR", fill_last_value, frame, u, np.array([1, 1, 2]), ("x",), MONTHLY)
    refused("J2d", fill_last_value, frame, u, s, "x", MONTHLY)
    refused("J2d", fill_last_value, frame, u, s, ("x", "x"), MONTHLY)
    refused("J2d", fill_last_value, frame, u, s, ("x", ""), MONTHLY)
    assert "not columns of the frame" in refused("J2d", fill_last_value, frame, u, s, ("x", "nope"), MONTHLY)
    text = frame.assign(t=["a", "b", "c"])
    assert "numeric" in refused("J2d", fill_last_value, text, u, s, ("t",), MONTHLY)
    inf = frame.assign(x=[1.0, np.inf, 3.0])
    refused("G-SENTINEL", fill_last_value, inf, u, s, ("x",), MONTHLY)
    refused("J2d", fill_last_value, frame, u, s, ("x",), NS(kind="static"))


def test_the_internal_proof_refuses_a_broken_source(monkeypatch):
    """A planted fault in the source lookup (each fill reads the NEXT value instead of the previous
    one) is caught by the proof every fill carries."""
    real_searchsorted = np.searchsorted

    def shifted(a, v, *args, **kwargs):
        return real_searchsorted(a, v, *args, **kwargs) + 1
    monkeypatch.setattr(LV.np, "searchsorted", shifted)
    frame, u, s = one_unit([1.0, 2.0, NAN, 4.0, 5.0, 6.0])
    msg = refused("J2d", fill_last_value, frame, u, s, ("x",), MONTHLY)
    assert "internal" in msg


# ---------------------------------------------------------------------------------------------------
# a brute-force reference and the leak proofs on random panels
def reference(units, steps, values, max_steps):
    """Loops, written from the ruling: fill a missing row when its unit has a value before and after
    it with a gap of at most max_steps calendar steps; the fill is the value just before."""
    out = values.copy()
    for unit in np.unique(units):
        rows = np.flatnonzero(units == unit)
        rows = rows[np.argsort(steps[rows], kind="stable")]
        have = [r for r in rows if not np.isnan(values[r])]
        for r in rows:
            if not np.isnan(values[r]):
                continue
            before = [h for h in have if steps[h] < steps[r]]
            after = [h for h in have if steps[h] > steps[r]]
            if not before or not after:
                continue
            a, b = before[-1], after[0]
            if steps[b] - steps[a] - 1 <= max_steps:
                out[r] = values[a]
    return out


def random_panel(seed, n_units=25, n_steps=40, drop=0.08):
    rng = np.random.default_rng(seed)
    units, steps, values = [], [], []
    for unit in range(n_units):
        v = rng.normal(size=n_steps).round(3)
        k = 0
        while k < n_steps:                                  # gaps of 1 to 5 steps at random places
            if rng.random() < 0.15:
                length = int(rng.integers(1, 6))
                v[k:k + length] = np.nan
                k += length
            k += 1
        if unit % 7 == 3:
            v[:] = np.nan                                   # a unit with no value at all
        keep = rng.random(n_steps) >= drop                  # rows missing from the frame altogether
        st = np.arange(100, 100 + n_steps)[keep]
        units.append(np.full(len(st), unit * 3 + 11)), steps.append(st), values.append(v[keep])
    units, steps, values = np.concatenate(units), np.concatenate(steps), np.concatenate(values)
    perm = rng.permutation(len(units))
    return units[perm], steps[perm], values[perm]


@pytest.mark.parametrize("seed", range(6))
def test_matches_the_reference_on_random_panels(seed):
    units, steps, values = random_panel(seed)
    frame = pd.DataFrame({"x": values, "x32": values.astype(np.float32)})
    for cadence, max_steps in ((MONTHLY, 2), (ANNUAL, 0), (COMPOSITE, 7)):
        out, rec = fill_last_value(frame, units, steps, ("x", "x32"), cadence)
        want = reference(units, steps, values, max_steps)
        assert same(out["x"], want)
        assert same(out["x32"], reference(units, steps, values.astype(np.float32), max_steps))
        filled = ~np.isnan(want) & np.isnan(values)
        assert rec.filled["x"] == int(filled.sum()) and rec.missing["x"] == int(np.isnan(values).sum())
        # every filled value is the same unit's most recent earlier value, at most the maximum back
        for r in np.flatnonzero(filled):
            mine = (units == units[r]) & (steps < steps[r]) & ~np.isnan(values)
            src = np.flatnonzero(mine)[np.argmax(steps[mine])]
            assert out["x"].iloc[r] == values[src] and 0 < steps[r] - steps[src] <= max_steps


@pytest.mark.parametrize("seed", range(4))
def test_a_planted_later_value_never_enters(seed):
    """Plant 1e9 in EVERY later step that holds a value, for every cut T: nothing at or before T moves,
    and no output at or before T is 1e9 (the planted values sit after T only)."""
    units, steps, values = random_panel(seed + 100)
    frame = pd.DataFrame({"x": values})
    base, _ = fill_last_value(frame, units, steps, ("x",), MONTHLY)
    for cut in range(100, 140, 3):
        planted = values.copy()
        later = (steps > cut) & ~np.isnan(values)
        planted[later] = PLANT
        out, rec = fill_last_value(pd.DataFrame({"x": planted}), units, steps, ("x",), MONTHLY)
        upto = steps <= cut
        assert same(out["x"][upto], base["x"][upto]), cut
        assert not (out["x"][upto] == PLANT).any()
        # presence is the same, so the same rows are filled; after T a fill may read a planted value
        # only from an EARLIER step that itself holds the plant
        assert rec.filled["x"] == int((~np.isnan(base["x"]) & np.isnan(values)).sum())
        took_plant = (out["x"].to_numpy() == PLANT) & ~later
        for r in np.flatnonzero(took_plant):
            mine = (units == units[r]) & (steps < steps[r]) & later
            assert mine.any() and steps[r] > cut


def test_every_gap_ignores_a_planted_value_just_after_it():
    """Each short gap is followed by planted 1e9 values: every fill is the value before the gap."""
    v = [3.0, NAN, PLANT, 5.0, NAN, NAN, PLANT, PLANT, 7.0, NAN, PLANT]
    frame, u, s = one_unit(v)
    out, rec = fill_last_value(frame, u, s, ("x",), MONTHLY)
    assert same(out["x"], [3.0, 3.0, PLANT, 5.0, 5.0, 5.0, PLANT, PLANT, 7.0, 7.0, PLANT])
    assert rec.filled["x"] == 4
