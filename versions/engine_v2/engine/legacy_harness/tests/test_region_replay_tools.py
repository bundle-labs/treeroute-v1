"""Unit tests for region_replay.py's helpers and its cache-time bytecode checks (nothing heavy runs, nothing
is written; the shipped scripts and the bytecode copies are read only).

    cd "C:\\Users\\<user>\\Desktop\\data set for reserch paper\\engine"
    py -3.9 -m pytest legacy_harness/tests -q
"""
import os
import sys
import types

import numpy as np
import pytest

HARNESS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HARNESS)

import region_replay as RR  # noqa: E402

HAVE_SHIPPED = all(os.path.isfile(p) for p in (RR.TRAIN, RR.ADD, RR.SOFT, RR.CORR))
needs_shipped = pytest.mark.skipif(not HAVE_SHIPPED, reason="the shipped scripts are not beside the engine")


def test_the_bytecode_copies_are_pinned_and_record_sources_older_than_the_caches():
    code, info = RR.pyc_module(RR.TRAIN_PYC, RR.TRAIN_PYC_SHA256, RR.TRAIN_PYC_SOURCE)
    assert isinstance(code, types.CodeType) and info["source_size"] == 22398
    code2, info2 = RR.pyc_module(RR.ADD_PYC, RR.ADD_PYC_SHA256, RR.ADD_PYC_SOURCE)
    assert info2["source_mtime"] == "2026-09-13 22:19:00"
    assert info["source_mtime_epoch"] < info2["source_mtime_epoch"]
    with pytest.raises(RR.Refused):
        RR.pyc_module(RR.TRAIN_PYC, "0" * 64, RR.TRAIN_PYC_SOURCE)
    with pytest.raises(RR.Refused):
        RR.pyc_module(RR.TRAIN_PYC, RR.TRAIN_PYC_SHA256, ("2026-09-07 12:22:31", 22398))


@needs_shipped
def test_todays_load_region_differs_from_the_cache_time_one_only_by_the_sentinel_mask():
    old = RR.code_functions(RR.pyc_module(RR.TRAIN_PYC, RR.TRAIN_PYC_SHA256, RR.TRAIN_PYC_SOURCE)[0])
    new = RR.code_functions(compile(open(RR.TRAIN, encoding="utf-8").read(), "defo_train.py", "exec"))
    for name in ("load_split", "feature_cols", "extra_cols"):
        assert RR.same_code(old[name], new[name]), name
    assert not RR.same_code(old["load_region"], new["load_region"])
    assert sorted(set(new["load_region"].co_names) - set(old["load_region"].co_names)) == ["mask", "panel_sentinel"]
    # instruction for instruction: today's load_region minus its two sentinel lines is the cache-time one
    text = open(RR.TRAIN, encoding="utf-8").read()
    skip = RR.check_load_region_is_cache_time_plus_mask(old["load_region"], new["load_region"], text)
    lines = text.split("\n")
    assert [lines[i - 1].rstrip("\r") for i in skip] == list(RR.SENTINEL_LINES)
    # any other change is refused: a constant, and an added statement using no new name
    for before, after in (("keep = set(ids[:: max(1, len(ids) // cap)][:cap])",
                           "keep = set(ids[:: max(2, len(ids) // cap)][:cap])"),
                          ("    _ps.mask(d)\n", "    _ps.mask(d)\n    d = d[np.isfinite(d.y)]\n")):
        assert text.count(before) == 1, before
        changed = text.replace(before, after)
        code = RR.code_functions(compile(changed, "defo_train.py", "exec"))["load_region"]
        with pytest.raises(RR.Refused):
            RR.check_load_region_is_cache_time_plus_mask(old["load_region"], code, changed)


@needs_shipped
def test_the_add_linkcorr_blocks_the_gate_runs_are_the_cache_time_bytecode():
    text = open(RR.ADD, encoding="utf-8").read()
    old = RR.code_functions(RR.pyc_module(RR.ADD_PYC, RR.ADD_PYC_SHA256, RR.ADD_PYC_SOURCE)[0])
    new = RR.code_functions(compile(text, "add_linkcorr.py", "exec"))
    for name in ("stack", "form"):
        assert RR.same_code(old[name], new[name]), name
    for first, last in (RR.BLOCK_DONORS, RR.BLOCK_ROWS):
        _, lo, hi = RR.cut_block(text, first, last)
        a = RR.instructions_in_lines(old["main"], lo, hi)
        assert a and a == RR.instructions_in_lines(new["main"], lo, hi)
    # main() as a whole did change after the caches (its report section): the check is per block
    assert not RR.same_code(old["main"], new["main"])


