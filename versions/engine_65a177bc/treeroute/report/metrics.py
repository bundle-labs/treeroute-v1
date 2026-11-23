"""Baselines, scores, detection, the jackknife, the single verdict, the equivalence band, the guard
tolerances and the row writers (plan 4.2 report/metrics.py row; R31-R36; leave one region out,
owner rulings D and E).

SCIENCE bodies for the owner-approved signatures in treeroute/_proposed/metrics.py (approved in the
owner rulings file, part A: every proposed default accepted, D74 ruled; the LORO addendum's wording
for the jackknife, the verdict and the band). Where the rulings file differs from a docstring there,
the rulings file wins.

Every score in any report comes from these functions on SAVED rows; no formula is re-implemented
elsewhere. Uncertainty is over GROUPS (the jackknife at 1.96, Q19 a), never seeds. No multiplicity
correction (Q21 a).

Rulings used (owner rulings file, part A; SIGNATURES_FOR_REVIEW.md defaults accepted):
  - D66  the last-5-years normal uses the 5 calendar years ending with the cut's year; a unit-season
         with no row there takes the unit's all-season mean over those years (R15's chain).
  - D67  option (a): mae, anomaly_r2, corr2, calibration_ratio and hit_rate REFUSE any non-finite
         pair; score_table picks the rows each column is scored on and prints the count. The same
         policy is applied to top10_detection (its quantiles are meaningless over missing values).
  - D68  anomaly R2 against the ARITHMETIC (identity-link) normal for every arm (the saved 'normal'
         column holds it).
  - D69  anomaly R2 is NaN under 10 rows.
  - D70  calibration ratio = mean(p) / mean(y); flagged outside [0.5, 2.0], report only (Q51 a).
  - D71  hit tolerance = half the donor rows' MEAN absolute deviation from their own reference.
  - D72  quantiles: numpy's default linear interpolation.
  - D73  stratum bins are right-closed.
  - D74  the R5 reading rule (owner ruling): HELPS = CI low end above 0 AND point estimate at or
         above +band; HURTS = CI high end below 0 AND point estimate at or below -band; EQUIVALENT =
         the whole CI inside +-band; IDENTICAL = every contrast 0; CANNOT TELL = everything else. The
         band is checked FIRST (fix F42): EQUIVALENT is tested before HELPS and HURTS. That order
         differs from the source's only when the SE is 0 and the point estimate sits exactly on +-band.
  - D75  the band's contrasts: each tree arm vs its own trees-off, and each arm vs its placebo.
  - D76  guard tolerance s uses ddof = 0; k is an input (C9 is not fixed yet).
  - D77  a group contrast of exactly 0 is not a sign flip (and a pooled contrast of exactly 0 has no
         sign, so nothing flips against it).
  - D78  trend slope = ordinary least squares of y on time in years, per donor unit.
  - D88  damped-persistence minimum counts: shared season key, more than 2 labels in the shared mean;
         separate season keys, at least 2 labels in each unit-season; otherwise the pair is dropped.

Readings awaiting the owner (flagged in the build report):
  - The last-5-years normal needs each history step's calendar year. The approved UnitHistory
    carries steps, not years, so the year is read off the engine's own step-index forms (R1): the
    annual index is the year; day ordinals (events) carry their year; monthly and composite indices
    are year x P + position, with P recovered from the cut and its year and checked against EVERY
    history row's season key. Any mismatch is refused.
  - The last-5-years normal of a unit with NO label in those years would take the donor-row mean,
    the last step of R15's chain, which is not an input of the approved signature: such rows stay
    NaN and are counted by score_table.
  - The blocked jackknife (report only) takes each overlap block's value as the mean of its groups'
    values, then runs the same jackknife over blocks. The alternative for the owner is the standard
    delete-a-block jackknife: the statistic stays the mean over GROUPS, each leave-out drops all of
    one block's groups at once, and the SE is taken over the B leave-out means. The two agree when
    every block holds one group; otherwise the current reading's centre is the mean of block means.
  - score_table's macro line is the unweighted mean over the table's key lines (over groups for a
    per-group table, Q20 a), each metric over the keys where it is defined, with the count beside.

Signature gaps (fail loudly until the owner rules):
  - trend_flag: the approved DonorRows carries steps or days, not years, and nothing else in the
    signature says how many steps make a year, so the per-year slope cannot be computed from it.
    trend_flag raises NotImplementedError; median_unit_slope is the arithmetic, on times in years.
  - D87 (anomaly persistence as extra printed baselines) has no ruling and no default: not built.

The shared shapes VerdictTag and RunKind are FIELD-IDENTICAL copies of the approved shapes in the
proposed common module, which engine code may not import (G-IMPORT). DonorRows and UnitHistory (the
approved containers of fit/context.py) are read by attribute, so the real containers and plain
stand-ins with the same fields both serve. The R22 link transform and the R28 clip are the layer's
single homes (layer.links.link_forward, layer.links.clip_to_legal, layer.links.legal_range_of): this
module calls them and re-implements neither.

Saved rows (the writers; plan 7.1 test_preds): one row per scored unit x step at one lead, with the
keys (unit, group, time, year, plus any declared extra key such as a stratum bin), lead, issue,
y (NaN kept: such rows are saved and never scored), normal (the arithmetic normal, or NaN on every
row when the kind has none), the legal range, for every arm (tree arms and trees-off) its clipped
prediction ('arm__<name>') and every placebo its clipped prediction ('placebo__<name>', R24: never
selectable, so a placebo is never saved under the arm prefix), each with its pre-clip value
('pre__<name>'), and every baseline ('base__<name>', NaN where it does not exist). score_table stamps
each scored column's kind ('arm', 'placebo' or 'baseline') on its lines.
"""
# Provenance for the module: pm25_adaptation.py:263-307 (score: anomaly-R2, MAE, hit at an absolute
# tolerance, guess-normal's mae0 / hit0), :144 (HIT_TOL = 2.0, ACAG's absolute error floor, now a
# package's declared measurement floor), :584-604 (add_clim), :894-930 (N2 guard), :1010-1027 (per
# region / per year tables), :1085-1130 (contrasts, the four-outcome tags, the N3 band from the median
# jackknife SE); pm25_forecast.py:321-344 (the R5 reading rule, ruled for D74), :492-533 (persistence and
# damped persistence, phi through the origin, both pair years out when lead % 12 == 0, U-2 replaces that
# test with the season-key rule); forecast_report.py:57-77 (strict top-10% detection); final_table.py:
# 77-79 (per-region q90, now strict); adaptation.py:525-537 (mae, jack); HEADLINE_QUESTIONS_AND_FIXES.md
# F42 (check the band first), F43 (clip), F46 (save keys, lead, normal, pre-clip), F59 (sign flips);
# HEADLINE_RUN_PLAN.md:31 and UNIFORM_SCHEMA_PLAN.md:61, 209 (calibration ratio, 0.5-2.0 flag).

import datetime as _dt
import math
import os
from dataclasses import dataclass
from enum import Enum
from numbers import Integral, Real
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from treeroute import engine_constants as K
from treeroute.errors import RefusedError
from treeroute.io.steps import as_int_array
from treeroute.layer.links import clip_to_legal, clip_with_counts, legal_range_of, link_forward
from treeroute.runs import atomic

_SHOW = 5

# IDENTICAL: every per-group contrast within this of 0.
# origin: pm25_adaptation.py:1104 and pm25_forecast.py:332 (np.allclose(dv, 0.0, atol=1e-12))
# OWNER CONFIRMS: not yet in engine_constants.py (outside this module's write scope).
IDENTICAL_ATOL = 1e-12
# D69: anomaly R2 is NaN under this many rows.
# origin: pm25_adaptation.py:290 (score returns nothing under 10 rows). OWNER CONFIRMS (constants file).
ANOMALY_R2_MIN_ROWS = 10
# D70 / Q51 a: calibration ratio flagged outside this band, report only.
# origin: HEADLINE_RUN_PLAN.md:31; UNIFORM_SCHEMA_PLAN.md:61, 209. OWNER CONFIRMS (constants file).
CALIBRATION_FLAG_BAND = (0.5, 2.0)
# D88: minimum labels in the mean an anomaly is taken from.
# origin: pm25_forecast.py:514 (shared cell-month: C > 2); D88 (separate keys: at least 2).
PHI_SHARED_MIN_LABELS = 3
PHI_SEPARATE_MIN_LABELS = 2
# U-2 / pm25_forecast.py:522: phi is clipped to [0, 1]; an undefined phi is 0.
PHI_BOUNDS = (0.0, 1.0)
# R34 / Q50: stratum edges are the donor rows' quartiles; fewer distinct values than this are refused.
STRATUM_QUANTILES = (0.25, 0.5, 0.75)
STRATUM_MIN_DISTINCT = 4

# The two references of the single verdict (R34; Q17 a, Q15 a).
REFERENCE_OWN_LINK_TREES_OFF = "own_link_trees_off"
REFERENCE_DONOR_ROW_MEDIAN = "donor_row_median"
REFERENCES = (REFERENCE_OWN_LINK_TREES_OFF, REFERENCE_DONOR_ROW_MEDIAN)

# Router kinds (R12), by value; the enum copies in derive/ and route/ compare by value here.
KIND_VALUES = ("per_unit", "region", "neighbour")
KIND_NEIGHBOUR = "neighbour"

# Saved-row schema (plan 7.1 test_preds; F46).
COL_UNIT = "unit"
COL_GROUP = "group"
COL_TIME = "time"
COL_YEAR = "year"
COL_LEAD = "lead"
COL_ISSUE = "issue"
COL_Y = "y"
COL_NORMAL = "normal"
COL_LEGAL_MIN = "legal_min"
COL_LEGAL_MAX = "legal_max"
ARM_PREFIX = "arm__"
PLACEBO_PREFIX = "placebo__"
PRE_PREFIX = "pre__"
BASELINE_PREFIX = "base__"
PREDICTION_PREFIXES = (ARM_PREFIX, PLACEBO_PREFIX)     # every row predicted, pre-clip value saved
SCORED_PREFIXES = PREDICTION_PREFIXES + (BASELINE_PREFIX,)
COLUMN_KIND = {ARM_PREFIX: "arm", PLACEBO_PREFIX: "placebo", BASELINE_PREFIX: "baseline"}
KEY_COLUMNS = (COL_UNIT, COL_GROUP, COL_TIME, COL_YEAR)
RESERVED_COLUMNS = KEY_COLUMNS + (COL_LEAD, COL_ISSUE, COL_Y, COL_NORMAL, COL_LEGAL_MIN, COL_LEGAL_MAX)
ROWS_BASIS_ALL = "all"

# score_table's metric columns (one line per rows basis x column x key; plus pooled and macro lines).
MACRO_METRICS = ("mae", "anom_r2", "corr2", "hit", "hit_floor", "calibration_ratio", "preclip_rate",
                 "detection")
LINE_KEY = "key"
LINE_POOLED = "pooled"
LINE_MACRO = "macro"


