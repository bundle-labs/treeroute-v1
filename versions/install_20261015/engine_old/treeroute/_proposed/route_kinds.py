"""PROPOSED signatures: treeroute/route/kinds.py (plan 4.2, R12-R16). SCIENCE review: each kind
reproduces its source in the harness.

One column-block builder and three kinds:
    per-unit   one block-penalised ridge per test unit on its own history at or before the cut
               (merges route_percell, route_sweep, route_idx);
    region     one pooled ridge per test group, with the U-1 unpenalised normal column and the evenly
               spaced whole-unit cap; also serves short-history units of a per-unit dataset;
    neighbour  a strict pool per row, two-stage pick (M8 / optional track).
The linear solvers (solve_local, the dual and shared-Gram solves, the trace-normalised ridge) move
AS-IS into route/solve.py; the parallel unit loop there is boilerplate gated by byte identity.
"""
# Provenance for the module: pm25_adaptation.py:310-444 (route_percell, route_sweep, trees-off);
# pm25_forecast.py:265-305; defo_softgate.py:105-124 (trace-normalised ridge); adaptation.py:1149-1150
# (row linspace cap), 1572-1701 (neighbour pool). U-1 approved by the owner (plan Rulings table).
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

import numpy as np

from .common import (GridPoint, Link, RouterDesign, RouterKind, TreeAnswerStore)
from .fit_context import DonorRows, FitContext, RouterRows, UnitHistory


@dataclass(frozen=True)
class NormalTable:
    """R15: one unit's normal per season key in one link at one cut, with the fallback counts."""
    unit_id: str
    link: Link
    cut: int
    c: Optional[float]                 # the R23 c it was built with (log_c only)
    by_season: Mapping[int, float]
    unit_all_season_mean: float
    n_season_from_unit_mean: int
    used_donor_mean: bool


@dataclass(frozen=True)
class DesignMatrix:
    """One router design: rows x columns, with the block of each column (intercept, normal, context,
    trees) so the penalty vector can be built from RouterDesign."""
    X: np.ndarray
    blocks: Tuple[str, ...]


@dataclass(frozen=True)
class RouteOutput:
    """A router's predictions in link space for the rows it scores: one column per grid point, plus
    the trees-off column, with fallback counts."""
    row_positions: np.ndarray
    predictions: np.ndarray            # (rows, grid points)
    trees_off: np.ndarray              # (rows,)
    grid: Tuple[GridPoint, ...]
    n_units_fitted: int
    n_units_fallback: int
    n_rows_pool_fallback: int          # neighbour only


