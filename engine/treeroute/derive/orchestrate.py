"""derive_all: every plan-time rule in dependency order, under leave one region out (plan Section 2,
4.1 steps 1-2).

SCIENCE orchestration for the owner-approved derive_all signature (proposed derive_rules module), with
the LORO additions and the owner rulings file (sections A-F), which wins where it differs. derive_all
reads the package and the target table, writes nothing, and returns {entry name: Derived}, the content
of derived.json (derive.write_derived_json writes it once into a run folder).

Order (the approved one, with the LORO rules in place of the ones they supersede): R1, R2, R8 over the
kept columns, the R8-covers-the-kept-columns guard and the epoch-column stand-in, R4 (owner ruling J5:
the first data year is the latest first year of the driver stores holding a lag source, and a declared
'lag k=<k> unit=<unit>' operation's look-back counts on top of R8's lag; _r04_entry), the groups
(split.groups_under_loro), R3 over the joined rows of every group (F2), R5, R6, R7, R10, R11, R9, the
candidate units (split.candidate_units), R12, R13, R14, R17, R18 (bank count, scored count with the
event floor, and split.pick_unit_lists), the region router's fit budget (region kind: 'R14:region_fit',
L2 rule 2), R19 (and, under A7.inner_cut_bank_refit, the inner-cut bank's plan 'R19:inner_cut', L6 b),
R20 (with the fallback-router rows of L2 rule 3), R21, R22, R23 per lead cut with the rebuilt-rows
guard, R28, R30. The first rule that refuses stops the whole derivation.

Guards inside:
  - check_r08_covers_kept_columns (rules): R4 reads R8's lags over exactly the kept columns;
  - the epoch-column stand-in (G-EPOCH, until validators.check_g_epoch exists): R8 gives an epoch
    column no lag and R9 freezes only 'freeze' columns, so a kept epoch column without a 'freeze'
    verdict would enter unlagged and unfrozen; derive_all refuses it;
  - _check_r23_plan_time: every R23 entry is re-checked with check_r23_matches_run, the run's own
    check, against donor rows REBUILT at its lead's fit cut without donor_labels
    (_PlanLabels.rebuild_donor_rows: the bank lists checked against the target's groups, validity,
    and timing.label_usable per step), so the plan-time view's rows and c are compared with an
    independent selection. It stays a plan-time stand-in: the run's own side (layer.c_for_cut on
    FitContext.donor_rows) is not built yet, and the run will call the same check on it.

Labels. The approved contract hands target.y ONLY to a vault.LabelView. The label vault (plan 4.2
labels/vault.py, M2) is not built yet, so _PlanLabels below stands in for its two plan-time reads,
validity and donor_labels, with the approved semantics (validity never a value; donor rows valid, at or
before the cut, with their own label window ended by then, timing's rule; no cut at or after the test
window). It is the one place derive_all touches target.y. OWNER: swap it for LabelView when the vault
lands (the method names and the DonorLabels shape are the approved ones); until then G-LOCK holds by
this module's structure, not by the vault's.

The column reader (share_reader) is the approved MissingShareReader (measure, R30) with two more
methods this module calls, flagged for the owner because the approved protocol has one method:
  - drivers_present(unit_ids, group_ids, time_columns, columns) -> bool per target row: F2's joined
    rows (every driver store holding one of the columns has a row for the unit at that step; a
    declared-absent group counts as present). R4 asks it too, once per store catalog of the lag
    sources, for each store's first year (owner ruling J5, _r04_first_data_year);
  - content_epochs(column) -> the column's content epochs as Day ordinals, called only for 'freeze'
    columns (R9).

Row counts. R12's h and R18's region bank count follow the plan's wording: VALID rows from Y0 to the
inner-fit end (validity alone). The candidates follow split.candidate_units' approved contract (a valid
label at or before the train end); a candidate whose only valid labels have windows ending after the
train end becomes a bank unit that contributes no donor row (every donor view and fit-row count
applies the label-window rule itself), so validity cannot leak a label there. The router FIT-row
counts, the region router's fit budget and the fallback units, use the rows a router fitted at that cut
may read: valid labels from Y0 to the cut whose own window has ended by the cut (timing.label_usable,
D26), as FitContext.router_rows will hand them out.

Real packages (reported). derive_all does not run on any of the declared real packages today, for two
reasons: (1) its first step, the closed world (io.apply_verdicts), refuses G-CLOSED on every one,
because their ban.yaml files hold forced bans only until the Q34 review writes verdicts (177 to 510
columns per package have none); (2) the event-rate donor view reads every candidate unit's labels at
the train end, several hundred million rows on the largest packages, beyond this machine's memory as
whole arrays (a streaming vault view is needed). derive_all is exercised on synthetic packages only.
tests/test_derive_acceptance.py re-orchestrates the RULES itself on the real stores (it does not call
derive_all past its closed-world refusal, which it reports).

Events (an irregular target cadence) are milestone M8: derive_all raises NotImplementedError after R2.
Overlap blocks (split.derive_overlap_blocks) need the static table, which this signature does not
carry: the caller records them beside derived.json.
"""
# Provenance for the module: plan Section 2, 4.1 steps 1-2, 5 G-LOCK; owner rulings D, E (leave one
# region out), F (F2 joined rows; F8 declared-absent groups; F1 is the history block's, not derive's), J5
# (R4 from the driver stores' first years).

import re
from types import SimpleNamespace
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from treeroute import engine_constants as K
from treeroute import split as _split
from treeroute import timing
from treeroute.io import steps as _steps
from treeroute.io.apply import apply_verdicts

from . import router_rules as RR
from . import rules as R
from . import unit_rules as UR
from .derived import DeriveRefusal, make_derived, sha256_of_array, sha256_of_json
from .shapes import CutKind, DonorLabels, Link, RouterKind

IRREGULAR = "irregular"
ENTERING_ROLES = ("driver", "engineered", "router_context")
KEY_ROLES = ("key_unit", "key_group", "key_time")
TARGET_ROLE = "target"
_SHOW = 5


# ---------------------------------------------------------------------------------------------------
# Package facts
def _v(x: Any) -> Any:
    return getattr(x, "value", x)


def _dump(model: Any) -> Any:
    return model.model_dump() if hasattr(model, "model_dump") else model


