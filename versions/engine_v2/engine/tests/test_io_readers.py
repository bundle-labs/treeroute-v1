"""treeroute.io boilerplate: path templates, file listing, raw column reads, footer statistics.

Synthetic parquet files are written under pytest's tmp folder. One read-only smoke test lists the real
monthly panel on D: and reads one footer (skipped when the store is not on this machine); it reads no
data page and writes nothing.
"""

import math
import os
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml

from conftest import ENGINE_DIR, run_python
from treeroute.io import listing as L
from treeroute.io import readers as R
from treeroute.io.listing import (AMBIGUOUS, NO_MATCH, WRONG_KIND, ListingError, TemplateError,
                                  compare_expected, expand, list_store, parse_template)
from treeroute.io.readers import ReadError, iter_columns, iter_footers, read_columns, read_footer

INT32_MIN = -2147483648


def touch(path, text="x"):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_parquet(path, table, **kw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, str(path), **kw)
    return path


def small_table(tag=0):
    return pa.table({
        "unit_id": pa.array(["u%d_a" % tag, "u%d_b" % tag, "u%d_c" % tag]),
        "y": pa.array([0.5, float("nan"), None], type=pa.float32()),
        "code": pa.array([INT32_MIN, None, 7], type=pa.int32()),
        "k": pa.array([1, 2, 3], type=pa.int64()),
    })


# ---------------------------------------------------------------------------------------------------
# parse_template
def test_key_names_follow_the_fixed_order_whatever_the_template_order():
    tpl = parse_template("x/year={year}/group={group}/m{month:02d}.parquet")
    assert tpl.key_names == ("group", "year", "month")
    assert parse_template("{group}.parquet").key_names == ("group",)
    assert parse_template("static/part-0.parquet").key_names == ()
    assert parse_template("a\\{group}\\{year}.parquet").key_names == ("group", "year")


@pytest.mark.parametrize("bad", [
    "data/{group.parquet",               # unbalanced
    "data/group}.parquet",               # unbalanced
    "data/{region}.parquet",             # not a key-role placeholder
    "data/{}.parquet",                   # positional
    "data/{0}.parquet",                  # positional
    "data/{group!r}.parquet",            # conversion
    "data/{group.name}.parquet",         # attribute access
    "data/{group[0]}.parquet",           # index access
    "data/{group:>8}.parquet",           # spec on a text placeholder
    "data/{year:x}.parquet",             # integer spec other than d / 0Nd
    "data/{year:4d}.parquet",            # width without zero padding
    "data/{year:{w}}.parquet",           # nested spec
    "data/{group}{year}.parquet",        # two placeholders touch
    "data//{group}.parquet",             # empty segment
    "data/{group}/",                     # names a folder
    "///x/{group}.parquet",              # three leading separators
    "data/{group}/../x_{year}.parquet",  # '..' below the store root
    "data/{group}/./x_{year}.parquet",   # '.' below the store root
    "{group}/..",                        # '..' as the file segment
    "",
    "   ",
])
def test_malformed_templates_raise(bad):
    with pytest.raises(TemplateError):
        parse_template(bad)


def test_dot_segments_below_the_store_root_are_refused_with_a_reason():
    with pytest.raises(TemplateError, match="below its store root"):
        parse_template("t/{group}/../x_{year}.parquet")


def test_dot_segments_above_the_store_root_are_kept_and_expand_and_list_agree(tmp_path):
    base = tmp_path / "pkg"
    base.mkdir()
    for tpl in ("./s/{group}_{year}.parquet", "../pkg/s/{group}_{year}.parquet"):
        path = expand(tpl, {"group": "g", "year": 1}, base=base)
        touch(path)
        lst = list_store(tpl, base=base)
        assert lst.found() == {("g", 1)} and lst.not_read == ()
        assert lst.path_of(("g", 1)) == path


def test_non_string_template_raises():
    with pytest.raises(TemplateError):
        parse_template(123)


def test_escaped_braces_are_literal_text(tmp_path):
    touch(tmp_path / "s" / "a{v}_1.parquet")
    lst = list_store("s/{group}{{v}}_{year}.parquet", base=tmp_path)
    assert lst.found() == {("a", 1)}


# ---------------------------------------------------------------------------------------------------
# expand
def test_expand_fills_placeholders_and_joins_a_relative_template_to_its_base(tmp_path):
    out = expand("data/group={group}/year={year}/m{month:02d}.parquet",
                 {"group": "grp_a", "year": 7, "month": 3}, base=tmp_path)
    assert out == Path(os.path.abspath(tmp_path)).as_posix() + "/data/group=grp_a/year=7/m03.parquet"
    assert "\\" not in out
    tpl = parse_template("{group}_{year}.parquet")
    assert tpl.expand({"group": "g", "year": np.int64(5)}, base=tmp_path).endswith("/g_5.parquet")


