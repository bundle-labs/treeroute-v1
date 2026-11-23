"""treeroute.split: the groups and unit lists under leave-one-region-out (plan 4.2 split.py row; R14,
R18, C16, C17; G-SPLIT, G-DISJOINT, G-NODRAW). SCIENCE (CV splits): owner-approved signatures, agent
bodies.

Signatures: _proposed/split.py (as_sorted_set D37, candidate_units, stride_pick D40) and
_proposed/loro_additions.py with engine/SIGNATURES_LORO_ADDENDUM.md, approved by the owner rulings file
(engine/OWNER_RULINGS_*.md, sections D and E: L1 K = 20, L2 all five companion rules, L7 option b).
Where the rulings file differs from a docstring there, the rulings file wins.

There is no donor or test list. Every group in the data that is not excluded trains its own trees and
is tested; a router never uses the trees of its own OVERLAP BLOCK (the groups that share or touch a
unit location with its group). split.yaml holds only exclusions and seen_during_design (L7 b); the
old hand-split lists live outside the engine (legacy_harness/, treeroute_report/).

BUILT here:
  - sorted sets (D37: plain code-point order of the strings), the split sets and their differences
    with the data, the groups (the data's groups minus the exclusions);
  - R18's two unit lists per group: candidates (a valid label at or before the train end), BANK units
    by a stride over the sorted ids (D40), SCORED units as an evenly spaced subset of the bank units
    (L2), and the C16 scored-unit budget max(minimum, floor(K x n / G)) capped at the bank count (the
    event floor on top of it is derive's R18 rule, which needs the donor labels);
  - the region router's fit cap: the largest evenly spaced set of WHOLE bank units whose pooled fit
    rows stay within the budget (R14, C7);
  - overlap blocks from the static table (R14, L2 rule 4): groups linked when a unit of one lies at
    the same grid position as, or in the 8-neighbourhood of, a unit of the other (grid indices), or
    within sqrt(2) x the larger median nearest-unit spacing (no grid indices); blocks are the
    connected components; block_of_group gives a group's block;
  - the rivals' region folds: round-robin over the blocks sorted by their first group (C17);
  - set and disjointness checks: scored units in the outputs (G-SPLIT), each group's tree manifest
    (G-DISJOINT, R19), each rival prediction's fold model (G-DISJOINT), a recomputed block set
    against the recorded one (G-DISJOINT at run start), the report groupings (R34, R35).

NOT here: the router's own-block column mask and its assert (route/kinds.py, router_tree_columns and
assert_no_own_group_column); the R18 count rules with the event floor, R13 and R21 (derive/); the
G-SPLIT and G-SUPPORT guard results (the validators); the masked Type-3 gateway (fit context, M4);
the distance bands (report metrics).

No draw anywhere: subsets by stride or by evenly spaced positions, folds round-robin (G-NODRAW).
Every function is pure and refuses bad input loudly; nothing here reads a file.
"""
# Provenance for the module: pm25_split.py:55-189 (lists only); pm25_architecture.py:101-108 (the
# stride pick); adaptation.py:1149-1150, 1213 (the region router's evenly spaced whole-unit cap and its
# row budget); owner rulings D and E (leave one region out; L1 K = 20; L2 companion rules 1-5; L3
# deferred to M8; L7 b); LORO review measurements D:/treeroute/loro_measure (read-only).

import hashlib
import math
from dataclasses import dataclass
from numbers import Integral
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from treeroute import engine_constants as K
from treeroute.derive import Derived, make_derived, sha256_of_array
from treeroute.errors import RefusedError

_SHOW = 5
GRID_INDICES = "grid_indices"
SPACING = "spacing"
LINK_RULES = (GRID_INDICES, SPACING)


class SplitRefusal(RefusedError):
    """A split rule refused (G-SPLIT, G-DISJOINT, G-NODRAW, R14, R18, C16, C17). Nothing catches it to
    carry on (fail loudly)."""


# ---------------------------------------------------------------------------------------------------
# Shapes (field-identical to the approved LORO shapes, _proposed/loro_additions.py)
@dataclass(frozen=True)
class LoroSplitSets:
    """split.yaml under LORO (plan 1.2). It replaces common.SplitSets: there is no donor or test list.
    Lists are sets; the engine sorts them by name. Under L7 (b) continuity_groups is always empty
    here: the old hard-split test groups live in treeroute_report/, which reports them from saved
    rows."""
    excluded: Mapping[str, str]
    seen_during_design: Tuple[str, ...]
    continuity_groups: Tuple[str, ...]


@dataclass(frozen=True)
class LoroSplitDiff:
    """Every set difference between split.yaml and the data under LORO (printed by `split freeze`)."""
    listed_not_in_data: Tuple[str, ...]
    reported_and_excluded: Tuple[str, ...]
    duplicates: Tuple[str, ...]


@dataclass(frozen=True)
class UnitCounts:
    """R18 outcome under LORO: two counts per group."""
    rule_value: int
    k_group_equivalents: int
    n_groups: int
    bank_by_group: Mapping[str, int]
    scored_by_group: Mapping[str, int]


@dataclass(frozen=True)
class UnitLists:
    """R18 picks under LORO: per group, the bank units (stride over sorted candidates) and the scored
    units (an evenly spaced subset of the bank units). Both lists are hashed into the manifest."""
    bank: Mapping[str, Tuple[str, ...]]
    scored: Mapping[str, Tuple[str, ...]]


@dataclass(frozen=True)
class OverlapBlocks:
    """R14 overlap blocks: groups that share or touch a unit location, as connected components.
    Derived from the static table only (derive_overlap_blocks); no list is hand-set."""
    block_of_group: Mapping[str, int]
    members: Tuple[Tuple[str, ...], ...]
    linked_pairs: Tuple[Tuple[str, str, int], ...]
    link_rule: str


# ---------------------------------------------------------------------------------------------------
# Small checks shared by the rules
def _count(value: Any, what: str, rule: str, low: int = 1) -> int:
    """An integer count >= low; a bool, a float or a string is refused."""
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (Integral, np.integer)):
        raise SplitRefusal(rule, "%s must be an integer, got %s %r" % (what, type(value).__name__, value),
                           fix="pass a plain integer count")
    out = int(value)
    if out < low:
        raise SplitRefusal(rule, "%s = %d is below %d" % (what, out, low))
    return out


def _name(value: Any, what: str, rule: str) -> str:
    if not isinstance(value, str) or value == "":
        raise SplitRefusal(rule, "%s must be a non-empty name string, got %s %r"
                           % (what, type(value).__name__, value),
                           fix="pass names exactly as the data spells them")
    return value


def _sorted_unique(units: Any, what: str, rule: str) -> Tuple[str, ...]:
    """A tuple of names in strictly increasing code-point order (sorted, no repeat)."""
    if isinstance(units, (str, bytes)) or not isinstance(units, Sequence):
        raise SplitRefusal(rule, "%s must be a sequence of names, got %s" % (what, type(units).__name__))
    out = tuple(_name(u, "every entry of %s" % what, rule) for u in units)
    for i in range(1, len(out)):
        if not out[i - 1] < out[i]:
            problem = "repeats %r" % out[i] if out[i - 1] == out[i] else (
                "is not sorted (%r before %r)" % (out[i - 1], out[i]))
            raise SplitRefusal(rule, "%s %s" % (what, problem),
                               fix="pass the ids sorted by as_sorted_set (plain code-point order), each once")
    return out