def _store_facts(package: Any) -> Dict[str, Any]:
    """{column: its store facts} over the included store catalogs; a column declared by two catalogs
    must carry the same facts in both."""
    out: Dict[str, Any] = {}
    where: Dict[str, str] = {}
    for store_name, catalog in sorted(getattr(package, "stores", {}).items()):
        for column, facts in catalog.columns.items():
            if column in out and _dump(out[column]) != _dump(facts):
                raise DeriveRefusal("R8", "column %s is declared by the store catalogs %s and %s with "
                                    "different facts" % (column, where[column], store_name),
                                    fix="declare each column's physical facts once (plan 1.3)")
            out.setdefault(column, facts)
            where.setdefault(column, store_name)
    return out


class _Facts(object):
    """What derive_all reads from the loaded package (treeroute.package.load.LoadedPackage)."""

    def __init__(self, package: Any):
        columns = package.catalog.columns
        targets = [c for c, f in columns.items() if _v(f.role) == TARGET_ROLE]
        if len(targets) != 1:
            raise DeriveRefusal("R1", "the catalog declares %d target columns" % len(targets),
                                fix="declare exactly one column with role target (plan 1.2)")
        self.target_name = targets[0]
        self.store = _store_facts(package)
        tf = columns[self.target_name]
        ts = self.store.get(self.target_name)
        legal = tf.legal_range if tf.legal_range is not None else getattr(ts, "legal_range", None)
        if legal is None:
            raise DeriveRefusal("R22", "the target %s has no legal range" % self.target_name,
                                fix="cite the product's documented valid range (plan 1.3)")
        self.target = SimpleNamespace(name=self.target_name, window=tf.window, stamp=tf.stamp,
                                      computed_from=tuple(tf.computed_from), fact_status=tf.fact_status,
                                      legal_range=tuple(float(x) for x in legal))
        self.time_facts = {c: f.calendar_part for c, f in columns.items() if _v(f.role) == "key_time"}
        if not self.time_facts:
            raise DeriveRefusal("R1", "the catalog declares no key_time column",
                                fix="declare the target's time columns with their calendar parts")
        non_key = tuple(c for c, f in columns.items() if _v(f.role) not in KEY_ROLES)
        verdicts = dict(package.ban.verdicts)
        roles = {c: _v(columns[c].role) for c in non_key}
        self.sets = apply_verdicts(non_key, verdicts, roles)       # closed world, G-KEYS (io)
        self.context_columns = tuple(self.sets.router_context)
        self.kept = tuple(self.sets.tree_features) + tuple(self.sets.router_context)
        self.frozen = tuple(self.sets.frozen)
        no_facts = [c for c in self.kept if c not in self.store]
        if no_facts:
            raise DeriveRefusal("R8", "%d kept columns have no store facts, e.g. %s: R8 cannot lag them"
                                % (len(no_facts), no_facts[:_SHOW]),
                                fix="declare their facts in a store catalog, or build them with the "
                                    "feature script, which records its output facts (plan 1.5)")
        self.kept_facts = {}
        for c in self.kept:
            s = self.store[c]
            self.kept_facts[c] = SimpleNamespace(
                name=c, cadence=s.cadence, stamp=s.stamp, window=s.window, fact_status=s.fact_status,
                co_measured_with_target=columns[c].co_measured_with_target)
        self.absent_groups = {c: dict(getattr(self.store[c], "absent_groups", {}) or {})
                              for c in self.kept}


