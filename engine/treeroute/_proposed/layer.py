"""PROPOSED signatures: treeroute/layer/ (links, arms, decide, ladder; plan 4.2, R22-R29). SCIENCE:
owner signatures; gated by the harness.

The one Type-2 layer: links from R22 with the clip (R28); arms, trees-off and placebo (R24); the grid
search on the decision surface (R26); the N2 guard, MAE adoption and the decline rule (R27); the
forecast ladder's pinned adoption with its lead-12 placebo (R29). decide() sees only decision-surface
data. The nowcast adoption is hashed before its test labels open (vault.lock_adoption), and each
lead's adoption before that lead's test rows are scored (vault.lock_lead_adoption). The outcome shapes
(PenaltyPick, Adoption, LeadAdoption) live in common.py, so the vault can name them.
"""
# Provenance for the module: extracted from pm25_adaptation._run(): add_clim 584-604, run_arm 695-768,
# rank 795-818, guard 894-930; pm25_forecast.py:495-533, 566-574, 601-606, 636-645, 743-773.
from __future__ import annotations

from typing import Mapping, Optional, Tuple

import numpy as np

from .common import (Adoption, ArmSpec, GridPoint, GuardResult, LeadAdoption, Link, PenaltyPick,
                     Weighting)
from .fit_context import DonorRows


