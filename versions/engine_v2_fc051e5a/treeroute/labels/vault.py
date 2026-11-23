"""The label vault: LabelView, the ONLY object that holds target labels, and the adoption locks.

SCIENCE bodies for the owner-approved signatures of treeroute/_proposed/vault.py (owner rulings A-F;
LORO addendum: donor_labels takes the LORO split sets; D54 (a): per-row as-of reads serve test rows'
history and persistence before the pass's lock, because each label is known at its row's issue step
and decide() never sees a test row). The owner reviews this body: it is the test-label lock (G-LOCK).

What goes in. The target table's y goes into the constructor and nowhere else, aligned to the
keys-only dense grid. Every read after that goes through one of the methods below and is logged
(method, purpose, cut, row count, newest label time served):
    validity(first, last)     label validity only, never a value (R3, R12, R18 counts)
    donor_labels(...)         label-only donor view at or before a cut, for plan-time rules
    asof(cut)                 every label at or before a cut whose own window has ended (FitContext)
    asof_rows(...)            per-row reads of the label exactly k steps before a row's newest
                              readable step (history block, persistence, target-derived recomputes);
                              each read logs how many test-window positions it served and which
                              passes were locked and open at that moment (D54 a serves them before
                              the lock); test_window_reads() totals them and lock_adoption prints
                              and records the total
    decision_surface(...)     the ONLY source of layer.decide's DecisionSurface: the as-of labels at
                              a cut for given (unit, step) rows, read-only and content-hashed
    open_test_labels(...)     test-window labels, per scoring pass, against that pass's locked adoption
The label rule of R11 applies to every cut: a label counts at a cut when it is dated at or before the
cut AND its own label window ended by the cut's last day (timing.label_usable, D26), so a cut step's
own label is dropped when the target's window reaches past its step. No cut inside the test window is
ever served, except to open_test_labels, which releases the test window only against a lock.

The locks. lock_adoption writes the nowcast's adoption.json ONCE (atomically: temp file, fsync,
rename) and hashes it; lock_lead_adoption does the same for each forecast lead. The nowcast document
is the one decide() registered with this vault when it scored a surface this vault issued (the
adoption, every candidate, and the decision section); an adoption no such decide() made is refused,
and so is an adoption naming a link R22 does not have unless its decision declared a legacy candidate
list. Each lock also writes
a lock record (<file>.lock.json: the file, its SHA-256, the time) beside it. open_test_labels(hash,
lead) opens a pass only if that pass's adoption file exists, its SHA-256 equals the given hash AND the
recorded one, and the lock was written before the call; it then writes a write-once marker
(test_labels_opened_lead_<lead>.json). After a pass is open its adoption can never change (a new lock
for that pass is refused). A vault built on a run folder re-reads the lock records and markers and
refuses a folder whose adoption files do not match their records, or whose opened marker names
another adoption.

The alarm lock (owner ruling AE). lock_alarm writes one pass's alarm record (alarm_lead_<lead>.json, the
twin-disagreement alarm's decision and its locked predictions' hash) once, after that pass's adoption lock and
before its test labels open, with a lock record ending in ALARM_LOCK_SUFFIX. open_test_labels then also takes the
alarm record's hash (keyword alarm_sha256, required) and opens only against it; the opened marker records it.

Signature notes (flagged for the owner). The approved constructor carries no calendar, but R11's
label rule compares each label's window end (a Day) with the cut's last day, and the cut of a grid is
a step; the vault therefore takes the target cadence as a keyword (cadence=...), required for grids,
read with io.steps.step_bounds. asof_rows takes a keyword purpose (logged). donor_labels takes a
keyword picks (split.UnitLists): the LORO addendum refuses "a unit that is not a bank unit", but the
approved signature carries no bank lists, so without picks the vault can refuse only a unit outside
the split's groups; with picks it refuses a unit outside the bank lists. decision_surface is a new
method (the G-LOCK source of decide()'s surface). Events (grid None) are milestone M8.
"""
# Provenance for the module: plan 4.2 labels/vault.py; plan 2.1 R11; plan 5 G-LOCK; plan 9.2 A6;
# pm25_forecast.py:601-606 (each rung's adoption on disk before any test row is routed), :347-356 (the
# atomic writer, now runs/atomic.py); owner rulings A (D54 a), D and E (leave one region out).

import hashlib
import json
import os
import re
import time
import weakref
from dataclasses import dataclass
from numbers import Integral
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import numpy as np

from treeroute.derive.derived import sha256_of_array, sha256_of_json
from treeroute.derive.rules import PICKED_SCOPE
from treeroute.derive.shapes import CutKind, DonorLabels, Link
from treeroute.derive.unit_rules import ALL_UNITS_SCOPE
from treeroute import split as _split
from treeroute.errors import RefusedError
from treeroute.io.steps import DenseGrid, as_int_array, step_bounds
from treeroute.layer.decide import (Adoption, DecisionSurface, LeadAdoption, _issuing_surface,
                                    adoption_document, as_point, lead_adoption_document, pin_of,
                                    surface_sha256)
from treeroute.runs.atomic import dumps, read_json, write_text_once

