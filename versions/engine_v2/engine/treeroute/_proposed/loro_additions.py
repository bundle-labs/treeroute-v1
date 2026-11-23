"""PROPOSED signatures: leave-one-region-out (LORO) additions to treeroute/split.py, derive/,
route/kinds.py and the validators (plan 1.2, R12-R14, R18, R21, R34, 4.6). SCIENCE (CV splits and
routing): owner signatures, agent bodies.

The owner's LORO ruling replaces the hand-made donor/test split. Every group that is not excluded
trains its own specialist trees and is tested, and a unit's router never sees its own group's trees
(they are dropped as columns). The time split, the router on the unit's own history and the
issue-date cuts do not change. This file holds the NEW and CHANGED science signatures that follow:

    split file and its checks            LoroSplitSets, loro_split_differences, groups_under_loro,
                                         check_g_split_loro, check_g_support_loro,
                                         check_scored_units_loro
    two unit lists per group (R18)       derive_r18_bank_count, derive_r18_scored_count,
                                         evenly_spaced_subset, pick_unit_lists
    overlap blocks (R14)                 OverlapBlocks, derive_overlap_blocks
    own-block column exclusion (R14)     router_tree_columns, assert_no_own_group_column,
                                         assert_group_manifests, own_block_masked_answers
    routers, fit and scored decoupled    route_per_unit_loro, route_region_loro
    neighbour kind (R13, R14; M8)        derive_r13_surface_loro, neighbour_pool_loro,
                                         route_neighbour_loro
    reporting groups (R34)               report_groupings, nearest_other_group_distance,
                                         distance_band_edges
    smoke plan (R21)                     derive_r21_smoke_plan_loro
    donor-only rivals' folds (4.6)       rival_fold_of_group, rival_fold_training_groups,
                                         rival_tuning_holdout, assert_rival_source

engine/SIGNATURES_LORO_ADDENDUM.md lists which older _proposed signatures these supersede and the new
owner decisions (L1-L7). Every body is one line that raises NotImplementedError; nothing here runs.

"A router's own groups" below always means its OVERLAP BLOCK (derive_overlap_blocks): the groups that
share or touch a unit location with its group. Most blocks hold one group.

No draw anywhere: subsets by stride or by evenly spaced positions, folds round-robin (G-NODRAW).
"""
# Provenance for the module: engine/OWNER_RULINGS_2026-09-28.md section D (owner ruling, 2026-09-28
# night: leave-one-region-out, same total test cells); APP_PLAN.md 1.2, R12-R14, R18-R21, R25, R34,
# R35, C16, C17, 4.6. Measurements: D:/treeroute/loro_measure (units_census.csv, loro_components.csv,
# bench_region_gram.py, subsample_precision.py). Package numbers live in comments only (G-NONAMES
# convention of this folder): PM2.5 127 groups, fire 40, defo 42, NDVI 133. Revised 2026-09-28 late
# night after the LORO review: overlap blocks, masked Type-3 services, fallback bank rows, budget options.
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Optional, Tuple

import numpy as np

from .common import (BankManifest, Derived, GuardResult, Link, RouterDesign, RouterKind,
                     SeasonKeySpec, TreeAnswerStore)
from .fit_context import FitContext, RouterRows
from .route_kinds import NormalTable, RouteOutput
from .vault import DonorLabels


# ------------------------------------------------------------------------------------------------
# Shapes
# ------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class LoroSplitSets:
    """split.yaml under LORO (plan 1.2). It replaces common.SplitSets: there is no donor or test list.
    Lists are sets; the engine sorts them by name."""
    excluded: Mapping[str, str]
    seen_during_design: Tuple[str, ...]
    continuity_groups: Tuple[str, ...]       # reporting only: the old hard-split test groups (may be empty)


@dataclass(frozen=True)
class LoroSplitDiff:
    """Every set difference between split.yaml and the data under LORO (printed by `split freeze`)."""
    listed_not_in_data: Tuple[str, ...]      # an excluded, seen or continuity group absent from the data
    reported_and_excluded: Tuple[str, ...]   # a seen_during_design or continuity group that is also excluded
    duplicates: Tuple[str, ...]


@dataclass(frozen=True)
class UnitCounts:
    """R18 outcome under LORO: two counts per group."""
    rule_value: int                          # n: the bank-count rule value before the per-group cap
    k_group_equivalents: int                 # K (C16), recorded
    n_groups: int                            # G
    bank_by_group: Mapping[str, int]         # units whose rows train the group's trees and fit its region router
    scored_by_group: Mapping[str, int]       # units scored per group; never above the bank count


@dataclass(frozen=True)
class UnitLists:
    """R18 picks under LORO: per group, the bank units (stride over sorted candidates) and the scored
    units (an evenly spaced subset of the bank units). Both lists are hashed into the manifest."""
    bank: Mapping[str, Tuple[str, ...]]
    scored: Mapping[str, Tuple[str, ...]]


class LoroSurfaceKind(Enum):
    """R13 outcome under LORO. Replaces common.SurfaceKind's DONOR_FOLDS for the neighbour kind."""
    INNER_WINDOW = "inner_window"
    LEAVE_ONE_GROUP_OUT = "leave_one_group_out"


@dataclass(frozen=True)
class OverlapBlocks:
    """R14 overlap blocks: groups that share or touch a unit location, as connected components.
    Derived from the static table only (derive_overlap_blocks); no list is hand-set."""
    block_of_group: Mapping[str, int]                 # group -> block index (blocks sorted by first member)
    members: Tuple[Tuple[str, ...], ...]              # each block's groups, sorted; most blocks hold one group
    linked_pairs: Tuple[Tuple[str, str, int], ...]    # (group, group, units of the smaller group linked)
    link_rule: str                                    # 'grid_indices' or 'spacing'; recorded with its inputs