# Provenance: plan 2.4 R22; pm25_adaptation.py:153-154 (logc: log(y + c), back exp(p) - c);
# adaptation.py:1436 (arcsine inverse UB x sin(clip(p, 0, pi/2))^2).
def link_forward(y: np.ndarray, link: Link, c: Optional[float], ub: Optional[float]) -> np.ndarray:
    """Transform y into a link's space.

    Rule: R22.  Needed: Sat 3 Oct (layer).

    Contract (plan 2.4 R22):
        identity: y. log_c: log(y + c) with c from R23 for the cut in use. arcsine: only with a
        finite legal upper bound UB from the target fact.
    Inputs:
        y: values in y units.
        link: the link.
        c: R23 constant (log_c only).
        ub: the legal upper bound (arcsine only).
    Returns:
        values in link space.
    Refuses:
        - log_c without c > 0; arcsine without a finite ub; y outside the link's domain.
    OWNER DECISION: the arcsine formula is not written in the plan; propose
        forward = arcsin(sqrt(y / UB)), matching the source's inverse.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: as link_forward; pm25_adaptation.py:734, 765, 768 (unclipped exp(p) - c, the defect G-CLIP
# closes).
def link_inverse(z: np.ndarray, link: Link, c: Optional[float], ub: Optional[float]) -> np.ndarray:
    """Back-transform link-space predictions to y units (clipping happens in clip_to_legal).

    Rule: R22, R28.  Needed: Sat 3 Oct (layer).

    Contract (plan 2.4 R22, R28):
        identity: z. log_c: exp(z) - c. arcsine: UB x sin(clip(z, 0, pi/2))^2. Every result then
        goes through clip_to_legal; the pre-clip value is kept for the pre-clip rate.
    Inputs:
        z: link-space predictions.
        link, c, ub: as link_forward.
    Returns:
        y-unit predictions before the legal clip.
    Refuses:
        - as link_forward.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.4 R23 (F8: one c per cut); pm25_adaptation.py:572-577 (C_LOG = np.percentile(ypos, 1),
# ypos = finite positive donor y; "one constant for the whole run -- identical on the inner and the test
# pass"); plan 2.4 R25 (one weight model per cut serves that cut's decision and test pass).
def c_for_cut(donor_rows: DonorRows) -> float:
    """R23: c = the 1st percentile of positive donor-row y at or before the cut.

    Rule: R23, G-DONOR.  Needed: Sat 3 Oct (layer).

    Contract (plan 2.4 R23, 5 G-DONOR):
        One c per cut (F8). DonorRows only (the picked donor units, as R22 reads them). Written to
        derived.json with the lead, cut kind and fold it belongs to. Which cuts get their own c is
        the decision below; whichever it is, one c serves both the decision surface and the test
        pass it is paired with, so an arm is never selected under one transform and scored under
        another.
    Inputs:
        donor_rows: DonorRows of the cut.
    Returns:
        c (> 0).
    Refuses:
        - no positive finite donor value (then log_c is not in the link set, R22).
    OWNER DECISION: percentile method -- propose numpy's default linear interpolation, as the source.
    OWNER DECISION: which cuts get their own c. Option (a), proposed: one c per LEAD cut, from donor
        rows at that lead's FIT cut (plus one per fold on the donor-fold surface), serving that
        lead's decision or guard surface AND its test pass -- the source's one-c-per-run rule, and
        the same pairing R25 uses for the weight model. Option (b): a separate c at each guard cut,
        so the guard surface and the test pass of one lead use different transforms.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.4 R24; C13; ARM table at pm25_adaptation.py:705-708, INNER_ARMS at :824-825.
def candidate_arms(links: Tuple[Link, ...]) -> Tuple[ArmSpec, ...]:
    """R24: the nowcast candidate list.

    Rule: R24.  Needed: Sat 3 Oct (layer).

    Contract (plan 2.4 R24):
        Per link: plain and corrector, each unweighted and GLS-weighted (selectable); trees-off,
        unweighted (it keeps the identity; not selectable, it is the guard reference); one placebo
        per link x weighting (scrambled residual, never selectable). Fixed order: links in R22
        order; within a link plain before corrector, unweighted before GLS; then trees-off; then
        placebos.
    Inputs:
        links: R22 link set.
    Returns:
        the candidate arms in fixed order.
    Refuses:
        - a link set without identity.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.4 R26 (whole grid on the decision surface for every package; edge picks flagged,
# never extended, Q13 a; trees-off one candidate with no grid); pm25_adaptation.py:795-808 (rank: best
# MAE, strict '<' so the FIRST grid point wins a tie).
def penalty_search(arm: ArmSpec, surface_predictions: np.ndarray, y_surface: np.ndarray,
                   grid: Tuple[GridPoint, ...]) -> PenaltyPick:
    """R26: score every grid point of one arm on the decision surface by MAE and keep the best.

    Rule: R26.  Needed: Sat 3 Oct (layer).

    Contract (plan 2.4 R26, R27, R28):
        MAE in y units on back-transformed, CLIPPED predictions (R28 before any score). The whole
        grid is searched for every package. A pick on the grid's edge (first or last level, first
        or last ratio) is flagged, never extended. Trees-off has one candidate and no grid. On a
        tie the first grid point in grid order wins (the source's strict comparison).
    Inputs:
        arm: the arm.
        surface_predictions: (surface rows, grid points), y units, clipped.
        y_surface: decision-surface labels (inner score rows, or held-out fold rows).
        grid: the grid (R14), in its fixed order.
    Returns:
        PenaltyPick.
    Refuses:
        - a surface row count mismatch; non-finite predictions.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: pm25_adaptation.py:894-915 (N2 guard: eligible iff inner MAE < own link-matched normal's
# MAE, strict); plan 2.4 R27, Q17 a.
def n2_eligible(arm_mae: float, own_trees_off_mae: float) -> bool:
    """N2 guard: an arm is eligible only if it beats its own-link trees-off on the decision surface.

    Rule: R27 (N2).  Needed: Sat 3 Oct (layer).

    Contract (plan 2.4 R27, 2.2 R16):
        The comparison is against the arm's OWN link-matched trees-off (the geometric normal for a
        log arm, the arithmetic normal for an identity arm), both scored by MAE in y units.
    Inputs:
        arm_mae: the arm's best surface MAE (penalty_search).
        own_trees_off_mae: MAE of its link's trees-off on the same rows.
    Returns:
        True if eligible.
    Refuses:
        - non-finite inputs.
    OWNER DECISION: "beats" = strictly lower MAE (the source), versus lower by more than the R36
        tolerance.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: pm25_adaptation.py:915-930 (pick = min(eligible, key=MAE) else the arithmetic normal;
# tree_pick = best tree arm for the pin when declined); plan 2.4 R27; owner ruling (a decline adopts the
# ARITHMETIC normal, pm25_adaptation.py:133-138).
def select_adoption(picks: Tuple[PenaltyPick, ...], trees_off_mae: Mapping[Link, float],
                    beside: Mapping[str, float]) -> Adoption:
    """R27: rank eligible tree arms by decision-surface MAE; decline to the arithmetic normal when none
    is eligible.

    Rule: R27, G-LOCK.  Needed: Sat 3 Oct (layer).

    Contract (plan 2.4 R27):
        Only selectable tree arms are ranked, by MAE (Q37). N2: an arm is eligible only if it beats
        its own-link trees-off. If none is eligible, the layer declines to the decline target (the
        identity-link trees-off, the arithmetic normal). The best tree arm and its penalty are
        recorded either way (R29 pins it when the nowcast declined). predict-zero and corr2 are
        printed beside and never used. The result is hashed by vault.lock_adoption before test
        labels open.
    Inputs:
        picks: penalty_search results of every selectable tree arm.
        trees_off_mae: surface MAE of each link's trees-off.
        beside: printed-only numbers (predict-zero MAE, corr2 per arm).
    Returns:
        Adoption.
    Refuses:
        - a placebo or trees-off arm among the picks (never selectable).
    OWNER DECISION: a tie in MAE between two eligible arms -- propose the first in candidate_arms
        order (the source's min() behaviour).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.4 R28, 5 G-CLIP ("Legal-range clip on every back-transformed prediction and
# baseline; pre-clip rate logged"); pm25_forecast.py:530-531 (persistence floored at 0, replaced by R28).
def clip_to_legal(pred: np.ndarray, legal_range: Tuple[float, float],
                  allow_nan: bool) -> Tuple[np.ndarray, float, int]:
    """R28: clip to the target's legal range and report the pre-clip rate and the NaN count.

    Rule: R28, G-CLIP.  Needed: Sat 3 Oct (layer).

    Contract (plan 2.4 R28):
        Applied to every back-transformed prediction AND every baseline. The pre-clip rate (share of
        finite rows outside the range before clipping) is logged per arm; the pre-clip values are
        saved in test_preds. allow_nan=False for tree arms and trees-off: a prediction must exist
        for every scored row, so NaN is refused. allow_nan=True for baselines only: NaN marks a row
        with no baseline value (persistence where the issue step has no valid label), passes
        through unclipped and is counted.
    Inputs:
        pred: y-unit values before the clip.
        legal_range: the target's cited range (max may be inf).
        allow_nan: False for predictions, True for baselines.
    Returns:
        (clipped values with NaN kept, pre-clip rate over finite rows, NaN count).
    Refuses:
        - NaN in pred when allow_nan is False; +-inf anywhere.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.4 R24, R29 (at forecast leads only the pinned arm's placebo is built, at the
# longest lead; other arms are diagnostic).
def lead_arms(pinned: ArmSpec, lead: int, longest_lead: int) -> Tuple[ArmSpec, ...]:
    """The arms built at one forecast lead: the pinned arm and its link's trees-off; its placebo only
    at the longest lead.

    Rule: R24, R29.  Needed: Fri 9 Oct (forecast ladder).

    Contract (plan 2.4 R24, R29):
        Lagtrain at every lead is pinned to the nowcast adoption. The pinned arm's placebo (its link
        x weighting) is built and scored once, at the longest lead in R10's list (12 months; 1 year
        on annual data; 365 days for events). Other arms are diagnostic.
    Inputs:
        pinned: the arm R29 pins.
        lead: this lead.
        longest_lead: the longest lead in the lead plan.
    Returns:
        the arms to build at this lead.
    Refuses:
        - lead 0 (the nowcast uses candidate_arms).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.4 R29; pm25_adaptation.py:922-923 (pin to the best tree arm when declined);
# Q7 a (lagtrain + guard at every lead); Part 559, F45 (one placebo at the longest lead).
def forecast_adoption(nowcast: Adoption, lead: int, pinned_mae_guard: float, own_trees_off_mae_guard: float,
                      longest_lead: int) -> LeadAdoption:
    """R29: the adoption at one lead, pinned to the nowcast's link, tool, weighting and penalty, with
    the N2 guard run on the inner guard's cut.

    Rule: R29, R27 (N2), G-LOCK.  Needed: Fri 9 Oct (forecast ladder).

    Contract (plan 2.4 R29, 5 G-LOCK):
        Pin = the nowcast's adopted link, tool, weighting and penalty; if the nowcast declined, the
        best tree arm and that arm's penalty. The N2 guard runs at each lead on the inner guard's
        cut. The result is this lead's own adoption: it is hashed by vault.lock_lead_adoption
        before any of this lead's test rows is scored, and that lead's test labels open only
        against that hash. The nowcast band decides HELPS/HURTS at every lead
        (metrics.single_verdict).
    Inputs:
        nowcast: the nowcast Adoption.
        lead: this lead.
        pinned_mae_guard: the pinned arm's MAE on this lead's inner guard surface.
        own_trees_off_mae_guard: its link's trees-off MAE on the same rows.
        longest_lead: for the placebo flag.
    Returns:
        LeadAdoption.
    Refuses:
        - lead 0.
    OWNER DECISION: a pinned arm that FAILS the guard at a lead -- propose that lead adopts the decline
        target (as R27 does at the nowcast); the plan does not restate it in R29.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-PLUMB (trees-off = normal within the R36 tolerance; the base grid point reproduces
# the un-swept route; shared-Gram solve = reference solver on sample units; column layout per kind; lead
# 0 = nowcast; weighted arms with equal weights = unweighted arms); pm25_forecast.py:484-486.
def check_plumbing(trees_off: np.ndarray, normal: np.ndarray, base_point: np.ndarray, unswept: np.ndarray,
                   weighted_equal: Optional[np.ndarray], unweighted: Optional[np.ndarray],
                   lead0: Optional[np.ndarray], nowcast: Optional[np.ndarray],
                   tolerance: float) -> GuardResult:
    """G-PLUMB: the plumbing identities asserted at runtime.

    Rule: G-PLUMB, R36.  Needed: Sat 3 Oct (layer); lead-0 identity Fri 9 Oct.

    Contract (plan 5 G-PLUMB):
        Each identity must hold within the R36 tolerance of its link: trees-off equals the normal
        (every kind with a normal); the base grid point reproduces the un-swept route; weighted arms
        with equal weights equal unweighted arms; lead 0 equals the nowcast. (The shared-Gram versus
        reference-solver check lives in route/solve.py, moved as-is.)
    Inputs:
        pairs of arrays to compare (None skips that identity) and the tolerance.
    Returns:
        GuardResult (BLOCK on any failed identity).
    Refuses:
        - shape mismatches.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")
