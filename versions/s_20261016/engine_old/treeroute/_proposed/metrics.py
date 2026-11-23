"""PROPOSED signatures: treeroute/report/metrics.py (plan 4.2, R31-R36). SCIENCE: owner signatures (the
rules are already ruled), agent bodies.

Baselines (R31), hit tolerance (R32), one strict top-10% detection function (R33), scoring tables and
the single verdict (R34), the equivalence band (R35) and relative guard tolerances (R36). Every score
in any report, including treeroute_report's paper tables, comes from these functions on saved rows;
no formula is re-implemented elsewhere. No multiplicity correction (Q21 a). The jackknife uses 1.96
(Q19 a). Uncertainty is over GROUPS, never seeds.
"""
# Provenance for the module: pm25_adaptation.py:263-307 (score), 894-930 (guard), 1085-1130
# (contrasts, verdict tags, N3 band); pm25_forecast.py:321-344, 495-533 (persistence baselines);
# forecast_report.py:57-77 (detection); adaptation.py:525-537 (mae, jack).
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .common import Link, RouterKind, RunKind, VerdictTag
from .fit_context import DonorRows, UnitHistory


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


# ------------------------------------------------------------------------------------------------ R31
# Provenance: plan 2.5 R31 ("predict-zero ... All clipped (R28)").
def baseline_predict_zero(n_rows: int, legal_range: Tuple[float, float]) -> np.ndarray:
    """predict-zero, clipped to the legal range.

    Rule: R31, R28.  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.5 R31): zero for every row, then the R28 clip (a legal minimum above 0 lifts it).
    Inputs:
        n_rows: rows to fill.
        legal_range: the target's range.
    Returns:
        predictions.
    Refuses:
        - n_rows < 0.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.5 R31 (guess-normal where a normal exists); plan 2.2 R16 (decline target = the
# arithmetic normal).
def baseline_guess_normal(arithmetic_normal: np.ndarray, legal_range: Tuple[float, float]) -> np.ndarray:
    """guess-normal: the per-unit arithmetic normal (the R16 decline target), clipped.

    Rule: R31, R16, R28.  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.5 R31): only where a normal exists (not neighbour).
    Inputs:
        arithmetic_normal: identity-link normal per scored row (route_kinds.unit_season_normal).
        legal_range: the target's range.
    Returns:
        predictions.
    Refuses:
        - NaN in the normal.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.5 R31, Q26 (the last-5-years normal beside).
