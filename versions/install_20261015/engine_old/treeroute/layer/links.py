"""R22's links, R23's c and R28's legal clip.

SCIENCE bodies for the owner-approved signatures link_forward, link_inverse, c_for_cut and
clip_to_legal (treeroute/_proposed/layer.py; owner rulings A-F, which accepted every proposed default):
  - D61: arcsine forward = arcsin(sqrt(y / UB)), the inverse of the source's back-transform
    UB x sin(clip(z, 0, pi/2))^2.
  - D62: c is numpy's default (linear) percentile, as the source.
  - D63 (a): ONE c per LEAD cut, from the donor rows at that lead's FIT cut; it serves that lead's
    decision (or guard) surface AND its test pass, so an arm is never selected under one transform and
    scored under another. c_for_cut therefore refuses donor rows of a GUARD cut.
The link transforms are the source's own expressions (log(y + c), exp(z) - c), so a replay reproduces
the shipped values bit for bit.

R23 has ONE formula: derive.rules.c_from_donor_y, which derive's plan-time record (derive_r23_c_for_cut)
calls on the label-only donor view and c_for_cut calls on FitContext's DonorRows (G-DONOR: c accepts
only DonorRows). c_for_cut_against_plan runs derive's check_r23_matches_run on the result, so the run
refuses a c (or donor rows) that differ from the ones plan showed.

R28: every back-transformed prediction AND every baseline goes through clip_to_legal. Tree arms and
trees-off must exist on every scored row (NaN refused); a baseline may be NaN where it has no value
(persistence without an issue label): NaN passes through unclipped and is counted. The pre-clip rate
is over finite rows; clip_counts gives the counts behind it (below the minimum, above the maximum).
"""
# Provenance for the module: plan 2.4 R22, R23, R28, 5 G-CLIP; pm25_adaptation.py:572-577 (C_LOG =
# np.percentile(ypos, 1) over finite positive donor y), :711-719 (LINKS: logc forward log(v + C_LOG),
# back exp(v) - C_LOG); adaptation.py:1436 (arcsine back-transform UB x sin(clip(p, 0, pi/2))^2);
# pm25_forecast.py:530-531 (persistence floored at 0, replaced by R28).

import math
from dataclasses import dataclass
from numbers import Real
from typing import Any, Mapping, Optional, Tuple

import numpy as np

from treeroute.derive import rules as _rules
from treeroute.derive.shapes import CutKind, Link

from .arms import LayerRefusal


# ---------------------------------------------------------------------------------------------------
def _engine_link(link: Any) -> Link:
    if not isinstance(link, Link):
        raise LayerRefusal("R22", "the link must be one of R22's links (treeroute.derive.shapes.Link), "
                           "got %r" % (link,), fix="take the links from derived.json's R22 entry")
    return link


def _values(values: Any, what: str) -> np.ndarray:
    """A numeric array as float64 (a copy for non-float64 input), any shape, all finite."""
    arr = np.asarray(values)
    if arr.dtype.kind not in "iuf" or arr.dtype == np.bool_:
        raise LayerRefusal("R22", "%s must be numeric, got dtype %s" % (what, arr.dtype))
    arr = np.asarray(arr, dtype=np.float64)
    if arr.size and not np.isfinite(arr).all():
        bad = int(arr.size - np.count_nonzero(np.isfinite(arr)))
        raise LayerRefusal("R22", "%s holds %d missing or infinite value(s); a link transforms valid "
                           "labels and fitted predictions only" % (what, bad),
                           fix="leave rows with a missing label out (R30), and never transform a row "
                               "a router did not fit")
    return arr


def _c(c: Any) -> float:
    if isinstance(c, bool) or not isinstance(c, (Real, np.floating)) or not math.isfinite(float(c)) \
            or not float(c) > 0:
        raise LayerRefusal("R23", "log(y + c) needs a finite c > 0 (R23), got %r" % (c,),
                           fix="pass c_for_cut of the lead's fit cut")
    return float(c)


def _ub(ub: Any) -> float:
    if isinstance(ub, bool) or not isinstance(ub, (Real, np.floating)) or not math.isfinite(float(ub)) \
            or not float(ub) > 0:
        raise LayerRefusal("R22", "the arcsine link needs a finite legal upper bound UB > 0 (the target "
                           "fact), got %r" % (ub,),
                           fix="the arcsine link exists only for a legal range [0, UB] with UB finite")
    return float(ub)