@needs_shipped
def test_the_shipped_namespace_builds_and_uses_the_cache_time_load_region():
    report = {}
    ns = RR.shipped_namespace(report)
    assert "panel_sentinel" not in ns.T.load_region.__code__.co_names
    assert ns.T.load_region.__defaults__ == (None, False)
    assert report["shipped_constants"] == {"CELLS": 4000, "REGROWS": 60000, "LAM": 100.0, "INNER": 2016, "BLK": 20000}
    assert set(report["cache_time_bytecode"]) == {"defo_train", "add_linkcorr"}
    g = ns.A["LINK_G"](np.array([0.0, 0.25, 1.0, 2.0]))
    assert np.allclose(ns.A["LINK_I"](g), [0.0, 0.25, 1.0, 1.0])


def test_compare_counts_rows_bytes_and_the_tolerance():
    c = np.array([0.1, 0.2, 0.3])
    assert RR.compare(c.copy(), c) == {"rows_engine": 3, "rows_cache": 3, "rows_match": True, "max_abs_diff": 0.0,
                                       "n_bytes_equal": 3, "pass": True}
    near = c + np.array([0.0, 5e-10, 0.0])
    got = RR.compare(near, c)
    assert got["pass"] and got["n_bytes_equal"] == 2
    assert not RR.compare(c + 2e-9, c)["pass"]
    assert not RR.compare(c[:2], c)["pass"] and not RR.compare(c[:2], c)["rows_match"]


def test_preflight_refuses_an_out_dir_outside_the_build_root_or_an_existing_one(tmp_path):
    with pytest.raises(RR.Refused):
        RR.preflight(str(tmp_path / "x"), False)
    with pytest.raises(RR.Refused):
        RR.preflight(RR.BUILD_ROOT, False)


def test_instructions_in_lines_ignores_code_object_addresses_and_later_changes():
    src = "def f(x):\n    if x:\n        return [i for i in range(x)]\n    return None\n"
    a = compile(src, "a", "exec").co_consts[0]
    later = src.replace("    return None\n", "    y = [j for j in range(3)]\n    return y\n")
    b = compile(later, "a", "exec").co_consts[0]                  # lines 1-3 the same, the rest changed
    assert RR.instructions_in_lines(a, 2, 3) == RR.instructions_in_lines(b, 2, 3)
    assert RR.instructions_in_lines(a, 2, 3)
    assert RR.instructions_in_lines(a, 4, 4) != RR.instructions_in_lines(b, 4, 5)


def test_instructions_except_lines_skips_lines_and_compares_nested_code_without_file_names():
    src = "def f(x):\n    y = [i * 2 for i in range(x)]\n    return y\n"
    masked = "def f(x):\n    y = [i * 2 for i in range(x)]\n    x.mask()\n    return y\n"
    a = compile(src, "C:/somewhere/a.py", "exec").co_consts[0]
    b = compile(masked, "a.py", "exec").co_consts[0]
    assert RR.instructions_except_lines(a) == RR.instructions_except_lines(b, {3})
    assert RR.instructions_except_lines(a) != RR.instructions_except_lines(b)
    assert ("<nested>", "<listcomp>") in RR.instructions_except_lines(a)
    inner = compile(src.replace("i * 2", "i * 3"), "a.py", "exec").co_consts[0]
    assert RR.instructions_except_lines(a) != RR.instructions_except_lines(inner)      # the comprehension body


def test_main_refuses_both_bank_modes_and_unknown_options():
    assert RR.main(["--out-dir=%s/x" % RR.BUILD_ROOT, "--deep-banks", "--size-only-banks"]) == 2
    assert RR.main(["--out-dir=%s/x" % RR.BUILD_ROOT, "--no-such-option"]) == 2
    assert RR.main(["--only=costa_rica"]) == 2