def test_expand_ignores_base_for_an_absolute_template(tmp_path):
    absolute = (tmp_path / "abs").as_posix() + "/{group}.parquet"
    assert expand(absolute, {"group": "g"}, base="elsewhere") == (tmp_path / "abs").as_posix() + "/g.parquet"


@pytest.mark.parametrize("values", [
    {"group": "g"},                                  # missing year
    {"group": "g", "year": 1, "month": 2},           # not in the template
    {"group": "", "year": 1},                        # empty text
    {"group": "a/b", "year": 1},                     # leaves the segment
    {"group": "..", "year": 1},
    {"group": 5, "year": 1},                         # text needs a string
    {"group": "g", "year": True},                    # bool is not an integer
    {"group": "g", "year": np.bool_(True)},          # nor is numpy bool (operator.index takes it)
    {"group": "g", "year": 1.0},                     # float is not an integer
    {"group": "g", "year": "1"},                     # string is not an integer
    {"group": "g", "year": -1},                      # negative
])
def test_expand_refuses_bad_values(tmp_path, values):
    with pytest.raises(TemplateError):
        expand("{group}_{year}.parquet", values, base=tmp_path)


def test_expand_refuses_a_value_that_would_not_read_back(tmp_path):
    # group 'a_b' with template {group}_{unit} would read back two ways
    with pytest.raises(TemplateError, match="read back"):
        expand("{group}_{unit}.parquet", {"group": "a_b", "unit": "c"}, base=tmp_path)
    assert expand("{group}_{unit}.parquet", {"group": "a", "unit": "c"}, base=tmp_path).endswith("/a_c.parquet")


def test_relative_template_without_base_raises():
    with pytest.raises(TemplateError, match="relative"):
        expand("data/{group}.parquet", {"group": "g"})
    with pytest.raises(TemplateError, match="relative"):
        list_store("data/{group}.parquet")


# ---------------------------------------------------------------------------------------------------
# list_store
def test_partitioned_layout_is_listed_and_everything_else_is_reported(tmp_path):
    base = tmp_path / "pkg"
    for g in ("grp_a", "grp_b"):
        for y in (1, 2):
            touch(base / "data" / "t" / ("group=%s" % g) / ("year=%d" % y) / "part-0.parquet")
    touch(base / "data" / "t" / "group=grp_a" / "year=2" / "part-1.parquet")   # a second part
    touch(base / "data" / "t" / "_SUCCESS")                                    # stray file
    (base / "data" / "t" / "group=grp_c" / "year=1").mkdir(parents=True)       # folder, no file
    (base / "data" / "t" / "group=grp_b" / "year=3" / "part-0.parquet").mkdir(parents=True)  # folder as file
    touch(base / "data" / "t" / "group=grp_b" / "year=x" / "part-0.parquet")   # year not an integer
    lst = list_store("data/t/group={group}/year={year}/part-0.parquet", base=base)

    assert lst.key_names == ("group", "year")
    assert lst.store_root == Path(os.path.abspath(base / "data" / "t")).as_posix()
    assert lst.store_root_exists
    assert [k for k, _ in lst.files] == [("grp_a", 1), ("grp_a", 2), ("grp_b", 1), ("grp_b", 2)]
    assert lst.path_of(("grp_a", 2)).endswith("/data/t/group=grp_a/year=2/part-0.parquet")
    kinds = {Path(e.path).relative_to(os.path.abspath(base)).as_posix(): e.kind for e in lst.not_read}
    assert kinds == {
        "data/t/_SUCCESS": NO_MATCH,
        "data/t/group=grp_a/year=2/part-1.parquet": NO_MATCH,
        "data/t/group=grp_b/year=3/part-0.parquet": WRONG_KIND,
        "data/t/group=grp_b/year=x": NO_MATCH,
    }
    assert [e.path for e in lst.not_read] == sorted(e.path for e in lst.not_read)


def test_flat_layout_reads_underscored_group_names(tmp_path):
    root = tmp_path / "store"
    for name in ("alpha_beta_gamma_monthly_1.parquet", "alpha_beta_gamma_monthly_2.parquet",
                 "x_monthly_10.parquet", "x_monthly_abc.parquet", "x_monthly_010.parquet",
                 "notes.txt"):
        touch(root / name)
    lst = list_store(root.as_posix() + "/{group}_monthly_{year}.parquet")
    assert lst.found() == {("alpha_beta_gamma", 1), ("alpha_beta_gamma", 2), ("x", 10)}
    assert sorted(Path(e.path).name for e in lst.not_read) == [
        "notes.txt", "x_monthly_010.parquet", "x_monthly_abc.parquet"]
    assert all(e.kind == NO_MATCH for e in lst.not_read)