# ------------------------------------------------------------------------------------------------
# The split file and the groups (plan 1.2; G-SPLIT, G-SUPPORT)
# ------------------------------------------------------------------------------------------------
# Provenance: plan 1.2 split.yaml (LORO: exclusions, seen_during_design, continuity_groups; every listed
# group exists in the data; a reported group may not be excluded). Supersedes split.split_differences
# (D38, D39).
def loro_split_differences(split: LoroSplitSets, data_groups: Tuple[str, ...]) -> LoroSplitDiff:
    """Every difference between split.yaml and the data's groups, under LORO.

    Rule: G-SPLIT, plan 1.2.  Needed: Tue 29 Sep (M1).

    Contract (plan 1.2, 5 G-SPLIT):
        There is no donor or test list, so there is no disjointness to check. Every group that
        split.yaml names (excluded, seen_during_design, continuity_groups) must exist in the data,
        and a seen_during_design or continuity group may not also be excluded. Counts are printed
        but never used as the check. check_g_split_loro turns a non-empty difference into a BLOCK.
    Inputs:
        split: the LORO split sets.
        data_groups: groups present in the target table.
    Returns:
        LoroSplitDiff (all empty when consistent).
    Refuses:
        - nothing (pure; the validator decides).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 1.2 ("The groups are the data's groups minus the exclusions"); owner ruling D (every
# group gets its own specialist trees and every group is tested).
def groups_under_loro(split: LoroSplitSets, data_groups: Tuple[str, ...]) -> Tuple[str, ...]:
    """The groups: the data's groups minus the exclusions, sorted by name. Every one is trained and
    tested.

    Rule: plan 1.2, R18, R19.  Needed: Tue 29 Sep (M1).

    Contract (plan 1.2; owner ruling D):
        Sorted in split.as_sorted_set's order (D37). Each returned group trains its own trees on its
        bank units (R19) and is scored on its scored units (R18). G, the number of groups in the
        R18 budget rule, is the length of the result.
    Inputs:
        split: the LORO split sets.
        data_groups: groups present in the target table.
    Returns:
        the groups, sorted.
    Refuses:
        - an exclusion that names a group not in the data (check_g_split_loro reports it first).
        - an empty result.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-SPLIT (LORO row); NDVI 25-vs-44 (Part 426); pm25_split.check() never called