# Provenance: plan 2.4 R22; pm25_adaptation.py:153-154, 718-719 (logc: log(y + c), back exp(p) - c);
# adaptation.py:1436 (arcsine inverse UB x sin(clip(p, 0, pi/2))^2).
def link_forward(y: np.ndarray, link: Link, c: Optional[float], ub: Optional[float]) -> np.ndarray:
    """Transform y into a link's space.

    Rule: R22 (D61). identity: y. log_c: log(y + c), c from R23 for the cut in use. arcsine:
    arcsin(sqrt(y / UB)), only with a finite legal upper bound UB. A constant a link does not use is
    ignored (callers pass the lead's constants to every arm).
    Returns float64 values of the same shape.
    Refuses: a link that is not R22's; log_c without a finite c > 0; arcsine without a finite UB > 0;
    y outside the link's domain (a missing or infinite value; y + c <= 0 for log_c; y outside
    [0, UB] for arcsine).
    """
    link = _engine_link(link)
    v = _values(y, "y")
    if link is Link.IDENTITY:
        return v.copy()
    if link is Link.LOG_C:
        cc = _c(c)
        low = v + cc
        if low.size and not (low > 0).all():
            raise LayerRefusal("R22", "%d value(s) of y are at or below -c = %r, outside the domain of "
                               "log(y + c)" % (int(np.count_nonzero(~(low > 0))), -cc),
                               fix="log(y + c) is a link only when the legal minimum is >= 0 (R22)")
        return np.log(v + cc)
    top = _ub(ub)
    outside = (v < 0) | (v > top)
    if outside.any():
        raise LayerRefusal("R22", "%d value(s) of y lie outside [0, UB = %r], the domain of the arcsine "
                           "link" % (int(outside.sum()), top),
                           fix="labels outside the legal range are refused earlier (G-RANGE)")
    return np.arcsin(np.sqrt(v / top))


# Provenance: as link_forward; pm25_adaptation.py:734, 765, 768 (unclipped exp(p) - c, the defect G-CLIP
# closes).
def link_inverse(z: np.ndarray, link: Link, c: Optional[float], ub: Optional[float]) -> np.ndarray:
    """Back-transform link-space predictions to y units (clipping happens in clip_to_legal).

    Rule: R22, R28. identity: z. log_c: exp(z) - c. arcsine: UB x sin(clip(z, 0, pi/2))^2. Every
    result then goes through clip_to_legal; the pre-clip value is kept for the pre-clip rate.
    Returns float64 y-unit predictions of the same shape, before the legal clip.
    Refuses: as link_forward; a missing or infinite z (a row a router did not fit is never
    back-transformed or scored).
    """
    link = _engine_link(link)
    v = _values(z, "z (link-space predictions)")
    if link is Link.IDENTITY:
        return v.copy()
    if link is Link.LOG_C:
        return np.exp(v) - _c(c)
    top = _ub(ub)
    return top * np.sin(np.clip(v, 0.0, np.pi / 2.0)) ** 2


# ---------------------------------------------------------------------------------------------------
def _cut_kind_value(x: Any) -> str:
    return getattr(x, "value", x)


# Provenance: plan 2.4 R23 (F8: one c per cut); pm25_adaptation.py:572-577 (C_LOG = np.percentile(ypos, 1),
# ypos = finite positive donor y; "one constant for the whole run -- identical on the inner and the test
# pass"); plan 2.4 R25 (one weight model per cut serves that cut's decision and test pass).
def c_for_cut(donor_rows: Any) -> float:
    """R23: c = the 1st percentile of positive donor-row y at or before the cut.

    Rule: R23, G-DONOR (D62, D63 a). One c per LEAD cut, from the DonorRows of that lead's FIT cut
    (FitContext(lead, FIT).donor_rows(...)); the same c serves the lead's decision (or guard) surface
    and its test pass. The value is derive.rules.c_from_donor_y on the rows' labels, the one R23
    formula (derive's plan-time record calls it too; check with c_for_cut_against_plan).
    Returns c (> 0).
    Refuses: anything but FitContext's DonorRows (G-DONOR); donor rows of a GUARD cut (D63 a: the
    guard surface uses its lead's fit-cut c); no positive finite donor value (log_c is then not in
    the link set, R22).
    """
    from treeroute.fit.context import DonorRows   # at call time: fit.context imports the layer

    if not isinstance(donor_rows, DonorRows):
        raise LayerRefusal("G-DONOR", "c accepts only DonorRows (FitContext.donor_rows), got %s"
                           % type(donor_rows).__name__,
                           fix="hand the donor rows of the lead's fit cut from FitContext")
    if donor_rows.fold is None and _cut_kind_value(donor_rows.cut_kind) != CutKind.FIT.value:
        raise LayerRefusal("R23", "these donor rows are at the %r cut of lead %d; one c per lead comes "
                           "from that lead's FIT cut and serves its guard surface too (D63 a)"
                           % (_cut_kind_value(donor_rows.cut_kind), donor_rows.lead),
                           fix="use FitContext(lead, FIT).donor_rows")
    c, _ = _rules.c_from_donor_y(np.asarray(donor_rows.y))
    return c


def c_for_cut_against_plan(donor_rows: Any, derived: Mapping[str, Any]) -> float:
    """c_for_cut, then derive's check_r23_matches_run against derived.json's 'R23:lead=<lead>' entry:
    the same lead and cut, the same donor rows (row-key hash) and the same c. Returns c.
    Refuses: a derived.json without that entry; anything the check or c_for_cut refuses."""
    c = c_for_cut(donor_rows)
    key = "R23:lead=%d" % int(donor_rows.lead)
    if key not in derived:
        raise LayerRefusal("R23", "derived.json has no %s entry (plan wrote one per lead cut when "
                           "log_c is a link)" % key, fix="run plan (derive_all) first")
    _rules.check_r23_matches_run(derived[key], int(donor_rows.lead), int(donor_rows.cut), c,
                                 donor_rows.row_key_hash)
    return c


