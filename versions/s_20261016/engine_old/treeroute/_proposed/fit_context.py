"""PROPOSED signatures: treeroute/fit/context (plan 4.2). SCIENCE: owner signatures, agent bodies.

FitContext is the ONLY gateway to rows for every fitted object in R11: banks, correctors, router
rows, normals, c, fills, scalers, the GLS model, persistence phi and Type-3 blind constants. It is
built from three separate sources, so no single object carries both features and labels:
    DenseGrid       keys only (unit ids, groups, steps)
    FeatureSource   the joined, label-free feature pool (tree features and router context)
    LabelView       the vault, the only label source (G-LOCK)
and it hands out two containers:
    DonorRows    donor groups, dated at or before the cut. c, UB checks, tolerance, the GLS model and
                 its clip bounds, and Type-3 blind constants accept ONLY DonorRows (G-DONOR). Before
                 any FitContext exists, plan-time rules read vault.DonorLabels (label-only, same rule).
    UnitHistory  one unit's own rows at or before the cut. Normals and history fills accept ONLY
                 UnitHistory (G-DONOR).
Every hand-out writes a fitctx_log row: object kind, cut, max label time, row-key hash (G-FITCUT).
"""
# Provenance for the module: pm25_adaptation.py:546-549, 572-582, 621-650; plan 2.1 R11; plan 5
# G-FITCUT, G-DONOR, G-DISJOINT. F1/F2/F3 of the headline run go into FitContext (plan 8.1).
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Tuple

import numpy as np

from .common import (Bank, CutKind, CutPair, DenseGrid, Derived, FeatureSource, FitCtxLogRow,
                     FoldPurpose, SplitSets)
from .vault import LabelView


@dataclass(frozen=True)
class DonorRows:
    """Donor-group rows dated at or before one cut, labels valid (plan 2.1 R11, 5 G-DONOR).

    Constructed ONLY by FitContext.donor_rows. Any function that needs donor data types its
    parameter as DonorRows, so passing test rows is a type error before it is a leak."""
    groups: Tuple[str, ...]
    cut: int
    cut_kind: CutKind
    lead: int
    fold: Optional[int]
    unit_ids: np.ndarray
    times: np.ndarray
    group_of_row: np.ndarray
    grid_rows: np.ndarray               # dense-grid positions of the rows
    y: np.ndarray                       # from the vault (LabelView.asof)
    X: np.ndarray                       # kept tree features from the FeatureSource, 0-filled (R30), float32
    row_key_hash: str


@dataclass(frozen=True)
class UnitHistory:
    """One unit's own labelled rows at or before one cut (plan 5 G-DONOR).

    Constructed ONLY by FitContext.unit_history."""
    unit_id: str
    group: str
    cut: int
    cut_kind: CutKind
    lead: int
    times: np.ndarray
    season_keys: np.ndarray
    y: np.ndarray


@dataclass(frozen=True)
class RouterRows:
    """Fit rows of the router at one cut: the listed units' own labelled rows at or before the cut
    (per-unit, region), or a neighbour pool. Also the only rows scalers may be fitted on."""
    cut: int
    cut_kind: CutKind
    lead: int
    unit_ids: np.ndarray
    times: np.ndarray
    row_positions: np.ndarray           # rows in the tree-answer store's row-key order
    y: np.ndarray                       # from the vault
    context: np.ndarray                 # router_context on these rows, from the FeatureSource (NaN kept)