def _show(names: Iterable[Any]) -> str:
    names = list(names)
    text = ", ".join(repr(n) for n in names[:_SHOW])
    return text + (" and %d more" % (len(names) - _SHOW) if len(names) > _SHOW else "")


# ---------------------------------------------------------------------------------------------------
# Sorted sets, the split file and the groups (plan 1.2; G-SPLIT)
# Provenance: plan 1.2 split.yaml ("The engine sorts group names, so order carries no meaning"); 1.7
# (donor order door closed); D37 accepted (plain code-point order).
def as_sorted_set(names: Iterable[str], what: str) -> Tuple[str, ...]:
    """Turn a declared list into a set sorted by name.

    Rule: plan 1.2, 1.7, G-SPLIT (D37). Order carries no meaning: seeds come from names (R19) and folds
    are round-robin over sorted blocks (C17). The sort is plain code-point order of the strings (what
    Python and numpy sort give), recorded in the manifest by the caller.
    Returns the names sorted, as a tuple.
    Refuses: a repeated name (a list with a repeat is not a set); an empty or non-string name; a bare
    string passed as the list.
    """
    rule = "G-SPLIT"
    what = _name(what, "the list's name", rule)
    if isinstance(names, (str, bytes)):
        raise SplitRefusal(rule, "%s must be a list of names, got the single string %r" % (what, names))
    out = [_name(n, "every name in %s" % what, rule) for n in names]
    seen, repeats = set(), []
    for n in out:
        if n in seen and n not in repeats:
            repeats.append(n)
        seen.add(n)
    if repeats:
        raise SplitRefusal(rule, "%s names %s more than once" % (what, _show(sorted(repeats))),
                           fix="list each group once (the list is a set)")
    return tuple(sorted(out))


def loro_split_sets(split_file: Any) -> LoroSplitSets:
    """The LORO split sets from the package's split.yaml model (package/schema.py SplitFile).

    Boilerplate: reads the two fields split.yaml may hold (excluded, seen_during_design), sorts the
    seen list (D37), and leaves continuity_groups empty (L7 b: the continuity list is not package
    input). Refuses a model without those fields or with a repeated seen group.
    """
    rule = "G-SPLIT"
    for field in ("excluded", "seen_during_design"):
        if not hasattr(split_file, field):
            raise SplitRefusal(rule, "the split file has no %r field (got %s)"
                               % (field, type(split_file).__name__),
                               fix="pass the loaded package's split (package.load: pkg.split)")
    excluded = {}
    for group, reason in dict(split_file.excluded).items():
        excluded[_name(group, "an excluded group", rule)] = _name(reason, "the reason for %r" % group, rule)
    return LoroSplitSets(excluded=dict(sorted(excluded.items())),
                         seen_during_design=as_sorted_set(split_file.seen_during_design,
                                                          "seen_during_design"),
                         continuity_groups=())


def _repeats(names: Sequence[str]) -> List[str]:
    seen, out = set(), []
    for n in names:
        if n in seen and n not in out:
            out.append(n)
        seen.add(n)
    return out


# Provenance: plan 1.2 split.yaml (LORO: exclusions, seen_during_design, continuity_groups; every listed
# group exists in the data; a reported group may not be excluded). Supersedes split.split_differences
# (D38, D39 lapse).
def loro_split_differences(split: LoroSplitSets, data_groups: Tuple[str, ...]) -> LoroSplitDiff:
    """Every difference between split.yaml and the data's groups, under LORO.

    Rule: G-SPLIT, plan 1.2. There is no donor or test list, so there is no disjointness to check.
    Every group that split.yaml names (excluded, seen_during_design, continuity_groups) must exist in
    the data, and a seen_during_design or continuity group may not also be excluded. Duplicates are
    names repeated inside seen_during_design, inside continuity_groups, or inside data_groups. Counts
    are printed but never used as the check. Pure: the validator turns a non-empty difference into a
    BLOCK.
    Returns LoroSplitDiff (every field sorted; all empty when consistent).
    """
    data = set(data_groups)
    excluded = set(split.excluded)
    reported = set(split.seen_during_design) | set(split.continuity_groups)
    duplicates = set(_repeats(tuple(split.seen_during_design))) | set(
        _repeats(tuple(split.continuity_groups))) | set(_repeats(tuple(data_groups)))
    return LoroSplitDiff(listed_not_in_data=tuple(sorted((excluded | reported) - data)),
                         reported_and_excluded=tuple(sorted(reported & excluded)),
                         duplicates=tuple(sorted(duplicates)))


# Provenance: plan 1.2 ("The groups are the data's groups minus the exclusions"); owner ruling D (every
# group gets its own specialist trees and every group is tested).
def groups_under_loro(split: LoroSplitSets, data_groups: Tuple[str, ...]) -> Tuple[str, ...]:
    """The groups: the data's groups minus the exclusions, sorted by name. Every one is trained and
    tested.

    Rule: plan 1.2, R18, R19. Sorted in as_sorted_set's order (D37). Each returned group trains its own
    trees on its bank units (R19) and is scored on its scored units (R18). G, the number of groups in
    the R18 budget rule, is the length of the result.
    Refuses: a repeated data group; an exclusion that names a group not in the data; an empty result.
    """
    rule = "G-SPLIT"
    data = as_sorted_set(data_groups, "the data's groups")
    missing = sorted(set(split.excluded) - set(data))
    if missing:
        raise SplitRefusal(rule, "split.yaml excludes %s, not in the data" % _show(missing),
                           fix="exclude only groups the target table holds (check the spelling)")
    out = tuple(g for g in data if g not in split.excluded)
    if not out:
        raise SplitRefusal(rule, "every group of the data is excluded, so no group is left to train "
                                 "and test", fix="remove exclusions")
    return out


# Provenance: owner ruling D ("free continuity row: the old hard-split test groups are also reported
# alone, from the same run"); plan R34, R35, Q49 (seen_during_design row); L7 b.
def report_groupings(groups: Tuple[str, ...], split: LoroSplitSets) -> Mapping[str, Tuple[str, ...]]:
    """The group sets every score table, jackknife and verdict is reported on.

    Rule: R34, R35, Q49. 'all' = every group (the headline, the jackknife and the band).
    'without_seen_during_design' = all minus seen_during_design (only when that list is non-empty).
    'continuity' = the continuity groups (only when that list is non-empty; under L7 b the package
    never holds it, and treeroute_report computes that row from saved rows). The band is derived on
    'all' only and judges every set (R35). Reporting only: no set changes a fit, a pick or a decision.
    Returns {grouping name: sorted groups}.
    Refuses: repeated groups; a seen_during_design or continuity group not in groups.
    """
    rule = "R34"
    every = as_sorted_set(groups, "the groups")
    out: Dict[str, Tuple[str, ...]] = {"all": every}
    for key, listed in (("without_seen_during_design", split.seen_during_design),
                        ("continuity", split.continuity_groups)):
        listed = as_sorted_set(listed, key)
        if not listed:
            continue
        unknown = sorted(set(listed) - set(every))
        if unknown:
            raise SplitRefusal(rule, "%s names %s, which are not among the groups" % (key, _show(unknown)),
                               fix="a reported group must be one of the groups (data minus exclusions)")
        if key == "continuity":
            out[key] = listed
        else:
            out[key] = tuple(g for g in every if g not in set(listed))
    return out


