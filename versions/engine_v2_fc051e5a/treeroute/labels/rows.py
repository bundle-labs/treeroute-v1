"""The row vault of the table option: RowLabelView, the label vault over a table's ROW GRID.

Owner ruling U1 (the owner rulings file, section U); design in SPEC_TABLE_MODE.md 3.4. In a table run each
sample row is the engine's unit, so the rows form a keys-only DenseGrid with ONE step (package/table.py). The
parent LabelView (labels/vault.py, not edited) is built on that grid unchanged, with every row at step 0; this
subclass then swaps "step" for "day": every position's time is the row's TARGET DAY (a day ordinal), and a cut is a
day. Every inherited read that compares a position's time with a cut (the as-of rule of R11, validity, the donor
views, the decision surface's checks, the test-window release) then works in days, through the parent's own code.

What changes against the parent (and only this):
  - _steps_of_pos holds the target days (read-only); _cut_last_day(cut) is the cut itself (a cut is a day);
  - decision_surface: a row's position is the row itself, and each given time must equal its row's target day;
    the rest is the parent's checks (the as-of label rule, the hash, the issuer registration);
  - asof_rows refuses (R17: a table run builds no own-history block);
  - for_lead(present): the same rows and run folder with the labels of rows absent at that lead set to NaN, so a
    lead's donor rows, contexts, guard surface, lock and test labels never hold a row the lead's file lacks
    (SPEC_TABLE_MODE.md 1.6, departure table_absent_rows); built after the nowcast lock, it re-reads the locks
    from the run folder (the parent constructor's _load_folder_state);
  - last_label_before(...): R31's persistence input: per scored row, the newest valid label of the SAME package
    unit with target day strictly before the row's issue day (D54 a: it may read a test-window label before the
    lead's lock), asserted on every label it serves and logged with how many test-window labels it served; with
    with_days=True it also returns the day of each label served (damped persistence's issue-side normal), so
    no caller reads the labels outside the vault;
  - test_window_reads counts the reads of asof_rows OR last_label_before, so the totals are true.
Locks (labels.vault.lock_adoption, lock_lead_adoption) take this vault unchanged: it is a LabelView.
"""
# Provenance for the module: SPEC_TABLE_MODE.md 3.4; labels/vault.py (the parent, owner rulings A-F, D54 a);
# OWNER_RULINGS_2026-10-06.md U1, U4 (the pool and every label read is strictly before the issue date).

import weakref
from types import SimpleNamespace
from typing import Any, Dict, Optional

import numpy as np

from treeroute.derive.shapes import Cadence, CadenceKind
from treeroute.io.steps import as_int_array
from treeroute.layer.decide import DecisionSurface, _issuing_surface, surface_sha256

from .vault import LabelView, VaultRefusal, _SHOW, _name

LAST_LABEL_METHOD = "last_label_before"
COUNTED_METHODS = ("asof_rows", LAST_LABEL_METHOD)


