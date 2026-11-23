"""Unit tests for layer_replay.py's pure helpers (nothing heavy runs, nothing is written).

    cd "C:\\Users\\<user>\\Desktop\\data set for reserch paper\\engine"
    py -3.9 -m pytest legacy_harness/tests -q
"""
import os
import sys

import pytest

HARNESS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.dirname(HARNESS)
sys.path.insert(0, HARNESS)
sys.path.insert(0, ENGINE)

import bank_replay as BR  # noqa: E402
import layer_replay as LR  # noqa: E402

ARM = {"identity": ("base", "corrector", "placebo", "treesoff"),
       "log": ("log", "log_corrector", "log_placebo", "log_treesoff"),
       "logc": ("logc", "logc_corrector", "logc_placebo", "logc_treesoff")}


def test_shipped_names_of_engine_arms():
    from treeroute.derive.shapes import Link
    from treeroute.layer.arms import ArmSpec, Tool, Weighting, trees_off_of

    key = {"identity": Link.IDENTITY, "log": LR.LegacyLink.LOG1P, "logc": Link.LOG_C}
    back = {v: k for k, v in key.items()}
    U = Weighting.UNWEIGHTED
    assert LR.shipped_name(ArmSpec(Link.IDENTITY, Tool.PLAIN, U, True), ARM, back) == "base"
    assert LR.shipped_name(ArmSpec(LR.LegacyLink.LOG1P, Tool.CORRECTOR, U, True), ARM, back) == "log_corrector"
    assert LR.shipped_name(trees_off_of(Link.LOG_C), ARM, back) == "logc_treesoff"
    assert LR.shipped_name(trees_off_of(Link.IDENTITY), ARM, back) == "treesoff"


def test_the_declared_legacy_list_is_the_shipped_normal_of_order():
    from treeroute.derive.shapes import Link
    from treeroute.layer import arms as LA

    key = {"identity": Link.IDENTITY, "log": LR.LegacyLink.LOG1P, "logc": Link.LOG_C}
    legacy = LR.legacy_candidates(LA, key, ["identity", "log", "logc"])
    back = {v: k for k, v in key.items()}
    names = [LR.shipped_name(a, ARM, back) for a in legacy.arms]
    # NORMAL_OF (pm25_adaptation.py:900-905): per link plain then corrector; then the trees-off arms
    assert names == ["base", "corrector", "log", "log_corrector", "logc", "logc_corrector",
                     "treesoff", "log_treesoff", "logc_treesoff"]
    assert legacy.reason == LR.LEGACY_REASON and "log1p" in legacy.reason
    assert legacy.link_keys() == ("identity", "log1p", "log_c")
    assert all(a.weighting is LA.Weighting.UNWEIGHTED for a in legacy.arms)


def test_edge_words_are_the_shipped_spelling():
    assert LR.edge_word(None) is None
    assert LR.edge_word("top") == "TOP" and LR.edge_word("bottom") == "BOTTOM"


def test_the_donor_matrix_lines_are_cut_from_the_shipped_file_exactly_once():
    with open(BR.PM25_SCRIPT, encoding="utf-8") as f:
        text = f.read()
    src, a, b = BR.cut_block(text, *LR.BLOCK_DONOR_MATRIX)
    assert b == a + 1
    assert src == "Vd = don[feat].fillna(0).values.astype(np.float32)\nyd = don.y.values.astype(np.float64)\n"


def test_fences():
    assert LR.BUILD_ROOT == "D:/treeroute/layer_build"
    assert "layer_replay" in LR.HEAVY_MARKERS and "router_replay" in LR.HEAVY_MARKERS
    assert LR.GOLDEN_ID == "pm25_wide_smoke_blas1"


def test_preflight_refuses_when_numeric_modules_are_loaded():
    import numpy  # noqa: F401  (pytest has it loaded anyway)

    with pytest.raises(BR.Refused, match="numeric modules"):
        LR.preflight(LR.BUILD_ROOT + "/never_made")