# ---------------------------------------------------------------------------------------------------
# R18: candidates, bank units by stride, scored units as an evenly spaced subset
# Provenance: plan 2.3 R18 ("Candidates = units with at least one valid target row at or before the
# train end").
def candidate_units(unit_ids: np.ndarray, group_ids: np.ndarray, steps: np.ndarray,
                    label_is_valid: np.ndarray, group: str, train_end_step: int) -> Tuple[str, ...]:
    """Candidate units of one group: at least one valid target row at or before the train end.

    Rule: R18. Reads only label validity at or before the train end; never a value, never a
    test-window row, so the unit set is not chosen from target values (AUDIT_CHECKLIST). Under LORO
    it runs for every group.
    Returns candidate unit ids, sorted (code-point order).
    Refuses: arrays of different lengths; a non-boolean validity array; non-integer steps; a unit id
    that is not a non-empty string; a group with no candidate unit.
    """
    rule = "R18"
    group = _name(group, "group", rule)
    cut = _count(train_end_step, "train_end_step", rule, low=-(1 << 62))
    units = np.asarray(unit_ids)
    groups = np.asarray(group_ids)
    t = np.asarray(steps)
    ok = np.asarray(label_is_valid)
    n = len(units)
    for what, arr in (("group_ids", groups), ("steps", t), ("label_is_valid", ok)):
        if arr.ndim != 1 or len(arr) != n:
            raise SplitRefusal(rule, "%s has shape %s for %d unit ids" % (what, arr.shape, n))
    if units.ndim != 1:
        raise SplitRefusal(rule, "unit_ids must be 1-D, got shape %s" % (units.shape,))
    if ok.dtype != np.bool_:
        raise SplitRefusal(rule, "label_is_valid must be boolean, got %s" % ok.dtype,
                           fix="pass finite-label validity (D6) as a boolean array")
    if n and not np.issubdtype(t.dtype, np.integer):
        raise SplitRefusal(rule, "steps must be integer steps or days, got %s" % t.dtype)
    keep = (groups == group) & ok & (t <= cut) if n else np.zeros(0, dtype=bool)
    found = set(units[keep].tolist())
    bad = sorted(repr(u) for u in found if not isinstance(u, str) or u == "")
    if bad:
        raise SplitRefusal(rule, "unit ids must be non-empty strings; found %s" % ", ".join(bad[:_SHOW]))
    if not found:
        raise SplitRefusal(rule, "group %r has no unit with a valid label at or before step %d" % (group, cut),
                           fix="exclude the group in split.yaml, with its reason, or check the store")
    return tuple(sorted(found))


