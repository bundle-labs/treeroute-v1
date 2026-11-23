"""io science: sentinel masking at read (G-SENTINEL read, D30). Synthetic frames, every branch."""

from enum import Enum
from types import SimpleNamespace as NS

import numpy as np
import pandas as pd
import pytest

from treeroute.errors import RefusedError
from treeroute.io.sentinel import SentinelReport, mask_sentinels

PANEL_FILLS = (-32768, -32767, -2 ** 31, -2 ** 31 + 1)  # a store fact in the tests, never in the engine


def facts(role="driver", fills=PANEL_FILLS, optout=False):
    return NS(role=role, fill_values=fills, near_sentinel_optout=optout)


class Role(Enum):  # stands in for the proposed common.Role
    DRIVER = "driver"
    KEY_UNIT = "key_unit"


def test_declared_fills_and_huge_values_are_masked_in_float_columns():
    f32 = np.array([1.5, -32768, -2 ** 31, np.nan, 9.96921e36, -np.inf, 2.0], dtype=np.float32)
    frame = pd.DataFrame({"x": f32})
    out, rep = mask_sentinels(frame, {"x": facts()})
    assert out["x"].dtype == np.float32
    assert np.isnan(out["x"].to_numpy()).tolist() == [False, True, True, True, True, True, False]
    assert rep.masked == {"x": 4}  # the NaN was already missing and is not counted
    assert isinstance(rep, SentinelReport)


def test_a_fill_rounded_by_a_float32_writer_is_still_masked():
    # -2^31 + 1 cannot be held in float32; a writer stores it as -2^31
    frame = pd.DataFrame({"x": np.array([-2 ** 31 + 1, 3.0], dtype=np.float32)})
    out, rep = mask_sentinels(frame, {"x": facts(fills=(-2 ** 31 + 1,))})
    assert rep.masked == {"x": 1} and np.isnan(out["x"].iloc[0])
    # a non-representable decimal fill in float32 matches in the column's own type
    frame = pd.DataFrame({"x": np.array([-9999.9, 1.0], dtype=np.float32)})
    out, rep = mask_sentinels(frame, {"x": facts(fills=(-9999.9,))})
    assert rep.masked == {"x": 1}
    # a fill too large for float16 does not overflow into a false match
    frame = pd.DataFrame({"x": np.array([1.0, -np.inf], dtype=np.float16)})
    out, rep = mask_sentinels(frame, {"x": facts(fills=(-2 ** 31,))})
    assert rep.masked == {"x": 1}  # only the -inf, by magnitude


def test_integer_columns_are_cast_to_float_first():
    frame = pd.DataFrame({"n": np.array([5, -32768, 7], dtype=np.int64),
                          "clean": np.array([1, 2, 3], dtype=np.int32)})
    out, rep = mask_sentinels(frame, {"n": facts(), "clean": facts(fills=())})
    assert out["n"].dtype == np.float64 and np.isnan(out["n"].iloc[1]) and out["n"].iloc[0] == 5.0
    assert out["clean"].dtype == np.float64 and rep.masked == {"n": 1, "clean": 0}
    nullable = pd.DataFrame({"n": pd.array([1, None, -32767], dtype="Int64")})
    out, rep = mask_sentinels(nullable, {"n": facts()})
    assert out["n"].dtype == np.float64 and rep.masked == {"n": 1}
    assert np.isnan(out["n"].to_numpy()).tolist() == [False, True, True]


def test_pandas_extension_float_column():
    frame = pd.DataFrame({"x": pd.array([1.0, None, -32768.0], dtype="Float64")})
    out, rep = mask_sentinels(frame, {"x": facts()})
    assert rep.masked == {"x": 1} and np.isnan(out["x"].to_numpy(dtype=float)).tolist() == [False, True, True]


def test_near_sentinel_values_are_flagged_not_masked_unless_opted_out():
    derived = -2 ** 31 - (-32768)  # a sentinel combination no exact code catches
    frame = pd.DataFrame({"a": np.array([derived, 1.0, 2.0 ** 30, -2 ** 31]),
                          "b": np.array([derived, 1.0, 1.0, 1.0])})
    out, rep = mask_sentinels(frame, {"a": facts(), "b": facts(optout=True)})
    assert out["a"].iloc[0] == derived and np.isnan(out["a"].iloc[3])
    assert rep.flagged_near_sentinel == {"a": 2}  # derived and 2^30; the masked -2^31 is not flagged
    assert "b" not in rep.flagged_near_sentinel and rep.masked["b"] == 0