def test_zero_padded_spec_reads_back_only_its_own_form(tmp_path):
    root = tmp_path / "s"
    touch(root / "g" / "m01.parquet")
    touch(root / "g" / "m12.parquet")
    touch(root / "g" / "m1.parquet")       # not the 02d form
    touch(root / "g" / "m123.parquet")     # 02d of 123 is '123': allowed
    lst = list_store("s/{group}/m{month:02d}.parquet", base=tmp_path)
    assert lst.found() == {("g", 1), ("g", 12), ("g", 123)}
    assert [Path(e.path).name for e in lst.not_read] == ["m1.parquet"]


def test_ambiguous_names_are_reported_not_guessed(tmp_path):
    touch(tmp_path / "s" / "a_b_c.parquet")
    touch(tmp_path / "s" / "a_b.parquet")
    lst = list_store("s/{group}_{unit}.parquet", base=tmp_path)
    assert lst.found() == {("a", "b")}
    (entry,) = lst.not_read
    assert entry.kind == AMBIGUOUS and entry.path.endswith("/a_b_c.parquet")
    assert "group='a'" in entry.detail and "group='a_b'" in entry.detail


def test_a_repeated_placeholder_must_agree(tmp_path):
    touch(tmp_path / "s" / "g=a" / "a_1.parquet")
    touch(tmp_path / "s" / "g=a" / "b_1.parquet")
    lst = list_store("s/g={group}/{group}_{year}.parquet", base=tmp_path)
    assert lst.found() == {("a", 1)}
    assert [Path(e.path).name for e in lst.not_read] == ["b_1.parquet"]


def test_letter_case_is_exact_on_every_platform(tmp_path):
    touch(tmp_path / "s" / "g" / "PART-0.parquet")
    lst = list_store("s/{group}/part-0.parquet", base=tmp_path)
    assert lst.found() == frozenset()
    assert [(Path(e.path).name, e.kind) for e in lst.not_read] == [("PART-0.parquet", NO_MATCH)]


def test_missing_store_root_lists_nothing_and_says_so(tmp_path):
    lst = list_store("nowhere/{group}_{year}.parquet", base=tmp_path)
    assert lst.files == () and lst.not_read == ()
    assert lst.store_root_exists is False


def test_store_root_that_is_a_file_is_reported(tmp_path):
    touch(tmp_path / "s")
    lst = list_store("s/{group}.parquet", base=tmp_path)
    assert lst.files == ()
    assert [(e.kind, Path(e.path).name) for e in lst.not_read] == [(WRONG_KIND, "s")]


def test_placeholder_in_the_first_segment_uses_the_base_as_store_root(tmp_path):
    base = tmp_path / "b"
    touch(base / "grp_a" / "f.parquet")
    lst = list_store("{group}/f.parquet", base=base)
    assert lst.store_root == Path(os.path.abspath(base)).as_posix()
    assert lst.found() == {("grp_a",)}


def test_single_file_template(tmp_path):
    touch(tmp_path / "data" / "static" / "part-0.parquet")
    lst = list_store("data/static/part-0.parquet", base=tmp_path)
    assert lst.key_names == () and lst.found() == {()}
    assert lst.path_of(()).endswith("/data/static/part-0.parquet")
    assert list_store("data/static/part-9.parquet", base=tmp_path).found() == frozenset()
    # a folder where the template names a file is reported, as below a placeholder, not refused
    folder = list_store("data/static", base=tmp_path)
    assert folder.files == () and folder.store_root_exists
    assert [(e.kind, Path(e.path).name) for e in folder.not_read] == [(WRONG_KIND, "static")]


def test_expand_and_list_agree(tmp_path):
    tpl = "d/grp={group}/{group}_{year}_{month:02d}.parquet"
    keys = [("g_1", 3, 1), ("g_1", 3, 11), ("h", 10, 2)]
    for g, y, m in keys:
        touch(expand(tpl, {"group": g, "year": y, "month": m}, base=tmp_path))
    lst = list_store(tpl, base=tmp_path)
    assert [k for k, _ in lst.files] == sorted(keys)
    assert lst.not_read == ()
    for key, path in lst.files:
        assert expand(tpl, dict(zip(lst.key_names, key)), base=tmp_path) == path