# (pm25_split.py:192-197); a hand-picked test set (CLAIMS_LEDGER.md PM-10). Supersedes
# validators.check_g_split.
def check_g_split_loro(split: LoroSplitSets, data_groups: Tuple[str, ...]) -> GuardResult:
    """G-SPLIT (quick) under LORO: split.yaml holds only exclusions, seen_during_design and
    continuity_groups, and every group it names is consistent with the data.

    Rule: G-SPLIT.  Needed: Tue 29 Sep (quick checks).

    Contract (plan 5 G-SPLIT, 1.2):
        Uses split.as_sorted_set and loro_split_differences. A donor_groups or test_groups key never
        reaches this check: the package schema refuses it first (G-NOKNOB, "derived: every group is
        trained and tested"). The output re-check (scored units = derived scored lists, inside the
        bank lists) is check_scored_units_loro.
    Inputs:
        split: split.yaml as LORO sets.
        data_groups: groups in the target table.
    Returns:
        GuardResult.
    Refuses (BLOCK):
        - duplicates, a listed group absent from the data, or a reported group that is also excluded.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-SUPPORT (LORO row); C15; D44 (thresholds signed as "3 test or 2 donor refuse; 14
# test or 5 donor flag"), restated for LORO; D45 unchanged. Supersedes validators.check_g_support.
def check_g_support_loro(donor: DonorLabels, census_complete: bool, is_events: bool,
                         n_zero_observations: int, n_groups: int, any_all_zero_unit: bool) -> GuardResult:
    """G-SUPPORT under LORO: enough support to learn and to judge, counted in groups.

    Rule: G-SUPPORT, C15.  Needed: Tue 29 Sep (quick checks).

    Contract (plan 5 G-SUPPORT):
        As validators.check_g_support, with one group count. Every group is tested and each router
        sees the trees of G-1 groups, so the signed "fewer than 3 test or 2 donor groups" reads
        "fewer than 3 groups" (refuse), and "fewer than 14 test or 5 donor groups" reads "fewer than
        14 groups" (flag, report only). The five-donor flag belonged to the old donor folds and goes.
        Donor y has at least 2 distinct values; the census and presence-only rules are unchanged
        (D45: label counts at or before the donor train end).
    Inputs:
        donor: plan-time donor labels at the nowcast fit cut (every group's bank units).
        census_complete: io_science.build_dense_grid succeeded without holes.
        is_events: True for events.
        n_zero_observations: zero labels in the event table.
        n_groups: G (groups_under_loro).
        any_all_zero_unit: whether any unit's labels are all zero.
    Returns:
        GuardResult.
    Refuses (BLOCK):
        - fewer than 2 distinct donor values; an incomplete census; fewer than 3 groups; a
          presence-only table.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# ------------------------------------------------------------------------------------------------
# Two unit lists per group (R18)
# ------------------------------------------------------------------------------------------------
# Provenance: plan 2.3 R18 (1) bank units = the pre-LORO count; C7; pm25_adaptation.py:122-123 (100);
# region budget adaptation.py:1149-1150, 1213. Supersedes derive_rules.derive_r18_unit_count together
# with derive_r18_scored_count (its event floor, D13 and D14, moves to the scored count; D15 unchanged).
# Package values: PM2.5, fire, NDVI 100; defo 4,285 (4 groups under it use all their cells).
def derive_r18_bank_count(kind: RouterKind, season: SeasonKeySpec, median_inner_fit_rows_per_unit: float,
                          available_units: Mapping[str, int], pooled_fit_rows_per_group: Mapping[str, int],
                          n_non_tree_router_columns: int) -> Derived[Tuple[int, Mapping[str, int]]]:
    """Bank units per group: the units whose rows train the group's trees, fit its region router and
    pool its fallback router. The pre-LORO count, unchanged.

    Rule: R18 (1), C7.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.3 R18, C7; LORO companion rule 1, decision L2):
        Per-unit: 100; at steps finer than a month min(100, ceil(1,200 / steps per year)). Region:
        floor(60,000 / the median valid inner-fit rows per unit). Neighbour: every unit, and the
        rule value is the median available units per group. The same rule value applies to every
        group, capped at the group's available units. A capped group is flagged 'thin' when its
        pooled fit rows fall below 20 per NON-tree router column (D15). The event floor is not here;
        it applies to the scored count (derive_r18_scored_count).
    Inputs:
        kind: R12 outcome.
        season: R2 (steps per year).
        median_inner_fit_rows_per_unit: median valid inner-fit rows per candidate unit, over every
            group (region).
        available_units: {group: candidate units} (split.candidate_units), every group.
        pooled_fit_rows_per_group: {group: pooled fit rows at the capped count} (thin flag).
        n_non_tree_router_columns: router columns other than the tree block (thin flag, D15).
    Returns:
        Derived[(rule value n, {group: bank count})]; flags carry 'thin:<group>' and 'capped:<group>'.
    Refuses:
        - an empty group map; a median of 0 rows (region).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: owner ruling D asks for "the same TOTAL as the old hard split, spread over all groups";
# plan 2.3 R18 (2); C16 (K = 20 is the plan's working value, NOT signed: PM2.5's old 20 test groups;
# geometric mean 19.5 of the old counts 20, 10, 16.45 capped, 44); D13 (event-floor formula) and D14
# (event rate from every labelled donor row at or before the train end). K = 20 gives PM2.5 15, fire 50,
# defo 2,040, NDVI 15 per group: totals 1,905 / 2,000 / 85,680 / 1,995 against the old 2,000 / 1,000 /
# 70,487 / 4,400. So K = 20 does NOT meet "same total": it is about the old total on PM2.5 only (x0.95);
# fire x2, NDVI x0.45, defo x1.22. No single K can meet it on all four (plan 9.1 item 6a).
def derive_r18_scored_count(kind: RouterKind, rule_value: int, bank_by_group: Mapping[str, int],
                            available_units: Mapping[str, int], k_group_equivalents: int,
                            donor_all: DonorLabels, test_window_rows_per_unit: int) -> Derived[UnitCounts]:
    """Scored units per group: max(10, floor(K x n / G)), capped at the group's bank units, with the
    event floor on top.

    Rule: R18 (2), C16.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.3 R18, C16; owner ruling D):
        G = the number of groups (the keys of bank_by_group). The scored count is
        max(10, floor(K x n / G)), rounded DOWN so the budget is never exceeded, then capped at the
        group's bank count. The 10 is flagged 'minimum' where it binds. Then the event floor (it
        exists for detection): the count is raised if needed so each group expects at least 10
        test-window events at the donor event rate, count >= ceil(10 / (test_window_rows_per_unit x
        rate)) (D13); the rate is the share of every group's labelled donor rows at or before the
        train end that lie strictly above their 90th percentile (D14). The floor is skipped, and the
        reason recorded, when the rate is 0. If the floor lifts a scored count above its bank count,
        the bank count is raised to match, capped at the available units. The scored units are later
        taken as an evenly spaced subset of the bank units (pick_unit_lists).
    Inputs:
        kind: R12 outcome (recorded; the rule itself is the same for every kind).
        rule_value: n from derive_r18_bank_count.
        bank_by_group: {group: bank count} from derive_r18_bank_count.
        available_units: {group: candidate units}.
        k_group_equivalents: K, the engine constant C16 (never from a package or a flag).
        donor_all: plan-time donor labels over every group's candidate units at the nowcast fit cut
            (scope 'all_donor_units'), for the event rate.
        test_window_rows_per_unit: census rows per unit in the test window.
    Returns:
        Derived[UnitCounts]; inputs record K, n, G, the event rate and donor_all's row-key hash; flags
        carry 'minimum:<group>', 'event_floor:<group>' and any skipped-floor reason.
    Refuses:
        - K < 1; n < 1; donor_all with another scope or no row.
    OWNER DECISION (L1), no default proposed; the owner chooses (plan 9.1 item 6a):
        (a) one engine constant K = 20: generic, but it departs from "same total" on fire (x2), NDVI
            (x0.45) and defo (x1.22); the old totals are printed beside.
        (b) each package's own old total, K_p = the number of its continuity groups: PM2.5 15 per
            group, fire 25, defo 1,734, NDVI 33 (totals 1,905 / 1,000 / 72,828 / 4,389). A reporting
            list then sets a count, which breaks "continuity is reporting only" and plug and predict,
            and a new problem still needs K as the fallback. This signature would gain a
            continuity_count argument.
        (c) one larger K = 44 (NDVI's old count), so every package gets about its old total or more
            (NDVI 4,389 against 4,400; PM2.5 34 per group, fire 100,
            defo every bank unit, NDVI 33); PM2.5, defo and NDVI tables no longer fit on the disk.
        Two other rules were measured and are not offered: a total of T units per package, and a total
        of test rows per package.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.2 R14 (positions floor(i x (N-1)/(m-1))); adaptation.py:1149-1150 (the shipped
# np.linspace pick); region_cap_units' accepted m = 1 default (position 0).
def evenly_spaced_subset(sorted_units: Tuple[str, ...], count: int) -> Tuple[str, ...]:
    """The scored units of a group: an evenly spaced subset of its sorted bank units.

    Rule: R18 (2), R14's formula, G-NODRAW.  Needed: Tue 29 Sep (M1).

    Contract (plan 2.3 R18, 2.2 R14):
        Over the N sorted units keep positions floor(i x (N-1)/(m-1)), i = 0..m-1, with m = count;
        all units when count >= N; position 0 when m = 1. The subset spans the whole sorted list,
        first and last unit included. No seed, no draw.
    Inputs:
        sorted_units: the group's bank units, sorted.
        count: the scored count (derive_r18_scored_count).
    Returns:
        the kept units, in sorted order.
    Refuses:
        - count < 1; unsorted or duplicated units.
    OWNER DECISION (L2): this formula rather than stride_pick's s = N // m, which starts at the
        first unit and never reaches the tail of the sorted list.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.3 R18; plan 4.1 step 5 (pick both lists, hash both); pm25_architecture.py:101-108
# (stride over sorted ids, D40). Supersedes split.pick_units.
def pick_unit_lists(groups: Tuple[str, ...], candidates_by_group: Mapping[str, Tuple[str, ...]],
                    counts: UnitCounts) -> UnitLists:
    """Pick every group's bank units by stride and its scored units as an evenly spaced subset of them.

    Rule: R18.  Needed: Tue 29 Sep (M1).

    Contract (plan 2.3 R18, 4.1 step 5):
        For every group: bank = split.stride_pick(candidates, bank count) (D40); scored =
        evenly_spaced_subset(bank, scored count). The scored list is always inside the bank list
        (asserted). Both lists are hashed into the manifest (hashing is boilerplate).
    Inputs:
        groups: groups_under_loro.
        candidates_by_group: {group: candidate ids} (split.candidate_units).
        counts: derive_r18_scored_count's UnitCounts.
    Returns:
        UnitLists.
    Refuses:
        - a group without candidates or without counts; a count above its candidates.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-SPLIT (outputs: per group, the scored units = the derived scored list and lie
# inside the bank list); 7.1 (the headline table builder re-checks). Supersedes split.check_scored_units,
# which had no bank lists to check against.
def check_scored_units_loro(scored_in_outputs: Mapping[str, Tuple[str, ...]], lists: UnitLists) -> None:
    """The units in saved predictions must equal the derived scored lists, per group, and lie inside the
    group's bank list.

    Rule: G-SPLIT (outputs).  Needed: Sun 4 Oct (scoring; every row saved).

    Contract (plan 5 G-SPLIT, 7.1):
        For EVERY group (LORO): the set of units in test_preds equals lists.scored[group], and
        lists.scored[group] is a subset of lists.bank[group]. Compared as sets; counts are printed but
        never the check. The headline table builder re-runs this.
    Inputs:
        scored_in_outputs: {group: unit ids found in test_preds}.
        lists: the R18 picks (pick_unit_lists).
    Returns:
        None.
    Refuses:
        - a group missing from the outputs or from the lists; any set difference, naming the units; a
          scored unit outside its bank list.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# ------------------------------------------------------------------------------------------------
# Overlap blocks (R14; G-DISJOINT, C17, R34)
# ------------------------------------------------------------------------------------------------
# Provenance: LORO review, 2026-09-28 late night (measured read-only on D:/monthly_panel, NDVI's 133
# groups, 2015 cells): 8 linked pairs, 125 blocks, no pair that only touches. brigalow_belt shares 8,251
# cells with australian_mulga (48.8% / 16.5%); california_central_valley / california_chaparral 1,032;
# thar_desert / indian_acacia_babool 60; pampas / uruguay 42; cape_floristic_region / karoo 32;
# angola_zambia_fire_belt / miombo_woodland_zambia 29; andes_puna / bolivia_beni_savanna 1;
# north_china_plain / ordos_plateau 1. By name, all 8 pairs are among PM2.5's groups, 1 among fire's and
# 2 among defo's; each package is re-measured on its own grid at M1. Structural law "in-bag fits learn
# nothing": a group's trees answer a unit at a location they trained on in-bag, whatever its group label.
def derive_overlap_blocks(unit_group: np.ndarray, unit_lat: np.ndarray, unit_lon: np.ndarray,
                          grid_ix: Optional[np.ndarray], grid_iy: Optional[np.ndarray]) -> Derived[OverlapBlocks]:
    """Overlap blocks: groups linked when a unit of one lies at the same grid position as, or in the
    8-neighbourhood of, a unit of the other; blocks are the connected components.

    Rule: R14 (overlap blocks), G-DISJOINT, C17, R34.  Needed: Tue 29 Sep (derive v1; LORO companion
    rule 4, decision L2).

    Contract (plan 2.2 R14):
        Units are every candidate unit of every group, from the static table (not the picks, so the
        blocks do not move with the unit counts). Link rule, no hand-set number:
        - 'grid_indices' when the static table has grid_ix and grid_iy: two units are linked when both
          indices differ by at most 1 (same cell or one of its 8 neighbours);
        - 'spacing' otherwise: two units are linked when their great-circle distance is at most
          sqrt(2) x the larger of the two groups' median nearest-unit spacing (the diagonal of the
          8-neighbourhood), each spacing computed from the group's own units.
        Two groups are linked when any pair of their units is linked. Blocks are the connected
        components, each sorted by name, and sorted by their first member. Every group is in exactly
        one block. A router drops the trees of every group in its block (router_tree_columns); rival
        folds keep a block together (rival_fold_of_group); the report-only blocked jackknife leaves one
        block out at a time (R34). plan prints the linked pairs with their unit counts.
    Inputs:
        unit_group, unit_lat, unit_lon: every candidate unit's group and representative point (EPSG:4326).
        grid_ix, grid_iy: integer grid indices, or None when the static table has none.
    Returns:
        Derived[OverlapBlocks]; inputs record the link rule, each group's spacing and the static table's
        hash; flags carry 'overlap:<group>+<group>:<units>' per linked pair.
    Refuses:
        - mismatched lengths; latitudes outside [-90, 90]; a group with one unit and no grid indices
          (no spacing can be computed; the fix is to add grid indices to the static table).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# ------------------------------------------------------------------------------------------------
# The router's own-block column exclusion (R14, R20; G-DISJOINT)
# ------------------------------------------------------------------------------------------------
# Provenance: owner ruling D ("a unit's router never sees its OWN group's trees; dropped as columns");
# plan 2.2 R14 (tree columns, every kind), 2.3 R20 (one table per kind, column mask); structural law
# "in-bag fits learn nothing" (a group's own trees answer its own bank units in-bag, and the scored units
# are among them). Router widths: PM2.5 12,600; fire 3,900; defo 4,100; NDVI 13,200, for a group alone in
# its overlap block (100 fewer per other group in the block).
def router_tree_columns(tree_group: Tuple[str, ...], router_groups: Tuple[str, ...]) -> np.ndarray:
    """The tree columns a router may use: every tree whose group is not one of the router's own
    groups, in bank order.

    Rule: R14, R20, G-DISJOINT.  Needed: Fri 2 Oct (per-unit router).

    Contract (plan 2.2 R14, 2.3 R20):
        router_groups is always a union of whole overlap blocks (derive_overlap_blocks). Per-unit and
        region routers, and the fallback region router, pass their group's block. The neighbour kind
        passes, by default, the scored row's block AND the block of every group present in its pool
        (plan R14: every pool row from group h was trained on by h's trees, about 39% of them in-bag);
        relaxing that default needs an owner signature. The fold-g pool on the neighbour decision
        surface uses the same rule as the test-pass pool. The same mask serves the plain, corrector
        and placebo tables, so one table per kind serves every group. The GLS error target (R25) and
        every FitContext tree service (own_block_masked_answers) exclude a row's block by the same rule.
    Inputs:
        tree_group: the group of each bank tree, in bank (column) order.
        router_groups: the groups whose trees this router may not use (whole blocks).
    Returns:
        int64 column indices, ascending.
    Refuses:
        - empty router_groups; router_groups that split a block; a router group with no tree in the
          bank (under LORO every group trains trees); an empty result.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-DISJOINT (LORO row: "a unit's router has no column from its own group", asserted
# on every router fit, the fallback region router included).
def assert_no_own_group_column(column_tree_group: np.ndarray, router_groups: Tuple[str, ...],
                               router_id: str) -> None:
    """Refuse a router fit that holds a tree column from one of its own groups.

    Rule: G-DISJOINT.  Needed: Fri 2 Oct (per-unit router).

    Contract (plan 5 G-DISJOINT):
        Called on every router fit, per-unit, region, fallback and neighbour alike, with the tree
        group of each column actually in its design matrix, and on every answer a FitContext tree
        service hands out (own_block_masked_answers). Any column whose group is in router_groups is
        refused, naming the router and the columns. The check is on physical keys, not only on labels:
        router_groups must be the whole block(s) of derive_overlap_blocks, and at run start G-DISJOINT
        recomputes the blocks from the static table and refuses a mismatch with derived.json. The count
        of checked fits goes to guard_report.json. A planted fault (a service answer that keeps an
        own-block column) must be refused.
    Inputs:
        column_tree_group: tree group of each tree column in the fitted design, in column order.
        router_groups: the router's own groups: its overlap block (router_tree_columns' input).
        router_id: the unit or group the router serves, for the message.
    Returns:
        None.
    Refuses:
        - any own-block column.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-DISJOINT (each group's trees see only that group's bank units at or before the
# cut; a manifest per group, the neighbour kind's inner-cut bank too); CLAIMS_LEDGER.md:523 (banks
# without a year filter); F15. Supersedes split.assert_bank_disjoint.
def assert_group_manifests(group_manifests: Mapping[str, BankManifest], unit_lists: UnitLists,
                           cut: int) -> None:
    """Refuse a bank in which any group's trees saw another group, units outside its bank list, or a
    label after the cut.

    Rule: G-DISJOINT, R19.  Needed: Wed 30 Sep (bank).

    Contract (plan 5 G-DISJOINT, 2.3 R19):
        Every group has one manifest. Its groups are exactly that group; its units are that group's
        bank units (compared by hash; hashing is boilerplate); its max label time is at or before
        the cut. Applies to the main bank at every lead cut and to the neighbour kind's inner-cut
        bank (R13).
    Inputs:
        group_manifests: {group: the manifest of that group's trees}.
        unit_lists: the R18 picks.
        cut: the bank's cut.
    Returns:
        None.
    Refuses:
        - a missing group, a manifest naming another group, other units, or a label after the cut.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 1.6 (Type-3 services ctx.fit_bank and ctx.donor_fold_predict); LORO review 2026-09-28
# late night: fit_bank now fits every group's trees on its own bank units, so a plug-in holding a whole
# Bank would answer a donor row, or a scored unit, with its own group's trees in-bag. D98's open return
# type is kept.
def own_block_masked_answers(answers: TreeAnswerStore, row_positions: np.ndarray, row_group: np.ndarray,
                             tree_group: Tuple[str, ...], blocks: OverlapBlocks) -> np.ndarray:
    """The one gateway through which every FitContext tree service (fit_bank answers,
    donor_fold_predict) hands tree answers to a Type-3 plug-in: each row's own block's trees dropped.

    Rule: plan 1.6, R14, G-DISJOINT, G-FITCUT.  Needed: M4 (Type-3 slot).

    Contract (plan 1.6):
        For each row, the answer is the mean over the trees whose group is NOT in the row's overlap
        block (router_tree_columns(tree_group, block of the row's group)), on donor rows and scored
        rows alike. A plug-in never receives the raw Bank or per-tree access; ctx.fit_bank(transform)
        returns a service that answers through this function. assert_no_own_group_column runs on every
        call, and a planted fault checks it. If the owner rules (D98) that a plug-in needs per-tree
        answers, they come as the masked column block, never the raw bank.
    Inputs:
        answers: the tree-answer store of the service's bank (the main bank, or the fit_bank bank on a
            declared transform).
        row_positions: rows to answer.
        row_group: each row's group.
        tree_group: each tree's group, in column order.
        blocks: derive_overlap_blocks' result.
    Returns:
        float64 answer per row.
    Refuses:
        - a row group with no block; mismatched lengths; a row whose block holds every group.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# ------------------------------------------------------------------------------------------------
# Routers with fit and scored units decoupled (R12, R14)
# ------------------------------------------------------------------------------------------------
# Provenance: route_kinds.route_per_unit (pm25_adaptation.py:360-444); plan 2.2 R12 (the fallback region
# router pools the group's BANK units, LORO companion rule 3); R14 (own-block columns dropped).
# Supersedes route_kinds.route_per_unit.
def route_per_unit_loro(ctx: FitContext, scored_units: Tuple[str, ...],
                        bank_units_by_group: Mapping[str, Tuple[str, ...]], link: Link, c: Optional[float],
                        ub: Optional[float], normals: Mapping[str, NormalTable], design: RouterDesign,
                        answers: TreeAnswerStore, tree_columns_by_group: Mapping[str, np.ndarray],
                        score_row_positions: np.ndarray, weights: Optional[np.ndarray]) -> RouteOutput:
    """Per-unit router under LORO: one ridge per scored unit on its own history, with its own block's
    trees dropped; short-history units go to their group's region router pooled over bank units.

    Rule: R12, R14-R16, R23, G-FITCUT, G-DISJOINT.  Needed: Fri 2 Oct (per-unit router).

    Contract (plan 2.2 R12-R16, 2.3 R20, 2.4 R23, 4.5 speedup 3):
        As route_kinds.route_per_unit, with two changes. (1) Each unit's tree block is the store's
        answers at tree_columns_by_group[the unit's group] (router_tree_columns over the group's
        overlap block), and every fit calls assert_no_own_group_column. (2) A scored unit with fewer
        than 24 valid fit rows uses route_region_loro with fit_units = its group's BANK units (not the
        group's scored units) and the level from search_fallback_level. The tree-answer tables hold
        the rows at or before the cut of every bank unit of such a group (R20; plan lists them), so
        the fallback can be fitted. Units are solved 8 at once with BLAS at 1 thread (boilerplate;
        byte-identical).
    Inputs:
        ctx: the FitContext of this cut.
        scored_units: the scored units served here.
        bank_units_by_group: {group: bank units} (the fallback router's fit units).
        link, c, ub: the arm's link and its constants at this cut.
        normals: {unit id: NormalTable in this link at this cut}, for every scored and bank unit used.
        design: R14 outcome.
        answers: the tree-answer store (plain or corrector table, by the arm).
        tree_columns_by_group: {group: router_tree_columns(tree_group, the group's overlap block)}.
        score_row_positions: rows to predict (decision surface or test rows of scored units).
        weights: GLS weights on fit rows, or None.
    Returns:
        RouteOutput.
    Refuses:
        - as route_kinds.route_per_unit; a score row outside scored_units; an own-block column.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: route_kinds.route_region (defo_softgate.py:105-124; adaptation.py:1149-1150); plan 2.2 R14
# (fit units = the group's bank units under the 60,000-row whole-unit cap, decoupled from the scored
# units, LORO companion rule 2); D81 unchanged. Defo: 4,285 bank units, about 3,529 kept at the test pass,
# 2,040 scored. Supersedes route_kinds.route_region.
def route_region_loro(ctx: FitContext, group: str, fit_units: Tuple[str, ...], scored_units: Tuple[str, ...],
                      link: Link, c: Optional[float], ub: Optional[float], normals: Mapping[str, NormalTable],
                      design: RouterDesign, answers: TreeAnswerStore, tree_columns: np.ndarray,
                      score_row_positions: np.ndarray, weights: Optional[np.ndarray]) -> RouteOutput:
    """Region router under LORO: one pooled ridge per group, fitted on its capped BANK units, scoring
    its scored units, with its own block's trees dropped.

    Rule: R12, R14-R16, U-1, G-DISJOINT.  Needed: Tue 6 Oct (region router).

    Contract (plan 2.2 R14-R16):
        Fit rows = ctx.router_rows(route_kinds.region_cap_units(fit_units, ...)) at the cut: the
        60,000-row whole-unit cap over the bank units, decoupled from the scored units. Columns:
        intercept, the unit's link-matched normal (unpenalised, D81), the trees at tree_columns
        (trace-normalised ridge). Every fit calls assert_no_own_group_column. Only rows of
        scored_units are scored. Trees-off = the normal (asserted). BLAS stays at 4 threads (owner
        ruling C). Sharing one group's tree-block Gram across its links (L4) would be a solver change
        in route/solve.py, boilerplate gated by byte identity: only the tree block's Gram is shared;
        the border with the normal column, which changes with the link, is recomputed per link. It
        does not change this contract.
    Inputs:
        ctx: FitContext of this cut.
        group: the group.
        fit_units: the group's bank units (for the fallback router of a per-unit package, also its
            bank units).
        scored_units: the group's scored units (a subset of fit_units).
        link, c, ub, normals, design, answers, score_row_positions, weights: as route_per_unit_loro
            (normals cover every fit and scored unit).
        tree_columns: router_tree_columns(tree_group, the group's overlap block).
    Returns:
        RouteOutput.
    Refuses:
        - a scored unit that is not in fit_units; a score row outside scored_units; an own-block
          column; as route_kinds.route_region.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# ------------------------------------------------------------------------------------------------
# Reporting groups (R34, R35)
# ------------------------------------------------------------------------------------------------
# Provenance: owner ruling D ("free continuity row: the old hard-split test groups are also reported
# alone, from the same run"); plan R34, R35, Q49 (seen_during_design row). Continuity groups: PM2.5 20,
# fire 10, defo 17, NDVI 44.
def report_groupings(groups: Tuple[str, ...], split: LoroSplitSets) -> Mapping[str, Tuple[str, ...]]:
    """The group sets every score table, jackknife and verdict is reported on.

    Rule: R34, R35, Q49.  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.5 R34, R35):
        'all' = every group (the headline, the jackknife and the band). 'without_seen_during_design'
        = all minus seen_during_design (only when that list is non-empty). 'continuity' = the
        continuity groups (only when that list is non-empty, and only if the owner keeps the list in
        the package, decision L7; otherwise treeroute_report computes that row from saved rows). The
        same metrics functions run on each set; the band is derived on 'all' only and judges every set
        (R35). The continuity row is labelled 'continuity, not a replication'. On 'all', the
        report-only blocked jackknife also runs with overlap blocks as the leave-out unit (R34).
        Reporting only: no set changes a fit, a pick or a decision.
    Inputs:
        groups: groups_under_loro.
        split: the LORO split sets.
    Returns:
        {grouping name: sorted groups}.
    Refuses:
        - a seen_during_design or continuity group not in groups.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan Section 10 (spatial neighbours always among the donors: report nearest-donor
# distances); CLAIMS_LEDGER.md PM-10 and :729 (the old split's median 777 km centre to centre, and the
# coral 500 km ablation, Part 533); route_kinds.neighbour_pool's accepted great-circle distance. Earth
# radius constant as in the neighbour pool source (adaptation.py:1620-1640).
def nearest_other_group_distance(scored_lat: np.ndarray, scored_lon: np.ndarray, scored_group: np.ndarray,
                                 bank_lat: np.ndarray, bank_lon: np.ndarray, bank_group: np.ndarray) -> np.ndarray:
    """For each scored unit, the great-circle distance to the nearest bank unit of ANOTHER group.

    Rule: R34 (report only).  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.5 R34, Section 10):
        Representative points from the static table (cell centre or polygon centroid), great-circle
        (haversine) distance in km, as route_kinds.neighbour_pool. Printed per group (median and
        minimum) and used for scores by distance band (distance_band_edges). A distance of 0 km, or a
        nearest unit that belongs to the scored unit's own overlap block, is FLAGGED (not only
        printed) as 'overlap:<group>', pointing to derive_overlap_blocks; those trees are dropped from
        the router, so the distance to the nearest group OUTSIDE the block is printed beside. Never a
        selector, never an input.
    Inputs:
        scored_lat, scored_lon, scored_group: scored units' points and groups.
        bank_lat, bank_lon, bank_group: every group's bank units' points and groups.
    Returns:
        float64 km per scored unit.
    Refuses:
        - a scored group with no other group's bank unit; mismatched lengths; latitudes outside
          [-90, 90].
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan Section 10 and R34 (scores by nearest-donor distance band); LORO review 2026-09-28 late
# night (the band edges had no written rule, so a hand-set number would have entered the report).
def distance_band_edges(distances_km: np.ndarray) -> Derived[Tuple[float, float, float]]:
    """The edges of the report's distance bands: the quartiles of the per-unit nearest-other-block
    distances over every scored unit.

    Rule: R34 (report only).  Needed: Sun 4 Oct (scoring).

    Contract (plan 2.5 R34, Section 10):
        Edges = the 25th, 50th and 75th percentiles of distances_km (linear interpolation), so four
        bands with about a quarter of the scored units each. No hand-set number. The same edges serve
        the report's decision-by-distance-band rows (A7 disclosure, 7.2). Report only: never a
        selector, never an input.
    Inputs:
        distances_km: nearest_other_group_distance to the nearest group outside the unit's block.
    Returns:
        Derived[(q25, q50, q75)]; inputs record the unit count and the row-key hash.
    Refuses:
        - an empty array; a non-finite or negative distance.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# ------------------------------------------------------------------------------------------------
# The neighbour surface (R13) and the smoke plan (R21)
# ------------------------------------------------------------------------------------------------
# Provenance: plan 2.1 R13 (LORO: neighbour folds become leave-one-group-out from one bank cut at the
# inner-fit end; fold g drops g's trees); C8. Supersedes derive_rules.derive_r13_decision_surface and, for
# the neighbour kind, split.make_donor_folds.
def derive_r13_surface_loro(kind: RouterKind,
                            groups: Tuple[str, ...]) -> Derived[Tuple[LoroSurfaceKind, Tuple[Tuple[str, ...], ...]]]:
    """Decision surface under LORO: the inner window (per-unit, region) or leave-one-group-out folds
    (neighbour).

    Rule: R13, C8.  Needed: Tue 29 Sep (derive v1); folds used only in M8 (neighbour track).

    Contract (plan 2.1 R13, C8):
        Per-unit and region: the inner window, unchanged; their routers drop their own block's trees
        there too. Neighbour: one fold per group, in sorted order. One extra bank cut at the
        inner-fit end serves every fold; fold g drops the trees of group g's overlap block, and, by
        the pool default, of every group present in each row's pool, with their correctors and
        placebo correctors (router_tree_columns), so no bank is refitted per fold. The fold-g pool
        follows the same rule as the test-pass pool (neighbour_pool_loro). Fold g's c and GLS model
        are built from the rows outside g's block at or before the inner-fit end; its scored rows are
        group g's rows in the inner score years.
    Inputs:
        kind: R12 outcome.
        groups: groups_under_loro.
    Returns:
        Derived[(surface kind, one single-group tuple per fold)] (empty fold tuple for the inner
        window).
    Refuses:
        - neighbour kind with fewer than 3 groups (G-SUPPORT refuses earlier).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: route_kinds.neighbour_pool (adaptation.py:1620-1640; C11; flag 13); plan 2.2 R14 (LORO: every
# group may lend pool rows at or before the cut; no test_groups argument, because no group is held back).
# Supersedes route_kinds.neighbour_pool. M8 / optional track.
def neighbour_pool_loro(row_unit: str, row_group: str, row_lat: float, row_lon: float, row_features: np.ndarray,
                        candidates: RouterRows, candidate_lat: np.ndarray, candidate_lon: np.ndarray,
                        candidate_features: np.ndarray, candidate_group: np.ndarray,
                        blocks: OverlapBlocks) -> Tuple[Optional[np.ndarray], Tuple[str, ...]]:
    """The strict pool of one neighbour-kind row under LORO, and the groups whose trees its router must
    drop.

    Rule: R14 (neighbour), C11.  Needed: M8 (neighbour track).

    Contract (plan 2.2 R14, C11, 3.3 flag 13):
        Eligible rows: labelled, at or before the lead's cut, from ANY group (every group is a donor to
        the others), never the row itself. Take the 150 nearest by distance, then the 50 nearest of
        those in standardised tree-feature space. Under 12 eligible rows the caller falls back to the
        donor-row median (counted). The second return value is the union of the row's own block and
        the blocks of every group present in the pool: the default drop set for router_tree_columns
        (fail safe: every pool row from group h was trained on by h's trees). Relaxing the default to
        the row's own block only needs an owner signature. The same function serves the fold-g pools
        of the decision surface and the test pass.
    Inputs:
        row_*: the target row's unit, group, location and standardised features.
        candidates: labelled rows at or before the cut (FitContext.router_rows over the pool units).
        candidate_*: their locations, standardised features and groups.
        blocks: derive_overlap_blocks' result.
    Returns:
        (pool row positions, at most 50, or None; the groups to drop, sorted, whole blocks).
    Refuses:
        - (assert) any pool row after the cut, or the row itself.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: route_kinds.route_neighbour (adaptation.py:1434; R14, R16, R23); plan 2.2 R14 (LORO: the drop
# set per row from neighbour_pool_loro). Supersedes route_kinds.route_neighbour, whose signature had no
# tree-column argument. M8 / optional track.
def route_neighbour_loro(ctx: FitContext, link: Link, c: Optional[float], ub: Optional[float],
                         design: RouterDesign, answers: TreeAnswerStore, tree_group: Tuple[str, ...],
                         blocks: OverlapBlocks, score_row_positions: np.ndarray, donor_median: float,
                         weights: Optional[np.ndarray]) -> RouteOutput:
    """Neighbour router under LORO: per row, a ridge on its strict pool (intercept, context, trees) at
    every grid point, plus trees-off, with the row's drop set's trees removed.

    Rule: R12, R14, R16, R23, G-DISJOINT.  Needed: M8 (neighbour track).

    Contract (plan 2.2 R14, R16, 2.4 R23):
        As route_kinds.route_neighbour. Per row, the tree block is
        router_tree_columns(tree_group, drop set from neighbour_pool_loro), and every fit calls
        assert_no_own_group_column with that drop set. Pool y goes to link space with the GIVEN c and
        ub. Rows whose pool is None take the donor-row median (counted). Rows are solved 8 at once
        (boilerplate).
    Inputs:
        ctx: FitContext (fold context on the decision surface).
        link, c, ub: the arm's link and its constants at this cut (per fold on the surface).
        design: R14 outcome.
        answers: tree-answer store.
        tree_group: each tree's group, in column order.
        blocks: derive_overlap_blocks' result.
        score_row_positions: rows to predict.
        donor_median: metrics.baseline_donor_median at this cut.
        weights: GLS weights, or None.
    Returns:
        RouteOutput.
    Refuses:
        - as neighbour_pool_loro; an own-block or pool-block column.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.3 R21 (40 units, 12 trees; pm25_adaptation.py:122-126); LORO: the first 4 groups
# (the old 2 donor + 2 test), all trained and tested. Supersedes derive_rules.derive_r21_smoke_plan.
def derive_r21_smoke_plan_loro(groups: Tuple[str, ...]) -> Derived[Mapping[str, Any]]:
    """The fixed smoke plan under LORO: the first 4 groups in sorted order, 40 units per group (all
    scored), 12 trees per group.

    Rule: R21.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.3 R21):
        Engine constants, never a flag. Every smoke group is trained and tested, and each router
        sees the trees of the other smoke groups outside its overlap block. All groups when there are
        fewer than 4. Plumbing only: smoke deltas carry no sign information.
    Inputs:
        groups: groups_under_loro.
    Returns:
        Derived[{'groups', 'units_per_group', 'scored_per_group', 'trees_per_group'}].
    Refuses:
        - fewer than 3 groups.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# ------------------------------------------------------------------------------------------------
# Donor-only rivals: region folds (plan 4.6; M8)
# ------------------------------------------------------------------------------------------------
# Provenance: owner ruling D ("donor-only rivals are trained on region folds (10), and each group is
# scored by the fold model that never saw it"); plan 4.6, C17 (round-robin over sorted overlap blocks, as
# C8 did over names before LORO; a block stays in one fold, so a fold model never saw a group that shares
# locations with the group it scores).
def rival_fold_of_group(blocks: OverlapBlocks, n_folds: int) -> Mapping[str, int]:
    """Each group's rival fold: round-robin over the overlap blocks, sorted by their first group name;
    every group takes its block's fold.

    Rule: plan 4.6, C17, G-NODRAW.  Needed: M8 (rival-board command).

    Contract (plan 4.6, C17):
        The block at sorted position j goes to fold j mod n_folds, and every group of that block with
        it. Fold f's donor-only rival model is fitted on every group NOT in fold f; the groups of fold
        f are scored only by that model. Where every block holds one group, this is round-robin over
        the sorted names.
    Inputs:
        blocks: derive_overlap_blocks' result (its members cover groups_under_loro).
        n_folds: C17 (10), an engine constant.
    Returns:
        {group: fold index}.
    Refuses:
        - n_folds < 2 or greater than the number of blocks.
    OWNER DECISION (L3): round-robin over sorted blocks (the ruling fixes 10 folds, not the assignment).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 4.6 (fold f's model is fitted on the other folds' groups, bank units at or before the
# cut).
def rival_fold_training_groups(fold_of_group: Mapping[str, int], fold: int) -> Tuple[str, ...]:
    """The groups a fold's donor-only rival model is fitted on: every group outside the fold.

    Rule: plan 4.6, G-DISJOINT.  Needed: M8 (rival-board command).

    Contract (plan 4.6):
        Sorted groups whose fold differs from `fold`. The fitted rows are those groups' bank units'
        rows at or before the cut; the fold model's manifest records them.
    Inputs:
        fold_of_group: rival_fold_of_group's result.
        fold: the fold index.
    Returns:
        training groups, sorted.
    Refuses:
        - an unknown fold; an empty result.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: pm25_rivals.py:317-319 (the old board: holdout = donors[::4] in frozen order; trials fitted
# on the other donors up to the inner-fit end, scored on the holdout's inner-score years; the pick then
# refitted on all donors up to the train end, :422); plan 4.6 (moved to all groups, once, then refitted
# on each fold).
def rival_tuning_holdout(blocks: OverlapBlocks, every: int) -> Tuple[str, ...]:
    """The fixed hyperparameter holdout of the donor-only rivals: the groups of every `every`-th overlap
    block in sorted block order, starting at the first.

    Rule: plan 4.6, G-NODRAW.  Needed: M8 (rival-board command).

    Contract (plan 4.6):
        blocks.members[::every], flattened and sorted. Trials are fitted on the other groups' rows up
        to the inner-fit end and scored on the holdout groups' inner-score rows, once for the whole
        board; each of the fold models then refits the picked trial on its own training groups up to
        the train end. No test-window label is read. Disclosed: the tuning reads the pre-cut rows of
        groups that a fold model later "never saw", as the engine's own decision surface does. Quirk,
        harmless: block positions 0, 4, 8, ... taken mod 10 fall only in even folds.
    Inputs:
        blocks: derive_overlap_blocks' result.
        every: 4, as the old board.
    Returns:
        holdout groups, sorted.
    Refuses:
        - every < 2; an empty holdout.
    OWNER DECISION (L3): this tuning rule (the old board's rule over all blocks, run once), AND Board B
        (the per-unit MOS), which used to pick its rival trial jointly with the MOS by inner MAE. Under
        LORO the one tuning run fits each trial on about 3/4 of all groups, so a trial's z on a scored
        unit's fit rows is in-sample for most groups. Options: (a) Board B takes Board A's pick and its
        z comes only from the fold models (a disclosed change from the old board); (b) every trial runs
        on all 10 folds, so every z is out-of-fold (about 10x the tuning cost, roughly +15 h on PM2.5).
        No default; the owner chooses.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 4.6 and 5 G-DISJOINT (a donor-only prediction for a group comes only from the fold
# model that did not see it).
def assert_rival_source(prediction_group: np.ndarray, model_fold: np.ndarray,
                        fold_of_group: Mapping[str, int]) -> None:
    """Refuse any donor-only rival prediction, or Board B z value, that did not come from its group's
    own fold model.

    Rule: G-DISJOINT, plan 4.6.  Needed: M8 (rival-board command).

    Contract (plan 4.6, 5 G-DISJOINT):
        For every saved prediction row AND every z row the per-unit MOS (Board B) reads, on its fit
        rows and its test rows alike, the fold of the model that made it equals the fold of the row's
        group, which is the one model that never saw that group or its overlap block. Called once on
        the predictions and once on the z rows.
    Inputs:
        prediction_group: group of each saved prediction row (or z row).
        model_fold: fold index of the model that made each row.
        fold_of_group: rival_fold_of_group's result.
    Returns:
        None.
    Refuses:
        - any row whose model fold differs from its group's fold; mismatched lengths.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")