# Provenance: pm25_architecture.py:101-108 (cells_for: c = sorted ids; all if len(c) <= n; else
# c[::max(1, len(c) // n)][:n]); pm25_adaptation.py:531-533 uses the same formula on factorised codes.
def stride_pick(candidates: Tuple[str, ...], count: int) -> Tuple[str, ...]:
    """Deterministic stride over sorted unit ids. No seed, no draw.

    Rule: R18, G-NODRAW (D40). If there are at most `count` candidates, take all. Otherwise take every
    s-th id from the sorted list, s = max(1, N // count), starting at the first, and keep the first
    `count`. Under LORO the stride picks each group's BANK units. The engine sorts id STRINGS; the M1
    gate checks that this reproduces the shipped picks, or flags the difference (D40).
    Returns picked ids, in sorted order.
    Refuses: count < 1; unsorted or repeated candidates.
    """
    rule = "R18"
    count = _count(count, "count", rule)
    cands = _sorted_unique(candidates, "candidates", rule)
    n = len(cands)
    if n <= count:
        return cands
    step = max(1, n // count)
    return cands[::step][:count]


# Provenance: plan 2.2 R14 (positions floor(i x (N-1)/(m-1))); adaptation.py:1149-1150 (the shipped
# np.linspace pick); region_cap_units' accepted m = 1 default (position 0); L2 approved (this formula,
# not stride_pick's N // m, which never reaches the tail of the sorted list).
def evenly_spaced_subset(sorted_units: Tuple[str, ...], count: int) -> Tuple[str, ...]:
    """The scored units of a group: an evenly spaced subset of its sorted bank units.

    Rule: R18 (2), R14's formula, G-NODRAW. Over the N sorted units keep positions
    floor(i x (N-1)/(m-1)), i = 0..m-1, with m = count, in exact integer arithmetic; all units when
    count >= N; position 0 when m = 1. The subset spans the whole sorted list, first and last unit
    included. No seed, no draw.
    Returns the kept units, in sorted order.
    Refuses: count < 1; unsorted or duplicated units; an empty unit list.
    """
    rule = "R18"
    count = _count(count, "count", rule)
    units = _sorted_unique(sorted_units, "sorted_units", rule)
    n = len(units)
    if n == 0:
        raise SplitRefusal(rule, "no unit to pick from")
    return tuple(units[p] for p in _even_positions(n, count))


def _even_positions(n: int, m: int) -> List[int]:
    """Positions floor(i x (n-1)/(m-1)), i = 0..m-1 (all positions when m >= n; [0] when m = 1)."""
    if m >= n:
        return list(range(n))
    if m == 1:
        return [0]
    return [(i * (n - 1)) // (m - 1) for i in range(m)]


# Provenance: owner ruling D ("the same TOTAL as the old hard split, spread over all groups"); plan 2.3
# R18 (2); C16 (L1 ruled: one engine constant K = 20; scored units per group = max(10, floor(20 x R18
# count / G)), capped at the units available). K = 20 gives 15 / 50 / 2,040 / 15 per group on the four
# headline packages (comments only, G-NONAMES).
def scored_count_budget(rule_value: int, bank_by_group: Mapping[str, int],
                        k_group_equivalents: int) -> Tuple[Mapping[str, int], Tuple[str, ...]]:
    """The C16 scored-unit budget per group, BEFORE the event floor: max(minimum, floor(K x n / G)),
    capped at the group's bank count.

    Rule: R18 (2), C16. G = the number of groups (the keys of bank_by_group); n = the bank-count rule
    value before the per-group cap; K = the engine constant C16 (the caller passes
    engine_constants.K_GROUP_EQUIVALENTS; never a package value or a flag). floor(K x n / G) is exact
    integer arithmetic, rounded DOWN so the budget is never exceeded; the minimum is C16's
    SCORED_UNITS_MIN. The event floor (D13, D14) raises a count on top of this and belongs to derive's
    R18 rule, which reads the donor labels.
    Returns ({group: scored count}, flags). Flags: 'minimum:<group>' for every group when the minimum
    binds; 'scored_capped:<group>' when a group's bank count is below the budget.
    Refuses: K < 1; n < 1; an empty group map; a bank count < 1.
    """
    rule = "C16"
    n = _count(rule_value, "rule_value (n)", rule)
    k = _count(k_group_equivalents, "k_group_equivalents (K)", rule)
    if not isinstance(bank_by_group, Mapping) or not bank_by_group:
        raise SplitRefusal(rule, "bank_by_group must be a non-empty {group: bank count} map")
    banks = {_name(g, "a group", rule): _count(c, "the bank count of %r" % g, rule)
             for g, c in bank_by_group.items()}
    g_count = len(banks)
    raw = (k * n) // g_count
    base = max(int(K.SCORED_UNITS_MIN), raw)
    out: Dict[str, int] = {}
    flags: List[str] = []
    for g in sorted(banks):
        out[g] = min(base, banks[g])
        if raw < int(K.SCORED_UNITS_MIN):
            flags.append("minimum:%s" % g)
        if banks[g] < base:
            flags.append("scored_capped:%s" % g)
    return out, tuple(flags)


# Provenance: plan 2.3 R18; plan 4.1 step 5 (pick both lists, hash both); pm25_architecture.py:101-108
# (stride over sorted ids, D40). Supersedes split.pick_units.
def pick_unit_lists(groups: Tuple[str, ...], candidates_by_group: Mapping[str, Tuple[str, ...]],
                    counts: UnitCounts) -> UnitLists:
    """Pick every group's bank units by stride and its scored units as an evenly spaced subset of them.

    Rule: R18, G-DISJOINT. For every group: bank = stride_pick(candidates, bank count) (D40); scored =
    evenly_spaced_subset(bank, scored count). The scored list is always inside the bank list
    (asserted). A unit id listed under two groups is refused (unit ids carry their group, plan 1.2;
    physical overlap between groups is handled by overlap blocks). Hashing the lists into the
    manifest is boilerplate (unit_ids_hash).
    Returns UnitLists, keyed in sorted group order.
    Refuses: repeated groups; a group without candidates or without counts; counts for a group that is
    not listed; a bank count above its candidates; a scored count above its bank count; a count < 1.
    """
    rule = "R18"
    groups = as_sorted_set(groups, "groups")
    if not groups:
        raise SplitRefusal(rule, "no group to pick units for")
    for what, keys in (("candidates_by_group", candidates_by_group), ("bank counts", counts.bank_by_group),
                       ("scored counts", counts.scored_by_group)):
        missing = sorted(set(groups) - set(keys))
        extra = sorted(set(keys) - set(groups))
        if missing:
            raise SplitRefusal(rule, "%s has no entry for %s" % (what, _show(missing)))
        if extra and what != "candidates_by_group":
            raise SplitRefusal(rule, "%s names groups that are not listed: %s" % (what, _show(extra)))
    bank: Dict[str, Tuple[str, ...]] = {}
    scored: Dict[str, Tuple[str, ...]] = {}
    owner: Dict[str, str] = {}
    for g in groups:
        cands = _sorted_unique(candidates_by_group[g], "the candidates of %r" % g, rule)
        nb = _count(counts.bank_by_group[g], "the bank count of %r" % g, rule)
        ns = _count(counts.scored_by_group[g], "the scored count of %r" % g, rule)
        if nb > len(cands):
            raise SplitRefusal(rule, "group %r: bank count %d is above its %d candidates" % (g, nb, len(cands)),
                               fix="cap the bank count at the units available (derive R18)")
        if ns > nb:
            raise SplitRefusal(rule, "group %r: scored count %d is above its bank count %d" % (g, ns, nb),
                               fix="the scored units are a subset of the bank units (derive R18)")
        b = stride_pick(cands, nb)
        s = evenly_spaced_subset(b, ns)
        if not set(s) <= set(b):
            raise SplitRefusal("G-SPLIT", "internal: a scored unit of %r is outside its bank list" % g)
        for u in b:
            if u in owner:
                raise SplitRefusal("G-DISJOINT", "unit %r is listed under groups %r and %r" % (u, owner[u], g),
                                   fix="a unit belongs to one group (unit ids carry their group, plan 1.2)")
            owner[u] = g
        bank[g] = b
        scored[g] = s
    return UnitLists(bank=bank, scored=scored)


# Provenance: plan 5 G-SPLIT (outputs: per group, the scored units = the derived scored list and lie
# inside the bank list); 7.1 (the headline table builder re-checks). Supersedes split.check_scored_units.
def check_scored_units_loro(scored_in_outputs: Mapping[str, Tuple[str, ...]], lists: UnitLists) -> None:
    """The units in saved predictions must equal the derived scored lists, per group, and lie inside the
    group's bank list.

    Rule: G-SPLIT (outputs). For EVERY group (LORO): the set of units in test_preds equals
    lists.scored[group], and lists.scored[group] is a subset of lists.bank[group]. Compared as sets;
    counts are printed but never the check.
    Returns None.
    Refuses: a group missing from the outputs or from the lists; a group in the outputs that the lists
    do not hold; any set difference, naming the units; a scored unit outside its bank list.
    """
    rule = "G-SPLIT"
    listed = set(lists.scored)
    if set(lists.bank) != listed:
        raise SplitRefusal(rule, "the unit lists hold bank lists for %s but scored lists for %s"
                           % (_show(sorted(lists.bank)), _show(sorted(listed))))
    missing = sorted(listed - set(scored_in_outputs))
    extra = sorted(set(scored_in_outputs) - listed)
    if missing:
        raise SplitRefusal(rule, "the outputs hold no scored unit of %s" % _show(missing),
                           fix="every group is tested under LORO: score each group's scored units")
    if extra:
        raise SplitRefusal(rule, "the outputs hold groups outside the unit lists: %s" % _show(extra))
    for g in sorted(listed):
        want, got = set(lists.scored[g]), set(scored_in_outputs[g])
        outside = sorted(want - set(lists.bank[g]))
        if outside:
            raise SplitRefusal(rule, "group %r: scored units outside its bank list: %s" % (g, _show(outside)))
        if want != got:
            raise SplitRefusal(rule, "group %r: the outputs score %d units, the derived list has %d; "
                               "missing %s; not derived %s" % (g, len(got), len(want),
                                                               _show(sorted(want - got)) or "none",
                                                               _show(sorted(got - want)) or "none"),
                               fix="score exactly the derived scored units (split.pick_unit_lists)")


def unit_ids_hash(units: Iterable[str]) -> str:
    """SHA-256 of a unit set: its distinct ids sorted (code-point order), joined by new lines.

    Boilerplate, the same formula as the bank manifest's unit_ids_hash (fit/bank.py), so a group's
    manifest can be compared with its bank list."""
    distinct = sorted(set(_name(u, "a unit id", "G-DISJOINT") for u in units))
    return hashlib.sha256("\n".join(distinct).encode("utf-8")).hexdigest()


# Provenance: plan 5 G-DISJOINT (each group's trees see only that group's bank units at or before the
# cut; a manifest per group); CLAIMS_LEDGER.md:523 (banks without a year filter); F15; owner rulings E
# (no fold banks under LORO). Supersedes split.assert_bank_disjoint.
def assert_group_manifests(group_manifests: Mapping[str, Any], unit_lists: UnitLists, cut: int) -> None:
    """Refuse a bank in which any group's trees saw another group, units outside its bank list, or a
    label after the cut.

    Rule: G-DISJOINT, R19. Every group has one manifest (fit/bank.py BankManifest). Its groups are
    exactly that group; its units are that group's bank units (compared by unit_ids_hash, and by
    count); its cut is `cut` and its max label time is at or before it; it is not a fold bank (no
    fold bank is fitted under LORO). Applies to the main bank at every lead cut and to any bank refitted
    at the inner cut (L6 b).
    Returns None.
    Refuses: a missing or extra group; a manifest naming another group; other units; another cut; a
    label after the cut; a held-out fold.
    """
    rule = "G-DISJOINT"
    cut = _count(cut, "cut", rule, low=-(1 << 62))
    want, have = set(unit_lists.bank), set(group_manifests)
    if want - have:
        raise SplitRefusal(rule, "no tree manifest for groups %s" % _show(sorted(want - have)),
                           fix="every group trains its own trees under LORO (one manifest per group)")
    if have - want:
        raise SplitRefusal(rule, "tree manifests for groups outside the unit lists: %s"
                           % _show(sorted(have - want)))
    for g in sorted(want):
        m = group_manifests[g]
        for field in ("groups", "unit_ids_hash", "n_units", "max_label_time", "cut", "held_out_fold"):
            if not hasattr(m, field):
                raise SplitRefusal(rule, "the manifest of %r has no %r field" % (g, field),
                                   fix="pass BankManifest records (fit/bank.py)")
        if tuple(m.groups) != (g,):
            raise SplitRefusal(rule, "the trees of %r saw groups %r" % (g, tuple(m.groups)),
                               fix="each group's trees train on that group's bank units only (R19)")
        bank = unit_lists.bank[g]
        if int(m.n_units) != len(set(bank)) or m.unit_ids_hash != unit_ids_hash(bank):
            raise SplitRefusal(rule, "the trees of %r saw %d units that are not its %d bank units "
                               "(unit hash differs)" % (g, int(m.n_units), len(set(bank))),
                               fix="fit each group's trees on its bank units' rows (split.pick_unit_lists)")
        if int(m.cut) != cut:
            raise SplitRefusal(rule, "the manifest of %r records cut %d, not %d" % (g, int(m.cut), cut))
        if int(m.max_label_time) > cut:
            raise SplitRefusal(rule, "the trees of %r saw a label at %d, after the cut %d"
                               % (g, int(m.max_label_time), cut))
        if tuple(m.held_out_fold or ()):
            raise SplitRefusal(rule, "the manifest of %r is a fold bank (held out %r); no fold bank is "
                               "fitted under LORO" % (g, tuple(m.held_out_fold)))


# ---------------------------------------------------------------------------------------------------
# The region router's fit budget (R14, C7)
# Provenance: plan 2.2 R14 ("Fit rows are capped at 60,000 by keeping whole UNITS, evenly spaced ...
# the largest number m of units at positions floor(i x (N-1)/(m-1)) whose pooled fit rows stay at or
# under 60,000"); adaptation.py:1149-1150 (the shipped np.linspace pick, moved from rows to units),
# :1213 (REGROWS = 60000); L2 rule 2 (the fit units are the group's BANK units, decoupled from its
# scored units). m = 1 keeps position 0 (the accepted default).
def region_cap_units(sorted_units: Tuple[str, ...], fit_rows_per_unit: Mapping[str, int],
                     budget: int) -> Tuple[str, ...]:
    """The region router's fit cap: the largest set of evenly spaced WHOLE units whose pooled fit rows
    stay within the budget.

    Rule: R14, C7. Over the N units in sorted id order (a group's bank units), keep the largest m such
    that the units at positions floor(i x (N-1)/(m-1)), i = 0..m-1, have pooled fit rows at or under
    the budget (engine_constants.REGION_ROUTER_ROW_BUDGET); all units when they fit. Every kept unit
    keeps all its fit years. m is searched from N down, so the answer is the largest feasible m even
    where the pooled rows are not monotone in m.
    Returns the kept units, in sorted order.
    Refuses: an empty, unsorted or repeated unit list; a unit without a row count, or a negative or
    non-integer count; budget < 1; a single unit whose own rows exceed the budget.
    """
    rule = "R14"
    units = _sorted_unique(sorted_units, "sorted_units", rule)
    budget = _count(budget, "budget", rule)
    if not units:
        raise SplitRefusal(rule, "no unit to cap")
    missing = [u for u in units if u not in fit_rows_per_unit]
    if missing:
        raise SplitRefusal(rule, "no fit-row count for units %s" % _show(missing))
    rows = np.array([_count(fit_rows_per_unit[u], "the fit rows of %r" % u, rule, low=0) for u in units],
                    dtype=np.int64)
    over = [u for u, r in zip(units, rows.tolist()) if r > budget]
    if over:
        raise SplitRefusal(rule, "units %s each hold more fit rows than the whole budget %d"
                           % (_show(over), budget), fix="check the fit rows per unit (one row per step)")
    n = len(units)
    if int(rows.sum()) <= budget:
        return units
    for m in range(n - 1, 0, -1):
        pos = (np.arange(m, dtype=np.int64) * (n - 1)) // (m - 1) if m > 1 else np.zeros(1, np.int64)
        if int(rows[pos].sum()) <= budget:
            return tuple(units[p] for p in pos.tolist())
    raise SplitRefusal(rule, "internal: no evenly spaced unit set fits the budget %d" % budget)


# ---------------------------------------------------------------------------------------------------
# Overlap blocks (R14; G-DISJOINT, C17, R34)
class _Components(object):
    """Union-find over group codes (connected components of the linked-pair graph)."""

    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, a: int) -> int:
        while self.parent[a] != a:
            self.parent[a] = self.parent[self.parent[a]]
            a = self.parent[a]
        return a

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def _int_indices(values: Any, what: str, n: int, rule: str) -> np.ndarray:
    arr = np.asarray(values)
    if arr.ndim != 1 or len(arr) != n:
        raise SplitRefusal(rule, "%s has shape %s for %d units" % (what, arr.shape, n))
    if n and not np.issubdtype(arr.dtype, np.integer):
        raise SplitRefusal(rule, "%s must hold integer grid indices, got %s" % (what, arr.dtype),
                           fix="the static table's grid_ix / grid_iy are plain integers (plan 1.2)")
    return arr.astype(np.int64)


def _linked_units_grid(codes: np.ndarray, ix: np.ndarray, iy: np.ndarray):
    """(unit, other group) pairs for the same position or the 8-neighbourhood, and for the same
    position alone. Each is an int64 array of shape (k, 2), distinct rows."""
    lo_x, lo_y = int(ix.min()) - 1, int(iy.min()) - 1
    width = int(iy.max()) - lo_y + 2
    height = int(ix.max()) - lo_x + 2
    if width * height >= (1 << 62):
        raise SplitRefusal("R14", "the grid indices span too wide a range to encode")
    key = (ix - lo_x) * width + (iy - lo_y)
    order = np.lexsort((codes, key))
    k_sorted, g_sorted = key[order], codes[order]
    distinct = np.ones(len(k_sorted), dtype=bool)
    distinct[1:] = (k_sorted[1:] != k_sorted[:-1]) | (g_sorted[1:] != g_sorted[:-1])
    k_sorted, g_sorted = k_sorted[distinct], g_sorted[distinct]
    unit = np.arange(len(codes), dtype=np.int64)
    linked, shared = [], []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            q = key + dx * width + dy
            left = np.searchsorted(k_sorted, q, side="left")
            right = np.searchsorted(k_sorted, q, side="right")
            hits = right - left
            if not hits.any():
                continue
            who = np.repeat(unit, hits)
            start = np.repeat(left, hits)
            offset = np.arange(len(who), dtype=np.int64) - np.repeat(np.cumsum(hits) - hits, hits)
            other = g_sorted[start + offset]
            keep = other != codes[who]
            pairs = np.stack([who[keep], other[keep]], axis=1)
            linked.append(pairs)
            if dx == 0 and dy == 0:
                shared.append(pairs)
    return _distinct_rows(linked), _distinct_rows(shared)


def _distinct_rows(parts: List[np.ndarray]) -> np.ndarray:
    if not parts:
        return np.zeros((0, 2), dtype=np.int64)
    rows = np.concatenate(parts, axis=0)
    if len(rows) == 0:
        return rows.reshape(0, 2)
    return np.unique(rows, axis=0)


def _unit_vectors(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    la, lo = np.radians(lat), np.radians(lon)
    return np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], axis=1)