# ---------------------------------------------------------------------------------------------------
# The plan-time label reader (stand-in for vault.LabelView's plan-time reads; see the module docstring)
class _PlanLabels(object):
    """Holds target.y; serves validity (never a value), label-only donor views and fit rows at or
    before a cut that lies before the test window, fit-row counts at a cut (the label-window rule), and
    guard 2's independent rebuild of the donor rows. Rows are one per (unit, step), as R1 checked."""

    def __init__(self, unit_ids: np.ndarray, group_ids: np.ndarray, steps: np.ndarray, y: np.ndarray,
                 cadence: Any, target_facts: Any):
        self._units = unit_ids
        self._groups = group_ids
        self._steps = steps
        values = np.asarray(y)
        if values.ndim != 1 or len(values) != len(steps) or values.dtype.kind not in "iuf":
            raise DeriveRefusal("G-LOCK", "target y must be one number per target row, got %s %s"
                                % (values.dtype, values.shape), fix="pass the target table as read")
        big = np.isfinite(values) & (np.abs(values.astype(np.float64)) >= K.SENTINEL_MASK_ABS)
        if big.any():
            raise DeriveRefusal("G-SENTINEL", "%d target values at the sentinel magnitude; the ingest "
                                "writes invalid labels as NaN (D30)" % int(big.sum()),
                                fix="write invalid labels as NaN in the target store")
        self._y = values
        self._valid = np.isfinite(values.astype(np.float64)) if values.dtype.kind == "f" else \
            np.ones(len(values), dtype=bool)
        self._cadence = cadence
        self._target_facts = target_facts
        self._test_first: Optional[int] = None
        # each step's own label window: its content's last day (timing's target content)
        distinct = np.unique(steps)
        first, last = _steps.step_bounds(distinct, cadence)
        window_end = np.array([timing.target_content(target_facts, (int(a), int(b)))[1]
                               for a, b in zip(first.tolist(), last.tolist())], dtype=np.int64)
        self._window_end = window_end[np.searchsorted(distinct, steps)]

    def set_test_first_step(self, first_step: int) -> None:
        """Fix the first step of the test window (R5), once: donor and fit-row reads then refuse any cut
        at or after it. Validity alone may be read before (R3 reads whether rows exist up to Y_end)."""
        if self._test_first is not None:
            raise DeriveRefusal("G-LOCK", "the test window's first step is fixed already (%d)"
                                % self._test_first, fix="internal: set it once")
        self._test_first = int(first_step)

    def _before_test(self, step: int, what: str) -> None:
        if self._test_first is None:
            raise DeriveRefusal("G-LOCK", "%s before the test window is fixed (R5)" % what,
                                fix="internal: set the test window's first step first")
        if int(step) >= self._test_first:
            raise DeriveRefusal("G-LOCK", "%s at step %d reaches the test window (first step %d)"
                                % (what, int(step), self._test_first),
                                fix="donor and fit-row reads lie before the test window")

    def validity(self, first_step: int, last_step: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """(unit ids, steps, is_valid) of every row inside [first_step, last_step]; never a value."""
        if first_step > last_step:
            raise DeriveRefusal("G-LOCK", "validity window [%d, %d] is empty" % (first_step, last_step),
                                fix="pass first <= last")
        inside = (self._steps >= first_step) & (self._steps <= last_step)
        return self._units[inside], self._steps[inside], self._valid[inside]

    def donor_labels(self, groups: Tuple[str, ...], cut: int, cut_kind: CutKind, lead: int,
                     unit_ids: Optional[Sequence[str]], purpose: str) -> DonorLabels:
        """Label-only donor rows of the given groups at or before a cut (valid labels whose own window
        has ended by the cut's last day), for the given units (scope 'picked') or every unit (scope
        'all_donor_units'). Rows in ascending (unit, step) order; the row-key hash covers the unit ids
        and steps of the rows handed out."""
        cut = int(cut)
        self._before_test(cut, "a donor view")
        cut_day = int(_steps.step_bounds(np.array([cut], dtype=np.int64), self._cadence)[1][0])
        in_groups = pd.Series(self._groups).isin(list(groups)).to_numpy()
        keep = in_groups & self._valid & (self._steps <= cut) & (self._window_end <= cut_day)
        if unit_ids is None:
            scope = UR.ALL_UNITS_SCOPE
        else:
            wanted = set(unit_ids)
            unknown = sorted(wanted - set(pd.unique(self._units[in_groups]).tolist()))
            if unknown:
                raise DeriveRefusal("G-DONOR", "donor units %s are not units of the donor groups"
                                    % unknown[:_SHOW], fix="pass bank units of the groups")
            keep &= pd.Series(self._units).isin(wanted).to_numpy()
            scope = R.PICKED_SCOPE
        rows = np.flatnonzero(keep)
        codes = pd.factorize(self._units[rows], sort=True)[0]      # code-point order of the unit ids
        order = rows[np.lexsort((self._steps[rows], codes))]
        units, times = self._units[order], self._steps[order].astype(np.int64)
        key_hash = sha256_of_json([sha256_of_array(units.astype(object)), sha256_of_array(times)])
        return DonorLabels(groups=tuple(sorted(groups)), cut=cut, cut_kind=cut_kind, lead=int(lead),
                           unit_scope=scope, unit_ids=units, times=times,
                           group_of_row=self._groups[order], y=self._y[order].astype(np.float64),
                           row_key_hash=key_hash)

    def fit_rows(self, unit_ids: Sequence[str], first_step: int,
                 last_step: int) -> Tuple[np.ndarray, np.ndarray]:
        """(unit id, label) of the valid rows of the given units inside [first_step, last_step] whose
        own label window has ended by last_step's last day (before the test window): the fit rows
        behind R12's constant-history share."""
        keep = self._usable_mask(unit_ids, first_step, last_step, "fit rows")
        return self._units[keep], self._y[keep].astype(np.float64)

    def _usable_mask(self, unit_ids: Sequence[str], first_step: int, last_step: int, what: str) -> np.ndarray:
        self._before_test(int(last_step), what)
        last_day = int(_steps.step_bounds(np.array([int(last_step)], dtype=np.int64), self._cadence)[1][0])
        return (pd.Series(self._units).isin(set(unit_ids)).to_numpy() & self._valid
                & (self._steps >= int(first_step)) & (self._steps <= int(last_step))
                & (self._window_end <= last_day))

    def fit_row_counts(self, unit_ids: Sequence[str], first_step: int, last_step: int) -> Dict[str, int]:
        """{unit: its fit rows at the cut last_step}: valid labels inside [first_step, last_step] whose
        own label window has ended by last_step's last day (timing.label_usable, D26), the rows a
        router fitted at that cut may read. Every listed unit gets an entry (0 when it has none).
        Counts only, never a value; the cut lies before the test window."""
        keep = self._usable_mask(unit_ids, first_step, last_step, "fit-row counts")
        names, counts = np.unique(self._units[keep], return_counts=True)
        out = {str(u): 0 for u in unit_ids}
        out.update({str(u): int(n) for u, n in zip(names.tolist(), counts.tolist())})
        return out

    def rebuild_donor_rows(self, bank_by_group: Mapping[str, Sequence[str]], cut: int) -> SimpleNamespace:
        """The donor rows at one cut rebuilt WITHOUT donor_labels (guard 2's independent side), the
        way the run's FitContext.donor_rows selects them: each listed unit must be a unit of its
        listed group in the target table; a row is kept when its label is valid and
        timing.label_usable(its step's last day, its own label window's last day from
        timing.target_content, the cut's last day) holds; rows in ascending (unit id, step) order.
        Returns (unit_ids, times, group_of_row, y, row_key_hash) with the row-key hash formula of the
        donor views. Refuses: a cut at or after the test window; a unit that is not a unit of its
        listed group."""
        cut = int(cut)
        self._before_test(cut, "a donor-row rebuild")
        listed: Dict[str, str] = {}
        for g in sorted(bank_by_group):
            for u in bank_by_group[g]:
                listed[str(u)] = str(g)
        owner = pd.Series(self._groups, index=self._units)
        owner = owner[~owner.index.duplicated()].to_dict()
        wrong = sorted(u for u, g in listed.items() if owner.get(u) != g)
        if wrong:
            raise DeriveRefusal("G-DONOR", "listed bank units are not units of their listed group, e.g. %s"
                                % wrong[:_SHOW], fix="pass split.pick_unit_lists' bank lists")
        rows = np.flatnonzero(pd.Series(self._units).isin(list(listed)).to_numpy() & self._valid)
        steps = self._steps[rows]
        distinct, where = np.unique(steps, return_inverse=True)
        cut_day = int(_steps.step_bounds(np.array([cut], dtype=np.int64), self._cadence)[1][0])
        first, last = _steps.step_bounds(distinct, self._cadence)
        usable = np.array([timing.label_usable(int(b), int(timing.target_content(self._target_facts,
                                                                                 (int(a), int(b)))[1]),
                                               cut_day)
                           for a, b in zip(first.tolist(), last.tolist())], dtype=bool)
        rows = rows[usable[where]]
        names, codes = np.unique(self._units[rows], return_inverse=True)     # code-point order
        rows = rows[np.lexsort((self._steps[rows], codes))]
        units, times = self._units[rows], self._steps[rows].astype(np.int64)
        key_hash = sha256_of_json([sha256_of_array(units.astype(object)), sha256_of_array(times)])
        return SimpleNamespace(unit_ids=units, times=times, group_of_row=self._groups[rows],
                               y=self._y[rows].astype(np.float64), row_key_hash=key_hash)


# ---------------------------------------------------------------------------------------------------
def _target_arrays(target: Any) -> Tuple[np.ndarray, np.ndarray, Mapping[str, np.ndarray]]:
    for field in ("unit_ids", "group_ids", "time_columns", "y"):
        if not hasattr(target, field):
            raise DeriveRefusal("R1", "the target table has no %r (TargetTable is expected)" % field,
                                fix="pass the target table as read")
    units = np.asarray(target.unit_ids, dtype=object)
    groups = np.asarray(target.group_ids, dtype=object)
    n = len(units)
    if units.ndim != 1 or groups.shape != units.shape or len(np.asarray(target.y)) != n:
        raise DeriveRefusal("R1", "unit ids, group ids and y must be one per target row",
                            fix="pass the target table as read")
    bad = [g for g in pd.unique(groups) if not isinstance(g, str) or not g]
    if bad:
        raise DeriveRefusal("R1", "group ids must be non-empty names, got %r" % (bad[:_SHOW],),
                            fix="pass the key_group column")
    pairs = pd.DataFrame({"u": units, "g": groups}).drop_duplicates()
    twice = pairs["u"][pairs["u"].duplicated()]
    if len(twice):
        raise DeriveRefusal("G-DISJOINT", "%d units belong to more than one group, e.g. %s"
                            % (len(twice), twice.iloc[:_SHOW].tolist()),
                            fix="a unit belongs to one group (unit ids carry their group, plan 1.2)")
    return units, groups, target.time_columns


def _step_years(steps: np.ndarray, cadence: Any) -> np.ndarray:
    """The calendar year of each step (the year of its first day)."""
    distinct, inverse = np.unique(steps, return_inverse=True)
    first, _ = _steps.step_bounds(distinct, cadence)
    years = _steps._split_days(first - _steps._EPOCH_ORDINAL)[0]
    return np.asarray(years, dtype=np.int64)[inverse]


def _first_step_of_year(year: int, cadence: Any) -> int:
    return int(timing.year_last_step(year - 1, cadence)) + 1


def _non_tree_columns(design: Any, context_columns: Tuple[str, ...]) -> int:
    """Router columns other than the tree block (D15): one each for the intercept and the normal,
    one per context column."""
    n = 0
    for block in design.columns:
        if block == RR.CONTEXT:
            n += len(context_columns)
        elif block != RR.TREES:
            n += 1
    return n


def _check_r23_plan_time(entry: Any, lead: int, cut: int, rebuilt: Any) -> None:
    """Guard 2: the plan-time R23 entry of a lead is re-checked with the run's own
    check_r23_matches_run against donor rows REBUILT at that lead's fit cut without donor_labels
    (_PlanLabels.rebuild_donor_rows): same lead and cut, same row-key hash (so the view's scope, unit
    lists, validity and label-window rule agree with the independent selection), and the same c from
    c_from_donor_y on the rebuilt rows' labels. A stand-in until layer.c_for_cut and
    FitContext.donor_rows exist; the run calls the same check on its own rows."""
    c, _ = R.c_from_donor_y(np.asarray(rebuilt.y))
    R.check_r23_matches_run(entry, lead, cut, c, rebuilt.row_key_hash)


def _check_epoch_columns(r08: Any, frozen: Tuple[str, ...]) -> None:
    """The G-EPOCH stand-in (until validators.check_g_epoch exists): every kept column R8 listed as
    'epoch' (no lag) must carry a 'freeze' verdict, so R9 freezes it at each cut; otherwise it would
    enter unlagged and unfrozen, a silent leak."""
    unfrozen = sorted(set(r08.inputs.get("epoch", ())) - set(frozen))
    if unfrozen:
        raise DeriveRefusal("G-EPOCH", "%d kept epoch-cadence columns have no 'freeze' verdict, e.g. %s: "
                            "R8 gives them no lag and R9 freezes only 'freeze' columns, so they would "
                            "enter unlagged and unfrozen" % (len(unfrozen), unfrozen[:_SHOW]),
                            fix="give each a 'freeze' verdict (R9 computes its epoch at every cut) or "
                                "ban it (plan 1.4, 5 G-EPOCH)")


# Provenance: plan 4.1 steps 1-2 (the run refuses if derived.json differs from the one plan showed);
# plan Section 2; owner rulings D, E, F.
def derive_all(package: Any, target: Any, share_reader: Any) -> Dict[str, Any]:
    """Run every plan-time rule in dependency order and return the derived.json content.

    Rule: R1-R23, R28, R30 (orchestration; the module docstring lists the order and the guards). The
    kept columns are the tree features and router context that enter after verdicts (io.apply_verdicts:
    closed world); each needs store facts. The groups are the data's groups minus the exclusions, every
    one trained and tested. Labels are read through the plan-time label reader only (validity and
    label-only donor views), never directly; no feature pool, FitContext or run folder is built. R30's
    shares come from share_reader.measure over the donor rows of R19 (every group's bank units at the
    nowcast fit cut). Run-time rules (R15, R16, R24-R27, R29, R31-R36) are recorded by their modules.
    Pure: reads the package and the data, writes nothing.
    Returns {entry name: Derived}: one entry per rule, named by its rule id; rules with several entries
    add a qualifier ('R18:units', 'R23:lead=3', ...).
    Refuses: the first rule that refuses stops the whole derivation (fail loudly); a column without a
    verdict (G-CLOSED, io.apply_verdicts); a unit in two groups; a kept column without store facts; a
    kept epoch column without a 'freeze' verdict (G-EPOCH stand-in); a lag source whose driver store
    holds no target row (R4, owner ruling J5); a plan-time R23 entry that differs from the rebuilt
    donor rows (guard 2); a reader without the methods this module calls.
    Raises NotImplementedError for events (M8).
    """
    facts = _Facts(package)
    units, groups_of_row, time_columns = _target_arrays(target)
    out: Dict[str, Any] = {}

    # R1, R2
    out["R1"] = R.derive_r01_cadence(units, time_columns, facts.time_facts)
    cadence = out["R1"].value
    out["R2"] = R.derive_r02_season_key(cadence, getattr(cadence, "composites_per_year", None))
    if _v(cadence.kind) == IRREGULAR:
        raise NotImplementedError("derive_all for events (irregular target cadence): the plan-time "
                                  "event rules are milestone M8")
    season = out["R2"].value

    # R8 over the kept columns, the guard, R4
    out["R8"] = R.derive_r08_feature_lags(facts.kept_facts, facts.target, cadence)
    R.check_r08_covers_kept_columns(facts.kept, out["R8"])
    _check_epoch_columns(out["R8"], facts.frozen)
    steps = _steps.step_index(time_columns, facts.time_facts, cadence)
    years = _step_years(steps, cadence)
    _require(share_reader, "drivers_present", "F2 (R3 counts the joined rows) and J5 (R4 counts from the "
                                              "driver stores' first years)")
    present = np.asarray(share_reader.drivers_present(units, groups_of_row, time_columns, facts.kept))
    if present.shape != units.shape or present.dtype.kind != "b":
        raise DeriveRefusal("R3", "drivers_present must give one boolean per target row, got %s %s"
                            % (present.dtype, present.shape), fix="the column reader answers per row")
    out["R4"] = _r04_entry(package, facts, out["R8"].value, share_reader, units, groups_of_row, time_columns,
                           years, int(years.min()))

    # the groups (leave one region out), R3 over the joined rows of every group (F2)
    split_sets = _split.loro_split_sets(package.split)
    data_groups = tuple(sorted(pd.unique(groups_of_row).tolist()))
    groups = _split.groups_under_loro(split_sets, data_groups)
    diff = _split.loro_split_differences(split_sets, data_groups)
    if diff.listed_not_in_data or diff.reported_and_excluded or diff.duplicates:
        raise DeriveRefusal("G-SPLIT", "split.yaml differs from the data: %s" % (diff,),
                            fix="list only groups the data holds; a reported group is never excluded")
    out["R18:groups"] = make_derived("R18", groups, {
        "data_groups": len(data_groups), "excluded": dict(split_sets.excluded),
        "seen_during_design": list(split_sets.seen_during_design),
        "design": "leave one region out: every group trains its own trees and is tested"})
    labels = _PlanLabels(units, groups_of_row, steps, np.asarray(target.y), cadence, facts.target)
    _, _, y_valid = labels.validity(int(steps.min()), int(steps.max()))
    counts = R.count_valid_rows_per_group_year(groups_of_row, years, y_valid, present, groups)
    out["R3"] = R.derive_r03_coverage_end(counts, groups, False)

    # R5 - R7, R10, R11, R9
    y0, y_end = out["R4"].value, out["R3"].value
    out["R5"] = R.derive_r05_test_window(y0, y_end)
    out["R6"] = R.derive_r06_train_end(out["R5"].value.test_years)
    out["R7"] = R.derive_r07_inner_windows(y0, y_end, out["R5"].value, out["R6"].value)
    windows = out["R7"].value
    out["R10"] = R.derive_r10_leads(season, False)
    out["R11"] = R.derive_r11_cuts(windows, out["R10"].value, cadence)
    cuts = out["R11"].value
    epochs: Dict[str, Sequence[int]] = {}
    if facts.frozen:
        _require(share_reader, "content_epochs", "R9 (the content epochs of 'freeze' columns)")
        epochs = {c: tuple(int(e) for e in share_reader.content_epochs(c)) for c in facts.frozen}
    out["R9"] = R.derive_r09_freeze_epochs(epochs, R.cut_days(cuts, cadence))

    # the test window closes the label reader's donor reads
    labels.set_test_first_step(_first_step_of_year(min(windows.test_years), cadence))
    train_end_step = int(cuts[0].fit_cut)
    inner_end_step = int(timing.year_last_step(windows.inner_fit[1], cadence))
    y0_step = _first_step_of_year(y0, cadence)

    # candidates (every group), R12: validity alone, by the approved contracts (the module docstring,
    # 'Row counts', says why no label leaks through it)
    v_units, v_steps, v_valid = labels.validity(int(steps.min()), train_end_step)
    group_of_unit = pd.Series(groups_of_row, index=units)
    group_of_unit = group_of_unit[~group_of_unit.index.duplicated()]
    v_groups = group_of_unit.reindex(v_units).to_numpy(dtype=object)
    candidates = {g: _split.candidate_units(v_units, v_groups, v_steps, v_valid, g, train_end_step)
                  for g in groups}
    every_candidate = np.asarray([u for g in groups for u in candidates[g]], dtype=object)
    w_units, w_steps, w_valid = labels.validity(y0_step, inner_end_step)
    in_cand = pd.Series(w_units).isin(set(every_candidate.tolist())).to_numpy()
    inner_counts = dict(RR.count_valid_rows_per_unit(w_units[in_cand], w_steps[in_cand], w_valid[in_cand],
                                                     y0_step, inner_end_step))
    for u in every_candidate.tolist():
        inner_counts.setdefault(u, 0)             # a candidate with no row in the window counts 0
    out["R12"] = RR.derive_r12_router_kind(inner_counts)
    kind = out["R12"].value

    # R13, R14, R17
    out["R13"] = RR.derive_r13_surface_loro(kind, groups)
    out["R14"] = RR.derive_r14_router_design(kind, facts.context_columns)
    out["R17"] = RR.derive_r17_history_spec(season, facts.target, cadence, kind, False)

    # R18: bank count, scored count (event floor), unit lists
    available = {g: len(candidates[g]) for g in groups}
    pooled = {g: int(sum(inner_counts[u] for u in candidates[g])) for g in groups}
    median_inner = float(np.median(list(inner_counts.values())))
    out["R18:bank"] = UR.derive_r18_bank_count(kind, season, median_inner, available, pooled,
                                               _non_tree_columns(out["R14"].value, facts.context_columns))
    rule_value, bank = out["R18:bank"].value
    donor_all = labels.donor_labels(groups, train_end_step, CutKind.FIT, 0, None, "event_rate")
    test_rows = int(season.steps_per_year) * len(windows.test_years)
    out["R18"] = UR.derive_r18_scored_count(kind, rule_value, bank, available, K.K_GROUP_EQUIVALENTS,
                                            donor_all, test_rows)
    lists = _split.pick_unit_lists(groups, candidates, out["R18"].value)
    out["R18:units"] = make_derived("R18", lists, {
        "bank_units_hash": {g: _split.unit_ids_hash(lists.bank[g]) for g in groups},
        "scored_units_hash": {g: _split.unit_ids_hash(lists.scored[g]) for g in groups},
        "rule": "bank by a stride over the sorted candidates (D40); scored = an evenly spaced subset "
                "of the bank units (L2)"})
    bank_units = tuple(u for g in groups for u in lists.bank[g])
    scored_units = tuple(u for g in groups for u in lists.scored[g])

    # R12's report-only constant-history share over the scored units' fit rows (its refusal of no
    # fit row at all stands: fail loudly)
    fit_units, fit_y = labels.fit_rows(scored_units, y0_step, inner_end_step)
    share = RR.constant_history_share(fit_units, fit_y)
    out["R12:constant_history_share"] = make_derived("R12", share, {
        "units": len(scored_units), "rows": int(len(fit_y)),
        "rows_scope": "valid labels of every group's scored units, Y0 to the inner-fit end, whose own "
                      "label window has ended by then",
        "report_only": True})

    # the region router's fit budget (R14, L2 rule 2): whole, evenly spaced bank units; fit rows are
    # the label-usable rows at each surface's cut (the inner-fit end, the train end)
    if _v(kind) == RouterKind.REGION.value:
        inner_fit_rows = labels.fit_row_counts(bank_units, y0_step, inner_end_step)
        test_fit_rows = labels.fit_row_counts(bank_units, y0_step, train_end_step)
        out["R14:region_fit"] = _region_fit(groups, lists, inner_fit_rows, test_fit_rows)

    # R19 (and the inner-cut bank's plan, L6 b), R20 (and the fallback routers' rows), R21
    donor = labels.donor_labels(groups, train_end_step, CutKind.FIT, 0, bank_units, "bank_plan")
    out["R19"] = UR.derive_r19_bank_plan(donor, False)
    if K.INNER_CUT_BANK_REFIT:
        inner_cut = int(cuts[0].guard_cut)
        inner_donor = labels.donor_labels(groups, inner_cut, CutKind.GUARD, 0, bank_units,
                                          "bank_plan_inner_cut")
        out["R19:inner_cut"] = UR.derive_r19_inner_cut_bank_plan(inner_donor, False)
    out["R20"] = UR.derive_r20_batching(False, groups)
    out["R20:fallback_rows"] = _fallback_rows(kind, groups, lists, labels, y0_step, cuts, donor)
    out["R21"] = UR.derive_r21_smoke_plan_loro(groups)

    # R22, R23 per lead cut (with guard 2 on independently rebuilt donor rows), R28
    out["R22"] = R.derive_r22_links(facts.target.legal_range, donor)
    if Link.LOG_C in out["R22"].value:
        bank_by_group = {g: lists.bank[g] for g in groups}
        for lead in sorted(cuts):
            cut = int(cuts[lead].fit_cut)
            view = labels.donor_labels(groups, cut, CutKind.FIT, lead, bank_units, "links")
            entry = R.derive_r23_c_for_cut(view)
            _check_r23_plan_time(entry, lead, cut, labels.rebuild_donor_rows(bank_by_group, cut))
            out["R23:lead=%d" % lead] = entry
    out["R28"] = R.derive_r28_clip_bounds(facts.target.legal_range)

    # R30
    _require(share_reader, "measure", "R30 (the missing and real-zero shares)")
    shares = share_reader.measure(donor, out["R8"].value, tuple(windows.test_years))
    if getattr(shares, "donor_row_key_hash", None) != donor.row_key_hash:
        raise DeriveRefusal("R30", "the shares were measured on other rows (row-key hash %s, the donor "
                            "rows' %s)" % (getattr(shares, "donor_row_key_hash", None), donor.row_key_hash),
                            fix="measure the shares over the donor view derive_all passes")
    out["R30"] = UR.derive_r30_missing_flags(shares, facts.absent_groups)
    return out


# Provenance: plan 2.2 R14 (region: fit rows capped at the budget by keeping whole, evenly spaced units;
# the fit units are the group's BANK units, decoupled from its scored units, L2 rule 2);
# adaptation.py:1149-1150, 1213 (the shipped linspace pick and REGROWS).
def _region_fit(groups: Tuple[str, ...], lists: Any, inner_fit_rows: Mapping[str, int],
                test_fit_rows: Mapping[str, int]) -> Any:
    """The region router's fit units per group: split.region_cap_units over the group's bank units,
    with each unit's fit rows at the decision surface's cut (the inner-fit end) and at the test pass's
    cut (the train end): valid labels from Y0 to the cut whose own window has ended by it (the rows
    FitContext.router_rows hands out), within C7.region_router_row_budget."""
    budget = int(K.REGION_ROUTER_ROW_BUDGET)
    value: Dict[str, Dict[str, int]] = {}
    flags = []
    for g in groups:
        bank = lists.bank[g]
        entry: Dict[str, int] = {}
        for surface, rows in (("inner_surface", inner_fit_rows), ("test_pass", test_fit_rows)):
            fit_rows = {u: int(rows.get(u, 0)) for u in bank}
            kept = _split.region_cap_units(bank, fit_rows, budget)
            entry[surface + "_units"] = len(kept)
            entry[surface + "_rows"] = int(sum(fit_rows[u] for u in kept))
            if len(kept) < len(bank):
                flags.append("capped:%s:%s" % (surface, g))
        value[g] = entry
    inputs = {"budget": budget, "fit_units": "every group's bank units (L2 rule 2)",
              "fit_rows": "valid labels from Y0 to the surface's cut whose own label window has ended by "
                          "the cut (timing.label_usable, D26)",
              "rule": "the largest evenly spaced set of whole bank units within the budget "
                      "(split.region_cap_units)",
              "constants": {"C7.region_router_row_budget": budget}}
    return make_derived("R14", value, inputs, flags=tuple(flags))


# Provenance: owner ruling J5, 2026-10-05 (OWNER_RULINGS_2026-10-05.md section J): R4 counts from the first
# year of the driver stores (the lag sources), not the target's first year; F2 / F8 (drivers_present: a
# declared-absent group counts as present).
def _r04_first_data_year(package: Any, facts: _Facts, lags: Mapping[str, Any], reader: Any,
                         units: np.ndarray, groups_of_row: np.ndarray, time_columns: Mapping[str, Any],
                         years: np.ndarray) -> Tuple[int, Dict[str, Any]]:
    """J5: R4's first data year, the first year of the driver stores the lag sources read, and its record.

    A lag source is a kept column whose lag in ``lags`` is above 0: derive_all passes R4's lags
    (_r04_lags: R8's lag plus a counted lag operation's look-back). Its store's first year is measured on the
    target's own rows with the column reader's drivers_present (F2), asked once per store catalog and set
    of declared-absent groups: the year of the earliest target row the store holds, leaving out the rows
    of the groups it declares absent (F8 counts them as present, but they hold nothing, so they say
    nothing about when the store starts). The first data year is the LATEST of these first years, so no
    lagged column reads a year before its own store's first year; with no lag source it is the target's
    first year. A store year before the target's first year cannot be seen on the target's rows, so the
    first data year is never before the target's first year (Y0 never comes out earlier than the old
    rule's). Columns of one catalog that the reader finds in different stores share the latest of their
    first years (the reader answers for every store holding one of them): conservative.
    READING (owner confirmation asked): with several lag-source stores starting in different years, the
    LATEST first year is used for every column (J5's "the first year of the driver stores"); a tighter
    per-column bound (Y0 = max over lag sources of its store's first year + its own lag) would need
    R4's approved signature to carry the per-column first years.
    READING (owner confirmation asked): J5 is applied in whole YEARS (its wording): a store that starts
    part-way through its first year counts that year as its first, so a column lagged in months (e.g. 3)
    can still read a few months before the store's first month early in Y0's first year; R30 fills
    them. Measuring each store's first STEP instead would close that.
    Returns (first data year, record: the target's first year and, per store catalog and absent-group
    set, the lag sources and the first year). Refuses (R4): an answer that is not one boolean per target
    row; a lag source whose store holds no target row outside its declared-absent groups."""
    target_first = int(years.min())
    record: Dict[str, Any] = {"target_first_year": target_first, "stores": [],
                              "rule": "J5: R4 counts from the latest first year of the driver stores that hold a "
                                      "lag source (R4 lag above 0: R8's lag plus a counted lag operation's "
                                      "look-back, _r04_lags), measured on the target's rows outside "
                                      "declared-absent groups, in whole years; never before the target's "
                                      "first year"}
    sources = [c for c in sorted(lags) if int(lags[c].steps) > 0]
    catalog_of: Dict[str, str] = {}
    for store_name, catalog in sorted(getattr(package, "stores", {}).items()):
        for column in catalog.columns:
            catalog_of.setdefault(column, store_name)
    batches: Dict[Tuple[str, Tuple[str, ...]], list] = {}
    for c in sources:
        absent = tuple(sorted(str(g) for g in facts.absent_groups.get(c, {})))
        batches.setdefault((catalog_of.get(c, ""), absent), []).append(c)
    first_data_year = target_first
    for (store_name, absent), columns in sorted(batches.items()):
        held = np.asarray(reader.drivers_present(units, groups_of_row, time_columns, tuple(columns)))
        if held.shape != units.shape or held.dtype.kind != "b":
            raise DeriveRefusal("R4", "drivers_present must give one boolean per target row, got %s %s"
                                % (held.dtype, held.shape), fix="the column reader answers per row")
        if absent:
            held = held & ~pd.Series(groups_of_row).isin(list(absent)).to_numpy()
        if not held.any():
            raise DeriveRefusal("R4", "the driver store of the lag sources %s (catalog %s) holds no target row "
                                "outside its declared-absent groups, so its first year is unknown (J5)"
                                % (columns[:_SHOW], store_name),
                                fix="check the store's coverage, or ban the columns")
        first = int(years[held].min())
        first_data_year = max(first_data_year, first)
        record["stores"].append({"catalog": store_name, "absent_groups": list(absent),
                                 "lag_sources": list(columns), "first_year": first})
    record["first_data_year"] = first_data_year
    return first_data_year, record


# Provenance: owner ruling J5, 2026-10-05 ("a lagged column never reads a year the store does not have");
# plan 1.5 (a feature output declares derived_from and its operation); the review of the J5 build: a lag-k
# output gets R8 lag 0 (its content already ends k steps back), so R4 must add the k it reads back.
_LAG_OPERATION = re.compile(r"lag k=([0-9]+) unit=([a-z_]+)")


def _r04_lags(facts: Any, lags: Mapping[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """J5: the lags R4 counts (R8's lag plus a declared lag operation's look-back), and their record.

    A column whose store facts declare derived_from and the operation 'lag k=<k> unit=<unit>' (the
    spelling the feature scripts write, e.g. a J2 (a) <parent>_lag12 column) holds at row t its parent's
    value k steps of that unit before t, and R8 then shifts it by its own lag L. So it reads its parent's
    store L + k steps back, while R8's lag is L alone (R8 reads the forward edge of the content, which
    already ends k steps back, so L is often 0). R4 counts L + k, with k turned into the column's own
    steps: the same unit -> ceil(k / cadence length); k years on a month cadence -> ceil(12k / length);
    k months on a year cadence -> ceil(k / (12 x length)) (C6).
    Not counted, and listed under 'not_counted' by operation text: any other operation (a trailing mean,
    a cumulative sum, free text); their look-back stays with R30 (READING, owner confirmation asked).
    One whose first word is 'lag' but that does not carry k and unit in that spelling is also listed
    under 'lag_operation_not_counted' (derive flags R4 'lag_operation_not_counted': R4 cannot count a
    look-back it cannot read).
    Returns ({column: Lag}, record): the map has R8's keys; a counted column's Lag is R8's with steps
    L + k. Refuses (R4): a structured lag in a unit it cannot turn into the column's steps."""
    rule = "R4"
    store = getattr(facts, "store", {}) or {}
    out: Dict[str, Any] = {}
    counted: Dict[str, Any] = {}
    not_counted: Dict[str, list] = {}
    unread: list = []
    for c in sorted(lags):
        lag = lags[c]
        out[c] = lag
        s = store.get(c)
        operation = getattr(s, "operation", None)
        if not operation or not getattr(s, "derived_from", None):
            continue
        text = str(operation).strip()
        match = _LAG_OPERATION.fullmatch(text)
        if match is None:
            not_counted.setdefault(text, []).append(c)
            if text.split()[:1] == ["lag"]:
                unread.append(c)
            continue
        k, unit = int(match.group(1)), match.group(2)
        cadence = lag.column_cadence
        kind, length, own = _v(getattr(cadence, "kind", None)), getattr(cadence, "length", None), \
            _v(getattr(cadence, "unit", None))
        months = K.MONTHS_PER_YEAR
        if kind == "regular" and isinstance(length, int) and length > 0 and unit == own:
            extra = -(-k // length)
        elif kind == "regular" and isinstance(length, int) and length > 0 and (unit, own) == ("year", "month"):
            extra = -(-(k * months) // length)
        elif kind == "regular" and isinstance(length, int) and length > 0 and (unit, own) == ("month", "year"):
            extra = -(-k // (months * length))
        else:
            raise DeriveRefusal(rule, "column %s declares the operation %r on a %s cadence (length %s, unit %s); "
                                "R4 cannot turn its look-back into the column's steps (J5)"
                                % (c, text, kind, length, own),
                                fix="declare the lag in the column's own step unit")
        steps = int(lag.steps) + extra
        counted[c] = {"operation": text, "derived_from": list(s.derived_from), "r8_steps": int(lag.steps),
                      "operation_steps": extra, "r4_steps": steps}
        out[c] = timing.Lag(column=c, steps=steps, column_cadence=cadence, floor_reason=lag.floor_reason)
    record = {"rule": "J5: R4 counts R8's lag plus the look-back of a declared 'lag k=<k> unit=<unit>' "
                      "operation (in the column's steps); other operations are not counted (listed)",
              "counted": counted, "not_counted": {t: cols for t, cols in sorted(not_counted.items())},
              "lag_operation_not_counted": unread}
    return out, record


# Provenance: owner ruling J5 (R4 from the driver stores' first years, counting every look-back); one
# entry builder for derive_all and the streaming census (census.derive_all_streamed), so the two agree.
def _r04_entry(package: Any, facts: Any, r8_lags: Mapping[str, Any], reader: Any, units: np.ndarray,
               groups_of_row: np.ndarray, time_columns: Mapping[str, Any], years: np.ndarray,
               target_first_year: int) -> Any:
    """R4's derived entry: _r04_lags, then _r04_first_data_year over those lags, then the approved
    derive_r04_first_year. inputs gain 'driver_stores' (the first-year record) and 'lag_operations'
    (_r04_lags' record); flags gain 'store_first_year_moved_y0' when the driver stores start after
    target_first_year, and 'lag_operation_not_counted' when a 'lag' operation could not be read.
    Refuses: whatever the three refuse (R4)."""
    lags, operations = _r04_lags(facts, r8_lags)
    first_data_year, stores = _r04_first_data_year(package, facts, lags, reader, units, groups_of_row,
                                                   time_columns, years)
    r4 = R.derive_r04_first_year(first_data_year, lags)
    flags = tuple(r4.flags)
    if first_data_year > int(target_first_year):
        flags += ("store_first_year_moved_y0",)
    if operations["lag_operation_not_counted"]:
        flags += ("lag_operation_not_counted",)
    return make_derived("R4", r4.value, dict(r4.inputs, driver_stores=stores, lag_operations=operations),
                        margins=r4.margins, flags=flags)


def _require(reader: Any, method: str, why: str) -> None:
    if not callable(getattr(reader, method, None)):
        raise DeriveRefusal("derive_all", "the column reader has no %s(); %s needs it" % (method, why),
                            fix="pass the io column reader (derive.orchestrate module docstring)")


# Provenance: plan 2.2 R12 and 2.3 R20 (L2 rule 3: a per-unit package's fallback region router pools the
# group's bank units, so the tables also hold those units' rows at or before the cut, for every group
# that has a fallback unit; plan lists those groups and prices the rows).
def _fallback_rows(kind: Any, groups: Tuple[str, ...], lists: Any, labels: _PlanLabels, y0_step: int,
                   cuts: Mapping[int, Any], donor: DonorLabels) -> Any:
    """R20's extra rows (a per-unit package only): per group with a scored unit that falls back at ANY
    cut where its per-unit router is fitted, the fallback units and the bank-unit rows at the nowcast
    fit cut. The router cuts are every lead's fit cut (test pass) and guard cut (inner decision); at
    each, a scored unit falls back when its fit rows (valid labels from Y0 to the cut whose own window
    has ended by it, the rows route.kinds.valid_fit_rows counts) are fewer than
    C5.per_unit_min_valid_rows. The fallback set is the union over the cuts."""
    value: Dict[str, Dict[str, Any]] = {}
    router_cuts = sorted({int(c.fit_cut) for c in cuts.values()} | {int(c.guard_cut) for c in cuts.values()})
    short_at: Dict[str, list] = {}
    if _v(kind) == RouterKind.PER_UNIT.value:
        scored = [u for g in groups for u in lists.scored[g]]
        for cut in router_cuts:
            counts = labels.fit_row_counts(scored, y0_step, cut)
            for u in scored:
                if counts[u] < K.PER_UNIT_MIN_VALID_ROWS:
                    short_at.setdefault(u, []).append(cut)
        rows_by_group = pd.Series(np.asarray(donor.group_of_row, dtype=object)).value_counts()
        for g in groups:
            short = [u for u in lists.scored[g] if u in short_at]
            if short:
                value[g] = {"fallback_units": len(short), "units": short,
                            "bank_rows_at_cut": int(rows_by_group.get(g, 0))}
    inputs = {"kind": _v(kind), "groups_with_fallback": len(value),
              "extra_rows": int(sum(v["bank_rows_at_cut"] for v in value.values())),
              "router_cuts": router_cuts, "short_at_cuts": {u: c for u, c in sorted(short_at.items())},
              "fit_rows": "valid labels from Y0 to the cut whose own label window has ended by the cut",
              "rule": "a scored unit falls back at any router cut (every lead's fit and guard cut) with "
                      "fewer fit rows than the minimum; the tables hold every bank unit's rows at or "
                      "before the cut for each listed group (L2 rule 3)",
              "constants": {"C5.per_unit_min_valid_rows": K.PER_UNIT_MIN_VALID_ROWS}}
    return make_derived("R20", value, inputs)
