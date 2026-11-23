"""The unit, bank, batching, smoke and missing-value rules of plan 2.3 and 2.4 under leave one region
out: R18's two unit counts per group (bank and scored, with the event floor), R19 bank plan, R20
batching, R21 smoke plan, R30 missing-value flags.

SCIENCE bodies for the owner-approved signatures of the LORO additions (derive_r18_bank_count and
derive_r18_scored_count supersede derive_r18_unit_count; derive_r21_smoke_plan_loro supersedes
derive_r21_smoke_plan) and of the proposed derive_rules module (R19, R20, R30), with the decisions of
SIGNATURES_FOR_REVIEW.md (proposed defaults accepted: D13, D14, D15, D16, D17, D18) and the owner rulings
file, which wins where it differs (sections D and E: L1 K = 20, L2 companion rules 1-5). Each rule is a
pure function: it reads its arguments only, writes nothing, draws nothing, and returns a Derived.

The unit LISTS are split's (split.pick_unit_lists: bank by stride, scored as an evenly spaced subset of
the bank); the C16 budget formula is split.scored_count_budget. Derive adds what needs the donor labels
(the event floor) and records both counts.

Under leave one region out every group trains its own trees and is tested, so the donor rows of R19
and R30 are every group's BANK units at or before the cut (scope 'picked', D16 restated), and R18's
event rate reads every candidate unit of every group (scope 'all_donor_units', D14).
"""
# Provenance for the module: plan 2.3 R18-R21, 2.4 R30; C7, C13, C15, C16; pm25_adaptation.py:122-126
# (100 cells; 40 cells and 12 trees at smoke size), :621 (0-fill), :636-648 (bags, tree constants);
# adaptation.py:454-477 (correctors), :1149-1150, :1213 (the region budget); owner rulings D, E (leave
# one region out; L1 K = 20; L2 rules 1-3).

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Dict, List, Mapping, Tuple

import numpy as np

from treeroute import engine_constants as K
from treeroute import split as _split
from treeroute.fit import bank as _bank

from .derived import DeriveRefusal, borderline_flags, constants_used, make_derived
from .rules import FIT, GUARD, PICKED_SCOPE, _int, _value
from .shapes import Derived, RouterKind

ALL_UNITS_SCOPE = "all_donor_units"     # D14: the R18 event rate reads every candidate unit
PER_UNIT, REGION, NEIGHBOUR = (RouterKind.PER_UNIT.value, RouterKind.REGION.value,
                               RouterKind.NEIGHBOUR.value)
_SHOW = 5


def _kind(kind: Any, rule: str) -> RouterKind:
    try:
        return RouterKind(_value(kind))
    except ValueError:
        raise DeriveRefusal(rule, "unknown router kind %r" % (kind,), fix="pass R12's outcome")


def _group_counts(counts: Any, what: str, rule: str, low: int = 0) -> Dict[str, int]:
    if not isinstance(counts, Mapping) or not counts:
        raise DeriveRefusal(rule, "%s must be a non-empty {group: count} map" % what,
                            fix="pass one count per group")
    out: Dict[str, int] = {}
    for g in sorted(counts):
        if not isinstance(g, str) or not g:
            raise DeriveRefusal(rule, "%s is keyed by group names, got %r" % (what, g),
                                fix="key the counts by group name")
        n = _int(counts[g], "%s of %s" % (what, g), rule)
        if n < low:
            raise DeriveRefusal(rule, "%s of %s is %d, below %d" % (what, g, n, low),
                                fix="pass counts of at least %d" % low)
        out[g] = n
    return out


