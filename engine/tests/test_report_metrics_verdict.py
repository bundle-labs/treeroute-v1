"""treeroute.report.metrics: the group and blocked jackknife (R34), the R5 tag rule and the single
verdict (D74, F42), the equivalence band (R35, D75), relative guard tolerances (R36), sign flips (D77),
the trend-slope arithmetic (D78) and the ladder's common rows. Synthetic data; every branch.
"""

import math
from dataclasses import dataclass

import numpy as np
import pytest

from treeroute import engine_constants as K
from treeroute.derive.shapes import Link
from treeroute.errors import RefusedError
from treeroute.report import metrics as M

T = M.VerdictTag


def refused(fn, *args, match=None, **kwargs):
    with pytest.raises(RefusedError) as info:
        fn(*args, **kwargs)
    if match:
        assert match in str(info.value), str(info.value)
    return info.value


@dataclass(frozen=True)
class Donor:
    y: np.ndarray


def _source_jack(v):
    """adaptation.py:530-537, verbatim (tests may cite the source)."""
    v = np.asarray(v, float)
    n = len(v)
    if n < 3:
        return float(v.mean()), float("nan"), float("nan"), float("nan")
    jk = np.array([np.delete(v, i).mean() for i in range(n)])
    se = float(np.sqrt((n - 1) / n * ((jk - jk.mean()) ** 2).sum()))
    return float(v.mean()), v.mean() - 1.96 * se, v.mean() + 1.96 * se, se


# ---------------------------------------------------------------------------------------------------
# jackknife
def test_group_jackknife_reproduces_the_source_bit_for_bit():
    rng = np.random.RandomState(4)
    for n in (3, 7, 20, 127):
        v = rng.normal(0.1, 0.3, n)
        jk = M.group_jackknife(v)
        m, lo, hi, se = _source_jack(v)
        assert (jk.mean, jk.low, jk.high, jk.se, jk.n_groups) == (m, lo, hi, se, n)
    assert K.JACKKNIFE_Z == 1.96


def test_group_jackknife_small_and_refusals():
    two = M.group_jackknife([1.0, 3.0])
    assert two.mean == 2.0 and math.isnan(two.se) and math.isnan(two.low) and two.n_groups == 2
    refused(M.group_jackknife, [], match="at least one")
    refused(M.group_jackknife, [1.0, np.nan, 2.0], match="non-finite")


def test_blocked_jackknife_means_each_block_then_jackknifes():
    values = {"a": 1.0, "b": 3.0, "c": 5.0, "d": 7.0, "e": 0.0}
    blocks = {"a": 0, "b": 0, "c": 1, "d": 2, "e": 3}
    got = M.blocked_jackknife(values, blocks)
    want = M.group_jackknife(np.array([2.0, 5.0, 7.0, 0.0]))
    assert got == want
    singles = {g: i for i, g in enumerate(sorted(values))}
    assert M.blocked_jackknife(values, singles) == M.group_jackknife(np.array([1.0, 3.0, 5.0, 7.0, 0.0]))
    refused(M.blocked_jackknife, {}, blocks, match="per-group values")
    refused(M.blocked_jackknife, {"a": 1.0, "z": 2.0}, blocks, match="without an overlap block")


def test_blocked_jackknife_flag_at_the_borderline_share():
    g = M.JackknifeResult(0.0, 1.0, -1.96, 1.96, 20)
    assert M.blocked_jackknife_flag(g, M.JackknifeResult(0.0, 1.21, 0, 0, 15))
    assert not M.blocked_jackknife_flag(g, M.JackknifeResult(0.0, 1.2, 0, 0, 15))
    assert not M.blocked_jackknife_flag(g, M.JackknifeResult(0.0, float("nan"), 0, 0, 2))


# ---------------------------------------------------------------------------------------------------
# the R5 tag rule (D74), band first (F42)
def _contrasts(mean, spread, n=10):
    """n per-group contrasts with the given mean and a symmetric spread."""
    offs = np.linspace(-1.0, 1.0, n)
    return mean + spread * offs