class FitContext:
    """The gateway for every fitted object at one (lead, cut kind[, fold]).

    Rule: R11, G-FITCUT, G-DONOR.  Needed: Wed 30 Sep (bank fits go through it).

    Attributes (read-only): features, the FeatureSource it was built with. It is label-free, so the
    route and scoring code may read score rows' router context from it.
    """

    # Provenance: plan 2.1 R11; plan 4.1 steps 3, 5 and 6.
    def __init__(self, derived: Mapping[str, Derived[Any]], split: SplitSets, grid: DenseGrid,
                 labels: LabelView, features: FeatureSource, picks: Mapping[str, Tuple[str, ...]],
                 lead: int, cut_kind: CutKind, fold: Optional[int] = None,
                 fold_purpose: Optional[FoldPurpose] = None) -> None:
        """Bind one cut from derived.json; never compute a cut here.

        Rule: R11, R13.  Needed: Wed 30 Sep (bank).

        Contract (plan 2.1 R11, R13, 1.6):
            The cut is read from derived.json (timing.cuts_for_leads) for this lead and cut kind.
            Donor groups come from the split (sorted). Rows come from three separate sources: keys
            from the grid, features from the FeatureSource, labels from the vault. The R18 unit
            picks decide which units each hand-out may return. In a fold context the held-out
            fold's groups are removed: a DECISION_SURFACE fold (R13, neighbour kind) is cut at the
            inner-fit end; a TYPE3 fold (plan 1.6 donor_fold_predict) keeps this lead's cut. Both
            are cut and logged like any context.
        Inputs:
            derived: derived.json content.
            split: the split sets.
            grid: the keys-only dense grid.
            labels: the label vault (the only label source).
            features: the joined, label-free feature pool (step 3 of plan 4.1).
            picks: {group: picked unit ids} (split.pick_units; hashed into the manifest).
            lead: lead in steps or days (0 = nowcast).
            cut_kind: FIT or GUARD.
            fold: donor fold index, or None.
            fold_purpose: why the fold exists (required with a fold, refused without one).
        Returns:
            None.
        Refuses:
            - a lead not in derived.json.
            - a DECISION_SURFACE fold when the decision surface is the inner window.
            - a fold without fold_purpose, or fold_purpose without a fold.
            - picks that name a unit outside its group or a group outside the split.
        """
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")

    # Provenance: plan 2.1 R11.
    def cut_pair(self) -> CutPair:
        """Both cuts of this context's lead, from derived.json.

        Rule: R11.  Needed: Wed 30 Sep (bank).

        Contract (plan 2.1 R11): read-only view of the cut pair this context enforces.
        Inputs:
            none.
        Returns:
            CutPair.
        Refuses:
            - nothing.
        """
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")

    # Provenance: plan 5 G-DONOR (c, UB checks, tolerance, GLS model and clip bounds, Type-3 blind
    # constants accept only DonorRows); Tier 1 reading test labels at adaptation.py:1702-1709.
    def donor_rows(self, purpose: str, unit_ids: Optional[Tuple[str, ...]] = None) -> DonorRows:
        """Donor-group rows with valid labels at or before this context's cut.

        Rule: R11, G-DONOR, G-FITCUT.  Needed: Wed 30 Sep (bank).

        Contract (plan 2.1 R11, 5 G-DONOR, G-FITCUT):
            Only donor groups (minus the held-out fold in a fold context), only rows at or before
            the cut whose label window has ended (timing.label_usable), only valid labels. y comes
            from the vault, X from the FeatureSource with the R30 0-fill. Writes a fitctx_log row
            (purpose, cut, max label time, row-key hash).
        Inputs:
            purpose: what the rows are for (bank, c, gls, tolerance, type3_blind, ...).
            unit_ids: restrict to these donor units; None = every picked donor unit.
        Returns:
            DonorRows.
        Refuses:
            - a unit that belongs to a test group or is not picked.
            - (internal assert) any row after the cut.
        """
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")

    # Provenance: plan 5 G-DONOR (normals and history fills accept only UnitHistory); plan 2.2 R15.
    def unit_history(self, unit_id: str, purpose: str) -> UnitHistory:
        """One unit's own labelled rows at or before this context's cut.

        Rule: R15, R17, G-DONOR.  Needed: Wed 30 Sep (bank); used Fri 2 Oct (normals).

        Contract (plan 2.2 R15, 5 G-DONOR):
            Rows of that unit only, at or before the cut, valid labels only, with their season keys
            (R2). Logged to fitctx_log.
        Inputs:
            unit_id: the unit.
            purpose: normal, history_fill, phi, last5_normal, ...
        Returns:
            UnitHistory.
        Refuses:
            - (internal assert) any row after the cut or from another unit.
        """
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")

    # Provenance: plan 2.1 R6 ("every router row is at or before [the train end]"); plan 2.3 R20
    # (router standardisation constants come from fit rows at or before the cut); pm25_adaptation.py:
    # 326-327 (cut asserts, now on the integer step).
    def router_rows(self, unit_ids: Tuple[str, ...], purpose: str) -> RouterRows:
        """The router's fit rows (and the only rows a scaler may see) for the listed units.

        Rule: R11, R14, R20, G-FITCUT.  Needed: Fri 2 Oct (per-unit router).

        Contract (plan 2.1 R6, R11; 2.3 R20):
            The listed units' own valid rows at or before the cut, in the tree-answer store's
            row-key order (unit by unit, step order), with their router context from the
            FeatureSource. Logged.
        Inputs:
            unit_ids: the picked test units served by this router fit.
            purpose: router, scaler, fallback_router.
        Returns:
            RouterRows.
        Refuses:
            - a unit that is not picked.
            - (internal assert) any row after the cut.
        """
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")

    # Provenance: plan 5 G-FITCUT ("every inner score row issued at or after the inner guard's cut",
    # pm25_forecast.py:566-574).
    def check_inner_score_rows(self, issue_times: np.ndarray) -> None:
        """Assert every inner score row is issued at or after the inner guard's cut.

        Rule: G-FITCUT.  Needed: Fri 9 Oct (forecast ladder).

        Contract (plan 5 G-FITCUT):
            Applies to guard contexts at every lead; a row issued before the guard cut would be
            scored by objects that saw its label.
        Inputs:
            issue_times: issue step (or day) of each inner score row.
        Returns:
            None.
        Refuses:
            - any row issued before the guard cut.
        """
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")

    # Provenance: plan 2.1 R11 (both cuts per lead); plan 4.1 step 11.
    def for_lead(self, lead: int, cut_kind: CutKind) -> "FitContext":
        """A new context at another lead and cut kind, same split, grid, features, picks and vault.

        Rule: R11, R29.  Needed: Fri 9 Oct (forecast ladder).

        Contract (plan 2.1 R11, 4.1 step 11):
            The lead's fit cut and the inner guard's cut come from derived.json.
        Inputs:
            lead: lead in steps or days.
            cut_kind: FIT or GUARD.
        Returns:
            FitContext.
        Refuses:
            - a lead not in derived.json.
        """
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")

    # Provenance: plan 2.1 R13 (fold i built from the OTHER donor groups, rows at or before the
    # inner-fit end); plan 1.6 (ctx.donor_fold_predict, per region K donor folds held out of the bank,
    # adaptation.py:104-106). Decision-surface folds: M8 (neighbour track); Type-3 folds: M4.
    def for_fold(self, fold: int, purpose: FoldPurpose) -> "FitContext":
        """A context for donor fold i: donor rows from the OTHER donor groups only.

        Rule: R13, plan 1.6, G-DISJOINT.  Needed: M4 (Type-3 folds); M8 (neighbour decision surface).

        Contract (plan 2.1 R13, 1.6):
            The held-out fold comes from split.make_donor_folds (K = min(5, donor groups), C8).
            DECISION_SURFACE (R13, neighbour kind only): fold i's bank, correctors, placebo, GLS
            model and c see only the other donor groups, with rows at or before the inner-fit end;
            its scored rows are the held-out groups' rows in the inner score years. TYPE3 (plan 1.6,
            any surface kind): the fold bank keeps this context's lead and cut, and serves only
            donor_fold_predict. Every fold context is cut and logged (fitctx_log records the fold
            and its purpose), and its bank manifest names the held-out fold (G-DISJOINT).
        Inputs:
            fold: fold index in [0, K).
            purpose: DECISION_SURFACE or TYPE3.
        Returns:
            FitContext.
        Refuses:
            - a fold index outside [0, K).
            - DECISION_SURFACE on an inner-window surface.
        """
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")

    # Provenance: plan 1.6 (ctx.fit_bank(target_transform) fits the engine recipe on a declared
    # transform, e.g. y > 0); M4 (Type-3 slot).
    def fit_bank(self, target_transform: Optional[Callable[[np.ndarray], np.ndarray]] = None) -> Bank:
        """Type-3 service: fit the engine bank recipe on donor rows at this cut, optionally on a
        declared transform of y.

        Rule: plan 1.6, R19, G-FITCUT.  Needed: M4 (Type-3 slot; not on the 8.0 day list).

        Contract (plan 1.6):
            A plug-in never builds its own bank. The bank uses bank_recipe.fit_donor_bank on
            donor_rows('type3_bank'); the transform is applied to y only.
        Inputs:
            target_transform: a declared elementwise transform of y (None = y itself).
        Returns:
            Bank.
        Refuses:
            - a transform that returns a different length or non-finite values.
        """
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")

    # Provenance: plan 1.6 (ctx.donor_fold_predict serves a plug-in's EVT boost, adaptation.py:104-106:
    # per region, K=5 donor folds held out of the bank). M4 (Type-3 slot).
    def donor_fold_predict(self, rows: np.ndarray) -> np.ndarray:
        """Type-3 service: tree predictions for donor rows from banks that did not see those rows'
        donor groups (donor folds).

        Rule: plan 1.6, R13 folds.  Needed: M4 (Type-3 slot; not on the 8.0 day list).

        Contract (plan 1.6; source: provenance comment):
            Donor groups are split into K folds (split.make_donor_folds); each fold bank is built
            through for_fold(i, TYPE3), so it keeps this context's cut on any surface kind; each row
            is predicted by the bank fitted without its fold.
        Inputs:
            rows: donor row positions.
        Returns:
            predictions per row.
        Refuses:
            - a row from a test group.
        OWNER DECISION: the plan does not state this service's return (mean tree answer, or routed
            prediction); the Type-3 plug-in's author must declare it.
        """
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")

    # Provenance: plan 7.1 (fitctx_log.parquet in the run folder); plan 5 G-FITCUT.
    def log(self) -> Tuple[FitCtxLogRow, ...]:
        """Every row hand-out this context made, for fitctx_log.parquet.

        Rule: G-FITCUT.  Needed: Wed 30 Sep (bank).

        Contract (plan 5 G-FITCUT, 7.1):
            One row per hand-out: object kind, purpose, lead, cut kind, cut, max label time, row
            count, groups hash, row-key hash, fold and fold purpose.
        Inputs:
            none.
        Returns:
            tuple of FitCtxLogRow.
        Refuses:
            - nothing.
        """
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")