class MetricsRefusal(RefusedError):
    """A scoring rule refused (R31-R36, G-DONOR, G-FITCUT, G-CLIP, G-DECIDE). Nothing catches it."""


# ---------------------------------------------------------------------------------------------------
# Shapes (field-identical to the approved shared shapes)
class VerdictTag(Enum):
    """Single-verdict outcomes (R34, G-DECIDE)."""
    HELPS = "helps"
    HURTS = "hurts"
    EQUIVALENT = "does_not_help_equivalent"
    CANNOT_TELL = "cannot_tell"
    IDENTICAL = "identical"
    DECLINED = "declined"


class RunKind(Enum):
    """Stamped on every score line (plan 7.1). Only the headline-table builder refuses a kind."""
    HEADLINE = "headline"
    SMOKE = "smoke"
    LEGACY = "legacy"


@dataclass(frozen=True)
class DetectionScore:
    """R33 outcome."""
    score: float                       # NaN when undefined
    n_events: int
    event_share: float


@dataclass(frozen=True)
class JackknifeResult:
    """Leave-one-group-out jackknife over per-group values."""
    mean: float
    se: float
    low: float
    high: float
    n_groups: int


@dataclass(frozen=True)
class VerdictResult:
    """R34 single verdict."""
    tag: VerdictTag
    reference: str                     # 'own_link_trees_off' or 'donor_row_median'
    contrast: JackknifeResult          # per-group MAE(reference) - MAE(adopted); positive = adopted better
    pooled_contrast: float
    groups_better: int
    band: float
    sign_flip_groups: Tuple[str, ...]


# ---------------------------------------------------------------------------------------------------
# Private checks
def _refuse(rule, message, fix=None):
    raise MetricsRefusal(rule, message, fix=fix)


def _vector(values, what, rule="R34"):
    """A 1-D float64 array (numbers only; NaN kept for the caller to judge)."""
    arr = np.asarray(values)
    if arr.dtype.kind == "b" or arr.dtype.kind not in "iuf":
        _refuse(rule, "%s must be numeric, got dtype %s" % (what, arr.dtype))
    arr = arr.astype(np.float64)
    if arr.ndim != 1:
        _refuse(rule, "%s must be one-dimensional, got shape %s" % (what, arr.shape))
    return arr


def _finite_scalar(value, what, rule, positive=False):
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
        _refuse(rule, "%s must be a finite number, got %r" % (what, value))
    if positive and not float(value) > 0:
        _refuse(rule, "%s must be above 0, got %r" % (what, value))
    return float(value)


def _positions(mask):
    return np.flatnonzero(mask)[:_SHOW].tolist()


def _pair(y, p, rule="R34"):
    """D67 (a): labels and predictions of the rows given; a shape mismatch, no rows or any
    non-finite pair is refused (the caller picks the rows and prints the count)."""
    yy = _vector(y, "y", rule)
    pp = _vector(p, "the predictions", rule)
    if yy.shape != pp.shape:
        _refuse(rule, "y has %d rows and the predictions %d" % (yy.size, pp.size))
    if yy.size == 0:
        _refuse(rule, "no rows to score", fix="the caller picks the rows each column is scored on")
    bad = ~(np.isfinite(yy) & np.isfinite(pp))
    if bad.any():
        _refuse(rule, "%d non-finite (label, prediction) pairs (D67 a), e.g. at rows %s"
                % (int(bad.sum()), _positions(bad)),
                fix="pass only the rows where both exist; score_table picks them and prints the count")
    return yy, pp


def _legal(legal_range):
    """The target's legal range, read by the layer's one reader (layer.links.legal_range_of)."""
    return legal_range_of(legal_range)


def _clip(values, legal_range, allow_nan, what="the values"):
    """R28 through the layer's one clip (layer.links.clip_to_legal): NaN refused unless allow_nan
    (baselines: a row with no baseline value keeps NaN and is counted by score_table); +-inf always
    refused. The values must be one per row."""
    v = _vector(values, what, "R28")
    clipped, _, _ = clip_to_legal(v, legal_range, bool(allow_nan))
    return clipped


def _value_of(obj, allowed, what, rule):
    """The value of an enum member (any of the engine's field-identical copies) or a plain string."""
    value = getattr(obj, "value", obj)
    if not isinstance(value, str) or value not in allowed:
        _refuse(rule, "%s must be one of %s, got %r" % (what, list(allowed), obj))
    return value


def _donor_y(donor_rows, what, rule="G-DONOR"):
    """DonorRows.y: labels of donor rows at the cut (valid labels only, so any non-finite is refused)."""
    try:
        y = donor_rows.y
    except AttributeError:
        _refuse(rule, "%s is not a DonorRows (no field y)" % what,
                fix="pass the DonorRows that FitContext.donor_rows hands out")
    arr = _vector(y, "%s y" % what, rule)
    if arr.size == 0:
        _refuse(rule, "%s hold no row" % what)
    bad = ~np.isfinite(arr)
    if bad.any():
        _refuse(rule, "%s hold %d non-finite labels; DonorRows holds valid labels only"
                % (what, int(bad.sum())))
    return arr


def _history(history, what):
    """UnitHistory fields (unit_id, times, season_keys, y, cut), checked: one per label, valid labels
    only, every label at or before the cut, no time named twice."""
    try:
        unit_id, times, keys, labels, cut = (history.unit_id, history.times, history.season_keys,
                                             history.y, history.cut)
    except AttributeError:
        _refuse("G-DONOR", "%s is not a UnitHistory (unit_id, times, season_keys, y, cut)" % what)
    t = as_int_array(times, "the history times of %s" % what, rule="G-DONOR")
    k = as_int_array(keys, "the history season keys of %s" % what, rule="G-DONOR")
    y = _vector(labels, "the history labels of %s" % what, "G-DONOR")
    if not (t.size == k.size == y.size):
        _refuse("G-DONOR", "%s has %d times, %d season keys and %d labels; they must be one per label"
                % (what, t.size, k.size, y.size))
    if y.size and not np.isfinite(y).all():
        _refuse("G-DONOR", "%s holds non-finite labels; a UnitHistory holds valid labels only" % what)
    if isinstance(cut, bool) or not isinstance(cut, Integral):
        _refuse("G-FITCUT", "the cut of %s must be an integer, got %r" % (what, cut))
    cut = int(cut)
    after = t > cut
    if after.any():
        _refuse("G-FITCUT", "%s holds %d labels after its cut %d, e.g. times %s"
                % (what, int(after.sum()), cut, t[after][:_SHOW].tolist()))
    if np.unique(t).size != t.size:
        _refuse("G-DONOR", "%s names a label time twice" % what)
    return str(unit_id), t, k, y, cut


# ================================================================================================ R31
# Provenance: plan 2.5 R31 ("predict-zero ... All clipped (R28)").
def baseline_predict_zero(n_rows: int, legal_range: Tuple[float, float]) -> np.ndarray:
    """predict-zero, clipped to the legal range.

    Rule: R31, R28. Zero for every row, then the R28 clip (a legal minimum above 0 lifts it).
    Refuses: n_rows that is not a whole number at or above 0; an invalid legal range.
    """
    if isinstance(n_rows, bool) or not isinstance(n_rows, Integral) or int(n_rows) < 0:
        _refuse("R31", "n_rows must be a whole number at or above 0, got %r" % (n_rows,))
    return _clip(np.zeros(int(n_rows)), legal_range, allow_nan=False, what="predict-zero")


# Provenance: plan 2.5 R31; plan 2.2 R16 (decline target = the arithmetic normal).
def baseline_guess_normal(arithmetic_normal: np.ndarray, legal_range: Tuple[float, float]) -> np.ndarray:
    """guess-normal: the per-unit arithmetic normal (the R16 decline target), clipped.

    Rule: R31, R16, R28. Only where a normal exists (not neighbour).
    Refuses: NaN in the normal (and +-inf, as every clip).
    """
    v = _vector(arithmetic_normal, "the arithmetic normal", "R31")
    if np.isnan(v).any():
        _refuse("R31", "the arithmetic normal holds %d missing values; guess-normal exists only where a "
                "normal exists" % int(np.isnan(v).sum()))
    return _clip(v, legal_range, allow_nan=False, what="guess-normal")


