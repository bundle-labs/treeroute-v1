"""io science: 1:1 joins (G-JOIN runtime, D31) and the column-set / missing-file checks (G-JOIN,
G-CLOSED, G-MISSING). Synthetic frames, every branch."""

import numpy as np
import pandas as pd
import pytest

from treeroute.errors import RefusedError
from treeroute.io.checks import MissingFileReport, check_column_set, check_missing_files
from treeroute.io.joins import JoinReport, join_one_to_one


def _left():
    return pd.DataFrame({"u": ["a", "b", "c", "a"], "t": [1, 1, 1, 2], "x": [1.0, 2.0, 3.0, 4.0]},
                        index=[40, 30, 20, 10])


def test_left_rows_order_and_index_are_kept_and_unmatched_rows_counted():
    left = _left()
    right = pd.DataFrame({"t": [2, 1, 1], "u": ["a", "c", "a"], "z": [9.0, 7.0, 5.0]})
    before_l, before_r = left.copy(), right.copy()
    out, rep = join_one_to_one(left, right, ("u", "t"), "drivers")
    assert out.index.tolist() == [40, 30, 20, 10]
    assert out[["u", "t", "x"]].equals(left)
    assert out["z"].tolist()[0] == 5.0 and np.isnan(out["z"].iloc[1]) and out["z"].tolist()[2:] == [7.0, 9.0]
    assert rep == JoinReport(what="drivers", left_rows=4, right_rows=3, out_rows=4, unmatched_left=1)
    assert list(out.columns) == ["u", "t", "x", "z"]
    pd.testing.assert_frame_equal(left, before_l)
    pd.testing.assert_frame_equal(right, before_r)


def test_left_key_values_and_dtypes_are_restored():
    left = pd.DataFrame({"k": np.array([1, 2], dtype=np.int32), "x": [0.0, 0.0]})
    right = pd.DataFrame({"k": np.array([2.0, 1.0]), "z": [5.0, 6.0]})
    out, _ = join_one_to_one(left, right, ("k",), "mixed numeric keys")
    assert out["k"].dtype == np.int32 and out["z"].tolist() == [6.0, 5.0]


def test_extension_key_dtypes_come_back_unchanged():
    left = pd.DataFrame({"k": pd.Categorical(["a", "b"]), "x": [1.0, 2.0]}, index=[7, 3])
    right = pd.DataFrame({"k": ["b", "a"], "z": [5.0, 6.0]})
    out, _ = join_one_to_one(left, right, ("k",), "categorical key")
    assert isinstance(out["k"].dtype, pd.CategoricalDtype) and out["k"].tolist() == ["a", "b"]
    assert out["z"].tolist() == [6.0, 5.0] and out.index.tolist() == [7, 3]
    left = pd.DataFrame({"k": pd.array([1, 2], dtype="Int64"), "x": [1.0, 2.0]})
    right = pd.DataFrame({"k": [2, 1], "z": [5.0, 6.0]})
    out, _ = join_one_to_one(left, right, ("k",), "nullable integer key")
    assert str(out["k"].dtype) == "Int64" and out["z"].tolist() == [6.0, 5.0]


def test_numbers_held_as_objects_against_text_are_refused():
    left = pd.DataFrame({"k": pd.Series(["1", "2"], dtype=object), "x": [1.0, 2.0]})
    right = pd.DataFrame({"k": pd.Series([1, 2], dtype=object), "z": [5.0, 6.0]})
    with pytest.raises(RefusedError, match="not numeric on the left"):
        join_one_to_one(left, right, ("k",), "text vs object numbers")
    # numbers held as objects on both sides, or against a numeric dtype, still join
    both = pd.DataFrame({"k": pd.Series([2, 1], dtype=object), "x": [0.0, 0.0]})
    out, rep = join_one_to_one(both, right, ("k",), "object numbers")
    assert out["z"].tolist() == [6.0, 5.0] and rep.unmatched_left == 0
    out, rep = join_one_to_one(pd.DataFrame({"k": [1, 2]}), right, ("k",), "int vs object numbers")
    assert out["z"].tolist() == [5.0, 6.0] and rep.unmatched_left == 0
    # a categorical of numbers is numeric, a categorical of text is not
    cat_num = pd.DataFrame({"k": pd.Categorical([1, 2]), "x": [0.0, 0.0]})
    with pytest.raises(RefusedError, match="on the left"):
        join_one_to_one(cat_num, pd.DataFrame({"k": ["1", "2"], "z": [0.0, 0.0]}), ("k",), "cat num vs text")


def test_an_indicator_name_already_in_use_does_not_collide():
    left = pd.DataFrame({"k": [1, 2], "_join_indicator": ["p", "q"]})
    right = pd.DataFrame({"k": [1], "z": [3.0]})
    out, rep = join_one_to_one(left, right, ("k",), "indicator")
    assert out["_join_indicator"].tolist() == ["p", "q"] and rep.unmatched_left == 1


@pytest.mark.parametrize("side", ["left", "right"])
def test_duplicate_keys_on_either_side_are_refused(side):
    left, right = _left(), pd.DataFrame({"u": ["a", "b"], "t": [1, 1], "z": [1.0, 2.0]})
    if side == "left":
        left = pd.concat([left, left.iloc[:1]])
    else:
        right = pd.concat([right, right.iloc[:1]])
    with pytest.raises(RefusedError, match="share a key"):
        join_one_to_one(left, right, ("u", "t"), "dups")


