"""Unit tests for bank_replay.py's pure helpers (nothing heavy runs, nothing is written).

    cd "C:\\Users\\<user>\\Desktop\\data set for reserch paper\\engine"
    py -3.9 -m pytest legacy_harness/tests -q
"""
import hashlib
import os
import sys

import pytest

HARNESS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HARNESS)

import bank_replay as BR  # noqa: E402


def test_legacy_seed_formulas_are_the_shipped_ones():
    # pm25_adaptation.py:642 RandomState(7 * 1000 + int(e) * 17 + j); :646 random_state=700 + j;
    # adaptation.py:470 random_state=j over the global tree list
    assert BR.legacy_bag_seed(0, 0) == 7000
    assert BR.legacy_bag_seed(3, 5) == 7000 + 3 * 17 + 5
    assert BR.legacy_tree_seed(11) == 711
    assert BR.legacy_corrector_seed(95) == 95
    # the old overlap the name seeds remove: two groups share a bag seed
    assert BR.legacy_bag_seed(0, 17) == BR.legacy_bag_seed(1, 0)


def test_cut_block_finds_the_shipped_blocks_exactly_once():
    with open(BR.PM25_SCRIPT, encoding="utf-8") as f:
        text = f.read()
    frames, a, b = BR.cut_block(text, *BR.BLOCK_FRAMES)
    bank, c, d = BR.cut_block(text, *BR.BLOCK_BANK)
    assert frames.startswith("donors = list(SPLIT.DONORS)\n")
    assert frames.rstrip("\n").endswith('test = test.sort_values(["cell", "t"]).reset_index(drop=True)')
    assert "PA.build_pool(" in frames and "PA.cleanup()" in frames
    assert bank.startswith("# ---------------------------------------------------------------- bank")
    assert "7 * 1000 + int(e) * 17 + j" in bank and "random_state=700 + j" in bank
    assert a < b < c < d
    compile(frames, "frames", "exec")
    compile(bank, "bank", "exec")


def test_cut_block_refuses_missing_or_repeated_lines():
    with pytest.raises(BR.Refused):
        BR.cut_block("a\nb\n", "x", "b")
    with pytest.raises(BR.Refused):
        BR.cut_block("a\nb\na\nb\n", "a", "b")
    with pytest.raises(BR.Refused):
        BR.cut_block("b\na\n", "a", "b")


def test_function_source_is_the_exact_shipped_fit_correctors():
    with open(BR.ADAPT_SCRIPT, encoding="utf-8") as f:
        text = f.read()
    src, a, b = BR.function_source(text, "fit_correctors")
    assert src.startswith("def fit_correctors(trees, inbag, home, X, y, mf, depth=6, placebo=False, "
                          "minrows=50):")
    assert "np.roll(r, len(r) // 2)" in src and "random_state=j" in src
    lines = text.split("\n")[a - 1:b]
    assert src == "\n".join(ln.rstrip("\r") for ln in lines) + "\n"
    with pytest.raises(BR.Refused):
        BR.function_source(text, "no_such_function")


def test_reversed_inside_reverses_one_group_and_keeps_the_rest():
    import numpy as np
    member = np.array([False, True, True, True, False, True, False])
    order = BR.reversed_inside(member)
    assert order.tolist() == [0, 5, 3, 2, 4, 1, 6]
    assert sorted(order.tolist()) == list(range(7))
    assert BR.reversed_inside(np.zeros(4, dtype=bool)).tolist() == [0, 1, 2, 3]


def test_refusal_rule_returns_the_rule_tag_or_none():
    engine = os.path.dirname(HARNESS)
    if engine not in sys.path:
        sys.path.insert(0, engine)
    from treeroute.errors import RefusedError

    def refuses():
        raise RefusedError("R30", "a missing value")

    assert BR.refusal_rule(refuses) == "R30"
    assert BR.refusal_rule(lambda a: a, 1) is None
    with pytest.raises(ZeroDivisionError):                 # other errors are not swallowed
        BR.refusal_rule(lambda: 1 / 0)


def test_out_dir_fence_helpers():
    assert BR.is_under("D:/treeroute/fit_build/bank_replay_x", BR.BUILD_ROOT)
    assert not BR.is_under("D:/treeroute/fit_build_other/x", BR.BUILD_ROOT)
    assert BR.norm("d:\\TREEROUTE\\fit_build\\") == BR.norm("D:/treeroute/fit_build")


def test_preflight_refuses_when_numpy_is_already_loaded():
    import numpy  # noqa: F401  (pytest has loaded it anyway)
    with pytest.raises(BR.Refused) as info:
        BR.preflight(BR.BUILD_ROOT + "/bank_replay_never_created")
    assert "numeric modules" in str(info.value)
    assert not os.path.exists(BR.BUILD_ROOT + "/bank_replay_never_created")


def test_shipped_files_match_the_registry():
    _, reg = BR.newest_registry()
    assert hashlib.sha256(open(BR.PM25_SCRIPT, "rb").read()).hexdigest() == \
        reg["goldens"][BR.GOLDEN_ID]["script_sha256_now"]
    assert hashlib.sha256(open(BR.ADAPT_SCRIPT, "rb").read()).hexdigest() == \
        reg["goldens"]["fire_smoke"]["source_sha256"]