def _chord(angle: float) -> float:
    """Chord length on the unit sphere for a central angle (clamped at a half turn)."""
    return 2.0 * math.sin(min(angle, math.pi) / 2.0)


def _angle(chord: np.ndarray) -> np.ndarray:
    return 2.0 * np.arcsin(np.clip(chord / 2.0, 0.0, 1.0))


def _linked_units_spacing(codes: np.ndarray, names: Tuple[str, ...], lat: np.ndarray, lon: np.ndarray,
                          rule: str):
    """(unit, other group) pairs within sqrt(2) x the larger median nearest-unit spacing of the two
    groups; same-position pairs; and each group's spacing (central angle, radians)."""
    from scipy.spatial import cKDTree   # lazy: only the no-grid-indices rule needs it

    xyz = _unit_vectors(lat, lon)
    spacing: Dict[str, float] = {}
    by_group = []
    for c, g in enumerate(names):
        members = np.flatnonzero(codes == c)
        if len(members) < 2:
            raise SplitRefusal(rule, "group %r has %d unit and the static table has no grid indices, so no "
                               "unit spacing can be computed" % (g, len(members)),
                               fix="add grid_ix / grid_iy to the static table (plan 1.2)")
        dist, _ = cKDTree(xyz[members]).query(xyz[members], k=2)
        spacing[g] = float(np.median(_angle(dist[:, 1])))
        by_group.append(members)
    tree_all = cKDTree(xyz)
    linked, shared = [], []
    for c, g in enumerate(names):
        members = by_group[c]
        radius = _chord(math.sqrt(2.0) * spacing[g])
        found = cKDTree(xyz[members]).sparse_distance_matrix(tree_all, radius, output_type="ndarray")
        if len(found) == 0:
            continue
        i = members[found["i"].astype(np.int64)]
        j = found["j"].astype(np.int64)
        other = codes[j] != c
        i, j = i[other], j[other]
        # symmetric: unit i of g is linked to j's group, and unit j to g
        linked.append(np.stack([i, codes[j]], axis=1))
        linked.append(np.stack([j, np.full(len(i), c, dtype=np.int64)], axis=1))
        same = found["v"][other] == 0.0
        shared.append(np.stack([i[same], codes[j[same]]], axis=1))
        shared.append(np.stack([j[same], np.full(int(same.sum()), c, dtype=np.int64)], axis=1))
    return _distinct_rows(linked), _distinct_rows(shared), spacing


