"""layer/links.py: R22's links, R23's c and R28's legal clip.

  - the link transforms are the source's own expressions, bit for bit (log(v + c), exp(v) - c; D61's
    arcsin(sqrt(y / UB)) inverts UB x sin(clip(z, 0, pi/2))^2);
  - refusals: log_c without c > 0, arcsine without a finite UB, values outside a link's domain, a
    missing or infinite value, anything but R22's links;
  - c_for_cut: FitContext's DonorRows at a FIT cut only (D63 a), derive's one formula; it matches the
    plan-time R23 record built from the vault's label-only view (check_r23_matches_run);
  - clip_to_legal: the pre-clip rate over finite rows and the NaN count; NaN refused for predictions,
    passed through (and counted) for baselines; infinities refused; in-range values unchanged.
"""

import math

import numpy as np
import pytest

from test_vault_world import FIT_CUT_0, GROUPS, make_context, make_world
from treeroute.derive import rules as R
from treeroute.derive.derived import DeriveRefusal
from treeroute.derive.shapes import CutKind, Link
from treeroute.layer.arms import LayerRefusal
from treeroute.layer.links import (c_for_cut, c_for_cut_against_plan, clip_to_legal, clip_with_counts,
                                   link_forward, link_inverse)

Y = np.array([0.0, 0.006, 1.3, 18.5, 689.0])
C = 3.5416667461395264


# ------------------------------------------------------------------------------------ transforms
def test_identity_is_a_copy_of_the_values():
    out = link_forward(Y, Link.IDENTITY, None, None)
    assert out.tobytes() == Y.tobytes() and out is not Y
    back = link_inverse(out, Link.IDENTITY, 5.0, 7.0)          # unused constants are ignored
    assert back.tobytes() == Y.tobytes()


def test_log_c_is_the_source_expression_bit_for_bit():
    fwd = link_forward(Y, Link.LOG_C, C, None)
    assert fwd.tobytes() == np.log(Y + C).tobytes()
    z = np.linspace(-1.0, 7.0, 50)
    assert link_inverse(z, Link.LOG_C, C, None).tobytes() == (np.exp(z) - C).tobytes()
    assert np.allclose(link_inverse(fwd, Link.LOG_C, C, None), Y, atol=1e-12, rtol=0)


def test_arcsine_forward_inverts_the_source_back_transform():
    ub = 1.0
    y = np.array([0.0, 0.1, 0.5, 0.99, 1.0])
    z = link_forward(y, Link.ARCSINE, None, ub)
    assert np.array_equal(z, np.arcsin(np.sqrt(y / ub)))
    back = link_inverse(z, Link.ARCSINE, None, ub)
    assert np.allclose(back, y, atol=1e-15)
    wide = link_inverse(np.array([-0.5, 2.0]), Link.ARCSINE, None, 4.0)
    assert np.array_equal(wide, 4.0 * np.sin(np.clip(np.array([-0.5, 2.0]), 0, math.pi / 2)) ** 2)


def test_link_refusals():
    with pytest.raises(LayerRefusal, match="c > 0"):
        link_forward(Y, Link.LOG_C, 0.0, None)
    with pytest.raises(LayerRefusal, match="c > 0"):
        link_inverse(Y, Link.LOG_C, float("nan"), None)
    with pytest.raises(LayerRefusal, match="domain"):
        link_forward(np.array([-4.0]), Link.LOG_C, C, None)
    with pytest.raises(LayerRefusal, match="upper bound"):
        link_forward(np.array([0.5]), Link.ARCSINE, None, float("inf"))
    with pytest.raises(LayerRefusal, match="upper bound"):
        link_forward(np.array([0.5]), Link.ARCSINE, None, None)
    with pytest.raises(LayerRefusal, match="outside"):
        link_forward(np.array([1.5]), Link.ARCSINE, None, 1.0)
    with pytest.raises(LayerRefusal, match="missing or infinite"):
        link_forward(np.array([1.0, np.nan]), Link.IDENTITY, None, None)
    with pytest.raises(LayerRefusal, match="missing or infinite"):
        link_inverse(np.array([1.0, np.inf]), Link.IDENTITY, None, None)
    with pytest.raises(LayerRefusal, match="R22's links"):
        link_forward(Y, "log", None, None)
    with pytest.raises(LayerRefusal, match="numeric"):
        link_forward(np.array(["a"]), Link.IDENTITY, None, None)


# ------------------------------------------------------------------------------------ c (R23)
def test_c_for_cut_is_derives_formula_on_fit_cut_donor_rows():
    w = make_world()
    d = make_context(w, 0, CutKind.FIT).donor_rows("c")
    c = c_for_cut(d)
    assert c == R.c_from_donor_y(d.y)[0]
    positive = d.y[d.y > 0]
    assert c == float(np.percentile(positive, 1))                 # the source's np.percentile(ypos, 1)