ADOPTION_FILE = "adoption.json"
LEAD_ADOPTION_FILE = "adoption_lead_%d.json"
LOCK_SUFFIX = ".lock.json"
# owner ruling AE (the twin-disagreement alarm, layer/alarm.py): each scoring pass's alarm record is locked before the
# pass's test labels open. Its lock record's suffix deliberately does NOT end in LOCK_SUFFIX, so the adoption-lock
# glob of _load_folder_state and its one-adoption-lock-per-lead rule never see it.
ALARM_FILE = "alarm_lead_%d.json"
ALARM_LOCK_SUFFIX = ".alarmlock.json"
OPENED_FILE = "test_labels_opened_lead_%d.json"
_OPENED_RE = re.compile(r"^test_labels_opened_lead_(\d+)\.json$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_SHOW = 5


class VaultRefusal(RefusedError):
    """A vault rule refused (G-LOCK, G-FITCUT, G-DONOR, R11). Nothing catches it to carry on."""


# ---------------------------------------------------------------------------------------------------
# Shapes (field-identical to the approved vault shapes; DonorLabels is derive's copy of the approved one)
@dataclass(frozen=True)
class LabelSlice:
    """Labels visible at one cut: rows (unit, step or day) and y, with the cut recorded."""
    cut: int
    unit_ids: np.ndarray
    times: np.ndarray
    y: np.ndarray


@dataclass(frozen=True)
class TestLabels:
    """Test-window labels of one scoring pass, released only by LabelView.open_test_labels."""
    __test__ = False                    # not a pytest test class, whatever its name says
    lead: int                           # 0 = the nowcast test pass
    adoption_sha256: str
    unit_ids: np.ndarray
    times: np.ndarray
    y: np.ndarray


# ---------------------------------------------------------------------------------------------------
def _int(value: Any, what: str, rule: str = "G-LOCK") -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise VaultRefusal(rule, "%s must be a whole number, got %r" % (what, value))
    return int(value)


def _name(value: Any, what: str) -> str:
    if not isinstance(value, str) or not value:
        raise VaultRefusal("G-LOCK", "%s must be a non-empty name, got %r" % (what, value))
    return value


def _cut_kind(value: Any) -> CutKind:
    raw = getattr(value, "value", value)
    try:
        return CutKind(raw)
    except ValueError:
        raise VaultRefusal("R11", "cut_kind must be FIT or GUARD, got %r" % (value,)) from None


def _sha(text_bytes: bytes) -> str:
    return hashlib.sha256(text_bytes).hexdigest()


def _file_sha(path: Path) -> str:
    return _sha(path.read_bytes())


def row_key_hash(unit_ids: np.ndarray, times: np.ndarray) -> str:
    """The row-key hash of a set of label rows: SHA-256 of the canonical JSON of [the hash of the unit
    ids (as text), the hash of the times (int64)]. The formula of derive's plan-time donor view, so
    DonorLabels and FitContext.donor_rows at one cut compare by hash."""
    return sha256_of_json([sha256_of_array(np.asarray(unit_ids, dtype=object)),
                           sha256_of_array(np.asarray(times, dtype=np.int64))])


# ---------------------------------------------------------------------------------------------------
class LabelView:
    """The only object that hands out labels.

    Rule: A6, G-LOCK, G-FITCUT. Attributes (read-only): grid, test_first_time, run_folder.
    """

    # Provenance: plan 4.2 labels/vault.py; plan 2.1 R11 (labels at or before the cut whose own window
    # has ended); plan 1.2 target table (NaN y = a label the ingest declared invalid).
    def __init__(self, grid: Optional[DenseGrid], target: Any, times: np.ndarray, test_first_time: int,
                 label_window_last_day: np.ndarray, run_folder: Optional[Path], *,
                 cadence: Any = None) -> None:
        """Take the target table's labels into the vault, aligned to the dense grid.

        Rule: A6, G-LOCK. The ONLY consumer of TargetTable.y. Labels are aligned to the keys-only grid;
        every later read is logged. With run_folder None the view serves validity, donor labels and
        as-of reads (plan, check --deep) but can never lock an adoption or open test labels.
        Inputs: grid (DenseGrid; None = events, milestone M8); target (unit_ids, group_ids, y);
        times (integer step per target row); test_first_time (first step of the test window, R5);
        label_window_last_day (last day of each row's own label window, Day ordinals); run_folder
        (the folder that will hold the adoption files, or None); cadence (keyword, required for
        grids: the target cadence, to find a cut step's last day).
        Refuses: a target row whose (unit, step) is not on the grid, or a duplicate (unit, step); a
        grid position with no target row (the grid is the census of this target); a unit whose group
        differs from the grid's; an infinite label (invalid labels are NaN, D30); a missing cadence;
        a run folder that already holds opened test labels from another adoption, or an adoption
        file that differs from its lock record.
        """
        if grid is None:
            raise NotImplementedError("the label vault for events (one row per visit, grid None) is "
                                      "built at milestone M8 (the event rules)")
        for field in ("unit_ids", "group_of_unit", "first_step", "n_steps"):
            if not hasattr(grid, field):
                raise VaultRefusal("G-LOCK", "grid must be the keys-only DenseGrid (no %r field)" % field)
        for field in ("unit_ids", "group_ids", "y"):
            if not hasattr(target, field):
                raise VaultRefusal("G-LOCK", "the target table has no %r (TargetTable is expected)" % field)
        if cadence is None:
            raise VaultRefusal("R11", "the vault needs the target cadence (keyword cadence=...) to find "
                                      "each cut step's last day for R11's label-window rule",
                               fix="pass R1's cadence (derived.json R1)")
        self._cadence = cadence
        self._grid = grid
        self._units = tuple(str(u) for u in grid.unit_ids)
        self._unit_groups = tuple(str(g) for g in grid.group_of_unit)
        self._first = _int(grid.first_step, "grid.first_step", "R30")
        self._n = _int(grid.n_steps, "grid.n_steps", "R30")
        if self._n < 1 or not self._units or len(self._units) != len(self._unit_groups):
            raise VaultRefusal("R30", "the grid is empty or its unit and group lists differ in length")
        self._row_of = {u: i for i, u in enumerate(self._units)}
        if len(self._row_of) != len(self._units):
            raise VaultRefusal("R30", "the grid names a unit twice")
        self._test_first = _int(test_first_time, "test_first_time", "R5")
        units = np.asarray(target.unit_ids, dtype=object)
        groups = np.asarray(target.group_ids, dtype=object)
        t = as_int_array(times, "times", rule="G-LOCK")
        wend = as_int_array(label_window_last_day, "label_window_last_day", rule="R11")
        y = np.asarray(target.y)
        if y.ndim != 1 or y.dtype.kind not in "iuf" or y.dtype == np.bool_:
            raise VaultRefusal("G-LOCK", "target y must be one number per row, got %s %s" % (y.dtype, y.shape))
        n_rows = len(units)
        if not (len(groups) == len(t) == len(wend) == len(y) == n_rows):
            raise VaultRefusal("G-LOCK", "unit ids (%d), group ids (%d), times (%d), label windows (%d) "
                               "and y (%d) must be one per target row"
                               % (n_rows, len(groups), len(t), len(wend), len(y)))
        rows = np.fromiter((self._row_of.get(str(u), -1) for u in units.tolist()), dtype=np.int64,
                           count=n_rows)
        off = rows < 0
        if off.any():
            raise VaultRefusal("G-LOCK", "%d target rows name units that are not on the grid, e.g. %s"
                               % (int(off.sum()), sorted(set(str(u) for u in units[off][:_SHOW]))))
        grid_groups = np.asarray(self._unit_groups, dtype=object)[rows]
        wrong = grid_groups != groups
        if np.any(wrong):
            raise VaultRefusal("G-DISJOINT", "%d target rows carry a group other than their unit's grid "
                               "group, e.g. %s" % (int(np.sum(wrong)),
                                                  sorted(set(str(u) for u in units[wrong][:_SHOW]))))
        last = self._first + self._n - 1
        outside = (t < self._first) | (t > last)
        if outside.any():
            raise VaultRefusal("G-LOCK", "%d target rows lie outside the grid's steps [%d, %d]"
                               % (int(outside.sum()), self._first, last))
        pos = rows * self._n + (t - self._first)
        size = len(self._units) * self._n
        order = np.argsort(pos, kind="stable")
        ps = pos[order]
        if ps.size > 1 and (ps[1:] == ps[:-1]).any():
            raise VaultRefusal("G-LOCK", "%d target rows repeat a (unit, step)"
                               % int((ps[1:] == ps[:-1]).sum()))
        if ps.size != size:
            raise VaultRefusal("G-LOCK", "the grid has %d unit x step positions and the target %d rows; "
                               "the grid is the census of this target" % (size, ps.size),
                               fix="build the grid from this target table (io.steps.build_dense_grid)")
        values = np.asarray(y, dtype=np.float64)
        if np.isinf(values).any():
            raise VaultRefusal("G-SENTINEL", "%d target labels are infinite; the ingest writes invalid "
                               "labels as NaN (D30)" % int(np.isinf(values).sum()))
        self._y = np.empty(size, dtype=np.float64)
        self._y[pos] = values
        self._y.setflags(write=False)
        self._window_end = np.empty(size, dtype=np.int64)
        self._window_end[pos] = wend
        self._window_end.setflags(write=False)
        self._valid = np.isfinite(self._y)
        self._valid.setflags(write=False)
        self._steps_of_pos = np.tile(np.arange(self._first, self._first + self._n, dtype=np.int64),
                                     len(self._units))
        self._steps_of_pos.setflags(write=False)
        self._reads: List[Dict[str, Any]] = []
        self._locks: Dict[int, Dict[str, Any]] = {}
        self._alarm_locks: Dict[int, Dict[str, Any]] = {}     # owner ruling AE: lead -> alarm lock record
        self._opened: Dict[int, str] = {}
        self._surfaces: set = set()                  # SHA-256 of every DecisionSurface issued
        self._decisions: List[Dict[str, Any]] = []   # adoption documents decide() registered
        self._run_folder: Optional[Path] = None
        if run_folder is not None:
            folder = Path(run_folder)
            if not folder.is_dir():
                raise VaultRefusal("G-LOCK", "the run folder %s does not exist" % folder,
                                   fix="create the run folder first (runs/)")
            self._run_folder = folder.resolve()
            self._load_folder_state()

    # ---------------------------------------------------------------- properties
    @property
    def grid(self) -> DenseGrid:
        return self._grid

    @property
    def test_first_time(self) -> int:
        return self._test_first

    @property
    def run_folder(self) -> Optional[Path]:
        return self._run_folder

    def read_log(self) -> Tuple[Dict[str, Any], ...]:
        """Every read made through this view, in order (for the fitctx_log and the manifest)."""
        return tuple(dict(r) for r in self._reads)

    def opened_passes(self) -> Dict[int, str]:
        """{lead: adoption hash} of the scoring passes whose test labels are open."""
        return dict(self._opened)

    def locked_passes(self) -> Dict[int, str]:
        """{lead: adoption hash} of the passes whose adoption is locked."""
        return {lead: rec["sha256"] for lead, rec in self._locks.items()}

    def alarm_locked_passes(self) -> Dict[int, str]:
        """{lead: alarm record hash} of the passes whose alarm record is locked (owner ruling AE)."""
        return {lead: rec["sha256"] for lead, rec in self._alarm_locks.items()}

    def test_window_reads(self) -> Dict[str, Any]:
        """The test-window positions asof_rows served (D54 a): the number of reads that reached the
        test window, their rows, and the rows served before any pass was locked. lock_adoption prints
        this total and writes it into its lock record."""
        reads = [r for r in self._reads if r.get("method") == "asof_rows" and r.get("test_window_rows")]
        return {"rule": "D54 (a): each row's history and persistence read the labels known at its issue "
                        "step, served before the pass's lock",
                "reads": len(reads), "rows": int(sum(r["test_window_rows"] for r in reads)),
                "rows_before_any_lock": int(sum(r["test_window_rows"] for r in reads
                                                if not r.get("locked_passes")))}

    def decision_documents(self) -> Tuple[Dict[str, Any], ...]:
        """Every adoption document decide() registered with this vault, in order (copies)."""
        return tuple(json.loads(dumps(d)) for d in self._decisions)

    # ---------------------------------------------------------------- internals
    def _log(self, method: str, purpose: str, cut: Optional[int], n_rows: int,
             max_time: Optional[int], **extra: Any) -> None:
        rec = {"method": method, "purpose": purpose, "cut": cut, "rows": int(n_rows),
               "max_label_time": None if max_time is None else int(max_time)}
        rec.update(extra)
        self._reads.append(rec)

    def _cut_last_day(self, cut: int) -> int:
        return int(step_bounds(np.array([int(cut)], dtype=np.int64), self._cadence)[1][0])

    def _before_test(self, cut: int, what: str) -> int:
        cut = _int(cut, "the cut of %s" % what, "G-FITCUT")
        if cut >= self._test_first:
            raise VaultRefusal("G-FITCUT", "%s at %d reaches the test window (first step %d); no fitted "
                               "object is ever cut inside it" % (what, cut, self._test_first),
                               fix="every fit and guard cut lies at or before the donor train end")
        return cut

    def _usable(self, cut: int) -> np.ndarray:
        """Grid positions usable at a cut (R11): valid, dated at or before the cut, own window ended
        by the cut's last day. Boolean mask over every position."""
        return (self._valid & (self._steps_of_pos <= cut)
                & (self._window_end <= self._cut_last_day(cut)))

    def _unit_rows_mask(self, unit_rows: np.ndarray) -> np.ndarray:
        keep = np.zeros(len(self._units), dtype=bool)
        keep[unit_rows] = True
        return np.repeat(keep, self._n)

    def _asof_positions(self, cut: int, unit_rows: Optional[np.ndarray], purpose: str,
                        method: str = "asof") -> np.ndarray:
        """The positions asof(cut) serves, optionally restricted to some unit rows, ascending (grid
        order: unit by unit, step order). FitContext's hand-outs come through here, logged. The one
        implementation of the as-of rule (asof calls it too)."""
        cut = self._before_test(cut, "an as-of read")
        mask = self._usable(cut)
        if unit_rows is not None:
            rows = np.asarray(unit_rows, dtype=np.int64)
            if rows.size and (rows.min() < 0 or rows.max() >= len(self._units)):
                raise VaultRefusal("G-LOCK", "unit rows off the grid")
            mask &= self._unit_rows_mask(rows)
        pos = np.flatnonzero(mask)
        latest = int(self._steps_of_pos[pos].max()) if pos.size else None
        if latest is not None and latest > cut:
            raise VaultRefusal("G-FITCUT", "internal: an as-of read served a label after its cut")
        self._log(method, purpose, cut, pos.size, latest)
        return pos

    def _label_values(self, positions: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """(unit ids as object array, times int64, y float64) of grid positions (copies)."""
        pos = np.asarray(positions, dtype=np.int64)
        unit_rows = pos // self._n
        units = np.asarray(self._units, dtype=object)[unit_rows]
        return units, self._steps_of_pos[pos].copy(), self._y[pos].copy()

    def _issued_surface(self, sha256: str) -> bool:
        """True if this vault issued a DecisionSurface with this content hash (decide() asks)."""
        return sha256 in self._surfaces

    def _register_decision(self, document: Mapping[str, Any]) -> None:
        """decide() registers the adoption document of a surface this vault issued (a strict-JSON copy
        is kept; an identical document is kept once). lock_adoption locks only a registered one."""
        if not isinstance(document, Mapping) or not isinstance(document.get("decision"), Mapping):
            raise VaultRefusal("G-LOCK", "internal: a decision document carries its decision section")
        if document["decision"].get("surface_sha256") not in self._surfaces:
            raise VaultRefusal("G-LOCK", "the decision was made on a surface this vault did not issue")
        copy = json.loads(dumps(document))
        if copy not in self._decisions:
            self._decisions.append(copy)

    def _decision_for(self, adoption: Adoption) -> Dict[str, Any]:
        """The registered document whose adoption part is this adoption's document; refuses none, or
        several distinct ones."""
        want = dumps(adoption_document(adoption))
        found = {}
        for doc in self._decisions:
            part = {k: v for k, v in doc.items() if k != "decision"}
            if dumps(part) == want:
                found[dumps(doc)] = doc
        if not found:
            raise VaultRefusal("G-LOCK", "this adoption was not made by decide() on a decision surface "
                                         "this vault issued; only such an adoption is locked",
                               fix="issue the surface with LabelView.decision_surface and run "
                                   "layer.decide.decide on it")
        if len(found) > 1:
            raise VaultRefusal("G-LOCK", "decide() made this same adoption on %d different decision "
                               "surfaces of this vault; which one to lock is ambiguous" % len(found))
        return json.loads(next(iter(found)))

    # ---------------------------------------------------------------- reads
    # Provenance: plan 2.1 R3 ("reads only whether rows exist, never their values"), R12 (valid rows
    # only), R18 (candidates = units with at least one valid row at or before the train end).
    def validity(self, first_time: int, last_time: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Label validity (valid or NaN) of every row inside [first_time, last_time]; never a value.

        Rule: R3, R12, R18, G-LOCK. Returns (unit ids, times, is_valid) per grid row in the window, in
        grid order. The window may span the test window (R3 reads whether valid rows exist there).
        The read is logged. Refuses: first_time > last_time.
        """
        first = _int(first_time, "first_time", "R3")
        last = _int(last_time, "last_time", "R3")
        if first > last:
            raise VaultRefusal("R3", "validity window [%d, %d] is empty" % (first, last))
        pos = np.flatnonzero((self._steps_of_pos >= first) & (self._steps_of_pos <= last))
        units, times, _ = self._label_values(pos)
        self._log("validity", "validity", None, pos.size, None, first=first, last=last)
        return units, times, self._valid[pos].copy()

    # Provenance: plan 2.1 R11 and 5 G-DONOR; plan 4.1 step 2 (derive runs before any feature pool or
    # FitContext exists); LORO addendum (donor groups = every group; the refusal of a test-group unit
    # becomes the refusal of a unit that belongs to no group of the split).
    def donor_labels(self, split: Any, cut: int, cut_kind: CutKind, lead: int,
                     unit_ids: Optional[Tuple[str, ...]], purpose: str, *,
                     picks: Any = None) -> DonorLabels:
        """Label-only donor rows at or before a cut, for plan-time rules.

        Rule: R11, G-DONOR; R18, R19, R22, R30. Donor groups: every group of the data minus the
        exclusions (split.groups_under_loro), sorted. Rows at or before the cut whose own label window
        has ended by then, valid labels only. unit_ids restricts to those units (the bank units,
        scope 'picked'); None takes every unit of the donor groups (scope 'all_donor_units', R18's
        event rate only). Rows in grid order (unit id, step); the row-key hash is row_key_hash's. The
        hand-out is logged, with whether the bank-unit check ran.
        LORO addendum (flagged): the refusal becomes "a unit that is not a bank unit". The approved
        signature carries no bank lists, so the vault checks it only when the keyword picks (the R18
        lists, split.UnitLists) is given; without it only a unit outside the split's groups is refused.
        Refuses: a unit that is not on the grid or belongs to no donor group; with picks, a unit
        outside the bank lists, or picks with unit_ids None; a cut at or after test_first_time; a
        negative lead; an empty purpose.
        """
        purpose = _name(purpose, "purpose")
        kind = _cut_kind(cut_kind)
        lead = _int(lead, "lead", "R11")
        if lead < 0:
            raise VaultRefusal("R11", "lead %d is negative" % lead)
        cut = self._before_test(cut, "a donor view")
        data_groups = tuple(sorted(set(self._unit_groups)))
        groups = _split.groups_under_loro(split, data_groups)
        in_group = np.isin(np.asarray(self._unit_groups, dtype=object), np.asarray(groups, dtype=object))
        bank_units = None
        if picks is not None:
            bank = getattr(picks, "bank", None)
            if not isinstance(bank, Mapping):
                raise VaultRefusal("R18", "picks must be the R18 unit lists (split.UnitLists)")
            if unit_ids is None:
                raise VaultRefusal("R18", "picks restrict a 'picked' donor view; the all-units view "
                                          "(unit_ids None) takes none")
            bank_units = {str(u) for g in bank for u in bank[g]}
        if unit_ids is None:
            rows = np.flatnonzero(in_group)
            scope = ALL_UNITS_SCOPE
        else:
            wanted = [str(u) for u in unit_ids]
            bad = sorted(u for u in set(wanted) if u not in self._row_of or not in_group[self._row_of[u]])
            if bad:
                raise VaultRefusal("G-DONOR", "donor units %s are not units of the donor groups"
                                   % bad[:_SHOW], fix="pass bank units of the split's groups")
            if bank_units is not None:
                off = sorted(set(wanted) - bank_units)
                if off:
                    raise VaultRefusal("G-DONOR", "donor units %s are not bank units (R18 lists)"
                                       % off[:_SHOW], fix="donor rows are every group's bank units")
            rows = np.asarray(sorted({self._row_of[u] for u in wanted}), dtype=np.int64)
            scope = PICKED_SCOPE
        mask = self._usable(cut) & self._unit_rows_mask(rows)
        pos = np.flatnonzero(mask)
        units, times, y = self._label_values(pos)
        group_of_row = np.asarray(self._unit_groups, dtype=object)[pos // self._n]
        self._log("donor_labels", purpose, cut, pos.size, int(times.max()) if times.size else None,
                  scope=scope, lead=lead, cut_kind=kind.value, bank_unit_check=bank_units is not None)
        return DonorLabels(groups=groups, cut=cut, cut_kind=kind, lead=lead, unit_scope=scope,
                           unit_ids=units, times=times, group_of_row=group_of_row, y=y,
                           row_key_hash=row_key_hash(units, times))

    # Provenance: plan 4.2 (LabelView.asof(cut)); plan 2.1 R11.
    def asof(self, cut: int) -> LabelSlice:
        """Every label dated at or before the cut whose own window has ended by then.

        Rule: R11, G-FITCUT. FitContext is the only caller for fitted objects. Valid labels only, in
        grid order. Refuses: a cut at or after test_first_time.
        """
        pos = self._asof_positions(cut, None, "asof")
        units, times, y = self._label_values(pos)
        return LabelSlice(cut=int(cut), unit_ids=units, times=times, y=y)

    # Provenance: plan 5 G-LOCK ("history, persistence and pools read labels through the as-of view");
    # plan 2.3 R17; plan 4.1 steps 4 and 8; D54 (a).
    def asof_rows(self, unit_rows: np.ndarray, newest_readable: np.ndarray, k_back: int, *,
                  purpose: str = "rows") -> np.ndarray:
        """Per-row as-of reads: for each row, the same unit's label exactly k_back steps before its
        newest readable step, or NaN.

        Rule: R17, R31, G-LOCK, G-CALENDAR (D54 a). Every read is in the row's own unit and dated at or
        before its newest readable step (timing.latest_label_step, or step - 1 for a target-derived
        column), through the dense-grid position (unit row, step). A read before the grid's first
        step, or of an invalid label, is NaN. Under D54 (a) a test row's read may fall in the test
        window before its own issue step, served before the pass's lock: decide() never sees a test
        row (its surface comes from decision_surface, never from here). Each read is logged with its
        purpose (keyword, default 'rows'), the newest step it served, how many test-window positions it
        read (test_window_rows), and the passes locked and opened at that moment; test_window_reads()
        totals them.
        Returns float64 labels, NaN where absent or invalid.
        Refuses: k_back < 0; unit rows off the grid; mismatched lengths; a read after the grid's last
        step; an empty purpose.
        """
        purpose = _name(purpose, "purpose")
        k = _int(k_back, "k_back", "R17")
        if k < 0:
            raise VaultRefusal("R17", "k_back is negative (%d)" % k)
        rows = as_int_array(unit_rows, "unit rows", rule="R17")
        newest = as_int_array(newest_readable, "newest readable steps", rule="R17")
        if rows.shape != newest.shape:
            raise VaultRefusal("R17", "unit rows (%d) and newest readable steps (%d) differ in length"
                               % (rows.size, newest.size))
        if rows.size and (rows.min() < 0 or rows.max() >= len(self._units)):
            raise VaultRefusal("R17", "unit rows off the grid (0..%d)" % (len(self._units) - 1))
        read = newest - k
        last = self._first + self._n - 1
        if read.size and int(read.max()) > last:
            raise VaultRefusal("G-LOCK", "a read at step %d lies after the grid's last step %d"
                               % (int(read.max()), last))
        out = np.full(rows.size, np.nan)
        inside = read >= self._first
        pos = rows[inside] * self._n + (read[inside] - self._first)
        out[inside] = self._y[pos]
        served = read[inside][np.isfinite(out[inside])]
        self._log("asof_rows", purpose, None, rows.size, int(served.max()) if served.size else None,
                  k_back=k, test_window_rows=int(np.count_nonzero(read[inside] >= self._test_first)),
                  locked_passes=sorted(self._locks), opened_passes=sorted(self._opened))
        return out

    # Provenance: plan 5 G-LOCK ("decide() sees only decision-surface data"); plan 2.4 R26 (the inner
    # score rows, labels read at the train end); D67 (the caller picks the rows and prints the counts).
    def decision_surface(self, unit_ids: np.ndarray, times: np.ndarray, cut: int, *,
                         purpose: str = "decision_surface") -> DecisionSurface:
        """The decision surface of the layer: the as-of labels at a cut for the given (unit, step) rows,
        in the order given (the caller routes the rows in that order).

        Rule: R11, R26, G-LOCK, D67. The ONLY way a layer.decide.DecisionSurface is made: y is looked up
        by the vault, never passed in. Each row must have a label in asof(cut) (valid, dated at or
        before the cut, its own window ended by the cut's last day); the cut must lie before the test
        window. The arrays are read-only; the surface carries its SHA-256 (surface_sha256), which the
        vault records and decide() re-checks. The issue is logged.
        Returns DecisionSurface.
        Refuses: a cut at or after test_first_time; no row; mismatched lengths; a unit off the grid; a
        step off the grid; a repeated (unit, step); a row without a label in the as-of view (after the
        cut, in the test window, invalid, or whose window has not ended), counted by reason.
        """
        purpose = _name(purpose, "purpose")
        cut = self._before_test(cut, "a decision surface")
        units = np.asarray([str(u) for u in np.asarray(unit_ids, dtype=object).ravel().tolist()], dtype=object)
        t = as_int_array(times, "surface times", rule="G-LOCK")
        if np.asarray(unit_ids).ndim != 1 or units.shape != t.shape:
            raise VaultRefusal("G-LOCK", "a decision surface needs one unit id per step (1-D, %d unit ids, "
                               "%d steps)" % (units.size, t.size))
        if units.size == 0:
            raise VaultRefusal("R26", "the decision surface has no row")
        rows = np.fromiter((self._row_of.get(u, -1) for u in units.tolist()), dtype=np.int64,
                           count=units.size)
        if (rows < 0).any():
            raise VaultRefusal("G-LOCK", "%d surface rows name units that are not on the grid, e.g. %s"
                               % (int((rows < 0).sum()), sorted(set(units[rows < 0].tolist()))[:_SHOW]))
        last = self._first + self._n - 1
        outside = (t < self._first) | (t > last)
        if outside.any():
            raise VaultRefusal("G-LOCK", "%d surface rows lie outside the grid's steps [%d, %d]"
                               % (int(outside.sum()), self._first, last))
        pos = rows * self._n + (t - self._first)
        if np.unique(pos).size != pos.size:
            raise VaultRefusal("R26", "%d surface rows repeat a (unit, step)" % int(pos.size - np.unique(pos).size))
        usable = self._usable(cut)[pos]
        if not usable.all():
            bad = ~usable
            after = bad & (t > cut)
            in_test = bad & (t >= self._test_first)
            invalid = bad & ~after & ~self._valid[pos]
            window = bad & ~after & self._valid[pos]
            raise VaultRefusal("G-LOCK", "%d surface row(s) have no label in the as-of view at the cut %d: "
                               "%d dated after the cut (%d of them in the test window), %d invalid "
                               "(NaN), %d whose own label window ends after the cut's last day"
                               % (int(bad.sum()), cut, int(after.sum()), int(in_test.sum()),
                                  int(invalid.sum()), int(window.sum())),
                               fix="the decision surface is the inner score rows with a valid label at "
                                   "the cut (D67: the caller picks the rows and prints the counts)")
        y = np.array(self._y[pos], dtype=np.float64, copy=True)
        sha = surface_sha256(units, t, y, cut, self._test_first)
        frozen = []
        for arr in (units, np.array(t, dtype=np.int64, copy=True), y):
            base = np.array(arr, copy=True)
            base.setflags(write=False)
            frozen.append(base.view())                # a view of a read-only base cannot be made writable
        with _issuing_surface():
            surface = DecisionSurface(unit_ids=frozen[0], times=frozen[1], y=frozen[2], label_cut=int(cut),
                                      test_first_time=int(self._test_first), sha256=sha)
        object.__setattr__(surface, "_issuer", weakref.ref(self))
        self._surfaces.add(sha)
        self._log("decision_surface", purpose, cut, units.size, int(t.max()), surface_sha256=sha)
        return surface

    # ---------------------------------------------------------------- the locks
    def _require_folder(self, run_folder: Any, what: str) -> Path:
        if self._run_folder is None:
            raise VaultRefusal("G-LOCK", "%s needs a vault built with the run folder; this vault has none"
                               % what, fix="build LabelView with run_folder=<the run folder>")
        if run_folder is not None and Path(run_folder).resolve() != self._run_folder:
            raise VaultRefusal("G-LOCK", "%s: the vault was built with the run folder %s, not %s"
                               % (what, self._run_folder, Path(run_folder).resolve()))
        return self._run_folder

    def _load_folder_state(self) -> None:
        """Re-read the lock records and opened markers of the run folder (a resumed run), refusing a
        folder whose adoption file differs from its lock record, or whose opened marker names an
        adoption other than the locked one."""
        folder = self._run_folder
        for path in sorted(folder.glob("*" + LOCK_SUFFIX)):
            rec = read_json(path)
            name = rec.get("file")
            lead = rec.get("lead")
            if name != path.name[:-len(LOCK_SUFFIX)] or not isinstance(lead, int):
                raise VaultRefusal("G-LOCK", "the lock record %s is malformed" % path)
            target = folder / name
            if not target.is_file():
                raise VaultRefusal("G-LOCK", "the lock record %s names %s, which is missing" % (path, name))
            if _file_sha(target) != rec.get("sha256"):
                raise VaultRefusal("G-LOCK", "%s differs from its lock record (SHA-256 %s, recorded %s): "
                                   "a locked adoption was changed" % (target, _file_sha(target),
                                                                       rec.get("sha256")))
            if lead in self._locks:
                raise VaultRefusal("G-LOCK", "two lock records for lead %d" % lead)
            self._locks[lead] = dict(rec)
        # owner ruling AE: the alarm lock records, with the same checks (file present, hash equal, one per lead)
        for path in sorted(folder.glob("*" + ALARM_LOCK_SUFFIX)):
            rec = read_json(path)
            name = rec.get("file")
            lead = rec.get("lead")
            if name != path.name[:-len(ALARM_LOCK_SUFFIX)] or not isinstance(lead, int):
                raise VaultRefusal("G-LOCK", "the alarm lock record %s is malformed" % path)
            target = folder / name
            if not target.is_file():
                raise VaultRefusal("G-LOCK", "the alarm lock record %s names %s, which is missing" % (path, name))
            if _file_sha(target) != rec.get("sha256"):
                raise VaultRefusal("G-LOCK", "%s differs from its alarm lock record (SHA-256 %s, recorded %s): a "
                                   "locked alarm record was changed" % (target, _file_sha(target), rec.get("sha256")))
            if lead in self._alarm_locks:
                raise VaultRefusal("G-LOCK", "two alarm lock records for lead %d" % lead)
            self._alarm_locks[lead] = dict(rec)
        for path in sorted(folder.glob("test_labels_opened_lead_*.json")):
            m = _OPENED_RE.match(path.name)
            if not m:
                continue
            lead = int(m.group(1))
            rec = read_json(path)
            locked = self._locks.get(lead)
            if locked is None or rec.get("adoption_sha256") != locked["sha256"]:
                raise VaultRefusal("G-LOCK", "the run folder holds test labels of lead %d opened against "
                                   "adoption %s, but its locked adoption is %s"
                                   % (lead, rec.get("adoption_sha256"),
                                      None if locked is None else locked["sha256"]),
                                   fix="a run folder whose test labels were opened under another "
                                       "adoption is never reused")
            if "alarm_sha256" in rec:
                alarm = self._alarm_locks.get(lead)
                if alarm is None or rec.get("alarm_sha256") != alarm["sha256"]:
                    raise VaultRefusal("G-LOCK", "the run folder holds test labels of lead %d opened against alarm "
                                       "record %s, but its locked alarm record is %s"
                                       % (lead, rec.get("alarm_sha256"), None if alarm is None else alarm["sha256"]),
                                       fix="a run folder whose test labels were opened under another alarm record "
                                           "is never reused")
            self._opened[lead] = rec["adoption_sha256"]

    def _register_lock(self, lead: int, record: Dict[str, Any]) -> None:
        self._locks[int(lead)] = dict(record)

    def _register_alarm_lock(self, lead: int, record: Dict[str, Any]) -> None:
        self._alarm_locks[int(lead)] = dict(record)

    # Provenance: plan 4.1 steps 8-9 and 11 (adoption hashed before the test labels open; the ladder per
    # lead); plan 5 G-LOCK; pm25_forecast.py:601-606.
    def open_test_labels(self, adoption_sha256: str, lead: int, *, alarm_sha256: str) -> TestLabels:
        """Release the test-window labels for ONE scoring pass, only against the hash of the adoption
        that pass uses and the hash of its locked alarm record.

        Rule: R27, R29, G-LOCK. Lead 0 is the nowcast test pass (lock_adoption), lead L that lead's
        pass (lock_lead_adoption). It opens only if that pass's adoption file exists in the run
        folder, its SHA-256 equals the given hash and the hash the lock recorded, and the lock was
        written before this call. The opening is logged and marked on disk (write-once). Every
        test-window row of every unit is released (NaN = an invalid label; the scoring code picks the
        rows and prints the counts), in grid order.
        alarm_sha256 (keyword, required; owner ruling AE): the hash lock_alarm returned for this pass's
        alarm record. The pass opens only if that record is locked (lock_alarm), its SHA-256 equals the
        given hash, the recorded one and the file on disk, and its lock was written before this call; the
        opened marker records it.
        Returns TestLabels.
        Refuses: no run folder; no locked adoption for that pass; a hash mismatch (given, recorded or
        on disk); a lead pass whose nowcast adoption was never locked; no locked alarm record for that
        pass, an alarm hash mismatch, or an alarm lock written after this call.
        """
        folder = self._require_folder(None, "opening test labels")
        lead = _int(lead, "lead", "G-LOCK")
        if lead < 0:
            raise VaultRefusal("G-LOCK", "lead %d is negative" % lead)
        if not isinstance(adoption_sha256, str) or not _SHA_RE.match(adoption_sha256):
            raise VaultRefusal("G-LOCK", "the adoption hash must be a SHA-256 hex digest, got %r"
                               % (adoption_sha256,))
        if lead > 0 and 0 not in self._locks:
            raise VaultRefusal("G-LOCK", "lead %d's test labels cannot open: the nowcast adoption was "
                               "never locked" % lead, fix="lock_adoption first, then lock_lead_adoption")
        rec = self._locks.get(lead)
        if rec is None:
            raise VaultRefusal("G-LOCK", "no locked adoption for the %s pass; test labels open only "
                               "after the adoption is hashed" % ("nowcast" if lead == 0 else "lead %d" % lead),
                               fix="lock_adoption (nowcast) or lock_lead_adoption (lead) first")
        path = folder / rec["file"]
        if not path.is_file():
            raise VaultRefusal("G-LOCK", "the locked adoption file %s is missing" % path)
        on_disk = _file_sha(path)
        if not (adoption_sha256 == rec["sha256"] == on_disk):
            raise VaultRefusal("G-LOCK", "hash mismatch for the %s pass: given %s, recorded %s, on disk %s"
                               % ("nowcast" if lead == 0 else "lead %d" % lead, adoption_sha256,
                                  rec["sha256"], on_disk),
                               fix="open test labels only with the hash the lock returned")
        now = time.time()
        if float(rec.get("locked_at_epoch", now + 1.0)) > now or os.path.getmtime(path) > now + 1.0:
            raise VaultRefusal("G-LOCK", "the adoption of this pass was not written before this call")
        # owner ruling AE: the pass's alarm record is locked before its test labels open
        if not isinstance(alarm_sha256, str) or not _SHA_RE.match(alarm_sha256):
            raise VaultRefusal("G-LOCK", "the alarm record hash must be a SHA-256 hex digest, got %r"
                               % (alarm_sha256,))
        alarm = self._alarm_locks.get(lead)
        if alarm is None:
            raise VaultRefusal("G-LOCK", "no locked alarm record for the %s pass; test labels open only after the "
                               "twin-disagreement alarm is decided and locked (owner ruling AE)"
                               % ("nowcast" if lead == 0 else "lead %d" % lead), fix="lock_alarm first")
        alarm_path = folder / alarm["file"]
        if not alarm_path.is_file():
            raise VaultRefusal("G-LOCK", "the locked alarm record %s is missing" % alarm_path)
        alarm_disk = _file_sha(alarm_path)
        if not (alarm_sha256 == alarm["sha256"] == alarm_disk):
            raise VaultRefusal("G-LOCK", "alarm hash mismatch for the %s pass: given %s, recorded %s, on disk %s"
                               % ("nowcast" if lead == 0 else "lead %d" % lead, alarm_sha256, alarm["sha256"],
                                  alarm_disk), fix="open test labels only with the hash lock_alarm returned")
        if float(alarm.get("locked_at_epoch", now + 1.0)) > now or os.path.getmtime(alarm_path) > now + 1.0:
            raise VaultRefusal("G-LOCK", "the alarm record of this pass was not written before this call")
        pos = np.flatnonzero(self._steps_of_pos >= self._test_first)
        units, times, y = self._label_values(pos)
        marker = folder / (OPENED_FILE % lead)
        if marker.exists():
            old = read_json(marker)
            if old.get("adoption_sha256") != adoption_sha256:
                raise VaultRefusal("G-LOCK", "lead %d's test labels were opened under adoption %s"
                                   % (lead, old.get("adoption_sha256")))
            if old.get("alarm_sha256") != alarm_sha256:
                raise VaultRefusal("G-LOCK", "lead %d's test labels were opened under alarm record %s"
                                   % (lead, old.get("alarm_sha256")))
        else:
            write_text_once(marker, dumps({"lead": lead, "adoption_sha256": adoption_sha256,
                                           "alarm_sha256": alarm_sha256,
                                           "opened_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                           "rows": int(pos.size)}) + "\n")
        self._opened[lead] = adoption_sha256
        self._log("open_test_labels", "test_pass", None, pos.size,
                  int(times.max()) if times.size else None, lead=lead, adoption_sha256=adoption_sha256)
        return TestLabels(lead=lead, adoption_sha256=adoption_sha256, unit_ids=units, times=times, y=y)


# ---------------------------------------------------------------------------------------------------
def _write_locked(folder: Path, name: str, lead: int, text: str, labels: LabelView,
                  extra: Optional[Dict[str, Any]] = None, suffix: str = LOCK_SUFFIX) -> str:
    """Write <name> once and its lock record <name><suffix> (with any extra fields), register the lock with the
    vault, return the hash. An existing file with the same text completes (or confirms) its lock; different
    text is refused. suffix LOCK_SUFFIX: an adoption; ALARM_LOCK_SUFFIX: an alarm record (owner ruling AE)."""
    if suffix not in (LOCK_SUFFIX, ALARM_LOCK_SUFFIX):
        raise VaultRefusal("G-LOCK", "internal: unknown lock suffix %r" % (suffix,))
    what = "adoption" if suffix == LOCK_SUFFIX else "alarm record"
    path = folder / name
    want = _sha(text.encode("utf-8"))
    if path.exists():
        if path.read_bytes() != text.encode("utf-8"):
            raise VaultRefusal("G-LOCK", "%s exists with different content (SHA-256 %s, this %s %s); "
                               "a locked %s never changes" % (path, _file_sha(path), what, want, what),
                               fix="start a new run")
    else:
        write_text_once(path, text)
    got = _file_sha(path)
    if got != want:
        raise VaultRefusal("G-LOCK", "internal: %s reads back with SHA-256 %s, written %s" % (path, got, want))
    lock = folder / (name + suffix)
    record = {"lead": int(lead), "file": name, "sha256": got,
              "locked_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "locked_at_epoch": time.time()}
    record.update(extra or {})
    if lock.exists():
        old = read_json(lock)
        if old.get("sha256") != got or old.get("file") != name or old.get("lead") != int(lead):
            raise VaultRefusal("G-LOCK", "the lock record %s names another %s" % (lock, what))
        record = old
    else:
        write_text_once(lock, dumps(record) + "\n")
    if suffix == LOCK_SUFFIX:
        labels._register_lock(lead, record)
    else:
        labels._register_alarm_lock(lead, record)
    print("%s locked: lead %d, %s, SHA-256 %s" % (what, lead, name, got))
    return got


def _check_vault(labels: Any, run_folder: Any, what: str) -> Path:
    if not isinstance(labels, LabelView):
        raise VaultRefusal("G-LOCK", "%s needs the run's LabelView, got %s" % (what, type(labels).__name__))
    if run_folder is None:
        raise VaultRefusal("G-LOCK", "%s needs the run folder" % what)
    return labels._require_folder(run_folder, what)


# Provenance: plan 2.4 R27 ("adoption.json is hashed before test labels open"); plan 7.1 (written once,
# atomically: temp file, fsync, rename -- runs/atomic.py, the source's pm25_forecast.py:347-356).
def lock_adoption(adoption: Adoption, labels: LabelView, run_folder: Path) -> str:
    """Write the nowcast's adoption.json once and return its SHA-256; after this the nowcast adoption
    cannot change.

    Rule: R27, G-LOCK. The adoption (arm, link, tool, weighting, penalty, or declined, with the best
    tree arm and its penalty, and every candidate's MAE; layer.decide.adoption_document) is checked (a
    placebo or trees-off arm is never adopted). The document written is the one decide() registered
    with this vault when it scored a surface this vault issued: the adoption plus its decision section
    (surface hash, cuts, candidate order, missing arms with their declared reason, the legacy
    declaration, the candidate table's hash). It is written atomically once, hashed, and recorded in a
    lock record and in the vault; the lock record and the console carry the pre-lock test-window reads
    (test_window_reads, D54 a). The caller puts the hash in the manifest before any test label is
    opened; Type 3 runs only after it. Calling it again with the same adoption returns the same hash
    (resume).
    Returns the SHA-256 hex digest of adoption.json.
    Refuses: any test labels already opened in this run; an adoption no decide() made on a surface of
    this vault (or made on several); an adoption naming a link R22 does not have when its decision
    declared no legacy candidate list; an existing adoption.json with different content; a vault
    built without this run folder; an adoption the layer could not have made.
    """
    folder = _check_vault(labels, run_folder, "lock_adoption")
    if labels._opened:
        raise VaultRefusal("G-LOCK", "test labels of pass(es) %s are open already; the nowcast adoption "
                           "is locked before any test label opens" % sorted(labels._opened))
    document = labels._decision_for(adoption)
    arms = [a for a in (adoption.adopted, adoption.best_tree_arm) + tuple(adoption.eligible) if a is not None]
    foreign = sorted({getattr(a.link, "value", repr(a.link)) for a in arms if not isinstance(a.link, Link)})
    if foreign and not document["decision"].get("legacy"):
        raise VaultRefusal("R22", "the adoption names link key(s) %s, which R22 does not have, and its "
                           "decision declared no legacy candidate list" % foreign,
                           fix="production adoptions use R22's links; a harness replay declares "
                               "LegacyCandidates")
    reads = labels.test_window_reads()
    text = dumps(document) + "\n"
    sha = _write_locked(folder, ADOPTION_FILE, 0, text, labels, {"pre_lock_test_window_reads": reads})
    print("pre-lock test-window reads (asof_rows, D54 a): %d rows over %d reads, %d before any lock"
          % (reads["rows"], reads["reads"], reads["rows_before_any_lock"]))
    return sha


# Provenance: plan 2.4 R29 (the N2 guard at each lead on the inner guard's cut; a pinned arm);
# pm25_forecast.py:601-606 (each rung's adoption written to disk before any test row is routed).
def lock_lead_adoption(lead_adoption: LeadAdoption, nowcast: Adoption, nowcast_sha256: str,
                       labels: LabelView, run_folder: Path) -> str:
    """Write one forecast lead's adoption file once and return its SHA-256, before any of that lead's
    test rows is scored.

    Rule: R29, R27 (N2), G-LOCK. The file (lead, pinned arm, penalty, guard result, adopted or
    declined, placebo flag, and the nowcast adoption's hash; layer.decide.lead_adoption_document) is
    written atomically once and hashed; only then may open_test_labels(hash, lead) release that lead's
    test labels. The pin must be R29's pin (layer.decide.pin_of): the nowcast's adopted arm and
    penalty, or its best tree arm and that arm's penalty when it declined.
    Returns the SHA-256 hex digest of the lead's file.
    Refuses: lead 0 (the nowcast uses lock_adoption); a nowcast hash that lock_adoption did not
    record, or a nowcast Adoption whose document differs from the locked adoption.json's adoption
    part (the file on disk must still hash to the recorded lock); a pin that differs from R29's pin;
    this lead's test labels already open; an existing file for this lead with different content; a
    vault built without this run folder.
    """
    folder = _check_vault(labels, run_folder, "lock_lead_adoption")
    if not isinstance(lead_adoption, LeadAdoption):
        raise VaultRefusal("G-LOCK", "lock_lead_adoption takes a LeadAdoption, got %s"
                           % type(lead_adoption).__name__)
    lead = _int(lead_adoption.lead, "the lead", "R29")
    if lead < 1:
        raise VaultRefusal("R29", "lead %d: the nowcast pass is locked by lock_adoption" % lead)
    recorded = labels._locks.get(0)
    if recorded is None or recorded["sha256"] != nowcast_sha256:
        raise VaultRefusal("G-LOCK", "the nowcast hash %r is not the one lock_adoption recorded (%s)"
                           % (nowcast_sha256, None if recorded is None else recorded["sha256"]),
                           fix="pass the hash lock_adoption returned")
    locked_path = folder / recorded["file"]
    if not locked_path.is_file() or _file_sha(locked_path) != nowcast_sha256:
        raise VaultRefusal("G-LOCK", "the locked nowcast adoption %s is missing or differs from its lock"
                           % locked_path)
    locked_doc = json.loads(locked_path.read_text(encoding="utf-8"))
    locked_part = {k: v for k, v in locked_doc.items() if k != "decision"}
    if dumps(locked_part) != dumps(adoption_document(nowcast)):
        raise VaultRefusal("G-LOCK", "the nowcast Adoption passed is not the locked one (its document "
                           "differs from the locked adoption.json)")
    pinned, penalty = pin_of(nowcast)
    if lead_adoption.pinned != pinned or as_point(lead_adoption.penalty) != penalty:
        raise VaultRefusal("R29", "lead %d is pinned to %r at %r; R29's pin is %r at %r"
                           % (lead, lead_adoption.pinned, lead_adoption.penalty, pinned, penalty),
                           fix="pin to the nowcast's adopted arm, or its best tree arm when it declined")
    if lead in labels._opened:
        raise VaultRefusal("G-LOCK", "lead %d's test labels are open already; its adoption can no longer "
                           "change" % lead)
    text = dumps(lead_adoption_document(lead_adoption, nowcast_sha256)) + "\n"
    return _write_locked(folder, LEAD_ADOPTION_FILE % lead, lead, text, labels)


# Provenance: OWNER_RULINGS_2026-10-06.md section AE (AE1: "the ratio, the decision and both predictions are recorded
# and locked before labels open"); D:/treeroute/engine_v2/SPEC_ALARM.txt 5.3-5.4.
def lock_alarm(document: Mapping[str, Any], lead: int, labels: LabelView, run_folder: Path) -> str:
    """Write one scoring pass's alarm record (alarm_lead_<lead>.json) once and return its SHA-256, before any of
    that pass's test labels opens (owner ruling AE).

    Rule: AE1, G-LOCK. The document (layer/alarm.py alarm_document or not_applicable_document: the rule, the AE3
    origin, the constants, the adopted arm and its twin, the eligibility, the reference gap, every batch and the
    hash of the locked predictions) is written atomically once with a lock record
    alarm_lead_<lead>.json.alarmlock.json (lead, file, SHA-256, times and the pass's adoption hash). A pass whose
    alarm record is already locked with the same bytes is confirmed (a resumed pass recomputes it).
    Returns the SHA-256 hex digest of the file.
    Refuses: a document whose lead or adoption hash differ from the arguments or the pass's locked adoption; no
    locked adoption for that pass; that pass's test labels already open (unless the same record was locked
    before them); an existing record with other bytes (start a new run); a vault built without this run folder.
    """
    folder = _check_vault(labels, run_folder, "lock_alarm")
    lead = _int(lead, "the lead", "G-LOCK")
    if lead < 0:
        raise VaultRefusal("G-LOCK", "lead %d is negative" % lead)
    if not isinstance(document, Mapping):
        raise VaultRefusal("G-LOCK", "an alarm record is a mapping, got %s" % type(document).__name__)
    if document.get("lead") != lead:
        raise VaultRefusal("G-LOCK", "the alarm record names lead %r, not %d" % (document.get("lead"), lead))
    adoption = labels._locks.get(lead)
    if adoption is None:
        raise VaultRefusal("G-LOCK", "no locked adoption for the %s pass: its alarm record is locked after its "
                           "adoption" % ("nowcast" if lead == 0 else "lead %d" % lead),
                           fix="lock_adoption (nowcast) or lock_lead_adoption (lead) first")
    if document.get("adoption_sha256") != adoption["sha256"]:
        raise VaultRefusal("G-LOCK", "the alarm record names adoption %r; the %s pass's locked adoption is %s"
                           % (document.get("adoption_sha256"), "nowcast" if lead == 0 else "lead %d" % lead,
                              adoption["sha256"]))
    name = ALARM_FILE % lead
    text = dumps(document) + "\n"
    old = labels._alarm_locks.get(lead)
    same = old is not None and (folder / name).is_file() and (folder / name).read_bytes() == text.encode("utf-8")
    if lead in labels._opened and not same:
        raise VaultRefusal("G-LOCK", "lead %d's test labels are open already; its alarm record is locked before "
                           "they open" % lead, fix="start a new run")
    return _write_locked(folder, name, lead, text, labels, {"adoption_sha256": adoption["sha256"]},
                         suffix=ALARM_LOCK_SUFFIX)


__all__ = ["ADOPTION_FILE", "LEAD_ADOPTION_FILE", "LOCK_SUFFIX", "ALARM_FILE", "ALARM_LOCK_SUFFIX", "OPENED_FILE",
           "VaultRefusal", "LabelSlice", "TestLabels", "DonorLabels", "row_key_hash", "LabelView", "lock_adoption",
           "lock_lead_adoption", "lock_alarm"]