def _unit_counts_by_pair(pairs: np.ndarray, codes: np.ndarray) -> Dict[Tuple[int, int], int]:
    """{(group code of the unit, other group code): distinct units of the first group linked}."""
    if len(pairs) == 0:
        return {}
    own = codes[pairs[:, 0]]
    keys, counts = np.unique(np.stack([own, pairs[:, 1]], axis=1), axis=0, return_counts=True)
    return {(int(a), int(b)): int(n) for (a, b), n in zip(keys.tolist(), counts.tolist())}


# Provenance: plan 2.2 R14 (overlap blocks: rule on the static table, no list); owner rulings E L2 rule
# 4 ("groups that share cells are dropped together, so a router drops the trees of its whole overlap
# block"; approved as the addendum's share-or-touch rule); LORO review, measured read-only on
# D:/monthly_panel (133 groups): 8 linked pairs, 125 blocks, no pair that only touches. Unit ids carry
# their group (plan 1.2), so two groups never share an id string: they share a grid POSITION.
def derive_overlap_blocks(unit_group: np.ndarray, unit_lat: np.ndarray, unit_lon: np.ndarray,
                          grid_ix: Optional[np.ndarray], grid_iy: Optional[np.ndarray]) -> Derived:
    """Overlap blocks: groups linked when a unit of one lies at the same grid position as, or in the
    8-neighbourhood of, a unit of the other; blocks are the connected components.

    Rule: R14 (overlap blocks), G-DISJOINT, C17, R34 (L2 rule 4). Units are every candidate unit of
    every group, from the static table (not the picks, so the blocks do not move with the unit counts).
    Link rule, no hand-set number:
      - 'grid_indices' when the static table has grid_ix and grid_iy: two units are linked when both
        indices differ by at most 1 (same cell or one of its 8 neighbours);
      - 'spacing' otherwise: two units are linked when their great-circle distance is at most
        sqrt(2) x the larger of the two groups' median nearest-unit spacing, each spacing computed
        from the group's own units (central angles, so no Earth radius enters).
    Two groups are linked when any pair of their units is linked. Blocks are the connected
    components, each sorted by name, and sorted by their first member; every group is in exactly one
    block. linked_pairs holds (group, group, units of the smaller group linked to the other), the
    pair sorted by name; the smaller group is the one with fewer units (the first by name on a tie).
    Returns Derived[OverlapBlocks] (rule 'R14'); inputs record the link rule, the unit count per
    group, each linked pair's shared-position and linked unit counts on both sides (a pair with no
    shared position only touches), each group's spacing (spacing rule) and the static table's hashes;
    flags carry 'overlap:<group>+<group>:<units>' per linked pair.
    Refuses: mismatched lengths; no unit; a group name that is not a non-empty string; a non-finite
    latitude or longitude, or a latitude outside [-90, 90]; one of grid_ix / grid_iy without the
    other; non-integer grid indices; a group with one unit and no grid indices.
    """
    rule = "R14"
    groups = np.asarray(unit_group, dtype=object)
    lat = np.asarray(unit_lat, dtype=np.float64)
    lon = np.asarray(unit_lon, dtype=np.float64)
    n = len(groups)
    if groups.ndim != 1 or n == 0:
        raise SplitRefusal(rule, "unit_group must be a non-empty 1-D array (one entry per candidate unit)")
    for what, arr in (("unit_lat", lat), ("unit_lon", lon)):
        if arr.ndim != 1 or len(arr) != n:
            raise SplitRefusal(rule, "%s has shape %s for %d units" % (what, arr.shape, n))
    bad = sorted(set(repr(g) for g in groups.tolist() if not isinstance(g, str) or g == ""))
    if bad:
        raise SplitRefusal(rule, "unit_group holds entries that are not group names: %s" % ", ".join(bad[:_SHOW]))
    if not (np.all(np.isfinite(lat)) and np.all(np.isfinite(lon))):
        raise SplitRefusal(rule, "%d unit coordinates are not finite"
                           % int(np.sum(~np.isfinite(lat)) + np.sum(~np.isfinite(lon))),
                           fix="every unit has a representative point (EPSG:4326, plan 1.2)")
    if np.any(np.abs(lat) > 90.0):
        raise SplitRefusal(rule, "%d latitudes lie outside [-90, 90]" % int(np.sum(np.abs(lat) > 90.0)),
                           fix="pass latitude and longitude in degrees, in that order")
    if (grid_ix is None) != (grid_iy is None):
        raise SplitRefusal(rule, "grid_ix and grid_iy come together (both or neither)")
    names, codes = np.unique(groups, return_inverse=True)
    names = tuple(str(g) for g in names)
    codes = codes.astype(np.int64).ravel()
    units_by_group = {g: int(c) for g, c in zip(names, np.bincount(codes, minlength=len(names)).tolist())}
    hashes = {"unit_group": sha256_of_array(groups), "unit_lat": sha256_of_array(lat),
              "unit_lon": sha256_of_array(lon)}
    inputs: Dict[str, Any] = {"n_units": n, "units_by_group": units_by_group}
    if grid_ix is not None:
        ix = _int_indices(grid_ix, "grid_ix", n, rule)
        iy = _int_indices(grid_iy, "grid_iy", n, rule)
        hashes["grid_ix"], hashes["grid_iy"] = sha256_of_array(ix), sha256_of_array(iy)
        linked, shared = _linked_units_grid(codes, ix, iy)
        link_rule = GRID_INDICES
        inputs["link_rule"] = {"rule": link_rule,
                               "linked_when": "both grid indices differ by at most 1 (same cell or one "
                                              "of its 8 neighbours)"}
    else:
        linked, shared, spacing = _linked_units_spacing(codes, names, lat, lon, rule)
        link_rule = SPACING
        inputs["link_rule"] = {"rule": link_rule,
                               "linked_when": "great-circle distance at most sqrt(2) x the larger of the "
                                              "two groups' median nearest-unit spacing"}
        inputs["spacing_radians"] = spacing
    linked_n = _unit_counts_by_pair(linked, codes)
    shared_n = _unit_counts_by_pair(shared, codes)
    comps = _Components(len(names))
    pairs_out: List[Tuple[str, str, int]] = []
    pair_record: List[Dict[str, Any]] = []
    flags: List[str] = []
    done = set()
    for (a, b) in sorted(linked_n):
        lo, hi = min(a, b), max(a, b)
        if (lo, hi) in done:
            continue
        done.add((lo, hi))
        comps.union(lo, hi)
        ga, gb = names[lo], names[hi]
        smaller = lo if units_by_group[ga] <= units_by_group[gb] else hi
        other = hi if smaller == lo else lo
        count = linked_n.get((smaller, other), 0)
        pairs_out.append((ga, gb, count))
        flags.append("overlap:%s+%s:%d" % (ga, gb, count))
        pair_record.append({"groups": [ga, gb],
                            "linked_units": [linked_n.get((lo, hi), 0), linked_n.get((hi, lo), 0)],
                            "shared_position_units": [shared_n.get((lo, hi), 0), shared_n.get((hi, lo), 0)],
                            "only_touches": shared_n.get((lo, hi), 0) == 0})
    roots: Dict[int, List[str]] = {}
    for c, g in enumerate(names):
        roots.setdefault(comps.find(c), []).append(g)
    members = tuple(sorted(tuple(sorted(m)) for m in roots.values()))
    block_of = {g: i for i, block in enumerate(members) for g in block}
    inputs["linked_pairs"] = pair_record
    inputs["n_blocks"] = len(members)
    value = OverlapBlocks(block_of_group=dict(sorted(block_of.items())), members=members,
                          linked_pairs=tuple(pairs_out), link_rule=link_rule)
    _check_blocks(value, "derive_overlap_blocks")
    return make_derived(rule, value, inputs, array_hashes=hashes, flags=tuple(flags))


