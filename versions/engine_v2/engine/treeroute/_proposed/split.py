"""PROPOSED signatures: treeroute/split.py (plan 4.2). SCIENCE (CV splits): owner signatures, agent bodies.

Sorted sets, stride unit picks (R18), donor folds (R13), disjointness (G-DISJOINT) and set checks on
outputs (G-SPLIT). No draw anywhere: subsets by stride only (G-NODRAW).
"""
# Provenance for the module: pm25_split.py:55-189 (lists only); pm25_architecture.py:101-108.
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Tuple

import numpy as np

from .common import BankManifest, SplitSets, Step


@dataclass(frozen=True)
class SplitDiff:
    """Every set difference between the split and the data (printed by `split freeze`)."""
    overlap_donor_test: Tuple[str, ...]
    in_data_not_split: Tuple[str, ...]
    in_split_not_data: Tuple[str, ...]
    seen_not_test: Tuple[str, ...]


# Provenance: plan 1.2 split.yaml ("The engine sorts group names, so order carries no meaning"); 1.7
# (donor order door closed).
def as_sorted_set(names: Iterable[str], what: str) -> Tuple[str, ...]:
    """Turn a declared list into a set sorted by name.

    Rule: plan 1.2, 1.7, G-SPLIT.  Needed: Tue 29 Sep (M1).

    Contract (plan 1.2, 1.7):
        Order carries no meaning; seeds come from names (R19) and folds are round-robin over sorted
        names (R13).
    Inputs:
        names: the declared names.
        what: which list (donor_groups, test_groups, ...), for the message.
    Returns:
        names sorted, as a tuple.
    Refuses:
        - duplicates (a list with a repeat is not a set) or empty names.
    OWNER DECISION: sort order -- propose plain code-point order of the UTF-8 strings (what Python
        and numpy sort give), recorded in the manifest.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 1.2 split.yaml (donor and test disjoint; data groups equal split groups as sets;
# seen_during_design adds a report row without those groups, Q49).
def split_differences(split: SplitSets, data_groups: Tuple[str, ...]) -> SplitDiff:
    """Every difference between the split's sets and the data's groups.

    Rule: G-SPLIT.  Needed: Tue 29 Sep (M1).

    Contract (plan 1.2, 5 G-SPLIT):
        Donor and test groups must be disjoint, and the data's groups must equal the split's groups
        as sets. Counts are printed but never used as the check. validators.check_g_split turns a
        non-empty difference into a BLOCK.
    Inputs:
        split: the split sets.
        data_groups: groups present in the target table.
    Returns:
        SplitDiff (all empty when consistent).
    Refuses:
        - nothing (pure; the validator decides).
    OWNER DECISION: "the split's groups" -- propose donor + test + excluded, so an excluded group
        present in the data is not a difference.
    OWNER DECISION: seen_during_design -- propose it must be a subset of the test groups.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.3 R18 ("Candidates = units with at least one valid target row at or before the
# train end").
def candidate_units(unit_ids: np.ndarray, group_ids: np.ndarray, steps: np.ndarray,
                    label_is_valid: np.ndarray, group: str, train_end_step: Step) -> Tuple[str, ...]:
    """Candidate units of one group: at least one valid target row at or before the train end.

    Rule: R18.  Needed: Tue 29 Sep (M1).

    Contract (plan 2.3 R18):
        Reads only label validity at or before the train end; never a value, never a test-window
        row. The unit set is not chosen from target values (AUDIT_CHECKLIST).
    Inputs:
        unit_ids, group_ids, steps, label_is_valid: target rows.
        group: the group.
        train_end_step: last step of the donor train end year (Day for events).
    Returns:
        candidate unit ids, sorted.
    Refuses:
        - a group with no candidate unit.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: pm25_architecture.py:101-108 (cells_for: c = sorted ids; all if len(c) <= n; else
# c[::max(1, len(c) // n)][:n]); pm25_adaptation.py:531-533 uses the same formula on factorised codes.
def stride_pick(candidates: Tuple[str, ...], count: int) -> Tuple[str, ...]:
    """Deterministic stride over sorted unit ids. No seed, no draw.

    Rule: R18, G-NODRAW.  Needed: Tue 29 Sep (M1).

    Contract (plan 2.3 R18; source: provenance comment):
        If there are at most `count` candidates, take all. Otherwise take every s-th id from the
        sorted list, s = max(1, N // count), starting at the first, and keep the first `count`.
    Inputs:
        candidates: sorted candidate ids (candidate_units).
        count: R18 units per group.
    Returns:
        picked ids, in sorted order.
    Refuses:
        - count < 1 or unsorted candidates.
    OWNER DECISION: the source sorted factorised integer codes in one script (order of first
        appearance in the pool) and id strings in another; the engine sorts id STRINGS. The M1 gate
        checks that this reproduces the shipped picks, or flags the difference.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.3 R18 ("The same count applies to donor and test groups"); plan 4.1 step 5 (hash
# the id lists).
def pick_units(split: SplitSets, candidates_by_group: Mapping[str, Tuple[str, ...]],
               count: int) -> Mapping[str, Tuple[str, ...]]:
    """Pick units for every donor and test group with the same count, capped at what is available.

    Rule: R18.  Needed: Tue 29 Sep (M1).

    Contract (plan 2.3 R18, 4.1 step 5):
        stride_pick per group with one count for donor and test groups alike (a donor bank sees
        count x rows per unit, intended). The id lists are hashed into the manifest (hashing is
        boilerplate).
    Inputs:
        split: the split sets.
        candidates_by_group: {group: candidate ids}.
        count: R18 count (the neighbour kind passes 'every unit' as the group size).
    Returns:
        {group: picked ids}.
    Refuses:
        - a split group with no candidates entry.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R13, C8 (K = min(5, donor groups), round-robin over sorted donor names).
def make_donor_folds(donor_groups: Tuple[str, ...], k: int) -> Tuple[Tuple[str, ...], ...]:
    """Donor folds, round-robin over the sorted donor names.

    Rule: R13, plan 1.6.  Needed: M4 (Type-3 donor-fold service); M8 (neighbour track).

    Contract (plan 2.1 R13, C8):
        The donor at sorted position j goes to fold j mod K. Fold i's objects are built from the
        other donor groups only (FitContext.for_fold, for the R13 surface or the Type-3 service).
    Inputs:
        donor_groups: sorted donor set.
        k: K = min(5, donor groups), from derive_r13.
    Returns:
        held-out groups per fold, each tuple sorted.
    Refuses:
        - k < 2 or k greater than the number of donors.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-DISJOINT (banks see donor groups at or before the cut only; each bank, fold banks
# included, carries a manifest of its units and years; any overlap with test, or with its own held-out
# fold, is refused); banks without a year filter (CLAIMS_LEDGER.md:523); F15.
def assert_bank_disjoint(manifest: BankManifest, test_groups: Tuple[str, ...]) -> None:
    """Refuse a bank that saw a test group, its own held-out fold, or a label after its cut.

    Rule: G-DISJOINT.  Needed: Wed 30 Sep (bank).

    Contract (plan 5 G-DISJOINT):
        The manifest's groups must be donor groups only, disjoint from test_groups and from its own
        held_out_fold; its max label time must be at or before its cut.
    Inputs:
        manifest: the bank's manifest.
        test_groups: the sorted test set.
    Returns:
        None.
    Refuses:
        - any overlap, or max label time after the cut.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-SPLIT ("scored units = derived unit lists, re-checked on the OUTPUTS"); NDVI
# 25-vs-44 (Part 426); pm25_split.check() never called (pm25_split.py:192-197).
def check_scored_units(scored: Mapping[str, Tuple[str, ...]], derived: Mapping[str, Tuple[str, ...]]) -> None:
    """The units present in saved predictions must equal the derived unit lists, per group.

    Rule: G-SPLIT (outputs).  Needed: Sun 4 Oct (scoring; every row saved).

    Contract (plan 5 G-SPLIT, 7.1):
        Compared as sets per test group; counts are printed but never the check. The headline table
        builder re-runs this.
    Inputs:
        scored: {group: unit ids found in test_preds}.
        derived: {group: unit ids from pick_units}.
    Returns:
        None.
    Refuses:
        - any group whose sets differ, naming the units.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")