def test_listing_is_deterministic_and_serialisable(tmp_path):
    for g in ("b", "a", "c"):
        touch(tmp_path / "s" / ("%s_1.parquet" % g))
    first = list_store("s/{group}_{year}.parquet", base=tmp_path)
    second = list_store("s/{group}_{year}.parquet", base=tmp_path)
    assert first == second
    d = first.as_dict()
    assert d["key_names"] == ["group", "year"]
    assert [f[0] for f in d["files"]] == [["a", 1], ["b", 1], ["c", 1]]


def test_path_of_an_unknown_key_raises(tmp_path):
    lst = list_store("s/{group}.parquet", base=tmp_path)
    with pytest.raises(ListingError):
        lst.path_of(("zz",))


def test_path_of_takes_numpy_integers_and_refuses_bool_and_float(tmp_path):
    touch(tmp_path / "s" / "a_1.parquet")
    lst = list_store("s/{group}_{year}.parquet", base=tmp_path)
    assert lst.path_of(("a", np.int64(1))).endswith("/a_1.parquet")
    key, _ = lst.file_of((np.str_("a"), np.int32(1)))
    assert key == ("a", 1) and type(key[0]) is str and type(key[1]) is int
    for bad in (("a", True), ("a", 1.0), ("a", np.float64(1.0)), ("a", "1")):
        with pytest.raises(ListingError):
            lst.path_of(bad)  # a bare dict lookup would match True and 1.0 to 1


def test_listing_cache_is_not_data_and_duplicate_keys_are_refused(tmp_path):
    touch(tmp_path / "s" / "a_1.parquet")
    lst = list_store("s/{group}_{year}.parquet", base=tmp_path)
    assert "_index" not in lst.as_dict() and "_index" not in repr(lst)
    same = L.StoreListing(**{f: getattr(lst, f) for f in (
        "template", "path_template", "store_root", "store_root_exists", "key_names", "files",
        "not_read")})
    assert same == lst and hash(same) == hash(lst)
    with pytest.raises(ListingError, match="twice"):
        L.StoreListing(template="t", path_template="t", store_root=".", store_root_exists=True,
                       key_names=("group",), files=((("a",), "x"), (("a",), "y")), not_read=())