class RowLabelView(LabelView):
    """The label vault of a table run (module docstring). Built like the parent with times all 0 on the one-step
    row grid; package_units (keyword) names each row's package unit (R31's persistence reads the same unit)."""

    def __init__(self, grid: Any, target: Any, target_days: np.ndarray, test_first_day: int, run_folder: Any, *,
                 package_units: np.ndarray) -> None:
        days = as_int_array(target_days, "target days", rule="G-LOCK")
        n = len(tuple(grid.unit_ids))
        if int(getattr(grid, "n_steps", 0)) != 1 or int(getattr(grid, "first_step", -1)) != 0:
            raise VaultRefusal("G-LOCK", "the row vault takes the one-step row grid (first step 0, one step)")
        if days.shape != (n,):
            raise VaultRefusal("G-LOCK", "the row vault needs one target day per row (%d days for %d rows)"
                               % (days.size, n))
        units = np.asarray(package_units, dtype=object)
        if units.shape != (n,):
            raise VaultRefusal("G-LOCK", "the row vault needs one package unit per row")
        if tuple(str(u) for u in np.asarray(target.unit_ids, dtype=object).tolist()) != tuple(str(u) for u in grid.unit_ids):
            raise VaultRefusal("G-LOCK", "the row vault's target rows must be the grid's rows, in grid order")
        super().__init__(grid, target, np.zeros(n, dtype=np.int64), int(test_first_day), days, run_folder,
                         cadence=Cadence(kind=CadenceKind.IRREGULAR))
        steps = np.array(days, dtype=np.int64, copy=True)
        steps.setflags(write=False)
        self._steps_of_pos = steps
        self._package_units = np.array(units, dtype=object, copy=True)
        self._package_units.setflags(write=False)
        self._target = target
        self._lead = 0

    # ---------------------------------------------------------------- the day form
    def _cut_last_day(self, cut: int) -> int:
        """A table cut is a day (R11 events): its last day is itself."""
        return int(cut)

    @property
    def package_units(self) -> np.ndarray:
        return self._package_units

    @property
    def target_days(self) -> np.ndarray:
        return self._steps_of_pos

    # ---------------------------------------------------------------- reads
    def decision_surface(self, unit_ids: np.ndarray, times: np.ndarray, cut: int, *,
                         purpose: str = "decision_surface") -> DecisionSurface:
        """The parent's decision surface on the row grid: each row's position is the row itself, and each given
        time must equal its row's target day (else refused). The as-of rule, the hash and the issuer
        registration are the parent's (labels/vault.py decision_surface)."""
        purpose = _name(purpose, "purpose")
        cut = self._before_test(cut, "a decision surface")
        units = np.asarray([str(u) for u in np.asarray(unit_ids, dtype=object).ravel().tolist()], dtype=object)
        t = as_int_array(times, "surface times", rule="G-LOCK")
        if np.asarray(unit_ids).ndim != 1 or units.shape != t.shape:
            raise VaultRefusal("G-LOCK", "a decision surface needs one row id per day (1-D, %d row ids, %d days)"
                               % (units.size, t.size))
        if units.size == 0:
            raise VaultRefusal("R26", "the decision surface has no row")
        pos = np.fromiter((self._row_of.get(u, -1) for u in units.tolist()), dtype=np.int64, count=units.size)
        if (pos < 0).any():
            raise VaultRefusal("G-LOCK", "%d surface rows name rows that are not on the row grid, e.g. %s"
                               % (int((pos < 0).sum()), sorted(set(units[pos < 0].tolist()))[:_SHOW]))
        if not np.array_equal(self._steps_of_pos[pos], t):
            raise VaultRefusal("G-LOCK", "%d surface row(s) give a day other than their row's target day"
                               % int((self._steps_of_pos[pos] != t).sum()))
        if np.unique(pos).size != pos.size:
            raise VaultRefusal("R26", "%d surface rows repeat a row" % int(pos.size - np.unique(pos).size))
        usable = self._usable(cut)[pos]
        if not usable.all():
            bad = ~usable
            after = bad & (t > cut)
            in_test = bad & (t >= self._test_first)
            invalid = bad & ~after & ~self._valid[pos]
            raise VaultRefusal("G-LOCK", "%d surface row(s) have no label in the as-of view at the cut %d: %d dated "
                               "after the cut (%d of them in the test window), %d invalid (NaN)"
                               % (int(bad.sum()), cut, int(after.sum()), int(in_test.sum()), int(invalid.sum())),
                               fix="the decision surface is train rows with a valid label at the cut (D67)")
        y = np.array(self._y[pos], dtype=np.float64, copy=True)
        sha = surface_sha256(units, t, y, cut, self._test_first)
        frozen = []
        for arr in (units, np.array(t, dtype=np.int64, copy=True), y):
            base = np.array(arr, copy=True)
            base.setflags(write=False)
            frozen.append(base.view())
        with _issuing_surface():
            surface = DecisionSurface(unit_ids=frozen[0], times=frozen[1], y=frozen[2], label_cut=int(cut),
                                      test_first_time=int(self._test_first), sha256=sha)
        object.__setattr__(surface, "_issuer", weakref.ref(self))
        self._surfaces.add(sha)
        self._log("decision_surface", purpose, cut, units.size, int(t.max()), surface_sha256=sha)
        return surface

    def asof_rows(self, unit_rows: np.ndarray, newest_readable: np.ndarray, k_back: int, *,
                  purpose: str = "rows") -> np.ndarray:
        """Refused: a table run builds no own-history block (R17 is empty for the neighbour kind); persistence
        reads last_label_before."""
        raise VaultRefusal("R17", "asof_rows reads a grid unit's label k steps back; a table run has no own-history "
                           "block (R17 empty) and reads persistence with last_label_before")

    def last_label_before(self, unit_codes: np.ndarray, issue_days: np.ndarray, purpose: str, *,
                          with_days: bool = False) -> Any:
        """R31's persistence input (D54 a): per scored row, the newest VALID label of the SAME package unit whose
        target day is strictly before the row's issue day, or NaN. unit_codes: each scored row's package unit;
        issue_days: each scored row's issue day. Asserts both conditions on every label served. Logged with the
        purpose, the newest day served and how many served labels lie in the test window (test_window_rows).
        with_days: also return the target day of each served label (-1 where none), as (labels, days); the one
        read is logged once. Never an arm, a guard or a decide() input."""
        purpose = _name(purpose, "purpose")
        units = np.asarray(unit_codes, dtype=object)
        issue = as_int_array(issue_days, "issue days", rule="R31")
        if units.shape != issue.shape:
            raise VaultRefusal("R31", "%d package units and %d issue days" % (units.size, issue.size))
        by_unit: Dict[str, np.ndarray] = {}
        valid_pos = np.flatnonzero(self._valid)
        pu = self._package_units[valid_pos]
        order = np.lexsort((self._steps_of_pos[valid_pos], pu.astype(str)))
        vp = valid_pos[order]
        names, starts = np.unique(self._package_units[vp].astype(str), return_index=True)
        bounds = list(starts.tolist()) + [vp.size]
        for k, u in enumerate(names.tolist()):
            by_unit[u] = vp[bounds[k]:bounds[k + 1]]
        out = np.full(units.size, np.nan)
        out_day = np.full(units.size, -1, dtype=np.int64)
        served_days = []
        test_rows = 0
        for i, (u, d) in enumerate(zip(units.astype(str).tolist(), issue.tolist())):
            pos = by_unit.get(u)
            if pos is None or pos.size == 0:
                continue
            days = self._steps_of_pos[pos]
            j = int(np.searchsorted(days, int(d), side="left")) - 1
            if j < 0:
                continue
            p = int(pos[j])
            if not (int(self._steps_of_pos[p]) < int(d) and str(self._package_units[p]) == u and self._valid[p]):
                raise VaultRefusal("R31", "internal: last_label_before served a label not strictly before the issue "
                                   "day or of another unit")
            out[i] = self._y[p]
            out_day[i] = int(self._steps_of_pos[p])
            served_days.append(int(self._steps_of_pos[p]))
            test_rows += int(self._steps_of_pos[p] >= self._test_first)
        self._log(LAST_LABEL_METHOD, purpose, None, units.size, max(served_days) if served_days else None,
                  test_window_rows=int(test_rows), locked_passes=sorted(self._locks),
                  opened_passes=sorted(self._opened))
        if with_days:
            return out, out_day
        return out

    def test_window_reads(self) -> Dict[str, Any]:
        """The parent's totals, counting the reads of asof_rows OR last_label_before (D54 a)."""
        reads = [r for r in self._reads if r.get("method") in COUNTED_METHODS and r.get("test_window_rows")]
        return {"rule": "D54 (a): each row's persistence reads the labels known at its issue date, served before "
                        "the pass's lock",
                "reads": len(reads), "rows": int(sum(r["test_window_rows"] for r in reads)),
                "rows_before_any_lock": int(sum(r["test_window_rows"] for r in reads if not r.get("locked_passes")))}

    # ---------------------------------------------------------------- one lead
    def for_lead(self, present: np.ndarray, lead: int) -> "RowLabelView":
        """The same rows and run folder with the labels of rows absent at the lead set to NaN (SPEC_TABLE_MODE.md
        1.6; departure table_absent_rows). The absence is logged on this vault ('absent at lead L'). Built after
        the nowcast lock, the new vault re-reads the locks from the run folder."""
        mask = np.asarray(present, dtype=bool)
        if mask.shape != (len(self._units),):
            raise VaultRefusal("U1", "for_lead needs one presence flag per row")
        y = np.where(mask, np.asarray(self._target.y, dtype=np.float64), np.nan)
        target = SimpleNamespace(unit_ids=self._target.unit_ids, group_ids=self._target.group_ids, y=y)
        view = RowLabelView(self._grid, target, self._steps_of_pos, self._test_first, self._run_folder,
                            package_units=self._package_units)
        view._lead = int(lead)
        self._log("for_lead", "absent at lead %d" % int(lead), None, int((~mask).sum()), None, lead=int(lead))
        return view


def build_row_vault(data: Any, test_first_day: int, run_folder: Optional[Any]) -> RowLabelView:
    """The run's row vault over package/table.TableData (the ONLY holder of the labels, G-LOCK)."""
    target = SimpleNamespace(unit_ids=np.asarray(data.row_ids, dtype=object), group_ids=np.asarray(data.groups, dtype=object),
                             y=np.asarray(data.y, dtype=np.float64))
    return RowLabelView(data.grid, target, np.asarray(data.target_day, dtype=np.int64), int(test_first_day), run_folder,
                        package_units=np.asarray(data.units, dtype=object))


__all__ = ["RowLabelView", "build_row_vault", "LAST_LABEL_METHOD"]