# ---------------------------------------------------------------------------------------------------
# R28: the legal clip
@dataclass(frozen=True)
class ClipCounts:
    """What R28's clip found on one array: rows, finite rows, rows below the legal minimum and above
    the legal maximum (before the clip), and NaN rows (baselines only)."""
    n_rows: int
    n_finite: int
    n_below: int
    n_above: int
    n_nan: int

    @property
    def preclip_rate(self) -> float:
        """Share of finite rows outside the legal range before the clip (NaN with no finite row)."""
        if self.n_finite == 0:
            return float("nan")
        return (self.n_below + self.n_above) / float(self.n_finite)


def legal_range_of(legal_range: Any) -> Tuple[float, float]:
    """(min, max) of a legal range: two numbers, not NaN, min < max; either may be infinite."""
    try:
        low, high = legal_range
    except (TypeError, ValueError):
        raise LayerRefusal("R28", "the legal range must be (min, max), got %r" % (legal_range,),
                           fix="pass the target's cited legal range") from None
    out = []
    for what, x in (("min", low), ("max", high)):
        if isinstance(x, bool) or not isinstance(x, (Real, np.floating, np.integer)):
            raise LayerRefusal("R28", "legal range %s must be a number, got %r" % (what, x))
        out.append(float(x))
    low, high = out
    if math.isnan(low) or math.isnan(high) or not low < high:
        raise LayerRefusal("R28", "the legal range [%r, %r] needs min < max" % (low, high),
                           fix="cite the product's documented valid range (plan 1.3)")
    return low, high


def clip_with_counts(pred: np.ndarray, legal_range: Tuple[float, float],
                     allow_nan: bool) -> Tuple[np.ndarray, ClipCounts]:
    """clip_to_legal with the counts behind the pre-clip rate (the one implementation)."""
    low, high = legal_range_of(legal_range)
    if not isinstance(allow_nan, bool):
        raise LayerRefusal("R28", "allow_nan must be a bool (False for predictions, True for "
                                  "baselines), got %r" % (allow_nan,))
    arr = np.asarray(pred)
    if arr.dtype.kind not in "iuf" or arr.dtype == np.bool_:
        raise LayerRefusal("R28", "predictions must be numeric, got dtype %s" % arr.dtype)
    v = np.array(arr, dtype=np.float64, copy=True)
    inf = np.isinf(v)
    if inf.any():
        raise LayerRefusal("R28", "%d prediction(s) are infinite; a back-transform overflowed or a "
                           "value was never computed" % int(inf.sum()),
                           fix="find the arm that produced them; nothing infinite is ever clipped")
    nan = np.isnan(v)
    n_nan = int(nan.sum())
    if n_nan and not allow_nan:
        raise LayerRefusal("R28", "%d prediction(s) are missing; a tree arm or trees-off must predict "
                           "every scored row (only a baseline may lack a value)" % n_nan,
                           fix="score only rows every arm predicts (a short-history unit waits for "
                               "the region fallback router)")
    finite = ~nan
    below = finite & (v < low)
    above = finite & (v > high)
    counts = ClipCounts(n_rows=int(v.size), n_finite=int(finite.sum()), n_below=int(below.sum()),
                        n_above=int(above.sum()), n_nan=n_nan)
    if counts.n_below or counts.n_above:
        v[below] = low
        v[above] = high
    return v, counts


# Provenance: plan 2.4 R28, 5 G-CLIP ("Legal-range clip on every back-transformed prediction and
# baseline; pre-clip rate logged"); pm25_forecast.py:530-531 (persistence floored at 0, replaced by R28).
def clip_to_legal(pred: np.ndarray, legal_range: Tuple[float, float],
                  allow_nan: bool) -> Tuple[np.ndarray, float, int]:
    """R28: clip to the target's legal range and report the pre-clip rate and the NaN count.

    Rule: R28, G-CLIP. Applied to every back-transformed prediction AND every baseline. The pre-clip
    rate is the share of finite rows outside the range before clipping (NaN when no row is finite);
    the caller logs it per arm and saves the pre-clip values in test_preds (clip_with_counts gives the
    counts). allow_nan=False for tree arms and trees-off (a prediction must exist for every scored
    row); allow_nan=True for baselines only (NaN passes through unclipped and is counted). A value
    inside the range is returned unchanged, bit for bit.
    Returns (clipped float64 values with NaN kept, pre-clip rate over finite rows, NaN count).
    Refuses: NaN in pred when allow_nan is False; +-inf anywhere; a legal range that is not
    (min, max) with min < max.
    """
    clipped, counts = clip_with_counts(pred, legal_range, allow_nan)
    return clipped, counts.preclip_rate, counts.n_nan


__all__ = ["link_forward", "link_inverse", "c_for_cut", "c_for_cut_against_plan", "ClipCounts",
           "legal_range_of", "clip_with_counts", "clip_to_legal"]