def _check_blocks(blocks: OverlapBlocks, what: str) -> None:
    """Blocks partition the groups; each block is sorted; blocks are sorted by their first member; the
    group -> block map agrees with the members."""
    rule = "R14"
    if not isinstance(blocks, OverlapBlocks):
        raise SplitRefusal(rule, "%s needs OverlapBlocks (derive_overlap_blocks(...).value), got %s"
                           % (what, type(blocks).__name__))
    seen: Dict[str, int] = {}
    for i, block in enumerate(blocks.members):
        if not block or tuple(sorted(block)) != tuple(block):
            raise SplitRefusal(rule, "block %d is empty or not sorted: %r" % (i, block))
        for g in block:
            if g in seen:
                raise SplitRefusal(rule, "group %r is in blocks %d and %d" % (g, seen[g], i))
            seen[g] = i
    firsts = [b[0] for b in blocks.members]
    if firsts != sorted(firsts):
        raise SplitRefusal(rule, "blocks are not sorted by their first group")
    if dict(blocks.block_of_group) != seen:
        raise SplitRefusal(rule, "block_of_group disagrees with the block members")


# Provenance: owner rulings E L2 rule 4 (a router drops the trees of its whole overlap block); plan 2.2
# R14 (router_groups is always a union of whole overlap blocks).
def block_of_group(blocks: OverlapBlocks, group: str) -> Tuple[str, ...]:
    """The overlap block of a group: every group whose trees a router of that group must drop, the
    group itself included, sorted by name.

    Rule: R14, G-DISJOINT. Most blocks hold one group. route/kinds.router_tree_columns takes this as
    its router_groups.
    Refuses: a group that is not a non-empty string; a group in no block.
    """
    rule = "R14"
    _check_blocks(blocks, "block_of_group")
    group = _name(group, "group", rule)
    if group not in blocks.block_of_group:
        raise SplitRefusal(rule, "group %r is in no overlap block" % group,
                           fix="derive the blocks over every group's candidate units")
    return tuple(blocks.members[blocks.block_of_group[group]])


