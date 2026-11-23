"""PROPOSED signatures: the GLS row-weight model in treeroute/fit/weights (plan 4.2, R25). SCIENCE:
owner signatures, agent bodies.

GLS weights are a Type-2 TOOL: they change the router's row weights, never the tree answers, so
weighted arms read the same tree-answer tables. One weight model per cut serves that cut's decision
and test pass. At a forecast lead it is refit at the lead's cut, with its own donor-row pass, only if
the pinned arm is weighted (R29). Per fold for the neighbour kind.
"""
# Provenance for the module: coral_architecture.py:304-313 (the shipped weight model, corrected):
# RandomForestRegressor(120, max_depth=8, min_samples_leaf=20, n_jobs=-1, random_state=0) fitted on
# |y - oof| (in-sample residuals, :305-307); clip bounds from whatever frame it weighted, test rows
# included (:311). Plan 9.1 item 2b (owner signs the error target and the constants).
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np

from .common import FittedTree, TreeAnswerStore
from .fit_context import DonorRows, FitContext


@dataclass(frozen=True)
class WeightModel:
    """One cut's weight model and its donor-only constants (all written to derived.json)."""
    forest: FittedTree
    cut: int
    lead: int
    sigma_floor: float
    clip_low: float
    clip_high: float
    fold: int


# Provenance: plan 2.4 R25 ("the absolute gap between y and the mean of the trees from the OTHER donor
# groups"); coral_architecture.py:305-307 fitted in-sample residuals instead.
def cross_region_error(donor_rows: DonorRows, tree_answers: np.ndarray, tree_group: Tuple[str, ...]) -> np.ndarray:
    """The weight model's target: |y - mean answer of the trees from the OTHER donor groups|, per
    donor row.

    Rule: R25.  Needed: Sat 3 Oct (layer: GLS tool).

    Contract (plan 2.4 R25, 9.1 item 2b):
        For a donor row of group g, average the answers of every tree whose donor group is not g,
        and take the absolute gap to y. This needs every tree's answer on every donor row up to the
        inner-fit end (the donor-row pass, served by the parallel writer, plan 4.5).
    Inputs:
        donor_rows: donor rows at or before the inner-fit end of this cut.
        tree_answers: (rows, trees) answers from the donor-row pass, rows in donor_rows order.
        tree_group: donor group of each tree column.
    Returns:
        float64 error per donor row.
    Refuses:
        - a donor group whose rows have no tree from another group (a single-donor bank).
        - shape mismatches.
    OWNER DECISION: sign this error target (9.1 item 2b).
    OWNER DECISION: which answers -- propose the PLAIN tree answers (not tree + corrector); the plan
        says "the mean of the trees".
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.4 R25, C13 (120 trees, depth 8, min leaf 20, max_features 1.0, bootstrap on,
# random_state 0, 4 pinned threads); coral_architecture.py:304.
def fit_weight_model(donor_rows: DonorRows, error_target: np.ndarray) -> FittedTree:
    """Fit the sigma model: a random forest from the kept tree features to the cross-region error.

    Rule: R25, G-DONOR, G-NODRAW.  Needed: Sat 3 Oct (layer: GLS tool).

    Contract (plan 2.4 R25, C13, 5 G-NODRAW):
        Engine constants: 120 trees, depth 8, min leaf 20, max_features 1.0 (all features),
        bootstrap on, random_state 0 (fixed, disclosed, never varied, recorded in the manifest),
        4 pinned threads. Inputs are the kept tree features (0-filled, R30), from donor rows at or
        before the inner-fit end of its cut.
    Inputs:
        donor_rows: DonorRows (G-DONOR: only donor rows may fit it).
        error_target: cross_region_error on the same rows.
    Returns:
        the fitted forest.
    Refuses:
        - rows after the cut, or a length mismatch.
    OWNER DECISION: "the inner-fit end of its cut" at a forecast lead -- propose that lead's guard
        cut (the plan defines it only for the nowcast).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.4 R25 ("sigma is floored at 1% of the donor spread (R36's s)").