def test_lookups_scale_linearly_with_the_number_of_files():
    # 20,000 keys: a lookup that rebuilt a dict per call, or a list.count duplicate check, would
    # take minutes here; the cached index takes well under a second.
    import time
    files = tuple(((("g%03d" % (i // 200)), 2000 + i % 200), "p/%d" % i) for i in range(20000))
    lst = L.StoreListing(template="t", path_template="t", store_root=".", store_root_exists=True,
                         key_names=("group", "year"), files=files, not_read=())
    start = time.perf_counter()
    for key, path in files:
        assert lst.path_of(key) == path
    chosen = R._chosen(lst, [k for k, _ in files])
    assert chosen == list(files)
    assert time.perf_counter() - start < 10.0


# ---------------------------------------------------------------------------------------------------
# compare_expected
def test_expected_against_found_is_data(tmp_path):
    for g, y in (("a", 1), ("a", 2), ("b", 1), ("z", 9)):
        touch(tmp_path / "s" / ("%s_%d.parquet" % (g, y)))
    lst = list_store("s/{group}_{year}.parquet", base=tmp_path)
    cmp = compare_expected(lst, [("b", 1), ("a", 1), ("a", 2), ("b", 2), ("b", 2)])
    assert cmp.key_names == ("group", "year")
    assert cmp.expected_found == (("a", 1), ("a", 2), ("b", 1))
    assert cmp.missing == (("b", 2),)
    assert cmp.unexpected == (("z", 9),)
    assert cmp.as_dict()["missing"] == [["b", 2]]


def test_expected_with_no_files_at_all_is_still_data(tmp_path):
    lst = list_store("nowhere/{group}_{year}.parquet", base=tmp_path)
    cmp = compare_expected(lst, {("a", 1)})
    assert cmp.missing == (("a", 1),) and cmp.expected_found == () and cmp.unexpected == ()


def test_expected_keys_may_hold_numpy_values_as_a_target_table_gives_them(tmp_path):
    for g, y in (("a", 1), ("a", 2), ("b", 1)):
        touch(tmp_path / "s" / ("%s_%d.parquet" % (g, y)))
    lst = list_store("s/{group}_{year}.parquet", base=tmp_path)
    groups = np.array(["a", "a", "b", "b"])
    for dtype in (np.int64, np.int32):
        years = np.array([1, 2, 1, 3], dtype=dtype)
        cmp = compare_expected(lst, list(zip(groups, years)))
        assert cmp.expected_found == (("a", 1), ("a", 2), ("b", 1))
        assert cmp.missing == (("b", 3),) and cmp.unexpected == ()
        for key in cmp.expected_found + cmp.missing:
            assert type(key[0]) is str and type(key[1]) is int
    # expand and compare_expected accept the same values
    assert expand("s/{group}_{year}.parquet", {"group": groups[0], "year": np.int32(2)},
                  base=tmp_path) == lst.path_of(("a", 2))


@pytest.mark.parametrize("bad", [
    [("a",)],              # too short
    [("a", 1, 2)],         # too long
    [["a", 1]],            # not a tuple
    [(1, 1)],              # group must be text
    [("a", "1")],          # year must be an integer
    [("a", True)],         # bool is not an integer
    [("a", np.bool_(True))],
    [("a", 1.0)],          # float is not an integer
    [("a", np.float64(1.0))],
    [("a", -1)],           # negative, as expand refuses
    [("a/b", 1)],          # leaves its path segment, as expand refuses
    "a1",                  # a string, not a collection of keys
    5,                     # not a collection
])
def test_expected_keys_of_the_wrong_shape_raise(tmp_path, bad):
    lst = list_store("s/{group}_{year}.parquet", base=tmp_path)
    with pytest.raises(ListingError):
        compare_expected(lst, bad)


def test_listing_module_is_light():
    proc = run_python("""
import sys
import treeroute.io, treeroute.io.listing
print('HEAVY', [m for m in ('pyarrow', 'numpy', 'pandas') if m in sys.modules])
""")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "HEAVY []" in proc.stdout, proc.stdout


# ---------------------------------------------------------------------------------------------------
# read_columns / iter_columns
def _valid(arr):
    return arr.is_valid().to_numpy(zero_copy_only=False)


def test_values_come_back_exactly_as_stored(tmp_path):
    path = write_parquet(tmp_path / "f.parquet", small_table())
    t = read_columns(path, ["code", "y", "unit_id"])
    assert t.column_names == ["code", "y", "unit_id"]
    # types kept: no int -> float cast, no float64 widening
    assert t.schema.field("code").type == pa.int32()
    assert t.schema.field("y").type == pa.float32()
    # the sentinel is NOT masked; the null stays a null
    assert t.column("code").to_pylist() == [INT32_MIN, None, 7]
    # NaN stays a value (not a null) and the null stays a null
    y = t.column("y").combine_chunks()
    assert list(_valid(y)) == [True, True, False]
    bits = y.fill_null(0).to_numpy().view(np.uint32)
    want = np.array([0.5, np.nan], dtype=np.float32).view(np.uint32)
    assert bits[0] == want[0] and math.isnan(y[1].as_py())
    assert t.column("unit_id").to_pylist() == ["u0_a", "u0_b", "u0_c"]


def test_a_missing_column_is_refused_where_pyarrow_would_drop_it(tmp_path):
    path = write_parquet(tmp_path / "f.parquet", small_table())
    with pq.ParquetFile(str(path)) as pf:  # the pyarrow behaviour the reader guards against
        assert pf.read(columns=["k", "nope"]).column_names == ["k"]
    with pytest.raises(ReadError, match="nope") as info:
        read_columns(path, ["k", "nope"])
    assert str(path) in str(info.value) or path.as_posix() in str(info.value)


@pytest.mark.parametrize("columns", [[], "k", ["k", "k"], [""], [None], 5])
def test_bad_column_requests_are_refused(tmp_path, columns):
    path = write_parquet(tmp_path / "f.parquet", small_table())
    with pytest.raises(ReadError):
        read_columns(path, columns)


def test_a_file_that_is_not_parquet_raises_read_error_naming_it(tmp_path):
    bad = touch(tmp_path / "bad.parquet", "not parquet")
    with pytest.raises(ReadError, match="bad.parquet"):
        read_columns(bad, ["k"])
    with pytest.raises(ReadError, match="bad.parquet"):
        read_footer(bad)
    with pytest.raises(ReadError, match="absent.parquet"):
        read_columns(tmp_path / "absent.parquet", ["k"])


def _store(tmp_path, keys):
    for g, y in keys:
        write_parquet(tmp_path / "s" / ("group=%s" % g) / ("year=%d" % y) / "part-0.parquet",
                      small_table(y))
    return list_store("s/group={group}/year={year}/part-0.parquet", base=tmp_path)


def test_iter_columns_reads_one_file_per_step_only_when_asked(tmp_path, monkeypatch):
    lst = _store(tmp_path, [("b", 1), ("a", 2), ("a", 1)])
    calls = []
    real = R.read_columns

    def counting(path, columns):
        calls.append(path)
        return real(path, columns)

    monkeypatch.setattr(R, "read_columns", counting)
    it = iter_columns(lst, ["k", "unit_id"])
    assert calls == []
    key, table = next(it)
    assert key == ("a", 1) and len(calls) == 1
    assert table.column_names == ["k", "unit_id"] and table.column("unit_id")[0].as_py() == "u1_a"
    rest = list(it)
    assert [k for k, _ in rest] == [("a", 2), ("b", 1)] and len(calls) == 3


def test_iter_columns_follows_the_keys_asked_and_checks_them_before_reading(tmp_path, monkeypatch):
    lst = _store(tmp_path, [("a", 1), ("a", 2)])
    got = [k for k, _ in iter_columns(lst, ["k"], keys=[("a", 2), ("a", 1)])]
    assert got == [("a", 2), ("a", 1)]
    monkeypatch.setattr(R, "read_columns", lambda *a: pytest.fail("a file was read"))
    with pytest.raises(ReadError, match="no file"):
        iter_columns(lst, ["k"], keys=[("a", 1), ("zz", 9)])
    with pytest.raises(ReadError, match="more than once"):
        iter_columns(lst, ["k"], keys=[("a", 1), ("a", 1)])
    with pytest.raises(ReadError, match="one key"):
        iter_columns(lst, ["k"], keys=("a", 1))  # one key tuple instead of a list of keys
    with pytest.raises(ReadError):
        iter_columns(lst, ["k", "k"])
    for unordered in ({("a", 1)}, frozenset({("a", 1)}), {("a", 1): 0}, {("a", 1): 0}.keys()):
        with pytest.raises(ReadError, match="fixed order"):
            iter_columns(lst, ["k"], keys=unordered)
    for bad in ([("a", True)], [("a", 1.0)], [("a",)], [["a", 1]], (("a", 1), "x"), 5):
        with pytest.raises(ReadError):
            iter_columns(lst, ["k"], keys=bad)


def test_keys_may_be_a_tuple_of_key_tuples_such_as_expected_found(tmp_path):
    lst = _store(tmp_path, [("a", 1), ("a", 2), ("b", 1)])
    cmp = compare_expected(lst, [("b", 1), ("a", 2), ("c", 9)])
    assert cmp.expected_found == (("a", 2), ("b", 1))
    got = list(iter_footers(lst, keys=cmp.expected_found))
    assert [k for k, _ in got] == [("a", 2), ("b", 1)] and all(f.num_rows == 3 for _, f in got)
    assert [k for k, _ in iter_columns(lst, ["k"], keys=(("b", 1),))] == [("b", 1)]
    # an empty tuple is an empty collection when the listing has placeholders
    assert list(iter_footers(lst, keys=())) == []
    assert list(iter_footers(lst, keys=compare_expected(lst, [("c", 9)]).expected_found)) == []


def test_numpy_keys_find_their_file_and_come_back_as_the_listing_holds_them(tmp_path):
    lst = _store(tmp_path, [("a", 1), ("a", 2)])
    got = [k for k, _ in iter_columns(lst, ["k"], keys=[(np.str_("a"), np.int64(2)),
                                                           ("a", np.int32(1))])]
    assert got == [("a", 2), ("a", 1)]
    assert all(type(k[0]) is str and type(k[1]) is int for k in got)
    with pytest.raises(ReadError, match="more than once"):
        iter_columns(lst, ["k"], keys=[("a", 1), ("a", np.int64(1))])


def test_empty_tuple_keys_are_refused_for_a_listing_without_placeholders(tmp_path):
    write_parquet(tmp_path / "one" / "part-0.parquet", small_table())
    lst = list_store("one/part-0.parquet", base=tmp_path)
    with pytest.raises(ReadError, match="ambiguous"):
        iter_footers(lst, keys=())
    assert [k for k, _ in iter_footers(lst, keys=[()])] == [()]
    assert [k for k, _ in iter_footers(lst, keys=((),))] == [()]
    assert list(iter_footers(lst, keys=[])) == []


def test_files_are_released_after_reading(tmp_path):
    path = write_parquet(tmp_path / "f.parquet", small_table())
    read_columns(path, ["k"])
    read_footer(path)
    moved = tmp_path / "g.parquet"
    os.rename(str(path), str(moved))  # Windows refuses to rename a file that is still open
    os.rename(str(moved), str(path))


# ---------------------------------------------------------------------------------------------------
# read_footer / iter_footers
def test_footer_counts_and_ranges_combine_row_groups(tmp_path):
    table = pa.table({
        "a": pa.array([5, None, -3, 9, None, 1], type=pa.int32()),
        "f": pa.array([1.5, float("nan"), -2.0, None, 4.0, 0.0], type=pa.float64()),
        "s": pa.array(["m", "b", None, "z", "c", "d"]),
        "empty": pa.array([None] * 6, type=pa.float32()),
    })
    path = write_parquet(tmp_path / "f.parquet", table, row_group_size=2)
    ft = read_footer(path)
    assert ft.num_rows == 6 and ft.row_group_rows == (2, 2, 2)
    assert ft.names == ("a", "f", "s", "empty")
    a = ft.column("a")
    assert (a.null_count, a.min, a.max) == (2, -3, 9)
    assert a.physical_type == "INT32" and a.arrow_type == "int32"
    assert a.row_groups_with_null_count == 3 and a.row_groups_with_min_max == 3
    f = ft.column("f")
    assert f.null_count == 1          # the NaN is a value, not a null
    assert (f.min, f.max) == (-2.0, 4.0)  # pyarrow's writer leaves NaN out of min/max
    s = ft.column("s")
    assert (s.null_count, s.min, s.max) == (1, "b", "z") and s.logical_type == "STRING"
    e = ft.column("empty")
    assert e.null_count == 6 and e.min is None and e.max is None
    assert e.row_groups_with_min_max == 0 and e.row_groups_without_values == 3
    assert a.row_groups_without_values == 0
    assert "parquet" in (ft.created_by or "").lower()
    with pytest.raises(ReadError):
        ft.column("nope")


def test_an_all_null_row_group_keeps_the_range_of_the_others(tmp_path):
    # a column that starts late: its first row group is all null, so pyarrow records no min/max
    # there; the other row groups still give the column's range
    table = pa.table({
        "late": pa.array([None, None, 3, 1, 7, None], type=pa.int32()),
        "mid": pa.array([2.0, 4.0, None, None, -1.0, 8.0], type=pa.float64()),
        "lst": pa.array([None, None, [2], [None], [], [5, 6]], type=pa.list_(pa.int64())),
    })
    path = write_parquet(tmp_path / "f.parquet", table, row_group_size=2)
    with pq.ParquetFile(str(path)) as pf:  # the pyarrow behaviour the combining rule answers
        s = pf.metadata.row_group(0).column(0).statistics
        assert s.null_count == 2 and not s.has_min_max
    ft = read_footer(path)
    late = ft.column("late")
    assert (late.null_count, late.min, late.max) == (3, 1, 7)
    assert (late.row_groups_with_min_max, late.row_groups_without_values) == (2, 1)
    mid = ft.column("mid")
    assert (mid.null_count, mid.min, mid.max) == (2, -1.0, 8.0)
    assert (mid.row_groups_with_min_max, mid.row_groups_without_values) == (2, 1)
    lst = ft.column("lst.list.element")  # nested: null_count is compared with num_values, not rows
    assert (lst.min, lst.max) == (2, 6) and lst.row_groups_without_values == 1


def test_a_file_without_rows_has_counts_but_no_range(tmp_path):
    path = write_parquet(tmp_path / "e.parquet", pa.table({"x": pa.array([], type=pa.int32())}))
    ft = read_footer(path)
    assert ft.num_rows == 0
    x = ft.column("x")
    assert x.null_count == 0 and x.min is None and x.max is None
    assert x.row_groups_with_null_count == 0 and x.row_groups_without_values == len(ft.row_group_rows)


def test_a_pandas_index_column_is_in_the_footer_but_read_only_when_asked(tmp_path):
    # the fact behind an owner question: does '__index_level_0__' count as a store column?
    pd = pytest.importorskip("pandas")
    path = tmp_path / "pd.parquet"
    pd.DataFrame({"v": [1.0, np.nan, 3.0]}, index=[10, 20, 30]).to_parquet(str(path))
    ft = read_footer(path)
    assert ft.names == ("v", "__index_level_0__")
    assert ft.column("v").null_count == 1  # pandas writes NaN as null
    assert read_columns(path, ["v"]).column_names == ["v"]
    assert read_columns(path, ["__index_level_0__"]).column("__index_level_0__").to_pylist() == [10, 20, 30]
    ranged = tmp_path / "pd_range.parquet"
    pd.DataFrame({"v": [1.0, 2.0]}).to_parquet(str(ranged))
    assert read_footer(ranged).names == ("v",)  # a plain range index is not stored as a column


def test_footer_without_statistics_says_none(tmp_path):
    path = write_parquet(tmp_path / "f.parquet", small_table(), write_statistics=False)
    col = read_footer(path).column("k")
    assert col.null_count is None and col.min is None and col.max is None
    assert col.row_groups_with_null_count == 0 and col.row_groups_with_min_max == 0


def test_statistics_missing_in_one_row_group_give_none(tmp_path):
    # a footer-only file (_metadata) whose first row group has statistics and whose second has none
    table = pa.table({"k": pa.array([1, 2, 3, 4], type=pa.int64())})
    write_parquet(tmp_path / "p0.parquet", table.slice(0, 2), write_statistics=True)
    write_parquet(tmp_path / "p1.parquet", table.slice(2, 2), write_statistics=False)
    md = pq.read_metadata(str(tmp_path / "p0.parquet"))
    md.append_row_groups(pq.read_metadata(str(tmp_path / "p1.parquet")))
    md.write_metadata_file(str(tmp_path / "_metadata"))
    ft = read_footer(tmp_path / "_metadata")
    assert ft.num_rows == 4 and ft.row_group_rows == (2, 2)
    col = ft.column("k")
    assert col.row_groups_with_null_count == 1 and col.row_groups_with_min_max == 1
    assert col.row_groups_without_values == 0  # not recorded is not the same as all null
    assert col.null_count is None and col.min is None and col.max is None


def test_a_nan_in_any_row_group_statistic_makes_the_combined_value_nan():
    assert math.isnan(R._combine([1.0, float("nan"), 3.0], min))
    assert R._combine([3, 1, 2], min) == 1 and R._combine([3, 1, 2], max) == 3


def test_footer_read_never_touches_a_data_page(tmp_path):
    n = 5000
    table = pa.table({"k": pa.array(np.arange(n, dtype=np.int64)),
                      "v": pa.array(np.linspace(0, 1, n), type=pa.float64())})
    good = write_parquet(tmp_path / "good.parquet", table, compression="none")
    raw = bytearray(good.read_bytes())
    footer_len = int.from_bytes(raw[-8:-4], "little")
    footer_start = len(raw) - 8 - footer_len
    assert raw[:4] == b"PAR1" and raw[-4:] == b"PAR1" and footer_start > 4
    raw[4:footer_start] = b"\xff" * (footer_start - 4)  # wreck every data page, keep the footer
    broken = tmp_path / "broken.parquet"
    broken.write_bytes(bytes(raw))

    a, b = read_footer(good), read_footer(broken)
    assert (a.num_rows, a.row_group_rows, a.columns) == (b.num_rows, b.row_group_rows, b.columns)
    assert b.column("k").min == 0 and b.column("k").max == n - 1
    with pytest.raises(ReadError, match="broken.parquet"):
        read_columns(broken, ["k"])


def test_iter_footers_is_lazy_and_keyed(tmp_path, monkeypatch):
    lst = _store(tmp_path, [("a", 1), ("b", 1)])
    calls = []
    real = R.read_footer
    monkeypatch.setattr(R, "read_footer", lambda p: calls.append(p) or real(p))
    it = iter_footers(lst)
    assert calls == []
    got = list(it)
    assert [k for k, _ in got] == [("a", 1), ("b", 1)] and len(calls) == 2
    assert all(ft.num_rows == 3 for _, ft in got)


def test_readers_refuse_something_that_is_not_a_listing(tmp_path):
    with pytest.raises(ReadError):
        iter_columns({"files": ()}, ["k"])
    with pytest.raises(ReadError):
        iter_footers([("a", "b")])


# ---------------------------------------------------------------------------------------------------
# read-only smoke on the real store (tests may name it; the engine may not)
PANEL_CATALOG = ENGINE_DIR / "datasets" / "_stores" / "monthly_panel_v170.yaml"
PANEL_DIR = Path("D:/monthly_panel")


@pytest.mark.skipif(not PANEL_DIR.is_dir() or not PANEL_CATALOG.is_file(),
                    reason="the monthly panel store is not on this machine")
def test_real_panel_listing_and_one_footer_read_only():
    cat = yaml.safe_load(PANEL_CATALOG.read_text(encoding="utf-8"))
    lst = list_store(cat["path_template"])
    assert lst.key_names == ("group", "year")
    assert lst.store_root == PANEL_DIR.as_posix()
    assert lst.not_read == (), lst.not_read[:5]
    found = lst.found()
    assert len(found) == cat["n_files"], (len(found), cat["n_files"])
    assert len({g for g, _ in found}) == cat["groups"]
    assert (min(y for _, y in found), max(y for _, y in found)) == tuple(cat["years"])
    # the catalog's cadence-sample files are all found under their keys
    for path in cat["cadence_sample"]["files"]:
        name = Path(path).name
        group, year = name[:-len(".parquet")].rsplit("_monthly_", 1)
        assert lst.path_of((group, int(year))).endswith("/" + name)

    key, path = lst.files[0]
    ft = read_footer(path)
    assert ft.num_rows > 0 and sum(ft.row_group_rows) == ft.num_rows
    assert len(ft.columns) == cat["n_columns"]
    keys = cat["keys"]
    for name in [keys["unit"], keys["group"]] + list(keys["time"]):
        assert name in ft.names, name