def test_contrast_tag_every_outcome():
    band = 0.05
    assert M.contrast_tag(np.zeros(5), band)[0] is T.IDENTICAL
    assert M.contrast_tag(np.full(5, 1e-13), band)[0] is T.IDENTICAL
    assert M.contrast_tag(np.array([0.3, 0.4]), band)[0] is T.CANNOT_TELL        # interval undefined
    assert M.contrast_tag(_contrasts(0.0, 0.01), band)[0] is T.EQUIVALENT
    assert M.contrast_tag(_contrasts(0.5, 0.1), band)[0] is T.HELPS
    assert M.contrast_tag(_contrasts(-0.5, 0.1), band)[0] is T.HURTS
    assert M.contrast_tag(_contrasts(0.0, 0.5), band)[0] is T.CANNOT_TELL        # straddles past the band


def test_certain_but_negligible_is_not_helps_or_hurts():
    """R5: a CI that excludes 0 with its point inside the band is EQUIVALENT (whole CI in the band) or
    CANNOT TELL (CI crosses the band edge) -- never HELPS / HURTS as the four-outcome rule said."""
    band = 0.05
    tag, jk = M.contrast_tag(_contrasts(0.02, 0.005), band)
    assert jk.low > 0 and tag is T.EQUIVALENT
    tag, jk = M.contrast_tag(_contrasts(-0.02, 0.005), band)
    assert jk.high < 0 and tag is T.EQUIVALENT
    tag, jk = M.contrast_tag(_contrasts(0.045, 0.02), band)
    assert jk.low > 0 and jk.mean < band and jk.high > band and tag is T.CANNOT_TELL
    tag, jk = M.contrast_tag(_contrasts(-0.045, 0.02), band)
    assert jk.high < 0 and jk.mean > -band and jk.low < -band and tag is T.CANNOT_TELL


def test_band_is_checked_first_on_the_degenerate_tie():
    """SE 0 with the point exactly on +-band: the whole CI is inside the band -> EQUIVALENT (F42),
    where the source's order would have said HELPS / HURTS."""
    band = 0.25
    assert M.contrast_tag(np.full(6, 0.25), band)[0] is T.EQUIVALENT
    assert M.contrast_tag(np.full(6, -0.25), band)[0] is T.EQUIVALENT
    assert M.contrast_tag(np.full(6, 0.5), band)[0] is T.HELPS     # SE 0 beyond the band still HELPS


def test_contrast_tag_refuses_a_bad_band_first():
    for bad in (0.0, -0.1, float("nan"), None, "0.1"):
        refused(M.contrast_tag, np.zeros(5), bad, match="equivalence band")
    refused(M.contrast_tag, np.array([]), 0.1, match="at least one")


# ---------------------------------------------------------------------------------------------------
# the single verdict
def _maps(ref_minus_adopted, base=3.0):
    groups = ["g%02d" % i for i in range(len(ref_minus_adopted))]
    ref = {g: base + d for g, d in zip(groups, ref_minus_adopted)}
    adopted = {g: base for g in groups}
    return ref, adopted


def test_single_verdict_helps_with_pooled_better_groups_and_flips():
    dv = np.r_[np.full(9, 0.4), -0.1]
    ref, adopted = _maps(dv)
    v = M.single_verdict(ref, adopted, 3.4, 3.0, 0.05, False, M.REFERENCE_OWN_LINK_TREES_OFF)
    assert v.tag is T.HELPS and v.reference == "own_link_trees_off"
    assert v.pooled_contrast == pytest.approx(0.4) and v.groups_better == 9 and v.band == 0.05
    assert v.sign_flip_groups == ("g09",)
    assert v.contrast == M.group_jackknife(np.array([ref[g] - adopted[g] for g in sorted(ref)]))