def _donor_rows(donor: Any, scope: str, rule: str, cut_kind: str = FIT) -> Tuple[np.ndarray, np.ndarray]:
    """(y, group of each row) of a label-only donor view (vault.DonorLabels) of the given scope at
    lead 0's cut of the given kind (the fit cut, the train end, unless a caller names the guard cut,
    the inner-fit end), checked: one entry per row, at least one row, finite labels."""
    for field in ("y", "group_of_row", "unit_scope", "cut_kind", "lead", "groups", "row_key_hash",
                  "times", "cut"):
        if not hasattr(donor, field):
            raise DeriveRefusal(rule, "the donor view has no %r (vault.DonorLabels is expected)" % field,
                                fix="pass LabelView.donor_labels(...)")
    if _value(donor.unit_scope) != scope:
        raise DeriveRefusal(rule, "the donor view's unit scope is %r; this rule reads %r"
                            % (_value(donor.unit_scope), scope),
                            fix="pass the donor labels of the scope the rule names (D14, D16)")
    if _value(donor.cut_kind) != cut_kind or _int(donor.lead, "the donor view's lead", rule) != 0:
        where = ("nowcast fit cut (the train end)" if cut_kind == FIT
                 else "nowcast %s cut (the inner-fit end)" % cut_kind)
        raise DeriveRefusal(rule, "the donor view is at lead %r, cut kind %r; this rule reads the %s"
                            % (donor.lead, _value(donor.cut_kind), where),
                            fix="pass the donor labels at lead 0's %s cut" % cut_kind)
    y = np.asarray(donor.y)
    g = np.asarray(donor.group_of_row, dtype=object)
    t = np.asarray(donor.times)
    if y.ndim != 1 or y.dtype.kind not in "iuf" or g.shape != y.shape or t.shape != y.shape:
        raise DeriveRefusal(rule, "the donor view holds y %s %s, groups %s, times %s; one entry per row "
                            "is expected" % (y.dtype, y.shape, g.shape, t.shape),
                            fix="build the donor view with LabelView.donor_labels")
    if y.size == 0:
        raise DeriveRefusal(rule, "the donor view holds no row", fix="check the units and the cut")
    if y.dtype.kind == "f" and not np.isfinite(y).all():
        raise DeriveRefusal(rule, "donor y holds %d non-finite values" % int((~np.isfinite(y)).sum()),
                            fix="the donor view holds valid labels only")
    if t.dtype.kind not in "iu" or (t > _int(donor.cut, "the donor view's cut", rule)).any():
        raise DeriveRefusal(rule, "donor rows must be whole steps or days at or before the view's cut",
                            fix="build the donor view with LabelView.donor_labels at the cut")
    return y, g


def _donor_record(donor: Any) -> Dict[str, Any]:
    return {"unit_scope": _value(donor.unit_scope), "cut": int(donor.cut),
            "cut_kind": _value(donor.cut_kind), "lead": int(donor.lead),
            "groups": len(tuple(donor.groups)), "rows": int(np.asarray(donor.y).size)}