def _years_of_times(times, keys, cut, cut_year, what):
    """The calendar year of each history time, read off the engine's step-index forms (R1, D28):
    annual steps ARE years; day ordinals (events) carry their year; monthly and composite steps are
    year x P + position (1..P), with P recovered from the cut and its year. Every row's season key is
    checked against the form (position in the year; the month for events; one class when annual)."""
    if cut == cut_year:
        if np.unique(keys).size > 1:
            _refuse("R31", "%s: the cut equals its year, so the steps are years, but the season keys "
                    "hold %d classes (annual data has one)" % (what, np.unique(keys).size))
        return times.copy()
    day_max = _dt.date.max.toordinal()
    if 1 <= cut <= day_max and _dt.date.fromordinal(cut).year == cut_year:
        if times.size and (times.min() < 1 or times.max() > day_max):
            _refuse("R31", "%s: the cut is a day ordinal but some history times are not" % what)
        dates = [_dt.date.fromordinal(int(t)) for t in times.tolist()]
        months = np.array([d.month for d in dates], dtype=np.int64)
        if not np.array_equal(months, keys):
            _refuse("R31", "%s: event season keys must be the month of the event date (R2)" % what)
        return np.array([d.year for d in dates], dtype=np.int64)
    # steps per year P with cut_year x P < cut <= (cut_year + 1) x P: the integers in
    # [cut / (cut_year + 1), cut / cut_year); exactly one for any calendar year above P
    per_year = -(-cut // (cut_year + 1))
    per_year_max = (cut - 1) // cut_year
    if per_year < 2 or per_year > per_year_max:
        _refuse("R31", "%s: the cut %d is not a step of the year %d in any step-index form (annual "
                "year, day ordinal, or year x steps per year + position)" % (what, cut, cut_year),
                fix="pass the calendar year that holds the cut")
    if per_year != per_year_max:
        _refuse("R31", "%s: the cut %d fits the year %d with %d to %d steps per year; the steps per "
                "year cannot be read off the cut" % (what, cut, cut_year, per_year, per_year_max))
    years = (times - 1) // per_year
    position = times - years * per_year
    if not np.array_equal(position, keys):
        bad = position != keys
        _refuse("R31", "%s: %d history season keys are not the step's position in its year for %d "
                "steps per year (read off the cut %d and its year %d), e.g. times %s"
                % (what, int(bad.sum()), per_year, cut, cut_year, times[bad][:_SHOW].tolist()))
    return years


# Provenance: plan 2.5 R31, Q26; D66 (5 calendar years ending with the cut's year; R15's chain).
def baseline_last5_normal(history: Any, kind: Any, season_keys: np.ndarray, cut_year: int,
                          legal_range: Tuple[float, float]) -> np.ndarray:
    """The last-5-years normal, printed beside guess-normal (Q26). Report only.

    Rule: R31, D66. Per season key, the mean of y over the unit's own rows in the RECENT_NORMAL_YEARS
    calendar years ending with the cut's year (every row at or before the cut); a season key with no
    row there takes the unit's all-season mean over those years (R15's chain). A unit with no row in
    those years would take the donor-row mean, which this signature does not receive: its rows stay
    NaN and are counted by score_table. Clipped (NaN kept).
    The year of each history step is read off the step-index form (see _years_of_times).
    Refuses: kind NEIGHBOUR (no normal exists); a history that is not a valid UnitHistory within its
    cut; a cut that is not a step of cut_year; season keys that do not match the step form.
    """
    if _value_of(kind, KIND_VALUES, "kind", "R31") == KIND_NEIGHBOUR:
        _refuse("R31", "the neighbour kind has no normal, so no last-5-years normal exists")
    what = "the last-5-years history"
    _, t, k, y, cut = _history(history, what)
    if isinstance(cut_year, bool) or not isinstance(cut_year, Integral) or int(cut_year) < 1:
        _refuse("R31", "cut_year must be a positive whole number, got %r" % (cut_year,))
    cut_year = int(cut_year)
    need = as_int_array(season_keys, "the season keys of the scored rows", rule="R31")
    years = _years_of_times(t, k, cut, cut_year, what)
    first = cut_year - int(K.RECENT_NORMAL_YEARS) + 1
    window = (years >= first) & (years <= cut_year)
    out = np.full(need.size, np.nan)
    if window.any():
        wy, wk = y[window], k[window]
        unit_mean = float(wy.mean())
        by_key = {int(key): float(wy[wk == key].mean()) for key in np.unique(wk).tolist()}
        out = np.array([by_key.get(int(key), unit_mean) for key in need.tolist()], dtype=np.float64)
    return _clip(out, legal_range, allow_nan=True, what="the last-5-years normal")


# Provenance: plan 2.5 R31; pm25_forecast.py:492 (persist = y at the issue step).
def baseline_persistence(y_issue: np.ndarray, legal_range: Tuple[float, float]) -> np.ndarray:
    """Persistence: the unit's label at the issue step (events: the last valid label before the issue
    date), clipped with NaN kept.

    Rule: R31, R28. The label comes from the vault's as-of rows (D54 a). A row whose issue step has
    no valid label stays NaN; score_table scores persistence on the rows where it exists and prints
    the count. Refuses nothing beyond the clip's own refusals (+-inf, an invalid legal range).
    """
    return _clip(y_issue, legal_range, allow_nan=True, what="persistence")


def shares_season_key(lead_steps: int, steps_per_year: int) -> bool:
    """U-2 / R2: whether a target step and its predecessor lead_steps back share the season key, i.e.
    whether the lead is a whole number of years (annual data: every lead).

    Refuses: a lead below 1 or steps per year below 1 (events have no steps per year: their pairs
    are judged pair by pair, M8)."""
    for v, what in ((lead_steps, "lead_steps"), (steps_per_year, "steps_per_year")):
        if isinstance(v, bool) or not isinstance(v, Integral) or int(v) < 1:
            _refuse("R31", "%s must be a whole number at or above 1, got %r" % (what, v))
    return int(lead_steps) % int(steps_per_year) == 0


# Provenance: pm25_forecast.py:494-527 (phi = regression through the origin of a(t) on a(t-L), both
# labels <= cut, leave-out means, clipped to [0, 1], undefined -> 0); U-2 (season-key rule); D88.
def damped_persistence_phi(histories: Mapping[str, Any], lead_steps: int,
                           same_season_key: bool) -> Mapping[str, float]:
    """Damped-persistence phi per unit, from (label, predecessor) pairs at or before the cut.

    Rule: R31, U-2, D88. For each unit: pairs (y(t), y(t - L)) with both labels in its history (all at
    or before the cut). Anomalies come from the unit x season-key mean with the pair's own labels
    left out: when target and predecessor SHARE the season key, BOTH are left out of their shared
    mean (at least PHI_SHARED_MIN_LABELS labels in it); otherwise each label leaves itself out of its
    own mean (at least PHI_SEPARATE_MIN_LABELS labels in each). Pairs short of those counts are
    dropped. phi = sum(a x a_pred) / sum(a_pred^2), clipped to [0, 1]; undefined phi (no pair, or a
    zero denominator) is 0. Grids only: the events' (visit, previous visit) pairs are built with the
    as-of label view (M8).
    Refuses: lead_steps below 1; no history; a history that is not a valid UnitHistory, stored
    under another unit's id, or at another cut than the others; a pair whose season keys contradict
    same_season_key.
    """
    if isinstance(lead_steps, bool) or not isinstance(lead_steps, Integral) or int(lead_steps) < 1:
        _refuse("R31", "lead_steps must be a whole number at or above 1, got %r" % (lead_steps,))
    if not isinstance(same_season_key, (bool, np.bool_)):
        _refuse("R31", "same_season_key must be True or False, got %r" % (same_season_key,))
    if not isinstance(histories, Mapping) or not histories:
        _refuse("R31", "damped persistence needs at least one unit history")
    lead = int(lead_steps)
    shared = bool(same_season_key)
    cuts = set()
    out: Dict[str, float] = {}
    for unit in sorted(histories):
        uid, t, k, y, cut = _history(histories[unit], "the history of %r" % (unit,))
        if uid != str(unit):
            _refuse("G-DONOR", "the history stored under %r belongs to unit %r" % (unit, uid))
        cuts.add(cut)
        if len(cuts) > 1:
            _refuse("G-FITCUT", "the unit histories are at different cuts %s; phi uses one lead's cut"
                    % sorted(cuts))
        keys = np.unique(k)
        sums = {int(key): float(y[k == key].sum()) for key in keys.tolist()}
        counts = {int(key): int((k == key).sum()) for key in keys.tolist()}
        pos = {int(ti): i for i, ti in enumerate(t.tolist())}
        a_list, ap_list = [], []
        for i, ti in enumerate(t.tolist()):
            j = pos.get(ti - lead)
            if j is None:
                continue
            ki, kj = int(k[i]), int(k[j])
            if (ki == kj) != shared:
                _refuse("R31", "unit %r: the pair at times (%d, %d) has season keys (%d, %d), which "
                        "contradicts same_season_key=%s (U-2)" % (unit, ti, ti - lead, ki, kj, shared),
                        fix="pass shares_season_key(lead_steps, steps_per_year)")
            yi, yp = float(y[i]), float(y[j])
            if shared:
                c = counts[ki]
                if c < PHI_SHARED_MIN_LABELS:
                    continue
                m = (sums[ki] - yi - yp) / (c - 2)
                a_list.append(yi - m)
                ap_list.append(yp - m)
            else:
                ci, cj = counts[ki], counts[kj]
                if ci < PHI_SEPARATE_MIN_LABELS or cj < PHI_SEPARATE_MIN_LABELS:
                    continue
                a_list.append(yi - (sums[ki] - yi) / (ci - 1))
                ap_list.append(yp - (sums[kj] - yp) / (cj - 1))
        a, ap = np.array(a_list), np.array(ap_list)
        den = float(np.sum(ap ** 2)) if ap.size else 0.0
        if den > 0:
            phi = float(np.clip(float(np.sum(a * ap)) / den, PHI_BOUNDS[0], PHI_BOUNDS[1]))
        else:
            phi = 0.0
        out[str(unit)] = phi
    return out


# Provenance: pm25_forecast.py:524 (damped = clim(t) + phi x (y_issue - clim(issue))).
def baseline_damped_persistence(normal_target: np.ndarray, normal_issue: np.ndarray, y_issue: np.ndarray,
                                phi: np.ndarray, legal_range: Tuple[float, float]) -> np.ndarray:
    """Damped persistence: normal(t) + phi x (y_issue - normal(issue)), clipped with NaN kept.

    Rule: R31, R28. The arithmetic normal of each step's season key. A row with no issue label stays
    NaN (counted by score_table).
    Refuses: shape mismatches; non-finite normals; phi outside [0, 1] or non-finite.
    """
    nt = _vector(normal_target, "the target-step normal", "R31")
    ni = _vector(normal_issue, "the issue-step normal", "R31")
    yi = _vector(y_issue, "the issue-step label", "R31")
    ph = _vector(phi, "phi", "R31")
    if not (nt.size == ni.size == yi.size == ph.size):
        _refuse("R31", "damped persistence needs one value per row: %d target normals, %d issue "
                "normals, %d issue labels, %d phi" % (nt.size, ni.size, yi.size, ph.size))
    if not (np.isfinite(nt).all() and np.isfinite(ni).all()):
        _refuse("R31", "the normals must be finite on every row")
    if not np.isfinite(ph).all() or (ph < PHI_BOUNDS[0]).any() or (ph > PHI_BOUNDS[1]).any():
        _refuse("R31", "phi must lie in [0, 1] on every row (damped_persistence_phi)")
    return _clip(nt + ph * (yi - ni), legal_range, allow_nan=True, what="damped persistence")


# Provenance: plan 2.5 R31 ("Neighbour: donor-row median (Q15 a)"); replaces the training mean at
# adaptation.py:1633.
def baseline_donor_median(donor_rows: Any) -> float:
    """The donor-row median of y: the neighbour kind's reference and pool fallback.

    Rule: R31, R34, G-DONOR. Median over DonorRows only.
    Refuses: no row; any non-finite label (DonorRows holds valid labels only).
    """
    return float(np.median(_donor_y(donor_rows, "the donor rows")))


# ============================================================================================ scores
# Provenance: adaptation.py:525-527; pm25_adaptation.py:303.
def mae(y: np.ndarray, p: np.ndarray) -> float:
    """Mean absolute error in y units over the rows given.

    Rule: R34, D67 (a). Refuses: shape mismatch, no rows, a non-finite pair.
    """
    yy, pp = _pair(y, p)
    return float(np.mean(np.abs(yy - pp)))


# Provenance: pm25_adaptation.py:287-294 (anomalies against the normal; 1 - sum((ay - ap)^2) / sum(ay^2);
# NaN when the denominator is 0).
def anomaly_r2(y: np.ndarray, p: np.ndarray, normal: np.ndarray) -> float:
    """Anomaly R2 against the per-unit normal: 1 - SSE(p) / SSE(normal).

    Rule: R34, D67 (a), D68 (the ARITHMETIC normal for every arm), D69 (NaN under 10 rows).
    Guess-normal scores 0 by construction. NaN when SSE(normal) is 0.
    Refuses: shape mismatch; no rows; a non-finite label, prediction or normal.
    """
    yy, pp = _pair(y, p)
    nn = _vector(normal, "the normal")
    if nn.shape != yy.shape:
        _refuse("R34", "the normal has %d rows and y %d" % (nn.size, yy.size))
    if not np.isfinite(nn).all():
        _refuse("R34", "the normal holds %d non-finite values (D67 a)" % int((~np.isfinite(nn)).sum()),
                fix="anomaly R2 exists only where a normal exists")
    if yy.size < ANOMALY_R2_MIN_ROWS:
        return float("nan")
    ay, ap = yy - nn, pp - nn
    s0 = float(np.sum(ay ** 2))
    if not s0 > 0:
        return float("nan")
    return 1.0 - float(np.sum((ay - ap) ** 2)) / s0


# Provenance: plan 2.5 R34 (corr2 beside MAE, Q37).
def corr2(y: np.ndarray, p: np.ndarray) -> float:
    """Squared Pearson correlation between labels and predictions; printed beside MAE, never used to
    select.

    Rule: R34, R27, D67 (a). NaN when either side is constant.
    Refuses: shape mismatch; no rows; a non-finite pair.
    """
    yy, pp = _pair(y, p)
    if yy.max() == yy.min() or pp.max() == pp.min():
        return float("nan")
    yc, pc = yy - yy.mean(), pp - pp.mean()
    syy, spp = float(np.sum(yc * yc)), float(np.sum(pc * pc))
    if not (syy > 0 and spp > 0):
        return float("nan")
    r = float(np.sum(yc * pc)) / math.sqrt(syy * spp)
    return r * r


# Provenance: HEADLINE_RUN_PLAN.md:31, UNIFORM_SCHEMA_PLAN.md:61, 209; D70.
def calibration_ratio(y: np.ndarray, p: np.ndarray) -> float:
    """Calibration ratio: mean prediction / mean truth (D70). Logged per arm; report only.

    Rule: R28, R34, G-RANGE, D67 (a). NaN when the mean truth is 0.
    Refuses: shape mismatch; no rows; a non-finite pair.
    """
    yy, pp = _pair(y, p)
    my = float(np.mean(yy))
    if my == 0:
        return float("nan")
    return float(np.mean(pp)) / my


def calibration_flagged(ratio: float) -> bool:
    """D70 / Q51 a: True when a finite calibration ratio lies outside CALIBRATION_FLAG_BAND (report
    only, never a choice). An undefined (NaN) ratio is not flagged; its NaN is printed instead."""
    r = float(ratio)
    if not math.isfinite(r):
        return False
    return r < CALIBRATION_FLAG_BAND[0] or r > CALIBRATION_FLAG_BAND[1]


# Provenance: plan 2.4 R28 (pre-clip rate logged per arm).
def preclip_rate(pre_clip: np.ndarray, legal_range: Tuple[float, float]) -> float:
    """Share of predictions outside the legal range before the clip, from the saved pre-clip values.

    Rule: R28, R34. The rate is the layer's one implementation (layer.links.clip_with_counts'
    ClipCounts.preclip_rate) on the saved values; with no NaN allowed it is over every row.
    Refuses: NaN in pre_clip; no rows; an invalid legal range; +-inf (the layer's clip never clips
    an infinite value, and assemble_rows saves finite pre-clip values only).
    """
    legal = _legal(legal_range)
    v = _vector(pre_clip, "the pre-clip values", "R28")
    if v.size == 0:
        _refuse("R28", "no pre-clip values to rate")
    if np.isnan(v).any():
        _refuse("R28", "the pre-clip values hold %d missing values" % int(np.isnan(v).sum()))
    return float(clip_with_counts(v, legal, False)[1].preclip_rate)


# Provenance: plan 2.5 R32 (D9 with the mean, D71); pm25_adaptation.py:144 (the old absolute tolerance,
# now a package's declared measurement floor, printed beside).
def hit_tolerance(donor_rows: Any, donor_reference: np.ndarray) -> float:
    """R32: half the donor rows' MEAN absolute deviation from their own normal (neighbour: from the
    donor-row median).

    Rule: R32, G-DONOR, D71. tol = HIT_TOLERANCE_DEVIATION_SHARE x mean(|y - reference|) over donor
    rows at the cut. A declared measurement_error_floor is printed beside (a second hit rate), never
    used to select.
    Refuses: a reference that is not one finite value per donor row; a tolerance of 0.
    """
    y = _donor_y(donor_rows, "the donor rows", "R32")
    ref = _vector(donor_reference, "the donor reference", "R32")
    if ref.shape != y.shape:
        _refuse("R32", "the donor reference has %d values for %d donor rows" % (ref.size, y.size))
    if not np.isfinite(ref).all():
        _refuse("R32", "the donor reference holds %d non-finite values" % int((~np.isfinite(ref)).sum()))
    tol = float(K.HIT_TOLERANCE_DEVIATION_SHARE) * float(np.mean(np.abs(y - ref)))
    if not tol > 0:
        _refuse("R32", "the hit tolerance is 0: every donor row equals its reference",
                fix="G-SUPPORT refuses a constant target first")
    return tol


# Provenance: pm25_adaptation.py:305 (hit = mean(|y - p| <= tol), inclusive).
def hit_rate(y: np.ndarray, p: np.ndarray, tol: float) -> float:
    """Share of rows within +/- tol of the truth (inclusive).

    Rule: R32, R34, D67 (a). Printed with guess-normal's hit rate beside it.
    Refuses: tol that is not a finite number above 0; shape mismatch; no rows; a non-finite pair.
    """
    t = _finite_scalar(tol, "the hit tolerance", "R32", positive=True)
    yy, pp = _pair(y, p)
    return float(np.mean(np.abs(yy - pp) <= t))


# Provenance: plan 2.5 R33, U-3; forecast_report.py:57-77; final_table.py:77-79 (per group, now strict).
def top10_detection(y: np.ndarray, p: np.ndarray) -> DetectionScore:
    """R33: the one strict top-10% detection score.

    Rule: R33, U-3, D72. Event = y strictly above the rows' own 90th percentile. Score = the share
    of events whose prediction is strictly above the predictions' own 90th percentile. NaN when
    there are fewer than DETECTION_MIN_EVENTS events or more than DETECTION_MAX_EVENT_SHARE of the
    rows are events; the event count and share are always returned. Pooled rows use the pooled q90;
    one group's rows use their own. A yes/no target whose q90 equals its maximum has no event: NaN.
    Refuses: shape mismatch; no rows; a non-finite pair (the D67 policy).
    """
    yy, pp = _pair(y, p, rule="R33")
    q = 1.0 - float(K.DETECTION_TOP_SHARE)
    events = yy > np.quantile(yy, q)
    n_events = int(events.sum())
    share = n_events / float(yy.size)
    if n_events < int(K.DETECTION_MIN_EVENTS) or share > float(K.DETECTION_MAX_EVENT_SHARE):
        return DetectionScore(score=float("nan"), n_events=n_events, event_share=share)
    return DetectionScore(score=float(np.mean(pp[events] > np.quantile(pp, q))), n_events=n_events,
                          event_share=share)


# Provenance: plan 2.5 R34 ("quartile edges from donor rows"); Q50; D72, D73.
def stratum_edges(donor_rows: Any, stratum_values: np.ndarray) -> Tuple[float, float, float]:
    """Quartile edges of a declared report_stratum column, from donor rows only.

    Rule: R34, G-DONOR, D72. Test rows are binned with them by stratum_bins (right-closed, D73).
    Refuses: stratum values that are not one finite value per donor row; fewer than 4 distinct values.
    """
    y = _donor_y(donor_rows, "the donor rows", "R34")
    v = _vector(stratum_values, "the stratum values", "R34")
    if v.shape != y.shape:
        _refuse("R34", "%d stratum values for %d donor rows" % (v.size, y.size))
    if not np.isfinite(v).all():
        _refuse("R34", "the stratum values hold %d non-finite values; the caller picks the rows"
                % int((~np.isfinite(v)).sum()))
    distinct = np.unique(v).size
    if distinct < STRATUM_MIN_DISTINCT:
        _refuse("R34", "the stratum column has %d distinct donor values; quartiles need at least %d"
                % (distinct, STRATUM_MIN_DISTINCT))
    q = np.quantile(v, STRATUM_QUANTILES)
    return float(q[0]), float(q[1]), float(q[2])


def stratum_bins(values: np.ndarray, edges: Tuple[float, float, float]) -> np.ndarray:
    """D73: the stratum (1-4) of each row, right-closed: 1 = (-inf, q25], 2 = (q25, q50],
    3 = (q50, q75], 4 = (q75, inf).

    Refuses: edges that are not three finite non-decreasing numbers; a non-finite value (the caller
    picks the rows)."""
    try:
        e = tuple(float(x) for x in edges)
    except (TypeError, ValueError):
        _refuse("R34", "stratum edges must be three numbers, got %r" % (edges,))
    if len(e) != 3 or not all(math.isfinite(x) for x in e) or not (e[0] <= e[1] <= e[2]):
        _refuse("R34", "stratum edges must be three finite non-decreasing numbers, got %r" % (edges,))
    v = _vector(values, "the stratum values", "R34")
    if not np.isfinite(v).all():
        _refuse("R34", "the stratum values hold %d non-finite values; the caller picks the rows"
                % int((~np.isfinite(v)).sum()))
    return (np.searchsorted(np.asarray(e), v, side="left") + 1).astype(np.int64)


# ========================================================================================= tables
def _line_metrics(y, p, normal, pre, legal, tol, floor, units):
    """Every R34 metric of one column on the rows given (already selected by the caller)."""
    n = int(y.size)
    rec: Dict[str, Any] = {"n": n, "n_units": int(np.unique(units).size) if n else 0}
    if n == 0:
        rec.update(mae=np.nan, anom_r2=np.nan, anom_r2_n=0, corr2=np.nan, hit=np.nan, hit_floor=np.nan,
                   calibration_ratio=np.nan, calibration_flag=False, preclip_rate=np.nan, preclip_n=0,
                   detection=np.nan, detection_events=0, detection_event_share=np.nan)
        return rec
    rec["mae"] = mae(y, p)
    if normal is not None:
        rec["anom_r2"], rec["anom_r2_n"] = anomaly_r2(y, p, normal), n
    else:
        rec["anom_r2"], rec["anom_r2_n"] = np.nan, 0
    rec["corr2"] = corr2(y, p)
    rec["hit"] = hit_rate(y, p, tol)
    rec["hit_floor"] = hit_rate(y, p, floor) if floor is not None else np.nan
    ratio = calibration_ratio(y, p)
    rec["calibration_ratio"], rec["calibration_flag"] = ratio, calibration_flagged(ratio)
    if pre is not None:
        rec["preclip_rate"], rec["preclip_n"] = preclip_rate(pre, legal), n
    else:
        rec["preclip_rate"], rec["preclip_n"] = np.nan, 0
    det = top10_detection(y, p)
    rec["detection"], rec["detection_events"] = det.score, det.n_events
    rec["detection_event_share"] = det.event_share
    return rec


def _prefix_of(column):
    """The scored prefix of a column name, or None (the prefixes do not start one another)."""
    if isinstance(column, str):
        for prefix in SCORED_PREFIXES:
            if column.startswith(prefix):
                return prefix
    return None


def _scored_columns(preds):
    cols = [c for c in preds.columns if _prefix_of(c) is not None]
    for c in cols:
        if len(c) == len(_prefix_of(c)):
            _refuse("R34", "column %r names no arm, placebo or baseline" % c)
    return cols


def _column_kind(column):
    return COLUMN_KIND[_prefix_of(column)]


def _prediction_of_pre(preds, pre_column):
    """The one arm or placebo column a 'pre__<name>' column belongs to."""
    name = pre_column[len(PRE_PREFIX):]
    owners = [p + name for p in PREDICTION_PREFIXES if p + name in preds.columns]
    if not owners:
        _refuse("R34", "pre-clip column %r has no arm or placebo column (%s)"
                % (pre_column, " or ".join(repr(p + name) for p in PREDICTION_PREFIXES)))
    if len(owners) > 1:
        _refuse("R34", "pre-clip column %r belongs to both %s; an arm and a placebo never share a name"
                % (pre_column, owners))
    return owners[0]


def _run_kind_value(run_kind):
    return _value_of(run_kind, tuple(k.value for k in RunKind), "run_kind", "R34")


def _table_legal(preds, needed):
    """The legal range the saved rows carry (one value per run), when a pre-clip column needs it."""
    if not needed:
        return None
    missing = [c for c in (COL_LEGAL_MIN, COL_LEGAL_MAX) if c not in preds.columns]
    if missing:
        _refuse("R34", "pre-clip columns are saved but the legal range columns %s are not" % missing)
    lo = pd.unique(preds[COL_LEGAL_MIN].to_numpy(dtype=np.float64))
    hi = pd.unique(preds[COL_LEGAL_MAX].to_numpy(dtype=np.float64))
    if lo.size != 1 or hi.size != 1:
        _refuse("R34", "the saved legal range is not one value per run (%d minima, %d maxima)"
                % (lo.size, hi.size))
    return _legal((float(lo[0]), float(hi[0])))


# Provenance: plan 2.5 R34, 7.1; pm25_adaptation.py:1010-1027 (per region / per year tables); Q20 a.
def score_table(preds: pd.DataFrame, by: Tuple[str, ...], tol: float, floor: Optional[float],
                run_kind: Any) -> pd.DataFrame:
    """Scoring table over saved rows, one line per rows basis x scored column x (by-key), with a
    pooled line and a macro line per rows basis x column.

    Rule: R34, D67 (a), D68-D72. Scored columns are every 'arm__<name>', 'placebo__<name>' and
    'base__<name>' column; 'column_kind' says which ('arm', 'placebo', 'baseline'; a placebo is
    never selectable, R24). An arm or placebo predicts every scored row (R28: only a baseline may
    lack a value), so one missing on a labelled row is refused.
    Rows: a column is scored on the rows where y and the column are finite (D67 a: the count is
    printed as 'n'; 'rows_missing' counts the labelled rows of the line where the column is
    missing; 'n_unlabelled' counts the line's rows with no label, which no column is scored on).
    For every baseline that is missing on some labelled rows (persistence without an issue label,
    the last-5-years normal of a unit without recent rows), every column is ALSO scored on that
    baseline's rows: those lines carry its name in 'rows_basis' (otherwise 'all').
    Per line: MAE; anomaly R2 against the saved 'normal' column (D68; NaN with anom_r2_n 0 when the
    kind has no normal, i.e. the column is NaN on every labelled row); corr2; the hit rate at tol and,
    beside it, at the declared floor; the calibration ratio and its flag; the pre-clip rate from
    'pre__<name>' when saved (with the saved legal range); strict top-10% detection with its event
    count and share (each key uses its own rows' q90, the pooled line the pooled q90); the scored
    units. Pooled line: every scored row. Macro line: the unweighted mean over the key lines, each
    metric over the keys where it is defined, with '<metric>_keys' counting them (over groups for a
    per-group table, Q20 a). Every line carries run_kind; score_table serves every run folder and
    never refuses a kind (the headline-table builder reads the stamp).
    Inputs: preds, the saved rows (see the module docstring); by, the key columns (e.g. ('year',),
    ('group',), ('stratum',)); an empty tuple gives the pooled line only. tol: the R32 tolerance.
    floor: the declared measurement_error_floor, or None. run_kind: RunKind (or its value).
    Returns: the table (attrs['by'] records the keys).
    Refuses: preds without the unit, y, normal or key columns; no scored column; a missing key value;
    an infinite label or scored value; a normal that exists on some labelled rows and not others; an
    arm or placebo missing on a labelled row; a pre-clip column without its arm or placebo, or without the saved legal range;
    tol or floor that is not a finite number above 0.
    """
    if not isinstance(preds, pd.DataFrame):
        _refuse("R34", "score_table reads a DataFrame of saved rows, got %s" % type(preds).__name__)
    if isinstance(by, str) or not isinstance(by, tuple) or not all(isinstance(b, str) and b for b in by):
        _refuse("R34", "by must be a tuple of column names, got %r" % (by,))
    if len(set(by)) != len(by):
        _refuse("R34", "by names a column twice: %r" % (by,))
    tol = _finite_scalar(tol, "the hit tolerance", "R32", positive=True)
    if floor is not None:
        floor = _finite_scalar(floor, "the declared measurement floor", "R32", positive=True)
    kind_value = _run_kind_value(run_kind)
    missing = [c for c in (COL_UNIT, COL_Y, COL_NORMAL) + tuple(by) if c not in preds.columns]
    if missing:
        _refuse("R34", "the saved rows lack the columns %s the lines need" % missing)
    columns = _scored_columns(preds)
    if not columns:
        _refuse("R34", "the saved rows hold no scored column (%s)"
                % ", ".join(p + "<name>" for p in SCORED_PREFIXES))
    pre_cols = [c for c in preds.columns if isinstance(c, str) and c.startswith(PRE_PREFIX)]
    pre_of = {_prediction_of_pre(preds, c): c for c in pre_cols}
    legal = _table_legal(preds, bool(pre_cols))
    for b in by:
        if preds[b].isna().any():
            _refuse("R34", "key column %r is missing on %d rows" % (b, int(preds[b].isna().sum())))

    y = preds[COL_Y].to_numpy(dtype=np.float64)
    if np.isinf(y).any():
        _refuse("R34", "y holds %d infinite values; a missing label is NaN" % int(np.isinf(y).sum()))
    labelled = np.isfinite(y)
    n_unlabelled = int((~labelled).sum())
    normal_all = preds[COL_NORMAL].to_numpy(dtype=np.float64)
    has_normal = np.isfinite(normal_all[labelled])
    if has_normal.any() and not has_normal.all():
        _refuse("R34", "the normal exists on %d labelled rows and not on %d; it exists everywhere or "
                "nowhere (neighbour)" % (int(has_normal.sum()), int((~has_normal).sum())))
    normal_ok = bool(has_normal.any())
    units = preds[COL_UNIT].to_numpy()
    values = {c: preds[c].to_numpy(dtype=np.float64) for c in columns}
    finite = {c: np.isfinite(values[c]) for c in columns}
    for c in columns:
        if np.isinf(values[c]).any():
            _refuse("G-CLIP", "%s %r holds %d infinite values; a missing value is NaN and nothing "
                    "infinite is ever clipped" % (_column_kind(c), c, int(np.isinf(values[c]).sum())))
        if _prefix_of(c) in PREDICTION_PREFIXES and not finite[c][labelled].all():
            _refuse("R28", "%s %r is missing on %d labelled rows; an arm or placebo predicts every "
                    "scored row (only a baseline may lack a value), so contrasts never compare MAEs "
                    "over different rows" % (_column_kind(c), c, int((~finite[c][labelled]).sum())),
                    fix="save only rows every arm predicts (assemble_rows refuses such arms)")
    pre_values = {c: preds[p].to_numpy(dtype=np.float64) for c, p in pre_of.items()}
    partial = [c for c in columns if not finite[c][labelled].all()]      # baselines only
    bases = [ROWS_BASIS_ALL] + partial

    if by:
        groups = preds.groupby(list(by), sort=True).indices
        key_items = sorted(groups.items(), key=lambda kv: kv[0])
    else:
        key_items = []

    lines: List[Dict[str, Any]] = []
    for basis in bases:
        basis_mask = labelled if basis == ROWS_BASIS_ALL else (labelled & finite[basis])
        for col in columns:
            mask = basis_mask & finite[col]
            head = {"run_kind": kind_value, "rows_basis": basis, "column": col,
                    "column_kind": _column_kind(col)}
            pre = pre_values.get(col)
            key_recs = []

            def _metrics(rows):
                return _line_metrics(y[rows], values[col][rows],
                                     normal_all[rows] if normal_ok else None,
                                     pre[rows] if pre is not None else None, legal, tol, floor,
                                     units[rows])

            for key, idx in key_items:
                idx = np.asarray(idx)
                rows = idx[mask[idx]]
                rec = dict(head, line=LINE_KEY)
                kv = key if isinstance(key, tuple) else (key,)
                rec.update({b: v for b, v in zip(by, kv)})
                rec.update(_metrics(rows))
                rec["rows_missing"] = int((basis_mask[idx] & ~finite[col][idx]).sum())
                rec["n_unlabelled"] = int((~labelled[idx]).sum())
                key_recs.append(rec)
                lines.append(rec)
            rows = np.flatnonzero(mask)
            pooled = dict(head, line=LINE_POOLED)
            pooled.update({b: None for b in by})
            pooled.update(_metrics(rows))
            pooled["rows_missing"] = int((basis_mask & ~finite[col]).sum())
            pooled["n_unlabelled"] = n_unlabelled
            lines.append(pooled)
            if key_recs:
                macro = dict(head, line=LINE_MACRO)
                macro.update({b: None for b in by})
                macro.update(n=pooled["n"], n_units=pooled["n_units"], rows_missing=pooled["rows_missing"],
                             n_unlabelled=n_unlabelled, anom_r2_n=pooled["anom_r2_n"],
                             preclip_n=pooled["preclip_n"], detection_events=np.nan,
                             detection_event_share=np.nan)
                for m in MACRO_METRICS:
                    vals = np.array([r[m] for r in key_recs], dtype=np.float64)
                    ok = np.isfinite(vals)
                    macro[m] = float(vals[ok].mean()) if ok.any() else np.nan
                    macro[m + "_keys"] = int(ok.sum())
                macro["calibration_flag"] = calibration_flagged(macro["calibration_ratio"])
                lines.append(macro)

    order = (["run_kind", "rows_basis", "column", "column_kind", "line"] + list(by)
             + ["n", "n_units", "rows_missing", "n_unlabelled", "mae", "anom_r2", "anom_r2_n", "corr2", "hit",
                "hit_floor", "calibration_ratio", "calibration_flag", "preclip_rate", "preclip_n",
                "detection", "detection_events", "detection_event_share"]
             + [m + "_keys" for m in MACRO_METRICS])
    table = pd.DataFrame(lines)
    for c in order:
        if c not in table.columns:
            table[c] = np.nan
    table = table[order]
    table.attrs["by"] = tuple(by)
    return table


def metric_by_key(table: pd.DataFrame, column: str, metric: str, key: str,
                  rows_basis: str = ROWS_BASIS_ALL) -> Dict[Any, float]:
    """{key value: metric} from a one-key score table's key lines (e.g. per-group MAE for the verdict).

    Every value returned is over ALL the rows of its key under the rows basis: a line where the
    column is missing on some of those rows (rows_missing above 0) is refused, so two maps read on
    the same basis are always over the same rows and their per-key contrast is paired
    (band_from_pairs, single_verdict). A baseline missing on some rows is read on its own basis
    (rows_basis=<its column>), where every column is scored on its rows.
    Refuses: a table without that key, metric or rows_missing; no line for the column and rows
    basis; a key named twice; a line with rows_missing above 0."""
    for c in ("line", "column", "rows_basis", "rows_missing", key, metric):
        if c not in table.columns:
            _refuse("R34", "the score table has no column %r" % c)
    sel = table[(table["line"] == LINE_KEY) & (table["column"] == column)
                & (table["rows_basis"] == rows_basis)]
    if sel.empty:
        _refuse("R34", "the score table has no key line for column %r on rows %r" % (column, rows_basis))
    keys = sel[key].tolist()
    if len(set(keys)) != len(keys):
        _refuse("R34", "the score table names a %r value twice for column %r" % (key, column))
    short = sel[sel["rows_missing"] > 0]
    if not short.empty:
        _refuse("R34", "column %r is missing on %d rows of the %r basis (in %d %r values, e.g. %s), so "
                "its %s there is over fewer rows than the other columns' and a contrast would compare "
                "different rows" % (column, int(short["rows_missing"].sum()), rows_basis, len(short),
                                    key, short[key].tolist()[:_SHOW], metric),
                fix="read it on its own rows: rows_basis=%r" % column)
    return {k: float(v) for k, v in zip(keys, sel[metric].tolist())}


# ====================================================================================== jackknife
# Provenance: adaptation.py:530-537 (jack); Q19 a.
def group_jackknife(per_group_values: np.ndarray) -> JackknifeResult:
    """Leave-one-group-out jackknife at JACKKNIFE_Z (1.96) over per-group values.

    Rule: R34, Q19 a. mean = the mean of the per-group values; leave-one-out means; SE =
    sqrt((n-1)/n x sum of squared deviations of the leave-one-out means from their mean); interval
    mean +/- 1.96 SE. Fewer than 3 groups: SE and interval NaN. No multiplicity correction.
    Refuses: no value; non-finite values.
    """
    v = _vector(per_group_values, "the per-group values")
    if v.size == 0:
        _refuse("R34", "the jackknife needs at least one group value")
    if not np.isfinite(v).all():
        _refuse("R34", "the per-group values hold %d non-finite values" % int((~np.isfinite(v)).sum()))
    n = int(v.size)
    if n < 3:
        return JackknifeResult(mean=float(v.mean()), se=float("nan"), low=float("nan"),
                               high=float("nan"), n_groups=n)
    jk = np.array([np.delete(v, i).mean() for i in range(n)])
    se = float(np.sqrt((n - 1) / n * ((jk - jk.mean()) ** 2).sum()))
    z = float(K.JACKKNIFE_Z)
    return JackknifeResult(mean=float(v.mean()), se=se, low=float(v.mean() - z * se),
                           high=float(v.mean() + z * se), n_groups=n)


# Provenance: plan 2.5 R34 (blocked jackknife, report only, LORO); SIGNATURES_LORO_ADDENDUM.md
# ("group_jackknife also runs on per-block values"); C10 (20% borderline share).
def blocked_jackknife(per_group_values: Mapping[str, float], block_of_group: Mapping[str, int]) -> JackknifeResult:
    """The report-only blocked jackknife: the same jackknife with the overlap blocks (R14) as the
    leave-out unit. Each block's value is the mean of its groups' values; blocks in index order.
    The ruled group jackknife still decides. READING FOR THE OWNER: with blocks of more than one
    group, the centre here is the mean of block means, not the verdict's mean over groups; the
    standard delete-a-block alternative keeps the group mean and drops a whole block per leave-out
    (see the module docstring).

    Refuses: no group; a group without a block; non-finite values."""
    if not isinstance(per_group_values, Mapping) or not per_group_values:
        _refuse("R34", "the blocked jackknife needs per-group values")
    absent = sorted(g for g in per_group_values if g not in block_of_group)
    if absent:
        _refuse("R34", "groups without an overlap block: %s" % absent[:_SHOW],
                fix="pass derive_overlap_blocks' block_of_group")
    members: Dict[int, List[float]] = {}
    for g in sorted(per_group_values):
        members.setdefault(int(block_of_group[g]), []).append(float(per_group_values[g]))
    per_block = [float(np.mean(members[b])) for b in sorted(members)]
    return group_jackknife(np.array(per_block))


def blocked_jackknife_flag(group_result: JackknifeResult, blocked_result: JackknifeResult) -> bool:
    """R34 / C10: True ('group jackknife may be too narrow') when the blocked SE is more than
    BORDERLINE_SHARE above the group SE. Report only; False when either SE is undefined."""
    g, b = float(group_result.se), float(blocked_result.se)
    if not (math.isfinite(g) and math.isfinite(b)):
        return False
    return b > (1.0 + float(K.BORDERLINE_SHARE)) * g


# ======================================================================================== verdict
def _band(band):
    """The band is checked first (F42): a finite number above 0."""
    return _finite_scalar(band, "the equivalence band", "R35", positive=True)


# Provenance: pm25_forecast.py:321-344 (the R5 rule, ruled for D74); HEADLINE_QUESTIONS_AND_FIXES.md F42
# (check the band first; HELPS needs the point estimate at or above it).
def contrast_tag(per_group_contrast: np.ndarray, band: float) -> Tuple[VerdictTag, JackknifeResult]:
    """The R5 reading rule (D74) for one contrast: its tag and its group jackknife.

    Order: the band is validated first; IDENTICAL when every contrast is within IDENTICAL_ATOL of 0;
    CANNOT TELL when the interval is undefined (fewer than 3 groups); EQUIVALENT when the whole
    interval lies inside [-band, band] (the band before HELPS and HURTS, F42); HELPS when the low end
    is above 0 AND the point estimate is at or above +band; HURTS when the high end is below 0 AND
    the point estimate is at or below -band; otherwise CANNOT TELL. The one tag rule of the engine:
    single_verdict and every printed contrast use it.
    Refuses: a band that is not a finite number above 0; no contrast; non-finite contrasts."""
    b = _band(band)
    dv = _vector(per_group_contrast, "the per-group contrasts", "R34")
    jk = group_jackknife(dv)
    if np.all(np.abs(dv) <= IDENTICAL_ATOL):
        return VerdictTag.IDENTICAL, jk
    if not (math.isfinite(jk.low) and math.isfinite(jk.high)):
        return VerdictTag.CANNOT_TELL, jk
    if -b <= jk.low and jk.high <= b:
        return VerdictTag.EQUIVALENT, jk
    if jk.low > 0 and jk.mean >= b:
        return VerdictTag.HELPS, jk
    if jk.high < 0 and jk.mean <= -b:
        return VerdictTag.HURTS, jk
    return VerdictTag.CANNOT_TELL, jk


def _paired_contrast(per_group_mae_reference, per_group_mae_arm, what):
    for m, name in ((per_group_mae_reference, "reference"), (per_group_mae_arm, "arm")):
        if not isinstance(m, Mapping) or not m:
            _refuse("R34", "%s: the %s MAE map is empty or not a mapping" % (what, name))
    ref_groups, arm_groups = set(per_group_mae_reference), set(per_group_mae_arm)
    if ref_groups != arm_groups:
        _refuse("G-DECIDE", "%s: the two MAE maps hold different groups (only in the reference: %s; "
                "only in the arm: %s)" % (what, sorted(ref_groups - arm_groups)[:_SHOW],
                                          sorted(arm_groups - ref_groups)[:_SHOW]))
    groups = sorted(ref_groups)
    dv = np.array([float(per_group_mae_reference[g]) - float(per_group_mae_arm[g]) for g in groups])
    if not np.isfinite(dv).all():
        _refuse("R34", "%s: %d groups have a non-finite MAE" % (what, int((~np.isfinite(dv)).sum())))
    return groups, dv


# Provenance: plan 2.5 R34, R35, 5 G-DECIDE; Q17 a, Q15 a; D74 (owner ruling); F57 (the nowcast band at
# every lead); F59 (pooled sign printed, flips flagged).
def single_verdict(per_group_mae_reference: Mapping[str, float], per_group_mae_adopted: Mapping[str, float],
                   pooled_mae_reference: float, pooled_mae_adopted: float, band: float, declined: bool,
                   reference: str) -> VerdictResult:
    """R34: the ONE verdict -- the adopted arm against its own link-matched trees-off (or the donor-row
    median without a normal), judged with the package's nowcast band at every lead.

    Rule: R34, R35, G-DECIDE, D74. Contrast per group = MAE(reference) - MAE(adopted) (positive =
    adopted better), in sorted group order; the tag is contrast_tag's (the band first). If the layer
    declined, the tag is DECLINED (the adopted prediction is the arithmetic normal); the contrast is
    still computed and printed. The pooled contrast, the groups where the adopted arm is better and
    the sign-flip groups are printed beside. The arithmetic normal and predict-zero are printed
    beside by the report, from the same table.
    Refuses: different group sets in the two maps; an empty map; non-finite MAEs; a band that is not
    a finite number above 0; declined that is not True or False; an unknown reference.
    """
    b = _band(band)
    if reference not in REFERENCES:
        _refuse("G-DECIDE", "the verdict reference must be one of %s, got %r" % (list(REFERENCES), reference))
    if not isinstance(declined, (bool, np.bool_)):
        _refuse("G-DECIDE", "declined must be True or False, got %r" % (declined,))
    ref_pooled = _finite_scalar(pooled_mae_reference, "the pooled reference MAE", "R34")
    adopted_pooled = _finite_scalar(pooled_mae_adopted, "the pooled adopted MAE", "R34")
    groups, dv = _paired_contrast(per_group_mae_reference, per_group_mae_adopted, "the single verdict")
    tag, jk = contrast_tag(dv, b)
    if bool(declined):
        tag = VerdictTag.DECLINED
    pooled = ref_pooled - adopted_pooled
    flips = sign_flip_groups(dict(zip(groups, dv.tolist())), pooled)
    return VerdictResult(tag=tag, reference=reference, contrast=jk, pooled_contrast=pooled,
                         groups_better=int((dv > 0).sum()), band=b, sign_flip_groups=flips)


# Provenance: plan 2.5 R35 (N3 rule, pm25_adaptation.py:127-132, 1121-1126: the median jackknife SE of the
# non-identical contrasts); Q22 b; D75.
def equivalence_band(contrast_ses: Sequence[float]) -> float:
    """R35: the band = the median jackknife SE of the arm contrasts in the package's first headline run.

    Rule: R35, D75. Median over the finite SEs given (the caller passes the non-identical contrasts:
    band_from_pairs does). Stored in registry/bands.csv by the run plumbing (keyed by the target +
    unit-list fingerprint and the engine version); used for HELPS/HURTS at every lead.
    Refuses: no finite SE (fewer than 3 groups).
    """
    try:
        ses = np.asarray(list(contrast_ses), dtype=np.float64)
    except (TypeError, ValueError):
        _refuse("R35", "the contrast SEs must be numbers, got %r" % (contrast_ses,))
    if ses.ndim != 1:
        _refuse("R35", "the contrast SEs must be a flat list")
    ok = ses[np.isfinite(ses)]
    if ok.size == 0:
        _refuse("R35", "no finite contrast SE: the band needs at least one contrast over 3 or more groups")
    return float(np.median(ok))


def band_from_pairs(per_group_mae: Mapping[str, Mapping[str, float]],
                    pairs: Sequence[Tuple[str, str]]) -> Tuple[float, Tuple[Dict[str, Any], ...]]:
    """R35 / D75: the band from named contrasts. Each pair is (reference column, arm column); D75's set
    is each tree arm vs its own trees-off and each arm vs its placebo. Per pair: the per-group
    contrast MAE(reference) - MAE(arm) and its group jackknife; IDENTICAL contrasts are left out of
    the median (the N3 rule). Returns (band, one record per pair).

    Refuses: no pair; a pair of one column with itself; a column absent from per_group_mae; pairs over
    different groups; and whatever equivalence_band refuses."""
    if not pairs:
        _refuse("R35", "the band needs at least one contrast pair (D75)")
    records: List[Dict[str, Any]] = []
    ses: List[float] = []
    for pair in pairs:
        try:
            ref, arm = pair
        except (TypeError, ValueError):
            _refuse("R35", "each pair is (reference column, arm column), got %r" % (pair,))
        if ref == arm:
            _refuse("R35", "the pair %r contrasts a column with itself" % (pair,))
        for c in (ref, arm):
            if c not in per_group_mae:
                _refuse("R35", "column %r has no per-group MAE" % (c,))
        _, dv = _paired_contrast(per_group_mae[ref], per_group_mae[arm], "the band pair %r" % (pair,))
        jk = group_jackknife(dv)
        identical = bool(np.all(np.abs(dv) <= IDENTICAL_ATOL))
        records.append({"reference": ref, "arm": arm, "mean": jk.mean, "se": jk.se, "low": jk.low,
                        "high": jk.high, "n_groups": jk.n_groups, "identical": identical})
        if not identical:
            ses.append(jk.se)
    return equivalence_band(ses), tuple(records)


# Provenance: plan 2.5 R36, U-4, C9; D76 (ddof 0); the 1e-4 regression tolerance stays in the harness.
def guard_tolerance(donor_rows: Any, link: Any, c: Optional[float], ub: Optional[float], k: float) -> float:
    """R36: the relative guard tolerance of one link, k x s, with s = the donor-row standard deviation
    of link(y) (ddof 0, D76).

    Rule: R36, U-4, G-DONOR. k is one engine constant (C9, not fixed yet), passed in. link(y) is the
    layer's R22 transform (layer.links.link_forward), with the lead's c and the legal upper bound.
    Refuses: s == 0 (a constant target, which G-SUPPORT refuses first); k that is not a finite number
    above 0; and whatever link_forward refuses (a link that is not R22's, y outside the link's
    domain, log_c without c > 0, arcsine without a finite upper bound).
    """
    kk = _finite_scalar(k, "k", "R36", positive=True)
    z = link_forward(_donor_y(donor_rows, "the donor rows", "R36"), link, c, ub)
    s = float(np.std(z))
    if not (math.isfinite(s) and s > 0):
        _refuse("R36", "the donor-row standard deviation of link(y) is %r; the target is constant" % s,
                fix="G-SUPPORT refuses a constant target first")
    return kk * s


# Provenance: plan 2.5 R34 ("sign flips flagged"); F59; D77.
def sign_flip_groups(per_group_contrast: Mapping[str, float], pooled_contrast: float) -> Tuple[str, ...]:
    """Groups whose contrast sign differs from the pooled sign (flagged, report only).

    Rule: R34, G-DECIDE, D77. A group contrast of exactly 0 is not a flip; a pooled contrast of
    exactly 0 has no sign, so no group flips against it. Returns the sorted group names.
    Refuses: non-finite values (the contrasts come from finite MAEs, D67)."""
    pooled = _finite_scalar(pooled_contrast, "the pooled contrast", "R34")
    if not isinstance(per_group_contrast, Mapping):
        _refuse("R34", "the per-group contrasts must map groups to values")
    for g, v in per_group_contrast.items():
        _finite_scalar(v, "the contrast of group %r" % (g,), "R34")
    sign = np.sign(pooled)
    if sign == 0:
        return ()
    return tuple(sorted(str(g) for g, v in per_group_contrast.items()
                        if float(v) != 0 and np.sign(float(v)) != sign))


# Provenance: plan 2.5 R34 ("A report-only trend flag (median per-unit donor slope)"); D78.
def median_unit_slope(unit_ids: np.ndarray, years: np.ndarray, y: np.ndarray) -> float:
    """D78's arithmetic: per unit, the ordinary least-squares slope of y on time in YEARS; the median
    over units with at least 2 distinct times (y units per year). Report only.

    Refuses: mismatched lengths; non-finite times or labels; no unit with 2 distinct times."""
    u = np.asarray(unit_ids)
    t = _vector(years, "the times in years", "R34")
    v = _vector(y, "the labels", "R34")
    if u.ndim != 1 or not (u.size == t.size == v.size):
        _refuse("R34", "unit ids, times and labels must be one per row")
    if not (np.isfinite(t).all() and np.isfinite(v).all()):
        _refuse("R34", "the trend flag needs finite times and labels")
    slopes = []
    for unit in pd.unique(u):
        m = u == unit
        x, yy = t[m], v[m]
        if np.unique(x).size < 2:
            continue
        xc = x - x.mean()
        slopes.append(float(np.sum(xc * (yy - yy.mean())) / np.sum(xc * xc)))
    if not slopes:
        _refuse("R34", "no unit has at least 2 distinct times")
    return float(np.median(slopes))


def trend_flag(donor_rows: Any) -> float:
    """Report-only trend flag: the median per-unit slope of y over time in donor rows (y units per
    year; D78).

    NOT CALLABLE YET (signature gap, owner decision): the approved DonorRows carries times as steps
    (grids) or days (events), and nothing in the signature says how many steps make a year, so a
    per-year slope cannot be computed from it. median_unit_slope holds the arithmetic on times in
    years; the owner rules how the years reach this function (proposed: the R2 steps per year as an
    input, or a years field on DonorRows)."""
    raise NotImplementedError(
        "trend_flag needs each donor row's time in years, but the approved DonorRows carries steps or "
        "days and the signature carries no steps per year: owner decision pending (proposed: the R2 "
        "steps per year as an input). median_unit_slope(unit_ids, years, y) holds the arithmetic")


# Provenance: plan 2.5 R34 ("The ladder is scored on rows common to all leads, with all rows beside").
def common_rows(row_keys_by_lead: Mapping[int, np.ndarray]) -> np.ndarray:
    """Row keys present at every lead of the ladder, sorted.

    Rule: R34. The ladder table is scored on these rows; all rows are scored beside.
    Refuses: no lead; keys that are not one-dimensional; a key named twice within a lead; an empty
    intersection."""
    if not isinstance(row_keys_by_lead, Mapping) or not row_keys_by_lead:
        _refuse("R34", "the ladder needs the row keys of at least one lead")
    common = None
    for lead in sorted(row_keys_by_lead):
        keys = np.asarray(row_keys_by_lead[lead])
        if keys.ndim != 1:
            _refuse("R34", "the row keys of lead %r must be one-dimensional" % (lead,))
        values = keys.tolist()
        if len(set(values)) != len(values):
            _refuse("R34", "lead %r names a row key twice" % (lead,))
        common = set(values) if common is None else common & set(values)
    if not common:
        _refuse("R34", "no row is scored at every lead")
    try:
        ordered = sorted(common)
    except TypeError:
        _refuse("R34", "the row keys cannot be ordered (mixed types)")
    return np.asarray(ordered)


# ======================================================================================== writers
# Provenance: plan 7.1 (test_preds.parquet, per_group.csv, verdict.json); F46 (save keys, lead/issue,
# normal, pre-clip for every row); owner rule: save EVERY row-level prediction.
def assemble_rows(keys: Mapping[str, np.ndarray], lead: int, issue: np.ndarray, y: np.ndarray,
                  normal: np.ndarray, arms: Mapping[str, np.ndarray], placebos: Mapping[str, np.ndarray],
                  pre_clip: Mapping[str, np.ndarray], baselines: Mapping[str, np.ndarray],
                  legal_range: Tuple[float, float]) -> pd.DataFrame:
    """The saved rows of one lead (plan 7.1 test_preds): keys, lead, issue, y, normal, legal range,
    every arm's and every placebo's clipped prediction and pre-clip value, every baseline.

    keys: at least unit, group, time and year (extra declared keys, e.g. a stratum bin, pass through).
    arms: the tree arms and trees-off, saved as 'arm__<name>'. placebos: the placebo correctors
    (R24, never selectable), saved as 'placebo__<name>'; may be empty (a lead without a placebo).
    Checks (fail loudly): one value per row everywhere; (unit, time) unique; y finite or NaN (NaN
    rows are saved, never scored); normal finite on every row or NaN on every row; no name both an
    arm and a placebo; every arm and placebo has a pre-clip array and nothing else does; each arm
    and placebo finite, inside the legal range and EQUAL to its pre-clip value clipped by the
    layer's R28 clip (G-CLIP); each pre-clip value finite; each baseline inside the legal range
    where it exists (NaN allowed and counted by score_table), never infinite.
    Refuses any breach, naming the column."""
    lo, hi = _legal(legal_range)
    if isinstance(lead, bool) or not isinstance(lead, Integral) or int(lead) < 0:
        _refuse("R34", "lead must be a whole number at or above 0, got %r" % (lead,))
    if not isinstance(keys, Mapping):
        _refuse("R34", "keys must map key names to arrays")
    absent = [c for c in KEY_COLUMNS if c not in keys]
    if absent:
        _refuse("R34", "the saved rows need the key columns %s" % absent)
    yy = _vector(y, "y", "R34")
    n = yy.size
    if np.isinf(yy).any():
        _refuse("R34", "y holds infinite values")
    frame: Dict[str, Any] = {}
    for name in keys:
        if not isinstance(name, str) or not name or name in RESERVED_COLUMNS[len(KEY_COLUMNS):] or \
                name.startswith((ARM_PREFIX, PRE_PREFIX, BASELINE_PREFIX)):
            _refuse("R34", "key name %r is empty or collides with a saved column" % (name,))
        col = np.asarray(keys[name])
        if col.ndim != 1 or col.size != n:
            _refuse("R34", "key %r has shape %s for %d rows" % (name, col.shape, n))
        if pd.isna(col).any():
            _refuse("R34", "key %r is missing on %d rows" % (name, int(pd.isna(col).sum())))
        frame[name] = col
    dup = pd.DataFrame({COL_UNIT: frame[COL_UNIT], COL_TIME: frame[COL_TIME]}).duplicated()
    if dup.any():
        _refuse("R34", "%d rows repeat a (unit, time) key" % int(dup.sum()))
    iss = as_int_array(issue, "the issue steps", rule="R34")
    if iss.size != n:
        _refuse("R34", "%d issue values for %d rows" % (iss.size, n))
    nn = _vector(normal, "the normal", "R34")
    if nn.size != n:
        _refuse("R34", "%d normal values for %d rows" % (nn.size, n))
    fin = np.isfinite(nn)
    if fin.any() and not fin.all():
        _refuse("R34", "the normal is finite on %d rows and not on %d; it exists everywhere or nowhere"
                % (int(fin.sum()), int((~fin).sum())))
    if not isinstance(arms, Mapping) or not arms:
        _refuse("R34", "the saved rows need at least one arm")
    if not isinstance(placebos, Mapping):
        _refuse("R34", "placebos must map names to arrays (an empty mapping when the lead has none)")
    both = sorted(set(arms) & set(placebos), key=str)
    if both:
        _refuse("R24", "%s are named both as an arm and as a placebo; a placebo is never an arm" % both)
    predicted = dict(arms)
    predicted.update(placebos)
    if not isinstance(pre_clip, Mapping) or set(pre_clip) != set(predicted):
        _refuse("G-CLIP", "every arm and placebo needs its pre-clip values and nothing else: arms %s, "
                "placebos %s, pre-clip %s" % (sorted(arms, key=str), sorted(placebos, key=str),
                                              sorted(pre_clip, key=str) if isinstance(pre_clip, Mapping)
                                              else pre_clip))
    if not isinstance(baselines, Mapping):
        _refuse("R34", "baselines must map names to arrays")
    frame.update({COL_LEAD: np.full(n, int(lead), dtype=np.int64), COL_ISSUE: iss, COL_Y: yy,
                  COL_NORMAL: nn, COL_LEGAL_MIN: np.full(n, lo), COL_LEGAL_MAX: np.full(n, hi)})
    for name in list(predicted) + list(baselines):
        if not isinstance(name, str) or not name:
            _refuse("R34", "arm, placebo and baseline names must be non-empty strings, got %r" % (name,))
    for name in sorted(predicted):
        kind, prefix = ("arm", ARM_PREFIX) if name in arms else ("placebo", PLACEBO_PREFIX)
        p = _vector(predicted[name], "%s %r" % (kind, name), "G-CLIP")
        pre = _vector(pre_clip[name], "the pre-clip values of %s %r" % (kind, name), "G-CLIP")
        if p.size != n or pre.size != n:
            _refuse("R34", "%s %r has %d values and %d pre-clip values for %d rows"
                    % (kind, name, p.size, pre.size, n))
        if not np.isfinite(pre).all():
            _refuse("G-CLIP", "%s %r: %d pre-clip values are not finite"
                    % (kind, name, int((~np.isfinite(pre)).sum())))
        clipped, _, _ = clip_to_legal(pre, (lo, hi), False)      # the layer's one R28 clip
        if not np.array_equal(p, clipped):
            bad = ~(p == clipped)
            _refuse("G-CLIP", "%s %r: %d predictions are not their pre-clip value clipped to the legal "
                    "range, e.g. at rows %s" % (kind, name, int(bad.sum()), _positions(bad)))
        frame[prefix + name] = p
        frame[PRE_PREFIX + name] = pre
    for name in sorted(baselines):
        b = _vector(baselines[name], "baseline %r" % name, "G-CLIP")
        if b.size != n:
            _refuse("R34", "baseline %r has %d values for %d rows" % (name, b.size, n))
        if np.isinf(b).any():
            _refuse("G-CLIP", "baseline %r holds infinite values" % name)
        fb = b[np.isfinite(b)]
        if (fb < lo).any() or (fb > hi).any():
            _refuse("G-CLIP", "baseline %r holds %d values outside the legal range; every baseline is "
                    "clipped (R28)" % (name, int(((fb < lo) | (fb > hi)).sum())))
        frame[BASELINE_PREFIX + name] = b
    return pd.DataFrame(frame)


def _one_value(sub, column, lead):
    values = pd.unique(sub[column].to_numpy(dtype=np.float64))
    if values.size != 1:
        _refuse("R34", "lead %d: the saved %s is not one value (%d values)" % (lead, column, values.size))
    return float(values[0])


def _check_row_frame(frame):
    """The frame must be what assemble_rows builds from its own columns: every assemble_rows check
    is re-run on it, lead by lead (a file may hold several leads; (unit, time) is unique within
    each), through assemble_rows itself, so the checks have one home."""
    if not isinstance(frame, pd.DataFrame):
        _refuse("R34", "the saved rows must be a DataFrame, got %s" % type(frame).__name__)
    if len(set(frame.columns)) != len(frame.columns):
        _refuse("R34", "the saved rows name a column twice")
    missing = [c for c in RESERVED_COLUMNS if c not in frame.columns]
    if missing:
        _refuse("R34", "the saved rows lack the columns %s (build them with assemble_rows)" % missing)
    if frame.empty:
        _refuse("R34", "the saved rows hold no row")
    names = {prefix: [c[len(prefix):] for c in frame.columns if isinstance(c, str) and c.startswith(prefix)]
             for prefix in PREDICTION_PREFIXES + (PRE_PREFIX, BASELINE_PREFIX)}
    if not names[ARM_PREFIX]:
        _refuse("R34", "the saved rows hold no arm")
    if sorted(names[ARM_PREFIX] + names[PLACEBO_PREFIX]) != sorted(names[PRE_PREFIX]):
        _refuse("G-CLIP", "every arm and placebo needs its pre-clip column and nothing else (arms %s, "
                "placebos %s, pre-clip %s)" % (sorted(names[ARM_PREFIX]), sorted(names[PLACEBO_PREFIX]),
                                               sorted(names[PRE_PREFIX])))
    key_names = [c for c in frame.columns if c not in RESERVED_COLUMNS[len(KEY_COLUMNS):]
                 and _prefix_of(c) is None and not (isinstance(c, str) and c.startswith(PRE_PREFIX))]
    leads = frame[COL_LEAD]
    if leads.isna().any():
        _refuse("R34", "the lead is missing on %d saved rows" % int(leads.isna().sum()))
    lead_values = as_int_array(pd.unique(leads.to_numpy()), "the saved leads", rule="R34")
    for lead in sorted(lead_values.tolist()):
        sub = frame[leads.to_numpy() == lead]
        assemble_rows(keys={c: sub[c].to_numpy() for c in key_names}, lead=int(lead),
                      issue=sub[COL_ISSUE].to_numpy(), y=sub[COL_Y].to_numpy(),
                      normal=sub[COL_NORMAL].to_numpy(),
                      arms={a: sub[ARM_PREFIX + a].to_numpy() for a in names[ARM_PREFIX]},
                      placebos={a: sub[PLACEBO_PREFIX + a].to_numpy() for a in names[PLACEBO_PREFIX]},
                      pre_clip={a: sub[PRE_PREFIX + a].to_numpy() for a in names[PRE_PREFIX]},
                      baselines={b: sub[BASELINE_PREFIX + b].to_numpy() for b in names[BASELINE_PREFIX]},
                      legal_range=(_one_value(sub, COL_LEGAL_MIN, lead), _one_value(sub, COL_LEGAL_MAX, lead)))


def _publish_once(tmp, path):
    """Publish a finished, fsynced temp file under a NEW name (never overwrites) with runs.atomic's
    own publish rule and sharing retries; the temp file is removed on any failure.
    OWNER / OTHER TASK: runs.atomic has a text write-once only; a public bytes write-once there would
    replace this function (it reuses atomic's private retry and cleanup helpers meanwhile)."""
    def _publish():
        if os.name == "nt":
            os.rename(tmp, path)  # on Windows rename fails if the target exists: atomic write-once
        else:
            os.link(tmp, path)  # fails if the target exists
            os.remove(tmp)

    try:
        atomic._retry_sharing(_publish, "publishing the write-once file", path)
    except FileExistsError as exc:
        atomic._remove_own_temp(tmp)
        raise atomic.AtomicWriteError("refusing to overwrite %s (appeared during the write)" % path) from exc
    except BaseException:
        atomic._remove_own_temp(tmp)
        raise


def write_rows_once(frame: pd.DataFrame, path: Any) -> str:
    """Save every row (parquet) under a NEW file, atomically (plan 7.1): a temp file in the same
    folder, written, flushed and fsynced, then a write-once publish, so after a crash the final name
    is either absent or complete. The run folder itself is resolved through the shipped-results
    registry by the run plumbing (G-NOOVERWRITE) before this is called.

    Refuses: a frame that assemble_rows would refuse to build from its own columns (every one of its
    checks re-run, lead by lead: reserved columns, keys, (unit, time) unique within a lead, y, the
    normal, the legal range one value per lead, each arm and placebo finite and equal to its pre-clip
    value clipped, baselines inside the legal range); an existing path."""
    _check_row_frame(frame)
    path = os.fspath(path)
    if os.path.lexists(path):
        raise atomic.AtomicWriteError("refusing to overwrite %s (written once)" % path)
    tmp = atomic.temp_name(path)
    try:
        with open(tmp, "xb") as fh:           # 'x' never clobbers a file, even though the name is new
            frame.to_parquet(fh, index=False)
            fh.flush()
            os.fsync(fh.fileno())
    except BaseException:
        atomic._remove_own_temp(tmp)
        raise
    _publish_once(tmp, path)
    return path


def read_rows(path: Any) -> pd.DataFrame:
    """Read saved rows back (the only input of score_table)."""
    return pd.read_parquet(os.fspath(path))


def write_table_once(table: pd.DataFrame, path: Any) -> str:
    """Save a score table (CSV, every line) under a NEW file, atomically (runs.atomic)."""
    if not isinstance(table, pd.DataFrame):
        _refuse("R34", "a score table is a DataFrame, got %s" % type(table).__name__)
    path = os.fspath(path)
    atomic.write_text_once(path, table.to_csv(index=False))
    return path


def _json_safe(obj):
    """Plain JSON values with every non-finite float as None (strict JSON refuses NaN)."""
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (JackknifeResult, DetectionScore, VerdictResult)):
        return {f: _json_safe(getattr(obj, f)) for f in obj.__dataclass_fields__}
    if isinstance(obj, Mapping):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (Integral, np.integer)):
        return int(obj)
    if isinstance(obj, (Real, np.floating)):
        v = float(obj)
        return v if math.isfinite(v) else None
    return obj


def verdict_record(result: VerdictResult) -> Dict[str, Any]:
    """The verdict as plain JSON values (NaN printed as null)."""
    if not isinstance(result, VerdictResult):
        _refuse("G-DECIDE", "verdict_record reads a VerdictResult, got %s" % type(result).__name__)
    return _json_safe(result)


def write_json_once(record: Mapping[str, Any], path: Any) -> str:
    """Save a verdict or band record (JSON, NaN as null) under a NEW file, atomically (runs.atomic)."""
    if not isinstance(record, Mapping):
        _refuse("R34", "a record is a mapping, got %s" % type(record).__name__)
    path = os.fspath(path)
    atomic.write_json_once(path, _json_safe(record))
    return path