def test_single_verdict_declined_reads_declined_and_keeps_the_contrast():
    ref, adopted = _maps(np.zeros(5))
    v = M.single_verdict(ref, adopted, 3.0, 3.0, 0.05, True, M.REFERENCE_OWN_LINK_TREES_OFF)
    assert v.tag is T.DECLINED and v.contrast.mean == 0.0
    v2 = M.single_verdict(ref, adopted, 3.0, 3.0, 0.05, np.bool_(False), M.REFERENCE_DONOR_ROW_MEDIAN)
    assert v2.tag is T.IDENTICAL and v2.reference == "donor_row_median"


def test_single_verdict_refusals():
    ref, adopted = _maps(np.full(5, 0.1))
    args = (3.1, 3.0, 0.05, False, M.REFERENCE_OWN_LINK_TREES_OFF)
    refused(M.single_verdict, ref, dict(adopted, extra=1.0), *args, match="different groups")
    refused(M.single_verdict, {}, {}, *args, match="empty")
    refused(M.single_verdict, dict(ref, g00=np.nan), adopted, *args, match="non-finite")
    refused(M.single_verdict, ref, adopted, 3.1, 3.0, 0.05, False, "arithmetic_normal", match="reference")
    refused(M.single_verdict, ref, adopted, 3.1, 3.0, 0.05, 1, M.REFERENCE_OWN_LINK_TREES_OFF,
            match="True or False")
    refused(M.single_verdict, ref, adopted, float("nan"), 3.0, 0.05, False,
            M.REFERENCE_OWN_LINK_TREES_OFF, match="pooled reference")
    refused(M.single_verdict, ref, adopted, 3.1, 3.0, 0.0, False, M.REFERENCE_OWN_LINK_TREES_OFF,
            match="band")


# ---------------------------------------------------------------------------------------------------
# the band (R35, D75)
def test_equivalence_band_is_the_median_finite_se():
    assert M.equivalence_band([0.3, 0.1, float("nan"), 0.2]) == pytest.approx(0.2)
    refused(M.equivalence_band, [float("nan")], match="no finite")
    refused(M.equivalence_band, [], match="no finite")
    refused(M.equivalence_band, ["a"], match="numbers")
    refused(M.equivalence_band, 5.0, match="numbers")
    refused(M.equivalence_band, [[0.1, 0.2]], match="flat")


def test_band_from_pairs_leaves_identical_contrasts_out():
    groups = ["a", "b", "c", "d"]
    mae = {
        "arm__plain": {"a": 2.0, "b": 2.1, "c": 1.9, "d": 2.4},
        "arm__off": {"a": 2.5, "b": 2.2, "c": 2.6, "d": 2.5},
        "arm__corr": {"a": 1.8, "b": 2.3, "c": 1.7, "d": 2.2},
        "arm__plac": {"a": 1.9, "b": 2.2, "c": 1.9, "d": 2.1},
        "arm__same": {"a": 2.5, "b": 2.2, "c": 2.6, "d": 2.5},
    }
    band, records = M.band_from_pairs(mae, [("arm__off", "arm__plain"), ("arm__off", "arm__corr"),
                                            ("arm__plac", "arm__corr"), ("arm__off", "arm__same")])
    ses = []
    for rec in records:
        dv = np.array([mae[rec["reference"]][g] - mae[rec["arm"]][g] for g in groups])
        assert rec["se"] == M.group_jackknife(dv).se
        if not rec["identical"]:
            ses.append(rec["se"])
    assert records[-1]["identical"] is True and len(ses) == 3
    assert band == float(np.median(ses))