def baseline_last5_normal(history: UnitHistory, kind: RouterKind, season_keys: np.ndarray, cut_year: int,
                          legal_range: Tuple[float, float]) -> np.ndarray:
    """The last-5-years normal, printed beside guess-normal (Q26).

    Rule: R31.  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.5 R31, Q26):
        Per unit and season key, the mean of y over the unit's own rows in the last 5 years at or
        before the cut; clipped. Report only. Only where a normal exists.
    Inputs:
        history: UnitHistory at the cut (G-DONOR).
        kind: the R12 router kind of the run.
        season_keys: season key per scored row of this unit.
        cut_year: the year of the cut.
        legal_range: the target's range.
    Returns:
        predictions per scored row.
    Refuses:
        - kind NEIGHBOUR (no normal exists).
    OWNER DECISION: "last 5 years" -- propose the 5 calendar years ending with the cut's year; a
        unit-season with no row there takes the R15 fallback chain.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.5 R31; pm25_forecast.py:492 (persist = y at the issue step).
def baseline_persistence(y_issue: np.ndarray, legal_range: Tuple[float, float]) -> np.ndarray:
    """Persistence: the unit's label at the issue step (events: the last valid label before the issue
    date), clipped.

    Rule: R31, R28.  Needed: Fri 9 Oct (forecast ladder).

    Contract (plan 2.5 R31):
        Only where units have repeat history. The label comes from vault.LabelView.asof_rows. The
        clip is layer.clip_to_legal with allow_nan=True: a row whose issue step has no valid label
        stays NaN and is counted, and score_table scores persistence only on rows where it exists
        (count printed; see mae's decision).
    Inputs:
        y_issue: label at the issue step per row (NaN where absent).
        legal_range: the target's range.
    Returns:
        predictions (NaN where no issue label exists; such rows are counted).
    Refuses:
        - nothing.
    OWNER DECISION: the source also computes anomaly persistence (normal(t) + y_issue - normal(issue),
        and its log form); the plan names only persistence and damped persistence -- keep them as
        extra printed baselines, or drop.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: pm25_forecast.py:494-527 (phi per cell = regression through the origin of a(t) on a(t-L),
# both labels <= cut; leave-one-out means; BOTH pair members left out of their shared mean when lead is a
# multiple of 12; phi clipped to [0, 1], undefined -> 0); U-2 (the season-key rule replaces lead % 12).
def damped_persistence_phi(histories: Mapping[str, UnitHistory], lead_steps: int,
                           same_season_key: bool) -> Mapping[str, float]:
    """Damped-persistence phi per unit, from (label, predecessor) pairs at or before the cut.

    Rule: R31, U-2.  Needed: Fri 9 Oct (forecast ladder).

    Contract (plan 2.5 R31, U-2):
        For each unit: pairs (y(t), y(t-L)) with both labels at or before the cut. Anomalies are
        taken from the unit x season-key mean with the pair's own labels left out: when target and
        predecessor SHARE the season key (U-2; annual data: every lead), BOTH pair members are left
        out of their shared mean; otherwise each label leaves itself out of its own mean. phi = the
        regression through the origin of a(t) on a(t-L), clipped to [0, 1]; undefined phi is 0.
        Events with repeat visits: pairs (visit, previous visit), the same season-key rule per pair.
    Inputs:
        histories: {unit: UnitHistory at the lead's cut}.
        lead_steps: L.
        same_season_key: whether target and predecessor share the season key at this lead (R2).
    Returns:
        {unit: phi}.
    Refuses:
        - lead_steps < 1.
    OWNER DECISION: minimum counts. Shared season key: more than 2 labels in the shared mean, else
        NaN and the pair is dropped (the source). Separate season keys: propose at least 2 labels in
        each unit-season, else NaN and the pair is dropped. The source's max(C - 1, 1) gives a
        leave-one-out mean of 0 for a single-label unit-season, so its 'anomaly' is the raw label;
        porting that as-is would carry the quirk over silently.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: pm25_forecast.py:524 (damped = clim(t) + phi x (y_issue - clim(issue))).
def baseline_damped_persistence(normal_target: np.ndarray, normal_issue: np.ndarray, y_issue: np.ndarray,
                                phi: np.ndarray, legal_range: Tuple[float, float]) -> np.ndarray:
    """Damped persistence: normal(t) + phi x (y_issue - normal(issue)), clipped.

    Rule: R31, R28.  Needed: Fri 9 Oct (forecast ladder).

    Contract (plan 2.5 R31): uses the arithmetic normal of each step's season key.
    Inputs:
        normal_target, normal_issue: arithmetic normals of the target and issue steps.
        y_issue: label at the issue step.
        phi: damped_persistence_phi per row's unit.
        legal_range: the target's range.
    Returns:
        predictions.
    Refuses:
        - shape mismatches.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.5 R31 ("Neighbour: donor-row median (Q15 a)"); replaces the training mean at
# adaptation.py:1633.
def baseline_donor_median(donor_rows: DonorRows) -> float:
    """The donor-row median of y: the neighbour kind's reference and pool fallback.

    Rule: R31, R34, G-DONOR.  Needed: M8 (neighbour track).

    Contract (plan 2.5 R31, R34; Q15 a): median over DonorRows only.
    Inputs:
        donor_rows: DonorRows at the cut.
    Returns:
        the median.
    Refuses:
        - no finite value.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# ------------------------------------------------------------------------------------------------ scores
# Provenance: adaptation.py:525-527 (mae: plain mean of |y - p|, so one NaN makes the MAE NaN).
def mae(y: np.ndarray, p: np.ndarray) -> float:
    """Mean absolute error in y units.

    Rule: R34.  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.5 R34):
        mean(|y - p|) over the rows given. Which rows are given, and what a non-finite pair does,
        is the decision below; no row is ever dropped silently.
    Inputs:
        y, p: labels and predictions.
    Returns:
        MAE.
    Refuses:
        - shape mismatch, no rows, or a non-finite pair (under option a).
    OWNER DECISION: non-finite pairs. Option (a), proposed: mae refuses any non-finite pair (fail
        loudly); the caller (score_table) selects the rows each column is scored on and prints
        that count -- a baseline that is NaN on some rows (persistence without an issue label) is
        scored on the rows where it exists, beside the arms on the same rows. Option (b): mae
        drops non-finite pairs itself and returns (value, rows used). The same policy applies to
        anomaly_r2, corr2, calibration_ratio and hit_rate. The source propagated NaN.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: pm25_adaptation.py:263-292 (anomaly-R2: 1 - sum((ay - ap)^2) / sum(ay^2), anomalies
# against the cell's own month normal from calibration years only; NaN when the denominator is 0).
def anomaly_r2(y: np.ndarray, p: np.ndarray, normal: np.ndarray) -> float:
    """Anomaly R2 against the per-unit normal: 1 - SSE(p) / SSE(normal).

    Rule: R34.  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.5 R34):
        Where a normal exists (N/A for neighbour). Guess-normal scores 0 by construction.
    Inputs:
        y, p: labels and predictions.
        normal: the per-unit normal per row, fitted at or before the cut.
    Returns:
        anomaly R2 (NaN when SSE(normal) is 0).
    Refuses:
        - shape mismatch; a non-finite pair (the policy of mae's decision).
    OWNER DECISION: which normal -- propose the ARITHMETIC (identity-link) normal for every arm.
    OWNER DECISION: the source returns nothing under 10 rows; propose NaN under 10 finite rows.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.5 R34 (corr2 beside MAE, Q37).
def corr2(y: np.ndarray, p: np.ndarray) -> float:
    """Squared Pearson correlation between labels and predictions.

    Rule: R34, R27 (printed beside).  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.4 R27, 2.5 R34): printed beside MAE; never used to select.
    Inputs:
        y, p: labels and predictions.
    Returns:
        corr2 (NaN if either side is constant).
    Refuses:
        - shape mismatch; a non-finite pair (the policy of mae's decision).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: HEADLINE_RUN_PLAN.md:31 and UNIFORM_SCHEMA_PLAN.md:61, 209 (calibration ratio = mean
# prediction / mean truth; flagged outside 0.5-2.0); Q51 a (flag only).
def calibration_ratio(y: np.ndarray, p: np.ndarray) -> float:
    """Calibration ratio: mean prediction / mean truth.

    Rule: R28, R34, G-RANGE.  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.4 R28, 2.5 R34): logged per arm; report only.
    Inputs:
        y, p: labels and predictions.
    Returns:
        the ratio (NaN when mean truth is 0).
    Refuses:
        - shape mismatch; a non-finite pair (the policy of mae's decision).
    OWNER DECISION: the plan names the ratio but not its formula; propose mean(p) / mean(y) from the
        earlier plans, and confirm whether the 0.5-2.0 flag band (Q51: flag only) is kept.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.4 R28 (pre-clip rate logged per arm).
def preclip_rate(pre_clip: np.ndarray, legal_range: Tuple[float, float]) -> float:
    """Share of predictions outside the legal range before the clip.

    Rule: R28, R34.  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.4 R28): from the saved pre-clip values.
    Inputs:
        pre_clip: y-unit predictions before the clip.
        legal_range: the target's range.
    Returns:
        the share.
    Refuses:
        - NaN in pre_clip.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.5 R32 (D9 with the mean instead of the median, which is exactly 0 on one package;
# owner signs, 9.1 item 2c); pm25_adaptation.py:144 (the old absolute tolerance, now a package floor).
def hit_tolerance(donor_rows: DonorRows, donor_reference: np.ndarray) -> float:
    """R32: half the donor rows' MEAN absolute deviation from their own normal (neighbour: from the
    donor-row median).

    Rule: R32, G-DONOR.  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.5 R32):
        tol = 0.5 x mean(|y - reference|) over donor rows at the cut. A declared
        measurement_error_floor is printed beside (a second hit rate), never used to select.
    Inputs:
        donor_rows: DonorRows at the nowcast cut.
        donor_reference: each donor row's own unit x season normal (identity link), or the
            donor-row median for the neighbour kind.
    Returns:
        the tolerance.
    Refuses:
        - a tolerance of 0 (constant donor rows; G-SUPPORT refuses first).
    OWNER DECISION: sign the MEAN form (9.1 item 2c).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: pm25_adaptation.py:284-287, 305 (hit = mean(|y - p| <= tol), inclusive).
def hit_rate(y: np.ndarray, p: np.ndarray, tol: float) -> float:
    """Share of rows within +/- tol of the truth (inclusive).

    Rule: R32, R34.  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.5 R32, R34): printed with guess-normal's hit rate beside it.
    Inputs:
        y, p: labels and predictions.
        tol: hit_tolerance (or the declared floor, for the printed second rate).
    Returns:
        the share.
    Refuses:
        - tol <= 0; a non-finite pair (the policy of mae's decision).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.5 R33, U-3; forecast_report.py:57-77 (t = quantile(y, 0.9); events y > t; NaN if
# fewer than 10 events or more than 50% events; score = mean(p[events] > quantile(p, 0.9))); per-group
# q90 as final_table.py:77-79, now strict.
def top10_detection(y: np.ndarray, p: np.ndarray) -> DetectionScore:
    """R33: the one strict top-10% detection score.

    Rule: R33, U-3.  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.5 R33):
        Event = y strictly above the rows' own 90th percentile. Score = the share of events whose
        prediction is strictly above the predictions' own 90th percentile. NaN when there are fewer
        than 10 events or more than 50% of rows are events; the event share is always returned. The
        headline is pooled (pooled q90); for the jackknife each group uses its OWN q90, over groups
        with a defined score (count printed). A yes/no target whose q90 equals its maximum gets NaN.
    Inputs:
        y, p: labels and predictions (one group, or pooled).
    Returns:
        DetectionScore.
    Refuses:
        - shape mismatch.
    OWNER DECISION: quantile method -- propose numpy's default linear interpolation, as the source.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.5 R34 ("quartile edges from donor rows"); Q50 (forest-pixel quartiles).
def stratum_edges(donor_rows: DonorRows, stratum_values: np.ndarray) -> Tuple[float, float, float]:
    """Quartile edges of a declared report_stratum column, from donor rows.

    Rule: R34, G-DONOR.  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.5 R34): edges from DonorRows only; test rows are binned with them.
    Inputs:
        donor_rows: DonorRows at the nowcast cut.
        stratum_values: the stratum column on those rows.
    Returns:
        (q25, q50, q75).
    Refuses:
        - fewer than 4 distinct values.
    OWNER DECISION: bin edges inclusive on the right or left -- propose right-closed bins.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.5 R34 (per year, per group, per stratum; pooled headline with macro beside, Q20 a;
# declared support weights printed beside, never used to select).
def score_table(preds: pd.DataFrame, by: Tuple[str, ...], tol: float, floor: Optional[float],
                run_kind: RunKind) -> pd.DataFrame:
    """Scoring table over saved rows, one line per arm x (by-key), with pooled and macro lines.

    Rule: R34.  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.5 R34, 7.1):
        Per arm and key: MAE, anomaly R2 (where a normal exists), corr2, hit rate (and at the
        declared floor), calibration ratio, pre-clip rate, detection, and the row count each
        column was scored on. Pooled line and macro (mean over groups) line beside it. Built only
        from saved rows (test_preds.parquet). It serves EVERY run folder (smoke included: plan 7.1
        writes per_group.csv and verdict.json there too) and stamps the run kind on every line; it
        never refuses a kind. The refusal of smoke and legacy rows belongs to the headline-table
        builder (boilerplate, G-LEGACY), which reads the stamp.
    Inputs:
        preds: saved row-level predictions (keys, lead, issue date, y, arms, normal, pre-clip).
        by: grouping keys, e.g. ('year',), ('group',), ('stratum',).
        tol: R32 tolerance.
        floor: declared measurement_error_floor, or None.
        run_kind: HEADLINE, SMOKE or LEGACY (from the run folder's manifest).
    Returns:
        the table, with a run_kind column.
    Refuses:
        - preds without the key, y or normal columns the lines need.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: adaptation.py:530-537 (jack: mean of per-group values; leave-one-out means; se =
# sqrt((n-1)/n x sum((jk - mean(jk))^2)); CI mean +/- 1.96 se; n < 3 -> NaN); Q19 a.
def group_jackknife(per_group_values: np.ndarray) -> JackknifeResult:
    """Leave-one-group-out jackknife at 1.96 over per-group values.

    Rule: R34, Q19 a.  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.5 R34; source: provenance comment):
        mean = the mean of the per-group values; leave-one-out means; SE = sqrt((n-1)/n x sum of
        squared deviations of the leave-one-out means from their mean); interval mean +/- 1.96 SE.
        Fewer than 3 groups: SE and interval NaN. No multiplicity correction.
    Inputs:
        per_group_values: one value per group (e.g. MAE(reference) - MAE(adopted)).
    Returns:
        JackknifeResult.
    Refuses:
        - non-finite values.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.5 R34, 5 G-DECIDE; Q17 a, Q15 a; pm25_adaptation.py:1096-1115 (tags: IDENTICAL if all
# contrasts are 0 at 1e-12; CANNOT TELL if the interval is undefined; HELPS if low > 0; HURTS if high < 0;
# DOES NOT HELP (equivalent) if -band <= low and high <= band; else CANNOT TELL); F57 (the nowcast band at
# every lead).
def single_verdict(per_group_mae_reference: Mapping[str, float], per_group_mae_adopted: Mapping[str, float],
                   pooled_mae_reference: float, pooled_mae_adopted: float, band: float, declined: bool,
                   reference: str) -> VerdictResult:
    """R34: the ONE verdict -- the adopted arm against its own link-matched trees-off (or the donor-row
    median without a normal), judged with the package's nowcast band.

    Rule: R34, R35, G-DECIDE.  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.5 R34, R35, 5 G-DECIDE):
        Contrast per group = MAE(reference) - MAE(adopted) (positive = adopted better); jackknife at
        1.96 over groups. Reference = the R16 guard reference of the adopted arm (geometric normal
        for a log arm, arithmetic for identity); neighbour: the donor-row median, with neighbour
        trees-off printed beside. The arithmetic normal and predict-zero are printed beside. If the
        layer declined, the verdict reads 'declined'. Per-group and pooled signs are printed; a flip
        is flagged. BINDING (plan R35, G-DECIDE): the package's nowcast band decides HELPS and
        HURTS, at every lead. Tags: IDENTICAL when every contrast is 0 (within 1e-12); CANNOT TELL
        when the interval is undefined; EQUIVALENT when the whole interval lies inside [-band,
        band]; HELPS and HURTS as the decision below; otherwise CANNOT TELL.
    Inputs:
        per_group_mae_reference, per_group_mae_adopted: MAE per test group.
        pooled_mae_reference, pooled_mae_adopted: pooled MAEs.
        band: R35 band of this package.
        declined: True when the layer declined.
        reference: 'own_link_trees_off' or 'donor_row_median'.
    Returns:
        VerdictResult.
    Refuses:
        - different group sets in the two maps.
    OWNER DECISION: how the band decides HELPS and HURTS -- no default is proposed. Option (a), the
        shipped verdict rule: HELPS when the interval's low end is above 0, HURTS when its high end
        is below 0 (the band enters only through EQUIVALENT). Option (b), the plan's wording read
        literally: HELPS when the low end is above +band, HURTS when the high end is below -band.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.5 R35 (N3 rule, pm25_adaptation.py:127-132, 1121-1126: the median jackknife SE of
# the non-identical arm contrasts); Q22 b; registry/bands.csv (plan 7.1).
def equivalence_band(contrast_ses: Sequence[float]) -> float:
    """R35: the band = the median jackknife SE of the arm contrasts in the package's first headline run.

    Rule: R35.  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.5 R35):
        Median over the finite SEs of the non-identical contrasts. Stored in registry/bands.csv
        keyed by the target + split fingerprint and the engine version (storage is boilerplate); a
        re-derivation is explained, never silent. Used for HELPS/HURTS at every lead.
    Inputs:
        contrast_ses: jackknife SEs of the run's arm contrasts.
    Returns:
        the band.
    Refuses:
        - no finite SE (fewer than 3 groups).
    OWNER DECISION: which contrasts feed the median -- the source used penalty sweep, tool worth, each
        arm vs its placebo and log-vs-log1p; the engine has no inherited penalty or log1p, so the set
        must be named (propose: each tree arm vs its own trees-off, and each arm vs its placebo).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.5 R36, U-4, C9 (k fixed once so the first shipped package's identity gate stays at
# 1e-6; checked to be at least 10x the measured 9e-8 arithmetic error); the 1e-4 regression tolerance
# stays in the harness.
def guard_tolerance(donor_rows: DonorRows, link: Link, c: Optional[float], ub: Optional[float], k: float) -> float:
    """R36: the relative guard tolerance of one link, k x s, with s = the donor-row standard deviation
    of link(y).

    Rule: R36, U-4, G-DONOR.  Needed: Sun 4 Oct (scoring; used by G-PLUMB from Fri 2 Oct).

    Contract (plan 2.5 R36):
        s is never 0 unless the target is constant, which G-SUPPORT refuses. k is one engine
        constant (C9).
    Inputs:
        donor_rows: DonorRows at the cut.
        link, c, ub: the link and its constants.
        k: the engine constant.
    Returns:
        k x s.
    Refuses:
        - s == 0.
    OWNER DECISION: the value of k (computed once off-engine from the first shipped package's donor
        s, stored in engine_constants.py with its origin comment) and the standard-deviation
        convention (propose ddof = 0).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.5 R34 ("sign flips flagged"); F59 (hidden sign flips).
def sign_flip_groups(per_group_contrast: Mapping[str, float], pooled_contrast: float) -> Tuple[str, ...]:
    """Groups whose contrast sign differs from the pooled sign (flagged, report only).

    Rule: R34, G-DECIDE.  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.5 R34, 5 G-DECIDE): printed with the verdict.
    Inputs:
        per_group_contrast: MAE(reference) - MAE(adopted) per group.
        pooled_contrast: the pooled contrast.
    Returns:
        sorted group names with a flipped sign.
    Refuses:
        - nothing.
    OWNER DECISION: a contrast of exactly 0 -- propose it is not a flip.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.5 R34 ("A report-only trend flag (median per-unit donor slope)").
def trend_flag(donor_rows: DonorRows) -> float:
    """Report-only trend flag: the median per-unit slope of y over time in donor rows.

    Rule: R34.  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.5 R34): never used to select or to decide.
    Inputs:
        donor_rows: DonorRows at the nowcast cut.
    Returns:
        the median slope (y units per year).
    Refuses:
        - no unit with at least 2 distinct times.
    OWNER DECISION: the slope -- propose an ordinary least-squares slope of y on time (in years) per
        donor unit.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.5 R34 ("The ladder is scored on rows common to all leads, with all rows beside").
def common_rows(row_keys_by_lead: Mapping[int, np.ndarray]) -> np.ndarray:
    """Row keys present at every lead of the ladder.

    Rule: R34.  Needed: Fri 9 Oct (forecast ladder).

    Contract (plan 2.5 R34): the ladder table is scored on these rows; all rows are scored beside.
    Inputs:
        row_keys_by_lead: {lead: row keys scored at that lead}.
    Returns:
        the common keys, sorted.
    Refuses:
        - an empty intersection.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")