def test_c_for_cut_refuses_guard_rows_and_anything_but_donor_rows():
    w = make_world()
    guard = make_context(w, 0, CutKind.GUARD).donor_rows("c")
    with pytest.raises(LayerRefusal, match="D63"):
        c_for_cut(guard)
    bank = tuple(u for g in GROUPS for u in w.picks.bank[g])
    view = w.labels.donor_labels(w.split, FIT_CUT_0, CutKind.FIT, 0, bank, "links")
    with pytest.raises(LayerRefusal, match="only DonorRows"):
        c_for_cut(view)                                           # the plan-time label-only view


def test_c_matches_the_plan_time_record_and_refuses_another():
    w = make_world()
    bank = tuple(u for g in GROUPS for u in w.picks.bank[g])
    for lead in (0, 3):
        ctx = make_context(w, lead, CutKind.FIT)
        view = w.labels.donor_labels(w.split, ctx.cut, CutKind.FIT, lead, bank, "links")
        w.derived["R23:lead=%d" % lead] = R.derive_r23_c_for_cut(view)
        assert c_for_cut_against_plan(ctx.donor_rows("c"), w.derived) == w.derived["R23:lead=%d" % lead].value
    ctx1 = make_context(w, 1, CutKind.FIT)
    with pytest.raises(LayerRefusal, match="no R23:lead=1"):
        c_for_cut_against_plan(ctx1.donor_rows("c"), w.derived)
    w.derived["R23:lead=1"] = w.derived["R23:lead=3"]              # another lead's record
    with pytest.raises(DeriveRefusal, match="lead"):
        c_for_cut_against_plan(ctx1.donor_rows("c"), w.derived)
    one_unit = w.labels.donor_labels(w.split, ctx1.cut, CutKind.FIT, 1, bank[:1], "links")
    w.derived["R23:lead=1"] = R.derive_r23_c_for_cut(one_unit)     # other rows: other hash
    with pytest.raises(DeriveRefusal, match="differ from plan"):
        c_for_cut_against_plan(ctx1.donor_rows("c"), w.derived)


# ------------------------------------------------------------------------------------ clip (R28)
def test_clip_counts_the_values_outside_the_range():
    p = np.array([-2.0, 0.0, 3.0, 12.0, 7.5])
    out, rate, n_nan = clip_to_legal(p, (0.0, 10.0), allow_nan=False)
    assert out.tolist() == [0.0, 0.0, 3.0, 10.0, 7.5]
    assert rate == 2 / 5.0 and n_nan == 0
    _, counts = clip_with_counts(p, (0.0, 10.0), allow_nan=False)
    assert (counts.n_below, counts.n_above, counts.n_finite, counts.n_rows) == (1, 1, 5, 5)
    assert p.tolist() == [-2.0, 0.0, 3.0, 12.0, 7.5]               # the input is never changed


def test_clip_leaves_in_range_values_unchanged_bit_for_bit():
    p = np.random.RandomState(3).normal(5.0, 1.0, size=(40, 7))
    out, rate, _ = clip_to_legal(p, (0.0, float("inf")), allow_nan=False)
    assert out.tobytes() == p.tobytes() and rate == 0.0 and out.shape == p.shape
    out2, rate2, _ = clip_to_legal(p, (-float("inf"), float("inf")), allow_nan=False)
    assert out2.tobytes() == p.tobytes() and rate2 == 0.0


def test_clip_nan_rules_for_predictions_and_baselines():
    p = np.array([1.0, np.nan, -3.0])
    with pytest.raises(LayerRefusal, match="missing"):
        clip_to_legal(p, (0.0, float("inf")), allow_nan=False)
    out, rate, n_nan = clip_to_legal(p, (0.0, float("inf")), allow_nan=True)
    assert np.isnan(out[1]) and out[2] == 0.0 and n_nan == 1 and rate == 0.5
    out, rate, n_nan = clip_to_legal(np.array([np.nan]), (0.0, 1.0), allow_nan=True)
    assert math.isnan(rate) and n_nan == 1
    with pytest.raises(LayerRefusal, match="infinite"):
        clip_to_legal(np.array([1.0, np.inf]), (0.0, float("inf")), allow_nan=True)


def test_clip_legal_range_checks():
    for bad in ((1.0, 1.0), (2.0, 1.0), (float("nan"), 1.0), ("0", 1.0), (0.0,)):
        with pytest.raises(LayerRefusal):
            clip_to_legal(np.array([0.5]), bad, allow_nan=False)
    with pytest.raises(LayerRefusal, match="bool"):
        clip_to_legal(np.array([0.5]), (0.0, 1.0), allow_nan=0)