# ===================================================================================================
# R18 (1) bank units
# Provenance: plan 2.3 R18 (1) bank units = the pre-LORO count; C7; pm25_adaptation.py:122-123 (100);
# region budget adaptation.py:1149-1150, 1213; L2 rule 1; D15 (thin = non-tree router columns).
def derive_r18_bank_count(kind: Any, season: Any, median_inner_fit_rows_per_unit: float,
                          available_units: Mapping[str, int], pooled_fit_rows_per_group: Mapping[str, int],
                          n_non_tree_router_columns: int) -> Derived:
    """Bank units per group: the units whose rows train the group's trees, fit its region router and
    pool its fallback router. The pre-LORO count, unchanged.

    Rule: R18 (1), C7, D15 (L2 rule 1). Per-unit: C7.bank_units_per_group (100); at steps finer than a
    month min(that, ceil(C7.submonthly_rows_per_group_year / steps per year)). Region:
    floor(C7.region_router_row_budget / the median valid inner-fit rows per unit), exact. Neighbour:
    every unit, and the rule value n is the median available units per group, rounded down. The same
    rule value applies to every group, capped at the group's available units ('capped:<group>'). A
    capped group is flagged 'thin:<group>' when its pooled fit rows fall below
    C10.thin_group_rows_per_router_column per NON-tree router column (D15). The event floor is not here;
    it applies to the scored count (derive_r18_scored_count).
    Returns Derived[(rule value n, {group: bank count})].
    Refuses: an unknown kind; an empty or malformed group map; a group without pooled fit rows; a
    median of 0 rows or less (region); a steps-per-year below 1; fewer than 1 non-tree column.
    """
    rule = "R18"
    k = _kind(kind, rule)
    avail = _group_counts(available_units, "available units", rule, low=1)
    pooled = _group_counts(pooled_fit_rows_per_group, "pooled fit rows", rule, low=0)
    missing = sorted(set(avail) - set(pooled))
    if missing:
        raise DeriveRefusal(rule, "no pooled fit rows for groups %s" % missing[:_SHOW],
                            fix="pass the pooled fit rows of every group")
    non_tree = _int(n_non_tree_router_columns, "n_non_tree_router_columns", rule)
    if non_tree < 1:
        raise DeriveRefusal(rule, "a router has at least one non-tree column (the intercept), got %d"
                            % non_tree, fix="count the non-tree router columns (D15)")
    inputs: Dict[str, Any] = {"kind": k.value, "available_units": avail}
    used = ["C7.bank_units_per_group", "C10.thin_group_rows_per_router_column"]
    if k == RouterKind.PER_UNIT:
        n = _int(K.BANK_UNITS_PER_GROUP, "C7.bank_units_per_group", rule)
        spy = getattr(season, "steps_per_year", None)
        if spy is not None:
            spy = _int(spy, "steps_per_year", rule)
            if spy < 1:
                raise DeriveRefusal(rule, "steps_per_year is %d" % spy, fix="pass R2's outcome")
            if spy > K.MONTHS_PER_YEAR:
                n = min(n, -(-_int(K.SUBMONTHLY_ROWS_PER_GROUP_YEAR, "C7", rule) // spy))
                used.append("C7.submonthly_rows_per_group_year")
        inputs["steps_per_year"] = spy
    elif k == RouterKind.REGION:
        median = float(median_inner_fit_rows_per_unit)
        if not math.isfinite(median) or median <= 0:
            raise DeriveRefusal(rule, "the median valid inner-fit rows per unit is %r; the region rule "
                                "divides the row budget by it" % (median_inner_fit_rows_per_unit,),
                                fix="check the valid rows per candidate unit (R12)")
        budget = _int(K.REGION_ROUTER_ROW_BUDGET, "C7.region_router_row_budget", rule)
        n = math.floor(Fraction(budget) / Fraction(repr(median)))
        inputs["median_inner_fit_rows_per_unit"] = median
        used.append("C7.region_router_row_budget")
    else:
        n = int(math.floor(float(np.median(list(avail.values())))))
        inputs["rule_value_from"] = "the median available units per group, rounded down"
    if n < 1:
        raise DeriveRefusal(rule, "the bank-count rule value is %d" % n,
                            fix="the region median exceeds the row budget; check the valid rows")
    bank: Dict[str, int] = {}
    flags: List[str] = []
    for g, a in avail.items():
        bank[g] = a if k == RouterKind.NEIGHBOUR else min(n, a)
        if k != RouterKind.NEIGHBOUR and a < n:
            flags.append("capped:%s" % g)
            if pooled[g] < K.THIN_GROUP_ROWS_PER_ROUTER_COLUMN * non_tree:
                flags.append("thin:%s" % g)
    inputs.update({"rule_value": n, "pooled_fit_rows_per_group": pooled,
                   "n_non_tree_router_columns": non_tree, "constants": constants_used(*used)})
    return make_derived(rule, (n, bank), inputs, flags=tuple(flags))


# ===================================================================================================
# R18 (2) scored units
# Provenance: plan 2.3 R18 (2); C16 (owner rulings E, L1: one engine constant K = 20); D13 (event floor:
# count >= ceil(10 / (test rows per unit x rate))); D14 (the rate from every labelled row of every group at
# or before the train end, before any pick); plan R33 (event = y strictly above the q90).
@dataclass(frozen=True)
class EventRate:
    """NOT an approved shape (engine helper, flagged for the owner): the donor event rate R18's floor
    reads, with the donor view it came from. donor_event_rate gives (events, rows, q90) from a label
    array; a caller that cannot hold every candidate unit's labels at once (the largest packages) may
    stream the same three numbers and record how in `source`."""
    events: int
    rows: int
    q90: float
    unit_scope: str
    cut: int
    cut_kind: str
    lead: int
    groups: int
    row_key_hash: str
    source: str


def donor_event_rate(y: np.ndarray) -> Tuple[int, int, float]:
    """(events, rows, q90): events are the rows strictly above the rows' own 90th percentile
    (C7.event_quantile, numpy's default linear interpolation, as D62 reads percentiles)."""
    arr = np.asarray(y, dtype=np.float64)
    q = float(np.percentile(arr, float(K.EVENT_QUANTILE) * 100.0))
    return int((arr > q).sum()), int(arr.size), q


def derive_r18_scored_count(kind: Any, rule_value: int, bank_by_group: Mapping[str, int],
                            available_units: Mapping[str, int], k_group_equivalents: int,
                            donor_all: Any, test_window_rows_per_unit: int) -> Derived:
    """Scored units per group: max(10, floor(K x n / G)), capped at the group's bank units, with the
    event floor on top.

    Rule: R18 (2), C16 (owner rulings E, L1), D13, D14. The event rate is the share of donor_all's rows
    strictly above their 90th percentile (donor_event_rate): every labelled row of every group's
    candidate units at the nowcast fit cut (scope 'all_donor_units', D14). The counts follow from the
    rate by scored_counts_at_event_rate, which documents the budget, the floor and the flags.
    Returns Derived[UnitCounts] (split's shape).
    Refuses: donor_all of another scope, not at lead 0's fit cut, with no row or a non-finite label;
    and whatever scored_counts_at_event_rate refuses.
    """
    rule = "R18"
    y, _ = _donor_rows(donor_all, ALL_UNITS_SCOPE, rule)
    events, rows, q90 = donor_event_rate(y)
    rate = EventRate(events=events, rows=rows, q90=q90, unit_scope=_value(donor_all.unit_scope),
                     cut=int(donor_all.cut), cut_kind=_value(donor_all.cut_kind), lead=int(donor_all.lead),
                     groups=len(tuple(donor_all.groups)), row_key_hash=str(donor_all.row_key_hash),
                     source="donor_event_rate over the label-only donor view")
    return scored_counts_at_event_rate(kind, rule_value, bank_by_group, available_units,
                                       k_group_equivalents, rate, test_window_rows_per_unit)


def scored_counts_at_event_rate(kind: Any, rule_value: int, bank_by_group: Mapping[str, int],
                                available_units: Mapping[str, int], k_group_equivalents: int,
                                rate: EventRate, test_window_rows_per_unit: int) -> Derived:
    """R18 (2) from a donor event rate: the C16 budget, then the event floor.

    Rule: R18 (2), C16, D13, D14 (called by derive_r18_scored_count; NOT an approved signature, flagged).
    G = the number of groups (the keys of bank_by_group); the base count is split.scored_count_budget:
    max(C16.scored_units_min, floor(K x n / G)), rounded down, capped at the bank count ('minimum:<group>'
    where the minimum binds, 'scored_capped:<group>'). K is the engine constant C16 (never a package
    value or a flag: any other value is refused). Then the event floor: each group should expect at
    least C7.event_floor_per_group test-window events at the donor event rate, so the count is raised
    to ceil(floor / (test_window_rows_per_unit x rate)) where it is lower (exact arithmetic), capped at
    the group's available units ('event_floor:<group>'; 'event_floor_capped:<group>' where even every
    unit falls short). A rate of 0 (the q90 equals the maximum, as when R33 gives NaN) skips the floor,
    flagged 'event_floor_skipped:rate_zero'. A scored count lifted above its bank count raises the
    bank count to match ('bank_raised:<group>'); both stay within the available units. The scored
    units are taken later as an evenly spaced subset of the bank units (split.pick_unit_lists).
    Returns Derived[UnitCounts] (split's shape); inputs record K, n, G, the event rate with its q90,
    counts and source, the floor count and the donor rows' row-key hash.
    Refuses: an unknown kind; K < 1 or K other than C16's; n < 1; bank and available maps over
    different groups, or a bank count above its available units; a rate not from scope
    'all_donor_units' at lead 0's fit cut, with no row or more events than rows; test rows per unit < 1.
    """
    rule = "R18"
    k = _kind(kind, rule)
    kk = _int(k_group_equivalents, "k_group_equivalents (K)", rule)
    if kk < 1 or kk != K.K_GROUP_EQUIVALENTS:
        raise DeriveRefusal(rule, "K = %d; the scored-unit budget takes the engine constant "
                            "C16.k_group_equivalents = %d, never a package value or a flag"
                            % (kk, K.K_GROUP_EQUIVALENTS), fix="pass engine_constants.K_GROUP_EQUIVALENTS")
    n = _int(rule_value, "rule_value (n)", rule)
    if n < 1:
        raise DeriveRefusal(rule, "rule_value n = %d is below 1" % n, fix="pass R18 (1)'s rule value")
    bank = _group_counts(bank_by_group, "bank counts", rule, low=1)
    avail = _group_counts(available_units, "available units", rule, low=1)
    if set(bank) != set(avail):
        raise DeriveRefusal(rule, "bank counts name %d groups, available units %d: the maps differ"
                            % (len(bank), len(avail)), fix="pass both maps over every group")
    over = sorted(g for g in bank if bank[g] > avail[g])
    if over:
        raise DeriveRefusal(rule, "bank counts above the available units for %s" % over[:_SHOW],
                            fix="cap the bank counts (derive_r18_bank_count)")
    test_rows = _int(test_window_rows_per_unit, "test_window_rows_per_unit", rule)
    if test_rows < 1:
        raise DeriveRefusal(rule, "test_window_rows_per_unit is %d" % test_rows,
                            fix="pass the census rows per unit in the test window")
    if (_value(rate.unit_scope) != ALL_UNITS_SCOPE or _value(rate.cut_kind) != FIT
            or _int(rate.lead, "the rate's lead", rule) != 0):
        raise DeriveRefusal(rule, "the event rate comes from scope %r at lead %r, cut kind %r; D14 reads "
                            "every candidate unit ('%s') at the nowcast fit cut"
                            % (_value(rate.unit_scope), rate.lead, _value(rate.cut_kind), ALL_UNITS_SCOPE),
                            fix="pass the donor labels of every candidate unit at lead 0's fit cut")
    events, n_rows = _int(rate.events, "events", rule), _int(rate.rows, "rows", rule)
    if n_rows < 1 or not 0 <= events <= n_rows:
        raise DeriveRefusal(rule, "the event rate holds %d events over %d rows" % (events, n_rows),
                            fix="pass the donor rows' event count and row count")
    base, split_flags = _split.scored_count_budget(n, bank, kk)
    flags: List[str] = list(split_flags)
    floor_units = None
    if events == 0:
        flags.append("event_floor_skipped:rate_zero")
    else:
        floor_n = _int(K.EVENT_FLOOR_PER_GROUP, "C7.event_floor_per_group", rule)
        floor_units = -(-(floor_n * n_rows) // (test_rows * events))       # ceil(floor / (rows x rate))
    scored: Dict[str, int] = {}
    bank_out: Dict[str, int] = {}
    for g in sorted(bank):
        s = base[g]
        if floor_units is not None and floor_units > s:
            s = min(floor_units, avail[g])
            flags.append("event_floor:%s" % g)
            if floor_units > avail[g]:
                flags.append("event_floor_capped:%s" % g)
        b = bank[g]
        if s > b:
            b = s
            flags.append("bank_raised:%s" % g)
        scored[g], bank_out[g] = s, b
    counts = _split.UnitCounts(rule_value=n, k_group_equivalents=kk, n_groups=len(bank),
                               bank_by_group=bank_out, scored_by_group=scored)
    inputs = {"kind": k.value, "k_group_equivalents": kk, "rule_value": n, "n_groups": len(bank),
              "budget_before_floor": (kk * n) // len(bank),
              "event_rate": {"events": events, "rows": n_rows, "rate": events / float(n_rows),
                             "q90": float(rate.q90), "source": str(rate.source),
                             "definition": "y strictly above the donor rows' q90 (D14)"},
              "event_floor_units": floor_units, "test_window_rows_per_unit": test_rows,
              "donor_all": {"unit_scope": _value(rate.unit_scope), "cut": int(rate.cut),
                            "cut_kind": _value(rate.cut_kind), "lead": int(rate.lead),
                            "groups": int(rate.groups), "rows": n_rows},
              "scored_total": sum(scored.values()), "bank_total": sum(bank_out.values()),
              "constants": constants_used("C16.k_group_equivalents", "C16.scored_units_min",
                                          "C7.event_floor_per_group", "C7.event_quantile")}
    return make_derived(rule, counts, inputs, {"donor_all_row_key_hash": str(rate.row_key_hash)},
                        flags=tuple(flags))


# ===================================================================================================
# R19 bank plan
# Provenance: plan 2.3 R19; C13; pm25_adaptation.py:636-648 (bag max(30, int(0.5 n)); depth 8, leaf 5,
# max_features 0.1); adaptation.py:454-477 (correctors depth 6, leaf 10); D47 (name seeds), D50 (expected
# held-out share), D52 (50 out-of-bag rows); LORO: every group trains its own trees (owner ruling D).
SEED_FORMULA = ("first 4 bytes, big-endian, of SHA-256 of '<group>|<tree number>|<role>' with role "
                "bag, tree or corrector (D47; fit.bank.name_seed)")


def derive_r19_bank_plan(donor: Any, smoke: bool) -> Derived:
    """The bank recipe as data: trees per group, bag size per group, tree and corrector constants,
    and the seed formula.

    Rule: R19 (C13, D47, D50, D52). Under leave one region out EVERY group trains its own trees:
    C13.trees_per_group per group (C13.smoke_trees_per_group in smoke, R21), each tree on a bag of
    max(C13.bag_min_rows, int(C13.bag_fraction x the group's rows)) drawn with replacement
    (fit.bank.bag_size, the recipe's own function); depth, leaf, max_features, criterion and dtype
    from C13. Three seeds per tree from the group NAME (the seed formula). Correctors out of bag, with
    the expected held-out share per group from the bag size (fit.bank.expected_oob_share, D50), and no
    corrector for a tree with fewer than C13.corrector_min_oob_rows held-out rows (D52). Groups in
    sorted order. Rows per group are counted from `donor`, the rows the bank will see: every group's
    BANK units at the nowcast fit cut (scope 'picked', D16); its row-key hash is recorded.
    Returns Derived[{'trees_per_group', 'bank_trees', 'groups', 'rows_per_group', 'bag_size',
    'expected_oob_share', 'tree', 'corrector', 'seed_formula'}].
    Refuses: a donor view whose scope is not 'picked', not at lead 0's fit cut, with no row or a
    non-finite label; a listed group with 0 rows; a row whose group is not listed.
    """
    return _bank_plan(donor, smoke, FIT)


# Provenance: owner rulings E, L6 option b (A7.inner_cut_bank_refit: for the inner decision the bank and
# the correctors are refit at the INNER cut); plan 2.3 R19. NOT an approved signature (flagged for the
# owner): the approved derive_r19_bank_plan reads the nowcast fit cut only, so the inner-cut bank had
# no plan-time record for G-LOCK to pin.
def derive_r19_inner_cut_bank_plan(donor: Any, smoke: bool) -> Derived:
    """The inner-cut bank's recipe as data (L6 b): R19's record built from the donor rows that bank
    will see, every group's BANK units at lead 0's GUARD cut (the inner-fit end), scope 'picked'.

    Rule: R19 (C13, D47, D50, D52) under A7.inner_cut_bank_refit. Same trees, bag rule, tree and
    corrector constants and seed formula as derive_r19_bank_plan; the rows per group, bag sizes and
    expected held-out shares come from the inner cut's rows, and the donor view's row-key hash is
    recorded, so plan pins the inner-cut bank as it pins the nowcast one.
    Returns Derived[same keys as derive_r19_bank_plan].
    Refuses: as derive_r19_bank_plan, with the view at lead 0's guard cut instead of its fit cut.
    """
    return _bank_plan(donor, smoke, GUARD)


def _bank_plan(donor: Any, smoke: bool, cut_kind: str) -> Derived:
    rule = "R19"
    _, g = _donor_rows(donor, PICKED_SCOPE, rule, cut_kind)
    groups = tuple(sorted(donor.groups))
    if not groups or len(set(groups)) != len(groups):
        raise DeriveRefusal(rule, "the donor view lists no groups or a group twice",
                            fix="build the donor view over every group's bank units")
    names, counts = np.unique(g, return_counts=True)
    stray = sorted(set(names.tolist()) - set(groups))
    if stray:
        raise DeriveRefusal(rule, "donor rows of groups the view does not list: %s" % stray[:_SHOW],
                            fix="build the donor view with LabelView.donor_labels")
    rows = {str(n): int(c) for n, c in zip(names.tolist(), counts.tolist())}
    empty = [x for x in groups if rows.get(x, 0) == 0]
    if empty:
        raise DeriveRefusal(rule, "%d groups have no donor row at the cut, e.g. %s: a group with no row "
                            "cannot train its trees" % (len(empty), empty[:_SHOW]),
                            fix="exclude the group in split.yaml, with its reason, or check its units")
    trees = int(K.SMOKE_TREES_PER_GROUP if smoke else K.TREES_PER_GROUP)
    bag = {x: _bank.bag_size(rows[x]) for x in groups}
    oob = {x: _bank.expected_oob_share(rows[x], bag[x]) for x in groups}
    value = {"trees_per_group": trees, "bank_trees": trees * len(groups), "groups": list(groups),
             "rows_per_group": {x: rows[x] for x in groups}, "bag_size": bag, "expected_oob_share": oob,
             "tree": {"max_depth": int(K.TREE_MAX_DEPTH), "min_leaf": int(K.TREE_MIN_LEAF),
                      "max_features": float(K.TREE_MAX_FEATURES), "criterion": str(K.TREE_CRITERION),
                      "dtype": str(K.TREE_DTYPE), "bag_min_rows": int(K.BAG_MIN_ROWS),
                      "bag_fraction": float(K.BAG_FRACTION),
                      "bag_with_replacement": bool(K.BAG_WITH_REPLACEMENT)},
             "corrector": {"max_depth": int(K.CORRECTOR_MAX_DEPTH), "min_leaf": int(K.CORRECTOR_MIN_LEAF),
                           "min_oob_rows": int(K.CORRECTOR_MIN_OOB_ROWS), "fit_on": "out-of-bag rows"},
             "seed_formula": SEED_FORMULA}
    names_used = ("A7.inner_cut_bank_refit",) if cut_kind == GUARD else ()
    inputs = {"donor": _donor_record(donor), "smoke": bool(smoke),
              "bank": ("the inner-cut bank (L6 b): rows at or before the inner-fit end" if cut_kind == GUARD
                       else "the nowcast bank: rows at or before the train end"),
              "constants": constants_used(
                  *names_used,
                  "C13.smoke_trees_per_group" if smoke else "C13.trees_per_group", "C13.bag_min_rows",
                  "C13.bag_fraction", "C13.bag_with_replacement", "C13.tree_max_depth",
                  "C13.tree_min_leaf", "C13.tree_max_features", "C13.tree_criterion", "C13.tree_dtype",
                  "C13.corrector_max_depth", "C13.corrector_min_leaf", "C13.corrector_min_oob_rows")}
    return make_derived(rule, value, inputs, {"donor_row_key_hash": str(donor.row_key_hash)})


# ===================================================================================================
# R20 batching
# Provenance: plan 2.3 R20 (LORO: tables per group, every row through all trees once, a column mask per
# router); plan 4.5 speedup 1 (row key); C14 (the row block).
def derive_r20_batching(is_events: bool, test_groups: Tuple[str, ...]) -> Derived:
    """Matrix batching: tree-answer tables per group, in row blocks, keyed by row.

    Rule: R20 (4.5). Under leave one region out every group is tested, so the caller passes EVERY
    group (the argument keeps its approved name) and the tables are built per group, in that sorted
    batch order, in row blocks of C14.table_row_block_rows. Each row goes through ALL the bank's trees
    once, its own group's included; each router drops its own block's column blocks (R14), so one
    table per kind (plain, corrector, placebo) serves every group. The row key is unit + step for
    grids and unit + event date + issue date for events (event features depend on the issue date).
    Batching changes hours, never a number. The extra rows of a per-unit package's fallback region
    routers (every bank unit at or before the cut of a group with a fallback unit, L2 rule 3) are
    listed by derive_all beside this record, because they need the unit lists.
    Returns Derived[{'row_key', 'batch_order', 'tables', 'row_block_rows'}].
    Refuses: groups that are not distinct non-empty names, or none.
    """
    rule = "R20"
    if isinstance(test_groups, str) or not isinstance(test_groups, (tuple, list)) or not test_groups:
        raise DeriveRefusal(rule, "the groups must be a non-empty tuple of names, got %r" % (test_groups,),
                            fix="pass every group (split.groups_under_loro)")
    names = tuple(test_groups)
    if any(not isinstance(x, str) or not x for x in names) or len(set(names)) != len(names):
        raise DeriveRefusal(rule, "the groups must be distinct non-empty names", fix="pass a set")
    key = ["unit", "event_date", "issue_date"] if is_events else ["unit", "step"]
    value = {"row_key": key, "batch_order": sorted(names), "tables": ["plain", "corrector", "placebo"],
             "row_block_rows": int(K.TABLE_ROW_BLOCK_ROWS)}
    inputs = {"is_events": bool(is_events), "groups": len(names),
              "constants": constants_used("C14.table_row_block_rows")}
    return make_derived(rule, value, inputs)


# ===================================================================================================
# R21 smoke plan
# Provenance: plan 2.3 R21 (40 units, 12 trees; pm25_adaptation.py:122-126); LORO: the first 4 groups
# (the old 2 donor + 2 test), all trained; tested when they have scored units. Supersedes derive_r21_smoke_plan.
def derive_r21_smoke_plan_loro(groups: Tuple[str, ...]) -> Derived:
    """The fixed smoke plan under LORO: the first 4 groups in sorted order, 40 units per group (all
    scored where the group has scored units), 12 trees per group.

    Rule: R21 (C13 smoke constants, C15). Engine constants, never a flag: the first C13.smoke_groups
    groups in sorted order (all groups when there are fewer), C13.smoke_units_per_group units per
    group, C13.smoke_trees_per_group trees per group. Every smoke group is trained, and each router
    sees the trees of the other smoke groups outside its overlap block. A grid smoke group is always
    tested. A table smoke group with no test-marked row (V6 b: donor-only, derive/table.py
    'R18:donor_only') is trained only; 'scored_per_group' is then the plan's cap, not a count of
    scored units (the run's scored lists hold the counts).
    Plumbing only: smoke deltas carry no sign information.
    Returns Derived[{'groups', 'units_per_group', 'scored_per_group', 'trees_per_group'}].
    Refuses: groups that are not distinct non-empty names; fewer than C15.min_groups groups.
    """
    rule = "R21"
    if isinstance(groups, str) or not isinstance(groups, (tuple, list)):
        raise DeriveRefusal(rule, "groups must be a tuple of names, got %r" % (groups,),
                            fix="pass split.groups_under_loro")
    names = tuple(groups)
    if any(not isinstance(x, str) or not x for x in names) or len(set(names)) != len(names):
        raise DeriveRefusal(rule, "the groups must be distinct non-empty names", fix="pass a set")
    if len(names) < K.MIN_GROUPS:
        raise DeriveRefusal(rule, "the smoke plan needs at least %d groups, got %d"
                            % (K.MIN_GROUPS, len(names)),
                            fix="G-SUPPORT refuses a package with fewer groups")
    first = sorted(names)[:int(K.SMOKE_GROUPS)]
    units = int(K.SMOKE_UNITS_PER_GROUP)
    value = {"groups": first, "units_per_group": units, "scored_per_group": units,
             "trees_per_group": int(K.SMOKE_TREES_PER_GROUP)}
    inputs = {"groups_available": len(names),
              "constants": constants_used("C13.smoke_groups", "C13.smoke_units_per_group",
                                          "C13.smoke_trees_per_group", "C15.min_groups")}
    flags = ("fewer_groups_than_smoke_plan",) if len(names) < K.SMOKE_GROUPS else ()
    return make_derived(rule, value, inputs, flags=flags)


# ===================================================================================================
# R30 missing-value flags
def _share(value: Any, what: str, rule: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise DeriveRefusal(rule, "%s must be a number, got %r" % (what, value), fix="pass shares")
    x = float(value)
    if not (0.0 <= x <= 1.0):
        raise DeriveRefusal(rule, "%s is %r, outside [0, 1]" % (what, value), fix="pass shares")
    return x


# Provenance: plan 2.4 R30, 1.4, 5 G-MISSING; 9.1 item 2f; D17 (the 25% threshold, C15, signed as
# proposed); D18 ("vanishes" = 100% missing over ALL groups' rows of that test year); zero-fill as today
# at pm25_adaptation.py:621.
def derive_r30_missing_flags(shares: Any, absent_groups: Mapping[str, Mapping[str, str]]) -> Derived:
    """Missing-value flags: a column over 25% missing in donor training rows, or vanishing in a test
    year, needs an explicit verdict in the Q34 review.

    Rule: R30 (C15, D17, D18). Tree features are 0-filled (today's rule). Per column the filled share
    (missing before the fill) and the share of real zeros on the donor training rows are recorded. A
    column is FLAGGED, not banned, when it is more than C15.missing_flag_share missing on the donor
    training rows ('over_threshold'), or when it is 100% missing over every group's rows of a test year
    ('vanishes:<year>', D18). It then needs keep with evidence or ban (G-MISSING enforces);
    keep_unreviewed is not enough. Groups a store declares absent get NaN and are counted in the shares;
    their declarations are recorded per column. The donor training rows are one plan-time donor view
    (every group's bank units at the nowcast fit cut, D16); MissingShares carries its row-key hash,
    which is recorded.
    Returns Derived[{column: reasons}] (flagged columns only; reasons in the order over_threshold, then
    vanishes:<year> by year); margins: each column's missing share against C15.missing_flag_share,
    keyed '<column>' (borderline flags 'borderline:<column>').
    Refuses: a share outside [0, 1] or not a number; zero shares for a column without a missing share;
    a test-year share of a column without a missing share; a donor scope other than 'picked'; absent
    groups that are not {column: {group: reason}}.
    """
    rule = "R30"
    for field in ("donor_row_key_hash", "donor_unit_scope", "donor_training_missing_share",
                  "donor_training_zero_share", "test_year_missing_share"):
        if not hasattr(shares, field):
            raise DeriveRefusal(rule, "the shares have no %r (MissingShares is expected)" % field,
                                fix="pass the column reader's MissingShares")
    if _value(shares.donor_unit_scope) != PICKED_SCOPE:
        raise DeriveRefusal(rule, "the shares were measured on scope %r; R30 reads the donor training "
                            "rows of the picked (bank) units (D16)" % (_value(shares.donor_unit_scope),),
                            fix="measure the shares over LabelView.donor_labels of the bank units")
    missing = {c: _share(v, "the missing share of %s" % c, rule)
               for c, v in sorted(shares.donor_training_missing_share.items())}
    zeros = {c: _share(v, "the zero share of %s" % c, rule)
             for c, v in sorted(shares.donor_training_zero_share.items())}
    stray = sorted(set(zeros) - set(missing))
    if stray:
        raise DeriveRefusal(rule, "zero shares for columns without a missing share: %s" % stray[:_SHOW],
                            fix="measure both shares over the same columns")
    by_year: Dict[str, Dict[int, float]] = {}
    for key, v in shares.test_year_missing_share.items():
        try:
            column, year = key
        except (TypeError, ValueError):
            raise DeriveRefusal(rule, "test-year shares are keyed (column, year), got %r" % (key,),
                                fix="pass {(column, test year): share}")
        if column not in missing:
            raise DeriveRefusal(rule, "a test-year share of %r, which has no donor missing share"
                                % (column,), fix="measure every column on both row sets")
        by_year.setdefault(column, {})[_int(year, "the year of %r" % (key,), rule)] = _share(
            v, "the %s missing share of %s" % (year, column), rule)
    if not isinstance(absent_groups, Mapping):
        raise DeriveRefusal(rule, "absent groups must be {column: {group: reason}}",
                            fix="pass each store's absent_groups")
    absent: Dict[str, List[str]] = {}
    for column, groups in sorted(absent_groups.items()):
        if not isinstance(groups, Mapping):
            raise DeriveRefusal(rule, "absent groups of %r must be {group: reason}" % (column,),
                                fix="pass each store's absent_groups")
        if groups:
            absent[column] = sorted(groups)
    threshold = float(K.MISSING_FLAG_SHARE)
    value: Dict[str, Tuple[str, ...]] = {}
    margins: Dict[str, float] = {}
    flags: List[str] = []
    for column, share in missing.items():
        reasons: List[str] = []
        if share > threshold:
            reasons.append("over_threshold")
        reasons.extend("vanishes:%d" % year for year, s in sorted(by_year.get(column, {}).items())
                       if s == 1.0)
        m, b = borderline_flags(share, {column: threshold})
        margins.update(m)
        flags.extend(b)
        if reasons:
            value[column] = tuple(reasons)
            flags.append("flagged:%s" % column)
    inputs = {"donor_unit_scope": _value(shares.donor_unit_scope), "columns": len(missing),
              "filled_share": missing, "real_zero_share": zeros,
              "test_year_missing_share": {c: {str(y): s for y, s in sorted(v.items())}
                                          for c, v in sorted(by_year.items())},
              "absent_groups": absent,
              "vanish_rule": "100% missing over every group's rows of the test year (D18)",
              "constants": constants_used("C15.missing_flag_share")}
    return make_derived(rule, value, inputs, {"donor_row_key_hash": str(shares.donor_row_key_hash)},
                        margins, tuple(flags))