# Provenance: plan 5 G-DISJOINT (LORO row: at run start G-DISJOINT recomputes the blocks from the static
# table and refuses a mismatch with derived.json).
def assert_blocks_equal(recorded: OverlapBlocks, recomputed: OverlapBlocks) -> None:
    """Refuse a run whose overlap blocks, recomputed from the static table at run start, differ from the
    blocks recorded in derived.json.

    Rule: G-DISJOINT. Compared as the block member sets and the link rule (the linked-pair unit counts
    are printed, not compared).
    Refuses: any difference, naming the groups whose block changed.
    """
    rule = "G-DISJOINT"
    _check_blocks(recorded, "assert_blocks_equal (recorded)")
    _check_blocks(recomputed, "assert_blocks_equal (recomputed)")
    if recorded.link_rule != recomputed.link_rule:
        raise SplitRefusal(rule, "overlap blocks were recorded with the %r rule but recompute with %r"
                           % (recorded.link_rule, recomputed.link_rule))
    if tuple(recorded.members) != tuple(recomputed.members):
        a = {g: tuple(recorded.members[i]) for g, i in recorded.block_of_group.items()}
        b = {g: tuple(recomputed.members[i]) for g, i in recomputed.block_of_group.items()}
        changed = sorted(g for g in set(a) | set(b) if a.get(g) != b.get(g))
        raise SplitRefusal(rule, "the overlap blocks recomputed from the static table differ from "
                           "derived.json for groups %s" % _show(changed),
                           fix="the static table changed since plan: re-run plan")


# ---------------------------------------------------------------------------------------------------
# Donor-only rivals: region folds (plan 4.6, C17; built for M8)
# Provenance: owner ruling D ("donor-only rivals are trained on region folds (10), and each group is
# scored by the fold model that never saw it"); plan 4.6, C17 (round-robin over sorted overlap blocks;
# a block stays in one fold). L3 deferred to M8: the plan's default (this rule) stands.
def rival_fold_of_group(blocks: OverlapBlocks, n_folds: int) -> Mapping[str, int]:
    """Each group's rival fold: round-robin over the overlap blocks, sorted by their first group name;
    every group takes its block's fold.

    Rule: plan 4.6, C17, G-NODRAW. The block at sorted position j goes to fold j mod n_folds, and every
    group of that block with it. Fold f's donor-only rival model is fitted on every group NOT in fold
    f; the groups of fold f are scored only by that model. Where every block holds one group, this is
    round-robin over the sorted names. n_folds is C17 (engine_constants.RIVAL_FOLDS).
    Returns {group: fold index}, in sorted group order.
    Refuses: n_folds < 2 or greater than the number of blocks.
    """
    rule = "C17"
    _check_blocks(blocks, "rival_fold_of_group")
    k = _count(n_folds, "n_folds", rule)
    if k < 2 or k > len(blocks.members):
        raise SplitRefusal(rule, "n_folds = %d, but it must lie in [2, %d] (the number of overlap blocks)"
                           % (k, len(blocks.members)),
                           fix="the fold count is the engine constant C17; a package with fewer blocks "
                               "cannot run the donor-only rivals")
    out = {g: j % k for j, block in enumerate(blocks.members) for g in block}
    return dict(sorted(out.items()))


# Provenance: plan 4.6 (fold f's model is fitted on the other folds' groups, bank units at or before the
# cut).
def rival_fold_training_groups(fold_of_group: Mapping[str, int], fold: int) -> Tuple[str, ...]:
    """The groups a fold's donor-only rival model is fitted on: every group outside the fold.

    Rule: plan 4.6, G-DISJOINT. Sorted groups whose fold differs from `fold`.
    Refuses: an unknown fold; an empty result.
    """
    rule = "C17"
    f = _count(fold, "fold", rule, low=0)
    folds = set(int(v) for v in fold_of_group.values())
    if f not in folds:
        raise SplitRefusal(rule, "fold %d is not one of the folds %s" % (f, sorted(folds)))
    out = tuple(sorted(g for g, v in fold_of_group.items() if int(v) != f))
    if not out:
        raise SplitRefusal(rule, "fold %d holds every group, so its model has no group to fit on" % f)
    return out


# Provenance: plan 4.6 and 5 G-DISJOINT (a donor-only prediction for a group comes only from the fold
# model that did not see it).
def assert_rival_source(prediction_group: np.ndarray, model_fold: np.ndarray,
                        fold_of_group: Mapping[str, int]) -> None:
    """Refuse any donor-only rival prediction, or Board B z value, that did not come from its group's
    own fold model.

    Rule: G-DISJOINT, plan 4.6. For every row, the fold of the model that made it equals the fold of
    the row's group (the one model that never saw that group or its overlap block). Called once on the
    predictions and once on the z rows.
    Refuses: mismatched lengths; a row group without a fold; any row whose model fold differs from its
    group's fold.
    """
    rule = "G-DISJOINT"
    groups = np.asarray(prediction_group, dtype=object)
    folds = np.asarray(model_fold)
    if groups.ndim != 1 or folds.ndim != 1 or len(groups) != len(folds):
        raise SplitRefusal(rule, "prediction_group and model_fold must be 1-D and of one length, got %s "
                           "and %s" % (groups.shape, folds.shape))
    if len(folds) and not np.issubdtype(folds.dtype, np.integer):
        raise SplitRefusal(rule, "model_fold must hold integer fold indices, got %s" % folds.dtype)
    names, codes = np.unique(groups, return_inverse=True)
    unknown = [g for g in names.tolist() if g not in fold_of_group]
    if unknown:
        raise SplitRefusal(rule, "rows of groups without a rival fold: %s" % _show(sorted(map(str, unknown))))
    want = np.array([int(fold_of_group[g]) for g in names.tolist()], dtype=np.int64)[codes.ravel()]
    wrong = np.flatnonzero(want != folds.astype(np.int64))
    if len(wrong):
        first = wrong[:_SHOW].tolist()
        raise SplitRefusal(rule, "%d rows came from another fold's model (first rows %s: groups %s, model "
                           "folds %s, own folds %s)" % (len(wrong), first, [groups[i] for i in first],
                                                        [int(folds[i]) for i in first],
                                                        [int(want[i]) for i in first]),
                           fix="score each group only with its own fold's model (rival_fold_of_group)")


__all__ = [
    "SplitRefusal", "LoroSplitSets", "LoroSplitDiff", "UnitCounts", "UnitLists", "OverlapBlocks",
    "GRID_INDICES", "SPACING", "LINK_RULES",
    "as_sorted_set", "loro_split_sets", "loro_split_differences", "groups_under_loro",
    "report_groupings", "candidate_units", "stride_pick", "evenly_spaced_subset", "scored_count_budget",
    "pick_unit_lists", "check_scored_units_loro", "unit_ids_hash", "assert_group_manifests",
    "region_cap_units", "derive_overlap_blocks", "block_of_group", "assert_blocks_equal",
    "rival_fold_of_group", "rival_fold_training_groups", "assert_rival_source",
]