def test_other_refusals():
    left = _left()
    right = pd.DataFrame({"u": ["a"], "t": [1], "z": [1.0]})
    with pytest.raises(RefusedError, match="NaN key"):
        join_one_to_one(left, pd.DataFrame({"u": [None], "t": [1], "z": [1.0]}), ("u", "t"), "nan")
    with pytest.raises(RefusedError, match="NaN key"):
        join_one_to_one(pd.DataFrame({"u": ["a"], "t": [np.nan]}), right, ("u", "t"), "nan")
    with pytest.raises(RefusedError, match="no key column"):
        join_one_to_one(left, right.drop(columns=["t"]), ("u", "t"), "absent")
    with pytest.raises(RefusedError, match="numeric on the left .* not numeric on the right"):
        join_one_to_one(left, right.assign(t=["1"]), ("u", "t"), "text vs number")
    with pytest.raises(RefusedError, match="collide"):
        join_one_to_one(left, right.assign(x=[0.0]), ("u", "t"), "collision")
    with pytest.raises(RefusedError, match="non-empty list"):
        join_one_to_one(left, right, (), "no keys")
    with pytest.raises(RefusedError, match="non-empty list"):
        join_one_to_one(left, right, ("u", "u"), "repeated key")
    with pytest.raises(RefusedError, match="not one string"):
        join_one_to_one(left, right, "u", "string key")
    with pytest.raises(RefusedError, match="more than once"):
        join_one_to_one(pd.DataFrame([[1, 2]], columns=["u", "u"]), right, ("u",), "twice")
    with pytest.raises(RefusedError, match="label"):
        join_one_to_one(left, right, ("u", "t"), "")
    with pytest.raises(RefusedError, match="DataFrame"):
        join_one_to_one(left, {"u": []}, ("u",), "not a frame")


# ---------------------------------------------------------------------------------------------------
def test_column_set_equal_in_any_order_passes():
    assert check_column_set(("b", "a", "c"), ("a", "b", "c"), "tbl") is None


def test_column_set_names_every_missing_and_extra_column():
    with pytest.raises(RefusedError) as info:
        check_column_set(("a", "x", "y"), ("a", "b", "c"), "tbl")
    text = str(info.value)
    assert "['b', 'c']" in text and "['x', 'y']" in text and "G-JOIN" in text


def test_column_set_refusals():
    with pytest.raises(RefusedError, match="more than once"):
        check_column_set(("a", "a"), ("a",), "tbl")
    with pytest.raises(RefusedError, match="not one string"):
        check_column_set("ab", ("a", "b"), "tbl")
    with pytest.raises(RefusedError, match="non-empty strings"):
        check_column_set(("a", 3), ("a",), "tbl")
    with pytest.raises(RefusedError, match="non-empty name"):
        check_column_set(("a",), ("a",), "")


def test_missing_files_all_found():
    exp = {("g1", 2001), ("g1", 2002)}
    rep = check_missing_files(exp, set(exp), {}, "store")
    assert rep == MissingFileReport(store="store", missing=(), absent_by_fact=(), unexpected=())


def test_missing_files_in_a_declared_absent_group_are_reported_not_refused():
    exp = {("g1", 2001), ("g2", 2001), ("g2", 2002)}
    found = {("g1", 2001), ("g3", 2001)}
    rep = check_missing_files(exp, found, {"g2": "no coverage"}, "store")
    assert rep.missing == (("g2", 2001), ("g2", 2002)) == rep.absent_by_fact
    assert rep.unexpected == (("g3", 2001),)


def test_a_missing_file_outside_the_absent_groups_stops_the_run():
    exp = {("g1", 2001), ("g2", 2001)}
    with pytest.raises(RefusedError, match="G-MISSING") as info:
        check_missing_files(exp, {("g1", 2001)}, {"g9": "other"}, "store")
    assert "('g2', 2001)" in str(info.value)


def test_files_present_for_a_declared_absent_group_are_not_refused_and_not_reported():
    # current behaviour, owner decision pending (refuse, flag or allow): the found (g2, 2001) file of
    # a declared-absent group appears in no field, so a stale absent_groups fact is invisible here
    exp = {("g2", 2001), ("g2", 2002)}
    rep = check_missing_files(exp, {("g2", 2001)}, {"g2": "partly absent"}, "store")
    assert rep.missing == rep.absent_by_fact == (("g2", 2002),)
    assert rep.unexpected == ()
    rep = check_missing_files(exp, set(exp), {"g2": "stale fact"}, "store")
    assert rep == MissingFileReport(store="store", missing=(), absent_by_fact=(), unexpected=())


def test_missing_file_input_checks():
    assert check_missing_files({("g", np.int64(3))}, {("g", 3)}, {}, "s").missing == ()
    for bad in ({("g", "2001")}, {("g", True)}, {("g", 1, 2)}, {("", 1)}, {"g2001"}):
        with pytest.raises(RefusedError, match="pairs"):
            check_missing_files(bad, set(), {}, "s")
    with pytest.raises(RefusedError, match="reason"):
        check_missing_files(set(), set(), {"g": ""}, "s")
    with pytest.raises(RefusedError, match="mapping"):
        check_missing_files(set(), set(), ["g"], "s")
    with pytest.raises(RefusedError, match="non-empty name"):
        check_missing_files(set(), set(), {}, "")