# Provenance: plan 2.2 R15; pm25_adaptation.py:584-604 (add_clim: per cell-month mean of link(y) over
# the given rows ONLY; fallbacks the cell's own mean, then the donor mean); :436-440 (residual has zero
# mean in every season with fit rows, so trees-off = normal).
def unit_season_normal(history: UnitHistory, kind: RouterKind, link: Link, c: Optional[float],
                       ub: Optional[float], needed_season_keys: Tuple[int, ...],
                       donor_link_mean: float) -> NormalTable:
    """R15: the unit's normal per season key: the mean of link(y) over its own fit rows at or before
    the cut, however few.

    Rule: R15, G-DONOR.  Needed: Fri 2 Oct (per-unit router + normal column).

    Contract (plan 2.2 R15):
        Per unit and season key, the mean of link(y) over the unit's own fit rows at or before the
        cut, however few. Only a unit-season with NO fit row takes the unit's all-season mean, then
        the donor-row mean (counted). Region: each unit's normal uses all its fit-year rows, whether
        or not the unit is inside the capped router fit. None for neighbour.
    Inputs:
        history: FitContext.unit_history (the only accepted source, G-DONOR).
        kind: the R12 router kind of the run.
        link: the arm's link; c and ub are the link constants (c per cut, R23; ub from the fact).
        needed_season_keys: keys of the rows this normal must serve.
        donor_link_mean: donor_link_mean() at the same cut (last fallback).
    Returns:
        NormalTable (with the cut and c it was built with).
    Refuses:
        - kind NEIGHBOUR (no normal exists).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: pm25_adaptation.py:570-577 (gmean, lgmean, lcgmean over donor rows).
def donor_link_mean(donor_rows: DonorRows, link: Link, c: Optional[float], ub: Optional[float]) -> float:
    """The donor-row mean of link(y) at a cut: the last fallback of the normal.

    Rule: R15, G-DONOR.  Needed: Fri 2 Oct (per-unit router + normal column).

    Contract (plan 2.2 R15, 5 G-DONOR):
        Mean over DonorRows only.
    Inputs:
        donor_rows: DonorRows at the cut.
        link, c, ub: the link and its constants.
    Returns:
        the mean.
    Refuses:
        - no finite value.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.2 R14 (column layouts); pm25_adaptation.py:409-414 (design built once per cell:
# intercept, normal centred on its fit-row mean, standardised context, tree answers).
def build_column_block(design: RouterDesign, normal: Optional[np.ndarray], context: Optional[np.ndarray],
                       trees: Optional[np.ndarray], normal_centre: Optional[float]) -> DesignMatrix:
    """Build one router design matrix in the layout R14 names for the kind.

    Rule: R14, G-PLUMB (layout).  Needed: Fri 2 Oct (per-unit router).

    Contract (plan 2.2 R14):
        Per-unit: intercept, normal (unpenalised), context, trees. Region: intercept, normal
        (unpenalised, U-1), trees. Neighbour: intercept, context, trees. The normal column is
        centred on its fit-row mean (as the source does); context is standardised with constants
        from fit rows at or before the cut (router_standardisation). The same builder serves fit
        and score rows.
    Inputs:
        design: R14 outcome.
        normal: link-matched normal per row (None for neighbour).
        context: standardised context per row (None when the kind has none or none is declared).
        trees: tree answers per row (None for trees-off).
        normal_centre: the fit-row mean of the normal (applied to fit and score rows alike).
    Returns:
        DesignMatrix.
    Refuses:
        - a block the design does not list, or a missing block it does list.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.3 R20 ("Router standardisation constants come from fit rows at or before the cut,
# after the batched = whole proof"); pm25_adaptation.py:335, 395 (mean and sd over all fit rows,
# sd + 1e-9).
def router_standardisation(fit_rows: RouterRows, context: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Mean and standard deviation of each context column over the router's fit rows at the cut.

    Rule: R20, G-DONOR (scalers).  Needed: Fri 2 Oct (per-unit router).

    Contract (plan 2.3 R20, 5 G-DONOR):
        Scalers see only fit rows at or before the cut. Constants come from ALL fit rows of the
        pass (whole), never from one batch, so batching cannot move a number.
    Inputs:
        fit_rows: FitContext.router_rows.
        context: context values on those rows.
    Returns:
        (mean, sd) per context column.
    Refuses:
        - rows after the cut.
    OWNER DECISION: the source adds 1e-9 to sd; propose keeping it (a constant context column then
        standardises to 0 instead of failing).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.2 R16; 9.1 item 2a (trees-off = intercept + normal only, context dropped);
# pm25_adaptation.py:436-442 (trees-off solved with the tree block dropped).
def trees_off_with_normal(fit_normal: np.ndarray, fit_y_link: np.ndarray, score_normal: np.ndarray) -> np.ndarray:
    """R16 trees-off for kinds with a normal: intercept + normal only, unweighted, context dropped.

    Rule: R16, G-PLUMB.  Needed: Fri 2 Oct (per-unit router + normal column).

    Contract (plan 2.2 R16):
        Fitted unweighted on the unit's (per-unit) or group's (region) fit rows. It equals the
        normal exactly, even when context varies inside a unit-season; the equality is asserted
        within the R36 tolerance (G-PLUMB).
    Inputs:
        fit_normal: link-matched normal on fit rows.
        fit_y_link: link(y) on fit rows.
        score_normal: the normal on the rows to predict.
    Returns:
        trees-off predictions (link space) on the score rows.
    Refuses:
        - (assert) a result that differs from score_normal beyond the R36 tolerance.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.2 R16 ("Neighbour: trees-off = intercept + context fit").
def trees_off_neighbour(fit: DesignMatrix, fit_y_link: np.ndarray, score: DesignMatrix, level: GridPoint) -> np.ndarray:
    """R16 trees-off for the neighbour kind: intercept + context, fitted on the row's pool.

    Rule: R16.  Needed: M8 (neighbour track).

    Contract (plan 2.2 R16):
        No normal exists; trees-off is the intercept + context fit on the pool; its identity-link
        version is the decline target. The single verdict still uses the donor-row median (Q15 a).
    Inputs:
        fit, score: intercept + context designs (no tree block).
        fit_y_link: link(y) on the pool.
        level: the context penalty point in use.
    Returns:
        trees-off predictions (link space).
    Refuses:
        - a design containing a tree block.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.2 R16 (guard reference = each arm's own-link trees-off; decline target = the
# identity-link trees-off, the arithmetic normal; ruling of the owner in the Rulings table).
def reference_predictions(trees_off_by_link: Mapping[Link, np.ndarray]) -> Tuple[Mapping[Link, np.ndarray], np.ndarray]:
    """R16 references: the guard reference per link and the one decline target, in y units.

    Rule: R16, R27, R34.  Needed: Fri 2 Oct (per-unit router + normal column).

    Contract (plan 2.2 R16):
        Guard reference of a link = that link's trees-off, back-transformed and clipped (the
        geometric normal for a log arm). Decline target = the identity-link trees-off (the
        arithmetic normal). For identity arms the two are the same.
    Inputs:
        trees_off_by_link: {link: trees-off already back-transformed and clipped, y units}.
    Returns:
        ({link: guard reference}, decline target).
    Refuses:
        - no identity entry.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: pm25_adaptation.py:360-444 (route_sweep: design built once per unit, all grid points
# solved; shared-Gram dual with a check against solve_local on NVERIFY units; asserts on the cut).
def route_per_unit(ctx: FitContext, unit_ids: Tuple[str, ...], link: Link, c: Optional[float],
                   ub: Optional[float], normals: Mapping[str, NormalTable], design: RouterDesign,
                   answers: TreeAnswerStore, score_row_positions: np.ndarray,
                   weights: Optional[np.ndarray]) -> RouteOutput:
    """Per-unit router: one block-penalised ridge per test unit on its own history at or before the
    cut, solved at every grid point, plus trees-off.

    Rule: R12, R14, R15, R16, R23, G-FITCUT.  Needed: Fri 2 Oct (per-unit router + grid + parallel units).

    Contract (plan 2.2 R12-R16, 2.4 R23, 4.5 speedup 3):
        For each unit: fit rows = FitContext.router_rows (own rows at or before the cut, with their
        context); y goes to link space with the GIVEN c and ub (never recomputed here: one c per
        cut, R23); design by build_column_block with the unit's GIVEN link-matched normal
        (unpenalised), standardised context and tree answers; solve every grid point
        (route/solve.py, moved as-is, including the reference cross-check on the first units).
        Score rows' context is read from ctx.features (label-free). Units with fewer than 24 valid
        fit rows go to their group's fallback region router (fallback_units; route_region fitted on
        all of the group's picked units, at the level from search_fallback_level). Weights (GLS
        arms) apply to fit rows only. Units are solved 8 at once with BLAS at 1 thread
        (boilerplate; byte-identical).
    Inputs:
        ctx: the FitContext of this cut.
        unit_ids: the picked test units.
        link: the arm's link.
        c, ub: the link constants of this cut (layer.c_for_cut; the target's legal maximum).
        normals: {unit id: NormalTable in this link at this cut} (unit_season_normal).
        design: R14 outcome.
        answers: tree-answer store (plain or corrector table, by the arm).
        score_row_positions: the rows to predict (decision surface or test rows).
        weights: GLS weights on fit rows, or None.
    Returns:
        RouteOutput.
    Refuses:
        - a fit row after the cut, or a score row at or before it (source asserts).
        - a normal of another link, cut or c, or a unit without a normal.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.2 R14 (largest m with positions floor(i x (N-1)/(m-1)) whose pooled fit rows stay
# at or under 60,000); adaptation.py:1149-1150 (the shipped np.linspace pick over rows).
def region_cap_units(sorted_units: Tuple[str, ...], fit_rows_per_unit: Mapping[str, int], budget: int) -> Tuple[str, ...]:
    """The region router's fit cap: the largest set of evenly spaced WHOLE units whose pooled fit rows
    stay within the budget.

    Rule: R14, C7.  Needed: Tue 6 Oct (region router).

    Contract (plan 2.2 R14, C7, Q11 a):
        Over the N units in sorted id order, keep the largest m such that the units at positions
        floor(i x (N-1)/(m-1)), i = 0..m-1, have pooled fit rows at or under the budget (60,000);
        all units when they fit. Every kept unit keeps all its fit years.
    Inputs:
        sorted_units: the group's picked units, sorted.
        fit_rows_per_unit: valid fit rows per unit at the cut.
        budget: the engine constant (60,000).
    Returns:
        the kept units, in sorted order.
    Refuses:
        - a single unit whose own rows exceed the budget.
    OWNER DECISION: m = 1 makes the formula divide by zero; propose position 0 (the first unit).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.2 R14 (region: intercept, normal unpenalised (U-1), trees trace-normalised ridge);
# defo_softgate.py:105-124 (ridge: centre columns and y, add lam x trace(G)/p to the diagonal).
def route_region(ctx: FitContext, group: str, unit_ids: Tuple[str, ...], link: Link, c: Optional[float],
                 ub: Optional[float], normals: Mapping[str, NormalTable], design: RouterDesign,
                 answers: TreeAnswerStore, score_row_positions: np.ndarray,
                 weights: Optional[np.ndarray]) -> RouteOutput:
    """Region router: one pooled ridge per test group on its capped whole units, with the per-unit
    normal as an unpenalised column, solved at every level, plus trees-off.

    Rule: R12, R14, R15, R16, U-1.  Needed: Tue 6 Oct (region router + normal column).

    Contract (plan 2.2 R14-R16):
        Fit rows = router_rows of region_cap_units(...) at the cut. Columns: intercept, the unit's
        link-matched normal (unpenalised; each unit's normal uses all its fit-year rows even when
        the unit is outside the cap), trees (trace-normalised ridge). 7 levels around lambda 100.
        Trees-off = intercept + normal = the normal (asserted). BLAS stays at 4 threads (one pooled
        solve; not sped up).
    Inputs:
        ctx: FitContext of this cut.
        group: the test group.
        unit_ids: the group's picked test units.
        link, c, ub, normals, design, answers, score_row_positions, weights: as route_per_unit
            (normals cover every picked unit of the group, inside the cap or not).
    Returns:
        RouteOutput.
    Refuses:
        - as route_per_unit.
    OWNER DECISION: the shipped ridge had no normal column; propose the unpenalised normal enters by
        projecting intercept and normal out first (as the per-unit dual path does) with the trace
        normalisation taken over the tree block only.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.2 R12 (a unit with fewer than 24 valid rows uses its group's region router;
# counted; flagged above 5%); replaces the donor-wide mean at pm25_adaptation.py:342-344.
def fallback_units(valid_fit_rows: Mapping[str, int]) -> Tuple[Tuple[str, ...], float]:
    """Units of a per-unit dataset with fewer than 24 valid fit rows, and their share.

    Rule: R12, C10.  Needed: Tue 6 Oct (region router serves short-history units).

    Contract (plan 2.2 R12, C10):
        Counted per pass; the share is flagged above 5% of units (report only).
    Inputs:
        valid_fit_rows: {picked test unit: valid fit rows at the cut}.
    Returns:
        (fallback unit ids sorted, share).
    Refuses:
        - an empty map.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.2 R12 (the fallback router is the region design fitted on all of the group's picked
# units' rows at or before the cut; its level is searched once on the 7-level region grid, scored on the
# fallback units' inner score rows pooled across groups; under 10 such units it uses the lambda centre).
def search_fallback_level(surface_mae_by_level: Mapping[GridPoint, float], n_fallback_units_scored: int,
                          centre: GridPoint) -> Tuple[GridPoint, bool]:
    """The fallback region router's level: searched once, pooled across groups, or the centre when
    fewer than 10 fallback units have inner score rows.

    Rule: R12, C15.  Needed: Tue 6 Oct (region router serves short-history units).

    Contract (plan 2.2 R12, C15):
        Minimum pooled MAE on the fallback units' inner score rows over the 7 region levels; ties go
        to the first level in grid order (as layer.penalty_search). With fewer than 10 such units,
        the lambda centre is used and the count is printed.
    Inputs:
        surface_mae_by_level: pooled MAE per level (y units, clipped, R28).
        n_fallback_units_scored: fallback units with inner score rows.
        centre: the region centre (level 1).
    Returns:
        (chosen level, used_centre).
    Refuses:
        - a level set that is not the region grid.
    OWNER DECISION: sign the 10-unit threshold (9.1 item 2f).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.2 R14 (neighbour pool: donor groups and the unit's own group, never another test
# group; labelled rows at or before the lead's cut; 150 nearest by distance then 50 nearest in
# standardised tree-feature space; under 12 rows -> donor-row median, counted); adaptation.py:1620-1640
# (haversine; 3K then K in Z-space; MINOK 12); flag 13 (strict pool; the shipped fallback was the
# training mean, adaptation.py:1633). M8 / optional track.
def neighbour_pool(row_unit: str, row_group: str, row_lat: float, row_lon: float, row_features: np.ndarray,
                   candidates: RouterRows, candidate_lat: np.ndarray, candidate_lon: np.ndarray,
                   candidate_features: np.ndarray, candidate_group: np.ndarray,
                   test_groups: Tuple[str, ...]) -> Optional[np.ndarray]:
    """The strict pool of one neighbour-kind row, or None when fewer than 12 rows qualify.

    Rule: R14 (neighbour), C11.  Needed: M8 (neighbour track).

    Contract (plan 2.2 R14, C11, 3.3 flag 13):
        Eligible rows: labelled, at or before the lead's cut, from the donor groups and the row's
        own group, never another test group, never the row itself. Take the 150 nearest by
        distance, then the 50 nearest of those in standardised tree-feature space. Under 12 eligible
        rows the caller falls back to the donor-row median (counted).
    Inputs:
        row_*: the target row's unit, group, location and standardised features.
        candidates: labelled rows at or before the cut (FitContext.router_rows over the pool units).
        candidate_*: their locations, standardised features and groups.
        test_groups: the sorted test set.
    Returns:
        pool row positions (at most 50), or None.
    Refuses:
        - (assert) any pool row after the cut or from another test group.
    OWNER DECISION: distance -- propose great-circle (haversine), as the source.
    OWNER DECISION: feature standardisation constants -- propose donor rows at or before the cut.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.2 R14 (neighbour: intercept, context, trees; 35 points around 0.5 / 0.25,
# adaptation.py:1434). M8 / optional track.
def route_neighbour(ctx: FitContext, link: Link, c: Optional[float], ub: Optional[float],
                    design: RouterDesign, answers: TreeAnswerStore,
                    score_row_positions: np.ndarray, donor_median: float,
                    weights: Optional[np.ndarray]) -> RouteOutput:
    """Neighbour router: per row, a ridge on its strict pool (intercept, context, trees) at every grid
    point, plus trees-off; the donor-row median when the pool is too small.

    Rule: R12, R14, R16, R23.  Needed: M8 (neighbour track).

    Contract (plan 2.2 R14, R16, 2.4 R23):
        Pools from neighbour_pool; pool y goes to link space with the GIVEN c and ub (never
        recomputed here); rows whose pool is None take the donor-row median (counted in
        RouteOutput.n_rows_pool_fallback). Rows are solved 8 at once (boilerplate).
    Inputs:
        ctx: FitContext (fold context on the decision surface).
        link, c, ub: the arm's link and its constants at this cut (per fold on the surface).
        design: R14 outcome.
        answers: tree-answer store.
        score_row_positions: rows to predict.
        donor_median: metrics.baseline_donor_median at this cut.
        weights: GLS weights, or None.
    Returns:
        RouteOutput.
    Refuses:
        - as neighbour_pool.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")