def test_key_columns_are_never_touched():
    frame = pd.DataFrame({"u": np.array([-32768, 1]), "g": ["x", "y"], "t": np.array([1, 2]),
                          "x": np.array([-32768.0, 1.0])})
    fx = {"u": NS(role=Role.KEY_UNIT), "g": NS(role="key_group"), "t": NS(role="key_time"),
          "x": NS(role=Role.DRIVER, fill_values=[-32768], near_sentinel_optout=False)}
    out, rep = mask_sentinels(frame, fx)
    assert out["u"].dtype == frame["u"].dtype and out["u"].tolist() == [-32768, 1]
    assert set(rep.masked) == {"x"} and set(rep.flagged_near_sentinel) == {"x"}


def test_the_target_is_never_masked_and_refused_when_it_holds_a_fill_or_huge_value():
    clean = pd.DataFrame({"y": np.array([0.1, np.nan, 0.3], dtype=np.float32)})
    out, rep = mask_sentinels(clean, {"y": facts(role="target")})
    assert out["y"].dtype == np.float32 and "y" not in rep.masked and rep.flagged_near_sentinel == {"y": 0}
    for bad in (-32768.0, 1e31):
        frame = pd.DataFrame({"y": np.array([0.1, bad])})
        with pytest.raises(RefusedError, match="D30"):
            mask_sentinels(frame, {"y": facts(role="target")})
    ints = pd.DataFrame({"y": np.array([1, 2])})
    out, _ = mask_sentinels(ints, {"y": facts(role="target")})
    assert out["y"].dtype == ints["y"].dtype


def test_a_target_twin_is_masked_like_any_measurement():
    frame = pd.DataFrame({"tw": np.array([-32768.0, 1.0])})
    out, rep = mask_sentinels(frame, {"tw": facts(role="target_twin")})
    assert rep.masked == {"tw": 1}


def test_non_numeric_measurement_columns():
    frame = pd.DataFrame({"s": ["a", "b"], "f": [True, False],
                          "d": np.array(["2010-01-01", "2010-01-02"], dtype="datetime64[ns]")})
    fx = {c: facts(fills=()) for c in frame.columns}
    out, rep = mask_sentinels(frame, fx)
    assert rep.masked == {"s": 0, "f": 0, "d": 0}
    assert out["s"].tolist() == ["a", "b"] and out["f"].dtype == bool
    with pytest.raises(RefusedError, match="not numeric but declares"):
        mask_sentinels(frame[["s"]], {"s": facts()})


def test_the_input_frame_is_not_changed_and_order_and_index_are_kept():
    frame = pd.DataFrame({"b": [-32768.0, 1.0], "a": [2.0, -32767.0]}, index=[10, 20])
    before = frame.copy()
    out, _ = mask_sentinels(frame, {"a": facts(), "b": facts()})
    pd.testing.assert_frame_equal(frame, before)
    assert list(out.columns) == ["b", "a"] and out.index.tolist() == [10, 20]


def test_refusals():
    frame = pd.DataFrame({"x": [1.0]})
    with pytest.raises(RefusedError, match="without facts"):
        mask_sentinels(frame, {})
    with pytest.raises(RefusedError, match="more than once"):
        mask_sentinels(pd.DataFrame([[1.0, 2.0]], columns=["x", "x"]), {"x": facts()})
    with pytest.raises(RefusedError, match="no 'fill_values'"):
        mask_sentinels(frame, {"x": NS(role="driver", near_sentinel_optout=False)})
    with pytest.raises(RefusedError, match="no 'role'"):
        mask_sentinels(frame, {"x": NS(fill_values=(), near_sentinel_optout=False)})
    with pytest.raises(RefusedError, match="NaN as a fill"):
        mask_sentinels(frame, {"x": facts(fills=(float("nan"),))})
    with pytest.raises(RefusedError, match="not a number"):
        mask_sentinels(frame, {"x": facts(fills=("-32768",))})
    with pytest.raises(RefusedError, match="DataFrame"):
        mask_sentinels({"x": [1.0]}, {"x": facts()})


def test_extra_facts_for_columns_not_read_are_fine():
    out, rep = mask_sentinels(pd.DataFrame({"x": [1.0]}), {"x": facts(), "unread": facts()})
    assert rep.masked == {"x": 0}