def sigma_floor(identity_link_s: float) -> float:
    """The floor on predicted sigma: 1% of the donor spread.

    Rule: R25, R36.  Needed: Sat 3 Oct (layer: GLS tool).

    Contract (plan 2.4 R25):
        floor = 0.01 x s, where s is R36's donor-row standard deviation (metrics.guard_tolerance's s).
    Inputs:
        identity_link_s: R36's s for the identity link at this cut.
    Returns:
        the floor.
    Refuses:
        - s <= 0 (G-SUPPORT refuses a constant target earlier).
    OWNER DECISION: R36 has one s per link; propose the IDENTITY-link s, because sigma is on the y
        scale.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.4 R25 ("The clip bounds are the 5th and 95th percentiles of sigma on those donor
# rows, written to derived.json"); coral_architecture.py:311 took them from test rows (the defect).
def sigma_clip_bounds(sigma_on_donor_rows: np.ndarray) -> Tuple[float, float]:
    """The clip bounds of sigma: its 5th and 95th percentiles on the donor rows the model was fitted on.

    Rule: R25, G-DONOR.  Needed: Sat 3 Oct (layer: GLS tool).

    Contract (plan 2.4 R25, 5 G-DONOR):
        Donor rows only; never the frame being weighted. Written to derived.json.
    Inputs:
        sigma_on_donor_rows: the model's predictions on its own donor rows (after the floor).
    Returns:
        (low, high).
    Refuses:
        - fewer than 2 finite values.
    OWNER DECISION: percentile method -- propose numpy's default (linear), as the source.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.4 R25 ("Weight = 1/sigma^2, with the max/min ratio capped at 100");
# coral_architecture.py:308-313.
def row_weights(sigma: np.ndarray, floor: float, clip_low: float, clip_high: float) -> np.ndarray:
    """Router row weights from predicted sigma: floor, clip, 1/sigma^2, max/min ratio capped at 100.

    Rule: R25.  Needed: Sat 3 Oct (layer: GLS tool).

    Contract (plan 2.4 R25):
        sigma is floored, clipped to the donor bounds, and turned into weight = 1/sigma^2; the ratio
        of the largest to the smallest weight is capped at 100. Weights apply to router fit rows
        only. With equal sigma the weighted arm must equal the unweighted arm (G-PLUMB).
    Inputs:
        sigma: predicted sigma on the router's fit rows.
        floor, clip_low, clip_high: from sigma_floor and sigma_clip_bounds.
    Returns:
        weights (float64).
    Refuses:
        - non-finite sigma.
    OWNER DECISION: order and cap mechanics -- propose floor, then clip, then weights, then cap the
        ratio by raising the smallest weights to (largest / 100).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.4 R25 (per cut; per fold for neighbour; refit per lead only if the pinned arm is
# weighted); plan 4.5 (donor-row pass through the parallel writer).
def weight_model_for_cut(fit_ctx: FitContext, guard_ctx: FitContext, answers: TreeAnswerStore,
                         tree_group: Tuple[str, ...]) -> WeightModel:
    """Build one cut's weight model end to end: donor rows, the donor-row pass, the error target,
    the forest, the floor and the clip bounds.

    Rule: R25, G-FITCUT, G-DONOR.  Needed: Sat 3 Oct (layer: GLS tool).

    Contract (plan 2.4 R25, 4.5):
        One model per lead cut; it serves that cut's decision and test pass. The model is fitted on
        donor rows at or before the inner-fit end of its cut, which is the same lead's GUARD cut
        (at lead 0 the guard cut is the inner-fit end), so those rows come from
        guard_ctx.donor_rows('gls'); the tree answers come from the bank of fit_ctx's cut; the
        model is recorded in derived.json under fit_ctx's lead. Called at a forecast lead only when
        the pinned arm is weighted (R29). Per fold for the neighbour kind (both contexts then carry
        the same DECISION_SURFACE fold).
    Inputs:
        fit_ctx: the FIT context of this lead (whose decision and test pass the weights serve).
        guard_ctx: the GUARD context of the same lead (it supplies the DonorRows and logs the
            hand-out).
        answers: the tree-answer store (plain table) for the donor-row pass.
        tree_group: donor group of each tree column.
    Returns:
        WeightModel.
    Refuses:
        - contexts of different leads or folds; fit_ctx not a FIT context; guard_ctx not a GUARD
          context.
        - anything its parts refuse.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")