def test_band_from_pairs_refusals():
    mae = {"x": {"a": 1.0, "b": 2.0, "c": 3.0}, "y": {"a": 1.0, "b": 2.0}}
    refused(M.band_from_pairs, mae, [], match="at least one contrast pair")
    refused(M.band_from_pairs, mae, [("x", "x")], match="with itself")
    refused(M.band_from_pairs, mae, [("x", "z")], match="no per-group MAE")
    refused(M.band_from_pairs, mae, [("x", "y")], match="different groups")
    refused(M.band_from_pairs, mae, [("x",)], match="each pair")
    same = {"x": {"a": 1.0, "b": 2.0, "c": 3.0}, "w": {"a": 1.0, "b": 2.0, "c": 3.0}}
    refused(M.band_from_pairs, same, [("x", "w")], match="no finite")


# ---------------------------------------------------------------------------------------------------
# guard tolerances (R36), sign flips (D77), trend arithmetic (D78), common rows
def test_guard_tolerance_is_k_times_the_donor_sd_of_link_y():
    y = np.array([0.1, 0.4, 0.2, 0.9, 0.5])
    d = Donor(y=y)
    assert M.guard_tolerance(d, Link.IDENTITY, None, None, 1e-6) == pytest.approx(1e-6 * np.std(y))
    assert M.guard_tolerance(d, Link.LOG_C, 0.05, None, 2.0) == pytest.approx(2.0 * np.std(np.log(y + 0.05)))
    assert M.guard_tolerance(d, Link.ARCSINE, None, 1.0, 3.0) == pytest.approx(
        3.0 * np.std(np.arcsin(np.sqrt(y))))
    refused(M.guard_tolerance, Donor(y=np.full(4, 2.0)), Link.IDENTITY, None, None, 1.0, match="constant")
    refused(M.guard_tolerance, d, Link.IDENTITY, None, None, 0.0, match="above 0")
    refused(M.guard_tolerance, d, Link.IDENTITY, None, None, float("nan"), match="finite")


def test_sign_flip_groups_d77():
    per = {"b": -0.2, "a": 0.3, "c": 0.0, "d": -0.01}
    assert M.sign_flip_groups(per, 0.1) == ("b", "d")
    assert M.sign_flip_groups(per, -0.1) == ("a",)
    assert M.sign_flip_groups(per, 0.0) == ()
    refused(M.sign_flip_groups, {"a": float("nan")}, 0.1, match="group 'a'")
    refused(M.sign_flip_groups, per, float("inf"), match="pooled")
    refused(M.sign_flip_groups, [0.1], 0.1, match="map groups")


def test_median_unit_slope_and_trend_flag_gap():
    units = np.array(["u", "u", "u", "v", "v", "w"])
    years = np.array([0.0, 1.0, 2.0, 0.0, 2.0, 5.0])
    y = np.array([1.0, 2.0, 3.0, 4.0, 0.0, 9.0])
    assert M.median_unit_slope(units, years, y) == pytest.approx(np.median([1.0, -2.0]))
    refused(M.median_unit_slope, units, years[:3], y, match="one per row")
    refused(M.median_unit_slope, units, np.r_[years[:5], np.nan], y, match="finite")
    refused(M.median_unit_slope, np.array(["u", "v"]), np.array([1.0, 1.0]), np.array([1.0, 2.0]),
            match="2 distinct times")
    with pytest.raises(NotImplementedError, match="steps per year"):
        M.trend_flag(Donor(y=y))


def test_common_rows():
    got = M.common_rows({1: np.array(["b", "a", "c"]), 3: np.array(["c", "a", "d"]), 0: np.array(["a", "c"])})
    assert got.tolist() == ["a", "c"]
    assert M.common_rows({1: np.array([5, 3, 1]), 2: np.array([1, 5])}).tolist() == [1, 5]
    refused(M.common_rows, {}, match="at least one lead")
    refused(M.common_rows, {1: np.zeros((2, 2))}, match="one-dimensional")
    refused(M.common_rows, {1: np.array(["a", "a"])}, match="twice")
    refused(M.common_rows, {1: np.array(["a"]), 2: np.array(["b"])}, match="every lead")
    refused(M.common_rows, {1: np.array([1, "a"], dtype=object)}, match="ordered")
